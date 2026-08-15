#!/usr/bin/env python3
"""cf-durum.py — Cloudflare/GitHub panel durumunu TARAYICI YERINE API'den oku (SALT OKUMA).

Amac: panel turlarinin cogunu kaldirmak; Okan'in ekraninda pencere acilmasin.
Hicbir alt komut degisiklik yapmaz (POST yalniz GraphQL ANALITIK sorgusu icin).

Kimlik sirasi:
  1) ortam: CLOUDFLARE_API_TOKEN (+ varsa CLOUDFLARE_ACCOUNT_ID) — Actions ile ayni adlar
  2) wrangler OAuth: ~/.wrangler/config/default.toml (oauth_token; suresi dolmussa
     yenileme BU ARACTAN YAPILMAZ — bir kez `npx --yes wrangler@4 whoami` kosulur)

Cikis kodlari: 0=basari · 3=kimlik yok/yetki eksik (OKAN KAPISI: kapsam panelde eklenir)
               4=ag/uc hatasi

GUVENLIK: token degeri hicbir ciktiya yazilmaz; hesap adi/id MASKELENIR; DNS kayit
icerikleri ilk 6 karakter + '…' ile gosterilir.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

CF_BASE = "https://api.cloudflare.com/client/v4"
GH_API = "https://api.github.com"
GH_REPO = "Pruvo138/pruvo"          # public repo — GitHub Pages dagitimlari burada
WRANGLER_TOML = os.path.expanduser("~/.wrangler/config/default.toml")
DB_AD = "pruvo-katalog"

RC_OK = 0
RC_YETKI = 3
RC_AG = 4

HTTP_ZAMAN_ASIMI = 30
D1_ZAMAN_ASIMI = 600


class YetkiEksik(Exception):
    """Kimlik yok ya da kapsam yetmiyor — OKAN KAPISI."""


class AgHatasi(Exception):
    """Ag ya da uc hatasi."""


def _maske(deger, n=6):
    deger = str(deger or "")
    return (deger[:n] + "…") if deger else "—"


def kimlik_bul():
    """(token, account_id|None, kaynak) dondur; bulamazsa YetkiEksik."""
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if tok:
        return tok, os.environ.get("CLOUDFLARE_ACCOUNT_ID"), "ortam(CLOUDFLARE_API_TOKEN)"
    if os.path.exists(WRANGLER_TOML):
        icerik = open(WRANGLER_TOML).read()
        m = re.search(r'oauth_token\s*=\s*"([^"]+)"', icerik)
        if m:
            son = re.search(r'expiration_time\s*=\s*"([^"]+)"', icerik)
            if son:
                try:
                    bitis = datetime.fromisoformat(son.group(1).replace("Z", "+00:00"))
                    if bitis <= datetime.now(timezone.utc):
                        raise YetkiEksik(
                            "wrangler OAuth token SURESI DOLMUS (%s). Yenileme bu aractan "
                            "yapilmaz; bir kez: npx --yes wrangler@4 whoami (tarayici girisi "
                            "gerekebilir — OKAN KAPISI) ya da CLOUDFLARE_API_TOKEN verin."
                            % son.group(1))
                except ValueError:
                    pass  # tarih cozulemedi — token'i dene, uc karar versin
            return m.group(1), None, "wrangler-oauth(~/.wrangler/config/default.toml)"
    raise YetkiEksik(
        "Cloudflare kimligi YOK. Beklenen kaynaklar: ortamda CLOUDFLARE_API_TOKEN veya "
        "~/.wrangler/config/default.toml icinde oauth_token. Token uretme/degistirme "
        "OKAN KAPISI'dir — panelde 'My Profile → API Tokens' uzerinden salt-okuma "
        "kapsamli token eklenmeli.")


def _cf_istek(yol, token, kapsam, method="GET", data=None):
    """Cloudflare API cagrisi. 401/403 -> YetkiEksik(kapsam); diger -> AgHatasi."""
    govde = json.dumps(data).encode() if data is not None else None
    istek = urllib.request.Request(
        CF_BASE + yol, data=govde, method=method,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(istek, timeout=HTTP_ZAMAN_ASIMI) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise YetkiEksik(
                "yetki eksik (HTTP %s): %s — Cloudflare panelinde API token'a bu kapsam "
                "eklenmeli (OKAN KAPISI; bu araç token uretmez/degistirmez)."
                % (e.code, kapsam))
        raise AgHatasi("Cloudflare API HTTP %s (%s)" % (e.code, yol))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AgHatasi("Cloudflare API erisilemedi (%s): %s" % (yol, e))


def hesap_id_bul(token, bilinen=None):
    if bilinen:
        return bilinen
    res = _cf_istek("/accounts?per_page=5", token,
                    "Account → Account Settings → Read")
    hesaplar = res.get("result") or []
    if not hesaplar:
        raise AgHatasi("/accounts bos dondu — token hicbir hesaba bagli degil.")
    return hesaplar[0]["id"]


# ---------------------------------------------------------------- D1
def d1_durum():
    """Kanonik okuyucu tools/d1-sync.py --durum'dur; ikinci kopya YAZILMAZ, o cagrilir."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    arac = os.path.join(repo, "tools", "d1-sync.py")
    if not os.path.exists(arac):
        raise AgHatasi("tools/d1-sync.py bulunamadi: " + arac)
    print("(kanonik okuyucu: tools/d1-sync.py --durum --hizli cagriliyor)", flush=True)
    try:
        p = subprocess.run([sys.executable, arac, "--durum", "--hizli"],
                           cwd=repo, timeout=D1_ZAMAN_ASIMI)
    except subprocess.TimeoutExpired:
        raise AgHatasi("d1-sync.py --durum %ds icinde bitmedi." % D1_ZAMAN_ASIMI)
    if p.returncode != 0:
        raise AgHatasi("d1-sync.py --durum rc=%s (ustteki ciktiya bakin)" % p.returncode)


# ---------------------------------------------------------------- R2
def r2_durum(token, acc):
    res = _cf_istek("/accounts/%s/r2/buckets?per_page=50" % acc, token,
                    "Account → Cloudflare R2 → Read")
    kovalar = res.get("result") or []
    if isinstance(kovalar, dict):
        kovalar = kovalar.get("buckets", [])
    isimler = [k.get("name") for k in kovalar]

    olcum = {}
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sorgu = {"query": (
        "query { viewer { accounts(filter: {accountTag: \"%s\"}) { "
        "r2StorageAdaptiveGroups(limit: 200, filter: {datetime_geq: \"%s\"}, "
        "orderBy: [datetime_DESC]) { dimensions { bucketName datetime } "
        "max { objectCount payloadSize } } } } }" % (acc, since))}
    g = _cf_istek("/graphql", token, "Account → Account Analytics → Read",
                  method="POST", data=sorgu)
    if g.get("errors"):
        raise AgHatasi("GraphQL analitik hatasi: " +
                       json.dumps(g["errors"], ensure_ascii=False)[:300])
    gruplar = (((g.get("data") or {}).get("viewer") or {}).get("accounts") or [{}])[0]
    for satir in gruplar.get("r2StorageAdaptiveGroups") or []:
        ad = satir["dimensions"]["bucketName"]
        if ad not in olcum:  # DESC sirali — ilk gorulen en taze
            olcum[ad] = satir["max"]

    print("R2 kovalari (%d):" % len(isimler))
    for k in kovalar:
        ad = k.get("name")
        m = olcum.get(ad) or {}
        nesne = m.get("objectCount")
        boyut = m.get("payloadSize")
        boyut_s = ("%.2f GB" % (boyut / 1e9)) if isinstance(boyut, (int, float)) else "—"
        print("  %-22s nesne=%-8s boyut=%-9s olusturma=%s"
              % (ad, nesne if nesne is not None else "—", boyut_s,
                 k.get("creation_date", "—")))


# ---------------------------------------------------------------- Pages (GitHub)
def _gh_get(yol):
    istek = urllib.request.Request(GH_API + yol, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "pruvo-cf-durum"})
    try:
        with urllib.request.urlopen(istek, timeout=HTTP_ZAMAN_ASIMI) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise AgHatasi("GitHub API HTTP %s (%s)" % (e.code, yol))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AgHatasi("GitHub API erisilemedi: %s" % e)


def pages_durum(adet):
    """Site GitHub Pages'te (repo public): son N dagitim /deployments uzerinden.

    (/pages/builds ucu kimliksiz 404 veriyor; /deployments public ve yeterli —
    her dagitimin son durumu /deployments/{id}/statuses ile okunur.)"""
    deps = _gh_get("/repos/%s/deployments?per_page=%d" % (GH_REPO, adet))
    if not deps:
        print("GitHub dagitimi bulunamadi (%s)." % GH_REPO)
        return
    print("GitHub Pages son %d dagitim (%s):" % (len(deps), GH_REPO))
    for d in deps:
        durum = "—"
        try:
            sts = _gh_get("/repos/%s/deployments/%s/statuses?per_page=1"
                          % (GH_REPO, d.get("id")))
            if sts:
                durum = sts[0].get("state", "—")
        except AgHatasi:
            pass  # tekil durum okunamazsa satiri durumsuz birak
        print("  %-10s %-20s %-14s sha=%s"
              % (d.get("environment", "?"), d.get("created_at", "—"), durum,
                 (d.get("sha") or "")[:8] or "—"))


# ---------------------------------------------------------------- DNS
def dns_durum(token):
    zres = _cf_istek("/zones?name=pruvo3d.com", token,
                     "Zone → Zone → Read")
    zonlar = zres.get("result") or []
    if not zonlar:
        raise AgHatasi("pruvo3d.com zone'u bu hesapta gorunmuyor.")
    zid = zonlar[0]["id"]
    print("zone: pruvo3d.com (id=%s, durum=%s)"
          % (_maske(zid, 4), zonlar[0].get("status", "?")))
    res = _cf_istek("/zones/%s/dns_records?per_page=100" % zid, token,
                    "Zone → DNS → Read (wrangler OAuth bu kapsami TASIMIYOR; DNS icin "
                    "'Zone.DNS Read' kapsamli CLOUDFLARE_API_TOKEN gerekir)")
    kayitlar = res.get("result") or []
    print("DNS kayitlari (%d) — icerikler maskeli:" % len(kayitlar))
    for r in kayitlar:
        print("  %-6s %-40s proxied=%-5s icerik=%s"
              % (r.get("type"), r.get("name"), r.get("proxied"),
                 _maske(r.get("content"))))


# ---------------------------------------------------------------- orkestra
def _kosu(ad, fn):
    print("== %s ==" % ad, flush=True)
    try:
        fn()
        print(flush=True)
        return RC_OK
    except YetkiEksik as e:
        print("YETKI/KIMLIK EKSIK: %s\n" % e, flush=True)
        return RC_YETKI
    except AgHatasi as e:
        print("AG/UC HATASI: %s\n" % e, flush=True)
        return RC_AG


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d1", action="store_true", help="D1 katalog durumu (d1-sync.py uzerinden)")
    ap.add_argument("--r2", action="store_true", help="R2 kova listesi + nesne/boyut")
    ap.add_argument("--pages", action="store_true", help="GitHub Pages son dagitimlar")
    ap.add_argument("--dns", action="store_true", help="pruvo3d.com DNS kayitlari (maskeli)")
    ap.add_argument("--hepsi", action="store_true", help="hepsini sirayla")
    ap.add_argument("-n", type=int, default=5, help="--pages icin dagitim sayisi (vars. 5)")
    a = ap.parse_args()
    if not (a.d1 or a.r2 or a.pages or a.dns or a.hepsi):
        ap.print_help()
        return RC_OK

    rcler = []
    if a.d1 or a.hepsi:
        rcler.append(_kosu("D1", d1_durum))

    token = acc = None
    cf_gerek = a.r2 or a.dns or a.hepsi
    if cf_gerek:
        try:
            token, acc, kaynak = kimlik_bul()
            print("kimlik: %s (deger yazilmaz)" % kaynak)
            acc = hesap_id_bul(token, acc)
            print("hesap: id=%s\n" % _maske(acc, 4))
        except (YetkiEksik, AgHatasi) as e:
            print("KIMLIK HATASI: %s" % e)
            return RC_YETKI if isinstance(e, YetkiEksik) else RC_AG

    if a.r2 or a.hepsi:
        rcler.append(_kosu("R2", lambda: r2_durum(token, acc)))
    if a.pages or a.hepsi:
        rcler.append(_kosu("PAGES", lambda: pages_durum(a.n)))
    if a.dns or a.hepsi:
        rcler.append(_kosu("DNS", lambda: dns_durum(token)))

    if RC_YETKI in rcler:
        return RC_YETKI
    if RC_AG in rcler:
        return RC_AG
    return RC_OK


if __name__ == "__main__":
    sys.exit(main())
