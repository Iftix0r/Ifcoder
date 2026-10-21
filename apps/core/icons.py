"""Lucide ikonlari (apps/core/icons/*.svg) — serverda inline SVG sifatida chiqariladi."""

import re
from functools import lru_cache
from pathlib import Path

from django.utils.html import escape
from django.utils.safestring import mark_safe

ICON_DIR = Path(__file__).resolve().parent / "icons"
_COMMENT = re.compile(r"<!--.*?-->\s*", re.S)
_SVG_ATTRS = re.compile(r"<svg[^>]*>", re.S)


@lru_cache(maxsize=512)
def _inner(name: str) -> str:
    path = ICON_DIR / f"{name}.svg"
    if not path.is_file():
        path = ICON_DIR / "circle-help.svg"
    raw = _COMMENT.sub("", path.read_text())
    raw = _SVG_ATTRS.sub("", raw, count=1).replace("</svg>", "")
    return " ".join(raw.split())


def icon_svg(name: str, css: str = "size-5", stroke: str = "2") -> str:
    return mark_safe(
        f'<svg xmlns="http://www.w3.org/2000/svg" class="{escape(css)}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="{escape(stroke)}" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false">{_inner(name)}</svg>'
    )
