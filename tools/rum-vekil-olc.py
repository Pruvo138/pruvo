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
  * Tek satir: `RUM_VEKIL=YAZILDI gun=<gun>` (--ham: `RUM_VEKIL_HAM=YAZILDI gun=<gun>`)
    ya da `RUM_VEKIL=OLCULEMEDI sebep=<jeton>` rc=3.
  * Token/hesap kimligi HICBIR cikti/hata metninde gorunmez (maskeleme).
  * `--ham` modu: tek seferlik refererHost × bot kirilimini `rum_vekil_ham` tablosuna
    yazar; `rum_vekil` tablosuna DOKUNMAZ (iki tablo tamamen ayri yazicilardir).
  * `--bos-ulke` modu: tek seferlik BOS referrer × ulke × UTC saat kirilimini
    `rum_vekil_bos_ulke` tablosuna yazar; `rum_vekil`/`rum_vekil_ham` tablolarina
    DOKUNMAZ (16 Eki 9.441 yuklemenin %93'u BOS referrer; hipotez = bizim CI nobet
    tarayicilarimiz; ayni gun ikinci kez koarsa cift sayim YOK).

KULLANIM (borusuz):
  python3 tools/rum-vekil-olc.py                 # dunden UTC, CANLI D1
  python3 tools/rum-vekil-olc.py --gun 2026-10-16
  python3 tools/rum-vekil-olc.py --fikstur <graphql.json>   # test kolu (aga CIKMAZ)
  python3 tools/rum-vekil-olc.py --vt /tmp/yerel.sqlite     # CANLI YERINE sqlite
  python3 tools/rum-vekil-olc.py --ham                       # rum_vekil_ham'a yazar (ham kirilim)
  python3 tools/rum-vekil-olc.py --bos-ulke                  # rum_vekil_bos_ulke'ye yazar

ENV (canli kol):
  CLOUDFLARE_API_TOKEN     zorunlu
  CLOUDFLARE_ACCOUNT_ID    zorunlu
  PRUVO_RUM_HAM            "true" ise --ham ile AYNI (CI workflow'dan)
  PRUVO_RUM_BOS_ULKE       "true" ise --bos-ulke ile AYNI (CI workflow'dan)
  PRUVO_RUM_GUN            dolu ise --gun <deger> ile AYNI (CI workflow'dan)
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
        # Bicim 16 Eki tek olcum kosumunun (CI run 38933700908, HTTP 200) sorgusuyla AYNI:
        # `viewer { accounts(...) }` ic ice (nokta YOK), CF skaleri kucuk harf `string`,
        # bot suzgeci YOK. Bicim `rum-vekil-test.py::V7` ile olculur.
        "query RumGunluk($accountTag: string!, $gun: Date!) {\n"
        "  viewer {\n"
        "    accounts(filter: {accountTag: $accountTag}) {\n"
        "      rumPageloadEventsAdaptiveGroups(\n"
        "        limit: 500\n"
        "        filter: {date: $gun}\n"
        "        orderBy: [count_DESC]\n"
        "      ) {\n"
        "        count\n"
        "        dimensions { refererHost }\n"
        "      }\n"
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


def graphql_ham_yukle(gun, token, account_id):
    """Ham kol — CF GraphQL'den refererHost × bot kirilimini okur.
    Tek seferlik teshir/karakter icin; siniflama YAPMAZ, ham kirilimi
    `rum_vekil_ham`'a yazar. Iskelet V7 ile ayni (`viewer { accounts }` ic ice,
    kucuk harf `string!` skaler, `Date!`); bicim `rum-vekil-test.py::V10` ile olculur.
    accountTag `variables` ile gider; sorgu dizesine elle BIRLESMEZ (enjeksiyon riski)."""
    sorgu = (
        # Bicim `graphql_yukle` ile AYNI iskelet (V7) + ek boyut `bot`:
        # `viewer { accounts(...) }` ic ice (nokta YOK), CF skaleri kucuk harf `string`,
        # bot suzgeci YOK (CF'nin ham sinifi — bize dokunmaz).
        "query RumHam($accountTag: string!, $gun: Date!) {\n"
        "  viewer {\n"
        "    accounts(filter: {accountTag: $accountTag}) {\n"
        "      rumPageloadEventsAdaptiveGroups(\n"
        "        limit: 1000\n"
        "        filter: {date: $gun}\n"
        "        orderBy: [count_DESC]\n"
        "      ) {\n"
        "        count\n"
        "        dimensions { refererHost bot }\n"
        "      }\n"
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


def graphql_bos_ulke_yukle(gun, token, account_id):
    """Bos-referrer kolu — CF GraphQL'den refererHost × countryName × datetimeHour
    kirilimini okur. Istemci YALNIZ bos referrer satirlarini biriktirir; ulke
    None ise "" kullanilir, saat datetimeHour'dan UTC 0-23 olarak cikarilir.
    Iskelet V7 ile ayni (`viewer { accounts }` ic ice, kucuk harf `string!` skaler,
    `Date!`); bicim `rum-vekil-test.py::V12` ile olculur. accountTag `variables`
    ile gider; sorgu dizesine elle BIRLESMEZ (enjeksiyon riski). Limit 10000:
    16 Eki 9.441 yuklemenin tamamini tek sayfada almak icin (CF varsayilan 100
    yetmez; 1000 ham icin yeterliydi, bos-ulke daha genis bir eksen)."""
    sorgu = (
        # Bicim `graphql_ham_yukle` ile AYNI iskelet + boyutlar `countryName` ve
        # `datetimeHour` (UTC). `viewer { accounts(...) }` ic ice (nokta YOK), CF
        # skaleri kucuk harf `string`, bot suzgeci YOK.
        "query RumBosUlke($accountTag: string!, $gun: Date!) {\n"
        "  viewer {\n"
        "    accounts(filter: {accountTag: $accountTag}) {\n"
        "      rumPageloadEventsAdaptiveGroups(\n"
        "        limit: 10000\n"
        "        filter: {date: $gun}\n"
        "        orderBy: [count_DESC]\n"
        "      ) {\n"
        "        count\n"
        "        dimensions { refererHost countryName datetimeHour }\n"
        "      }\n"
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


def ham_satirlari(grupations):
    """GraphQL `dimensions { refererHost bot }` listesi -> [(host, bot, n), ...].
    Host kucuk harfe cekilir; None/bos -> "" (dogrudan). Bot suzgeci YOK
    (CF'nin ham sinifi — bize dokunmaz). Ayni (host, bot) birden fazla satirda
    gelirse TOPLANIR (CF genellikle zaten tek satir verir; savunma ama cli)."""
    toplam = {}
    if not grupations:
        return []
    for row in grupations:
        try:
            n = int(row.get("count") or 0)
        except (TypeError, ValueError):
            continue
        dims = row.get("dimensions") or {}
        h = dims.get("refererHost")
        if h is None:
            h = ""
        try:
            bot = int(dims.get("bot") or 0)
        except (TypeError, ValueError):
            bot = 0
        anahtar = (str(h).lower().strip(), bot)
        toplam[anahtar] = toplam.get(anahtar, 0) + n
    return [(h, b, n) for (h, b), n in toplam.items()]


def yazma_ham_sql(gun, satirlar, q_fn):
    """TEK SQL metin — DELETE + INSERT. `rum_vekil_ham` tablosuna yazar;
    `rum_vekil`'e DOKUNMAZ. Ayni gun ikinci kez koarsa cift sayim YOK
    (PRIMARY KEY (gun, host, bot) + DELETE oncesi)."""
    satirlar_out = ["DELETE FROM rum_vekil_ham WHERE gun=%s;" % q_fn(gun)]
    for host, bot, n in satirlar:
        satirlar_out.append(
            "INSERT INTO rum_vekil_ham (gun, host, bot, n) VALUES (%s, %s, %d, %d);"
            % (q_fn(gun), q_fn(host), int(bot), int(n))
        )
    return "\n".join(satirlar_out) + "\n"


def _saat_coz(datetime_hour):
    """CF `datetimeHour` boyutundan UTC saat 0-23 cikar. Gecerli format
    `YYYY-MM-DDThh[:mm[:ss]][Z]` (CF `YYYY-MM-DDThh:00:00Z` verir). Ayrik
    saat (`:00:00`) disinda gelirse hata OLUME; -1 dondurur (ust katman satir
    ATLAR, sessiz %0 YOKTUR)."""
    if not datetime_hour or not isinstance(datetime_hour, str):
        return -1
    # En azindan 13 karakter (YYYY-MM-DDThh); saat parcasi 11..13.
    if len(datetime_hour) < 13 or datetime_hour[10] != "T":
        return -1
    hh = datetime_hour[11:13]
    if not hh.isdigit():
        return -1
    saat = int(hh)
    if saat < 0 or saat > 23:
        return -1
    return saat


def bos_ulke_satirlari(grupations):
    """GraphQL `dimensions { refererHost countryName datetimeHour }` listesi
    -> [(ulke, saat, n), ...]. YALNIZ refererHost None/bos satirlari alinir
    (dolu referrer AYRI tabloda: rum_vekil/rum_vekil_ham). ulke None ise ""
    kullanilir; saat _saat_coz ile UTC 0-23 (gecersiz saat -> satir ATLANIR,
    count OLMADAN; sayim YUTULMAZ). Ayni (ulke, saat) birden fazla satirda
    gelirse TOPLANIR (CF'nin pagination davranisi nedeniyle savunma ama cli)."""
    toplam = {}
    if not grupations:
        return []
    for row in grupations:
        try:
            n = int(row.get("count") or 0)
        except (TypeError, ValueError):
            continue
        dims = row.get("dimensions") or {}
        h = dims.get("refererHost")
        if h is None or h == "":
            pass  # bos referrer — bu kolun konusu
        else:
            continue  # dolu referrer — rum_vekil/rum_vekil_ham isi
        ulke = dims.get("countryName")
        if ulke is None:
            ulke = ""
        saat = _saat_coz(dims.get("datetimeHour"))
        if saat < 0:
            # Gecersiz saat — sayim YUTULMAZ; bu beklenmedik veri, hata olarak
            # satir birakip sayimi sayma yerine -- saat ayristirilamadiysa bu
            # satirin count'u ATILIR (sessiz %0 YASAK). Olcum journali:
            # PRUVO_RUM_BOS_ULKE ekseninde hata = atla + stderr yok (CI loguna
            # bilincli sizmaz; debug icin yerel --fikstur kosumu disinda muaf).
            continue
        anahtar = (str(ulke).strip(), saat)
        toplam[anahtar] = toplam.get(anahtar, 0) + n
    return [(u, s, n) for (u, s), n in toplam.items()]


def yazma_bos_ulke_sql(gun, satirlar, q_fn):
    """TEK SQL metin — DELETE + INSERT. `rum_vekil_bos_ulke` tablosuna yazar;
    `rum_vekil`/`rum_vekil_ham`'a DOKUNMAZ. Ayni gun ikinci kez koarsa cift
    sayim YOK (PRIMARY KEY (gun, ulke, saat) + DELETE oncesi)."""
    satirlar_out = ["DELETE FROM rum_vekil_bos_ulke WHERE gun=%s;" % q_fn(gun)]
    for ulke, saat, n in satirlar:
        satirlar_out.append(
            "INSERT INTO rum_vekil_bos_ulke (gun, ulke, saat, n) VALUES (%s, %s, %d, %d);"
            % (q_fn(gun), q_fn(ulke), int(saat), int(n))
        )
    return "\n".join(satirlar_out) + "\n"


class YerelVt(object):
    ad = "sqlite"

    def __init__(self, yol):
        self.yol = yol
        self.conn = sqlite3.connect(yol)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._sema()

    def _sema(self):
        """Yerel sqlite'a minimum gerekli tablolari kur (CI'da --sema D1'i OLUSTURMAZ; bu
        test kolunun HIZLI KENDI KURULUSUDUR — d1-sema.sql kanonik tanim, orada da var)."""
        self.conn.executescript(
            "CREATE TABLE IF NOT EXISTS rum_vekil ("
            "  gun TEXT NOT NULL,"
            "  kaynak TEXT NOT NULL,"
            "  n INTEGER NOT NULL,"
            "  PRIMARY KEY (gun, kaynak)"
            ");"
            "CREATE TABLE IF NOT EXISTS rum_vekil_ham ("
            "  gun TEXT NOT NULL,"
            "  host TEXT NOT NULL,"
            "  bot INTEGER NOT NULL,"
            "  n INTEGER NOT NULL,"
            "  PRIMARY KEY (gun, host, bot)"
            ");"
            "CREATE TABLE IF NOT EXISTS rum_vekil_bos_ulke ("
            "  gun TEXT NOT NULL,"
            "  ulke TEXT NOT NULL,"
            "  saat INTEGER NOT NULL,"
            "  n INTEGER NOT NULL,"
            "  PRIMARY KEY (gun, ulke, saat)"
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
    ap.add_argument("--ham", action="store_true", default=False,
                    help="Tek seferlik refererHost x bot kirilimi (rum_vekil_ham tablosuna yazar; rum_vekil'e DOKUNMAZ)")
    ap.add_argument("--bos-ulke", action="store_true", default=False,
                    help="Tek seferlik BOS referrer x ulke x UTC saat kirilimi (rum_vekil_bos_ulke tablosuna yazar; rum_vekil/rum_vekil_ham'a DOKUNMAZ)")
    a = ap.parse_args(argv)

    # CI workflow input'lari: PRUVO_RUM_HAM=true -> --ham; PRUVO_RUM_BOS_ULKE=true -> --bos-ulke;
    # PRUVO_RUM_GUN=YYYY-MM-DD -> --gun. CLI bayraklari acik oldugunda onceliklidir; aksi halde
    # env'den okunur. Boylece test kolu (--ham/--gun ile) oldugu gibi calisir, CI da inputs'lari
    # env'ye yazip python'a hicbir sey gecmeden devreye alir (enjeksiyon yuzeyi YOK).
    if not a.ham and os.environ.get("PRUVO_RUM_HAM", "").lower() == "true":
        a.ham = True
    if not a.bos_ulke and os.environ.get("PRUVO_RUM_BOS_ULKE", "").lower() == "true":
        a.bos_ulke = True
    if not a.gun:
        _env_gun = os.environ.get("PRUVO_RUM_GUN", "").strip()
        if _env_gun:
            a.gun = _env_gun

    # KOL CAKISMASI: --ham + --bos-ulke AYNI ANDA kullanilamaz (ayri tablolara
    # yazan iki kol, tek CF istegi + tek D1 yazma atomikligi beklendigi icin).
    # Erken cik: herhangi bir hata kirilmadan once raporlanir, CI logunda
    # tek satir `RUM_VEKIL_BOS_ULKE=OLCULEMEDI sebep=KOL-CAKISMA`.
    if a.ham and a.bos_ulke:
        print("RUM_VEKIL_BOS_ULKE=OLCULEMEDI sebep=KOL-CAKISMA")
        return 3

    try:
        if a.bos_ulke:
            baslik = "RUM_VEKIL_BOS_ULKE"
        elif a.ham:
            baslik = "RUM_VEKIL_HAM"
        else:
            baslik = "RUM_VEKIL"
        if a.gun:
            try:
                gun_t = datetime.date.fromisoformat(a.gun)
            except ValueError as e:
                print("%s=OLCULEMEDI sebep=PENCERE-BICIMI" % baslik)
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
                print("%s=OLCULEMEDI sebep=JETON-YOK" % baslik)
                return 3
            if a.bos_ulke:
                grup = graphql_bos_ulke_yukle(gun, token, account_id)
            elif a.ham:
                grup = graphql_ham_yukle(gun, token, account_id)
            else:
                grup = graphql_yukle(gun, token, account_id)
            kaynak = "CF-RUM"

        vt = vt_ac(a.vt)
        try:
            d1 = _d1_modulu() if a.vt is None else _YerelQ()
            q_fn = d1.q
        except Exception as e:
            raise Olculemedi("D1-MODULU-YOK", "d1-sync yuklenemedi: %s" % str(e)[:200])
        if a.bos_ulke:
            satirlar = bos_ulke_satirlari(grup)
            sql = yazma_bos_ulke_sql(gun, satirlar, q_fn)
        elif a.ham:
            satirlar = ham_satirlari(grup)
            sql = yazma_ham_sql(gun, satirlar, q_fn)
        else:
            toplamlar = siniflara_ayir(grup)
            sql = yazma_sql(gun, toplamlar, q_fn)
        try:
            vt.calistir(sql)
        except Olculemedi:
            raise
        except Exception as e:
            raise Olculemedi("D1-YAZIM-HATASI", "yazim basarisiz: %s" % str(e)[:200])
        # Basarili: TEK satir, sayi YOK (gun disinda HICBIR rakam dizgesi).
        print("%s=YAZILDI gun=%s" % (baslik, gun))
        return 0
    except Olculemedi as x:
        # Sebep jetonu disinda HICBIR sey basma; hesap/token sizintisi YASAK.
        sys.stderr.write("%s=OLCULEMEDI sebep=%s\n" % (baslik, x.jeton))
        print("%s=OLCULEMEDI sebep=%s" % (baslik, x.jeton))
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