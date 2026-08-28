#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gecici_worktree.py — GECICI (temp-koklu) worktree fiksturlerinin TEK KAYNAGI.

NEDEN VAR (olculdu 28 Agu 2026, cip `KraL-DiskFikstur-28Agu`):
Bazi kapi bataryalari hermetiklik icin GERCEK repoya sistem gecici dizini altinda bir
worktree KAYDEDER (`git -C <gercek-repo> worktree add <tmp>/...`). Bu kayit iki yerde
birden yasar: diskte bir dizin + `.git/worktrees/<ad>` kaydi. Uretici sureç normal
biterse kendi `finally`si ikisini de kaldirir; **SIGKILL/timeout/erken cikis** ile
olurse **IKISI DE KALIR** ve hicbir kol gormez:

  * `git worktree prune` bu arizada NO-OP'tur — dizin diskte DURDUGU icin kayit
    "prunable" degildir. Yani ureticinin elindeki tek temizlik kolu, tam da kapatmasi
    gereken vakada calismaz.
  * `pruvo-kapi-test-*` dizini ureticinin kendi `MUTASYON_KOK`unun KARDESIDIR, altinda
    degil → `shutil.rmtree(MUTASYON_KOK)` menzilinde DEGIL.
  * Repo disi oldugu icin `.gitignore`, `urunler-guard`, `kisisel-veri-test.py` gibi
    nobetcilerin HICBIRI orayi gormez → [[diskte-iz-birakma-yasagi]].

🔴 SAHTE KIRMIZI TEHLIKESI — bu modulun VAR OLMA SEBEBININ YARISI.
"gecici koklu worktree sayisi != 0 ise KIRMIZI" seklinde NAIF bir kol YAZILAMAZ: bu
fiksturler SANIYELIK yasar ve ayni anda baska bir evde/cipte KOSAN bir batarya her an
bir tane dogurup oldururken olcum yapilabilir. Tam bu vaka 19 Agu 2026'da
`worktree-tavan-nobeti.py`de yasandi (`TAVAN ASILDI ROL=MIMAR SAYI=3` SAHTE cikti) ve
28 Agu'da bu cip tarafindan TEKRAR olculdu: 15:24'te `pruvo-kapi-test-ub7g6gr6`,
15:25'te `pruvo-kapi-test-pp1d1xdk` — ad her olcumde degisiyordu, cunku komsu ev
`frosty-meitner-deb9f0` o an `mimar-kapi-mutasyon-test.py` kosuyordu.
**Sahte kirmizi, gercek kirmiziyi gorunmez yapar.**

COZUM — SAHIPLIK DAMGASI: gecici taban dizinin ADINA ureten surecin PID'i yazilir
(`pruvo-kapi-test-p<PID>-xxxxxxxx`). Siniflama o PID'den TURETILIR:

  CANLI       sahip PID hala yasiyor  -> fikstur KOSUYOR, DOKUNULMAZ, yesil
  SIZINTI     sahip PID olmus         -> terk edilmis, KIRMIZI + `--temizle` ile kaldirilir
  OLCULEMEDI  damga YOK (eski surum / yabanci uretici) -> KIRMIZI-DEGIL-YESIL-DE-DEGIL;
              **ASLA SILINMEZ** ([[olculemedi-bypass-degil-menzil-daraltmasi]])

🔴 SUPHE YONU TEK TARAFLIDIR. Yanlis `CANLI` (sizinti canli sanilir) bedeli: bir tur
gecikme — PID geri donusumu nadirdir, sonraki kosum toplar. Yanlis `SIZINTI` (canli
fikstur sizinti sanilir) bedeli: **KOSAN bir komsunun fiksturunu silmek**, yani onun
bataryasini ortasindan kesmek. Bu yuzden `os.kill(pid, 0)` PermissionError verirse de
(baska kullanicinin sureci) CANLI sayilir ve komut satiri/ps ile IKINCI bir dogrulama
YAPILMAZ: ps'in yanilmasi silme yonune akardi. Yalniz KESIN olu PID sizintidir.

Damgasiz eski isimlerin damgayla KARISMASI mumkun degildir: `tempfile.mkdtemp` sonekinde
tire YOKTUR (alfabe `[a-z0-9_]`), dolayisiyla `-p<rakamlar>-` dizisi yalniz bu modulun
yazdigi onekte olusabilir.

Kullanim (uretici tarafi):
    import gecici_worktree
    temel = gecici_worktree.damgali_mkdtemp("pruvo-kapi-test-")   # atexit+sinyal bagli
    gecici_worktree.kaydet(REPO, yol, "--no-checkout", "--detach")
    ...
    gecici_worktree.kaldir(REPO, yol)          # hata metni ya da None

Kullanim (olcum tarafi): tools/gecici-worktree-nobeti.py
"""
import atexit
import os
import re
import shutil
import signal
import subprocess
import tempfile

# Siniflar — JETONLAR BIRBIRININ ALT DIZESI OLAMAZ (rapor filtreleri ayirt edebilsin).
CANLI = "CANLI"
SIZINTI = "SIZINTI"
OLCULEMEDI = "OLCULEMEDI"

# Sahiplik damgasi. `\Z` sart: sonekin TAMAMI damgadan SONRA gelmeli, yani damga dizin
# adinin ORTASINDA aranmaz — `pruvo-p1-ab/pruvo-kapi-test-xy` gibi bir yolda YANLIS
# segmente atif yapmasin diye siniflama segment segment yapilir (bkz. sahip_pid).
PID_DESENI = re.compile(r"-p(\d+)-[A-Za-z0-9_]+\Z")

_IZLENEN_WORKTREELER = []   # [(repo, yol)]
_IZLENEN_DIZINLER = []      # [yol]
_TEMIZLIK_BAGLI = False


# --------------------------------------------------------------------------
# GECICI KOKLER — TEK KAYNAK (tools/worktree-tavan-nobeti.py buradan ithal eder)
# --------------------------------------------------------------------------
def gecici_kokler():
    """Sabit yol listesi YAZILMAZ, TURETILIR.

    Kaynaklar: (a) bu surecin gercek gecici dizini `tempfile.gettempdir()` (macOS'ta
    TMPDIR=/var/folders/..., Linux CI'da /tmp), (b) platformun kanonik gecici koku
    `/tmp`, (c) macOS TMPDIR tabani `/var/folders` — baska bir kapinin fiksturu BIZIM
    TMPDIR'imizin altinda olmayabilir (farkli oturum/kullanici) ama yine de platformun
    gecici agacindadir. Hepsi `realpath`lenir: macOS'ta /var -> /private/var symlink'i
    yuzunden ham karsilastirma esleseni SESSIZCE kaciriyordu."""
    kokler = []
    for aday in (tempfile.gettempdir(), "/tmp", "/var/folders", "/private/var/folders"):
        try:
            gercek = os.path.realpath(aday)
        except OSError:
            continue
        if gercek and gercek != os.sep and gercek not in kokler:
            kokler.append(gercek)
    return kokler


def gecici_altinda_mi(yol):
    gercek = os.path.realpath(yol)
    return any(gercek.startswith(kok + os.sep) for kok in gecici_kokler())


# --------------------------------------------------------------------------
# SAHIPLIK DAMGASI
# --------------------------------------------------------------------------
def damgali_onek(onek):
    """`pruvo-kapi-test-` -> `pruvo-kapi-test-p<PID>-`."""
    return "%sp%d-" % (onek, os.getpid())


def sahip_pid(yol):
    """Yolun HERHANGI bir segmentindeki sahiplik damgasindan PID; yoksa None.

    Segment segment bakilir cunku kayit iki bicimde olabilir:
      <tmp>/pruvo-kapi-test-p123-abcd1234/kayitli-wt   (damga UST dizinde)
      <tmp>/pruvo-k80-p123-abcd1234                    (damga worktree dizininde)
    Ilk eslesen segment sahiptir."""
    try:
        gercek = os.path.realpath(yol)
    except OSError:
        gercek = yol
    for parca in gercek.split(os.sep):
        m = PID_DESENI.search(parca)
        if m:
            return int(m.group(1))
    return None


def pid_canli_mi(pid):
    """🔴 SUPHE = CANLI. Yalniz KESIN olu (ProcessLookupError) False doner."""
    if pid is None or pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True          # baska kullanicinin sureci — YASIYOR
    except OSError:
        return True          # olculemedi -> silme yonune AKMAZ
    return True


def sinifla(yol):
    """(sinif, pid) — pid None ise damga yoktu."""
    pid = sahip_pid(yol)
    if pid is None:
        return OLCULEMEDI, None
    return (CANLI if pid_canli_mi(pid) else SIZINTI), pid


# --------------------------------------------------------------------------
# URETICI TARAFI — "URETEN TEMIZLER", ERKEN CIKISTA DA
# --------------------------------------------------------------------------
def damgali_mkdtemp(onek):
    """PID damgali gecici taban acar ve temizligini BAGLAR."""
    yol = os.path.realpath(tempfile.mkdtemp(prefix=damgali_onek(onek)))
    _IZLENEN_DIZINLER.append(yol)
    temizligi_bagla()
    return yol


def kaydet(repo, yol, *bayraklar, commitish=None, zaman_asimi=None):
    """`git -C <repo> worktree add <bayraklar> <yol> [<commitish>]` — IZLEMEYE alir.

    🔴 SIRA SOZLESMESI: `git worktree add` yolu bayraklardan SONRA, commit-ish'i ise
    YOLDAN SONRA bekler. Bayraklarla commit-ish tek bir *argv'de toplanirsa git
    commit-ish'i YOL sanar ve gercek yolu commit-ish'e cevirir (olculdu: prob
    `worktree add --detach HEAD <yol>` uretip sessizce dustu). Bu yuzden commit-ish
    AYRI bir anahtar kelime argumanidir.

    Doner: subprocess sonucu (returncode/stderr cagirana ait)."""
    komut = ["git", "-C", repo, "worktree", "add"] + list(bayraklar) + [yol]
    if commitish:
        komut.append(commitish)
    sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=zaman_asimi)
    if sonuc.returncode == 0:
        _IZLENEN_WORKTREELER.append((repo, os.path.normpath(yol)))
        temizligi_bagla()
    return sonuc


def kaldir(repo, yol, zaman_asimi=None):
    """Kaydi + dizini kaldirir. Doner: hata metni listesi ya da None.

    Donus kodu DENETLENIR: kaldirilamayan gecici worktree hem diskte hem
    `.git/worktrees` kaydinda kalir — yani batarya kendi kurdugu MUAF BOLGEYI
    sizdirir ve sonraki kosumlar bu kayittan etkilenir (hermetiklik kaybi)."""
    if not yol:
        return None
    normal = os.path.normpath(yol)
    sonuc = subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", normal],
                           capture_output=True, text=True, timeout=zaman_asimi)
    _izlemeden_dus(repo, normal)
    if sonuc.returncode != 0:
        return (sonuc.stderr or "?").strip().splitlines()[-1:] or ["?"]
    if os.path.exists(normal):
        return ["dizin hala diskte: " + normal]
    return None


def _izlemeden_dus(repo, yol):
    kalan = [(r, y) for (r, y) in _IZLENEN_WORKTREELER
             if not (r == repo and y == os.path.normpath(yol))]
    del _IZLENEN_WORKTREELER[:]
    _IZLENEN_WORKTREELER.extend(kalan)


def hepsini_temizle():
    """Idempotent: izlenen worktree kayitlarini ve gecici dizinleri kaldirir.
    atexit ve sinyal kollarindan cagirilir; hata BASTIRILIR (temizlik kendisi
    yeni bir arizanin sebebi olmamali)."""
    while _IZLENEN_WORKTREELER:
        repo, yol = _IZLENEN_WORKTREELER.pop()
        try:
            subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", yol],
                           capture_output=True, text=True)
        except Exception:
            pass
    while _IZLENEN_DIZINLER:
        try:
            shutil.rmtree(_IZLENEN_DIZINLER.pop(), ignore_errors=True)
        except Exception:
            pass


def _sinyal_kolu(imza, _cerceve):
    hepsini_temizle()
    # Varsayilan davranisi GERI YUKLE ve sinyali KENDIMIZE tekrar gonder: cikis
    # kodu/olum sebebi ORIJINAL kalsin (yutulmus SIGTERM, ust surece "duzgun bitti"
    # gibi gorunurdu).
    try:
        signal.signal(imza, signal.SIG_DFL)
        os.kill(os.getpid(), imza)
    except Exception:
        os._exit(128 + imza)


def temizligi_bagla():
    """atexit + SIGTERM/SIGINT/SIGHUP. Idempotent.

    `finally` TEK BASINA YETMEZ: uretici bir alt sureç olarak kosuyorsa ust sureç onu
    timeout/iptal ile SIGTERM'ler ve `finally` HIC KOSMAZ. SIGKILL yine kapsam disidir
    — o yuzden olcum kolu (tools/gecici-worktree-nobeti.py) AYRI bir savunma hattidir,
    bu kolun yedegi degil."""
    global _TEMIZLIK_BAGLI
    if _TEMIZLIK_BAGLI:
        return
    _TEMIZLIK_BAGLI = True
    atexit.register(hepsini_temizle)
    for ad in ("SIGTERM", "SIGINT", "SIGHUP"):
        imza = getattr(signal, ad, None)
        if imza is None:
            continue
        try:
            if signal.getsignal(imza) in (signal.SIG_DFL, signal.default_int_handler):
                signal.signal(imza, _sinyal_kolu)
        except (ValueError, OSError):
            pass          # ana thread degiliz / platform desteklemiyor


# --------------------------------------------------------------------------
# OLCUM TARAFI
# --------------------------------------------------------------------------
def kayitli_agaclar(repo):
    """`git worktree list --porcelain` -> [{'yol':..., 'detached':bool}]"""
    sonuc = subprocess.run(["git", "-C", repo, "worktree", "list", "--porcelain"],
                           capture_output=True, text=True)
    if sonuc.returncode != 0:
        raise RuntimeError("git worktree list basarisiz: " +
                           (sonuc.stderr or "").strip()[:200])
    agaclar = []
    simdiki = None
    for satir in (sonuc.stdout or "").splitlines():
        if satir.startswith("worktree "):
            simdiki = {"yol": satir[len("worktree "):].strip(), "detached": False}
            agaclar.append(simdiki)
        elif satir.strip() == "detached" and simdiki is not None:
            simdiki["detached"] = True
    return agaclar


def gecici_kayitlar(repo):
    """Gercek repoya kayitli, GECICI kok altindaki agaclar: [(yol, sinif, pid)].

    🔴 ANA AGAC HARIC TUTULUR (porcelain ciktisinin ILK girisi daima anadir): ana
    checkout'un KENDISI gecici bir kokte durabilir (sentetik fikstur depolari tam da
    boyledir) ve o bir fikstur DEGILDIR — sayilsaydi her sentetik depo kendi
    olcumunde bir `OLCULEMEDI` uretir, gercek bulguyu golgelerdi."""
    bulgular = []
    for sira, entry in enumerate(kayitli_agaclar(repo)):
        if sira == 0:
            continue
        if not gecici_altinda_mi(entry["yol"]):
            continue
        sinif, pid = sinifla(entry["yol"])
        bulgular.append((entry["yol"], sinif, pid))
    return bulgular


def sizintilari_temizle(repo):
    """YALNIZ sahibi OLU olan kayitlari kaldirir. Doner: (kaldirilan, kalan_hata).

    🔴 CANLI ve OLCULEMEDI'ye ASLA DOKUNULMAZ — biri komsunun kosan bataryasi, digeri
    hakkinda hukum veremedigimiz yabanci/eski bir fikstur."""
    kaldirilan = []
    hatalar = []
    for yol, sinif, _pid in gecici_kayitlar(repo):
        if sinif != SIZINTI:
            continue
        hata = kaldir(repo, yol)
        if hata:
            hatalar.append((yol, hata))
        else:
            kaldirilan.append(yol)
    # Dizini gitmis ama kaydi duran girisler icin (SIZINTI'nin diger yarisi).
    subprocess.run(["git", "-C", repo, "worktree", "prune"],
                   capture_output=True, text=True)
    return kaldirilan, hatalar
