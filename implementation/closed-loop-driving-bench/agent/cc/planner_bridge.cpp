// DE4SDV closed-loop driving bench: drivingAgent's embedded CPython (see planner_bridge.h).
#include "planner_bridge.h"

#include <Python.h>

#include <cstring>

#include "json_lite.h"

namespace de4sdv::driving::agent {
namespace {

std::string FetchPythonError() {
  PyObject *type = nullptr, *value = nullptr, *trace = nullptr;
  PyErr_Fetch(&type, &value, &trace);
  PyErr_NormalizeException(&type, &value, &trace);
  std::string text = "python error";
  if (value != nullptr) {
    PyObject* s = PyObject_Str(value);
    if (s != nullptr) {
      const char* c = PyUnicode_AsUTF8(s);
      if (c != nullptr) text = c;
      Py_DECREF(s);
    }
  }
  if (type != nullptr) {
    PyObject* name = PyObject_GetAttrString(type, "__name__");
    if (name != nullptr) {
      const char* c = PyUnicode_AsUTF8(name);
      if (c != nullptr) text = std::string(c) + ": " + text;
      Py_DECREF(name);
    }
  }
  // Keep the traceback on stderr (drivingAgent.stderr) for the post-mortem.
  PyErr_Restore(type, value, trace);
  PyErr_Print();
  return text;
}

std::string AsString(PyObject* o) {
  if (o == nullptr || !PyUnicode_Check(o)) return {};
  const char* c = PyUnicode_AsUTF8(o);
  return c != nullptr ? std::string(c) : std::string{};
}

class Gil {
 public:
  Gil() : state_(PyGILState_Ensure()) {}
  ~Gil() { PyGILState_Release(state_); }

 private:
  PyGILState_STATE state_;
};

PyObject* MemoryViewOrNone(const void* data, std::size_t bytes) {
  if (data == nullptr || bytes == 0) Py_RETURN_NONE;
  return PyMemoryView_FromMemory(const_cast<char*>(static_cast<const char*>(data)), static_cast<Py_ssize_t>(bytes),
                                 PyBUF_READ);
}

// Releases every memoryview over agent memory after a call. memoryview.release() raises
// BufferError while an export (a numpy view) is still alive: Python then holds a reference into a
// frame-store buffer that is about to be reused, which must never pass silently.
bool ReleaseViews(std::vector<PyObject*>& views, std::string* error) {
  bool ok = true;
  for (PyObject* v : views) {
    if (v == nullptr || v == Py_None) {
      Py_XDECREF(v);
      continue;
    }
    PyObject* r = PyObject_CallMethod(v, "release", nullptr);
    if (r == nullptr) {
      ok = false;
      *error = "a buffer of agent memory is still referenced from Python: " + FetchPythonError();
    } else {
      Py_DECREF(r);
    }
    Py_DECREF(v);
  }
  views.clear();
  return ok;
}

}  // namespace

bool PlannerBridge::Start(const std::string& python_executable, const std::vector<std::string>& paths,
                          const std::string& setup_json, Identity* identity, std::string* setup_result_json,
                          std::string* error) {
  PyConfig config;
  PyConfig_InitPythonConfig(&config);
  config.install_signal_handlers = 0;  // FEO keeps SIGINT/SIGTERM
  // The planner's Python comes only from the configuration (the executable's environment plus
  // `paths`): PYTHONPATH, PYTHONHOME and the other PYTHON* variables of the host, and the user's
  // site directory, would change which libraries the planner loads without the run record showing
  // it (on the simulator host a PYTHONPATH meant for Python 3.10 tools broke the numpy import).
  config.use_environment = 0;
  config.user_site_directory = 0;
  PyStatus status = PyConfig_SetBytesString(&config, &config.executable, python_executable.c_str());
  if (PyStatus_Exception(status)) {
    PyConfig_Clear(&config);
    *error = "PyConfig executable failed";
    return false;
  }
  status = Py_InitializeFromConfig(&config);
  PyConfig_Clear(&config);
  if (PyStatus_Exception(status)) {
    *error = std::string("Py_InitializeFromConfig failed: ") + (status.err_msg ? status.err_msg : "?");
    return false;
  }
  PyObject* sys_path = PySys_GetObject("path");  // borrowed
  for (auto it = paths.rbegin(); it != paths.rend(); ++it) {
    PyObject* p = PyUnicode_FromString(it->c_str());
    PyList_Insert(sys_path, 0, p);
    Py_DECREF(p);
  }
  PyObject* module = PyImport_ImportModule("de4sdv_planner");
  if (module == nullptr) {
    *error = "import de4sdv_planner: " + FetchPythonError();
    main_state_ = PyEval_SaveThread();
    return false;
  }
  module_ = module;
  PyObject* result = PyObject_CallMethod(module, "setup", "s", setup_json.c_str());
  if (result == nullptr) {
    *error = "de4sdv_planner.setup: " + FetchPythonError();
    main_state_ = PyEval_SaveThread();
    return false;
  }
  *setup_result_json = AsString(result);
  Py_DECREF(result);
  std::string parse_error;
  const auto doc = json::Value::Parse(*setup_result_json, &parse_error);
  const auto* ident = doc.Find("identity");
  if (ident == nullptr) {
    *error = "setup returned no identity: " + parse_error;
    main_state_ = PyEval_SaveThread();
    return false;
  }
  identity->refused = ident->Find("refused") != nullptr && ident->Find("refused")->AsBool(true);
  identity->reason = ident->Find("reason") ? ident->Find("reason")->AsString("") : "";
  identity->expected = ident->Find("expectedSha256") ? ident->Find("expectedSha256")->AsString("") : "";
  identity->actual = ident->Find("actualSha256") ? ident->Find("actualSha256")->AsString("") : "";
  started_ = !identity->refused;
  module_ready_ = true;  // REQ-DRIVING-035: a refused run still writes its run record
  main_state_ = PyEval_SaveThread();  // release the GIL; every later call takes it
  return true;
}

bool PlannerBridge::BindThread(std::string* result_json, std::string* error) {
  if (!started_) return false;
  Gil gil;
  PyObject* r = PyObject_CallMethod(static_cast<PyObject*>(module_), "bind_thread", nullptr);
  if (r == nullptr) {
    *error = "bind_thread: " + FetchPythonError();
    return false;
  }
  *result_json = AsString(r);
  Py_DECREF(r);
  return true;
}

bool PlannerBridge::SetRig(const std::string& rig_json, std::string* result_json, std::string* error) {
  if (!started_) return false;
  Gil gil;
  PyObject* r = PyObject_CallMethod(static_cast<PyObject*>(module_), "set_rig", "s", rig_json.c_str());
  if (r == nullptr) {
    *error = "set_rig: " + FetchPythonError();
    return false;
  }
  *result_json = AsString(r);
  Py_DECREF(r);
  return true;
}

bool PlannerBridge::WriteRunRecord(const std::string& path, const std::string& fields_json,
                                   std::string* result_json, std::string* error) {
  if (!module_ready_) {
    *error = "write_run_record: de4sdv_planner.setup has not returned";
    return false;
  }
  Gil gil;
  PyObject* r = PyObject_CallMethod(static_cast<PyObject*>(module_), "write_run_record", "ss", path.c_str(),
                                    fields_json.c_str());
  if (r == nullptr) {
    *error = "write_run_record: " + FetchPythonError();
    return false;
  }
  *result_json = AsString(r);
  Py_DECREF(r);
  return true;
}

bool PlannerBridge::Condition(const ConditionIn& in, ConditionOut* out, std::string* error) {
  if (!started_) return false;
  Gil gil;
  std::vector<PyObject*> views;
  PyObject* images = PyList_New(6);
  PyObject* shapes = PyList_New(6);
  for (int i = 0; i < 6; ++i) {
    PyObject* mv = MemoryViewOrNone(in.image[i], in.image_bytes[i]);
    Py_INCREF(mv);  // one reference for the list, one kept to release the view after the call
    views.push_back(mv);
    PyList_SET_ITEM(images, i, mv);
    PyList_SET_ITEM(shapes, i, Py_BuildValue("(ii)", in.height[i], in.width[i]));
  }
  PyObject* matrix = PyBytes_FromStringAndSize(reinterpret_cast<const char*>(in.world_from_vehicle),
                                               sizeof(in.world_from_vehicle));
  PyObject* mc = MemoryViewOrNone(in.map_context, in.map_bytes);
  PyObject* rm = MemoryViewOrNone(in.route_mask, in.route_bytes);
  Py_INCREF(mc);
  Py_INCREF(rm);
  views.push_back(mc);
  views.push_back(rm);
  PyObject* r = PyObject_CallMethod(static_cast<PyObject*>(module_), "condition", "KOOOOO",
                                    static_cast<unsigned long long>(in.frame), images, shapes, matrix, mc, rm);
  Py_DECREF(images);
  Py_DECREF(shapes);
  Py_DECREF(matrix);
  Py_DECREF(mc);
  Py_DECREF(rm);
  bool ok = r != nullptr;
  if (!ok) *error = "condition: " + FetchPythonError();
  if (ok) {
    PyObject *primed = nullptr, *measured = nullptr, *checkpoint = nullptr, *record = nullptr;
    if (!PyArg_ParseTuple(r, "OSSU", &primed, &measured, &checkpoint, &record)) {
      *error = "condition returned an unexpected tuple: " + FetchPythonError();
      ok = false;
    } else {
      out->primed = PyObject_IsTrue(primed) == 1;
      const Py_ssize_t n = PyBytes_GET_SIZE(measured);
      out->has_rows = n == static_cast<Py_ssize_t>(sizeof(out->measured));
      if (out->has_rows && PyBytes_GET_SIZE(checkpoint) == n) {
        std::memcpy(out->measured, PyBytes_AS_STRING(measured), sizeof(out->measured));
        std::memcpy(out->checkpoint, PyBytes_AS_STRING(checkpoint), sizeof(out->checkpoint));
      } else if (n != 0) {
        *error = "condition returned rows of " + std::to_string(n) + " bytes";
        ok = false;
      }
      out->record_json = AsString(record);
    }
    Py_DECREF(r);
  }
  std::string release_error;
  if (!ReleaseViews(views, &release_error)) {
    *error = release_error;
    ok = false;
  }
  return ok;
}

bool PlannerBridge::Infer(std::uint64_t frame, InferOut* out, std::string* error) {
  if (!started_) return false;
  Gil gil;
  PyObject* r = PyObject_CallMethod(static_cast<PyObject*>(module_), "infer", "K", static_cast<unsigned long long>(frame));
  if (r == nullptr) {
    *error = "infer: " + FetchPythonError();
    return false;
  }
  bool ok = true;
  out->planned = false;
  if (r != Py_None) {
    PyObject *samples = nullptr, *record = nullptr;
    double v0 = 0.0;
    if (!PyArg_ParseTuple(r, "SdU", &samples, &v0, &record)) {
      *error = "infer returned an unexpected tuple: " + FetchPythonError();
      ok = false;
    } else if (PyBytes_GET_SIZE(samples) != static_cast<Py_ssize_t>(sizeof(out->samples))) {
      *error = "infer returned " + std::to_string(PyBytes_GET_SIZE(samples)) + " sample bytes";
      ok = false;
    } else {
      std::memcpy(out->samples, PyBytes_AS_STRING(samples), sizeof(out->samples));
      out->v0 = static_cast<float>(v0);
      out->record_json = AsString(record);
      out->planned = true;
    }
  }
  Py_DECREF(r);
  return ok;
}

void PlannerBridge::Stop() {
  if (module_ == nullptr) return;
  Gil gil;
  PyObject* r = PyObject_CallMethod(static_cast<PyObject*>(module_), "shutdown", nullptr);
  if (r == nullptr) {
    FetchPythonError();
  } else {
    Py_DECREF(r);
  }
  started_ = false;
  // No Py_FinalizeEx: CUDA and torch's threads end with the process.
}

}  // namespace de4sdv::driving::agent
