#!/usr/bin/env python3
"""Check available PDF-to-image options without installing anything.

Usage:
    python scripts/preflight_pdf.py

The skill does not require PyMuPDF. This script reports what is already
available so an agent can pick a fallback instead of blocking on pip.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path

TOOLS = [
    "pdftoppm",
    "pdftocairo",
    "magick",
    "gswin64c",
    "gs",
    "mutool",
    "qpdf",
]

PY_MODULES = [
    "fitz",          # PyMuPDF, optional
    "pypdfium2",
    "pdf2image",
    "PIL",
]

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def main() -> int:
    print("cet-wordlist-ocr PDF preflight")
    print("=" * 36)

    found = []
    print("\nPDF renderers on PATH:")
    for name in TOOLS:
        path = shutil.which(name)
        if path:
            print(f"  OK   {name}: {path}")
            found.append(name)
        else:
            print(f"  --   {name}")

    print("\nPython modules:")
    for name in PY_MODULES:
        ok = importlib.util.find_spec(name) is not None
        print(f"  {'OK  ' if ok else '--  '} {name}")
        if ok and name in {"pypdfium2", "pdf2image"}:
            found.append(name)

    print("\nBrowsers:")
    for path in BROWSERS:
        print(f"  {'OK  ' if Path(path).exists() else '--  '} {path}")

    print("\nRecommended:")
    if found:
        print(f"  Use: {', '.join(found)}")
    else:
        print("  No command-line renderer found.")
        print("  A. Give the PDF/pages directly to a vision-capable agent.")
        print("  B. Use Edge/Chrome to screenshot pages.")
        print("  C. Ask the user for PNG/JPG pages.")
        print("  D. Use an external OCR tool and import TXT.")
    print("\nDo NOT install PyMuPDF just for this skill.")
    print("If an install is already running, stop it and use one of the fallbacks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
