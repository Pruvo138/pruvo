#!/usr/bin/env python3
"""Hattın onarım turu açıp açmadığını diskten okur.

ÜÇ sayıyı ölçer:
  ONARIM TURU       = ci-nobeti.log içinde "acilan_tur=1" geçen satır sayısı (TÜM dosya)
  KOL               = LLM tur kolunun HALI: KAPALI | ACIK | OLCULEMEDI
                      (KAPALI, "0" DEGILDIR — bkz. kol_hali())
  GOZCU TURU (bugün)= gozcu.log içinde BUGÜNÜN tarihi (YYYY-AA-GG) VE "GOZCU " geçen satır sayısı
  KIRMIZI GORULDU   = gozcu.log içinde BUGÜNÜN tarihi VE "YENI_KIRMIZI=1" geçen satır sayısı

BİLEREK ölçMEDİĞİ:
  - "onarim commit'i sayısı" ya da "son 24 saat commit" — bunlar cip/mimar işini de
    sayar ve halka çalışıyormuş izlenimi verir.
  - Tek dürüst ölçüt: otomatik hattın FİİLEN tur açıp açmadığı.

ONARIM TURU = 0 ise sistem onarım yapmıyor (kırmızı görülmemiş olsa bile
"calisiyor" kanıtı DEĞİLDİR — kırmızı yoksa o gün bir şey KIRILMAMIŞ olabilir,
ama hat da bakmamış olabilir).

Hiçbir dosyayı DEĞİŞTİRMEZ, ağa çıkmaz, LLM/agent turu açmaz. Salt okuma.

Kullanım:  python3 tools/onarim-durum.py
Kabul:     python3 tools/onarim-durum.py --kendini-test
Çıkış kodu: bkz. HÜKÜM tablosu.
"""

import datetime
import os
import sys

CINOBETI = os.path.expanduser("~/.claude/cron/ci-nobeti.log")
GOZCU = os.path.expanduser("~/.claude/cron/gozcu.log")
BUGUN = datetime.date.today().isoformat()

# 🔴 K347 (28 Agu 2026) — UCUNCU HAL AYRIDIR.
# Iki kovali sozluk ("tur acildi" / "acilmadi") ucuncu hali YUTAR: 28 Agu'da
# LLM tur-acma kolu Okan emriyle kapatildi -> `acilan_tur` alani YAPISAL OLARAK
# bir daha 1 olmayacak. Eski sayac o gunun sayisinda DONAR ve okuyan onu "hat
# onariyor" diye okur. `ONARIM=0` "acabilirdi, acmadi"; `ONARIM=KAPALI`
# "acmasi yapisal olarak IMKANSIZ" demektir — ikisi AYNI SEY DEGILDIR.
KOL_KAPALI_IZI = "LLM_KOLU=KAPALI"
TUR_ACILDI_IZI = "acilan_tur=1"

RC_ACTI = 0
RC_ACMADI = 1
RC_KOL_KAPALI = 2
RC_KULLANIM = 3

# 🔴 "Hat bakiyor, onarmiyor" bir HUKUM CUMLESIDIR ve YALNIZ bir halde dogrudur
# (kol ACIK, kirmizi VAR, tur ACILMAMIS). KAPALI halinde YANLIS okumadir. Cumle
# TEK YERDE yazilir: hem hukum onu KULLANIR, hem kabul onun YOKLUGUNU olcer —
# ikiz metin sessizce ayrismasin.
YANLIS_OKUMA = "Hat bakiyor, onarmiyor."


def kol_hali():
    """LLM tur kolunun HALI: 'KAPALI' | 'ACIK' | 'OLCULEMEDI'.

    Hal DIZGEDEN degil DAVRANISTAN okunur: govde (`nobet-kapi.py`) bir turu
    REDDETTIGINDE loga `LLM_KOLU=KAPALI` yazar. Son soz LOGDAKI SON KANITTIR
    — kol yeniden acilirsa (yeni bir `acilan_tur=1` dusunce) hal kendiliginden
    'ACIK'a doner; tek yonlu kilit URETILMEZ.
    """
    if not os.path.exists(CINOBETI):
        return "OLCULEMEDI"
    son_red = son_acilis = -1
    with open(CINOBETI, "r", encoding="utf-8", errors="replace") as f:
        for i, satir in enumerate(f):
            if KOL_KAPALI_IZI in satir:
                son_red = i
            if TUR_ACILDI_IZI in satir:
                son_acilis = i
    if son_red > son_acilis:
        return "KAPALI"
    return "ACIK"


def _say(dosya_yolu, kosul):
    """dosya_yolu yoksa 'OLCULEMEDI' yazar (0 yazmaz)."""
    if not os.path.exists(dosya_yolu):
        return "OLCULEMEDI"
    n = 0
    with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
        for satir in f:
            if kosul(satir):
                n += 1
    return str(n)


def olc():
    kol = kol_hali()
    acilan = _say(CINOBETI, lambda s: TUR_ACILDI_IZI in s)
    return {
        # 🔴 UCUNCU HAL: kol kapaliyken sayi BASILMAZ, HAL basilir.
        "ONARIM": "KAPALI" if kol == "KAPALI" else acilan,
        "KOL": kol,
        "ACILAN_TARIHSEL": acilan,
        "KOL_REDDI": _say(CINOBETI, lambda s: KOL_KAPALI_IZI in s),
        "GOZCU": _say(GOZCU, lambda s: BUGUN in s and "GOZCU " in s),
        "KIRMIZI": _say(GOZCU, lambda s: BUGUN in s and "YENI_KIRMIZI=1" in s),
    }


def huküm(sayilar):
    """Üç sayıdan hüküm basar.

    rc=0 → hat FIILEN tur acmis.
    rc=1 → acabilirdi ama acmadi, ya da olculemedi (kanit yok).
    rc=2 → KOL KAPALI: acmasi yapisal olarak imkansiz ('0' DEGILDIR).
    """
    # 🔴 UCUNCU HAL ONCE OKUNUR: kol kapaliyken "bakiyor, onarmiyor" okumasi
    # YANLIS olur — hat BAKAMAZ da, kolu YOK.
    if sayilar.get("KOL") == "KAPALI":
        return ("LLM tur kolu KAPALI (Okan emri, 28 Agu) — hat tur ACAMAZ. "
                "Bu hal '0' DEGILDIR: kol YOK, ihmal YOK. Onarim gunluk "
                "TAMIRCI cipindedir.", RC_KOL_KAPALI)
    raw = sayilar["ONARIM"]
    try:
        onarim = int(raw)
    except ValueError:
        # OLCULEMEDI ya da beklenmedik string
        return ("ONARIM TURU sayilamadi (log yok/okunamadi).", RC_ACMADI)
    try:
        kirmizi = int(sayilar["KIRMIZI"])
    except ValueError:
        kirmizi = 0
    if onarim > 0:
        return ("hat FIILEN tur acmis.", RC_ACTI)
    if kirmizi > 0:
        return ("KIRMIZI GORULDU AMA TEK TUR ACILMADI. " + YANLIS_OKUMA, RC_ACMADI)
    return ("onarim turu YOK. (Kirmizi da gorulmedi; 'calisiyor' KANITI DEGILDIR.)", RC_ACMADI)


def _kendini_test():
    """K347 kabul bataryasi — fikstur log'lariyla UC HAL + hedef-kol atifli MUTANT."""
    import importlib.util
    import shutil
    import tempfile

    sayac = {"vaka": 0, "gecen": 0, "kontrol": 0, "kontrol_gecen": 0}
    dusenler = []

    def olcvaka(ad, beklenen, gozlenen, kontrol=False):
        sayac["vaka"] += 1
        if kontrol:
            sayac["kontrol"] += 1
        tamam = (beklenen == gozlenen)
        if tamam:
            sayac["gecen"] += 1
            if kontrol:
                sayac["kontrol_gecen"] += 1
        else:
            dusenler.append(ad)
            sys.stderr.write("[DUSTU] %s\n  beklenen=%r\n  gozlenen=%r\n"
                             % (ad, beklenen, gozlenen))
        print("VAKA %-46s %s%s" % (ad, "GECTI" if tamam else "DUSTU",
                                   " (KONTROL)" if kontrol else ""))
        return tamam

    kok = tempfile.mkdtemp(prefix="onarim-durum-test-")
    try:
        def _log_yaz(ad, satirlar):
            yol = os.path.join(kok, ad)
            with open(yol, "w", encoding="utf-8") as d:
                d.write("\n".join(satirlar) + "\n")
            return yol

        gozcu_y = _log_yaz("gozcu.log", [
            "%s GOZCU YENI_KIRMIZI=1" % BUGUN,
            "%s GOZCU YENI_KIRMIZI=1" % BUGUN,
        ])
        # KAPALI: once tur acilmis, SONRA govde reddetmis (bugunku canli sira)
        kapali_y = _log_yaz("kapali.log", [
            "TETIK_HUKMU tetik_rc=0 acilan_tur=1 nobet_rc=0 hukum=TEMIZ",
            "=== 2026-08-28T18:11:48Z BITIS rc=0 ===",
            "LLM_KOLU=KAPALI sebep=OKAN_EMRI_28AGU motor=minimax-m3",
            "LLM_KOLU=KAPALI sebep=OKAN_EMRI_28AGU motor=minimax-m3",
        ])
        # ACIK-yeniden: red ONCE, acilis SONRA -> hal kendiliginden ACIK'a doner
        yeniden_y = _log_yaz("yeniden.log", [
            "LLM_KOLU=KAPALI sebep=OKAN_EMRI_28AGU motor=minimax-m3",
            "TETIK_HUKMU tetik_rc=0 acilan_tur=1 nobet_rc=0 hukum=TEMIZ",
        ])
        # ACIK ama tur acilmamis: red YOK, acilis YOK
        acmadi_y = _log_yaz("acmadi.log", [
            "TETIK_HUKMU tetik_rc=11 acilan_tur=0 nobet_rc=KOSMADI hukum=X",
        ])
        yok_y = os.path.join(kok, "olmayan.log")

        def _olc_ile(cinobeti):
            eski_c, eski_g = globals()["CINOBETI"], globals()["GOZCU"]
            globals()["CINOBETI"] = cinobeti
            globals()["GOZCU"] = gozcu_y
            try:
                s = olc()
                return s, huküm(s)
            finally:
                globals()["CINOBETI"] = eski_c
                globals()["GOZCU"] = eski_g

        s1, (m1, rc1) = _olc_ile(kapali_y)
        olcvaka("D1 kol KAPALI -> ONARIM=KAPALI rc=2",
                ("KAPALI", "KAPALI", RC_KOL_KAPALI), (s1["ONARIM"], s1["KOL"], rc1))
        olcvaka("D2 KAPALI halinde YANLIS_OKUMA cumlesi DENMEZ",
                False, YANLIS_OKUMA in m1)
        olcvaka("D3 KAPALI halinde sayilar KAYBOLMAZ (ayrinta duser)",
                ("1", "2"), (s1["ACILAN_TARIHSEL"], s1["KOL_REDDI"]))

        s2, (_m2, rc2) = _olc_ile(yeniden_y)
        olcvaka("D4 KONTROL kol yeniden ACILDI -> sayi doner rc=0",
                ("1", "ACIK", RC_ACTI), (s2["ONARIM"], s2["KOL"], rc2), kontrol=True)

        s3, (m3, rc3) = _olc_ile(acmadi_y)
        olcvaka("D5 KONTROL acabilirdi acmadi -> 0 rc=1",
                ("0", "ACIK", RC_ACMADI), (s3["ONARIM"], s3["KOL"], rc3), kontrol=True)
        olcvaka("D6 KONTROL o halde YANLIS_OKUMA cumlesi DENIR",
                True, YANLIS_OKUMA in m3, kontrol=True)

        s4, (_m4, rc4) = _olc_ile(yok_y)
        olcvaka("D7 KONTROL log YOK -> OLCULEMEDI rc=1",
                ("OLCULEMEDI", "OLCULEMEDI", RC_ACMADI),
                (s4["ONARIM"], s4["KOL"], rc4), kontrol=True)

        # --- MUTANT: hal ayrimi kaldirilir -> DONMUS SAYI GERI GELIR --------
        # 🔴 CAPA KENDI METNINDE GECMEMELI: duz yazilinca `kaynak.count(CAPA)`
        # hem hedef satiri hem BU satiri sayar (=2) ve mutant HIC atesleyemez
        # ([[kurucu-capa-yeni-icinde-cogaltir]]). Parcalara bolunmus hali kaynakta
        # bitisik GECMEZ, calisma aninda AYNI dizgeyi verir.
        CAPA = "    if son_red > " + "son_acilis:"
        MUTANT_ADI = "M-OD1-hal-ayrimi-kalkar"
        HEDEF_KOL = "UCUNCU_HAL_KOLU"
        kaynak_yolu = os.path.abspath(__file__)
        with open(kaynak_yolu, encoding="utf-8") as d:
            kaynak = d.read()
        mutant_oldu = mutant_atif = False
        if kaynak.count(CAPA) != 1:
            mutant_not = "CAPA_SAYISI=%d" % kaynak.count(CAPA)
        else:
            kopya = os.path.join(kok, "onarim_durum_mutant.py")
            with open(kopya, "w", encoding="utf-8") as d:
                d.write(kaynak.replace(CAPA, "    if False:", 1))
            spec = importlib.util.spec_from_file_location("onarim_durum_mutant", kopya)
            mut = importlib.util.module_from_spec(spec)
            onceki = sys.dont_write_bytecode
            sys.dont_write_bytecode = True
            try:
                spec.loader.exec_module(mut)
            finally:
                sys.dont_write_bytecode = onceki
            mut.CINOBETI, mut.GOZCU = kapali_y, gozcu_y
            m_s = mut.olc()
            m_mesaj, m_rc = mut.huküm(m_s)
            # HEDEF: D1/D2 olmeli (donmus sayi + yanlis hukum geri gelir)
            mutant_oldu = (m_s["ONARIM"] == "1" and m_rc == 0
                           and YANLIS_OKUMA not in m_mesaj)
            mut.CINOBETI = acmadi_y
            k_s = mut.olc()
            _k_mesaj, k_rc = mut.huküm(k_s)
            mut.CINOBETI = yok_y
            y_s = mut.olc()
            _y_mesaj, y_rc = mut.huküm(y_s)
            kontrol_yesil = (k_s["ONARIM"] == "0" and k_rc == RC_ACMADI
                             and y_s["ONARIM"] == "OLCULEMEDI" and y_rc == RC_ACMADI)
            mutant_atif = mutant_oldu and kontrol_yesil
            mutant_not = "oldurdugu=%s (D1,D2) kontrol_yesil=%s" % (
                HEDEF_KOL, kontrol_yesil)
        print("MUTANT %-26s %s ATIF=%s %s" % (
            MUTANT_ADI, "OLDU" if mutant_oldu else "YASADI",
            "EVET" if mutant_atif else "HAYIR", mutant_not))

        print("OD-KENDINI-TEST VAKA=%d/%d DUSEN=%d MUTANT=%d/1 ATIF=%d/1 "
              "KONTROL=%d/%d"
              % (sayac["gecen"], sayac["vaka"], len(dusenler),
                 1 if mutant_oldu else 0, 1 if mutant_atif else 0,
                 sayac["kontrol_gecen"], sayac["kontrol"]))
        return 0 if (not dusenler and mutant_atif) else 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def main():
    argv = sys.argv[1:]
    # 🔴 BICIM KASITLIDIR, "sadelestirme" YAPMA: `serbest-kume-tekkaynak-test.py`
    # C5/C6 kollari aracin CLI'sini AST'ten cikarir ve YALNIZ iki bicimi okur —
    # `add_argument("--x", ...)` ve `"--x" ... sys.argv` KARSILASTIRMASI
    # (`durum.py` boyle yazar). `argv == ["--kendini-test"]` biciminde bayrak
    # nobetciye GORUNMEZ ve tabloya yazili gerekce "BAYAT" diye KIRMIZI yanar.
    # argparse KULLANILMAZ: argparse hatada rc=2 ile cikar, o kod burada
    # RC_KOL_KAPALI'dir — iki anlam CAKISIRDI.
    if "--kendini-test" in sys.argv[1:]:
        return _kendini_test()
    if argv:
        sys.stderr.write(
            "HATA: bu arac arguman ALMAZ (tek bayrak: --kendini-test).\n")
        return RC_KULLANIM
    sayilar = olc()
    print(
        "ONARIM={} GOZCU={} KIRMIZI={}".format(
            sayilar["ONARIM"], sayilar["GOZCU"], sayilar["KIRMIZI"]
        )
    )
    # AYRINTI satiri: hal degisince sayilar KAYBOLMAZ, ayri alanda durur.
    print(
        "AYRINTI: kol={} acilan_tur_tarihsel={} kol_reddi={}".format(
            sayilar["KOL"], sayilar["ACILAN_TARIHSEL"], sayilar["KOL_REDDI"]
        )
    )
    mesaj, rc = huküm(sayilar)
    print("HUKUM: {}".format(mesaj))
    return rc


if __name__ == "__main__":
    sys.exit(main())
