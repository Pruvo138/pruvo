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
# 🔴 CAPRAZ DUZLEM: enforcement `~/.claude/cron/` duzlemindedir (git DISI) ve
# CI'da o dizin YOKTUR -> jeton ITHAL EDILEMEZ, ikinci literal KACINILMAZDIR.
# Ama SESSIZ KALMAZ: `tools/nobet-uc-kol-kabul.py` B22 vakasi iki duzlemin
# jetonunu KIYASLAR ve ayrisirsa KIRMIZI yanar.
KOL_KAPALI_JETONU = "LLM_KOLU_KAPALI"
# 🔴 TEK ALAN, TEK OKUMA YOLU (mimar sarti ③): hal `ci-nobeti.log`'daki
# `kol_hali=` alanindan okunur. Govde log satirindan `HUKUM=` greplemek
# IKINCI yoldu ve BIRAKILDI — iki okuma yolu sessizce ayrisir.
KOL_ALANI = "kol_hali="
KOL_KAPALI_IZI = KOL_ALANI + KOL_KAPALI_JETONU
KOL_ACIK_IZI = KOL_ALANI + "ACIK"
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

    Hal DIZGEDEN degil DAVRANISTAN okunur: govde bir turu REDDETTIGINDE loga
    `kol_hali=LLM_KOLU_KAPALI` yazar, bir tur ACILDIGINDA `kol_hali=ACIK` duser.
    Son soz LOGDAKI SON KANITTIR — kol yeniden acilirsa hal kendiliginden
    'ACIK'a doner; tek yonlu kilit URETILMEZ.

    🔴 KANIT YOKSA 'ACIK' DENMEZ. Bu araci Okan terminale girmeden hat sormak
    icin kullaniyor; hicbir markor ESLESMIYORSA arac KENDINDEN EMIN VE YANLIS
    bir sey soylemez, `OLCULEMEDI` basar.
    """
    if not os.path.exists(CINOBETI):
        return "OLCULEMEDI"
    son_red = son_acilis = -1
    try:
        with open(CINOBETI, "r", encoding="utf-8", errors="replace") as f:
            for i, satir in enumerate(f):
                if KOL_KAPALI_IZI in satir:
                    son_red = i
                if KOL_ACIK_IZI in satir:
                    son_acilis = i
    except OSError:
        return "OLCULEMEDI"
    if son_red < 0 and son_acilis < 0:
        return "OLCULEMEDI"
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
        # 🔴 Hal OLCULEMEDIYSE sayi da basilmaz: "0" bir CEVAPTIR, bilmedigimiz
        # yerde cevap vermeyiz.
        "ONARIM": ("KAPALI" if kol == "KAPALI"
                   else ("OLCULEMEDI" if kol == "OLCULEMEDI" else acilan)),
        "KOL": kol,
        "ACILAN_TARIHSEL": acilan,
        # SAYAC yalniz yeni alani saysin; eski `LLM_KOLU=KAPALI` yazisi artik
        # gelmiyor (gecis penceresi kapandi) ve yalniz yeni iz birakilir.
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
    # 🔴 UCUNCU HAL'IN KARDESI: hal OLCULEMEDI. 'ACIK' DEMEK YASAK — bu arac
    # Okan'a hat durumu soyluyor; emin olmadigi yerde emin konusmaz.
    if sayilar.get("KOL") == "OLCULEMEDI":
        return ("LLM tur kolunun hali OLCULEMEDI (logda markor YOK). "
                "Hal hakkinda hukum VERMIYORUM: olculemeyen hal, yanlis "
                "cevaba cevrilemez.", RC_ACMADI)
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
            "TETIK_HUKMU ... kol_hali=%s" % KOL_KAPALI_JETONU,
            "TETIK_HUKMU ... kol_hali=%s" % KOL_KAPALI_JETONU,
        ])
        # ACIK-yeniden: red ONCE, acilis SONRA -> hal kendiliginden ACIK'a doner
        yeniden_y = _log_yaz("yeniden.log", [
            "TETIK_HUKMU ... kol_hali=%s" % KOL_KAPALI_JETONU,
            "TETIK_HUKMU tetik_rc=0 acilan_tur=1 nobet_rc=0 hukum=TEMIZ kol_hali=ACIK",
        ])
        # ACIK ama tur acilmamis: kol=ACIK, acilan_tur=0 YOK (D10 vakasi)
        acik_y = _log_yaz("acik.log", [
            "TETIK_HUKMU tetik_rc=10 acilan_tur=0 nobet_rc=KOSMADI hukum=TEMIZ "
            "tetik_karari=ACMA kol_hali=ACIK",
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

        s3, (m3, rc3) = _olc_ile(acik_y)

        # 🔴 D5/D6 — BIRIM DUZEYI. `D10` ayni kolu FIKSTURLE olcer; bu ikisi
        # `huküm()`u DOGRUDAN cagirir ve kolun IKI YONUNU birden civiler:
        # kirmizi VARKEN cumle DENIR, kirmizi YOKKEN DENMEZ. Tek yon olculurse
        # "her halde ayni cumleyi basan" bir gerileme GORUNMEZ.
        m5, rc5 = huküm({"KOL": "ACIK", "ONARIM": "0", "KIRMIZI": "2"})
        olcvaka("D5 birim: kol ACIK + tur 0 + kirmizi VAR -> rc=1 + cumle",
                (RC_ACMADI, True), (rc5, YANLIS_OKUMA in m5))
        m6, rc6 = huküm({"KOL": "ACIK", "ONARIM": "0", "KIRMIZI": "0"})
        olcvaka("D6 KONTROL kirmizi YOKKEN cumle DENMEZ",
                (RC_ACMADI, False), (rc6, YANLIS_OKUMA in m6), kontrol=True)

        s4, (_m4, rc4) = _olc_ile(yok_y)
        olcvaka("D7 KONTROL log YOK -> OLCULEMEDI rc=1",
                ("OLCULEMEDI", "OLCULEMEDI", RC_ACMADI),
                (s4["ONARIM"], s4["KOL"], rc4), kontrol=True)

        kanitsiz_y = _log_yaz("kanitsiz.log", [
            "TETIK_HUKMU tetik_rc=10 acilan_tur=0 nobet_rc=KOSMADI hukum=TEMIZ",
            "=== 2026-08-28T21:07:00Z BITIS rc=0 ===",
        ])
        s8, (m8, rc8) = _olc_ile(kanitsiz_y)
        olcvaka("D8 kanit YOK -> OLCULEMEDI, 'ACIK' DENMEZ",
                ("OLCULEMEDI", "OLCULEMEDI", RC_ACMADI),
                (s8["ONARIM"], s8["KOL"], rc8))
        olcvaka("D8b mesaj 'ACIK' IDDIA ETMEZ", False, "ACIK" in m8)

        yeni_jeton_y = _log_yaz("yenijeton.log", [
            "TETIK_HUKMU tetik_rc=10 acilan_tur=0 nobet_rc=KOSMADI hukum=TEMIZ "
            "tetik_karari=ACMA kol_hali=%s" % KOL_KAPALI_JETONU,
        ])
        s9, (_m9, rc9) = _olc_ile(yeni_jeton_y)
        olcvaka("D9 KONTROL yeni jeton markoru taninir",
                ("KAPALI", RC_KOL_KAPALI), (s9["KOL"], rc9), kontrol=True)

        # 🔴 D10 artik `kol_hali=ACIK` vakasi: `acik_y` -> kol=ACIK,
        # `ONARIM="0"` (log'da `acilan_tur=1` YOK) -> rc=1 + YANLIS_OKUMA
        # cumlesi. Eski hal (D5/D6 huküm() dogrudan cagrisi) BIRAKILDI: ayni
        # kol AYNI ANDA iki duzeyle (donus metni + fikstur) olculuyor.
        olcvaka("D10 KONTROL kol ACIK + tur 0 -> bakiyor-onarmiyor",
                (RC_ACMADI, "ACIK", "0", True),
                (rc3, s3["KOL"], s3["ONARIM"], YANLIS_OKUMA in m3),
                kontrol=True)

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
            mut.CINOBETI = kanitsiz_y
            k_s = mut.olc()
            _k_mesaj, k_rc = mut.huküm(k_s)
            mut.CINOBETI = yok_y
            y_s = mut.olc()
            _y_mesaj, y_rc = mut.huküm(y_s)
            # 🔴 UCUNCU HAL/kanit-yoksa-ACIK kapilari (`if son_red < 0 and
            # son_acilis < 0: return "OLCULEMEDI"`) `son_red > son_acilis`
            # satirindan ONCE geldigi icin mutant yalniz KAPALI/ACIK
            # ayrimini oldurur — "kanit YOK -> OLCULEMEDI" davranisi iki
            # kontrolde de AYNI kalir.
            kontrol_yesil = (k_s["ONARIM"] == "OLCULEMEDI" and k_rc == RC_ACMADI
                             and y_s["ONARIM"] == "OLCULEMEDI" and y_rc == RC_ACMADI)
            mutant_atif = mutant_oldu and kontrol_yesil
            mutant_not = "oldurdugu=%s (D1,D2) kontrol_yesil=%s" % (
                HEDEF_KOL, kontrol_yesil)
        print("MUTANT %-26s %s ATIF=%s %s" % (
            MUTANT_ADI, "OLDU" if mutant_oldu else "YASADI",
            "EVET" if mutant_atif else "HAYIR", mutant_not))

        # --- MUTANT 2: kanit-yoksa-ACIK-der --------------------------------
        # CAPA parcaciklara bolunmus (kaynakta bitisik GECMEZ, calisma aninda
        # AYNI dizgeyi verir — [[kurucu-capa-yeni-icinde-cogaltir]]).
        CAPA2 = "    if son_red < 0 and " + "son_acilis < 0:"
        MUTANT_ADI2 = "M-OD2-kanit-yoksa-acik-der"
        HEDEF_KOL2 = "KANIT_YOKSA_OLCULEMEDI"
        mutant2_oldu = mutant2_atif = False
        if kaynak.count(CAPA2) != 1:
            mutant2_not = "CAPA_SAYISI=%d" % kaynak.count(CAPA2)
        else:
            kopya2 = os.path.join(kok, "onarim_durum_mutant2.py")
            with open(kopya2, "w", encoding="utf-8") as d:
                d.write(kaynak.replace(CAPA2, "    if False:", 1))
            spec2 = importlib.util.spec_from_file_location(
                "onarim_durum_mutant2", kopya2)
            mut2 = importlib.util.module_from_spec(spec2)
            onceki2 = sys.dont_write_bytecode
            sys.dont_write_bytecode = True
            try:
                spec2.loader.exec_module(mut2)
            finally:
                sys.dont_write_bytecode = onceki2
            mut2.CINOBETI, mut2.GOZCU = kanitsiz_y, gozcu_y
            m2_s = mut2.olc()
            _m2_mesaj, _m2_rc = mut2.huküm(m2_s)
            # HEDEF: D8 olmeli (mutantta kanitsiz log -> kol=ACIK, ONARIM=0;
            # original OLCULEMEDI basar, mutant ACIK der -> kirmizi)
            mutant2_oldu = (m2_s["ONARIM"] != "OLCULEMEDI"
                            and m2_s["KOL"] != "OLCULEMEDI")
            mut2.CINOBETI = yeni_jeton_y
            d9_s = mut2.olc()
            _, d9_rc = mut2.huküm(d9_s)
            mut2.CINOBETI = kapali_y
            d10_s = mut2.olc()
            _, d10_rc = mut2.huküm(d10_s)
            mut2.CINOBETI = yok_y
            d7_s = mut2.olc()
            _, d7_rc = mut2.huküm(d7_s)
            kontrol2_yesil = (d9_s["KOL"] == "KAPALI" and d9_rc == RC_KOL_KAPALI
                              and d10_s["KOL"] == "KAPALI" and d10_rc == RC_KOL_KAPALI
                              and d7_s["KOL"] == "OLCULEMEDI" and d7_rc == RC_ACMADI)
            mutant2_atif = mutant2_oldu and kontrol2_yesil
            mutant2_not = "oldurdugu=%s (D8) kontrol_yesil=%s" % (
                HEDEF_KOL2, kontrol2_yesil)
        print("MUTANT %-26s %s ATIF=%s %s" % (
            MUTANT_ADI2, "OLDU" if mutant2_oldu else "YASADI",
            "EVET" if mutant2_atif else "HAYIR", mutant2_not))

        toplam_mutant_oldu = (1 if mutant_oldu else 0) + (1 if mutant2_oldu else 0)
        toplam_mutant_atif = (1 if mutant_atif else 0) + (1 if mutant2_atif else 0)
        print("OD-KENDINI-TEST VAKA=%d/%d DUSEN=%d MUTANT=%d/2 ATIF=%d/2 "
              "KONTROL=%d/%d"
              % (sayac["gecen"], sayac["vaka"], len(dusenler),
                 toplam_mutant_oldu, toplam_mutant_atif,
                 sayac["kontrol_gecen"], sayac["kontrol"]))
        return 0 if (not dusenler and mutant_atif and mutant2_atif) else 1
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
