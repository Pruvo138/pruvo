#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/katalog-alan-kapisi.py FIILEN blokluyor mu? (CI'da bloklayici)

    python3 tools/katalog-alan-kapisi-test.py

Surucu KENDI sentetik depolarini kurar (`tempfile` + gercek `git init`), icine
GERCEK `tools/arama.py` ve GERCEK `tools/katalog-alan-kapisi.py` dosyalarini
KOPYALAR. GERCEK `urunler.json` yalnizca OKUNUR; gercek `.git`e HICBIR SEY
yazilmaz (tek istisna: yok — kanca kurulumu da yapilmaz).

═══════════════════════════════════════════════════════════════════════════════
OLCULEN IDDIALAR
═══════════════════════════════════════════════════════════════════════════════
A1 KIRMIZI  izinsiz `altkategori` TEK BASINA rc=1 yakar.
A2 KIRMIZI  `uyum` dolu + `marka` ELLE yazilmis (K5 ikizi) TEK BASINA rc=1 yakar.
            🔴 [[beyan-edilmis-survivor]]: tek bir "ikisi birden bozuk" vaka iki
            ekseni birden OLCMEZ, katmanlarin VEYA'sini olcer. Iki eksen AYRI
            vakalarda ve AYRI mutantlarla olculur.
B1 YESIL    BUGUNKU gercek katalogun TAMAMI (22.698 kayit) "yeni" olarak
            stage'lendiginde yanlis-pozitif URETMEZ.
B2 YESIL    Gercek katalogda TEK bir MESRU degisiklik (bir kaydin `fiyat`i) rc=0.
B3 YESIL    urunler.json HIC degismediginde rc=0 VE atlama NEDENI BASILIR
            (sessiz atlama = sessiz yesil).
B4 YESIL    Yalniz SIRALAMA degistiginde rc=0 (degisen KAYIT yok).
K  KAPSAM   HEAD'de ZATEN duran bir ihlal, ILGISIZ bir kaydin degistigi commit'i
            BLOKLAMAZ ([[kanca-stage-disi-agaci-tarar]]: paylasilan checkout'ta
            baska bir mimarin yarim partisi herkesi kilitlemesin).
E  EKSEN    Calisma agaci BOZUK + index TEMIZ -> rc=0. Kapinin ekseni INDEX'tir.
O1 OLCULEMEDI  index'teki JSON bozuksa rc=2 (0 DEGIL, 1 DEGIL).
O2 OLCULEMEDI  tools/arama.py yoksa rc=2 — kanonik kaynak kayipken hukum VERILMEZ.
O3 OLCULEMEDI  arguman verilirse rc=2 (ikinci bir eksen/kip ACILMAZ).
            🔴 ILK SURUMDE BEYAN EDILMIS SURVIVOR'DI (mimar iadesi, 9 Agu): O3 `arama.py`
            OLMAYAN depoda kosuyordu, yani rc=2 argumandan DEGIL kayip kanonik modulden
            geliyordu — iddia katmanlarin VEYA'sini olcuyordu ([[beyan-edilmis-survivor]]).
            ARTIK: `arama.py` OLAN, index'i TEMIZ bir depoda kosar ve AYIRT EDICI KONTROL
            tasir (ayni depoda ARGUMANSIZ cagri rc=0 vermeli). Nobeti: MUT-ARG.
KOK         GERCEK worktree + GERCEK kanca baglaminda kapinin BASTIGI kok, o
            worktree'nin kokudur ([[kanca-git-dir-kok-cozumu]]).
KOK-ALT     🔴 AYIRT EDICI KOL (mimar iadesi, 9 Agu): yukaridaki KOK olcumu her iki kolu
            da cwd = AGACIN TEPESI'nde kosturur; orada `__file__` turetimi ile
            `rev-parse --show-toplevel` AYNI cevabi verir, yani KOK ekseni kok cozumunu
            OLCMUYORDU ([[olculdu-diyen-hukum-kaniti]]). Bu vaka kapiyi GERCEK kanca
            ortaminda ve cwd = `<agac>/tools` (tepe DEGIL) iken cagirir; orada iki
            uygulama AYRISIR. Nobeti: MUT-KOK.
INDEX       Miras alinan GIT_INDEX_FILE ONURLANIR (ortam TEMIZLENMEZ) + AYIRT
            EDICI KONTROL: ayni agacta degisken VERILMEDIGINDE hukum rc=0'dir.
            Bu ikisi kapinin docstring'indeki (1)/(2) tuzaklarinin AYRI olcumudur.
MUT-ALT     `altkategori_sebebi` kolu KALDIRILAN kopyada A1 YESILE doner (mutant
MUT-UYUM    olur) ve A2 KIRMIZI KALIR; `uyum_sebebi` kolu icin simetrigi.
MUT-ARG     `main()`'deki arguman kolu (`if len(argv) > 1:`) SILINEN kopyada O3 dusmeli;
            A1/A2 AYAKTA kalmali (yani O3 gercekten O KOLU olcuyor).
MUT-KOK     `ROOT` turetimi `rev-parse --show-toplevel`e cevrilen kopyada KOK-ALT dusmeli;
            A1/A2 AYAKTA kalmali (eski eksenler bu bozulmaya KORDU — kanit budur).
            🔴 [[mutasyon-diske-yazma-tuzagi]] + [[mutasyon-bytecode-onbellegi]]:
            mutant AYRI dizine yazilir, bytecode yazimi kapalidir ve mutasyonun
            FIILEN uygulandigi (metin degisti mi) AYRICA dogrulanir.

KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
([[mutasyon-kaniti-yeniden-uretilebilir]]): her vaka guvenli sarmalayicida kosar,
COKME "kirmizi" SAYILMAZ, AYRI bir OLCULEMEDI kovasina dusar ve rc'yi bozar.
Iddia sayisi IDDIA_TABANI'nin altina duserse (bir iddia SESSIZCE kaybolmussa)
hukum KIRMIZI'dir.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(TOOLS)
GERCEK_KAPI = os.path.join(TOOLS, "katalog-alan-kapisi.py")
GERCEK_ARAMA = os.path.join(TOOLS, "arama.py")
GERCEK_KATALOG = os.path.join(GERCEK_KOK, "urunler.json")

# Bir iddia silmek MESRU olabilir; sessizce kaybolmasi DEGIL. Iddia sayisi bunun
# altina duserse hukum KIRMIZI olur ve taban AYNI commit'te gerekceyle dusurulur.
IDDIA_TABANI = 49

# Git baglam scrub'inin TEK KAYNAGI tools/git_ortami.py'dir; burada IKINCI bir
# kume TANIMLANMAZ ([[ikiz-tanim-sessiz-ayrisma]]). Surucunun kendi cocuk
# sureclerine miras kalan git baglami temizlenir ki sentetik olcum, surucunun
# NEREDEN kosturuldugundan bagimsiz olsun.
_gospec = importlib.util.spec_from_file_location(
    "git_ortami", os.path.join(TOOLS, "git_ortami.py"))
go = importlib.util.module_from_spec(_gospec)
_gospec.loader.exec_module(go)

# Mutasyon capalari — kapinin IKI dogrulama kolu (AYRI AYRI kaldirilabilir olmali).
MUTASYONLAR = (
    ("MUT-ALT", 'arama.altkategori_sebebi(u.get("kategori"), u.get("altkategori"))',
     "None"),
    ("MUT-UYUM", "arama.uyum_sebebi(u)", "None"),
)

# ARGUMAN KOLU mutanti: `main()`in "ikinci eksen ACILMAZ" kolu tumuyle etkisizlesir.
MUT_ARG_CAPA = "if len(argv) > 1:"
MUT_ARG_YERINE = "if False:"

# KOK TURETIMI mutanti: `__file__` yerine `rev-parse --show-toplevel` (CWD'ye bagli,
# `-C` YOK — bu depodaki ESKI kanca govdelerinin birebir deyimi:
# `root=$(git rev-parse --show-toplevel)`).
# 🔴 MUTANT KASITLI OLARAK "ZOR" SECILDI: cwd = AGACIN TEPESI iken bu ifade DOGRU cevabi
# verir, yani tepede kosan sondalara (git_ortami.worktree_kanca_kok_olcumu) GORUNMEZ.
# Yalnizca cwd tepe DEGILKEN ve kanca ortami (MUTLAK GIT_DIR + BOS GIT_WORK_TREE)
# git'in depo KESFINI atlattiginda ayrisir: git CARI DIZINI agacin tepesi sanar.
# `subprocess` bu satirdan ONCE import edilmis durumda -> mutant SOZDIZIMSEL olarak gecerli.
MUT_KOK_CAPA = "ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))"
MUT_KOK_YERINE = ('ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], '
                  'capture_output=True, text=True).stdout.strip()')

_KOK_DESENI = re.compile(r"olculen agac = (.+?)\s*$", re.M)

# cwd'yi AGACIN TEPESINDEN alt dizine kaydiran GERCEK pre-commit kancasi. git kancayi
# tepede baslatir; `cd` olmadan iki kok turetimi AYNI cevabi verir ve eksen KOR kalir.
_ALT_KANCA_GOVDESI = """#!/bin/sh
# Sentetik pre-commit: kapiyi ALT DIZINDEN (cwd != agacin tepesi) ve kanca ortaminda
# kosar, ciktisini kaydeder, commit'i BLOKLAMAZ (olculen sey BASILAN KOK).
cd "%(altdizin)s" || exit 0
"%(python)s" "%(kapi)s" > "%(kayit)s" 2>&1
printf 'SONDA_RC=%%s\\n' "$?" >> "%(kayit)s"
exit 0
"""

TEMIZ_KAYIT = {
    "id": "sentetik-temiz-1",
    "kategori": "Otomobil",
    "baslik": "Sentetik temiz kayit",
    "aciklama": "Sentetik.",
    "fiyat": "100 TL",
    "gorseller": ["https://ornek.invalid/1.jpg"],
}

# 8 Agu 2026 partisinin YENIDEN URETILMIS hali — IKI EKSEN AYRI KAYITLARDA.
BOZUK_ALTKATEGORI = {
    "id": "sentetik-bozuk-altkategori",
    "kategori": "Otomobil",
    "baslik": "Sentetik izinsiz altkategori",
    "aciklama": "Sentetik.",
    "fiyat": "100 TL",
    # ALTKATEGORI_IZINLI["Otomobil"] icinde YOK (olculen ihlalin ta kendisi).
    "altkategori": "Elektrik ve Aydınlatma",
    "gorseller": ["https://ornek.invalid/2.jpg"],
}

# `uyum` dolu iken `marka` ELLE yazilmis: turetilen ["Ford", "Focus"] ile TUTMAZ.
BOZUK_UYUM = {
    "id": "sentetik-bozuk-uyum",
    "kategori": "Otomobil",
    "baslik": "Sentetik ikiz marka",
    "aciklama": "Sentetik.",
    "fiyat": "100 TL",
    "marka": ["Ford", "Fiesta"],
    "uyum": [{"marka": "Ford", "model": "Focus"}],
    "gorseller": ["https://ornek.invalid/3.jpg"],
}


# ---------------------------------------------------------------------------
class Sayac(object):
    def __init__(self):
        self.gecen = 0
        self.kalan = 0
        self.olculemedi = 0
        self.kirmizi = []

    def bekle(self, etiket, kosul, detay=""):
        if kosul:
            self.gecen += 1
            print("  GECTI  %s" % etiket)
        else:
            self.kalan += 1
            self.kirmizi.append(etiket)
            print("  KALDI  %s — %s" % (etiket, str(detay)[:500]))
        return bool(kosul)

    def cokme(self, etiket, hata):
        self.olculemedi += 1
        self.kirmizi.append(etiket + "(COKME)")
        print("  ⚪ OLCULEMEDI %s — %s" % (etiket, str(hata)[:300]))

    @property
    def toplam(self):
        return self.gecen + self.kalan + self.olculemedi


def vaka(s, ad, fn, *args):
    """Guvenli sarmalayici: COKME kirmizi ile KARISMAZ, ayri kovaya dusar."""
    print("\n%s" % ad)
    try:
        fn(s, *args)
    except Exception as e:
        s.cokme(ad, "%s: %s | %s" % (type(e).__name__, e,
                                     traceback.format_exc().splitlines()[-1]))


# ---------------------------------------------------------------------------
def _git(depo, *args, **kw):
    return go.sentetik_git(depo, *args, capture_output=True, text=True,
                            errors="replace", ek_ortam=kw.get("ortam"),
                            korunan_baglam=("GIT_INDEX_FILE",),
                            kimlik_ad="t", kimlik_eposta="t@t.local")


def _json_yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def depo_kur(yol, kapi_kaynagi, head_kayitlari, arama_koy=True):
    """Sentetik depo: tools/ + urunler.json + TEK taban commit'i."""
    os.makedirs(os.path.join(yol, "tools"))
    if arama_koy:
        shutil.copyfile(GERCEK_ARAMA, os.path.join(yol, "tools", "arama.py"))
    shutil.copyfile(kapi_kaynagi, os.path.join(yol, "tools", "katalog-alan-kapisi.py"))
    _git(yol, "init", "-q", "-b", "main")
    _json_yaz(os.path.join(yol, "urunler.json"), head_kayitlari)
    _git(yol, "add", "-A")
    # `core.hooksPath=/dev/null`: sentetik depo ASLA bu makinenin kancalarini kosmasin.
    _git(yol, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "taban")
    return yol


def stage_et(depo, kayitlar, ham=None):
    yol = os.path.join(depo, "urunler.json")
    if ham is not None:
        with open(yol, "w", encoding="utf-8") as f:
            f.write(ham)
    else:
        _json_yaz(yol, kayitlar)
    r = _git(depo, "add", "urunler.json")
    if r.returncode != 0:
        raise RuntimeError("git add basarisiz: %s" % r.stderr[:200])


def kapiyi_kos(depo, ortam=None):
    p = subprocess.run([sys.executable,
                        os.path.join(depo, "tools", "katalog-alan-kapisi.py")],
                       cwd=depo, capture_output=True, text=True, errors="replace",
                       env=ortam or go.git_ortami())
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ---------------------------------------------------------------------------
# A — KIRMIZI eksenleri (AYRI AYRI)
# ---------------------------------------------------------------------------
def _tek_eksen_kos(kok, ad, kapi_kaynagi, bozuk_kayit):
    d = depo_kur(os.path.join(kok, ad), kapi_kaynagi, [TEMIZ_KAYIT])
    stage_et(d, [TEMIZ_KAYIT, bozuk_kayit])
    return kapiyi_kos(d)


def vaka_a(s, kok):
    rc1, c1 = _tek_eksen_kos(kok, "a1", GERCEK_KAPI, BOZUK_ALTKATEGORI)
    s.bekle("A1.altkategori-tek-basina-kirmizi", rc1 == 1,
            "izinsiz altkategori TEK BASINA rc=1 yakmali; rc=%d cikti=%s" % (rc1, c1[-400:]))
    s.bekle("A1.rapor-alani-adlandiriyor", "[altkategori]" in c1 and
            "sentetik-bozuk-altkategori" in c1,
            "rapor id + alan adi tasimali; cikti=%s" % c1[-400:])
    s.bekle("A1.rapor-duzelt-yolu", "tools/duzelt.py" in c1,
            "rapor MESRU duzeltme yolunu gostermeli; cikti=%s" % c1[-400:])

    rc2, c2 = _tek_eksen_kos(kok, "a2", GERCEK_KAPI, BOZUK_UYUM)
    s.bekle("A2.uyum-ikiz-tek-basina-kirmizi", rc2 == 1,
            "K5 ikizi TEK BASINA rc=1 yakmali; rc=%d cikti=%s" % (rc2, c2[-400:]))
    s.bekle("A2.rapor-alani-adlandiriyor", "[uyum/marka]" in c2 and
            "sentetik-bozuk-uyum" in c2,
            "rapor id + alan adi tasimali; cikti=%s" % c2[-400:])


# ---------------------------------------------------------------------------
# B — YESIL eksenleri (yanlis-pozitif butcesi)
# ---------------------------------------------------------------------------
def vaka_b(s, kok):
    with open(GERCEK_KATALOG, encoding="utf-8") as f:
        katalog = json.load(f)
    s.bekle("B0.gercek-katalog-okundu", isinstance(katalog, list) and len(katalog) > 1000,
            "gercek katalog dizi olmali; tip=%s" % type(katalog).__name__)

    # HEAD BOS: gercek katalogun TAMAMI "yeni kayit" sayilir -> en genis yanlis-pozitif olcumu.
    d = depo_kur(os.path.join(kok, "b"), GERCEK_KAPI, [])
    stage_et(d, katalog)
    rc, c = kapiyi_kos(d)
    s.bekle("B1.gercek-katalog-tamami-yesil", rc == 0,
            "bugunku %d kaydin TAMAMI yeni sayildiginda yanlis-pozitif OLMAMALI; "
            "rc=%d cikti=%s" % (len(katalog), rc, c[-800:]))
    s.bekle("B1.tamami-fiilen-dogrulandi", ("%d degisen kayit" % len(katalog)) in c,
            "kapi TUM kayitlari degisen saymali (yesil, ATLANDI ile gelmemeli); "
            "cikti=%s" % c[-400:])
    _git(d, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "katalog")

    # HIC DEGISMEDI -> rc=0 AMA NEDEN BASILIR.
    rc, c = kapiyi_kos(d)
    s.bekle("B3.degismedi-yesil", rc == 0, "rc=%d cikti=%s" % (rc, c[-300:]))
    s.bekle("B3.atlama-nedeni-basiliyor", "ATLANDI" in c and "DEGISMEDI" in c,
            "sessiz atlama = sessiz yesil; neden BASILMALI. cikti=%s" % c[-300:])

    # TEK MESRU degisiklik (bir kaydin fiyati).
    yeni = [dict(u) for u in katalog]
    yeni[0]["fiyat"] = "1234 TL"
    stage_et(d, yeni)
    rc, c = kapiyi_kos(d)
    s.bekle("B2.mesru-fiyat-degisimi-yesil", rc == 0,
            "tek alan duzeltmesi bloklanMAmali; rc=%d cikti=%s" % (rc, c[-500:]))
    s.bekle("B2.kapsam-tek-kayit", "1 degisen kayit" in c,
            "kapsam INDEX ekseninde TEK kayda inmeli; cikti=%s" % c[-300:])

    # YALNIZ SIRALAMA degisti -> degisen KAYIT yok.
    stage_et(d, list(reversed(katalog)))
    rc, c = kapiyi_kos(d)
    s.bekle("B4.siralama-degisimi-yesil", rc == 0 and "DEGISEN KAYIT yok" in c,
            "siralama commit'i bloklamamali; rc=%d cikti=%s" % (rc, c[-300:]))


# ---------------------------------------------------------------------------
# K — KAPSAM: HEAD'deki eski ihlal ILGISIZ commit'i kilitlemez
# ---------------------------------------------------------------------------
def vaka_kapsam(s, kok):
    d = depo_kur(os.path.join(kok, "kapsam"), GERCEK_KAPI,
                 [TEMIZ_KAYIT, BOZUK_ALTKATEGORI, BOZUK_UYUM])
    degisen = dict(TEMIZ_KAYIT)
    degisen["fiyat"] = "999 TL"
    stage_et(d, [degisen, BOZUK_ALTKATEGORI, BOZUK_UYUM])
    rc, c = kapiyi_kos(d)
    s.bekle("K.eski-ihlal-ilgisiz-commiti-kilitlemez", rc == 0,
            "HEAD'de duran ihlal, DOKUNULMAYAN kayitlar uzerinden commit'i "
            "bloklamamali (paylasilan checkout tuzagi); rc=%d cikti=%s" % (rc, c[-500:]))


# ---------------------------------------------------------------------------
# E — EKSEN: calisma agaci DEGIL, INDEX
# ---------------------------------------------------------------------------
def vaka_eksen(s, kok):
    d = depo_kur(os.path.join(kok, "eksen"), GERCEK_KAPI, [TEMIZ_KAYIT])
    # Calisma agacina BOZUK kayit yazilir ama STAGE EDILMEZ.
    _json_yaz(os.path.join(d, "urunler.json"), [TEMIZ_KAYIT, BOZUK_ALTKATEGORI])
    rc, c = kapiyi_kos(d)
    s.bekle("E.calisma-agaci-bozuk-index-temiz-yesil", rc == 0,
            "kapinin ekseni INDEX'tir; stage EDILMEMIS bozukluk commit'i "
            "bloklamamali; rc=%d cikti=%s" % (rc, c[-400:]))


# ---------------------------------------------------------------------------
# O — OLCULEMEDI kolu (rc=2 YESIL SAYILMAZ)
# ---------------------------------------------------------------------------
def _arguman_kolu_kos(kok, ad, kapi_kaynagi):
    """(rc_argumanli, rc_argumansiz) — `arama.py` VAR ve index TEMIZ bir depoda.

    🔴 IKI SART DA KASITLI ([[beyan-edilmis-survivor]]): `arama.py` VAR ki rc=2 kayip
    modulden GELMESIN; index TEMIZ ki argumansiz kol rc=0 versin ve iddia AYIRT EDICI
    olsun. Ilk surumde bu vaka `arama.py`si OLMAYAN depoda kosuyordu ve arguman kolunu
    tumuyle silen mutant surucuyu YESIL birakiyordu.
    """
    d = depo_kur(os.path.join(kok, ad), kapi_kaynagi, [TEMIZ_KAYIT])
    kapi = os.path.join(d, "tools", "katalog-alan-kapisi.py")
    p = subprocess.run([sys.executable, kapi, "--calisma-agaci"], cwd=d,
                       capture_output=True, text=True, errors="replace",
                       env=go.git_ortami())
    rc_argsiz, _ = kapiyi_kos(d)
    return p.returncode, rc_argsiz


def vaka_olculemedi(s, kok):
    d = depo_kur(os.path.join(kok, "o1"), GERCEK_KAPI, [TEMIZ_KAYIT])
    stage_et(d, None, ham='[{"id": "bozuk", ')
    rc, c = kapiyi_kos(d)
    s.bekle("O1.bozuk-json-rc2", rc == 2,
            "bozuk JSON YESIL de KIRMIZI da degil, OLCULEMEDI olmali; rc=%d cikti=%s"
            % (rc, c[-300:]))

    d2 = depo_kur(os.path.join(kok, "o2"), GERCEK_KAPI, [TEMIZ_KAYIT], arama_koy=False)
    stage_et(d2, [TEMIZ_KAYIT, BOZUK_ALTKATEGORI])
    rc, c = kapiyi_kos(d2)
    s.bekle("O2.arama-yok-rc2", rc == 2,
            "kanonik kaynak kayipken hukum VERILMEZ; rc=%d cikti=%s" % (rc, c[-300:]))

    rc_arg, rc_argsiz = _arguman_kolu_kos(kok, "o3", GERCEK_KAPI)
    s.bekle("O3.ikinci-eksen-acilmiyor", rc_arg == 2,
            "ikinci bir kip/eksen YOKTUR, arguman rc=2 vermeli; rc=%d" % rc_arg)
    s.bekle("O3.ayirt-edici-kontrol", rc_argsiz == 0,
            "AYNI depoda ARGUMANSIZ cagri rc=0 olmali — yoksa rc=2 argumandan degil "
            "deponun halinden geliyordur (survivor); rc=%d" % rc_argsiz)


# ---------------------------------------------------------------------------
# KOK — worktree + GERCEK kanca baglaminda basilan kok
# ---------------------------------------------------------------------------
def _altdizin_kanca_kok(kok, ad, kapi_kaynagi):
    """(worktree_koku, basilan_kok, kanca_ciktisi) — GERCEK worktree + GERCEK kanca,
    cwd = `<worktree>/tools` (agacin TEPESI DEGIL).

    🔴 NEDEN ALT DIZIN: git kancayi agacin TEPESINDE baslatir; orada `__file__` turetimi
    ile `rev-parse --show-toplevel` AYNI cevabi verir ve kok ekseni KOR kalir (mimar
    iadesi, 9 Agu). Kanca `cd` ile alt dizine gecince kanca ortami (MUTLAK GIT_DIR +
    BOS GIT_WORK_TREE) git'in depo KESFINI atlatir ve `-C <alt dizin>` cagrisi o ALT
    DIZINI agacin tepesi sanar -> iki uygulama AYRISIR.
    """
    ana = os.path.join(kok, ad + "-ana")
    os.makedirs(os.path.join(ana, "tools"))
    _git(ana, "init", "-q", "-b", "main")
    shutil.copyfile(GERCEK_ARAMA, os.path.join(ana, "tools", "arama.py"))
    shutil.copyfile(kapi_kaynagi, os.path.join(ana, "tools", "katalog-alan-kapisi.py"))
    _json_yaz(os.path.join(ana, "urunler.json"), [TEMIZ_KAYIT])
    with open(os.path.join(ana, "veri.txt"), "w", encoding="utf-8") as f:
        f.write("sentetik icerik\n")
    _git(ana, "add", "-A")
    _git(ana, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "taban")

    wt = os.path.join(kok, ad + "-wt")
    _git(ana, "worktree", "add", "-q", "-b", ad + "-dal", wt)
    gercek_wt = os.path.realpath(wt)

    kayit = os.path.join(kok, ad + "-kanca-cikti.txt")
    kanca = os.path.join(ana, ".git", "hooks", "pre-commit")
    os.makedirs(os.path.dirname(kanca), exist_ok=True)
    with open(kanca, "w", encoding="utf-8") as f:
        f.write(_ALT_KANCA_GOVDESI % {
            "altdizin": os.path.join(gercek_wt, "tools"),
            "python": sys.executable,
            "kapi": os.path.join(gercek_wt, "tools", "katalog-alan-kapisi.py"),
            "kayit": kayit})
    os.chmod(kanca, 0o755)

    with open(os.path.join(wt, "veri.txt"), "a", encoding="utf-8") as f:
        f.write("worktree'de degisiklik\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "kok sondasi")

    cikti = ""
    if os.path.exists(kayit):
        with open(kayit, encoding="utf-8", errors="replace") as f:
            cikti = f.read()
    m = _KOK_DESENI.search(cikti)
    return gercek_wt, (m.group(1).strip() if m else None), cikti


def vaka_kok(s, kok):
    olcum = go.worktree_kanca_kok_olcumu(GERCEK_KAPI, "katalog-alan-kapisi.py")
    s.bekle("KOK.kanca-kosti", olcum["kanca_kosti"],
            "sonda kancasi hic kosmadi -> eksen olculemedi: %r" % (olcum,))
    s.bekle("KOK.worktree-kancasinda-dogru-kok", olcum["kanca"][2],
            "kanca baglaminda basilan kok worktree koku olmali; olculen=%r beklenen=%s"
            % (olcum["kanca"][1], olcum["wt"]))
    s.bekle("KOK.kancasiz-dogru-kok", olcum["kancasiz"][2],
            "kancasiz cagride de kok worktree koku olmali; olculen=%r"
            % (olcum["kancasiz"][1],))

    # AYIRT EDICI KOL — cwd = <worktree>/tools (tepe DEGIL), gercek kanca ortami.
    wt, basilan, cikti = _altdizin_kanca_kok(kok, "kokalt", GERCEK_KAPI)
    s.bekle("KOK-ALT.kanca-kosti", bool(cikti) and basilan is not None,
            "alt dizin sondasi kok satirini basmadi -> eksen olculemedi; cikti=%s"
            % cikti[-300:])
    s.bekle("KOK-ALT.altdizinde-dogru-kok",
            basilan is not None and os.path.realpath(basilan) == wt,
            "cwd=<agac>/tools iken bile kok AGACIN TEPESI olmali; olculen=%r beklenen=%s"
            % (basilan, wt))


# ---------------------------------------------------------------------------
# INDEX — miras alinan GIT_INDEX_FILE ONURLANIR (ortam TEMIZLENMEZ)
# ---------------------------------------------------------------------------
def vaka_index_dosyasi(s, kok):
    d = depo_kur(os.path.join(kok, "indexfile"), GERCEK_KAPI, [TEMIZ_KAYIT])
    alt_index = os.path.join(kok, "alt-index")

    ortam = go.git_ortami()
    ortam["GIT_INDEX_FILE"] = alt_index
    _json_yaz(os.path.join(d, "urunler.json"), [TEMIZ_KAYIT, BOZUK_ALTKATEGORI])
    r = _git(d, "read-tree", "HEAD", ortam=ortam)
    if r.returncode != 0:
        raise RuntimeError("read-tree basarisiz: %s" % r.stderr[:200])
    r = _git(d, "add", "urunler.json", ortam=ortam)
    if r.returncode != 0:
        raise RuntimeError("alt index'e add basarisiz: %s" % r.stderr[:200])
    # VARSAYILAN index'i TEMIZ birak: calisma agacini HEAD haline geri yaz.
    _json_yaz(os.path.join(d, "urunler.json"), [TEMIZ_KAYIT])

    rc_alt, c_alt = kapiyi_kos(d, ortam=ortam)
    s.bekle("INDEX.miras-alinan-index-onurlaniyor", rc_alt == 1,
            "GIT_INDEX_FILE ile gosterilen index'teki ihlal YAKALANMALI (ortam "
            "temizlenseydi kapi BASKA bir index okurdu); rc=%d cikti=%s"
            % (rc_alt, c_alt[-400:]))

    rc_var, c_var = kapiyi_kos(d)
    s.bekle("INDEX.ayirt-edici-kontrol", rc_var == 0,
            "AYNI agacta degisken VERILMEDIGINDE hukum rc=0 olmali — yoksa iddia "
            "ortami degil baska bir seyi olcuyordur; rc=%d cikti=%s"
            % (rc_var, c_var[-400:]))


# ---------------------------------------------------------------------------
# MUTANTLAR — her dogrulama kolu AYRI AYRI oldurulebilir mi?
# ---------------------------------------------------------------------------
def vaka_mutasyon(s, kok):
    with open(GERCEK_KAPI, encoding="utf-8") as f:
        kaynak = f.read()
    for etiket, capa, yerine in MUTASYONLAR:
        sayi = kaynak.count(capa)
        s.bekle("%s.capa-tekil" % etiket, sayi == 1,
                "mutasyon capasi kaynakta TAM 1 kez gecmeli; gecti=%d capa=%r"
                % (sayi, capa))
        if sayi != 1:
            continue
        mut_dizin = os.path.join(kok, "mutant-" + etiket)
        os.makedirs(mut_dizin)
        mut_kapi = os.path.join(mut_dizin, "katalog-alan-kapisi.py")
        govde = kaynak.replace(capa, yerine)
        with open(mut_kapi, "w", encoding="utf-8") as f:
            f.write(govde)
        s.bekle("%s.mutasyon-fiilen-uygulandi" % etiket,
                govde != kaynak and capa not in govde,
                "mutant metni kaynakla AYNI kalmis -> mutasyon UYGULANMADI "
                "([[mutasyon-diske-yazma-tuzagi]])")

        rc_alt, _ = _tek_eksen_kos(kok, etiket + "-alt", mut_kapi, BOZUK_ALTKATEGORI)
        rc_uyum, _ = _tek_eksen_kos(kok, etiket + "-uyum", mut_kapi, BOZUK_UYUM)
        if etiket == "MUT-ALT":
            s.bekle("MUT-ALT.oldurdu", rc_alt == 0,
                    "altkategori kolu KALDIRILINCA A1 YESILE donmeli (donmuyorsa "
                    "mutant HAYATTA); rc=%d" % rc_alt)
            s.bekle("MUT-ALT.ayirt-edici", rc_uyum == 1,
                    "ayni mutant uyum eksenini DUSURMEMELI — yoksa iki iddia tek "
                    "mutantla olculur ([[beyan-edilmis-survivor]]); rc=%d" % rc_uyum)
        else:
            s.bekle("MUT-UYUM.oldurdu", rc_uyum == 0,
                    "uyum kolu KALDIRILINCA A2 YESILE donmeli; rc=%d" % rc_uyum)
            s.bekle("MUT-UYUM.ayirt-edici", rc_alt == 1,
                    "ayni mutant altkategori eksenini DUSURMEMELI; rc=%d" % rc_alt)

        s.bekle("%s.bytecode-bulasmadi" % etiket,
                not os.path.exists(os.path.join(mut_dizin, "__pycache__")),
                "mutant dizininde __pycache__ olusmus ([[mutasyon-bytecode-onbellegi]])")


def _mutant_yaz(kok, etiket, kaynak, capa, yerine, s):
    """(mutant_kapi_yolu|None) — capayi tekillik + FIILEN uygulanma ile dogrulayarak yazar."""
    sayi = kaynak.count(capa)
    s.bekle("%s.capa-tekil" % etiket, sayi == 1,
            "mutasyon capasi kaynakta TAM 1 kez gecmeli; gecti=%d capa=%r" % (sayi, capa))
    if sayi != 1:
        return None
    mut_dizin = os.path.join(kok, "mutant-" + etiket)
    os.makedirs(mut_dizin)
    mut_kapi = os.path.join(mut_dizin, "katalog-alan-kapisi.py")
    govde = kaynak.replace(capa, yerine)
    with open(mut_kapi, "w", encoding="utf-8") as f:
        f.write(govde)
    s.bekle("%s.mutasyon-fiilen-uygulandi" % etiket,
            govde != kaynak and capa not in govde,
            "mutant metni kaynakla AYNI kalmis -> mutasyon UYGULANMADI "
            "([[mutasyon-diske-yazma-tuzagi]])")
    return mut_kapi


def vaka_mutasyon_arg_kok(s, kok):
    """MUT-ARG ve MUT-KOK: SART 2 ve SART 3'un ayirt edici nobetleri.

    Her mutant icin IKI iddia: (1) HEDEF eksen DUSUYOR mu, (2) OTEKI eksenler (A1/A2)
    AYAKTA mi. Ikincisi olmadan "eski 33 iddia bu bozulmaya kordu" hukmu KANITSIZ kalir.
    """
    with open(GERCEK_KAPI, encoding="utf-8") as f:
        kaynak = f.read()

    # --- MUT-ARG: `main()`'in arguman kolu etkisizlestirilir --------------------
    mut = _mutant_yaz(kok, "MUT-ARG", kaynak, MUT_ARG_CAPA, MUT_ARG_YERINE, s)
    if mut:
        rc_arg, rc_argsiz = _arguman_kolu_kos(kok, "mutarg", mut)
        s.bekle("MUT-ARG.oldurdu", rc_arg != 2,
                "arguman kolu SILININCE O3 dusmeli (rc 2 OLMAMALI); rc=%d" % rc_arg)
        s.bekle("MUT-ARG.kontrol-argumansiz", rc_argsiz == 0,
                "mutant argumansiz kolu bozmamali (harness saglam mi); rc=%d" % rc_argsiz)
        rc_a1, _ = _tek_eksen_kos(kok, "mutarg-alt", mut, BOZUK_ALTKATEGORI)
        rc_a2, _ = _tek_eksen_kos(kok, "mutarg-uyum", mut, BOZUK_UYUM)
        s.bekle("MUT-ARG.eski-eksenler-diri", rc_a1 == 1 and rc_a2 == 1,
                "A1/A2 bu mutanta KOR olmali (yoksa hangi eksenin olctugu ANLASILMAZ); "
                "A1 rc=%d A2 rc=%d" % (rc_a1, rc_a2))
        s.bekle("MUT-ARG.bytecode-bulasmadi",
                not os.path.exists(os.path.join(os.path.dirname(mut), "__pycache__")),
                "mutant dizininde __pycache__ olusmus")

    # --- MUT-KOK: kok turetimi `rev-parse --show-toplevel`a cevrilir ------------
    mut = _mutant_yaz(kok, "MUT-KOK", kaynak, MUT_KOK_CAPA, MUT_KOK_YERINE, s)
    if mut:
        wt, basilan, cikti = _altdizin_kanca_kok(kok, "mutkok", mut)
        s.bekle("MUT-KOK.sonda-kosti", bool(cikti) and basilan is not None,
                "mutant sonda kok satirini basmadi -> mutant OLCULEMEDI; cikti=%s"
                % cikti[-300:])
        s.bekle("MUT-KOK.oldurdu",
                basilan is not None and os.path.realpath(basilan) != wt,
                "kok turetimi `--show-toplevel`e cevrilince KOK-ALT dusmeli; "
                "olculen=%r worktree=%s" % (basilan, wt))
        # ESKI KOL AYIRT EDICI DEGIL: ayni mutant, cwd = agacin TEPESI olan sondada
        # AYNI koku basar -> o kol bu bozulmayi GORMEZ. Kanit burada dursun.
        eski = go.worktree_kanca_kok_olcumu(mut, "katalog-alan-kapisi.py")
        s.bekle("MUT-KOK.eski-kok-kolu-kor", eski["kanca"][2] is True,
                "tepede kosan eski KOK kolu bu mutanti YAKALAMAMALI (yakalasaydi "
                "KOK-ALT gereksiz olurdu); olculen=%r" % (eski["kanca"],))
        rc_a1, _ = _tek_eksen_kos(kok, "mutkok-alt", mut, BOZUK_ALTKATEGORI)
        rc_a2, _ = _tek_eksen_kos(kok, "mutkok-uyum", mut, BOZUK_UYUM)
        s.bekle("MUT-KOK.eski-eksenler-diri", rc_a1 == 1 and rc_a2 == 1,
                "A1/A2 bu mutanta KOR olmali (cwd = agacin tepesi oldugu icin iki kok "
                "turetimi ayni cevabi verir); A1 rc=%d A2 rc=%d" % (rc_a1, rc_a2))
        s.bekle("MUT-KOK.bytecode-bulasmadi",
                not os.path.exists(os.path.join(os.path.dirname(mut), "__pycache__")),
                "mutant dizininde __pycache__ olusmus")


# ---------------------------------------------------------------------------
def main():
    print("KATALOG ALAN KAPISI — KABUL TESTI")
    print("  gercek kapi   : %s" % GERCEK_KAPI)
    print("  gercek katalog: %s (yalniz OKUNUR)" % GERCEK_KATALOG)
    s = Sayac()
    kok = tempfile.mkdtemp(prefix="pruvo-katalog-alan-")
    kok = os.path.realpath(kok)
    try:
        vaka(s, "A — KIRMIZI eksenleri (iki eksen AYRI vakalarda)", vaka_a, kok)
        vaka(s, "B — YESIL / yanlis-pozitif butcesi (GERCEK katalog)", vaka_b, kok)
        vaka(s, "K — kapsam (HEAD'deki eski ihlal kilitlemez)", vaka_kapsam, kok)
        vaka(s, "E — eksen INDEX'tir (calisma agaci degil)", vaka_eksen, kok)
        vaka(s, "O — OLCULEMEDI kolu (rc=2)", vaka_olculemedi, kok)
        vaka(s, "KOK — worktree + gercek kanca baglami", vaka_kok, kok)
        vaka(s, "INDEX — miras alinan GIT_INDEX_FILE", vaka_index_dosyasi, kok)
        vaka(s, "MUT — dogrulama kollarinin AYRI AYRI oldurulmesi", vaka_mutasyon, kok)
        vaka(s, "MUT — arguman kolu (SART 2) + kok turetimi (SART 3)",
             vaka_mutasyon_arg_kok, kok)
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    print("\n" + "-" * 70)
    print("OLCULEN IDDIA: %d   (gecen %d · kalan %d · olculemedi %d)"
          % (s.toplam, s.gecen, s.kalan, s.olculemedi))
    taban_dustu = s.toplam < IDDIA_TABANI
    if taban_dustu:
        print("🔴 IDDIA TABANI DUSTU: olculen %d < beklenen %d (IDDIA_TABANI) — bir "
              "kabul iddiasi SESSIZCE kayboldu. Iddia silmek mesruysa IDDIA_TABANI'ni "
              "AYNI commit'te dusur ve gerekcesini yaz." % (s.toplam, IDDIA_TABANI))
    elif s.toplam > IDDIA_TABANI:
        print("OLCUM: iddia sayisi %d, taban %d — ARTIS serbest (IDDIA_TABANI'ni "
              "yukselt ki capa ilerlesin)." % (s.toplam, IDDIA_TABANI))
    if s.kirmizi:
        print("KIRMIZI-ETIKET: %s" % ", ".join(s.kirmizi))
    kotu = bool(s.kalan or s.olculemedi or taban_dustu)
    print("SONUC: %s" % ("KIRMIZI 🔴" if kotu else "YESIL ✅"))
    return 1 if kotu else 0


if __name__ == "__main__":
    sys.exit(main())
