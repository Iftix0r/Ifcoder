#!/usr/bin/env bash
# Eskiz.uz (cPanel → Setup Python App) serverida yangilash: ./deploy.sh
#
# Virtualenv avtomatik topiladi: ~/virtualenv/<papka nomi>/<python versiya>/bin/activate
# Boshqa yo'l bo'lsa:  VENV_ACTIVATE=/path/bin/activate ./deploy.sh
# Backup'siz:          SKIP_BACKUP=1 ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
APP_DIR="$(basename "$PWD")"
DEPLOY_STARTED=$SECONDS
STEP_NO=0
STEP_TOTAL=8

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  C_RESET=$'\033[0m'
  C_BOLD=$'\033[1m'
  C_MUTED=$'\033[2m'
  C_AMBER=$'\033[38;5;214m'
  C_GREEN=$'\033[38;5;78m'
  C_RED=$'\033[38;5;203m'
else
  C_RESET="" C_BOLD="" C_MUTED="" C_AMBER="" C_GREEN="" C_RED=""
fi

banner() {
  printf '\n%s%s  ◆ IFCODER DEPLOY%s\n' "$C_BOLD" "$C_AMBER" "$C_RESET"
  printf '%s  Ishonchli · xavfsiz · takrorlanuvchi%s\n\n' "$C_MUTED" "$C_RESET"
}

step() {
  STEP_NO=$((STEP_NO + 1))
  printf '%s[%d/%d]%s %s%s%s\n' "$C_AMBER" "$STEP_NO" "$STEP_TOTAL" "$C_RESET" "$C_BOLD" "$1" "$C_RESET"
}

ok() {
  printf '      %s✓%s %s\n' "$C_GREEN" "$C_RESET" "$1"
}

die() {
  printf '\n%s✗ Deploy toxtadi:%s %s\n' "$C_RED" "$C_RESET" "$1" >&2
  exit 1
}

on_error() {
  local code=$? line=$1
  printf '\n%s✗ Xatolik%s · qator %s · kod %s\n' "$C_RED" "$C_RESET" "$line" "$code" >&2
  printf '%s  Ozgarishlarni tekshiring va deployni qayta ishga tushiring.%s\n' "$C_MUTED" "$C_RESET" >&2
  exit "$code"
}
trap 'on_error $LINENO' ERR

banner

if [[ -z "${VENV_ACTIVATE:-}" ]]; then
  for v in 3.13 3.12 3.11 3.10; do
    if [[ -f "$HOME/virtualenv/$APP_DIR/$v/bin/activate" ]]; then
      VENV_ACTIVATE="$HOME/virtualenv/$APP_DIR/$v/bin/activate"
      break
    fi
  done
fi
if [[ -z "${VENV_ACTIVATE:-}" ]]; then
  die "Virtualenv topilmadi. VENV_ACTIVATE=/path/bin/activate ./deploy.sh deb ishga tushiring."
fi
# shellcheck disable=SC1090
source "$VENV_ACTIVATE"
export DJANGO_SETTINGS_MODULE=config.settings.prod

if [[ ! -f .env && -z "${DJANGO_SECRET_KEY:-}" ]]; then
  die ".env fayli yo‘q. Avval .env.example nusxasini yarating va to‘ldiring."
fi

# prod.py loglarni logs/django.log ga yozadi — papka manage.py dan oldin bo'lishi shart
mkdir -p tmp logs backups public/media

step "Kod yangilanmoqda"
git pull --ff-only
ok "Git yangilandi: $(git log -1 --format='%h')"

step "Python kutubxonalari"
pip install -q --upgrade pip
pip install -q -r requirements.txt
ok "Bog‘liqliklar tayyor"

if [[ -z "${SKIP_BACKUP:-}" && -f db.sqlite3 ]]; then
  step "Ma’lumotlar bazasi zaxirasi"
  python manage.py backup_db
  ok "Backup yaratildi"
else
  step "Ma’lumotlar bazasi zaxirasi"
  ok "O‘tkazib yuborildi"
fi

step "Migratsiyalar"
python manage.py migrate --noinput
ok "Baza sxemasi yangilandi"

step "Statik fayllar"
python manage.py collectstatic --noinput -v0
ok "Statik fayllar yig‘ildi"

step "Django xavfsizlik tekshiruvi"
python manage.py check --deploy --fail-level ERROR
ok "Production tekshiruvi o‘tdi"

# Ilova papkasi saytning ochiq ildizi: qoida bo'lmasa baza, backup va loglar internetdan yuklanadi
step "Server himoyasi"
if ! grep -qs "IFCODER-SECURITY" .htaccess; then
  touch .htaccess
  cp -a .htaccess .htaccess.pre-security
  cat scripts/htaccess-security.conf .htaccess.pre-security > .htaccess.new
  cat .htaccess.new > .htaccess
  rm -f .htaccess.new
  ok ".htaccess himoyasi o‘rnatildi"
else
  ok ".htaccess himoyasi faol"
fi

step "Ilovani qayta ishga tushirish"
touch tmp/restart.txt
# CloudLinux (cPanel «Setup Python App»): ilovani majburan qayta ishga tushirish
if command -v cloudlinux-selector >/dev/null 2>&1; then
  cloudlinux-selector restart --json --interpreter python --app-root "$APP_DIR" >/dev/null 2>&1 || true
fi

# Userbot eski kodda qolmasin: to'xtatamiz, cron bir necha daqiqada yangi kod bilan qayta ishga tushiradi
pkill -f "manage.py userbot" || true
ok "Passenger yangilandi"

SITE_URL="${SITE_URL:-$(grep -s '^SITE_URL=' .env | cut -d= -f2- || true)}"
SITE_URL="${SITE_URL:-https://iftix0r.uz}"
for path in db.sqlite3 .git/config; do
  status="$(curl -s -o /dev/null -I -m 15 -w '%{http_code}' "$SITE_URL/$path" || true)"
  if [[ "$status" == "200" ]]; then
    die "XAVF: $SITE_URL/$path internetdan ochiq. .htaccess ni tekshiring."
  fi
done

ELAPSED=$((SECONDS - DEPLOY_STARTED))
printf '\n%s%s  ✓ DEPLOY TAYYOR%s\n' "$C_BOLD" "$C_GREEN" "$C_RESET"
printf '  %sSayt%s     %s\n' "$C_MUTED" "$C_RESET" "$SITE_URL"
printf '  %sVersiya%s  %s\n' "$C_MUTED" "$C_RESET" "$(git log -1 --format='%h · %s')"
printf '  %sVaqt%s     %dm %02ds\n\n' "$C_MUTED" "$C_RESET" "$((ELAPSED / 60))" "$((ELAPSED % 60))"
