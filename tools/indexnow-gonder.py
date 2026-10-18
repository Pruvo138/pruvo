#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INDEXNOW — sitemap.xml'in ESKI + YENI halini karsilastirip farki tek POST ile
IndexNow'a bildiren arac. ESKI sitemap SUREKLI yoldan (yerel dosya) gelir; canli onceki
sitemap ya da `--hazirla` ile indirilmis dosya kullanilir (CI'da sitemap.xml git'e
GIRMEZ; onceki tasarimdaki git gecmisi kuyrugu tek denek olarak hep dustu).

Kullanim:
    python3 tools/indexnow-gonder.py --eski <yol> --yeni <yol>
    python3 tools/indexnow-gonder.py --eski eski.xml --yeni yeni.xml --kuru
    python3 tools/indexnow-gonder.py --hazirla _indexnow/

iki ayri kol — birbirini dislar:

  A) ESKI/YENI KARSILASTIRMA + POST (varsayilan):
     --eski <yol>  ESKI sitemap.xml yolu (XML olmazsa rc=3)
     --yeni <yol>  YENI sitemap.xml yolu (XML olmazsa rc=3)
     ikisi zorunlu. Fark listesi = ekle ∪ kaldir ∪ lastmod-degisen, https://pruvo3d.com/
     onekli, sirali, tekil. 10.000'lik parcalarla POST.

  B) HAZIRLA (build isinden, deploy ONCESI):
     --hazirla <dizin>  DIZIN yoksa olustur; canli sitemap'i indir -> <dizin>/eski.xml,
                       ./sitemap.xml'i -> <dizin>/yeni.xml olarak kopyala.
                       Hata OLSA bile rc=0 (build'i ASLA dusurmez).
                       Tek satir:
                         INDEXNOW_HAZIRLA=TAMAM   ikisi de yazildi
                         INDEXNOW_HAZIRLA=ESKI-YOK  indirme dustu (eski.xml yazilmaz)
                         INDEXNOW_HAZIRLA=YENI-YOK  ./sitemap.xml yok/kopya basarisiz
                       Indirme adresi PRUVO_INDEXNOW_SITEMAP_UC ile degistirilebilir
                       (vars. https://pruvo3d.com/sitemap.xml). YALNIZ `http://127.0.0.1:`
                       onekiyse (test); baska deger -> ESKI-YOK, aga cikMAZ, rc=0.

CIKTI (A kolu, TEK SATIR):
    INDEXNOW=<n> URL http=<kod>                   n>0, 200/202 -> rc=0
    INDEXNOW=0 URL                                fark yok      -> rc=0, POST YOK
    INDEXNOW_KURU=<n> URL                         --kuru        -> rc=0, POST YOK
    INDEXNOW=OLCULEMEDI sebep=<sebep>             olcum yok     -> rc=3

HATA rc'leri:
    rc=2  PRUVO_INDEXNOW_UC `http://127.0.0.1:` oneki DEGIL (guisiz override REDDEDILIR)
          (hicbir POST yapilmaz; cikti INDEXNOW=OLCULEMEDI sebep=BICIM)
    rc=3  ESKI-SITEMAP  --eski yok/okunamadi/bozuk XML
          YENI-SITEMAP  --yeni yok/okunamadi/bozuk XML
          HTTP-<kod>    IndexNow 200/202 DISINDA kodla yanitladi
          AG            ag hatasi (DNS, baglanti kesildi, vb.)
          XML           sitemap ayristirilamadi

Liste = YENI eklenen loc ∪ KALDIRILAN loc ∪ lastmod'u DEĞİŞEN loc; yalnizca
https://pruvo3d.com/ onekli; sirali, tekil. 10.000'lik parcalarla POST edilir
(IndexNow tek istekteki URL tavaninı).
"""
import argparse
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True                            # hedef repoya __pycache__ yazma

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)

# IndexNow sabitleri — anahtar tasarım gereği HALKA AÇIK (sır degildir), anahtar dosyasi
# da kok meta olarak yayina girer. Bu uc SABIT yayin topolojisine BAGLI: site URL'si,
# anahtar degeri ve anahtar dosyasi adi uc ayri yerde degistirilirse POST hedeften sapar.
HOST = "pruvo3d.com"
SITE_ONEK = "https://" + HOST + "/"
ANAHTAR = "pruvo3d-indexnow-anahtari-17eki"
ANAHTAR_DOSYA = ANAHTAR + ".txt"
INDEXNOW_UC_VARSAYILAN = "https://api.indexnow.org/indexnow"
INDEXNOW_UC_TEST_ONEK = "http://127.0.0.1:"
SITEMAP_UC_VARSAYILAN = "https://pruvo3d.com/sitemap.xml"
SITEMAP_UC_TEST_ONEK = "http://127.0.0.1:"
PARCA_TAVAN = 10000
HAZIRLA_TIMEOUT_SN = 30
HAZIRLA_DENEME_SAYISI = 2
# 🔴 KIMLIKLI ISTEK (18 Eki, olculdu): urllib'in varsayilan `Python-urllib/3.x` kimligi
# canli sitemap'te HTTP 403 yiyor (CI koşucusu VE yerel ag — IP degil kimlik engeli);
# ilk main yayininda `INDEXNOW_HAZIRLA=ESKI-YOK` -> indexnow isi rc=3. Acik, sahibini
# soyleyen bir kimlik gonderilir (tarayici taklidi DEGIL).
ISTEK_KIMLIGI = "PruvoIndexNow/1.0 (+https://pruvo3d.com/)"


def _hata(mesaj):
    """Tek satirlik OLCULEMEDI ciktisi -> rc=3. CI'da gorunurluk icin."""
    sys.stdout.write("INDEXNOW=OLCULEMEDI sebep=%s\n" % mesaj)
    return 3


def _uc_kontrol():
    """PRUVO_INDEXNOW_UC guvenli mi? -> (uc, gecerli_mi).

    Yalniz `http://127.0.0.1:` oneki (yerel stub kolu); baska her sey REDDEDILIR
    (rc=2). None ise varsayilan uca doner."""
    aday = os.environ.get("PRUVO_INDEXNOW_UC")
    if aday is None:
        return INDEXNOW_UC_VARSAYILAN, True
    if aday.startswith(INDEXNOW_UC_TEST_ONEK):
        return aday, True
    return aday, False


def _sitemap_uc_kontrol():
    """PRUVO_INDEXNOW_SITEMAP_UC guvenli mi? -> (uc, gecerli_mi).

    Yalniz `http://127.0.0.1:` oneki (test); canliya karisik env ile gidemez.
    Bos/None ise varsayilan canli uca doner. `--hazirla` her durumda rc=0; gecersiz
    override ise gecici dosya YAZMAZ, `INDEXNOW_HAZIRLA=ESKI-YOK` basar, aga
    CIKMAZ."""
    aday = os.environ.get("PRUVO_INDEXNOW_SITEMAP_UC")
    if aday is None or aday == "":
        return SITEMAP_UC_VARSAYILAN, True
    if aday.startswith(SITEMAP_UC_TEST_ONEK):
        return aday, True
    return aday, False


def _indir(uc):
    """Sitemap URL'sini indir -> bytes. Timeout 30 sn, en fazla 2 deneme.

    Hata durumunda `None`. DNS/baglanti/timeout/HTTP>=400 hepsi ayni tasima gider
    (kullanici adina tekrarlanan istek sessiz kalmasin)."""
    son = None
    req = urllib.request.Request(uc, headers={"User-Agent": ISTEK_KIMLIGI})
    for _ in range(HAZIRLA_DENEME_SAYISI):
        try:
            with urllib.request.urlopen(req, timeout=HAZIRLA_TIMEOUT_SN) as r:
                return r.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            son = e
    sys.stderr.write("sitemap indirilemedi: %s\n" % (son or "?"))
    return None


def _oku_sitemap(yol):
    """XML dosyasinin icerigi -> {loc: lastmod} sozluk. lastmod yoksa ''.

    ElementTree standart, stdlib disinda bagimlilik yok."""
    with open(yol, "rb") as f:
        govde = f.read()
    kok = ET.fromstring(govde)
    out = {}
    # Gercek sitemap `xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"` tasir; etiketler
    # `{ns}url` olur. Namespace'siz `findall("url")` 43 bin URL'lik sitemap'te 0 buluyordu
    # (17 Eki olculdu) -> etiket YEREL ADIYLA eslenir.
    for url in kok:
        if _yerel_ad(url.tag) != "url":
            continue
        alan = {_yerel_ad(c.tag): (c.text or "").strip() for c in url}
        loc = alan.get("loc", "")
        if not loc:
            continue
        out[loc] = alan.get("lastmod", "")
    return out


def _yerel_ad(etiket):
    """`{ns}url` -> `url`; namespace'siz etiket aynen."""
    return etiket.rsplit("}", 1)[-1] if isinstance(etiket, str) else ""


def _fark_listesi(eski, yeni):
    """Iki {url: lastmod} sozlugunun farki -> sirali, tekillestirilmis URL listesi.

    Semantik: ekle ∪ kaldir ∪ lastmod-degisti; pruvo3d.com disindaki URL'ler dustu
    (yabanci site / arsiv / cdg vb. POST'a GIRMEZ — IndexNow'da pruvo3d.com hesap
    tarafindan YETKILENDIRILDI). Cikti sirali (test deterministikligi) ve tekil
    (sozluk zaten tekil; iki sozlugun ortak kesisimi de tekil)."""
    set_eski, set_yeni = set(eski), set(yeni)
    fark = (set_yeni - set_eski) | (set_eski - set_yeni)
    fark |= {u for u in (set_eski & set_yeni) if eski[u] != yeni[u]}
    return sorted(u for u in fark if u.startswith(SITE_ONEK))


def _post_parca(uc, url_list):
    """Tek parca (en fazla PARCA_TAVAN URL) -> (http_kod, ham_yanit).

    200/202 BASARI; diger kodlar HATA. Baglanti/timeout da HATA. JSON govde."""
    govde = json.dumps({
        "host": HOST, "key": ANAHTAR,
        "keyLocation": SITE_ONEK + ANAHTAR_DOSYA,
        "urlList": url_list,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(uc, data=govde, method="POST",
                                headers={"Content-Type": "application/json; charset=utf-8",
                                         "User-Agent": ISTEK_KIMLIGI})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, b""


# ──────────────────────────────────────────────────────────────────────────────
# KOLLAR
# ──────────────────────────────────────────────────────────────────────────────
def kol_hazirla(dizin):
    """Build isinden ONCE kosar; ciktiyi <dizin>/eski.xml + <dizin>/yeni.xml yazar.

    `INDEXNOW_HAZIRLA=` tek satir cikti + rc=0 (build'i ASLA dusurmez)."""
    try:
        os.makedirs(dizin, exist_ok=True)
    except OSError as e:
        sys.stdout.write("INDEXNOW_HAZIRLA=ESKI-YOK\n")
        sys.stderr.write("dizin olusturulamadi: %s\n" % e)
        return 0

    # 1) YENI: ./sitemap.xml -> <dizin>/yeni.xml
    yerel = os.path.join(KOK, "sitemap.xml")
    yeni_hedef = os.path.join(dizin, "yeni.xml")
    yeni_ok = False
    if os.path.isfile(yerel):
        try:
            shutil.copyfile(yerel, yeni_hedef)
            yeni_ok = True
        except OSError as e:
            sys.stderr.write("sitemap.xml kopyalanamadi: %s\n" % e)

    # 2) ESKI: PRUVO_INDEXNOW_SITEMAP_UC (guvenli ise) -> <dizin>/eski.xml
    uc, uc_ok = _sitemap_uc_kontrol()
    eski_ok = False
    if uc_ok:
        govde = _indir(uc)
        if govde:
            try:
                # indirilen baytin GECERLI XML oldugunu onayla; degilse DOSYA YAZMA —
                # arindirilamayan icerigi A/B test kolu olarak bile yayinlamayiz.
                ET.fromstring(govde)
            except ET.ParseError as e:
                sys.stderr.write("indirilen sitemap XML degil: %s\n" % e)
            else:
                try:
                    with open(os.path.join(dizin, "eski.xml"), "wb") as f:
                        f.write(govde)
                    eski_ok = True
                except OSError as e:
                    sys.stderr.write("eski.xml yazilamadi: %s\n" % e)

    if eski_ok and yeni_ok:
        sys.stdout.write("INDEXNOW_HAZIRLA=TAMAM\n")
    elif not yeni_ok:
        sys.stdout.write("INDEXNOW_HAZIRLA=YENI-YOK\n")
    else:
        sys.stdout.write("INDEXNOW_HAZIRLA=ESKI-YOK\n")
    return 0


def kol_karsilastir_post(args):
    """ESKI + YENI dosyadan farki hesapla; gerekirse POST et."""
    # 0. Uc override kontrolu (PRUVO_INDEXNOW_UC) -> gecersiz override rc=2.
    uc, uc_ok = _uc_kontrol()
    if not uc_ok:
        sys.stdout.write("INDEXNOW=OLCULEMEDI sebep=BICIM\n")
        return 2

    # 1. Yeni sitemap diskten oku (YOK/bozuk XML -> rc=3).
    if not os.path.isfile(args.yeni):
        return _hata("YENI-SITEMAP")
    try:
        yeni = _oku_sitemap(args.yeni)
    except (ET.ParseError, OSError):
        return _hata("XML")
    # Sitenin sitemap'i ASLA bos degildir: 0 URL = ayristirici/uretim kusuru, "fark yok"
    # sanilip sessizce INDEXNOW=0 basilmaz (17 Eki namespace vakasi).
    if not yeni:
        return _hata("YENI-BOS")

    # 2. Eski sitemap dosyadan oku (YOK/bozuk XML -> rc=3).
    if not os.path.isfile(args.eski):
        return _hata("ESKI-SITEMAP")
    try:
        eski = _oku_sitemap(args.eski)
    except (ET.ParseError, OSError):
        return _hata("XML")

    # 3. Fark listesi (sirali, tekil, SITE_ONEK'le sinirli).
    url_listesi = _fark_listesi(eski, yeni)

    # 4. Bos -> POST yok.
    if not url_listesi:
        sys.stdout.write("INDEXNOW=0 URL\n")
        return 0

    # 5. --kuru -> POST yok; sadece say.
    if args.kuru:
        sys.stdout.write("INDEXNOW_KURU=%d URL\n" % len(url_listesi))
        return 0

    # 6. POST (parcalara bolunerek; PARCA_TAVAN = 10.000).
    toplam = 0
    son_kod = None
    for i in range(0, len(url_listesi), PARCA_TAVAN):
        parca = url_listesi[i:i + PARCA_TAVAN]
        kod, _ = _post_parca(uc, parca)
        son_kod = kod
        if kod in (200, 202):
            toplam += len(parca)
            continue
        if kod is None:
            return _hata("AG")
        return _hata("HTTP-%d" % kod)
    sys.stdout.write("INDEXNOW=%d URL http=%d\n" % (toplam, son_kod))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--eski", default=None,
                    help="ESKI sitemap.xml yolu (zorunlu, --hazirla yoksa)")
    ap.add_argument("--yeni", default=None,
                    help="YENI sitemap.xml yolu (zorunlu, --hazirla yoksa)")
    ap.add_argument("--kuru", action="store_true",
                    help="POST yok; sadece URL sayisini bas")
    ap.add_argument("--hazirla", default=None, metavar="DIZIN",
                    help="Build isinden: canli sitemap'i indir + ./sitemap.xml kopyala -> <DIZIN>/eski.xml + <DIZIN>/yeni.xml; rc=0")
    args = ap.parse_args()

    # Kol secimi: --hazirla ise yalnizca hazirla; degilse karsilastir+POST.
    if args.hazirla:
        return kol_hazirla(args.hazirla)

    # Karsilastirma kolu: --eski ve --yeni zorunlu.
    if not args.eski or not args.yeni:
        sys.stderr.write("--eski ve --yeni zorunlu (ya da --hazirla <dizin>)\n")
        return 2
    return kol_karsilastir_post(args)


if __name__ == "__main__":
    sys.exit(main())
