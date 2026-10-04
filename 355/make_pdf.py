#!/usr/bin/env python3
"""Print the book to a 6x9 paperback PDF: title page, copyright, contents with page
numbers, every chapter on a new page, the Facts at the back.

    python3 make_pdf.py            -> ../../355.pdf (outside site/, never published)

Uses build.py's own chapter parser, so the PDF reads exactly like the site. Chrome
prints it twice: the first pass finds which page each chapter starts on, the second
writes those numbers into the contents.
"""
import pathlib, re, subprocess, tempfile, html, time

ROOT = pathlib.Path(__file__).parent
src = (ROOT / "build.py").read_text()
ns = {"__file__": str(ROOT / "build.py")}
exec(src[: src.index("BUILD = ")], ns)  # definitions only, no side effects
BOOK, chapter = ns["BOOK"], ns["chapter"]
chapters = sorted((chapter(p) for p in (ROOT / "chapters").glob("*.md")), key=lambda c: c["num"])


def curly(h):
    """Book quotes in text, never inside a tag. A quote opens after a space, a bracket,
    a dash or the start of a paragraph, judged on the TEXT, so a quote closing right
    after italics still closes."""
    out, prev = [], ">"
    for part in re.split(r"(<[^>]+>)", h):
        if part.startswith("<"):
            if part.startswith("<p"):
                prev = " "
            out.append(part)
            continue
        for ch in part:
            if ch in "\"'":
                opening = prev.isspace() or prev in "([\u2014\u201c"
                ch = ("\u201c" if opening else "\u201d") if ch == '"' else ("\u2018" if opening else "\u2019")
            out.append(ch)
            prev = ch
    return "".join(out)


for c in chapters:
    c["html"], c["title"] = curly(c["html"]), curly(c["title"])

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
import sys, datetime
# python3 make_pdf.py 2  -> ../Sic-Semper-v2.pdf, "Version 2" on the title and copyright pages
VERSION = sys.argv[1] if len(sys.argv) > 1 else ""
STAMP = f"Version {VERSION} &middot; {datetime.date.today():%B} {datetime.date.today().day}, {datetime.date.today().year}" if VERSION else ""
OUT = ROOT.parent.parent / (BOOK["title"].replace(" ", "-") + (f"-v{VERSION}" if VERSION else "") + ".pdf")

CSS = """
@page { size: 6in 9in; margin: .8in .7in .85in; @bottom-center { content: counter(page); font: 9pt "EB Garamond", Georgia, serif; color: #555; } }
@page bare { @bottom-center { content: none; } }
body { font-family: "EB Garamond", Georgia, serif; font-size: 11pt; line-height: 1.45; color: #111; margin: 0; }
.front, .open { page: bare; }
.front { break-after: page; text-align: center; }
.title { padding-top: 2.2in; }
.title .series { letter-spacing: .3em; text-transform: uppercase; font-size: 8pt; color: #555; }
.title h1 { font-weight: 500; font-size: 30pt; margin: .3em 0 .2em; }
.title .by { font-style: italic; font-size: 13pt; }
.title .star { color: #8a1c1c; font-size: 16pt; margin-top: 2.4in; }
.title .ver { margin-top: .5in; font-size: 8pt; letter-spacing: .1em; color: #777; }
.legal { padding-top: 5.6in; text-align: left; font-size: 8.5pt; line-height: 1.5; color: #333; }
.toc { text-align: left; padding-top: .6in; }
.toc h2 { text-align: center; font-weight: 500; font-size: 16pt; margin-bottom: 1.2em; }
.toc div { display: flex; font-size: 10.5pt; line-height: 1.75; }
.toc .n { width: 2em; color: #555; }
.toc .t { flex: 1; }
.chapter { break-before: page; }
.chapter header { text-align: center; padding-top: 1.1in; margin-bottom: 2.2em; }
.chapter .num { letter-spacing: .25em; text-transform: uppercase; font-size: 8pt; color: #555; }
.chapter h2 { font-weight: 500; font-size: 18pt; margin: .35em 0 0; }
.chapter p { margin: 0; text-indent: 1.3em; text-align: justify; hyphens: auto; orphans: 2; widows: 2; }
.chapter header + p, .chapter p.break + p, .chapter p.tape-head + p { text-indent: 0; }
.chapter p.break { text-align: center; text-indent: 0; margin: .8em 0; color: #8a1c1c; }
.chapter p.tape { padding-left: .8em; border-left: 1px solid #bbb; }
.chapter p.break.tape { margin: 0; padding: .8em 0 .8em .8em; }
.chapter p.tape-head { text-indent: 0; padding-bottom: .4em; font-variant: small-caps; letter-spacing: .05em; color: #8a1c1c; }
.chapter p.tape-head em { font-style: normal; }
.chapter p.tape-head::before { content: "\\25CF\\00a0 Recording \\00b7\\00a0"; font-size: .75em; letter-spacing: .12em; text-transform: uppercase; color: #555; }
.chapter p:last-child { break-before: avoid; }
.chapter.extra p { text-indent: 0; text-align: left; margin: 0 0 .7em; }
"""


def page(pages):
    toc = "".join(
        f'<div><span class="n">{"" if c["extra"] else c["num"]}</span><span class="t">{html.escape(c["title"])}</span>'
        f'<span>{pages.get(c["num"], "")}</span></div>' for c in chapters)
    body = "".join(
        f'<section class="chapter{" extra" if c["extra"] else ""}" id="c{c["num"]}"><header>'
        f'<div class="num">{"" if c["extra"] else "Chapter " + str(c["num"])}</div><h2>{html.escape(c["title"])}</h2>'
        f'</header>{c["html"]}</section>' for c in chapters)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=block" rel="stylesheet">
<style>{CSS}</style></head><body>
<section class="front title"><div class="series">{BOOK["series"]} &middot; Book {BOOK["number"]}</div>
<h1>{BOOK["title"]}</h1><div class="by">{BOOK["author"]}</div><div class="star">&#10043;</div><div class="ver">{STAMP}</div></section>
<section class="front legal">Copyright &copy; 2026 {BOOK["author"]}. All rights reserved.<br><br>
This is a work of fiction. Apart from the historical figures and events described in the Facts at the back of this book,
names, characters and incidents are the product of the author's imagination.<br><br>{STAMP}</section>
<section class="front toc"><h2>Contents</h2>{toc}</section>
{body}</body></html>"""


def render(pages, pdf):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(page(pages))
    # Chrome sometimes stays up after printing, so wait for the file to stop growing and close it.
    pdf = pathlib.Path(pdf)
    pdf.unlink(missing_ok=True)
    proc = subprocess.Popen([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                             f"--user-data-dir={tempfile.gettempdir()}/wyl-pdf-chrome", f"--print-to-pdf={pdf}", f"file://{f.name}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    last, still = -1, 0
    for _ in range(600):
        time.sleep(0.5)
        size = pdf.stat().st_size if pdf.exists() else -1
        still = still + 1 if size > 0 and size == last else 0
        last = size
        if proc.poll() is not None or still >= 4:
            break
    else:
        proc.kill()
        raise SystemExit("Chrome never finished the PDF")
    if proc.poll() is None:
        proc.kill()
    if not pdf.exists():
        raise SystemExit("Chrome exited without writing the PDF")


def start_pages(pdf):
    """Which page each chapter opens on, read back off the printed PDF."""
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout)[1])
    found, want = {}, list(chapters)
    for p in range(4, n + 1):  # past the front matter
        text = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-layout", pdf, "-"],
                              capture_output=True, text=True).stdout
        head = " ".join(text.split())[:200].upper()
        while want:
            c = want[0]
            key = (c["title"] if c["extra"] else f"CHAPTER {c['num']}").upper()
            if not head.startswith(key.upper()):
                break
            found[c["num"]] = p
            want.pop(0)
    if want:
        raise SystemExit(f"could not find the start page of: {[c['title'] for c in want]}")
    return found


render({}, OUT)
render(start_pages(OUT), OUT)
pages = start_pages(OUT)  # contents filled in can't move a chapter (same page count up front); check anyway
print(f"wrote {OUT} ({len(chapters)} chapters, chapter 1 on page {pages[chapters[0]['num']]})")
