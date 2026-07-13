#!/usr/bin/env python3
"""Printables model metadata (ad/lisans/tasarimci/aciklama/gorseller) — thing-meta.py esdegeri.

Kullanim:  python3 tools/printables-meta.py <id> [<id> ...]
   ID = printables.com/model/<ID>-<slug> icindeki sayi.

Cikti her model icin: ad, lisans (satilabilir mi), tasarimci, ozet+aciklama, gorsel URL'leri
(media.printables.com tam yol), STL adlari/boyutlari (indirme public DEGIL — bilgi amacli).
Token GEREKMEZ.
"""
import importlib.util, os, sys

ROOT = "/Users/okan/dev/pruvo"
_spec = importlib.util.spec_from_file_location("pr_api", os.path.join(ROOT, "tools", "printables-api.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


def show(pid):
    print("=== %s ===" % pid)
    try:
        d = pr.detail(pid)
    except Exception as e:
        print("HATA:", e); return
    if not d:
        print("BULUNAMADI"); return
    lic = d.get("license") or {}
    abbr = lic.get("abbreviation") or ""
    print(d.get("name"))
    print("URL:", pr.model_url(pid, d.get("slug")))
    print("LISANS:", abbr, "(%s)" % lic.get("name"),
          "-> SATILABILIR" if pr.satilabilir(abbr) else "-> !! SATILAMAZ (NC) — ATLA")
    print("BY:", (d.get("user") or {}).get("publicUsername"))
    print("dosya:", d.get("filesCount"), "gorsel:", d.get("imagesCount"),
          "indirme:", d.get("downloadCount"), "begeni:", d.get("likesCount"))
    if d.get("thingiverseLink"):
        print("thingiverse:", d["thingiverseLink"])
    print("--- ozet/aciklama ---")
    print((d.get("summary") or "").strip())
    desc = pr.strip_html(d.get("description") or "")
    if desc:
        print(desc[:1200])
    print("--- gorseller (%d) ---" % len(d.get("images") or []))
    for im in sorted(d.get("images") or [], key=lambda x: x.get("order") or 0):
        print("  ", pr.img_url(im["filePath"]))
    stls = d.get("stls") or []
    if stls:
        print("--- STL (%d, indirme public DEGIL) ---" % len(stls))
        for s in stls[:20]:
            print("   %-40s %d KB" % (s.get("name"), (s.get("fileSize") or 0) // 1024))
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanim: python3 tools/printables-meta.py <id> [<id> ...]")
    for pid in sys.argv[1:]:
        show(pid)
