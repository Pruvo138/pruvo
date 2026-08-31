#!/usr/bin/env node
/**
 * PRUVO shop — YONETIM PANELI: SIPARIS KAYNAGI (KANAL + REKLAM ATFI).
 *
 *   node shop/test/panel-atif.mjs
 *
 * NE OLCER: bir siparisin hangi kanaldan (site / WhatsApp) ve hangi reklamdan
 * (utm_* / REF) geldiginin panelde GORUNDUGUNU — ve hangi alanlarin GORUNMEDIGINI.
 *
 * NEDEN wrangler'siz: olculen davranis SAF yuzeylerdedir —
 *   (A) shop/src/kanal-sinif.mjs — kanal+atif siniflamasinin TEK kaynagi (DOGRUDAN import;
 *       raporun kullandigi modulun TA KENDISI, kopya degil),
 *   (B) panelin `kaynakSatiriHtml()`/`kartHtml()` render'i — shop/src/yonet.js'ten HAM
 *       KAYNAK olarak cekilip vm'de kosturulur; KOPYA YAZILMAZ (kopya yazilsaydi kaynak
 *       degistiginde test yesil kalir, iddia sessizce olurdu),
 *   (C) `/liste` kablolamasi — kaynak metninde capa olarak olculur.
 * Desen kardesi: shop/test/panel-kaynak.mjs — ayni dilimleme gerekcesi orada yazili.
 *
 * 🔴 FIKSTUR UYDURMADIR: gercek musteri verisi, gercek telefon, gercek kampanya adi bu
 * dosyaya YAZILMAZ. Fikstur yalnizca BICIMI taklit eder. Asagidaki `fbp`/`fbc`/
 * `ga_client_id` degerleri de UYDURMA sabitlerdir — NEGATIF iddianin capasidirlar
 * (cikti icinde ARANIRLAR, cikti icine KONMAZLAR).
 *
 * ONCE-KIRMIZI KANITI: `python3 tools/kanal-gorunurluk-mutasyon.py` (gecici AYNAYA
 * uygular; calisma agacina yazmaz).
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (kaynak capasi bulunamadi).
 */

import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

import {
  KOVALAR, KOVA_ETIKET, CIRO_DURUMLARI, BASILMAYAN_ATIF_ALANLARI,
  KOVA_SITE_UCRETLI, KOVA_SITE_ORGANIK, KOVA_WHATSAPP, KOVA_ATIF_YOK,
  KOVA_KANAL_BILINMIYOR, KOVA_KANAL_OLCULEMEDI,
  atifAlanlari, kanalKovasi, kaynakOzeti, ciroyaGirer, tahsilatKurus,
} from "../src/kanal-sinif.mjs";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KAYNAK_YOL = process.env.PRUVO_YONET_KAYNAK || path.join(BURASI, "..", "src", "yonet.js");
const KAYNAK = fs.readFileSync(KAYNAK_YOL, "utf8");

let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}
/** Kaynaktan [baslangic, bitis) dilimi. Capalar bulunamazsa null (fail-loud). */
function dilimAl(metin, baslangic, bitis) {
  const b = metin.indexOf(baslangic);
  const s = b >= 0 ? metin.indexOf(bitis, b + baslangic.length) : -1;
  return (b >= 0 && s > b) ? metin.slice(b, s) : null;
}
/** SAYFA_HTML bir sablon dizesidir: `\\'` tarayiciya `\'` gider — vm icin cozulur. */
function sablonCoz(s) { return s.replace(/\\\\/g, "\\"); }

// 🔴 NEGATIF CAPALAR — UYDURMA degerler. Bu uc alan panele/JSON'a HIC girmemeli.
const FBP = "fb.1.9999999999999.1234567890";
const FBC = "fb.1.9999999999999.SAHTE-CLICK-ID";
const GA_CID = "GA1.1.9999999999.8888888888";
const ATIF_TAM = JSON.stringify({
  ga_client_id: GA_CID, fbp: FBP, fbc: FBC,
  utm_source: "google", utm_medium: "cpc", utm_campaign: "yaz-kampanyasi",
  utm_id: "17777777777", ref: "REF:GS-BK-9Z3Q",
});

// ---------------------------------------------------------------- A) SINIFLAMA (TEK KAYNAK)
console.log("A) kanal-sinif.mjs — kova yargisi (raporun kullandigi MODULUN TA KENDISI)");

ol("A0  kova listesi DORT is kovasini + IKI gorunur bilinmiyorum kovasini tasiyor",
  KOVALAR.length === 6 &&
  KOVALAR.indexOf(KOVA_SITE_UCRETLI) >= 0 && KOVALAR.indexOf(KOVA_SITE_ORGANIK) >= 0 &&
  KOVALAR.indexOf(KOVA_WHATSAPP) >= 0 && KOVALAR.indexOf(KOVA_ATIF_YOK) >= 0 &&
  KOVALAR.indexOf(KOVA_KANAL_BILINMIYOR) >= 0 && KOVALAR.indexOf(KOVA_KANAL_OLCULEMEDI) >= 0,
  JSON.stringify(KOVALAR));
ol("A0a her kovanin bir etiketi VAR (etiketsiz kova ekranda ham id gosterirdi)",
  KOVALAR.every((k) => typeof KOVA_ETIKET[k] === "string" && KOVA_ETIKET[k].length > 0));

ol("A1  REF:GS-… -> site-ucretli",
  kanalKovasi("site", '{"ref":"REF:GS-BK-9Z3Q"}').kova === KOVA_SITE_UCRETLI);
ol("A2  REF:OG-… -> site-organik",
  kanalKovasi("site", '{"ref":"REF:OG-BK-9Z3Q"}').kova === KOVA_SITE_ORGANIK);
ol("A3  kanal 'whatsapp' -> whatsapp (atif bos olsa da)",
  kanalKovasi("whatsapp", "").kova === KOVA_WHATSAPP &&
  kanalKovasi("whatsapp", ATIF_TAM).kova === KOVA_WHATSAPP);

// 🔴 SPEC OLDURUCUSU: 'atif yok' ORGANIGE KATLANMAZ.
ol("A4  site + atif BOS -> atif-yok/siniflanamaz (ORGANIK DEGIL)",
  kanalKovasi("site", "").kova === KOVA_ATIF_YOK &&
  kanalKovasi("site", "").kova !== KOVA_SITE_ORGANIK);
ol("A4a site + atif VAR ama cozulemez (utm_medium tanimsiz, ref yok) -> ayni kova, FARKLI sebep",
  (() => {
    const bos = kanalKovasi("site", "");
    const coz = kanalKovasi("site", '{"utm_source":"bilinmeyen","utm_medium":"zzz"}');
    return coz.kova === KOVA_ATIF_YOK && bos.sebep === "atif-bos" &&
      coz.sebep === "atif-cozulemedi";
  })());
ol("A4b bozuk JSON / dizi / null -> patlamaz, atif-yok kovasina duser",
  kanalKovasi("site", "{bozuk").kova === KOVA_ATIF_YOK &&
  kanalKovasi("site", "[1,2]").kova === KOVA_ATIF_YOK &&
  kanalKovasi("site", null).kova === KOVA_ATIF_YOK);

// 🔴 SPEC OLDURUCUSU: `kanal` YOKKEN 'site' SAYILMAZ.
ol("A5  kanal undefined/'' -> kanal-olculemedi (SITE SAYILMAZ)",
  kanalKovasi(undefined, ATIF_TAM).kova === KOVA_KANAL_OLCULEMEDI &&
  kanalKovasi("", ATIF_TAM).kova === KOVA_KANAL_OLCULEMEDI &&
  kanalKovasi(undefined, ATIF_TAM).kova !== KOVA_SITE_UCRETLI);
// 🔴 UCUNCU SINIF: tanimadigi kanal degeri site'ye de whatsapp'a de YAZILMAZ.
ol("A6  kanal 'instagram-dm' gibi TANIMSIZ deger -> kanal-bilinmiyor (yutulmaz)",
  (() => {
    const k = kanalKovasi("instagram-dm", "");
    return k.kova === KOVA_KANAL_BILINMIYOR && k.sebep === "kanal:instagram-dm";
  })());

ol("A7  utm_medium yedek ekseni: cpc -> ucretli, organic -> organik",
  kanalKovasi("site", '{"utm_medium":"cpc"}').kova === KOVA_SITE_UCRETLI &&
  kanalKovasi("site", '{"utm_medium":"CPC"}').kova === KOVA_SITE_UCRETLI &&
  kanalKovasi("site", '{"utm_medium":"organic"}').kova === KOVA_SITE_ORGANIK);
ol("A7a ref, utm_medium ile CELISIRSE ref KAZANIR (dogrulanmis dar anahtar)",
  kanalKovasi("site", '{"ref":"REF:GS-BK-9Z3Q","utm_medium":"organic"}').kova
    === KOVA_SITE_UCRETLI);
ol("A8  ref'ten grup/src AYRISTIRILIYOR (ek D1 okumasi olmadan)",
  (() => {
    const o = kaynakOzeti("site", '{"ref":"REF:GS-BK-9Z3Q"}');
    return o.src === "GS" && o.grup === "BK";
  })(), JSON.stringify(kaynakOzeti("site", '{"ref":"REF:GS-BK-9Z3Q"}')));

// ---- CIRO KAPSAMI ----
ol("A9  ciro kapsami: odendi/uretimde/kargolandi/tamamlandi GIRER",
  ["odendi", "uretimde", "kargolandi", "tamamlandi"].every(ciroyaGirer));
// 🔴 SPEC OLDURUCUSU: bekliyor/iptal ciroya GIRMEZ.
ol("A9a bekliyor · iptal · havale-bekliyor · incele · basarisiz ciroya GIRMEZ",
  ["bekliyor", "iptal", "havale-bekliyor", "incele", "basarisiz"]
    .every((d) => !ciroyaGirer(d)) && !CIRO_DURUMLARI.has("iptal") &&
  !CIRO_DURUMLARI.has("bekliyor"));
ol("A9b tahsilat = tutar_kurus + kargo_kurus (musterinin odedigi)",
  tahsilatKurus({ tutar_kurus: 125000, kargo_kurus: 9000 }) === 134000 &&
  tahsilatKurus({ tutar_kurus: 100 }) === 100 && tahsilatKurus({}) === 0);

// ---- BEYAZ-LISTE ----
ol("A10 atifAlanlari() POZITIF beyaz-liste: yalniz utm_*/ref gecer",
  (() => {
    const a = atifAlanlari(ATIF_TAM);
    return Object.keys(a).sort().join(",") ===
      "ref,utm_campaign,utm_id,utm_medium,utm_source";
  })(), JSON.stringify(atifAlanlari(ATIF_TAM)));
ol("A10a beyaz-liste FAIL-CLOSED: atfa yeni bir alan girerse OTOMATIK BASILMAZ",
  Object.keys(atifAlanlari('{"yeni_reklam_kimligi":"XYZ","utm_source":"g"}')).join(",")
    === "utm_source");
ol("A10b BASILMAYAN_ATIF_ALANLARI uc adi da beyan ediyor (belge capasi)",
  BASILMAYAN_ATIF_ALANLARI.join(",") === "ga_client_id,fbp,fbc");

// 🔴 NEGATIF — kaynakOzeti() ciktisinda uc yasak ad AYRI AYRI aranir.
const OZET_TAM = JSON.stringify(kaynakOzeti("site", ATIF_TAM));
ol("A11 kaynakOzeti ciktisinda 'ga_client_id' ADI da DEGERI de YOK",
  OZET_TAM.indexOf("ga_client_id") < 0 && OZET_TAM.indexOf(GA_CID) < 0, OZET_TAM);
ol("A11a kaynakOzeti ciktisinda 'fbp' ADI da DEGERI de YOK",
  OZET_TAM.indexOf("fbp") < 0 && OZET_TAM.indexOf(FBP) < 0, OZET_TAM);
ol("A11b kaynakOzeti ciktisinda 'fbc' ADI da DEGERI de YOK",
  OZET_TAM.indexOf("fbc") < 0 && OZET_TAM.indexOf(FBC) < 0, OZET_TAM);

// ---------------------------------------------------------------- B) PANEL RENDER
console.log("B) panel render — GERCEK esc()/kaynakSatiriHtml()/kartHtml()");
const panelKaynak = sablonCoz(dilimAl(KAYNAK, "function esc(s){", "async function yukle(){") || "");
if (!panelKaynak) {
  console.error("KAYNAK CAPASI BULUNAMADI (sayfa JS blogu) — yonet.js yapisi degisti mi?");
  process.exit(3);
}
const panel = { document: null };
vm.createContext(panel);
vm.runInContext(panelKaynak, panel, { filename: "yonet-sayfa.js" });
const kaynakSatiriHtml = panel.kaynakSatiriHtml;
const kartHtml = panel.kartHtml;
if (typeof kaynakSatiriHtml !== "function" || typeof kartHtml !== "function") {
  console.error("SAYFA FONKSIYONLARI CEKILEMEDI (kaynakSatiriHtml/kartHtml) — OLCULEMEDI");
  process.exit(3);
}

const musteri = {
  ad: "Ornek Musteri", tel: "0500 000 00 00",
  eposta: "ornek@ornek.invalid", adres: "Ornek Mah. Ornek Sk. No 1",
};
const kalem = {
  kalem: 0, id: "ornek-parca", baslik: "Örnek Parça", malzeme: "PETG", renk: "Siyah",
  adet: 1, parametrik: false, parametre_detay: "", baski_oneri: "PETG siyah, 0.16 mm.",
  uretim_kaynaklari: [], urun_url: "https://pruvo3d.com/urun/ornek-parca/", kaynak_link: "",
};
function siparis(kanalHam, atifHam, durum) {
  return {
    siparis_no: "PR-TEST-1", tarih: "2026-08-31T10:00:00Z", durum: durum || "uretimde",
    kanal: kanalHam || "site", dis_no: "", odeme_yontemi: "kart",
    tutar_kurus: 125000, kargo_kurus: 9000, kdv_kurus: 22500,
    kargo_firma: "", kargo_kodu: "", durum_gecmisi: [], izinli_gecisler: ["tamamlandi"],
    musteri: musteri, kalemler: [kalem], musteri_notu: "",
    yazdir_komut: "python3 tools/yazdir.py PR-TEST-1",
    // Sunucunun (kaynakOzeti) urettigi ozet — panel bunu OLDUGU GIBI basar.
    kaynak: kaynakOzeti(kanalHam, atifHam),
  };
}

// VAKA a — ATIFLI site siparisi: utm + ref BASILIR
const kAtifli = kartHtml(siparis("site", ATIF_TAM));
ol("Ba  atifli kartta 'Kaynak' satiri BASILIYOR",
  kAtifli.indexOf("📣 Kaynak:") > 0, kAtifli.slice(0, 300));
ol("Ba1 utm_source · utm_medium · utm_campaign · utm_id GORUNUYOR",
  kAtifli.indexOf("google") > 0 && kAtifli.indexOf("cpc") > 0 &&
  kAtifli.indexOf("yaz-kampanyasi") > 0 && kAtifli.indexOf("17777777777") > 0);
ol("Ba2 ref + ondan turetilen grup/src GORUNUYOR",
  kAtifli.indexOf("REF:GS-BK-9Z3Q") > 0 && kAtifli.indexOf("grup: BK") > 0 &&
  kAtifli.indexOf("src: GS") > 0);
ol("Ba3 kova ETIKETI basiliyor (ham kova id'si degil)",
  kAtifli.indexOf(KOVA_ETIKET[KOVA_SITE_UCRETLI]) > 0);
ol("Ba4 karar SEBEBI de basiliyor (bos kova 'neden bos' sorusunu cevaplasin)",
  kAtifli.indexOf("(ref:GS)") > 0);

// VAKA b — ATIFSIZ: SESSIZ BOSLUK YASAK
// 🔴 IDDIA KART GENELINDE DEGIL, KENDI SATIRINDA OLCULUR. Kartta AYNI metni ("kaynak
// kaydı yok") uretebilen IKINCI bir yer daha var: kalem satirindaki `kaynakLinkHtml()`
// (uretici kaynagi). Kart genelinde arayan bir iddia, bu satir tamamen bossaltilsa
// bile komsunun metniyle YESIL kalirdi — mutant M6 tam bunu gosterdi
// ([[ad-iki-rolde-mutanti-golgeler]]). Bu yuzden once fonksiyonun KENDI ciktisi,
// sonra karttan DILIMLENEN kendi satiri olculur.
const kAtifsiz = kartHtml(siparis("site", ""));
const satirAtifsiz = kaynakSatiriHtml(siparis("site", ""));
const satirAtifli = kaynakSatiriHtml(siparis("site", ATIF_TAM));
/** Karttan YALNIZ "Kaynak" satirini dilimle (komsu satirlar iddiaya karismasin). */
function kaynakSatiri(kart) {
  return dilimAl(kart, '<div class="kucuk kaynak-atif">', "</div>") || "";
}
ol("Bb  atif YOKKEN 'kaynak kaydı yok' KENDI SATIRINDA yaziliyor (bos DEGIL)",
  satirAtifsiz.indexOf("kaynak kaydı yok") > 0, satirAtifsiz);
ol("Bb0 karttan DILIMLENEN Kaynak satiri da bos DEGIL (komsu metne yaslanmiyor)",
  kaynakSatiri(kAtifsiz).indexOf("kaynak kaydı yok") > 0, kaynakSatiri(kAtifsiz));
ol("Bb1 atifsiz kartta 'Kaynak' satiri YINE VAR (satirin kendisi kaybolmuyor)",
  kAtifsiz.indexOf("📣 Kaynak:") > 0);
ol("Bb2 atifsiz Kaynak SATIRINDA utm/ref alan ETIKETLERI HIC basilmiyor",
  satirAtifsiz.indexOf("kaynak: ") < 0 && satirAtifsiz.indexOf("ref: ") < 0 &&
  satirAtifsiz.indexOf("kampanya: ") < 0);
ol("Bb3 atifli ile atifsiz SATIR farkli (iddia gercekten ayirt ediyor)",
  satirAtifli !== satirAtifsiz && kAtifli !== kAtifsiz);

// VAKA c — WHATSAPP: kanal WA, utm YOK
const kWa = kartHtml(siparis("whatsapp", ""));
ol("Bc  WhatsApp siparisinde kova etiketi WhatsApp (Ege)",
  kWa.indexOf(KOVA_ETIKET[KOVA_WHATSAPP]) > 0, kWa.slice(0, 400));
ol("Bc1 WhatsApp kartinda utm/ref alani BASILMIYOR (atif zaten bos yazilir)",
  kWa.indexOf("kaynak: ") < 0 && kWa.indexOf("ref: ") < 0 &&
  kaynakSatiri(kWa).indexOf("kaynak kaydı yok") > 0, kaynakSatiri(kWa));
ol("Bc2 mevcut kanal ROZETI bozulmadi (regresyon)",
  kWa.indexOf('<span class="rozet kanal">whatsapp</span>') > 0);

// VAKA — kanal kolonu YOK: ekran 'site' DEMEZ
const kKanalsiz = kartHtml(siparis(undefined, ATIF_TAM));
ol("Bd  kanal kolonu YOKKEN kart 'kanal ölçülemedi' der (site DEMEZ)",
  kKanalsiz.indexOf(KOVA_ETIKET[KOVA_KANAL_OLCULEMEDI]) > 0 &&
  kKanalsiz.indexOf(KOVA_ETIKET[KOVA_SITE_UCRETLI]) < 0, kKanalsiz.slice(0, 400));

// VAKA d — 🔴 NEGATIF: uc yasak ad panelde HIC GECMEZ (ayri ayri, her kartta)
const TUM_KARTLAR = [kAtifli, kAtifsiz, kWa, kKanalsiz].join("\n");
ol("Bd1 NEGATIF: 'ga_client_id' panel ciktisinda HIC gecmiyor (ad ve deger)",
  TUM_KARTLAR.indexOf("ga_client_id") < 0 && TUM_KARTLAR.indexOf(GA_CID) < 0);
ol("Bd2 NEGATIF: 'fbp' panel ciktisinda HIC gecmiyor (ad ve deger)",
  TUM_KARTLAR.indexOf("fbp") < 0 && TUM_KARTLAR.indexOf(FBP) < 0);
ol("Bd3 NEGATIF: 'fbc' panel ciktisinda HIC gecmiyor (ad ve deger)",
  TUM_KARTLAR.indexOf("fbc") < 0 && TUM_KARTLAR.indexOf(FBC) < 0);
ol("Bd4 NEGATIF: click-id (gclid/gbraid/wbraid) panelde de basilmiyor",
  TUM_KARTLAR.indexOf("gclid") < 0 && TUM_KARTLAR.indexOf("gbraid") < 0 &&
  TUM_KARTLAR.indexOf("wbraid") < 0);

// HTML kacisi — atif degeri musteri tarafindan etkilenebilir bir girdidir.
const kXss = kartHtml(siparis("site",
  JSON.stringify({ utm_campaign: '<script>alert(1)</script>', utm_medium: "cpc" })));
ol("Be  atif degerindeki < > ESCAPE ediliyor (ham <script> YOK)",
  !/<script>/i.test(kXss) && kXss.indexOf("&lt;script&gt;") > 0, kXss.slice(0, 400));

// Panelde `s.kaynak` HIC yoksa (eski bir yanit) satir sessizce atlanir, patlamaz.
ol("Bf  s.kaynak YOKKEN kaynakSatiriHtml bos doner (eski yanitla patlamaz)",
  kaynakSatiriHtml({}) === "" && kaynakSatiriHtml(undefined) === "");

// ---------------------------------------------------------------- C) /liste KABLOLAMASI
console.log("C) Worker /liste kablolamasi — kaynak metninde capa");
const listeTaban = dilimAl(KAYNAK, "async function liste(env, url) {", "const sonuc = await");
if (!listeTaban) {
  console.error("KAYNAK CAPASI BULUNAMADI (liste TABAN) — OLCULEMEDI");
  process.exit(3);
}
ol("C1  /liste SELECT'i `atif` kolonunu CEKIYOR (yoksa panel hep bos gorurdu)",
  /\batif\b/.test(listeTaban), listeTaban.slice(-300));
ol("C2  /liste ciktisina kaynakOzeti() konuyor — HAM s.kanal ile ('site' varsayilani YOK)",
  KAYNAK.indexOf("kaynak: kaynakOzeti(s.kanal, s.atif)") > 0);
ol("C3  siniflama TEK KAYNAKTAN import ediliyor (yonet.js'te ikinci kopya YOK)",
  KAYNAK.indexOf('from "./kanal-sinif.mjs"') > 0 &&
  KAYNAK.indexOf('const KANAL_SITE = "site"') < 0 &&
  KAYNAK.indexOf('const WA_KANAL = "whatsapp"') < 0);
// 🔒 HAM atif JSON'u istemciye GITMEMELI — yalniz suzulmus ozet gider.
ol("C4  /liste ciktisinda HAM `atif` alani YOK (yalniz suzulmus ozet gider)",
  (() => {
    const donus = dilimAl(KAYNAK, "    return {\n      siparis_no: s.siparis_no,",
      "      yazdir_komut:") || "";
    return donus.length > 0 && !/^\s*atif:/m.test(donus);
  })());

// ---------------------------------------------------------------- SONUC
console.log("\n%d gecti / %d kaldi", gecen, kalan);
process.exit(kalan === 0 ? 0 : 1);
