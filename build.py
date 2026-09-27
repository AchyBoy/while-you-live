#!/usr/bin/env python3
"""Build index.html from chapters/*.md.

Each chapter file needs a line "## Chapter N: Title". Everything after it is the
chapter text: blank lines split paragraphs, *italic*, **bold**, and a line of
"---" or "* * *" is a scene break. Run: python3 build.py

revisions.json remembers, per chapter, when each paragraph's text was first
built, so the page can box in paragraphs that changed since the reader last
looked. version.json holds this build's stamp so an open page can tell it's
out of date. Both are public and hold only hashes and times, no text.
"""
import hashlib, html, json, pathlib, re, time

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
    blocks, para, hashes = [], [], []

    def flush():
        if para:
            text = " ".join(para)
            blocks.append("<p>" + inline(text) + "</p>")
            hashes.append(hashlib.sha1(text.encode()).hexdigest()[:12])
            para.clear()

    for line in lines[head + 1:] + [""]:
        s = line.strip()
        if s in ("---", "* * *"):
            flush()
            blocks.append('<p class="break">&#10043;</p>')
        elif not s:
            flush()
        else:
            para.append(s)
    return {"num": num, "title": title, "html": "\n".join(blocks), "hashes": hashes}


BUILD = int(time.time() * 1000)
chapters = sorted((chapter(p) for p in (ROOT / "chapters").glob("*.md")), key=lambda c: c["num"])

# A paragraph keeps the time its exact text first appeared; new or edited text gets this build's time.
rev_path = ROOT / "revisions.json"
old = json.loads(rev_path.read_text()) if rev_path.exists() else {}
rev = {}
for c in chapters:
    prev = old.get(str(c["num"]))
    added = prev["added"] if prev else BUILD
    seen = prev["paras"] if prev else {}
    paras = {h: seen.get(h, BUILD) for h in c["hashes"]}
    rev[str(c["num"])] = {"added": added, "paras": paras}
    c["added"] = added
    c["pt"] = [paras[h] for h in c.pop("hashes")]
rev_path.write_text(json.dumps(rev, indent=1) + "\n")
(ROOT / "version.json").write_text(json.dumps({"v": BUILD}) + "\n")

template = (ROOT / "template.html").read_text()
out = (template.replace("/*BOOK*/null", json.dumps(BOOK)).replace("/*CHAPTERS*/[]", json.dumps(chapters))
       .replace("/*BUILD*/0", str(BUILD)))
(ROOT / "index.html").write_text(out)
print(f"built index.html with {len(chapters)} chapter(s)")
