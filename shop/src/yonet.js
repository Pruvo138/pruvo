/**
 * pruvo-shop — anahtar korumali SIPARIS YONETIMI (siparis yonetimi paketi, Faz 1).
 *
 * Uclar (shop worker'a takili; site route'u pruvo3d.com/api/shop/yonet*):
 *   GET  /api/shop/yonet            -> tek dosyalik yonetim SAYFASI (inline HTML/CSS/JS)
 *   GET  /api/shop/yonet/liste      -> JSON siparis listesi (son 50; ?durum= ile suzme)
 *   POST /api/shop/yonet/durum      -> {siparis_no, durum} durum makinesi (izinli gecisler)
 *   POST /api/shop/yonet/kargo      -> {siparis_no, kargo_firma, kargo_kodu} -> 'kargolandi' + e-posta
 *   GET  /api/shop/yonet/stl        -> uretim dosyasi indir (parametrik: derleyici; normal: R2)
 *
 * KIRMIZI CIZGILER (tools/paket-siparis-yonetimi.md):
 *  - Erisim: ?anahtar=<YONET_ANAHTAR> ya da X-Yonet-Anahtar. Anahtar YOK/YANLIS -> 404
 *    (varligi sizmasin). YONET_ANAHTAR secret tanimli DEGILSE tum /yonet* 404 (ozellik kapali).
 *  - Anahtar loglara/HATA metnine YAZILMAZ. PII yalniz anahtarli yanitta. CORS yok (same-origin).
 *  - Gizli kaynak bilgisi (tedarikci/link) sayfaya/JSON'a GIRMEZ.
 *  - 'kargolandi'ya SADECE /kargo ucundan gecilir (takip kodu zorunlu) — tek yol.
 */

import { SEMALAR } from "./semalar.js";
import {
  epostaAkisi, onayEpostasiHtml, kargoEpostasiHtml,
} from "./eposta.js";

// ---- durum makinesi -----------------------------------------------------------
// Sirali ilerleme; her durum -> iptal (asagida ayrica). 'kargolandi' hedefine /durum'dan
// GECILMEZ (takip kodsuz kargolandi olusmasin) — sadece /kargo ucu.
const IZINLI = {
  "odendi": ["uretimde"],
  "uretimde": ["kargolandi"],
  "kargolandi": ["tamamlandi"],
  "havale-bekliyor": ["odendi"],
};
const TUM_DURUMLAR = new Set([
  "bekliyor", "odendi", "basarisiz", "incele", "havale-bekliyor",
  "uretimde", "kargolandi", "tamamlandi", "iptal",
]);

function gecisGecerli(mevcut, hedef) {
  if (!TUM_DURUMLAR.has(hedef)) { return false; }
  if (hedef === "iptal") { return mevcut !== "iptal"; } // her durum -> iptal
  return (IZINLI[mevcut] || []).includes(hedef);
}

// ---- malzeme bazli baski fallback (filament rehberi degerleri; UYDURMA YOK) ---
// Kaynak: tools/paket-filament-rehberi.md isi dayanimi araliklari + gizli kayitlardaki
// ortak duvar/doluluk deseni ("wall line count 6-8, %15 infill"). Genel BASLANGIC onerisi;
// urune ozel oneri gizli .urun-kaynaklari.json'dan D1 baski kolonuna gelir (o varsa bu kullanilmaz).
const BASKI_FALLBACK = {
  "PLA": "Genel öneri: 0.2 mm katman · %15 doluluk · 4-5 duvar hattı · ısı dayanımı ~55-60°C (iç mekân).",
  "PETG": "Genel öneri: 0.2 mm katman · %15-20 doluluk · 4-6 duvar hattı · ısı dayanımı ~70-75°C (genel amaçlı).",
  "ASA": "Genel öneri: 0.2 mm katman · %20 doluluk · 5-6 duvar hattı · ısı dayanımı ~90-95°C (UV/su, dış mekân).",
  "TPU": "Genel öneri: 0.2 mm katman · %15 doluluk · 3-4 duvar hattı · esnek; yavaş baskı önerilir.",
};

function baskiOnerisi(satir, d1Baski, sema) {
  if (d1Baski && d1Baski.trim() && d1Baski.trim() !== "-") { return d1Baski.trim(); }
  if (sema && (sema.baski || sema.baskiIpucu)) { return sema.baski || sema.baskiIpucu; }
  return BASKI_FALLBACK[satir.malzeme] || "Malzemeye uygun genel baskı ayarlarıyla üretilir.";
}

// ---- anahtar ------------------------------------------------------------------

/** Sabit-zamanli string esitligi (erken donus zamanlama sizintisini onler). */
function sabitEsit(a, b) {
  a = String(a || ""); b = String(b || "");
  if (a.length !== b.length) { return false; }
  let fark = 0;
  for (let i = 0; i < a.length; i++) { fark |= a.charCodeAt(i) ^ b.charCodeAt(i); }
  return fark === 0;
}

/** Anahtar gecerli mi? Secret tanimsizsa DAIMA false (ozellik kapali; 404). */
function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  const verilen = request.headers.get("X-Yonet-Anahtar") ||
    url.searchParams.get("anahtar") || "";
  return sabitEsit(verilen, env.YONET_ANAHTAR);
}

// ---- yanit yardimcilari (CORS YOK — yonetim same-origin) ----------------------

function yjson(veri, kod) {
  return new Response(JSON.stringify(veri), {
    status: kod || 200,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}
function yon404() { return yjson({ hata: "bulunamadi" }, 404); }

// ---- /liste -------------------------------------------------------------------

async function liste(env, url) {
  const durum = url.searchParams.get("durum") || "";
  const limit = Math.min(200, Math.max(1, parseInt(url.searchParams.get("limit") || "50", 10) || 50));
  const secim =
    "SELECT id, siparis_no, tarih, durum, tutar_kurus, kargo_kurus, kdv_kurus, odeme_yontemi," +
    " urunler, kargo_firma, kargo_kodu, durum_gecmisi," +
    " musteri_ad, musteri_tel, musteri_eposta, musteri_adres FROM siparisler";
  const stmt = durum
    ? env.KATALOG.prepare(secim + " WHERE durum = ? ORDER BY id DESC LIMIT ?").bind(durum, limit)
    : env.KATALOG.prepare(secim + " ORDER BY id DESC LIMIT ?").bind(limit);
  const sonuc = await stmt.all();
  const satirlar = sonuc.results || [];

  // Satir urun id'lerinin D1 baski/parametrik kayitlarini topla (baski fisi zenginlestirme).
  const idKume = new Set();
  const cozulmus = satirlar.map((s) => {
    let urunler = [];
    try { urunler = JSON.parse(s.urunler) || []; } catch (e) { urunler = []; }
    for (const k of urunler) { if (k && k.id) { idKume.add(k.id); } }
    return { satir: s, urunler };
  });
  const baskiMap = new Map();
  if (idKume.size) {
    const idler = [...idKume];
    const yertut = idler.map(() => "?").join(",");
    const ur = await env.KATALOG.prepare(
      "SELECT id, baski, parametrik FROM urunler WHERE id IN (" + yertut + ")"
    ).bind(...idler).all();
    for (const u of (ur.results || [])) { baskiMap.set(u.id, u); }
  }

  const cikti = cozulmus.map(({ satir: s, urunler }) => {
    const kalemler = urunler.map((k, i) => {
      const ur = baskiMap.get(k.id) || {};
      const sema = SEMALAR.get(k.id);
      const parametrik = !!(k.parametreler || ur.parametrik);
      const kayit = {
        kalem: i,
        id: k.id,
        baslik: k.baslik || "",
        malzeme: k.malzeme || "",
        renk: k.renk_ozel || k.renk || "",
        adet: k.adet || 1,
        parametrik: parametrik,
        parametre_detay: k.parametre_detay || "",
        baski_oneri: baskiOnerisi(k, ur.baski, sema),
      };
      // Yerel yazdir.py + tarayici indirme uclari (anahtar sayfa URL'inden eklenir).
      if (parametrik) {
        // Sari: siparisteki parametrelerle derleyiciden uretim.
        kayit.stl_ucu = "/api/shop/yonet/stl?siparis_no=" +
          encodeURIComponent(s.siparis_no) + "&kalem=" + i;
      } else {
        // Normal: COK-PARCA — once liste, sonra parca basina /stl?id=&dosya=.
        kayit.stl_liste_ucu = "/api/shop/yonet/stl-liste?id=" + encodeURIComponent(k.id);
      }
      return kayit;
    });
    let gecmis = [];
    try { gecmis = JSON.parse(s.durum_gecmisi) || []; } catch (e) { gecmis = []; }
    return {
      siparis_no: s.siparis_no,
      tarih: s.tarih,
      durum: s.durum,
      odeme_yontemi: s.odeme_yontemi,
      tutar_kurus: s.tutar_kurus,
      kargo_kurus: s.kargo_kurus,
      kdv_kurus: s.kdv_kurus,
      kargo_firma: s.kargo_firma || "",
      kargo_kodu: s.kargo_kodu || "",
      durum_gecmisi: gecmis,
      izinli_gecisler: [...(IZINLI[s.durum] || []), ...(s.durum !== "iptal" ? ["iptal"] : [])],
      musteri: { ad: s.musteri_ad, tel: s.musteri_tel, eposta: s.musteri_eposta,
                 adres: s.musteri_adres },
      kalemler: kalemler,
      // Yerel araç (Faz 2) komutu — sayfadaki "kopyala" düğmesi bunu panoya yazar.
      yazdir_komut: "python3 tools/yazdir.py " + s.siparis_no,
    };
  });
  return yjson({ siparisler: cikti }, 200);
}

// ---- durum gecmisi yardimci ---------------------------------------------------

function gecmiseEkle(mevcutJson, hedef) {
  let g = [];
  try { g = JSON.parse(mevcutJson) || []; } catch (e) { g = []; }
  if (!Array.isArray(g)) { g = []; }
  g.push({ d: hedef, z: new Date().toISOString() });
  if (g.length > 50) { g = g.slice(-50); } // sinirla (same-row buyumesin)
  return JSON.stringify(g);
}

async function siparisGetir(env, siparisNo) {
  return env.KATALOG.prepare(
    "SELECT siparis_no, durum, durum_gecmisi, urunler, tutar_kurus, kargo_kurus, kdv_kurus," +
    " musteri_ad, musteri_eposta, musteri_adres FROM siparisler WHERE siparis_no = ?"
  ).bind(siparisNo).first();
}

// ---- /durum -------------------------------------------------------------------

async function durumDegistir(request, env) {
  let govde;
  try { govde = await request.json(); } catch (e) { return yjson({ hata: "gecersiz-json" }, 400); }
  const siparisNo = govde && typeof govde.siparis_no === "string" ? govde.siparis_no : "";
  const hedef = govde && typeof govde.durum === "string" ? govde.durum : "";
  if (!siparisNo || !hedef) { return yjson({ hata: "eksik-alan" }, 400); }
  if (!TUM_DURUMLAR.has(hedef)) { return yjson({ hata: "bilinmeyen-durum" }, 400); }
  // 'kargolandi' tek yoldan: /kargo (takip kodu zorunlu). /durum'dan reddedilir.
  if (hedef === "kargolandi") { return yjson({ hata: "kargo-ucunu-kullan" }, 400); }

  const s = await siparisGetir(env, siparisNo);
  if (!s) { return yjson({ hata: "siparis-yok" }, 404); }
  if (!gecisGecerli(s.durum, hedef)) {
    return yjson({ hata: "gecersiz-gecis", mevcut: s.durum, hedef: hedef }, 400);
  }
  const yeniGecmis = gecmiseEkle(s.durum_gecmisi, hedef);
  const g = await env.KATALOG.prepare(
    "UPDATE siparisler SET durum = ?, durum_gecmisi = ? WHERE siparis_no = ? AND durum = ?"
  ).bind(hedef, yeniGecmis, siparisNo, s.durum).run();
  if (!(g.meta && g.meta.changes > 0)) {
    return yjson({ hata: "durum-degismis", mevcut: s.durum }, 409);
  }
  return yjson({ ok: true, siparis_no: siparisNo, durum: hedef }, 200);
}

// ---- /kargo -------------------------------------------------------------------

async function kargo(request, env, ctx, telegram) {
  let govde;
  try { govde = await request.json(); } catch (e) { return yjson({ hata: "gecersiz-json" }, 400); }
  const siparisNo = govde && typeof govde.siparis_no === "string" ? govde.siparis_no : "";
  const firma = govde && typeof govde.kargo_firma === "string" ? govde.kargo_firma.trim() : "";
  const kod = govde && typeof govde.kargo_kodu === "string" ? govde.kargo_kodu.trim() : "";
  if (!siparisNo) { return yjson({ hata: "eksik-alan" }, 400); }
  if (!firma || firma.length > 80) { return yjson({ hata: "kargo-firma" }, 400); }
  if (!kod || kod.length > 80) { return yjson({ hata: "kargo-kodu" }, 400); }

  const s = await siparisGetir(env, siparisNo);
  if (!s) { return yjson({ hata: "siparis-yok" }, 404); }
  if (!gecisGecerli(s.durum, "kargolandi")) {
    return yjson({ hata: "gecersiz-gecis", mevcut: s.durum, hedef: "kargolandi" }, 400);
  }
  const yeniGecmis = gecmiseEkle(s.durum_gecmisi, "kargolandi");
  const g = await env.KATALOG.prepare(
    "UPDATE siparisler SET durum = 'kargolandi', kargo_firma = ?, kargo_kodu = ?," +
    " durum_gecmisi = ? WHERE siparis_no = ? AND durum = ?"
  ).bind(firma, kod, yeniGecmis, siparisNo, s.durum).run();
  if (!(g.meta && g.meta.changes > 0)) {
    return yjson({ hata: "durum-degismis", mevcut: s.durum }, 409);
  }

  // Kargo e-postasi (tetik 2) — ctx.waitUntil: yanit bloklanmaz, hata siparisi dusurmez.
  let satirlar = [];
  try { satirlar = JSON.parse(s.urunler) || []; } catch (e) { satirlar = []; }
  if (s.musteri_eposta) {
    const html = kargoEpostasiHtml(s, satirlar, firma, kod);
    ctx.waitUntil(epostaAkisi(env, telegram, siparisNo, [
      { kime: s.musteri_eposta, konu: "Siparişiniz kargoda — " + siparisNo,
        html: html, etiket: "müşteri-kargo" },
    ]));
  }
  return yjson({ ok: true, siparis_no: siparisNo, durum: "kargolandi",
                 kargo_firma: firma, kargo_kodu: kod }, 200);
}

// ---- /stl + /stl-liste (COK-PARCA tasarimi — mimar duzeltme turu) ---------------
// R2 duzeni: stl/<urun-id>/<parca-adi> (bir urunun BIRDEN COK parca dosyasi olabilir —
// norm bu; tools/stl-r2-yukle.py tek adlilari da stl/<id>/<id>.stl'e normalize eder).
// ZIP YOK: 280 MB'lik dosyalar var, worker'da sikistirma yapilmaz — parcalar tek tek iner.

function tirnaksiz(s) { return String(s || "").replace(/["\r\n]/g, ""); }

const IZINLI_UZANTI = /\.(stl|3mf)$/i;

/** Urunun R2'deki parca dosyalari: [{dosya, boyut}]. */
async function parcalariListele(env, urunId) {
  const liste = await env.OZEL_DOSYA.list({ prefix: "stl/" + urunId + "/" });
  return (liste.objects || []).map((o) => ({
    dosya: o.key.slice(("stl/" + urunId + "/").length),
    boyut: o.size,
  })).filter((p) => p.dosya);
}

/** GET /yonet/stl-liste?id= -> {id, parcalar:[{dosya,boyut}], not?} */
async function stlListe(env, url) {
  const urunId = url.searchParams.get("id") || "";
  if (!/^[a-z0-9-]{1,120}$/.test(urunId)) { return yjson({ hata: "gecersiz-id" }, 400); }
  if (!env.OZEL_DOSYA) { return yjson({ hata: "r2-baglanti-yok" }, 503); }
  const parcalar = await parcalariListele(env, urunId);
  const govde = { id: urunId, parcalar: parcalar };
  if (!parcalar.length) {
    govde.not = "dosya R2 stl/ prefix'inde yok — stl/ klasörü / Drive / gizli kaynak " +
      "kaydına bak (id: " + urunId + ")";
  }
  return yjson(govde, 200);
}

/** GET /yonet/stl?id=&dosya=[&siparis_no=]  -> tek parca stream (normal urun)
 *  GET /yonet/stl?siparis_no=&kalem=N       -> SARI satir: derleyiciden uret (DEGISMEDI)
 *  Dosya adi dogrulamasi: R2 listesinde OLMAYAN ad 404 (path traversal yolu yok). */
async function stlIndir(env, url) {
  const siparisNo = url.searchParams.get("siparis_no") || "";
  const idParam = url.searchParams.get("id") || "";
  const dosyaParam = url.searchParams.get("dosya") || "";

  // --- Normal urun parcasi: id + dosya ---
  if (idParam && dosyaParam) {
    if (!/^[a-z0-9-]{1,120}$/.test(idParam)) { return yjson({ hata: "gecersiz-id" }, 400); }
    if (!env.OZEL_DOSYA) { return yjson({ hata: "r2-baglanti-yok" }, 503); }
    // Savunma 1: ayirac/ust-dizin icermesin; uzanti .stl|.3mf olsun.
    if (dosyaParam.includes("/") || dosyaParam.includes("\\") ||
        dosyaParam.includes("..") || !IZINLI_UZANTI.test(dosyaParam)) {
      return yjson({ hata: "dosya-yok" }, 404);
    }
    // Savunma 2 (spec): LISTEDE olmayan ad 404 — anahtar dogrudan kurulup GET edilmez.
    const parcalar = await parcalariListele(env, idParam);
    const parca = parcalar.find((p) => p.dosya === dosyaParam);
    if (!parca) {
      return yjson({
        hata: "dosya-yok",
        not: "dosya R2 stl/" + idParam + "/ altinda yok — stl/ klasörü / Drive / gizli " +
          "kaynak kaydına bak (id: " + idParam + ")",
      }, 404);
    }
    const nesne = await env.OZEL_DOSYA.get("stl/" + idParam + "/" + parca.dosya);
    if (!nesne) { return yjson({ hata: "dosya-yok" }, 404); }
    const indirmeAdi = (siparisNo ? tirnaksiz(siparisNo) + "-" : "") + tirnaksiz(parca.dosya);
    return new Response(nesne.body, {
      status: 200,
      headers: {
        "Content-Type": /\.3mf$/i.test(parca.dosya) ? "model/3mf" : "application/octet-stream",
        "Content-Disposition": "attachment; filename=\"" + indirmeAdi + "\"",
        "Cache-Control": "no-store",
      },
    });
  }

  // --- Siparis kalemi yolu (sari uretim; normal kalem parca listesine yonlendirilir) ---
  const kalemStr = url.searchParams.get("kalem");
  const s = await env.KATALOG.prepare(
    "SELECT siparis_no, urunler FROM siparisler WHERE siparis_no = ?"
  ).bind(siparisNo).first();
  if (!s) { return yjson({ hata: "siparis-yok" }, 404); }
  let satirlar = [];
  try { satirlar = JSON.parse(s.urunler) || []; } catch (e) { satirlar = []; }
  let satir = null;
  if (kalemStr != null && kalemStr !== "") {
    const i = parseInt(kalemStr, 10);
    satir = (Number.isInteger(i) && i >= 0) ? satirlar[i] || null : null;
  }
  if (!satir) { return yjson({ hata: "kalem-yok" }, 404); }
  const urunId = satir.id;

  // Parametrik (sari): onizleme derleyicisinden URET (anahtar korumali ic uc; musteri
  // kotasini yemez, gzip'siz ham STL). Onizleme worker'i ayni zone'dan cagrilir.
  if (satir.parametreler && SEMALAR.has(urunId)) {
    const taban = (env.ONIZLEME_TABAN || env.SITE_URL || "https://pruvo3d.com").replace(/\/$/, "");
    let c;
    try {
      c = await fetch(taban + "/api/onizleme/ic-derle", {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   "X-Ic-Anahtar": env.IC_DERLE_ANAHTAR || "" },
        body: JSON.stringify({ aile: urunId, parametreler: satir.parametreler }),
      });
    } catch (e) {
      return yjson({ hata: "derleyici-ulasilamiyor" }, 502);
    }
    if (c.status !== 200) {
      let h = "derleme-hatasi";
      try { h = ((await c.json()) || {}).hata || h; } catch (e) { /* jenerik */ }
      return yjson({ hata: h }, c.status < 500 ? c.status : 502);
    }
    return new Response(c.body, {
      status: 200,
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": "attachment; filename=\"" +
          tirnaksiz(siparisNo + "-" + urunId) + ".stl\"",
        "Cache-Control": "no-store",
      },
    });
  }

  // Normal kalem: parca listesi ucu kullanilir (bir urunun birden cok dosyasi olabilir).
  return yjson({ hata: "parca-listesi-kullan",
                 stl_liste_ucu: "/api/shop/yonet/stl-liste?id=" + urunId }, 400);
}

// ---- yonetim sayfasi (tek dosya, inline) --------------------------------------

function sayfa() {
  return new Response(SAYFA_HTML, {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

// ---- giris (index.js buraya yonlendirir) --------------------------------------

/**
 * /yonet* yonlendirici. altYol = "/", "/liste", "/durum", "/kargo", "/stl".
 * Anahtar YOK/YANLIS -> 404 (varlik sizmasin). telegram: index.js'in telegram fonksiyonu.
 */
export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!anahtarGecerli(request, url, env)) { return yon404(); }
  const m = request.method;
  if (altYol === "/" && m === "GET") { return sayfa(); }
  if (altYol === "/liste" && m === "GET") { return liste(env, url); }
  if (altYol === "/durum" && m === "POST") { return durumDegistir(request, env); }
  if (altYol === "/kargo" && m === "POST") { return kargo(request, env, ctx, telegram); }
  if (altYol === "/stl" && m === "GET") { return stlIndir(env, url); }
  if (altYol === "/stl-liste" && m === "GET") { return stlListe(env, url); }
  return yon404();
}

// Sayfa HTML en altta (okunurluk): mobil uyumlu, lacivert/gri, harici kutuphane YOK.
const SAYFA_HTML = `<!doctype html><html lang="tr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>PRUVO — Sipariş Yönetimi</title>
<style>
:root{--lacivert:#12294d;--gri:#f3f4f6;--kenar:#e5e7eb;--kirmizi:#b91c1c;--sari:#f59e0b}
*{box-sizing:border-box}
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--gri);color:#1f2937;font-size:15px}
header{background:var(--lacivert);color:#fff;padding:12px 16px;position:sticky;top:0;z-index:5;
 display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
header h1{font-size:18px;margin:0}
header .araclar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
select,button,input{font-size:15px;padding:7px 10px;border:1px solid var(--kenar);border-radius:6px}
button{background:var(--lacivert);color:#fff;border:0;cursor:pointer}
button.sil{background:var(--kirmizi)}
button.ikincil{background:#6b7280}
main{padding:12px;max-width:960px;margin:0 auto}
.kart{background:#fff;border:1px solid var(--kenar);border-radius:10px;padding:14px;margin:0 0 14px}
.ust{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:center}
.no{font-weight:bold;font-size:16px;color:var(--lacivert)}
.rozet{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:bold;
 background:#e5edff;color:var(--lacivert)}
.rozet.kargolandi{background:#dbeafe;color:#1e40af}
.rozet.tamamlandi{background:#dcfce7;color:#166534}
.rozet.iptal{background:#fee2e2;color:#991b1b}
.rozet.havale-bekliyor{background:#fef9c3;color:#854d0e}
.mus{font-size:14px;color:#374151;margin:8px 0}
.satir{border:1px solid var(--kenar);border-radius:8px;padding:10px;margin:8px 0;background:#fafafa}
.filrenk{font-size:17px;font-weight:bold;color:var(--lacivert)}
.filrenk .renk{color:#b45309}
.baski{font-size:13px;color:#374151;background:#fff7ed;border-left:3px solid var(--sari);
 padding:6px 8px;margin:6px 0;border-radius:4px}
.eylemler{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.kargoform{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.kucuk{font-size:12px;color:#6b7280}
.hata{color:var(--kirmizi)}
a.indir{display:inline-block;padding:6px 10px;background:#374151;color:#fff;border-radius:6px;
 text-decoration:none;font-size:13px}
.yok{font-size:12px;color:#92400e;background:#fef3c7;padding:4px 8px;border-radius:4px}
.gecmis{font-size:12px;color:#6b7280;margin-top:6px}
</style></head><body>
<header>
 <h1>PRUVO Sipariş Yönetimi</h1>
 <div class="araclar">
  <select id="durumSuzgec">
   <option value="">Tümü</option>
   <option value="odendi">Ödendi</option>
   <option value="havale-bekliyor">Havale bekliyor</option>
   <option value="uretimde">Üretimde</option>
   <option value="kargolandi">Kargolandı</option>
   <option value="tamamlandi">Tamamlandı</option>
   <option value="incele">İncele</option>
   <option value="iptal">İptal</option>
  </select>
  <button id="yenile">Yenile</button>
 </div>
</header>
<main id="liste"><p>Yükleniyor…</p></main>
<script>
var ANAHTAR=new URLSearchParams(location.search).get("anahtar")||"";
function esc(s){s=(s==null?"":""+s);return s.replace(/&/g,"&amp;").replace(/</g,"&lt;")
 .replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function tl(k){k=Math.max(0,Math.floor(+k||0));var t=Math.floor(k/100),ku=(""+(k%100)).padStart(2,"0");
 return (""+t).replace(/\\B(?=(\\d{3})+(?!\\d))/g,".")+","+ku+" TL";}
async function api(yol,secenek){
 secenek=secenek||{};secenek.headers=Object.assign({"X-Yonet-Anahtar":ANAHTAR},secenek.headers||{});
 var c=await fetch("/api/shop/yonet"+yol,secenek);
 var v=null;try{v=await c.json();}catch(e){}
 return {kod:c.status,govde:v};
}
function durumRozet(d){return '<span class="rozet '+esc(d)+'">'+esc(d)+'</span>';}
function satirHtml(no,k){
 var indir;
 if(k.parametrik){
  indir='<a class="indir" href="/api/shop/yonet/stl?siparis_no='+encodeURIComponent(no)+
   '&kalem='+k.kalem+'&anahtar='+encodeURIComponent(ANAHTAR)+'">STL üret + indir</a>';
 }else{
  // COK-PARCA: dugme parca listesini ceker, parcalar tek tek indirilir (zip yok).
  var kutuId='parca-'+no+'-'+k.kalem;
  indir='<button class="ikincil" onclick="parcalar(\\''+esc(no)+'\\',\\''+esc(k.id)+
   '\\',\\''+kutuId+'\\')">Üretim dosyaları</button>'+
   '<span id="'+kutuId+'"></span>';
 }
 return '<div class="satir">'+
  '<div class="filrenk">'+esc(k.malzeme)+' · <span class="renk">'+esc(k.renk)+'</span>'+
  ' × '+esc(k.adet)+'</div>'+
  '<div>'+esc(k.baslik)+(k.parametre_detay?' <span class="kucuk">['+esc(k.parametre_detay)+']</span>':'')+'</div>'+
  '<div class="baski">🖨️ '+esc(k.baski_oneri)+'</div>'+
  indir+' <span class="kucuk">id: '+esc(k.id)+'</span>'+
  '</div>';
}
function boyutMetni(b){
 if(!(b>0))return "";
 if(b>=1048576)return " ("+(b/1048576).toFixed(1)+" MB)";
 if(b>=1024)return " ("+Math.round(b/1024)+" KB)";
 return " ("+b+" B)";
}
async function parcalar(no,id,kutuId){
 var kutu=document.getElementById(kutuId);
 kutu.innerHTML=' yükleniyor…';
 var r=await api("/stl-liste?id="+encodeURIComponent(id));
 if(r.kod!==200){kutu.innerHTML=' <span class="hata">liste alınamadı ('+r.kod+')</span>';return;}
 var p=(r.govde&&r.govde.parcalar)||[];
 if(!p.length){
  kutu.innerHTML=' <span class="yok">'+esc((r.govde&&r.govde.not)||"dosya yok")+'</span>';
  return;
 }
 kutu.innerHTML=" "+p.map(function(x){
  return '<a class="indir" style="margin:2px 4px 2px 0" href="/api/shop/yonet/stl?id='+
   encodeURIComponent(id)+'&dosya='+encodeURIComponent(x.dosya)+
   '&siparis_no='+encodeURIComponent(no)+'&anahtar='+encodeURIComponent(ANAHTAR)+'">'+
   esc(x.dosya)+esc(boyutMetni(x.boyut))+'</a>';
 }).join("");
}
function kartHtml(s){
 var kalem=s.kalemler.map(function(k){return satirHtml(s.siparis_no,k);}).join("");
 var eylem=s.izinli_gecisler.map(function(d){
  if(d==="kargolandi")return "";
  var cls=d==="iptal"?"sil":"";
  return '<button class="'+cls+'" onclick="durumDegis(\\''+s.siparis_no+'\\',\\''+d+'\\')">'+esc(d)+'</button>';
 }).join("");
 var kargoForm="";
 if(s.durum==="uretimde"){
  kargoForm='<div class="kargoform">'+
   '<input id="kf-'+s.siparis_no+'" placeholder="Kargo firması">'+
   '<input id="kk-'+s.siparis_no+'" placeholder="Takip kodu">'+
   '<button onclick="kargoGonder(\\''+s.siparis_no+'\\')">Kargolandı olarak işaretle</button></div>';
 }
 var kargoBilgi=s.kargo_kodu?'<div class="kucuk">Kargo: '+esc(s.kargo_firma)+' — '+esc(s.kargo_kodu)+'</div>':'';
 var gecmis=(s.durum_gecmisi||[]).map(function(g){return esc(g.d)+" ("+esc((g.z||"").slice(0,16).replace("T"," "))+")";}).join(" → ");
 return '<div class="kart">'+
  '<div class="ust"><span class="no">'+esc(s.siparis_no)+'</span>'+durumRozet(s.durum)+
   '<span class="kucuk">'+esc((s.tarih||"").slice(0,16).replace("T"," "))+' · '+esc(s.odeme_yontemi)+'</span></div>'+
  '<div class="mus"><b>'+esc(s.musteri.ad)+'</b> · '+esc(s.musteri.tel)+'<br>'+esc(s.musteri.adres)+
   ' · '+esc(s.musteri.eposta)+'</div>'+
  '<div class="kucuk">Toplam '+tl(s.tutar_kurus)+' + kargo '+tl(s.kargo_kurus)+
   ' · KDV '+tl(s.kdv_kurus)+'</div>'+
  kalem+kargoBilgi+
  '<div class="eylemler">'+eylem+
   '<button class="ikincil" onclick="komutKopyala(\\''+esc(s.yazdir_komut)+'\\')">Yerel komut kopyala</button>'+
  '</div>'+kargoForm+
  (gecmis?'<div class="gecmis">Geçmiş: '+gecmis+'</div>':'')+
  '</div>';
}
async function yukle(){
 var d=document.getElementById("durumSuzgec").value;
 var m=document.getElementById("liste");
 m.innerHTML="<p>Yükleniyor…</p>";
 var r=await api("/liste"+(d?"?durum="+encodeURIComponent(d):""));
 if(r.kod!==200){m.innerHTML='<p class="hata">Liste alınamadı ('+r.kod+'). Anahtar doğru mu?</p>';return;}
 var s=r.govde.siparisler||[];
 if(!s.length){m.innerHTML="<p>Sipariş yok.</p>";return;}
 m.innerHTML=s.map(kartHtml).join("");
}
async function durumDegis(no,d){
 if(d==="iptal"&&!confirm("Sipariş iptal edilsin mi?"))return;
 var r=await api("/durum",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({siparis_no:no,durum:d})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));}
 yukle();
}
async function kargoGonder(no){
 var f=document.getElementById("kf-"+no).value.trim(),k=document.getElementById("kk-"+no).value.trim();
 if(!f||!k){alert("Firma ve takip kodu gerekli.");return;}
 var r=await api("/kargo",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({siparis_no:no,kargo_firma:f,kargo_kodu:k})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));}
 yukle();
}
function komutKopyala(t){navigator.clipboard&&navigator.clipboard.writeText(t);
 alert("Panoya kopyalandı:\\n"+t);}
document.getElementById("yenile").onclick=yukle;
document.getElementById("durumSuzgec").onchange=yukle;
yukle();
</script></body></html>`;
