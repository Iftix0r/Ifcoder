"""Robot o'yinining yuragi: o'quvchi yozgan Python kodi shu yerda bajariladi.

Kod ``eval``/``exec`` ga berilmaydi. ``ast`` daraxti faqat ro'yxatdagi tugunlar bo'yicha yuriladi: import,
atribut (``a.b``), ro'yxat, klass va boshqalar shunchaki yo'q. Cheksiz sikl ``MAX_STEPS`` da to'xtaydi.
Natija serverda hisoblanadi, shuning uchun brauzerdan ball soxtalashtirib bo'lmaydi.
"""

import ast
import difflib
import operator
from dataclasses import dataclass, field

MAX_CODE = 3000
MAX_STEPS = 20_000
MAX_ACTIONS = 300
MAX_DEPTH = 40
MAX_NUMBER = 10**12
MAX_PRINTS = 50

# Yuqori, o'ng, past, chap. Ekranda y pastga o'sadi.
DIRECTIONS = ((0, -1), (1, 0), (0, 1), (-1, 0))
START_MARKS = {"^": 0, ">": 1, "v": 2, "<": 3}


class CodeError(Exception):
    def __init__(self, message: str, line: int | None = None):
        super().__init__(message)
        self.message = message
        self.line = line


class World:
    """Xarita belgilari: # devor, . yo'l, * kristall, E manzil, ^ > v < robot va uning yo'nalishi."""

    def __init__(self, rows: tuple[str, ...]):
        self.width = max(len(row) for row in rows)
        self.height = len(rows)
        self.walls: set[tuple[int, int]] = set()
        self.crystals: set[tuple[int, int]] = set()
        self.exit: tuple[int, int] | None = None
        self.x = self.y = self.direction = 0
        for y, row in enumerate(rows):
            for x, mark in enumerate(row):
                if mark == "#":
                    self.walls.add((x, y))
                elif mark == "*":
                    self.crystals.add((x, y))
                elif mark == "E":
                    self.exit = (x, y)
                elif mark in START_MARKS:
                    self.x, self.y, self.direction = x, y, START_MARKS[mark]

    def as_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "walls": sorted(self.walls),
            "crystals": sorted(self.crystals),
            "exit": self.exit,
            "robot": {"x": self.x, "y": self.y, "d": self.direction},
        }

    def blocked(self, turn: int = 0) -> bool:
        dx, dy = DIRECTIONS[(self.direction + turn) % 4]
        x, y = self.x + dx, self.y + dy
        return (x, y) in self.walls or not (0 <= x < self.width and 0 <= y < self.height)

    @property
    def at_exit(self) -> bool:
        return (self.x, self.y) == self.exit

    @property
    def won(self) -> bool:
        return not self.crystals and (self.exit is None or self.at_exit)


@dataclass
class Outcome:
    events: list[dict] = field(default_factory=list)
    won: bool = False
    error: str = ""
    line: int | None = None


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Return(Exception):
    def __init__(self, value):
        self.value = value


@dataclass
class _Function:
    node: ast.FunctionDef


NOT_ALLOWED = {
    ast.Import: "import",
    ast.ImportFrom: "import",
    ast.ClassDef: "class",
    ast.Attribute: "nuqta orqali murojaat (a.b)",
    ast.List: "ro'yxat",
    ast.Dict: "lug'at",
    ast.Tuple: "kortej",
    ast.Set: "to'plam",
    ast.Lambda: "lambda",
    ast.JoinedStr: "f-satr",
    ast.Subscript: "indeks (a[0])",
    ast.Global: "global",
    ast.Nonlocal: "nonlocal",
    ast.Try: "try",
    ast.With: "with",
    ast.Raise: "raise",
    ast.Delete: "del",
}

MATH = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
COMPARE = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


def _explain_syntax(error: SyntaxError) -> str:
    text = (error.msg or "").lower()
    if "expected an indented block" in text:
        return "Ikki nuqtadan (:) keyingi qator 4 ta bo'sh joy bilan surilishi kerak."
    if "unexpected indent" in text:
        return "Bu qator ortiqcha surilgan. Boshidagi bo'sh joylarni olib tashlang."
    if "unindent" in text or isinstance(error, TabError):
        return "Bu qatorning surilishi yuqoridagi qatorlarga mos emas."
    if "expected ':'" in text:
        return "Qator oxirida ikki nuqta (:) yetishmayapti."
    if "never closed" in text or "unmatched" in text or "parenthes" in text:
        return "Qavslarni tekshiring: ochilgan qavs yopilishi kerak."
    if "unterminated string" in text:
        return "Qo'shtirnoq yopilmagan."
    if "maybe you meant '=='" in text:
        return "Taqqoslash uchun = emas, == yoziladi."
    return "Bu qatorda yozuv xatosi bor. Python qoidalarini tekshiring."


def parse(code: str) -> ast.Module:
    if len(code) > MAX_CODE:
        raise CodeError(f"Kod juda uzun: {MAX_CODE} belgidan oshmasin.")
    try:
        return ast.parse(code)
    except SyntaxError as error:
        raise CodeError(_explain_syntax(error), error.lineno) from error
    except (ValueError, RecursionError, MemoryError) as error:
        raise CodeError("Kodni o'qib bo'lmadi: u juda murakkab yoki noto'g'ri belgi bor.") from error


class Interpreter:
    """Python qismi. O'yinlar o'z buyruqlarini ``commands`` ga qo'shadi: {nom: (funksiya, argumentlar soni)}."""

    tired = "Harakatlar juda ko'p. Sikl to'xtayaptimi?"

    def __init__(self):
        self.events: list[dict] = []
        self.steps = 0
        self.actions = 0
        self.prints = 0
        self.depth = 0
        self.line = 1
        self.globals: dict = {}
        self.scopes: list[dict] = [self.globals]
        self.commands: dict = {}

    def _action(self) -> None:
        self.actions += 1
        if self.actions > MAX_ACTIONS:
            raise CodeError(self.tired, self.line)

    # --- Bajarish ---

    def run(self, tree: ast.Module) -> None:
        try:
            self._block(tree.body)
        except _Return:
            raise CodeError("return faqat funksiya ichida ishlaydi.", self.line) from None
        except (_Break, _Continue):
            raise CodeError("break va continue faqat sikl ichida ishlaydi.", self.line) from None

    def _tick(self) -> None:
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise CodeError("Dastur to'xtamayapti: cheksiz sikl bo'lishi mumkin.", self.line)

    def _block(self, body: list[ast.stmt]) -> None:
        for node in body:
            self._statement(node)

    def _statement(self, node: ast.stmt) -> None:
        self._tick()
        self.line = node.lineno
        if isinstance(node, ast.Expr):
            self._expression_statement(node)
        elif isinstance(node, ast.Assign):
            self._assign(node)
        elif isinstance(node, ast.AugAssign):
            self._aug_assign(node)
        elif isinstance(node, ast.For):
            self._for(node)
        elif isinstance(node, ast.While):
            self._while(node)
        elif isinstance(node, ast.If):
            self._block(node.body if self._truth(node.test) else node.orelse)
        elif isinstance(node, ast.FunctionDef):
            self._define(node)
        elif isinstance(node, ast.Return):
            raise _Return(self._eval(node.value) if node.value else None)
        elif isinstance(node, ast.Break):
            raise _Break
        elif isinstance(node, ast.Continue):
            raise _Continue
        elif not isinstance(node, ast.Pass):
            self._refuse(node)

    def _refuse(self, node: ast.AST):
        name = NOT_ALLOWED.get(type(node))
        text = f"O'yinda «{name}» ishlamaydi." if name else "Bu yozuv o'yinda ishlamaydi."
        raise CodeError(text, getattr(node, "lineno", self.line))

    def _expression_statement(self, node: ast.Expr) -> None:
        value = node.value
        if isinstance(value, ast.Name) and value.id in self.commands:
            raise CodeError(f"Buyruq oxiriga qavs qo'ying: {value.id}()", node.lineno)
        self._eval(value)

    def _target(self, node: ast.expr) -> str:
        if not isinstance(node, ast.Name):
            self._refuse(node)
        if node.id in self.commands or node.id in ("print", "range"):
            raise CodeError(f"«{node.id}» band nom: o'zgaruvchiga boshqa nom bering.", node.lineno)
        return node.id

    def _assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1:
            self._refuse(node)
        name = self._target(node.targets[0])
        self.scopes[-1][name] = self._eval(node.value)

    def _aug_assign(self, node: ast.AugAssign) -> None:
        name = self._target(node.target)
        scope = self.scopes[-1]
        if name not in scope:
            raise CodeError(f"«{name}» hali qiymat olmagan.", node.lineno)
        scope[name] = self._math(node.op, scope[name], self._eval(node.value), node)

    def _define(self, node: ast.FunctionDef) -> None:
        args = node.args
        if args.vararg or args.kwarg or args.kwonlyargs or args.posonlyargs or args.defaults or node.decorator_list:
            self._refuse(node)
        if node.name in self.commands or node.name in ("print", "range"):
            raise CodeError(f"«{node.name}» band nom: funksiyaga boshqa nom bering.", node.lineno)
        self.scopes[-1][node.name] = _Function(node)

    def _loop_body(self, body: list[ast.stmt]) -> bool:
        """Sikl davom etsa True."""
        try:
            self._block(body)
        except _Break:
            return False
        except _Continue:
            pass
        return True

    def _for(self, node: ast.For) -> None:
        call = node.iter
        if node.orelse or not (isinstance(call, ast.Call) and getattr(call.func, "id", "") == "range"):
            raise CodeError("for faqat range(...) bilan ishlaydi: for i in range(3):", node.lineno)
        if not 1 <= len(call.args) <= 3 or call.keywords:
            raise CodeError("range ichida 1 tadan 3 tagacha son bo'ladi.", node.lineno)
        numbers = [self._eval(arg) for arg in call.args]
        if any(type(n) is not int for n in numbers):
            raise CodeError("range ichida butun son bo'lishi kerak.", node.lineno)
        if len(numbers) == 3 and numbers[2] == 0:
            raise CodeError("range qadami 0 bo'lmaydi.", node.lineno)
        name = self._target(node.target)
        for value in range(*numbers):
            self._tick()
            self.scopes[-1][name] = value
            if not self._loop_body(node.body):
                break

    def _while(self, node: ast.While) -> None:
        if node.orelse:
            self._refuse(node)
        while True:
            self._tick()
            self.line = node.lineno
            if not self._truth(node.test) or not self._loop_body(node.body):
                break

    def _truth(self, node: ast.expr) -> bool:
        return bool(self._eval(node))

    def _eval(self, node: ast.expr):
        self._tick()
        if isinstance(node, ast.Constant):
            if node.value is None or isinstance(node.value, (bool, int, str)):
                return node.value
            raise CodeError("O'yinda faqat butun son, matn, True va False ishlaydi.", node.lineno)
        if isinstance(node, ast.Name):
            return self._lookup(node)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, ast.BinOp):
            return self._math(node.op, self._eval(node.left), self._eval(node.right), node)
        if isinstance(node, ast.UnaryOp):
            return self._unary(node)
        if isinstance(node, ast.BoolOp):
            return self._bool(node)
        if isinstance(node, ast.Compare):
            return self._compare(node)
        self._refuse(node)

    def _lookup(self, node: ast.Name):
        if node.id in self.commands:
            raise CodeError(f"Buyruq oxiriga qavs qo'ying: {node.id}()", node.lineno)
        for scope in (self.scopes[-1], self.globals):
            if node.id in scope:
                return scope[node.id]
        raise CodeError(self._unknown(node.id), node.lineno)

    def _unknown(self, name: str) -> str:
        if set(name) == {"_"}:
            return "Bo'sh joyni (___) to'ldiring."
        known = [*self.commands, *self.scopes[-1], *self.globals]
        close = difflib.get_close_matches(name, known, n=1)
        return f"«{name}» degan nom yo'q." + (f" Balki «{close[0]}»?" if close else "")

    def _call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            self._refuse(node.func)
        if node.keywords or any(isinstance(arg, ast.Starred) for arg in node.args):
            self._refuse(node)
        name = node.func.id
        self.line = node.lineno
        if name in self.commands:
            command, arity = self.commands[name]
            if len(node.args) != arity:
                wanted = f"{arity} ta qiymat kutadi" if arity else "qavs ichida hech narsa olmaydi"
                raise CodeError(f"{name}() buyrug'i {wanted}.", node.lineno)
            return command(*[self._eval(arg) for arg in node.args])
        if name == "print":
            return self._print(node)
        target = self.scopes[-1].get(name, self.globals.get(name))
        if target is None and name not in self.scopes[-1] and name not in self.globals:
            raise CodeError(self._unknown(name), node.lineno)
        if not isinstance(target, _Function):
            raise CodeError(f"«{name}» funksiya emas.", node.lineno)
        return self._invoke(target, [self._eval(arg) for arg in node.args], node)

    def _print(self, node: ast.Call) -> None:
        self.prints += 1
        if self.prints > MAX_PRINTS:
            raise CodeError("print juda ko'p chaqirildi.", node.lineno)
        text = " ".join(str(self._eval(arg)) for arg in node.args)
        self.events.append({"a": "print", "text": text[:200], "line": node.lineno})

    def _invoke(self, function: _Function, values: list, node: ast.Call):
        params = [arg.arg for arg in function.node.args.args]
        if len(params) != len(values):
            raise CodeError(
                f"{function.node.name}() {len(params)} ta qiymat kutadi, {len(values)} ta berildi.", node.lineno
            )
        if self.depth >= MAX_DEPTH:
            raise CodeError("Funksiya o'zini juda ko'p chaqirdi.", node.lineno)
        self.depth += 1
        self.scopes.append(dict(zip(params, values, strict=True)))
        try:
            self._block(function.node.body)
        except _Return as result:
            return result.value
        except (_Break, _Continue):
            raise CodeError("break va continue faqat sikl ichida ishlaydi.", self.line) from None
        finally:
            self.scopes.pop()
            self.depth -= 1
            self.line = node.lineno
        return None

    def _math(self, op: ast.operator, left, right, node: ast.AST):
        if type(op) not in MATH:
            hint = "butun bo'lish uchun // ishlating" if isinstance(op, ast.Div) else "bu amal yo'q"
            raise CodeError(f"O'yinda {hint}.", node.lineno)
        if type(left) is not int or type(right) is not int:
            raise CodeError("Bu amal faqat sonlar bilan ishlaydi.", node.lineno)
        if isinstance(op, (ast.FloorDiv, ast.Mod)) and right == 0:
            raise CodeError("Nolga bo'lib bo'lmaydi.", node.lineno)
        value = MATH[type(op)](left, right)
        if abs(value) > MAX_NUMBER:
            raise CodeError("Son juda katta bo'lib ketdi.", node.lineno)
        return value

    def _unary(self, node: ast.UnaryOp):
        value = self._eval(node.operand)
        if isinstance(node.op, ast.Not):
            return not value
        if isinstance(node.op, ast.USub) and type(value) is int:
            return -value
        self._refuse(node)

    def _bool(self, node: ast.BoolOp):
        stop_on = isinstance(node.op, ast.Or)
        value = None
        for item in node.values:
            value = self._eval(item)
            if bool(value) is stop_on:
                break
        return value

    def _compare(self, node: ast.Compare) -> bool:
        left = self._eval(node.left)
        for op, item in zip(node.ops, node.comparators, strict=True):
            if type(op) not in COMPARE:
                self._refuse(node)
            right = self._eval(item)
            try:
                passed = COMPARE[type(op)](left, right)
            except TypeError:
                raise CodeError("Son va matnni solishtirib bo'lmaydi.", node.lineno) from None
            if not passed:
                return False
            left = right
        return True


class RobotMachine(Interpreter):
    tired = "Robot charchadi: harakatlar juda ko'p. Sikl to'xtayaptimi?"

    def __init__(self, world: World):
        super().__init__()
        self.world = world
        self.commands = {
            "yur": (self._move, 0),
            "chapga": (lambda: self._turn(-1), 0),
            "ongga": (lambda: self._turn(1), 0),
            "ol": (self._take, 0),
            "oldinda_devor": (lambda: self.world.blocked(), 0),
            "chapda_devor": (lambda: self.world.blocked(-1), 0),
            "ongda_devor": (lambda: self.world.blocked(1), 0),
            "kristall_bor": (lambda: (self.world.x, self.world.y) in self.world.crystals, 0),
            "yetib_keldi": (lambda: self.world.at_exit, 0),
        }

    def _move(self) -> None:
        self._action()
        world = self.world
        if world.blocked():
            self.events.append({"a": "crash", "line": self.line})
            raise CodeError("Robot devorga urildi!", self.line)
        dx, dy = DIRECTIONS[world.direction]
        world.x, world.y = world.x + dx, world.y + dy
        self.events.append({"a": "move", "x": world.x, "y": world.y, "line": self.line})

    def _turn(self, side: int) -> None:
        self._action()
        self.world.direction = (self.world.direction + side) % 4
        self.events.append({"a": "turn", "side": side, "line": self.line})

    def _take(self) -> None:
        self._action()
        here = (self.world.x, self.world.y)
        if here not in self.world.crystals:
            raise CodeError("Bu katakda kristall yo'q.", self.line)
        self.world.crystals.remove(here)
        self.events.append({"a": "take", "x": here[0], "y": here[1], "line": self.line})


def capture(machine: Interpreter, tree: ast.Module) -> Outcome:
    """Dasturni bajaradi. Xato chiqsa ham shu paytgacha bo'lgan hodisalar animatsiya uchun qoladi."""
    outcome = Outcome(events=machine.events)
    try:
        machine.run(tree)
    except CodeError as error:
        outcome.error, outcome.line = error.message, error.line
    except RecursionError:
        outcome.error, outcome.line = "Kod juda chuqur: soddaroq yozing.", machine.line
    return outcome


def execute(tree: ast.Module, world: World) -> Outcome:
    outcome = capture(RobotMachine(world), tree)
    outcome.won = not outcome.error and world.won
    return outcome


def printed(outcome: Outcome) -> list[str]:
    return [event["text"] for event in outcome.events if event["a"] == "print"]


def count_statements(tree: ast.Module) -> int:
    """Qator emas, buyruq sanaladi: «;» bilan bir qatorga yig'ish yulduz bermaydi."""
    return sum(isinstance(node, ast.stmt) for node in ast.walk(tree))
