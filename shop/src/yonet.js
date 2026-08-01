/**
 * pruvo-shop — anahtar korumali SIPARIS YONETIMI (siparis yonetimi paketi, Faz 1).
 *
 * Uclar (shop worker'a takili; site route'u pruvo3d.com/api/shop/yonet*):
 *   GET  /api/shop/yonet            -> tek dosyalik yonetim SAYFASI (inline HTML/CSS/JS)
 *   GET  /api/shop/yonet/liste      -> JSON siparis listesi (son 50; ?durum= ile suzme)
 *   POST /api/shop/yonet/durum      -> {siparis_no, durum} durum makinesi (izinli gecisler)
 *   POST /api/shop/yonet/kargo      -> {siparis_no, kargo_firma, kargo_kodu} -> 'kargolandi' + e-posta
 *   GET  /api/shop/yonet/stl        -> uretim dosyasi indir (parametrik: derleyici; normal: R2)
 *   POST /api/shop/yonet/wa-siparis -> WhatsApp (Ege) kanalindan gelen siparisi panele yazar
 *
 * KIRMIZI CIZGILER (tools/paket-siparis-yonetimi.md):
 *  - Erisim: ?anahtar=<YONET_ANAHTAR> ya da X-Yonet-Anahtar. Anahtar YOK/YANLIS -> 404
 *    (varligi sizmasin). YONET_ANAHTAR secret tanimli DEGILSE tum /yonet* 404 (ozellik kapali).
 *  - Anahtar loglara/HATA metnine YAZILMAZ. PII yalniz anahtarli yanitta. CORS yok (same-origin).
 *  - Gizli kaynak bilgisi (tedarikci/link) sayfaya/JSON'a GIRMEZ.
 *  - 'kargolandi'ya SADECE /kargo ucundan gecilir (takip kodu zorunlu) — tek yol.
 *  - 'odendi'ye gecis (havale onayi) REKLAM OLCUMU tetikler: Purchase, event_id = siparis_no
 *    (kart akisiyla ayni dedup anahtari). IDEMPOTENS uc katmanli — bkz. durumDegistir().
 *    ⚠️ KURULUM.md'deki yedek ham SQL komutu bu uctan GECMEZ -> olcum de gitmez; havale
 *    onayinin normal yolu YONETIM SAYFASIDIR (ham SQL yalniz sayfa/anahtar yoksa).
 */

import { SEMALAR } from "./semalar.js";
import { yeniSiparisNo } from "./siparis-no.js";
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
  // WHATSAPP KANALI (Ege): kalemin malzemesi/rengi ve olcusu sohbette konusulur, siparis
  // ucuna beyan olarak GELMEZ. Katalog kaydi varsa yukaridaki kollar zaten onu bastirdi;
  // buraya dusen kalem katalog disi ozel parcadir. Malzeme fallback'i basmak UYDURMA
  // olurdu ("%15 doluluk" diye bir karar verilmedi) -> nereye bakilacagi soylenir.
  if (satir && satir.kanal === WA_KANAL) {
    return "WhatsApp siparişi — üretim detayı müşteri sohbetinde (Ege) kayıtlı; " +
      "malzeme/ölçü beyanı bu uçtan gelmez.";
  }
  return BASKI_FALLBACK[satir.malzeme] || "Malzemeye uygun genel baskı ayarlarıyla üretilir.";
}

// ---- anahtar ------------------------------------------------------------------

/** Sabit-zamanli string esitligi (erken donus zamanlama sizintisini onler). */
function sabitEsit(a, b) {
  a = String(a || ""); b = String(b || "");
  if (a.length !== b.length) { return false; }
  let fark = 0;
  for (let i = 0; i < a.length; i++) { fark |= a.charCodeAt(i) ^ b.charCodeAt(i); }
  return fark === 0;
}

/** Anahtar gecerli mi? Secret tanimsizsa DAIMA false (ozellik kapali; 404). */
function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  const verilen = request.headers.get("X-Yonet-Anahtar") ||
    url.searchParams.get("anahtar") || "";
  return sabitEsit(verilen, env.YONET_ANAHTAR);
}

/**
 * EGE (WhatsApp botu) ANAHTARI — YALNIZ /wa-siparis ucunu acar. EN AZ YETKI:
 * Ege AYRI bir worker'dir (pruvo-bot deposu, ayri secret seti). Ona YONET_ANAHTAR'i
 * vermek panelin TAMAMINI acardi: butun siparislerin PII'si (/liste), durum degistirme,
 * iptal, uretim dosyasi indirme. Bir siparis YAZMAK icin bunlarin hicbiri gerekmiyor.
 * Bu yuzden ayri, TEK UCA yetkili bir secret tanimlanir:
 *     npx wrangler secret put EGE_ANAHTAR
 * Tanimli DEGILSE bu kol tamamen kapalidir (fail-closed) ve /wa-siparis yalnizca
 * YONET_ANAHTAR ile calisir — yani "acik uc" hicbir konfigurasyonda olusmaz.
 */
function egeAnahtarGecerli(request, url, env) {
  if (!env.EGE_ANAHTAR) { return false; }
  const verilen = request.headers.get("X-Ege-Anahtar") ||
    url.searchParams.get("ege_anahtar") || "";
  return sabitEsit(verilen, env.EGE_ANAHTAR);
}

// ---- yanit yardimcilari (CORS YOK — yonetim same-origin) ----------------------

// ---- KANAL ayraci -------------------------------------------------------------
// 'site'     -> pruvo3d.com self-servis akisi (index.js /baslat). D1 kolonunun DEFAULT'u.
// 'whatsapp' -> Ege'nin (WhatsApp botu) kapattigi siparis (/wa-siparis).
const KANAL_SITE = "site";
const WA_KANAL = "whatsapp";

/**
 * OPSIYONEL KOLON MERDIVENI (index.js sepetiFiyatla'daki desenin AYNISI).
 *
 * `kanal`/`dis_no` kolonlari canli D1'de ancak `python3 tools/d1-sync.py --sema` kosunca
 * olusur. Kolonlu bir SELECT o ALTER'dan ONCE "no such column" ile PATLAR. Bu sarmalayici
 * OKUMA yollarini (liste, siparisGetir) o pencerede AYAKTA tutar: kolonlu sorgu patlarsa
 * AYNI sorgu kolonsuz tekrarlanir, alanlar undefined kalir ve cagiran bugunku davranisina
 * duser. Yani panelin GET/render tarafi goc kosmadan da BOZULMAZ.
 * ⚠️ YAZMA yolunda (/wa-siparis) KULLANILMAZ: orada fail-CLOSED 503 doner — kanal ayraci
 * OLMADAN yazilan bir WhatsApp siparisi panelde SITE siparisi gibi gorunurdu (sessiz hata).
 * Yalniz "no such column" yutulur; baska her hata (D1 down, bind hatasi) YUKARI FIRLAR.
 */
async function kolonMerdiveni(kolonlu, kolonsuz) {
  try {
    return await kolonlu();
  } catch (e) {
    if (!/no such column/i.test(String((e && e.message) || e))) { throw e; }
    return await kolonsuz();
  }
}

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
  const TABAN =
    "SELECT id, siparis_no, tarih, durum, tutar_kurus, kargo_kurus, kdv_kurus, odeme_yontemi," +
    " urunler, kargo_firma, kargo_kodu, durum_gecmisi," +
    " musteri_ad, musteri_tel, musteri_eposta, musteri_adres";
  // kanal/dis_no OPSIYONEL (goc kosmadiysa yok) -> merdiven; yoksa alanlar undefined kalir
  // ve asagida 'site'/'' varsayilanina duser (bugunku ekranin AYNISI).
  const kur = (alanlar) => {
    const secim = alanlar + " FROM siparisler";
    return durum
      ? env.KATALOG.prepare(secim + " WHERE durum = ? ORDER BY id DESC LIMIT ?").bind(durum, limit)
      : env.KATALOG.prepare(secim + " ORDER BY id DESC LIMIT ?").bind(limit);
  };
  const sonuc = await kolonMerdiveni(
    () => kur(TABAN + ", kanal, dis_no").all(),
    () => kur(TABAN).all());
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
        // WhatsApp kaleminde kalemin KENDI linki (k.url) varsa O kullanilir: o kalem
        // katalog id'siyle gelmeyebilir, /urun/<id>/ adresi 404 olurdu. Link YAZILIRKEN
        // dogrulanir (yalniz https://); burada ikinci savunma olarak yine suzulur.
        urun_url: (typeof k.url === "string" && /^https:\/\//i.test(k.url))
          ? k.url
          : siteUrl + "/urun/" + encodeURIComponent(k.id || "") + "/",
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
      // KANAL: kolon yoksa (goc oncesi) ya da bos gelirse 'site' — mevcut satirlarin
      // TAMAMI site siparisidir, ekran bugunku gibi rozet basmaz.
      kanal: s.kanal || KANAL_SITE,
      // Ege'nin KENDI numarasi (PR-yyMMdd-HHmmss, sonek YOK) — Sheet kaydiyla eslesme icin.
      // Panel ID'si ile KARISTIRILMAZ: panelin siparis_no'su yine bu tabloda uretilir.
      dis_no: s.dis_no || "",
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
  const TABAN =
    "SELECT siparis_no, tarih, durum, durum_gecmisi, urunler, tutar_kurus, kargo_kurus," +
    " kdv_kurus, odeme_yontemi, atif," +
    " musteri_ad, musteri_eposta, musteri_adres";
  const kur = (alanlar) => env.KATALOG.prepare(
    alanlar + " FROM siparisler WHERE siparis_no = ?").bind(siparisNo);
  // `kanal` opsiyoneldir (goc kosmadiysa yok): merdiven. Kolon yoksa s.kanal undefined
  // kalir -> asagidaki olcum kapisi bugunku gibi ACIK olur (davranis degismez).
  return kolonMerdiveni(
    () => kur(TABAN + ", kanal").first(),
    () => kur(TABAN).first());
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
  //
  // 🔴 DORDUNCU KAPI — KANAL (1 Agu 2026, WhatsApp siparis ucu): reklam olcumu SITE
  // siparisleri icindir. WhatsApp siparisi tarayicidan gecmez -> `atif` BOSTUR: Meta
  // zaten atlar (user_data-bos) ama GA4 fallback client_id (siparis_no + ".0") ile
  // Purchase'i YINE GONDERIRDI. Sonuc: web disi ciro GA4'te "direct" satis gibi gorunur
  // ve site ROI raporunu sisirir. Bu yuzden kanal 'site' DEGILSE olcum tetiklenmez;
  // atlama SESSIZ DEGIL, olcumLog ile gorunur yazilir.
  // GERIYE UYUM: `kanal` kolonu yoksa (goc kosmadi) s.kanal undefined -> kapi ACIK kalir;
  // mevcut satirlarin hepsi ALTER'dan sonra DEFAULT 'site' alir. Yani site akisinda
  // davranis DEGISMEZ.
  const siteKanali = !s.kanal || s.kanal === KANAL_SITE;
  const olcumluGecis = (hedef === "odendi") && siteKanali;
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
  if (hedef === "odendi" && !siteKanali) {
    // Kanal kapisi (yukari bak). Gecis BASARIYLA yapildiktan sonra loglanir — 409'da
    // yanlis bir "atlandi" satiri uretmeyelim.
    olcumLog({ olay: "Purchase", siparis_no: siparisNo, kaynak: String(s.kanal),
               atlandi: "site-disi-kanal" });
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

// ---- /wa-siparis (WhatsApp / Ege kanali) --------------------------------------

/**
 * POST /api/shop/yonet/wa-siparis — Ege'nin (WhatsApp botu, AYRI depo/worker) kapattigi
 * siparisi AYNI panele yazar. Okan tek yerden takip etsin diye (Okan talebi, 1 Agu 2026).
 *
 * KIRMIZI CIZGILER
 *  - ID SEMASI BURADA URETILIR: siparis_no = PR-yyMMdd-HHmmss-XXX (siparis-no.js, kart/havale
 *    akisiyla AYNI uretec). Ege'nin KENDI numarasi (sonek YOK) siparis_no OLARAK ALINMAZ —
 *    iki sema karisirdi; o numara `dis_no` kolonunda MUTABAKAT ANAHTARI olarak durur.
 *  - PARA: bu uc TAHSILAT YAPMAZ. iyzico'ya gitmez, fiyat HESAPLAMAZ, katalog fiyatina
 *    BAKMAZ. `tutar_kurus` cagirandan gelir ve BOS/0 kalabilir (Okan cogu WhatsApp isini
 *    elle fiyatlandirir) — sunucu-tarafi fiyat kurali SITE akisinin kirmizi cizgisidir ve
 *    orada AYNEN durur, buraya TASINMAZ.
 *  - DURUM: yalniz 'havale-bekliyor' (varsayilan, "odeme bekleniyor") ya da 'odendi'
 *    yazilabilir. Uretim/kargo/tamamlandi gecisleri PANELDEN yapilir (durum makinesi
 *    degismedi) -> bu uc kargolandi/tamamlandi damgasi URETEMEZ.
 *  - IDEMPOTENS: `dis_no` verilirse ayni dis_no ile ikinci cagri YENI siparis ACMAZ,
 *    mevcut kaydi doner ({tekrar:true}). Ege'nin agi kopup yeniden denemesi Okan'in
 *    panelinde ikiz siparis olusturmasin.
 *  - E-POSTA/TELEGRAM GONDERMEZ: musteri zaten WhatsApp'ta konusuyor, ikinci bir kanaldan
 *    "siparisiniz alindi" mesaji cift bildirim olur. (Bilincli kapsam karari.)
 *  - REKLAM OLCUMU TETIKLEMEZ (ne burada ne panelde 'odendi' geciste — durumDegistir'deki
 *    KANAL kapisi). Gerekce orada yazili.
 */

/** Bosluk kirpilmis metin; uzunluk araligi disindaysa null (index.js metin() ile ayni sozlesme). */
function waMetin(v, enAz, enCok) {
  const s = typeof v === "string" ? v.trim() : "";
  return s.length >= enAz && s.length <= enCok ? s : null;
}

/** Tamsayi kurus alani: verilmemisse 0, gecersizse null (cagiran 400 doner). */
function waKurus(v) {
  if (v === undefined || v === null || v === "") { return 0; }
  if (!Number.isInteger(v) || v < 0 || v > 100000000) { return null; }
  return v;
}

/** Urun linkinden katalog id'si: https://<host>/urun/<id>/ -> "<id>". Eslesmezse "". */
function waLinktenId(link) {
  const m = /^https:\/\/[^/]+\/urun\/([a-z0-9-]{1,120})\/?$/i.exec(String(link || ""));
  return m ? m[1].toLowerCase() : "";
}

/** Katalog disi kalem icin GUVENLI sentetik id: "wa-" + baslik slug'i.
 *  "wa-" oneki ZORUNLU: sentetik id GERCEK bir katalog id'sine denk gelirse panel o urunun
 *  baski notunu ve R2 dosyalarini bu kaleme yapistirirdi (yanlis uretim dosyasi = pahali
 *  hata). Onek carpismayi yapisal olarak imkansiz kilar. */
function waSentetikId(baslik) {
  const TR = { "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u" };
  const slug = String(baslik || "").toLowerCase()
    .replace(/[çğıöşüâîû]/g, (c) => TR[c] || c)
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
  return "wa-" + (slug || "parca");
}

/** Kalem dizisini coz. Hata -> {hata}; basari -> {satirlar, kalemToplamKurus}. */
function waKalemleriCoz(urunler) {
  const SECENEK = globalThis.PRUVO_SECENEK;
  const enAzAdet = (SECENEK && SECENEK.ADET_EN_AZ) || 1;
  const enCokAdet = (SECENEK && SECENEK.ADET_EN_COK) || 99;
  if (!Array.isArray(urunler) || urunler.length < 1 || urunler.length > 20) {
    return { hata: "gecersiz-urunler" };
  }
  const satirlar = [];
  let toplam = 0;
  for (const u of urunler) {
    if (!u || typeof u !== "object") { return { hata: "gecersiz-urun" }; }
    const ad = waMetin(u.ad, 2, 200);
    if (!ad) { return { hata: "urun-ad" }; }
    // Link OPSIYONEL ama verildiyse SADECE https:// kabul edilir: bu deger yonetim
    // sayfasinda href olarak basilir -> javascript:/data: semasi yolu kapali kalsin.
    let link = "";
    if (u.link !== undefined && u.link !== null && u.link !== "") {
      link = waMetin(u.link, 12, 300) || "";
      if (!link || !/^https:\/\//i.test(link)) { return { hata: "urun-link" }; }
    }
    const adet = (u.adet === undefined || u.adet === null) ? 1 : u.adet;
    if (!Number.isInteger(adet) || adet < enAzAdet || adet > enCokAdet) {
      return { hata: "urun-adet" };
    }
    const tutar = waKurus(u.tutar_kurus);
    if (tutar === null) { return { hata: "urun-tutar" }; }
    toplam += tutar;
    const id = waLinktenId(link) || waSentetikId(ad);
    // Satir bicimi SITE akisiyla AYNI anahtarlari tasir (liste() ve yazdir.py bunu okur).
    // malzeme/renk BOS: WhatsApp'ta beyan sohbette kalir, uydurulmaz (bkz. baskiOnerisi).
    satirlar.push({
      id: id, baslik: ad, malzeme: "", renk: "", renk_ozel: "",
      adet: adet, birim_kurus: adet > 0 ? Math.floor(tutar / adet) : tutar,
      tutar_kurus: tutar,
      kanal: WA_KANAL,
      ...(link ? { url: link } : {}),
    });
  }
  return { satirlar, kalemToplamKurus: toplam };
}

export async function waSiparis(request, env) {
  let govde;
  try { govde = await request.json(); } catch (e) { return yjson({ hata: "gecersiz-json" }, 400); }
  if (!govde || typeof govde !== "object") { return yjson({ hata: "gecersiz-istek" }, 400); }

  // --- musteri (ad + tel + adres ZORUNLU; eposta opsiyonel — WhatsApp'ta cogu zaman yok) ---
  const m = govde.musteri || {};
  const ad = waMetin(m.ad, 2, 120);
  if (!ad) { return yjson({ hata: "musteri-ad" }, 400); }
  const tel = (typeof m.tel === "string" ? m.tel : "").replace(/[^0-9]/g, "");
  if (tel.length < 10 || tel.length > 15) { return yjson({ hata: "musteri-tel" }, 400); }
  const adres = waMetin(m.adres, 5, 500);
  if (!adres) { return yjson({ hata: "musteri-adres" }, 400); }
  let eposta = "";
  if (m.eposta !== undefined && m.eposta !== null && m.eposta !== "") {
    eposta = waMetin(m.eposta, 6, 200) || "";
    if (!eposta || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(eposta)) {
      return yjson({ hata: "musteri-eposta" }, 400);
    }
  }

  // --- odeme yontemi: sessiz varsayilan YOK (site akisindaki kural burada da gecerli) ---
  const odeme = govde.odeme;
  if (odeme !== "kart" && odeme !== "havale") { return yjson({ hata: "gecersiz-odeme" }, 400); }

  // --- durum: yalniz iki deger; varsayilan 'havale-bekliyor' (= odeme bekleniyor) ---
  const durum = (govde.durum === undefined || govde.durum === null || govde.durum === "")
    ? "havale-bekliyor" : govde.durum;
  if (durum !== "havale-bekliyor" && durum !== "odendi") {
    return yjson({ hata: "gecersiz-durum" }, 400);
  }

  // --- kalemler ---
  const kc = waKalemleriCoz(govde.urunler);
  if (kc.hata) { return yjson({ hata: kc.hata }, 400); }
  const { satirlar, kalemToplamKurus } = kc;

  // --- tutar: govdeden gelen toplam, yoksa kalem toplamlari (ikisi de 0 olabilir) ---
  const tutarAlani = waKurus(govde.tutar_kurus);
  if (tutarAlani === null) { return yjson({ hata: "gecersiz-tutar" }, 400); }
  const tutarKurus = tutarAlani > 0 ? tutarAlani : kalemToplamKurus;
  const kargoKurus = waKurus(govde.kargo_kurus);
  if (kargoKurus === null) { return yjson({ hata: "gecersiz-kargo" }, 400); }
  // KDV dokumu: oran TEK KAYNAK secenekler.js (index.js ile ayni fonksiyon). Tutar 0 ise
  // dokum de 0'dir — "bilinmiyor" demek, sifir KDV beyani DEGIL (fiyat sonra elle girilir).
  const SECENEK = globalThis.PRUVO_SECENEK;
  const kdvKurus = (SECENEK && typeof SECENEK.kdvAyristir === "function")
    ? SECENEK.kdvAyristir(tutarKurus + kargoKurus).kdvKurus : 0;

  // --- dis_no (Ege'nin kendi numarasi) — idempotens anahtari ---
  let disNo = "";
  if (govde.dis_no !== undefined && govde.dis_no !== null && govde.dis_no !== "") {
    disNo = waMetin(govde.dis_no, 3, 40) || "";
    if (!disNo || !/^[A-Za-z0-9_-]{3,40}$/.test(disNo)) { return yjson({ hata: "gecersiz-dis-no" }, 400); }
  }

  // --- SEMA KAPISI (FAIL-CLOSED) + IDEMPOTENS + YAZMA ---------------------------
  // `kanal`/`dis_no` kolonlari canli D1'de ancak `python3 tools/d1-sync.py --sema` kosunca
  // olusur. Kolonsuz bir INSERT teknik olarak calisirdi ama kayit panelde SITE siparisi
  // gibi gorunurdu (kanal rozeti yok, olcum kapisi devre disi) — sessiz ve geri donusu
  // zahmetli bir hata. Bu yuzden OKUMA yollarinin aksine burada FAIL-CLOSED: kolon yoksa
  // hicbir sey yazilmaz, gurultulu 503 + ne yapilacagi doner.
  try {
    // IDEMPOTENS: ayni dis_no ile ikinci cagri yeni siparis ACMAZ (Ege'nin agi kopup
    // yeniden denemesi Okan'in panelinde ikiz siparis olusturmasin).
    if (disNo) {
      const varOlan = await env.KATALOG.prepare(
        "SELECT siparis_no, durum FROM siparisler WHERE kanal = ? AND dis_no = ?"
      ).bind(WA_KANAL, disNo).first();
      if (varOlan) {
        return yjson({ ok: true, tekrar: true, siparis_no: varOlan.siparis_no,
                       durum: varOlan.durum, kanal: WA_KANAL, dis_no: disNo }, 200);
      }
    }

    const siparisNo = await yeniSiparisNo(env);
    const simdi = new Date().toISOString();
    // token NULL: /donus bu satiri HICBIR iyzico token'iyla bulamaz (havale akisiyla ayni
    // koruma) -> WhatsApp siparisinin durumu istemciden degistirilemez.
    await env.KATALOG.prepare(
      "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, kargo_kurus," +
      " kdv_kurus, odeme_yontemi, sozlesme_onay, urunler, filament, renk," +
      " musteri_ad, musteri_tel, musteri_eposta, musteri_adres, atif, durum_gecmisi," +
      " kanal, dis_no)" +
      " VALUES (?, NULL, ?, ?, ?, ?, ?, ?, '', ?, '', '', ?, ?, ?, ?, '', ?, ?, ?)"
    ).bind(
      siparisNo, simdi, durum, tutarKurus, kargoKurus, kdvKurus, odeme,
      JSON.stringify(satirlar),
      ad, tel, eposta, adres,
      gecmiseEkle("", durum), WA_KANAL, disNo
    ).run();

    return yjson({ ok: true, siparis_no: siparisNo, durum: durum, kanal: WA_KANAL,
                   dis_no: disNo, tutar_kurus: tutarKurus, kargo_kurus: kargoKurus,
                   kdv_kurus: kdvKurus }, 201);
  } catch (e) {
    if (!/no such column/i.test(String((e && e.message) || e))) { throw e; }
    console.error("wa-siparis: D1 semasinda kanal/dis_no kolonu YOK -> yazma reddedildi " +
                  "(coz: python3 tools/d1-sync.py --sema)");
    return yjson({ hata: "sema-goc-gerekli",
                   not: "siparisler.kanal / siparisler.dis_no kolonlari yok; " +
                        "python3 tools/d1-sync.py --sema calistirilmali" }, 503);
  }
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
 * Anahtar YOK/YANLIS -> 404 (varlik sizmasin). telegram: index.js'in telegram fonksiyonu.
 */
export async function yonet(request, env, url, ctx, altYol, telegram) {
  const m = request.method;
  // WHATSAPP SIPARIS UCU — IKI anahtardan biri yeter: yonetim anahtari (Okan) ya da
  // yalnizca bu uca yetkili EGE_ANAHTAR (bkz. egeAnahtarGecerli). Ikisi de yok/yanlissa
  // /yonet* ile AYNI davranis: 404 (ucun varligi sizmaz). EGE_ANAHTAR yalnizca BU kolda
  // okunur -> /liste, /durum, /kargo, /stl onunla ACILMAZ.
  if (altYol === "/wa-siparis" && m === "POST") {
    if (!anahtarGecerli(request, url, env) && !egeAnahtarGecerli(request, url, env)) {
      return yon404();
    }
    return waSiparis(request, env);
  }
  if (!anahtarGecerli(request, url, env)) { return yon404(); }
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
/* KANAL rozeti — yalniz site DISI kanalda basilir (WhatsApp/Ege). Site siparisinde
   ekran bugunku gibi kalir (rozet HIC olusmaz). */
.rozet.kanal{background:#dcfce7;color:#14532d}
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
var ANAHTAR=new URLSearchParams(location.search).get("anahtar")||"";
function esc(s){s=(s==null?"":""+s);return s.replace(/&/g,"&amp;").replace(/</g,"&lt;")
 .replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function tl(k){k=Math.max(0,Math.floor(+k||0));var t=Math.floor(k/100),ku=(""+(k%100)).padStart(2,"0");
 return (""+t).replace(/\\B(?=(\\d{3})+(?!\\d))/g,".")+","+ku+" TL";}
async function api(yol,secenek){
 secenek=secenek||{};secenek.headers=Object.assign({"X-Yonet-Anahtar":ANAHTAR},secenek.headers||{});
 var c=await fetch("/api/shop/yonet"+yol,secenek);
 var v=null;try{v=await c.json();}catch(e){}
 return {kod:c.status,govde:v};
}
function durumRozet(d){return '<span class="rozet '+esc(d)+'">'+esc(d)+'</span>';}
function satirHtml(no,k){
 var indir;
 if(k.parametrik){
  indir='<a class="indir" href="/api/shop/yonet/stl?siparis_no='+encodeURIComponent(no)+
   '&kalem='+k.kalem+'&anahtar='+encodeURIComponent(ANAHTAR)+'">STL üret + indir</a>';
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
   '&siparis_no='+encodeURIComponent(no)+'&anahtar='+encodeURIComponent(ANAHTAR)+'">'+
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
 // KANAL rozeti + Ege'nin kendi numarasi: yalniz site DISI siparislerde basilir.
 // Site siparisinde (kanal yok ya da "site") kart bugunku HALIYLE kalir.
 var kanalRozet=(s.kanal&&s.kanal!=="site")?'<span class="rozet kanal">'+esc(s.kanal)+'</span>':'';
 var disNo=s.dis_no?'<div class="kucuk">Ege sipariş no: '+esc(s.dis_no)+'</div>':'';
 return '<div class="kart">'+
  '<div class="ust"><span class="no">'+esc(s.siparis_no)+'</span>'+durumRozet(s.durum)+kanalRozet+
   '<span class="kucuk">'+esc((s.tarih||"").slice(0,16).replace("T"," "))+' · '+esc(s.odeme_yontemi)+'</span></div>'+
  disNo+
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
 if(r.kod!==200){m.innerHTML='<p class="hata">Liste alınamadı ('+r.kod+'). Anahtar doğru mu?</p>';return;}
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
