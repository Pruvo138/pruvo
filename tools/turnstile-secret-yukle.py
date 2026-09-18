#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TURNSTILE SECRET YAYIN ARACI (17 Eyl 2026) — `TURNSTILE_SECRET` worker secret'ini kurar.

NE YAPAR
  --kuru (VARSAYILAN)  CF API'den `pruvo-odeme` widget'ini BULUR; sitekey'i (PUBLIC) ve
                       secret'in UZUNLUGUNU basar. Hicbir seye YAZMAZ, wrangler CAGIRMAZ.
  --uygula             Widget secret'ini API'den okur ve `npx wrangler secret put
                       TURNSTILE_SECRET` surecine **STDIN'den** verir (cwd = shop/).
                       wrangler'in rc'si aynen yansitilir.

🔴 SECRET HICBIR YERE DUSMEZ: ne stdout'a, ne stderr'e, ne argv'ye (komut satiri `ps` ile
   okunur!), ne dosyaya, ne loga. Tek cikis kapisi cocuk surecin STDIN'idir. Bu yuzden
   `--uygula` kolu secret'i degiskende tutar, basmaz ve hata mesajlarinda TASIMAZ.
   Ayni sebeple CF API token'i da ("~/.claude/cron/.cf-token") asla yazdirilmaz.

YAYIN SIRASI (mimarda): merge -> Pages deploy -> worker deploy -> BU ARAC --uygula.
Kod once cikar, secret EN SON konur; worker o ana kadar FAIL-OPEN'dir (secret yoksa gecirir),
yani arada odeme yolu DUSMEZ.

Kullanim:
  python3 tools/turnstile-secret-yukle.py            # kuru kosum (olcum)
  python3 tools/turnstile-secret-yukle.py --uygula   # secret'i canliya koyar
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
TOKEN_YOLU = os.path.expanduser("~/.claude/cron/.cf-token")
WIDGET_ADI = "pruvo-odeme"
ZONE_ADI = "pruvo3d.com"
API = "https://api.cloudflare.com/client/v4"
SECRET_ADI = "TURNSTILE_SECRET"


def cikis(kod, *satirlar):
    for s in satirlar:
        print(s)
    sys.exit(kod)


def token_oku():
    if not os.path.exists(TOKEN_YOLU):
        cikis(2, "HAL=TOKEN_YOK", "CF API token dosyasi bulunamadi: " + TOKEN_YOLU)
    with open(TOKEN_YOLU, encoding="utf-8") as f:
        t = f.read().strip()
    if not t:
        cikis(2, "HAL=TOKEN_BOS")
    return t


def cagir(token, yol):
    """CF API GET. Donus: (sonuc, hata_metni). Token hicbir cikti yoluna girmez."""
    istek = urllib.request.Request(API + yol, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(istek, timeout=20) as c:
            veri = json.loads(c.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            veri = json.loads(e.read().decode("utf-8"))
        except Exception:
            return None, "HTTP " + str(e.code)
    except Exception as e:
        return None, type(e).__name__
    if not veri.get("success"):
        return None, json.dumps(veri.get("errors") or [], ensure_ascii=False)
    return veri.get("result"), ""


def hesap_id(token):
    zonlar, hata = cagir(token, "/zones?name=" + ZONE_ADI)
    if zonlar:
        for z in zonlar:
            hid = (z.get("account") or {}).get("id")
            if hid:
                return hid, ""
    hesaplar, hata2 = cagir(token, "/accounts")
    if hesaplar:
        return hesaplar[0].get("id"), ""
    return None, (hata or hata2 or "hesap bulunamadi")


def widget_bul(token, hid):
    """(widget | None, hata). Widget detayi secret'i tasir — DONDURULUR ama BASILMAZ."""
    liste, hata = cagir(token, "/accounts/" + hid + "/challenges/widgets")
    if liste is None:
        return None, hata
    for w in liste:
        if w.get("name") == WIDGET_ADI:
            detay, dhata = cagir(token, "/accounts/" + hid + "/challenges/widgets/" +
                                 str(w.get("sitekey")))
            return (detay or w), dhata
    return None, ""


def main():
    uygula = "--uygula" in sys.argv[1:]
    bilinmeyen = [a for a in sys.argv[1:] if a not in ("--uygula", "--kuru")]
    if bilinmeyen:
        cikis(2, "HAL=ARGUMAN", "bilinmeyen arguman: " + " ".join(bilinmeyen))

    token = token_oku()
    hid, hata = hesap_id(token)
    if not hid:
        cikis(3, "HAL=HESAP_YOK", "API: " + hata)

    widget, whata = widget_bul(token, hid)
    if widget is None:
        cikis(4, "HAL=WIDGET_YOK",
              "widget adi: " + WIDGET_ADI,
              "API: " + (whata or "hesapta bu adda widget yok"),
              "Widget olusturma YETKISI gerekir (Turnstile: Edit). Panelden ya da yetkili "
              "token ile olusturulmali; sonra bu arac --uygula ile secret'i koyar.")

    sitekey = str(widget.get("sitekey") or "")
    secret = str(widget.get("secret") or "")
    print("HESAP=" + hid)
    print("WIDGET=" + WIDGET_ADI)
    print("SITEKEY=" + sitekey)                      # PUBLIC deger — koda da girer
    print("DOMAINS=" + ",".join(widget.get("domains") or []))
    print("MODE=" + str(widget.get("mode") or ""))
    print("SECRET_UZUNLUK=" + str(len(secret)))      # 🔴 degerin KENDISI asla basilmaz

    if not uygula:
        cikis(0, "HAL=KURU", "Uygulamak icin: python3 tools/turnstile-secret-yukle.py --uygula")

    if not secret:
        cikis(5, "HAL=SECRET_OKUNAMADI",
              "API widget kaydinda secret alani YOK (token'in Turnstile okuma yetkisi dar "
              "olabilir). Secret elle konacaksa: cd shop && npx wrangler secret put " + SECRET_ADI)

    # 🔴 Secret YALNIZ stdin'den gider: argv'ye/dosyaya/ortam degiskenine KONMAZ.
    surec = subprocess.run(["npx", "wrangler", "secret", "put", SECRET_ADI],
                           cwd=SHOP, input=(secret + "\n").encode("utf-8"))
    print("WRANGLER_RC=" + str(surec.returncode))
    cikis(surec.returncode, "HAL=" + ("UYGULANDI" if surec.returncode == 0 else "WRANGLER_HATA"))


if __name__ == "__main__":
    main()
