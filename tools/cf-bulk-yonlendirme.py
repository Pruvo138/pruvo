#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KALICI 301 — Cloudflare Bulk Redirects kurucusu (TEK KAYNAK: tools/yonlendirmeler.py).

NEDEN VAR
---------
Yayin origin'i GitHub Pages'tir ve sunucu tarafi 301 URETEMEZ; bugunku mekanizma
`canonical` + 0 sn `meta-refresh` (bkz. tools/yonlendirmeler.py ust bilgisi). Gercek
301 yalnizca onundeki Cloudflare zone'unda kurulabilir. Zone'un A kayitlari
`proxied=True` oldugu icin kenar kurallari trafigi GORUR ⇒ Bulk Redirects calisir.

BU ARAC IKINCI KOPYA TUTMAZ: 5 esleme `yonlendirmeler.py::YONLENDIRMELER`'den,
Cloudflare kimligi `cf-durum.py::kimlik_bul`'dan OKUNUR.

KOLLAR
------
  --olc       SALT OKUMA. Token'in liste/kural yetkisini ve mevcut durumu olcer.
              Hicbir yazma yapmaz; ana oturumda kosulabilir.
  --csv YOL   Panel yuklemesi icin CSV uretir (yazma yalnizca yerel dosyaya).
              🔴 OLCULDU (11 Eyl 2026, canli panel turu): CF panelinin "Drag and drop
              a CSV file" kolu BASLIK SATIRINI DA BIR KAYIT SAYAR — 5 satirlik basliklI
              dosya panelde 6 redirect uretir ve ilki `source -> target` olur. Panele
              yuklerken `--basliksiz` kullan; basliklI bicim yalnizca insan okumasi
              ve belge icindir.
  --basliksiz --csv ile birlikte: baslik satirini YAZMA (panel yuklemesi icin).
  --kur       Listeyi olusturur/gunceller ve kurali **enabled=false** yazar.
              Kurali ACMA adimi BILEREK yapilmaz: acma = yayin yuzeyini degistiren
              tik, o OKAN KAPISI'dir.
  --dogrula   5 eski URL'yi ister, gercek 3xx + Location + hedef 200 olcer.
  --kendini-test  Ag'a CIKMADAN ic iddialari kosar.

KURULU DURUM (11 Eyl 2026, panelden elle kuruldu — API yolu 403)
----------------------------------------------------------------
Hesap `dbbe…` → Delivery & performance → Bulk redirects:
  liste `pruvo_beyaz_esya_301`  — 5 redirect, Status **Active**
  kural `beyaz-esya-kapsam-301` — Associated List yukaridaki, Enabled **Disabled**
Kalan TEK adim OKAN'IN TIKIDIR: kural satirinin `...` menusunden Enable.
Taban (kural kapaliyken, 11 Eyl 23:5x): `--dogrula` → **GERCEK_3XX=0/5** (5 kaynak 200,
5 hedef 200). Okan tiklayinca ayni komut **5/5** basmali.
🔴 API YOLU KAPALI, OLCULDU: hem `.cf-token` hem wrangler OAuth kimligi
`/accounts/{id}/rules/lists` ve `.../rulesets/...` uclarinda **HTTP 403**. `--kur`
kolunun calismasi icin token'a `Account Filter Lists: Edit` + `Account Rulesets: Edit`
kapsamlari EKLENMELIDIR (token kapsami degistirmek OKAN KAPISI'dir).

CIKIS KODU SOZLESMESI (iki yonlu): basilan `❌` sayisi >0 ise rc!=0; =0 ise rc=0.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import urllib.error
import urllib.request

_BURASI = os.path.dirname(os.path.abspath(__file__))
if _BURASI not in sys.path:
    sys.path.insert(0, _BURASI)

import importlib

_cf = importlib.import_module("cf-durum")
_yon = importlib.import_module("yonlendirmeler")

KOK = "https://pruvo3d.com"
# Cloudflare liste adi sozlesmesi: ^[a-zA-Z0-9_]+$ (TIRE KABUL EDILMEZ).
LISTE_ADI = "pruvo_beyaz_esya_301"
KURAL_ACIKLAMA = "beyaz-esya-kapsam-301"
CSV_BASLIK = ["source", "target", "status", "preserve_query_string",
              "include_subdomains", "subpath_matching", "preserve_path_suffix"]


def esleme_tablosu():
    """[(kaynak_url, hedef_url, gerekce)] — TEK KAYNAK'tan turetilir."""
    return [("%s/%s/" % (KOK, eski), "%s/%s/" % (KOK, hedef), gerekce)
            for eski, hedef, gerekce in _yon.YONLENDIRMELER]


def csv_metni(basliklI=True):
    tampon = io.StringIO()
    yazici = csv.writer(tampon, lineterminator="\n")
    if basliklI:
        yazici.writerow(CSV_BASLIK)
    for kaynak, hedef, _ in esleme_tablosu():
        yazici.writerow([kaynak, hedef, 301, "true", "false", "false", "false"])
    return tampon.getvalue()


def liste_ogeleri():
    return [{"redirect": {"source_url": kaynak.replace("https://", ""),
                          "target_url": hedef,
                          "status_code": 301,
                          "preserve_query_string": True,
                          "include_subdomains": False,
                          "subpath_matching": False,
                          "preserve_path_suffix": False}}
            for kaynak, hedef, _ in esleme_tablosu()]


# ------------------------------------------------------------------ olcum
def _wrangler_kimligi():
    """wrangler OAuth kolunu ZORLA sec (dosya tokeni yetkisizse ikinci kimlik).

    `kimlik_bul` sirasi dosya->wrangler oldugu icin dosya kolu varken wrangler'a
    dusulmez; bu yardimci AYNI kaynak koddan (cf-durum) okur, ikinci kopya TUTMAZ.
    """
    import re as _re
    if not os.path.exists(_cf.WRANGLER_TOML):
        raise _cf.YetkiEksik("wrangler OAuth dosyasi YOK: %s" % _cf.WRANGLER_TOML)
    m = _re.search(r'oauth_token\s*=\s*"([^"]+)"', open(_cf.WRANGLER_TOML).read())
    if not m:
        raise _cf.YetkiEksik("wrangler dosyasinda oauth_token YOK")
    return m.group(1), None, "wrangler-oauth(~/.wrangler/config/default.toml)"


def _liste_bul(token, hesap):
    res = _cf._cf_istek("/accounts/%s/rules/lists" % hesap, token,
                        "Account → Account Filter Lists → Read")
    for kayit in res.get("result") or []:
        if kayit.get("name") == LISTE_ADI:
            return kayit
    return None


def _kural_seti(token, hesap):
    return _cf._cf_istek(
        "/accounts/%s/rulesets/phases/http_request_redirect/entrypoint" % hesap,
        token, "Account → Account Rulesets → Read")


def olc(yaz=True, kimlik="varsayilan"):
    """SALT OKUMA durum raporu. (hata_sayisi, bilgi) dondur."""
    hata = []
    token, hesap_ipucu, kaynak = (_wrangler_kimligi() if kimlik == "wrangler"
                                  else _cf.kimlik_bul())
    if yaz:
        print("kimlik: %s (deger yazilmaz)" % kaynak)
    hesap = _cf.hesap_id_bul(token, hesap_ipucu)
    if yaz:
        print("hesap: %s… (maskeli)" % hesap[:4])

    tablo = esleme_tablosu()
    if yaz:
        print("TEK KAYNAK esleme: %d satir (yonlendirmeler.py)" % len(tablo))

    try:
        mevcut = _liste_bul(token, hesap)
        print("LISTE_YETKISI: VAR")
        if mevcut:
            print("LISTE_DURUM: VAR (id=%s…, oge=%s)"
                  % (mevcut["id"][:8], mevcut.get("num_items")))
        else:
            print("LISTE_DURUM: YOK (adi %s)" % LISTE_ADI)
    except _cf.YetkiEksik as e:
        print("LISTE_YETKISI: YOK — %s" % e)
        hata.append("liste yetkisi")

    try:
        kset = _kural_seti(token, hesap)
        kurallar = (kset.get("result") or {}).get("rules") or []
        print("KURAL_YETKISI: VAR (http_request_redirect kural sayisi=%d)" % len(kurallar))
        for k in kurallar:
            print("  kural: %r enabled=%s" % (k.get("description"), k.get("enabled")))
    except _cf.YetkiEksik as e:
        print("KURAL_YETKISI: YOK — %s" % e)
        hata.append("kural yetkisi")

    return len(hata), hata


# ------------------------------------------------------------------ kurulum
def kur(kimlik="varsayilan"):
    hata = 0
    token, hesap_ipucu, _ = (_wrangler_kimligi() if kimlik == "wrangler"
                             else _cf.kimlik_bul())
    hesap = _cf.hesap_id_bul(token, hesap_ipucu)

    mevcut = _liste_bul(token, hesap)
    if mevcut is None:
        res = _cf._cf_istek(
            "/accounts/%s/rules/lists" % hesap, token,
            "Account → Account Filter Lists → Edit", method="POST",
            data={"name": LISTE_ADI, "kind": "redirect",
                  "description": "Beyaz esya kapsam disi 5 slug -> kapsam ICI hedef "
                                 "(kaynak: tools/yonlendirmeler.py)"})
        liste_id = res["result"]["id"]
        print("LISTE OLUSTURULDU: id=%s…" % liste_id[:8])
    else:
        liste_id = mevcut["id"]
        print("LISTE ZATEN VAR: id=%s… (ogeler DEGISTIRILECEK)" % liste_id[:8])

    _cf._cf_istek("/accounts/%s/rules/lists/%s/items" % (hesap, liste_id), token,
                  "Account → Account Filter Lists → Edit", method="PUT",
                  data=liste_ogeleri())
    print("OGE YAZILDI: %d satir" % len(liste_ogeleri()))

    kset = _kural_seti(token, hesap)
    kurallar = list((kset.get("result") or {}).get("rules") or [])
    yeni = {"expression": 'http.request.full_uri in $%s' % LISTE_ADI,
            "description": KURAL_ACIKLAMA,
            "action": "redirect",
            "action_parameters": {"from_list": {"name": LISTE_ADI,
                                                "key": "http.request.full_uri"}},
            "enabled": False}
    kalanlar = [k for k in kurallar if k.get("description") != KURAL_ACIKLAMA]
    govde = [{ana: k[ana] for ana in ("expression", "description", "action",
                                      "action_parameters", "enabled") if ana in k}
             for k in kalanlar] + [yeni]
    _cf._cf_istek(
        "/accounts/%s/rulesets/phases/http_request_redirect/entrypoint" % hesap, token,
        "Account → Account Rulesets → Edit", method="PUT", data={"rules": govde})
    print("KURAL YAZILDI: %r enabled=False (ACMA = OKAN KAPISI)" % KURAL_ACIKLAMA)
    return hata


# ------------------------------------------------------------------ dogrulama
def _istek(url):
    """(durum_kodu, location) — yonlendirmeyi TAKIP ETMEZ."""
    class _Durdur(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    acici = urllib.request.build_opener(_Durdur)
    istek = urllib.request.Request(url, method="GET",
                                   headers={"User-Agent": "pruvo-yonlendirme-olcum"})
    try:
        with acici.open(istek, timeout=20) as r:
            return r.status, r.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")


def dogrula():
    hata = 0
    gercek_3xx = 0
    for kaynak, hedef, _ in esleme_tablosu():
        kod, konum = _istek(kaynak)
        if kod == 301 and konum and konum.rstrip("/") == hedef.rstrip("/"):
            gercek_3xx += 1
            print("✅ %s -> %s (%s)" % (kaynak, konum, kod))
        else:
            hata += 1
            print("❌ %s -> kod=%s Location=%s (beklenen 301 -> %s)"
                  % (kaynak, kod, konum, hedef))
        hkod, _ = _istek(hedef)
        if hkod != 200:
            hata += 1
            print("❌ HEDEF %s kod=%s (beklenen 200)" % (hedef, hkod))
    print("GERCEK_3XX=%d/%d" % (gercek_3xx, len(esleme_tablosu())))
    return hata


# ------------------------------------------------------------------ oz test
def kendini_test():
    hata = 0
    tablo = esleme_tablosu()
    if len(tablo) != len(_yon.YONLENDIRMELER):
        hata += 1
        print("❌ A1 tablo uzunlugu TEK KAYNAK ile ayrisiyor")
    else:
        print("✅ A1 tablo TEK KAYNAK ile ayni uzunlukta (%d)" % len(tablo))

    if all(k.startswith(KOK + "/") and k.endswith("/") for k, _, _ in tablo):
        print("✅ A2 tum kaynak URL'leri mutlak ve sondaki / ile")
    else:
        hata += 1
        print("❌ A2 kaynak URL bicimi bozuk")

    if any(k == h for k, h, _ in tablo):
        hata += 1
        print("❌ A3 kaynak == hedef olan satir var (dongu)")
    else:
        print("✅ A3 kaynak != hedef (dongu yok)")

    hedef_slug = {h.rstrip("/").rsplit("/", 1)[-1] for _, h, _ in tablo}
    eski_slug = {k.rstrip("/").rsplit("/", 1)[-1] for k, _, _ in tablo}
    if hedef_slug & eski_slug:
        hata += 1
        print("❌ A4 bir hedef ayni zamanda kaldirilan slug (zincir)")
    else:
        print("✅ A4 hedefler kaldirilan slug kumesinden ayrik")

    satirlar = csv_metni().strip().split("\n")
    if len(satirlar) == len(tablo) + 1 and satirlar[0] == ",".join(CSV_BASLIK):
        print("✅ A5 CSV %d satir + baslik" % len(tablo))
    else:
        hata += 1
        print("❌ A5 CSV bicimi bozuk")

    # A9 — panele giden bicimde baslik OLMAMALI (canli panel basligi kayit sayiyor)
    basliksiz = csv_metni(basliklI=False).strip().split("\n")
    if len(basliksiz) == len(tablo) and not basliksiz[0].startswith("source,"):
        print("✅ A9 --basliksiz CSV tam %d satir, baslik YOK" % len(tablo))
    else:
        hata += 1
        print("❌ A9 basliksiz CSV hala baslik tasiyor ya da satir sayisi yanlis")

    if all(o["redirect"]["status_code"] == 301 for o in liste_ogeleri()):
        print("✅ A6 tum oge status_code=301")
    else:
        hata += 1
        print("❌ A6 301 disi status_code var")

    import re as _re
    if _re.match(r"^[a-zA-Z0-9_]+$", LISTE_ADI):
        print("✅ A7 liste adi CF sozlesmesine uyuyor (%s)" % LISTE_ADI)
    else:
        hata += 1
        print("❌ A7 liste adi CF sozlesmesini ihlal ediyor: %s" % LISTE_ADI)

    if all(not o["redirect"]["source_url"].startswith("https://")
           for o in liste_ogeleri()):
        print("✅ A8 source_url semasiz (CF bulk redirect sozlesmesi)")
    else:
        hata += 1
        print("❌ A8 source_url sema tasiyor")

    # KONTROL: gecerli bir tabloda ihlal URETILMEMELI
    print("(kontrol) K1 TEK KAYNAK okundu, ag cagrisi yapilmadi")
    print("DUSEN: %d" % hata)
    return hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--olc", action="store_true")
    ap.add_argument("--csv", metavar="YOL")
    ap.add_argument("--basliksiz", action="store_true",
                    help="--csv ile: baslik satirini YAZMA (CF paneli onu kayit sayar)")
    ap.add_argument("--kur", action="store_true")
    ap.add_argument("--dogrula", action="store_true")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--kimlik", choices=["varsayilan", "wrangler"],
                    default="varsayilan",
                    help="wrangler: dosya tokeni yetkisizse OAuth kimligini ZORLA")
    a = ap.parse_args()

    if not any([a.olc, a.csv, a.kur, a.dogrula, a.kendini_test]):
        ap.print_help()
        return 2

    hata = 0
    if a.kendini_test:
        hata += kendini_test()
    if a.csv:
        with open(a.csv, "w") as f:
            f.write(csv_metni(basliklI=not a.basliksiz))
        print("CSV YAZILDI: %s (%d satir)" % (a.csv, len(esleme_tablosu())))
    if a.olc:
        try:
            n, _ = olc(kimlik=a.kimlik)
            hata += n
        except (_cf.YetkiEksik, _cf.AgHatasi) as e:
            print("OLCULEMEDI: %s" % e)
            return 2
    if a.kur:
        try:
            hata += kur(kimlik=a.kimlik)
        except (_cf.YetkiEksik, _cf.AgHatasi) as e:
            print("KURULAMADI: %s" % e)
            return 2
    if a.dogrula:
        hata += dogrula()
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
