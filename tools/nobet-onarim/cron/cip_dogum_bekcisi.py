#!/usr/bin/env python3
"""PRUVO CIP-DOGUM BEKCISI — "bugunun Tamirci cipi DOGDU MU?" SEVIYE sorusu.

NEDEN VAR (26 Agu 2026, Okan isteği, BaBa yonu):
Yeni Tamirci duzeninin basarisizlik bicimi K311'in AYNISI — `kral-sabah.py` bir
sabah atesLEMEZSE cip DOGMAZ ve HICBIR KOL bunu goremez. Kenar-tetikli kollar
(yeni kirmizi geldi mi / yeni satir dustu mu) bu olayi URETMEZ: ortada bir OLAY
yoktur, bir YOKLUK vardir. Yokluk ancak SEVIYE sorulunca gorulur
([[kenar-tetikli-kol-seviye-sorusunu-cevaplayamaz]]).

DESEN (BaBa, baglayici): YENI BAGIMSIZ CRON SATIRI ACILMAZ — bekciyi bekleyen
bekci sarmali olur, yeni satir da sessiz olur. Bu modul, ZATEN KANITLI ATESLEYEN
bir hatta (`gozcu.py`, crontab `8,23,38,53` = 96 tur/gun) ILISTIRILIR. Sifir
jeton, LLM turu YOK.

DOGUM KANITI — TEK EKSEN (secim gerekcesi burada kalir):
  ~/.claude/cron/tamirci-spec/KraL-Tamirci-<YYYYAAGG>.md  (tarihli spec dosyasi)
Rutinin LOG SATIRI eksen olarak SECILMEDI: log satiri DENEMEYI olcer, dosya
SONUCU olcer. `kral-sabah.py` kosup girdilerinden birini okuyamazsa yine bir log
satiri duser ama cipin tuketecegi spec eksik/uretilmemis olabilir; log ekseni o
halde YESIL yanardi. Cipin FIILEN tukettigi artefakt bu dosyadir. IKI eksen
okuyan bekci = IKI bakim noktasi = sessiz ayrisma; bu yuzden TEK eksen.

KURAL:
  yerel saat >= ESIK_SAAT  VE  bugunun dogum kaniti YOK  ->  KIRMIZI + BILDIRIM
  yerel saat <  ESIK_SAAT                                ->  PENCERE_DISI (SESSIZ)
  kanit VAR                                              ->  YESIL (SESSIZ)
  kanit dizini/saat okunamadi                            ->  OLCULEMEDI (KIRMIZI sayilir)

FAIL-CLOSED: `OLCULEMEDI` YESIL DEGILDIR — cagiran rc'yi yukseltir.

BILDIRIM TEKILLIGI: gun basina EN FAZLA 1 bildirim. Damga dosyasi
`O_CREAT|O_EXCL` ile atomik konur; ayni gun ikinci cagri bildirim GONDERMEZ
(96 tur/gun x 1 banner = spam olurdu). Damga YAZILAMAZSA bildirim GONDERILMEZ
(fail-closed: veremedigimiz tekillik garantisini "verdik" saymayiz).

URETEN TEMIZLER (Okan, USTUN kural): damgalar `DAMGA_YAS_ESIGI_SN` sonrasi
silinir; bu modul baska hicbir dosyaya dokunmaz.

Kabul: python3 <kaynak>/bekci-kabul.py
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"

# --- sabitler (TEK KAYNAK) --------------------------------------------------
KANIT_DIZINI = os.path.join(CRON_KOKU, "tamirci-spec")
KANIT_KALIBI = "KraL-Tamirci-%s.md"          # %s = YYYYAAGG (yerel tarih)
ASGARI_BOYUT = 1                              # bayt; 0 baytlik dosya KANIT DEGIL
ESIK_SAAT = 9                                 # yerel saat; 09:00 oncesi SESSIZ

DAMGA_DIZINI = os.path.join(CRON_KOKU, "bekci-damga")
DAMGA_SONEKI = ".bildirildi"
DAMGA_YAS_ESIGI_SN = 14 * 86400
BILDIRIM_LOG = os.path.join(CRON_KOKU, "bekci-bildirim.log")

OSASCRIPT = "/usr/bin/osascript"
TERMINAL_NOTIFIER_ADAYLARI = (
    "/opt/homebrew/bin/terminal-notifier",
    "/usr/local/bin/terminal-notifier",
    "/Users/okan/.local/bin/terminal-notifier",
)

# 🔴 KANAL HUKMU — 26 Agu 2026, TATBIKATTA OLCULDU (bedeli Okan'in ekrani oldu).
# `osascript -e 'display notification ...'` bildirimin SAHIBINI **Script Editor**
# yapar. Uygulama daha once acilmamissa macOS onu BASLATIR ve Script Editor
# acilista iCloud BELGE SECICI PENCERESI gosterir. Yani kanal "sessiz banner"
# degil, **GUI PENCERESI** uretir. 96 tur/gun bir hatta baglanacak bir kol icin
# bu kabul EDILEMEZ ([[okan-kapisi-tikla-hazir-sunum]] — Okan'a is birakilmaz).
#
# OLCULEN ADAYLAR (26 Agu):
#   · terminal-notifier / alerter : UC yolun HICBIRINDE YOK (kurulumu Okan kapisi
#                                   + makinede kalici iz -> [[diskte-iz-birakma-yasagi]])
#   · osascript (duz)             : RED — Script Editor penceresi (yukarida)
#   · osascript + "tell app Finder": DENENMEDI — ilk kullanimda Automation TCC
#                                   penceresi dusurme riski var; "pencere
#                                   dusurmedigini" olcmenin yolu pencere
#                                   dusurmekten geciyor. Mimar karari beklenir.
#
# 🔴 VARSAYILAN "YOK" — FAIL-CLOSED VE SESSIZ: kol TESPITI yapar (KIRMIZI + rc +
# kalp alani + log satiri), ama EKRANA hicbir sey dusurmez. Teslim ayagi bilerek
# `OLCULEMEDI`dir; SAHTE YESIL YAZILMAZ. Teslim, Okan'in ZATEN okudugu kanaldan
# (gunluk 15:00 zamanlanmis gorevi `gozcu-kalp.json`daki `bekci_hukum` alanini
# okur) gider. Kanal degistirilecekse BU SABIT degistirilir ve kabul bataryasi
# `C-GUI` kolunu YENIDEN kosar.
KANALLAR = ("YOK", "terminal-notifier", "osascript", "cip")
# 🔴 27 Agu 2026 OKAN KARARI: teslim kanali CIP. Gerekce OLCULMUS —
# bugun Okan'a ULASTIGI KANITLANMIS tek kanal paneldir.
BILDIRIM_KANALI = "cip"

BILDIRIM_BASLIGI = "PRUVO — cip dogmadi"
# Teslim sondasinin arayacagi jeton. Bildirim govdesinde AYNEN gecer.
BILDIRIM_JETONU = "PRUVO-BEKCI"
# macOS Notification Center kaydi (teslim sondasi). Okunamazsa OLCULEMEDI.
USERNOTED_DB = os.path.expanduser(
    "~/Library/Group Containers/group.com.apple.usernoted/db2/db")

HUKUMLER = ("PENCERE_DISI", "YESIL", "KIRMIZI", "OLCULEMEDI")

# --- TESLIM KOLUNUN KENDI OLCUMU (26 Agu 2026, mimar ek maddesi) -----------
# 🔴 NEDEN: bekcinin TESPITI makinede (bu modul), TESLIMI ise gunluk 15:00
# zamanlanmis gorevindedir (`gunluk-mimar-ihtar` -> `ADIM 0`). Teslim ayagi
# (a) gorevin KOSMASINA ve (b) SKILL.md'deki ADIM 0 blogunun DURMASINA baglidir.
# Ikisinden biri SESSIZCE giderse "bekci yesil ama sesi kimseye ulasmiyor" hali
# dogar — bu tam olarak K311'in bir kat YUKARIDA yeniden kurulmasidir.
# CARE YENI BEKCI DEGIL (sarmal yasak): ayni kol iki alani KENDI olcer ve
# ikisinden biri olu/bayatsa hukum `OLCULEMEDI`ye duser (rc zaten yukselir).
# 🔴 IKI KOL (26 Agu 2026, ikinci kol eklendi). Tek kolluyken teslim ayagi TEK
# NOKTAYA baglilydi: `gunluk-mimar-ihtar` devre disi kalirsa/metni degisirse ses
# tamamen kesiliyordu. Simdi iki BAGIMSIZ zamanlanmis gorev tasiyor:
#   IHTAR  15:00        · TEFTIS 17:00 + 23:00
# Yedeklilik hukmu: `saglam = EN AZ BIR kol sag` — cunku soru "ses Okan'a
# ULASIYOR MU"dur; bir kol olse de oteki ulastirir. AMA olu kol GIZLENMEZ:
# `sebep` `SAG_1/2_OLU:<id>` yazar ve AYAKTA KALAN kol bunu KraL'in blogunda
# bakim kalemi olarak basar. Ikisi birden olurse hukum `OLCULEMEDI` -> rc yukselir.
# 🔴 rc'yi YALNIZ "hicbir kol sag degil" yukseltir; tek olu kol yanlis-pozitif
# kirmizi uretmez ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).
# 🔴 27 AGU 2026 — TAVAN TURETILIR, ELLE KOPYALANMAZ.
# Sinif [[K316]] ile AYNI: turetilebilir bir degerin elle kopyalanmasi ve
# kaynagindan sessizce ayrismasi. Her kolun TEK KAYNAGI kendi `saatler`
# demetidir; tavan ondan HESAPLANIR:
#     tavan = EN GENIS SESSIZLIK PENCERESI + PAY
# Bir kacirilan kosum en genis bosluk kadar sessizlik uretir; PAY makine
# uykusu/jitter payidir. DOGRULAMA (regresyon YOK — sayilar DEGISMEDI):
#     TEFTIS (17,23) -> bosluklar 6/18 -> 18+12 = 30  (ESKI SABIT ILE AYNI)
#     IHTAR  ( 9,15) -> bosluklar 6/18 -> 18+12 = 30  (ESKI SABIT ILE AYNI)
# Degisen sey SAYI degil, gerekcenin TEK KAYNAGA baglanmasidir.
TESLIM_PAY_SAAT = 12

# 🔴 SABAH SAATI ESIKTEN TURER — IKIZ SAYI YOK. Kol esikten ONCE atesLERSE
# (or. 08:59) hukum PENCERE_DISI olur ve sabah SESSIZ gecer; bu, 27 Agu
# arizasinin kardesidir. Baglama burada YAPISAL olarak kapatilir.
TESLIM_SABAH_SAATI = ESIK_SAAT


def en_genis_bosluk(saatler):
    """Gunluk kosum saatlerinden EN GENIS sessizlik penceresi (saat)."""
    s = sorted({int(h) % 24 for h in saatler})
    if len(s) <= 1:
        return 24.0
    araliklar = [s[i + 1] - s[i] for i in range(len(s) - 1)]
    araliklar.append(24 - s[-1] + s[0])
    return float(max(araliklar))


def kol_tavani(saatler, pay=None):
    """TEK FORMUL. `tavan_saat` alani BUNDAN doldurulur, elle YAZILMAZ."""
    return en_genis_bosluk(saatler) + (TESLIM_PAY_SAAT if pay is None else pay)


TESLIM_KOLLARI = (
    {"id": "IHTAR",
     "kanca": "/Users/okan/.claude/scheduled-tasks/gunluk-mimar-ihtar/SKILL.md",
     "jeton": "ADIM 0 — ÇİP-DOĞUM BEKÇİSİ",
     # 🔴 27 Agu 2026 OKAN TASARIMI: IHTAR gunde 1 -> 2 kosum.
     #   09:00 = SABAH gozden gecirmesi (bugunun cipi dogdu mu) — TESLIM KOLU
     #   15:00 = mevcut gunluk mimar ihtari
     # Sabah saati `TESLIM_SABAH_SAATI` (= ESIK_SAAT) uzerinden gelir.
     "saatler": (TESLIM_SABAH_SAATI, 15),
     "tavan_saat": kol_tavani((TESLIM_SABAH_SAATI, 15))},
    {"id": "TEFTIS",
     "kanca": "/Users/okan/.claude/scheduled-tasks/teftis-takip/SKILL.md",
     # 🔴 AYRI JETON: teftis-takip'in KENDI "ADIM 0"i (erteleme kontrolu) zaten
     # var; ayni jetonu kullanmak iki blogu birbirine karistirir.
     "jeton": "ADIM 00 — ÇİP-DOĞUM BEKÇİSİ",
     "saatler": (17, 23),
     "tavan_saat": kol_tavani((17, 23))},
)
TESLIM_KALP_YOLU = os.path.join(CRON_KOKU, "bekci-teslim-kalp.md")
# Kol id'si TASIMAYAN eski/tohum damgalari icin taban tavan.
TESLIM_BAYATLIK_SAAT = 30

# Damga bicimleri (UCU DE OKUNUR):
#   KOSTU=<KOL_ID>@<ISO>Z  -> o KOLA ait kosum damgasi (yeni bicim)
#   KOSTU=<ISO>Z           -> ESKI bicim; yalniz IHTAR'a yazdirilmisti, ONA sayilir
#   KURULDU=<ISO>Z         -> kurulum TOHUMU; HER kola sayilir (sayac baslangici,
#                             muafiyet DEGIL — ayni tavana tabi)
_TESLIM_KOL_DESENI = re.compile(
    r"^KOSTU=([A-Z_]+)@(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z", re.M)
_TESLIM_ESKI_DESENI = re.compile(
    r"^KOSTU=(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z", re.M)
_TESLIM_TOHUM_DESENI = re.compile(
    r"^KURULDU=(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z", re.M)
# Eski bicim damgasinin sahibi (geriye donuk atif; yeni yazimlar id tasir).
TESLIM_ESKI_BICIM_SAHIBI = "IHTAR"


# --- saf karar --------------------------------------------------------------

def kanit_adi(yerel_tarih):
    """Dogum kanitinin dosya ADI. Tek yerde uretilir."""
    return KANIT_KALIBI % yerel_tarih.strftime("%Y%m%d")


def kanit_yolu(yerel_tarih, dizin=None):
    return os.path.join(dizin or KANIT_DIZINI, kanit_adi(yerel_tarih))


def kanit_olc(yerel_tarih, dizin=None):
    """(var_mi, yol, boyut). Dizin YOKSA (var=False, boyut=-1) — cagiran
    bunu 'kanit yok' sayar; dizinin kendisinin okunamamasi AYRI kolda
    (`_dizin_okunur_mu`) OLCULEMEDI'ye gider."""
    yol = kanit_yolu(yerel_tarih, dizin)
    try:
        if not os.path.isfile(yol):
            return False, yol, -1
        boyut = os.path.getsize(yol)
    except OSError:
        return False, yol, -1
    return boyut >= ASGARI_BOYUT, yol, boyut


def _dizin_okunur_mu(dizin=None):
    """Kanit dizini var VE listelenebiliyor mu. Yoksa OLCULEMEDI kolu acilir:
    'dizini goremedim' ile 'dizin bos' AYNI SEY DEGILDIR."""
    dizin = dizin or KANIT_DIZINI
    try:
        os.listdir(dizin)
        return True
    except OSError:
        return False


def _yas_saat(damga, simdi):
    """ISO damgasini SAAT yasina cevirir. `None` = cozulemedi.

    🔴 `None` = DAMGA YOK/OKUNAMADI; NEGATIF YAS ILE KARISTIRILMAZ. Olculdu
    (26 Agu): sentetik `simdi` damganin GERISINDE oldugunda yas negatif cikiyor
    ve "-1 ise yok" kisayolu onu KALP_YOK sayip 16 fiksturu birden dusurdu.
    Damga simdinin ILERISINDEYSE kalp TAZEDIR (0 saat), YOK DEGIL — makine saat
    kaymasi da ayni kola duser.
    """
    try:
        an = dt.datetime.strptime(damga, "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=dt.timezone.utc)
        return max(0.0, (simdi - an.timestamp()) / 3600.0)
    except (ValueError, OverflowError, TypeError):
        return None


def _kalp_damgalari(kalp_yolu):
    """Kalp dosyasini AYRISTIRIR. Doner: (kol_id -> [ISO...], tohum [ISO...])."""
    try:
        with open(kalp_yolu, encoding="utf-8") as dosya:
            metin = dosya.read()
    except OSError:
        return {}, []
    kol_damgalari = {}
    for kol_id, damga in _TESLIM_KOL_DESENI.findall(metin):
        kol_damgalari.setdefault(kol_id, []).append(damga)
    for damga in _TESLIM_ESKI_DESENI.findall(metin):
        kol_damgalari.setdefault(TESLIM_ESKI_BICIM_SAHIBI, []).append(damga)
    return kol_damgalari, _TESLIM_TOHUM_DESENI.findall(metin)


def _tek_kol_olc(kol, kol_damgalari, tohumlar, simdi, bayatlik_saat=None):
    """TEK teslim kolunun sagligi. Doner: {id, kanca, kalp_saat, sag, sebep}."""
    tavan = float(kol.get("tavan_saat") or TESLIM_BAYATLIK_SAAT)
    if bayatlik_saat is not None:
        tavan = float(bayatlik_saat)

    try:
        with open(kol["kanca"], encoding="utf-8") as dosya:
            kanca = 1 if kol["jeton"] in dosya.read() else 0
    except OSError:
        kanca = 0

    # Kolun kendi damgalari + TOHUM (tohum her kola sayilir, ayni tavana tabi).
    adaylar = list(kol_damgalari.get(kol["id"], [])) + list(tohumlar)
    yaslar = [y for y in (_yas_saat(d, simdi) for d in adaylar) if y is not None]
    kalp_saat = min(yaslar) if yaslar else None
    bildirilen = -1.0 if kalp_saat is None else kalp_saat

    if not kanca:
        return {"id": kol["id"], "kanca": 0, "kalp_saat": bildirilen,
                "sag": False, "sebep": "KANCA_YOK"}
    if kalp_saat is None:
        return {"id": kol["id"], "kanca": 1, "kalp_saat": -1.0,
                "sag": False, "sebep": "KALP_YOK"}
    if kalp_saat > tavan:
        return {"id": kol["id"], "kanca": 1, "kalp_saat": kalp_saat,
                "sag": False, "sebep": "KALP_BAYAT_%.0fh" % kalp_saat}
    return {"id": kol["id"], "kanca": 1, "kalp_saat": kalp_saat,
            "sag": True, "sebep": "SAG"}


def teslim_kanali_olc(simdi=None, kollar=None, kalp_yolu=None,
                      bayatlik_saat=None):
    """TESLIM KOLLARI SAG MI (coklu kol). Doner sozluk:
        {kanca, kalp_saat, saglam, sebep, kollar, olu}
      · `kanca`     : SAG KANCA SAYISI (0..N)
      · `kalp_saat` : SAG kollar arasindaki EN TAZE yas (saat; -1 = hicbiri yok)
      · `saglam`    : **EN AZ BIR** kol tam sag mi (soru: ses ULASIYOR MU)
      · `sebep`     : `SAG_2/2` · `SAG_1/2_OLU:TEFTIS` · `OLU_IHTAR:KANCA_YOK+...`
      · `kollar`    : kol basina kirilim (id/kanca/kalp_saat/sag/sebep)
      · `olu`       : olu kol id'leri (sag olsa bile BASILIR — gizlenmez)
    FAIL-CLOSED: okunamayan her sey o kol icin `sag=False`. "Olcemedim" SAG
    DEMEK DEGIL. Hicbir kol sag degilse `saglam=False` -> hukum OLCULEMEDI.
    """
    simdi = simdi if simdi is not None else time.time()
    kollar = kollar or TESLIM_KOLLARI
    kalp_yolu = kalp_yolu or TESLIM_KALP_YOLU

    kol_damgalari, tohumlar = _kalp_damgalari(kalp_yolu)
    olculen = [_tek_kol_olc(k, kol_damgalari, tohumlar, simdi, bayatlik_saat)
               for k in kollar]

    saglar = [k for k in olculen if k["sag"]]
    olu = [k["id"] for k in olculen if not k["sag"]]
    toplam = len(olculen)
    taze = [k["kalp_saat"] for k in saglar if k["kalp_saat"] >= 0]

    if not saglar:
        # Hicbir kol sag DEGIL -> ses kimseye ulasmiyor. Sebep kol kol yazilir.
        detay = "+".join("%s:%s" % (k["id"], k["sebep"]) for k in olculen) or "KOL_YOK"
        return {"kanca": 0, "kalp_saat": -1.0, "saglam": False,
                "sebep": "OLU_%s" % detay, "kollar": olculen, "olu": olu}

    if olu:
        # Ses ULASIYOR (yedeklilik is gordu) ama bir kol OLMUS — rc yukselmez,
        # AMA gizlenmez: ayakta kalan kol bunu bakim kalemi olarak basar.
        return {"kanca": len(saglar), "kalp_saat": min(taze) if taze else -1.0,
                "saglam": True,
                "sebep": "SAG_%d/%d_OLU:%s" % (len(saglar), toplam, ",".join(olu)),
                "kollar": olculen, "olu": olu}

    return {"kanca": len(saglar), "kalp_saat": min(taze) if taze else -1.0,
            "saglam": True, "sebep": "SAG_%d/%d" % (len(saglar), toplam),
            "kollar": olculen, "olu": []}


# ============================================================================
# DOGUM EKSENI — K331 (28 Agu 2026, `KraL-OnarimZinciri-28Agu`)
# ----------------------------------------------------------------------------
# 🔴 OLCULEN ARIZA: `kanit_olc()` TEK EKSEN olcuyordu (spec dosyasi VAR MI +
# boyut >= ASGARI_BOYUT) ve `karar()` bundan "cip DOGMUS" sonucunu cikariyordu.
# Yani mekanizma yalnizca *"spec URETILEMEDI"* halini gorebiliyordu; *"spec
# URETILDI ama KOSULMADI"* hali YAPISAL OLARAK GORUNMEZDI.
# CANLI VAKA (28 Agu): spec 17.606 B @06:20 URETILDI, bekci `YESIL/KANIT_VAR`
# dedi -> `GEREKSIZ` -> cip HIC DOGMADI, gun kayitsiz kapandi.
#
# 🔴 AD SECIMI — `teslim` DEGIL `dogum`: bu dosyada `teslim` ADI ZATEN KANAL
# SAGLIGINI (teslim kollari/kalp) ifade ediyor. Ayni adi ikinci bir role vermek
# mutanti golgeler. Iki eksen AYRI ADLA ve AYRI ALANDA raporlanir:
# `kanit` (spec var mi) · `dogum` (cip gercekten dogdu mu).
#
# OLCUM KAYNAGI beyan degil KAYITTIR: `bekci-bildirim.log` icinde o ANAHTARA ait
# `teslim=BASARILI ... task_id=task_xxxxxx` satiri. Jeton bicimi ELLE IKINCI KEZ
# YAZILMAZ — `_TASK_ID_DESENI` tek kaynagindan dogrulanir.
_DOGUM_SATIR_DESENI = re.compile(
    r"\banahtar=(?P<anahtar>\S+)\b.*?\bteslim=BASARILI\b.*?\btask_id=(?P<task>\S+)")


def dogum_olc(anahtar, log_yolu=None):
    """CIP O ANAHTAR ICIN GERCEKTEN DOGDU MU? Doner sozluk:
        {olculdu, dogdu, task_id, sebep}
      · `olculdu=False` -> log OKUNAMADI. "Olcemedim" DOGDU DEMEK DEGIL ve
        YESIL de demek degil; cagiran bunu OLCULEMEDI'ye cevirir (fail-closed).
      · `dogdu=True`    -> kayitta `teslim=BASARILI` + GECERLI task_id VAR.
    """
    if not anahtar or anahtar == "-":
        return {"olculdu": False, "dogdu": False, "task_id": "-",
                "sebep": "ANAHTAR_YOK"}
    yol = log_yolu or BILDIRIM_LOG
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            satirlar = dosya.readlines()
    except FileNotFoundError:
        # Log dosyasinin HIC olmamasi okunamamak DEGILDIR: hicbir teslim
        # yazilmamis demektir ve bu OLCULMUS bir "dogmadi"dir.
        return {"olculdu": True, "dogdu": False, "task_id": "-",
                "sebep": "LOG_YOK"}
    except OSError as hata:
        return {"olculdu": False, "dogdu": False, "task_id": "-",
                "sebep": "LOG_OKUNAMADI_%s" % type(hata).__name__}
    for satir in satirlar:
        esles = _DOGUM_SATIR_DESENI.search(satir)
        if not esles:
            continue
        if esles.group("anahtar") != anahtar:
            continue
        jeton = esles.group("task").strip()
        if not _TASK_ID_DESENI.match(jeton):
            # Bicimsiz jeton DOGUM SAYILMAZ; `teslim_kaydet` de onu BASARISIZ
            # yazar. Aramaya devam: ayni gun gecerli bir satir olabilir.
            continue
        return {"olculdu": True, "dogdu": True, "task_id": jeton,
                "sebep": "TASK_ID_VAR"}
    return {"olculdu": True, "dogdu": False, "task_id": "-",
            "sebep": "TESLIM_SATIRI_YOK"}


def karar(simdi=None, dizin=None, esik_saat=None, yerel_cozucu=None,
          teslim_kollari=None, teslim_kalp_yolu=None, teslim_bayatlik_saat=None,
          log_yolu=None, anahtar_oneki=""):
    """SAF karar — dosya YAZMAZ, bildirim GONDERMEZ. Yalniz OKUR.

    Doner: {hukum, sebep, saat, tarih, kanit_yolu, boyut, esik, teslim, dogum}
    """
    simdi = simdi if simdi is not None else time.time()
    dizin = dizin or KANIT_DIZINI
    esik = ESIK_SAAT if esik_saat is None else int(esik_saat)
    cozucu = yerel_cozucu or (lambda e: dt.datetime.fromtimestamp(e))

    try:
        yerel = cozucu(simdi)
        saat = int(yerel.hour)
        tarih = yerel.date()
    except Exception as hata:                 # saat cozulemiyorsa SESSIZ KALMA
        return {"hukum": "OLCULEMEDI", "sebep": "SAAT_COZULEMEDI_%s" % type(hata).__name__,
                "saat": -1, "tarih": "-", "kanit_yolu": "-", "boyut": -1, "esik": esik}

    var, yol, boyut = kanit_olc(tarih, dizin)
    ad = os.path.basename(yol)

    # 🔴 0. SORU YALNIZ **BUGUN** ICIN ANLAMLIDIR (KOL_ADI=BUGUN_KOLU).
    # `gozcu.tur()` sentetik/gecmis bir `simdi` ile de cagrilabilir (gozcu-test.py
    # 1_755_000_000.0 kullanir). "O GUNUN cipi dogdu mu" sorusunun cevabi bugunden
    # okunamaz: kanit dosyalari gunluktur ve eski gunler icin diskte olmayabilir.
    # Duvar saatiyle AYNI GUNDE degilsek kol SESSIZ kalir.
    # Bu bir BYPASS DEGILDIR: kiyas sabit bir tarihe degil CANLI duvar saatine
    # yapilir — uretimde cagiran daima `time.time()` gecirir, yani bu kol uretimde
    # HIC ATESLEMEZ. Kabul: A6 (bugun -> kol ATESLEMEZ) + A7 (dun -> SESSIZ).
    try:
        bugun_duvar = cozucu(time.time()).date()
    except Exception:
        bugun_duvar = tarih
    # K331: ANAHTAR burada turer — `teslim_karari` ile AYNI kalip
    # (`anahtar_oneki` + tarih, tireler atilir). Ikinci bir bicim YAZILMAZ.
    _anahtar = "%s%s" % (anahtar_oneki, tarih.isoformat().replace("-", ""))
    taban = {"saat": saat, "tarih": tarih.isoformat(), "kanit_yolu": yol,
             "boyut": boyut, "esik": esik, "kanit_adi": ad,
             "kanit": bool(var), "anahtar": _anahtar,
             "teslim": {"kanca": -1, "kalp_saat": -1.0, "saglam": None,
                        "sebep": "OLCULMEDI", "kollar": [], "olu": []},
             "dogum": {"olculdu": None, "dogdu": None, "task_id": "-",
                       "sebep": "OLCULMEDI"}}

    def _don(hukum, sebep, teslim=None, dogum=None):
        s = dict(taban)
        if teslim is not None:
            s["teslim"] = teslim
        if dogum is not None:
            s["dogum"] = dogum
        s["hukum"] = hukum
        s["sebep"] = sebep
        return s

    if tarih != bugun_duvar:
        return _don("PENCERE_DISI", "SIMDI_BUGUN_DEGIL")

    # 🔴 0b. TESLIM KOLU SAG MI (KOL_ADI=TESLIM_KOLU).
    # Tespit dogru calissa bile SESI KIMSEYE ULASMIYORSA bekci YOK hukmundedir.
    # Bu kol o hali ISIMLENDIRIR: kanca dustuyse ya da 15:00 gorevi ~30 saattir
    # kosmadiysa hukum `OLCULEMEDI` (rc yukselir), "yesil" DEGIL.
    # 🔴 SIRA HUKUMDUR: "bugun mu" guard'indan SONRA (sentetik turlar sessiz
    # kalsin), kanit kollarindan ONCE (yesil hukum teslimsiz VERILEMESIN).
    teslim = teslim_kanali_olc(simdi, teslim_kollari, teslim_kalp_yolu,
                               teslim_bayatlik_saat)
    if not teslim["saglam"]:
        return _don("OLCULEMEDI", "TESLIM_KOLU_%s" % teslim["sebep"], teslim)

    # 1. KANIT VAR — 🔴 K331: DOSYANIN VARLIGI CIPIN DOGDUGU ANLAMINA GELMEZ.
    # Iki eksen AYRI olculur: `kanit` (spec var mi) ve `dogum` (cip dogdu mu).
    if var:
        # PENCERE ACILMADAN dogum BEKLENMEZ: spec 06:20'de uretilir, cip 09:00
        # rutininde dogar. Erken saatte "dogmadi" demek SAHTE ALARM olurdu —
        # eski davranis (YESIL/KANIT_VAR) bu aralikta AYNEN durur.
        if saat < esik:
            return _don("YESIL", "KANIT_VAR", teslim)
        dogum = dogum_olc(_anahtar, log_yolu)
        if not dogum["olculdu"]:
            # Kayit OKUNAMADI. "Olcemedim" YESIL DEGILDIR (fail-closed).
            return _don("OLCULEMEDI", "DOGUM_%s" % dogum["sebep"], teslim, dogum)
        if dogum["dogdu"]:
            return _don("YESIL", "KANIT_VAR_CIP_DOGDU", teslim, dogum)
        # Spec URETILDI ama cip KOSULMADI — K331'in gorunmez kildigi TAM HAL.
        return _don("KIRMIZI", "KANIT_VAR_CIP_DOGMADI", teslim, dogum)

    # 2. PENCERE DISI: 09:00 oncesi kanit YOKLUGU ARIZA DEGILDIR (rutin 06:20'de
    #    koşar ama makine uykuda olabilir; sahte alarm URETME).
    if saat < esik:
        return _don("PENCERE_DISI", "SAAT_%02d_ESIK_%02d" % (saat, esik), teslim)

    # 3. Dizini hic goremiyorsak "kanit yok" HUKMU VERME — olcemedik.
    if not _dizin_okunur_mu(dizin):
        return _don("OLCULEMEDI", "KANIT_DIZINI_OKUNAMADI", teslim)

    # 4. Pencere ICI + kanit YOK -> CIP DOGMADI.
    return _don("KIRMIZI", "CIP_DOGMADI", teslim)


# --- bildirim (yan etkili) --------------------------------------------------

def _as_kacir(metin):
    return str(metin).replace("\\", "\\\\").replace('"', '\\"')


def _kabuk(argv, zaman_asimi=15):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=zaman_asimi)
    except FileNotFoundError:
        return 127, "YOK (%s)" % argv[0]
    except subprocess.TimeoutExpired:
        return 124, "zaman asimi %ds" % zaman_asimi
    except Exception as hata:
        return 125, "%s: %s" % (type(hata).__name__, str(hata)[:160])
    return r.returncode, (((r.stderr or "") + (r.stdout or "")).strip()[:300] or "-")


def uygulama_bildirimi(baslik, altbaslik, mesaj, osascript=None, zaman_asimi=15,
                       kanal=None):
    """Bildirimi SECILI KANALDAN gonderir. (rc, ayrinti).

    `rc is None` = kanal YOK; hicbir sey gonderilmedi ve EKRANA HICBIR SEY
    DUSMEDI. Bu bir hata degil, OLCULMUS bir hukumdur (yukaridaki KANAL HUKMU).
    """
    kanal = kanal or BILDIRIM_KANALI

    if kanal == "cip":
        # 🔴 Bu SUREC cip DOGURAMAZ (cipi yalniz bir Claude oturumu
        # yaratabilir). Teslim `teslim_karari`/`teslim_kaydet` kolunda.
        # SOMUT rc doner: `rc=None` bir daha YAZILMAZ.
        return 0, ("KANAL=cip — teslim RUTIN kolunda "
                   "(`cip_dogum_bekcisi.py --teslim-karari`)")

    if kanal == "YOK":
        return None, ("KANAL=YOK — GUI acan kanal RED (Script Editor penceresi), "
                      "terminal-notifier kurulu DEGIL; teslim MIMAR KARARINDA")

    if kanal == "terminal-notifier":
        for aday in TERMINAL_NOTIFIER_ADAYLARI:
            if os.path.exists(aday):
                return _kabuk([aday, "-title", baslik, "-subtitle", altbaslik,
                               "-message", mesaj], zaman_asimi)
        return 127, "terminal-notifier YOK (%s)" % ", ".join(TERMINAL_NOTIFIER_ADAYLARI)

    if kanal == "osascript":
        # 🔴 GUI RISKI VAR — yalniz kabul fiksturunde (sahte ikili ile) ya da
        # mimar kararindan sonra kullanilir.
        yol = osascript or OSASCRIPT
        betik = 'display notification "%s" with title "%s" subtitle "%s"' % (
            _as_kacir(mesaj), _as_kacir(baslik), _as_kacir(altbaslik))
        return _kabuk([yol, "-e", betik], zaman_asimi)

    return 126, "BILINMEYEN KANAL=%r (izinli: %s)" % (kanal, KANALLAR)


def teslim_sondasi(jeton=None, db_yolu=None):
    """TESLIM KANITI denemesi: bildirim macOS Notification Center kaydinda
    GORUNUYOR MU. Doner: ("TESLIM_VAR"|"TESLIM_YOK"|"OLCULEMEDI", ayrinti).

    🔴 `rc=0` TESLIM DEMEK DEGILDIR — osascript'in sifir donmesi yalnizca
    "sistem cagriyi kabul etti" demektir. Bu sonda ONU dogrulamaya calisir.
    Okunamazsa (TCC izni, kilitli db, sema degisimi) `OLCULEMEDI` doner ve
    cagiran bunu SAHTE YESIL saymaz.
    """
    jeton = jeton or BILDIRIM_JETONU
    yol = db_yolu or USERNOTED_DB
    try:
        import sqlite3
    except Exception as hata:
        return "OLCULEMEDI", "sqlite3 yok: %s" % type(hata).__name__
    if not os.path.exists(yol):
        return "OLCULEMEDI", "db yok: %s" % yol
    try:
        baglanti = sqlite3.connect("file:%s?mode=ro&immutable=1" % yol, uri=True, timeout=5)
    except Exception as hata:
        return "OLCULEMEDI", "acilamadi: %s" % type(hata).__name__
    try:
        tablolar = {r[0] for r in baglanti.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "record" not in tablolar:
            return "OLCULEMEDI", "record tablosu yok (tablolar=%s)" % sorted(tablolar)[:6]
        toplam = int(baglanti.execute("SELECT COUNT(*) FROM record").fetchone()[0])
        if toplam == 0:
            # Sonda KOR: db hic kayit tutmuyor -> "bulunamadi" TESLIM EDILMEDI DEMEK DEGIL.
            return "OLCULEMEDI", "record BOS (toplam=0)"
        imza = "%" + jeton.encode("utf-8").hex().upper() + "%"
        satir = baglanti.execute(
            "SELECT COUNT(*) FROM record WHERE hex(data) LIKE ?", (imza,)).fetchone()
        adet = int(satir[0]) if satir else 0
    except Exception as hata:
        return "OLCULEMEDI", "sorgu: %s: %s" % (type(hata).__name__, str(hata)[:120])
    finally:
        try:
            baglanti.close()
        except Exception:
            pass
    return ("TESLIM_VAR" if adet > 0 else "TESLIM_YOK"), "kayit=%d/%d" % (adet, toplam)


def _damga_koy(anahtar, simdi, dizin=None):
    """Atomik tekillik damgasi. True = BU cagri kazandi (bildirim gonderilebilir)."""
    dizin = dizin or DAMGA_DIZINI
    yol = os.path.join(dizin, "%s%s" % (anahtar, DAMGA_SONEKI))
    try:
        os.makedirs(dizin, exist_ok=True)
        fd = os.open(yol, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False, yol
    except OSError as hata:
        return False, "%s (%s)" % (yol, type(hata).__name__)
    with os.fdopen(fd, "w", encoding="utf-8") as dosya:
        dosya.write("ANAHTAR=%s\nEPOK=%.3f\nPID=%d\n" % (anahtar, simdi, os.getpid()))
    return True, yol


def damga_temizle(dizin=None, yas_esik=DAMGA_YAS_ESIGI_SN, simdi=None):
    """Ureten temizler: yalniz `*.bildirildi` dosyalari, yalniz yasli olanlar."""
    dizin = dizin or DAMGA_DIZINI
    simdi = simdi if simdi is not None else time.time()
    try:
        adlar = os.listdir(dizin)
    except OSError:
        return 0
    silinen = 0
    for ad in adlar:
        if not ad.endswith(DAMGA_SONEKI):
            continue
        yol = os.path.join(dizin, ad)
        try:
            if not os.path.isfile(yol):
                continue
            if (simdi - os.path.getmtime(yol)) <= yas_esik:
                continue
            os.unlink(yol)
            silinen += 1
        except OSError:
            continue
    return silinen


def _loga_yaz(satir, yol=None):
    yol = yol or BILDIRIM_LOG
    try:
        with open(yol, "a", encoding="utf-8") as dosya:
            dosya.write(satir.rstrip("\n") + "\n")
        return True
    except OSError:
        return False


def bildir(k, simdi=None, damga_dizini=None, log_yolu=None, osascript=None,
           anahtar_oneki="", sonda=True, db_yolu=None, kanal=None):
    """KIRMIZI karari icin bildirimi FIILEN gonderir (gun basina EN FAZLA 1).

    Doner: {denendi, gonderildi, rc, ayrinti, teslim, teslim_ayrinti, damga, anahtar}
    """
    simdi = simdi if simdi is not None else time.time()
    kanal = kanal or BILDIRIM_KANALI
    bos = {"denendi": False, "gonderildi": False, "rc": None, "ayrinti": "-",
           "teslim": "-", "teslim_ayrinti": "-", "damga": "-", "anahtar": "-",
           "kanal": kanal}
    if (k or {}).get("hukum") != "KIRMIZI":
        bos["ayrinti"] = "HUKUM=%s (bildirim GEREKMEZ)" % (k or {}).get("hukum")
        return bos

    anahtar = "%s%s" % (anahtar_oneki, str(k.get("tarih") or "-").replace("-", ""))

    if kanal == "cip":
        # 🔴 DAMGA TUKETILMEZ. Damga 'bugun TESLIM EDILDI' jetonudur ve onu
        # yalniz teslim kolu koyar. Bu kol gunde 96 kez kosar; damgayi
        # burada yakmak sabah rutinini MUKERRER'e dusurup teslimi SONSUZA
        # KADAR engellerdi — 26/27 Agu'da fiilen yasanan hal budur.
        bos["anahtar"] = anahtar
        bos["rc"] = 0
        bos["teslim"] = "TESLIM_KOLUNDA"
        bos["ayrinti"] = ("KANAL=cip — hukum KIRMIZI, teslim RUTIN kolunda; "
                          "damga TUKETILMEDI")
        return bos

    kazandi, damga_yolu = _damga_koy(anahtar, simdi, damga_dizini)
    if not kazandi:
        bos["anahtar"] = anahtar
        bos["damga"] = damga_yolu
        bos["ayrinti"] = "DAMGA_VAR (bugun zaten bildirildi ya da damga yazilamadi)"
        return bos

    mesaj = "%s: bugunun Tamirci cipi DOGMADI — %s yok (saat %02d, esik %02d)." % (
        BILDIRIM_JETONU, k.get("kanit_adi") or "-", int(k.get("saat") or -1),
        int(k.get("esik") or -1))
    altbaslik = "kral-sabah.py atesLEMEDI mi? %s" % (k.get("tarih") or "-")
    rc, ayrinti = uygulama_bildirimi(BILDIRIM_BASLIGI, altbaslik, mesaj, osascript,
                                     kanal=kanal)

    if rc is None:
        # Kanal YOK: ekrana HICBIR SEY dusmedi. Teslim bilerek OLCULEMEDI —
        # "gonderdim" DEMEYIZ, "gonderemedim" de bir olcumdur.
        teslim, teslim_ayrinti = "OLCULEMEDI", "kanal=YOK, ekrana hicbir sey dusmedi"
    elif not sonda:
        teslim, teslim_ayrinti = "ATLANDI", "sonda kapali"
    else:
        teslim, teslim_ayrinti = teslim_sondasi(BILDIRIM_JETONU, db_yolu)

    # 🔴 MAKINE-OKUR KALICI KAYIT: teslim kanali ne olursa olsun bu satir DUSER.
    # `gunluk-mimar-ihtar` (15:00) kolu bu satiri VE `gozcu-kalp.json`daki
    # `bekci_hukum` alanini okur — Okan'a cikis oradan gider.
    _loga_yaz("%s BEKCI_BILDIRIM anahtar=%s kanal=%s rc=%s teslim=%s (%s) ayrinti=%s" % (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(simdi)), anahtar, kanal, rc,
        teslim, teslim_ayrinti, ayrinti), log_yolu)

    return {"denendi": True, "gonderildi": rc == 0, "rc": rc, "ayrinti": ayrinti,
            "teslim": teslim, "teslim_ayrinti": teslim_ayrinti,
            "damga": damga_yolu, "anahtar": anahtar, "kanal": kanal}


# --- gozcunun cagirdigi TEK giris ------------------------------------------

def kol(simdi=None, kuru=False, dizin=None, esik_saat=None, damga_dizini=None,
        log_yolu=None, osascript=None, anahtar_oneki="", sonda=True,
        yerel_cozucu=None, db_yolu=None, kanal=None,
        teslim_kollari=None, teslim_kalp_yolu=None, teslim_bayatlik_saat=None):
    """`gozcu.py`nin her turda cagirdigi TEK fonksiyon.

    `kuru=True`: karar VERILIR, bildirim GONDERILMEZ, damga KONMAZ, log YAZILMAZ.
    Doner: karar sozlugu + {"bildirim": {...}, "ozet": "<tek satir>"}
    """
    simdi = simdi if simdi is not None else time.time()
    k = karar(simdi, dizin, esik_saat, yerel_cozucu, teslim_kollari,
              teslim_kalp_yolu, teslim_bayatlik_saat, log_yolu, anahtar_oneki)
    if kuru:
        b = {"denendi": False, "gonderildi": False, "rc": None, "ayrinti": "KURU",
             "teslim": "-", "teslim_ayrinti": "-", "damga": "-", "anahtar": "-",
             "kanal": kanal or BILDIRIM_KANALI}
    else:
        b = bildir(k, simdi, damga_dizini, log_yolu, osascript, anahtar_oneki,
                   sonda, db_yolu, kanal)
        damga_temizle(damga_dizini, simdi=simdi)
    k = dict(k)
    k["bildirim"] = b
    t = k.get("teslim") or {}
    d = k.get("dogum") or {}
    k["ozet"] = ("BEKCI=%s sebep=%s saat=%02d kanal=%s bildirim=%s rc=%s teslim=%s "
                 "TESLIM_KANCA=%s TESLIM_KALP=%.1fh KANIT=%s DOGUM=%s DOGUM_SEBEP=%s "
                 "DOGUM_TASK=%s" % (
                     k["hukum"], k["sebep"], int(k.get("saat") or -1), b.get("kanal"),
                     1 if b.get("gonderildi") else 0, b.get("rc"), b.get("teslim"),
                     t.get("kanca"), float(t.get("kalp_saat") or -1.0),
                     int(bool(k.get("kanit"))), d.get("dogdu"), d.get("sebep"),
                     d.get("task_id")))
    return k


def kirmizi_mi(k):
    """rc yukseltme hukmu TEK NOKTADA. `OLCULEMEDI` YESIL DEGILDIR."""
    return (k or {}).get("hukum") in ("KIRMIZI", "OLCULEMEDI")


# ============================================================================
# TESLIM KOLU — KANAL=cip   (27 Agu 2026, `KraL-SabahTeslim-27Agu`, OKAN KARARI)
# ----------------------------------------------------------------------------
# 🔴 OLCULEN ARIZA (26-27 Agu): bekci DOGRU atesledi, DOGRU hukum verdi, DOGRU
# damgaladi — ve Okan HICBIR SEY GORMEDI. Log satiri birebir:
#   `... anahtar=20260827 kanal=YOK rc=None teslim=OLCULEMEDI (kanal=YOK,
#    ekrana hicbir sey dusmedi)`
# Yani zincirin uc halkasindan ikisi calisti, sonuncusu BOSLUGA BASTI.
#
# 🔴 OKAN KARARI: teslim kanali CIP. Gerekce OLCULMUS — bugun ona ULASTIGI
# KANITLANMIS tek kanal paneldir (dusurulen ciplerin hepsini gordu ve tikladi).
#
# 🔴 MIMARI KISIT (bu blogun VAROLUS SEBEBI): kabuk betigi / cron CIP DUSUREMEZ.
# Cipi ancak bir Claude oturumu yaratabilir. Dolayisiyla teslim IKI PARCADIR:
#   (a) HUKUM + YUK  -> burasi (`teslim_karari`), her yerden cagrilabilir
#   (b) CIP DOGUMU   -> panel `Routines` uzerindeki zamanlanmis Claude oturumu
#   (c) KAYIT        -> burasi (`teslim_kaydet`), task_id ile geri yazar
# `bildir()` bu yuzden CIP kanalinda damgayi TUKETMEZ; damga "bugun TESLIM
# EDILDI" jetonudur ve onu yalniz (a) koyar. Aksi halde gunde 96 kez kosan
# in-process kol damgayi 09:08'de yakar, 09:00 rutini MUKERRER goruр teslim
# etmez — teslim ASLA gerceklesmez.
#
# 🔴 `rc=None` ARTIK YAZILAMAZ: her teslim satiri somut bir rc tasir; kanal ya
# cipi uretir (`TESLIM=BASARILI task_id=...`) ya da `TESLIM=BASARISIZ sebep=...`
# basar. "Olcemedim" bir teslim hukmu DEGILDIR.
# ============================================================================

TESLIM_PROMPT_DIZINI = "/private/tmp/pruvo-bekci-teslim"
TESLIM_KARARLARI = ("GEREKLI", "GEREKSIZ", "MUKERRER", "OLCULEMEDI")
# Cip adi `<Ev>-<Is>` duzenine uyar (CLAUDE.md CHIP DUZENI ②).
TESLIM_AYLARI = ("Oca", "Sub", "Mar", "Nis", "May", "Haz",
                 "Tem", "Agu", "Eyl", "Eki", "Kas", "Ara")
# task_id BICIM KAPISI: isci/oturum ciktisi jeton UYDURABILIR
# ([[isci-ciktisi-arsiv-jetonunu-uydurabilir]]). Bicimi tutmayan jeton TESLIM
# SAYILMAZ; kayit `BASARISIZ` duser ve damga geri verilir (yeniden denenebilsin).
_TASK_ID_DESENI = re.compile(r"^task_[0-9a-fA-F]{6,}$")


def cip_adi(yerel_tarih):
    """O gunun Tamirci cipinin adi. TEK yerde uretilir."""
    return "KraL-Tamirci-%d%s" % (yerel_tarih.day,
                                  TESLIM_AYLARI[yerel_tarih.month - 1])


def _son_satirlar(yol, adet=25):
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            satirlar = dosya.read().splitlines()
    except OSError as hata:
        return "(%s okunamadi: %s)" % (yol, type(hata).__name__)
    if not satirlar:
        return "(%s BOS)" % yol
    return "\n".join(satirlar[-adet:])


def prompt_govdesi(k, sabah_log=None):
    """CIPIN PROMPT'U — tek tikla is baslar, Okan'a "git bak" DENMEZ.

    Iki hal:
      · o gunun spec'i VAR    -> spec metni AYNEN gomulur
      · spec YOK (asil hal)   -> URETILEMEME SEBEBI gomulur (bekci hukmu +
        beklenen yol + `kral-sabah.log` kuyrugu) ve cipin ILK adimi spec'i
        URETMEK olur.
    """
    sabah_log = sabah_log or os.path.join(CRON_KOKU, "kral-sabah.log")
    yol = k.get("kanit_yolu") or "-"
    ad = k.get("kanit_adi") or "-"
    tarih = k.get("tarih") or "-"

    spec_metni = None
    try:
        if os.path.isfile(yol) and os.path.getsize(yol) > 0:
            with open(yol, encoding="utf-8", errors="replace") as dosya:
                spec_metni = dosya.read()
    except OSError:
        spec_metni = None

    bas = [
        "Sen `%s` CIPISIN (PRUVO / KraL evi). Raporlarini bu imzayla at." % cip_adi(
            dt.date.fromisoformat(tarih) if tarih != "-" else dt.date.today()),
        "",
        "## ADIM 0 — ACILIS",
        "1. `/Users/okan/dev/pruvo/CLAUDE.md` oku ve uy (KOMUT STILI dahil).",
        "2. Ortak kutuyu (`~/.claude/projects/-Users-okan-dev-pruvo/memory/"
        "mimar-posta-kutusu.md`) oku; 🔴 oraya **`Write` ile ASLA** yazma, yalniz "
        "`Edit` ile EN USTE ekle. Kutuya kisa bir `BASLIYORUM` blogu birak.",
        "3. Kapanista sayili kapanis + son satir birebir `✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM`.",
        "",
        "## NEDEN DOGDUN (bekci olcumu — iddia degil)",
        "- BEKCI_HUKUM=%s  sebep=%s" % (k.get("hukum"), k.get("sebep")),
        "- Beklenen dogum kaniti: `%s`" % yol,
        "- Olculen boyut: %s bayt (0/-1 = kanit YOK)" % k.get("boyut"),
        "- Yerel saat %s, esik %s" % (k.get("saat"), k.get("esik")),
        "",
    ]

    if spec_metni:
        bas += [
            "## BUGUNUN TAMIRCI SPEC'I (`%s` — AYNEN)" % ad,
            "",
            spec_metni.rstrip("\n"),
        ]
    else:
        bas += [
            "## 🔴 SPEC URETILMEDI — ISININ BIRINCI ADIMI ONU URETMEK",
            "",
            "O gunun Tamirci spec'i (`%s`) YOK. Sebebi asagidaki kuyrukta." % ad,
            "",
            "**ILK KOMUT (tek satir):**",
            "```bash",
            "python3 /Users/okan/.claude/cron/kral-sabah.py",
            "```",
            "Cikti `SONUC_KOLU=SPEC_VAR` derse spec uretildi -> onu OKU ve isini ondan al.",
            "`SONUC_KOLU=SPEC_URETILMEDI` derse SEBEBI onar; araci onarmadan is yapma "
            "(bugunun arizasi tam olarak buydu).",
            "",
            "**`kral-sabah.log` KUYRUGU (son 25 satir, ham):**",
            "```",
            _son_satirlar(sabah_log, 25),
            "```",
        ]

    bas += [
        "",
        "## YASAKLAR",
        "Tekil yama (tek satir duzeltip kapatmak) · olcmedigine YESIL demek · "
        "`urunler.json` · ortak kutuya `Write` · bypass · main'e merge/push "
        "(karar MIMARDA) · Okan'a rutin bildirim.",
    ]
    return "\n".join(bas)


def _teslim_log_satiri(anahtar, rc, teslim, detay, ayrinti, simdi=None):
    """🔴 TEK BICIM: her teslim satiri SOMUT rc + SOMUT teslim hukmu tasir."""
    simdi = simdi if simdi is not None else time.time()
    return "%s BEKCI_BILDIRIM anahtar=%s kanal=cip rc=%d teslim=%s (%s) ayrinti=%s" % (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(simdi)),
        anahtar, int(rc), teslim, detay, ayrinti)


def teslim_karari(simdi=None, dizin=None, esik_saat=None, damga_dizini=None,
                  log_yolu=None, prompt_dizini=None, yerel_cozucu=None,
                  teslim_kollari=None, teslim_kalp_yolu=None,
                  teslim_bayatlik_saat=None, anahtar_oneki="", kuru=False,
                  sabah_log=None):
    """(a) HUKUM + YUK. Rutin (zamanlanmis Claude oturumu) BUNU cagirir.

    Doner sozluk: {karar, anahtar, hukum, sebep, cip_adi, prompt_yolu, ayrinti}
      · GEREKLI    -> cip DOGACAK; damga KONDU, prompt YAZILDI
      · GEREKSIZ   -> hukum YESIL/PENCERE_DISI; cip DOGMAZ, damga KONMAZ (B2)
      · MUKERRER   -> bugun zaten teslim edildi; ikinci cip YOK (B3)
      · OLCULEMEDI -> damga/prompt yazilamadi; SESSIZ GECILMEZ

    🔴 HEARTBEAT: karar ne olursa olsun loga BIR satir duser. "Rutin bugun kostu
    mu" sorusu boylece tek dosyadan cevaplanir — kolun kendisi de OLCULUR.
    """
    simdi = simdi if simdi is not None else time.time()
    prompt_dizini = prompt_dizini or TESLIM_PROMPT_DIZINI

    k = karar(simdi, dizin, esik_saat, yerel_cozucu, teslim_kollari,
              teslim_kalp_yolu, teslim_bayatlik_saat, log_yolu, anahtar_oneki)
    anahtar = "%s%s" % (anahtar_oneki, str(k.get("tarih") or "-").replace("-", ""))
    taban = {"karar": "OLCULEMEDI", "anahtar": anahtar, "hukum": k.get("hukum"),
             "sebep": k.get("sebep"), "cip_adi": "-", "prompt_yolu": "-",
             "ayrinti": "-", "kanit_yolu": k.get("kanit_yolu"),
             "kanit": k.get("kanit"), "dogum": k.get("dogum")}

    def _don(karar_adi, ayrinti, rc, teslim, detay):
        s = dict(taban)
        s["karar"] = karar_adi
        s["ayrinti"] = ayrinti
        if not kuru:
            _loga_yaz(_teslim_log_satiri(anahtar, rc, teslim, detay, ayrinti, simdi),
                      log_yolu)
        return s

    # --- B2 POZITIF KONTROL: sessiz gun SESSIZ KALIR ---
    # 🔴 Bu kol OLMAZSA arac "her sabah cip" makinesine doner. Hukum YESIL ya da
    # PENCERE_DISI ise cip DOGMAZ ve damga TUKETILMEZ.
    if not kirmizi_mi(k):
        return _don("GEREKSIZ",
                    "hukum=%s -> cip DOGMAZ (sessiz gun sessiz kalir)" % k.get("hukum"),
                    0, "GEREKMEDI", "hukum=%s" % k.get("hukum"))

    # --- B3 MUKERRER YASAGI: gun basina EN FAZLA 1 cip ---
    if kuru:
        var = os.path.isfile(os.path.join(damga_dizini or DAMGA_DIZINI,
                                          "%s%s" % (anahtar, DAMGA_SONEKI)))
        if var:
            return _don("MUKERRER", "damga VAR (kuru)", 0, "MUKERRER", "kuru")
    else:
        kazandi, damga_yolu = _damga_koy(anahtar, simdi, damga_dizini)
        if not kazandi:
            return _don("MUKERRER",
                        "damga VAR -> bugun zaten teslim edildi (%s)" % damga_yolu,
                        0, "MUKERRER", "damga=%s" % damga_yolu)

    # --- B4 CIPIN ICI: o gunun spec'i ya da URETILEMEME SEBEBI ---
    ad = cip_adi(dt.date.fromisoformat(k["tarih"]) if k.get("tarih") not in (None, "-")
                 else dt.date.today())
    taban["cip_adi"] = ad
    govde = prompt_govdesi(k, sabah_log)
    prompt_yolu = os.path.join(prompt_dizini, "prompt-%s.md" % anahtar)
    if not kuru:
        try:
            os.makedirs(prompt_dizini, exist_ok=True)
            with open(prompt_yolu, "w", encoding="utf-8") as dosya:
                dosya.write(govde)
        except OSError as hata:
            # Damgayi GERI VER: teslim edilemedi, yarinki/sonraki kosum denesin.
            _damga_geri_ver(anahtar, damga_dizini)
            return _don("OLCULEMEDI",
                        "prompt YAZILAMADI: %s" % type(hata).__name__,
                        1, "BASARISIZ", "prompt_yazilamadi")
    taban["prompt_yolu"] = prompt_yolu

    return _don("GEREKLI",
                "cip=%s prompt=%s bayt=%d" % (ad, prompt_yolu, len(govde.encode("utf-8"))),
                0, "BEKLIYOR", "cip=%s" % ad)


def _damga_geri_ver(anahtar, damga_dizini=None):
    """Teslim BASARISIZ olduysa damga geri verilir — yoksa arac 'teslim ettim'
    yalanini kalicilastirir ve o gun bir daha denenemez."""
    yol = os.path.join(damga_dizini or DAMGA_DIZINI,
                       "%s%s" % (anahtar, DAMGA_SONEKI))
    try:
        os.unlink(yol)
        return True
    except OSError:
        return False


def teslim_kaydet(anahtar, task_id=None, sebep=None, log_yolu=None,
                  damga_dizini=None, simdi=None):
    """(c) KAYIT — cip DOGDUKTAN sonra rutin bunu cagirir.

    `task_id` verilirse TESLIM=BASARILI + task_id loga yazilir.
    Verilmezse/bicimsizse TESLIM=BASARISIZ + SEBEP yazilir ve damga GERI VERILIR.
    🔴 Her iki yolda da rc SOMUTTUR; `rc=None` URETILEMEZ.
    Doner: (rc, satir)
    """
    simdi = simdi if simdi is not None else time.time()
    if task_id and _TASK_ID_DESENI.match(str(task_id).strip()):
        satir = _teslim_log_satiri(anahtar, 0, "BASARILI",
                                   "cip panelde DOGDU", "task_id=%s" % task_id.strip(),
                                   simdi)
        _loga_yaz(satir, log_yolu)
        return 0, satir
    if task_id:
        neden = "TASK_ID_BICIMI:%r" % str(task_id)[:40]
    else:
        neden = sebep or "SEBEP_VERILMEDI"
    geri = _damga_geri_ver(anahtar, damga_dizini)
    satir = _teslim_log_satiri(anahtar, 1, "BASARISIZ", neden,
                               "damga_geri_verildi=%d" % (1 if geri else 0), simdi)
    _loga_yaz(satir, log_yolu)
    return 1, satir


if __name__ == "__main__":
    _ap = argparse.ArgumentParser(description="cip-dogum bekcisi")
    _ap.add_argument("--kuru", action="store_true",
                     help="karar VERILIR, bildirim/damga/log YOK")
    _ap.add_argument("--teslim-karari", action="store_true",
                     help="(a) TESLIM KOLU: bugun cip dusurulecek mi")
    _ap.add_argument("--teslim-kaydet", action="store_true",
                     help="(c) KAYIT: cip dogdu, task_id'yi yaz")
    _ap.add_argument("--anahtar", default=None, help="teslim anahtari (YYYYAAGG)")
    _ap.add_argument("--task-id", default=None, help="dogan cipin task_id'si")
    _ap.add_argument("--sebep", default=None, help="teslim BASARISIZ ise sebep")
    _a = _ap.parse_args()

    if _a.teslim_kaydet:
        if not _a.anahtar:
            print("TESLIM_KAYIT=OLCULEMEDI sebep=ANAHTAR_YOK")
            sys.exit(2)
        _rc, _satir = teslim_kaydet(_a.anahtar, _a.task_id, _a.sebep)
        print(_satir)
        print("TESLIM_KAYIT=%s rc=%d" % ("BASARILI" if _rc == 0 else "BASARISIZ", _rc))
        sys.exit(_rc)

    if _a.teslim_karari:
        _t = teslim_karari(kuru=_a.kuru)
        print("TESLIM_KARARI=%s" % _t["karar"])
        print("ANAHTAR=%s" % _t["anahtar"])
        print("HUKUM=%s" % _t["hukum"])
        print("SEBEP=%s" % _t["sebep"])
        print("KANIT=%s" % ("VAR" if _t.get("kanit") else "YOK"))
        print("DOGUM=%s sebep=%s task_id=%s" % (
            (_t.get("dogum") or {}).get("dogdu"),
            (_t.get("dogum") or {}).get("sebep"),
            (_t.get("dogum") or {}).get("task_id")))
        print("CIP_ADI=%s" % _t["cip_adi"])
        print("PROMPT_YOLU=%s" % _t["prompt_yolu"])
        print("AYRINTI=%s" % _t["ayrinti"])
        sys.exit(0 if _t["karar"] in ("GEREKLI", "GEREKSIZ", "MUKERRER") else 1)

    _s = kol(kuru=_a.kuru)
    print(_s["ozet"] + " kanit=%s boyut=%s" % (_s.get("kanit_adi"), _s.get("boyut")))
    sys.exit(1 if kirmizi_mi(_s) else 0)
