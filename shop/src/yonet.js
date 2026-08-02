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
 *  - Erisim: X-Yonet-Anahtar basligi (makine istemcileri) YA DA `pruvo_yonet` HttpOnly cerezi
 *    (tarayici; POST /yonet sifre kutusundan kurulur). ❌ `?anahtar=` SORGU PARAMETRESI YOK —
 *    tam URL erisim loglarina/tarayici gecmisine/Referer basligina yaziliyordu (sessiz sizinti).
 *    Anahtar YOK/YANLIS -> /yonet GET'te sifre kutusu, diger uclarda 404 (varligi sizmasin).
 *    YONET_ANAHTAR secret tanimli DEGILSE tum /yonet* 404 (ozellik kapali; form bile yok).
 *  - Anahtar loglara/HATA metnine YAZILMAZ. PII yalniz anahtarli yanitta. CORS yok (same-origin).
 *  - Gizli kaynak bilgisi (tedarikci/link) sayfaya/JSON'a GIRMEZ.
 *  - 'kargolandi'ya SADECE /kargo ucundan gecilir (takip kodu zorunlu) — tek yol.
 *  - 'odendi'ye gecis (havale onayi) REKLAM OLCUMU tetikler: Purchase, event_id = siparis_no
 *    (kart akisiyla ayni dedup anahtari). IDEMPOTENS uc katmanli — bkz. durumDegistir().
 *    ⚠️ KURULUM.md'deki yedek ham SQL komutu bu uctan GECMEZ -> olcum de gitmez; havale
 *    onayinin normal yolu YONETIM SAYFASIDIR (ham SQL yalniz sayfa/anahtar yoksa).
 */

import { SEMALAR } from "./semalar.js";
import { KONFIGURLAR } from "./konfigurlar.js";
import { golgeRaporu } from "./konfigur-golge.js";
import {
  epostaAkisi, onayEpostasiHtml, kargoEpostasiHtml,
} from "./eposta.js";
import { olcumGonder, olcumLog } from "./olcum.js";

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
  // HAZIR TICARI MAL (satirda `tur:"fiziksel"`): BASKI YOK. Baski onerisi basmak — hatta
  // "Malzemeye uygun genel baskı ayarlarıyla üretilir." demek — bir boya kutusunu URETIYORMUS
  // gibi gosterir. Kosul TAM dize; `tur` yok/taninmaz ise bugunku kollar aynen isler.
  if (satir && satir.tur === "fiziksel") {
    return "Hazır ticari ürün — 3D baskı YOK, stoktan gönderilir.";
  }
  if (d1Baski && d1Baski.trim() && d1Baski.trim() !== "-") { return d1Baski.trim(); }
  if (sema && (sema.baski || sema.baskiIpucu)) { return sema.baski || sema.baskiIpucu; }
  return BASKI_FALLBACK[satir.malzeme] || "Malzemeye uygun genel baskı ayarlarıyla üretilir.";
}

// ---- anahtar ------------------------------------------------------------------

/**
 * Sabit-zamanli string esitligi (erken donus zamanlama sizintisini onler).
 *
 * 🔴 FAIL-CLOSED PRIMITIF: taraflardan biri string DEGILSE ya da BOS ise DAIMA false.
 * Eski hali `String(a || "")` ile ikisini de `""`ye cevirir ve `sabitEsit("", undefined)`
 * icin **true** donerdi. Tek basina zararsiz gorunur; ama `env.YONET_ANAHTAR` tanimsizken
 * bos sifreyle giris = YETKI demekti. O gun korumayi tutan sey yalnizca CAGRI SIRASIYDI
 * (yonet() secret'i once kontrol ediyordu). Koruma cagri sirasina birakilmaz — primitifin
 * KENDISI kapali olmali. (Olculdu: curutucunun "secret kapisini giris POST'undan sonraya
 * al" mutanti, bu satir duzelmeden bos sifreye 200 + yetki veriyordu.)
 * ⚠️ Uzunluk farkinda erken donuyor — yani anahtarin UZUNLUGUNU sizdirir. Bilinen,
 * mimarin kaydettigi ve bu tura ALINMAYAN kalem.
 */
export function sabitEsit(a, b) {
  if (typeof a !== "string" || typeof b !== "string") { return false; }
  if (a.length === 0 || b.length === 0) { return false; }
  if (a.length !== b.length) { return false; }
  let fark = 0;
  for (let i = 0; i < a.length; i++) { fark |= a.charCodeAt(i) ^ b.charCodeAt(i); }
  return fark === 0;
}

// ---- oturum cerezi ------------------------------------------------------------
// TEK KAYNAK: ad/omur/bayraklar asagidaki uc sabitten turer. Ikizlenirse ("pruvo_yonet"
// bir yerde, "pruvo-yonet" baska yerde) kapi SESSIZCE ayrisir.

const CEREZ_ADI = "pruvo_yonet";
const CEREZ_OMUR_SN = 12 * 60 * 60;   // 12 saat
/**
 * Bayraklarin hepsi ZORUNLU:
 *  HttpOnly        — sayfa JS'i okuyamaz (XSS anahtari calamaz),
 *  Secure          — yalniz TLS uzerinde gider,
 *  SameSite=Strict — capraz-siteden gelen gezinmede GONDERILMEZ (Referer/CSRF ekseni kapali),
 *  Path=/          — hem /api/shop/yonet paneli hem /api/shop/yonet/stl indirmeleri kapsanir.
 */
const CEREZ_BAYRAK = "HttpOnly; Secure; SameSite=Strict; Path=/";

/** Oturum cerezini KURAN Set-Cookie dizesi (saf: yan etkisi yok, istek gormez). */
export function yonetCereziKur(anahtar) {
  return CEREZ_ADI + "=" + encodeURIComponent(anahtar == null ? "" : String(anahtar)) +
    "; " + CEREZ_BAYRAK + "; Max-Age=" + CEREZ_OMUR_SN;
}

/** Oturum cerezini SILEN Set-Cookie dizesi (cikis; ayni bayraklar, Max-Age=0). */
export function yonetCereziSil() {
  return CEREZ_ADI + "=; " + CEREZ_BAYRAK + "; Max-Age=0";
}

/**
 * Istekteki yonetim cerezinin DEGERI (yoksa ""). Cerez ADI TAM esitlenir.
 * ⚠️ `cookieBasligi.includes(anahtar)` gibi naive bir arama, `baska=pruvo_yonet=<anahtar>`
 * seklinde BASKA bir cerezin DEGERI icine gomulen anahtari da gecerli sayardi; ayni sekilde
 * `pruvo_yonet_x=<anahtar>` yakin-iskasini da. Ad esitligi bu iki yolu da kapatir.
 */
export function yonetCereziOku(request) {
  const ham = (request && request.headers && request.headers.get("Cookie")) || "";
  if (!ham) { return ""; }
  for (const parca of ham.split(";")) {
    const esit = parca.indexOf("=");
    if (esit < 0) { continue; }
    if (parca.slice(0, esit).trim() !== CEREZ_ADI) { continue; }
    let deger = parca.slice(esit + 1).trim();
    if (deger.length >= 2 && deger.charAt(0) === '"' &&
        deger.charAt(deger.length - 1) === '"') {
      deger = deger.slice(1, -1);
    }
    try { return decodeURIComponent(deger); } catch (e) { return deger; }
  }
  return "";
}

/**
 * Anahtar gecerli mi? Secret tanimsizsa DAIMA false (ozellik kapali; 404).
 * IKI TASIYICI: `X-Yonet-Anahtar` basligi (tools/yazdir.py + makine istemcileri) ve
 * `pruvo_yonet` HttpOnly cerezi (tarayici — cerez hem fetch'te hem <a href> gezinmesinde
 * kendiliginden gider; sorgu parametresinin var olma sebebi buydu, cerez onu IKAME EDER).
 * ❌ `url.searchParams.get("anahtar")` KALDIRILDI (sizinti). `url` imzada DURUYOR ama
 * yetki icin OKUNMUYOR — cagri yerleri degismesin diye.
 */
function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  if (sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR)) {
    return true;
  }
  return sabitEsit(yonetCereziOku(request), env.YONET_ANAHTAR);
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
  // Ana siteye kalici urun sayfasi linki (yonetim ekraninda kalem basligi buraya tiklanir).
  const siteUrl = ((env && env.SITE_URL) || "https://pruvo3d.com").replace(/\/$/, "");
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
        // Hazir ticari mal isareti — beyan alanlari BOS oldugunda "veri kayip" mi yoksa
        // "secim yok" mu oldugunu ekran bu alandan bilir (bkz. baskiOnerisi + satir cizici).
        tur: k.tur === "fiziksel" ? "fiziksel" : "",
        adet: k.adet || 1,
        parametrik: parametrik,
        parametre_detay: k.parametre_detay || "",
        baski_oneri: baskiOnerisi(k, ur.baski, sema),
        // Yonetim ekraninda kalem basligi buraya tiklanir (urun sayfasi, ana site).
        urun_url: siteUrl + "/urun/" + encodeURIComponent(k.id || "") + "/",
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

/**
 * Durum gecmisine tek kayit dusurur. TEK KAYNAK: kart akisi (index.js donus()) da BUNU
 * cagirir — iki akis ayni iz bicimini uretsin diye (ikinci kopya YOK; bicim ayrisirsa
 * tools/olculmemis-siparis.py sessizce yanlislanirdi).
 */
export function gecmiseEkle(mevcutJson, hedef, ekstra) {
  let g = [];
  try { g = JSON.parse(mevcutJson) || []; } catch (e) { g = []; }
  if (!Array.isArray(g)) { g = []; }
  const kayit = { d: hedef, z: new Date().toISOString() };
  // "o": 1 -> bu geciste Purchase olcumu DENENDI (tetiklendi). Idempotens izi; asagida okunur.
  // ⚠️ ANLAMI "DENENDI", "ULASTI" DEGIL: iz, gonderim SONUCUNDAN once (ayni atomik UPDATE
  // icinde) yazilir; olcum fire-and-forget'tir. Meta 400 dondurse, ag koparsa, secret
  // tanimsiz olsa bile iz "1" kalir. Teshis icin izin varligina DEGIL, Cloudflare Logs'taki
  // `olcum {...}` satirina bakilir (orada kod/events_received/fbtrace_id var).
  if (ekstra && ekstra.olcumDenendi) { kayit.o = 1; }
  g.push(kayit);
  if (g.length > 50) { g = g.slice(-50); } // sinirla (same-row buyumesin)
  return JSON.stringify(g);
}

/**
 * Bu siparis icin Purchase olcumu DAHA ONCE bu uctan DENENDI mi? (durum_gecmisi izi)
 * "Denendi" = gonderim tetiklendi; ULASTIGINI GARANTI ETMEZ (bkz. gecmiseEkle notu).
 * Amaci yalnizca TEKRARI onlemek — "Meta aldi" teshisi icin KULLANILMAZ.
 * Not: gecmis 50 kayitta kirpilir; pratikte bir siparis 50 durum degisimi yasamaz, ama
 * kirpilma olsa bile ikinci savunma calisir: 'odendi'ye SADECE 'havale-bekliyor'dan
 * gecilebilir ve gecis CAS'tir (asagi bak) — yani tekrar zaten mumkun degil.
 */
function olcumDenendiMi(gecmisJson) {
  let g = [];
  try { g = JSON.parse(gecmisJson) || []; } catch (e) { g = []; }
  if (!Array.isArray(g)) { return false; }
  return g.some((k) => k && k.o === 1);
}

async function siparisGetir(env, siparisNo) {
  return env.KATALOG.prepare(
    "SELECT siparis_no, tarih, durum, durum_gecmisi, urunler, tutar_kurus, kargo_kurus," +
    " kdv_kurus, odeme_yontemi, atif," +
    " musteri_ad, musteri_eposta, musteri_adres FROM siparisler WHERE siparis_no = ?"
  ).bind(siparisNo).first();
}

/** ISO tarihi -> saniye damgasi. Bozuk/bossa 0 (cagiran "simdi"ye duser). */
function isoSaniye(iso) {
  const t = Date.parse(String(iso || ""));
  return Number.isFinite(t) ? Math.floor(t / 1000) : 0;
}

// ---- /durum -------------------------------------------------------------------

/**
 * HAVALE CIROSU OLCUMU (mimar acigi 3).
 *
 * NEDEN: havale ile odenen siparis /donus akisindan GECMEZ (iyzico yok) -> daha once
 * hicbir Purchase olayi gitmiyordu. Sonuc: havale cirosu Meta'da ve GA4'te YOKTU; Meta
 * "bu reklam satmiyor" diye YANLIS ogreniyordu (kart-disi ciro gorunmez).
 *
 * DEDUP: event_id = siparis_no — kart akisiyla AYNI anahtar (olcum.js satinAlmaOlayi).
 *
 * 🔒 IP/UA GONDERILMEZ (bilincli): bu istek OKAN'IN yonetim tarayicisindan gelir; buradaki
 * IP/UA musteriye ait DEGILDIR. Yanlis kisiyi eslestirmek, hic eslestirmemekten kotudur.
 * (Musterinin rizali fbp/fbc'si atif kaydindan zaten gider — /baslat'ta yakalanmisti.)
 *
 * event_time = SIPARIS TARIHI (odemenin gercek ani; havalede musteri parayi siparis
 * gunu gonderir, Okan dekontu sonra gorur). Meta'nin 7 gunluk geriye-donuk penceresini
 * asan olayi olcum.js atlar + loglar.
 */
function havaleOlcumu(env, ctx, s) {
  const zaman = isoSaniye(s.tarih);
  return olcumGonder(env, ctx, s, undefined, {
    kaynak: "havale",
    event_time: zaman > 0 ? zaman : Math.floor(Date.now() / 1000),
    // istemci YOK — yukaridaki gerekce.
  });
}

async function durumDegistir(request, env, ctx) {
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
  // --- Purchase olcumu karari (yalniz 'odendi'ye gecis) --------------------------
  // IDEMPOTENS — UC KATMAN, hicbirine TEK basina guvenilmez:
  //  1) DURUM MAKINESI: 'odendi' hedefine SADECE 'havale-bekliyor'dan gecilebilir
  //     (IZINLI). Kart siparisi zaten 'odendi'dir; 'odendi'->'odendi' gecersiz (400)
  //     -> kart akisinin gonderdigi olay buradan TEKRARLANAMAZ.
  //  2) CAS (compare-and-swap): UPDATE ... WHERE durum = <okunan durum>. Iki es zamanli
  //     istek gelse yalniz BIRI changes>0 alir; olcum yalniz o daldan tetiklenir.
  //  3) KALICI IZ: durum_gecmisi'ne {"o":1} yazilir; ayni UPDATE icinde (atomik).
  //     Iz varsa bir daha DENENMEZ — elle iki kez 'odendi' denenirse de tek olay.
  //     ⚠️ Iz "denendi" demek, "Meta aldi" DEMEK DEGIL (bkz. gecmiseEkle/olcumDenendiMi).
  // Meta event_id ile ayrica dedup yapar; o DORDUNCU ag, tek savunma DEGIL.
  const olcumluGecis = (hedef === "odendi");
  const zatenDenendi = olcumDenendiMi(s.durum_gecmisi);
  const olcumTetikle = olcumluGecis && !zatenDenendi;

  const yeniGecmis = gecmiseEkle(s.durum_gecmisi, hedef, { olcumDenendi: olcumTetikle });
  const g = await env.KATALOG.prepare(
    "UPDATE siparisler SET durum = ?, durum_gecmisi = ? WHERE siparis_no = ? AND durum = ?"
  ).bind(hedef, yeniGecmis, siparisNo, s.durum).run();
  if (!(g.meta && g.meta.changes > 0)) {
    return yjson({ hata: "durum-degismis", mevcut: s.durum }, 409);
  }

  if (olcumluGecis && zatenDenendi) {
    // Sessiz atlama YOK: "bu siparisin ikinci Purchase'i nerede?" sorusu cevaplanabilsin.
    olcumLog({ olay: "Purchase", siparis_no: siparisNo, kaynak: "havale",
               atlandi: "zaten-denendi" });
  }
  if (olcumTetikle && g.meta.changes > 0) {
    // Fire-and-forget (ctx.waitUntil olcum.js icinde): olcum hatasi durum degisimini
    // ETKILEMEZ — durum D1'de zaten kalici olarak degisti.
    havaleOlcumu(env, ctx, { ...s, durum: hedef });
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
    // 2-RENK (COK GOVDELI) SIPARIS: satirda `yazi_renk` varsa urun IKI govde olarak
    // basilir (AMS 2 filaman). Her govde AYRI indirilir:
    //   ...&parca=govde  -> yazisiz cerceve kabugu
    //   ...&parca=yazi   -> yalniz kabartma yazi
    // `parca` VERILMEZSE bugunku TEK STL (birlesik govde) aynen doner — var olan
    // yonetim baglantilari kirilmaz. Degerin GECERLILIGINI onizleme worker'i
    // fail-closed dogrular (liste disi deger 400 `gecersiz-parca`).
    const parcaParam = url.searchParams.get("parca");
    const istekGovdesi = { aile: urunId, parametreler: satir.parametreler };
    if (parcaParam) { istekGovdesi.parca = parcaParam; }
    let c;
    try {
      c = await fetch(taban + "/api/onizleme/ic-derle", {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   "X-Ic-Anahtar": env.IC_DERLE_ANAHTAR || "" },
        body: JSON.stringify(istekGovdesi),
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
          tirnaksiz(siparisNo + "-" + urunId + (parcaParam ? "-" + parcaParam : "")) +
          ".stl\"",
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

// ---- giris kapisi (sifre kutusu) ----------------------------------------------

/**
 * Yetkisiz `GET /yonet` VE yanlis/bos anahtarli `POST /yonet` icin BIREBIR AYNI yanit.
 * ⚠️ AYIRT EDICI MESAJ YOK ("anahtar yanlis" DEMEZ): "varligi sizmasin" kurali burada da
 * gecerli — yanlis deneme ile hic denememis ziyaretci ayni kodu, ayni govdeyi, ayni
 * basliklari gorur (Set-Cookie de YOK). Ekranda siparis/PII/panel govdesi YOKTUR.
 * Form eylemi istegin KENDI yolundan turer (sorgu dizesi TASINMAZ).
 */
function girisEkrani(url) {
  const yol = String((url && url.pathname) || "/api/shop/yonet").replace(/[&<>"']/g, "");
  // 🔴 IKAME FONKSIYON — dize DEGIL. `String.replace`'in IKAME DIZESI `$&`, `$\``, `$'`,
  // `$$` desenlerini yorumlar; backtick yukaridaki [&<>"'] suzgecinden GECER ve `$\``
  // eslesmeden ONCEKI tum HTML'i action niteligine kopyalar (olculdu: 967 -> 1762 bayt).
  // Fonksiyon ikamesinde bu desenler yorumlanmaz — `yol` HARFI HARFINE basilir.
  // (Bugun yonlendirici `yol === "/yonet"` TAM esitligi dayattigi icin erisilemezdi; ama
  // rota bir gun on-ek eslesmesine cevrilirse dogrudan enjeksiyon olurdu. Suzgec tek
  // basina sahte guvenceydi.)
  return new Response(GIRIS_HTML.replace("__EYLEM__", () => yol), {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

// ---- giris hiz siniri (worker-ici; Cloudflare binding'i GEREKTIRMEZ) ----------
// NEDEN GEREKLI: panel eskiden anahtarsiz 404'tu, artik 200 sifre formu donuyor — ucun
// VARLIGI kesfedilebilir. Anahtar tek ve paylasilan bir sir; kaba kuvvete karsi tek katman
// bu. (Takas bilincli: anahtarin erisim loglarinda/Referer'da durmasindan cok daha ucuz.)
// ⚠️ DURUSTCE SINIRI: sayac ISOLATE BASINA tutulur. Cloudflare istegi baska bir isolate'a
// dusurebilir, dolayisiyla bu MUTLAK bir tavan DEGIL — ucuz bir yavaslatici. Kalici/global
// tavan Rate Limiting binding'i ister; mimar bu turda kapsam disi tuttu.
const GIRIS_PENCERE_MS = 60 * 1000;
const GIRIS_TAVAN = 5;              // pencere basina BASARISIZ deneme
const GIRIS_GECIKME_MS = 250;       // her basarisiz/bloke denemede sabit bekleme
const GIRIS_GOVDE_SINIRI = 1024;    // bayt — sifre formu icin fazlasiyla yeterli
let girisSayac = { pencereBas: 0, adet: 0 };

function bekle(ms) { return new Promise((coz) => setTimeout(coz, ms)); }

/**
 * Pencere doldu mu (esik asildi mi)? Pencere gecmisse sayac sifirlanir.
 * Sayac isolate basina tutulur; GARANTILI bir ust sinir DEGILDIR (bkz. yukaridaki not).
 */
function girisBlokeMi(simdi) {
  if (simdi - girisSayac.pencereBas > GIRIS_PENCERE_MS) {
    girisSayac = { pencereBas: simdi, adet: 0 };
  }
  return girisSayac.adet >= GIRIS_TAVAN;
}

/**
 * Istek govdesini SINIRLI okur. Sinir asilirsa null (fail-closed) — `request.formData()`
 * govde boyutuna UST SINIR KOYMAZ; anahtarsiz bir uca sinirsiz ayristirma yaptirmayiz.
 * Yalniz `application/x-www-form-urlencoded` ayristirilir (form bunu yollar); multipart
 * yuzeyi bilerek ACILMAZ.
 */
async function girisGovdesi(request) {
  const bildirilen = parseInt(request.headers.get("Content-Length") || "", 10);
  if (Number.isFinite(bildirilen) && bildirilen > GIRIS_GOVDE_SINIRI) { return null; }
  if (!request.body) { return ""; }
  const okuyucu = request.body.getReader();
  const parcalar = [];
  let toplam = 0;
  for (;;) {
    const { done, value } = await okuyucu.read();
    if (done) { break; }
    toplam += value.byteLength;
    // Content-Length YALAN soyleyebilir / hic olmayabilir (chunked): gercek bayt sayilir.
    if (toplam > GIRIS_GOVDE_SINIRI) { try { await okuyucu.cancel(); } catch (e) {} return null; }
    parcalar.push(value);
  }
  const hepsi = new Uint8Array(toplam);
  let ofs = 0;
  for (const p of parcalar) { hepsi.set(p, ofs); ofs += p.byteLength; }
  return new TextDecoder().decode(hepsi);
}

/**
 * POST /yonet — sifre kutusundan gelen anahtar. Anahtar istek GOVDESINDE gider; GET
 * DEGIL, cunku GET onu sorgu dizesine yazardi = kapatmaya calistigimiz sizintinin ta
 * kendisi. Dogruysa HttpOnly cerez kurulur + panele 302 (Location'da sorgu YOK).
 *
 * FAIL-CLOSED KOLLARI — hepsi AYNI giris ekranini doner (ayirt edilemez):
 *   secret yok -> 404 · tavan asildi -> form · govde buyuk/bozuk/bos -> form · yanlis -> form.
 * Anahtar loga/yanita/hata metnine YAZILMAZ.
 */
// `export` DAVRANISI DEGISTIRMEZ: yalnizca OLCULEBILIRLIK — kendi kapisi yonet()
// uzerinden gecmeden, IZOLE cagrilabilsin diye disa acildi (kabul.js C22a).
export async function girisYap(request, url, env) {
  // 🔴 KENDI KAPISI (savunma derinligi): yonet() de secret'i basta kontrol eder — ama
  // koruma CAGRI SIRASINA birakilmaz. Sira degisirse bu uc anahtarsiz cerez kuruluma
  // yetki verirdi. Kapi burada TEKRARLANIR.
  // OLCULDU (mutasyon, --yonet-cerez): iki kapi ARTIK AYRI AYRI olculuyor. Bu satir TEK
  // BASINA silinince C22a kirmizi yanar; yonet()'in ust kapisi TEK BASINA silinince C22b
  // + C15 kirmizi yanar. Once bu satirin tek basina silinmesi alt kumeyi YESIL biraki-
  // yordu (eski C22 iki kapinin VEYA'sini olcuyordu) — o bosluk kapandi.
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();
  if (girisBlokeMi(simdi)) {
    // Tavan asildi: sifre HIC BAKILMADAN reddedilir (dogru sifre de). Yanit, hic
    // denememis ziyaretcininkiyle BIREBIR ayni — "bloke oldun" bile denmez.
    await bekle(GIRIS_GECIKME_MS);
    return girisEkrani(url);
  }
  const metin = await girisGovdesi(request);
  const verilen = metin === null ? "" :
    String(new URLSearchParams(metin).get("sifre") || "");
  if (!sabitEsit(verilen, env.YONET_ANAHTAR)) {
    girisSayac.adet++;
    await bekle(GIRIS_GECIKME_MS);
    return girisEkrani(url);
  }
  girisSayac = { pencereBas: simdi, adet: 0 };   // basarili giris sayaci sifirlar
  return new Response(null, {
    status: 302,
    headers: {
      "Location": String((url && url.pathname) || "/api/shop/yonet"),
      "Set-Cookie": yonetCereziKur(env.YONET_ANAHTAR),
      "Cache-Control": "no-store",
    },
  });
}

// ---- giris (index.js buraya yonlendirir) --------------------------------------

// ---- /konfigur-golge (FAZ 3 KONTROL KIPI) -------------------------------------

/**
 * GET /yonet/konfigur-golge — "D1'deki konfigur semasi Worker bundle'iyla AYNI mi?"
 *
 * 🔴 SALT OKUMA: tek bir SELECT; D1'e YAZMAZ, siparis/olcum/e-posta/iyzico TETIKLEMEZ,
 * musteriye giden hicbir davranisi degistirmez. Yalnizca FAZ 4 (cevirme) kararinin girdisi
 * olan sayiyi gorunur kilar: `fark_kurus_toplam` 0 ise iki kaynak ayni parayi uretiyor.
 *
 * Anahtar korumasi /yonet* ile AYNI (anahtar yok/yanlis -> 404). Konfigur verisi zaten
 * public (matematik + aralik + renk/malzeme; sir icermez) ama uc yine de gizli tutulur —
 * ic teshis yuzeyi genisletilmez.
 *
 * KOLON YOKSA (--sema henuz kosmadi) SELECT duser -> 200 + durum "kolon-yok" doner
 * (500 DEGIL: bu bir rapor ucu, kendisi kirmizi yanmamali; teshis metni acik yazilir).
 */
async function konfigurGolge(env, url) {
  const SECENEK = globalThis.PRUVO_SECENEK;
  if (!SECENEK) { return yjson({ hata: "secenekler-yok" }, 500); }
  const bundleIdler = [...KONFIGURLAR.keys()];
  const yertut = bundleIdler.map(() => "?").join(",") || "''";
  let satirlar = [];
  try {
    // IKI YON: (a) D1'de konfigur DOLU olan her satir (bundle'da olmayanlar = acik pencere),
    // (b) bundle'daki her id (D1'de bos/eksik olanlar = senkron kacmis). Tek sorgu.
    const r = await env.KATALOG.prepare(
      "SELECT id, kategori, konfigur FROM urunler WHERE konfigur <> '' OR id IN (" +
      yertut + ")").bind(...bundleIdler).all();
    satirlar = r.results || [];
  } catch (e) {
    return yjson({
      durum: "kolon-yok",
      teshis: "D1'de `konfigur` kolonu okunamadi: " + (e && e.message || String(e)),
      coz: "python3 tools/d1-sync.py --sema   (additive ALTER; sonra python3 tools/d1-sync.py)",
      bundle_urun: bundleIdler.length,
    }, 200);
  }
  const ornekBoy = parseInt(url.searchParams.get("boy") || "0", 10);
  const ornekler = ornekBoy > 0 ? [[ornekBoy, url.searchParams.get("malzeme") || "PLA"]] : null;
  const rapor = golgeRaporu(KONFIGURLAR, satirlar, SECENEK, ornekler);
  return yjson({
    durum: rapor.fark_kurus_toplam === 0 && rapor.kayitlar.length === 0 ? "parite" : "ayrisim",
    bundle_urun: bundleIdler.length,
    d1_konfigurlu_satir: satirlar.filter((s) => s.konfigur).length,
    ozet: rapor.ozet,
    fark_kurus_toplam: rapor.fark_kurus_toplam,
    kayitlar: rapor.kayitlar,
    not: "GOLGE MODU: tahsilat HALA bundle'dan hesaplanir; bu uc yalniz olcer.",
  }, 200);
}

/**
 * /yonet* yonlendirici. altYol = "/", "/liste", "/durum", "/kargo", "/stl", "/konfigur-golge".
 * KAPI SIRASI (fail-closed):
 *   1. YONET_ANAHTAR secret YOK -> her sey 404 (ozellik kapali; giris formu BILE yok),
 *   2. POST /yonet -> giris kapisi (sifre kutusu; dogruysa cerez + 302),
 *   3. anahtar yok/yanlis -> GET /yonet'te sifre kutusu, DIGER her ucta 404 (varlik sizmasin),
 *   4. yetkili -> normal yonlendirme.
 * telegram: index.js'in telegram fonksiyonu.
 */
export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;
  if (altYol === "/" && m === "POST") { return girisYap(request, url, env); }
  if (!anahtarGecerli(request, url, env)) {
    return (altYol === "/" && m === "GET") ? girisEkrani(url) : yon404();
  }
  if (altYol === "/" && m === "GET") { return sayfa(); }
  if (altYol === "/liste" && m === "GET") { return liste(env, url); }
  if (altYol === "/durum" && m === "POST") { return durumDegistir(request, env, ctx); }
  if (altYol === "/kargo" && m === "POST") { return kargo(request, env, ctx, telegram); }
  if (altYol === "/stl" && m === "GET") { return stlIndir(env, url); }
  if (altYol === "/stl-liste" && m === "GET") { return stlListe(env, url); }
  // FAZ 3 kontrol kipi — SALT OKUMA (yazma/yan etki YOK).
  if (altYol === "/konfigur-golge" && m === "GET") { return konfigurGolge(env, url); }
  return yon404();
}

// Giris ekrani: TEK sifre alani. Siparis/PII/panel govdesi/JS YOK; baslikta "Sipariş
// Yönetimi" gibi ne oldugunu soyleyen bir ipucu da YOK. `__EYLEM__` istegin kendi
// yoluyla degistirilir (girisEkrani); anahtar POST GOVDESINDE gider, sorgu dizesinde DEGIL.
const GIRIS_HTML = `<!doctype html><html lang="tr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>PRUVO</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
 background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#1f2937}
form{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:22px;
 display:flex;flex-direction:column;gap:12px;min-width:260px}
h1{font-size:18px;margin:0;color:#12294d}
input{font-size:16px;padding:9px 10px;border:1px solid #e5e7eb;border-radius:6px}
button{font-size:16px;padding:9px 10px;border:0;border-radius:6px;background:#12294d;
 color:#fff;cursor:pointer}
</style></head><body>
<form method="post" action="__EYLEM__">
 <h1>PRUVO</h1>
 <input type="password" name="sifre" autocomplete="current-password" autofocus>
 <button type="submit">Gir</button>
</form>
</body></html>`;

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
function esc(s){s=(s==null?"":""+s);return s.replace(/&/g,"&amp;").replace(/</g,"&lt;")
 .replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function tl(k){k=Math.max(0,Math.floor(+k||0));var t=Math.floor(k/100),ku=(""+(k%100)).padStart(2,"0");
 return (""+t).replace(/\\B(?=(\\d{3})+(?!\\d))/g,".")+","+ku+" TL";}
async function api(yol,secenek){
 // Kimlik HttpOnly cerezden gelir; sayfa JS'i anahtari GORMEZ (okuyamaz da).
 secenek=secenek||{};secenek.credentials="same-origin";
 var c=await fetch("/api/shop/yonet"+yol,secenek);
 var v=null;try{v=await c.json();}catch(e){}
 return {kod:c.status,govde:v};
}
function durumRozet(d){return '<span class="rozet '+esc(d)+'">'+esc(d)+'</span>';}
function satirHtml(no,k){
 var indir;
 if(k.parametrik){
  // Anahtar URL'e GOMULMEZ: gezinme de cerezi tasir (SameSite=Strict, Path=/).
  indir='<a class="indir" href="/api/shop/yonet/stl?siparis_no='+encodeURIComponent(no)+
   '&kalem='+k.kalem+'">STL üret + indir</a>';
 }else{
  // COK-PARCA: dugme parca listesini ceker, parcalar tek tek indirilir (zip yok).
  var kutuId='parca-'+no+'-'+k.kalem;
  indir='<button class="ikincil" onclick="parcalar(\\''+esc(no)+'\\',\\''+esc(k.id)+
   '\\',\\''+kutuId+'\\')">Üretim dosyaları</button>'+
   '<span id="'+kutuId+'"></span>';
 }
 var baslikLink=k.urun_url?
  '<a href="'+esc(k.urun_url)+'" target="_blank" rel="noopener">'+esc(k.baslik)+'</a>':
  esc(k.baslik);
 // Beyan (malzeme · renk) YALNIZ varsa basilir; fiziksel kalemde " · " gibi yarim bir satir
 // yerine "Hazır ürün" yazar — ekran kaydin ne oldugunu SOYLER, bosluk birakmaz.
 var filrenk=(k.malzeme||k.renk)?
  esc(k.malzeme)+' · <span class="renk">'+esc(k.renk)+'</span>':
  (k.tur==='fiziksel'?'Hazır ürün':'');
 return '<div class="satir">'+
  '<div class="filrenk">'+filrenk+' × '+esc(k.adet)+'</div>'+
  '<div>'+baslikLink+(k.parametre_detay?' <span class="kucuk">['+esc(k.parametre_detay)+']</span>':'')+'</div>'+
  '<div class="kucuk">Ürün kodu: '+esc(k.id)+'</div>'+
  '<div class="baski">🖨️ '+esc(k.baski_oneri)+'</div>'+
  indir+
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
   '&siparis_no='+encodeURIComponent(no)+'">'+
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
 if(r.kod!==200){m.innerHTML='<p class="hata">Liste alınamadı ('+r.kod+
  '). Oturum düşmüş olabilir — sayfayı yenileyin.</p>';return;}
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
