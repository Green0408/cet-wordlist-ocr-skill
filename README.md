# cet-wordlist-ocr

把扫描版 / 无文字层 PDF 词书 OCR 成《四六级背单词》可直接导入的 `.txt`。

## 用法

```bash
python scripts/check_wordlist.py 词表.txt
```

- 退出码 0：通过
- 退出码 1：有格式错误
- `--json`：机器可读输出

## 不要安装 PyMuPDF

这个 skill 不需要 PyMuPDF。若 agent 在 `pip install pymupdf` 卡住：

```bash
python scripts/preflight_pdf.py
```

然后按输出走：

1. 直接把 PDF / 页面图片交给视觉能力
2. 用 `pdftoppm` / `pdftocairo` / Ghostscript / `magick`
3. 用 Edge / Chrome 截图
4. 让用户提供 PNG/JPG
5. 外部 OCR 导出 TXT

不要再跑 `pip install`，也不要无限重试。

## 文件

- `SKILL.md` — agent 工作流和提示词
- `references/format.md` — 完整格式规范
- `templates/example.txt` — 正确示例
- `scripts/check_wordlist.py` — 格式校验器
- `scripts/preflight_pdf.py` — 检查本机 PDF 渲染方式
- `tests/` — 校验器测试

## 测试

```bash
python -m unittest discover -s tests -v
```

当前 7 个测试，覆盖：

- 正确样例
- 双栏被拼成一行
- 残留音标
- 只有英文的行
- 只有中文的续行
- 单词重复
- 缺页码
- CLI 退出码
