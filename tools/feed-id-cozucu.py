#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""feed-id-cozucu.py — SALT-OKUNUR tanilama araci: Merchant feed g:id -> GERCEK urun id.

NEDEN VAR (olculdu, 22 Tem):
  Merchant panelinden gelen sikayetlerde ("urun sayfasi kullanilamiyor", politika reddi)
  urun, feed'deki <g:id> ile anilir. build.feed_id() Google'in 50 KARAKTER sinirini
  uygulamak icin uzun urun id'lerini KISALTIR: ilk 41 karakter + '-' + sha1(pid)[:8].
  Bu kisaltilmis kimlik urunler.json'da YOKTUR -> panel kimligini katalogda arayan
  (ArTisT/Okan/mimar) "boyle bir urun yok / sayfa 404" sonucuna varir. Yasanmis vaka:
    citroen-jumpy-expert-scudo-uyumlu-ekran-t-7f10ac01   (feed g:id, 50 krk)
      -> gercek id: citroen-jumpy-expert-scudo-uyumlu-ekran-tutucu-aparat   (canli 200)
  Tanilama koru buydu; bu arac onu kalici olarak kapatir.

NE YAPAR: verilen her kimligi (g:id VEYA gercek urun id) cozer ve basar:
  gercek urun id · baslik · canli URL · feed'de var mi · parametrik mi · (istege bagli) HTTP kodu.

AGA CIKMAZ (varsayilan). HTTP kodu YALNIZ --canli bayragiyla olculur; bayraksiz kosumda
"HTTP" sutunu "-" basar (olculmedi, TAHMIN EDILMEZ).

KAPI DEGIL: hicbir sey bloklamaz, cikis kodu yalniz "hepsi cozuldu mu"yu bildirir
(0 = hepsi cozuldu, 1 = en az biri cozulemedi, 2 = kullanim hatasi).

Kullanim:
  python3 tools/feed-id-cozucu.py citroen-jumpy-expert-scudo-uyumlu-ekran-t-7f10ac01
  python3 tools/feed-id-cozucu.py <gid1> <gid2> --canli
  python3 tools/feed-id-cozucu.py <gid> --json

Modul olarak:
  from importlib ... ; mod.coz(["<gid>"])  ->  [{'girdi','id','baslik','url','feedde','parametrik'}, ...]
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# build.py MODUL olarak import edilir (komut olarak KOSTURULMAZ: build.py main()'i
# izlenen 4 statik sayfayi YERINDE yeniden yazar -> calisma agacini kirletir).
import build  # noqa: E402


def urunleri_yukle(yol=None):
    with open(yol or build.JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def feed_gid_kumesi(products):
    """Feed'i GERCEKTEN uretip icindeki <g:id> degerlerini dondurur.

    'feed'de var mi' sorusunu TAHMIN etmez (parametrik/fiyat/gorsel elemelerini burada
    yeniden yazsaydik build.py degistiginde sessizce sapardi) -> render_merchant_feed'in
    kendi ciktisini okur."""
    xml, _n = build.render_merchant_feed(products)
    return set(re.findall(r"<g:id>(.*?)</g:id>", xml))


def harita(products):
    """feed g:id -> urun  VE  gercek id -> urun (ikisi de tek sozlukte).
    Cakisma olmaz: feed_id kisa id'yi AYNEN dondurur, uzun id icin uretilen 50-karakterlik
    kimlik sha1 ekiyle benzersizdir (bkz tools/test-merchant-feed.py b sikki)."""
    h = {}
    for p in products:
        pid = p.get("id")
        if not pid:
            continue
        h[pid] = p
        h[build.feed_id(pid)] = p
    return h


def http_kodu(url, zaman_asimi=15):
    """Canli HTTP durum kodu (yalniz --canli). Olculemezse None dondurur (TAHMIN YOK)."""
    import urllib.error
    import urllib.request
    istek = urllib.request.Request(url, method="GET", headers={"User-Agent": "pruvo-feed-id-cozucu"})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
            return r.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def coz(kimlikler, products=None, canli=False):
    """Her kimlik icin cozum kaydi dondurur (ag'a yalniz canli=True ise cikar)."""
    products = products if products is not None else urunleri_yukle()
    h = harita(products)
    gidler = feed_gid_kumesi(products)
    sonuc = []
    for k in kimlikler:
        p = h.get(k)
        kayit = {"girdi": k, "id": None, "baslik": None, "url": None,
                 "feedde": None, "parametrik": None, "http": None,
                 "kisaltilmis": None}
        if p is None:
            sonuc.append(kayit)
            continue
        pid = p["id"]
        kayit["id"] = pid
        kayit["baslik"] = p.get("baslik") or ""
        kayit["url"] = build.product_url(pid)
        kayit["parametrik"] = bool(p.get("parametrik"))
        kayit["feedde"] = build.feed_id(pid) in gidler
        kayit["kisaltilmis"] = (build.feed_id(pid) != pid)
        if canli:
            kayit["http"] = http_kodu(kayit["url"])
        sonuc.append(kayit)
    return sonuc


def main():
    ap = argparse.ArgumentParser(description="Merchant feed g:id -> gercek urun id cozucu (salt-okunur)")
    ap.add_argument("kimlikler", nargs="*", help="feed g:id ya da gercek urun id")
    ap.add_argument("--canli", action="store_true", help="canli URL'in HTTP kodunu OLC (ag'a cikar)")
    ap.add_argument("--json", action="store_true", help="cikti JSON")
    ap.add_argument("--urunler", help="alternatif urunler.json yolu (test icin)")
    args = ap.parse_args()

    if not args.kimlikler:
        print("kimlik verilmedi. Ornek: python3 tools/feed-id-cozucu.py <g:id>", file=sys.stderr)
        return 2

    products = urunleri_yukle(args.urunler)
    kayitlar = coz(args.kimlikler, products, canli=args.canli)

    if args.json:
        print(json.dumps(kayitlar, ensure_ascii=False, indent=2))
    else:
        print("FEED g:id -> GERCEK URUN ID  (katalog: %d urun)" % len(products))
        print("-" * 78)
        for k in kayitlar:
            print("girdi     : %s" % k["girdi"])
            if k["id"] is None:
                print("  SONUC   : ❌ COZULEMEDI — ne feed g:id ne de urun id olarak katalogda yok")
                print("            (silinmis urun ya da baska bir katalog surumunden gelmis olabilir)")
                print("-" * 78)
                continue
            print("  urun id : %s%s" % (k["id"], "   (girdi KISALTILMIS feed kimligiydi)"
                                        if k["kisaltilmis"] and k["girdi"] != k["id"] else ""))
            print("  baslik  : %s" % k["baslik"])
            print("  URL     : %s" % k["url"])
            print("  feed'de : %s" % ("EVET" if k["feedde"] else "HAYIR (parametrik/fiyatsiz/gorselsiz)"))
            print("  parametrik: %s" % ("EVET" if k["parametrik"] else "hayir"))
            print("  HTTP    : %s" % (k["http"] if k["http"] is not None
                                      else ("OLCULEMEDI (ag hatasi)" if args.canli else "- (olculmedi; --canli ver)")))
            print("-" * 78)

    cozulemeyen = [k["girdi"] for k in kayitlar if k["id"] is None]
    if cozulemeyen:
        print("COZULEMEYEN: %d (%s)" % (len(cozulemeyen), ", ".join(cozulemeyen)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
