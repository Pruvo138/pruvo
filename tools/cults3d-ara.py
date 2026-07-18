#!/usr/bin/env python3
"""Cults3D'te MARKA/terim arar; sitede OLMAYAN + satilabilir + UCRETSIZ + gurultusuz + MARKA-ALAKALI
model SLUG'larini verir. MakerWorld makerworld-ara.py'nin Cults3D esdegeri.

Kullanim:  python3 tools/cults3d-ara.py "Renault" [max]
   -> aday model SLUG'larini bir satirda (bosluk ayirli) yazar + slug/lisans/baslik listesi basar.
   (KIMLIK GEREKIR: env CULTS_USERNAME + CULTS_API_KEY — bkz cults3d-api.py.)

ELER:  * satilamaz lisans (satilabilir() FAIL-CLOSED — Cults tescilli/NC/bilinmeyen)
       * UCRETLI model (price>0) — Cults bir PAZAR; sadece ucretsiz+satilabilir alinir
       * anahtarlik/logo/amblem/minyatur/kit-card gurultusu (COP listesi)
       * \\bMARKA\\b KELIME-SINIRI: printables-api.marka_kelime_gecer() ORTAK filtresi
         (Oxford/afford gibi alt-dize gurultusu elenir; Turkce-duyarli). INLINE DEGIL — import.
       * `.urun-kaynaklari.json`'da zaten kayitli Cults3D slug'lari (dedup)
"""
import importlib.util, os, re, sys

ROOT = "/Users/okan/dev/pruvo"
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(_HERE, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


c3 = _load("cults3d_api", "cults3d-api.py")
pr = _load("printables_api", "printables-api.py")   # ORTAK \bMARKA\b filtresi buradan


def marka_alakali(marka, baslik, tags=None, slug=None):
    r"""Marka, baslik/etiket/slug birlesiminde TAM KELIME (\bMARKA\b) olarak geciyor mu?
    ORTAK filtre pr.marka_kelime_gecer(baslik, marka) uzerine kurulu (inline DEGIL) — metinleri
    birlestirip tek cagriyla test eder. 'ford' -> 'Ford Focus' EVET; 'Oxford'/'afford' HAYIR."""
    parcalar = [baslik or ""]
    if tags:
        parcalar.append(" ".join(tags) if isinstance(tags, (list, tuple)) else str(tags))
    if slug:
        parcalar.append(str(slug).replace("-", " "))
    birlesik = " ".join(parcalar)
    return pr.marka_kelime_gecer(birlesik, marka)


def mevcut_slugler():
    """`.urun-kaynaklari.json`'daki Cults3D slug'lari (dedup)."""
    slugs = set()
    if os.path.exists(KAYNAK):
        blob = open(KAYNAK, encoding="utf-8").read()
        for m in re.findall(r'cults3d\.com/(?:[a-z]{2}/)?3d-model/[^/"]+/([^/"\\]+)', blob):
            slugs.add(m.split("?")[0])
        for m in re.findall(r'cults3d[:/]([a-z0-9][a-z0-9-]{2,})', blob):
            slugs.add(m)
    return slugs


def main(term, maxn):
    mevcut = mevcut_slugler()
    bulunan, elenen_cop, elenen_nc, elenen_marka, elenen_ucretli = [], [], [], [], []
    seen = set()
    offset, total = 0, None
    LIMIT = 40
    while len(bulunan) < maxn and offset < 2000:
        try:
            res = c3.search(term, limit=LIMIT, offset=offset)
        except Exception as e:
            print("ARAMA HATA (offset %d):" % offset, e); break
        total = res.get("total") if total is None else total
        items = res.get("results") or []
        if not items:
            break
        for c in items:
            slug = c3.slug_of(c)
            if not slug or slug in seen:
                continue
            seen.add(slug)
            if slug in mevcut:
                continue
            name = (c.get("name") or "").replace("\n", " ")
            tags = c.get("tags") or []
            lic = c3.lisans_str(c)
            dl = c.get("downloadsCount") or 0
            likes = c.get("likesCount") or 0
            if not c3.satilabilir(lic):
                elenen_nc.append((slug, lic, name)); continue    # satilamaz -> populerlik DELMEZ
            if not c3.ucretsiz(c):
                elenen_ucretli.append((slug, lic, name)); continue  # ucretli pazar modeli -> atla
            if not marka_alakali(term, name, tags, slug):
                elenen_marka.append((slug, name)); continue
            pop = c3.populer(dl, likes)
            if c3.is_nobypass(name):
                elenen_cop.append((slug, name)); continue        # logo/amblem/merch -> hep ele
            if c3.is_cop(name) and not pop:
                elenen_cop.append((slug, name)); continue         # cop VE populer degil -> ele
            bulunan.append((slug, lic, name, dl, likes, c3.is_cop(name)))
            if len(bulunan) >= maxn:
                break
        offset += LIMIT
        if total and offset >= total:
            break

    bulunan.sort(key=lambda b: (b[4], b[3]), reverse=True)   # (likes, dl) azalan

    if elenen_nc:
        print("--- SATILAMAZ elenen %d (Cults tescilli/NC/bilinmeyen — populerlik DELMEZ) ---" % len(elenen_nc))
        for slug, lic, name in elenen_nc[:15]:
            print("  x %-28s %-30s %s" % (slug[:28], ("[" + str(lic)[:28] + "]"), name[:40]))
    if elenen_ucretli:
        print("--- UCRETLI elenen %d (Cults pazar modeli, price>0) ---" % len(elenen_ucretli))
        for slug, lic, name in elenen_ucretli[:10]:
            print("  x %-28s %s" % (slug[:28], name[:45]))
    if elenen_marka:
        print("--- MARKA-ALAKASIZ elenen %d (\\b%s\\b tam kelime degil) ---" % (len(elenen_marka), term))
        for slug, name in elenen_marka[:15]:
            print("  x %-28s %s" % (slug[:28], name[:45]))
    if elenen_cop:
        print("--- COP elenen %d (anahtarlik/logo/amblem/minyatur/kit-card; populer OLMAYAN) ---" % len(elenen_cop))
        for slug, name in elenen_cop[:15]:
            print("  x %-28s %s" % (slug[:28], name[:45]))
    pop_cop = sum(1 for b in bulunan if b[5])
    print("=== '%s' icin %d yeni aday (toplam eslesme %s, zaten ekli %d, satilamaz %d, ucretli %d, "
          "marka-alakasiz %d, cop %d elendi; populer-cop ISTISNA %d) ==="
          % (term, len(bulunan), total, len(mevcut & seen), len(elenen_nc), len(elenen_ucretli),
             len(elenen_marka), len(elenen_cop), pop_cop))
    for slug, lic, name, dl, likes, iscop in bulunan:
        yildiz = " ★POPULER-COP" if iscop else ""
        print("  %-30s %-16s ♥%-5d ⭳%-6d %s%s" % (slug[:30], str(lic)[:16], likes, dl, name[:40], yildiz))
    print("\nSLUGLAR (talep sirasi, populer basta):")
    print(" ".join(b[0] for b in bulunan))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Kullanim: python3 tools/cults3d-ara.py "<marka/terim>" [max]')
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 250)
