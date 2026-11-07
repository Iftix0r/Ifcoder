/* Kod rassomi: server qalam harakatlarini qaytaradi, bu yerda ular qog'ozga chiziladi. */
(() => {
  const { $, config, sound } = Kit;
  const SVG = "http://www.w3.org/2000/svg";
  const paper = $("paper");
  const runLabel = $("run-label");
  const svg = document.createElementNS(SVG, "svg");
  const ghost = document.createElementNS(SVG, "g");
  const ink = document.createElementNS(SVG, "g");
  const pen = document.createElementNS(SVG, "polygon");

  let runId = 0;
  let running = false;
  let position = config.start;
  let heading = 0;
  const lines = [];

  const line = (parent, x1, y1, x2, y2, attrs) => {
    const node = document.createElementNS(SVG, "line");
    for (const [key, value] of Object.entries({ x1, y1, x2, y2, "stroke-linecap": "round", ...attrs })) node.setAttribute(key, value);
    parent.append(node);
    return node;
  };

  function placePen() {
    pen.setAttribute("transform", `translate(${position[0]} ${position[1]}) rotate(${heading})`);
  }

  function clear() {
    ink.replaceChildren();
    position = config.start;
    heading = 0;
    placePen();
  }

  const speed = Kit.speedControl();
  const editor = Kit.editor({ onRun: run, isBusy: () => running });

  function setRunning(value) {
    running = value;
    editor.readOnly = value;
    runLabel.textContent = value ? "To'xtatish" : "Ishga tushirish";
  }

  function reset() {
    runId += 1;
    setRunning(false);
    clear();
    editor.mark(null);
    Kit.status("");
    lines.length = 0;
    Kit.printLines([]);
  }

  function stroke(event, ms, id) {
    const [x1, y1] = position;
    const node = event.draw ? line(ink, x1, y1, x1, y1, { stroke: event.color, "stroke-width": 3.5 }) : null;
    const began = performance.now();
    return new Promise((done) => {
      (function frame(now) {
        if (id !== runId) return done();
        const part = Math.min((now - began) / ms, 1);
        const x = x1 + (event.x - x1) * part;
        const y = y1 + (event.y - y1) * part;
        node?.setAttribute("x2", x);
        node?.setAttribute("y2", y);
        position = [x, y];
        placePen();
        if (part < 1) requestAnimationFrame(frame);
        else done();
      })(began);
    });
  }

  async function animate(events, id) {
    // Gul yoki spiralda yuzlab harakat bor: umumiy vaqt cheklanadi
    const ms = Math.max(30, Math.min(260, 7000 / Math.max(events.length, 1))) / speed();
    for (const event of events) {
      if (id !== runId) return false;
      editor.mark(event.line);
      if (event.a === "go") {
        await stroke(event, ms, id);
        if (event.draw) sound.step();
      } else if (event.a === "turn") {
        heading = event.h;
        placePen();
        await Kit.wait(ms / 3);
      } else if (event.a === "print") {
        lines.push(event.text);
        Kit.printLines(lines);
      }
    }
    return id === runId;
  }

  async function run() {
    if (running) return reset();
    reset();
    const id = runId;
    setRunning(true);
    const data = await Kit.post({ code: editor.value });
    if (id !== runId) return;
    if (data.failed) {
      setRunning(false);
      return Kit.status(data.message);
    }
    if (!(await animate(data.events, id))) return;
    setRunning(false);
    Kit.saveProgress(data);
    if (data.ok) {
      editor.mark(null);
      Kit.win(data, Kit.statementsNote(data), () => {
        reset();
        $("code").focus();
      });
    } else {
      sound.bad();
      editor.mark(null, data.line);
      Kit.status(data.line ? `${data.line}-qator: ${data.message}` : data.message);
    }
  }

  svg.setAttribute("viewBox", `0 0 ${config.size} ${config.size}`);
  for (const [x1, y1, x2, y2] of config.target) {
    line(ghost, x1, y1, x2, y2, { stroke: "#cbd5e1", "stroke-width": 7 });
  }
  for (const [x1, y1, x2, y2, color] of config.target) {
    line(ghost, x1, y1, x2, y2, { stroke: color, "stroke-width": 2, "stroke-dasharray": "2 7", opacity: 0.75 });
  }
  pen.setAttribute("points", "0,-11 7,7 0,3 -7,7");
  pen.setAttribute("fill", "#6366f1");
  pen.setAttribute("stroke", "#fff");
  pen.setAttribute("stroke-width", "1.5");
  svg.append(ghost, ink, pen);
  paper.append(svg);
  placePen();

  $("run").addEventListener("click", run);
  $("reset").addEventListener("click", reset);
})();
