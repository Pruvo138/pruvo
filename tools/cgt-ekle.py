#!/usr/bin/env python3
"""PRUVO ******** SATICI toplu listeleme aracı.

Amac: bir satici profilinin TUM urunlerini siteye LISTELEMEK (satin almadan). Siparis gelince
ilgili model ********'dan satin alinip uretilir. Ucretli kaynak -> `lisans` YOK, atif YOK
(ticari mahremiyet). Maliyet (USD) + link gizli `.urun-kaynaklari.json`'a yazilir.

Kullanim:  python3 tools/cgt-ekle.py "https://www.********.com/3d-print-models?author=<satici>"

Her urun icin: JSON-LD (baslik + USD fiyat + kapak) + galeri gorselleri cekilir -> .thing-cache/
cgt-<id>/ + meta.json -> thing-gemini.py (gorsel secimi + Turkce icerik + kategori + marka) ->
secili gorseller R2'ye -> urun STAGE edilir. COMMIT ETMEZ (gozden gecirme).

FIYAT: TL = round(USD × 100)  ($8->800, $6.5->650, $2.5->250). ********'da aktif INDIRIM olabilir;
JSON-LD indirimli fiyati verebilir -> gozden gecirmede urun sayfasindaki INDIRIMSIZ fiyatla DOGRULA.

STL/olcu YOK (dosya henuz bizde degil). Nezaket icin istekler arasi kisa gecikme.
"""
import json, os, re, subprocess, sys, time, urllib.parse

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
IMGROOT = os.path.join(ROOT, ".thing-cache")
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
PY = sys.executable or "python3"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def fetch(url):
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "cgt_%d.html" % (abs(hash(url)) % 10**8))
    subprocess.run(["curl", "-sSL", "-A", UA, url, "-o", tmp], check=False)
    if not os.path.exists(tmp):
        return ""
    return open(tmp, encoding="utf-8", errors="ignore").read()


def profil_urunleri(profil_url):
    """Profildeki tum urun URL'lerini topla (sayfalama dahil)."""
    urls = []
    seen = set()
    for page in range(1, 12):   # emniyet: en fazla 11 sayfa
        sep = "&" if "?" in profil_url else "?"
        html = fetch(profil_url + "%spage=%d" % (sep, page))
        if not html:
            break
        found = re.findall(r'/3d-print-models/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+', html)
        yeni = [u for u in dict.fromkeys(found) if u not in seen]
        if not yeni:
            break
        for u in yeni:
            seen.add(u); urls.append("https://www.********.com" + u)
        time.sleep(1.5)
    return urls


def urun_verisi(url, author=None):
    html = fetch(url)
    if not html:
        return None
    if author and ("/designers/" + author) not in html:
        return {"_yanlis_yazar": True}   # oneri/baska satici -> atla
    m = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
    baslik = None; usd = None
    if m:
        try:
            d = json.loads(m.group(1).strip())
            baslik = (d.get("name") or "").split("|")[0].strip()
            off = d.get("offers") or {}
            off = off if isinstance(off, dict) else (off[0] if off else {})
            usd = off.get("price")
        except Exception:
            pass
    # galeri gorselleri: items/<id>/<hash>/...
    imgs = re.findall(r'https://img-new\.********\.com/items/(\d+)/[a-z0-9]+/[a-z0-9-]+\.(?:webp|jpg|png)', html)
    itemid = imgs[0] if imgs else None
    galeri = list(dict.fromkeys(re.findall(
        r'https://img-new\.********\.com/items/\d+/[a-z0-9]+/[a-z0-9-]+\.(?:webp|jpg|png)', html)))
    return {"itemid": itemid, "baslik": baslik, "usd": usd, "galeri": galeri, "link": url}


def indir_gorseller(itemid, galeri, n=6):
    import tempfile
    d = os.path.join(IMGROOT, "cgt-" + itemid); os.makedirs(d, exist_ok=True)
    saved = []
    for u in galeri:
        if len(saved) >= n:
            break
        raw = os.path.join(tempfile.gettempdir(), "cgtimg_%d" % (abs(hash(u)) % 10**8))
        subprocess.run(["curl", "-sSL", "-A", UA, u, "-o", raw], check=False)
        if not os.path.exists(raw) or os.path.getsize(raw) < 4000:
            continue
        jpg = os.path.join(d, "g%d.jpg" % (len(saved) + 1))
        subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1400", raw, "--out", jpg],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(jpg):
            saved.append(jpg)
    return d, saved


def sips_upload(local_jpg, key):
    import tempfile
    small = os.path.join(tempfile.gettempdir(), "up_" + os.path.basename(key))
    subprocess.run(["sips", "-Z", "1000", "-s", "formatOptions", "80", local_jpg, "--out", small],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run([PY, os.path.join(TOOLS, "r2-upload.py"), small, key],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.strip().startswith("https://"):
            return line.strip()
    return None


def tl_fiyat(usd):
    try:
        return "%d TL" % round(float(usd) * 100)
    except Exception:
        return ""


def stage_one(url, urunler, mevcut_ids, stage_src, author=None):
    v = urun_verisi(url, author)
    if v and v.get("_yanlis_yazar"):
        return {"url": url, "durum": "ATLA: baska satici/oneri"}
    if not v or not v.get("itemid") or not v.get("galeri"):
        return {"url": url, "durum": "HATA: veri/gorsel yok"}
    itemid = v["itemid"]
    key = "cgt-" + itemid
    d, imgs = indir_gorseller(itemid, v["galeri"])
    if not imgs:
        return {"url": url, "durum": "HATA: gorsel inmedi"}
    # meta.json (thing-gemini bunu okur) — lisans BOS, olcu YOK
    json.dump({"id": key, "baslik": v.get("baslik") or itemid, "tasarimci": "",
               "lisans": "", "olcu_mm": None, "stl_adet": 0,
               "gorseller": [os.path.basename(p) for p in imgs]},
              open(os.path.join(d, "meta.json"), "w"), ensure_ascii=False)
    # gemini onerisi
    subprocess.run([PY, os.path.join(TOOLS, "thing-gemini.py"), key],
                   capture_output=True, text=True)
    onerip = os.path.join(d, "oneri.json")
    if not os.path.exists(onerip):
        return {"url": url, "durum": "HATA: gemini oneri yok"}
    o = json.load(open(onerip))
    base = re.sub(r"[^a-z0-9]+", "-", (o.get("baslik") or itemid).lower()).strip("-")[:60] or itemid
    uid = base if base not in mevcut_ids else base + "-" + itemid
    secili = o.get("sec_gorseller") or sorted(os.path.basename(p) for p in imgs)
    urls = []
    for i, fn in enumerate(secili, 1):
        fp = os.path.join(d, fn)
        if os.path.exists(fp):
            uu = sips_upload(fp, "urunler/%s-%d.jpg" % (uid, i))
            if uu:
                urls.append(uu)
    if not urls:
        return {"url": url, "durum": "HATA: yuklenemedi"}
    urun = {"id": uid, "kategori": o.get("kategori", "Otomobil"), "marka": o.get("marka", []),
            "baslik": o.get("baslik", itemid), "aciklama": o.get("aciklama", ""),
            "fiyat": tl_fiyat(v.get("usd")), "gorseller": urls}   # lisans YOK
    stage_src.append((uid, {"kaynak": "********", "link": url, "tur": "satin-alma",
                            "usd": v.get("usd"), "itemid": itemid, "baski": "",
                            "not": "listeleme; siparis gelince satin al+uret"}))
    mevcut_ids.add(uid)
    return {"url": url, "durum": "STAGED", "uid": uid, "usd": v.get("usd"),
            "fiyat": urun["fiyat"], "kategori": urun["kategori"], "marka": urun["marka"],
            "gorsel": len(urls), "baslik": urun["baslik"], "_urun": urun}


def main(profil_url):
    urunler = json.load(open(URUNLER))
    kaynak = json.load(open(KAYNAK))
    mevcut_ids = {p["id"] for p in urunler}
    am = re.search(r'author=([a-zA-Z0-9_-]+)', profil_url)
    author = am.group(1) if am else None
    print("Profil taraniyor:", profil_url, "(satici:", author, ")", flush=True)
    urls = profil_urunleri(profil_url)
    print("Bulunan urun:", len(urls), flush=True)
    stage_src = []; sonuc = []
    for i, u in enumerate(urls, 1):
        print("### (%d/%d)" % (i, len(urls)), u, flush=True)
        sonuc.append(stage_one(u, urunler, mevcut_ids, stage_src, author))
        time.sleep(1.2)
    yeni = [s["_urun"] for s in sonuc if s.get("durum") == "STAGED"]
    for un in reversed(yeni):
        urunler.insert(0, un)
    json.dump(urunler, open(URUNLER, "w"), ensure_ascii=False, indent=2)
    for uid, rec in stage_src:
        kaynak[uid] = rec
    json.dump(kaynak, open(KAYNAK, "w"), ensure_ascii=False, indent=1)
    print("\n" + "=" * 74)
    print("STAGED (commit ETMEDIM — fiyatlari INDIRIMSIZ ******** fiyatiyla dogrula):")
    for s in sonuc:
        if s.get("durum") == "STAGED":
            print("  ✔ %-40s | %-10s | usd:%s -> %s | g:%d | %s"
                  % (s["uid"], s["kategori"], s["usd"], s["fiyat"], s["gorsel"], s["marka"]))
        else:
            print("  ✘", s["url"], "->", s["durum"])
    print("-" * 74)
    print("%d urun STAGE edildi, urunler.json toplam %d." % (len(yeni), len(urunler)))
    print("SONRAKI: fiyatlari dogrula/duzelt -> yedekle + commit + push (lisans alani YOK, isimsiz commit).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Kullanim: python3 tools/cgt-ekle.py "<******** profil url>"')
    main(sys.argv[1])
