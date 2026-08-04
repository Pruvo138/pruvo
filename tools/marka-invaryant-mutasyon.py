#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — tools/marka-invaryant-kapisi.py gercek ihlali yakiyor mu?

NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR ([[mutasyon-kaniti-yeniden-uretilebilir]]).
Kapinin en buyuk riski TOTOLOJI'dir: iki ucu da AYNI fonksiyondan turetilirse kapi her zaman
yesil yanar ve hicbir sey olcmez. Buradaki OLDURUCU mutantlar tam o hali kurar (uc modelini
sayfa yuklemine cevir, arama modelini sayfa kumesine cevir) ve kapinin KIRMIZI yanmasini
sart kosar. KONTROL mutantlari iddia edilmeyen eksende YESIL kalmali — yoksa kapi "her
degisiklige kirmizi yanan" bir gurultu kaynagidir, nobetci degil.

NASIL: mutant DAIMA KOPYAYA uygulanir (gercek agac degismez). ROOT'un tamami gecici bir
dizine SYMLINK'lenir, mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve kapi
O AYNADAN kosulur. Gercek tools/ agacina HICBIR SEY yazilmaz.

🔴 COKME KIRMIZIYLA KARISTIRILMAZ: rc 0/1 disi, "kirmizi ama olculen FAIL yok" ya da
olculen PASS sayisi tabanin altina dusmus kosum COKME sayilir — coken mutant "oldurulmus"
DEGILDIR.

Kabul: her OLDURUCU KIRMIZI + her KONTROL YESIL. Koşum ~15 sn.

Calistir:  python3 tools/marka-invaryant-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_ADI = "marka-invaryant-kapisi.py"
TABAN_PASS = 5          # bunun altina dusen kosum "yesil/kirmizi" degil COKME'dir

# (ad, mutasyona ugrayan dosya, eski, yeni, beklenen)
MUTANTLAR = [
    ("OLDURUCU M1 KATLAMAYI KAPAT — uyelik ham degerden dogsun (Volvo Penta artik Volvo degil)",
     "marka_model_build.py",
     "        kan = evren.katla((x or \"\").strip())",
     "        kan = (x or \"\").strip()", "KIRMIZI"),
    ("OLDURUCU M2 TOTOLOJI — uctaki ?marka= modelini SAYFA yuklemine cevir",
     KAPI_ADI,
     "        filtre = {p[\"id\"] for p in urunler\n"
     "                  if p.get(\"id\") and marka in (p.get(\"marka\") or [])}",
     "        filtre = set(sayfa)", "KIRMIZI"),
    ("OLDURUCU M3 TOTOLOJI — serbest metin modelini SAYFA kumesine cevir",
     KAPI_ADI,
     "        srch = {i for i, h in hs if i and arama.esles(h, tok)}",
     "        srch = set(sayfa)", "KIRMIZI"),
    ("OLDURUCU M4 SAYFA kumesinden IKINCIL markali urunleri dusur",
     KAPI_ADI,
     "                       + [d[\"marka_only\"], d.get(\"ikincil\", [])]):",
     "                       + [d[\"marka_only\"]]):", "KIRMIZI"),
    ("KONTROL K1 davranisi degistirmeyen yazim (uyeler = [] -> list())",
     "marka_model_build.py",
     "    uyeler = []\n    for x in marka_dizisi:",
     "    uyeler = list()\n    for x in marka_dizisi:", "YESIL"),
    ("KONTROL K2 iddia edilmeyen eksen (kapinin beyan metni)",
     KAPI_ADI,
     "NE OLCULMEDI (beyan):",
     "NE OLCULMEDI (beyan) :", "YESIL"),
]


def ayna_kur(tmp):
    """ROOT'un SALT OKUNUR aynasi: tools/ gercek bir dizin (icindekiler symlink), digerleri
    dogrudan symlink. Kapi kendi TOOLS/ROOT'unu bu aynadan cozer."""
    kok = os.path.join(tmp, "kok")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(kok, ad))
    for ad in os.listdir(TOOLS):
        os.symlink(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    return kok


def main():
    tmp = tempfile.mkdtemp(prefix="marka-invaryant-mutasyon-")
    sonuc = []
    try:
        for ad, dosya, eski, yeni, beklenen in MUTANTLAR:
            kaynak_yolu = os.path.join(TOOLS, dosya)
            taban = open(kaynak_yolu, encoding="utf-8").read()
            if taban.count(eski) != 1:
                # Capa kaymis: "mutant uygulanamadi" YESIL sayilmaz, kanit OLCULEMEDI'dir.
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            kok = ayna_kur(tmp + "/" + str(len(sonuc)))
            hedef = os.path.join(kok, "tools", dosya)
            os.unlink(hedef)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run([sys.executable, os.path.join(kok, "tools", KAPI_ADI)],
                               capture_output=True, text=True, cwd=kok)
            cikti = r.stdout + r.stderr
            fail = len(re.findall(r"^  FAIL ", cikti, re.M))
            gecen = len(re.findall(r"^  PASS ", cikti, re.M))
            if r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d: %s)" % (r.returncode, cikti.strip().split("\n")[-1][:80])
            elif r.returncode == 1 and fail == 0:
                gozlem = "COKME(kirmizi ama olculen iddia yok)"
            elif gecen < TABAN_PASS:
                gozlem = "COKME(olculen PASS sayisi dusuk: %d)" % gecen
            else:
                gozlem = "KIRMIZI" if r.returncode == 1 else "YESIL"
            sonuc.append((ad, beklenen, "%s (FAIL=%d PASS=%d)" % (gozlem, fail, gecen)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kapi: tools/%s)" % KAPI_ADI)
    kalan = 0
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-92s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
