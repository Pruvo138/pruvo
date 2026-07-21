#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""feed-id-cozucu-test.py — tools/feed-id-cozucu.py KABUL TESTI.

NE KANITLAR:
  A. SENTETIK katalog (deterministik): 50 karakteri ASAN bir urun id'sinin feed g:id'si
     (build.feed_id ile kisaltilmis) GERCEK urun id'sine geri cozulur; kisa id kendine
     cozulur; katalogda olmayan kimlik COZULEMEDI doner (sessizce yanlis urun DONMEZ).
  B. SENTETIK: parametrik urun feed'de YOK (feedde=False), normal urun feed'de VAR.
     ('feedde' alani render_merchant_feed'in GERCEK ciktisindan okunur, tahminden degil.)
  C. GERCEK katalog: id'si >50 karakter olan TUM urunlerin feed g:id'si dogru pid'e cozulur
     ve g:id kumesinde CAKISMA yoktur (iki urun ayni feed kimligine dusmez).
  D. AG'A CIKMAZ: canli=False iken http alani None kalir ve http_kodu() HIC cagrilmaz
     (nobetci: cagrilirsa test patlar). CI'da deterministik olmasi buna bagli.

Salt-okunur; dosyaya yazmaz, ag'a cikmaz. Cikis: 0 = yesil, 1 = kirmizi.
Calistir:  python3 tools/feed-id-cozucu-test.py
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

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


def sentetik():
    """Deterministik mini katalog: 1 uzun-id, 1 kisa-id, 1 parametrik."""
    uzun = "citroen-jumpy-expert-scudo-uyumlu-ekran-tutucu-aparat-uzatma-parcasi"
    kisa = "1967-1968-chrysler-300-far-kapa-di-lisi"
    return uzun, kisa, [
        {"id": uzun, "kategori": "Otomobil", "marka": ["Citroen"],
         "baslik": "Citroen Ekran Tutucu Aparat", "aciklama": "Test aciklamasi.",
         "fiyat": "650 TL", "gorseller": ["https://media.pruvo3d.com/urunler/x-1.jpg"]},
        {"id": kisa, "kategori": "Otomobil", "marka": ["Chrysler"],
         "baslik": "Chrysler far kapagi dislisi", "aciklama": "Test aciklamasi.",
         "fiyat": "850 TL", "gorseller": ["https://media.pruvo3d.com/urunler/y-1.jpg"]},
        {"id": "parametrik-ornek-urun", "kategori": "Jeneratör", "marka": [],
         "baslik": "Parametrik ornek", "aciklama": "Olcuye ozel.", "fiyat": "",
         "parametrik": True, "gorseller": ["https://media.pruvo3d.com/urunler/z-1.jpg"]},
    ]


def main():
    coz_mod = _yukle("feed_id_cozucu", "feed-id-cozucu.py")
    import build

    print("A) SENTETIK katalog — kisaltilmis g:id -> gercek id")
    uzun, kisa, urunler = sentetik()
    uzun_gid = build.feed_id(uzun)
    check("uzun id GERCEKTEN kisaltiliyor (test anlamli)",
          uzun_gid != uzun and len(uzun_gid) == 50,
          "gid=%s (len=%d, pid len=%d)" % (uzun_gid, len(uzun_gid), len(uzun)))
    k = coz_mod.coz([uzun_gid, kisa, "boyle-bir-urun-yok-12345"], urunler, canli=False)
    check("kisaltilmis g:id -> gercek pid", k[0]["id"] == uzun, "%r" % k[0]["id"])
    check("kisaltilmis kimlik isaretlendi", k[0]["kisaltilmis"] is True)
    check("kisa id kendine cozulur", k[1]["id"] == kisa, "%r" % k[1]["id"])
    check("kisa id 'kisaltilmis' DEGIL", k[1]["kisaltilmis"] is False)
    check("bilinmeyen kimlik COZULEMEDI (None) — sessiz yanlis eslesme yok",
          k[2]["id"] is None, "%r" % k[2]["id"])
    check("URL gercek pid ile kurulur (feed kimligiyle DEGIL)",
          k[0]["url"] == build.product_url(uzun), "%s" % k[0]["url"])

    print("B) SENTETIK — feed uyelik bilgisi render ciktisindan okunuyor")
    kb = coz_mod.coz([uzun, "parametrik-ornek-urun"], urunler, canli=False)
    check("normal urun feed'de VAR", kb[0]["feedde"] is True)
    check("parametrik urun feed'de YOK", kb[1]["feedde"] is False)
    check("parametrik bayragi tasiniyor", kb[1]["parametrik"] is True)

    print("C) GERCEK katalog — 50 karakteri asan TUM id'ler geri cozulur")
    with open(build.JSON_PATH, encoding="utf-8") as f:
        gercek = json.load(f)
    uzunlar = [p["id"] for p in gercek if len(p["id"]) > 50]
    gid_sayaci = {}
    for p in gercek:
        gid_sayaci.setdefault(build.feed_id(p["id"]), []).append(p["id"])
    cakisan = {g: v for g, v in gid_sayaci.items() if len(v) > 1}
    check("feed g:id CAKISMASI yok", not cakisan,
          "%d cakisma" % len(cakisan) if cakisan else "%d urun, %d benzersiz g:id"
          % (len(gercek), len(gid_sayaci)))
    h = coz_mod.harita(gercek)
    yanlis = [pid for pid in uzunlar
              if (h.get(build.feed_id(pid)) or {}).get("id") != pid]
    check("uzun id'lerin hepsi dogru pid'e cozulur", not yanlis,
          "uzun id: %d, yanlis: %d" % (len(uzunlar), len(yanlis)))

    print("D) AG NOBETCISI — varsayilan kosumda HIC ag yok")
    cagrildi = []
    orijinal = coz_mod.http_kodu

    def tuzak(*a, **kw):
        cagrildi.append(a)
        raise AssertionError("http_kodu canli=False iken CAGRILDI (ag sizintisi)")

    coz_mod.http_kodu = tuzak
    try:
        kd = coz_mod.coz([kisa], urunler, canli=False)
        check("canli=False -> http_kodu cagrilmadi", not cagrildi)
        check("canli=False -> http alani None (TAHMIN yok)", kd[0]["http"] is None)
    finally:
        coz_mod.http_kodu = orijinal

    print("-" * 70)
    if FAILS:
        print("SONUC: KIRMIZI ❌  (%d basarisiz: %s)" % (len(FAILS), "; ".join(FAILS)))
        return 1
    print("SONUC: YESIL ✅  — feed g:id cozucu dogru calisiyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
