#!/usr/bin/env python3
"""Hattın onarım turu açıp açmadığını diskten okur.

ÜÇ sayıyı ölçer:
  ONARIM TURU       = ci-nobeti.log içinde "acilan_tur=1" geçen satır sayısı (TÜM dosya)
  GOZCU TURU (bugün)= gozcu.log içinde BUGÜNÜN tarihi (YYYY-AA-GG) VE "GOZCU " geçen satır sayısı
  KIRMIZI GORULDU   = gozcu.log içinde BUGÜNÜN tarihi VE "YENI_KIRMIZI=1" geçen satır sayısı

BİLEREK ölçMEDİĞİ:
  - "onarim commit'i sayısı" ya da "son 24 saat commit" — bunlar cip/mimar işini de
    sayar ve halka çalışıyormuş izlenimi verir.
  - Tek dürüst ölçüt: otomatik hattın FİİLEN tur açıp açmadığı.

ONARIM TURU = 0 ise sistem onarım yapmıyor (kırmızı görülmemiş olsa bile
"calisiyor" kanıtı DEĞİLDİR — kırmızı yoksa o gün bir şey KIRILMAMIŞ olabilir,
ama hat da bakmamış olabilir).

Hiçbir dosyayı DEĞİŞTİRMEZ, ağa çıkmaz, LLM/agent turu açmaz. Salt okuma.

Kullanım:  python3 tools/onarim-durum.py
Çıkış kodu: bkz. HÜKÜM tablosu.
"""

import datetime
import os
import sys

CINOBETI = os.path.expanduser("~/.claude/cron/ci-nobeti.log")
GOZCU = os.path.expanduser("~/.claude/cron/gozcu.log")
BUGUN = datetime.date.today().isoformat()


def _say(dosya_yolu, kosul):
    """dosya_yolu yoksa 'OLCULEMEDI' yazar (0 yazmaz)."""
    if not os.path.exists(dosya_yolu):
        return "OLCULEMEDI"
    n = 0
    with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
        for satir in f:
            if kosul(satir):
                n += 1
    return str(n)


def olc():
    return {
        "ONARIM": _say(CINOBETI, lambda s: "acilan_tur=1" in s),
        "GOZCU": _say(GOZCU, lambda s: BUGUN in s and "GOZCU " in s),
        "KIRMIZI": _say(GOZCU, lambda s: BUGUN in s and "YENI_KIRMIZI=1" in s),
    }


def huküm(sayilar):
    """Üç sayıdan hüküm basar.

    rc=0 → hat FİİLEN tur açmış.
    rc=1 → ya kırmızı görüldü ama tur açılmadı, ya da tur hiç yok.
    'OLCULEMEDI' değerler VEYA (worktree'dir) sayılmamışsa → rc=1 (kanıt yok).
    """
    raw = sayilar["ONARIM"]
    try:
        onarim = int(raw)
    except ValueError:
        # OLCULEMEDI ya da beklenmedik string
        return ("ONARIM TURU sayilamadi (log yok/okunamadi).", 1)
    try:
        kirmizi = int(sayilar["KIRMIZI"])
    except ValueError:
        kirmizi = 0
    if onarim > 0:
        return ("hat FIILEN tur acmis.", 0)
    if kirmizi > 0:
        return ("KIRMIZI GORULDU AMA TEK TUR ACILMADI. Hat bakiyor, onarmiyor.", 1)
    return ("onarim turu YOK. (Kirmizi da gorulmedi; 'calisiyor' KANITI DEGILDIR.)", 1)


def main():
    sayilar = olc()
    print(
        "ONARIM={} GOZCU={} KIRMIZI={}".format(
            sayilar["ONARIM"], sayilar["GOZCU"], sayilar["KIRMIZI"]
        )
    )
    mesaj, rc = huküm(sayilar)
    print("HUKUM: {}".format(mesaj))
    return rc


if __name__ == "__main__":
    sys.exit(main())
