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
 *
 * MUTANTLAR: os.tmpdir()'de shop/src + foto-uretim-veri.js + secenekler.js IZOLE kopyasi
 * (calisma agacina yazim YOK; kopya cikista silinir). M1..M4 hedef grubu KIRMIZIYA cevirmeli,
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

import { spawn } from "node:child_process";
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

function koprukur() {
  const p = spawn("python3", [path.join(BURASI, "ortak", "sqlite-koprusu.py")],
                  { stdio: ["pipe", "pipe", "inherit"] });
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
    URETIM_API_TABAN: TABAN, URETIM_TUR_ONEK: "tur-onek", URETIM_TUR_PLAKET: "tur-plaket", URETIM_API_ANAHTAR: "sahte-anahtar",
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
const litofanGovde = (ek) => ({ tur: "litofan", olcu_mm: 120, gorsel: uri(HARITA), hak_onay: true,
  turnstile_token: "jeton", ...(ek || {}) });

// ---------------------------------------------------------------- SENARYO (canli + her mutant)

/** Gruplu sonuc: {L2: [{ad, ok, ek}], ...}. Her kosum TEMIZ SQLite + temiz R2 ile. */
async function senaryo(ms) {
  const { modul, foto, VERI } = ms;
  const g = { L2: [], L3: [], L4: [], L5: [], L6: [], L7: [] };
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

    // ---- L2: fiyat satiri YOK
    const a2 = await istek("/foto/acik");
    iddia("L2", "fiyat yokken /foto/acik'te litofan 0",
          a2.kod === 200 && !(a2.v.turler || []).some((t) => t.kod === "litofan"), JSON.stringify(a2.v));
    const l2 = await istek("/foto/litofan", { ip: "10.2.0.1", govde: litofanGovde({ onay_surum: surum }) });
    iddia("L2", "fiyat yokken /foto/litofan 400 tur-kapali", l2.kod === 400 && l2.v && l2.v.hata === "tur-kapali", JSON.stringify(l2.v));
    const isEl = "a".repeat(32);
    await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih) VALUES (?, 'litofan', 120, 'z', ?, 'hazir', ?)")
      .bind(isEl, simdi, simdi).run();
    const iyOnce = P.iyzico;
    const b2 = await istek("/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: isEl, olcu_mm: 120, adet: 1, secim: { panel_malzeme: "PLA", ayak_malzeme: "PLA", ayak_renk: "Beyaz" } }] } });
    iddia("L2", "fiyat yokken /baslat litofan kalemi 400 (odeme baslamaz)", b2.kod === 400 && P.iyzico === iyOnce, JSON.stringify(b2.v));

    // ---- L3: fiyat + ornek VAR
    await d1.prepare("INSERT INTO foto_fiyat (tur, olcu_mm, fiyat_kurus, guncel) VALUES ('litofan', 120, 45000, 'x')").run();
    const sgOnce = P.saglayici;
    const a3 = await istek("/foto/acik");
    const lt = a3.v && (a3.v.turler || []).find((t) => t.kod === "litofan");
    iddia("L3", "fiyatla /foto/acik litofan 120 mm sunar", !!lt && lt.olculer.length === 1 && lt.olculer[0].mm === 120, JSON.stringify(a3.v));
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
    const onaysiz = await istek("/foto/litofan", { ip: "10.3.0.5", govde: litofanGovde({ onay_surum: surum, hak_onay: false }) });
    const eskiSurum = await istek("/foto/litofan", { ip: "10.3.0.6", govde: litofanGovde({ onay_surum: "eski" }) });
    iddia("L3", "hak onayi yok 400 · eski onay surumu 409", onaysiz.kod === 400 && eskiSurum.kod === 409,
          onaysiz.kod + "/" + eskiSurum.kod);
    const olcuYok = await istek("/foto/litofan", { ip: "10.3.0.7", govde: litofanGovde({ onay_surum: surum, olcu_mm: 150 }) });
    iddia("L3", "fiyat tablosunda olmayan olcu 400 gecersiz-olcu", olcuYok.kod === 400 && olcuYok.v.hata === "gecersiz-olcu", JSON.stringify(olcuYok.v));
    const sgOnce2 = P.saglayici;
    const yanlisUc = await istek("/foto/onizleme", { ip: "10.3.0.8", govde: { tur: "litofan", olcu_mm: 120, gorsel: uri(HARITA),
      hak_onay: true, aktarim_onay: true, onay_surum: surum, turnstile_token: "j" } });
    iddia("L3", "/foto/onizleme litofani saglayiciya GOTURMEZ (400 tur-kapali, cagri 0)",
          yanlisUc.kod === 400 && yanlisUc.v.hata === "tur-kapali" && P.saglayici === sgOnce2, JSON.stringify(yanlisUc.v));

    // ---- L4: /baslat
    const sepet = (secim, adet) => ({ sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: isNo, olcu_mm: 120, adet: adet || 1, ...(secim ? { secim } : {}) }] });
    const iyOnce4 = P.iyzico;
    const b4 = await istek("/baslat", { govde: sepet({ panel_malzeme: "PETG", ayak_malzeme: "ASA", ayak_renk: "Siyah" }, 2) });
    const siparisNo = b4.v && b4.v.no;
    const s4 = siparisNo ? await d1.prepare("SELECT durum, urunler, tutar_kurus FROM siparisler WHERE siparis_no = ?").bind(siparisNo).first() : null;
    const k4 = s4 && JSON.parse(s4.urunler)[0];
    iddia("L4", "/baslat 200, tutar = tablo x adet (45000 x 2), istemci tutari okunmaz",
          b4.kod === 200 && P.iyzico === iyOnce4 + 1 && !!s4 && s4.tutar_kurus === 90000 && k4.birim_kurus === 45000 &&
          k4.tutar_kurus === 90000, JSON.stringify(b4.v) + " " + (s4 && s4.tutar_kurus));
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
    await d1.prepare("INSERT INTO foto_fiyat (tur, olcu_mm, fiyat_kurus, guncel) VALUES ('plaket', 100, 34900, 'x')").run();
    const p7 = await istek("/foto/onizleme", { ip: "10.7.0.1", govde: { tur: "plaket", olcu_mm: 100, gorsel: uri(HARITA),
      hak_onay: true, aktarim_onay: true, onay_surum: surum, turnstile_token: "j" } });
    const pis = p7.v && p7.v.is;
    const dur = pis ? await istek("/foto/durum?is=" + pis) : { v: null };
    iddia("L7", "plaket onizleme saglayici kolundan 'hazir'", p7.kod === 200 && !!dur.v && dur.v.asama === "hazir",
          JSON.stringify(p7.v) + " " + JSON.stringify(dur.v));
    const b7 = await istek("/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: pis, olcu_mm: 100, adet: 1, secim: { ayak_renk: "Mor" } }] } });
    const s7 = b7.v && b7.v.no ? await d1.prepare("SELECT urunler, tutar_kurus FROM siparisler WHERE siparis_no = ?").bind(b7.v.no).first() : null;
    const k7 = s7 && JSON.parse(s7.urunler)[0];
    iddia("L7", "plaket satiri bugunku gibi (PLA, 4 renk, ayak 1, secim YOK SAYILIR)", b7.kod === 200 && !!k7 &&
          s7.tutar_kurus === 34900 && k7.malzeme === "PLA" && k7.renk === "4 renk" && k7.foto_ayak === 1 &&
          k7.foto_secim === undefined && k7.foto_kol === undefined, JSON.stringify(k7));
    if (b7.v && b7.v.no) { await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(b7.v.no).run(); }
    await foto.fotoUretimTuru(env, Date.now(), null);
    const u7 = b7.v && b7.v.no ? await d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = ?").bind(b7.v.no).first() : null;
    iddia("L7", "odenen plaket kuyrukta 'build-baslat'", !!u7 && u7.asama === "build-baslat", JSON.stringify(u7));
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
  const hatali = [];
  for (const t of VERI.turler) {
    const a = t.olcu_mm || {};
    if (t.girdi !== "foto-1") { hatali.push(t.kod + ":girdi"); }
    if (!KOLLAR.includes(t.kol)) { hatali.push(t.kod + ":kol"); }
    if (!(Number.isInteger(a.en_az) && Number.isInteger(a.en_cok) && a.en_az > 0 && a.en_cok >= a.en_az)) { hatali.push(t.kod + ":olcu"); }
    if (!Array.isArray(t.renk_bolgeleri) || t.renk_bolgeleri.some((b) => !b || !b.kod || !b.ad ||
        !Array.isArray(b.renkler) || !b.renkler.length)) { hatali.push(t.kod + ":renk"); }
    const m = t.malzemeler;
    if (!m || typeof m !== "object" || Array.isArray(m) ||
        Object.values(m).some((l) => !Array.isArray(l) || !l.length || l.some((x) => !filament.includes(x)))) {
      hatali.push(t.kod + ":malzeme");
    }
  }
  ol("L1a her tur: girdi/kol/olcu_mm/renk_bolgeleri/malzemeler gecerli (malzeme ⊆ FILAMENT_SIRA)",
     filament.length > 0 && hatali.length === 0, hatali.join(","));
  const sag = VERI.turler.filter((t) => t.kol === "saglayici").map((t) => t.kod).sort();
  ol("L1b saglayici turleri = TUR_ORTAM anahtarlari", JSON.stringify(sag) === JSON.stringify(Object.keys(foto.TUR_ORTAM).sort()),
     JSON.stringify(sag));
  const det = VERI.turler.filter((t) => t.kol === "deterministik").map((t) => t.kod);
  ol("L1c deterministik ∩ TUR_ORTAM = ∅ ve sunucu kumesi kayittan turetilir",
     det.every((d) => !Object.prototype.hasOwnProperty.call(foto.TUR_ORTAM, d)) &&
       JSON.stringify(foto.DETERMINISTIK_TURLER) === JSON.stringify(det), JSON.stringify(foto.DETERMINISTIK_TURLER));
  const lit = VERI.turBul("litofan");
  ol("L1d litofan: deterministik, 80–200 mm, ABS 0 (Dekorasyon sinifi)", !!lit && lit.kol === "deterministik" &&
     lit.olcu_mm.en_az === 80 && lit.olcu_mm.en_cok === 200 &&
     !Object.values(lit.malzemeler).some((l) => l.includes("ABS")), JSON.stringify(lit && lit.malzemeler));
  const pl = VERI.olcuAraligi("plaket");
  ol("L1e plaket kaydi bugunku davranisi birebir tarif eder (50–300 mm, renk secimi yok, malzeme {})",
     !!pl && pl.en_az === foto.OLCU_MM_EN_AZ && pl.en_cok === foto.OLCU_MM_EN_COK &&
       VERI.turBul("plaket").renk_bolgeleri.length === 0 && Object.keys(VERI.turBul("plaket").malzemeler).length === 0 &&
       VERI.kolu("plaket") === "saglayici" && VERI.kolu("yok") === "" && VERI.olcuAraligi("yok") === null, JSON.stringify(pl));
}

const ADLAR = {
  L2: "L2 FIYAT YOK -> SATIN ALMA RED", L3: "L3 /foto/litofan SAGLAYICISIZ", L4: "L4 /baslat TUTAR + SECIM",
  L5: "L5 KUYRUK uretec-bekliyor", L6: "L6 PANEL YUKLEME", L7: "L7 PLAKET REGRESYONU",
};
const sonuc = await senaryo(canli);
for (const grup of Object.keys(ADLAR)) {
  console.log(ADLAR[grup]);
  for (const x of sonuc[grup]) { ol(x.ad, x.ok, x.ek); }
}

// ================================================================ MUTANTLAR (izole kopya)

console.log("MUTANTLAR (os.tmpdir() izole kopya; calisma agacina yazilmaz)");
const GECICILER = [];
const temizle = () => { for (const d of GECICILER) { fs.rmSync(d, { recursive: true, force: true }); } };
process.on("exit", temizle);

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
  { ad: "M2 acikTurler fiyat suzgeci kalkti", dosya: "shop/src/foto.js", hedef: "L2",
    capa: "    .filter((t) => t.olculer.length > 0);", yerine: "    ;" },
  { ad: "M3 litofan kuyruga 'build-baslat' ile girer", dosya: "shop/src/foto.js", hedef: "L5",
    capa: 'det ? "uretec-bekliyor" : "build-baslat"', yerine: '"build-baslat"' },
  { ad: "M4 yukleme ucu yetki kapisinin ONUNE alindi", dosya: "shop/src/yonet.js", hedef: "L6",
    capa: "  if (!anahtarGecerli(request, url, env)) {",
    yerine: '  if (altYol === "/foto/uretec-yukle" && m === "POST") { return panelUretecYukle(request, env, url, Date.now()); }\n' +
            "  if (!anahtarGecerli(request, url, env)) {" },
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
  try { g = await senaryo(await modulKur(kok)); } catch (e) {
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
