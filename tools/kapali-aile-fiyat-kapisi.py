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

  --- UCUNCU YUZEY: CAP CAPALI FIYAT (2026-08-04, Okan karari) ---------------------
  `rulman` fiyati DIS CAPLA DOGRU ORANTILI: 10 TL x mm -> 60/80/100 mm = 600/800/
  1000 TL. Cap fiyatin CAPASINI verir; diger ayarlar (eleman, flans, genislik,
  bosluk, ic cap) capanin etrafinda HACIM ORANINCA module eder (referans = o captaki
  orantili/varsayilan konfigurasyon, hacmi CALISMA ANINDA hesaplanir). Fiyat
  fonksiyonu TUM ailelerce PAYLASILDIGI icin yanlis kapsam 18 ailenin fiyatini
  degistirirdi.
  H. CAPA + EGRI + KAPSAM (gercek `parametrikFiyatKurus` kosumu, koda BAKMADAN):
       H1  varsayilan ayarlarda 60/80/100 mm = 60000/80000/100000 kurus BIREBIR
           (+H1b olculen noktalar semaya gore GECERLI konfigurasyon)
       H2  egri capla KESIN ARTAN (28/30/40/50/60/80/100) + H2b DUZ DEGIL
       H3  28 mm >= 20000 kurus (200,00 TL zemini)
       H4  modulasyon CANLI: flans (H4) ve eleman (H4b) tutari OYNATIYOR
       H5  tavan capaya goreli, MESRU isi kirpmiyor (H5b/H5c) + H5d baglamsiz
           cagri fail-closed null
       H6  capasiz 18 ailenin kurusu (4 yapisal nokta) ve 3x tavani DEGISMEDI
           (+H6b >=3 aile olculdu, +H6c rulman capasiz olculmedi)
  Mutantlar: g (varsayilan tavan 5x -> H6), h (cap kurali TUM ailelere sizar -> H6),
  i (capa orani 9 TL/mm -> H1), j (modulasyon olur, flans bedava -> H4),
  k (kontrol: zemin argumanlari yer degistirir -> YESIL).

SAYI GOMULMEZ: kapali/acik kumesi secenekler.js + jenerator/urunler/*.json
hacimFormulu'sundan TURETILIR. Aile listesi degisince kapi kendini gunceller.

Kullanim (once python3 tools/build.py ile urun/ uretilmis olmali):
  python3 tools/kapali-aile-fiyat-kapisi.py
  python3 tools/kapali-aile-fiyat-kapisi.py --mutasyon   # 9 mutant, IZOLE KOPYADA
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


# FIYAT PROBU (H bolumu) — CAP CAPALI FIYAT + DIGER AILELERIN DEGISMEZLIGI.
# Hicbir sayi BURAYA YAZILMAZ: gercek `parametrikFiyatKurus` kosturulur ve donen
# kurus okunur, yani olculen sey KODUN DAVRANISIDIR ([[mimar-kapi-parser-taklidi]]).
# Rulman egrisi gercek hacim.js + konfigurator.js (fiyatBaglami) uzerinden gecer;
# orantili/varsayilan olcek ic=dis/3, genislik=dis*0,3 (sema izgarasina yuvarli)
# — Okan'in 2026-08-04 karari: 10 TL x dis cap.
NODE_TAVAN_PROBU = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const KOK = process.argv[2];
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), sandbox);
const S = sandbox.window.PRUVO_SECENEK;
if (!S) { console.error("PRUVO_SECENEK yuklenemedi"); process.exit(2); }
const HACIM = require(path.join(KOK, "jenerator", "hacim.js"));
const KONF = require(path.join(KOK, "jenerator", "konfigurator.js"));
const TABAN = 100, DEV_HACIM = 1e12;

/* --- DIGER (capasiz) AILELER: hacim-oranli kural + 3x tavan DEGISMEDI mi?
   Kural BURAYA KOPYALANMAZ; dort YAPISAL nokta olculur:
     taban hacimde taban fiyat · iki kat hacimde iki kat · yari hacimde ZEMIN ·
     dev hacimde tavan (tavan carpani = kurus / (taban*100)).            */
const capasiz = {};
for (const aile of Object.keys(S.HACIM_DOGRULANMIS_AILELER || {})) {
  if (S.capCapasi && S.capCapasi(aile)) { continue; }
  const f = (h) => S.parametrikFiyatKurus(aile, TABAN, 1000, h, "PLA", "Siyah");
  capasiz[aile] = { taban: f(1000), iki_kat: f(2000), yari: f(500),
                    tavan_carpani: (f(DEV_HACIM) == null) ? null : f(DEV_HACIM) / (TABAN * 100) };
}

const semaYol = path.join(KOK, "jenerator", "urunler", "olcuye-ozel-rulman.json");
let egri = null, varyant = null, capa = null, hata = null;
try {
  const sema = JSON.parse(fs.readFileSync(semaYol, "utf8"));
  const varsayilan = KONF.varsayilanDegerler(sema);
  const izgara = (ad, v) => {
    const p = sema.parametreler.filter((x) => x.ad === ad)[0];
    return (p && p.adim) ? Math.round(v / p.adim) * p.adim : v;
  };
  // ORANTILI/VARSAYILAN konfigurasyon: semanin KENDI varsayilanlari + capla
  // olceklenen iki olcu. Ikinci bir parametre listesi YAZILMAZ.
  const ref = (dis) => Object.assign({}, varsayilan, {
    dis_cap: dis, ic_cap: izgara("ic_cap", dis / 3), genislik: izgara("genislik", dis * 0.3) });
  const fiyat = (p, m, r) => KONF.fiyatKurus(sema, p, m || "PLA", r || "Siyah",
                                             { secenek: S, hacim: HACIM });
  egri = {};
  for (const dis of [28, 30, 40, 50, 60, 80, 100]) {
    const p = ref(dis);
    egri[dis] = { kurus: fiyat(p), gecerli: KONF.dogrula(sema, p).gecerli };
  }
  varyant = {
    ref100: fiyat(ref(100)),
    flansli100: fiyat(Object.assign(ref(100), { flans: "var" })),
    ref60: fiyat(ref(60)),
    makara60: fiyat(Object.assign(ref(60), { eleman: "makara" })),
    tutmali60: fiyat(Object.assign(ref(60), { eleman: "tutmali" })),
  };
  /* TAVAN: dev hacimle kosulur -> donen kurus / capa = carpan. EN PAHALI MESRU
     konfigurasyon (2026-08-04 tam izgara taramasinin azami oran noktasi) ASA+Diger
     ile ayri olculur: tavan mesru isi KIRPARSA "flans bedava" geri gelirdi. */
  const ucP = { ic_cap: 6, dis_cap: 28.5, genislik: 30, eleman: "tutmali",
                bosluk: 0.15, flans: "var" };
  const bag100 = KONF.fiyatBaglami(sema, ref(100), HACIM);
  const bagUc = KONF.fiyatBaglami(sema, ucP, HACIM);
  capa = {
    tavan_kurus_100: S.parametrikFiyatKurus(sema.hacimFormulu, sema.tabanFiyatTL,
      sema.tabanHacimMm3, DEV_HACIM, "PLA", "Siyah", bag100),
    tavan_kurus_uc: S.parametrikFiyatKurus(sema.hacimFormulu, sema.tabanFiyatTL,
      sema.tabanHacimMm3, DEV_HACIM, "ASA", "Diğer", bagUc),
    uc_gecerli: KONF.dogrula(sema, ucP).gecerli,
    uc_kurus: fiyat(ucP, "ASA", "Diğer"),
    baglamsiz: S.parametrikFiyatKurus(sema.hacimFormulu, sema.tabanFiyatTL,
      sema.tabanHacimMm3, 5000, "PLA", "Siyah"),
    taban_fiyat_tl: sema.tabanFiyatTL,
  };
} catch (e) { hata = String(e && e.message || e); }
console.log(JSON.stringify({ capasiz: capasiz, egri: egri, varyant: varyant,
                             capa: capa, hata: hata }));
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


def _node_tavan(kok):
    """(veri, hata) — {tavan: {aile: carpan}, egri: {dis: kurus}}. GERCEK kosum."""
    if shutil.which("node") is None:
        return None, "node yok -> tavan ekseni GERCEKTEN kosturulamadi (fail-closed)"
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(NODE_TAVAN_PROBU)
        prob = f.name
    try:
        s = subprocess.run(["node", prob, kok], capture_output=True, text=True)
        if s.returncode != 0:
            return None, "tavan probu rc=%d: %s" % (s.returncode,
                                                    (s.stderr or "").strip()[:200])
        return json.loads(s.stdout), None
    except Exception as e:                                  # noqa: BLE001
        return None, "tavan probu cozumlenemedi: %s" % e
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

    # ------------------------------------------------------- H. CAP CAPALI FIYAT
    # (2026-08-04, Okan karari) `rulman` fiyati DIS CAPLA DOGRU ORANTILI: 10 TL x mm
    # -> 60/80/100 mm = 600/800/1000 TL. Capa fiyatin CAPASI, diger ayarlar (eleman,
    # flans, genislik, bosluk, ic cap) bu capanin etrafinda HACIM ORANINCA module eder.
    # Fiyat fonksiyonu TUM ailelerce PAYLASILDIGI icin yanlis kapsam 18 ailenin
    # fiyatini degistirirdi -> her eksen AYRI olculur:
    #   H1  varsayilan/orantili ayarlarda 60/80/100 mm = 60000/80000/100000 kurus (BIREBIR)
    #   H2  egri capla MONOTON ARTAN (28..100) ve H2b DUZ DEGIL (doygunluk YOK)
    #   H3  28 mm >= 20000 kurus (200,00 TL zemini)
    #   H4  modulasyon CANLI: flans/eleman degisimi tutari OYNATIYOR (bedava degil)
    #   H5  tavan capaya gorelidir ve MESRU isi KIRPMAZ (en pahali mesru konfig < tavan)
    #   H6  capasiz ailelerin kurusu ve 3x tavani DEGISMEDI (>=3 aile, 4 yapisal nokta)
    # Sayilar koda BAKILARAK degil, gercek `parametrikFiyatKurus` kosumundan olculur.
    HEDEF = {60: 60000, 80: 80000, 100: 100000}   # Okan karari: 10 TL x dis cap
    ZEMIN_KURUS = 20000                            # taban fiyat 200,00 TL
    VARSAYILAN_TAVAN_CARPANI = 3
    tavan_veri, tavan_hata = _node_tavan(kok)
    iddia += 1
    if tavan_veri is None:
        ihlal.append("H/OLCULEMEDI: %s" % tavan_hata)
    elif tavan_veri.get("hata"):
        ihlal.append("H/OLCULEMEDI: rulman fiyat egrisi hesaplanamadi: %s"
                     % tavan_veri["hata"])
    else:
        capasiz = tavan_veri.get("capasiz") or {}
        varyant = tavan_veri.get("varyant") or {}
        capa = tavan_veri.get("capa") or {}
        egri = {int(k): v for k, v in (tavan_veri.get("egri") or {}).items()}
        kurus = {d: (egri[d] or {}).get("kurus") for d in egri}

        # H1 — uc capa noktasi BIREBIR (para yuzeyi: musteriye gosterilen tutar)
        for dis in sorted(HEDEF):
            iddia += 1
            if kurus.get(dis) != HEDEF[dis]:
                ihlal.append("H1: rulman %d mm dis capta %r kurus (beklenen %d) — "
                             "Okan'in 10 TL/mm karari tutmuyor"
                             % (dis, kurus.get(dis), HEDEF[dis]))
            iddia += 1
            if not (egri.get(dis) or {}).get("gecerli"):
                ihlal.append("H1b: rulman %d mm orantili konfigurasyonu SEMAYA GORE "
                             "GECERSIZ — olculen nokta satin alinamaz" % dis)
        # H2 — egri capla KESIN MONOTON ARTAN (esitlik = doygunluk, kirmizi)
        iddia += 1
        capraz = sorted(egri)
        artmayan = [(capraz[i - 1], capraz[i]) for i in range(1, len(capraz))
                    if not (isinstance(kurus[capraz[i]], int)
                            and isinstance(kurus[capraz[i - 1]], int)
                            and kurus[capraz[i]] > kurus[capraz[i - 1]])]
        if len(capraz) < 7:
            ihlal.append("H2: egri ekseni bos — yalniz %d nokta olculdu (>=7 sart)"
                         % len(capraz))
        elif artmayan:
            ihlal.append("H2: rulman fiyat egrisi KESIN ARTAN DEGIL (doygunluk/dusus: "
                         "%s; egri=%s)" % (artmayan, {d: kurus[d] for d in capraz}))
        # H2b — CANLILIK: egri duz degil (iddia bos yere yesil yanmasin)
        iddia += 1
        if len(capraz) >= 2 and kurus.get(capraz[0]) == kurus.get(capraz[-1]):
            ihlal.append("H2b: rulman egrisi DUZ (%r) — monotonluk iddiasi bos yere yesil"
                         % kurus.get(capraz[0]))
        # H3 — ZEMIN: en kucuk cap bile taban fiyatin altina inmez
        iddia += 1
        if not (isinstance(kurus.get(28), int) and kurus[28] >= ZEMIN_KURUS):
            ihlal.append("H3: rulman 28 mm %r kurus — %d kurusluk taban zemini tutmuyor"
                         % (kurus.get(28), ZEMIN_KURUS))
        # H4 — MODULASYON CANLI: capa disi secimler tutari OYNATIYOR
        iddia += 1
        if not (isinstance(varyant.get("flansli100"), int)
                and isinstance(varyant.get("ref100"), int)
                and varyant["flansli100"] > varyant["ref100"]):
            ihlal.append("H4: 100 mm'de FLANS BEDAVA (flansli=%r, flanssiz=%r) — capa "
                         "etrafindaki hacim modulasyonu olu"
                         % (varyant.get("flansli100"), varyant.get("ref100")))
        iddia += 1
        elemanlar = [varyant.get("ref60"), varyant.get("makara60"), varyant.get("tutmali60")]
        if len(set(elemanlar)) != 3 or None in elemanlar:
            ihlal.append("H4b: 60 mm'de eleman secimi tutari OYNATMIYOR (bilya/makara/"
                         "tutmali = %r) — modulasyon olu" % (elemanlar,))
        # H5 — TAVAN capaya gorelidir VE mesru isi KIRPMAZ
        iddia += 1
        tavan100 = capa.get("tavan_kurus_100")
        if not (isinstance(tavan100, int) and tavan100 > HEDEF[100]):
            ihlal.append("H5: rulman tavani capaya gore degil (100 mm dev hacimde %r "
                         "kurus, capa %d) — tavan capayi kirpiyorsa egri duzlesir"
                         % (tavan100, HEDEF[100]))
        iddia += 1
        if not capa.get("uc_gecerli"):
            ihlal.append("H5b: en pahali MESRU konfigurasyon capasi bayat — sema bu "
                         "konfigurasyonu artik gecerli saymiyor")
        elif not (isinstance(capa.get("uc_kurus"), int)
                  and isinstance(capa.get("tavan_kurus_uc"), int)
                  and capa["uc_kurus"] < capa["tavan_kurus_uc"]):
            ihlal.append("H5c: TAVAN MESRU ISI KIRPIYOR (en pahali mesru konfig %r kurus, "
                         "tavan %r) — o bolgede flans/eleman secimi bedavaya duser"
                         % (capa.get("uc_kurus"), capa.get("tavan_kurus_uc")))
        # H5d — FAIL-CLOSED: capa baglami olmadan cagri TUTAR URETMEZ
        iddia += 1
        if capa.get("baglamsiz") is not None:
            ihlal.append("H5d: capa baglami OLMADAN rulman tutar uretti (%r) — guncellenmemis "
                         "bir cagri yeri SESSIZ YANLIS FIYAT tahsil ettirir"
                         % capa.get("baglamsiz"))
        # H6 — CAPASIZ ailelerin kurusu ve 3x tavani DEGISMEDI (dort yapisal nokta)
        for aile in sorted(capasiz):
            o = capasiz[aile]
            iddia += 4
            if o.get("taban") != 10000:
                ihlal.append("H6: %s taban hacimde %r kurus (beklenen 10000) — capasiz "
                             "ailenin hacim-orani kurali degismis" % (aile, o.get("taban")))
            if o.get("iki_kat") != 20000:
                ihlal.append("H6: %s iki kat hacimde %r kurus (beklenen 20000)"
                             % (aile, o.get("iki_kat")))
            if o.get("yari") != 10000:
                ihlal.append("H6: %s yari hacimde %r kurus (beklenen 10000 = zemin)"
                             % (aile, o.get("yari")))
            if o.get("tavan_carpani") != VARSAYILAN_TAVAN_CARPANI:
                ihlal.append("H6: %s tavan carpani %r (beklenen %d) — cap capasi/tavan "
                             "istisnasi sizmis" % (aile, o.get("tavan_carpani"),
                                                   VARSAYILAN_TAVAN_CARPANI))
        # H6b — YUZEY GUVENCESI: capasiz eksen bosa kosmasin
        iddia += 1
        if len(capasiz) < 3:
            ihlal.append("H6b: capasiz eksen bos — yalniz %d capasiz acik aile olculdu "
                         "(>=3 sart)" % len(capasiz))
        iddia += 1
        if "rulman" in capasiz:
            ihlal.append("H6c: rulman CAPASIZ olculdu — cap capasi tablosu bosalmis, "
                         "10 TL/mm kurali yururlukte degil")

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

# H bolumu capalari — FIYAT KURALININ TEK KAYNAGI (secenekler.js).
_TAVAN_TABLO_CAPASI = ("  var TAVAN_CARPANI_VARSAYILAN = 3;\n"
                       "  var AILE_TAVAN_CARPANI = {};")
# Cap capasi tablosu: KAPSAM (hangi aile) + ORAN (kac kurus/mm).
_CAPA_KAPSAM_CAPASI = """  function capCapasi(aile) {
    return (typeof aile === "string" &&
            Object.prototype.hasOwnProperty.call(AILE_CAP_CAPASI, aile))
      ? AILE_CAP_CAPASI[aile] : null;
  }"""
_CAPA_ORAN_CAPASI = "      kurusMm: 1000,                            // 10,00 TL / mm"
# Capa etrafindaki HACIM MODULASYONU (flans/eleman/genislik farki buradan gelir).
_CAPA_MODULASYON_CAPASI = "      temel: capa.kurusMm * deger * (hacimMm3 / refHacim),"
# Zemin (kontrol mutantinin capasi — davranis KORUNMALI).
_CAPA_ZEMIN_CAPASI = "      temelKurus = Math.max(tabanFiyatTL * 100, c.temel);"

MUTANTLAR = [
    # (ad, beklenen, eski, yeni[, dosya])  dosya verilmezse tools/build.py
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
    # --- H BOLUMU: CAP CAPALI FIYAT (para). Hepsi secenekler.js'e uygulanir.
    # Her mutant AYIRT EDICI olmali ([[beyan-edilmis-survivor]]): tek bir ekseni
    # bozup digerlerini dogru birakir, yani o eksenin TEK BASINA kirmizi yakabildigini
    # kanitlar. Yoksa "savunma derinligi" iddiasi katmanlarin VEYA'si olurdu.
    # g: tavan istisnasi GLOBALLESIR -> capasiz 18 ailenin tavani %66 zamlanir (H6).
    ("g-tavan-GLOBAL (varsayilan tavan 3x -> 5x)", "KIRMIZI",
     _TAVAN_TABLO_CAPASI,
     "  var TAVAN_CARPANI_VARSAYILAN = 5;\n  var AILE_TAVAN_CARPANI = {};",
     "secenekler.js"),
    # h: CAP KURALI TUM AILELERE SIZAR -> rulman DOGRU kalir, digerleri capa koluna
    #    duser (baglamsiz cagride fail-closed null) -> H6 TEK BASINA yakar.
    ("h-capa-SIZINTI (cap kurali tum ailelere yayilir)", "KIRMIZI",
     _CAPA_KAPSAM_CAPASI,
     """  function capCapasi(aile) {
    return (typeof aile === "string") ? AILE_CAP_CAPASI.rulman : null;
  }""",
     "secenekler.js"),
    # i: capa orani bozulur (10 -> 9 TL/mm) -> H1 uc noktasi yikilir, capasiz
    #    aileler (H6) ve modulasyon (H4) DOGRU kalir.
    ("i-capa-orani-bozuk (10 TL/mm -> 9 TL/mm)", "KIRMIZI",
     _CAPA_ORAN_CAPASI,
     "      kurusMm: 900,                             // 10,00 TL / mm",
     "secenekler.js"),
    # j: MODULASYON OLDURULUR (hacim orani dusurulur) -> capa noktalari (H1) ve
    #    egri (H2) YESIL kalir, ama flans/eleman BEDAVA olur -> H4 TEK BASINA yakar.
    ("j-modulasyon-olu (flans/eleman bedava)", "KIRMIZI",
     _CAPA_MODULASYON_CAPASI,
     "      temel: capa.kurusMm * deger,",
     "secenekler.js"),
    # k: KONTROL — zemin ayni sayilardan turer, davranis KORUNUR.
    ("k-capa-kontrol (zemin argumanlari yer degistirir)", "YESIL",
     _CAPA_ZEMIN_CAPASI,
     "      temelKurus = Math.max(c.temel, tabanFiyatTL * 100);",
     "secenekler.js"),
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
    for mutant in MUTANTLAR:
        ad, beklenen, eski, yeni = mutant[:4]
        hedef_ad = mutant[4] if len(mutant) > 4 else "tools/build.py"
        gecici = tempfile.mkdtemp(prefix="kapali-fiyat-mutant-")
        kopya = os.path.join(gecici, "repo")
        try:
            _kopyala(kopya)
            bp = os.path.join(kopya, "tools", "build.py")
            hedef = os.path.join(kopya, *hedef_ad.split("/"))
            with open(hedef, encoding="utf-8") as f:
                kaynak = f.read()
            if kaynak.count(eski) != 1:
                print("  %-46s MUTASYON UYGULANAMADI (%s icinde capa %d kez bulundu)"
                      % (ad, hedef_ad, kaynak.count(eski)))
                sonuc.append((ad, beklenen, "UYGULANAMADI"))
                continue
            with open(hedef, "w", encoding="utf-8") as f:
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
