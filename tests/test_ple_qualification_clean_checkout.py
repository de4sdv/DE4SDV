"""The privileged PLE qualification keeps its executor checkout clean (static + executed steps).

Both qualification scripts record ``executor_source_dirty`` from ``git status
--porcelain`` of the executor checkout. Runs 37410659181 and 38755211223 wrote
their inputs and evidence into that checkout (``_ple-baseline/``,
``ple-evidence/``, the nested ``_ple-experiment/`` checkout, the API service's
``logs/``), so every receipt said ``true``. These tests pin that no step writes
into the checkout, that the frozen experiment leaves it, that background
services run outside it, that the uploaded artifact keeps its name and layout,
and that a guard refuses a dirty checkout before each script that records the
flag. Both experiment checkouts (the experiment at PLEML 1.1.0 and the Gate A
experiment) leave it right after their checkout. The guard and relocation
steps run for real in scratch checkouts; the script command lines parse
against the real parsers (spied, nothing executes). No network, no dispatch.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/privileged-ple-qualification.yml"
INGESTION = ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
JOB = "qualify"
REV = "a" * 40
EXPERIMENT_CHECKOUT = "Checkout frozen experiment read-only as a separate input"
RELOCATE = "Relocate the frozen experiment outside the executor checkout"
GATE_A_CHECKOUT = "Checkout the Gate A experiment read-only as a separate input"
RELOCATE_GATE_A = "Relocate the Gate A experiment outside the executor checkout"
#: Each experiment checkout, the step that relocates it, and its workspace path.
EXPERIMENTS = ((EXPERIMENT_CHECKOUT, RELOCATE, "_ple-experiment"),
               (GATE_A_CHECKOUT, RELOCATE_GATE_A, "_ple-gate-a"))
LOCK = "Resolve current executor library lock without modifying frozen inputs"
REPLAY = "Exercise qualification guards and historical replay"
SCOPED = "Execute missing scoped PLE probes"
API = "Start isolated API and verify readiness"
FRESH = "Fresh current-toolchain serialization and real API readback"
UPLOAD = "Retain actual observations including failed execution"
GUARDS = ("Refuse a dirty checkout before the historical replay",
          "Refuse a dirty checkout before the scoped probes",
          "Refuse a dirty checkout before the fresh serialization")
# Everything the workflow produces; each name must only ever appear anchored
# outside the checkout.
OUTPUTS = ("_ple-baseline", "ple-evidence", "_ple-experiment", "_ple-gate-a", "ple-scoped-execution")
ANCHORS = ("/", "$RUNNER_TEMP/", "${RUNNER_TEMP}/", "$HOME/", "${HOME}/")
# Files the runner keeps under its own temporary directory.
RUNNER_FILES = frozenset(form % name for form in ("$%s", "${%s}")
                         for name in ("GITHUB_OUTPUT", "GITHUB_ENV", "GITHUB_STEP_SUMMARY", "GITHUB_PATH"))
INSIDE = ("./", "$GITHUB_WORKSPACE", "${GITHUB_WORKSPACE}")
PATH_OPTIONS = ("--out", "--historical-export", "--experiment", "--historical-experiment", "-o")
HEREDOC = re.compile(r"<<'PY'\n(.*?)\nPY(?:\n|$)", re.S)
REDIRECTION = re.compile(r"^(?:\d|&)?>>?(.*)$")
# A Path or open() literal rooted at a workflow output is a path relative to
# the checkout (run 38755211223: Path('_ple-baseline'), Path('ple-evidence/...')).
PYTHON_RELATIVE_OUTPUT = re.compile(r"""(?:Path|open)\(\s*['"](?:%s)""" % "|".join(map(re.escape, OUTPUTS)))
TEMP = "/tmp/de4sdv-ple-runner-temp"  # stands in for $RUNNER_TEMP when parsing command lines


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _steps():
    return _workflow()["jobs"][JOB]["steps"]


def _names():
    return [s.get("name") for s in _steps()]


def _step(name):
    matches = [s for s in _steps() if s.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _shell_lines(run):
    """Shell lines of a run script: heredoc bodies dropped, continuations joined, comments removed."""
    text = re.sub(r"\\\n\s*", " ", HEREDOC.sub("<<'PY'\n", run))
    for line in text.splitlines():
        code = re.split(r"(?:^|\s)#", line, maxsplit=1)[0].strip()
        if code:
            yield code


def _written_paths(argv):
    """Paths a shell command line writes, plus the workflow-produced paths it takes as input."""
    for index, token in enumerate(argv):
        following = argv[index + 1] if index + 1 < len(argv) else None
        redirection = REDIRECTION.match(token)
        if redirection:
            target = redirection.group(1) or following
            if target and not re.fullmatch(r"&\d+", target):  # 2>&1 and >&2 duplicate descriptors
                yield target
        elif token in PATH_OPTIONS and following:
            yield following
    if argv[0] == "mkdir":
        yield from (token for token in argv[1:] if not token.startswith("-"))
    elif argv[0] in ("cp", "mv") or argv[:2] == ["git", "clone"]:
        yield argv[-1]


@pytest.mark.parametrize("line, expected", [
    ('x --version > "$RUNNER_TEMP/ple-evidence/sysand-version.txt"', ["$RUNNER_TEMP/ple-evidence/sysand-version.txt"]),
    ("serve > ple-evidence/sysml-api.log 2>&1 &", ["ple-evidence/sysml-api.log"]),
    ("printf x >&2", []), ("echo x >>out.txt", ["out.txt"]),
    ("python scripts/x.py --out ple-evidence/r.json --experiment _ple-experiment", ["ple-evidence/r.json", "_ple-experiment"]),
    ("python scripts/x.py --historical-experiment _ple-gate-a", ["_ple-gate-a"]),
    ("mkdir -p ple-evidence/scoped", ["ple-evidence/scoped"]),
    ('cp -R "$RUNNER_TEMP/x/." ple-evidence/scoped/', ["ple-evidence/scoped/"]),
    ('mv _ple-experiment "$RUNNER_TEMP/_ple-experiment"', ["$RUNNER_TEMP/_ple-experiment"]),
    ("git clone --filter=blob:none https://example.invalid/r.git /tmp/r", ["/tmp/r"]),
    ("curl -fsSL -o /tmp/sbt-launch.jar https://example.invalid/sbt.jar", ["/tmp/sbt-launch.jar"]),
])
def test_the_written_path_pattern(line, expected):
    assert list(_written_paths(shlex.split(line))) == expected


_RUN_STEPS = [s["name"] for s in _steps() if s.get("run")]


def _outside_the_checkout(token):
    """A path the runner keeps outside the checkout: absolute (not the workspace), under RUNNER_TEMP or HOME, or a runner command file."""
    if token.startswith(INSIDE):
        return False
    if token.startswith("/home/runner/work/") and not token.startswith("/home/runner/work/_temp/"):
        return False
    return token.startswith(ANCHORS) or token in RUNNER_FILES


@pytest.mark.parametrize("token, outside", [
    ("/tmp/x", True), ("$RUNNER_TEMP/ple-evidence/x", True), ("${RUNNER_TEMP}/x", True),
    ("$HOME/.local/bin/sysand", True), ("$GITHUB_OUTPUT", True), ("${GITHUB_ENV}", True),
    ("/home/runner/work/_temp/x", True),
    ("ple-evidence/x", False), ("./x", False), ("$GITHUB_WORKSPACE/x", False),
    ("${GITHUB_WORKSPACE}/x", False), ("/home/runner/work/DE4SDV/DE4SDV/x", False),
    ("$GITHUB_OUTPUT/x", False), ("$RUNNER_TEMP", False),
])
def test_the_outside_the_checkout_pattern(token, outside):
    assert _outside_the_checkout(token) is outside


@pytest.mark.parametrize("name", _RUN_STEPS)
def test_no_run_step_writes_a_relative_or_workspace_path(name):
    for code in _shell_lines(_step(name)["run"]):
        for path in _written_paths(shlex.split(code)):
            assert _outside_the_checkout(path), (name, path)


@pytest.mark.parametrize("name", _RUN_STEPS)
def test_every_workflow_output_is_addressed_outside_the_checkout(name):
    for code in _shell_lines(_step(name)["run"]):
        argv = shlex.split(code)
        for index, token in enumerate(argv):
            if any(output in token for output in OUTPUTS):
                if argv[0] == "mv" and index < len(argv) - 1:
                    continue  # the relocation takes the experiment out of the checkout
                assert _outside_the_checkout(token), (name, token)


PATH_WRITES = {"write_text", "write_bytes", "mkdir", "touch", "unlink", "rmdir", "rename",
               "replace", "symlink_to", "hardlink_to", "chmod"}
FUNCTION_WRITES = {("os", "makedirs"), ("os", "mkdir"), ("os", "remove"), ("os", "unlink"),
                   ("os", "rename"), ("os", "replace"), ("os", "rmdir"), ("os", "symlink"),
                   ("os", "link"), ("os", "chmod"), ("shutil", "copy"), ("shutil", "copy2"),
                   ("shutil", "copyfile"), ("shutil", "copytree"), ("shutil", "move"),
                   ("shutil", "rmtree")}
COPIES = {"copy", "copy2", "copyfile", "copytree"}  # their first argument is only read


def _is_environment(node):
    """``os.environ`` or ``os.getenv``."""
    return (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "os" and node.attr in ("environ", "getenv"))


def _root(node, assignments, path_context=False, depth=0):
    """Where a path expression is rooted: relative, absolute, environment or unknown.

    A string literal is a path only in path context (an argument of Path(),
    open() or a writing os/shutil function); as a method receiver it is a string.
    """
    if depth > 8:
        return "unknown"
    if isinstance(node, ast.Constant):
        if not path_context or not isinstance(node.value, str):
            return "unknown"
        return "absolute" if node.value.startswith("/") else "relative"
    if isinstance(node, ast.Name):
        if node.id not in assignments:
            return "unknown"
        return _root(assignments[node.id], assignments, path_context, depth + 1)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _root(node.left, assignments, False, depth + 1)
    if isinstance(node, ast.Subscript):
        return "environment" if _is_environment(node.value) else "unknown"
    if isinstance(node, ast.Attribute):
        return "environment" if _is_environment(node) else _root(node.value, assignments, False, depth + 1)
    if isinstance(node, ast.Call):
        func = node.func
        if (isinstance(func, ast.Name) and func.id == "Path") or (isinstance(func, ast.Attribute) and func.attr == "Path"):
            return _root(node.args[0], assignments, True, depth + 1) if node.args else "relative"
        if isinstance(func, ast.Attribute):
            if _is_environment(func) or _is_environment(func.value):
                return "environment"
            return _root(func.value, assignments, False, depth + 1)
    return "unknown"


def _writing_mode(call, position):
    """True when the open() call's mode writes; a non-literal mode counts as writing."""
    mode = call.args[position] if len(call.args) > position else next(
        (keyword.value for keyword in call.keywords if keyword.arg == "mode"), None)
    if mode is None:
        return False
    return not isinstance(mode, ast.Constant) or any(flag in str(mode.value) for flag in "wax+")


def _checkout_relative_writes(source):
    """Writes through a path rooted at a relative literal, as (line, call) pairs."""
    tree = ast.parse(source)
    assignments = {target.id: node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   for target in node.targets if isinstance(target, ast.Name)}
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and (func.attr in PATH_WRITES
                                                or (func.attr == "open" and _writing_mode(node, 0))):
            paths, path_context = [func.value], False  # a receiver literal is a string, not a path
        elif isinstance(func, ast.Name) and func.id == "open" and _writing_mode(node, 1):
            paths, path_context = node.args[:1], True
        elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
              and (func.value.id, func.attr) in FUNCTION_WRITES):
            paths, path_context = (node.args[1:] if func.attr in COPIES else node.args), True
        else:
            continue
        if any(_root(path, assignments, path_context) == "relative" for path in paths):
            found.append((node.lineno, ast.unparse(func)))
    return found


@pytest.mark.parametrize("source, written", [
    ("Path('scratch.json').write_text('x')", True),
    ("p = Path('_ple-baseline')\n(p / 'export.json').write_bytes(b'')", True),
    ("name = 'note.txt'\nwith open(name, 'w') as f:\n    f.write('x')", True),
    ("os.makedirs('ple-evidence/scoped')", True),
    ("shutil.copytree('/tmp/src', 'ple-evidence')", True),
    ("Path().mkdir()", True),
    ("Path('docs/x').resolve().parent.mkdir()", True),
    ("temp = Path(os.environ['RUNNER_TEMP'])\nout = temp / 'ple-evidence'\nout.mkdir()\n(out / 'r.json').write_text('x')", False),
    ("with open(os.environ['GITHUB_OUTPUT'], 'a') as f:\n    f.write('x')", False),
    ("Path('/tmp/x').write_text('x')", False),
    ("base = Path('docs/gate-a-baseline')\n(base / 'manifest.json').read_text()", False),
    ("open('docs/manifest.json').read()", False),
    ("shutil.copytree('docs/x', '/tmp/x')", False),
    ("'a-b'.replace('-', '_')", False),
    ("Path(os.getenv('HOME')).joinpath('x').mkdir()", False),
    ("Path(os.environ.get('RUNNER_TEMP')).mkdir()", False),
])
def test_the_checkout_relative_write_pattern(source, written):
    assert bool(_checkout_relative_writes(source)) is written


@pytest.mark.parametrize("name", _RUN_STEPS)
def test_no_heredoc_writes_through_a_checkout_relative_path(name):
    for body in HEREDOC.findall(_step(name)["run"]):
        assert _checkout_relative_writes(body) == [], name
        assert PYTHON_RELATIVE_OUTPUT.search(body) is None, name


def _starts_a_background_process(run):
    """A lone ``&`` outside a comment (not ``&&``, ``2>&1``, ``&>`` or ``|&``)."""
    for line in run.splitlines():
        code = re.split(r"(?:^|\s)#", line, maxsplit=1)[0]
        if re.search(r"(?<![&|<>])&(?![&>])", code):
            return True
    return False


@pytest.mark.parametrize("line, started", [
    ("serve > /tmp/x.log 2>&1 &", True), ("serve & # comment", True), ("( serve & )", True),
    ("a && b", False), ("serve 2>&1 | tee x", False), ("serve &> /tmp/x", False),
    ("a |& b", False), ("# serve &", False), ('[ "${#SHA}" != "40" ]', False),
])
def test_the_background_process_pattern(line, started):
    assert _starts_a_background_process(line) is started


def test_background_services_run_outside_the_checkout():
    # The API service keeps writing logs/application.log relative to its
    # working directory after its step ends (#369, run 38669722943: "?? logs/"),
    # and the fresh serialization records executor_source_dirty after it.
    started = [s for s in _steps() if _starts_a_background_process(s.get("run") or "")]
    assert [s["name"] for s in started] == [API]
    for step in started:
        assert step.get("working-directory", "").startswith("/tmp/"), step["name"]
    assert '> "$RUNNER_TEMP/ple-evidence/sysml-api.log" 2>&1 &' in _step(API)["run"]


@pytest.mark.parametrize("checkout, relocate, path", EXPERIMENTS)
def test_each_experiment_leaves_the_executor_checkout_right_after_its_checkout(checkout, relocate, path):
    # actions/checkout refuses a path outside the workspace, and a nested
    # checkout is an untracked path of the executor checkout ("?? _ple-experiment/").
    names = _names()
    assert names.index(relocate) == names.index(checkout) + 1
    assert _step(checkout)["with"]["path"] == path
    assert _step(relocate)["run"] == _step(RELOCATE)["run"].replace("_ple-experiment", path)


def test_every_checkout_into_the_workspace_is_a_relocated_output():
    # A further nested checkout must be an output the path checks know and be
    # relocated in the next step, or it would make the receipts dirty unseen.
    steps = _steps()
    nested = [(index, step) for index, step in enumerate(steps)
              if str(step.get("uses", "")).startswith("actions/checkout@") and "path" in step.get("with", {})]
    assert [step["with"]["path"] for _, step in nested] == [path for _, _, path in EXPERIMENTS]
    for index, step in nested:
        path = step["with"]["path"]
        assert path in OUTPUTS, path
        assert f'mv {path} "$RUNNER_TEMP/{path}"' in (steps[index + 1].get("run") or ""), path


def test_the_replay_reads_gate_a_and_the_current_arms_read_the_pleml_1_1_0_experiment():
    assert _step(SCOPED)["env"]["DE4SDV_PLE_ORACLE"] == "${{ runner.temp }}/_ple-experiment"
    assert '--experiment "$RUNNER_TEMP/_ple-gate-a"' in _step(REPLAY)["run"]
    assert "_ple-experiment" not in _step(REPLAY)["run"]
    for name in (SCOPED, FRESH):
        assert '--experiment "$RUNNER_TEMP/_ple-experiment"' in _step(name)["run"], name
    assert '--historical-experiment "$RUNNER_TEMP/_ple-gate-a"' in _step(FRESH)["run"]
    assert "--historical-experiment" not in _step(REPLAY)["run"] + _step(SCOPED)["run"]


def test_the_upload_keeps_the_artifact_name_and_layout():
    upload = _step(UPLOAD)
    assert upload["if"] == "always()"
    assert upload["with"]["name"] == "ple-qualification-${{ inputs.ref }}-${{ github.run_id }}"
    assert upload["with"]["path"] == "${{ runner.temp }}/ple-evidence/"
    assert upload["with"]["if-no-files-found"] == "error"
    text = "\n".join(s.get("run") or "" for s in _steps())
    # The artifact root layout of run 38755211223; provider-origin.json and
    # scoped/receipt.json are pinned where their heredocs run (the PLE tests).
    for relative in ("sysand-version.txt", "historical-replay.json", "scoped/",
                     "scoped/cli-exit.txt", "sysml-api.log", "current/receipt.json"):
        assert re.search(r'"\$\{?RUNNER_TEMP\}?/ple-evidence/' + re.escape(relative) + '"', text), relative


def test_dirty_checkout_guards_run_before_each_script_that_records_the_flag():
    names = _names()
    assert names.index(RELOCATE) < names.index(LOCK) and names.index(RELOCATE_GATE_A) < names.index(LOCK)
    assert names.index(LOCK) < names.index(GUARDS[0]) < names.index(REPLAY)
    assert names.index(REPLAY) < names.index(GUARDS[1]) < names.index(SCOPED)
    assert names.index(API) < names.index(GUARDS[2]) < names.index(FRESH)
    ingestion = yaml.safe_load(INGESTION.read_text(encoding="utf-8"))
    reference = next(s for s in ingestion["jobs"]["ingest-and-validate"]["steps"]
                     if s.get("name") == "Refuse a dirty checkout before the import")
    for guard in GUARDS:
        step = _step(guard)
        assert step["run"] == reference["run"], guard  # the same check as the ingestion run (#369)
        assert "if" not in step and "continue-on-error" not in step, guard


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                           "-c", "commit.gpgsign=false", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def _scratch_checkout(path):
    """A one-commit Git checkout with one tracked file; returns its HEAD."""
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    (path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(path, "add", "tracked.txt")
    _git(path, "commit", "-q", "-m", "c")
    return _git(path, "rev-parse", "HEAD")


def _bash(script, cwd, env=None):
    """Run a step script the way GitHub runs a `run:` step without `shell:` (bash -e)."""
    assert "${{" not in script
    return subprocess.run(["bash", "-e", "-c", script], cwd=cwd, env=env,
                          capture_output=True, text=True)


def _dirty(checkout, kind):
    """Leave the checkout dirty the way the real runs were; returns the porcelain line."""
    if kind == "untracked baseline":
        (checkout / "_ple-baseline").mkdir()
        (checkout / "_ple-baseline/de4sdv-pleml-gate-a-export.json").write_text("{}", encoding="utf-8")
        return "?? _ple-baseline/"
    if kind == "nested experiment checkout":
        _scratch_checkout(checkout / "_ple-experiment")
        return "?? _ple-experiment/"
    if kind == "service log":
        (checkout / "logs").mkdir()
        (checkout / "logs/application.log").write_text("x", encoding="utf-8")
        return "?? logs/"
    assert kind == "modified tracked file"
    (checkout / "tracked.txt").write_text("changed\n", encoding="utf-8")
    return " M tracked.txt"


@pytest.mark.parametrize("guard", GUARDS)
@pytest.mark.parametrize("kind", [None, "untracked baseline", "nested experiment checkout",
                                  "service log", "modified tracked file"])
def test_a_dirty_checkout_guard_refuses_what_the_receipts_would_record(tmp_path, guard, kind):
    checkout = tmp_path / "checkout"
    _scratch_checkout(checkout)
    expected = _dirty(checkout, kind) if kind else None
    result = _bash(_step(guard)["run"], checkout)
    if expected:
        assert result.returncode == 1 and expected in result.stderr, result.stderr
    else:
        assert result.returncode == 0, result.stderr


def _experiment_checkout(workspace, library, name="_ple-experiment"):
    """A nested scratch checkout with a submodule, as actions/checkout leaves an experiment."""
    _scratch_checkout(library)
    experiment = workspace / name
    _scratch_checkout(experiment)
    _git(experiment, "-c", "protocol.file.allow=always", "submodule", "add", "-q",
         str(library), "external/pleml")
    _git(experiment, "commit", "-q", "-m", "submodule")
    return _git(experiment, "rev-parse", "HEAD")


def _relocate(tmp_path, relocate, name, *, occupied=False):
    """Run a relocation step in a scratch workspace; the scripts verify the frozen revision themselves."""
    workspace, temp = tmp_path / "workspace", tmp_path / "runner-temp"
    _scratch_checkout(workspace)
    head = _experiment_checkout(workspace, tmp_path / "pleml", name)
    temp.mkdir()
    if occupied:
        (temp / name).mkdir()
    result = _bash(_step(relocate)["run"], workspace, dict(os.environ, RUNNER_TEMP=str(temp)))
    return result, workspace, temp, head


@pytest.mark.parametrize("checkout, relocate, name", EXPERIMENTS)
def test_the_relocation_leaves_a_clean_executor_checkout_and_a_working_experiment(tmp_path, checkout, relocate, name):
    result, workspace, temp, head = _relocate(tmp_path, relocate, name)
    assert result.returncode == 0, result.stderr
    assert _git(workspace, "status", "--porcelain") == ""
    assert not (workspace / name).exists()
    moved = temp / name
    assert _git(moved, "rev-parse", "HEAD") == head
    assert _git(moved, "status", "--porcelain") == ""
    assert _git(moved, "show", "HEAD:tracked.txt") == "tracked"
    assert _git(moved / "external/pleml", "rev-parse", "HEAD") == _git(tmp_path / "pleml", "rev-parse", "HEAD")


@pytest.mark.parametrize("checkout, relocate, name", EXPERIMENTS)
def test_the_relocation_refuses_an_occupied_destination(tmp_path, checkout, relocate, name):
    result, workspace, _, _ = _relocate(tmp_path, relocate, name, occupied=True)
    assert result.returncode == 1, result.stderr
    assert (workspace / name).is_dir()  # nothing moved


def _script_commands():
    out = []
    for step in _steps():
        for code in _shell_lines(step.get("run") or ""):
            if code.startswith(("python scripts/", "python3 scripts/")):
                code = code.replace('"$SELECTED_REVISION"', REV).replace("$RUNNER_TEMP", TEMP)
                out.append((step["name"], shlex.split(code)))
    return out


class _Parsed(Exception):
    pass


#: The qualification scripts and the byte check of the fenced PLEML package they read.
_SCRIPTS = ("run_ple_qualification.py", "run_ple_scoped_execution.py", "check_pleml_package.py")
_COMMANDS = _script_commands()


def test_every_qualification_script_is_exercised():
    assert {Path(argv[1]).name for _, argv in _COMMANDS} == set(_SCRIPTS)
    assert len(_COMMANDS) == 4


@pytest.mark.parametrize("name, argv", _COMMANDS, ids=[c[0] for c in _COMMANDS])
def test_command_lines_parse_with_the_real_parsers_and_point_outside_the_checkout(monkeypatch, name, argv):
    import importlib
    import sys

    module = importlib.import_module("scripts." + Path(argv[1]).stem)
    captured = {}
    real = argparse.ArgumentParser.parse_args

    def spy(self, args=None, namespace=None):
        captured["namespace"] = real(self, args, namespace)
        raise _Parsed

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    monkeypatch.setattr(sys, "argv", argv[1:])
    with pytest.raises(_Parsed):
        module.main()
    namespace = vars(captured["namespace"])
    if namespace.get("expected_executor") is not None:
        assert namespace["expected_executor"] == REV
    for key in ("out", "historical_export", "experiment", "historical_experiment"):
        if namespace.get(key) is not None:
            path = Path(namespace[key])
            assert path.is_absolute() and not path.resolve().is_relative_to(ROOT), (name, key, path)
