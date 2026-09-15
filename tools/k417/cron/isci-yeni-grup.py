#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K417 — CLAUDE'U YENI SUREC GRUBUNDA BASLATAN SARMALAYICI (15 Eyl 2026).

KULLANIM NEDENI
---------------
macOS'ta `setsid` ikilisi yok; isci.sh'in pgid taramasi `$$` (isci.sh'in
kendisi) yerine CLAUDE'un kendi grubunu tarasin diye arada bu sarmalayici
calisir. Sarmalayici:

  1) fork eder — cocuk surec
  2) cocukta os.setsid() cagirir (yeni session + process group leader;
     yeni pgid = cocugun kendi pid'i)
  3) yeni pgid'yi $CLAUDE_GRUP_DOSYASI dosyasina yazar (isci.sh sonra
     okuyacak; yasayan alt surec taramasi bu pgid ile yapilacak)
  4) os.execvp ile asil komutu (claude) calistirir

isci.sh bu sarmalayiciyi `env ... python3 isci-yeni-grup.py "$CLAUDE_BIN"
...args...` biciminde cagirir; sarmalayicinin stdout'u = claude'un
stdout'u (fork+exec ile miras). Pipeline (isci-hal-cozucu.py · tee) AYNI
KALIR; yalniz claude'un kendisi ayrilir.

CIKTI KODU
----------
Sarmalayici, claude'un exit kodunu aynen dondurur. isci.sh
${pipestatus[1]} = sarmalayicinin kodu = claude'un kodu. Tek kaynak.

ORTAM DEGISKENLERI
------------------
  CLAUDE_GRUP_DOSYASI: yeni pgid'nin yazilacagi dosya yolu (bos ise
    yazilmaz). isci.sh bu dosyayi uretip sarmalayiciya gecirir.

YASAK SINIF
-----------
Kendi setpgid'ini yapan daemon (ornek: isci-tur-bekcisi.py zaten
os.setsid() cagirir) bu eksenden YASAYAMAZ; pgid KENDI KENDININ oldugu
icin taramada gorunmez ve HAL=EKSIK tetiklenmez. Bu yordam, isci'nin
"disaridan fark edilen" alt surec taramasidir; kendi kendini izole eden
sistem surecleri icin degil ([[kendi-setsid-yapan-eksen-kacisi]]).
"""

import os
import sys


def _kullanim():
    sys.stderr.write(
        "KULLANIM: isci-yeni-grup.py [--bekleme-sn N] <komut> [arg...]\n")
    return 2


def main():
    # Argv ayristirma: opsiyonel --bekleme-sn
    argv = sys.argv[1:]
    bekleme_sn = 2  # yazma tamamlanma garantisi icin (fsync zaten yapar)
    while argv and argv[0].startswith("-"):
        if argv[0] == "--bekleme-sn" and len(argv) > 1:
            try:
                bekleme_sn = float(argv[1])
            except ValueError:
                return _kullanim()
            argv = argv[2:]
            continue
        if argv[0] in ("-h", "--help"):
            _kullanim()
            return 0
        sys.stderr.write("BILINMEYEN OPSIYON: %s\n" % argv[0])
        return _kullanim()

    if not argv:
        return _kullanim()

    hedef = argv[0]
    args = argv
    grup_dosyasi = os.environ.get("CLAUDE_GRUP_DOSYASI", "")

    pid = os.fork()
    if pid == 0:
        # COCUK: yeni pg/session leader
        try:
            os.setsid()
        except OSError as e:
            sys.stderr.write("K417-SARMA SETSID basarisiz: %s\n" % e)
            os._exit(126)

        yeni_pgid = os.getpid()
        if grup_dosyasi:
            try:
                # fsync ile diske yaz; isci.sh dosyayi okumadan once
                # pipe kapanip sarmalayici exit etmesini BEKLEMEK
                # istemiyoruz; fsync + flush yeterli (kernel page cache
                # ici ayni surec).
                with open(grup_dosyasi, "w") as f:
                    f.write(str(yeni_pgid))
                    f.flush()
                    os.fsync(f.fileno())
            except OSError as e:
                sys.stderr.write(
                    "K417-SARMA PGID yazilamadi: %s\n" % e)

        # Exec: bu noktadan sonra biz = claude
        try:
            os.execvp(hedef, args)
        except OSError as e:
            sys.stderr.write("K417-SARMA EXEC basarisiz: %s\n" % e)
            os._exit(127)

    # ANNE: cocugu bekle ve exit kodunu dondur
    try:
        while True:
            wpid, status = os.waitpid(pid, 0)
            if wpid == pid:
                if os.WIFEXITED(status):
                    return os.WEXITSTATUS(status)
                if os.WIFSIGNALED(status):
                    return 128 + os.WTERMSIG(status)
                return 1
    except KeyboardInterrupt:
        try:
            os.kill(pid, 9)
        except OSError:
            pass
        return 1
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())