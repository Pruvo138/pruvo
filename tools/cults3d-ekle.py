#!/usr/bin/env python3
# ⛔ ÇAĞIRMA — EMEKLİ (Okan 18 Tem: Cults3D rate-limit/429 yüzünden çıkarıldı)
"""PRUVO toplu urun ekleme ORKESTRATORU (Cults3D) — PARALEL + concurrency-safe.
makerworld-ekle.py'nin Cults3D esdegeri; ayni Codex icerik adimini (thing-codex.py) AYNEN kullanir.

Kullanim:
  python3 tools/cults3d-ekle.py <slug> [<slug> ...]          # STAGE eder
  python3 tools/cults3d-ekle.py --kuru <slug> [<slug> ...]   # KURU MOD: yazmaz, gosterir
  (KIMLIK GEREKIR: env CULTS_USERNAME + CULTS_API_KEY — bkz cults3d-api.py.)

Her slug PARALEL islenir:
  detail -> lisans kapisi (satilamaz atla) + ucretsiz kapisi (ucretli atla) -> galeri gorselleri
  indir -> .thing-cache/c3d<slug>/{gN.jpg, meta.json} yaz -> thing-codex.py c3d<slug> (gorsel secimi +
  Turkce icerik + fiyat_oneri) -> secili gorseller R2 -> STAGE. Yazma dosya KILIDI (.urunler.lock
  flock) altinda urunler.json'u O AN yeniden okuyup ekler (EZMEZ). COMMIT ETMEZ; sonda tablo basar.

R2/cache anahtari `c3d<slug>` -> MakerWorld (mw<id>) / Printables (pr<id>) / Thingiverse (<id>) ile
CAKISMAZ. OLCU: Cults3D blueprint indirme hesap/satin-alma gerektirir -> olcu genelde YOK (kaynak
notuna yazilir). CULTS3D_TRY_MEASURE=1 verilirse blueprint fileUrl varsa indirip olcmeyi DENER.

HIZ SINIRI: Cults3D GraphQL ~60/30sn, ~500/gun. Yalniz detail() cagrilari sayilir; gorsel
indirmeleri (CDN) saymaz. WORKERS varsayilan 4 (burst throttle'a saygi); PRUVO_WORKERS ile degistir.
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
WORKERS = int(os.environ.get("PRUVO_WORKERS", "4"))
TRY_MEASURE = os.environ.get("CULTS3D_TRY_MEASURE")   # verilirse olcu icin blueprint indirme DENENIR

# api + yardimci modulleri betigin KENDI dizininden yukle (worktree'de de calissin).
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(_HERE, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


c3 = _load("cults3d_api", "cults3d-api.py")
bi = _load("baski_ipucu", "baski_ipucu.py")
fo = _load("filament_ortak", "filament_ortak.py")

sys.path.insert(0, _HERE)
import drive_yolu
DRIVE = drive_yolu.stl_dizini(sessiz=True)


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


def prep(slug, key):
    """Gorseller + (mumkunse) olcu + meta.json'u .thing-cache/c3d<slug>/'e yazar.
    Doner: (meta, lisans_str) veya (None, lisans_str) = satilamaz/ucretli atla sinyali."""
    c = c3.detail(slug)
    if not c:
        raise RuntimeError("model bulunamadi")
    lic = c3.lisans_str(c)
    if not c3.satilabilir(lic):
        return None, lic                        # satilamaz -> atla sinyali
    if not c3.ucretsiz(c):
        return None, lic + " (UCRETLI)"         # ucretli pazar modeli -> atla sinyali
    outdir = os.path.join(CACHE, key); os.makedirs(outdir, exist_ok=True)
    saved = []
    for url in c3.gallery_images(c, limit=8):
        try:
            blob = c3.http_get(url)
        except Exception:
            continue
        jpg = os.path.join(outdir, "g%d.jpg" % (len(saved) + 1))
        if sips_jpeg(blob, jpg):
            saved.append(os.path.basename(jpg))
        if len(saved) >= 8:
            break
    # olcu: Cults3D blueprint indirme hesap/satin-alma gerektirir. TRY_MEASURE varsa DENE, yoksa None.
    olcu = None
    if TRY_MEASURE:
        try:
            os.makedirs(STLDIR, exist_ok=True)
            _, stlpath, _ = c3.download_stl(slug, os.path.join(STLDIR, key))
            olcu = c3.model_bbox(stlpath)
            if DRIVE and os.path.isdir(DRIVE) and os.path.exists(stlpath):
                with open(stlpath, "rb") as rf, open(os.path.join(DRIVE, key + ".stl"), "wb") as wf:
                    wf.write(rf.read())
        except Exception:
            olcu = None
    meta = {"id": key, "baslik": c.get("name", ""),
            "tasarimci": (c.get("creator") or {}).get("nick", "?"),
            "lisans": c3.lisans_ad(c),
            "olcu_mm": [round(x) for x in olcu] if olcu else None,
            "gorseller": saved,
            "baski": bi.baski_ipucu(c.get("description") or ""),
            "slug": slug}
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w"), ensure_ascii=False)
    return meta, lic


def process_one(slug):
    """PARALEL calisir; urunler.json'a DOKUNMAZ."""
    # cache/R2 anahtari FULL slug'dan (tirelerle korunur, KISALTMA YOK) -> slug globalce benzersiz
    # oldugu icin anahtar da benzersiz; lossy kisaltma R2 gorsel-cakismasi riskini dogururdu
    # (bkz memory: gorsel-anahtar-cakismasi, 143 urun tek fotoya dusmustu).
    key = "c3d" + re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    try:
        meta, lic = prep(slug, key)
        if meta is None:
            return {"id": slug, "durum": "ATLA: satilamaz/ucretli lisans", "lisans": lic}
        if not meta.get("gorseller"):
            return {"id": slug, "durum": "ATLA: gorsel indirilemedi"}
        subprocess.run([PY, os.path.join(TOOLS, "thing-codex.py"), key], capture_output=True, text=True)
        onerip = os.path.join(CACHE, key, "oneri.json")
        if not os.path.exists(onerip):
            return {"id": slug, "durum": "HATA: codex oneri yok"}
        o = json.load(open(onerip))
        uid = re.sub(r"[^a-z0-9]+", "-", (o.get("baslik") or key).lower()).strip("-")[:60] or key
        # R2 gorsel anahtari KAYNAK-ID'den (c3d<slug>) turer, baslik-slug'indan DEGIL (cakisma onlemi).
        gkey = re.sub(r"[^a-z0-9-]+", "-", key.lower()).strip("-") or key
        d = os.path.join(CACHE, key)
        secili = o.get("sec_gorseller") or meta["gorseller"]
        urls = []
        for i, fn in enumerate(secili, 1):
            fp = os.path.join(d, fn)
            if os.path.exists(fp):
                uu = sips_upload(fp, "urunler/%s-%d.jpg" % (gkey, i))
                if uu:
                    urls.append(uu)
        if not urls:
            return {"id": slug, "durum": "HATA: gorsel yuklenemedi"}
        cc_tur = c3.cc_turu(lic)
        urun = {"id": uid, "kategori": o.get("kategori", "Tamirat"), "marka": o.get("marka", []),
                "baslik": o.get("baslik", key), "aciklama": o.get("aciklama", ""),
                "fiyat": o.get("fiyat_oneri", ""), "gorseller": urls}
        tavsiye = fo.tavsiye_filament(meta.get("baski", ""))
        if tavsiye:
            urun["tavsiyeFilament"] = tavsiye
        if cc_tur:
            urun["lisans"] = {"tasarimci": meta.get("tasarimci", "?"), "tur": cc_tur}
        src = {"kaynak": "Cults3D", "link": c3.model_url(c3.detail(slug)) or ("cults3d:" + slug),
               "lisans": meta.get("lisans", lic), "tasarimci": meta.get("tasarimci", "?"),
               "tur": "ucretsiz-cc" if cc_tur else "diger", "baski": meta.get("baski", ""),
               "not": ("en buyuk parca %s mm" % meta.get("olcu_mm")) if meta.get("olcu_mm")
                      else "olcu yok (Cults3D indirme hesap/satin-alma gerektirir)"}
        return {"id": slug, "durum": "STAGED", "urun": urun, "src": src,
                "kategori": urun["kategori"], "marka": urun["marka"], "gorsel": len(urls),
                "fiyat": urun["fiyat"], "baslik": urun["baslik"]}
    except Exception as e:
        return {"id": slug, "durum": "HATA: %s" % str(e)[:120]}


def _atomic_write(path, obj, **kw):
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, **kw)
    os.replace(tmp, path)


def merge_safe(staged):
    """urunler.json + .urun-kaynaklari.json'a SADECE .urunler.lock flock'u altinda, kilit icinde
    O AN yeniden okuyup yazar (makerworld-ekle.py merge_safe ile BIREBIR ayni desen; ezmez)."""
    lockf = open(LOCK, "w"); fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        urunler = json.load(open(URUNLER)); kaynak = json.load(open(KAYNAK))
        mevcut = {p["id"] for p in urunler}; yeni = []
        for s in staged:
            urun = s["urun"]; uid = urun["id"]
            if uid in mevcut:
                uid = uid + "-c3d"; urun["id"] = uid          # id cakismasi -> -c3d ile ayir
            mevcut.add(uid); yeni.append(urun); kaynak[uid] = s["src"]
        for u in reversed(yeni):
            urunler.insert(0, u)
        _atomic_write(URUNLER, urunler, ensure_ascii=False, indent=2)
        _atomic_write(KAYNAK, kaynak, ensure_ascii=False, indent=1)
        return len(yeni), len(urunler)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()


def kuru(slugs):
    """KURU MOD: urunler.json'a YAZMAZ, R2/Codex CAGIRMAZ. Her slug icin meta+lisans+gorsel
    dogru geldi mi gosterir (canli duman testi)."""
    print("KURU MOD (yazma YOK) | islenecek:", len(slugs), "| kaynak: Cults3D\n", flush=True)
    for slug in slugs:
        try:
            c = c3.detail(slug)
        except Exception as e:
            print("  ✘ %s -> API/kimlik hatasi: %s" % (slug, str(e)[:80])); continue
        if not c:
            print("  ✘ %s -> model bulunamadi" % slug); continue
        lic = c3.lisans_str(c)
        sat = c3.satilabilir(lic)
        free = c3.ucretsiz(c)
        imgs = c3.gallery_images(c, limit=8)
        ok_img = 0
        with tempfile.TemporaryDirectory() as td:
            for j, url in enumerate(imgs[:2], 1):
                try:
                    blob = c3.http_get(url)
                    if sips_jpeg(blob, os.path.join(td, "t%d.jpg" % j)):
                        ok_img += 1
                except Exception:
                    pass
        alinir = sat and free
        print("  %s slug=%s" % ("✔" if alinir else "✘(%s)" % ("ucretli" if sat and not free else "satilamaz"), slug))
        print("     baslik   : %s" % (c.get("name", "")[:70]))
        print("     tasarimci: %s" % (c.get("creator") or {}).get("nick"))
        print("     lisans   : %r -> satilabilir=%s ucretsiz=%s cc_turu=%r" % (lic, sat, free, c3.cc_turu(lic)))
        print("     gorsel   : %d bulundu, %d/2 indirilip JPEG dogrulandi" % (len(imgs), ok_img))
        print("     link     : %s" % c3.model_url(c))
        print()


def main(slugs):
    print("Islenecek:", len(slugs), "urun | paralel worker:", WORKERS, "| kaynak: Cults3D", flush=True)
    sonuc = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(process_one, t): t for t in slugs}
        done = 0
        for f in concurrent.futures.as_completed(futs):
            r = f.result(); sonuc.append(r); done += 1
            print("  (%d/%d) %s %s" % (done, len(slugs), r.get("durum"),
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
    print("SONRAKI: c3d<slug>/oneri.json'lari suz -> fiyat/kategori/gorsel duzelt -> yedekle + commit + push.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit("Kullanim: python3 tools/cults3d-ekle.py [--kuru] <slug> [<slug> ...]")
    if args[0] == "--kuru":
        ids = args[1:]
        if not ids:
            sys.exit("Kullanim: python3 tools/cults3d-ekle.py --kuru <slug> ...")
        kuru(ids)
    else:
        main(args)
