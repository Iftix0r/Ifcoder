# Session state (auto-saved — last known reality)

_Updated: 2026-11-01 21:34:16_  ·  branch: `main`

## Uncommitted changes
```
 M .anchor/session-state.md
 M apps/core/navigation.py
 M apps/finance/admin.py
 M apps/finance/forms.py
 M apps/finance/models.py
 M apps/finance/urls.py
 M apps/finance/views.py
 M static/dist/app.css
 M tests/test_pages.py
?? apps/finance/migrations/0003_wishes.py
?? apps/finance/templates/finance/wish_list.html
?? tests/test_wishes.py
```

Diff stat:
```
 .anchor/session-state.md |  40 ++++---------
 apps/core/navigation.py  |   1 +
 apps/finance/admin.py    |   4 +-
 apps/finance/forms.py    |  36 +++++++++++-
 apps/finance/models.py   | 115 +++++++++++++++++++++++++++++++++++++
 apps/finance/urls.py     |   7 +++
 apps/finance/views.py    | 144 ++++++++++++++++++++++++++++++++++++++++++++++-
 static/dist/app.css      |   2 +-
 tests/test_pages.py      |   3 +
 9 files changed, 317 insertions(+), 35 deletions(-)
```

## Recent commits
```
f476fb8 af
cfb15ae qwaf
2e769a5 egy
fd730fb 133ss
225dd66 ewgse
9d5f9ee qwd
f28128d chore: ignore tmp/ and allow deploy without .env file
7ecca72 docs: add deploy guide to README and refresh session state
```

## Resume
Read `memory/HANDOFF.md` for intent/next-step, then reconcile against the diff above. If HANDOFF.md is older than this checkpoint, trust the diff.
