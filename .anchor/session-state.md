# Session state (auto-saved — last known reality)

_Updated: 2026-10-25 16:46:39_  ·  branch: `main`

## Uncommitted changes
```
 M .anchor/session-state.md
 M apps/core/forms.py
 M apps/finance/forms.py
 M apps/finance/templates/finance/invoice_detail.html
 M apps/landing/templates/landing/index.html
 M static/dist/app.css
 M templates/components/modal_form.html
```

Diff stat:
```
 .anchor/session-state.md                           | 41 ++++------------------
 apps/core/forms.py                                 | 19 +++++++++-
 apps/finance/forms.py                              |  8 ++++-
 apps/finance/templates/finance/invoice_detail.html |  2 +-
 apps/landing/templates/landing/index.html          | 10 +++---
 static/dist/app.css                                |  2 +-
 templates/components/modal_form.html               |  2 +-
 7 files changed, 39 insertions(+), 45 deletions(-)
```

## Recent commits
```
cfb15ae qwaf
2e769a5 egy
fd730fb 133ss
225dd66 ewgse
9d5f9ee qwd
f28128d chore: ignore tmp/ and allow deploy without .env file
7ecca72 docs: add deploy guide to README and refresh session state
e756455 chore: reformat code, add __str__ methods and fix UI bugs
```

## Resume
Read `memory/HANDOFF.md` for intent/next-step, then reconcile against the diff above. If HANDOFF.md is older than this checkpoint, trust the diff.
