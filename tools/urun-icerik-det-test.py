#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — urun ekleme ICERIK ADIMI TEK BACAKLI OLMASIN (K398 turu, 9 Eyl 2026).

OLCULEN KUSUR (bu testin var olma sebebi):
  `tools/urun-ekle.py` + `printables-ekle.py` + `makerworld-ekle.py` icerik adimini
  emekli motora TEK BACAKLA baglamisti:
      rc != 0        -> "HATA: kredi kapisi — urun AI izni yok"   -> URUN DUSER
      oneri.json yok -> "HATA: emekli motor oneri yok"            -> URUN DUSER
  Emekli motor 400 dondugu gun (`gpt-5.4-mini` ChatGPT hesabinda desteklenmiyor) uc
  platformun hatti da 0/N STAGE verdi. Deterministik yedek YOKTU.

BU TEST NEYI KANITLAR (uc iddia + kaynak envanteri):
  (a) AI IZNI KAPALIYKEN icerik adimi urun DUSURMEZ ve DETERMINISTIK icerik uretir.
  (b) AI IZNI ACIK ama motor hata dondurdugunde (rc=0 + hata govdesi fiksturu) adim
      BASARISIZ sayilir ve deterministik yola DUSER — urun yine DUSMEZ.
  (c) Uretilen icerik alan sozlesmesini ve `denetim-kapisi.py` kapilarini GECER.
  (d) UC ekle betiginin UCU DE ortak adimi cagirir ve hicbirinde eski TEK BACAKLI
      dusuru KALMAMISTIR ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).

AG YOK, MODEL CAGRISI YOK, `urunler.json`'a YAZMA YOK. Butun AI bacaklari sahtelenir.

MUTASYON BATARYASI (--mutasyon; kontroller=True iken CI'da BLOKLAYICI kosar):
  Her mutant IZOLE bir golge agacta calisir (tools/ symlink kopyasi); canli gövde
  sha256 ONCE == SONRA olarak KANITLANIR ([[mutant-canli-govdede-yasamaz]]).
  Her mutantin HEDEF KOL ATFI yazilidir: "bu satiri silsem hangi iddia kirmizi yanar".

Calistir:  python3 tools/urun-icerik-det-test.py            (cikis 0 = gecti)
           python3 tools/urun-icerik-det-test.py --mutasyon (batarya)

# CI-ALT-KUME: --mutasyon
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
FAILS = []

# Deterministik + hizli olsun diye SABIT marka sozlugu: canli `urunler.json` (36k kayit)
# okunmaz. Sozlugun KENDI turetimi ayri bir eksendir, burada olculmez.
MARKA_FIKSTUR = {"renault": "Renault", "clio": "Clio", "bosch": "Bosch"}
KATEGORI_FIKSTUR = ["Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat", "Ev",
                    "Ofis", "Elektronik", "Kamera", "Bahçe", "Dekorasyon", "Oyun/Hobi"]


def _load(yol, modad):
    spec = importlib.util.spec_from_file_location(modad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _chk(ad, kosul, detay=""):
    if kosul:
        print("  ok  " + ad)
    else:
        print("  KALDI  " + ad + ("  -> " + detay if detay else ""))
        FAILS.append(ad)


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _fikstur_dizin(galeri=("g1.jpg", "g2.jpg", "g3.jpg", "g4.jpg", "g5.jpg")):
    d = tempfile.mkdtemp(prefix="uicd-fikstur-")
    for f in galeri:
        open(os.path.join(d, f), "wb").close()
    return d, list(galeri)


META = {"id": "th777", "baslik": "Renault Clio dashboard cup holder insert",
        "tasarimci": "someone", "lisans": "Creative Commons - Attribution",
        "olcu_mm": [120, 80, 45], "stl_adet": 1, "baski": ""}


# =============================================================================
# IDDIA (a) — AI IZNI KAPALI: urun DUSMEZ, deterministik icerik uretilir
# =============================================================================
def iddia_a(uicd):
    d, galeri = _fikstur_dizin()
    try:
        os.environ.pop("PRUVO_URUN_AI_IZNI", None)
        cagrildi = {"n": 0}

        def ai(anahtar):
            cagrildi["n"] += 1
            return True

        o, kaynak, notu = uicd.icerik_sagla("th777", d, META, galeri,
                                            kategoriler=KATEGORI_FIKSTUR, ai_cagir=ai,
                                            urunler_yolu=os.devnull)
        _chk("(a) izin KAPALI -> urun DUSMEZ (oneri uretildi)", o is not None, notu)
        _chk("(a) izin KAPALI -> AI bacagi HIC cagrilmadi", cagrildi["n"] == 0,
             "cagri sayisi=%d" % cagrildi["n"])
        _chk("(a) kaynak damgasi 'deterministik'", kaynak == uicd.KAYNAK_DET, str(kaynak))
        _chk("(a) oneri.json diske YAZILDI",
             os.path.exists(os.path.join(d, "oneri.json")))
        return o
    finally:
        shutil.rmtree(d, ignore_errors=True)


# =============================================================================
# IDDIA (b) — AI IZNI ACIK ama motor HATA: adim basarisiz sayilir, urun DUSMEZ
# =============================================================================
# rc=0 + hata govdesi FIKSTURU: gercek CLI bu makinede rc=1 donuyor (9 Eyl olcumu),
# ama rc TEK BASINA yargic olamaz. Bu fikstur tam olarak "rc yalan soyluyor" halini
# kurar ve icerik kolunun tuttugunu olcer.
class _SahteKosum(object):
    def __init__(self, rc, stdout, stderr):
        self.returncode, self.stdout, self.stderr = rc, stdout, stderr


HATA_GOVDESI = ('ERROR: {"type":"error","status":400,"error":{"type":'
                '"invalid_request_error","message":"model not supported"}}')


def iddia_b(uicd, tc):
    # b1: thing-icerik.py'nin ICERIK KOLU — rc=0 + hata govdesi -> BASARISIZ
    _chk("(b1) hata_govdesi() rc'ye BAKMADAN hata govdesini gorur",
         tc.hata_govdesi("", HATA_GOVDESI) is not None)
    _chk("(b1) temiz ciktida hata govdesi GORMEZ (yanlis-pozitif yok)",
         tc.hata_govdesi("hepsi yolunda", "") is None)

    tmp = tempfile.mkdtemp(prefix="uicd-k398-")
    try:
        cikti = os.path.join(tmp, "oneri.json")
        gercek_run = tc.subprocess.run

        def sahte_run(cmd, **kw):
            # Motor "basarili" bir rc doner AMA hata govdesi basar ve (senaryo geregi)
            # cikti dosyasi da yazilmis olur -> eski iki kol (rc + varlik) YANILIR.
            with open(cikti, "w", encoding="utf-8") as f:
                json.dump({"baslik": "sahte"}, f)
            return _SahteKosum(0, "", HATA_GOVDESI)

        tc.subprocess.run = sahte_run
        try:
            ok, hata = tc.emekli_motor_cagir("p", [], cikti)
        finally:
            tc.subprocess.run = gercek_run
        _chk("(b1) rc=0 + hata govdesi -> emekli_motor_cagir BASARISIZ", ok is False,
             "ok=%r" % ok)
        _chk("(b1) hata metni API govdesini ADIYLA tasir",
             "invalid_request_error" in (hata or ""), repr(hata)[:120])
        _chk("(b1) hata govdesi varken YAZILMIS cikti SILINIR (bayat kanit birakma)",
             not os.path.exists(cikti))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # b2: ORKESTRASYON — izin ACIK, AI bacagi DUSUYOR -> urun DUSMEZ
    d, galeri = _fikstur_dizin()
    try:
        os.environ["PRUVO_URUN_AI_IZNI"] = "EVET"
        cagrildi = {"n": 0}

        def ai_dusen(anahtar):
            cagrildi["n"] += 1
            return False                      # motor 400 dondu

        o, kaynak, notu = uicd.icerik_sagla("th777", d, META, galeri,
                                            kategoriler=KATEGORI_FIKSTUR,
                                            ai_cagir=ai_dusen, urunler_yolu=os.devnull)
        _chk("(b2) izin ACIK -> AI bacagi DENENDI", cagrildi["n"] == 1)
        _chk("(b2) AI DUSTU -> urun DUSMEZ (deterministik yola dusuldu)",
             o is not None and kaynak == uicd.KAYNAK_DET, "%r / %s" % (o is None, kaynak))
    finally:
        os.environ.pop("PRUVO_URUN_AI_IZNI", None)
        shutil.rmtree(d, ignore_errors=True)

    # b3: BAYAT DOSYA KAPISI — onceki kosumdan kalan oneri.json, DUSEN bir cagriyi
    #     "basarili" gostermemeli. Dosya cagridan ONCE silinmeli.
    d, galeri = _fikstur_dizin()
    try:
        os.environ["PRUVO_URUN_AI_IZNI"] = "EVET"
        onerip = os.path.join(d, "oneri.json")
        with open(onerip, "w", encoding="utf-8") as f:
            json.dump({"baslik": "BAYAT — onceki kosumdan", "kategori": "Ev"}, f)

        def ai_dokunmaz(anahtar):
            return True                        # rc temiz ama HICBIR SEY yazmadi

        o, kaynak, _n = uicd.icerik_sagla("th777", d, META, galeri,
                                          kategoriler=KATEGORI_FIKSTUR,
                                          ai_cagir=ai_dokunmaz, urunler_yolu=os.devnull)
        _chk("(b3) BAYAT oneri.json AI kaniti sayilmaz (deterministik yol kazandi)",
             kaynak == uicd.KAYNAK_DET, "kaynak=%s" % kaynak)
        _chk("(b3) bayat baslik SIZMADI",
             (o or {}).get("baslik") != "BAYAT — onceki kosumdan",
             repr((o or {}).get("baslik")))
    finally:
        os.environ.pop("PRUVO_URUN_AI_IZNI", None)
        shutil.rmtree(d, ignore_errors=True)


# =============================================================================
# IDDIA (c) — SOZLESME + denetim-kapisi kapilari
# =============================================================================
SOZLESME_ALANLARI = ("sec_gorseller", "elenen", "baslik", "aciklama", "kategori",
                     "marka", "fiyat_oneri", "not")


def iddia_c(uicd, o):
    for alan in SOZLESME_ALANLARI:
        _chk("(c) sozlesme alani var: " + alan, alan in o)
    _chk("(c) kategori KANONIK listeden", o.get("kategori") in KATEGORI_FIKSTUR,
         repr(o.get("kategori")))
    _chk("(c) galeri kapsami TAM (secili ∪ elenen == galeri)",
         set(o["sec_gorseller"]) | {e["dosya"] for e in o["elenen"]} ==
         {"g1.jpg", "g2.jpg", "g3.jpg", "g4.jpg", "g5.jpg"})

    # BAS ISIM KURALI — gercek urunde olculdu (thing:4790449 "Safety cover latch for
    # skate blades"): konumu yok sayan tarama "cover"i dondurup urunu "Kapak" yapmisti.
    # Dogru bas isim EN SAGDAKI eslesme, edattan ONCEKI parcada.
    _chk("(c) bas isim: 'Safety cover latch for skate blades' -> Mandal (Kapak DEGIL)",
         uicd.parca_terimi("Safety cover latch for skate blades CCM") == "Mandal",
         repr(uicd.parca_terimi("Safety cover latch for skate blades CCM")))
    _chk("(c) edat kuyrugu urunu adlandirmaz: 'grip for a fork' -> Tutamak",
         uicd.parca_terimi("Handlebar grip for a fork") == "Gidon Tutamağı",
         repr(uicd.parca_terimi("Handlebar grip for a fork")))
    # COGUL TOLERANSI — gercek basliklarda "dampers"/"fenders"/"Bolts" geciyor.
    _chk("(c) cogul jeton eslesir: 'Bicycle chain dampers' -> Damper",
         uicd.parca_terimi("Bicycle chain dampers") == "Damper",
         repr(uicd.parca_terimi("Bicycle chain dampers")))

    dk = _load(os.path.join(DIR, "denetim-kapisi.py"), "denetim_kapisi_t")
    urun = {"id": "renault-clio-bardaklik", "kategori": o["kategori"],
            "marka": o["marka"], "baslik": o["baslik"], "aciklama": o["aciklama"],
            "fiyat": o["fiyat_oneri"], "gorseller": ["https://x/y/g1.jpg"]}
    kayit = {"kaynak": "Thingiverse", "link": "https://www.thingiverse.com/thing:777",
             "lisans": "Creative Commons - Attribution", "tur": "ucretsiz-cc"}

    kf, gf = dk.kapi_fiyat(urun)
    _chk("(c) KAPI fiyat: taban ustu", kf is None, gf)
    ko, go = dk.kapi_olcu(urun, kayit)
    _chk("(c) KAPI olcu: aciklamada olcu satiri VAR", ko is None, go)
    _chk("(c) KAPI maket: yasak maket dili YOK", dk.kapi_maket_auto(urun) is None)
    _chk("(c) KAPI marka-kirli: kirli jeton YOK", dk.kapi_marka_kirli(urun) is None)
    ifsa = dk.kapi_ifsa(urun)
    _chk("(c) KAPI ifsa: SERT uretim-sureci dili YOK", not ifsa.get("sert"),
         str(ifsa.get("sert"))[:160])
    ka, ga = dk.kapi_ascii_id(urun)
    _chk("(c) KAPI ascii-id: id gecerli", ka is None, ga)


# =============================================================================
# IDDIA (d) — TUKETICI ENVANTERI: uc ekle betiginin UCU DE delege ediyor mu?
# =============================================================================
# 🔴 [[tuketici-yazilirken-tum-okuyucular-sayilir]]: ortak adimi yazmak yetmez; eski
# TEK BACAKLI dusus BIR betikte kalirsa ariza YER DEGISTIRIR, kapanmaz. Bu yuzden
# hem DELEGASYON hem ESKI DESENIN YOKLUGU iki yonlu olcuulur.
TUKETICILER = ("urun-ekle.py", "printables-ekle.py", "makerworld-ekle.py")
ESKI_DESEN = ('"HATA: emekli motor oneri yok"', '"HATA: kredi kapisi — urun AI izni yok"')


def iddia_d():
    for ad in TUKETICILER:
        yol = os.path.join(DIR, ad)
        govde = open(yol, encoding="utf-8").read()
        _chk("(d) %s ortak adimi CAGIRIYOR" % ad, "uicd.icerik_sagla(" in govde)
        for desen in ESKI_DESEN:
            _chk("(d) %s eski TEK BACAKLI dusus KALMADI: %s" % (ad, desen[:34]),
                 desen not in govde)


# =============================================================================
# MUTASYON BATARYASI — IZOLE golge agacta
# =============================================================================
# Her giris: (ad, dosya, eski, yeni, oldurucu_mu, HEDEF KOL ATFI)
MUTANTLAR = [
    ("M1 deterministik yedek SOKULDU", "urun_icerik_det.py",
     "    if not galeri:\n        return None, None,",
     "    if True:\n        return None, None,",
     True,
     "iddia (a)+(b2): yedek yolu kesilirse urun YINE DUSER — hattin tek-bacakliligi geri gelir"),
    ("M2 K398 icerik kolu SOKULDU", "thing-icerik.py",
     "if r.returncode == 0 and os.path.exists(cikti_yolu) and govde is None:",
     "if r.returncode == 0 and os.path.exists(cikti_yolu):",
     True,
     "iddia (b1): rc yalan soylerken hata govdesi SESSIZCE basarili sayilir (fail-open)"),
    ("M3 OLCU CAPASI SOKULDU", "urun_icerik_det.py",
     "        satirlar.append(OLCU_CAPA %",
     "        [].append(OLCU_CAPA %",
     True,
     "iddia (c): denetim-kapisi kapi_olcu 'olcu satiri yok' der -> kayit auto_sil olur"),
    ("M4 BAYAT DOSYA KAPISI SOKULDU", "urun_icerik_det.py",
     "        if os.path.exists(onerip):\n            os.unlink(onerip)",
     "        if False:\n            os.unlink(onerip)",
     True,
     "iddia (b3): onceki kosumdan kalan oneri.json DUSEN cagrinin kaniti sayilir"),
    ("M5 KONTROL — yalniz serbest metin", "urun_icerik_det.py",
     '"not": "deterministik ureteç (AI cagrisi YOK)"',
     '"not": "deterministik ureteç (AI cagrisi YOK).."',
     False,
     "hicbir iddia bu metne capalanmamali; kirmizi yanarsa batarya BATTANIYE kirmizidir"),
]


KOK = os.path.dirname(DIR)


def _golge_agac():
    """DEPO KOKUNUN symlink golgesi (yalniz `tools/` gercek dizin olarak yeniden kurulur).

    🔴 ILK HALI YALNIZ tools/ GOLGELIYORDU ve OLCULDU ki golgenin KENDISI kirmiziydi:
    `kategori-kapisi.py` kok dizindeki `index.html`i okur, golge kokte o dosya YOKTU ->
    test ACILISTA cokuyordu. Sonuc: DORT mutantin dordu de "oldu" gorunuyordu ama
    HICBIRI hedefine ULASMAMISTI ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
    Yakalayan sey KONTROL mutantiydi: serbest metin degisimi de kirmizi yandi =
    BATTANIYE KIRMIZI. Bu yuzden golge artik TUM koku tasir ve batarya TABAN kolu
    kosar (mutasyonsuz golge YESIL olmali; degilse batarya HICBIR SEY olcmez).

    [[pythonpath-mutanti-modulun-kendi-syspath-insertiyle-olur]]: modul kendi dizinini
    sys.path'e koydugu icin golge TAM dizin olmali, tek dosya DEGIL.
    """
    golge = tempfile.mkdtemp(prefix="uicd-golge-")
    for ad in os.listdir(KOK):
        if ad == "tools":
            continue
        os.symlink(os.path.join(KOK, ad), os.path.join(golge, ad))
    hedef = os.path.join(golge, "tools")
    os.mkdir(hedef)
    for ad in os.listdir(DIR):
        os.symlink(os.path.join(DIR, ad), os.path.join(hedef, ad))
    return golge, hedef


def _golgede_kos(hedef):
    return subprocess.run(
        [sys.executable, os.path.join(hedef, os.path.basename(__file__))],
        capture_output=True, text=True)


def mutasyon_bataryasi():
    print("\n=== MUTASYON BATARYASI (izole golge agac) ===")
    onceki_sha = {ad: _sha(os.path.join(DIR, ad))
                  for ad in ("urun_icerik_det.py", "thing-icerik.py")}

    # 🔴 TABAN KOLU — ONCE bu. Mutasyonsuz golge YESIL degilse her mutant "oldu"
    # gorunur ve batarya hicbir sey olcmez; bu kol o korlugu KAPATIR.
    golge, hedef = _golge_agac()
    try:
        taban = _golgede_kos(hedef)
        _chk("TABAN: mutasyonsuz golge agac YESIL", taban.returncode == 0,
             (taban.stderr or taban.stdout or "")[-200:])
        if taban.returncode != 0:
            print("  -> TABAN KIRMIZI: mutantlar KOSULMADI (olcum yapilamaz).")
            return
    finally:
        shutil.rmtree(golge, ignore_errors=True)

    oldu = kacan = kontrol_yesil = 0
    for ad, dosya, eski, yeni, oldurucu, atif in MUTANTLAR:
        golge, hedef = _golge_agac()
        try:
            kaynak = os.path.join(DIR, dosya)
            govde = open(kaynak, encoding="utf-8").read()
            if eski not in govde:
                print("  KALDI  %s -> CAPA BULUNAMADI (mutant hedefe ULASMADI)" % ad)
                FAILS.append(ad + " (capa yok)")
                continue
            os.unlink(os.path.join(hedef, dosya))
            with open(os.path.join(hedef, dosya), "w", encoding="utf-8") as f:
                f.write(govde.replace(eski, yeni, 1))
            r = _golgede_kos(hedef)
            kirmizi = r.returncode != 0
            if oldurucu and kirmizi:
                oldu += 1
                print("  ok  %s -> OLDU (kirmizi)  | %s" % (ad, atif))
            elif oldurucu and not kirmizi:
                kacan += 1
                print("  KALDI  %s -> HAYATTA (yesil kaldi!)  | %s" % (ad, atif))
                FAILS.append(ad + " HAYATTA")
            elif not oldurucu and not kirmizi:
                kontrol_yesil += 1
                print("  ok  %s -> KONTROL yesil kaldi  | %s" % (ad, atif))
            else:
                print("  KALDI  %s -> KONTROL KIRMIZI yandi (battaniye kirmizi!)" % ad)
                FAILS.append(ad + " KONTROL kirmizi")
        finally:
            shutil.rmtree(golge, ignore_errors=True)
    print("  OLDURUCU oldu: %d/%d · KONTROL yesil: %d"
          % (oldu, sum(1 for m in MUTANTLAR if m[4]), kontrol_yesil))
    for ad, sha in onceki_sha.items():
        _chk("CANLI GOVDE sha256 ONCE == SONRA: " + ad,
             _sha(os.path.join(DIR, ad)) == sha)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true")
    args = ap.parse_args()

    uicd = _load(os.path.join(DIR, "urun_icerik_det.py"), "urun_icerik_det_t")
    tc = _load(os.path.join(DIR, "thing-icerik.py"), "thing_icerik_t")

    print("=== IDDIA (a) AI izni KAPALI -> urun DUSMEZ ===")
    o = iddia_a(uicd)
    print("=== IDDIA (b) AI DUSTU -> adim BASARISIZ, urun DUSMEZ ===")
    iddia_b(uicd, tc)
    print("=== IDDIA (c) sozlesme + denetim-kapisi kapilari ===")
    if o:
        iddia_c(uicd, o)
    print("=== IDDIA (d) tuketici envanteri (3 ekle betigi) ===")
    iddia_d()

    if args.mutasyon:
        mutasyon_bataryasi()

    print("\n%s" % ("KIRMIZI: %d iddia kaldi -> %s" % (len(FAILS), FAILS[:6])
                    if FAILS else "YESIL: tum iddialar gecti"))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
