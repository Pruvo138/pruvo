#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/git_ortami.py — GIT BAGLAM SCRUB'ININ TEK TANIMI (kutuphane modulu).

NE ISE YARAR: bu depodaki kapilar depo kokunu `git -C <yol> rev-parse --show-toplevel`
ile TURETIR. Cagiran surecten MIRAS ALINAN git baglam degiskenleri (bir git kancasi
bunlari IHRAC EDER) bu ACIK `-C` hedefini SESSIZCE ezer. Bu modul, git cagrilarinin
kosacagi TEMIZ ortami ve o ortamla kok turetimini TEK YERDE tanimlar.

OLCULEN KUSUR (6 Agu 2026, yeniden uretildi — tools/diriltme-kapisi.py):
  * linked worktree kancasinda GIT_DIR MUTLAK olarak miras alinir (ana checkout
    kancasinda hic set EDILMEZ);
  * GIT_DIR mutlak + GIT_WORK_TREE bos oldugunda git depo KESFINI ATLAR ve CARI DIZINI
    calisma agacinin tepesi kabul eder;
  * boylece `git -C <depo>/tools rev-parse --show-toplevel` -> `<depo>/tools` doner
    (YANLIS), cunku `-C` once o ALT DIZINE gecer.
Sonuc: kapi worktree'de ya yanlis agaci olcer ya da OLCULEMEDI verip commit'i bloklar
(ve isciyi kapinin kendisini atlatmaya iter).

NEDEN TEK KAYNAK ([[ikiz-tanim-sessiz-ayrisma]]): ayni listenin ikinci bir kopyasi
zamanla sessizce ayrisir ve ayrisma DAIMA gevsek yonde olur (bir ad eksik kalir, o ad
uzerinden miras alinan baglam geri sizar). Bu yuzden:
  * `GIT_BAGLAM_DEGISKENLERI` bu depoda YALNIZ BURADA tanimlanir (nobeti asagida:
    `--kendini-test` izlenen .py dosyalarini tarar, ikinci tanim gorurse KIRMIZI);
  * `tools/ic-rapor-adi-kapisi.py`, `tools/spec-ifsa-kapisi.py` ve
    `tools/diriltme-kapisi.py` UCU DE bu modulden turer;
  * TUKETICIDE `try/except ImportError -> yerel tanim` YAZILMAZ: o dusus yolu ikizin
    ta kendisidir ve gevsek yonde ayrisir. Modul yoksa cagri COKSUN (gurultulu).

Kullanim (kutuphane):
    from git_ortami import git_kok, git_ortami
    kok = git_kok(dizin, git_ortami())      # "" = git agaci degil (fail-closed sozlesme)

Kullanim (nobet):
    python3 tools/git_ortami.py --kendini-test    # scrub davranisi + TEK KAYNAK nobeti

Cikis kodu (--kendini-test): 0 = tum iddialar gecti, 1 = en az biri dustu.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # tuketiciler SALT-OKUNUR tarar: hedef repoya __pycache__ yazma.

MODUL_ADI = "git_ortami.py"

# Miras alinan git baglami: bu 11 ad git'in depo KESFINI degistirir ya da ACIK `-C`
# hedefini ezer. Liste DAR degil GENIS tutulur — eksik kalan her ad bir sizinti yoludur.
GIT_BAGLAM_DEGISKENLERI = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_PREFIX", "GIT_NAMESPACE", "GIT_INDEX_VERSION",
)


def git_ortami():
    """Miras alinan git baglami SILINMIS `os.environ` kopyasi (PATH vb. KORUNUR)."""
    ort = os.environ.copy()
    for ad in GIT_BAGLAM_DEGISKENLERI:
        ort.pop(ad, None)
    return ort


def git_kok(dizin, ortam=None):
    """<dizin>'in AIT OLDUGU git agacinin kokunu doner; "" = git agaci DEGIL.

    `-C dizin` ZORUNLUDUR (argumansiz cagri CWD'ye bakar) ve cagri VARSAYILAN OLARAK
    temizlenmis ortamda kosar: kok ORTAMDAN degil, `-C <yol>` KESFINDEN turer.
    <ortam> yalniz cagri yerinin bu secimi ACIKCA tasimasi icin disaridan verilebilir
    (mutasyon capasi cagri yerinde dursun diye); None = git_ortami().

    Fail-closed sozlesme: hata durumunda "" doner — hukum veren taraf bunu OLCULEMEDI
    sayar, sessiz bir yesile CEVIRMEZ.
    """
    p = subprocess.run(["git", "-C", dizin, "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, errors="replace",
                       env=git_ortami() if ortam is None else ortam)
    return p.stdout.strip() if p.returncode == 0 else ""


def _kos(depo, *args):
    return subprocess.run(["git", "-C", depo, *args], capture_output=True, text=True,
                          errors="replace", env=git_ortami())


# ===========================================================================
# DAVRANISSAL SONDA — kapilarin KENDI kabul testleri icin ORTAK surucu.
# Anlati kanit degildir: sentetik depo + GERCEK `git worktree add` + GERCEK `git commit`
# ile tetiklenen GERCEK bir pre-commit kancasi kurulur; kapinin BASTIGI KOK olculur.
# Ortam ELLE set edilip kanca TAKLIT EDILMEZ — kanca baglamini git'in kendisi uretir.
# ===========================================================================
_KOK_DESENI = re.compile(r"olculen agac = (.+?)(?:\s+\(|\s*$)", re.M)
_KANCA_GOVDESI = """#!/bin/sh
# Sentetik pre-commit: kapiyi kanca baglamindan kosar, ciktisini kaydeder ve
# commit'i BLOKLAMAZ (olculen sey kapinin HUKMU degil, BASTIGI KOK).
"%(python)s" "./tools/%(kapi)s" > "%(kayit)s" 2>&1
printf 'SONDA_RC=%%s\\n' "$?" >> "%(kayit)s"
exit 0
"""


def _basilan_kok(cikti):
    m = _KOK_DESENI.search(cikti or "")
    return m.group(1).strip() if m else None


def worktree_kanca_kok_olcumu(kapi_kaynagi, hedef_ad):
    """Kapi kopyasini IKI baglamda kosturur ve BASTIGI KOKU olcer.

    <kapi_kaynagi> : kosturulacak kapi dosyasinin yolu (mutasyonlu KOPYA olabilir).
    <hedef_ad>     : sentetik depoda `tools/` altina konacak AD (kapinin kendi
                     dosyasini tarama disi birakan istisnasi bu ada bagli olabilir).

    Dondurur: {"wt": <worktree koku>, "kancasiz": (rc, kok, esit_mi),
               "kanca": (rc, kok, esit_mi), "kanca_kosti": bool, "kanca_cikti": str}
    """
    with tempfile.TemporaryDirectory(prefix="pruvo-kok-sondasi-") as kd:
        ana = os.path.join(kd, "ana")
        os.makedirs(os.path.join(ana, "tools"))
        _kos(ana, "init", "-q", "-b", "main")
        _kos(ana, "config", "user.email", "t@t.local")
        _kos(ana, "config", "user.name", "t")
        shutil.copyfile(kapi_kaynagi, os.path.join(ana, "tools", hedef_ad))
        shutil.copyfile(os.path.abspath(__file__), os.path.join(ana, "tools", MODUL_ADI))
        with open(os.path.join(ana, "veri.txt"), "w", encoding="utf-8") as f:
            f.write("sentetik icerik\n")
        _kos(ana, "add", "-A")
        _kos(ana, "commit", "-q", "-m", "ilk")

        wt = os.path.join(kd, "wt")
        _kos(ana, "worktree", "add", "-q", "-b", "sonda-dali", wt)
        gercek_wt = os.path.realpath(wt)
        kapi_wt = os.path.join(wt, "tools", hedef_ad)

        # (a) KANCASIZ: dogrudan calistirma, cwd = worktree koku.
        pa = subprocess.run([sys.executable, kapi_wt], cwd=wt, capture_output=True,
                            text=True, errors="replace", env=git_ortami())
        kok_a = _basilan_kok(pa.stdout + pa.stderr)

        # (b) KANCA ICI: GERCEK commit -> GERCEK pre-commit. Linked worktree kancalari
        #     ORTAK dizinden (`<ana>/.git/hooks`) okunur.
        kayit = os.path.join(kd, "kanca-cikti.txt")
        kanca = os.path.join(ana, ".git", "hooks", "pre-commit")
        os.makedirs(os.path.dirname(kanca), exist_ok=True)
        with open(kanca, "w", encoding="utf-8") as f:
            f.write(_KANCA_GOVDESI % {"python": sys.executable, "kapi": hedef_ad,
                                      "kayit": kayit})
        os.chmod(kanca, 0o755)
        with open(os.path.join(wt, "veri.txt"), "a", encoding="utf-8") as f:
            f.write("worktree'de degisiklik\n")
        _kos(wt, "add", "-A")
        subprocess.run(["git", "-C", wt, "-c", "user.email=t@t.local", "-c",
                        "user.name=t", "commit", "-q", "-m", "kanca sondasi"],
                       capture_output=True, text=True, errors="replace",
                       env=git_ortami())
        kanca_cikti = ""
        if os.path.exists(kayit):
            with open(kayit, "r", encoding="utf-8", errors="replace") as f:
                kanca_cikti = f.read()
        m = re.search(r"SONDA_RC=(\d+)", kanca_cikti)
        kanca_rc = int(m.group(1)) if m else None
        kok_b = _basilan_kok(kanca_cikti)

        def esit(k):
            return k is not None and os.path.realpath(k) == gercek_wt

        return {
            "wt": gercek_wt,
            "kancasiz": (pa.returncode, kok_a, esit(kok_a)),
            "kanca": (kanca_rc, kok_b, esit(kok_b)),
            "kanca_kosti": bool(kanca_cikti),
            "kanca_cikti": kanca_cikti,
        }


# ===========================================================================
# NOBET — scrub DAVRANISI + TEK KAYNAK (drift) iddiasi.
# ===========================================================================
_TANIM_DESENI = re.compile(r"^\s*" + "GIT_BAGLAM" + r"_DEGISKENLERI\s*=\s*\(", re.M)


def ikinci_tanimlar():
    """Izlenen .py dosyalarinda `GIT_BAGLAM_DEGISKENLERI` TANIMI arar (bu modul HARIC).

    Dondurur: (yollar, hata). hata != None -> OLCULEMEDI (fail-closed: tarama
    yapilamadiysa 'ikinci tanim yok' HUKMU VERILMEZ)."""
    betik_dizini = os.path.dirname(os.path.abspath(__file__))
    kok = git_kok(betik_dizini, git_ortami())
    if not kok:
        return None, "betigin agaci bir git deposu DEGIL: %s" % betik_dizini
    r = _kos(kok, "ls-files", "-z")
    if r.returncode != 0:
        return None, "git ls-files basarisiz: %s" % r.stderr.strip()[:200]
    kendi = os.path.relpath(os.path.abspath(__file__), kok)
    bulunan = []
    for yol in [y for y in r.stdout.split("\0") if y]:
        if not yol.endswith(".py") or yol == kendi:
            continue
        try:
            with open(os.path.join(kok, yol), "r", encoding="utf-8") as f:
                icerik = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        if _TANIM_DESENI.search(icerik):
            bulunan.append(yol)
    return sorted(bulunan), None


def _kendini_test():
    sonuclar = []

    # IDDIA-ORTAM (DAVRANIS): dusman bir GIT_DIR mirasi ALTINDA bile kok, `-C` ile
    # verilen ALT DIZININ agacinin TEPESIDIR — o alt dizin DEGIL.
    with tempfile.TemporaryDirectory(prefix="pruvo-git-ortami-") as d:
        depo = os.path.join(d, "depo")
        alt = os.path.join(depo, "tools")
        os.makedirs(alt)
        _kos(depo, "init", "-q", "-b", "main")
        eski = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = os.path.join(depo, ".git")   # kancanin ihrac ettigi sekil
        try:
            temiz = git_kok(alt, git_ortami())
            kirli = git_kok(alt, os.environ.copy())
        finally:
            if eski is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = eski
        iddia_ortam = (os.path.realpath(temiz or "") == os.path.realpath(depo))
        sonuclar.append(("IDDIA-ORTAM scrub-kok-dogru", iddia_ortam,
                         "miras alinan GIT_DIR altinda kok=%r beklenen=%r" % (temiz, depo)))
        # KONTROL: scrub'siz cagri AYNI girdide FARKLI (yanlis) cevap verir — iddia
        # gercekten scrub'i olcuyor, her ortamda kendiliginden yesil degil.
        sonuclar.append(("KONTROL-SCRUBSUZ ayirt-edici",
                         os.path.realpath(kirli or "") != os.path.realpath(depo),
                         "scrub'siz cagri kok=%r (alt dizini agac tepesi sanmali)" % (kirli,)))

    # IDDIA-TEK-KAYNAK (drift): listenin IKINCI bir tanimi VARSA KIRMIZI.
    ikinci, hata = ikinci_tanimlar()
    sonuclar.append(("IDDIA-TEK-KAYNAK ikinci-tanim-yok", hata is None and ikinci == [],
                     "ikinci tanim tasiyan izlenen .py: %r (hata=%r)" % (ikinci, hata)))

    # KONTROL: liste TAM — ad sayisi ve icerik beyanla ayni (kirpilma nobeti).
    sonuclar.append(("KONTROL-LISTE 11-ad", len(GIT_BAGLAM_DEGISKENLERI) == 11
                     and "GIT_DIR" in GIT_BAGLAM_DEGISKENLERI
                     and "GIT_WORK_TREE" in GIT_BAGLAM_DEGISKENLERI,
                     "ad sayisi=%d" % len(GIT_BAGLAM_DEGISKENLERI)))

    basarisiz = [s for s in sonuclar if not s[1]]
    for etiket, gecti, detay in sonuclar:
        print("  [%s] %s — %s" % ("PASS" if gecti else "FAIL", etiket, detay))
    print("  TOPLAM: %d/%d gecti" % (len(sonuclar) - len(basarisiz), len(sonuclar)))
    return 0 if not basarisiz else 1


def main():
    ap = __import__("argparse").ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true", dest="kendini",
                    help="scrub davranisi + TEK KAYNAK (drift) nobeti")
    args = ap.parse_args()
    if args.kendini:
        return _kendini_test()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
