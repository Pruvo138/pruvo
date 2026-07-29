#!/usr/bin/env node
/**
 * FIYAT ESDEGERLIGI + PROVA (yan etkisiz fiyat sorgusu) KABUL TESTI.
 *
 *   node shop/test/fiyat-prova.mjs
 *
 * NE KANITLAR:
 *   1) ESDEGERLIK — konfigur aynasi (elle bakimli konfigurlar.js) URETILMIS artefakta
 *      cevrildi ve fiyat hesabi sepetiFiyatla()'ya cikarildi. ESKI kod (git HEAD: eski index
 *      + ELLE yazilmis ayna) ile YENI kod (yeni index + URETILMIS artefakt) 14 konfigur
 *      urununun 6 kombinasyonunda AYNI kurusu uretmeli — FARK 0.
 *   2) TAVAN — 3x tavan (150000 kurus) hala uygulaniyor (kapaksiz formul asiyor, sonuc kirpik).
 *   3) PROVA == TAHSILAT — /fiyat ucu, /baslat'in D1'e YAZDIGI tutarin AYNISINI doner.
 *   4) PROVA YAN ETKISIZ — YAPISAL kanit: D1 `run()` (yazma) sayaci ve global `fetch`
 *      (iyzico/Telegram/e-posta) sayaci prova cagrilarinda 0; ayni kosumda /baslat cagrisi
 *      ikisini de ARTIRIYOR (sayaclarin OLU olmadigi kaniti).
 *   5) PROVA SIZINTI YUZEYI — cevap beyaz-liste; katalog ic alanlari (baslik/kategori/gorsel),
 *      uretim verisi (hacim_mm3), siparis no / IBAN / token DONMEZ.
 *   6) PROVA FAIL-CLOSED — artefaktta olmayan konfigur urunu provada da 400 (sabit fiyata
 *      DUSMEZ); /baslat ile AYNI davranis.
 *   7) 4 KIRMIZI-MUTASYON (M1..M4) — bkz. asagidaki set 7.
 *
 * OFFLINE: ag YOK (fetch sahtelenir; beklenmeyen adres HATA), D1 sahte, hicbir siparis
 * olusmaz, depo dosyasi DEGISMEZ (gecici dizinler kosum sonunda silinir).
 *
 * NODE 20 (CI runner tabani): module.registerHooks (Node 22+) KULLANILMAZ. Worker kaynaklari
 * shop/ ALTINDA AYNI DERINLIKTE gecici dizinlere yazilir (goreli ../../secenekler.js aynen
 * cozulur), JSON import satirlari icerige gomulur.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const SRC = path.join(SHOP, "src");
const require = createRequire(import.meta.url);

// ------------------------------------------------------------------ yukleyici
const TEMP_ONEK = "src-fiyat-tmp-";

function tempSupur() {
  for (const ad of fs.readdirSync(SHOP)) {
    if (ad.startsWith(TEMP_ONEK)) {
      fs.rmSync(path.join(SHOP, ad), { recursive: true, force: true });
    }
  }
}

/** `import X from "...json";` -> `const X = <json icerigi>;` (Node surumunden bagimsiz). */
function jsonGom(kaynak, kaynakDizin, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(kaynakDizin, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ") — desen guncellenmeli");
  }
  return cikti;
}

const dizinler = [];
/** Verilen {dosyaAdi: kaynak} haritasini shop/ altinda gecici bir dizine yazar, yolu doner. */
function dizinKur(etiket, dosyalar) {
  const yol = path.join(SHOP, TEMP_ONEK + etiket + "-" + process.pid);
  fs.rmSync(yol, { recursive: true, force: true });
  fs.mkdirSync(yol, { recursive: true });
  for (const [ad, kaynak] of Object.entries(dosyalar)) {
    fs.writeFileSync(path.join(yol, ad), jsonGom(kaynak, SRC, etiket + "/" + ad));
  }
  dizinler.push(yol);
  return yol;
}

tempSupur();
process.on("exit", () => {
  for (const d of dizinler) { fs.rmSync(d, { recursive: true, force: true }); }
});

function guncelKaynaklar() {
  const d = {};
  for (const ad of fs.readdirSync(SRC)) {
    if (ad.endsWith(".js")) { d[ad] = fs.readFileSync(path.join(SRC, ad), "utf8"); }
  }
  return d;
}

function headKaynaklari() {
  const liste = execFileSync("git", ["-C", KOK, "ls-tree", "--name-only", "HEAD", "shop/src/"],
                             { encoding: "utf8" }).trim().split("\n");
  const d = {};
  for (const yol of liste) {
    if (!yol.endsWith(".js")) { continue; }
    d[path.basename(yol)] = execFileSync("git", ["-C", KOK, "show", "HEAD:" + yol],
                                         { encoding: "utf8" });
  }
  return d;
}

let sayac = 0;
async function modulYukle(dizin) {
  sayac += 1;
  // Cache-buster: ayni dosya adiyla ikinci kez import edilirse Node onbellekten donerdi.
  return await import(pathToFileURL(path.join(dizin, "index.js")).href + "?s=" + sayac);
}

// ------------------------------------------------------------------ sahte cevre
const ag = { iyzico: 0, telegram: 0, diger: 0, toplam: 0 };
globalThis.fetch = async function sahteFetch(hedef) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  ag.toplam += 1;
  if (u.includes("iyzico.test")) {
    ag.iyzico += 1;
    return new Response(JSON.stringify({
      status: "success", token: "test-token-" + ag.iyzico,
      paymentPageUrl: "https://odeme.test/sayfa",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  if (u.includes("telegram")) {
    ag.telegram += 1;
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  }
  ag.diger += 1;
  return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
};

function d1Sahte(satirlar, sayaclar) {
  const harita = new Map(satirlar.map((u) => [u.id, u]));
  return {
    prepare(sql) {
      return {
        bind(...arg) {
          return {
            async all() {
              sayaclar.select += 1;
              return { results: arg.map((id) => harita.get(id)).filter(Boolean) };
            },
            async first() { sayaclar.first += 1; return null; },
            async run() {
              sayaclar.run += 1;
              sayaclar.yazilan.push({ sql, arg });
              return { meta: { changes: 1 } };
            },
          };
        },
      };
    },
  };
}

const ENV_TABAN = {
  SITE_URL: "https://pruvo3d.com",
  IYZICO_BASE_URL: "https://iyzico.test",
  IYZICO_API_KEY: "test-api-key",
  IYZICO_SECRET_KEY: "test-secret-key",
  TELEGRAM_TOKEN: "test-telegram-token",
  TELEGRAM_CHAT: "1",
  TELEGRAM_API: "https://telegram.test",
};

function yeniSayac() { return { select: 0, first: 0, run: 0, yazilan: [] }; }

const MUSTERI = { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
                  adres: "Test mahallesi test sokak no 1", sehir: "Mugla" };

/** /baslat — GERCEK worker kodundan; cevabi + D1'e yazilan satiri + sayaclari dondurur. */
async function baslat(mod, d1Satirlari, sepet) {
  const sayaclar = yeniSayac();
  const agOnce = ag.toplam;
  const env = Object.assign({}, ENV_TABAN, { KATALOG: d1Sahte(d1Satirlari, sayaclar) });
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sozlesme_onay: true, odeme: "kart", musteri: MUSTERI, sepet }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  const insert = sayaclar.yazilan.find((k) => /INSERT INTO siparisler/.test(k.sql));
  let satir = null, tutarKurus = null;
  if (insert) {
    const dizi = insert.arg.find((x) => typeof x === "string" && x.startsWith("["));
    satir = dizi ? JSON.parse(dizi)[0] : null;
    tutarKurus = insert.arg.find((x) => typeof x === "number" && x > 0) ?? null;
  }
  return { kod: cevap.status, govde, satir, birimKurus: satir ? satir.birim_kurus : null,
           tutarKurus, d1Yazma: sayaclar.run, agCagri: ag.toplam - agOnce, sayaclar };
}

let ipSayaci = 0;
/** /fiyat (prova) — GERCEK worker kodundan; cevabi + sayaclari dondurur. */
async function prova(mod, d1Satirlari, sepet, sabitIp) {
  const sayaclar = yeniSayac();
  const agOnce = ag.toplam;
  const env = Object.assign({}, ENV_TABAN, { KATALOG: d1Sahte(d1Satirlari, sayaclar) });
  ipSayaci += 1;
  const ip = sabitIp || ("10." + Math.floor(ipSayaci / 65536) % 256 + "." +
                         Math.floor(ipSayaci / 256) % 256 + "." + (ipSayaci % 256));
  const istek = new Request("https://pruvo3d.com/api/shop/fiyat", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": ip },
    body: JSON.stringify({ sepet }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  let hamMetin = "";
  try { hamMetin = await cevap.clone().text(); govde = JSON.parse(hamMetin); } catch (e) { govde = {}; }
  return { kod: cevap.status, govde, ham: hamMetin, d1Yazma: sayaclar.run,
           d1Okuma: sayaclar.select, d1First: sayaclar.first,
           agCagri: ag.toplam - agOnce, sayaclar };
}

// ------------------------------------------------------------------ veri
require(path.join(KOK, "secenekler.js"));
const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi"); }
const FRONT = require(path.join(KOK, "konfigur.js"));

const URUNLER = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));
const KONFIGUR_URUNLER = URUNLER.filter((u) => u.konfigur);

function d1Satiri(u) {
  return { id: u.id, baslik: u.baslik || "", kategori: u.kategori || "",
           fiyat: u.fiyat || "", parametrik: u.parametrik ? 1 : 0,
           gorsel: (u.gorseller && u.gorseller[0]) || "" };
}

// Artefaktta OLMAYAN konfigur urunu (D1'e girmis, Worker deploy edilmemis penceresi).
const YENI_KONFIGUR = { id: "ejderha-serit-dekoratif-figur", baslik: "Ejderha Heykeli — Şerit",
                        kategori: "Skan Art", fiyat: "500 TL", parametrik: 0, gorsel: "" };

// 6 kombinasyon (boy mm / malzeme) — aralik ucu + orta + tavan bolgesi.
const KOMBIN = [[60, "PLA"], [150, "PLA"], [150, "PETG"], [220, "PETG"], [300, "PLA"],
                [300, "ASA"]];

const ham = [];
let kirmizi = 0;
let setSayisi = 0;
function baslik(s) { setSayisi += 1; ham.push(""); ham.push(s); }
function not(s) { ham.push("    " + s); }

ham.push("Node: " + process.version + " (CI tabani: 20.x — daha yeni API KULLANMA)");

const YENI_DIZIN = dizinKur("yeni", guncelKaynaklar());
const YENI = await modulYukle(YENI_DIZIN);

// =================================================================== 1) ESDEGERLIK
baslik("== 1) FIYAT ESDEGERLIGI — ESKI (git HEAD: elle ayna) vs YENI (uretilmis artefakt) ==");
let eskiMod = null;
try {
  eskiMod = await modulYukle(dizinKur("eski", headKaynaklari()));
} catch (e) {
  kirmizi += 1;
  not("❌ ÖLÇÜLEMEDİ: HEAD kaynaklari yuklenemedi — " + e.message);
}
if (eskiMod) {
  const basliklar = KOMBIN.map(([b, m]) => b + "/" + m);
  not("urun".padEnd(42) + basliklar.map((s) => s.padStart(9)).join("") + "     fark");
  let farkToplam = 0, olcum = 0;
  for (const u of KONFIGUR_URUNLER) {
    const hucre = [];
    let fark = 0;
    for (const [boy, malzeme] of KOMBIN) {
      const kalem = { id: u.id, malzeme, renk: "Siyah", adet: 1, parametreler: { boy_mm: boy } };
      const e = await baslat(eskiMod, [d1Satiri(u)], [kalem]);
      const y = await baslat(YENI, [d1Satiri(u)], [kalem]);
      olcum += 1;
      if (e.birimKurus !== y.birimKurus || e.kod !== y.kod) {
        fark += 1; farkToplam += 1;
        ham.push("    ❌ " + u.id + " " + boy + "/" + malzeme + ": eski=" + e.birimKurus +
                 "(" + e.kod + ") yeni=" + y.birimKurus + "(" + y.kod + ")");
      }
      hucre.push(String(y.birimKurus));
    }
    not(u.id.padEnd(42) + hucre.map((s) => s.padStart(9)).join("") + fark.toString().padStart(9));
  }
  not("olculen kombinasyon: " + olcum + " (14 urun x 6) — TOPLAM FARK: " + farkToplam);
  if (farkToplam !== 0) { kirmizi += 1; ham.push("  ❌ KALDI — fiyat esdegerligi"); }
  else { ham.push("  ✅ GECTI — eski ve yeni kod BIREBIR ayni kurusu uretti (fark 0)"); }
}

// =================================================================== 2) TAVAN
baslik("== 2) 3x TAVAN (shop/src/konfigur.js:59 — 3 x fiyatCapalari[0][1]) hala uygulaniyor ==");
{
  const hatalar = [];
  let tavanVuran = 0;
  for (const u of KONFIGUR_URUNLER) {
    const kf = u.konfigur;
    const tavan = 3 * kf.fiyatCapalari[0][1] * 100;
    const kat = (kf.malzemeler.find((m) => m.ad === "ASA") || {}).katsayi;
    const m = FRONT.fiyatModeli(kf);
    const kapaksizTl = (m.sabit + m.birim * (FRONT.hacimMm3(kf, 300) / 1000)) * kat;
    const r = await baslat(YENI, [d1Satiri(u)],
      [{ id: u.id, malzeme: "ASA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 300 } }]);
    if (Math.round(kapaksizTl) * 100 <= tavan) {
      hatalar.push(u.id + ": kapaksiz fiyat tavani ASMIYOR (test anlamsiz)");
    }
    if (r.birimKurus !== tavan) {
      hatalar.push(u.id + ": 300mm/ASA = " + r.birimKurus + " != tavan " + tavan);
    } else { tavanVuran += 1; }
  }
  not("300mm/ASA'da tavana kirpilan urun: " + tavanVuran + "/" + KONFIGUR_URUNLER.length +
      " (tavan = 3 x 500 TL = 150000 kurus)");
  if (hatalar.length) {
    kirmizi += 1;
    hatalar.slice(0, 5).forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — tavan");
  } else { ham.push("  ✅ GECTI — tavan 14/14 urunde uygulaniyor"); }
}

// =================================================================== 3) PROVA == TAHSILAT
baslik("== 3) PROVA == TAHSILAT — /fiyat, /baslat'in D1'e YAZDIGI tutarin AYNISINI doner ==");
{
  const hatalar = [];
  let olcum = 0;
  for (const u of KONFIGUR_URUNLER) {
    for (const [boy, malzeme] of KOMBIN) {
      const kalem = { id: u.id, malzeme, renk: "Siyah", adet: 1, parametreler: { boy_mm: boy } };
      const b = await baslat(YENI, [d1Satiri(u)], [kalem]);
      const p = await prova(YENI, [d1Satiri(u)], [kalem]);
      olcum += 1;
      const pb = p.govde.satirlar && p.govde.satirlar[0] ? p.govde.satirlar[0].birim_kurus : null;
      const beklenenTahsilat = b.tutarKurus + SECENEK.kargoKurus(b.tutarKurus);
      if (p.kod !== 200 || pb !== b.birimKurus) {
        hatalar.push(u.id + " " + boy + "/" + malzeme + ": prova=" + pb + "(" + p.kod +
                     ") baslat=" + b.birimKurus);
      }
      if (p.govde.tahsilat_kurus !== beklenenTahsilat) {
        hatalar.push(u.id + " " + boy + "/" + malzeme + ": prova tahsilat=" +
                     p.govde.tahsilat_kurus + " != " + beklenenTahsilat);
      }
    }
  }
  // Sabit fiyatli urunlerden orneklem (konfigur DISI kol da provada birebir mi).
  const sabitAday = URUNLER.filter((u) => !u.konfigur && !u.parametrik && u.fiyat &&
                                          /[0-9]/.test(String(u.fiyat)));
  const adim = Math.max(1, Math.floor(sabitAday.length / 40));
  let sabitOlcum = 0;
  for (let i = 0; i < sabitAday.length && sabitOlcum < 40; i += adim) {
    const u = sabitAday[i];
    const kalem = { id: u.id, malzeme: "PETG", renk: "Siyah", adet: 3 };
    const b = await baslat(YENI, [d1Satiri(u)], [kalem]);
    const p = await prova(YENI, [d1Satiri(u)], [kalem]);
    sabitOlcum += 1;
    const pb = p.govde.satirlar && p.govde.satirlar[0] ? p.govde.satirlar[0].birim_kurus : null;
    if (b.kod !== 200 || p.kod !== 200 || pb !== b.birimKurus ||
        p.govde.urun_kurus !== b.tutarKurus) {
      hatalar.push("sabit " + u.id + ": baslat=" + b.birimKurus + "/" + b.tutarKurus +
                   " prova=" + pb + "/" + p.govde.urun_kurus);
    }
  }
  not("konfigur kombinasyonu: " + olcum + "; sabit-fiyatli orneklem: " + sabitOlcum +
      "; uyusmazlik: " + hatalar.length);
  if (hatalar.length) {
    kirmizi += 1;
    hatalar.slice(0, 5).forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — prova/tahsilat esitligi");
  } else { ham.push("  ✅ GECTI — prova tutari tahsilat tutariyla BIREBIR"); }
}

// =================================================================== 4) YAN ETKISIZLIK
baslik("== 4) PROVA YAN ETKISIZ — D1 yazma + ag cagri SAYACLARI (yapisal kanit) ==");
{
  const hatalar = [];
  let toplamYazma = 0, toplamAg = 0, toplamOkuma = 0, toplamFirst = 0;
  const vaka = [
    ["konfigur 300/ASA", [d1Satiri(KONFIGUR_URUNLER[0])],
     [{ id: KONFIGUR_URUNLER[0].id, malzeme: "ASA", renk: "Siyah", adet: 2,
        parametreler: { boy_mm: 300 } }]],
    ["konfigur 60/PLA", [d1Satiri(KONFIGUR_URUNLER[1])],
     [{ id: KONFIGUR_URUNLER[1].id, malzeme: "PLA", renk: "Siyah", adet: 1,
        parametreler: { boy_mm: 60 } }]],
    ["sabit fiyatli", [d1Satiri(URUNLER.find((u) => !u.konfigur && !u.parametrik && u.fiyat &&
                                                   /[0-9]/.test(String(u.fiyat))))],
     [{ id: URUNLER.find((u) => !u.konfigur && !u.parametrik && u.fiyat &&
                                /[0-9]/.test(String(u.fiyat))).id,
        malzeme: "PLA", renk: "Siyah", adet: 1 }]],
    ["artefaktta YOK (fail-closed)", [YENI_KONFIGUR],
     [{ id: YENI_KONFIGUR.id, malzeme: "PLA", renk: "Siyah", adet: 1,
        parametreler: { boy_mm: 300 } }]],
    ["bilinmeyen urun", [], [{ id: "olmayan-urun-xyz", malzeme: "PLA", renk: "Siyah", adet: 1 }]],
  ];
  for (const [ad, satirlar, sepet] of vaka) {
    const p = await prova(YENI, satirlar, sepet);
    toplamYazma += p.d1Yazma; toplamAg += p.agCagri;
    toplamOkuma += p.d1Okuma; toplamFirst += p.d1First;
    if (p.d1Yazma !== 0) { hatalar.push(ad + ": D1'e " + p.d1Yazma + " YAZMA yapildi"); }
    if (p.agCagri !== 0) { hatalar.push(ad + ": " + p.agCagri + " AG cagrisi yapildi"); }
    if (p.d1First !== 0) { hatalar.push(ad + ": siparis_no sorgusu (first) " + p.d1First); }
    if (p.sayaclar.yazilan.length) { hatalar.push(ad + ": SQL yazma: " + p.sayaclar.yazilan[0].sql.slice(0, 40)); }
  }
  not("prova x" + vaka.length + " -> D1 YAZMA=" + toplamYazma + " (0 olmali), AG cagri=" +
      toplamAg + " (0 olmali), siparis_no sorgusu=" + toplamFirst + " (0 olmali), D1 SALT-OKUMA=" +
      toplamOkuma);

  // SAYAC OLU MU? Ayni kosumda /baslat ikisini de ARTIRMALI (yoksa yukaridaki 0'lar anlamsiz).
  const b = await baslat(YENI, [d1Satiri(KONFIGUR_URUNLER[0])],
    [{ id: KONFIGUR_URUNLER[0].id, malzeme: "ASA", renk: "Siyah", adet: 2,
       parametreler: { boy_mm: 300 } }]);
  not("KONTROL (/baslat ayni sepet) -> D1 YAZMA=" + b.d1Yazma + " (>0 olmali), AG cagri=" +
      b.agCagri + " (>0 olmali) — sayaclarin OLU olmadigi kaniti");
  if (!(b.d1Yazma > 0)) { hatalar.push("KONTROL: /baslat D1'e yazmadi -> yazma sayaci OLU"); }
  if (!(b.agCagri > 0)) { hatalar.push("KONTROL: /baslat ag cagrisi yapmadi -> ag sayaci OLU"); }

  if (hatalar.length) {
    kirmizi += 1;
    hatalar.forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — yan etkisizlik");
  } else { ham.push("  ✅ GECTI — prova hicbir yazma/bildirim uretmiyor, sayaclar canli"); }
}

// =================================================================== 5) SIZINTI YUZEYI
baslik("== 5) PROVA SIZINTI YUZEYI — beyaz liste + yasak alan taramasi ==");
{
  const hatalar = [];
  const UST_IZIN = new Set(["prova", "satirlar", "urun_kurus", "kargo_kurus", "tahsilat_kurus",
                            "tutar", "net_kurus", "kdv_kurus", "kdv_yuzde"]);
  const SATIR_IZIN = new Set(["id", "adet", "birim_kurus", "tutar_kurus", "parametre_detay"]);
  const urun = KONFIGUR_URUNLER[0];
  const p = await prova(YENI, [d1Satiri(urun)],
    [{ id: urun.id, malzeme: "PETG", renk: "Siyah", adet: 1, parametreler: { boy_mm: 220 } }]);
  const ustFazla = Object.keys(p.govde).filter((k) => !UST_IZIN.has(k));
  if (ustFazla.length) { hatalar.push("cevapta izinsiz UST alan: " + ustFazla.join(",")); }
  for (const s of (p.govde.satirlar || [])) {
    const f = Object.keys(s).filter((k) => !SATIR_IZIN.has(k));
    if (f.length) { hatalar.push("satirda izinsiz alan: " + f.join(",")); }
  }
  // Icerik taramasi: katalog basligi / gorsel URL'i / hacim ham metinde GECMEMELI.
  const gorselUrl = (urun.gorseller && urun.gorseller[0]) || "";
  const yasak = [["baslik", urun.baslik], ["kategori", urun.kategori], ["gorsel", gorselUrl],
                 ["hacim_mm3", "hacim"], ["iban", "iban"], ["token", "token"],
                 ["siparis no", "PR-"]];
  for (const [ad, deger] of yasak) {
    if (deger && p.ham.toLowerCase().includes(String(deger).toLowerCase())) {
      hatalar.push("cevap govdesinde '" + ad + "' izi var");
    }
  }
  not("cevap alanlari: " + Object.keys(p.govde).join(",") + " | satir alanlari: " +
      Object.keys((p.govde.satirlar || [{}])[0]).join(","));
  not("yasak iz taramasi (baslik/kategori/gorsel/hacim/iban/token/siparis-no): " +
      (hatalar.length ? "IHLAL" : "TEMIZ"));

  // PII: govdeye musteri konsa bile cevaba SIZMAZ ve yazma OLMAZ.
  const sayaclar = yeniSayac();
  const env = Object.assign({}, ENV_TABAN, { KATALOG: d1Sahte([d1Satiri(urun)], sayaclar) });
  const agOnce = ag.toplam;
  const istek = new Request("https://pruvo3d.com/api/shop/fiyat", {
    method: "POST", headers: { "Content-Type": "application/json", "CF-Connecting-IP": "10.9.9.9" },
    body: JSON.stringify({ musteri: MUSTERI, sozlesme_onay: true, atif: { fbp: "fb.1.x" },
                           sepet: [{ id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                                     parametreler: { boy_mm: 150 } }] }),
  });
  const cev = await mod_fetch(YENI, istek, env);
  const metin = await cev.text();
  if (metin.includes(MUSTERI.eposta) || metin.includes(MUSTERI.tel) ||
      metin.includes("fb.1.x")) { hatalar.push("PII/atif cevaba yansidi"); }
  if (sayaclar.run !== 0) { hatalar.push("musterili prova D1'e YAZDI"); }
  if (ag.toplam !== agOnce) { hatalar.push("musterili prova AG cagrisi yapti"); }
  not("PII testi: govdede musteri+atif verildi -> cevapta iz=" +
      (metin.includes(MUSTERI.eposta) ? "VAR" : "YOK") + ", D1 yazma=" + sayaclar.run +
      ", ag=" + (ag.toplam - agOnce));

  // Yontem/uc yuzeyi: GET /fiyat kabul EDILMEZ.
  const getCev = await mod_fetch(YENI, new Request("https://pruvo3d.com/api/shop/fiyat"),
                                 Object.assign({}, ENV_TABAN,
                                   { KATALOG: d1Sahte([], yeniSayac()) }));
  if (getCev.status !== 404) { hatalar.push("GET /fiyat " + getCev.status + " (404 olmali)"); }
  not("GET /fiyat -> " + getCev.status + " (404 beklenir; uc yalniz POST)");

  if (hatalar.length) {
    kirmizi += 1;
    hatalar.forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — sizinti yuzeyi");
  } else { ham.push("  ✅ GECTI — cevap beyaz-liste; ic alan/PII/uc yuzeyi temiz"); }
}

async function mod_fetch(mod, istek, env) {
  return await mod.default.fetch(istek, env, { waitUntil() {} });
}

// =================================================================== 6) DOGRULAMA + HIZ SINIRI
baslik("== 6) PROVA DOGRULAMASI /baslat ILE AYNI + hiz siniri ==");
{
  const hatalar = [];
  const urun = KONFIGUR_URUNLER[0];
  const satirlar = [d1Satiri(urun)];
  const vaka = [
    ["bilinmeyen malzeme", { id: urun.id, malzeme: "TITANYUM", renk: "Siyah", adet: 1 }],
    ["bilinmeyen renk", { id: urun.id, malzeme: "PLA", renk: "Neon", adet: 1 }],
    ["adet 500", { id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 500 }],
    ["adet 0", { id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 0 }],
    ["id bicimi bozuk", { id: "BUYUK HARF!", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    ["boy_etiket (D1'de yok)", { id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                                 boy_etiket: "L" }],
  ];
  for (const [ad, kalem] of vaka) {
    const b = await baslat(YENI, satirlar, [kalem]);
    const p = await prova(YENI, satirlar, [kalem]);
    if (b.kod !== p.kod || b.govde.hata !== p.govde.hata) {
      hatalar.push(ad + ": baslat=" + b.kod + "/" + b.govde.hata + " prova=" + p.kod + "/" +
                   p.govde.hata);
    }
  }
  const bosSepet = await prova(YENI, satirlar, []);
  if (bosSepet.kod !== 400) { hatalar.push("bos sepet " + bosSepet.kod); }
  const cokKalem = await prova(YENI, satirlar,
    Array.from({ length: 31 }, () => ({ id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1 })));
  if (cokKalem.kod !== 400 || cokKalem.govde.hata !== "gecersiz-sepet") {
    hatalar.push("31 kalem " + cokKalem.kod + "/" + cokKalem.govde.hata);
  }
  not("dogrulama paritesi: " + vaka.length + " vaka + bos sepet(" + bosSepet.kod +
      ") + 31 kalem(" + cokKalem.govde.hata + ") -> uyusmazlik " + hatalar.length);

  // HIZ SINIRI: ayni IP'den 31 istek -> sonuncusu 429; farkli IP etkilenmez; yazma YOK.
  const sepet = [{ id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                   parametreler: { boy_mm: 150 } }];
  let ilk429 = 0, yazma = 0;
  // Pencere sinirinda (dakika basi) sayac sifirlanabilir -> patlama BIR KEZ taze IP ile
  // tekrarlanir (kararsiz CI kirmizisi olmasin; iddia degismez).
  for (let tur = 0; tur < 2 && ilk429 === 0; tur++) {
    const ip = "203.0.113." + (7 + tur * 10);
    for (let i = 1; i <= 31; i++) {
      const r = await prova(YENI, satirlar, sepet, ip);
      yazma += r.d1Yazma;
      if (r.kod === 429 && !ilk429) { ilk429 = i; }
    }
  }
  const baskaIp = await prova(YENI, satirlar, sepet, "203.0.113.8");
  not("hiz siniri: ayni IP'de ilk 429 = " + ilk429 + ". istek (31. beklenir); baska IP -> " +
      baskaIp.kod + "; sinir sirasinda D1 yazma=" + yazma);
  if (ilk429 !== 31) { hatalar.push("hiz siniri 31. istekte devreye girmedi (ilk429=" + ilk429 + ")"); }
  if (baskaIp.kod !== 200) { hatalar.push("baska IP de kisitlandi: " + baskaIp.kod); }
  if (yazma !== 0) { hatalar.push("hiz siniri yolunda D1 yazma: " + yazma); }

  if (hatalar.length) {
    kirmizi += 1;
    hatalar.forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — dogrulama/hiz siniri");
  } else { ham.push("  ✅ GECTI — prova dogrulamasi tahsilatla ayni; hiz siniri calisiyor"); }
}

// =================================================================== 7) FAIL-CLOSED IDDIALARI
/** Artefaktta OLMAYAN konfigur urunu icin FAIL-CLOSED iddialari (hem /baslat hem /fiyat).
 *  Mutasyon altinda bu iddialarin KIRMIZI yanmasi beklenir (vakum olcumu). */
async function failClosedIddialari(mod) {
  const sonuc = [];
  for (const [boy, malzeme] of [[60, "PLA"], [150, "PLA"], [300, "PLA"], [300, "ASA"]]) {
    const kalem = { id: YENI_KONFIGUR.id, malzeme, renk: "Siyah", adet: 1,
                    parametreler: { boy_mm: boy } };
    const b = await baslat(mod, [YENI_KONFIGUR], [kalem]);
    const p = await prova(mod, [YENI_KONFIGUR], [kalem]);
    const et = boy + "mm/" + malzeme;
    sonuc.push({ ad: "baslat " + et + " kod=400", ok: b.kod === 400, olculen: b.kod });
    sonuc.push({ ad: "baslat " + et + " hata=konfigur-urun", ok: b.govde.hata === "konfigur-urun",
                 olculen: b.govde.hata });
    sonuc.push({ ad: "baslat " + et + " SABIT FIYAT HESAPLANMADI", ok: b.birimKurus === null,
                 olculen: b.birimKurus });
    sonuc.push({ ad: "baslat " + et + " D1'e YAZILMADI", ok: b.d1Yazma === 0, olculen: b.d1Yazma });
    sonuc.push({ ad: "prova " + et + " kod=400", ok: p.kod === 400, olculen: p.kod });
    sonuc.push({ ad: "prova " + et + " hata=konfigur-urun", ok: p.govde.hata === "konfigur-urun",
                 olculen: p.govde.hata });
    sonuc.push({ ad: "prova " + et + " FIYAT DONMEDI",
                 ok: !p.govde.satirlar && p.govde.tahsilat_kurus === undefined,
                 olculen: JSON.stringify(p.govde.tahsilat_kurus) });
  }
  return sonuc;
}

baslik("== 7) FAIL-CLOSED — artefaktta olmayan konfigur urunu (baslat + prova) ==");
{
  const iddia = await failClosedIddialari(YENI);
  const kalan = iddia.filter((i) => !i.ok);
  not("iddia: " + iddia.length + " (4 kombinasyon x 7) — kalan: " + kalan.length);
  kalan.slice(0, 10).forEach((i) => ham.push("    ❌ " + i.ad + " (olculen: " + i.olculen + ")"));
  if (kalan.length) { kirmizi += 1; ham.push("  ❌ KALDI — fail-closed"); }
  else { ham.push("  ✅ GECTI — 28/28 iddia; sabit fiyat HESAPLANMIYOR, prova da 400 doner"); }
}

// =================================================================== 8) MUTANTLAR
baslik("== 8) KIRMIZI-MUTASYON (M1..M4) ==");
{
  const KAYNAKLAR = guncelKaynaklar();

  // ---- M1: ARTEFAKT BAYAT (urunler.json'da var, artefaktta yok) ----
  ham.push("  -- M1: artefakt bayat (yeni konfigurlu urun uretilmedi) --");
  const gecici = path.join(SHOP, TEMP_ONEK + "m1-" + process.pid);
  fs.mkdirSync(gecici, { recursive: true });
  dizinler.push(gecici);
  // MUTANT KATALOG = GERCEK urunler.json BAYTLARI + basa eklenmis YENI konfigurlu urun.
  // (Katalogu JS'te yeniden serilestirmek sayi YAZIMINI degistirir — mutasyon o gurultuye
  // degil, YENI URUNE dayansin.)
  const hamKatalog = fs.readFileSync(path.join(KOK, "urunler.json"), "utf8");
  const yeniUrunMetni = JSON.stringify({ id: YENI_KONFIGUR.id, kategori: "Skan Art",
    baslik: "Ejderha", fiyat: "500 TL", gorseller: [],
    konfigur: KONFIGUR_URUNLER[0].konfigur });
  const miniYol = path.join(KOK, "urunler.json");            // KONTROL: gercek katalog
  const miniArtiYol = path.join(gecici, "urunler-arti.json");  // MUTANT: +1 konfigurlu urun
  fs.writeFileSync(miniArtiYol,
    hamKatalog.replace(/^\s*\[/, "[" + yeniUrunMetni + ","));
  function kapiKos(urunlerYolu) {
    try {
      execFileSync("python3", [path.join(KOK, "tools", "konfigur-bundle-kapisi.py"),
                               "--urunler", urunlerYolu,
                               "--dosya", path.join(SRC, "konfigurlar.js")],
                   { encoding: "utf8", stdio: "pipe" });
      return 0;
    } catch (e) { return e.status; }
  }
  const rcGuncel = kapiKos(miniYol);
  const rcBayat = kapiKos(miniArtiYol);
  not("M1 kapi: guncel katalog rc=" + rcGuncel + " (0 olmali) | +1 konfigurlu urun rc=" +
      rcBayat + " (1 olmali)");
  // Calisma zamani sonucu: GERCEK artefakttan bir urun dusurulurse -> 400 (sabit fiyata dusmez).
  // Artefakt id'ye gore SIRALI: ilk kaydi secmek blok deseninin (virgulle biten) tutmasini
  // garanti eder (son kayitta kapanis virgulsuzdur).
  let eksikKaynak = KAYNAKLAR["konfigurlar.js"];
  const dusen = [...KONFIGUR_URUNLER].sort((a, b) => (a.id < b.id ? -1 : 1))[0];
  const blok = new RegExp('\\n  "' + dusen.id + '": \\{[\\s\\S]*?\\n  \\},');
  const kesildi = blok.test(eksikKaynak);
  eksikKaynak = eksikKaynak.replace(blok, "");
  const m1Mod = await modulYukle(dizinKur("m1src",
    Object.assign({}, KAYNAKLAR, { "konfigurlar.js": eksikKaynak })));
  const m1r = await baslat(m1Mod, [d1Satiri(dusen)],
    [{ id: dusen.id, malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 300 } }]);
  const m1p = await prova(m1Mod, [d1Satiri(dusen)],
    [{ id: dusen.id, malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 300 } }]);
  not("M1 calisma zamani (" + dusen.id + " artefakttan silindi, kesildi=" + kesildi + "): " +
      "baslat=" + m1r.kod + "/" + m1r.govde.hata + " fiyat=" + m1r.birimKurus +
      " | prova=" + m1p.kod + "/" + m1p.govde.hata);
  const m1Ok = rcGuncel === 0 && rcBayat === 1 && kesildi && m1r.kod === 400 &&
               m1r.govde.hata === "konfigur-urun" && m1r.birimKurus === null &&
               m1p.kod === 400 && m1p.govde.hata === "konfigur-urun";
  if (!m1Ok) { kirmizi += 1; ham.push("    ❌ M1 KALDI"); }
  else { ham.push("    ✅ M1: bayat artefakt CI'da rc=1; calisma zamani fail-closed 400"); }

  // ---- M2: FAIL-CLOSED KOLU SILINDI (sabit fiyata dusurulmus) ----
  ham.push("  -- M2: fail-closed kol silindi (kalem sabit fiyata duser) --");
  const DESEN = /\n\s*\} else if \(konfigurBeklenirMi\(u\)\) \{[\s\S]*?\n(\s*)\} else if \(u\.parametrik\) \{/;
  const mutantKaynak = KAYNAKLAR["index.js"].replace(DESEN, "\n$1} else if (u.parametrik) {");
  const m2Uygulandi = DESEN.test(KAYNAKLAR["index.js"]) &&
                      !/konfigurBeklenirMi\(u\)/.test(mutantKaynak);
  let m2Kalan = [];
  if (!m2Uygulandi) {
    kirmizi += 1;
    ham.push("    ❌ M2 mutasyonu UYGULANAMADI (kol deseni degismis — desen guncellenmeli)");
  } else {
    const m2Mod = await modulYukle(dizinKur("m2src",
      Object.assign({}, KAYNAKLAR, { "index.js": mutantKaynak })));
    const iddia = await failClosedIddialari(m2Mod);
    m2Kalan = iddia.filter((i) => !i.ok);
    not("M2 VAKUM: " + iddia.length + " iddiadan " + m2Kalan.length + " tanesi KIRMIZI yandi " +
        "(>=10 olmali)");
    m2Kalan.slice(0, 12).forEach((i) => ham.push("    · yakalandi: " + i.ad +
                                                 " (olculen: " + i.olculen + ")"));
    if (m2Kalan.length < 10) {
      kirmizi += 1;
      ham.push("    ❌ M2 KALDI — kol silindi ama iddialar sessiz kaldi (OLU NOBETCI)");
    } else { ham.push("    ✅ M2: " + m2Kalan.length + " iddia KIRMIZI"); }
  }

  // ---- M3: KAPININ CAGRI SATIRI deploy.yml'den SILINDI ----
  ham.push("  -- M3: kapinin CI cagri satiri silindi --");
  const deployYol = path.join(KOK, ".github", "workflows", "deploy.yml");
  const deploy = fs.readFileSync(deployYol, "utf8");
  const cagriDeseni = /^.*python3 tools\/konfigur-bundle-kapisi\.py\s*$/m;
  const cagriVar = cagriDeseni.test(deploy);
  const mutantDeploy = deploy.replace(/^.*konfigur-bundle-kapisi\.py.*$/gm, "");
  const mutantDeployYol = path.join(gecici, "deploy-mutant.yml");
  fs.writeFileSync(mutantDeployYol, mutantDeploy);
  function kapsamKos(yol) {
    try {
      execFileSync("python3", [path.join(KOK, "tools", "ci-kapsam-test.py"), "--deploy", yol],
                   { encoding: "utf8", stdio: "pipe" });
      return 0;
    } catch (e) { return e.status; }
  }
  const rcGercek = kapsamKos(deployYol);
  const rcMutant = kapsamKos(mutantDeployYol);
  not("M3: deploy.yml'de kapi cagrisi=" + (cagriVar ? "VAR" : "YOK") +
      "; ci-kapsam gercek rc=" + rcGercek + " (0 olmali), cagri silinmis rc=" + rcMutant +
      " (1 olmali)");
  if (!(cagriVar && rcGercek === 0 && rcMutant === 1)) {
    kirmizi += 1;
    ham.push("    ❌ M3 KALDI — kapi CI'dan silinince kimse uyarmiyor");
  } else { ham.push("    ✅ M3: cagri satiri silinince ci-kapsam-test.py KIRMIZI"); }

  // ---- M4: PROVA YAN ETKI URETIYOR (D1 yazma + Telegram) ----
  ham.push("  -- M4: prova yan etki uretiyor (D1 INSERT + Telegram) --");
  const capa = "  const kargoKurus = SECENEK.kargoKurus(toplamKurus);\n" +
               "  const tahsilatKurus = toplamKurus + kargoKurus;\n" +
               "  const kdv = SECENEK.kdvAyristir(tahsilatKurus);\n\n  return json({\n    prova: true,";
  const enjekte = "  const kargoKurus = SECENEK.kargoKurus(toplamKurus);\n" +
    "  const tahsilatKurus = toplamKurus + kargoKurus;\n" +
    "  const kdv = SECENEK.kdvAyristir(tahsilatKurus);\n" +
    "  await env.KATALOG.prepare(\"INSERT INTO siparisler (siparis_no) VALUES (?)\")" +
    ".bind(\"PR-MUTANT\").run();\n" +
    "  await telegram(env, \"mutant prova bildirimi\");\n\n  return json({\n    prova: true,";
  const m4Kaynak = KAYNAKLAR["index.js"].replace(capa, enjekte);
  const m4Uygulandi = m4Kaynak !== KAYNAKLAR["index.js"];
  if (!m4Uygulandi) {
    kirmizi += 1;
    ham.push("    ❌ M4 mutasyonu UYGULANAMADI (capa metni degismis)");
  } else {
    const m4Mod = await modulYukle(dizinKur("m4src",
      Object.assign({}, KAYNAKLAR, { "index.js": m4Kaynak })));
    const urun = KONFIGUR_URUNLER[0];
    const p = await prova(m4Mod, [d1Satiri(urun)],
      [{ id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 150 } }]);
    const yakalanan = [];
    if (p.d1Yazma !== 0) { yakalanan.push("D1 yazma=" + p.d1Yazma); }
    if (p.agCagri !== 0) { yakalanan.push("ag cagri=" + p.agCagri); }
    if (p.sayaclar.yazilan.length) { yakalanan.push("SQL=" + p.sayaclar.yazilan[0].sql.slice(0, 30)); }
    not("M4: mutant provada yakalanan yan etki -> " + (yakalanan.join(", ") || "HICBIRI"));
    if (yakalanan.length < 2) {
      kirmizi += 1;
      ham.push("    ❌ M4 KALDI — yan etki sayaclari OLU (mutant sessiz gecti)");
    } else { ham.push("    ✅ M4: " + yakalanan.length + " sayac KIRMIZI yandi"); }
  }
}

// ------------------------------------------------------------------ kosum sonu
console.log(ham.join("\n"));
console.log("");
console.log(kirmizi === 0 ? "✅ HEPSI GECTI (" + setSayisi + "/" + setSayisi + " set)"
                          : "❌ " + kirmizi + "/" + setSayisi + " set KALDI");
process.exit(kirmizi === 0 ? 0 : 1);
