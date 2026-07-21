#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EGE-BILGI TAVAN KAPISI (kalici nobetci)

NEDEN VAR: WhatsApp botu Ege, ege-bilgi.md'yi musteriye aktarirken metni
pruvo-bot tarafinda slice(0,6000) ile SESSIZCE kesiyor. Dosya 6000 karakteri
asarsa sondaki icerik (bugun fiyat/teslimat/malzeme satirlarina yakin) botun
gozunden KAYBOLUR ve kimse bir hata gormez. Bu kapi olcumu CI'ya baglar.

Kural:
  * len > 6000  -> KIRMIZI ("bot kesiyor, icerik kaybi"): tavan asildi.
  * len > 5900  -> KIRMIZI ("erken alarm"): pay 100 karakterin altinda; tavana
    carpmadan once ege-bilgi.md kisaltilmali (ya da tavan/bot mantigi ele alinmali).
  * aksi halde  -> YESIL.

Olcum: len(str) = Python karakter sayisi; bot tarafi JS String.slice (UTF-16 kod
birimi) kullanir — ege-bilgi.md'deki Turkce harfler BMP oldugu icin ikisi esittir.
Fail-closed: ege-bilgi.md okunamazsa KIRMIZI.
Cikis: 0 = pay guvenli, 1 = tavan asildi / erken alarm / okuma hatasi.
"""
import os
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(KOK)
EGE_BILGI = os.path.join(ROOT, "ege-bilgi.md")

TAVAN = 6000   # pruvo-bot slice(0,6000): ustunde metin SESSIZCE kesilir
ERKEN = 5900   # pay < 100 -> tavana carpmadan once uyar


def main():
    try:
        with open(EGE_BILGI, encoding="utf-8") as fp:
            metin = fp.read()
    except Exception as hata:  # fail-closed
        print("KIRMIZI: ege-bilgi.md okunamadi -> %s" % hata)
        return 1

    uzunluk = len(metin)
    pay = TAVAN - uzunluk
    print("ege-bilgi.md uzunluk: %d karakter | tavan: %d | kalan pay: %d"
          % (uzunluk, TAVAN, pay))

    if uzunluk > TAVAN:
        print("KIRMIZI: tavan asildi -> bot slice(0,%d) ile metni SESSIZCE kesiyor, "
              "icerik kaybi (%d karakter kesiliyor)" % (TAVAN, uzunluk - TAVAN))
        return 1
    if uzunluk > ERKEN:
        print("KIRMIZI: erken alarm -> kalan pay %d (< 100); tavana (%d) carpmadan "
              "once ege-bilgi.md kisaltilmali" % (pay, TAVAN))
        return 1

    print("SONUC: YESIL - uzunluk %d, kalan pay %d (>= 100)" % (uzunluk, pay))
    return 0


if __name__ == "__main__":
    sys.exit(main())
