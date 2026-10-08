/**
 * FOTOGRAFTAN URETIM — KATEGORI KAYDI + LITOFAN (deterministik kol) kabul testi.
 *
 * Kapsam: foto-uretim-veri.js tur kaydi alanlari · shop/src/foto.js /foto/litofan ucu, odeme
 * kalemi secimi, kuyruk 'uretec-bekliyor' · yonet.js uretec girdi/yukle uclari · plaket regresyonu.
 *
 *   L1 KAYIT        : her tur girdi/kol/olcu_mm/renk_bolgeleri/malzemeler gecerli; saglayici turleri
 *                     = TUR_ORTAM anahtarlari; deterministik ∩ TUR_ORTAM = ∅; malzeme ⊆ FILAMENT_SIRA;
 *                     litofanda ABS 0
 *   L2 FIYAT YOK    : /foto/acik'te litofan 0 · /foto/litofan 400 tur-kapali · /baslat litofan 400
 *   L3 FIYAT+ORNEK  : /foto/litofan 200 -> R2'de 1 nesne, foto_isler 'hazir', kredi defteri 0,
 *                     SAGLAYICI cagrisi 0; bozuk/oransiz harita + /foto/onizleme'den litofan RED
 *   L4 /baslat      : tutar = tablo x adet; secim listede degilse 400; ABS ayak 400
 *   L5 KUYRUK       : odeninca 'uretec-bekliyor'; 3 cron turu sonra AYNI + saglayici sayaci 0;
 *                     saglayici anahtari yokken de kuyruga girer (ozet bugunkuyle ayni)
 *   L6 PANEL        : yetkisiz yukleme reddedilir (yonet kapisi: 401/403/404) · bozuk imza 400 ·
 *                     gecerli 3MF -> 'hazir' + R2 · ikinci yukleme 409 · girdi indir = harita
 *   L7 PLAKET       : ayni sahte ortamda onizleme -> /baslat -> kuyruk 'build-baslat' (bugunku gibi)
 *   L10 URETEC ONIZL: sentetik `isimlik` (kopya veri dosyasinda) -> /foto/onizleme 'uretec-onizleme' + R2
 *                     girdi.json -> GERCEK koşucu (sahte wrangler/uretec, ortak SQLite dosyasi) ->
 *                     'onizleme-hazir' -> durum/gorsel -> /baslat -> 'uretec-bekliyor' -> KOPYA KOLU 'hazir'
 *   L11 TURETILMIS  : kopru-15 dilim-3 — sentetik `turetik` (olcu_ekseni turetilmis): onizleme istemcinin olcu_mm'sini
 *                     OKUMAZ (satir/girdi 0) · onizlemesiz siparis 400 · GERCEK koşucu olculen uzun kenari (123,4 ->
 *                     123) satira yazar · durum fiyat_kurus = 123 x 1000 + olcu_kaynagi · istemci sahte olcu/fiyatla
 *                     siparis -> satir sunucunun olcusu (fark 0) · aralik disi (250,5) -> uretec reddi metni
 *   L8 SAKLAMA      : saglayici env'siz cron: 73 sa onceki siparise girmemis litofan haritasi R2'den
 *                     silinir + satir 'silindi', saglayici cagrisi 0; siparise girmis harita KALIR
 *
 * MUTANTLAR: os.tmpdir()'de shop/src + foto-uretim-veri.js + secenekler.js IZOLE kopyasi
 * (calisma agacina yazim YOK; kopya cikista silinir). M1..M5 hedef grubu KIRMIZIYA cevirmeli,
 * M0 (yorum) hicbir grubu cevirmemeli. Son satir `SURVIVOR=<n>`; n>0 ya da kirmizi -> rc=1.
 * CIKIS KODU: 0 yesil · 1 kirmizi · 3 OLCULEMEDI (modul/kopru kurulamadi).
 */

// ---- JSON IMPORT KOPRUSU (foto-uretim.mjs ile ayni gerekce; uretim kodunu ETKILEMEZ) ----
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) {" +
  "    return { ...r, format: 'json', importAttributes: { type: 'json' } }; }" +
  "  return r; }"));

import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import readline from "node:readline";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");

let kirmizi = 0;
const ol = (ad, kosul, ek) => {
  if (kosul) { console.log("  ✅ " + ad); } else { kirmizi++; console.log("  ❌ " + ad + (ek ? " — " + ek : "")); }
};

// ---------------------------------------------------------------- gercek SQLite koprusu

function koprukur(dbYolu) {
  const p = spawn("python3", [path.join(BURASI, "ortak", "sqlite-koprusu.py")],
                  { stdio: ["pipe", "pipe", "inherit"],
                    env: dbYolu ? { ...process.env, SQLITE_KOPRU_DB: dbYolu } : process.env });
  const rl = readline.createInterface({ input: p.stdout });
  const bekleyen = [];
  rl.on("line", (s) => { const c = bekleyen.shift(); if (c) { c(JSON.parse(s)); } });
  const istek = (o) => new Promise((coz) => { bekleyen.push(coz); p.stdin.write(JSON.stringify(o) + "\n"); });
  const hazir = new Promise((coz) => bekleyen.push(coz));
  const d1 = {
    prepare(sql) {
      let binds = [];
      const st = {
        bind(...b) { binds = b; return st; },
        async all() { const c = await istek({ sql, binds, mod: "all" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return { results: c.results, meta: c.meta, success: true }; },
        async first() { const c = await istek({ sql, binds, mod: "all" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return c.results[0] || null; },
        async run() { const c = await istek({ sql, binds, mod: "run" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return { meta: c.meta, success: true }; },
      };
      return st;
    },
  };
  return { d1, hazir, kapat: () => p.stdin.end() };
}

function r2Kur() {
  const m = new Map();
  return {
    m,
    async put(k, v, o) { m.set(k, { bayt: new Uint8Array(v), httpMetadata: (o && o.httpMetadata) || {} }); },
    async get(k) { const x = m.get(k); return x ? { body: x.bayt, httpMetadata: x.httpMetadata } : null; },
    async delete(k) { m.delete(k); },
    async list() { return { objects: [] }; },
  };
}

// ---------------------------------------------------------------- sahte ag

const TABAN = "https://saglayici.test/openapi";
const P = { saglayici: 0, iyzico: 0 };
let sayac = 0;
const yanit = (v, kod) => new Response(JSON.stringify(v), { status: kod || 200, headers: { "Content-Type": "application/json" } });
const PNG_IMZA = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
const SAGLAYICI_PNG = Uint8Array.from([...PNG_IMZA, ...new Array(64).fill(7)]);

globalThis.fetch = async function sahteFetch(hedef, init) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  const yontem = (init && init.method) || "GET";
  if (u.startsWith(TABAN)) {
    // SAGLAYICI SAYACI: litofan kolunda bu sayi DEGISMEMELI.
    P.saglayici++;
    const yol = u.slice(TABAN.length);
    if (yol === "/v1/balance") { return yanit({ balance: 100000 }); }
    if (yontem === "POST" && /\/v1\/prototype$/.test(yol)) { return yanit({ result: "gorev-" + (++sayac) + "-aaaa" }); }
    if (/\/v1\/prototype\/.+$/.test(yol)) {
      return yanit({ status: "SUCCEEDED", consumed_credits: 6, image_urls: ["https://dosya.test/onizleme.png?Expires=1"] });
    }
    // Build gecici hata: plaket satiri 'build-baslat'ta kalir (L7 kuyruk asamasini olcer).
    if (yontem === "POST" && /\/v1\/build$/.test(yol)) { return yanit({ message: "gecici" }, 503); }
    return yanit({ message: "bilinmeyen" }, 404);
  }
  if (u.startsWith("https://dosya.test/onizleme.png")) {
    return new Response(SAGLAYICI_PNG, { headers: { "Content-Type": "image/png", "Content-Length": String(SAGLAYICI_PNG.length) } });
  }
  if (u.includes("challenges.cloudflare.com/turnstile")) { return yanit({ success: true, hostname: "pruvo3d.com" }); }
  if (u.startsWith("https://telegram.test")) { return yanit({ ok: true }); }
  if (u.startsWith("https://iyzico.test")) {
    P.iyzico++;
    return yanit({ status: "success", token: "iyz-" + P.iyzico, paymentPageUrl: "https://odeme.test/sayfa" });
  }
  throw new Error("TESTTE BEKLENMEYEN AG ISTEGI: " + u);
};

// ---------------------------------------------------------------- ortam + yardimcilar

const limiter = () => ({ limit: async () => ({ success: true }) });
function envKur(d1, r2, ek) {
  return {
    KATALOG: d1, OZEL_DOSYA: r2, SITE_URL: "https://pruvo3d.com",
    IYZICO_BASE_URL: "https://iyzico.test", IYZICO_API_KEY: "k", IYZICO_SECRET_KEY: "s",
    TELEGRAM_TOKEN: "t", TELEGRAM_API: "https://telegram.test", TELEGRAM_CHAT: "1",
    TURNSTILE_SECRET: "ts", YONET_ANAHTAR: "yonet-test-anahtari",
    BASLAT_RATE_LIMIT: limiter(), FIYAT_RATE_LIMIT: limiter(), FOTO_RATE_LIMIT: limiter(),
    URETIM_API_TABAN: TABAN, URETIM_TUR_ONEK: "tur-onek", URETIM_TUR_PLAKET: "tur-plaket", URETIM_TUR_FIGUR: "tur-figur", URETIM_API_ANAHTAR: "sahte-anahtar",
    ...(ek || {}),
  };
}
const ctx = { bekleyen: [], waitUntil(p) { this.bekleyen.push(p); } };
const YONET = { "X-Yonet-Anahtar": "yonet-test-anahtari" };
const musteri = { ad: "Deneme Musteri", tel: "05000000000", eposta: "deneme@ornek.test", adres: "Deneme mahallesi 1", sehir: "Ankara" };

/** Gecerli IHDR'li PNG (gri harita yerine); govde GORSEL_EN_AZ_BAYT ustune dolgu. */
function pngYap(en, boy) {
  const b32 = (n) => [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255];
  return Uint8Array.from([...PNG_IMZA, 0, 0, 0, 13, 0x49, 0x48, 0x44, 0x52, ...b32(en), ...b32(boy),
    8, 0, 0, 0, 0, 0, 0, 0, 0, ...new Array(3000).fill(5)]);
}
const uri = (bayt, tip) => "data:image/" + (tip || "png") + ";base64," + Buffer.from(bayt).toString("base64");
const HARITA = pngYap(400, 300);
const UCMF = Uint8Array.from([0x50, 0x4B, 0x03, 0x04, ...new TextEncoder().encode("sahte-uretec-3mf-govdesi-litofan")]);

/** Kok dizinden worker + foto modulu; modulun KENDI veri nesnesi (kopyada ayri nesne). */
async function modulKur(kok) {
  const modul = (await import(url.pathToFileURL(path.join(kok, "shop", "src", "index.js")).href)).default;
  const foto = await import(url.pathToFileURL(path.join(kok, "shop", "src", "foto.js")).href);
  return { modul, foto, VERI: globalThis.PRUVO_FOTO, SECENEK: globalThis.PRUVO_SECENEK };
}

function istekKur(modul, env) {
  return async function istek(yol, o) {
    o = o || {};
    const basliklar = { "CF-Connecting-IP": o.ip || "198.51.100.7", ...(o.basliklar || {}) };
    let govde;
    if (o.ham) { govde = o.ham; } else if (o.govde) { basliklar["Content-Type"] = "application/json"; govde = JSON.stringify(o.govde); }
    const r = await modul.fetch(new Request("https://pruvo3d.com/api/shop" + yol, {
      method: o.yontem || (govde ? "POST" : "GET"), headers: basliklar, body: govde }), env, ctx);
    let v = null; let bayt = null; const tip = r.headers.get("Content-Type") || "";
    if (tip.includes("json")) { try { v = await r.json(); } catch (e) { v = null; } } else { bayt = new Uint8Array(await r.arrayBuffer()); }
    return { kod: r.status, v, bayt, tip };
  };
}

const ornek = (tur) => ({ tur, olcu_mm: 120, foto: "https://media.pruvo3d.com/t-foto.webp",
  onizleme: "https://media.pruvo3d.com/t-onizleme.webp", baski: "https://media.pruvo3d.com/t-baski.webp", not: "test" });
const litofanGovde = (ek) => ({ tur: "litofan", olcu_mm: 120, gorsel: uri(HARITA), aydinlatma_onay: true,
  turnstile_token: "jeton", ...(ek || {}) });

// ---------------------------------------------------------------- SENARYO (canli + her mutant)

/** Gruplu sonuc: {L2: [{ad, ok, ek}], ...}. Her kosum TEMIZ SQLite + temiz R2 ile. */
async function senaryo(ms) {
  const { modul, foto, VERI } = ms;
  const g = { L2: [], L3: [], L4: [], L5: [], L6: [], L7: [], L8: [], L9: [] };
  const iddia = (grup, ad, ok, ek) => g[grup].push({ ad, ok: !!ok, ek: ek || "" });
  const k = koprukur(); await k.hazir;
  const d1 = k.d1; const r2 = r2Kur();
  const env = envKur(d1, r2);
  const istek = istekKur(modul, env);
  const surum = VERI.onay_surum;
  const yedekOrnek = VERI.ornekler.splice(0);
  try {
    VERI.ornekler.push(ornek("litofan"));
    const simdi = new Date().toISOString();

    // ---- L9: uretec olcu.json (sozlesme §3) + svg + aydinlatma kolu (saf fonksiyonlar)
    const ko = { tur: "litofan", olcu_mm: 140 };
    const oj = (ek) => ({ sozlesme: 1, kategori: "litofan", uzun_kenar_mm: 140.0, kutu_mm: { x: 140, y: 96, z: 3 },
                          renk_sayisi: 2, sizdirmaz: true, ...ek });
    iddia("L9", "gecerli olcu.json -> ''", foto.uretecOlcuDogrula(oj({}), ko) === "", foto.uretecOlcuDogrula(oj({}), ko));
    iddia("L9", "sizdirmaz:false -> elle (sizdirmaz-degil)", foto.uretecOlcuDogrula(oj({ sizdirmaz: false }), ko) === "sizdirmaz-degil",
          foto.uretecOlcuDogrula(oj({ sizdirmaz: false }), ko));
    iddia("L9", "uzun kenar %1 disi (142) -> uzun-kenar-tolerans; %1 ici (141,2) gecer",
          foto.uretecOlcuDogrula(oj({ uzun_kenar_mm: 142 }), ko) === "uzun-kenar-tolerans" &&
          foto.uretecOlcuDogrula(oj({ uzun_kenar_mm: 141.2 }), ko) === "", "");
    iddia("L9", "renk 5 -> renk-fazla · kategori uyusmaz · aralik disi olcu",
          foto.uretecOlcuDogrula(oj({ renk_sayisi: 5 }), ko) === "renk-fazla" &&
          foto.uretecOlcuDogrula(oj({ kategori: "plaket" }), ko) === "kategori-uyusmaz" &&
          foto.uretecOlcuDogrula(oj({ uzun_kenar_mm: 250 }), { tur: "litofan", olcu_mm: 250 }) === "olcu-aralik-disi", "");
    // G2b mimar karari (7 Eki): plaka 300 (manifest PLAKA_MM, tek kaynak) · yapboz 100-190.
    const yk = { tur: "yapboz", olcu_mm: 190 };
    const yj = (ek) => ({ sozlesme: 1, kategori: "yapboz", uzun_kenar_mm: 190.0, kutu_mm: { x: 284.5, y: 192, z: 6.3 },
                          renk_sayisi: 1, sizdirmaz: true, ...ek });
    iddia("L9", "plaka 300: kutu 290 gecer, 310 plaka-disi; PLAKA_MM manifestten 300",
          VERI.PLAKA_MM === 300 && foto.uretecOlcuDogrula(yj({ kutu_mm: { x: 290, y: 192, z: 6 } }), yk) === "" &&
          foto.uretecOlcuDogrula(yj({ kutu_mm: { x: 310, y: 192, z: 6 } }), yk) === "plaka-disi",
          foto.uretecOlcuDogrula(yj({ kutu_mm: { x: 310, y: 192, z: 6 } }), yk));
    iddia("L9", "yapboz 190 gecer (raf duzeni 284×192), 200 olcu-aralik-disi",
          foto.uretecOlcuDogrula(yj({}), yk) === "" &&
          foto.uretecOlcuDogrula(yj({ uzun_kenar_mm: 200 }), { tur: "yapboz", olcu_mm: 200 }) === "olcu-aralik-disi",
          foto.uretecOlcuDogrula(yj({ uzun_kenar_mm: 200 }), { tur: "yapboz", olcu_mm: 200 }));
    iddia("L9", "svg: script/olay/harici referans RED, temiz svg gecer",
          VERI.svgDogrula("<svg><script>x()</script></svg>") === "svg-script" &&
          VERI.svgDogrula("<svg onload=\"x()\"></svg>") === "svg-script" &&
          VERI.svgDogrula("<svg><image href=\"https://ornek.test/a.png\"/></svg>") === "svg-harici-referans" &&
          VERI.svgDogrula("<svg>" + "a".repeat(205 * 1024) + "</svg>") === "svg-buyuk" &&
          VERI.svgDogrula("<svg viewBox=\"0 0 10 10\"><path d=\"M0 0L10 10\" fill=\"url(#g)\"/></svg>") === "", "");
    const aktarimMaddeleri = VERI.onay.aydinlatma.filter((x) => x.kol === "M").map((x) => x.metin);
    const litM = VERI.aydinlatmaMaddeleri("litofan");
    iddia("L9", "D kategorisinde aktarim maddesi 0 (aktarim rizasi cumlesi dahil); plakette tum maddeler",
          aktarimMaddeleri.length > 0 && litM.filter((m) => aktarimMaddeleri.includes(m)).length === 0 &&
          VERI.aydinlatmaMaddeleri("plaket").length === VERI.onay.aydinlatma.length, JSON.stringify(litM.length));

    // ---- L2: acilis anahtari YOK (fiyat tablosu kalkti; Okan 7 Eki)
    const a2 = await istek("/foto/acik");
    iddia("L2", "anahtar yokken /foto/acik'te litofan 0",
          a2.kod === 200 && !(a2.v.turler || []).some((t) => t.kod === "litofan"), JSON.stringify(a2.v));
    // Canli D1'in bugunku hali: `foto_acik` tablosu YOK (goc uygulanmadi) ya da okuma hatasi -> 0 tur.
    for (const hata of ["D1_ERROR: no such table: foto_acik: SQLITE_ERROR", "D1_ERROR: network"]) {
      const kume = await foto.acikAnahtari({ KATALOG: { prepare() { throw new Error(hata); } } });
      iddia("L2", "anahtar okunamaz (" + hata.slice(10, 23) + ") -> acik tur 0 (fail-closed, deploy edilse de canlida tur acilmaz)",
            kume instanceof Set && kume.size === 0 && foto.acikTurler(kume).length === 0 &&
            foto.acikTurler(new Set(VERI.turler.map((t) => t.kod))).length > 0, String(kume && kume.size));
    }
    const l2 = await istek("/foto/litofan", { ip: "10.2.0.1", govde: litofanGovde({ onay_surum: surum }) });
    iddia("L2", "anahtar yokken /foto/litofan 400 tur-kapali", l2.kod === 400 && l2.v && l2.v.hata === "tur-kapali", JSON.stringify(l2.v));
    const isEl = "a".repeat(32);
    await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih) VALUES (?, 'litofan', 120, 'z', ?, 'hazir', ?)")
      .bind(isEl, simdi, simdi).run();
    const iyOnce = P.iyzico;
    const b2 = await istek("/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: isEl, olcu_mm: 120, adet: 1, secim: { panel_malzeme: "PLA", ayak_malzeme: "PLA", ayak_renk: "Beyaz" } }] } });
    iddia("L2", "anahtar yokken /baslat litofan kalemi 400 (odeme baslamaz)", b2.kod === 400 && P.iyzico === iyOnce, JSON.stringify(b2.v));

    // ---- L3: acilis anahtari + ornek VAR
    await d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('litofan', 1, 'x')").run();
    const sgOnce = P.saglayici;
    const a3 = await istek("/foto/acik");
    const lt = a3.v && (a3.v.turler || []).find((t) => t.kod === "litofan");
    iddia("L3", "anahtarla /foto/acik litofan 80..200 mm (13 olcu) FORMULDEN sunar (120 mm = 120000)", !!lt && lt.olculer.length === 13 &&
          lt.olculer.every((o) => o.fiyat_kurus === o.mm * 1000) && lt.olculer.some((o) => o.mm === 120 && o.fiyat_kurus === 120000),
          JSON.stringify(a3.v));
    const r2Once = r2.m.size;
    const l3 = await istek("/foto/litofan", { ip: "10.3.0.1", govde: litofanGovde({ onay_surum: surum }) });
    const isNo = l3.v && l3.v.is;
    iddia("L3", "/foto/litofan 200 + is numarasi", l3.kod === 200 && /^[a-f0-9]{32}$/.test(isNo || ""), JSON.stringify(l3.v));
    const nesne = r2.m.get("foto-onizleme/" + isNo + ".png");
    iddia("L3", "R2'de tam 1 yeni nesne = gonderilen harita", r2.m.size === r2Once + 1 && !!nesne &&
          Buffer.from(nesne.bayt).equals(Buffer.from(HARITA)), String(r2.m.size - r2Once));
    const fi = isNo ? await d1.prepare("SELECT tur, asama, kredi, gorev, hazir_tarih FROM foto_isler WHERE is_no = ?").bind(isNo).first() : null;
    iddia("L3", "foto_isler satiri 'hazir', kredi 0, gorev bos", !!fi && fi.tur === "litofan" && fi.asama === "hazir" &&
          fi.kredi === 0 && fi.gorev === "" && !!fi.hazir_tarih, JSON.stringify(fi));
    const kr = await d1.prepare("SELECT COUNT(*) AS n FROM foto_kredi").first();
    iddia("L3", "foto_kredi defterine yazim 0", kr.n === 0, String(kr.n));
    iddia("L3", "SAGLAYICI cagrisi 0 (/foto/acik + /foto/litofan)", P.saglayici === sgOnce, String(P.saglayici - sgOnce));
    const oran = await istek("/foto/litofan", { ip: "10.3.0.2", govde: litofanGovde({ onay_surum: surum, gorsel: uri(pngYap(1200, 200)) }) });
    iddia("L3", "en/boy 6:1 harita 400 gorsel-gecersiz", oran.kod === 400 && oran.v.hata === "gorsel-gecersiz", JSON.stringify(oran.v));
    const buyuk = await istek("/foto/litofan", { ip: "10.3.0.3", govde: litofanGovde({ onay_surum: surum, gorsel: uri(pngYap(1300, 900)) }) });
    iddia("L3", "uzun kenar > 1200 px 400", buyuk.kod === 400 && buyuk.v.hata === "gorsel-gecersiz", JSON.stringify(buyuk.v));
    const jpeg = Uint8Array.from([0xFF, 0xD8, 0xFF, 0xE0, ...new Array(3000).fill(1)]);
    const jp = await istek("/foto/litofan", { ip: "10.3.0.4", govde: litofanGovde({ onay_surum: surum, gorsel: uri(jpeg, "jpeg") }) });
    iddia("L3", "PNG olmayan (orijinal foto) 400", jp.kod === 400 && jp.v.hata === "gorsel-gecersiz", JSON.stringify(jp.v));
    const onaysiz = await istek("/foto/litofan", { ip: "10.3.0.5", govde: litofanGovde({ onay_surum: surum, aydinlatma_onay: false }) });
    // GIRDI TURLERI (manifest): litofanin `form`u {} ve girdisinde svg yok -> sema disi 400.
    const semaDisi = await istek("/foto/litofan", { ip: "10.3.0.6", govde: litofanGovde({ onay_surum: surum, parametreler: { delik_mm: 5 } }) });
    iddia("L3", "sema disi parametre 400 (sema-disi-parametre)", semaDisi.kod === 400 && !!semaDisi.v &&
          semaDisi.v.hata === "sema-disi-parametre", JSON.stringify(semaDisi.v));
    const svgli = await istek("/foto/litofan", { ip: "10.3.0.7", govde: litofanGovde({ onay_surum: surum, svg: "<svg><path d=\"M0 0\"/></svg>" }) });
    iddia("L3", "girdisinde svg olmayan ture svg alani 400", svgli.kod === 400 && !!svgli.v &&
          svgli.v.hata === "sema-disi-parametre", JSON.stringify(svgli.v));
    const eskiSurum = await istek("/foto/litofan", { ip: "10.3.0.6", govde: litofanGovde({ onay_surum: "eski" }) });
    iddia("L3", "aydinlatma onayi yok 400 onay-yok · eski onay surumu 400 onay-surumu-eski", onaysiz.kod === 400 &&
          onaysiz.v.hata === "onay-yok" && eskiSurum.kod === 400 && eskiSurum.v.hata === "onay-surumu-eski",
          onaysiz.kod + "/" + eskiSurum.kod);
    const olcuYok = await istek("/foto/litofan", { ip: "10.3.0.7", govde: litofanGovde({ onay_surum: surum, olcu_mm: 125 }) });
    iddia("L3", "formulde olmayan olcu (adim disi 125) 400 gecersiz-olcu", olcuYok.kod === 400 && olcuYok.v.hata === "gecersiz-olcu", JSON.stringify(olcuYok.v));
    const sgOnce2 = P.saglayici;
    const yanlisUc = await istek("/foto/onizleme", { ip: "10.3.0.8", govde: { tur: "litofan", olcu_mm: 120, gorsel: uri(HARITA),
      aydinlatma_onay: true, onay_surum: surum, turnstile_token: "j" } });
    iddia("L3", "/foto/onizleme litofani saglayiciya GOTURMEZ (400 tur-kapali, cagri 0)",
          yanlisUc.kod === 400 && yanlisUc.v.hata === "tur-kapali" && P.saglayici === sgOnce2, JSON.stringify(yanlisUc.v));

    // ---- L4: /baslat
    const sepet = (secim, adet) => ({ sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: isNo, olcu_mm: 120, adet: adet || 1, ...(secim ? { secim } : {}) }] });
    const iyOnce4 = P.iyzico;
    const b4 = await istek("/baslat", { govde: sepet({ panel_malzeme: "PETG", ayak_malzeme: "ASA", ayak_renk: "Siyah" }, 2) });
    const siparisNo = b4.v && b4.v.no;
    const s4 = siparisNo ? await d1.prepare("SELECT durum, urunler, tutar_kurus FROM siparisler WHERE siparis_no = ?").bind(siparisNo).first() : null;
    const k4 = s4 && JSON.parse(s4.urunler)[0];
    iddia("L4", "/baslat 200, tutar = formul x adet (120 mm x 1000 = 120000 x 2), istemci tutari okunmaz",
          b4.kod === 200 && P.iyzico === iyOnce4 + 1 && !!s4 && s4.tutar_kurus === 240000 && k4.birim_kurus === 120000 &&
          k4.tutar_kurus === 240000, JSON.stringify(b4.v) + " " + (s4 && s4.tutar_kurus));
    iddia("L4", "satir secimi tasir (panel PETG, ayak ASA Siyah) + foto_kol deterministik",
          !!k4 && k4.foto_kol === "deterministik" && k4.foto_tur === "litofan" && k4.foto_secim &&
          k4.foto_secim.panel_malzeme === "PETG" && k4.foto_secim.ayak_malzeme === "ASA" &&
          k4.foto_secim.ayak_renk === "Siyah" && k4.foto_secim.panel_renk === "Beyaz" && /Siyah/.test(k4.renk), JSON.stringify(k4));
    const mor = await istek("/baslat", { govde: sepet({ panel_malzeme: "PLA", ayak_malzeme: "PLA", ayak_renk: "Mor" }) });
    iddia("L4", "listede olmayan renk 400 gecersiz-secim", mor.kod === 400 && mor.v.hata === "gecersiz-secim", JSON.stringify(mor.v));
    const abs = await istek("/baslat", { govde: sepet({ panel_malzeme: "PLA", ayak_malzeme: "ABS", ayak_renk: "Beyaz" }) });
    iddia("L4", "ABS ayak 400 gecersiz-secim", abs.kod === 400 && abs.v.hata === "gecersiz-secim", JSON.stringify(abs.v));
    const secimsiz = await istek("/baslat", { govde: sepet(null) });
    iddia("L4", "secimsiz litofan kalemi 400", secimsiz.kod === 400 && secimsiz.v.hata === "gecersiz-secim", JSON.stringify(secimsiz.v));

    // ---- L5: odeme -> kuyruk 'uretec-bekliyor', cron saglayiciya GITMEZ
    if (siparisNo) { await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(siparisNo).run(); }
    const sg5 = P.saglayici;
    for (let i = 0; i < 3; i++) { await foto.fotoUretimTuru(env, Date.now() + i * 1000, null); }
    const u5 = siparisNo ? await d1.prepare("SELECT asama, deneme FROM foto_uretim WHERE siparis_no = ? AND kalem = 0").bind(siparisNo).first() : null;
    iddia("L5", "3 cron turu sonra satir 'uretec-bekliyor'", !!u5 && u5.asama === "uretec-bekliyor", JSON.stringify(u5));
    iddia("L5", "cron saglayici cagri sayaci 0", P.saglayici === sg5, String(P.saglayici - sg5));
    // Saglayici anahtari yokken: litofan yine kuyruga girer, ozet bugunkuyle ayni.
    const is5 = "b".repeat(32);
    await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih) VALUES (?, 'litofan', 120, 'z', ?, 'hazir', ?)")
      .bind(is5, simdi, simdi).run();
    await d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES ('PR-LIT-ANAHTARSIZ', ?, 'odendi', 1, ?)")
      .bind(simdi, JSON.stringify([{ id: "ozel-foto-litofan", foto_is: is5, foto_tur: "litofan", olcu_mm: 120 }])).run();
    const oz = await foto.fotoUretimTuru(envKur(d1, r2, { URETIM_API_ANAHTAR: "" }), Date.now(), null);
    const u5b = await d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = 'PR-LIT-ANAHTARSIZ'").first();
    iddia("L5", "saglayici anahtari yokken litofan kuyrukta 'uretec-bekliyor' + ozet atlandi/kuyruga 0",
          !!u5b && u5b.asama === "uretec-bekliyor" && oz.atlandi === "yapilandirma" && oz.kuyruga === 0,
          JSON.stringify(u5b) + " " + JSON.stringify(oz));

    // ---- L6: panel uretec uclari
    const q = "?siparis=" + encodeURIComponent(siparisNo || "yok") + "&kalem=0";
    const anahtar3mf = "foto/" + siparisNo + "/0/model.3mf";
    const yetkisiz = await istek("/yonet/foto/uretec-yukle" + q, { yontem: "POST", ham: UCMF });
    const u6a = await d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = ? AND kalem = 0").bind(siparisNo || "").first();
    iddia("L6", "yetkisiz yukleme reddedilir (401/403/404), R2 + asama degismez",
          [401, 403, 404].includes(yetkisiz.kod) && !r2.m.has(anahtar3mf) && !!u6a && u6a.asama === "uretec-bekliyor", String(yetkisiz.kod));
    const bozuk = await istek("/yonet/foto/uretec-yukle" + q, { yontem: "POST", basliklar: YONET,
      ham: new TextEncoder().encode("bu-bir-3mf-degil-zip-imzasi-yok") });
    iddia("L6", "bozuk imza 400", bozuk.kod === 400 && !r2.m.has(anahtar3mf), JSON.stringify(bozuk.v));
    const girdi = await istek("/yonet/foto/uretec-girdi" + q, { basliklar: YONET });
    iddia("L6", "girdi indir = musteri haritasi (PNG)", girdi.kod === 200 && /image\/png/.test(girdi.tip) &&
          !!girdi.bayt && Buffer.from(girdi.bayt).equals(Buffer.from(HARITA)), String(girdi.kod));
    // SOZLESME §2/§4: girdi.json + olcu.json/onizleme.png ayni cagri ailesiyle.
    const gj = await istek("/yonet/foto/uretec-girdi" + q + "&dosya=girdi.json", { basliklar: YONET });
    iddia("L6", "girdi.json: sozlesme 1, kategori litofan, olcu_mm, renk/malzeme bolgeleri, dosyalar.gri_harita",
          gj.kod === 200 && !!gj.v && gj.v.sozlesme === 1 && gj.v.kategori === "litofan" && Number.isInteger(gj.v.olcu_mm) &&
          gj.v.renkler && gj.v.malzemeler && gj.v.dosyalar && gj.v.dosyalar.gri_harita === "gri_harita.png", JSON.stringify(gj.v));
    const kucukOn = await istek("/yonet/foto/uretec-yukle" + q + "&dosya=onizleme.png", { yontem: "POST", basliklar: YONET, ham: HARITA });
    iddia("L6", "onizleme.png < 1024 px -> 400", kucukOn.kod === 400, JSON.stringify(kucukOn.v));
    const onz = await istek("/yonet/foto/uretec-yukle" + q + "&dosya=onizleme.png", { yontem: "POST", basliklar: YONET, ham: pngYap(1200, 800) });
    const olcuGovde = { sozlesme: 1, kategori: "litofan", uzun_kenar_mm: (gj.v && gj.v.olcu_mm) || 0,
                        kutu_mm: { x: (gj.v && gj.v.olcu_mm) || 0, y: 80, z: 3 }, renk_sayisi: 2, sizdirmaz: true };
    const olc = await istek("/yonet/foto/uretec-yukle" + q + "&dosya=olcu.json", { yontem: "POST", basliklar: YONET,
      ham: new TextEncoder().encode(JSON.stringify(olcuGovde)) });
    const u6b = await d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = ? AND kalem = 0").bind(siparisNo || "").first();
    iddia("L6", "onizleme.png + olcu.json 200, asama DEGISMEZ (uretec-bekliyor)", onz.kod === 200 && olc.kod === 200 &&
          !!u6b && u6b.asama === "uretec-bekliyor", onz.kod + "/" + olc.kod + " " + JSON.stringify(u6b));
    const iyi = await istek("/yonet/foto/uretec-yukle" + q, { yontem: "POST", basliklar: YONET, ham: UCMF });
    const u6 = await d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = ? AND kalem = 0").bind(siparisNo || "").first();
    iddia("L6", "gecerli 3MF -> 200, satir 'hazir', R2'de 3MF", iyi.kod === 200 && !!u6 && u6.asama === "hazir" &&
          r2.m.has(anahtar3mf) && Buffer.from(r2.m.get(anahtar3mf).bayt).equals(Buffer.from(UCMF)), JSON.stringify(iyi.v));
    const ikinci = await istek("/yonet/foto/uretec-yukle" + q, { yontem: "POST", basliklar: YONET, ham: UCMF });
    iddia("L6", "ikinci yukleme 409", ikinci.kod === 409, String(ikinci.kod));
    const dq = "?siparis_no=" + encodeURIComponent(siparisNo || "yok") + "&kalem=0&bicim=";
    const d3 = await istek("/yonet/foto-dosya" + dq + "3mf", { basliklar: YONET });
    const dg = await istek("/yonet/foto-dosya" + dq + "glb", { basliklar: YONET });
    iddia("L6", "panel dosya: 3MF 200, GLB 404 (deterministik kolda GLB yok)", d3.kod === 200 && dg.kod === 404, d3.kod + "/" + dg.kod);
    const pk = foto.panelFotoKaydi(siparisNo, 0, k4 || {}, new Map([[siparisNo + "|0", { asama: "hazir" }]]));
    iddia("L6", "panel kaydi: kol deterministik + secim + yalniz 3MF baglantisi", pk.kol === "deterministik" &&
          !!pk.secim && pk.secim.ayak_renk === "Siyah" && !!pk.dosyalar && !!pk.dosyalar["3mf"] && !pk.dosyalar.glb && !!pk.uretec,
          JSON.stringify(pk));

    // ---- L7: plaket regresyonu (ayni sahte ortam)
    VERI.ornekler.push(ornek("plaket"));
    await d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
    const p7 = await istek("/foto/onizleme", { ip: "10.7.0.1", govde: { tur: "plaket", olcu_mm: 100, gorsel: uri(HARITA),
      aydinlatma_onay: true, onay_surum: surum, turnstile_token: "j" } });
    const pis = p7.v && p7.v.is;
    const dur = pis ? await istek("/foto/durum?is=" + pis) : { v: null };
    iddia("L7", "plaket onizleme saglayici kolundan 'hazir'", p7.kod === 200 && !!dur.v && dur.v.asama === "hazir",
          JSON.stringify(p7.v) + " " + JSON.stringify(dur.v));
    const b7 = await istek("/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: pis, olcu_mm: 100, adet: 1, secim: { ayak_renk: "Mor" } }] } });
    const s7 = b7.v && b7.v.no ? await d1.prepare("SELECT urunler, tutar_kurus FROM siparisler WHERE siparis_no = ?").bind(b7.v.no).first() : null;
    const k7 = s7 && JSON.parse(s7.urunler)[0];
    iddia("L7", "plaket satiri bugunku gibi (PLA, 4 renk, ayak 1, secim YOK SAYILIR)", b7.kod === 200 && !!k7 &&
          s7.tutar_kurus === 100000 && k7.malzeme === "PLA" && k7.renk === "4 renk" && k7.foto_ayak === 1 &&
          k7.foto_secim === undefined && k7.foto_kol === undefined, JSON.stringify(k7));
    if (b7.v && b7.v.no) { await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(b7.v.no).run(); }
    await foto.fotoUretimTuru(env, Date.now(), null);
    const u7 = b7.v && b7.v.no ? await d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = ?").bind(b7.v.no).first() : null;
    iddia("L7", "odenen plaket kuyrukta 'build-baslat'", !!u7 && u7.asama === "build-baslat", JSON.stringify(u7));

    // ---- L8: saglayici env'siz ortamda saklama kurali (72 sa) yine koşar
    const eski = new Date(Date.now() - 73 * 3600 * 1000).toISOString();
    const is8 = "c".repeat(32); const is8s = "d".repeat(32);
    for (const n of [is8, is8s]) {
      await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih) VALUES (?, 'litofan', 120, 'z', ?, 'hazir', ?)")
        .bind(n, eski, eski).run();
      await r2.put("foto-onizleme/" + n + ".png", HARITA, { httpMetadata: { contentType: "image/png" } });
    }
    await d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-LIT-SAKLAMA', 0, ?, 'litofan', 120, 'uretec-bekliyor', ?, ?)")
      .bind(is8s, eski, eski).run();
    const sg8 = P.saglayici;
    const oz8 = await foto.fotoUretimTuru(envKur(d1, r2, { URETIM_API_ANAHTAR: "", URETIM_API_TABAN: "" }), Date.now(), null);
    const f8 = await d1.prepare("SELECT asama FROM foto_isler WHERE is_no = ?").bind(is8).first();
    iddia("L8", "siparise girmemis 73 sa'lik litofan haritasi: R2'de nesne 0 + satir 'silindi'",
          !r2.m.has("foto-onizleme/" + is8 + ".png") && !!f8 && f8.asama === "silindi", JSON.stringify(f8));
    iddia("L8", "ozet atlandi 'yapilandirma' + silinen >= 1, saglayici fetch 0",
          oz8.atlandi === "yapilandirma" && oz8.silinen >= 1 && P.saglayici === sg8, JSON.stringify(oz8) + " fetch=" + (P.saglayici - sg8));
    const f8s = await d1.prepare("SELECT asama FROM foto_isler WHERE is_no = ?").bind(is8s).first();
    iddia("L8", "siparise girmis (foto_uretim'de) litofan haritasi SILINMEZ",
          r2.m.has("foto-onizleme/" + is8s + ".png") && !!f8s && f8s.asama === "hazir", JSON.stringify(f8s));
  } catch (e) {
    iddia("L2", "senaryo hatasiz kostu", false, (e && e.stack) || String(e));
  } finally {
    VERI.ornekler.splice(0, VERI.ornekler.length, ...yedekOrnek);
    k.kapat();
  }
  return g;
}

const grupYesil = (g, ad) => g[ad].every((x) => x.ok);

// ================================================================ ANA KOSUM

const GECICILER = [];
const temizle = () => { for (const d of GECICILER) { fs.rmSync(d, { recursive: true, force: true }); } };
process.on("exit", temizle);

let canli;
try { canli = await modulKur(KOK); } catch (e) {
  console.log("OLCULEMEDI: worker modulu yuklenemedi — " + ((e && e.stack) || e));
  process.exit(3);
}
{
  const k = koprukur(); const ilk = await k.hazir; k.kapat();
  if (!ilk || !ilk.hazir) { console.log("OLCULEMEDI: SQLite koprusu kurulamadi — " + JSON.stringify(ilk)); process.exit(3); }
}

console.log("L1) KATEGORI KAYDI");
{
  const { foto, VERI, SECENEK } = canli;
  const KOLLAR = ["saglayici", "deterministik"];
  const filament = (SECENEK && SECENEK.FILAMENT_SIRA) || [];
  const kayitDenetle = (turler) => {
  const hatali = [];
  for (const t of turler) {
    const a = t.olcu_mm || {};
    // Sozlesme §6 alanlari TAM: girdi[] · motor · uretec (D/R dolu, M bos) · form · fiyat · ornek_kanit_izni.
    if (!Array.isArray(t.girdi) || !t.girdi.length ||
        t.girdi.some((x) => !Object.prototype.hasOwnProperty.call(VERI.GIRDI_TURLERI, x))) { hatali.push(t.kod + ":girdi"); }
    if (!["M", "D", "R"].includes(t.motor) || !KOLLAR.includes(VERI.kolu(t.kod))) { hatali.push(t.kod + ":kol"); }
    if (typeof t.uretec !== "string" || (t.motor === "M" ? t.uretec !== "" : !t.uretec)) { hatali.push(t.kod + ":uretec"); }
    if (!t.form || typeof t.form !== "object" || Array.isArray(t.form)) { hatali.push(t.kod + ":form"); }
    if (!t.fiyat || t.fiyat.formul !== "mm_x_10tl" || !(Number.isInteger(t.fiyat.adim_mm) && t.fiyat.adim_mm > 0)) { hatali.push(t.kod + ":fiyat"); }
    if (!Array.isArray(t.ornek_kanit_izni) || !t.kod || !t.ad || !t.aciklama) { hatali.push(t.kod + ":kimlik"); }
    // Render orneginin durustluk cumlesi tur kaydinda ZORUNLU (mimar karari 7 Eki; bos -> KIRMIZI).
    if (typeof t.ornek_notu !== "string" || !t.ornek_notu.trim()) { hatali.push(t.kod + ":ornek_notu"); }
    // Ust durustluk kutusu metni tur kaydinda ZORUNLU (7 Eki, G1 madde 12; bos -> KIRMIZI).
    if (typeof t.durustluk !== "string" || !t.durustluk.trim()) { hatali.push(t.kod + ":durustluk"); }
    if (!(Number.isInteger(a.en_az) && Number.isInteger(a.en_cok) && a.en_az > 0 && a.en_cok >= a.en_az)) { hatali.push(t.kod + ":olcu"); }
    if (!Array.isArray(t.renk_bolgeleri) || t.renk_bolgeleri.some((b) => !b || !b.kod || !b.ad ||
        !Array.isArray(b.renkler) || !b.renkler.length)) { hatali.push(t.kod + ":renk"); }
    const m = t.malzemeler;
    if (!m || typeof m !== "object" || Array.isArray(m) ||
        Object.values(m).some((l) => !Array.isArray(l) || !l.length || l.some((x) => !filament.includes(x)))) {
      hatali.push(t.kod + ":malzeme");
    }
  }
  return hatali;
  };
  const hatali = kayitDenetle(VERI.turler);
  ol("L1a her tur: §6 alanlari tam (girdi[]/motor/uretec/form/fiyat) + olcu_mm/renk_bolgeleri/malzemeler gecerli (malzeme ⊆ FILAMENT_SIRA)",
     filament.length > 0 && hatali.length === 0, hatali.join(","));
  const yeni = (not) => { const t = JSON.parse(JSON.stringify(VERI.turBul("litofan"))); t.kod = "yeni"; if (not === undefined) { delete t.ornek_notu; } else { t.ornek_notu = not; } return t; };
  // ":kol" satiri sentetik turun manifestte olmamasindan (VERI.kolu kod ile manifestten okur) -> sayilmaz.
  const den = (t) => kayitDenetle([t]).filter((x) => x !== "yeni:kol");
  const h1 = den(yeni("")), h2 = den(yeni(undefined)), h3 = den(yeni("x"));
  ol("L1a2 yeni tur ornek_notu bos/yok -> KIRMIZI (yeni:ornek_notu); dolu -> temiz (pozitif kontrol)",
     JSON.stringify(h1) === '["yeni:ornek_notu"]' && JSON.stringify(h2) === '["yeni:ornek_notu"]' && h3.length === 0,
     JSON.stringify([h1, h2, h3]));
  const yeniD = (d) => { const t = JSON.parse(JSON.stringify(VERI.turBul("litofan"))); t.kod = "yeni"; if (d === undefined) { delete t.durustluk; } else { t.durustluk = d; } return t; };
  const d1 = den(yeniD("")), d2 = den(yeniD(undefined)), d3 = den(yeniD("x"));
  ol("L1a3 yeni tur durustluk bos/yok -> KIRMIZI (yeni:durustluk); dolu -> temiz",
     JSON.stringify(d1) === '["yeni:durustluk"]' && JSON.stringify(d2) === '["yeni:durustluk"]' && d3.length === 0,
     JSON.stringify([d1, d2, d3]));
  ol("L1a4 durustluk metinleri AYNEN (plaket = onceki sabit metin; litofan = mimar metni)",
     VERI.turBul("plaket").durustluk === "Önizleme, fotoğrafının stilize bir yorumudur. Ürün en çok 4 renkle kabartma olarak üretilir — önizlemenin 4 renkli yorumu; birebir aynısı değildir, küçük yazı ve ince ayrıntılar sadeleşir." && VERI.turBul("litofan").durustluk === "Litofan tek renkli ince bir paneldir; görüntü arkadan ışık geldiğinde belirir. İnce ayrıntılar ve küçük yazılar sadeleşir.",
     JSON.stringify([VERI.turBul("plaket").durustluk, VERI.turBul("litofan").durustluk]));
  const sag = VERI.turler.filter((t) => VERI.kolu(t.kod) === "saglayici").map((t) => t.kod).sort();
  ol("L1b saglayici turleri = TUR_ORTAM anahtarlari", JSON.stringify(sag) === JSON.stringify(Object.keys(foto.TUR_ORTAM).sort()),
     JSON.stringify(sag));
  const det = VERI.turler.filter((t) => VERI.kolu(t.kod) === "deterministik").map((t) => t.kod);
  ol("L1c deterministik ∩ TUR_ORTAM = ∅ ve sunucu kumesi kayittan turetilir",
     det.every((d) => !Object.prototype.hasOwnProperty.call(foto.TUR_ORTAM, d)) &&
       JSON.stringify(foto.DETERMINISTIK_TURLER) === JSON.stringify(det), JSON.stringify(foto.DETERMINISTIK_TURLER));
  const lit = VERI.turBul("litofan");
  ol("L1d litofan: motor D (deterministik), uretec litofan_uret, 80–200 mm, ABS 0 (Dekorasyon sinifi)", !!lit &&
     VERI.kolu("litofan") === "deterministik" && lit.motor === "D" && lit.uretec === "litofan_uret" &&
     lit.olcu_mm.en_az === 80 && lit.olcu_mm.en_cok === 200 &&
     !Object.values(lit.malzemeler).some((l) => l.includes("ABS")), JSON.stringify(lit && lit.malzemeler));
  const pl = VERI.olcuAraligi("plaket");
  ol("L1e plaket kaydi bugunku davranisi birebir tarif eder (60–300 mm, renk secimi yok, malzeme {})",
     !!pl && pl.en_az === foto.OLCU_MM_EN_AZ && pl.en_cok === foto.OLCU_MM_EN_COK &&
       VERI.turBul("plaket").renk_bolgeleri.length === 0 && Object.keys(VERI.turBul("plaket").malzemeler).length === 0 &&
       VERI.kolu("plaket") === "saglayici" && VERI.kolu("yok") === "" && VERI.olcuAraligi("yok") === null, JSON.stringify(pl));
}

// ---------------------------------------------------------------- L10: URETEC ONIZLEME KUYRUGU (uctan uca)
// Sentetik `isimlik` satiri (form girdili, tarayici onizleyicisi YOK) KOPYA kokun veri dosyasina
// eklenir (calisma agacina yazim YOK). Sunucu ucu -> gercek koşucu (sahte wrangler + sahte uretec;
// D1 = kopru ile AYNI gecici SQLite dosyasi, R2 = gecici dizin) -> siparis -> KOPYA KOLU.

const ISIMLIK = '      { kod: "isimlik", ad: "İsimlik", aciklama: "x", girdi: ["form"], motor: "D", uretec: "isimlik_uret",\n' +
  '        olcu_mm: { en_az: 80, en_cok: 200 }, renk_bolgeleri: [], malzemeler: {},\n' +
  '        form: { yazi: { tip: "metin", max: 20, etiket: "Yazı" } }, fiyat: { formul: "mm_x_10tl", adim_mm: 10 },\n' +
  '        ornek_kanit_izni: ["render"], durustluk: "t", ornek_notu: "t" },\n';

// L11: TURETILMIS eksenli sentetik tur (surgu yok; olcu onizlemede OLCULUR). Sahte uretec uzun kenari `uk`
// parametresinden yazar (gercek uretecte geometriden dogar).
const TURETIK = '      { kod: "turetik", ad: "Türetik", aciklama: "x", girdi: ["form"], motor: "D", uretec: "isimlik_uret",\n' +
  '        olcu_mm: { en_az: 80, en_cok: 200 }, renk_bolgeleri: [], malzemeler: {}, olcu_ekseni: "turetilmis",\n' +
  '        form: { uk: { tip: "sayi", min: 1, max: 999, adim: 0.01, etiket: "Uk" } }, fiyat: { formul: "mm_x_10tl", adim_mm: 10 },\n' +
  '        ornek_kanit_izni: ["render"], durustluk: "t", ornek_notu: "t" },\n';

const SAHTE_WR = `import json, os, shutil, sqlite3, sys
a = sys.argv[1:]
if a[:2] == ["d1", "execute"]:
    sql = a[a.index("--command") + 1]
    c = sqlite3.connect(os.environ["FAKE_DB"]); c.row_factory = sqlite3.Row
    cur = c.execute(sql); rows = [dict(r) for r in cur.fetchall()]; c.commit()
    print(json.dumps([{"results": rows, "success": True, "meta": {"changes": cur.rowcount if sql.startswith("UPDATE") else 0}}]))
    sys.exit(0)
if a[:2] == ["r2", "object"]:
    anahtar = a[3].split("/", 1)[1]; dosya = a[a.index("--file") + 1]
    yol = os.path.join(os.environ["FAKE_R2"], anahtar)
    if a[2] == "get":
        if not os.path.isfile(yol):
            sys.stderr.write("The specified key does not exist."); sys.exit(1)
        shutil.copyfile(yol, dosya); sys.exit(0)
    os.makedirs(os.path.dirname(yol), exist_ok=True); shutil.copyfile(dosya, yol); sys.exit(0)
sys.exit(9)
`;

const SAHTE_URETEC_I = `import json, os, struct, sys
a = sys.argv[1:]; g = json.load(open(a[a.index("--girdi") + 1])); c = a[a.index("--cikti") + 1]
open(os.environ["FAKE_URETEC_SAYAC"], "a").write("1" + chr(10))
os.makedirs(c)
open(os.path.join(c, "model.3mf"), "wb").write(b"PK" + bytes([3, 4]) + json.dumps(g["parametreler"], sort_keys=True).encode())
ihdr = struct.pack(">II", 1024, 512) + bytes([8, 2, 0, 0, 0])
open(os.path.join(c, "onizleme.png"), "wb").write(bytes([0x89]) + b"PNG" + bytes([13, 10, 26, 10]) + struct.pack(">I", 13) + b"IHDR" + ihdr + bytes(4))
m = g["parametreler"].get("uk") or g["olcu_mm"]
json.dump({"sozlesme": 1, "kategori": g["kategori"], "uzun_kenar_mm": float(m), "kutu_mm": {"x": float(m), "y": 30.0, "z": 5.0},
           "renk_sayisi": 1, "sizdirmaz": True, "parcalar": [{"ad": "govde", "renk": "Beyaz"}], "girdi_sha256": "", "model_sha256": ""},
          open(os.path.join(c, "olcu.json"), "w"))
`;

/** Dizin destekli sahte R2 (koşucunun sahte wrangler'i AYNI dizini okur/yazar). */
function r2DizinKur(dizin) {
  const yol = (k) => path.join(dizin, k);
  return {
    async put(k, v) {
      fs.mkdirSync(path.dirname(yol(k)), { recursive: true });
      fs.writeFileSync(yol(k), typeof v === "string" ? v : Buffer.from(v));
    },
    async get(k) { return fs.existsSync(yol(k)) ? { body: new Uint8Array(fs.readFileSync(yol(k))), httpMetadata: {} } : null; },
    async delete(k) { fs.rmSync(yol(k), { force: true }); },
    async list() { return { objects: [] }; },
  };
}

/** Kopya kok: (varsa mutant) + sentetik isimlik satiri + koşucunun kopyasi (manifesti kopyadan okur). */
function isimlikKokKur(mu) {
  const kok = kopyaKur();
  if (mu) {
    const asil = fs.readFileSync(path.join(KOK, mu.dosya), "utf8");
    fs.writeFileSync(path.join(kok, mu.dosya), asil.replace(mu.capa, mu.yerine));
  }
  const vy = path.join(kok, "foto-uretim-veri.js");
  const v = fs.readFileSync(vy, "utf8");
  if (v.split("    turler: [\n").length !== 2) { throw new Error("isimlik capasi bulunamadi"); }
  fs.writeFileSync(vy, v.replace("    turler: [\n", "    turler: [\n" + ISIMLIK + TURETIK));
  fs.mkdirSync(path.join(kok, "tools"));
  fs.copyFileSync(path.join(KOK, "tools", "foto-uretec-kosucu.py"), path.join(kok, "tools", "foto-uretec-kosucu.py"));
  return kok;
}

async function senaryoIsimlik(kok) {
  const g = { L10: [], ozet: [] };
  const iddia = (ad, ok, ek) => g.L10.push({ ad, ok: !!ok, ek: ek || "" });
  const { modul, foto, VERI } = await modulKur(kok);
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-foto-isimlik-"));
  GECICILER.push(d);
  const db = path.join(d, "d1.sqlite"), r2d = path.join(d, "r2"), sayac = path.join(d, "uretec.sayac");
  fs.mkdirSync(r2d);
  fs.writeFileSync(path.join(d, "wr.py"), SAHTE_WR);
  fs.writeFileSync(path.join(d, "uretec.py"), SAHTE_URETEC_I);
  fs.writeFileSync(sayac, "");
  fs.writeFileSync(path.join(d, "tablo.json"), JSON.stringify({ isimlik_uret: { bicim: "sozlesme", komut: ["python3", path.join(d, "uretec.py")] } }));
  const uretecSayisi = () => fs.readFileSync(sayac, "utf8").split("\n").filter(Boolean).length;
  const kosucu = () => {
    const p = spawnSync("python3", [path.join(kok, "tools", "foto-uretec-kosucu.py"), "--uygula"], {
      encoding: "utf8", timeout: 120000,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", FAKE_DB: db, FAKE_R2: r2d, FAKE_URETEC_SAYAC: sayac,
             FOTO_KOSUCU_WRANGLER: "python3 " + path.join(d, "wr.py"), FOTO_KOSUCU_KILIT: path.join(d, "kilit"),
             FOTO_KOSUCU_PYTHON: "python3", FOTO_KOSUCU_URETEC_TABLO: path.join(d, "tablo.json") } });
    const cikti = (p.stdout || "") + (p.stderr || "");
    return { son: (p.stdout || "").trim().split("\n").pop(), cikti };
  };
  const k = koprukur(db); await k.hazir;
  const d1 = k.d1; const r2 = r2DizinKur(r2d);
  const env = envKur(d1, r2);
  const istek = istekKur(modul, env);
  const siparis = (isNo) => ({ sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
                               sepet: [{ foto_is: isNo, olcu_mm: 100, adet: 1 }] });
  const yedek = VERI.ornekler.splice(0);
  try {
    VERI.ornekler.push({ tur: "isimlik", kanit: "render", olcu_mm: 100, onizleme: "https://media.pruvo3d.com/t-io.webp",
                         render: "https://media.pruvo3d.com/t-ir.webp", not: "t" });
    await d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('isimlik', 1, '2026-10-07T00:00:00.000Z')").run();
    const sg = P.saglayici;
    const o = await istek("/foto/onizleme", { ip: "198.51.100.210", govde: { tur: "isimlik", olcu_mm: 100,
      parametreler: { yazi: "Ada" }, aydinlatma_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton" } });
    const isNo = (o.v && o.v.is) || "yok";
    const satir = () => d1.prepare("SELECT asama, hazir_tarih, hata FROM foto_isler WHERE is_no = ?").bind(isNo).first();
    const dz = path.join(r2d, "foto-uretec-onizleme", isNo);
    const s1 = await satir();
    const gj = fs.existsSync(path.join(dz, "girdi.json")) ? JSON.parse(fs.readFileSync(path.join(dz, "girdi.json"), "utf8")) : null;
    iddia("onizleme ucu 200 -> satir 'uretec-onizleme' + R2 girdi.json (§2: siparis_no '', kalem 0, olcu 100, parametreler) · saglayici 0 · yoklama 5/180 sn",
      o.kod === 200 && !!s1 && s1.asama === "uretec-onizleme" && !!gj && gj.sozlesme === 1 && gj.kategori === "isimlik" &&
        gj.siparis_no === "" && gj.kalem === 0 && gj.olcu_mm === 100 && JSON.stringify(gj.parametreler) === JSON.stringify({ yazi: "Ada" }) &&
        P.saglayici === sg && !!o.v.yoklama && o.v.yoklama.aralik_sn === 5 && o.v.yoklama.tavan_sn === 180,
      JSON.stringify([o.kod, o.v, s1, gj]));
    const sema = await istek("/foto/onizleme", { ip: "198.51.100.211", govde: { tur: "isimlik", olcu_mm: 100,
      parametreler: { yazi: "Ada", fazla: 1 }, aydinlatma_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton" } });
    iddia("sema disi parametre -> 400 (VERI.parametreDogrula), satir/R2 yazimi yok", sema.kod === 400 && sema.v && sema.v.hata === "sema-disi-parametre",
      JSON.stringify([sema.kod, sema.v]));
    // AYDINLATMA ONAYI (tek kutu, taslak-2): uretec onizleme ucu da kutusuz / eski surumle 400; dogru istekte damga+surum satirda.
    const uGovde = (ek) => ({ tur: "isimlik", olcu_mm: 100, parametreler: { yazi: "Ada" }, turnstile_token: "jeton", ...ek });
    const uKutusuz = await istek("/foto/onizleme", { ip: "198.51.100.212", govde: uGovde({ onay_surum: VERI.onay_surum }) });
    const uEskiAlan = await istek("/foto/onizleme", { ip: "198.51.100.213", govde: uGovde({ hak_onay: true, onay_surum: VERI.onay_surum }) });
    const uEski = await istek("/foto/onizleme", { ip: "198.51.100.214", govde: uGovde({ aydinlatma_onay: true, onay_surum: "2026-10-05-taslak-1" }) });
    const uKayit = await d1.prepare("SELECT onay_tarih, onay_surum FROM foto_isler WHERE is_no = ?").bind(isNo).first();
    iddia("uretec onizleme: kutusuz / eski alanla 400 onay-yok · eski surum 400 onay-surumu-eski · dogru istekte onay_tarih+onay_surum satirda",
      uKutusuz.kod === 400 && uKutusuz.v.hata === "onay-yok" && uEskiAlan.kod === 400 && uEskiAlan.v.hata === "onay-yok" &&
        uEski.kod === 400 && uEski.v.hata === "onay-surumu-eski" && !!uKayit && uKayit.onay_surum === VERI.onay_surum &&
        !Number.isNaN(Date.parse(uKayit.onay_tarih)),
      JSON.stringify([uKutusuz.kod, uKutusuz.v, uEskiAlan.kod, uEski.kod, uEski.v, uKayit]));
    const d0 = await istek("/foto/durum?is=" + isNo);
    const b0 = await istek("/baslat", { govde: siparis(isNo) });
    iddia("kuyrukta: durum 'bekliyor' · siparis 400 foto-onizleme-yok (kuyruk atlanamaz)",
      !!d0.v && d0.v.asama === "bekliyor" && b0.kod === 400 && !!b0.v && b0.v.hata === "foto-onizleme-yok", JSON.stringify([d0.v, b0.kod, b0.v]));
    const k1 = kosucu();
    const s2 = await satir();
    g.ozet.push("onizleme koşucu: " + k1.son + " · asama=" + (s2 && s2.asama) + " · uretec=" + uretecSayisi());
    iddia("koşucu (sahte uretec) -> 'onizleme-hazir', uretec 1 kez", k1.son === "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" &&
      !!s2 && s2.asama === "onizleme-hazir" && uretecSayisi() === 1, k1.cikti.slice(-500));
    const dy = await istek("/foto/durum?is=" + isNo);
    const gy = await istek("/foto/gorsel?is=" + isNo);
    const png = fs.existsSync(path.join(dz, "onizleme.png")) ? fs.readFileSync(path.join(dz, "onizleme.png")) : Buffer.alloc(0);
    iddia("durum 'hazir' + olcu.json ozeti (uzun kenar 100) · gorsel ucu koşucunun onizleme.png'si",
      !!dy.v && dy.v.asama === "hazir" && !!dy.v.olcu && dy.v.olcu.uzun_kenar_mm === 100 && dy.v.gorsel === "/api/shop/foto/gorsel?is=" + isNo &&
        gy.kod === 200 && !!gy.bayt && png.length > 0 && Buffer.compare(Buffer.from(gy.bayt), png) === 0, JSON.stringify([dy.v, gy.kod]));
    const b1 = await istek("/baslat", { govde: siparis(isNo) });
    const no = b1.v && b1.v.no;
    if (no) { await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(no).run(); }
    await foto.fotoUretimTuru(env, Date.now(), null);
    const urt = () => d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = ?").bind(no || "-").first();
    const u1 = await urt();
    iddia("siparis 200 (onizleme-hazir ise baglanir) -> odeninca foto_uretim 'uretec-bekliyor'",
      b1.kod === 200 && !!u1 && u1.asama === "uretec-bekliyor", JSON.stringify([b1.kod, b1.v, u1]));
    const k2 = kosucu();
    const u2 = await urt();
    const m1 = path.join(r2d, "foto", String(no), "0", "model.3mf"), m0 = path.join(dz, "model.3mf");
    const ayni = fs.existsSync(m1) && fs.existsSync(m0) && Buffer.compare(fs.readFileSync(m1), fs.readFileSync(m0)) === 0;
    g.ozet.push("siparis koşucu: " + k2.son + " · " + ((k2.cikti.split("\n").find((x) => /^HAZIR siparis/.test(x))) || "-") +
                " · foto_uretim=" + (u2 && u2.asama) + " · uretec toplam=" + uretecSayisi() + " · model onizlemeyle ayni=" + ayni);
    iddia("KOPYA KOLU: koşucu siparisi uretec KOSMADAN 'hazir' yapar (uretec toplam 1) · model = onizleme modeli",
      k2.son === "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" && /KOPYA/.test(k2.cikti) && !!u2 && u2.asama === "hazir" &&
        uretecSayisi() === 1 && ayni, k2.cikti.slice(-500));
  } catch (e) {
    iddia("L10 senaryo hatasiz kostu", false, (e && e.stack) || String(e));
  } finally {
    VERI.ornekler.splice(0, VERI.ornekler.length, ...yedek);
    k.kapat();
  }
  return g;
}

async function senaryoTuretik(kok) {
  const g = { L11: [], ozet: [] };
  const iddia = (ad, ok, ek) => g.L11.push({ ad, ok: !!ok, ek: ek || "" });
  const { modul, foto, VERI } = await modulKur(kok);
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-foto-turetik-"));
  GECICILER.push(d);
  const db = path.join(d, "d1.sqlite"), r2d = path.join(d, "r2"), sayac = path.join(d, "uretec.sayac");
  fs.mkdirSync(r2d);
  fs.writeFileSync(path.join(d, "wr.py"), SAHTE_WR);
  fs.writeFileSync(path.join(d, "uretec.py"), SAHTE_URETEC_I);
  fs.writeFileSync(sayac, "");
  fs.writeFileSync(path.join(d, "tablo.json"), JSON.stringify({ isimlik_uret: { bicim: "sozlesme", komut: ["python3", path.join(d, "uretec.py")] } }));
  const kosucu = () => {
    const p = spawnSync("python3", [path.join(kok, "tools", "foto-uretec-kosucu.py"), "--uygula"], {
      encoding: "utf8", timeout: 120000,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", FAKE_DB: db, FAKE_R2: r2d, FAKE_URETEC_SAYAC: sayac,
             FOTO_KOSUCU_WRANGLER: "python3 " + path.join(d, "wr.py"), FOTO_KOSUCU_KILIT: path.join(d, "kilit"),
             FOTO_KOSUCU_PYTHON: "python3", FOTO_KOSUCU_URETEC_TABLO: path.join(d, "tablo.json") } });
    return { son: (p.stdout || "").trim().split("\n").pop(), cikti: (p.stdout || "") + (p.stderr || "") };
  };
  const k = koprukur(db); await k.hazir;
  const d1 = k.d1;
  const env = envKur(d1, r2DizinKur(r2d));
  const istek = istekKur(modul, env);
  // Istemci SAHTE olcu (200 = 2.000 TL) ve sahte tutarlar gonderir; sunucu hicbirini okumamali.
  const siparis = (isNo) => ({ sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri,
    turnstile_token: "j", sepet: [{ foto_is: isNo, olcu_mm: 200, adet: 1, birim_kurus: 1, tutar_kurus: 1, fiyat_kurus: 1 }] });
  const onizle = (ip, uk) => istek("/foto/onizleme", { ip, govde: { tur: "turetik", olcu_mm: 200, parametreler: { uk },
    aydinlatma_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton" } });
  const satir = (n) => d1.prepare("SELECT asama, hata, olcu_mm FROM foto_isler WHERE is_no = ?").bind(n).first();
  const yedek = VERI.ornekler.splice(0);
  try {
    VERI.ornekler.push({ tur: "turetik", kanit: "render", olcu_mm: 100, onizleme: "https://media.pruvo3d.com/t-to.webp",
                         render: "https://media.pruvo3d.com/t-tr.webp", not: "t" });
    await d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('turetik', 1, '2026-10-07T00:00:00.000Z')").run();
    const o = await onizle("198.51.100.220", 123.4);
    const isNo = (o.v && o.v.is) || "yok";
    const gy = path.join(r2d, "foto-uretec-onizleme", isNo, "girdi.json");
    const gj = fs.existsSync(gy) ? JSON.parse(fs.readFileSync(gy, "utf8")) : null;
    const s1 = await satir(isNo);
    iddia("onizleme 200: istemcinin olcu_mm'si (200) OKUNMAZ -> satir olcu 0 + girdi.json olcu 0 (surgu yok)",
      o.kod === 200 && !!s1 && s1.asama === "uretec-onizleme" && s1.olcu_mm === 0 && !!gj && gj.olcu_mm === 0,
      JSON.stringify([o.kod, o.v, s1, gj && gj.olcu_mm]));
    const b0 = await istek("/baslat", { govde: siparis(isNo) });
    const bYok = await istek("/baslat", { govde: siparis("0123456789abcdef0123456789abcdef") });
    iddia("onizlemesiz siparis 400 foto-onizleme-yok (kuyruktaki is + olmayan is)",
      b0.kod === 400 && !!b0.v && b0.v.hata === "foto-onizleme-yok" && bYok.kod === 400 && !!bYok.v && bYok.v.hata === "foto-onizleme-yok",
      JSON.stringify([b0.kod, b0.v, bYok.kod, bYok.v]));
    const k1 = kosucu();
    const s2 = await satir(isNo);
    g.ozet.push("turetilmis koşucu: " + k1.son + " · satir=" + JSON.stringify(s2));
    iddia("GERCEK koşucu onizlemeyi OLCER: uk 123,4 -> satir olcu_mm 123 (yarim yukari) + 'onizleme-hazir'",
      k1.son === "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" && !!s2 && s2.asama === "onizleme-hazir" && s2.olcu_mm === 123,
      JSON.stringify(s2) + " " + k1.cikti.slice(-400));
    const dy = await istek("/foto/durum?is=" + isNo);
    iddia("durum: fiyat onizlemeyle BIRLIKTE = 123 mm x 1000 = 123000 kurus · olcu_kaynagi turetilmis · olcu.json uk 123,4",
      !!dy.v && dy.v.asama === "hazir" && dy.v.olcu_mm === 123 && dy.v.fiyat_kurus === 123000 && dy.v.olcu_kaynagi === "turetilmis" &&
        !!dy.v.olcu && dy.v.olcu.uzun_kenar_mm === 123.4, JSON.stringify(dy.v));
    const b1 = await istek("/baslat", { govde: siparis(isNo) });
    const no = b1.v && b1.v.no;
    const sr = no ? await d1.prepare("SELECT urunler FROM siparisler WHERE siparis_no = ?").bind(no).first() : null;
    const kalem = sr ? (JSON.parse(sr.urunler) || []).find((x) => x && x.foto_is === isNo) : null;
    const fark = kalem && dy.v ? kalem.birim_kurus - dy.v.fiyat_kurus : null;
    g.ozet.push("turetilmis siparis: istemci olcu=200 birim=1 -> satir olcu=" + (kalem && kalem.olcu_mm) + " birim=" +
                (kalem && kalem.birim_kurus) + " fark=" + fark);
    iddia("istemci sahte olcu/fiyat (200 mm, 1 kurus) -> satir SUNUCUNUN olcusu: olcu 123, birim 123000, fark 0, olcu_kaynagi turetilmis",
      b1.kod === 200 && !!kalem && kalem.olcu_mm === 123 && kalem.birim_kurus === 123000 && kalem.tutar_kurus === 123000 &&
        fark === 0 && kalem.olcu_kaynagi === "turetilmis" && foto.olcuKaynagi("isimlik") === "surgu",
      JSON.stringify([b1.kod, b1.v, kalem]));
    const o2 = await onizle("198.51.100.221", 250.5);
    const is2 = (o2.v && o2.v.is) || "yok";
    const k2 = kosucu();
    const s3 = await satir(is2);
    const d2 = await istek("/foto/durum?is=" + is2);
    const b2 = await istek("/baslat", { govde: siparis(is2) });
    iddia("aralik disi olcu (250,5 > 200) -> koşucu RED uretec-red:olcu-aralik-disi, olcu yazilmaz · durum uretec reddi metni · siparis 400",
      o2.kod === 200 && !!s3 && s3.asama === "basarisiz" && s3.hata === "uretec-red:olcu-aralik-disi" && s3.olcu_mm === 0 &&
        !!d2.v && d2.v.asama === "basarisiz" && d2.v.hata === "uretec-red" && d2.v.metin === VERI.URETEC_RED_METIN["olcu-aralik-disi"] &&
        b2.kod === 400, JSON.stringify([s3, d2.v, b2.kod]) + " " + k2.son);
  } catch (e) {
    iddia("L11 senaryo hatasiz kostu", false, (e && e.stack) || String(e));
  } finally {
    VERI.ornekler.splice(0, VERI.ornekler.length, ...yedek);
    k.kapat();
  }
  return g;
}

const ADLAR = {
  L2: "L2 FIYAT YOK -> SATIN ALMA RED", L3: "L3 /foto/litofan SAGLAYICISIZ", L4: "L4 /baslat TUTAR + SECIM",
  L5: "L5 KUYRUK uretec-bekliyor", L6: "L6 PANEL YUKLEME", L7: "L7 PLAKET REGRESYONU", L9: "L9 URETEC OLCU + SVG + AYDINLATMA KOLU",
  L8: "L8 SAKLAMA saglayicisiz",
  L11: "L11 TURETILMIS OLCU EKSENI: olcu onizlemede olculur, fiyat sunucu kaydindan (sentetik turetik, uctan uca)", L10: "L10 URETEC ONIZLEME KUYRUGU -> SIPARIS -> KOPYA KOLU (sentetik isimlik, uctan uca)",
};
const sonuc = await senaryo(canli);
{
  const gi = await senaryoIsimlik(isimlikKokKur(null));
  sonuc.L10 = gi.L10;
  for (const x of gi.ozet) { console.log("UCTAN_UCA_ONIZLEME " + x); }
  const gt = await senaryoTuretik(isimlikKokKur(null));
  sonuc.L11 = gt.L11;
  for (const x of gt.ozet) { console.log("UCTAN_UCA_TURETILMIS " + x); }
}
for (const grup of Object.keys(ADLAR)) {
  console.log(ADLAR[grup]);
  for (const x of sonuc[grup]) { ol(x.ad, x.ok, x.ek); }
}

// ================================================================ MUTANTLAR (izole kopya)

console.log("MUTANTLAR (os.tmpdir() izole kopya; calisma agacina yazilmaz)");

/** shop/src + veri + secenekler KOPYA; buyuk salt-okunur bagimliliklar (jenerator, konfigur.js) bag. */
function kopyaKur() {
  const kok = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-foto-litofan-"));
  GECICILER.push(kok);
  fs.mkdirSync(path.join(kok, "shop"));
  fs.cpSync(path.join(KOK, "shop", "src"), path.join(kok, "shop", "src"), { recursive: true });
  fs.copyFileSync(path.join(KOK, "shop", "config.json"), path.join(kok, "shop", "config.json"));
  fs.copyFileSync(path.join(KOK, "foto-uretim-veri.js"), path.join(kok, "foto-uretim-veri.js"));
  fs.copyFileSync(path.join(KOK, "secenekler.js"), path.join(kok, "secenekler.js"));
  fs.symlinkSync(path.join(KOK, "jenerator"), path.join(kok, "jenerator"));
  fs.symlinkSync(path.join(KOK, "konfigur.js"), path.join(kok, "konfigur.js"));
  return kok;
}

const MUTANTLAR = [
  { ad: "M0 KONTROL (yorum eklendi)", dosya: "shop/src/foto.js", hedef: null,
    capa: 'import "../../foto-uretim-veri.js";', yerine: '// M0 kontrol yorumu\nimport "../../foto-uretim-veri.js";' },
  { ad: "M1 zincir secimi uretec-bekliyor'u HARIC TUTMAZ", dosya: "shop/src/foto.js", hedef: "L5",
    capa: "WHERE asama NOT IN ('hazir', 'elle', 'uretec-bekliyor')", yerine: "WHERE asama NOT IN ('hazir', 'elle')" },
  // ACILIS ANAHTARI mutanti: anahtar suzgeci silinirse anahtarsiz tur acilir -> L2 KIRMIZI.
  { ad: "M2 acikTurler acilis anahtari suzgeci kalkti", dosya: "shop/src/foto.js", hedef: "L2",
    capa: "    .filter((t) => kume.has(t.kod))\n", yerine: "" },
  { ad: "M2b acilis anahtari okunamazsa ACIK (fail-open)", dosya: "shop/src/foto.js", hedef: "L2",
    capa: "    return new Set();\n  }\n}", yerine: "    return new Set(VERI.turler.map((t) => t.kod));\n  }\n}" },
  { ad: "M3 litofan kuyruga 'build-baslat' ile girer", dosya: "shop/src/foto.js", hedef: "L5",
    capa: 'det ? "uretec-bekliyor" : "build-baslat"', yerine: '"build-baslat"' },
  { ad: "M4 yukleme ucu yetki kapisinin ONUNE alindi", dosya: "shop/src/yonet.js", hedef: "L6",
    capa: "  if (!anahtarGecerli(request, url, env)) {",
    yerine: '  if (altYol === "/foto/uretec-yukle" && m === "POST") { return panelUretecYukle(request, env, url, Date.now()); }\n' +
            "  if (!anahtarGecerli(request, url, env)) {" },
  { ad: "M6 olcu.json sizdirmazlik kontrolu silindi", dosya: "shop/src/foto.js", hedef: "L9",
    capa: '  if (o.sizdirmaz !== true) { return "sizdirmaz-degil"; }\n', yerine: "" },
  { ad: "M7a plaka siniri eski sabit 250", dosya: "shop/src/foto.js", hedef: "L9",
    capa: "const PLAKA_MM = VERI.PLAKA_MM;", yerine: "const PLAKA_MM = 250;" },
  { ad: "M7b plaka siniri kontrolu yok", dosya: "shop/src/foto.js", hedef: "L9",
    capa: "kutu.x <= PLAKA_MM && kutu.y <= PLAKA_MM", yerine: "true" },
  { ad: "M7c manifest yapboz ust siniri 280", dosya: "foto-uretim-veri.js", hedef: "L9",
    capa: "        olcu_mm: { en_az: 100, en_cok: 190 },", yerine: "        olcu_mm: { en_az: 100, en_cok: 280 }," },
  { ad: "M7 uzun kenar tolerans kontrolu silindi", dosya: "shop/src/foto.js", hedef: "L9",
    capa: "!(Math.abs(o.uzun_kenar_mm - k.olcu_mm) <= k.olcu_mm * tol + 1e-9)", yerine: "false" },
  { ad: "M8 parametre sema kontrolu silindi", dosya: "shop/src/foto.js", hedef: "L3",
    capa: "  if (!p.ok) { return p.hata; }\n", yerine: "" },
  { ad: "M9 kuyruk atlandi: uretec onizleme satiri dogrudan 'hazir'", dosya: "shop/src/foto.js", hedef: "L10",
    capa: "\" VALUES (?, ?, ?, ?, ?, 'uretec-onizleme', 0, '', ?, ?)\"", yerine: "\" VALUES (?, ?, ?, ?, ?, 'hazir', 0, '', ?, ?)\"" },
  { ad: "M10 siparis ucu uretec turunde 'hazir' bekler (onizleme-hazir ise baglanmaz)", dosya: "shop/src/foto.js", hedef: "L10",
    capa: "? \"onizleme-hazir\" : \"hazir\";", yerine: "? \"hazir\" : \"hazir\";" },
  { ad: "M11 uretec kolu yonlendirmesi silindi (saglayici yoluna duser)", dosya: "shop/src/foto.js", hedef: "L10",
    capa: "  if (g && typeof g === \"object\" && uretecOnizlemeTuru(g.tur)) { return uretecOnizlemeUcu(request, env, simdi, g); }\n", yerine: "" },
  // kopru-15 dilim-3 (TURETILMIS eksen): sunucu istemcinin olcusunu/fiyatini kullanirsa L11 KIRMIZI.
  { ad: "M12 siparis fiyati istemcinin olcu_mm'sinden (kayitli onizleme olcusu yerine)", dosya: "shop/src/foto.js", hedef: "L11",
    capa: "  const mm = VERI.olcuTuretilmis(tur.kod) ? is.olcu_mm : k.olcu_mm;\n", yerine: "  const mm = k.olcu_mm;\n" },
  { ad: "M13 onizleme ucu istemcinin olcu_mm'sini yazar", dosya: "shop/src/foto.js", hedef: "L11",
    capa: "  const olcu = turetilmis ? 0 : Number.isInteger(g.olcu_mm) ? g.olcu_mm : null;\n",
    yerine: "  const olcu = Number.isInteger(g.olcu_mm) ? g.olcu_mm : null;\n" },
  { ad: "M14 durum fiyati kayitli olcu yerine aralik ucundan", dosya: "shop/src/foto.js", hedef: "L11",
    capa: "v.fiyat_kurus = VERI.fiyatKurus(is.tur, is.olcu_mm);", yerine: "v.fiyat_kurus = VERI.fiyatKurus(is.tur, VERI.olcuAraligi(is.tur).en_cok);" },
  { ad: "M5 saglayici env'siz dalda onizleme temizligi kaldirildi", dosya: "shop/src/foto.js", hedef: "L8",
    capa: "      try { ozet.silinen = await onizlemeTemizle(env, simdi); } catch (e) { if (!tabloYok(e)) { throw e; } }\n",
    yerine: "" },
];

let survivor = 0;
for (const mu of MUTANTLAR) {
  const asil = fs.readFileSync(path.join(KOK, mu.dosya), "utf8");
  if (asil.split(mu.capa).length - 1 !== 1) {
    survivor++;
    ol(mu.ad + " — capa bulundu (tek)", false, "capa kayip/coklu: " + mu.capa);
    continue;
  }
  const kok = kopyaKur();
  fs.writeFileSync(path.join(kok, mu.dosya), asil.replace(mu.capa, mu.yerine));
  let g;
  try {
    g = await senaryo(await modulKur(kok));
    g.L10 = (await senaryoIsimlik(isimlikKokKur(mu))).L10;
    g.L11 = (await senaryoTuretik(isimlikKokKur(mu))).L11;
  } catch (e) {
    survivor++;
    ol(mu.ad + " — mutant yuklendi", false, (e && e.stack) || String(e));
    continue;
  }
  const kirmizilar = Object.keys(ADLAR).filter((a) => !grupYesil(g, a));
  if (mu.hedef === null) {
    ol(mu.ad + " -> hicbir grup kirmizi yanmaz", kirmizilar.length === 0, kirmizilar.join(","));
  } else {
    const oldu = kirmizilar.includes(mu.hedef);
    if (!oldu) { survivor++; }
    ol(mu.ad + " -> " + mu.hedef + " KIRMIZI yanar", oldu, "kirmizi gruplar: " + (kirmizilar.join(",") || "yok"));
  }
}
temizle();
const kalan = GECICILER.filter((d) => fs.existsSync(d)).length;
ol("GECICI kopyalar silindi (kalan 0)", kalan === 0, String(kalan));

console.log("SURVIVOR=" + survivor);
if (kirmizi || survivor) { console.log("\n❌ KIRMIZI: " + kirmizi + " · SURVIVOR=" + survivor); process.exit(1); }
console.log("\n✅ HEPSI GECTI");
process.exit(0);
