#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SARI SERİ KONFİGÜRATÖR — 8 KABUL TESTİ (tools/paket-sari-konfigurator.md).

Kullanım: python3 jenerator/test/kabul.py [--hizli]
  --hizli: #1'de rastgele set sayısını düşürür (3 -> 1) ve site build'ini
           mevcut urun/ çıktısı varsa atlar (geliştirme turu için).
Çıkış kodu 0 = 8/8 YEŞİL.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
JEN_DIR = os.path.dirname(TEST_DIR)
ROOT = os.path.dirname(JEN_DIR)
SONUC = []

# Yasaklı ifadeler parçalı kurulur ki bu dosya kendi taramasına takılmasın.
YASAK_GIZLI = "ko" + "olm"
YASAK_BASKI = re.compile(r"3\s*[dD]\s*[-\s]?bask|3\s*boyutlu\s+bask", re.I)
YASAK_RENK = re.compile(r"her\s+renk", re.I)

# TEST 7'nin gecici ornek urunu (finally'de silinir) katalog urunu degil —
# TEST 8 kapsam kumesinden haric tutulur ki yarim kalan kosu yanlis kirmizi yakmasin.
SEMA_FIXTURE = {"ornek-plaka"}


def kayit(no, ad, yesil, detay=""):
    SONUC.append((no, ad, yesil))
    print("[%s] TEST %d — %s%s" % ("YESIL" if yesil else "KIRMIZI", no, ad,
                                   ("\n" + detay) if detay else ""))


def kos(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def fold(s):
    return (s or "").lower().translate(str.maketrans("çğıöşüâî", "cgiosuai"))


def parametrik_urunler():
    with io.open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        d = json.load(f)
    urunler = d["urunler"] if isinstance(d, dict) and "urunler" in d else d
    return [u for u in urunler if u.get("parametrik")]


def hacim_fonksiyonlari():
    p = kos(["node", "-p",
             'Object.keys(require("%s")).join(",")' %
             os.path.join(JEN_DIR, "hacim.js")])
    return set(p.stdout.strip().split(",")) if p.returncode == 0 else set()


def dosya_tara(kokler, desenler, atla=()):
    """Verilen kok dosya/dizinlerde desen arar; eslesen (dosya, desen_adi) listesi."""
    bulunan = []
    for kok in kokler:
        if not os.path.exists(kok):
            continue
        yollar = []
        if os.path.isfile(kok):
            yollar = [kok]
        else:
            for dizin, _, dosyalar in os.walk(kok):
                yollar += [os.path.join(dizin, x) for x in dosyalar]
        for yol in yollar:
            if os.path.abspath(yol) in atla or yol.endswith((".stl", ".png", ".jpg")):
                continue
            try:
                with io.open(yol, "r", encoding="utf-8", errors="ignore") as f:
                    icerik = f.read()
            except (IOError, OSError):
                continue
            for ad, desen in desenler:
                if (desen.search(icerik) if hasattr(desen, "search")
                        else desen in icerik.lower()):
                    bulunan.append((os.path.relpath(yol, ROOT), ad))
    return bulunan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hizli", action="store_true")
    args = ap.parse_args()

    urunler = parametrik_urunler()

    # ---------- TEST 1: hacim doğruluğu (hacim.js vs OpenSCAD render, <=%3) ----------
    set_sayisi = "1" if args.hizli else "3"
    p = subprocess.run([sys.executable, os.path.join(TEST_DIR, "dogrula.py"),
                        "--hepsi", "--set", set_sayisi], text=True)
    kayit(1, "hacim dogrulugu (>=%s rastgele set + varsayilan, <=%%3)" % set_sayisi,
          p.returncode == 0)

    # ---------- site build (3b/5/6 icin gerekli) ----------
    urun_dir = os.path.join(ROOT, "urun")
    if not (args.hizli and os.path.isdir(urun_dir)):
        b = kos([sys.executable, os.path.join(ROOT, "tools", "build.py")], cwd=ROOT)
        if b.returncode != 0:
            print(b.stdout[-2000:], b.stderr[-2000:])
            sys.exit("build.py basarisiz — kabul testleri kosulamaz")

    # ---------- TEST 2: fiyat orantısı (kuruş korunur) + TEST 3a: sınır doğrulama ----------
    p = kos(["node", os.path.join(TEST_DIR, "fiyat-test.js")])
    print(p.stdout.rstrip())
    kayit(2, "fiyat orantisi (198,72 birebir; kurus korunur, yuvarlama yok)",
          p.returncode == 0)

    # ---------- TEST 3b: sayfa kablolaması (geçersiz giriş kilitler + alan kızarır) ----------
    eksik = []
    for u in urunler:
        sayfa = os.path.join(urun_dir, u["id"], "index.html")
        if not os.path.exists(sayfa):
            eksik.append(u["id"] + ": sayfa yok"); continue
        with io.open(sayfa, encoding="utf-8") as f:
            h = f.read()
        if os.path.exists(os.path.join(JEN_DIR, "urunler", u["id"] + ".json")):
            for gerek in ("konfAlanlar", "PRUVO_KONF.gecerliMi", ".hatali",
                          "/jenerator/hacim.js", "/jenerator/konfigurator.js"):
                if gerek not in h:
                    eksik.append(u["id"] + ": " + gerek + " eksik")
    kayit(3, "sinir dogrulama (saf cekirdek #2'de; sayfa kilit/kizarma kablolamasi)",
          p.returncode == 0 and not eksik, "\n".join(eksik))

    # ---------- TEST 4: tek kaynak hacim.js ----------
    hacim_yolu = os.path.join(JEN_DIR, "hacim.js")
    with io.open(hacim_yolu, "rb") as f:
        onceki = f.read()
    kos([sys.executable, os.path.join(TEST_DIR, "birlestir.py")])
    with io.open(hacim_yolu, "rb") as f:
        sonraki = f.read()
    deterministik = onceki == sonraki
    with tempfile.TemporaryDirectory() as tmp:  # deploy kopyasi simulasyonu
        shutil.copy(hacim_yolu, os.path.join(tmp, "hacim.js"))
        with io.open(os.path.join(tmp, "hacim.js"), "rb") as f:
            ayni = f.read() == sonraki
    with io.open(os.path.join(ROOT, ".github", "workflows", "deploy.yml"),
                 encoding="utf-8") as f:
        deploy = f.read()
    beyaz = "jenerator/hacim.js" in deploy
    kopya = dosya_tara(
        [os.path.join(ROOT, "secenekler.js"), os.path.join(ROOT, "index.html"),
         urun_dir, os.path.join(ROOT, "tools")],
        [("hacim fn kopyasi", re.compile(r"function\s+(oring|huni|disli)\s*\("))])
    kayit(4, "tek kaynak: hacim.js deterministik + deploy kopyasi bayt-ozdes + kopya yok",
          deterministik and ayni and beyaz and not kopya,
          "" if not kopya else str(kopya))

    # ---------- TEST 5: gizlilik ----------
    bulunan = dosya_tara(
        [JEN_DIR, urun_dir, os.path.join(ROOT, "index.html"),
         os.path.join(ROOT, "secenekler.js")],
        [("gizli-marka", YASAK_GIZLI)],
        atla={os.path.abspath(__file__)})
    kayit(5, "gizlilik: public dosyalarda '%s' yok" % ("k*" + "olm"),
          not bulunan, "\n".join("%s -> %s" % b for b in bulunan))

    # ---------- TEST 6: sarı seri kuralları ----------
    bulunan = dosya_tara(
        [JEN_DIR, urun_dir, os.path.join(ROOT, "index.html"),
         os.path.join(ROOT, "secenekler.js")],
        [("3D-baski-ifadesi", YASAK_BASKI), ("her-renk", YASAK_RENK)],
        atla={os.path.abspath(__file__)})
    duzen = []
    for u in urunler:
        sema_yolu = os.path.join(JEN_DIR, "urunler", u["id"] + ".json")
        sayfa = os.path.join(urun_dir, u["id"], "index.html")
        if not (os.path.exists(sema_yolu) and os.path.exists(sayfa)):
            continue
        with io.open(sema_yolu, encoding="utf-8") as f:
            sema = json.load(f)
        with io.open(sayfa, encoding="utf-8") as f:
            h = f.read()
        if "ozel-badge" not in h:
            duzen.append(u["id"] + ": rozet yok")
        if sema.get("tabanFiyatTL") is None:
            # fiyatsiz duzen: konfigurator fiyati "—" baslar, sabit fiyat basilmaz
            if 'id="opsiyonFiyat">&mdash;<' not in h and 'id="opsiyonFiyat">—<' not in h:
                duzen.append(u["id"] + ": fiyat '—' degil")
    kayit(6, "sari seri kurallari: yasak ifade yok + rozet/fiyatsiz duzen korunuyor",
          not bulunan and not duzen,
          "\n".join(["%s -> %s" % b for b in bulunan] + duzen))

    # ---------- TEST 7: KURULUM.md canlı testi (örnek ürün uçtan uca + temizlik) ----------
    with io.open(hacim_yolu, "rb") as f:
        hacim_oncesi = f.read()
    ornek_dosyalar = [
        os.path.join(JEN_DIR, "urunler", "ornek-plaka.json"),
        os.path.join(TEST_DIR, "aileler", "ornekplaka.js"),
        os.path.join(TEST_DIR, "esleme", "ornekplaka.json")]
    yesil7 = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with io.open(os.path.join(tmp, "ornek-plaka.scad"), "w",
                         encoding="utf-8") as f:
                f.write("En = 60;\nBoy = 100;\nKalinlik = 3;\ncube([En, Boy, Kalinlik]);\n")
            with io.open(ornek_dosyalar[0], "w", encoding="utf-8") as f:
                json.dump({"id": "ornek-plaka", "hacimFormulu": "ornekplaka",
                           "parametreler": [
                               {"ad": "en", "etiket": "En", "birim": "mm", "tip": "sayi",
                                "min": 20, "max": 200, "adim": 1, "varsayilan": 60,
                                "aciklama": "Kisa kenar"},
                               {"ad": "boy", "etiket": "Boy", "birim": "mm", "tip": "sayi",
                                "min": 20, "max": 300, "adim": 1, "varsayilan": 100,
                                "aciklama": "Uzun kenar"},
                               {"ad": "kalinlik", "etiket": "Kalinlik", "birim": "mm",
                                "tip": "sayi", "min": 1, "max": 10, "adim": 0.5,
                                "varsayilan": 3, "aciklama": "Kalinlik"}],
                           "tabanHacimMm3": 18000, "tabanFiyatTL": None}, f)
            with io.open(ornek_dosyalar[1], "w", encoding="utf-8") as f:
                f.write("function ornekplaka(p) {\n  return p.en * p.boy * p.kalinlik;\n}\n")
            with io.open(ornek_dosyalar[2], "w", encoding="utf-8") as f:
                json.dump({"urunId": "ornek-plaka", "scad": "ornek-plaka.scad",
                           "fonksiyon": "ornekplaka",
                           "esleme": {"en": "En", "boy": "Boy", "kalinlik": "Kalinlik"},
                           "sabit": {}}, f)
            ortam = dict(os.environ, PRUVO_SCAD_DIR=tmp)
            p = kos([sys.executable, os.path.join(TEST_DIR, "dogrula.py"),
                     "ornekplaka", "--set", "3", "--seed", "7"], env=ortam)
            print(p.stdout.rstrip())
            yesil7 = p.returncode == 0
    finally:
        for yol in ornek_dosyalar:
            if os.path.exists(yol):
                os.remove(yol)
        kos([sys.executable, os.path.join(TEST_DIR, "birlestir.py")])
    with io.open(hacim_yolu, "rb") as f:
        geri_geldi = f.read() == hacim_oncesi
    kayit(7, "KURULUM.md canli test (ornek urun ucta uca + temizlik izsiz)",
          yesil7 and geri_geldi)

    # ---------- TEST 8: kapsam (küme farkı) + açıklama tutarlılığı ----------
    # Kapsam = "şema tanımlı her parametrik ürün test ediliyor mu?" — SAYI DEĞİL KÜME.
    # Sabit sayı (eski hâli: len(urunler) == 18) katalog büyüyünce kapıyı sürekli
    # kırmızıya çakar; sürekli kırmızı nöbetçi = körelmiş nöbetçi.
    fonksiyonlar = hacim_fonksiyonlari()
    sema_dizin = os.path.join(JEN_DIR, "urunler")
    sema_tanimli = set(
        d[:-5] for d in os.listdir(sema_dizin) if d.endswith(".json")
    ) - SEMA_FIXTURE
    test_edilen = set(u["id"] for u in urunler)
    eksikler = ["KAPSAM DISI (sema var, test edilmiyor): " + uid
                for uid in sorted(sema_tanimli - test_edilen)]
    for u in urunler:
        uid = u["id"]
        sema_yolu = os.path.join(JEN_DIR, "urunler", uid + ".json")
        if not os.path.exists(sema_yolu):
            eksikler.append(uid + ": SEMA YOK"); continue
        with io.open(sema_yolu, encoding="utf-8") as f:
            sema = json.load(f)
        if sema.get("id") != uid:
            eksikler.append(uid + ": sema id uyusmuyor")
        if sema.get("hacimFormulu") not in fonksiyonlar:
            eksikler.append(uid + ": hacim fonksiyonu yok (%s)" % sema.get("hacimFormulu"))
        if not isinstance(sema.get("tabanHacimMm3"), (int, float)):
            eksikler.append(uid + ": tabanHacimMm3 sayisal degil")
        if not (sema.get("tabanFiyatTL") is None or
                isinstance(sema.get("tabanFiyatTL"), (int, float))):
            eksikler.append(uid + ": tabanFiyatTL null/sayi degil")
        aciklama = fold(u.get("aciklama"))
        eslesen = 0
        for prm in sema.get("parametreler", []):
            tip = prm.get("tip", "sayi")
            if tip == "sayi":
                for alan in ("ad", "min", "max", "adim", "varsayilan", "birim"):
                    if prm.get(alan) in (None, ""):
                        eksikler.append("%s.%s: '%s' alani eksik" %
                                        (uid, prm.get("ad"), alan))
            govde = fold(prm.get("etiket", "")) + " " + fold(prm.get("aciklama", ""))
            if any(k and k in aciklama for k in re.split(r"[^a-z0-9]+", govde) if len(k) >= 4):
                eslesen += 1
        if not sema.get("parametreler"):
            eksikler.append(uid + ": parametre listesi bos")
        elif eslesen == 0:
            eksikler.append(uid + ": hicbir parametre 'Neyi ayarliyoruz?' metniyle eslesmiyor")
    kayit(8, "kapsam %d/%d + sema-aciklama tutarliligi" %
          (len(sema_tanimli & test_edilen), len(sema_tanimli | test_edilen)),
          not eksikler, "\n".join(eksikler))

    # ---------- özet ----------
    kirmizi = [s for s in SONUC if not s[2]]
    print("\n==== KABUL OZETI: %d/8 YESIL ====" % (8 - len(kirmizi)))
    for no, ad, yesil in SONUC:
        print("  %s  #%d %s" % ("+" if yesil else "-", no, ad))
    sys.exit(1 if kirmizi else 0)


if __name__ == "__main__":
    main()
