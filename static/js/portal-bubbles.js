/* Pufakcha: qaysi pufak to'g'riligini faqat server biladi. */
(() => {
  const { $, config, sound } = Kit;
  const sky = $("sky");
  const TINTS = ["rgb(34 211 238 / 0.35)", "rgb(167 139 250 / 0.35)", "rgb(52 211 153 / 0.35)", "rgb(251 191 36 / 0.3)", "rgb(244 114 182 / 0.32)"];
  const SPAWN_MS = 1500;
  const RISE_S = 9;

  let pops = [];
  let combo = 0;
  let round = 0;
  let queue = Promise.resolve();

  function showScore(hits) {
    $("hits").textContent = hits;
    $("combo").textContent = combo > 1 ? `seriya ×${combo}` : "";
  }

  function finish(data) {
    round += 1;
    sky.querySelectorAll(".bubble").forEach((bubble) => bubble.remove());
    Kit.saveProgress(data);
    if (data.ok) {
      const text = `${data.good} tadan ${data.hits} tasi topildi.${data.misses ? ` ${data.misses} ta xato.` : ""}`;
      Kit.win(data, text, showStart);
    } else {
      Kit.status(data.message);
      showStart();
    }
  }

  function send(body) {
    queue = queue.then(() => Kit.post(body));
    return queue;
  }

  async function popBubble(index, bubble, id) {
    if (bubble.dataset.popped) return;
    bubble.dataset.popped = "1";
    bubble.disabled = true;
    pops.push(index);
    const data = await send({ pops: [...pops] });
    if (id !== round) return;
    if (data.failed) return Kit.status(data.message);
    bubble.classList.add(data.hit ? "is-hit" : "is-miss");
    combo = data.hit ? combo + 1 : 0;
    data.hit ? sound.take() : sound.bad();
    showScore(data.hits);
    setTimeout(() => bubble.remove(), 280);
    if (data.finished) finish(data);
  }

  function spawn(index, id) {
    if (id !== round) return;
    const size = sky.clientWidth < 420 ? 76 : 92;
    const bubble = document.createElement("button");
    bubble.type = "button";
    bubble.className = "bubble";
    bubble.textContent = config.items[index];
    bubble.style.setProperty("--d", `${size}px`);
    bubble.style.setProperty("--x", `${16 + Math.random() * Math.max(sky.clientWidth - size - 32, 0)}px`);
    bubble.style.setProperty("--t", `${RISE_S}s`);
    bubble.style.setProperty("--tint", TINTS[index % TINTS.length]);
    bubble.addEventListener("pointerdown", () => popBubble(index, bubble, id));
    bubble.addEventListener("click", () => popBubble(index, bubble, id));
    bubble.addEventListener("animationend", (event) => {
      if (event.animationName === "bubble-rise") bubble.remove();
    });
    sky.append(bubble);
  }

  function start() {
    round += 1;
    const id = round;
    pops = [];
    combo = 0;
    queue = Promise.resolve();
    showScore(0);
    Kit.status("");
    $("sky-start").hidden = true;
    config.items.forEach((_, index) => setTimeout(() => spawn(index, id), index * SPAWN_MS));
    setTimeout(async () => {
      if (id !== round) return;
      const data = await send({ pops: [...pops], done: true });
      if (id !== round) return;
      if (data.failed) return Kit.status(data.message);
      finish(data);
    }, (config.items.length - 1) * SPAWN_MS + RISE_S * 1000 + 300);
  }

  function showStart() {
    $("sky-start").hidden = false;
  }

  $("sky-go").addEventListener("click", start);
})();
