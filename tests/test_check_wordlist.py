#!/usr/bin/env python3
"""Tests for scripts/check_wordlist.py.

Run from the skill root:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_wordlist.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("check_wordlist", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker()


class ValidatorTests(unittest.TestCase):
    def test_good_fixture_passes(self):
        report = checker.validate_file(ROOT / "tests" / "fixtures" / "good.txt")
        self.assertTrue(report.ok, [i.as_text() for i in report.errors])
        self.assertEqual(report.entries, 9)
        self.assertEqual(report.pages, 2)
        self.assertEqual(report.warnings, [])

    def test_bad_fixture_reports_expected_errors(self):
        report = checker.validate_file(ROOT / "tests" / "fixtures" / "bad.txt")
        self.assertFalse(report.ok)
        text = "\n".join(i.message for i in report.errors)
        self.assertIn("页眉/书名", text)
        self.assertIn("音标", text)
        self.assertIn("多个单词", text)
        self.assertIn("只有英文", text)
        self.assertIn("只有中文", text)
        self.assertIn("单词重复", text)

    def test_two_column_line_is_rejected(self):
        report = checker.validate_text(
            "===== 第 1 页 =====\n"
            "expand v. (使)膨胀    vary v. 改变\n",
            "two-col.txt",
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("多个单词" in i.message for i in report.errors))

    def test_ipa_is_accepted(self):
        report = checker.validate_text(
            "===== 第 1 页 =====\n"
            "expand [ɪkˈspænd] v. (使)膨胀\n"
            "sufficient 【səˈfɪʃənt】 a. 足够的\n",
            "ipa.txt",
        )
        self.assertTrue(report.ok, [i.as_text() for i in report.errors])
        self.assertEqual(report.entries, 2)

    def test_unclosed_ipa_is_rejected(self):
        report = checker.validate_text(
            "===== 第 1 页 =====\n"
            "expand [ɪkˈspænd v. (使)膨胀\n",
            "ipa-broken.txt",
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("音标" in i.message for i in report.errors))

    def test_missing_page_is_warning(self):
        report = checker.validate_text("expand v. (使)膨胀\n", "no-page.txt")
        self.assertTrue(report.ok)
        self.assertEqual(report.entries, 1)
        self.assertTrue(any("没有页码" in i.message for i in report.warnings))

    def test_duplicate_word_is_error(self):
        report = checker.validate_text(
            "===== 第 1 页 =====\n"
            "expand v. (使)膨胀\n"
            "expand v. 扩大\n",
            "dup.txt",
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("单词重复" in i.message for i in report.errors))

    def test_cli_exit_codes(self):
        good = subprocess.run(
            [sys.executable, str(SCRIPT), str(ROOT / "tests" / "fixtures" / "good.txt")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertIn("PASS", good.stdout)

        bad = subprocess.run(
            [sys.executable, str(SCRIPT), str(ROOT / "tests" / "fixtures" / "bad.txt")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
        self.assertIn("FAIL", bad.stdout)


if __name__ == "__main__":
    unittest.main()
