#!/usr/bin/env python3
"""Build index.html from chapters/*.md.

Each chapter file needs a line "## Chapter N: Title". Everything after it is the
chapter text: blank lines split paragraphs, *italic*, **bold**, and a line of
"---" or "* * *" is a scene break. Run: python3 build.py
"""
import html, json, pathlib, re

ROOT = pathlib.Path(__file__).parent
BOOK = {"series": "While You Live", "title": "Sic Semper", "number": 1}


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def chapter(path):
    lines = path.read_text().splitlines()
    head = next(i for i, l in enumerate(lines) if l.startswith("## "))
    m = re.match(r"##\s*Chapter\s+(\d+)\s*:\s*(.+)", lines[head])
    num, title = int(m.group(1)), m.group(2).strip()
    blocks, para = [], []
    for line in lines[head + 1:] + [""]:
        s = line.strip()
        if s in ("---", "* * *"):
            if para:
                blocks.append("<p>" + inline(" ".join(para)) + "</p>")
                para = []
            blocks.append('<p class="break">&#10043;</p>')
        elif not s:
            if para:
                blocks.append("<p>" + inline(" ".join(para)) + "</p>")
                para = []
        else:
            para.append(s)
    return {"num": num, "title": title, "html": "\n".join(blocks)}


chapters = sorted((chapter(p) for p in (ROOT / "chapters").glob("*.md")), key=lambda c: c["num"])
template = (ROOT / "template.html").read_text()
out = template.replace("/*BOOK*/null", json.dumps(BOOK)).replace("/*CHAPTERS*/[]", json.dumps(chapters))
(ROOT / "index.html").write_text(out)
print(f"built index.html with {len(chapters)} chapter(s)")
