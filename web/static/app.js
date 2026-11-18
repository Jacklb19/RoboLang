"use strict";

// RoboLang interface. It only displays what the API returns: it never
// tokenizes, type-checks, optimizes or moves the robot by itself.

const API_PREFIX = "/api";
const PLAYBACK_DELAY_MS = { slow: 900, normal: 450, fast: 150 };
const ORIENTATION_DEGREES = { NORTE: 0, ESTE: 90, SUR: 180, OESTE: 270 };
// "fase léxica" (feminine) and "error léxico" (masculine).
const PHASE_NAMES = { lexical: "léxica", syntax: "sintáctica", semantic: "semántica", runtime: "ejecución" };
const ERROR_NAMES = { lexical: "léxico", syntax: "sintáctico", semantic: "semántico", runtime: "de ejecución" };
const MESSAGES = {
  notCompiled: "Sin compilar",
  invalidated: "El código cambió: vuelve a compilar",
  compiling: "Compilando…",
  running: "Ejecutando…",
  compileOk: (optimize) => `Compilación exitosa · ${optimize ? "con" : "sin"} optimización`,
  compileError: (diag) => `Error ${ERROR_NAMES[diag.phase] || diag.phase} · línea ${diag.line}, col. ${diag.column}`,
  runOk: (pos) => `Ejecución completada · ${formatPosition(pos)}`,
  runError: (count) => `Error de ejecución tras ${count} ${count === 1 ? "evento válido" : "eventos válidos"}`,
  requestFailed: "No se pudo procesar la solicitud",
  network: "No se pudo contactar con el servidor.",
  configFailed: "No se pudo cargar la configuración del servidor. Recarga la página.",
  notReached: "Esta fase no se alcanzó.",
  compileFirst: "Compila para ver esta fase.",
  runFirst: "Ejecuta el programa para ver la traza.",
};

const $ = (id) => document.getElementById(id);
const dom = {
  source: $("source"), gutter: $("gutter"), lineMark: $("line-mark"), charCount: $("char-count"),
  optimize: $("optimize"), examples: $("examples"), status: $("status"),
  alert: $("alert"), alertTitle: $("alert-title"), alertCode: $("alert-code"), alertMessage: $("alert-message"),
  compile: $("btn-compile"), run: $("btn-run"), pause: $("btn-pause"), step: $("btn-step"), restart: $("btn-restart"),
  speed: $("speed"), grid: $("grid"), badge: $("play-badge"),
  posStart: $("pos-start"), posNow: $("pos-now"), posFinal: $("pos-final"), currentEvent: $("current-event"),
  tablist: $("tablist"),
  panels: {
    tokens: $("panel-tokens"), ast: $("panel-ast"), symbols: $("panel-symbols"), tac: $("panel-tac"),
    assembly: $("panel-assembly"), trace: $("panel-trace"), diagnostics: $("panel-diagnostics"),
  },
};

const state = {
  config: null,
  version: 0,          // Changes whenever the source or the optimize option changes.
  controller: null,    // In-flight request, aborted when results become stale.
  busy: null,          // "compile" | "run" | null
  hadResults: false,
  compilation: null,   // Last compile payload for the current version.
  optimizeUsed: true,
  execution: null,
  index: 0,            // Number of execution events already shown.
  playing: false,
  timer: null,
};

// --- Helpers ----------------------------------------------------------------------------------

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function formatPosition(pos) {
  return `(${pos.x},${pos.y}) ${pos.orientation}`;
}

// Keep integers beyond JavaScript's safe range as their exact digits (display only).
function parseJson(text) {
  return JSON.parse(text, (key, value, context) =>
    typeof value === "number" && !Number.isSafeInteger(value) && context && context.source
      ? context.source
      : value);
}

function setStatus(text, tone = "") {
  dom.status.textContent = text;
  dom.status.dataset.tone = tone;
}

function setBadge(text, tone = "") {
  dom.badge.textContent = text;
  dom.badge.dataset.tone = tone;
}

function showAlert(tone, title, code, message) {
  dom.alert.hidden = false;
  dom.alert.dataset.tone = tone;
  dom.alertTitle.textContent = title;
  dom.alertCode.textContent = code;
  dom.alertMessage.textContent = message;
}

function hideAlert() {
  dom.alert.hidden = true;
}

function diagnosticWhere(diag) {
  return `línea ${diag.line}, columna ${diag.column}`;
}

// --- Editor -------------------------------------------------------------------------------------

function editorLineHeight() {
  return parseFloat(getComputedStyle(dom.source).lineHeight) || 26;
}

function updateGutter() {
  const count = dom.source.value.split("\n").length;
  dom.gutter.textContent = Array.from({ length: count }, (_, i) => i + 1).join("\n");
  dom.gutter.scrollTop = dom.source.scrollTop;
}

function updateCharCount() {
  const max = state.config ? state.config.max_source_chars : 0;
  const length = dom.source.value.length;
  dom.charCount.textContent = `${length} / ${max}`;
  dom.charCount.style.color = max && length > max ? "var(--err)" : "";
}

function markLine(line, tone) {
  state.markedLine = line ? { line, tone } : null;
  positionLineMark();
}

function positionLineMark() {
  const mark = state.markedLine;
  if (!mark) {
    dom.lineMark.hidden = true;
    return;
  }
  dom.lineMark.hidden = false;
  dom.lineMark.dataset.tone = mark.tone || "";
  dom.lineMark.style.top = `${(mark.line - 1) * editorLineHeight() - dom.source.scrollTop}px`;
}

function focusSource(line, column) {
  const lines = dom.source.value.split("\n");
  let offset = 0;
  for (let i = 0; i < Math.min(line - 1, lines.length); i += 1) offset += lines[i].length + 1;
  offset += Math.max(0, column - 1);
  dom.source.focus();
  dom.source.setSelectionRange(offset, offset);
}

// --- Grid -------------------------------------------------------------------------------------

function buildGrid() {
  const { width, height } = state.config.grid;
  dom.grid.style.setProperty("--cols", width);
  dom.grid.replaceChildren(el("div", { class: "axis" }));
  for (let x = 0; x < width; x += 1) dom.grid.append(el("div", { class: "axis", text: x }));
  state.cells = [];
  for (let y = 0; y < height; y += 1) {
    dom.grid.append(el("div", { class: "axis", text: y }));
    const row = [];
    for (let x = 0; x < width; x += 1) {
      const cell = el("div", { class: "cell" });
      dom.grid.append(cell);
      row.push(cell);
    }
    state.cells.push(row);
  }
  const size = `${width}×${height}`;
  $("grid-size").textContent = size;
  $("sim-size").textContent = size;
}

function robotIcon(orientation) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "robot-icon");
  svg.setAttribute("aria-hidden", "true");
  svg.style.transform = `rotate(${ORIENTATION_DEGREES[orientation] ?? 0}deg)`;
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", "M12 3l7 17-7-4-7 4z");
  path.setAttribute("fill", "#2563EB");
  path.setAttribute("stroke", "#FFFFFF");
  path.setAttribute("stroke-width", "1.5");
  path.setAttribute("stroke-linejoin", "round");
  svg.append(path);
  return svg;
}

// Draw the robot after `shown` events: positions come only from VM events.
function drawRobot(shown) {
  const start = state.execution ? state.execution.start : state.config.start;
  const events = state.execution ? state.execution.events.slice(0, shown) : [];
  const current = events.length ? events[events.length - 1] : start;
  const visited = new Set([start, ...events.slice(0, -1)].map((p) => `${p.x},${p.y}`));
  const startKey = `${start.x},${start.y}`;
  const currentKey = `${current.x},${current.y}`;

  state.cells.forEach((row, y) => row.forEach((cell, x) => {
    const key = `${x},${y}`;
    cell.className = "cell";
    cell.replaceChildren();
    if (key === currentKey) {
      cell.classList.add("robot");
      cell.append(robotIcon(current.orientation));
    } else if (key === startKey && events.length) {
      cell.classList.add("start-label");
    } else if (visited.has(key) && events.length) {
      cell.classList.add("trail");
    }
  }));

  dom.grid.setAttribute("aria-label",
    `Cuadrícula ${state.config.grid.width} por ${state.config.grid.height}. Robot en (${current.x},${current.y}) mirando al ${current.orientation}.`);
  dom.posStart.textContent = formatPosition(start);
  dom.posNow.textContent = formatPosition(current);
  dom.posFinal.textContent = state.execution ? formatPosition(state.execution.final) : "—";
}

// --- Tabs -------------------------------------------------------------------------------------

function tabs() {
  return Array.from(dom.tablist.querySelectorAll('[role="tab"]'));
}

function selectTab(name, focus = false) {
  for (const tab of tabs()) {
    const selected = tab.id === `tab-${name}`;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    document.getElementById(tab.getAttribute("aria-controls")).hidden = !selected;
    if (selected && focus) tab.focus();
  }
}

function setupTabs() {
  dom.tablist.addEventListener("click", (event) => {
    const tab = event.target.closest('[role="tab"]');
    if (tab) selectTab(tab.id.replace("tab-", ""));
  });
  dom.tablist.addEventListener("keydown", (event) => {
    const list = tabs();
    const index = list.findIndex((tab) => tab.getAttribute("aria-selected") === "true");
    const moves = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: list.length - 1 };
    if (!(event.key in moves)) return;
    event.preventDefault();
    const next = list[(moves[event.key] + list.length) % list.length];
    selectTab(next.id.replace("tab-", ""), true);
  });
}

// --- Phase rendering --------------------------------------------------------------------------

function empty(text) {
  return el("p", { class: "empty", text });
}

function table(headers, rows) {
  return el("table", { class: "data" },
    el("thead", {}, el("tr", {}, headers.map((h) => el("th", { scope: "col", text: h })))),
    el("tbody", {}, rows));
}

function renderTokens(result) {
  const panel = dom.panels.tokens;
  if (!result) return panel.replaceChildren(empty(MESSAGES.compileFirst));
  if (!result.tokens.length) return panel.replaceChildren(empty(MESSAGES.notReached));
  panel.replaceChildren(
    el("p", { class: "empty", text: `${result.tokens.length} tokens (incluye EOF)` }),
    table(["Tipo", "Lexema", "Línea", "Columna"], result.tokens.map((t) => el("tr", {},
      el("td", { class: "type", text: t.type }), el("td", { text: t.lexeme }),
      el("td", { text: t.line }), el("td", { text: t.column })))));
}

const AST_HIDDEN_KEYS = new Set(["node", "location", "name_location"]);

function astLabel(node) {
  const parts = [el("span", { class: "node", text: node.node })];
  const details = [];
  if ("name" in node) details.push(String(node.name));
  if ("declared_type" in node) details.push(`: ${node.declared_type}`);
  if ("operator" in node) details.push(String(node.operator));
  if ("value" in node) details.push(String(node.value));
  if (node.resolved_slot) details.push(`→ ${node.resolved_slot}`);
  for (const [key, value] of Object.entries(node)) {
    const shown = ["name", "declared_type", "operator", "value", "resolved_slot"].includes(key);
    if (!shown && !AST_HIDDEN_KEYS.has(key) && (value === null || typeof value !== "object")) {
      details.push(`${key}=${value}`);
    }
  }
  if (details.length) parts.push(" ", details.join(" "));
  if (node.location) parts.push(" ", el("span", { class: "loc", text: `${node.location.line}:${node.location.column}` }));
  return parts;
}

function astChildren(node) {
  const children = [];
  for (const [key, value] of Object.entries(node)) {
    if (AST_HIDDEN_KEYS.has(key)) continue;
    if (Array.isArray(value)) children.push(...value.filter((v) => v && v.node));
    else if (value && typeof value === "object" && value.node) children.push(value);
  }
  return children;
}

function astItem(node) {
  const children = astChildren(node);
  if (!children.length) return el("li", { class: "leaf" }, astLabel(node));
  return el("li", {}, el("details", { open: true },
    el("summary", {}, astLabel(node)),
    el("ul", {}, children.map(astItem))));
}

function renderAst(result) {
  const panel = dom.panels.ast;
  if (!result) return panel.replaceChildren(empty(MESSAGES.compileFirst));
  if (!result.ast) return panel.replaceChildren(empty(MESSAGES.notReached));
  panel.replaceChildren(el("ul", { class: "ast" }, astItem(result.ast)));
}

function renderSymbols(result) {
  const panel = dom.panels.symbols;
  if (!result) return panel.replaceChildren(empty(MESSAGES.compileFirst));
  if (!result.symbols.length) return panel.replaceChildren(empty(result.ok ? "No hay variables declaradas." : MESSAGES.notReached));
  const seen = new Set();
  const rows = result.symbols.map((s) => {
    const shadows = seen.has(s.name);
    seen.add(s.name);
    return el("tr", { class: shadows ? "shadow" : null },
      el("td", { text: s.name }), el("td", { text: s.type }), el("td", { text: s.scope_id }),
      el("td", { class: "type", text: s.slot }), el("td", { text: `${s.decl_line}:${s.decl_col}` }));
  });
  const shadowed = result.symbols.length !== seen.size;
  panel.replaceChildren(
    table(["Nombre", "Tipo", "Ámbito", "Slot", "Declaración"], rows),
    shadowed ? el("p", { class: "note", text: "Las filas resaltadas sombrean a una variable externa con el mismo nombre; usan otro slot." }) : null);
}

function codeList(items, classFor, start = 1) {
  return el("ol", { class: "code-list", start }, items.map((text, i) => el("li", { class: classFor(i), text })));
}

function renderTac(result) {
  const panel = dom.panels.tac;
  if (!result) return panel.replaceChildren(empty(MESSAGES.compileFirst));
  if (!result.tac_before.length) return panel.replaceChildren(empty(MESSAGES.notReached));
  const changed = (i) => result.tac_before[i] !== result.tac_after[i];
  const anyChange = result.tac_before.some((_, i) => changed(i)) || result.tac_before.length !== result.tac_after.length;
  const note = !state.optimizeUsed
    ? "Optimización desactivada: el TAC queda sin cambios."
    : anyChange ? "Resaltadas: cuádruplas cambiadas por el plegado de constantes." : "El plegado de constantes no cambió ninguna cuádrupla.";
  panel.replaceChildren(
    el("div", { class: "tac-columns" },
      el("div", {}, el("h3", { text: "Antes de optimizar" }), codeList(result.tac_before, (i) => (changed(i) ? "changed-before" : null))),
      el("div", {}, el("h3", { text: "Después" }), codeList(result.tac_after, (i) => (changed(i) ? "changed-after" : null)))),
    el("p", { class: "note", text: note }));
}

function renderAssembly(result, currentPc = null) {
  const panel = dom.panels.assembly;
  if (!result) return panel.replaceChildren(empty(MESSAGES.compileFirst));
  if (!result.assembly.length) return panel.replaceChildren(empty(MESSAGES.notReached));
  panel.replaceChildren(
    el("p", { class: "code-list-title", text: "PC base 0 · durante la reproducción se resalta la instrucción del evento" }),
    codeList(result.assembly, (i) => (i === currentPc ? "current" : null), 0));
}

function renderTrace() {
  const panel = dom.panels.trace;
  const execution = state.execution;
  if (!execution) {
    const reason = state.compilation && !state.compilation.ok ? "No hay ejecución: la compilación falló." : MESSAGES.runFirst;
    return panel.replaceChildren(empty(reason));
  }
  if (!execution.events.length && execution.ok) {
    return panel.replaceChildren(empty("La ejecución terminó sin movimientos ni giros."));
  }
  const rows = execution.events.map((e, i) => {
    const cls = i === state.index - 1 ? "current" : i >= state.index ? "pending" : null;
    return el("tr", { class: cls },
      el("td", { text: i + 1 }), el("td", { text: e.action }), el("td", { text: `(${e.x},${e.y})` }),
      el("td", { text: e.orientation }), el("td", { text: `línea ${e.source_line}, col. ${e.source_column}` }),
      el("td", { text: e.pc }));
  });
  const finished = state.index >= execution.events.length;
  if (!execution.ok && finished) {
    for (const diag of execution.diagnostics) {
      rows.push(el("tr", { class: "rejected" },
        el("td", { text: "✕" }), el("td", { text: diag.code }),
        el("td", { colspan: 4, text: `${diagnosticWhere(diag)} · ${diag.message}` })));
    }
  }
  panel.replaceChildren(table(["#", "Acción", "Posición", "Orientación", "Fuente", "PC"], rows));
}

function diagnosticButton(diag, tone) {
  return el("button", { type: "button", class: "diag", "data-tone": tone, onclick: () => focusSource(diag.line, diag.column) },
    el("div", { text: `fase: ${diag.phase} · código: ${diag.code}` }),
    el("div", { text: `posición: ${diagnosticWhere(diag)}` }),
    el("div", { class: "msg", text: diag.message }));
}

function renderDiagnostics() {
  const panel = dom.panels.diagnostics;
  const result = state.compilation;
  if (!result) return panel.replaceChildren(empty(MESSAGES.compileFirst));
  const group = (title, diags, tone, fallback) => el("div", { class: "diag-group" },
    el("h3", { text: title }),
    diags.length ? diags.map((d) => diagnosticButton(d, tone)) : el("div", { class: fallback.cls, text: fallback.text }));
  const execution = state.execution;
  const executionFallback = execution
    ? { cls: "diag-ok", text: "Sin diagnósticos" }
    : { cls: "empty", text: result.ok ? "Sin ejecutar." : "No se ejecutó: la compilación falló." };
  panel.replaceChildren(
    group("Compilación", result.diagnostics, "err", { cls: "diag-ok", text: "Sin diagnósticos" }),
    group("Ejecución", execution ? execution.diagnostics : [], "warn", executionFallback));
}

function renderPhases() {
  const result = state.compilation;
  renderTokens(result);
  renderAst(result);
  renderSymbols(result);
  renderTac(result);
  renderAssembly(result, currentEvent() ? currentEvent().pc : null);
  renderTrace();
  renderDiagnostics();
}

// --- Playback ---------------------------------------------------------------------------------

function currentEvent() {
  return state.execution && state.index > 0 ? state.execution.events[state.index - 1] : null;
}

function stopTimer() {
  if (state.timer !== null) clearTimeout(state.timer);
  state.timer = null;
}

function scheduleNext() {
  stopTimer();
  state.timer = setTimeout(() => {
    state.timer = null;
    advance();
    if (state.playing) scheduleNext();
  }, PLAYBACK_DELAY_MS[dom.speed.value] ?? PLAYBACK_DELAY_MS.normal);
}

function showFrame() {
  const execution = state.execution;
  const total = execution.events.length;
  const event = currentEvent();
  drawRobot(state.index);
  renderTrace();
  renderAssembly(state.compilation, event ? event.pc : null);

  if (state.index >= total) return finishPlayback();
  markLine(event ? event.source_line : null, "");
  dom.currentEvent.replaceChildren(...(event
    ? ["Evento actual: ", el("strong", { text: event.action }), ` · línea ${event.source_line}, columna ${event.source_column} · `,
       el("code", { text: sourceLine(event.source_line).trim() })]
    : ["Robot en el estado inicial."]));
  setBadge(`${state.playing ? "Reproduciendo" : "En pausa"} · evento ${state.index} de ${total}`, state.playing ? "busy" : "");
  updateButtons();
}

function sourceLine(line) {
  return dom.source.value.split("\n")[line - 1] || "";
}

function advance() {
  if (!state.execution || state.index >= state.execution.events.length) return;
  state.index += 1;
  showFrame();
}

function startPlayback() {
  state.index = 0;
  state.playing = true;
  hideAlert();
  showFrame();
  if (state.playing) scheduleNext();
}

function finishPlayback() {
  stopTimer();
  state.playing = false;
  const execution = state.execution;
  const last = currentEvent();
  dom.currentEvent.textContent = last
    ? `Último evento: ${last.action} · línea ${last.source_line}, columna ${last.source_column}`
    : "No hubo movimientos ni giros.";
  if (execution.ok) {
    markLine(null);
    setBadge("Completada", "ok");
    setStatus(MESSAGES.runOk(execution.final), "ok");
  } else {
    const diag = execution.diagnostics[0];
    markLine(diag ? diag.line : null, "warn");
    setBadge("Error de ejecución", "warn");
    setStatus(MESSAGES.runError(execution.events.length), "warn");
    if (diag) showAlert("warn", "Error de ejecución · la compilación fue correcta", `${diag.code} · ${diagnosticWhere(diag)}`, diag.message);
  }
  renderDiagnostics();
  updateButtons();
}

function cancelPlayback() {
  stopTimer();
  state.playing = false;
  state.index = 0;
}

// --- Requests ---------------------------------------------------------------------------------

function updateButtons() {
  const busy = state.busy !== null;
  const ready = state.config !== null;
  dom.compile.disabled = busy || !ready;
  dom.run.disabled = busy || !ready || !state.compilation?.ok;
  dom.compile.textContent = state.busy === "compile" ? MESSAGES.compiling : "Compilar";
  dom.run.textContent = state.busy === "run" ? MESSAGES.running : "Ejecutar";

  const execution = state.execution;
  const total = execution ? execution.events.length : 0;
  const midway = execution !== null && state.index < total;
  dom.pause.disabled = busy || !midway;
  dom.pause.textContent = midway && !state.playing ? "Reanudar" : "Pausar";
  dom.step.disabled = busy || !midway || state.playing;
  dom.restart.disabled = busy || execution === null;
}

function clearResults() {
  cancelPlayback();
  state.compilation = null;
  state.execution = null;
  hideAlert();
  markLine(null);
  dom.currentEvent.textContent = "";
  setBadge("Sin ejecutar");
  if (state.config) drawRobot(0);
  renderPhases();
}

function invalidate() {
  state.version += 1;
  if (state.controller) state.controller.abort();
  state.controller = null;
  state.busy = null;
  clearResults();
  setStatus(state.hadResults ? MESSAGES.invalidated : MESSAGES.notCompiled);
  updateButtons();
}

async function submit(endpoint) {
  const version = state.version;
  const optimize = dom.optimize.checked;
  const controller = new AbortController();
  if (state.controller) state.controller.abort();
  state.controller = controller;
  state.busy = endpoint;
  cancelPlayback();
  setStatus(endpoint === "run" ? MESSAGES.running : MESSAGES.compiling, "busy");
  updateButtons();

  try {
    const response = await fetch(`${API_PREFIX}/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: dom.source.value, optimize }),
      signal: controller.signal,
    });
    const text = await response.text();
    if (version !== state.version) return; // Stale: the code or option changed meanwhile.
    let body = null;
    try { body = parseJson(text); } catch { body = null; }
    if (!response.ok || body === null) return showRequestFailure(body);
    showResult(body, optimize, endpoint);
  } catch (error) {
    if (error.name === "AbortError" || version !== state.version) return;
    showRequestFailure(null, MESSAGES.network);
  } finally {
    if (state.controller === controller) {
      state.controller = null;
      state.busy = null;
      updateButtons();
    }
  }
}

function showRequestFailure(body, fallback) {
  let detail = fallback || (body && body.message) || "";
  if (body && Array.isArray(body.errors) && body.errors.length) detail = body.errors[0].message;
  if (state.execution) showFrame();
  setBadge(MESSAGES.requestFailed, "err");
  setStatus(detail ? `${MESSAGES.requestFailed}: ${detail}` : MESSAGES.requestFailed, "err");
}

function showResult(body, optimize, endpoint) {
  state.hadResults = true;
  state.optimizeUsed = optimize;
  state.compilation = body;
  state.execution = endpoint === "run" ? body.execution : null;
  state.index = 0;
  hideAlert();
  markLine(null);
  drawRobot(0);
  renderPhases();

  if (!body.ok) {
    const diag = body.diagnostics[0];
    setStatus(diag ? MESSAGES.compileError(diag) : "Error de compilación", "err");
    setBadge("Sin ejecutar");
    dom.currentEvent.textContent = "El robot no se mueve: la compilación falló.";
    if (diag) {
      showAlert("err", `Error de compilación · fase ${PHASE_NAMES[diag.phase] || diag.phase}`, `${diag.code} · ${diagnosticWhere(diag)}`, diag.message);
      markLine(diag.line, "err");
    }
    selectTab("diagnostics");
    return;
  }
  if (endpoint === "compile") {
    setStatus(MESSAGES.compileOk(optimize), "ok");
    setBadge("Listo para ejecutar");
    dom.currentEvent.textContent = "Compilar no mueve el robot.";
    return;
  }
  setStatus(MESSAGES.compileOk(optimize), "ok");
  selectTab("trace");
  startPlayback();
}

// --- Startup ----------------------------------------------------------------------------------

async function getJson(path) {
  const response = await fetch(`${API_PREFIX}/${path}`);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

function loadExamples(data) {
  const options = data.examples.map((ex) => el("option", { value: ex.id, text: ex.title }));
  dom.examples.replaceChildren(el("option", { value: "", text: "Elegir…" }), ...options);
  state.examples = new Map(data.examples.map((ex) => [ex.id, ex.source]));
  if (state.examples.has(data.default)) {
    dom.examples.value = data.default;
    setSource(state.examples.get(data.default));
  }
}

function setSource(text) {
  dom.source.value = text;
  updateGutter();
  updateCharCount();
}

function bindEvents() {
  dom.source.addEventListener("input", () => {
    updateGutter();
    updateCharCount();
    dom.examples.value = "";
    invalidate();
  });
  dom.source.addEventListener("scroll", () => {
    dom.gutter.scrollTop = dom.source.scrollTop;
    positionLineMark();
  });
  dom.optimize.addEventListener("change", invalidate);
  dom.examples.addEventListener("change", () => {
    if (!dom.examples.value) return;
    setSource(state.examples.get(dom.examples.value) || "");
    invalidate();
  });
  dom.compile.addEventListener("click", () => submit("compile"));
  dom.run.addEventListener("click", () => submit("run"));
  dom.pause.addEventListener("click", () => {
    state.playing = !state.playing;
    if (state.playing) scheduleNext(); else stopTimer();
    showFrame();
  });
  dom.step.addEventListener("click", advance);
  dom.restart.addEventListener("click", () => {
    hideAlert();
    setStatus(MESSAGES.compileOk(state.optimizeUsed), "ok");
    startPlayback();
  });
  dom.speed.addEventListener("change", () => { if (state.playing) scheduleNext(); });
  window.addEventListener("resize", positionLineMark);
}

async function init() {
  setupTabs();
  bindEvents();
  updateGutter();
  setStatus(MESSAGES.notCompiled);
  renderPhases();
  updateButtons();
  try {
    const [config, examples] = await Promise.all([getJson("config"), getJson("examples")]);
    state.config = config;
    buildGrid();
    drawRobot(0);
    loadExamples(examples);
    updateCharCount();
    updateButtons();
  } catch {
    setStatus(MESSAGES.configFailed, "err");
  }
}

init();
