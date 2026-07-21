#!/usr/bin/env python3
"""PRUVO toplu urun ekleme ORKESTRATORU (MakerWorld) — PARALEL + concurrency-safe.
printables-ekle.py'nin (Printables) MakerWorld esdegeri; ayni Codex icerik adimini AYNEN kullanir.

Kullanim:
  python3 tools/makerworld-ekle.py <design_id> [<design_id> ...]          # STAGE eder
  python3 tools/makerworld-ekle.py --kuru <design_id> [<design_id> ...]   # KURU MOD: yazmaz, gosterir

Her id PARALEL islenir:
  detail -> lisans kapisi (satilamaz atla) -> galeri gorselleri indir ->
  .thing-cache/mw<id>/{gN.jpg, meta.json} yaz -> thing-codex.py mw<id> (gorsel secimi + Turkce icerik
  + fiyat_oneri) -> secili gorseller R2 -> STAGE. Yazma dosya KILIDI (.urunler.lock flock) altinda
  urunler.json'u O AN yeniden okuyup ekler (EZMEZ). COMMIT ETMEZ; sonda gozden gecirme tablosu basar.

MakerWorld cache/R2 anahtari `mw<id>` -> Printables (pr<id>) / Thingiverse (<id>) ile CAKISMAZ.
OLCU: MakerWorld model dosyasi indirme LOGIN ISTER (403) + API'de boyut yok -> olcu genelde YOK
(kaynak notuna yazilir). MW_COOKIE ortam degiskeni verilirse indirip olcmeyi DENER.
Token GEREKMEZ (MakerWorld public API).
"""
import concurrent.futures, fcntl, importlib.util, json, os, re, subprocess, sys, tempfile

# KOD KOKU (moduller, asagida _HERE) ile VERI KOKU (urunler.json + kilit) AYRIDIR —
# bkz tools/veri_kok.py. Worktree'den kosulursa STDERR'e gurultulu uyari basilir (akis olmez).
TOOLS = os.path.dirname(os.path.abspath(__file__))
_vkspec = importlib.util.spec_from_file_location("veri_kok", os.path.join(TOOLS, "veri_kok.py"))
_vk = importlib.util.module_from_spec(_vkspec)
_vkspec.loader.exec_module(_vk)
_KOD_KOK, ROOT, _KOK_UYARI = _vk.cozumle(__file__)
if _KOK_UYARI:
    sys.stderr.write(_KOK_UYARI)
CACHE = os.path.join(ROOT, ".thing-cache")
STLDIR = os.path.join(ROOT, "stl")
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
PY = sys.executable or "python3"
WORKERS = int(os.environ.get("PRUVO_WORKERS", "6"))
MW_COOKIE = os.environ.get("MW_COOKIE")   # verilirse olcu icin model indirme DENENIR

# api + yardimci modulleri betigin KENDI dizininden yukle (worktree'de de calissin).
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(_HERE, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mw = _load("makerworld_api", "makerworld-api.py")
bi = _load("baski_ipucu", "baski_ipucu.py")
fo = _load("filament_ortak", "filament_ortak.py")
gmk = _load("gorsel_mukerrer_kapisi", "gorsel_mukerrer_kapisi.py")
gbk = _load("gorsel_boyut_kapisi", "gorsel_boyut_kapisi.py")
# R2 anahtar turetme TEK KAYNAK (satir-ici kopya YASAK, bkz tools/r2_anahtar.py)
r2k = _load("r2_anahtar", "r2_anahtar.py")

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


def prep(did, key):
    """Gorseller + (mumkunse) olcu + meta.json'u .thing-cache/mw<id>/'e yazar.
    Doner: (meta, lisans_str) veya (None, lisans_str) = satilamaz atla sinyali."""
    d = mw.detail(did)
    if not d:
        raise RuntimeError("model bulunamadi")
    lic = d.get("license") or ""
    if not mw.satilabilir(lic):
        return None, lic                       # satilamaz -> atla sinyali
    outdir = os.path.join(CACHE, key); os.makedirs(outdir, exist_ok=True)
    saved = []
    for url in mw.gallery_images(d, limit=8):
        try:
            blob = mw.http_get(url)
        except Exception:
            continue
        jpg = os.path.join(outdir, "g%d.jpg" % (len(saved) + 1))
        if sips_jpeg(blob, jpg):
            saved.append(os.path.basename(jpg))
        if len(saved) >= 8:
            break
    # olcu: MakerWorld indirme login-gated. MW_COOKIE varsa DENE, yoksa None.
    olcu = None
    if MW_COOKIE:
        try:
            os.makedirs(STLDIR, exist_ok=True)
            _, stlpath, _ = mw.download_stl(did, os.path.join(STLDIR, key), cookie=MW_COOKIE)
            olcu = mw.model_bbox(stlpath) if hasattr(mw, "model_bbox") else None
            if olcu is None and hasattr(mw, "bbox_3mf"):
                olcu = mw.bbox_3mf(stlpath)
            if DRIVE and os.path.isdir(DRIVE) and os.path.exists(stlpath):
                with open(stlpath, "rb") as rf, open(os.path.join(DRIVE, key + ".3mf"), "wb") as wf:
                    wf.write(rf.read())
        except Exception:
            olcu = None
    meta = {"id": key, "baslik": d.get("title", ""),
            "tasarimci": (d.get("designCreator") or {}).get("name", "?"),
            "lisans": lic,
            "olcu_mm": [round(x) for x in olcu] if olcu else None,
            "gorseller": saved,
            "baski": bi.baski_ipucu(d.get("summary") or d.get("description") or ""),
            "slug": d.get("slug"), "did": did}
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w"), ensure_ascii=False)
    return meta, lic


def process_one(did):
    """PARALEL calisir; urunler.json'a DOKUNMAZ."""
    key = "mw" + str(did)
    try:
        meta, lic = prep(did, key)
        if meta is None:
            return {"id": did, "durum": "ATLA: satilamaz lisans", "lisans": lic}
        if not meta.get("gorseller"):
            return {"id": did, "durum": "ATLA: gorsel indirilemedi"}
        ai = subprocess.run([PY, os.path.join(TOOLS, "thing-codex.py"), key], capture_output=True, text=True)
        if ai.returncode != 0:
            return {"id": did, "durum": "HATA: kredi kapisi — urun AI izni yok"}
        onerip = os.path.join(CACHE, key, "oneri.json")
        if not os.path.exists(onerip):
            return {"id": did, "durum": "HATA: codex oneri yok"}
        o = json.load(open(onerip))
        uid = r2k.urun_slug(o.get("baslik") or key, yedek=key)
        # R2 gorsel anahtari KAYNAK-ID'den (mw<id>) turer, baslik-slug'indan DEGIL (cakisma onlemi).
        gkey = r2k.gkey("MakerWorld", did)
        d = os.path.join(CACHE, key)
        secili = o.get("sec_gorseller") or meta["gorseller"]
        # ALGISAL MUKERRER KAPISI: ayni fotografin ikizini R2'ye yuklemeden ELE (aday-ici dedup).
        # PIL yoksa FAIL-OPEN (hicbir seyi elemez, akis bozulmaz). bkz gorsel_mukerrer_kapisi.py
        secili, _mkres = gmk.secili_temizle(d, secili)
        # ASGARI BOYUT KAPISI (bkz gorsel_boyut_kapisi.py): 100x100 altindaki gorsel Google
        # Merchant "resim cok kucuk" reddi aliyor (olculen vaka 1000x88) -> R2'ye yuklemeden
        # ELE. Boyut okunamazsa FAIL-LOUD: gorsel gecer + stderr'e uyari.
        secili, _bres = gbk.secili_ele(d, secili)
        urls = []
        for i, fn in enumerate(secili, 1):
            fp = os.path.join(d, fn)
            if os.path.exists(fp):
                uu = sips_upload(fp, r2k.gorsel_yolu(gkey, i))
                if uu:
                    urls.append(uu)
        if not urls:
            return {"id": did, "durum": "HATA: gorsel yuklenemedi"}
        cc_tur = mw.cc_turu(lic)
        urun = {"id": uid, "kategori": o.get("kategori", "Tamirat"), "marka": o.get("marka", []),
                "baslik": o.get("baslik", key), "aciklama": o.get("aciklama", ""),
                "fiyat": o.get("fiyat_oneri", ""), "gorseller": urls}
        tavsiye = fo.tavsiye_filament(meta.get("baski", ""))
        if tavsiye:
            urun["tavsiyeFilament"] = tavsiye
        if cc_tur:
            urun["lisans"] = {"tasarimci": meta.get("tasarimci", "?"), "tur": cc_tur}
        src = {"kaynak": "MakerWorld", "link": mw.model_url(did, meta.get("slug")),
               "lisans": lic, "tasarimci": meta.get("tasarimci", "?"),
               "tur": "ucretsiz-cc" if cc_tur else "diger", "baski": meta.get("baski", ""),
               "not": ("en buyuk parca %s mm" % meta.get("olcu_mm")) if meta.get("olcu_mm")
                      else "olcu yok (MakerWorld indirme login-gated)"}
        return {"id": did, "durum": "STAGED", "urun": urun, "src": src,
                "kategori": urun["kategori"], "marka": urun["marka"], "gorsel": len(urls),
                "fiyat": urun["fiyat"], "baslik": urun["baslik"]}
    except Exception as e:
        return {"id": did, "durum": "HATA: %s" % str(e)[:120]}


def _atomic_write(path, obj, **kw):
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, **kw)
    os.replace(tmp, path)


def merge_safe(staged):
    """urunler.json + .urun-kaynaklari.json'a SADECE .urunler.lock flock'u altinda, kilit icinde
    O AN yeniden okuyup yazar (printables-ekle.py merge_safe ile BIREBIR ayni desen; ezmez)."""
    lockf = open(LOCK, "w"); fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        urunler = json.load(open(URUNLER)); kaynak = json.load(open(KAYNAK))
        mevcut = {p["id"] for p in urunler}; yeni = []
        for s in staged:
            urun = s["urun"]; uid = urun["id"]
            if uid in mevcut:
                uid = uid + "-mw" + str(s["id"]); urun["id"] = uid   # id cakismasi -> mw<id> ile ayir
            mevcut.add(uid); yeni.append(urun); kaynak[uid] = s["src"]
        for u in reversed(yeni):
            urunler.insert(0, u)
        _atomic_write(URUNLER, urunler, ensure_ascii=False, indent=2)
        _atomic_write(KAYNAK, kaynak, ensure_ascii=False, indent=1)
        return len(yeni), len(urunler)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()


def kuru(ids):
    """KURU MOD: urunler.json'a YAZMAZ, R2/Codex ÇAĞIRMAZ. Her id icin meta+lisans+gorsel
    dogru geldi mi gosterir (canli duman testi)."""
    print("KURU MOD (yazma YOK) | islenecek:", len(ids), "| kaynak: MakerWorld\n", flush=True)
    for did in ids:
        d = mw.detail(did)
        if not d:
            print("  ✘ %s -> model bulunamadi" % did); continue
        lic = d.get("license") or ""
        sat = mw.satilabilir(lic)
        imgs = mw.gallery_images(d, limit=8)
        # gorsellerin gercekten inip JPEG'e cevrilebildigini dogrula (ilk 2)
        ok_img = 0
        with tempfile.TemporaryDirectory() as td:
            for j, url in enumerate(imgs[:2], 1):
                try:
                    blob = mw.http_get(url)
                    if sips_jpeg(blob, os.path.join(td, "t%d.jpg" % j)):
                        ok_img += 1
                except Exception:
                    pass
        print("  %s id=%s" % ("✔" if sat else "✘(satilamaz)", did))
        print("     baslik   : %s" % (d.get("title", "")[:70]))
        print("     tasarimci: %s" % (d.get("designCreator") or {}).get("name"))
        print("     lisans   : %r -> satilabilir=%s  cc_turu=%r" % (lic, sat, mw.cc_turu(lic)))
        print("     gorsel   : %d bulundu, %d/2 indirilip JPEG dogrulandi" % (len(imgs), ok_img))
        print("     link     : %s" % mw.model_url(did, d.get("slug")))
        print()


def main(ids):
    print("Islenecek:", len(ids), "urun | paralel worker:", WORKERS, "| kaynak: MakerWorld", flush=True)
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
    print("SONRAKI: mw<id>/oneri.json'lari suz -> fiyat/kategori/gorsel duzelt -> yedekle + commit + push.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit("Kullanim: python3 tools/makerworld-ekle.py [--kuru] <design_id> [<design_id> ...]")
    if args[0] == "--kuru":
        ids = args[1:]
        if not ids:
            sys.exit("Kullanim: python3 tools/makerworld-ekle.py --kuru <design_id> ...")
        kuru(ids)
    else:
        main(args)
