/**
 * POST /api/shop/baslat BOT KAPISI (Cloudflare Turnstile) — kabul bataryasi (17 Eyl 2026).
 *
 * OLCULEN OLAY: 17 Eyl 03:45-05:30 bir bot 188 CALINTI KART denedi (iyzico 0 basarili,
 * iyzico zorunlu 3DS'e gecti). TEK siparis token'inda ~50 kart denenebildigi icin
 * `/baslat` istek hizi kolu (c03159ae) bu akisi durdurmuyordu: bot bir siparis acip ayni
 * token uzerinde onlarca kart deniyor. Hedef: bot `/baslat`a HIC siparis actiramasin.
 *
 * IDDIALAR (hepsi GERCEK worker kodundan; sahte D1 + sahte iyzico + sahte siteverify):
 *   V1 secret VAR + jeton YOK            -> 403 · D1'e siparis YAZILMAZ · iyzico ACILMAZ
 *   V2 siteverify success:false          -> 403
 *   V3 siteverify hostname YABANCI       -> 403
 *   V4 gecerli jeton                     -> 403 DEGIL ve iyzico ACILIR
 *   V5 secret YOK (henuz konmadi)        -> 403 DEGIL (FAIL-OPEN: yayin sirasi)
 *   V6 siteverify FIRLATIR               -> 403 DEGIL (FAIL-OPEN: CF duserse satis durmaz)
 *   V7 siteverify'a remoteip = CF-Connecting-IP iletilir
 *   V8 HAVALE yolu da kapsanir           -> jetonsuz 403 · D1'e YAZILMAZ
 *   V9 index.html: `turnstile_token` govdede · api.js ILK YUKTE DEGIL (yalniz fonksiyon
 *      icinde, `<script src>` etiketi YOK) · harici script HOST kumesi GENISLEMEDI
 *   M1 MUTANT: baslat() icindeki dogrulama cagrisi silinirse V1 KIRMIZI yanar
 *
 * Calistir: node shop/test/turnstile-kapisi.mjs  -> rc=0 ve "SONUC: YESIL"
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const SRC = path.join(SHOP, "src");
const TEMP_ONEK = "src-test-tmp-turnstile-";
const TEMP_DIZIN = path.join(SHOP, TEMP_ONEK + process.pid);

function jsonGom(kaynak) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(SRC, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) { throw new Error("JSON import gomulemedi"); }
  return cikti;
}

for (const ad of fs.readdirSync(SHOP)) {
  if (ad.startsWith(TEMP_ONEK)) { fs.rmSync(path.join(SHOP, ad), { recursive: true, force: true }); }
}
fs.mkdirSync(TEMP_DIZIN, { recursive: true });
process.on("exit", () => { fs.rmSync(TEMP_DIZIN, { recursive: true, force: true }); });
for (const ad of fs.readdirSync(SRC)) {
  if (/\.m?js$/.test(ad)) {
    fs.writeFileSync(path.join(TEMP_DIZIN, ad), jsonGom(fs.readFileSync(path.join(SRC, ad), "utf8")));
  }
}

let sayac = 0;
async function yukle(kaynak) {
  sayac += 1;
  const yol = path.join(TEMP_DIZIN, "index-turnstile-" + sayac + ".js");
  fs.writeFileSync(yol, jsonGom(kaynak));
  return await import(pathToFileURL(yol).href);
}

// --------------------------------------------------------------- sahte dis dunya
const URUN_ID = "test-turnstile-urun";
let iyzicoCagri = 0;
let siteverifyCagri = 0;
let siteverifyGovde = null;     // son cagrida gonderilen form (URLSearchParams)
let siteverifyPlani = null;     // {gonder:<obj>} | {firlat:true} | {bozukJson:true}

globalThis.fetch = async function (hedef, ayar) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (u.includes("challenges.cloudflare.com")) {
    siteverifyCagri += 1;
    const g = ayar && ayar.body;
    siteverifyGovde = g && typeof g.get === "function" ? g : new URLSearchParams(String(g || ""));
    if (siteverifyPlani && siteverifyPlani.firlat) { throw new Error("siteverify ulasilamadi"); }
    if (siteverifyPlani && siteverifyPlani.bozukJson) { return new Response("<html>", { status: 200 }); }
    return new Response(JSON.stringify((siteverifyPlani && siteverifyPlani.gonder) || {}),
      { status: 200, headers: { "Content-Type": "application/json" } });
  }
  if (u.includes("iyzico.test")) {
    iyzicoCagri += 1;
    return new Response(JSON.stringify({ status: "success", token: "t-" + iyzicoCagri,
      paymentPageUrl: "https://odeme.test/s" }), { status: 200 });
  }
  return new Response("{}", { status: 200 });   // telegram/eposta/olcum yan kanallari
};

function d1Sahte(kayitlar) {
  return {
    prepare(sql) {
      return { bind(...arg) { return {
        async all() {
          if (/FROM urunler/.test(sql)) {
            return { results: [{ id: URUN_ID, baslik: "Test Turnstile Urunu",
              kategori: "Tamirat", fiyat: "450 TL", parametrik: 0, gorsel: "",
              konfigur: "", tur: "", boy_secenekleri: "" }] };
          }
          return { results: [] };
        },
        async first() { return null; },
        async run() { kayitlar.push({ sql, arg }); return { meta: { changes: 1 } }; },
      }; } };
    },
  };
}

/** Tek bir /baslat cagrisi. secret===null -> env.TURNSTILE_SECRET HIC yok. */
async function cagir(mod, { secret = "gizli-test", jeton = null, siteverify = null,
                            odeme = "kart", ip = "203.0.113.7" } = {}) {
  siteverifyPlani = siteverify;
  siteverifyGovde = null;
  const kayitlar = [];
  const env = { SITE_URL: "https://pruvo3d.com", IYZICO_BASE_URL: "https://iyzico.test",
    IYZICO_API_KEY: "k", IYZICO_SECRET_KEY: "s", KATALOG: d1Sahte(kayitlar),
    HAVALE_IBAN: "TR000000000000000000000000", HAVALE_UNVAN: "PRUVO",
    BASLAT_RATE_LIMIT: { async limit() { return { success: true }; } } };
  if (secret !== null) { env.TURNSTILE_SECRET = secret; }
  const govde = { sozlesme_onay: true, odeme,
    sepet: [{ id: URUN_ID, malzeme: "PLA", renk: "Siyah", adet: 1 }],
    musteri: { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
               adres: "Test mahallesi test sokak no 1", sehir: "Mugla" } };
  if (jeton !== null) { govde.turnstile_token = jeton; }
  const once = iyzicoCagri;
  const svOnce = siteverifyCagri;
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": ip },
    body: JSON.stringify(govde),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let veri = null;
  try { veri = await cevap.clone().json(); } catch (e) { /* metin cevap */ }
  return { kod: cevap.status, hata: veri && veri.hata,
           d1Siparis: kayitlar.some((k) => /INSERT INTO siparisler/.test(k.sql)),
           iyzico: iyzicoCagri > once, siteverify: siteverifyCagri - svOnce };
}

const sonuclar = [];
function iddia(ad, kosul, detay) { sonuclar.push({ ad, kosul: Boolean(kosul), detay }); }

const kaynak = fs.readFileSync(path.join(SRC, "index.js"), "utf8");
const mod = await yukle(kaynak);
const GECERLI = { gonder: { success: true, hostname: "pruvo3d.com" } };

// ---------------------------------------------------------------- V1..V8
let r = await cagir(mod, { jeton: null, siteverify: GECERLI });
iddia("V1 secret var + jeton YOK -> 403, D1 yok, iyzico yok",
  r.kod === 403 && r.hata === "bot-dogrulama" && !r.d1Siparis && !r.iyzico, JSON.stringify(r));

r = await cagir(mod, { jeton: "   ", siteverify: GECERLI });
iddia("V1b jeton BOSLUK -> 403 ve siteverify'a HIC gidilmez",
  r.kod === 403 && r.hata === "bot-dogrulama" && r.siteverify === 0, JSON.stringify(r));

r = await cagir(mod, { jeton: "x", siteverify: { gonder: { success: false,
  "error-codes": ["invalid-input-response"] } } });
iddia("V2 siteverify success:false -> 403, D1 yok, iyzico yok",
  r.kod === 403 && r.hata === "bot-dogrulama" && !r.d1Siparis && !r.iyzico, JSON.stringify(r));

r = await cagir(mod, { jeton: "x", siteverify: { gonder: { success: true, hostname: "kotu.example" } } });
iddia("V3 hostname YABANCI -> 403, D1 yok, iyzico yok",
  r.kod === 403 && r.hata === "bot-dogrulama" && !r.d1Siparis && !r.iyzico, JSON.stringify(r));

r = await cagir(mod, { jeton: "x", siteverify: { gonder: { success: true } } });
iddia("V3b hostname YOK -> 403 (yesile katlanmaz)", r.kod === 403, JSON.stringify(r));

r = await cagir(mod, { jeton: "gecerli-jeton", siteverify: GECERLI });
iddia("V4 gecerli jeton -> 403 DEGIL, siteverify BIR kez cagrildi, iyzico ACILIR",
  r.kod !== 403 && r.iyzico && r.siteverify === 1, JSON.stringify(r));

r = await cagir(mod, { jeton: "x", siteverify: { gonder: { success: true, hostname: "www.pruvo3d.com" } } });
iddia("V4b hostname www.pruvo3d.com da KABUL", r.kod !== 403 && r.iyzico, JSON.stringify(r));

r = await cagir(mod, { secret: null, jeton: null, siteverify: GECERLI });
iddia("V5 secret YOK -> 403 DEGIL (fail-open) ve siteverify'a HIC gidilmez",
  r.kod !== 403 && r.iyzico && r.siteverify === 0, JSON.stringify(r));

r = await cagir(mod, { jeton: "x", siteverify: { firlat: true } });
iddia("V6 siteverify FIRLATIR -> 403 DEGIL (fail-open), iyzico acilir",
  r.kod !== 403 && r.iyzico, JSON.stringify(r));

r = await cagir(mod, { jeton: "x", siteverify: { bozukJson: true } });
iddia("V6b siteverify BOZUK JSON -> 403 DEGIL (fail-open)", r.kod !== 403, JSON.stringify(r));

r = await cagir(mod, { jeton: "jeton-7", siteverify: GECERLI, ip: "198.51.100.42" });
iddia("V7 siteverify govdesi: remoteip = CF-Connecting-IP, response = jeton",
  siteverifyGovde && siteverifyGovde.get("remoteip") === "198.51.100.42" &&
  siteverifyGovde.get("response") === "jeton-7" &&
  (siteverifyGovde.get("secret") || "") !== "",
  siteverifyGovde ? "remoteip=" + siteverifyGovde.get("remoteip") : "govde yok");

r = await cagir(mod, { jeton: null, odeme: "havale", siteverify: GECERLI });
iddia("V8 HAVALE yolu jetonsuz -> 403, D1'e siparis YAZILMAZ",
  r.kod === 403 && r.hata === "bot-dogrulama" && !r.d1Siparis, JSON.stringify(r));

r = await cagir(mod, { jeton: "x", odeme: "havale", siteverify: GECERLI });
iddia("V8b HAVALE gecerli jetonla -> 403 DEGIL ve D1'e YAZILIR",
  r.kod !== 403 && r.d1Siparis, JSON.stringify(r));

// ---------------------------------------------------------------- V9 (on yuz)
const html = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const API_URL = "challenges.cloudflare.com/turnstile/v0/api.js";
iddia("V9a istek govdesinde turnstile_token alani var",
  /turnstile_token:\s*turnstileJeton\(\)/.test(html), "yok");
iddia("V9b api.js ILK YUKTE DEGIL: <script src=...challenges...> etiketi YOK",
  !new RegExp('<script[^>]+src=["\'][^"\']*challenges\\.cloudflare\\.com').test(html), "etiket var");
// Tembel yukleme: api.js adresi YALNIZ bir fonksiyonun (turnstileYukle) okudugu sabitte
// gecer ve o fonksiyon yalniz odeme formu acilinca cagrilir.
const apiGecis = html.split(API_URL).length - 1;
iddia("V9c api.js adresi TEK yerde (sabit) gecer", apiGecis === 1, "adet=" + apiGecis);
iddia("V9d turnstileYukle() YALNIZ odeme formu acilinca cagrilir",
  (html.split(/turnstileYukle\(\)/).length - 1) === 2 &&      // tanim disi 1 cagri + 1 ic cagri yok
  /function odemeFormuGoster\(ac\)\{\s*\n\s*if\(ac\)\{ turnstileYukle\(\); \}/.test(html),
  "cagri sayisi=" + (html.split(/turnstileYukle\(\)/).length - 1));
iddia("V9e cevaptan sonra turnstile.reset() cagrilir (jeton tek kullanimlik)",
  /turnstile\.reset\(turnstileWidget\)/.test(html) &&
  (html.split(/turnstileSifirla\(\);/).length - 1) >= 2, "reset kablolamasi eksik");
iddia("V9f HATA_METNI['bot-dogrulama'] tanimli",
  /"bot-dogrulama":\s*"Güvenlik doğrulaması/.test(html), "yok");
/* 🔴 ISTISNANIN GENISLEMEDIGI OLCULUR: index.html'in yukledigi HARICI script HOST kumesi
   bugun {googletagmanager.com (rizali analitik), challenges.cloudflare.com (bot kapisi)}.
   Bu vaka yeni bir CDN/kutuphane eklenirse KIRMIZI yanar — "harici script yok" kuralina
   acilan delik BU IKISIYLE sinirli kalsin diye. */
const IZINLI_HOSTLAR = ["www.googletagmanager.com", "challenges.cloudflare.com"];
const scriptHostlari = [...html.matchAll(/\.src\s*=\s*"https:\/\/([^/"]+)/g)].map((m) => m[1])
  .concat([...html.matchAll(/<script[^>]+src="https:\/\/([^/"]+)/g)].map((m) => m[1]))
  .concat([...html.matchAll(/TURNSTILE_API\s*=\s*"https:\/\/([^/"]+)/g)].map((m) => m[1]));
const yabanci = [...new Set(scriptHostlari)].filter((h) => !IZINLI_HOSTLAR.includes(h));
iddia("V9g harici script HOST kumesi genislemedi (yalniz gtag + turnstile)",
  yabanci.length === 0, "yabanci=" + JSON.stringify(yabanci));

// ---------------------------------------------------------------- M1 mutant
const cagriSatiri =
  "  const botRed = await turnstileDogrula(request, env, govde && govde.turnstile_token);\n" +
  "  if (botRed) { return botRed; }\n";
const adet = kaynak.split(cagriSatiri).length - 1;
iddia("M1 capa kaynakta TEK", adet === 1, "adet=" + adet);
if (adet === 1) {
  const mutant = await yukle(kaynak.replace(cagriSatiri, ""));
  const m = await cagir(mutant, { jeton: null, siteverify: GECERLI });
  iddia("M1 mutant (dogrulama cagrisi silindi) V1'i KIRMIZI yakar",
    m.kod !== 403, JSON.stringify(m));
}

let kirmizi = 0;
for (const s of sonuclar) {
  if (!s.kosul) { kirmizi += 1; }
  console.log((s.kosul ? "  ✅ " : "  🔴 ") + s.ad + (s.kosul ? "" : "  -> " + s.detay));
}
console.log("IDDIA=" + sonuclar.length + " KIRMIZI=" + kirmizi);
console.log("SONUC: " + (kirmizi === 0 ? "YESIL" : "KIRMIZI"));
process.exit(kirmizi === 0 ? 0 : 1);
