#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K257 KURUCU — eskalasyon merdivenini nobet hattina KABLOLAR.

KALEM: K257 (Okan, 20 Agu 2026) — m3(2) -> kimi(1) -> mimar(1) -> KraL ->
BaBa(SLA) -> Okan. Proza olan merdiveni SAYILAN kurala cevirir.
DUZLEM: ~/.claude/cron (git YOK) -> idempotent + yedekli.

🔴 KAPININ MENZILI CAGRI YERIDIR ([[kapinin-menzili-cagri-yeridir]]): bu betik
yalniz modulu KOPYALAMAZ, uretim kollarini da baglar. Kablolanmamis kapi
bir MESAJDIR, kapi degildir.

YAMALAR
  P0  modul kurulur                 -> ~/.claude/cron/nobet_merdiven.py
  P1  nobet-kapi.py modulu import eder
  P2  (e) TUR_MOTOR_ZINCIRI ELLE TUPLE degil, CANLI kumeden TURETILIR
  P3  `_kalemi_dusur` merdivenle karar verir (dort hal, uc ayri yon)
  P4a BEYAN_VAR_KANIT_YOK kolu  -> metin + rc gecirir (varsayilan YETENEK)
  P4b KOMUT_REDDEDILDI kolu     -> 🔴 KAPI_REDDI ZORLANIR (arac kusuru)
  P4c OLU ISCI kolu             -> varsayilan BITMEYEN_TUR (B7 kovasi)
  P4d YAS ESIGI kolu            -> varsayilan YETENEK
  P5  dagitilmayacak durumlar merdivenden TURER (ARAC_KUSURU / KOTA_BEKLEMEDE)
  P6  `kalem_dagit` SAYACI SIFIRLAMAZ + merdiven kaydini TASIR + basamaga dagitir
  P7  `tur_kapat` (d) SLA kolunu kosar ve merdiven satirlarini BASAR
  T1  kabul bataryasi kurulur
  T2  batarya `testler.py`'ye kaydedilir (CAGRI YERI)

KOSUM:
    python3 tools/k257/k257-kur.py                # yalniz OLCER
    python3 tools/k257/k257-kur.py --uygula
    python3 tools/k257/k257-kur.py --geri-al DAMGA
"""

import argparse
import os
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
TESTLER = os.path.join(CRON_KOKU, "testler.py")

KAYNAK_DIZIN = os.path.dirname(os.path.abspath(__file__))
MODUL_ADI = "nobet_merdiven.py"
TEST_ADI = "nobet-merdiven-test.py"
MODUL_HEDEF = os.path.join(CRON_KOKU, MODUL_ADI)
TEST_HEDEF = os.path.join(CRON_KOKU, TEST_ADI)
MODUL_KAYNAK = os.path.join(KAYNAK_DIZIN, MODUL_ADI)
TEST_KAYNAK = os.path.join(KAYNAK_DIZIN, TEST_ADI)

HEDEFLER = (NOBET_KAPI, TESTLER)
YEDEK_ONEK = "yedek-k257"


# ---------------------------------------------------------------------------
# P1 — import
# ---------------------------------------------------------------------------

P1_ESKI = """import kilit  # noqa: E402
sys.dont_write_bytecode = _eski_pyc
"""
P1_YENI = """import kilit  # noqa: E402
# K257: eskalasyon merdiveni (m3 2 · kimi 1 · MIMAR 1 · KRAL 1 · BABA SLA · OKAN).
import nobet_merdiven as MERDIVEN  # noqa: E402
sys.dont_write_bytecode = _eski_pyc
"""


# ---------------------------------------------------------------------------
# P2 — (e) IKINCI MOTOR LISTESI KALDIRILIR
# ---------------------------------------------------------------------------

P2_ESKI = """# H5: nobet TURUNUN motor zinciri (kota reddinde sirayla dusulur)
# 16 Agu 2026: BaBa hukmu (mimar posta kutusu) — "cron nobetleri Kimi'ye BAGLANMAZ"
# gerekcesi: Kimi haftalik LIMIT 5s/hafta, nobet tasarimi cok-turlu, limit baglayici.
TUR_MOTOR_ZINCIRI = ("minimax-m3",)
"""
P2_YENI = '''# H5: nobet TURUNUN motor zinciri (kota reddinde sirayla dusulur)
# 🔴 K257(e) — 20 Agu 2026, mimar hukmu. Burada ELLE YAZILMIS tekil bir tuple
# duruyordu (`("minimax-m3",)`) ve sira mutanti onu OLDURMUYORDU: hicbir seyden
# TUREMEDIGI icin degistirilmesi bir seyi bozmuyordu. Ikinci motor listesi
# TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]) — zincir CANLI kumeden turer.
# Bu satir 16 Agu BaBa notunun ("cron nobetleri Kimi'ye BAGLANMAZ") YERINE
# gecer: Okan'in 20 Agu motor karari (m3 BIRINCIL, kimi YEDEK) ve K257(b)'nin
# KOTA -> YANA hamlesi yedek motoru ACIKCA istiyor. Zincirin ILK elemani
# birincil kattir; kalani yalniz kota/karantina reddinde denenir.
TUR_MOTOR_ZINCIRI = tuple(CANLI_ISCI_MOTORLARI)
'''


# ---------------------------------------------------------------------------
# P3 — _kalemi_dusur MERDIVENLE karar verir
# ---------------------------------------------------------------------------

P3_ESKI = '''def _kalemi_dusur(kayit, kimlik, sonuc):
    """H4 eskalasyon merdiveni: 3. dagitimda hala kapanmadiysa Okan kapisi."""
    if int(kayit.get("dagitim_sayisi", 1)) >= ESKALASYON_DAGITIM:
        kayit["durum"] = "ESKALASYON"
        sonuc["eskalasyon"].append(kimlik)
    else:
        kayit["durum"] = "DUSTU"
        sonuc["dusen"].append(kimlik)
'''

P3_YENI = '''def _kalemi_dusur(kayit, kimlik, sonuc, hal=None, metin=None, rc=1,
                 varsayilan=None):
    """K257 MERDIVENI: dusmenin SINIFI yonu belirler (dort hal, UC ayri yon).

    Eskiden TEK esik vardi ("3. dagitimda Okan") ve HER dusme ayni kovaya
    giriyordu: kota reddi de, kapi reddi de, sure tavani da "yetenek yok"
    sayiliyordu. K236 aylarca "motor yetersiz" sanildi cunku KAPI_REDDI kolu
    YOKTU. Artik:
      KOTA         -> YANA     (m3 -> kimi), sayac ARTMAZ
      YETENEK      -> YUKARI   , sayac ARTAR
      BITMEYEN_TUR -> B7 KOVASI, ayni tur YENIDEN KURULMAZ
      KAPI_REDDI   -> SAHIBINE , NE YANA NE YUKARI (arac kusuru)
    """
    sinif = hal or MERDIVEN.hal_coz(
        rc, metin, kota_reddi_mi,
        varsayilan=varsayilan or MERDIVEN.HAL_YETENEK)
    if sinif is None:                       # rc=0 gelirse fail-closed
        sinif = MERDIVEN.HAL_YETENEK
    karar = MERDIVEN.merdiven_ilerlet(
        kayit, sinif, motor=kayit.get("motor"), damga=_damga(),
        canli_motorlar=CANLI_ISCI_MOTORLARI, rc=rc,
        atif=kayit.get("rapor_yolu"), metin=metin)
    if karar is None:
        # Canli kume BOS: kalem HICBIR yone tasinmaz (fail-closed).
        kayit["durum"] = "MERDIVEN_OLCULEMEDI"
        sonuc.setdefault("merdiven_olculemedi", []).append(kimlik)
        sonuc.setdefault("merdiven_satirlari", []).append(
            MERDIVEN.merdiven_satiri(kimlik, None))
        return None
    sonuc.setdefault("merdiven_satirlari", []).append(
        MERDIVEN.merdiven_satiri(kimlik, karar))
    durum = karar["durum"]
    if durum == MERDIVEN.DURUM_ESKALASYON:
        sonuc["eskalasyon"].append(kimlik)
        # (c) Ust kata giden is OLCULMUSU de goturur.
        sonuc.setdefault("eskalasyon_satirlari", []).append(
            MERDIVEN.eskalasyon_satiri(kimlik, kayit))
    elif durum == MERDIVEN.DURUM_ARAC_KUSURU:
        sonuc.setdefault("arac_kusuru", []).append(kimlik)
    elif durum == MERDIVEN.DURUM_BITMEYEN_TUR:
        sonuc.setdefault("bitmeyen_tur", []).append(kimlik)
    elif durum == MERDIVEN.DURUM_KOTA_BEKLEMEDE:
        sonuc.setdefault("kota_beklemede", []).append(kimlik)
    else:
        sonuc["dusen"].append(kimlik)
    return karar
'''


# ---------------------------------------------------------------------------
# P4 — dort cagri yeri, dort SINIF
# ---------------------------------------------------------------------------

P4A_ESKI = '''                sonuc["beyan_var_kanit_yok"].append(kimlik)
                _kalemi_dusur(kayit, kimlik, sonuc)
'''
P4A_YENI = '''                sonuc["beyan_var_kanit_yok"].append(kimlik)
                # Is GERCEKTEN denendi ve kabul dustu -> varsayilan YETENEK.
                _kalemi_dusur(kayit, kimlik, sonuc, metin=metin,
                              rc=hukum.get("rc") or 1,
                              varsayilan=MERDIVEN.HAL_YETENEK)
'''

P4B_ESKI = '''                sonuc["reddedilen"].append(kimlik)
                _kalemi_dusur(kayit, kimlik, sonuc)
'''
P4B_YENI = '''                sonuc["reddedilen"].append(kimlik)
                # 🔴 K257(b): kabul komutu C4 kapisinca REDDEDILDI -> komut HIC
                # KOSMADI. Bu bir ARAC KUSURUDUR, yetenek kusuru DEGIL:
                # ne yana ne yukari, sayaca DAHIL DEGIL.
                _kalemi_dusur(
                    kayit, kimlik, sonuc, hal=MERDIVEN.HAL_KAPI_REDDI,
                    metin="kabul-komutu-kapisi sebep=%s" % hukum.get("sebep"),
                    rc=1)
'''

P4C_ESKI = '''            sonuc["olu"].append(kimlik)
            _kalemi_dusur(kayit, kimlik, sonuc)
            continue
'''
P4C_YENI = '''            sonuc["olu"].append(kimlik)
            # Isci basladi ama BITIREMEDI -> B7 kovasi (varsayilan). Metinde
            # kota/kapi izi varsa `hal_coz` onu USTUN tutar.
            _kalemi_dusur(kayit, kimlik, sonuc, metin=metin, rc=1,
                          varsayilan=MERDIVEN.HAL_BITMEYEN_TUR)
            continue
'''

P4D_ESKI = '''        if yas >= DUSME_TUR_ESIGI:
            _kalemi_dusur(kayit, kimlik, sonuc)
        else:
'''
P4D_YENI = '''        if yas >= DUSME_TUR_ESIGI:
            _kalemi_dusur(kayit, kimlik, sonuc, metin=metin, rc=1,
                          varsayilan=MERDIVEN.HAL_YETENEK)
        else:
'''


# ---------------------------------------------------------------------------
# P5 — dagitilmayacak durumlar merdivenden TURER
# ---------------------------------------------------------------------------

P5_ESKI = '''    return [k for k, v in geri_iz.get("kalemler", {}).items()
            if v.get("durum") == "ESKALASYON"]
'''
P5_YENI = '''    # K257: insan kapisindaki kalemlere ek olarak ARAC_KUSURU (kapi reddi,
    # sahibine dondu) ve KOTA_BEKLEMEDE (tum canli motorlar kotada) kalemleri
    # de bu turda DAGITILMAZ. Liste merdiven modulunden TURER, burada IKINCI
    # bir kopya tutulmaz.
    return [k for k, v in geri_iz.get("kalemler", {}).items()
            if v.get("durum") in MERDIVEN.DAGITILMAZ_DURUMLAR]
'''


# ---------------------------------------------------------------------------
# P6 — kalem_dagit: SAYAC SIFIRLANMAZ + merdiven TASINIR
# ---------------------------------------------------------------------------

P6A_ESKI = '''    sayi = int(onceki.get("dagitim_sayisi", 0)) + 1 if yeniden else 1
'''
P6A_YENI = '''    # 🔴 K257(a): SAYAC SIFIRDAN BASLAMAZ. Burada `yeniden` False iken sayi
    # 1'e EZILIYORDU — kalem baska bir kata gecince gecmisi siliniyor, merdiven
    # sonsuz donguye donuyordu. Merdiven kaydi varsa sayi ORADAN turer.
    _merdiven_sayaci = MERDIVEN.sayac(onceki)
    if _merdiven_sayaci:
        sayi = _merdiven_sayaci
    else:
        sayi = int(onceki.get("dagitim_sayisi", 0)) + 1 if yeniden else 1
'''

P6B_ESKI = '''    komut = isci_komutu(motor, spec_yolu, rapor_yolu, etiket)
'''
P6B_YENI = '''    # K257: merdiven yalniz raporda degil ICRADA da yon verir — kalemin
    # basamagi CANLI bir isci motoruysa dagitim O basamaga yapilir.
    _basamak = MERDIVEN.merdiven_kaydi(onceki).get("basamak")
    if _basamak in CANLI_ISCI_MOTORLARI and motor_ayakta(_basamak):
        motor = _basamak
    komut = isci_komutu(motor, spec_yolu, rapor_yolu, etiket)
'''

P6C_ESKI = '''        "dagitim_sayisi": sayi,
    }
    geri_iz.setdefault("kalemler", {})[kalem["id"]] = kayit
'''
P6C_YENI = '''        "dagitim_sayisi": sayi,
    }
    # 🔴 (c) OLCULMUS TASINIR: kayit YENIDEN kuruldugu icin merdiven gecmisi
    # burada DUSERDI; ust kat sifirdan olcmesin diye ACIKCA tasinir.
    if onceki.get("merdiven"):
        kayit["merdiven"] = onceki["merdiven"]
    geri_iz.setdefault("kalemler", {})[kalem["id"]] = kayit
'''


# ---------------------------------------------------------------------------
# P7 — tur_kapat: (d) SLA + merdiven satirlari
# ---------------------------------------------------------------------------

P7_ESKI = '''    goc_satirlari, goc_sayisi = bayat_eskalasyonlari_gocur(geri_iz)
'''
P7_YENI = '''    goc_satirlari, goc_sayisi = bayat_eskalasyonlari_gocur(geri_iz)
    # 🔴 K257(d): BaBa basamagi HUKUM/TESHIS katidir, icra kati DEGIL. Orada
    # SAYAC islemez, SLA isler: kalem yasi 24 saati asarsa Okan basamagi.
    # Bu kol `denemeler` listesine DOKUNMAZ (sayaca dahil DEGIL).
    sla_satirlari = []
    for _sla_id, _sla_kayit in sorted((geri_iz.get("kalemler") or {}).items()):
        _sla = MERDIVEN.sla_karari(_sla_kayit,
                                   canli_motorlar=CANLI_ISCI_MOTORLARI)
        if _sla and _sla.get("asildi"):
            sla_satirlari.append(
                "MERDIVEN_SLA kalem=%s BASAMAK=BABA->OKAN YAS_SN=%d SAYAC=%d"
                % (_sla_id, int(_sla["yas_sn"]), _sla["sayac"]))
'''

P7B_ESKI = '''    satirlar.extend(goc_satirlari)
    satirlar.append("ESKALASYON_BAYAT_GOC=%d" % goc_sayisi)
'''
P7B_YENI = '''    satirlar.extend(goc_satirlari)
    satirlar.append("ESKALASYON_BAYAT_GOC=%d" % goc_sayisi)
    satirlar.extend(sla_satirlari)
    satirlar.extend(olcum.get("merdiven_satirlari") or ())
    satirlar.extend(olcum.get("eskalasyon_satirlari") or ())
    satirlar.append("MERDIVEN_ARAC_KUSURU=%d MERDIVEN_BITMEYEN_TUR=%d "
                    "MERDIVEN_KOTA_BEKLEMEDE=%d MERDIVEN_OLCULEMEDI=%d"
                    % (len(olcum.get("arac_kusuru") or ()),
                       len(olcum.get("bitmeyen_tur") or ()),
                       len(olcum.get("kota_beklemede") or ()),
                       len(olcum.get("merdiven_olculemedi") or ())))
'''

P7C_ESKI = '''    plan = fanout_plani(kalemler, geri_iz, FANOUT_TAVANI, yeniden=yeniden,
                        haric=set(olcum["kapanan"]))
'''
P7C_YENI = '''    # K257(b): BITMEYEN_TUR kalemi B7'nin kovasindadir — AYNI TUR YENIDEN
    # KURULMAZ, kalem BU turda aday havuzuna girmez (sonraki turda girer).
    plan = fanout_plani(kalemler, geri_iz, FANOUT_TAVANI, yeniden=yeniden,
                        haric=set(olcum["kapanan"])
                        | set(olcum.get("bitmeyen_tur") or ()))
'''


# ---------------------------------------------------------------------------
# P8 — eski TEK ESIK sabiti ADIYLA emekli edilir (ikinci esik = ikinci kaynak)
# ---------------------------------------------------------------------------

P8_ESKI = """ESKALASYON_DAGITIM = 3     # H4: 3. dagitim da rapor uretmezse Okan'a
"""
P8_YENI = '''# 🔴 K257 (20 Agu 2026): bu TEK ESIK ARTIK OKUNMUYOR. Merdiven basamak basamak
# `nobet_merdiven` modulunde sayilir (m3 2 · kimi 1 · MIMAR 1 · KRAL 1 · BABA SLA
# · OKAN). Sabit yalniz eski geri-iz kayitlarini okuyan araclar ADIYLA bulsun
# diye birakildi; hicbir uretim kolu onu okumaz — okuyan kol IKINCI BIR ESIK
# demektir ve kabul bataryasi (S7g) bunu ast ekseninde REDDEDER.
ESKALASYON_DAGITIM = 3     # KULLANILMIYOR (K257 oncesi H4 esigi)
'''


YAMALAR = (
    ("P1 merdiven import", P1_ESKI, P1_YENI),
    ("P8 eski tek esik emekli", P8_ESKI, P8_YENI),
    ("P2 TUR_MOTOR_ZINCIRI turetildi", P2_ESKI, P2_YENI),
    ("P3 _kalemi_dusur merdiven", P3_ESKI, P3_YENI),
    ("P4a beyan_var_kanit_yok", P4A_ESKI, P4A_YENI),
    ("P4b KOMUT_REDDEDILDI=KAPI_REDDI", P4B_ESKI, P4B_YENI),
    ("P4c olu isci=BITMEYEN_TUR", P4C_ESKI, P4C_YENI),
    ("P4d yas esigi=YETENEK", P4D_ESKI, P4D_YENI),
    ("P5 dagitilmaz durumlar", P5_ESKI, P5_YENI),
    ("P6a sayac sifirlanmaz", P6A_ESKI, P6A_YENI),
    ("P6b basamaga dagitim", P6B_ESKI, P6B_YENI),
    ("P6c merdiven kaydi tasinir", P6C_ESKI, P6C_YENI),
    ("P7a SLA kolu", P7_ESKI, P7_YENI),
    ("P7b merdiven satirlari", P7B_ESKI, P7B_YENI),
    ("P7c bitmeyen tur haric", P7C_ESKI, P7C_YENI),
)


# ---------------------------------------------------------------------------

def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yaz(yol, metin):
    """🔴 ATOMIK yazma: cron nobeti AYNI ANDA bu dosyayi import ediyor olabilir.

    Duz `open(w)` yarim yazilmis bir dosya penceresi acar ve o pencerede
    baslayan tur SyntaxError ile duser. `os.replace` ayni dosya sisteminde
    atomiktir; okuyucu ya ESKI ya YENI dosyayi gorur, arasini GORMEZ.
    """
    gecici = "%s.k257-yazim-%d" % (yol, os.getpid())
    with open(gecici, "w", encoding="utf-8") as dosya:
        dosya.write(metin)
    shutil.copymode(yol, gecici)
    os.replace(gecici, yol)


def yedekle(yol, damga):
    hedef = "%s.%s-%s" % (yol, YEDEK_ONEK, damga)
    if not os.path.exists(hedef):
        shutil.copy2(yol, hedef)
    return hedef


def degistir(metin, eski, yeni):
    """Ankor TEKIL degilse yama UYGULANMAZ (fail-closed, sessiz kayma YOK)."""
    if yeni in metin:
        return metin, False
    if metin.count(eski) != 1:
        return metin, None
    return metin.replace(eski, yeni, 1), True


DURUM_ADLARI = {True: "UYGULANDI", False: "ZATEN_VARDI", None: "ANKOR_YOK"}


def olculer():
    kapi = oku(NOBET_KAPI)
    tst = oku(TESTLER)
    return [
        ("P0 merdiven modulu kurulu", os.path.isfile(MODUL_HEDEF)),
        ("P1 nobet-kapi import ediyor",
         "import nobet_merdiven as MERDIVEN" in kapi),
        ("P2 zincir turetildi", "TUR_MOTOR_ZINCIRI = tuple(CANLI_ISCI_MOTORLARI)"
         in kapi),
        ("P2b elle tuple KALMADI",
         'TUR_MOTOR_ZINCIRI = ("minimax-m3",)' not in kapi),
        ("P3 _kalemi_dusur merdiven", "MERDIVEN.merdiven_ilerlet(" in kapi),
        ("P4b KAPI_REDDI zorlaniyor",
         "hal=MERDIVEN.HAL_KAPI_REDDI" in kapi),
        ("P4c BITMEYEN_TUR varsayilani",
         "varsayilan=MERDIVEN.HAL_BITMEYEN_TUR" in kapi),
        ("P5 dagitilmaz durumlar", "MERDIVEN.DAGITILMAZ_DURUMLAR" in kapi),
        ("P6a sayac sifirlanmaz", "_merdiven_sayaci = MERDIVEN.sayac(onceki)"
         in kapi),
        ("P6c merdiven kaydi tasinir",
         'kayit["merdiven"] = onceki["merdiven"]' in kapi),
        ("P7a SLA kolu", "MERDIVEN.sla_karari(" in kapi),
        ("P7b merdiven satirlari", "MERDIVEN_ARAC_KUSURU=%d" in kapi),
        ("P8 eski tek esik emekli",
         "ESKALASYON_DAGITIM = 3     # KULLANILMIYOR" in kapi),
        ("T1 kabul bataryasi kurulu", os.path.isfile(TEST_HEDEF)),
        ("T2 testler.py kaydi (CAGRI YERI)", TEST_ADI in tst),
    ]


def olc():
    try:
        liste = olculer()
    except OSError as hata:
        print("HUKUM=OLCULEMEDI sebep=%s" % hata)
        return 2
    kurulu = 0
    for ad, var in liste:
        print("YAMA=%-38s DURUM=%s" % (ad, "VAR" if var else "YOK"))
        kurulu += 1 if var else 0
    print("K257_KURULU=%d/%d" % (kurulu, len(liste)))
    print("HUKUM=%s" % ("KURULU" if kurulu == len(liste) else "EKSIK"))
    return 0 if kurulu == len(liste) else 1


def _dosya_kur(kaynak, hedef, ad, rapor):
    if not os.path.isfile(kaynak):
        rapor.append((ad, None))
        return
    shutil.copy2(kaynak, hedef)
    os.chmod(hedef, 0o755)
    rapor.append((ad, True))


def uygula():
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rapor = []

    _dosya_kur(MODUL_KAYNAK, MODUL_HEDEF, "P0 modul kuruldu", rapor)

    kapi = oku(NOBET_KAPI)
    yedek_kapi = yedekle(NOBET_KAPI, damga)
    for ad, eski, yeni in YAMALAR:
        kapi, durum = degistir(kapi, eski, yeni)
        rapor.append((ad, durum))
    yaz(NOBET_KAPI, kapi)

    _dosya_kur(TEST_KAYNAK, TEST_HEDEF, "T1 batarya kuruldu", rapor)

    tst = oku(TESTLER)
    yedek_tst = yedekle(TESTLER, damga)
    if TEST_ADI in tst:
        rapor.append(("T2 testler.py kaydi", False))
    else:
        ankor = '    "nobet-tur-izolasyon-test.py",\n'
        if ankor in tst:
            tst = tst.replace(ankor, ankor + '    "%s",\n' % TEST_ADI, 1)
            yaz(TESTLER, tst)
            rapor.append(("T2 testler.py kaydi", True))
        else:
            rapor.append(("T2 testler.py kaydi", None))

    for ad, durum in rapor:
        print("YAMA=%-38s SONUC=%s" % (ad, DURUM_ADLARI[durum]))
    ankorsuz = sum(1 for _, d in rapor if d is None)
    print("YEDEK=%s" % yedek_kapi)
    print("YEDEK=%s" % yedek_tst)
    print("DAMGA=%s" % damga)
    print("ANKORSUZ=%d" % ankorsuz)
    print("HUKUM=%s" % ("UYGULANDI" if ankorsuz == 0 else "ANKOR_YOK"))
    return 0 if ankorsuz == 0 else 1


def geri_al(damga):
    n = 0
    for yol in HEDEFLER:
        yedek = "%s.%s-%s" % (yol, YEDEK_ONEK, damga)
        if os.path.isfile(yedek):
            shutil.copy2(yedek, yol)
            n += 1
            print("GERI_ALINDI=%s" % yol)
    for yol in (MODUL_HEDEF, TEST_HEDEF):
        if os.path.isfile(yol):
            os.remove(yol)
            print("SILINDI=%s" % yol)
    print("GERI_ALINAN=%d" % n)
    return 0 if n else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="K257 kurucu (eskalasyon merdiveni)")
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--geri-al", metavar="DAMGA")
    args = ap.parse_args(argv)
    if args.geri_al:
        return geri_al(args.geri_al)
    if args.uygula:
        rc = uygula()
        print("--- KURULUM SONRASI OLCUM ---")
        olc()
        return rc
    return olc()


if __name__ == "__main__":
    sys.exit(main())
