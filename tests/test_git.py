import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from todo_radar.gitinfo import parse_porcelain  # noqa: E402
from todo_radar.scanner import scan  # noqa: E402

MARIA = ("Maria Exemplo", "maria@example.com")
JOAO = ("João Exemplo", "joao@example.com")
JAN_2023 = "2023-01-15T12:00:00+00:00"
JUN_2025 = "2025-06-01T12:00:00+00:00"


def epoch(iso):
    return int(datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc).timestamp())


class PorcelainTests(unittest.TestCase):
    def test_parse(self):
        sha = "a" * 40
        output = (
            f"{sha} 1 1 2\nauthor Maria Exemplo\nauthor-mail <maria@example.com>\nauthor-time 1673784000\n"
            "author-tz +0000\nsummary inicio\nfilename app.py\n\tlinha 1\n"
            f"{sha} 2 2\nauthor Maria Exemplo\nauthor-time 1673784000\nfilename app.py\n\tlinha 2\n"
            f"{'0' * 40} 3 3 1\nauthor Not Committed Yet\nauthor-time 1790000000\nfilename app.py\n\tnova\n"
        )
        lines = parse_porcelain(output)
        self.assertEqual(lines[1].author, "Maria Exemplo")
        self.assertEqual(lines[2].timestamp, 1673784000)
        self.assertFalse(lines[3].committed)
        self.assertIsNone(lines[3].author)


@unittest.skipIf(shutil.which("git") is None, "git não está instalado")
class GitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.git("init", "-q")

    def git(self, *args, person=MARIA, date=None):
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
        if date:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
        command = [
            "git", "-c", f"user.name={person[0]}", "-c", f"user.email={person[1]}",
            "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false", *args,
        ]
        subprocess.run(command, cwd=self.repo, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message, person, date):
        self.git("add", "-A", person=person, date=date)
        self.git("commit", "-q", "-m", message, person=person, date=date)

    def test_authors_dates_ignore_and_fallbacks(self):
        self.write("app.py", "def salvar():\n    # TODO(joao): validar o CPF\n    pass\n")
        self.write(".gitignore", "segredos.py\n")
        self.commit("primeiro", MARIA, JAN_2023)
        self.write("web/index.html", "<main>\n<!-- FIXME: menu no celular -->\n</main>\n")
        self.commit("web", JOAO, JUN_2025)
        self.write("app.py", "def salvar():\n    # TODO(joao): validar o CPF\n    pass\n# HACK: ainda não commitado\n")
        self.write("novo.js", "// XXX arquivo novo\n")
        self.write("segredos.py", "# TODO: ignorado pelo .gitignore\n")
        self.write("node_modules/pacote/index.js", "// TODO: dependência\n")

        result = scan(self.repo)
        self.assertTrue(result.used_git)
        items = {(i.path, i.line): i for i in result.items}
        self.assertEqual(sorted(items), [("app.py", 2), ("app.py", 4), ("novo.js", 1), ("web/index.html", 2)])

        todo = items[("app.py", 2)]
        self.assertEqual((todo.author, todo.owner, todo.source), ("Maria Exemplo", "joao", "git"))
        self.assertEqual(todo.timestamp, epoch(JAN_2023))
        fixme = items[("web/index.html", 2)]
        self.assertEqual((fixme.author, fixme.timestamp), ("João Exemplo", epoch(JUN_2025)))
        hack = items[("app.py", 4)]
        self.assertEqual((hack.author, hack.source), (None, "nao-commitado"))
        self.assertIsNotNone(hack.timestamp)
        untracked = items[("novo.js", 1)]
        self.assertEqual((untracked.author, untracked.source), (None, "nao-commitado"))

    def test_subfolder_of_repository(self):
        self.write("api/rotas.py", "# FIXME: rota duplicada\n")
        self.write("outro.py", "# TODO: fora da subpasta\n")
        self.commit("api", MARIA, JAN_2023)
        result = scan(self.repo / "api")
        self.assertEqual([(i.path, i.author) for i in result.items], [("rotas.py", "Maria Exemplo")])

    def test_without_git_option(self):
        self.write("app.py", "# TODO: algo\n")
        self.commit("app", MARIA, JAN_2023)
        result = scan(self.repo, use_git=False)
        self.assertFalse(result.used_git)
        [item] = result.items
        self.assertEqual((item.author, item.source), (None, "arquivo"))


if __name__ == "__main__":
    unittest.main()
