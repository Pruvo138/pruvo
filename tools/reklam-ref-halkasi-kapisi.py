#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REKLAM ATIF HALKASI KAPISI — "bu siparis hangi reklamdan geldi" sorusunun D1'den
cevaplanabilir KALDIGINI, halkanin HER bacagini FIILEN KOSTURARAK olcer.

OLCULEN BASLANGIC DURUMU (K99, 25 Agu 2026 — iki bagimsiz curutucu + bu kapinin ilk kosumu):
  * `siparisler.atif` canlida DOLU (11 siparisin 9'u) ama icerigi yalniz {ga_client_id, fbp}.
  * `reklam_ref_gclid` tablosu canlida VAR (29 satir) ama KANONIK SEMADA YOKTU
    (`tools/d1-sema.sql`de 0 hit) -> `--sema` gocu ve hicbir kapi onu GORMUYORDU.
  * Ikisi arasinda kurulmus olmasi GEREKEN bag `siparisler.atif->>'ref'` idi ve
    HICBIR kayitta doluymuyordu.

🔴 KOK NEDEN, "kolon yok" DEGILDI — OLCULDU:
  Sunucu tarafi ZATEN HAZIRDI. `shop/src/index.js` atifTemizle `ref`i 30 Tem'den beri
  beyaz-listede tutuyor (REF_KALIBI, fail-closed, kirpma yok) ve `shop/test/olcum.mjs`
  set 28 ("REF HALKASI") o kolu CI'da YESIL olcuyordu. index.js'in kendi yorumu da
  "halka kapali" diyordu. KOPUK BACAK ISTEMCIDEYDI: `index.html` icindeki
  `PRUVO_ATIF.topla()` odeme aninda UTM + (rizali) ga_client_id/fbp/fbc gonderiyor,
  `ref`i HIC gondermiyordu. Yani yesil sunucu testi olu istemci bacagini GIZLIYORDU;
  kod yorumu ("halka kapali") bir OLCUM DEGIL bir IDDIAYDI ([[aracin-teshis-cumlesi-olcum-degil]]).
  Yeni bir kolon eklemek bu kusuru KAPATMAZDI — bos bir kolon daha uretirdi
  ([[ayni-alan-iki-hukum-biri-sessiz]]: ikinci bag anahtari = ikiz tanim).

BU KAPI NE YAPAR (jeton taramasi DEGIL — her adim GERCEKTEN KOSAR):
  1. GERCEK `index.html`ten `PRUVO_ATIF` dilimi kesilip vm'de KOSTURULUR; `topla()`nin
     dondurdugu govde alinir (rizasiz kol + rizali kol AYRI).
  2. O govde, GERCEK `shop/src/index.js` worker'inin `/baslat` ucuna POST edilir; D1
     stub'i worker'in URETTIGI `INSERT INTO siparisler` SQL'ini ve bind degerlerini yakalar.
  3. GERCEK `shop/src/ref.js` `refKaydet()` cagrilir; beacon'in URETTIGI
     `INSERT OR IGNORE INTO reklam_ref_gclid` SQL'i ve bind degerleri yakalanir.
  4. GERCEK `tools/d1-sema.sql`den `siparisler` + `reklam_ref_gclid` CREATE bloklari
     cikarilip bellek-ici sqlite3'e kurulur; (2) ve (3)'teki SQL'ler O SEMADA KOSTURULUR.
     Tablo kanonik semada yoksa sqlite "no such table" der -> KIRMIZI. Worker'in kolon
     listesi semadan ayrismissa INSERT duser -> KIRMIZI.
  5. HALKA SORUSU calistirilir:
        SELECT r.gclid FROM siparisler s
          JOIN reklam_ref_gclid r ON r.ref = json_extract(s.atif,'$.ref')
     Satir donmezse halka KOPUKTUR -> KIRMIZI. Yani kapinin yesili "kolon var" degil,
     "sorunun cevabi GERCEKTEN geliyor" demektir.
  6. TEK KAYNAK: repoda `reklam_ref_gclid` icin IKINCI bir CREATE TABLE olmamali
     (eski `tools/d1-reklam-ref-gclid.sql` silindi; geri gelirse iki tanim sessizce ayrisir).

DAR EKSEN ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]): kapi YALNIZ bu halkaya bakar.
Urun eklemek/silmek, fiyat/gorsel/kategori duzenlemek, ILGISIZ bir tablonun semasini
degistirmek kapiyi KIRMIZI YAKMAZ — `--kendini-test` K0 kolu bunu OLCER.

FAIL-CLOSED: node yok / modul import edilemiyor / sema okunamiyor / sqlite JSON1 yok ->
OLCULEMEDI + exit 3 ("yesil" DEGIL, [[olculemedi-bypass-degil-menzil-daraltmasi]]).

AG YOK: canli D1'e, wrangler'a, iyzico'ya DOKUNULMAZ (fetch stub'lanir; beklenmeyen ag
istegi testi patlatir). Uretilen her gecici dosya kosum sonunda silinir.

KULLANIM:
    python3 tools/reklam-ref-halkasi-kapisi.py                # KAPI (CI): halka kopuksa exit 1
    python3 tools/reklam-ref-halkasi-kapisi.py --kendini-test # oldurucu mutantlar + K0 kontrol
    python3 tools/reklam-ref-halkasi-kapisi.py --sema X --index Y   # fikstur yollari
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SEMA_VARSAYILAN = os.path.join(TOOLS, "d1-sema.sql")
INDEX_VARSAYILAN = os.path.join(ROOT, "index.html")
SHOP_INDEX = os.path.join(ROOT, "shop", "src", "index.js")
REF_JS = os.path.join(ROOT, "shop", "src", "ref.js")

RC_YESIL = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 3

# Halkada tasinan sabitler. REF landing kanonigine (attribution-ref.js REF_RE /
# shop/src/ref.js REF_KALIBI) UYAR; uymayan deger sunucuda fail-closed DUSER ve bu kapi
# halkayi kopuk olcer — yani sabit de dolayli olarak kalibi sinar.
REF_DEGERI = "REF:GS-BYP-A7K2"
GCLID_DEGERI = "Cj0KCQTEST-K99-GCLID"

# ---------------------------------------------------------------- node kosucu
# 🔴 GECICI DOSYA, REPOYA GIRMEZ ([[diskte-iz-birakma-yasagi]]): kosum sonunda silinir.
# Neden ayri bir node sureci: halkanin iki bacagi (index.html dilimi + worker modulu)
# JAVASCRIPT'tir ve KENDI kaynagindan kosmalidir. Python tarafinda taklit edilseydi kapi
# "kodun ne yaptigini" degil "benim kopyamin ne yaptigini" olcerdi.
NODE_KOSUCU = r"""
import fs from "node:fs";
import vm from "node:vm";
import * as nodeModule from "node:module";
import { pathToFileURL } from "node:url";

const [, , INDEX_HTML, SHOP_INDEX, REF_JS, REF_DEGERI, GCLID_DEGERI] = process.argv;

// JSON IMPORT ATTRIBUTE ENJEKSIYONU — shop/src/index.js `../config.json`i esbuild
// desenine gore attribute'suz import eder (wrangler'in ihtiyaci yok, duz node'un VAR).
// Cozum shop/test/olcum.mjs ile AYNI: `module.register` (Node >= 20.6, off-thread loader).
// 🔴 TEK KOD YOLU, surum dali YOK — surum dali "yerelde yesil / CI'da kirmizi" ayrismasi
// uretir. Hook kurulamazsa SUSMAYIZ: throw -> python tarafi OLCULEMEDI (exit 3) der.
const JSON_IMPORT_HOOK =
  "export async function resolve(s, c, n) {" +
  "  const r = await n(s, c);" +
  "  return r.url.endsWith('.json')" +
  "    ? { ...r, format: 'json', importAttributes: { type: 'json' } }" +
  "    : r;" +
  "}";
if (typeof nodeModule.register !== "function") {
  throw new Error("node:module.register YOK (Node >= 20.6 gerekir) — " + process.version);
}
nodeModule.register("data:text/javascript," + encodeURIComponent(JSON_IMPORT_HOOK));

function dilim(metin, bas, son) {
  const i = metin.indexOf(bas);
  if (i < 0) { throw new Error("PRUVO_ATIF dilim BASI bulunamadi"); }
  const j = metin.indexOf(son, i + 1);
  if (j < 0) { throw new Error("PRUVO_ATIF dilim SONU bulunamadi"); }
  return metin.slice(i, j);
}

function kavanoz() {
  const s = new Map();
  return {
    getItem: (k) => (s.has(k) ? s.get(k) : null),
    setItem: (k, v) => { s.set(k, String(v)); },
    removeItem: (k) => { s.delete(k); },
  };
}

// ---- (1) ISTEMCI BACAGI: gercek index.html dilimi vm'de kosar --------------
const INDEX = fs.readFileSync(INDEX_HTML, "utf8");
const ATIF_SRC = dilim(INDEX, "var PRUVO_ATIF = (function(){",
                       "\n  function placeholder(txt){");

const win = { addEventListener() {}, location: { search: "", href: "https://pruvo3d.com/" } };
win.localStorage = kavanoz();
win.window = win;
win.pruvoRef = function () { return REF_DEGERI; };   // yayin kopyasindaki landing modulu
const belge = { cookie: "" };
const ctx = {
  window: win, localStorage: win.localStorage, document: belge, location: win.location,
  URLSearchParams, URL, console, JSON, Object, String, Number, Date, Math, Array, RegExp,
};
ctx.globalThis = ctx;
vm.runInNewContext(ATIF_SRC + "\n;window.__ATIF = PRUVO_ATIF;", ctx,
                   { filename: "index.html#PRUVO_ATIF" });

// RIZA YOK kolu — REF rizadan BAGIMSIZ akmali (tiklama kimligi degil), kimlik alanlari akmamali.
const payloadRizasiz = win.__ATIF.topla();

// RIZA VAR kolu — regresyon nobeti: kimlik alanlari HALA geliyor mu, ref de duruyor mu.
belge.cookie = "_fbp=fb.1.9.9; _ga=GA1.1.111.222";
win.localStorage.setItem("pruvo_onay_analitik", "kabul");
const payloadRizali = win.__ATIF.topla();

// ---- (2) SUNUCU BACAGI: gercek worker /baslat ------------------------------
const D1SATIR = { id: "audi-yakit-kapagi", baslik: "Audi Yakit Kapagi",
                  kategori: "Otomobil", fiyat: "850 TL", parametrik: 0, gorsel: "" };
const kayitlar = [];
const env = {
  SITE_URL: "https://pruvo3d.com", IYZICO_BASE_URL: "https://iyzico.test",
  IYZICO_API_KEY: "test-k", IYZICO_SECRET_KEY: "test-s",
  KATALOG: { prepare(sql) { return { bind(...arg) { return {
    async all() { return { results: arg.filter((x) => x === D1SATIR.id).map(() => D1SATIR) }; },
    async first() { return null; },
    async run() { kayitlar.push({ sql, arg }); return { meta: { changes: 1 } }; },
  }; } }; } },
};

const mod = await import(pathToFileURL(SHOP_INDEX).href);
const eskiFetch = globalThis.fetch;
globalThis.fetch = async (hedef) => {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (u.includes("iyzico.test")) {
    return new Response(JSON.stringify({ status: "success", token: "tok",
      paymentPageUrl: "https://odeme.test/s" }),
      { status: 200, headers: { "Content-Type": "application/json" } });
  }
  throw new Error("KAPIDA BEKLENMEYEN AG ISTEGI: " + u);
};
let baslatKod = 0;
try {
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sozlesme_onay: true, odeme: "kart",
      musteri: { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
                 adres: "Test mahallesi test sokak no 1", sehir: "Mugla" },
      sepet: [{ id: D1SATIR.id, malzeme: "PLA", renk: "Siyah", adet: 1 }],
      atif: payloadRizasiz,
    }),
  });
  baslatKod = (await mod.default.fetch(istek, env, { waitUntil() {} })).status;
} finally {
  globalThis.fetch = eskiFetch;
}
const siparisKaydi = kayitlar.find((k) => /INSERT INTO siparisler/.test(k.sql)) || null;

// ---- (3) BEACON BACAGI: gercek refKaydet ----------------------------------
const refKayitlari = [];
const refEnv = { KATALOG: { prepare(sql) { return { bind(...arg) { return {
  async run() { refKayitlari.push({ sql, arg }); return {}; },
}; } }; } } };
const refMod = await import(pathToFileURL(REF_JS).href);
const refYanit = await refMod.refKaydet(new Request("https://pruvo3d.com/api/shop/ref", {
  method: "POST",
  headers: { "Content-Type": "application/json", "Origin": "https://pruvo3d.com" },
  body: JSON.stringify({ ref: REF_DEGERI, gclid: GCLID_DEGERI, grup: "BYP",
                         src: "GS", ts: 1690000000000 }),
}), refEnv);
const refKaydi = refKayitlari[0] || null;

process.stdout.write(JSON.stringify({
  payloadRizasiz, payloadRizali, baslatKod,
  refKod: refYanit.status,
  siparisSql: siparisKaydi && siparisKaydi.sql,
  siparisArg: siparisKaydi && siparisKaydi.arg,
  refSql: refKaydi && refKaydi.sql,
  refArg: refKaydi && refKaydi.arg,
}));
"""


class Olculemedi(Exception):
    """Olcum kurulamadi — 'yesil' DEGIL (exit 3)."""


def oku(yol):
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise Olculemedi("okunamadi: " + yol + " (" + str(e) + ")")


def create_blok(sema_metni, tablo):
    """d1-sema.sql'den `CREATE TABLE IF NOT EXISTS <tablo> (...);` blogunu dondurur.

    Bulunamazsa None — cagiran onu KURMAZ ve o tabloyu kullanan INSERT sqlite tarafindan
    "no such table" ile reddedilir (hukum ORADA verilir, burada degil).
    """
    m = re.search(r"CREATE TABLE IF NOT EXISTS %s\s*\(.*?\n\);" % re.escape(tablo),
                  sema_metni, re.S)
    return m.group(0) if m else None


def sql_yorumsuz(s):
    """SQL satir yorumlarini atar (sqlite bunlari kabul eder ama gurultu yapar)."""
    return "\n".join(satir for satir in s.splitlines()
                     if not satir.strip().startswith("--"))


def node_kos(index_yolu):
    """Gecici dizinde node kosucusunu calistirip JSON ciktisini dondurur.

    FAIL-CLOSED: node yok / modul import edilemedi / kosucu patladi -> Olculemedi.
    """
    gec = tempfile.mkdtemp(prefix="k99-halka-")
    try:
        kosucu = os.path.join(gec, "halka.mjs")
        with open(kosucu, "w", encoding="utf-8") as f:
            f.write(NODE_KOSUCU)
        try:
            p = subprocess.run(
                ["node", kosucu, index_yolu, SHOP_INDEX, REF_JS, REF_DEGERI, GCLID_DEGERI],
                capture_output=True, text=True, timeout=180, cwd=ROOT)
        except (OSError, subprocess.SubprocessError) as e:
            raise Olculemedi("node kosucusu calistirilamadi: " + str(e))
        if p.returncode != 0:
            raise Olculemedi("node kosucusu rc=" + str(p.returncode) + "\n" +
                             (p.stderr or "").strip()[-1500:])
        try:
            return json.loads(p.stdout)
        except ValueError as e:
            raise Olculemedi("node ciktisi JSON degil (" + str(e) + "): " +
                             (p.stdout or "")[:400])
    finally:
        shutil.rmtree(gec, ignore_errors=True)


def ikinci_tanim_ara():
    """`reklam_ref_gclid` icin d1-sema.sql DISINDA CREATE TABLE tasiyan izlenen dosyalar.

    Bu kapinin KENDI kaynagi ve rapor/paket .md dosyalari haric — onlar tabloyu ANLATIR,
    TANIMLAMAZ. Aranan sey calistirilabilir ikinci DDL'dir.
    """
    bulunan = []
    try:
        p = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True,
                           text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise Olculemedi("git ls-files calistirilamadi: " + str(e))
    if p.returncode != 0:
        raise Olculemedi("git ls-files rc=" + str(p.returncode))
    kalip = re.compile(r"CREATE\s+TABLE(\s+IF\s+NOT\s+EXISTS)?\s+reklam_ref_gclid", re.I)
    for gorece in p.stdout.splitlines():
        if not gorece.endswith(".sql"):
            continue
        if os.path.abspath(os.path.join(ROOT, gorece)) == os.path.abspath(SEMA_VARSAYILAN):
            continue
        tam = os.path.join(ROOT, gorece)
        try:
            with open(tam, "r", encoding="utf-8", errors="replace") as f:
                if kalip.search(f.read()):
                    bulunan.append(gorece)
        except OSError:
            continue
    return bulunan


def kapi(sema_yolu, index_yolu, sessiz=False):
    """Halkanin dort bacagini kosturur. Cikis kodu sozlesmesine uyar."""
    ham = ["REKLAM ATIF HALKASI KAPISI"]
    kirmizi = []

    def iddia(ad, kosul, detay=""):
        if kosul:
            ham.append("  ✅ " + ad)
        else:
            kirmizi.append(ad)
            ham.append("  ❌ " + ad + ("  [" + str(detay)[:300] + "]" if detay else ""))

    try:
        sema_metni = oku(sema_yolu)
        sonuc = node_kos(index_yolu)
    except Olculemedi as e:
        if not sessiz:
            print("REKLAM ATIF HALKASI KAPISI")
            print("  ⚠️ OLCULEMEDI: " + str(e))
            print("-" * 70)
            print("SONUC: OLCULEMEDI ⚠️  — 'yesil' DEGIL (exit " + str(RC_OLCULEMEDI) + ")")
        return RC_OLCULEMEDI

    # ---- (H1..H3) ISTEMCI BACAGI ------------------------------------------
    prz = sonuc.get("payloadRizasiz") or {}
    prl = sonuc.get("payloadRizali") or {}
    iddia("H1 topla() landing REF'ini gonderiyor (RIZA YOKKEN de — REF tik kimligi degil)",
          prz.get("ref") == REF_DEGERI, "rizasiz payload=" + json.dumps(prz))
    iddia("H2 riza yokken KIMLIK alanlari HALA gitmiyor (KVKK regresyonu yok)",
          not any(k in prz for k in ("ga_client_id", "fbp", "fbc")),
          "rizasiz payload=" + json.dumps(prz))
    iddia("H3 riza varken hem REF hem kimlik alanlari gidiyor (rizali kol bozulmadi)",
          prl.get("ref") == REF_DEGERI and prl.get("fbp") == "fb.1.9.9"
          and bool(prl.get("ga_client_id")), "rizali payload=" + json.dumps(prl))

    # ---- (H4) SUNUCU BACAGI ------------------------------------------------
    iddia("H4 /baslat 200 (REF akisi odeme yolunu BOZMUYOR)",
          sonuc.get("baslatKod") == 200, "kod=" + str(sonuc.get("baslatKod")))
    siparis_sql = sonuc.get("siparisSql")
    siparis_arg = sonuc.get("siparisArg")
    atif_ham = siparis_arg[-1] if siparis_arg else None
    try:
        atif = json.loads(atif_ham) if atif_ham else None
    except (TypeError, ValueError):
        atif = None
    iddia("H5 worker `siparisler.atif`e REF'i YAZIYOR (atifTemizle beyaz-listesi tutuyor)",
          isinstance(atif, dict) and atif.get("ref") == REF_DEGERI, "atif=" + str(atif_ham))

    # ---- (H6) BEACON BACAGI ------------------------------------------------
    ref_sql = sonuc.get("refSql")
    ref_arg = sonuc.get("refArg")
    iddia("H6 beacon 204 + `reklam_ref_gclid` INSERT'i URETILDI",
          sonuc.get("refKod") == 204 and bool(ref_sql), "refKod=" + str(sonuc.get("refKod")))

    # ---- (H7..H9) KANONIK SEMA: GERCEK SQL, GERCEK SEMADA -------------------
    db = None
    join_satir = None
    try:
        db = sqlite3.connect(":memory:")
        for tablo in ("siparisler", "reklam_ref_gclid"):
            blok = create_blok(sema_metni, tablo)
            if blok:
                db.executescript(sql_yorumsuz(blok))

        ref_kuruldu = False
        if ref_sql and ref_arg is not None:
            try:
                db.execute(ref_sql, ref_arg)
                ref_kuruldu = True
                ref_hata = ""
            except sqlite3.Error as e:
                ref_hata = str(e)
        else:
            ref_hata = "beacon INSERT'i uretilmedi"
        iddia("H7 beacon INSERT'i KANONIK semada (tools/d1-sema.sql) KOSTU "
              "— tablo kanonda YOKSA burasi 'no such table' ile duser",
              ref_kuruldu, ref_hata)

        siparis_kuruldu = False
        if siparis_sql and siparis_arg is not None:
            try:
                db.execute(siparis_sql, siparis_arg)
                siparis_kuruldu = True
                sip_hata = ""
            except sqlite3.Error as e:
                sip_hata = str(e)
        else:
            sip_hata = "siparis INSERT'i uretilmedi"
        iddia("H8 worker siparis INSERT'i KANONIK semada KOSTU (kolon listesi ayrismamis)",
              siparis_kuruldu, sip_hata)

        # 🔴 ASIL SORU. "Kolon var mi" degil: sorunun cevabi GERCEKTEN geliyor mu.
        if ref_kuruldu and siparis_kuruldu:
            try:
                join_satir = db.execute(
                    "SELECT r.gclid, r.grup, r.src FROM siparisler s "
                    "JOIN reklam_ref_gclid r ON r.ref = json_extract(s.atif, '$.ref')"
                ).fetchall()
                join_hata = ""
            except sqlite3.Error as e:
                join_hata = str(e)
        else:
            join_hata = "onceki bacak kirmizi"
        iddia("H9 HALKA KAPALI — 'bu siparis hangi reklamdan geldi' JOIN'i CEVAP DONDURUYOR",
              bool(join_satir) and len(join_satir) == 1
              and join_satir[0][0] == GCLID_DEGERI,
              join_hata or ("satir=" + str(join_satir)))
    finally:
        if db is not None:
            db.close()

    # ---- (H10) TEK KAYNAK ---------------------------------------------------
    try:
        ikizler = ikinci_tanim_ara()
        iddia("H10 `reklam_ref_gclid` TEK yerde tanimli (d1-sema.sql) — ikiz DDL yok",
              not ikizler, "ikinci tanim: " + ", ".join(ikizler))
    except Olculemedi as e:
        iddia("H10 tek-kaynak taramasi", False, str(e))

    if not sessiz:
        ham.append("-" * 70)
        ham.append("  sema      : " + os.path.relpath(sema_yolu, ROOT))
        ham.append("  istemci   : " + os.path.relpath(index_yolu, ROOT) + " (PRUVO_ATIF.topla)")
        ham.append("  worker    : shop/src/index.js  ·  shop/src/ref.js")
        ham.append("  halka     : topla().ref -> siparisler.atif.ref -> "
                   "json_extract JOIN -> reklam_ref_gclid.gclid")
        print("\n".join(ham))
        print("-" * 70)
        if kirmizi:
            print("SONUC: KIRMIZI ❌ — " + str(len(kirmizi)) + " bacak kopuk: " +
                  "; ".join(kirmizi))
            print("  Halka koparsa reklam harcamasi olculemez: siparis gelir, hangi")
            print("  tiklamadan geldigi D1'den CEVAPLANAMAZ (paid tarafta offline")
            print("  conversion import IMKANSIZ, organik tarafta ROI olculemez).")
        else:
            print("SONUC: YESIL ✅  — halkanin dort bacagi da FIILEN kosturuldu.")
    return RC_KIRMIZI if kirmizi else RC_YESIL


# ---------------------------------------------------------------- kendini test
def _fikstur(gec, sema_donusum=None, index_donusum=None):
    """Gercek dosyalarin KOPYASI (istege bagli mutasyonla). (sema_yolu, index_yolu)."""
    sema = os.path.join(gec, "d1-sema.sql")
    idx = os.path.join(gec, "index.html")
    s = oku(SEMA_VARSAYILAN)
    i = oku(INDEX_VARSAYILAN)
    if sema_donusum:
        s = sema_donusum(s)
    if index_donusum:
        i = index_donusum(i)
    with open(sema, "w", encoding="utf-8") as f:
        f.write(s)
    with open(idx, "w", encoding="utf-8") as f:
        f.write(i)
    return sema, idx


def _tablo_sil(tablo):
    def d(metin):
        blok = create_blok(metin, tablo)
        if not blok:
            raise Olculemedi("MUTASYON CAPASI YOK: CREATE TABLE " + tablo)
        return metin.replace(blok, "")
    return d


def _capa_degistir(capa, yerine):
    def d(metin):
        if metin.count(capa) != 1:
            raise Olculemedi("MUTASYON CAPASI YOK/COK (" + str(metin.count(capa)) +
                             "): " + capa[:60])
        return metin.replace(capa, yerine)
    return d


# 🔴 CAPA IKI SATIRLI: tek satirlik `var ref = ... pruvoRef() ...` capasi index.html'de IKI
# yerde gecer (topla() ve waRefliMetin) -> "capa yok/cok" ile mutant OLCUMSUZ kalirdi
# (ilk kosumda FIILEN oldu, harness bayat bildirdi). Ikinci satir onu tekillestirir.
REF_ATAMASI = "if(ref){ cikti.ref = ref; }"
REF_BLOGU = ('var ref = (typeof window.pruvoRef === "function") ? window.pruvoRef() : "";\n'
             "        " + REF_ATAMASI)
REF_BLOGU_OLU = 'var ref = "";\n        ' + REF_ATAMASI


def kendini_test():
    """OLDURUCU MUTANTLAR + DAR EKSEN KONTROLU.

    Kapinin yesil olmasi tek basina bir sey kanitlamaz ([[kabul-fiksturu-yasagi-kutsar]]):
    her iddianin YUK TASIDIGI, o iddiayi oldurmesi GEREKEN mutantin KIRMIZI yakmasiyla
    olculur. K0 kolu ters yonu olcer — ilgisiz bir degisiklik kapiyi kirmiziya YAKMAMALI.
    """
    ham = ["REKLAM ATIF HALKASI — KENDINI TEST"]
    hata = 0

    vakalar = [
        # (ad, sema_donusum, index_donusum, beklenen_rc)
        ("P0 MUTASYONSUZ TABAN — gercek dosyalar", None, None, RC_YESIL),
        ("MU1 `reklam_ref_gclid` KANONIK SEMADAN SILINDI (K99 oncesi hal)",
         _tablo_sil("reklam_ref_gclid"), None, RC_KIRMIZI),
        ("MU2 istemci REF'i GONDERMIYOR (K99 oncesi topla() hali)",
         None, _capa_degistir(REF_ATAMASI, "if(false){ cikti.ref = ref; }"), RC_KIRMIZI),
        ("MU3 istemci pruvoRef'i HIC CAGIRMIYOR (landing baglantisi kopar)",
         None, _capa_degistir(REF_BLOGU, REF_BLOGU_OLU), RC_KIRMIZI),
        ("MU4 `siparisler` kanonik semadan silindi (kolon listesi ayrismasi sinifi)",
         _tablo_sil("siparisler"), None, RC_KIRMIZI),
        ("K0 KONTROL — ILGISIZ tablo (`talepler`) semadan silindi: kapi YESIL KALMALI "
         "(dar eksen; komsuyu kirmiziya yakmaz)",
         _tablo_sil("talepler"), None, RC_YESIL),
    ]

    for ad, sd, idd, beklenen in vakalar:
        gec = tempfile.mkdtemp(prefix="k99-mut-")
        try:
            try:
                sema, idx = _fikstur(gec, sd, idd)
            except Olculemedi as e:
                hata += 1
                ham.append("  ❌ HARNESS BAYAT: " + ad + " -> " + str(e))
                continue
            rc = kapi(sema, idx, sessiz=True)
            if rc == beklenen:
                ham.append("  ✅ " + ad + " -> rc=" + str(rc))
            else:
                hata += 1
                ham.append("  ❌ " + ad + " -> rc=" + str(rc) + " (beklenen " +
                           str(beklenen) + ")")
        finally:
            shutil.rmtree(gec, ignore_errors=True)

    print("\n".join(ham))
    print("-" * 70)
    if hata:
        print("SONUC: KIRMIZI ❌ — " + str(hata) + " vaka beklenen hukmu vermedi")
        return RC_KIRMIZI
    print("SONUC: YESIL ✅ (kendini test) — " + str(len(vakalar)) +
          " vaka; her oldurucu mutant KIRMIZI, ilgisiz degisiklik YESIL.")
    return RC_YESIL


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true", dest="kendini",
                    help="oldurucu mutantlar + dar eksen (K0) kontrolu")
    ap.add_argument("--sema", default=SEMA_VARSAYILAN)
    ap.add_argument("--index", default=INDEX_VARSAYILAN)
    a = ap.parse_args()
    if a.kendini:
        return kendini_test()
    return kapi(a.sema, a.index)


if __name__ == "__main__":
    sys.exit(main())
