#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K262 — N2 "4 SAATLIK OTOMATIK DEVIR" KABUL KAPISI (iki yonlu).

Kurgunun (memory/nobet-onarim-kurgusu.md) N2 maddesi birebir:
  "kalem sahibinde 4 saat hareketsizse gozcu onu Tamirci'ye (KraL)
   DEVREDER, kutuya `DEVREDILDI` duser, kaciran evin hanesine IHLAL
   SAYACI islenir."
Bitis olcutu ise IKI YONLU: "4 saatte devir olur, 4 saatten ONCE olmaz."

🔴 NEDEN AYRI BIR KAPI: 20 Agu 2026'da olculdu — `14400` / `DEVREDILDI` /
`ihlal_sayaci` jetonlari `gozcu.py` + `nobet-kapi.py` + `nobet-tetik.py` +
`nobet_merdiven.py` dosyalarinda TOPLAM **0** kez geciyor. Yani mekanizma
YAZILMAMIS. Ama "jeton yok" bir DAVRANIS olcumu DEGILDIR
([[aracin-teshis-cumlesi-olcum-degil]]): jeton eklenip davranis yanlis
kurulabilir ya da jeton hic gecmeden davranis dogru kurulabilir. Bu kapi
o yuzden jeton DEGIL, DAVRANIS olcer ve mekanizma yokken FAIL-CLOSED
(rc=1) doner.

## SOZLESME — mekanizmayi kuran taraf bunu saglar

`~/.claude/cron/nobet_devir.py` modulu su ikisini disa acar:

    DEVIR_ESIGI_SN = 14400          # 4 saat

    def devir_karari(kayit, simdi):
        \"\"\"kayit: {"id","sahip","son_hareket" (epok), "durum", ...}
        Doner: {"devredildi": bool, "eski_sahip": str, "yeni_sahip": str,
                "sebep": str, "ihlal_delta": int}
        KURAL: simdi - son_hareket >= DEVIR_ESIGI_SN  -> devredildi=True,
               yeni_sahip="KraL", ihlal_delta=1 (eski_sahip hanesine).
               Esigin ALTINDA  -> devredildi=False, ihlal_delta=0.
               KAPANMIS kalem  -> devredildi=False (yas ne olursa olsun).
               AYNI kalem ikinci kez devredilemez -> ihlal_delta=0.
        SAYACA/DEFTERE YAZMAZ: saf karar fonksiyonudur (test edilebilir
        olsun diye). Yazmayi cagiran taraf yapar.\"\"\"

KOSUM: python3 /Users/okan/dev/pruvo/tools/devir-4saat-kabul.py
KABUL: son satir `KABUL=GECTI`, rc=0.
"""

import importlib.util
import os
import sys

CRON_KOKU = "/Users/okan/.claude/cron"
MODUL_YOLU = os.path.join(CRON_KOKU, "nobet_devir.py")

SAAT = 3600
ESIK = 4 * SAAT          # 14400 — sozlesmedeki beklenen deger
SON_HAREKET = 1_000_000  # sabit epok tabani (Date.now bagimliligi YOK)

BEKLENEN_YENI_SAHIP = "KraL"


def _modul_yukle(yol=None):
    yol = yol or MODUL_YOLU
    if not os.path.isfile(yol):
        return None, "DOSYA_YOK"
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    try:
        spec = importlib.util.spec_from_file_location("k262_devir", yol)
        modul = importlib.util.module_from_spec(spec)
        sys.modules["k262_devir"] = modul
        spec.loader.exec_module(modul)
    except Exception as hata:                       # noqa: BLE001
        return None, "IMPORT_HATASI:%s" % (hata,)
    for ad in ("DEVIR_ESIGI_SN", "devir_karari"):
        if not hasattr(modul, ad):
            return None, "SOZLESME_EKSIK:%s" % ad
    return modul, None


def _kayit(sahip="MaCiT", durum="ACIK", devredildi_mi=False):
    kayit = {"id": "K262-VAKA", "sahip": sahip, "durum": durum,
             "son_hareket": SON_HAREKET}
    if devredildi_mi:
        kayit["devredildi"] = True
    return kayit


# --- vakalar: (ad, kayit uretici, simdi, beklenen) -------------------------
# 🔴 IKI YONLU: V1/V2 esigin IKI YANINI da civiler. Yalniz "devir OLDU"
# olcen bir batarya, esigi 1 sn'ye dusuren mutanti GOREMEZ.
VAKALAR = (
    ("V1 esikten 1 sn ONCE devir OLMAZ",
     lambda: _kayit(), SON_HAREKET + ESIK - 1,
     {"devredildi": False, "ihlal_delta": 0}),

    ("V2 esikte (tam 4 saat) devir OLUR",
     lambda: _kayit(), SON_HAREKET + ESIK,
     {"devredildi": True, "yeni_sahip": BEKLENEN_YENI_SAHIP,
      "eski_sahip": "MaCiT", "ihlal_delta": 1}),

    ("V3 esikten 1 saat SONRA devir OLUR",
     lambda: _kayit(), SON_HAREKET + ESIK + SAAT,
     {"devredildi": True, "yeni_sahip": BEKLENEN_YENI_SAHIP,
      "ihlal_delta": 1}),

    ("V4 yeni acilmis kalem (0 sn) devir OLMAZ",
     lambda: _kayit(), SON_HAREKET,
     {"devredildi": False, "ihlal_delta": 0}),

    # KONTROL: yas esigin COK ustunde ama kalem KAPANMIS -> devir OLMAZ.
    # Bu vaka olmadan "yas>esik ise hep True" diyen bos bir mekanizma gecer.
    ("V5 KAPANMIS kalem 8 saat sonra bile devir OLMAZ",
     lambda: _kayit(durum="KAPANDI"), SON_HAREKET + 2 * ESIK,
     {"devredildi": False, "ihlal_delta": 0}),

    # IDEMPOTANS: ikinci devir ihlali TEKRAR saymaz.
    ("V6 ZATEN devredilmis kalem ikinci kez IHLAL saymaz",
     lambda: _kayit(sahip=BEKLENEN_YENI_SAHIP, devredildi_mi=True),
     SON_HAREKET + 2 * ESIK,
     {"ihlal_delta": 0}),

    # SAHIP EKSENI: devir hep KraL'a (son mercii), sahibin evine DEGIL.
    ("V7 HocA'nin kalemi de KraL'a devredilir",
     lambda: _kayit(sahip="HocA"), SON_HAREKET + ESIK,
     {"devredildi": True, "yeni_sahip": BEKLENEN_YENI_SAHIP,
      "eski_sahip": "HocA", "ihlal_delta": 1}),
)


def vakalari_kos(modul, esik_gecersiz_kil=None):
    """Doner: (gecen, kalan, satirlar). `esik_gecersiz_kil`:
    - int ise DEVIR_ESIGI_SN'i gecici olarak override eder (eski arayuz).
    - callable ise modul uzerinde keyfi mutasyon yapar (orn: devir_karari'yi
      sarmalayarak belli bir kolu kirmak). Iki arayuz turu isinstance ile
      anlasilir; vakalari_kos kosumun sonunda modulu ESKI HALINE geri alir
      (DEVIR_ESIGI_SN ve devir_karari)."""
    eski_esik = getattr(modul, "DEVIR_ESIGI_SN", None)
    eski_func = getattr(modul, "devir_karari", None)
    if callable(esik_gecersiz_kil):
        esik_gecersiz_kil(modul)
    elif esik_gecersiz_kil is not None:
        modul.DEVIR_ESIGI_SN = esik_gecersiz_kil
    gecen, kalan, satirlar = 0, 0, []
    try:
        for ad, uretici, simdi, beklenen in VAKALAR:
            kayit = uretici()
            try:
                sonuc = modul.devir_karari(kayit, simdi)
            except Exception as hata:               # noqa: BLE001
                satirlar.append("  VAKA=%s HATA=%s -> KALDI" % (ad, hata))
                kalan += 1
                continue
            sapan = []
            for anahtar, deger in beklenen.items():
                gelen = (sonuc or {}).get(anahtar)
                if gelen != deger:
                    sapan.append("%s: beklenen=%r gelen=%r"
                                 % (anahtar, deger, gelen))
            if sapan:
                kalan += 1
                satirlar.append("  VAKA=%s SAPAN=[%s] -> KALDI"
                                % (ad, " · ".join(sapan)))
            else:
                gecen += 1
                satirlar.append("  VAKA=%s -> GECTI" % ad)
    finally:
        if eski_esik is not None:
            modul.DEVIR_ESIGI_SN = eski_esik
        if eski_func is not None and callable(esik_gecersiz_kil):
            modul.devir_karari = eski_func
    return gecen, kalan, satirlar


def _m3_kir_devredildi_ihlal(modul):
    """M3 mutatoru: DEVREDILDI kaydi (ihlal_delta) kirilir.

    devir_karari'yi sarmalayip devredildi=True donen sonuclarda
    ihlal_delta'yi 0 yapar. V2/V3/V7 (devredildi=True beklenen) bundan
    OLUR; V1/V4/V5/V6 zaten devredildi=False dondurdugu icin etkilenmez.
    """
    original = modul.devir_karari

    def kirik(kayit, simdi):
        sonuc = original(kayit, simdi)
        if sonuc.get("devredildi"):
            sonuc["ihlal_delta"] = 0
        return sonuc

    modul.devir_karari = kirik


def _kontrol_sebep_ekle(modul):
    """KONTROL mutatoru: kapinin BAKMADIGI bir kol degisir.

    devir_karari'yi sarmalayip donus sozlugundeki 'sebep' anahtarini
    '_KONTROL' sonekiyle degistirir. Gate vakalarinin hicbirinde 'sebep'
    beklenmedigi icin hicbir vaka KALMAMALI (YESIL kalmali = tautoloji yok).
    """
    original = modul.devir_karari

    def sarmalayici(kayit, simdi):
        sonuc = original(kayit, simdi)
        sonuc["sebep"] = sonuc.get("sebep", "") + "_KONTROL"
        return sonuc

    modul.devir_karari = sarmalayici


# --- mutantlar: esigin IKI YANI ayri ayri oldurulmeli ----------------------
# M1 ve M2 esik (DEVIR_ESIGI_SN) kolunu hedefler; M3 ise DEVREDILDI kaydini
# (ihlal_delta) callable mutator ile kirar — kapsam disi ama ayni KAPI uzerinden
# gecer. Spec: en az 3 mutant (a esik / b DEVREDILDI kaydi / c erken-devir).
MUTANTLAR = (
    ("M1 esik 4 saat -> 99 saat (devir HIC olmaz)", 99 * SAAT,
     "V2/V3/V7 (devir OLUR kolu) OLMELI"),
    ("M2 esik 4 saat -> 1 sn (devir HEP olur)", 1,
     "V1/V4 (devir OLMAZ kolu) OLMELI"),
    ("M3 DEVREDILDI kaydi (ihlal_delta=0, callable mutator)", _m3_kir_devredildi_ihlal,
     "V2/V3/V7 (ihlal_delta kolu) OLMELI"),
)

# KONTROL mutanti: kapinin BAKMADIGI bir kolu (sebep) degistirir. Tum
# vakalar YESIL kalmali (tautoloji yok). Callable formda.
KONTROL_MUTATOR = _kontrol_sebep_ekle


def sozlesme_bas():
    print("SOZLESME — mekanizmayi kuran taraf sunu saglar:")
    print("  dosya : %s" % MODUL_YOLU)
    print("  sabit : DEVIR_ESIGI_SN = %d  (4 saat)" % ESIK)
    print("  islev : devir_karari(kayit, simdi) -> "
          "{devredildi, eski_sahip, yeni_sahip, sebep, ihlal_delta}")
    print("  kural : simdi-son_hareket >= ESIK -> devredildi=True, "
          "yeni_sahip='%s', ihlal_delta=1" % BEKLENEN_YENI_SAHIP)
    print("          esigin ALTINDA -> False/0 · KAPANMIS kalem -> False/0")
    print("          ZATEN devredilmis kalem -> ihlal_delta=0 (idempotans)")
    print("  not   : saf KARAR fonksiyonu — sayaca/deftere YAZMAZ.")


# ===========================================================================
# --kendini-test : kapinin YESIL kolu da olculur
# ===========================================================================
#
# 🔴 NEDEN: "mekanizma yok -> rc=1" tek basina bu kapinin CALISTIGINI
# kanitlamaz. Hep kirmizi yanan KOR bir kapi da ayni ciktiyi verir
# ([[kor-kapi]] sinifi). Asagidaki referans gerceklestirimler kapinin
# YESILE DONEBILDIGINI ve BOZUK gerceklestirimleri REDDETTIGINI olcer.

_REFERANS = '''
DEVIR_ESIGI_SN = 14400


def devir_karari(kayit, simdi):
    kayit = kayit or {}
    eski = kayit.get("sahip")
    yas = simdi - (kayit.get("son_hareket") or 0)
    kapali = (kayit.get("durum") or "") in ("KAPANDI", "KAPANIS")
    zaten = bool(kayit.get("devredildi"))
    if kapali or zaten or yas < DEVIR_ESIGI_SN:
        sebep = ("KAPALI" if kapali else
                 "ZATEN_DEVREDILDI" if zaten else "SLA_ICINDE")
        return {"devredildi": False, "eski_sahip": eski,
                "yeni_sahip": eski, "sebep": sebep, "ihlal_delta": 0}
    return {"devredildi": True, "eski_sahip": eski, "yeni_sahip": "KraL",
            "sebep": "DEVREDILDI", "ihlal_delta": 1}
'''

# BOZUK-1: `>=` yerine `>` — esikte (TAM 4 saat) devir OLMAZ. V2 dusmeli.
_BOZUK_SINIR = _REFERANS.replace("yas < DEVIR_ESIGI_SN",
                                 "yas <= DEVIR_ESIGI_SN")
# BOZUK-2: idempotans YOK — devredilmis kalem ikinci kez ihlal sayar.
_BOZUK_IDEMPOTANS = _REFERANS.replace('zaten = bool(kayit.get("devredildi"))',
                                      "zaten = False")
# BOZUK-3: KAPANMIS kalem korunmuyor — V5 dusmeli.
_BOZUK_KAPALI = _REFERANS.replace(
    'kapali = (kayit.get("durum") or "") in ("KAPANDI", "KAPANIS")',
    "kapali = False")
# BOZUK-4: devir sahibin KENDI evine — V2/V7'nin yeni_sahip kolu dusmeli.
_BOZUK_SAHIP = _REFERANS.replace('"yeni_sahip": "KraL"',
                                 '"yeni_sahip": eski')

KENDINI_TEST_VAKALARI = (
    ("referans gerceklestirim", _REFERANS, True),
    ("BOZUK sinir (> yerine >=)", _BOZUK_SINIR, False),
    ("BOZUK idempotans", _BOZUK_IDEMPOTANS, False),
    ("BOZUK kapali-kalem korumasi", _BOZUK_KAPALI, False),
    ("BOZUK devir sahibi (KraL degil)", _BOZUK_SAHIP, False),
)


def kendini_test():
    import tempfile
    print("# K262 kapisi — KENDINI TEST (yesil kolu da olculur)")
    gecen, kalan = 0, 0
    gecici = tempfile.mkdtemp(prefix="k262-kendini-")
    try:
        for ad, govde, beklenen_yesil in KENDINI_TEST_VAKALARI:
            yol = os.path.join(gecici, "nobet_devir.py")
            with open(yol, "w", encoding="utf-8") as dosya:
                dosya.write(govde)
            modul, hata = _modul_yukle(yol)
            if modul is None:
                print("  VAKA=%s YUKLENEMEDI=%s -> KALDI" % (ad, hata))
                kalan += 1
                continue
            v_gecen, v_kalan, _ = vakalari_kos(modul)
            mutant_hepsi = True
            for _m_ad, esik, _hedef in MUTANTLAR:
                _g, m_kalan, _s = vakalari_kos(modul, esik_gecersiz_kil=esik)
                mutant_hepsi = mutant_hepsi and (m_kalan > 0)
            yesil = (v_kalan == 0 and mutant_hepsi)
            uygun = yesil == beklenen_yesil
            gecen, kalan = (gecen + 1, kalan) if uygun else (gecen, kalan + 1)
            print("  VAKA=%s YESIL=%s BEKLENEN=%s (vaka %d/%d, mutant=%s) -> %s"
                  % (ad, yesil, beklenen_yesil, v_gecen, len(VAKALAR),
                     "oldurdu" if mutant_hepsi else "YASADI",
                     "GECTI" if uygun else "KALDI"))
    finally:
        import shutil
        shutil.rmtree(gecici, ignore_errors=True)
    print("KENDINI_TEST GECEN=%d KALAN=%d" % (gecen, kalan))
    rc = 0 if kalan == 0 else 1
    print("KAPSAM=%d gerceklestirim (1 referans + %d bozuk)"
          % (len(KENDINI_TEST_VAKALARI), len(KENDINI_TEST_VAKALARI) - 1))
    print("KABUL=%s" % ("GECTI" if rc == 0 else "KALDI"))
    return rc


def main():
    if "--kendini-test" in sys.argv[1:]:
        return kendini_test()
    print("# K262 — N2 4 saatlik otomatik devir, IKI YONLU kabul kapisi")
    print("VAKA_SAYISI=%d MUTANT_SAYISI=%d" % (len(VAKALAR), len(MUTANTLAR)))

    modul, hata = _modul_yukle()
    if modul is None:
        print("MEKANIZMA=YOK sebep=%s" % hata)
        print("OLCULEN_DAVRANIS=0/%d — jeton taramasi DEGIL, davranis "
              "olcumu yapilamadi cunku sozlesme yuzeyi YOK." % len(VAKALAR))
        print()
        sozlesme_bas()
        print()
        print("🔴 FAIL-CLOSED: mekanizma kurulana kadar bu kapi KIRMIZI "
              "yanar. Yesile donmesi = K262 KAPANDI demektir.")
        print("KABUL=KALDI")
        return 1

    print("MEKANIZMA=VAR yol=%s DEVIR_ESIGI_SN=%s"
          % (MODUL_YOLU, getattr(modul, "DEVIR_ESIGI_SN", None)))
    if getattr(modul, "DEVIR_ESIGI_SN", None) != ESIK:
        print("🔴 ESIK SAPMASI: beklenen=%d gelen=%s"
              % (ESIK, getattr(modul, "DEVIR_ESIGI_SN", None)))

    gecen, kalan, satirlar = vakalari_kos(modul)
    print("--- TABAN ---")
    for satir in satirlar:
        print(satir)
    print("TABAN GECEN=%d KALAN=%d" % (gecen, kalan))

    print("--- MUTANTLAR (esigin IKI YANI + DEVREDILDI kaydi) ---")
    mutant_hepsi = True
    for ad, esik, hedef in MUTANTLAR:
        m_gecen, m_kalan, m_satirlar = vakalari_kos(modul, esik_gecersiz_kil=esik)
        oldu = m_kalan > 0
        mutant_hepsi = mutant_hepsi and oldu
        # Hangi vakalar KALDI? Spec: hedef kol kaniti (K182 sinifi).
        dusenler = []
        for s in m_satirlar:
            if "KALDI" in s:
                vaka = s.split("VAKA=")[1].split(" ")[0]
                dusenler.append(vaka)
        print("  MUTANT=%s HEDEF=%s KALAN=%d DUSEN=%s SONUC=%s"
              % (ad, hedef, m_kalan, dusenler,
                 "GECTI" if oldu else "KALDI(mutant YASADI)"))

    print("--- KONTROL MUTANTI (ilgisiz kol — kapi YESIL kalmali) ---")
    k_gecen, k_kalan, k_satirlar = vakalari_kos(
        modul, esik_gecersiz_kil=KONTROL_MUTATOR)
    kontrol_ok = (k_kalan == 0)
    print("  KONTROL=sebep koluna _KONTROL ekleniyor KALAN=%d SONUC=%s"
          % (k_kalan, "YESIL(ilgisiz kol, kapi gecti)" if kontrol_ok
             else "KIRMIZI(ilgisiz kol kirildi — tautoloji BOZULDU)"))

    rc = 0 if (kalan == 0 and mutant_hepsi and kontrol_ok) else 1
    print("KAPSAM=%d vaka · %d mutant (esik+D'REDILDI+erken-devir) · "
          "1 kontrol" % (len(VAKALAR), len(MUTANTLAR)))
    print("KABUL=%s" % ("GECTI" if rc == 0 else "KALDI"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
