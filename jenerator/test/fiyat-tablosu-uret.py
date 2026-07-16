#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Okan'a taban fiyat şablonu üretir -> tools/taban-fiyat-tablosu.md

18 satır: ürün, varsayılan ölçüler, taban hacim, fiyat=___ TL.
Okan fiyatları doldurdukça jenerator/urunler/<id>.json 'tabanFiyatTL' alanına
işlenir (tools/duzelt.py benzeri tekil düzenleme; build sonrası fiyat canlanır).
"""
import io
import json
import os

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
JEN_DIR = os.path.dirname(TEST_DIR)
ROOT = os.path.dirname(JEN_DIR)
CIKTI = os.path.join(ROOT, "tools", "taban-fiyat-tablosu.md")


def main():
    with io.open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        d = json.load(f)
    urunler = d["urunler"] if isinstance(d, dict) and "urunler" in d else d
    basliklar = dict((u["id"], u.get("baslik") or u["id"])
                     for u in urunler if u.get("parametrik"))

    satirlar = []
    for dosya in sorted(os.listdir(os.path.join(JEN_DIR, "urunler"))):
        if not dosya.endswith(".json"):
            continue
        with io.open(os.path.join(JEN_DIR, "urunler", dosya), encoding="utf-8") as f:
            sema = json.load(f)
        olculer = ", ".join(
            "%s=%s%s" % (p.get("etiket") or p["ad"], p["varsayilan"],
                         (" " + p["birim"]) if p.get("birim") else "")
            for p in sema["parametreler"] if (p.get("tip", "sayi") != "metin"))
        taban_cm3 = sema["tabanHacimMm3"] / 1000.0
        fiyat = sema.get("tabanFiyatTL")
        fiyat_metni = ("**___ TL**" if fiyat is None
                       else str(fiyat).replace(".", ",") + " TL")
        satirlar.append("| %s | %s | %.1f cm³ | %s |" % (
            basliklar.get(sema["id"], sema["id"]), olculer,
            taban_cm3, fiyat_metni))

    icerik = u"""# TABAN FİYAT TABLOSU — Okan dolduracak (sarı seri konfigüratör)

Taban fiyat = ürünün **varsayılan ölçülerdeki PLA (Siyah/Beyaz/Gri)** satış fiyatı.
Diğer her şey formülden türetilir: `fiyat = tabanFiyat × (hacim/tabanHacim) ×
filamentKatsayı × renkFaktör` (PLA 1.00 / PETG 1.30 / ABS 1.50 / TPU 1.55 /
ASA 1.60 / Karbon 2.00; Diğer renk ×1.15). Kuruş korunur, yuvarlama yok.

Fiyat girilene kadar sitede o ürünün fiyatı "—" görünür (sipariş WhatsApp'la sürer).
Doldurulan fiyat `jenerator/urunler/<id>.json` içindeki `tabanFiyatTL` alanına yazılır.

| Ürün | Varsayılan ölçüler | Taban hacim | Taban fiyat (PLA) |
|---|---|---|---|
%s

*Bu dosya `python3 jenerator/test/fiyat-tablosu-uret.py` ile şemalardan üretildi;
elle fiyat işlendikten sonra yeniden üretirsen fiyatlar şemadan gelir (kaybolmaz).*
""" % "\n".join(satirlar)

    with io.open(CIKTI, "w", encoding="utf-8") as f:
        f.write(icerik)
    print("yazildi: %s (%d satir)" % (CIKTI, len(satirlar)))


if __name__ == "__main__":
    main()
