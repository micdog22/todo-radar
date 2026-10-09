import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from todo_radar.extract import Item  # noqa: E402
from todo_radar.report import (  # noqa: E402
    filter_older_than,
    group_items,
    render_json,
    render_markdown,
    render_table,
    sort_items,
)

DAY = 86400
NOW = 1_790_000_000.0


def sample():
    return sort_items([
        Item("web/index.html", 2, "FIXME", "o menu quebra | no celular", author="João Exemplo",
             timestamp=NOW - 40 * DAY, source="git"),
        Item("src/clientes.py", 2, "TODO", "validar o CPF", owner="joao", author="Maria Exemplo",
             timestamp=NOW - 800 * DAY, source="git"),
        Item("src/novo.py", 1, "HACK", "provisório", timestamp=NOW, source="nao-commitado"),
        Item("src/clientes.py", 9, "TODO", "sem data"),
    ])


class ReportTests(unittest.TestCase):
    def test_oldest_first_and_undated_last(self):
        self.assertEqual([(i.path, i.line) for i in sample()], [
            ("src/clientes.py", 2), ("web/index.html", 2), ("src/novo.py", 1), ("src/clientes.py", 9),
        ])

    def test_table(self):
        lines = render_table(sample(), NOW).splitlines()
        self.assertEqual(lines[0].split(), ["LOCAL", "TAG", "AUTOR", "IDADE", "TEXTO"])
        self.assertTrue(lines[1].startswith("src/clientes.py:2"))
        self.assertIn("TODO(joao)", lines[1])
        self.assertIn("Maria Exemplo", lines[1])
        self.assertIn("há 2 anos", lines[1])
        self.assertIn("há 1 mês", lines[2])
        self.assertIn("(não commitado)", lines[3])
        self.assertIn("sem data", lines[4])
        self.assertEqual(lines[-1], "4 marcações em 3 arquivos (TODO 2, FIXME 1, HACK 1).")

    def test_table_truncates_to_terminal_width(self):
        long_item = [Item("a.py", 1, "TODO", "x" * 200, timestamp=NOW)]
        for line in render_table(long_item, NOW, width=80).splitlines():
            self.assertLessEqual(len(line), 80)

    def test_empty(self):
        self.assertEqual(render_table([], NOW), "Nenhuma marcação encontrada.\n")
        self.assertEqual(json.loads(render_json([], NOW))["total"], 0)

    def test_grouping(self):
        by_file = [name for name, _ in group_items(sample(), "arquivo")]
        self.assertEqual(by_file, ["src/clientes.py", "src/novo.py", "web/index.html"])
        by_tag = [(name, len(group)) for name, group in group_items(sample(), "tag")]
        self.assertEqual(by_tag, [("TODO", 2), ("FIXME", 1), ("HACK", 1)])
        by_author = [name for name, _ in group_items(sample(), "autor")]
        self.assertEqual(by_author, ["(não commitado)", "-", "João Exemplo", "Maria Exemplo"])
        text = render_table(sample(), NOW, group_by="tag")
        self.assertIn("\nTODO (2)\n", text)

    def test_markdown_escapes_pipes(self):
        text = render_markdown(sample(), NOW)
        self.assertIn("| Local | Tag | Autor | Idade | Texto |", text)
        self.assertIn("o menu quebra \\| no celular", text)
        self.assertIn("| `src/clientes.py:2` | TODO(joao) | Maria Exemplo | há 2 anos | validar o CPF |", text)
        grouped = render_markdown(sample(), NOW, group_by="arquivo")
        self.assertIn("### src/clientes.py (2)", grouped)

    def test_json(self):
        data = json.loads(render_json(sample(), NOW))
        self.assertEqual(data["total"], 4)
        self.assertEqual(data["por_tag"], {"TODO": 2, "FIXME": 1, "HACK": 1})
        first = data["itens"][0]
        self.assertEqual(first["responsavel"], "joao")
        self.assertEqual(first["autor"], "Maria Exemplo")
        self.assertEqual(first["idade_dias"], 800)
        self.assertEqual(first["origem"], "git")
        self.assertIsNotNone(first["data"])
        self.assertIsNone(data["itens"][-1]["data"])
        grouped = json.loads(render_json(sample(), NOW, group_by="autor"))
        self.assertEqual(grouped["agrupado_por"], "autor")
        self.assertEqual(sum(g["total"] for g in grouped["grupos"]), 4)

    def test_filter_older_than(self):
        old = filter_older_than(sample(), 90, NOW)
        self.assertEqual([i.path for i in old], ["src/clientes.py"])
        self.assertEqual(len(filter_older_than(sample(), 30, NOW)), 2)


if __name__ == "__main__":
    unittest.main()
