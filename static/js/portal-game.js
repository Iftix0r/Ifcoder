/* Robot yo'li va Xato ovchisi: kod serverda bajariladi (apps/portal/engine.py), bu yerda faqat animatsiya. */
(() => {
  const { $, config, sound } = Kit;
  const CELL = 48;
  const SVG = "http://www.w3.org/2000/svg";
  const STEP_MS = 340;
  const board = $("board");
  const runLabel = $("run-label");

  let runId = 0; // Har yangi ishga tushirish eskisini bekor qiladi
  let running = false;
  let robot = null;
  let angle = 0;
  const lines = [];

  const el = (name, attrs = {}, parent = null) => {
    const node = document.createElementNS(SVG, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (parent) parent.append(node);
    return node;
  };

  function drawCrystal(svg, x, y) {
    const cx = x * CELL + CELL / 2;
    const cy = y * CELL + CELL / 2;
    const group = el("g", { class: "crystal", "data-cell": `${x},${y}` }, svg);
    el("polygon", { points: `${cx},${cy - 14} ${cx + 11},${cy - 3} ${cx},${cy + 14} ${cx - 11},${cy - 3}`, fill: "#22d3ee" }, group);
    el("polygon", { points: `${cx},${cy - 14} ${cx + 11},${cy - 3} ${cx},${cy} ${cx - 11},${cy - 3}`, fill: "#a5f3fc" }, group);
  }

  function drawExit(svg, x, y) {
    const px = x * CELL;
    const py = y * CELL;
    el("rect", { x: px + 5, y: py + 5, width: CELL - 10, height: CELL - 10, rx: 8, fill: "#10b981", opacity: 0.18 }, svg);
    el("line", { x1: px + 17, y1: py + 10, x2: px + 17, y2: py + 38, stroke: "#059669", "stroke-width": 3, "stroke-linecap": "round" }, svg);
    el("polygon", { points: `${px + 18},${py + 10} ${px + 36},${py + 17} ${px + 18},${py + 24}`, fill: "#10b981" }, svg);
  }

  /* Tepadan ko'rinish, (0,0) atrofida chizilgan: yuqoriga qaragan */
  function drawRobot(svg) {
    const outer = el("g", { class: "robot" }, svg);
    const body = el("g", { class: "robot-body" }, outer);
    el("rect", { x: -19, y: -11, width: 6, height: 22, rx: 3, fill: "#312e81" }, body);
    el("rect", { x: 13, y: -11, width: 6, height: 22, rx: 3, fill: "#312e81" }, body);
    el("rect", { x: -14, y: -16, width: 28, height: 31, rx: 10, fill: "#6366f1" }, body);
    el("rect", { x: -10, y: -13, width: 20, height: 11, rx: 5, fill: "#0f172a" }, body);
    el("circle", { cx: -4.5, cy: -7.5, r: 2.6, fill: "#22d3ee" }, body);
    el("circle", { cx: 4.5, cy: -7.5, r: 2.6, fill: "#22d3ee" }, body);
    el("circle", { cx: 0, cy: 7, r: 3, fill: "#c7d2fe" }, body);
    return outer;
  }

  const placeRobot = (x, y) => {
    robot.style.transform = `translate(${x * CELL + CELL / 2}px, ${y * CELL + CELL / 2}px)`;
  };
  const turnRobot = () => {
    robot.firstChild.style.transform = `rotate(${angle}deg)`;
  };
  const applySpeed = (value) => {
    board.firstChild?.style.setProperty("--step", `${Math.round(STEP_MS / value)}ms`);
  };

  function drawWorld(world) {
    const svg = el("svg", { viewBox: `0 0 ${world.width * CELL} ${world.height * CELL}` });
    const walls = new Set(world.walls.map(([x, y]) => `${x},${y}`));
    for (let y = 0; y < world.height; y++) {
      for (let x = 0; x < world.width; x++) {
        const wall = walls.has(`${x},${y}`);
        el("rect", { x: x * CELL + 1, y: y * CELL + 1, width: CELL - 2, height: CELL - 2, rx: 7, class: wall ? "tile-wall" : "tile-floor" }, svg);
      }
    }
    if (world.exit) drawExit(svg, ...world.exit);
    for (const [x, y] of world.crystals) drawCrystal(svg, x, y);
    robot = drawRobot(svg);
    svg.style.setProperty("--step", "0ms");
    angle = world.robot.d * 90;
    placeRobot(world.robot.x, world.robot.y);
    turnRobot();
    board.replaceChildren(svg);
    applySpeed(speed());
  }

  const speed = Kit.speedControl(applySpeed);
  const editor = Kit.editor({ onRun: run, isBusy: () => running });

  function setRunning(value) {
    running = value;
    editor.readOnly = value || Kit.blockMode === true;
    runLabel.textContent = value ? "To'xtatish" : "Ishga tushirish";
  }

  function reset() {
    runId += 1;
    setRunning(false);
    drawWorld(config.world);
    editor.mark(null);
    Kit.status("");
    lines.length = 0;
    Kit.printLines([]);
    if ($("map-label")) $("map-label").textContent = "1-xarita";
  }

  function play(event) {
    if (event.a === "move") {
      placeRobot(event.x, event.y);
      sound.step();
    }
    if (event.a === "turn") {
      angle += event.side * 90;
      turnRobot();
    }
    if (event.a === "take") {
      board.querySelector(`[data-cell="${event.x},${event.y}"]`)?.classList.add("is-taken");
      sound.take();
    }
    if (event.a === "crash") {
      robot.classList.add("is-crashed");
      sound.bad();
    }
    if (event.a === "print") {
      lines.push(event.text);
      Kit.printLines(lines);
    }
  }

  async function animate(events, id) {
    for (const event of events) {
      if (id !== runId) return false;
      editor.mark(event.line);
      play(event);
      await Kit.wait((event.a === "print" ? 80 : STEP_MS + 40) / speed());
    }
    return id === runId;
  }

  function winText(data) {
    if (data.changes !== undefined) {
      return data.stars < 3 ? `${data.changes} ta qator o'zgardi. ${data.allowed} tasi yetardi.` : "Eng kam o'zgartirish bilan tuzatdingiz!";
    }
    const maps = config.maps > 1 ? `Kod ${config.maps} ta xaritaning hammasida ishladi.` : "";
    return [maps, Kit.statementsNote(data)].filter(Boolean).join(" ");
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
    if (data.map_index > 0) {
      drawWorld(data.world);
      if ($("map-label")) $("map-label").textContent = `${data.map_index + 1}-xarita`;
    }
    if (!(await animate(data.events, id))) return;
    setRunning(false);
    Kit.saveProgress(data);
    if (data.ok) {
      editor.mark(null);
      Kit.win(data, winText(data), () => {
        reset();
        $("code").focus();
      });
    } else {
      sound.bad();
      editor.mark(null, data.line);
      Kit.status(data.line ? `${data.line}-qator: ${data.message}` : data.message);
      Kit.failed(data);
    }
  }

  $("run").addEventListener("click", run);
  $("reset").addEventListener("click", reset);
  $("restore")?.addEventListener("click", () => {
    reset();
    editor.value = config.starter;
  });
  drawWorld(config.world);
  Kit.code = editor;
})();
