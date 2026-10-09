#!/usr/bin/env python3
"""pruvo-shop ONIZLEME SURUMU — kurulum / yukleme / sokum (FOTO-DUZEN-d, 7 Eki 2026).

CANLIYI ETKILEMEZ: yalniz `wrangler versions upload --preview-alias` (deploy YOK). Yapilandirma
shop/wrangler.onizleme.toml (ayri D1 + ayri kova + statik varliklar, rota/cron yok, odeme kapali).

  python3 tools/foto-onizleme.py statik   # shop/.onizleme-statik kurar (yalniz bakmak icin; SILMEYI unutma)
  python3 tools/foto-onizleme.py yukle    # statik kur -> versions upload -> statik dizini SIL (try/finally)
  python3 tools/foto-onizleme.py sokum    # Okan "gordum" deyince kosulacak sokum komutlarini basar

Statik dizin: sayfa + foto bolumu dosyalari; katalog verisi BOS saplama (urunler.json = [],
ozet.json = {}) -> onizlemede katalog bos, foto bolumu calisir. Sir dosyasi kopyalanmaz (liste kapali).

SHA DAMGASI + TEK-YUKLEYICI KILIDI (BaBa 17:0x, 9 Eki 2026):
- statik_kur: statik dizine `onizleme-surum.json` yazar = {"sha", "dal", "kirli"} (HEAD/dal/kirli_sayisi).
  Yukleme adimi KIRLI agactaysa (kirli>0) YUKLEME REDDEDILIR (rc 2); commit'siz kod onizlemeye cikmaz.
  Kirli sayimi statik dizin OLUSMADAN once olculur ve sayimdan YALNIZ `shop/.onizleme-statik/` dislanir
  (dizin git'e gorunur, ignore degil; temiz agacta sahte kirli=1 basiyordu — 9 Eki). Baska yol dislanmaz.
- yukle: `pruvo-onizleme.lock` uzerinde TEK YUKLEYICI kilidi (fcntl.flock, bloklayan, en cok 900 sn;
  asilirsa rc 2 "YUKLE RED kilit-zaman-asimi"). Kilit dosyasi is bitince SILINMEZ ama icerigi bos
  kalir (lock: makinede yeni dosya tek, baska iz YOK).
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
STATIK = os.path.join(SHOP, ".onizleme-statik")
TOML = os.path.join(SHOP, "wrangler.onizleme.toml")
ALIAS = "foto-onizleme"
HESAP = "dbbe2a8620c3c3a57c586b8a98142fb9"
# KAPALI liste: yalniz bunlar kopyalanir (sir/veri dosyasi kazara tasinamaz).
# 2 dosya (taban-fiyatlar.js + filament-veri.js) ana checkout'tan (bu branch'te yoklar); sayfa 404 aliyordu.
DOSYALAR = ["index.html", "foto-uretim.js", "foto-uretim-veri.js", "secenekler.js",
            "konfigur.js", "attribution-ref.js", "taban-fiyatlar.js", "filament-veri.js"]
ANA = "/Users/okan/dev/pruvo"  # ana checkout kokue: 2 dosya oradan alinir (bu branch'te yok)
SAPLAMA = {"urunler.json": "[]\n", "ozet.json": "{}\n"}
STATIK_GIT = "shop/.onizleme-statik/"  # porcelain yolu (repo kokune gore); kirli sayimindan YALNIZ bu dislanir
SURUM_DOSYA = "onizleme-surum.json"  # statik dizine yazilan SHA damgasi (worker'dan okunur)
KILIT_AD = "pruvo-onizleme.lock"     # TEK YUKLEYICI kilit dosyasi (git-common-dir altinda)
KILIT_TAVAN = 900                    # flock en cok 900 sn; asarsa rc 2


def _git(*args):
    """git komutunu liste olarak calistir; stdout text (hata stderr)."""
    return subprocess.run(("git",) + args, cwd=KOK, capture_output=True, text=True)


def _kirli_sayisi():
    p = _git("status", "--porcelain")
    if p.returncode != 0:
        return -1
    return sum(1 for s in p.stdout.splitlines() if s.strip() and not s[3:].startswith(STATIK_GIT))


def _damga_olc():
    """{sha, dal, kirli} olc (kirli=-1 hata durumu)."""
    sha = (_git("rev-parse", "HEAD").stdout or "").strip()
    dal = (_git("rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()
    return {"sha": sha, "dal": dal, "kirli": _kirli_sayisi()}


def _damga_yazi(cikti=None):
    """statik dizine SHA damgasi yaz. cikti verilmezse YAZMA aninda olcer."""
    if cikti is None:
        cikti = _damga_olc()
    with open(os.path.join(STATIK, SURUM_DOSYA), "w") as f:
        json.dump(cikti, f, ensure_ascii=False, sort_keys=True)


def statik_kur():
    damga = _damga_olc()  # STATIK olusmadan ONCE: dizin sayima girmesin
    if os.path.exists(STATIK):
        shutil.rmtree(STATIK)
    os.mkdir(STATIK)
    for ad in DOSYALAR:
        kaynak = os.path.join(ANA, ad) if ad in ("taban-fiyatlar.js", "filament-veri.js") else os.path.join(KOK, ad)
        if os.path.isfile(kaynak):
            shutil.copyfile(kaynak, os.path.join(STATIK, ad))
        else:
            print("ATLANDI=" + ad)
    for ad, icerik in SAPLAMA.items():
        with open(os.path.join(STATIK, ad), "w") as f:
            f.write(icerik)
    _damga_yazi(damga)
    return sorted(os.listdir(STATIK))


def _kilitle():
    """TEK YUKLEYICI kilidi acar; icerigi bos; geri donen dosya handle ile finally'de unlock.

    Bloklayan mod: 1 sn aralikla LOCK_NB dener; KILIT_TAVAN sn dolunca TimeoutError.
    """
    ortak = _git("rev-parse", "--git-common-dir")
    kok = (ortak.stdout or "").strip() or os.path.join(KOK, ".git")
    kilit_yol = os.path.join(kok, KILIT_AD)
    f = open(kilit_yol, "w")
    baslangic = time.monotonic()
    while True:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except OSError:
            if time.monotonic() - baslangic >= KILIT_TAVAN:
                f.close()
                raise TimeoutError("kilit-zaman-asimi")
            time.sleep(1)


def yukle():
    fk = None
    try:
        fk = _kilitle()
    except TimeoutError:
        print("YUKLE RED kilit-zaman-asimi")
        return 2
    except Exception:
        print("YUKLE RED kilit-acilamadi")
        return 2
    try:
        kirli = _kirli_sayisi()
        if kirli > 0:
            print("YUKLE RED kirli-agac kirli=" + str(kirli))
            return 2
        if kirli < 0:
            print("YUKLE RED git-status-hatasi")
            return 2
        print("STATIK=" + ",".join(statik_kur()))
        ortam = dict(os.environ, CLOUDFLARE_ACCOUNT_ID=HESAP)
        komut = ["npx", "--no-install", "wrangler", "versions", "upload", "-c", TOML,
                 "--preview-alias", ALIAS, "--message", "foto onizleme (canli degil)"]
        return subprocess.run(komut, cwd=SHOP, env=ortam).returncode
    finally:
        if fk is not None:
            try:
                fcntl.flock(fk.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                fk.truncate(0)  # kilit dosyasi is bitince SILINMEZ ama icerigi bos kalir
            except Exception:
                pass
            fk.close()
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
