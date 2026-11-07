/* Darslikdagi kod maydoni: natijani chiqaradi, ball bermaydi. */
(() => {
  const { $ } = Kit;
  const editor = Kit.editor({ onRun: run });

  async function run() {
    editor.mark(null);
    Kit.status("");
    const data = await Kit.post({ code: editor.value });
    if (data.failed) return Kit.status(data.message);
    Kit.printLines(data.output.length ? data.output : data.error ? [] : ["(hech narsa chiqmadi)"]);
    if (data.error) {
      editor.mark(null, data.line);
      Kit.status(data.line ? `${data.line}-qator: ${data.error}` : data.error);
    }
  }

  $("run").addEventListener("click", run);
  $("reset").addEventListener("click", () => {
    editor.value = Kit.config.code;
    Kit.status("");
    Kit.printLines([]);
  });
  document.querySelectorAll("[data-try]").forEach((button) => {
    button.addEventListener("click", () => {
      editor.value = button.previousElementSibling.textContent;
      $("code").scrollIntoView({ behavior: "smooth", block: "center" });
      run();
    });
  });
})();
