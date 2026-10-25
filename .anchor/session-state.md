# Session state (auto-saved — last known reality)

_Updated: 2026-10-25 16:32:28_  ·  branch: `main`

## Uncommitted changes
```
 M .anchor/session-state.md
 M apps/crm/templates/crm/deal_board.html
 M apps/dashboard/templates/dashboard/home.html
 M apps/dashboard/views.py
 M apps/finance/templates/finance/credit_list.html
 M apps/finance/templates/finance/overview.html
 M apps/finance/templates/finance/partials/bars.html
 M apps/planner/templates/planner/board.html
 M apps/projects/templates/projects/detail.html
 M assets/app.css
 M static/dist/app.css
```

Diff stat:
```
 .anchor/session-state.md                          | 53 ++++-------------------
 apps/crm/templates/crm/deal_board.html            |  2 +-
 apps/dashboard/templates/dashboard/home.html      | 37 +++++++++-------
 apps/dashboard/views.py                           |  5 ++-
 apps/finance/templates/finance/credit_list.html   |  8 ++--
 apps/finance/templates/finance/overview.html      |  8 ++--
 apps/finance/templates/finance/partials/bars.html |  8 ++--
 apps/planner/templates/planner/board.html         |  4 +-
 apps/projects/templates/projects/detail.html      |  2 +-
 assets/app.css                                    | 32 +++++++++++++-
 static/dist/app.css                               |  2 +-
 11 files changed, 83 insertions(+), 78 deletions(-)
```

## Recent commits
```
fd730fb 133ss
225dd66 ewgse
9d5f9ee qwd
f28128d chore: ignore tmp/ and allow deploy without .env file
7ecca72 docs: add deploy guide to README and refresh session state
e756455 chore: reformat code, add __str__ methods and fix UI bugs
6ca0331 qdwq
d82844b qwdfq
```

## Resume
Read `memory/HANDOFF.md` for intent/next-step, then reconcile against the diff above. If HANDOFF.md is older than this checkpoint, trust the diff.
