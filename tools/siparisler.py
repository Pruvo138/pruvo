#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO SIPARIS LISTESI — canli D1'den siparisleri okur. SALT-OKUNUR.

    python3 tools/siparisler.py                       # son 10, tum durumlar
    python3 tools/siparisler.py --son 25
    python3 tools/siparisler.py --durum odendi
    python3 tools/siparisler.py --son 5 --durum bekliyor

KAPSAM = SADECE OKUMA. wrangler'a giden tek yol `wrangler_sorgu()`; SELECT
disinda bir ifade gecerse (assert) calismadan durur. Hicbir yazma/silme yolu
YOKTUR — shop/ worker'i (src/index.js) siparisleri yazar, bu arac dokunmaz.

Sema: tools/d1-sema.sql (tablo: siparisler). Para KURUS tamsayisinda tutulur
(yuvarlama yok); genel toplam = tutar_kurus + kargo_kurus (KDV dahil fiyat,
kdv_kurus sadece dokum icin — bkz sema yorumu).

wrangler'i shop/ dizininden cagiriyoruz (wrangler.toml + D1 binding orada,
KURULUM.md'deki gibi); yerelde wrangler'in kendi oturumu kullanilir, token
gerekmez (bkz tools/d1-sync.py'deki ayni desen).
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    YEREL_TZ = ZoneInfo("Europe/Istanbul")
except Exception:  # pragma: no cover - zoneinfo veritabani eksikse yedek
    YEREL_TZ = timezone(timedelta(hours=3))

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
DB = "pruvo-katalog"

DURUMLAR = ("odendi", "bekliyor", "havale-bekliyor", "incele")
KOLONLAR = (
    "siparis_no", "tarih", "durum", "odeme_yontemi",
    "tutar_kurus", "kargo_kurus", "kdv_kurus",
    "musteri_ad", "musteri_tel", "urunler",
)


# ------------------------------------------------------------------ sorgu

def sql_sorgu(son, durum):
    """SELECT SQL'i uretir. `durum` "hepsi" ise filtre eklenmez.

    `durum` argparse `choices` ile zaten kisitli (DURUMLAR + "hepsi"); yine de
    burada ikinci kez dogrulaniyor — bu fonksiyon dogrudan da cagrilabilir.
    """
    if durum != "hepsi" and durum not in DURUMLAR:
        raise ValueError("bilinmeyen durum: %r" % durum)
    son = max(int(son), 0)
    sql = "SELECT %s FROM siparisler" % ", ".join(KOLONLAR)
    if durum != "hepsi":
        sql += " WHERE durum = '%s'" % durum
    sql += " ORDER BY id DESC LIMIT %d" % son
    return sql


def wrangler_sorgu(sql):
    """wrangler d1 execute --remote --json calistirir, satir listesi doner.

    SALT-OKUNUR KAPI: SELECT disinda bir ifade buraya gelirse calismaz.
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("sadece SELECT calistirilir, gelen: %r" % sql)

    komut = ["npx", "--yes", "wrangler@4", "d1", "execute", DB,
             "--remote", "--json", "--command", sql]
    p = subprocess.run(komut, cwd=SHOP, capture_output=True, text=True)
    ham = (p.stdout or "") + (p.stderr or "")

    if "code: 10000" in ham or "Authentication error" in ham:
        sys.exit(
            "D1 KIMLIK HATASI (code 10000) — token/oturum D1'e erisemiyor.\n"
            "  Yerelde 'npx wrangler login' ile giris yapilmis olmali (tools/d1-sync.py\n"
            "  ile ayni gereksinim)."
        )

    i = p.stdout.find("[")
    if i == -1:
        sys.exit("wrangler cikti vermedi:\n" + ham[-2000:])
    try:
        veri = json.loads(p.stdout[i:])
    except (ValueError, TypeError):
        sys.exit("wrangler ciktisi cozulemedi:\n" + ham[-2000:])

    if not veri or not veri[0].get("success", False):
        sys.exit("wrangler sorgusu basarisiz:\n" + ham[-2000:])
    return veri[0].get("results", []) or []


# ------------------------------------------------------------------ bicim

def tl(kurus):
    """Kurus tamsayisini Turkce bicimli 'X.XXX,XX TL' string'e cevirir."""
    try:
        lira = (kurus or 0) / 100.0
    except TypeError:
        lira = 0.0
    s = "{:,.2f}".format(lira)
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " TL"


def yerel_saat(iso_utc):
    """ISO 8601 UTC ('...Z') -> 'gg.aa.yyyy ss:dd' Europe/Istanbul saatinde.

    Format bozuksa (beklenmedik veri) crash etmez, ham degeri geri verir —
    bu arac SALT-OKUNUR bir rapor araci, kotu bir satir yuzunden durmamali.
    """
    if not iso_utc:
        return "?"
    s = iso_utc[:-1] + "+00:00" if iso_utc.endswith("Z") else iso_utc
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return iso_utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(YEREL_TZ).strftime("%d.%m.%Y %H:%M")


def _kisalt(metin, azami=60):
    metin = (metin or "").strip()
    if len(metin) <= azami:
        return metin
    return metin[:azami - 3] + "..."


def format_siparis(row):
    """Tek siparis satirini okunur cok-satirli bloga cevirir."""
    lines = []
    lines.append("=" * 66)
    lines.append("%s   %s (yerel)" % (row.get("siparis_no") or "?",
                                       yerel_saat(row.get("tarih"))))
    lines.append("durum: %-16s yontem: %s"
                  % (row.get("durum") or "?", row.get("odeme_yontemi") or "?"))

    tutar = row.get("tutar_kurus") or 0
    kargo = row.get("kargo_kurus") or 0
    genel = tutar + kargo
    lines.append("urun toplami: %s | kargo: %s | genel toplam: %s"
                  % (tl(tutar), tl(kargo), tl(genel)))

    lines.append("musteri: %s | %s" % (row.get("musteri_ad") or "-",
                                        row.get("musteri_tel") or "-"))
    lines.append("-" * 66)

    try:
        kalemler = json.loads(row.get("urunler") or "[]")
    except (ValueError, TypeError):
        kalemler = []
    if not isinstance(kalemler, list) or not kalemler:
        lines.append("  (urun satiri yok)")
    else:
        for k in kalemler:
            if not isinstance(k, dict):
                continue
            baslik = k.get("baslik") or k.get("id") or "?"
            mr = " / ".join(p for p in (k.get("malzeme"), k.get("renk")) if p)
            lines.append("  - %s" % baslik)
            lines.append("      %s | adet: %s | tutar: %s"
                          % (mr or "-", k.get("adet", "?"),
                             tl(k.get("tutar_kurus") or 0)))
            detay = _kisalt(k.get("parametre_detay"))
            if detay:
                lines.append("      %s" % detay)
    return "\n".join(lines)


# ------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--son", type=int, default=10, help="son N siparis (varsayilan 10)")
    ap.add_argument("--durum", choices=list(DURUMLAR) + ["hepsi"], default="hepsi")
    args = ap.parse_args(argv)

    sql = sql_sorgu(args.son, args.durum)
    satirlar = wrangler_sorgu(sql)

    print("=" * 66)
    print("PRUVO SIPARISLER — son %d, durum=%s" % (args.son, args.durum))
    print("=" * 66)
    if not satirlar:
        print("(kayit yok)")
        return 0
    for row in satirlar:
        print(format_siparis(row))
        print()
    print("Toplam: %d siparis" % len(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
