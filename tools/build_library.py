#!/usr/bin/env python3
"""Rebuild PratMusic's bundled catalogue from the Internet Archive (open licences only).
Downloads the 13 CC/PD-licensed MP3s UNMODIFIED + cover art, writes library.json.
Usage:  python3 tools/build_library.py [--out DIR] [--skip-existing]
"""
import json, os, re, io, sys, math, random, urllib.request, urllib.parse, concurrent.futures as cf
from PIL import Image, ImageDraw, ImageFilter, ImageOps
UA = {"User-Agent": "Mozilla/5.0 (pratmusic catalogue builder; personal offline player)"}
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = HERE
SKIP = "--skip-existing" in sys.argv
for i, a in enumerate(sys.argv):
    if a == "--out": OUT = sys.argv[i + 1]
MEDIA, COV = f"{OUT}/media", f"{OUT}/covers"
os.makedirs(MEDIA, exist_ok=True); os.makedirs(COV, exist_ok=True)

def get(u, t=240, retry=3):
    last = None
    for i in range(retry):
        try:
            r = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(r, timeout=t) as x: return x.read()
        except Exception as e:
            last = e
    raise last
def meta(i): return json.loads(get(f"https://archive.org/metadata/{i}", t=60))
def norm(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())
FMT = {"VBR MP3": 0, "192Kbps MP3": 1, "128Kbps MP3": 2, "MP3": 2, "64Kbps MP3": 4}

PICKS = [
 ("amb_col_light","Light Part 2","Ambient","drifting / luminous","light-part-2"),
 ("gt390FandorinProjet2","Different But Equivalent","Experimental","hypnotic / CC0","different-but-equivalent"),
 ("DWK119","Streetlight Noir","Lo-Fi Jazz","rainy night city","streetlight-noir"),
 ("DWK301","SoInLoveWithYou","Lo-Fi Hip-Hop","warm tape hiss","so-in-love-with-you"),
 ("SCL203","Cool","Jazz","smoky lounge","pk-jazz-cool"),
 ("v-a-dark-synthwave","Ozone Cloud","Dark Synthwave","neon drive","ozone-cloud"),
 ("v-a-dark-synthwave","Night Lights 2","Dark Synthwave","midnight chrome","night-lights-2"),
 ("BFTG_177","Recycle 2.1","Vaporwave","mall echo / 80s dream","recycle-2-1"),
 ("qd-4244","darling i miss you","Chiptune","pixel heartbreak","darling-i-miss-you"),
 ("hc152_too_bleep_to_blop_by_8_bit_betty","Was that away message for me?","Chiptune","playful bleeps","was-that-away-message"),
 ("chase005","Hellfire","IDM","glitchy intensity","hellfire"),
 ("EVIL009","Dame Chocolate (feat. Fade In)","Electro Funk","dusty groove","dame-chocolate"),
 ("aer006","Es kann nicht ewig Winter sein","Post-Classical","melancholy strings","es-kann-nicht-ewig-winter"),
]
REAL = {  # best high-res album art per track
 "light-part-2":("amb_col_light","originalfront.png"),
 "different-but-equivalent":("gt390FandorinProjet2","00front.jpg"),
 "streetlight-noir":("DWK119","Jenova_7_-_Dusted_Jazz_Volume_Two_1_Front_Cover.jpg"),
 "so-in-love-with-you":("DWK301","Mounika_-_Born_To_Be_Beats.jpg"),
 "pk-jazz-cool":("SCL203","cover.jpg"),
 "ozone-cloud":("v-a-dark-synthwave","cover.jpg"),
 "night-lights-2":("v-a-dark-synthwave","cover.jpg"),
 "recycle-2-1":("BFTG_177","cover.png"),
 "hellfire":("chase005","00_-_Chase_005_Cover_Front.jpg"),
 "dame-chocolate":("EVIL009","Cover.jpg"),
}
FIX = {"light-part-2":dict(artist="Gregg Plummer"),
 "different-but-equivalent":dict(title="Different But Equivalent"),
 "so-in-love-with-you":dict(title="So In Love With You",album="Born To Be Beats EP"),
 "streetlight-noir":dict(album="Dusted Jazz Volume Two"),
 "pk-jazz-cool":dict(artist="Pk Jazz Collective",album="Analog"),
 "darling-i-miss-you":dict(artist="Cocolulu (Mark Redito)",album="8-Bit Love"),
 "was-that-away-message":dict(album="Too Bleep To Bloop"),
 "hellfire":dict(album="IDM For Cholos"),
 "dame-chocolate":dict(album="Cleaning The Dusty In My House"),
 "es-kann-nicht-ewig-winter":dict(artist="Bersarin Quartett",album="Electronica Unplugged 2"),
 "ozone-cloud":dict(album="Dark Synthwave (V/A)"),"night-lights-2":dict(album="Dark Synthwave (V/A)"),
 "recycle-2-1":dict(album="Vaporwave Is Alive And Well")}
LIC = {"light-part-2":"CC BY-ND 3.0","different-but-equivalent":"CC0 1.0 (Public Domain)","streetlight-noir":"CC BY-NC-ND 3.0",
 "so-in-love-with-you":"CC BY-NC-ND 3.0","pk-jazz-cool":"CC BY-NC-SA 4.0","ozone-cloud":"CC BY-NC-ND 4.0",
 "night-lights-2":"CC BY-NC-ND 4.0","recycle-2-1":"CC BY-SA 4.0","darling-i-miss-you":"CC BY-NC-ND 3.0",
 "was-that-away-message":"CC BY-NC-ND 2.5","hellfire":"CC BY-NC-SA 2.0 FR","dame-chocolate":"CC BY-NC-ND 2.5 ES",
 "es-kann-nicht-ewig-winter":"CC BY-NC-SA 3.0"}
ACCENT = {"light-part-2":"#8fd06a","different-but-equivalent":"#f0763f","streetlight-noir":"#d8b06a",
 "so-in-love-with-you":"#f2607a","pk-jazz-cool":"#e8c46a","ozone-cloud":"#b06ae8","night-lights-2":"#7ad0e8",
 "recycle-2-1":"#2f6bff","darling-i-miss-you":"#ff4fd8","was-that-away-message":"#8ef0c0",
 "hellfire":"#8fe8b8","dame-chocolate":"#4fd8c0","es-kann-nicht-ewig-winter":"#a9c4f2"}
ORDER = ["streetlight-noir","so-in-love-with-you","pk-jazz-cool","dame-chocolate","ozone-cloud","night-lights-2",
 "recycle-2-1","darling-i-miss-you","was-that-away-message","hellfire","es-kann-nicht-ewig-winter",
 "light-part-2","different-but-equivalent"]

def pick_file(m, want):
    best = None
    for f in m["files"]:
        n = f.get("name", "")
        if not n.lower().endswith(".mp3") or "spectrogram" in n: continue
        t = norm(f.get("title", "")) or norm(n)
        if norm(want) not in t and norm(want)[:18] not in t: continue
        fmt = f.get("format", "MP3"); rank = FMT.get(fmt, 5); size = int(f.get("size", 0))
        try:
            L = str(f.get("length", "0")); ln = float(L) if ":" not in L else sum(float(x)*60**k for k, x in enumerate(reversed(L.split(":"))))
        except Exception: ln = 0
        if best is None or (rank, size) < best[0]: best = ((rank, size), f, ln)
    return best

# ── generative covers for items that ship only low-res art ──
S = 800
def gen_sprite(tid, seed, pal, bg):
    rnd = random.Random(seed); N = 10; c = (S//2)//N
    grid = [[pal[int(rnd.random()*len(pal))] if rnd.random() > .45 else None for _ in range(N)] for _ in range(2*N)]
    im = Image.new("RGB", (S, S), bg); d = ImageDraw.Draw(im)
    for y in range(2*N):
        for x in range(2*N):
            col = grid[y][x] if x < N else grid[y][2*N-1-x]
            if col: d.rectangle([x*c, y*c, (x+1)*c-1, (y+1)*c-1], fill=col)
    im = im.filter(ImageFilter.GaussianBlur(.5)); d = ImageDraw.Draw(im)
    ov = Image.new("RGBA", (S, S), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for y in range(0, S, 4): od.line([0, y, S, y], fill=(0, 0, 0, 70), width=2)
    od.rectangle([0, 0, S-1, S-1], outline=pal[0], width=14)
    return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
def gen_wave(tid, seed, pal, bg):
    rnd = random.Random(seed); im = Image.new("RGB", (S, S), bg); d = ImageDraw.Draw(im)
    for i, (col, amp, off, w) in enumerate(zip(pal, [70, 50, 34, 22], [.30, .46, .62, .78], [3, 3, 2, 2])):
        pts = [(x, S*off + math.sin(x/140 + i*1.1)*amp + math.sin(x/47 + i)*amp*.22) for x in range(0, S+8, 8)]
        d.line(pts, fill=col, width=w, joint="curve")
    d.ellipse([S*.62, S*.10, S*.90, S*.38], outline=pal[0], width=3)
    return im
GEN = {"darling-i-miss-you": ("sprite", ["#ff4fd8", "#4df0ff", "#ffe14d", "#7bff6b"], (20, 12, 44)),
       "was-that-away-message": ("sprite", ["#5cf2c3", "#f2e15c", "#f2705c", "#8fb8ff"], (10, 28, 34)),
       "es-kann-nicht-ewig-winter": ("wave", ["#dfe8ff", "#a9bfe8", "#7d93c4", "#f2ede4"], (16, 20, 32))}

def palette(p):
    im = Image.open(p).convert("RGB").resize((64, 64))
    cols = sorted(im.quantize(colors=24, method=Image.FASTOCTREE).convert("RGB").getcolors(64*64) or [], reverse=True)
    def score(c):
        r, g, b = c; mx, mn = max(r, g, b), min(r, g, b)
        return (mx-mn)/255*(.35+.65*mx/255)
    vivid = max(cols[:14], key=lambda x: score(x[1]))[1] if cols else (160, 92, 255)
    deep = min(cols[:14], key=lambda x: sum(x[1]))[1] if cols else (10, 10, 20)
    return "#%02x%02x%02x" % vivid, "#%02x%02x%02x" % deep

def save_cover(im, tid):
    im = ImageOps.fit(im.convert("RGB"), (S, S), Image.LANCZOS, centering=(.5, .45))
    im.save(f"{COV}/{tid}.jpg", quality=88, optimize=True)

def work(p):
    ident, want, genre, mood, sl = p
    m = meta(ident); md = m["metadata"]
    got = pick_file(m, want)
    if not got: return None
    _, f, ln = got
    dst = f"{MEDIA}/{sl}.mp3"
    if not (SKIP and os.path.exists(dst)):
        open(dst, "wb").write(get(f"https://archive.org/download/{ident}/{urllib.parse.quote(f['name'])}"))
    cpath = f"{COV}/{sl}.jpg"
    if not (SKIP and os.path.exists(cpath)):
        if sl in REAL:
            i2, nm = REAL[sl]
            save_cover(Image.open(io.BytesIO(get(f"https://archive.org/download/{i2}/{urllib.parse.quote(nm)}"))), sl)
        else:
            kind, pal, bg = GEN[sl]
            im = gen_sprite(sl, hash(sl) % 100000, pal, bg) if kind == "sprite" else gen_wave(sl, hash(sl) % 100000, pal, bg)
            if sl == "es-kann-nicht-ewig-winter": im = Image.blend(im, Image.new("RGB", (S, S), (230, 238, 250)), .28)
            save_cover(im, sl)
    lic = md.get("licenseurl") or ""
    if isinstance(lic, list): lic = lic[0]
    artist = f.get("artist") or md.get("creator") or ident
    if isinstance(artist, list): artist = artist[0]
    artist = re.sub(r"^\[[^\]]*\]\s*", "", str(artist)).strip()
    title = re.sub(r"^\d+[\. )-]+", "", str(f.get("title") or want).strip())
    _, deep = palette(cpath)
    return {"id": sl, "title": title, "artist": artist, "album": str(md.get("title") or ident), "genre": genre,
            "mood": mood, "duration": round(ln, 1), "file": f"media/{sl}.mp3", "bytes": os.path.getsize(dst),
            "cover": f"covers/{sl}.jpg", "year": str(md.get("date", ""))[:4], "license": str(lic),
            "licenseName": LIC[sl], "source": f"https://archive.org/details/{ident}", "sourceId": ident,
            "accent": ACCENT[sl], "deep": deep}

recs = {}
with cf.ThreadPoolExecutor(3) as ex:
    for r in ex.map(work, PICKS):
        if r: recs[r["id"]] = r; print(f"  ok {r['title'][:36]:38} {r['artist'][:22]:24} {round(r['bytes']/1e6,1)}MB")
lib = []
for i, tid in enumerate(ORDER):
    t = recs[tid]; t.update(FIX.get(tid, {})); t["n"] = i + 1; lib.append(t)
json.dump(lib, open(f"{OUT}/library.json", "w"), indent=1)
print(f"library.json: {len(lib)} tracks, {sum(t['bytes'] for t in lib)/1e6:.1f} MB")
