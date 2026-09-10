#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/nobet-olcum.py — NOBET OLCUMU: butun evler x 6 eksen, TEK kosum, TEK cikti.

NEDEN (olculmus gerekce, 10 Eyl 2026 — kutu blogu `2026-09-10 23:4x OKAN KARARI`):
BaBa'nin iki cron rutini (`gunluk-mimar-ihtar` 09:00 · `teftis-takip` 23:00) ayni
deterministik olcumu HER EVDE AYRI AYRI, LLM turu harcayarak atiyordu. 10 Eyl sayimi:
6 kosum / 403 tur / 51,1M opus = gunun %81'i (09:08 ihtar 66 tur/10,2M · 15:08 ihtar
72/9,3M). Okan karari (23:3x): **olcum deterministik betige, cron yalniz OKUR.**

🔴 BU BETIK HUKUM YAZMAZ. Yalniz sayi + esik asimi BAYRAGI basar (`ASIM=`,
`ARTIK/CANLI/OLCULEMEDI`). Emir/ihtar/hukum blogunu RUTIN yazar (Okan karari ②:
cron kolu hukum yazamaz — betik de yazmaz).

🔴 EV LISTESI KODA CIVILENMEZ. Tek kaynak `~/.claude/cron/evler.json` (K361: PRUVO
reposunun DISINDA). Dosya yok/bozuk/bos ise `EVLER_KAYNAGI=OLCULEMEDI` basilir ve
rc=1 ile DURULUR — sessiz varsayilana DUSULMEZ. Bu, betigin TEK fail-closed kolu;
tek bir evin olculemezligi digerlerini durdurmaz (o ev birebir `OLCULEMEDI` + sebep
alir, rc 0 kalir).

🔴 `evler.json` SEMASI: ad -> Claude HAFIZA PROJE DIZINI (repo yolu DEGIL). Repo
koku oradan TURETILIR; naif `-`->`/` cevirimi cok parcali ev adlarini bozar
(`-Users-okan-dev-faralya-panel` -> `/Users/okan/dev/faralya/panel`, yok). Bkz.
`repo_yolu_turet`.

TAVAN KAYNAKLARI — SAYI BU DOSYAYA YAZILMAZ, SAHIPTEN OKUNUR:
    DEVAM.md    -> tools/defter-kota-taban.py::TAVAN_SATIR / TAVAN_BAYT
    MEMORY.md   -> tools/hafiza-indeks-arsivle.py::VARSAYILAN_TAVAN_SATIR / _BAYT
    ortak kutu  -> tools/kutu-arsivle.py::VARSAYILAN_TAVAN
Tek istisna `CLAUDE.md` bayt tavani: sahip modulu YOKTUR, tek sozlukte durur ve
kaynagi ADIYLA yanina yazilir (bkz. `CLAUDE_TAVAN_BAYT`).

CIKTI (ikisi AYNI kosumdan turer, ikinci kaynak YOK):
    ~/.claude/cron/nobet-olcum.json   — makine okunur
    ~/.claude/cron/nobet-olcum.md     — rutinin okudugu kisa tablo

Kabul testi: tools/nobet-olcum-test.py (CI: .github/workflows/nobet.yml serit-b).
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

OLCULEMEDI = "OLCULEMEDI"

EVLER_JSON_VARSAYILAN = os.path.expanduser("~/.claude/cron/evler.json")
ISCI_LOG_VARSAYILAN = os.path.expanduser("~/.claude/cron/isci.log")
KALP_MD_VARSAYILAN = os.path.expanduser("~/.claude/cron/bekci-teslim-kalp.md")
KALP_JSON_VARSAYILAN = os.path.expanduser("~/.claude/cron/gozcu-kalp.json")
CIKTI_JSON_VARSAYILAN = os.path.expanduser("~/.claude/cron/nobet-olcum.json")
CIKTI_MD_VARSAYILAN = os.path.expanduser("~/.claude/cron/nobet-olcum.md")

# 🔴 `CLAUDE.md` BAYT TAVANI — TEK SOZLUK, KAYNAK ADIYLA:
# `.claude/skills/kral-yordam/SKILL.md` §⑤ DEFTER tablosu (`CLAUDE.md | 12.288 B`).
# Bu eksenin sahip MODULU yoktur (DEVAM/MEMORY/kutu eksenlerinin aksine), o yuzden
# sayi burada durur. Ev basina degisirse ANAHTAR EKLENIR; `*` varsayilandir.
# 🔴 Bu tablo BAYATLAR: ayni skill tablosundaki kutu tavani (300) 10 Eyl'de
# sahibinin degerinden (250) ayrismis ve evin commit'ini KILITLEYENE kadar
# gorunmemisti. Tablo buyurken tavani SAHIBI OLAN eksene tasi.
CLAUDE_TAVAN_BAYT = {"*": 12288}

MOTOR_PENCERE_SN = 24 * 3600  # "son 24 saat" — MOTOR ORANI ekseni

_BASLANGIC_RE = re.compile(
    r"^=== (?P<ts>\S+) BASLANGIC motor=(?P<motor>\S+) ev=(?P<ev>\S+)"
    r"(?:\s+etiket=(?P<etiket>\S+))?")
_BITIS_RE = re.compile(r"^=== (?P<ts>\S+) BITIS rc=(?P<rc>-?\d+)")
_MOTOR_RE = re.compile(r"^MOTOR=(?P<motor>\S+)\s*$")
_ANAHTAR_RE = re.compile(r"\bANAHTAR=(?P<yol>\S+)")
_KOSTU_RE = re.compile(r"^KOSTU=(?P<kol>[^@]+)@(?P<ts>\S+)\s*$")
_TERCIH_RE = re.compile(r"^EV_TERCIH_SIRASI\s*=\s*\(([^)]*)\)", re.MULTILINE)

# Kapanis bekleyen blok jetonu — kutu arsivleyicisinin okudugu satir.
KAPANIS_JETONU = "ARŞİVLENEBİLİRİM"


# ---------------------------------------------------------------------------
# ALTYAPI
# ---------------------------------------------------------------------------
class Sayac:
    """Betigin attigi deterministik komut turlarini sayar (rutinin LLM turu yerine)."""

    def __init__(self):
        self.komut = 0


def kos(sayac, argv, kok=None, zaman_asimi=60):
    """(rc, stdout, stderr) — hic patlamaz; patlarsa rc=None + sebep stderr'de."""
    sayac.komut += 1
    try:
        p = subprocess.run(argv, cwd=kok, capture_output=True, text=True,
                           timeout=zaman_asimi)
    except KeyboardInterrupt:
        raise
    except BaseException as hata:                                  # noqa: BLE001
        return None, "", "komut kosulamadi: %r" % (hata,)
    return p.returncode, p.stdout, p.stderr


def _iso_coz(damga):
    """ISO8601 (Z ya da offset) -> aware datetime; cozulemezse None."""
    if not damga:
        return None
    metin = damga.strip()
    if metin.endswith("Z"):
        metin = metin[:-1] + "+00:00"
    try:
        an = dt.datetime.fromisoformat(metin)
    except ValueError:
        return None
    if an.tzinfo is None:
        an = an.replace(tzinfo=dt.timezone.utc)
    return an


def _simdi():
    return dt.datetime.now(dt.timezone.utc)


# ---------------------------------------------------------------------------
# EVLER.JSON — TEK KAYNAK, FAIL-CLOSED
# ---------------------------------------------------------------------------
def evler_yukle(yol):
    """(ad -> hafiza proje dizini, hata). Yok/bozuk/bos ise (None, sebep).

    Alt cizgiyle baslayan anahtarlar YORUM'dur, ev SAYILMAZ (evler.json `_sema`).
    """
    if not os.path.isfile(yol):
        return None, "dosya yok: %s" % yol
    try:
        with open(yol, encoding="utf-8") as dosya:
            ham = json.load(dosya)
    except KeyboardInterrupt:
        raise
    except BaseException as hata:                                  # noqa: BLE001
        return None, "okunamadi/bozuk: %r" % (hata,)
    if not isinstance(ham, dict):
        return None, "beklenen sozluk, gelen %s" % type(ham).__name__
    tablo = {}
    for ad, deger in ham.items():
        if ad.startswith("_"):
            continue
        if not isinstance(deger, str) or not deger.strip():
            continue
        tablo[ad] = deger.strip()
    if not tablo:
        return None, "tabloda EV yok (yalniz yorum anahtarlari)"
    return tablo, None


def ev_tercih_sirasi(repo_kok):
    """`tools/parti-kapisi.py::EV_TERCIH_SIRASI` — IKINCI KOPYA TUTULMAZ, OKUNUR.

    Ayni repo yoluna birden fazla ad eslesirse (or. KraL ve ORTAK ayni dizini
    gosterir) satirin BIRINCIL adini bu sira belirler. Okunamazsa bos tuple
    doner; cagiran alfabetik sirayi kullanir (fail-soft: yalniz AD secimi).
    """
    yol = os.path.join(repo_kok, "tools", "parti-kapisi.py")
    try:
        with open(yol, encoding="utf-8") as dosya:
            metin = dosya.read()
    except KeyboardInterrupt:
        raise
    except BaseException:                                          # noqa: BLE001
        return (), "okunamadi: %s" % yol
    esleme = _TERCIH_RE.search(metin)
    if not esleme:
        return (), "EV_TERCIH_SIRASI bulunamadi: %s" % yol
    adlar = tuple(p.strip().strip("\"'") for p in esleme.group(1).split(",")
                  if p.strip())
    return adlar, None


def repo_yolu_turet(proje_dizini, kok="/"):
    """Claude hafiza proje dizininden REPO kokunu turetir. (yol, hata).

    🔴 NAIF `-`->`/` CEVIRIMI YANLISTIR. Claude proje dizin adi `/` -> `-`
    kodlamasidir ve KAYIPLIDIR: icinde `-` tasiyan dizin adlari ayirt edilemez.
    `-Users-okan-dev-faralya-panel` naif cevrilirse `/Users/okan/dev/faralya/panel`
    olur (yok) — `faralya-panel` / `faralya-pazarlama` / `pruvo-hasat` gibi
    COK PARCALI ev adlari tam bu yuzden cozulemiyordu (FaR, 10 Eyl 23:5x).
    CARE: soldan yuru, her adimda dosya sistemine sorarak EN UZUN eslesen
    birlesik adi al. Kayipsiz cozum yoktur; olcum dosya sisteminden gelir.
    """
    ad = os.path.basename(os.path.abspath(proje_dizini).rstrip("/"))
    parcalar = [p for p in ad.lstrip("-").split("-") if p]
    if not parcalar:
        return None, "proje dizini adi bos: %s" % proje_dizini
    yol = kok
    i = 0
    while i < len(parcalar):
        for j in range(len(parcalar), i, -1):
            aday = os.path.join(yol, "-".join(parcalar[i:j]))
            if os.path.isdir(aday):
                yol, i = aday, j
                break
        else:
            return None, ("repo koku cozulemedi (takildigi parca=%r, gelinen=%s)"
                          % (parcalar[i], yol))
    return yol, None


# ---------------------------------------------------------------------------
# TAVANLAR — SAHIPTEN OKU (sayi yazma)
# ---------------------------------------------------------------------------
def _sabit_oku(yol, ad):
    """Bir .py dosyasindan `AD = <tamsayi>` degerini metinden okur. (deger, hata).

    Import edilmez: sahip moduller (kutu-arsivle / hafiza-indeks-arsivle) modul
    duzeyinde IS yapabiliyor; tavan okumak icin o bedeli odemeye gerek yok.
    """
    if not os.path.isfile(yol):
        return None, "sahip dosyasi yok: %s" % yol
    try:
        with open(yol, encoding="utf-8") as dosya:
            metin = dosya.read()
    except KeyboardInterrupt:
        raise
    except BaseException as hata:                                  # noqa: BLE001
        return None, "sahip okunamadi (%s): %r" % (yol, hata)
    esleme = re.search(r"^%s\s*=\s*(\d+)\s*$" % re.escape(ad), metin, re.MULTILINE)
    if not esleme:
        return None, "%s::%s bulunamadi" % (os.path.basename(yol), ad)
    return int(esleme.group(1)), None


def tavanlar_coz(repo_kok):
    """Tavan sozlugu + kaynak defteri. Bulunamayan eksen None + sebep alir."""
    tools = os.path.join(repo_kok, "tools")
    kaynaklar = {}
    tavan = {}
    for anahtar, dosya, ad in (
            ("devam_satir", "defter-kota-taban.py", "TAVAN_SATIR"),
            ("devam_bayt", "defter-kota-taban.py", "TAVAN_BAYT"),
            ("memory_satir", "hafiza-indeks-arsivle.py", "VARSAYILAN_TAVAN_SATIR"),
            ("memory_bayt", "hafiza-indeks-arsivle.py", "VARSAYILAN_TAVAN_BAYT"),
            ("kutu_satir", "kutu-arsivle.py", "VARSAYILAN_TAVAN")):
        deger, hata = _sabit_oku(os.path.join(tools, dosya), ad)
        tavan[anahtar] = deger
        kaynaklar[anahtar] = ("%s::%s" % (dosya, ad)) if deger is not None \
            else "%s (%s::%s — %s)" % (OLCULEMEDI, dosya, ad, hata)
    tavan["claude_bayt"] = CLAUDE_TAVAN_BAYT
    kaynaklar["claude_bayt"] = ("nobet-olcum.py::CLAUDE_TAVAN_BAYT "
                                "(kaynak: .claude/skills/kral-yordam/SKILL.md §⑤)")
    return tavan, kaynaklar


def asim_bayragi(satir, tavan_satir, bayt, tavan_bayt):
    """`SATIR` | `BAYT` | `IKISI` | `""` — hukum DEGIL, esik asimi BAYRAGI."""
    satir_as = (tavan_satir is not None and satir is not None and satir > tavan_satir)
    bayt_as = (tavan_bayt is not None and bayt is not None and bayt > tavan_bayt)
    if satir_as and bayt_as:
        return "IKISI"
    if satir_as:
        return "SATIR"
    if bayt_as:
        return "BAYT"
    return ""


def dosya_olcusu(yol):
    """(satir, bayt, hata) — dosya yoksa (None, None, sebep)."""
    if not os.path.isfile(yol):
        return None, None, "dosya yok"
    try:
        with open(yol, "rb") as dosya:
            ham = dosya.read()
    except KeyboardInterrupt:
        raise
    except BaseException as hata:                                  # noqa: BLE001
        return None, None, "okunamadi: %r" % (hata,)
    satir = ham.count(b"\n") + (0 if (not ham or ham.endswith(b"\n")) else 1)
    return satir, len(ham), None


# ---------------------------------------------------------------------------
# EKSEN a — DEFTER / CLAUDE / MEMORY
# ---------------------------------------------------------------------------
def defter_olc(repo_kok, hafiza_dizin, ev, tavan):
    sonuc = {}
    devam_satir, devam_bayt, hata = dosya_olcusu(os.path.join(repo_kok, "DEVAM.md"))
    sonuc["DEVAM"] = {
        "satir": devam_satir, "bayt": devam_bayt,
        "tavan_satir": tavan["devam_satir"], "tavan_bayt": tavan["devam_bayt"],
        "ASIM": asim_bayragi(devam_satir, tavan["devam_satir"],
                             devam_bayt, tavan["devam_bayt"]),
        "hata": hata,
    }
    _, claude_bayt, hata = dosya_olcusu(os.path.join(repo_kok, "CLAUDE.md"))
    claude_tavan = tavan["claude_bayt"].get(ev, tavan["claude_bayt"].get("*"))
    sonuc["CLAUDE"] = {
        "bayt": claude_bayt, "tavan_bayt": claude_tavan,
        "ASIM": asim_bayragi(None, None, claude_bayt, claude_tavan),
        "hata": hata,
    }
    # 🔴 MEMORY.md'nin YERI EVE GORE DEGISIR (olculdu, 10 Eyl): KraL/MaCiT/...
    # `<proje>/memory/MEMORY.md`, `faralya-panel` (eLiF) ise `<proje>/MEMORY.md`.
    # Tek konuma civilenirse o evin ekseni SESSIZCE `dosya yok` olur ve tavan
    # asimi hic olculmez. Iki konum da DENENIR; ikisi de yoksa sebep yazilir.
    mem_adaylar = (os.path.join(hafiza_dizin, "memory", "MEMORY.md"),
                   os.path.join(hafiza_dizin, "MEMORY.md"))
    mem_yol = mem_adaylar[0]
    mem_satir = mem_bayt = None
    hata = "dosya yok (denenen: %s)" % " · ".join(mem_adaylar)
    for aday in mem_adaylar:
        satir, bayt, aday_hata = dosya_olcusu(aday)
        if aday_hata is None:
            mem_yol, mem_satir, mem_bayt, hata = aday, satir, bayt, None
            break
    sonuc["MEMORY"] = {
        "yol": mem_yol, "satir": mem_satir, "bayt": mem_bayt,
        "tavan_satir": tavan["memory_satir"], "tavan_bayt": tavan["memory_bayt"],
        "ASIM": asim_bayragi(mem_satir, tavan["memory_satir"],
                             mem_bayt, tavan["memory_bayt"]),
        "hata": hata,
    }
    return sonuc


# ---------------------------------------------------------------------------
# EKSEN b — GIT DURUMU
# ---------------------------------------------------------------------------
def git_durumu(sayac, repo_kok):
    """status satiri · UU · remote BOS mu · main'in origin'e gore ileri/geri."""
    sonuc = {"kirli": None, "UU": None, "remote_bos": None, "remote_satir": None,
             "ileri": None, "geri": None, "rc": {}, "hata": None}
    rc, cikti, err = kos(sayac, ["git", "-C", repo_kok, "status", "--porcelain"])
    sonuc["rc"]["status"] = rc
    if rc != 0:
        sonuc["hata"] = "git status rc=%s: %s" % (rc, (err or "").strip()[:160])
        return sonuc
    satirlar = [s for s in cikti.splitlines() if s.strip()]
    sonuc["kirli"] = len(satirlar)
    sonuc["UU"] = sum(1 for s in satirlar if s[:2] == "UU")

    rc, cikti, err = kos(sayac, ["git", "-C", repo_kok, "remote", "-v"])
    sonuc["rc"]["remote"] = rc
    if rc == 0:
        uzak = [s for s in cikti.splitlines() if s.strip()]
        sonuc["remote_satir"] = len(uzak)
        # 🔴 FILO DERSI (BaBa, 4 Eyl): `git remote -v` BOS = kirmizi. Betik hukum
        # yazmaz, yalniz BAYRAGI basar; hukmu rutin kurar.
        sonuc["remote_bos"] = (len(uzak) == 0)

    rc, cikti, err = kos(sayac, ["git", "-C", repo_kok, "rev-list",
                                 "--left-right", "--count", "main...origin/main"])
    sonuc["rc"]["ileri_geri"] = rc
    if rc == 0:
        parcalar = cikti.split()
        if len(parcalar) == 2 and all(p.isdigit() for p in parcalar):
            sonuc["ileri"], sonuc["geri"] = int(parcalar[0]), int(parcalar[1])
    return sonuc


# ---------------------------------------------------------------------------
# EKSEN c — WORKTREE ARTIK OLCUSU (BaBa, 10 Eyl 17:0x: tavan SAYI DEGIL ARTIK)
# ---------------------------------------------------------------------------
def worktree_bloklari(cikti):
    """`git worktree list --porcelain` ciktisini blok sozluklerine cevirir."""
    bloklar = []
    gecerli = {}
    for satir in cikti.splitlines():
        satir = satir.rstrip()
        if not satir:
            if gecerli:
                bloklar.append(gecerli)
                gecerli = {}
            continue
        if " " in satir:
            ad, _, deger = satir.partition(" ")
        else:
            ad, deger = satir, ""
        gecerli[ad] = deger
    if gecerli:
        bloklar.append(gecerli)
    return bloklar


def worktree_artik_olc(sayac, repo_kok, ana_dal="main"):
    """Her worktree icin ARTIK / CANLI / OLCULEMEDI.

    ARTIK  = calisma agaci TEMIZ **ve** HEAD `main`in ATASI (icerik main'de).
    CANLI  = ikisinden biri tutmuyor (kirli ya da main'de olmayan is var).
    OLCULEMEDI = olcum komutu dustu.
    🔴 Sinif HUKUM DEGILDIR: "kaldirilir mi" karari rutinin/mimarin — canli
    oturum / acik cip / `locked` muafiyetleri bu betikte YARGILANMAZ, `kilitli`
    alani ham olarak tasinir.
    """
    rc, cikti, err = kos(sayac, ["git", "-C", repo_kok, "worktree", "list",
                                 "--porcelain"])
    if rc != 0:
        return None, "git worktree list rc=%s: %s" % (rc, (err or "").strip()[:160])
    agaclar = []
    ana = os.path.abspath(repo_kok).rstrip("/")
    for blok in worktree_bloklari(cikti):
        yol = blok.get("worktree")
        if not yol:
            continue
        mutlak = os.path.abspath(yol).rstrip("/")
        if mutlak == ana:
            continue  # ana checkout artik olmaz
        kayit = {
            "yol": mutlak,
            "ad": os.path.basename(mutlak),
            "HEAD": blok.get("HEAD"),
            "dal": blok.get("branch") or ("(detached)" if "detached" in blok else None),
            "kilitli": "locked" in blok,
            "kirli": None,
            "main_atasi": None,
            "SINIF": OLCULEMEDI,
            "sebep": None,
        }
        drc, dcikti, derr = kos(sayac, ["git", "-C", mutlak, "status", "--porcelain"])
        if drc != 0:
            kayit["sebep"] = "status rc=%s: %s" % (drc, (derr or "").strip()[:120])
            agaclar.append(kayit)
            continue
        kayit["kirli"] = len([s for s in dcikti.splitlines() if s.strip()])
        if not kayit["HEAD"]:
            kayit["sebep"] = "HEAD okunamadi (worktree list blogunda yok)"
            agaclar.append(kayit)
            continue
        arc, _, aerr = kos(sayac, ["git", "-C", repo_kok, "merge-base",
                                   "--is-ancestor", kayit["HEAD"], ana_dal])
        if arc is None or arc not in (0, 1):
            kayit["sebep"] = "merge-base rc=%s: %s" % (arc, (aerr or "").strip()[:120])
            agaclar.append(kayit)
            continue
        kayit["main_atasi"] = (arc == 0)
        kayit["SINIF"] = "ARTIK" if (kayit["kirli"] == 0 and kayit["main_atasi"]) \
            else "CANLI"
        agaclar.append(kayit)
    return agaclar, None


# ---------------------------------------------------------------------------
# EKSEN d — MOTOR ORANI (ev bazinda, son 24 saat)
# ---------------------------------------------------------------------------
def ev_eslestir(ev_jetonu, anahtar_yolu, basename_haritasi):
    """(ev|None, nasil) — `isci.log` kosumunu EV adina cozer.

    🔴 TAM BASENAME ile eslesilir, `-`'den PARCALANMAZ. Eski (tek-parcali) esleme
    `faralya-panel` jetonunu `faralya`ya kirpiyor ve kosumu YANLIS eve (FaR)
    katliyordu; `faralya-panel` (eLiF) ve `faralya-pazarlama` (EyLüL) kovalari
    0 goruniyordu — FaR'in 10 Eyl 23:5x notunun kok nedeni budur.
    🔴 IKINCI KOL: `ev=` alani worktree/alt-ajan adi olabilir (`elated-mccarthy-26ab4a`,
    `agent-...`). O halde ayni blokta duran `ANAHTAR=<tam yol>` uzerinden YUKARI
    yurunur; yoksa kosum `bilinmeyen:` kovasinda kalir (ve o kova ciktida GORUNUR,
    sessizce yutulmaz).
    """
    jeton = (ev_jetonu or "").strip().rstrip("/")
    if jeton:
        if "/" in jeton:
            jeton = os.path.basename(jeton)
        ev = basename_haritasi.get(jeton)
        if ev:
            return ev, "ev-alani"
    if anahtar_yolu:
        aday = os.path.abspath(anahtar_yolu).rstrip("/")
        gorulen = 0
        while aday and aday != "/" and gorulen < 32:
            gorulen += 1
            ev = basename_haritasi.get(os.path.basename(aday))
            if ev:
                return ev, "anahtar-yolu"
            aday = os.path.dirname(aday)
    return None, "eslesmedi"


def motor_orani(log_metni, basename_haritasi, simdi=None, pencere_sn=MOTOR_PENCERE_SN):
    """isci.log -> {ev: {motor: sayi}} + `bilinmeyen:<jeton>` kovasi + ozet."""
    simdi = simdi or _simdi()
    esik = simdi - dt.timedelta(seconds=pencere_sn)
    evler = {}
    bilinmeyen = {}
    toplam = {"kosum": 0, "pencere_ici": 0, "motor_satiri": 0, "eslesmeyen_kosum": 0}
    blok = None

    def blogu_kapat(blok):
        if blok is None:
            return
        toplam["kosum"] += 1
        if blok["ts"] is None or blok["ts"] < esik:
            return
        toplam["pencere_ici"] += 1
        ev, _nasil = ev_eslestir(blok["ev"], blok["anahtar"], basename_haritasi)
        if ev is None:
            toplam["eslesmeyen_kosum"] += 1
            kova = bilinmeyen.setdefault("bilinmeyen:%s" % (blok["ev"] or "-"), {})
        else:
            kova = evler.setdefault(ev, {})
        for motor in blok["motorlar"]:
            kova[motor] = kova.get(motor, 0) + 1
            toplam["motor_satiri"] += 1

    for satir in log_metni.splitlines():
        bas = _BASLANGIC_RE.match(satir)
        if bas:
            blogu_kapat(blok)
            blok = {"ts": _iso_coz(bas.group("ts")), "ev": bas.group("ev"),
                    "anahtar": None, "motorlar": []}
            continue
        if blok is None:
            continue
        mot = _MOTOR_RE.match(satir)
        if mot:
            blok["motorlar"].append(mot.group("motor"))
            continue
        anahtar = _ANAHTAR_RE.search(satir)
        if anahtar and blok["anahtar"] is None:
            blok["anahtar"] = anahtar.group("yol")
            continue
        if _BITIS_RE.match(satir):
            blogu_kapat(blok)
            blok = None
    blogu_kapat(blok)

    kovalar = dict(evler)
    kovalar.update(bilinmeyen)
    return {"kovalar": kovalar, "ozet": toplam,
            "pencere_sn": pencere_sn, "esik": esik.isoformat()}


# ---------------------------------------------------------------------------
# EKSEN e — ORTAK KUTU
# ---------------------------------------------------------------------------
def kutu_olc(repo_kok, tavan_satir):
    """Kutu satiri + tavani + kapanis bekleyen blok sayisi."""
    yol_sabit = os.path.join(repo_kok, "tools", "kutu-arsivle.py")
    yol = None
    hata = None
    if os.path.isfile(yol_sabit):
        try:
            with open(yol_sabit, encoding="utf-8") as dosya:
                metin = dosya.read()
            esleme = re.search(
                r"^KUTU_VARSAYILAN\s*=\s*os\.path\.expanduser\(\s*\n?\s*"
                r"[\"'](?P<yol>[^\"']+)[\"']", metin, re.MULTILINE)
            if esleme:
                yol = os.path.expanduser(esleme.group("yol"))
            else:
                hata = "kutu-arsivle.py::KUTU_VARSAYILAN cozulemedi"
        except KeyboardInterrupt:
            raise
        except BaseException as h:                                 # noqa: BLE001
            hata = "kutu-arsivle.py okunamadi: %r" % (h,)
    else:
        hata = "kutu-arsivle.py yok: %s" % yol_sabit
    if yol is None:
        return {"yol": None, "satir": None, "tavan_satir": tavan_satir,
                "ASIM": "", "kapanis_bekleyen": None, "hata": hata or OLCULEMEDI}
    satir, bayt, dhata = dosya_olcusu(yol)
    bekleyen = None
    if dhata is None:
        try:
            with open(yol, encoding="utf-8") as dosya:
                bekleyen = dosya.read().count(KAPANIS_JETONU)
        except KeyboardInterrupt:
            raise
        except BaseException as h:                                 # noqa: BLE001
            dhata = "kapanis jetonu sayilamadi: %r" % (h,)
    return {"yol": yol, "satir": satir, "bayt": bayt, "tavan_satir": tavan_satir,
            "ASIM": asim_bayragi(satir, tavan_satir, None, None),
            "kapanis_bekleyen": bekleyen, "hata": dhata or hata}


# ---------------------------------------------------------------------------
# EKSEN f — BEKCI KALBI
# ---------------------------------------------------------------------------
def kalp_olc(kalp_md, kalp_json, simdi=None):
    """Iki kalp dosyasinin son damga YASI (dk). Damga yoksa mtime yasi + sebep."""
    simdi = simdi or _simdi()
    sonuc = {}

    kayit = {"yol": kalp_md, "damga": None, "yas_dk": None, "kol": None, "hata": None}
    if not os.path.isfile(kalp_md):
        kayit["hata"] = "dosya yok"
    else:
        try:
            with open(kalp_md, encoding="utf-8") as dosya:
                satirlar = dosya.read().splitlines()
        except KeyboardInterrupt:
            raise
        except BaseException as h:                                 # noqa: BLE001
            kayit["hata"] = "okunamadi: %r" % (h,)
            satirlar = []
        son = None
        for satir in satirlar:
            esleme = _KOSTU_RE.match(satir.strip())
            if esleme:
                an = _iso_coz(esleme.group("ts"))
                if an is not None and (son is None or an > son[0]):
                    son = (an, esleme.group("kol"))
        if son is None and kayit["hata"] is None:
            kayit["hata"] = "KOSTU=<kol>@<ISO> satiri bulunamadi"
        elif son is not None:
            kayit["damga"] = son[0].isoformat()
            kayit["kol"] = son[1]
            kayit["yas_dk"] = round((simdi - son[0]).total_seconds() / 60.0, 1)
    sonuc["bekci_teslim_kalp"] = kayit

    kayit = {"yol": kalp_json, "damga": None, "yas_dk": None, "hata": None}
    if not os.path.isfile(kalp_json):
        kayit["hata"] = "dosya yok"
    else:
        try:
            with open(kalp_json, encoding="utf-8") as dosya:
                ham = json.load(dosya)
        except KeyboardInterrupt:
            raise
        except BaseException as h:                                 # noqa: BLE001
            ham = None
            kayit["hata"] = "okunamadi/bozuk: %r" % (h,)
        if isinstance(ham, dict):
            an = _iso_coz(ham.get("damga"))
            if an is None:
                kayit["hata"] = "`damga` alani yok/cozulemedi"
            else:
                kayit["damga"] = an.isoformat()
                kayit["yas_dk"] = round((simdi - an).total_seconds() / 60.0, 1)
    sonuc["gozcu_kalp"] = kayit
    return sonuc


# ---------------------------------------------------------------------------
# TOPLAYICI
# ---------------------------------------------------------------------------
def olc(evler_json=EVLER_JSON_VARSAYILAN, isci_log=ISCI_LOG_VARSAYILAN,
        kalp_md=KALP_MD_VARSAYILAN, kalp_json=KALP_JSON_VARSAYILAN,
        repo_kok=None, fs_kok="/", simdi=None, ana_dal="main"):
    """Tek kosum, tek sozluk. rc=1 YALNIZ `EVLER_KAYNAGI` dustugunde."""
    bas = time.time()
    simdi = simdi or _simdi()
    sayac = Sayac()
    repo_kok = repo_kok or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    rapor = {
        "sema": "nobet-olcum/1",
        "damga": simdi.isoformat(),
        "repo_kok": repo_kok,
        "EVLER_KAYNAGI": evler_json,
        "rc": 0,
        "evler": [],
        "motor_orani": None,
        "kutu": None,
        "kalp": None,
    }

    tablo, hata = evler_yukle(evler_json)
    if tablo is None:
        # 🔴 TEK FAIL-CLOSED KOL: ev listesi yoksa sessiz varsayilana DUSULMEZ.
        rapor["EVLER_KAYNAGI"] = OLCULEMEDI
        rapor["EVLER_KAYNAGI_SEBEP"] = hata
        rapor["rc"] = 1
        rapor["sure_sn"] = round(time.time() - bas, 3)
        rapor["komut_turu"] = sayac.komut
        return rapor

    tavan, tavan_kaynaklari = tavanlar_coz(repo_kok)
    rapor["tavan_kaynaklari"] = tavan_kaynaklari
    tercih, tercih_hata = ev_tercih_sirasi(repo_kok)
    rapor["ev_tercih_kaynagi"] = ("parti-kapisi.py::EV_TERCIH_SIRASI"
                                  if tercih else "%s (%s)" % (OLCULEMEDI, tercih_hata))

    # ad -> repo koku; ayni koke dusen adlar TEK satirda birlesir (ORTAK = KraL aynasi)
    koke_gore = {}
    cozulemeyen = []
    for ad in sorted(tablo):
        yol, hata = repo_yolu_turet(tablo[ad], kok=fs_kok)
        if yol is None:
            cozulemeyen.append({"ev": ad, "hafiza_dizin": tablo[ad],
                                "SINIF": OLCULEMEDI, "sebep": hata})
            continue
        koke_gore.setdefault(yol, []).append(ad)

    def birincil(adlar):
        for secim in tercih:
            if secim in adlar:
                return secim
        return sorted(adlar)[0]

    basename_haritasi = {}
    for yol, adlar in koke_gore.items():
        basename_haritasi[os.path.basename(yol)] = birincil(adlar)
    rapor["basename_haritasi"] = dict(sorted(basename_haritasi.items()))

    siralama = sorted(koke_gore.items(),
                      key=lambda p: (tercih.index(birincil(p[1]))
                                     if birincil(p[1]) in tercih else len(tercih),
                                     birincil(p[1])))
    for yol, adlar in siralama:
        ev = birincil(adlar)
        kayit = {"ev": ev, "adlar": sorted(adlar), "repo_kok": yol,
                 "hafiza_dizin": tablo[ev], "SINIF": "OLCULDU", "sebep": None}
        if not os.path.isdir(os.path.join(yol, ".git")) and \
                not os.path.isfile(os.path.join(yol, ".git")):
            kayit["SINIF"] = OLCULEMEDI
            kayit["sebep"] = "git deposu degil: %s" % yol
            rapor["evler"].append(kayit)
            continue
        kayit["defter"] = defter_olc(yol, tablo[ev], ev, tavan)
        kayit["git"] = git_durumu(sayac, yol)
        agaclar, wt_hata = worktree_artik_olc(sayac, yol, ana_dal=ana_dal)
        if agaclar is None:
            kayit["worktree"] = {"SINIF": OLCULEMEDI, "sebep": wt_hata, "agaclar": []}
        else:
            kayit["worktree"] = {
                "agaclar": agaclar,
                "toplam": len(agaclar),
                "ARTIK": sum(1 for a in agaclar if a["SINIF"] == "ARTIK"),
                "CANLI": sum(1 for a in agaclar if a["SINIF"] == "CANLI"),
                OLCULEMEDI: sum(1 for a in agaclar if a["SINIF"] == OLCULEMEDI),
            }
        rapor["evler"].append(kayit)
        # 🔴 WORKTREE ADI DA EV ESLEMESINE GIRER: `isci.log`'da `ev=` alani bir
        # worktree adi olabilir (`elated-mccarthy-26ab4a`, `tekin-gunluk-20260910`)
        # ve o blokta `ANAHTAR=` her zaman DURMAZ -> kosum `bilinmeyen:` kovasinda
        # kalirdi. Olculdu (10 Eyl): 3 kosum bu yuzden eve katlanmiyordu.
        for agac in ((kayit.get("worktree") or {}).get("agaclar") or []):
            basename_haritasi.setdefault(agac["ad"], ev)
    rapor["evler"].extend(cozulemeyen)
    rapor["basename_haritasi"] = dict(sorted(basename_haritasi.items()))

    # EKSEN d
    if os.path.isfile(isci_log):
        try:
            with open(isci_log, encoding="utf-8", errors="replace") as dosya:
                rapor["motor_orani"] = motor_orani(dosya.read(), basename_haritasi,
                                                   simdi=simdi)
        except KeyboardInterrupt:
            raise
        except BaseException as h:                                 # noqa: BLE001
            rapor["motor_orani"] = {"SINIF": OLCULEMEDI,
                                    "sebep": "isci.log okunamadi: %r" % (h,)}
    else:
        rapor["motor_orani"] = {"SINIF": OLCULEMEDI,
                                "sebep": "isci.log yok: %s" % isci_log}

    rapor["kutu"] = kutu_olc(repo_kok, tavan["kutu_satir"])
    rapor["kalp"] = kalp_olc(kalp_md, kalp_json, simdi=simdi)
    rapor["sure_sn"] = round(time.time() - bas, 3)
    rapor["komut_turu"] = sayac.komut
    return rapor


# ---------------------------------------------------------------------------
# MD CIKTISI — ayni rapordan turer, ikinci kaynak YOK
# ---------------------------------------------------------------------------
def _sayi(deger):
    return OLCULEMEDI if deger is None else str(deger)


def md_uret(rapor):
    satirlar = []
    satirlar.append("# NOBET OLCUM — %s" % rapor.get("damga"))
    satirlar.append("")
    satirlar.append("🔴 BU DOSYA HUKUM ICERMEZ. Yalniz sayi + esik asimi bayragi; "
                    "emir blogunu RUTIN yazar.")
    satirlar.append("")
    satirlar.append("- `EVLER_KAYNAGI` = `%s`" % rapor.get("EVLER_KAYNAGI"))
    if rapor.get("EVLER_KAYNAGI") == OLCULEMEDI:
        satirlar.append("- **SEBEP:** %s" % rapor.get("EVLER_KAYNAGI_SEBEP"))
        satirlar.append("- rc = %s" % rapor.get("rc"))
        satirlar.append("- sure = %s sn · komut turu = %s"
                        % (rapor.get("sure_sn"), rapor.get("komut_turu")))
        return "\n".join(satirlar) + "\n"
    satirlar.append("- sure = **%s sn** · deterministik komut turu = **%s** · rc = %s"
                    % (rapor.get("sure_sn"), rapor.get("komut_turu"), rapor.get("rc")))
    satirlar.append("- ev sayisi = **%d**" % len(rapor.get("evler") or []))
    satirlar.append("")

    satirlar.append("## EV TABLOSU (a · b · c)")
    satirlar.append("")
    satirlar.append("| ev | DEVAM st/B (ASIM) | CLAUDE B (ASIM) | MEMORY st/B (ASIM) "
                    "| status | UU | remote | main ileri/geri | worktree ARTIK/CANLI/? |")
    satirlar.append("|---|---|---|---|---|---|---|---|---|")
    for ev in rapor.get("evler") or []:
        if ev.get("SINIF") == OLCULEMEDI:
            satirlar.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s |"
                            % (ev.get("ev"), OLCULEMEDI, OLCULEMEDI, OLCULEMEDI,
                               OLCULEMEDI, OLCULEMEDI, OLCULEMEDI, OLCULEMEDI,
                               OLCULEMEDI))
            satirlar.append("| ↳ sebep | %s |||||||||" % ev.get("sebep"))
            continue
        d = ev["defter"]
        g = ev["git"]
        w = ev["worktree"]
        wt = ("%s/%s/%s" % (w.get("ARTIK"), w.get("CANLI"), w.get(OLCULEMEDI))
              if "ARTIK" in w else OLCULEMEDI)
        satirlar.append(
            "| `%s` | %s/%s (%s) | %s (%s) | %s/%s (%s) | %s | %s | %s | %s/%s | %s |"
            % (ev["ev"],
               _sayi(d["DEVAM"]["satir"]), _sayi(d["DEVAM"]["bayt"]),
               d["DEVAM"]["ASIM"] or "-",
               _sayi(d["CLAUDE"]["bayt"]), d["CLAUDE"]["ASIM"] or "-",
               _sayi(d["MEMORY"]["satir"]), _sayi(d["MEMORY"]["bayt"]),
               d["MEMORY"]["ASIM"] or "-",
               _sayi(g["kirli"]), _sayi(g["UU"]),
               ("BOS" if g.get("remote_bos") else _sayi(g.get("remote_satir"))),
               _sayi(g.get("ileri")), _sayi(g.get("geri")), wt))
    satirlar.append("")
    # 🔴 OLCULEMEDI SEBEPSIZ BASILMAZ: tabloda hucre `OLCULEMEDI` gorunuyorsa
    # sebebi BURADA durur. Sebepsiz OLCULEMEDI, "bos kova" ile "olcemedim"i
    # birbirine benzetir ([[hukum-yanlis-birimde]]).
    olculemedi = []
    for ev in rapor.get("evler") or []:
        if ev.get("SINIF") == OLCULEMEDI:
            olculemedi.append("`%s` · EV · %s" % (ev.get("ev"), ev.get("sebep")))
            continue
        for eksen in ("DEVAM", "CLAUDE", "MEMORY"):
            hata = (ev.get("defter") or {}).get(eksen, {}).get("hata")
            if hata:
                olculemedi.append("`%s` · %s · %s" % (ev["ev"], eksen, hata))
        if (ev.get("git") or {}).get("hata"):
            olculemedi.append("`%s` · git · %s" % (ev["ev"], ev["git"]["hata"]))
        w = ev.get("worktree") or {}
        if w.get("SINIF") == OLCULEMEDI:
            olculemedi.append("`%s` · worktree · %s" % (ev["ev"], w.get("sebep")))
        for agac in (w.get("agaclar") or []):
            if agac["SINIF"] == OLCULEMEDI:
                olculemedi.append("`%s` · worktree `%s` · %s"
                                  % (ev["ev"], agac["ad"], agac.get("sebep")))
    satirlar.append("### %s SEBEPLERI (%d)" % (OLCULEMEDI, len(olculemedi)))
    satirlar.append("")
    for satir in olculemedi or ["- YOK"]:
        satirlar.append("- %s" % satir if not satir.startswith("- ") else satir)
    satirlar.append("")
    satirlar.append("Tavan kaynaklari: %s"
                    % "; ".join("`%s` → %s" % (a, k) for a, k
                                in sorted((rapor.get("tavan_kaynaklari") or {}).items())))
    satirlar.append("")

    satirlar.append("## ARTIK/CANLI WORKTREE DOKUMU (c)")
    satirlar.append("")
    satirlar.append("| ev | agac | SINIF | kirli | main atasi | kilitli | dal |")
    satirlar.append("|---|---|---|---|---|---|---|")
    dokum = 0
    for ev in rapor.get("evler") or []:
        for agac in ((ev.get("worktree") or {}).get("agaclar") or []):
            dokum += 1
            satirlar.append("| `%s` | `%s` | %s | %s | %s | %s | %s |"
                            % (ev.get("ev"), agac["ad"], agac["SINIF"],
                               _sayi(agac["kirli"]), _sayi(agac["main_atasi"]),
                               "EVET" if agac["kilitli"] else "hayir",
                               agac.get("dal") or "-"))
    if dokum == 0:
        satirlar.append("| — | — | — | — | — | — | — |")
    satirlar.append("")

    satirlar.append("## MOTOR ORANI (d · son %s saat)"
                    % int((rapor.get("motor_orani") or {}).get("pencere_sn",
                                                               MOTOR_PENCERE_SN) / 3600))
    satirlar.append("")
    mo = rapor.get("motor_orani") or {}
    if mo.get("SINIF") == OLCULEMEDI:
        satirlar.append("`%s` — %s" % (OLCULEMEDI, mo.get("sebep")))
    else:
        satirlar.append("| kova | motorlar |")
        satirlar.append("|---|---|")
        for kova, motorlar in sorted((mo.get("kovalar") or {}).items()):
            satirlar.append("| `%s` | %s | " % (
                kova, ", ".join("%s=%d" % (m, n) for m, n in sorted(motorlar.items()))))
        ozet = mo.get("ozet") or {}
        satirlar.append("")
        satirlar.append("Ozet: kosum **%s** · pencere ici **%s** · `MOTOR=` satiri "
                        "**%s** · eve eslesmeyen kosum **%s**"
                        % (ozet.get("kosum"), ozet.get("pencere_ici"),
                           ozet.get("motor_satiri"), ozet.get("eslesmeyen_kosum")))
    satirlar.append("")

    k = rapor.get("kutu") or {}
    satirlar.append("## ORTAK KUTU (e) · BEKCI KALBI (f)")
    satirlar.append("")
    satirlar.append("- kutu satir **%s** / tavan **%s** (ASIM=%s) · kapanis bekleyen "
                    "(`%s`) **%s** · hata: %s"
                    % (_sayi(k.get("satir")), _sayi(k.get("tavan_satir")),
                       k.get("ASIM") or "-", KAPANIS_JETONU,
                       _sayi(k.get("kapanis_bekleyen")), k.get("hata") or "-"))
    for ad, kayit in sorted((rapor.get("kalp") or {}).items()):
        satirlar.append("- `%s` son damga **%s** · yas **%s dk** · hata: %s"
                        % (ad, kayit.get("damga") or OLCULEMEDI,
                           _sayi(kayit.get("yas_dk")), kayit.get("hata") or "-"))
    satirlar.append("")
    return "\n".join(satirlar) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evler-json", default=EVLER_JSON_VARSAYILAN)
    ap.add_argument("--isci-log", default=ISCI_LOG_VARSAYILAN)
    ap.add_argument("--cikti-json", default=CIKTI_JSON_VARSAYILAN)
    ap.add_argument("--cikti-md", default=CIKTI_MD_VARSAYILAN)
    ap.add_argument("--fs-kok", default="/",
                    help="repo koku turetiminde taban dizin (kabul testi icin)")
    ap.add_argument("--repo-kok", default=None,
                    help="tavan/kutu sahiplerinin okundugu KraL checkout'u")
    ap.add_argument("--yazma", action="store_true",
                    help="dosyaya YAZMA, yalniz stdout (kuru kosum)")
    a = ap.parse_args(argv)

    rapor = olc(evler_json=a.evler_json, isci_log=a.isci_log,
                repo_kok=a.repo_kok, fs_kok=a.fs_kok)
    metin = md_uret(rapor)
    if not a.yazma:
        for yol, icerik in ((a.cikti_json, json.dumps(rapor, ensure_ascii=False,
                                                      indent=2, sort_keys=True) + "\n"),
                            (a.cikti_md, metin)):
            try:
                os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
                with open(yol, "w", encoding="utf-8") as dosya:
                    dosya.write(icerik)
            except KeyboardInterrupt:
                raise
            except BaseException as h:                             # noqa: BLE001
                print("!! cikti yazilamadi (%s): %r" % (yol, h), file=sys.stderr)
    sys.stdout.write(metin)
    if rapor.get("EVLER_KAYNAGI") == OLCULEMEDI:
        print("EVLER_KAYNAGI=%s — %s" % (OLCULEMEDI,
                                         rapor.get("EVLER_KAYNAGI_SEBEP")),
              file=sys.stderr)
    return int(rapor.get("rc") or 0)


if __name__ == "__main__":
    sys.exit(main())
