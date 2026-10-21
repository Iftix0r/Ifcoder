/* Ifcoder — frontend yadrosi (Alpine.js komponentlari + HTMX sozlamalari). */

const isTyping = (e) => ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) || e.target.isContentEditable || !!document.querySelector("#modal-content > *");

const storage = {
  get(key, fallback = null) {
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

function applyTheme(mode) {
  const dark = mode === "dark" || (mode === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

document.addEventListener("alpine:init", () => {
  const Alpine = window.Alpine;

  /* --- Tema: light / dark / system --- */
  Alpine.store("theme", {
    mode: storage.get("theme", "system"),
    set(mode) {
      this.mode = mode;
      storage.set("theme", mode);
      applyTheme(mode);
    },
    cycle() {
      const order = ["light", "dark", "system"];
      this.set(order[(order.indexOf(this.mode) + 1) % order.length]);
    },
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (Alpine.store("theme").mode === "system") applyTheme("system");
  });

  /* --- Sidebar --- */
  Alpine.store("sidebar", {
    collapsed: document.documentElement.classList.contains("sb-collapsed"),
    mobileOpen: false,
    toggle() {
      this.collapsed = !this.collapsed;
      document.documentElement.classList.toggle("sb-collapsed", this.collapsed);
      storage.set("sidebar", this.collapsed ? "collapsed" : "open");
    },
  });

  /* --- Toast bildirishnomalar --- */
  Alpine.store("toasts", {
    items: [],
    seq: 0,
    push(message, level = "success", timeout = 4200) {
      const id = ++this.seq;
      this.items.push({ id, message, level, visible: true });
      if (timeout) setTimeout(() => this.remove(id), timeout);
    },
    remove(id) {
      const item = this.items.find((t) => t.id === id);
      if (item) item.visible = false;
      setTimeout(() => (this.items = this.items.filter((t) => t.id !== id)), 300);
    },
  });

  /* --- Modal (HTMX kontent #modal-content ga yuklanadi) --- */
  Alpine.store("modal", {
    open: false,
    size: "md",
    show() {
      this.open = true;
    },
    close() {
      this.open = false;
      setTimeout(() => {
        const el = document.getElementById("modal-content");
        if (el && !this.open) el.innerHTML = "";
      }, 250);
    },
  });

  /* --- ⌘K buyruqlar paneli (bo'limlar + serverdan qidiruv) --- */
  Alpine.data("palette", () => ({
    open: false,
    query: "",
    active: 0,
    items: [],
    remote: [],
    loading: false,
    searchUrl: null,
    timer: null,
    init() {
      const el = document.getElementById("palette-data");
      this.items = el ? JSON.parse(el.textContent) : [];
      this.searchUrl = this.$el.dataset.searchUrl || null;
      this.$watch("query", (q) => this.fetchRemote(q));
    },
    get results() {
      const q = this.query.trim().toLowerCase();
      const local = q ? this.items.filter((i) => (i.label + " " + i.section).toLowerCase().includes(q)) : this.items;
      return [...this.remote, ...local];
    },
    fetchRemote(q) {
      clearTimeout(this.timer);
      if (!this.searchUrl || q.trim().length < 2) {
        this.remote = [];
        return;
      }
      this.loading = true;
      this.timer = setTimeout(async () => {
        try {
          const resp = await fetch(`${this.searchUrl}?q=${encodeURIComponent(q.trim())}`, { headers: { Accept: "application/json" } });
          const data = await resp.json();
          if (q === this.query) this.remote = data.results || [];
        } catch {
          this.remote = [];
        } finally {
          this.loading = false;
        }
      }, 200);
    },
    show() {
      this.open = true;
      this.query = "";
      this.remote = [];
      this.active = 0;
      this.$nextTick(() => this.$refs.input?.focus());
    },
    hide() {
      this.open = false;
    },
    onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        this.open ? this.hide() : this.show();
      } else if (e.key.toLowerCase() === "n" && !e.ctrlKey && !e.metaKey && !e.altKey && !this.open && !isTyping(e)) {
        e.preventDefault();
        htmx.ajax("GET", "/tasks/new/", { target: "#modal-content" });
      } else if (e.key === "/" && !this.open && !["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) && !e.target.isContentEditable) {
        e.preventDefault();
        this.show();
      }
    },
    move(step) {
      const n = this.results.length;
      if (!n) return;
      this.active = (this.active + step + n) % n;
      this.$nextTick(() => this.$refs.list?.querySelector("[data-active=true]")?.scrollIntoView({ block: "nearest" }));
    },
    go(item = this.results[this.active]) {
      if (!item) return;
      this.hide();
      if (!window.htmx) return (location.href = item.href);
      htmx.ajax("GET", item.href, { target: "body", swap: "innerHTML" }).then(() => history.pushState({}, "", item.href));
    },
  }));

  /* --- Kanban (vazifalar, bitimlar): drag & drop --- */
  Alpine.data("kanban", () => ({
    dragging: null,
    overStage: null,
    fromList: null,
    fromNext: null,
    start(e) {
      const card = e.target.closest("[data-card]");
      if (!card) return;
      this.dragging = card;
      this.fromList = card.parentElement;
      this.fromNext = card.nextElementSibling;
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", card.dataset.card);
      requestAnimationFrame(() => card.classList.add("opacity-40", "scale-95"));
    },
    over(e) {
      if (!this.dragging) return;
      const list = e.target.closest("[data-stage]")?.querySelector("[data-list]");
      if (!list) return;
      e.preventDefault();
      this.overStage = list.closest("[data-stage]").dataset.stage;
      const after = [...list.querySelectorAll("[data-card]:not(.opacity-40)")].find((el) => {
        const box = el.getBoundingClientRect();
        return e.clientY < box.top + box.height / 2;
      });
      if (after) list.insertBefore(this.dragging, after);
      else list.appendChild(this.dragging);
    },
    async drop(e) {
      if (!this.dragging) return;
      e.preventDefault();
      const card = this.dragging;
      const column = card.closest("[data-stage]");
      const order = [...column.querySelectorAll("[data-card]")].map((el) => +el.dataset.card);
      this.end();
      this.recount();
      const token = document.querySelector("meta[name=csrf-token]")?.content;
      try {
        const resp = await fetch(card.dataset.moveUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": token },
          body: JSON.stringify({ stage: column.dataset.stage, order }),
        });
        const data = await resp.json();
        if (!data.ok) throw new Error();
        if (data.toast) Alpine.store("toasts").push(data.toast, "success");
        htmx.trigger(document.body, "kanban:moved");
      } catch {
        this.revert(card);
        Alpine.store("toasts").push("Ko'chirib bo'lmadi. Qayta urinib ko'ring.", "error");
      }
    },
    end() {
      this.dragging?.classList.remove("opacity-40", "scale-95");
      this.dragging = null;
      this.overStage = null;
    },
    revert(card) {
      if (this.fromList) this.fromList.insertBefore(card, this.fromNext && this.fromNext.parentElement === this.fromList ? this.fromNext : null);
      this.recount();
    },
    recount() {
      this.$root.querySelectorAll("[data-stage]").forEach((col) => {
        const counter = col.querySelector("[data-count]");
        if (counter) counter.textContent = col.querySelectorAll("[data-card]").length;
        col.querySelector("[data-empty]")?.classList.toggle("hidden", !!col.querySelector("[data-card]"));
      });
    },
  }));

  /* --- Ishlayotgan taymer: o'tgan vaqtni har soniyada yangilaydi --- */
  Alpine.data("ticker", (startedIso) => ({
    text: "",
    init() {
      const start = new Date(startedIso).getTime();
      const tick = () => {
        const s = Math.max(0, Math.floor((Date.now() - start) / 1000));
        const h = Math.floor(s / 3600);
        const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
        const sec = String(s % 60).padStart(2, "0");
        this.text = (h ? h + ":" : "") + m + ":" + sec;
      };
      tick();
      const t = setInterval(() => (document.body.contains(this.$el) ? tick() : clearInterval(t)), 1000);
    },
  }));

  /* --- Fokus (pomodoro) taymeri — store: sahifa almashsa ham to'xtamaydi --- */
  Alpine.store("pomodoro", {
    mode: "focus",
    left: 25 * 60,
    running: false,
    timer: null,
    durations: { focus: 25 * 60, break: 5 * 60 },
    get display() {
      return String(Math.floor(this.left / 60)).padStart(2, "0") + ":" + String(this.left % 60).padStart(2, "0");
    },
    get percent() {
      return 100 - (this.left * 100) / this.durations[this.mode];
    },
    toggle() {
      this.running ? this.pause() : this.start();
    },
    start() {
      this.running = true;
      this.timer = setInterval(() => {
        if (this.left > 0) return this.left--;
        this.pause();
        const next = this.mode === "focus" ? "break" : "focus";
        Alpine.store("toasts").push(next === "break" ? "Fokus tugadi — 5 daqiqa dam oling ☕" : "Tanaffus tugadi — yana ishga! 🚀", "info", 8000);
        this.set(next);
      }, 1000);
    },
    pause() {
      this.running = false;
      clearInterval(this.timer);
    },
    set(mode) {
      this.pause();
      this.mode = mode;
      this.left = this.durations[mode];
    },
  });

  /* --- Nusxa olish tugmasi --- */
  Alpine.data("copy", (text) => ({
    copied: false,
    async run() {
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const t = document.createElement("textarea");
        t.value = text;
        document.body.appendChild(t);
        t.select();
        document.execCommand("copy");
        t.remove();
      }
      this.copied = true;
      setTimeout(() => (this.copied = false), 1800);
    },
  }));

  /* --- Raqamlarni animatsiya bilan sanash --- */
  Alpine.data("countUp", (target = 0, suffix = "") => ({
    display: "0" + suffix,
    init() {
      const format = (n) => Math.round(n).toLocaleString("ru-RU").replace(/,/g, " ") + suffix;
      if (!target || matchMedia("(prefers-reduced-motion: reduce)").matches) {
        this.display = format(target);
        return;
      }
      const io = new IntersectionObserver(([entry]) => {
        if (!entry.isIntersecting) return;
        io.disconnect();
        const start = performance.now();
        const duration = 900;
        const tick = (now) => {
          const p = Math.min(1, (now - start) / duration);
          this.display = format(target * (1 - Math.pow(1 - p, 3)));
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
      io.observe(this.$el);
    },
  }));

  /* --- Qayta yuborish taymeri --- */
  Alpine.data("countdown", (seconds = 0) => ({
    left: seconds,
    init() {
      const t = setInterval(() => (this.left > 0 ? this.left-- : clearInterval(t)), 1000);
    },
  }));

  /* --- Pul summasi: 1250000 → «1 250 000» (serverga bo'shliqsiz ketadi) --- */
  Alpine.directive("money", (el) => {
    const format = () => {
      const digits = el.value.replace(/\D/g, "").replace(/^0+(?=\d)/, "");
      const caret = el.value.length - el.selectionStart;
      el.value = digits.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
      if (document.activeElement === el) el.setSelectionRange(el.value.length - caret, el.value.length - caret);
    };
    el.addEventListener("input", format);
    el.form?.addEventListener("submit", () => (el.value = el.value.replace(/\s/g, "")), true);
    el.form?.addEventListener("htmx:configRequest", (e) => {
      if (e.detail.parameters[el.name] !== undefined) e.detail.parameters[el.name] = el.value.replace(/\s/g, "");
    });
    format();
  });
});

/* --- Oddiy formalar ikki marta yuborilmasin (masalan, SMS kod avtomatik yuborilib, keyin tugma bosilsa) --- */
document.addEventListener(
  "submit",
  (e) => {
    const form = e.target;
    if (form.closest("[hx-boost=true]") || form.matches("[hx-post],[hx-get],[hx-put],[hx-patch],[hx-delete]")) return;
    if (form.dataset.submitting) {
      e.preventDefault();
      return;
    }
    form.dataset.submitting = "1";
    // fayl yuklab olish kabi sahifa almashmaydigan holatlar uchun
    setTimeout(() => delete form.dataset.submitting, 8000);
  },
  true,
);
window.addEventListener("pageshow", () => document.querySelectorAll("form[data-submitting]").forEach((f) => delete f.dataset.submitting));

/* --- HTMX --- */
document.addEventListener("htmx:configRequest", (e) => {
  const token = document.querySelector("meta[name=csrf-token]")?.content;
  if (token) e.detail.headers["X-CSRFToken"] = token;
});

document.addEventListener("DOMContentLoaded", () => {
  if (window.htmx) {
    htmx.config.globalViewTransitions = true;
    htmx.config.scrollBehavior = "instant";
    htmx.config.defaultFocusScroll = false;
  }
  flushServerMessages();
});

/* Sidebar menyusi: sahifa almashganda scroll joyini saqlash va faol bo'limni ko'rinadigan qilish */
let sidebarScroll = null;
function revealActiveNav() {
  const nav = document.querySelector("[data-sidebar-nav]");
  if (!nav) return;
  if (sidebarScroll !== null) nav.scrollTop = sidebarScroll;
  sidebarScroll = null;
  const active = nav.querySelector(".is-active");
  if (!active) return;
  const a = active.getBoundingClientRect();
  const n = nav.getBoundingClientRect();
  if (a.top < n.top + 16 || a.bottom > n.bottom - 28) nav.scrollTop += a.top - n.top - n.height / 2 + a.height / 2;
}
document.addEventListener("htmx:beforeSwap", (e) => {
  if (e.detail.boosted) sidebarScroll = document.querySelector("[data-sidebar-nav]")?.scrollTop ?? null;
});
document.addEventListener("htmx:afterSettle", (e) => {
  if (e.detail.boosted) revealActiveNav();
});
document.addEventListener("DOMContentLoaded", revealActiveNav);

function flushServerMessages() {
  const el = document.getElementById("django-messages");
  if (!el || !window.Alpine) return;
  const items = JSON.parse(el.textContent);
  el.remove();
  items.forEach((m) => Alpine.store("toasts").push(m.message, m.level));
}

document.addEventListener("alpine:initialized", flushServerMessages);
document.addEventListener("htmx:afterSettle", flushServerMessages);

document.addEventListener("toast", (e) => window.Alpine?.store("toasts").push(e.detail.message, e.detail.level));
document.addEventListener("modal:close", () => window.Alpine?.store("modal").close());
document.addEventListener("htmx:afterSwap", (e) => {
  if (e.detail.target.id === "modal-content" && window.Alpine) {
    const store = Alpine.store("modal");
    store.size = e.detail.target.firstElementChild?.dataset.modalSize || "md";
    store.show();
  }
});

document.addEventListener("htmx:beforeRequest", (e) => {
  if (e.detail.boosted || e.detail.requestConfig?.target === document.body) {
    document.documentElement.classList.remove("is-done");
    document.documentElement.classList.add("is-loading");
  }
});
document.addEventListener("htmx:afterRequest", () => {
  const root = document.documentElement;
  if (!root.classList.contains("is-loading")) return;
  root.classList.remove("is-loading");
  root.classList.add("is-done");
  setTimeout(() => root.classList.remove("is-done"), 500);
});
document.addEventListener("htmx:responseError", (e) => {
  const status = e.detail.xhr.status;
  const text = status === 403 ? "Bu amal uchun ruxsat yo'q." : status === 404 ? "Sahifa topilmadi." : "Xatolik yuz berdi. Qayta urinib ko'ring.";
  window.Alpine?.store("toasts").push(text, "error");
});
document.addEventListener("htmx:sendError", () => {
  window.Alpine?.store("toasts").push("Internet aloqasini tekshiring.", "error");
});
