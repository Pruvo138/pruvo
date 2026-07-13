#!/usr/bin/env python3
"""SARI SERI render uretici — Gemini 2.5 Flash Image ("Nano Banana") ile foto-gercekci
sari FDM urun render'i uretir. SVG/vektor REDDEDILDI; bu gercek AI render.

Kullanim:
  # Tek serbest prompt:
  python3 tools/gemini-render.py <cikti.png> "<prompt>"

  # Parametrik urun(ler) icin sari-seri render (PARCALAR haritasindan prompt kurar):
  python3 tools/gemini-render.py --urun <id> [<id> ...]
      -> scratchpad'e <id>.png yazar (SCRATCH altinda). Okan gozle onaylar, sonra olceklenir.

Anahtar: `.gemini-key` (gitignore, 1. satir = API key). Ayni anahtar metin+gorsel uretir.
Harici pip paketi YOK (duz REST). Model: gemini-2.5-flash-image (generateContent),
gorsel yanitta candidates[].content.parts[].inlineData.data (base64 png) doner.

KURALLAR (CLAUDE.md SARI SERI):
- Coklu-sekil kalibi: ailenin birden cok sekli bir arada, mat SARI FDM, ince katman cizgileri.
- LOGO/YAZI YOK. Sari SADECE bu seride. Temiz sicak kirik-beyaz studio zemin, sol-ust yumusak isik.
"""
import base64, json, os, sys, time, urllib.request, urllib.error

ROOT = "/Users/okan/dev/pruvo"
KEYFILE = os.path.join(ROOT, ".gemini-key")
MODEL = "gemini-2.5-flash-image"
RETRYABLE = (429, 500, 503)
SCRATCH = ("/private/tmp/claude-501/-Users-okan-dev-pruvo--claude-worktrees-goofy-merkle-89ddc6/"
           "2ea8fedd-d8a4-4ea7-9a32-d2c2625e9d87/scratchpad")

# Coklu-sekil sari FDM kalibi. {parcalar} ureune gore doldurulur.
TEMPLATE = ("Photorealistic 3D product render of a group of several different matte YELLOW "
            "FDM 3D-printed {parcalar}, visible fine layer lines, arranged together on a clean "
            "warm off-white studio background, soft top-left light, gentle contact shadow, "
            "centered, product photography, no text, no logo, no watermark")

# parametrik urun id -> [PARCALAR] (ailenin birden cok somut sekli, ingilizce)
PARCALAR = {
    "olcuye-ozel-oring-conta":
        "O-rings and seal gaskets of several different diameters and cross-sections",
    "olcuye-ozel-profil-beam":
        "structural extrusion profiles: an I-beam, a T-slot bar, a square tube and a U-channel",
    "ozel-disli-kramayer-uretimi":
        "mechanical gears: a spur gear, a helical gear, a bevel gear, a ring gear and a straight rack",
    "olcuye-ozel-vida-civata-somun-pul":
        "fasteners: bolts, screws, hex nuts, washers and a threaded rod of different sizes",
    "olcuye-ozel-rulman":
        "plastic ball bearings of several different diameters",
    "olcuye-ozel-triger-kayisi":
        "GT2 and HTD timing belts, both closed-loop and open lengths",
    "olcuye-ozel-triger-kasnagi":
        "timing belt pulleys of several tooth counts and bore sizes",
    "olcuye-ozel-montaj-braketi":
        "mounting brackets: an angle bracket, an L bracket, a T bracket and a flat bracket",
    "olcuye-ozel-baglanti-konektor":
        "modular joint connectors for rods, tubes and profiles",
    "olcuye-ozel-yay-dalga-flexure":
        "compression springs, wave springs and serpentine flexures",
    "olcuye-ozel-petek-delikli-panel":
        "honeycomb and perforated grid panels of different hole patterns",
    "olcuye-ozel-huni":
        "funnels of several different sizes with straight and angled spouts",
    "olcuye-ozel-izgara-menfez-kapak":
        "vent grilles, louvered covers and register caps of different sizes",
    "olcuye-ozel-pervane-fan-cark":
        "impellers, fan rotors and centrifugal wheels of different blade counts",
    "olcuye-ozel-ramp-sim-takoz":
        "leveling ramps, shims and wedge blocks of different angles",
    "olcuye-ozel-cetvel":
        "measuring tools: a straight ruler, a triangle square and an L square",
    "olcuye-ozel-damga-kase":
        "custom stamps and seals with blank plates (no text on the plates)",
    "kisiye-ozel-jeton-cip-madalyon":
        "round tokens, poker chips and blank medallions of different diameters",
}


def load_key():
    if not os.path.exists(KEYFILE):
        sys.exit("HATA: .gemini-key yok -> " + KEYFILE)
    lines = [x.strip() for x in open(KEYFILE).read().splitlines() if x.strip()]
    return lines[0]


def _one_call(key, body):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s"
           % (MODEL, key))
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    raw = urllib.request.urlopen(req, timeout=180).read()
    return json.loads(raw)


def _extract_image(resp):
    """candidates[].content.parts[].inlineData.data (base64 png) bul."""
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return inline["data"], inline.get("mimeType") or inline.get("mime_type", "image/png")
    return None, None


def render(prompt, outpath, key):
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }).encode("utf-8")
    last = ""
    for attempt in range(4):
        try:
            resp = _one_call(key, body)
        except urllib.error.HTTPError as e:
            last = "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300])
            if e.code in RETRYABLE and attempt < 3:
                time.sleep(4 * (attempt + 1)); continue
            sys.exit("Gemini render basarisiz: " + last)
        except Exception as e:
            last = str(e)
            if attempt < 3:
                time.sleep(4 * (attempt + 1)); continue
            sys.exit("Gemini render basarisiz: " + last)
        data, mime = _extract_image(resp)
        if not data:
            # bazen guvenlik/istek reddi metinle doner -> gorunur kil
            txt = json.dumps(resp, ensure_ascii=False)[:400]
            if attempt < 3:
                time.sleep(4 * (attempt + 1)); continue
            sys.exit("Gorsel yok, yanit: " + txt)
        open(outpath, "wb").write(base64.b64decode(data))
        return mime
    sys.exit("Gemini render basarisiz: " + last)


def urun_prompt(uid):
    if uid not in PARCALAR:
        sys.exit("HATA: '%s' PARCALAR haritasinda yok. Ekle veya serbest prompt kullan." % uid)
    return TEMPLATE.format(parcalar=PARCALAR[uid])


def main(argv):
    key = load_key()
    if argv and argv[0] == "--urun":
        ids = argv[1:]
        if not ids:
            sys.exit("Kullanim: python3 tools/gemini-render.py --urun <id> [<id> ...]")
        for uid in ids:
            prompt = urun_prompt(uid)
            outpath = os.path.join(SCRATCH, uid + ".png")
            print("=== %s ===" % uid)
            print("   prompt:", prompt)
            mime = render(prompt, outpath, key)
            print("   -> %s (%s)\n" % (outpath, mime))
        return
    if len(argv) < 2:
        sys.exit(__doc__)
    outpath, prompt = argv[0], argv[1]
    mime = render(prompt, outpath, key)
    print("-> %s (%s)" % (outpath, mime))


if __name__ == "__main__":
    main(sys.argv[1:])
