#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/kapali-aile-fiyat-kapisi.py — SATIS KAPISI KAPALI ailede SAHTE FIYAT BEYANI nobetcisi.

NEDEN VAR (olculmus canli kusur, 2026-08-04):
  secenekler.js `parametrikFiyatKurus` hacmi DOGRULANMAMIS ailede **null** dondurur
  (fail-closed, dogru) ve Worker sepeti 400 `hacim-dogrulanmamis` ile reddeder —
  yani o urun BUGUN SATILAMAZ. Buna ragmen uretilen urun sayfasi:
    * JS ONCESI / JS'siz / crawler HTML'inde `<div class="opsiyon-fiyat">200,00 TL'den
      baslayan</div>` basiyordu,
    * JSON-LD'de `{"price":"200","availability":"…/InStock"}` beyan ediyordu.
  Yani musteriye ve arama motoruna OLMAYAN bir tutar + ALINABILIR bir stok
  bildiriliyordu. Duzeltme tools/build.py'de; bu dosya duzeltmenin GERI GELMESINI
  (regresyonu) olcer.

NE OLCER (uretilen sayfalarin KENDISINI okur — kaynak koda "bakip yorum yapmaz"):
  A. TEK KAYNAK PARITESI — "aile satisa acik mi" sorusunun cevabi build.py'nin metin
     okuyucusundan ve secenekler.js'in GERCEK node kosumundan AYNI cikmali. Ayrisirsa
     kirmizi ([[ikiz-tanim-sessiz-ayrisma]]). Regex ile "sanki kosmus gibi" yapilmaz
     ([[mimar-kapi-parser-taklidi]]): node yoksa kapi OLCEMEDI der ve KIRMIZI yanar.
  B. KAPALI aile sayfasi (her biri 4 iddia):
       1. sayfada sayisal "…,… TL" fiyat beyani YOK
       2. JSON-LD'de price/lowPrice YOK
       3. JSON-LD'de availability InStock YOK
       4. fiyat alaninda ACIKLAYICI metin VAR (secenekler.js'in `kurus == null` dali)
  C. ACIK aile sayfasi (her biri 2 iddia — POZITIF nobetci, kapi asiri hevesli OLAMAZ):
       1. fiyat alaninda sayisal "…,… TL" beyani VAR
       2. JSON-LD'de sayisal price VAR
  D. YUZEY GUVENCESI: semali her parametrik urunun sayfasi uretilmis olmali ve
     pozitif eksende EN AZ 3 acik aile olculmus olmali (yoksa kapi bosa kosuyordur).

SAYI GOMULMEZ: kapali/acik kumesi secenekler.js + jenerator/urunler/*.json
hacimFormulu'sundan TURETILIR. Aile listesi degisince kapi kendini gunceller.

Kullanim (once python3 tools/build.py ile urun/ uretilmis olmali):
  python3 tools/kapali-aile-fiyat-kapisi.py
  python3 tools/kapali-aile-fiyat-kapisi.py --mutasyon   # 3 mutant, IZOLE KOPYADA
Cikis kodu: 0 = YESIL, 1 = KIRMIZI/OLCULEMEDI.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# "1.234,50 TL" bicimli SAYISAL fiyat beyani (secenekler.js kurusMetni'nin cikti bicimi).
TL_BEYAN_RE = re.compile(r"\d[\d.]*,\d\d\s*TL")
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
OPSIYON_FIYAT_RE = re.compile(
    r'<div class="opsiyon-fiyat" id="opsiyonFiyat">(.*?)</div>', re.S)
# JSON-LD price/lowPrice degeri sayisal mi (test-jsonld-offers.py ile AYNI kural)
PRICE_RE = re.compile(r"^\d+(?:\.\d+)?$")

NODE_PROBU = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const KOK = process.argv[2];
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), sandbox);
const S = sandbox.window.PRUVO_SECENEK;
if (!S) { console.error("PRUVO_SECENEK yuklenemedi"); process.exit(2); }
console.log(JSON.stringify({ acik: Object.keys(S.HACIM_DOGRULANMIS_AILELER || {}) }));
"""


def _node_acik_aileler(kok):
    """secenekler.js'i GERCEKTEN kosturur; (kume, hata) doner."""
    if shutil.which("node") is None:
        return None, "node yok -> tek kaynak GERCEKTEN kosturulamadi (fail-closed)"
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(NODE_PROBU)
        prob = f.name
    try:
        s = subprocess.run(["node", prob, kok], capture_output=True, text=True)
        if s.returncode != 0:
            return None, "node probu rc=%d: %s" % (s.returncode, (s.stderr or "").strip()[:200])
        return set(json.loads(s.stdout)["acik"]), None
    except Exception as e:                                  # noqa: BLE001
        return None, "node probu cozumlenemedi: %s" % e
    finally:
        os.unlink(prob)


def _build_acik_aileler(kok):
    """build.py'nin KENDI okuyucusunu cagirir (ikinci kopya yazilmaz)."""
    tools = os.path.join(kok, "tools")
    onceki = list(sys.path)
    sys.path.insert(0, tools)
    for ad in ("build",):
        sys.modules.pop(ad, None)
    try:
        import build  # noqa: PLC0415
        return set(build.HACIM_DOGRULANMIS_AILELER), build.FIYATSIZ_METIN
    finally:
        sys.path[:] = onceki
        sys.modules.pop("build", None)


def _semalar(kok):
    """{pid: hacimFormulu} — parametrik sarı seri semalari."""
    d = {}
    for yol in sorted(glob.glob(os.path.join(kok, "jenerator", "urunler", "*.json"))):
        pid = os.path.splitext(os.path.basename(yol))[0]
        with open(yol, encoding="utf-8") as f:
            d[pid] = (json.load(f) or {}).get("hacimFormulu")
    return d


def _ld_fiyat_isaretleri(html):
    """(sayisal_price_var, instock_var, herhangi_price_anahtari_var)"""
    sayisal = False
    instock = False
    anahtar = False
    for blok in LD_RE.findall(html):
        try:
            veri = json.loads(blok)
        except ValueError:
            continue
        metin = json.dumps(veri, ensure_ascii=False)
        if "schema.org/InStock" in metin:
            instock = True
        yigin = [veri]
        while yigin:
            o = yigin.pop()
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("price", "lowPrice"):
                        anahtar = True
                        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                            sayisal = True
                        elif isinstance(v, str) and PRICE_RE.match(v.strip()) \
                                and float(v.strip()) > 0:
                            sayisal = True
                    yigin.append(v)
            elif isinstance(o, list):
                yigin.extend(o)
    return sayisal, instock, anahtar


def olc(kok):
    """(iddia_sayisi, ihlaller, ozet) doner."""
    iddia = 0
    ihlal = []
    node_acik, node_hata = _node_acik_aileler(kok)
    build_acik, fiyatsiz_metin = _build_acik_aileler(kok)

    # --- A. tek kaynak paritesi
    iddia += 1
    if node_acik is None:
        ihlal.append("A/OLCULEMEDI: %s" % node_hata)
        node_acik = set()
    elif node_acik != build_acik:
        ihlal.append("A: build.py okuyucusu ile secenekler.js kosumu AYRISTI "
                     "(yalniz build: %s | yalniz js: %s)"
                     % (sorted(build_acik - node_acik), sorted(node_acik - build_acik)))
    acik_kume = node_acik or build_acik

    semalar = _semalar(kok)
    kapali_olculen = []
    acik_olculen = []
    for pid in sorted(semalar):
        aile = semalar[pid]
        yol = os.path.join(kok, "urun", pid, "index.html")
        iddia += 1
        if not os.path.exists(yol):
            ihlal.append("D: %s sayfasi uretilmemis (%s)" % (pid, yol))
            continue
        with open(yol, encoding="utf-8") as f:
            html = f.read()
        ops = OPSIYON_FIYAT_RE.search(html)
        ops_metin = ops.group(1).strip() if ops else ""
        sayisal_price, instock, _ = _ld_fiyat_isaretleri(html)
        acik_mi = isinstance(aile, str) and aile in acik_kume

        if not acik_mi:
            kapali_olculen.append(pid)
            iddia += 4
            if TL_BEYAN_RE.search(html):
                ihlal.append("B1: %s (aile=%s) KAPALI ama sayfada sayisal TL beyani var: %s"
                             % (pid, aile, TL_BEYAN_RE.findall(html)[:3]))
            if sayisal_price:
                ihlal.append("B2: %s (aile=%s) KAPALI ama JSON-LD'de sayisal price var"
                             % (pid, aile))
            if instock:
                ihlal.append("B3: %s (aile=%s) KAPALI ama JSON-LD'de InStock beyani var"
                             % (pid, aile))
            if fiyatsiz_metin not in ops_metin:
                ihlal.append("B4: %s (aile=%s) KAPALI ama aciklayici metin YOK "
                             "(fiyat alani: %r)" % (pid, aile, ops_metin[:80]))
        else:
            acik_olculen.append(pid)
            iddia += 2
            if not TL_BEYAN_RE.search(ops_metin):
                ihlal.append("C1: %s (aile=%s) ACIK ama fiyat alaninda sayisal TL beyani "
                             "YOK (%r) — kapi asiri hevesli" % (pid, aile, ops_metin[:80]))
            if not sayisal_price:
                ihlal.append("C2: %s (aile=%s) ACIK ama JSON-LD'de sayisal price YOK "
                             "— kapi asiri hevesli" % (pid, aile))

    # --- D. yuzey guvencesi: pozitif eksen bosa kosmasin
    iddia += 1
    if len(acik_olculen) < 3:
        ihlal.append("D: pozitif eksen bos — yalniz %d acik aile sayfasi olculdu (>=3 sart)"
                     % len(acik_olculen))
    iddia += 1
    if not semalar:
        ihlal.append("D: hic parametrik sema bulunamadi — kapi bosa kosuyor")

    ozet = {"acik_aile": len(acik_kume), "kapali_sayfa": len(kapali_olculen),
            "acik_sayfa": len(acik_olculen), "kapali": kapali_olculen}
    return iddia, ihlal, ozet


# ---------------------------------------------------------------------------
# MUTASYON SURUCUSU — DAIMA IZOLE KOPYADA ([[mutasyon-diske-yazma-tuzagi]]).
# Kanit yeniden uretilebilir olsun diye surucu REPODA durur
# ([[mutasyon-kaniti-yeniden-uretilebilir]]).
# ---------------------------------------------------------------------------
MUTANTLAR = [
    # (ad, beklenen, eski, yeni)
    ("a-duzeltmeyi-oldur (kapali aileye fiyat bas)", "KIRMIZI",
     "aile_satis_kapali = bool(sema) and not (",
     "aile_satis_kapali = False and not ("),
    ("b-asiri-hevesli (acik aileden fiyati kaldir)", "KIRMIZI",
     "aile_satis_kapali = bool(sema) and not (",
     "aile_satis_kapali = bool(sema) or not ("),
    ("c-kontrol (De Morgan, davranis korunur)", "YESIL",
     "aile_satis_kapali = bool(sema) and not (\n        isinstance(_aile, str) "
     "and _aile in HACIM_DOGRULANMIS_AILELER)",
     "aile_satis_kapali = bool(sema) and (\n        (not isinstance(_aile, str)) "
     "or (_aile not in HACIM_DOGRULANMIS_AILELER))"),
]


def _kopyala(hedef):
    def gormezden(dizin, adlar):
        atla = set()
        for ad in adlar:
            if ad in (".git", "urun", ".claude", "node_modules", "__pycache__"):
                atla.add(ad)
        return atla
    shutil.copytree(KOK, hedef, ignore=gormezden, symlinks=True)


def _agac_damgasi(kok):
    h = hashlib.sha256()
    for ad in ("tools/build.py", "secenekler.js", "tools/kapali-aile-fiyat-kapisi.py"):
        with open(os.path.join(kok, ad), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def mutasyon():
    basta = _agac_damgasi(KOK)
    print("canli agac sha256 (basta): %s" % basta)
    sonuc = []
    for ad, beklenen, eski, yeni in MUTANTLAR:
        gecici = tempfile.mkdtemp(prefix="kapali-fiyat-mutant-")
        kopya = os.path.join(gecici, "repo")
        try:
            _kopyala(kopya)
            bp = os.path.join(kopya, "tools", "build.py")
            with open(bp, encoding="utf-8") as f:
                kaynak = f.read()
            if kaynak.count(eski) != 1:
                print("  %-46s MUTASYON UYGULANAMADI (capa %d kez bulundu)"
                      % (ad, kaynak.count(eski)))
                sonuc.append((ad, beklenen, "UYGULANAMADI"))
                continue
            with open(bp, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
            b = subprocess.run([sys.executable, bp], capture_output=True, text=True)
            if b.returncode != 0:
                print("  %-46s BUILD DUSTU rc=%d" % (ad, b.returncode))
                sonuc.append((ad, beklenen, "BUILD-DUSTU"))
                continue
            iddia, ihlal, ozet = olc(kopya)
            gozlenen = "KIRMIZI" if ihlal else "YESIL"
            print("  %-46s beklenen=%-8s gozlenen=%-8s iddia=%d ihlal=%d"
                  % (ad, beklenen, gozlenen, iddia, len(ihlal)))
            for m in ihlal[:3]:
                print("      - %s" % m)
            sonuc.append((ad, beklenen, gozlenen))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    sonda = _agac_damgasi(KOK)
    print("canli agac sha256 (sonda): %s" % sonda)
    if basta != sonda:
        print("KIRMIZI: canli agac mutasyondan etkilendi!")
        return 1
    kotu = [s for s in sonuc if s[1] != s[2]]
    print("MUTASYON: %d/%d mutant beklendigi gibi." % (len(sonuc) - len(kotu), len(sonuc)))
    return 1 if kotu else 0


def main():
    if "--mutasyon" in sys.argv:
        return mutasyon()
    iddia, ihlal, ozet = olc(KOK)
    print("acik aile: %d | olculen KAPALI sayfa: %d | olculen ACIK sayfa: %d"
          % (ozet["acik_aile"], ozet["kapali_sayfa"], ozet["acik_sayfa"]))
    if ozet["kapali"]:
        print("kapali aile sayfalari: %s" % ", ".join(ozet["kapali"]))
    if ihlal:
        print("KIRMIZI: %d ihlal / %d iddia" % (len(ihlal), iddia))
        for m in ihlal:
            print("  - %s" % m)
        return 1
    print("YESIL: %d iddia, 0 ihlal (kapali ailede fiyat/InStock beyani yok, "
          "acik ailede fiyat yerinde)." % iddia)
    return 0


if __name__ == "__main__":
    sys.exit(main())
