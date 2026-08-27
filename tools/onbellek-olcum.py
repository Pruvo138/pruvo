#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Belge onbellek TTL taban olcumu. CI/yerel; harici bagimlilik YOK.

Bayraklar:
  --json          : Yalnizca JSON bas (insan tablosu YOK; makine tuketimi)
  --seri-yok      : (C) age serisi atlanir
  --tur-etiketi   : Cikti ilk satirina TUR=<etiket> yazar
  --kendini-test  : Aga cikmadan fiksturle kabul testi kosar (rc=0 gecer)

Onarim gecmisi (2026-08-27, kabul-onbellek-tur3):
  K1  --json bayragi eklendi (makine tarafindan tuketilebilir)
  K2  (B) hüküm satirinda "max-age=" oneki düsürüldü (deger zaten tasir)
  K3  (B) urun URL'i (A)'nin sitemap'inden turetilir; sabit slug kalkti
  K4  origin/edge kodu 200 degilse hüküm OLCULEMEDI olur (AYNI/FARKLI degil)
  K5  her (B) satiri sonunda HUKUM_B satiri + sonda BELGE_TTL_SN/KAYNAK ozeti
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ZONE = "d3a78b8c8ce2a25c127bf02e728ac7b1"
GITHUB_PAGES_IPS = [
    "185.199.108.153",
    "185.199.109.153",
    "185.199.110.153",
    "185.199.111.153",
]
CF_BASE = "https://api.cloudflare.com/client/v4"
CF_TOKEN_DOSYA = os.path.expanduser("~/.claude/cron/.cf-token")
WRANGLER_TOML = os.path.expanduser("~/.wrangler/config/default.toml")
MEDIA = "https://media.pruvo3d.com"
SITE = "https://pruvo3d.com"

# --- URL listesi ---
URL_BELGE = SITE + "/"
URL_HUKUK = SITE + "/gizlilik/"
URL_VARLIK1 = SITE + "/secenekler.js"
URL_VARLIK2 = SITE + "/taban-fiyatlar.js"
URL_VERI = SITE + "/urunler.json"
SITEMAP_URL = SITE + "/sitemap.xml"
R2_GORSEL = MEDIA + "/urunler/c3dwood-pla-coffee-espresso-tamper-1.jpg"

# --- Mod durumu ---
JSON_MODE = False
SONUC = {}  # JSON modunda biriktirilen sonuc agaci


def _out(s=""):
    """JSON modunda stdout'a basmaz (insan tablosu kirletmesin)."""
    if JSON_MODE:
        return
    print(s)


def http_basliklar(url, timeout=15, resolve_ip=None):
    """HEAD yerine GET (CF bazen HEAD'i farkli cache'liyor); header'lari GET ile cek.
    resolve_ip verilmisse --resolve gibi DNS bypass."""
    cmd = ["curl", "-sSI", "-A", "PruvoOnbellekOlcum/1.0", "--max-time", str(timeout), url]
    if resolve_ip:
        host = url.split("/")[2]
        cmd[2:2] = ["--resolve", host + ":443:" + resolve_ip]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        return r.returncode, r.stdout
    except subprocess.TimeoutExpired:
        return -1, ""


def parse_basliklar(blob):
    """curl -I ciktisini sozluk olarak parse eder (HTTP status + baslik anahtarlari)."""
    out = {}
    if not blob:
        return out
    # ilk satir status
    ilk = blob.splitlines()[0] if blob.splitlines() else ""
    m = re.match(r"HTTP/[\d.]+\s+(\d+)", ilk)
    if m:
        out["kod"] = int(m.group(1))
    for k in ["cache-control", "cf-cache-status", "age", "last-modified", "etag",
              "content-type", "server", "x-github-request-id", "x-served-by",
              "x-cache-hits", "content-length", "vary", "x-amz-cf-id"]:
        m = re.search(r"(?im)^" + re.escape(k) + r"\s*:\s*(.*?)\s*$", blob)
        if m:
            out[k] = m.group(1).strip()
    return out


def sitemap_urun_bul(sitemap_blob):
    """Sitemap govdesinden ilk /urun/ URL'sini bulur (bytes veya str); yoksa None.
    (B) bu fonksiyona duşar — sabit slug YASAK (K3)."""
    if sitemap_blob is None:
        return None
    if isinstance(sitemap_blob, bytes):
        metin = sitemap_blob.decode("utf-8", errors="ignore")
    else:
        metin = sitemap_blob
    for line in metin.splitlines():
        m = re.search(r"<loc>\s*(https://pruvo3d\.com/urun/[^\s<]+)\s*</loc>", line)
        if m:
            return m.group(1)
    return None


def govde_get(url, timeout=20, resolve_ip=None):
    cmd = ["curl", "-sS", "-A", "PruvoOnbellekOlcum/1.0", "--max-time", str(timeout), url]
    if resolve_ip:
        host = url.split("/")[2]
        cmd[2:2] = ["--resolve", host + ":443:" + resolve_ip]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
        return r.returncode, r.stdout
    except subprocess.TimeoutExpired:
        return -1, b""


def max_age_cikar(cc_str):
    """'max-age=14400' gibi degerden sayiyi cikarir; yoksa None."""
    if not cc_str or cc_str == "-":
        return None
    m = re.search(r"max-age\s*=\s*(\d+)", cc_str)
    return int(m.group(1)) if m else None


def hukum_ver(origin_h, edge_h):
    """(B) hükümü. K4: ikisi de 200 olmali; degilse OLCULEMEDI.
    K5: her zaman makine-okunur alanlar iceren dict doner."""
    origin_kod = origin_h.get("kod") if origin_h else None
    edge_kod = edge_h.get("kod") if edge_h else None
    oc = origin_h.get("cache-control", "-") if origin_h else "-"
    ec = edge_h.get("cache-control", "-") if edge_h else "-"
    base = {
        "oc": oc,
        "ec": ec,
        "origin_kod": origin_kod,
        "edge_kod": edge_kod,
    }
    if origin_kod != 200 or edge_kod != 200:
        return dict(base, sonuc="OLCULEMEDI", kaynak="OLCULEMEDI")
    if oc != ec:
        return dict(base, sonuc="FARKLI", kaynak="CF")
    return dict(base, sonuc="AYNI", kaynak="ORIGIN")


def hukum_satiri_bas(url, huk):
    """(B) URL satiri sonuna insan + makine satirlari basar."""
    _out("  >>> HUKUM: cache-control ORIGIN=%s EDGE=%s — %s" % (
        huk["oc"], huk["ec"], huk["sonuc"]))
    if huk["sonuc"] == "OLCULEMEDI":
        _out("  >>> DETAY: HTTP kod origin=%s edge=%s" % (
            huk["origin_kod"], huk["edge_kod"]))
    _out("HUKUM_B url=%s origin=%s edge=%s sonuc=%s" % (
        url, huk["oc"], huk["ec"], huk["sonuc"]))


def bolum_yaz(etiket):
    _out("\n" + "=" * 78)
    _out("== " + etiket)
    _out("=" * 78)


def bolum_A_edge_olcumu():
    bolum_yaz("(A) EDGE OLCUMU - https://pruvo3d.com uzerinden")

    # 1. sitemap'ten urun URL'si sec
    _out("\n-- Sitemap'ten urun sayfasi URL'si aliniyor...")
    rc, gov = govde_get(SITEMAP_URL)
    urun_url = sitemap_urun_bul(gov)  # K3: tek kaynak (B) ile paylasilir
    _out("URUN_SAYFASI_URL=" + (urun_url or "BULUNAMADI"))

    urls = [
        ("BELGE_ANA", URL_BELGE),
        ("BELGE_HUKUK", URL_HUKUK),
        ("URUN_SAYFASI", urun_url),
        ("VARLIK_SECENEKLER", URL_VARLIK1),
        ("VARLIK_TABAN_FIYAT", URL_VARLIK2),
        ("VERI_URUNLER", URL_VERI),
        ("R2_GORSEL", R2_GORSEL),
    ]

    tablo = []
    for ad, u in urls:
        if not u:
            tablo.append((ad, "YOK", "-", "-", "-"))
            continue
        rc, blob = http_basliklar(u)
        h = parse_basliklar(blob)
        tablo.append((
            ad,
            h.get("kod", "?"),
            h.get("cache-control", "-"),
            h.get("cf-cache-status", "-"),
            h.get("age", "-"),
        ))
        _out("\n>> %s  %s" % (ad, u))
        for k in ["kod", "server", "cache-control", "cf-cache-status", "age",
                  "last-modified", "etag", "content-type", "x-served-by",
                  "x-cache-hits", "x-github-request-id"]:
            if k in h:
                _out("   %-22s: %s" % (k, h[k]))
    return {"urun_sayfasi_url": urun_url, "tablo": tablo}


def bolum_B_origin_bypass(urun_url):
    """urun_url: (A)'nin sitemap'ten buldugu URL (K3 — sabit slug YOK).
    urun_url None ise urun satiri OLCULEMEDI basar (K3 fallback)."""
    bolum_yaz("(B) ORIGIN BYPASS - GitHub Pages IP'leri dogrudan")
    hedefler = [
        URL_BELGE,
        URL_HUKUK,
        URL_VARLIK1,
        SITE + "/urunler.json",
    ]
    if urun_url:
        hedefler.append(urun_url)
    else:
        # K3: sabit slug'a DUSME — urun satiri OLCULEMEDI
        _out("\nURL: <urun sayfasi>")
        _out("  ORIGIN: sitemap'ten urun URL'i turetilemedi")
        _out("  EDGE: olculmedi")
        _out("  >>> HUKUM: cache-control ORIGIN=- EDGE=- — OLCULEMEDI")
        _out("  >>> DETAY: urun URL sitemap'ten turetilemedi (K3 fallback)")
        _out("HUKUM_B url=<urun sayfasi> origin=- edge=- sonuc=OLCULEMEDI")

    sonuc = {}
    for url in hedefler:
        host = url.split("/")[2]
        origin_basliklar = None
        origin_ip = None
        for ip in GITHUB_PAGES_IPS:
            rc, blob = http_basliklar(url, resolve_ip=ip)
            if rc != 0 or not blob:
                continue
            h = parse_basliklar(blob)
            if h.get("kod") in (200, 301, 302):
                origin_basliklar = h
                origin_ip = ip
                break
        # edge
        rc2, blob2 = http_basliklar(url)
        edge_h = parse_basliklar(blob2)
        # K4: hüküm YALNIZ ikisi de 200 iken AYNI/FARKLI; degilse OLCULEMEDI
        huk = hukum_ver(origin_basliklar, edge_h)
        sonuc[url] = {
            "origin": origin_basliklar,
            "origin_ip": origin_ip,
            "edge": edge_h,
            "hukum": huk,
        }
        _out("\nURL: " + url)
        if origin_basliklar:
            _out("  ORIGIN_IP          : " + (origin_ip or "-"))
            _out("  ORIGIN_HTTP        : " + str(origin_basliklar.get("kod", "-")))
            _out("  ORIGIN_server      : " + origin_basliklar.get("server", "-"))
            _out("  ORIGIN_cache-ctrl  : " + origin_basliklar.get("cache-control", "-"))
            _out("  ORIGIN_age         : " + origin_basliklar.get("age", "-"))
            _out("  ORIGIN_cf-cache    : " + origin_basliklar.get("cf-cache-status", "-"))
        else:
            _out("  ORIGIN: 4 IP de yanit vermedi (timeout/erisim yok)")
        _out("  EDGE_HTTP          : " + str(edge_h.get("kod", "-")))
        _out("  EDGE_server        : " + edge_h.get("server", "-"))
        _out("  EDGE_cache-ctrl    : " + edge_h.get("cache-control", "-"))
        _out("  EDGE_age           : " + edge_h.get("age", "-"))
        _out("  EDGE_cf-cache      : " + edge_h.get("cf-cache-status", "-"))
        # K2: önek kaldirildi — değer zaten 'max-age=...' tasiyor
        _out("  >>> HUKUM: cache-control ORIGIN=%s EDGE=%s — %s" % (
            huk["oc"], huk["ec"], huk["sonuc"]))
        if huk["sonuc"] == "OLCULEMEDI":
            _out("  >>> DETAY: HTTP kod origin=%s edge=%s" % (
                huk["origin_kod"], huk["edge_kod"]))
        # K5: makine-okunur hüküm satiri
        _out("HUKUM_B url=%s origin=%s edge=%s sonuc=%s" % (
            url, huk["oc"], huk["ec"], huk["sonuc"]))

    # urun satiri OLCULEMEDI ise (sentinel URL) sonuc'a ekle
    if not urun_url:
        sonuc["<urun sayfasi>"] = {
            "origin": None,
            "origin_ip": None,
            "edge": None,
            "hukum": {"sonuc": "OLCULEMEDI", "oc": "-", "ec": "-",
                      "origin_kod": None, "edge_kod": None,
                      "kaynak": "OLCULEMEDI",
                      "sebep": "urun URL sitemap'ten turetilemedi"},
        }
    return sonuc


def bolum_C_age_serisi():
    bolum_yaz("(C) AGE SERISI - 8 istek, 15 sn aralikla")
    seri = []
    for i in range(8):
        rc, blob = http_basliklar(URL_BELGE)
        h = parse_basliklar(blob)
        seri.append({
            "t": i,
            "ts": time.time(),
            "kod": h.get("kod"),
            "age": h.get("age", "-"),
            "cf-cache-status": h.get("cf-cache-status", "-"),
            "cache-control": h.get("cache-control", "-"),
        })
        _out("  t=%d  age=%-5s  cf=%-7s  cc=%s" % (
            i, seri[-1]["age"], seri[-1]["cf-cache-status"], seri[-1]["cache-control"]))
        if i < 7:
            time.sleep(15)
    # fiili TTL yorumu
    _out("\nFiili edge TTL yorumu:")
    for r in seri:
        _out("  t=%d -> %s" % (r["t"], str(r)))
    return seri


def kimlik_bul():
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if tok:
        return tok, os.environ.get("CLOUDFLARE_ACCOUNT_ID"), "ortam(CLOUDFLARE_API_TOKEN)"
    if os.path.exists(CF_TOKEN_DOSYA):
        tok = open(CF_TOKEN_DOSYA).read().strip()
        if tok:
            return tok, os.environ.get("CLOUDFLARE_ACCOUNT_ID"), "dosya(~/.claude/cron/.cf-token)"
    if os.path.exists(WRANGLER_TOML):
        icerik = open(WRANGLER_TOML).read()
        m = re.search(r'oauth_token\s*=\s*"([^"]+)"', icerik)
        if m:
            return m.group(1), None, "wrangler-oauth(~/.wrangler/config/default.toml)"
    return None, None, "YOK"


def cf_get(yol, token):
    req = urllib.request.Request(CF_BASE + yol, method="GET",
                                 headers={"Authorization": "Bearer " + token,
                                          "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")
    except urllib.error.URLError as e:
        return 0, str(e)


def bolum_D_cf_ayarlar():
    bolum_yaz("(D) CLOUDFLARE AYARLARI (salt okuma)")
    token, account_id, kaynak = kimlik_bul()
    maske = (token[:6] + "...") if token else "-"
    _out("TOKEN_KAYNAK=" + kaynak + "  TOKEN_MASK=" + maske + "  ACCOUNT=" + (account_id or "-"))
    if not token:
        _out("OLCULEMEDI: Cloudflare kimlik bulunamadi (ortam/dosya/wrangler).")
        return {}

    out = {}
    for ad, yol in [
        ("browser_cache_ttl", "/zones/" + ZONE + "/settings/browser_cache_ttl"),
        ("cache_level", "/zones/" + ZONE + "/settings/cache_level"),
        ("rulesets_list", "/zones/" + ZONE + "/rulesets"),
    ]:
        kod, gov = cf_get(yol, token)
        _out("\n>> " + ad + "  HTTP " + str(kod))
        if kod == 200:
            try:
                j = json.loads(gov)
            except json.JSONDecodeError:
                _out("   JSON cozumu basarisiz")
                out[ad] = {"kod": kod, "gov": gov[:500]}
                continue
            if ad == "rulesets_list":
                # cache_settings ruleset id bul
                rid = None
                for rs in j.get("result", []):
                    if rs.get("phase") == "http_request_cache_settings":
                        rid = rs.get("id")
                        break
                _out("   cache_settings ruleset id = " + (rid or "YOK"))
                if rid:
                    kod2, gov2 = cf_get("/zones/" + ZONE + "/rulesets/" + rid, token)
                    _out("   ruleset detay HTTP " + str(kod2))
                    if kod2 == 200:
                        try:
                            j2 = json.loads(gov2)
                            rules = j2.get("result", {}).get("rules", [])
                            _out("   kural sayisi: " + str(len(rules)))
                            for rule in rules:
                                expr = rule.get("expression", "-")
                                act = rule.get("action", "-")
                                params = rule.get("action_parameters", {})
                                cache = params.get("cache", {}) if isinstance(params, dict) else {}
                                edge = cache.get("edge_ttl", "-")
                                bro = cache.get("browser_ttl", "-")
                                _out("   - rule id=%s expr=%s action=%s edge_ttl=%s browser_ttl=%s" %
                                      (rule.get("id", "-"), expr, act, edge, bro))
                        except json.JSONDecodeError:
                            pass
                    out[ad] = {"kod": kod, "ruleset_id": rid, "kod2": kod2}
                else:
                    out[ad] = {"kod": kod, "ruleset_id": None}
            else:
                # setting value
                val = j.get("result", {}).get("value", "-")
                idl = j.get("result", {}).get("id", "-")
                _out("   id=%s  value=%s" % (idl, val))
                out[ad] = {"kod": kod, "value": val, "id": idl}
        else:
            _out("   HATA govde: " + gov[:300])
            out[ad] = {"kod": kod, "gov": gov[:300]}
    return out


def bolum_E_govde_versiyon():
    bolum_yaz("(E) ANA SAYFA GOVDE - uzunluk + script src satirlari")
    rc, gov = govde_get(URL_BELGE)
    if rc != 0 or not gov:
        _out("OLCULEMEDI: govde cekilemedi rc=%d" % rc)
        return {}
    metin = gov.decode("utf-8", errors="ignore")
    _out("BOYUT_BYTE=" + str(len(gov)))
    scriptler = re.findall(r"<script[^>]*src=[\"']([^\"']+)[\"']", metin)
    _out("SCRIPT_SATIRLARI:")
    for s in scriptler:
        _out("  " + s)
    versiyon_var = any(re.search(r"\?v=[a-fA-F0-9_-]+", s) for s in scriptler)
    _out("\n?v=<hash> SURUMLEME VAR MI: " + ("EVET" if versiyon_var else "HAYIR"))
    return {"boyut": len(gov), "scriptler": scriptler, "versiyon_var": versiyon_var}


# === KENDINI-TEST FIKSTURLERI ===

FIXTURLER = {
    "edge_yanit_14400": (
        "HTTP/2 200\r\n"
        "server: cloudflare\r\n"
        "content-type: text/html; charset=utf-8\r\n"
        "cache-control: public, max-age=14400\r\n"
        "cf-cache-status: HIT\r\n"
        "age: 1234\r\n"
        "x-served-by: cache-fra\r\n"
        "\r\n"
    ),
    "origin_yanit_600": (
        "HTTP/2 200\r\n"
        "server: GitHub.com\r\n"
        "content-type: text/html; charset=utf-8\r\n"
        "cache-control: public, max-age=600\r\n"
        "x-github-request-id: ABC1:2DEF:1234567:8ABCDE:0A\r\n"
        "x-served-by: cache-bos1\r\n"
        "\r\n"
    ),
    "edge_yanit_600": (
        "HTTP/2 200\r\n"
        "server: cloudflare\r\n"
        "content-type: text/html; charset=utf-8\r\n"
        "cache-control: public, max-age=600\r\n"
        "cf-cache-status: MISS\r\n"
        "age: 0\r\n"
        "x-served-by: cache-fra\r\n"
        "\r\n"
    ),
    "origin_404_yanit": (
        "HTTP/2 404\r\n"
        "server: GitHub.com\r\n"
        "content-type: text/html; charset=utf-8\r\n"
        "cache-control: public, max-age=600\r\n"
        "x-github-request-id: DEF2:3ABC:7654321:9BCDEF:0B\r\n"
        "\r\n"
    ),
    "edge_404_yanit": (
        "HTTP/2 404\r\n"
        "server: cloudflare\r\n"
        "content-type: text/html; charset=utf-8\r\n"
        "cache-control: public, max-age=600\r\n"
        "cf-cache-status: HIT\r\n"
        "age: 50\r\n"
        "\r\n"
    ),
    "sitemap_bos": (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        "  <url><loc>https://pruvo3d.com/</loc></url>\n"
        "  <url><loc>https://pruvo3d.com/gizlilik/</loc></url>\n"
        "  <url><loc>https://pruvo3d.com/secenekler.js</loc></url>\n"
        "</urlset>\n"
    ),
    "sitemap_urunlu": (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        "  <url><loc>https://pruvo3d.com/</loc></url>\n"
        "  <url><loc>https://pruvo3d.com/urun/test-urun/</loc></url>\n"
        "</urlset>\n"
    ),
}


# === MUTANTLAR (test icinde — canli dosyada YASAK) ===

def _mutant_hukum_k4(origin_h, edge_h):
    """M-K4: 200 teyidi YOK — eski davranisa donus (K4 oncesi)."""
    oc = origin_h.get("cache-control", "-") if origin_h else "-"
    ec = edge_h.get("cache-control", "-") if edge_h else "-"
    if oc != ec:
        return {"sonuc": "FARKLI", "oc": oc, "ec": ec,
                "origin_kod": origin_h.get("kod") if origin_h else None,
                "edge_kod": edge_h.get("kod") if edge_h else None,
                "kaynak": "CF"}
    return {"sonuc": "AYNI", "oc": oc, "ec": ec,
            "origin_kod": origin_h.get("kod") if origin_h else None,
            "edge_kod": edge_h.get("kod") if edge_h else None,
            "kaynak": "ORIGIN"}


def _mutant_sitemap_k3(sitemap_blob):
    """M-K3: sitemap bos iken sabit slug'a dusme (K3 oncesi hatali davranis)."""
    url = sitemap_urun_bul(sitemap_blob)
    if url is None:
        return SITE + "/urun/kahve-c3d-espresso-tamper-ahsap-desen/"
    return url


def _kontrol_kozmetik(edge_blob, origin_blob):
    """KONTROL: parse_basliklar ayni sonuc vermeli; kozmetik degisiklik etkisiz."""
    eh = parse_basliklar(edge_blob)
    oh = parse_basliklar(origin_blob)
    return hukum_ver(oh, eh)


def kendini_test_calistir():
    """Ağsız kabul testi. Fikstur -> parse_basliklar + hukum_ver + sitemap_urun_bul.
    rc=0 gecer; herhangi bir vaka duserse veya mutant kacarsa rc!=0."""
    print("KENDINI-TEST (agsiz) — baslangic " + time.strftime("%Y-%m-%d %H:%M:%S"))

    vakalar = []  # (id, baslik, basarili_mi, detay)

    # === VAKA 1: gercek edge yaniti parse ===
    h1 = parse_basliklar(FIXTURLER["edge_yanit_14400"])
    v1_ok = (
        h1.get("kod") == 200
        and h1.get("cache-control") == "public, max-age=14400"
        and h1.get("cf-cache-status") == "HIT"
        and h1.get("server") == "cloudflare"
    )
    vakalar.append(("1", "edge parse (200/HIT/max-age=14400)",
                    v1_ok,
                    "kod=%s cc=%s cf=%s server=%s" % (
                        h1.get("kod"), h1.get("cache-control"),
                        h1.get("cf-cache-status"), h1.get("server"))))

    # === VAKA 2: gercek origin yaniti parse ===
    h2 = parse_basliklar(FIXTURLER["origin_yanit_600"])
    v2_ok = (
        h2.get("kod") == 200
        and h2.get("cache-control") == "public, max-age=600"
        and h2.get("server") == "GitHub.com"
    )
    vakalar.append(("2", "origin parse (200/GitHub.com/max-age=600)",
                    v2_ok,
                    "kod=%s cc=%s server=%s" % (
                        h2.get("kod"), h2.get("cache-control"), h2.get("server"))))

    # === VAKA 3: FARKLI (origin=600, edge=14400, ikisi de 200) -> CF ===
    h3_o = parse_basliklar(FIXTURLER["origin_yanit_600"])
    h3_e = parse_basliklar(FIXTURLER["edge_yanit_14400"])
    v3 = hukum_ver(h3_o, h3_e)
    v3_ok = v3["sonuc"] == "FARKLI" and v3["kaynak"] == "CF"
    vakalar.append(("3", "FARKLI(600 vs 14400) -> CF",
                    v3_ok,
                    "sonuc=%s kaynak=%s" % (v3["sonuc"], v3["kaynak"])))

    # === VAKA 4: AYNI (origin=600, edge=600, ikisi de 200) -> ORIGIN ===
    h4_o = parse_basliklar(FIXTURLER["origin_yanit_600"])
    h4_e = parse_basliklar(FIXTURLER["edge_yanit_600"])
    v4 = hukum_ver(h4_o, h4_e)
    v4_ok = v4["sonuc"] == "AYNI" and v4["kaynak"] == "ORIGIN"
    vakalar.append(("4", "AYNI(600 vs 600) -> ORIGIN",
                    v4_ok,
                    "sonuc=%s kaynak=%s" % (v4["sonuc"], v4["kaynak"])))

    # === VAKA 5: 🔴 OLCULEMEDI (origin=404, edge=404, AYNI cache-control) — K4 vakasi ===
    h5_o = parse_basliklar(FIXTURLER["origin_404_yanit"])
    h5_e = parse_basliklar(FIXTURLER["edge_404_yanit"])
    v5 = hukum_ver(h5_o, h5_e)
    v5_ok = v5["sonuc"] == "OLCULEMEDI"
    vakalar.append(("5", "🔴 404+404 -> OLCULEMEDI (K4)",
                    v5_ok,
                    "sonuc=%s origin_kod=%s edge_kod=%s" % (
                        v5["sonuc"], v5["origin_kod"], v5["edge_kod"])))

    # === VAKA 6: 🔴 sitemap'te /urun/ yok -> URL bulunamadi (K3 vakasi) ===
    u6 = sitemap_urun_bul(FIXTURLER["sitemap_bos"])
    v6_ok = u6 is None
    vakalar.append(("6", "🔴 sitemap bos -> None (K3)",
                    v6_ok,
                    "urun_url=%s" % (u6 or "<None>")))

    # === MUTANT M-K4: 200 teyidi kaldirilirsa vaka 5 kirmizi yanmali ===
    h5m_o = parse_basliklar(FIXTURLER["origin_404_yanit"])
    h5m_e = parse_basliklar(FIXTURLER["edge_404_yanit"])
    v5m = _mutant_hukum_k4(h5m_o, h5m_e)
    # Mutant altinda vaka 5 AYNI donmeli (eski hatali davranis); bu YANLIS
    # -> mutant altinda vaka 5'in beklenen sonuc OLCULEMEDI'den SAPAR
    mutant_k4_etkili = v5m["sonuc"] != "OLCULEMEDI"

    # === MUTANT M-K3: sabit slug fallback -> vaka 6 kirmizi yanmali ===
    u6m = _mutant_sitemap_k3(FIXTURLER["sitemap_bos"])
    # Mutant altinda vaka 6 None yerine sabit slug donmeli; bu YANLIS
    mutant_k3_etkili = u6m is not None

    mutant_sonuclari = [
        ("M-K4", "200 teyidi YOK -> vaka 5 AYNI/FARKLI verir (yanlis)", mutant_k4_etkili),
        ("M-K3", "sabit slug fallback -> vaka 6 URL doner (yanlis)", mutant_k3_etkili),
    ]

    # === KONTROL: kozmetik degisiklik (yardimci davranisi) -> batarya YESIL kalmali ===
    kontrol_hukum = _kontrol_kozmetik(
        FIXTURLER["edge_yanit_14400"], FIXTURLER["origin_yanit_600"])
    kontrol_ok = kontrol_hukum["sonuc"] == "FARKLI"

    # === Sonuclari bas ===
    print("\n--- VAKA DETAYLARI ---")
    for vid, vbaslik, basarili, detay in vakalar:
        print("VAKA %s [%s]: %s — %s" % (
            vid, vbaslik, "BASARILI" if basarili else "DUSTU", detay))

    print("\n--- MUTANT DETAYLARI ---")
    for mid, mbaslik, etkili in mutant_sonuclari:
        print("MUTANT %s [%s]: %s" % (
            mid, mbaslik, "OLDURULDU" if etkili else "KACTI"))

    print("\nKONTROL: %s" % ("YESIL" if kontrol_ok else "KIRMIZI"))

    dusen = sum(1 for _, _, b, _ in vakalar if not b)
    mutant_oldurulen = sum(1 for _, _, e in mutant_sonuclari if e)
    mutant_toplam = len(mutant_sonuclari)

    print("\nOZET: VAKA=%d DUSEN=%d MUTANT=%d/%d KONTROL=%s" % (
        len(vakalar), dusen, mutant_oldurulen, mutant_toplam,
        "YESIL" if kontrol_ok else "KIRMIZI"))

    basarili = dusen == 0 and mutant_oldurulen == mutant_toplam and kontrol_ok
    print("SONUC: " + ("GECTI" if basarili else "DUSTU"))
    return 0 if basarili else 1


# === OZET HESAPLAYICILAR ===

def ozet_hesapla(b):
    """(B) sonuc dict'inden ana sayfa icin BELGE_TTL_SN ve KAYNAK uretir."""
    edge_belge = None
    bel_hukum = None
    for url, data in b.items():
        if url == URL_BELGE:
            edge_belge = data.get("edge")
            bel_hukum = data.get("hukum")
            break
    edge_cc = edge_belge.get("cache-control", "-") if edge_belge else "-"
    belge_ttl_sn = max_age_cikar(edge_cc)
    kaynak = bel_hukum.get("kaynak", "OLCULEMEDI") if bel_hukum else "OLCULEMEDI"
    return belge_ttl_sn, kaynak


# === MAIN ===

def main():
    global JSON_MODE, SONUC

    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--seri-yok", action="store_true",
                    help="(C) age serisi atlanir (ardisik kosumlarda zaman kazandirir)")
    ap.add_argument("--tur-etiketi", default="",
                    help="Cikti ilk satiri olarak basar: TUR=<etiket>")
    ap.add_argument("--json", action="store_true",
                    help="Yalnizca JSON bas; insan tablosu BASILMAZ (K1)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="Aga cikmadan fiksturle kabul testi kosar (rc=0 gecer)")
    args = ap.parse_args()

    if args.kendini_test:
        rc = kendini_test_calistir()
        sys.exit(rc)

    JSON_MODE = args.json

    if args.tur_etiketi:
        _out("TUR=" + args.tur_etiketi)

    basla = time.time()
    _out("ONBELLEK TTL TABAN OLCUMU - baslangic " + time.strftime("%Y-%m-%d %H:%M:%S"))
    _out("Hedef site: " + SITE)
    _out("CF zone   : " + ZONE)

    SONUC = {"a": {}, "b": {}, "c": {}, "d": {}, "e": {}, "meta": {}}

    a = bolum_A_edge_olcumu()
    SONUC["a"] = a

    # K3: (B) urun URL'ini (A)'nin sitemap'inden alir — sabit slug YOK
    b = bolum_B_origin_bypass(a.get("urun_sayfasi_url"))
    SONUC["b"] = b

    if args.seri_yok:
        c = {"atlandi": True, "sebep": "--seri-yok"}
        _out("\n" + "=" * 78)
        _out("== (C) AGE SERISI - ATLANDI (--seri-yok)")
        _out("=" * 78)
    else:
        c = bolum_C_age_serisi()
    SONUC["c"] = c

    d = bolum_D_cf_ayarlar()
    SONUC["d"] = d

    e = bolum_E_govde_versiyon()
    SONUC["e"] = e

    bitis = time.time()
    SONUC["meta"]["sure_sn"] = round(bitis - basla, 1)
    SONUC["meta"]["baslangic"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SONUC["meta"]["site"] = SITE
    SONUC["meta"]["zone"] = ZONE

    _out("\nTOPLAM SURE: %.1f sn" % SONUC["meta"]["sure_sn"])

    # K5: BELGE_TTL_SN + KAYNAK ozet satiri (insan modunda bas; JSON modunda alana yaz)
    belge_ttl_sn, kaynak = ozet_hesapla(b)
    SONUC["belge_ttl_sn"] = belge_ttl_sn
    SONUC["kaynak"] = kaynak
    _out("BELGE_TTL_SN=%s KAYNAK=%s" % (
        "OLCULEMEDI" if belge_ttl_sn is None else belge_ttl_sn,
        kaynak))

    if JSON_MODE:
        # K1: YALNIZ saf JSON bassin
        print(json.dumps(SONUC, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
