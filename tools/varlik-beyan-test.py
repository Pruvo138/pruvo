#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VARLIK CIKARIM BEYANI KAPISI — kabul testi (T1-T8).

🔴 16 Agu 2026 — SPEC: varlik-cikarim-beyani.md. Bu kapinin tek kabul testi:
kapinin kendi muafiyet kolu (kullanici beyaniyla KIRMIZI bulguyu yutma) SESSIZ
calisamaz; bos/bozuk/blanket beyan REDDEDILIR, beyan edilemez alanlar her durumda
RED kalir. Mutantlara (T7/T8) gelince: kapinin bug yakalayan testi, bug'in
"kapsam kontrolu kaldirildi" ya da "beyan-edilemez listesi bosaltildi" gibi
bilinen sekillerini algilamak ZORUNDADIR.

KABUL FORMATI: sonda `VAKA=<n> DUSEN=<n>` basar; DUSEN>0 ise rc=1.
"""
import importlib.util
import io
import os
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

# `varlik-test.py` dosya adi dash tasidigi icin dogrudan `import varlik_test` YAPILAMAZ;
# importlib ile modul olarak yuklenir (olculdu: tools/diriltme-kapisi.py'de ayni desen).
_spec = importlib.util.spec_from_file_location(
    "varlik_test", os.path.join(TOOLS, "varlik-test.py"))
varlik_test = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(varlik_test)


# --------------------------------------------------------------------- sabitler
URUN_TEMEL = {
    "id": "u1",
    "kategori": "Test",
    "baslik": "Test urunu",
    "fiyat": "100 TL",
    "gorseller": ["https://media.pruvo3d.com/urunler/u1-1.jpg"],
    "marka": [],
}
# Spec'teki ornek ref — kapida gercek ref dogrulamasi yapilir (T1'de devre disi).
ORNEK_REF = "4380e7c8b4c27d6538cb433e70bad32b685efc96"
BEYAN_TAM = [{
    "ref": ORNEK_REF,
    "tarih": "2026-08-16",
    "gerekce": "rel-card hedefleri ve breadcrumb adresi merge 4380e7c8",
    "kapsam": ["breadcrumb-adresi", "rel-card-hedefleri"],
    "urunler": ["u1"],
}]


# --------------------------------------------------------------------- T1-T6
def t1_beyan_yok():
    """T1: beyan YOK -> kati davranis (hicbir bulgu gecmez)."""
    bulgular = ["<img src> KAYIP: https://media.pruvo3d.com/urunler/u2-1.jpg"]
    g, kd, be, yb = varlik_test.cikarim_beyan_degerlendir(bulgular, URUN_TEMEL, None)
    if kd != bulgular or be or g:
        return False, "T1 beyan YOK -> bulgular kapsam_disi olmali (g=%r kd=%r be=%r)" % (
            g, kd, be)
    # Dogrudan None ile de ayni sonuc (test yardimcilari icin):
    g2, kd2, be2, _ = varlik_test.cikarim_beyan_degerlendir(bulgular, URUN_TEMEL, [])
    if kd2 != bulgular or be2 or g2:
        return False, "T1 beyan [] -> kapsam_disi olmali"
    return True, ""


def t2_beyan_tamamini_kapsiyor():
    """T2: beyan VAR, urun listede, kapsaminda -> GECER, baski yapilir."""
    bulgular = [
        "<img src> KAYIP: https://media.pruvo3d.com/urunler/u2-1.jpg",
        "<a href=/kategori/test/1/> sorgu parametresi KAYIP/DEGISTI: "
        "eski={'kategori': 'Test'} yeni={'kategori': 'Test2'}",
    ]
    g, kd, be, yb = varlik_test.cikarim_beyan_degerlendir(bulgular, URUN_TEMEL, BEYAN_TAM)
    if not g or kd or be or yb:
        return False, "T2 beyan VAR+tum kosullar uyuyor -> GECMELI (g=%r kd=%r be=%r yb=%r)" % (
            g, kd, be, yb)
    return True, ""


def t3_bir_bulgu_kapsam_disi():
    """T3: bulgulardan biri kapsam adayi beyan kapsaminda DEGIL -> REDDEDILIR.

    Beyan yalniz `breadcrumb-adresi` tutuyor; bulgularin biri rel-card-hedefleri
    kapsaminda — o bulgu kapsam_disi olmali. Ayirt edici kontrol: diger bulgu
    gecmeli (TUMUYLE kapsam disi degil)."""
    beyan_sadece_bc = [{
        "ref": ORNEK_REF,
        "tarih": "2026-08-16",
        "gerekce": "x",
        "kapsam": ["breadcrumb-adresi"],  # SADECE breadcrumb
        "urunler": ["u1"],
    }]
    bulgular = [
        # bulgu 1: rel-card-hedefleri -> kapsam_disi
        "<img src> KAYIP: https://media.pruvo3d.com/urunler/u2-1.jpg",
        # bulgu 2: breadcrumb-adresi -> gecer
        "<a href=/kategori/test/1/> sorgu parametresi KAYIP/DEGISTI: "
        "eski={'kategori': 'Test'} yeni={'kategori': 'Test2'}",
    ]
    g, kd, be, yb = varlik_test.cikarim_beyan_degerlendir(
        bulgular, URUN_TEMEL, beyan_sadece_bc)
    if len(g) != 1 or len(kd) != 1 or be:
        return False, "T3 1 gecen + 1 kapsam_disi olmali (g=%r kd=%r be=%r)" % (g, kd, be)
    # Tam olarak hangi bulgunun kapsam_disi oldugunu dogrula (kismi gecis YOK):
    if kd[0] != bulgular[0]:
        return False, "T3 kapsam_disi olan rel-card bulgusu olmali (kd=%r)" % (kd,)
    return True, ""


def t4_blanket_beyan():
    """T4: blanket beyan (`"*"` / `"hepsi"` / bos kapsam) -> REDDEDILIR."""
    bulgular = ["<img src> KAYIP: https://media.pruvo3d.com/urunler/u2-1.jpg"]
    blanket_halleri = (["*"], ["hepsi"], ["tumu"], ["all"], ["Hepsi"], ["ALL"], [])
    for kapsam in blanket_halleri:
        beyan = [{
            "ref": ORNEK_REF,
            "tarih": "2026-08-16",
            "gerekce": "x",
            "kapsam": kapsam,
            "urunler": ["u1"],
        }]
        g, kd, be, yb = varlik_test.cikarim_beyan_degerlendir(bulgular, URUN_TEMEL, beyan)
        if g or be:
            return False, "T4 blanket=%r -> hicbir bulgu gecmemeli (g=%r be=%r)" % (
                kapsam, g, be)
        if kd != bulgular:
            return False, "T4 blanket=%r -> kd dolu olmali (kd=%r)" % (kapsam, kd)
    return True, ""


def t5_beyan_edilemez():
    """T5: beyan edilemez alanlar beyan kapsamini icse bile GECMEZ (5 alt vaka).

    Spec 4'te 5 alt vaka KAPALI:
      1. kendi gorseli      : <img src> KAYIP (urunun gorsellerinden biri)
      2. canonical          : <link rel=canonical> degisti
      3. siparis/WhatsApp   : <a href> icinde wa.me / whatsapp / siparis
      4. baslik (title/h1)  : <title> degisti
      5. fiyat              : JSON-LD offers/price (fiyat beyan alani)
    """
    vakalar = [
        ("kendi gorseli", "<img src> KAYIP: https://media.pruvo3d.com/urunler/u1-1.jpg"),
        ("canonical", "canonical degisti"),
        ("title", "<title> degisti"),
        ("fiyat (JSON-LD offers)",
         "JSON-LD yapragi DEGISTI: /offers/price: '100' -> '200'"),
        ("siparis/WhatsApp",
         "<a href=https://wa.me/905451386526> sorgu parametresi KAYIP/DEGISTI: "
         "eski={'q': 'x'} yeni={'q': 'y'}"),
    ]
    beyan_kapsam_tam = [{
        "ref": ORNEK_REF,
        "tarih": "2026-08-16",
        "gerekce": "x",
        "kapsam": list(varlik_test.BEYAN_KAPSA_KUMESI),
        "urunler": ["u1"],
    }]
    basarisiz = []
    for ad, bulgu in vakalar:
        g, kd, be, yb = varlik_test.cikarim_beyan_degerlendir(
            [bulgu], URUN_TEMEL, beyan_kapsam_tam)
        if g or kd or not be:
            basarisiz.append("%s: g=%r kd=%r be=%r (beyan_edilemez olmali)" % (ad, g, kd, be))
    return (not basarisiz), ("T5: " + "; ".join(basarisiz)) if basarisiz else ""


def t6_bozuk_json():
    """T6: bozuk/eksik JSON -> fail-closed (kati davranis).

    IKI seviye yapisal kontrol:
      · Dosya seviyesi  : `_beyan_yapisi_gecerli_mi`  -> dict + beyanlar dizisi
      · Kayit seviyesi  : `_beyan_kayit_gecerli_mi`   -> her beyan sema kontrolu

    Yanlis tipli beyan verisi (sozluk yerine liste/dize/sayi) ve sema bozuklugu
    (beyanlar alani yok, yanlis tip, ref eksik/yanlis) REDDEDILIR. HICBIR bozuk
    beyan dosyasi kapinin kati davranisini ACAMAZ ([[ikiz-tanim-sessiz-ayrisma]])."""
    basarisiz = []
    bulgu = "<img src> KAYIP: https://media.pruvo3d.com/urunler/u2-1.jpg"

    # --- SEVIYE 1: dosya yapisal kontrolu
    dosya_duzeyi = [
        ([], "JSON dizisi (sozluk degil)"),
        ("string", "JSON dizesi"),
        (123, "JSON sayi"),
        (None, "None"),
        ({"kapsam": []}, "'beyanlar' alani YOK"),
        ({"beyanlar": "yanlis"}, "'beyanlar' dize (dizi degil)"),
        ({"beyanlar": {}}, "'beyanlar' sozluk (dizi degil)"),
    ]
    for veri, ad in dosya_duzeyi:
        if veri is None:
            # _beyan_dosyasi_oku() None doner; kati davranis
            g, kd, be, _ = varlik_test.cikarim_beyan_degerlendir(
                [bulgu], URUN_TEMEL, None)
            if g or be:
                basarisiz.append("[seviye1] %s: bos dosya kati davranisa dusmemeli" % ad)
            continue
        ok, gerekce = varlik_test._beyan_yapisi_gecerli_mi(veri)
        if ok:
            basarisiz.append("[seviye1] %s: yanlis tip gecerli sayildi" % ad)

    # --- SEVIYE 2: kayit sema kontrolu (dosya yapi gecerli, kayit bozuk)
    kayit_duzeyi = [
        ([{"kapsam": ["breadcrumb-adresi"], "urunler": ["u1"]}], "ref alani YOK"),
        ([{"ref": 123, "kapsam": ["breadcrumb-adresi"], "urunler": ["u1"]}], "ref sayi"),
        ([{"ref": "abc", "kapsam": ["breadcrumb-adresi"], "urunler": ["u1"]}], "ref cok kisa"),
        ([{"ref": "0123456789abcdef", "kapsam": ["breadcrumb-adresi"], "urunler": ["u1"]}],
         "ref depoda cozulemiyor"),
        ([{"ref": ORNEK_REF, "kapsam": "yanlis", "urunler": ["u1"]}], "kapsam dizi degil"),
        ([{"ref": ORNEK_REF, "kapsam": [], "urunler": ["u1"]}], "kapsam bos (blanket)"),
        ([{"ref": ORNEK_REF, "kapsam": ["yeni-kapsam"], "urunler": ["u1"]}],
         "kapsam kapali kumede degil"),
        ([{"ref": ORNEK_REF, "kapsam": ["*"], "urunler": ["u1"]}], "kapsam blanket ('*')"),
        ([{"ref": ORNEK_REF, "kapsam": ["breadcrumb-adresi"], "urunler": "yanlis"}],
         "urunler dizi degil"),
    ]
    for beyanlar, ad in kayit_duzeyi:
        ok, gerekce = varlik_test._beyan_kayit_gecerli_mi(beyanlar[0], ref=None)
        if ok:
            basarisiz.append("[seviye2] %s: bozuk kayit gecerli sayildi" % ad)
    return (not basarisiz), ("T6: " + "; ".join(basarisiz)) if basarisiz else ""


# --------------------------------------------------------------------- T7/T8 mutantlar
def _gecici_kok():
    """varlik-test.py'yi gecici agaca kopyala; root dosyalari SYMLINK.

    `varlik_test` modulunu import ederken icindeki yollar `TOOLS` ve `ROOT`'a
    baglidir. Gecici agacta import icin yalnizca `tools/varlik-test.py` gercek
    dosya olmali; `.git` ve diger root ogeleri symlink. Boylece mutasyon
    gercek depoya DOKUNMAZ ([[mutasyon-diske-yazma-tuzagi]])."""
    tmp = tempfile.mkdtemp(prefix="varlik-beyan-test-")
    # tools/: tam kopyala (ger鏴k dosya, cunku uzerinde mutant uygulayacagiz)
    shutil.copytree(os.path.join(ROOT, "tools"), os.path.join(tmp, "tools"))
    # diger root ogeleri: symlink (cikarim_beyan_dosyasi_yolu icin vs.)
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(tmp, ad))
    # .git: ger鏴k symlink (referans_cozulur icin)
    os.symlink(os.path.join(ROOT, ".git"), os.path.join(tmp, ".git"))
    return tmp


def _mutantli_yukle(tmp, eski_capa, yeni_capa):
    """Gecici agacta varlik-test.py uzerinde TEK BIR capa degisikligi yap ve
    modul olarak yukle. Capa TAM OLARAK bir kez gecmeli (birden cok eslesme
    belirsizlik yaratir)."""
    yol = os.path.join(tmp, "tools", "varlik-test.py")
    with io.open(yol, encoding="utf-8") as f:
        s = f.read()
    n = s.count(eski_capa)
    if n != 1:
        raise RuntimeError("capa %d kez gecti (1 bekleniyordu): %r" % (n, eski_capa[:60]))
    s = s.replace(eski_capa, yeni_capa, 1)
    with io.open(yol, "w", encoding="utf-8") as f:
        f.write(s)
    spec = importlib.util.spec_from_file_location(
        "varlik_test_mutated_%d" % id(tmp), yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def t7_mutant_kapsam_yok():
    """T7 MUTANT: kapsam kontrolu kaldirilirsa gate yanlis gecirir -> test bunu YAKALAR.

    Senaryo: T3-equivalent — bulgulardan biri rel-card-hedefleri, beyan SADECE
    breadcrumb-adresi tutuyor. Orijinal gate: rel-card bulgusu kapsam_disi.
    Mutant gate (kapsam kontrolu `if False: pass` ile devre disi): bulgu
    gecer sayilir.

    Test gecme kosulu: orijinal davranis != mutant davranis (yani test, bilinen
    bu bug'i algilayabilir)."""
    bulgular = [
        # rel-card-hedefleri -> beyan kapsaminda degil (sadece breadcrumb var)
        "<img src> KAYIP: https://media.pruvo3d.com/urunler/u2-1.jpg",
    ]
    beyan_sadece_bc = [{
        "ref": ORNEK_REF,
        "tarih": "2026-08-16",
        "gerekce": "x",
        "kapsam": ["breadcrumb-adresi"],
        "urunler": ["u1"],
    }]
    g_orig, kd_orig, be_orig, _ = varlik_test.cikarim_beyan_degerlendir(
        bulgular, URUN_TEMEL, beyan_sadece_bc)
    # Capa: `cikarim_beyan_degerlendir` icindeki kapsam kontrolu. Kaldirilinca
    # her bulgu (beyan_edilemez degilse) gecer.
    capa_eski = ('if kapsam_adayi not in set(kayit["kapsam"]):\n'
                 '                continue')
    capa_yeni = 'if False:\n                pass  # T7 MUTANT: kapsam kontrolu kaldirildi'
    tmp = _gecici_kok()
    try:
        try:
            mut = _mutantli_yukle(tmp, capa_eski, capa_yeni)
        except RuntimeError as e:
            return False, "T7 capa uygulanamadi: %s" % e
        g_m, kd_m, be_m, _ = mut.cikarim_beyan_degerlendir(
            bulgular, URUN_TEMEL, beyan_sadece_bc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # Orijinal: rel-card bulgusu kapsam_disi (RED). Mutant: gecer (GREEN).
    # Test PASSES = orijinal RED + mutant GREEN (yani bug algilanabilir).
    orig_kirmizi = bool(kd_orig)
    mutant_kirmizi = bool(kd_m)
    if orig_kirmizi and not mutant_kirmizi:
        return True, ""
    return False, ("T7 mutant davranisi beklenen sekilde degil: "
                   "orig_kirmizi=%s mutant_kirmizi=%s (kapsam kontrolu KALDIRILDI "
                   "isleyisi kontrol edilemedi)" % (orig_kirmizi, mutant_kirmizi))


def t8_mutant_beyan_edilemez_yok():
    """T8 MUTANT: beyan-edilemez listesi bosaltilirsa gate yanlis gecirir -> test bunu YAKALAR.

    Senaryo: T5-equivalent — bulgu `<title> degisti` (beyan_edilemez). Orijinal
    gate: bulgu beyan_edilemez olarak REDDEDILIR. Mutant gate (beyan_edilemez
    kontrolu `if False: pass` ile devre disi): bulgu gecer sayilir.

    Test gecme kosulu: orijinal davranis != mutant davranis."""
    bulgular = ["<title> degisti"]
    g_orig, kd_orig, be_orig, _ = varlik_test.cikarim_beyan_degerlendir(
        bulgular, URUN_TEMEL, BEYAN_TAM)
    # Capa: `cikarim_beyan_degerlendir` icindeki beyan-edilemez kontrolu.
    capa_eski = ('if edilemez:\n'
                 '            beyan_edilemez.append((bulgu, sebep))\n'
                 '            continue')
    capa_yeni = 'if False:\n            pass  # T8 MUTANT: beyan-edilemez listesi bosaltildi'
    tmp = _gecici_kok()
    try:
        try:
            mut = _mutantli_yukle(tmp, capa_eski, capa_yeni)
        except RuntimeError as e:
            return False, "T8 capa uygulanamadi: %s" % e
        g_m, kd_m, be_m, _ = mut.cikarim_beyan_degerlendir(
            bulgular, URUN_TEMEL, BEYAN_TAM)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # Orijinal: beyan_edilemez dolu (RED). Mutant: beyan_edilemez bos (GREEN).
    orig_kirmizi = bool(be_orig)
    mutant_kirmizi = bool(be_m)
    if orig_kirmizi and not mutant_kirmizi:
        return True, ""
    return False, ("T8 mutant davranisi beklenen sekilde degil: "
                   "orig_kirmizi=%s mutant_kirmizi=%s (beyan-edilemez KONTROLU "
                   "KALDIRILDI isleyisi kontrol edilemedi)" % (orig_kirmizi, mutant_kirmizi))


# --------------------------------------------------------------------- calistirici
SENARYOLAR = [
    ("T1 beyan YOK -> tazeleme reddedilir (kati davranis)", t1_beyan_yok),
    ("T2 beyan bulgularin tamamini kapsiyor -> tazeleme gecer", t2_beyan_tamamini_kapsiyor),
    ("T3 bulgulardan biri kapsam disi -> REDDEDILIR (kismi gecis YOK)", t3_bir_bulgu_kapsam_disi),
    ("T4 blanket beyan (`\"*\"` / `\"hepsi\"` / bos kapsam) -> REDDEDILIR", t4_blanket_beyan),
    ("T5 beyan edilemez alan beyan kapsamini icse bile GECMEZ", t5_beyan_edilemez),
    ("T6 bozuk/eksik JSON -> fail-closed (tazeleme reddedilir)", t6_bozuk_json),
    ("T7 MUTANT kapsam kontrolu kaldirilirsa KIRMIZI yakar", t7_mutant_kapsam_yok),
    ("T8 MUTANT beyan-edilemez listesi bosaltilirsa KIRMIZI yakar", t8_mutant_beyan_edilemez_yok),
]


def main():
    vaka = 0
    dusen = 0
    for ad, fn in SENARYOLAR:
        vaka += 1
        try:
            ok, hata = fn()
        except Exception as e:
            ok = False
            hata = "EXCEPTION: %s (%s)" % (type(e).__name__, e)
        durum = "OK  " if ok else "HATA"
        print("%s  %s" % (durum, ad))
        if not ok:
            dusen += 1
            print("         -> %s" % hata)
    print()
    print("VAKA=%d DUSEN=%d" % (vaka, dusen))
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())