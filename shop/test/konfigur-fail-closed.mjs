#!/usr/bin/env node
/**
 * KONFIGUR FAIL-CLOSED KABUL TESTI — "D1'de var, Worker bundle'inda yok" penceresinde
 * SESSIZ EKSIK TAHSILAT olmadigini kanitlar.
 *
 *   node shop/test/konfigur-fail-closed.mjs
 *
 * NASIL (OFFLINE — wrangler/ag/gercek odeme YOK): shop/src/index.js'in KENDISI Node'a
 * yuklenir (JSON import'lari yukleme kancasiyla "with { type: json }"a cevrilir), D1 ve
 * iyzico yerine bellek-ici sahteleri konur. Fiyat, worker'in D1'e YAZDIGI satirdan okunur —
 * yani gercek para yolundan. Hicbir dis servise istek gitmez, hicbir siparis olusmaz.
 *
 * KOSTUGU 4 SET:
 *   (a) REGRESYON — 13 konfigur urununun hepsi, KONFIGURLAR'da VARKEN: fiyat DEGISMEDI
 *       (yeni index == eski index (git HEAD) == front /konfigur.js orakili, birebir kurus).
 *   (b) PARA KANITI — urun D1'de var, KONFIGURLAR'da YOK: 400 "konfigur-urun", sabit fiyat
 *       HESAPLANMAZ, D1'e satir YAZILMAZ, iyzico oturumu ACILMAZ.
 *   (c) YANLIS-POZITIF — canli katalogdan genis konfigursuz orneklem: hicbiri "konfigur-urun"
 *       yemez (+ konfigurBeklenirMi tahmini TUM katalogda 13/13 birebir).
 *   (d) VAKUM (mutasyon) — index.js'ten kapi SILINIRSE (a)+(c) yesil kalmali ama (b) KIRMIZI
 *       yanmali. Mutant yesil kalirsa bu test OLU nobetcidir -> suite KIRMIZI.
 */

import fs from "node:fs";
import path from "node:path";
import module from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const require = createRequire(import.meta.url);

// ---------------------------------------------------------------- yukleme kancasi
// 1) Worker kaynagi bare JSON import kullanir (esbuild bunu bundle'lar); Node ise import
//    niteligi ister -> kaynak metninde "with { type: json }" eklenir. DOSYA DEGISMEZ.
// 2) Sanal URL'ler (index.js'in eski/mutant kopyalari) bellekten servis edilir; goreli
//    import'lari shop/src'e gore cozulsun diye URL yine shop/src altindadir.
const SANAL = new Map();

function jsonNiteligiEkle(kaynak) {
  return kaynak.replace(
    /(\bfrom\s+"[^"]*\.json")(\s*;)/g,
    (t, a, b) => (/\bwith\b/.test(t) ? t : a + ' with { type: "json" }' + b));
}

module.registerHooks({
  resolve(belirtec, baglam, sonraki) {
    if (SANAL.has(belirtec)) { return { url: belirtec, format: "module", shortCircuit: true }; }
    return sonraki(belirtec, baglam);
  },
  load(url, baglam, sonraki) {
    if (SANAL.has(url)) {
      return { format: "module", source: SANAL.get(url), shortCircuit: true };
    }
    // YALNIZ shop/src altindaki Worker moduleri (hepsi ESM). Depo kokundeki UMD dosyalari
    // (secenekler.js/konfigur.js) DOKUNULMADAN, Node'un kendi CJS/ESM kararina birakilir.
    if (url.startsWith("file://") && url.endsWith(".js")) {
      const yol = fileURLToPath(url);
      if (yol.startsWith(path.join(SHOP, "src") + path.sep)) {
        return { format: "module", shortCircuit: true,
                 source: jsonNiteligiEkle(fs.readFileSync(yol, "utf8")) };
      }
    }
    return sonraki(url, baglam);
  },
});

let sanalSayac = 0;
/** Verilen index.js kaynagini SANAL bir modul olarak yukler (shop/src altinda gorunur). */
async function indexYukle(kaynak) {
  sanalSayac += 1;
  const url = pathToFileURL(path.join(SHOP, "src", "__sanal-index-" + sanalSayac + ".js")).href;
  SANAL.set(url, jsonNiteligiEkle(kaynak));
  return await import(url);
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

/** urunler.json kaydindan D1 satiri (d1-sync.py'nin yazdigi alanlar). */
function d1Satiri(u) {
  return { id: u.id, baslik: u.baslik || "", kategori: u.kategori || "",
           fiyat: u.fiyat || "", parametrik: u.parametrik ? 1 : 0,
           gorsel: (u.gorseller && u.gorseller[0]) || "" };
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

  return { hata, aSayac, ornekSayisi: ornek.length, cYanlis, cOk };
}

// ---------------------------------------------------------------- kosum

const ham = [];
let kirmizi = 0;

function baslik(s) { ham.push(s); }

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
baslik("== 2) konfigurBeklenirMi kapsami (13717 urunluk katalog taramasi) ==");
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
const DESEN = /\n\s*\} else if \(konfigurBeklenirMi\(u\)\) \{[\s\S]*?\n(\s*)\} else if \(u\.parametrik\) \{/;
if (!DESEN.test(KAYNAK)) {
  kirmizi += 1;
  ham.push("    ❌ MUTASYON UYGULANAMADI — kapi deseni index.js'te bulunamadi.");
  ham.push("       (Kapi yeniden yazildiysa bu desen guncellenmeli; mutasyon testi OLU kalamaz.)");
} else {
  const mutant = KAYNAK.replace(DESEN, "\n$1} else if (u.parametrik) {");
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

console.log(ham.join("\n"));
console.log("");
console.log(kirmizi === 0 ? "✅ HEPSI GECTI (4/4 set)" : "❌ " + kirmizi + " set KALDI");
process.exit(kirmizi === 0 ? 0 : 1);
