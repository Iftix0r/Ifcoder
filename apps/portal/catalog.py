"""Hamma o'yinlar ro'yxati. Har bir bosqich ``slug`` i butun portal bo'yicha yagona: natija shu nom bilan saqlanadi."""

from collections.abc import Callable
from dataclasses import dataclass

from . import engine, solutions
from . import levels as robot
from .games import BadPayload, bubbles, bugs, code_from, draw, machine, pairs, puzzle, quiz, snake, space, truth

# Yangi mavzuning birinchi bosqichlari bo'sh varaqdan boshlanmaydi: bola qolipni to'ldiradi
SCAFFOLDS = {
    "uzun-yol": "for i in range(___):\n    yur()\n",
    "kristall-qatori": "for i in range(___):\n    yur()\n    ol()\nyur()\n",
    "orqaga-qayt": "def orqaga():\n    chapga()\n    chapga()\n\n# Kodni shu yerdan davom ettiring\n",
    "bormi": "for i in range(6):\n    yur()\n    # Shu yerga if yozing\n",
    "devorgacha": "while not ___():\n    yur()\n",
    "yarim-yol": "qadam = 0\nwhile not oldinda_devor():\n    yur()\n    qadam = qadam + 1\nol()\n"
    "# Endi orqaga buriling va qadam // 2 marta yuring\n",
}
ADVANCED = {"def", "return", "o'zgaruvchi"}


def _robot_attempt(level, payload, attempts) -> dict:
    code = code_from(payload)
    return {**robot.attempt(level, code), "stored": code}


def _bug_config(level, row) -> dict:
    return {
        "world": engine.World(level.maps[0]).as_dict(),
        "code": row.code if row and row.code else level.starter,
        "starter": level.starter,
        "maps": len(level.maps),
    }


def _blocks_for(level) -> list[str] | None:
    """Bloklar boshlovchi uchun: funksiya va o'zgaruvchiga yetganda bola Python'ga o'tgan bo'ladi."""
    if ADVANCED & set(level.require):
        return None
    tools = CHAPTER_OF[level.slug].tools
    blocks = ["yur", "chapga", "ongga", "ol"]
    blocks += ["repeat"] if "for i in range(3):" in tools else []
    blocks += ["if"] if "if kristall_bor():" in tools else []
    blocks += ["while"] if "yetib_keldi()" in tools else []
    return blocks


def _robot_config(level, row) -> dict:
    starter = SCAFFOLDS.get(level.slug, level.starter)
    return {**_bug_config(level, row), "code": row.code if row and row.code else starter, "blocks": _blocks_for(level)}


@dataclass(frozen=True)
class Game:
    slug: str
    title: str
    tagline: str
    skill: str
    icon: str
    tone: str
    template: str
    script: str
    chapters: tuple
    attempt: Callable
    config: Callable
    difficulty: str = "O'rta"
    solution: Callable | None = None  # Bola qotib qolganda ko'rsatiladigan yechim

    @property
    def levels(self) -> tuple:
        return tuple(level for chapter in self.chapters for level in chapter.levels)


GAMES: tuple[Game, ...] = (
    Game(
        "pufak",
        "Pufakcha",
        "Qoidaga mos pufaklarni bosib yoring",
        "Eng oson",
        "circle-dot",
        "tone-cyan",
        "portal/play_bubbles.html",
        "portal-bubbles.js",
        bubbles.CHAPTERS,
        bubbles.attempt,
        bubbles.config,
        "Oson",
    ),
    Game(
        "rostmi",
        "Rostmi?",
        "Kartani o'ngga yoki chapga suring: rost yoki yolg'on",
        "Tez o'yin",
        "thumbs-up",
        "tone-emerald",
        "portal/play_truth.html",
        "portal-truth.js",
        truth.CHAPTERS,
        truth.attempt,
        truth.config,
        "Oson",
    ),
    Game(
        "ilon",
        "Kod iloni",
        "So'zlarni tartib bilan yeb, kod qatorini yig'ing",
        "Sintaksis",
        "worm",
        "tone-emerald",
        "portal/play_snake.html",
        "portal-snake.js",
        snake.CHAPTERS,
        snake.attempt,
        snake.config,
        "Oson",
    ),
    Game(
        "robot",
        "Robot yo'li",
        "Bloklardan yoki kod bilan robotni manzilga olib boring",
        "Algoritm",
        "bot",
        "tone-brand",
        "portal/play.html",
        "portal-game.js",
        robot.CHAPTERS,
        _robot_attempt,
        _robot_config,
        "Oson",
        lambda level: solutions.SOLUTIONS[level.slug],
    ),
    Game(
        "kosmos",
        "Kod kosmosi",
        "Kemani boshqaring, to'g'ri javobli asteroidni oting",
        "Tez fikrlash",
        "rocket",
        "tone-cyan",
        "portal/play_space.html",
        "portal-space.js",
        space.CHAPTERS,
        quiz.attempt,
        quiz.config,
        "Oson",
    ),
    Game(
        "juftlik",
        "Kod juftligi",
        "Kartalarni ochib, kodni natijasi bilan juftlang",
        "Kod o'qish",
        "layers",
        "tone-violet",
        "portal/play_pairs.html",
        "portal-pairs.js",
        pairs.CHAPTERS,
        pairs.attempt,
        pairs.config,
        "Oson",
    ),
    Game(
        "jumboq",
        "Kod jumboq",
        "Aralashgan qatorlarni to'g'ri tartibga tering",
        "Tartib va surilish",
        "puzzle",
        "tone-cyan",
        "portal/play_puzzle.html",
        "portal-puzzle.js",
        puzzle.CHAPTERS,
        puzzle.attempt,
        puzzle.config,
        "Oson",
        lambda level: level.answer,
    ),
    Game(
        "detektiv",
        "Kod detektivi",
        "Kod nima chiqarishini 3 ta jon bilan toping",
        "Kod o'qish",
        "search-code",
        "tone-amber",
        "portal/play_quiz.html",
        "portal-quiz.js",
        quiz.CHAPTERS,
        quiz.attempt,
        quiz.config,
    ),
    Game(
        "rassom",
        "Kod rassomi",
        "Qalamni boshqaring va namunadagi rasmni chizing",
        "Sikl va burchak",
        "palette",
        "tone-violet",
        "portal/play_draw.html",
        "portal-draw.js",
        draw.CHAPTERS,
        draw.attempt,
        draw.config,
        "O'rta",
        lambda level: level.solution,
    ),
    Game(
        "mashina",
        "Sehrli mashina",
        "Son kirsin, to'g'ri javob chiqsin: funksiya yozing",
        "Funksiya",
        "cog",
        "tone-emerald",
        "portal/play_machine.html",
        "portal-machine.js",
        machine.CHAPTERS,
        machine.attempt,
        machine.config,
        "Qiyin",
        lambda level: level.solution,
    ),
    Game(
        "xato",
        "Xato ovchisi",
        "Buzilgan kodni eng kam o'zgartirish bilan tuzating",
        "Xato topish",
        "bug",
        "tone-rose",
        "portal/play.html",
        "portal-game.js",
        bugs.CHAPTERS,
        bugs.attempt,
        _bug_config,
        "Qiyin",
        lambda level: solutions.FIXES[level.slug],
    ),
)

GAME_BY_SLUG: dict[str, Game] = {game.slug: game for game in GAMES}
EVERY_LEVEL: tuple = tuple(level for game in GAMES for level in game.levels)
BY_SLUG: dict = {level.slug: level for level in EVERY_LEVEL}
GAME_OF: dict[str, Game] = {level.slug: game for game in GAMES for level in game.levels}
CHAPTER_OF: dict = {level.slug: chapter for game in GAMES for chapter in game.chapters for level in chapter.levels}
TOTAL_LEVELS = len(EVERY_LEVEL)
MAX_XP = TOTAL_LEVELS * 3 * robot.XP_PER_STAR

__all__ = ["BY_SLUG", "BadPayload", "CHAPTER_OF", "EVERY_LEVEL", "GAMES", "GAME_BY_SLUG", "GAME_OF", "MAX_XP"]
