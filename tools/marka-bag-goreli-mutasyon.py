#!/usr/bin/env python3
"""MARKA DUZ-BAG KOK-GORELI KESINTISI — MUTASYON BATARYASI (6 Eyl 2026).

NEYI KORUR
──────────
`marka-sayac-kapisi.py::AGIRLIK` 6 Eyl'de KIRMIZI yandi: `/marka/yamaha/` uretilen HTML'i
218.175 bayt > tavan 213.155. OLCULEN KOK: sayfanin kart kolu `MARKA_KART_N=80` ile TAVANLI
ama duz bag listesi (`.mm-kalan-oge`) TAVANSIZ — yamaha'da 583 oge / 175.718 bayt =
sayfanin %80'i; her katalog partisi onu buyutuyor. Kesinti: bu listedeki href'ler KOK-GORELI
(`/urun/<id>/`) yazilir; oge basina 19 bayt (`https://pruvo3d.com`) duser -> 11.077 bayt,
yamaha 218.175 -> 207.098 (tavanin 6.057 bayt ALTI).

BU BATARYA NEYI OLCER (dort eksen, hepsi AGSIZ + SENTETIK fikstur, ~1 sn):
  BICIM        : duz bag href'leri KOK-GORELI (kesinti FIILEN yapiliyor mu)
  KANONIK      : kart href'leri MUTLAK KALDI (kesinti kanonik adrese TASMADI)
  FAIL_CLOSED  : `_kok_goreli` beklenmeyen kok gorunce girdiyi AYNEN dondurur (bozuk
                 `//host/...` adres URETMEZ)
  OKUYUCU      : `marka-model-test.py` oksuz supurmesi IKI bicimi de sayar (tek yonlu
                 kalsaydi 583 kalem bir anda "oksuz" gorunurdu)

🔴 NEDEN METIN CAPASI DEGIL: eksenler uretilen HTML'den okunur — `mm.uret()` 140 kalemlik
SENTETIK katalogla kosturulur (0,0 sn). Kaynakta "cagri duruyor mu" diye bakan bir capa,
cagriyi koruyup DAVRANISI bozan mutanti yesil gecirirdi
([[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]).

EMNIYET (FILO DERSI, 4 Eyl): mutant CANLI govdede ASLA kosmaz; her mutant IZOLE bir
tempfile.mkdtemp() kopyasinda uygulanir. Bu dosyada GERCEK ev yoluna `rm -rf`/`rmtree`/
`unlink` YOKTUR — silinen tek sey bu betigin KENDI olusturdugu gecici agactir.

KOSUM:  python3 tools/marka-bag-goreli-mutasyon.py
KABUL:  `OLDURULEN=<n>/<n>  KACAN=0  KONTROL=YESIL` + `HUKUM=YESIL` (rc=0).
FAIL-CLOSED: taban yesil degilse rc=3 (OLCULEMEDI).
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
MM = "marka_model_build.py"
MTEST = "marka-model-test.py"

# ── PROB: izole kopyada kosan cocuk surec. Sentetik katalog, AG YOK, urunler.json OKUNMAZ.
PROB_KAYNAK = r'''
import os, sys, json, re, shutil, tempfile
MUT = sys.argv[1]; GERCEK = sys.argv[2]
sys.path.insert(0, os.path.join(MUT, "tools"))
import build
import marka_model_build as mm

sonuc = {}
urunler = [{"id": "fikstur-parca-%03d" % i,
            "baslik": "Yamaha Fikstur Parca %03d" % i,
            "kategori": "Marin", "marka": ["Yamaha"], "fiyat": "100",
            "gorseller": ["https://media.pruvo3d.com/urunler/x.jpg"]} for i in range(140)]
tmp = tempfile.mkdtemp(prefix="bag-goreli-prob-")
try:
    ctx = build.marka_model_ctx()
    ctx["ROOT"] = tmp
    shutil.copy(os.path.join(GERCEK, "index.html"), os.path.join(tmp, "index.html"))
    mm.uret(urunler, ctx)
    h = open(os.path.join(tmp, "marka", "yamaha", "index.html"), encoding="utf-8").read()
    bag = re.findall(r'<li class="mm-kalan-oge" data-kat="[^"]*"><a href="([^"]+)"', h)
    kart = re.findall(r'<a class="card-main" href="([^"]+)"', h)
    SITE = ctx["SITE"]
    sonuc["BICIM"] = bool(bag) and all(u.startswith("/urun/") for u in bag)
    sonuc["KANONIK"] = bool(kart) and all(u.startswith(SITE + "/urun/") for u in kart)
    # FAIL_CLOSED: beklenmeyen kok + zaten goreli girdi AYNEN donmeli
    sonuc["FAIL_CLOSED"] = (
        mm._kok_goreli("https://baska.example/urun/x/", SITE) == "https://baska.example/urun/x/"
        and mm._kok_goreli("/zaten/goreli/", SITE) == "/zaten/goreli/"
        and mm._kok_goreli(SITE + "/urun/x/", SITE) == "/urun/x/")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# OKUYUCU: oksuz supurmesinin deseni IKI bicimi de saymali (kaynak metinden ayiklanir)
mt = open(os.path.join(MUT, "tools", "marka-model-test.py"), encoding="utf-8").read()
m = re.search(r"for pid in re\.findall\(\s*(r'[^']+'|r\"[^\"]+\")", mt)
desen = eval(m.group(1)) if m else None
ornek = ('<a href="https://pruvo3d.com/urun/mutlak-kalem/">x</a>'
         '<li class="mm-kalan-oge" data-kat="Marin"><a href="/urun/goreli-kalem/">y</a></li>')
bulunan = set(re.findall(desen, ornek)) if desen else set()
sonuc["OKUYUCU"] = bulunan == {"mutlak-kalem", "goreli-kalem"}

print("PROB_JSON:" + json.dumps(sonuc))
'''

EKSENLER = ("BICIM", "KANONIK", "FAIL_CLOSED", "OKUYUCU")


def _kopya_kur():
    tmp = tempfile.mkdtemp(prefix="bag-goreli-mutant-")
    hedef = os.path.join(tmp, "tools")
    os.makedirs(hedef)
    for ad in os.listdir(TOOLS):
        kaynak = os.path.join(TOOLS, ad)
        if os.path.isfile(kaynak) and (ad.endswith(".py") or ad.endswith(".js")):
            shutil.copy2(kaynak, os.path.join(hedef, ad))
    # 🔴 KOK DOSYALARI: `model_kanon` ve `build` ITHALAT ANINDA kok dosyalarini okur
    # (index.html -> MARKA_ALIAS/MODEL_ALIAS · secenekler.js · konfigur.js ...). Eksik
    # birakilirsa mutant degil ORTAM coker ve "olduruldu" iddiasi yanlis yerden gelirdi
    # ([[mutant-kopyasi-cokerse-izin-okunur]]).
    # ⚠️ `urunler.json` KOPYALANMAZ (30 MB) ve LINKLENMEZ: prob kendi SENTETIK katalogunu
    # verir; kokte BOS bir dizi durur. Boylece canli katalog bu bataryanin menzilinde DEGIL.
    for ad in os.listdir(REPO):
        kaynak = os.path.join(REPO, ad)
        if os.path.isfile(kaynak) and ad != "urunler.json" and not ad.startswith("."):
            if os.path.getsize(kaynak) <= 3 * 1024 * 1024:
                shutil.copy2(kaynak, os.path.join(tmp, ad))
    with open(os.path.join(tmp, "urunler.json"), "w", encoding="utf-8") as f:
        f.write("[]")
    return tmp


def _yamala(tmp, dosya, eski, yeni):
    yol = os.path.join(tmp, "tools", dosya)
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    if eski not in metin:
        return False
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin.replace(eski, yeni, 1))
    return True


def _olc(tmp):
    """Izole kopyada dort ekseni olcer. Doner: {eksen: bool} ya da None (cokme)."""
    import json                                    # noqa: PLC0415
    betik = os.path.join(tmp, "prob.py")
    with open(betik, "w", encoding="utf-8") as f:
        f.write(PROB_KAYNAK)
    p = subprocess.run([sys.executable, betik, tmp, REPO],
                       capture_output=True, text=True, cwd=tmp)
    for satir in (p.stdout or "").splitlines():
        if satir.startswith("PROB_JSON:"):
            return json.loads(satir[len("PROB_JSON:"):])
    return None


MUTANTLAR = [
    ("M1_kesinti_noop", MM, "BICIM",
     "    if site and url.startswith(site + \"/\"):\n        return url[len(site):]\n    return url",
     "    return url"),
    ("M2_fail_closed_kalkti", MM, "FAIL_CLOSED",
     "    if site and url.startswith(site + \"/\"):\n        return url[len(site):]\n    return url",
     "    return url[len(site):] if site else url"),
    ("M3_bag_mutlaga_geri", MM, "BICIM",
     'esc(_kok_goreli(ctx["product_url"](p.get("id")), ctx["SITE"])),',
     'esc(ctx["product_url"](p.get("id"))),'),
    ("M4_kanonik_de_goreli", MM, "KANONIK",
     '% (esc(kategori), ek_attr, esc(ctx["product_url"](pid)), esc(baslik), esc(cover),',
     '% (esc(kategori), ek_attr, esc(_kok_goreli(ctx["product_url"](pid), ctx["SITE"])),'
     ' esc(baslik), esc(cover),'),
    ("M5_okuyucu_tek_yonlu", MTEST, "OKUYUCU",
     "r'href=\"(?:https://pruvo3d\\.com)?/urun/([^/\"]+)/\"'",
     "r'href=\"https://pruvo3d\\.com/urun/([^/\"]+)/\"'"),
]

KONTROLLER = [
    ("K1_yorum_eklendi", MM,
     "def _kok_goreli(url, site):",
     "def _kok_goreli(url, site):  # kontrol mutanti: davranis AYNI"),
    ("K2_atil_sabit", MM,
     "MARKA_KART_N = 80",
     "MARKA_KART_N = 80\n_KONTROL_ATIL_SABIT = 1  # kimse okumuyor"),
]


def main():
    print("== TABAN (mutasyonsuz IZOLE kopya) ==")
    tmp = _kopya_kur()
    try:
        taban = _olc(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if taban is None:
        print("OLCULEMEDI: prob CALISMADI (izole kopyada cokme).")
        return 3
    for e in EKSENLER:
        print("  %-12s %s" % (e, "✅" if taban.get(e) else "❌"))
    if not all(taban.get(e) for e in EKSENLER):
        print("OLCULEMEDI: taban YESIL degil, mutasyon olculemez.")
        return 3

    print("\n== OLDURUCU MUTANTLAR ==")
    oldurulen, kacan, sapan, capa_yok = 0, [], [], []
    for ad, dosya, hedef, eski, yeni in MUTANTLAR:
        tmp = _kopya_kur()
        try:
            if not _yamala(tmp, dosya, eski, yeni):
                capa_yok.append(ad)
                print("  %-24s CAPA_YOK 🔴 (mutant ULASMADI — capa bayat)" % ad)
                continue
            s = _olc(tmp)
            if s is None:
                # Cokme kirmiziyla KARISMAZ: ayri sinif olarak yazilir.
                sapan.append(ad + "(COKME)")
                print("  %-24s COKME 🔴 (prob calismadi; oldurme iddiasi KURULAMAZ)" % ad)
                continue
            dusen = [e for e in EKSENLER if not s.get(e)]
            if not dusen:
                kacan.append(ad)
                print("  %-24s KACTI 🔴 (hedef=%s, hicbir eksen dusmedi)" % (ad, hedef))
            elif hedef not in dusen:
                sapan.append(ad)
                print("  %-24s SAPAN 🔴 (hedef=%s ama dusen: %s)"
                      % (ad, hedef, ", ".join(dusen)))
            else:
                oldurulen += 1
                print("  %-24s OLDURULDU ✅ hedef=%-11s | dusen: %s"
                      % (ad, hedef, ", ".join(dusen)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n== KONTROL MUTANTLARI (davranis AYNI -> hicbir eksen dusmemeli) ==")
    kirli = []
    for ad, dosya, eski, yeni in KONTROLLER:
        tmp = _kopya_kur()
        try:
            if not _yamala(tmp, dosya, eski, yeni):
                kirli.append(ad + "(CAPA_YOK)")
                print("  %-24s CAPA_YOK 🔴" % ad)
                continue
            s = _olc(tmp)
            dusen = [e for e in EKSENLER if not (s or {}).get(e)]
            if s is None or dusen:
                kirli.append(ad)
                print("  %-24s KIRLI 🔴 (yanlis-pozitif: %s)"
                      % (ad, ", ".join(dusen) or "prob coktu"))
            else:
                print("  %-24s YESIL ✅ (imza AYNI)" % ad)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "-" * 78)
    print("OLDURULEN=%d/%d  KACAN=%d  SAPAN=%d  CAPA_YOK=%d  KONTROL=%s"
          % (oldurulen, len(MUTANTLAR), len(kacan), len(sapan), len(capa_yok),
             "KIRLI" if kirli else "YESIL"))
    hukum = (oldurulen == len(MUTANTLAR) and not kacan and not sapan
             and not capa_yok and not kirli)
    print("HUKUM=%s" % ("YESIL" if hukum else "KIRMIZI"))
    return 0 if hukum else 1


if __name__ == "__main__":
    sys.exit(main())
