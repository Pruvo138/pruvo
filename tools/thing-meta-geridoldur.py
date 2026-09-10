#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""thing-meta-geridoldur.py — `.thing-cache/<id>/meta.json` GERI DOLDURMA kolu (K400).

NEDEN VAR (10 Eyl 2026, OLCULDU — rapor edilen teshis CURUDU, dogrusu bu):
Ilk teshis "thing-hazirla.py'deki `except Exception: pass` 365 dizinde meta.json'u
sessizce yuttu" diyordu. Onbellek ONEK'e gore ayrildiginda iddia YIKILDI:

    ONEK          DIZIN   META  gN.jpg   uretici
    (saf-sayi)        3      3       3   tools/thing-hazirla.py   <- 3/3 TAM
    th              146      0     137   BU DEPODA URETICI YOK
    pr              113      0       0   tools/printables-ekle.py (goruntu adimi hic kosmamis)
    mw               63      0       0   tools/makerworld-ekle.py (ayni)
    cgt              43      0       0   tools/cgt-ekle.py        (ayni)

thing-hazirla.py'nin EVRENI saf-sayisal id'dir ve orada bosluk YOKTUR; yutma kolu
gozlenen veride HIC atesLENMEMIStir. Bosluk BASKA ureticilerin duzlemindedir
(yanlis evrende olculen bulgu -> sahte KIRMIZI).

BU KOL NE YAPAR: yalnizca ONBELLEKTE ZATEN DURAN gercek veriden turetir.
  * `detail.json` Thingiverse semasindaysa (name + license + creator{}) -> haritalanir.
  * pr/mw/cgt semalari HARITALANMAZ: alanlari farklidir ve o ailelerde gorsel de YOK
    (0/219). Uydurma meta.json yazmak, icerik bacagini BOS galeri uzerinde kosturur.
    Onlar KENDI ureticilerinin isidir -> ADIYLA ATLANIR, sessiz gecilmez.

IKI SERT KURAL:
  1. VAR OLANI EZMEZ. meta.json duruyorsa dokunulmaz (idempotent; tekrar kosmak no-op).
  2. VARSAYILAN KURU KOSUM. Diske ancak `--yaz` ile dokunur.

Kullanim:
    python3 tools/thing-meta-geridoldur.py            # kuru kosum (rapor)
    python3 tools/thing-meta-geridoldur.py --yaz      # gercekten yaz
    python3 tools/thing-meta-geridoldur.py --kok /yol # baska bir onbellek koku (test)
"""
import importlib.util, json, os, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))


def _yukle(dosya, ad):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(TOOLS, dosya))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_vk = _yukle("veri_kok.py", "veri_kok_geridoldur")
_KOD_KOK, ROOT, _KOK_UYARI = _vk.cozumle(__file__)
if _KOK_UYARI:
    sys.stderr.write(_KOK_UYARI)
bi = _yukle("baski_ipucu.py", "baski_ipucu_geridoldur")

VARSAYILAN_KOK = os.path.join(ROOT, ".thing-cache")

# Durum etiketleri — TEK KAYNAK (test bunlara capalanir; serbest metin YASAK).
YAZILDI = "YAZILDI"
KURU = "KURU-KOSUM"
ATLA_VAR = "ATLA: meta.json ZATEN VAR"
ATLA_DETAY_YOK = "ATLA: detail.json yok"
ATLA_DETAY_BOZUK = "ATLA: detail.json BOZUK"
ATLA_SEMA = "ATLA: sema haritalanamaz (ureticisinin isi)"
HATA_YAZ = "HATA: yazilamadi"


def thingiverse_semasi(d):
    """detail.json Thingiverse semasi MI? (pr `user`, cgt `tasarimci`, mw `title` tasir)"""
    return (isinstance(d, dict) and "name" in d and "license" in d
            and isinstance(d.get("creator"), dict))


def _galeri(ic):
    g = [f for f in ic if f.startswith("g") and f.endswith(".jpg")]
    return sorted(g, key=lambda f: (len(f), f))


def meta_turet(d, ic):
    """detail.json + dizin icerigi -> thing-hazirla.py ile AYNI meta sozlesmesi.

    olcu_mm UYDURULMAZ: bbox yalniz STL baytindan cikar, onbellekte STL yoksa None kalir
    (thing-hazirla da STL yokken None yazar). stl_adet = YEREL .stl sayisi — API sayisi
    DEGIL; onbellekte olmayani saymak sahte "STL var" hukmu uretirdi.
    """
    return {
        "id": d.get("id"),
        "baslik": (d.get("name") or "").replace("\n", " "),
        "tasarimci": (d.get("creator") or {}).get("name", "?"),
        "lisans": d.get("license", "?"),
        "olcu_mm": None,
        "stl_adet": len([f for f in ic if f.lower().endswith(".stl")]),
        "gorseller": _galeri(ic),
        "baski": bi.baski_ipucu(d.get("description")),
    }


def geri_doldur(kok, yaz=False):
    """Doner: [(id, durum, ayrinti)]. Yan etki YALNIZ yaz=True iken."""
    rapor = []
    if not os.path.isdir(kok):
        return rapor
    for tid in sorted(os.listdir(kok)):
        p = os.path.join(kok, tid)
        if not os.path.isdir(p):
            continue
        ic = os.listdir(p)
        mp = os.path.join(p, "meta.json")
        # 🔴 IDEMPOTENS KAPISI — var olani EZME. Bu kol kaldirilirsa geri doldurma
        # thing-hazirla'nin (olculmus, saglam) ciktisini uzerine yazar.
        if os.path.exists(mp):
            rapor.append((tid, ATLA_VAR, "")); continue
        dp = os.path.join(p, "detail.json")
        if not os.path.exists(dp):
            rapor.append((tid, ATLA_DETAY_YOK, "")); continue
        try:
            with open(dp, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            rapor.append((tid, ATLA_DETAY_BOZUK, "%s: %s" % (type(e).__name__, e))); continue
        if not thingiverse_semasi(d):
            rapor.append((tid, ATLA_SEMA, "anahtarlar=%s" % ",".join(sorted(d)[:4]
                                                                    if isinstance(d, dict) else []))); continue
        meta = meta_turet(d, ic)
        ayrinti = "gorsel=%d stl=%d" % (len(meta["gorseller"]), meta["stl_adet"])
        if not yaz:
            rapor.append((tid, KURU, ayrinti)); continue
        try:
            tmp = mp + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
            os.replace(tmp, mp)
            rapor.append((tid, YAZILDI, ayrinti))
        except Exception as e:
            # thing-hazirla ile AYNI hukum: yazim dusuşu SESSIZ GECILMEZ.
            rapor.append((tid, HATA_YAZ, "%s: %s" % (type(e).__name__, e)))
    return rapor


def main(argv):
    yaz = "--yaz" in argv
    kok = VARSAYILAN_KOK
    if "--kok" in argv:
        kok = argv[argv.index("--kok") + 1]
    rapor = geri_doldur(kok, yaz=yaz)
    sayac = {}
    for tid, durum, ayrinti in rapor:
        sayac[durum] = sayac.get(durum, 0) + 1
    print("KOK: %s   (%s)" % (kok, "YAZIM ACIK" if yaz else "KURU KOSUM — diske dokunulmadi"))
    for durum in sorted(sayac):
        print("  %-40s %d" % (durum, sayac[durum]))
    hata = sayac.get(HATA_YAZ, 0)
    if hata:
        sys.stderr.write("HAL=GERIDOLDURMA-YAZILAMADI adet=%d\n" % hata)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
