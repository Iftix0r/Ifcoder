/* Bloklar: bola bosib teradi, Python kodi shu zahoti yoziladi. Serverga oddiy kod boradi, baholash o'zgarmaydi. */
(() => {
  const { $, config } = Kit;
  const LABELS = { yur: "yur", chapga: "chapga", ongga: "ongga", ol: "ol" };
  const CONDITIONS = [
    ["kristall_bor()", "kristall bor"],
    ["oldinda_devor()", "oldinda devor"],
    ["not oldinda_devor()", "oldinda yo'l"],
    ["chapda_devor()", "chapda devor"],
    ["not ongda_devor()", "o'ngda yo'l"],
    ["not yetib_keldi()", "yetib kelmagan"],
  ];
  const palette = $("block-palette");
  const root = $("block-program");
  const storeKey = `blocks:${config.runUrl}`;
  let program = [];
  let target = program;

  const read = () => {
    try {
      return JSON.parse(localStorage.getItem(storeKey)) || [];
    } catch {
      return [];
    }
  };
  const save = () => {
    try {
      localStorage.setItem(storeKey, JSON.stringify(program));
    } catch {
      /* private rejim */
    }
  };

  function python(items, depth = 0) {
    const pad = "    ".repeat(depth);
    if (!items.length) return depth ? [`${pad}pass`] : [];
    return items.flatMap((item) => {
      if (item.t === "cmd") return [`${pad}${item.cmd}()`];
      if (item.t === "repeat") return [`${pad}for i in range(${item.n}):`, ...python(item.body, depth + 1)];
      if (item.t === "while") return [`${pad}while ${item.cond}:`, ...python(item.body, depth + 1)];
      const head = [`${pad}if ${item.cond}:`, ...python(item.body, depth + 1)];
      return item.else ? [...head, `${pad}else:`, ...python(item.else, depth + 1)] : head;
    });
  }

  function sync() {
    Kit.code.value = python(program).join("\n");
    save();
    draw();
  }

  function add(kind) {
    const item =
      kind === "repeat"
        ? { t: "repeat", n: 3, body: [] }
        : kind === "if"
          ? { t: "if", cond: "kristall_bor()", body: [], else: null }
          : kind === "while"
            ? { t: "while", cond: "not oldinda_devor()", body: [] }
            : { t: "cmd", cmd: kind };
    target.push(item);
    if (item.body) target = item.body; // Yangi blok ichiga terish davom etadi
    Kit.sound.step();
    sync();
  }

  function select(options, value, onChange) {
    const node = document.createElement("select");
    for (const [key, label] of options) node.add(new Option(label, key, false, key === value));
    node.addEventListener("click", (event) => event.stopPropagation());
    node.addEventListener("change", () => onChange(node.value));
    return node;
  }

  function body(list) {
    const holder = document.createElement("div");
    holder.className = `block-body${target === list ? " is-target" : ""}`;
    holder.addEventListener("click", (event) => {
      event.stopPropagation();
      target = list;
      draw();
    });
    holder.append(...list.map((item, index) => drawItem(item, list, index)));
    if (!list.length) {
      const empty = document.createElement("p");
      empty.className = "px-1 py-1 text-xs font-normal text-white/70";
      empty.textContent = "Bu yerni bosing va ichiga blok qo'shing";
      holder.append(empty);
    }
    return holder;
  }

  function drawItem(item, list, index) {
    const block = document.createElement("div");
    block.className = `block block-${item.t}`;
    const head = document.createElement("div");
    head.className = "block-head";
    if (item.t === "cmd") head.append(LABELS[item.cmd]);
    if (item.t === "repeat") {
      const numbers = Array.from({ length: 12 }, (_, i) => [String(i + 1), String(i + 1)]);
      head.append(select(numbers, String(item.n), (value) => ((item.n = Number(value)), sync())), "marta takrorla");
    }
    if (item.t === "if" || item.t === "while") {
      head.append(item.t === "if" ? "agar" : "toki", select(CONDITIONS, item.cond, (value) => ((item.cond = value), sync())));
    }
    if (item.t === "if") {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "rounded bg-black/25 px-1.5 py-0.5 text-xs";
      toggle.textContent = item.else ? "aks holda −" : "aks holda +";
      toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        item.else = item.else ? null : [];
        target = program;
        sync();
      });
      head.append(toggle);
    }
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "block-x";
    remove.textContent = "×";
    remove.setAttribute("aria-label", "O'chirish");
    remove.addEventListener("click", (event) => {
      event.stopPropagation();
      list.splice(index, 1);
      target = program;
      sync();
    });
    head.append(remove);
    block.append(head);
    if (item.body) block.append(body(item.body));
    if (item.else) {
      const label = document.createElement("p");
      label.className = "px-2 text-xs";
      label.textContent = "aks holda";
      block.append(label, body(item.else));
    }
    return block;
  }

  function draw() {
    root.className = `block-root mt-3 min-h-28 rounded-xl border border-dashed border-line-strong p-2${target === program ? " is-target" : ""}`;
    root.replaceChildren(...program.map((item, index) => drawItem(item, program, index)));
    if (!program.length) {
      const empty = document.createElement("p");
      empty.className = "py-8 text-center text-sm text-ink-3";
      empty.textContent = "Yuqoridagi bloklarni bosing";
      root.append(empty);
    }
  }

  function setMode(mode) {
    const blocks = mode === "blocks";
    Kit.blockMode = blocks;
    $("blocks").hidden = !blocks;
    $("tools").hidden = blocks;
    $("code").readOnly = blocks;
    document.querySelectorAll("[data-mode]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.mode === mode);
    });
    if ($("mode-note")) $("mode-note").hidden = !blocks;
    try {
      localStorage.setItem("game-mode", mode);
    } catch {
      /* private rejim */
    }
  }

  const names = { repeat: ["repeat", "takrorla"], if: ["if", "agar"], while: ["while", "toki"] };
  palette.append(
    ...config.blocks.map((kind) => {
      const button = document.createElement("button");
      const [css, label] = names[kind] ?? ["cmd", LABELS[kind]];
      button.type = "button";
      button.className = `block-chip block-${css}`;
      button.textContent = label;
      button.addEventListener("click", () => add(kind));
      return button;
    }),
  );
  root.addEventListener("click", () => {
    target = program;
    draw();
  });
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });

  program = read();
  target = program;
  let mode = "blocks";
  try {
    mode = localStorage.getItem("game-mode") || "blocks";
  } catch {
    /* private rejim */
  }
  setMode(mode);
  if (mode === "blocks" && program.length) Kit.code.value = python(program).join("\n");
  draw();
})();
