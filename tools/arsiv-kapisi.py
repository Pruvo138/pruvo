#!/usr/bin/env python3
"""ARSIV KAPISI — bir cipi ARSIVLEMEDEN ONCE kosulur; arsiv VERI KAYBI yapabilir.

NEDEN VAR (olculmus vaka, 3 Eyl 2026): `archive_session` oturumun surecini durdurur
VE VARSAYILAN OLARAK WORKTREE'SINI SILER. Worktree'de commit'lenmemis is varsa ya da
dalin icerigi main'e girmemisse, arsivleme o isi SESSIZCE yok eder. Ayni gun kutuda
`BASLIYORUM` yazip kapanis yazmamis 13 blok olculdu (BaBa sabah 19/23 olcmustu) —
yani "cip kapanis yazar" varsayimi UCUNCU KEZ tutmadi; tekil uyari degil KAPI gerekir.

NE OLCER (dort kol, her biri UC HALLI — TEMIZ / KIRMIZI / OLCULEMEDI):
  K1 AGAC_KIRLI      worktree'de commit'lenmemis degisiklik var mi (porcelain)
  K2 ICERIK_DISARIDA dalin ucu main'in ATASI mi (`merge-base --is-ancestor`)
  K3 ITILMEMIS       dalin ucu herhangi bir `origin/*` ref'inde var mi
  K4 KAPANIS_YOK     ortak kutuda cipin ESLESEN sayili kapanisi var mi

🔴 K4'un hukmu BURADA TANIMLANMAZ — `tools/kutu-arsivle.py::kapanan_cipler`
IMPORT EDILIR. Bu depoda "ikinci envanter" olculmus bir bayatlama sinifidir
([[tuketici-yazilirken-tum-okuyucular-sayilir]]): esleme kurali iki yerde yasarsa
biri sessizce ayrisir ve kapi yanlis alani dogrular.
🔴 KARDES EVLER: kutu ORTAKtir ama `kutu-arsivle.py` yalniz pruvo'da yasar. Kaynak
once `--repo`da, YOKSA kanonik pruvo'da aranir; ilk canli kosumda bu dusme YOKTU ve
hasat'taki bes cipin hepsinde K4 `OLCULEMEDI` dondu (4 Eyl, Okan ekraninda gorulda).

HUKUM (fail-closed, UC KOVA — ucuncu kova yesile KATLANMAZ):
  herhangi bir kol KIRMIZI      -> HUKUM=ARSIVLENEMEZ   rc=1
  kirmizi yok, olculemeyen var  -> HUKUM=OLCULEMEDI     rc=2
  hepsi TEMIZ / KAPSAM_DISI     -> HUKUM=ARSIVLENEBILIR rc=0

KAPSAM_DISI ≠ TEMIZ: dalin cikarilmis agaci yoksa K1'in silecegi bir sey de yoktur;
bu hal AYRI basilir ve gerekcesi yazilir, sessizce yesile sayilmaz.

KULLANIM:
  python3 tools/arsiv-kapisi.py <worktree-yolu | dal-adi> [--cip AD] [--repo YOL] [--kutu YOL]
  python3 tools/arsiv-kapisi.py --kendini-test     # davranissal kabul bataryasi
  python3 tools/arsiv-kapisi.py --mutasyon         # her mutant HEDEF KOLU adiyla oldurur
"""

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

VARSAYILAN_REPO = "/Users/okan/dev/pruvo"
VARSAYILAN_KUTU = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md")

RC_ARSIVLENEBILIR = 0
RC_ARSIVLENEMEZ = 1
RC_OLCULEMEDI = 2

# Kol hal jetonlari — BIRI DIGERININ ALT DIZGESI DEGIL (grep ile ayrik olculebilir).
HAL_TEMIZ = "TEMIZ"
HAL_KIRMIZI = "KIRMIZI"
HAL_OLCULEMEDI = "OLCULEMEDI"
HAL_KAPSAM_DISI = "KAPSAM_DISI"

KOL_AGAC = "AGAC_KIRLI"
KOL_ICERIK = "ICERIK_DISARIDA"
KOL_ITILMEMIS = "ITILMEMIS"
KOL_KAPANIS = "KAPANIS_YOK"

HUKUM_YESIL = "ARSIVLENEBILIR"
HUKUM_KIRMIZI = "ARSIVLENEMEZ"
HUKUM_OLCULEMEDI = "OLCULEMEDI"


# --------------------------------------------------------------------------- git

def _git(kok, *args):
    """(rc, stdout, stderr) — hicbir zaman istisna atmaz; cagiran rc'yi YARGILAR."""
    try:
        s = subprocess.run(["git", "-C", kok] + list(args),
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return 127, "", str(e)
    return s.returncode, s.stdout, s.stderr


def repo_mu(kok):
    rc, cikti, _ = _git(kok, "rev-parse", "--show-toplevel")
    return rc == 0 and cikti.strip() != ""


# ------------------------------------------------------------------ kutu kaynagi

def _kutu_kaynak_yolu(repo):
    """(yol|None, nereden) — kapanis hukmunun KANONIK kaynagi.

    🔴 OLCULMUS KUSUR (4 Eyl, ilk canli kosum): kaynak YALNIZ `<repo>/tools/`de
    arananiyordu. Kutu ORTAKtir ama `kutu-arsivle.py` yalniz pruvo'da yasar; kardes
    evlerde (hasat/pazarlama/bot/jenerator) kosuldugunda K4 HER ZAMAN `OLCULEMEDI`
    doner — yani kapanis kolu bu evlerde HIC olculmemis olur. Kapinin menzili cagri
    yeridir: kaynak once cagrilan repoda, YOKSA kanonik pruvo'da aranir."""
    yerel = os.path.join(repo, "tools", "kutu-arsivle.py")
    if os.path.isfile(yerel):
        return yerel, "yerel"
    kanonik = os.path.join(VARSAYILAN_REPO, "tools", "kutu-arsivle.py")
    if os.path.isfile(kanonik):
        return kanonik, "kanonik"
    return None, "yok"


def _kutu_modulu(repo):
    """kutu-arsivle.py'yi MODUL olarak yukle (dosya adinda '-' var, import edilemez).

    Bulunamazsa None doner -> K4 OLCULEMEDI olur, ASLA sessiz yesil."""
    yol, nereden = _kutu_kaynak_yolu(repo)
    if yol is None:
        return None, ("kapanis hukmunun kaynagi HICBIR YERDE yok (ne %s/tools/ ne %s/tools/)"
                      % (repo, VARSAYILAN_REPO))
    try:
        spec = importlib.util.spec_from_file_location("_kutu_arsivle_kaynak", yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:                                   # noqa: BLE001
        return None, "kaynak yuklenemedi: %s: %s" % (type(e).__name__, e)
    for gerekli in ("oku", "blok_baslari", "frontmatter_sonu", "kapanan_cipler"):
        if not hasattr(mod, gerekli):
            return None, "kaynakta `%s` YOK (imza degismis)" % gerekli
    return mod, None


def kapanan_kumesi(repo, kutu_yolu):
    """(kume, hata) — kapanisi kutuda OLAN cip adlari. Hukum kutu-arsivle.py'nindir."""
    mod, hata = _kutu_modulu(repo)
    if mod is None:
        return None, hata
    if not os.path.isfile(kutu_yolu):
        return None, "kutu yok: %s" % kutu_yolu
    try:
        # 🔴 Kaynagin imzalari CIFT DEGER dondurur (metin|None, hata) ve
        # (indeks|None, hata). Ikinci degeri yutmak bozuk/yarim bir kutuyu SAGLAM
        # sanip K4'u yesile yakardi — bu yuzden iki hata kolu da AYRI okunur.
        metin, oku_hata = mod.oku(kutu_yolu)
        if oku_hata or metin is None:
            return None, "kutu okunamadi: %s" % (oku_hata or "metin bos")
        satirlar = metin.splitlines(keepends=True)
        fm, fm_hata = mod.frontmatter_sonu(satirlar)
        if fm_hata or fm is None:
            return None, "kutu frontmatter'i bozuk: %s" % (fm_hata or "?")
        baslar = mod.blok_baslari(satirlar, fm)
        return mod.kapanan_cipler(satirlar, baslar), None
    except Exception as e:                                   # noqa: BLE001
        return None, "kutu okunamadi: %s: %s" % (type(e).__name__, e)


# ------------------------------------------------------------------- cozumleme

def worktree_haritasi(repo):
    """{mutlak_yol: dal_ya_da_None} — `git worktree list --porcelain`den TURETILIR."""
    rc, cikti, _ = _git(repo, "worktree", "list", "--porcelain")
    if rc != 0:
        return None
    harita = {}
    yol = None
    for satir in cikti.splitlines():
        if satir.startswith("worktree "):
            yol = os.path.realpath(satir[len("worktree "):].strip())
            harita[yol] = None
        elif satir.startswith("branch ") and yol:
            harita[yol] = satir[len("branch "):].strip().replace("refs/heads/", "")
    return harita


def hedefi_coz(repo, hedef):
    """(worktree_yolu|None, dal|None, uc_sha|None, hata|None)

    `hedef` bir DIZIN yolu ise worktree kabul edilir; degilse DAL adi denenir."""
    harita = worktree_haritasi(repo)
    if harita is None:
        return None, None, None, "worktree listesi okunamadi (repo degil?)"

    if os.path.isdir(hedef):
        yol = os.path.realpath(hedef)
        if yol not in harita:
            return None, None, None, "dizin bu reponun worktree'si DEGIL: %s" % yol
        dal = harita[yol]
        rc, sha, _ = _git(yol, "rev-parse", "HEAD")
        if rc != 0:
            return yol, dal, None, "HEAD cozulemedi: %s" % yol
        return yol, dal, sha.strip(), None

    dal = hedef
    rc, sha, _ = _git(repo, "rev-parse", "--verify", dal)
    if rc != 0:
        return None, None, None, "ne dizin ne de dal: %s" % hedef
    yol = next((y for y, d in harita.items() if d == dal), None)
    return yol, dal, sha.strip(), None


def cip_adini_cikar(worktree, dal, acik):
    """Kutuda aranacak cip adi. Oncelik: --cip > worktree dizin adi > dal son parcasi."""
    if acik:
        return acik
    if worktree:
        return os.path.basename(worktree.rstrip("/"))
    if dal:
        return dal.split("/")[-1]
    return None


# ------------------------------------------------------------------------ kollar

def kol_agac(worktree):
    if worktree is None:
        return HAL_KAPSAM_DISI, "dalin cikarilmis agaci YOK -> arsivin silecegi agac da yok"
    rc, cikti, hata = _git(worktree, "status", "--porcelain")
    if rc != 0:
        return HAL_OLCULEMEDI, "porcelain okunamadi (rc=%d): %s" % (rc, hata.strip()[:120])
    kirli = [s for s in cikti.splitlines() if s.strip()]
    if kirli:
        return HAL_KIRMIZI, "%d commit'lenmemis degisiklik: %s" % (
            len(kirli), ", ".join(s[3:] for s in kirli[:5]))
    return HAL_TEMIZ, "porcelain temiz"


def kol_icerik(repo, uc, ana="main"):
    if uc is None:
        return HAL_OLCULEMEDI, "dalin ucu cozulemedi"
    rc, _, hata = _git(repo, "rev-parse", "--verify", ana)
    if rc != 0:
        return HAL_OLCULEMEDI, "`%s` cozulemedi: %s" % (ana, hata.strip()[:120])
    rc, _, hata = _git(repo, "merge-base", "--is-ancestor", uc, ana)
    if rc == 0:
        return HAL_TEMIZ, "ucu `%s`in atasi (icerik iceride)" % ana
    if rc == 1:
        return HAL_KIRMIZI, "ucu `%s`in atasi DEGIL — icerik main'e girmemis" % ana
    return HAL_OLCULEMEDI, "is-ancestor beklenmedik rc=%d: %s" % (rc, hata.strip()[:120])


def kol_itilmemis(repo, uc):
    if uc is None:
        return HAL_OLCULEMEDI, "dalin ucu cozulemedi"
    rc, cikti, hata = _git(repo, "branch", "-r", "--contains", uc)
    if rc != 0:
        return HAL_OLCULEMEDI, "uzak ref taramasi rc=%d: %s" % (rc, hata.strip()[:120])
    uzaklar = [s.strip() for s in cikti.splitlines() if s.strip()]
    if uzaklar:
        return HAL_TEMIZ, "ucu %d uzak ref'te: %s" % (len(uzaklar), uzaklar[0])
    return HAL_KIRMIZI, "uc HICBIR `origin/*` ref'inde yok — is yalniz LOKALDE"


def arsiv_yolu(kutu_yolu):
    """Kutunun ARSIV esi — `kutu-arsivle.py`nin adlandirma kurali: <ad>-arsiv.md."""
    kok, uzanti = os.path.splitext(kutu_yolu)
    return kok + "-arsiv" + uzanti


def kol_kapanis(repo, kutu_yolu, cip):
    if cip is None:
        return HAL_OLCULEMEDI, "cip adi cikarilamadi (--cip ver)"
    kume, hata = kapanan_kumesi(repo, kutu_yolu)
    if kume is None:
        return HAL_OLCULEMEDI, hata
    _yol, nereden = _kutu_kaynak_yolu(repo)
    if cip in kume:
        return HAL_TEMIZ, "kutuda eslesen sayili kapanis VAR (hukum kaynagi: %s)" % nereden

    # 🔴 ARSIV DE SAYILIR (olculdu 4 Eyl): kutu tavana degdiginde rotasyon en eski
    # bloklari `<ad>-arsiv.md`ye TASIR — kapanis SILINMEZ, YER DEGISTIRIR. Yalniz
    # canli kutuya bakan bir kol, kapanisini duzgun yazmis bir cipi rotasyondan
    # SONRA "kapanis YOK" diye kirmiziya yakar. Ayni gece kutu UC KEZ dondu; bu
    # yanlis-pozitif nadir degil, KURAL olurdu.
    ars = arsiv_yolu(kutu_yolu)
    if os.path.isfile(ars):
        ars_kume, ars_hata = kapanan_kumesi(repo, ars)
        if ars_kume is None:
            return HAL_OLCULEMEDI, "canli kutuda yok, ARSIV okunamadi: %s" % ars_hata
        if cip in ars_kume:
            return HAL_TEMIZ, ("kapanis ARSIVDE var (rotasyonla tasinmis; hukum kaynagi: %s)"
                               % nereden)
    return HAL_KIRMIZI, ("ne kutuda ne arsivde `%s` icin eslesen sayili kapanis YOK "
                         "(hukum kaynagi: %s)" % (cip, nereden))


# ------------------------------------------------------------------------ hukum

def olc(repo, hedef, cip_acik=None, kutu_yolu=VARSAYILAN_KUTU, ana="main"):
    """(hukum, rc, satirlar) — hicbir sey YAZMAZ, hicbir sey SILMEZ."""
    satirlar = []
    if not repo_mu(repo):
        return HUKUM_OLCULEMEDI, RC_OLCULEMEDI, [
            "KOL=%s HAL=%s  repo degil: %s" % (KOL_AGAC, HAL_OLCULEMEDI, repo)]

    worktree, dal, uc, hata = hedefi_coz(repo, hedef)
    if hata and uc is None:
        return HUKUM_OLCULEMEDI, RC_OLCULEMEDI, ["HEDEF COZULEMEDI: %s" % hata]

    cip = cip_adini_cikar(worktree, dal, cip_acik)
    satirlar.append("HEDEF worktree=%s dal=%s uc=%s cip=%s"
                    % (worktree or "-", dal or "-", (uc or "-")[:12], cip or "-"))

    kollar = [
        (KOL_AGAC, kol_agac(worktree)),
        (KOL_ICERIK, kol_icerik(repo, uc, ana)),
        (KOL_ITILMEMIS, kol_itilmemis(repo, uc)),
        (KOL_KAPANIS, kol_kapanis(repo, kutu_yolu, cip)),
    ]
    for ad, (hal, gerekce) in kollar:
        satirlar.append("KOL=%s HAL=%s  %s" % (ad, hal, gerekce))

    haller = [h for _, (h, _) in kollar]
    if HAL_KIRMIZI in haller:
        return HUKUM_KIRMIZI, RC_ARSIVLENEMEZ, satirlar
    if HAL_OLCULEMEDI in haller:
        return HUKUM_OLCULEMEDI, RC_OLCULEMEDI, satirlar
    return HUKUM_YESIL, RC_ARSIVLENEBILIR, satirlar


# ------------------------------------------------------- kabul bataryasi (fikstur)

def _kur_fikstur(kok, *, kirli=False, mainde=True, itilmis=True, kapanis=True,
                 agac_ac=True, kutu_yok=False, kaynak_kopyala=True,
                 kapanis_arsivde=False):
    """Sentetik git deposu + uzak + worktree + kutu kurar; (repo, worktree, cip) doner.

    🔴 realpath SART: macOS'ta /tmp -> /private/tmp sembolik bagidir ve
    `git worktree list` GERCEK yolu basar; realpath'siz esleme sessizce kacar
    ([[sentetik-git-fiksturinde-realpath-sart]])."""
    kok = os.path.realpath(kok)
    uzak = os.path.join(kok, "uzak.git")
    repo = os.path.join(kok, "repo")
    subprocess.run(["git", "init", "--bare", "-q", uzak], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
    for anahtar, deger in (("user.email", "k@p"), ("user.name", "kapi"),
                           ("commit.gpgsign", "false")):
        subprocess.run(["git", "-C", repo, "config", anahtar, deger], check=True)
    with open(os.path.join(repo, "a.txt"), "w", encoding="utf-8") as f:
        f.write("taban\n")
    subprocess.run(["git", "-C", repo, "add", "a.txt"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "taban"], check=True)
    subprocess.run(["git", "-C", repo, "remote", "add", "origin", uzak], check=True)
    subprocess.run(["git", "-C", repo, "push", "-q", "origin", "main"], check=True)

    cip = "cip-ornek-a1b2c3"
    dal = "claude/" + cip
    subprocess.run(["git", "-C", repo, "branch", dal], check=True)
    worktree = os.path.join(kok, "wt", cip)
    if agac_ac:
        subprocess.run(["git", "-C", repo, "worktree", "add", "-q", worktree, dal],
                       check=True)
        hedef_kok = worktree
    else:
        hedef_kok = None

    if not mainde:
        # dala main'de OLMAYAN bir commit koy
        calisma = worktree or os.path.join(kok, "gecici")
        if worktree is None:
            subprocess.run(["git", "-C", repo, "worktree", "add", "-q", calisma, dal],
                           check=True)
        with open(os.path.join(calisma, "b.txt"), "w", encoding="utf-8") as f:
            f.write("dal isi\n")
        subprocess.run(["git", "-C", calisma, "add", "b.txt"], check=True)
        subprocess.run(["git", "-C", calisma, "commit", "-qm", "dal isi"], check=True)
        if worktree is None:
            subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", calisma],
                           check=True)
    if itilmis:
        subprocess.run(["git", "-C", repo, "push", "-q", "origin", dal], check=True)
    subprocess.run(["git", "-C", repo, "fetch", "-q", "origin"], check=True)

    if kirli and worktree:
        with open(os.path.join(worktree, "a.txt"), "a", encoding="utf-8") as f:
            f.write("kirli\n")

    # kutu: kutu-arsivle.py'nin BEKLEDIGI bicimde
    kutu = os.path.join(kok, "kutu.md")
    govde = []
    govde.append("## 2026-09-04 — 🚧 Ev-Is (çip `%s`) **BAŞLIYORUM: örnek iş.**\n" % cip)
    govde.append("— Ev\n\n---\n\n")
    if kapanis:
        govde.append("## 2026-09-04 — ✅ Ev-Is (çip `%s`) **SAYILI KAPANIŞ: örnek iş bitti, 3 ölçüm.**\n"
                     % cip)
        govde.append("— Ev\n\n---\n\n")
    if not kutu_yok:
        with open(kutu, "w", encoding="utf-8") as f:
            f.write("".join(govde))
    # ROTASYON taklidi: kapanis blogu canli kutudan CIKIP arsive tasinmis olsun.
    if kapanis_arsivde:
        kapanis_blogu = (
            "## 2026-09-04 — ✅ Ev-Is (çip `%s`) **SAYILI KAPANIŞ: örnek iş bitti, 3 ölçüm.**\n"
            "— Ev\n\n---\n\n" % cip)
        with open(kutu, "w", encoding="utf-8") as f:
            f.write("## 2026-09-04 — 🚧 Ev-Is (çip `%s`) **BAŞLIYORUM: örnek iş.**\n"
                    "— Ev\n\n---\n\n" % cip)
        with open(os.path.splitext(kutu)[0] + "-arsiv" + os.path.splitext(kutu)[1],
                  "w", encoding="utf-8") as f:
            f.write(kapanis_blogu)

    # K4'un hukum kaynagi. `kaynak_kopyala=False` KARDES EV halini taklit eder:
    # repoda `tools/kutu-arsivle.py` YOKTUR ve kapi KANONIK pruvo kaynagina DUSMELIDIR.
    if kaynak_kopyala:
        os.makedirs(os.path.join(repo, "tools"), exist_ok=True)
        shutil.copy2(os.path.join(VARSAYILAN_REPO, "tools", "kutu-arsivle.py"),
                     os.path.join(repo, "tools", "kutu-arsivle.py"))
    return repo, (hedef_kok if hedef_kok else dal), kutu, cip


VAKALAR = (
    # (ad, fikstur_kwargs, beklenen_hukum, beklenen_kirmizi_kol, beklenen_olculemedi_kol)
    ("V1 temiz+mainde+itilmis+kapanis", dict(mainde=True), HUKUM_YESIL, None, None),
    ("V2 agac KIRLI", dict(kirli=True), HUKUM_KIRMIZI, KOL_AGAC, None),
    ("V3 icerik main'de DEGIL", dict(mainde=False), HUKUM_KIRMIZI, KOL_ICERIK, None),
    ("V4 ITILMEMIS (uzakta yok)", dict(mainde=False, itilmis=False), HUKUM_KIRMIZI,
     KOL_ITILMEMIS, None),
    ("V5 KAPANIS yok", dict(kapanis=False), HUKUM_KIRMIZI, KOL_KAPANIS, None),
    ("V6 NEGATIF: agac YOK ama dal temiz", dict(agac_ac=False), HUKUM_YESIL, None, None),
    # V7 UCUNCU KOVA: kutu OKUNAMIYOR -> K4 ne yesil ne kirmizi. Bu vaka olmadan
    # `HAL_OLCULEMEDI` kolu hic kosulmuyordu ve onu yesile katlayan mutant (M5)
    # bataryayi YESIL geciyordu ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
    ("V7 UCUNCU KOVA: kutu YOK", dict(kutu_yok=True), HUKUM_OLCULEMEDI, None, KOL_KAPANIS),
    # V9 KARDES EV: repoda `tools/kutu-arsivle.py` YOK (hasat/pazarlama/bot/jenerator
    # boyle). K4 KANONIK pruvo kaynagina dusup OLCMELI — `OLCULEMEDI` DEGIL. Bu vaka
    # olmadan kapi kardes evlerde kapanis kolunu HIC olcmuyordu (canlida gorulda).
    ("V9 KARDES EV: yerel kaynak yok, kanonige dus",
     dict(kapanis=False, kaynak_kopyala=False), HUKUM_KIRMIZI, KOL_KAPANIS, None),
    # V10 ROTASYON: kapanis YAZILMIS ama rotasyon onu arsive tasimis. Kutu her gun
    # birkac kez donuyor; yalniz canli kutuya bakan kol duzgun kapanmis cipi
    # kirmiziya yakardi (d43'te canlida gorulda).
    ("V10 ROTASYON: kapanis ARSIVDE", dict(kapanis_arsivde=True), HUKUM_YESIL, None, None),
)


def _vaka_kos(ad, kwargs):
    kok = os.path.realpath(tempfile.mkdtemp(prefix="arsiv-kapisi-"))
    try:
        repo, hedef, kutu, _cip = _kur_fikstur(kok, **kwargs)
        return olc(repo, hedef, kutu_yolu=kutu)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


DURDUR_JETON = "ARSIVLEME: DURDUR"


def _cikti_sozlesmesi(sessiz=False):
    """(gecti, iddia) — KARAR SATIRI stdout'ta VE en sonda mi?

    🔴 NEDEN AYRI VAKA: yukaridaki batarya `olc()`u DOGRUDAN cagirir, `main()`in
    YAZDIRMA yolunu HIC kosmaz. Karar satiri stderr'e gectiginde hicbir kol kirmizi
    yanmiyordu ama kullanici ciktinin BASINDA bir uyari gorup dogru bir `rc=1`
    hukmunu COKME sandi (olculdu). Sozlesme test edilmeyen yuzeyde yasayamaz.
    """
    kok = os.path.realpath(tempfile.mkdtemp(prefix="arsiv-kapisi-cikti-"))
    gecti = iddia = 0
    try:
        repo, hedef, kutu, _cip = _kur_fikstur(kok, kapanis=False)   # -> ARSIVLENEMEZ
        s = subprocess.run([sys.executable, os.path.realpath(__file__), hedef,
                            "--repo", repo, "--kutu", kutu],
                           capture_output=True, text=True)
        out = s.stdout
        err = s.stderr
        satirlar = [x for x in out.splitlines() if x.strip()]

        kontroller = (
            ("karar satiri STDOUT'ta", DURDUR_JETON in out),
            ("karar satiri stderr'de DEGIL", DURDUR_JETON not in err),
            ("karar satiri EN SON satir", bool(satirlar) and DURDUR_JETON in satirlar[-1]),
            ("HUKUM satiri karardan ONCE", ("HUKUM=" in out) and
             out.index("HUKUM=") < (out.index(DURDUR_JETON) if DURDUR_JETON in out else -1)),
            ("rc korundu", s.returncode == RC_ARSIVLENEMEZ),
        )
        for ad, ok in kontroller:
            iddia += 1
            if ok:
                gecti += 1
            elif not sessiz:
                print("      ! CIKTI SOZLESMESI: %s — TUTMADI" % ad)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return gecti, iddia


def kendini_test(sessiz=False):
    gecti = kirmizi = 0
    iddia = 0
    for ad, kwargs, beklenen, beklenen_kol, beklenen_olc_kol in VAKALAR:
        hukum, rc, satirlar = _vaka_kos(ad, kwargs)
        metin = "\n".join(satirlar)

        iddia += 1
        if hukum == beklenen:
            gecti += 1
            durum = "OK"
        else:
            kirmizi += 1
            durum = "KIRMIZI"
        if not sessiz:
            print("  [%s] %-38s HUKUM=%s rc=%d (beklenen %s)"
                  % (durum, ad, hukum, rc, beklenen))

        # rc ekseni AYRI iddia — hukum dogru ama rc yanlis olabilir
        iddia += 1
        beklenen_rc = {HUKUM_YESIL: RC_ARSIVLENEBILIR,
                       HUKUM_KIRMIZI: RC_ARSIVLENEMEZ,
                       HUKUM_OLCULEMEDI: RC_OLCULEMEDI}[beklenen]
        if rc == beklenen_rc:
            gecti += 1
        else:
            kirmizi += 1
            if not sessiz:
                print("      ! rc=%d beklenen %d" % (rc, beklenen_rc))

        # KIRMIZI kolun ADI da iddiadir: dogru sebeple kirmizi mi?
        if beklenen_kol:
            iddia += 1
            if ("KOL=%s HAL=%s" % (beklenen_kol, HAL_KIRMIZI)) in metin:
                gecti += 1
            else:
                kirmizi += 1
                if not sessiz:
                    print("      ! beklenen kirmizi kol %s bulunamadi" % beklenen_kol)
        else:
            # KIRMIZI beklenmeyen vakada HICBIR kol kirmizi olmamali
            iddia += 1
            if ("HAL=%s" % HAL_KIRMIZI) not in metin:
                gecti += 1
            else:
                kirmizi += 1
                if not sessiz:
                    print("      ! kirmizi beklenmeyen vakada kirmizi kol var")

        # UCUNCU KOVA ekseni: olculemeyen kolun ADI da iddiadir
        if beklenen_olc_kol:
            iddia += 1
            if ("KOL=%s HAL=%s" % (beklenen_olc_kol, HAL_OLCULEMEDI)) in metin:
                gecti += 1
            else:
                kirmizi += 1
                if not sessiz:
                    print("      ! beklenen OLCULEMEDI kol %s bulunamadi" % beklenen_olc_kol)

    # OLCULEMEDI kovasi: var olmayan repo -> ucuncu kova, yesile KATLANMAZ
    iddia += 2
    hukum, rc, _ = olc("/var/empty/yok-boyle-bir-repo", "main")
    if hukum == HUKUM_OLCULEMEDI:
        gecti += 1
    else:
        kirmizi += 1
        if not sessiz:
            print("      ! olculemedi kovasi calismadi: %s" % hukum)
    if rc == RC_OLCULEMEDI:
        gecti += 1
    else:
        kirmizi += 1

    # V8: CIKTI SOZLESMESI — `main()`in yazdirma yolu (yukaridakiler `olc()`u cagirir)
    v8_gecti, v8_iddia = _cikti_sozlesmesi(sessiz)
    iddia += v8_iddia
    gecti += v8_gecti
    kirmizi += (v8_iddia - v8_gecti)
    if not sessiz:
        print("  [%s] V8 CIKTI SOZLESMESI (karar satiri stdout + EN SON)  %d/%d"
              % ("OK" if v8_gecti == v8_iddia else "KIRMIZI", v8_gecti, v8_iddia))

    if not sessiz:
        print("\nVAKA=%d IDDIA=%d GECTI=%d KIRMIZI=%d" % (len(VAKALAR) + 2, iddia, gecti, kirmizi))
        print("KABUL %s" % ("YESIL" if kirmizi == 0 else "KIRMIZI"))
    return kirmizi == 0, iddia, gecti


# ------------------------------------------------------------- mutasyon bataryasi

MUTANTLAR = (
    ("M1 agac-kolu-korlestir", KOL_AGAC,
     '    if kirli:\n        return HAL_KIRMIZI,',
     '    if False:\n        return HAL_KIRMIZI,'),
    ("M2 icerik-kolu-uc-karsilastir", KOL_ICERIK,
     '    if rc == 1:\n        return HAL_KIRMIZI, "ucu `%s`in atasi DEGIL',
     '    if False:\n        return HAL_KIRMIZI, "ucu `%s`in atasi DEGIL'),
    ("M3 itilmemis-kolu-korlestir", KOL_ITILMEMIS,
     '    return HAL_KIRMIZI, "uc HICBIR `origin/*` ref\'inde yok',
     '    return HAL_TEMIZ, "uc HICBIR `origin/*` ref\'inde yok'),
    # 🔴 Capa COK SATIRLI olmali: tek satirlik bir capa BU TABLODA da birebir gecer,
    # dosyada iki kez bulunur ve mutant "CAPA ULASMADI" ile SAYILMAZ olur (olculdu).
    # `\n` tasiyan capa dosyada kacisli durur, calisma zamanindaki dizgeyle eslesmez.
    ("M4 kapanis-kolu-ikinci-envanter", KOL_KAPANIS,
     '    if cip in kume:\n        return HAL_TEMIZ,',
     '    if True:\n        return HAL_TEMIZ,'),
    ("M5 olculemedi-kovasini-yesile-katla", "UCUNCU_KOVA",
     '    if HAL_OLCULEMEDI in haller:\n        return HUKUM_OLCULEMEDI, RC_OLCULEMEDI, satirlar',
     '    if False:\n        return HUKUM_OLCULEMEDI, RC_OLCULEMEDI, satirlar'),
    # Okan'in bildirdigi gercek arizanin mutanti: karar satirini stderr'e geri al.
    # V8 olmasaydi bu degisiklik bataryayi YESIL gecerdi — sozlesme test edilmeyen
    # yuzeyde yasayamaz.
    ("M6 karar-satirini-stderr'e-al", "CIKTI_SOZLESMESI",
     '              "SILER ve o isi kaybeder.")\n',
     '              "SILER ve o isi kaybeder.", file=sys.stderr)\n'),
    # Canlida bulunan kusurun mutanti: kanonik kaynaga dusme kolunu kaldir ->
    # kardes evlerde K4 yine HER ZAMAN OLCULEMEDI olur. V9 bunu oldurur.
    ("M7 kanonik-kaynak-dusmesini-kaldir", KOL_KAPANIS,
     '    kanonik = os.path.join(VARSAYILAN_REPO, "tools", "kutu-arsivle.py")\n'
     '    if os.path.isfile(kanonik):',
     '    kanonik = os.path.join(VARSAYILAN_REPO, "tools", "kutu-arsivle.py")\n'
     '    if False:'),
    # Rotasyon kolunu kaldir -> arsive tasinmis kapanis GORUNMEZ olur. V10 oldurur.
    ("M8 arsiv-kolunu-kaldir", KOL_KAPANIS,
     '    ars = arsiv_yolu(kutu_yolu)\n    if os.path.isfile(ars):',
     '    ars = arsiv_yolu(kutu_yolu)\n    if False:'),
)


def mutasyon():
    """Her mutant HEDEF KOLU adiyla oldurmeli; KONTROL kopya taban ile AYNI olmali.

    🔴 Mutasyon CANLI govdeye DEGIL, KOPYAYA uygulanir — bir kesinti canliya mutant
    birakirdi ([[mutant-canli-govdede-yasamaz]])."""
    kaynak = os.path.realpath(__file__)
    with open(kaynak, encoding="utf-8") as f:
        taban_metin = f.read()

    print("MUTASYON BATARYASI — kopya uzerinde, canli govdeye DOKUNULMAZ")
    kok = os.path.realpath(tempfile.mkdtemp(prefix="arsiv-kapisi-mut-"))
    kirmizi = 0
    try:
        # KONTROL: mutantsiz kopya taban ile AYNI hukmu vermeli
        kontrol = os.path.join(kok, "kontrol.py")
        with open(kontrol, "w", encoding="utf-8") as f:
            f.write(taban_metin)
        rc_k = subprocess.run([sys.executable, kontrol, "--kendini-test"],
                              capture_output=True, text=True).returncode
        print("  [%s] MK kontrol (mutantsiz kopya) rc=%d — beklenen 0"
              % ("OK" if rc_k == 0 else "KIRMIZI", rc_k))
        if rc_k != 0:
            kirmizi += 1

        for ad, hedef_kol, capa, yeni in MUTANTLAR:
            if taban_metin.count(capa) != 1:
                print("  [KIRMIZI] %-34s CAPA ULASMADI (count=%d) -> mutant SAYILMAZ"
                      % (ad, taban_metin.count(capa)))
                kirmizi += 1
                continue
            yol = os.path.join(kok, ad.split()[0] + ".py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(taban_metin.replace(capa, yeni))
            s = subprocess.run([sys.executable, yol, "--kendini-test"],
                               capture_output=True, text=True)
            oldu = s.returncode != 0
            print("  [%s] %-34s hedef kol=%-16s rc=%d %s"
                  % ("OK" if oldu else "KIRMIZI", ad, hedef_kol, s.returncode,
                     "-> KABUL KIRMIZI (mutant oldu)" if oldu
                     else "-> KABUL YESIL KALDI (mutant ULASMADI)"))
            if not oldu:
                kirmizi += 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    print("\nMUTANT=%d KIRMIZI=%d" % (len(MUTANTLAR) + 1, kirmizi))
    print("MUTASYON %s" % ("YESIL" if kirmizi == 0 else "KIRMIZI"))
    return kirmizi == 0


# ---------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Cipi ARSIVLEMEDEN ONCE kosulan kapi.")
    ap.add_argument("hedef", nargs="?", help="worktree yolu ya da dal adi")
    ap.add_argument("--repo", default=VARSAYILAN_REPO)
    ap.add_argument("--kutu", default=VARSAYILAN_KUTU)
    ap.add_argument("--cip", default=None, help="kutuda aranacak cip adi (varsayilan: agac adi)")
    ap.add_argument("--ana", default="main")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--mutasyon", action="store_true")
    a = ap.parse_args(argv)

    if a.kendini_test:
        yesil, _, _ = kendini_test()
        return 0 if yesil else 1
    if a.mutasyon:
        return 0 if mutasyon() else 1
    if not a.hedef:
        ap.error("hedef gerekli (worktree yolu ya da dal adi) — ya da --kendini-test")

    hukum, rc, satirlar = olc(a.repo, a.hedef, a.cip, a.kutu, a.ana)
    for s in satirlar:
        print(s)
    print("HUKUM=%s rc=%d" % (hukum, rc))
    # 🔴 CIKTI SOZLESMESI (Okan, 4 Eyl): karar satiri STDOUT'a ve EN SONA yazilir.
    # Onceki hali stderr'e gidiyordu; iki akim ayri tamponlandigi icin uyari cogu
    # zaman CIKTININ BASINDA gorunuyordu ve dogru bir `rc=1` hukmu COKME gibi
    # okunuyordu (Okan bildirdi, terminalden dogrulandi). Kollarin uzerinde durmayan
    # bir karar satiri, karar satiri degildir.
    if hukum == HUKUM_KIRMIZI:
        print("ARSIVLEME: DURDUR — yukarida KIRMIZI kol(lar) var; arsivleme worktree'yi "
              "SILER ve o isi kaybeder.")
    elif hukum == HUKUM_OLCULEMEDI:
        print("ARSIVLEME: DURDUR — kol(lar) OLCULEMEDI; olculmemis eksen yesil SAYILMAZ "
              "(fail-closed).")
    sys.stdout.flush()
    return rc


if __name__ == "__main__":
    sys.exit(main())
