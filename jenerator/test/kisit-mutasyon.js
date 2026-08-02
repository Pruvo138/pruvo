/* sema.kisitlar MUTASYON SURUCUSU — nobetcinin CANLI oldugunun kaniti.
   Kullanim:  node jenerator/test/kisit-mutasyon.js
   CI'da KOSMAZ (depo konvansiyonu: mutasyon suruculeri elle kosar, bkz.
   tools/eski-fiyat-test.py --mutasyon). Kanit REPODA DURSUN diye buradadir:
   anlatilan batarya kanit degildir → [[mutasyon-kaniti-yeniden-uretilebilir]].

   KABUL (cikis kodu TEK BASINA yetmez — mutant COKERSE de kod 1 olur):
     1) IDDIA SAYISI taban kosumla ESIT  -> test sonuna kadar kostu
     2) en az bir KIRMIZI satir
     3) ISARET SARTI: beklenen vaka KODLARI kirmizi satirlarda ADIYLA gecmeli
        (mutant kaza eseri baska yerden kirmizi yakip gecmis sayilmasin)
   Taban iddia sayisi KOSUMDA olculur, koda YAZILMAZ (capa yasagi).

   KONTROL MUTANTI ZORUNLU: davranis-koruyan mutant YESIL kalmali — yoksa surucu
   "her sey kirmizi" diye ucuza gecer.

   DISKE YAZMA: mutasyon YALNIZ gecici kopyaya uygulanir; kaynak dosyalarin
   sha256'si basta ve sonda dogrulanir → [[mutasyon-diske-yazma-tuzagi]]. */
"use strict";
var fs = require("fs");
var os = require("os");
var path = require("path");
var crypto = require("crypto");

var KOK = path.join(__dirname, "..", "..");
var KONF_YOL = path.join(KOK, "jenerator", "konfigurator.js");
var RULMAN_YOL = path.join(KOK, "jenerator", "urunler", "olcuye-ozel-rulman.json");
var VIDA_YOL = path.join(KOK, "jenerator", "urunler", "olcuye-ozel-vida-civata-somun-pul.json");
var VAKA = require(path.join(__dirname, "kisit-vakalar.js"));

function sha(yol) {
  return crypto.createHash("sha256").update(fs.readFileSync(yol)).digest("hex");
}
var BASLANGIC = { konf: sha(KONF_YOL), rulman: sha(RULMAN_YOL) };

var TMP = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-kisit-mut-"));
var sayac = 0;

/* Mutasyonu KOPYAYA uygular, kosar. -> {iddia, kirmiziKodlar, cokme} */
function kos(mut) {
  var konfMetin = fs.readFileSync(KONF_YOL, "utf8");
  var rulmanMetin = fs.readFileSync(RULMAN_YOL, "utf8");
  if (mut.dosya === "konf") {
    if (konfMetin.indexOf(mut.ara) < 0) {
      throw new Error("BAYAT HARNESS: mutasyon dayanagi konfigurator.js'te yok: " + mut.ara);
    }
    konfMetin = konfMetin.replace(mut.ara, mut.yeni);
  } else if (mut.dosya === "sema") {
    if (rulmanMetin.indexOf(mut.ara) < 0) {
      throw new Error("BAYAT HARNESS: mutasyon dayanagi rulman semasinda yok: " + mut.ara);
    }
    rulmanMetin = rulmanMetin.replace(mut.ara, mut.yeni);
  } else if (mut.dosya !== "yok") {
    throw new Error("bilinmeyen mutasyon hedefi: " + mut.dosya);
  }
  if (mut.dosya !== "yok" &&
      konfMetin === fs.readFileSync(KONF_YOL, "utf8") &&
      rulmanMetin === fs.readFileSync(RULMAN_YOL, "utf8")) {
    throw new Error("BAYAT HARNESS: mutasyon metni DEGISTIRMEDI: " + mut.ad);
  }
  var dizin = path.join(TMP, "m" + (++sayac));
  fs.mkdirSync(dizin);
  var konfKopya = path.join(dizin, "konfigurator.js");
  fs.writeFileSync(konfKopya, konfMetin);
  try {
    var KONF = require(konfKopya);
    var semalar = {
      rulman: JSON.parse(rulmanMetin),
      vida: JSON.parse(fs.readFileSync(VIDA_YOL, "utf8"))
    };
    var sonuc = VAKA.kosu(KONF, semalar);
    return {
      iddia: sonuc.length,
      kirmiziKodlar: sonuc.filter(function (r) { return !r.ok; })
                          .map(function (r) { return r.kod; }),
      cokme: null
    };
  } catch (e) {
    return { iddia: 0, kirmiziKodlar: [], cokme: String(e && e.message || e) };
  }
}

/* ad · dosya · ara/yeni · bekle ("kirmizi"|"yesil") · kodlar (isaret sarti) */
var MUTANTLAR = [
  // ---- konfigurator.js: kiyas mantigi ----
  { ad: "M01 kiyas yonu ters (< -> >)", dosya: "konf", bekle: "kirmizi",
    ara: "kv < altSinir - KISIT_TOLERANS", yeni: "kv > altSinir + KISIT_TOLERANS",
    kodlar: ["RK01", "RK06", "RK10", "VK01"] },
  { ad: "M02 sinir KAPSAYICI olmaktan cikti (< -> <=)", dosya: "konf", bekle: "kirmizi",
    ara: "kv < altSinir - KISIT_TOLERANS", yeni: "kv <= altSinir + KISIT_TOLERANS",
    kodlar: ["RK05", "VK02"] },
  { ad: "M03 tolerans buyutuldu (1e-6 -> 1e3) = her seyi kabul et", dosya: "konf",
    bekle: "kirmizi", ara: "var KISIT_TOLERANS = 1e-6;", yeni: "var KISIT_TOLERANS = 1e3;",
    kodlar: ["RK01", "RK06", "RK10", "VK01"] },
  // ---- konfigurator.js: dogrusal bicim ----
  { ad: "M04 dogrusal bicimde `sabit` yok sayildi", dosya: "konf", bekle: "kirmizi",
    ara: 'var toplam = (typeof min.sabit === "number") ? min.sabit : 0;',
    yeni: "var toplam = 0;", kodlar: ["RK11"] },
  { ad: "M05 terim katsayisi isaret ters", dosya: "konf", bekle: "kirmizi",
    ara: "toplam += terimler[ad] * v;", yeni: "toplam -= terimler[ad] * v;",
    kodlar: ["RK01", "RK06", "RK10"] },
  { ad: "M06 obje-min kolu tamamen olu (rulman kisiti yok olur)", dosya: "konf",
    bekle: "kirmizi", ara: 'if (!min || typeof min !== "object") { return null; }',
    yeni: "if (min) { return null; }", kodlar: ["RK01", "RK06", "RK10"] },
  { ad: "M07 sayi-min kolu olu (VIDA capasi duser)", dosya: "konf", bekle: "kirmizi",
    ara: 'if (typeof min === "number") { return isFinite(min) ? min : null; }',
    yeni: 'if (typeof min === "number") { return null; }', kodlar: ["VK01"] },
  { ad: "M08 referans parametre fail-open yerine 0 sayildi", dosya: "konf", bekle: "kirmizi",
    ara: 'if (typeof v !== "number" || !isFinite(v)) { return null; }',
    yeni: 'if (typeof v !== "number" || !isFinite(v)) { v = 0; }', kodlar: ["RK18"] },
  // ---- sema: kisit verisi ----
  { ad: "M09 `eger` elemani dusuruldu (makara kisiti herkese)", dosya: "sema",
    bekle: "kirmizi", ara: '"eger": {"eleman": "makara"},', yeni: '"eger": {},',
    kodlar: ["RK04", "RK16"] },
  { ad: "M10 bilya payi genisletildi (-0.24 -> -2.0)", dosya: "sema", bekle: "kirmizi",
    ara: '"sabit": -0.24', yeni: '"sabit": -2.0', kodlar: ["RK12"] },
  { ad: "M11 makara katsayisi bilya katsayisiyla degistirildi", dosya: "sema",
    bekle: "kirmizi",
    ara: '"min": {"terimler": {"dis_cap": 0.31666666666666665, "ic_cap": -0.31666666666666665}}',
    yeni: '"min": {"terimler": {"dis_cap": 0.3333333333333333, "ic_cap": -0.3333333333333333}}',
    kodlar: ["RK05"] },
  { ad: "M12 makara kisiti tamamen silindi", dosya: "sema", bekle: "kirmizi",
    ara: '"eger": {"eleman": "makara"},', yeni: '"eger": {"eleman": "__yok__"},',
    kodlar: ["RK01", "RK06", "RK08"] },
  // ---- KONTROL MUTANTLARI: davranis korunur -> YESIL kalmali ----
  { ad: "K01 KONTROL: yerel degisken adi degisti (davranis ayni)", dosya: "konf",
    bekle: "yesil", ara: "var toplam = (typeof min.sabit", yeni: "var _t = (typeof min.sabit",
    kodlar: [], ek: [["toplam += terimler[ad] * v;", "_t += terimler[ad] * v;"],
                     ["return isFinite(toplam) ? toplam : null;", "return isFinite(_t) ? _t : null;"]] },
  { ad: "K02 KONTROL: yalniz yorum satiri degisti", dosya: "konf", bekle: "yesil",
    ara: "// ---- kisit alt siniri ---", yeni: "// ---- kisit alt siniri (yorum) ---",
    kodlar: [] }
];

// K01 birden fazla yer degistirir; kos() tek `ara` alir -> ek degisiklikleri uygula.
function kosGenis(mut) {
  if (!mut.ek) { return kos(mut); }
  var konfMetin = fs.readFileSync(KONF_YOL, "utf8");
  if (konfMetin.indexOf(mut.ara) < 0) {
    throw new Error("BAYAT HARNESS: " + mut.ad + " dayanagi yok: " + mut.ara);
  }
  konfMetin = konfMetin.replace(mut.ara, mut.yeni);
  mut.ek.forEach(function (p) {
    if (konfMetin.indexOf(p[0]) < 0) {
      throw new Error("BAYAT HARNESS: " + mut.ad + " ek dayanagi yok: " + p[0]);
    }
    konfMetin = konfMetin.replace(p[0], p[1]);
  });
  var dizin = path.join(TMP, "m" + (++sayac));
  fs.mkdirSync(dizin);
  var kopya = path.join(dizin, "konfigurator.js");
  fs.writeFileSync(kopya, konfMetin);
  try {
    var sonuc = VAKA.kosu(require(kopya), {
      rulman: JSON.parse(fs.readFileSync(RULMAN_YOL, "utf8")),
      vida: JSON.parse(fs.readFileSync(VIDA_YOL, "utf8"))
    });
    return { iddia: sonuc.length,
             kirmiziKodlar: sonuc.filter(function (r) { return !r.ok; })
                                 .map(function (r) { return r.kod; }), cokme: null };
  } catch (e) { return { iddia: 0, kirmiziKodlar: [], cokme: String(e.message || e) }; }
}

// ---- TABAN KOSUM (iddia sayisi burada OLCULUR, koda yazilmaz) ----
var taban = kos({ ad: "taban", dosya: "yok" });
if (taban.cokme) {
  console.error("TABAN KOSUM COKTU: " + taban.cokme);
  process.exit(1);
}
console.log("TABAN: %d iddia, %d kirmizi", taban.iddia, taban.kirmiziKodlar.length);
if (taban.kirmiziKodlar.length !== 0) {
  console.error("TABAN KIRMIZI (mutasyon olculemez): " + taban.kirmiziKodlar.join(","));
  process.exit(1);
}

var yakalanan = 0, kacan = [], bozuk = [];
MUTANTLAR.forEach(function (mut) {
  var r = kosGenis(mut);
  var kod;
  if (r.cokme) {
    kod = "COKME";                       // cokme KIRMIZI SAYILMAZ
  } else if (r.iddia !== taban.iddia) {
    kod = "EKSIK(" + r.iddia + "/" + taban.iddia + ")";
  } else if (r.kirmiziKodlar.length === 0) {
    kod = "YESIL";
  } else {
    var eksik = mut.kodlar.filter(function (k) { return r.kirmiziKodlar.indexOf(k) < 0; });
    kod = eksik.length ? "ISARET-YOK(" + eksik.join(",") + ")" : "KIRMIZI";
  }
  var basarili = (mut.bekle === "kirmizi") ? (kod === "KIRMIZI") : (kod === "YESIL");
  if (basarili) {
    yakalanan++;
  } else if (mut.bekle === "kirmizi") {
    kacan.push(mut.ad + " -> " + kod);
  } else {
    bozuk.push(mut.ad + " -> " + kod);
  }
  // NOT: Node'un console.log bicimlendiricisi genislik belirteci (%-52s) DESTEKLEMEZ
  // — dolgu elle yapilir, aksi halde satirlar okunamaz hale gelir.
  function dol(s, n) { s = String(s); return s + " ".repeat(Math.max(0, n - s.length)); }
  console.log("  " + (basarili ? "+" : "-") + " " + dol(mut.ad, 54) +
              "bekle=" + dol(mut.bekle, 9) + "sonuc=" + dol(kod, 24) +
              "kirmizi=[" + r.kirmiziKodlar.join(",") + "]");
});

// ---- KAYNAK BUTUNLUGU: mutasyon canli dosyaya sizmadi mi? ----
var bitis = { konf: sha(KONF_YOL), rulman: sha(RULMAN_YOL) };
var sizinti = (bitis.konf !== BASLANGIC.konf) || (bitis.rulman !== BASLANGIC.rulman);
fs.rmSync(TMP, { recursive: true, force: true });

var oldurulecek = MUTANTLAR.filter(function (m) { return m.bekle === "kirmizi"; }).length;
var kontrol = MUTANTLAR.length - oldurulecek;
console.log("\nSONUC: %d/%d mutant yakalandi (%d kontrol mutanti yesil kalmali)",
            yakalanan, MUTANTLAR.length, kontrol);
if (kacan.length) { console.log("KACAN (nobetci bunlari GORMUYOR):\n  " + kacan.join("\n  ")); }
if (bozuk.length) { console.log("KONTROL MUTANTI KIRMIZI YANDI (yanlis alarm):\n  " + bozuk.join("\n  ")); }
if (sizinti) { console.log("🔴 KAYNAK DEGISTI — mutant canli dosyaya sizdi!"); }
console.log("kaynak butunlugu: %s", sizinti ? "BOZUK" : "SAGLAM (sha256 basta=sonda)");
process.exit((kacan.length || bozuk.length || sizinti) ? 1 : 0);
