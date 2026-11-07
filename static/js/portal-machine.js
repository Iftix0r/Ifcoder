/* Sehrli mashina: sinovlar birma-bir o'tkaziladi, natija serverdan keladi. */
(() => {
  const { $, config, sound } = Kit;
  const holder = $("machine-rows");
  const gear = $("gear");
  const runLabel = $("run-label");

  let runId = 0;
  let running = false;

  const cell = (text, css = "") => {
    const node = document.createElement("span");
    node.className = css;
    node.textContent = text;
    return node;
  };

  function drawRows(rows) {
    holder.replaceChildren(
      ...rows.map((row) => {
        const item = document.createElement("div");
        item.className = "machine-row";
        item.append(cell(row.input, "machine-value"), cell("→", "text-ink-3"), cell(row.expected, "machine-value"), cell("", "machine-value machine-got"));
        return item;
      }),
    );
  }

  const editor = Kit.editor({ onRun: run, isBusy: () => running });

  function setRunning(value) {
    running = value;
    editor.readOnly = value;
    gear.classList.toggle("is-spinning", value);
    runLabel.textContent = value ? "Tekshirilmoqda…" : "Ishga tushirish";
  }

  function reset() {
    runId += 1;
    setRunning(false);
    drawRows(config.rows);
    editor.mark(null);
    Kit.status("");
    Kit.printLines([]);
  }

  async function reveal(rows, id) {
    drawRows(rows);
    const items = holder.children;
    for (const [index, row] of rows.entries()) {
      if (id !== runId) return false;
      if (row.ok === null) continue;
      const got = items[index].querySelector(".machine-got");
      got.textContent = row.got;
      items[index].classList.add(row.ok ? "is-ok" : "is-bad");
      row.ok ? sound.good() : sound.bad();
      await Kit.wait(280);
    }
    return id === runId;
  }

  async function run() {
    if (running) return;
    reset();
    const id = runId;
    setRunning(true);
    const data = await Kit.post({ code: editor.value });
    if (id !== runId) return;
    if (data.failed) {
      setRunning(false);
      return Kit.status(data.message);
    }
    Kit.printLines(data.events.filter((event) => event.a === "print").map((event) => event.text));
    if (!(await reveal(data.rows, id))) return;
    setRunning(false);
    Kit.saveProgress(data);
    if (data.ok) {
      const text = [`${data.hidden} ta yashirin sinovdan ham o'tdi.`, Kit.statementsNote(data)].filter(Boolean).join(" ");
      Kit.win(data, text, () => {
        reset();
        $("code").focus();
      });
    } else {
      editor.mark(null, data.line);
      Kit.status(data.line ? `${data.line}-qator: ${data.message}` : data.message);
    }
  }

  $("machine-hidden").textContent = `Yana ${config.hidden} ta yashirin sinov bor: javoblarni yodlab bo'lmaydi.`;
  drawRows(config.rows);
  $("run").addEventListener("click", run);
  $("reset").addEventListener("click", reset);
})();
