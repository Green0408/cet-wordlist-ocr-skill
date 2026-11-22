# Agent policy: zero-install

This repository is a skill, not a Python/Node application.

## Do not install anything

Never run:

```text
pip install / pip3 install / uv pip install
poetry add / conda install
npm install / pnpm add / yarn add
winget install / choco install / scoop install
apt-get install / brew install
```

Never download OCR models, `traineddata`, PDF engines, fonts, or browser
automation packages to make this skill work.

## If a PDF cannot be opened

1. Use the agent's own PDF / image vision.
2. Run `python scripts/preflight_pdf.py` and use an already-installed tool.
3. Use Edge/Chrome screenshots.
4. Ask the user for PNG/JPG pages.
5. Use an external OCR tool and import the TXT.

`PyMuPDF` is **not** a dependency. If an installation is already running,
stop it; do not retry.

## Validate output

Only this command is required:

```bash
python scripts/check_wordlist.py 词表.txt
```

It uses the Python standard library only.
