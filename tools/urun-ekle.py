#!/usr/bin/env python3
"""PRUVO toplu urun ekleme ORKESTRATORU (Thingiverse).

Amac: taze oturumda tek komutla, disiplin KODDA (modelin kafasinda degil) — 3-4 gorsel,
STL olcusu, dogru kayit yerleri, "3D baski" demeyen aciklama HER SEFERINDE garanti.

Kullanim:  python3 tools/urun-ekle.py <thing_id> [<thing_id> ...]

Her id icin sirayla:
  1) thing-hazirla.py  -> gorseller + meta.json + STL olcusu (stl/ + Drive'a kaydeder)
  2) NC/Non-Commercial lisans -> ATLA + bildir (satamayiz)
  3) thing-gemini.py   -> oneri.json (gorsel secimi + Turkce baslik/aciklama/kategori/marka/fiyat_oneri)
  4) secili gorselleri kucult + R2'ye yukle
  5) urun objesini + kaynak kaydini STAGE et (urunler.json + .urun-kaynaklari.json'a YAZAR)

COMMIT ETMEZ. Sonda gozden gecirme tablosu basar. Sen:
  - oneri.json'lari suz (kategori/fiyat/gorsel mantikli mi), fiyatlari kesinlestir,
  - sonra: yedekle + git add urunler.json + commit + push  (rehber adim i/j).

Sifir soru sorar; belirsizde makul varsayimla devam eder. Sir icermez.
"""
import json, os, re, subprocess, sys, tempfile

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
IMGROOT = os.path.join(ROOT, ".thing-cache")
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
PY = sys.executable or "python3"

# Thingiverse lisans metni -> (satilabilir mi, urunler.json 'tur' etiketi)
def lisans_map(lic):
    l = (lic or "").lower()
    if "noncommercial" in l or "non-commercial" in l or "non commercial" in l:
        return False, None
    if "public domain" in l or "cc0" in l:
        return True, None           # CC0 -> lisans alani KONMAZ (nota yazilir)
    if "creative commons" in l or l.startswith("cc "):
        if "share alike" in l or "sharealike" in l:
            tur = "CC BY-SA 4.0"
        elif "no deriv" in l:
            tur = "CC BY-ND 4.0"
        else:
            tur = "CC BY 4.0"
        return True, tur
    if "gnu" in l or "gpl" in l or "bsd" in l:
        return True, None
    # bilinmeyen -> temkinli: satilabilir say ama lisans alani koyma, notta ham metni birak
    return True, None


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def sips_upload(local_jpg, key):
    small = os.path.join(tempfile.gettempdir(), "up_" + os.path.basename(key))
    subprocess.run(["sips", "-Z", "1000", "-s", "formatOptions", "80", local_jpg, "--out", small],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = run([PY, os.path.join(TOOLS, "r2-upload.py"), small, key])
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("https://"):
            return line
    return None


def stage_one(tid, urunler, kaynak):
    # 1) hazirla (gorsel + meta.json + STL)
    r = run([PY, os.path.join(TOOLS, "thing-hazirla.py"), tid])
    metap = os.path.join(IMGROOT, tid, "meta.json")
    if not os.path.exists(metap):
        return {"id": tid, "durum": "HATA: hazirla meta.json uretmedi", "detay": r.stdout[-300:]}
    meta = json.load(open(metap))

    # 2) lisans
    satilir, cc_tur = lisans_map(meta.get("lisans"))
    if not satilir:
        return {"id": tid, "durum": "ATLA: NC/Non-Commercial lisans (satilamaz)", "lisans": meta.get("lisans")}

    # 3) gemini onerisi
    rg = run([PY, os.path.join(TOOLS, "thing-gemini.py"), tid])
    onerip = os.path.join(IMGROOT, tid, "oneri.json")
    if not os.path.exists(onerip):
        return {"id": tid, "durum": "HATA: gemini oneri uretmedi", "detay": rg.stdout[-300:]}
    o = json.load(open(onerip))

    # benzersiz kebab id: gemini basligindan turet, cakisirsa -tid ekle
    base = re.sub(r"[^a-z0-9]+", "-", (o.get("baslik") or tid).lower()).strip("-")[:60] or tid
    uid = base
    mevcut = {p["id"] for p in urunler}
    if uid in mevcut or uid in [s["_id"] for s in kaynak.get("_stage", [])]:
        uid = base + "-" + tid

    # 4) secili gorselleri yukle (taban: en az 1; gemini genelde 2-4 verir)
    secili = o.get("sec_gorseller") or []
    d = os.path.join(IMGROOT, tid)
    if not secili:  # gemini bos birakti -> mevcut tum g*.jpg'yi al
        secili = sorted(f for f in os.listdir(d) if f.startswith("g") and f.endswith(".jpg"))
    urls = []
    for i, fn in enumerate(secili, 1):
        fp = os.path.join(d, fn)
        if not os.path.exists(fp):
            continue
        url = sips_upload(fp, "urunler/%s-%d.jpg" % (uid, i))
        if url:
            urls.append(url)
    if not urls:
        return {"id": tid, "durum": "HATA: gorsel yuklenemedi"}

    # 5) urun objesi
    urun = {
        "id": uid,
        "kategori": o.get("kategori", "Tamirat"),
        "marka": o.get("marka", []),
        "baslik": o.get("baslik", tid),
        "aciklama": o.get("aciklama", ""),
        "fiyat": o.get("fiyat_oneri", ""),   # GEMINI ONERISI — gozden gecirmede kesinlestir
        "gorseller": urls,
    }
    if cc_tur:
        urun["lisans"] = {"tasarimci": meta.get("tasarimci", "?"), "tur": cc_tur}

    kaynak["_stage"].append({
        "_id": uid,
        "kaynak": "Thingiverse",
        "link": "https://www.thingiverse.com/thing:" + tid,
        "lisans": meta.get("lisans", ""),
        "tasarimci": meta.get("tasarimci", "?"),
        "tur": "ucretsiz-cc" if cc_tur else "diger",
        "not": "en buyuk parca %s mm; %d STL" % (meta.get("olcu_mm"), meta.get("stl_adet", 0)),
        "baski": "",
    })
    return {"id": tid, "durum": "STAGED", "uid": uid, "kategori": urun["kategori"],
            "marka": urun["marka"], "gorsel": len(urls), "fiyat_oneri": urun["fiyat"],
            "baslik": urun["baslik"], "_urun": urun}


def main(ids):
    urunler = json.load(open(URUNLER))
    kaynak = json.load(open(KAYNAK)); kaynak["_stage"] = []
    sonuc = []
    for tid in ids:
        print("### islenen:", tid, flush=True)
        sonuc.append(stage_one(tid, urunler, kaynak))

    # STAGE'leri yaz (en yeni en ustte: ters sirada basa ekle -> girdideki sira korunur)
    yeni = [s["_urun"] for s in sonuc if s.get("durum") == "STAGED"]
    for u in reversed(yeni):
        urunler.insert(0, u)
    json.dump(urunler, open(URUNLER, "w"), ensure_ascii=False, indent=2)
    for s in kaynak.pop("_stage"):
        sid = s.pop("_id"); kaynak[sid] = s
    json.dump(kaynak, open(KAYNAK, "w"), ensure_ascii=False, indent=1)

    # GOZDEN GECIRME TABLOSU
    print("\n" + "=" * 70)
    print("STAGED (commit ETMEDIM — gozden gecir, fiyatlari kesinlestir):")
    for s in sonuc:
        if s.get("durum") == "STAGED":
            print("  ✔ %-42s | %-11s | g:%d | %s | marka:%s"
                  % (s["uid"], s["kategori"], s["gorsel"], s["fiyat_oneri"], s["marka"]))
            print("      baslik:", s["baslik"])
            print("      oneri :", os.path.join(IMGROOT, s["id"], "oneri.json"))
        else:
            print("  ✘ %s -> %s %s" % (s["id"], s["durum"], s.get("lisans", "")))
    n = len(yeni)
    print("-" * 70)
    print("%d urun STAGE edildi, urunler.json toplam %d." % (n, len(urunler)))
    print("SONRAKI: oneri.json'lari suz -> fiyat/kategori/gorsel duzelt -> yedekle + commit + push.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanim: python3 tools/urun-ekle.py <thing_id> [<thing_id> ...]")
    main(sys.argv[1:])
