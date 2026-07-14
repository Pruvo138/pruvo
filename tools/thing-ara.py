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
# LOGO: marka logosu/amblemi tasiyan urunler — telif/marka hakki riski nedeniyle POPULERLIK
# BILE DELMEZ, her zaman elenir (Okan, 2026-07-14).
COP_LOGO = ("logo", "emblem", "badge", "nameplate", "name plate", "symbol", "monogram")
COP_OTHER = ("keychain", "keyring", "key ring", "keyfob", "key fob", "keytag", "key tag",
             "keyholder", "key holder", "keychains",
             "letters", "lettering", "sticker", "wall art", "trophy",
             "coaster", "fridge magnet", "magnet",
             "miniature", "diecast", "die-cast", "diorama", "scale model", "1:18", "1:24", "1:32",
             "1:43", "1:64", "1/18", "1/24", "1/43", "keycap")
COP = COP_LOGO + COP_OTHER


def is_cop(name):
    n = " " + name.lower() + " "
    return any(c in n for c in COP)


def is_logo(name):
    n = " " + name.lower() + " "
    return any(c in n for c in COP_LOGO)


# POPULERLIK: cok talep goren thing (asagidaki esigi asan) COP/yasakli olsa bile ALINIR ve
# aramada EN UST onceligi alir. (Thingiverse aramasinda indirme yok -> begeni/make/collect.)
POP_LIKE = 300
POP_MAKE = 25
POP_COLLECT = 300


def populer(h):
    return ((h.get("like_count") or 0) >= POP_LIKE or (h.get("make_count") or 0) >= POP_MAKE
            or (h.get("collect_count") or 0) >= POP_COLLECT)


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
    page = 0
    while len(bulunan) < maxn and page < 400:
        page += 1
        # license=cc -> satilabilir CC havuzu (NC'yi urun-ekle kapisi ayrica eler)
        url = ("https://api.thingiverse.com/search/%s?type=things&license=cc&per_page=30&page=%d"
               % (urllib.parse.quote(term), page))
        try:
            d = api(url)
        except Exception as e:
            print("ARAMA HATA (sayfa %d):" % page, e); break
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
            likes = h.get("like_count") or 0
            makes = h.get("make_count") or 0
            pop = populer(h)
            if is_logo(name):
                elenen.append((tid, name)); continue         # logo -> populerlik DELMEZ, hep ele
            if is_cop(name) and not pop:
                elenen.append((tid, name)); continue        # cop VE populer degil -> ele
            bulunan.append((tid, name, likes, makes, is_cop(name)))  # son alan: populer-cop mu
            if len(bulunan) >= maxn:
                break
        if len(bulunan) >= maxn:
            break
    # EN YUKSEK ONCELIK: talep (begeni, sonra make) cok olan thing basa. Populer-cop da burada.
    bulunan.sort(key=lambda b: (b[2], b[3]), reverse=True)
    if elenen:
        print("--- COP elenen %d (anahtarlik/logo/amblem/minyatur; populer OLMAYAN) ---" % len(elenen))
        for tid, name in elenen[:20]:
            print("  x %s  %s" % (tid, name[:60]))
    pop_cop = sum(1 for b in bulunan if b[4])
    print("=== '%s' icin %d yeni aday (zaten ekli %d, cop %d elendi; populer-cop ISTISNA %d) ==="
          % (term, len(bulunan), len(mevcut & seen), len(elenen), pop_cop))
    for tid, name, likes, makes, iscop in bulunan:
        yildiz = " ★POPULER-COP" if iscop else ""
        print("  %s  ♥%-5d ⚒%-4d %s%s" % (tid, likes, makes, name[:52], yildiz))
    print("\nIDLER (talep sirasi, populer basta):")
    print(" ".join(b[0] for b in bulunan))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Kullanim: python3 tools/thing-ara.py "<marka/terim>" [max]')
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 250)
