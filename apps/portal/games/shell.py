"""Terminal o'yini: haqiqiy Linux buyruqlari, lekin hammasi xayoliy kompyuterda.

MUHIM: bu fayl hech qanday haqiqiy buyruq bajarmaydi. Fayl tizimi oddiy lug'at, ``os``, ``subprocess`` va ``open``
ishlatilmaydi va ishlatilmasin: o'quvchi yozgan matn saytning serveriga yetib bormasligi shart.

Server holat saqlamaydi: brauzer yozilgan buyruqlarning hammasini yuboradi, simulyator ularni boshidan takrorlaydi.
"""

import difflib
import fnmatch
import posixpath
import shlex
from collections.abc import Callable
from dataclasses import dataclass

from ..levels import Chapter
from . import BadPayload

HOME = "/home/bola"
USER = "bola"
HOST = "kema"
MAX_COMMANDS = 80
MAX_LINE = 300
MAX_OUTPUT = 200
MAX_FILE = 20_000

MANUAL = {
    "pwd": "Hozir qaysi papkada ekanini ko'rsatadi.",
    "ls": "Papka ichini ko'rsatadi. -a yashirinlarni, -l batafsil.",
    "cd": "Boshqa papkaga o'tadi. cd .. bir pog'ona yuqoriga, cd ~ uyga.",
    "cat": "Fayl ichini ko'rsatadi.",
    "echo": "Matnni chiqaradi. > bilan faylga yozadi, >> bilan oxiriga qo'shadi.",
    "touch": "Bo'sh fayl yaratadi.",
    "mkdir": "Yangi papka yaratadi.",
    "rm": "Faylni o'chiradi. -r papkani ichi bilan. Qaytarib bo'lmaydi!",
    "cp": "Nusxa oladi: cp eski yangi",
    "mv": "Ko'chiradi yoki nomini o'zgartiradi: mv eski yangi",
    "grep": "Faylda so'z qidiradi: grep so'z fayl. -i katta-kichik farqsiz, -c sanaydi.",
    "head": "Faylning boshini ko'rsatadi: head -n 3 fayl",
    "tail": "Faylning oxirini ko'rsatadi: tail -n 3 fayl",
    "wc": "Sanaydi. wc -l qatorlarni.",
    "sort": "Qatorlarni tartiblaydi.",
    "uniq": "Ketma-ket takrorlanganlarni olib tashlaydi.",
    "find": "Fayl qidiradi: find . -name '*.txt'",
    "chmod": "Ruxsatni o'zgartiradi: chmod +x fayl ishga tushadigan qiladi.",
    "tree": "Papkalarni daraxt ko'rinishida chiqaradi.",
    "history": "Yozilgan buyruqlarni ko'rsatadi.",
    "whoami": "Kim bo'lib kirganingizni ko'rsatadi.",
    "clear": "Ekranni tozalaydi.",
    "man": "Buyruq haqida ma'lumot beradi: man ls",
}


# shlex qo'shtirnoqni olib tashlaydi, lekin '*.txt' ochilmasligi kerak: bunday belgilar vaqtincha yashiriladi
GUARD = str.maketrans({"*": "\x01", "?": "\x02"})
UNGUARD = str.maketrans({"\x01": "*", "\x02": "?"})


def _guard_quoted(line: str) -> str:
    result, quote = [], ""
    for char in line:
        if quote:
            quote = "" if char == quote else quote
            result.append(char.translate(GUARD))
        else:
            quote = char if char in "\"'" else ""
            result.append(char)
    return "".join(result)


class ShellError(Exception):
    def __init__(self, message: str, tip: str = ""):
        super().__init__(message)
        self.message = message
        self.tip = tip


class Shell:
    def __init__(self, files: dict[str, str], start: str = HOME, executable: tuple[str, ...] = ()):
        self.dirs = {"/", "/home", HOME, "/tmp"}
        self.files: dict[str, str] = {}
        self.executable = set(executable)
        self.cwd = start
        self.dirs.add(start)
        self.history: list[str] = []
        self.line = ""
        self.out = ""
        self.ok = True
        self.tip = ""
        self.cleared = False
        for path, content in files.items():
            if path.endswith("/"):
                self._make_parents(path.rstrip("/") + "/x")
                self.dirs.add(path.rstrip("/"))
            else:
                self._make_parents(path)
                self.files[path] = content
        self._make_parents(start + "/x")
        self.commands: dict[str, Callable] = {
            "pwd": self._pwd,
            "ls": self._ls,
            "cd": self._cd,
            "cat": self._cat,
            "echo": self._echo,
            "touch": self._touch,
            "mkdir": self._mkdir,
            "rm": self._rm,
            "cp": self._cp,
            "mv": self._mv,
            "grep": self._grep,
            "head": self._head,
            "tail": self._tail,
            "wc": self._wc,
            "sort": self._sort,
            "uniq": self._uniq,
            "find": self._find,
            "chmod": self._chmod,
            "tree": self._tree,
            "history": self._history,
            "whoami": lambda args, stdin: USER,
            "hostname": lambda args, stdin: HOST,
            "date": lambda args, stdin: "Sat Nov  7 12:00:00 UTC 2126",
            "clear": self._clear,
            "man": self._man,
            "help": self._help,
            "sudo": self._sudo,
        }

    # --- Yo'llar ---

    def _make_parents(self, path: str) -> None:
        parent = posixpath.dirname(path)
        while parent not in self.dirs:
            self.dirs.add(parent)
            parent = posixpath.dirname(parent)

    def resolve(self, path: str) -> str:
        if path == "~" or path.startswith("~/"):
            path = HOME + path[1:]
        full = posixpath.normpath(posixpath.join(self.cwd, path))
        return "/" + full.lstrip("/")

    def exists(self, path: str) -> bool:
        full = self.resolve(path)
        return full in self.dirs or full in self.files

    def read(self, path: str) -> str:
        return self.files.get(self.resolve(path), "")

    def children(self, folder: str) -> list[str]:
        prefix = folder.rstrip("/") + "/"
        found = {
            path[len(prefix) :].split("/")[0]
            for path in (*self.dirs, *self.files)
            if path.startswith(prefix) and path != prefix
        }
        return sorted(found)

    def _expand(self, args: list[str]) -> list[str]:
        result = []
        for arg in args:
            if "*" not in arg and "?" not in arg:
                result.append(arg.translate(UNGUARD))
                continue
            folder, pattern = posixpath.split(arg)
            names = [n for n in self.children(self.resolve(folder or ".")) if not n.startswith(".")]
            matched = [posixpath.join(folder, n) for n in names if fnmatch.fnmatchcase(n, pattern)]
            result += matched or [arg]
        return result

    def _need_file(self, name: str, path: str) -> str:
        full = self.resolve(path)
        if full in self.dirs:
            raise ShellError(f"{name}: {path}: Is a directory", "Bu papka, fayl emas. Ichini ko'rish uchun ls yozing.")
        if full not in self.files:
            raise ShellError(
                f"{name}: {path}: No such file or directory", "Bunday fayl yo'q. Nomini ls bilan tekshiring."
            )
        return full

    @staticmethod
    def _flags(name: str, args: list[str], allowed: str) -> tuple[set[str], list[str]]:
        flags, rest = set(), []
        for arg in args:
            if arg.startswith("-") and len(arg) > 1 and not arg[1].isdigit():
                for letter in arg[1:]:
                    if letter not in allowed:
                        raise ShellError(f"{name}: invalid option -- '{letter}'", f"{name} da -{letter} yo'q.")
                    flags.add(letter)
            else:
                rest.append(arg)
        return flags, rest

    def _write(self, path: str, text: str, append: bool) -> None:
        full = self.resolve(path)
        if full in self.dirs:
            raise ShellError(f"bash: {path}: Is a directory", "Papkaga yozib bo'lmaydi, fayl nomini bering.")
        if posixpath.dirname(full) not in self.dirs:
            raise ShellError(
                f"bash: {path}: No such file or directory", "Bunday papka yo'q. Avval mkdir bilan yarating."
            )
        content = (self.files.get(full, "") if append else "") + text
        self.files[full] = content[:MAX_FILE]

    # --- Bajarish ---

    def run(self, line: str) -> None:
        """Natija ``out``, ``tip``, ``ok`` da qoladi. Hech qachon istisno chiqarmaydi."""
        self.line = line.strip()
        self.out, self.tip, self.ok, self.cleared = "", "", True, False
        if not self.line:
            return
        self.history.append(self.line)
        try:
            lexer = shlex.shlex(_guard_quoted(self.line), posix=True, punctuation_chars="|>;&")
            lexer.whitespace_split = True
            lexer.commenters = ""
            tokens = list(lexer)
        except ValueError:
            self._fail("bash: unexpected EOF while looking for matching quote", "Qo'shtirnoq yopilmagan.")
            return
        output = []
        try:
            for part in self._sequence(tokens):
                text = self._pipeline(part)
                if text:
                    output.append(text)
        except ShellError as error:
            output.append(error.message)
            self.ok = False
            self.tip = error.tip
        lines = "\n".join(output).split("\n")
        self.out = "\n".join(lines[:MAX_OUTPUT])

    def _fail(self, message: str, tip: str) -> None:
        self.out, self.tip, self.ok = message, tip, False

    @staticmethod
    def _sequence(tokens: list[str]) -> list[list[str]]:
        parts, current = [], []
        for token in tokens:
            if token in (";", "&&"):
                parts.append(current)
                current = []
            else:
                current.append(token)
        parts.append(current)
        return [part for part in parts if part]

    def _pipeline(self, tokens: list[str]) -> str:
        stages, current = [], []
        for token in tokens:
            if token == "|":
                stages.append(current)
                current = []
            else:
                current.append(token)
        stages.append(current)
        if not all(stages):
            raise ShellError("bash: syntax error near unexpected token `|'", "| ning ikki tomonida buyruq bo'lsin.")
        target, append = None, False
        last = stages[-1]
        for mark in (">>", ">"):
            if mark in last:
                index = last.index(mark)
                if index + 2 != len(last):
                    raise ShellError(
                        "bash: syntax error near unexpected token `newline'", f"{mark} dan keyin fayl nomi yozing."
                    )
                target, append = last[index + 1].translate(UNGUARD), mark == ">>"
                stages[-1] = last[:index]
                break
        data = None
        for stage in stages:
            data = self._command(stage, data)
        if target is None:
            return data or ""
        self._write(target, (data or "") + "\n", append)
        return ""

    def _command(self, stage: list[str], stdin: str | None) -> str:
        name, *args = stage
        name = name.translate(UNGUARD)
        args = self._expand(args)
        if name.startswith(("./", "/", "~/")):
            return self._execute(name)
        command = self.commands.get(name)
        if command is None:
            close = difflib.get_close_matches(name, self.commands, n=1, cutoff=0.6)
            tip = f"Balki {close[0]}?" if close else "Bunday buyruq yo'q. help yozib ko'ring."
            raise ShellError(f"bash: {name}: command not found", tip)
        return command(args, stdin) or ""

    def _execute(self, name: str) -> str:
        full = self._need_file("bash", name)
        if full not in self.executable:
            raise ShellError(f"bash: {name}: Permission denied", "Avval ruxsat bering: chmod +x fayl")
        lines = [line[5:].strip("\"' ") for line in self.files[full].splitlines() if line.startswith("echo ")]
        return "\n".join(lines)

    # --- Buyruqlar ---

    def _pwd(self, args, stdin):
        return self.cwd

    def _ls(self, args, stdin):
        flags, paths = self._flags("ls", args, "al")
        results = []
        for path in paths or ["."]:
            full = self.resolve(path)
            if full in self.files:
                results.append(path)
                continue
            if full not in self.dirs:
                raise ShellError(f"ls: cannot access '{path}': No such file or directory", "Bunday papka yo'q.")
            names = [n for n in self.children(full) if "a" in flags or not n.startswith(".")]
            if "l" in flags:
                results += [self._long(posixpath.join(full, n), n) for n in names]
            else:
                results.append("  ".join(names))
        return "\n".join(results)

    def _long(self, path: str, name: str) -> str:
        if path in self.dirs:
            return f"drwxr-xr-x  {USER}  {name}/"
        mode = "-rwxr-xr-x" if path in self.executable else "-rw-r--r--"
        return f"{mode}  {USER}  {len(self.files[path]):>5}  {name}"

    def _cd(self, args, stdin):
        path = args[0] if args else "~"
        full = self.resolve(path)
        if full in self.files:
            raise ShellError(
                f"bash: cd: {path}: Not a directory", "Bu fayl. cd faqat papkaga kiradi, faylni cat bilan o'qing."
            )
        if full not in self.dirs:
            raise ShellError(f"bash: cd: {path}: No such file or directory", "Bunday papka yo'q. ls bilan tekshiring.")
        self.cwd = full
        return ""

    def _cat(self, args, stdin):
        if not args:
            return stdin or ""
        return "\n".join(self.files[self._need_file("cat", path)].rstrip("\n") for path in args)

    def _echo(self, args, stdin):
        return " ".join(args)

    def _touch(self, args, stdin):
        if not args:
            raise ShellError("touch: missing file operand", "Fayl nomini yozing: touch fayl.txt")
        for path in args:
            if not self.exists(path):
                self._write(path, "", False)
        return ""

    def _mkdir(self, args, stdin):
        flags, paths = self._flags("mkdir", args, "p")
        if not paths:
            raise ShellError("mkdir: missing operand", "Papka nomini yozing: mkdir papka")
        for path in paths:
            full = self.resolve(path)
            if self.exists(path):
                if "p" in flags:
                    continue
                raise ShellError(f"mkdir: cannot create directory '{path}': File exists", "Bunday nom allaqachon bor.")
            if posixpath.dirname(full) not in self.dirs:
                if "p" not in flags:
                    raise ShellError(
                        f"mkdir: cannot create directory '{path}': No such file or directory",
                        "Ichma-ich papka uchun -p qo'shing.",
                    )
                self._make_parents(full)
            self.dirs.add(full)
        return ""

    def _rm(self, args, stdin):
        flags, paths = self._flags("rm", args, "rf")
        if not paths:
            raise ShellError("rm: missing operand", "Nimani o'chirish kerak? rm fayl")
        for path in paths:
            full = self.resolve(path)
            if full == "/":
                raise ShellError(
                    "rm: it is dangerous to operate recursively on '/'",
                    "Haqiqiy kompyuterda bu buyruq hammasini o'chiradi! Hech qachon yozmang.",
                )
            if full in self.dirs:
                if "r" not in flags:
                    raise ShellError(
                        f"rm: cannot remove '{path}': Is a directory", "Papka uchun -r qo'shing: rm -r papka"
                    )
                prefix = full + "/"
                self.dirs = {d for d in self.dirs if d != full and not d.startswith(prefix)}
                self.files = {f: c for f, c in self.files.items() if not f.startswith(prefix)}
                if self.cwd == full or self.cwd.startswith(prefix):
                    self.cwd = posixpath.dirname(full)
            elif full in self.files:
                del self.files[full]
                self.executable.discard(full)
            elif "f" not in flags:
                raise ShellError(f"rm: cannot remove '{path}': No such file or directory", "Bunday fayl yo'q.")
        return ""

    def _destination(self, name: str, source: str, target: str) -> str:
        full = self.resolve(target)
        return posixpath.join(full, posixpath.basename(source)) if full in self.dirs else full

    def _two_paths(self, name: str, paths: list[str]) -> tuple[str, str]:
        if len(paths) != 2:
            raise ShellError(f"{name}: missing destination file operand", f"Ikkita nom kerak: {name} eski yangi")
        return paths[0], paths[1]

    def _copy_tree(self, source: str, target: str) -> None:
        prefix = source + "/"
        self.dirs.add(target)
        for folder in [d for d in self.dirs if d.startswith(prefix)]:
            self.dirs.add(target + folder[len(source) :])
        for path, content in [(p, c) for p, c in self.files.items() if p.startswith(prefix)]:
            self.files[target + path[len(source) :]] = content

    def _cp(self, args, stdin):
        flags, paths = self._flags("cp", args, "r")
        first, second = self._two_paths("cp", paths)
        source = self.resolve(first)
        target = self._destination("cp", source, second)
        if source in self.dirs:
            if "r" not in flags:
                raise ShellError(
                    f"cp: -r not specified; omitting directory '{first}'", "Papka uchun: cp -r papka yangi"
                )
            if target == source or target.startswith(source + "/"):
                raise ShellError(
                    f"cp: cannot copy a directory, '{first}', into itself", "Papkani o'z ichiga ko'chirib bo'lmaydi."
                )
            self._copy_tree(source, target)
            return ""
        full = self._need_file("cp", first)
        if posixpath.dirname(target) not in self.dirs:
            raise ShellError(
                f"cp: cannot create regular file '{second}': No such file or directory", "Bunday papka yo'q."
            )
        self.files[target] = self.files[full]
        return ""

    def _mv(self, args, stdin):
        first, second = self._two_paths("mv", args)
        source = self.resolve(first)
        target = self._destination("mv", source, second)
        if source in self.dirs:
            if target == source or target.startswith(source + "/") or source == "/":
                raise ShellError(
                    f"mv: cannot move '{first}' to a subdirectory of itself", "Papkani o'z ichiga ko'chirib bo'lmaydi."
                )
            self._copy_tree(source, target)
            self._rm(["-r", first], None)
            return ""
        full = self._need_file("mv", first)
        if posixpath.dirname(target) not in self.dirs:
            raise ShellError(
                f"mv: cannot move '{first}' to '{second}': No such file or directory", "Bunday papka yo'q."
            )
        self.files[target] = self.files.pop(full)
        if full in self.executable:
            self.executable.discard(full)
            self.executable.add(target)
        return ""

    def _input(self, name: str, paths: list[str], stdin: str | None) -> str:
        if paths:
            return "\n".join(self.files[self._need_file(name, path)].rstrip("\n") for path in paths)
        if stdin is None:
            raise ShellError(f"{name}: missing file operand", f"Fayl nomini yozing yoki | bilan bering: {name} fayl")
        return stdin

    def _grep(self, args, stdin):
        flags, rest = self._flags("grep", args, "incv")
        if not rest:
            raise ShellError("usage: grep PATTERN [FILE]", "Nima qidiramiz? grep so'z fayl")
        word, *paths = rest
        lines = self._input("grep", paths, stdin).split("\n")
        needle = word.lower() if "i" in flags else word
        found = []
        for number, line in enumerate(lines, 1):
            haystack = line.lower() if "i" in flags else line
            if (needle in haystack) != ("v" in flags):
                found.append(f"{number}:{line}" if "n" in flags else line)
        return str(len(found)) if "c" in flags else "\n".join(found)

    @staticmethod
    def _count(args: list[str]) -> tuple[int, list[str]]:
        count, rest, index = 10, [], 0
        while index < len(args):
            arg = args[index]
            if arg == "-n" and index + 1 < len(args) and args[index + 1].isdigit():
                count = int(args[index + 1])
                index += 1
            elif arg.startswith("-") and arg[1:].isdigit():
                count = int(arg[1:])
            else:
                rest.append(arg)
            index += 1
        return count, rest

    def _head(self, args, stdin):
        count, paths = self._count(args)
        return "\n".join(self._input("head", paths, stdin).split("\n")[:count])

    def _tail(self, args, stdin):
        count, paths = self._count(args)
        lines = self._input("tail", paths, stdin).split("\n")
        return "\n".join(lines[-count:] if count else [])

    def _wc(self, args, stdin):
        flags, paths = self._flags("wc", args, "lwc")
        text = self._input("wc", paths, stdin)
        lines = len(text.split("\n")) if text else 0
        value = len(text.split()) if "w" in flags else len(text) if "c" in flags else lines
        return f"{value} {paths[0]}" if paths else str(value)

    def _sort(self, args, stdin):
        flags, paths = self._flags("sort", args, "r")
        return "\n".join(sorted(self._input("sort", paths, stdin).split("\n"), reverse="r" in flags))

    def _uniq(self, args, stdin):
        result = []
        for line in self._input("uniq", args, stdin).split("\n"):
            if not result or result[-1] != line:
                result.append(line)
        return "\n".join(result)

    def _find(self, args, stdin):
        pattern = None
        start = "."
        if "-name" in args:
            index = args.index("-name")
            if index + 1 >= len(args):
                raise ShellError("find: missing argument to `-name'", "Nom yozing: find . -name '*.txt'")
            pattern = args[index + 1]
            args = args[:index] + args[index + 2 :]
        if args:
            start = args[0]
        root = self.resolve(start)
        if root not in self.dirs:
            raise ShellError(f"find: '{start}': No such file or directory", "Bunday papka yo'q.")
        prefix = root.rstrip("/") + "/"
        found = []
        for path in sorted({*self.dirs, *self.files}):
            if path == root or path.startswith(prefix):
                if pattern is None or fnmatch.fnmatchcase(posixpath.basename(path), pattern):
                    found.append(start.rstrip("/") + path[len(root.rstrip("/")) :] if path != root else start)
        return "\n".join(found)

    def _chmod(self, args, stdin):
        if len(args) < 2:
            raise ShellError("chmod: missing operand", "Masalan: chmod +x fayl")
        mode, *paths = args
        for path in paths:
            full = self._need_file("chmod", path)
            if mode in ("+x", "u+x", "a+x") or (mode.isdigit() and int(mode[0]) & 1):
                self.executable.add(full)
            elif mode in ("-x", "u-x", "a-x") or mode.isdigit():
                self.executable.discard(full)
            else:
                raise ShellError(f"chmod: invalid mode: '{mode}'", "Masalan: chmod +x fayl")
        return ""

    def _tree(self, args, stdin):
        root = self.resolve(args[0]) if args else self.cwd
        return "\n".join([".", *[f"{'    ' * row['depth']}{row['name']}" for row in self.listing(root)]])

    def listing(self, root: str = "/home/bola", depth: int = 0) -> list[dict]:
        rows = []
        for name in self.children(root):
            if name.startswith("."):
                continue
            path = root.rstrip("/") + "/" + name
            folder = path in self.dirs
            rows.append({"name": name, "path": path, "depth": depth, "dir": folder})
            if folder:
                rows += self.listing(path, depth + 1)
        return rows

    def _history(self, args, stdin):
        return "\n".join(f"{number:>4}  {line}" for number, line in enumerate(self.history, 1))

    def _clear(self, args, stdin):
        self.cleared = True
        return ""

    def _man(self, args, stdin):
        if not args:
            raise ShellError("What manual page do you want?", "Masalan: man ls")
        return MANUAL.get(args[0]) or f"No manual entry for {args[0]}"

    def _help(self, args, stdin):
        return "\n".join(f"{name:<8} {text}" for name, text in MANUAL.items())

    def _sudo(self, args, stdin):
        raise ShellError(
            f"{USER} is not in the sudoers file.", "sudo administrator huquqi beradi. Bu o'yinda kerak emas."
        )

    # --- O'yin uchun ---

    @property
    def prompt(self) -> str:
        path = "~" + self.cwd[len(HOME) :] if self.cwd == HOME or self.cwd.startswith(HOME + "/") else self.cwd
        return f"{USER}@{HOST}:{path}$"

    def names(self) -> list[str]:
        """Tab uchun: hozirgi papkadan pastdagi hamma nisbiy yo'llar, papkalar «/» bilan."""
        prefix = self.cwd.rstrip("/") + "/"
        folders = [d[len(prefix) :] + "/" for d in self.dirs if d.startswith(prefix)]
        files = [f[len(prefix) :] for f in self.files if f.startswith(prefix)]
        return sorted([*folders, *files])

    def did(self, start: str) -> bool:
        return self.ok and " ".join(self.line.split()).startswith(start)


@dataclass(frozen=True)
class Step:
    task: str
    teach: str
    example: str
    check: Callable[[Shell], bool]


@dataclass(frozen=True)
class ShellLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    files: tuple[tuple[str, str], ...]
    steps: tuple[Step, ...]
    solution: tuple[str, ...]
    start: str = HOME
    executable: tuple[str, ...] = ()
    hint: str = ""
    example: str = ""


def boot(level: ShellLevel) -> Shell:
    return Shell(dict(level.files), level.start, level.executable)


def stars_for(commands: int, par: int) -> int:
    if commands <= par + 2:
        return 3
    return 2 if commands <= par + 7 else 1


def attempt(level: ShellLevel, payload: dict, attempts: int) -> dict:
    commands = payload.get("commands")
    if not isinstance(commands, list) or not 1 <= len(commands) <= MAX_COMMANDS:
        raise BadPayload
    if any(not isinstance(line, str) or len(line) > MAX_LINE for line in commands):
        raise BadPayload
    shell = boot(level)
    step = 0
    advanced = False
    for line in commands:
        shell.run(line)
        advanced = False
        if step < len(level.steps) and level.steps[step].check(shell):
            step += 1
            advanced = True
    finished = step == len(level.steps)
    typed = sum(bool(line.strip()) for line in commands)
    return {
        "ok": finished,
        "stars": stars_for(typed, len(level.solution)) if finished else 0,
        "out": shell.out,
        "tip": shell.tip,
        "failed_command": not shell.ok,
        "clear": shell.cleared,
        "prompt": shell.prompt,
        "cwd": shell.cwd,
        "step": step,
        "advanced": advanced,
        "tree": shell.listing(),
        "names": shell.names(),
        "finished": finished,
        "partial": not finished,
        "stored": "\n".join(commands),
        "message": "Tizim tiklandi!" if finished else "",
    }


def config(level: ShellLevel, row) -> dict:
    shell = boot(level)
    return {
        "steps": [{"task": s.task, "teach": s.teach, "example": s.example} for s in level.steps],
        "prompt": shell.prompt,
        "cwd": shell.cwd,
        "tree": shell.listing(),
        "names": shell.names(),
        "commands": sorted(shell.commands),
    }


NOTE = "Salom, muhandis! Kema kompyuteri buzildi. Faqat terminal ishlayapti. Bizga yordam bering!\n"
LOG = (
    "08:00 OK dvigatel ishga tushdi\n"
    "08:05 XATO yoqilg'i bosimi past\n"
    "08:10 OK aloqa tiklandi\n"
    "08:15 XATO kislorod sensori\n"
    "08:20 OK navigatsiya\n"
    "08:25 XATO radar javob bermayapti\n"
    "08:30 OK harorat normal\n"
)
CREW = "Zebo\nAli\nVali\nAli\nZebo\nSardor\n"
HOME_FILES = (
    (f"{HOME}/xabar.txt", NOTE),
    (f"{HOME}/xarita/yulduzlar.txt", "Mars\nYupiter\nSaturn\n"),
    (f"{HOME}/dvigatel/holat.txt", "Dvigatel: tayyor\n"),
)

BASICS = ("ls", "pwd", "cd ", "cd ..", "cat ", "ls -a", "whoami")
FILES = ("ls", "cd ", "cat ", "mkdir ", "touch ", "cp ", "mv ", "rm ", "rm -r ", "echo ", ">", ">>")
SEARCH = ("ls", "cat ", "grep ", "|", "wc -l", "sort", "uniq", "head ", "tail ", "find . -name ", "chmod +x ", "./")

CHAPTERS = (
    Chapter(
        "yol",
        "Kemada yo'l topish",
        "Qayerdaman? Atrofda nima bor? Qanday o'taman?",
        "tone-emerald",
        BASICS,
        (
            ShellLevel(
                "term-salom",
                "Uyg'onish",
                "Tizimga kirdingiz. Atrofni o'rganing.",
                "Terminal — kompyuterga so'z bilan buyruq berish oynasi. Buyruqni yozib Enter bosasiz.",
                HOME_FILES,
                (
                    Step(
                        "Kim ekaningizni bilib oling.",
                        "whoami — «men kimman?» degani. Kompyuter foydalanuvchi nomini aytadi.",
                        "whoami",
                        lambda s: s.did("whoami"),
                    ),
                    Step(
                        "Hozir qaysi papkada ekaningizni toping.",
                        "pwd — print working directory: hozirgi papka manzilini chiqaradi.",
                        "pwd",
                        lambda s: s.did("pwd"),
                    ),
                    Step(
                        "Papka ichida nima borligini ko'ring.",
                        "ls — list: papkadagi fayl va papkalarni ko'rsatadi.",
                        "ls",
                        lambda s: s.did("ls"),
                    ),
                ),
                ("whoami", "pwd", "ls"),
            ),
            ShellLevel(
                "term-cd",
                "Xonalar bo'ylab",
                "Papkalar orasida yuring.",
                "Papka — xona, cd — eshikdan o'tish. cd .. orqaga, bir xona yuqoriga qaytaradi.",
                HOME_FILES,
                (
                    Step(
                        "xarita papkasiga kiring.",
                        "cd — change directory: papkaga o'tadi. Yozuvchi satr o'zgarganini ko'ring!",
                        "cd xarita",
                        lambda s: s.cwd == f"{HOME}/xarita",
                    ),
                    Step(
                        "Bu papka ichini ko'ring.",
                        "ls hozir turgan papkangizni ko'rsatadi, boshqa papkada boshqacha natija chiqadi.",
                        "ls",
                        lambda s: s.did("ls") and s.cwd == f"{HOME}/xarita",
                    ),
                    Step(
                        "Bir papka yuqoriga qayting.",
                        "Ikki nuqta (..) yuqoridagi papka degani. cd va .. orasida bo'sh joy bor!",
                        "cd ..",
                        lambda s: s.cwd == HOME,
                    ),
                    Step(
                        "Endi dvigatel papkasiga kiring.",
                        "Yozishni boshlang va Tab bosing: terminal nomni o'zi to'ldiradi. Dasturchilar shunday qiladi.",
                        "cd dvigatel",
                        lambda s: s.cwd == f"{HOME}/dvigatel",
                    ),
                ),
                ("cd xarita", "ls", "cd ..", "cd dvigatel"),
            ),
            ShellLevel(
                "term-cat",
                "Yashirin xabar",
                "Faylni o'qing va yashirin faylni toping.",
                "cat fayl ichini ko'rsatadi. Nuqta bilan boshlangan fayl yashirin: oddiy ls uni ko'rsatmaydi.",
                (*HOME_FILES, (f"{HOME}/.maxfiy", "Maxfiy kod: ORION-7\n")),
                (
                    Step(
                        "xabar.txt faylini o'qing.",
                        "cat fayl ichini ekranga chiqaradi. cat dan keyin fayl nomini yozing.",
                        "cat xabar.txt",
                        lambda s: s.did("cat") and "muhandis" in s.out,
                    ),
                    Step(
                        "Yashirin fayllarni ham ko'ring.",
                        "-a bu bayroq: buyruqqa qo'shimcha ko'rsatma. ls -a hammasini (all) ko'rsatadi.",
                        "ls -a",
                        lambda s: s.ok and ".maxfiy" in s.out,
                    ),
                    Step(
                        "Yashirin faylni o'qing.",
                        "Nomini aniq yozing, boshidagi nuqta bilan birga.",
                        "cat .maxfiy",
                        lambda s: "ORION-7" in s.out,
                    ),
                ),
                ("cat xabar.txt", "ls -a", "cat .maxfiy"),
            ),
            ShellLevel(
                "term-yol",
                "To'liq manzil",
                "Adashib qoldingiz. Uyga qayting.",
                "Har faylning to'liq manzili bor: /home/bola/xarita. Boshidagi / — eng yuqori papka. ~ — uyingiz.",
                HOME_FILES,
                (
                    Step(
                        "Qayerda ekaningizni tekshiring.",
                        "Adashganda birinchi ish: pwd.",
                        "pwd",
                        lambda s: s.did("pwd"),
                    ),
                    Step(
                        "Uyga qayting.",
                        "~ (tilda) uy papkangiz. cd ~ qayerda bo'lsangiz ham uyga olib boradi.",
                        "cd ~",
                        lambda s: s.cwd == HOME,
                    ),
                    Step(
                        "Eng yuqori papkaga o'ting.",
                        "/ — ildiz: hamma papkalar shu yerdan boshlanadi.",
                        "cd /",
                        lambda s: s.cwd == "/",
                    ),
                    Step(
                        "Bir buyruq bilan xarita papkasiga o'ting.",
                        "To'liq yo'l yozsangiz, bir qadamda yetib borasiz.",
                        "cd ~/xarita",
                        lambda s: s.cwd == f"{HOME}/xarita",
                    ),
                ),
                ("pwd", "cd ~", "cd /", "cd ~/xarita"),
                start="/tmp/chiqindi/eski",
            ),
        ),
    ),
    Chapter(
        "fayllar",
        "Omborda ish",
        "Yaratish, nusxalash, ko'chirish, o'chirish",
        "tone-cyan",
        FILES,
        (
            ShellLevel(
                "term-yarat",
                "Yangi ombor",
                "Yuklar uchun joy tayyorlang.",
                "mkdir papka yaratadi, touch bo'sh fayl yaratadi.",
                HOME_FILES,
                (
                    Step(
                        "ombor nomli papka yarating.",
                        "mkdir — make directory.",
                        "mkdir ombor",
                        lambda s: s.exists(f"{HOME}/ombor"),
                    ),
                    Step(
                        "Unga kiring.",
                        "Yangi papka ham oddiy papka: cd bilan kiriladi.",
                        "cd ombor",
                        lambda s: s.cwd == f"{HOME}/ombor",
                    ),
                    Step(
                        "yuk.txt nomli bo'sh fayl yarating.",
                        "touch fayl bo'lmasa, bo'sh fayl yaratadi.",
                        "touch yuk.txt",
                        lambda s: s.exists(f"{HOME}/ombor/yuk.txt"),
                    ),
                    Step(
                        "Fayl paydo bo'lganini tekshiring.",
                        "Har ishdan keyin natijani tekshirish yaxshi odat.",
                        "ls",
                        lambda s: s.did("ls") and "yuk.txt" in s.out,
                    ),
                ),
                ("mkdir ombor", "cd ombor", "touch yuk.txt", "ls"),
            ),
            ShellLevel(
                "term-nusxa",
                "Zaxira",
                "Muhim faylni saqlab qo'ying.",
                "cp nusxa oladi, asli qoladi. mv ko'chiradi, asli yo'qoladi. mv bilan nomni ham o'zgartirish mumkin.",
                (*HOME_FILES, (f"{HOME}/arxiv/.gitkeep", ""), (f"{HOME}/eski.txt", "Eski ma'lumot\n")),
                (
                    Step(
                        "xabar.txt dan zaxira.txt nusxasini oling.",
                        "cp qayerdan qayerga: avval asl fayl, keyin yangi nom.",
                        "cp xabar.txt zaxira.txt",
                        lambda s: s.exists(f"{HOME}/zaxira.txt") and s.exists(f"{HOME}/xabar.txt"),
                    ),
                    Step(
                        "zaxira.txt ni arxiv papkasiga ko'chiring.",
                        "mv oxirgi nom papka bo'lsa, fayl o'sha papkaga tushadi.",
                        "mv zaxira.txt arxiv/",
                        lambda s: s.exists(f"{HOME}/arxiv/zaxira.txt") and not s.exists(f"{HOME}/zaxira.txt"),
                    ),
                    Step(
                        "eski.txt nomini yangi.txt ga o'zgartiring.",
                        "Linux'da alohida «nomini o'zgartirish» buyrug'i yo'q: mv shu ishni bajaradi.",
                        "mv eski.txt yangi.txt",
                        lambda s: s.exists(f"{HOME}/yangi.txt") and not s.exists(f"{HOME}/eski.txt"),
                    ),
                ),
                ("cp xabar.txt zaxira.txt", "mv zaxira.txt arxiv/", "mv eski.txt yangi.txt"),
            ),
            ShellLevel(
                "term-tozala",
                "Katta tozalash",
                "Keraksiz fayllarni o'chiring. Ehtiyot bo'ling!",
                "rm o'chiradi va SAVATCHA YO'Q: o'chgan fayl qaytmaydi. * — istalgan nom degani.",
                (
                    *HOME_FILES,
                    (f"{HOME}/axlat.txt", "keraksiz\n"),
                    (f"{HOME}/a.tmp", ""),
                    (f"{HOME}/b.tmp", ""),
                    (f"{HOME}/c.tmp", ""),
                    (f"{HOME}/eski/1.txt", "1\n"),
                    (f"{HOME}/eski/2.txt", "2\n"),
                ),
                (
                    Step(
                        "axlat.txt faylini o'chiring.",
                        "rm — remove. Haqiqiy kompyuterda o'chirishdan oldin ikki marta o'ylang!",
                        "rm axlat.txt",
                        lambda s: not s.exists(f"{HOME}/axlat.txt"),
                    ),
                    Step(
                        "Hamma .tmp fayllarni bitta buyruq bilan o'chiring.",
                        "*.tmp — oxiri .tmp bilan tugaydigan hamma fayl. * o'rniga istalgan narsa tushadi.",
                        "rm *.tmp",
                        lambda s: not any(s.exists(f"{HOME}/{n}.tmp") for n in "abc"),
                    ),
                    Step(
                        "eski papkasini ichi bilan o'chiring.",
                        "Papka uchun -r kerak (recursive: ichidagilari bilan).",
                        "rm -r eski",
                        lambda s: not s.exists(f"{HOME}/eski"),
                    ),
                ),
                ("rm axlat.txt", "rm *.tmp", "rm -r eski"),
            ),
            ShellLevel(
                "term-yoz",
                "Kapitan kundaligi",
                "Faylga yozing.",
                "> natijani faylga yozadi va eski matnni o'chiradi. >> oxiriga qo'shadi, eskisini saqlaydi.",
                HOME_FILES,
                (
                    Step(
                        "kundalik.txt fayliga «Kun 1» deb yozing.",
                        "echo matnni chiqaradi, > uni ekranga emas, faylga yo'naltiradi.",
                        'echo "Kun 1" > kundalik.txt',
                        lambda s: "Kun 1" in s.read(f"{HOME}/kundalik.txt"),
                    ),
                    Step(
                        "Faylga «Kun 2» ni qo'shing, eskisi o'chmasin.",
                        "Ikkita >> oxiriga qo'shadi. Bitta > bo'lsa, «Kun 1» o'chib ketardi!",
                        'echo "Kun 2" >> kundalik.txt',
                        lambda s: (
                            "Kun 1" in s.read(f"{HOME}/kundalik.txt") and "Kun 2" in s.read(f"{HOME}/kundalik.txt")
                        ),
                    ),
                    Step(
                        "Faylni o'qib tekshiring.",
                        "Ikkala qator ham turganini ko'ring.",
                        "cat kundalik.txt",
                        lambda s: s.did("cat") and "Kun 2" in s.out,
                    ),
                ),
                ('echo "Kun 1" > kundalik.txt', 'echo "Kun 2" >> kundalik.txt', "cat kundalik.txt"),
            ),
        ),
    ),
    Chapter(
        "quvur",
        "Xatoni izlash",
        "Qidiruv va quvur: terminalning kuchi",
        "tone-violet",
        SEARCH,
        (
            ShellLevel(
                "term-grep",
                "Jurnalni tekshirish",
                "Kema jurnalidan xatolarni toping.",
                "Haqiqiy fayllar minglab qatorli bo'ladi. head boshini, tail oxirini, grep kerakli so'zni ko'rsatadi.",
                ((f"{HOME}/kema.log", LOG),),
                (
                    Step(
                        "Jurnalning birinchi 3 qatorini ko'ring.",
                        "head -n 3 boshidan 3 qator ko'rsatadi.",
                        "head -n 3 kema.log",
                        lambda s: s.did("head") and "08:10" in s.out and "08:15" not in s.out,
                    ),
                    Step(
                        "Oxirgi 2 qatorni ko'ring.",
                        "tail oxiridan ko'rsatadi: yangi yozuvlar odatda oxirida bo'ladi.",
                        "tail -n 2 kema.log",
                        lambda s: s.did("tail") and "08:30" in s.out and "08:20" not in s.out,
                    ),
                    Step(
                        "Faqat XATO so'zi bor qatorlarni toping.",
                        "grep faylda so'z qidiradi. Katta-kichik harf farq qiladi!",
                        "grep XATO kema.log",
                        lambda s: s.did("grep") and "kislorod" in s.out and "dvigatel" not in s.out,
                    ),
                ),
                ("head -n 3 kema.log", "tail -n 2 kema.log", "grep XATO kema.log"),
            ),
            ShellLevel(
                "term-quvur",
                "Quvur",
                "Buyruqlarni bir-biriga ulang.",
                "| (quvur) birinchi buyruq natijasini ikkinchisiga uzatadi. Kichik buyruqlardan katta ish yasaladi.",
                ((f"{HOME}/kema.log", LOG), (f"{HOME}/ekipaj.txt", CREW)),
                (
                    Step(
                        "Jurnalda nechta XATO borligini sanang.",
                        "grep topadi, wc -l qatorlarni sanaydi. | ularni ulaydi.",
                        "grep XATO kema.log | wc -l",
                        lambda s: s.ok and "|" in s.line and s.out.strip() == "3",
                    ),
                    Step(
                        "Ekipaj ismlarini alifbo tartibida ko'ring.",
                        "sort qatorlarni tartiblaydi.",
                        "sort ekipaj.txt",
                        lambda s: s.did("sort") and s.out.startswith("Ali\nAli"),
                    ),
                    Step(
                        "Takrorlanmagan ismlar ro'yxatini chiqaring.",
                        "uniq faqat yonma-yon takrorlarni olib tashlaydi, shuning uchun avval sort kerak.",
                        "sort ekipaj.txt | uniq",
                        lambda s: s.ok and s.out.split() == ["Ali", "Sardor", "Vali", "Zebo"],
                    ),
                ),
                ("grep XATO kema.log | wc -l", "sort ekipaj.txt", "sort ekipaj.txt | uniq"),
            ),
            ShellLevel(
                "term-find",
                "Yo'qolgan kalit",
                "Kalit fayli qayerdadir yo'qolgan. Uni toping.",
                "find papkalarni ichma-ich aylanib, nom bo'yicha qidiradi. Nuqta (.) hozirgi papka degani.",
                (
                    *HOME_FILES,
                    (f"{HOME}/ombor/quti/eski/start.key", "Kalit: NEPTUN-42\n"),
                    (f"{HOME}/ombor/quti/ruyxat.txt", "bolt\ngayka\n"),
                ),
                (
                    Step(
                        "Oxiri .key bilan tugaydigan faylni toping.",
                        "Qo'shtirnoq * ni find ga yetkazadi. find . -name degani «shu yerdan nom bo'yicha qidir».",
                        "find . -name '*.key'",
                        lambda s: s.did("find") and "start.key" in s.out,
                    ),
                    Step(
                        "Topilgan faylni o'qing.",
                        "find bergan yo'lni shundayligicha yozing. Tab yordam beradi.",
                        "cat ombor/quti/eski/start.key",
                        lambda s: "NEPTUN-42" in s.out,
                    ),
                ),
                ("find . -name '*.key'", "cat ombor/quti/eski/start.key"),
            ),
            ShellLevel(
                "term-final",
                "Dvigatelni yoqish",
                "Oxirgi vazifa: kemani ishga tushiring!",
                "Linux'da fayl ishga tushishi uchun ruxsat kerak. chmod +x ruxsat beradi, ./fayl ishga tushiradi.",
                (
                    (f"{HOME}/kema.log", LOG),
                    (f"{HOME}/dvigatel/start.sh", 'echo "DVIGATEL ISHGA TUSHDI! Uchdik!"\n'),
                ),
                (
                    Step(
                        "dvigatel papkasiga kiring.",
                        "Hammasi o'rgangan narsangiz.",
                        "cd dvigatel",
                        lambda s: s.cwd == f"{HOME}/dvigatel",
                    ),
                    Step(
                        "Fayl ruxsatlarini ko'ring.",
                        "ls -l batafsil ko'rsatadi. Boshidagi -rw-r--r-- ruxsatlar: x yo'q, demak ishga tushmaydi.",
                        "ls -l",
                        lambda s: s.did("ls") and "-l" in s.line and "start.sh" in s.out,
                    ),
                    Step(
                        "start.sh ga ishga tushish ruxsatini bering.",
                        "chmod — change mode. +x execute: bajarish ruxsati.",
                        "chmod +x start.sh",
                        lambda s: f"{HOME}/dvigatel/start.sh" in s.executable,
                    ),
                    Step(
                        "Dvigatelni ishga tushiring!",
                        "./ «shu papkadagi» degani. Fayl nomi oldidan yoziladi.",
                        "./start.sh",
                        lambda s: "DVIGATEL" in s.out,
                    ),
                ),
                ("cd dvigatel", "ls -l", "chmod +x start.sh", "./start.sh"),
            ),
        ),
    ),
)
