/**
 * pruvo-shop — FOTOGRAFTAN OZEL URETIM (ana sayfa bolumu; Okan karari 5 Eki 2026).
 *
 * AKIS: musteri fotograf yukler -> tur + olcu -> ONIZLEME (odemeden ONCE yalniz bu adim
 * kredi harcar) -> mevcut odeme (/baslat, kart) -> odeme DOGRULANINCA (siparis 'odendi')
 * cron uretim zincirini yurutur: model -> basilabilirlik analizi -> 4 renk ayrimi -> 3MF +
 * GLB bizim ozel R2 kovamiza -> siparis panelinde kalemin yaninda.
 *
 * Uclar (index.js /api/shop/foto/* -> fotoUclari):
 *   GET  /foto/acik            -> bolum durumu: acik mi, siparis alan turler + olcu/fiyat (fiyat FORMULDEN)
 *   POST /foto/onizleme        -> fotograf (data URI) + tur + olcu + onaylar + bot jetonu
 *                                 -> {is}  (is = tahmin edilemez 32 hex onizleme anahtari)
 *   GET  /foto/durum?is=       -> onizleme hazir mi; hazirsa bizim adresimizden gorsel
 *   GET  /foto/gorsel?is=      -> onizleme gorseli (ozel kovadan; yalniz is anahtariyla)
 *   POST /foto/litofan         -> DETERMINISTIK KOL: tarayicinin cizdigi gri kalinlik haritasi
 *                                 (PNG) -> {is}; saglayici cagrisi 0, kredi 0, orijinal foto GELMEZ
 *
 * IKI KOL (tur kaydi `kol`, foto-uretim-veri.js): "saglayici" (plaket) yukaridaki zincir;
 *   "deterministik" (litofan) odenince 'uretec-bekliyor' asamasinda bekler, 3MF'i panelden
 *   bizim uretecimizin ciktisi olarak yuklenir (/yonet/foto/uretec-yukle) -> 'hazir'.
 *
 * 🔴 MARKASIZ / GIZLILIK (BaBa hukmu 5. madde): hizmet saglayicinin ADI ve HOST'U bu dosyada,
 *    sitede ve commit mesajinda GECMEZ. Uc tabani ve tur yolu onegi de anahtar gibi ORTAM
 *    DEGISKENINDEN okunur (URETIM_API_TABAN, URETIM_TUR_ONEK, URETIM_TUR_PLAKET,
 *    URETIM_API_ANAHTAR — hepsi
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
 * ONARIM (6 Eki, ilk gercek ornek sizdirmaz cikmadi): ILK kirmizi analizde satir BIR KEZ
 *    onarima gider: 'onarim' (sizdirmazlik onarimi; dokuyu siler) -> 'doku' (onarilan modele
 *    onizleme gorseliyle yeniden doku; renk adimi dokusuz modeli reddeder) -> 'analiz' YENIDEN.
 *    Onarim sonrasi analiz hala kirmiziysa 'elle' (ikinci onarim YOK, renk KOSMAZ).
 *    Zincir D1 semasi degismeden build_gorev'de tutulur: "<model>" | "<model>~<onarim>" |
 *    "<model>~<onarim>~<doku>"; son ogedeki model renk adimina ve depoya giden modeldir.
 * OLCU KAPISI (6 Eki, onarimli ornekte 3MF 1094 mm geldi): 3MF R2'ye yazilmadan ONCE olculur
 *    ve siparis olcusune duze olceklenir (bkz. ucmfOlcekle); tutmazsa 'elle' olcu-tutmadi.
 */

import "../../foto-uretim-veri.js";
// "../src/" bilerek: mutant bataryalari foto.js'i shop/<gecici>/ altina TEK dosya kopyalar; bu yol
// hem shop/src/ hem kopya dizininden ayni modulu bulur.
import { turnstileHostKabul } from "../src/onizleme.js";

const VERI = globalThis.PRUVO_FOTO;
if (!VERI) { throw new Error("foto-uretim-veri.js yuklenemedi — tur/ornek tek kaynagi yok"); }

// ---------------------------------------------------------------- sabitler (tek yer)

/**
 * SUNULAN TURLER (Okan karari 5 Eki 21:4x: "plaket yapalim" — yalniz plastik uretiyoruz,
 * metal halka/miknatis YOK): bizim tur kodumuz -> saglayicinin urun yolu parcasini tasiyan
 * ORTAM DEGISKENININ ADI. Saglayicinin tur adi/yolu bu dosyada GECMEZ (`wrangler secret put`).
 * Bu tabloda olmayan tur (anahtarlik, magnet ...) HER uclu REDDEDILIR: onizleme
 * `tur-kapali`, odeme kalemi `foto-kapali`, panel acilis `gecersiz-tur`, kuyruk almaz.
 */
export const TUR_ORTAM = { plaket: "URETIM_TUR_PLAKET", figur: "URETIM_TUR_FIGUR" };
/** Build adiminda olcu sinirlari (mm; plaketin en uzun boyutu) — manifest kaydi yoksa yedek aralik. */
export const OLCU_MM_EN_AZ = 60; // Okan 6 Eki: "min 60 max 300" (manifest plaket olcu_mm ile AYNI)
export const OLCU_MM_EN_COK = 300; // Okan 6 Eki: 60–300 mm (saglayici sinir 400)
/**
 * PLAKET GEOMETRISI (herkese AYNI; ayak bu taban kalinligina gore yuvali uretilir — TeKiN).
 * Duz arka (kapali sirt), alt kenari duz sekil: masada ayakla durur. Model uzerinde DELME YOK.
 */
export const PLAKET_KABARTMA_MM = 3.3;
export const PLAKET_TABAN_MM = 3.0;
export const PLAKET_SEKIL = "rounded-rect";
/** Plaket basina ayak adedi — ayak ayri parametrik parca, plaketle AYNI plakada basilir. */
export const AYAK_PLAKET_BASI = 1;

/**
 * DETERMINISTIK KOL turleri — veri dosyasindaki kayittan (`kol === "deterministik"`), elle liste
 * YOK. Bu turlerde saglayici HIC cagrilmaz: onizleme tarayicida cizilir, uretim dosyasi bizim
 * uretecimizden panelden yuklenir.
 */
export const DETERMINISTIK_TURLER = VERI.turler
  .filter((t) => VERI.kolu(t.kod) === "deterministik").map((t) => t.kod);

/** Tur saglayici kolunda mi (yalniz bu turler icin saglayiciya gidilir). */
function saglayiciTuru(kod) {
  // Uyelik MANIFESTTEN (motor M); TUR_ORTAM yalniz ortam degiskeni eslemesi (kategori listesi DEGIL).
  return typeof kod === "string" && VERI.kolu(kod) === "saglayici" &&
    Object.prototype.hasOwnProperty.call(TUR_ORTAM, kod);
}
/** Tur deterministik kolda mi. */
function deterministikTur(kod) { return typeof kod === "string" && DETERMINISTIK_TURLER.includes(kod); }
/**
 * URETEC ONIZLEMELI tur: deterministik kol VE tarayici onizleyicisi YOK (manifest
 * VERI.TARAYICI_ONIZLEYICI). Siparis oncesi onizlemeyi koşucu (Mac) uretir: /foto/onizleme satiri
 * 'uretec-onizleme' ile kuyruga yazar, koşucu 'onizleme-hazir' yapar; siparis YALNIZ ona baglanir.
 */
export function uretecOnizlemeTuru(kod) {
  const t = deterministikTur(kod) ? VERI.turBul(kod) : null;
  const tablo = VERI.TARAYICI_ONIZLEYICI || {};
  return !!t && !(Object.prototype.hasOwnProperty.call(tablo, t.uretec) && tablo[t.uretec] === true);
}
/** Tur kodu bizim sundugumuz bir tur mu (prototip zincirinden gelen ad kirintisina guvenme). */
function turSunuluyor(kod) { return saglayiciTuru(kod) || deterministikTur(kod); }
/** Tur basina olcu araligi (kayittan); plaket kaydi OLCU_MM_EN_AZ/EN_COK ile AYNI. */
function olcuAraligi(kod) {
  return VERI.olcuAraligi(kod) || { en_az: OLCU_MM_EN_AZ, en_cok: OLCU_MM_EN_COK };
}
/**
 * GIRDI DOGRULAMASI (genel, manifestten): `parametreler` turun `form` semasina karsi; `svg` alani
 * yalniz girdisinde "svg" olan turde ve VERI.svgDogrula'dan gecerse. Turun girdisinde YAKINDA
 * (acik:false) bir tip varsa tur bu uctan gecmez. Donus "" = gecerli, aksi hata kodu (400).
 */
export function girdiGovdeDogrula(turKod, g) {
  const t = VERI.turBul(turKod);
  if (!t || !Array.isArray(t.girdi) || !t.girdi.length) { return "girdi-tanimsiz"; }
  for (const x of t.girdi) {
    const gt = Object.prototype.hasOwnProperty.call(VERI.GIRDI_TURLERI, x) ? VERI.GIRDI_TURLERI[x] : null;
    if (!gt) { return "girdi-tanimsiz"; }
    if (gt.acik !== true) { return "girdi-yakinda"; }
  }
  const p = VERI.parametreDogrula(turKod, g.parametreler);
  if (!p.ok) { return p.hata; }
  if (g.svg !== undefined) {
    if (!t.girdi.includes("svg")) { return "sema-disi-parametre"; }
    const sv = VERI.svgDogrula(g.svg);
    if (sv) { return sv; }
  }
  return "";
}

/** Uretim notu ("Nasil olsun?") en cok kac karakter — bolumun sayaci AYNI sayi (foto-uretim.js). */
export const URETIM_NOTU_EN_COK = 300;
// Kontrol + gorunmez yon/sifir genislik karakterleri bosluga cevrilir (operator ekraninda gizli metin olmasin).
const NOT_KONTROL = new RegExp("[\\u0000-\\u001F\\u007F-\\u009F\\u200B-\\u200F\\u2028-\\u202E\\u2060-\\u2069\\uFEFF]", "g");
const NOT_BOSLUK = new RegExp("\\s+", "g");
const NOT_EPOSTA = new RegExp("[^\\s@]+@[^\\s@]+\\.[^\\s@]+");
// 10+ rakam (araya bosluk/tire/nokta/parantez girebilir) = telefon kalibi.
const NOT_TELEFON = new RegExp("(?:\\+?\\d[\\s().-]*){10,}");
/**
 * "Nasil olsun?" uretim notu: yok/bos -> "" · metin degil -> not-gecersiz · temizlenmis hali
 * 300 karakteri asarsa -> not-uzun · e-posta/telefon kalibi -> not-kisisel-veri (not, foto disinda
 * kisisel veri TASIMAZ; 2D acilirsa saglayiciya bu temiz metin gider).
 */
export function uretimNotuDogrula(x) {
  if (x === undefined || x === null) { return { ok: true, deger: "" }; }
  if (typeof x !== "string") { return { ok: false, hata: "not-gecersiz" }; }
  const d = x.replace(NOT_KONTROL, " ").replace(NOT_BOSLUK, " ").trim();
  if (Array.from(d).length > URETIM_NOTU_EN_COK) { return { ok: false, hata: "not-uzun" }; }
  if (NOT_EPOSTA.test(d) || NOT_TELEFON.test(d)) { return { ok: false, hata: "not-kisisel-veri" }; }
  return { ok: true, deger: d };
}

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

/**
 * ORNEK URETIM (panel "Örnek üret"; BaBa 6 Eki): Okan'in KENDI fotografindan odemesiz
 * onizleme + uretim — vitrin ornegi (`ornekler`) cikarmak icin. Is satiri SEMA DEGISMEDEN
 * isaretlenir: `foto_isler.ziyaretci = ORNEK_ZIYARETCI`. Musteri ziyaretci ozeti 16 hex'tir,
 * bu sabit hex DEGILDIR -> carpisma yok. Ayrimlar (her biri shop/test/foto-uretim.mjs O):
 *   - ornek isi musteri sepetinde/odemede RED (fotoKalemFiyatla)
 *   - musteri /foto/durum + /foto/gorsel ornek isini GOSTERMEZ (404)
 *   - ziyaretci siniri / gunluk tavan ornek islerini SAYMAZ
 *   - uretim satiri siparissizdir: siparis_no = ORNEK_SIPARIS_ONEK + is ilk 12
 */
export const ORNEK_ZIYARETCI = "ornek";
export const ORNEK_SIPARIS_ONEK = "ORNEK-";
/** Ornek kolunda ATLANAN sartlar (Okan kendi fotografi): bot, onay metni, gercek-ornek kapisi. */
const ORNEK_ATLANAN = ["bot-dogrulama", "onay-metni-onayi", "gercek-ornek"];

function ornekMi(is) { return !!is && is.ziyaretci === ORNEK_ZIYARETCI; }

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
/** Saglayici kolunda en az bir turun yolu (ortam degiskeni) dolu mu. */
function saglayiciYoluVar(env) {
  return !!env && Object.keys(TUR_ORTAM).some((k) => !!env[TUR_ORTAM[k]]);
}
/** Bu saglayici turunun yolu dolu mu (giris uclari: yoksa 503 kapali, saglayiciya istek 0). */
function turYoluVar(env, kod) {
  return !!env && Object.prototype.hasOwnProperty.call(TUR_ORTAM, kod) && !!env[TUR_ORTAM[kod]];
}

export function yapilandirma(env) {
  const eksik = [];
  if (!env || !env.URETIM_API_TABAN) { eksik.push("uc-tabani"); }
  if (!env || !env.URETIM_TUR_ONEK) { eksik.push("tur-oneki"); }
  // Global sart: EN AZ BIR saglayici tur yolu. Tek turun yolu eksikse yalniz O tur kapanir
  // (turHazir); "hepsi" sarti yeni bir tur eklenip sirri henuz konmadiginda plaketi de kapatirdi.
  if (!saglayiciYoluVar(env)) {
    for (const kod of Object.keys(TUR_ORTAM)) { eksik.push("tur-yolu-" + kod); }
  }
  if (!env || !env.URETIM_API_ANAHTAR) { eksik.push("api-anahtari"); }
  if (!env || !env.TURNSTILE_SECRET) { eksik.push("bot-dogrulama"); }
  if (!env || !env.OZEL_DOSYA) { eksik.push("ozel-kova"); }
  if (!env || !env.KATALOG) { eksik.push("veritabani"); }
  if (VERI.onay_onayli !== true) { eksik.push("onay-metni-onayi"); }
  if (!VERI.turler.some((t) => VERI.ornekSayisi(t.kod) > 0)) { eksik.push("gercek-ornek"); }
  return { hazir: eksik.length === 0, eksik };
}

/**
 * Tek turun hazirligi: ortak sartlar (bot dogrulama, ozel kova, veritabani, onay, o turun gercek
 * ornegi) + YALNIZ saglayici kolunda saglayici ortam degiskenleri. Deterministik tur saglayici
 * anahtari olmadan da hazir olabilir (saglayiciya hic gitmez).
 */
export function turHazir(env, kod) {
  if (!turSunuluyor(kod)) { return { hazir: false, eksik: ["tur-kapali"] }; }
  const eksik = [];
  if (saglayiciTuru(kod)) {
    if (!env || !env.URETIM_API_TABAN) { eksik.push("uc-tabani"); }
    if (!env || !env.URETIM_TUR_ONEK) { eksik.push("tur-oneki"); }
    if (!env || !env[TUR_ORTAM[kod]]) { eksik.push("tur-yolu-" + kod); }
    if (!env || !env.URETIM_API_ANAHTAR) { eksik.push("api-anahtari"); }
  }
  if (!env || !env.TURNSTILE_SECRET) { eksik.push("bot-dogrulama"); }
  if (!env || !env.OZEL_DOSYA) { eksik.push("ozel-kova"); }
  if (!env || !env.KATALOG) { eksik.push("veritabani"); }
  if (VERI.onay_onayli !== true) { eksik.push("onay-metni-onayi"); }
  if (!(VERI.ornekSayisi(kod) > 0)) { eksik.push("gercek-ornek"); }
  return { hazir: eksik.length === 0, eksik };
}

/**
 * Ornek kolunun yapilandirmasi: musteri sartlarinin AYNISI eksi ORNEK_ATLANAN. Anahtar /
 * taban / tur yolu / ozel kova / veritabani eksikse ornek kolu da KAPALI (fail-closed AYNEN).
 */
export function ornekYapilandirma(env) {
  const eksik = yapilandirma(env).eksik.filter((e) => !ORNEK_ATLANAN.includes(e));
  return { hazir: eksik.length === 0, eksik };
}

/**
 * ACILIS ANAHTARI (Okan 7 Eki 15:4x: fiyat tablosu KALKTI). Eskiden bir turun ACIK olmasi = fiyat
 * tablosunda satiri var demekti (11:2x kapatmasi satirlar silinerek yapildi); o anahtar burada ACIK
 * yazilir: D1 `foto_acik` (tur, acik). VARSAYILAN KAPALI — satir yok, acik != 1, tablo yok ya da
 * okuma HERHANGI bir hatayla dusuyorsa o tur KAPALI (fail-closed). Donus: acik tur kodlari (Set).
 */
export async function acikAnahtari(env) {
  try {
    const r = await env.KATALOG.prepare("SELECT tur FROM foto_acik WHERE acik = 1").all();
    return new Set((r.results || []).map((x) => x.tur).filter((k) => typeof k === "string"));
  } catch (e) {
    return new Set();
  }
}

/**
 * Siparis alabilen turler: acilis anahtari ACIK · gercek ornegi >=1 · fiyat formulu gecerli.
 * Olculer + fiyat TEK FORMULDEN (VERI.fiyatKurus = en uzun boyut mm × 1000); tablo OKUNMAZ.
 */
export function acikTurler(acik) {
  const kume = acik instanceof Set ? acik : new Set();
  return VERI.turler
    .filter((t) => kume.has(t.kod))
    .filter((t) => turSunuluyor(t.kod))
    .filter((t) => VERI.ornekSayisi(t.kod) > 0)
    .map((t) => ({
      kod: t.kod, ad: t.ad, aciklama: t.aciklama,
      ornek_sayisi: VERI.ornekSayisi(t.kod),
      olculer: VERI.olcuSecenekleri(t.kod)
        .map((mm) => ({ mm, fiyat_kurus: VERI.fiyatKurus(t.kod, mm) }))
        .filter((o) => o.fiyat_kurus > 0),
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
  const parca = saglayiciTuru(tur) ? String(env[TUR_ORTAM[tur]] || "") : "";
  if (!parca) { throw new Error("foto: sunulmayan tur ya da tur yolu eksik"); }
  return "/" + String(env.URETIM_TUR_ONEK || "").replace(/^\/+|\/+$/g, "") + "/" +
    parca.replace(/^\/+|\/+$/g, "");
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

// ---------------------------------------------------------------- 3MF olcu kapisi
//
// 6 Eki olcumu: onarim zincirinden cikan 3MF 1094 mm geldi (120 mm siparis). 3MF R2'ye
// yazilmadan ONCE tepe sinir kutusu olculur; XY uzun kenar siparis olcusunden %3'ten fazla
// saparsa ana modeldeki build item transform'una duze olcek uygulanir (tepe verisi ve diger
// zip girdileri bayt-esit kalir), sonuc YENIDEN olculur; tutmazsa satir 'elle' olcu-tutmadi.

/** XY uzun kenarin siparis olcusunden izin verilen goreli sapmasi. */
export const OLCU_TOLERANS = 0.03;
const ANA_MODEL = "3D/3dmodel.model";
const BIRIM_MM = { micron: 0.001, millimeter: 1, centimeter: 10, inch: 25.4, foot: 304.8, meter: 1000 };

let CRC_TABLO = null;
function crc32(b) {
  if (!CRC_TABLO) {
    CRC_TABLO = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) { c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; }
      CRC_TABLO[n] = c >>> 0;
    }
  }
  let c = 0xFFFFFFFF;
  for (let i = 0; i < b.length; i++) { c = CRC_TABLO[(c ^ b[i]) & 0xFF] ^ (c >>> 8); }
  return (c ^ 0xFFFFFFFF) >>> 0;
}

/** Zip merkez dizini: [{ad, yontem, csize, usize, yerel, merkez(bas, son)}]; okunamazsa null. Zip64 RED. */
function zipDizini(b) {
  const v = new DataView(b.buffer, b.byteOffset, b.byteLength);
  let e = -1;
  for (let i = b.length - 22; i >= Math.max(0, b.length - 22 - 65535); i--) {
    if (v.getUint32(i, true) === 0x06054b50) { e = i; break; }
  }
  if (e < 0) { return null; }
  const adet = v.getUint16(e + 10, true);
  let p = v.getUint32(e + 16, true);
  if (adet === 0xFFFF || p === 0xFFFFFFFF || p >= e) { return null; }
  const cozucu = new TextDecoder();
  const g = [];
  for (let i = 0; i < adet; i++) {
    if (p + 46 > e || v.getUint32(p, true) !== 0x02014b50) { return null; }
    const ad = v.getUint16(p + 28, true), ek = v.getUint16(p + 30, true), yorum = v.getUint16(p + 32, true);
    const x = { ad: cozucu.decode(b.subarray(p + 46, p + 46 + ad)), bayrak: v.getUint16(p + 8, true),
                yontem: v.getUint16(p + 10, true), csize: v.getUint32(p + 20, true),
                usize: v.getUint32(p + 24, true), yerel: v.getUint32(p + 42, true),
                merkez: [p, p + 46 + ad + ek + yorum] };
    if (x.csize === 0xFFFFFFFF || x.usize === 0xFFFFFFFF || x.yerel === 0xFFFFFFFF || x.yerel + 30 > e) { return null; }
    if (v.getUint32(x.yerel, true) !== 0x04034b50) { return null; }
    x.veri = x.yerel + 30 + v.getUint16(x.yerel + 26, true) + v.getUint16(x.yerel + 28, true);
    if (x.veri + x.csize > e) { return null; }
    g.push(x);
    p = x.merkez[1];
  }
  return { girdiler: g, merkezBas: v.getUint32(e + 16, true), son: e };
}

/** Girdinin acik govdesini akis olarak verir (0 = saklanmis, 8 = deflate). */
function girdiAkisi(b, x) {
  const ham = b.subarray(x.veri, x.veri + x.csize);
  const akis = new Blob([ham]).stream();
  if (x.yontem === 0) { return akis; }
  if (x.yontem === 8) { return akis.pipeThrough(new DecompressionStream("deflate-raw")); }
  return null;
}

async function girdiMetni(b, x) {
  const a = girdiAkisi(b, x);
  return a ? new Response(a).text() : null;
}

/**
 * Bir .model girdisinin her tepesini `fn(x, y, z)` ile gezer; bellek dostu (akisli, parca
 * sinirinda kuyruk tutar). Her `<vertex` x/y/z ile okunamazsa null (sayim tutmazsa olcum YOK;
 * fail-closed), yoksa gezilen tepe sayisi.
 */
async function tepeGez(b, x, fn) {
  const a = girdiAkisi(b, x);
  if (!a) { return null; }
  const kalip = /<vertex\s[^>]*?\bx="([^"]+)"[^>]*?\by="([^"]+)"[^>]*?\bz="([^"]+)"[^>]*>/g;
  let n = 0, etiket = 0, kuyruk = "";
  const isle = (s) => {
    kalip.lastIndex = 0;
    let m;
    while ((m = kalip.exec(s)) !== null) {
      fn(+m[1], +m[2], +m[3]);
      n++;
    }
    for (let i = s.indexOf("<vertex"); i >= 0; i = s.indexOf("<vertex", i + 7)) {
      const c = s.charCodeAt(i + 7);
      if (c === 32 || c === 9 || c === 10 || c === 13) { etiket++; }
    }
  };
  const okuyucu = a.pipeThrough(new TextDecoderStream()).getReader();
  for (;;) {
    const { value, done } = await okuyucu.read();
    if (done) { break; }
    const s = kuyruk + value;
    const kes = s.lastIndexOf(">") + 1;
    isle(s.slice(0, kes));
    kuyruk = s.slice(kes);
    if (kuyruk.length > 4096) { return null; }
  }
  isle(kuyruk);
  return n === etiket ? n : null;
}

/** Bir .model girdisinin tepe sinir kutusu (model birimi); okunamazsa null. */
async function tepeKutusu(b, x) {
  const en = [Infinity, Infinity, Infinity], ust = [-Infinity, -Infinity, -Infinity];
  const n = await tepeGez(b, x, (px, py, pz) => {
    if (px < en[0]) { en[0] = px; }
    if (px > ust[0]) { ust[0] = px; }
    if (py < en[1]) { en[1] = py; }
    if (py > ust[1]) { ust[1] = py; }
    if (pz < en[2]) { en[2] = pz; }
    if (pz > ust[2]) { ust[2] = pz; }
  });
  if (n == null || [...en, ...ust].some((d) => !Number.isFinite(d))) { return null; }
  return { en, ust, n };
}

const BIRIM_DONUSUM = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0];
function donusumOku(s) {
  if (s == null) { return BIRIM_DONUSUM.slice(); }
  const d = String(s).trim().split(/\s+/).map(Number);
  return d.length === 12 && d.every(Number.isFinite) ? d : null;
}
/** 3MF satir-vektor kurali: p' = [x y z 1] * M. */
function noktaDonustur(p, m) {
  return [0, 1, 2].map((k) => p[0] * m[k] + p[1] * m[3 + k] + p[2] * m[6 + k] + m[9 + k]);
}
function kutuDonustur(k, m) {
  const en = [Infinity, Infinity, Infinity], ust = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < 8; i++) {
    const q = noktaDonustur([i & 1 ? k.ust[0] : k.en[0], i & 2 ? k.ust[1] : k.en[1], i & 4 ? k.ust[2] : k.en[2]], m);
    for (let j = 0; j < 3; j++) { en[j] = Math.min(en[j], q[j]); ust[j] = Math.max(ust[j], q[j]); }
  }
  return { en, ust };
}
const oznitelik = (etiket, ad) => {
  const m = new RegExp("(?:^|\\s)" + ad + "=\"([^\"]*)\"").exec(etiket);
  return m ? m[1] : null;
};

/**
 * 3MF'in yapi plakasindaki sinir kutusu (mm). Tek build item sart; nesne ya ana modelde tepe
 * tasir ya da bilesenleri (p:path dosyasi + transform) uzerinden kurulur.
 * Donus {en, ust, L (XY uzun kenar), z, item: {bas, son, M}, metin} ya da {hata}.
 */
async function ucmfOlc(b) {
  const z = zipDizini(b);
  if (!z) { return { hata: "zip-okunamadi" }; }
  const ana = z.girdiler.find((x) => x.ad === ANA_MODEL);
  if (!ana) { return { hata: "ana-model-yok" }; }
  const metin = await girdiMetni(b, ana);
  if (metin == null) { return { hata: "ana-model-acilamadi" }; }
  const birim = BIRIM_MM[oznitelik((/<model\b[^>]*>/.exec(metin) || [""])[0], "unit") || "millimeter"];
  if (!birim) { return { hata: "birim-bilinmiyor" }; }
  const ogeler = [...metin.matchAll(/<item\b[^>]*>/g)];
  if (ogeler.length !== 1) { return { hata: "build-item-sayisi-" + ogeler.length }; }
  const ie = ogeler[0];
  const M = donusumOku(oznitelik(ie[0], "transform"));
  if (!M) { return { hata: "item-transform-okunamadi" }; }
  const kutular = new Map();
  const dosyaKutusu = async (ad) => {
    if (!kutular.has(ad)) {
      const x = z.girdiler.find((g) => g.ad === ad);
      kutular.set(ad, x ? await tepeKutusu(b, x) : null);
    }
    return kutular.get(ad);
  };
  const parcalar = [], kaynaklar = [];
  const bilesenler = [...metin.matchAll(/<component\b[^>]*>/g)];
  if (bilesenler.length) {
    for (const c of bilesenler) {
      const yol = (oznitelik(c[0], "p:path") || "/" + ANA_MODEL).replace(/^\//, "");
      const C = donusumOku(oznitelik(c[0], "transform"));
      const k = await dosyaKutusu(yol);
      if (!C || !k) { return { hata: "bilesen-olculemedi" }; }
      parcalar.push(kutuDonustur(kutuDonustur(k, C), M));
      kaynaklar.push({ ad: yol, C });
    }
  } else {
    const k = await dosyaKutusu(ANA_MODEL);
    if (!k) { return { hata: "tepe-yok" }; }
    parcalar.push(kutuDonustur(k, M));
    kaynaklar.push({ ad: ANA_MODEL, C: BIRIM_DONUSUM });
  }
  const en = [0, 1, 2].map((j) => Math.min(...parcalar.map((p) => p.en[j])) * birim);
  const ust = [0, 1, 2].map((j) => Math.max(...parcalar.map((p) => p.ust[j])) * birim);
  // OLCU EKSENI (Okan 7 Eki 15:4x): sinir kutusunun EN UZUN boyutu — x/y/z hangisi buyukse
  // (ayak/cerceve dahil tek nesne). Fiyat ve olcek bu degere baglidir; yalniz X/Y'ye bakmak YANLIS.
  const L = Math.max(ust[0] - en[0], ust[1] - en[1], ust[2] - en[2]);
  if (!(L > 0)) { return { hata: "olcu-sifir" }; }
  return { en, ust, L, z: ust[2] - en[2], birim, metin, kaynaklar, zip: z,
           item: { bas: ie.index, son: ie.index + ie[0].length, etiket: ie[0], M } };
}

// ---------------------------------------------------------------- plaket alt kenar kalinligi
//
// TeKiN bulgusu (6 Eki): ilk ornek plaketin alt kenari nominal 3,0 mm DEGIL, olculen 6,61 mm
// (cerceve seridi 6,2-6,6). Ayak yivi = t + bosluk oldugundan ayak ureteci nominal tabani degil
// OLCULEN kalinligi almali. TANIM: plaket yapi plakasinda yatar, ayakta dik durur; alt kenar =
// yapi plakasinda Y EN KUCUK kenar. Serit = [Y_min, Y_min + ALT_KENAR_SERIT_MM]; kalinlik =
// seritteki tepelerin Z yayilimi (en ust - en alt, mm), OLCEKLENMIS dosyada (build transform +
// bilesen transform + birim uygulanmis). Kabartma seritte basliyorsa o da sayilir (yiv onu da
// almalidir). Okunamazsa null (fail-closed: tahmini deger YAZILMAZ).

/** Alt kenar seridinin eni (mm; ayak uretecinin `taban_kalinlik` tanimi: "alttaki ~10 mm serit"). */
export const ALT_KENAR_SERIT_MM = 10;

/** Olculmus 3MF'in (ucmfOlc donusu) alt kenar kalinligi, mm (2 hane) ya da null. */
async function altKenarOlc(b, o) {
  const gez = async (fn) => {
    for (const p of o.kaynaklar) {
      const x = o.zip.girdiler.find((g) => g.ad === p.ad);
      if (!x) { return false; }
      const n = await tepeGez(b, x, (px, py, pz) => {
        const q = noktaDonustur(noktaDonustur([px, py, pz], p.C), o.item.M);
        fn(q[1] * o.birim, q[2] * o.birim);
      });
      if (n == null) { return false; }
    }
    return true;
  };
  let yEn = Infinity;
  if (!(await gez((y) => { if (y < yEn) { yEn = y; } }))) { return null; }
  const sinir = yEn + ALT_KENAR_SERIT_MM;
  let zEn = Infinity, zUst = -Infinity;
  if (!(await gez((y, z) => {
    if (y <= sinir) { if (z < zEn) { zEn = z; } if (z > zUst) { zUst = z; } }
  }))) { return null; }
  const t = zUst - zEn;
  return Number.isFinite(t) && t > 0 ? +t.toFixed(2) : null;
}

const sayiYaz = (d) => String(Math.abs(d) < 1e-12 ? 0 : +d.toPrecision(10));

/** Ana model girdisini `yeni` metinle degistirip zip'i yeniden kurar; diger girdiler bayt-esit. */
function zipGirdiDegistir(b, z, ad, yeniMetin) {
  const yeni = new TextEncoder().encode(yeniMetin);
  const crc = crc32(yeni);
  const sira = z.girdiler.slice().sort((p, q) => p.yerel - q.yerel);
  const parca = [], yeniYerel = new Map();
  let p = 0;
  sira.forEach((x, i) => {
    const son = i + 1 < sira.length ? sira[i + 1].yerel : z.merkezBas;
    yeniYerel.set(x, p);
    if (x.ad !== ad) { parca.push(b.subarray(x.yerel, son)); p += son - x.yerel; return; }
    const adB = new TextEncoder().encode(x.ad);
    const h = new Uint8Array(30 + adB.length), v = new DataView(h.buffer);
    v.setUint32(0, 0x04034b50, true); v.setUint16(4, 20, true); v.setUint16(6, x.bayrak & 0x0800, true);
    v.setUint16(8, 0, true);
    v.setUint32(10, new DataView(b.buffer, b.byteOffset).getUint32(x.merkez[0] + 12, true), true);
    v.setUint32(14, crc, true); v.setUint32(18, yeni.length, true); v.setUint32(22, yeni.length, true);
    v.setUint16(26, adB.length, true); v.setUint16(28, 0, true); h.set(adB, 30);
    parca.push(h, yeni); p += h.length + yeni.length;
  });
  const merkezBas = p;
  for (const x of z.girdiler) {
    const r = b.slice(x.merkez[0], x.merkez[1]), v = new DataView(r.buffer);
    v.setUint32(42, yeniYerel.get(x), true);
    if (x.ad === ad) {
      v.setUint16(8, x.bayrak & 0x0800, true); v.setUint16(10, 0, true);
      v.setUint32(16, crc, true); v.setUint32(20, yeni.length, true); v.setUint32(24, yeni.length, true);
    }
    parca.push(r); p += r.length;
  }
  const e = new Uint8Array(22), v = new DataView(e.buffer);
  v.setUint32(0, 0x06054b50, true);
  v.setUint16(8, z.girdiler.length, true); v.setUint16(10, z.girdiler.length, true);
  v.setUint32(12, p - merkezBas, true); v.setUint32(16, merkezBas, true);
  parca.push(e); p += 22;
  const c = new Uint8Array(p);
  let o = 0;
  for (const x of parca) { c.set(x, o); o += x.length; }
  return c;
}

/**
 * OLCU KAPISI: 3MF'i siparis olcusune getirir. Donus:
 *   {tampon, olcek, L_once, L_sonra, z_mm, alt_kenar_mm}  (tolerans icindeyse tampon = girdi, olcek 1;
 *                                            alt_kenar_mm olculemezse null — bkz. altKenarOlc)
 *   {hata, L_once?}                          -> cagiran 'elle' olcu-tutmadi, R2'ye YAZMAZ
 */
export async function ucmfOlcekle(tampon, hedefMm) {
  const b = new Uint8Array(tampon);
  if (!(hedefMm > 0)) { return { hata: "hedef-olcu-yok" }; }
  const o = await ucmfOlc(b);
  if (o.hata) { return { hata: o.hata }; }
  const L_once = +o.L.toFixed(3);
  if (Math.abs(o.L - hedefMm) / hedefMm <= OLCU_TOLERANS) {
    return { tampon, olcek: 1, L_once, L_sonra: L_once, z_mm: +o.z.toFixed(3),
             alt_kenar_mm: await altKenarOlc(b, o) };
  }
  const s = hedefMm / o.L;
  const M = o.item.M.slice();
  for (let i = 0; i < 9; i++) { M[i] *= s; }
  // Duze olcek item kokunun etrafinda; XY merkezi ve Z tabani yerinde kalsin (birim -> mm donusumu).
  const merkez = [(o.en[0] + o.ust[0]) / 2, (o.en[1] + o.ust[1]) / 2, o.en[2]].map((d) => d / o.birim);
  for (let k = 0; k < 3; k++) { M[9 + k] = merkez[k] - s * (merkez[k] - o.item.M[9 + k]); }
  const yeniDeger = M.map(sayiYaz).join(" ");
  const etiket = /(?:^|\s)transform="[^"]*"/.test(o.item.etiket)
    ? o.item.etiket.replace(/((?:^|\s)transform=")[^"]*"/, "$1" + yeniDeger + "\"")
    : o.item.etiket.replace(/^<item\b/, "<item transform=\"" + yeniDeger + "\"");
  const yeniMetin = o.metin.slice(0, o.item.bas) + etiket + o.metin.slice(o.item.son);
  let cikti;
  try {
    cikti = zipGirdiDegistir(b, zipDizini(b), ANA_MODEL, yeniMetin);
  } catch (e) {
    return { hata: "zip-yazilamadi", L_once };
  }
  const y = await ucmfOlc(cikti);
  if (y.hata) { return { hata: "olcek-sonrasi-" + y.hata, L_once }; }
  const L_sonra = +y.L.toFixed(3);
  if (Math.abs(y.L - hedefMm) / hedefMm > OLCU_TOLERANS) { return { hata: "olcek-tutmadi", L_once, L_sonra }; }
  // Alt kenar OLCEKLENMIS dosyada olculur (ayak bu dosyadan basilan plakete takilir).
  return { tampon: cikti.buffer, olcek: +s.toPrecision(8), L_once, L_sonra, z_mm: +y.z.toFixed(3),
           alt_kenar_mm: await altKenarOlc(cikti, y) };
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
  // Saglayici kolu hazir degilse yalniz hazir deterministik turler acik kalabilir.
  if (!y.hazir && !DETERMINISTIK_TURLER.some((k) => turHazir(env, k).hazir)) {
    return fjson({ acik: false, turler: [], ...taban }, 200);
  }
  let turler = acikTurler(await acikAnahtari(env)).filter((t) => turHazir(env, t.kod).hazir);
  if (!turler.length) { return fjson({ acik: false, turler: [], ...taban }, 200); }
  // Havuz (kredi) yalniz saglayici kolunu kapatir; deterministik kol kredi harcamaz.
  if (turler.some((t) => saglayiciTuru(t.kod))) {
    const havuz = await havuzHukmu(env, simdi, telegram);
    if (!havuz.acik) { turler = turler.filter((t) => !saglayiciTuru(t.kod)); }
  }
  if (!turler.length) { return fjson({ acik: false, turler: [], ...taban }, 200); }
  // 2D konsept yalniz saglayici kolundaki ACIK turlerde (manifest kaydi gecerliyse) sunulur.
  const konsept = konseptAyarGecerli()
    ? { turler: turler.filter((t) => saglayiciTuru(t.kod)).map((t) => t.kod), deneme: KONSEPT.deneme_is_basi }
    : { turler: [], deneme: 0 };
  return fjson({ acik: true, turler, konsept, ...taban }, 200);
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
export async function botDogrula(request, env, jeton) {
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
    return !!(s && s.success === true && turnstileHostKabul(env, s.hostname));
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
  // Ornek isleri (panel, Okan) musterinin gunluk tavanini YEMEZ.
  const g = await env.KATALOG.prepare(
    "SELECT COUNT(*) AS n FROM foto_isler WHERE tarih >= ? AND ziyaretci != ?"
  ).bind(esik, ORNEK_ZIYARETCI).first();
  return { kisi: (k && k.n) || 0, genel: (g && g.n) || 0 };
}

/**
 * AYDINLATMA ONAYI (tek kutu, taslak-2): musteri aydinlatma metnini (hak beyani + aktarim rizasi
 * cumleleri dahil) okudugunu isaretler. `aydinlatma_onay` true ve gordugu metin GUNCEL surum
 * olmali; aksi her durumda 400 (eski sayfadan / eski alanla gelen onay yeni metne sayilmaz).
 * Onizleme · uretec onizleme · litofan · konsept · foto kalemli /baslat AYNI kontrolu kullanir.
 * Donus: hata kodu ya da null.
 */
export function aydinlatmaOnayHatasi(g) {
  if (!g || g.aydinlatma_onay !== true) { return "onay-yok"; }
  if (g.onay_surum !== VERI.onay_surum) { return "onay-surumu-eski"; }
  return null;
}

async function onizlemeUcu(request, env, simdi, telegram) {
  const y = yapilandirma(env);
  let g;
  try { g = await request.json(); } catch (e) { g = null; }
  // URETEC KOLU: tarayici onizleyicisi olmayan D/R turu saglayiciya GITMEZ, koşucu kuyruguna girer.
  if (g && typeof g === "object" && uretecOnizlemeTuru(g.tur)) { return uretecOnizlemeUcu(request, env, simdi, g); }
  if (!y.hazir) { return fjson({ hata: "kapali" }, 503); }
  if (!g || typeof g !== "object") { return fjson({ hata: "gecersiz-istek" }, 400); }

  // Deterministik tur bu uctan GECMEZ (saglayiciya gitmez): /foto/litofan.
  const tur = acikTurler(await acikAnahtari(env)).find((t) => t.kod === g.tur && saglayiciTuru(t.kod));
  if (!tur) { return fjson({ hata: "tur-kapali" }, 400); }
  if (!turYoluVar(env, tur.kod)) { return fjson({ hata: "kapali" }, 503); }
  const gh = girdiGovdeDogrula(tur.kod, g);
  if (gh) { return fjson({ hata: gh }, 400); }
  const nt = uretimNotuDogrula(g.not);
  if (!nt.ok) { return fjson({ hata: nt.hata }, 400); }
  const olcu = Number.isInteger(g.olcu_mm) ? g.olcu_mm : null;
  if (!tur.olculer.some((o) => o.mm === olcu)) { return fjson({ hata: "gecersiz-olcu" }, 400); }
  // ONAY: tek aydinlatma kutusu + musterinin gordugu metin GUNCEL surum.
  const oh = aydinlatmaOnayHatasi(g);
  if (oh) { return fjson({ hata: oh }, 400); }
  // KONSEPT ONAYLANDIYSA 3D onizlemenin girdisi konsept gorselidir (foto ikinci kez gelmez).
  const gorsel = g.konsept !== undefined ? await konseptGirdisi(env, g.konsept, tur.kod, false) : gorselCoz(g.gorsel);
  if (!gorsel) { return fjson({ hata: g.konsept !== undefined ? "konsept-gecersiz" : "gorsel-gecersiz" }, 400); }

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

  const isNo = yeniIsNo();
  const hata = await onizlemeGonder(env, isNo, tur.kod, olcu, ziyaretci, gorsel.uri, simdi, telegram, nt.deger,
    VERI.onay_surum);
  if (hata) { return hata; }
  if (gorsel.konsept) { await konseptBagla(env, gorsel.konsept, isNo); }
  return fjson({ is: isNo, kalan: Math.max(0, VERI.sinir_ziyaretci_24s - sayi.kisi - 1) }, 200);
}

/** Onay kaydi: surum doluysa {tarih: onay ani (ISO), surum}; bos surum (ornek kolu) -> iki alan da bos. */
function onayKaydi(onaySurum, simdi) {
  return onaySurum ? { tarih: simdiIso(simdi), surum: onaySurum } : { tarih: "", surum: "" };
}

/**
 * Is satirini yazar + saglayiciya onizleme gorevini gonderir (musteri ve ornek kolu ORTAK).
 * Basarida null; hatada musteriye/panele donulecek yanit.
 */
async function onizlemeGonder(env, isNo, tur, olcu, ziyaretci, uri, simdi, telegram, uretimNotu, onaySurum) {
  // Is satiri SAGLAYICIDAN ONCE yazilir: reddedilen deneme de ziyaretci sinirindan duser
  // (sinir "basarili onizleme" degil "deneme" sayar -> kaba kuvvetle kredi yakilamaz).
  // Uretim notu (dogrulanmis) yalniz doluysa sutuna yazilir: bos notta goc oncesi sema da calisir.
  // Aydinlatma onayi (damga + surum) musteri kolunda her satira; ornek (panel) kolu muaf -> bos.
  const onay = onayKaydi(onaySurum, simdi);
  if (uretimNotu) {
    await env.KATALOG.prepare(
      "INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, uretim_notu, onay_tarih, onay_surum)" +
      " VALUES (?, ?, ?, ?, ?, 'onizleme', ?, ?, ?)"
    ).bind(isNo, tur, olcu, ziyaretci, simdiIso(simdi), uretimNotu, onay.tarih, onay.surum).run();
  } else {
    await env.KATALOG.prepare(
      "INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, onay_tarih, onay_surum)" +
      " VALUES (?, ?, ?, ?, ?, 'onizleme', ?, ?)"
    ).bind(isNo, tur, olcu, ziyaretci, simdiIso(simdi), onay.tarih, onay.surum).run();
  }

  const c = await saglayici(env, "POST", turYolu(env, tur) + "/v1/prototype", {
    image_url: uri,
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
  return null;
}

// ---------------------------------------------------------------- uc: /foto/konsept (2D KONSEPT)
//
// Okan 7 Eki 14:5x: "görsel eklendikten sonra müşteri ... not yazabilmeli ve 2d sonuç buna göre çıkmalı".
// AKIS: foto + "Nasil olsun?" notu -> saglayicinin gorsel+metin -> gorsel ucu -> konsept gorseli (ozel
// kova) -> musteri "Bunu kullan" -> /foto/onizleme {konsept} -> 3D onizlemenin GIRDISI konsept gorselidir.
// Sinirlar (hepsi burada, testli: shop/test/foto-konsept.mjs): is (oturum) basi deneme · bot jetonu
// (fail-closed) · ziyaretci 24 s siniri · gunluk kredi tavani (asilinca 429) · acilis anahtari (tur
// kapaliysa saglayiciya 0 cagri) · havuz esigi. ORNEK kolu (panel) ziyaretci/bot/tavan sinirsiz.
// Saglayiciya giden: foto (data URI) + sabit cerceve + DOGRULANMIS not (e-posta/telefon RED). IP, ad,
// siparis bilgisi GITMEZ.

/** Konsept ayarlari TEK KAYNAK: manifest (foto-uretim-veri.js VERI.konsept). */
const KONSEPT = VERI.konsept;
/** Saglayicinin gorsel+metin -> gorsel ucu (taban URETIM_API_TABAN; ad/host kodda YOK). */
const KONSEPT_YOLU = "/v1/image-to-image";
/** Konsept gorseli ozel kovada; yalniz konsept anahtariyla sunulur, 3 gun sonra silinir. */
export function konseptAnahtari(no) { return "foto-konsept/" + no + ".png"; }

/** Manifest kaydi eksik/bozuksa konsept KAPALI (fail-closed: harcama yolu). */
export function konseptAyarGecerli() {
  const k = KONSEPT;
  const tam = (n) => Number.isInteger(n) && n > 0;
  return !!k && typeof k.model === "string" && /^[a-z0-9.-]{2,40}$/.test(k.model) &&
    tam(k.kredi_tahmini) && tam(k.deneme_is_basi) && tam(k.sinir_ziyaretci_24s) && tam(k.gunluk_kredi_tavani);
}

/**
 * SABIT CERCEVE (Ingilizce: model talimati). Musteri notu (dogrulanmis, temiz) yalniz SONUNA eklenir;
 * not bossa cerceve tek basina gider (foto -> stil konsepti).
 */
export const KONSEPT_CERCEVE =
  "Redraw the main subject of the reference photo as a clean, bold, flat-colour illustration for a " +
  "raised relief plaque: at most 4 solid colours, clear outlines, simple plain light background, " +
  "no text, no letters, no logos, no watermark. Keep the subject recognisable and centred.";
export function konseptPromptu(not) {
  return not ? KONSEPT_CERCEVE + " Customer request (may be in Turkish): \"" + String(not).replace(/"/g, "'") + "\""
    : KONSEPT_CERCEVE;
}

/** Bayt -> base64 (Worker'da Buffer yok; parcali btoa). */
function b64(bayt) {
  const u = new Uint8Array(bayt);
  let s = "";
  for (let i = 0; i < u.length; i += 0x8000) { s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); }
  return btoa(s);
}

/** Konsept sayilari: oturumdaki deneme · ziyaretcinin 24 s denemesi · tum musterilerin 24 s denemesi. */
async function konseptSayilari(env, oturum, ziyaretci, simdi) {
  const esik = saatOnce(simdi, 24);
  const o = oturum ? await env.KATALOG.prepare(
    "SELECT COUNT(*) AS n, COALESCE(SUM(ziyaretci = ?), 0) AS ornek FROM foto_konsept WHERE oturum = ?"
  ).bind(ORNEK_ZIYARETCI, oturum).first() : null;
  const k = await env.KATALOG.prepare(
    "SELECT COUNT(*) AS n FROM foto_konsept WHERE ziyaretci = ? AND tarih >= ?").bind(ziyaretci, esik).first();
  // Ornek konseptleri (panel) musterinin gunluk kredi tavanini YEMEZ.
  const g = await env.KATALOG.prepare(
    "SELECT COUNT(*) AS n FROM foto_konsept WHERE ziyaretci != ? AND tarih >= ?").bind(ORNEK_ZIYARETCI, esik).first();
  return { oturum: (o && o.n) || 0, oturumOrnek: (o && o.ornek) || 0, kisi: (k && k.n) || 0, genel: (g && g.n) || 0 };
}

/**
 * POST /foto/konsept {tur, gorsel, not?, oturum?, aydinlatma_onay, onay_surum, turnstile_token}
 * -> {konsept, oturum, kalan}. `ornek` = panel kolu (bot/onay/ziyaretci/tavan ATLANIR, havuz AYNEN).
 */
async function konseptUret(request, env, simdi, telegram, ornek) {
  const y = ornek ? ornekYapilandirma(env) : yapilandirma(env);
  if (!y.hazir || !konseptAyarGecerli()) { return fjson({ hata: "kapali" }, 503); }
  let g;
  try { g = await request.json(); } catch (e) { g = null; }
  if (!g || typeof g !== "object") { return fjson({ hata: "gecersiz-istek" }, 400); }
  // Konsept yalniz SAGLAYICI kolunda (3D onizlemeye girer). Musteride acilis anahtari ZORUNLU.
  let tur = null;
  if (ornek) {
    const k = g.tur === undefined ? Object.keys(TUR_ORTAM)[0] : g.tur;
    tur = saglayiciTuru(k) ? k : null;
  } else {
    const t = acikTurler(await acikAnahtari(env)).find((x) => x.kod === g.tur && saglayiciTuru(x.kod));
    tur = t ? t.kod : null;
  }
  if (!tur) { return fjson({ hata: "tur-kapali" }, 400); }
  if (!turYoluVar(env, tur)) { return fjson({ hata: "kapali" }, 503); }
  if (!ornek && (typeof g.turnstile_token !== "string" || !g.turnstile_token.trim())) {
    return fjson({ hata: "bot-jetonu-yok" }, 400);
  }
  const nt = uretimNotuDogrula(g.not);
  if (!nt.ok) { return fjson({ hata: nt.hata }, 400); }
  if (!ornek) {
    const oh = aydinlatmaOnayHatasi(g);
    if (oh) { return fjson({ hata: oh }, 400); }
  }
  const gorsel = gorselCoz(g.gorsel);
  if (!gorsel) { return fjson({ hata: "gorsel-gecersiz" }, 400); }
  const oturum = g.oturum === undefined || g.oturum === null || g.oturum === "" ? null : g.oturum;
  if (oturum !== null && !IS_KALIBI.test(String(oturum))) { return fjson({ hata: "gecersiz-oturum" }, 400); }

  const ziyaretci = ornek ? ORNEK_ZIYARETCI :
    await ziyaretciOzeti(env, request.headers.get("CF-Connecting-IP") || "yok");
  let sayi;
  try { sayi = await konseptSayilari(env, oturum, ziyaretci, simdi); } catch (e) {
    // Sayilamayan sinir = KAPALI (tablo yok dahil): saglayiciya istek 0.
    return fjson({ hata: "kapali" }, 503);
  }
  // Musteri oturumu ornek kolunda (ya da tersi) kullanilamaz.
  if (oturum && (ornek ? sayi.oturum !== sayi.oturumOrnek : sayi.oturumOrnek > 0)) {
    return fjson({ hata: "bulunamadi" }, 404);
  }
  if (sayi.oturum >= KONSEPT.deneme_is_basi) {
    return fjson({ hata: "konsept-hakki-bitti", deneme: KONSEPT.deneme_is_basi }, 429);
  }
  if (!ornek) {
    if (await hizSiniriAsildi(request, env)) { return fjson({ hata: "cok-istek" }, 429); }
    if (sayi.kisi >= KONSEPT.sinir_ziyaretci_24s) {
      return fjson({ hata: "konsept-siniri", sinir: KONSEPT.sinir_ziyaretci_24s }, 429);
    }
    if ((sayi.genel + 1) * KONSEPT.kredi_tahmini > KONSEPT.gunluk_kredi_tavani) {
      return fjson({ hata: "konsept-gunluk-tavan" }, 429);
    }
    const botGecti = await botDogrula(request, env, g.turnstile_token);
    if (!botGecti) { return fjson({ hata: "bot-dogrulama" }, 403); }
  }
  const havuz = await havuzHukmu(env, simdi, telegram);
  if (!havuz.acik) { return fjson({ hata: ornek ? "havuz-esikte" : "kapali" }, 503); }

  // Satir saglayicidan ONCE yazilir: reddedilen deneme de sinirlardan duser (kaba kuvvetle kredi yakilamaz).
  const no = yeniIsNo();
  const ot = oturum || yeniIsNo();
  await env.KATALOG.prepare(
    "INSERT INTO foto_konsept (konsept_no, oturum, tur, ziyaretci, tarih, asama) VALUES (?, ?, ?, ?, ?, 'uretiliyor')"
  ).bind(no, ot, tur, ziyaretci, simdiIso(simdi)).run();
  const c = await saglayici(env, "POST", KONSEPT_YOLU, {
    ai_model: KONSEPT.model,
    prompt: konseptPromptu(nt.deger),
    reference_image_urls: [gorsel.uri],
  });
  const gorev = gorevKimligi(c.govde);
  if (c.kod < 200 || c.kod >= 300 || !gorev) {
    const sebep = c.kod === 400 ? "gorsel-uygun-degil" : (c.kod === 402 ? "kredi" : "saglayici");
    await env.KATALOG.prepare(
      "UPDATE foto_konsept SET asama = 'basarisiz', hata = ? WHERE konsept_no = ?").bind(sebep, no).run();
    if (c.kod === 402 && typeof telegram === "function") {
      await telegram(env, "📸 Fotoğraftan üretim: konsept kredisi YETMEDİ (sağlayıcı 402).");
    }
    return fjson({ hata: sebep === "gorsel-uygun-degil" ? "gorsel-uygun-degil" : "gecici-hata" },
                 sebep === "gorsel-uygun-degil" ? 422 : 503);
  }
  await env.KATALOG.prepare("UPDATE foto_konsept SET gorev = ? WHERE konsept_no = ?").bind(gorev, no).run();
  return fjson({ konsept: no, oturum: ot, kalan: Math.max(0, KONSEPT.deneme_is_basi - sayi.oturum - 1) }, 200);
}

async function konseptGetir(env, no) {
  if (!IS_KALIBI.test(String(no || ""))) { return null; }
  try {
    return await env.KATALOG.prepare(
      "SELECT konsept_no, oturum, tur, ziyaretci, tarih, asama, gorev, son_kontrol, hazir_tarih, hata, is_no" +
      " FROM foto_konsept WHERE konsept_no = ?").bind(no).first();
  } catch (e) {
    if (tabloYok(e)) { return null; }
    throw e;
  }
}

function konseptYaniti(k, ornek) {
  const v = { konsept: k.konsept_no, oturum: k.oturum, asama: k.asama };
  if (k.asama === "hazir") {
    v.gorsel = (ornek ? "/api/shop/yonet/foto/ornek-konsept-gorsel" : "/api/shop/foto/konsept-gorsel") +
      "?konsept=" + k.konsept_no;
  }
  if (k.asama === "basarisiz") { v.hata = k.hata === "gorsel-uygun-degil" ? "gorsel-uygun-degil" : "uretilemedi"; }
  if (k.asama === "silindi") { v.asama = "suresi-doldu"; }
  if (k.ilerleme !== undefined) { v.ilerleme = k.ilerleme; }
  return fjson(v, 200);
}

/** GET /foto/konsept-durum?konsept= — gorevi yoklar; hazirsa gorseli ozel kovaya indirir (CAS'li). */
async function konseptDurum(env, url, simdi, ornek) {
  const k = await konseptGetir(env, url.searchParams.get("konsept"));
  // Ornek konsepti musteri ucunda (ve tersi) YOK sayilir: varligi da sizmaz.
  if (!k || ornekMi(k) !== !!ornek) { return fjson({ hata: "bulunamadi" }, 404); }
  const hazir = (ornek ? ornekYapilandirma(env) : yapilandirma(env)).hazir;
  if (k.asama !== "uretiliyor" || !k.gorev || !hazir) { return konseptYaniti(k, ornek); }
  if (simdi - (k.son_kontrol || 0) < DURUM_ARALIK_MS) { return konseptYaniti(k, ornek); }
  const kilit = await env.KATALOG.prepare(
    "UPDATE foto_konsept SET son_kontrol = ? WHERE konsept_no = ? AND son_kontrol = ? AND asama = 'uretiliyor'"
  ).bind(simdi, k.konsept_no, k.son_kontrol || 0).run();
  if (!kilit || !kilit.meta || kilit.meta.changes !== 1) { return konseptYaniti(k, ornek); }
  const c = await saglayici(env, "GET", KONSEPT_YOLU + "/" + k.gorev, null);
  if (c.kod !== 200 || !c.govde) { return konseptYaniti(k, ornek); }
  const d = gorevDurumu(c.govde);
  if (d === "dustu") {
    await env.KATALOG.prepare("UPDATE foto_konsept SET asama = 'basarisiz', hata = 'uretilemedi'" +
      " WHERE konsept_no = ? AND asama = 'uretiliyor'").bind(k.konsept_no).run();
    return konseptYaniti({ ...k, asama: "basarisiz", hata: "uretilemedi" }, ornek);
  }
  if (d !== "bitti") {
    const p = c.govde.progress;
    return konseptYaniti({ ...k, ilerleme: Number.isInteger(p) ? p : null }, ornek);
  }
  const adres = Array.isArray(c.govde.image_urls) ? c.govde.image_urls[0] : "";
  const dosya = await dosyaIndir(adres);
  if (!dosya) { return konseptYaniti(k, ornek); }   // sonraki yoklama yeniden dener
  await env.OZEL_DOSYA.put(konseptAnahtari(k.konsept_no), dosya.tampon,
    { httpMetadata: { contentType: /png|jpeg|webp/.test(dosya.tip) ? dosya.tip.split(";")[0] : "image/png" } });
  const kredi = krediSayisi(c.govde);
  await env.KATALOG.prepare("UPDATE foto_konsept SET asama = 'hazir', hazir_tarih = ?, kredi = ?" +
    " WHERE konsept_no = ? AND asama = 'uretiliyor'").bind(simdiIso(simdi), kredi, k.konsept_no).run();
  await krediYaz(env, simdi, "konsept", k.konsept_no, "", k.gorev, kredi);
  return konseptYaniti({ ...k, asama: "hazir" }, ornek);
}

/** GET /foto/konsept-gorsel?konsept= — yalniz konsept anahtariyla, ozel kovadan. */
async function konseptGorsel(env, url, ornek) {
  if (!env.OZEL_DOSYA) { return fjson({ hata: "bulunamadi" }, 404); }
  const k = await konseptGetir(env, url.searchParams.get("konsept"));
  if (!k || ornekMi(k) !== !!ornek || k.asama !== "hazir") { return fjson({ hata: "bulunamadi" }, 404); }
  return onizlemeGorseli(env, k.konsept_no, konseptAnahtari(k.konsept_no));
}

/**
 * Onaylanan konseptin gorseli -> 3D onizlemenin girdisi (data URI). Konsept 'hazir', ayni tur ve ayni
 * kol (musteri/ornek) olmali; gorsel gorselCoz'dan gecmeli. Gecersizse null (400 konsept-gecersiz).
 */
async function konseptGirdisi(env, no, tur, ornek) {
  const k = await konseptGetir(env, no);
  if (!k || ornekMi(k) !== !!ornek || k.asama !== "hazir" || k.tur !== tur || !env.OZEL_DOSYA) { return null; }
  const n = await env.OZEL_DOSYA.get(konseptAnahtari(k.konsept_no));
  if (!n) { return null; }
  const tip = (n.httpMetadata && n.httpMetadata.contentType) || "image/png";
  const bayt = new Uint8Array(await new Response(n.body).arrayBuffer());
  const g = gorselCoz("data:" + tip + ";base64," + b64(bayt));
  return g ? { ...g, konsept: k.konsept_no } : null;
}

/** 3D onizleme isi konsepte baglanir (temizlik siparise donen konsepti SILMEZ). */
async function konseptBagla(env, konsept, isNo) {
  await env.KATALOG.prepare("UPDATE foto_konsept SET is_no = ? WHERE konsept_no = ?").bind(isNo, konsept).run();
}

/** 3 gun kurali (ONIZLEME_SAKLAMA_SAAT): siparise donmeyen konsept gorseli silinir. Tablo yoksa 0. */
async function konseptTemizle(env, simdi) {
  let r;
  try {
    r = await env.KATALOG.prepare(
      "SELECT konsept_no FROM foto_konsept WHERE asama != 'silindi' AND tarih < ?" +
      " AND (is_no = '' OR is_no NOT IN (SELECT is_no FROM foto_uretim)) LIMIT 50"
    ).bind(saatOnce(simdi, ONIZLEME_SAKLAMA_SAAT)).all();
  } catch (e) {
    if (tabloYok(e)) { return 0; }
    throw e;
  }
  let silinen = 0;
  for (const s of (r.results || [])) {
    await env.OZEL_DOSYA.delete(konseptAnahtari(s.konsept_no));
    await env.KATALOG.prepare("UPDATE foto_konsept SET asama = 'silindi' WHERE konsept_no = ?").bind(s.konsept_no).run();
    silinen++;
  }
  return silinen;
}

// ---------------------------------------------------------------- uc: /foto/onizleme URETEC KOLU

/** Siparis oncesi uretec onizlemesinin R2 dizini (koşucunun girdi/cikti sozlesmesi; ozel kova). */
export const URETEC_ONIZLEME_DIZIN = "foto-uretec-onizleme/";
export function uretecOnizlemeAnahtari(isNo, ad) { return URETEC_ONIZLEME_DIZIN + isNo + "/" + ad; }
/** Bolumun yoklama sozlesmesi (aralik 5 sn, tavan 180 sn) — yanitta da doner. */
export const URETEC_YOKLAMA = { aralik_sn: 5, tavan_sn: 180 };
/** Girdi fotografinin sozlesme §2 adi (koşucu ad kalibi `[a-z_]+.(png|jpg|svg|wav)`; webp YOK). */
const URETEC_FOTO_UZANTI = { "image/png": "png", "image/jpeg": "jpg" };
/** Dizinde olabilecek her ad (temizlik bunlari siler). */
const URETEC_DIZIN_ADLARI = ["girdi.json", "olcu.json", "model.3mf", "onizleme.png", "foto.png", "foto.jpg", "svg.svg"];

/**
 * POST /foto/onizleme (uretec kolu) — girdi + parametreler (VERI.parametreDogrula) + secim dogrulanir;
 * girdi dosyalari ve sozlesme §2 girdi.json (`siparis_no:""`, `kalem:0`) R2 dizinine, satir EN SON
 * `asama='uretec-onizleme'` ile yazilir (koşucu satiri gordugunde girdi tamdir). Saglayici cagrisi 0,
 * kredi 0. Ziyaretci siniri + genel tavan + bot jetonu (fail-closed) plaketle AYNI.
 */
async function uretecOnizlemeUcu(request, env, simdi, g) {
  if (!turHazir(env, g.tur).hazir) { return fjson({ hata: "kapali" }, 503); }
  const tur = acikTurler(await acikAnahtari(env)).find((t) => t.kod === g.tur);
  if (!tur) { return fjson({ hata: "tur-kapali" }, 400); }
  const gh = girdiGovdeDogrula(tur.kod, g);
  if (gh) { return fjson({ hata: gh }, 400); }
  const nt = uretimNotuDogrula(g.not);
  if (!nt.ok) { return fjson({ hata: nt.hata }, 400); }
  // TURETILMIS olcu ekseni: olcu musteriden ALINMAZ (surgu yok) -> 0; koşucu onizlemede OLCULEN uzun
  // kenari (VERI.olculenMm) satirin olcu_mm'sine yazar, fiyat ORADAN (uretecDurumYaniti/fotoKalemFiyatla).
  const turetilmis = VERI.olcuTuretilmis(tur.kod);
  const olcu = turetilmis ? 0 : Number.isInteger(g.olcu_mm) ? g.olcu_mm : null;
  if (!turetilmis && !tur.olculer.some((o) => o.mm === olcu)) { return fjson({ hata: "gecersiz-olcu" }, 400); }
  const oh = aydinlatmaOnayHatasi(g);
  if (oh) { return fjson({ hata: oh }, 400); }
  const sc = secimDogrula(tur.kod, g.secim);
  if (!sc) { return fjson({ hata: "gecersiz-secim" }, 400); }
  const kayit = VERI.turBul(tur.kod);
  const dosyalar = {};
  const yazilacak = [];
  if (kayit.girdi.some((x) => x === "foto-1" || x === "foto-1-3")) {
    const gorsel = gorselCoz(g.gorsel);
    const tip = gorsel ? gorsel.uri.slice(5, gorsel.uri.indexOf(";")) : "";
    if (!gorsel || !Object.prototype.hasOwnProperty.call(URETEC_FOTO_UZANTI, tip)) {
      return fjson({ hata: "gorsel-gecersiz" }, 400);
    }
    let bayt;
    try {
      bayt = Uint8Array.from(atob(gorsel.uri.slice(gorsel.uri.indexOf(",") + 1)), (c) => c.charCodeAt(0));
    } catch (e) { return fjson({ hata: "gorsel-gecersiz" }, 400); }
    dosyalar.foto = "foto." + URETEC_FOTO_UZANTI[tip];
    yazilacak.push([dosyalar.foto, bayt, tip]);
  } else if (g.gorsel !== undefined) { return fjson({ hata: "sema-disi-parametre" }, 400); }
  if (kayit.girdi.includes("svg")) {
    if (typeof g.svg !== "string") { return fjson({ hata: "svg-bos" }, 400); }
    dosyalar.svg = "svg.svg";
    yazilacak.push([dosyalar.svg, new TextEncoder().encode(g.svg), "image/svg+xml"]);
  }

  if (await hizSiniriAsildi(request, env)) { return fjson({ hata: "cok-istek" }, 429); }
  const ip = request.headers.get("CF-Connecting-IP") || "yok";
  const ziyaretci = await ziyaretciOzeti(env, ip);
  const sayi = await onizlemeSayisi(env, ziyaretci, simdi);
  const sinir = VERI.sinir_ziyaretci_24s;
  if (sayi.kisi >= sinir) { return fjson({ hata: "onizleme-siniri", sinir }, 429); }
  if (sayi.genel >= GUNLUK_ONIZLEME_TAVANI) { return fjson({ hata: "kapali" }, 503); }
  const bot = await botDogrula(request, env, g.turnstile_token);
  if (!bot) { return fjson({ hata: "bot-dogrulama" }, 403); }

  const isNo = yeniIsNo();
  const girdi = { sozlesme: 1, kategori: tur.kod, siparis_no: "", kalem: 0, olcu_mm: olcu,
                  renkler: sc.renk, malzemeler: sc.malzeme,
                  parametreler: VERI.parametreDogrula(tur.kod, g.parametreler).deger, dosyalar };
  for (const [ad, bayt, tip] of yazilacak) {
    await env.OZEL_DOSYA.put(uretecOnizlemeAnahtari(isNo, ad), bayt, { httpMetadata: { contentType: tip } });
  }
  await env.OZEL_DOSYA.put(uretecOnizlemeAnahtari(isNo, "girdi.json"), JSON.stringify(girdi),
    { httpMetadata: { contentType: "application/json" } });
  const onay = onayKaydi(VERI.onay_surum, simdi);
  if (nt.deger) {
    await env.KATALOG.prepare(
      "INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol, hata, uretim_notu, onay_tarih, onay_surum)" +
      " VALUES (?, ?, ?, ?, ?, 'uretec-onizleme', 0, '', ?, ?, ?)"
    ).bind(isNo, tur.kod, olcu, ziyaretci, simdiIso(simdi), nt.deger, onay.tarih, onay.surum).run();
  } else {
    await env.KATALOG.prepare(
      "INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol, hata, onay_tarih, onay_surum)" +
      " VALUES (?, ?, ?, ?, ?, 'uretec-onizleme', 0, '', ?, ?)"
    ).bind(isNo, tur.kod, olcu, ziyaretci, simdiIso(simdi), onay.tarih, onay.surum).run();
  }
  return fjson({ is: isNo, kalan: Math.max(0, VERI.sinir_ziyaretci_24s - sayi.kisi - 1),
                 yoklama: URETEC_YOKLAMA }, 200);
}

/** Olcunun kaynagi (is/siparis kaydi alani): "turetilmis" (onizlemede olculdu) | "surgu" (musteri secti). */
export function olcuKaynagi(tur) { return VERI.olcuTuretilmis(tur) ? "turetilmis" : "surgu"; }

/** Uretec onizlemesinin durum yaniti: hazir -> gorsel + olcu.json ozeti; kuyrukta -> bekliyor. */
async function uretecDurumYaniti(env, is) {
  if (is.asama === "uretec-onizleme") { return fjson({ asama: "bekliyor" }, 200); }
  if (is.asama !== "onizleme-hazir") { return durumYaniti(is); }
  let olcu = null;
  try {
    const n = await env.OZEL_DOSYA.get(uretecOnizlemeAnahtari(is.is_no, "olcu.json"));
    const o = n ? JSON.parse(await new Response(n.body).text()) : null;
    if (o && typeof o === "object") {
      olcu = { uzun_kenar_mm: o.uzun_kenar_mm, kutu_mm: o.kutu_mm, renk_sayisi: o.renk_sayisi };
    }
  } catch (e) { olcu = null; }
  const v = { asama: "hazir", tur: is.tur, olcu_mm: is.olcu_mm, olcu,
              gorsel: "/api/shop/foto/gorsel?is=" + is.is_no,
              gecerlilik_bitis: new Date(Date.parse(is.hazir_tarih) +
                VERI.gecerlilik_saat * 3600 * 1000).toISOString() };
  // TURETILMIS eksen: fiyat onizlemeyle BIRLIKTE, koşucunun KAYITLI olcusunden (D1 olcu_mm; istemci degil).
  v.olcu_kaynagi = olcuKaynagi(is.tur);
  if (v.olcu_kaynagi === "turetilmis") { v.fiyat_kurus = VERI.fiyatKurus(is.tur, is.olcu_mm); }
  return fjson(v, 200);
}

// ---------------------------------------------------------------- uc: /foto/litofan (deterministik)

/** Gri kalinlik haritasinin uzun kenar siniri (px) ve en/boy orani tavani (uretec 5:1 ustunu reddeder). */
export const LITOFAN_KENAR_EN_COK_PX = 1200;
export const LITOFAN_ORAN_EN_COK = 5;

/** PNG imzasi + IHDR'den {en, boy}; gecersizse null. */
function pngBoyut(bayt) {
  const imza = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
  if (!bayt || bayt.length < 24 || imza.some((b, i) => bayt[i] !== b)) { return null; }
  if (String.fromCharCode(bayt[12], bayt[13], bayt[14], bayt[15]) !== "IHDR") { return null; }
  const oku = (i) => ((bayt[i] << 24) >>> 0) + (bayt[i + 1] << 16) + (bayt[i + 2] << 8) + bayt[i + 3];
  return { en: oku(16), boy: oku(20) };
}

/**
 * POST /foto/litofan — tarayici fotograftan gri kalinlik haritasini (PNG) kendisi cizer; sunucuya
 * YALNIZ bu turetilmis harita gelir (orijinal fotograf gelmez). Saglayici cagrisi 0, havuz
 * sorgusu 0, kredi defterine yazim 0. Ayni ziyaretci siniri + bot jetonu (fail-closed) gecerli.
 * Harita onizleme anahtarina yazilir: saklama kurali plaketle AYNI (onizlemeTemizle).
 */
async function litofanUcu(request, env, simdi) {
  let g;
  try { g = await request.json(); } catch (e) { return fjson({ hata: "gecersiz-istek" }, 400); }
  if (!g || typeof g !== "object") { return fjson({ hata: "gecersiz-istek" }, 400); }
  if (!deterministikTur(g.tur)) { return fjson({ hata: "tur-kapali" }, 400); }
  if (!turHazir(env, g.tur).hazir) { return fjson({ hata: "kapali" }, 503); }
  const tur = acikTurler(await acikAnahtari(env)).find((t) => t.kod === g.tur);
  if (!tur) { return fjson({ hata: "tur-kapali" }, 400); }
  const gh = girdiGovdeDogrula(tur.kod, g);
  if (gh) { return fjson({ hata: gh }, 400); }
  const olcu = Number.isInteger(g.olcu_mm) ? g.olcu_mm : null;
  if (!tur.olculer.some((o) => o.mm === olcu)) { return fjson({ hata: "gecersiz-olcu" }, 400); }
  const oh = aydinlatmaOnayHatasi(g);
  if (oh) { return fjson({ hata: oh }, 400); }
  const gorsel = gorselCoz(g.gorsel);
  if (!gorsel || !gorsel.uri.startsWith("data:image/png;")) { return fjson({ hata: "gorsel-gecersiz" }, 400); }
  let bayt;
  try {
    bayt = Uint8Array.from(atob(gorsel.uri.slice(gorsel.uri.indexOf(",") + 1)), (c) => c.charCodeAt(0));
  } catch (e) { return fjson({ hata: "gorsel-gecersiz" }, 400); }
  const b = pngBoyut(bayt);
  const uzun = b ? Math.max(b.en, b.boy) : 0;
  const kisa = b ? Math.min(b.en, b.boy) : 0;
  if (!b || kisa < 1 || uzun > LITOFAN_KENAR_EN_COK_PX || uzun > LITOFAN_ORAN_EN_COK * kisa) {
    return fjson({ hata: "gorsel-gecersiz" }, 400);
  }

  if (await hizSiniriAsildi(request, env)) { return fjson({ hata: "cok-istek" }, 429); }
  const ip = request.headers.get("CF-Connecting-IP") || "yok";
  const ziyaretci = await ziyaretciOzeti(env, ip);
  const sayi = await onizlemeSayisi(env, ziyaretci, simdi);
  // Plaketle AYNI sayac (foto_isler): litofan haritasi da ziyaretcinin gunluk hakkindan duser.
  if (VERI.sinir_ziyaretci_24s <= sayi.kisi) {
    return fjson({ hata: "onizleme-siniri", sinir: VERI.sinir_ziyaretci_24s }, 429);
  }
  if (sayi.genel >= GUNLUK_ONIZLEME_TAVANI) { return fjson({ hata: "kapali" }, 503); }
  const botGecti = await botDogrula(request, env, g.turnstile_token);
  if (!botGecti) { return fjson({ hata: "bot-dogrulama" }, 403); }

  const isNo = yeniIsNo();
  await env.OZEL_DOSYA.put(onizlemeAnahtari(isNo), bayt, { httpMetadata: { contentType: "image/png" } });
  const onay = onayKaydi(VERI.onay_surum, simdi);
  await env.KATALOG.prepare(
    "INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih, kredi, onay_tarih, onay_surum)" +
    " VALUES (?, ?, ?, ?, ?, 'hazir', ?, 0, ?, ?)"
  ).bind(isNo, tur.kod, olcu, ziyaretci, simdiIso(simdi), simdiIso(simdi), onay.tarih, onay.surum).run();
  return fjson({ is: isNo, kalan: Math.max(0, VERI.sinir_ziyaretci_24s - sayi.kisi - 1),
                 gecerlilik_bitis: new Date(simdi + VERI.gecerlilik_saat * 3600 * 1000).toISOString() }, 200);
}

// ---------------------------------------------------------------- uc: /foto/durum + /foto/gorsel

function onizlemeAnahtari(isNo) { return "foto-onizleme/" + isNo + ".png"; }

async function isGetir(env, isNo) {
  return env.KATALOG.prepare(
    "SELECT is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, son_kontrol, hata" +
    " FROM foto_isler WHERE is_no = ?").bind(isNo).first();
}

/** Is satirini getirir; tablo yoksa null (bolum kapali). */
async function isGetirYoksaNull(env, isNo) {
  try { return await isGetir(env, isNo); } catch (e) {
    if (tabloYok(e)) { return null; }
    throw e;
  }
}

function durumYaniti(is) {
  if (is.asama === "hazir") {
    return fjson({ asama: "hazir", tur: is.tur, olcu_mm: is.olcu_mm,
                   gorsel: "/api/shop/foto/gorsel?is=" + is.is_no,
                   gecerlilik_bitis: new Date(Date.parse(is.hazir_tarih) +
                     VERI.gecerlilik_saat * 3600 * 1000).toISOString() }, 200);
  }
  if (is.asama === "basarisiz") {
    // Uretec reddi (koşucu `uretec-red:<kod>`): musteri metni manifestten (VERI.uretecRedMetni).
    if (typeof is.hata === "string" && is.hata.startsWith("uretec-red")) {
      return fjson({ asama: "basarisiz", hata: "uretec-red", metin: VERI.uretecRedMetni(is.hata) }, 200);
    }
    return fjson({ asama: "basarisiz",
                   hata: is.hata === "gorsel-uygun-degil" ? "gorsel-uygun-degil" : "uretilemedi" }, 200);
  }
  if (is.asama === "silindi") { return fjson({ asama: "suresi-doldu" }, 200); }
  if (is.ilerleme !== undefined) { return fjson({ asama: "onizleme", ilerleme: is.ilerleme }, 200); }
  return fjson({ asama: "onizleme" }, 200);
}

async function durumUcu(env, url, simdi) {
  const isNo = url.searchParams.get("is") || "";
  if (!IS_KALIBI.test(isNo)) { return fjson({ hata: "bulunamadi" }, 404); }
  const is = await isGetirYoksaNull(env, isNo);
  if (!is) { return fjson({ hata: "bulunamadi" }, 404); }
  // Ornek isi (panel) musteri ucunda YOK sayilir: varligi da sizmaz.
  if (ornekMi(is)) { return fjson({ hata: "bulunamadi" }, 404); }
  if (uretecOnizlemeTuru(is.tur)) { return uretecDurumYaniti(env, is); }
  return onizlemeIlerle(env, is, simdi, yapilandirma(env).hazir, durumYaniti);
}

/**
 * Onizleme gorevini yoklar ve hazirsa gorseli ozel kovaya indirir (musteri + ornek ORTAK).
 * `hazir`: ilgili kolun yapilandirmasi; `yanitla(is)`: kolun yanit bicimi.
 */
async function onizlemeIlerle(env, is, simdi, hazir, yanitla) {
  const isNo = is.is_no;
  if (is.asama !== "onizleme" || !is.gorev) { return yanitla(is); }
  if (simdi - (is.son_kontrol || 0) < DURUM_ARALIK_MS) { return yanitla(is); }
  if (!hazir || !saglayiciTuru(is.tur)) { return yanitla(is); }

  // CAS: ayni anda iki yoklama saglayiciya iki kez gitmesin.
  const kilit = await env.KATALOG.prepare(
    "UPDATE foto_isler SET son_kontrol = ? WHERE is_no = ? AND son_kontrol = ? AND asama = 'onizleme'"
  ).bind(simdi, isNo, is.son_kontrol || 0).run();
  if (!kilit || !kilit.meta || kilit.meta.changes !== 1) { return yanitla(is); }

  const c = await saglayici(env, "GET", turYolu(env, is.tur) + "/v1/prototype/" + is.gorev, null);
  if (c.kod !== 200 || !c.govde) { return yanitla(is); }
  const d = gorevDurumu(c.govde);
  if (d === "dustu") {
    await env.KATALOG.prepare(
      "UPDATE foto_isler SET asama = 'basarisiz', hata = 'uretilemedi' WHERE is_no = ? AND asama = 'onizleme'"
    ).bind(isNo).run();
    return yanitla({ ...is, asama: "basarisiz", hata: "uretilemedi" });
  }
  if (d !== "bitti") {
    const p = c.govde.progress;
    return yanitla({ ...is, ilerleme: Number.isInteger(p) ? p : null });
  }
  const adres = Array.isArray(c.govde.image_urls) ? c.govde.image_urls[0] : "";
  const dosya = await dosyaIndir(adres);
  if (!dosya) { return yanitla(is); }   // sonraki yoklama yeniden dener
  await env.OZEL_DOSYA.put(onizlemeAnahtari(isNo), dosya.tampon,
    { httpMetadata: { contentType: /png|jpeg|webp/.test(dosya.tip) ? dosya.tip : "image/png" } });
  const kredi = krediSayisi(c.govde);
  await env.KATALOG.prepare(
    "UPDATE foto_isler SET asama = 'hazir', hazir_tarih = ?, kredi = ? WHERE is_no = ? AND asama = 'onizleme'"
  ).bind(simdiIso(simdi), kredi, isNo).run();
  // Ornek onizlemesinin kredisi de deftere girer (siparis_no = uretimde kullanilacak ornek no).
  await krediYaz(env, simdi, "onizleme", isNo, ornekMi(is) ? ornekSiparisNo(isNo) : "", is.gorev, kredi);
  return yanitla({ ...is, asama: "hazir", hazir_tarih: simdiIso(simdi) });
}

/** Ozel kovadaki onizleme gorselinin yaniti (musteri + ornek ORTAK). */
async function onizlemeGorseli(env, isNo, anahtar) {
  const n = await env.OZEL_DOSYA.get(anahtar || onizlemeAnahtari(isNo));
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

async function gorselUcu(env, url) {
  const isNo = url.searchParams.get("is") || "";
  if (!IS_KALIBI.test(isNo) || !env.OZEL_DOSYA) { return fjson({ hata: "bulunamadi" }, 404); }
  const is = await isGetirYoksaNull(env, isNo);
  if (!is) { return fjson({ hata: "bulunamadi" }, 404); }
  // Ornek isinin gorseli musteri ucundan SUNULMAZ (panel ucu: /yonet/foto/ornek-gorsel).
  if (ornekMi(is)) { return fjson({ hata: "bulunamadi" }, 404); }
  // Uretec onizlemesi koşucunun R2 dizininde (onizleme.png); digerleri foto-onizleme/<is>.png.
  return onizlemeGorseli(env, isNo, uretecOnizlemeTuru(is.tur) ? uretecOnizlemeAnahtari(isNo, "onizleme.png") : "");
}

/** /api/shop/foto/* yonlendiricisi. */
export async function fotoUclari(request, env, url, yol, telegram) {
  const simdi = Date.now();
  const m = request.method;
  if (yol === "/foto/acik" && m === "GET") { return acikUcu(env, simdi, telegram); }
  if (yol === "/foto/onizleme" && m === "POST") { return onizlemeUcu(request, env, simdi, telegram); }
  if (yol === "/foto/litofan" && m === "POST") { return litofanUcu(request, env, simdi); }
  if (yol === "/foto/durum" && m === "GET") { return durumUcu(env, url, simdi); }
  if (yol === "/foto/gorsel" && m === "GET") { return gorselUcu(env, url); }
  if (yol === "/foto/konsept" && m === "POST") { return konseptUret(request, env, simdi, telegram, false); }
  if (yol === "/foto/konsept-durum" && m === "GET") { return konseptDurum(env, url, simdi, false); }
  if (yol === "/foto/konsept-gorsel" && m === "GET") { return konseptGorsel(env, url, false); }
  return fjson({ hata: "bulunamadi" }, 404);
}

// ---------------------------------------------------------------- /baslat kalemi

/** Kalemdeki renk/malzeme secimi: yalniz kisa dize alanlari tasinir (dogrulama fiyatlamada, kayda karsi). */
function secimSuz(s) {
  if (!s || typeof s !== "object" || Array.isArray(s)) { return null; }
  const cikti = {};
  for (const a of Object.keys(s).slice(0, 8)) {
    if (/^[a-z_]{1,30}$/.test(a) && typeof s[a] === "string" && s[a].length <= 40) { cikti[a] = s[a]; }
  }
  return cikti;
}

/**
 * Deterministik tur seciminin kayda karsi dogrulamasi: her renk bolgesi icin `<bolge>_renk`
 * (bolgede tek renk varsa o renk), her malzeme bolgesi icin `<bolge>_malzeme` listede OLMALI.
 * Gecersizse null.
 */
function secimDogrula(turKod, secim) {
  const t = VERI.turBul(turKod);
  if (!t) { return null; }
  const s = secim || {};
  const renk = {}, malzeme = {};
  for (const b of (t.renk_bolgeleri || [])) {
    const liste = Array.isArray(b.renkler) ? b.renkler : [];
    const d = s[b.kod + "_renk"] === undefined && liste.length === 1 ? liste[0] : s[b.kod + "_renk"];
    if (!liste.includes(d)) { return null; }
    renk[b.kod] = d;
  }
  for (const bolge of Object.keys(t.malzemeler || {})) {
    const d = s[bolge + "_malzeme"];
    if (!(t.malzemeler[bolge] || []).includes(d)) { return null; }
    malzeme[bolge] = d;
  }
  return { renk, malzeme };
}

/** Sepet kalemi bicimi: {foto_is, olcu_mm, adet[, secim]}. Gecersizse {hata}. */
export function fotoKalemCoz(k) {
  const isNo = typeof k.foto_is === "string" && IS_KALIBI.test(k.foto_is) ? k.foto_is : null;
  if (!isNo) { return { hata: "gecersiz-kalem" }; }
  const olcu = Number.isInteger(k.olcu_mm) ? k.olcu_mm : null;
  if (!olcu) { return { hata: "gecersiz-olcu" }; }
  const adet = Number.isInteger(k.adet) && k.adet >= 1 && k.adet <= FOTO_ADET_EN_COK ? k.adet : null;
  if (!adet) { return { hata: "gecersiz-adet" }; }
  // Secim yalniz deterministik turde okunur; plakette gelse de YOK SAYILIR (satir bugunkuyle ayni).
  const secim = secimSuz(k.secim);
  return { kalem: { foto_is: isNo, olcu_mm: olcu, adet, ...(secim ? { secim } : {}) } };
}

/**
 * FOTO KALEMINI FIYATLA — sunucu hesabi (istemcinin hicbir tutari okunmaz). Sartlar:
 * yapilandirma hazir · onizleme 'hazir' ve gecerlilik suresi icinde · tur acik (acilis anahtari) ·
 * olcu manifest araliginda ve adim izgarasinda. Birim fiyat TEK FORMULDEN (VERI.fiyatKurus);
 * istemcinin tutari OKUNMAZ. Donus {satir} ya da {hata:{...}, kod}.
 */
export async function fotoKalemFiyatla(env, k, simdi) {
  if (!yapilandirma(env).hazir && !DETERMINISTIK_TURLER.some((d) => turHazir(env, d).hazir)) {
    return { hata: { hata: "foto-kapali", mesaj: "Fotoğraftan üretim şu an alınamıyor." }, kod: 400 };
  }
  let is;
  try { is = await isGetir(env, k.foto_is); } catch (e) {
    if (tabloYok(e)) { return { hata: { hata: "foto-kapali" }, kod: 400 }; }
    throw e;
  }
  // Uretec onizlemeli tur YALNIZ koşucunun 'onizleme-hazir' yaptigi ise baglanir (kuyruk atlanamaz).
  const hazirAsama = is && uretecOnizlemeTuru(is.tur) ? "onizleme-hazir" : "hazir";
  if (!is || is.asama !== hazirAsama) { return { hata: { hata: "foto-onizleme-yok" }, kod: 400 }; }
  // Ornek isi (panel, odemesiz) sepette/odemede KABUL EDILMEZ; musteriye "yok" gibi gorunur.
  if (ornekMi(is)) { return { hata: { hata: "foto-onizleme-yok" }, kod: 400 }; }
  const yas = (simdi - Date.parse(is.hazir_tarih)) / 3600000;
  if (!(yas >= 0 && yas <= VERI.gecerlilik_saat)) {
    return { hata: { hata: "foto-onizleme-suresi-doldu",
                     mesaj: "Önizlemenin süresi doldu; yeni önizleme gerekiyor." }, kod: 400 };
  }
  // Turun kendi kolu hazir olmali (deterministik tur saglayici anahtari istemez).
  if (turSunuluyor(is.tur) && !turHazir(env, is.tur).hazir) { return { hata: { hata: "foto-kapali" }, kod: 400 }; }
  const tur = acikTurler(await acikAnahtari(env)).find((t) => t.kod === is.tur);
  if (!tur) { return { hata: { hata: "foto-kapali" }, kod: 400 }; }
  // TURETILMIS eksen: olcu = onizleme isinin KAYITLI (koşucunun olctugu) olcusu; istemcinin olcu_mm'si OKUNMAZ.
  const mm = VERI.olcuTuretilmis(tur.kod) ? is.olcu_mm : k.olcu_mm;
  const fk = VERI.fiyatKurus(tur.kod, mm);
  const olcu = fk > 0 ? { mm, fiyat_kurus: fk } : null;
  if (!olcu) { return { hata: { hata: "gecersiz-olcu" }, kod: 400 }; }
  const birim = olcu.fiyat_kurus;
  if (deterministikTur(tur.kod)) { return deterministikSatir(tur, olcu, k, is); }
  return {
    satir: {
      // id kalici urun sayfasi DEGIL (katalog disi kalem); id kalibi /^[a-z0-9-]+$/ korunur.
      id: "ozel-foto-" + tur.kod,
      baslik: "Fotoğrafından özel üretim — " + tur.ad + " (" + olcu.mm + " mm, ayaklı)",
      kategori: "Özel Üretim",
      gorsel: "",
      malzeme: "PLA",
      renk: "4 renk",
      renk_ozel: "",
      adet: k.adet,
      birim_kurus: birim,
      tutar_kurus: birim * k.adet,
      parametre_detay: olcu.mm + " mm · önizlemenin 4 renkli yorumu · ayak: " + AYAK_PLAKET_BASI,
      foto_is: is.is_no,
      foto_tur: tur.kod,
      olcu_mm: olcu.mm,
      olcu_kaynagi: olcuKaynagi(tur.kod),
      // URETIMDE UNUTULMASIN: plaket basina ayak (ayri parca, ayni plakada basilir).
      foto_ayak: AYAK_PLAKET_BASI,
    },
  };
}

/** Deterministik tur odeme satiri: renk/malzeme kalemin seciminden, kayittaki listelere karsi. */
function deterministikSatir(tur, olcu, k, is) {
  const sc = secimDogrula(tur.kod, k.secim);
  if (!sc) {
    return { hata: { hata: "gecersiz-secim", mesaj: "Renk ya da malzeme seçimi geçersiz." }, kod: 400 };
  }
  const bolgeler = [...new Set([...Object.keys(sc.malzeme), ...Object.keys(sc.renk)])];
  const kayit = VERI.turBul(tur.kod);
  const bolgeAdi = (b) => ((kayit.renk_bolgeleri || []).find((x) => x.kod === b) || {}).ad || b;
  const secim = {};
  for (const b of bolgeler) {
    if (sc.malzeme[b]) { secim[b + "_malzeme"] = sc.malzeme[b]; }
    if (sc.renk[b]) { secim[b + "_renk"] = sc.renk[b]; }
  }
  const birim = olcu.fiyat_kurus;
  return {
    satir: {
      id: "ozel-foto-" + tur.kod,
      baslik: "Fotoğrafından özel üretim — " + tur.ad + " (" + olcu.mm + " mm)",
      kategori: "Özel Üretim",
      gorsel: "",
      malzeme: sc.malzeme[bolgeler[0]] || "PLA",
      renk: bolgeler.filter((b) => sc.renk[b]).map((b) => bolgeAdi(b) + ": " + sc.renk[b]).join(" · "),
      renk_ozel: "",
      adet: k.adet,
      birim_kurus: birim,
      tutar_kurus: birim * k.adet,
      parametre_detay: olcu.mm + " mm · " + bolgeler.map((b) => bolgeAdi(b) + ": " +
        [sc.malzeme[b], sc.renk[b]].filter(Boolean).join(", ")).join(" · "),
      foto_is: is.is_no,
      foto_tur: tur.kod,
      olcu_mm: olcu.mm,
      olcu_kaynagi: olcuKaynagi(tur.kod),
      foto_kol: "deterministik",
      foto_secim: secim,
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
        turSunuluyor(k.foto_tur) && Number.isInteger(k.olcu_mm)) {
      cikti.push({ kalem: i, is_no: k.foto_is, tur: k.foto_tur, olcu_mm: k.olcu_mm,
                   ...(k.foto_secim && typeof k.foto_secim === "object" ? { secim: k.foto_secim } : {}) });
    }
  });
  return cikti;
}

/**
 * Odenmis siparislerdeki foto kalemlerini uretim kuyruguna alir (INSERT OR IGNORE). Saglayici
 * kolu 'build-baslat' ile, deterministik kol 'uretec-bekliyor' ile girer (zincir onu SECMEZ).
 * `yalnizDeterministik`: saglayici yapilandirmasi eksikken yalniz deterministik kalemler.
 */
async function odenenleriKuyrugaAl(env, simdi, yalnizDeterministik) {
  const r = await env.KATALOG.prepare(
    "SELECT siparis_no, urunler FROM siparisler WHERE durum IN ('odendi', 'uretimde')" +
    " AND tarih >= ? AND urunler LIKE '%\"foto_is\"%' ORDER BY id DESC LIMIT 50"
  ).bind(saatOnce(simdi, 24 * 7)).all();
  let eklenen = 0;
  for (const s of (r.results || [])) {
    for (const k of siparistekiFotoKalemleri(s.urunler)) {
      const det = deterministikTur(k.tur);
      if (yalnizDeterministik && !det) { continue; }
      // Aydinlatma onayi (damga + surum) is satirindan uretim satirina tasinir (ispat kaydi siparisle kalir).
      const y = await env.KATALOG.prepare(
        "INSERT OR IGNORE INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel, onay_tarih, onay_surum)" +
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?," +
        " COALESCE((SELECT onay_tarih FROM foto_isler WHERE is_no = ?), '')," +
        " COALESCE((SELECT onay_surum FROM foto_isler WHERE is_no = ?), ''))"
      ).bind(s.siparis_no, k.kalem, k.is_no, k.tur, k.olcu_mm, det ? "uretec-bekliyor" : "build-baslat",
             simdiIso(simdi), simdiIso(simdi), k.is_no, k.is_no).run();
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
  "analiz-kirmizi": "basılabilirlik analizi onarımdan sonra da KIRMIZI (renk adımı koşmadı)",
  "analiz-basarisiz": "basılabilirlik analizi tamamlanamadı",
  "onarim-basarisiz": "sızdırmazlık onarımı ya da yeniden doku üretilemedi",
  "renk-basarisiz": "4 renk ayrımı üretilemedi",
  "olcu-tutmadi": "3MF ölçüsü sipariş ölçüsüne getirilemedi (dosya depoya yazılmadı)",
  "indirme-basarisiz": "dosyalar depoya indirilemedi",
  "kredi-yetersiz": "kredi yetmedi (otomatik alım yok)",
  "saglayici-erisilemiyor": "sağlayıcıya tekrar tekrar ulaşılamadı",
  "tur-kapali": "bu tür artık sunulmuyor (elle bakılacak)",
};

/** Analiz ozetindeki alt kenar kalinligi (mm) ya da null (ozet yok/bozuk/olculmemis). */
function analizAltKenar(analiz) {
  try {
    const v = JSON.parse(analiz || "{}");
    return v && typeof v.alt_kenar_mm === "number" && v.alt_kenar_mm > 0 ? v.alt_kenar_mm : null;
  } catch (e) {
    return null;
  }
}

/** Analiz ozetine olcu kapisi sonucunu ekler (panel + kapanis okur). */
function analizOlcekli(analiz, olc) {
  let o = {};
  try { o = JSON.parse(analiz || "{}") || {}; } catch (e) { o = { ham: String(analiz).slice(0, 200) }; }
  o.olcek = olc.tampon ? olc.olcek : 0;
  o.L_once = olc.L_once == null ? null : olc.L_once;
  o.L_sonra = olc.L_sonra == null ? null : olc.L_sonra;
  o.z_mm = olc.z_mm == null ? null : olc.z_mm;
  // Ayak ureteci girdisi (TeKiN: `alt_kenar_mm`); olculemediyse null — panel bunu acikca gosterir.
  o.alt_kenar_mm = olc.alt_kenar_mm == null ? null : olc.alt_kenar_mm;
  if (olc.hata) { o.olcu_hata = olc.hata; }
  return JSON.stringify(o);
}

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

/** build_gorev zinciri: [model, onarim?, doku?] (bkz. dosya basi ONARIM). */
function zincir(u) { return String(u.build_gorev || "").split("~"); }

/** Renk adimina ve depoya giden model: onarilip dokulandiysa doku gorevi, degilse model gorevi. */
async function modelGorevi(env, u) {
  const z = zincir(u);
  if (z.length >= 3) { return saglayici(env, "GET", "/v1/retexture/" + z[2], null); }
  return saglayici(env, "GET", turYolu(env, u.tur) + "/v1/build/" + z[0], null);
}

/** Verilen modelin analizini baslatir; baslatilamazsa satir asamasinda KALIR (yeniden dener). */
async function analizBaslat(env, u, glb, simdi, telegram) {
  const a = await saglayici(env, "POST", "/v1/print/analyze", { model_url: glb });
  const ag = gorevKimligi(a.govde);
  if (a.kod >= 200 && a.kod < 300 && ag) { return asamaYaz(env, u, "analiz", { analiz_gorev: ag }, simdi); }
  return hataKolu(a.kod) === "gecici" ? gecici(env, u, simdi, telegram)
    : elleDusur(env, u, "analiz-basarisiz", "", simdi, telegram);
}

/** YALNIZ yesil analizden cagrilir: analiz edilen modelin 4 renk ayrimini baslatir. */
async function renkBaslat(env, u, ozet, simdi, telegram) {
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

/** Saglayici baslatma yanitini asamaya cevirir (onarim/doku): 402 kredi, red elle, gerisi gecici. */
async function baslatildi(env, u, c, yeni, alanlar, ozet, simdi, telegram) {
  const id = gorevKimligi(c.govde);
  if (c.kod >= 200 && c.kod < 300 && id) { return asamaYaz(env, u, yeni, alanlar(id), simdi); }
  const kol = hataKolu(c.kod);
  if (kol === "kredi") { return elleDusur(env, u, "kredi-yetersiz", ozet, simdi, telegram); }
  if (kol === "red") { return elleDusur(env, u, "onarim-basarisiz", ozet, simdi, telegram); }
  return gecici(env, u, simdi, telegram);
}

/** Tek uretim satirini BIR adim ilerletir. */
async function uretimAdimi(env, u, simdi, telegram) {
  // Sunulmayan tur satiri saglayiciya HIC gitmez; sessiz donmez, 'elle'ye sebebiyle duser.
  // Saglayici kolu disindaki satir zincire DUSMEMELI; dustuyse saglayiciya gitmeden 'elle'.
  if (!saglayiciTuru(u.tur)) { return elleDusur(env, u, "tur-kapali", "", simdi, telegram); }
  if (u.asama === "build-baslat") {
    const is = await isGetir(env, u.is_no);
    if (!is || is.asama !== "hazir" || !is.gorev) { return elleDusur(env, u, "onizleme-yok", "", simdi, telegram); }
    if ((simdi - Date.parse(is.hazir_tarih)) / 3600000 > ONIZLEME_KURULUM_SINIRI_SAAT) {
      return elleDusur(env, u, "onizleme-suresi-doldu", "", simdi, telegram);
    }
    const c = await saglayici(env, "POST", turYolu(env, u.tur) + "/v1/build", {
      input_task_id: is.gorev,
      name: "pruvo-" + u.siparis_no,
      // Plaket: duz kapali sirt + sabit kabartma/taban (ayak yuvasi bu tabana gore) — delme yok.
      options: { size_mm: u.olcu_mm, relief_height_mm: PLAKET_KABARTMA_MM,
                 base_thickness_mm: PLAKET_TABAN_MM, has_closed_back: true, badge_shape: PLAKET_SEKIL },
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
    // Analiz baslatilamadiysa satir 'build'de KALIR (bir sonraki tur yeniden dener).
    return analizBaslat(env, u, glb, simdi, telegram);
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
      // Deneme tavani: satir basina TEK onarim. Onarilmis modelin analizi de kirmiziysa elle.
      if (zincir(u).length >= 2) {
        return elleDusur(env, u, "analiz-kirmizi", ozet, simdi, telegram);
      }
      const m = await modelGorevi(env, u);
      const glb = m.kod === 200 && m.govde && m.govde.model_urls && m.govde.model_urls.glb;
      if (!glb) { return gecici(env, u, simdi, telegram); }
      const o = await saglayici(env, "POST", "/v1/print/repair", { model_url: glb });
      return baslatildi(env, u, o, "onarim",
                        (id) => ({ build_gorev: zincir(u)[0] + "~" + id, analiz: ozet }), ozet, simdi, telegram);
    }
    return renkBaslat(env, u, ozet, simdi, telegram);
  }

  if (u.asama === "onarim") {
    const z = zincir(u);
    const c = await saglayici(env, "GET", "/v1/print/repair/" + z[1], null);
    if (c.kod !== 200 || !c.govde) { return gecici(env, u, simdi, telegram); }
    const d = gorevDurumu(c.govde);
    if (d === "surdu") { return false; }
    if (d !== "bitti") { return elleDusur(env, u, "onarim-basarisiz", "", simdi, telegram); }
    await krediYaz(env, simdi, "onarim", u.is_no, u.siparis_no, z[1], krediSayisi(c.govde));
    const glb = c.govde.model_urls && c.govde.model_urls.glb;
    if (!glb) { return elleDusur(env, u, "onarim-basarisiz", "", simdi, telegram); }
    // Onarim dokuyu siler; renk adimi dokusuz modeli reddeder -> musterinin onizleme
    // gorseliyle yeniden doku (gorsel adresi sureli: her seferinde tazesi alinir).
    const is = await isGetir(env, u.is_no);
    if (!is || !is.gorev) { return elleDusur(env, u, "onizleme-yok", "", simdi, telegram); }
    const p = await saglayici(env, "GET", turYolu(env, u.tur) + "/v1/prototype/" + is.gorev, null);
    const gorsel = p.kod === 200 && p.govde && Array.isArray(p.govde.image_urls) && p.govde.image_urls[0];
    if (!gorsel) {
      return hataKolu(p.kod) === "gecici" ? gecici(env, u, simdi, telegram)
        : elleDusur(env, u, "onarim-basarisiz", "", simdi, telegram);
    }
    const t = await saglayici(env, "POST", "/v1/retexture", { model_url: glb, image_style_url: gorsel });
    return baslatildi(env, u, t, "doku",
                      (id) => ({ build_gorev: z[0] + "~" + z[1] + "~" + id }), "", simdi, telegram);
  }

  if (u.asama === "doku") {
    const z = zincir(u);
    const c = await saglayici(env, "GET", "/v1/retexture/" + z[2], null);
    if (c.kod !== 200 || !c.govde) { return gecici(env, u, simdi, telegram); }
    const d = gorevDurumu(c.govde);
    if (d === "surdu") { return false; }
    if (d !== "bitti") { return elleDusur(env, u, "onarim-basarisiz", "", simdi, telegram); }
    await krediYaz(env, simdi, "doku", u.is_no, u.siparis_no, z[2], krediSayisi(c.govde));
    const dokuGlb = c.govde.model_urls && c.govde.model_urls.glb;
    if (!dokuGlb) { return elleDusur(env, u, "onarim-basarisiz", "", simdi, telegram); }
    // Onarilmis + dokulu model YENIDEN analiz edilir; yesil degilse renk KOSMAZ.
    return analizBaslat(env, u, dokuGlb, simdi, telegram);
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
    // OLCU KAPISI (onarimli + onarimsiz HER yol buradan gecer): olcu tutmazsa R2'ye YAZILMAZ.
    const olc = await ucmfOlcekle(ucmf.tampon, u.olcu_mm);
    const ozet = analizOlcekli(u.analiz, olc);
    if (!olc.tampon) { return elleDusur(env, u, "olcu-tutmadi", ozet, simdi, telegram); }
    await env.OZEL_DOSYA.put(uretimAnahtari(u.siparis_no, u.kalem, "3mf"), olc.tampon,
                             { httpMetadata: { contentType: "model/3mf" } });
    await env.OZEL_DOSYA.put(uretimAnahtari(u.siparis_no, u.kalem, "glb"), glb.tampon,
                             { httpMetadata: { contentType: "model/gltf-binary" } });
    const tasindi = await asamaYaz(env, u, "hazir", { analiz: ozet }, simdi);
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
    "SELECT is_no, tur FROM foto_isler WHERE asama IN ('hazir', 'onizleme', 'basarisiz', 'uretec-onizleme'," +
    " 'onizleme-hazir') AND tarih < ?" +
    " AND is_no NOT IN (SELECT is_no FROM foto_uretim) LIMIT 50"
  ).bind(saatOnce(simdi, ONIZLEME_SAKLAMA_SAAT)).all();
  let silinen = 0;
  for (const s of (r.results || [])) {
    await env.OZEL_DOSYA.delete(onizlemeAnahtari(s.is_no));
    if (uretecOnizlemeTuru(s.tur)) {
      for (const ad of URETEC_DIZIN_ADLARI) { await env.OZEL_DOSYA.delete(uretecOnizlemeAnahtari(s.is_no, ad)); }
    }
    await env.KATALOG.prepare(
      "UPDATE foto_isler SET asama = 'silindi' WHERE is_no = ?").bind(s.is_no).run();
    silinen++;
  }
  // 2D konsept gorselleri AYNI 3 gun kuralina bagli (tablo yoksa 0; onizleme temizligini DURDURMAZ).
  return silinen + await konseptTemizle(env, simdi);
}

/**
 * CRON KOLU — uretim zincirini yurutur. Yapilandirma eksikse saglayici zinciri KOSMAZ;
 * yalniz deterministik kuyruk + onizleme temizligi (saklama kurali) koşar.
 * Donus olcum ozeti (log + test): {kuyruga, ilerleyen, silinen}.
 */
export async function fotoUretimTuru(env, simdi, telegram) {
  const ozet = { kuyruga: 0, ilerleyen: 0, silinen: 0, atlandi: "" };
  if (!env || !env.KATALOG || !env.OZEL_DOSYA || !env.URETIM_API_ANAHTAR || !env.URETIM_API_TABAN ||
      !env.URETIM_TUR_ONEK || !saglayiciYoluVar(env)) {
    ozet.atlandi = "yapilandirma";
    // Deterministik kol saglayicisizdir: odenen kalemleri yine kuyruga alir (zincir KOSMAZ,
    // ozet saglayici kolu icin bugunkuyle ayni kalir).
    if (env && env.KATALOG && env.OZEL_DOSYA) {
      if (DETERMINISTIK_TURLER.length) {
        try { await odenenleriKuyrugaAl(env, simdi, true); } catch (e) { if (!tabloYok(e)) { throw e; } }
      }
      // Saklama kurali saglayicidan bagimsizdir (onay metni: en gec 3 gun) — litofan haritasi da silinir.
      try { ozet.silinen = await onizlemeTemizle(env, simdi); } catch (e) { if (!tabloYok(e)) { throw e; } }
    }
    return ozet;
  }
  try {
    ozet.kuyruga = await odenenleriKuyrugaAl(env, simdi);
    const r = await env.KATALOG.prepare(
      "SELECT siparis_no, kalem, is_no, tur, olcu_mm, asama, build_gorev, analiz_gorev, renk_gorev," +
      " analiz, deneme FROM foto_uretim WHERE asama NOT IN ('hazir', 'elle', 'uretec-bekliyor')" +
      " ORDER BY guncel LIMIT ?"
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
  const det = deterministikTur(k.foto_tur);
  const q = "?siparis=" + encodeURIComponent(siparisNo) + "&kalem=" + i;
  // DETERMINISTIK KOL: secim (malzeme/renk) + uretec girdisi indir + 3MF yukle; dosya yalniz 3MF.
  const ek = det ? {
    kol: "deterministik",
    secim: k.foto_secim && typeof k.foto_secim === "object" ? k.foto_secim : {},
    uretec: { girdi: "/api/shop/yonet/foto/uretec-girdi" + q, yukle: "/api/shop/yonet/foto/uretec-yukle" + q },
  } : {};
  return {
    is_no: k.foto_is,
    tur: k.foto_tur || "",
    olcu_mm: k.olcu_mm || 0,
    // Plaket basina ayak; siparis kaydinda yoksa da varsayilan basilir (sessiz eksik yok).
    ayak: Number.isInteger(k.foto_ayak) && k.foto_ayak > 0 ? k.foto_ayak : AYAK_PLAKET_BASI,
    asama: u ? u.asama : "kuyrukta-degil",
    sebep: u ? (ELLE_METNI[u.sebep] || u.sebep || "") : "",
    analiz: u ? (u.analiz || "") : "",
    // Plaket ayak ureteci girdisi (analiz ozetinden; olculmediyse null).
    alt_kenar_mm: u ? analizAltKenar(u.analiz) : null,
    onizleme: taban + "&bicim=onizleme",
    dosyalar: u && u.asama === "hazir"
      ? (det ? { "3mf": taban + "&bicim=3mf" } : { "3mf": taban + "&bicim=3mf", "glb": taban + "&bicim=glb" }) : null,
    // Onizleme kredisi is_no'ya, uretim kredileri siparis_no'ya yazilir; panel ikisini toplar.
    kredi_uretim: harita.get("kredi|" + siparisNo) || 0,
    ...ek,
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
  let k;
  if (no.startsWith(ORNEK_SIPARIS_ONEK)) {
    // ORNEK uretimi siparissizdir: kalem uretim satirindan, yalniz ornek isaretli istan.
    k = await env.KATALOG.prepare(
      "SELECT u.kalem, u.is_no, u.tur, u.olcu_mm FROM foto_uretim u JOIN foto_isler i ON i.is_no = u.is_no" +
      " WHERE u.siparis_no = ? AND u.kalem = ? AND i.ziyaretci = ?"
    ).bind(no, kalem, ORNEK_ZIYARETCI).first();
  } else {
    const s = await env.KATALOG.prepare(
      "SELECT urunler FROM siparisler WHERE siparis_no = ?").bind(no).first();
    k = s && siparistekiFotoKalemleri(s.urunler).find((x) => x.kalem === kalem);
  }
  if (!k) { return fjson({ hata: "kalem-yok" }, 404); }
  // Deterministik kalemin uretim dosyasi yalniz 3MF'tir (GLB uretilmez).
  if (bicim === "glb" && deterministikTur(k.tur)) { return fjson({ hata: "dosya-yok" }, 404); }
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

/** Panel uretec uclari icin kalem cozumu: musteri siparisindeki DETERMINISTIK foto kalemi. */
async function uretecKalemi(env, url) {
  const no = url.searchParams.get("siparis") || "";
  const kalem = parseInt(url.searchParams.get("kalem") || "", 10);
  if (!SIPARIS_KALIBI.test(no) || !Number.isInteger(kalem) || kalem < 0 || !env.OZEL_DOSYA || !env.KATALOG) {
    return { yanit: fjson({ hata: "gecersiz" }, 400) };
  }
  const s = await env.KATALOG.prepare("SELECT urunler FROM siparisler WHERE siparis_no = ?").bind(no).first();
  const k = s && siparistekiFotoKalemleri(s.urunler).find((x) => x.kalem === kalem);
  if (!k) { return { yanit: fjson({ hata: "kalem-yok" }, 404) }; }
  if (!deterministikTur(k.tur)) { return { yanit: fjson({ hata: "uretec-kalemi-degil" }, 400) }; }
  return { no, kalem, k };
}

/** Uretec kopru dosyalarinin R2 anahtari (ozel kova; model.3mf ile ayni dizin). */
export function uretecAnahtari(siparisNo, kalem, ad) { return "foto/" + siparisNo + "/" + kalem + "/" + ad; }

/** Sozlesme §2 girdi.json — kalemin seciminden (renk/malzeme) + manifest bolgelerinden. */
export function uretecGirdiJson(no, k) {
  const t = VERI.turBul(k.tur) || {};
  const sc = k.secim || {};
  const renkler = {}, malzemeler = {};
  for (const b of (t.renk_bolgeleri || [])) { if (sc[b.kod + "_renk"]) { renkler[b.kod] = sc[b.kod + "_renk"]; } }
  for (const b of Object.keys(t.malzemeler || {})) { if (sc[b + "_malzeme"]) { malzemeler[b] = sc[b + "_malzeme"]; } }
  return { sozlesme: 1, kategori: k.tur, siparis_no: no, kalem: k.kalem, olcu_mm: k.olcu_mm,
           renkler, malzemeler, parametreler: k.parametreler || {}, dosyalar: { gri_harita: "gri_harita.png" } };
}

/**
 * GET /yonet/foto/uretec-girdi?siparis=&kalem=[&dosya=girdi.json|gri_harita.png] — uretecin girdisi
 * (sozlesme §2/§4). `dosya` yoksa gri harita PNG (panel "girdi indir" baglantisi, geriye uyumlu).
 */
export async function panelUretecGirdi(env, url) {
  const c = await uretecKalemi(env, url);
  if (c.yanit) { return c.yanit; }
  const dosya = url.searchParams.get("dosya") || "gri_harita.png";
  if (dosya === "girdi.json") {
    return new Response(JSON.stringify(uretecGirdiJson(c.no, c.k)), { status: 200, headers: {
      "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
  }
  if (dosya !== "gri_harita.png") { return fjson({ hata: "dosya-yok" }, 404); }
  const n = await env.OZEL_DOSYA.get(onizlemeAnahtari(c.k.is_no));
  if (!n) { return fjson({ hata: "dosya-yok" }, 404); }
  return new Response(n.body, {
    status: 200,
    headers: {
      "Content-Type": "image/png",
      "Content-Disposition": "attachment; filename=\"" + c.no + "-" + c.kalem + "-" + c.k.tur + "-" +
        c.k.olcu_mm + "mm-girdi.png\"",
      "Cache-Control": "no-store",
    },
  });
}

/** Uzun kenar toleransi (sozlesme §3): D kolu ±%1, R kolu ±%3. */
const UZUN_KENAR_TOLERANS = { D: 0.01, R: 0.03 };
/** Plaka siniri (sozlesme §3, mm) — TEK kaynak manifest `PLAKA_MM` (7 Eki: 300); yoksa yukleme durur. */
const PLAKA_MM = VERI.PLAKA_MM;
if (!(typeof PLAKA_MM === "number" && PLAKA_MM > 0)) { throw new Error("foto-uretim-veri.js PLAKA_MM yok/bozuk"); }

/**
 * olcu.json DOGRULAMASI (sozlesme §3 + manifest araligi). Donus "" = gecerli, aksi sebep kodu
 * (siparis 'elle'ye duser). `sizdirmaz` true OLMAK ZORUNDA; uzun kenar (sinir kutusunun en uzun
 * boyutu, x/y/z) = olcu_mm ± tolerans ve kutu Z'sinden kucuk degil;
 * renk 1..4; olcu_mm manifest araliginda; kutu plakada.
 */
export function uretecOlcuDogrula(o, k) {
  const t = VERI.turBul(k.tur);
  if (!o || typeof o !== "object" || Array.isArray(o) || o.sozlesme !== 1) { return "olcu-bozuk"; }
  if (o.kategori !== k.tur || !t) { return "kategori-uyusmaz"; }
  if (o.sizdirmaz !== true) { return "sizdirmaz-degil"; }
  const a = VERI.olcuAraligi(k.tur);
  if (!a || !(k.olcu_mm >= a.en_az && k.olcu_mm <= a.en_cok)) { return "olcu-aralik-disi"; }
  const tol = UZUN_KENAR_TOLERANS[t.motor];
  // TURETILMIS eksen: hedef yok -> olculen uzun kenar KAYITLI araliga duser mi (koşucu cikti_dogrula ile ayni).
  const turetilmis = VERI.olcuTuretilmis(k.tur);
  const olculen = VERI.olculenMm(o.uzun_kenar_mm);
  // uzun_kenar_mm = nesnenin sinir kutusunun EN UZUN boyutu (x/y/z, ayak dahil; sozlesme §3) = olcu_mm ± tol.
  // kutu_mm PLAKA yerlesimidir (yapboz parcalari yan yana: x/y nesneden buyuk olabilir), Z ise nesnenin
  // yuksekligidir: Z en uzun boyuttan buyukse uzun kenar yalniz X/Y'den olculmus demektir -> RED.
  const kz = Number((o.kutu_mm || {}).z) || 0;
  if (!(tol > 0) || typeof o.uzun_kenar_mm !== "number" ||
      (turetilmis ? !(olculen >= a.en_az && olculen <= a.en_cok)
        : !(Math.abs(o.uzun_kenar_mm - k.olcu_mm) <= k.olcu_mm * tol + 1e-9)) ||
      kz > o.uzun_kenar_mm * (1 + tol) + 1e-9) { return "uzun-kenar-tolerans"; }
  if (!Number.isInteger(o.renk_sayisi) || o.renk_sayisi < 1 || o.renk_sayisi > 4) { return "renk-fazla"; }
  const kutu = o.kutu_mm || {};
  if (!(kutu.x > 0 && kutu.y > 0 && kutu.x <= PLAKA_MM && kutu.y <= PLAKA_MM)) { return "plaka-disi"; }
  return "";
}

/**
 * POST /yonet/foto/uretec-yukle?siparis=&kalem=[&dosya=model.3mf|olcu.json|onizleme.png] — sozlesme §4.
 * Yalniz 'uretec-bekliyor' satirina. olcu.json (JSON, <= 64 KB) ve onizleme.png (PNG, uzun kenar
 * >= 1024 px) R2'ye yazilir, asama DEGISMEZ. model.3mf (zip imzasi, <= DOSYA_EN_COK_BAYT) yazilir ve
 * karar verilir: olcu.json + onizleme.png var ve olcu §3'ten geciyor -> CAS ile 'hazir'; aksi
 * 'elle' + sebep (olcu-yok · onizleme-yok · sizdirmaz-degil · uzun-kenar-tolerans · ...).
 * Yanlis asama 409, bozuk dosya 400. Yetki: yonet.js anahtar/cerez kapisinin ARKASINDA.
 */
export async function panelUretecYukle(request, env, url, simdi) {
  const c = await uretecKalemi(env, url);
  if (c.yanit) { return c.yanit; }
  const dosya = url.searchParams.get("dosya") || "model.3mf";
  if (!["model.3mf", "olcu.json", "onizleme.png"].includes(dosya)) { return fjson({ hata: "dosya-yok" }, 400); }
  const u = await env.KATALOG.prepare(
    "SELECT siparis_no, kalem, asama, tur, olcu_mm FROM foto_uretim WHERE siparis_no = ? AND kalem = ?"
  ).bind(c.no, c.kalem).first();
  if (!u || u.asama !== "uretec-bekliyor") {
    return fjson({ hata: "asama-uygun-degil", asama: u ? u.asama : "kuyrukta-degil" }, 409);
  }
  const beyan = parseInt(request.headers.get("Content-Length") || "0", 10);
  if (beyan > DOSYA_EN_COK_BAYT) { return fjson({ hata: "dosya-buyuk" }, 400); }
  let bayt;
  try { bayt = new Uint8Array(await request.arrayBuffer()); } catch (e) { return fjson({ hata: "gecersiz-dosya" }, 400); }
  if (dosya === "olcu.json") {
    let o = null;
    try { o = bayt.length <= 65536 ? JSON.parse(new TextDecoder().decode(bayt)) : null; } catch (e) { o = null; }
    if (!o || typeof o !== "object") { return fjson({ hata: "olcu-bozuk" }, 400); }
    await env.OZEL_DOSYA.put(uretecAnahtari(c.no, c.kalem, "olcu.json"), bayt,
                             { httpMetadata: { contentType: "application/json" } });
    return fjson({ ok: true, dosya, asama: u.asama }, 200);
  }
  if (dosya === "onizleme.png") {
    const b = pngBoyut(bayt);
    if (!b || bayt.length > DOSYA_EN_COK_BAYT || Math.max(b.en, b.boy) < 1024) { return fjson({ hata: "gecersiz-onizleme" }, 400); }
    await env.OZEL_DOSYA.put(uretecAnahtari(c.no, c.kalem, "onizleme.png"), bayt,
                             { httpMetadata: { contentType: "image/png" } });
    return fjson({ ok: true, dosya, asama: u.asama }, 200);
  }
  if (bayt.length < 22 || bayt.length > DOSYA_EN_COK_BAYT ||
      bayt[0] !== 0x50 || bayt[1] !== 0x4B || bayt[2] !== 0x03 || bayt[3] !== 0x04) {
    return fjson({ hata: "gecersiz-3mf" }, 400);
  }
  await env.OZEL_DOSYA.put(uretimAnahtari(c.no, c.kalem, "3mf"), bayt,
                           { httpMetadata: { contentType: "model/3mf" } });
  const on = await env.OZEL_DOSYA.get(uretecAnahtari(c.no, c.kalem, "onizleme.png"));
  const ob = await env.OZEL_DOSYA.get(uretecAnahtari(c.no, c.kalem, "olcu.json"));
  let sebep = "";
  if (!ob) { sebep = "olcu-yok"; } else if (!on) { sebep = "onizleme-yok"; } else {
    let o = null;
    try { o = JSON.parse(await new Response(ob.body).text()); } catch (e) { o = null; }
    sebep = uretecOlcuDogrula(o, c.k);
  }
  if (sebep) {
    await elleDusur(env, u, sebep, "", simdi);
    return fjson({ ok: false, asama: "elle", sebep, bayt: bayt.length }, 422);
  }
  if (!(await asamaYaz(env, u, "hazir", {}, simdi))) {
    return fjson({ hata: "asama-uygun-degil" }, 409);
  }
  return fjson({ ok: true, asama: "hazir", bayt: bayt.length }, 200);
}

/**
 * GET /yonet/foto-ozet — "hata cok mu" sorusunun SAYISI (8. madde): tur basina siparis
 * kalemi ↔ elle bakilacak; aylik kredi; havuz; acilis anahtari; yapilandirma eksikleri.
 */
export async function panelFotoOzet(env, simdi) {
  const y = yapilandirma(env);
  const cikti = { yapilandirma: y, turler: [], kredi: { bu_ay: 0, gecen_ay: 0 }, bakiye: null,
                  acik: [], fiyat_formulu: "en uzun boyut (mm) × 10 TL", onay_onayli: VERI.onay_onayli === true, onay_surum: VERI.onay_surum,
                  ornek: VERI.turler.map((t) => ({ tur: t.kod, sayi: VERI.ornekSayisi(t.kod) })),
                  sunulan_turler: VERI.turler.filter((t) => turSunuluyor(t.kod))
                    .map((t) => ({ kod: t.kod, ad: t.ad, kol: VERI.kolu(t.kod),
                                   olcu_en_az: olcuAraligi(t.kod).en_az, olcu_en_cok: olcuAraligi(t.kod).en_cok,
                                   olcu_adim: VERI.olcuAdimi(t.kod),
                                   fiyat_en_az_kurus: VERI.fiyatKurus(t.kod, olcuAraligi(t.kod).en_az) })),
                  olcu_en_az: OLCU_MM_EN_AZ, olcu_en_cok: OLCU_MM_EN_COK,
                  ayak_plaket_basi: AYAK_PLAKET_BASI,
                  elle: [], sema: true };
  try {
    const t = await env.KATALOG.prepare(
      "SELECT tur, COUNT(*) AS kalem, SUM(asama = 'hazir') AS hazir, SUM(asama = 'elle') AS elle" +
      " FROM foto_uretim WHERE siparis_no NOT LIKE '" + ORNEK_SIPARIS_ONEK + "%' GROUP BY tur").all();
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
    cikti.acik = [...(await acikAnahtari(env))].sort();
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

/**
 * POST /yonet/foto-acik {tur, acik} — turun ACILIS ANAHTARI (fiyat tablosunun yerine; fiyat formulden).
 * acik true -> satir acik=1; false -> satir SILINIR (varsayilan KAPALI). Bilinmeyen tur 400.
 */
export async function panelFotoAcik(request, env, simdi) {
  let g;
  try { g = await request.json(); } catch (e) { return fjson({ hata: "gecersiz-json" }, 400); }
  const tur = g && turSunuluyor(g.tur) ? g.tur : null;
  if (!tur) { return fjson({ hata: "gecersiz-tur" }, 400); }
  if (typeof g.acik !== "boolean") { return fjson({ hata: "gecersiz-acik" }, 400); }
  if (g.acik) {
    await env.KATALOG.prepare(
      "INSERT INTO foto_acik (tur, acik, guncel) VALUES (?, 1, ?)" +
      " ON CONFLICT(tur) DO UPDATE SET acik = 1, guncel = excluded.guncel"
    ).bind(tur, simdiIso(simdi)).run();
  } else {
    await env.KATALOG.prepare("DELETE FROM foto_acik WHERE tur = ?").bind(tur).run();
  }
  return fjson({ ok: true, tur, acik: g.acik }, 200);
}

// ---------------------------------------------------------------- panel: ORNEK URETIM

/** Ornek isinin siparissiz uretim numarasi (kalem 0). */
export function ornekSiparisNo(isNo) { return ORNEK_SIPARIS_ONEK + String(isNo).slice(0, 12); }

function ornekDurumYaniti(is) {
  const v = { is: is.is_no, tur: is.tur, olcu_mm: is.olcu_mm, asama: is.asama };
  if (is.asama === "hazir") { v.gorsel = "/api/shop/yonet/foto/ornek-gorsel?is=" + is.is_no; }
  if (is.asama === "basarisiz") { v.hata = is.hata || "uretilemedi"; }
  if (is.ilerleme !== undefined) { v.ilerleme = is.ilerleme; }
  return fjson(v, 200);
}

/** Ornek isini getirir; musteri isi ya da yok -> null (panel ornek uclari musteri isine DOKUNMAZ). */
async function ornekIsGetir(env, isNo) {
  if (!IS_KALIBI.test(isNo || "")) { return null; }
  const is = await isGetirYoksaNull(env, isNo);
  return ornekMi(is) ? is : null;
}

/**
 * POST /yonet/foto/ornek-onizleme {gorsel, olcu_mm, tur?} — musteri ucuyla AYNI saglayici
 * cagrisi + `foto_isler` satiri; ziyaretci siniri / bot / onay / gercek-ornek kapisi ATLANIR.
 * Anahtar/taban/tur yolu yoksa 503 (saglayiciya istek 0); havuz esigi AYNEN uygulanir.
 */
export async function panelOrnekOnizleme(request, env, simdi, telegram) {
  const y = ornekYapilandirma(env);
  if (!y.hazir) { return fjson({ hata: "kapali", eksik: y.eksik }, 503); }
  let g;
  try { g = await request.json(); } catch (e) { return fjson({ hata: "gecersiz-istek" }, 400); }
  if (!g || typeof g !== "object") { return fjson({ hata: "gecersiz-istek" }, 400); }
  const tur = g.tur === undefined ? Object.keys(TUR_ORTAM)[0] : (saglayiciTuru(g.tur) ? g.tur : null);
  if (!tur) { return fjson({ hata: "gecersiz-tur" }, 400); }
  if (!turYoluVar(env, tur)) { return fjson({ hata: "kapali", eksik: ["tur-yolu-" + tur] }, 503); }
  const olcu = Number.isInteger(g.olcu_mm) && g.olcu_mm >= OLCU_MM_EN_AZ && g.olcu_mm <= OLCU_MM_EN_COK
    ? g.olcu_mm : null;
  // Olcu satilabilir olculerden biri olmali (ornek, satilan urunun aynisi olsun; formul gecerli).
  if (!olcu || !(VERI.fiyatKurus(tur, olcu) > 0)) {
    return fjson({ hata: "gecersiz-olcu" }, 400);
  }
  const gorsel = g.konsept !== undefined ? await konseptGirdisi(env, g.konsept, tur, true) : gorselCoz(g.gorsel);
  if (!gorsel) { return fjson({ hata: g.konsept !== undefined ? "konsept-gecersiz" : "gorsel-gecersiz" }, 400); }
  const havuz = await havuzHukmu(env, simdi, telegram);
  if (!havuz.acik) {
    return fjson({ hata: "havuz-esikte", bakiye: havuz.bakiye, gereken: havuz.gereken }, 503);
  }
  const isNo = yeniIsNo();
  const hata = await onizlemeGonder(env, isNo, tur, olcu, ORNEK_ZIYARETCI, gorsel.uri, simdi, telegram);
  if (hata) { return hata; }
  if (gorsel.konsept) { await konseptBagla(env, gorsel.konsept, isNo); }
  return fjson({ is: isNo }, 200);
}

/** GET /yonet/foto/ornek-durum?is= — onizlemeyi yoklar (musteri durum ucuyla ayni zincir). */
export async function panelOrnekDurum(env, url, simdi) {
  const is = await ornekIsGetir(env, url.searchParams.get("is"));
  if (!is) { return fjson({ hata: "bulunamadi" }, 404); }
  return onizlemeIlerle(env, is, simdi, ornekYapilandirma(env).hazir, ornekDurumYaniti);
}

/** GET /yonet/foto/ornek-gorsel?is= — ornek onizleme gorseli (yalniz ornek isi). */
export async function panelOrnekGorsel(env, url) {
  if (!env.OZEL_DOSYA) { return fjson({ hata: "bulunamadi" }, 404); }
  const is = await ornekIsGetir(env, url.searchParams.get("is"));
  if (!is) { return fjson({ hata: "bulunamadi" }, 404); }
  return onizlemeGorseli(env, is.is_no);
}

/**
 * POST /yonet/foto/ornek-uret {is} — 'hazir' ornek isi icin `foto_uretim`e SIPARISSIZ satir
 * (siparis_no = ORNEK-<is ilk 12>, kalem 0). Zinciri mevcut cron AYNEN yurutur; kredi defteri
 * cron'da bu numarayla yazilir. Musteri isi bu yoldan uretilemez (404).
 */
export async function panelOrnekUret(request, env, simdi, telegram) {
  const y = ornekYapilandirma(env);
  if (!y.hazir) { return fjson({ hata: "kapali", eksik: y.eksik }, 503); }
  let g;
  try { g = await request.json(); } catch (e) { return fjson({ hata: "gecersiz-istek" }, 400); }
  const is = await ornekIsGetir(env, g && g.is);
  if (!is) { return fjson({ hata: "bulunamadi" }, 404); }
  if (is.asama !== "hazir" || !is.gorev) { return fjson({ hata: "onizleme-hazir-degil" }, 409); }
  if ((simdi - Date.parse(is.hazir_tarih)) / 3600000 > ONIZLEME_KURULUM_SINIRI_SAAT) {
    return fjson({ hata: "onizleme-suresi-doldu" }, 409);
  }
  if (!saglayiciTuru(is.tur)) { return fjson({ hata: "gecersiz-tur" }, 400); }
  const havuz = await havuzHukmu(env, simdi, telegram);
  if (!havuz.acik) {
    return fjson({ hata: "havuz-esikte", bakiye: havuz.bakiye, gereken: havuz.gereken }, 503);
  }
  const no = ornekSiparisNo(is.is_no);
  const r = await env.KATALOG.prepare(
    "INSERT OR IGNORE INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)" +
    " VALUES (?, 0, ?, ?, ?, 'build-baslat', ?, ?)"
  ).bind(no, is.is_no, is.tur, is.olcu_mm, simdiIso(simdi), simdiIso(simdi)).run();
  return fjson({ ok: true, siparis_no: no, yeni: !!(r && r.meta && r.meta.changes === 1) }, 200);
}

/** GET /yonet/foto/ornekler — "Örnek üretimler": ornek onizlemeleri + uretim asamasi + dosyalar. */
export async function panelOrnekListe(env) {
  let satirlar = [];
  try {
    const r = await env.KATALOG.prepare(
      "SELECT i.is_no, i.tur, i.olcu_mm, i.tarih, i.asama AS onizleme, i.hata," +
      " u.siparis_no, u.asama, u.sebep, u.analiz," +
      " (SELECT COALESCE(SUM(kredi), 0) FROM foto_kredi k WHERE k.siparis_no = u.siparis_no) AS kredi" +
      " FROM foto_isler i LEFT JOIN foto_uretim u ON u.is_no = i.is_no AND u.siparis_no LIKE '" +
      // Uretime girenler ONCE (basarisiz onizleme yigini uretilmis ornegi listeden itmesin).
      ORNEK_SIPARIS_ONEK + "%' WHERE i.ziyaretci = ? ORDER BY (u.siparis_no IS NULL), i.tarih DESC LIMIT 30"
    ).bind(ORNEK_ZIYARETCI).all();
    satirlar = r.results || [];
  } catch (e) {
    if (!tabloYok(e)) { throw e; }
  }
  const ornekler = satirlar.map((s) => {
    const taban = s.siparis_no ? "/api/shop/yonet/foto-dosya?siparis_no=" + encodeURIComponent(s.siparis_no) +
      "&kalem=0" : "";
    return {
      is: s.is_no, tur: s.tur, olcu_mm: s.olcu_mm, tarih: s.tarih,
      onizleme: s.onizleme, hata: s.hata || "",
      gorsel: s.onizleme === "hazir" ? "/api/shop/yonet/foto/ornek-gorsel?is=" + s.is_no : "",
      siparis_no: s.siparis_no || "",
      asama: s.siparis_no ? s.asama : "uretilmedi",
      sebep: s.sebep ? (ELLE_METNI[s.sebep] || s.sebep) : "",
      analiz: s.analiz || "",
      alt_kenar_mm: analizAltKenar(s.analiz),
      kredi: s.kredi || 0,
      dosyalar: s.asama === "hazir" && taban
        ? { "3mf": taban + "&bicim=3mf", "glb": taban + "&bicim=glb" } : null,
    };
  });
  return fjson({ ornekler, yapilandirma: ornekYapilandirma(env) }, 200);
}

// ---------------------------------------------------------------- panel: ORNEK KONSEPT (2D)

/** POST /yonet/foto/ornek-konsept — musteri ucuyla AYNI cagri; bot/onay/ziyaretci/gunluk tavan ATLANIR. */
export async function panelOrnekKonsept(request, env, simdi, telegram) {
  return konseptUret(request, env, simdi, telegram, true);
}
/** GET /yonet/foto/ornek-konsept-durum?konsept= — yalniz ornek konsepti. */
export async function panelOrnekKonseptDurum(env, url, simdi) { return konseptDurum(env, url, simdi, true); }
/** GET /yonet/foto/ornek-konsept-gorsel?konsept= — yalniz ornek konsepti. */
export async function panelOrnekKonseptGorsel(env, url) { return konseptGorsel(env, url, true); }
