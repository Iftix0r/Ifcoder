/* Terminal o'yini. Buyruqlar haqiqiy kompyuterda emas, serverdagi xayoliy fayl tizimida bajariladi. */
(() => {
  const { $, config, sound } = Kit;
  const log = $("term-log");
  const input = $("term-input");
  const screen = $("screen");

  let commands = [];
  let history = [];
  let cursor = 0;
  let step = 0;
  let wrong = 0;
  let prompt = config.prompt;
  let names = config.names;
  let busy = false;

  function line(text, css = "") {
    const row = document.createElement("div");
    row.className = `term-out ${css}`;
    row.textContent = text;
    log.append(row);
  }

  function scroll() {
    screen.scrollTop = screen.scrollHeight;
  }

  function drawPrompt() {
    $("term-prompt").textContent = prompt;
    $("term-title").textContent = `${prompt.replace(/\$$/, "")} — kema terminali`;
  }

  function drawTree(rows, cwd) {
    const home = document.createElement("div");
    home.className = `tree-row ${cwd === "/home/bola" ? "is-here" : ""}`;
    home.textContent = "🏠 ~";
    $("tree").replaceChildren(
      home,
      ...rows.map((row) => {
        const item = document.createElement("div");
        item.className = `tree-row ${row.path === cwd ? "is-here" : ""}`;
        item.style.paddingLeft = `${(row.depth + 1) * 1.1}rem`;
        item.textContent = `${row.dir ? "📁" : "📄"} ${row.name}`;
        return item;
      }),
    );
    if (!cwd.startsWith("/home/bola")) {
      const away = document.createElement("div");
      away.className = "tree-row is-here mt-1";
      away.textContent = `📍 ${cwd}`;
      $("tree").append(away);
    }
  }

  function drawStep() {
    const current = config.steps[step];
    $("step-dots").replaceChildren(
      ...config.steps.map((_, index) => {
        const dot = document.createElement("li");
        dot.className = `step-dot ${index < step ? "is-done" : index === step ? "is-now" : ""}`;
        return dot;
      }),
    );
    if (!current) return;
    $("step-count").textContent = `${step + 1}-vazifa / ${config.steps.length}`;
    $("step-task").textContent = current.task;
    $("term-task").textContent = `${step + 1}/${config.steps.length}: ${current.task}`;
    $("step-teach").textContent = current.teach;
    $("example-btn").textContent = current.example;
    $("step-example").hidden = true;
    $("show-example").hidden = false;
    wrong = 0;
  }

  function showExample() {
    $("step-example").hidden = false;
    $("show-example").hidden = true;
  }

  function restart() {
    commands = [];
    step = 0;
    prompt = config.prompt;
    names = config.names;
    log.replaceChildren();
    line("Kema kompyuteri v2.6. Faqat terminal ishlayapti.", "term-dim");
    line("Yordam kerak bo'lsa: help", "term-dim");
    drawPrompt();
    drawTree(config.tree, config.cwd);
    drawStep();
    input.value = "";
    input.disabled = false;
    input.focus();
  }

  async function submit() {
    if (busy) return;
    const text = input.value;
    line(`${prompt} ${text}`, "term-echo");
    input.value = "";
    if (!text.trim()) return scroll();
    history.push(text);
    cursor = history.length;
    busy = true;
    commands.push(text);
    const data = await Kit.post({ commands });
    busy = false;
    if (data.failed) {
      commands.pop();
      line(data.message, "term-err");
      return scroll();
    }
    if (data.clear) log.replaceChildren();
    if (data.out) line(data.out, data.failed_command ? "term-err" : "");
    if (data.tip) line(`💡 ${data.tip}`, "term-tip");
    prompt = data.prompt;
    names = data.names;
    drawPrompt();
    drawTree(data.tree, data.cwd);
    if (data.advanced) {
      step = data.step;
      sound.take();
      line("✔ Vazifa bajarildi", "term-ok");
      drawStep();
    } else {
      sound.step();
      wrong += 1;
      if (wrong >= 2) showExample(); // Ikki marta adashsa, namuna o'zi ochiladi
    }
    scroll();
    if (data.finished) {
      input.disabled = true;
      Kit.saveProgress(data);
      await Kit.wait(700);
      Kit.win(data, `${commands.length} ta buyruq bilan.`, restart);
    }
  }

  function candidates(part, first) {
    if (first) return config.commands.filter((name) => name.startsWith(part));
    const found = new Set();
    for (const path of names) {
      const hidden = path.split("/").some((piece) => piece.startsWith("."));
      if (!path.startsWith(part) || (hidden && !part.includes("."))) continue;
      // Faqat keyingi pog'onagacha: ombor/ yozilsa, ombor/quti/ taklif qilinadi
      const slash = path.indexOf("/", part.length);
      found.add(slash === -1 ? path : path.slice(0, slash + 1));
    }
    return [...found];
  }

  function commonStart(words) {
    let start = words[0];
    for (const word of words) {
      while (!word.startsWith(start)) start = start.slice(0, -1);
    }
    return start;
  }

  function complete() {
    const words = input.value.split(" ");
    const part = words[words.length - 1];
    const matches = candidates(part, words.length === 1);
    if (!matches.length) return;
    words[words.length - 1] = commonStart(matches);
    const whole = matches.length === 1 && !matches[0].endsWith("/");
    input.value = words.join(" ") + (whole ? " " : "");
    if (matches.length > 1) {
      line(`${prompt} ${input.value}`, "term-echo");
      line(matches.join("  "), "term-dim");
      scroll();
    }
  }

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      submit();
    } else if (event.key === "Tab") {
      event.preventDefault();
      complete();
    } else if (event.key === "ArrowUp" || event.key === "ArrowDown") {
      event.preventDefault();
      cursor = Math.max(0, Math.min(history.length, cursor + (event.key === "ArrowUp" ? -1 : 1)));
      input.value = history[cursor] ?? "";
    } else if (event.key === "l" && event.ctrlKey) {
      event.preventDefault();
      log.replaceChildren();
    } else if (event.key === "c" && event.ctrlKey) {
      event.preventDefault();
      line(`${prompt} ${input.value}^C`, "term-echo");
      input.value = "";
      scroll();
    }
  });
  $("term").addEventListener("click", (event) => {
    if (!event.target.closest("button") && !getSelection().toString()) input.focus();
  });
  $("term-tools").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.key === "tab") complete();
    else if (button.dataset.key === "enter") submit();
    else input.value += button.dataset.insert;
    input.focus();
  });
  $("show-example").addEventListener("click", showExample);
  $("example-btn").addEventListener("click", () => {
    input.value = $("example-btn").textContent;
    input.focus();
  });
  $("term-reset").addEventListener("click", restart);
  restart();
})();
