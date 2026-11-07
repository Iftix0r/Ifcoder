/* Kod jumboq: bosish bilan ishlaydi, telefonda ham qulay. Serverga faqat qator raqami va surilishi ketadi. */
(() => {
  const { $, config, sound } = Kit;
  const bank = $("bank");
  const program = $("program");
  let picked = []; // {id, indent}
  let busy = false;

  function tileCode(id) {
    const code = document.createElement("code");
    code.className = "tile-code";
    code.innerHTML = Kit.colorize(config.tiles[id]);
    return code;
  }

  function render() {
    const used = new Set(picked.map((item) => item.id));
    bank.replaceChildren(
      ...config.tiles.flatMap((_, id) => {
        if (used.has(id)) return [];
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tile";
        button.append(tileCode(id));
        button.addEventListener("click", () => add(id));
        return [button];
      }),
    );
    if (!bank.children.length) bank.textContent = "Hamma qator dasturda.";
    program.replaceChildren(
      ...picked.map((item, index) => {
        const row = document.createElement("div");
        row.className = "tile is-placed";
        row.style.marginLeft = `${item.indent * 1.5}rem`;
        row.dataset.index = index;
        row.append(tileCode(item.id));
        const tools = document.createElement("span");
        tools.className = "tile-tools";
        tools.append($("tile-tools").content.cloneNode(true));
        row.append(tools);
        return row;
      }),
    );
    if (!picked.length) {
      const empty = document.createElement("p");
      empty.className = "py-10 text-center text-sm text-ink-3";
      empty.textContent = "Chapdagi qatorlarni bosib, dasturni shu yerda yig'ing.";
      program.append(empty);
    }
  }

  function add(id) {
    if (busy) return;
    // Surilish oldingi qatordan olinadi: «:» dan keyin bir pog'ona ichkariga. Bola faqat chiqishni o'zi belgilaydi
    const previous = picked[picked.length - 1];
    const opensBlock = previous && config.tiles[previous.id].endsWith(":");
    const indent = previous ? Math.min(previous.indent + (opensBlock ? 1 : 0), config.maxIndent) : 0;
    picked.push({ id, indent });
    sound.step();
    clearNote();
    render();
  }

  function clearNote() {
    Kit.status("");
    Kit.printLines([]);
  }

  program.addEventListener("click", (event) => {
    const act = event.target.closest("[data-act]")?.dataset.act;
    const row = event.target.closest("[data-index]");
    if (!act || !row || busy) return;
    const index = Number(row.dataset.index);
    const item = picked[index];
    if (act === "in") item.indent = Math.min(item.indent + 1, config.maxIndent);
    if (act === "out") item.indent = Math.max(item.indent - 1, 0);
    if (act === "remove") picked.splice(index, 1);
    if (act === "up" && index > 0) [picked[index - 1], picked[index]] = [picked[index], picked[index - 1]];
    if (act === "down" && index < picked.length - 1) [picked[index + 1], picked[index]] = [picked[index], picked[index + 1]];
    clearNote();
    render();
  });

  async function run() {
    if (busy) return;
    busy = true;
    const data = await Kit.post({ lines: picked.map((item) => [item.id, item.indent]) });
    busy = false;
    clearNote();
    if (data.failed) return Kit.status(data.message);
    Kit.printLines(data.output);
    Kit.saveProgress(data);
    if (data.ok) {
      const text = data.stars < 3 ? `${data.tries}-urinishda yechdingiz. 3 yulduz uchun 2 ta urinish yetadi.` : "Ajoyib!";
      Kit.win(data, text);
    } else {
      sound.bad();
      Kit.status(data.line ? `${data.line}-qator: ${data.message}` : data.message);
      Kit.failed(data);
    }
  }

  $("expected").replaceChildren(
    ...config.expected.map((text) => {
      const row = document.createElement("div");
      row.textContent = text;
      return row;
    }),
  );
  $("run").addEventListener("click", run);
  $("reset").addEventListener("click", () => {
    picked = [];
    clearNote();
    render();
  });
  render();
})();
