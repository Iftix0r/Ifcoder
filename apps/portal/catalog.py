"""Hamma o'yinlar ro'yxati. Har bir bosqich ``slug`` i butun portal bo'yicha yagona: natija shu nom bilan saqlanadi."""

from collections.abc import Callable
from dataclasses import dataclass

from . import engine
from . import levels as robot
from .games import BadPayload, bugs, code_from, draw, machine, puzzle, quiz


def _robot_attempt(level, payload, attempts) -> dict:
    code = code_from(payload)
    return {**robot.attempt(level, code), "stored": code}


def _robot_config(level, row) -> dict:
    return {
        "world": engine.World(level.maps[0]).as_dict(),
        "code": row.code if row and row.code else level.starter,
        "starter": level.starter,
        "maps": len(level.maps),
    }


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

    @property
    def levels(self) -> tuple:
        return tuple(level for chapter in self.chapters for level in chapter.levels)


GAMES: tuple[Game, ...] = (
    Game(
        "robot",
        "Robot yo'li",
        "Robotni kod bilan labirintdan olib chiqing",
        "Algoritm",
        "bot",
        "tone-brand",
        "portal/play.html",
        "portal-game.js",
        robot.CHAPTERS,
        _robot_attempt,
        _robot_config,
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
        _robot_config,
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
