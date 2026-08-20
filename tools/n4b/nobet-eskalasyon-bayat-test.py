#!/usr/bin/env python3
"""B4 KABUL BATARYASI — EMEKLI motora eskale kalem CANLI kata gociyor mu?

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B4.
KANONIK KAYNAK: pruvo deposu `tools/n4b/nobet-eskalasyon-bayat-test.py`.

KOSUM:  python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
KABUL:  son satir `KABUL=GECTI (n/n vaka)` ve rc=0.
CAGRI YERI: `testler.py` PAKETLER listesi.

OLCULEN KABUL MADDELERI
  1) Pozitif: motor=deepseek-pro + ESKALASYON -> goc VAR, kalem fanout
     havuzuna girer (DAGITILACAK>=1) ve logda `ESKALASYON_BAYAT` satiri  -> D1/D3
  2) Negatif: motor CANLI + ESKALASYON -> gocmez, DAGITILMAZ
     (orijinal invaryant korunur, sonsuz dongu ACILMAZ)                  -> D2/D3
  3) Mutant A (kapsam): canli kume BOS -> HICBIR SEY gocmez, OLCULEMEDI  -> D4/R3
  4) Mutant B (sayac durustlugu): goc yolu sayaci sifirlarsa KIRMIZI     -> D5/R4
  5) Her mutantin hedef kolu oldugu AYRI olculur, yan eksen YESIL        -> R1..R4
  6) `gozcu-eskalasyon.md` SILINMEZ/TEMIZLENMEZ — kanittir               -> D6
"""

import ast
import importlib.util
import json
import os
import shutil
import sys
import tempfile

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
ESKALASYON_MD = os.path.join(CRON_KOKU, "gozcu-eskalasyon.md")
SAYAC_JSON = os.path.join(CRON_KOKU, "nobet-onarimsiz-sayac.json")

EMEKLI = "deepseek-pro"
VAKALAR = []


def vaka(vid, beklenen, olculen):
    gecti = (str(beklenen) == str(olculen))
    VAKALAR.append((vid, beklenen, olculen, gecti))
    print("VAKA=%-34s BEKLENEN=%-22s OLCULEN=%-22s SONUC=%s"
          % (vid, beklenen, olculen, "GECTI" if gecti else "KALDI"))
    return gecti


def modul_yukle(yol, ad):
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


def _geri_iz(motor, durum="ESKALASYON", kalem_id="K55"):
    return {"tur_no": 6, "kalemler": {kalem_id: {
        "id": kalem_id, "durum": durum, "motor": motor, "kat": motor,
        "dagitim_sayisi": 3, "tur": 6, "etiket": "nobet-%s-t6" % kalem_id}}}


def _kalem(nk, kalem_id="K55", is_metni="mekanik toplu donusum isi"):
    return {"id": kalem_id, "tarih": "20 Agu", "kimden_kime": "KraL → MaCiT",
            "kime": "MaCiT", "is": is_metni, "durum_ham": nk.ONARIM_DURUMU,
            "durum": nk.ONARIM_DURUMU, "kanit_ham": "", "kabul": "", "satir_no": 1}


# ===========================================================================
# D1..D2 — BAYAT AYRIMI (saf)
# ===========================================================================

def bolum_d1(nk, ek=""):
    print("--- BOLUM D1%s: BAYAT AYRIMI (saf) ---" % ek)
    canli = tuple(nk.CANLI_ISCI_MOTORLARI)
    vaka("D0-canli-kume-dolu%s" % ek, "dolu", "dolu" if canli else "BOS")

    gi = _geri_iz(EMEKLI)
    vaka("D1a-emekli-bayat%s" % ek, True,
         nk.eskalasyon_bayat_mi(gi["kalemler"]["K55"], canli))
    satirlar, sayi = nk.bayat_eskalasyonlari_gocur(gi, damga="D", canli_motorlar=canli)
    kayit = gi["kalemler"]["K55"]
    vaka("D1b-goc-sayisi%s" % ek, 1, sayi)
    vaka("D1c-yeni-durum%s" % ek, "BAYAT_GOC", kayit.get("durum"))
    vaka("D1d-yeni-kat-canli%s" % ek, "CANLI",
         "CANLI" if kayit.get("motor") in canli else kayit.get("motor"))
    vaka("D1e-log-satiri%s" % ek, "VAR",
         "VAR" if satirlar and satirlar[0].startswith(
             "ESKALASYON_BAYAT kalem=K55 eski_motor=%s" % EMEKLI) else str(satirlar))
    # KANIT SILINMEZ: eski durum/motor SAKLANIR, dagitim_sayisi AYNEN kalir.
    vaka("D1f-kanit-saklandi%s" % ek, "%s/ESKALASYON" % EMEKLI,
         "%s/%s" % ((kayit.get("eskalasyon_bayat") or {}).get("eski_motor"),
                    (kayit.get("eskalasyon_bayat") or {}).get("eski_durum")))
    vaka("D1g-dagitim-sayisi-korundu%s" % ek, 3, kayit.get("dagitim_sayisi"))
    # GOC BIR KEZ olur.
    _, sayi2 = nk.bayat_eskalasyonlari_gocur(gi, damga="D", canli_motorlar=canli)
    vaka("D1h-goc-tekrar-etmez%s" % ek, 0, sayi2)

    # D2 — NEGATIF: motor CANLI ise gocmez.
    gi2 = _geri_iz(canli[0] if canli else "kimi")
    vaka("D2a-canli-bayat-degil%s" % ek, False,
         nk.eskalasyon_bayat_mi(gi2["kalemler"]["K55"], canli))
    _, sayi3 = nk.bayat_eskalasyonlari_gocur(gi2, damga="D", canli_motorlar=canli)
    vaka("D2b-canli-gocmez%s" % ek, 0, sayi3)
    vaka("D2c-durum-degismedi%s" % ek, "ESKALASYON",
         gi2["kalemler"]["K55"].get("durum"))

    # Insan katlari kapsam DISI.
    gi3 = _geri_iz(nk.KAT_MIMAR)
    vaka("D2d-mimar-kati-gocmez%s" % ek, False,
         nk.eskalasyon_bayat_mi(gi3["kalemler"]["K55"], canli))


# ===========================================================================
# D3 — FANOUT EKSENI: goc kalemi ADAY HAVUZUNA sokuyor mu?
# ===========================================================================

def bolum_d3(nk, ek=""):
    print("--- BOLUM D3%s: FANOUT HAVUZU ---" % ek)
    canli = tuple(nk.CANLI_ISCI_MOTORLARI)
    kalemler = [_kalem(nk)]

    gi = _geri_iz(EMEKLI)
    plan_once = nk.fanout_plani(kalemler, gi, nk.FANOUT_TAVANI)
    vaka("D3a-goc-oncesi-dagitilmaz%s" % ek, 0,
         len(plan_once["dagitilacak"]))

    nk.bayat_eskalasyonlari_gocur(gi, damga="D", canli_motorlar=canli)
    plan_sonra = nk.fanout_plani(kalemler, gi, nk.FANOUT_TAVANI)
    vaka("D3b-goc-sonrasi-dagitilir%s" % ek, 1,
         len(plan_sonra["dagitilacak"]))
    vaka("D3c-eskale-listesinden-cikti%s" % ek, "[]",
         str(nk.eskale_kalemler(gi)))

    # NEGATIF: canli motorlu eskalasyon havuzda KALMAZ (invaryant korunur).
    gi2 = _geri_iz(canli[0] if canli else "kimi")
    nk.bayat_eskalasyonlari_gocur(gi2, damga="D", canli_motorlar=canli)
    plan2 = nk.fanout_plani(kalemler, gi2, nk.FANOUT_TAVANI)
    vaka("D3d-canli-eskale-dagitilmaz%s" % ek, 0, len(plan2["dagitilacak"]))


# ===========================================================================
# D4..D6 — FAIL-CLOSED, SAYAC DURUSTLUGU, KANIT DOSYASI
# ===========================================================================

def bolum_d4(nk, kaynak, tmp, ek=""):
    print("--- BOLUM D4%s: FAIL-CLOSED + SAYAC + KANIT ---" % ek)

    # D4 — canli kume BOS: HICBIR SEY gocmez, hukum OLCULEMEDI (MUTANT A).
    gi = _geri_iz(EMEKLI)
    satirlar, sayi = nk.bayat_eskalasyonlari_gocur(gi, damga="D",
                                                   canli_motorlar=())
    vaka("D4a-bos-kume-goc-yok%s" % ek, 0, sayi)
    vaka("D4b-bos-kume-durum-korundu%s" % ek, "ESKALASYON",
         gi["kalemler"]["K55"].get("durum"))
    vaka("D4c-bos-kume-olculemedi%s" % ek, "VAR",
         "VAR" if satirlar and "OLCULEMEDI" in satirlar[0] else str(satirlar))

    # D5 — SAYAC DURUSTLUGU (MUTANT B), IKI eksen:
    #  (a) KAYNAK: goc govdesinde sayac adi GECMEZ. 🔴 Govde OLCULEN MODULUN
    #      kaynagindan alinir; gercek dosyadan okunsaydi mutant kaynagi hic
    #      olculmez ve R4 "yasadi" gorunurdu.
    #  (b) DISK: goc yolu sayac dosyasini OLUSTURMAZ. Yol GECICI bir dosyaya
    #      cevrilir — mutant uretim sayacina yazmasin.
    # 🔴 Metin araması DEGIL CAGRI aramasi: govdenin DOCSTRING'i "sayaca
    # DOKUNMAZ" cumlesini tasidigi icin duz `in` testi kendi yorumuna takilip
    # KIRMIZI yaniyordu (olculdu: b4-kanit/06, K0 kontrol mutanti D5a).
    vaka("D5a-govde-sayaca-dokunmuyor%s" % ek, "YOK",
         "VAR" if _sayac_cagrisi_var(kaynak, "bayat_eskalasyonlari_gocur")
         else "YOK")

    sahte_sayac = os.path.join(tmp, "sayac%s.json" % ek)
    asil_yol = nk.ONARIMSIZ_SAYAC_YOLU
    nk.ONARIMSIZ_SAYAC_YOLU = sahte_sayac
    try:
        nk.bayat_eskalasyonlari_gocur(
            _geri_iz(EMEKLI), damga="D",
            canli_motorlar=tuple(nk.CANLI_ISCI_MOTORLARI))
    finally:
        nk.ONARIMSIZ_SAYAC_YOLU = asil_yol
    vaka("D5b-sayac-dosyasi-yazilmadi%s" % ek, "YOK",
         "VAR" if os.path.exists(sahte_sayac) else "YOK")

    # D6 — KANIT DOSYASI: gozcu-eskalasyon.md'ye DOKUNULMAZ (kabul-6).
    once_md = _dosya_imzasi(ESKALASYON_MD)
    nk.bayat_eskalasyonlari_gocur(_geri_iz(EMEKLI), damga="D",
                                  canli_motorlar=tuple(nk.CANLI_ISCI_MOTORLARI))
    vaka("D6-kanit-dosyasi-degismedi%s" % ek, once_md,
         _dosya_imzasi(ESKALASYON_MD))


SAYAC_ADLARI = ("ustuste_onarimsiz_guncelle", "ustuste_onarimsiz_oku",
                "ustuste_onarimsiz_sonraki", "tur_sayacini_kaydet")


def _sayac_cagrisi_var(kaynak, fonksiyon_adi):
    """Fonksiyonun govdesinde sayaca giden bir CAGRI var mi? (ast, yorum-bagisik)"""
    try:
        agac = ast.parse(kaynak)
    except SyntaxError:
        return True                      # ayristiramiyorsak fail-closed
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef)
                and dugum.name == fonksiyon_adi):
            continue
        for alt in ast.walk(dugum):
            if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name) \
                    and alt.func.id in SAYAC_ADLARI:
                return True
        return False
    return True                          # fonksiyon YOKSA fail-closed


def _dosya_imzasi(yol):
    try:
        durum = os.stat(yol)
        return "%d@%.0f" % (durum.st_size, durum.st_mtime)
    except OSError:
        return "YOK"


# ===========================================================================
# R — MUTANTLAR
# ===========================================================================

def sayim():
    return sum(1 for *_x, g in VAKALAR if g), len(VAKALAR)


def _atif(ad, isaret, hedef_onek, yan_onek):
    yeni = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    hedef = [v for v in yeni if any(v[0].startswith(o) for o in hedef_onek)]
    yan = [v for v in yeni if any(v[0].startswith(o) for o in yan_onek)]
    hedef_oldu = bool(hedef) and all(not v[3] for v in hedef)
    yan_yesil = bool(yan) and all(v[3] for v in yan)
    print("MUTANT=%-28s HEDEF_KOL=%-7s (%d vaka) YAN_EKSEN=%-8s (%d vaka)"
          % (ad, "OLDU" if hedef_oldu else "YASADI", len(hedef),
             "YESIL" if yan_yesil else "KIRMIZI", len(yan)))
    return hedef_oldu, yan_yesil


MUTASYON_UYGULANMADI = []


def mutant_kos(ad, kaynak, tmp, hedef_onek, yan_onek, taban=None):
    """Mutanti kosar. 🔴 Mutasyon HIC UYGULANMADIYSA bunu SESSIZ gecmez.

    Capa bayatlayinca `str.replace` hicbir sey degistirmez ve mutant "YASADI"
    gorunur — oysa gercek hukum OLCULEMEDI'dir
    ([[capa-cokmesi-arkasindaki-capalari-gizler]]). Olculdu (b4-kanit/06):
    R2 capasi satir-sonu yorumunu atlamis, mutasyon uygulanmamis, mutant
    "YASADI" diye raporlanmisti.
    """
    if taban is not None and kaynak == taban:
        MUTASYON_UYGULANMADI.append(ad)
        print("MUTANT=%-28s HEDEF_KOL=OLCULEMEDI (capa BAYAT: kaynak DEGISMEDI)"
              % ad)
        return False, False
    isaret = len(VAKALAR)
    yol = os.path.join(CRON_KOKU, ".b4-mutant-%s.py" % ad.split("-")[0].lower())
    try:
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(kaynak)
        mod = modul_yukle(yol, "b4_mutant_%s" % ad.split("-")[0].lower())
        # 🔴 Mutant URETIM sayacina YAZMASIN: R4 mutanti goc yolunda
        # `ustuste_onarimsiz_guncelle` cagirir ve varsayilan yol GERCEK
        # `nobet-onarimsiz-sayac.json`dur. Yol mutantin TUM kosumu boyunca
        # gecici dosyaya cevrilir ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).
        mod.ONARIMSIZ_SAYAC_YOLU = os.path.join(tmp, "mutant-sayac-%s.json" % ad)
        bolum_d1(mod, ek="-%s" % ad)
        bolum_d3(mod, ek="-%s" % ad)
        bolum_d4(mod, kaynak, tmp, ek="-%s" % ad)
    finally:
        try:
            os.remove(yol)
        except OSError:
            pass
    return _atif(ad, isaret, hedef_onek, yan_onek)


def bolum_r(kaynak, tmp):
    print("--- BOLUM R: MUTANTLAR ---")
    sonuclar = []

    # R1 — BAYAT KONTROLU KALDIRILDI: canli motorlu eskalasyon da gocer.
    r1 = kaynak.replace("    return motor not in canli\n",
                        "    return True\n", 1)
    sonuclar.append(("R1-bayat-kontrolu-yok",) + mutant_kos(
        "R1-bayat-kontrolu-yok", r1, tmp,
        ("D2a", "D2b", "D2c", "D3d"),
        ("D1a", "D1b", "D1c", "D1e", "D4", "D5", "D6"), taban=kaynak))

    # R2 — ESKALASYON KANITI SILINIYOR (kabul-6'nin kayit ekseni).
    # 🔴 NEDEN "goc TEKRAR EDER" MUTANTI DEGIL: D1h (goc bir kez olur) UC
    # BAGIMSIZ kalkanla saglaniyor — (a) `eskalasyon_bayat` damgasi,
    # (b) `durum` -> BAYAT_GOC, (c) `motor` -> CANLI kat. Herhangi ikisi
    # kaldirilsa ucuncusu D1h'i yine yesil tutuyor; olculdu: iki ayri denemede
    # mutant "YASADI" gorundu ve bu "kol saglam" DEGIL "bu vaka tek bir kolla
    # olculemiyor" demekti ([[ad-iki-rolde-mutanti-golgeler]]). D1h bu yuzden
    # ASIRI-BELIRLENMIS bir ozelliktir ve mutantla ayristirilmaz; onun yerine
    # AYIRT EDILEBILIR bir kol olculur: kanitin saklanmasi.
    r2 = kaynak.replace(
        '        kayit["eskalasyon_bayat"] = {\n'
        '            "eski_motor": eski_motor,\n'
        '            "eski_durum": kayit.get("durum"),\n'
        '            "damga": damga,\n'
        '        }\n', "", 1)
    sonuclar.append(("R2-kanit-silinir",) + mutant_kos(
        "R2-kanit-silinir", r2, tmp,
        ("D1f",),
        ("D1a", "D1b", "D1c", "D1d", "D1e", "D1g", "D1h", "D2", "D3",
         "D4", "D5", "D6"),
        taban=kaynak))

    # R3 — FAIL-CLOSED KALDIRILDI: bos kumede HEPSI bayat sayilir (MUTANT A).
    r3 = kaynak.replace(
        '    canli = CANLI_ISCI_MOTORLARI if canli_motorlar is None else tuple(canli_motorlar)\n'
        '    if not canli:\n'
        '        return ["ESKALASYON_BAYAT=OLCULEMEDI sebep=canli_motor_kumesi_bos"], 0\n',
        '    canli = CANLI_ISCI_MOTORLARI if canli_motorlar is None else tuple(canli_motorlar)\n'
        '    canli = canli or ("kimi",)\n', 1).replace(
        "    canli = CANLI_ISCI_MOTORLARI if canli_motorlar is None else tuple(canli_motorlar)\n"
        "    if not canli:\n        return False\n",
        "    canli = CANLI_ISCI_MOTORLARI if canli_motorlar is None else tuple(canli_motorlar)\n"
        '    canli = canli or ("kimi",)\n', 1)
    sonuclar.append(("R3-fail-closed-yok",) + mutant_kos(
        "R3-fail-closed-yok", r3, tmp,
        ("D4a", "D4b", "D4c"), ("D1", "D2", "D3", "D5", "D6"), taban=kaynak))

    # R4 — SAYAC DURUSTLUGU: goc yolu sayaci DOGRUDAN sifirliyor (MUTANT B).
    r4 = kaynak.replace(
        '        kayit["durum"] = BAYAT_GOC_DURUMU\n',
        '        kayit["durum"] = BAYAT_GOC_DURUMU\n'
        '        ustuste_onarimsiz_guncelle(1)\n', 1)
    sonuclar.append(("R4-sayac-sifirlaniyor",) + mutant_kos(
        "R4-sayac-sifirlaniyor", r4, tmp,
        ("D5a", "D5b"), ("D1", "D2", "D3", "D4", "D6"), taban=kaynak))

    # K0 — KONTROL: kaynak DEGISMEDEN ayni harness'ten gecer.
    isaret = len(VAKALAR)
    yol = os.path.join(CRON_KOKU, ".b4-mutant-k0.py")
    try:
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(kaynak)
        mod = modul_yukle(yol, "b4_mutant_k0")
        mod.ONARIMSIZ_SAYAC_YOLU = os.path.join(tmp, "mutant-sayac-K0.json")
        bolum_d1(mod, ek="-K0")
        bolum_d3(mod, ek="-K0")
        bolum_d4(mod, kaynak, tmp, ek="-K0")
    finally:
        try:
            os.remove(yol)
        except OSError:
            pass
    k0 = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    k0_yesil = all(v[3] for v in k0)
    print("MUTANT=%-28s HEDEF_KOL=%-7s (%d vaka)"
          % ("K0-kontrol", "YESIL" if k0_yesil else "KIRMIZI", len(k0)))
    return sonuclar, k0_yesil, len(k0)


# ===========================================================================

def main():
    try:
        with open(NOBET_KAPI, encoding="utf-8") as dosya:
            kaynak = dosya.read()
    except OSError as hata:
        print("KABUL=KALDI (nobet-kapi.py okunamadi: %s)" % hata)
        return 2
    nk = modul_yukle(NOBET_KAPI, "b4_nobet_kapi")
    if not hasattr(nk, "bayat_eskalasyonlari_gocur"):
        print("KABUL=KALDI (B4 yamasi KURULU DEGIL)")
        return 2
    if not nk.CANLI_ISCI_MOTORLARI:
        print("KABUL=OLCULEMEDI (CANLI_ISCI_MOTORLARI BOS — kapsam olculemez)")
        return 3

    tmp = tempfile.mkdtemp(prefix="b4-bayat-")
    try:
        bolum_d1(nk)
        bolum_d3(nk)
        bolum_d4(nk, kaynak, tmp)
        mutantlar, k0_yesil, k0_n = bolum_r(kaynak, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen, toplam = sayim()
    m_gecen = sum(1 for _, h, y in mutantlar if h and y)
    print("MUTANT=%d/%d  HEDEF_KOL_ATFI=%d/%d  KONTROL=%d/%d"
          % (m_gecen, len(mutantlar),
             sum(1 for _, h, _y in mutantlar if h), len(mutantlar),
             k0_n if k0_yesil else 0, k0_n))
    print("TOPLAM=%d GECTI=%d KALDI=%d" % (toplam, gecen, toplam - gecen))
    if MUTASYON_UYGULANMADI:
        print("KABUL=OLCULEMEDI (mutasyon capasi BAYAT: %s)"
              % ",".join(MUTASYON_UYGULANMADI))
        return 3
    if not k0_yesil:
        print("KABUL=OLCULEMEDI (K0 kontrol mutanti kirmizi — batarya kararsiz)")
        return 3
    if gecen == toplam and m_gecen == len(mutantlar):
        print("KABUL=GECTI (%d/%d vaka)" % (gecen, toplam))
        return 0
    print("KABUL=KALDI (%d/%d vaka, %d/%d mutant)"
          % (gecen, toplam, m_gecen, len(mutantlar)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
