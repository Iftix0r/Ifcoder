/* Rostmi?: karta suriladi yoki tugma bosiladi. To'g'ri javobni faqat server biladi. */
(() => {
  const { $, config, sound } = Kit;
  const stage = $("stage");
  const nextButton = $("truth-next");
  const SWIPE = 90;
  let answers = [];
  let lives = config.lives;
  let combo = 0;
  let card = null;
  let busy = false;

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

  function showTags(x) {
    card.querySelector(".truth-yes").style.opacity = Math.max(x / SWIPE, 0);
    card.querySelector(".truth-no").style.opacity = Math.max(-x / SWIPE, 0);
  }

  function drawCard() {
    $("truth-step").textContent = `${answers.length + 1} / ${config.cards.length}`;
    $("combo").textContent = combo > 1 ? `seriya ×${combo}` : "";
    card = document.createElement("div");
    card.className = "truth-card animate-fade-up";
    const code = document.createElement("pre");
    code.innerHTML = config.cards[answers.length].split("\n").map(Kit.colorize).join("\n");
    const yes = document.createElement("span");
    yes.className = "truth-tag truth-yes";
    yes.textContent = "ROST";
    const no = document.createElement("span");
    no.className = "truth-tag truth-no";
    no.textContent = "YOLG'ON";
    card.append(code, yes, no);
    let startX = null;
    let moved = 0;
    card.addEventListener("pointerdown", (event) => {
      if (busy) return;
      startX = event.clientX;
      card.setPointerCapture(event.pointerId);
      card.classList.add("is-dragging");
      card.classList.remove("animate-fade-up");
    });
    card.addEventListener("pointermove", (event) => {
      if (startX === null) return;
      moved = event.clientX - startX;
      card.style.transform = `translateX(${moved}px) rotate(${moved / 16}deg)`;
      showTags(moved);
    });
    const release = () => {
      if (startX === null) return;
      startX = null;
      card.classList.remove("is-dragging");
      if (Math.abs(moved) >= SWIPE) answer(moved > 0);
      else {
        card.style.transform = "";
        showTags(0);
      }
      moved = 0;
    };
    card.addEventListener("pointerup", release);
    card.addEventListener("pointercancel", release);
    stage.replaceChildren(card);
    Kit.status("");
    nextButton.hidden = true;
  }

  function restart() {
    answers = [];
    lives = config.lives;
    combo = 0;
    busy = false;
    drawLives();
    drawCard();
  }

  async function answer(value) {
    if (busy || !nextButton.hidden) return;
    busy = true;
    const flown = card;
    flown.classList.remove("animate-fade-up");
    flown.style.transform = `translateX(${value ? 520 : -520}px) rotate(${value ? 22 : -22}deg)`;
    flown.style.opacity = "0";
    const data = await Kit.post({ answers: [...answers, value] });
    busy = false;
    if (data.failed) {
      flown.style.transform = "";
      flown.style.opacity = "";
      return Kit.status(data.message);
    }
    answers.push(value);
    lives = data.lives;
    drawLives();
    combo = data.correct ? combo + 1 : 0;
    data.correct ? sound.take() : sound.bad();
    if (data.finished) {
      Kit.saveProgress(data);
      if (data.ok) {
        Kit.status(data.why, "info");
        await Kit.wait(700);
        return Kit.win(data, data.mistakes ? `${data.mistakes} ta xato bilan.` : "Birorta ham xatosiz!", restart);
      }
      Kit.status(`${data.why} ${data.message}`);
      nextButton.textContent = "Qaytadan boshlash";
      nextButton.onclick = restart;
      nextButton.hidden = false;
      return;
    }
    if (data.correct) {
      setTimeout(drawCard, 260);
    } else {
      // Xatoda to'xtaymiz: bola tushuntirishni o'qib olsin
      Kit.status(`Xato. ${data.why}`);
      nextButton.textContent = "Davom";
      nextButton.onclick = drawCard;
      nextButton.hidden = false;
      nextButton.focus();
    }
  }

  $("say-yes").addEventListener("click", () => answer(true));
  $("say-no").addEventListener("click", () => answer(false));
  addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") answer(true);
    if (event.key === "ArrowLeft") answer(false);
  });
  restart();
})();
