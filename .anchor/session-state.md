# Session state (auto-saved — last known reality)

_Updated: 2026-10-21 09:42:38_  ·  branch: `main`

## Uncommitted changes
```
 M .anchor/session-state.md
 M apps/core/forms.py
 M apps/core/navigation.py
 M apps/dashboard/digest.py
 M apps/dashboard/views.py
 M apps/finance/forms.py
 M apps/finance/models.py
 M apps/finance/templates/finance/debt_list.html
 M apps/finance/urls.py
 M apps/finance/views.py
 M static/dist/app.css
 M tests/test_pages.py
?? apps/finance/migrations/0002_credits.py
?? apps/finance/templates/finance/credit_list.html
?? apps/finance/templates/finance/partials/debt_tabs.html
?? tests/test_credits.py
```

Diff stat:
```
 .anchor/session-state.md                      |  60 ++++---------
 apps/core/forms.py                            |   7 ++
 apps/core/navigation.py                       |   2 +-
 apps/dashboard/digest.py                      |  10 +++
 apps/dashboard/views.py                       |  20 ++++-
 apps/finance/forms.py                         |  43 ++++++++-
 apps/finance/models.py                        | 123 ++++++++++++++++++++++++++
 apps/finance/templates/finance/debt_list.html |   2 +
 apps/finance/urls.py                          |   6 ++
 apps/finance/views.py                         | 105 +++++++++++++++++++++-
 static/dist/app.css                           |   2 +-
 tests/test_pages.py                           |   2 +-
 12 files changed, 330 insertions(+), 52 deletions(-)
```

## Recent commits
```
225dd66 ewgse
9d5f9ee qwd
f28128d chore: ignore tmp/ and allow deploy without .env file
7ecca72 docs: add deploy guide to README and refresh session state
e756455 chore: reformat code, add __str__ methods and fix UI bugs
6ca0331 qdwq
d82844b qwdfq
ff97f80 Add initial Flutter project configuration and dependencies in pubspec.yaml
```

## Resume
Read `memory/HANDOFF.md` for intent/next-step, then reconcile against the diff above. If HANDOFF.md is older than this checkpoint, trust the diff.
