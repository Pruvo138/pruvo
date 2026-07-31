#!/usr/bin/env node
/**
 * YAYIN KOPYASI PARITE KABUL TESTI — "yorum soyma parayi degistirmedi mi?"
 *
 *   node jenerator/test/yayin-fiyat-parite.mjs
 *
 * NEDEN VAR (olculmus sessiz-hata sinifi): tools/build.py, tarayiciya inen JS
 * varliklarinin YORUMU SOYULMUS bir kopyasini `_yayin/<rel>`e yazar ve deploy _site'a
 * ORADAN kopyalar (bkz. build.py yayin_js_yaz / .github/workflows/deploy.yml). Soyucu
 * (tools/yorum_soy.py) kendi JS lexer'ini kullanir; regex-mi-bolme, sablon literali,
 * dizge icindeki `//` gibi vakalarda YANILIRSA soyulmus dosya SOZDIZIMSEL OLARAK
 * GECERLI kalip DAVRANISI degismis olabilir. O hata odeme yolunda SESSIZDIR: musteriye
 * gosterilen fiyat degisir, hicbir sey kirmizi yanmaz. `node --check` (build.py'nin
 * ikinci gozu) bu sinifi YAKALAMAZ — cunku sozdizimi bozulmaz.
 *
 * BU TEST ONU DAVRANIS EKSENINDE OLCER: fiyat KAYNAK dosyalarla ve YAYIN (soyulmus)
 * dosyalarla ayri ayri hesaplanir; TAM KUME, orneklem YOK, kurus cinsinden SAPAN 0.
 *
 * BOLUM A — FIYAT PARITESI (tam kume)
 *   jenerator/urunler/*.json semalarinin HEPSI x BOY_SAYISI deterministik olcu seti
 *   x tum filamentler x tum renkler. Iki kume:
 *     KAYNAK = secenekler.js + jenerator/hacim.js + jenerator/konfigurator.js
 *     YAYIN  = _yayin/ altindaki AYNI uc dosya (soyulmus)
 *   Iddia: her kombinasyonda parametrikFiyatKurus ciktisi BIREBIR ayni (null'lar dahil).
 *
 * BOLUM B — `?v=` SURUM HATTI
 *   Uretilen sayfalardaki her site-ici <script src="/x.js?v=hash"> icin:
 *     (1) deploy'un _site'a koyacagi dosya (_yayin/x.js) VAR,
 *     (2) sayfaya basilan hash o YAYIN kopyasinin sha1'inin ilk 10 hex'i.
 *   Yani tarayiciya giden bayt ile URL'deki surum damgasi AYNI dosyadan turer; soyma
 *   hash'i kaydirdiysa bu bolum kirmizi yanar.
 *   OLCULEMEDI (bilerek): "canlida 200 doner" — bu kosum AGSIZDIR; buradaki karsiligi
 *   "deploy'un kopyalayacagi dosya diskte var" (yol butunlugu).
 *
 * BOLUM C — OZ-NOBETCI (karsilastirma OLU MU?)
 *   Yayin kopyasina bellekte tek karakterlik bir fiyat mutasyonu enjekte edilir
 *   (filament katsayisi) ve BOLUM A'nin karsilastiricisi CAGRILIR: sapma > 0
 *   GORMEZSE bu testin kendisi yalancidir -> kirmizi.
 *
 * BAGIMLILIK: `python3 tools/build.py` bu testten ONCE kosmus olmali (_yayin uretir).
 * _yayin yoksa test OLCULEMEDI ile exit 3 verir (sessizce yesil YANMAZ).
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import crypto from "node:crypto";
import childProcess from "node:child_process";
import { fileURLToPath } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const KOK = path.dirname(path.dirname(BURASI));
const YAYIN = path.join(KOK, "_yayin");
const SEMA_DIZINI = path.join(KOK, "jenerator", "urunler");

const JS_VARLIKLARI = ["secenekler.js", "jenerator/hacim.js", "jenerator/konfigurator.js"];
const BOY_SAYISI = 25;            // urun basina deterministik olcu seti
const ASGARI_ANLAMLI = 1275;      // KraL'in tam-kume esigi (17 x 25 x 3)

let hata = 0;
let iddiaSayisi = 0;
function iddia(ad, kosul, ek) {
  iddiaSayisi++;
  if (kosul) { console.log("  OK   " + ad); return; }
  hata++;
  console.log("  HATA " + ad + (ek ? "  -> " + ek : ""));
}
function olculemedi(sebep) {
  console.log("OLCULEMEDI: " + sebep);
  process.exit(3);
}

// ------------------------------------------------------------------ yukleyici
/** Uc JS varligini TEK bir vm baglaminda yukler; {SECENEK, HACIM, KONF} doner.
 *  `metinler` verilirse dosya yerine O METIN yuklenir (oz-nobetci mutasyonu icin). */
function moduleriYukle(kok, metinler) {
  const sandbox = { console };
  vm.createContext(sandbox);
  for (const rel of JS_VARLIKLARI) {
    const kaynak = (metinler && metinler[rel] != null)
      ? metinler[rel]
      : fs.readFileSync(path.join(kok, rel), "utf8");
    vm.runInContext(kaynak, sandbox, { filename: path.join(kok, rel) });
  }
  return { SECENEK: sandbox.PRUVO_SECENEK, HACIM: sandbox.PRUVO_HACIM, KONF: sandbox.PRUVO_KONF };
}

// --------------------------------------------------------- deterministik setler
function nicele(deger, p) {
  const adim = (typeof p.adim === "number" && p.adim > 0) ? p.adim : 1;
  const min = p.min, max = p.max;
  let v = min + Math.round((deger - min) / adim) * adim;
  if (v < min) { v = min; }
  if (v > max) { v = max; }
  return Math.round(v * 1e6) / 1e6;     // kayan nokta gurultusu temizligi
}

/** Bir sema icin BOY_SAYISI adet deterministik parametre seti (tohum = indeksler). */
function olcuSetleri(sema) {
  const setler = [];
  for (let k = 0; k < BOY_SAYISI; k++) {
    const d = {};
    for (let i = 0; i < sema.parametreler.length; i++) {
      const p = sema.parametreler[i];
      const tip = p.tip || "sayi";
      if (tip === "sayi") {
        const yayilim = ((k * (i + 3) + i) % BOY_SAYISI) / (BOY_SAYISI - 1);   // 0..1
        d[p.ad] = nicele(p.min + yayilim * (p.max - p.min), p);
      } else if (tip === "secim") {
        const secenekler = p.secenekler || [];
        const s = secenekler[(k + i) % secenekler.length];
        d[p.ad] = (s && typeof s === "object") ? s.deger : s;
      } else {
        d[p.ad] = p.varsayilan != null ? p.varsayilan : "PRUVO";
      }
    }
    setler.push(d);
  }
  return setler;
}

// ------------------------------------------------------------------ karsilastirici
/** Hacim (mm3) TABLOSU: [sema indeksi][olcu indeksi]. konfigurator.hacimMm3 uzerinden
 *  hesaplanir (hem konfigurator.js hem hacim.js yolu olculur).
 *  MALZEME/RENK EKSENINDEN BAGIMSIZ -> her (urun, olcu) icin BIR KEZ hesaplanir;
 *  aksi halde `konektor` ailesinin sayisal integrali (48x520x520 hucre) kombinasyon
 *  basina yeniden kosar ve suite dakikalarca surerdi. */
function hacimTablosu(M, semalar, setTablosu) {
  return semalar.map((sema, si) =>
    setTablosu[si].map((degerler) => M.KONF.hacimMm3(sema, degerler, M.HACIM)));
}

/** Iki modul kumesini TAM KUME uzerinde karsilastirir (fiyat + hacim ekseni).
 *  `hacimA/hacimB` verilirse hacim yeniden HESAPLANMAZ (mutant kosumu icin). */
function fiyatlariKarsilastir(A, B, semalar, setTablosu, hacimA, hacimB) {
  const filamentler = A.SECENEK.FILAMENT_SIRA;
  const renkler = A.SECENEK.RENK_SECENEKLERI;
  const hA = hacimA || hacimTablosu(A, semalar, setTablosu);
  const hB = hacimB || hacimTablosu(B, semalar, setTablosu);
  let toplam = 0, anlamli = 0, sapan = 0, ilkSapma = null, hacimSapan = 0;
  semalar.forEach((sema, si) => {
    setTablosu[si].forEach((degerler, oi) => {
      const va = hA[si][oi], vb = hB[si][oi];
      if (!Object.is(va, vb)) { hacimSapan++; }
      for (const malzeme of filamentler) {
        for (const renk of renkler) {
          const a = (va == null) ? null : A.SECENEK.parametrikFiyatKurus(
            sema.hacimFormulu, sema.tabanFiyatTL, sema.tabanHacimMm3, va, malzeme, renk);
          const b = (vb == null) ? null : B.SECENEK.parametrikFiyatKurus(
            sema.hacimFormulu, sema.tabanFiyatTL, sema.tabanHacimMm3, vb, malzeme, renk);
          toplam++;
          if (a != null) { anlamli++; }
          if (!Object.is(a, b)) {
            sapan++;
            if (!ilkSapma) {
              ilkSapma = { id: sema.id, malzeme, renk, kaynak: a, yayin: b,
                           degerler: JSON.stringify(degerler) };
            }
          }
        }
      }
    });
  });
  return { toplam, anlamli, sapan, ilkSapma, hacimSapan, hA, hB };
}

// ====================================================================== KOSUM
if (!fs.existsSync(YAYIN)) {
  olculemedi("_yayin/ yok -> once `python3 tools/build.py` kosmali "
             + "(yayin kopyalari uretilmeden parite olculemez)");
}
for (const rel of JS_VARLIKLARI) {
  if (!fs.existsSync(path.join(YAYIN, rel))) {
    olculemedi("_yayin/" + rel + " yok -> build.py yayin kopyasini uretmemis");
  }
}

const semalar = fs.readdirSync(SEMA_DIZINI).filter((a) => a.endsWith(".json")).sort()
  .map((a) => JSON.parse(fs.readFileSync(path.join(SEMA_DIZINI, a), "utf8")));
if (semalar.length === 0) { olculemedi("jenerator/urunler bos"); }

const KAYNAK = moduleriYukle(KOK);
const YAYIN_MOD = moduleriYukle(YAYIN);

console.log("BOLUM A — FIYAT PARITESI (kaynak JS  vs  _yayin soyulmus JS)");
const setTablosu = semalar.map(olcuSetleri);
const A = fiyatlariKarsilastir(KAYNAK, YAYIN_MOD, semalar, setTablosu);
console.log("  urun=%d  boy=%d  filament=%d  renk=%d  ->  kombinasyon=%d (anlamli/fiyatli=%d)",
            semalar.length, BOY_SAYISI, KAYNAK.SECENEK.FILAMENT_SIRA.length,
            KAYNAK.SECENEK.RENK_SECENEKLERI.length, A.toplam, A.anlamli);
iddia("A1 SAPAN 0 (kurus cinsinden birebir esitlik, orneklem YOK)",
      A.sapan === 0, A.ilkSapma ? JSON.stringify(A.ilkSapma) : "");
iddia("A1b HACIM ekseni de sapmasiz (hacim.js + konfigurator.js yolu)",
      A.hacimSapan === 0, "hacim-sapan=" + A.hacimSapan);
iddia("A2 anlamli (fiyat donen) kombinasyon >= " + ASGARI_ANLAMLI + " — kume OLU degil",
      A.anlamli >= ASGARI_ANLAMLI, "anlamli=" + A.anlamli);
iddia("A3 yayin modulleri gercekten YUKLENDI (SECENEK/HACIM/KONF)",
      !!(YAYIN_MOD.SECENEK && YAYIN_MOD.HACIM && YAYIN_MOD.KONF));
iddia("A4 yayin kopyasi KAYNAKTAN farkli (soyma fiilen calisti)",
      JS_VARLIKLARI.some((rel) =>
        fs.readFileSync(path.join(KOK, rel), "utf8")
          !== fs.readFileSync(path.join(YAYIN, rel), "utf8")));

console.log("BOLUM B — `?v=` surum hatti (sayfaya basilan hash == YAYINLANAN bayt)");
// Site-ici <script src="/x.js"> — surumlu VE surumsuz hali AYNI desende yakalanir ki
// "hic ?v= basilmamis" hali de olculebilsin (orneklem YOK: uretilen TUM sayfalar).
const SCRIPT_RE = /<script\b[^>]*\ssrc="(\/[^"?]+\.js)(\?v=([0-9a-f]{10}))?"/g;
const HARIC = new Set([".git", "_yayin", "node_modules", ".claude", "raporlar"]);

function hashOf(dosya) {
  return crypto.createHash("sha1").update(fs.readFileSync(dosya)).digest("hex").slice(0, 10);
}
/** IZLENEN (git ls-files) .html = KAYNAK dosya; build.py'nin yayin donusumunden
 *  GECMEZ (elle yazilmis 4 yasal sayfa + kaynak index.html). Kapsam = URETILEN sayfalar. */
function izlenenHtml() {
  const cikti = require_execFileSync("git", ["-C", KOK, "ls-files", "*.html"]);
  return new Set(cikti.split("\n").filter(Boolean).map((r) => path.join(KOK, r)));
}
function require_execFileSync(cmd, args) {
  // dinamik import yerine senkron cocuk surec (test tek gecisli ve saf tutulur)
  return childProcess.execFileSync(cmd, args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
}
function htmlTara(dizin, biriktir) {
  for (const g of fs.readdirSync(dizin, { withFileTypes: true })) {
    if (g.isDirectory()) {
      if (HARIC.has(g.name)) { continue; }
      htmlTara(path.join(dizin, g.name), biriktir);
    } else if (g.name.endsWith(".html")) {
      biriktir.push(path.join(dizin, g.name));
    }
  }
}
const izlenen = izlenenHtml();
const tumHtml = [];
htmlTara(KOK, tumHtml);
const sayfaListesi = tumHtml.filter((y) => !izlenen.has(y)).sort();
if (sayfaListesi.length === 0) {
  olculemedi("uretilmis sayfa yok (index.built.html / urun/) -> once build.py");
}
let refToplam = 0, refEksik = 0, refHashSapan = 0, refSurumsuz = 0;
const refOrnek = [];
for (const s of sayfaListesi) {
  const metin = fs.readFileSync(s, "utf8");
  let m;
  SCRIPT_RE.lastIndex = 0;
  while ((m = SCRIPT_RE.exec(metin)) !== null) {
    refToplam++;
    const rel = m[1].replace(/^\//, "");
    const yayinDosyasi = path.join(YAYIN, rel);
    if (!fs.existsSync(yayinDosyasi)) {
      refEksik++;
      if (refOrnek.length < 5) { refOrnek.push(s + " -> _yayin/" + rel + " YOK"); }
      continue;
    }
    if (!m[3]) {
      refSurumsuz++;
      if (refOrnek.length < 5) { refOrnek.push(s + " -> " + rel + " ?v= YOK"); }
      continue;
    }
    if (hashOf(yayinDosyasi) !== m[3]) {
      refHashSapan++;
      if (refOrnek.length < 5) {
        refOrnek.push(s + " -> " + rel + " hash " + m[3] + " != " + hashOf(yayinDosyasi));
      }
    }
  }
}
console.log("  uretilen sayfa=%d (izlenen kaynak html haric=%d)  script referansi=%d",
            sayfaListesi.length, izlenen.size, refToplam);
iddia("B1 referans sayisi > 0 (tarama OLU degil)", refToplam > 0);
iddia("B2 her referansin YAYIN kopyasi diskte VAR (deploy'un kopyalayacagi bayt)",
      refEksik === 0, refOrnek.join(" | "));
iddia("B3 sayfadaki ?v= hash'i YAYIN kopyasinin hash'i (kaynak degil)",
      refHashSapan === 0, refOrnek.join(" | "));
iddia("B4 uretilen sayfada SURUMSUZ site-ici script referansi yok",
      refSurumsuz === 0, refOrnek.join(" | "));

console.log("BOLUM D — DIGER YAYIN JS VARLIKLARI (veri + API yuzeyi esitligi)");
// A bolumu fiyat ucgenini (secenekler + hacim + konfigurator) DAVRANIS ekseninde olcer.
// Kalan yayin varliklari icin ayni ekseni ucuz ama GERCEK bir imzayla olceriz:
//   * VERI dosyalari (filament-veri.js / taban-fiyatlar.js): yayilan objenin DERIN esitligi
//     -> soyma bir rakami/dizgeyi kirptiysa burada kirmizi.
//   * KOD dosyalari (konfigur.js / jenerator/viewer.js): yayilan API'nin anahtar kumesi +
//     her uyenin tipi + fonksiyon arite'si (length) -> soyma bir fonksiyonu yuttuysa
//     ya da imzasini bozduysa burada kirmizi.
const DIGER_VARLIKLAR = [
  { rel: "filament-veri.js", global: "PRUVO_FILAMENT", veri: true },
  { rel: "taban-fiyatlar.js", global: "PRUVO_TABAN_FIYATLAR", veri: true },
  { rel: "konfigur.js", global: "PRUVO_KONFIGUR", veri: false },
  { rel: "jenerator/viewer.js", global: "PRUVO_VIEWER", veri: false }
];
function tekYukle(kok, rel) {
  const sandbox = { console };
  sandbox.window = sandbox;      // window'a yazan varliklar (filament-veri / viewer)
  sandbox.self = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(kok, rel), "utf8"), sandbox,
                  { filename: path.join(kok, rel) });
  return sandbox;
}
function apiImzasi(o) {
  if (o == null) { return "YOK"; }
  return Object.keys(o).sort().map((k) => {
    const v = o[k];
    return k + ":" + typeof v + (typeof v === "function" ? "/" + v.length : "");
  }).join(",");
}
const eksikVarliklar = DIGER_VARLIKLAR
  .filter((v) => !fs.existsSync(path.join(YAYIN, v.rel))).map((v) => v.rel);
if (eksikVarliklar.length) {
  olculemedi("_yayin/{" + eksikVarliklar.join(", ") + "} yok -> build.py yayin kopyasini uretmemis");
}
for (const v of DIGER_VARLIKLAR) {
  const k = tekYukle(KOK, v.rel)[v.global];
  const y = tekYukle(YAYIN, v.rel)[v.global];
  iddia("D-" + v.rel + " yayilan " + v.global + " YUKLENDI (iki tarafta da)",
        k != null && y != null);
  if (v.veri) {
    iddia("D-" + v.rel + " VERI derin esitlik (soyma veriyi kirpmadi)",
          JSON.stringify(k) === JSON.stringify(y),
          "kaynak=" + JSON.stringify(k).length + "b  yayin=" + JSON.stringify(y).length + "b");
  } else {
    iddia("D-" + v.rel + " API imzasi ayni (anahtar + tip + arite)",
          apiImzasi(k) === apiImzasi(y), apiImzasi(k) + "  !=  " + apiImzasi(y));
  }
}

console.log("BOLUM C — OZ-NOBETCI (karsilastirici olu mu?)");
const mutantMetinleri = {};
const secenekMetni = fs.readFileSync(path.join(YAYIN, "secenekler.js"), "utf8");
mutantMetinleri["secenekler.js"] = secenekMetni.replace('"PETG": 30', '"PETG": 31');
iddia("C0 mutasyon fiilen uygulandi (capa metni bulundu)",
      mutantMetinleri["secenekler.js"] !== secenekMetni);
const MUTANT = moduleriYukle(YAYIN, mutantMetinleri);
// Mutasyon YALNIZ secenekler.js'te -> hacim tablolari degismez, yeniden hesaplanmaz
// (konektor integrali pahali; A bolumunun tablolari aynen kullanilir).
const C = fiyatlariKarsilastir(KAYNAK, MUTANT, semalar, setTablosu, A.hA, A.hB);
iddia("C1 fiyat mutanti SAPMA uretir (bu test yalanci yesil vermiyor)",
      C.sapan > 0, "sapan=" + C.sapan);

console.log("");
console.log("yayin-fiyat-parite: %d/%d iddia | kombinasyon=%d anlamli=%d sapan=%d hacim-sapan=%d | "
            + "sayfa=%d script-ref=%d eksik=%d surumsuz=%d hash-sapan=%d | mutant-sapma=%d",
            iddiaSayisi - hata, iddiaSayisi, A.toplam, A.anlamli, A.sapan, A.hacimSapan,
            sayfaListesi.length, refToplam, refEksik, refSurumsuz, refHashSapan, C.sapan);
process.exit(hata ? 1 : 0);
