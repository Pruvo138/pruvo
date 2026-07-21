#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gorsel-boyut-test.py — tools/gorsel_boyut_kapisi.py KABUL TESTI.

NE KANITLAR:
  A. Boyut okuma saf Python ile DOGRU: PNG (tam gecerli, zlib ile uretilir), JPEG (SOFn
     basligi), WebP (VP8/VP8L/VP8X), GIF. Harici kutuphane GEREKMEZ (CI'da PIL olmayabilir).
  B. GERCEK VAKA: 1000x88 -> ELENIR (Merchant "resim cok kucuk" reddi; olculen urun
     alfa-romeo-166-yak-t-kapa-ask-s), 1000x1000 -> GECER.
  C. Esik sinirlari: 100x100 GECER, 99x100 ELENIR; kisa kenar 799 -> UYARI ama GECER,
     800 -> uyari YOK.
  D. FAIL-LOUD: boyutu okunamayan dosya ELENMEZ ('olculemeyen' + gecen) — yeni kapi
     ekleme akisini SESSIZCE oldurmez.
  E. secili_ele SIRAYI korur ve yalniz kucuk olani duser (ekleme hattinin cagirdigi imza).
  F. 🔴 KABLOLAMA — DAVRANISLA (metinle DEGIL): uc ekleme betigi (urun-ekle / printables-ekle /
     makerworld-ekle) GERCEKTEN import edilir (importlib exec_module; patlarsa KIRMIZI) ve
     process_one() sentetik bir cache dizini + sahte upload ile UCTAN UCA kosturulur.
     1000x88 gorselin R2 upload'una HIC ULASMADIGI olculur.
  G. AYNI AKISTA KONTROL KOSUMU: yalniz ORTA gorselin YUKSEKLIGI degistirilir (88 -> 900);
     ayni desen, ayni sira, ayni akis -> bu kez UCU DE yuklenir. Boylece "gorsel baska bir
     sebeple (or. algisal mukerrer kapisi) dusmus olabilir" acigi kapanir: tek degisken boy.
  H. AKIS FAIL-LOUD: boyutu OKUNAMAYAN gorsel akista da ELENMEZ (MaCiT'in hatti sessizce
     olmez), yalnizca stderr'e uyari basilir.

⚠️ F/G/H NEDEN VAR (olculdu, 1. tur): kablolama nobetcisi METIN tabanliydi ("dosyada
'gbk.secili_ele(' geciyor mu") ve SAHTE YESIL veriyordu — cagrinin DONEN DEGERI atilinca
("_atilan, _bres = ...") ya da cagri "if False:" altina alininca hicbir gorsel elenmedigi
hâlde test YESIL kaliyordu. Ayrica "[PASS] <betik> modul yukleniyor" iddiasi OLCUM DEGILDI:
o betikler ROOT sabiti yuzunden GERCEKTEN import edilemiyorken bile PASS basiyordu.

⚠️ FIKSTUR DURUSTLUGU: PNG/GIF/WebP fiksturleri BAYT BAYT gecerli dosyalardir. JPEG
fiksturu SOI+APP0+SOF0+EOI'dan ibaret bir BASLIK fiksturudur (entropi verisi yok) —
kapinin JPEG yolu zaten yalniz SOFn basligini okur. Gercek bir JPEG uzerindeki dogrulama
CI DISINDA olculdu (canli alfa-romeo gorseli: 1000x88, kapi ELEDI) ve RAPOR-MIMARA.md'de
kayitlidir; gorsel dosyasi repoya EKLENMEZ (git'e gorsel girmez kurali).

Salt-okunur (yalniz gecici dizine yazar), ag'a cikmaz. Cikis: 0 = yesil, 1 = kirmizi.
Calistir:  python3 tools/gorsel-boyut-test.py
"""
import importlib.util
import json
import os
import struct
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def _yukle(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(HERE, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(etiket, kosul, detay=""):
    print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", etiket, ("  -> " + detay) if detay else ""))
    if not kosul:
        FAILS.append(etiket)
    return kosul


# ---------------------------------------------------------------- fikstur ureticiler
def png_yaz(yol, w, h):
    """TAM GECERLI 8-bit gri PNG (harici kutuphane yok)."""
    def parca(tur, veri):
        return (struct.pack(">I", len(veri)) + tur + veri
                + struct.pack(">I", zlib.crc32(tur + veri) & 0xFFFFFFFF))
    ham = b"".join(b"\x00" + bytes(w) for _ in range(h))     # her satir: filtre 0 + siyah
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(parca(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)))
        f.write(parca(b"IDAT", zlib.compress(ham, 6)))
        f.write(parca(b"IEND", b""))
    return yol


def png_desenli(yol, w, h, tohum):
    """TAM GECERLI gri PNG — 17x16 KABA blok deseni (tohuma gore) buyutulerek doldurulur.

    Neden desen: ekleme hattinda boyut kapisindan ONCE ALGISAL MUKERRER kapisi (dHash 16x16)
    kosuyor. Duz siyah fiksturler birbirinin algisal IKIZI olur ve gorseller boyut yuzunden
    DEGIL mukerrerlik yuzunden duserdi -> kabul testi yanlis sebeple yesil yanardi. Kaba blok
    deseni yeniden-boyutlandirmadan SAG CIKAR, farkli tohum farkli dHash uretir."""
    rnd = tohum * 1103515245 + 12345
    blok = []
    for _ in range(16):
        satir = []
        for _ in range(17):
            rnd = (rnd * 1103515245 + 12345) & 0x7FFFFFFF
            satir.append((rnd >> 16) & 0xFF)
        blok.append(satir)

    def parca(tur, veri):
        return (struct.pack(">I", len(veri)) + tur + veri
                + struct.pack(">I", zlib.crc32(tur + veri) & 0xFFFFFFFF))

    satirlar = []
    for y in range(h):
        by = min(15, (y * 16) // h)
        satirlar.append(b"\x00" + bytes(blok[by][min(16, (x * 17) // w)] for x in range(w)))
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(parca(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)))
        f.write(parca(b"IDAT", zlib.compress(b"".join(satirlar), 6)))
        f.write(parca(b"IEND", b""))
    return yol


def jpeg_basligi_yaz(yol, w, h):
    """JPEG BASLIK fikstruu: SOI + APP0(JFIF) + SOF0(w,h) + EOI (bkz ustteki durustluk notu)."""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = (b"\xff\xc0" + struct.pack(">H", 11) + b"\x08" + struct.pack(">HH", h, w)
            + b"\x01\x01\x11\x00")
    with open(yol, "wb") as f:
        f.write(b"\xff\xd8" + app0 + sof0 + b"\xff\xd9")
    return yol


def gif_yaz(yol, w, h):
    with open(yol, "wb") as f:
        f.write(b"GIF89a" + struct.pack("<HH", w, h) + b"\x00\x00\x00")
    return yol


def webp_vp8l_yaz(yol, w, h):
    bits = (w - 1) | ((h - 1) << 14)
    govde = b"VP8L" + struct.pack("<I", 5) + b"\x2f" + struct.pack("<I", bits)
    with open(yol, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(govde)) + b"WEBP" + govde)
    return yol


def webp_vp8x_yaz(yol, w, h):
    veri = b"\x00\x00\x00\x00" + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little")
    govde = b"VP8X" + struct.pack("<I", len(veri)) + veri
    with open(yol, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(govde)) + b"WEBP" + govde)
    return yol


def webp_vp8_yaz(yol, w, h):
    veri = b"\x00\x00\x00" + b"\x9d\x01\x2a" + struct.pack("<HH", w, h) + b"\x00" * 4
    govde = b"VP8 " + struct.pack("<I", len(veri)) + veri
    with open(yol, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(govde)) + b"WEBP" + govde)
    return yol


# ---------------------------------------------------------------- akis (kablolama) kosumu
class _Kosum(object):
    returncode = 0
    stdout = ""
    stderr = ""


class _SahteSubprocess(object):
    """Ekleme betiklerinin subprocess'ini degistirir: thing-hazirla / thing-codex / sips
    CALISTIRILMAZ (ag + AI kredisi + macOS bagimliligi yok), hepsi basarili sayilir."""
    DEVNULL = -3
    PIPE = -1

    def __init__(self):
        self.cagrilar = []

    def run(self, *a, **kw):
        self.cagrilar.append(a[0] if a else None)
        return _Kosum()


_META = {"baslik": "Sentetik", "tasarimci": "x", "lisans": "Creative Commons - Attribution",
         "olcu_mm": [10, 20, 30], "stl_adet": 1, "baski": "", "abbr": "CC-BY", "slug": "s"}
_ONERI = {"baslik": "Sentetik Test Parcasi", "kategori": "Tamirat", "marka": [],
          "aciklama": "deneme", "fiyat_oneri": "250 TL"}


def _fikstur_yaz(dizin, olcular):
    """g1..gN.jpg fiksturlerini yazar. olcu (w,h) ise desenli PNG, 'BOZUK' ise okunamaz dosya."""
    os.makedirs(dizin, exist_ok=True)
    adlar = []
    for i, o in enumerate(olcular, 1):
        ad = "g%d.jpg" % i
        yol = os.path.join(dizin, ad)
        if o == "BOZUK":
            with open(yol, "wb") as f:
                f.write(b"bu bir gorsel degil" * 200)
        else:
            png_desenli(yol, o[0], o[1], tohum=i * 7 + 3)
        adlar.append(ad)
    return adlar


def _kos(mod, betik, kok, etiket, olcular):
    """Ekleme betiginin GERCEK process_one'ini sentetik girdiyle kosar.
    Doner (sonuc_sozlugu, R2'ye GIDEN dosya adlari)."""
    kdir = os.path.join(kok, "akis-%s-%s" % (betik.replace(".py", ""), etiket))
    yuklenen = []

    def _sahte_upload(local_jpg, key):
        yuklenen.append(os.path.basename(local_jpg))
        return "https://media.pruvo3d.com/" + key

    mod.subprocess = _SahteSubprocess()
    mod.sips_upload = _sahte_upload

    if betik == "urun-ekle.py":
        tid = "9000001"
        adlar = _fikstur_yaz(os.path.join(kdir, tid), olcular)
        mod.IMGROOT = kdir
        meta = dict(_META, id=tid)
        with open(os.path.join(kdir, tid, "meta.json"), "w") as f:
            json.dump(meta, f)
        with open(os.path.join(kdir, tid, "oneri.json"), "w") as f:
            json.dump(dict(_ONERI, sec_gorseller=adlar), f)
        return mod.process_one(tid), yuklenen

    if betik == "printables-ekle.py":
        pid, key = "900001", "pr900001"
        adlar = _fikstur_yaz(os.path.join(kdir, key), olcular)
        mod.CACHE = kdir
        meta = dict(_META, id=key, gorseller=adlar, pid=pid)
        with open(os.path.join(kdir, key, "oneri.json"), "w") as f:
            json.dump(dict(_ONERI, sec_gorseller=adlar), f)
        mod.prep = lambda p, k: (meta, "CC-BY", "Creative Commons - Attribution")
        return mod.process_one(pid), yuklenen

    did, key = "900002", "mw900002"
    adlar = _fikstur_yaz(os.path.join(kdir, key), olcular)
    mod.CACHE = kdir
    meta = dict(_META, id=key, gorseller=adlar, did=did)
    with open(os.path.join(kdir, key, "oneri.json"), "w") as f:
        json.dump(dict(_ONERI, sec_gorseller=adlar), f)
    mod.prep = lambda dd, k: (meta, "Creative Commons - Attribution")
    return mod.process_one(did), yuklenen


def _akis_dogrula(betik, kok):
    """GERCEK import + uctan uca akis: kucuk gorsel R2 upload'una ULASMAMALI."""
    ad = betik.replace("-", "_").replace(".py", "")
    try:
        mod = _yukle(ad, betik)                     # 🔴 GERCEK exec_module — patlarsa KIRMIZI
    except Exception as e:
        check("%s — GERCEK import (exec_module)" % betik, False,
              "%s: %s" % (type(e).__name__, e))
        return
    check("%s — GERCEK import (exec_module)" % betik, True)
    if not hasattr(mod, "process_one"):
        check("%s — process_one var" % betik, False)
        return

    # F) 1000x88 serit gorsel akista ELENMELI (R2'ye HIC gitmemeli).
    s, yuklenen = _kos(mod, betik, kok, "f", [(1000, 1000), (1000, 88), (900, 900)])
    check("%s — akis STAGED dondu" % betik, s.get("durum") == "STAGED", str(s.get("durum")))
    check("%s — 1000x88 R2'ye HIC gitmedi (kapi CANLI)" % betik,
          yuklenen == ["g1.jpg", "g3.jpg"], "yuklenen=%r" % yuklenen)
    check("%s — urun 2 gorselle STAGE edildi" % betik,
          len(((s.get("urun") or {}).get("gorseller")) or []) == 2,
          "gorsel=%d" % len(((s.get("urun") or {}).get("gorseller")) or []))

    # G) KONTROL: tek degisken orta gorselin BOYU (88 -> 900). Ayni desen/sira/akis.
    s2, yuklenen2 = _kos(mod, betik, kok, "g", [(1000, 1000), (1000, 900), (900, 900)])
    check("%s — kontrol kosumu: boy 900 olunca UCU DE yuklendi" % betik,
          s2.get("durum") == "STAGED" and yuklenen2 == ["g1.jpg", "g2.jpg", "g3.jpg"],
          "durum=%s yuklenen=%r" % (s2.get("durum"), yuklenen2))

    # H) FAIL-LOUD: olculemeyen gorsel akisi OLDURMEZ, elenmez de.
    s3, yuklenen3 = _kos(mod, betik, kok, "h", [(1000, 1000), "BOZUK", (900, 900)])
    check("%s — olculemeyen gorsel akista ELENMEDI (fail-loud)" % betik,
          s3.get("durum") == "STAGED" and yuklenen3 == ["g1.jpg", "g2.jpg", "g3.jpg"],
          "durum=%s yuklenen=%r" % (s3.get("durum"), yuklenen3))


def main():
    g = _yukle("gorsel_boyut_kapisi", "gorsel_boyut_kapisi.py")
    d = tempfile.mkdtemp(prefix="pruvo-gorsel-boyut-")

    print("A) Boyut okuma — saf Python, format basliklarindan")
    ornek = [
        ("png 1000x88", png_yaz(os.path.join(d, "a.png"), 1000, 88), (1000, 88)),
        ("png 640x480", png_yaz(os.path.join(d, "b.png"), 640, 480), (640, 480)),
        ("jpeg 1000x88", jpeg_basligi_yaz(os.path.join(d, "c.jpg"), 1000, 88), (1000, 88)),
        ("jpeg 1200x1200", jpeg_basligi_yaz(os.path.join(d, "dd.jpg"), 1200, 1200), (1200, 1200)),
        ("gif 300x200", gif_yaz(os.path.join(d, "e.gif"), 300, 200), (300, 200)),
        ("webp VP8L 1024x768", webp_vp8l_yaz(os.path.join(d, "f.webp"), 1024, 768), (1024, 768)),
        ("webp VP8X 2000x50", webp_vp8x_yaz(os.path.join(d, "g.webp"), 2000, 50), (2000, 50)),
        ("webp VP8  800x600", webp_vp8_yaz(os.path.join(d, "h.webp"), 800, 600), (800, 600)),
    ]
    for ad, yol, beklenen in ornek:
        check(ad, g.boyut(yol) == beklenen, "okundu=%r beklenen=%r" % (g.boyut(yol), beklenen))

    print("B) GERCEK VAKA — 1000x88 elenir, 1000x1000 gecer")
    kucuk = png_yaz(os.path.join(d, "serit.png"), 1000, 88)
    buyuk = png_yaz(os.path.join(d, "kare.png"), 1000, 1000)
    s = g.filtrele([kucuk, buyuk])
    check("1000x88 ELENDI", [e["yol"] for e in s["elenen"]] == [kucuk],
          "elenen=%r" % [os.path.basename(e["yol"]) for e in s["elenen"]])
    check("1000x1000 GECTI", s["gecen"] == [buyuk])
    check("1000x1000 uyari da vermez (kisa kenar >= %d)" % g.UYARI_KENAR, not s["uyari"])
    jk = jpeg_basligi_yaz(os.path.join(d, "serit.jpg"), 1000, 88)
    sj = g.filtrele([jk])
    check("ayni vaka JPEG basliginda da ELENIR", len(sj["elenen"]) == 1 and not sj["gecen"])

    print("C) Esik sinirlari")
    tam = png_yaz(os.path.join(d, "t100.png"), 100, 100)
    eksik = png_yaz(os.path.join(d, "t99.png"), 99, 100)
    s = g.filtrele([tam, eksik])
    check("100x100 GECER (sinir dahil)", tam in s["gecen"])
    check("99x100 ELENIR", [e["yol"] for e in s["elenen"]] == [eksik])
    u799 = png_yaz(os.path.join(d, "u799.png"), 1200, 799)
    u800 = png_yaz(os.path.join(d, "u800.png"), 1200, 800)
    s = g.filtrele([u799, u800])
    check("kisa kenar 799 -> UYARI ama GECER",
          [x["yol"] for x in s["uyari"]] == [u799] and u799 in s["gecen"])
    check("kisa kenar 800 -> uyari YOK", u800 in s["gecen"] and len(s["uyari"]) == 1)

    print("D) FAIL-LOUD — okunamayan dosya ELENMEZ")
    bozuk = os.path.join(d, "bozuk.jpg")
    with open(bozuk, "wb") as f:
        f.write(b"bu bir gorsel degil, sadece metin" * 4)
    s = g.filtrele([bozuk])
    check("olculemeyen isaretlendi", s["olculemeyen"] == [bozuk])
    check("olculemeyen ELENMEDI (akis olmuyor)", s["gecen"] == [bozuk] and not s["elenen"])

    print("E) secili_ele — ekleme hattinin cagirdigi sarmalayici")
    png_yaz(os.path.join(d, "g1.png"), 1000, 1000)
    png_yaz(os.path.join(d, "g2.png"), 1000, 88)
    png_yaz(os.path.join(d, "g3.png"), 900, 900)
    temiz, sonuc = g.secili_ele(d, ["g1.png", "g2.png", "g3.png"])
    check("kucuk olan dusuruldu, SIRA korundu", temiz == ["g1.png", "g3.png"], "%r" % temiz)
    check("elenen kaydinda olcu var", len(sonuc["elenen"]) == 1
          and (sonuc["elenen"][0]["en"], sonuc["elenen"][0]["boy"]) == (1000, 88))

    print("F/G/H) KABLOLAMA — ekleme hatti UCTAN UCA kosturulur (DAVRANIS nobetcisi)")
    for betik in ("urun-ekle.py", "printables-ekle.py", "makerworld-ekle.py"):
        _akis_dogrula(betik, d)

    print("-" * 70)
    if FAILS:
        print("SONUC: KIRMIZI ❌  (%d basarisiz: %s)" % (len(FAILS), "; ".join(FAILS)))
        return 1
    print("SONUC: YESIL ✅  — asgari gorsel boyutu kapisi dogru calisiyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
