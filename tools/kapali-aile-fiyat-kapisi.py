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

  --- IKINCI YUZEY: ANA SAYFA KARTI (2026-08-04) -----------------------------------
  Ayni kusur sinifi KART yuzeyinde de vardi: sayfa yuzeyi kapatildiktan sonra da
  ana sayfa sari karti "130,00 TL'den baslayan" gosteriyordu (canlida olculdu).
  Kartin fiyat metnini index.html'deki `kartFiyatMetni` uretir; sayiyi ona
  /taban-fiyatlar.js (build.py uretir) tasir. Kart ekseni GERCEKTEN kosturularak
  olculur: node, secenekler.js + uretilmis taban-fiyatlar.js'i yukler, index.html'den
  `kartFiyatMetni` fonksiyonunun KENDI KAYNAGINI cikarip calistirir (yeniden yazilmaz).
  E. KAPALI aile karti (her biri 4 iddia):
       1. kart metninde sayisal "…,… TL" YOK
       2. kart metni = sayfadaki aciklayici cumle (FIYATSIZ_METIN) — metin ayrisamaz
       3. id taban fiyat haritasinda YOK (sayiyi tasiyan kanal kapali)
       4. urunler.json'da sabit `fiyat` alani BOS (dolu olsa kart onu basardi)
  F. ACIK aile karti (her biri 2 iddia — POZITIF eksen):
       1. kart metninde sayisal "…,… TL" VAR
       2. taban haritasindaki deger semanin tabanFiyatTL'si ile AYNI
  G. KART YUZEY GUVENCESI: en az 3 acik + en az 1 kapali kart olculmus olmali;
     artefakt/fonksiyon okunamazsa OLCULEMEDI (kirmizi), sessiz yesil YOK.

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


# KART PROBU — index.html'in GERCEK `kartFiyatMetni` fonksiyonunu (kaynagi cikarilip)
# uretilmis taban-fiyatlar.js + secenekler.js ile calistirir. Kod BURAYA KOPYALANMAZ
# ([[mimar-kapi-parser-taklidi]]): kural degisirse bu prob degisen kodu kosar.
NODE_KART_PROBU = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const KOK = process.argv[2];
const idler = JSON.parse(process.argv[3]);
const sandbox = { console: { log(){}, warn(){}, error(){} } };
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), sandbox);
if (!sandbox.PRUVO_SECENEK) { console.error("PRUVO_SECENEK yuklenemedi"); process.exit(2); }
const tabanYol = path.join(KOK, "taban-fiyatlar.js");
if (!fs.existsSync(tabanYol)) {
  console.error("taban-fiyatlar.js YOK — once python3 tools/build.py"); process.exit(3);
}
vm.runInContext(fs.readFileSync(tabanYol, "utf8"), sandbox);
const html = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const bas = html.indexOf("function kartFiyatMetni(");
if (bas < 0) { console.error("index.html'de kartFiyatMetni bulunamadi"); process.exit(4); }
let derinlik = 0, son = -1;
for (let j = html.indexOf("{", bas); j < html.length; j++) {
  const c = html[j];
  if (c === "{") { derinlik++; }
  else if (c === "}") { derinlik--; if (derinlik === 0) { son = j; break; } }
}
if (son < 0) { console.error("kartFiyatMetni govdesi kapanmiyor"); process.exit(5); }
vm.runInContext(html.slice(bas, son + 1), sandbox, { filename: "index.html:kartFiyatMetni" });
if (typeof sandbox.kartFiyatMetni !== "function") {
  console.error("kartFiyatMetni calistirilamadi"); process.exit(6);
}
const kart = {};
for (const id of idler) {
  kart[id] = sandbox.kartFiyatMetni({ id: id, parametrik: true, fiyat: "" });
}
console.log(JSON.stringify({
  kart: kart,
  taban: sandbox.window.PRUVO_TABAN_FIYATLAR || null,
  kapali: sandbox.window.PRUVO_SATIS_KAPALI || null,
  fiyatsiz: sandbox.window.PRUVO_FIYATSIZ_METIN || null
}));
"""


def _node_kart_metinleri(kok, idler):
    """Kartin BUGUN bastigi metni gercek kodla olcer; (veri, hata) doner."""
    if shutil.which("node") is None:
        return None, "node yok -> kart yuzeyi GERCEKTEN kosturulamadi (fail-closed)"
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(NODE_KART_PROBU)
        prob = f.name
    try:
        s = subprocess.run(["node", prob, kok, json.dumps(sorted(idler))],
                           capture_output=True, text=True)
        if s.returncode != 0:
            return None, "kart probu rc=%d: %s" % (s.returncode, (s.stderr or "").strip()[:200])
        return json.loads(s.stdout), None
    except Exception as e:                                  # noqa: BLE001
        return None, "kart probu cozumlenemedi: %s" % e
    finally:
        os.unlink(prob)


def _urun_fiyat_alanlari(kok, idler):
    """urunler.json'dan {id: (parametrik_mi, fiyat_metni)} — yalniz istenen id'ler."""
    yol = os.path.join(kok, "urunler.json")
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    istenen = set(idler)
    return {u.get("id"): (bool(u.get("parametrik")), (u.get("fiyat") or "").strip())
            for u in veri if u.get("id") in istenen}


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


def _sema_tabani(kok, pid):
    """Semadaki tabanFiyatTL (yoksa None) — kart haritasinin DOGRU sayiyi tasidigi
    iddiasinin bagimsiz kaynagi."""
    yol = os.path.join(kok, "jenerator", "urunler", pid + ".json")
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return (json.load(f) or {}).get("tabanFiyatTL")


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

    # ------------------------------------------------------------------ KART YUZEYI
    # (E/F/G) — ana sayfa sari karti. Sayfa yuzeyinden BAGIMSIZ olculur: sayfa dogru
    # olup kart yanlis olabilir (2026-08-04'te tam olarak bu oldu).
    kart_kapali_olculen = []
    kart_acik_olculen = []
    kart_veri, kart_hata = _node_kart_metinleri(kok, list(semalar))
    iddia += 1
    if kart_veri is None:
        ihlal.append("E/OLCULEMEDI: %s" % kart_hata)
    else:
        taban_harita = kart_veri.get("taban") or {}
        kart_metinleri = kart_veri.get("kart") or {}
        urun_alanlari = _urun_fiyat_alanlari(kok, list(semalar))
        for pid in sorted(semalar):
            aile = semalar[pid]
            acik_mi = isinstance(aile, str) and aile in acik_kume
            kart = kart_metinleri.get(pid) or {}
            metin = (kart.get("metin") or "").strip()
            if not acik_mi:
                kart_kapali_olculen.append(pid)
                iddia += 4
                if TL_BEYAN_RE.search(metin):
                    ihlal.append("E1: %s (aile=%s) KAPALI ama KARTTA sayisal TL beyani: %r"
                                 % (pid, aile, metin[:80]))
                if metin != fiyatsiz_metin:
                    ihlal.append("E2: %s (aile=%s) KAPALI ama kart metni sayfadakiyle AYNI "
                                 "degil (kart=%r, beklenen=%r)"
                                 % (pid, aile, metin[:80], fiyatsiz_metin))
                if pid in taban_harita:
                    ihlal.append("E3: %s (aile=%s) KAPALI ama taban fiyat haritasinda: %r"
                                 % (pid, aile, taban_harita[pid]))
                _, sabit_fiyat = urun_alanlari.get(pid, (False, ""))
                if sabit_fiyat:
                    ihlal.append("E4: %s (aile=%s) KAPALI ama urunler.json'da sabit fiyat "
                                 "dolu (%r) — kart onu basar" % (pid, aile, sabit_fiyat))
            else:
                kart_acik_olculen.append(pid)
                iddia += 2
                if not TL_BEYAN_RE.search(metin):
                    ihlal.append("F1: %s (aile=%s) ACIK ama KARTTA sayisal TL beyani YOK "
                                 "(%r) — kapi asiri hevesli" % (pid, aile, metin[:80]))
                sema_taban = _sema_tabani(kok, pid)
                if sema_taban is not None and taban_harita.get(pid) != sema_taban:
                    ihlal.append("F2: %s (aile=%s) ACIK ama taban haritasi semadan ayristi "
                                 "(harita=%r, sema=%r)"
                                 % (pid, aile, taban_harita.get(pid), sema_taban))
        # --- G. kart yuzey guvencesi
        iddia += 1
        if len(kart_acik_olculen) < 3:
            ihlal.append("G: kart POZITIF ekseni bos — yalniz %d acik kart olculdu (>=3 sart)"
                         % len(kart_acik_olculen))
        iddia += 1
        if kapali_olculen and not kart_kapali_olculen:
            ihlal.append("G: kart NEGATIF ekseni bos — sayfa ekseninde %d kapali aile var "
                         "ama kartta 0 olculdu" % len(kapali_olculen))

    ozet = {"acik_aile": len(acik_kume), "kapali_sayfa": len(kapali_olculen),
            "acik_sayfa": len(acik_olculen), "kapali": kapali_olculen,
            "kapali_kart": len(kart_kapali_olculen), "acik_kart": len(kart_acik_olculen)}
    return iddia, ihlal, ozet


# ---------------------------------------------------------------------------
# MUTASYON SURUCUSU — DAIMA IZOLE KOPYADA ([[mutasyon-diske-yazma-tuzagi]]).
# Kanit yeniden uretilebilir olsun diye surucu REPODA durur
# ([[mutasyon-kaniti-yeniden-uretilebilir]]).
# ---------------------------------------------------------------------------
_KARAR_CAPASI = "    return not (isinstance(aile, str) and aile in HACIM_DOGRULANMIS_AILELER)"
# Kart haritasinin KAPALI aileyi disarida birakan kolu (yalniz KART yuzeyini etkiler).
_KART_CAPASI = ("            if aile_satis_kapali_mi(sema):\n"
                "                kapali[pid] = 1\n"
                "                continue")

MUTANTLAR = [
    # (ad, beklenen, eski, yeni)
    # --- ORTAK KARAR (iki yuzeyi de besler)
    ("a-duzeltmeyi-oldur (kapali aile ACIK sayilsin)", "KIRMIZI",
     _KARAR_CAPASI, "    return False"),
    ("b-asiri-hevesli (her aile KAPALI sayilsin)", "KIRMIZI",
     _KARAR_CAPASI, "    return True"),
    ("c-kontrol (De Morgan, davranis korunur)", "YESIL",
     _KARAR_CAPASI,
     "    return (not isinstance(aile, str)) or (aile not in HACIM_DOGRULANMIS_AILELER)"),
    # --- YALNIZ KART YUZEYI: sayfa/JSON-LD ekseni DOGRU kalirken kart bozulur.
    # AYIRT EDICI mutantlar ([[beyan-edilmis-survivor]]): kart iddialari zincirin
    # geri kalanindan BAGIMSIZ kirmizi yakabiliyor mu, onu olcerler.
    ("d-kart-duzeltmesini-oldur (kapali id haritada kalsin)", "KIRMIZI",
     _KART_CAPASI,
     "            if False:\n                kapali[pid] = 1\n                continue"),
    ("e-kart-asiri-hevesli (acik id de haritadan dussun)", "KIRMIZI",
     _KART_CAPASI,
     "            if True:\n                kapali[pid] = 1\n                continue"),
    ("f-kart-kontrol (cift olumsuzlama, davranis korunur)", "YESIL",
     _KART_CAPASI,
     "            if not (not aile_satis_kapali_mi(sema)):\n"
     "                kapali[pid] = 1\n                continue"),
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
    for ad in ("tools/build.py", "secenekler.js", "index.html",
               "tools/kapali-aile-fiyat-kapisi.py"):
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
    print("acik aile: %d | olculen KAPALI sayfa: %d | olculen ACIK sayfa: %d "
          "| KAPALI kart: %d | ACIK kart: %d"
          % (ozet["acik_aile"], ozet["kapali_sayfa"], ozet["acik_sayfa"],
             ozet["kapali_kart"], ozet["acik_kart"]))
    if ozet["kapali"]:
        print("kapali aile sayfalari: %s" % ", ".join(ozet["kapali"]))
    if ihlal:
        print("KIRMIZI: %d ihlal / %d iddia" % (len(ihlal), iddia))
        for m in ihlal:
            print("  - %s" % m)
        return 1
    print("YESIL: %d iddia, 0 ihlal (kapali ailede sayfa VE kart fiyat/InStock beyani "
          "yok, acik ailede fiyat yerinde)." % iddia)
    return 0


if __name__ == "__main__":
    sys.exit(main())
