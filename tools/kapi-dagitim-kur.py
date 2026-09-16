#!/usr/bin/env python3
"""K304/K335 KURUCU — kardes evin mimar icra kapisi SHIM'ini kurar ve GIT'te gorunur kilar.

Tek kaynak `tools/kapi_dagitim.py` (shim metni + siniflama); bu arac ikinci bir renderer
YAZMAZ. Ic-kapi muafiyeti bu araca ADIYLA baglidir (`mimar-icra-kapisi.py`
KAPI_DAGITIM_KURUCU_ADI) — dosya adi degistirilmez.

KULLANIM:
  python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-kur.py --ev <ev_koku>            # KURU: plan basar, YAZMAZ
  python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-kur.py --ev <ev_koku> --uygula

--uygula su uc seyi yapar (yalniz gerekeni):
  1. diskteki shim beklenen metinden farkliysa yazar;
  2. shim uzerindeki skip-worktree / assume-unchanged bayragini kaldirir;
  3. evin `.git/info/exclude` dosyasindan shim'i TAM ADIYLA anan satiri siler.
COMMIT ETMEZ: kardes evin commit'i ev sahibinin (ya da mimarin pathspec'li) isidir; arac
sonunda gereken komutu basar. Kabul: `kapi-dagitim-kapisi.py --ev <kok>` -> GUNCEL.

rc: 0 = islem tamam / kuru plan basildi · 1 = uygulama sonrasi sinif hala kirmizi ·
    2 = kullanim hatasi / tanimsiz ev / kaynak evi.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi_dagitim as KD  # noqa: E402


def ev_kaydi(kok):
    hedef = os.path.normpath(kok)
    for kayit in KD.EVLER:
        if os.path.normpath(kayit[1]) == hedef:
            return kayit
    return None


def exclude_satirlari(ev_koku, goreli):
    """exclude dosyasi yolu + shim'i TAM ADIYLA anan satir indeksleri."""
    yol = os.path.join(ev_koku, ".git", "info", "exclude")
    if not os.path.isfile(yol):
        return yol, [], []
    with open(yol, encoding="utf-8") as f:
        satirlar = f.read().splitlines()
    adaylar = {goreli, "/" + goreli}
    return yol, satirlar, [i for i, s in enumerate(satirlar) if s.strip() in adaylar]


def main(argv):
    uygula = "--uygula" in argv
    if "--ev" not in argv or argv.index("--ev") + 1 >= len(argv):
        sys.stderr.write(__doc__ + "\n")
        return 2
    kayit = ev_kaydi(argv[argv.index("--ev") + 1])
    if kayit is None:
        sys.stderr.write("KUR: tanimsiz ev (tools/kapi_dagitim.py:EVLER). Fail-closed.\n")
        return 2
    ad, kok, goreli, mod = kayit
    if mod != "shim":
        sys.stderr.write("KUR: " + ad + " kaynak evidir, shim KURULMAZ.\n")
        return 2

    yol = KD.kurulu_yol(kok, goreli)
    beklenen = KD.shim_metni(ad, kok)
    once = KD.siniflandir(ad, kok, goreli, mod)[0]
    print("EV=" + ad + " ONCE=" + once + " YOL=" + yol)

    mevcut = None
    if os.path.isfile(yol):
        with open(yol, encoding="utf-8") as f:
            mevcut = f.read()
    yaz = mevcut != beklenen
    ls = KD._git(kok, "ls-files", "-v", "--", goreli)
    etiket = ls.stdout.decode("utf-8", "replace")[:1] if ls.returncode == 0 else ""
    bayrak = etiket == "S" or (etiket != "" and etiket.islower())
    ex_yol, ex_satirlar, ex_idx = exclude_satirlari(kok, goreli)

    print("PLAN YAZ=" + ("EVET" if yaz else "HAYIR")
          + " BAYRAK_KALDIR=" + ("EVET" if bayrak else "HAYIR")
          + " EXCLUDE_SIL=" + str(len(ex_idx)))
    if not uygula:
        print("KURU: hicbir sey yazilmadi (--uygula ile uygula).")
        return 0

    if yaz:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(beklenen)
    if bayrak:
        # Iki bayrak AYRI cagrida kalkar: tek cagrida birlestirilince git skip-worktree'yi
        # sessizce BIRAKIYOR (rc=0, etiket 'S' kaliyor) — kapi-dagitim-test.py V10a olcer.
        for secenek in ("--no-skip-worktree", "--no-assume-unchanged"):
            r = KD._git(kok, "update-index", secenek, "--", goreli)
            if r.returncode != 0:
                sys.stderr.write("KUR: git update-index " + secenek + " rc="
                                 + str(r.returncode) + "\n")
                return 1
    if ex_idx:
        kalan = [s for i, s in enumerate(ex_satirlar) if i not in set(ex_idx)]
        with open(ex_yol, "w", encoding="utf-8") as f:
            f.write("\n".join(kalan) + ("\n" if kalan else ""))

    disk = KD.siniflandir(ad, kok, goreli, mod)[0]
    print("SONRA=" + disk)
    if disk in (KD.GIT_YOK, KD.GIT_BAYAT):
        print("SIRADAKI (commit, pathspec'li): git -C " + kok + " add -- " + goreli
              + " && git -C " + kok + " commit -m 'kapi: mimar icra kapisi shim git'e alindi (K335)' -- "
              + goreli)
    return 0 if disk in KD.YESIL_SINIFLAR or disk in (KD.GIT_YOK, KD.GIT_BAYAT) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
