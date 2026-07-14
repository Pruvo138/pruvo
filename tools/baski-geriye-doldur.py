#!/usr/bin/env python3
"""GERIYE DONUK baski/filament onerisi doldurma — TUM urunler icin tek seferlik.

`.urun-kaynaklari.json`'da `baski` alani BOS olan her kaydin kaynak (Printables/Thingiverse)
aciklamasini cekip `tools/baski_ipucu.py` ile filament/baski onerisini cikarir, alana yazar.

RESUMABLE + IDEMPOTENT: sadece baski == "" olanlar islenir. Oneri bulunursa yazilir; bulunamazsa
"-" yazilir (hem "tarandi" isareti hem mevcut convention). Boylece tekrar calistirinca kaldigi
yerden devam eder, dolu/gercek onerilere ASLA dokunmaz.

Kaynaklar: Printables (token'siz GraphQL), Thingiverse (.thingiverse-token). CGTrader/bilinmeyen
kaynak: aciklama kolay cekilemez -> "-" ile isaretlenip gecilir (elle bakilir).

Kullanim:
    python3 tools/baski-geriye-doldur.py           # hepsi
    python3 tools/baski-geriye-doldur.py 10         # ilk 10 aday (TEST)
"""
import concurrent.futures, fcntl, importlib.util, json, os, re, sys, time, urllib.request

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
WORKERS = int(os.environ.get("PRUVO_WORKERS", "4"))

_TOKENP = os.path.join(ROOT, ".thingiverse-token")
TVTOKEN = open(_TOKENP).read().strip() if os.path.exists(_TOKENP) else None


def _load(p, n):
    s = importlib.util.spec_from_file_location(n, os.path.join(TOOLS, p))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pr = _load("printables-api.py", "pr_api")
bi = _load("baski_ipucu.py", "baski_ipucu")


def tv_description(tid):
    req = urllib.request.Request("https://api.thingiverse.com/things/%s" % tid,
                                 headers={"Authorization": "Bearer " + TVTOKEN, "User-Agent": "pruvo/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read()).get("description") or ""


def aciklama(link):
    """Kaynak linkinden aciklama metni. (metin, kaynak_turu) doner; cekemezse (None, tur)."""
    m = re.search(r"printables\.com/model/(\d+)", link or "")
    if m:
        try:
            return pr.detail(m.group(1)).get("description") or "", "printables"
        except Exception:
            return None, "printables"
    m = re.search(r"thingiverse\.com/thing:(\d+)", link or "")
    if m and TVTOKEN:
        try:
            return tv_description(m.group(1)), "thingiverse"
        except Exception:
            return None, "thingiverse"
    return None, "diger"   # cgtrader / bilinmeyen


def bir(uid_link):
    uid, link = uid_link
    for attempt in range(3):
        desc, tur = aciklama(link)
        if desc is None and tur in ("printables", "thingiverse") and attempt < 2:
            time.sleep(3 * (attempt + 1)); continue   # gecici hata/rate-limit -> tekrar dene
        break
    if desc is None:
        return uid, "-", tur, False          # cekilemedi -> isaretle, gec
    hint = bi.baski_ipucu(desc)
    return uid, (hint or "-"), tur, bool(hint)


def merge(updates):
    lockf = open(LOCK, "w"); fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        k = json.load(open(KAYNAK))
        for uid, val in updates.items():
            if uid in k and isinstance(k[uid], dict) and not k[uid].get("baski"):
                k[uid]["baski"] = val     # yalnizca hala BOS ise yaz (baska oturum doldurmus olabilir)
        json.dump(k, open(KAYNAK, "w"), ensure_ascii=False, indent=1)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()


def main(limit=None):
    k = json.load(open(KAYNAK))
    adaylar = [(uid, r.get("link", "")) for uid, r in k.items()
               if isinstance(r, dict) and not r.get("baski")]
    if limit:
        adaylar = adaylar[:limit]
    print("Aday (baski BOS):", len(adaylar), "| worker:", WORKERS, flush=True)
    updates = {}; bulundu = 0; taranan = 0; hata = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(bir, a): a[0] for a in adaylar}
        for f in concurrent.futures.as_completed(futs):
            uid, val, tur, ok = f.result()
            updates[uid] = val; taranan += 1
            if ok:
                bulundu += 1
            elif val == "-" and tur != "diger":
                pass
            if taranan % 50 == 0:
                print("  ...%d/%d tarandi, %d oneri bulundu" % (taranan, len(adaylar), bulundu), flush=True)
                merge(updates); updates = {}      # ara kayit (cokerse ilerleme kaybolmaz)
    if updates:
        merge(updates)
    print("=" * 60)
    print("BITTI: %d aday tarandi, %d urune baski onerisi eklendi, kalani '-' isaretlendi." % (taranan, bulundu))
    print("SONRAKI: python3 tools/yedekle.py --sirlar  (Drive yedegi)")


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(lim)
