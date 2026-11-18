"""
Build the public site from the talk files in the vault.

    python build.py            # rebuild everything, including the PDF
    python build.py --no-pdf   # skip the PDF (quicker)

Then commit and push. GitHub Pages updates about a minute later.

What it does:
  - copies the deck to slides/index.html, with image paths fixed and the
    offline / home-screen bits added (the deck goes view-only on the web by itself)
  - copies only the images the deck uses into slides/images/
  - turns the shareable reading list (11) into reading-list/index.html,
    dropping the Obsidian properties block
  - prints the deck to slides/deck.pdf with Chrome or Edge, if one is found
  - writes sw.js, the offline cache, with a fresh version so phones pick up changes
No third-party packages needed.
"""
import hashlib, html, re, shutil, subprocess, sys
from pathlib import Path

# ---- where the source files live --------------------------------------------
TALK = Path(r"C:\Users\Luke\Desktop\Write\CoreVault\QA\Me\Talks\MotLondonNov26")
DECK = TALK / "Mockups" / "G_deck.html"
IMAGES = TALK / "Images"
READING = TALK / "11_Reading list - Shareable.md"
# -----------------------------------------------------------------------------

SITE = Path(__file__).resolve().parent
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

HEAD_EXTRAS = """<meta name="theme-color" content="#1E3A2F">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Get a pad">
<link rel="manifest" href="{root}manifest.webmanifest">
<link rel="icon" href="{root}icons/icon-192.png">
<link rel="apple-touch-icon" href="{root}icons/apple-touch-icon.png">
"""
SW_REGISTER = """<script>
if ('serviceWorker' in navigator && location.protocol.startsWith('http'))
  navigator.serviceWorker.register('{root}sw.js').catch(function () {{}});
</script>
"""


def build_deck():
    src = DECK.read_text(encoding="utf-8")
    out_dir = SITE / "slides"
    img_dir = out_dir / "images"
    if img_dir.exists():
        shutil.rmtree(img_dir)
    img_dir.mkdir(parents=True)
    used = sorted(set(re.findall(r'src="\.\./Images/([^"]+)"', src)))
    for name in used:
        shutil.copy2(IMAGES / name, img_dir / name)
    src = src.replace('src="../Images/', 'src="images/')
    src = src.replace('<meta name="viewport" content="width=device-width, initial-scale=1">',
                      '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">', 1)
    src = src.replace("</title>", "</title>\n" + HEAD_EXTRAS.format(root="../"), 1)
    src = src.replace("</body>", SW_REGISTER.format(root="../") + "</body>", 1)
    (out_dir / "index.html").write_text(src, encoding="utf-8", newline="\n")
    print(f"slides: {len(used)} images")
    return ["slides/images/" + n for n in used]


# ---- tiny markdown converter, enough for the reading list --------------------
LINK = re.compile(r"\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")

def inline(t):
    t = html.escape(t, quote=False)
    t = LINK.sub(lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*(?!\*)", r"<strong>\1</strong>", t)
    t = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", t)
    return t

def markdown(md):
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)  # Obsidian properties
    out, lst, item, quote = [], None, [], []

    def close_item():
        nonlocal item
        if item:
            first, rest = item[0], item[1:]
            out.append("<li><p>" + inline(first) + "</p>" + "".join(f"<p>{inline(r)}</p>" for r in rest) + "</li>")
            item = []

    def close_list():
        nonlocal lst
        close_item()
        if lst:
            out.append(f"</{lst}>")
            lst = None

    def close_quote():
        nonlocal quote
        if quote:
            out.append("<blockquote>" + "".join(f"<p>{inline(q)}</p>" for q in quote) + "</blockquote>")
            quote = []

    for raw in md.splitlines():
        line = raw.rstrip()
        m_num, m_bul = re.match(r"^\d+\.\s+(.*)", line), re.match(r"^-\s+(.*)", line)
        if not line.strip():
            close_quote()
            continue
        if line.startswith(">"):
            close_list(); quote.append(line.lstrip("> ").strip()); continue
        close_quote()
        if m_num or m_bul:
            kind = "ol" if m_num else "ul"
            if lst != kind:
                close_list(); out.append(f"<{kind}>"); lst = kind
            close_item(); item = [(m_num or m_bul).group(1)]
            continue
        if lst and raw.startswith(" "):
            item.append(line.strip()); continue
        close_list()
        if line.strip() == "---":
            out.append("<hr>")
        elif m := re.match(r"^(#{1,4})\s+(.*)", line):
            n = len(m.group(1)); out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        else:
            out.append(f"<p>{inline(line)}</p>")
    close_list(); close_quote()
    return "\n".join(out)


def build_reading_list():
    body = markdown(READING.read_text(encoding="utf-8"))
    tpl = (SITE / "templates" / "page.html").read_text(encoding="utf-8")
    page = tpl.replace("{{title}}", "Reading list · Who's holding what now?").replace("{{root}}", "../").replace("{{body}}", body)
    page = page.replace("</title>", "</title>\n" + HEAD_EXTRAS.format(root="../"), 1)
    page = page.replace("</body>", SW_REGISTER.format(root="../") + "</body>", 1)
    d = SITE / "reading-list"; d.mkdir(exist_ok=True)
    (d / "index.html").write_text(page, encoding="utf-8", newline="\n")
    print("reading list: done")


def build_pdf():
    exe = next((b for b in BROWSERS if Path(b).exists()), None)
    if not exe:
        print("pdf: skipped (no Chrome or Edge found)"); return
    target = SITE / "slides" / "deck.pdf"
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
                    "--no-pdf-header-footer", "--virtual-time-budget=8000",
                    f"--print-to-pdf={target}", (SITE / "slides" / "index.html").as_uri()],
                   check=True, capture_output=True)
    print(f"pdf: {target.stat().st_size // 1024} KB")


def build_sw(images):
    files = ["./", "index.html", "site.css", "manifest.webmanifest", "icons/icon-192.png", "icons/apple-touch-icon.png",
             "slides/", "slides/index.html", "reading-list/", "reading-list/index.html"] + images
    h = hashlib.sha1()
    for f in files:
        p = SITE / (f + "index.html" if f.endswith("/") else f)
        h.update(p.read_bytes())
    version = h.hexdigest()[:10]
    sw = (SITE / "templates" / "sw.js").read_text(encoding="utf-8")
    sw = sw.replace("__VERSION__", version).replace("__FILES__", ",\n  ".join(f'"{f}"' for f in files))
    (SITE / "sw.js").write_text(sw, encoding="utf-8", newline="\n")
    print(f"sw.js: version {version}, {len(files)} files cached for offline")


if __name__ == "__main__":
    imgs = build_deck()
    build_reading_list()
    if "--no-pdf" not in sys.argv:
        build_pdf()
    build_sw(imgs)
