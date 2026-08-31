/**
 * pruvo-shop — self-servis satin alma worker'i.
 *
 * Uclar (site Cloudflare route'u: pruvo3d.com/api/shop/*):
 *   POST /api/shop/baslat   -> sepet + musteri (+ zorunlu sozlesme_onay) -> D1'den fiyat +
 *                              KARGO + KDV dokumu (sunucu hesabi),
 *                              odeme:"kart" -> iyzico CF initialize -> {url, no}
 *                              odeme:"havale" -> D1 'havale-bekliyor' + Telegram ->
 *                              {havale:true, no, iban, unvan, tutar, kdv dokumu}
 *   POST /api/shop/donus    -> iyzico callback (token) -> retrieve DOGRULAMA -> siparis 'odendi'
 *                              + Telegram bildirimi + musteriyi siteye yonlendir (KDV dokumuyla)
 *   POST /api/shop/fiyat    -> PROVA (yan etkisiz fiyat sorgusu): AYNI sunucu hesabini kosar,
 *                              tutari doner. D1'e YAZMAZ, iyzico'ya GITMEZ, Telegram/e-posta
 *                              GONDERMEZ, siparis OLUSTURMAZ. Fiyat regresyonu canlida
 *                              gercek siparis acmadan olculebilsin diye var.
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
import { cfBaslat, cfDetay, hataKodu, hataMetni, kesinBasarisizMi } from "./iyzico.js";
import { parametrikHesapla } from "./parametrik.js";
import { SEMALAR } from "./semalar.js";
import { konfigurHesapla, d1Coz } from "./konfigur.js";
import { KONFIGURLAR } from "./konfigurlar.js";
import { konfigurBeklenirMi } from "./konfigur-beklenen.js";
import { golgeKalem, golgeLogSatiri } from "./konfigur-golge.js";
import { yonet, gecmiseEkle } from "./yonet.js";
// Siparis numarasi ureteci TEK KAYNAK (yonet.js /wa-siparis de bunu kullanir; dairesel
// import olmasin diye ortak modulde).
import { yeniSiparisNo } from "./siparis-no.js";
import { epostaAkisi, onayEpostasiHtml } from "./eposta.js";
import { olcumGonder, olcumLog } from "./olcum.js";
import { biletUret, biletDogrula } from "./olcum-bilet.js";
import { refKaydet, REF_KALIBI } from "./ref.js";

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
/** Siparis satirinin MALZEME/RENK BEYANI (fis metni). Karar YUKARIDA verilir (sepetiFiyatla:
 *  fiziksel urunde alanlar BOS yazilir); burasi yalnizca BICIMLEYICI — bos alan "beyan yok"
 *  demektir ve "" doner, cagiran yuzey o zaman ibareyi HIC basmaz. Kural burada TEKRARLANMAZ
 *  (`tur` kontrolu yok): tek karar noktasi satirin kuruldugu yerdir. */
function kalemSecimi(s, ayrac) {
  const m = (s && s.malzeme) || "";
  const r = (s && (s.renk_ozel || s.renk)) || "";
  if (!m && !r) { return ""; }
  return (m && r) ? (m + (ayrac || " / ") + r) : (m || r);
}

/** D1 `siparisler.filament` / `.renk` kolon degeri: satirlardaki BENZERSIZ beyanlar, "+" ile.
 *  BOS beyan ELENIR (fiziksel kalem malzeme/renk YAZMAZ): karma sepette "PLA+" gibi ucu acik
 *  bir dize, tamami fiziksel siparişte ise anlamsiz bir ayrac olusurdu. Tamami fiziksel
 *  siparişte deger BOS DIZEDIR — "bilinmiyor" degil, "beyan yok". */
function kolonBirlestir(satirlar, sec) {
  return [...new Set((satirlar || []).map(sec).filter(Boolean))].join("+");
}

function kurusMetin(kurus) {
  return Math.floor(kurus / 100) + "." + String(kurus % 100).padStart(2, "0");
}

function kurusTL(kurus) {
  return kurusMetin(kurus).replace(".", ",") + " TL";
}

// Siparis numarasi ureteci (siparisNoUret / yeniSiparisNo) 1 Agu 2026'da ./siparis-no.js'e
// TASINDI — govde birebir ayni, davranis DEGISMEDI. Gerekce: WhatsApp kanali (yonet.js
// /wa-siparis) AYNI numara ailesini uretmek zorunda ve index.js <-> yonet.js dogrudan
// import'u DAIRESEL olurdu. Ikinci kopya YOK (iki uretec zamanla ayrisirdi).

function yonlendir(env, sonuc, siparisNo, dokum) {
  // dokum (kalem 8, yalniz 'ok' donusunde): t=tahsilat kurus, kdv=kdv kurus — musteri donus
  // sayfasi KDV dokumunu bunlardan basar. Gosterim amaclidir; tahsilat coktan yapilmistir.
  // `b` (olcum bileti, yalniz 'ok' + GERCEK gecis): tarayici Purchase'inin TEK kanitidir.
  // Tek kullanimliktir ve /olcum-donus'ta yakilir (shop/src/olcum-bilet.js). Bilet YOKSA
  // tarayici olayi ATMAZ — URL'nin kendisi kanit DEGILDIR (uydurulabilir/tekrarlanabilir).
  const hedef = env.SITE_URL + "/?siparis=" + sonuc +
    (siparisNo ? "&no=" + encodeURIComponent(siparisNo) : "") +
    (dokum ? "&t=" + dokum.tahsilatKurus + "&kdv=" + dokum.kdvKurus : "") +
    (dokum && dokum.bilet ? "&b=" + encodeURIComponent(dokum.bilet) : "");
  return new Response(null, { status: 303, headers: { "Location": hedef } });
}

// ---------------------------------------------------------------- dogrulama

function metin(v, enAz, enCok) {
  const s = typeof v === "string" ? v.trim() : "";
  return s.length >= enAz && s.length <= enCok ? s : null;
}

/** REKLAM ATIF KIMLIKLERI (reklam-roi-sistemi.md Faz 0): tarayicidan gelen GA _ga client_id +
 *  Meta _fbp/_fbc + utm_source/medium/campaign/id + landing REF. Odeme ONCESI order kaydina
 *  yazilir (redirect'te UTM/cerez duser); purchase event (donus'ta) bunlarla atif yapar.
 *  Yalniz beyaz-liste alanlar, string'e zorlanip kirpilir; PII (email/telefon) BURADAN GECMEZ.
 *  Bos ise {} doner.
 *
 *  🔗 REF HALKASI (30 Tem): landing modulu (attribution-ref.js) her oturumda REF uretir ve
 *  wa.me lead beacon'i ile REF -> click-id eslemesini D1 `reklam_ref_gclid` tablosuna yazar
 *  (shop/src/ref.js). O tabloda REF -> gclid/gbraid/wbraid VARDI ama SIPARIS -> REF baglantisi
 *  YOKTU: `ref` beyaz-listede olmadigi icin SESSIZCE dusuyordu. Sonuc: hangi siparisin hangi
 *  tiklamadan/organik oturumdan geldigi JOIN'lenemiyordu (paid tarafta offline conversion
 *  import IMKANSIZ, organik tarafta ROI olculemez). `ref` artik kaydediliyor -> halka kapali:
 *      siparisler.atif.ref  ==  reklam_ref_gclid.ref  ->  click-id / grup / src
 *
 *  KIRMIZI CIZGILER:
 *   - KIRPILMAZ. Digerleri slice ile kirpilir (uzun cerez degeri kirpik de olsa isini gorur);
 *     KIRPIK BIR REF ise BASKA BIR REF'e benzeyen, hicbir kayda eslesmeyen COPTUR ve yanlis
 *     atif uretme riski tasir. Kalibina TAM uymayan deger ATILIR (fail-closed).
 *   - Kalip ref.js'ten (REF_KALIBI) gelir; landing + beacon + siparis TEK kaynaktan dogrular.
 *   - REF PII DEGILDIR (src + grup + rastgele 4 karakter; click-id tasimaz) ve olcum.js'in
 *     Meta/GA4 govdelerine GIRMEZ (o govdeler kendi beyaz-listelerini kullanir) — bizim ic
 *     atif anahtarimizdir. Negatif test: shop/test/olcum.mjs set 28. */
function atifTemizle(govde) {
  const a = (govde && govde.atif && typeof govde.atif === "object" && !Array.isArray(govde.atif))
    ? govde.atif : {};
  const al = (v, n) => (typeof v === "string" ? v.trim().slice(0, n) : "");
  const alanlar = {
    ga_client_id: al(a.ga_client_id, 64),
    fbp: al(a.fbp, 128),
    fbc: al(a.fbc, 256),
    utm_source: al(a.utm_source, 120),
    utm_medium: al(a.utm_medium, 120),
    utm_campaign: al(a.utm_campaign, 200),
    utm_id: al(a.utm_id, 120),
    // TAM eslesme; kirpma YOK (yukaridaki kirmizi cizgi).
    ref: REF_KALIBI.test(al(a.ref, 64)) ? al(a.ref, 64) : "",
  };
  const dolu = {};
  for (const k in alanlar) { if (alanlar[k]) { dolu[k] = alanlar[k]; } }
  return dolu;
}

/** Istek govdesini dogrula; hata varsa {hata}, yoksa {musteri, kalemler, odeme}. Istemciden
 *  gelen tutar/fiyat/kargo alanlari BILEREK okunmaz. */
function istekCoz(govde) {
  if (!govde || typeof govde !== "object") return { hata: "gecersiz-istek" };

  // SOZLESME ONAYI (kalem 9, yasal): istemci kutusunun isaretli olmasi YETMEZ — sunucu
  // /baslat'ta onay alanini sart kosar. true disindaki her deger red (istemci kodu
  // bozulursa sessizce onayli sayilmasin); onay ani D1'e damgalanir (ispat kaydi).
  if (govde.sozlesme_onay !== true) return { hata: "sozlesme-onay-yok" };

  // Odeme yontemi: 'kart' (varsayilan, iyzico) | 'havale'. Bilinmeyen deger sessizce karta
  // dusurulmez — istemci kodu bozulduysa yanlis kanaldan tahsilat yapilmasin.
  const odeme = govde.odeme == null ? "kart" : govde.odeme;
  if (odeme !== "kart" && odeme !== "havale") return { hata: "gecersiz-odeme" };

  const m = govde.musteri || {};
  const ad = metin(m.ad, 3, 120);
  const tel = (typeof m.tel === "string" ? m.tel : "").replace(/[^0-9]/g, "");
  const eposta = metin(m.eposta, 6, 200);
  const adres = metin(m.adres, 10, 500);
  const sehir = metin(m.sehir, 2, 60);
  const tckn = (typeof m.tckn === "string" ? m.tckn : "").replace(/[^0-9]/g, "");
  // MUSTERI NOTU: istege bagli serbest metin. 500 karakteri asan istek REDDEDILIR
  // (sessizce kirpmak, musteriye "gitti" yalani soyler). Kontrol karakterleri atilir,
  // satir sonu KORUNUR. Bos ise '' yazilir; siparis ASLA bu yuzden dusmez.
  const musteri_notu_ham = typeof govde.musteri_notu === "string" ? govde.musteri_notu : "";
  if (musteri_notu_ham.length > 500) return { hata: "not-uzun" };
  const musteri_notu = musteri_notu_ham.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "").trim();
  if (!ad) return { hata: "musteri-ad" };
  if (tel.length < 10 || tel.length > 13) return { hata: "musteri-tel" };
  if (!eposta || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(eposta)) return { hata: "musteri-eposta" };
  if (!adres) return { hata: "musteri-adres" };
  if (!sehir) return { hata: "musteri-sehir" };
  if (tckn && tckn.length !== 11) return { hata: "musteri-tckn" };

  const kc = kalemleriCoz(govde.sepet);
  if (kc.hata) return kc;
  return { musteri: { ad, tel, eposta, adres, sehir, tckn }, kalemler: kc.kalemler, odeme,
           atif: atifTemizle(govde), musteri_notu };
}

/** SEPET KALEMLERI — dogrulama TEK KAYNAK: /baslat (istekCoz) ve /fiyat (prova) AYNI
 *  fonksiyonu cagirir. Boylece prova yolu ASLA daha gevsek dogrulama yapamaz (bir kalem
 *  odeme yolunda reddediliyorsa provada da reddedilir; tersi de gecerli).
 *  Istemciden gelen tutar/fiyat/hacim alanlari BILEREK okunmaz. */
function kalemleriCoz(sepet) {
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
    const boy_etiket = k.boy_etiket == null || k.boy_etiket === "" ? null
      : (typeof k.boy_etiket === "string" && k.boy_etiket.length <= 60 ? k.boy_etiket : false);
    if (boy_etiket === false) return { hata: "gecersiz-boy", id: id };
    const renk_ozel = renk === "Diğer" ? metin(k.renk_ozel, 1, 60) : "";
    if (renk === "Diğer" && !renk_ozel) return { hata: "renk-ozel-bos", id: id };
    // Parametreler ISTEMCIDEN alinir ama fiyat/hacim ONDAN OKUNMAZ — sunucu yeniden hesaplar
    // (parametrik.js). Istemcinin yolladigi hacim_mm3/parametrik_fiyat_kurus BILEREK atilir.
    const parametreler = (k.parametreler && typeof k.parametreler === "object" &&
                          !Array.isArray(k.parametreler)) ? k.parametreler : null;
    // yazi_renk (cerceve 2-renk yazi): OPSIYONEL 2. renk — standart palette'ten dogrulanir,
    // gecersiz/yoksa null (tek renk). parametrik.js bunu okuyup +75 TL 2-renk ek ucretini
    // uygular; burada whitelist edilmezse client'in gonderdigi alan DUSER ve sunucu 2-renk'i
    // GORMEZ -> front 675 gosterip sunucu 600 tahsil ederdi (sessiz eksik tahsilat).
    const yazi_renk = SECENEK.RENK_SECENEKLERI.includes(k.yazi_renk) ? k.yazi_renk : null;
    kalemler.push({ id, malzeme, renk, renk_ozel: renk_ozel || "", boy_etiket, adet,
                    parametreler, yazi_renk });
  }
  return { kalemler };
}

// ---------------------------------------------------------------- fiyat (tek kaynak)

/**
 * SEPET FIYATI — SUNUCU hesabi. /baslat (tahsilat) ve /fiyat (prova) BU fonksiyonu cagirir;
 * ikinci bir hesap kopyasi YOKTUR -> prova ile tahsilat AYRISAMAZ (fiyat regresyonu provada
 * gorunur). Kollarin sirasi ve fail-closed davranisi DEGISMEDI:
 *   1) kalem KONFIGURATORLU (D1 kolonu dolu | bundle taniyor | konfigur-beklenen.js) ->
 *      konfigur (olcuye ozel dekor) sunucu hesabi, sema D1 `konfigur` KOLONUNDAN (FAZ 4)
 *   2) konfiguratorlu ama D1 kaydi YOK/BOZUK -> FAIL-CLOSED 400 (bundle'a ya da sabit
 *      katalog fiyatina DUSULMEZ; sessiz varsayilan = yanlis tahsilat)
 *   3) urun parametrik                -> parametrik (sari) sunucu hesabi
 *   4) aksi                           -> sabit katalog fiyati (secenekler.js satirOzeti)
 * @returns {{hata: object, kod: number}} veya {{satirlar, toplamKurus}}
 */
async function sepetiFiyatla(env, kalemler) {
  // FIYAT SUNUCUDA: sepetteki id'lerin guncel kaydi D1 katalogundan (SALT OKUMA).
  const idler = [...new Set(kalemler.map((k) => k.id))];
  const yertut = idler.map(() => "?").join(",");
  const ALANLAR = "id, baslik, kategori, fiyat, parametrik, gorsel";
  // OPSIYONEL KOLONLAR — ZORUNLU ALANLARDAN AYRI (asagidaki merdiven): D1 semasi bunlardan
  // birini tasimiyorsa SELECT "no such column" ile PATLAR. `tur` (hazir ticari mal isareti,
  // 31 Tem) `konfigur`a BAGLANMAZ: tek listede olsalardi `tur`u olmayan bir sema (ornegin
  // geri alinmis bir ALTER) konfigur kalemlerini de fail-closed 400'e dusururdu.
  const EK_KOLONLAR = ["konfigur", "tur", "boy_secenekleri"];
  // `konfigur` (D1'deki sema) AYNI SELECT'e kolon olarak eklendi — EK SORGU ve EK ROUND-TRIP
  // YOK, satirla birlikte gelir (maliyet O(sepet kalemi), katalog buyuklugunden BAGIMSIZ).
  // FAZ 4'ten beri bu kolon PARA YOLUDUR: konfigur kaleminin fiyati BUNDAN hesaplanir.
  //
  // 🔴 KOLONSUZ YEDEK YOL (kolon canli D1'de ancak `python3 tools/d1-sync.py --sema` ile
  // olusur; kolonlu SELECT o ALTER'dan once "no such column" ile PATLAR ve TUM odeme yolunu
  // dusururdu). Yedek yolda `u.konfigur` undefined kalir -> konfigur kalemleri FAIL-CLOSED
  // 400 alir (WhatsApp kanali), katalogun geri kalani SATILMAYA DEVAM EDER. Yani yedek yol
  // yalnizca konfigursuz urunler icin fail-open, konfigurlu urunler icin fail-CLOSED'dur.
  // KOLON MERDIVENI: once TUM opsiyonel kolonlarla dene, patlarsa sondan BIRER BIRER dus,
  // en sonda ciplak ALANLAR (bugunku yedek yol). Her basamak bir onceki kadar veri getirir
  // ARTI bir kolon; yani en fazla EK_KOLONLAR.length+1 deneme olur ve normal halde (canli
  // sema, 24 kolon) ILK deneme tutar -> EK SORGU YOK.
  let sonuc;
  for (let n = EK_KOLONLAR.length; ; n -= 1) {
    const ek = EK_KOLONLAR.slice(0, n);
    try {
      sonuc = await env.KATALOG.prepare(
        "SELECT " + ALANLAR + ek.map((c) => ", " + c).join("") +
        " FROM urunler WHERE id IN (" + yertut + ")"
      ).bind(...idler).all();
      break;
    } catch (e) {
      if (n === 0) { throw e; }
      console.log("SELECT dustu (ek kolonlar: " + ek.join(",") + "), daralan yola dusuldu: " +
                  (e && e.message || e));
    }
  }
  const katalog = new Map((sonuc.results || []).map((u) => [u.id, u]));

  // GOLGE KAYDI — para yolunun DISINDA. FAZ 4'ten beri YONU TERS: fiyat D1'den geldigi icin
  // bu kayit "bundle artefakti (konfigurlar.js) BAYAT mi?" sorusunu olcer. Hicbir dondugu
  // deger fiyata/tutara/siparise girmez; atarsa yutulur (olcum tahsilati ASLA dusuremez).
  const golgeYaz = (k, u, birimKurus) => {
    try {
      const g = golgeKalem(k, SECENEK, KONFIGURLAR.get(k.id) || null,
                           (u && u.konfigur) || "", birimKurus);
      const satir = golgeLogSatiri(k.id, g);
      if (satir) { console.log(satir); }
    } catch (e) { /* golge sessizdir: olcum hatasi parayi etkilemez */ }
  };

  const satirlar = [];
  let toplamKurus = 0;
  for (const k of kalemler) {
    const u = katalog.get(k.id);
    if (!u) return { hata: { hata: "bilinmeyen-urun", id: k.id }, kod: 400 };

    // 🔴 MALZEME x KATEGORI KAPISI (14 Agu, isletme karari) — FAIL-CLOSED, HER KOLDAN ONCE.
    // Bazi malzemeler (bugun ABS) yalniz belirli urun gruplarinda sunulur; tablo TEK
    // kaynakta (secenekler.js FILAMENT_KATEGORI_HARIC) durur ve site secim listesi de
    // ayni tabloyu uygular. UI'dan GIZLEMEK YETMEZ: bu depoda olculdu ki secici
    // kaldirilan bir yolda sunucu hesaplamaya devam edebiliyor
    // ([[ui-kaldirmak-odeme-yolunu-kapatmaz]]) — istemci dogrudan istek gonderirse kalem
    // BURADA reddedilir ve FIYAT HESABINA HIC GIRMEZ (konfigur/parametrik/sabit, uc kol da
    // bu satirin ALTINDA). Kategori D1'den gelir; bos/taninmayan ise cevap yine RED.
    if (!SECENEK.malzemeKategoriUygunMu(k.malzeme, u.kategori)) {
      return { hata: { hata: "malzeme-kategori", id: k.id, malzeme: k.malzeme,
                       mesaj: "Bu ürün grubunda seçilen malzeme sunulmuyor." }, kod: 400 };
    }

    let birimKurus, ekAlanlar = {};
    // 🔴 KONFIGUR FIYAT KAYNAGI = D1 (FAZ 4, 31 Tem). Eskiden fiyat Worker bundle'indaki
    // KONFIGURLAR haritasindan (shop/src/konfigurlar.js) hesaplanirdi; o harita ELLE uretilen
    // + ELLE deploy edilen bir artefakt oldugu icin "D1'de VAR, bundle'da YOK/BAYAT" penceresi
    // YAPISAL olarak acikti. Artik sema, katalogla AYNI otomatik yoldan (tools/d1-sync.py,
    // pre-push hook) gelen `urunler.konfigur` KOLONUNDAN okunur -> vitrinin gosterdigi fiyat
    // ile tahsil edilen fiyatin kaynagi TEKTIR. Cevirmenin sarti canlida olculdu: FAZ 3 golge
    // raporu 17/17 urunde `ayni`, fark_kurus_toplam = 0 (bkz. konfigur-golge.js).
    const d1Konfigur = d1Coz(u.konfigur);   // obje | null (bos/kolonsuz) | undefined (bozuk)
    let boySecenekleri = null;
    if (typeof u.boy_secenekleri === "string") {
      try {
        const aday = JSON.parse(u.boy_secenekleri);
        if (Array.isArray(aday) && aday.every((s) => s && typeof s === "object" &&
            typeof s.etiket === "string" && s.etiket !== "" &&
            Number.isInteger(s.fark_tl) && s.fark_tl >= 0)) boySecenekleri = aday;
      } catch (e) { /* asagidaki fail-closed hukum */ }
    }
    if (boySecenekleri === null) {
      if (k.boy_etiket) return { hata: { hata: "boy-desteklenmiyor", id: k.id }, kod: 400 };
      boySecenekleri = [];
    }
    if (boySecenekleri.length && !k.boy_etiket) {
      return { hata: { hata: "boy-secimi-zorunlu", id: k.id }, kod: 400 };
    }
    if (k.boy_etiket && !boySecenekleri.some((s) => s.etiket === k.boy_etiket)) {
      return { hata: { hata: "gecersiz-boy", id: k.id }, kod: 400 };
    }

    // "Bu kalem konfiguratorlu MU?" — UC BAGIMSIZ SINYAL, herhangi biri yeterli. Amac: hicbir
    // konfigur kalemi asagidaki SABIT FIYAT koluna DUSMESIN (dusseydi 30 cm'lik 1.500 TL'lik
    // urun 500 TL'ye satilirdi = sessiz eksik tahsilat). Sinyaller birbirini yedekler:
    //   (1) D1 kolonu dolu (normal hal), (2) bundle haritasi taniyor (D1 senkronu kacmis olsa
    //   bile), (3) konfigur-beklenen.js (gizli kategori / seri id soneki — ikisi de kacsa bile).
    const konfigurluMu = Boolean(d1Konfigur) || KONFIGURLAR.has(k.id) || konfigurBeklenirMi(u);
    if (konfigurluMu) {
      // Kanal SECENEK.KONFIGUR_ODEME_ACIK ile ACIK; kapaliyken kalem WhatsApp'a duser.
      if (!SECENEK.KONFIGUR_ODEME_ACIK) {
        return { hata: { hata: "konfigur-urun", id: k.id,
                         mesaj: "Ölçüye özel ürünler için WhatsApp'tan teklif alın." }, kod: 400 };
      }
      // FAIL-CLOSED: kalem konfiguratorlu ama D1 kaydi YOK ya da BOZUK. Bundle'a ya da sabit
      // katalog fiyatina DUSULMEZ — "sessiz varsayilan" tam olarak budur ve bedeli yanlis
      // tahsilattir. Kalem gorunur 400 ile WhatsApp kanalina duser (Okan kurali: siparis
      // kaybetmek yanlis tahsilattan iyidir). Kayit ATILIR ki pencere sayilabilsin.
      if (!d1Konfigur) {
        golgeYaz(k, u, undefined);
        return { hata: { hata: "konfigur-urun", id: k.id,
                         mesaj: "Ölçüye özel ürünler için WhatsApp'tan teklif alın." }, kod: 400 };
      }
      // Fiyat SUNUCUDA yeniden hesaplanir (konfigur.js: /konfigur.js cekirdegi; istemcinin
      // boy'u [min,max]+adim'a KIRPILIR, katsayi LISTEDEN okunur, istemcinin yolladigi
      // hacim/fiyat alanlari OKUNMAZ). Sema artik D1'den geldigi icin bozuk/eksik alanli bir
      // kayit da konfigurHesapla'nin kendi hata kollarina takilir -> yine 400, asla 0 TL.
      const kh = konfigurHesapla(k, SECENEK, d1Konfigur);
      if (kh.hata) { return { hata: { hata: kh.hata, id: k.id }, kod: 400 }; }
      birimKurus = kh.birimKurus;
      ekAlanlar = { parametreler: kh.parametreler, parametre_detay: kh.detay,
                    hacim_mm3: kh.hacimMm3 };
    } else if (u.parametrik) {
      // Olcuye ozel (sari seri). Kanal SECENEK.PARAMETRIK_ODEME_ACIK ile ACIK (17 Tem);
      // fiyat SUNUCUDA yeniden hesaplanir (parametrik.js: sema + hacim.js + taban fiyat;
      // istemcinin hacim/fiyat alanlari OKUNMAZ). Anahtar kapatilirsa asagidaki kol
      // kalemi WhatsApp'a yonlendirir (kabul testi 5).
      if (!SECENEK.PARAMETRIK_ODEME_ACIK) {
        return { hata: { hata: "parametrik-urun", id: k.id,
                         mesaj: "Ölçüye özel ürünler için WhatsApp'tan teklif alın." }, kod: 400 };
      }
      const sema = SEMALAR.get(k.id);
      if (!sema) {
        // Semasiz parametrik urun (konfiguratoru yok) -> her zaman WhatsApp kanali.
        return { hata: { hata: "parametrik-urun", id: k.id,
                         mesaj: "Ölçüye özel ürünler için WhatsApp'tan teklif alın." }, kod: 400 };
      }
      const ph = parametrikHesapla(k, SECENEK, sema);
      if (ph.hata) { return { hata: { hata: ph.hata, id: k.id, alan: ph.alan }, kod: 400 }; }
      birimKurus = ph.birimKurus;
      ekAlanlar = { parametreler: ph.parametreler, parametre_detay: ph.detay,
                    hacim_mm3: ph.hacimMm3 };
    } else {
      // HESAP TEK KAYNAK: front'un gosterdigi fiyati ureten fonksiyonun AYNISI (secenekler.js).
      // Boy etiketi D1'deki kanonik listeye karsi yukarida dogrulandi; fiyat cekirdegi
      // istemci ve sunucuda AYNI secenekler.js boyFarki fonksiyonunu kullanir.
      // 🔴 `tur` D1'DEN GECER (para yolu): tam "fiziksel" ise hazir ticari mal demektir ve
      // satirOzeti/hesaplaFiyatKurus malzeme+renk carpanini 1,00'e sabitler -> tutar = LISTE
      // fiyati. Kural burada TEKRARLANMAZ, secenekler.js'te TEK yerdedir (front ile ayni
      // fonksiyon). Kolon okunamazsa (yukaridaki merdivenin daralan basamagi) u.tur undefined
      // kalir -> BUGUNKU davranis, yani `tur`suz 15.930 baski urununde regresyon 0.
      const ozet = SECENEK.satirOzeti(
        { kategori: u.kategori, fiyat: u.fiyat, parametrik: false,
          boy_secenekleri: boySecenekleri,
          tur: u.tur },
        { id: k.id, malzeme: k.malzeme, renk: k.renk, renk_ozel: k.renk_ozel,
          boy_etiket: k.boy_etiket, adet: 1 });
      if (!ozet.odenebilir || !(ozet.birimKurus > 0)) {
        return { hata: { hata: "fiyatsiz-urun", id: k.id }, kod: 400 };
      }
      birimKurus = ozet.birimKurus;
    }

    // ARTEFAKT DRIFT OLCUMU — fiyat YUKARIDA D1'den hesaplandi ve BURASI onu DEGISTIRMEZ.
    // Kaydedilen soru: "bundle artefakti D1 ile hala ayni mi?" (ayrisim = konfigurlar.js
    // bayat, deploy bekliyor). Konfigursuz urunlerde durum "yok" -> HIC log yazilmaz.
    golgeYaz(k, u, birimKurus);

    // Ara yuvarlama YOK: birim kurus x adet, kalem tutari kurusuyla toplanir.
    const tutar = birimKurus * k.adet;
    toplamKurus += tutar;
    // 🔴 BEYAN TEK KARAR NOKTASI (fis ekseni): fiziksel urunde (hazir ticari mal) malzeme/renk
    // SECIMI YOKTUR -> siparis satirina YAZILMAZ. Asagi akistaki HICBIR yuzey (e-posta,
    // Telegram, iyzico kalem adi, D1 filament/renk kolonlari, yonetim ekrani) bu karari
    // TEKRARLAMAZ; hepsi bos degeri "beyan yok" olarak bicimler. Aksi halde bir boya kutusu
    // "Malzeme: ASA / turuncu" diye KAYDEDILIR, liste fiyati tahsil edilirdi — fis tutarla
    // celisirdi. `tur` satirda POZITIF isaret olarak tasinir: kayit kendini "hazir ticari mal"
    // diye tanimlar, bos alanlar "veri kayip" gibi okunmaz.
    // FAIL-CLOSED: kosul TAM "fiziksel"; `tur` yok/taninmaz ise satir BUGUNKU gibi kurulur
    // (3D siparislerinde malzeme/renk AYNEN durur).
    const fizikselKalem = SECENEK.fizikselMi(u.tur);
    satirlar.push({
      id: k.id, baslik: u.baslik, kategori: u.kategori, gorsel: u.gorsel || "",
      malzeme: fizikselKalem ? "" : k.malzeme,
      renk: fizikselKalem ? "" : k.renk,
      renk_ozel: fizikselKalem ? "" : k.renk_ozel,
      ...(fizikselKalem ? { tur: SECENEK.TUR_FIZIKSEL } : {}),
      adet: k.adet,
      birim_kurus: birimKurus, tutar_kurus: tutar, ...ekAlanlar,
    });
  }
  return { satirlar, toplamKurus };
}

// ---------------------------------------------------------------- /baslat

async function baslat(request, env, url, ctx) {
  let govde;
  try {
    govde = await request.json();
  } catch (e) {
    return json({ hata: "gecersiz-json" }, 400, env);
  }
  const c = istekCoz(govde);
  if (c.hata) return json(c, 400, env);
  const { musteri, kalemler, odeme, atif, musteri_notu } = c;
  // Atif kimlikleri (GA client_id + Meta fbp/fbc + UTM) order kaydina yazilir; purchase event
  // (donus'ta, iyzico OK aninda) bunlari kullanir. Redirect'te URL param/cerez duser.
  const atifJson = JSON.stringify(atif || {});

  // FIYAT SUNUCUDA (TEK KAYNAK): hesap sepetiFiyatla()'da — /fiyat (prova) ucu AYNI
  // fonksiyonu cagirir, ikinci bir hesap kopyasi YOKTUR. Kollar + fail-closed davranisi
  // o fonksiyonda; buradan istemcinin gonderdigi hicbir tutar alani gecmez.
  const f = await sepetiFiyatla(env, kalemler);
  if (f.hata) return json(f.hata, f.kod, env);
  const { satirlar, toplamKurus } = f;
  if (!(toplamKurus > 0)) return json({ hata: "gecersiz-tutar" }, 400, env);

  // KARGO (Okan, 16 Tem — KESIN; tools/paket-shop-kargo.md): urun toplami < 2.500,00 TL ->
  // 250,00 TL; >= 2.500,00 TL (tam 2.500 dahil) -> bedava. Kural tek kaynagi secenekler.js
  // (sepet paneli ayni fonksiyonla gosterir); hesap BURADA — istemcinin yolladigi kargo/tutar
  // alanlari istekCoz'da zaten okunmuyor. Kargo urun fiyatina yedirilmez, ayri kalemdir.
  const kargoKurus = SECENEK.kargoKurus(toplamKurus);
  const tahsilatKurus = toplamKurus + kargoKurus;

  // KDV (kalem 8, Okan KESIN %20): tahsilat DEGISMEZ — dokum + D1 kaydi. Kargo dahil
  // genel toplam uzerinden TEK ayristirma; net+KDV=brut birebir (fark KDV'ye yedirilir).
  const kdv = SECENEK.kdvAyristir(tahsilatKurus);

  const siparisNo = await yeniSiparisNo(env);
  const acikAdres = musteri.adres + " / " + musteri.sehir;
  // Onay istekCoz'dan gecti (sozlesme_onay === true sart) — damga SUNUCU saati (ispat kaydi).
  const onayDamgasi = new Date().toISOString();

  if (odeme === "havale") {
    // HAVALE/EFT (kalem 6): iyzico'ya GIDILMEZ; siparis 'havale-bekliyor' dusulur, musteriye
    // IBAN + unvan + odenecek TAM tutar + siparis no gosterilir. IBAN/unvan TEK kaynaktan
    // (wrangler secret; koda/HTML'e yazilmaz). Tanimli degilse secenek musteriye kapali:
    // acik 503 doner, sessizce bos IBAN gosterilmez.
    if (!env.HAVALE_IBAN || !env.HAVALE_UNVAN) {
      return json({ hata: "havale-hazir-degil" }, 503, env);
    }
    // token NULL: /donus havale satirini HICBIR token'la bulamaz -> durum istemciden
    // degistirilemez. Onay tek yoldan: shop/KURULUM.md'deki wrangler d1 komutu.
    await env.KATALOG.prepare(
      "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, kargo_kurus," +
      " kdv_kurus, odeme_yontemi, sozlesme_onay, urunler, filament, renk," +
      " musteri_ad, musteri_tel, musteri_eposta, musteri_adres, musteri_notu, atif)" +
      " VALUES (?, NULL, ?, 'havale-bekliyor', ?, ?, ?, 'havale', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(
      siparisNo, new Date().toISOString(), toplamKurus, kargoKurus, kdv.kdvKurus,
      onayDamgasi, JSON.stringify(satirlar),
      kolonBirlestir(satirlar, (s) => s.malzeme),
      kolonBirlestir(satirlar, (s) => s.renk_ozel || s.renk),
      musteri.ad, musteri.tel, musteri.eposta, acikAdres, musteri_notu, atifJson
    ).run();
    ctx.waitUntil(telegram(env, havaleMesaji(siparisNo, satirlar, toplamKurus, kargoKurus,
      tahsilatKurus, musteri, acikAdres, musteri_notu)));
    // Musteriye onay e-postasi (tetik 1, havale basladi) + satici kopyasi.
    onayEpostalari(env, ctx,
      { siparis_no: siparisNo, musteri_ad: musteri.ad, musteri_adres: acikAdres,
        musteri_eposta: musteri.eposta, musteri_notu: musteri_notu },
      satirlar,
      { tutarKurus: toplamKurus, kargoKurus: kargoKurus, kdvKurus: kdv.kdvKurus,
        tahsilatKurus: tahsilatKurus }, true);
    // Ekrandaki TAM tutar = D1 tahsilati (tutar_kurus + kargo_kurus) BIREBIR (kabul testi 13);
    // net/kdv alanlari musteri ekranindaki KDV dokumu icin (kalem 8).
    return json({ havale: true, no: siparisNo, iban: env.HAVALE_IBAN,
                  unvan: env.HAVALE_UNVAN, tutar_kurus: tahsilatKurus,
                  tutar: kurusTL(tahsilatKurus), kargo_kurus: kargoKurus,
                  net_kurus: kdv.netKurus, kdv_kurus: kdv.kdvKurus,
                  kdv_yuzde: SECENEK.KDV_YUZDE }, 200, env);
  }

  const adParcalari = musteri.ad.split(/\s+/);
  const soyad = adParcalari.length > 1 ? adParcalari.pop() : adParcalari[0];
  const isim = adParcalari.join(" ") || soyad;
  // tel normalize (yalniz rakam): "0532..." -> +90532..., "90532..." -> +90532..., "532..." -> +90532...
  const gsm = musteri.tel.startsWith("90") && musteri.tel.length === 12 ? "+" + musteri.tel
    : musteri.tel.startsWith("0") ? "+9" + musteri.tel
    : "+90" + musteri.tel;
  const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";

  // Ayni id birden cok satirda (farkli malzeme/renk/olcu) yer alabilir -> iyzico'ya giden
  // basketItems id'si BENZERSIZ olmali (tekrar edene #1,#2 sira eki; tekil id degismez).
  // NOT: /donus callback'i basketItems id'siyle ESLESME YAPMAZ — kimlik denetimi yalniz
  // basketId/conversationId (= siparisNo) uzerinden; bu yuzden son ek eklemek guvenli.
  const idAdedi = {};
  for (const s of satirlar) { idAdedi[s.id] = (idAdedi[s.id] || 0) + 1; }
  const idSira = {};
  const urunKalemleri = satirlar.map((s) => {
    let bid = s.id;
    if (idAdedi[s.id] > 1) { idSira[s.id] = (idSira[s.id] || 0) + 1; bid = s.id + "#" + idSira[s.id]; }
    // Parametrik (sari) satirda olcu ozeti ada eklenir (ilk ~60 karakter — iyzico ad alani
    // sinirina karsi kisaltilir): ayni urunun farkli olculu iki satiri iyzico ekraninda
    // ve dekontunda ayirt edilsin.
    const detay = s.parametre_detay ? " — " + String(s.parametre_detay).slice(0, 60) : "";
    // Parantez ici = BEYAN. Fiziksel kalemde malzeme/renk beyani YOKTUR (kalemSecimi "" doner)
    // -> parantez yalniz adet icin acilir, hic icerik kalmazsa HIC acilmaz. Karti okuyan
    // musteri dekontunda "Tekne boyasi (ASA, turuncu)" GORMEZ.
    const secim = kalemSecimi(s, ", ");
    const adetMetni = s.adet > 1 ? s.adet + " adet" : "";
    const parantez = [secim, adetMetni].filter(Boolean).join(", ");
    return {
      id: bid,
      name: (s.baslik + (parantez ? " (" + parantez + ")" : "") + detay).slice(0, 120),
      category1: s.kategori || "Genel",
      itemType: "PHYSICAL",
      // iyzico: basketItems price toplami = price. Kurus toplaminda birebir tutar.
      price: kurusMetin(s.tutar_kurus),
    };
  });

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
    basketItems: urunKalemleri.concat(kargoKurus > 0 ? [{
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
    " kdv_kurus, odeme_yontemi, sozlesme_onay, urunler, filament, renk," +
    " musteri_ad, musteri_tel, musteri_eposta, musteri_adres, musteri_notu, atif)" +
    " VALUES (?, ?, ?, 'bekliyor', ?, ?, ?, 'kart', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
  ).bind(
    siparisNo, init.token, new Date().toISOString(), toplamKurus, kargoKurus,
    kdv.kdvKurus, onayDamgasi,
    JSON.stringify(satirlar),
    kolonBirlestir(satirlar, (s) => s.malzeme),
    // "Diğer" renkte musterinin yazdigi renk kaydedilir (uretim bunu okur), yoksa liste rengi
    kolonBirlestir(satirlar, (s) => s.renk_ozel || s.renk),
    musteri.ad, musteri.tel, musteri.eposta, acikAdres, musteri_notu, atifJson
  ).run();

  return json({ url: init.paymentPageUrl, no: siparisNo }, 200, env);
}

// ---------------------------------------------------------------- /fiyat (PROVA)

/**
 * PROVA HIZ SINIRI — EN IYI CABA maliyet freni (native Cloudflare rate limiting binding).
 *
 * 🔴 NE OLDUGU / NE OLMADIGI — 29 Tem canli olcum (worker version 60f56ffb-…; curl ile canli
 * uca, ayni cikis IP'si). BU UC BIR GUVENLIK SINIRI DEGILDIR:
 *   - wrangler.toml'daki `limit` degeri GARANTILI ust sinir DEGIL. Native ratelimit sayaci IP
 *     basina TEK sayac tutmuyor; baglanti uc-noktasi / kolo basina BOLUNUYOR.
 *   - Olculen: kalici TEK baglantida 61 istek 200 + ilk 429 = 62. istek (limiter yapilandirilan
 *     degerden BIR FAZLASINI gecirir). Her istekte YENI baglanti acan istemcide ise 300 istek /
 *     11,2 sn kosuldu ve ilk 429 ancak 265. istekte geldi -> 60 yapilandirmasinda EFEKTIF tavan
 *     ~4,4 x 60. Carpani istemcinin baglanti davranisi belirler; bizim kontrolumuzde DEGIL.
 *   - Dort alternatif aciklama (pencere kaymasi, deploy yansimamasi, binding yok/bozuk, cikis
 *     IP degisimi) ayni turda olcumle elendi -> bolunme gercek, olcum artefakti degil.
 * AMAC: tek bir istemcinin uretebilecegi MALIYETI (D1 SELECT + hesap) buyuklukce sinirlamak.
 * Bir yetkilendirme/abuse sinirina, kota garantisine ya da "IP basina en fazla N" iddiasina
 * DAYANAK YAPILAMAZ. Boyle bir garanti gerekiyorsa mekanizma degismelidir (or. imzali jeton).
 *
 * NEDEN YINE DE VAR: onceki hal isolate-ici bir Map sayacti (30 istek/dk) ve HICBIR fren
 * uygulamiyordu — her istekte yeni baglanti acan istemciye 40/40 HTTP 200 dondu (her isolate'in
 * Map'i BOS basliyordu). Native binding en azindan kolo basina sayiyor: sinirsizdan ~4-5x
 * limite gecis olculdu. EK D1 YAZMASI YAPMAZ (prova ucunun "yan etki yok" kirmizi cizgisi
 * korunur; kalici sayac icin D1/KV YAZMASI gerekirdi ve o cizgiyi delerdi).
 *
 * 🔒 AYRI KOTA: binding /ref ile PAYLASILMAZ (ayri ad FIYAT_RATE_LIMIT + ayri namespace_id).
 * Paylasilsaydi beacon trafigi fiyat sorgusunu, fiyat trafigi de beacon'i kapatabilirdi.
 *
 * LIMIT SECIMI (wrangler.toml simple.limit = 60 / period = 60 sn) ve NEDEN DUSURULMEDI:
 * mesru kullanimin en yogun makul hali konfiguratorde ayar deneyen tek musteridir — olculdu
 * (kabul testi set 9.5): en yogun yanlis-pozitif senaryosu 40 istek/dk, NAT arkasindaki 2
 * musteri 50 istek/dk; 60 bunlarin USTUNDE kalir. Bolunme YUKARI yonludur (efektif tavan
 * yapilandirilandan BUYUK), dolayisiyla degeri kismak kacagi kismaz ama KALICI BAGLANTI
 * kullanan gercek musteriyi dogrudan vurur -> yanlis-pozitif = satis kaybi. Mimar karari
 * (29 Tem): deger 60'ta KALIR.
 *
 * 🔴 FAIL-CLOSED (bilincli secim; /ref FAIL-OPEN'dan AYRILIR): binding yoksa, bozuksa ya da
 * limiter patlarsa uc 429 doner — sessizce SINIRSIZA DONMEZ. Gerekce: /ref bir attribution
 * beacon'idir, kaybi olculemeyen veri kaybidir -> orada fail-open dogru; /fiyat ise YAN
 * ETKISIZ bir dogrulama/konfigurator ucudur, kaybi GORULUR ve GERI DONULEBILIR. Yanlis
 * konfigurasyonun bedeli "ucun gurultuyle olmesi" olmalidir, "tavanin sessizce kalkmasi"
 * degil. Yanlislikla silinmeyi CI yakalar: shop/test/fiyat-prova.mjs set 9.1 wrangler.toml'da
 * binding beyanini BLOKLAYICI olarak arar (mutant M6).
 */
const PROVA_PENCERE_SN = 60;   // wrangler.toml FIYAT_RATE_LIMIT simple.period ile AYNI olmali
                               // (drift kapisi: fiyat-prova.mjs set 9.1)

/** 429 cevabi — TEK yer. Govde/basliklar sabit; D1'e, aga ya da katalog verisine DOKUNMAZ. */
function cokIstek(env) {
  return new Response(JSON.stringify({ hata: "cok-istek" }), {
    status: 429,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Retry-After": String(PROVA_PENCERE_SN),
      ...cors(env),
    },
  });
}

/** true -> cap asildi (ya da tavan UYGULANAMIYOR) -> cagiran 429 doner ve govdeyi bile
 *  ayristirmaz. Native binding EK D1 YAZMASI YAPMAZ. Fail-closed: binding yok/bozuk/patladi
 *  hallerinin HEPSI true (yuksek sesli log ile). */
async function provaHizSiniriAsildi(request, env) {
  const rl = env && env.FIYAT_RATE_LIMIT;
  if (!rl || typeof rl.limit !== "function") {
    console.error("FIYAT_RATE_LIMIT binding YOK/BOZUK -> /fiyat fail-closed 429 " +
                  "(wrangler.toml [[unsafe.bindings]] beyanini kontrol et)");
    return true;
  }
  const ip = (request.headers && typeof request.headers.get === "function"
    ? request.headers.get("CF-Connecting-IP") : "") || "yok";
  try {
    const sonuc = await rl.limit({ key: ip });
    return !(sonuc && sonuc.success);           // success !== true -> cap asildi
  } catch (e) {
    console.error("fiyat rate-limit hatasi (fail-closed):", (e && e.stack) || e);
    return true;                                // limiter patladi -> tavan yok sayilmaz
  }
}

/**
 * POST /api/shop/fiyat — YAN ETKISIZ fiyat sorgusu (prova).
 *
 * NEDEN VAR: canli tahsilat tutari bugune dek ancak GERCEK siparis acilarak olculebiliyordu
 * (D1 satiri + Telegram + e-posta). Fiyat regresyonu bu yuzden canlida dogrulanamiyordu.
 * Bu uc, /baslat ile AYNI dogrulama (kalemleriCoz) ve AYNI hesap (sepetiFiyatla) cekirdegini
 * kosar, yalnizca TUTARI doner.
 *
 * 🔴 KIRMIZI CIZGI — YAN ETKI YOK: D1'e YAZMAZ (yalniz sepetiFiyatla'nin SELECT'i), siparis
 * numarasi URETMEZ, iyzico'ya GITMEZ, Telegram/e-posta GONDERMEZ, olcum olayi (Purchase)
 * GONDERMEZ. Yapisal kanit: shop/test/fiyat-prova.mjs D1 run() ve global fetch cagrilarini
 * SAYAR; prova cagrisinda ikisi de 0 olmali.
 *
 * 🔒 SIZINTI YUZEYI: cevap BEYAZ LISTE ile kurulur (yeni bir ic alan eklense bile kendiliginden
 * SIZMAZ): id + adet + kurus tutarlari + musteriye zaten gosterilen parametre_detay. Katalog
 * ic alanlari (baslik/kategori/gorsel), uretim verisi (hacim_mm3), IBAN/unvan, siparis no,
 * tedarikci/lisans bilgisi ve secret DONMEZ. Musteri (PII) alani HIC OKUNMAZ.
 */
async function fiyatProva(request, env) {
  // TAVAN EN ONDE: cap asilinca govde ayristirilmaz, D1'e HIC gidilmez, hicbir hesap kosmaz.
  if (await provaHizSiniriAsildi(request, env)) { return cokIstek(env); }

  let govde;
  try {
    govde = await request.json();
  } catch (e) {
    return json({ hata: "gecersiz-json" }, 400, env);
  }
  if (!govde || typeof govde !== "object") return json({ hata: "gecersiz-istek" }, 400, env);

  // Dogrulama TEK KAYNAK: /baslat ile AYNI fonksiyon (gevsek prova yolu YOK). Musteri /
  // sozlesme_onay / odeme alanlari burada BILEREK istenmez ve OKUNMAZ (siparis olusmuyor).
  const kc = kalemleriCoz(govde.sepet);
  if (kc.hata) return json(kc, 400, env);

  // Hesap TEK KAYNAK: tahsilatta kosan fonksiyonun AYNISI. Konfigur/parametrik fail-closed
  // kollari da burada -> bundle'da olmayan konfigur urunu provada da 400 alir (provanin
  // "odenebilir" demesi ile /baslat'in tahsil etmesi AYRISAMAZ).
  const f = await sepetiFiyatla(env, kc.kalemler);
  if (f.hata) return json(f.hata, f.kod, env);
  const { satirlar, toplamKurus } = f;
  if (!(toplamKurus > 0)) return json({ hata: "gecersiz-tutar" }, 400, env);

  const kargoKurus = SECENEK.kargoKurus(toplamKurus);
  const tahsilatKurus = toplamKurus + kargoKurus;
  const kdv = SECENEK.kdvAyristir(tahsilatKurus);

  return json({
    prova: true,
    // BEYAZ LISTE (bkz. yukarida): sepetiFiyatla satirindaki baslik/kategori/gorsel/hacim_mm3
    // gibi alanlar BILEREK disarida.
    satirlar: satirlar.map((s) => {
      const c = { id: s.id, adet: s.adet, birim_kurus: s.birim_kurus,
                  tutar_kurus: s.tutar_kurus };
      if (s.parametre_detay) { c.parametre_detay = s.parametre_detay; }
      return c;
    }),
    urun_kurus: toplamKurus,
    kargo_kurus: kargoKurus,
    tahsilat_kurus: tahsilatKurus,
    tutar: kurusTL(tahsilatKurus),
    net_kurus: kdv.netKurus,
    kdv_kurus: kdv.kdvKurus,
    kdv_yuzde: SECENEK.KDV_YUZDE,
  }, 200, env);
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
    "SELECT siparis_no, durum, durum_gecmisi, tutar_kurus, kargo_kurus, kdv_kurus, urunler, atif," +
    " musteri_ad, musteri_tel, musteri_eposta, musteri_adres, musteri_notu" +
    " FROM siparisler WHERE token = ?"
  ).bind(token).first();
  if (!siparis) return json({ hata: "bilinmeyen-token" }, 404, env);

  // 🔴 SUNUCU-TARAFI DOGRULAMA + dogrulanmis odemenin 'odendi' KAPANISI: TEK KAYNAK
  // `odemeHukmu()` (asagida). Cron terk supurmesi de AYNI fonksiyonu cagirir — ikinci
  // dogrulama kopyasi YOKTUR. Bu fonksiyon YALNIZ 'odendi' yazar; asagidaki ODENMEMIS
  // kollarin D1 yazmasi cagirana (yani buraya) aittir.
  const h = await odemeHukmu(env, ctx, token, siparis, {
    // istemci{ip,ua}: Meta eslesme kalitesi icin (client_ip_address / client_user_agent).
    // Bu istek MUSTERININ tarayicisindan gelir (iyzico redirect'i) -> IP/UA gercekten
    // musteriye aittir. Cron kolunda BOSTUR (orada IP/UA Cloudflare'indir, musterinin degil).
    istemci: {
      ip: request.headers.get("CF-Connecting-IP") || "",
      ua: request.headers.get("User-Agent") || "",
    },
  });
  const det = h.det;

  // ALTYAPI HATASI: retrieve CEVAP VEREMEDI -> odemenin gercek durumu BILINMIYOR.
  // 'basarisiz' yazmak parasi cekilmis musteriyi sessizce dusurur; 'incele' + yuksek sesli
  // bildirim. Otomatik onay YOK. Sonraki gecerli callback'te retrieve duzelirse 'odendi'ye
  // ilerleyebilir (asagidaki UPDATE'ler durum <> 'odendi' kosuluyla calisir).
  if (h.hal === "altyapi-hatasi") {
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
  // 🔴 K358: iyzico'nun KESIN-BASARISIZ kodlari (5122/10054/10057) da BU kola akar — eskiden
  // 'incele' + Telegram'a dusuyorlardi. Kart reddi INSAN INCELEMESI GEREKTIRMEZ (para ortada
  // degil, iyzico bunu kendisi beyan etti); o kol yalnizca gurultu uretiyordu. Telegram
  // BILEREK gitmez. Gercek altyapi hatasi ve `uyusmazlik` kollari AYNEN durur.
  if (h.hal === "basarisiz") {
    await env.KATALOG.prepare(
      "UPDATE siparisler SET durum = 'basarisiz' WHERE token = ? AND durum = 'bekliyor'"
    ).bind(token).run();
    return yonlendir(env, "hata", siparis.siparis_no);
  }

  // Odeme iyzico'da BASARILI ama bizim kayitla uyusmuyor: otomatik onaylanmaz,
  // insan incelemesine dusurulur + yuksek sesle bildirilir.
  if (h.hal === "uyusmazlik") {
    const beklenenTahsilat = siparis.tutar_kurus + (siparis.kargo_kurus || 0);
    await env.KATALOG.prepare(
      "UPDATE siparisler SET durum = 'incele', iyzico_odeme_id = ? WHERE token = ? AND durum <> 'odendi'"
    ).bind(String(det.paymentId || ""), token).run();
    ctx.waitUntil(telegram(env,
      "⚠️ PRUVO shop TUTARSIZLIK — " + siparis.siparis_no +
      "\niyzico paidPrice: " + det.paidPrice + " / bizim: " + kurusTL(beklenenTahsilat) +
      " (urun " + kurusTL(siparis.tutar_kurus) + " + kargo " + kurusTL(siparis.kargo_kurus || 0) + ")" +
      "\nconversationId: " + det.conversationId + "\nToken: " + token.slice(0, 12) + "…" +
      "\nSiparis 'incele' durumunda, elle bak."));
    // Musteri iyzico'dan donerken TARAYICIDADIR: ham 409 JSON gostermek yerine siteye
    // yonlendir (retrieve-altyapi-hatasi kolu ile AYNI desen — ikisi de 'incele' durumu).
    return yonlendir(env, "hata", siparis.siparis_no);
  }

  // Donus sayfasi KDV dokumu (kalem 8): tahsilat + kdv paramlari — istemci dokumu basar.
  // 🔴 BILET YALNIZ GERCEK GECISTE URL'YE KONUR (odemeHukmu degisti=false ise "" doner):
  // changes=0 demek "bu siparis ZATEN kapanmisti" demektir (ayni token 2. kez / geri tusu /
  // yenileme): sunucu CAPI olayini da TEKRARLAMADI, tarayici da TEKRARLAMAMALI.
  return yonlendir(env, "ok", siparis.siparis_no, {
    tahsilatKurus: siparis.tutar_kurus + (siparis.kargo_kurus || 0),
    kdvKurus: siparis.kdv_kurus || 0,
    bilet: h.bilet,
  });
}

/**
 * 🔴 TEK KAYNAK — ODEME HUKMU: iyzico `retrieve` ile sunucu-tarafi dogrulama + dogrulanmis
 * odemenin 'odendi' KAPANISI (atomik CAS UPDATE + uc katmanli idempotens + Purchase olcumu
 * + Telegram + onay e-postasi).
 *
 * IKI CAGIRAN VAR, IKINCI KOPYA YOK:
 *   1) `donus()`     — musteri iyzico'dan donunce (tarayici baglami VAR),
 *   2) `terkSupur()` — `scheduled` (cron) kolu, terk edilmis eski 'bekliyor' satirlari icin
 *                      (tarayici baglami YOK).
 * Supurmenin kendi dogrulamasini yazmasi bu yuzden YAPISAL OLARAK imkansizdir: "kor iptal"
 * sinifi ancak bu fonksiyon atlanarak uretilebilir.
 *
 * 🔴 D1 YAZMASI — SINIR: bu fonksiyon YALNIZ 'odendi' gecisini yazar. ODENMEMIS/BILINMEYEN
 * kollarin ('incele' / 'basarisiz' / 'iptal' / hic dokunmama) yazmasi CAGIRANA aittir,
 * cunku iki cagiranin hukmu FARKLIDIR: musteri callback'i 'basarisiz' yazar; terk supurmesi
 * 'iptal' + makine-okunur 'terk' sebebi yazar ve retrieve ULASILAMAZSA HICBIR SEY yazmaz.
 *
 * Doner: { hal, det, degisti, bilet }
 *   hal     : "altyapi-hatasi" | "basarisiz" | "uyusmazlik" | "odendi"
 *             ("basarisiz"in IKI kaynagi vardir ve ikisi de AYNI sozlesmedir: (1) retrieve
 *              basarili ama `paymentStatus !== "SUCCESS"`, (2) K358 KESIN-BASARISIZ —
 *              iyzico "failure" beyan etti ve kod KAPALI kumede.)
 *   det     : iyzico retrieve cevabi (altyapi hatasinda null/failure govdesi olabilir)
 *   degisti : YALNIZ hal="odendi" — bu cagri gecisi GERCEKTEN yapti mi (CAS changes>0)
 *   bilet   : YALNIZ degisti=true — tarayici Purchase bileti; aksi halde ""
 */
export async function odemeHukmu(env, ctx, token, siparis, secenek) {
  const s = secenek || {};
  const det = await cfDetay(env, token);

  // ALTYAPI HATASI (or. 1001 anahtar/URL uyusmazligi, gecici iyzico hatasi; DEVAM.md bulgusu,
  // 16 Tem): retrieve CEVAP VEREMEDIYSE odemenin gercek durumu BILINMIYOR — 'basarisiz' yazmak
  // parasi cekilmis musteriyi sessizce dusurur. 'incele' + yuksek sesli bildirim; otomatik
  // onay YOK. Sonraki gecerli callback'te retrieve duzelirse 'odendi'ye ilerleyebilir
  // (asagidaki UPDATE'ler durum <> 'odendi' kosuluyla calisir).
  if (!det || det.status !== "success") {
    // 🔴 K358 (31 Agu 2026) — UCUNCU SINIF: "KESIN BASARISIZ". Bu kapi IKI KOVALIYDI ve
    // iyzico CEVAP VERDIGI halde (`status:"failure"` + KAPALI kumede bir `errorCode`) hukum
    // "bilinmiyor" kovasina dusuyordu; fail-closed oldugu icin terk supurmesinin ZATEN VAR
    // OLAN `iptal` kolu hic kosmadi (K356 canli olcumu: 5/5 `ulasilamadi`, `degisen=0`).
    // Yuklem TEK KAYNAKTIR (iyzico.js kesinBasarisizMi) ve UCU BIRDEN arar: det VAR +
    // iyzico "failure" BEYAN ETTI + kod KAPALI kumede. Bilinmeyen/bos kod, taninmayan
    // `status` ve `det` yoklugu ASAGIDAKI fail-closed yolunda KALIR — kor iptal YASAK.
    const kesin = kesinBasarisizMi(det);
    // OLCUM IZI: burada Purchase GONDERILMEZ (odemenin gercek durumu BILINMIYOR). Sessiz
    // bosluk birakma — "bu siparisin Purchase'i neden yok?" sorusu loglardan cevaplanabilsin.
    //
    // 🔴 K356 (31 Agu 2026) — NEDEN ULASILAMADIGI DA YAZILIR. Cron terk supurmesi UC ardisik
    // turda `degisen=0` verdi; aged 'bekliyor' satirlari icin acilan TEK kol buydu ve
    // fail-closed oldugu icin hicbir sey yazmiyordu. Kod/metin loglanmadan "iyzico checkout
    // token omru esikten KISA (yapisal)" ile "gecici iyzico arizasi" AYIRT EDILEMIYOR.
    // 🔴 IKINCI LOG BICIMI ACILMADI: mevcut `olcum {...}` tek-satir JSON'una IKI ALAN eklendi
    // (terk supurmesinin `terk-supurme {...}` sayac satiriyla ayni sekil: etiket + tek satir
    // JSON). Yeni bir etiket/desen uretmek, grep'i ve gizlilik kapisini ikiye bolerdi.
    // 🔒 GIZLILIK: alanlar olcum.js LOG_ALANLARI BEYAZ LISTESINDEN gecer — musteri_*, atif
    // (fbp/fbc/ga_client_id) ve token listede OLMADIGI icin yapisal olarak basilamaz; metin
    // ayrica token maskesinden ve kirpmadan gecer (iyzico.js hataMetni).
    // 🔴 IKINCI LOG CAGRISI ACILMADI: `atlandi` iki hali AYIRIR ("kesin-basarisiz" ile
    // "retrieve-hatasi" ASLA ayni dizge degildir, yoksa logda birbirine karisirlardi);
    // alan listesi TEK yerde kalir, ikinci kopya sessizce ayrisamaz.
    olcumLog({ olay: "Purchase", siparis_no: siparis.siparis_no, kaynak: "kart",
               atlandi: kesin ? "kesin-basarisiz" : "retrieve-hatasi",
               errorCode: hataKodu(det), errorMessage: hataMetni(det, token) });
    // KESIN BASARISIZ: iyzico "bu odeme OLMADI" dedi -> MEVCUT `basarisiz` sozlesmesi.
    // D1 yazmasi yine CAGIRANIN: callback 'basarisiz' yazar (Telegram GITMEZ — kart reddi
    // insan incelemesi gerektirmez), terk supurmesi 'iptal' + makine-okunur 'terk' sebebi.
    if (kesin) { return { hal: "basarisiz", det: det, degisti: false, bilet: "" }; }
    // 🔴 FAIL-CLOSED: HICBIR D1 YAZMASI YAPILMAZ. Hukum cagiranindir — musteri callback'i
    // 'incele' yazar, cron supurmesi HIC DOKUNMAZ (bilinmeyen odemeyi iptal etmek parayi
    // gorunmez yapar). Iki farkli hukum burada birlestirilirse biri digerini ezerdi.
    return { hal: "altyapi-hatasi", det: det || null, degisti: false, bilet: "" };
  }

  // Retrieve CEVAP VERDI ve odeme basarili degil (or. kart reddi) -> gercek 'basarisiz'.
  //
  // 🔴 REKLAM OLCUMU ACISINDAN KRITIK KAPI: Purchase YALNIZ paymentStatus === "SUCCESS"
  // oldugunda gonderilir. Bu kosul gevserse karti REDDEDILEN musteri icin Meta+GA4'e
  // GERCEK TUTARLI SAHTE Purchase gider -> Okan'in reklam butcesi yanlis ogrenir, veri
  // geri alinamaz. Negatif testler: shop/test/olcum.mjs T25 (FAILURE/INIT_THREEDS/bos/
  // kucuk-harf 'success' degerleri icin 0 POST + atlandi logu).
  const odendi = det.paymentStatus === "SUCCESS";
  if (!odendi) {
    olcumLog({ olay: "Purchase", siparis_no: siparis.siparis_no, kaynak: "kart",
               atlandi: "odeme-basarisiz" });
    // D1 yazmasi CAGIRANIN: callback 'basarisiz' yazar, terk supurmesi 'iptal' + 'terk'.
    return { hal: "basarisiz", det: det, degisti: false, bilet: "" };
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
    // Odeme iyzico'da BASARILI ama bizim kayitla uyusmuyor: otomatik ONAYLANMAZ ve
    // asla IPTAL EDILMEZ — para ORTADA, insan incelemesine dusurulur (yazma cagiranda).
    // OLCUM IZI: Purchase GONDERILMEZ (tutar guvenilmez — yanlis ciro ogretmeyelim).
    olcumLog({ olay: "Purchase", siparis_no: siparis.siparis_no, kaynak: "kart",
               atlandi: "tutar-uyusmazligi" });
    return { hal: "uyusmazlik", det: det, degisti: false, bilet: "" };
  }

  // IDEMPOTENT kapanis: ayni token ikinci kez gelirse changes=0 -> bildirim de tekrarlanmaz.
  //
  // OLCUM IZI (havale yoluyla AYNI DESEN): durum_gecmisi'ne {"d":"odendi","z":ISO,"o":1}
  // dusulur ve bu AYNI atomik UPDATE icinde yazilir — AYRI bir yazma turu EKLENMEZ
  // (ikinci UPDATE yaris penceresi acardi). Kayit bicimi yonet.js gecmiseEkle()'den gelir;
  // TEK KAYNAK, ikinci kopya YOK.
  //   ⚠️ IZIN ANLAMI "DENENDI", "META ALDI" DEGIL: iz gonderim SONUCUNDAN once yazilir,
  //   olcum fire-and-forget'tir (secret yok / fbp yok / HTTP 400 hallerinde de iz "1" kalir).
  //   Ulasma kaniti YALNIZ Cloudflare Logs'taki `olcum {...}` satirindadir.
  //   Ayni dil havale yolunda da kullanilir (gecmiseEkle / olcumDenendiMi / "zaten-denendi").
  //   NEDEN GEREKLI: bu iz yazilmadan once tespit araci (tools/olculmemis-siparis.py) kart
  //   siparisleri icin DOLAYLI sinyale (iyzico_odeme_id dolu mu) yaslanmak zorundaydi;
  //   iyzico paymentId'yi bos dondurse ya da bu akis degisse tespit SESSIZCE yanlislanirdi.
  // IDEMPOTENS: iz de UPDATE'in bir parcasi oldugundan changes=0 (ayni token 2. kez)
  // halinde HIC yazilmaz -> gecmiste tek {"o":1} kalir, olay da tekrarlanmaz.
  // TARAYICI PURCHASE BILETI: tek kullanimlik, tahmin edilemez. Ayni atomik UPDATE icinde
  // durum_gecmisi'ne yazilir; yani D1'e YALNIZ gercek 'odendi' gecisiyle birlikte iner.
  // changes=0 (ayni token 2. kez) halinde HIC yazilmaz -> asagida URL'ye de KONMAZ.
  const pikselBileti = biletUret();
  const yeniGecmis = gecmiseEkle(siparis.durum_gecmisi, "odendi",
    { olcumDenendi: true, pikselBileti: pikselBileti });
  const g = await env.KATALOG.prepare(
    "UPDATE siparisler SET durum = 'odendi', iyzico_odeme_id = ?, durum_gecmisi = ?" +
    " WHERE token = ? AND durum <> 'odendi'"
  ).bind(String(det.paymentId || ""), yeniGecmis, token).run();

  if (g.meta && g.meta.changes > 0) {
    ctx.waitUntil(telegram(env, siparisMesaji(siparis, det)));
    // REKLAM ROI OLCUMU (reklam-roi-sistemi.md Faz 0): iyzico DOGRULAMASI OK dondu ve siparis
    // ILK KEZ 'odendi'ye gecti (idempotent: ayni token 2. kez changes=0 -> olay da tekrarlanmaz)
    // -> Purchase olayini Meta CAPI + GA4'e gonder. Fire-and-forget, best-effort: secret yoksa
    // no-op, POST hatasi siparis onayini/musteri akisini ETKILEMEZ (olcum.js guvenli()).
    //
    // istemci{ip,ua}: Meta eslesme kalitesi icin (client_ip_address / client_user_agent).
    // Bu istek MUSTERININ tarayicisindan gelir (iyzico redirect'i) -> IP/UA gercekten
    // musteriye aittir. 🔒 GIZLILIK: olcum.js bunlari YALNIZCA atif'ta fbp varsa gonderir
    // (fbp = riza kapisindan gecmis piksel kaniti) — karar ve gerekce metaGovdesi()'nde.
    // event_time verilmez: odeme SU AN dogrulandi, "simdi" dogru damgadir.
    // 🔒 GIZLILIK/DOGRULUK: `istemci` YALNIZ musteri tarayicisindan gelen cagrida (callback)
    // doludur. Cron terk supurmesinde BOS gecilir — oradaki IP/UA Cloudflare'in cron
    // calistiricisinindir, MUSTERININ DEGIL; yanlis kisiyi eslestirmek hic eslestirmemekten
    // kotudur (yonet.js havaleOlcumu'ndaki AYNI karar).
    olcumGonder(env, ctx, siparis, undefined, {
      kaynak: "kart",
      istemci: s.istemci,
    });
    // Musteriye onay e-postasi (tetik 1, kart odemesi onaylandi) + satici kopyasi.
    // IDEMPOTENT: yalniz changes>0'da (ayni token 2. kez -> e-posta da tekrarlanmaz).
    let satirlar = [];
    try { satirlar = JSON.parse(siparis.urunler) || []; } catch (e) { satirlar = []; }
    onayEpostalari(env, ctx, siparis, satirlar, {
      tutarKurus: siparis.tutar_kurus, kargoKurus: siparis.kargo_kurus || 0,
      kdvKurus: siparis.kdv_kurus || 0,
      tahsilatKurus: siparis.tutar_kurus + (siparis.kargo_kurus || 0),
    }, false);
  }
  // 🔴 BILET YALNIZ GERCEK GECISTE DISARI CIKAR. changes=0 demek "bu siparis ZATEN
  // kapanmisti" demektir (ayni token 2. kez / geri tusu / yenileme / cron ile callback'in
  // YARISI): sunucu CAPI olayini da TEKRARLAMADI, tarayici da TEKRARLAMAMALI. Bilet D1'e
  // inmediginden zaten dogrulanamazdi; disari vermemek gereksiz bir uc cagrisini da onler.
  const degisti = !!(g.meta && g.meta.changes > 0);
  return { hal: "odendi", det: det, degisti: degisti, bilet: degisti ? pikselBileti : "" };
}

// ------------------------------------------------ terk edilmis 'bekliyor' supurmesi (cron)

/**
 * 🔴 TERK ESIGI — TEK SABIT (mimar karari 30 Agu 2026). Koda SERPILMEZ: esigi okuyan tek
 * yer `terkSupur()`, yazan tek yer burasi.
 *
 * NEDEN 24 SAAT: iyzico'nun hosted odeme sayfasi bundan cok daha kisa surede olur; 24 saat
 * "musteri gercekten odedi ama callback dusmedi" ihtimaline comert bir pay birakir. Esigi
 * KISALTMAK, odemesi tamamlanmis ama callback'i gecikmis bir satiri erken degerlendirme
 * riskini buyutur — ve o satir zaten `retrieve` ile DOGRULANDIGI icin iptal degil 'odendi'
 * olur; yine de sabiti buyuk tutmak hatanin maliyetini dusurur.
 */
export const TERK_ESIK_SAAT = 24;

/**
 * 🔴 SUPURMENIN DOKUNABILECEGI TEK DURUM. Beyaz liste tektir ve TEK YERDE yazilidir:
 * asagidaki SELECT bunu bind eder, iki UPDATE'in CAS kosulu da BUNU bind eder.
 *   - 'havale-bekliyor' GERCEK SIPARISTIR (musteri banka havalesi gonderecek) — ne kadar
 *     eski olursa olsun DOKUNULMAZ. Adinin 'bekliyor' ile bitmesi bir tuzaktir: esitlik
 *     testi kullanilir, alt-dize/LIKE ASLA.
 *   - 'odendi' ve sonrasi (uretimde/kargolandi/tamamlandi), 'iptal', 'incele', 'basarisiz'
 *     de kapsam DISIDIR.
 */
export const TERK_KAYNAK_DURUM = "bekliyor";

/** `durum_gecmisi` kaydina dusen MAKINE-OKUNUR sebep (yonet.js gecmiseEkle -> {"s":"terk"}). */
export const TERK_SEBEP = "terk";

/** Bir cron turunda islenecek satir sayisi; artani sonraki tur alir. Amac tur suresini ve
 *  D1 yazma yukunu olculu tutmak. */
const TERK_TUR_TAVANI = 200;

/**
 * TERK EDILMIS ODEME DENEMELERINI SUPUR — ama ONCE DOGRULA.
 *
 * NEDEN VAR: kart akisinda `bekliyor` satiri, musteri iyzico odeme sayfasina YONLENDIRILIRKEN
 * (odemeden ONCE) yazilir; token saklanmak zorundadir, yoksa `/donus` dogrulamasi yapilamaz.
 * Musteri sayfayi kapatirsa o satir SONSUZA KADAR `bekliyor` kalir ve panelde gercek is
 * bekleyen siparislerden ayirt edilemez. Bunlari kapatan HICBIR SEY yoktu.
 *
 * 🔴 KOR IPTAL YASAK: bir `bekliyor` satiri, musterinin ODEYIP callback'i dusmemis GERCEK bir
 * tahsilati olabilir. Kor iptal parayi gorunmez yapar. Bu yuzden her satir icin `odemeHukmu()`
 * — yani `/donus` ile AYNI iyzico `retrieve` dogrulamasi — CAGRILIR; ikinci kopya YOK.
 *
 * HUKUM TABLOSU (odemeHukmu'nun dondugu hal -> burada yapilan):
 *   odendi         -> 'odendi' (odemeHukmu YAZDI). Bu TEMIZLIK DEGIL **PARA KURTARMADIR**:
 *                     Purchase olcumu + Telegram + onay e-postasi `/donus` ile AYNI yoldan
 *                     ve AYNI uc katmanli idempotensle gecer (ikinci kez SAYILMAZ).
 *   basarisiz      -> 'iptal' + gecmiste {"d":"iptal","s":"terk"}. Odeme YOK/expired.
 *                     K358: iyzico'nun KESIN-BASARISIZ kodlari (iyzico.js KAPALI kume) da
 *                     buraya akar — canlida bu satirlarin TAMAMI 'altyapi-hatasi' kovasina
 *                     dusuyor ve bu kol HIC KOSMUYORDU.
 *   uyusmazlik     -> 'incele' + Telegram. Para ORTADA ama tutar/kimlik tutmuyor: IPTAL EDILMEZ.
 *   altyapi-hatasi -> 🔴 HICBIR SEY. FAIL-CLOSED: retrieve ULASILAMADIYSA odemenin durumu
 *                     BILINMIYOR; sessizce iptal etmek tam da kacinilan zarardir. Satir
 *                     `bekliyor` kalir, sayac artar, sonraki tur yeniden dener.
 *
 * IDEMPOTENS: her yazma CAS'tir (`WHERE siparis_no = ? AND durum = ?`). Ayni supurme ikinci
 * kez kosunca islenen satirlar artik 'bekliyor' olmadigi icin SELECT'e bile girmez -> degisen=0.
 * Musteri callback'i supurme ile YARISIRSA yalniz biri changes>0 alir; Purchase TEK kalir.
 *
 * Doner: sayac nesnesi (asagida loglanir). Kisisel veri ICERMEZ.
 */
export async function terkSupur(env, ctx, simdi) {
  const an = Number.isFinite(simdi) ? simdi : Date.now();
  const esikISO = new Date(an - TERK_ESIK_SAAT * 3600 * 1000).toISOString();
  const sonuc = {
    esik_saat: TERK_ESIK_SAAT, esik: esikISO, bakilan: 0,
    odendi: 0, iptal: 0, incele: 0, ulasilamadi: 0, tokensiz: 0, degisen: 0,
  };

  // `tarih` ISO-8601 UTC metnidir (INSERT: new Date().toISOString()) -> sozlukbilimsel
  // karsilastirma kronolojik siralamayla BIREBIR ortusur.
  const q = await env.KATALOG.prepare(
    "SELECT siparis_no, token, tarih, durum, durum_gecmisi, tutar_kurus, kargo_kurus," +
    " kdv_kurus, urunler, atif, musteri_ad, musteri_tel, musteri_eposta, musteri_adres," +
    " musteri_notu FROM siparisler WHERE durum = ? AND tarih < ? ORDER BY tarih ASC LIMIT ?"
  ).bind(TERK_KAYNAK_DURUM, esikISO, TERK_TUR_TAVANI).all();
  const satirlar = (q && q.results) || [];

  for (const s of satirlar) {
    sonuc.bakilan++;
    // Kart akisinda token DAIMA doludur; bossa dogrulama YAPILAMAZ -> FAIL-CLOSED, dokunma.
    if (!s.token) { sonuc.tokensiz++; continue; }

    let h;
    try {
      // 🔴 `istemci` GECILMEZ: bu tur Cloudflare'in cron calistiricisindan kosar; buradaki
      // IP/UA musteriye AIT DEGILDIR (yonet.js havaleOlcumu ile AYNI karar).
      h = await odemeHukmu(env, ctx, s.token, s, {});
    } catch (e) {
      // Beklenmeyen hata da "bilinmiyor"dur -> FAIL-CLOSED, yazma YOK.
      console.error("terk supurmesi odemeHukmu hatasi:", s.siparis_no, (e && e.stack) || e);
      sonuc.ulasilamadi++;
      continue;
    }

    if (h.hal === "altyapi-hatasi") { sonuc.ulasilamadi++; continue; }

    if (h.hal === "odendi") {
      // Yazmayi odemeHukmu yapti (CAS + idempotens + olcum + bildirim + e-posta).
      if (h.degisti) { sonuc.odendi++; }
      continue;
    }

    if (h.hal === "uyusmazlik") {
      const gu = await env.KATALOG.prepare(
        "UPDATE siparisler SET durum = 'incele', iyzico_odeme_id = ?" +
        " WHERE siparis_no = ? AND durum = ?"
      ).bind(String((h.det && h.det.paymentId) || ""), s.siparis_no, TERK_KAYNAK_DURUM).run();
      if (gu.meta && gu.meta.changes > 0) { sonuc.incele++; }
      ctx.waitUntil(telegram(env,
        "⚠️ PRUVO shop TERK SUPURMESI — TUTARSIZLIK: " + s.siparis_no +
        "\niyzico paidPrice: " + (h.det && h.det.paidPrice) +
        " / bizim: " + kurusTL(s.tutar_kurus + (s.kargo_kurus || 0)) +
        "\nOdeme VAR ama kayitla uyusmuyor — IPTAL EDILMEDI, 'incele' durumunda, elle bak."));
      continue;
    }

    // h.hal === "basarisiz": retrieve CEVAP VERDI ve odeme YOK/expired -> terk edilmis deneme.
    const yeniGecmis = gecmiseEkle(s.durum_gecmisi, "iptal", { sebep: TERK_SEBEP });
    const gi = await env.KATALOG.prepare(
      "UPDATE siparisler SET durum = 'iptal', durum_gecmisi = ?" +
      " WHERE siparis_no = ? AND durum = ?"
    ).bind(yeniGecmis, s.siparis_no, TERK_KAYNAK_DURUM).run();
    if (gi.meta && gi.meta.changes > 0) { sonuc.iptal++; }
  }

  sonuc.degisen = sonuc.odendi + sonuc.iptal + sonuc.incele;
  // Sessiz bosluk birakma: "bu tur ne yapti?" sorusu Cloudflare Logs'tan cevaplanabilsin.
  // Kisisel veri YOK — yalniz sayaclar (siparis numarasi bile basilmaz).
  console.log("terk-supurme", JSON.stringify(sonuc));
  return sonuc;
}

/**
 * POST /olcum-donus — tarayici Purchase'inin SUNUCU HUKMU (shop/src/olcum-bilet.js).
 *
 * Govde: { no: "<siparis_no>", b: "<bilet>" }   Cevap: { ok:true, value, currency } | { ok:false }
 *
 * 🔒 CEVAP SOZLESMESI: basarisizlik kolu SEBEP TASIMAZ. "siparis yok" ile "bilet yanmis"i
 * ayirt edilebilir yapmak, siparis numarasi deneyerek ciro/siparis varligi sorgulamaya izin
 * verirdi. Sebep yalniz sunucu loguna yazilir (olcumLog), musteriye DEGIL.
 * Kisisel veri DONMEZ: yalniz dogrulanmis tahsilat tutari.
 */
async function olcumDonusu(request, env) {
  let govde = {};
  try { govde = await request.json(); } catch (e) { govde = {}; }
  const no = govde && govde.no;
  const b = govde && govde.b;
  const h = await biletDogrula(env, no, b);
  // Teshis izi: "bu siparisin tarayici Purchase'i neden yok?" sorusu loglardan cevaplanabilsin
  // (sessiz bosluk birakma — olcum.js/donus() ile AYNI dil).
  olcumLog({ olay: "Purchase", hedef: "tarayici",
             siparis_no: typeof no === "string" ? no : "",
             kaynak: "kart", atlandi: h.ok ? "" : h.sebep });
  if (!h.ok) { return json({ ok: false }, 200, env); }
  return json({ ok: true, value: h.value, currency: h.currency }, 200, env);
}

/** Havale bildirimi (kalem 6). DIKKAT: para HENUZ gorulmedi — metin "odeme geldi" tonunda
 *  OLAMAZ (kabul testi 13 bunu sinar); uretim ancak elle onaydan (KURULUM.md komutu) sonra. */
function havaleMesaji(siparisNo, satirlar, urunKurus, kargoKurus, tahsilatKurus, musteri, acikAdres,
  musteri_notu) {
  // Beyan bos ise (fiziksel kalem) " — ASA / turuncu" ibaresi HIC basilmaz; bkz. kalemSecimi.
  const kalemler = satirlar.map((s) =>
    "• " + s.baslik + (kalemSecimi(s) ? " — " + kalemSecimi(s) : "") +
    (s.parametre_detay ? " [" + s.parametre_detay + "]" : "") +
    " × " + s.adet + " = " + kurusTL(s.tutar_kurus)).join("\n");
  return "🏦 HAVALE BEKLENIYOR: " + siparisNo + " " + kurusTL(tahsilatKurus) +
    "\n" + kalemler +
    "\nAra toplam: " + kurusTL(urunKurus) +
    "\nGönderim: " + (kargoKurus > 0 ? kurusTL(kargoKurus) : "Bedava") +
    "\nGenel toplam: " + kurusTL(tahsilatKurus) +
    "\nMusteri: " + musteri.ad + " — " + musteri.tel +
    "\nAdres: " + acikAdres +
    (musteri_notu ? "\nNot: " + musteri_notu : "") +
    "\nDekont gorulunce shop/KURULUM.md'deki wrangler komutuyla isaretle; " +
    "isaretlenmeden uretim baslamaz, bildirim atilmaz.";
}

function siparisMesaji(siparis, det) {
  let satirlar = [];
  try { satirlar = JSON.parse(siparis.urunler) || []; } catch (e) { satirlar = []; }
  const kalemler = satirlar.map((s) =>
    "• " + s.baslik + (kalemSecimi(s) ? " — " + kalemSecimi(s) : "") +
    (s.parametre_detay ? " [" + s.parametre_detay + "]" : "") +
    " × " + s.adet + " = " + kurusTL(s.tutar_kurus)).join("\n");
  const kargo = siparis.kargo_kurus || 0;
  return "🛒 YENI SIPARIS (odendi) — " + siparis.siparis_no +
    "\n" + kalemler +
    "\nAra toplam: " + kurusTL(siparis.tutar_kurus) +
    "\nGönderim: " + (kargo > 0 ? kurusTL(kargo) : "Bedava") +
    "\nGenel toplam: " + kurusTL(siparis.tutar_kurus + kargo) +
    "\nMusteri: " + siparis.musteri_ad + " — " + siparis.musteri_tel +
    "\nAdres: " + siparis.musteri_adres +
    (siparis.musteri_notu ? "\nNot: " + siparis.musteri_notu : "") +
    "\niyzico odeme id: " + (det.paymentId || "?");
}

/** Siparis onay e-postalari (tetik 1: odendi / havale-bekliyor) — musteri + satici kopyasi.
 *  ctx.waitUntil ile: yanit bloklanmaz; anahtar yok/gonderim hatasi Telegram'a duser, siparis
 *  akisini ASLA dusurmez (epostaAkisi try/catch'li). */
function onayEpostalari(env, ctx, siparis, satirlar, dokum, havale) {
  const musteriHtml = onayEpostasiHtml(siparis, satirlar, dokum, havale, false);
  const saticiHtml = onayEpostasiHtml(siparis, satirlar, dokum, havale, true);
  const olaylar = [];
  if (siparis.musteri_eposta) {
    olaylar.push({ kime: siparis.musteri_eposta, konu: "Sipariş onayı — " + siparis.siparis_no,
                   html: musteriHtml, etiket: "müşteri" });
  }
  if (env.BILDIRIM_EPOSTA) {
    olaylar.push({ kime: env.BILDIRIM_EPOSTA, konu: "Yeni sipariş — " + siparis.siparis_no,
                   html: saticiHtml, etiket: "satıcı" });
  }
  if (olaylar.length) {
    ctx.waitUntil(epostaAkisi(env, telegram, siparis.siparis_no, olaylar));
  }
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
      if (yol === "/baslat" && request.method === "POST") return await baslat(request, env, url, ctx);
      // PROVA (yan etkisiz fiyat sorgusu): /baslat ile AYNI dogrulama + AYNI hesap, TUTAR doner;
      // D1'e yazmaz, iyzico/Telegram/e-posta yok. Yalniz POST (govde sepet tasir).
      if (yol === "/fiyat" && request.method === "POST") return await fiyatProva(request, env);
      if (yol === "/donus") return await donus(request, env, ctx);
      // TARAYICI PURCHASE KAPISI: donus sayfasi olayi atmadan ONCE burayi cagirir. Bilet
      // dogrulanip YAKILIR (tek kullanimlik) -> {ok:true, value}. Her basarisizlik AYNI
      // {ok:false} cevabini verir (sebep SIZDIRILMAZ) ve tarayici olayi ATMAZ.
      if (yol === "/olcum-donus" && request.method === "POST") {
        return await olcumDonusu(request, env);
      }
      // wa.me lead attribution (OCI #1): landing beacon'i REF->click-id'yi D1'e kalici kilar.
      // Handler yalniz POST'u yazar, digerini 204 gecer; her durumda 204 (bilgi sizmaz).
      if (yol === "/ref") return await refKaydet(request, env);
      // Anahtar korumali yonetim (same-origin; anahtar yok/yanlis -> 404, telegram fallback icin
      // index.js'in telegram fonksiyonu gecirilir).
      if (yol === "/yonet" || yol.startsWith("/yonet/")) {
        const altYol = yol.slice("/yonet".length) || "/";
        return await yonet(request, env, url, ctx, altYol, telegram);
      }
      return json({ hata: "bulunamadi" }, 404, env);
    } catch (e) {
      console.error("pruvo-shop hata:", e && e.stack || e);
      return json({ hata: "sunucu-hatasi" }, 500, env);
    }
  },

  /**
   * CRON KOLU (wrangler.toml [triggers] crons) — terk edilmis 'bekliyor' satirlarinin
   * DOGRULAYAN supurmesi. Tek is budur; baska yan etki yoktur.
   *
   * Sikligi BILEREK DUSUK (saatlik): is aciliyet tasimaz (esik 24 saat) ve her tur D1
   * yazma kotasi harcar. Hata TUM turu dusurur ama bir sonraki tur temiz baslar —
   * yarim kalan satirlar `bekliyor` kaldigi icin yeniden ele alinir (fail-closed).
   */
  async scheduled(controller, env, ctx) {
    try {
      await terkSupur(env, ctx, controller && controller.scheduledTime);
    } catch (e) {
      console.error("pruvo-shop cron (terk supurmesi) dustu:", (e && e.stack) || e);
    }
  },
};
