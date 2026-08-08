#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/yedekle.py SIR ELEMESI + KOK SIR TEMIZLIGI (8 Agu 2026).

OKAN KARARI: "Jetonlari yedekten cikar." Sir dosyalari ORTAK Drive yedegine
KOPYALANMAZ; yalniz yerel makinede dururlar (hepsi kaynagindan yeniden uretilebilir).

BU DOSYA IKI IDDIAYI NOBETLER — ikisi de SESSIZ hata sinifidir:
  (A) YAZMA YOLU KAPALI: hicbir bayrakla (varsayilan ya da EMEKLI `--sirlar`) kanonik
      sir kumesindeki bir ad yedek hedefine YAZILMAZ. Bu kol curursa sir sessizce
      ORTAK Drive'a geri sizar ve hicbir sey kirmizi yanmaz.
  (B) TEMIZLIK GERCEKTEN KOKE ULASIYOR: `--sir-temizle` bayragi ONCEDEN yalniz
      skills_yaz()'a geciyordu; yedek KOKUNDEKI sirlara ULASAN HICBIR KOD YOLU YOKTU
      ("temizleme araci var" beyani o kalemler icin GERCEK DEGILDI). Bu, [[beyan-edilmis-
      survivor]] sinifinin ta kendisidir: arac vardi, yuzey olculmemisti.
  Ayrica FAIL-CLOSED yon: yereldeki ASLI olmayan/okunamayan kalem SILINMEZ (yanlis
  silme KALICI kayiptir), ve `--kuru-prova` HICBIR SEY silmez.

⚠️ GERCEK DRIVE'A/HOME'A DOKUNMAZ: tum kosumlar yedekle-test.py'nin KANONIK izole
ortaminda (sahte HOME + sahte git deposu + drive_yolu STUB'u) kosar. Kum havuzu
kurulumu BURADA YENIDEN YAZILMAZ — ikiz tanim sessizce ayrisir ([[ikiz-tanim-sessiz-
ayrisma]]), bu yuzden yedekle-test.py'den ITHAL edilir.

🔴 SIR ICERIGI YOK: fiksturler sentetik, ANLAMSIZ govdelerdir; gercek jeton bicimi
taklit edilmez ([[nobetci-kendi-dosyasinda-sizinti]]).

Kosum:
    python3 tools/yedek-sir-eleme-test.py            # tam batarya (iddia + mutasyon)
    python3 tools/yedek-sir-eleme-test.py --iddia    # yalniz iddialar (mutasyon YOK)
"""
import importlib.util
import os
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
YEDEKLE = os.path.join(TOOLS, "yedekle.py")
YEDEKLE_TEST = os.path.join(TOOLS, "yedekle-test.py")

# Kum havuzunda YEREL ASLI OLAN sir adlari (silinebilir olmalari icin sart).
YERELI_OLAN = (".r2-credentials.json", ".thingiverse-token", ".onizleme-kapat-anahtar")
# Kanonik kumede olan ama kum havuzunda YEREL ASLI OLMAYAN ad -> FAIL-CLOSED kalemi.
YERELSIZ = ".npmrc"
# YALNIZ REPO_SIR'de olan (SIR_ADLARI ad kara-listesinde ve ad deseninde OLMAYAN) ad:
# kanonik kume DARALIRSA once bu sizar -> kume kaynagini tek basina olcen iddia.
YALNIZ_REPO_SIR = ".mukerrer-istisna.json"
# Sir OLMAYAN, hedefte BULUNMASI beklenen kontrol izi: eslestirici oluyse "bulunamadi"
# sahte temizlik olurdu ([[olculdu-diyen-hukum-kaniti]]).
KONTROL_IZI = "AGENTS.md"

SAHTE_GOVDE = "sentetik-fikstur-govdesi-gercek-deger-DEGIL\n"
ISARET_CAPA = '    kuru = ("--kuru" in sys.argv) or ("--dry-run" in sys.argv)\n'

SONUC = []


def kontrol(ad, ok, ayrinti=""):
    SONUC.append((ad, bool(ok), ayrinti))
    print(("  ✅ " if ok else "  ❌ ") + ad + (("  — " + ayrinti) if ayrinti else ""))
    return bool(ok)


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _yaz(yol, govde=SAHTE_GOVDE):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde)


def senaryo(betik, yedekle, harness, td):
    """TEK senaryo — saglam kodda TUM iddialar YESIL olmali; mutantta en az biri DUSER.

    Doner: {iddia_adi: bool}. Iddia adlari (a)..(j) harfleriyle onlenir ki mutasyon
    raporunda HANGI iddianin dustugu gorunsun (toplu 'kirmizi' hukmu ekseni gizler)."""
    o = harness.izole_ortam(td, yedekle, memory_adet=6, skills_adet=4)
    if betik != YEDEKLE:                       # mutant: kum havuzunun betigini degistir
        shutil.copy2(betik, o["betik"])
    kok, hedef = o["kok"], o["hedef"]

    # Kum havuzu repo kokune KANONIK sir adlarinin YERELDEKI ASILLARINI koy.
    for ad in tuple(yedekle.REPO_SIR) + YERELI_OLAN:
        _yaz(os.path.join(kok, ad))
    kanonik = yedekle.kok_sir_kumesi()

    def hedefteki_sirlar():
        try:
            return sorted(g for g in os.listdir(hedef) if g.lower() in kanonik)
        except OSError:
            return []

    iddia = {}
    # ---- 1) VARSAYILAN KOSUM: sir YAZILMAZ --------------------------------
    r1 = harness.izole_kos(o)
    iddia["(a) varsayilan kosum hedefe HIC sir yazmadi"] = (hedefteki_sirlar() == [])
    iddia["(b) yedek KAPSAMI cokmedi (memory+skills+repo yazildi)"] = (
        len(harness.hedef_dosyalari(hedef)) >= o["memory_adet"] + o["skills_adet"]
        + len(yedekle.REPO_BEKLENEN))
    iddia["(c) eleme SESSIZ degil (elenen kalemler ADIYLA basildi)"] = (
        "SIR ELEMESI:" in r1.stdout
        and all(ad in r1.stdout for ad in yedekle.REPO_SIR))

    # ---- 2) EMEKLI --sirlar bayragi de yazmamali ---------------------------
    r2 = harness.izole_kos(o, "--sirlar")
    iddia["(d) EMEKLI --sirlar da hedefe sir yazmadi"] = (hedefteki_sirlar() == [])
    # 🔴 KUMENIN IKI KAYNAGI AYRI AYRI OLCULUR: tek "hic sir sizmadi" iddiasi
    # katmanlarin VEYA'sidir ([[beyan-edilmis-survivor]]) — kume REPO_SIR'i kaybederse
    # (e) tek basina, SIR_ADLARI'ni kaybederse (k) tek basina kirmizi yanmali.
    iddia["(e) yalniz REPO_SIR'de olan ad da elendi (kume kaynagi 1)"] = (
        not os.path.exists(os.path.join(hedef, YALNIZ_REPO_SIR))
        and YALNIZ_REPO_SIR in r2.stdout)
    iddia["(k) SIR_ADLARI kara-listesindeki adlar da elendi (kume kaynagi 2)"] = not any(
        os.path.exists(os.path.join(hedef, ad)) for ad in YERELI_OLAN)

    # ---- 3) ONCEKI SURUMDEN KALMA kopyalar hedefe EKILIR ------------------
    for ad in YERELI_OLAN:
        _yaz(os.path.join(hedef, ad))
    _yaz(os.path.join(hedef, YERELSIZ))        # yerel asli YOK -> FAIL-CLOSED
    kontrol_izi_yolu = os.path.join(hedef, KONTROL_IZI)

    # ---- 4) KURU PROVA: hicbir sey SILINMEZ -------------------------------
    r3 = harness.izole_kos(o, "--sir-temizle", "--kuru-prova")
    iddia["(f) --kuru-prova HICBIR SEYI silmedi"] = all(
        os.path.exists(os.path.join(hedef, ad)) for ad in YERELI_OLAN + (YERELSIZ,))
    iddia["(g) --kuru-prova silinecekleri ADIYLA bastI"] = all(
        ad in r3.stdout for ad in YERELI_OLAN)

    # ---- 5) GERCEK TEMIZLIK: kok sirlari SILINIR, fail-closed kalem DURUR --
    r4 = harness.izole_kos(o, "--sir-temizle")
    iddia["(h) --sir-temizle yedek KOKUNDEKI sirlari SILDI"] = not any(
        os.path.exists(os.path.join(hedef, ad)) for ad in YERELI_OLAN)
    iddia["(i) FAIL-CLOSED: yerel asli olmayan kalem SILINMEDI"] = (
        os.path.exists(os.path.join(hedef, YERELSIZ)) and "SILINMEDI" in r4.stdout)
    iddia["(j) YEREL ASILLAR korundu + KONTROL IZI hedefte DURUYOR"] = (
        all(os.path.isfile(os.path.join(kok, ad)) for ad in YERELI_OLAN)
        and os.path.isfile(kontrol_izi_yolu))

    cokme = [k for k, r in (("1", r1), ("2", r2), ("3", r3), ("4", r4))
             if "Traceback" in r.stderr]
    return iddia, cokme, "".join(r.stdout for r in (r1, r2, r3, r4))


def mutant_yaz(dizin, degisimler, isaret):
    """yedekle.py'nin mutasyonlu kopyasi + CANLILIK ISARETI.
    Capa bulunamazsa RuntimeError -> bayat mutasyon capasi SESSIZCE gecmesin."""
    with open(YEDEKLE, encoding="utf-8") as f:
        kaynak = f.read()
    for eski, yeni in degisimler + [(ISARET_CAPA,
                                     '    print("MUTANT-ISARET: %s")\n' % isaret
                                     + ISARET_CAPA)]:
        if eski not in kaynak:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r"
                               % eski[:70])
        kaynak = kaynak.replace(eski, yeni, 1)
    hedef = os.path.join(dizin, "mutant-yedekle.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak)
    return hedef


# ===================== MUTASYON TARIFLERI ====================================
# Her mutant AYRI bir savunma katmanini oldurur; hicbiri "her degisiklik kirmizi"
# olmasin diye 1 KONTROL mutanti (davranisa DOKUNMAYAN metin degisikligi) YESIL
# kalmalidir — tek yonlu batarya "her duzenleme kirmizi" halini AYIRT EDEMEZ.
MUTANTLAR = [
    ("M1 ELEME OLDU (kok sir elemesi devre disi)", "M1", False, [
        ("        if kok_sir_adi_mi(ad):\n            elenen.append(",
         "        if False:  # MUTANT\n            elenen.append(")]),
    ("M2 KANONIK KUME DARALDI (REPO_SIR dusuruldu)", "M2", False, [
        ("    return frozenset(a.lower() for a in tuple(REPO_SIR) + tuple(SIR_ADLARI))",
         "    return frozenset(a.lower() for a in tuple(SIR_ADLARI))  # MUTANT")]),
    ("M3 TEMIZLIK KOKE ULASMIYOR (eski kusur geri geldi)", "M3", False, [
        ("    kok_sir_sayilari = yedek_kok_sir_raporu(backup, sir_temizle=sir_temizle)",
         "    kok_sir_sayilari = {}  # MUTANT")]),
    ("M4 KURU PROVA SILIYOR (prova sozlesmesi oldu)", "M4", False, [
        ("        if kuru_prova:\n            islenen.append((ad, hedef))",
         "        if False:  # MUTANT\n            islenen.append((ad, hedef))")]),
    ("M5 FAIL-CLOSED OLDU (yerel asil dogrulamasi atlandi)", "M5", False, [
        ('            cikti.append((giris, hedef, yerel, False,\n'
         '                          "yereldeki ASIL YOK (silinirse tek kopya gider)"))',
         '            cikti.append((giris, hedef, yerel, True, ""))  # MUTANT')]),
    # KONTROL — davranisi DEGISTIRMEZ, YESIL kalmali.
    ("C1 KONTROL (yalniz yorum metni degisti)", "C1", True, [
        ("# 🔴 KUME ELLE YAZILMAZ: eleme KANONIK kumeden TURER (REPO_SIR + SIR_ADLARI).",
         "# 🔴 KUME ELLE YAZILMAZ (KONTROL MUTANTI: yalniz bu yorum satiri degisti).")]),
]


def main():
    yedekle = modul_yukle(YEDEKLE, "yedekle_sir")
    harness = modul_yukle(YEDEKLE_TEST, "yedekle_test_harness")

    print("=" * 70)
    print("1) SAGLAM KOD — sir eleme + kok temizligi iddialari")
    with tempfile.TemporaryDirectory() as td:
        saglam, cokme, _c = senaryo(YEDEKLE, yedekle, harness, td)
    kontrol("saglam kosumlarin hicbiri COKMEDI", not cokme, "cokme: " + (
        ", ".join(cokme) or "yok"))
    for ad, ok in sorted(saglam.items()):
        kontrol(ad, ok)
    temel_yesil = {k for k, v in saglam.items() if v}

    if "--iddia" in sys.argv:
        return _rapor()

    print("\n2) MUTASYON — her savunma katmani TEK BASINA kirmiziya cevrilebiliyor mu?")
    dusenler = {}
    for baslik, isaret, kontrol_mu, degisimler in MUTANTLAR:
        with tempfile.TemporaryDirectory() as td:
            try:
                mutant = mutant_yaz(td, degisimler, isaret)
            except RuntimeError as e:
                kontrol(baslik + " — CAPA", False, str(e))
                continue
            m_iddia, m_cokme, m_cikti = senaryo(mutant, yedekle, harness, td)
        dusen = sorted(k for k in temel_yesil if not m_iddia.get(k, False))
        dusenler[isaret] = dusen
        # MUTASYON GERCEKTEN KOSTU MU: kirmizi/yesil hukmu ancak KOSAN mutant icin
        # anlamlidir; yuklenmemis mutant "yesil" der ve kontrol mutantini SAHTE
        # dogrular ([[mutasyon-bytecode-onbellegi]]).
        kontrol(baslik + " — MUTASYON KOSAN BETIKTE CANLI",
                ("MUTANT-ISARET: " + isaret) in m_cikti, "isaret=" + isaret)
        # COKME KIRMIZI SAYILMAZ: cokmus mutant her iddiayi dusurur, bu bir kanit degil.
        kontrol(baslik + " — COKMEDI", not m_cokme, "cokme: " + (", ".join(m_cokme) or "yok"))
        if kontrol_mu:
            kontrol(baslik + " — YESIL KALDI (kontrol)", not dusen,
                    "dusen: " + (", ".join(dusen) or "yok"))
        else:
            kontrol(baslik + " — KIRMIZI (en az 1 iddia DUSTU)", bool(dusen),
                    "dusen %d: %s" % (len(dusen), " · ".join(d.split(" ")[0] for d in dusen)))

    oldurucu = [i for _b, i, k, _d in MUTANTLAR if not k and dusenler.get(i)]
    kontrol("OLDURUCU MUTANT SAYISI >= 3", len(oldurucu) >= 3,
            "%d/%d: %s" % (len(oldurucu), sum(1 for m in MUTANTLAR if not m[2]),
                           ", ".join(oldurucu)))
    kumeler = {i: tuple(d) for i, d in dusenler.items() if d}
    esit = [(a, b) for a in kumeler for b in kumeler
            if a < b and kumeler[a] == kumeler[b]]
    kontrol("mutantlar AYIRT EDICI (ayni iddia kumesini dusuren cift yok)", not esit,
            "esit cift: " + (", ".join("%s=%s" % c for c in esit) or "yok"))

    print("\n3) KORELME KONTROLU — mutasyondan SONRA saglam kod yine tam yesil mi?")
    with tempfile.TemporaryDirectory() as td:
        tekrar, _c, _o = senaryo(YEDEKLE, yedekle, harness, td)
    kontrol("KORELME YOK: saglam kod tekrar TAM YESIL", all(tekrar.values()),
            "%d/%d iddia" % (sum(1 for v in tekrar.values() if v), len(tekrar)))
    return _rapor()


def _rapor():
    kirmizi = [ad for ad, ok, _a in SONUC if not ok]
    print("\n" + "=" * 70)
    print("TOPLAM %d kontrol, %d kirmizi" % (len(SONUC), len(kirmizi)))
    for ad in kirmizi:
        print("  ❌ " + ad)
    print("SONUC: " + ("KIRMIZI 🔴" if kirmizi else "YESIL ✅"))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
