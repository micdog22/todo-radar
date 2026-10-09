import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from todo_radar.extract import DEFAULT_TAGS, extract, markers_for, parse_tags  # noqa: E402


def found(text, path, tags=DEFAULT_TAGS):
    return [(i.line, i.tag, i.owner, i.text) for i in extract(text, path, tags)]


class CommentStyleTests(unittest.TestCase):
    def test_hash(self):
        text = "x = 1  # TODO: trocar por constante\n## FIXME(ana) arrumar\n#XXX\n"
        self.assertEqual(found(text, "app.py"), [
            (1, "TODO", "", "trocar por constante"),
            (2, "FIXME", "ana", "arrumar"),
            (3, "XXX", "", ""),
        ])

    def test_double_slash_and_single_line_block(self):
        text = "let a = 1; // HACK: contorna bug do navegador\n/* OPTIMIZE: cache */ let b = 2;\n/// BUG falha com CEP vazio\n"
        self.assertEqual(found(text, "app.ts"), [
            (1, "HACK", "", "contorna bug do navegador"),
            (2, "OPTIMIZE", "", "cache"),
            (3, "BUG", "", "falha com CEP vazio"),
        ])

    def test_multiline_block_comments(self):
        text = (
            "/**\n"
            " * Calcula o frete.\n"
            " * TODO(maria): usar a tabela nova\n"
            " */\n"
            "int x = 0; /* começa aqui\n"
            "   FIXME: termina aqui */ int y = 0;\n"
            "/* fecha */ // XXX depois do bloco\n"
        )
        self.assertEqual(found(text, "frete.c"), [
            (3, "TODO", "maria", "usar a tabela nova"),
            (6, "FIXME", "", "termina aqui"),
            (7, "XXX", "", "depois do bloco"),
        ])

    def test_html_and_markdown(self):
        self.assertEqual(found("<div>\n<!-- TODO: trocar o logo -->\n</div>\n", "index.html"),
                         [(2, "TODO", "", "trocar o logo")])
        self.assertEqual(found("Texto\n<!--\nFIXME: link quebrado\n-->\n", "LEIAME.md"),
                         [(3, "FIXME", "", "link quebrado")])

    def test_dash_semicolon_percent_and_vb(self):
        self.assertEqual(found("SELECT 1; -- TODO: remover\n", "consulta.sql"), [(1, "TODO", "", "remover")])
        self.assertEqual(found("print(1) -- HACK provisório\n", "jogo.lua"), [(1, "HACK", "", "provisório")])
        self.assertEqual(found(";; FIXME: recursão infinita\n", "init.el"), [(1, "FIXME", "", "recursão infinita")])
        self.assertEqual(found("[app]\n; TODO: porta\n", "config.ini"), [(2, "TODO", "", "porta")])
        self.assertEqual(found("Texto % TODO: citar fonte\n", "tese.tex"), [(1, "TODO", "", "citar fonte")])
        self.assertEqual(found("Dim x = 1 ' FIXME: tipo errado\n", "Modulo.vb"), [(1, "FIXME", "", "tipo errado")])
        self.assertEqual(found("REM TODO: limpar a pasta\n:: FIXME caminho fixo\n", "build.bat"), [
            (1, "TODO", "", "limpar a pasta"), (2, "FIXME", "", "caminho fixo"),
        ])

    def test_unknown_extension_uses_generic_markers(self):
        self.assertEqual(found("# TODO: a\n// FIXME: b\nTODO: sem comentário\n", "notas.txt"), [
            (1, "TODO", "", "a"), (2, "FIXME", "", "b"),
        ])
        self.assertEqual(markers_for("Dockerfile.prod"), (("#",), True))
        self.assertEqual(markers_for("src/Makefile")[0], ("#",))


class PrecisionTests(unittest.TestCase):
    def test_only_uppercase_whole_words_at_comment_start(self):
        text = (
            "# todo o arquivo é lido\n"
            "# Todo cliente tem CPF\n"
            "# TODOS os casos\n"
            "# veja o TODO acima\n"
            "# TODO-123 formato de ticket\n"
        )
        self.assertEqual(found(text, "app.py"), [])

    def test_strings_without_comment_marker(self):
        self.assertEqual(found('mensagem = "TODO: isso é texto"\n', "app.py"), [])
        self.assertEqual(found("nome = 'TODO: texto entre aspas'\n", "app.py"), [])

    def test_slash_star_inside_python_string_does_not_open_block(self):
        text = 'padrao = "src/**/*.py"\nTODO = 1\n'
        self.assertEqual(found(text, "busca.py"), [])

    def test_custom_tags(self):
        tags = parse_tags("todo, revisar,REVISAR")
        self.assertEqual(tags, ("TODO", "REVISAR"))
        self.assertEqual(found("# REVISAR: regra do ICMS\n# FIXME: ignorado\n", "nf.py", tags),
                         [(1, "REVISAR", "", "regra do ICMS")])

    def test_invalid_tags(self):
        for raw in (",", "TO DO", "#TODO"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_tags(raw)
        self.assertEqual(parse_tags(None), DEFAULT_TAGS)

    def test_owner_and_separators(self):
        text = "// TODO(João Exemplo): revisar\n// FIXME - usar Decimal\n// TODO(maria) sem dois-pontos\n"
        self.assertEqual(found(text, "a.js"), [
            (1, "TODO", "João Exemplo", "revisar"),
            (2, "FIXME", "", "usar Decimal"),
            (3, "TODO", "maria", "sem dois-pontos"),
        ])


if __name__ == "__main__":
    unittest.main()
