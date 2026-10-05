/**
 * pruvo-shop — FOTOGRAFTAN OZEL URETIM (ana sayfa bolumu; Okan karari 5 Eki 2026).
 *
 * AKIS: musteri fotograf yukler -> tur + olcu -> ONIZLEME (odemeden ONCE yalniz bu adim
 * kredi harcar) -> mevcut odeme (/baslat, kart) -> odeme DOGRULANINCA (siparis 'odendi')
 * cron uretim zincirini yurutur: model -> basilabilirlik analizi -> 4 renk ayrimi -> 3MF +
 * GLB bizim ozel R2 kovamiza -> siparis panelinde kalemin yaninda.
 *
 * Uclar (index.js /api/shop/foto/* -> fotoUclari):
 *   GET  /foto/acik            -> bolum durumu: acik mi, siparis alan turler + olcu/fiyat
 *   POST /foto/onizleme        -> fotograf (data URI) + tur + olcu + onaylar + bot jetonu
 *                                 -> {is}  (is = tahmin edilemez 32 hex onizleme anahtari)
 *   GET  /foto/durum?is=       -> onizleme hazir mi; hazirsa bizim adresimizden gorsel
 *   GET  /foto/gorsel?is=      -> onizleme gorseli (ozel kovadan; yalniz is anahtariyla)
 *
 * 🔴 MARKASIZ / GIZLILIK (BaBa hukmu 5. madde): hizmet saglayicinin ADI ve HOST'U bu dosyada,
 *    sitede ve commit mesajinda GECMEZ. Uc tabani ve tur yolu onegi de anahtar gibi ORTAM
 *    DEGISKENINDEN okunur (URETIM_API_TABAN, URETIM_TUR_ONEK, URETIM_API_ANAHTAR — ucu de
 *    `wrangler secret put`). Saglayicinin hata metni musteriye ASLA aktarilmaz (ad sizabilir);
 *    musteri yalniz bizim sabit Turkce metinlerimizi gorur. Saglayici gorsel adresi de
 *    tarayiciya verilmez: onizleme indirilip bizim ucumuzdan sunulur.
 * 🔴 MUSTERI FOTOGRAFI SAKLANMAZ: fotograf saglayiciya data URI olarak dogrudan gider; D1'e,
 *    R2'ye, loga YAZILMAZ. Ham IP de yazilmaz (ziyaretci = tuzlu sha256 ozeti).
 * 🔴 KREDI KORUMASI (6. madde): bot jetonu (fail-CLOSED) + ziyaretci basi 24 saatte
 *    PRUVO_FOTO.sinir_ziyaretci_24s onizleme + gunluk tavan + havuz esigi (bakiye esigin
 *    altina inince bolum kendini kapatir + Okan'a TEK bildirim). Otomatik kredi satin alma
 *    YOKTUR. Harcanan her kredi `foto_kredi` defterine gorev kimligiyle (idempotent) yazilir.
 * 🔴 SESSIZ GECIS YOK (2. madde): analiz kirmiziysa renk adimi KOSMAZ; uretim satiri
 *    'elle' asamasina sebebiyle duser, panelde gorunur ve Telegram'a bir kez gider.
 */

import "../../foto-uretim-veri.js";

const VERI = globalThis.PRUVO_FOTO;
if (!VERI) { throw new Error("foto-uretim-veri.js yuklenemedi — tur/ornek tek kaynagi yok"); }

// ---------------------------------------------------------------- sabitler (tek yer)

/** Bizim tur kodumuz -> saglayicinin urun yolu parcasi (genel Ingilizce adlar). */
export const TUR_YOLU = { anahtarlik: "keychain", magnet: "fridge-magnet" };
/** Build adiminda olcu sinirlari (mm) — fiyat tablosu satiri bu araligin disinda YAZILAMAZ. */
export const OLCU_MM_EN_AZ = 20;
export const OLCU_MM_EN_COK = 150;
/** Bir siparis kalemi en cok kac adet (ayni dosyadan coklu baski). */
export const FOTO_ADET_EN_COK = 20;
/** Yuklenen fotografin cozulmus boyut sinirlari (bayt). Bolum gondermeden once kucultur. */
export const GORSEL_EN_COK_BAYT = 4 * 1024 * 1024;
export const GORSEL_EN_AZ_BAYT = 2 * 1024;
/** Tum ziyaretciler icin 24 saatlik onizleme tavani (kotu niyetli dagitik kullanima fren). */
export const GUNLUK_ONIZLEME_TAVANI = 40;
/** Havuz esigi: bakiye (kredi) bunun + bekleyen uretim payinin altina inince bolum kapanir. */
export const HAVUZ_ESIK_KREDI = 120;
/** Odenmis ama modeli henuz kurulmamis HER uretim icin ayrilan kredi (model+renk payi). */
export const URETIM_PAYI_KREDI = 40;
/** Bakiye onbellegi (ms) — her ana sayfa gorunumunde saglayiciya gidilmesin. */
export const BAKIYE_TAZELIK_MS = 5 * 60 * 1000;
/** Cron turunda en cok kac uretim satiri ilerletilir. */
export const URETIM_TUR_LIMITI = 4;
/** Saglayici gecici hatasinda (ag/5xx/429) kac turdan sonra satir 'elle'ye duser. */
export const URETIM_DENEME_TAVANI = 8;
/** Onizleme durum sorgusu saglayiciya en sik bu araliklarla gider (ms). */
export const DURUM_ARALIK_MS = 2500;
/** Siparise donusmeyen onizleme gorseli bu kadar saat sonra silinir (onay metninde: 3 gun). */
export const ONIZLEME_SAKLAMA_SAAT = 72;
/** Saglayici dosyalari 3 gun tutar; model bu saatten eski onizlemeden KURULMAZ (elle). */
export const ONIZLEME_KURULUM_SINIRI_SAAT = 70;
/** Indirilen uretim dosyasi icin ust sinir (bayt). */
export const DOSYA_EN_COK_BAYT = 80 * 1024 * 1024;
const SAGLAYICI_ZAMAN_ASIMI_MS = 30000;

const IS_KALIBI = /^[a-f0-9]{32}$/;
const SIPARIS_KALIBI = /^[A-Za-z0-9-]{6,40}$/;

// ---------------------------------------------------------------- yardimcilar

function fjson(veri, kod, ekBaslik) {
  return new Response(JSON.stringify(veri), {
    status: kod || 200,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
               ...(ekBaslik || {}) },
  });
}

function simdiIso(simdi) { return new Date(simdi).toISOString(); }

function saatOnce(simdi, saat) { return new Date(simdi - saat * 3600 * 1000).toISOString(); }

function hex(bayt) {
  return [...new Uint8Array(bayt)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function yeniIsNo() {
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  return hex(b);
}

/** Ziyaretci kimligi: tuzlu sha256(ip) ilk 16 hex. HAM IP HICBIR YERE YAZILMAZ. */
export async function ziyaretciOzeti(env, ip) {
  const tuz = (env && (env.FOTO_TUZ || env.YONET_ANAHTAR)) || "pruvo-foto";
  const veri = new TextEncoder().encode("foto|" + String(ip || "yok") + "|" + tuz);
  return hex(await crypto.subtle.digest("SHA-256", veri)).slice(0, 16);
}

/** Tablo yoksa (sema henuz canliya uygulanmadi) bos sonuc — bolum kapali sayilir. */
function tabloYok(e) { return /no such table/i.test(String((e && e.message) || e)); }

// ---------------------------------------------------------------- yapilandirma

/**
 * Bolumun siparis/onizleme alabilmesi icin gereken HER sart. Biri eksikse bolum KAPALI
 * (fail-closed): eksik listesi panelde gorunur, musteriye yalniz "su an alinamiyor" denir.
 */
export function yapilandirma(env) {
  const eksik = [];
  if (!env || !env.URETIM_API_TABAN) { eksik.push("uc-tabani"); }
  if (!env || !env.URETIM_TUR_ONEK) { eksik.push("tur-oneki"); }
  if (!env || !env.URETIM_API_ANAHTAR) { eksik.push("api-anahtari"); }
  if (!env || !env.TURNSTILE_SECRET) { eksik.push("bot-dogrulama"); }
  if (!env || !env.OZEL_DOSYA) { eksik.push("ozel-kova"); }
  if (!env || !env.KATALOG) { eksik.push("veritabani"); }
  if (VERI.onay_onayli !== true) { eksik.push("onay-metni-onayi"); }
  if (!VERI.turler.some((t) => VERI.ornekSayisi(t.kod) > 0)) { eksik.push("gercek-ornek"); }
  return { hazir: eksik.length === 0, eksik };
}

/** Fiyat tablosu: [{tur, olcu_mm, fiyat_kurus}] (yalniz fiyati > 0 olan satirlar). */
export async function fiyatTablosu(env) {
  try {
    const r = await env.KATALOG.prepare(
      "SELECT tur, olcu_mm, fiyat_kurus FROM foto_fiyat WHERE fiyat_kurus > 0 ORDER BY tur, olcu_mm"
    ).all();
    return r.results || [];
  } catch (e) {
    if (tabloYok(e)) { return []; }
    throw e;
  }
}

/** Siparis alabilen turler: gercek ornegi >=1 VE fiyat tablosunda >=1 olcusu olanlar. */
export function acikTurler(fiyatlar) {
  return VERI.turler
    .filter((t) => Object.prototype.hasOwnProperty.call(TUR_YOLU, t.kod))
    .filter((t) => VERI.ornekSayisi(t.kod) > 0)
    .map((t) => ({
      kod: t.kod, ad: t.ad, aciklama: t.aciklama,
      ornek_sayisi: VERI.ornekSayisi(t.kod),
      olculer: fiyatlar.filter((f) => f.tur === t.kod &&
        Number.isInteger(f.olcu_mm) && f.olcu_mm >= OLCU_MM_EN_AZ && f.olcu_mm <= OLCU_MM_EN_COK)
        .map((f) => ({ mm: f.olcu_mm, fiyat_kurus: f.fiyat_kurus })),
    }))
    .filter((t) => t.olculer.length > 0);
}

// ---------------------------------------------------------------- saglayici istemcisi

/**
 * Saglayiciya tek cagri. Donus {kod, govde}; ag hatasi/zaman asimi -> {kod: 0}.
 * Hata METNI cagirana tasinir ama MUSTERIYE ASLA iletilmez (yalniz loga, kisaltilmis).
 */
async function saglayici(env, yontem, yol, govde) {
  const taban = String(env.URETIM_API_TABAN || "").replace(/\/+$/, "");
  const iptal = new AbortController();
  const saat = setTimeout(() => iptal.abort(), SAGLAYICI_ZAMAN_ASIMI_MS);
  try {
    const c = await fetch(taban + yol, {
      method: yontem,
      headers: {
        "Authorization": "Bearer " + env.URETIM_API_ANAHTAR,
        "Content-Type": "application/json; charset=utf-8",
      },
      body: govde == null ? undefined : JSON.stringify(govde),
      signal: iptal.signal,
    });
    let v = null;
    try { v = await c.json(); } catch (e) { v = null; }
    return { kod: c.status, govde: v };
  } catch (e) {
    console.error("foto saglayici ulasilamadi: " + yontem + " " + yol.split("/").slice(0, 4).join("/"));
    return { kod: 0, govde: null };
  } finally {
    clearTimeout(saat);
  }
}

function turYolu(env, tur) {
  return "/" + String(env.URETIM_TUR_ONEK || "").replace(/^\/+|\/+$/g, "") + "/" + TUR_YOLU[tur];
}

function gorevKimligi(g) {
  const id = g && typeof g.result === "string" ? g.result : "";
  return /^[A-Za-z0-9-]{8,80}$/.test(id) ? id : "";
}

/** Gorev durumu: 'bitti' | 'surdu' | 'dustu' (FAILED/CANCELED) | 'bilinmiyor'. */
function gorevDurumu(g) {
  const s = g && g.status;
  if (s === "SUCCEEDED") { return "bitti"; }
  if (s === "PENDING" || s === "IN_PROGRESS") { return "surdu"; }
  if (s === "FAILED" || s === "CANCELED") { return "dustu"; }
  return "bilinmiyor";
}

function krediSayisi(g) {
  const n = g && g.consumed_credits;
  return Number.isInteger(n) && n >= 0 ? n : 0;
}

/** Saglayicidaki dosyayi indirir (imzali, sureli adres). Boyut tavanli; hata -> null. */
async function dosyaIndir(adres) {
  if (typeof adres !== "string" || !/^https:\/\//.test(adres)) { return null; }
  try {
    const c = await fetch(adres);
    if (c.status !== 200) { return null; }
    const boy = parseInt(c.headers.get("content-length") || "0", 10);
    if (boy > DOSYA_EN_COK_BAYT) { return null; }
    const tampon = await c.arrayBuffer();
    if (!tampon.byteLength || tampon.byteLength > DOSYA_EN_COK_BAYT) { return null; }
    return { tampon, tip: c.headers.get("content-type") || "application/octet-stream" };
  } catch (e) {
    return null;
  }
}

// ---------------------------------------------------------------- kredi defteri + havuz

async function krediYaz(env, simdi, adim, isNo, siparisNo, gorev, kredi) {
  // UNIQUE(gorev, adim) -> ayni gorev iki kez sayilmaz (yoklama tekrarinda cift kayit yok).
  await env.KATALOG.prepare(
    "INSERT OR IGNORE INTO foto_kredi (tarih, adim, is_no, siparis_no, gorev, kredi)" +
    " VALUES (?, ?, ?, ?, ?, ?)"
  ).bind(simdiIso(simdi), adim, isNo, siparisNo || "", gorev, kredi).run();
}

async function ayarOku(env, anahtar) {
  try {
    return await env.KATALOG.prepare(
      "SELECT deger, guncel FROM foto_ayar WHERE anahtar = ?").bind(anahtar).first();
  } catch (e) {
    if (tabloYok(e)) { return null; }
    throw e;
  }
}

async function ayarYaz(env, anahtar, deger, simdi) {
  await env.KATALOG.prepare(
    "INSERT INTO foto_ayar (anahtar, deger, guncel) VALUES (?, ?, ?)" +
    " ON CONFLICT(anahtar) DO UPDATE SET deger = excluded.deger, guncel = excluded.guncel"
  ).bind(anahtar, String(deger), simdi).run();
}

/** Bakiye (kredi): onbellek taze ise oradan; degilse saglayicidan. Okunamazsa null. */
export async function bakiyeOku(env, simdi, zorla) {
  const kayit = await ayarOku(env, "bakiye");
  if (!zorla && kayit && (simdi - kayit.guncel) < BAKIYE_TAZELIK_MS) {
    const n = parseInt(kayit.deger, 10);
    return Number.isFinite(n) ? n : null;
  }
  const c = await saglayici(env, "GET", "/v1/balance", null);
  const n = c.kod === 200 && c.govde && Number.isFinite(c.govde.balance) ? c.govde.balance : null;
  if (n == null) { return null; }
  await ayarYaz(env, "bakiye", n, simdi);
  return n;
}

/** Odenmis ama modeli henuz kurulmamis uretim sayisi (havuzdan ayrilacak pay). */
async function bekleyenUretim(env) {
  try {
    const r = await env.KATALOG.prepare(
      "SELECT COUNT(*) AS n FROM foto_uretim WHERE asama IN ('build-baslat', 'build')").first();
    return (r && r.n) || 0;
  } catch (e) {
    if (tabloYok(e)) { return 0; }
    throw e;
  }
}

/**
 * Havuz hukmu: {acik, bakiye}. Bakiye OKUNAMAZSA kapali (fail-closed: harcama yolu).
 * Acik -> kapali gecisinde Okan'a TEK bildirim (durum foto_ayar'da tutulur).
 */
export async function havuzHukmu(env, simdi, telegram) {
  const bakiye = await bakiyeOku(env, simdi, false);
  const gereken = HAVUZ_ESIK_KREDI + URETIM_PAYI_KREDI * (await bekleyenUretim(env));
  const acik = bakiye != null && bakiye >= gereken;
  const once = await ayarOku(env, "havuz_durum");
  const yeni = acik ? "acik" : "kapali";
  if (!once || once.deger !== yeni) {
    await ayarYaz(env, "havuz_durum", yeni, simdi);
    if (!acik && typeof telegram === "function") {
      await telegram(env, "📸 Fotoğraftan üretim bölümü KAPANDI — kredi havuzu eşikte" +
        " (bakiye: " + (bakiye == null ? "okunamadı" : bakiye) + ", gereken: " + gereken + ")." +
        " Otomatik kredi alımı YOK; ek kredi alınınca bölüm kendiliğinden açılır.");
    }
  }
  return { acik, bakiye, gereken };
}

// ---------------------------------------------------------------- uc: /foto/acik

async function acikUcu(env, simdi, telegram) {
  const y = yapilandirma(env);
  const sinir = VERI.sinir_ziyaretci_24s;
  const taban = { onay_surum: VERI.onay_surum, sinir: sinir, gecerlilik_saat: VERI.gecerlilik_saat };
  if (!y.hazir) { return fjson({ acik: false, turler: [], ...taban }, 200); }
  const turler = acikTurler(await fiyatTablosu(env));
  if (!turler.length) { return fjson({ acik: false, turler: [], ...taban }, 200); }
  const havuz = await havuzHukmu(env, simdi, telegram);
  if (!havuz.acik) { return fjson({ acik: false, turler: [], ...taban }, 200); }
  return fjson({ acik: true, turler, ...taban }, 200);
}

// ---------------------------------------------------------------- uc: /foto/onizleme

/** data URI dogrulamasi: tur + base64 + boyut + sihirli bayt. Gecerliyse {uri, bayt}. */
export function gorselCoz(ham) {
  if (typeof ham !== "string" || ham.length > Math.ceil(GORSEL_EN_COK_BAYT * 4 / 3) + 64) {
    return null;
  }
  const m = /^data:image\/(jpeg|png|webp);base64,([A-Za-z0-9+/]+={0,2})$/.exec(ham);
  if (!m) { return null; }
  const b64 = m[2];
  const dolgu = b64.endsWith("==") ? 2 : (b64.endsWith("=") ? 1 : 0);
  const bayt = Math.floor(b64.length * 3 / 4) - dolgu;
  if (bayt < GORSEL_EN_AZ_BAYT || bayt > GORSEL_EN_COK_BAYT) { return null; }
  let bas;
  try { bas = atob(b64.slice(0, 24)); } catch (e) { return null; }
  const k = (i) => bas.charCodeAt(i);
  const jpeg = k(0) === 0xFF && k(1) === 0xD8 && k(2) === 0xFF;
  const png = k(0) === 0x89 && bas.slice(1, 4) === "PNG";
  const webp = bas.slice(0, 4) === "RIFF" && bas.slice(8, 12) === "WEBP";
  const beklenen = { jpeg: jpeg, png: png, webp: webp }[m[1]];
  if (!beklenen) { return null; }
  return { uri: ham, bayt: bayt };
}

async function hizSiniriAsildi(request, env) {
  // FAIL-CLOSED (kredi harcayan yol): binding yok/bozuk -> asildi say.
  const rl = env && env.FOTO_RATE_LIMIT;
  if (!rl || typeof rl.limit !== "function") {
    console.error("FOTO_RATE_LIMIT binding YOK -> /foto/onizleme KAPALI (fail-closed)");
    return true;
  }
  const ip = request.headers.get("CF-Connecting-IP") || "yok";
  try {
    const s = await rl.limit({ key: ip });
    return !(s && s.success);
  } catch (e) {
    return true;
  }
}

/**
 * Bot dogrulamasi — /baslat'takinin AKSINE her belirsizlikte RED (fail-closed): bu yol
 * kredi harcar; dogrulayici dusunce onizleme durur, satis yolu (/baslat) etkilenmez.
 */
async function botDogrula(request, env, jeton) {
  if (!env.TURNSTILE_SECRET || typeof jeton !== "string" || !jeton.trim()) { return false; }
  const form = new URLSearchParams();
  form.set("secret", env.TURNSTILE_SECRET);
  form.set("response", jeton);
  const ip = request.headers.get("CF-Connecting-IP") || "";
  if (ip) { form.set("remoteip", ip); }
  const iptal = new AbortController();
  const saat = setTimeout(() => iptal.abort(), 5000);
  try {
    const c = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify",
      { method: "POST", body: form, signal: iptal.signal });
    const s = await c.json();
    return !!(s && s.success === true &&
              ["pruvo3d.com", "www.pruvo3d.com"].includes(String(s.hostname || "")));
  } catch (e) {
    return false;
  } finally {
    clearTimeout(saat);
  }
}

async function onizlemeSayisi(env, ziyaretci, simdi) {
  const esik = saatOnce(simdi, 24);
  const k = await env.KATALOG.prepare(
    "SELECT COUNT(*) AS n FROM foto_isler WHERE ziyaretci = ? AND tarih >= ?"
  ).bind(ziyaretci, esik).first();
  const g = await env.KATALOG.prepare(
    "SELECT COUNT(*) AS n FROM foto_isler WHERE tarih >= ?").bind(esik).first();
  return { kisi: (k && k.n) || 0, genel: (g && g.n) || 0 };
}

async function onizlemeUcu(request, env, simdi, telegram) {
  const y = yapilandirma(env);
  if (!y.hazir) { return fjson({ hata: "kapali" }, 503); }
  let g;
  try { g = await request.json(); } catch (e) { return fjson({ hata: "gecersiz-istek" }, 400); }
  if (!g || typeof g !== "object") { return fjson({ hata: "gecersiz-istek" }, 400); }

  const fiyatlar = await fiyatTablosu(env);
  const tur = acikTurler(fiyatlar).find((t) => t.kod === g.tur);
  if (!tur) { return fjson({ hata: "tur-kapali" }, 400); }
  const olcu = Number.isInteger(g.olcu_mm) ? g.olcu_mm : null;
  if (!tur.olculer.some((o) => o.mm === olcu)) { return fjson({ hata: "gecersiz-olcu" }, 400); }
  // ONAY: iki kutu da true olmali ve musterinin gordugu metin GUNCEL surum olmali.
  if (g.hak_onay !== true || g.aktarim_onay !== true) { return fjson({ hata: "onay-yok" }, 400); }
  if (g.onay_surum !== VERI.onay_surum) { return fjson({ hata: "onay-surumu-eski" }, 409); }
  const gorsel = gorselCoz(g.gorsel);
  if (!gorsel) { return fjson({ hata: "gorsel-gecersiz" }, 400); }

  if (await hizSiniriAsildi(request, env)) { return fjson({ hata: "cok-istek" }, 429); }
  const ip = request.headers.get("CF-Connecting-IP") || "yok";
  const ziyaretci = await ziyaretciOzeti(env, ip);
  const sayi = await onizlemeSayisi(env, ziyaretci, simdi);
  if (sayi.kisi >= VERI.sinir_ziyaretci_24s) {
    return fjson({ hata: "onizleme-siniri", sinir: VERI.sinir_ziyaretci_24s }, 429);
  }
  if (sayi.genel >= GUNLUK_ONIZLEME_TAVANI) { return fjson({ hata: "kapali" }, 503); }
  if (!(await botDogrula(request, env, g.turnstile_token))) {
    return fjson({ hata: "bot-dogrulama" }, 403);
  }
  const havuz = await havuzHukmu(env, simdi, telegram);
  if (!havuz.acik) { return fjson({ hata: "kapali" }, 503); }

  // Is satiri SAGLAYICIDAN ONCE yazilir: reddedilen deneme de ziyaretci sinirindan duser
  // (sinir "basarili onizleme" degil "deneme" sayar -> kaba kuvvetle kredi yakilamaz).
  const isNo = yeniIsNo();
  await env.KATALOG.prepare(
    "INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama) VALUES (?, ?, ?, ?, ?, 'onizleme')"
  ).bind(isNo, tur.kod, olcu, ziyaretci, simdiIso(simdi)).run();

  const c = await saglayici(env, "POST", turYolu(env, tur.kod) + "/v1/prototype", {
    image_url: gorsel.uri,
    name: "pruvo-" + isNo.slice(0, 12),
    // Arka plan kaldirilir: kabartma urun de arka plani atar; onizleme urune benzesin.
    remove_background: true,
  });
  const gorev = gorevKimligi(c.govde);
  if (c.kod < 200 || c.kod >= 300 || !gorev) {
    const sebep = c.kod === 400 ? "gorsel-uygun-degil" : (c.kod === 402 ? "kredi" : "saglayici");
    await env.KATALOG.prepare(
      "UPDATE foto_isler SET asama = 'basarisiz', hata = ? WHERE is_no = ?").bind(sebep, isNo).run();
    if (c.kod === 402 && typeof telegram === "function") {
      await telegram(env, "📸 Fotoğraftan üretim: önizleme kredisi YETMEDİ (sağlayıcı 402). Bölüm kredi gelene dek önizleme üretemez.");
    }
    return fjson({ hata: sebep === "gorsel-uygun-degil" ? "gorsel-uygun-degil" : "gecici-hata" },
                 sebep === "gorsel-uygun-degil" ? 422 : 503);
  }
  await env.KATALOG.prepare("UPDATE foto_isler SET gorev = ? WHERE is_no = ?").bind(gorev, isNo).run();
  return fjson({ is: isNo, kalan: Math.max(0, VERI.sinir_ziyaretci_24s - sayi.kisi - 1) }, 200);
}

// ---------------------------------------------------------------- uc: /foto/durum + /foto/gorsel

function onizlemeAnahtari(isNo) { return "foto-onizleme/" + isNo + ".png"; }

async function isGetir(env, isNo) {
  return env.KATALOG.prepare(
    "SELECT is_no, tur, olcu_mm, tarih, asama, gorev, hazir_tarih, son_kontrol, hata" +
    " FROM foto_isler WHERE is_no = ?").bind(isNo).first();
}

function durumYaniti(is) {
  if (is.asama === "hazir") {
    return fjson({ asama: "hazir", tur: is.tur, olcu_mm: is.olcu_mm,
                   gorsel: "/api/shop/foto/gorsel?is=" + is.is_no,
                   gecerlilik_bitis: new Date(Date.parse(is.hazir_tarih) +
                     VERI.gecerlilik_saat * 3600 * 1000).toISOString() }, 200);
  }
  if (is.asama === "basarisiz") {
    return fjson({ asama: "basarisiz",
                   hata: is.hata === "gorsel-uygun-degil" ? "gorsel-uygun-degil" : "uretilemedi" }, 200);
  }
  if (is.asama === "silindi") { return fjson({ asama: "suresi-doldu" }, 200); }
  return fjson({ asama: "onizleme" }, 200);
}

async function durumUcu(env, url, simdi) {
  const isNo = url.searchParams.get("is") || "";
  if (!IS_KALIBI.test(isNo)) { return fjson({ hata: "bulunamadi" }, 404); }
  let is;
  try { is = await isGetir(env, isNo); } catch (e) {
    if (tabloYok(e)) { return fjson({ hata: "bulunamadi" }, 404); }
    throw e;
  }
  if (!is) { return fjson({ hata: "bulunamadi" }, 404); }
  if (is.asama !== "onizleme" || !is.gorev) { return durumYaniti(is); }
  if (simdi - (is.son_kontrol || 0) < DURUM_ARALIK_MS) { return durumYaniti(is); }
  if (!yapilandirma(env).hazir) { return durumYaniti(is); }

  // CAS: ayni anda iki yoklama saglayiciya iki kez gitmesin.
  const kilit = await env.KATALOG.prepare(
    "UPDATE foto_isler SET son_kontrol = ? WHERE is_no = ? AND son_kontrol = ? AND asama = 'onizleme'"
  ).bind(simdi, isNo, is.son_kontrol || 0).run();
  if (!kilit || !kilit.meta || kilit.meta.changes !== 1) { return durumYaniti(is); }

  const c = await saglayici(env, "GET", turYolu(env, is.tur) + "/v1/prototype/" + is.gorev, null);
  if (c.kod !== 200 || !c.govde) { return durumYaniti(is); }
  const d = gorevDurumu(c.govde);
  if (d === "dustu") {
    await env.KATALOG.prepare(
      "UPDATE foto_isler SET asama = 'basarisiz', hata = 'uretilemedi' WHERE is_no = ? AND asama = 'onizleme'"
    ).bind(isNo).run();
    return fjson({ asama: "basarisiz", hata: "uretilemedi" }, 200);
  }
  if (d !== "bitti") {
    const p = c.govde.progress;
    return fjson({ asama: "onizleme", ilerleme: Number.isInteger(p) ? p : null }, 200);
  }
  const adres = Array.isArray(c.govde.image_urls) ? c.govde.image_urls[0] : "";
  const dosya = await dosyaIndir(adres);
  if (!dosya) { return fjson({ asama: "onizleme" }, 200); }   // sonraki yoklama yeniden dener
  await env.OZEL_DOSYA.put(onizlemeAnahtari(isNo), dosya.tampon,
    { httpMetadata: { contentType: /png|jpeg|webp/.test(dosya.tip) ? dosya.tip : "image/png" } });
  const kredi = krediSayisi(c.govde);
  await env.KATALOG.prepare(
    "UPDATE foto_isler SET asama = 'hazir', hazir_tarih = ?, kredi = ? WHERE is_no = ? AND asama = 'onizleme'"
  ).bind(simdiIso(simdi), kredi, isNo).run();
  await krediYaz(env, simdi, "onizleme", isNo, "", is.gorev, kredi);
  return durumYaniti({ ...is, asama: "hazir", hazir_tarih: simdiIso(simdi) });
}

async function gorselUcu(env, url) {
  const isNo = url.searchParams.get("is") || "";
  if (!IS_KALIBI.test(isNo) || !env.OZEL_DOSYA) { return fjson({ hata: "bulunamadi" }, 404); }
  const n = await env.OZEL_DOSYA.get(onizlemeAnahtari(isNo));
  if (!n) { return fjson({ hata: "bulunamadi" }, 404); }
  return new Response(n.body, {
    status: 200,
    headers: {
      "Content-Type": (n.httpMetadata && n.httpMetadata.contentType) || "image/png",
      "Cache-Control": "private, max-age=600",
      "X-Robots-Tag": "noindex",
    },
  });
}

/** /api/shop/foto/* yonlendiricisi. */
export async function fotoUclari(request, env, url, yol, telegram) {
  const simdi = Date.now();
  const m = request.method;
  if (yol === "/foto/acik" && m === "GET") { return acikUcu(env, simdi, telegram); }
  if (yol === "/foto/onizleme" && m === "POST") { return onizlemeUcu(request, env, simdi, telegram); }
  if (yol === "/foto/durum" && m === "GET") { return durumUcu(env, url, simdi); }
  if (yol === "/foto/gorsel" && m === "GET") { return gorselUcu(env, url); }
  return fjson({ hata: "bulunamadi" }, 404);
}

// ---------------------------------------------------------------- /baslat kalemi

/** Sepet kalemi bicimi: {foto_is, olcu_mm, adet}. Gecersizse {hata}. */
export function fotoKalemCoz(k) {
  const isNo = typeof k.foto_is === "string" && IS_KALIBI.test(k.foto_is) ? k.foto_is : null;
  if (!isNo) { return { hata: "gecersiz-kalem" }; }
  const olcu = Number.isInteger(k.olcu_mm) ? k.olcu_mm : null;
  if (!olcu) { return { hata: "gecersiz-olcu" }; }
  const adet = Number.isInteger(k.adet) && k.adet >= 1 && k.adet <= FOTO_ADET_EN_COK ? k.adet : null;
  if (!adet) { return { hata: "gecersiz-adet" }; }
  return { kalem: { foto_is: isNo, olcu_mm: olcu, adet } };
}

/**
 * FOTO KALEMINI FIYATLA — sunucu hesabi (istemcinin hicbir tutari okunmaz). Sartlar:
 * yapilandirma hazir · onizleme 'hazir' ve gecerlilik suresi icinde · tur acik · olcu fiyat
 * tablosunda. Donus {satir} ya da {hata:{...}, kod}.
 */
export async function fotoKalemFiyatla(env, k, simdi) {
  if (!yapilandirma(env).hazir) {
    return { hata: { hata: "foto-kapali", mesaj: "Fotoğraftan üretim şu an alınamıyor." }, kod: 400 };
  }
  let is;
  try { is = await isGetir(env, k.foto_is); } catch (e) {
    if (tabloYok(e)) { return { hata: { hata: "foto-kapali" }, kod: 400 }; }
    throw e;
  }
  if (!is || is.asama !== "hazir") { return { hata: { hata: "foto-onizleme-yok" }, kod: 400 }; }
  const yas = (simdi - Date.parse(is.hazir_tarih)) / 3600000;
  if (!(yas >= 0 && yas <= VERI.gecerlilik_saat)) {
    return { hata: { hata: "foto-onizleme-suresi-doldu",
                     mesaj: "Önizlemenin süresi doldu; yeni önizleme gerekiyor." }, kod: 400 };
  }
  const tur = acikTurler(await fiyatTablosu(env)).find((t) => t.kod === is.tur);
  if (!tur) { return { hata: { hata: "foto-kapali" }, kod: 400 }; }
  const olcu = tur.olculer.find((o) => o.mm === k.olcu_mm);
  if (!olcu || !(olcu.fiyat_kurus > 0)) { return { hata: { hata: "gecersiz-olcu" }, kod: 400 }; }
  const birim = olcu.fiyat_kurus;
  return {
    satir: {
      // id kalici urun sayfasi DEGIL (katalog disi kalem); id kalibi /^[a-z0-9-]+$/ korunur.
      id: "ozel-foto-" + tur.kod,
      baslik: "Fotoğrafından özel üretim — " + tur.ad + " (" + olcu.mm + " mm)",
      kategori: "Özel Üretim",
      gorsel: "",
      malzeme: "PLA",
      renk: "4 renk",
      renk_ozel: "",
      adet: k.adet,
      birim_kurus: birim,
      tutar_kurus: birim * k.adet,
      parametre_detay: olcu.mm + " mm · önizlemenin 4 renkli yorumu",
      foto_is: is.is_no,
      foto_tur: tur.kod,
      olcu_mm: olcu.mm,
    },
  };
}

// ---------------------------------------------------------------- cron: uretim zinciri

/** Uretim dosyalarinin R2 anahtari (ozel kova). */
export function uretimAnahtari(siparisNo, kalem, bicim) {
  return "foto/" + siparisNo + "/" + kalem + "/model." + bicim;
}

/** Siparis satirindaki (urunler JSON) foto kalemleri: [{kalem, is_no, tur, olcu_mm}]. */
export function siparistekiFotoKalemleri(urunlerJson) {
  let s = [];
  try { s = JSON.parse(urunlerJson) || []; } catch (e) { s = []; }
  const cikti = [];
  s.forEach((k, i) => {
    if (k && typeof k.foto_is === "string" && IS_KALIBI.test(k.foto_is) &&
        Object.prototype.hasOwnProperty.call(TUR_YOLU, k.foto_tur) && Number.isInteger(k.olcu_mm)) {
      cikti.push({ kalem: i, is_no: k.foto_is, tur: k.foto_tur, olcu_mm: k.olcu_mm });
    }
  });
  return cikti;
}

/** Odenmis siparislerdeki foto kalemlerini uretim kuyruguna alir (INSERT OR IGNORE). */
async function odenenleriKuyrugaAl(env, simdi) {
  const r = await env.KATALOG.prepare(
    "SELECT siparis_no, urunler FROM siparisler WHERE durum IN ('odendi', 'uretimde')" +
    " AND tarih >= ? AND urunler LIKE '%\"foto_is\"%' ORDER BY id DESC LIMIT 50"
  ).bind(saatOnce(simdi, 24 * 7)).all();
  let eklenen = 0;
  for (const s of (r.results || [])) {
    for (const k of siparistekiFotoKalemleri(s.urunler)) {
      const y = await env.KATALOG.prepare(
        "INSERT OR IGNORE INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)" +
        " VALUES (?, ?, ?, ?, ?, 'build-baslat', ?, ?)"
      ).bind(s.siparis_no, k.kalem, k.is_no, k.tur, k.olcu_mm, simdiIso(simdi), simdiIso(simdi)).run();
      if (y && y.meta && y.meta.changes) { eklenen++; }
    }
  }
  return eklenen;
}

/** Satiri bir sonraki asamaya CAS ile tasir (yalniz beklenen asamadaysa). */
async function asamaYaz(env, u, yeni, alanlar, simdi) {
  const ad = Object.keys(alanlar || {});
  const set = ["asama = ?", "guncel = ?", "deneme = 0"].concat(ad.map((a) => a + " = ?")).join(", ");
  const r = await env.KATALOG.prepare(
    "UPDATE foto_uretim SET " + set + " WHERE siparis_no = ? AND kalem = ? AND asama = ?"
  ).bind(yeni, simdiIso(simdi), ...ad.map((a) => alanlar[a]), u.siparis_no, u.kalem, u.asama).run();
  return !!(r && r.meta && r.meta.changes === 1);
}

const ELLE_METNI = {
  "onizleme-yok": "önizleme kaydı bulunamadı",
  "onizleme-suresi-doldu": "önizleme 3 günlük saklama sınırını geçti",
  "model-reddedildi": "model adımı isteği reddetti",
  "model-basarisiz": "model üretilemedi",
  "analiz-kirmizi": "basılabilirlik analizi KIRMIZI (renk adımı koşmadı)",
  "analiz-basarisiz": "basılabilirlik analizi tamamlanamadı",
  "renk-basarisiz": "4 renk ayrımı üretilemedi",
  "indirme-basarisiz": "dosyalar depoya indirilemedi",
  "kredi-yetersiz": "kredi yetmedi (otomatik alım yok)",
  "saglayici-erisilemiyor": "sağlayıcıya tekrar tekrar ulaşılamadı",
};

async function elleDusur(env, u, sebep, ek, simdi, telegram) {
  const tasindi = await asamaYaz(env, u, "elle", { sebep: sebep, analiz: ek || u.analiz || "" }, simdi);
  if (tasindi && typeof telegram === "function") {
    await telegram(env, "📸 Fotoğraftan üretim — ELLE BAKILACAK: " + u.siparis_no + " kalem " + u.kalem +
      " (" + u.tur + ", " + u.olcu_mm + " mm): " + (ELLE_METNI[sebep] || sebep));
  }
  return tasindi;
}

/** Gecici hata: deneme sayaci artar; tavanda 'elle'. */
async function gecici(env, u, simdi, telegram) {
  if ((u.deneme || 0) + 1 >= URETIM_DENEME_TAVANI) {
    return elleDusur(env, u, "saglayici-erisilemiyor", "", simdi, telegram);
  }
  await env.KATALOG.prepare(
    "UPDATE foto_uretim SET deneme = deneme + 1, guncel = ? WHERE siparis_no = ? AND kalem = ? AND asama = ?"
  ).bind(simdiIso(simdi), u.siparis_no, u.kalem, u.asama).run();
  return false;
}

function hataKolu(kod) {
  if (kod === 402) { return "kredi"; }
  if (kod === 400 || kod === 404 || kod === 403) { return "red"; }
  return "gecici";   // 0 (ag), 429, 5xx
}

async function modelGorevi(env, u) {
  return saglayici(env, "GET", turYolu(env, u.tur) + "/v1/build/" + u.build_gorev, null);
}

/** Tek uretim satirini BIR adim ilerletir. */
async function uretimAdimi(env, u, simdi, telegram) {
  if (u.asama === "build-baslat") {
    const is = await isGetir(env, u.is_no);
    if (!is || is.asama !== "hazir" || !is.gorev) { return elleDusur(env, u, "onizleme-yok", "", simdi, telegram); }
    if ((simdi - Date.parse(is.hazir_tarih)) / 3600000 > ONIZLEME_KURULUM_SINIRI_SAAT) {
      return elleDusur(env, u, "onizleme-suresi-doldu", "", simdi, telegram);
    }
    const c = await saglayici(env, "POST", turYolu(env, u.tur) + "/v1/build", {
      input_task_id: is.gorev,
      name: "pruvo-" + u.siparis_no,
      options: { size_mm: u.olcu_mm },
    });
    const gorev = gorevKimligi(c.govde);
    if (c.kod >= 200 && c.kod < 300 && gorev) {
      return asamaYaz(env, u, "build", { build_gorev: gorev }, simdi);
    }
    const kol = hataKolu(c.kod);
    if (kol === "kredi") { return elleDusur(env, u, "kredi-yetersiz", "", simdi, telegram); }
    if (kol === "red") { return elleDusur(env, u, "model-reddedildi", "", simdi, telegram); }
    return gecici(env, u, simdi, telegram);
  }

  if (u.asama === "build") {
    const c = await modelGorevi(env, u);
    if (c.kod !== 200 || !c.govde) { return gecici(env, u, simdi, telegram); }
    const d = gorevDurumu(c.govde);
    if (d === "surdu") { return false; }
    if (d !== "bitti") { return elleDusur(env, u, "model-basarisiz", "", simdi, telegram); }
    await krediYaz(env, simdi, "build", u.is_no, u.siparis_no, u.build_gorev, krediSayisi(c.govde));
    const glb = c.govde.model_urls && c.govde.model_urls.glb;
    const a = await saglayici(env, "POST", "/v1/print/analyze", { model_url: glb });
    const ag = gorevKimligi(a.govde);
    if (a.kod >= 200 && a.kod < 300 && ag) { return asamaYaz(env, u, "analiz", { analiz_gorev: ag }, simdi); }
    // Analiz baslatilamadiysa satir 'build'de KALIR (bir sonraki tur yeniden dener).
    return hataKolu(a.kod) === "gecici" ? gecici(env, u, simdi, telegram)
      : elleDusur(env, u, "analiz-basarisiz", "", simdi, telegram);
  }

  if (u.asama === "analiz") {
    const c = await saglayici(env, "GET", "/v1/print/analyze/" + u.analiz_gorev, null);
    if (c.kod !== 200 || !c.govde) { return gecici(env, u, simdi, telegram); }
    const d = gorevDurumu(c.govde);
    if (d === "surdu") { return false; }
    if (d !== "bitti") { return elleDusur(env, u, "analiz-basarisiz", "", simdi, telegram); }
    await krediYaz(env, simdi, "analiz", u.is_no, u.siparis_no, u.analiz_gorev, krediSayisi(c.govde));
    const p = c.govde.printability || {};
    const ozet = JSON.stringify({ durum: p.status || "unknown", hata: p.error_count || 0,
                                  uyari: p.warning_count || 0, olcum: p.metrics || {} }).slice(0, 600);
    // KIRMIZI = 'error' ya da durum hic gelmedi: renk adimi KOSMAZ (sessiz gecis yok).
    if (p.status !== "healthy" && p.status !== "warning") {
      return elleDusur(env, u, "analiz-kirmizi", ozet, simdi, telegram);
    }
    const m = await modelGorevi(env, u);
    const glb = m.kod === 200 && m.govde && m.govde.model_urls && m.govde.model_urls.glb;
    if (!glb) { return gecici(env, u, simdi, telegram); }
    const r = await saglayici(env, "POST", "/v1/print/multi-color",
                              { model_url: glb, max_colors: 4, printer_brand: "bambu" });
    const rg = gorevKimligi(r.govde);
    if (r.kod >= 200 && r.kod < 300 && rg) {
      return asamaYaz(env, u, "renk", { renk_gorev: rg, analiz: ozet }, simdi);
    }
    const kol = hataKolu(r.kod);
    if (kol === "kredi") { return elleDusur(env, u, "kredi-yetersiz", ozet, simdi, telegram); }
    if (kol === "red") { return elleDusur(env, u, "renk-basarisiz", ozet, simdi, telegram); }
    return gecici(env, u, simdi, telegram);
  }

  if (u.asama === "renk") {
    const c = await saglayici(env, "GET", "/v1/print/multi-color/" + u.renk_gorev, null);
    if (c.kod !== 200 || !c.govde) { return gecici(env, u, simdi, telegram); }
    const d = gorevDurumu(c.govde);
    if (d === "surdu") { return false; }
    if (d !== "bitti") { return elleDusur(env, u, "renk-basarisiz", "", simdi, telegram); }
    await krediYaz(env, simdi, "renk", u.is_no, u.siparis_no, u.renk_gorev, krediSayisi(c.govde));
    const m = await modelGorevi(env, u);
    const glbAdres = m.kod === 200 && m.govde && m.govde.model_urls && m.govde.model_urls.glb;
    const ucmf = await dosyaIndir(c.govde.model_urls && c.govde.model_urls["3mf"]);
    const glb = await dosyaIndir(glbAdres);
    if (!ucmf || !glb) { return gecici(env, u, simdi, telegram); }
    await env.OZEL_DOSYA.put(uretimAnahtari(u.siparis_no, u.kalem, "3mf"), ucmf.tampon,
                             { httpMetadata: { contentType: "model/3mf" } });
    await env.OZEL_DOSYA.put(uretimAnahtari(u.siparis_no, u.kalem, "glb"), glb.tampon,
                             { httpMetadata: { contentType: "model/gltf-binary" } });
    const tasindi = await asamaYaz(env, u, "hazir", {}, simdi);
    if (tasindi && typeof telegram === "function") {
      await telegram(env, "📸 Fotoğraftan üretim — 4 renkli dosya HAZIR: " + u.siparis_no +
        " kalem " + u.kalem + " (" + u.tur + ", " + u.olcu_mm + " mm). Panelde siparişin yanında.");
    }
    return tasindi;
  }
  return false;
}

/** Siparise donusmeyen onizlemeleri siler (onay metni: en gec 3 gun). */
async function onizlemeTemizle(env, simdi) {
  const r = await env.KATALOG.prepare(
    "SELECT is_no FROM foto_isler WHERE asama IN ('hazir', 'onizleme', 'basarisiz') AND tarih < ?" +
    " AND is_no NOT IN (SELECT is_no FROM foto_uretim) LIMIT 50"
  ).bind(saatOnce(simdi, ONIZLEME_SAKLAMA_SAAT)).all();
  let silinen = 0;
  for (const s of (r.results || [])) {
    await env.OZEL_DOSYA.delete(onizlemeAnahtari(s.is_no));
    await env.KATALOG.prepare(
      "UPDATE foto_isler SET asama = 'silindi' WHERE is_no = ?").bind(s.is_no).run();
    silinen++;
  }
  return silinen;
}

/**
 * CRON KOLU — uretim zincirini yurutur. Yapilandirma eksikse HICBIR SEY yapmaz.
 * Donus olcum ozeti (log + test): {kuyruga, ilerleyen, silinen}.
 */
export async function fotoUretimTuru(env, simdi, telegram) {
  const ozet = { kuyruga: 0, ilerleyen: 0, silinen: 0, atlandi: "" };
  if (!env || !env.KATALOG || !env.OZEL_DOSYA || !env.URETIM_API_ANAHTAR || !env.URETIM_API_TABAN ||
      !env.URETIM_TUR_ONEK) {
    ozet.atlandi = "yapilandirma";
    return ozet;
  }
  try {
    ozet.kuyruga = await odenenleriKuyrugaAl(env, simdi);
    const r = await env.KATALOG.prepare(
      "SELECT siparis_no, kalem, is_no, tur, olcu_mm, asama, build_gorev, analiz_gorev, renk_gorev," +
      " analiz, deneme FROM foto_uretim WHERE asama NOT IN ('hazir', 'elle') ORDER BY guncel LIMIT ?"
    ).bind(URETIM_TUR_LIMITI).all();
    for (const u of (r.results || [])) {
      try {
        if (await uretimAdimi(env, u, simdi, telegram)) { ozet.ilerleyen++; }
      } catch (e) {
        console.error("foto uretim adimi dustu " + u.siparis_no + "/" + u.kalem + ": " + ((e && e.message) || e));
      }
    }
    ozet.silinen = await onizlemeTemizle(env, simdi);
  } catch (e) {
    if (tabloYok(e)) { ozet.atlandi = "sema"; return ozet; }
    throw e;
  }
  console.log("FOTO_URETIM kuyruga=" + ozet.kuyruga + " ilerleyen=" + ozet.ilerleyen + " silinen=" + ozet.silinen);
  return ozet;
}

// ---------------------------------------------------------------- panel (yonetim anahtari arkasi)

/** Siparis listesindeki foto kalemleri icin uretim durumu haritasi: "no|kalem" -> kayit. */
export async function panelUretimHaritasi(env, siparisNolari) {
  const harita = new Map();
  if (!siparisNolari.length) { return harita; }
  const yer = siparisNolari.map(() => "?").join(",");
  try {
    const r = await env.KATALOG.prepare(
      "SELECT siparis_no, kalem, is_no, asama, sebep, analiz FROM foto_uretim WHERE siparis_no IN (" + yer + ")"
    ).bind(...siparisNolari).all();
    for (const u of (r.results || [])) { harita.set(u.siparis_no + "|" + u.kalem, u); }
    const k = await env.KATALOG.prepare(
      "SELECT siparis_no, SUM(kredi) AS kredi FROM foto_kredi WHERE siparis_no IN (" + yer + ") GROUP BY siparis_no"
    ).bind(...siparisNolari).all();
    for (const x of (k.results || [])) { harita.set("kredi|" + x.siparis_no, x.kredi || 0); }
  } catch (e) {
    if (!tabloYok(e)) { throw e; }
  }
  return harita;
}

/** Panel kalem kaydi (liste ucu). Uretim satiri YOKSA bunu acikca soyler (sessiz bosluk yok). */
export function panelFotoKaydi(siparisNo, i, k, harita) {
  const u = harita.get(siparisNo + "|" + i);
  const taban = "/api/shop/yonet/foto-dosya?siparis_no=" + encodeURIComponent(siparisNo) + "&kalem=" + i;
  return {
    is_no: k.foto_is,
    tur: k.foto_tur || "",
    olcu_mm: k.olcu_mm || 0,
    asama: u ? u.asama : "kuyrukta-degil",
    sebep: u ? (ELLE_METNI[u.sebep] || u.sebep || "") : "",
    analiz: u ? (u.analiz || "") : "",
    onizleme: taban + "&bicim=onizleme",
    dosyalar: u && u.asama === "hazir" ? { "3mf": taban + "&bicim=3mf", "glb": taban + "&bicim=glb" } : null,
    // Onizleme kredisi is_no'ya, uretim kredileri siparis_no'ya yazilir; panel ikisini toplar.
    kredi_uretim: harita.get("kredi|" + siparisNo) || 0,
  };
}

/** GET /yonet/foto-dosya?siparis_no=&kalem=&bicim=3mf|glb|onizleme */
export async function panelFotoDosya(env, url) {
  const no = url.searchParams.get("siparis_no") || "";
  const kalem = parseInt(url.searchParams.get("kalem") || "", 10);
  const bicim = url.searchParams.get("bicim") || "";
  if (!SIPARIS_KALIBI.test(no) || !Number.isInteger(kalem) || kalem < 0 ||
      !["3mf", "glb", "onizleme"].includes(bicim) || !env.OZEL_DOSYA) {
    return fjson({ hata: "gecersiz" }, 400);
  }
  const s = await env.KATALOG.prepare(
    "SELECT urunler FROM siparisler WHERE siparis_no = ?").bind(no).first();
  const k = s && siparistekiFotoKalemleri(s.urunler).find((x) => x.kalem === kalem);
  if (!k) { return fjson({ hata: "kalem-yok" }, 404); }
  const anahtar = bicim === "onizleme" ? onizlemeAnahtari(k.is_no) : uretimAnahtari(no, kalem, bicim);
  const n = await env.OZEL_DOSYA.get(anahtar);
  if (!n) { return fjson({ hata: "dosya-yok" }, 404); }
  const ad = no + "-" + kalem + "-" + k.tur + "-" + k.olcu_mm + "mm." + (bicim === "onizleme" ? "png" : bicim);
  return new Response(n.body, {
    status: 200,
    headers: {
      "Content-Type": (n.httpMetadata && n.httpMetadata.contentType) || "application/octet-stream",
      "Content-Disposition": (bicim === "onizleme" ? "inline" : "attachment") + "; filename=\"" + ad + "\"",
      "Cache-Control": "no-store",
    },
  });
}

/**
 * GET /yonet/foto-ozet — "hata cok mu" sorusunun SAYISI (8. madde): tur basina siparis
 * kalemi ↔ elle bakilacak; aylik kredi; havuz; fiyat tablosu; yapilandirma eksikleri.
 */
export async function panelFotoOzet(env, simdi) {
  const y = yapilandirma(env);
  const cikti = { yapilandirma: y, turler: [], kredi: { bu_ay: 0, gecen_ay: 0 }, bakiye: null,
                  fiyatlar: [], onay_onayli: VERI.onay_onayli === true, onay_surum: VERI.onay_surum,
                  ornek: VERI.turler.map((t) => ({ tur: t.kod, sayi: VERI.ornekSayisi(t.kod) })),
                  elle: [], sema: true };
  try {
    const t = await env.KATALOG.prepare(
      "SELECT tur, COUNT(*) AS kalem, SUM(asama = 'hazir') AS hazir, SUM(asama = 'elle') AS elle" +
      " FROM foto_uretim GROUP BY tur").all();
    cikti.turler = VERI.turler.map((x) => {
      const s = (t.results || []).find((r) => r.tur === x.kod) || {};
      const kalem = s.kalem || 0, hazir = s.hazir || 0, elle = s.elle || 0;
      return { tur: x.kod, ad: x.ad, kalem, hazir, elle, suruyor: kalem - hazir - elle };
    });
    const d = new Date(simdi);
    const buAy = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1)).toISOString();
    const gecenAy = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - 1, 1)).toISOString();
    const k1 = await env.KATALOG.prepare(
      "SELECT COALESCE(SUM(kredi), 0) AS n FROM foto_kredi WHERE tarih >= ?").bind(buAy).first();
    const k2 = await env.KATALOG.prepare(
      "SELECT COALESCE(SUM(kredi), 0) AS n FROM foto_kredi WHERE tarih >= ? AND tarih < ?"
    ).bind(gecenAy, buAy).first();
    cikti.kredi = { bu_ay: (k1 && k1.n) || 0, gecen_ay: (k2 && k2.n) || 0 };
    const f = await env.KATALOG.prepare(
      "SELECT tur, olcu_mm, fiyat_kurus FROM foto_fiyat ORDER BY tur, olcu_mm").all();
    cikti.fiyatlar = f.results || [];
    const e = await env.KATALOG.prepare(
      "SELECT siparis_no, kalem, tur, sebep, guncel FROM foto_uretim WHERE asama = 'elle'" +
      " ORDER BY guncel DESC LIMIT 20").all();
    cikti.elle = (e.results || []).map((x) => ({ ...x, sebep: ELLE_METNI[x.sebep] || x.sebep }));
    const b = await ayarOku(env, "bakiye");
    cikti.bakiye = b ? { kredi: parseInt(b.deger, 10), guncel: b.guncel } : null;
  } catch (e) {
    if (!tabloYok(e)) { throw e; }
    cikti.sema = false;
  }
  return fjson(cikti, 200);
}

/** POST /yonet/foto-fiyat {tur, olcu_mm, fiyat_kurus}; fiyat 0 -> satir silinir (olcu kapanir). */
export async function panelFotoFiyat(request, env, simdi) {
  let g;
  try { g = await request.json(); } catch (e) { return fjson({ hata: "gecersiz-json" }, 400); }
  const tur = g && typeof g.tur === "string" && Object.prototype.hasOwnProperty.call(TUR_YOLU, g.tur)
    ? g.tur : null;
  const olcu = g && Number.isInteger(g.olcu_mm) && g.olcu_mm >= OLCU_MM_EN_AZ && g.olcu_mm <= OLCU_MM_EN_COK
    ? g.olcu_mm : null;
  const fiyat = g && Number.isInteger(g.fiyat_kurus) && g.fiyat_kurus >= 0 && g.fiyat_kurus <= 10000000
    ? g.fiyat_kurus : null;
  if (!tur) { return fjson({ hata: "gecersiz-tur" }, 400); }
  if (!olcu) { return fjson({ hata: "gecersiz-olcu", en_az: OLCU_MM_EN_AZ, en_cok: OLCU_MM_EN_COK }, 400); }
  if (fiyat == null) { return fjson({ hata: "gecersiz-fiyat" }, 400); }
  if (fiyat === 0) {
    await env.KATALOG.prepare("DELETE FROM foto_fiyat WHERE tur = ? AND olcu_mm = ?").bind(tur, olcu).run();
  } else {
    await env.KATALOG.prepare(
      "INSERT INTO foto_fiyat (tur, olcu_mm, fiyat_kurus, guncel) VALUES (?, ?, ?, ?)" +
      " ON CONFLICT(tur, olcu_mm) DO UPDATE SET fiyat_kurus = excluded.fiyat_kurus, guncel = excluded.guncel"
    ).bind(tur, olcu, fiyat, simdiIso(simdi)).run();
  }
  return fjson({ ok: true, tur, olcu_mm: olcu, fiyat_kurus: fiyat }, 200);
}
