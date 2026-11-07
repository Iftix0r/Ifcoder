/* Kod kosmosi: o'yin brauzerda, to'g'ri javobni esa faqat server biladi. */
(() => {
  const { $, config, sound } = Kit;
  const canvas = $("space");
  const context = canvas.getContext("2d");
  const LANES = 4;
  const stars = Array.from({ length: 70 }, () => ({ x: Math.random(), y: Math.random(), s: 0.3 + Math.random() }));

  let width = 0;
  let height = 0;
  let phase = "ready"; // ready | flying | waiting | review | over
  let pace = 30;
  let answers = [];
  let lives = config.lives;
  let score = 0;
  let combo = 1;
  let rocks = [];
  let shots = [];
  let sparks = [];
  let lane = 1;
  let shipX = 0;
  let flash = 0;
  let last = performance.now();
  let waveTime = 0;

  function resize() {
    const ratio = devicePixelRatio || 1;
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  const laneX = (index) => (width / LANES) * (index + 0.5);
  const shipY = () => height - 44;

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

  function showHud() {
    $("score").textContent = score;
    $("combo").textContent = combo > 1 ? `×${combo}` : "";
    $("wave").textContent = `${Math.min(answers.length + 1, config.questions.length)}-to'lqin / ${config.questions.length}`;
  }

  function startWave() {
    const question = config.questions[answers.length];
    $("space-code").innerHTML = question.code.split("\n").map(Kit.colorize).join("\n");
    $("space-why").hidden = true;
    rocks = question.options.map((text, index) => ({ index, text, y: 40 + Math.random() * 24, alive: true, spin: Math.random() * 6, state: "" }));
    waveTime = pace + question.code.split("\n").length * 3;
    shots = [];
    phase = "flying";
    showHud();
    canvas.focus();
  }

  function restart() {
    answers = [];
    lives = config.lives;
    score = 0;
    combo = 1;
    drawLives();
    $("space-overlay").hidden = true;
    startWave();
  }

  function burst(x, y, color) {
    for (let i = 0; i < 26; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 50 + Math.random() * 190;
      sparks.push({ x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life: 0.7, color });
    }
  }

  async function answer(index) {
    if (phase !== "flying") return;
    phase = "waiting";
    const data = await Kit.post({ answers: [...answers, index] });
    if (data.failed) {
      phase = "flying";
      return Kit.status(data.message);
    }
    answers.push(index);
    lives = data.lives;
    drawLives();
    const hit = rocks[index];
    const right = rocks[data.right];
    right.state = "right";
    if (data.correct) {
      score += 100 * combo;
      combo += 1;
      burst(laneX(index), hit.y, "#34d399");
      hit.alive = false;
      sound.take();
    } else {
      combo = 1;
      flash = 1;
      if (hit) hit.state = "wrong";
      sound.bad();
    }
    showHud();
    $("why-text").textContent = `${data.correct ? "To'g'ri!" : "Xato."} ${data.why}`;
    if (data.finished) {
      Kit.saveProgress(data);
      phase = "over";
      if (data.ok) {
        $("space-why").hidden = false;
        $("space-next").textContent = "Natija";
        $("space-next").onclick = () => {
          $("space-why").hidden = true;
          Kit.win(data, `${score} ball.`, () => showReady());
        };
      } else {
        $("space-why").hidden = false;
        $("space-next").textContent = "Qaytadan";
        $("space-next").onclick = restart;
      }
    } else {
      phase = "review";
      $("space-next").textContent = "Davom";
      $("space-next").onclick = startWave;
      $("space-why").hidden = false;
    }
    $("space-next").focus();
  }

  function fire() {
    if (phase !== "flying" || shots.length) return;
    shots.push({ x: laneX(lane), y: shipY() - 22, lane });
    sound.step();
  }

  function aim(index) {
    lane = Math.max(0, Math.min(LANES - 1, index));
  }

  function rock(item) {
    const x = laneX(item.index);
    const radius = Math.min(width / LANES / 2 - 6, 38);
    context.save();
    context.translate(x, item.y);
    context.beginPath();
    for (let i = 0; i < 9; i++) {
      const angle = (i / 9) * Math.PI * 2 + item.spin;
      const size = radius * (0.86 + 0.14 * Math.sin(i * 2.3 + item.index));
      context[i ? "lineTo" : "moveTo"](Math.cos(angle) * size, Math.sin(angle) * size);
    }
    context.closePath();
    context.fillStyle = item.state === "right" ? "#059669" : item.state === "wrong" ? "#be123c" : "#3f4470";
    context.strokeStyle = item.state === "right" ? "#6ee7b7" : item.state === "wrong" ? "#fda4af" : "#818cf8";
    context.lineWidth = 2;
    context.fill();
    context.stroke();
    context.fillStyle = "#fff";
    context.textAlign = "center";
    context.textBaseline = "middle";
    const size = item.text.length > 6 ? 11 : item.text.length > 3 ? 14 : 19;
    context.font = `700 ${size}px ui-monospace, monospace`;
    context.fillText(item.text, 0, 1, radius * 2 - 4);
    context.restore();
  }

  function ship() {
    context.save();
    context.translate(shipX, shipY());
    context.shadowColor = "#22d3ee";
    context.shadowBlur = 16;
    context.fillStyle = getComputedStyle(canvas).getPropertyValue("--skin").trim() || "#e0e7ff";
    context.beginPath();
    context.moveTo(0, -24);
    context.lineTo(17, 16);
    context.lineTo(0, 8);
    context.lineTo(-17, 16);
    context.closePath();
    context.fill();
    context.shadowBlur = 0;
    context.fillStyle = "#22d3ee";
    context.beginPath();
    context.arc(0, -6, 5, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = "#fb923c";
    context.beginPath();
    context.moveTo(-6, 13);
    context.lineTo(6, 13);
    context.lineTo(0, 22 + Math.random() * 8);
    context.fill();
    context.restore();
  }

  function frame(now) {
    const delta = Math.min((now - last) / 1000, 0.05);
    last = now;
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#050514";
    context.fillRect(0, 0, width, height);
    context.fillStyle = "#fff";
    for (const star of stars) {
      star.y = (star.y + delta * 0.05 * star.s) % 1;
      context.globalAlpha = 0.3 + star.s * 0.4;
      context.fillRect(star.x * width, star.y * height, star.s * 1.6, star.s * 1.6);
    }
    context.globalAlpha = 1;
    context.strokeStyle = "rgb(99 102 241 / 0.14)";
    for (let i = 1; i < LANES; i++) {
      context.beginPath();
      context.moveTo((width / LANES) * i, 0);
      context.lineTo((width / LANES) * i, height);
      context.stroke();
    }
    if (phase === "flying") {
      const speed = (shipY() - 20) / waveTime;
      for (const item of rocks) {
        item.y += speed * delta;
        item.spin += delta * 0.4;
      }
      if (rocks.some((item) => item.y > shipY() - 30)) answer(-1);
    }
    shipX += (laneX(lane) - shipX) * Math.min(delta * 14, 1);
    for (const shot of shots) {
      shot.y -= 760 * delta;
      context.fillStyle = "#22d3ee";
      context.fillRect(shot.x - 2, shot.y - 12, 4, 20);
      const target = rocks[shot.lane];
      if (target?.alive && shot.y <= target.y + 26) {
        shot.done = true;
        answer(shot.lane);
      } else if (shot.y < 0) {
        shot.done = true;
      }
    }
    shots = shots.filter((shot) => !shot.done);
    for (const item of rocks) if (item.alive) rock(item);
    for (const spark of sparks) {
      spark.life -= delta;
      spark.x += spark.vx * delta;
      spark.y += spark.vy * delta;
      context.globalAlpha = Math.max(spark.life / 0.7, 0);
      context.fillStyle = spark.color;
      context.fillRect(spark.x, spark.y, 3, 3);
    }
    context.globalAlpha = 1;
    sparks = sparks.filter((spark) => spark.life > 0);
    ship();
    if (flash > 0) {
      flash -= delta * 2.5;
      context.fillStyle = `rgb(244 63 94 / ${Math.max(flash, 0) * 0.3})`;
      context.fillRect(0, 0, width, height);
    }
    requestAnimationFrame(frame);
  }

  function showReady() {
    $("space-overlay").hidden = false;
    $("space-why").hidden = true;
    phase = "ready";
    rocks = [];
  }

  document.querySelectorAll("[data-pace]").forEach((button) => {
    const choose = () => {
      pace = Number(button.dataset.pace);
      document.querySelectorAll("[data-pace]").forEach((item) => item.classList.toggle("is-active", item === button));
    };
    button.addEventListener("click", choose);
    if (Number(button.dataset.pace) === pace) choose();
  });
  $("space-start").addEventListener("click", restart);
  canvas.addEventListener("pointerdown", (event) => {
    const box = canvas.getBoundingClientRect();
    aim(Math.floor(((event.clientX - box.left) / box.width) * LANES));
    fire();
  });
  addEventListener("keydown", (event) => {
    if (phase !== "flying") return;
    if (event.key === "ArrowLeft") aim(lane - 1);
    else if (event.key === "ArrowRight") aim(lane + 1);
    else if (event.key === " ") fire();
    else if ("1234".includes(event.key)) {
      aim(Number(event.key) - 1);
      fire();
    } else return;
    event.preventDefault();
  });
  addEventListener("resize", resize);

  resize();
  shipX = laneX(lane);
  $("space-code").textContent = "# Tayyormisiz?";
  drawLives();
  showHud();
  requestAnimationFrame(frame);
})();
