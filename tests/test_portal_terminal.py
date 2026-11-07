"""Terminal o'yini: buyruqlar xayoliy kompyuterda bajariladi, haqiqiy tizimga tegmaydi."""

import ast
import json
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

from apps.portal.catalog import BY_SLUG, GAME_BY_SLUG
from apps.portal.games import BadPayload, shell
from apps.portal.models import Student

LEVELS = GAME_BY_SLUG["terminal"].levels
HOME = shell.HOME
FILES = {
    f"{HOME}/xabar.txt": "salom\ndunyo\n",
    f"{HOME}/.maxfiy": "kod\n",
    f"{HOME}/papka/ichki.txt": "ichki\n",
    f"{HOME}/skript.sh": 'echo "ishladi"\n',
    f"{HOME}/a.tmp": "",
    f"{HOME}/b.tmp": "",
}


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def sh():
    return shell.Shell(dict(FILES))


@pytest.fixture
def child(client, db):
    user = get_user_model().objects.create_user("ali", password="Robot-2026!", first_name="Ali")
    client.student = Student.objects.create(user=user)
    client.force_login(user)
    return client


def send(client, slug, commands):
    body = json.dumps({"commands": commands})
    return client.post(reverse("portal_run", args=[slug]), body, content_type="application/json")


def run(sh, line):
    sh.run(line)
    return sh.out


# --- Eng muhimi: haqiqiy tizimga tegmaslik ---


def test_simulator_imports_nothing_that_can_touch_the_real_system():
    source = (Path(settings.BASE_DIR) / "apps/portal/games/shell.py").read_text()
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            imported.add(node.module.split(".")[0])
    assert imported <= {"difflib", "fnmatch", "posixpath", "shlex", "collections", "dataclasses"}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not calls & {"open", "eval", "exec", "__import__", "compile", "getattr"}


@pytest.mark.parametrize(
    "line",
    [
        "cat /etc/passwd",
        "cat ../../../etc/passwd",
        "cat /home/ab-education/.env",
        "cat db.sqlite3",
        "ls /etc",
        "cd /etc",
        "cat ../../../../proc/self/environ",
    ],
)
def test_real_files_are_invisible(sh, line):
    sh.run(line)
    assert not sh.ok
    assert "root:" not in sh.out


@pytest.mark.parametrize(
    "line",
    [
        "$(id)",
        "`id`",
        "cat $(whoami)",
        "python3 -c 'print(1)'",
        "bash -c id",
        "sh",
        "curl http://example.com",
        "wget http://example.com",
        "nc -l 1234",
        "sudo rm -rf /",
    ],
)
def test_nothing_escapes_to_a_real_shell(sh, line):
    sh.run(line)
    assert not sh.ok


def test_redirect_stays_in_the_virtual_world(sh, tmp_path):
    target = tmp_path / "hack.txt"
    sh.run(f"echo salom > {target}")
    assert not target.exists()


def test_rm_everything_is_refused_and_harmless(sh):
    assert "dangerous" in run(sh, "rm -rf /")
    assert sh.exists(f"{HOME}/xabar.txt")
    assert "Hech qachon" in sh.tip


@pytest.mark.parametrize("line", ["rm -rf ~", "rm -rf /home", "rm -r ..", "rm -rf *", "cd /; rm -rf home"])
def test_destructive_commands_never_crash(sh, line):
    sh.run(line)
    sh.run("pwd")
    assert sh.ok
    sh.run("ls")


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "|",
        "| ls",
        "ls |",
        ">",
        "ls >",
        "ls > a b",
        '"',
        "'",
        "&&",
        ";",
        "&",
        "cat <",
        "x" * 300,
        "* * *",
        "ls [",
        "cd",
        "\x00",
    ],
)
def test_odd_input_never_crashes(sh, line):
    sh.run(line)


# --- Buyruqlar ---


def test_pwd_cd_and_prompt(sh):
    assert run(sh, "pwd") == HOME
    assert sh.prompt == "bola@kema:~$"
    sh.run("cd papka")
    assert run(sh, "pwd") == f"{HOME}/papka"
    assert sh.prompt == "bola@kema:~/papka$"
    sh.run("cd ..")
    assert sh.cwd == HOME
    sh.run("cd /")
    assert sh.prompt == "bola@kema:/$"
    sh.run("cd")
    assert sh.cwd == HOME


def test_cd_errors_are_real_with_uzbek_tip(sh):
    assert run(sh, "cd yoq") == "bash: cd: yoq: No such file or directory"
    assert "ls" in sh.tip
    assert "Not a directory" in run(sh, "cd xabar.txt")


def test_ls_hides_dotfiles(sh):
    assert ".maxfiy" not in run(sh, "ls")
    assert ".maxfiy" in run(sh, "ls -a")
    assert "-rw-r--r--" in run(sh, "ls -l")
    assert ".maxfiy" in run(sh, "ls -la")


def test_unknown_command_suggests_fix(sh):
    assert run(sh, "lss") == "bash: lss: command not found"
    assert "ls" in sh.tip
    assert not sh.ok


def test_unknown_flag(sh):
    assert "invalid option" in run(sh, "ls -z")


def test_case_matters(sh):
    assert "command not found" in run(sh, "LS")


def test_cat_and_redirects(sh):
    assert run(sh, "cat xabar.txt") == "salom\ndunyo"
    sh.run('echo "bir" > f.txt')
    sh.run("echo ikki >> f.txt")
    assert run(sh, "cat f.txt") == "bir\nikki"
    sh.run("echo uch > f.txt")
    assert run(sh, "cat f.txt") == "uch"


def test_redirect_into_missing_folder(sh):
    assert "No such file" in run(sh, "echo a > yoq/f.txt")


def test_mkdir_touch_rm(sh):
    sh.run("mkdir yangi")
    assert sh.exists("yangi")
    assert "File exists" in run(sh, "mkdir yangi")
    assert "No such file" in run(sh, "mkdir a/b/c")
    sh.run("mkdir -p a/b/c")
    assert sh.exists("a/b/c")
    sh.run("touch yangi/f.txt")
    assert "Is a directory" in run(sh, "rm yangi")
    sh.run("rm -r yangi")
    assert not sh.exists("yangi") and not sh.exists("yangi/f.txt")


def test_removing_current_folder_moves_up(sh):
    sh.run("cd papka")
    sh.run("rm -r ../papka")
    assert sh.cwd == HOME


def test_glob(sh):
    sh.run("rm *.tmp")
    assert not sh.exists("a.tmp") and not sh.exists("b.tmp") and sh.exists("xabar.txt")


def test_glob_skips_hidden(sh):
    sh.run("rm *")
    assert sh.exists(".maxfiy")


def test_cp_mv(sh):
    sh.run("cp xabar.txt n.txt")
    assert sh.read("n.txt") == sh.read("xabar.txt") and sh.exists("xabar.txt")
    sh.run("mv n.txt papka/")
    assert sh.exists("papka/n.txt") and not sh.exists("n.txt")
    sh.run("mv papka/n.txt papka/m.txt")
    assert sh.exists("papka/m.txt")
    assert "-r not specified" in run(sh, "cp papka p2")
    sh.run("cp -r papka p2")
    assert sh.read("p2/ichki.txt") == "ichki\n"
    sh.run("mv p2 p3")
    assert sh.exists("p3/ichki.txt") and not sh.exists("p2")


@pytest.mark.parametrize("line", ["mv papka papka/ichki", "cp -r papka papka/x", "mv / x"])
def test_folder_into_itself_is_refused(sh, line):
    sh.run(line)
    assert not sh.ok


def test_text_tools_and_pipes(sh):
    sh.run('echo "b" > n.txt')
    sh.run("echo a >> n.txt")
    sh.run("echo a >> n.txt")
    assert run(sh, "sort n.txt") == "a\na\nb"
    assert run(sh, "sort n.txt | uniq") == "a\nb"
    assert run(sh, "sort n.txt | uniq | wc -l") == "2"
    assert run(sh, "grep a n.txt | wc -l") == "2"
    assert run(sh, "grep -c a n.txt") == "2"
    assert run(sh, "grep -v a n.txt") == "b"
    assert run(sh, "head -n 1 n.txt") == "b"
    assert run(sh, "tail -1 n.txt") == "a"
    assert run(sh, "cat n.txt | head -n 2 | tail -n 1") == "a"


def test_grep_is_case_sensitive_unless_asked(sh):
    assert run(sh, "grep SALOM xabar.txt") == ""
    assert run(sh, "grep -i SALOM xabar.txt") == "salom"


def test_find(sh):
    assert run(sh, "find . -name '*.txt'") == "./papka/ichki.txt\n./xabar.txt"
    assert "No such file" in run(sh, "find yoq -name x")


def test_quotes_protect_glob(sh):
    assert run(sh, 'echo "*.tmp"') == "*.tmp"
    assert run(sh, "echo *.tmp") == "a.tmp b.tmp"
    assert run(sh, "echo 'a?'") == "a?"


def test_sequence(sh):
    assert run(sh, "cd papka && pwd") == f"{HOME}/papka"
    assert run(sh, "cd .. ; pwd") == HOME


def test_chmod_and_run(sh):
    assert "Permission denied" in run(sh, "./skript.sh")
    assert "chmod" in sh.tip
    sh.run("chmod +x skript.sh")
    assert run(sh, "./skript.sh") == "ishladi"
    assert "-rwxr-xr-x" in run(sh, "ls -l")
    sh.run("chmod -x skript.sh")
    assert "Permission denied" in run(sh, "./skript.sh")
    sh.run("chmod 755 skript.sh")
    assert run(sh, "./skript.sh") == "ishladi"


def test_tab_names_reach_nested_files(sh):
    assert "papka/" in sh.names() and "papka/ichki.txt" in sh.names()
    sh.run("cd papka")
    assert sh.names() == ["ichki.txt"]


def test_history_clear_man_help(sh):
    sh.run("pwd")
    assert "pwd" in run(sh, "history")
    sh.run("clear")
    assert sh.cleared
    assert "Papka ichini" in run(sh, "man ls")
    assert "No manual entry" in run(sh, "man yoq")
    assert "grep" in run(sh, "help")


def test_huge_output_is_capped(sh):
    sh.run("echo a > f.txt")
    for _ in range(9):
        sh.run("cat f.txt f.txt f.txt > g.txt")
        sh.run("mv g.txt f.txt")
    assert sh.read("f.txt").count("\n") <= shell.MAX_FILE
    assert len(run(sh, "cat f.txt").split("\n")) <= shell.MAX_OUTPUT


def test_file_size_is_capped(sh):
    sh.run("echo " + "a" * 250 + " > f.txt")
    for _ in range(12):
        sh.run("cat f.txt f.txt > g.txt")
        sh.run("cp g.txt f.txt")
    assert len(sh.read("f.txt")) <= shell.MAX_FILE


# --- Bosqichlar ---


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.slug)
def test_level_solution_finishes_with_three_stars(level):
    result = shell.attempt(level, {"commands": list(level.solution)}, 0)
    assert result["ok"], f"{result['step']}-vazifada to'xtadi: {result['out']}"
    assert result["stars"] == 3


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.slug)
def test_every_step_example_really_works(level):
    """Namuna ko'rsatilgan buyruq vazifani bajarishi shart: bola adashib qolmasin."""
    commands = []
    for number, step in enumerate(level.steps, 1):
        commands.append(step.example)
        result = shell.attempt(level, {"commands": commands}, 0)
        assert result["step"] == number, f"{step.example!r}: {result['out']}"


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.slug)
def test_steps_are_not_solved_by_doing_nothing(level):
    assert shell.attempt(level, {"commands": ["echo salom"]}, 0)["step"] == 0


def test_steps_stay_in_order():
    level = BY_SLUG["term-salom"]
    result = shell.attempt(level, {"commands": ["ls"]}, 0)
    assert result["step"] == 0 and not result["advanced"]


def test_equivalent_command_is_accepted():
    level = BY_SLUG["term-cd"]
    assert shell.attempt(level, {"commands": [f"cd {HOME}/xarita"]}, 0)["step"] == 1


def test_wrong_commands_cost_stars_but_never_block():
    level = BY_SLUG["term-salom"]
    noisy = ["yoq"] * 20 + list(level.solution)
    result = shell.attempt(level, {"commands": noisy}, 0)
    assert result["ok"] and result["stars"] == 1


def test_stars_scale():
    assert [shell.stars_for(n, 3) for n in (3, 5, 6, 10, 11)] == [3, 3, 2, 2, 1]


def test_blank_lines_are_free():
    level = BY_SLUG["term-salom"]
    result = shell.attempt(level, {"commands": [""] * 10 + list(level.solution)}, 0)
    assert result["stars"] == 3


@pytest.mark.parametrize("commands", [[], "ls", None, [1], [None], ["x" * 301], ["ls"] * 81])
def test_rejects_forged_requests(commands):
    with pytest.raises(BadPayload):
        shell.attempt(LEVELS[0], {"commands": commands}, 0)


def test_page_and_partial_run(child):
    level = LEVELS[0]
    response = child.get(reverse("portal_play", args=[level.slug]))
    assert response.status_code == 200
    assert 'id="term-input"' in response.content.decode()
    data = send(child, level.slug, ["whoami"]).json()
    assert data["out"] == "bola" and data["advanced"] and data["step"] == 1
    assert not child.student.progress.exists()


def test_finishing_saves_stars_and_commands(child):
    level = LEVELS[0]
    data = send(child, level.slug, list(level.solution)).json()
    assert data["ok"] and data["gained"] == 30
    row = child.student.progress.get()
    assert row.stars == 3 and row.code == "whoami\npwd\nls"


def test_each_run_starts_fresh_so_students_do_not_share_state(child):
    level = BY_SLUG["term-yarat"]
    LevelProgress = child.student.progress.model
    for earlier in LEVELS[: LEVELS.index(level)]:
        LevelProgress.objects.create(student=child.student, level=earlier.slug, stars=1)
    send(child, level.slug, ["mkdir ombor"])
    assert "ombor" not in send(child, level.slug, ["ls"]).json()["out"]


def test_terminal_lesson_has_no_python_sandbox(child):
    html = child.get(reverse("portal_lesson", args=["terminal"])).content.decode()
    assert "portal-lesson.js" not in html and "Sinab ko" not in html
    assert "Sichqonchasiz" in html
