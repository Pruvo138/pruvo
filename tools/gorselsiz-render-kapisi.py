#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GORSELSIZ RENDER KAPISI — gorseli HIC olmayan urunun MUSTERIYE GORUNEN yuzeylerde
duzgun ve KASITLI cizildigini, gorseli OLAN urunun ise HIC etkilenmedigini olcer.

NEDEN VAR (olculdu 1 Agu; hatanin TAMAMI sessizdi)
--------------------------------------------------
`tools/parti-kontrol.py` 724a69b2 ile gorsel zorunluluguna DAR bir istisna acti: acik
`"gorselsiz": true` beyani + hazir ticari mal sinifi (`tur == "fiziksel"`) + gercekten hic
gorsel olmamasi bir arada saglanirsa urun gorselsiz eklenebiliyor. Kapi tarafi olculmustu;
o urunun MUSTERIYE NASIL GORUNDUGU olculmemisti. Olcum sonuclari (ONCE):

  1. URUN SAYFASI KAPAGI — `cover = imgs[0] if imgs else (SITE + "/favicon.png")`.
     `favicon.png` depoda YOK ve canlida 404 (olculdu: `curl https://pruvo3d.com/
     favicon.png` -> HTTP 404, text/html hata sayfasi). Yani musteri 800x800'luk bir
     KIRIK GORSEL ikonu goruyordu. Sayfadaki tek gorsel bu.
  2. og:image + twitter:image — AYNI 404 URL. WhatsApp/X paylasim onizlemesi kirik.
  3. JSON-LD Product.image — AYNI 404 URL. Google icin "gorsel beyan edildi, alinamadi".
  4. 🔴 ILGILI URUNLER KARTI — `rcov = rimgs[0] if rimgs else cover`: gorselsiz KOMSU
     urunun karti, BULUNULAN SAYFANIN kapagiyla basiliyordu. "B urunu" yazan ve B'nin
     sayfasina giden kartta A urununun FOTOGRAFI. Kirik gorselden BETER — musteri yanlis
     parcayi siparis edebilir.

Hicbiri kirmizi yakmiyordu: build gecer, feed gecer (gorselsiz urun feed'e zaten girmez),
sitemap gecer. Yalniz musteri ve crawler gorur.

SONRA (bu kapinin kilitledigi davranis)
---------------------------------------
  * Kapak ve ilgili-urun karti: ag istegi OLMAYAN `data:` URI yer tutucu. Sekil ana
    sayfadaki kart yer tutucusuyla (index.html `phData`) BAYT-AYNI -> ziyaretciye yeni
    bir gorsel dil uydurulmuyor, katalogda gordugu kutu urun sayfasinda da cikiyor.
  * og:image / twitter:image / JSON-LD `image`: gorsel yoksa alan HIC basilmaz.
    "Yanlis/kirik gorsel" yerine "gorsel yok" beyani (fail-closed). data: URI bu
    alanlara KONMAZ — OG kaziyicilari ve schema.org tuketicileri mutlak URL bekler.
  * Gorseli OLAN urun: cikti bugunkuyle BAYT-ESIT (olculdu; bkz. R iddialari).

IDDIALAR
--------
  D1 DRIFT   build.py `placeholder_data_uri(kat)` ciktisi, index.html'in GERCEK
             `phData(kat)` fonksiyonunun node'daki ciktisiyla BEYAN EDILEN HER KATEGORI
             icin BAYT-AYNI. Kod kopyalanmaz; canli dosyanin fonksiyonu kosturulur.
             ([[ikiz-tanim-sessiz-ayrisma]] — iki yuzey sessizce ayrisamaz.)
  D2 JS      index.html gorselsiz kayitta PATLAMAZ: `coverOf` uc gercek girdi seklinde
             (gorseller: [], gorseller yok, edge karti `gorsel: null`) atmadan bir yer
             tutucu dizesi dondurur. Bos/undefined donerse `img.src = coverOf(p)` kirik
             gorsel ikonu cizerdi.
  G1 KAPAK   Gorselsiz urun sayfasinda main-img `data:image/svg+xml` yer tutucudur;
             sayfanin HICBIR yerinde "favicon.png" GECMEZ.
  G2 META    Gorselsiz sayfada og:image ve twitter:image etiketleri HIC YOK.
  G3 JSONLD  Gorselsiz sayfada Product JSON-LD'de `image` ANAHTARI HIC YOK
             (bos dizi/bos dize de degil — anahtar yok).
  G4 KOMSU   Gorselli bir sayfanin ILGILI URUNLER bolumundeki gorselsiz komsu kart,
             O SAYFANIN kapagini TASIMAZ; kendi kategorisinin yer tutucusunu tasir.
  R1 REG     Gorselli urun sayfasi: og:image + twitter:image + JSON-LD `image` GERCEK
             URL ile basilir ve sayfada HICBIR `data:image/svg+xml` yer tutucu YOKTUR.
  R2 REG     Gorselli urunun ILGILI URUNLER kartlari gercek URL tasir.
  R3 REG     Gorselsiz urun Merchant feed'e GIRMEZ (eski davranis korundu).
  R4 REG     Gorselsiz urunun edge karti (`kart_ozeti`) `gorsel: None` tasir — index.html
             bu sekli zaten yer tutucuya cevirir (D2 ile baglanir).

MUTASYON (--mutasyon): build.py'de tek satirlik kaynak mutasyonlari (hepsi ESKI/hatali
davranisin geri getirilmesi ya da yer tutucunun sessizce ayrilmasi) uygulanir ve bu
kapinin KIRMIZI yandigi KANITLANIR. Mutasyon DISKE YAZILMAZ (kosum yarida kalirsa mutant
build.py commit'e sizardi — [[mutasyon-diske-yazma-tuzagi]]).

Offline (ag yok), GERCEK urunler.json OKUNMAZ (sentetik fiksturler), repoya DOSYA YAZMAZ.
node ZORUNLU — yoksa FAIL-CLOSED kirmizi: D1/D2 iddialari olculmeden kapi YESIL veremez.

NE OLCULMEZ (acikca): tarayicida gercek boyama; index.html sepet PANELININ tam DOM
render'i (o eksen shop/test/sepet-panel.js'te); Worker/D1 edge kart yolu (HocA duzlemi);
e-posta sablonu (shop/src/eposta.js gorseli zaten kosullu basiyor).

Kullanim:
    python3 tools/gorselsiz-render-kapisi.py
    python3 tools/gorselsiz-render-kapisi.py --mutasyon

Cikis kodlari: 0 = YESIL · 1 = KIRMIZI.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
BUILD_YOL = os.path.join(TOOLS, "build.py")
INDEX_YOL = os.path.join(ROOT, "index.html")
AYIKLA_YOL = os.path.join(TOOLS, "html-blok-ayikla.js")


# --------------------------------------------------------------------------- build modulu
def build_modulu(mutasyon=None):
    """tools/build.py'yi (istege bagli TEK kaynak-kodu mutasyonuyla) BELLEKTE yukler."""
    with open(BUILD_YOL, encoding="utf-8") as f:
        src = f.read()
    if mutasyon is not None:
        eski, yeni = mutasyon
        if src.count(eski) != 1:
            raise SystemExit("MUTASYON CAPASI KAYIP/COKLU (%d adet): %r — build.py "
                             "degismis, capa guncellenmeli." % (src.count(eski), eski))
        src = src.replace(eski, yeni, 1)
    mod = types.ModuleType("build_olculen")
    mod.__file__ = BUILD_YOL
    mod.__name__ = "build_olculen"          # __main__ DEGIL -> main() kendiliginden kosmaz
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    exec(compile(src, BUILD_YOL, "exec"), mod.__dict__)
    return mod


# --------------------------------------------------------------------------- fiksturler
def _urun(uid, gorseller, kategori="Marin", tur=None, gorselsiz=False):
    """Sentetik urun. gorseller=None -> `gorseller` ALANI HIC YOK."""
    u = {"id": uid, "baslik": "Sinama %s" % uid, "kategori": kategori,
         "marka": ["Sinama"], "fiyat": "1000 TL",
         "aciklama": "Sinama aciklamasi.\nIkinci satir."}
    if gorseller is not None:
        u["gorseller"] = gorseller
    if tur is not None:
        u["tur"] = tur
    if gorselsiz:
        u["gorselsiz"] = True
    return u


GERCEK_URL = "https://media.pruvo3d.com/urunler/dolu-1.jpg"
GERCEK_URL2 = "https://media.pruvo3d.com/urunler/dolu-2.jpg"
# ⚠️ ";utf8," DAHIL: her sayfada `<link rel="icon" href="data:image/svg+xml,<svg ...">`
# (build.FAVICON) zaten var. Kisa onek kullansaydik "gorselli sayfaya yer tutucu sizdi"
# iddiasi FAVICON'un KENDISIYLE karsilanir ve mutant hayatta kalirdi (olculdu).
YER_TUTUCU_ONEK = "data:image/svg+xml;utf8,"


def _product_ld(html):
    """Sayfadaki Product tipli JSON-LD blogu (yoksa None)."""
    for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                           html, re.S):
        try:
            o = json.loads(blob)
        except ValueError:
            continue
        if isinstance(o, dict) and o.get("@type") == "Product":
            return o
    return None


def _rel_kartlari(html):
    """[(alt, src), ...] — ILGILI URUNLER bolumundeki kartlar."""
    return [(m.group(2), m.group(1)) for m in re.finditer(
        r'<img class="rel-img" src="([^"]*)"[^>]*alt="([^"]*)"', html)]


def _main_img_src(html):
    m = re.search(r'<img class="main-img"[^>]*\ssrc="([^"]*)"', html)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- node (drift)
def node_olcumu(kategoriler):
    """index.html'in GERCEK phData/coverOf fonksiyonlarini node'da kosturur.

    Inline blok tools/html-blok-ayikla.js ile ICERIK IMZASINA gore ayiklanir (konum/sira
    capasi YOK). Blok bir IIFE ile sarilidir; ic fonksiyonlara ulasmak icin YALNIZ bu
    sarmal soyulur — soyma FAIL-CLOSED dogrulanir (sarmalin sekli degisirse kapi ACIKCA
    kirmizi yanar, sessizce "olculemedi" demez).

    Blok node:vm'de kosturulur; DOM'u taklit etmek icin her ozelligi kendine benzer bir
    nesne donduren Proxy kullanilir. Kosum bir yerde atarsa YUTULUR: `function`
    bildirimleri betik degerlendirmesinin BASINDA hoist edildigi icin phData/coverOf
    sandbox'ta her halukarda tanimlidir. Tanimli DEGILSE -> kirmizi."""
    betik = """
const fs = require("node:fs");
const vm = require("node:vm");
const { inlineScriptBul } = require(%(ayikla)s);
const html = fs.readFileSync(%(index)s, "utf8");
const govde = inlineScriptBul(html, "kartCiz");
if (!govde) { console.error("index.html inline katalog scripti bulunamadi"); process.exit(3); }

// IIFE SARMALINI SOY — ic fonksiyonlara (phData/coverOf) ulasmanin tek yolu. Sarmalin
// sekli degisirse BURADA kirmizi yanar; sessizce "olculemedi" YOK.
const kirp = govde.trim();
const BAS = "(function(){";
const SON = "})();";
if (!kirp.startsWith(BAS) || !kirp.endsWith(SON)) {
  console.error("inline blok IIFE sarmali beklenen sekilde degil: bas="
    + JSON.stringify(kirp.slice(0, 20)) + " son=" + JSON.stringify(kirp.slice(-8)));
  process.exit(5);
}
const ic = kirp.slice(BAS.length, kirp.length - SON.length);

function sahte(ad) {
  const hedef = function () { return sahte(ad); };
  return new Proxy(hedef, {
    get(_t, k) {
      if (k === Symbol.toPrimitive || k === "toString") { return () => ""; }
      if (k === "length") { return 0; }
      if (k === Symbol.iterator) { return function* () {}; }
      return sahte(ad + "." + String(k));
    },
    set() { return true; },
    apply() { return sahte(ad + "()"); },
    has() { return true; },
  });
}
const kum = {
  console, JSON, Math, Date, RegExp, Array, Object, String, Number, Boolean, Error,
  encodeURIComponent, decodeURIComponent, setTimeout: () => 0, clearTimeout: () => {},
  document: sahte("document"), localStorage: sahte("localStorage"),
  fetch: () => Promise.resolve(sahte("resp")), navigator: sahte("navigator"),
  location: { search: "", hash: "", href: "https://pruvo3d.com/", pathname: "/" },
  history: sahte("history"), addEventListener: () => {}, requestAnimationFrame: () => 0,
};
kum.window = kum; kum.globalThis = kum; kum.self = kum;
const ctx = vm.createContext(kum);
try { vm.runInContext(ic, ctx, { timeout: 20000 }); } catch (e) { /* hoisting yeter */ }

if (typeof kum.phData !== "function" || typeof kum.coverOf !== "function") {
  console.error("phData/coverOf sandbox'ta tanimli degil (index.html yapisi degisti mi?)");
  process.exit(4);
}
const kategoriler = %(kategoriler)s;
const ph = {};
for (const k of kategoriler) { ph[k] = kum.phData(k); }

// D2 — gorselsiz kaydin UC gercek sekli. Atarsa burada patlar (rc != 0).
const sekiller = {
  bos_dizi: { id: "x", kategori: "Marin", baslik: "b", gorseller: [] },
  alan_yok: { id: "x", kategori: "Marin", baslik: "b" },
  edge_null: { id: "x", kategori: "Marin", baslik: "b", gorsel: null },
};
const cover = {};
let hata = null;
try {
  for (const ad of Object.keys(sekiller)) { cover[ad] = kum.coverOf(sekiller[ad]); }
} catch (e) { hata = String(e && e.message || e); }
console.log(JSON.stringify({ ph, cover, hata }));
""" % {"ayikla": json.dumps(AYIKLA_YOL), "index": json.dumps(INDEX_YOL),
       "kategoriler": json.dumps(kategoriler, ensure_ascii=False)}
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8",
                                     delete=False) as f:
        f.write(betik)
        yol = f.name
    try:
        r = subprocess.run([os.environ.get("NODE", "node"), yol],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise SystemExit("KIRMIZI: node kosturulamadi (%s) — D1/D2 iddialari OLCULEMEDI. "
                         "node bu kapinin BLOKLAYICI on-kosuludur." % e)
    finally:
        os.unlink(yol)
    if r.returncode != 0:
        raise SystemExit("KIRMIZI: index.html olcumu node'da kosmadi (rc=%d):\n%s"
                         % (r.returncode, (r.stderr or "")[:2000]))
    return json.loads(r.stdout.strip().splitlines()[-1])


# --------------------------------------------------------------------------- iddialar
def kosum(mod, node):
    """Butun iddialari olcer; (hatalar, satirlar) dondurur. hatalar bos = YESIL."""
    hatalar, satirlar = [], []

    kategoriler = list(mod.CATEGORIES) + list(mod.NAV_GIZLI)

    # --- D1 DRIFT: build.py yer tutucusu == index.html phData (BAYT)
    ayrisan = [k for k in kategoriler
               if mod.placeholder_data_uri(k) != node["ph"].get(k)]
    if ayrisan:
        ornek = ayrisan[0]
        hatalar.append(
            "D1 yer tutucu index.html phData'dan AYRISTI (%d/%d kategori). Ornek %r:\n"
            "    build.py : %s\n    index.html: %s"
            % (len(ayrisan), len(kategoriler), ornek,
               mod.placeholder_data_uri(ornek)[:160], (node["ph"].get(ornek) or "")[:160]))
    satirlar.append("D1 yer tutucu drift (%d kategori): %s"
                    % (len(kategoriler),
                       "BAYT-AYNI ✔" if not ayrisan else "AYRISAN: %s ✘" % ayrisan[:4]))

    # --- D2 JS: gorselsiz kayitta index.html patlamaz, bos donmez
    if node["hata"]:
        hatalar.append("D2 index.html coverOf gorselsiz kayitta ATTI: %s" % node["hata"])
    else:
        bos = [ad for ad, v in node["cover"].items()
               if not isinstance(v, str) or not v.startswith(YER_TUTUCU_ONEK)]
        if bos:
            hatalar.append("D2 coverOf gorselsiz kayitta yer tutucu DONDURMEDI: %s"
                           % {ad: node["cover"][ad] for ad in bos})
    satirlar.append("D2 index.html coverOf (bos dizi / alan yok / edge gorsel:null): %s"
                    % ("3/3 yer tutucu, JS hatasi YOK ✔" if not hatalar
                       or not any(h.startswith("D2") for h in hatalar)
                       else "SORUNLU ✘"))

    # --- fiksturler
    bos = _urun("bos-urun", [], tur="fiziksel", gorselsiz=True)
    bos_alansiz = _urun("bos-alansiz", None, tur="fiziksel", gorselsiz=True)
    dolu = _urun("dolu-urun", [GERCEK_URL, GERCEK_URL2])
    tum = [bos, bos_alansiz, dolu]

    bos_html = mod.render_product(bos, tum)
    bos_alansiz_html = mod.render_product(bos_alansiz, tum)
    dolu_html = mod.render_product(dolu, tum)

    # --- G1 KAPAK
    for etiket, h in (("gorseller: []", bos_html), ("gorseller alani YOK", bos_alansiz_html)):
        src = _main_img_src(h)
        if src is None or not src.startswith(YER_TUTUCU_ONEK):
            hatalar.append("G1 (%s) main-img yer tutucu DEGIL: %r" % (etiket, (src or "")[:120]))
        if "favicon.png" in h:
            hatalar.append("G1 (%s) sayfada hala 'favicon.png' (404 URL) geciyor" % etiket)
    satirlar.append("G1 gorselsiz kapak (2 fikstur): %s"
                    % ("data: yer tutucu, favicon.png YOK ✔"
                       if not [h for h in hatalar if h.startswith("G1")] else "SORUNLU ✘"))

    # --- G2 META
    g2 = []
    for etiket, h in (("gorseller: []", bos_html), ("gorseller alani YOK", bos_alansiz_html)):
        if 'property="og:image"' in h:
            g2.append("%s: og:image basilmis" % etiket)
        if 'name="twitter:image"' in h:
            g2.append("%s: twitter:image basilmis" % etiket)
    if g2:
        hatalar.append("G2 gorselsiz sayfada paylasim gorseli etiketi VAR: " + "; ".join(g2))
    satirlar.append("G2 gorselsiz sayfa og:image/twitter:image: %s"
                    % ("HIC BASILMIYOR ✔" if not g2 else "SIZAN: %s ✘" % g2))

    # --- G3 JSONLD
    g3 = []
    for etiket, h in (("gorseller: []", bos_html), ("gorseller alani YOK", bos_alansiz_html)):
        ld = _product_ld(h)
        if ld is None:
            g3.append("%s: Product JSON-LD blogu bulunamadi" % etiket)
        elif "image" in ld:
            g3.append("%s: `image` anahtari VAR (%r)" % (etiket, ld["image"]))
    if g3:
        hatalar.append("G3 gorselsiz sayfa JSON-LD: " + "; ".join(g3))
    satirlar.append("G3 gorselsiz sayfa JSON-LD `image`: %s"
                    % ("anahtar HIC YOK ✔" if not g3 else "SORUNLU: %s ✘" % g3))

    # --- G4 KOMSU (capraz bulasma)
    dolu_rel = _rel_kartlari(dolu_html)
    komsu = {alt: src for alt, src in dolu_rel}
    g4 = []
    if not dolu_rel:
        g4.append("ILGILI URUNLER bolumu HIC basilmadi — iddia OLCULEMEDI (fikstur bozuk)")
    for alt, src in dolu_rel:
        if alt in ("Sinama bos-urun", "Sinama bos-alansiz"):
            if src in (GERCEK_URL, GERCEK_URL2):
                g4.append("%r kartinda BASKA urunun fotografi: %s" % (alt, src))
            elif not src.startswith(YER_TUTUCU_ONEK):
                g4.append("%r kartinda yer tutucu degil: %r" % (alt, src[:120]))
    if g4:
        hatalar.append("G4 ilgili-urun karti capraz bulasma: " + "; ".join(g4))
    satirlar.append("G4 gorselsiz komsu kart (%d kart): %s"
                    % (len(dolu_rel),
                       "kendi yer tutucusu ✔" if not g4 else "SORUNLU: %s ✘" % g4))

    # --- R1 REG: gorselli sayfa etkilenmedi
    r1 = []
    if ('<meta property="og:image" content="%s">' % GERCEK_URL) not in dolu_html:
        r1.append("og:image gercek URL ile basilmiyor")
    if ('<meta name="twitter:image" content="%s">' % GERCEK_URL) not in dolu_html:
        r1.append("twitter:image gercek URL ile basilmiyor")
    dolu_ld = _product_ld(dolu_html)
    if dolu_ld is None or dolu_ld.get("image") != [GERCEK_URL, GERCEK_URL2]:
        r1.append("JSON-LD `image` gercek URL dizisi degil: %r"
                  % (dolu_ld.get("image") if dolu_ld else None))
    # ⚠️ BOLGE: ILGILI URUNLER bolumu cikarilir. O bolumdeki yer tutucu MESRUDUR (G4'un
    # onardigi sey: gorselsiz KOMSU kendi yer tutucusunu tasir). Bolge kirpilmasaydi bu
    # iddia G4'un dogru davranisiyla catisirdi.
    dolu_kendi = re.sub(r'<section class="related">.*?</section>', "", dolu_html, flags=re.S)
    if YER_TUTUCU_ONEK in dolu_kendi:
        r1.append("gorselli sayfanin KENDI yuzeylerine yer tutucu SIZDI")
    if _main_img_src(dolu_html) != GERCEK_URL:
        r1.append("main-img gercek kapak degil: %r" % (_main_img_src(dolu_html),))
    if r1:
        hatalar.append("R1 gorselli urun sayfasi ETKILENDI: " + "; ".join(r1))
    satirlar.append("R1 gorselli sayfa (og+twitter+jsonld+kapak, yer tutucu sizmasi): %s"
                    % ("DEGISMEDI ✔" if not r1 else "SORUNLU: %s ✘" % r1))

    # --- R2 REG: gorselli komsu kart gercek URL
    dolu_komsu_src = komsu.get("Sinama dolu-urun")
    bos_rel = _rel_kartlari(bos_html)
    bos_komsu = {a: s for a, s in bos_rel}
    r2 = []
    if bos_komsu.get("Sinama dolu-urun") != GERCEK_URL:
        r2.append("gorselli komsu kart gercek URL tasimiyor: %r"
                  % (bos_komsu.get("Sinama dolu-urun"),))
    if r2:
        hatalar.append("R2 " + "; ".join(r2))
    satirlar.append("R2 gorselli komsu kart: %s"
                    % ("gercek URL ✔" if not r2 else "SORUNLU: %s ✘" % r2))
    del dolu_komsu_src

    # --- R3 REG: feed
    xml, adet = mod.render_merchant_feed(tum)
    r3 = []
    if "bos-urun" in xml or "bos-alansiz" in xml:
        r3.append("gorselsiz urun Merchant feed'e GIRDI")
    if adet != 1:
        r3.append("feed adedi 1 degil: %d" % adet)
    if r3:
        hatalar.append("R3 " + "; ".join(r3))
    satirlar.append("R3 Merchant feed (gorselsiz eleme): %s"
                    % ("1/3 urun, gorselsizler ELENDI ✔" if not r3 else "SORUNLU: %s ✘" % r3))

    # --- R4 REG: edge kart sekli
    kart = mod.kart_ozeti(bos)
    r4 = []
    if kart.get("gorsel") is not None:
        r4.append("kart_ozeti `gorsel` None degil: %r" % (kart.get("gorsel"),))
    if r4:
        hatalar.append("R4 " + "; ".join(r4))
    satirlar.append("R4 edge kart (kart_ozeti gorsel): %s"
                    % ("None -> index.html yer tutucuya cevirir ✔"
                       if not r4 else "SORUNLU: %s ✘" % r4))

    return hatalar, satirlar


# --------------------------------------------------------------------------- mutasyon
# Her mutant, YALNIZCA bu kapinin yakalayabilecegi bir davranisi bozar. Cogu ESKI
# (hatali) davranisin AYNEN geri getirilmesidir — yani kapi "gecmise donusu" olcer.
MUTANTLAR = [
    ("kapak yeniden 404 favicon.png olur (eski davranis)",
     ('cover = paylasim_gorseli or placeholder_data_uri(kategori)',
      'cover = paylasim_gorseli or (SITE + "/favicon.png")')),
    ("ilgili-urun karti yine SAYFANIN kapagini kullanir (capraz bulasma, eski davranis)",
     ('rcov = rimgs[0] if rimgs else placeholder_data_uri(r.get("kategori") or "")',
      'rcov = rimgs[0] if rimgs else cover')),
    ("og:image/twitter:image kosulsuz basilir (yer tutucu OG'ye sizar)",
     ('paylasim_gorseli = imgs[0] if imgs else ""',
      'paylasim_gorseli = imgs[0] if imgs else placeholder_data_uri(kategori)')),
    ("JSON-LD `image` kosulsuz basilir (eski `imgs or [cover]`)",
     ('    if imgs:\n        product_ld["image"] = imgs\n',
      '    product_ld["image"] = imgs or [cover]\n')),
    ("yer tutucu rengi sessizce degisir (index.html ile drift)",
     ('fill="#1c3a6b"', 'fill="#1c3a6a"')),
    ("data: URI kacis kumesi encodeURIComponent'ten ayrilir ('/' ham kalir)",
     ('quote(placeholder_svg(kat), safe="-_.!~*\'()")',
      'quote(placeholder_svg(kat), safe="/-_.!~*\'()")')),
    ("gorselli urunde paylasim gorseli bosaltilir (regresyon nobetcisi)",
     ('paylasim_gorseli = imgs[0] if imgs else ""',
      'paylasim_gorseli = ""')),
]


def mutasyon_kosumu(node):
    print("MUTASYON — her mutant bu kapiyi KIRMIZI yakmali:")
    olen = 0
    for ad, mut in MUTANTLAR:
        try:
            m = build_modulu(mutasyon=mut)
            hatalar, _ = kosum(m, node)
        except SystemExit as e:
            print("  ⚪ %s -> capa hatasi: %s" % (ad, e))
            continue
        except Exception as e:                                   # noqa: BLE001
            hatalar = ["mutant coktu: %s: %s" % (type(e).__name__, e)]
        if hatalar:
            olen += 1
            print("  ✔ OLDU  %s" % ad)
            print("          ilk bulgu: %s" % hatalar[0].splitlines()[0][:150])
        else:
            print("  ✘ HAYATTA %s  — KAPI BU DEGISIKLIGI GORMUYOR" % ad)
    print("\nMUTASYON: %d/%d oldu" % (olen, len(MUTANTLAR)))
    return 0 if olen == len(MUTANTLAR) else 1


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Gorselsiz urun render kapisi")
    ap.add_argument("--mutasyon", action="store_true",
                    help="kapinin gercekten olctugunu mutantlarla kanitla")
    args = ap.parse_args()

    temiz = build_modulu()
    node = node_olcumu(list(temiz.CATEGORIES) + list(temiz.NAV_GIZLI))

    if args.mutasyon:
        return mutasyon_kosumu(node)

    hatalar, satirlar = kosum(temiz, node)
    print("GORSELSIZ RENDER KAPISI")
    print("-" * 72)
    for s in satirlar:
        print("  " + s)
    print("-" * 72)
    if hatalar:
        print("KIRMIZI — %d bulgu:" % len(hatalar))
        for h in hatalar:
            print("  ✘ " + h)
        return 1
    print("YESIL — butun iddialar olculdu ve gecti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
