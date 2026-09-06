#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIKSTUR BAYAT CAPA KAPISI — "kod bozulmadan, YALNIZ ZAMAN GECTIGI ICIN kirmizi".

NEDEN VAR (SINIF, 3. tekrar — 6 Eyl 2026, KraL-CipKapi-6Eyl):
Bugun SERIT B'de olculen 6 kirmizi adimin IKISI ayni koktendi ve kok KODDA DEGIL,
FIKSTURDEYDI:

  ① `tools/cip-supurme-test.py` — V3b "esik 2 gun: bugunku cip ELENIR".
     Fikstur blogunun tarihi `2026-09-04` diye CIVILIYDI; arac `date.today()`
     ile yas hesaplar. 6 Eyl sabahi yas 2 gunu gecti ve iddia KIRMIZI yandi.
     Kodda hicbir sey bozulmadi — TAKVIM ILERLEDI. Olculen sey kolun kendisi
     degil, bataryanin kosuldugu GUNDU.

  ② `tools/nobetci-mutasyon-test.py` bolum E — mutasyon capasi `G_IDDIA_TABANI = 11`.
     Canli deger 13 olmustu; capa TAM BIR KEZ eslesmedigi icin bolum "HARNESS BAYAT"
     basip HICBIR SEY OLCMEDEN geciyordu. Ayni capa daha once `= 8` iken de
     bayatlamisti. Yani SABIT SAYI CAPASI tanim geregi bayatlar.

Bunlar tekil yama ile UC KEZ kapatildi ve UC KEZ geri geldi; kural
[[ucuncu-tekrar-sinif-kapisi]] geregi artik SINIF kapisi vardir.

NE OLCER (iki kol, her biri UC HALLI):
  A) MUTLAK TARIH: yas/esik ekseni olcen bir batarya, fikstur govdesinde `YYYY-MM-DD`
     bicimli SABIT tarih tasiyorsa KIRMIZI. Kabul edilen bicim `bugun - N` turetimidir.
  B) SABIT SAYI CAPASI: bir mutasyon capasi `<AD> = <sayi>` dizgesini SABIT metin
     olarak tasiyorsa KIRMIZI — capa kaynaktan TURETILMELIDIR (`re` ile okunup
     govdeye yerlestirilmeli).

HALLER: TEMIZ · KIRMIZI · KAPSAM_DISI (kol o dosyada hic yok) · MUAF (kayitli istisna).

FAIL-CLOSED: dosya ayrisamazsa OLCULEMEDI ve KIRMIZI sayilir; sessizce atlanmaz.

KULLANIM:
  python3 tools/fikstur-bayat-capa-kapisi.py                # canli tools/ taramasi
  python3 tools/fikstur-bayat-capa-kapisi.py --kendini-test # sentetik kabul bataryasi
  python3 tools/fikstur-bayat-capa-kapisi.py --mutasyon     # her mutant hedef kolu oldurur
"""
import argparse
import ast
import io
import os
import re
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))

HAL_TEMIZ = "TEMIZ"
HAL_KIRMIZI = "KIRMIZI"
HAL_KAPSAM_DISI = "KAPSAM_DISI"
HAL_MUAF = "MUAF"
HAL_OLCULEMEDI = "OLCULEMEDI"

# ── KOL A: yas/esik ekseni isaretleri ───────────────────────────────────────────
# Bir dosya BU cagrilardan birini yapiyorsa "bugune gore yas" olcuyor demektir.
YAS_ISARETLERI = ("date.today", "datetime.today", "datetime.now", "utcnow",
                  "time.time")
ISO_TARIH_RE = re.compile(r"\b20\d{2}-[01]\d-[0-3]\d\b")
# `bugun - N` turetimi: bu adlardan biri geciyorsa fikstur GORELIDIR.
GORELI_ISARETLERI = ("timedelta", "_gun_once", "gun_once", "GUN_ONCE")

# ── KOL B: sabit sayi capasi ────────────────────────────────────────────────────
# `"<AD> = <sayi>"` seklinde bir DIZGE SABITI — mutasyon capasi olarak kullanildiginda
# kaynak degisince TAM BIR KEZ eslesmez ve bolum sessizce olcmez hale gelir.
SABIT_CAPA_RE = re.compile(r"^[A-Z][A-Z0-9_]{3,} = \d+$")
# Capa TURETILDIGINDE bu isaretlerden biri gecer (sayi kaynaktan OKUNUR).
TURETME_ISARETLERI = ("_capa_turet", "capa_turet", "re.findall", "re.search")

# 🔴 MUAFIYET KAYDI — ad bazli DEGIL, GEREKCE bazli. Her giris NEDEN muaf oldugunu
# yazar; gerekcesiz giris eklemek bu kapiyi kozmetiklestirir.
MUAFIYET = {
    "fikstur-bayat-capa-kapisi.py":
        "kapinin KENDISI: desenleri tanimlayan dosya (kendi deseniyle kirmizi yanamaz)",
}


def _kaynak(yol):
    with io.open(yol, encoding="utf-8") as f:
        return f.read()


def _dizge_sabitleri(agac):
    return [d.value for d in ast.walk(agac)
            if isinstance(d, ast.Constant) and isinstance(d.value, str)]


def _yas_ekseni_mi(kaynak):
    return any(i in kaynak for i in YAS_ISARETLERI)


def kol_a_mutlak_tarih(kaynak, agac):
    """(hal, gerekce) — yas ekseni olcen bataryada SABIT ISO tarih var mi."""
    if not _yas_ekseni_mi(kaynak):
        return HAL_KAPSAM_DISI, "yas/esik ekseni isareti yok"
    kirli = []
    for d in _dizge_sabitleri(agac):
        for m in ISO_TARIH_RE.findall(d):
            kirli.append(m)
    if not kirli:
        return HAL_TEMIZ, "yas ekseni var, SABIT ISO tarih yok"
    if any(i in kaynak for i in GORELI_ISARETLERI):
        # Goreli turetim VAR: sabit tarihler fikstur DISI (ornek/yorum) olabilir.
        # Ayirt edici: turetimin urettigi degerler `%(...)s` / degisken uzerinden
        # govdeye giriyorsa TEMIZ; hicbiri yoksa yine KIRMIZI.
        return HAL_TEMIZ, ("goreli turetim VAR (%s); sabit tarih %d adet ama fikstur "
                           "govdesi turetimden besleniyor"
                           % (",".join(i for i in GORELI_ISARETLERI if i in kaynak),
                              len(kirli)))
    return HAL_KIRMIZI, ("yas ekseni SABIT tarihle besleniyor (%d adet, ilk=%s) -> "
                         "kod bozulmadan takvimle KIRMIZI yanar"
                         % (len(kirli), kirli[0]))


def kol_b_sabit_capa(kaynak, agac):
    """(hal, gerekce) — mutasyon capasi SABIT SAYI dizgesi mi (turetilmemis mi)."""
    if "mutasyon" not in kaynak.lower() and "MUTANT" not in kaynak:
        return HAL_KAPSAM_DISI, "mutasyon capasi tasimiyor"
    sabitler = [d.strip() for d in _dizge_sabitleri(agac)
                if SABIT_CAPA_RE.match(d.strip())]
    if not sabitler:
        return HAL_TEMIZ, "sabit sayi capasi yok"
    if any(i in kaynak for i in TURETME_ISARETLERI):
        return HAL_TEMIZ, ("capa TURETILIYOR (%s); sabit dizge %d adet ama kaynak "
                           "okunuyor"
                           % (",".join(i for i in TURETME_ISARETLERI if i in kaynak),
                              len(sabitler)))
    return HAL_KIRMIZI, ("mutasyon capasi SABIT SAYI dizgesi (%d adet, ilk=%r) -> "
                         "kaynak degisince TAM BIR KEZ eslesmez, bolum sessizce OLCMEZ"
                         % (len(sabitler), sabitler[0]))


def sinifla(yol):
    """(hal, gerekce) — dosyanin BIRLESIK hukmu (kirmizi bir kol yeterlidir)."""
    ad = os.path.basename(yol)
    if ad in MUAFIYET:
        return HAL_MUAF, MUAFIYET[ad]
    try:
        kaynak = _kaynak(yol)
        agac = ast.parse(kaynak, filename=yol)
    except (OSError, SyntaxError, UnicodeError) as exc:
        return HAL_OLCULEMEDI, "kaynak ayrisamadi: %s" % exc
    a_hal, a_ger = kol_a_mutlak_tarih(kaynak, agac)
    b_hal, b_ger = kol_b_sabit_capa(kaynak, agac)
    if a_hal == HAL_KIRMIZI:
        return HAL_KIRMIZI, "KOL_A " + a_ger
    if b_hal == HAL_KIRMIZI:
        return HAL_KIRMIZI, "KOL_B " + b_ger
    if a_hal == HAL_KAPSAM_DISI and b_hal == HAL_KAPSAM_DISI:
        return HAL_KAPSAM_DISI, "iki kol da kapsam disi"
    return HAL_TEMIZ, "KOL_A=%s · KOL_B=%s" % (a_hal, b_hal)


def tara(tools=TOOLS):
    sonuc = []
    for ad in sorted(os.listdir(tools)):
        if ad.endswith(".py"):
            hal, ger = sinifla(os.path.join(tools, ad))
            sonuc.append((ad, hal, ger))
    return sonuc


# ─────────────────────────────────────────────────────── kabul bataryasi (sentetik)

VAKALAR = (
    # (ad, govde, beklenen_hal)
    ("a_mutlak_tarih.py",
     'import datetime as dt\n'
     'BLOK = "## 2026-09-04 — acilis\\n"\n'
     'def yas():\n    return dt.date.today()\n',
     HAL_KIRMIZI),
    ("b_goreli_tarih.py",
     'import datetime as dt\n'
     'def _gun_once(n):\n    return (dt.date.today() - dt.timedelta(days=n)).isoformat()\n'
     'BLOK = "## %s — acilis\\n" % _gun_once(7)\n',
     HAL_TEMIZ),
    ("c_yas_ekseni_yok.py",
     'BLOK = "## 2026-09-04 — sadece bir belge ornegi\\n"\n',
     HAL_KAPSAM_DISI),
    ("d_sabit_capa.py",
     'MUTANT_CAPA = "G_IDDIA_TABANI = 11"\n'
     'def mutasyon():\n    return MUTANT_CAPA\n',
     HAL_KIRMIZI),
    ("e_turetilmis_capa.py",
     'import re\n'
     'def mutasyon(kaynak):\n'
     '    n = int(re.findall(r"^G_IDDIA_TABANI = (\\d+)$", kaynak)[0])\n'
     '    return "G_IDDIA_TABANI = %d" % n\n',
     HAL_TEMIZ),
    ("f_bozuk.py", "def (:\n", HAL_OLCULEMEDI),
)


def kendini_test():
    gecici = tempfile.mkdtemp(prefix="bayat-capa-kabul-")
    iddia = 0
    kirmizi = []
    try:
        for ad, govde, beklenen in VAKALAR:
            yol = os.path.join(gecici, ad)
            with io.open(yol, "w", encoding="utf-8") as f:
                f.write(govde)
            hal, ger = sinifla(yol)
            iddia += 1
            ok = hal == beklenen
            if not ok:
                kirmizi.append(ad)
            print("%s %s beklenen=%s olculen=%s (%s)"
                  % ("OK" if ok else "KIRMIZI", ad, beklenen, hal, ger[:90]))
        # MUAFIYET kolu: kapinin KENDISI muaf sayilir (kendi deseniyle yanmaz)
        iddia += 1
        hal, _g = sinifla(os.path.join(TOOLS, "fikstur-bayat-capa-kapisi.py"))
        if hal != HAL_MUAF:
            kirmizi.append("muafiyet")
        print("%s muafiyet: kapinin KENDISI MUAF (olculen=%s)"
              % ("OK" if hal == HAL_MUAF else "KIRMIZI", hal))
    finally:
        # 🔴 SILME MENZILI: yalnizca bu turun kendi actigi gecici dizin.
        shutil.rmtree(gecici, ignore_errors=True)
    print("SONUC: %s — iddia %d" % ("YESIL" if not kirmizi else "KIRMIZI", iddia))
    return 1 if kirmizi else 0


# ──────────────────────────────────────────────────────────────── mutasyon turu

MUTANTLAR = (
    ("M1 KOL_A yargisi oldurulur (mutlak tarih artik kirmizi yanmaz)",
     '    return HAL_KIRMIZI, ("yas ekseni ' + 'SABIT tarihle besleniyor',
     '    return HAL_TEMIZ, ("MUTANT yas ekseni ' + 'SABIT tarihle besleniyor',
     "a_mutlak_tarih.py"),
    ("M2 KOL_B yargisi oldurulur (sabit capa artik kirmizi yanmaz)",
     '    return HAL_KIRMIZI, ("mutasyon capasi ' + 'SABIT SAYI dizgesi',
     '    return HAL_TEMIZ, ("MUTANT mutasyon capasi ' + 'SABIT SAYI dizgesi',
     "d_sabit_capa.py"),
    ("M3 ISO tarih deseni oldurulur (hicbir tarih gorulmez)",
     'ISO_TARIH_RE = re.compile(r"\\b20\\d{2}-[01]\\d-[0-3]\\d\\b")',
     'ISO_TARIH_RE = re.compile(r"(?!x)x")  # MUTANT: desen OLU',
     "a_mutlak_tarih.py"),
    ("M4 GORELI muafiyeti genisletilir (her dosya 'goreli' sayilir)",
     '    if any(i in kaynak for i in ' + 'GORELI_ISARETLERI):',
     '    if True:  # MUTANT goreli muafiyeti HERKESE acildi',
     "a_mutlak_tarih.py"),
)

KONTROL_MUTANTI = ("K1 KONTROL [DAVRANIS DISI]: yalnizca dokumantasyon dizgesi degisir",
                   'NEDEN VAR (SINIF, ' + '3. tekrar',
                   'NEDEN VAR (KONTROL MUTANTI, ' + '3. tekrar')


_MUTANT_SAYACI = [0]


def _mutant_hukmu(mutant_kaynak, gecici, vaka_ad):
    """Mutant kopyayi IZOLE yukle ve verilen sentetik vakayi siniflandir.

    🔴 HER MUTANT KENDI DOSYA ADINA YAZILIR (olculen tuzak, 6 Eyl 2026): mutantlar
    ayni ada (`mutant-kapi.py`) yazilinca CPython'un bytecode onbellegi devreye girdi —
    iki mutant AYNI SANIYEDE ve AYNI BOYUTTA uretildigi icin `__pycache__` gecerli
    sayildi ve IKINCI mutant BIRINCININ BYTECODE'UNU kostu. Gozlenen: M2 "KACTI"
    (mutant hedefe HIC ULASMADI) ama tek basina kosunca OLUYORDU. Bu, harness'in
    kendisini yalanlayan bir sinif: [[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]].
    Iki kat emniyet: benzersiz ad + `dont_write_bytecode`.
    """
    import importlib.util
    _MUTANT_SAYACI[0] += 1
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    mut_yol = os.path.join(gecici, "mutant-kapi-%d.py" % _MUTANT_SAYACI[0])
    with io.open(mut_yol, "w", encoding="utf-8") as f:
        f.write(mutant_kaynak)
    spec = importlib.util.spec_from_file_location(
        "bayat_capa_mutant_%d" % _MUTANT_SAYACI[0], mut_yol)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = onceki
    govde = dict((a, g) for a, g, _b in VAKALAR)[vaka_ad]
    vaka_yol = os.path.join(gecici, vaka_ad)
    with io.open(vaka_yol, "w", encoding="utf-8") as f:
        f.write(govde)
    return mod.sinifla(vaka_yol)[0]


def mutasyon():
    kaynak = _kaynak(os.path.join(TOOLS, "fikstur-bayat-capa-kapisi.py"))
    oldu = 0
    kirmizi = []
    gecici = tempfile.mkdtemp(prefix="bayat-capa-mutant-")
    try:
        # TABAN: mutasyonsuz kopya, hedef vakalari DOGRU siniflandirmali.
        for ad, _g, beklenen in VAKALAR:
            if beklenen != HAL_KIRMIZI:
                continue
            taban = _mutant_hukmu(kaynak, gecici, ad)
            if taban != HAL_KIRMIZI:
                print("!! TABAN BOZUK (%s -> %s) — mutasyon turu ANLAMSIZ" % (ad, taban))
                return 2
        print("TABAN: mutasyonsuz kopya hedef vakalari KIRMIZI okuyor ✅")

        for etiket, eski, yeni, vaka_ad in MUTANTLAR:
            if kaynak.count(eski) != 1:
                print("  [OLCULEMEDI] %s — capa %d kez eslesti"
                      % (etiket, kaynak.count(eski)))
                kirmizi.append(etiket)
                continue
            hal = _mutant_hukmu(kaynak.replace(eski, yeni, 1), gecici, vaka_ad)
            olduruldu = hal != HAL_KIRMIZI
            oldu += 1 if olduruldu else 0
            if not olduruldu:
                kirmizi.append(etiket)
            print("  [%s] %s -> hedef vaka `%s` hukmu=%s (beklenen: KIRMIZI DEGIL)"
                  % ("OLDU" if olduruldu else "KACTI", etiket, vaka_ad, hal))

        etiket, eski, yeni = KONTROL_MUTANTI
        if kaynak.count(eski) != 1:
            print("  [OLCULEMEDI] %s — capa %d kez" % (etiket, kaynak.count(eski)))
            kirmizi.append(etiket)
        else:
            hal = _mutant_hukmu(kaynak.replace(eski, yeni, 1), gecici,
                                "a_mutlak_tarih.py")
            ok = hal == HAL_KIRMIZI
            if not ok:
                kirmizi.append(etiket)
            print("  [%s] %s -> hukum=%s (beklenen: KIRMIZI, davranis DEGISMEMELI)"
                  % ("OK" if ok else "KIRMIZI", etiket, hal))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    print("MUTANT=%d/%d KONTROL=%s"
          % (oldu, len(MUTANTLAR), "YESIL" if not kirmizi else "KIRMIZI"))
    return 1 if kirmizi else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--mutasyon", action="store_true")
    ap.add_argument("--tools", default=TOOLS)
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    if a.mutasyon:
        return mutasyon()

    kirli = []
    olculemedi = []
    for ad, hal, ger in tara(a.tools):
        if hal == HAL_KIRMIZI:
            kirli.append((ad, ger))
            print("KIRMIZI %s — %s" % (ad, ger))
        elif hal == HAL_OLCULEMEDI:
            olculemedi.append((ad, ger))
            print("OLCULEMEDI %s — %s" % (ad, ger))
    if kirli or olculemedi:
        print("SONUC: KIRMIZI — %d bayat capa, %d olculemedi"
              % (len(kirli), len(olculemedi)))
        return 1
    print("SONUC: YESIL — fikstur capalari goreli/turetilmis")
    return 0


if __name__ == "__main__":
    sys.exit(main())
