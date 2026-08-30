/**
 * KABUL BATARYASI — PANEL "KAYNAK" SATIRI (siparisi hangi kanal/kampanya getirdi).
 *
 * Neyi olcer:
 *   (a) atifli site siparisi   -> utm_* + ref + kampanya grubu BASILIR, sinif dogru
 *   (b) atifsiz site siparisi  -> "kaynak kaydı yok" ACIKCA yazilir (sessiz bosluk YOK)
 *   (c) WhatsApp siparisi      -> kanal WhatsApp, utm YOK
 *   (d) 🔴 NEGATIF — `fbp` / `fbc` / `ga_client_id` ciktida HIC GECMEZ (uc ad AYRI AYRI
 *       aranir; tek dizge aramasi biri gecerken otekini gizleyebilirdi). Ayrica
 *       reklam tablosunun click-id'leri (gclid/gbraid/wbraid) de gecmez.
 *   (e) TANIMADIGIMIZ kanal -> OLCULEMEDI hali; sessizce bir kovaya YAZILMAZ
 *   (f) 🔴 MUTANT — kanal-sinifi.js'e cakilan 4 hedefli mutantin DORDU DE, ADI VERILEN
 *       iddiayi kirmizi yakmali; KONTROL mutanti YESIL kalmali. Mutant yakmiyorsa
 *       iddia degil DEKOR yazmisiz demektir.
 *
 * wrangler GEREKMEZ: /liste'nin D1 katmani sahte bir KATALOG binding'i ile taklit edilir.
 * 🔴 Olculen sey CALISAN GERCEK GOVDEDIR: hem `liste()` hem panelin `kaynakSatiriHtml()`
 * govdesi yonet.js'in KENDI metninden cikarilip degerlendirilir (yeniden yazilmis bir
 * kopya degil) — kopya olsaydi kaynak degisince test sessizce eski davranisi olcerdi.
 *
 * Kosum:  node shop/test/kanal-gorunurluk.mjs
 */
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURASI = dirname(fileURLToPath(import.meta.url));
const SRC = join(BURASI, "..", "src");

// ---------------------------------------------------------------- FIKSTUR SATIRLARI
const ATIFLI = {
  id: 1, siparis_no: "PR-A", tarih: "2026-08-30T10:00:00Z", durum: "odendi",
  tutar_kurus: 20000, kargo_kurus: 5000, kdv_kurus: 4200, odeme_yontemi: "kart",
  urunler: "[]", kargo_firma: "", kargo_kodu: "", durum_gecmisi: "[]",
  kanal: "site", dis_no: "",
  // 🔴 Gizli alanlar BILEREK doludur: suzgec olculebilsin diye. Gercek siparislerde de
  // bu kayitta dururlar — testin isi ekrana GECMEDIKLERINI kanitlamak.
  atif: JSON.stringify({
    utm_source: "google", utm_medium: "cpc", utm_campaign: "yaz-kampanya",
    utm_id: "17654321", ref: "REF:GS-MRN-9K2A",
    ga_client_id: "GA1.1.999.888", fbp: "fb.1.1700.111", fbc: "fb.1.1700.CLICKID",
  }),
  musteri_ad: "A", musteri_tel: "1", musteri_eposta: "a@b.c", musteri_adres: "x",
  musteri_notu: "",
};
const ATIFSIZ = { ...ATIFLI, id: 2, siparis_no: "PR-B", atif: "{}" };
const WHATSAPP = { ...ATIFLI, id: 3, siparis_no: "PR-C", kanal: "whatsapp",
                   dis_no: "PR-260830-100000", atif: "" };
// (e) Yarin eklenecek bir kanal. BUGUN tanimiyoruz -> hukum YOK demeli.
const BILINMEYEN = { ...ATIFLI, id: 4, siparis_no: "PR-D", kanal: "instagram" };

const REKLAM_SATIRI = { ref: "REF:GS-MRN-9K2A", grup: "MRN", src: "GS",
                        gclid: "CJ-GIZLI-CLICKID", gbraid: "GB-GIZLI", wbraid: "WB-GIZLI" };

// ---------------------------------------------------------------- SAHTE D1
function sahteEnv(satirlar) {
  const hazirla = (sql) => ({
    bind: (...p) => ({
      all: async () => {
        if (/FROM siparisler/.test(sql)) { return { results: satirlar }; }
        if (/FROM reklam_ref_gclid/.test(sql)) {
          return { results: p.includes(REKLAM_SATIRI.ref) ? [REKLAM_SATIRI] : [] };
        }
        return { results: [] };
      },
      first: async () => null,
    }),
  });
  return { KATALOG: { prepare: hazirla }, SITE_URL: "https://pruvo3d.com" };
}

/** `liste()` disa acilmadigi icin govdesi modul METNINDEN cikarilip calistirilabilir
 *  bir modul olarak sarilir. Cevresindeki yardimcilar (kimlik kapisi, baski fisi,
 *  urun kaynagi) BU olcumun ekseni DEGIL; sadeleri konur. Kaynak/atif eksenindeki
 *  her sey (kaynakOzeti, kaynakRefi, reklam JOIN'i) GERCEK govdeden gelir. */
async function listeCiktisi(satirlar, yonetYolu, siniflandiriciYolu) {
  const metin = readFileSync(yonetYolu, "utf8");
  const bas = metin.indexOf("async function liste(env, url) {");
  if (bas < 0) { throw new Error("liste() govdesi bulunamadi"); }
  const son = metin.indexOf("\n// ---- durum gecmisi yardimci", bas);
  if (son < 0) { throw new Error("liste() govdesinin sonu bulunamadi"); }
  const govde = metin.slice(bas, son);
  const refBas = metin.indexOf("function kaynakRefi(atif) {");
  if (refBas < 0) { throw new Error("kaynakRefi() govdesi bulunamadi"); }
  const refSon = metin.indexOf("\n}", refBas) + 2;
  const refGovde = metin.slice(refBas, refSon);

  const dizin = mkdtempSync(join(tmpdir(), "kanal-liste-"));
  const yol = join(dizin, "liste.mjs");
  try {
    writeFileSync(yol, [
      "import { kaynakOzeti, atifCoz } from " +
        JSON.stringify(pathToFileURL(siniflandiriciYolu).href) + ";",
      'const KANAL_SITE = "site";',
      "const SEMALAR = new Map();",
      'function baskiOnerisi(){ return ""; }',
      "function driveKaynaklari(){ return []; }",
      "function izinliHedefler(){ return []; }",
      "function kaynakLinkSuz(){ return ''; }",
      "function yjson(veri, kod){ return { veri, kod }; }",
      "async function kolonMerdiveni(kolonlu){ return kolonlu(); }",
      "async function tabloMerdiveni(tablolu){ return tablolu(); }",
      refGovde,
      "export " + govde,
    ].join("\n"), "utf8");
    const m = await import(pathToFileURL(yol).href);
    const sonuc = await m.liste(sahteEnv(satirlar), new URL("https://x/liste"));
    return sonuc.veri.siparisler;
  } finally {
    rmSync(dizin, { recursive: true, force: true });
  }
}

/** Panelin kart HTML'i — SAYFA_HTML sablonundan CIKARILAN gercek `kaynakSatiriHtml`
 *  govdesi calistirilir (ekranda ne yazacagini o soyler). */
function kaynakSatiriUretici(yonetYolu) {
  const metin = readFileSync(yonetYolu, "utf8");
  const bas = metin.indexOf("function kaynakSatiriHtml(s){");
  if (bas < 0) { throw new Error("kaynakSatiriHtml govdesi bulunamadi"); }
  const son = metin.indexOf("\nfunction satirHtml(no,k){", bas);
  if (son < 0) { throw new Error("kaynakSatiriHtml sonu bulunamadi"); }
  const govde = metin.slice(bas, son);
  const esc = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  // 🔴 SERBEST DEGISKEN OLMAMALI: panel govdesi yalnizca `esc` ve kendi argumaniyla
  // calismali. "kaynak kaydı yok" dili veriyle (k.yok) gelir; govde onu kendi icinde
  // yeniden yazarsa ikinci sozluk dogar. Asagidaki `new Function` yalniz `esc` verir —
  // govde baska bir dis degere uzanirsa BURADA coker ve test kirmizi yanar.
  // eslint-disable-next-line no-new-func
  const uret = new Function("esc", govde + "\nreturn kaynakSatiriHtml;");
  return uret(esc);
}

// ---------------------------------------------------------------- IDDIALAR
const GIZLI_ADLAR = ["fbp", "fbc", "ga_client_id"];
const GIZLI_DEGERLER = ["fb.1.1700.111", "fb.1.1700.CLICKID", "GA1.1.999.888"];
const CLICK_ID_DEGERLERI = ["CJ-GIZLI-CLICKID", "GB-GIZLI", "WB-GIZLI"];

async function iddialar(yonetYolu, siniflandiriciYolu) {
  const hatalar = [];
  let gecti = 0;
  const iddia = (ad, kosul, ek) => {
    if (kosul) { gecti++; return; }
    hatalar.push(ad + (ek ? "  → " + String(ek).slice(0, 240) : ""));
  };

  const cikti = await listeCiktisi([ATIFLI, ATIFSIZ, WHATSAPP, BILINMEYEN],
                                   yonetYolu, siniflandiriciYolu);
  const [a, b, c, d] = cikti;
  // "kaynak kaydı yok" dili KANONIK moduldan okunur — testte ikinci kopya TUTULMAZ.
  const { KAYNAK_YOK_METNI } = await import(pathToFileURL(siniflandiriciYolu).href);
  const html = kaynakSatiriUretici(yonetYolu);

  // (a) ATIFLI
  iddia("a1 sinif site-ucretli", a.kaynak && a.kaynak.sinif === "site-ucretli",
        JSON.stringify(a.kaynak));
  iddia("a2 utm_source tasindi", a.kaynak.atif.utm_source === "google");
  iddia("a3 utm_medium tasindi", a.kaynak.atif.utm_medium === "cpc");
  iddia("a4 utm_campaign tasindi", a.kaynak.atif.utm_campaign === "yaz-kampanya");
  iddia("a5 ref tasindi", a.kaynak.atif.ref === "REF:GS-MRN-9K2A");
  iddia("a6 reklam grubu JOIN'lendi", a.kaynak.grup === "MRN" && a.kaynak.src === "GS",
        JSON.stringify(a.kaynak));
  const aHtml = html(a);
  iddia("a7 panel utm_source BASIYOR", aHtml.includes("google"), aHtml);
  iddia("a8 panel kampanya BASIYOR", aHtml.includes("yaz-kampanya"), aHtml);
  iddia("a9 panel ref BASIYOR", aHtml.includes("REF:GS-MRN-9K2A"), aHtml);
  iddia("a10 panel sinif etiketi BASIYOR", aHtml.includes("site · ücretli"), aHtml);
  iddia("a11 panel grup/src BASIYOR", aHtml.includes("MRN") && aHtml.includes("GS"), aHtml);

  // (b) ATIFSIZ
  iddia("b1 sinif atif-yok", b.kaynak.sinif === "atif-yok", JSON.stringify(b.kaynak));
  const bHtml = html(b);
  iddia("b2 panel 'kaynak kaydı yok' YAZIYOR", bHtml.includes(KAYNAK_YOK_METNI), bHtml);
  iddia("b3 sessiz bosluk YOK", bHtml.trim().length > 0);

  // (c) WHATSAPP
  iddia("c1 sinif whatsapp", c.kaynak.sinif === "whatsapp", JSON.stringify(c.kaynak));
  iddia("c2 kanal whatsapp", c.kanal === "whatsapp");
  const cHtml = html(c);
  iddia("c3 panel WhatsApp etiketi", cHtml.includes("WhatsApp"), cHtml);
  iddia("c4 utm alani YOK", Object.keys(c.kaynak.atif).length === 0,
        JSON.stringify(c.kaynak.atif));
  iddia("c5 panel utm BASMIYOR", !/utm_id|ortam <b>|kampanya <b>/.test(cHtml), cHtml);

  // (e) BILINMEYEN KANAL -> hukum YOK (sessizce bir kovaya yazilmaz)
  const dHtml = html(d);
  iddia("e1 bilinmeyen kanal sinifi null", d.kaynak.sinif === null,
        JSON.stringify(d.kaynak));
  iddia("e2 panel OLCULEMEDI rozeti", dHtml.includes("olculemedi"), dHtml);
  iddia("e3 panel 'kaynak kaydı yok' etiketi", dHtml.includes(KAYNAK_YOK_METNI), dHtml);

  // (d) 🔴 NEGATIF — uc ad AYRI AYRI, hem JSON'da hem HTML'de.
  const jsonHepsi = JSON.stringify(cikti);
  const htmlHepsi = [aHtml, bHtml, cHtml, dHtml].join("\n");
  for (const ad of GIZLI_ADLAR) {
    iddia("d/ad '" + ad + "' /liste JSON'unda GECMIYOR", !jsonHepsi.includes(ad));
    iddia("d/ad '" + ad + "' panel HTML'inde GECMIYOR", !htmlHepsi.includes(ad));
  }
  for (const deger of GIZLI_DEGERLER) {
    iddia("d/deger '" + deger + "' GECMIYOR",
          !jsonHepsi.includes(deger) && !htmlHepsi.includes(deger));
  }
  for (const deger of CLICK_ID_DEGERLERI) {
    iddia("d/click-id '" + deger + "' GECMIYOR",
          !jsonHepsi.includes(deger) && !htmlHepsi.includes(deger));
  }
  return { gecti, hatalar };
}

// ---------------------------------------------------------------- MUTANTLAR
/**
 * 🔴 Her mutant HEDEF KOLA atfedilir: hangi iddianin onu yakalamasi gerektigi YAZILI.
 * "Bir yerde kirmizi yandi" YETMEZ — yanlis eksende yanan kirmizi korlugu gizler
 * ([[sinif-adi-kol-adi-olarak-basilirsa-yanlis-alan-dogrulanir]]).
 */
const MUTANTLAR = [
  { ad: "M1 'atif-yok' kovasi organige katlanir",
    ara: "  if (!isaretVarMi(a)) { return KOVA_ATIF_YOK; }",
    yaz: "  if (!isaretVarMi(a)) { return KOVA_SITE_ORGANIK; }",
    kol: "b1" },
  { ad: "M2 bilinmeyen/eksik kanal sessizce siniflanir",
    ara: "  if (kanal !== KANAL_SITE && kanal !== KANAL_WHATSAPP) { return null; }",
    yaz: "  if (kanal !== KANAL_SITE && kanal !== KANAL_WHATSAPP) { return KOVA_ATIF_YOK; }",
    kol: "e1" },
  { ad: "M3 fbp panele sizar (beyaz liste delinir)",
    ara: 'export const ATIF_GORUNUR_ALANLAR = ["utm_source", "utm_medium", "utm_campaign", '
       + '"utm_id", "ref"];',
    yaz: 'export const ATIF_GORUNUR_ALANLAR = ["utm_source", "utm_medium", "utm_campaign", '
       + '"utm_id", "ref", "fbp"];',
    kol: "d/ad 'fbp'" },
  { ad: "M4 ucretli/organik ayrimi kaldirilir",
    ara: "  return ucretliMi(a) ? KOVA_SITE_UCRETLI : KOVA_SITE_ORGANIK;",
    yaz: "  return KOVA_SITE_ORGANIK;",
    kol: "a1" },
  { ad: "KONTROL (yalniz yorum eklendi — davranis AYNI)",
    ara: "export const KOVA_SITE_UCRETLI",
    yaz: "// KONTROL MUTANTI — davranisa dokunmaz\nexport const KOVA_SITE_UCRETLI",
    kol: null },
];

async function mutantlariKos() {
  const kok = mkdtempSync(join(tmpdir(), "kanal-mutant-"));
  const sonuclar = [];
  try {
    for (const m of MUTANTLAR) {
      const kaynak = readFileSync(join(SRC, "kanal-sinifi.js"), "utf8");
      if (!kaynak.includes(m.ara)) {
        // 🔴 Capa cokmesi SESSIZ GECILMEZ: mutant ulasmadiysa olcum yapilmamistir.
        sonuclar.push({ ad: m.ad, kol: m.kol, hal: "CAPA_COKTU", hatalar: [],
                        not: "capa kaynakta YOK: " + m.ara.slice(0, 70) });
        continue;
      }
      const dizin = mkdtempSync(join(kok, "m-"));
      writeFileSync(join(dizin, "kanal-sinifi.js"), kaynak.replace(m.ara, m.yaz), "utf8");
      const yonetYolu = join(SRC, "yonet.js");
      let r;
      try {
        r = await iddialar(yonetYolu, join(dizin, "kanal-sinifi.js"));
      } catch (e) {
        r = { gecti: 0, hatalar: ["COKTU: " + (e && e.message)] };
      }
      sonuclar.push({ ad: m.ad, kol: m.kol,
                      hal: r.hatalar.length ? "KIRMIZI" : "YESIL", hatalar: r.hatalar });
    }
  } finally {
    rmSync(kok, { recursive: true, force: true });
  }
  return sonuclar;
}

/**
 * 🔴 SABLON BUTUNLUGU — OLCULMUS BIR ARIZA SINIFI (30 Agu 2026).
 * Panel kodu `SAYFA_HTML` sablon dizesinin ICINDE yasar. Oraya konan tek bir TERS TIRNAK
 * (or. bir yorumda `atif-yok` yazmak) sablonu ERKEN BITIRIR ve TUM yonet.js modulu
 * ayristirilamaz olur — panel komple olur. `node --check yonet.js` bunu YAKALAMAZ:
 * dosya .js oldugu icin ESM olarak ayristirilmaz ve YESIL doner. Bu yuzden kaynak
 * gecici bir .mjs kopyasina yazilip AYRISTIRILIR (arizayi bulan olcumun ta kendisi).
 */
function sablonButunlugu(yonetYolu) {
  const dizin = mkdtempSync(join(tmpdir(), "kanal-sozdizim-"));
  const kopya = join(dizin, "yonet.mjs");
  try {
    writeFileSync(kopya, readFileSync(yonetYolu, "utf8"), "utf8");
    execFileSync(process.execPath, ["--check", kopya], { stdio: "pipe" });
    return "";
  } catch (e) {
    return String((e && e.stderr) || e).slice(0, 300);
  } finally {
    rmSync(dizin, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------- KOSUM
const sozdizimHatasi = sablonButunlugu(join(SRC, "yonet.js"));
if (sozdizimHatasi) {
  console.log("  ✗ z1 yonet.js ES modulu olarak AYRISMIYOR (SAYFA_HTML sablonu bozuk?)");
  console.log("      | " + sozdizimHatasi.split("\n").filter(Boolean).slice(0, 3).join(" | "));
  process.exit(1);
}
console.log("✓ z1 yonet.js ES modulu olarak ayrisiyor (SAYFA_HTML sablonu butun)");

const taban = await iddialar(join(SRC, "yonet.js"), join(SRC, "kanal-sinifi.js"));
console.log("TABAN  iddia=%d kirmizi=%d", taban.gecti, taban.hatalar.length);
for (const h of taban.hatalar) { console.log("  ✗ " + h); }

const mutantSonuc = await mutantlariKos();
let mutantHatasi = 0;
for (const m of mutantSonuc) {
  const beklenenHal = m.kol ? "KIRMIZI" : "YESIL";
  const halUygun = m.hal === beklenenHal;
  const koluYakti = m.kol ? (m.hatalar || []).some((h) => h.startsWith(m.kol)) : true;
  const ok = halUygun && koluYakti;
  if (!ok) { mutantHatasi++; }
  console.log("%s %s  hal=%s%s%s", ok ? "✓" : "✗", m.ad, m.hal,
              m.kol ? ("  kol='" + m.kol + "' " + (koluYakti ? "YAKTI" : "YAKMADI")) : "",
              m.not ? ("  " + m.not) : "");
  if (!ok) { for (const h of (m.hatalar || []).slice(0, 3)) { console.log("      | " + h); } }
}

const kirmizi = taban.hatalar.length + mutantHatasi;
console.log("SONUC iddia=%d kirmizi=%d mutant=%d/%d",
            taban.gecti, kirmizi, mutantSonuc.length - mutantHatasi, mutantSonuc.length);
process.exit(kirmizi ? 1 : 0);
