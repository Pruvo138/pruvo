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


def say_eski(baglanti, esik):
    satirlar = baglanti.execute("SELECT olusturma FROM talepler").fetchall()
    sayi = 0
    for (olusturma,) in satirlar:
        try:
            zaman = datetime.fromisoformat(olusturma.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            continue
        if zaman < esik:
            sayi += 1
    return sayi


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
        sayi = say_eski(baglanti, esik)
        if uygula and sayi:
            baglanti.execute("DELETE FROM talepler WHERE olusturma < ?", (esik.isoformat(),))
            baglanti.commit()
        print("KURU=" + str(int(not uygula)) + " SILINECEK=" + str(sayi))
    return 0


def kendini_test():
    simdi = datetime.now(timezone.utc)
    with tempfile.NamedTemporaryFile(prefix="k186-talep-", suffix=".sqlite3") as dosya:
        with sqlite3.connect(dosya.name) as baglanti:
            baglanti.execute("CREATE TABLE talepler (kod TEXT PRIMARY KEY, olusturma TEXT NOT NULL)")
            baglanti.executemany("INSERT INTO talepler (kod, olusturma) VALUES (?, ?)", [
                ("PR-89GUN", (simdi - timedelta(days=89)).isoformat()),
                ("PR-91GUN", (simdi - timedelta(days=91)).isoformat()),
            ])
            kalan = say_eski(baglanti, esik_zamani(simdi))
            baglanti.execute("DELETE FROM talepler WHERE olusturma < ?", (esik_zamani(simdi).isoformat(),))
            baglanti.commit()
            satirlar = baglanti.execute("SELECT kod FROM talepler ORDER BY kod").fetchall()
        sonuc = kalan == 1 and satirlar == [("PR-89GUN",)]
    print("KENDINI_TEST=" + ("GECTI" if sonuc else "DUSTU") + " 89=KALDI 91=GITTI")
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
