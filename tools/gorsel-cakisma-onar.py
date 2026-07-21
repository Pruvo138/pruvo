#!/usr/bin/env python3
"""gorsel-cakisma-onar.py — R2 gorsel anahtari cakismasi ONARIMI (tek seferlik veri onarimi).

KOK NEDEN (ayri onarim: tools/gorsel-anahtar-test.py + printables-ekle.py yorumu): ekleyiciler
R2 anahtarini urun basligindan turetip merge_safe'ten once yukluyordu -> ayni basligi ureten iki
urun ayni anahtari ezerek TEK foto paylasiyordu. Bu arac, cakisan urunlerin her birinin gorselini
KAYNAKTAN yeniden indirip YENI, kaynak-id tabanli benzersiz anahtara (pr<pid>/th<tid>/cgt-<itemid>)
yukler ve urunler.json'daki gorseller[] alanini duzelt.py ile (guard-uyumlu, kilit altinda) gunceller.

Iki fazli (ikisi de LIVE main'e karsi calisir, ROOT=main):
  --plan        : cakisan urunleri tespit + kaynak coz + ne yapilacagini yaz (I/O YOK, salt-okunur).
  --getir       : her urunun gorselini kaynaktan indir + YENI anahtara R2'ye yukle; sonucu
                  onarim-getir.json'a yaz (urunler.json'a DOKUNMAZ; kesintiye dayanikli, resume eder).
  --uygula      : onarim-getir.json'daki yeni gorseller[]'i duzelt.py ile urunler.json'a yaz,
                  ~<chunk> urunde bir commit et (manifest penceresi kisa kalsin). Sonda re-tespit.

Kullanim:
  python3 tools/gorsel-cakisma-onar.py --plan
  python3 tools/gorsel-cakisma-onar.py --getir            # gerekince tekrar calistir (resume)
  python3 tools/gorsel-cakisma-onar.py --uygula
"""
import argparse
import collections
import concurrent.futures
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
PY = sys.executable or "python3"
STATE = os.path.join(TOOLS, "..", ".onarim-getir.json")   # gizli, resume durumu
N_IMG = 4          # urun basina en fazla gorsel geri yukle
CHUNK = 20         # kac urunde bir commit


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(TOOLS, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# R2 anahtar turetme TEK KAYNAK (satir-ici kopya YASAK, bkz tools/r2_anahtar.py).
# Betigin KENDI dizininden yuklenir ki worktree'de de dogru kopya kossun.
_r2spec = importlib.util.spec_from_file_location(
    "r2_anahtar", os.path.join(os.path.dirname(os.path.abspath(__file__)), "r2_anahtar.py"))
r2k = importlib.util.module_from_spec(_r2spec)
_r2spec.loader.exec_module(r2k)

pr = _load("printables-api.py", "pr_api_onar")
th = _load("thing-hazirla.py", "th_hazirla_onar")
cgt = _load("cgt-ekle.py", "cgt_ekle_onar")


# ----------------------------------------------------------------------------- tespit
def cakisan_urunler():
    urunler = json.load(open(URUNLER))
    url_ids = collections.defaultdict(set)
    for p in urunler:
        if isinstance(p, dict):
            for u in (p.get("gorseller") or []):
                url_ids[u].add(p["id"])
    etkilenen = set()
    for u, ids in url_ids.items():
        if len(ids) > 1:
            etkilenen |= ids
    return sorted(etkilenen)


# ----------------------------------------------------------------------------- kaynak coz
def resolve(pid, kaynak):
    """(platform, source_id, rec) doner. Kayit yoksa id sonundaki sayidan tahmin ('?')."""
    rec = kaynak.get(pid)
    if rec:
        k = rec.get("kaynak")
        link = rec.get("link", "") or ""
        if k == "Thingiverse":
            m = re.search(r"thing:(\d+)", link)
            return ("Thingiverse", m.group(1) if m else None, rec)
        if k == "Printables":
            m = re.search(r"/model/(\d+)", link)
            return ("Printables", m.group(1) if m else None, rec)
        if k == "CGTrader":
            return ("CGTrader", rec.get("itemid"), rec)
        return (k, None, rec)
    m = re.search(r"-(\d+)$", pid)
    return ("?", m.group(1) if m else None, None)


def gkey_for(platform, sid):
    """Anahtar turetme TEK KAYNAK'ta (tools/r2_anahtar.py). Bilinmeyen platform -> "x" oneki;
    yedek=False -> normalizasyon bosa duserse ham degere DONMEZ (eski davranis birebir)."""
    return r2k.gkey(platform, sid, yedek=False)


# ----------------------------------------------------------------------------- gorsel getir
def _sips_jpeg(blob, out_jpg):
    raw = tempfile.NamedTemporaryFile(delete=False, suffix=".raw")
    raw.write(blob); raw.close()
    subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1400", "-s", "formatOptions", "85",
                    raw.name, "--out", out_jpg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.unlink(raw.name)
    return os.path.exists(out_jpg) and os.path.getsize(out_jpg) > 3000


def fetch_printables(sid, outdir):
    d = pr.detail(sid)
    if not d:
        return []
    paths = []
    for im in sorted(d.get("images") or [], key=lambda x: x.get("order") or 0):
        if len(paths) >= N_IMG:
            break
        try:
            blob = pr.http_get(pr.img_url(im["filePath"]))
        except Exception:
            continue
        jpg = os.path.join(outdir, "g%d.jpg" % (len(paths) + 1))
        if _sips_jpeg(blob, jpg):
            paths.append(jpg)
    return paths


def fetch_thingiverse(sid, outdir):
    try:
        got = th.images(sid)   # th.IMGROOT/<sid>/gN.jpg yazar, tam yollar doner
    except Exception:
        return []
    return (got or [])[:N_IMG]


def fetch_cgt(rec, itemid, outdir):
    try:
        v = cgt.urun_verisi(rec.get("link"))
        if not v or not v.get("galeri"):
            return []
        d, imgs = cgt.indir_gorseller(itemid, v["galeri"], n=N_IMG)
        return imgs[:N_IMG]
    except Exception:
        return []


def fetch_any(platform, sid, rec, outdir):
    """Bilinen platform icin getir; '?' ise Printables sonra Thingiverse dene.
    (platform_kullanilan, paths) doner."""
    if platform == "Printables":
        return "Printables", fetch_printables(sid, outdir)
    if platform == "Thingiverse":
        return "Thingiverse", fetch_thingiverse(sid, outdir)
    if platform == "CGTrader":
        return "CGTrader", fetch_cgt(rec, sid, outdir)
    if platform == "?" and sid:
        p = fetch_printables(sid, outdir)
        if p:
            return "Printables", p
        t = fetch_thingiverse(sid, outdir)
        if t:
            return "Thingiverse", t
    return platform, []


# ----------------------------------------------------------------------------- yukle
def upload(paths, gkey):
    urls = []
    for i, p in enumerate(paths, 1):
        small = os.path.join(tempfile.gettempdir(), "onar_up_%s_%d.jpg" % (gkey, i))
        subprocess.run(["sips", "-Z", "1000", "-s", "formatOptions", "80", p, "--out", small],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        r = subprocess.run([PY, os.path.join(TOOLS, "r2-upload.py"), small, r2k.gorsel_yolu(gkey, i)],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.strip().startswith("https://"):
                urls.append(line.strip())
                break
    return urls


# ----------------------------------------------------------------------------- fazlar
def faz_plan():
    kaynak = json.load(open(KAYNAK))
    ids = cakisan_urunler()
    print("Cakisan urun:", len(ids))
    say = collections.Counter()
    cozulemez = []
    for pid in ids:
        platform, sid, rec = resolve(pid, kaynak)
        ok = bool(sid) and platform in ("Printables", "Thingiverse", "CGTrader", "?")
        say[platform] += 1
        gk = gkey_for(platform, sid) if sid else "-"
        if not ok:
            cozulemez.append(pid)
        print("  %-52s %-11s sid=%-10s -> %s" % (pid[:52], platform, sid, gk))
    print("\nPlatform dagilimi:", dict(say))
    if cozulemez:
        print("COZULEMEYEN (%d):" % len(cozulemez), cozulemez)
    else:
        print("Tumu cozulebilir (best-effort '?' dahil).")


def _getir_one(pid, kaynak):
    platform, sid, rec = resolve(pid, kaynak)
    if not sid:
        return pid, {"durum": "COZULEMEDI", "platform": platform}
    outdir = os.path.join(tempfile.gettempdir(), "onar_" + re.sub(r"[^a-z0-9]+", "_", pid.lower()))
    os.makedirs(outdir, exist_ok=True)
    used, paths = fetch_any(platform, sid, rec, outdir)
    if not paths:
        return pid, {"durum": "GORSEL_YOK", "platform": platform, "sid": sid}
    gk = gkey_for(used, sid)
    urls = upload(paths, gk)
    if not urls:
        return pid, {"durum": "YUKLENEMEDI", "platform": used, "sid": sid, "gkey": gk}
    return pid, {"durum": "OK", "platform": used, "sid": sid, "gkey": gk, "gorseller": urls}


def faz_getir(workers):
    kaynak = json.load(open(KAYNAK))
    ids = cakisan_urunler()
    state = {}
    if os.path.exists(STATE):
        try:
            state = json.load(open(STATE))
        except Exception:
            state = {}
    kalan = [p for p in ids if state.get(p, {}).get("durum") != "OK"]
    print("Cakisan: %d | zaten OK: %d | islenecek: %d | worker: %d"
          % (len(ids), len(ids) - len(kalan), len(kalan), workers))
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_getir_one, p, kaynak): p for p in kalan}
        for f in concurrent.futures.as_completed(futs):
            pid, res = f.result()
            state[pid] = res
            done += 1
            json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)  # her adimda kaydet (resume)
            print("  (%d/%d) %-9s %-52s g:%s"
                  % (done, len(kalan), res["durum"], pid[:52], len(res.get("gorseller", []))), flush=True)
    ok = sum(1 for v in state.values() if v.get("durum") == "OK")
    kotu = {p: v for p, v in state.items() if v.get("durum") != "OK" and p in ids}
    print("\nOK: %d / %d" % (ok, len(ids)))
    if kotu:
        print("BASARISIZ (%d) — elle bakilmali:" % len(kotu))
        for p, v in sorted(kotu.items()):
            print("  %-52s %s" % (p[:52], v))


def _git(*a):
    return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True)


def faz_uygula(chunk):
    if not os.path.exists(STATE):
        sys.exit("Once --getir calistir (%s yok)." % STATE)
    state = json.load(open(STATE))
    ids = cakisan_urunler()   # HALEN cakisan olanlar (guard revert etmis olabilir)
    yapilacak = [(p, state[p]["gorseller"]) for p in ids
                 if state.get(p, {}).get("durum") == "OK" and state[p].get("gorseller")]
    print("Uygulanacak (halen cakisan + getirilmis): %d" % len(yapilacak))
    if not yapilacak:
        print("Uygulanacak yok."); return
    n = 0
    for i in range(0, len(yapilacak), chunk):
        grup = yapilacak[i:i + chunk]
        for pid, urls in grup:
            r = subprocess.run([PY, os.path.join(TOOLS, "duzelt.py"), pid,
                                "--alan", "gorseller", "--deger", json.dumps(urls, ensure_ascii=False)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print("  ! duzelt HATA %s: %s" % (pid, (r.stderr or r.stdout).strip()[:160]))
            else:
                n += 1
        # chunk'i hemen commit et (manifest penceresi kisa). Atomik yol-sinirli commit:
        # `git commit -- urunler.json` = ayri `git add`+commit yerine (baska oturumun toplu
        # commit'i stage'i supurme yarisini onler; guard pre-commit yine calisir).
        msg = "Gorsel cakismasi onarimi: %d urune benzersiz kaynak-id anahtari (parti %d)" % (len(grup), i // chunk + 1)
        c = _git("commit", "-m", msg, "--", "urunler.json")
        print("  commit parti %d: %s" % (i // chunk + 1, (c.stdout or c.stderr).strip().splitlines()[0] if (c.stdout or c.stderr).strip() else "?"))
    print("\nduzelt uygulanan: %d" % n)
    # re-tespit
    kalan = cakisan_urunler()
    print("Onarim sonrasi HALEN cakisan urun: %d" % len(kalan))
    if kalan:
        print("  ", kalan[:40])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--getir", action="store_true")
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=CHUNK)
    args = ap.parse_args()
    if args.plan:
        faz_plan()
    elif args.getir:
        faz_getir(args.workers)
    elif args.uygula:
        faz_uygula(args.chunk)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
