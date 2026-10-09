import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from todo_radar import __version__  # noqa: E402
from todo_radar.cli import main  # noqa: E402
from todo_radar.scanner import read_text, scan, walk_files  # noqa: E402

OLD = 1_600_000_000  # setembro de 2020


class NonGitTests(unittest.TestCase):
    """Pasta fora de qualquer repositório: varre tudo e usa a data dos arquivos."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        ceiling = mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(self.root.parent)})
        ceiling.start()
        self.addCleanup(ceiling.stop)
        self.write("src/app.py", "# TODO: tratar erro de rede\n", OLD)
        self.write("src/estilo.css", "/* FIXME: contraste baixo */\n")
        for skipped in ("node_modules/x/index.js", "venv/lib/a.py", ".venv/b.py", "dist/app.js",
                        "build/c.py", "vendor/d.go", "__pycache__/e.py", ".git/hooks/f.sh"):
            self.write(skipped, "# TODO: não deve aparecer\n")
        (self.root / "imagem.png").write_bytes(b"\x89PNG\x00\x00TODO")
        (self.root / "grande.txt").write_text("# TODO: grande\n" + "x" * (2 * 1024 * 1024), encoding="utf-8")
        (self.root / "latin1.py").write_bytes("# TODO: acentuação em cp1252\n".encode("cp1252"))

    def write(self, rel, text, mtime=None):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if mtime:
            os.utime(path, (mtime, mtime))

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = main([str(self.root), *map(str, args)])
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_walk_skips_dependency_folders(self):
        files = walk_files(self.root)
        self.assertIn("src/app.py", files)
        self.assertFalse(any(f.split("/")[0] in {"node_modules", "venv", ".venv", "dist", "build", "vendor",
                                                  "__pycache__", ".git"} for f in files))

    def test_binary_and_large_files_are_skipped(self):
        self.assertIsNone(read_text(self.root / "imagem.png"))
        self.assertIsNone(read_text(self.root / "grande.txt"))
        self.assertEqual(read_text(self.root / "latin1.py"), "# TODO: acentuação em cp1252\n")

    def test_scan_without_git(self):
        result = scan(self.root)
        self.assertFalse(result.used_git)
        self.assertEqual(sorted((i.path, i.tag) for i in result.items),
                         [("latin1.py", "TODO"), ("src/app.py", "TODO"), ("src/estilo.css", "FIXME")])
        self.assertEqual(result.skipped, 2)
        app = next(i for i in result.items if i.path == "src/app.py")
        self.assertEqual((app.author, app.timestamp, app.source), (None, OLD, "arquivo"))

    def test_table_output_and_exit_codes(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertTrue(lines[1].startswith("src/app.py:1"), "a mais antiga vem primeiro")
        self.assertIn("há ", lines[1])
        self.assertIn("Sem git", out)
        code, _, _ = self.run_cli("--falhar-se-encontrar")
        self.assertEqual(code, 1)

    def test_older_than_filter(self):
        code, out, _ = self.run_cli("--mais-velho-que", "1a", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual([i["arquivo"] for i in data["itens"]], ["src/app.py"])
        code, out, _ = self.run_cli("--mais-velho-que", "100a", "--falhar-se-encontrar")
        self.assertEqual(code, 0)
        self.assertIn("Nenhuma marcação encontrada.", out)

    def test_tags_and_markdown(self):
        code, out, _ = self.run_cli("--tags", "fixme", "--markdown")
        self.assertEqual(code, 0)
        self.assertIn("| `src/estilo.css:1` | FIXME |", out)
        self.assertNotIn("src/app.py", out)

    def test_usage_errors(self):
        code, _, err = self.run_cli("--mais-velho-que", "noventa")
        self.assertEqual(code, 2)
        self.assertIn("idade inválida", err)
        code, _, err = self.run_cli("--tags", "TO DO")
        self.assertEqual(code, 2)
        self.assertIn("tags inválidas", err)
        code, _, err = self.run_cli("--markdown", "--json")
        self.assertEqual(code, 2)
        out, err_stream = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err_stream):
            with self.assertRaises(SystemExit) as ctx:
                main([str(self.root / "nao-existe")])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("pasta não encontrada", err_stream.getvalue())

    def test_version(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(__version__, out.getvalue())


if __name__ == "__main__":
    unittest.main()
