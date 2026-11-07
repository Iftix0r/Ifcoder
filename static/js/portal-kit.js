/* O'yinlar uchun umumiy asboblar: muharrir, ovoz, konfetti, natija oynasi. Baholash doim serverda. */
window.Kit = (() => {
  const $ = (id) => document.getElementById(id);
  const config = JSON.parse($("game-data").textContent);
  const INDENT = "    ";
  const INLINE_TOOL = /(_devor\(\)|yetib_keldi\(\)|% 2 == 0)$|^elif $/;
  const KEYWORDS = "for|in|range|while|if|elif|else|def|return|not|and|or|True|False|break|continue|pass|print";
  const COMMANDS =
    "yur|chapga|ongga|ol|oldinda_devor|chapda_devor|ongda_devor|kristall_bor|yetib_keldi|oldinga|orqaga|rang|qalam_ol|qalam_qoy|mashina";
  const TOKENS = new RegExp(`(#.*$)|("[^"]*"?|'[^']*'?)|\\b(${KEYWORDS})\\b|\\b(${COMMANDS})\\b|\\b(\\d+)\\b`, "g");

  const store = {
    get(key, fallback) {
      try {
        return localStorage.getItem(key) ?? fallback;
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, value);
      } catch {
        /* private rejim */
      }
    },
  };

  /* --- Ovoz: fayl yuklanmaydi, tovush brauzerda yasaladi --- */

  let audio = null;
  let muted = store.get("game-sound", "on") === "off";

  function tone(frequency, ms, delay = 0, type = "sine", volume = 0.05) {
    if (muted) return;
    try {
      audio ??= new AudioContext();
      const start = audio.currentTime + delay / 1000;
      const oscillator = audio.createOscillator();
      const gain = audio.createGain();
      oscillator.type = type;
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(volume, start);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + ms / 1000);
      oscillator.connect(gain).connect(audio.destination);
      oscillator.start(start);
      oscillator.stop(start + ms / 1000);
    } catch {
      /* Ovozsiz ham o'yin ishlayveradi */
    }
  }

  const sound = {
    step: () => tone(300, 50, 0, "triangle", 0.025),
    take: () => [660, 880].forEach((f, i) => tone(f, 110, i * 70)),
    bad: () => tone(150, 240, 0, "sawtooth", 0.04),
    good: () => [523, 784].forEach((f, i) => tone(f, 120, i * 80)),
    win: () => [523, 659, 784, 1047].forEach((f, i) => tone(f, 170, i * 105)),
  };

  function showSoundState() {
    const button = $("sound");
    if (!button) return;
    button.setAttribute("aria-pressed", String(!muted));
    button.querySelector("[data-sound=on]").hidden = muted;
    button.querySelector("[data-sound=off]").hidden = !muted;
  }

  $("sound")?.addEventListener("click", () => {
    muted = !muted;
    store.set("game-sound", muted ? "off" : "on");
    showSoundState();
    sound.good();
  });
  showSoundState();

  /* --- Konfetti --- */

  function confetti() {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas = document.createElement("canvas");
    canvas.className = "confetti";
    canvas.width = innerWidth;
    canvas.height = innerHeight;
    document.body.append(canvas);
    const context = canvas.getContext("2d");
    const colors = ["#6366f1", "#8b5cf6", "#22d3ee", "#fbbf24", "#34d399", "#fb7185"];
    const pieces = Array.from({ length: 110 }, () => ({
      x: canvas.width / 2 + (Math.random() - 0.5) * 240,
      y: canvas.height * 0.4,
      vx: (Math.random() - 0.5) * 15,
      vy: -Math.random() * 15 - 4,
      size: 5 + Math.random() * 6,
      spin: Math.random() * 6,
      color: colors[Math.floor(Math.random() * colors.length)],
    }));
    const began = performance.now();
    (function frame(now) {
      context.clearRect(0, 0, canvas.width, canvas.height);
      for (const piece of pieces) {
        piece.vy += 0.42;
        piece.x += piece.vx;
        piece.y += piece.vy;
        piece.spin += 0.2;
        context.save();
        context.translate(piece.x, piece.y);
        context.rotate(piece.spin);
        context.fillStyle = piece.color;
        context.fillRect(-piece.size / 2, -piece.size / 4, piece.size, piece.size / 2);
        context.restore();
      }
      if (now - began < 2200) requestAnimationFrame(frame);
      else canvas.remove();
    })(began);
  }

  /* --- Holat va natija --- */

  function status(text, kind = "error") {
    const box = $("status");
    if (!box) return;
    box.textContent = text;
    box.className = `game-status is-${kind}${box.dataset.extra ? ` ${box.dataset.extra}` : ""}`;
    box.hidden = !text;
  }

  function printLines(lines) {
    const box = $("console");
    if (!box) return;
    $("console-lines").replaceChildren(
      ...lines.map((text) => {
        const row = document.createElement("div");
        row.textContent = text;
        return row;
      }),
    );
    box.hidden = !lines.length;
  }

  async function post(body, url = config.runUrl) {
    const token = document.querySelector("meta[name=csrf-token]")?.content;
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": token },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      return response.ok ? data : { failed: true, message: data.message };
    } catch {
      return { failed: true, message: "Serverdan javob kelmadi. Sahifani yangilab, qayta urinib ko'ring." };
    }
  }

  /* --- Yordam zinapoyasi: 2-xatoda maslahat, 3-xatoda yechim --- */

  let attempts = config.attempts ?? 0;

  function offerHelp() {
    if ($("hint-box") && attempts >= 2) $("hint-box").open = true;
    if ($("ask-help") && !config.solved && attempts >= config.helpAfter && $("solution-box").hidden) {
      $("ask-help").hidden = false;
    }
  }

  function failed(data) {
    attempts = data.attempts ?? attempts + 1;
    offerHelp();
  }

  $("ask-help")?.addEventListener("click", async () => {
    const data = await post({}, config.helpUrl);
    if (data.failed) return status(data.message);
    $("solution").innerHTML = data.solution.split("\n").map(colorize).join("\n");
    $("solution-box").hidden = false;
    $("ask-help").hidden = true;
    $("solution-box").scrollIntoView({ behavior: "smooth", block: "center" });
  });

  /* --- Yangi mavzu oldidan qisqa dars --- */

  function startIntro() {
    const intro = $("intro");
    if (!intro) return;
    const slides = [...intro.querySelectorAll("[data-slide]")];
    const dots = [...$("intro-dots").children];
    let index = 0;
    const show = () => {
      slides.forEach((slide, i) => {
        slide.hidden = i !== index;
      });
      dots.forEach((dot, i) => dot.classList.toggle("is-on", i <= index));
      $("intro-next").textContent = index === slides.length - 1 ? "Boshladik!" : "Keyingisi";
    };
    const close = () => {
      intro.hidden = true;
      // Yopilgach bola darhol yoza olsin
      document.querySelector("#term-input, #code")?.focus();
    };
    $("intro-next").addEventListener("click", () => {
      if (index === slides.length - 1) return close();
      index += 1;
      show();
    });
    $("intro-skip").addEventListener("click", close);
    show();
    $("intro-next").focus();
  }

  function saveProgress(data) {
    if (data.best_stars !== undefined) {
      document.querySelectorAll("#best-stars [class^=star-]").forEach((star, index) => {
        star.className = index < data.best_stars ? "star-on" : "star-off";
      });
    }
    if (data.xp !== undefined && $("xp-value")) $("xp-value").textContent = data.xp;
  }

  function win(data, text, onAgain) {
    const holder = $("result-stars");
    holder.replaceChildren();
    for (let i = 1; i <= 3; i++) {
      const star = document.createElement("span");
      star.className = i <= data.stars ? "star-on" : "star-off";
      star.append($("star-template").content.cloneNode(true));
      holder.append(star);
    }
    const parts = [text];
    if (data.gained > 0) parts.push(`+${data.gained} XP`);
    $("result-title").textContent = data.message || "Barakalla!";
    $("result-text").textContent = parts.filter(Boolean).join(" ");
    $("result-next").href = config.nextUrl;
    $("result-next-label").textContent = config.isLast ? "O'yin xaritasi" : "Keyingisi";
    $("result").hidden = false;
    $("result-next").focus();
    sound.win();
    confetti();
    const again = () => {
      $("result").hidden = true;
      onAgain?.();
    };
    $("result-again").onclick = again;
    $("result").onkeydown = (event) => {
      if (event.key === "Escape") again();
    };
  }

  const statementsNote = (data) =>
    data.stars < 3 ? `Siz ${data.statements} ta buyruq yozdingiz. 3 yulduz uchun ${data.par} ta yetadi.` : "";

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

  function editor({ onRun, isBusy = () => false }) {
    const code = $("code");
    const highlight = $("highlight");
    const gutter = $("gutter");
    let marks = { active: null, error: null };

    function syncScroll() {
      highlight.scrollTop = code.scrollTop;
      highlight.scrollLeft = code.scrollLeft;
      gutter.scrollTop = code.scrollTop;
    }

    function render() {
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
      render();
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
        onRun();
      } else if (event.key === "Backspace" && code.selectionStart === code.selectionEnd) {
        const before = code.value.slice(currentLine().start, code.selectionStart);
        if (before.length >= 4 && before.length % 4 === 0 && !before.trim()) {
          event.preventDefault();
          code.setSelectionRange(code.selectionStart - 4, code.selectionStart);
          document.execCommand("delete") || code.setRangeText("");
        }
      }
    });
    $("tools")?.addEventListener("click", (event) => {
      const tool = event.target.closest("[data-tool]")?.dataset.tool;
      if (tool && !isBusy()) insertTool(tool);
    });

    code.value = config.code ?? "";
    render();

    return {
      get value() {
        return code.value;
      },
      set value(text) {
        code.value = text;
        marks = { active: null, error: null };
        render();
      },
      set readOnly(value) {
        code.readOnly = value;
      },
      mark(active, error = null) {
        marks = { active, error };
        render();
      },
    };
  }

  /* --- Tezlik --- */

  function speedControl(onChange) {
    let speed = Number(store.get("game-speed", "1")) || 1;
    const show = () => {
      document.querySelectorAll("[data-speed]").forEach((button) => {
        button.classList.toggle("is-active", Number(button.dataset.speed) === speed);
      });
      onChange?.(speed);
    };
    document.querySelectorAll("[data-speed]").forEach((button) => {
      button.addEventListener("click", () => {
        speed = Number(button.dataset.speed);
        store.set("game-speed", String(speed));
        show();
      });
    });
    show();
    return () => speed;
  }

  const wait = (ms) => new Promise((done) => setTimeout(done, ms));

  startIntro();
  offerHelp();

  return { $, config, sound, status, printLines, post, failed, saveProgress, win, statementsNote, colorize, editor, speedControl, wait };
})();
