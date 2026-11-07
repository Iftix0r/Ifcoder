/* Kod detektivi: to'g'ri javobni faqat server biladi, har javobdan keyin so'raladi. */
(() => {
  const { $, config, sound } = Kit;
  const options = $("quiz-options");
  const nextButton = $("quiz-next");
  let answers = [];
  let lives = config.lives;
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

  function show() {
    const question = config.questions[answers.length];
    $("quiz-step").textContent = `${answers.length + 1}-savol / ${config.questions.length}`;
    $("quiz-code").innerHTML = question.code.split("\n").map(Kit.colorize).join("\n");
    options.replaceChildren(
      ...question.options.map((text, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "quiz-option";
        button.textContent = text;
        button.addEventListener("click", () => choose(index));
        return button;
      }),
    );
    nextButton.hidden = true;
    Kit.status("");
  }

  function restart() {
    answers = [];
    lives = config.lives;
    drawLives();
    show();
  }

  async function choose(index) {
    if (busy || !nextButton.hidden) return;
    busy = true;
    const data = await Kit.post({ answers: [...answers, index] });
    busy = false;
    if (data.failed) return Kit.status(data.message);
    answers.push(index);
    lives = data.lives;
    drawLives();
    const buttons = [...options.children];
    buttons.forEach((button) => {
      button.disabled = true;
    });
    buttons[data.right].classList.add("is-right");
    if (data.correct) {
      sound.good();
    } else {
      buttons[index].classList.add("is-wrong");
      sound.bad();
    }
    if (!data.finished) {
      nextButton.firstChild.textContent = "Keyingi savol ";
      nextButton.onclick = show;
      nextButton.hidden = false;
      return nextButton.focus();
    }
    Kit.saveProgress(data);
    if (data.ok) {
      const text = data.mistakes ? `${data.mistakes} ta xato bilan.` : "Birorta ham xatosiz!";
      await Kit.wait(500);
      return Kit.win(data, text, restart);
    }
    Kit.status(data.message);
    nextButton.firstChild.textContent = "Qaytadan boshlash ";
    nextButton.onclick = restart;
    nextButton.hidden = false;
  }

  restart();
})();
