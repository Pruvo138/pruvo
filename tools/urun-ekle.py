#!/usr/bin/env python3
"""PRUVO toplu urun ekleme ORKESTRATORU (Thingiverse) — PARALEL + concurrency-safe.

Kullanim:  python3 tools/urun-ekle.py <thing_id> [<thing_id> ...]

Her id PARALEL islenir: thing-hazirla (gorsel+STL+olcu+meta) -> lisans NC kapisi -> thing-codex
(gorsel secimi + Turkce icerik + fiyat_oneri) -> secili gorseller R2 -> STAGE. Yazma: dosya KILIDI
altinda urunler.json'u O AN yeniden okuyup ekler (stale snapshot degil) -> baska oturum ayni anda
yazsa bile EZMEZ. COMMIT ETMEZ; sonda gozden gecirme tablosu basar.
"""
import concurrent.futures, fcntl, importlib.util, json, os, re, subprocess, sys, tempfile

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
_fspec = importlib.util.spec_from_file_location("filament_ortak", os.path.join(TOOLS, "filament_ortak.py"))
fo = importlib.util.module_from_spec(_fspec); _fspec.loader.exec_module(fo)
_gspec = importlib.util.spec_from_file_location("gorsel_mukerrer_kapisi", os.path.join(TOOLS, "gorsel_mukerrer_kapisi.py"))
gmk = importlib.util.module_from_spec(_gspec); _gspec.loader.exec_module(gmk)
# R2 anahtar turetme TEK KAYNAK (satir-ici kopya YASAK, bkz tools/r2_anahtar.py)
_r2spec = importlib.util.spec_from_file_location(
    "r2_anahtar", os.path.join(os.path.dirname(os.path.abspath(__file__)), "r2_anahtar.py"))
r2k = importlib.util.module_from_spec(_r2spec); _r2spec.loader.exec_module(r2k)
IMGROOT = os.path.join(ROOT, ".thing-cache")
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
PY = sys.executable or "python3"
WORKERS = int(os.environ.get("PRUVO_WORKERS", "6"))


def lisans_map(lic):
    l = (lic or "").lower()
    if "noncommercial" in l or "non-commercial" in l or "non commercial" in l:
        return False, None
    if "public domain" in l or "cc0" in l:
        return True, None
    if "creative commons" in l or l.startswith("cc "):
        if "share alike" in l or "sharealike" in l:
            return True, "CC BY-SA 4.0"
        if "no deriv" in l:
            return True, "CC BY-ND 4.0"
        return True, "CC BY 4.0"
    if "gnu" in l or "gpl" in l or "bsd" in l:
        return True, None
    return True, None


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


def process_one(tid):
    """PARALEL calisir; urunler.json'a DOKUNMAZ."""
    try:
        subprocess.run([PY, os.path.join(TOOLS, "thing-hazirla.py"), tid], capture_output=True, text=True)
        metap = os.path.join(IMGROOT, tid, "meta.json")
        if not os.path.exists(metap):
            return {"id": tid, "durum": "HATA: hazirla meta.json uretmedi"}
        meta = json.load(open(metap))
        satilir, cc_tur = lisans_map(meta.get("lisans"))
        if not satilir:
            return {"id": tid, "durum": "ATLA: NC/Non-Commercial (satilamaz)", "lisans": meta.get("lisans")}
        if not meta.get("stl_adet"):
            return {"id": tid, "durum": "ATLA: STL indirilemedi (0 dosya)"}
        ai = subprocess.run([PY, os.path.join(TOOLS, "thing-codex.py"), tid], capture_output=True, text=True)
        if ai.returncode != 0:
            return {"id": tid, "durum": "HATA: kredi kapisi — urun AI izni yok"}
        onerip = os.path.join(IMGROOT, tid, "oneri.json")
        if not os.path.exists(onerip):
            return {"id": tid, "durum": "HATA: codex oneri yok"}
        o = json.load(open(onerip))
        uid = r2k.urun_slug(o.get("baslik") or tid, yedek=tid)
        # R2 gorsel anahtari KAYNAK-ID'den (th<tid>) turer, baslik-slug'indan (uid) DEGIL: iki farkli
        # urun ayni basligi uretse bile anahtarlari cakismaz (bkz tools/r2_anahtar.py +
        # tools/r2-anahtar-test.py). uid, JSON id'si + SEO URL'si icin kalir.
        gkey = r2k.gkey("Thingiverse", tid)
        d = os.path.join(IMGROOT, tid)
        secili = o.get("sec_gorseller") or sorted(f for f in os.listdir(d) if f.startswith("g") and f.endswith(".jpg"))
        # ALGISAL MUKERRER KAPISI (bkz gorsel_mukerrer_kapisi.py): ayni fotografin ikizini R2'ye
        # yuklemeden ELE. Yeni urunde yayin gorseli yok -> aday-ici dedup (birebir/yakin ikiz
        # secildiyse birini birak). PIL yoksa FAIL-OPEN (hicbir seyi elemez, akis bozulmaz).
        secili, _mkres = gmk.secili_temizle(d, secili)
        urls = []
        for i, fn in enumerate(secili, 1):
            fp = os.path.join(d, fn)
            if os.path.exists(fp):
                uu = sips_upload(fp, r2k.gorsel_yolu(gkey, i))
                if uu:
                    urls.append(uu)
        if not urls:
            return {"id": tid, "durum": "HATA: gorsel yuklenemedi"}
        urun = {"id": uid, "kategori": o.get("kategori", "Tamirat"), "marka": o.get("marka", []),
                "baslik": o.get("baslik", tid), "aciklama": o.get("aciklama", ""),
                "fiyat": o.get("fiyat_oneri", ""), "gorseller": urls}
        # Kaynaktaki baski ipucunda malzeme onerisi varsa SANITIZE override yaz:
        # sadece kanonik malzeme adi gecer, tasarimci adi/kaynak izi TASINMAZ (gizlilik).
        tavsiye = fo.tavsiye_filament(meta.get("baski", ""))
        if tavsiye:
            urun["tavsiyeFilament"] = tavsiye
        if cc_tur:
            urun["lisans"] = {"tasarimci": meta.get("tasarimci", "?"), "tur": cc_tur}
        src = {"kaynak": "Thingiverse", "link": "https://www.thingiverse.com/thing:" + tid,
               "lisans": meta.get("lisans", ""), "tasarimci": meta.get("tasarimci", "?"),
               "tur": "ucretsiz-cc" if cc_tur else "diger", "baski": meta.get("baski", ""),
               "not": "en buyuk parca %s mm; %d STL" % (meta.get("olcu_mm"), meta.get("stl_adet", 0))}
        return {"id": tid, "durum": "STAGED", "urun": urun, "src": src,
                "kategori": urun["kategori"], "marka": urun["marka"], "gorsel": len(urls),
                "fiyat": urun["fiyat"], "baslik": urun["baslik"]}
    except Exception as e:
        return {"id": tid, "durum": "HATA: %s" % str(e)[:120]}


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
    print("Islenecek:", len(ids), "urun | paralel worker:", WORKERS, flush=True)
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
    print("SONRAKI: oneri.json'lari suz -> fiyat/kategori/gorsel duzelt -> yedekle + commit + push.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanim: python3 tools/urun-ekle.py <thing_id> [<thing_id> ...]")
    main(sys.argv[1:])
