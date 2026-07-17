#!/usr/bin/env python3
"""PRUVO ******** SATICI toplu listeleme araci (PARALEL + concurrency-safe).

Amac: bir satici profilinin TUM urunlerini siteye LISTELEMEK (satin almadan). Siparis gelince
model ********'dan alinip uretilir. Ucretli kaynak -> `lisans` YOK, atif YOK (ticari mahremiyet).
Maliyet (USD) + link gizli `.urun-kaynaklari.json`'a yazilir.

Kullanim:  python3 tools/cgt-ekle.py "https://www.********.com/3d-print-models?author=<satici>"

Her urun PARALEL islenir (fetch + Gemini + upload). Yazma: dosya KILIDI altinda urunler.json'u
O AN yeniden okuyup ekler (stale snapshot degil) -> baska oturum ayni anda yazsa bile EZMEZ.
COMMIT ETMEZ. Sonda gozden gecirme tablosu basar.

FIYAT: TL = round(USD × 100). Aktif indirim JSON-LD'yi sasirtabilir -> INDIRIMSIZ fiyatla dogrula.
STL/olcu YOK (dosya henuz bizde degil).
"""
import collections, concurrent.futures, fcntl, json, os, re, subprocess, sys, tempfile, time

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
IMGROOT = os.path.join(ROOT, ".thing-cache")
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
PY = sys.executable or "python3"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
WORKERS = int(os.environ.get("PRUVO_WORKERS", "6"))


def fetch(url):
    tmp = os.path.join(tempfile.gettempdir(), "cgt_%d.html" % (abs(hash(url)) % 10**8))
    subprocess.run(["curl", "-sSL", "-A", UA, url, "-o", tmp], check=False)
    return open(tmp, encoding="utf-8", errors="ignore").read() if os.path.exists(tmp) else ""


def profil_urunleri(profil_url):
    urls, seen = [], set()
    for page in range(1, 12):
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
        time.sleep(1.0)
    return urls


def urun_verisi(url, author=None):
    html = fetch(url)
    if not html:
        return None
    if author and ("/designers/" + author).lower() not in html.lower():   # slug kucuk harf olabilir
        return {"_yanlis_yazar": True}
    m = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
    baslik = usd = None
    if m:
        try:
            d = json.loads(m.group(1).strip())
            baslik = (d.get("name") or "").split("|")[0].strip()
            off = d.get("offers") or {}
            off = off if isinstance(off, dict) else (off[0] if off else {})
            usd = off.get("price")           # LISTE (indirimsiz) fiyati
        except Exception:
            pass
    # site geneli indirim yuzdesi (or. -50%); en sik goruleni al
    pcts = re.findall(r'-(\d{1,2})%', html)
    disc = int(collections.Counter(pcts).most_common(1)[0][0]) if pcts else 0
    imgs = re.findall(r'https://img-new\.********\.com/items/(\d+)/[a-z0-9]+/[a-z0-9-]+\.(?:webp|jpg|png)', html)
    galeri = list(dict.fromkeys(re.findall(
        r'https://img-new\.********\.com/items/\d+/[a-z0-9]+/[a-z0-9-]+\.(?:webp|jpg|png)', html)))
    return {"itemid": imgs[0] if imgs else None, "baslik": baslik, "usd": usd, "disc": disc,
            "galeri": galeri, "link": url}


def indir_gorseller(itemid, galeri, n=6):
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
    small = os.path.join(tempfile.gettempdir(), "up_" + os.path.basename(key))
    subprocess.run(["sips", "-Z", "1000", "-s", "formatOptions", "80", local_jpg, "--out", small],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run([PY, os.path.join(TOOLS, "r2-upload.py"), small, key],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.strip().startswith("https://"):
            return line.strip()
    return None


def tl_fiyat(usd, disc=0, mode="list"):
    """list = indirimsiz liste × 100 (rhymiespb). final = indirimli × 100 (liste × (1-%)) (3D-Wizzard)."""
    try:
        p = float(usd)
        if mode == "final" and disc:
            p = p * (1 - disc / 100.0)
        return "%d TL" % round(p * 100)
    except Exception:
        return ""


def process_one(url, author, mode="list"):
    """PARALEL calisir; urunler.json'a DOKUNMAZ. Sadece fetch+codex+upload yapip sonuc doner."""
    try:
        v = urun_verisi(url, author)
        if v and v.get("_yanlis_yazar"):
            return {"url": url, "durum": "ATLA: baska satici/oneri"}
        if not v or not v.get("itemid") or not v.get("galeri"):
            return {"url": url, "durum": "HATA: veri/gorsel yok"}
        itemid = v["itemid"]; key = "cgt-" + itemid
        d, imgs = indir_gorseller(itemid, v["galeri"])
        if not imgs:
            return {"url": url, "durum": "HATA: gorsel inmedi"}
        json.dump({"id": key, "baslik": v.get("baslik") or itemid, "tasarimci": "", "lisans": "",
                   "olcu_mm": None, "stl_adet": 0, "gorseller": [os.path.basename(p) for p in imgs]},
                  open(os.path.join(d, "meta.json"), "w"), ensure_ascii=False)
        subprocess.run([PY, os.path.join(TOOLS, "thing-codex.py"), key], capture_output=True, text=True)
        onerip = os.path.join(d, "oneri.json")
        if not os.path.exists(onerip):
            return {"url": url, "durum": "HATA: codex oneri yok"}
        o = json.load(open(onerip))
        uid = re.sub(r"[^a-z0-9]+", "-", (o.get("baslik") or itemid).lower()).strip("-")[:60] or itemid
        # R2 gorsel anahtari KAYNAK-ID'den (cgt-<itemid>) turer, baslik-slug'indan (uid) DEGIL: iki
        # farkli urun ayni basligi uretse bile anahtarlari cakismaz (bkz tools/gorsel-anahtar-test.py).
        # merge_safe eski yorumu "gorsel URL'leri etkilenmez" der; iste bu yuzden id -itemid ile
        # ayrilirken gorseller ESKI uid anahtarinda kalip EZILIYORDU. uid, JSON id + SEO URL icin kalir.
        gkey = re.sub(r"[^a-z0-9-]+", "-", key.lower()).strip("-") or key
        secili = o.get("sec_gorseller") or sorted(os.path.basename(p) for p in imgs)
        urls = []
        for i, fn in enumerate(secili, 1):
            fp = os.path.join(d, fn)
            if os.path.exists(fp):
                uu = sips_upload(fp, "urunler/%s-%d.jpg" % (gkey, i))
                if uu:
                    urls.append(uu)
        if not urls:
            return {"url": url, "durum": "HATA: yuklenemedi"}
        urun = {"id": uid, "kategori": o.get("kategori", "Otomobil"), "marka": o.get("marka", []),
                "baslik": o.get("baslik", itemid), "aciklama": o.get("aciklama", ""),
                "fiyat": tl_fiyat(v.get("usd"), v.get("disc", 0), mode), "gorseller": urls}   # lisans YOK
        src = {"kaynak": "********", "link": url, "tur": "satin-alma", "usd_liste": v.get("usd"),
               "indirim_pct": v.get("disc", 0), "fiyat_modu": mode, "itemid": itemid, "baski": "",
               "not": "listeleme; sipariste satin al+uret"}
        return {"url": url, "durum": "STAGED", "urun": urun, "src": src, "itemid": itemid,
                "usd": v.get("usd"), "disc": v.get("disc", 0), "fiyat": urun["fiyat"],
                "kategori": urun["kategori"], "marka": urun["marka"], "gorsel": len(urls),
                "baslik": urun["baslik"]}
    except Exception as e:
        return {"url": url, "durum": "HATA: %s" % str(e)[:120]}


def _atomic_write(path, obj, **kw):
    """json.dump'i once gecici dosyaya yazip os.replace ile devreye alir; yaziyi yarida
    kesen bir crash/kill orijinal dosyayi asla yarim/bozuk birakmaz."""
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, **kw)
    os.replace(tmp, path)


def merge_safe(staged):
    """Dosya KILIDI altinda urunler.json'u O AN okuyup ekler (stale snapshot degil)."""
    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        urunler = json.load(open(URUNLER))
        kaynak = json.load(open(KAYNAK))
        mevcut = {p["id"] for p in urunler}
        yeni = []
        for s in staged:
            urun = s["urun"]; uid = urun["id"]
            if uid in mevcut:                      # o an cakisiyorsa itemid ekle (gorsel URL'leri etkilenmez)
                uid = uid + "-" + s["itemid"]; urun["id"] = uid
            mevcut.add(uid); yeni.append(urun)
            kaynak[uid] = s["src"]
        for u in reversed(yeni):
            urunler.insert(0, u)
        _atomic_write(URUNLER, urunler, ensure_ascii=False, indent=2)
        _atomic_write(KAYNAK, kaynak, ensure_ascii=False, indent=1)
        return len(yeni), len(urunler)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()


def main(profil_url, mode="list"):
    am = re.search(r'author=([a-zA-Z0-9_-]+)', profil_url)
    author = am.group(1) if am else None
    print("Profil:", profil_url, "| satici:", author, "| FIYAT MODU:", mode,
          "(list=indirimsiz×100, final=indirimli×100)", flush=True)
    urls = profil_urunleri(profil_url)
    print("Bulunan urun:", len(urls), "| paralel worker:", WORKERS, flush=True)
    sonuc = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(process_one, u, author, mode): u for u in urls}
        done = 0
        for f in concurrent.futures.as_completed(futs):
            r = f.result(); sonuc.append(r); done += 1
            print("  (%d/%d) %s %s" % (done, len(urls), r.get("durum"), r.get("uid", r.get("baslik", ""))[:40] if r.get("durum") == "STAGED" else ""), flush=True)
    staged = [s for s in sonuc if s.get("durum") == "STAGED"]
    n, toplam = merge_safe(staged) if staged else (0, "?")
    print("\n" + "=" * 74)
    print("STAGED (commit ETMEDIM — fiyatlari INDIRIMSIZ ******** fiyatiyla dogrula):")
    for s in sorted(sonuc, key=lambda x: x.get("durum") != "STAGED"):
        if s.get("durum") == "STAGED":
            print("  ✔ %-38s | %-10s | usd:%s -%d%% -> %s | g:%d | %s"
                  % (s["urun"]["id"], s["kategori"], s["usd"], s["disc"], s["fiyat"], s["gorsel"], s["marka"]))
        else:
            print("  ✘", s["url"], "->", s["durum"])
    print("-" * 74)
    print("%s urun STAGE edildi (fiyat modu: %s), urunler.json toplam %s." % (n, mode, toplam))
    print("SONRAKI: fiyatlari dogrula -> yedekle + commit + push (lisans alani YOK, isimsiz commit).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Kullanim: python3 tools/cgt-ekle.py "<******** profil url>" [list|final]')
    mode = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in ("list", "final") else "list"
    main(sys.argv[1], mode)
