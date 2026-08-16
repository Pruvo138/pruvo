#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-kota-kapisi.py — DEVAM.md defter kota kapisi (INDEX kolu).

Kullanim:
    python3 tools/defter-kota-kapisi.py [depo-koku]

Davranis (INDEX kolu, pre-commit):
    * DEVAM.md INDEX'te (staged) yoksa: sessizce exit 0 (kapsam disi).
    * DEVAM.md INDEX'te varsa ve satir sayisi > 130 ise:
        - stderr'e iki satirlik RED mesaji basar.
        - sayac dosyasina `RED` satiri yazar.
        - exit 1
    * Satir sayisi 130 veya az ise: exit 0.

🔴 BYPASS KOLU (`--bypass-kontrol`, pre-push'ta cagrilir) — NEDEN AYRI VAR:
`--no-verify` ile atlanan bir kanca HIC KOSMAZ, yani kendi atlanisini KAYDEDEMEZ.
"RED sayisi" bypass sayisi DEGILDIR (RED, kapinin CALISTIGI haldir). Bypass ancak
SONUCUNDAN anlasilir: kota asilmis bir DEVAM.md **commit'lenmis** ve push'a gelmisse,
kapi ya atlanmistir ya hic kosmamistir. Bu kol o hali sayar:
    * HEAD'deki DEVAM.md satir sayisi > 130 ise sayac dosyasina `BYPASS` satiri yazar.
    * 🔴 BLOKLAMAZ (her zaman exit 0): Okan hukmu "yasaklanamaz ama SAYILIR".
Sayac repo DISINDADIR (`~/.claude/cron/defter-kota-bypass.tsv`) — commit'e girmez,
gunluk 15:00 olcumune `DEFTER_KOTA_BYPASS` ekseni olarak okunur.

CI'da kosmaz; kancalar/pre-commit adim 8 (INDEX) + kancalar/pre-push (bypass) cagrisi.
"""
import datetime
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SAYAC_YOLU = os.environ.get("PRUVO_DEFTER_KOTA_SAYAC",
                           os.path.expanduser("~/.claude/cron/defter-kota-bypass.tsv"))
TAVAN = 130


def _git(args, kok):
    r = subprocess.run(["git", "-C", kok] + list(args),
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def _devam_stage_de(kok):
    rc, out, _ = _git(["diff", "--cached", "--name-only",
                        "--diff-filter=ACMR", "-z"], kok)
    if rc != 0:
        return None  # OLCULEMEDI
    return "DEVAM.md" in (out.split("\0") if out else [])


def _devam_index_satir(kok):
    rc, out, _ = _git(["cat-file", "blob", ":DEVAM.md"], kok)
    if rc != 0:
        return None
    return len(out.splitlines())


def _sayaç_yaz(kok, satir, sinif="RED"):
    """Sayac satiri: <ISO>\t<sinif>\t<depo>\t<satir>. Yazim HUKMU ETKILEMEZ."""
    try:
        os.makedirs(os.path.dirname(SAYAC_YOLU), exist_ok=True)
        with open(SAYAC_YOLU, "a", encoding="utf-8") as f:
            f.write("%s\t%s\t%s\t%d\n" % (
                datetime.datetime.now().isoformat(), sinif, kok, satir))
        return True
    except Exception:                                       # noqa: BLE001
        return False


def _devam_head_satir(kok):
    rc, out, _ = _git(["cat-file", "blob", "HEAD:DEVAM.md"], kok)
    if rc != 0:
        return None
    return len(out.splitlines())


def bypass_kontrol(kok):
    """PUSH kolu — kota asilmis bir DEVAM.md commit'lenmisse BYPASS say. BLOKLAMAZ.

    🔴 Neden bloklamiyor: Okan hukmu "`--no-verify` yasaklanamaz ama SAYILIR".
    Bloklamak, kapiyi zaten atlamis birine ikinci bir duvar cikarmak olurdu; olculen
    ihtiyac SAYIDIR (gunluk 15:00 olcumu `DEFTER_KOTA_BYPASS`)."""
    satir = _devam_head_satir(kok)
    if satir is None:
        # Defteri olmayan depo (kardes evler) ya da okunamadi -> sessiz gec, BLOKLAMA.
        return 0
    if satir > TAVAN:
        _sayaç_yaz(kok, satir, sinif="BYPASS")
        print("!! DEFTER KOTASI BYPASS SAYILDI — HEAD'deki DEVAM.md %d satir "
              "(tavan %d). Push DURDURULMADI, yalnizca sayildi: %s"
              % (satir, TAVAN, SAYAC_YOLU), file=sys.stderr)
    return 0


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--bypass-kontrol" in argv:
        argv = [a for a in argv if a != "--bypass-kontrol"]
        return bypass_kontrol(argv[1] if len(argv) > 1 else ROOT)
    kok = argv[1] if argv and len(argv) > 1 else ROOT

    stage_de = _devam_stage_de(kok)
    if stage_de is None:
        print("!! COMMIT DURDURULDU — DEVAM.md stage kontrolu OLCULEMEDI.",
              file=sys.stderr)
        return 1
    if not stage_de:
        return 0

    satir = _devam_index_satir(kok)
    if satir is None:
        print("!! COMMIT DURDURULDU — DEVAM.md INDEX blob'u okunamadi.",
              file=sys.stderr)
        return 1

    if satir <= TAVAN:
        return 0

    print("!! DEFTER KOTASI ASILDI — DEVAM.md %d satir (tavan %d)." % (
        satir, TAVAN), file=sys.stderr)
    print("!! CARE: python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py "
          "/Users/okan/dev/pruvo/DEVAM.md /Users/okan/dev/pruvo/DEVAM-ARSIV.md",
          file=sys.stderr)
    _sayaç_yaz(kok, satir)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
