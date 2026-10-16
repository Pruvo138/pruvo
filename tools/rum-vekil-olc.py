#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RUM VEKIL — CF RUM'dan gunluk sayfa yuklemesini KAYNAK SINIFINA gore gunluk D1'e yazar.

NEDEN VAR (17 Eki 2026):
  GA4 rizasiz oturumu GORMEZ -> GA4'ten sayim almak DONGUSEL. CF RUM rizanin
  DISINDADIR ve `refererHost` boyutunu uretir; boylece "PRUVO'ya herhangi bir
  kanaldan ne kadar ziyaret geldi" SORUSUNU rizanin etkisinden BAGIMSIZ yanitlar.
  GA4 + reklam ROI ekisinin TAM DEGIL ama BAGIMSIZ bir parcasi; bu olcum
  kanal-bagli bir sayim SALGILAMAZ, yalniz trafik kokeni dagilimini gunluk
  D1'e yazar. Reklam tavan hesabi (tools/riza-tavani-olc.py) AYRI bir eksendir.

GUvenliK/CIKTI:
  * Sayilar stdout'a YAZILMAZ (CI loguna sizmaz, yalniz D1).
  * Tek satir: `RUM_VEKIL=YAZILDI gun=<gun> sinif=<k>` ya da
    `RUM_VEKIL=OLCULEMEDI sebep=<jeton>` rc=3.
  * Token/hesap kimligi HICBIR cikti/hata metninde gorunmez (maskeleme).

KULLANIM (borusuz):
  python3 tools/rum-vekil-olc.py                 # dunden UTC, CANLI D1
  python3 tools/rum-vekil-olc.py --gun 2026-10-16
  python3 tools/rum-vekil-olc.py --fikstur <graphql.json>   # test kolu (aga CIKMAZ)
  python3 tools/rum-vekil-olc.py --vt /tmp/yerel.sqlite     # CANLI YERINE sqlite

ENV (canli kol):
  CLOUDFLARE_API_TOKEN    zorunlu
  CLOUDFLARE_ACCOUNT_ID   zorunlu
"""
import argparse
import datetime
import importlib.util
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
SINIFLAR = ("facebook", "instagram", "google", "bing", "chatgpt", "ic",
            "dogrudan", "odeme", "diger")


class Olculemedi(Exception):
    """`HAL=<jeton>` + rc ile DURAN ariza. Sayi basilmaz; 'sessiz %0' YOKTUR."""

    def __init__(self, jeton, aciklama):
        super().__init__(aciklama)
        self.jeton = jeton
        self.aciklama = aciklama


def _d1_modulu():
    """`tools/d1-sync.py`yi importlib ile yukle (ad tire tasir, duz import calismaz).
    SQL kacisi `q` ORADAN alinir: ikinci kopya tutulsaydi biri guncellenir digeri kalirdi
    ve ayrisma SESSIZ olurdu."""
    yol = os.path.join(TOOLS, "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync_rum", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kaynak_sinifi(referer_host):
    """SAF fonksiyon — refererHost -> sinif. Diger tablolar BILMEZ (testin surdugu yuzey)."""
    if not referer_host:
        return "dogrudan"
    h = referer_host.lower().strip()
    if h in ("facebook.com", "l.facebook.com", "m.facebook.com", "lm.facebook.com"):
        return "facebook"
    if h in ("instagram.com", "l.instagram.com"):
        return "instagram"
    if h == "bing.com" or h == "www.bing.com":
        return "bing"
    if h == "chatgpt.com":
        return "chatgpt"
    if h == "pruvo3d.com" or h == "www.pruvo3d.com":
        return "ic"
    if h == "api.iyzipay.com" or h == "sandbox-api.iyzipay.com":
        return "odeme"
    if h == "com.google.android.googlequicksearchbox" or \
       h.startswith("www.google.") or h.startswith("google."):
        return "google"
    return "diger"


def siniflara_ayir(grupations):
    """GraphQL `data.viewer.accounts[0].rumPageloadEventsAdaptiveGroups` listesi
    -> {sinif: toplam} sozlugu. Tum siniflar anahtarda OLUR (toplam=0 dahil)."""
    out = {s: 0 for s in SINIFLAR}
    if not grupations:
        return out
    for row in grupations:
        try:
            n = int(row.get("count") or 0)
        except (TypeError, ValueError):
            continue
        dims = row.get("dimensions") or {}
        h = dims.get("refererHost")
        if h is None:
            h = ""
        out[kaynak_sinifi(h)] += n
    return out


def graphql_yukle(gun, token, account_id):
    """Canli kol — CF GraphQL'den `refererHost` boyutunda sayfa yuklemesini okur.
    accountTag `variables` ile gider; sorgu dizesine elle BIRLESMEZ (enjeksiyon riski)."""
    sorgu = (
        "query RumGunluk($accountTag: String!, $gun: Date!) {\n"
        "  viewer.accounts(filter: {accountTag: $accountTag}) {\n"
        "    rumPageloadEventsAdaptiveGroups(\n"
        "      limit: 500\n"
        "      filter: {date: $gun, bot: 0}\n"
        "      orderBy: [count_DESC]\n"
        "    ) {\n"
        "      count\n"
        "      dimensions { refererHost }\n"
        "    }\n"
        "  }\n"
        "}"
    )
    govde = json.dumps({
        "query": sorgu,
        "variables": {"accountTag": account_id, "gun": gun},
    }).encode("utf-8")
    req = urllib.request.Request(GRAPHQL_URL, data=govde, method="POST",
                                 headers={"Authorization": "Bearer %s" % token,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            yanit_metin = r.read().decode("utf-8", errors="replace")
            durum = r.getcode()
    except urllib.error.HTTPError as e:
        raise Olculemedi("HTTP-DELTA",
                       "HTTP %d CF GraphQL" % e.code)
    except urllib.error.URLError as e:
        raise Olculemedi("AG-DELTA", "CF GraphQL erisilemedi")
    except Exception as e:
        raise Olculemedi("AG-DELTA", "CF GraphQL hatasi: %s" % str(e)[:200])
    if durum != 200:
        raise Olculemedi("HTTP-DELTA", "HTTP %d" % durum)
    try:
        yanit = json.loads(yanit_metin)
    except ValueError:
        raise Olculemedi("YANIT-BOZUK", "CF yaniti JSON degil")
    errs = yanit.get("errors")
    if errs:
        raise Olculemedi("GRAFIK-HATA", "GraphQL errors dolu (n=%d)" % len(errs))
    data = yanit.get("data")
    if not isinstance(data, dict):
        raise Olculemedi("VERI-YOK", "data yolu yok")
    viewer = data.get("viewer")
    if not isinstance(viewer, dict):
        raise Olculemedi("VERI-YOK", "viewer yolu yok")
    hesaplar = viewer.get("accounts")
    if not isinstance(hesaplar, list) or not hesaplar:
        raise Olculemedi("VERI-YOK", "accounts yolu bos")
    grup = hesaplar[0].get("rumPageloadEventsAdaptiveGroups")
    if not isinstance(grup, list):
        raise Olculemedi("VERI-YOK", "rumPageloadEventsAdaptiveGroups yolu yok")
    return grup


def fikstur_oku(yol):
    """Test kolu — GraphQL yanit dosyasi (CANLI DOKUNMAZ, aga CIKMAZ)."""
    if not os.path.exists(yol):
        raise Olculemedi("FIKSTUR-YOK", "fikstur dosyasi yok")
    try:
        with open(yol, encoding="utf-8") as f:
            yanit = json.load(f)
    except Exception as e:
        raise Olculemedi("FIKSTUR-BOZUK", "fikstur okunamadi: %s" % e)
    errs = yanit.get("errors")
    if errs:
        raise Olculemedi("GRAFIK-HATA", "GraphQL errors dolu (n=%d)" % len(errs))
    data = yanit.get("data")
    if not isinstance(data, dict):
        raise Olculemedi("VERI-YOK", "data yolu yok")
    viewer = data.get("viewer")
    hesaplar = (viewer or {}).get("accounts") or []
    if not hesaplar:
        raise Olculemedi("VERI-YOK", "accounts yolu bos")
    return hesaplar[0].get("rumPageloadEventsAdaptiveGroups") or []


def yazma_sql(gun, toplamlar, q_fn):
    """TEK SQL metin — DELETE + INSERT. Cumartesi gun ayni gun ikinci kez koarsa cift
    sayim YOK (PRIMARY KEY + DELETE oncesi). Her satir tek bir sinif toplamini tasir."""
    satirlar = ["DELETE FROM rum_vekil WHERE gun=%s;" % q_fn(gun)]
    for sinif in SINIFLAR:
        if toplamlar.get(sinif, 0) == 0 and sinif != "dogrudan":
            # 0 satirlar ATLANMAZ — sinif yoksa YINE yazilir (0 olarak) ki SELECT'te
            # ayrim olsun; istemci yoksa toplam ayrik gorunmezdi. Ancak performans: 0
            # olanlari yazmamak da mumkun; burada TAM KAPSAM yaz (analiz kolayligi).
            pass
        satirlar.append(
            "INSERT INTO rum_vekil (gun, kaynak, n) VALUES (%s, %s, %d);"
            % (q_fn(gun), q_fn(sinif), int(toplamlar.get(sinif, 0)))
        )
    return "\n".join(satirlar) + "\n"


class YerelVt(object):
    ad = "sqlite"

    def __init__(self, yol):
        self.yol = yol
        self.conn = sqlite3.connect(yol)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._sema()

    def _sema(self):
        """Yerel sqlite'a minimum gerekli tabloyu kur (CI'da --sema D1'i OLUSTURMAZ; bu
        test kolunun HIZLI KENDI KURULUSUDUR — d1-sema.sql kanonik tanim, orada da var)."""
        self.conn.executescript(
            "CREATE TABLE IF NOT EXISTS rum_vekil ("
            "  gun TEXT NOT NULL,"
            "  kaynak TEXT NOT NULL,"
            "  n INTEGER NOT NULL,"
            "  PRIMARY KEY (gun, kaynak)"
            ");"
        )

    def calistir(self, sql_metin):
        try:
            self.conn.executescript(sql_metin)
            self.conn.commit()
        except Exception as e:
            raise Olculemedi("D1-YAZIM-HATASI", "yerel yazim basarisiz: %s" % str(e)[:200])

    def sorgu(self, sql):
        try:
            return [dict(r) for r in self.conn.execute(sql).fetchall()]
        except Exception as e:
            raise Olculemedi("D1-OKUMA-HATASI", "yerel okuma basarisiz: %s" % str(e)[:200])

    def kapat(self):
        try:
            self.conn.close()
        except Exception:
            pass


class D1Vt(object):
    ad = "D1"

    def __init__(self):
        self.d1 = _d1_modulu()

    def calistir(self, sql_metin):
        try:
            self.d1.dosya_calistir(sql_metin)
        except Exception as e:
            raise Olculemedi("D1-YAZIM-HATASI", "D1 yazimi basarisiz: %s" % str(e)[:200])

    def sorgu(self, sql):
        try:
            r = self.d1.sorgu(sql)
        except Exception as e:
            raise Olculemedi("D1-OKUMA-HATASI", "D1 sorgusu basarisiz: %s" % str(e)[:200])
        if not r or not r[0].get("success"):
            raise Olculemedi("D1-OKUMA-HATASI", "D1 yaniti basarili degil")
        return r[0].get("results") or []

    def kapat(self):
        pass


def vt_ac(vt_yolu):
    """`--vt` verildiyse yerel sqlite; verilmediyse CANLI D1."""
    try:
        return YerelVt(vt_yolu) if vt_yolu else D1Vt()
    except Olculemedi:
        raise
    except Exception as e:
        raise Olculemedi("VERITABANI-ACILAMADI", "vt acilamadi: %s" % str(e)[:200])


def bugun_utc():
    return datetime.datetime.now(datetime.timezone.utc).date()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gun", default=None,
                    help="YYYY-MM-DD; varsayilan: dun (UTC)")
    ap.add_argument("--fikstur", default=None,
                    help="GraphQL yanit JSON (test kolu, aga CIKMAZ)")
    ap.add_argument("--vt", default=None,
                    help="D1 yerine yerel sqlite (test kolu)")
    a = ap.parse_args(argv)

    try:
        if a.gun:
            try:
                gun_t = datetime.date.fromisoformat(a.gun)
            except ValueError as e:
                print("RUM_VEKIL=OLCULEMEDI sebep=PENCERE-BICIMI")
                return 3
            gun = gun_t.isoformat()
        else:
            gun = (bugun_utc() - datetime.timedelta(days=1)).isoformat()

        if a.fikstur:
            grup = fikstur_oku(a.fikstur)
            kaynak = "fikstur"
        else:
            token = os.environ.get("CLOUDFLARE_API_TOKEN")
            account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
            if not token or not account_id:
                print("RUM_VEKIL=OLCULEMEDI sebep=JETON-YOK")
                return 3
            grup = graphql_yukle(gun, token, account_id)
            kaynak = "CF-RUM"

        toplamlar = siniflara_ayir(grup)
        vt = vt_ac(a.vt)
        try:
            d1 = _d1_modulu() if a.vt is None else _YerelQ()
            q_fn = d1.q
        except Exception as e:
            raise Olculemedi("D1-MODULU-YOK", "d1-sync yuklenemedi: %s" % str(e)[:200])
        sql = yazma_sql(gun, toplamlar, q_fn)
        try:
            vt.calistir(sql)
        except Olculemedi:
            raise
        except Exception as e:
            raise Olculemedi("D1-YAZIM-HATASI", "yazim basarisiz: %s" % str(e)[:200])
        # Basarili: TEK satir, sayi YOK (gun disinda HICBIR rakam dizgesi).
        print("RUM_VEKIL=YAZILDI gun=%s" % gun)
        return 0
    except Olculemedi as x:
        # Sebep jetonu disinda HICBIR sey basma; hesap/token sizintisi YASAK.
        sys.stderr.write("RUM_VEKIL=OLCULEMEDI sebep=%s\n" % x.jeton)
        print("RUM_VEKIL=OLCULEMEDI sebep=%s" % x.jeton)
        return 3


class _YerelQ(object):
    """`--vt` kolunda d1-sync.py::q mantiginin YEREL KOPYASI — d1-sync import etmek
    icin wrangler'a gecmek gerekirdi; bu canli D1'e DOKUNMAZ, yalnizca SQL metin
    kacar. Ayni kural: tek tirnak -> iki tek tirnak."""

    def q(self, s):
        if s is None:
            return "NULL"
        return "'" + str(s).replace("'", "''") + "'"


if __name__ == "__main__":
    sys.exit(main())