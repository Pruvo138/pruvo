#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sabah spec'i AÇIK KALEM sayımı — `kral-sabah.py::acik_kalemleri_topla`.

5 Kas 2026 (KraL): sabah bloğu canlı defterdeki 5 açık kalemin 1'ini gösteriyordu.
İki kör nokta ölçüldü:
  (a) kimlik kalıbı `^K\\d+…` FİLTRE olarak kullanılıyordu → `D1-YOGUNLUK-04KAS`
      gibi K-öneksiz kimlikler hiç sayılmıyordu;
  (b) durum "son 2 hücre"den okunuyordu → 7 hücreli satırda (K442: `kabul:` ayrı
      hücre) durum `kabul:` hücresinden okunup kalem düşüyordu.
Düzeltme: konum sözleşmesi TEK PARSER ile aynı (`parti-borc-kapisi.py::
acik_kalem_listesi`: durum=F4), durum kümesi oradan (`ACIK_DURUMLAR`).

  V1 K-öneksiz kimlik ACIK                 -> sayılır
  V2 7 hücreli satır, durum F4=ACIK        -> sayılır, kimlik doğru
  V3 KAPANDI / başlık / ayraç              -> sayılmaz
  V4 iş hücresinde `\\|` kaçışı             -> kolon kaymaz, sayılır
  V5 UCUSTA / OKAN-KAPISI / 🔧             -> sayılır (tek parser kümesi)
  V6 bölücü yüklenemez                     -> RuntimeError (fail-loud)
  V7 tek parser EŞİTLİĞİ (fikstür)         -> kimlik kümesi == acik_kalem_listesi
  V8 tek parser EŞİTLİĞİ (canlı defter)    -> yalnız dosya varsa; yoksa ATLANDI
  M1 MUTANT durum = parts[-2] (eski kural) -> V2 KIRMIZI
  M2 MUTANT K-kalıbı filtresi geri         -> V1 KIRMIZI
  (her mutantta kontrol V3 YEŞİL kalır — hedef-kol atfı)

Ağ YOK, disk yazımı yalnız tempfile. rc=0 tümü yeşil · rc=1 kırmızı var.
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
ARAC = KOK / "tools" / "sabah-teslim" / "kral-sabah.py"
TEK_PARSER = KOK / "tools" / "parti-borc-kapisi.py"
CANLI_DEFTER = Path(os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md"))

BASLIK = ("| id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |\n"
          "|---|---|---|---|---|---|\n")

FIKSTUR = BASLIK + (
    "| K100 | 1 Kas | A→B | eski iş | KAPANDI | sha abc |\n"
    "| D1-YOGUNLUK-04KAS | 4 Kas | Tamirci→KraL | D1 yoğun | ACIK | - |\n"
    "| K442 | 2026-10-23 | BaBa → KraL | iki eşik dikişi | ACIK | kabul: fark 0 | **ÖLÇÜM** 27 Eki |\n"
    "| K443 | 1 Kas | A→B | boru \\| içeren iş | ACIK | - |\n"
    "| K444 | 1 Kas | A→B | uçuşta | UCUSTA | - |\n"
    "| K445 | 1 Kas | A→B | okan | OKAN-KAPISI | - |\n"
    "| K446 | 1 Kas | A→B | onarım | 🔧 | - |\n"
    "| SEGWAY-K1-KIRMIZI-26EKI | 26 Eki | A→B | kapalı | KAPANDI | sha |\n"
)
BEKLENEN = {"D1-YOGUNLUK-04KAS", "K442", "K443", "K444", "K445", "K446"}

MUTANTLAR = {
    "M1": ("        durum = parts[4]\n",
           "        durum = parts[-2]  # MUTANT\n", "V2"),
    "M2": ("        if not kid or durum not in acik_durumlar:\n",
           "        if not kid or not kid.startswith('K') or not kid[1:2].isdigit() "
           "or durum not in acik_durumlar:  # MUTANT\n", "V1"),
}


def modul_yukle(yol, ad, kaynak=None):
    if kaynak is None:
        s = importlib.util.spec_from_file_location(ad, yol)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        return m
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / (ad + ".py")
        p.write_text(kaynak, encoding="utf-8")
        s = importlib.util.spec_from_file_location(ad, p)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        return m


def hazirla(mod):
    """Bölücüyü BU ağacın tek parser'ından al (canlı yol sabit `/Users/okan/...`)."""
    mod.REPO = KOK
    mod._BOLUCU_ONBELLEK.clear()
    return mod


def kimlikler(mod, metin):
    kalemler, n = mod.acik_kalemleri_topla(metin)
    return {k["id"] for k in kalemler}, kalemler, n


def tek_parser_kimlikleri(tp, metin):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "acik-kalemler.md"
        p.write_text(metin, encoding="utf-8")
        kalemler, ok, hata = tp.acik_kalem_listesi(str(p))
    return {k["kimlik"] for k in kalemler}, ok, hata


def vakalar(mod, tp):
    """Doner: {vaka: (gecti_mi, detay)}"""
    out = {}
    ids, kalemler, n = kimlikler(mod, FIKSTUR)

    out["V1"] = ("D1-YOGUNLUK-04KAS" in ids, "ids=%s" % sorted(ids))
    k442 = [k for k in kalemler if k["id"] == "K442"]
    out["V2"] = (len(k442) == 1 and k442[0]["durum"] == "ACIK"
                 and k442[0]["is"] == "iki eşik dikişi",
                 "k442=%s" % k442)
    out["V3"] = (not ({"K100", "SEGWAY-K1-KIRMIZI-26EKI", "id", "---"} & ids),
                 "ids=%s" % sorted(ids))
    k443 = [k for k in kalemler if k["id"] == "K443"]
    out["V4"] = (len(k443) == 1 and k443[0]["durum"] == "ACIK"
                 and k443[0]["is"] == "boru | içeren iş", "k443=%s" % k443)
    out["V5"] = ({"K444", "K445", "K446"} <= ids, "ids=%s" % sorted(ids))

    # V6 fail-loud: bölücü yüklenemez
    eski_repo = mod.REPO
    mod.REPO = Path("/yok/boyle/bir/depo")
    mod._BOLUCU_ONBELLEK.clear()
    try:
        mod.acik_kalemleri_topla(FIKSTUR)
        out["V6"] = (False, "RuntimeError YOK")
    except RuntimeError as e:
        out["V6"] = (True, "RuntimeError: %s" % str(e)[:60])
    finally:
        mod.REPO = eski_repo
        mod._BOLUCU_ONBELLEK.clear()

    tp_ids, ok, hata = tek_parser_kimlikleri(tp, FIKSTUR)
    out["V7"] = (ok and ids == tp_ids == BEKLENEN and n == len(BEKLENEN),
                 "arac=%s tek_parser=%s ok=%s hata=%s" % (sorted(ids), sorted(tp_ids), ok, hata))
    return out


def v8_canli(mod, tp):
    if not CANLI_DEFTER.is_file():
        return None, "ATLANDI (canlı defter yok: CI)"
    metin = CANLI_DEFTER.read_text(encoding="utf-8")
    ids, _, n = kimlikler(mod, metin)
    tp_kalemler, ok, hata = tp.acik_kalem_listesi(str(CANLI_DEFTER))
    tp_ids = {k["kimlik"] for k in tp_kalemler}
    return (ok and ids == tp_ids,
            "arac=%d tek_parser=%d fark_arac=%s fark_tp=%s ok=%s hata=%s ids=%s" % (
                n, len(tp_ids), sorted(ids - tp_ids), sorted(tp_ids - ids), ok, hata,
                sorted(ids)))


def main():
    kirmizi = 0
    tp = modul_yukle(TEK_PARSER, "pruvo_tek_parser_sayim_test")
    mod = hazirla(modul_yukle(ARAC, "pruvo_kral_sabah_sayim_test"))

    for ad, (gecti, detay) in vakalar(mod, tp).items():
        print("%s %s — %s" % ("YESIL" if gecti else "KIRMIZI", ad, detay))
        kirmizi += 0 if gecti else 1

    gecti, detay = v8_canli(mod, tp)
    if gecti is None:
        print("ATLANDI V8 — %s" % detay)
    else:
        print("%s V8 — %s" % ("YESIL" if gecti else "KIRMIZI", detay))
        kirmizi += 0 if gecti else 1

    kaynak = ARAC.read_text(encoding="utf-8")
    for mad, (eski, yeni, hedef) in MUTANTLAR.items():
        if kaynak.count(eski) != 1:
            print("KIRMIZI %s — mutant çapası %d kez bulundu (1 olmalı)" % (mad, kaynak.count(eski)))
            kirmizi += 1
            continue
        mm = hazirla(modul_yukle(None, "pruvo_kral_sabah_%s" % mad.lower(),
                                 kaynak.replace(eski, yeni)))
        sonuc = vakalar(mm, tp)
        oldu = not sonuc[hedef][0]
        kontrol = sonuc["V3"][0]
        ok = oldu and kontrol
        print("%s %s — hedef %s %s · kontrol V3 %s" % (
            "YESIL" if ok else "KIRMIZI", mad, hedef,
            "KIRMIZI (mutant öldü)" if oldu else "YESIL (mutant KAÇTI)",
            "YESIL" if kontrol else "KIRMIZI"))
        kirmizi += 0 if ok else 1

    print("SONUC: %s (kirmizi=%d)" % ("YESIL" if kirmizi == 0 else "KIRMIZI", kirmizi))
    return 0 if kirmizi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
