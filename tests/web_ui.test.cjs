const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

// Minimal DOM for the app's state transitions. Requests stay pending so each
// test controls when a successful compilation or execution becomes available.
class Element {
  value = "";
  dataset = {};
  style = {};
  children = [];
  listeners = new Map();

  append(...children) {
    this.children.push(...children);
  }

  replaceChildren(...children) {
    this.children = children;
  }

  addEventListener(name, handler) {
    this.listeners.set(name, handler);
  }

  setAttribute(name, value) {
    this[name] = value;
  }
}

const source = readFileSync(
  resolve(__dirname, "../web/static/app.js"),
  "utf8",
);

function loadInterface() {
  const elements = new Map();
  const context = vm.createContext({
    document: {
      getElementById(id) {
        if (!elements.has(id)) elements.set(id, new Element());
        return elements.get(id);
      },
      createElement: () => new Element(),
      createTextNode: (text) => text,
    },
    window: new Element(),
    Node: Element,
    fetch: () => new Promise(() => {}),
    setTimeout,
    clearTimeout,
  });
  vm.runInContext(source, context);
  const run = (script) => vm.runInContext(script, context);
  run(`
    state.config = {
      grid: { width: 8, height: 8 },
      start: { x: 1, y: 4, orientation: "NORTE" },
    };
    state.cells = [];
    updateButtons();
  `);
  return { elements, run };
}

test("Execute requires a successful compilation", () => {
  const { elements, run } = loadInterface();
  assert.equal(elements.get("btn-run").disabled, true);
  run("state.compilation = { ok: false }; updateButtons();");
  assert.equal(elements.get("btn-run").disabled, true);
  run("state.compilation = { ok: true }; updateButtons();");
  assert.equal(elements.get("btn-run").disabled, false);
});

for (const [id, event] of [["source", "input"], ["optimize", "change"]]) {
  test(`Changing ${id} disables Execute until compilation succeeds again`, () => {
    const { elements, run } = loadInterface();
    run("state.compilation = { ok: true }; updateButtons();");
    assert.equal(elements.get("btn-run").disabled, false);
    elements.get(id).listeners.get(event)();
    assert.equal(elements.get("btn-run").disabled, true);
    assert.equal(run("state.compilation"), null);
  });
}

for (const failure of [
  'showRequestFailure(null, "No se pudo contactar con el servidor.");',
  'showRequestFailure({ message: "Error interno del servidor." });',
]) {
  test(`A new request failure stays visible after a completed execution: ${failure}`, () => {
    const { elements, run } = loadInterface();
    run(`
      state.compilation = { ok: true, assembly: [], diagnostics: [] };
      state.execution = {
        ok: true, start: state.config.start, final: state.config.start,
        events: [], diagnostics: [],
      };
      showFrame();
    `);
    assert.match(elements.get("status").textContent, /Ejecución completada/);
    run(failure);
    assert.equal(elements.get("status").dataset.tone, "err");
    assert.match(elements.get("status").textContent, /No se pudo procesar la solicitud/);
    assert.equal(elements.get("play-badge").dataset.tone, "err");
  });
}
