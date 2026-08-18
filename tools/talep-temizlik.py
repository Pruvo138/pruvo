#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""talepler tablosu icin 90 gunluk, durumdan bagimsiz temizlik araci."""

import argparse
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def esik_zamani(now=None):
    return (now or datetime.now(timezone.utc)) - timedelta(days=90)


def silinecek_kodlar(baglanti, esik):
    satirlar = baglanti.execute("SELECT kod, olusturma FROM talepler").fetchall()
    kodlar = []
    for kod, olusturma in satirlar:
        try:
            zaman = datetime.fromisoformat(olusturma.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            continue
        if zaman < esik:
            kodlar.append(kod)
    return kodlar


def say_eski(baglanti, esik):
    return len(silinecek_kodlar(baglanti, esik))


def sil_eski(baglanti, kodlar):
    """Yalniz calistir tarafindan hesaplanan kod listesini siler.

    Listeyi burada yeniden hesaplamak, canli D1 yazarlari arasinda sayilan ve
    silinen kumelerin ayrismasina izin verirdi. Bu fonksiyonun kendi SQL'i
    yalnizca verilen kodlar uzerindedir.
    """
    for baslangic in range(0, len(kodlar), 500):
        parca = kodlar[baslangic:baslangic + 500]
        yerler = ",".join("?" for _ in parca)
        baglanti.execute("DELETE FROM talepler WHERE kod IN (" + yerler + ")", parca)
    return len(kodlar)


def calistir(db_yolu, uygula=False):
    if db_yolu is None:
        print("KURU=1 SILINECEK=0 DB=YOK")
        return 0
    yol = Path(db_yolu)
    if not yol.exists():
        print("KURU=" + str(int(not uygula)) + " SILINECEK=0 DB=YOK")
        return 0
    with sqlite3.connect(yol) as baglanti:
        esik = esik_zamani()
        kodlar = silinecek_kodlar(baglanti, esik)
        sayi = len(kodlar)
        if uygula and sayi:
            sil_eski(baglanti, kodlar)
            baglanti.commit()
        print("KURU=" + str(int(not uygula)) + " SILINECEK=" + str(sayi))
    return 0


def kendini_test():
    simdi = datetime.now(timezone.utc)
    with tempfile.NamedTemporaryFile(prefix="k186-talep-", suffix=".sqlite3") as dosya:
        with sqlite3.connect(dosya.name) as baglanti:
            baglanti.execute("CREATE TABLE talepler (kod TEXT PRIMARY KEY, olusturma TEXT NOT NULL)")
            baglanti.executemany("INSERT INTO talepler (kod, olusturma) VALUES (?, ?)", [
                ("PR-Z89", (simdi - timedelta(days=89)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
                ("PR-P89", (simdi - timedelta(days=89)).isoformat()),
                ("PR-Z91", (simdi - timedelta(days=91)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
                ("PR-P91", (simdi - timedelta(days=91)).isoformat()),
                ("PR-BOZUK", "belli-degil"),
            ])
            esik = esik_zamani(simdi)
            kuru = silinecek_kodlar(baglanti, esik)
            silinen = sil_eski(baglanti, kuru)
            baglanti.commit()
            satirlar = baglanti.execute("SELECT kod FROM talepler ORDER BY kod").fetchall()
        kalan = {kod for (kod,) in satirlar}
        f1 = len(kuru) == silinen == 2
        f2 = "PR-Z91" not in kalan and "PR-P91" not in kalan
        f3 = "PR-Z89" in kalan and "PR-P89" in kalan
        f4 = "PR-BOZUK" in kalan
        f5 = sil_eski.__code__.co_argcount == 2 and "silinecek_kodlar" not in sil_eski.__code__.co_names
        with tempfile.NamedTemporaryFile(prefix="k186-talep-calistir-", suffix=".sqlite3") as calistir_dosyasi:
            with sqlite3.connect(calistir_dosyasi.name) as calistir_baglanti:
                calistir_baglanti.execute("CREATE TABLE talepler (kod TEXT PRIMARY KEY, olusturma TEXT NOT NULL)")
                calistir_baglanti.execute(
                    "INSERT INTO talepler (kod, olusturma) VALUES (?, ?)",
                    ("PR-R1", (simdi - timedelta(days=91)).isoformat()),
                )
            calistir(calistir_dosyasi.name, uygula=True)
            with sqlite3.connect(calistir_dosyasi.name) as kalan_baglanti:
                r1 = kalan_baglanti.execute("SELECT COUNT(*) FROM talepler").fetchone()[0] == 0
        sonuc = f1 and f2 and f3 and f4 and f5 and r1
    print("KENDINI_TEST=" + ("GECTI" if sonuc else "DUSTU") +
          " F1=" + ("GECTI" if f1 else "DUSTU") +
          " F2=" + ("GECTI" if f2 else "DUSTU") +
          " F3=" + ("GECTI" if f3 else "DUSTU") +
          " F4=" + ("GECTI" if f4 else "DUSTU") +
          " F5=" + ("GECTI" if f5 else "DUSTU") +
          " R1=" + ("GECTI" if r1 else "DUSTU"))
    return 0 if sonuc else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path)
    parser.add_argument("--uygula", action="store_true")
    parser.add_argument("--kendini-test", action="store_true")
    args = parser.parse_args()
    if args.kendini_test:
        return kendini_test()
    return calistir(args.db, args.uygula)


if __name__ == "__main__":
    sys.exit(main())
