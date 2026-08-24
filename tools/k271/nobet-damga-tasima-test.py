#!/usr/bin/env python3
"""K271 KABUL BATARYASI — dagitim goc damgasini DUSURMEZ, goc TEKRARLAMAZ.

CHIP: KraL-K260KatSec.

🔴 KABUL IKI YONLU (tek yon KUTSANIR — bu kalemin ozu):
  A  Damga dagitimdan SONRA KORUNUR ve kalem dusup havuza donunce kovasi
     yine `DAGITILABILIR` olur.                       (yon 1)
  B  Damga korundugu HALDE goc BIR DAHA ATESLEMEZ — `eskalasyon_bayat_mi`
     damgali kaydi eler, sonsuz dongu YOK.            (yon 2)
  C  REGRESYON: `dagitim_sayisi` ve `merdiven` bugunku davranisini AYNEN
     korur; damga TASIMASI baska hicbir alani degistirmez.
  D  NEGATIF: damgasi OLMAYAN kayda damga UYDURULMAZ.

Yalniz A olculseydi "her zaman True donen" bir goc kolu de yesil yanardi;
yalniz B olculseydi damgayi hic tasimayan bugunku kod da yesil yanardi.

KOSUM
    python3 nobet-damga-tasima-test.py              # kabul
    python3 nobet-damga-tasima-test.py --mutasyon   # mutant + KONTROL
🔴 MUTASYON GECICI KOPYAYA; canli `nobet-kapi.py`ye ASLA.
"""

import argparse
import importlib.util
import os
import shutil
import sys
import tempfile

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
VAKALAR = []
_SAYAC = [0]


def vaka(vid, beklenen, olculen):
    gecti = (str(beklenen) == str(olculen))
    VAKALAR.append((vid, beklenen, olculen, gecti))
    print("VAKA=%-44s BEKLENEN=%-18s OLCULEN=%-18s SONUC=%s"
          % (vid, beklenen, olculen, "GECTI" if gecti else "KALDI"))
    return gecti


def modul_yukle(yol):
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    _SAYAC[0] += 1
    ad = "_k271_nk_%d" % _SAYAC[0]
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


# K86'nin GERCEK metninden alinmis parca (serbest metinde "mutasyon" geciyor,
# yani metin TEK BASINA kalemi MIMAR'a cikarir — kurtaran YAPISAL damgadir).
M_K86 = ("SERIT B'de UC mutasyon bataryasi ayni anda kapsam deligi bildiriyor; "
         "deploy'u bloklamiyor ama her push'ta Run failed maili uretiyor")
# Metni ZATEN canli kata cikan kalem — damgaya ihtiyaci YOKTUR. Damga
# UYDURULMADIGINI olcen vakalar bunu kullanir: MIMAR metinli bir kalem
# `kalem_dagit` tarafindan HAKLI OLARAK reddedilir (KAT_MIMAR dagitilamaz),
# o yuzden negatif kollar mekanik metinle kurulur.
M_MEKANIK = "tasima sayim log okuma temizlik isi; kopya yeniden yaz"


def _kalem(nk, kalem_id="K86", metin=M_K86, kime="KraL"):
    return {"id": kalem_id, "tarih": "24 Agu", "kimden_kime": "KraL → %s" % kime,
            "kime": kime, "is": metin, "durum_ham": nk.ONARIM_DURUMU,
            "durum": nk.ONARIM_DURUMU, "kanit_ham": "", "kabul": "",
            "satir_no": 1}


def _damgali_kayit(nk, kalem_id="K86", sayi=3, merdiven=True):
    kayit = {"id": kalem_id, "durum": "BAYAT_GOC",
             "motor": nk.CANLI_ISCI_MOTORLARI[-1],
             "kat": nk.CANLI_ISCI_MOTORLARI[-1],
             "dagitim_sayisi": sayi, "tur": 269,
             "eskalasyon_bayat": {"eski_motor": nk.EMEKLI_ISCI_MOTORLARI[0],
                                  "eski_durum": "ESKALASYON", "damga": "D0"}}
    if merdiven:
        kayit["merdiven"] = {"basamak": nk.CANLI_ISCI_MOTORLARI[0],
                             "denemeler": ["d1", "d2"]}
    return kayit


def _geri_iz(kayitlar):
    return {"tur_no": 700, "kalemler": {k["id"]: k for k in kayitlar}}


def _dagit(nk, kalem, geri_iz, tur=700, yeniden=False):
    """kalem_dagit'i GERCEK imzasiyla cagirir; isci BASLATILMAZ (sahte
    calistirici) — olculen sey KAYDIN kendisi, yan etki DEGIL."""
    return nk.kalem_dagit(kalem, tur, geri_iz,
                          calistirici=lambda komut, log: 424242,
                          yeniden=yeniden)


# ===========================================================================
# A — DAMGA DAGITIMDAN SONRA KORUNUR (yon 1)
# ===========================================================================

def bolum_a(nk, ek=""):
    print("--- BOLUM A%s: DAMGA KORUNUR ---" % ek)
    kalem = _kalem(nk)
    onceki = _damgali_kayit(nk)
    gi = _geri_iz([onceki])
    beklenen_damga = dict(onceki["eskalasyon_bayat"])

    # A0 — TABAN: dagitimdan ONCE kalem DAGITILABILIR kovasinda.
    vaka("A0-once-dagitilabilir%s" % ek, nk.KOVA_DAGITILABILIR,
         nk.kova_sec(kalem, gi))
    # A0b — metin TEK BASINA MIMAR'a cikiyor (kurtaran damga, metin degil).
    vaka("A0b-metin-tek-basina-mimar%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(kalem, None))

    kayit = _dagit(nk, kalem, gi)
    vaka("A1-damga-kayitta%s" % ek, "VAR",
         "VAR" if kayit.get("eskalasyon_bayat") else "YOK")
    vaka("A2-damga-BIREBIR%s" % ek, beklenen_damga,
         kayit.get("eskalasyon_bayat"))
    vaka("A3-geri-izde-de-var%s" % ek, "VAR",
         "VAR" if (gi["kalemler"]["K86"].get("eskalasyon_bayat")) else "YOK")

    # A4 — ASIL IDDIA: kalem DUSUP havuza donunce kovasi YINE DAGITILABILIR.
    gi["kalemler"]["K86"]["durum"] = "BITMEYEN_TUR"
    vaka("A4-dusunce-yine-dagitilabilir%s" % ek, nk.KOVA_DAGITILABILIR,
         nk.kova_sec(kalem, gi))
    # 🔴 Beklenti MOTOR ADINA CIVILENMEZ: `kalem_dagit` motoru yedek
    # zincirinden/`motor_ayakta`dan secer, yani dagitim sonrasi kaydin motoru
    # fikstürde yazdigimiz ad OLMAYABILIR (olculdu: kimi -> minimax-m3).
    # Anlamli degismez: kat, KAYDIN motoruna ESIT ve CANLI kumede.
    vaka("A4b-kat-kaydin-motoru%s" % ek, gi["kalemler"]["K86"]["motor"],
         nk.kat_sec(kalem, gi))
    vaka("A4c-kat-canli-kumede%s" % ek, True,
         nk.kat_sec(kalem, gi) in nk.CANLI_ISCI_MOTORLARI)


# ===========================================================================
# B — GOC BIR DAHA ATESLEMEZ (yon 2)
# ===========================================================================

def bolum_b(nk, ek=""):
    print("--- BOLUM B%s: GOC TEKRARLAMAZ ---" % ek)
    canli = tuple(nk.CANLI_ISCI_MOTORLARI)
    emekli = tuple(nk.EMEKLI_ISCI_MOTORLARI)

    # B1 — DAMGALI + ESKALASYON + emekli motor -> goc ATESLEMEZ.
    damgali = _damgali_kayit(nk)
    damgali["durum"] = "ESKALASYON"
    damgali["motor"] = emekli[0]
    vaka("B1-damgali-goc-etmez%s" % ek, False,
         nk.eskalasyon_bayat_mi(damgali, canli))
    gi = _geri_iz([damgali])
    _, sayi = nk.bayat_eskalasyonlari_gocur(gi, damga="D", canli_motorlar=canli)
    vaka("B2-damgali-goc-sayisi%s" % ek, 0, sayi)
    vaka("B2b-durum-degismedi%s" % ek, "ESKALASYON",
         gi["kalemler"]["K86"].get("durum"))

    # B3 — KONTROL KOLU: DAMGASIZ ayni kayit HALA gocer (kol OLU DEGIL).
    damgasiz = _damgali_kayit(nk)
    damgasiz.pop("eskalasyon_bayat")
    damgasiz["durum"] = "ESKALASYON"
    damgasiz["motor"] = emekli[0]
    vaka("B3-damgasiz-gocer%s" % ek, True,
         nk.eskalasyon_bayat_mi(damgasiz, canli))
    gi2 = _geri_iz([damgasiz])
    _, sayi2 = nk.bayat_eskalasyonlari_gocur(gi2, damga="D",
                                             canli_motorlar=canli)
    vaka("B3b-damgasiz-goc-sayisi%s" % ek, 1, sayi2)

    # B4 — UCTAN UCA: dagit -> damga korunur -> goc YINE atesleme.
    kalem = _kalem(nk)
    gi3 = _geri_iz([_damgali_kayit(nk)])
    _dagit(nk, kalem, gi3)
    gi3["kalemler"]["K86"]["durum"] = "ESKALASYON"
    gi3["kalemler"]["K86"]["motor"] = emekli[0]
    _, sayi3 = nk.bayat_eskalasyonlari_gocur(gi3, damga="D",
                                             canli_motorlar=canli)
    vaka("B4-dagitim-sonrasi-goc-yok%s" % ek, 0, sayi3)


# ===========================================================================
# C — REGRESYON: baska hicbir alan degismez
# ===========================================================================

def bolum_c(nk, ek=""):
    print("--- BOLUM C%s: REGRESYON ---" % ek)
    kalem = _kalem(nk)

    # C1 — dagitim_sayisi: gecmisi olan kalem 1'e DUSMEZ (K257(a)).
    gi = _geri_iz([_damgali_kayit(nk, sayi=3)])
    kayit = _dagit(nk, kalem, gi)
    vaka("C1-dagitim-sayisi%s" % ek, 4, kayit.get("dagitim_sayisi"))

    # C2 — merdiven gecmisi HALA tasiniyor (komsu kol bozulmadi).
    vaka("C2-merdiven-tasindi%s" % ek, "VAR",
         "VAR" if kayit.get("merdiven") else "YOK")
    vaka("C2b-merdiven-birebir%s" % ek,
         {"basamak": nk.CANLI_ISCI_MOTORLARI[0], "denemeler": ["d1", "d2"]},
         kayit.get("merdiven"))

    # C3 — durum/etiket/tur bugunku davranisla AYNI.
    vaka("C3-durum%s" % ek, "DAGITILDI", kayit.get("durum"))
    vaka("C3b-etiket%s" % ek, "nobet-K86-t700", kayit.get("etiket"))

    # C4 — gecmissiz kalem 1'den baslar (sayac SISMEZ). Metin MEKANIK: MIMAR
    # metinli kalemi `kalem_dagit` HAKLI OLARAK reddeder.
    kayit2 = _dagit(nk, _kalem(nk, "KZ9", M_MEKANIK), _geri_iz([]))
    vaka("C4-gecmissiz-sayi%s" % ek, 1, kayit2.get("dagitim_sayisi"))


# ===========================================================================
# D — NEGATIF: damga UYDURULMAZ
# ===========================================================================

def bolum_d(nk, ek=""):
    print("--- BOLUM D%s: DAMGA UYDURULMAZ ---" % ek)
    # D1 — onceki kayit DAMGASIZ ise yeni kayitta da damga OLMAZ.
    damgasiz = _damgali_kayit(nk, kalem_id="KZ1")
    damgasiz.pop("eskalasyon_bayat")
    gi = _geri_iz([damgasiz])
    kayit = _dagit(nk, _kalem(nk, "KZ1", M_MEKANIK), gi)
    vaka("D1-damgasiz-kalir%s" % ek, "YOK",
         "VAR" if kayit.get("eskalasyon_bayat") else "YOK")
    # D2 — hic gecmisi olmayan kalem de damgasiz.
    kayit2 = _dagit(nk, _kalem(nk, "KZ2", M_MEKANIK), _geri_iz([]))
    vaka("D2-gecmissiz-damgasiz%s" % ek, "YOK",
         "VAR" if kayit2.get("eskalasyon_bayat") else "YOK")
    # D3 — damgasiz + MIMAR metinli kalem dusunce MIMAR'da KALIR
    # (fail-closed korunuyor; damga UYDURULMADIGI icin kurtulmuyor).
    damgasiz3 = _damgali_kayit(nk, kalem_id="KZ3")
    damgasiz3.pop("eskalasyon_bayat")
    damgasiz3["durum"] = "BITMEYEN_TUR"
    vaka("D3-damgasiz-dusen-mimar%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(_kalem(nk, "KZ3"), _geri_iz([damgasiz3])))


# ===========================================================================
# MUTASYON
# ===========================================================================

MUTANTLAR = (
    ("M1_DAMGA_TASIMA_KALDIRILDI",
     '    if onceki.get("eskalasyon_bayat"):\n'
     '        kayit["eskalasyon_bayat"] = onceki["eskalasyon_bayat"]\n',
     "",
     ("A1-", "A2-", "A3-", "A4-", "A4b-", "B4-"), False),
    ("M2_GOC_ELEME_KOLU_KALDIRILDI",
     '    if kayit.get("eskalasyon_bayat"):\n        return False\n',
     "    if False:\n        return False\n",
     ("B1-", "B2-", "B2b-", "B4-"), False),
    ("M3_MERDIVEN_TASIMA_KALDIRILDI",
     '    if onceki.get("merdiven"):\n'
     '        kayit["merdiven"] = onceki["merdiven"]\n',
     "",
     ("C2-", "C2b-"), False),
    ("K0_KONTROL_ILGISIZ_KOL",
     '        "spec_yolu": spec_yolu,\n',
     '        "spec_yolu": spec_yolu, "k0_kontrol": 1,\n',
     (), True),
)


def _batarya(nk, ek):
    del VAKALAR[:]
    bolum_a(nk, ek)
    bolum_b(nk, ek)
    bolum_c(nk, ek)
    bolum_d(nk, ek)
    return list(VAKALAR)


def mutasyon():
    print("=== K271 MUTASYON BATARYASI (GECICI KOPYA) ===")
    taban_kaynak = open(NOBET_KAPI, encoding="utf-8").read()
    gecici = tempfile.mkdtemp(prefix="k271-mut-")
    try:
        taban_yol = os.path.join(gecici, "nk_taban.py")
        shutil.copy2(NOBET_KAPI, taban_yol)
        taban = _batarya(modul_yukle(taban_yol), "-taban")
        taban_dusen = [v[0] for v in taban if not v[3]]
        print("TABAN_IDDIA=%d TABAN_DUSEN=%d" % (len(taban), len(taban_dusen)))
        if taban_dusen:
            print("HARNESS=BAYAT dusen=%s" % ",".join(taban_dusen))
            print("HUKUM=OLCULEMEDI sebep=taban_kirmizi")
            return 2

        oldu = hedefli = 0
        kontrol_yesil = True
        for ad, eski, yeni, hedefler, kontrol_mu in MUTANTLAR:
            if taban_kaynak.count(eski) != 1:
                print("MUTANT=%-38s DURUM=CAPA_YOK sayi=%d (OLCULEMEDI)"
                      % (ad, taban_kaynak.count(eski)))
                continue
            yol = os.path.join(gecici, "nk_%s.py" % ad.lower())
            with open(yol, "w", encoding="utf-8") as d:
                d.write(taban_kaynak.replace(eski, yeni, 1))
            try:
                dusen = [v[0] for v in _batarya(modul_yukle(yol), "-" + ad)
                         if not v[3]]
            except Exception as hata:                      # noqa: BLE001
                dusen = ["YUKLENEMEDI:%s" % type(hata).__name__]
            if kontrol_mu:
                yesil = not dusen
                kontrol_yesil = kontrol_yesil and yesil
                print("MUTANT=%-38s KONTROL SONUC=%s dusen=%s"
                      % (ad, "YESIL" if yesil else "KIRMIZI",
                         ",".join(dusen) or "-"))
                continue
            hedef_dusen = [v for v in dusen
                           if any(v.startswith(h) for h in hedefler)]
            hedefli += 1
            oldu += 1 if hedef_dusen else 0
            print("MUTANT=%-38s SONUC=%s hedef_dusen=%s tum_dusen=%d"
                  % (ad, "OLDU" if hedef_dusen else "HAYATTA(OLCULEMEDI)",
                     ",".join(hedef_dusen) or "-", len(dusen)))
        print("MUTANT=%d/%d" % (oldu, hedefli))
        print("KONTROL=%s" % ("YESIL" if kontrol_yesil else "KIRMIZI"))
        print("HUKUM=%s" % ("YESIL" if oldu == hedefli and kontrol_yesil
                            else "KIRMIZI"))
        return 0 if (oldu == hedefli and kontrol_yesil) else 1
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
        print("TEMIZLIK=%s silindi" % gecici)


def kabul():
    print("=== K271 KABUL BATARYASI ===")
    sonuc = _batarya(modul_yukle(NOBET_KAPI), "")
    dusen = [v[0] for v in sonuc if not v[3]]
    print("IDDIA=%d GECTI=%d KALDI=%d"
          % (len(sonuc), len(sonuc) - len(dusen), len(dusen)))
    if dusen:
        print("KALAN=%s" % ",".join(dusen))
    print("HUKUM=%s" % ("YESIL" if not dusen else "KIRMIZI"))
    return 0 if not dusen else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="K271 damga tasima bataryasi")
    ap.add_argument("--mutasyon", action="store_true")
    args = ap.parse_args(argv)
    return mutasyon() if args.mutasyon else kabul()


if __name__ == "__main__":
    sys.exit(main())
