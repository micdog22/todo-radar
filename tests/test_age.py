import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from todo_radar.age import format_age, parse_age  # noqa: E402


class ParseAgeTests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(parse_age("90d"), 90)
        self.assertEqual(parse_age("2s"), 14)
        self.assertEqual(parse_age("6m"), 180)
        self.assertEqual(parse_age("1a"), 365)
        self.assertEqual(parse_age(" 3 M "), 90)
        self.assertEqual(parse_age("0d"), 0)

    def test_invalid(self):
        for text in ("", "90", "d", "1x", "-1d", "1.5m", "2 anos", "1y"):
            with self.subTest(text=text), self.assertRaises(ValueError) as ctx:
                parse_age(text)
            self.assertIn("idade inválida", str(ctx.exception))


class FormatAgeTests(unittest.TestCase):
    def test_portuguese(self):
        cases = {
            None: "sem data",
            0: "hoje",
            0.9: "hoje",
            1: "ontem",
            3: "há 3 dias",
            7: "há 1 semana",
            13: "há 1 semana",
            14: "há 2 semanas",
            29: "há 4 semanas",
            30: "há 1 mês",
            59: "há 1 mês",
            90: "há 3 meses",
            364: "há 12 meses",
            365: "há 1 ano",
            800: "há 2 anos",
        }
        for days, expected in cases.items():
            with self.subTest(days=days):
                self.assertEqual(format_age(days), expected)


if __name__ == "__main__":
    unittest.main()
