#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`pre-push` kancasina GECMIS GERI-DONUS NOBETI BLOGUNU kurar (idempotent).

🖥️ YENI MAKINEDE / GOCTEN SONRA TEK YAPILACAK SEY:
        python3 tools/gecmis-geri-donus-hook-kur.py
    Kancalar `.git/hooks` altinda yasar ve GIT'E GIRMEZ -> her makinede yeniden kurulur.
    Kurulu mu: `python3 tools/gecmis-geri-donus-hook-kur.py --dogrula`.
    Nobetci: `python3 tools/kanca-nobeti.py` (bu blogu da yargilar).

NE YAPAR: `<git-common-dir>/hooks/pre-push` icine isaretli bir blok ekler. Blok
`tools/gecmis-geri-donus-kapisi.py --pre-push` cagirir; kapi kirmizi yanarsa PUSH DURUR.

🔴 NEDEN `pre-push` (commit-msg ya da CI degil) — eksen olcumuyle secildi:
  * Olculen ariza YENI YAZILAN bir commit DEGILDI: temizlikten ONCEKI taban uzerine
    kurulmus bir dalin merge'i, ESKI sizintili commit'leri gecmise geri bagladi.
    O commit'lerin mesajlari YENIDEN YAZILMAZ -> `commit-msg` kancasi onlari HIC
    gormez. Bu eksenin tek dogru kancasi push anidir.
  * CI (deploy.yml) push'TAN SONRA kosar; o an nesneler ZATEN public remote'tadir.
    Tamir degeri yoktur, gorunurluk degeri vardir -> ikinci hat.

🔴 STDIN GERI VERILIR — SESSIZ REGRESYON ONLENDI: `pre-push` kancasi itilen ref'leri
STDIN'den alir ve bu dosyadaki DIGER bloklar (ozellikle D1 SENKRONU) ayni stdin'i
`while read` ile okur. Blok stdin'i tuketip birakmis olsaydi D1 senkronu her push'ta
BOS girdi gorur, "urunler.json degismedi" sanip HIC KOSMAZDI — site urunu gosterir,
EGE GOREMEZ (bu depoda olculmus sessiz satis kaybi sinifi). Bu yuzden blok stdin'i
gecici bir dosyaya alir, kapiyi ondan besler ve `exec <` ile kalan kancaya AYNEN
geri verir.

🔴 FAIL-CLOSED (bilincli): betik bulunamazsa/patlarsa PUSH DURUR. Blokta `exit 1`
   VARDIR. Mesru tikanmada cikis yolu git'in kendi `--no-verify` bayragidir
   (gurultulu ve kayitli), kapiyi sessizce gevsetmek DEGIL.

🔴 BLOK EN BASA KONUR: bu dosyadaki diger bloklar (yedek, kutu arsivi, D1 senkronu)
   kosulsuz `exit 0` tasir; sona eklenen bir blok HIC KOSMAZDI.

Kullanim:
    python3 tools/gecmis-geri-donus-hook-kur.py            # kur / guncelle
    python3 tools/gecmis-geri-donus-hook-kur.py --kuru     # ne yapacagini goster, YAZMA
    python3 tools/gecmis-geri-donus-hook-kur.py --dogrula  # kurulu mu (cikis 0/1)
    python3 tools/gecmis-geri-donus-hook-kur.py --kaldir   # yalniz bu blogu cikar
    python3 tools/gecmis-geri-donus-hook-kur.py --repo YOL # baska bir depoya kur (test)
"""
import os
import shutil
import stat
import subprocess
import sys

BAS = ("# >>> PRUVO GECMIS GERI-DONUS NOBETI BLOGU "
       "(tools/gecmis-geri-donus-hook-kur.py uretir — ELLE DUZENLEME) >>>")
SON = "# <<< PRUVO GECMIS GERI-DONUS NOBETI BLOGU <<<"

BLOK = BAS + """
# FAIL-CLOSED: bu itme temizlenmis sizintiyi (mesaj YA DA icerik ekseni) GERI
# GETIRIYORSA PUSH DURUR. Gerekce: tools/gecmis-geri-donus-hook-kur.py basligi.
pruvo_gd_kok=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$pruvo_gd_kok" ] || [ ! -f "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" ]; then
  echo "!! GECMIS GERI-DONUS NOBETI KOSULAMADI (tools/gecmis-geri-donus-kapisi.py yok) — PUSH DURDURULDU."
  echo "!! Sizinti kapisi fail-closed'dir. Kasten atlamak icin: git push --no-verify"
  exit 1
fi
# STDIN'i al, kapiyi ondan besle, sonra kalan kancaya AYNEN geri ver (D1 senkronu
# ayni stdin'i okur — tuketip birakmak onu sessizce oldururdu).
pruvo_gd_girdi=$(mktemp 2>/dev/null || echo /tmp/pruvo-gd-$$)
cat > "$pruvo_gd_girdi"
python3 "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" --pre-push < "$pruvo_gd_girdi"
pruvo_gd_rc=$?
if [ "$pruvo_gd_rc" -ne 0 ]; then
  rm -f "$pruvo_gd_girdi"
  echo "!! PUSH DURDURULDU — bu itme temizlenmis sizintiyi geri getiriyor (rc=$pruvo_gd_rc)."
  exit 1
fi
exec < "$pruvo_gd_girdi"
rm -f "$pruvo_gd_girdi"
""" + SON


def hook_yolu(repo):
    """Ortak git dizinindeki hooks/pre-push (worktree'de de ANA depoyu gosterir)."""
    p = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    return os.path.join(p.stdout.strip(), "hooks", "pre-push")


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
    # Blok YOK -> shebang'in hemen ardina. 🔴 SONA EKLENEMEZ: bu dosyadaki diger
    # bloklar kosulsuz `exit 0` tasir, sondaki blok HIC kosmazdi.
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


def kur(repo, kuru=False, kaldir=False, sessiz=False):
    """(rc, yol). Yazar/gunceller/cikarir."""
    yol = hook_yolu(repo)
    if not yol:
        if not sessiz:
            print("HATA: git deposu bulunamadi: " + repo, file=sys.stderr)
        return 1, None
    mevcut = None
    if os.path.isfile(yol):
        with open(yol, encoding="utf-8", errors="replace") as f:
            mevcut = f.read()
    yeni, eylem = yeni_icerik(mevcut, kaldir=kaldir)
    if not sessiz:
        print("hook: " + yol)
        print("eylem: " + eylem)
    if yeni is None or yeni == mevcut:
        if not sessiz:
            print("degisiklik YOK (idempotent).")
        return 0, yol
    if kuru:
        if not sessiz:
            print("KURU KOSUM — yazilmadi.")
        return 0, yol
    kopya = yol + ".pruvo-geri-donus-oncesi"
    if mevcut is not None and not os.path.exists(kopya):
        shutil.copy2(yol, kopya)
        if not sessiz:
            print("guvenlik kopyasi: " + kopya)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if not sessiz:
        print("yazildi + calistirilabilir yapildi.")
    return 0, yol


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
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
        argv = argv[:i] + argv[i + 2:]
    bilinmeyen = [a for a in argv if a not in ("--kuru", "--kaldir", "--dogrula")]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2
    if "--dogrula" in argv:
        yol = hook_yolu(repo)
        var = kurulu_mu(yol)
        print("hook: %s\ngecmis geri-donus nobeti blogu: %s"
              % (yol, "KURULU" if var else "YOK"))
        return 0 if var else 1
    rc, _ = kur(repo, kuru="--kuru" in argv, kaldir="--kaldir" in argv)
    return rc


if __name__ == "__main__":
    sys.exit(main())
