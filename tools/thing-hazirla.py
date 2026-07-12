#!/usr/bin/env python3
"""Ürün ekleme HAZIRLIK aracı (Thingiverse).

Kullanim:  python3 tools/thing-hazirla.py <thing_id> [<thing_id> ...]

Her thing icin:
  - Metadata (baslik / tasarimci / LISANS) yazar  -> lisansi NC/ND ise SATMA.
  - TUM galeri gorsellerini indirir, jpeg'e cevirir, `.thing-cache/<id>/gN.jpg` olarak kaydeder,
    yerel yollari yazar  -> sen bunlari `Read` ile GOZLE INceleyip 3-4 iyi gorsel sec
    (gercek/montaj foto tercih; logo/filigran/CAD-UI/duplike ele; ASLA tek gorselle birakma).
  - TUM STL'leri indirir, `stl/` VE Drive STL klasorune kaydeder, sinir kutusu OLCUSUNU hesaplar
    -> en buyuk parcanin olcusunu urun aciklamasina "Yaklasik dis olculer: A x B x C mm" yaz.

Sir icermez: token `.thingiverse-token`'dan, Drive yolu `.stl-backup-dir`'den okunur.
Ayrinti: tools/URUN-EKLEME-REHBERI.md
"""
import json, os, re, struct, subprocess, sys, tempfile, urllib.parse, urllib.request

ROOT = "/Users/okan/dev/pruvo"
TOKEN = open(os.path.join(ROOT, ".thingiverse-token")).read().strip()
STLDIR = os.path.join(ROOT, "stl"); os.makedirs(STLDIR, exist_ok=True)
IMGROOT = os.path.join(ROOT, ".thing-cache"); os.makedirs(IMGROOT, exist_ok=True)
_bd = os.path.join(ROOT, ".stl-backup-dir")
DRIVE = open(_bd).read().strip() if os.path.exists(_bd) else None
if DRIVE:
    try: os.makedirs(DRIVE, exist_ok=True)
    except Exception: DRIVE = None


def api(url):
    r = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN,
                                             "User-Agent": "pruvo/1.0"})
    return urllib.request.urlopen(r).read()


def curl(url, out, bearer=False):
    cmd = ["curl", "-sSL", "-A", "Mozilla/5.0"]
    if bearer:
        cmd += ["-H", "Authorization: Bearer " + TOKEN]
    cmd += [url, "-o", out]
    subprocess.run(cmd, check=False)


def bbox(data):
    xs = []; ys = []; zs = []
    if b"vertex" in data[:2000] or data[:5].lower() == b"solid":
        for line in data.decode("utf-8", "ignore").splitlines():
            p = line.strip().split()
            if len(p) == 4 and p[0] == "vertex":
                try: xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
                except ValueError: pass
    if not xs and len(data) > 84:
        n = struct.unpack("<I", data[80:84])[0]; off = 84
        for _ in range(n):
            if off + 48 > len(data): break
            v = struct.unpack("<12f", data[off:off + 48]); off += 50
            for j in range(3, 12, 3): xs.append(v[j]); ys.append(v[j + 1]); zs.append(v[j + 2])
    if not xs: return None
    d = sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True)
    if d[0] < 2.0: d = [x * 1000 for x in d]   # metre -> mm
    return d


def safe(name):
    return name.replace(" ", "_").replace("/", "_")


def images(tid):
    outdir = os.path.join(IMGROOT, tid); os.makedirs(outdir, exist_ok=True)
    try: imgs = json.loads(api("https://api.thingiverse.com/things/%s/images" % tid))
    except Exception as e:
        print("   gorsel HATA:", e); return []
    saved = []
    for im in imgs:
        if len(saved) >= 8: break
        url = None
        for s in im.get("sizes", []):
            if s.get("type") == "display" and s.get("size") in ("large", "featured"):
                url = s.get("url")
        if not url and im.get("sizes"):
            url = im["sizes"][-1].get("url")
        if not url: continue
        raw = os.path.join(tempfile.gettempdir(), "th_%s_%d.raw" % (tid, len(saved) + 1))
        curl(urllib.parse.quote(url, safe=":/?=&%"), raw)
        if not os.path.exists(raw) or os.path.getsize(raw) < 5000:
            continue
        jpg = os.path.join(outdir, "g%d.jpg" % (len(saved) + 1))
        subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1400", "-s", "formatOptions", "85",
                        raw, "--out", jpg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(jpg):
            saved.append(jpg)
    return saved


def stls(tid, uidhint):
    try: files = json.loads(api("https://api.thingiverse.com/things/%s/files" % tid))
    except Exception as e:
        print("   STL HATA:", e); return None, 0
    biggest = None; bigdim = None; cnt = 0
    for f in files:
        n = f["name"]
        if not n.lower().endswith(".stl"): continue
        nm = "%s--%s" % (uidhint, safe(n))
        tmp = os.path.join(tempfile.gettempdir(), nm)
        curl(f["download_url"], tmp, bearer=True)
        if not os.path.exists(tmp): continue
        data = open(tmp, "rb").read()
        if data[:15].lower().startswith(b"<?xml") or b"AccessDenied" in data[:200]:
            continue
        open(os.path.join(STLDIR, nm), "wb").write(data)
        if DRIVE:
            try: open(os.path.join(DRIVE, nm), "wb").write(data)
            except Exception: pass
        d = bbox(data); cnt += 1
        ds = ("%.0f x %.0f x %.0f mm" % (d[0], d[1], d[2])) if d else "olcusuz"
        print("   STL:", n, "->", ds)
        if d and (biggest is None or d[0] > biggest):   # en buyuk BOYUTLU parca
            biggest = d[0]; bigdim = d
    return bigdim, cnt


def main(ids):
    for tid in ids:
        try: t = json.loads(api("https://api.thingiverse.com/things/%s" % tid))
        except Exception as e:
            print("=== %s === HATA: %s" % (tid, e)); continue
        name = t.get("name", "").replace("\n", " ")
        des = (t.get("creator") or {}).get("name", "?")
        lic = t.get("license", "?")
        print("=== thing:%s ===" % tid)
        print("   BASLIK  :", name)
        print("   TASARIMCI:", des)
        print("   LISANS  :", lic, "  <- NC / Non-Commercial ise SATMA, ATLA+bildir")
        imgs = images(tid)
        print("   GORSEL  :", len(imgs), "adet ->", os.path.join(IMGROOT, tid))
        for p in imgs:
            print("      Read:", p)
        dim, cnt = stls(tid, tid)
        if dim:
            print("   OLCU    : %.0f x %.0f x %.0f mm  (en buyuk parca; toplam %d STL)" % (dim[0], dim[1], dim[2], cnt))
        else:
            print("   OLCU    : STL yok / olculemedi -> aciklamada olcu satirini yazma")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanim: python3 tools/thing-hazirla.py <thing_id> [<thing_id> ...]"); sys.exit(1)
    main(sys.argv[1:])
