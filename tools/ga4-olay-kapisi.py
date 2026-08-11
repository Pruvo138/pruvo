#!/usr/bin/env python3
"""GA4 E-TICARET OLAY KAPISI — reklam olcumunun HUNI ayagi fiilen atesleniyor mu?

NEDEN VAR (olculdu, 11 Agu 2026)
--------------------------------
Reklam panelinde "Sayfa goruntuleme" tek basina dONusum sayilamaz; kampanya karari
huni olaylarina (urun goruntuleme / sepete ekleme / odemeye baslama) dayanir. 11 Agu'ya
kadar sitede GA4 tarafinda BU OLAYLARIN HICBIRI YOKTU: olcum etiketi her sayfada
duruyordu, Meta huni yuzeyi TAM kuruluydu, ama GA4'e yalniz sayfa goruntuleme gidiyordu.
Hata SESSIZ: sitede hicbir sey bozulmaz, konsolda iz kalmaz, panel yalnizca "dONusum yok"
der ve duraklatilan kampanyanin yeniden acilip acilmayacagi OLCUMSUZ kalir.

Ikinci sessiz sinif: Meta yuzeyine yeni bir huni noktasi eklenip GA4 ikizinin
UNUTULMASI. Iki huni sessizce ayrisir ve iki panel farkli rakam gosterir
([[ikiz-tanim-sessiz-ayrisma]]). Bu yuzden kapinin B bolumu esleme KAPSAMASINI olcer:
evren, izlenen agactaki GERCEK Meta cagri noktalarindan TURETILIR (elle defter YOK).

NE OLCER
--------
  (A) YAPISAL  : olay gondericisi (pruvoGA4Track) + beyaz liste, GA cekirdeginin ALTI
                 kopyasinda da var ve TEK KAYNAKTAN birebir ayni.
  (B) KAPSAMA  : her Meta huni noktasinin GA4 ikizi var. `Purchase` istisnasi ELLE
                 BEYAN DEGIL, KANITLA olculur: satin alma olayinin sunucu tarafindan
                 gittigi dogrulanir + istemcide GONDERILMEDIGI + beyaz listede
                 OLMADIGI ayri ayri olculur (cift sayim kapisi).
  (C) DAVRANIS : uretilen GERCEK urun sayfasinin KENDI JS'i node:vm'de kosar/tiklanir;
                 olay kuyruguna (dataLayer) DUSEN cagri olculur — "kod eklendi" degil.
                 Riza YOKKEN sifir olay (yanlis-pozitif ekseni), riza VARKEN view_item +
                 add_to_cart, beyaz liste disi ad (purchase) DUSER.
  (D) DAVRANIS : odemeye baslama noktasi index.html'den KESILIP (kopya tutulmaz) kosar;
                 GA4 kalem kimlikleri Meta'nin gonderdigi kimliklerle BIREBIR olculur.
  (E) KISISEL VERI: C ve D'de gozlenen TUM olay parametreleri musteri alanlarina karsi
                 taranir (ad/telefon/e-posta/adres/sehir) — sizinti 0 olmali.

CIKIS: 0 yesil · 1 kirmizi · 3 olculemedi (node/fikstur/capa yok). Depoya YAZMAZ.
KOSUM: python3 tools/ga4-olay-kapisi.py [--kendini-test]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build          # noqa: E402
import yayin_yuzey    # noqa: E402

YESIL, KIRMIZI, OLCULEMEDI_RC = 0, 1, 3

# --- Kanonik huni eslemesi: Meta olay adi -> GA4 olay adi. TEK KAYNAK. -------
# Yeni bir huni noktasi eklenirse buraya da eklenir; eklenmezse (B) evreni onu
# "eslemesi olmayan Meta noktasi" olarak gorur ve kapi KIRMIZI yanar.
HUNI = {
    "ViewContent": "view_item",
    "AddToCart": "add_to_cart",
    "InitiateCheckout": "begin_checkout",
    "Purchase": "purchase",
}
# Istemciden GONDERILMEYECEK olay: sunucu ayni islemi transaction_id ile zaten atiyor;
# istemci de atarsa ciro IKI KEZ sayilir ve kampanya karari yanlis veriye dayanir.
SUNUCU_TARAFI = "purchase"
SUNUCU_KAYNAK = "shop/src/olcum.js"

# GA cekirdeginin gondericiyi tasimasi ZORUNLU olan kopyalari (tek kaynak: build.py).
CEKIRDEK_KOPYALARI = ("index.html", "hakkimizda/index.html", "iletisim/index.html",
                      "sss/index.html", "gizlilik/index.html")
TEK_KAYNAK = "tools/build.py"

GONDERICI_CAPA = "window.pruvoGA4Track = function(olay, veri){"
BEYAZ_LISTE_CAPA = "window.PRUVO_GA4_OLAYLARI = ["
# Kapanis `};` bir onceki satira BITISIK yazilir: ciplak parantez satiri uretilirse
# tools/varlik-test.py'nin "beyan edilemeyen jenerik satir" kurali ihlal edilir.
GONDERICI_SON = "return; } } };\n"

# 🔴 BEYAZ LISTE (kara liste DEGIL). Kara liste yeni bir kisisel alan adini (ornegin
# `alici_unvani`) SESSIZCE gecirirdi; burada IZINLI kume kanonik e-ticaret alanlarindan
# ibarettir ve disaridaki HER anahtar kirmizidir — yeni alan eklemek bilincli karar olur.
IZINLI_ANAHTAR = frozenset((
    "currency", "value", "items",
    "item_id", "item_name", "item_category", "price", "quantity",
))
# (E) fikstur degerleri: kosumda DOM'a/sepete konan sahte musteri verisi.
PII_FIKSTUR = ("Ahmet Yilmaz", "5551234567", "musteri@example.com",
               "Ornek Mah. 5. Sok. No:3", "Istanbul")

HATALAR = []
OLCULEMEDI = []


def kontrol(kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)
    return bool(kosul)


def olculemedi(mesaj):
    print("  ⚠️  OLCULEMEDI: " + mesaj)
    OLCULEMEDI.append(mesaj)


def _izlenen(kok):
    """git ls-files — evrenin TEK turetim yolu. Basarisizsa OLCULEMEDI (fail-closed)."""
    r = subprocess.run(["git", "-C", kok, "ls-files"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None
    return [s for s in r.stdout.splitlines() if s.strip()]


def _oku(kok, rel):
    yol = os.path.join(kok, rel)
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8", errors="replace") as f:
        return f.read()


def _dilim(metin, bas, son, ad):
    """Kaynaktan CALISAN parcayi keser (kopya tutulmaz). Capa yoksa None."""
    i = metin.find(bas)
    if i == -1:
        return None
    j = metin.find(son, i)
    if j == -1:
        return None
    return metin[i:j + len(son)]


# ------------------------------------------------------------------ (A) YAPISAL
def bolum_a(kok):
    print("\n(a) YAPISAL — olay gondericisi + beyaz liste, ALTI kopyada TEK KAYNAKTAN")
    kaynak = _oku(kok, TEK_KAYNAK)
    if kaynak is None:
        olculemedi("tek kaynak okunamadi: %s" % TEK_KAYNAK)
        return None
    gonderici = _dilim(kaynak, GONDERICI_CAPA, GONDERICI_SON, TEK_KAYNAK)
    if gonderici is None:
        olculemedi("gonderici capasi yok (%s) — %s" % (GONDERICI_CAPA, TEK_KAYNAK))
        return None
    m = re.search(re.escape(BEYAZ_LISTE_CAPA) + r"([^\]]*)\]", kaynak)
    if m is None:
        olculemedi("beyaz liste capasi yok (%s)" % BEYAZ_LISTE_CAPA)
        return None
    beyaz = re.findall(r"'([^']+)'", m.group(1))
    beyaz_satiri = BEYAZ_LISTE_CAPA + m.group(1) + "]"

    kontrol(len(beyaz) >= 3, "beyaz liste dolu: %s" % ", ".join(beyaz))
    kontrol(SUNUCU_TARAFI not in beyaz,
            "cift sayim kapisi: '%s' beyaz listede DEGIL (sunucudan gidiyor)" % SUNUCU_TARAFI)
    bekleyen = sorted(v for k, v in HUNI.items() if v != SUNUCU_TARAFI)
    kontrol(sorted(beyaz) == bekleyen,
            "beyaz liste == huni eslemesinin istemci ayagi (%s)" % ", ".join(bekleyen))
    kontrol("localStorage.getItem('pruvo_onay_analitik') !== 'kabul'" in gonderici,
            "gonderici Meta ile AYNI riza anahtarina bagli (riza yoksa erken doner)")

    for rel in CEKIRDEK_KOPYALARI:
        metin = _oku(kok, rel)
        if metin is None:
            olculemedi("cekirdek kopyasi okunamadi: %s" % rel)
            continue
        kontrol(gonderici in metin and beyaz_satiri in metin,
                "%s — gonderici + beyaz liste BIREBIR tek kaynaktan" % rel)
    return beyaz


# ------------------------------------------------------------------ (B) KAPSAMA
def bolum_b(kok):
    print("\n(b) KAPSAMA — her Meta huni noktasinin GA4 ikizi var mi (evren: izlenen agac)")
    izlenen = _izlenen(kok)
    if izlenen is None:
        olculemedi("git ls-files basarisiz — evren turetilemedi")
        return
    meta_kalip = re.compile(r'pruvoMetaTrack\(\s*"([A-Za-z]+)"')
    ga4_kalip = re.compile(r'pruvoGA4Track\(\s*"([a-z_]+)"')
    meta_yerler, ga4_yerler = {}, {}
    for rel in izlenen:
        if not rel.endswith((".html", ".js", ".py")):
            continue
        metin = _oku(kok, rel)
        if not metin:
            continue
        for ad in meta_kalip.findall(metin):
            meta_yerler.setdefault(ad, set()).add(rel)
        for ad in ga4_kalip.findall(metin):
            ga4_yerler.setdefault(ad, set()).add(rel)
    # Nobetcinin KENDI dosyasi ve kardes surucu evrenden cikar: ornek metinleri
    # gercek cagri noktasi sanilmasin ([[nobetci-kendi-dosyasinda-sizinti]]).
    kendi = {"tools/ga4-olay-kapisi.py", "tools/ga4-olay-mutasyon.py"}
    for d in (meta_yerler, ga4_yerler):
        for ad in list(d):
            d[ad] -= kendi
            if not d[ad]:
                del d[ad]

    if not meta_yerler:
        olculemedi("Meta huni cagri noktasi BULUNAMADI — evren bos, yesil hukum verilmez")
        return
    print("      Meta cagri noktalari: %s" % ", ".join(sorted(meta_yerler)))
    print("      GA4  cagri noktalari: %s" % ", ".join(sorted(ga4_yerler)) or "(yok)")

    for meta_ad in sorted(meta_yerler):
        ga4_ad = HUNI.get(meta_ad)
        if ga4_ad is None:
            kontrol(False, "Meta noktasi '%s' kanonik huni eslemesinde YOK "
                           "(eslemeyi guncelle)" % meta_ad)
            continue
        if ga4_ad == SUNUCU_TARAFI:
            continue
        ortak = meta_yerler[meta_ad] & ga4_yerler.get(ga4_ad, set())
        kontrol(bool(ortak),
                "%s -> %s ikizi AYNI dosyada (%s)"
                % (meta_ad, ga4_ad, ", ".join(sorted(ortak)) or "YOK"))

    # Purchase: istisna ELLE BEYAN DEGIL, uc ayri kanitla olculur.
    sunucu = _oku(kok, SUNUCU_KAYNAK)
    kontrol(bool(sunucu) and 'name: "%s"' % SUNUCU_TARAFI in sunucu,
            "'%s' SUNUCU tarafindan gonderiliyor (kanit: olcum modulunde olay adi)"
            % SUNUCU_TARAFI)
    kontrol(bool(sunucu) and "transaction_id" in sunucu,
            "sunucu olayi transaction_id tasiyor (tekillestirme anahtari)")
    kontrol(SUNUCU_TARAFI not in ga4_yerler,
            "istemcide '%s' GONDERILMIYOR (cift sayim yolu KAPALI)" % SUNUCU_TARAFI)


# ------------------------------------------------------- node kosucusu (turetilen)
KOSUCU_DEPO_CAPA = "const depo = new Map();"
KOSUCU_SON_CAPA = "process.stdout.write(JSON.stringify(sonuc));"

KOSUCU_RIZA_EK = """const depo = new Map();
if (process.argv[4] === "riza") {
  depo.set("pruvo_onay_analitik", "kabul");
  depo.set("pruvo_onay_kapsam", "analitik+reklam");
}
"""

KOSUCU_OLCUM_EK = """/* ---- GA4 olay kuyrugu (dataLayer) — gtag.js'in TUKETTIGI kuyruk ---- */
function kuyruk() {
  const d = ctx.dataLayer || [];
  return d.map((a) => { try { return Array.from(a); } catch (e) { return [a]; } });
}
sonuc.dataLayer = kuyruk();
/* yanlis-pozitif ekseni: beyaz liste DISI ad kuyruga DUSMEMELI */
const oncekiUzunluk = (ctx.dataLayer || []).length;
try { ctx.pruvoGA4Track("purchase", { deneme: true }); } catch (e) {}
sonuc.beyazListeDisiEklendi = (ctx.dataLayer || []).length - oncekiUzunluk;
sonuc.gondericiVar = typeof ctx.pruvoGA4Track === "function";
sonuc.beyazListe = ctx.PRUVO_GA4_OLAYLARI || null;
process.stdout.write(JSON.stringify(sonuc));
"""


def kosucu_kaynagi():
    """Kardes kapinin GERCEK node:vm surucusunu TEK KAYNAK olarak alir ve iki capaya
    olcum ekler. Kopya DOM saplamasi tutulmaz: kardes surucu degisirse bu kapi da
    onunla birlikte degisir ([[ikiz-tanim-sessiz-ayrisma]]). Capa dusrse OLCULEMEDI."""
    yol = os.path.join(TOOLS, "sepet-secim-kapisi.py")
    if not os.path.exists(yol):
        return None, "kardes surucu yok: tools/sepet-secim-kapisi.py"
    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()
    m = re.search(r'NODE_RUNNER\s*=\s*r?"""(.*?)"""', kaynak, re.S)
    if m is None:
        return None, "kardes surucudeki NODE_RUNNER sabiti bulunamadi"
    kosucu = m.group(1)
    if kosucu.count(KOSUCU_DEPO_CAPA) != 1 or kosucu.count(KOSUCU_SON_CAPA) != 1:
        return None, "kardes surucudeki capalar degismis (depo / cikti)"
    kosucu = kosucu.replace(KOSUCU_DEPO_CAPA, KOSUCU_RIZA_EK, 1)
    kosucu = kosucu.replace(KOSUCU_SON_CAPA, KOSUCU_OLCUM_EK, 1)
    return kosucu, None


def sayfa_uret(gecici, pid):
    """Fikstur urununun GERCEK sayfasini uretir (/varlik/ referanslari icerikle doldurulur)."""
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        tum = json.load(f)
    ix = {p["id"]: p for p in tum}
    p = ix.get(pid)
    if not p:
        return None, "fikstur urunu katalogda YOK: %s" % pid
    build.VARLIK_DIR = os.path.join(gecici, "varlik")
    build._VARLIK_ONBELLEK = {}
    havuz = [x for x in tum if x.get("kategori") == p.get("kategori")][:12]
    if p not in havuz:
        havuz = [p] + havuz
    ham = build.render_product(p, havuz, None)
    yol = os.path.join(gecici, pid + ".html")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(yayin_yuzey.govde(ham, gecici))
    return yol, None


def node_kos(gecici, kosucu, sayfa_yolu, riza):
    node = shutil.which("node")
    if not node:
        return None, "node bulunamadi"
    yol = os.path.join(gecici, "ga4-kosucu.js")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kosucu)
    r = subprocess.run([node, yol, ROOT, sayfa_yolu] + (["riza"] if riza else []),
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None, "kosucu dustu (rc=%s): %s" % (r.returncode, (r.stderr or "")[-600:])
    try:
        return json.loads(r.stdout), None
    except ValueError as e:
        return None, "kosucu ciktisi ayristirilamadi: %s" % e


def _ga4_olaylari(dl):
    """dataLayer kuyrugundan GA4 olaylarini ayikla: ['event', <ad>, <parametreler>]."""
    out = []
    for kayit in dl or []:
        if len(kayit) >= 2 and kayit[0] == "event":
            out.append((kayit[1], kayit[2] if len(kayit) > 2 else {}))
    return out


# ------------------------------------------------------------- (C) DAVRANIS · urun
FIKSTUR_URUN = "bmw-kaput-a-ma-kolu"


def bolum_c(gecici, kosucu):
    print("\n(c) DAVRANIS — uretilen GERCEK urun sayfasi node:vm'de kosar; olay kuyrugu olculur")
    sayfa, hata = sayfa_uret(gecici, FIKSTUR_URUN)
    if hata:
        olculemedi(hata)
        return []
    gozlenen = []

    ret, hata = node_kos(gecici, kosucu, sayfa, riza=False)
    if hata:
        olculemedi("riza-YOK kosumu: " + hata)
        return gozlenen
    kontrol(ret.get("gondericiVar") is True, "sayfa gondericiyi tanimliyor (pruvoGA4Track)")
    olaylar = _ga4_olaylari(ret.get("dataLayer"))
    kontrol(not olaylar,
            "RIZA YOK -> sifir GA4 olayi (yanlis-pozitif ekseni; gozlenen: %d)" % len(olaylar))
    kontrol(ret.get("beyazListeDisiEklendi") == 0,
            "RIZA YOK -> beyaz liste disi ad da DUSER")

    ret, hata = node_kos(gecici, kosucu, sayfa, riza=True)
    if hata:
        olculemedi("riza-VAR kosumu: " + hata)
        return gozlenen
    olaylar = _ga4_olaylari(ret.get("dataLayer"))
    adlar = [a for a, _ in olaylar]
    gozlenen.extend(p for _, p in olaylar)
    kontrol("view_item" in adlar,
            "RIZA VAR -> sayfa yuklenince view_item ATESLENDI (kuyrukta: %s)"
            % (", ".join(adlar) or "hicbir sey"))
    kontrol("add_to_cart" in adlar, "RIZA VAR -> sepete ekle tiklamasi add_to_cart ATESLEDI")
    kontrol(ret.get("beyazListeDisiEklendi") == 0,
            "beyaz liste DISI ad ('%s') kuyruga DUSMEDI (cift sayim kapisi)" % SUNUCU_TARAFI)

    urun = ret.get("urun") or {}
    fid = urun.get("fid")
    for ad, par in olaylar:
        if ad not in ("view_item", "add_to_cart"):
            continue
        kalemler = (par or {}).get("items") or []
        kontrol(bool(kalemler) and kalemler[0].get("item_id") == fid,
                "%s kalem kimligi katalog kimligiyle AYNI (item_id=%r, URUN.fid=%r)"
                % (ad, kalemler[0].get("item_id") if kalemler else None, fid))
        kontrol((par or {}).get("currency") == "TRY", "%s para birimi TRY" % ad)

    istemci = ret.get("istemciKurus")
    atc = [p for a, p in olaylar if a == "add_to_cart"]
    if atc and istemci is not None:
        kontrol(abs((atc[0].get("value") or 0) - istemci / 100.0) < 0.005,
                "add_to_cart value == istemcinin GORDUGU tutar (%.2f TL / %s kurus)"
                % (atc[0].get("value") or 0, istemci))
    return gozlenen


# --------------------------------------------------- (D) DAVRANIS · odemeye baslama
ODEME_BAS = "      var icIds = lines.map("
ODEME_SON = 'window.pruvoGA4Track("begin_checkout", gIcVeri); }'


def bolum_d(kok, gecici):
    print("\n(d) DAVRANIS — odemeye baslama noktasi index.html'den KESILIP kosturulur")
    index_metin = _oku(kok, "index.html")
    if index_metin is None:
        olculemedi("index.html okunamadi")
        return []
    parca = _dilim(index_metin, ODEME_BAS, ODEME_SON, "index.html")
    if parca is None:
        olculemedi("odemeye baslama capasi yok (%s ... %s)" % (ODEME_BAS.strip(), ODEME_SON))
        return []
    gonderici = _dilim(index_metin, BEYAZ_LISTE_CAPA, GONDERICI_SON, "index.html")
    if gonderici is None:
        olculemedi("gonderici capasi index.html'de yok")
        return []
    node = shutil.which("node")
    if not node:
        olculemedi("node bulunamadi")
        return []

    surucu = """
const vm = require("node:vm");
const PARCA = %s;
const GONDERICI = %s;
function kos(riza) {
  const kuyruk = [];
  const depo = new Map();
  if (riza) { depo.set("pruvo_onay_analitik", "kabul"); }
  const ctx = {
    localStorage: { getItem: (k) => (depo.has(k) ? depo.get(k) : null),
                    setItem() {}, removeItem() {} },
    gtag: function () { kuyruk.push(Array.from(arguments)); },
    console: { log() {}, warn() {}, error() {} },
    JSON, Math, Date,
    /* Musteri alanlari BILEREK ortamda: sizarsa (E) bolumu gorur. */
    MUSTERI: %s,
    pruvoFeedId: (id) => "FID:" + id,
    cartToplamKurus: (ls) => ls.reduce((t, L) => t + (L.satir.adet * 12500), 0),
    PRUVO_SECENEK: { adetDuzelt: (a) => (Number(a) > 0 ? Math.floor(Number(a)) : 1) },
    lines: [
      { satir: { id: "urun-bir", adet: 2 }, urun: { baslik: "Ornek Parca A", kategori: "Otomobil" } },
      { satir: { id: "urun-iki", adet: 1 }, urun: { baslik: "Ornek Parca B", kategori: "Marin" } },
    ],
    metaKuyrugu: [],
  };
  ctx.window = ctx; ctx.globalThis = ctx;
  ctx.window.pruvoMetaTrack = function (olay, veri) { ctx.metaKuyrugu.push([olay, veri]); };
  vm.createContext(ctx);
  vm.runInContext(GONDERICI, ctx, { filename: "index.html#gonderici" });
  try { vm.runInContext(PARCA, ctx, { filename: "index.html#odeme" }); }
  catch (e) { return { hata: String((e && e.message) || e) }; }
  return { kuyruk, meta: ctx.metaKuyrugu };
}
process.stdout.write(JSON.stringify({ rizasiz: kos(false), rizali: kos(true) }));
""" % (json.dumps(parca), json.dumps("  " + gonderici), json.dumps(list(PII_FIKSTUR)))

    yol = os.path.join(gecici, "ga4-odeme-surucu.js")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(surucu)
    r = subprocess.run([node, yol], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        olculemedi("odeme surucusu dustu (rc=%s): %s" % (r.returncode, (r.stderr or "")[-600:]))
        return []
    try:
        ret = json.loads(r.stdout)
    except ValueError as e:
        olculemedi("odeme surucusu ciktisi ayristirilamadi: %s" % e)
        return []

    rizasiz, rizali = ret.get("rizasiz") or {}, ret.get("rizali") or {}
    if rizasiz.get("hata") or rizali.get("hata"):
        olculemedi("kesilen parca kosmadi: %s"
                   % (rizasiz.get("hata") or rizali.get("hata")))
        return []
    kontrol(not _ga4_olaylari(rizasiz.get("kuyruk")),
            "RIZA YOK -> begin_checkout ATESLENMEDI (yanlis-pozitif ekseni)")
    olaylar = _ga4_olaylari(rizali.get("kuyruk"))
    adlar = [a for a, _ in olaylar]
    kontrol("begin_checkout" in adlar,
            "RIZA VAR -> begin_checkout ATESLENDI (kuyrukta: %s)"
            % (", ".join(adlar) or "hicbir sey"))
    gozlenen = [p for _, p in olaylar]
    bc = [p for a, p in olaylar if a == "begin_checkout"]
    meta = [v for a, v in (rizali.get("meta") or []) if a == "InitiateCheckout"]
    if bc and meta:
        ga4_idler = [k.get("item_id") for k in (bc[0].get("items") or [])]
        meta_idler = meta[0].get("content_ids") or []
        kontrol(ga4_idler == meta_idler,
                "begin_checkout kalem kimlikleri Meta'nin gonderdigiyle BIREBIR (%s)"
                % ", ".join(str(x) for x in ga4_idler))
        kontrol(bc[0].get("value") == meta[0].get("value"),
                "begin_checkout tutari Meta ile AYNI (%s)" % bc[0].get("value"))
        kontrol([k.get("quantity") for k in (bc[0].get("items") or [])] == [2, 1],
                "begin_checkout adetleri satirlardan turedi (2, 1)")
    return gozlenen


# ------------------------------------------------------------- (E) KISISEL VERI
def bolum_e(gozlenen):
    print("\n(e) KISISEL VERI — gozlenen TUM olay parametreleri musteri alanlarina karsi taranir")
    if not gozlenen:
        olculemedi("gozlenen olay parametresi YOK — sizinti hukmu verilemez")
        return
    duz = json.dumps(gozlenen, ensure_ascii=False)
    anahtarlar = set()

    def gez(o):
        if isinstance(o, dict):
            for k, v in o.items():
                anahtarlar.add(k)
                gez(v)
        elif isinstance(o, list):
            for v in o:
                gez(v)

    gez(gozlenen)
    kotu = sorted(k for k in anahtarlar if k not in IZINLI_ANAHTAR)
    kontrol(not kotu, "olay parametreleri kanonik e-ticaret kumesinin ICINDE "
                      "(%d anahtar tarandi%s)"
            % (len(anahtarlar), "" if not kotu else "; izinsiz: " + ", ".join(kotu)))
    sizan = [d for d in PII_FIKSTUR if d in duz]
    kontrol(not sizan, "kosumdaki sahte musteri DEGERLERI olaylara sizmadi (%d fikstur)"
            % len(PII_FIKSTUR))
    print("      taranan anahtarlar: %s" % ", ".join(sorted(anahtarlar)))


# ---------------------------------------------------------------- IC NOBETCI
def _kendini_test():
    """Kapinin KENDI olcum yollari: pozitif tanima izi olmadan yesil hukum verilmez."""
    print("== IC NOBETCI (kapinin kendi yollari) ==")
    tamam = True

    dl = [["js", "x"], ["config", "AW-1"], ["event", "view_item", {"items": [{"item_id": "a"}]}]]
    ol = _ga4_olaylari(dl)
    tamam &= kontrol(ol == [("view_item", {"items": [{"item_id": "a"}]})],
                     "kuyruk ayiklama: yalniz 'event' kayitlari olay sayilir")
    tamam &= kontrol(_ga4_olaylari([["config", "G-1"]]) == [],
                     "kuyruk ayiklama: config/js kaydi olay SAYILMAZ (yanlis-pozitif)")

    tamam &= kontrol("eposta" not in IZINLI_ANAHTAR and
                     "musteri" not in IZINLI_ANAHTAR and
                     "alici_unvani" not in IZINLI_ANAHTAR and
                     {"item_id", "item_name", "currency", "value"} <= IZINLI_ANAHTAR,
                     "izinli anahtar kumesi: katalog alanini gecirir, musteri alanini "
                     "(beyan edilmemis yeni ad dahil) GECIRMEZ")

    tamam &= kontrol(HUNI.get("Purchase") == SUNUCU_TARAFI,
                     "huni eslemesi satin almayi sunucu ayagina baglar")

    kosucu, hata = kosucu_kaynagi()
    tamam &= kontrol(kosucu is not None and "sonuc.dataLayer" in (kosucu or ""),
                     "kardes surucu tek kaynaktan turetildi ve olcum eklendi (%s)"
                     % (hata or "capalar yerinde"))
    return tamam


def main():
    ap = argparse.ArgumentParser(description="GA4 e-ticaret olay kapisi")
    ap.add_argument("--kok", default=ROOT)
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()

    print("=" * 70)
    print("GA4 E-TICARET OLAY KAPISI — huni olaylari FIILEN atesleniyor mu?")
    print("=" * 70)

    if a.kendini_test:
        ok = _kendini_test()
        print("-" * 70)
        print(("SONUC: YESIL ✅ — ic nobetci gecti." if ok and not HATALAR
               else "SONUC: KIRMIZI ❌ — ic nobetci dustu."))
        return YESIL if (ok and not HATALAR) else KIRMIZI

    bolum_a(a.kok)
    bolum_b(a.kok)

    gozlenen = []
    kosucu, hata = kosucu_kaynagi()
    if kosucu is None:
        olculemedi("node:vm surucusu turetilemedi: %s" % hata)
    else:
        gecici = tempfile.mkdtemp(prefix="ga4-olay-")
        try:
            gozlenen.extend(bolum_c(gecici, kosucu))
            gozlenen.extend(bolum_d(a.kok, gecici))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    bolum_e(gozlenen)

    print("-" * 70)
    print("IDDIA: %d kirmizi · %d olculemedi" % (len(HATALAR), len(OLCULEMEDI)))
    if OLCULEMEDI and not HATALAR:
        print("SONUC: OLCULEMEDI ⚠️  — yesil hukum VERILMEZ:")
        for m in OLCULEMEDI:
            print("   · " + m)
        return OLCULEMEDI_RC
    if HATALAR:
        print("SONUC: KIRMIZI ❌ — GA4 huni olayi eksik/atesenmiyor:")
        for m in HATALAR:
            print("   · " + m)
        return KIRMIZI
    print("SONUC: YESIL ✅ — huni olaylari riza kapisinin ARKASINDA fiilen atesleniyor, "
          "kalem kimlikleri Meta ile birebir, kisisel veri 0.")
    return YESIL


if __name__ == "__main__":
    sys.exit(main())
