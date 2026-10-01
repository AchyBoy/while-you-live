#!/usr/bin/env python3
"""Before/after review page: every paragraph that differs from a tagged version,
old above new, grouped by chapter, with flags (plot, clue or motive questions) on top.

    python3 make_changes.py v2 3     -> changes-v3.html (compares the chapters to git tag v2)

Flags come from ../notes/style-flags-*.md and ../notes/flags-v<N>.md if present.
"""
import difflib, html, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).parent
TAG, VER = sys.argv[1], sys.argv[2]


def paras(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def old_text(name):
    r = subprocess.run(["git", "show", f"{TAG}:chapters/{name}"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def fmt(p):
    p = html.escape(p)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", p)


def word_diff(a, b):
    """New paragraph with inserted words highlighted, old with removed words struck."""
    aw, bw = a.split(" "), b.split(" ")
    sm = difflib.SequenceMatcher(None, aw, bw, autojunk=False)
    old, new = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        A, B = fmt(" ".join(aw[i1:i2])), fmt(" ".join(bw[j1:j2]))
        if op == "equal":
            old.append(A); new.append(B)
        else:
            if A: old.append(f"<del>{A}</del>")
            if B: new.append(f"<ins>{B}</ins>")
    return " ".join(x for x in old if x), " ".join(x for x in new if x)


sections, total = [], 0
for path in sorted((ROOT / "chapters").glob("*.md")):
    new_p, old_p = paras(path.read_text()), paras(old_text(path.name))
    title = next((p[3:] for p in new_p if p.startswith("## ")), path.stem)
    sm = difflib.SequenceMatcher(None, old_p, new_p, autojunk=False)
    items = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        olds, news = old_p[i1:i2], new_p[j1:j2]
        for k in range(max(len(olds), len(news))):
            a = olds[k] if k < len(olds) else ""
            b = news[k] if k < len(news) else ""
            if a and b:
                o, n = word_diff(a, b)
            else:
                o, n = (f"<del>{fmt(a)}</del>" if a else ""), (f"<ins>{fmt(b)}</ins>" if b else "")
            items.append(f'<div class="pair"><div class="old">{o or "<i>(new paragraph)</i>"}</div>'
                         f'<div class="new">{n or "<i>(paragraph cut)</i>"}</div></div>')
    if items:
        total += len(items)
        sections.append(f'<section><h2>{html.escape(title)} <small>{len(items)} changed</small></h2>{"".join(items)}</section>')

flags = []
for f in sorted((ROOT.parent / "notes").glob("style-flags-*.md")) + [ROOT.parent / "notes" / f"flags-v{VER}.md"]:
    if f.exists():
        t = f.read_text().strip()
        if t and t.lower().rstrip(".") != "none":
            flags.append(f"<pre>{html.escape(t)}</pre>")

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Version {VER} changes</title><style>
body {{ font: 17px/1.5 Georgia, serif; max-width: 46em; margin: 0 auto; padding: 1em; color: #1a1a1a; background: #faf7f0; }}
h1 {{ font-weight: 500; }} h2 {{ font-weight: 500; margin-top: 2em; border-bottom: 1px solid #ccc; }} small {{ color: #777; font-size: .6em; }}
.pair {{ margin: 1em 0 1.6em; }}
.old {{ color: #666; font-size: .92em; padding: .5em .7em; border-left: 3px solid #c9a; background: #f3ece8; }}
.new {{ padding: .5em .7em; border-left: 3px solid #6a8; background: #eef4ee; margin-top: .3em; }}
del {{ color: #a33; }} ins {{ background: #cfe8cf; text-decoration: none; }}
.flags {{ background: #fff6d8; border: 1px solid #e3c96b; padding: .5em 1em; }} pre {{ white-space: pre-wrap; font: inherit; }}
@media (prefers-color-scheme: dark) {{ body {{ background: #171512; color: #e6e1d6; }} .old {{ background: #2a2220; color: #b7aea3; }}
 .new {{ background: #1f2a20; }} ins {{ background: #2f5a33; }} del {{ color: #e08a8a; }} .flags {{ background: #3a3115; border-color: #7a6526; }} }}
</style></head><body>
<h1>Sic Semper, Version {VER}: what changed</h1>
<p>Compared with Version {TAG.lstrip("v")}. {total} paragraphs changed. Old text is on top with <del>removed words</del>; new text below with <ins>added words</ins>.</p>
{f'<div class="flags"><h2 style="margin-top:.3em">Questions for you (plot, clue, motive)</h2>{"".join(flags)}</div>' if flags else ""}
{"".join(sections)}
</body></html>"""
(ROOT / f"changes-v{VER}.html").write_text(page)
print(f"wrote changes-v{VER}.html: {total} changed paragraphs in {len(sections)} chapters")
