#!/usr/bin/env python3
"""PRUVO toplu urun ekleme ORKESTRATORU (Printables) — PARALEL + concurrency-safe.
urun-ekle.py'nin (Thingiverse) Printables esdegeri; Gemini adimini AYNEN tekrar kullanir.

Kullanim:  python3 tools/printables-ekle.py <print_id> [<print_id> ...]

Her id PARALEL islenir:
  detail -> lisans NC kapisi (satilamaz atla) -> galeri gorselleri + en buyuk STL indir + olcu ->
  .thing-cache/pr<id>/{gN.jpg, meta.json} yaz -> thing-gemini.py pr<id> (gorsel secimi + Turkce icerik
  + fiyat_oneri) -> secili gorseller R2 -> STAGE. Yazma dosya KILIDI altinda urunler.json'u O AN yeniden
  okuyup ekler (EZMEZ). COMMIT ETMEZ; sonda gozden gecirme tablosu basar.

Printables cache anahtari `pr<id>` -> Thingiverse cache'iyle (.thing-cache/<id>) CAKISMAZ.
Token GEREKMEZ (Printables public GraphQL).
"""
import concurrent.futures, fcntl, importlib.util, json, os, re, subprocess, sys, tempfile

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
CACHE = os.path.join(ROOT, ".thing-cache")
STLDIR = os.path.join(ROOT, "stl")
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
PY = sys.executable or "python3"
WORKERS = int(os.environ.get("PRUVO_WORKERS", "6"))

_spec = importlib.util.spec_from_file_location("pr_api", os.path.join(TOOLS, "printables-api.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)

_bspec = importlib.util.spec_from_file_location("baski_ipucu", os.path.join(TOOLS, "baski_ipucu.py"))
bi = importlib.util.module_from_spec(_bspec)
_bspec.loader.exec_module(bi)

_bd = os.path.join(ROOT, ".stl-backup-dir")
DRIVE = open(_bd).read().strip() if os.path.exists(_bd) else None


def sips_jpeg(src_bytes, out_jpg):
    raw = tempfile.NamedTemporaryFile(delete=False, suffix=".raw"); raw.write(src_bytes); raw.close()
    subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1400", "-s", "formatOptions", "85",
                    raw.name, "--out", out_jpg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.unlink(raw.name)
    return os.path.exists(out_jpg) and os.path.getsize(out_jpg) > 3000


def sips_upload(local_jpg, key):
    small = os.path.join(tempfile.gettempdir(), "up_" + os.path.basename(key))
    subprocess.run(["sips", "-Z", "1000", "-s", "formatOptions", "80", local_jpg, "--out", small],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run([PY, os.path.join(TOOLS, "r2-upload.py"), small, key], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.strip().startswith("https://"):
            return line.strip()
    return None


def prep(pid, key):
    """Gorseller + STL + meta.json'u .thing-cache/pr<id>/'e yazar. (meta, olcu, stl_adet) doner."""
    d = pr.detail(pid)
    if not d:
        raise RuntimeError("model bulunamadi")
    lic = d.get("license") or {}
    abbr = lic.get("abbreviation") or ""
    if not pr.satilabilir(abbr):
        return None, abbr, lic.get("name")   # NC -> atla sinyali
    outdir = os.path.join(CACHE, key); os.makedirs(outdir, exist_ok=True)
    # gorseller (order'a gore, en fazla 8)
    saved = []
    for im in sorted(d.get("images") or [], key=lambda x: x.get("order") or 0):
        if len(saved) >= 8:
            break
        try:
            blob = pr.http_get(pr.img_url(im["filePath"]))
        except Exception:
            continue
        jpg = os.path.join(outdir, "g%d.jpg" % (len(saved) + 1))
        if sips_jpeg(blob, jpg):
            saved.append(os.path.basename(jpg))
    # model dosyasi (en buyuk gercek .stl; yoksa .3mf'e duser) + olcu
    stls = [s for s in (d.get("stls") or []) if (s.get("name") or "").lower().endswith((".stl", ".3mf"))]
    olcu = None
    if stls:
        stlpath_noext = os.path.join(STLDIR, key); os.makedirs(STLDIR, exist_ok=True)
        try:
            _, stlpath, _ = pr.download_stl(pid, stlpath_noext)
            olcu = pr.model_bbox(stlpath)
            if DRIVE and os.path.isdir(DRIVE):
                ext = os.path.splitext(stlpath)[1]
                with open(stlpath, "rb") as rf, open(os.path.join(DRIVE, key + ext), "wb") as wf:
                    wf.write(rf.read())
        except Exception:
            pass
    meta = {"id": key, "baslik": d.get("name", ""),
            "tasarimci": (d.get("user") or {}).get("publicUsername", "?"),
            "lisans": lic.get("name", abbr),
            "olcu_mm": [round(x) for x in olcu] if olcu else None,
            "stl_adet": len(stls), "gorseller": saved,
            "baski": bi.baski_ipucu(d.get("description")),
            "abbr": abbr, "slug": d.get("slug"), "pid": pid}
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w"), ensure_ascii=False)
    return meta, abbr, lic.get("name")


def process_one(pid):
    """PARALEL calisir; urunler.json'a DOKUNMAZ."""
    key = "pr" + pid
    try:
        meta, abbr, licname = prep(pid, key)
        if meta is None:
            return {"id": pid, "durum": "ATLA: NC/Non-Commercial (satilamaz)", "lisans": abbr}
        if not meta.get("gorseller"):
            return {"id": pid, "durum": "ATLA: gorsel indirilemedi"}
        subprocess.run([PY, os.path.join(TOOLS, "thing-gemini.py"), key], capture_output=True, text=True)
        onerip = os.path.join(CACHE, key, "oneri.json")
        if not os.path.exists(onerip):
            return {"id": pid, "durum": "HATA: gemini oneri yok"}
        o = json.load(open(onerip))
        uid = re.sub(r"[^a-z0-9]+", "-", (o.get("baslik") or key).lower()).strip("-")[:60] or key
        d = os.path.join(CACHE, key)
        secili = o.get("sec_gorseller") or meta["gorseller"]
        urls = []
        for i, fn in enumerate(secili, 1):
            fp = os.path.join(d, fn)
            if os.path.exists(fp):
                uu = sips_upload(fp, "urunler/%s-%d.jpg" % (uid, i))
                if uu:
                    urls.append(uu)
        if not urls:
            return {"id": pid, "durum": "HATA: gorsel yuklenemedi"}
        cc_tur = pr.cc_turu(abbr)
        urun = {"id": uid, "kategori": o.get("kategori", "Tamirat"), "marka": o.get("marka", []),
                "baslik": o.get("baslik", key), "aciklama": o.get("aciklama", ""),
                "fiyat": o.get("fiyat_oneri", ""), "gorseller": urls}
        if cc_tur:
            urun["lisans"] = {"tasarimci": meta.get("tasarimci", "?"), "tur": cc_tur}
        src = {"kaynak": "Printables", "link": pr.model_url(pid, meta.get("slug")),
               "lisans": licname or abbr, "tasarimci": meta.get("tasarimci", "?"),
               "tur": "ucretsiz-cc" if cc_tur else "diger", "baski": meta.get("baski", ""),
               "not": "en buyuk parca %s mm; %d STL" % (meta.get("olcu_mm"), meta.get("stl_adet", 0))}
        return {"id": pid, "durum": "STAGED", "urun": urun, "src": src,
                "kategori": urun["kategori"], "marka": urun["marka"], "gorsel": len(urls),
                "fiyat": urun["fiyat"], "baslik": urun["baslik"]}
    except Exception as e:
        return {"id": pid, "durum": "HATA: %s" % str(e)[:120]}


def _atomic_write(path, obj, **kw):
    """json.dump'i once gecici dosyaya yazip os.replace ile devreye alir; yaziyi yarida
    kesen bir crash/kill orijinal dosyayi asla yarim/bozuk birakmaz."""
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, **kw)
    os.replace(tmp, path)


def merge_safe(staged):
    lockf = open(LOCK, "w"); fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        urunler = json.load(open(URUNLER)); kaynak = json.load(open(KAYNAK))
        mevcut = {p["id"] for p in urunler}; yeni = []
        for s in staged:
            urun = s["urun"]; uid = urun["id"]
            if uid in mevcut:
                uid = uid + "-" + s["id"]; urun["id"] = uid
            mevcut.add(uid); yeni.append(urun); kaynak[uid] = s["src"]
        for u in reversed(yeni):
            urunler.insert(0, u)
        _atomic_write(URUNLER, urunler, ensure_ascii=False, indent=2)
        _atomic_write(KAYNAK, kaynak, ensure_ascii=False, indent=1)
        return len(yeni), len(urunler)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()


def main(ids):
    print("Islenecek:", len(ids), "urun | paralel worker:", WORKERS, "| kaynak: Printables", flush=True)
    sonuc = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(process_one, t): t for t in ids}
        done = 0
        for f in concurrent.futures.as_completed(futs):
            r = f.result(); sonuc.append(r); done += 1
            print("  (%d/%d) %s %s" % (done, len(ids), r.get("durum"),
                  r["urun"]["id"] if r.get("durum") == "STAGED" else r.get("id", "")), flush=True)
    staged = [s for s in sonuc if s.get("durum") == "STAGED"]
    n, toplam = merge_safe(staged) if staged else (0, "?")
    print("\n" + "=" * 70)
    print("STAGED (commit ETMEDIM — gozden gecir, fiyatlari kesinlestir):")
    for s in sorted(sonuc, key=lambda x: x.get("durum") != "STAGED"):
        if s.get("durum") == "STAGED":
            print("  ✔ %-42s | %-11s | g:%d | %s | marka:%s"
                  % (s["urun"]["id"], s["kategori"], s["gorsel"], s["fiyat"], s["marka"]))
        else:
            print("  ✘ %s -> %s %s" % (s.get("id"), s["durum"], s.get("lisans", "")))
    print("-" * 70)
    print("%s urun STAGE edildi, urunler.json toplam %s." % (n, toplam))
    print("SONRAKI: pr<id>/oneri.json'lari suz -> fiyat/kategori/gorsel duzelt -> yedekle + commit + push.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanim: python3 tools/printables-ekle.py <print_id> [<print_id> ...]")
    main(sys.argv[1:])
