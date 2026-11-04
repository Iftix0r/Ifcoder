import asyncio
import fcntl
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.userbot.runner import Runner


class Command(BaseCommand):
    help = "Telegram userbot jarayoni. Cron har 5 daqiqada chaqirsa bo'ladi: ishlab turgan bo'lsa, darhol chiqadi."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Bir marta sinxronlab chiqish (doimiy jarayon o'rniga)")

    def handle(self, *args, once=False, **options):
        logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        path = settings.BASE_DIR / "tmp" / "userbot.lock"
        path.parent.mkdir(exist_ok=True)
        with path.open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return  # bitta sessiya — bitta jarayon
            try:
                asyncio.run(Runner().run(once=once))
            except KeyboardInterrupt:
                pass
