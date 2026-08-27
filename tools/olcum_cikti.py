#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OLCUM CIKTI KOKU (K314②, 27 Agu 2026) — olcum araclarinin YAZDIGI YER CIVILIDIR.

═══════════════════════════════════════════════════════════════════════════════
OLCULEN ARIZA
═══════════════════════════════════════════════════════════════════════════════
26 Agu 2026: `tools/k309d2-kos.py` ve `tools/k309d2-olcum.py` raporlarini
`os.path.join(os.path.dirname(__file__), "...-rapor.txt")` ile YANIBASLARINA —
yani IZLENEN AGACA — yaziyordu. Iki dosya `k309-d2` merge'iyle main'e girdi:

    tools/k309d2-kosum-rapor.txt
    tools/k309d2-olcum-rapor.txt

Ikisi de saf IC KOSUM RAPORU idi ve PUBLIC depoda mimarin olcum duzlemini +
worktree yollarini duz metin tasiyordu. `kisisel-veri-test.py` KURAL A
(izlenen dosya adi ic-rapor ailesine uymayacak) KIRMIZI yandi ve YAYIN DURDU.

🔴 IKI DOSYAYI SILMEK KALEMI KAPATMAZ. Silme, VAKAYI temizler; MEKANIZMAYI
degil. Araclarin bir sonraki kosumu AYNI YERE yeniden yazar ve ariza BIREBIR
geri gelir ([[ucuncu-tekrar-sinif-kapisi]], [[tekil-yama-sinifi-kapatmaz]]).

═══════════════════════════════════════════════════════════════════════════════
🔴 KURAL — ARAC KENDI YOLUNU SECEMEZ
═══════════════════════════════════════════════════════════════════════════════
Olcum ciktisinin koku BU MODULDE SABITTIR ve izlenen agacin DISINDADIR. Cagiran
yalnizca DOSYA ADI verir; dizin veremez.

    from olcum_cikti import olcum_yolu
    rapor = olcum_yolu("k309d2-kosum-rapor.txt")

FAIL-CLOSED KOLLAR (hepsi `OlcumYoluReddi` firlatir — sessiz duzeltme YOK):
  1. Ad icinde yol ayraci (`/`, `\\`) ya da `..` varsa RED. "Alt dizin" istegi
     yolun ele gecirilmesidir; alt dizin `alt=` argumaniyla ve AYNI denetimle
     alinir.
  2. Cozulen yol depo agacinin ICINE duserse RED — kok degiskeni bir sekilde
     depoya cevrilmis demektir.
  3. `PRUVO_OLCUM_KOKU` ile kok DEGISTIRILEBILIR (fikstur/CI izolasyonu icin)
     ama ayni (2) denetimi ona da uygulanir: depo icini gosteren bir override
     KABUL EDILMEZ. Yani override bir BYPASS DEGILDIR.

NEDEN `tempfile.gettempdir()` ALTI (ve neden repoda bir `.gitignore` deseni
DEGIL): CLAUDE.md "makinede iz birakma" kurali olcum ciktisini GECICI sinifa
koyar; `.gitignore` deseni kovalamak ise 27 Tem'de UC KEZ kacan bir yoldur
([[kisisel-veri-test.py KURAL A gerekcesi]]) — dosya izlenmese bile depo
agacinda durur ve bir sonraki `git add -A` onu geri getirebilir. Kok, agacin
DISINDA olunca bu sinif tumden kapanir.

🔴 IKI EKSEN AYRIDIR: bu modul dosyanin NEREYE yazildigini civiler;
`kisisel-veri-test.py` KURAL A izlenen dosyanin ADINI olcer. Biri otekini
KANITLAMAZ ve biri otekinin yerine gecmez — ikisi de durur.
"""
import os
import tempfile

# Depo koku (bu dosya tools/ altindadir).
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🔴 SABIT KOK. Cagiran bunu ARGUMANLA degistiremez.
VARSAYILAN_KOK = os.path.join(tempfile.gettempdir(), "pruvo-olcum")
KOK_ENV = "PRUVO_OLCUM_KOKU"


class OlcumYoluReddi(ValueError):
    """Istenen olcum ciktisi yolu KABUL EDILMEDI (fail-closed)."""


def _depo_ici_mi(yol):
    """`yol` depo agacinin ICINDE mi? (symlink/`..` numaralarina karsi realpath)"""
    hedef = os.path.realpath(yol)
    depo = os.path.realpath(_REPO)
    return hedef == depo or hedef.startswith(depo + os.sep)


def olcum_koku():
    """Olcum ciktisinin SABIT koku. Depo icini gosteren her deger REDDEDILIR."""
    ham = os.environ.get(KOK_ENV, "").strip() or VARSAYILAN_KOK
    kok = os.path.abspath(os.path.expanduser(ham))
    if _depo_ici_mi(kok):
        raise OlcumYoluReddi(
            "olcum kok dizini DEPO AGACININ ICINE dustu (%s). Olcum ciktisi izlenen "
            "agaca YAZILAMAZ — 26 Agu 2026'da tam bu yol yayini 4,7 saat durdurdu. "
            "%s degiskenini depo disindaki bir dizine ayarla ya da hic ayarlama."
            % (kok, KOK_ENV))
    return kok


def _ad_dogrula(ad, etiket):
    if not isinstance(ad, str) or not ad.strip():
        raise OlcumYoluReddi("%s BOS olamaz" % etiket)
    ad = ad.strip()
    if os.path.isabs(ad):
        raise OlcumYoluReddi("%s MUTLAK yol olamaz (%r) — kok bu modulde sabittir"
                             % (etiket, ad))
    if "/" in ad or "\\" in ad or os.sep in ad:
        raise OlcumYoluReddi("%s yol ayraci tasiyamaz (%r) — alt dizin icin `alt=` kullan"
                             % (etiket, ad))
    if ad in (".", "..") or ad.startswith(".."):
        raise OlcumYoluReddi("%s `..` ile yukari cikamaz (%r)" % (etiket, ad))
    return ad


def olcum_dizini(alt=None):
    """Olcum kokunu (ve istege bagli TEK seviyelik alt dizini) hazirlar, doner."""
    kok = olcum_koku()
    if alt is not None:
        kok = os.path.join(kok, _ad_dogrula(alt, "alt dizin adi"))
    if _depo_ici_mi(kok):  # ikinci okuma — `alt` ile kacis denemesine karsi
        raise OlcumYoluReddi("cozulen olcum dizini depo agacinin ICINDE (%s)" % kok)
    os.makedirs(kok, exist_ok=True)
    return kok


def olcum_yolu(ad, alt=None):
    """Olcum ciktisi icin CIVILI tam yol. Cagiran YALNIZ dosya adi verir."""
    dizin = olcum_dizini(alt=alt)
    yol = os.path.join(dizin, _ad_dogrula(ad, "dosya adi"))
    if _depo_ici_mi(yol):  # ucuncu okuma (fail-closed, ucuz)
        raise OlcumYoluReddi("cozulen olcum yolu depo agacinin ICINDE (%s)" % yol)
    return yol
