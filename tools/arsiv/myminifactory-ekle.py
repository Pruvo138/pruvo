#!/usr/bin/env python3
# EMEKLI - Okan 19 Tem: bu platformda arama YAPILMAZ (parity-backfill'den cikarildi).
"""PRUVO toplu urun ekleme ORKESTRATORU (MyMiniFactory) — PARALEL + concurrency-safe.
makerworld-ekle.py'nin (MakerWorld) MMF esdegeri; ayni Codex icerik adimini AYNEN kullanir.

Kullanim:
  python3 tools/myminifactory-ekle.py <object_id> [<object_id> ...]          # STAGE eder
  python3 tools/myminifactory-ekle.py --kuru <object_id> [<object_id> ...]   # KURU MOD: yazmaz, gosterir

Her id PARALEL islenir:
  detail -> lisans kapisi (satilamaz atla: string FAIL-CLOSED + licenses[] flag capraz reddi) ->
  galeri gorselleri indir -> .thing-cache/mmf<id>/{gN.jpg, meta.json} yaz ->
  thing-codex.py mmf<id> (gorsel secimi + Turkce icerik + fiyat_oneri) -> secili gorseller R2 ->
  STAGE. Yazma dosya KILIDI (.urunler.lock flock) altinda urunler.json'u O AN yeniden okuyup
  ekler (EZMEZ). COMMIT ETMEZ; sonda gozden gecirme tablosu basar.

MMF cache/R2 anahtari `mmf<id>` -> Printables (pr<id>) / MakerWorld (mw<id>) / Thingiverse (<id>)
ile CAKISMAZ. OLCU: MMF tam STL indirme OAuth ister (API key ile alinmaz); Object.dimensions
STRING alani parse edilir (parse_dimensions) -> yoksa olcu None (kaynak notuna yazilir).
ANAHTAR GEREKIR (MMF API). Anahtar yoksa net rapor basar (uydurma yok).
"""
import concurrent.futures, fcntl, importlib.util, json, os, re, subprocess, sys, tempfile

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
CACHE = os.path.join(ROOT, ".thing-cache")
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
PY = sys.executable or "python3"
WORKERS = int(os.environ.get("PRUVO_WORKERS", "6"))

# api + yardimci modulleri betigin KENDI dizininden yukle (worktree'de de calissin).
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(_HERE, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mmf = _load("myminifactory_api", "myminifactory-api.py")
bi = _load("baski_ipucu", "baski_ipucu.py")
fo = _load("filament_ortak", "filament_ortak.py")


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


def _satilabilir(d):
    """String kapisi (FAIL-CLOSED) VE licenses[] flag capraz reddi. flag asla KURTARMAZ."""
    lic = d.get("license") or ""
    if not mmf.satilabilir(lic):
        return False, lic
    if mmf.ticari_flags(d.get("licenses")) is False:
        return False, lic
    return True, lic


def prep(oid, key):
    """Gorseller + (mumkunse) olcu + meta.json'u .thing-cache/mmf<id>/'e yazar.
    Doner: (meta, lisans_str) veya (None, lisans_str) = satilamaz atla sinyali."""
    d = mmf.detail(oid)
    if not d:
        raise RuntimeError("obje bulunamadi")
    ok, lic = _satilabilir(d)
    if not ok:
        return None, lic                       # satilamaz -> atla sinyali
    outdir = os.path.join(CACHE, key); os.makedirs(outdir, exist_ok=True)
    saved = []
    for url in mmf.gallery_images(d, limit=8):
        try:
            blob = mmf.http_get(url)
        except Exception:
            continue
        jpg = os.path.join(outdir, "g%d.jpg" % (len(saved) + 1))
        if sips_jpeg(blob, jpg):
            saved.append(os.path.basename(jpg))
        if len(saved) >= 8:
            break
    # olcu: MMF tam STL OAuth-gated; Object.dimensions string'inden parse et.
    olcu = mmf.parse_dimensions(d.get("dimensions"))
    meta = {"id": key, "baslik": d.get("name", ""),
            "tasarimci": mmf.designer_adi(d),
            "lisans": lic,
            "olcu_mm": [round(x) for x in olcu] if olcu else None,
            "gorseller": saved,
            "baski": bi.baski_ipucu(d.get("printing_details") or d.get("description") or ""),
            "url": mmf.model_url(oid, d.get("url")), "oid": oid}
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w"), ensure_ascii=False)
    return meta, lic


def process_one(oid):
    """PARALEL calisir; urunler.json'a DOKUNMAZ."""
    key = "mmf" + str(oid)
    try:
        meta, lic = prep(oid, key)
        if meta is None:
            return {"id": oid, "durum": "ATLA: satilamaz lisans", "lisans": lic}
        if not meta.get("gorseller"):
            return {"id": oid, "durum": "ATLA: gorsel indirilemedi"}
        subprocess.run([PY, os.path.join(TOOLS, "thing-codex.py"), key], capture_output=True, text=True)
        onerip = os.path.join(CACHE, key, "oneri.json")
        if not os.path.exists(onerip):
            return {"id": oid, "durum": "HATA: codex oneri yok"}
        o = json.load(open(onerip))
        uid = re.sub(r"[^a-z0-9]+", "-", (o.get("baslik") or key).lower()).strip("-")[:60] or key
        # R2 gorsel anahtari KAYNAK-ID'den (mmf<id>) turer, baslik-slug'indan DEGIL (cakisma onlemi).
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
            return {"id": oid, "durum": "HATA: gorsel yuklenemedi"}
        cc_tur = mmf.cc_turu(lic)
        urun = {"id": uid, "kategori": o.get("kategori", "Tamirat"), "marka": o.get("marka", []),
                "baslik": o.get("baslik", key), "aciklama": o.get("aciklama", ""),
                "fiyat": o.get("fiyat_oneri", ""), "gorseller": urls}
        tavsiye = fo.tavsiye_filament(meta.get("baski", ""))
        if tavsiye:
            urun["tavsiyeFilament"] = tavsiye
        if cc_tur:
            urun["lisans"] = {"tasarimci": meta.get("tasarimci", "?"), "tur": cc_tur}
        src = {"kaynak": "MyMiniFactory", "link": meta.get("url"),
               "lisans": lic, "tasarimci": meta.get("tasarimci", "?"),
               "tur": "ucretsiz-cc" if cc_tur else "diger", "baski": meta.get("baski", ""),
               "not": ("en buyuk parca %s mm" % meta.get("olcu_mm")) if meta.get("olcu_mm")
                      else "olcu yok (MMF tam STL OAuth-gated; dimensions bos/ayristirilmadi)"}
        return {"id": oid, "durum": "STAGED", "urun": urun, "src": src,
                "kategori": urun["kategori"], "marka": urun["marka"], "gorsel": len(urls),
                "fiyat": urun["fiyat"], "baslik": urun["baslik"]}
    except Exception as e:
        return {"id": oid, "durum": "HATA: %s" % str(e)[:120]}


def _atomic_write(path, obj, **kw):
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, **kw)
    os.replace(tmp, path)


def merge_safe(staged):
    """urunler.json + .urun-kaynaklari.json'a SADECE .urunler.lock flock'u altinda, kilit icinde
    O AN yeniden okuyup yazar (makerworld-ekle.py / printables-ekle.py merge_safe ile BIREBIR ayni
    desen; ezmez)."""
    lockf = open(LOCK, "w"); fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        urunler = json.load(open(URUNLER)); kaynak = json.load(open(KAYNAK))
        mevcut = {p["id"] for p in urunler}; yeni = []
        for s in staged:
            urun = s["urun"]; uid = urun["id"]
            if uid in mevcut:
                uid = uid + "-mmf" + str(s["id"]); urun["id"] = uid   # id cakismasi -> mmf<id> ile ayir
            mevcut.add(uid); yeni.append(urun); kaynak[uid] = s["src"]
        for u in reversed(yeni):
            urunler.insert(0, u)
        _atomic_write(URUNLER, urunler, ensure_ascii=False, indent=2)
        _atomic_write(KAYNAK, kaynak, ensure_ascii=False, indent=1)
        return len(yeni), len(urunler)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()


def kuru(ids):
    """KURU MOD: urunler.json'a YAZMAZ, R2/Codex CAGIRMAZ. Her id icin meta+lisans+gorsel
    dogru geldi mi gosterir (canli duman testi). ANAHTAR GEREKIR."""
    try:
        mmf.require_key()
    except mmf.MMFNoKey as e:
        print("ANAHTAR YOK — kuru mod calisamaz:", e)
        return
    print("KURU MOD (yazma YOK) | islenecek:", len(ids), "| kaynak: MyMiniFactory\n", flush=True)
    for oid in ids:
        try:
            d = mmf.detail(oid)
        except Exception as e:                                   # noqa: BLE001
            print("  ✘ %s -> HATA: %s" % (oid, e)); continue
        if not d:
            print("  ✘ %s -> obje bulunamadi" % oid); continue
        lic = d.get("license") or ""
        flags = mmf.ticari_flags(d.get("licenses"))
        sat = mmf.satilabilir(lic) and flags is not False
        imgs = mmf.gallery_images(d, limit=8)
        ok_img = 0
        with tempfile.TemporaryDirectory() as td:
            for j, url in enumerate(imgs[:2], 1):
                try:
                    blob = mmf.http_get(url)
                    if sips_jpeg(blob, os.path.join(td, "t%d.jpg" % j)):
                        ok_img += 1
                except Exception:
                    pass
        olcu = mmf.parse_dimensions(d.get("dimensions"))
        print("  %s id=%s" % ("✔" if sat else "✘(satilamaz)", oid))
        print("     baslik   : %s" % (d.get("name", "")[:70]))
        print("     tasarimci: %s" % mmf.designer_adi(d))
        print("     lisans   : %r -> satilabilir=%s (flags=%s)  cc_turu=%r"
              % (lic, sat, flags, mmf.cc_turu(lic)))
        print("     olcu     : dimensions=%r -> %s mm" % (d.get("dimensions"), olcu))
        print("     gorsel   : %d bulundu, %d/2 indirilip JPEG dogrulandi" % (len(imgs), ok_img))
        print("     link     : %s" % mmf.model_url(oid, d.get("url")))
        print()


def main(ids):
    try:
        mmf.require_key()
    except mmf.MMFNoKey as e:
        print("ANAHTAR YOK — ekleme calisamaz:", e)
        return
    print("Islenecek:", len(ids), "urun | paralel worker:", WORKERS, "| kaynak: MyMiniFactory", flush=True)
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
    print("SONRAKI: mmf<id>/oneri.json'lari suz -> fiyat/kategori/gorsel duzelt -> yedekle + commit + push.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit("Kullanim: python3 tools/myminifactory-ekle.py [--kuru] <object_id> [<object_id> ...]")
    if args[0] == "--kuru":
        ids = args[1:]
        if not ids:
            sys.exit("Kullanim: python3 tools/myminifactory-ekle.py --kuru <object_id> ...")
        kuru(ids)
    else:
        main(args)
