/**
 * pruvo-shop — self-servis satin alma worker'i.
 *
 * Uclar (site Cloudflare route'u: pruvo3d.com/api/shop/*):
 *   POST /api/shop/baslat   -> sepet + musteri -> D1'den fiyat, iyzico CF initialize -> {url, no}
 *   POST /api/shop/donus    -> iyzico callback (token) -> retrieve DOGRULAMA -> siparis 'odendi'
 *                              + Telegram bildirimi + musteriyi siteye yonlendir
 *
 * KIRMIZI CIZGILER (tools/paket-shop-odeme.md):
 *  - Fiyat SUNUCUDA hesaplanir: sepetteki id'lerin fiyati D1 `urunler`den okunur, katsayi
 *    uygulanir. Istemciden gelen HICBIR tutar alani okunmaz.
 *  - `retrieve` ile sunucu-tarafi dogrulama olmadan siparis 'odendi' OLMAZ; musterinin donus
 *    URL'sine/istemci verisine guvenilmez.
 *  - Callback idempotent: ayni token kac kez gelirse gelsin TEK siparis, TEK bildirim.
 *  - parametrik:true ve fiyati bos urunler bu akisin DISINDA (WhatsApp kanali).
 *
 * TEK KAYNAK: katsayi/renk/adet kurallari ve fiyat hesabi /secenekler.js'ten gelir (front ile
 * AYNI dosya; ikinci kopya YOK). Import yan etkilidir: dosya IIFE olup globalThis'e yazar.
 */

import AYAR from "../config.json";
import "../../secenekler.js";
import { cfBaslat, cfDetay } from "./iyzico.js";
import { parametrikHesapla } from "./parametrik.js";
import { SEMALAR } from "./semalar.js";

const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi — fiyat kurali tek kaynagi yok"); }

// ---------------------------------------------------------------- yardimcilar

function json(veri, kod, env) {
  return new Response(JSON.stringify(veri), {
    status: kod || 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...cors(env),
    },
  });
}

// Ayni alan adindan (route) sunuldugu icin CORS normalde devreye girmez; workers.dev
// uzerinden test/yedek erisim icin site origin'ine izin verilir.
function cors(env) {
  return {
    "Access-Control-Allow-Origin": (env && env.SITE_URL) || "https://pruvo3d.com",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

/** Kurusu para metnine cevirir — TAMSAYI aritmetigi (toFixed FP'ye dokunur): 43290 -> "432.90".
 *  iyzico nokta bekler; ekranda/Telegram'da virgullu gosterilir. */
function kurusMetin(kurus) {
  return Math.floor(kurus / 100) + "." + String(kurus % 100).padStart(2, "0");
}

function kurusTL(kurus) {
  return kurusMetin(kurus).replace(".", ",") + " TL";
}

function siparisNoUret() {
  return "SP" + Date.now().toString(36).toUpperCase() +
    Math.floor(1000 + Math.random() * 9000);
}

function yonlendir(env, sonuc, siparisNo) {
  const hedef = env.SITE_URL + "/?siparis=" + sonuc +
    (siparisNo ? "&no=" + encodeURIComponent(siparisNo) : "");
  return new Response(null, { status: 303, headers: { "Location": hedef } });
}

// ---------------------------------------------------------------- dogrulama

function metin(v, enAz, enCok) {
  const s = typeof v === "string" ? v.trim() : "";
  return s.length >= enAz && s.length <= enCok ? s : null;
}

/** Istek govdesini dogrula; hata varsa {hata}, yoksa {musteri, kalemler}. Istemciden gelen
 *  tutar/fiyat alanlari BILEREK okunmaz. */
function istekCoz(govde) {
  if (!govde || typeof govde !== "object") return { hata: "gecersiz-istek" };

  const m = govde.musteri || {};
  const ad = metin(m.ad, 3, 120);
  const tel = (typeof m.tel === "string" ? m.tel : "").replace(/[^0-9]/g, "");
  const eposta = metin(m.eposta, 6, 200);
  const adres = metin(m.adres, 10, 500);
  const sehir = metin(m.sehir, 2, 60);
  const tckn = (typeof m.tckn === "string" ? m.tckn : "").replace(/[^0-9]/g, "");
  if (!ad) return { hata: "musteri-ad" };
  if (tel.length < 10 || tel.length > 13) return { hata: "musteri-tel" };
  if (!eposta || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(eposta)) return { hata: "musteri-eposta" };
  if (!adres) return { hata: "musteri-adres" };
  if (!sehir) return { hata: "musteri-sehir" };
  if (tckn && tckn.length !== 11) return { hata: "musteri-tckn" };

  const sepet = govde.sepet;
  if (!Array.isArray(sepet) || sepet.length < 1 || sepet.length > AYAR.sepet_en_cok_kalem) {
    return { hata: "gecersiz-sepet" };
  }
  const kalemler = [];
  for (const k of sepet) {
    if (!k || typeof k !== "object") return { hata: "gecersiz-kalem" };
    const id = typeof k.id === "string" && /^[a-z0-9-]{1,120}$/.test(k.id) ? k.id : null;
    // Malzeme/renk listeleri secenekler.js'ten (tek kaynak) — worker'da ikinci kopya yok.
    const malzeme = Object.prototype.hasOwnProperty.call(SECENEK.FILAMENT_FARK, k.malzeme)
      ? k.malzeme : null;
    const renk = SECENEK.RENK_SECENEKLERI.includes(k.renk) ? k.renk : null;
    // Adet 1-99 (Okan, 16 Tem): araliga CEKILMEZ, aralik disi istek REDDEDILIR — istemcinin
    // 500 adet gondermesi sessizce 99'a inip musteriyi sasirtmasin.
    const adet = Number.isInteger(k.adet) && k.adet >= SECENEK.ADET_EN_AZ &&
                 k.adet <= SECENEK.ADET_EN_COK ? k.adet : null;
    if (!id) return { hata: "gecersiz-kalem" };
    if (!malzeme) return { hata: "gecersiz-malzeme", id: id };
    if (!renk) return { hata: "gecersiz-renk", id: id };
    if (!adet) return { hata: "gecersiz-adet", id: id };
    // BOY: D1 katalogunda boy_secenekleri YOK -> sunucu boy farkini dogrulayamaz. Bugun hicbir
    // urunde kullanilmiyor; ileride eklenirse sessizce 0 TL fark uygulayip musteriden eksik
    // tahsil etmektense istek REDDEDILIR (D1'e kolon eklenince burasi acilir).
    if (k.boy_etiket) return { hata: "boy-desteklenmiyor", id: id };
    const renk_ozel = renk === "Diğer" ? metin(k.renk_ozel, 1, 60) : "";
    if (renk === "Diğer" && !renk_ozel) return { hata: "renk-ozel-bos", id: id };
    // Parametreler ISTEMCIDEN alinir ama fiyat/hacim ONDAN OKUNMAZ — sunucu yeniden hesaplar
    // (parametrik.js). Istemcinin yolladigi hacim_mm3/parametrik_fiyat_kurus BILEREK atilir.
    const parametreler = (k.parametreler && typeof k.parametreler === "object" &&
                          !Array.isArray(k.parametreler)) ? k.parametreler : null;
    kalemler.push({ id, malzeme, renk, renk_ozel: renk_ozel || "", boy_etiket: null, adet,
                    parametreler });
  }
  return { musteri: { ad, tel, eposta, adres, sehir, tckn }, kalemler };
}

// ---------------------------------------------------------------- /baslat

async function baslat(request, env, url) {
  let govde;
  try {
    govde = await request.json();
  } catch (e) {
    return json({ hata: "gecersiz-json" }, 400, env);
  }
  const c = istekCoz(govde);
  if (c.hata) return json(c, 400, env);
  const { musteri, kalemler } = c;

  // FIYAT SUNUCUDA: sepetteki id'lerin guncel kaydi D1 katalogundan.
  const idler = [...new Set(kalemler.map((k) => k.id))];
  const yertut = idler.map(() => "?").join(",");
  const sonuc = await env.KATALOG.prepare(
    "SELECT id, baslik, kategori, fiyat, parametrik FROM urunler WHERE id IN (" + yertut + ")"
  ).bind(...idler).all();
  const katalog = new Map((sonuc.results || []).map((u) => [u.id, u]));

  const satirlar = [];
  let toplamKurus = 0;
  for (const k of kalemler) {
    const u = katalog.get(k.id);
    if (!u) return json({ hata: "bilinmeyen-urun", id: k.id }, 400, env);

    let birimKurus, ekAlanlar = {};
    if (u.parametrik) {
      // Olcuye ozel (sari seri). SUNUCU-TARAFI YENIDEN HESAP altyapisi hazir (parametrik.js:
      // sema + hacim.js + taban fiyat; istemcinin hacim/fiyat alanlari OKUNMAZ), ama kanal
      // SECENEK.PARAMETRIK_ODEME_ACIK ile kapali: taban fiyatlar bos (18/18 null) ve mimar
      // karari beklemede -> kalem WhatsApp'a yonlendirilir (kabul testi 5).
      if (!SECENEK.PARAMETRIK_ODEME_ACIK) {
        return json({ hata: "parametrik-urun", id: k.id,
                      mesaj: "Ölçüye özel ürünler için WhatsApp'tan teklif alın." }, 400, env);
      }
      const sema = SEMALAR.get(k.id);
      if (!sema) {
        // Semasiz parametrik urun (konfiguratoru yok) -> her zaman WhatsApp kanali.
        return json({ hata: "parametrik-urun", id: k.id,
                      mesaj: "Ölçüye özel ürünler için WhatsApp'tan teklif alın." }, 400, env);
      }
      const ph = parametrikHesapla(k, SECENEK, sema);
      if (ph.hata) { return json({ hata: ph.hata, id: k.id, alan: ph.alan }, 400, env); }
      birimKurus = ph.birimKurus;
      ekAlanlar = { parametreler: ph.parametreler, parametre_detay: ph.detay,
                    hacim_mm3: ph.hacimMm3 };
    } else {
      // HESAP TEK KAYNAK: front'un gosterdigi fiyati ureten fonksiyonun AYNISI (secenekler.js).
      // D1'de boy_secenekleri yok; boy'lu kalem zaten yukarida reddedildi (bkz. istekCoz).
      const ozet = SECENEK.satirOzeti(
        { kategori: u.kategori, fiyat: u.fiyat, parametrik: false, boy_secenekleri: [] },
        { id: k.id, malzeme: k.malzeme, renk: k.renk, renk_ozel: k.renk_ozel,
          boy_etiket: null, adet: 1 });
      if (!ozet.odenebilir || !(ozet.birimKurus > 0)) {
        return json({ hata: "fiyatsiz-urun", id: k.id }, 400, env);
      }
      birimKurus = ozet.birimKurus;
    }

    // Ara yuvarlama YOK: birim kurus x adet, kalem tutari kurusuyla toplanir.
    const tutar = birimKurus * k.adet;
    toplamKurus += tutar;
    satirlar.push({
      id: k.id, baslik: u.baslik, kategori: u.kategori,
      malzeme: k.malzeme, renk: k.renk, renk_ozel: k.renk_ozel, adet: k.adet,
      birim_kurus: birimKurus, tutar_kurus: tutar, ...ekAlanlar,
    });
  }
  if (!(toplamKurus > 0)) return json({ hata: "gecersiz-tutar" }, 400, env);

  // KARGO (Okan, 16 Tem — KESIN; tools/paket-shop-kargo.md): urun toplami < 2.500,00 TL ->
  // 250,00 TL; >= 2.500,00 TL (tam 2.500 dahil) -> bedava. Kural tek kaynagi secenekler.js
  // (sepet paneli ayni fonksiyonla gosterir); hesap BURADA — istemcinin yolladigi kargo/tutar
  // alanlari istekCoz'da zaten okunmuyor. Kargo urun fiyatina yedirilmez, ayri kalemdir.
  const kargoKurus = SECENEK.kargoKurus(toplamKurus);
  const tahsilatKurus = toplamKurus + kargoKurus;

  const siparisNo = siparisNoUret();
  const adParcalari = musteri.ad.split(/\s+/);
  const soyad = adParcalari.length > 1 ? adParcalari.pop() : adParcalari[0];
  const isim = adParcalari.join(" ") || soyad;
  // tel normalize (yalniz rakam): "0532..." -> +90532..., "90532..." -> +90532..., "532..." -> +90532...
  const gsm = musteri.tel.startsWith("90") && musteri.tel.length === 12 ? "+" + musteri.tel
    : musteri.tel.startsWith("0") ? "+9" + musteri.tel
    : "+90" + musteri.tel;
  const acikAdres = musteri.adres + " / " + musteri.sehir;
  const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";

  const init = await cfBaslat(env, {
    locale: "tr",
    conversationId: siparisNo,
    // Tutar D1'den hesaplanan urun toplami + kargo — istemcinin gonderdigi hicbir sayi giremez.
    price: kurusMetin(tahsilatKurus),
    paidPrice: kurusMetin(tahsilatKurus),
    currency: "TRY",
    basketId: siparisNo,
    paymentGroup: "PRODUCT",
    callbackUrl: url.origin + "/api/shop/donus",
    enabledInstallments: AYAR.taksit,
    buyer: {
      id: siparisNo,
      name: isim,
      surname: soyad,
      gsmNumber: gsm,
      email: musteri.eposta,
      // iyzico buyer.identityNumber zorunlu alan; musteri TCKN girmediyse jenerik deger
      // gonderilir (yaygin uygulama; fatura icin gerekirse Okan musteriden ayrica alir).
      identityNumber: musteri.tckn || "11111111111",
      registrationAddress: acikAdres,
      ip: ip,
      city: musteri.sehir,
      country: "Turkey",
    },
    shippingAddress: { contactName: musteri.ad, city: musteri.sehir, country: "Turkey", address: acikAdres },
    billingAddress: { contactName: musteri.ad, city: musteri.sehir, country: "Turkey", address: acikAdres },
    basketItems: satirlar.map((s) => ({
      id: s.id,
      name: (s.baslik + " (" + s.malzeme + ", " + (s.renk_ozel || s.renk) +
             (s.adet > 1 ? ", " + s.adet + " adet" : "") + ")").slice(0, 120),
      category1: s.kategori || "Genel",
      itemType: "PHYSICAL",
      // iyzico: basketItems price toplami = price. Kurus toplaminda birebir tutar.
      price: kurusMetin(s.tutar_kurus),
    })).concat(kargoKurus > 0 ? [{
      // Kargo AYRI kalem (urun fiyatina yedirilmez); boylece kalem toplami = tahsilat kurali
      // kurusuyla korunur. Bedava kargoda kalem hic eklenmez (0 TL kalemi iyzico kabul etmez).
      id: "gonderim", name: "Gönderim (kargo)", category1: "Kargo",
      itemType: "PHYSICAL", price: kurusMetin(kargoKurus),
    }] : []),
  });

  if (init.status !== "success" || !init.token || !init.paymentPageUrl) {
    console.error("iyzico initialize hatasi:", init.errorCode, init.errorMessage);
    return json({ hata: "odeme-baslatilamadi" }, 502, env);
  }

  // Siparis kaydi 'bekliyor' olarak dusulur; 'odendi' SADECE /donus'taki retrieve
  // dogrulamasindan gecerse olur. INSERT patlarsa musteri henuz odememis olur (token kullanilmamis).
  await env.KATALOG.prepare(
    "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, kargo_kurus," +
    " urunler, filament, renk, musteri_ad, musteri_tel, musteri_eposta, musteri_adres)" +
    " VALUES (?, ?, ?, 'bekliyor', ?, ?, ?, ?, ?, ?, ?, ?, ?)"
  ).bind(
    siparisNo, init.token, new Date().toISOString(), toplamKurus, kargoKurus,
    JSON.stringify(satirlar),
    [...new Set(satirlar.map((s) => s.malzeme))].join("+"),
    // "Diğer" renkte musterinin yazdigi renk kaydedilir (uretim bunu okur), yoksa liste rengi
    [...new Set(satirlar.map((s) => s.renk_ozel || s.renk))].join("+"),
    musteri.ad, musteri.tel, musteri.eposta, acikAdres
  ).run();

  return json({ url: init.paymentPageUrl, no: siparisNo }, 200, env);
}

// ---------------------------------------------------------------- /donus

async function tokenCoz(request) {
  const tip = (request.headers.get("Content-Type") || "").toLowerCase();
  try {
    if (tip.includes("json")) {
      const g = await request.json();
      return typeof g.token === "string" ? g.token : null;
    }
    const f = await request.formData();
    const t = f.get("token");
    return typeof t === "string" ? t : null;
  } catch (e) {
    return null;
  }
}

async function donus(request, env, ctx) {
  // Musteri callback URL'ini elle GET ile acarsa (yenileme vb.) siteye don.
  if (request.method === "GET") return yonlendir(env, "hata", "");

  const token = await tokenCoz(request);
  if (!token || token.length > 200) return json({ hata: "token-yok" }, 400, env);

  // Uydurma token: bizde kaydi yok -> siparis OLUSMAZ, 4xx (kabul testi 2).
  const siparis = await env.KATALOG.prepare(
    "SELECT siparis_no, durum, tutar_kurus, kargo_kurus, urunler," +
    " musteri_ad, musteri_tel, musteri_adres FROM siparisler WHERE token = ?"
  ).bind(token).first();
  if (!siparis) return json({ hata: "bilinmeyen-token" }, 404, env);

  // SUNUCU-TARAFI DOGRULAMA: sonuc iyzico'dan retrieve ile alinir; istemciye guvenilmez.
  const det = await cfDetay(env, token);

  // ALTYAPI HATASI (or. 1001 anahtar/URL uyusmazligi, gecici iyzico hatasi; DEVAM.md bulgusu,
  // 16 Tem): retrieve CEVAP VEREMEDIYSE odemenin gercek durumu BILINMIYOR — 'basarisiz' yazmak
  // parasi cekilmis musteriyi sessizce dusurur. 'incele' + yuksek sesli bildirim; otomatik
  // onay YOK. Sonraki gecerli callback'te retrieve duzelirse 'odendi'ye ilerleyebilir
  // (asagidaki UPDATE'ler durum <> 'odendi' kosuluyla calisir).
  if (!det || det.status !== "success") {
    await env.KATALOG.prepare(
      "UPDATE siparisler SET durum = 'incele' WHERE token = ? AND durum = 'bekliyor'"
    ).bind(token).run();
    ctx.waitUntil(telegram(env,
      "⚠️ PRUVO shop RETRIEVE HATASI — " + siparis.siparis_no +
      "\niyzico cevabi: " + (det ? (det.errorCode || "?") + " " + (det.errorMessage || "") : "yok") +
      "\nOdeme durumu BILINMIYOR — siparis 'incele' durumunda, elle bak."));
    return yonlendir(env, "hata", siparis.siparis_no);
  }

  // Retrieve CEVAP VERDI ve odeme basarili degil (or. kart reddi) -> gercek 'basarisiz'.
  const odendi = det.paymentStatus === "SUCCESS";
  if (!odendi) {
    await env.KATALOG.prepare(
      "UPDATE siparisler SET durum = 'basarisiz' WHERE token = ? AND durum = 'bekliyor'"
    ).bind(token).run();
    return yonlendir(env, "hata", siparis.siparis_no);
  }

  // Tutar/kimlik denetimi: iyzico'daki odeme bizim hesapladigimiz siparisle eslesmeli.
  // Karsilastirma KURUSTA ve TAM: iyzico "432.9"/"432.90" dondurse de kurus tamsayisi ayni;
  // 1 kurus fark bile gercek uyusmazliktir (tolerans yok) -> 'incele'.
  // TAHSILAT = urun toplami + kargo (kargo_kurus eski satirlarda/kolonsuz gecmiste 0).
  const beklenenTahsilat = siparis.tutar_kurus + (siparis.kargo_kurus || 0);
  const paraUyar = Math.round(parseFloat(det.paidPrice) * 100) !== beklenenTahsilat;
  const kimlikUyar = (det.conversationId && det.conversationId !== siparis.siparis_no) ||
                     (det.basketId && det.basketId !== siparis.siparis_no);
  if (paraUyar || kimlikUyar) {
    // Odeme iyzico'da BASARILI ama bizim kayitla uyusmuyor: otomatik onaylanmaz,
    // insan incelemesine dusurulur + yuksek sesle bildirilir.
    await env.KATALOG.prepare(
      "UPDATE siparisler SET durum = 'incele', iyzico_odeme_id = ? WHERE token = ? AND durum <> 'odendi'"
    ).bind(String(det.paymentId || ""), token).run();
    ctx.waitUntil(telegram(env,
      "⚠️ PRUVO shop TUTARSIZLIK — " + siparis.siparis_no +
      "\niyzico paidPrice: " + det.paidPrice + " / bizim: " + kurusTL(beklenenTahsilat) +
      " (urun " + kurusTL(siparis.tutar_kurus) + " + kargo " + kurusTL(siparis.kargo_kurus || 0) + ")" +
      "\nconversationId: " + det.conversationId + "\nToken: " + token.slice(0, 12) + "…" +
      "\nSiparis 'incele' durumunda, elle bak."));
    return json({ hata: "tutar-uyusmuyor" }, 409, env);
  }

  // IDEMPOTENT kapanis: ayni token ikinci kez gelirse changes=0 -> bildirim de tekrarlanmaz.
  const g = await env.KATALOG.prepare(
    "UPDATE siparisler SET durum = 'odendi', iyzico_odeme_id = ? WHERE token = ? AND durum <> 'odendi'"
  ).bind(String(det.paymentId || ""), token).run();

  if (g.meta && g.meta.changes > 0) {
    ctx.waitUntil(telegram(env, siparisMesaji(siparis, det)));
  }
  return yonlendir(env, "ok", siparis.siparis_no);
}

function siparisMesaji(siparis, det) {
  let satirlar = [];
  try { satirlar = JSON.parse(siparis.urunler) || []; } catch (e) { satirlar = []; }
  const kalemler = satirlar.map((s) =>
    "• " + s.baslik + " — " + s.malzeme + " / " + (s.renk_ozel || s.renk) +
    " × " + s.adet + " = " + kurusTL(s.tutar_kurus)).join("\n");
  const kargo = siparis.kargo_kurus || 0;
  return "🛒 YENI SIPARIS (odendi) — " + siparis.siparis_no +
    "\n" + kalemler +
    "\nAra toplam: " + kurusTL(siparis.tutar_kurus) +
    "\nGönderim: " + (kargo > 0 ? kurusTL(kargo) : "Bedava") +
    "\nGenel toplam: " + kurusTL(siparis.tutar_kurus + kargo) +
    "\nMusteri: " + siparis.musteri_ad + " — " + siparis.musteri_tel +
    "\nAdres: " + siparis.musteri_adres +
    "\niyzico odeme id: " + (det.paymentId || "?");
}

async function telegram(env, mesaj) {
  if (!env.TELEGRAM_TOKEN) return; // bildirim kurulmamissa odeme akisini bloklama
  try {
    await fetch((env.TELEGRAM_API || "https://api.telegram.org") +
      "/bot" + env.TELEGRAM_TOKEN + "/sendMessage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT, text: mesaj }),
    });
  } catch (e) {
    console.error("telegram bildirimi gonderilemedi:", e);
  }
}

// ---------------------------------------------------------------- giris

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const yol = url.pathname.replace(/^\/api\/shop/, "") || "/";
    try {
      if (request.method === "OPTIONS") {
        return new Response(null, { status: 204, headers: cors(env) });
      }
      // NOT: /ayarlar ucu KALDIRILDI — front katsayi/renk listesini /secenekler.js'ten alir
      // (tek kaynak). Worker'in ayni listeyi ikinci bir ucdan yayinlamasi drift kapisi acardi.
      if (yol === "/baslat" && request.method === "POST") return await baslat(request, env, url);
      if (yol === "/donus") return await donus(request, env, ctx);
      return json({ hata: "bulunamadi" }, 404, env);
    } catch (e) {
      console.error("pruvo-shop hata:", e && e.stack || e);
      return json({ hata: "sunucu-hatasi" }, 500, env);
    }
  },
};
