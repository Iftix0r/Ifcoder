/* Kod iloni: devorga urilib o'lmaydi, faqat noto'g'ri so'z jonni oladi. Keyingi so'zni faqat server biladi. */
(() => {
  const { $, config, sound } = Kit;
  const canvas = $("snake");
  const context = canvas.getContext("2d");
  const COLS = 14;
  const ROWS = 10;
  const STEP_MS = 210;
  const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
  const COLORS = ["#6366f1", "#ec4899", "#f59e0b", "#06b6d4", "#8b5cf6", "#10b981", "#ef4444"];

  let cell = 0;
  let width = 0;
  let height = 0;
  let playing = false;
  let waiting = false;
  let snake = [];
  let direction = [1, 0];
  let turn = null;
  let grow = 0;
  let tiles = [];
  let lineIndex = 0;
  let built = [];
  let eaten = [];
  let lives = config.lives;
  let acc = 0;
  let last = performance.now();
  let shake = 0;

  function resize() {
    const ratio = devicePixelRatio || 1;
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    cell = width / COLS;
  }

  function drawLives() {
    $("lives").setAttribute("aria-label", `${lives} ta jon`);
    $("lives").replaceChildren(
      ...Array.from({ length: config.lives }, (_, index) => {
        const heart = document.createElement("span");
        heart.className = index < lives ? "heart-on" : "heart-off";
        heart.append($("heart-template").content.cloneNode(true));
        return heart;
      }),
    );
  }

  function showLine() {
    const line = config.lines[lineIndex];
    $("snake-goal").textContent = `${lineIndex + 1}/${config.lines.length}: ${line.goal}`;
    const words = built.map((text) => {
      const word = document.createElement("span");
      word.className = "snake-word";
      word.textContent = text;
      return word;
    });
    const slots = Array.from({ length: line.size - built.length }, () => {
      const slot = document.createElement("span");
      slot.className = "snake-slot";
      return slot;
    });
    $("built").replaceChildren(...words, ...slots);
  }

  const span = (text) => Math.max(1, Math.ceil((text.length * 0.62 + 0.5) * (Math.max(cell * 0.46, 11) / cell)));

  function free(x, y, size) {
    for (const tile of tiles) {
      if (tile.gone) continue;
      if (Math.abs(tile.y - y) <= 1 && x < tile.x + tile.size + 1 && tile.x < x + size + 1) return false;
    }
    return !snake.some(([sx, sy]) => sy === y && sx >= x - 1 && sx <= x + size);
  }

  function place(tile) {
    for (let tries = 0; tries < 200; tries++) {
      const x = Math.floor(Math.random() * (COLS - tile.size));
      const y = Math.floor(Math.random() * ROWS);
      if (free(x, y, tile.size)) {
        tile.x = x;
        tile.y = y;
        return;
      }
    }
  }

  function startLine() {
    built = [];
    tiles = [];
    config.lines[lineIndex].tiles.forEach((text, id) => {
      const tile = { id, text, size: span(text), color: COLORS[id % COLORS.length], x: -9, y: -9 };
      place(tile);
      tiles.push(tile);
    });
    showLine();
  }

  function restart() {
    snake = [[3, 5], [2, 5], [1, 5]];
    direction = [1, 0];
    turn = null;
    grow = 0;
    lineIndex = 0;
    eaten = [];
    lives = config.lives;
    waiting = false;
    drawLives();
    startLine();
    $("snake-overlay").hidden = true;
    Kit.status("");
    playing = true;
    canvas.focus();
  }

  function over(title, text) {
    playing = false;
    $("snake-title").textContent = title;
    $("snake-text").textContent = text;
    $("snake-go").lastChild.textContent = "Qaytadan";
    $("snake-overlay").hidden = false;
  }

  async function eat(tile) {
    waiting = true;
    const line = lineIndex;
    eaten.push([line, tile.id]);
    const data = await Kit.post({ eaten });
    waiting = false;
    if (data.failed) {
      eaten.pop();
      return Kit.status(data.message);
    }
    lives = data.lives;
    drawLives();
    if (data.right) {
      tile.gone = true;
      grow += 2;
      sound.take();
    } else {
      place(tile);
      shake = 1;
      sound.bad();
    }
    if (data.finished) {
      Kit.saveProgress(data);
      if (data.ok) {
        playing = false;
        return Kit.win(data, lives < config.lives ? `${config.lives - lives} ta xato bilan.` : "Birorta ham xatosiz!", restart);
      }
      return over(data.message, "So'zlar tartibini eslab qoling va yana urinib ko'ring.");
    }
    if (data.line !== lineIndex) {
      lineIndex = data.line;
      sound.good();
      startLine();
    } else {
      built = data.built;
      showLine();
    }
  }

  function step() {
    if (turn) {
      direction = turn;
      turn = null;
    }
    const [hx, hy] = snake[0];
    const head = [(hx + direction[0] + COLS) % COLS, (hy + direction[1] + ROWS) % ROWS];
    snake.unshift(head);
    if (grow > 0) grow -= 1;
    else snake.pop();
    if (waiting) return;
    const tile = tiles.find((item) => !item.gone && item.y === head[1] && head[0] >= item.x && head[0] < item.x + item.size);
    if (tile) eat(tile);
  }

  function draw() {
    context.fillStyle = "#061126";
    context.fillRect(0, 0, width, height);
    context.fillStyle = "rgb(255 255 255 / 0.05)";
    for (let y = 0; y < ROWS; y++) {
      for (let x = (y % 2); x < COLS; x += 2) context.fillRect(x * cell, y * cell, cell, cell);
    }
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = `700 ${Math.max(cell * 0.46, 11)}px ui-monospace, monospace`;
    for (const tile of tiles) {
      if (tile.gone) continue;
      context.fillStyle = tile.color;
      context.beginPath();
      context.roundRect(tile.x * cell + 2, tile.y * cell + 3, tile.size * cell - 4, cell - 6, 7);
      context.fill();
      context.fillStyle = "#fff";
      context.fillText(tile.text, (tile.x + tile.size / 2) * cell, (tile.y + 0.5) * cell + 1);
    }
    const color = getComputedStyle(canvas).getPropertyValue("--skin").trim() || "#10b981";
    snake.forEach(([x, y], index) => {
      context.globalAlpha = index ? Math.max(1 - index * 0.03, 0.55) : 1;
      context.fillStyle = color;
      context.beginPath();
      context.roundRect(x * cell + 2, y * cell + 2, cell - 4, cell - 4, cell * 0.32);
      context.fill();
    });
    context.globalAlpha = 1;
    if (snake.length) {
      const [x, y] = snake[0];
      const cx = (x + 0.5) * cell + direction[0] * cell * 0.14;
      const cy = (y + 0.5) * cell + direction[1] * cell * 0.14;
      const side = cell * 0.16;
      for (const sign of [-1, 1]) {
        const ex = cx + direction[1] * side * sign;
        const ey = cy + direction[0] * side * sign;
        context.fillStyle = "#fff";
        context.beginPath();
        context.arc(ex, ey, cell * 0.11, 0, Math.PI * 2);
        context.fill();
        context.fillStyle = "#0f172a";
        context.beginPath();
        context.arc(ex + direction[0] * 1.5, ey + direction[1] * 1.5, cell * 0.05, 0, Math.PI * 2);
        context.fill();
      }
    }
    if (shake > 0) {
      context.fillStyle = `rgb(244 63 94 / ${shake * 0.28})`;
      context.fillRect(0, 0, width, height);
    }
  }

  function frame(now) {
    const delta = now - last;
    last = now;
    shake = Math.max(shake - delta / 400, 0);
    if (playing) {
      acc += Math.min(delta, 100);
      while (acc >= STEP_MS) {
        acc -= STEP_MS;
        step();
      }
    }
    draw();
    requestAnimationFrame(frame);
  }

  function steer(name) {
    const next = DIRS[name];
    const base = turn ?? direction;
    if (next && !(next[0] === -base[0] && next[1] === -base[1])) turn = next;
  }

  addEventListener("keydown", (event) => {
    const keys = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", w: "up", s: "down", a: "left", d: "right" };
    if (!playing || !keys[event.key]) return;
    if (event.target.tagName === "TEXTAREA") return;
    event.preventDefault();
    steer(keys[event.key]);
  });
  document.querySelectorAll("[data-dir]").forEach((button) => {
    button.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      steer(button.dataset.dir);
    });
  });
  let swipe = null;
  canvas.addEventListener("pointerdown", (event) => {
    swipe = [event.clientX, event.clientY];
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!swipe) return;
    const dx = event.clientX - swipe[0];
    const dy = event.clientY - swipe[1];
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 24) return;
    steer(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : dy > 0 ? "down" : "up");
    swipe = [event.clientX, event.clientY];
  });
  addEventListener("pointerup", () => {
    swipe = null;
  });
  addEventListener("resize", resize);
  $("snake-go").addEventListener("click", restart);

  resize();
  drawLives();
  startLine();
  requestAnimationFrame(frame);
})();
