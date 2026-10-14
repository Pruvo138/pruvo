#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre-push GECMIS NOBETI BLOGUNUN tanimi + `.git/hooks` kurucusu (hooksPath'te REDDEDER).

🔴 14 Eki 2026 YENIDEN HEDEFLENDI: bu depoda `core.hooksPath` 4 Agu'tan (c2b1292e) beri
   `.git/pruvo-kancalar`dir (tools/kanca-kur.py, izlenen kaynak tools/kancalar/). Bu
   betik blogu hala `<git-common-dir>/hooks/pre-push`a yaziyordu -> git o dosyayi HIC
   okumuyordu, nobet ~10 hafta HICBIR push'ta kosmadi (o pencerede 5 ic rapor PUBLIC'e
   cikti: `python3 tools/kisisel-veri-test.py --gecmis`). Simdi:
     * BLOK izlenen kaynakta, tools/kancalar/pre-push icinde BAYT-ESIT durur
       (tools/kanca-kablolama-test.py olcer); kurulum = `python3 tools/kanca-kur.py`.
     * Git BASKA bir yolu okuyorsa (core.hooksPath) kurma/kaldirma REDDEDILIR (rc 3,
       hicbir sey yazilmaz) — olu dosyaya "yazildi" demek kapatilan hatanin ta kendisi.
     * `--dogrula` git'in FIILEN okudugu kancaya bakar.
   `.git/hooks` yolu yalniz core.hooksPath'siz depolarda (sentetik/test) yazilir.

Kurulu mu: `python3 tools/gecmis-nobeti-hook-kur.py --dogrula` ya da
`python3 tools/kisisel-veri-test.py` son satirlari ("Canli aralik taramasi pre-push
kancasinda: KURULU / KURULU DEGIL").

NE YAPAR: pre-push icine isaretli bir blok ekler. Blok her push'ta
`tools/kisisel-veri-test.py --pre-push` cagirir; kapi kirmizi yanarsa PUSH DURUR.

NEDEN VAR (olculdu 30 Tem — AYNI HATA DORDUNCU KEZ):
  Ic rapor sizinti nobetcisi dosya ADINI dogru taniyordu ama yalniz `git ls-files` =
  MEVCUT CALISMA AGACINI tariyordu. Bir dosya eklenip AYNI GUN silinirse calisma
  agaci tertemiz olur, nobetci hicbir sey gormez — ama commit KALICIDIR ve depo
  PUBLIC oldugu icin blob raw.githubusercontent.com'dan anonim cekilebilir.
  Olculdu: `tools/yedek-topolojisi-raporu.md` 2b6373ec ile eklendi, d058a11c ile
  cikarildi (ikisi de 21 Tem, ikisi de origin/main'in atasi) -> bugun hala HTTP 200.
  `--gecmis` kipi ilk kosumda 11 kayit buldu, 6'si uzak referanstan erisilebilir.

🔴 NEDEN CI DEGIL DE KANCA (olculerek secildi):
  1) `.github/workflows/deploy.yml` `actions/checkout@v4`i fetch-depth VERMEDEN
     kullanir -> SIG (depth=1) klon: `origin/main..HEAD` gibi bir aralik CI'da
     COZULEMEZ, taranacak gecmis YOKTUR.
  2) deploy.yml `on: push: branches: [main]` -> yalniz main'e ve yalniz PUSH'TAN
     SONRA kosar. O anda commit ZATEN public remote'tadir; yayini durdurmak sizmis
     blob'u geri getirmez. 27 Tem'in iki kacagi da DAL push'unda olmustu; CI o
     dallari hic gormez. Bu eksenin butun degeri ONLEMEDIR.
  CI'da yine de gecmis kolunun FIKSTURLERI kosar (gercek git ile gecici depo kurup
  olayi yeniden oynatan bicim capasi dahil) -> parser/kural zinciri nobetsiz kalmaz.

🔴 FAIL-CLOSED (yedek blogunun tam TERSI, bilincli): sizinti kapisi bir "iyi olurdu"
   degil, gecilemez bir kapidir. Betik bulunamazsa/patlarsa push DURUR. Blokta
   `exit 1` VARDIR. Mesru bir tikanmada cikis yolu git'in kendi `--no-verify`
   bayragidir; DOGRU cozum ise commit'i daldan cikarmaktir (rapor IZLENMEYEN kalir).

STDIN DIKKATI: pre-push girdisi (ref satirlari) stdin'den gelir ve BIR KEZ okunur.
Bu blok stdin'i gecici bir dosyaya alir, kapiyi onunla besler, sonra `exec 0<` ile
dosyanin BASINDAN geri baglar -> ayni hook'taki D1 senkron blogunun `while read`
dongusu girdiyi eksiksiz gorur. Blok bu yuzden D1 blogundan ONCE yerlestirilir
(D1 blogu `exit 0` ile cikabiliyor; sona eklenen blok cogu push'ta hic kosmazdi).
tools/kancalar/pre-push'ta GERI-DONUS blogunun ARDINA, KANARYA SONRASI'ndan ONCE durur:
blogun gercek-git fiksturu (gecici depo) kanarya once/sonra olcumunun ICINDE kalir.

Kullanim:
    python3 tools/gecmis-nobeti-hook-kur.py            # kur / guncelle (hooksPath'te RET)
    python3 tools/gecmis-nobeti-hook-kur.py --kuru     # ne yapacagini goster, YAZMA
    python3 tools/gecmis-nobeti-hook-kur.py --dogrula  # git'in OKUDUGU kancada kurulu mu (0/1)
    python3 tools/gecmis-nobeti-hook-kur.py --kaldir   # yalniz bu blogu cikar (hooksPath'te RET)
    python3 tools/gecmis-nobeti-hook-kur.py --repo YOL # baska bir depoya (test: K384-V5/V6)
"""
import os
import shutil
import stat
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from git_ortami import kanca_hedef_reddi, kanca_yollari  # noqa: E402

# Kurulum REDDEDILDI: git bu kurucunun yazdigi yolu OKUMUYOR (core.hooksPath).
RC_RET = 3

BAS = ("# >>> PRUVO GECMIS NOBETI BLOGU "
       "(tools/gecmis-nobeti-hook-kur.py uretir — ELLE DUZENLEME) >>>")
SON = "# <<< PRUVO GECMIS NOBETI BLOGU <<<"

BLOK = BAS + """
# FAIL-CLOSED: ic rapor bir commit'te EKLENDIYSE (sonradan SILINSE BILE) push DURUR.
# Gerekce + CI yerine kanca secimi: tools/gecmis-nobeti-hook-kur.py basligi.
# stdin BIR KEZ okunur -> gecici dosyaya alinip 'exec 0<' ile geri baglanir ki
# asagidaki D1 senkron blogunun 'while read' dongusu ref satirlarini gorebilsin.
pruvo_gn_kok=$(git rev-parse --show-toplevel 2>/dev/null)
pruvo_gn_tmp=$(mktemp 2>/dev/null)
if [ -z "$pruvo_gn_tmp" ] || [ ! -f "$pruvo_gn_tmp" ]; then
  echo "!! PUSH DURDURULDU — gecmis nobeti girdisi icin gecici dosya acilamadi." >&2
  exit 1
fi
cat > "$pruvo_gn_tmp"
if [ -z "$pruvo_gn_kok" ] || [ ! -f "$pruvo_gn_kok/tools/kisisel-veri-test.py" ]; then
  echo "!! GECMIS NOBETI KOSULAMADI (tools/kisisel-veri-test.py yok) — PUSH DURDURULDU." >&2
  echo "!! Sizinti kapisi fail-closed'dir. Kasten atlamak icin: git push --no-verify" >&2
  rm -f "$pruvo_gn_tmp"
  exit 1
fi
if ! python3 "$pruvo_gn_kok/tools/kisisel-veri-test.py" --pre-push < "$pruvo_gn_tmp"; then
  echo "!! PUSH DURDURULDU — ic rapor sizintisi ya da OLCULEMEDI (gecmis ekseni)." >&2
  echo "!! Envanter: python3 tools/kisisel-veri-test.py --gecmis" >&2
  rm -f "$pruvo_gn_tmp"
  exit 1
fi
exec 0< "$pruvo_gn_tmp"
rm -f "$pruvo_gn_tmp"
""" + SON


def hook_yolu(repo):
    """Ortak git dizinindeki hooks/pre-push (worktree'de de ANA depoyu gosterir)."""
    p = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    return os.path.join(p.stdout.strip(), "hooks", "pre-push")


# Yedek blogunun isareti — bizim blok ONUN ARDINA girer (yedek fail-open'dir ve
# stdin okumaz; boylece push bloklansa bile yedek yine alinmis olur).
_YEDEK_SON = "# <<< PRUVO YEDEK BLOGU <<<"


def yeni_icerik(mevcut, kaldir=False):
    """Blogu ekler/gunceller/cikarir. (yeni_metin, eylem) doner."""
    if mevcut is None:
        if kaldir:
            return None, "hook yok — yapacak bir sey yok"
        return "#!/bin/sh\n" + BLOK + "\n", "YENI hook olusturuldu"

    if BAS in mevcut and SON in mevcut:
        bas = mevcut.index(BAS)
        son = mevcut.index(SON) + len(SON)
        yeni = mevcut[:bas] + ("" if kaldir else BLOK) + mevcut[son:]
        if kaldir:
            yeni = yeni.replace("\n\n\n", "\n\n")
        return yeni, ("blok CIKARILDI" if kaldir else "mevcut blok GUNCELLENDI")

    if kaldir:
        return mevcut, "blok zaten yok"

    # Blok YOK -> yedek blogunun ARDINA; yoksa shebang'in hemen ardina.
    # Her iki halde de D1 senkron blogunun 'exit 0'larindan ve 'while read'inden ONCE.
    if _YEDEK_SON in mevcut:
        kes = mevcut.index(_YEDEK_SON) + len(_YEDEK_SON)
        return (mevcut[:kes] + "\n" + BLOK + mevcut[kes:],
                "blok EKLENDI (yedek blogunun ardina)")
    satirlar = mevcut.splitlines(True)
    yer = 1 if satirlar and satirlar[0].startswith("#!") else 0
    return ("".join(satirlar[:yer]) + BLOK + "\n" + "".join(satirlar[yer:]),
            "blok EKLENDI (basa)")


def kurulu_mu(yol):
    if not yol or not os.path.isfile(yol):
        return False
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    except OSError:
        return False
    return BAS in metin and "--pre-push" in metin


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--repo" in argv:
        i = argv.index("--repo")
        if i + 1 >= len(argv):
            print("HATA: --repo bir yol ister", file=sys.stderr)
            return 2
        repo = argv[i + 1]
        del argv[i:i + 2]
    kuru = "--kuru" in argv
    kaldir = "--kaldir" in argv
    dogrula = "--dogrula" in argv
    bilinmeyen = [a for a in argv if a not in ("--kuru", "--kaldir", "--dogrula")]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2

    yol = hook_yolu(repo)
    if not yol:
        print("HATA: git deposu bulunamadi: " + repo, file=sys.stderr)
        return 1

    if dogrula:
        # Git'in FIILEN okudugu kanca (core.hooksPath dahil) — `yol` degil.
        okunan, _eski = kanca_yollari(repo, "pre-push")
        if not okunan:
            print("HATA: git'in okudugu pre-push yolu OLCULEMEDI: " + repo, file=sys.stderr)
            return 1
        var = kurulu_mu(okunan)
        print("hook (git'in okudugu): %s\ngecmis nobeti blogu: %s"
              % (okunan, "KURULU" if var else "YOK"))
        return 0 if var else 1

    ret = kanca_hedef_reddi(repo, "pre-push")
    if ret:
        print("🔴 KURULUM REDDEDILDI (rc=%d, hicbir sey yazilmadi): %s" % (RC_RET, ret),
              file=sys.stderr)
        return RC_RET

    mevcut = None
    if os.path.isfile(yol):
        with open(yol, encoding="utf-8", errors="replace") as f:
            mevcut = f.read()

    yeni, eylem = yeni_icerik(mevcut, kaldir=kaldir)
    print("hook: " + yol)
    print("eylem: " + eylem)
    if yeni is None or yeni == mevcut:
        print("degisiklik YOK (idempotent).")
        return 0
    if kuru:
        print("KURU KOSUM — yazilmadi.")
        return 0

    kopya = yol + ".pruvo-gecmis-oncesi"
    if mevcut is not None and not os.path.exists(kopya):
        shutil.copy2(yol, kopya)
        print("guvenlik kopyasi: " + kopya)

    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("yazildi + calistirilabilir yapildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
