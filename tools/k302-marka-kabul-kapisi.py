#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K302 — kahve marka mimar-eki kabul bataryasi (5 eksen + 2 mutant + kontrol).

Hedef: `tools/arama.py` UYUM_MARKA_IZINLI ve UYUM_MARKA_MIMAR_EKI kumesine
26 Agu 2026 mimar karariyla 6 kahve markasi (AeroPress kanonik / Bialetti /
DeLonghi / Jura / Lavazza / Mazzer) eklendi. Bu batarya:

  A1 — 6 markanin kanonik kabulu + YAZIM TABLOSU (kanonik 6/6, alt. red N/12)
  A2 — MaCiT dilim-1'in 6 aday fiksturu uyum_sebebi() ile GECTI, marka turetimi
  A3 — BOS marka jenerik kayit GECTI (uyum opsiyonel, tara() kirli=0)
  A4 — NEGATIF: kategori adi (Kahve/Coffee) marka olarak REDDEDILDI
  A5 — SERT KOL: 6 marka eki yeni uyum RED'i dogurmadi mi? (mutant ONCE vs SONRA)

  KONTROL — regresyon: izinli-eki farki 139 (ONCE ve SONRA AYNI) +
            ilgisiz uyum_marka_kanonik iddialari YESIL.

  M1 — mutant: 6 jeton UYUM_MARKA_IZINLI'den cikar -> A1+A2 DUSMELI, A3 GECmeli.
  M2 — mutant: uyum_ogesi_sebebi() bos-marka kolu gevsetilir -> A4 DUSMELI.
  KONTROL-MUTANT — ilgisiz: UYUM_YIL_EN_ERKEN 1 azaltilir, 5/5 YESIL.

CIKTIDA: yalniz stdout. rc=0 hepsi gectiyse, rc=1 tek madde dustuyse.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "arama.py")
MARKA_BOS = os.path.join(KOK, "tools", "marka-uyumdan-bos-kapisi.py")

# SABIT: kod degisikliginden ONCE olculdu (python3 -c ile). 6 jeton iki kumeye
# BIRDEN girdigi icin SONRA da AYNI olmali.
IZINLI_EKSI_EKI_TABAN = 139

KANONIK_MARKALAR = ["AeroPress", "Bialetti", "DeLonghi", "Jura", "Lavazza", "Mazzer"]
ALTERNATIF = {
    "AeroPress": "Aeropress",
    "Bialetti": "bialetti",
    "DeLonghi": "De'Longhi",
    "Jura": "JURA",
    "Lavazza": "LAVAZZA",
    "Mazzer": "mazzer",
}


def _yukle_arama():
    sys.path.insert(0, os.path.dirname(ARAC))
    import arama
    return arama


def _yukle_marka_bos_tara():
    spec = importlib.util.spec_from_file_location("marka_uyumdan_bos", MARKA_BOS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.tara


def _urun(**kw):
    return kw


# ──────────────────────────────────────────────────────────────────────────
# 5 EKSEN + KONTROL
# ──────────────────────────────────────────────────────────────────────────

def eksen_a1(arama):
    """6 markanin kanonik kabulu + YAZIM TABLOSU."""
    print("A1 — 6 markanin kanonik kabulu + YAZIM TABLOSU")

    gecti_kanonik = 0
    alt_red = 0

    print()
    print("  %-12s %-12s %-22s %-22s %-10s %-12s" % (
        "ham", "kume-bicim", "norm(ham)", "norm(kume)", "ESLESTI?", "kanonik()"))
    print("  " + "-" * 95)

    for k in KANONIK_MARKALAR:
        ham_norm = arama.model_normalize(k)
        kume_norm = arama.model_normalize(k)
        kan = arama.uyum_marka_kanonik(k)
        eslesti = "EVET" if ham_norm == kume_norm else "HAYIR"
        k_kan = (kan == k)
        if k_kan:
            gecti_kanonik += 1
        print("  %-12s %-12s %-22s %-22s %-10s %-12s %s" % (
            k, k, ham_norm, kume_norm, eslesti, repr(kan),
            "OK" if k_kan else "FAIL"))

    print()
    for k, alt in ALTERNATIF.items():
        ham_norm = arama.model_normalize(alt)
        kume_norm = arama.model_normalize(k)
        kan = arama.uyum_marka_kanonik(alt)
        eslesti = "EVET" if ham_norm == kume_norm else "HAYIR"
        ayrisma = ""
        if k == "DeLonghi":
            ayrisma = "  NORMALIZE-DE-AYRISIYOR"
        red_mi = (kan == "")
        if red_mi:
            alt_red += 1
        print("  %-12s %-12s %-22s %-22s %-10s %-12s %s%s" % (
            alt, k, ham_norm, kume_norm, eslesti, repr(kan),
            "RED" if red_mi else "SIZDI!", ayrisma))

    gecti = (gecti_kanonik == 6) and (alt_red == 6)
    print()
    print("A1: kanonik=%d/6 alt-red=%d/6" % (gecti_kanonik, alt_red))
    print("A1-YAZIM: alternatif yazim %d/12 REDDEDILDI (fail-closed korundu)" % alt_red)
    print("A1 SONUC: %s" % ("GECTI" if gecti else "DUSTU"))
    return gecti


def eksen_a2(arama):
    """MaCiT dilim-1'in 6 adayi, kuru kosum.

    Fikstur olarak bataryaya gomulur (urunler.json'a YAZILMAZ).
    """
    print()
    print("A2 — MaCiT dilim-1'in 6 aday fiksturu")

    # (pid, uyum, marka). marka None ise alan YOK; jenerik kol.
    fikstur = [
        ("wood-pla-coffee-espresso-tamper", None, None),
        ("cuchara-y-prensadora-cafe", None, None),
        ("waste-container-for-krups-coffee-machine",
         [{"marka": "Krups"}], ["Krups"]),
        ("coffe-machine-storage", None, None),
        ("cup-s-under-plate-lavazza-a-modo-mio-tiny-coffee-machine",
         [{"marka": "Lavazza"}], ["Lavazza"]),
        ("mazzer-super-jolly-deckel-fuer-kaffeebohnenbehaelter-o-120mm",
         [{"marka": "Mazzer"}], ["Mazzer"]),
    ]

    gecen = 0
    red = 0
    marka_eslesen = []
    jenerik_bos = 0

    for pid, uyum, marka in fikstur:
        kayit = _urun(id=pid, kategori="Elektronik")
        if uyum is not None:
            kayit["uyum"] = uyum
        if marka is not None:
            kayit["marka"] = marka
        sebep = arama.uyum_sebebi(kayit)
        turetilmis = arama.marka_uyumdan_turet(kayit)
        if sebep is None:
            gecen += 1
        else:
            red += 1
        if uyum is None:
            if turetilmis == []:
                jenerik_bos += 1
        else:
            for m in uyum:
                if m["marka"] not in marka_eslesen:
                    marka_eslesen.append(m["marka"])
        print("  pid=%s sebep=%s marka=%s" % (pid, sebep, turetilmis))

    print()
    print("A2: GECEN=%d/6 RED=%d | marka-esleseni=%d (%s) · jenerik-bos=%d" % (
        gecen, red, len(marka_eslesen),
        ", ".join(marka_eslesen), jenerik_bos))
    gecti = (gecen == 6) and (red == 0)
    print("A2 SONUC: %s" % ("GECTI" if gecti else "DUSTU"))
    return gecti


def eksen_a3(arama, tara):
    """Bos marka jenerik kayit GECTI: 3 varyant (yok / [] / None)."""
    print()
    print("A3 — BOS marka jenerik kayit GECTI")

    varyantlar = [
        {"id": "jenerik-tamper", "kategori": "Elektronik"},
        {"id": "jenerik-tamper", "kategori": "Elektronik", "marka": []},
        {"id": "jenerik-tamper", "kategori": "Elektronik", "marka": None},
    ]

    gecen = 0
    kirli_toplam = 0
    for v in varyantlar:
        sebep = arama.uyum_sebebi(v)
        kirli = tara([v])
        if sebep is None:
            gecen += 1
        kirli_toplam += len(kirli)
        print("  varyant marka=%s sebep=%s kirli=%d" % (
            v.get("marka", "YOK"), sebep, len(kirli)))

    print()
    print("A3: gecen=%d/3 kirli=%d" % (gecen, kirli_toplam))
    gecti = (gecen == 3) and (kirli_toplam == 0)
    print("A3 SONUC: %s" % ("GECTI" if gecti else "DUSTU"))
    return gecti


def eksen_a4(arama):
    """NEGATIF, KRITIK: kategori adi marka olarak REDDEDILMELI.

    Fixture: uyum=[{"marka": "Kahve"}], marka=[] (turetilen ile ayni; oge_sebebi yolu
    IKIZ TANIM'dan ONCE calistigi icin 'KAPALI kumeden olmali' mesaji once yakalanir).
    """
    print()
    print("A4 — NEGATIF: kategori adi marka olarak REDDEDILMELI")

    fikstur = [
        {"uyum": [{"marka": "Kahve"}], "marka": []},
        {"uyum": [{"marka": "Coffee"}], "marka": []},
    ]

    red = 0
    for f in fikstur:
        sebep = arama.uyum_sebebi(f)
        kan = arama.uyum_marka_kanonik(f["uyum"][0]["marka"])
        sebep_ok = sebep is not None and "KAPALI kumeden olmali" in sebep
        kan_ok = (kan == "")
        if sebep_ok and kan_ok:
            red += 1
        print("  marka=%s sebep=%s kanonik=%r sebep_ok=%s kan_ok=%s" % (
            f["uyum"][0]["marka"], sebep, kan, sebep_ok, kan_ok))

    print()
    print("A4: red=%d/2" % red)
    gecti = (red == 2)
    print("A4 SONUC: %s" % ("GECTI" if gecti else "DUSTU"))
    return gecti


def eksen_a5(arama):
    """YENI varyant hiçbir uyum ogesini REDDETTIRMİYOR mu? SERT KOL.

    B4 yalniz top-level `marka` dizisini tarar. Asil risk: `uyum[].marka` ya da
    `uyum[].model` uzerinden `marka_varyanti_sebebi()` RED yolu acabilir
    (arama.py:2460-2463). ONCE: mutant ile 6 jeton kumeden cikarilmis
    (pre-K302 simulasyonu). SONRA: canli modül. Fark > 0 ise YENI RED dogdu.
    """
    print()
    print("A5 — SERT KOL: 6 marka eki yeni uyum RED'i dogurdu mu?")

    urunler = os.path.join(KOK, "urunler.json")
    with open(urunler, encoding="utf-8") as f:
        katalog = json.load(f)

    def _redleri_say(arama_modul):
        red = 0
        for u in katalog:
            for oge in (u.get("uyum") or []):
                if arama_modul.uyum_ogesi_sebebi(oge) is not None:
                    red += 1
        return red

    # SONRA: canli arama
    sonra_red = _redleri_say(arama)

    # ONCE: mutant ile 6 jeton kumeden cikarilmis
    with open(ARAC, encoding="utf-8") as f:
        metin = f.read()

    hedef_bas = '    # 5. tur, C grubu (6) — mimar karari 26 Agu 2026, kahve sektoru.'
    hedef_son = '    "AeroPress", "Bialetti", "DeLonghi", "Jura", "Lavazza", "Mazzer",\n'

    satirlar = metin.split("\n")
    satir_indeks = None
    for i, s in enumerate(satirlar):
        if s.startswith(hedef_bas):
            satir_indeks = i
            break
    assert satir_indeks is not None, "A5 baslangic satiri bulunamadi"

    bitis_indeks = None
    for j in range(satir_indeks, len(satirlar)):
        if satirlar[j] == hedef_son.rstrip("\n"):
            bitis_indeks = j
            break
    assert bitis_indeks is not None, "A5 bitis satiri bulunamadi"

    yeni_satirlar = satirlar[:satir_indeks] + satirlar[bitis_indeks + 1:]
    yeni_metin = "\n".join(yeni_satirlar)
    assert yeni_metin != metin, "A5 metni degistirmedi"
    arama_mut = _mutant_yukle(yeni_metin)

    once_red = _redleri_say(arama_mut)

    yeni_red = sonra_red - once_red
    print("A5: uyum-ogesi RED ONCE=%d SONRA=%d · yeni-red=%d (0 olmali)" % (
        once_red, sonra_red, yeni_red))
    gecti = (yeni_red <= 0)
    print("A5 SONUC: %s" % ("GECTI" if gecti else "DUSTU"))
    return gecti


def eksen_kontrol(arama):
    """Regresyon: izinli-eki farki + ilgisiz uyum_marka_kanonik iddialari."""
    print()
    print("KONTROL — regresyon")

    fark = len(arama.UYUM_MARKA_IZINLI) - len(arama.UYUM_MARKA_MIMAR_EKI)
    iddialar = [
        ("Volvo", "Volvo"),
        ("Volvo Penta", "Volvo Penta"),
        ("Yanmar", "Yanmar"),
        ("Johnson", ""),
        ("Raspberry", ""),
    ]
    tum_ok = True
    for ham, bek in iddialar:
        kan = arama.uyum_marka_kanonik(ham)
        ok = (kan == bek)
        if not ok:
            tum_ok = False
        print("  uyum_marka_kanonik(%s) = %r (beklenen %r) %s" % (
            ham, kan, bek, "OK" if ok else "FAIL"))

    fark_ok = (fark == IZINLI_EKSI_EKI_TABAN)
    print("  izinli-eki farki = %d (taban %d) %s" % (
        fark, IZINLI_EKSI_EKI_TABAN, "OK" if fark_ok else "FAIL"))
    gecti = tum_ok and fark_ok
    print("KONTROL SONUC: %s (izinli-eksi-eki farki ONCE=%d SONRA=%d)" % (
        "GECTI" if gecti else "DUSTU", IZINLI_EKSI_EKI_TABAN, fark))
    return gecti


# ──────────────────────────────────────────────────────────────────────────
# MUTANTLAR — kaynak metin uzerinde gecici, exec ile ayri modul nesnesi.
# ──────────────────────────────────────────────────────────────────────────

def _mutant_yukle(metin):
    mod = type(sys)("arama_mutant")
    mod.__file__ = ARAC
    exec(compile(metin, ARAC, "exec"), mod.__dict__)
    return mod


def _mutant_bos_marka_tara(arama_mut, tara_mut):
    varyantlar = [
        {"id": "jenerik-tamper", "kategori": "Elektronik"},
        {"id": "jenerik-tamper", "kategori": "Elektronik", "marka": []},
        {"id": "jenerik-tamper", "kategori": "Elektronik", "marka": None},
    ]
    gecen = 0
    kirli_toplam = 0
    for v in varyantlar:
        sebep = arama_mut.uyum_sebebi(v)
        kirli = tara_mut([v])
        if sebep is None:
            gecen += 1
        kirli_toplam += len(kirli)
    return gecen == 3 and kirli_toplam == 0


def mutant_m1():
    """M1 — 6 jeton UYUM_MARKA_IZINLI metninden cikar."""
    print()
    print("M1 — UYUM_MARKA_IZINLI metninden 6 jeton cikarildi (MIMAR_EKI dokunulmaz)")

    with open(ARAC, encoding="utf-8") as f:
        metin = f.read()

    # IZINLI 5. tur blogunu (uzun gerekce + 6 jeton) sil.
    hedef_bas = '    # 5. tur, C grubu (6) — mimar karari 26 Agu 2026, kahve sektoru.'
    hedef_son = '    "AeroPress", "Bialetti", "DeLonghi", "Jura", "Lavazza", "Mazzer",\n'

    satir_indeks = None
    satirlar = metin.split("\n")
    for i, s in enumerate(satirlar):
        if s.startswith(hedef_bas):
            satir_indeks = i
            break
    assert satir_indeks is not None, "M1 baslangic satiri bulunamadi"

    bitis_indeks = None
    for j in range(satir_indeks, len(satirlar)):
        if satirlar[j] == hedef_son.rstrip("\n"):
            bitis_indeks = j
            break
    assert bitis_indeks is not None, "M1 bitis satiri bulunamadi"

    yeni_satirlar = satirlar[:satir_indeks] + satirlar[bitis_indeks + 1:]
    yeni_metin = "\n".join(yeni_satirlar)
    assert yeni_metin != metin, "M1 metni degistirmedi"

    arama_mut = _mutant_yukle(yeni_metin)
    spec = importlib.util.spec_from_file_location("mbk_mut", MARKA_BOS)
    mbk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mbk)
    tara_mut = mbk.tara

    # A1: 6 kanonik yazimdan 0/6 (kanonik(ham) doner "")
    a1_oldu = True
    for k in KANONIK_MARKALAR:
        if arama_mut.uyum_marka_kanonik(k) == k:
            a1_oldu = False
            break

    # A2: Lavazza/Mazzer RED (Krups hâlâ gecer)
    lav = _urun(id="cup-s-under-plate-lavazza",
                uyum=[{"marka": "Lavazza"}], marka=["Lavazza"])
    maz = _urun(id="mazzer-super-jolly-deckel",
                uyum=[{"marka": "Mazzer"}], marka=["Mazzer"])
    lav_red = arama_mut.uyum_sebebi(lav) is not None
    maz_red = arama_mut.uyum_sebebi(maz) is not None

    # A3: jenerik kolu — markadan bagimsiz — hâlâ gecmeli (M1 hedefi DEGIL).
    a3_ok = _mutant_bos_marka_tara(arama_mut, tara_mut)

    oldurdu = []
    if a1_oldu:
        oldurdu.append("A1")
    if lav_red and maz_red:
        oldurdu.append("A2")
    a3_oldurdu = not a3_ok

    beklenen = a1_oldu and lav_red and maz_red and a3_ok and (not a3_oldurdu)
    print("  A1=%s A2(red Lavazza,Mazzer)=(%s,%s) A3=%s" % (
        "DUSTU" if a1_oldu else "GECTI",
        "DUSTU" if lav_red else "GECTI",
        "DUSTU" if maz_red else "GECTI",
        "DUSTI" if not a3_ok else "GECTI"))
    if oldurdu:
        print("M1 OLDURDU=%s (hedef kol: UYUM_MARKA_IZINLI uyelik testi, arama.py:2065)" % ",".join(oldurdu))
    print("M1 SONUC: %s (A3 hedef degildi: %s)" % (
        "BEKLENDI" if beklenen else "BEKLENMEDIK",
        "OLDURDU" if a3_oldurdu else "DUSURMEDI"))
    return beklenen


def mutant_m2():
    """M2 — uyum_ogesi_sebebi() bos-marka kolu gevsetilir.

    `if uyum_marka_kanonik(ham) == "":` satirini
    `if ham is not None and not isinstance(ham, str):` ile degistir.
    """
    print()
    print("M2 — bos-marka kolu gevsetildi (tip-kontrol haline getirildi)")

    with open(ARAC, encoding="utf-8") as f:
        metin = f.read()

    eski = 'if uyum_marka_kanonik(ham) == "":'
    yeni = 'if ham is not None and not isinstance(ham, str):'
    yeni_metin = metin.replace(eski, yeni)
    assert yeni_metin != metin, "M2 metni degistirmedi — pattern eslesmedi"

    arama_mut = _mutant_yukle(yeni_metin)
    spec = importlib.util.spec_from_file_location("mbk_mut", MARKA_BOS)
    mbk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mbk)
    tara_mut = mbk.tara

    # A4: Kahve / Coffee — marka=[] ile turetilen=[] eslesir, oge_sebebi M2'de
    # Kahve'yi kabul eder, IKIZ TANIM devreye girmeden uyum_sebebi None doner.
    f1 = {"uyum": [{"marka": "Kahve"}], "marka": []}
    f2 = {"uyum": [{"marka": "Coffee"}], "marka": []}
    s1 = arama_mut.uyum_sebebi(f1)
    s2 = arama_mut.uyum_sebebi(f2)
    a4_oldu = (s1 is None) and (s2 is None)

    # A3: jenerik (marka yok/[]/None) — tip-kontrolu gevsedigi icin None ve []
    # icin eski kanonik() davranisindan farkli sonuc cikabilir; ama asil olarak
    # bos-marka kolu gevsediginden "yazilan ne olursa olsun gecer" olur.
    a3_ok = _mutant_bos_marka_tara(arama_mut, tara_mut)

    beklenen = a4_oldu and a3_ok
    print("  Kahve sebep=%s Coffee sebep=%s A3=%s" % (
        s1, s2, "GECTI" if a3_ok else "DUSTU"))
    if a4_oldu:
        print("M2 OLDURDU=A4 (hedef kol: uyum_ogesi_sebebi kapali-kume kontrolu, arama.py:2452)")
    print("M2 SONUC: %s" % ("BEKLENDI" if beklenen else "BEKLENMEDIK"))
    if a3_ok:
        print("M2 KANIT: A3-tek-eksenli batarya bu mutanti GORMEZDI (A3=GECTI)")
    return beklenen


def mutant_kontrol():
    """KONTROL-MUTANT: UYUM_YIL_EN_ERKEN 1 azaltilir; 5 eksen YESIL kalmali."""
    print()
    print("KONTROL-MUTANT — UYUM_YIL_EN_ERKEN 1 azaltildi (ilgisiz kol)")

    with open(ARAC, encoding="utf-8") as f:
        metin = f.read()

    eski = "UYUM_YIL_EN_ERKEN = 1900"
    yeni = "UYUM_YIL_EN_ERKEN = 1899"
    yeni_metin = metin.replace(eski, yeni)
    assert yeni_metin != metin, "KONTROL-MUTANT metni degistirmedi"

    arama_mut = _mutant_yukle(yeni_metin)
    spec = importlib.util.spec_from_file_location("mbk_mut", MARKA_BOS)
    mbk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mbk)
    tara_mut = mbk.tara

    # 5 ekseni mutant uzerinden kos:
    a1_ok = True
    for k in KANONIK_MARKALAR:
        if arama_mut.uyum_marka_kanonik(k) != k:
            a1_ok = False
            break

    lav = _urun(id="cup-s-under-plate-lavazza",
                uyum=[{"marka": "Lavazza"}], marka=["Lavazza"])
    maz = _urun(id="mazzer-super-jolly-deckel",
                uyum=[{"marka": "Mazzer"}], marka=["Mazzer"])
    a2_ok = (arama_mut.uyum_sebebi(lav) is None
             and arama_mut.uyum_sebebi(maz) is None)

    a3_ok = _mutant_bos_marka_tara(arama_mut, tara_mut)

    f1 = {"uyum": [{"marka": "Kahve"}], "marka": []}
    f2 = {"uyum": [{"marka": "Coffee"}], "marka": []}
    a4_ok = (arama_mut.uyum_sebebi(f1) is not None
             and arama_mut.uyum_sebebi(f2) is not None)

    fark = (len(arama_mut.UYUM_MARKA_IZINLI)
            - len(arama_mut.UYUM_MARKA_MIMAR_EKI))
    kontrol_ok = (fark == IZINLI_EKSI_EKI_TABAN)

    bes_yesil = a1_ok and a2_ok and a3_ok and a4_ok and kontrol_ok
    print("  A1=%s A2=%s A3=%s A4=%s KONTROL=%s" % (
        "YESIL" if a1_ok else "KIRMIZI",
        "YESIL" if a2_ok else "KIRMIZI",
        "YESIL" if a3_ok else "KIRMIZI",
        "YESIL" if a4_ok else "KIRMIZI",
        "YESIL" if kontrol_ok else "KIRMIZI"))
    print("KONTROL-MUTANT SONUC: %s" % ("YESIL" if bes_yesil else "KIRMIZI"))
    return bes_yesil


# ──────────────────────────────────────────────────────────────────────────
# ANA
# ──────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutant", action="store_true",
                    help="Sadece mutantlari kos")
    args = ap.parse_args()

    arama = _yukle_arama()
    tara = _yukle_marka_bos_tara()

    if args.mutant:
        m1 = mutant_m1()
        m2 = mutant_m2()
        km = mutant_kontrol()
        gecti = m1 and m2 and km
        sys.exit(0 if gecti else 1)

    a1 = eksen_a1(arama)
    a2 = eksen_a2(arama)
    a3 = eksen_a3(arama, tara)
    a4 = eksen_a4(arama)
    a5 = eksen_a5(arama)
    kontrol = eksen_kontrol(arama)

    m1 = mutant_m1()
    m2 = mutant_m2()
    km = mutant_kontrol()

    print()
    print("=" * 72)
    hepsi = a1 and a2 and a3 and a4 and a5 and kontrol and m1 and m2 and km
    print("OZET: A1=%s A2=%s A3=%s A4=%s A5=%s KONTROL=%s M1=%s M2=%s KONTROL-MUTANT=%s" % (
        "GECTI" if a1 else "DUSTU",
        "GECTI" if a2 else "DUSTU",
        "GECTI" if a3 else "DUSTU",
        "GECTI" if a4 else "DUSTU",
        "GECTI" if a5 else "DUSTU",
        "GECTI" if kontrol else "DUSTU",
        "GECTI" if m1 else "DUSTU",
        "GECTI" if m2 else "DUSTU",
        "YESIL" if km else "KIRMIZI"))
    print("BATARYA rc=%d" % (0 if hepsi else 1))
    sys.exit(0 if hepsi else 1)


if __name__ == "__main__":
    main()
