#!/usr/bin/env python3
"""Validate a CET word-list TXT before importing it into 四六级背单词.

Usage:
    python check_wordlist.py 词表.txt [更多.txt ...]
    python check_wordlist.py --json 词表.txt

Exit codes:
    0 = pass (warnings allowed)
    1 = validation errors
    2 = usage / read error

The target app parses:
    ===== 第 N 页 =====
    英文单词 + 词性（可选） + 中文释义

This checker is deliberately strict: it catches the OCR mistakes that make
the app silently drop entries or merge two columns into one definition.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

PAGE_RE = re.compile(r"^(?:={3,}|-{3,})\s*第\s*(\d+)\s*页\s*(?:={3,}|-{3,})$")
WORD = r"[A-Za-z][A-Za-z'\-]{1,33}"
ENTRY_RE = re.compile(
    rf"^(?P<word>{WORD}(?:\s+{WORD}){{0,3}})"
    rf"\s+(?:(?P<pos>[a-z]{{1,4}})\.\s*)?"
    rf"(?P<meaning>[（(]?[\u4e00-\u9fff].*)$"
)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ENGLISH_RE = re.compile(r"[A-Za-z]{2,}")
IPA_BRACKET_RE = re.compile(r"\[[^\[\]]{0,80}\]|【[^】]{0,80}】")
TWO_WORD_IPA_RE = re.compile(rf"\b{WORD}\s*(?=\[|【)")
TWO_POS_RE = re.compile(rf"\b{WORD}\s+[a-z]{{1,4}}\.\s+")
HEADER_RE = re.compile(
    r"^(?:大学英语|四六级|四级|六级|高频词汇|词汇|WORD\s*LIST|VOCABULARY|"
    r"DAY\s*\d+|UNIT\s*\d+|LIST\s*\d+)",
    re.IGNORECASE,
)
MARKDOWN_RE = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\|)")


@dataclass
class Issue:
    line: int
    level: str
    message: str

    def as_text(self) -> str:
        return f"line {self.line}: {self.level}: {self.message}"

    def as_dict(self) -> dict:
        return {"line": self.line, "level": self.level, "message": self.message}


@dataclass
class Report:
    path: str
    entries: int = 0
    pages: int = 0
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    words: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "ok": self.ok,
            "entries": self.entries,
            "pages": self.pages,
            "errors": [i.as_dict() for i in self.errors],
            "warnings": [i.as_dict() for i in self.warnings],
        }


def _issue(report: Report, line: int, level: str, message: str) -> None:
    target = report.errors if level == "ERROR" else report.warnings
    target.append(Issue(line=line, level=level, message=message))


def validate_text(text: str, path: str = "<string>") -> Report:
    report = Report(path=path)
    seen_words: dict[str, int] = {}
    seen_pages: dict[int, int] = {}
    page_numbers: list[int] = []
    current_page: int | None = None

    # Strip a UTF-8 BOM if present; keep line numbers stable.
    if text.startswith("\ufeff"):
        text = text[1:]

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        page_match = PAGE_RE.match(line)
        if page_match:
            page = int(page_match.group(1))
            report.pages += 1
            current_page = page
            page_numbers.append(page)
            if page in seen_pages:
                _issue(report, lineno, "ERROR",
                       f"页码重复：第 {page} 页（首次在第 {seen_pages[page]} 行）")
            else:
                seen_pages[page] = lineno
            continue

        if line.startswith("=") or line.startswith("-"):
            _issue(report, lineno, "ERROR",
                   "页码分隔线格式不对，应为：===== 第 N 页 =====")
            continue

        if HEADER_RE.match(line):
            _issue(report, lineno, "ERROR",
                   "页眉/书名/DAY/Unit 等标题不应进入词表")
            continue

        if MARKDOWN_RE.match(line):
            _issue(report, lineno, "ERROR",
                   "检测到 Markdown 标题、列表或表格；词表必须是纯文本单行")
            continue

        if IPA_BRACKET_RE.search(line):
            _issue(report, lineno, "ERROR",
                   "残留音标方括号，导入前删除 [...] / 【...】")
            continue

        word_ipa_hits = TWO_WORD_IPA_RE.findall(line)
        pos_hits = TWO_POS_RE.findall(line)
        if len(word_ipa_hits) > 1 or len(pos_hits) > 1:
            _issue(report, lineno, "ERROR",
                   "同一行出现多个单词，疑似双栏被拼成一行；应先左栏后右栏拆分")
            continue

        entry = ENTRY_RE.match(line)
        if entry:
            word = re.sub(r"\s+", " ", entry.group("word")).strip()
            meaning = entry.group("meaning").strip()
            key = word.lower()
            report.entries += 1
            report.words.append(word)

            if key in seen_words:
                _issue(report, lineno, "ERROR",
                       f"单词重复：{word}（首次在第 {seen_words[key]} 行）")
            else:
                seen_words[key] = lineno

            if len(word) > 34:
                _issue(report, lineno, "WARN", f"词头过长：{word}")
            if len(meaning) > 140:
                _issue(report, lineno, "WARN",
                       f"释义超过 140 字符，导入时会被截断：{word}")
            if current_page is None:
                _issue(report, lineno, "WARN",
                       "第一个词条出现在页码分隔线之前")
            continue

        # Classify the most useful failure instead of a generic "bad line".
        if CJK_RE.search(line) and not ENGLISH_RE.search(line):
            _issue(report, lineno, "ERROR",
                   "只有中文的续行；应合并到上一条释义")
        elif ENGLISH_RE.search(line) and not CJK_RE.search(line):
            _issue(report, lineno, "ERROR",
                   "只有英文、没有中文释义；会被应用丢弃")
        else:
            _issue(report, lineno, "ERROR",
                   "无法解析为「英文单词 + 词性（可选） + 中文释义」")

    if report.entries == 0:
        _issue(report, 1, "ERROR", "没有任何可导入的词条")
    if report.pages == 0 and report.entries:
        _issue(report, 1, "WARN",
               "没有页码分隔线；可以导入，但无法按页制定计划")

    # Page ordering / gaps are useful warnings, not fatal for a quick import.
    for i in range(1, len(page_numbers)):
        prev, cur = page_numbers[i - 1], page_numbers[i]
        if cur <= prev:
            _issue(report, seen_pages.get(cur, 1), "WARN",
                   f"页码没有递增：{prev} → {cur}")
        elif cur > prev + 1:
            _issue(report, seen_pages.get(cur, 1), "WARN",
                   f"页码跳号：{prev} → {cur}")

    return report


def validate_file(path: Path) -> Report:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        report = Report(path=str(path))
        _issue(report, 1, "ERROR", f"不是 UTF-8 文本：{exc}")
        return report
    except OSError as exc:
        report = Report(path=str(path))
        _issue(report, 1, "ERROR", f"读取失败：{exc}")
        return report
    return validate_text(text, str(path))


def _print_report(report: Report) -> None:
    status = "PASS" if report.ok else "FAIL"
    print(
        f"{status}  entries={report.entries} pages={report.pages} "
        f"errors={len(report.errors)} warnings={len(report.warnings)}"
    )
    for issue in report.errors:
        print(f"  {issue.as_text()}")
    for issue in report.warnings:
        print(f"  {issue.as_text()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="校验四六级背单词可导入 TXT 的格式"
    )
    parser.add_argument("files", nargs="+", help="一个或多个 UTF-8 词表 .txt")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    reports: list[Report] = []
    for name in args.files:
        path = Path(name)
        if not path.exists():
            report = Report(path=str(path))
            _issue(report, 1, "ERROR", "文件不存在")
            reports.append(report)
            continue
        reports.append(validate_file(path))

    if args.json:
        print(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))
    else:
        for i, report in enumerate(reports):
            if i:
                print()
            print(report.path)
            _print_report(report)

    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
