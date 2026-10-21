// node_modules'dagi frontend kutubxonalarni static/vendor va ikonlarni apps/core/icons ga ko'chiradi.
// Ishga tushirish: npm run vendor
import { cpSync, mkdirSync, readdirSync } from "node:fs";

const vendor = "static/vendor";
mkdirSync(vendor, { recursive: true });
const files = {
  "node_modules/htmx.org/dist/htmx.min.js": "htmx.min.js",
  "node_modules/alpinejs/dist/cdn.min.js": "alpine.min.js",
  "node_modules/@alpinejs/focus/dist/cdn.min.js": "alpine-focus.min.js",
  "node_modules/@alpinejs/collapse/dist/cdn.min.js": "alpine-collapse.min.js",
};
for (const [src, dst] of Object.entries(files)) cpSync(src, `${vendor}/${dst}`);

const icons = "apps/core/icons";
mkdirSync(icons, { recursive: true });
const src = "node_modules/lucide-static/icons";
for (const f of readdirSync(src)) cpSync(`${src}/${f}`, `${icons}/${f}`);
console.log("vendor: ok");
