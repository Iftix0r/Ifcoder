#!/usr/bin/env bash
# Eskiz.uz (cPanel → Setup Python App) serverida yangilash: ./deploy.sh
#
# Virtualenv avtomatik topiladi: ~/virtualenv/<papka nomi>/<python versiya>/bin/activate
# Boshqa yo'l bo'lsa:  VENV_ACTIVATE=/path/bin/activate ./deploy.sh
# Backup'siz:          SKIP_BACKUP=1 ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
APP_DIR="$(basename "$PWD")"

if [[ -z "${VENV_ACTIVATE:-}" ]]; then
  for v in 3.13 3.12 3.11 3.10; do
    if [[ -f "$HOME/virtualenv/$APP_DIR/$v/bin/activate" ]]; then
      VENV_ACTIVATE="$HOME/virtualenv/$APP_DIR/$v/bin/activate"
      break
    fi
  done
fi
if [[ -z "${VENV_ACTIVATE:-}" ]]; then
  echo "Virtualenv topilmadi (~/virtualenv/$APP_DIR/*). VENV_ACTIVATE=/path/bin/activate ./deploy.sh deb ishga tushiring." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$VENV_ACTIVATE"
export DJANGO_SETTINGS_MODULE=config.settings.prod

if [[ ! -f .env ]]; then
  echo ".env fayli yo'q. Nusxa olib to'ldiring: cp .env.example .env && nano .env" >&2
  exit 1
fi

# prod.py loglarni logs/django.log ga yozadi — papka manage.py dan oldin bo'lishi shart
mkdir -p tmp logs backups public/media

echo "→ Kod yangilanmoqda (git pull)"
git pull --ff-only

echo "→ Kutubxonalar"
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [[ -z "${SKIP_BACKUP:-}" && -f db.sqlite3 ]]; then
  echo "→ Migratsiyadan oldin backup"
  python manage.py backup_db
fi

echo "→ Migratsiyalar"
python manage.py migrate --noinput

echo "→ Statik fayllar"
python manage.py collectstatic --noinput -v0

echo "→ Tekshiruv"
python manage.py check --deploy --fail-level ERROR

echo "→ Passenger qayta ishga tushirilmoqda"
touch tmp/restart.txt
# CloudLinux (cPanel «Setup Python App»): ilovani majburan qayta ishga tushirish
if command -v cloudlinux-selector >/dev/null 2>&1; then
  cloudlinux-selector restart --json --interpreter python --app-root "$APP_DIR" >/dev/null 2>&1 || true
fi

echo "✓ Tayyor — $(git log -1 --format='%h %s')"
