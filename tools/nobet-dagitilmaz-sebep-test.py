#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/nobet-dagitilmaz-sebep-test.py — O4B: [DAGITILMAZ] satirinda SEBEP= alani.

Uretim kodu ~/.claude/cron/nobet-kapi.py'den ithal edilir; test pruvo repo icinde
tutulur ki CI/nobetci gorsun. Negatif kontrol + 3 oldurucu mutant + 1 kontrol
mutanti icerir."""

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

URETIM_YOLU = "/Users/okan/.claude/cron/nobet-kapi.py"


def uretim_modulu(yol=URETIM_YOLU):
    """nobet-kapi.py modulunu yukler; basarisizsa acik hata verir."""
    if not os.path.exists(yol):
        raise AssertionError("URETIM_YOLU YOK: %s" % yol)
    spec = importlib.util.spec_from_file_location("nobet_kapi_o4b", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(yol))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


def _defter_satiri(kimlik, kime, is_metni):
    return "| %s | 2026-08-24 | Tamirci→%s | %s | 🔧 | — |" % (
        kimlik, kime, is_metni)


def _rapor_uret(modul):
    """Kuru tur kapatir; K701 Okan, K702 MIMAR (kapi jetonu)."""
    kok = tempfile.mkdtemp(prefix="o4b-sebep-")
    try:
        eski = {}
        for ad in ("DEFTER_YOLU", "GERI_IZ_YOLU", "RAPOR_DIZINI",
                   "SPEC_DIZINI", "KILIT_YOLU", "ONARIMSIZ_SAYAC_YOLU",
                   "ATLANAN_SAYAC_YOLU", "KARANTINA_YOLU"):
            eski[ad] = getattr(modul, ad)
        modul.DEFTER_YOLU = os.path.join(kok, "acik-kalemler.md")
        modul.GERI_IZ_YOLU = os.path.join(kok, "geri-iz.json")
        modul.RAPOR_DIZINI = os.path.join(kok, "raporlar")
        modul.SPEC_DIZINI = os.path.join(kok, "specler")
        modul.KILIT_YOLU = os.path.join(kok, "tur.kilit")
        modul.ONARIMSIZ_SAYAC_YOLU = os.path.join(kok, "onarimsiz-sayac.json")
        modul.ATLANAN_SAYAC_YOLU = os.path.join(kok, "atlanan-sayac.json")
        modul.KARANTINA_YOLU = os.path.join(kok, "motor-karantina")
        os.makedirs(modul.RAPOR_DIZINI)
        os.makedirs(modul.SPEC_DIZINI)
        defter = "\n".join([
            "# o4b fikstur defteri",
            "",
            "| id | tarih | kimden→kime | iş (tek cümle) | durum | kanıt |",
            "|---|---|---|---|---|---|",
            _defter_satiri("K701", "Okan", "bakim isi"),
            _defter_satiri("K702", "Tamirci", "yeni kapi tasarimi"),
            "",
        ])
        with open(modul.DEFTER_YOLU, "w", encoding="utf-8") as dosya:
            dosya.write(defter)
        modul.geri_iz_yaz({"tur_no": 0, "kalemler": {}}, modul.GERI_IZ_YOLU)
        sonuc = modul.tur_kapat(kuru=True)
        return sonuc["rapor"]
    finally:
        for ad, deger in eski.items():
            setattr(modul, ad, deger)
        shutil.rmtree(kok, ignore_errors=True)


def sebep_kontrol(rapor):
    """Assertion patlar ise negatif kontrol duser."""
    dagitilmaz = [l for l in rapor.splitlines() if "[DAGITILMAZ]" in l]
    assert len(dagitilmaz) == 2, "beklenen 2 DAGITILMAZ satir, bulunan %d" % len(
        dagitilmaz)
    for l in dagitilmaz:
        assert "SEBEP=" in l, "SEBEP= alani yok: %s" % l
        deger = l.split("SEBEP=", 1)[1].strip()
        assert deger, "SEBEP= alani bos: %s" % l
    assert "KALEM K701 -> OKAN [DAGITILMAZ] SEBEP=OKAN_KAPISI" in rapor
    assert "KALEM K702 -> MIMAR [DAGITILMAZ] SEBEP=MIMAR_KATI_GERCEK" in rapor
    return True


# --- MUTANTLAR --------------------------------------------------------------

def m_sebep_kaldir(s):
    """[DAGITILMAZ] satirlarindan SEBEP= alani tamamen kaldirilir."""
    return s.replace(
        '    for kalem in plan["mimar"]:\n'
        '        satirlar.append("KALEM %s -> MIMAR [DAGITILMAZ] SEBEP=%s" % (\n'
        '            kalem["id"], kova_sec(kalem, geri_iz)))\n'
        '    for kalem in plan["okan"]:\n'
        '        satirlar.append("KALEM %s -> OKAN [DAGITILMAZ] SEBEP=%s" % (\n'
        '            kalem["id"], kova_sec(kalem, geri_iz)))',
        '    for kalem in plan["mimar"]:\n'
        '        satirlar.append("KALEM %s -> MIMAR [DAGITILMAZ]" % kalem["id"])\n'
        '    for kalem in plan["okan"]:\n'
        '        satirlar.append("KALEM %s -> OKAN [DAGITILMAZ]" % kalem["id"])')


def m_sebep_sabit(s):
    """SEBEP her kalem icin ayni sabit dizeye baglanir (turetilmez)."""
    return s.replace(
        '    for kalem in plan["mimar"]:\n'
        '        satirlar.append("KALEM %s -> MIMAR [DAGITILMAZ] SEBEP=%s" % (\n'
        '            kalem["id"], kova_sec(kalem, geri_iz)))\n'
        '    for kalem in plan["okan"]:\n'
        '        satirlar.append("KALEM %s -> OKAN [DAGITILMAZ] SEBEP=%s" % (\n'
        '            kalem["id"], kova_sec(kalem, geri_iz)))',
        '    for kalem in plan["mimar"]:\n'
        '        satirlar.append("KALEM %s -> MIMAR [DAGITILMAZ] SEBEP=MIMAR_KATI_GERCEK" % kalem["id"])\n'
        '    for kalem in plan["okan"]:\n'
        '        satirlar.append("KALEM %s -> OKAN [DAGITILMAZ] SEBEP=MIMAR_KATI_GERCEK" % kalem["id"])')


def m_ikinci_basim_sebepsiz(s):
    return s.replace(
        '    for kalem in plan["okan"]:\n'
        '        satirlar.append("KALEM %s -> OKAN [DAGITILMAZ] SEBEP=%s" % (\n'
        '            kalem["id"], kova_sec(kalem, geri_iz)))',
        '    for kalem in plan["okan"]:\n'
        '        satirlar.append("KALEM %s -> OKAN [DAGITILMAZ]" % kalem["id"])')


def m_kontrol_baslik(s):
    return s.replace('"=== %s NOBET ONARIM BACAGI tur=%d%s ==="',
                     '"=== %s NOBET ONARIM BACAGI_KONTROL tur=%d%s ==="', 1)


OLDURUCU = [
    ("SEBEP_KALDIR", m_sebep_kaldir),
    ("SEBEP_SABIT", m_sebep_sabit),
    ("IKINCI_BASIM_SEBEPSIZ", m_ikinci_basim_sebepsiz),
]

KONTROL = [
    ("BASLIK_DEGISMEZ", m_kontrol_baslik),
]


def _sha(yol):
    with open(yol, "rb") as dosya:
        return hashlib.sha256(dosya.read()).hexdigest()


def mutant_kos(ad, fn, kaynak, canli_modul):
    """Bir mutant kopyasinda sebep kontrolunu calistirir.

    Donus: (olduruldu, uygulandi, not)
    """
    mutant_metni = fn(kaynak)
    if mutant_metni == kaynak:
        return False, False, "UYGULANMADI"
    kok = tempfile.mkdtemp(prefix="o4b-mutant-")
    try:
        yol = os.path.join(kok, "nobet-kapi.py")
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(mutant_metni)
        # bagimli modulleri de kopyala
        for ad_f in ("kilit.py", "nobet_merdiven.py"):
            kaynak_f = os.path.join(os.path.dirname(URETIM_YOLU), ad_f)
            if os.path.exists(kaynak_f):
                shutil.copy(kaynak_f, kok)
        mod = uretim_modulu(yol)
        rapor = _rapor_uret(mod)
        try:
            sebep_kontrol(rapor)
        except AssertionError:
            return True, True, "KIRMIZI"
        return False, True, "YESIL (HAYATTA KALDI)"
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def main():
    if not os.path.exists(URETIM_YOLU):
        print("O4B= URETIM_YOLU_YOK rc=2")
        return 2
    sha_bas = _sha(URETIM_YOLU)
    modul = uretim_modulu()
    rapor = _rapor_uret(modul)
    try:
        sebep_kontrol(rapor)
        negatif = "GECTI"
    except AssertionError as hata:
        print("O4B= NEGATIF_KONTROL_DUSTU hata=%s rc=1" % hata)
        return 1

    kaynak = open(URETIM_YOLU, encoding="utf-8").read()
    oldurulen = 0
    uygulanan = 0
    kusur = []
    for ad, fn in OLDURUCU:
        oldur, uygul, not_ = mutant_kos(ad, fn, kaynak, modul)
        uygulanan += 1
        if oldur:
            oldurulen += 1
        print("MUTANT %-30s %s" % (ad, not_))
        if not oldur:
            kusur.append(ad)

    kontrol_ok = True
    for ad, fn in KONTROL:
        _, uygul, not_ = mutant_kos(ad, fn, kaynak, modul)
        if not uygul or "KIRMIZI" in not_:
            kontrol_ok = False
            kusur.append("KONTROL:" + ad)
        print("KONTROL %-29s %s" % (ad, not_))

    sha_son = _sha(URETIM_YOLU)
    kanonik_ok = (sha_bas == sha_son)
    rc = 0 if (oldurulen == uygulanan and kontrol_ok and kanonik_ok) else 1
    print("O4B= SEBEP_DOLU=2/2 NEGATIF_KONTROL=%s MUTANT=%d/%d KONTROL=%s "
          "KANONIK_SHA=%s rc=%d" % (
              negatif, oldurulen, uygulanan,
              "YESIL" if kontrol_ok else "BOZUK",
              "ESIT" if kanonik_ok else "DEGISTI", rc))
    if kusur:
        for k in kusur:
            print("KUSUR: " + k)
    return rc


if __name__ == "__main__":
    sys.exit(main())
