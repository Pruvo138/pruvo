#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MALZEME YUZEYI KAPISI — uretilen urun sayfasi malzeme (filament) yuzeyini SESSIZCE
kaybedebilir mi?

    python3 tools/malzeme-yuzey-kapisi.py            # build.py'den SONRA (BLOKLAYICI)
    python3 tools/malzeme-yuzey-kapisi.py --kok DIZIN    # (test) baska bir agacta olc
    python3 tools/malzeme-yuzey-kapisi.py --mutasyon     # mutasyon nobeti (kopya agacta)

════════════════════════════════════════════════════════════════════════════════════
NEDEN VAR (canlida olculdu, 12 Agu 2026)
════════════════════════════════════════════════════════════════════════════════════
  https://pruvo3d.com/urun/volvo-penta-xact-top-mount-tek-kumanda-paneli-tutucusu/
      -> sayfada `fil-cip` (malzeme cipi) sayisi 0
  karsi ornek volkswagen-polo-6r-...  -> 5

Sayfa "calisiyor" gorunuyordu: 200 donuyor, kart var, fiyat var, sepet var. Kaybolan sey
MALZEME SECIMININ TAMAMIYDI — cipler, "TAVSIYEMIZ" rozeti, muhendislik-malzeme WhatsApp
notu ve "Malzeme Rehberi" linki. Hicbir kapi kirmizi yakmiyordu.

KOK NEDEN (olculdu, ORNEKLEME YOK — 25.964 kaydin TAMAMI):
  `tools/build.py` malzeme bolumunu `malzeme=("" if fiziksel else filament_html(...))`
  ile basar ve `fiziksel = (p.get("tur") == "fiziksel")`. Yani HAZIR/STOK ticari malda
  malzeme yuzeyi BILEREK basilmaz (bir boya kutusunu ozel uretiyormus gibi gostermemek
  icin — Okan, 31 Tem). Kusur o daldA DEGIL, o dala DUSMEMESI gereken kayittadir:

  3 kayit AYNI ANDA hem `"tur":"fiziksel"` (hazir ticari mal = malzeme secimi YOK) hem
  `"tavsiyeFilament"` (baski malzemesi TAVSIYESI = ozel uretim beyani) tasiyor. Iki alan
  BIRBIRIYLE CELISIYOR; uretici sessizce `tur`u dinleyip malzeme yuzeyini tumuyle
  dusuruyor. Ucunun de aciklamasinda CLAUDE.md'nin ozel uretim icin zorunlu tuttugu
  "Yaklaşık dış ölçüler: A × B × C mm" satiri var (yani kayitlar gercekte ozel uretim).

🔴 VERIYE DOKUNULMAZ: `urunler.json` MaCiT'in tek-yazarli duzlemidir. Bu kapi veriyi
DUZELTMEZ; celiskiyi SESSIZ olmaktan cikarir ve SAYIYLA bildirir. Onarim = celiskili
kayitlardan `tur` alaninin kaldirilmasi (MaCiT); kapi o an kendiliginden yesillenir.

════════════════════════════════════════════════════════════════════════════════════
OLCULEN IDDIALAR — ORNEKLEME YOK, uretilen TUM urun sayfalari
════════════════════════════════════════════════════════════════════════════════════
  A) OZEL URETIM SAYFASI CIPLI     : `fiziksel_mi(p)` False olan HER urunun sayfasinda
                                     en az 1 `fil-cip` VAR.
  B) HAZIR SAYFASI CIPSIZ (POZITIF): `fiziksel_mi(p)` True olan HER urunun sayfasinda
                                     `fil-cip` YOK. Kapi tek yonlu olamaz — bu kol
                                     olmasaydi "her sayfaya cip bas" mutanti YESIL gecerdi.
  C) CELISKI (SESSIZ SINIF)        : hazir/stok koluna dusen ama kayitta OZEL URETIM
                                     sinyali tasiyan urun -> sayfasi CIPSIZ ve bu SESSIZ.
                                     Hukum: sayi > 0 ise KIRMIZI.

SINIF TANIMI TEK YERDEN: hazir/stok koluna dusme karari `build.fiziksel_mi` ile OLCULUR
(uretecin KENDI fonksiyonu; ikinci kopya yok). Ozel uretim sinyalleri ALAN duzlemindedir
(serbest metin DEGIL — aciklama prozasi bayatlar ve yanlis-pozitif uretir):
    tavsiyeFilament · parametrik · sema · konfigur
Her biri build.py'nin URETIM MODUNU suren bir alandir.

🔴 OZET = HUKUM: insana basilan sayi, hukmu besleyen LISTENIN uzunlugudur (ikinci sayim
noktasi YOK). Bu depoda olculmus hata sinifi: kapi KIRMIZI iken ozeti "sapan 0" yaziyordu
([[kapi-ozeti-hukumden-ayrisir]]).

CIKIS: 0 yesil · 1 kirmizi · 3 OLCULEMEDI (urun/ yok, JSON bozuk). `continue-on-error`
TASIMAZ; sessiz YESIL imkansiz. Offline, stdlib, depoya YAZMAZ.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build  # noqa: E402

# Sayfadaki malzeme cipinin GORUNUR isareti. build.py bu sinifi hem govde bolumunde
# (filament_html) hem panel secicisinde (panel_malzeme_html) hem de konfigur malzeme
# kartlarinda (_konfigur_malzeme_html) basar -> tek desen UC yuzeyi birden olcer.
CIP = re.compile(r'class="fil-cip')

# OZEL URETIM SINYALLERI — kayit "bunu biz uretiyoruz" diyorsa bu alanlardan biri doludur.
# ALAN duzlemi bilincli: serbest metin (aciklama) her urun partisinde degisir ve elle
# tutulan bir desen defterine donerdi ([[envanter-drift-parti-basina]]).
OZEL_URETIM_SINYALLERI = ("tavsiyeFilament", "parametrik", "sema", "konfigur")


def sinyaller(p):
    """Kayittaki DOLU ozel-uretim sinyallerinin adlari (sirali)."""
    return [ad for ad in OZEL_URETIM_SINYALLERI if p.get(ad)]


def urunleri_oku(kok):
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, list):
        raise ValueError("urunler.json dizi degil")
    return d


def olc(kok):
    """Tum urunleri olc. Donus: (rapor sozlugu) ya da None (OLCULEMEDI)."""
    urun_dir = os.path.join(kok, "urun")
    if not os.path.isdir(urun_dir):
        return None
    try:
        urunler = urunleri_oku(kok)
    except Exception as e:                                   # noqa: BLE001
        print("  ⚠️  OLCULEMEDI: urunler.json okunamadi: %s" % e)
        return None

    ozel_cipsiz = []      # A ihlali: ozel uretim sayfasi cipsiz
    hazir_cipli = []      # B ihlali: hazir sayfa cip basmis
    celiskili = []        # C: hazir koluna dusen ama ozel uretim sinyali tasiyan kayit
    sayfasiz = []
    olculen = 0
    ozel_toplam = 0
    hazir_toplam = 0

    for p in urunler:
        pid = p.get("id") or ""
        yol = os.path.join(urun_dir, pid, "index.html")
        if not pid or not os.path.isfile(yol):
            sayfasiz.append(pid)
            continue
        with open(yol, encoding="utf-8") as f:
            n = len(CIP.findall(f.read()))
        olculen += 1
        hazir = build.fiziksel_mi(p)
        if hazir:
            hazir_toplam += 1
            if n > 0:
                hazir_cipli.append(pid)
            imza = sinyaller(p)
            if imza:
                celiskili.append((pid, imza, n))
        else:
            ozel_toplam += 1
            if n == 0:
                ozel_cipsiz.append(pid)

    return {
        "toplam": len(urunler), "olculen": olculen, "sayfasiz": sayfasiz,
        "ozel_toplam": ozel_toplam, "hazir_toplam": hazir_toplam,
        "ozel_cipsiz": ozel_cipsiz, "hazir_cipli": hazir_cipli, "celiskili": celiskili,
    }


def yazdir(r):
    """Raporu bas ve cikis kodunu dondur. HUKUM ve OZET AYNI listelerden turer."""
    print("\nKAPSAM: %d/%d urun sayfasi olculdu (ozel uretim %d · hazir/stok %d)"
          % (r["olculen"], r["toplam"], r["ozel_toplam"], r["hazir_toplam"]))
    if r["sayfasiz"]:
        print("  ⚠️  OLCULEMEDI: %d urunun sayfasi yok (ornek: %s)"
              % (len(r["sayfasiz"]), r["sayfasiz"][:3]))
        return 3

    hata = 0
    print("\n(A) OZEL URETIM SAYFASI MALZEME CIPI TASIYOR")
    if r["ozel_cipsiz"]:
        print("  ❌ %d üründe malzeme çipi yok (ornek: %s)"
              % (len(r["ozel_cipsiz"]), r["ozel_cipsiz"][:5]))
        hata += 1
    else:
        print("  ✅ %d ozel uretim sayfasinin hepsinde cip var" % r["ozel_toplam"])

    print("\n(B) HAZIR/STOK SAYFASI MALZEME CIPI TASIMIYOR (pozitif nobetci)")
    if r["hazir_cipli"]:
        print("  ❌ %d hazir urun sayfasinda cip basilmis (ornek: %s)"
              % (len(r["hazir_cipli"]), r["hazir_cipli"][:5]))
        hata += 1
    else:
        print("  ✅ %d hazir/stok sayfasinin hicbirinde cip yok" % r["hazir_toplam"])

    print("\n(C) CELISKILI KAYIT — hazir/stok koluna dusen ama OZEL URETIM sinyali tasiyan")
    if r["celiskili"]:
        # 🔴 OZET = HUKUM: asagidaki sayi, kirmiziyi doguran LISTENIN uzunlugu.
        print("  ❌ %d üründe malzeme çipi yok — kayit hem hazir/stok (`tur`) hem ozel "
              "uretim sinyali beyan ediyor:" % len(r["celiskili"]))
        for pid, imza, n in r["celiskili"]:
            print("       %s  sinyal=%s  sayfadaki cip=%d" % (pid, ",".join(imza), n))
        print("     ONARIM (VERI — MaCiT duzlemi): bu kayitlardan `tur` alanini kaldir "
              "(ozel uretim fail-closed varsayilandir) ya da celisen sinyali kaldir.")
        hata += 1
    else:
        print("  ✅ celiskili kayit yok (0 urun)")

    # MAKINE OZETI — mutasyon nobetcisi ve dis denetci BUNU okur. Sayilar yukaridaki
    # hukmu doguran LISTELERIN ta kendisinden gelir (ikinci sayim noktasi YOK).
    print("\nOZET A=%d B=%d C=%d OLCULEN=%d/%d"
          % (len(r["ozel_cipsiz"]), len(r["hazir_cipli"]), len(r["celiskili"]),
             r["olculen"], r["toplam"]))
    print("-" * 70)
    if hata:
        print("SONUC: KIRMIZI ❌ — %d eksen dustu" % hata)
        return 1
    print("SONUC: YESIL ✅ — %d urun sayfasinin malzeme yuzeyi kurala uyuyor" % r["olculen"])
    return 0


# ------------------------------------------------------------------ mutasyon nobeti
# 🔴 MUTANT `rc` ILE KABUL EDILMEZ, BEKLENEN IDDIA AILESININ IZIYLE kabul edilir.
# Bu depoda TABAN bugun KIRMIZI (C ekseni, 3 celiskili kayit) — salt `rc` bakan bir
# surucude KONTROL mutanti da "kirmizi" gorunur ve hicbir sey kanitlanmaz
# ([[hukum-yanlis-birimde]]). Bu yuzden hukum TABAN ile MUTANT arasindaki eksen-bazli
# FARKTAN okunur: her mutant hangi ekseni KAC artirmasi gerektigini beyan eder.
# (eksen, delta) — KONTROL mutanti icin bos: hicbir eksen kimildamamali.
MUTANTLAR = [
    ("M1", "uretilen sayfadan malzeme cipleri soruldu (sessiz yuzey kaybi)",
     "sayfa-cip-sil", {"A": 1}),
    ("M2", "hazir kayda ozel uretim sinyali eklendi (celiski sinifi)",
     "veri-celiski-ekle", {"C": 1}),
    ("M3", "hazir sayfaya cip basildi (pozitif nobetci: kapi tek yonlu olamaz)",
     "sayfa-cip-ekle", {"B": 1}),
    ("M4", "KONTROL: sayfada davranis disi metin degisimi", "kontrol-yorum", {}),
]
OZET_RE = re.compile(r"^OZET A=(\d+) B=(\d+) C=(\d+) OLCULEN=(\d+)/(\d+)$", re.M)


def _kopya_agac(kok, tmp):
    """`urunler.json` + `urun/` KOPYALANIR (mutasyon orada yapilir), tools/ sembolik."""
    hedef = os.path.join(tmp, "agac")
    os.makedirs(hedef)
    os.symlink(TOOLS, os.path.join(hedef, "tools"))
    shutil.copy2(os.path.join(kok, "urunler.json"), os.path.join(hedef, "urunler.json"))
    return hedef


def _fikstur_sayfalari(kok, hedef, urunler):
    """Olcum icin GEREKEN sayfalari kopyala (mutasyon fiksturu: her siniftan ornek +
    kalanlar). Kopya agacta TUM sayfalar olmali ki kapi OLCULEMEDI'ye dusmesin."""
    for p in urunler:
        pid = p.get("id") or ""
        kaynak = os.path.join(kok, "urun", pid, "index.html")
        if not os.path.isfile(kaynak):
            return False
        d = os.path.join(hedef, "urun", pid)
        os.makedirs(d, exist_ok=True)
        os.symlink(kaynak, os.path.join(d, "index.html"))
    return True


def _gercek_sayfa(hedef, pid):
    """Sembolik bagi GERCEK kopyayla degistir (mutasyon yalniz kopyaya dokunur)."""
    yol = os.path.join(hedef, "urun", pid, "index.html")
    icerik = open(yol, encoding="utf-8").read()
    os.unlink(yol)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)
    return yol


def _mutantla(hedef, tur, urunler):
    ozel = [p for p in urunler if not build.fiziksel_mi(p)]
    hazir = [p for p in urunler if build.fiziksel_mi(p) and not sinyaller(p)]
    if not ozel or not hazir:
        return None
    if tur == "sayfa-cip-sil":
        yol = _gercek_sayfa(hedef, ozel[0]["id"])
        s = open(yol, encoding="utf-8").read()
        yeni = s.replace('class="fil-cip', 'class="malzeme-kart')
        if yeni == s:
            return None
        open(yol, "w", encoding="utf-8").write(yeni)
        return ozel[0]["id"]
    if tur == "sayfa-cip-ekle":
        yol = _gercek_sayfa(hedef, hazir[0]["id"])
        s = open(yol, encoding="utf-8").read()
        yeni = s.replace("<main>", '<main><button class="fil-cip"></button>', 1)
        if yeni == s:
            return None
        open(yol, "w", encoding="utf-8").write(yeni)
        return hazir[0]["id"]
    if tur == "veri-celiski-ekle":
        yol = os.path.join(hedef, "urunler.json")
        d = json.load(open(yol, encoding="utf-8"))
        for kayit in d:
            if kayit.get("id") == hazir[0]["id"]:
                kayit["tavsiyeFilament"] = ["ASA"]
                break
        else:
            return None
        json.dump(d, open(yol, "w", encoding="utf-8"), ensure_ascii=False)
        return hazir[0]["id"]
    if tur == "kontrol-yorum":
        yol = _gercek_sayfa(hedef, ozel[0]["id"])
        s = open(yol, encoding="utf-8").read()
        yeni = s.replace("<main>", "<main><!-- kontrol mutanti -->", 1)
        if yeni == s:
            return None
        open(yol, "w", encoding="utf-8").write(yeni)
        return ozel[0]["id"]
    return None


def _kosum(kok_yolu):
    """Kapiyi verilen agacta kos; eksen sayaclarini (OZET satirindan) dondur."""
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--kok", kok_yolu],
                       capture_output=True, text=True)
    m = OZET_RE.search(r.stdout)
    if not m:
        return None, r.returncode, r.stdout
    return ({"A": int(m.group(1)), "B": int(m.group(2)), "C": int(m.group(3))},
            r.returncode, r.stdout)


def mutasyon(kok):
    print("\n" + "=" * 70)
    print("MUTASYON NOBETI — kapi OLU mu? (uc oldurucu + bir KONTROL)")
    if not os.path.isdir(os.path.join(kok, "urun")):
        print("OLCULEMEDI: urun/ yok — once `python3 tools/build.py`")
        return 3
    urunler = urunleri_oku(kok)
    taban, taban_rc, _ = _kosum(kok)
    if taban is None:
        print("OLCULEMEDI: TABAN kosumunda OZET satiri yok — surucu capasi bayat.")
        return 3
    print("TABAN (mutasyonsuz): A=%d B=%d C=%d  rc=%d" % (taban["A"], taban["B"],
                                                          taban["C"], taban_rc))
    sapan = []
    print("\n%-4s %-52s %-14s %-14s %s"
          % ("KOD", "MUTANT", "BEKLENEN FARK", "OLCULEN FARK", "SONUC"))
    for kod, aciklama, tur, bek_fark in MUTANTLAR:
        tmp = tempfile.mkdtemp(prefix="malzeme-yuzey-mut-")
        try:
            hedef = _kopya_agac(kok, tmp)
            if not _fikstur_sayfalari(kok, hedef, urunler):
                sapan.append("%s: fikstur sayfalari kurulamadi" % kod)
                continue
            hangi = _mutantla(hedef, tur, urunler)
            if hangi is None:
                sapan.append("%s: mutant uygulanamadi (capa yok / etkisiz)" % kod)
                print("%-4s %-52s %-14s %-14s CAPA YOK" % (kod, aciklama[:52],
                                                           bek_fark, "-"))
                continue
            olculen, rc, cikti = _kosum(hedef)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if olculen is None:
            sapan.append("%s: OZET satiri yok (rc=%d)" % (kod, rc))
            continue
        fark = {k: olculen[k] - taban[k] for k in ("A", "B", "C")
                if olculen[k] != taban[k]}
        tamam = (fark == bek_fark)
        # KONTROL mutantinda ek sart: rc de TABANLA ayni kalmali (kapi kimildamadi).
        if not bek_fark and rc != taban_rc:
            tamam = False
        if not tamam:
            sapan.append("%s: beklenen fark %s · olculen %s (rc=%d)"
                         % (kod, bek_fark or "{} (kimildamamali)", fark, rc))
        print("%-4s %-52s %-14s %-14s %s"
              % (kod, aciklama[:52], bek_fark or "{}", fark or "{}",
                 "OK" if tamam else "SAPTI"))
    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    print("\nOK: %d mutantin hepsi BEKLENEN IDDIA EKSENINDE kimildatti "
          "(KONTROL hicbir ekseni kimildatmadi)." % len(MUTANTLAR))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=ROOT)
    ap.add_argument("--mutasyon", action="store_true")
    a = ap.parse_args()
    if a.mutasyon:
        raise SystemExit(mutasyon(a.kok))

    print("MALZEME YUZEYI KAPISI — uretilen urun sayfasi malzeme yuzeyini kaybetti mi?")
    r = olc(a.kok)
    if r is None:
        print("\nOLCULEMEDI: urun/ yok ya da katalog okunamadi — bu kapi build.py'den "
              "SONRA kosar. (sessiz YESIL yok: rc=3)")
        raise SystemExit(3)
    raise SystemExit(yazdir(r))


if __name__ == "__main__":
    main()
