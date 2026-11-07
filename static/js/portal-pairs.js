/* Kod juftligi: juftlikni faqat server biladi, brauzer har ochilgan juftni so'raydi. */
(() => {
  const { $, config, sound } = Kit;
  const holder = $("cards");
  let picks = [];
  let open = [];
  let busy = false;
  let found = 0;
  let misses = 0;

  function build() {
    holder.replaceChildren(
      ...config.cards.map((card, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "memory-card";
        button.setAttribute("aria-label", `${index + 1}-karta`);
        const inner = document.createElement("span");
        inner.className = "memory-inner";
        const back = document.createElement("span");
        back.className = "memory-face memory-back font-mono text-2xl font-bold";
        back.textContent = "</>";
        const front = document.createElement("span");
        front.className = "memory-face memory-front";
        front.innerHTML = card.text.split("\n").map(Kit.colorize).join("\n");
        inner.append(back, front);
        button.append(inner);
        button.addEventListener("click", () => flip(index, button));
        return button;
      }),
    );
  }

  function restart() {
    picks = [];
    open = [];
    found = 0;
    misses = 0;
    $("found").textContent = 0;
    $("misses").textContent = 0;
    build();
  }

  async function flip(index, button) {
    if (busy || button.classList.contains("is-up")) return;
    button.classList.add("is-up");
    button.setAttribute("aria-label", config.cards[index].text);
    sound.step();
    open.push({ index, button });
    if (open.length < 2) return;
    busy = true;
    const [first, second] = open;
    open = [];
    picks.push([first.index, second.index]);
    const data = await Kit.post({ picks });
    if (data.failed) {
      busy = false;
      first.button.classList.remove("is-up");
      second.button.classList.remove("is-up");
      picks.pop();
      return Kit.status(data.message);
    }
    if (data.match) {
      found += 1;
      sound.take();
      first.button.classList.add("is-found");
      second.button.classList.add("is-found");
    } else {
      misses += 1;
      sound.bad();
      first.button.classList.add("is-miss");
      second.button.classList.add("is-miss");
      await Kit.wait(1100);
      for (const { button: card } of [first, second]) card.classList.remove("is-up", "is-miss");
    }
    $("found").textContent = found;
    $("misses").textContent = misses;
    busy = false;
    if (data.ok) {
      Kit.saveProgress(data);
      await Kit.wait(400);
      Kit.win(data, data.misses ? `${data.misses} ta xato bilan.` : "Birorta ham xatosiz!", restart);
    }
  }

  build();
})();
