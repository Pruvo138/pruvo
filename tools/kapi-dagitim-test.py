#!/usr/bin/env python3
"""K335 KABUL — mimar icra kapisi shim'inin GIT duzlemi + kurucu.

Olculen ariza (16 Eyl 2026): `kapi-dagitim-kapisi.py --filo` shim'i yalniz DISKTE olcuyordu.
ArTisT/HocA'da shim `.git/info/exclude`'da (commit yok) -> o evlerde acilan her worktree
shim'siz dogdu, kanca zinciri her Bash cagrisinda dustu; TeKiN/BaBa'da `skip-worktree`
bayragi commit'teki bayat kopyayi sakliyordu. Olcum hepsine GUNCEL diyordu.

Hepsi GECICI fikstur git deposunda kosar; gercek ev kokune (~/dev/...) YAZMAZ, silmez.
Saf Python + git, OFFLINE.

  V1 commit'li shim                     -> GUNCEL
  V2 izlenmeyen shim (exclude)          -> GIT_YOK
  V3 HEAD bayat, disk yeni              -> GIT_BAYAT
  V4 skip-worktree                      -> GIT_GIZLI
  V5 assume-unchanged                   -> GIT_GIZLI
  V6 git deposu olmayan ev              -> OKUNAMADI (yesil DEGIL)
  V7 TATBIKAT: V1 evinde taze worktree  -> shim VAR ve beklenenle birebir
  V8 TATBIKAT: V2 evinde taze worktree  -> shim YOK (V2'nin kirmizisi gercek)
  V9 kurucu KURU                        -> fikstur dosyalari sha once=sonra, rc=0
  V10 kurucu --uygula (exclude+skip)    -> bayrak kalkar, exclude satiri silinir; commit -> GUNCEL
  M1 MUTANT: git_duzlemi devre disi     -> V2/V3/V4 GUNCEL'e doner (kapi olmezse test yakalar)
  K1 KONTROL: disk bayat shim           -> SHIM_BAYAT (git ekseni disk eksenini maskelemez)

rc: 0 = tum iddialar tuttu · 1 = en az bir iddia kirmizi.
"""
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ARAC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ARAC)
import kapi_dagitim as KD  # noqa: E402

GORELI = ".claude/mimar-icra-kapisi.py"
AD = "FIKSTUR"
SONUC = []


def git(kok, *args):
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", kok] + list(args),
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + ": " + r.stderr.decode("utf-8", "replace"))
    return r


def iddia(ad, kosul, ayrinti=""):
    SONUC.append((ad, bool(kosul)))
    print(("GECTI " if kosul else "KIRMIZI ") + ad + ("  " + ayrinti if ayrinti else ""))


def ev_kur(taban, ad, commit=True, icerik=None):
    kok = os.path.join(taban, ad)
    os.makedirs(os.path.join(kok, ".claude"))
    git(kok, "init", "-q", "-b", "main")
    with open(os.path.join(kok, "README"), "w") as f:
        f.write("x\n")
    yol = os.path.join(kok, GORELI)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik if icerik is not None else KD.shim_metni(AD, kok))
    git(kok, "add", "README")
    if commit:
        git(kok, "add", GORELI)
    git(kok, "commit", "-q", "-m", "ilk")
    return kok


def sinif(kok):
    return KD.siniflandir(AD, kok, GORELI, "shim")[0]


def yaz_beklenen(kok):
    with open(os.path.join(kok, GORELI), "w", encoding="utf-8") as f:
        f.write(KD.shim_metni(AD, kok))


def sha_agac(kok):
    h = hashlib.sha256()
    for yol in (os.path.join(kok, GORELI), os.path.join(kok, ".git", "info", "exclude"),
                os.path.join(kok, ".git", "index")):
        if os.path.isfile(yol):
            with open(yol, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


def main():
    taban = tempfile.mkdtemp(prefix="k335-")
    try:
        v1 = ev_kur(taban, "v1")
        iddia("V1 commit'li shim GUNCEL", sinif(v1) == KD.GUNCEL, sinif(v1))

        v2 = ev_kur(taban, "v2", commit=False)
        with open(os.path.join(v2, ".git", "info", "exclude"), "a") as f:
            f.write(GORELI + "\n")
        iddia("V2 izlenmeyen shim GIT_YOK", sinif(v2) == KD.GIT_YOK, sinif(v2))

        v3 = ev_kur(taban, "v3", icerik="# eski kopya\n")
        yaz_beklenen(v3)
        iddia("V3 HEAD bayat GIT_BAYAT", sinif(v3) == KD.GIT_BAYAT, sinif(v3))

        v4 = ev_kur(taban, "v4", icerik="# eski kopya\n")
        git(v4, "update-index", "--skip-worktree", GORELI)
        yaz_beklenen(v4)
        iddia("V4 skip-worktree GIT_GIZLI", sinif(v4) == KD.GIT_GIZLI, sinif(v4))

        v5 = ev_kur(taban, "v5", icerik="# eski kopya\n")
        git(v5, "update-index", "--assume-unchanged", GORELI)
        yaz_beklenen(v5)
        iddia("V5 assume-unchanged GIT_GIZLI", sinif(v5) == KD.GIT_GIZLI, sinif(v5))

        v6 = os.path.join(taban, "v6")
        os.makedirs(os.path.join(v6, ".claude"))
        yaz_beklenen(v6)
        iddia("V6 git deposu degil OKUNAMADI", sinif(v6) == KD.OKUNAMADI, sinif(v6))

        wt1 = os.path.join(taban, "wt1")
        git(v1, "worktree", "add", "-q", wt1)
        wt1_shim = os.path.join(wt1, GORELI)
        esit = os.path.isfile(wt1_shim) and KD.sha256_dosya(wt1_shim) == KD.sha256_metin(
            KD.shim_metni(AD, v1))
        iddia("V7 tatbikat: GUNCEL evin taze worktree'sinde shim birebir", esit)

        wt2 = os.path.join(taban, "wt2")
        git(v2, "worktree", "add", "-q", wt2)
        iddia("V8 tatbikat: GIT_YOK evin taze worktree'sinde shim YOK",
              not os.path.exists(os.path.join(wt2, GORELI)))

        spec = importlib.util.spec_from_file_location("kapi_dagitim_kur",
                                                      os.path.join(ARAC, "kapi-dagitim-kur.py"))
        KUR = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(KUR)
        eski_evler = KD.EVLER

        v10 = ev_kur(taban, "v10", icerik="# eski kopya\n")
        git(v10, "update-index", "--skip-worktree", GORELI)
        with open(os.path.join(v10, ".git", "info", "exclude"), "a") as f:
            f.write("# yorum\n" + GORELI + "\n")
        KD.EVLER = ((AD, v10, GORELI, "shim"),)
        try:
            once = sha_agac(v10)
            rc_kuru = KUR.main(["--ev", v10])
            iddia("V9 kurucu KURU yazmaz", rc_kuru == 0 and sha_agac(v10) == once,
                  "rc=" + str(rc_kuru))

            rc = KUR.main(["--ev", v10, "--uygula"])
            etiket = git(v10, "ls-files", "-v", GORELI).stdout.decode()[:1]
            with open(os.path.join(v10, ".git", "info", "exclude")) as f:
                ex = f.read().splitlines()
            iddia("V10a --uygula bayragi kaldirir", rc == 0 and etiket == "H",
                  "rc=" + str(rc) + " etiket=" + etiket)
            iddia("V10b --uygula exclude satirini siler, yorumu korur",
                  GORELI not in ex and "# yorum" in ex)
            iddia("V10c commit oncesi GIT_BAYAT", sinif(v10) == KD.GIT_BAYAT, sinif(v10))
            git(v10, "commit", "-q", "-m", "shim", "--", GORELI)
            iddia("V10d pathspec commit sonrasi GUNCEL", sinif(v10) == KD.GUNCEL, sinif(v10))
        finally:
            KD.EVLER = eski_evler

        gercek = KD.git_duzlemi
        KD.git_duzlemi = lambda *a, **k: KD.GUNCEL
        try:
            sahte = [sinif(v2), sinif(v3), sinif(v4)]
        finally:
            KD.git_duzlemi = gercek
        iddia("M1 mutant (git duzlemi kapali) V2/V3/V4'u GUNCEL'e cevirir -> test yakalar",
              sahte == [KD.GUNCEL] * 3 and sinif(v2) != KD.GUNCEL, str(sahte))

        k1 = ev_kur(taban, "k1", icerik=KD.SHIM_IMZASI + "\n# bayat shim\n")
        iddia("K1 kontrol: diskte bayat shim SHIM_BAYAT kalir", sinif(k1) == KD.SHIM_BAYAT, sinif(k1))
    finally:
        shutil.rmtree(taban, ignore_errors=True)

    gecen = sum(1 for _a, k in SONUC if k)
    print("IDDIA=" + str(len(SONUC)) + " GECTI=" + str(gecen) + " KIRMIZI=" + str(len(SONUC) - gecen))
    return 0 if SONUC and gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
