"""Türkçe index.html'den diğer dillerin sayfalarını üretir.

Kullanım:
  python3 i18n/build.py extract   -> i18n/strings.tr.json (çevrilecek metinler)
  python3 i18n/build.py build     -> /<dil>/index.html sayfaları (i18n/<dil>.json çevirileriyle)
"""
import json, re, sys, pathlib
from bs4 import BeautifulSoup, NavigableString, Comment

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
LANGS = [l for l in ["en", "de", "fr", "it", "es", "ru", "zh", "ja"] if (pathlib.Path(__file__).resolve().parent / f"{l}.json").exists()]
ALL = ["tr"] + LANGS
SKIP = {"script", "style", "svg", "noscript"}
INLINE = {"em", "strong", "i", "b", "small", "sup", "sub", "abbr", "br", "cite"}
ATTRS = ["alt", "aria-label", "title", "data-title", "data-cap", "data-credit", "data-photo"]
META = ["description", "og:title", "og:description"]

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def soup():
    return BeautifulSoup(SRC.read_text(encoding="utf-8"), "html.parser")

def own_text(el):
    return any(type(c) is NavigableString and c.strip() for c in el.children)

def is_inline(el):
    # Satır içi öğe (em, strong, cümle içindeki bağlantı...) ancak üst öğesinde de metin varsa birlikte çevrilir
    return el.name in INLINE | {"a", "span"} and el.parent is not None and own_text(el.parent)

def units(doc):
    seen, out = set(), []
    for t in doc.find_all(string=True):
        if type(t) is not NavigableString or not t.strip():
            continue
        if any(p.name in SKIP for p in t.parents):
            continue
        el = t.parent
        while is_inline(el):
            el = el.parent
        if el.name in ("summary",) and el.find("span"):
            continue
        if el.has_attr("lang") and el["lang"] != "tr":  # dil seçici adları
            continue
        if el.find_parent(class_="lang") or "brand" in (el.get("class") or []):
            continue
        if id(el) not in seen:
            seen.add(id(el)); out.append(el)
    return out

def attr_targets(doc):
    out = []
    for el in doc.find_all(True):
        if any(p.name in ("script", "style") for p in [el] + list(el.parents)):
            continue
        if el.find_parent(class_="lang") or el.get("class") == ["lang"]:
            continue
        for a in ATTRS:
            if el.has_attr(a) and norm(el[a]):
                out.append((el, a))
    for m in doc.find_all("meta"):
        if m.get("name") in META or m.get("property") in META:
            out.append((m, "content"))
    return out

def keys(doc):
    ks = []
    for el in units(doc):
        ks.append(norm(el.decode_contents()))
    for el, a in attr_targets(doc):
        ks.append(norm(el[a]))
    uniq = []
    for k in ks:
        if k not in uniq:
            uniq.append(k)
    return uniq

# Çevrilmeden aynen kalan metinler (özel adlar, akademik yayın başlıkları, simgeler)
KEEP_RE = [r"^[×‹›]$", r"^CC BY[\w\- .]*$", r"^8 × 15$", r"^~25 km$"]
KEEP_IDS_FILE = ROOT / "i18n" / "keep.json"

CC_DEED = {"en": "en", "de": "de", "fr": "fr", "it": "it", "es": "es", "ru": "ru", "zh": "zh-hans", "ja": "ja"}
COLON = {"zh": "：", "ja": "："}
UNKNOWN = {"en": "Unknown artist", "de": "Unbekannter Zeichner", "fr": "Dessinateur inconnu", "it": "Disegnatore sconosciuto",
           "es": "Dibujante desconocido", "ru": "Неизвестный художник", "zh": "佚名", "ja": "作者不詳"}

def who_of(name, T, lang):
    return UNKNOWN[lang] if name == "Bilinmeyen çizer" else T.get(name, name)

def keep_set():
    return set(json.loads(KEEP_IDS_FILE.read_text(encoding="utf-8"))) if KEEP_IDS_FILE.exists() else set()

def derive(k, T, lang, keep):
    """Çevirisi başka metinlerden türetilebilen metinler için çeviri döndürür; yoksa None."""
    if k in keep or any(re.match(r, k) for r in KEEP_RE):
        return k
    if k in T:
        return T[k]
    m = re.match(r"^(.+) fotoğrafını büyüt$", k)
    if m and "{} fotoğrafını büyüt" in T:
        inner = derive(m.group(1), T, lang, keep)
        return None if inner is None else T["{} fotoğrafını büyüt"].replace("{}", inner)
    m = re.match(r"^(.+) · (CC [^·]+|Kamu malı)$", k)
    if m:
        who = who_of(m.group(1), T, lang); lic = derive(m.group(2), T, lang, keep)
        return None if lic is None else f"{who} · {lic}"
    m = re.match(r'^<a href="([^"]+)" rel="noopener" target="_blank">(.+?)</a> — (.+?), (.+)$', k)
    if m:
        title = derive(m.group(2), T, lang, keep); who = who_of(m.group(3), T, lang); lic = m.group(4)
        if lic == "Kamu malı":
            lic = T.get("Kamu malı")
        else:
            lic = lic.replace("deed.tr", "deed." + CC_DEED[lang])
        if title is None or lic is None: return None
        return f'<a href="{m.group(1)}" rel="noopener" target="_blank">{title}</a> — {who}, {lic}'
    if ": " in k:
        a, b = k.split(": ", 1)
        ta, tb = derive(a, T, lang, keep), derive(b, T, lang, keep)
        if ta is not None and tb is not None:
            return ta + COLON.get(lang, ": ") + tb
    return None


def extract():
    ks = keys(soup()); keep = keep_set()
    need = []
    for k in ks:
        if k in keep or any(re.match(r, k) for r in KEEP_RE): continue
        if re.match(r"^.+ fotoğrafını büyüt$", k): continue
        if re.match(r"^(.+) · (CC [^·]+|Kamu malı)$", k): continue
        if k.startswith('<a href="https://commons.wikimedia.org/'): continue
        if ": " in k and all(p in ks for p in k.split(": ", 1)): continue
        need.append(k)
    need.append("{} fotoğrafını büyüt")
    need = list(dict.fromkeys(need))
    data = {str(i): k for i, k in enumerate(need)}
    (ROOT / "i18n" / "strings.tr.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(ks), "metin;", len(need), "elle çevrilecek,", sum(len(x) for x in need), "karakter")

def offsets(text):
    lines = text.split("\n"); acc = [0]
    for ln in lines: acc.append(acc[-1] + len(ln) + 1)
    return acc

def tag_span(src, el, acc):
    """Kaynak metinde öğenin açılış etiketi ve içeriğinin konumlarını bulur."""
    st = acc[el.sourceline - 1] + el.sourcepos
    assert src[st] == "<" and src[st + 1:st + 1 + len(el.name)].lower() == el.name, (el.name, src[st:st + 30])
    gt = src.index(">", st)
    depth, pos = 1, gt + 1
    pat = re.compile(r"<(/?)" + re.escape(el.name) + r"(?=[\s>/])", re.I)
    while depth:
        m = pat.search(src, pos)
        if m.group(1): depth -= 1
        else: depth += 1
        pos = m.end()
        if depth == 0: close = m.start()
    return st, gt + 1, close

def esc_attr(v):
    return v.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")

def render(lang, T_all):
    src = SRC.read_text(encoding="utf-8")
    doc = BeautifulSoup(src, "html.parser"); acc = offsets(src)
    edits = []  # (start, end, new)
    for el in units(doc):
        st, a, b = tag_span(src, el, acc)
        edits.append((a, b, T_all[norm(el.decode_contents())]))
    for el, attr in attr_targets(doc):
        st = acc[el.sourceline - 1] + el.sourcepos; gt = src.index(">", st)
        tag = src[st:gt + 1]
        m = re.search(r'(\s' + re.escape(attr) + r'=")([^"]*)(")', tag)
        edits.append((st + m.start(2), st + m.end(2), esc_attr(T_all[norm(el[attr])])))
    edits.sort(key=lambda e: e[0], reverse=True)
    for a, b, new in edits:
        src = src[:a] + new + src[b:]
    url = f"https://magnesia.com.tr/{lang}/"
    src = src.replace('<html lang="tr">', f'<html lang="{lang}">', 1)
    src = src.replace('<link rel="canonical" href="https://magnesia.com.tr/">', f'<link rel="canonical" href="{url}">', 1)
    src = src.replace('<meta property="og:url" content="https://magnesia.com.tr/">', f'<meta property="og:url" content="{url}">', 1)
    src = src.replace('<span>TR</span></summary>', f'<span>{lang.upper()}</span></summary>', 1)
    src = src.replace(' aria-current="page">Türkçe', '>Türkçe', 1)
    src = re.sub(r'(hreflang="' + lang + r'" lang="' + lang + r'")>', r'\1 aria-current="page">', src, count=1)
    return src

def hreflang_block():
    lines = []
    for l in ALL + ["x-default"]:
        href = "https://magnesia.com.tr/" + ("" if l in ("tr", "x-default") else l + "/")
        lines.append(f'<link rel="alternate" hreflang="{l}" href="{href}">')
    return "\n".join(lines)

def ensure_hreflang():
    src = SRC.read_text(encoding="utf-8")
    src = re.sub(r'(<link rel="alternate" hreflang="[^"]+" href="[^"]+">\n)+', "", src)
    src = src.replace('<link rel="canonical" href="https://magnesia.com.tr/">',
                      '<link rel="canonical" href="https://magnesia.com.tr/">\n' + hreflang_block(), 1)
    SRC.write_text(src, encoding="utf-8")

def build():
    ensure_hreflang()
    ks = keys(soup())
    ids = json.loads((ROOT / "i18n" / "strings.tr.json").read_text(encoding="utf-8"))
    for lang in LANGS:
        raw = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        if isinstance(raw, list):  # sıralı liste: strings.tr.json ile aynı sırada
            if len(raw) != len(ids):
                sys.exit(f"{lang}: {len(raw)} çeviri var, {len(ids)} bekleniyordu")
            raw = {str(i): v for i, v in enumerate(raw)}
        T = {ids[i]: v for i, v in raw.items()}
        keep = keep_set(); tr = {}
        for k in ks:
            v = derive(k, T, lang, keep)
            if v is not None: tr[k] = v
        missing = [k for k in ks if k not in tr]
        if missing:
            sys.exit(f"{lang}: {len(missing)} eksik çeviri, ilki: {missing[0][:80]}")
        out = ROOT / lang / "index.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(render(lang, tr), encoding="utf-8")
        print("yazıldı", out.relative_to(ROOT))

if __name__ == "__main__":
    {"extract": extract, "build": build}[sys.argv[1]]()
