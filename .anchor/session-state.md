# Session state (auto-saved — last known reality)

_Updated: 2026-10-21 08:57:33_  ·  branch: `main`

## Uncommitted changes
```
 M .anchor/session-state.md
 M .env.example
 M README.md
 M apps/accounts/templates/accounts/settings.html
 M apps/accounts/urls.py
 M apps/accounts/views.py
 M apps/landing/views.py
 M apps/vault/management/commands/backup_db.py
 M config/settings/base.py
 M config/settings/test.py
 M tests/conftest.py
 M tests/test_pages.py
?? apps/core/management/
?? apps/core/telegram.py
?? apps/dashboard/digest.py
?? tests/test_telegram.py
```

Diff stat:
```
 .anchor/session-state.md                       | 40 ++++++++-----------
 .env.example                                   |  5 +++
 README.md                                      | 15 ++++++++
 apps/accounts/templates/accounts/settings.html | 15 ++++++++
 apps/accounts/urls.py                          |  1 +
 apps/accounts/views.py                         | 12 ++++++
 apps/landing/views.py                          |  3 ++
 apps/vault/management/commands/backup_db.py    | 11 ++++++
 config/settings/base.py                        |  6 +++
 config/settings/test.py                        |  2 +
 tests/conftest.py                              | 53 ++++++++++++++++++++++++++
 tests/test_pages.py                            | 51 +------------------------
 12 files changed, 141 insertions(+), 73 deletions(-)
```

## Recent commits
```
9d5f9ee qwd
f28128d chore: ignore tmp/ and allow deploy without .env file
7ecca72 docs: add deploy guide to README and refresh session state
e756455 chore: reformat code, add __str__ methods and fix UI bugs
6ca0331 qdwq
d82844b qwdfq
ff97f80 Add initial Flutter project configuration and dependencies in pubspec.yaml
84170b3 Fix site-wide crash: static manifest lookup breaks with DEBUG=False
```

## Resume
Read `memory/HANDOFF.md` for intent/next-step, then reconcile against the diff above. If HANDOFF.md is older than this checkpoint, trust the diff.
