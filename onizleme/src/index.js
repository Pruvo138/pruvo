/**
 * pruvo-onizleme — sari seri interaktif 3D onizleme worker'i.
 * Is paketi: tools/paket-onizleme-3d.md (Faz C pilot). pruvo-shop'tan AYRI worker:
 * odeme yolu ile derleme yuku ayni izolasyona konmaz.
 *
 * Uclar (site route'u: pruvo3d.com/api/onizleme/*):
 *   POST /api/onizleme/olustur {aile, parametreler}
 *        -> 200 binary govde (gzip'li STL; istemci DecompressionStream ile acar,
 *           basliklar: X-Sikistirma: gzip, X-Kaynak: onbellek|derleyici, X-Ham-Boyut)
 *        -> 400 sema disi / 404 aile yok / 413 cikti tavani / 422 gecersiz geometri
 *           429 hiz siniri / 502-504 derleyici sorunu / 503 derleyici bagli degil
 *   GET  /api/onizleme/saglik -> {durum, derleyici}
 *
 * KIRMIZI CIZGILER:
 *  - Uretec kodu istemciye ASLA gitmez; giden yalnizca derlenmis mesh (binary STL).
 *  - Sema kapisi TEK KAYNAK: jenerator/konfigurator.js (KONF.dogrula) +
 *    shop/src/semalar.js — sitedeki/odemedeki dogrulamanin AYNISI, kopya yok.
 *  - Istemci metni OpenSCAD'e hicbir yoldan sizamaz: sayi disi her deger sema
 *    kapisinda 400 yer; derleyici tarafinda da ikinci savunma var (server.py oz-test).
 *  - Onbellek anahtari = aile + SHA-256(normalize parametreler); isabet derleyiciye
 *    GITMEZ ve hiz sinirina SAYILMAZ.
 *
 * Hiz siniri: IP basina dakikada 10 DERLEME (izolat ici bellek; Cloudflare'da
 * izolat basina ayri sayac olabilir = pilot icin kabul edilen yumusaklik, cunku
 * onbellek isabetleri zaten muaf ve asil koruma derleme maliyetine. Ileride
 * Cloudflare rate-limit binding'ine tek fonksiyon degisikligiyle gecilir).
 */

import KONF from "../../jenerator/konfigurator.js";
import { SEMALAR } from "../../shop/src/semalar.js";
import "../../secenekler.js";
import { derleyiciCagir } from "./derleyici.js";

const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK || !Array.isArray(SECENEK.ONIZLEME_AILELER)) {
  throw new Error("secenekler.js yuklenemedi — onizleme aile listesi tek kaynagi yok");
}
const AILELER = new Set(SECENEK.ONIZLEME_AILELER);

const GZIP_TAVANI = 2 * 1024 * 1024;   // pakete gore cikti tavani 2 MB
const HAM_TAVAN = 16 * 1024 * 1024;    // sisme korumasi (gzip oncesi)
const SINIR_ADET = 10;                 // IP basina dakikada derleme
const SINIR_PENCERE_MS = 60 * 1000;
const ONBELLEK_SURUM = "v3";           // cozunurluk/eslem degisirse artir (eski anahtar carpismasin)
                                       // v2: Faz E — eslem duzeltmeleri (yay Phase, kase gövde,
                                       // petek/cetvel kisitlari) + textmetrics bayragi
                                       // v3: eslem v5 onizleme hiz dugmeleri (17 Tem 502 turu:
                                       // cetvel/jeton/pervane/petek/izgara/ramp mesh'i degisti)

// ---------------------------------------------------------------- yardimcilar

function cors(env) {
  return {
    "Access-Control-Allow-Origin": (env && env.SITE_URL) || "https://pruvo3d.com",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(veri, kod, env) {
  return new Response(JSON.stringify(veri), {
    status: kod || 200,
    headers: { "Content-Type": "application/json; charset=utf-8",
               "Cache-Control": "no-store", ...cors(env) },
  });
}

/** Sema sirasinda, tipe gore normalize edilmis parametre seti.
 *  Sayilar Number'a cevrilir ("40" ve 40 ayni onbellek anahtarina duser). */
function normalizeEt(sema, parametreler) {
  const n = {};
  for (const p of sema.parametreler) {
    const tip = p.tip || "sayi";
    const v = parametreler[p.ad];
    n[p.ad] = (tip === "sayi") ? parseFloat(String(v).replace(",", ".")) : v;
  }
  return n;
}

async function anahtarUret(aile, normal, sema) {
  // Kanonik metin: sema sirasiyla [ad, deger] ciftleri (anahtar sirasi oynamaz).
  const ciftler = sema.parametreler.map((p) => [p.ad, normal[p.ad]]);
  const metin = JSON.stringify(ciftler);
  const ozet = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(metin));
  const hex = [...new Uint8Array(ozet)].map((b) => b.toString(16).padStart(2, "0")).join("");
  return "onizleme/" + ONBELLEK_SURUM + "/" + aile + "/" + hex + ".stl.gz";
}

async function gzipLe(buf) {
  const akis = new Response(buf).body.pipeThrough(new CompressionStream("gzip"));
  return await new Response(akis).arrayBuffer();
}

// ---- hiz siniri (izolat ici bellek; onbellek isabetleri muaf) ----
const sayaclar = new Map(); // ip -> son SINIR_PENCERE_MS icindeki derleme zamanlari

function hizSiniriAsildi(ip) {
  const simdi = Date.now();
  const eski = sayaclar.get(ip) || [];
  const taze = eski.filter((t) => simdi - t < SINIR_PENCERE_MS);
  if (taze.length >= SINIR_ADET) { sayaclar.set(ip, taze); return true; }
  taze.push(simdi);
  sayaclar.set(ip, taze);
  // Buyumeyi sinirla: eski IP kayitlarini ara ara sil.
  if (sayaclar.size > 5000) {
    for (const [k, v] of sayaclar) {
      if (!v.length || simdi - v[v.length - 1] > SINIR_PENCERE_MS) { sayaclar.delete(k); }
    }
  }
  return false;
}

// ---------------------------------------------------------------- /olustur

async function olustur(request, env) {
  let govde;
  try { govde = await request.json(); }
  catch (e) { return json({ hata: "gecersiz-json" }, 400, env); }
  if (!govde || typeof govde !== "object") { return json({ hata: "gecersiz-istek" }, 400, env); }

  const aile = govde.aile;
  const p = govde.parametreler;
  if (typeof aile !== "string" || !AILELER.has(aile)) {
    return json({ hata: "aile-yok" }, 404, env);
  }
  const sema = SEMALAR.get(aile);
  if (!sema) { return json({ hata: "sema-yok" }, 404, env); }
  if (!p || typeof p !== "object" || Array.isArray(p)) {
    return json({ hata: "parametre-yok" }, 400, env);
  }

  // SEMA KAPISI (shop/src/parametrik.js ile ayni kurallar, ayni fonksiyonlar):
  // 1) tanimsiz anahtar reddi, 2) min/max/adim/tip dogrulamasi (KONF.dogrula).
  const tanimli = new Set(sema.parametreler.map((x) => x.ad));
  for (const ad of Object.keys(p)) {
    if (!tanimli.has(ad)) { return json({ hata: "bilinmeyen-parametre", alan: ad }, 400, env); }
  }
  // SIKI TIP KAPISI (dogruladan ONCE): KONF.parametreHatasi tarayici girisine
  // hosgoruludur (parseFloat "40; cube(9)" -> 40 onekini alir — form alani icin dogru,
  // API icin degil). API'de sayi = JSON sayisi ya da SAF sayi metni; gerisi 400.
  for (const tanim of sema.parametreler) {
    if ((tanim.tip || "sayi") !== "sayi") { continue; }
    const v = p[tanim.ad];
    const sayiMi = (typeof v === "number" && Number.isFinite(v)) ||
      (typeof v === "string" && /^-?[0-9]+([.,][0-9]+)?$/.test(v.trim()));
    if (!sayiMi) { return json({ hata: "parametre-araligi", alanlar: [tanim.ad] }, 400, env); }
  }
  const sonuc = KONF.dogrula(sema, p);
  if (!sonuc.gecerli) {
    return json({ hata: "parametre-araligi",
                  alanlar: Object.keys(sonuc.hatalar || {}) }, 400, env);
  }

  // ONIZLEME KISITLARI (tek kaynak secenekler.js): uretim motorunda 3D
  // karsiligi olmayan secim degerleri — siparis akisini degil yalniz
  // onizlemeyi kisitlar; urun sayfasi ayni listeyle onceden uyarir.
  const kisitlar = (SECENEK.ONIZLEME_KISITLAR || {})[aile];
  if (kisitlar) {
    for (const [ad, izinli] of Object.entries(kisitlar)) {
      if (p[ad] !== undefined && !izinli.includes(p[ad])) {
        return json({ hata: "onizleme-secenek-kisiti", alan: ad }, 400, env);
      }
    }
  }

  const normal = normalizeEt(sema, p);
  const anahtar = await anahtarUret(aile, normal, sema);

  // ONBELLEK: isabet varsa derleyiciye gidilmez, hiz sinirina sayilmaz.
  if (env.ONBELLEK) {
    const kayit = await env.ONBELLEK.get(anahtar);
    if (kayit) {
      const ham = (kayit.customMetadata && kayit.customMetadata.hamBoyut) || "";
      return new Response(kayit.body, {
        status: 200,
        headers: { "Content-Type": "application/octet-stream",
                   "X-Sikistirma": "gzip", "X-Kaynak": "onbellek",
                   "X-Ham-Boyut": ham, "Cache-Control": "no-store", ...cors(env) },
      });
    }
  }

  // HIZ SINIRI: yalniz derleme yoluna girenler sayilir.
  const ip = request.headers.get("CF-Connecting-IP") || "yerel";
  if (hizSiniriAsildi(ip)) {
    return json({ hata: "hiz-siniri", mesaj: "Dakikada en fazla " + SINIR_ADET +
                  " yeni onizleme uretilebilir; az sonra tekrar deneyin." }, 429, env);
  }

  const d = await derleyiciCagir(env, aile, normal);
  if (d.kod !== 200) { return json({ hata: d.hata }, d.kod, env); }
  if (d.govde.byteLength > HAM_TAVAN) { return json({ hata: "cikti-cok-buyuk" }, 413, env); }

  const sikisik = await gzipLe(d.govde);
  if (sikisik.byteLength > GZIP_TAVANI) { return json({ hata: "cikti-cok-buyuk" }, 413, env); }

  if (env.ONBELLEK) {
    await env.ONBELLEK.put(anahtar, sikisik, {
      httpMetadata: { contentType: "application/octet-stream" },
      customMetadata: { aile: aile, hamBoyut: String(d.govde.byteLength) },
    });
  }

  return new Response(sikisik, {
    status: 200,
    headers: { "Content-Type": "application/octet-stream",
               "X-Sikistirma": "gzip", "X-Kaynak": "derleyici",
               "X-Ham-Boyut": String(d.govde.byteLength),
               "Cache-Control": "no-store", ...cors(env) },
  });
}

// ---------------------------------------------------------------- container

/**
 * Cloudflare Container sarmalayicisi (Durable Object). Harici kutuphane YOK —
 * ham ctx.container API'si: instance yoksa baslatir, 8080 portu hazir olana
 * kadar dener (soguk baslatma burada yasanir; adaptor butcesi 30 sn), istegi
 * icindeki server.py'ye aynen gecirir. Tek isimli instance kullanilir
 * (adaptor idFromName("derleyici")) — pilot icin tek konteyner yeter.
 */
export class OnizlemeDerleyici {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
  }

  async fetch(request) {
    const kap = this.ctx.container;
    if (!kap) {
      return new Response(JSON.stringify({ hata: "container-yok" }),
        { status: 503, headers: { "Content-Type": "application/json" } });
    }
    // Ops/olcum ucu (worker katmani KAPAT_ANAHTAR ile korur): container SURECINI
    // durdurur (SIGTERM) — kapi-1 soguk baslatma olcumu tekrarlanabilir olsun diye.
    // BILEREK destroy() DEGIL: destroy instance'i DEPROVISION eder, yeniden tahsis
    // DAKIKALAR surer (16 Tem'de olculdu) ve musteri yolunu temsil etmez. SIGTERM
    // ile instance tahsisli kalir; sonraki istek start() ile yalnizca boot'u oder =
    // gercek "sifirdan olcekleme" yolu.
    if (new URL(request.url).pathname === "/kapat") {
      if (kap.running) {
        try { kap.signal(15); } catch (e) {
          try { await kap.destroy(); } catch (e2) { /* zaten olmus */ }
        }
      }
      return new Response(JSON.stringify({ durum: "kapatildi" }),
        { headers: { "Content-Type": "application/json" } });
    }
    const port = kap.getTcpPort(8080);
    const govde = request.method === "POST" ? await request.arrayBuffer() : null;
    let sonHata = null;
    for (let i = 0; i < 110; i++) { // ~55 sn tavan (soguk baslatma penceresi; adaptor 60 sn)
      // start() DONGUNUN ICINDE: destroy hemen ardindan gelen istekte container henuz
      // "stopped" olmayabilir ve start() firlatir — bir kez deneyip vazgecmek konteyneri
      // SONSUZA DEK kapali birakiyordu (16 Tem kapi-1 ilk kosumunda olculdu: tum istekler
      // 28 sn sonra derleyici-acilamadi). Her turda yeniden denenir; kalkinca fetch gecer.
      if (!kap.running) {
        try { kap.start(); } catch (e) { sonHata = e; }
      }
      try {
        return await port.fetch(new Request(request.url, {
          method: request.method,
          headers: request.headers,
          body: govde,
        }));
      } catch (e) {
        sonHata = e;
        await new Promise((coz) => setTimeout(coz, 500));
      }
    }
    console.error("container porta ulasilamadi:", (sonHata && sonHata.message) || sonHata);
    return new Response(JSON.stringify({ hata: "derleyici-acilamadi" }),
      { status: 503, headers: { "Content-Type": "application/json" } });
  }
}

// ---------------------------------------------------------------- giris

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const yol = url.pathname.replace(/^\/api\/onizleme/, "") || "/";
    try {
      if (request.method === "OPTIONS") {
        return new Response(null, { status: 204, headers: cors(env) });
      }
      if (yol === "/olustur" && request.method === "POST") {
        return await olustur(request, env);
      }
      if (yol === "/saglik" && request.method === "GET") {
        return json({ durum: "ok", aileler: [...AILELER],
                      derleyici: !!(env.DERLEYICI || env.DERLEYICI_URL) }, 200, env);
      }
      // Ops/olcum: container'i kapat (kapi-1 soguk baslatma olcumu tekrar edilebilsin).
      // KAPAT_ANAHTAR secret'i ayarli degilse uc HIC YOKMUS gibi davranir (404).
      if (yol === "/derleyici-kapat" && request.method === "POST") {
        if (!env.KAPAT_ANAHTAR ||
            request.headers.get("X-Kapat-Anahtar") !== env.KAPAT_ANAHTAR) {
          return json({ hata: "bulunamadi" }, 404, env);
        }
        if (!(env.DERLEYICI && typeof env.DERLEYICI.idFromName === "function")) {
          return json({ hata: "derleyici-yok" }, 503, env);
        }
        const stub = env.DERLEYICI.get(
          env.DERLEYICI.idFromName(env.DERLEYICI_AD || "derleyici"));
        const c = await stub.fetch("http://derleyici/kapat", { method: "POST" });
        return json(await c.json(), c.status, env);
      }
      return json({ hata: "bulunamadi" }, 404, env);
    } catch (e) {
      console.error("pruvo-onizleme hata:", (e && e.stack) || e);
      return json({ hata: "sunucu-hatasi" }, 500, env);
    }
  },
};
