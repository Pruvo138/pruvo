/**
 * ONIZLEME SURUMU KAPISI — kabul bataryasi (FOTO-DUZEN-d, 7 Eki 2026).
 *
 * `pruvo-shop`un onizleme surumu (shop/wrangler.onizleme.toml, `ONIZLEME = "1"`) canli
 * secret'lari DEVRALIR; iyzico anahtari dahil. Bu batarya onizlemede para yolunun kapali,
 * canlida ise davranisin AYNEN kaldigini GERCEK worker kodundan olcer (sahte D1 + sahte
 * iyzico + sahte siteverify; gercek ag 0).
 *
 * IDDIALAR
 *   O1  ONIZLEME=1: /baslat -> 503 onizleme-odeme-kapali · iyzico 0 · D1 yazimi 0 · siteverify 0
 *   O2  ONIZLEME=1: /donus, /olcum-donus, /fiyat -> 503 · iyzico 0
 *   O3  ONIZLEME YOK (canli): ayni /baslat gecerli jetonla iyzico'yu ACAR (kontrol)
 *   O4  ONIZLEME=1: /foto/acik 503-odeme DEGIL (bolum ucu kapanmadi)
 *   T1  canli (env bos): onizleme alaninda cozulmus jeton /baslat'ta 403
 *   T2  ONIZLEME_HOST dolu ama ONIZLEME yok: liste GENISLEMEZ (403)
 *   T3  ONIZLEME=1 + ONIZLEME_HOST: foto bot dogrulamasi o alani KABUL eder
 *   T4  ONIZLEME=1 + ONIZLEME_HOST: baska yabanci alan yine RED
 *   T5  canli iki alan her ortamda KABUL (foto + /baslat)
 *   T6  kaynakta elle yazilmis hostname listesi KALMADI (index.js + foto.js tek kaynaktan)
 *   MUTANTLAR (gecici kopya; calisma agacina yazim YOK):
 *   MO1 index.js'teki onizleme odeme kolu silinir   -> O1 KIRMIZI
 *   MO2 onizleme.js ONIZLEME kosulunu atlar         -> T2 KIRMIZI
 *   MO3 onizleme.js ONIZLEME_HOST'u yok sayar       -> T3 KIRMIZI
 *   O5  ONIZLEME=1 + anahtar: POST /yonet/foto/uretim-tik -> 200 tur ozeti (kopru-15, cron'suz onizleme)
 *   O6  canli + anahtar: ayni uc 404 · O7 yanlis anahtar: calismaz
 *   MO4 yonet.js uretim-tik onizleme kosulu silinir   -> O6 KIRMIZI
 *   MO0 kontrol (yalniz yorum eklenir)              -> hicbiri KIRMIZI degil
 *
 * Calistir: node shop/test/onizleme-kapisi.mjs  -> rc=0 ve "SONUC: YESIL"
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const SRC = path.join(SHOP, "src");
const TEMP_ONEK = "src-test-tmp-onizleme-";

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
const gecici = [];
process.on("exit", () => { for (const d of gecici) { fs.rmSync(d, { recursive: true, force: true }); } });

/** src/'nin gecici kopyasi (degisiklikler: {dosya: yeniKaynak}); kopya shop/ altinda src/ ile
 *  ayni derinlikte durur. */
let sayac = 0;
function kopya(degisiklik) {
  sayac += 1;
  const dizin = path.join(SHOP, TEMP_ONEK + process.pid + "-" + sayac);
  const src = dizin;   // src/ ile AYNI derinlik: "../../" importlari KOK'e cozulur
  fs.mkdirSync(src, { recursive: true });
  gecici.push(dizin);
  for (const ad of fs.readdirSync(SRC)) {
    if (/\.m?js$/.test(ad)) {
      const k = degisiklik && degisiklik[ad] !== undefined ? degisiklik[ad]
        : fs.readFileSync(path.join(SRC, ad), "utf8");
      fs.writeFileSync(path.join(src, ad), jsonGom(k));
    }
  }
  return src;
}
// foto.js "../../foto-uretim-veri.js" -> shop/<gecici>/src'den iki ust = shop/ ; KOK'teki
// manifest oraya bakmaz. Bu yuzden importu mutlak yola cevir.
function fotoKaynak(k) {
  // foto.js onizleme modulunu "../src/onizleme.js" ile alir; kopyada KOPYANIN onizleme.js'i
  // (mutant) kullanilsin diye "./" yapilir — aksi halde MO2/MO3 foto kolunda olu kalirdi.
  const n = k.split('from "../src/onizleme.js";').length - 1;
  if (n !== 1) { throw new Error("foto.js onizleme importu capasi " + n); }
  k = k.replace('from "../src/onizleme.js";', 'from "./onizleme.js";');
  return k.replace('import "../../foto-uretim-veri.js";',
    'import ' + JSON.stringify(pathToFileURL(path.join(KOK, "foto-uretim-veri.js")).href) + ';');
}
async function yukle(degisiklik) {
  const d = Object.assign({}, degisiklik || {});
  d["foto.js"] = fotoKaynak(d["foto.js"] !== undefined ? d["foto.js"]
    : fs.readFileSync(path.join(SRC, "foto.js"), "utf8"));
  const src = kopya(d);
  return {
    index: await import(pathToFileURL(path.join(src, "index.js")).href),
    foto: await import(pathToFileURL(path.join(src, "foto.js")).href),
  };
}

// --------------------------------------------------------------- sahte dis dunya
const URUN_ID = "test-onizleme-urun";
const ONIZLEME_ALANI = "foto-onizleme-pruvo-shop.ornek.workers.dev";
let iyzicoCagri = 0;
let siteverifyCagri = 0;
let siteverifyPlani = null;
let gercekAg = 0;

globalThis.fetch = async function (hedef) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (u.includes("challenges.cloudflare.com")) {
    siteverifyCagri += 1;
    return new Response(JSON.stringify((siteverifyPlani && siteverifyPlani.gonder) || {}),
      { status: 200, headers: { "Content-Type": "application/json" } });
  }
  if (u.includes("iyzico.test")) {
    iyzicoCagri += 1;
    return new Response(JSON.stringify({ status: "success", token: "t-" + iyzicoCagri,
      paymentPageUrl: "https://odeme.test/s", paymentStatus: "SUCCESS" }), { status: 200 });
  }
  if (u.includes(".test")) { return new Response("{}", { status: 200 }); }
  gercekAg += 1;
  return new Response("{}", { status: 200 });   // telegram/eposta/olcum yan kanallari
};

function d1Sahte(yazimlar) {
  const ifade = (sql) => ({
    bind() { return ifade(sql); },
    async all() {
      if (/FROM urunler/.test(sql)) {
        return { results: [{ id: URUN_ID, baslik: "Test Onizleme Urunu", kategori: "Tamirat",
          fiyat: "450 TL", parametrik: 0, gorsel: "", konfigur: "", tur: "", boy_secenekleri: "" }] };
      }
      return { results: [] };
    },
    async first() { return null; },
    async run() { yazimlar.push(sql); return { meta: { changes: 1 } }; },
  });
  return { prepare: ifade, async batch(l) { return l.map(() => ({ results: [] })); } };
}

function ortam(ek) {
  const yazimlar = [];
  const env = Object.assign({ SITE_URL: "https://pruvo3d.com", IYZICO_BASE_URL: "https://iyzico.test",
    IYZICO_API_KEY: "k", IYZICO_SECRET_KEY: "s", KATALOG: d1Sahte(yazimlar),
    TURNSTILE_SECRET: "gizli-test", TELEGRAM_API: "https://tg.test",
    HAVALE_IBAN: "TR000000000000000000000000", HAVALE_UNVAN: "PRUVO",
    BASLAT_RATE_LIMIT: { async limit() { return { success: true }; } },
    FIYAT_RATE_LIMIT: { async limit() { return { success: true }; } } }, ek || {});
  return { env, yazimlar };
}

async function istek(mod, ek, yol, yontem, govde, svHost, baslik) {
  siteverifyPlani = { gonder: { success: true, hostname: svHost || "pruvo3d.com" } };
  const { env, yazimlar } = ortam(ek);
  const iy0 = iyzicoCagri;
  const sv0 = siteverifyCagri;
  const ayar = { method: yontem, headers: Object.assign({ "Content-Type": "application/json",
    "CF-Connecting-IP": "203.0.113.9" }, baslik || {}) };
  if (govde !== undefined) { ayar.body = JSON.stringify(govde); }
  const c = await mod.index.default.fetch(new Request("https://pruvo3d.com/api/shop" + yol, ayar),
    env, { waitUntil() {} });
  let v = null;
  try { v = await c.clone().json(); } catch (e) { /* metin */ }
  return { kod: c.status, hata: v && v.hata, govde: v, iyzico: iyzicoCagri - iy0, siteverify: siteverifyCagri - sv0,
           d1Yazim: yazimlar.filter((s) => /INSERT|UPDATE|DELETE/i.test(s)).length };
}

const SEPET = { sozlesme_onay: true, odeme: "kart", turnstile_token: "jeton",
  sepet: [{ id: URUN_ID, malzeme: "PLA", renk: "Siyah", adet: 1 }],
  musteri: { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
             adres: "Test mahallesi test sokak no 1", sehir: "Mugla" } };
const ONZ = { ONIZLEME: "1", ONIZLEME_HOST: ONIZLEME_ALANI };

async function fotoBot(mod, ek, host) {
  siteverifyPlani = { gonder: { success: true, hostname: host } };
  const { env } = ortam(ek);
  const r = new Request("https://x.test/", { headers: { "CF-Connecting-IP": "203.0.113.9" } });
  return await mod.foto.botDogrula(r, env, "jeton");
}

/** Tum iddialari bir modul ustunde kosar; {ad: bool} doner. */
async function batarya(mod) {
  const s = {};
  let r = await istek(mod, ONZ, "/baslat", "POST", SEPET);
  s.O1 = r.kod === 503 && r.hata === "onizleme-odeme-kapali" && r.iyzico === 0 && r.d1Yazim === 0 &&
    r.siteverify === 0;
  s._O1 = JSON.stringify(r);
  const o2 = [];
  o2.push(await istek(mod, ONZ, "/donus?token=t-1", "POST", undefined));
  o2.push(await istek(mod, ONZ, "/donus?token=t-1", "GET", undefined));
  o2.push(await istek(mod, ONZ, "/olcum-donus", "POST", { no: "X", bilet: "y" }));
  o2.push(await istek(mod, ONZ, "/fiyat", "POST", SEPET));
  s.O2 = o2.every((x) => x.kod === 503 && x.iyzico === 0);
  s._O2 = JSON.stringify(o2);
  r = await istek(mod, {}, "/baslat", "POST", SEPET);
  s.O3 = r.kod !== 503 && r.iyzico > 0;
  s._O3 = JSON.stringify(r);
  r = await istek(mod, ONZ, "/foto/acik", "GET", undefined);
  s.O4 = r.hata !== "onizleme-odeme-kapali";
  s._O4 = JSON.stringify(r);
  r = await istek(mod, {}, "/baslat", "POST", SEPET, ONIZLEME_ALANI);
  s.T1 = r.kod === 403 && r.iyzico === 0;
  s._T1 = JSON.stringify(r);
  r = await istek(mod, { ONIZLEME_HOST: ONIZLEME_ALANI }, "/baslat", "POST", SEPET, ONIZLEME_ALANI);
  const t2foto = await fotoBot(mod, { ONIZLEME_HOST: ONIZLEME_ALANI }, ONIZLEME_ALANI);
  s.T2 = r.kod === 403 && r.iyzico === 0 && t2foto === false;
  s._T2 = JSON.stringify(r) + " foto=" + t2foto;
  s.T3 = (await fotoBot(mod, ONZ, ONIZLEME_ALANI)) === true;
  s.T4 = (await fotoBot(mod, ONZ, "kotu.example")) === false &&
         (await fotoBot(mod, { ONIZLEME: "1", ONIZLEME_HOST: "" }, "")) === false;
  // URETIM TIKI (kopru-15, 8 Eki): onizleme cron'suz -> panel anahtariyla tek tur; canlida uc YOK.
  const YA = { "X-Yonet-Anahtar": "yonet-test-anahtar" };
  const YE = Object.assign({ YONET_ANAHTAR: "yonet-test-anahtar" }, ONZ);
  r = await istek(mod, YE, "/yonet/foto/uretim-tik", "POST", {}, undefined, YA);
  s.O5 = r.kod === 200 && !!r.govde && r.govde.atlandi === "yapilandirma" && r.iyzico === 0;
  s._O5 = JSON.stringify(r);
  r = await istek(mod, { YONET_ANAHTAR: "yonet-test-anahtar" }, "/yonet/foto/uretim-tik", "POST", {}, undefined, YA);
  s.O6 = r.kod === 404;
  s._O6 = JSON.stringify(r);
  r = await istek(mod, YE, "/yonet/foto/uretim-tik", "POST", {}, undefined, { "X-Yonet-Anahtar": "yanlis" });
  s.O7 = r.kod !== 200 && !(r.govde && "atlandi" in r.govde);
  s._O7 = JSON.stringify(r);
  r = await istek(mod, {}, "/baslat", "POST", SEPET, "www.pruvo3d.com");
  s.T5 = (await fotoBot(mod, {}, "pruvo3d.com")) === true &&
         (await fotoBot(mod, ONZ, "www.pruvo3d.com")) === true && r.kod !== 403 && r.iyzico > 0;
  s._T5 = JSON.stringify(r);
  return s;
}

const sonuclar = [];
function iddia(ad, kosul, detay) { sonuclar.push({ ad, kosul: Boolean(kosul), detay }); }

const asil = await batarya(await yukle(null));
const AD = {
  O1: "O1 ONIZLEME=1 /baslat -> 503, iyzico 0, D1 yazimi 0, siteverify 0",
  O2: "O2 ONIZLEME=1 /donus GET+POST, /olcum-donus, /fiyat -> 503, iyzico 0",
  O3: "O3 canli (ONIZLEME yok) /baslat iyzico'yu ACAR (kontrol)",
  O4: "O4 ONIZLEME=1 /foto/acik odeme koluna takilmaz",
  O5: "O5 ONIZLEME=1 + anahtar: POST /yonet/foto/uretim-tik -> 200 tur ozeti (yapilandirma yok -> atlandi)",
  O6: "O6 canli + anahtar: /yonet/foto/uretim-tik -> 404 (uc yalniz onizlemede)",
  O7: "O7 ONIZLEME=1 + yanlis anahtar: uretim-tik calismaz",
  T1: "T1 canli: onizleme alaninda cozulmus jeton /baslat'ta 403",
  T2: "T2 ONIZLEME_HOST tek basina listeyi GENISLETMEZ (/baslat + foto)",
  T3: "T3 ONIZLEME=1 + ONIZLEME_HOST: foto bot dogrulamasi onizleme alanini KABUL eder",
  T4: "T4 onizlemede yabanci/bos alan yine RED",
  T5: "T5 canli iki alan her ortamda KABUL",
};
for (const k of Object.keys(AD)) { iddia(AD[k], asil[k], asil["_" + k] || ""); }

const IDX = fs.readFileSync(path.join(SRC, "index.js"), "utf8");
const FOTO = fs.readFileSync(path.join(SRC, "foto.js"), "utf8");
const ONZK = fs.readFileSync(path.join(SRC, "onizleme.js"), "utf8");
const YON = fs.readFileSync(path.join(SRC, "yonet.js"), "utf8");
iddia("T6 index.js + foto.js'te elle yazilmis Turnstile alan listesi YOK",
  !/\[\s*"pruvo3d\.com",\s*"www\.pruvo3d\.com"\s*\]/.test(IDX) &&
  !/\[\s*"pruvo3d\.com",\s*"www\.pruvo3d\.com"\s*\]/.test(FOTO), "");

// ---------------------------------------------------------------- mutantlar
const MUTANT = [
  ["MO0", null, "", "", null, []],
  ["MO1", "index.js",
    '      if (onizlemeOdemeKapali(env, yol)) { return json({ hata: "onizleme-odeme-kapali" }, 503, env); }\n',
    "", null, ["O1", "O2"]],
  ["MO4", "yonet.js", '  if (altYol === "/foto/uretim-tik" && m === "POST" && onizlemeMi(env)) {\n',
    '  if (altYol === "/foto/uretim-tik" && m === "POST") {\n', null, ["O6"]],
  ["MO2", "onizleme.js", "  const ek = onizlemeMi(env) ? String(env.ONIZLEME_HOST || \"\").trim() : \"\";\n",
    "  const ek = String(env.ONIZLEME_HOST || \"\").trim();\n", null, ["T2"]],
  ["MO3", "onizleme.js", "  return ek !== \"\" && h === ek;\n", "  return false;\n", null, ["T3"]],
];
for (const [ad, dosya, capa, yeni, , beklenen] of MUTANT) {
  let degisiklik = {};
  if (ad === "MO0") {
    degisiklik = { "index.js": "/* FOTO-DUZEN-d kontrol mutanti */\n" + IDX };
  } else {
    const kaynak = { "index.js": IDX, "onizleme.js": ONZK, "yonet.js": YON }[dosya];
    const adet = kaynak.split(capa).length - 1;
    iddia(ad + " capa kaynakta TEK", adet === 1, "adet=" + adet);
    if (adet !== 1) { continue; }
    degisiklik[dosya] = kaynak.replace(capa, yeni);
  }
  const m = await batarya(await yukle(degisiklik));
  const kirmizi = Object.keys(AD).filter((k) => !m[k]);
  const tutar = JSON.stringify(kirmizi.slice().sort()) === JSON.stringify(beklenen.slice().sort());
  iddia(ad + " mutant KIRMIZI kumesi = " + JSON.stringify(beklenen), tutar, "olculen=" + JSON.stringify(kirmizi));
}

let kirmizi = 0;
for (const s of sonuclar) {
  if (!s.kosul) { kirmizi += 1; }
  console.log((s.kosul ? "  ✅ " : "  🔴 ") + s.ad + (s.kosul ? "" : "  -> " + s.detay));
}
console.log("IDDIA=" + sonuclar.length + " KIRMIZI=" + kirmizi + " IYZICO_SAHTE=" + iyzicoCagri +
  " GERCEK_AG=" + gercekAg);
console.log("SONUC: " + (kirmizi === 0 && gercekAg === 0 ? "YESIL" : "KIRMIZI"));
process.exit(kirmizi === 0 && gercekAg === 0 ? 0 : 1);
