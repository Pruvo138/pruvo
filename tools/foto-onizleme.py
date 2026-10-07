#!/usr/bin/env python3
"""pruvo-shop ONIZLEME SURUMU — kurulum / yukleme / sokum (FOTO-DUZEN-d, 7 Eki 2026).

CANLIYI ETKILEMEZ: yalniz `wrangler versions upload --preview-alias` (deploy YOK). Yapilandirma
shop/wrangler.onizleme.toml (ayri D1 + ayri kova + statik varliklar, rota/cron yok, odeme kapali).

  python3 tools/foto-onizleme.py statik   # shop/.onizleme-statik kurar (yalniz bakmak icin; SILMEYI unutma)
  python3 tools/foto-onizleme.py yukle    # statik kur -> versions upload -> statik dizini SIL (try/finally)
  python3 tools/foto-onizleme.py sokum    # Okan "gordum" deyince kosulacak sokum komutlarini basar

Statik dizin: sayfa + foto bolumu dosyalari; katalog verisi BOS saplama (urunler.json = [],
ozet.json = {}) -> onizlemede katalog bos, foto bolumu calisir. Sir dosyasi kopyalanmaz (liste kapali).
"""
import os
import shutil
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
STATIK = os.path.join(SHOP, ".onizleme-statik")
TOML = os.path.join(SHOP, "wrangler.onizleme.toml")
ALIAS = "foto-onizleme"
HESAP = "dbbe2a8620c3c3a57c586b8a98142fb9"
# KAPALI liste: yalniz bunlar kopyalanir (sir/veri dosyasi kazara tasinamaz).
DOSYALAR = ["index.html", "foto-uretim.js", "foto-uretim-veri.js", "secenekler.js",
            "konfigur.js", "attribution-ref.js", "taban-fiyatlar.js", "filament-veri.js"]
SAPLAMA = {"urunler.json": "[]\n", "ozet.json": "{}\n"}


def statik_kur():
    if os.path.exists(STATIK):
        shutil.rmtree(STATIK)
    os.mkdir(STATIK)
    for ad in DOSYALAR:
        kaynak = os.path.join(KOK, ad)
        if os.path.isfile(kaynak):
            shutil.copyfile(kaynak, os.path.join(STATIK, ad))
        else:
            print("ATLANDI=" + ad)
    for ad, icerik in SAPLAMA.items():
        with open(os.path.join(STATIK, ad), "w") as f:
            f.write(icerik)
    return sorted(os.listdir(STATIK))


def yukle():
    try:
        print("STATIK=" + ",".join(statik_kur()))
        ortam = dict(os.environ, CLOUDFLARE_ACCOUNT_ID=HESAP)
        komut = ["npx", "--no-install", "wrangler", "versions", "upload", "-c", TOML,
                 "--preview-alias", ALIAS, "--message", "foto onizleme (canli degil)"]
        return subprocess.run(komut, cwd=SHOP, env=ortam).returncode
    finally:
        shutil.rmtree(STATIK, ignore_errors=True)
        print("STATIK_SILINDI=" + str(not os.path.exists(STATIK)))


SOKUM = """# SOKUM (Okan "gordum" dedikten sonra; CLOUDFLARE_ACCOUNT_ID=%s, shop/ dizininden)
# 1) onizleme URL'lerini kapat (canli workers.dev zaten kapali kalir):
#    PUT /accounts/<hesap>/workers/scripts/pruvo-shop/subdomain {"enabled":false,"previews_enabled":false}
# 2) Turnstile widget alan listesinden onizleme alanini cikar (PUT .../challenges/widgets/<sitekey>, domains=["pruvo3d.com"])
# 3) onizleme veritabani ve kovasi:
npx wrangler r2 object delete --remote pruvo-ozel-onizleme/<anahtar>   # kovadaki her nesne (liste: rapor)
npx wrangler r2 bucket delete pruvo-ozel-onizleme
npx wrangler d1 delete pruvo-katalog-onizleme -y
# 4) onizleme surumu aktif dagitimda degildir; alias'siz kalinca erisilemez. Surum gecmisi silinmez
#    (Cloudflare surum silme ucu sunmaz) — preview_urls kapaninca URL 404 doner.
""" % HESAP


def main():
    alt = sys.argv[1] if len(sys.argv) > 1 else ""
    if alt == "statik":
        print("STATIK=" + ",".join(statik_kur()))
        return 0
    if alt == "yukle":
        return yukle()
    if alt == "sokum":
        print(SOKUM)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
