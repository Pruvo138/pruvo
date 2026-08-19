/**
 * POST /api/shop/talep — site talep hatti.
 *
 * Saf tutulur: wrangler importu yoktur, boylece dogrudan birim test edilebilir.
 * Kimlik bilgileri bu kayda alinmaz; WhatsApp koprusu talep kodudur.
 */

export const TALEP_ALFABE = "23456789ABCDEFGHJKMNPQRSTVWXYZ";
export const TALEP_KOD_RE = new RegExp("^PR-[" + TALEP_ALFABE + "]{6}$");

const KOD_UZUNLUGU = 6;
const GOVDE_BAYT_TAVANI = 4096;
const WA_BASE = "https://wa.me/905451386526";
const KANALLAR = new Set(["site", "whatsapp"]);
export const ALAN_TAVANLARI = Object.freeze({
  kategori: 40,
  marka: 60,
  model: 60,
  yil: 20,
  parca_adi: 120,
  notu: 500,
});
const izinliAnahtarlar = new Set([
  "kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",
]);

function cevap(govde, status) {
  return new Response(JSON.stringify(govde), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

function gecersiz(status = 400) {
  return cevap({ hata: "gecersiz", wa: WA_BASE }, status);
}

function waAdresi(kod) {
  return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod);
}

/*
 * Kategori/marka satirlari bu pakette yalniz kanonik jetonlardan uretilir.
 * Ham serbest metin, RED disindaki yolda bile WA URL'ine dogrudan tasinmaz.
 * Katalogdaki karsiligi olmayan jetonlar ozete girmez; serbest alanlar da
 * normalize edilip kendi tavanlarinin yarisinda tutulur.
 */
const KANONIK_KATEGORI_JETONLARI = new Set([
  "Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat", "Ev", "Ofis",
  "Elektronik", "Kamera", "Bahçe", "Dekorasyon", "Oyun/Hobi",
]);

function kanonikJeton(deger, kaynak) {
  if (typeof deger !== "string") { return ""; }
  const temiz = deger.normalize("NFKC").trim().replace(/\s+/gu, " ");
  if (!temiz || /[\u0000-\u001f\u007f]/u.test(temiz)) { return ""; }
  if (kaynak === "kategori" && !KANONIK_KATEGORI_JETONLARI.has(temiz)) { return ""; }
  /* Marka kaynagi D1'deki kanonik marka jetonudur; guvenli jeton bicimi korunur. */
  if (kaynak === "marka" && !/^[\p{L}\p{N}][\p{L}\p{N} ._\-/]*$/u.test(temiz)) { return ""; }
  return temiz;
}

function ozetAlani(deger, tavan) {
  if (typeof deger !== "string") { return ""; }
  const temiz = deger.replace(/[\u0000-\u001f\u007f]/gu, " ").replace(/\s+/gu, " ").trim();
  return temiz.slice(0, Math.floor(tavan / 2));
}

function waOzeti(govde) {
  const satirlar = [];
  const kategori = kanonikJeton(govde.kategori, "kategori");
  const marka = kanonikJeton(govde.marka, "marka");
  const alanlar = [
    ["kategori", kategori], ["marka", marka],
    ["model", ozetAlani(govde.model, ALAN_TAVANLARI.model)],
    ["yil", ozetAlani(govde.yil, ALAN_TAVANLARI.yil)],
    ["parca", ozetAlani(govde.parca_adi, ALAN_TAVANLARI.parca_adi)],
    ["not", ozetAlani(govde.notu, ALAN_TAVANLARI.notu)],
  ];
  for (const [ad, deger] of alanlar) {
    if (deger) { satirlar.push(ad + ": " + deger); }
  }
  let metin = satirlar.join("\n");
  if (metin.length > 1500) { metin = metin.slice(0, 1499) + "…"; }
  return WA_BASE + "?text=" + encodeURIComponent(metin);
}

function birHost(deger) {
  if (typeof deger !== "string" || !deger) { return null; }
  try { return new URL(deger).host.toLowerCase(); } catch (e) { return null; }
}

function izinliHostlar(env) {
  const set = new Set(["pruvo3d.com", "www.pruvo3d.com"]);
  const h = birHost(env && env.SITE_URL);
  if (h) { set.add(h); }
  return set;
}

function originIzinli(request, env) {
  const headers = request && request.headers;
  if (!headers || typeof headers.get !== "function") { return false; }
  const izin = izinliHostlar(env);
  const origin = birHost(headers.get("Origin"));
  if (origin) { return izin.has(origin); }
  const referer = birHost(headers.get("Referer"));
  if (referer) { return izin.has(referer); }
  return false;
}

/** Binding yoksa yerel test icin sessizce devam eder (deployment oncesi). */
async function kotaAsildi(request, env) {
  const rl = env && env.TALEP_RATE_LIMIT;
  if (!rl || typeof rl.limit !== "function") { return false; }
  const ip = (request.headers && typeof request.headers.get === "function"
    ? request.headers.get("CF-Connecting-IP") : "") || "yok";
  try {
    const sonuc = await rl.limit({ key: ip });
    return !(sonuc && sonuc.success);
  } catch (e) {
    console.error("talep rate-limit hatasi (fail-open):", e && e.stack ? e.stack : (e && e.name) || "Error");
    return false;
  }
}

function alanlarGecerli(govde) {
  if (!govde || typeof govde !== "object" || Array.isArray(govde)) { return false; }
  for (const anahtar of Object.keys(govde)) {
    if (!izinliAnahtarlar.has(anahtar)) { return false; }
  }
  for (const anahtar of izinliAnahtarlar) {
    if (govde[anahtar] !== undefined && typeof govde[anahtar] !== "string") { return false; }
  }
  if (!KANALLAR.has(govde.kanal)) { return false; }
  for (const [alan, tavan] of Object.entries(ALAN_TAVANLARI)) {
    if (govde[alan] !== undefined && govde[alan].length > tavan) { return false; }
  }
  return true;
}

function talepKoduUret() {
  let kod = "PR-";
  const bayt = new Uint8Array(1);
  const kabulSiniri = Math.floor(256 / TALEP_ALFABE.length) * TALEP_ALFABE.length;
  for (let i = 0; i < KOD_UZUNLUGU; i++) {
    do { crypto.getRandomValues(bayt); } while (bayt[0] >= kabulSiniri);
    kod += TALEP_ALFABE[bayt[0] % TALEP_ALFABE.length];
  }
  return kod;
}

function benzersizCakisma(hata) {
  const metin = String(hata && hata.message || hata || "").toUpperCase();
  return metin.includes("UNIQUE") || metin.includes("PRIMARY KEY");
}

function hataSinifi(hata) {
  return hata && hata.name ? hata.name : "Error";
}

/* KV binding yok: bugunku sayac sink'i yalniz gecici console.error kaydidir. */
function talepOlayiSay(env, sebep) {
  if (!["d1_hata", "kod_cakisma", "yapilandirma"].includes(sebep)) { sebep = "yapilandirma"; }
  console.error("talep_kod_uretilemedi sebep=" + sebep + " zaman=" + new Date().toISOString());
}

export async function talepKaydet(request, env) {
  if (request.method !== "POST") { return gecersiz(405); }
  if (!originIzinli(request, env)) { return gecersiz(); }
  if (await kotaAsildi(request, env)) { return gecersiz(); }

  const contentLength = request.headers && typeof request.headers.get === "function"
    ? request.headers.get("Content-Length") : null;
  if (contentLength !== null && Number.isFinite(Number(contentLength)) &&
      Number(contentLength) > GOVDE_BAYT_TAVANI) { return gecersiz(); }

  let metin;
  try {
    metin = await request.text();
  } catch (e) {
    return gecersiz();
  }
  if (new TextEncoder().encode(metin).length > GOVDE_BAYT_TAVANI) { return gecersiz(); }

  let govde;
  try {
    govde = JSON.parse(metin);
  } catch (e) {
    return gecersiz();
  }
  if (!alanlarGecerli(govde)) { return gecersiz(); }
  if (govde.website !== undefined && govde.website !== "") { return gecersiz(); }

  const tarih = new Date().toISOString();
  for (let deneme = 0; deneme < 5; deneme++) {
    const kod = talepKoduUret();
    let ifade;
    let bag;
    try {
      ifade = env.KATALOG.prepare(
        "INSERT INTO talepler" +
        " (kod, olusturma, kanal, kategori, marka, model, yil, parca_adi, notu, durum)" +
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'yeni')"
      );
      bag = ifade.bind(
        kod, tarih, govde.kanal, govde.kategori ?? null, govde.marka ?? null,
        govde.model ?? null, govde.yil ?? null, govde.parca_adi ?? null, govde.notu ?? null
      );
    } catch (e) {
      talepOlayiSay(env, "yapilandirma");
      return cevap({ kod: null, wa: waOzeti(govde) }, 200);
    }
    try {
      await bag.run();
      return cevap({ kod, wa: waAdresi(kod) }, 200);
    } catch (e) {
      if (benzersizCakisma(e) && deneme < 4) { continue; }
      talepOlayiSay(env, benzersizCakisma(e) ? "kod_cakisma" : "d1_hata");
      return cevap({ kod: null, wa: waOzeti(govde) }, 200);
    }
  }
}

export { izinliAnahtarlar, talepKoduUret };
