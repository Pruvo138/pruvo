#!/usr/bin/env python3
"""MakerWorld'te MARKA/terim arar; sitede OLMAYAN + satilabilir + gurultusuz + MARKA-ALAKALI
model ID'lerini verir. Printables'teki printables-ara.py'nin MakerWorld esdegeri.

Kullanim:  python3 tools/makerworld-ara.py "Renault" [max]
   -> aday model ID'lerini bir satirda (bosluk ayirli) yazar + id/lisans/baslik listesi basar.

ELER:  * satilamaz lisans (satilabilir() FAIL-CLOSED — Standard/Exclusive/NC/bilinmeyen)
       * anahtarlik/logo/amblem/minyatur/kit-card gurultusu (COP listesi)
       * \\bMARKA\\b KELIME-SINIRI: marka adi baslik/etiket/slug'da TAM KELIME olarak gecmiyorsa
         ele (Oxford/afford gibi alt-dize gurultusu elensin; Turkce-duyarli). Mimar bu inline
         filtreyi ORTAK filtreyle sonra birlestirecek (bkz. paket).
       * `.urun-kaynaklari.json`'da zaten kayitli MakerWorld model ID'leri (dedup)

Token GEREKMEZ (MakerWorld public API). Sir icermez.
"""
import importlib.util, os, re, sys

ROOT = "/Users/okan/dev/pruvo"
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("makerworld_api", os.path.join(_HERE, "makerworld-api.py"))
mw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mw)


# --- \bMARKA\b kelime-siniri (Turkce-duyarli) ---
_KELIME = "a-z0-9çğıöşü"


def _tr_lower(s):
    # Turkce'ye ozgu: 'İ'->'i', 'I'->'ı' (dogru kucultme), sonra lower().
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


def marka_geciyor(marka, *metinler):
    """marka, verilen metinlerden en az birinde TAM KELIME olarak geciyor mu?
    'ford' -> 'Ford Mustang' EVET; 'Oxford'/'afford' HAYIR (alt-dize)."""
    m = _tr_lower(marka).strip()
    if not m:
        return False
    pat = re.compile(r"(?<![%s])%s(?![%s])" % (_KELIME, re.escape(m), _KELIME))
    return any(pat.search(_tr_lower(t or "")) for t in metinler)


def mevcut_idler():
    ids = set()
    if os.path.exists(KAYNAK):
        blob = open(KAYNAK, encoding="utf-8").read()
        for m in re.findall(r'makerworld\.com/(?:[a-z]{2}/)?models/(\d+)', blob):
            ids.add(m)
        for m in re.findall(r'makerworld[:/](\d{3,})', blob):
            ids.add(m)
    return ids


def main(term, maxn, derin=False, cikis_limiti=None):
    """term/marka ara, sitede OLMAYAN uygun aday model ID'lerini bas.

    Sayfalama (pagination) ile keeper-cap AYRI (2026-07-18 duzeltme; thing-ara.py deseni):
      - derin=False (varsayilan, GERIYE-UYUMLU): dongu `maxn` keeper toplayinca DURUR (eski davranis).
      - derin=True (--derin): `maxn` dongoyu DURDURMAZ; ham havuz IKINCIL tavana (offset<3000) ya da
        `total` tukenene kadar TAM taranir. Boylece uygun havuz erken kesilmez.
    `cikis_limiti` (opsiyonel): siralamadan sonra cikti listesini kirpar (None=kirpma yok)."""
    mevcut = mevcut_idler()
    bulunan, elenen_cop, elenen_nc, elenen_marka = [], [], [], []
    seen = set()
    offset, total = 0, None
    LIMIT = 40
    # DONGU KOSULU: derin modda maxn'e bakma (havuzu ikincil tavana kadar tam gez); degilse eski cap.
    while offset < 3000 and (derin or len(bulunan) < maxn):
        try:
            res = mw.search(term, limit=LIMIT, offset=offset)
        except Exception as e:
            print("ARAMA HATA (offset %d):" % offset, e); break
        total = res.get("total") if total is None else total
        items = res.get("hits") or []
        if not items:
            break
        for h in items:
            pid = str(h.get("id"))
            if pid in seen:
                continue
            seen.add(pid)
            if pid in mevcut:
                continue
            name = (h.get("title") or "").replace("\n", " ")
            slug = h.get("slug") or ""
            tags = " ".join(h.get("tags") or [])
            lic = h.get("license") or ""
            dl = h.get("downloadCount") or 0
            likes = h.get("likeCount") or 0
            if not mw.satilabilir(lic):
                elenen_nc.append((pid, lic, name)); continue     # satilamaz -> populerlik DELMEZ
            # \bMARKA\b tam-kelime alaka testi (baslik + etiket + slug)
            if not marka_geciyor(term, name, tags, slug.replace("-", " ")):
                elenen_marka.append((pid, name)); continue
            pop = mw.populer(dl, likes)
            if mw.is_nobypass(name):
                elenen_cop.append((pid, name)); continue         # logo/amblem/merch -> hep ele
            if mw.is_cop(name) and not pop:
                elenen_cop.append((pid, name)); continue         # cop VE populer degil -> ele
            bulunan.append((pid, lic, name, dl, likes, mw.is_cop(name)))
            # keeper-cap SADECE derin-olmayan (eski) modda dongoyu keser
            if not derin and len(bulunan) >= maxn:
                break
        offset += LIMIT
        if total and offset >= total:
            break

    bulunan.sort(key=lambda b: (b[4], b[3]), reverse=True)   # (likes, dl) azalan
    havuz_toplam = len(bulunan)   # kirpmadan ONCE toplanan gercek aday sayisi (kabul olcumu)
    if cikis_limiti is not None:
        bulunan = bulunan[:cikis_limiti]

    if elenen_nc:
        print("--- SATILAMAZ elenen %d (Standard/Exclusive/NC/bilinmeyen — populerlik DELMEZ) ---" % len(elenen_nc))
        for pid, lic, name in elenen_nc[:15]:
            print("  x %-9s %-32s %s" % (pid, ("[" + str(lic)[:30] + "]"), name[:48]))
    if elenen_marka:
        print("--- MARKA-ALAKASIZ elenen %d (\\b%s\\b tam kelime degil) ---" % (len(elenen_marka), term))
        for pid, name in elenen_marka[:15]:
            print("  x %-9s %s" % (pid, name[:60]))
    if elenen_cop:
        print("--- COP elenen %d (anahtarlik/logo/amblem/minyatur/kit-card; populer OLMAYAN) ---" % len(elenen_cop))
        for pid, name in elenen_cop[:15]:
            print("  x %-9s %s" % (pid, name[:60]))
    pop_cop = sum(1 for b in bulunan if b[5])
    kirpma = "" if cikis_limiti is None else " (cikis %d'e kirpildi; havuz %d)" % (len(bulunan), havuz_toplam)
    print("=== '%s' icin %d yeni aday (toplam eslesme %s, zaten ekli %d, satilamaz %d, "
          "marka-alakasiz %d, cop %d elendi; populer-cop ISTISNA %d)%s ==="
          % (term, len(bulunan), total, len(mevcut & seen), len(elenen_nc),
             len(elenen_marka), len(elenen_cop), pop_cop, kirpma))
    for pid, lic, name, dl, likes, iscop in bulunan:
        yildiz = " ★POPULER-COP" if iscop else ""
        print("  %-9s %-14s ♥%-5d ⭳%-6d %s%s" % (pid, str(lic)[:14], likes, dl, name[:50], yildiz))
    print("\nIDLER (talep sirasi, populer basta):")
    print(" ".join(b[0] for b in bulunan))


if __name__ == "__main__":
    # Geriye uyumlu: eski cagri `makerworld-ara.py "<terim>" [max]` aynen calisir (derin=False).
    #  --derin : keeper-cap'i KALDIR, ham havuzu (offset<3000 tavanina/total'a kadar) TAM tara.
    #            derin modda pozisyonel sayi = OPSIYONEL cikis-trim (verilmezse tum havuz).
    args = sys.argv[1:]
    derin = "--derin" in args
    pos = [a for a in args if a != "--derin"]
    if not pos:
        sys.exit('Kullanim: python3 tools/makerworld-ara.py "<marka/terim>" [max] [--derin]')
    if derin:
        cikis = int(pos[1]) if len(pos) > 1 else None
        main(pos[0], maxn=10 ** 9, derin=True, cikis_limiti=cikis)
    else:
        main(pos[0], int(pos[1]) if len(pos) > 1 else 250)
