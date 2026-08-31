#!/usr/bin/env node
/**
 * KONFIGUR FAIL-CLOSED KABUL TESTI — "D1'de var, Worker bundle'inda yok" penceresinde
 * SESSIZ EKSIK TAHSILAT olmadigini kanitlar.
 *
 *   node shop/test/konfigur-fail-closed.mjs
 *
 * NASIL (OFFLINE — wrangler/ag/gercek odeme YOK): shop/src/index.js'in KENDISI Node'a
 * yuklenir, D1 ve iyzico yerine bellek-ici sahteleri konur. Fiyat, worker'in D1'e YAZDIGI
 * satirdan okunur — yani gercek para yolundan. Hicbir dis servise istek gitmez, hicbir
 * siparis olusmaz, hicbir kalici dosya degismez.
 *
 * NODE 20 UYUMU (CI arizasi, 28 Tem — deploy.yml node-version 20): bu test once ESM yukleme
 * kancasi (module.registerHooks, Node 22.15+) kullaniyordu; yerelde Node 25'te YESIL, CI'da
 * "TypeError: module.registerHooks is not a function" ile KIRMIZI yandi ve TUM site yayinini
 * durdurdu. Kanca KALDIRILDI: Worker kaynaklari (bare JSON import'lari gomulu sabitlere
 * cevrilerek) shop/ ALTINDA AYNI DERINLIKTE gecici bir dizine (shop/src-test-tmp-<pid>/)
 * yazilir ve oradan import edilir — goreli yollar (../../secenekler.js, ../../jenerator/...)
 * aynen cozulur. Kullanilan API'lerin hepsi Node 20 tabaninda: fs/path/url/vm/child_process +
 * global fetch/Request/Response (18+). Dizin calisma sonunda (finally + process 'exit')
 * silinir; bayat kopyalar her kosumun BASINDA da supurulur.
 *
 * KOSTUGU 5 SET:
 *   (a) REGRESYON — 13 konfigur urununun hepsi, KONFIGURLAR'da VARKEN: fiyat DEGISMEDI
 *       (yeni index == eski index (git HEAD) == front /konfigur.js orakili, birebir kurus).
 *   (b) PARA KANITI — urun D1'de var, KONFIGURLAR'da YOK: 400 "konfigur-urun", sabit fiyat
 *       HESAPLANMAZ, D1'e satir YAZILMAZ, iyzico oturumu ACILMAZ.
 *   (c) YANLIS-POZITIF — canli katalogdan genis konfigursuz orneklem: hicbiri "konfigur-urun"
 *       yemez (+ konfigurBeklenirMi tahmini TUM katalogda 13/13 birebir).
 *   (d) VAKUM (mutasyon) — index.js'ten kapi SILINIRSE (a)+(c) yesil kalmali ama (b) KIRMIZI
 *       yanmali. Mutant yesil kalirsa bu test OLU nobetcidir -> suite KIRMIZI.
 *   (e) MUSTERI METNI — worker'in DONDURDUGU hata kodu index.html HATA_METNI'nde karsiligini
 *       bulmali (jenerik "Odeme baslatilamadi" metnine DUSMEMELI), metin WhatsApp'a yonlendirmeli
 *       ve marka kurallarina uymali (baski/basim/3D ailesi + sehir adi YOK). Girdi silinirse
 *       (vakum) jenerik metne duser -> iddia KIRMIZI. Hata kodu UYDURULMAZ, worker'dan alinir.
 */

import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath, pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const SRC = path.join(SHOP, "src");
const require = createRequire(import.meta.url);

// ------------------------------------------------- Node 20 uyumlu yukleyici (kanca YOK)
// Worker kaynagi bare JSON import kullanir (esbuild bundle'lar; Node import NITELIGI ister ve
// nitelik sozdiziminin surum tabani Node surumune gore oynar). Surum-bagimsiz cozum: JSON
// import satiri, dosyanin ICERIGI gomulu bir `const` ile DEGISTIRILIR -> geriye hicbir ozel
// sozdizimi kalmaz, her Node'da ayni sekilde ayristirilir.
//
// Kopyalar shop/src ILE AYNI DERINLIKTE (shop/src-test-tmp-<pid>/) durur: dizin-ici goreli
// import'lar (./semalar.js) kopyalara, depo koku import'lari (../../secenekler.js,
// ../../jenerator/...) GERCEK dosyalara cozulur. Depo dosyalari DEGISMEZ; gecici dizin
// finally + process 'exit' ile silinir, bayat kopyalar kosum basinda supurulur.
const TEMP_ONEK = "src-test-tmp-";
const TEMP_DIZIN = path.join(SHOP, TEMP_ONEK + process.pid);

function tempSupur() {
  for (const ad of fs.readdirSync(SHOP)) {
    if (ad.startsWith(TEMP_ONEK)) {
      fs.rmSync(path.join(SHOP, ad), { recursive: true, force: true });
    }
  }
}

/** `import X from "...json";` -> `const X = <json icerigi>;` (fail-closed: bozuk JSON patlar). */
function jsonGom(kaynak, kaynakDizin, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(kaynakDizin, rel), "utf8").trim();
      JSON.parse(ham);                       // bozuk JSON sessizce sizmasin
      return "const " + ad + " = " + ham + ";";
    });
  // NOBETCI: gomulemeyen bir JSON import kalirsa Node'da anlasilmaz bir sozdizimi/nitelik
  // hatasi verirdi -> burada acikca patla (yeni import bicimi eklenmisse desen guncellensin).
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ") — desen guncellenmeli");
  }
  return cikti;
}

function tempKur() {
  tempSupur();
  fs.mkdirSync(TEMP_DIZIN, { recursive: true });
  for (const ad of fs.readdirSync(SRC)) {
    // 🔴 `.mjs` DE KOPYALANIR (31 Agu 2026): ayna shop/src'in TAMAMINI temsil etmeli.
    // `.js` suzgeci shop/src/kanal-sinif.mjs'i sessizce disarida birakiyordu -> onu
    // import eden yonet.js aynada ERR_MODULE_NOT_FOUND ile dusuyordu. Eksik kopya,
    // olculen yuzeyi olculmemis yapar.
    if (!/\.m?js$/.test(ad)) { continue; }
    fs.writeFileSync(path.join(TEMP_DIZIN, ad),
                     jsonGom(fs.readFileSync(path.join(SRC, ad), "utf8"), SRC, ad));
  }
}

tempKur();
process.on("exit", () => { fs.rmSync(TEMP_DIZIN, { recursive: true, force: true }); });

let sanalSayac = 0;
/** Verilen index.js kaynagini (gercek/eski/mutant) gecici dizinden modul olarak yukler. */
async function indexYukle(kaynak) {
  sanalSayac += 1;
  const yol = path.join(TEMP_DIZIN, "index-surum-" + sanalSayac + ".js");
  fs.writeFileSync(yol, jsonGom(kaynak, SRC, "index-surum-" + sanalSayac));
  return await import(pathToFileURL(yol).href);
}

// ---------------------------------------------------------------- sahte cevre (D1 + iyzico)

let iyzicoCagri = 0;
globalThis.fetch = async function sahteFetch(hedef) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (u.includes("iyzico.test")) {
    iyzicoCagri += 1;
    return new Response(JSON.stringify({
      status: "success", token: "test-token-" + iyzicoCagri,
      paymentPageUrl: "https://odeme.test/sayfa",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  throw new Error("TESTTE BEKLENMEYEN AG ISTEGI: " + u);
};

/** D1 sahtesi: katalog SELECT'i verilen satirlardan cevaplar, INSERT'leri kaydeder. */
function d1Sahte(satirlar, kayitlar) {
  const harita = new Map(satirlar.map((u) => [u.id, u]));
  return {
    prepare(sql) {
      return {
        bind(...arg) {
          return {
            async all() {
              return { results: arg.map((id) => harita.get(id)).filter(Boolean) };
            },
            async first() { return null; },       // siparis_no carpismasi yok
            async run() { kayitlar.push({ sql, arg }); return { meta: { changes: 1 } }; },
          };
        },
      };
    },
  };
}

const ENV = {
  SITE_URL: "https://pruvo3d.com",
  IYZICO_BASE_URL: "https://iyzico.test",
  IYZICO_API_KEY: "test-api-key",
  IYZICO_SECRET_KEY: "test-secret-key",
};

/** /baslat'i GERCEK worker kodundan cagirir; cevabi + D1'e yazilan satiri dondurur. */
async function baslat(mod, d1Satirlari, kalem) {
  const kayitlar = [];
  const env = Object.assign({}, ENV, { KATALOG: d1Sahte(d1Satirlari, kayitlar) });
  const oncekiIyzico = iyzicoCagri;
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sozlesme_onay: true, odeme: "kart",
      musteri: { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
                 adres: "Test mahallesi test sokak no 1", sehir: "Mugla" },
      sepet: [kalem],
    }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  const insert = kayitlar.find((k) => /INSERT INTO siparisler/.test(k.sql));
  let birimKurus = null, tutarKurus = null;
  if (insert) {
    const dizi = insert.arg.find((x) => typeof x === "string" && x.startsWith("["));
    const satir = dizi ? JSON.parse(dizi)[0] : null;
    birimKurus = satir ? satir.birim_kurus : null;
    tutarKurus = insert.arg.find((x) => typeof x === "number" && x > 0) ?? null;
  }
  return { kod: cevap.status, govde, birimKurus, tutarKurus,
           d1Yazildi: Boolean(insert), iyzicoAcildi: iyzicoCagri > oncekiIyzico };
}

// ---------------------------------------------------------------- veri

require(path.join(KOK, "secenekler.js"));
const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi"); }
const FRONT = require(path.join(KOK, "konfigur.js"));   // bagimsiz fiyat orakili

const URUNLER = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));
const KONFIGUR_URUNLER = URUNLER.filter((u) => u.konfigur);

/** Anahtar sirasindan bagimsiz kanonik JSON (d1-sync.py konfigur_kanonik aynasi). */
function kanonik(o) {
  if (o === null || typeof o !== "object") { return JSON.stringify(o); }
  if (Array.isArray(o)) { return "[" + o.map(kanonik).join(",") + "]"; }
  return "{" + Object.keys(o).sort().map((k) => JSON.stringify(k) + ":" + kanonik(o[k]))
    .join(",") + "}";
}

/** urunler.json kaydindan D1 satiri (d1-sync.py'nin yazdigi alanlar + `konfigur` kolonu).
 *  FAZ 4'ten beri fiyat BU KOLONDAN hesaplanir -> satir onsuz kurulursa kalem fail-closed
 *  400 alir; `konfigurUstuneYaz` ile o hal (bos/bozuk metin) bilerek kurulabilir. */
function d1Satiri(u, konfigurUstuneYaz) {
  return { id: u.id, baslik: u.baslik || "", kategori: u.kategori || "",
           fiyat: u.fiyat || "", parametrik: u.parametrik ? 1 : 0,
           gorsel: (u.gorseller && u.gorseller[0]) || "",
           konfigur: konfigurUstuneYaz !== undefined ? konfigurUstuneYaz
             : (u.konfigur ? kanonik(u.konfigur) : "") };
}

// (b) senaryosunun urunu: D1'e YENI girmis konfigur urunu, Worker HENUZ deploy edilmemis
// (KONFIGURLAR'da YOK). Gercek pencerenin birebir modeli.
const YENI_KONFIGUR = { id: "ejderha-serit-dekoratif-figur", baslik: "Ejderha Heykeli — Şerit",
                        kategori: "Skan Art", fiyat: "500 TL", parametrik: 0, gorsel: "" };

// ---------------------------------------------------------------- suite

const KAYNAK = fs.readFileSync(path.join(SHOP, "src", "index.js"), "utf8");

async function suite(mod, etiket, ham) {
  const hata = [];
  const not = (s) => { ham.push("    " + s); };

  // ---- (a) REGRESYON: konfigur urunu KONFIGURLAR'da VARKEN fiyat degismemeli
  const denemeler = [[150, "PLA"], [300, "ASA"], [60, "PLA"]];
  let aSayac = 0;
  for (const u of KONFIGUR_URUNLER) {
    for (const [boy, malzeme] of denemeler) {
      const r = await baslat(mod, [d1Satiri(u)], { id: u.id, malzeme, renk: "Siyah", adet: 1,
                                                   parametreler: { boy_mm: boy } });
      const kat = (u.konfigur.malzemeler.find((m) => m.ad === malzeme) || {}).katsayi;
      const beklenen = FRONT.fiyatKurus(u.konfigur, FRONT.boyDuzelt(u.konfigur, boy), kat);
      if (r.kod !== 200 || r.birimKurus !== beklenen) {
        hata.push("(a) " + u.id + " " + boy + "mm/" + malzeme + ": kod=" + r.kod +
                  " birim=" + r.birimKurus + " (beklenen " + beklenen + ")");
      } else { aSayac += 1; }
    }
  }
  not("(a) regresyon: " + aSayac + "/" + (KONFIGUR_URUNLER.length * denemeler.length) +
      " konfigur kalemi orakille BIREBIR (13 urun x 150/PLA,300/ASA,60/PLA)");

  // ---- (b) PARA KANITI: D1'de var, KONFIGURLAR'da YOK
  const bVaka = [[60, "PLA", 50000], [150, "PLA", 73600], [300, "PLA", 150000],
                 [300, "ASA", 150000]];
  const bSatir = [];
  for (const [boy, malzeme, konfigurFiyat] of bVaka) {
    const r = await baslat(mod, [YENI_KONFIGUR], { id: YENI_KONFIGUR.id, malzeme,
                                                   renk: "Siyah", adet: 1,
                                                   parametreler: { boy_mm: boy } });
    const sabit = SECENEK.satirOzeti(
      { kategori: YENI_KONFIGUR.kategori, fiyat: YENI_KONFIGUR.fiyat, parametrik: false,
        boy_secenekleri: [] },
      { id: YENI_KONFIGUR.id, malzeme, renk: "Siyah", renk_ozel: "", boy_etiket: null,
        adet: 1 }).birimKurus;
    const eksik = konfigurFiyat - sabit;
    bSatir.push(boy + "mm/" + malzeme + " -> kod=" + r.kod + " hata=" +
                (r.govde.hata || "-") + " tahsilat=" + (r.birimKurus == null ? "YOK" : r.birimKurus) +
                " (sabit kol " + sabit + ", konfigur " + konfigurFiyat + ", sessiz eksik " +
                eksik + " kurus)");
    if (r.kod !== 400 || r.govde.hata !== "konfigur-urun") {
      hata.push("(b) " + boy + "mm/" + malzeme + ": " + r.kod + "/" + (r.govde.hata || "-") +
                " (400 konfigur-urun olmali)");
    }
    if (r.birimKurus !== null) { hata.push("(b) SABIT FIYAT HESAPLANDI: " + r.birimKurus); }
    if (r.d1Yazildi) { hata.push("(b) D1'e siparis satiri YAZILDI"); }
    if (r.iyzicoAcildi) { hata.push("(b) iyzico oturumu ACILDI"); }
  }
  bSatir.forEach((s) => not("(b) " + s));

  // ---- (c) YANLIS-POZITIF: konfigursuz genis orneklem 400 yememeli
  const aday = URUNLER.filter((u) => !u.konfigur && !u.parametrik && u.fiyat &&
                                     /[0-9]/.test(String(u.fiyat)));
  const adim = Math.max(1, Math.floor(aday.length / 250));
  const ornek = [];
  for (let i = 0; i < aday.length && ornek.length < 250; i += adim) { ornek.push(aday[i]); }
  let cOk = 0, cYanlis = 0, c200 = 0;
  for (const u of ornek) {
    const r = await baslat(mod, [d1Satiri(u)], { id: u.id, malzeme: "PLA", renk: "Siyah", adet: 1 });
    if (r.govde && r.govde.hata === "konfigur-urun") {
      cYanlis += 1;
      if (cYanlis <= 3) { hata.push("(c) YANLIS-POZITIF: " + u.id + " (" + u.kategori + ")"); }
    } else { cOk += 1; }
    if (r.kod === 200) { c200 += 1; }
  }
  if (cYanlis > 0) { hata.push("(c) toplam yanlis-pozitif: " + cYanlis + "/" + ornek.length); }
  not("(c) yanlis-pozitif: " + ornek.length + " konfigursuz urun denendi -> " + cYanlis +
      " tanesi 'konfigur-urun' yedi (" + c200 + " tanesi 200 ile odenebilir kaldi)");

  // ---- (d) FAZ 4 KAZANIMI: D1'de konfigur VAR, bundle'da YOK -> ARTIK DOGRU FIYATLANIR.
  // (b)'deki pencerenin kapandigi hal: urun urunler.json'a girdi, d1-sync onu D1'e yazdi,
  // Worker artefakti HENUZ deploy edilmedi. FAZ 3'e kadar bu kalem 400 aliyordu (satis
  // kaybi); artik sema D1'den okundugu icin dogru kuruslu 200 doner.
  const kaynakKonf = KONFIGUR_URUNLER[0].konfigur;
  const dSatir = Object.assign({}, YENI_KONFIGUR, { konfigur: kanonik(kaynakKonf) });
  let dSayac = 0;
  for (const [boy, malzeme] of denemeler) {
    const r = await baslat(mod, [dSatir], { id: YENI_KONFIGUR.id, malzeme, renk: "Siyah",
                                            adet: 1, parametreler: { boy_mm: boy } });
    const kat = (kaynakKonf.malzemeler.find((m) => m.ad === malzeme) || {}).katsayi;
    const beklenen = FRONT.fiyatKurus(kaynakKonf, FRONT.boyDuzelt(kaynakKonf, boy), kat);
    if (r.kod !== 200 || r.birimKurus !== beklenen) {
      hata.push("(d) bundle'da OLMAYAN konfigur urunu " + boy + "mm/" + malzeme +
                ": kod=" + r.kod + " birim=" + r.birimKurus + " (beklenen 200/" + beklenen + ")");
    } else { dSayac += 1; }
  }
  not("(d) D1'de VAR / bundle'da YOK: " + dSayac + "/" + denemeler.length +
      " kalem D1 semasiyla DOGRU fiyatlandi (deploy penceresi kapandi)");

  // ---- (e) FAIL-CLOSED (F4'un asil riski): D1 kaydi YOK/BOS/BOZUK iken bundle'a ya da SABIT
  // katalog fiyatina DUSULMEMELI. Uc negatif vaka da 400 + tahsilat YOK olmali; 0 TL / bedava
  // siparis ASLA. Bundle bu urunleri BILIYOR -> "sessiz varsayilan" tam burada olurdu.
  const eVakalar = [["D1 konfigur BOS", ""], ["D1 metni BOZUK JSON", "{bozuk"],
                    ["D1 metni JSON ama DIZI", "[1,2]"]];
  const eKaynak = KONFIGUR_URUNLER[0];
  const eSabit = SECENEK.satirOzeti(
    { kategori: eKaynak.kategori, fiyat: eKaynak.fiyat, parametrik: false,
      boy_secenekleri: [] },
    { id: eKaynak.id, malzeme: "PLA", renk: "Siyah", renk_ozel: "", boy_etiket: null,
      adet: 1 }).birimKurus;
  for (const [ad, metin] of eVakalar) {
    const r = await baslat(mod, [d1Satiri(eKaynak, metin)],
                           { id: eKaynak.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                             parametreler: { boy_mm: 300 } });
    not("(e) " + ad + " -> kod=" + r.kod + " hata=" + (r.govde.hata || "-") +
        " tahsilat=" + (r.birimKurus == null ? "YOK" : r.birimKurus) +
        " (sabit kol olsaydi " + eSabit + ", D1 semasi 150000)");
    if (r.kod !== 400 || r.govde.hata !== "konfigur-urun") {
      hata.push("(e) " + ad + ": " + r.kod + "/" + (r.govde.hata || "-") +
                " (400 konfigur-urun olmali)");
    }
    if (r.birimKurus !== null) { hata.push("(e) " + ad + ": TAHSILAT HESAPLANDI " + r.birimKurus); }
    if (r.d1Yazildi) { hata.push("(e) " + ad + ": D1'e siparis satiri YAZILDI"); }
    if (r.iyzicoAcildi) { hata.push("(e) " + ad + ": iyzico oturumu ACILDI"); }
  }

  return { hata, aSayac, ornekSayisi: ornek.length, cYanlis, cOk, dSayac,
           eVaka: eVakalar.length };
}

// ---------------------------------------------------------------- kosum

const ham = [];
let kirmizi = 0;

let setSayisi = 0;
function baslik(s) { setSayisi += 1; ham.push(s); }

// Kosum ortami CIKTIYA yazilir: CI (deploy.yml node-version 20) ile yerel Node farki bu
// testte bir kez CI'yi kirmiziya cakti (module.registerHooks) — surum log'dan gorunsun.
ham.push("Node: " + process.version + " (CI tabani: 20.x — daha yeni API KULLANMA)");

// 1) GERCEK kaynak — hepsi yesil olmali.
baslik("== 1) GERCEK shop/src/index.js ==");
const gercekMod = await indexYukle(KAYNAK);
const gercek = await suite(gercekMod, "gercek", ham);
if (gercek.hata.length) {
  kirmizi += 1;
  gercek.hata.forEach((h) => ham.push("    ❌ " + h));
  ham.push("  ❌ KALDI — gercek kaynak");
} else {
  ham.push("  ✅ GECTI — gercek kaynak (a+b+c)");
}

// 2) TAHMIN KAPSAMI: konfigurBeklenirMi TUM katalogda konfigur urunleriyle birebir mi?
// Baslikta katalog boyutu CANLI okunur — sabit sayi yazilirsa katalog buyudukce bayatlar.
baslik("== 2) konfigurBeklenirMi kapsami (" + URUNLER.length + " urunluk katalog taramasi) ==");
const KB = await import(pathToFileURL(path.join(SHOP, "src", "konfigur-beklenen.js")).href);
const tahminEvet = URUNLER.filter((u) => KB.konfigurBeklenirMi(u));
const konfigurluIdler = new Set(KONFIGUR_URUNLER.map((u) => u.id));
const fazla = tahminEvet.filter((u) => !konfigurluIdler.has(u.id));
const eksik = KONFIGUR_URUNLER.filter((u) => !KB.konfigurBeklenirMi(u));
ham.push("    katalog=" + URUNLER.length + " urun; konfigur alanli=" + KONFIGUR_URUNLER.length +
         "; tahmin 'konfigur beklenir'=" + tahminEvet.length +
         "; fazla(yanlis-pozitif)=" + fazla.length + "; eksik(yanlis-negatif)=" + eksik.length);
if (fazla.length || eksik.length) {
  kirmizi += 1;
  ham.push("    ❌ fazla: " + fazla.map((u) => u.id).join(",") +
           " | eksik: " + eksik.map((u) => u.id).join(","));
  ham.push("  ❌ KALDI — tahmin kapsami");
} else {
  ham.push("  ✅ GECTI — tahmin kapsami 13/13 birebir, 0 yanlis-pozitif");
}

// 3) ESKI KOD (git HEAD) — kapatilan delik SAYIYLA belgelenir (bilgi amacli; (b) kirmizi OLMALI).
baslik("== 3) ESKI kod (git HEAD:shop/src/index.js) — kapatilan delik ==");
let eskiKaynak = null;
try {
  eskiKaynak = execFileSync("git", ["-C", KOK, "show", "HEAD:shop/src/index.js"],
                            { encoding: "utf8" });
} catch (e) { ham.push("    ÖLÇÜLEMEDİ: git show basarisiz (" + e.message + ")"); }
if (eskiKaynak && !/konfigurBeklenirMi/.test(eskiKaynak)) {
  const eskiMod = await indexYukle(eskiKaynak);
  const eski = await suite(eskiMod, "eski", ham);
  const bHata = eski.hata.filter((h) => h.startsWith("(b)"));
  const aHata = eski.hata.filter((h) => h.startsWith("(a)"));
  ham.push("    eski kodda (a) regresyon hatasi=" + aHata.length +
           " (0 olmali: fiyat DEGISMEDI), (b) hatasi=" + bHata.length + " (>0 olmali: delik)");
  if (aHata.length) {
    kirmizi += 1;
    aHata.forEach((h) => ham.push("    ❌ ESKI==YENI DEGIL: " + h));
    ham.push("  ❌ KALDI — regresyon (eski != yeni)");
  } else if (!bHata.length) {
    kirmizi += 1;
    ham.push("  ❌ KALDI — eski kodda delik GORULMEDI (test (b)'yi kilitlemiyor)");
  } else {
    ham.push("  ✅ GECTI — eski kod (a) AYNI fiyati uretti, (b)'de sessiz sabit fiyata dustu");
  }
} else if (eskiKaynak) {
  ham.push("    ÖLÇÜLEMEDİ: HEAD zaten kapiyi iceriyor (dal merge edilmis olabilir)");
}

// 4) VAKUM (mutasyon): kapi SILINIRSE (b) KIRMIZI yanmali.
baslik("== 4) VAKUM TESTI — kapi silindiginde test KIRMIZI yanmali ==");
// FAZ 4'ten beri kapi bir `else if` DALI degil, `konfigurluMu` sinyalinin BIR TERIMI:
// terim silinirse D1'de konfiguru olmayan + bundle'in tanimadigi seri urunu SABIT FIYAT
// koluna duser (tam olarak (b)'nin olctugu sessiz eksik tahsilat).
const DESEN = / \|\| konfigurBeklenirMi\(u\)/;
if (!DESEN.test(KAYNAK)) {
  kirmizi += 1;
  ham.push("    ❌ MUTASYON UYGULANAMADI — kapi deseni index.js'te bulunamadi.");
  ham.push("       (Kapi yeniden yazildiysa bu desen guncellenmeli; mutasyon testi OLU kalamaz.)");
} else {
  const mutant = KAYNAK.replace(DESEN, "");
  if (/konfigurBeklenirMi\(u\)/.test(mutant)) {
    kirmizi += 1;
    ham.push("    ❌ mutant hala kapiyi iceriyor (desen eksik kesti)");
  } else {
    const mutantMod = await indexYukle(mutant);
    const m = await suite(mutantMod, "mutant", ham);
    const bHata = m.hata.filter((h) => h.startsWith("(b)"));
    const digerHata = m.hata.filter((h) => !h.startsWith("(b)"));
    ham.push("    mutant sonucu: (b) hatasi=" + bHata.length + " (>0 olmali), " +
             "(a)+(c) hatasi=" + digerHata.length + " (0 olmali)");
    bHata.forEach((h) => ham.push("    · mutantta yakalanan: " + h));
    if (!bHata.length) {
      kirmizi += 1;
      ham.push("  ❌ KALDI — VAKUM: kapi silindi ama test YESIL kaldi (OLU NOBETCI)");
    } else if (digerHata.length) {
      kirmizi += 1;
      digerHata.forEach((h) => ham.push("    ❌ " + h));
      ham.push("  ❌ KALDI — VAKUM: mutant (a)/(c)'yi de bozdu (test cok genis)");
    } else {
      ham.push("  ✅ GECTI — VAKUM: kapi silininde YALNIZ (b) kirmizi yandi");
    }
  }
}

// 5) MUSTERI METNI: worker'in DONDURDUGU hata kodu, front'ta jenerik olmayan DOGRU metne
//    dusuyor mu? Kod adi iki taraftan birinde degisirse burasi kirmizi yanar (uctan uca capa).
baslik("== 5) MUSTERI METNI — index.html HATA_METNI (D-1 borcu) ==");
const HTML = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
// Marka kurallari (CLAUDE.md): pazarlama/musteri metninde "3D baski" ailesi ve SEHIR ADI GECMEZ.
const YASAK_MARKA = /bask[ıi]|bas[ıi]m|bas[ıi]lan|bas[ıi]l|3\s*-?\s*[dD]\b|üç boyut|uc boyut/;
const YASAK_SEHIR = /[Ff]ethiye|[GgĞğ]öcek|[Gg]ocek|[Mm]uğla|[Mm]ugla/;

/** index.html'deki GERCEK HATA_METNI sozlugunu (kopya degil, dosyanin kendisi) cozer. */
function hataSozlugu(html) {
  const m = html.match(/var HATA_METNI = \{[\s\S]*?\n  \};/);
  return m ? vm.runInNewContext(m[0] + "\nHATA_METNI;") : null;
}
/** index.html'deki GERCEK jenerik yedek metni (odemeHata cagrisindaki `||` sagi). */
function jenerikMetin(html) {
  const m = html.match(/odemeHata\(HATA_METNI\[veri\.hata\] \|\| "([^"]+)"\)/);
  return m ? m[1] : null;
}

const sozluk = hataSozlugu(HTML);
const jenerik = jenerikMetin(HTML);
if (!sozluk || !jenerik) {
  kirmizi += 1;
  ham.push("    ❌ index.html'de HATA_METNI sozlugu / jenerik yedek ayiklanamadi " +
           "(sozluk=" + Boolean(sozluk) + " jenerik=" + Boolean(jenerik) + ")");
} else {
  // Hata kodu UYDURULMAZ: gercek worker kodundan (b) senaryosuyla alinir.
  const wr = await baslat(gercekMod, [YENI_KONFIGUR],
    { id: YENI_KONFIGUR.id, malzeme: "PLA", renk: "Siyah", adet: 1,
      parametreler: { boy_mm: 300 } });
  const kod = wr.govde.hata;
  const gosterilen = sozluk[kod] || jenerik;
  ham.push("    worker kodu: " + kod + " (HTTP " + wr.kod + ")");
  ham.push("    jenerik yedek: \"" + jenerik + "\"");
  ham.push("    musteriye gosterilen: \"" + gosterilen + "\"");
  const m5 = [];
  if (!Object.prototype.hasOwnProperty.call(sozluk, kod)) {
    m5.push("HATA_METNI'nde '" + kod + "' anahtari YOK");
  }
  if (gosterilen === jenerik) { m5.push("jenerik metne dusuyor (yanlis: 'odeme basarisiz' izlenimi)"); }
  if (!/WhatsApp/.test(gosterilen)) { m5.push("metin musteriye ne yapacagini soylemiyor (WhatsApp yok)"); }
  if (YASAK_MARKA.test(gosterilen)) { m5.push("MARKA IHLALI: baski/basim/3D ailesinden kelime var"); }
  if (YASAK_SEHIR.test(gosterilen)) { m5.push("MARKA IHLALI: sehir adi geciyor"); }
  ham.push("    marka taramasi: baski/basim/3D=" + (YASAK_MARKA.test(gosterilen) ? "VAR" : "YOK") +
           ", sehir=" + (YASAK_SEHIR.test(gosterilen) ? "VAR" : "YOK") +
           ", WhatsApp yonlendirmesi=" + (/WhatsApp/.test(gosterilen) ? "VAR" : "YOK"));

  // VAKUM: girdiyi index.html kaynagindan SIL -> jenerik metne dusmeli (iddia KIRMIZI).
  const mutantHtml = HTML.replace(/\n\s*"konfigur-urun": "[^"]*",/, "");
  const mutantSozluk = hataSozlugu(mutantHtml);
  const mutantGosterilen = (mutantSozluk && mutantSozluk[kod]) || jenerik;
  const mutasyonOldu = mutantHtml !== HTML && mutantSozluk &&
                       !Object.prototype.hasOwnProperty.call(mutantSozluk, kod);
  ham.push("    VAKUM (girdi silindi): \"" + mutantGosterilen + "\"");
  if (!mutasyonOldu) { m5.push("VAKUM uygulanamadi (girdi deseni tutmadi)"); }
  else if (mutantGosterilen !== jenerik) { m5.push("VAKUM: girdi silindi ama metin degismedi (OLU IDDIA)"); }

  if (m5.length) {
    kirmizi += 1;
    m5.forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — musteri metni");
  } else {
    ham.push("  ✅ GECTI — musteri metni dogru + marka-temiz; girdi silinince VAKUM kirmizi yaniyor");
  }
}

console.log(ham.join("\n"));
console.log("");
console.log(kirmizi === 0 ? "✅ HEPSI GECTI (" + setSayisi + "/" + setSayisi + " set)"
                          : "❌ " + kirmizi + "/" + setSayisi + " set KALDI");
process.exit(kirmizi === 0 ? 0 : 1);
