#!/usr/bin/env node
/** Browser-level regression for connected drag/resize behavior.
 *
 * Start the editor and Chromium with a DevTools port, then run:
 *   node tools/sysml_view_editor/tests/browser_interaction_check.mjs --port 9223
 *
 * No npm packages are required on Node 22+.
 */

const roleId = "vmA.cuttlefishGuest";
const portId = `${roleId}.structuredLogcatOut`;
const portArg = process.argv.indexOf("--port");
const port = portArg >= 0 ? Number(process.argv[portArg + 1]) : 9223;

const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find((target) => `${target.title || ""}${target.url || ""}`.includes("DE4SDV"));
if (!page) throw new Error("DE4SDV editor page not found in CDP targets");

const socket = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

let nextId = 1;
const pending = new Map();
socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    pending.get(message.id)(message);
    pending.delete(message.id);
  }
});

function call(method, params = {}) {
  const id = nextId++;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`CDP timeout: ${method}`));
    }, 10_000);
    pending.set(id, (message) => {
      clearTimeout(timer);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result || {});
    });
  });
}

async function evaluate(expression) {
  const result = await call("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result?.value;
}

function mouse(type, x, y, buttons) {
  return call("Input.dispatchMouseEvent", {
    type,
    x,
    y,
    button: "left",
    buttons,
    clickCount: 1,
  });
}

function assert(condition, message, value) {
  if (!condition) throw new Error(`${message}: ${JSON.stringify(value)}`);
}

try {
  await call("Page.reload", { ignoreCache: true });
  await new Promise((resolve) => setTimeout(resolve, 500));
  await evaluate("resetLayout(); true");

  const start = await evaluate(`(() => {
    const rect = document.querySelector('[data-role="${roleId}"] .role-box').getBoundingClientRect();
    return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2,
             role: {...placed['${roleId}']} };
  })()`);

  await mouse("mousePressed", start.x, start.y, 1);
  await mouse("mouseMoved", start.x + 80, start.y + 70, 1);
  const moved = await evaluate(`(() => {
    const role = placed['${roleId}']; const port = placed['${portId}'];
    return { role: {...role}, port: {...port},
             path: document.querySelector('.flow-path').getAttribute('d') };
  })()`);
  assert(moved.role.x === start.role.x + 80, "role x did not move", moved);
  assert(moved.role.y === start.role.y + 70, "role y did not move", moved);
  assert(moved.port.x === moved.role.x + moved.role.w, "output port detached during move", moved);
  assert(moved.port.y === moved.role.y + 20, "output port y detached during move", moved);
  assert(moved.path.startsWith(`M ${moved.port.x} ${moved.port.y}`), "flow detached during move", moved);
  await mouse("mouseReleased", start.x + 80, start.y + 70, 0);

  const afterMove = await evaluate(`({...placed['${roleId}']})`);
  assert(JSON.stringify(afterMove) === JSON.stringify(moved.role), "role snapped back", { afterMove, moved });

  const handle = await evaluate(`(() => {
    const rect = document.querySelector('[data-resize="${roleId}"]').getBoundingClientRect();
    return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2,
             role: {...placed['${roleId}']} };
  })()`);
  await mouse("mousePressed", handle.x, handle.y, 1);
  await mouse("mouseMoved", handle.x + 60, handle.y + 40, 1);
  const resized = await evaluate(`({role: {...placed['${roleId}']}, port: {...placed['${portId}']}})`);
  assert(resized.role.w === handle.role.w + 60, "role width did not resize", resized);
  assert(resized.role.h === handle.role.h + 40, "role height did not resize", resized);
  assert(resized.port.x === resized.role.x + resized.role.w, "output port detached during resize", resized);
  await mouse("mouseReleased", handle.x + 60, handle.y + 40, 0);

  const beforeSave = await evaluate(`({...placed['${roleId}']})`);
  await evaluate("saveLayout()");
  await call("Page.reload", { ignoreCache: true });
  await new Promise((resolve) => setTimeout(resolve, 500));
  const afterReload = await evaluate(`({...placed['${roleId}']})`);
  assert(JSON.stringify(afterReload) === JSON.stringify(beforeSave), "layout did not survive save/reload", { beforeSave, afterReload });

  console.log(JSON.stringify({ move: moved, resize: resized, saved: afterReload, result: "PASS" }, null, 2));
} finally {
  socket.close();
}
