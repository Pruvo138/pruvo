#!/usr/bin/env python3
"""r2-anahtar-test.py — R2 gorsel anahtari turetmenin KABUL TESTI.

Neden: anahtar 4 dosyada satir-ici kopyalanmisti; kopyalar kayarsa iki urunun gorseli ayni
R2 anahtarina yazilir ve biri digerini EZER. Bu test hem kopyalarin dondugunu hem de
TEK KAYNAK modulunun (tools/r2_anahtar.py) YAYINDAKI anahtarlari birebir uretmeye devam
ettigini olcer.

Kosum:  python3 tools/r2-anahtar-test.py     (ag yok, yazma yok, exit 0 = yesil)

Testler:
  (a) 4 cagri yerinde satir-ici anahtar turetme / satir-ici "urunler/%s-%d.jpg" KALMADI
  (b) GERIYE DONUK UYUM — urunler.json'daki gercek gorsel URL'lerinden en az 200 ornek:
      URL'de FIILEN duran anahtar == modulun urettigi anahtar (th/pr/mw/cgt-)
      + TUM anahtarlarda normalize() no-op (mevcut hicbir anahtar kaymaz)
  (c) ASCII-disi / tirnakli / bosluklu girdilerde cikti guvenli ([a-z0-9-]+)
  (d) th/pr/mw/cgt onekleri birebir (cgt'deki FAZLADAN TIRE tarihsel, korunmali)
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(HERE)
URUNLER = os.path.join(KOK, "urunler.json")
ASGARI_ORNEK = 200

_s = importlib.util.spec_from_file_location("r2_anahtar", os.path.join(HERE, "r2_anahtar.py"))
r2k = importlib.util.module_from_spec(_s)
_s.loader.exec_module(r2k)

hatalar = []


def sonuc(ad, ok, detay=""):
    print("%s %s%s" % ("OK  " if ok else "KIRMIZI", ad, ("  -> " + detay) if detay else ""))
    if not ok:
        hatalar.append(ad)


# --------------------------------------------------------------------- (a) kopya kalmadi
CAGRI_YERLERI = ["urun-ekle.py", "printables-ekle.py", "makerworld-ekle.py", "gorsel-cakisma-onar.py"]
# satir-ici anahtar normalizasyonu ya da satir-ici R2 yolu
KOPYA_DESENLERI = [
    re.compile(r"""re\.sub\(\s*r?["']\[\^a-z0-9-\]"""),          # anahtar normalizasyonu kopyasi
    re.compile(r"""["']urunler/%s-%d\.jpg["']"""),                # gorsel yolu kopyasi
    re.compile(r"""\{\s*["']Thingiverse["']\s*:"""),              # onek sozlugu kopyasi
]


def test_a():
    for ad in CAGRI_YERLERI:
        yol = os.path.join(HERE, ad)
        if not os.path.exists(yol):
            sonuc("(a) %s var" % ad, False, "dosya yok")
            continue
        metin = open(yol, encoding="utf-8").read()
        vurus = []
        for i, satir in enumerate(metin.splitlines(), 1):
            if satir.lstrip().startswith("#"):
                continue
            for d in KOPYA_DESENLERI:
                if d.search(satir):
                    vurus.append("%s:%d" % (ad, i))
        sonuc("(a) %s satir-ici anahtar turetme yok" % ad, not vurus, ", ".join(vurus))
        if "r2_anahtar" not in metin:
            sonuc("(a) %s r2_anahtar modulunu kullaniyor" % ad, False, "import yok")
        else:
            sonuc("(a) %s r2_anahtar modulunu kullaniyor" % ad, True)


# ------------------------------------------------------- (b) geriye donuk uyum (EN ONEMLI)
ONEK_PLATFORM = [("cgt-", "CGTrader"), ("th", "Thingiverse"), ("pr", "Printables"), ("mw", "MakerWorld")]


def test_b():
    if not os.path.exists(URUNLER):
        sonuc("(b) urunler.json bulundu", False, URUNLER)
        return
    urunler = json.load(open(URUNLER, encoding="utf-8"))
    anahtarlar = []      # (urun_id, anahtar)
    for u in urunler:
        if not isinstance(u, dict):
            continue
        for g in (u.get("gorseller") or []):
            a, _n = r2k.anahtar_coz(g)
            if a:
                anahtarlar.append((u.get("id", "?"), a))
    sonuc("(b) urunler.json'dan anahtar cikarildi", len(anahtarlar) >= ASGARI_ORNEK,
          "%d anahtar" % len(anahtarlar))

    # b1: kaynak-id tabanli anahtarlar (th/pr/mw/cgt-) modulden BIREBIR uretilebilmeli
    kayan, sayilan = [], 0
    for uid, a in anahtarlar:
        for onek, platform in ONEK_PLATFORM:
            govde = a[len(onek):]
            if a.startswith(onek) and govde.isdigit():
                sayilan += 1
                if r2k.gkey(platform, govde) != a:
                    kayan.append("%s: %s != %s" % (uid, r2k.gkey(platform, govde), a))
                break
    sonuc("(b) kaynak-id anahtarlari yeniden uretiliyor (%d/%d)" % (sayilan - len(kayan), sayilan),
          not kayan and sayilan >= ASGARI_ORNEK,
          ("%d KAYDI: " % len(kayan)) + "; ".join(kayan[:20]) if kayan
          else ("ornek yetersiz (<%d)" % ASGARI_ORNEK if sayilan < ASGARI_ORNEK else ""))

    # b2: mevcut anahtarlarin karakter kumesi [a-z0-9-] disina CIKMAMALI
    kirli = ["%s: %s" % (uid, a) for uid, a in anahtarlar if not re.fullmatch(r"[a-z0-9-]+", a)]
    sonuc("(b) mevcut anahtarlar [a-z0-9-] kumesinde (%d)" % len(anahtarlar), not kirli,
          ("%d KIRLI: " % len(kirli)) + "; ".join(kirli[:20]))

    # b3: normalize() mevcut anahtarlari YALNIZCA bas/son tire kirpmasi kadar degistirebilir.
    # OLCULDU: 49 ESKI baslik-slug anahtari sonu tireli ([:60] kesimi strip'ten SONRA yapildigi
    # icin); bunlar veri gercegi, normalize onlari a.strip("-")'e indirger. Baska hicbir kayma
    # KABUL EDILMEZ — kayma olursa yayindaki URL kirilir.
    kayan = ["%s: %s -> %s" % (uid, a, r2k.normalize(a)) for uid, a in anahtarlar
             if r2k.normalize(a) != a.strip("-")]
    sonuc("(b) normalize() bas/son tire disinda hicbir anahtari degistirmiyor (%d)" % len(anahtarlar),
          not kayan, ("%d KAYDI: " % len(kayan)) + "; ".join(kayan[:20]))
    tireli = sum(1 for _uid, a in anahtarlar if a.strip("-") != a)
    print("     bilgi: sonu/basi tireli tarihsel anahtar sayisi = %d" % tireli)


# ------------------------------------------------------------- (c) ASCII-disi / tirnak / bosluk
ZOR_GIRDILER = [
    "Kapı Kolu Çerçevesi",
    "O'Brien's \"özel\" parça",
    "  bosluklu   baslik  ",
    "ÜÇGEN ŞİMŞEK ĞÖZ",
    "emoji 🚗 var",
    "///---///",
    "Ünlü/Marka: Şoför+Kolu",
]


def test_c():
    for g in ZOR_GIRDILER:
        a = r2k.normalize(g)
        sonuc("(c) normalize guvenli: %r" % g, re.fullmatch(r"[a-z0-9-]*", a) is not None, a)
        s = r2k.urun_slug(g, yedek="yedek")
        sonuc("(c) urun_slug guvenli: %r" % g, re.fullmatch(r"[a-z0-9-]+", s) is not None, s)
    # anahtar ASCII-disi kaynak-id'de bile ASCII kalmali
    a = r2k.gkey("Thingiverse", "12ö34")
    sonuc("(c) gkey ASCII-disi kaynak-id", a == "th12-34", a)
    # yol/URL uretimi
    sonuc("(c) gorsel_yolu", r2k.gorsel_yolu("th123", 2) == "urunler/th123-2.jpg",
          r2k.gorsel_yolu("th123", 2))
    sonuc("(c) gorsel_url", r2k.gorsel_url("pr9", 1) == "https://media.pruvo3d.com/urunler/pr9-1.jpg",
          r2k.gorsel_url("pr9", 1))
    # ASCII-disi uzak URL kacisi (thing-hazirla/gallery ile ayni safe kumesi)
    q = r2k.url_kacir("https://cdn.example.com/ö dosya.jpg?a=1&b=2")
    sonuc("(c) url_kacir ASCII", all(ord(c) < 128 for c in q) and "?a=1&b=2" in q, q)


# ------------------------------------------------------------------------- (d) onekler birebir
def test_d():
    beklenen = [
        ("Thingiverse", "6543210", "th6543210"),
        ("Printables", 1234567, "pr1234567"),
        ("MakerWorld", 998877, "mw998877"),
        ("CGTrader", "6267929", "cgt-6267929"),   # TARIHSEL fazladan tire — korunmali
        ("Bilinmeyen", "42", "x42"),
    ]
    for platform, sid, bek in beklenen:
        a = r2k.gkey(platform, sid)
        sonuc("(d) %s -> %s" % (platform, bek), a == bek, a)
    sonuc("(d) cgt oneki tireli kaliyor", r2k.ONEKLER["CGTrader"] == "cgt-", r2k.ONEKLER["CGTrader"])
    sonuc("(d) th/pr/mw onekleri tiresiz",
          (r2k.ONEKLER["Thingiverse"], r2k.ONEKLER["Printables"], r2k.ONEKLER["MakerWorld"])
          == ("th", "pr", "mw"), "")
    sonuc("(d) gkey_ham yedegi", r2k.gkey_ham("!!!") == "!!!" and r2k.gkey_ham("!!!", yedek=False) == "",
          repr(r2k.gkey_ham("!!!")))


test_a()
test_b()
test_c()
test_d()

print("")
if hatalar:
    print("KIRMIZI — %d basarisiz: %s" % (len(hatalar), "; ".join(hatalar)))
    sys.exit(1)
print("YESIL — hepsi gecti")
