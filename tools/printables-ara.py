#!/usr/bin/env python3
"""Printables'te MARKA/terim arar, sitede OLMAYAN + satilabilir + gurultusuz model ID'lerini verir.
Thingiverse'teki thing-ara.py'nin esdegeri.

Kullanim:  python3 tools/printables-ara.py "Renault" [max]
   -> aday model ID'lerini bir satirda (bosluk ayirli) yazar + id/lisans/baslik listesi basar.

ELER:  * CC-...-NC (satilamaz) lisanslar        (satilabilir() kurali)
       * anahtarlik/logo/amblem/minyatur gurultusu (COP listesi)
       * `.urun-kaynaklari.json`'da zaten kayitli printables model ID'leri

Token GEREKMEZ (Printables public GraphQL). Sir icermez.
"""
import importlib.util, os, re, sys

ROOT = "/Users/okan/dev/pruvo"
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")

_spec = importlib.util.spec_from_file_location("pr_api", os.path.join(ROOT, "tools", "printables-api.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


def mevcut_idler():
    ids = set()
    if os.path.exists(KAYNAK):
        blob = open(KAYNAK, encoding="utf-8").read()
        for m in re.findall(r'printables\.com/model/(\d+)', blob):
            ids.add(m)
        for m in re.findall(r'printables[:/](\d{3,})', blob):
            ids.add(m)
    return ids


def main(term, maxn):
    mevcut = mevcut_idler()
    bulunan, elenen_cop, elenen_nc = [], [], []
    seen = set()
    offset = 0
    total = None
    while len(bulunan) < maxn and offset < 3000:
        try:
            res = pr.search(term, limit=30, offset=offset, ordering="popular")
        except Exception as e:
            print("ARAMA HATA (offset %d):" % offset, e); break
        total = res["totalCount"] if total is None else total
        items = res["items"]
        if not items:
            break
        for h in items:
            pid = str(h["id"])
            if pid in seen:
                continue
            seen.add(pid)
            if pid in mevcut:
                continue
            name = (h.get("name") or "").replace("\n", " ")
            abbr = ((h.get("license") or {}).get("abbreviation")) or ""
            dl = h.get("downloadCount") or 0
            likes = h.get("likesCount") or 0
            if not pr.satilabilir(abbr):
                elenen_nc.append((pid, abbr, name)); continue    # NC = yasal, POPULERLIK DELMEZ
            pop = pr.populer(dl, likes)
            if pr.is_nobypass(name):
                elenen_cop.append((pid, name)); continue         # logo/amblem VEYA marka-merch -> populerlik DELMEZ, hep ele
            if pr.is_cop(name) and not pop:
                elenen_cop.append((pid, name)); continue         # cop VE populer degil -> ele
            bulunan.append((pid, abbr, name, dl, likes, pr.is_cop(name)))  # son alan: populer-cop mu
            if len(bulunan) >= maxn:
                break
        offset += 30
        if offset >= (total or 0):
            break

    # EN YUKSEK ONCELIK: talep (begeni + indirme) cok olan urun basa. Populer-cop olanlar da burada.
    bulunan.sort(key=lambda b: (b[4], b[3]), reverse=True)   # (likes, dl) azalan

    if elenen_nc:
        print("--- SATILAMAZ (NC) elenen %d (populerlik DELMEZ — yasal) ---" % len(elenen_nc))
        for pid, abbr, name in elenen_nc[:15]:
            print("  x %s  %-12s %s" % (pid, abbr, name[:55]))
    if elenen_cop:
        print("--- COP elenen %d (anahtarlik/logo/amblem/minyatur; populer OLMAYAN) ---" % len(elenen_cop))
        for pid, name in elenen_cop[:15]:
            print("  x %s  %s" % (pid, name[:60]))
    pop_cop = sum(1 for b in bulunan if b[5])
    print("=== '%s' icin %d yeni aday (toplam eslesme %s, zaten ekli %d, NC %d, cop %d elendi; "
          "populer-cop ISTISNA %d) ==="
          % (term, len(bulunan), total, len(mevcut & seen), len(elenen_nc), len(elenen_cop), pop_cop))
    for pid, abbr, name, dl, likes, iscop in bulunan:
        yildiz = " ★POPULER-COP" if iscop else ""
        print("  %s  %-12s ♥%-5d ⭳%-6d %s%s" % (pid, abbr, likes, dl, name[:52], yildiz))
    print("\nIDLER (talep sirasi, populer basta):")
    print(" ".join(b[0] for b in bulunan))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Kullanim: python3 tools/printables-ara.py "<marka/terim>" [max]')
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 250)
