#!/usr/bin/env python3
"""Bir Thingiverse modelinin TUM galeri gorsellerini tam boy indirir.
Kullanim: python3 tools/thingiverse-gallery.py <thing_id> <cikti_dizini> <onek>
Her gorseli <cikti>/<onek>_<n>.jpg olarak kaydeder, listeyi yazar.
"""
import sys, os, json, urllib.request, urllib.parse, re, subprocess

# ASCII-disi karakter iceren CDN url'leri urlopen'da UnicodeEncodeError ile cokerdi
# (HTTP istek satiri/basligi ASCII olmali). thing-hazirla.py ile AYNI kacis: safe kumesi
# tutarli olsun (bkz thing-hazirla.py satir 93).
_SAFE = ":/?=&%"


def qesc(u):
    return urllib.parse.quote(u, safe=_SAFE)

TOKEN = open(os.path.join(os.path.dirname(__file__), "..", ".thingiverse-token")).read().strip()


def get(u):
    r = urllib.request.Request(qesc(u), headers={"Authorization": "Bearer " + TOKEN, "User-Agent": "pruvo/1.0"})
    return urllib.request.urlopen(r).read()


def raw_url(im):
    # en buyuk display/preview boyutundan ham cdn url'sini cikar
    best = None
    for s in im.get("sizes", []):
        u = s.get("url", "")
        m = re.search(r"url=(https://cdn\.thingiverse\.com/[^&]+)", u)
        if m:
            best = m.group(1)
        elif u.startswith("https://cdn.thingiverse.com/"):
            best = u
    return best


def main():
    tid, outdir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    imgs = json.loads(get("https://api.thingiverse.com/things/%s/images" % tid))
    seen = set()
    n = 0
    for im in imgs:
        u = raw_url(im)
        if not u or u in seen:
            continue
        seen.add(u)
        n += 1
        ext = ".png" if u.lower().endswith(".png") else ".jpg"
        raw = os.path.join(outdir, "%s_%d%s" % (prefix, n, ext))
        data = urllib.request.urlopen(urllib.request.Request(qesc(u), headers={"User-Agent": "Mozilla/5.0"})).read()
        with open(raw, "wb") as f:
            f.write(data)
        jpg = os.path.join(outdir, "%s_%d.jpg" % (prefix, n))
        if ext != ".jpg":
            subprocess.run(["sips", "-s", "format", "jpeg", raw, "--out", jpg],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("%s_%d.jpg  <- %s" % (prefix, n, u.split("/")[-1]))
    print("TOPLAM", n)


if __name__ == "__main__":
    main()
