#!/usr/bin/env python3
"""Kabul testi: thingiverse-gallery.py ASCII-disi URL'de COKMEZ (UnicodeEncodeError).

Kok neden: HTTP istek satiri/basligi ASCII olmali; percent-encode edilmemis ASCII-disi
url urllib.request.urlopen'da 'ascii' codec UnicodeEncodeError ile cokerdi -> galeri
partisinde SESSIZ gorsel kaybi (orneklemde 1/28). Kardes arac thing-hazirla.py ayni
url'yi urllib.parse.quote(url, safe=":/?=&%") ile kaciriyordu; gallery kacirmiyordu.

Ag cagrisi MOCK'lanir (gercek Thingiverse'e GIDILMEZ) — yalniz URL-kacis mantigi olculur.
Kosum: python3 tools/thingiverse-gallery-test.py
"""
import importlib.util, io, os, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GALLERY = os.path.join(ROOT, "tools", "thingiverse-gallery.py")
TOKENF = os.path.join(ROOT, ".thingiverse-token")

# thing-hazirla.py satir 93 ile AYNI kacis (referans dogru davranis)
REF_SAFE = ":/?=&%"
def ref_esc(u):
    return urllib.parse.quote(u, safe=REF_SAFE)

NONASCII = "https://cdn.thingiverse.com/assets/ürün-görsel-ölçü.jpg"
ASCII = "https://cdn.thingiverse.com/assets/plain-image-123.jpg"


def load_gallery():
    # Modul import-aninda TOKEN dosyasini okur; gitignore geregi worktree'de yoksa
    # gecici sahte token yaz (yalniz biz yarattiysak sonra sil).
    created = False
    if not os.path.exists(TOKENF):
        open(TOKENF, "w").write("TEST-TOKEN")
        created = True
    try:
        spec = importlib.util.spec_from_file_location("tv_gallery", GALLERY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if created:
            os.remove(TOKENF)


def main():
    mod = load_gallery()
    fails = []

    # 1) qesc: ASCII-disi url -> ASCII-encodable (cokmenin onlendigi tek kosul)
    esc = mod.qesc(NONASCII)
    try:
        esc.encode("ascii")
    except UnicodeEncodeError:
        fails.append("qesc(NONASCII) hala ASCII-disi: %r" % esc)

    # 2) qesc thing-hazirla ile AYNI sonucu vermeli (safe kumesi tutarli)
    if esc != ref_esc(NONASCII):
        fails.append("qesc thing-hazirla ile uyumsuz: %r != %r" % (esc, ref_esc(NONASCII)))

    # 3) ASCII url BOZULMADAN gecmeli
    if mod.qesc(ASCII) != ASCII:
        fails.append("ASCII url degisti: %r" % mod.qesc(ASCII))

    # 4) ENTEGRASYON: get() urlopen'a verilen url ASCII olmali (urlopen MOCK)
    captured = {}
    real_urlopen = urllib.request.urlopen
    def fake_urlopen(req, *a, **k):
        captured["url"] = req.full_url if hasattr(req, "full_url") else req
        return io.BytesIO(b"OK")
    urllib.request.urlopen = fake_urlopen
    try:
        mod.get(NONASCII)
    except UnicodeEncodeError as e:
        fails.append("get(NONASCII) UnicodeEncodeError ile cokuyor: %s" % e)
    finally:
        urllib.request.urlopen = real_urlopen
    if "url" in captured:
        try:
            captured["url"].encode("ascii")
        except UnicodeEncodeError:
            fails.append("get() urlopen'a ASCII-disi url verdi: %r" % captured["url"])

    if fails:
        print("KIRMIZI:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("YESIL: 4/4 kontrol gecti (qesc ascii + hazirla-uyum + ascii-bozulmaz + get-entegrasyon)")


if __name__ == "__main__":
    main()
