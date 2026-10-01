#!/usr/bin/env python3
"""Build index.html from chapters/*.md.

Each chapter file needs a line "## Chapter N: Title" ("## Extra N: Title" for back matter such as an author's note, shown without a chapter number). Everything after it is the
chapter text: blank lines split paragraphs, *italic*, **bold**, and a line of
"---" or "* * *" is a scene break. Run: python3 build.py

revisions.json remembers, per chapter, when each paragraph's text was first
built, so the page can box in paragraphs that changed in the LATEST ROUND of
fixes. Start a new round with: python3 build.py --new-round  (only paragraphs
changed from that build on are boxed; earlier rounds stop being highlighted). version.json holds this build's stamp so an open page can tell it's
out of date. Both are public and hold only hashes and times, no text.
"""
import hashlib, html, json, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).parent
BOOK = {"series": "While You Live", "title": "Sic Semper", "number": 1, "author": "Andrew F. Young"}


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # [label](https://...) opens in a new tab so the reader keeps its place; a url may hold one level of ( )
    text = re.sub(r"\[([^\]]+)\]\((https?://(?:[^()\s]|\([^()\s]*\))+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


def chapter(path):
    lines = path.read_text().splitlines()
    head = next(i for i, l in enumerate(lines) if l.startswith("## "))
    m = re.match(r"##\s*(Chapter|Extra)\s+(\d+)\s*:\s*(.+)", lines[head])
    extra, num, title = m.group(1) == "Extra", int(m.group(2)), m.group(3).strip()
    blocks, para, hashes = [], [], []

    # Ari's testimony is set as a transcript. A section that opens with an italic line
    # holding a year ("*March 1865*") starts it; it runs across scene breaks until a
    # section that opens with a "[now]" line (Iola speaking again) or the chapter ends.
    tape = [False]
    start = [True]  # at the start of a section

    def flush():
        if para:
            text = " ".join(para)
            cls = ""
            if start[0] and re.fullmatch(r"\*[^*]*\b1[89]\d\d\b[^*]*\*", text):
                tape[0] = True
                cls = ' class="tape tape-head"'
            elif tape[0]:
                cls = ' class="tape"'
            blocks.append(f"<p{cls}>" + inline(text) + "</p>")
            hashes.append(hashlib.sha1(text.encode()).hexdigest()[:12])
            para.clear()
            start[0] = False

    for line in lines[head + 1:] + [""]:
        s = line.strip()
        if s in ("---", "* * *"):
            flush()
            blocks.append(f'<p class="break{" tape" if tape[0] else ""}">&#10043;</p>')
            start[0] = True
        elif s == "[now]":
            flush()
            tape[0] = False
            if blocks and blocks[-1].startswith('<p class="break tape"'):
                blocks[-1] = '<p class="break">&#10043;</p>'
        elif not s:
            flush()
        else:
            para.append(s)
    audio = (ROOT / "audio" / f"ch{num:02d}.mp3").exists()  # narration, made by ../audio/narrate.py
    return {"num": num, "title": title, "extra": extra, "html": "\n".join(blocks), "hashes": hashes, "audio": audio}


BUILD = int(time.time() * 1000)
chapters = sorted((chapter(p) for p in (ROOT / "chapters").glob("*.md")), key=lambda c: c["num"])

# A paragraph keeps the time its exact text first appeared; new or edited text gets this build's time.
rev_path = ROOT / "revisions.json"
old = json.loads(rev_path.read_text()) if rev_path.exists() else {}
rev = {"_round": BUILD if "--new-round" in sys.argv else old.get("_round", 0)}
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
       .replace("/*BUILD*/0", str(BUILD)).replace("/*ROUND*/0", str(rev["_round"])))
(ROOT / "index.html").write_text(out)
print(f"built index.html with {len(chapters)} chapter(s)")
