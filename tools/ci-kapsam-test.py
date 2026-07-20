#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI KAPSAM KAPISI — her kabul testi ya CI'da kosuluyor ya da GEREKCELI olarak muaf.

NEDEN VAR (denetim, 20 Tem): .github/workflows/deploy.yml uzun sure YALNIZ 2 test kosuyordu
(kisisel-veri + kategori-parite). Repodaki onlarca kabul testi hicbir push'ta kosmadigi icin
"olu nobetci" bir test CI'dan YESIL/success alarak gecebiliyordu (B paketi olu sepet nobetcisi
son 4 kosumda success aldi). Bu kapi FAIL-CLOSED bir kapsam bekcisidir: repoda IZLENEN
(git ls-files) her kabul-testi dosyasi ya deploy.yml'de FIILEN kosulur, ya da asagidaki
IZIN_LISTESI'nde GEREKCE ile muaf tutulur. Ucuncu bir hal yoktur -> yeni bir test sessizce
CI-disi kalamaz.

KESIF (discovery) — git ls-files uzerinden (CI checkout == yerel; os.walk kullanılmaz cunku
gitignore'lu/uretilmis dosyalar yerelde gorunup CI'da gorunmez, sapma yaratirdi):
  * tools/  (arsiv/ HARIC):  <ad>-test.(py|js)  VEYA  test-<ad>.(py|js)
  * shop/test, onizleme/test, jenerator/test:  o dizinin DOGRUDAN altindaki .py/.js/.mjs/.cjs
    (alt dizinler — jenerator/test/aileler, esleme — fikstur/aile verisi, kosulabilir suite degil)

KABUL (bu dosyanin kendi kabul testleri):
  1. IZLENEN her kabul testi ya kosuluyor ya IZIN_LISTESI'nde -> degilse exit 1 (KAPSAMSIZ).
  2. IZIN_LISTESI'nde GEREKCESIZ (bos) giris -> exit 1.
  3. IZIN_LISTESI'nde olup artik KESFEDILMEYEN (silinmis/yeniden adlandirilmis) giris -> exit 1
     (liste curumesin).
  4. IZIN_LISTESI'nde olup AYNI ZAMANDA deploy.yml'de kosulan giris -> exit 1 (bayat muafiyet;
     kosuluyorsa listeden cikarilmali).
KIRMIZI-MUTASYON: deploy.yml'den bir "python3 tools/<x>-test.py" satiri silinirse o test
kapsamsiz kalir -> kapi KIRMIZI (exit 1). (--deploy <yol> ile alternatif/mutasyonlu bir kopyaya
isaret ederek GERCEK deploy.yml'e dokunmadan kanitlanabilir.)

Kullanim:
    python3 tools/ci-kapsam-test.py
    python3 tools/ci-kapsam-test.py --deploy /gecici/mutant-deploy.yml
"""
import argparse
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DEPLOY_VARSAYILAN = os.path.join(ROOT, ".github", "workflows", "deploy.yml")

# ---- KESIF PREDIKATLARI ----------------------------------------------------
TOOLS_PAT = re.compile(r"^tools/([^/]*-test\.(?:py|js)|test-[^/]*\.(?:py|js))$")
DIR_PAT = re.compile(r"^(?:shop/test|onizleme/test|jenerator/test)/[^/]+\.(?:py|js|mjs|cjs)$")


def kesfet():
    """git ls-files uzerinden IZLENEN kabul-testi dosyalarini (repo-rel yol) dondur."""
    r = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("git ls-files basarisiz: " + r.stderr.strip())
    bulunan = []
    for yol in r.stdout.splitlines():
        if yol.startswith("tools/arsiv/"):
            continue
        if TOOLS_PAT.match(yol) or DIR_PAT.match(yol):
            bulunan.append(yol)
    return sorted(bulunan)


def kosulan(deploy_metin, kesif):
    """deploy.yml metninde FIILEN referans verilen (kosulan) kesif dosyalarini dondur."""
    kos = set()
    for yol in kesif:
        # yol'un hemen ardinda bir dosya-adi karakteri gelmesin (durum-test.py, uzun bir
        # baska yolun on-eki olarak yanlis eslesmesin diye negatif ileri-bakis).
        if re.search(re.escape(yol) + r"(?![\w./-])", deploy_metin):
            kos.add(yol)
    return kos


# ---- GEREKCE SABITLERI -----------------------------------------------------
R_AYRI = ("Ayri alt-proje/dagitim hedefi (shop=Cloudflare Worker, onizleme, jenerator kendi "
          "harness'i). Bu is akisi YALNIZ GitHub Pages site build'i; bu suite o projenin CI "
          "hattinda kosulur, Pages job'una girmez.")
R_NODE = ("CI build job'u Python-only (setup-node yok) -> JS/Node suite'i kosamaz. Ayri bir "
          "node job'u gerekir (RAPOR onerisi).")
R_AG = ("Ag/uzak platform erisimi gerektirir (parite CDN'e vurur) -> CI'da deterministik degil; "
        "ag-izinli ayri adim gerekir (RAPOR onerisi).")
R_YOL = ("Mimar-disiplin kapisi: mutlak /Users/okan/dev/pruvo yoluna VE commit EDILMEYEN "
         ".claude/settings.json + .git/hooks kablolamasina bagli -> GitHub fresh checkout'ta "
         "yapisal olarak KIRMIZI. Yerel gelistirici disiplini araci, deploy CI adimi degil.")
R_YAVAS = ("Yerelde >30s (build+ag ya da mutasyon harness) -> tek build job'unu blokar; "
           "izole/ayri job olmadan Pages hattina alinmaz (RAPOR onerisi).")
R_KIRMIZI = ("Su an KIRMIZI (yerelde olculdu) — B/E paketi onardiktan SONRA CI'ya eklenecek "
             "(paralel isci onariyor). Simdi eklenirse deploy hatti kirilir.")
R_SONRA = ("Offline + yerelde YESIL, ama Paket C kapsami YALNIZ mimarin verdigi cekirdek "
           "eklemeleri CI'ya aldi. Bu test sonraki turda (ubuntu path/env dogrulamasi sonrasi) "
           "CI'ya alinabilir — kod-kilidi ornegi 'yerel-yesil / CI-kirmizi' tuzagini kanitladi, "
           "o yuzden kor-ekleme yapilmadi.")

# ---- IZIN LISTESI (muaf test -> GEREKCE). Bos gerekce = exit 1. ----------
IZIN_LISTESI = {
    # --- Ayri dagitim hedefleri (shop / onizleme / jenerator) ---
    "shop/test/eposta.mjs": R_AYRI,
    "shop/test/kabul.js": R_AYRI,
    "shop/test/olcum-kapisi.cjs": R_AYRI,
    "shop/test/olcum.mjs": R_AYRI,
    "shop/test/ref-route.mjs": R_AYRI,
    "shop/test/sepet-panel.js": R_KIRMIZI,  # mimar mandasi: B/E onarim sonrasi eklenecek
    "onizleme/test/eslem-olcum.py": R_AYRI,
    "onizleme/test/kabul.js": R_AYRI,
    "onizleme/test/kapi1.js": R_AYRI,
    "jenerator/test/birlestir.py": R_AYRI,
    "jenerator/test/dogrula.py": R_AYRI,
    "jenerator/test/fiyat-tablosu-uret.py": R_AYRI,
    "jenerator/test/fiyat-test.js": R_AYRI,
    "jenerator/test/hacim-eval.js": R_AYRI,
    "jenerator/test/kabul.py": R_AYRI,
    "jenerator/test/kalibrasyon-referans-uret.py": R_AYRI,
    "jenerator/test/kalibrasyon-senkron.js": R_AYRI,
    "jenerator/test/stl_hacim.py": R_AYRI,
    "jenerator/test/vida-referans-uret.py": R_AYRI,
    "jenerator/test/vitrin-kabul.js": R_AYRI,
    # --- tools/ JS (CI'da node yok) ---
    "tools/attribution-ref-test.js": R_NODE,
    "tools/marka-limit-test.js": R_NODE,
    "tools/riza-tikkimligi-test.js": R_NODE,
    "tools/parite-test.js": R_AG,
    "tools/url-senkron-test.js": R_KIRMIZI,  # mimar mandasi: su an KIRMIZI
    # --- tools/ python: mimar-disiplin (mutlak yol + commit'siz kablolama) ---
    "tools/mimar-kilit-test.py": R_YOL,
    "tools/mimar-commit-kapisi-test.py": R_YOL,
    "tools/mimar-kapi-mutasyon-test.py": R_YOL,
    "tools/kapi-envanteri-test.py": R_YOL,
    # --- tools/ python: KIRMIZI (mimar mandasi) ---
    "tools/kod-kilidi-test.py": R_KIRMIZI,
    # --- tools/ python: yavas/harici (>30s) ---
    "tools/filament-test.py": R_YAVAS,
    "tools/kaynak-akis-test.py": R_YAVAS,
    "tools/test-bbox-3mf.py": R_YAVAS,
    # --- tools/ python: offline-yesil, sonraki turda alinabilir ---
    "tools/d1-sync-durum-test.py": R_SONRA,
    "tools/denetim-kapisi-test.py": R_SONRA,
    "tools/derin-cap-test.py": R_SONRA,
    "tools/durum-edge-test.py": R_SONRA,
    "tools/durum-test.py": R_SONRA,
    "tools/gorsel-anahtar-test.py": R_SONRA,
    "tools/gorsel-kapisi-test.py": R_SONRA,
    "tools/kaynak-entegrasyon-test.py": R_SONRA,
    "tools/lisans-havuz-test.py": R_SONRA,
    "tools/makerworld-ara-test.py": R_SONRA,
    "tools/makerworld-lisans-test.py": R_SONRA,
    "tools/marka-filtre-test.py": R_SONRA,
    "tools/meta-piksel-test.py": R_SONRA,
    "tools/olculmemis-siparis-test.py": R_SONRA,
    "tools/printables-lisans-test.py": R_SONRA,
    "tools/siparisler-test.py": R_SONRA,
    "tools/surum-test.py": R_SONRA,
    "tools/test-baski-senkron.py": R_SONRA,
    "tools/test-merchant-feed.py": R_SONRA,
    "tools/thing-codex-test.py": R_SONRA,
    "tools/thingiverse-gallery-test.py": R_SONRA,
    "tools/yargi-firearm-test.py": R_SONRA,
    "tools/yazdir-test.py": R_SONRA,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", default=DEPLOY_VARSAYILAN,
                    help="deploy.yml yolu (kirmizi-mutasyon icin alternatif kopya verilebilir)")
    args = ap.parse_args()

    if not os.path.exists(args.deploy):
        sys.exit("deploy.yml bulunamadi: " + args.deploy)
    with open(args.deploy, encoding="utf-8") as f:
        deploy_metin = f.read()

    kesif = kesfet()
    kos = kosulan(deploy_metin, kesif)
    kesif_kume = set(kesif)

    hatalar = []

    # 2) gerekcesiz izin girisi
    for yol, gerekce in IZIN_LISTESI.items():
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ izin girisi (bos gerekce): %s" % yol)

    # 3) bayat izin: kesfedilmeyen (silinmis/yeniden adlandirilmis) yol
    for yol in IZIN_LISTESI:
        if yol not in kesif_kume:
            hatalar.append("BAYAT izin (artik kesfedilmiyor — sil ya da yolu duzelt): %s" % yol)

    # 4) bayat izin: hem izinde hem kosuluyor
    for yol in IZIN_LISTESI:
        if yol in kos:
            hatalar.append("BAYAT izin (test ARTIK KOSULUYOR — izinden cikar): %s" % yol)

    # 1) kapsamsiz: kesfedilmis ama ne kosuluyor ne izinli
    kapsamsiz = []
    for yol in kesif:
        if yol in kos:
            continue
        if yol in IZIN_LISTESI:
            continue
        kapsamsiz.append(yol)
    for yol in kapsamsiz:
        hatalar.append("KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % yol)

    # ---- rapor ----
    muaf = [y for y in kesif if y not in kos]
    print("CI KAPSAM KAPISI")
    print("  Kesfedilen kabul testi : %d" % len(kesif))
    print("  deploy.yml'de kosulan  : %d  (%s)" % (
        len(kos), ", ".join(sorted(kos)) or "-"))
    print("  Muaf (izin listesi)    : %d" % len(muaf))
    print("-" * 70)
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("-" * 70)
        print("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1
    print("SONUC: YESIL ✅  — her kabul testi ya kosuluyor ya gerekceli muaf.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
