/* Robot o'yini: kod serverda bajariladi (apps/portal/engine.py), bu fayl faqat muharrir va animatsiya. */
(() => {
  const config = JSON.parse(document.getElementById("game-data").textContent);
  const CELL = 48;
  const SVG = "http://www.w3.org/2000/svg";
  const STEP_MS = 340;
  const INDENT = "    ";
  const INLINE_TOOL = /(_devor\(\)|yetib_keldi\(\))$|^elif $/;
  const KEYWORDS = "for|in|range|while|if|elif|else|def|return|not|and|or|True|False|break|continue|pass|print";
  const COMMANDS = "yur|chapga|ongga|ol|oldinda_devor|chapda_devor|ongda_devor|kristall_bor|yetib_keldi";
  const TOKENS = new RegExp(`(#.*$)|("[^"]*"?|'[^']*'?)|\\b(${KEYWORDS})\\b|\\b(${COMMANDS})\\b|\\b(\\d+)\\b`, "g");

  const $ = (id) => document.getElementById(id);
  const board = $("board");
  const code = $("code");
  const highlight = $("highlight");
  const gutter = $("gutter");
  const statusBox = $("status");
  const consoleBox = $("console");
  const consoleLines = $("console-lines");
  const runButton = $("run");
  const runLabel = $("run-label");
  const result = $("result");

  const store = {
    get: (key, fallback) => {
      try {
        return localStorage.getItem(key) ?? fallback;
      } catch {
        return fallback;
      }
    },
    set: (key, value) => {
      try {
        localStorage.setItem(key, value);
      } catch {
        /* private rejim */
      }
    },
  };

  let speed = Number(store.get("game-speed", "1")) || 1;
  let runId = 0; // Har yangi ishga tushirish eskisini bekor qiladi
  let running = false;
  let marks = { active: null, error: null };
  let robot = null;
  let angle = 0;

  /* --- Taxta --- */

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

  function placeRobot(x, y) {
    robot.style.transform = `translate(${x * CELL + CELL / 2}px, ${y * CELL + CELL / 2}px)`;
  }

  function turnRobot() {
    robot.firstChild.style.transform = `rotate(${angle}deg)`;
  }

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
    applySpeed();
  }

  function applySpeed() {
    board.firstChild?.style.setProperty("--step", `${Math.round(STEP_MS / speed)}ms`);
    document.querySelectorAll("[data-speed]").forEach((button) => {
      button.classList.toggle("is-active", Number(button.dataset.speed) === speed);
    });
  }

  /* --- Muharrir --- */

  const escapeHtml = (text) => text.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);

  function colorize(line) {
    let html = "";
    let last = 0;
    for (const match of line.matchAll(TOKENS)) {
      html += escapeHtml(line.slice(last, match.index));
      const kind = match[1] ? "com" : match[2] ? "str" : match[3] ? "key" : match[4] ? "cmd" : "num";
      html += `<span class="tok-${kind}">${escapeHtml(match[0])}</span>`;
      last = match.index + match[0].length;
    }
    return html + escapeHtml(line.slice(last));
  }

  function renderCode() {
    const lines = code.value.split("\n");
    highlight.innerHTML = lines
      .map((line, index) => {
        const number = index + 1;
        const state = number === marks.error ? " is-error" : number === marks.active ? " is-active" : "";
        return `<span class="code-line${state}">${colorize(line) || " "}</span>`;
      })
      .join("");
    gutter.innerHTML = lines.map((_, index) => `<div>${index + 1}</div>`).join("");
    syncScroll();
  }

  function syncScroll() {
    highlight.scrollTop = code.scrollTop;
    highlight.scrollLeft = code.scrollLeft;
    gutter.scrollTop = code.scrollTop;
  }

  function mark(active, error = null) {
    marks = { active, error };
    renderCode();
  }

  function insert(text) {
    code.focus();
    // execCommand brauzerning Ctrl+Z tarixini saqlaydi
    if (!document.execCommand("insertText", false, text)) {
      code.setRangeText(text, code.selectionStart, code.selectionEnd, "end");
      code.dispatchEvent(new Event("input"));
    }
  }

  function currentLine() {
    const start = code.value.lastIndexOf("\n", code.selectionStart - 1) + 1;
    const found = code.value.indexOf("\n", code.selectionStart);
    const end = found === -1 ? code.value.length : found;
    return { start, end, text: code.value.slice(start, end) };
  }

  const indentOf = (text) => text.match(/^ */)[0];

  function insertTool(tool) {
    if (INLINE_TOOL.test(tool)) return insert(tool);
    const line = currentLine();
    const indent = indentOf(line.text);
    const after = tool.endsWith(":") ? `\n${indent}${INDENT}` : "";
    code.focus();
    if (line.text.trim()) {
      code.setSelectionRange(line.end, line.end);
      insert(`\n${indent}${tool}${after}`);
    } else {
      insert(tool + after);
    }
  }

  code.addEventListener("input", () => {
    marks = { active: null, error: null };
    renderCode();
  });
  code.addEventListener("scroll", syncScroll);
  code.addEventListener("keydown", (event) => {
    if (event.key === "Escape") return code.blur(); // Klaviatura bilan muharrirdan chiqish
    if (event.key === "Tab" && !event.shiftKey) {
      event.preventDefault();
      insert(INDENT);
    } else if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      const before = code.value.slice(currentLine().start, code.selectionStart);
      insert(`\n${indentOf(before)}${before.trimEnd().endsWith(":") ? INDENT : ""}`);
    } else if (event.key === "Enter") {
      event.preventDefault();
      run();
    } else if (event.key === "Backspace" && code.selectionStart === code.selectionEnd) {
      const before = code.value.slice(currentLine().start, code.selectionStart);
      if (before.length >= 4 && before.length % 4 === 0 && !before.trim()) {
        event.preventDefault();
        code.setSelectionRange(code.selectionStart - 4, code.selectionStart);
        document.execCommand("delete") || code.setRangeText("");
      }
    }
  });
  $("tools").addEventListener("click", (event) => {
    const tool = event.target.closest("[data-tool]")?.dataset.tool;
    if (tool && !running) insertTool(tool);
  });

  /* --- Ishga tushirish --- */

  function showStatus(text, kind = "error") {
    statusBox.textContent = text;
    statusBox.className = `game-status is-${kind}`;
    statusBox.hidden = !text;
  }

  function setRunning(value) {
    running = value;
    code.readOnly = value;
    runLabel.textContent = value ? "To'xtatish" : "Ishga tushirish";
  }

  function reset(world = config.world) {
    runId += 1;
    setRunning(false);
    drawWorld(world);
    mark(null);
    showStatus("");
    consoleLines.replaceChildren();
    consoleBox.hidden = true;
    if ($("map-label")) $("map-label").textContent = "1-xarita";
  }

  const wait = (ms) => new Promise((done) => setTimeout(done, ms));

  function play(event) {
    if (event.a === "move") placeRobot(event.x, event.y);
    if (event.a === "turn") {
      angle += event.side * 90;
      turnRobot();
    }
    if (event.a === "take") board.querySelector(`[data-cell="${event.x},${event.y}"]`)?.classList.add("is-taken");
    if (event.a === "crash") robot.classList.add("is-crashed");
    if (event.a === "print") {
      const row = document.createElement("div");
      row.textContent = event.text;
      consoleLines.append(row);
      consoleBox.hidden = false;
    }
  }

  async function animate(events, id) {
    for (const event of events) {
      if (id !== runId) return false;
      mark(event.line);
      play(event);
      await wait(event.a === "print" ? 80 / speed : (STEP_MS + 40) / speed);
    }
    return id === runId;
  }

  function renderBestStars(count) {
    const stars = document.querySelectorAll("#best-stars [class^=star-]");
    stars.forEach((star, index) => {
      star.className = index < count ? "star-on" : "star-off";
    });
  }

  function showResult(data) {
    const holder = $("result-stars");
    holder.replaceChildren();
    for (let i = 1; i <= 3; i++) {
      const star = document.createElement("span");
      star.className = i <= data.stars ? "star-on" : "star-off";
      star.append($("star-template").content.cloneNode(true));
      holder.append(star);
    }
    const parts = [];
    if (config.maps > 1) parts.push(`Kod ${config.maps} ta xaritaning hammasida ishladi.`);
    if (data.gained > 0) parts.push(`+${data.gained} XP`);
    if (data.stars < 3) parts.push(`Siz ${data.statements} ta buyruq yozdingiz. 3 yulduz uchun ${data.par} ta yetadi.`);
    $("result-text").textContent = parts.join(" ");
    $("result-next").href = config.nextUrl;
    result.hidden = false;
    $("result-next").focus();
  }

  async function request() {
    const token = document.querySelector("meta[name=csrf-token]")?.content;
    const response = await fetch(config.runUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": token },
      body: JSON.stringify({ code: code.value }),
    });
    const data = await response.json();
    return { data, failed: !response.ok };
  }

  async function run() {
    if (running) return reset();
    reset();
    const id = runId;
    setRunning(true);
    let answer;
    try {
      answer = await request();
    } catch {
      setRunning(false);
      return showStatus("Serverdan javob kelmadi. Sahifani yangilab, qayta urinib ko'ring.");
    }
    if (id !== runId) return;
    const { data, failed } = answer;
    if (failed) {
      setRunning(false);
      return showStatus(data.message);
    }
    if (data.map_index > 0) {
      drawWorld(data.world);
      if ($("map-label")) $("map-label").textContent = `${data.map_index + 1}-xarita`;
    }
    const finished = await animate(data.events, id);
    if (!finished) return;
    setRunning(false);
    if (data.best_stars !== undefined) renderBestStars(data.best_stars);
    if (data.ok) {
      mark(null);
      showResult(data);
    } else {
      mark(null, data.line);
      showStatus(data.line ? `${data.line}-qator: ${data.message}` : data.message);
    }
  }

  runButton.addEventListener("click", run);
  $("reset").addEventListener("click", () => reset());
  $("result-again").addEventListener("click", () => {
    result.hidden = true;
    reset();
    code.focus();
  });
  result.addEventListener("keydown", (event) => {
    if (event.key === "Escape") $("result-again").click();
  });
  document.querySelectorAll("[data-speed]").forEach((button) => {
    button.addEventListener("click", () => {
      speed = Number(button.dataset.speed);
      store.set("game-speed", String(speed));
      applySpeed();
    });
  });

  code.value = config.code;
  drawWorld(config.world);
  renderCode();
})();
