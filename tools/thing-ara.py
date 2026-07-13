#!/usr/bin/env python3
"""Thingiverse'te MARKA/terim arar, zaten sitede OLMAYAN thing ID'lerini verir.

Kullanim:  python3 tools/thing-ara.py "Hyundai" [max]
   -> aday thing ID'lerini bir satirda (bosluk ayirli) yazar -> orkestratore (urun-ekle.py) girer.
      Ayrica id + baslik listesi basar (gozden gecirme). Lisans/uygunluk kontrolu urun-ekle.py'de.

Zaten eklenmis olanlari `.urun-kaynaklari.json` icindeki thing linklerinden tespit edip ELER.
Token `.thingiverse-token`'dan okunur. Sir icermez.
"""
import json, os, re, sys, urllib.parse, urllib.request

ROOT = "/Users/okan/dev/pruvo"
TOKEN = open(os.path.join(ROOT, ".thingiverse-token")).read().strip()
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")


# Yedek parca sitesine UYMAYAN gurultu (marka aramasi bunlari bol getirir) -> otomatik ELE.
COP = ("keychain", "keyring", "key ring", "keyfob", "key fob", "keytag", "key tag", "keyholder",
       "key holder", "keychains", "logo", "emblem", "badge", "nameplate", "name plate",
       "letters", "lettering", "symbol", "monogram", "sticker", "wall art", "trophy",
       "coaster", "fridge magnet", "magnet",
       "miniature", "diecast", "die-cast", "diorama", "scale model", "1:18", "1:24", "1:32",
       "1:43", "1:64", "1/18", "1/24", "1/43", "keycap")


def is_cop(name):
    n = " " + name.lower() + " "
    return any(c in n for c in COP)


def api(url):
    r = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN,
                                             "User-Agent": "pruvo/1.0"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())


def mevcut_thing_idleri():
    ids = set()
    if os.path.exists(KAYNAK):
        blob = open(KAYNAK, encoding="utf-8").read()
        for m in re.findall(r'thing[:/](\d{4,})', blob):
            ids.add(m)
        for m in re.findall(r'thingiverse\.com/thing:(\d+)', blob):
            ids.add(m)
    return ids


def main(term, maxn):
    mevcut = mevcut_thing_idleri()
    bulunan = []
    elenen = []
    seen = set()
    for page in range(1, 15):
        url = ("https://api.thingiverse.com/search/%s?type=things&per_page=30&page=%d"
               % (urllib.parse.quote(term), page))
        try:
            d = api(url)
        except Exception as e:
            print("ARAMA HATA:", e); break
        hits = d.get("hits") if isinstance(d, dict) else d
        if not hits:
            break
        for h in hits:
            tid = str(h.get("id"))
            if tid in seen:
                continue
            seen.add(tid)
            if tid in mevcut:
                continue
            name = (h.get("name") or "").replace("\n", " ")
            if is_cop(name):
                elenen.append((tid, name)); continue
            bulunan.append((tid, name))
            if len(bulunan) >= maxn:
                break
        if len(bulunan) >= maxn:
            break
    if elenen:
        print("--- COP olarak elenen %d (anahtarlik/logo/amblem/minyatur) ---" % len(elenen))
        for tid, name in elenen[:20]:
            print("  x %s  %s" % (tid, name[:60]))
    print("=== '%s' icin %d yeni aday (zaten ekli %d, cop %d elendi) ==="
          % (term, len(bulunan), len(mevcut & seen), len(elenen)))
    for tid, name in bulunan:
        print("  %s  %s" % (tid, name[:70]))
    print("\nIDLER (urun-ekle.py'ye ver):")
    print(" ".join(tid for tid, _ in bulunan))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Kullanim: python3 tools/thing-ara.py "<marka/terim>" [max]')
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 250)
