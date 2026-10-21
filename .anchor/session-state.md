# Session state (auto-saved — last known reality)

_Updated: 2026-10-21 08:40:28_  ·  branch: `main`

## Uncommitted changes
```
 M .gitignore
 M README.md
 M apps/core/templatetags/ui.py
 M apps/core/views.py
 M apps/crm/forms.py
 M apps/crm/models.py
 M apps/crm/templates/crm/deal_board.html
 M apps/crm/views.py
 M apps/finance/forms.py
 M apps/finance/models.py
 M apps/finance/views.py
 M apps/growth/models.py
 M apps/notes/models.py
 M apps/planner/models.py
 M apps/planner/views.py
 M apps/projects/forms.py
 M apps/projects/views.py
 M apps/resources/forms.py
 M apps/resources/models.py
 M apps/vault/forms.py
 M apps/vault/models.py
 M assets/app.css
 M config/settings/base.py
 M templates/components/form_modal.html
 M templates/partials/nav_list.html
 M templates/partials/sidebar.html
?? .anchor/
?? apps/accounts/forms.py
?? apps/accounts/templates/
?? apps/accounts/urls.py
?? apps/accounts/views.py
?? apps/core/search.py
?? apps/crm/admin.py
?? apps/crm/migrations/0001_initial.py
?? apps/crm/migrations/0002_initial.py
?? apps/dashboard/templates/
?? apps/dashboard/urls.py
?? apps/dashboard/views.py
?? apps/finance/admin.py
?? apps/finance/migrations/0001_initial.py
?? apps/finance/templates/finance/debt_list.html
?? apps/finance/templates/finance/invoice_detail.html
?? apps/finance/templates/finance/invoice_list.html
?? apps/finance/templates/finance/invoice_print.html
?? apps/finance/templates/finance/partials/debt_column.html
?? apps/growth/admin.py
?? apps/growth/migrations/0001_initial.py
?? apps/growth/templates/
?? apps/growth/urls.py
?? apps/growth/views.py
?? apps/landing/forms.py
?? apps/landing/templates/
?? apps/landing/urls.py
?? apps/landing/views.py
?? apps/notes/admin.py
?? apps/notes/migrations/0001_initial.py
?? apps/notes/templates/
?? apps/notes/urls.py
?? apps/notes/views.py
?? apps/planner/admin.py
?? apps/planner/migrations/0001_initial.py
?? apps/projects/admin.py
?? apps/projects/migrations/0001_initial.py
?? apps/resources/admin.py
?? apps/resources/migrations/0001_initial.py
?? apps/resources/templates/
?? apps/resources/urls.py
?? apps/resources/views.py
?? apps/vault/admin.py
?? apps/vault/management/
?? apps/vault/middleware.py
?? apps/vault/migrations/0001_initial.py
?? apps/vault/services.py
?? apps/vault/templates/
?? apps/vault/urls.py
?? apps/vault/views.py
?? config/urls.py
?? static/dist/
?? templates/layouts/auth.html
?? tests/conftest.py
?? tests/test_pages.py
```

Diff stat:
```
 apps/crm/views.py                      |  57 +++++++++--
 apps/finance/forms.py                  |  13 ++-
 apps/finance/models.py                 |  44 ++++++--
 apps/finance/views.py                  |  87 +++++++++++++---
 apps/growth/models.py                  |  14 +--
 apps/notes/models.py                   |   7 +-
 apps/planner/models.py                 |  17 +++-
 apps/planner/views.py                  |  95 ++++++++++++++----
 apps/projects/forms.py                 |  15 ++-
 apps/projects/views.py                 |  23 ++++-
 apps/resources/forms.py                |  15 ++-
 apps/resources/models.py               |   7 +-
 apps/vault/forms.py                    |   4 +-
 apps/vault/models.py                   |  21 +++-
 assets/app.css                         |   6 +-
 config/settings/base.py                |   1 +
 templates/components/form_modal.html   |   2 +-
 templates/partials/nav_list.html       |   3 +-
 templates/partials/sidebar.html        |   2 +-
 26 files changed, 498 insertions(+), 177 deletions(-)
```

## Recent commits
```
6ca0331 qdwq
d82844b qwdfq
ff97f80 Add initial Flutter project configuration and dependencies in pubspec.yaml
84170b3 Fix site-wide crash: static manifest lookup breaks with DEBUG=False
607ad8e Add new icons and web manifest for site branding
24ae76a feat: add Google site verification endpoint for Search Console integration
1ece455 Implement code changes to enhance functionality and improve performance
398ac96 feat: add location settings check before requesting location updates to enhance reliability
```

## Resume
Read `memory/HANDOFF.md` for intent/next-step, then reconcile against the diff above. If HANDOFF.md is older than this checkpoint, trust the diff.
