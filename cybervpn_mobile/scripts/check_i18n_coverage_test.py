#!/usr/bin/env python3
"""Unit tests for check_i18n_coverage.py."""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_i18n_coverage


def write_arb(path: Path, locale: str, values: dict[str, str]) -> None:
    lines = [f'  "@@locale": "{locale}"']
    for key, value in values.items():
        lines.append(f'  "{key}": "{value}"')
    path.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


def write_policy(
    path: Path,
    supported: list[str],
    selectable: list[str],
) -> None:
    supported_body = ", ".join(f"'{locale}'" for locale in supported)
    selectable_body = ", ".join(f"'{locale}'" for locale in selectable)
    path.write_text(
        "class LocaleConfig {\n"
        f"  static const List<String> supportedLocaleCodes = [{supported_body}];\n"
        f"  static const Set<String> selectableLocaleCodes = {{{selectable_body}}};\n"
        "}\n",
        encoding="utf-8",
    )


class CheckI18nCoverageTest(unittest.TestCase):
    def run_check(self, root: Path) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = check_i18n_coverage.check_coverage(
                root / "arb",
                root / "locale_config.dart",
            )
        return result, output.getvalue()

    def test_fallback_only_missing_keys_do_not_fail_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arb_dir = root / "arb"
            arb_dir.mkdir()
            write_policy(root / "locale_config.dart", ["en", "ru"], ["en"])
            write_arb(arb_dir / "app_en.arb", "en", {"hello": "Hello", "bye": "Bye"})
            write_arb(arb_dir / "app_ru.arb", "ru", {"hello": "Hello"})

            result, output = self.run_check(root)

            self.assertEqual(result, 0)
            self.assertIn("fallback-only", output)
            self.assertIn("SKIP", output)

    def test_reviewed_locale_missing_keys_fail_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arb_dir = root / "arb"
            arb_dir.mkdir()
            write_policy(root / "locale_config.dart", ["en", "ru"], ["en", "ru"])
            write_arb(arb_dir / "app_en.arb", "en", {"hello": "Hello", "bye": "Bye"})
            write_arb(arb_dir / "app_ru.arb", "ru", {"hello": "Hello"})

            result, output = self.run_check(root)

            self.assertEqual(result, 1)
            self.assertIn("FAIL", output)

    def test_unexpected_arb_outside_active_inventory_fails_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arb_dir = root / "arb"
            arb_dir.mkdir()
            write_policy(root / "locale_config.dart", ["en", "zh"], ["en"])
            write_arb(arb_dir / "app_en.arb", "en", {"hello": "Hello"})
            write_arb(arb_dir / "app_zh.arb", "zh", {"hello": "Hello"})
            write_arb(arb_dir / "app_zh_Hant.arb", "zh_Hant", {"hello": "Hello"})

            result, output = self.run_check(root)

            self.assertEqual(result, 1)
            self.assertIn("outside active locale inventory: zh_Hant", output)


if __name__ == "__main__":
    unittest.main()
