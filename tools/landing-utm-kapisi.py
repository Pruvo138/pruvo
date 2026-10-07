#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LANDING UTM KAPISI — reklamin son adresi ana sayfa DISINDA bir sayfa (landing / marka /
icerik sayfasi) oldugunda kampanya etiketi (UTM) siparise ULASIYOR MU, halkayi FIILEN
KOSTURARAK olcer.

OLCULEN BASLANGIC DURUMU (7 Eki 2026):
  * UTM yalniz ana sayfada (index.html PRUVO_ATIF.yakala) yakalaniyordu.
  * build.py'nin urettigi landing sayfalarinda UTM yakalayici YOKTU; sepet linki
    (`/?sepet=1`) sorgu dizesini dusurdugu icin etiket ana sayfaya da TASINMIYORDU.
  * Sonuc: reklamin son adresi landing ise `siparisler.atif.utm_campaign` BOS (canlida
    UTM'li siparis 0/87).
ONARIM: attribution-ref.js (HER sayfada yuklenen tek kaynak modul) UTM'i AYNI `pruvo_atif`
anahtarina, AYNI alanlar ve AYNI kirpma ile, mevcut kayitla birlestirerek yazar. Ana sayfa
ile landing ayni origin'dir -> localStorage paylasilir -> ana sayfanin topla()'si okur.

BU KAPI NE YAPAR (jeton taramasi DEGIL — her bacak GERCEK kaynaktan KOSAR):
  L1  GERCEK attribution-ref.js vm'de, landing adresi `?utm_campaign=test-x`, riza YOK
      -> localStorage `pruvo_atif.utm_campaign == test-x`.
  L2  AYNI depoyla GERCEK index.html PRUVO_ATIF dilimi, ana sayfa `/?sepet=1`
      -> topla() govdesinde utm_campaign == test-x.
  L3  O govde GERCEK shop/src/index.js `/baslat` ucuna POST edilir; D1 stub'i
      `INSERT INTO siparisler` bind degerlerini yakalar -> atif JSON'da utm_campaign == test-x
      (atifTemizle beyaz listesinden gecmis hali).
  L4  Riza = ret: L1-L3 AYNI sonuc; ustelik adresteki gclid/fbclid kayda GIRMEZ.
  L5  UTM'siz landing ziyareti mevcut UTM kaydini SILMEZ/DEGISTIRMEZ (riza yok + riza var).
  L6  Ana sayfa <-> landing ESITLIGI: anahtar adi, alan listesi, kirpma sabiti (statik) +
      ayni adres/ayni baslangic deposuyla iki yakalayicinin yazdigi kayit BAYT esit (davranis).

--kendini-test: oldurucu mutantlar (gecici kopyada, repo dosyasina DOKUNMAZ):
  M1 landing yakalayici cagrisi silinir           -> L1 KIRMIZI olmali
  M2 ana sayfa anahtar adi degisir                -> L2 KIRMIZI olmali
  M3 landing anahtar adi degisir                  -> L2 KIRMIZI olmali
  M4 landing kirpma sabiti 120'ye iner            -> L6 KIRMIZI olmali
  K0 mutasyonsuz kopya                            -> TUMU YESIL olmali

FAIL-CLOSED: node yok / dilim kesilemedi / modul import edilemedi -> OLCULEMEDI + exit 3
("yesil" DEGIL). AG YOK: fetch stub'lanir, beklenmeyen ag istegi testi patlatir.
Gecici dosyalar kosum sonunda silinir.

KULLANIM:
    python3 tools/landing-utm-kapisi.py                 # KAPI: kopuksa exit 1
    python3 tools/landing-utm-kapisi.py --kendini-test  # mutantlar + K0
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
INDEX_VARSAYILAN = os.path.join(ROOT, "index.html")
ATTR_VARSAYILAN = os.path.join(ROOT, "attribution-ref.js")
SHOP_INDEX = os.path.join(ROOT, "shop", "src", "index.js")

RC_YESIL = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 3

KOSUCU = r"""
import fs from "node:fs";
import vm from "node:vm";
import { webcrypto } from "node:crypto";
import * as nodeModule from "node:module";
import { pathToFileURL } from "node:url";

const [, , INDEX_HTML, ATTR_JS, SHOP_INDEX] = process.argv;

// shop/src/index.js `../config.json`i attribute'suz import eder; olcum.mjs ile AYNI kanca.
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
  if (i < 0) { throw new Error("dilim BASI bulunamadi: " + bas); }
  const j = metin.indexOf(son, i + 1);
  if (j < 0) { throw new Error("dilim SONU bulunamadi: " + son); }
  return metin.slice(i, j);
}

function kavanoz(ilk) {
  const s = new Map(Object.entries(ilk || {}));
  return {
    getItem: (k) => (s.has(k) ? s.get(k) : null),
    setItem: (k, v) => { s.set(k, String(v)); },
    removeItem: (k) => { s.delete(k); },
    _dok: () => Object.fromEntries(s),
  };
}

const INDEX = fs.readFileSync(INDEX_HTML, "utf8");
const ATIF_SRC = dilim(INDEX, "var PRUVO_ATIF = (function(){", "\n  function placeholder(txt){");
const ATTR_SRC = fs.readFileSync(ATTR_JS, "utf8");

function baglam(depo, arama, yol) {
  const ctx = {
    localStorage: depo,
    location: { search: arama, href: "https://pruvo3d.com" + yol + arama,
                hostname: "pruvo3d.com", pathname: yol },
    document: { cookie: "", referrer: "", readyState: "complete",
                addEventListener() {}, querySelectorAll() { return []; } },
    navigator: {}, crypto: webcrypto, URLSearchParams, URL, console,
    addEventListener() {},
  };
  ctx.window = ctx;
  ctx.globalThis = ctx;
  return ctx;
}

// Landing: yalniz attribution-ref.js (build.py'nin landing/marka/icerik sayfalarina bastigi modul).
function landing(depo, arama) {
  const ctx = baglam(depo, arama, "/ornek-landing/");
  vm.runInNewContext(ATTR_SRC, ctx, { filename: "attribution-ref.js" });
  return ctx;
}
// Ana sayfa: GERCEK PRUVO_ATIF dilimi; ref icin landing modulunun pruvoRef'i tasinabilir.
function anaSayfa(depo, arama) {
  const ctx = baglam(depo, arama, "/");
  vm.runInNewContext(ATIF_SRC + "\n;window.__ATIF = PRUVO_ATIF;", ctx,
                     { filename: "index.html#PRUVO_ATIF" });
  return ctx.__ATIF;
}
function kayit(depo) {
  try { return JSON.parse(depo.getItem("pruvo_atif")) || {}; } catch (e) { return {}; }
}

// ---- sunucu bacagi: gercek worker /baslat, D1 INSERT bind degerleri yakalanir ----
const D1SATIR = { id: "audi-yakit-kapagi", baslik: "Audi Yakit Kapagi",
                  kategori: "Otomobil", fiyat: "850 TL", parametrik: 0, gorsel: "" };
const mod = await import(pathToFileURL(SHOP_INDEX).href);
async function baslat(atif) {
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
  const eski = globalThis.fetch;
  globalThis.fetch = async (hedef) => {
    const u = String(hedef && hedef.url ? hedef.url : hedef);
    if (u.includes("iyzico.test")) {
      return new Response(JSON.stringify({ status: "success", token: "tok",
        paymentPageUrl: "https://odeme.test/s" }),
        { status: 200, headers: { "Content-Type": "application/json" } });
    }
    throw new Error("KAPIDA BEKLENMEYEN AG ISTEGI: " + u);
  };
  let kod = 0;
  try {
    const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sozlesme_onay: true, odeme: "kart",
        musteri: { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
                   adres: "Test mahallesi test sokak no 1", sehir: "Mugla" },
        sepet: [{ id: D1SATIR.id, malzeme: "PLA", renk: "Siyah", adet: 1 }],
        atif,
      }),
    });
    kod = (await mod.default.fetch(istek, env, { waitUntil() {} })).status;
  } finally {
    globalThis.fetch = eski;
  }
  const ins = kayitlar.find((k) => /INSERT INTO siparisler/.test(k.sql));
  let atifJson = null;
  if (ins) {
    for (const a of ins.arg) {
      if (typeof a !== "string" || a[0] !== "{") { continue; }
      try { const o = JSON.parse(a); if (o && typeof o === "object") {
        if ("utm_campaign" in o || "ref" in o || "ga_client_id" in o) { atifJson = o; } } } catch (e) {}
    }
  }
  return { kod, insert: !!ins, atifJson };
}

const R = {};
const TIK = ["fbc", "fbclid", "gclid", "gbraid", "wbraid", "ttclid", "msclkid"];

// ---- L1-L3 riza YOK ----
{
  const depo = kavanoz();
  landing(depo, "?utm_campaign=test-x");
  R.L1 = { depo: kayit(depo) };
  const govde = anaSayfa(depo, "?sepet=1").topla();
  R.L2 = { govde };
  R.L3 = await baslat(govde);
}
// ---- L4 riza = ret (+ adreste click-id) ----
{
  const depo = kavanoz({ pruvo_onay_analitik: "ret" });
  landing(depo, "?utm_campaign=test-x&gclid=GCL-L4&fbclid=FB-L4");
  const k = kayit(depo);
  let ref = null;
  try { ref = JSON.parse(depo.getItem("pruvo_ref")); } catch (e) {}
  const govde = anaSayfa(depo, "?sepet=1").topla();
  R.L4 = { depo: k, tik: TIK.filter((t) => t in k), refGclid: ref ? ref.gclid : null,
           govde, sunucu: await baslat(govde) };
}
// ---- L5 UTM'siz landing mevcut kaydi silmez ----
{
  const ilk = JSON.stringify({ utm_source: "google", utm_campaign: "eski-kampanya" });
  const a = kavanoz({ pruvo_atif: ilk });
  landing(a, "");
  const b = kavanoz({ pruvo_atif: ilk, pruvo_onay_analitik: "kabul" });
  landing(b, "?s=1");
  R.L5 = { ilk, rizasiz: a.getItem("pruvo_atif"), rizali: b.getItem("pruvo_atif") };
}
// ---- L6 davranis esitligi ----
{
  const uzun = "c".repeat(300);
  const senaryolar = [
    { ilk: {}, arama: "?utm_source=a&utm_medium=b&utm_campaign=" + uzun +
      "&utm_id=d&utm_term=t&utm_content=x&gclid=G6" },
    { ilk: { pruvo_atif: JSON.stringify({ utm_source: "eski", utm_medium: "m0" }) },
      arama: "?utm_campaign=yeni" },
    { ilk: { pruvo_atif: JSON.stringify({ utm_source: "eski" }) }, arama: "?utm_source=" },
  ];
  R.L6 = senaryolar.map((s) => {
    const l = kavanoz(s.ilk); landing(l, s.arama);
    const h = kavanoz(s.ilk); anaSayfa(h, s.arama);
    return { arama: s.arama.slice(0, 60), landing: l.getItem("pruvo_atif"),
             ana: h.getItem("pruvo_atif") };
  });
}
process.stdout.write(JSON.stringify(R));
"""


class Olculemedi(Exception):
    pass


def oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise Olculemedi("okunamadi: %s (%s)" % (yol, e))


def node_kos(index_yolu, attr_yolu):
    if not shutil.which("node"):
        raise Olculemedi("node YOK")
    gec = tempfile.mkdtemp(prefix="landing-utm-")
    try:
        kosucu = os.path.join(gec, "kosucu.mjs")
        with open(kosucu, "w", encoding="utf-8") as f:
            f.write(KOSUCU)
        p = subprocess.run(["node", kosucu, index_yolu, attr_yolu, SHOP_INDEX],
                           capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            raise Olculemedi("node kosucusu rc=%d: %s" % (p.returncode, p.stderr.strip()[-600:]))
        try:
            return json.loads(p.stdout)
        except ValueError:
            raise Olculemedi("node ciktisi JSON degil: %r" % p.stdout[:300])
    finally:
        shutil.rmtree(gec, ignore_errors=True)


def js_dizi(metin, ad):
    """`var <ad> = [ ... ];` dizisini JSON olarak cozer (tek/cift tirnak)."""
    i = metin.find("var " + ad + " = [")
    if i < 0:
        raise Olculemedi("dizi bulunamadi: " + ad)
    j = metin.find("];", i)
    govde = metin[metin.find("[", i):j + 1].replace("'", '"')
    try:
        return json.loads(govde)
    except ValueError:
        raise Olculemedi("dizi cozulemedi: " + ad)


def statik_esitlik(index_metni, attr_metni):
    """Ana sayfa <-> landing sabit esitligi. Doner: (tamam, aciklama)."""
    atif = index_metni[index_metni.find("var PRUVO_ATIF = (function(){"):]
    atif = atif[:atif.find("\n  function placeholder(txt){")]
    if not atif:
        raise Olculemedi("PRUVO_ATIF dilimi kesilemedi")
    ana_alan = js_dizi(atif, "UTM_ALANLARI")
    lan_alan = js_dizi(attr_metni, "ATIF_UTM_FIELDS")
    import re
    m_ana_key = re.search(r'var ANAHTAR = "([^"]+)";', atif)
    m_lan_key = re.search(r'var ATIF_KEY = "([^"]+)";', attr_metni)
    m_ana_kirp = re.search(r"utm\[UTM_ALANLARI\[i\]\] = String\(val\)\.slice\(0,\s*(\d+)\)", atif)
    m_lan_kirp = re.search(r"var ATIF_UTM_MAX = (\d+);", attr_metni)
    if not (m_ana_key and m_lan_key and m_ana_kirp and m_lan_kirp):
        raise Olculemedi("anahtar/kirpma sabiti kesilemedi (ana=%s/%s landing=%s/%s)" % (
            bool(m_ana_key), bool(m_ana_kirp), bool(m_lan_key), bool(m_lan_kirp)))
    tamam = (ana_alan == lan_alan and m_ana_key.group(1) == m_lan_key.group(1)
             and m_ana_kirp.group(1) == m_lan_kirp.group(1))
    return tamam, "alan ana=%s landing=%s · anahtar %s/%s · kirpma %s/%s" % (
        ana_alan, lan_alan, m_ana_key.group(1), m_lan_key.group(1),
        m_ana_kirp.group(1), m_lan_kirp.group(1))


def olc(index_yolu, attr_yolu):
    """Doner: (vakalar[(ad, tamam, aciklama)], ham)."""
    index_metni, attr_metni = oku(index_yolu), oku(attr_yolu)
    R = node_kos(index_yolu, attr_yolu)
    V = []
    d1 = R["L1"]["depo"]
    V.append(("L1", d1.get("utm_campaign") == "test-x",
              "landing sonrasi pruvo_atif=%s" % json.dumps(d1, ensure_ascii=False)))
    g2 = R["L2"]["govde"]
    V.append(("L2", g2.get("utm_campaign") == "test-x",
              "ana sayfa topla()=%s" % json.dumps(g2, ensure_ascii=False)))
    s3 = R["L3"]
    a3 = s3.get("atifJson") or {}
    V.append(("L3", s3["kod"] == 200 and s3["insert"] and a3.get("utm_campaign") == "test-x",
              "/baslat kod=%s insert=%s atif=%s" % (s3["kod"], s3["insert"],
                                                    json.dumps(a3, ensure_ascii=False))))
    r4 = R["L4"]
    a4 = r4["sunucu"].get("atifJson") or {}
    tamam4 = (r4["depo"].get("utm_campaign") == "test-x" and not r4["tik"]
              and r4["refGclid"] in (None, "") and r4["govde"].get("utm_campaign") == "test-x"
              and r4["sunucu"]["kod"] == 200 and a4.get("utm_campaign") == "test-x"
              and not any(k in r4["govde"] for k in ("ga_client_id", "fbp", "fbc")))
    V.append(("L4", tamam4, "riza=ret depo=%s tik=%s ref.gclid=%r govde=%s sunucu.atif=%s" % (
        json.dumps(r4["depo"]), r4["tik"], r4["refGclid"], json.dumps(r4["govde"]),
        json.dumps(a4))))
    r5 = R["L5"]
    V.append(("L5", r5["rizasiz"] == r5["ilk"] and r5["rizali"] == r5["ilk"],
              "ilk=%s rizasiz=%s rizali=%s" % (r5["ilk"], r5["rizasiz"], r5["rizali"])))
    st_tamam, st_acik = statik_esitlik(index_metni, attr_metni)
    dav = R["L6"]
    dav_tamam = all(s["landing"] == s["ana"] for s in dav)
    V.append(("L6", st_tamam and dav_tamam, "statik: %s · davranis: %s" % (
        st_acik, "; ".join("%s -> %s" % ("ESIT" if s["landing"] == s["ana"] else "FARKLI",
                                          (s["landing"] or "null")[:80]) for s in dav))))
    return V


def rapor(V, onek=""):
    for ad, tamam, acik in V:
        print("%s%s %s · %s" % (onek, ad, "TAMAM" if tamam else "KIRMIZI", acik))


def kendini_test():
    index_metni, attr_metni = oku(INDEX_VARSAYILAN), oku(ATTR_VARSAYILAN)
    mutantlar = [
        ("M1 landing yakalayici silindi", "attr", "  captureAtifUtm();\n  initialize();",
         "  initialize();", "L1"),
        ("M2 ana sayfa anahtar adi", "index", 'var ANAHTAR = "pruvo_atif";',
         'var ANAHTAR = "pruvo_atif_m2";', "L2"),
        ("M3 landing anahtar adi", "attr", 'var ATIF_KEY = "pruvo_atif";',
         'var ATIF_KEY = "pruvo_atif_m3";', "L2"),
        ("M4 landing kirpma 120", "attr", "var ATIF_UTM_MAX = 200;",
         "var ATIF_UTM_MAX = 120;", "L6"),
        ("K0 mutasyonsuz", None, None, None, None),
    ]
    gec = tempfile.mkdtemp(prefix="landing-utm-mut-")
    sonuc = []
    try:
        for ad, hedef, eski, yeni, beklenen in mutantlar:
            im, am = index_metni, attr_metni
            if hedef == "attr":
                if attr_metni.count(eski) != 1:
                    raise Olculemedi("%s: capa %d kez" % (ad, attr_metni.count(eski)))
                am = attr_metni.replace(eski, yeni)
            elif hedef == "index":
                if index_metni.count(eski) != 1:
                    raise Olculemedi("%s: capa %d kez" % (ad, index_metni.count(eski)))
                im = index_metni.replace(eski, yeni)
            iy, ay = os.path.join(gec, "index.html"), os.path.join(gec, "attribution-ref.js")
            with open(iy, "w", encoding="utf-8") as f:
                f.write(im)
            with open(ay, "w", encoding="utf-8") as f:
                f.write(am)
            V = olc(iy, ay)
            kirmizi = [v[0] for v in V if not v[1]]
            if beklenen is None:
                ok = not kirmizi
            else:
                ok = beklenen in kirmizi
            sonuc.append(ok)
            print("%s %s · KIRMIZI=%s (beklenen %s)" % (
                "OLDURULDU" if (ok and beklenen) else ("TAMAM" if ok else "HAYATTA/HATA"),
                ad, ",".join(kirmizi) or "-", beklenen or "hicbiri"))
    finally:
        shutil.rmtree(gec, ignore_errors=True)
    return all(sonuc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--index", default=INDEX_VARSAYILAN)
    ap.add_argument("--attribution", default=ATTR_VARSAYILAN)
    a = ap.parse_args()
    try:
        if a.kendini_test:
            ok = kendini_test()
            print("HUKUM=%s" % ("YESIL" if ok else "KIRMIZI"))
            return RC_YESIL if ok else RC_KIRMIZI
        V = olc(a.index, a.attribution)
    except Olculemedi as e:
        print("OLCULEMEDI: %s" % e)
        print("HUKUM=OLCULEMEDI")
        return RC_OLCULEMEDI
    rapor(V)
    ok = all(v[1] for v in V)
    print("LANDING_UTM=%s" % ("EVET" if ok else "HAYIR"))
    print("HUKUM=%s" % ("YESIL" if ok else "KIRMIZI"))
    return RC_YESIL if ok else RC_KIRMIZI


if __name__ == "__main__":
    sys.exit(main())
