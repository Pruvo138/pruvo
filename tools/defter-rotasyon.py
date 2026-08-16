#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-rotasyon.py — DEVAM.md -> DEVAM-ARSIV.md rotasyon araci.

Kullanim:
    python3 tools/defter-rotasyon.py <defter.md> <arsiv.md>
    python3 tools/defter-rotasyon.py <defter.md> <arsiv.md> --tarih 2026-08-16

KESME OLcUTU (mimar verdi):
  * Dosya `## ` baslikli bloklara bolunur; ilk `## `den onceki kisim BASLIK
    BOLGESI olup asla tasinmaz.
  * Bir blok tasinir ancak ve ancak:
      (a) icinde hic ACIK isaretci (`🔴` `🔧` `🟠` `BEKLIYOR` `KOSUYOR`
          `OKAN'DA` `ACIK KALEMLER` `YAPILACAK`) gecmiyorsa VE
      (b) baslik ya da govdesinde en az bir KAPANIS isaretci (`KAPANDI`
          `KAPANIS` `✅`) tasiyorsa.
  * Suphede kalirsan (fail-closed) tasma.

CIKIS:
    0 = basarili (veya tasinacak blok yok)
    2 = guvenlik dogrulamasi basarisiz, rotasyon iptal

Cikti son satiri:
    TASINAN=<n> DEFTER_SATIR=<n> ARSIV_SATIR=<n>
"""
import argparse
import os
import sys
import tempfile


ACIK_ISARETCILER = ("🔴", "🔧", "🟠", "BEKLIYOR", "KOSUYOR",
                    "OKAN'DA", "ACIK KALEMLER", "YAPILACAK")
KAPANIS_ISARETCILER = ("KAPANDI", "KAPANIS", "✅")


def _satir_sayisi(metin):
    """Dosyanin kendi satir sayisi (son satirda newline olmayabilir)."""
    if not metin:
        return 0
    return len(metin.splitlines())


def _bloklari_ayir(metin):
    """(baslik bolgesi, [(baslik, govde), ...]).

    Ilk `## `'den onceki her sey baslik bolgesidir. Her blok `## ` ile baslar.
    Blok basligi `## `'den sonraki ILK satirdir (newline'a kadar); gerisi govde.
    """
    satirlar = metin.splitlines()
    baslik_bolgesi = []
    bloklar = []
    aktif = None
    for satir in satirlar:
        if satir.startswith("## "):
            if aktif is not None:
                bloklar.append(aktif)
            aktif = {"baslik": satir, "govde": []}
        elif aktif is None:
            baslik_bolgesi.append(satir)
        else:
            aktif["govde"].append(satir)
    if aktif is not None:
        bloklar.append(aktif)
    return baslik_bolgesi, bloklar


def _blok_metni(blok):
    """Blok basligi + govde + orijinal newline yapisi (birebir)."""
    parcalar = [blok["baslik"]]
    if blok["govde"]:
        parcalar.extend(blok["govde"])
    return "\n".join(parcalar)


def _tasinir_mi(blok):
    """Kesme olcutunu uygula: suphede kalirsan (fail-closed) TASIMA."""
    tum = blok["baslik"] + "\n" + "\n".join(blok["govde"])
    for isaretci in ACIK_ISARETCILER:
        if isaretci in tum:
            return False
    for isaretci in KAPANIS_ISARETCILER:
        if isaretci in tum:
            return True
    return False


def _atomik_yaz(yol, icerik):
    """Gecici dosya + os.replace ile atomik yazma."""
    dizin = os.path.dirname(os.path.abspath(yol)) or "."
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".rotasyon-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(icerik.encode("utf-8"))
        os.replace(gecici, yol)
    except Exception:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("defter", help="kaynak defter (ornek: DEVAM.md)")
    p.add_argument("arsiv", help="hedef arsiv (ornek: DEVAM-ARSIV.md)")
    p.add_argument("--tarih", default=None,
                   help="rotasyon tarihi YYYY-MM-DD (varsayilan: bugun)")
    a = p.parse_args(argv)

    if a.tarih is None:
        import datetime
        tarih = datetime.date.today().isoformat()
    else:
        tarih = a.tarih

    defter_yol = os.path.abspath(a.defter)
    arsiv_yol = os.path.abspath(a.arsiv)

    # Oku (orijinal baytlar uzerinden dogrulama yapacagiz).
    with open(defter_yol, "rb") as f:
        defter_ham = f.read()
    arsiv_ham = b""
    if os.path.exists(arsiv_yol):
        with open(arsiv_yol, "rb") as f:
            arsiv_ham = f.read()

    defter_eski_bayt = len(defter_ham)
    arsiv_eski_bayt = len(arsiv_ham)

    defter_metin = defter_ham.decode("utf-8")
    arsiv_metin = arsiv_ham.decode("utf-8") if arsiv_ham else ""

    baslik_bolgesi, bloklar = _bloklari_ayir(defter_metin)

    tasinacak = []
    kalacak = []
    for blok in bloklar:
        if _tasinir_mi(blok):
            tasinacak.append(blok)
        else:
            kalacak.append(blok)

    if not tasinacak:
        defter_satir = _satir_sayisi(defter_metin)
        arsiv_satir = _satir_sayisi(arsiv_metin)
        print("TASINAN=0 DEFTER_SATIR=%d ARSIV_SATIR=%d" % (defter_satir, arsiv_satir))
        return 0

    tasinan_parcalar = [_blok_metni(b) for b in tasinacak]

    # Yeni defter: baslik bolgesi + kalan bloklar.
    yeni_defter_parcalar = []
    if baslik_bolgesi:
        yeni_defter_parcalar.append("\n".join(baslik_bolgesi))
    for blok in kalacak:
        yeni_defter_parcalar.append(_blok_metni(blok))
    yeni_defter_metin = "\n\n".join(yeni_defter_parcalar)
    # Eger orijinalde son satirda newline yoksa ayni sekilde koru.
    if defter_ham and not defter_ham.endswith(b"\n"):
        yeni_defter_metin = yeni_defter_metin.rstrip("\n")

    # Yeni arsiv: ayirac + tasinan bloklar + eski arsiv.
    ayirac = "## %s — ROTASYON: asagidaki %d blok defterden BURAYA TASINDI" % (
        tarih, len(tasinacak))
    yeni_arsiv_parcalar = [ayirac]
    yeni_arsiv_parcalar.extend(tasinan_parcalar)
    if arsiv_metin.strip():
        yeni_arsiv_parcalar.append(arsiv_metin)
    yeni_arsiv_metin = "\n\n".join(yeni_arsiv_parcalar)
    if arsiv_ham and not arsiv_ham.endswith(b"\n"):
        yeni_arsiv_metin = yeni_arsiv_metin.rstrip("\n")

    # GUVENLIK: tasinan bayt, defterdeki GERCEK azalmadir.
    yeni_defter_bayt = len(yeni_defter_metin.encode("utf-8"))
    yeni_arsiv_bayt = len(yeni_arsiv_metin.encode("utf-8"))
    tasinan_bayt = defter_eski_bayt - yeni_defter_bayt

    defter_yedek = defter_ham
    arsiv_yedek = arsiv_ham

    _atomik_yaz(defter_yol, yeni_defter_metin)
    _atomik_yaz(arsiv_yol, yeni_arsiv_metin)

    with open(defter_yol, "rb") as f:
        defter_disk = f.read()
    with open(arsiv_yol, "rb") as f:
        arsiv_disk = f.read()

    defter_yeni_bayt = len(defter_disk)
    arsiv_yeni_bayt = len(arsiv_disk)

    dogru = (
        arsiv_yeni_bayt - arsiv_eski_bayt >= tasinan_bayt and
        defter_eski_bayt - defter_yeni_bayt == tasinan_bayt
    )

    if not dogru:
        # Geri yaz.
        _atomik_yaz(defter_yol, defter_yedek.decode("utf-8"))
        _atomik_yaz(arsiv_yol, arsiv_yedek.decode("utf-8"))
        print("ROTASYON IPTAL", file=sys.stderr)
        print("  beklenen: arsiv +%d bayt, defter -%d bayt" % (
            tasinan_bayt, tasinan_bayt), file=sys.stderr)
        print("  gorulen:  arsiv %d -> %d bayt, defter %d -> %d bayt" % (
            arsiv_eski_bayt, arsiv_yeni_bayt,
            defter_eski_bayt, defter_yeni_bayt), file=sys.stderr)
        defter_satir = _satir_sayisi(defter_yedek.decode("utf-8"))
        arsiv_satir = _satir_sayisi(arsiv_yedek.decode("utf-8"))
        print("TASINAN=%d DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
            len(tasinacak), defter_satir, arsiv_satir))
        return 2

    defter_satir = _satir_sayisi(yeni_defter_metin)
    arsiv_satir = _satir_sayisi(yeni_arsiv_metin)
    print("TASINAN=%d DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
        len(tasinacak), defter_satir, arsiv_satir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
