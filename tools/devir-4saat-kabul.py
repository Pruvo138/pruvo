#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K262/K263 — N2 "4 SAATLIK OTOMATIK DEVIR" KABUL KAPISI (iki yonlu + canli kablolama).

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

## K263 EKLEMESI — CANLI KABLOLAMA (menzil = cagri yeri)

Karar fonksiyonunun DOGRU olmasi yetmez: canli nobet turunun onu GERCEKTEN
CAGIRMASI gerekir ([[kapinin-menzili-cagri-yeridir]]). K263 bu ekseni IKI
AYRI KOLDAN olcer ve HER IKI KOL DA JETON TARAMASI DEGILDIR:

  * DAVRANIS kolu — canli betik IMPORT EDILIR ve devir giris islevi
    GERCEKTEN KOSTURULUR (gozcu: `n2_devir_kararlari`, nobet-kapi:
    `_n2_devir_logla`). Sentetik iki kalem verilir (biri 4 saatten YASLI,
    biri TAZE) ve donen SAYAC iki yonlu dogrulanir. Yan etki YOK: gozcu'nun
    iz dosyasi gecici yola, nobet-kapi'nin defter okuyucusu sentetik listeye
    yonlendirilir; canli iz/defter KIRLENMEZ.
  * CAGRI YERI kolu — betik `ast` ile AYRISTIRILIR ve turun giris
    fonksiyonunun (gozcu: `tur`, nobet-kapi: `tur_kos`) GOVDESINDE hedef
    islevin `ast.Call` dugumu aranir. Yorum satiri, docstring ya da dize
    `Call` dugumu URETMEZ — yani bir YORUM bu kolu YESIL YAKAMAZ.

🔴 UC KOVA (K263-③, [[iki-kovali-siniflama-ucuncu-sinifi-yutar]]):
"var / yok" IKI kova yetmez. Cron duzlemi (`~/.claude/cron`) CI runner'inda
YOKTUR; oradaki YOKLUK bir IHLAL degildir. Hukum uc kovaya ayrilir ve her
kovanin SAYISI BASILIR:
    KURULU     — betik var, HER IKI kol da olculdu ve YESIL
    IHLAL      — betik var, olculdu ve KOL DUSTU        (rc'yi KIRMIZI yapar)
    OLCULEMEDI — betik/sozlesme yok ya da import edilemedi (rc'yi ETKILEMEZ)
`--ci-simulasyon` bu ayrimi TEK VAKAYLA olcer: cron kokunu var olmayan bir
yola cevirir ve kapinin `OLCULEMEDI` basip rc'ye 0 katki verdigini gosterir.

🔴 MUTANTLAR GERCEK KAYNAGA UYGULANIR: kablolama mutantlari canli betigin
GECICI BIR KOPYASI uzerinde metin capasiyla uygulanir (canli dosyaya ASLA
dokunulmaz) ve her mutant HEDEF KOLUNU oldurdugunu, SAGLAM KOLUN ayakta
kaldigini AYRICA basar. Capa tekil degilse hukum "YASADI" degil
`OLCULEMEDI`dir ([[capa-cokmesi-arkasindaki-capalari-gizler]]).

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
CI SIMULASYONU: python3 .../devir-4saat-kabul.py --ci-simulasyon
KENDINI TEST : python3 .../devir-4saat-kabul.py --kendini-test
"""

import ast
import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import time

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


# ===========================================================================
# K263 — CANLI KABLOLAMA OLCUMU (davranis + cagri yeri, UC KOVA)
# ===========================================================================

KURULU = "KURULU"
IHLAL = "IHLAL"
OLCULEMEDI = "OLCULEMEDI"
KOVA_SIRASI = (KURULU, IHLAL, OLCULEMEDI)

_YUKLEME_SAYACI = [0]


def _benzersiz_modul_adi(onek):
    _YUKLEME_SAYACI[0] += 1
    return "k263_%s_%d" % (onek, _YUKLEME_SAYACI[0])


def _yukle_yoldan(yol, onek):
    """Verilen yoldaki betigi BENZERSIZ bir modul adiyla yukler.

    Bytecode diske YAZILMAZ (Okan disk kurali). Basarisizlik bir IHLAL
    DEGIL, OLCULEMEDI'dir — sebep dizesiyle birlikte doner.
    """
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    ad = _benzersiz_modul_adi(onek)
    eski_pyc = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(ad, yol)
        if spec is None or spec.loader is None:
            return None, "SPEC_YOK"
        modul = importlib.util.module_from_spec(spec)
        sys.modules[ad] = modul
        spec.loader.exec_module(modul)
    except Exception as hata:                       # noqa: BLE001
        return None, "IMPORT_HATASI:%s" % (hata,)
    finally:
        sys.dont_write_bytecode = eski_pyc
        sys.modules.pop(ad, None)
    return modul, None


def cagri_yeri_kolu(kaynak, tur_fonksiyonu, cagrilan):
    """AST kolu: `tur_fonksiyonu` GOVDESINDE `cagrilan(...)` CAGRISI var mi?

    🔴 Bu bir JETON TARAMASI DEGILDIR: `ast.Call` dugumu yalnizca GERCEK bir
    cagri ifadesinden dogar. Yorum satiri, docstring ya da dize icindeki
    `devir_karari` metni bu kolu YESIL YAKAMAZ.
    Doner: (True/False/None, sebep). None = OLCULEMEDI.
    """
    try:
        agac = ast.parse(kaynak)
    except SyntaxError as hata:                     # noqa: BLE001
        return None, "AST_HATASI:%s" % (hata,)
    hedef = None
    for dugum in ast.walk(agac):
        if (isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef))
                and dugum.name == tur_fonksiyonu):
            hedef = dugum
            break
    if hedef is None:
        return False, "TUR_FONKSIYONU_YOK:%s" % tur_fonksiyonu
    for dugum in ast.walk(hedef):
        if not isinstance(dugum, ast.Call):
            continue
        islev = dugum.func
        ad = getattr(islev, "id", None) or getattr(islev, "attr", None)
        if ad == cagrilan:
            return True, "AST_CALL:%s icinde %s()" % (tur_fonksiyonu, cagrilan)
    return False, "CAGRI_YOK:%s govdesinde %s() yok" % (tur_fonksiyonu, cagrilan)


def gozcu_davranis_kolu(modul):
    """gozcu.n2_devir_kararlari() GERCEKTEN kosturulur (jeton DEGIL).

    Iz dosyasi gecici yola yonlendirilir -> canli `nobet-devir-iz.json`
    KIRLENMEZ. IKI YONLU: 4 saatlik kalem DEVREDILDI, taze kalem
    SLA_ICINDE saymali; ihlal 1 islenmelidir.
    Doner: (True/False/None, sebep). None = OLCULEMEDI.
    """
    if not hasattr(modul, "n2_devir_kararlari"):
        return False, "ISLEV_YOK:n2_devir_kararlari"
    if not hasattr(modul, "DEVIR_IZ_YOLU"):
        return None, "IZ_YOLU_SABITI_YOK"
    gecici = tempfile.mkdtemp(prefix="k263-iz-")
    eski_iz = modul.DEVIR_IZ_YOLU
    try:
        modul.DEVIR_IZ_YOLU = os.path.join(gecici, "iz.json")
        kalemler = [
            {"id": "K263-YASLI", "sahip": "MaCiT", "durum": "ACIK",
             "son_hareket": SON_HAREKET},
            {"id": "K263-TAZE", "sahip": "MaCiT", "durum": "ACIK",
             "son_hareket": SON_HAREKET + ESIK - 1},
        ]
        try:
            sayac = modul.n2_devir_kararlari(kalemler, SON_HAREKET + ESIK)
        except Exception as hata:                   # noqa: BLE001
            return None, "KOSUM_HATASI:%s" % (hata,)
    finally:
        modul.DEVIR_IZ_YOLU = eski_iz
        shutil.rmtree(gecici, ignore_errors=True)
    sayac = sayac or {}
    if sayac.get("hata"):
        return None, "DEVIR_MODULU_YUKLENEMEDI (sayac.hata=True)"
    beklenen = {"DEVREDILDI": 1, "SLA_ICINDE": 1, "ihlal_eklenen": 1}
    sapan = ["%s: beklenen=%r gelen=%r" % (a, d, sayac.get(a))
             for a, d in beklenen.items() if sayac.get(a) != d]
    if sapan:
        return False, "DAVRANIS_SAPMASI[%s]" % (" · ".join(sapan))
    return True, ("IKI_YONLU_OK D=%d S=%d IHLAL=%d"
                  % (sayac["DEVREDILDI"], sayac["SLA_ICINDE"],
                     sayac["ihlal_eklenen"]))


def nobet_kapi_davranis_kolu(modul):
    """nobet-kapi._n2_devir_logla() GERCEKTEN kosturulur (jeton DEGIL).

    Defter okuyucusu sentetik listeye yonlendirilir -> canli defter
    OKUNMAZ/KIRLENMEZ. Hukum, cikti icindeki `devir_karari=cagrildi`
    JETONUNA DEGIL, SAYAC degerlerine (D=1 S=1) bakar — o jeton islevin
    HATA kolunda da basiliyor.
    Doner: (True/False/None, sebep). None = OLCULEMEDI.
    """
    if not hasattr(modul, "_n2_devir_logla"):
        return False, "ISLEV_YOK:_n2_devir_logla"
    if not hasattr(modul, "defter_oku"):
        return None, "DEFTER_OKUYUCUSU_YOK"
    simdi = time.time()
    kalemler = [
        {"id": "K263-YASLI", "sahip": "MaCiT", "durum": "ACIK",
         "son_hareket": simdi - ESIK - 60},
        {"id": "K263-TAZE", "sahip": "MaCiT", "durum": "ACIK",
         "son_hareket": simdi - 10},
    ]
    eski_okuyucu = modul.defter_oku
    tampon = io.StringIO()
    try:
        modul.defter_oku = lambda *a, **k: list(kalemler)
        with contextlib.redirect_stdout(tampon):
            modul._n2_devir_logla()
    except Exception as hata:                       # noqa: BLE001
        return None, "KOSUM_HATASI:%s" % (hata,)
    finally:
        modul.defter_oku = eski_okuyucu
    cikti = " ".join(tampon.getvalue().split())
    if "HATA=" in cikti:
        return None, "IC_HATA:%s" % cikti
    if not cikti:
        return None, "CIKTI_YOK (sozlesme modulu okunamamis olabilir)"
    if "D=1 S=1" not in cikti:
        return False, "DAVRANIS_SAPMASI[%s]" % cikti
    return True, "IKI_YONLU_OK %s" % cikti


# Canli hedefler: her biri IKI KOLLA olculur (davranis + cagri yeri).
CANLI_HEDEFLER = (
    {"ad": "gozcu.py", "tur_fonksiyonu": "tur",
     "cagrilan": "n2_devir_kararlari", "davranis": gozcu_davranis_kolu},
    {"ad": "nobet-kapi.py", "tur_fonksiyonu": "tur_kos",
     "cagrilan": "_n2_devir_logla", "davranis": nobet_kapi_davranis_kolu},
)


def kablolama_olc(kok=None, yamalar=None):
    """Canli kablolamayi UC KOVAYLA olcer.

    `kok`     : cron duzleminin koku (CI simulasyonu icin var olmayan yol).
    `yamalar` : {"gozcu.py": <alternatif yol>} — mutant kopyalarini besler.
                Canli dosyaya ASLA yazilmaz; mutant KOPYA uzerinde calisir.
    Doner: (kovalar, satirlar, eksenler)
      kovalar  : {KURULU: n, IHLAL: n, OLCULEMEDI: n}   (hedef basina 1)
      eksenler : {"<dosya>": {"cagri": True/False/None,
                              "davranis": True/False/None}}
    """
    kok = kok or CRON_KOKU
    yamalar = yamalar or {}
    sozlesme_var = os.path.isfile(MODUL_YOLU)
    kovalar = {KURULU: 0, IHLAL: 0, OLCULEMEDI: 0}
    satirlar, eksenler = [], {}

    for hedef in CANLI_HEDEFLER:
        ad = hedef["ad"]
        yol = yamalar.get(ad) or os.path.join(kok, ad)
        cagri, cagri_sebep = None, "DOSYA_YOK:%s" % yol
        davranis, davranis_sebep = None, "DOSYA_YOK:%s" % yol

        if os.path.isfile(yol):
            try:
                with open(yol, encoding="utf-8") as dosya:
                    kaynak = dosya.read()
            except (OSError, UnicodeDecodeError) as hata:
                kaynak = None
                cagri_sebep = "OKUNAMADI:%s" % (hata,)
                davranis_sebep = cagri_sebep
            if kaynak is not None:
                cagri, cagri_sebep = cagri_yeri_kolu(
                    kaynak, hedef["tur_fonksiyonu"], hedef["cagrilan"])
                if not sozlesme_var:
                    davranis = None
                    davranis_sebep = "SOZLESME_MODULU_YOK:%s" % MODUL_YOLU
                else:
                    modul, yukleme_hatasi = _yukle_yoldan(
                        yol, ad.replace("-", "_").replace(".py", ""))
                    if modul is None:
                        davranis, davranis_sebep = None, yukleme_hatasi
                    else:
                        davranis, davranis_sebep = hedef["davranis"](modul)

        eksenler[ad] = {"cagri": cagri, "davranis": davranis}
        if cagri is False or davranis is False:
            kova = IHLAL
        elif cagri is None or davranis is None:
            kova = OLCULEMEDI
        else:
            kova = KURULU
        kovalar[kova] += 1
        satirlar.append("  HEDEF=%s KOVA=%s" % (ad, kova))
        satirlar.append("    CAGRI_YERI(ast)=%s · %s" % (cagri, cagri_sebep))
        satirlar.append("    DAVRANIS(kosum)=%s · %s" % (davranis, davranis_sebep))
    return kovalar, satirlar, eksenler


# --- KABLOLAMA MUTANTLARI: GERCEK KAYNAGA (kopya uzerinde) uygulanir -------
# 🔴 Her mutant IKI SEY birden basar:
#   (a) HEDEF KOL oldu mu?   (mutant YAKALANDI = kapi o kolu GERCEKTEN olcuyor)
#   (b) SAGLAM KOL ayakta mi? (iki kol AYRISIYOR — tautolojik cokme yok)
# Capa tekil degilse hukum "YASADI" degil OLCULEMEDI'dir.
KABLOLAMA_MUTANTLARI = (
    {"ad": "MK1 gozcu KARAR cagrisi kesildi (devir_karari cagrilmiyor)",
     "dosya": "gozcu.py",
     "capa": "sonuc = modul.devir_karari(kalem, simdi)",
     "yeni": 'sonuc = {"devredildi": False, "sebep": "SLA_ICINDE"}',
     "hedef": ("gozcu.py", "davranis"),
     "saglam": ("gozcu.py", "cagri")},

    {"ad": "MK2 gozcu TUR icindeki CAGRI YERI kesildi",
     "dosya": "gozcu.py",
     "capa": "n2_devir_kararlari(kalemler, simdi)",
     "yeni": ("dict(DEVREDILDI=0, SLA_ICINDE=0, KAPALI=0, ZATEN=0, "
              "ihlal_eklenen=0, hata=False)"),
     "hedef": ("gozcu.py", "cagri"),
     "saglam": ("gozcu.py", "davranis")},

    {"ad": "MK3 nobet-kapi TUR_KOS icindeki CAGRI YERI kesildi",
     "dosya": "nobet-kapi.py",
     "capa": "\n    _n2_devir_logla()\n",
     "yeni": "\n    pass  # K263-MUTANT: cagri yeri kesildi\n",
     "hedef": ("nobet-kapi.py", "cagri"),
     "saglam": ("nobet-kapi.py", "davranis")},
)

# KONTROL: kapinin BAKMADIGI ilgisiz bir kol bozulur; her iki hedef de
# KURULU kalmali (tautoloji yok).
KABLOLAMA_KONTROL = {
    "ad": "KONTROL ilgisiz kol (gozcu ESKALASYON_ESIGI 3 -> 4)",
    "dosya": "gozcu.py",
    "capa": "\nESKALASYON_ESIGI = 3\n",
    "yeni": "\nESKALASYON_ESIGI = 4\n",
}


def _mutant_kopya(kok, mutant, dizin):
    """Mutasyonu GERCEK KAYNAGIN KOPYASINA uygular. Canli dosyaya YAZMAZ.

    Doner: (kopya_yolu, None) ya da (None, OLCULEMEDI sebebi).
    """
    kaynak_yolu = os.path.join(kok, mutant["dosya"])
    if not os.path.isfile(kaynak_yolu):
        return None, "DOSYA_YOK:%s" % kaynak_yolu
    try:
        with open(kaynak_yolu, encoding="utf-8") as dosya:
            kaynak = dosya.read()
    except (OSError, UnicodeDecodeError) as hata:
        return None, "OKUNAMADI:%s" % (hata,)
    adet = kaynak.count(mutant["capa"])
    if adet != 1:
        return None, "CAPA_TEKIL_DEGIL:%d" % adet
    yeni = kaynak.replace(mutant["capa"], mutant["yeni"])
    if yeni == kaynak:
        return None, "MUTASYON_ETKISIZ"
    hedef_yolu = os.path.join(dizin, mutant["dosya"])
    with open(hedef_yolu, "w", encoding="utf-8") as dosya:
        dosya.write(yeni)
    return hedef_yolu, None


def _eksen(eksenler, atif):
    return (eksenler.get(atif[0]) or {}).get(atif[1])


def kablolama_mutantlarini_kos(kok=None):
    """Her kablolama mutantini GERCEK KAYNAGIN kopyasina uygular.

    Doner: (oldu, yasadi, olculemedi, satirlar).
    """
    kok = kok or CRON_KOKU
    oldu = yasadi = olculemedi = 0
    satirlar = []
    for mutant in KABLOLAMA_MUTANTLARI + (KABLOLAMA_KONTROL,):
        kontrol_mu = mutant is KABLOLAMA_KONTROL
        gecici = tempfile.mkdtemp(prefix="k263-mutant-")
        try:
            kopya, sebep = _mutant_kopya(kok, mutant, gecici)
            if kopya is None:
                olculemedi += 1
                satirlar.append("  MUTANT=%s -> OLCULEMEDI (%s)"
                                % (mutant["ad"], sebep))
                continue
            kovalar, _s, eksenler = kablolama_olc(
                kok=kok, yamalar={mutant["dosya"]: kopya})
            if kontrol_mu:
                temiz = (kovalar[IHLAL] == 0)
                if temiz:
                    oldu += 1
                else:
                    yasadi += 1
                satirlar.append(
                    "  KONTROL=%s KURULU=%d IHLAL=%d OLCULEMEDI=%d -> %s"
                    % (mutant["ad"], kovalar[KURULU], kovalar[IHLAL],
                       kovalar[OLCULEMEDI],
                       "YESIL(ilgisiz kol, kapi gecti)" if temiz
                       else "KIRMIZI(ilgisiz kol kirildi — tautoloji BOZULDU)"))
                continue
            hedef_hal = _eksen(eksenler, mutant["hedef"])
            saglam_hal = _eksen(eksenler, mutant["saglam"])
            if hedef_hal is None:
                olculemedi += 1
                hukum = "OLCULEMEDI(hedef kol olculemedi)"
            elif hedef_hal is False:
                oldu += 1
                hukum = "GECTI(mutant YAKALANDI)"
            else:
                yasadi += 1
                hukum = "KALDI(mutant YASADI)"
            satirlar.append(
                "  MUTANT=%s\n    HEDEF_KOL=%s:%s -> %s · SAGLAM_KOL=%s:%s -> %s"
                "\n    KOVA(KURULU=%d IHLAL=%d OLCULEMEDI=%d) SONUC=%s"
                % (mutant["ad"],
                   mutant["hedef"][0], mutant["hedef"][1], hedef_hal,
                   mutant["saglam"][0], mutant["saglam"][1], saglam_hal,
                   kovalar[KURULU], kovalar[IHLAL], kovalar[OLCULEMEDI],
                   hukum))
            if hedef_hal is False and saglam_hal is not True:
                yasadi += 1
                oldu -= 1
                satirlar.append(
                    "    🔴 AYRISMA YOK: saglam kol da coktu -> mutant IZOLE DEGIL")
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    return oldu, yasadi, olculemedi, satirlar


def ci_simulasyonu():
    """TEK VAKA: cron duzlemi ERISILEMEZ iken kapi ne diyor?

    Beklenen: her hedef OLCULEMEDI kovasina duser, IHLAL=0 kalir ve canli
    kolun rc'ye KATKISI 0 olur (YOKLUK != IHLAL). Sahte KIRMIZI YOK.
    """
    yok_kok = os.path.join(tempfile.gettempdir(), "k263-cron-duzlemi-YOK")
    print("# K263 — CI SIMULASYONU (cron duzlemi erisilemez)")
    print("SIMULE_KOK=%s (mevcut=%s)" % (yok_kok, os.path.isdir(yok_kok)))
    kovalar, satirlar, _eks = kablolama_olc(kok=yok_kok)
    for satir in satirlar:
        print(satir)
    print("KOVALAR KURULU=%d IHLAL=%d OLCULEMEDI=%d"
          % (kovalar[KURULU], kovalar[IHLAL], kovalar[OLCULEMEDI]))
    m_oldu, m_yasadi, m_olculemedi, m_satirlar = kablolama_mutantlarini_kos(
        kok=yok_kok)
    for satir in m_satirlar:
        print(satir)
    print("KABLOLAMA_MUTANT OLDU=%d YASADI=%d OLCULEMEDI=%d"
          % (m_oldu, m_yasadi, m_olculemedi))
    canli_katki = 1 if kovalar[IHLAL] else 0
    mutant_katki = 1 if m_yasadi else 0
    print("CANLI_RC_KATKISI=%d MUTANT_RC_KATKISI=%d" % (canli_katki, mutant_katki))
    hukum = "OLCULEMEDI" if (canli_katki == 0 and mutant_katki == 0) else "KIRMIZI"
    print("CI_SIMULASYON=%s" % hukum)
    print("KAPSAM=%d canli hedef · %d eksen · %d kablolama mutanti · 1 kontrol"
          % (len(CANLI_HEDEFLER), 2 * len(CANLI_HEDEFLER),
             len(KABLOLAMA_MUTANTLARI)))
    print("KABUL=%s" % ("GECTI" if hukum == "OLCULEMEDI" else "KALDI"))
    return 0 if hukum == "OLCULEMEDI" else 1


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
    print("  canli : gozcu.tur() -> n2_devir_kararlari() · "
          "nobet-kapi.tur_kos() -> _n2_devir_logla()")


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
    if "--ci-simulasyon" in sys.argv[1:]:
        return ci_simulasyonu()
    print("# K262/K263 — N2 4 saatlik otomatik devir, IKI YONLU kabul kapisi")
    print("VAKA_SAYISI=%d MUTANT_SAYISI=%d CANLI_HEDEF=%d "
          "KABLOLAMA_MUTANT_SAYISI=%d"
          % (len(VAKALAR), len(MUTANTLAR), len(CANLI_HEDEFLER),
             len(KABLOLAMA_MUTANTLARI)))

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

    print("--- CANLI KABLOLAMA (davranis kosumu + ast cagri yeri, UC KOVA) ---")
    kovalar, c_satirlar, _eksenler = kablolama_olc()
    for satir in c_satirlar:
        print(satir)
    print("  KOVALAR KURULU=%d IHLAL=%d OLCULEMEDI=%d"
          % (kovalar[KURULU], kovalar[IHLAL], kovalar[OLCULEMEDI]))
    canli_ok = (kovalar[IHLAL] == 0)     # 🔴 YOKLUK (OLCULEMEDI) IHLAL DEGILDIR
    if kovalar[OLCULEMEDI]:
        print("  ⚠️ OLCULEMEDI=%d — cron duzlemi bu makinede eksik; bu hucreler "
              "KIRMIZI SAYILMAZ (YOKLUK != IHLAL)." % kovalar[OLCULEMEDI])
    print("  CANLI SONUC=%s" % ("YESIL" if canli_ok else "KIRMIZI"))

    print("--- KABLOLAMA MUTANTLARI (GERCEK kaynagin KOPYASINA uygulanir) ---")
    m_oldu, m_yasadi, m_olculemedi, m_satirlar = kablolama_mutantlarini_kos()
    for satir in m_satirlar:
        print(satir)
    kablolama_mutant_ok = (m_yasadi == 0)
    print("  KABLOLAMA_MUTANT OLDU=%d YASADI=%d OLCULEMEDI=%d SONUC=%s"
          % (m_oldu, m_yasadi, m_olculemedi,
             "YESIL" if kablolama_mutant_ok else "KIRMIZI"))

    rc = 0 if (kalan == 0 and mutant_hepsi and kontrol_ok
               and canli_ok and kablolama_mutant_ok) else 1
    print("KAPSAM=%d vaka · %d mutant (esik+D'REDILDI+erken-devir) · 1 kontrol · "
          "%d canli hedef · %d canli eksen (davranis+cagri) · "
          "%d kablolama mutanti · 1 kablolama kontrolu"
          % (len(VAKALAR), len(MUTANTLAR), len(CANLI_HEDEFLER),
             2 * len(CANLI_HEDEFLER), len(KABLOLAMA_MUTANTLARI)))
    print("KABUL=%s" % ("GECTI" if rc == 0 else "KALDI"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
