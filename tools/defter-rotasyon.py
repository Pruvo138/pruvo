#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-rotasyon.py — DEVAM.md -> DEVAM-ARSIV.md rotasyon araci.

Kullanim:
    python3 tools/defter-rotasyon.py <defter.md> <arsiv.md>
    python3 tools/defter-rotasyon.py <defter.md> <arsiv.md> --tarih 2026-08-16

KESME OLcUTU (mimar verdi):
  * Dosya `## ` baslikli bloklara bolunur; ilk `## `den onceki kisim BASLIK
    BOLGESI olup asla tasinmaz.
  * Bir BLOK tasinir ancak ve ancak:
      (a) icinde hic ACIK isaretci gecmiyorsa VE
      (b) baslik ya da govdesinde en az bir KAPANIS isaretci tasiyorsa.
  * Blok granulu tasinma GERCEKLESMEYEN bir acik blok icindeki LISTE MADDELERI
    tek tek degerlendirilir. Bir MADDE tasinir ancak ve ancak:
      (a) maddede en az bir KAPANIS isaretci tasiyorsa VE
      (b) maddede hic ACIK isaretci gecmiyorsa VE
      (c) madde ARSIV'E isaret etmiyorsa (MADDE_VETO_DESENLERI icinde
          gecen desenlerden biri bulunursa TASINMAZ).
  * ACIK jetonlarin BULUNMASI harf tabanli olanlarda kelime-sinirli
    (`re` ile `\bJETON\b`); emoji/ikon olanlarda alt-dize kalir. Bu ayrim
    `ACIKLAMA`, `ACIKLANDI` gibi alakasiz kelimelerin yanlis veto
    tetiklememesi icin zorunludur (KUSUR-2).
  * Suphede kalirsan (fail-closed) tasma.

CIKIS:
    0 = basarili (veya tasinacak blok/madde yok)
    2 = guvenlik dogrulamasi basarisiz, rotasyon iptal

Cikti son satiri:
    TASINAN=<n> TASINAN_MADDE=<n> DEFTER_SATIR=<n> ARSIV_SATIR=<n>
"""
import argparse
import os
import re
import sys
import tempfile


ACIK_ISARETCILER = ("🔴", "🔧", "🟠", "🟡", "ACIK", "UCUSTA", "OKAN-KAPISI",
                    "BEKLIYOR", "KOSUYOR", "OKAN'DA", "ACIK KALEMLER", "YAPILACAK")
KAPANIS_ISARETCILER = ("KAPANDI", "KAPANIS", "✅")
# Madde seviyesinde ARSIV'E isaret eden kalip; gecerse madde TASINMAZ
# (KUSUR-1 onarimi). Case-insensitive alt-dize esleme.
MADDE_VETO_DESENLERI = ("arsivde",)

# ACIK_ISARETCILER ikiye ayrilir: harf tabanli olanlar kelime-sinirli
# (`\bJETON\b`), emoji/ikon olanlar alt-dize. Bu ayrim KUSUR-2'nin
# onarimi: aksi halde "ACIK" ciplak alt-dize aranirsa "ACIKLAMA",
# "ACIKLANDI" gibi alakasiz kelimeler acik veto tetikler ve kapanmis
# blok sonsuza kadar defterde kalirdi.
_HARF_JETON_RE = re.compile(
    r"\b(?:" + "|".join(
        re.escape(j) for j in ACIK_ISARETCILER if any(c.isalpha() for c in j)
    ) + r")\b"
)
_EMOJI_JETONLAR = tuple(j for j in ACIK_ISARETCILER if not any(c.isalpha() for c in j))


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


def _acik_eslesiyor(metin):
    """ACIK jetonu varsa True (veto). Harf tabanli kelime-sinirli, emoji alt-dize."""
    if _HARF_JETON_RE.search(metin):
        return True
    for jeton in _EMOJI_JETONLAR:
        if jeton in metin:
            return True
    return False


def _madde_arsiv_vetolu(metin):
    """Madde ARSIV'E isaret ediyorsa True (veto). Case-insensitive."""
    kucuk = metin.lower()
    return any(d in kucuk for d in MADDE_VETO_DESENLERI)


def _tasinir_mi(blok):
    """Blok kesme olcutunu uygula: suphede kalirsan (fail-closed) TASIMA."""
    tum = blok["baslik"] + "\n" + "\n".join(blok["govde"])
    if _acik_eslesiyor(tum):
        return False
    for isaretci in KAPANIS_ISARETCILER:
        if isaretci in tum:
            return True
    return False


def _madde_tasinir_mi(metin):
    """Madde kesme olcutunu uygula: suphede kalirsan (fail-closed) TASIMA."""
    if _acik_eslesiyor(metin):
        return False
    if _madde_arsiv_vetolu(metin):
        return False
    for isaretci in KAPANIS_ISARETCILER:
        if isaretci in metin:
            return True
    return False


def _maddeleri_isle(govde):
    """Acik kalan bir blogun govdesindeki maddeleri isle.

    Donus: (kalan_govde_satirlari, tasinacak_madde_metinleri).
    Madde = `- ` ile baslayan satir + ondan sonraki, `- ` ile baslamayan
    girintili devam satirlari.
    """
    kalan = []
    tasinacak = []
    i = 0
    n = len(govde)
    while i < n:
        satir = govde[i]
        if satir.startswith("- "):
            madde = [satir]
            j = i + 1
            while j < n and not govde[j].startswith("- "):
                madde.append(govde[j])
                j += 1
            madde_metni = "\n".join(madde)
            if _madde_tasinir_mi(madde_metni):
                tasinacak.append(madde_metni)
            else:
                kalan.extend(madde)
            i = j
        else:
            kalan.append(satir)
            i += 1
    return kalan, tasinacak


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

    tasinacak_bloklar = []
    tasinacak_maddeler = []
    kalacak_bloklar = []

    for blok in bloklar:
        if _tasinir_mi(blok):
            tasinacak_bloklar.append(blok)
        else:
            yeni_govde, maddeler = _maddeleri_isle(blok["govde"])
            if maddeler:
                blok["govde"] = yeni_govde
                tasinacak_maddeler.extend(maddeler)
            kalacak_bloklar.append(blok)

    if not tasinacak_bloklar and not tasinacak_maddeler:
        defter_satir = _satir_sayisi(defter_metin)
        arsiv_satir = _satir_sayisi(arsiv_metin)
        print("TASINAN=0 TASINAN_MADDE=0 DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
            defter_satir, arsiv_satir))
        return 0

    tasinan_blok_parcalar = [_blok_metni(b) for b in tasinacak_bloklar]

    # Yeni defter: baslik bolgesi + kalan bloklar.
    yeni_defter_parcalar = []
    if baslik_bolgesi:
        yeni_defter_parcalar.append("\n".join(baslik_bolgesi))
    for blok in kalacak_bloklar:
        yeni_defter_parcalar.append(_blok_metni(blok))
    yeni_defter_metin = "\n\n".join(yeni_defter_parcalar)
    # Eger orijinalde son satirda newline yoksa ayni sekilde koru.
    if defter_ham and not defter_ham.endswith(b"\n"):
        yeni_defter_metin = yeni_defter_metin.rstrip("\n")

    # Yeni arsiv: ayirac + tasinan bloklar + tasinan maddeler + eski arsiv.
    ayirac = "## %s — ROTASYON: asagidaki %d blok + %d madde defterden BURAYA TASINDI" % (
        tarih, len(tasinacak_bloklar), len(tasinacak_maddeler))
    yeni_arsiv_parcalar = [ayirac]
    yeni_arsiv_parcalar.extend(tasinan_blok_parcalar)
    yeni_arsiv_parcalar.extend(tasinacak_maddeler)
    if arsiv_metin.strip():
        yeni_arsiv_parcalar.append(arsiv_metin)
    yeni_arsiv_metin = "\n\n".join(yeni_arsiv_parcalar)
    if arsiv_ham and not arsiv_ham.endswith(b"\n"):
        yeni_arsiv_metin = yeni_arsiv_metin.rstrip("\n")

    # GUVENLIK: tasinan icerik, defterdeki GERCEK azalmadir.
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
    arsiv_yeni_bayt_disk = len(arsiv_disk)

    dogru = (
        arsiv_yeni_bayt_disk - arsiv_eski_bayt >= tasinan_bayt and
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
            arsiv_eski_bayt, arsiv_yeni_bayt_disk,
            defter_eski_bayt, defter_yeni_bayt), file=sys.stderr)
        defter_satir = _satir_sayisi(defter_yedek.decode("utf-8"))
        arsiv_satir = _satir_sayisi(arsiv_yedek.decode("utf-8"))
        print("TASINAN=%d TASINAN_MADDE=%d DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
            len(tasinacak_bloklar), len(tasinacak_maddeler), defter_satir, arsiv_satir))
        return 2

    defter_satir = _satir_sayisi(yeni_defter_metin)
    arsiv_satir = _satir_sayisi(yeni_arsiv_metin)
    print("TASINAN=%d TASINAN_MADDE=%d DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
        len(tasinacak_bloklar), len(tasinacak_maddeler), defter_satir, arsiv_satir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
