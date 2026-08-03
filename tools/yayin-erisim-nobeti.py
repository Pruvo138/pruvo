#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN ERISIM NOBETCISI — "yayinladigimiz sayfa CANLIDA GERCEKTEN ACIK MI?".

NEDEN VAR (3 Agu 2026, OLCULDU — bu nobetci bir olayin faturasidir)
====================================================================
UC landing sayfasi canlida **12 gun boyunca 403 Forbidden** dondu ve HICBIR NOBETCI
GORMEDI. Sebep bizim uretimimiz DEGILDI: kardes depodaki Worker rotasi
`pruvo3d.com/ara*` bir ONEK JOKERIDIR ve `araba-…` / `arac-…` ile baslayan slug'lari
yutup webhook catch-all'ina dusuruyordu (403, istek origin'e HIC ulasmiyordu).

O gun her kapi YESILDI:
  * dosyalar origin'de URETILDI  (deploy fail-closed kopyaladi, kosum success),
  * sitemap'te VARDI             (17.812 <loc> icinde ucu de),
  * 10 canli sayfadan 22 IC LINK onlara gidiyordu,
  * `_yayin-icerik-dizinleri.txt` beyaz-listesinde VARDI.
Musteri ve Googlebot ise KAPALI KAPIYA carpiyordu.

🔴 SINIF: yayinlanan icerigin URETILDIGI olculuyordu, ERISILEBILDIGI olculmuyordu.
Bu nobetci tam o bosluktadir: "depo/CI ne diyor" degil, "MUSTERI KAPIYI ACABILIYOR MU".

🔴 GET KULLANIR — HEAD YETMEZ (ayirt edici, o gun OLCULDU)
=========================================================
Ayni URL: `HEAD -> 200` · `GET -> 403`. Sebep worker kodunda `request.method === "GET"`
dalinin HEAD'i kapsamamasiydi. HEAD'e bakan bir nobetci bu kusuru **HIC GORMEZDI** ve
"290/290 acik" diye YESIL yanardi. Bu yuzden `YONTEM = "GET"` TEK KAYNAKTIR ve kabul
testi bunu FIKSTURLE (HEAD 200 / GET 403 uretn gercek bir HTTP sunucusu) nobetler;
`YONTEM`i "HEAD"e ceviren mutant kabul testini KIRMIZI yakar.

KUME NEREDEN TURER (elle liste YOK — elle liste CURUR)
======================================================
  K1  tools/sayfalar.py :: SITEMAP_SLUGS   (STATIK_SAYFALAR + CONTENT_PAGES slug'lari)
  K2  tools/landing_hub_build.py :: HUB_SLUG (landing hub dizini)
  K3  site KOKU "/" (ana sayfa; build.py render_sitemap'te de sabittir)
  K4  _yayin-icerik-dizinleri.txt — build'in URETTIGI deploy beyaz-listesi (VARSA;
      `marka` gibi ust dizinleri buradan alir). CI'da build kosmadan YOKTUR.
  K5  sitemap.xml — YEREL uretilmis kopya (VARSA): TEK SEGMENTLI (ust duzey) <loc>'lar.
K1 ve K2 ZORUNLUDUR: yuklenemezse hukum YOK -> OLCULEMEDI (rc 2). K4/K5 zenginlestirir;
yoksa kume kucuk kalir ama kaynak kaynak SAYIYLA basilir (sessiz daralma YASAK).

🔴 KUME TABANI (`KUME_TABANI`): turetilen kume tabandan kucukse OLCULEMEDI'dir.
Sebep: bos/collapsed bir kume uzerinde donen dongu HICBIR SEY olcmez ama "hepsi acik"
diye YESIL yanar — bu nobetcinin en ucuz oldurulme yoludur.

EKSEN SINIRI — IKINCI KOPYA ACILMAZ
===================================
  * `/urun/<id>/` sayfalari (bugun 17.028) BU ARACIN ISI DEGILDIR: onlar
    `tools/canli-saglik-kapisi.py` K2 ekseninindir (orneklemli, yeni urun odakli).
  * `/marka/...` sayfalari (bugun 487) varsayilan kapsamda DEGILDIR; `--kapsam marka`
    ya da `--kapsam tam` ile olculur ve kaynagi YEREL sitemap'tir (yoksa OLCULEMEDI —
    sessizce daraltilmaz).
  * Kapsam her kosumda BASILIR; "hepsi yesil" cumlesi kapsam sayisi OLMADAN kurulmaz.

HUKUM
=====
  ACIK        her URL 200 (ya da yonlendirme zinciri 200'de bitiyor).
  KAPALI      en az bir URL 200 disi / dongu / zincir tavani asildi  -> rc 1.
  OLCULEMEDI  ag/DNS/zaman asimi/kaynak yuklenemedi/kume tabanin altinda -> rc 2.
Yonlendirme zinciri 200'de bitiyorsa SAPMA DEGILDIR (rapora AYRI satir olarak yazilir:
sitemap kanonik URL vermeli, ama musteri kapiyi acabiliyor).

🔴 FAIL-CLOSED: olculemeyen sey ASLA yesil sayilmaz. Ag yoksa, DNS cozmuyorsa, zaman
asimi olduysa ya da oran sinirina takildiysak rc 2'dir — "hepsi 200" VARSAYILMAZ.
🔴 SAPMA KANITI OLCUM ARIZASINI EZER: elimizde zaten KAPALI bir kapi varken arac
"olculemedi"ye dusmez (kanit kaybolmasin); iki hal de raporda AYRI AYRI sayilir.

NEREYE BAGLIDIR (gerekce: yanlis-pozitif TUM EKIBIN yayinini durdurur)
======================================================================
  * CANLI olcum kolu `deploy.yml`'e BAGLANMAZ. `deploy` YALNIZ `build`'e baglidir;
    aga bagimli bir kapiyi oraya koymak, tek gecici DNS hatasinda yayini durdururdu
    ([[kapi-kapsam-eksen-secimi]], [[kapi-birikimi-yayin-gecikmesi]]).
  * CANLI kol AYRI ve SEYREK kosan bir ALARM KOLUNDADIR:
    `.github/workflows/yayin-erisim-alarmi.yml` (saatlik cron, `push` tetikleyicisi YOK,
    ayri `concurrency` grubu, `continue-on-error` YOK). Ayni desen 1 Agu'da paket
    tazeligi alarmi icin secildi ve kosuyor.
  * `deploy.yml`'de YALNIZ bu dosyanin AGSIZ/YEREL fikstur kabulu kosar
    (`tools/yayin-erisim-test.py`, serit B — beyan: tools/is-akisi-kapisi.py :: SERIT_B).

MALIYET
=======
Varsayilan kapsam bugun 295-296 URL. Istek hizi `--hiz` (istek/sn) ile SINIRLIDIR ve
toplam sure her kosumda OLCULUP BASILIR. ORNEKLEME YOKTUR: kume kirpilmaz; pahali
gelirse cadans seyreltilir (cron), kume degil.

KULLANIM
========
    python3 tools/yayin-erisim-nobeti.py                  # canli olcum (ag ISTER)
    python3 tools/yayin-erisim-nobeti.py --kapsam tam     # + /marka sayfalari (yerel sitemap)
    python3 tools/yayin-erisim-nobeti.py --liste          # yalniz kumeyi bas (AG YOK)
    python3 tools/yayin-erisim-nobeti.py --json           # makine okunur
    python3 tools/yayin-erisim-nobeti.py --gh-ozet        # GitHub kosum ozeti + output
    python3 tools/yayin-erisim-nobeti.py --kendini-test   # YEREL fikstur sunucusu kabulu
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

SITE_VARSAYILAN = "https://pruvo3d.com"

# 🔴 TEK KAYNAK — ISTEK YONTEMI. "HEAD" yapan her mutant kabul testini KIRMIZI yakar:
# 3 Agu 2026'da olculen kusurda ayni URL HEAD'e 200, GET'e 403 donuyordu.
YONTEM = "GET"

# 200 DISI HER SEY KAPALIDIR. Bu demet genisletilirse (or. 403/404 "acik" sayilirsa)
# nobetci tam da dogdugu kusuru gormez -> kabul testi KIRMIZI yanar.
ACIK_KODLAR = (200,)

# R2/edge urllib UA 403 dersi ([[r2-urllib-ua-403-tuzagi]]): ciplak `Python-urllib` UA'si
# Cloudflare tarafindan bot sayilip 403 yiyebilir -> nobetci TUM sayfalari "kapali"
# sanip yanlis alarm verirdi. Tarayici UA'si ZORUNLUDUR.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

ZAMAN_ASIMI_VARSAYILAN = 20.0
# Istek hizi (istek/sn). Sayfa istekleri statik CDN'e gider (worker oran siniri DEGIL);
# yine de uc nazikce kullanilir: 6/sn -> ~296 URL ~50 sn.
HIZ_VARSAYILAN = 6.0
YONLENDIRME_TAVANI = 5

# Kume tabani: bugun K1 tek basina 293 uretiyor. Taban ALTINA dusen bir kume "olculemedi"
# demektir (kaynak bozuldu / bos dondu), "her sey acik" DEMEK DEGILDIR.
KUME_TABANI = 250

SINIF_RC = {"ACIK": 0, "KAPALI": 1, "OLCULEMEDI": 2}
DURUM_ETIKET = {"ACIK": "acik", "KAPALI": "kapali", "OLCULEMEDI": "olculemedi"}

KAPSAMLAR = ("sayfa", "marka", "tam")


class OlcumHatasi(Exception):
    """Olculemedi -> YESIL degil, rc 2."""


# =========================================================== KUME (KAYNAK KATMANI)
def _modul(ad, yol):
    if not os.path.exists(yol):
        raise OlcumHatasi("kaynak dosya YOK: %s" % yol)
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    try:
        spec.loader.exec_module(m)
    except Exception as e:                                  # noqa: BLE001
        raise OlcumHatasi("%s yuklenemedi (%s: %s)" % (os.path.basename(yol),
                                                       type(e).__name__, e))
    return m


def _yol(slug):
    """slug -> '/slug/' (kok icin '/')."""
    s = (slug or "").strip().strip("/")
    return "/" if not s else "/%s/" % s


def kume_turet(kok=ROOT, kapsam="sayfa"):
    """(yollar, kaynaklar) — yollar sirali '/...' listesi; kaynaklar beyan tablosu.

    Elle yazilmis URL listesi YOKTUR: her yol bir KAYNAKTAN turer ve hangi kaynagin kac
    yol verdigi rapora basilir. K1/K2 ZORUNLU (yuklenemezse OlcumHatasi = rc 2)."""
    if kapsam not in KAPSAMLAR:
        raise OlcumHatasi("bilinmeyen kapsam %r (izinli: %s)" % (kapsam,
                                                                 ", ".join(KAPSAMLAR)))
    kaynaklar = []
    sayfa = []

    if kapsam in ("sayfa", "tam"):
        sayfalar = _modul("pruvo_sayfalar", os.path.join(kok, "tools", "sayfalar.py"))
        slugler = list(getattr(sayfalar, "SITEMAP_SLUGS", []) or [])
        if not slugler:
            raise OlcumHatasi("sayfalar.py::SITEMAP_SLUGS BOS -> olculecek sayfa yok "
                              "(kaynak bozuk; bos kume 'hepsi acik' DEMEK DEGILDIR)")
        k1 = [_yol(s) for s in slugler]
        kaynaklar.append(("K1 sayfalar.py::SITEMAP_SLUGS", len(k1), True, ""))
        sayfa += k1

        hub = _modul("pruvo_landing_hub", os.path.join(kok, "tools",
                                                       "landing_hub_build.py"))
        hub_slug = getattr(hub, "HUB_SLUG", None)
        if not hub_slug:
            raise OlcumHatasi("landing_hub_build.py::HUB_SLUG BOS -> hub dizini "
                              "olculemez")
        kaynaklar.append(("K2 landing_hub_build.py::HUB_SLUG", 1, True, hub_slug))
        sayfa.append(_yol(hub_slug))

        kaynaklar.append(("K3 site koku (ana sayfa)", 1, True, "/"))
        sayfa.append("/")

        man = os.path.join(kok, "_yayin-icerik-dizinleri.txt")
        if os.path.exists(man):
            with open(man, encoding="utf-8") as f:
                satirlar = [s.strip() for s in f if s.strip()]
            k4 = [_yol(s) for s in satirlar]
            yeni = len(set(k4) - set(sayfa))
            kaynaklar.append(("K4 _yayin-icerik-dizinleri.txt (build manifesti)",
                              len(k4), True, "%d yeni" % yeni))
            sayfa += k4
        else:
            kaynaklar.append(("K4 _yayin-icerik-dizinleri.txt (build manifesti)",
                              0, False, "dosya YOK (build kosmamis) — kume K1-K3'ten"))

    sitemap_yol = os.path.join(kok, "sitemap.xml")
    sitemap_var = os.path.exists(sitemap_yol)
    ust, marka = [], []
    if sitemap_var:
        with open(sitemap_yol, encoding="utf-8") as f:
            ham = f.read()
        for u in re.findall(r"<loc>([^<]+)</loc>", ham):
            p = urllib.parse.urlsplit(u.strip()).path or "/"
            if p.startswith("/marka/"):
                marka.append(p)
            elif p.startswith("/urun/"):
                continue                       # EKSEN SINIRI: canli-saglik-kapisi K2
            elif p.count("/") <= 2:
                ust.append(p)

    if kapsam in ("sayfa", "tam"):
        if sitemap_var:
            yeni = len(set(ust) - set(sayfa))
            kaynaklar.append(("K5 sitemap.xml (yerel, ust duzey)", len(ust), True,
                              "%d yeni" % yeni))
            sayfa += ust
        else:
            kaynaklar.append(("K5 sitemap.xml (yerel, ust duzey)", 0, False,
                              "dosya YOK (build kosmamis)"))

    yollar = list(sayfa)
    if kapsam in ("marka", "tam"):
        if not sitemap_var:
            raise OlcumHatasi("--kapsam %s YEREL sitemap.xml ISTER (marka sayfalarinin "
                              "tek kaynagi odur) ama dosya YOK -> kume sessizce "
                              "daraltilmaz, OLCULEMEDI" % kapsam)
        kaynaklar.append(("K6 sitemap.xml (yerel, /marka/)", len(marka), True, ""))
        yollar += marka

    benzersiz = sorted(set(yollar))
    if len(benzersiz) < KUME_TABANI and kapsam != "marka":
        raise OlcumHatasi("turetilen kume %d URL — TABAN %d'in ALTINDA. Collapsed bir "
                          "kume hicbir sey olcmez ama 'hepsi acik' diye yesil yanardi."
                          % (len(benzersiz), KUME_TABANI))
    return benzersiz, kaynaklar


# =========================================================== OLCUM (AG KATMANI)
class _YonlendirmeYok(urllib.request.HTTPRedirectHandler):
    """Otomatik yonlendirme KAPALI: zinciri KENDIMIZ gezeriz (nereye gittigi + dongu
    olculsun diye). urllib'in kendi takibi zinciri GORUNMEZ kilardi."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ACICI = urllib.request.build_opener(_YonlendirmeYok())


def _istek(url, yontem=None, zaman_asimi=ZAMAN_ASIMI_VARSAYILAN, acici=None):
    """(kod|None, basliklar, govde_ilk_baytlari, hata|None). ASLA istisna atmaz."""
    yontem = yontem or YONTEM
    istek = urllib.request.Request(url, method=yontem,
                                   headers={"User-Agent": UA,
                                            "Accept": "text/html,application/xhtml+xml,"
                                                      "application/xml;q=0.9,*/*;q=0.8"})
    acici = acici or _ACICI
    try:
        with acici.open(istek, timeout=zaman_asimi) as y:
            return y.status, {k.lower(): v for k, v in y.headers.items()}, \
                y.read(4096), None
    except urllib.error.HTTPError as e:
        try:
            ham = e.read(4096)
        except Exception:                                   # noqa: BLE001
            ham = b""
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, ham, None
    except Exception as e:                                  # ag / DNS / TLS / timeout
        return None, {}, b"", "%s: %s" % (type(e).__name__, e)


def _govde_ozeti(ham):
    metin = (ham or b"")[:80].decode("utf-8", "replace")
    metin = re.sub(r"\s+", " ", metin).strip()
    return "".join(c for c in metin if c.isprintable())[:60]


def olc_tek(taban, yol, zaman_asimi=ZAMAN_ASIMI_VARSAYILAN, acici=None, yontem=None):
    """TEK URL'in canli hali. Doner: kayit sozlugu.

    sinif: ACIK | YONLENDI | KAPALI | DONGU | ARIZA
    """
    url = taban.rstrip("/") + yol
    zincir = []
    gorulen = set()
    suanki = url
    for _adim in range(YONLENDIRME_TAVANI + 1):
        if suanki in gorulen:
            return {"yol": yol, "url": url, "sinif": "DONGU", "kod": None,
                    "zincir": zincir, "tani": "yonlendirme DONGUSU: %s tekrar ediyor"
                                              % suanki, "govde": ""}
        gorulen.add(suanki)
        kod, basliklar, govde, hata = _istek(suanki, yontem=yontem,
                                             zaman_asimi=zaman_asimi, acici=acici)
        if hata:
            return {"yol": yol, "url": url, "sinif": "ARIZA", "kod": None,
                    "zincir": zincir, "tani": hata[:160], "govde": ""}
        if kod in ACIK_KODLAR:
            return {"yol": yol, "url": url,
                    "sinif": "ACIK" if not zincir else "YONLENDI",
                    "kod": kod, "zincir": zincir, "tani": "", "govde": ""}
        if 300 <= (kod or 0) < 400:
            hedef = basliklar.get("location")
            if not hedef:
                return {"yol": yol, "url": url, "sinif": "KAPALI", "kod": kod,
                        "zincir": zincir,
                        "tani": "%d yonlendirmesi `location` basligi TASIMIYOR" % kod,
                        "govde": ""}
            suanki = urllib.parse.urljoin(suanki, hedef)
            zincir.append((kod, suanki))
            continue
        tani = "HTTP %d" % kod
        for b in ("server", "cf-mitigated", "cf-cache-status", "content-type", "age"):
            if basliklar.get(b):
                tani += " · %s=%s" % (b, basliklar[b][:40])
        return {"yol": yol, "url": url, "sinif": "KAPALI", "kod": kod,
                "zincir": zincir, "tani": tani, "govde": _govde_ozeti(govde)}
    return {"yol": yol, "url": url, "sinif": "DONGU", "kod": None, "zincir": zincir,
            "tani": "yonlendirme zinciri %d adimi asti" % YONLENDIRME_TAVANI,
            "govde": ""}


def olc(yollar, taban=SITE_VARSAYILAN, hiz=HIZ_VARSAYILAN,
        zaman_asimi=ZAMAN_ASIMI_VARSAYILAN, acici=None, yontem=None, uyu=time.sleep):
    """Kumenin TAMAMINI olcer (ORNEKLEME YOK). Doner: (kayitlar, sure_sn).

    `hiz` istek/sn tavanidir: istekler arasi en az 1/hiz saniye beklenir. Sure OLCULUR
    ve rapora basilir (butce karari sayiyla verilsin diye)."""
    bekleme = (1.0 / hiz) if hiz and hiz > 0 else 0.0
    kayitlar = []
    bas = time.monotonic()
    for i, yol in enumerate(yollar):
        if i and bekleme:
            uyu(bekleme)
        kayitlar.append(olc_tek(taban, yol, zaman_asimi=zaman_asimi, acici=acici,
                                yontem=yontem))
    return kayitlar, time.monotonic() - bas


# =========================================================== HUKUM (SAF)
def degerlendir(kayitlar, kume_sayisi=None):
    """(sinif, rc, satirlar, ozet) — AG YOK, saf fonksiyon."""
    sayim = {"ACIK": 0, "YONLENDI": 0, "KAPALI": 0, "DONGU": 0, "ARIZA": 0}
    for k in kayitlar:
        sayim[k["sinif"]] = sayim.get(k["sinif"], 0) + 1
    kapali = [k for k in kayitlar if k["sinif"] in ("KAPALI", "DONGU")]
    ariza = [k for k in kayitlar if k["sinif"] == "ARIZA"]
    olculen = len(kayitlar)
    beklenen = kume_sayisi if kume_sayisi is not None else olculen

    satirlar = []
    ozet = {"olculen": olculen, "beklenen": beklenen, "sayim": sayim,
            "kapali": [{"yol": k["yol"], "kod": k["kod"], "tani": k["tani"],
                        "govde": k["govde"]} for k in kapali],
            "ariza": [{"yol": k["yol"], "tani": k["tani"]} for k in ariza],
            "yonlendirme": [{"yol": k["yol"], "zincir": k["zincir"]}
                            for k in kayitlar if k["sinif"] == "YONLENDI"]}

    if olculen != beklenen:
        satirlar.append("🔴 ORNEKLEM: kume %d URL ama %d olculdu — kirpilmis olcum "
                        "'hepsi acik' diye raporlanamaz." % (beklenen, olculen))
    if not olculen:
        satirlar.append("🔴 HIC URL OLCULMEDI -> hukum YOK (bos kume yesil DEGILDIR)")
        return "OLCULEMEDI", SINIF_RC["OLCULEMEDI"], satirlar, ozet

    for k in kapali:
        satirlar.append("🔴 KAPALI %s -> %s%s"
                        % (k["yol"], k["tani"],
                           ("  govde=%r" % k["govde"]) if k["govde"] else ""))
    for k in kayitlar:
        if k["sinif"] == "YONLENDI":
            satirlar.append("🟡 YONLENDIRME %s -> %s (zincir 200'de bitiyor; sapma "
                            "DEGIL ama sitemap kanonik URL vermeli)"
                            % (k["yol"], " -> ".join("%d %s" % z for z in k["zincir"])))
    for k in ariza:
        satirlar.append("⚪ OLCULEMEDI %s -> %s" % (k["yol"], k["tani"]))

    # SAPMA KANITI, OLCUM ARIZASINI EZER: elimizde kapali kapi varken "olculemedi"ye
    # dusmek kaniti kaybettirirdi. Iki hal de sayida AYRI AYRI gorunur.
    if kapali:
        satirlar.append("HUKUM: KAPALI — %d URL kapali/dongu, %d olcum arizasi, "
                        "%d acik (%d yonlendirmeli)."
                        % (len(kapali), len(ariza), sayim["ACIK"] + sayim["YONLENDI"],
                           sayim["YONLENDI"]))
        return "KAPALI", SINIF_RC["KAPALI"], satirlar, ozet
    if ariza or olculen != beklenen:
        satirlar.append("HUKUM: OLCULEMEDI — %d URL olculemedi (ag/DNS/zaman asimi). "
                        "Saglik KANITLANMADI; 'hepsi 200' VARSAYILMAZ." % len(ariza))
        return "OLCULEMEDI", SINIF_RC["OLCULEMEDI"], satirlar, ozet
    satirlar.append("HUKUM: ACIK — %d/%d URL 200 (%d yonlendirme zinciriyle)."
                    % (sayim["ACIK"] + sayim["YONLENDI"], beklenen, sayim["YONLENDI"]))
    return "ACIK", SINIF_RC["ACIK"], satirlar, ozet


# =========================================================== FIKSTUR (YEREL SUNUCU)
# 🔴 Fikstur GERCEK bir HTTP sunucusudur (gercek soket, gercek yanit satirlari), kendi
# varsayimimizi aynalayan bir simulator DEGIL ([[nobetci-fikstur-sekli]]). Govdeler
# 3 Agu 2026'da CANLIDAN olculen sekli tasir: worker 403'u 9 baytlik `Forbidden` düz
# metindir ve AYNI yol HEAD'e 200 doner.
FIKSTUR_YOLLARI = {
    "/acik-1/": "acik",
    "/acik-2/": "acik",
    # 🔴 AYIRT EDICI VAKA: GET 403 · HEAD 200 (3 Agu'da canlida olculen davranis).
    "/araba-guneslik-klipsi-yaptirma/": "get403-head200",
    # Kontrol: metoda DUYARSIZ 403 (WAF benzeri) — HEAD mutanti bunu KACIRMAZ.
    "/tutarli-403/": "403",
    "/yok/": "404",
    "/tasindi/": "301",
    "/hedef/": "acik",
    "/dongu-a/": "dongu-a",
    "/dongu-b/": "dongu-b",
    "/uzun-zincir/": "uzun",
    "/yavas/": "yavas",
}


def _fikstur_handler():
    from http.server import BaseHTTPRequestHandler

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        gecikme_sn = 2.0

        def log_message(self, *a):                          # sessiz
            return

        def _yaz(self, kod, govde=b"", ctype="text/html; charset=utf-8", ek=None,
                 govde_gonder=True):
            self.send_response(kod)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Server", "cloudflare")
            for k, v in (ek or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if govde_gonder and govde:
                self.wfile.write(govde)

        def _sayfa(self, gorev, yontem):
            if gorev == "acik":
                self._yaz(200, b"<!doctype html><title>PRUVO</title><h1>acik</h1>",
                          govde_gonder=(yontem == "GET"))
            elif gorev == "get403-head200":
                if yontem == "GET":
                    self._yaz(403, b"Forbidden", ctype="text/plain;charset=UTF-8")
                else:
                    self._yaz(200, b"", ctype="text/plain;charset=UTF-8")
            elif gorev == "403":
                self._yaz(403, b"Forbidden", ctype="text/plain;charset=UTF-8",
                          govde_gonder=(yontem == "GET"))
            elif gorev == "404":
                self._yaz(404, b"<!doctype html><title>404</title>",
                          govde_gonder=(yontem == "GET"))
            elif gorev == "301":
                self._yaz(301, b"", ek={"Location": "/hedef/"})
            elif gorev == "dongu-a":
                self._yaz(302, b"", ek={"Location": "/dongu-b/"})
            elif gorev == "dongu-b":
                self._yaz(302, b"", ek={"Location": "/dongu-a/"})
            elif gorev == "uzun":
                self._yaz(302, b"", ek={"Location": "/uzun-zincir/?n=%d"
                                                    % int(time.time() * 1000 % 100000)})
            elif gorev == "yavas":
                time.sleep(H.gecikme_sn)
                self._yaz(200, b"gec", govde_gonder=(yontem == "GET"))
            else:
                self._yaz(404, b"", govde_gonder=(yontem == "GET"))

        def _gorev(self):
            yol = urllib.parse.urlsplit(self.path).path
            if yol.startswith("/uzun-zincir/"):
                return "uzun"
            return FIKSTUR_YOLLARI.get(yol)

        def do_GET(self):                                   # noqa: N802
            g = self._gorev()
            if g is None:
                self._yaz(404, b"yok")
                return
            self._sayfa(g, "GET")

        def do_HEAD(self):                                  # noqa: N802
            g = self._gorev()
            if g is None:
                self._yaz(404, b"", govde_gonder=False)
                return
            self._sayfa(g, "HEAD")

    return H


class FiksturSunucu:
    """`with FiksturSunucu() as s:` -> s.taban ('http://127.0.0.1:PORT')."""

    def __init__(self):
        self.httpd = None
        self.taban = None
        self._is = None

    def __enter__(self):
        from http.server import ThreadingHTTPServer
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _fikstur_handler())
        self.taban = "http://127.0.0.1:%d" % self.httpd.server_address[1]
        self._is = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._is.start()
        return self

    def __exit__(self, *a):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:                                   # noqa: BLE001
            pass
        return False


def olu_taban():
    """Dinleyicisi OLMAYAN bir taban (ag arizasi fiksturu): baglanti REDDEDILIR."""
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return "http://127.0.0.1:%d" % port


# =========================================================== RAPOR
def kaynak_satirlari(kaynaklar, yollar, kapsam):
    satirlar = ["KUME TURETIMI (elle liste YOK — her yol bir KAYNAKTAN gelir):"]
    for ad, sayi, var, not_ in kaynaklar:
        satirlar.append("   %-46s %5s %s%s"
                        % (ad, sayi if var else "-", "VAR" if var else "YOK",
                           ("  (%s)" % not_) if not_ else ""))
    satirlar.append("   %-46s %5d BENZERSIZ  (kapsam: %s)"
                    % ("BIRLESIM", len(yollar), kapsam))
    satirlar.append("   KAPSAM DISI (eksen siniri): /urun/<id>/ -> "
                    "tools/canli-saglik-kapisi.py K2 ekseni"
                    + ("" if kapsam in ("marka", "tam") else " · /marka/... -> "
                       "`--kapsam marka|tam`"))
    return satirlar


def gh_ozet_yaz(sinif, ozet, satirlar, sure):
    """GitHub kosum ozeti + step output (varsa). Yan etkisi YOK: env yoksa sessiz."""
    cikti = os.environ.get("GITHUB_OUTPUT")
    if cikti:
        with open(cikti, "a", encoding="utf-8") as f:
            f.write("durum=%s\n" % DURUM_ETIKET.get(sinif, "olculemedi"))
            f.write("kapali=%d\n" % len(ozet.get("kapali") or []))
            f.write("olculen=%d\n" % ozet.get("olculen", 0))
    ozet_yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozet_yol:
        with open(ozet_yol, "a", encoding="utf-8") as f:
            f.write("## Yayin erisim nobeti — %s\n\n" % sinif)
            f.write("* olculen URL: **%d** · sure: **%.1f s**\n"
                    % (ozet.get("olculen", 0), sure))
            f.write("* kapali: **%d** · olcum arizasi: **%d** · yonlendirme: **%d**\n\n"
                    % (len(ozet.get("kapali") or []), len(ozet.get("ariza") or []),
                       len(ozet.get("yonlendirme") or [])))
            for s in satirlar:
                f.write("%s\n" % s)
            f.write("\nNE YAPILMALI: kapali URL'ler ORIGIN'de degil EDGE'de kapanmis "
                    "olabilir (worker rotasi/WAF). Once yanitin `server`/`cf-mitigated` "
                    "basliklarina bak; 9 baytlik `Forbidden` duz metin worker rotasi "
                    "isaretidir.\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Yayin erisim nobetcisi (canli sayfa acik mi)")
    ap.add_argument("--taban", default=SITE_VARSAYILAN, help="olculecek origin")
    ap.add_argument("--kapsam", default="sayfa", choices=KAPSAMLAR)
    ap.add_argument("--hiz", type=float, default=HIZ_VARSAYILAN, help="istek/sn tavani")
    ap.add_argument("--zaman-asimi", type=float, default=ZAMAN_ASIMI_VARSAYILAN)
    ap.add_argument("--liste", action="store_true", help="yalniz kumeyi bas (AG YOK)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gh-ozet", action="store_true")
    ap.add_argument("--kendini-test", action="store_true",
                    help="YEREL fikstur sunucusuyla kabul (dis ag YOK)")
    a = ap.parse_args(argv)

    if a.kendini_test:
        return kendini_test()

    try:
        yollar, kaynaklar = kume_turet(kapsam=a.kapsam)
    except OlcumHatasi as e:
        print("⚪ OLCULEMEDI (kume turetilemedi): %s" % e)
        if a.gh_ozet:
            gh_ozet_yaz("OLCULEMEDI", {"olculen": 0}, ["kume turetilemedi: %s" % e], 0.0)
        return SINIF_RC["OLCULEMEDI"]

    print("YAYIN ERISIM NOBETCISI — %s (%s)" % (a.taban, a.kapsam))
    print("-" * 78)
    for s in kaynak_satirlari(kaynaklar, yollar, a.kapsam):
        print(s)
    if a.liste:
        for y in yollar:
            print(y)
        print("KUME: %d URL (AG KULLANILMADI — hukum YOK)" % len(yollar))
        return 0

    print("YONTEM: %s (HEAD YETMEZ — olculdu: ayni URL HEAD 200 / GET 403)" % YONTEM)
    print("HIZ: %.1f istek/sn · zaman asimi %.0f s" % (a.hiz, a.zaman_asimi))
    kayitlar, sure = olc(yollar, taban=a.taban, hiz=a.hiz, zaman_asimi=a.zaman_asimi)
    sinif, rc, satirlar, ozet = degerlendir(kayitlar, kume_sayisi=len(yollar))
    print("-" * 78)
    for s in satirlar:
        print(s)
    print("SURE: %.1f s (%d URL · %.1f istek/sn olculen)"
          % (sure, len(kayitlar), (len(kayitlar) / sure) if sure else 0.0))
    print("SINIF: %s (rc %d)" % (sinif, rc))
    if a.json:
        print(json.dumps({"sinif": sinif, "rc": rc, "sure_sn": round(sure, 2),
                          "kapsam": a.kapsam, "taban": a.taban, "ozet": ozet},
                         ensure_ascii=False, indent=2, sort_keys=True))
    if a.gh_ozet:
        gh_ozet_yaz(sinif, ozet, satirlar, sure)
    return rc


# =========================================================== KENDINI TEST (YEREL)
def kendini_test():
    """YEREL fikstur sunucusuyla hukum kabulu. DIS AG YOK.

    Bu kol `tools/yayin-erisim-test.py`nin bir alt kumesidir; alarm is akisi tikandiginda
    elle kosulabilsin diye burada da durur. TAM takim (kablolama + mutasyon nobetleri)
    kabul testindedir."""
    fails = []

    def iddia(ad, kosul, detay=""):
        print(("  ✔ " if kosul else "  ✘ ") + ad + (("   [%s]" % detay) if detay else ""))
        if not kosul:
            fails.append(ad)

    print("YAYIN ERISIM NOBETCISI — YEREL FIKSTUR KABULU")
    with FiksturSunucu() as s:
        kayitlar, _ = olc(["/acik-1/", "/acik-2/"], taban=s.taban, hiz=0)
        sinif, rc, _, _ = degerlendir(kayitlar)
        iddia("KONTROL: hepsi 200 -> ACIK (yanlis-pozitif yok)",
              sinif == "ACIK" and rc == 0, "%s rc=%d" % (sinif, rc))

        kayitlar, _ = olc(["/acik-1/", "/araba-guneslik-klipsi-yaptirma/"],
                          taban=s.taban, hiz=0)
        sinif, rc, _, _ = degerlendir(kayitlar)
        iddia("OLDURUCU: GET 403 / HEAD 200 olan URL -> KAPALI (rc 1)",
              sinif == "KAPALI" and rc == 1, "%s rc=%d" % (sinif, rc))

        kayitlar, _ = olc(["/yok/"], taban=s.taban, hiz=0)
        sinif, _, _, _ = degerlendir(kayitlar)
        iddia("OLDURUCU: 404 -> KAPALI", sinif == "KAPALI", sinif)

        kayitlar, _ = olc(["/dongu-a/"], taban=s.taban, hiz=0)
        sinif, _, _, ozet = degerlendir(kayitlar)
        iddia("OLDURUCU: 3xx DONGUSU -> KAPALI", sinif == "KAPALI",
              "%s %s" % (sinif, ozet["kapali"]))

        kayitlar, _ = olc(["/tasindi/"], taban=s.taban, hiz=0)
        sinif, rc, _, ozet = degerlendir(kayitlar)
        iddia("301 -> 200 zinciri KAPALI DEGIL ama RAPORLANIR",
              sinif == "ACIK" and rc == 0 and len(ozet["yonlendirme"]) == 1,
              "%s yonlendirme=%d" % (sinif, len(ozet["yonlendirme"])))

    kayitlar, _ = olc(["/acik-1/"], taban=olu_taban(), hiz=0, zaman_asimi=3)
    sinif, rc, _, _ = degerlendir(kayitlar)
    iddia("FAIL-CLOSED: ag yok (baglanti reddedildi) -> OLCULEMEDI rc 2, YESIL DEGIL",
          sinif == "OLCULEMEDI" and rc == 2, "%s rc=%d" % (sinif, rc))

    print("%d iddia, %d KIRMIZI." % (6, len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
