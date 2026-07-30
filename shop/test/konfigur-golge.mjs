#!/usr/bin/env node
/**
 * KONFIGUR GOLGE MODU KABUL TESTI (FAZ 3) — "D1'den OKU, bundle'dan HESAPLA, FARKI OLC".
 *
 *   node shop/test/konfigur-golge.mjs
 *
 * FAZ 3'un sozu tek cumle: MUSTERIYE GIDEN DAVRANIS HIC DEGISMEZ, yalniz "D1 verisi bundle
 * ile ayni mi" sorusu olculebilir hale gelir. Bu test o sozun IKI YARISINI da kanitlar:
 *   (1) fiyatlar BIREBIR ayni (konfigur kolonu OLAN ve OLMAYAN D1'de bile ayni),
 *   (2) fark 0 iken 0 olarak, kasten farklilastirilmis fiksturde GORUNUR + SAYILABILIR cikar.
 *
 * NASIL (OFFLINE — wrangler/ag/gercek odeme YOK): shop/src/index.js'in KENDISI Node'a
 * yuklenir, D1 ve iyzico yerine bellek-ici sahteleri konur. Fiyat, worker'in D1'e YAZDIGI
 * siparis satirindan okunur — yani gercek para yolundan. Yukleyici Node 20 uyumludur
 * (bkz. konfigur-fail-closed.mjs'teki ayni desen: JSON import'lari gomulur, ESM kancasi YOK).
 *
 * KOSTUGU SETLER:
 *   1) MUSTERI DAVRANISI — 4 capa fiyat + konfigursuz urun; konfigur kolonu VARKEN ve YOKKEN
 *      birebir AYNI (mimarin verdigi kabul sayilari).
 *   2) GOLGE PARITE — 17 urunun hepsinde bundle == D1 -> durum "ayni", fark 0, LOG YOK.
 *   3) KASTEN FARK — D1 semasi bozulur: fark GORUNUR (alan yolu) + SAYILABILIR (kurus),
 *      ama TAHSILAT DEGISMEZ (hala bundle fiyati).
 *   4) PENCERE SINIFLARI — d1-eksik / bundle-eksik / d1-bozuk ayrik ve dogru siniflanir.
 *   5) FAIL-SAFE — D1'de konfigur kolonu YOKKEN (SELECT patlar) odeme AYNEN calisir.
 *   6) RAPOR KIPI — /yonet/konfigur-golge: anahtarsiz 404, anahtarli 200 + sayilar; YAZMA YOK.
 *   7) YANLIS-POZITIF — 20+ konfigursuz normal urun: log YOK, fiyat degismedi.
 *   8) MUTASYON — golge nobetleri no-op yapilinca 2/3 KIRMIZI yanmali; ayni mutantta set 1
 *      (fiyat) YESIL kalmali (golge para yolundan gercekten AYRIK).
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const SRC = path.join(SHOP, "src");
const require = createRequire(import.meta.url);

// ------------------------------------------------- Node 20 uyumlu yukleyici (kanca YOK)
// Gerekce + tasarim: shop/test/konfigur-fail-closed.mjs dosya basi (AYNI desen; ikinci bir
// yukleme mekanizmasi icat edilmedi).
const TEMP_ONEK = "src-golge-tmp-";
const TEMP_DIZIN = path.join(SHOP, TEMP_ONEK + process.pid);

function tempSupur() {
  for (const ad of fs.readdirSync(SHOP)) {
    if (ad.startsWith(TEMP_ONEK)) {
      fs.rmSync(path.join(SHOP, ad), { recursive: true, force: true });
    }
  }
}

function jsonGom(kaynak, kaynakDizin, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(kaynakDizin, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ") — desen guncellenmeli");
  }
  return cikti;
}

function tempKur() {
  tempSupur();
  fs.mkdirSync(TEMP_DIZIN, { recursive: true });
  for (const ad of fs.readdirSync(SRC)) {
    if (!ad.endsWith(".js")) { continue; }
    fs.writeFileSync(path.join(TEMP_DIZIN, ad),
                     jsonGom(fs.readFileSync(path.join(SRC, ad), "utf8"), SRC, ad));
  }
}

tempKur();
process.on("exit", () => { fs.rmSync(TEMP_DIZIN, { recursive: true, force: true }); });

let sanalSayac = 0;
/** Verilen index.js kaynagini (gercek/mutant) gecici dizinden modul olarak yukler. */
async function indexYukle(kaynak) {
  sanalSayac += 1;
  const yol = path.join(TEMP_DIZIN, "index-surum-" + sanalSayac + ".js");
  fs.writeFileSync(yol, jsonGom(kaynak, SRC, "index-surum-" + sanalSayac));
  return await import(pathToFileURL(yol).href);
}

/**
 * Bagimli modulu (konfigur-golge.js) mutasyonlu yukler.
 * ⚠️ IKI TUKETICI: index.js (istek basi golge logu) VE yonet.js (rapor ucu). Yalniz index.js'in
 * import'u degistirilseydi rapor yolu MUTASYONSUZ kalir, mutant "yakalanmadi" gorunurdu
 * (olculdu: M1/M3 ilk kosumda tam bu yuzden sahte-yesildi). Bu yuzden yonet.js'in de mutant
 * kopyasi uretilir ve index.js ona baglanir.
 */
async function modulMutasyonu(dosyaAdi, capa, yerine, etiket) {
  const ham = fs.readFileSync(path.join(SRC, dosyaAdi), "utf8");
  if (ham.split(capa).length - 1 !== 1) {
    throw new Error("MUTASYON CAPASI YOK/COK (" + etiket + "): " + dosyaAdi);
  }
  sanalSayac += 1;
  const alt = "golge-mutant-" + sanalSayac + ".js";
  fs.writeFileSync(path.join(TEMP_DIZIN, alt),
                   jsonGom(ham.replace(capa, yerine), SRC, alt));

  // yonet.js -> mutant golge modulu
  const yonetHam = fs.readFileSync(path.join(SRC, "yonet.js"), "utf8");
  const yonetYeni = yonetHam.replace('from "./' + dosyaAdi + '"', 'from "./' + alt + '"');
  if (yonetYeni === yonetHam) {
    throw new Error("yonet.js import satiri bulunamadi: " + dosyaAdi);
  }
  const yonetAlt = "yonet-mutant-" + sanalSayac + ".js";
  fs.writeFileSync(path.join(TEMP_DIZIN, yonetAlt), jsonGom(yonetYeni, SRC, yonetAlt));

  // index.js -> mutant golge modulu + mutant yonet
  const indexHam = fs.readFileSync(path.join(SRC, "index.js"), "utf8");
  let yeni = indexHam.replace('from "./' + dosyaAdi + '"', 'from "./' + alt + '"');
  if (yeni === indexHam) { throw new Error("index.js import satiri bulunamadi: " + dosyaAdi); }
  const oncekiYonet = yeni;
  yeni = yeni.replace('from "./yonet.js"', 'from "./' + yonetAlt + '"');
  if (yeni === oncekiYonet) { throw new Error("index.js yonet.js import satiri bulunamadi"); }
  return await indexYukle(yeni);
}

// ---------------------------------------------------------------- sahte cevre (D1 + iyzico)

let iyzicoCagri = 0;
globalThis.fetch = async function sahteFetch(hedef) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (u.includes("iyzico.test")) {
    iyzicoCagri += 1;
    return new Response(JSON.stringify({
      status: "success", token: "test-token-" + iyzicoCagri,
      paymentPageUrl: "https://odeme.test/sayfa",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  if (u.includes("telegram.test")) {
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  }
  throw new Error("TESTTE BEKLENMEYEN AG ISTEGI: " + u);
};

// GOLGE LOG'LARINI YAKALA: worker console.log ile yazar; test onlari toplar.
let golgeLoglari = [];
const gercekLog = console.log;
function logYakalaBasla() { golgeLoglari = []; }
console.log = function (...a) {
  const s = a.length === 1 && typeof a[0] === "string" ? a[0] : a.join(" ");
  if (typeof s === "string" && s.startsWith("konfigur-golge")) { golgeLoglari.push(s); return; }
  gercekLog.apply(console, a);
};

/**
 * D1 sahtesi. `konfigurKolonu:false` -> `konfigur` iceren SELECT ATAR (canli D1'de kolon
 * henuz yokken olan sey). Yazmalar (run) kaydedilir -> "rapor ucu YAZMIYOR" olculebilir.
 */
function d1Sahte(satirlar, kayitlar, ayar) {
  const konfigurKolonu = !ayar || ayar.konfigurKolonu !== false;
  const harita = new Map(satirlar.map((u) => [u.id, u]));
  return {
    prepare(sql) {
      const konfigurIster = /\bkonfigur\b/.test(sql);
      return {
        bind(...arg) {
          return {
            async all() {
              if (konfigurIster && !konfigurKolonu) {
                throw new Error("D1_ERROR: no such column: konfigur");
              }
              // /yonet/konfigur-golge: "konfigur <> '' OR id IN (...)" — iki yonu de karsila.
              if (/konfigur <> ''/.test(sql)) {
                const idSet = new Set(arg);
                return { results: satirlar
                  .filter((u) => (u.konfigur && u.konfigur !== "") || idSet.has(u.id))
                  .map((u) => ({ id: u.id, kategori: u.kategori, konfigur: u.konfigur || "" })) };
              }
              const bulunan = arg.map((id) => harita.get(id)).filter(Boolean);
              return { results: konfigurIster ? bulunan
                : bulunan.map(({ konfigur, ...kalan }) => kalan) };
            },
            async first() { return null; },
            async run() { kayitlar.push({ sql, arg }); return { meta: { changes: 1 } }; },
          };
        },
      };
    },
  };
}

const ENV = {
  SITE_URL: "https://pruvo3d.com",
  IYZICO_BASE_URL: "https://iyzico.test",
  IYZICO_API_KEY: "test-api-key",
  IYZICO_SECRET_KEY: "test-secret-key",
};

/** /baslat'i GERCEK worker kodundan cagirir; cevabi + D1'e yazilan satiri dondurur. */
async function baslat(mod, d1Satirlari, kalem, ayar) {
  const kayitlar = [];
  logYakalaBasla();
  const env = Object.assign({}, ENV, { KATALOG: d1Sahte(d1Satirlari, kayitlar, ayar) });
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sozlesme_onay: true, odeme: "kart",
      musteri: { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
                 adres: "Test mahallesi test sokak no 1", sehir: "Mugla" },
      sepet: [kalem],
    }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  const insert = kayitlar.find((k) => /INSERT INTO siparisler/.test(k.sql));
  let birimKurus = null, tutarKurus = null;
  if (insert) {
    const dizi = insert.arg.find((x) => typeof x === "string" && x.startsWith("["));
    const satir = dizi ? JSON.parse(dizi)[0] : null;
    birimKurus = satir ? satir.birim_kurus : null;
    tutarKurus = insert.arg.find((x) => typeof x === "number" && x > 0) ?? null;
  }
  return { kod: cevap.status, govde, birimKurus, tutarKurus,
           loglar: golgeLoglari.slice(), kayitlar };
}

/**
 * POST /api/shop/fiyat (PROVA) — mimarin kabul sayilari BU uctan okunur: tahsilat tutari
 * (kargo dahil) ve birim kurus acikca doner. Yan etkisiz: D1'e yazmaz, iyzico'ya gitmez.
 * Hiz siniri binding'i sahtelenir (tavan bu testin olctugu eksen DEGIL — o fiyat-prova.mjs'te).
 */
async function prova(mod, d1Satirlari, kalem, ayar) {
  const kayitlar = [];
  logYakalaBasla();
  const env = Object.assign({}, ENV, {
    KATALOG: d1Sahte(d1Satirlari, kayitlar, ayar),
    FIYAT_RATE_LIMIT: { async limit() { return { success: true }; } },
  });
  const istek = new Request("https://pruvo3d.com/api/shop/fiyat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sepet: [kalem] }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  return { kod: cevap.status, govde, loglar: golgeLoglari.slice(), yazma: kayitlar.length };
}

/** /yonet/konfigur-golge raporunu cagirir. */
async function rapor(mod, d1Satirlari, anahtar, ayar) {
  const kayitlar = [];
  const env = Object.assign({}, ENV, { KATALOG: d1Sahte(d1Satirlari, kayitlar, ayar),
                                       YONET_ANAHTAR: "gizli-test-anahtari" });
  const url = "https://pruvo3d.com/api/shop/yonet/konfigur-golge" +
              (anahtar ? "?anahtar=" + encodeURIComponent(anahtar) : "");
  const cevap = await mod.default.fetch(new Request(url), env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  return { kod: cevap.status, govde, yazma: kayitlar.length };
}

// ---------------------------------------------------------------- veri

require(path.join(KOK, "secenekler.js"));
const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi"); }

const URUNLER = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));
const KONFIGUR_URUNLER = URUNLER.filter((u) => u.konfigur);
const NORMAL_URUNLER = URUNLER.filter(
  (u) => !u.konfigur && !u.parametrik && u.fiyat && u.kategori !== "Skan Art").slice(0, 25);

/** Kanonik JSON — tools/d1-sync.py konfigur_kanonik ile AYNI anlam (sort_keys + kompakt). */
function kanonik(o) {
  if (o === null || typeof o !== "object") { return JSON.stringify(o); }
  if (Array.isArray(o)) { return "[" + o.map(kanonik).join(",") + "]"; }
  return "{" + Object.keys(o).sort().map((k) => JSON.stringify(k) + ":" + kanonik(o[k]))
    .join(",") + "}";
}

/** urunler.json kaydindan D1 satiri (d1-sync.py'nin yazdigi alanlar + konfigur). */
function d1Satiri(u, konfigurUstuneYaz) {
  return { id: u.id, baslik: u.baslik || "", kategori: u.kategori || "",
           fiyat: u.fiyat || "", parametrik: u.parametrik ? 1 : 0,
           gorsel: (u.gorseller && u.gorseller[0]) || "",
           konfigur: konfigurUstuneYaz !== undefined ? konfigurUstuneYaz
             : (u.konfigur ? kanonik(u.konfigur) : "") };
}

// ---------------------------------------------------------------- kosum

const hatalar = [];
const ham = [];
function iddia(ad, kosul, detay) {
  if (kosul) { ham.push("  ✅ " + ad); }
  else { hatalar.push(ad + (detay ? " — " + detay : "")); ham.push("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

const MOD = await indexYukle(fs.readFileSync(path.join(SRC, "index.js"), "utf8"));

// === 1) MUSTERI DAVRANISI DEGISMEDI (mimarin verdigi 4 capa) ======================
ham.push("== 1) MUSTERI DAVRANISI — 4 capa fiyat, konfigur kolonu VARKEN ve YOKKEN ==");
const CAPA = URUNLER.find((u) => u.id === "capa-serit-dekoratif-figur");
const ANKA = URUNLER.find((u) => u.id === "anka-kusu-serit-dekoratif-figur");
const NORMAL = NORMAL_URUNLER[0];
if (!CAPA || !ANKA || !NORMAL) { throw new Error("capa/anka/normal urun bulunamadi"); }

/** Ayni kalemi konfigur kolonu OLAN ve OLMAYAN D1'de fiyatla; ikisini de dondur. */
async function ikiYol(urun, kalem) {
  const a = await baslat(MOD, [d1Satiri(urun)], kalem);                       // kolon VAR
  const b = await baslat(MOD, [d1Satiri(urun)], kalem, { konfigurKolonu: false }); // kolon YOK
  return { a, b };
}

const k1 = await ikiYol(CAPA, { id: CAPA.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                                parametreler: { boy_mm: 150 } });
iddia("capa 150mm/PLA birim = 73600 kurus (kolon VAR)", k1.a.birimKurus === 73600,
      "olculen=" + k1.a.birimKurus);
iddia("capa 150mm/PLA birim = 73600 kurus (kolon YOK — fail-safe yol)",
      k1.b.birimKurus === 73600, "olculen=" + k1.b.birimKurus);

const k2 = await ikiYol(CAPA, { id: CAPA.id, malzeme: "ASA", renk: "Siyah", adet: 1,
                                parametreler: { boy_mm: 300 } });
iddia("capa 300mm/ASA birim = 150000 kurus (kolon VAR)", k2.a.birimKurus === 150000,
      "olculen=" + k2.a.birimKurus);
iddia("capa 300mm/ASA birim = 150000 kurus (kolon YOK)", k2.b.birimKurus === 150000,
      "olculen=" + k2.b.birimKurus);

// ANKA capasi mimarin verdigi bicimde: TUTAR (kargo dahil) = 986,00 TL. Bu, /fiyat provasinin
// DONDURDUGU alanlardan okunur (INSERT arg'lari degil) -> "POST /api/shop/fiyat bugunkü
// fiyatlari birebir donmeli" kabulu dogrudan sinanir.
const ankaKalem = { id: ANKA.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                    parametreler: { boy_mm: 150 } };
const p3 = await prova(MOD, [d1Satiri(ANKA)], ankaKalem);
const p3b = await prova(MOD, [d1Satiri(ANKA)], ankaKalem, { konfigurKolonu: false });
iddia("anka-kusu 150mm/PLA /fiyat tutar = '986,00 TL' (kargo dahil)",
      p3.govde.tutar === "986,00 TL", "olculen=" + p3.govde.tutar);
iddia("anka-kusu tahsilat_kurus = 98600 (73600 urun + 25000 kargo)",
      p3.govde.tahsilat_kurus === 98600 && p3.govde.urun_kurus === 73600 &&
      p3.govde.kargo_kurus === 25000, JSON.stringify(p3.govde));
iddia("anka-kusu tutari kolon YOKKEN de AYNI ('986,00 TL')",
      p3b.govde.tutar === "986,00 TL" && p3b.govde.tahsilat_kurus === 98600,
      "olculen=" + p3b.govde.tutar);
iddia("🔴 /fiyat provasi D1'e YAZMAZ (golge eklendikten sonra da yan etkisiz)",
      p3.yazma === 0, "yazma=" + p3.yazma);
// capa capalari da /fiyat ucundan teyit (iki uc AYNI cekirdegi kosuyor)
const pCapa1 = await prova(MOD, [d1Satiri(CAPA)],
  { id: CAPA.id, malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 150 } });
const pCapa2 = await prova(MOD, [d1Satiri(CAPA)],
  { id: CAPA.id, malzeme: "ASA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 300 } });
iddia("/fiyat: capa 150mm/PLA birim_kurus = 73600",
      pCapa1.govde.satirlar && pCapa1.govde.satirlar[0].birim_kurus === 73600,
      JSON.stringify(pCapa1.govde.satirlar));
iddia("/fiyat: capa 300mm/ASA birim_kurus = 150000",
      pCapa2.govde.satirlar && pCapa2.govde.satirlar[0].birim_kurus === 150000,
      JSON.stringify(pCapa2.govde.satirlar));

const nKalem = { id: NORMAL.id, malzeme: "PLA", renk: "Siyah", adet: 1 };
const kn = await ikiYol(NORMAL, nKalem);
const nBeklenen = SECENEK.satirOzeti(
  { kategori: NORMAL.kategori, fiyat: NORMAL.fiyat, parametrik: false, boy_secenekleri: [] },
  { id: NORMAL.id, malzeme: "PLA", renk: "Siyah", renk_ozel: "", boy_etiket: null, adet: 1 }
).birimKurus;
iddia("KONFIGURSUZ urun (" + NORMAL.id + ") fiyati DEGISMEDI (" + nBeklenen + ")",
      kn.a.birimKurus === nBeklenen && kn.b.birimKurus === nBeklenen,
      "kolonVar=" + kn.a.birimKurus + " kolonYok=" + kn.b.birimKurus);
iddia("konfigursuz urun GOLGE LOGU URETMEZ (gurultu yok)", kn.a.loglar.length === 0,
      JSON.stringify(kn.a.loglar));

// TUM 17 urun x 3 nokta: kolon VAR/YOK fiyatlari BIREBIR ayni mi?
let ayniSayac = 0, toplamDeneme = 0;
for (const u of KONFIGUR_URUNLER) {
  for (const [boy, malzeme] of [[60, "PLA"], [150, "PETG"], [300, "ASA"]]) {
    toplamDeneme += 1;
    const kalem = { id: u.id, malzeme, renk: "Siyah", adet: 1, parametreler: { boy_mm: boy } };
    const r = await ikiYol(u, kalem);
    if (r.a.kod === 200 && r.a.birimKurus === r.b.birimKurus && r.a.birimKurus > 0) {
      ayniSayac += 1;
    }
  }
}
iddia("17 urun x 3 nokta = " + toplamDeneme + " kalem: kolon VAR/YOK fiyati BIREBIR ayni",
      ayniSayac === toplamDeneme, ayniSayac + "/" + toplamDeneme);

// === 2) GOLGE PARITE — bundle == D1 -> fark 0, LOG YOK ===========================
ham.push("== 2) GOLGE PARITE — bundle == D1 ==");
let logSayaci = 0;
for (const u of KONFIGUR_URUNLER) {
  const r = await baslat(MOD, [d1Satiri(u)],
                         { id: u.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                           parametreler: { boy_mm: 150 } });
  logSayaci += r.loglar.length;
}
iddia("17/17 urunde bundle == D1 -> HIC golge logu yok (fark 0)", logSayaci === 0,
      "log=" + logSayaci);
const rp = await rapor(MOD, KONFIGUR_URUNLER.map((u) => d1Satiri(u)), "gizli-test-anahtari");
iddia("rapor: durum='parite'", rp.govde.durum === "parite", JSON.stringify(rp.govde.ozet));
iddia("rapor: fark_kurus_toplam === 0", rp.govde.fark_kurus_toplam === 0,
      String(rp.govde.fark_kurus_toplam));
iddia("rapor: ozet.ayni === 17", rp.govde.ozet && rp.govde.ozet.ayni === 17,
      JSON.stringify(rp.govde.ozet));
iddia("rapor: ayrisim kaydi YOK", (rp.govde.kayitlar || []).length === 0,
      JSON.stringify(rp.govde.kayitlar));

// === 3) KASTEN FARK — gorunur + sayilabilir, TAHSILAT DEGISMEZ ====================
ham.push("== 3) KASTEN FARKLILASTIRILMIS FIKSTUR ==");
// D1'deki semanin fiyat capasi yukseltilir (500 -> 700 TL taban). Bundle DEGISMEZ.
const bozukKonf = JSON.parse(JSON.stringify(CAPA.konfigur));
bozukKonf.fiyatCapalari = [[60, 700], [300, 3300]];
const farkliSatir = d1Satiri(CAPA, kanonik(bozukKonf));
const rf = await baslat(MOD, [farkliSatir],
                        { id: CAPA.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                          parametreler: { boy_mm: 150 } });
iddia("TAHSILAT HALA BUNDLE FIYATI (73600) — golge parayi ETKILEMEZ",
      rf.birimKurus === 73600, "olculen=" + rf.birimKurus);
iddia("fark GORUNUR: tam 1 golge logu yazildi", rf.loglar.length === 1,
      JSON.stringify(rf.loglar));
const kayit = rf.loglar.length ? JSON.parse(rf.loglar[0].replace("konfigur-golge ", "")) : {};
iddia("log durum='farkli'", kayit.durum === "farkli", JSON.stringify(kayit));
iddia("fark SAYILABILIR: fark_kurus sayi ve 0 DEGIL (" + kayit.fark_kurus + ")",
      typeof kayit.fark_kurus === "number" && kayit.fark_kurus !== 0, JSON.stringify(kayit));
iddia("ayrisan ALAN YOLU raporlandi (fiyatCapalari...)",
      Array.isArray(kayit.alanlar) && kayit.alanlar.some((a) => a.startsWith("fiyatCapalari")),
      JSON.stringify(kayit.alanlar));
const rf2 = await rapor(MOD, [farkliSatir, ...KONFIGUR_URUNLER.filter((u) => u.id !== CAPA.id)
  .map((u) => d1Satiri(u))], "gizli-test-anahtari");
iddia("rapor: durum='ayrisim'", rf2.govde.durum === "ayrisim", JSON.stringify(rf2.govde.ozet));
iddia("rapor: ozet.farkli === 1", rf2.govde.ozet.farkli === 1, JSON.stringify(rf2.govde.ozet));
iddia("rapor: fark_kurus_toplam > 0 (" + rf2.govde.fark_kurus_toplam + ")",
      rf2.govde.fark_kurus_toplam > 0, String(rf2.govde.fark_kurus_toplam));
iddia("rapor: ayrisan id ve alan yolu listelendi",
      (rf2.govde.kayitlar || []).some((r) => r.id === CAPA.id &&
        r.alanlar.some((a) => a.startsWith("fiyatCapalari"))),
      JSON.stringify(rf2.govde.kayitlar));

// === 4) PENCERE SINIFLARI ========================================================
ham.push("== 4) PENCERE SINIFLARI (d1-eksik / bundle-eksik / d1-bozuk) ==");
const rEksik = await baslat(MOD, [d1Satiri(CAPA, "")],
                            { id: CAPA.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                              parametreler: { boy_mm: 150 } });
const kEksik = rEksik.loglar.length ? JSON.parse(rEksik.loglar[0].replace("konfigur-golge ", "")) : {};
iddia("D1'de konfigur BOS -> durum 'd1-eksik' (senkron kacmis) + fiyat 73600 AYNI",
      kEksik.durum === "d1-eksik" && rEksik.birimKurus === 73600,
      JSON.stringify(kEksik) + " birim=" + rEksik.birimKurus);

// bundle-eksik: D1'de konfigur VAR, bundle'da id YOK (= BUGUNKU acik pencere)
const YENI_ID = "ejderha-serit-dekoratif-figur";
const yeniSatir = { id: YENI_ID, baslik: "Ejderha", kategori: "Skan Art", fiyat: "500 TL",
                    parametrik: 0, gorsel: "", konfigur: kanonik(CAPA.konfigur) };
const rBundleEksik = await baslat(MOD, [yeniSatir],
                                  { id: YENI_ID, malzeme: "PLA", renk: "Siyah", adet: 1,
                                    parametreler: { boy_mm: 150 } });
const kBE = rBundleEksik.loglar.length
  ? JSON.parse(rBundleEksik.loglar[0].replace("konfigur-golge ", "")) : {};
iddia("D1'de VAR / bundle'da YOK -> durum 'bundle-eksik' KAYDEDILDI (pencere sayilabilir)",
      kBE.durum === "bundle-eksik", JSON.stringify(kBE));
iddia("... ve DAVRANIS DEGISMEDI: hala fail-closed 400 'konfigur-urun' (WhatsApp)",
      rBundleEksik.kod === 400 && rBundleEksik.govde.hata === "konfigur-urun",
      rBundleEksik.kod + "/" + rBundleEksik.govde.hata);
iddia("... ve D1 GOLGE FIYATI hesaplandi (pencerenin PARA bedeli olculebilir: " +
      kBE.d1_kurus + " kurus)", kBE.d1_kurus === 73600, String(kBE.d1_kurus));

const rBozuk = await baslat(MOD, [d1Satiri(CAPA, "{bozuk-json")],
                            { id: CAPA.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                              parametreler: { boy_mm: 150 } });
const kBozuk = rBozuk.loglar.length ? JSON.parse(rBozuk.loglar[0].replace("konfigur-golge ", "")) : {};
iddia("D1 metni BOZUK -> durum 'd1-bozuk' (istisna DEGIL) + fiyat 73600 AYNI",
      kBozuk.durum === "d1-bozuk" && rBozuk.birimKurus === 73600,
      JSON.stringify(kBozuk) + " birim=" + rBozuk.birimKurus);

// === 5) FAIL-SAFE — kolon yokken odeme yolu AYNEN calisir ========================
ham.push("== 5) FAIL-SAFE — D1'de konfigur kolonu YOK ==");
iddia("kolon YOKKEN /baslat 200 doner (odeme yolu DUSMEZ)", k1.b.kod === 200,
      String(k1.b.kod));
const rpYok = await rapor(MOD, KONFIGUR_URUNLER.map((u) => d1Satiri(u)), "gizli-test-anahtari",
                          { konfigurKolonu: false });
iddia("rapor ucu kolon yokken 200 + durum='kolon-yok' (500 DEGIL)",
      rpYok.kod === 200 && rpYok.govde.durum === "kolon-yok", JSON.stringify(rpYok.govde));
iddia("rapor ucu teshiste COZUM komutunu soyler (--sema)",
      typeof rpYok.govde.coz === "string" && rpYok.govde.coz.includes("--sema"),
      String(rpYok.govde.coz));

// === 6) RAPOR KIPI — yetki + yan etkisizlik =====================================
ham.push("== 6) RAPOR KIPI — /yonet/konfigur-golge ==");
const rpAnahtarsiz = await rapor(MOD, KONFIGUR_URUNLER.map((u) => d1Satiri(u)), "");
iddia("anahtarsiz -> 404 (uc varligi sizmaz)", rpAnahtarsiz.kod === 404,
      String(rpAnahtarsiz.kod));
const rpYanlis = await rapor(MOD, KONFIGUR_URUNLER.map((u) => d1Satiri(u)), "yanlis");
iddia("yanlis anahtar -> 404", rpYanlis.kod === 404, String(rpYanlis.kod));
iddia("anahtarli -> 200", rp.kod === 200, String(rp.kod));
iddia("🔴 RAPOR UCU D1'e YAZMAZ (run cagrisi 0) + iyzico ACMAZ", rp.yazma === 0,
      "yazma=" + rp.yazma);

// === 7) YANLIS-POZITIF — konfigursuz urun partisi ================================
ham.push("== 7) YANLIS-POZITIF — 25 konfigursuz normal urun ==");
let ypLog = 0, ypOk = 0;
for (const u of NORMAL_URUNLER) {
  const r = await baslat(MOD, [d1Satiri(u)],
                         { id: u.id, malzeme: "PLA", renk: "Siyah", adet: 1 });
  ypLog += r.loglar.length;
  const bek = SECENEK.satirOzeti(
    { kategori: u.kategori, fiyat: u.fiyat, parametrik: false, boy_secenekleri: [] },
    { id: u.id, malzeme: "PLA", renk: "Siyah", renk_ozel: "", boy_etiket: null, adet: 1 }
  ).birimKurus;
  if (r.kod === 200 && r.birimKurus === bek) { ypOk += 1; }
}
iddia("25/25 konfigursuz urun fiyati BIREBIR ayni", ypOk === NORMAL_URUNLER.length,
      ypOk + "/" + NORMAL_URUNLER.length);
iddia("25 konfigursuz urunden HIC golge logu cikmadi (gurultu 0)", ypLog === 0,
      "log=" + ypLog);

// === 8) MUTASYON — nobetler no-op yapilinca KIRMIZI yanmali ======================
ham.push("== 8) MUTASYON (no-op) ==");
async function mutantOlcum(mod) {
  const rr = await baslat(mod, [farkliSatir],
                          { id: CAPA.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                            parametreler: { boy_mm: 150 } });
  const rp3 = await rapor(mod, [farkliSatir], "gizli-test-anahtari");
  return { log: rr.loglar.length, birim: rr.birimKurus,
           farkToplam: rp3.govde.fark_kurus_toplam, farkli: (rp3.govde.ozet || {}).farkli };
}
// M1: alanFarklari DAIMA bos -> sema ayrisimi gorunmez olur.
const M1 = await modulMutasyonu("konfigur-golge.js",
  "export function alanFarklari(a, b, yol = \"\", cikti = []) {",
  "export function alanFarklari(a, b, yol = \"\", cikti = []) { return cikti;",
  "M1");
const m1 = await mutantOlcum(M1);
iddia("M1 (alanFarklari no-op): set 3'un 'farkli' iddiasi KIRMIZI yanar",
      m1.log === 0 && m1.farkli !== 1, JSON.stringify(m1));
iddia("M1'de FIYAT hala 73600 — golge para yolundan GERCEKTEN ayrik",
      m1.birim === 73600, String(m1.birim));

// M2: golgeLogSatiri daima null -> ayrisim log'a HIC dusmez.
const M2 = await modulMutasyonu("konfigur-golge.js",
  "export function golgeLogSatiri(id, g) {",
  "export function golgeLogSatiri(id, g) { return null;",
  "M2");
const m2 = await mutantOlcum(M2);
iddia("M2 (golgeLogSatiri no-op): 'fark GORUNUR' iddiasi KIRMIZI yanar", m2.log === 0,
      JSON.stringify(m2));
iddia("M2'de FIYAT hala 73600 (fiyat seti mutantta da YESIL — ayriklik kaniti)",
      m2.birim === 73600, String(m2.birim));

// M3: golgeKalem fiyat karsilastirmasini yapmasin -> fark_kurus olculemez.
const M3 = await modulMutasyonu("konfigur-golge.js",
  "  if (typeof bundleKurus === \"number\") { sonuc.farkKurus = kh.birimKurus - bundleKurus; }",
  "  if (false) { sonuc.farkKurus = kh.birimKurus - bundleKurus; }",
  "M3");
const m3 = await mutantOlcum(M3);
iddia("M3 (fark hesabi no-op): 'fark SAYILABILIR' iddiasi KIRMIZI yanar (toplam=" +
      m3.farkToplam + ")", m3.farkToplam === 0, JSON.stringify(m3));

// M4: index.js'ten golge cagrisi SILINIRSE -> olcum biter ama FIYAT degismez.
const indexHam = fs.readFileSync(path.join(SRC, "index.js"), "utf8");
const capaM4 = "    golgeYaz(k, u, birimKurus);";
if (indexHam.split(capaM4).length - 1 !== 1) { throw new Error("M4 capasi YOK/COK"); }
const M4 = await indexYukle(indexHam.replace(capaM4, "    /* M4: golge cagrisi silindi */"));
const m4 = await mutantOlcum(M4);
iddia("M4 (index.js golge cagrisi silindi): olcum KIRMIZI yanar", m4.log === 0,
      JSON.stringify(m4));
iddia("M4'te FIYAT hala 73600 — golge SILINSE BILE musteri davranisi ayni",
      m4.birim === 73600, String(m4.birim));

// ---------------------------------------------------------------- rapor
gercekLog(ham.join("\n"));
gercekLog("");
if (hatalar.length) {
  gercekLog("SONUC: KIRMIZI ❌ — " + hatalar.length + " iddia kaldi:");
  for (const h of hatalar) { gercekLog("  - " + h); }
  process.exit(1);
}
gercekLog("SONUC: YESIL ✅ — " + (ham.filter((s) => s.startsWith("  ✅")).length) +
          " iddianin hepsi gecti (8 set)");
