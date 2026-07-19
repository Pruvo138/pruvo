#!/usr/bin/env node
"use strict";
// ============================================================================
// MARKA ÇİP 32-CAP BİRİM TESTİ  (node tools/marka-limit-test.js)
// ----------------------------------------------------------------------------
// index.html renderBrands mantığını birebir yansıtır: brandCounts + sortedBrands
// + slice(0, MARKA_LIMIT) + aktif-marka koruma. Kural HEM ana sayfada HEM kategori
// seçiliyken çip evrenini en çok ürünlü ilk 32 marka ile sınırlar; 33+ uzun kuyruk
// marka çip DEĞİL (yalnız arama). "Tümü" çipi (filtre sıfırlama) her zaman kalır.
//
// Ayrıca kaynak dosyayı (index.html) tarayıp cap'in gerçekten orada olduğunu
// doğrular → biri cap'i kaldırıp eski "daha fazla göster" mekanizmasına dönerse
// bu test KIRMIZI olur (kırmızı-kanıt). Alt tarafta ayrıca mutasyon kanıtı var:
// cap kaldırılınca (Infinity) 32-invariantı bozulur.
// ============================================================================
const fs = require("fs");
const path = require("path");

const MARKA_LIMIT = 32; // index.html ile aynı sabit

// ---- index.html'deki norm/haystack'in birebir kopyası ----
function norm(s){
  return (s || "").toLocaleLowerCase("tr")
    .replace(/ı/g,"i").replace(/İ/g,"i")
    .replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ö/g,"o")
    .replace(/ş/g,"s").replace(/ü/g,"u").replace(/â/g,"a").replace(/î/g,"i");
}
function haystack(p){
  return norm([p.baslik, p.aciklama, (p.marka||[]).join(" "),
               p.kategori, (p.id||"").replace(/-/g," ")].join(" "));
}
// ---- index.html brandCounts / sortedBrands birebir ----
function brandCounts(products, activeCat, query){
  const tokens = norm(query).split(/\s+/).filter(Boolean);
  const counts = {};
  products.forEach(function(p){
    if(activeCat !== "Tümü" && p.kategori !== activeCat){ return; }
    if(tokens.length){
      const hs = haystack(p);
      for(let i=0;i<tokens.length;i++){ if(hs.indexOf(tokens[i]) === -1){ return; } }
    }
    (p.marka || []).forEach(function(b){ counts[b] = (counts[b] || 0) + 1; });
  });
  return counts;
}
function sortedBrands(products, activeCat, query){
  const counts = brandCounts(products, activeCat, query);
  return Object.keys(counts).sort(function(a, b){
    if(counts[b] !== counts[a]){ return counts[b] - counts[a]; }
    return a.localeCompare(b, "tr");
  });
}
// ---- renderBrands'in ürettiği çip listesi (ilk eleman DAİMA "Tümü") ----
// cap parametresi test/mutasyon içindir; üretimde MARKA_LIMIT'tir.
function renderChips(products, opts, cap){
  opts = opts || {};
  const activeCat   = opts.activeCat   || "Tümü";
  const query       = opts.query       || "";
  const activeBrand = opts.activeBrand || "Tümü";
  const out = ["Tümü"];
  const brands = sortedBrands(products, activeCat, query);
  let visible = brands.slice(0, cap);
  if(activeBrand !== "Tümü" &&
     visible.indexOf(activeBrand) === -1 && brands.indexOf(activeBrand) !== -1){
    visible = visible.concat([activeBrand]);
  }
  return out.concat(visible);
}
const chipsNoTumu = (list) => list.filter((m) => m !== "Tümü");

// ---- test altyapısı ----
let pass = 0, fail = 0;
function ok(cond, msg){
  if(cond){ pass++; console.log("  PASS  " + msg); }
  else    { fail++; console.log("  FAIL  " + msg); }
}
function eqArr(a, b){ return a.length === b.length && a.every((x, i) => x === b[i]); }

// ---- fixture üreteçleri ----
// Bk markası (41-k) üründe → B01=40 ... B40=1 (ürün sayısına göre kesin sıra).
function fixtureN(n, kategori, prefix){
  kategori = kategori || "Otomobil"; prefix = prefix || "B";
  const products = [];
  for(let k = 1; k <= n; k++){
    const brand = prefix + String(k).padStart(2, "0");
    const count = (n + 1) - k; // B01 en çok
    for(let j = 0; j < count; j++){
      products.push({ id: brand + "-" + j, kategori, marka: [brand],
                      baslik: brand + " parca " + j, aciklama: "aciklama" });
    }
  }
  return products;
}
function topBrands(n, prefix){
  prefix = prefix || "B";
  const out = [];
  for(let k = 1; k <= n; k++){ out.push(prefix + String(k).padStart(2, "0")); }
  return out;
}

console.log("MARKA 32-CAP BİRİM TESTİ\n");

// 1) Ana sayfa (Tümü, arama yok), 40 marka → tam 32 çip + "Tümü"
(function(){
  const P = fixtureN(40);
  const chips = renderChips(P, { activeCat: "Tümü" }, MARKA_LIMIT);
  const brandsOnly = chipsNoTumu(chips);
  ok(brandsOnly.length === 32, "Ana sayfa 40 marka → tam 32 çip (bulundu " + brandsOnly.length + ")");
  ok(eqArr(brandsOnly, topBrands(32)), "Ana sayfa çipleri = ürün sayısına göre ilk 32 (B01..B32)");
  ok(brandsOnly.indexOf("B33") === -1, "33. marka (B33) çip DEĞİL");
  ok(chips[0] === "Tümü", "İlk çip 'Tümü' (filtre sıfırlama) korunur");
})();

// 2) ≤32 marka → hepsi gösterilir
(function(){
  const P = fixtureN(10);
  const chips = renderChips(P, { activeCat: "Tümü" }, MARKA_LIMIT);
  const brandsOnly = chipsNoTumu(chips);
  ok(brandsOnly.length === 10, "10 marka → 10 çip (cap altında hepsi)");
  ok(eqArr(brandsOnly, topBrands(10)), "10 marka sırası doğru");
})();

// tam 32 sınır
(function(){
  const P = fixtureN(32);
  const brandsOnly = chipsNoTumu(renderChips(P, { activeCat: "Tümü" }, MARKA_LIMIT));
  ok(brandsOnly.length === 32, "Tam 32 marka → 32 çip (sınır)");
})();

// 3) Kategori seçili → o kategorinin markaları, 32-cap
(function(){
  const oto = fixtureN(40, "Otomobil", "O");   // 40 Otomobil markası
  const mar = fixtureN(35, "Marin", "M");       // 35 Marin markası
  const P = oto.concat(mar);
  const marinChips = chipsNoTumu(renderChips(P, { activeCat: "Marin" }, MARKA_LIMIT));
  ok(marinChips.length === 32, "Kategori(Marin) 35 marka → tam 32 çip");
  ok(eqArr(marinChips, topBrands(32, "M")), "Kategori çipleri o kategoriden ilk 32 (M01..M32)");
  ok(marinChips.every((m) => m.startsWith("M")), "Kategori çipleri BAŞKA kategoriden marka sızdırmaz");
})();

// 4) Sıralama ürün sayısına göre azalan (eşitlikte alfabetik-tr)
(function(){
  // A=3, B=3, C=5 ürün → sıra: C, A, B  (C en çok; A/B eşit → alfabetik)
  const P = [];
  ["A","A","A","B","B","B","C","C","C","C","C"].forEach((b, i) =>
    P.push({ id: b + i, kategori: "Otomobil", marka: [b], baslik: b, aciklama: "" }));
  const brandsOnly = chipsNoTumu(renderChips(P, { activeCat: "Tümü" }, MARKA_LIMIT));
  ok(eqArr(brandsOnly, ["C","A","B"]), "Sıra ürün-sayısı azalan + eşitlikte alfabetik (C,A,B)");
})();

// 5) Aktif marka cap dışındaysa (URL ?marka= / arama sonrası) çip kaybolmaz
(function(){
  const P = fixtureN(40);
  const chips = renderChips(P, { activeCat: "Tümü", activeBrand: "B40" }, MARKA_LIMIT);
  const brandsOnly = chipsNoTumu(chips);
  ok(brandsOnly.indexOf("B40") !== -1, "Seçili cap-dışı marka (B40) çip olarak korunur");
  ok(brandsOnly.length === 33, "32 + seçili cap-dışı marka = 33 çip");
})();

// 6) Arama kutusu davranışı değişmez: uzun-kuyruk marka aranınca sonuç gelir (brandCounts filtresi)
(function(){
  const P = fixtureN(40);
  // B37 nadir marka; başlığında geçen 'b37' aranınca brandCounts B37 sayar
  const counts = brandCounts(P, "Tümü", "B37");
  ok((counts["B37"] || 0) > 0, "Uzun-kuyruk marka arama ile bulunur (B37 sayısı > 0)");
})();

// 7) MUTASYON / KIRMIZI-KANIT: cap kaldırılınca (Infinity) 32-invariant bozulur
(function(){
  const P = fixtureN(40);
  const capped   = chipsNoTumu(renderChips(P, { activeCat: "Tümü" }, MARKA_LIMIT));
  const uncapped = chipsNoTumu(renderChips(P, { activeCat: "Tümü" }, Infinity));
  ok(capped.length === 32 && uncapped.length === 40 && uncapped.length !== capped.length,
     "MUTASYON: cap yokken 40 çip → cap 32-invariantını bozar (test bunu yakalar)");
})();

// 8) KAYNAK KUPLAJI: index.html gerçekten cap içeriyor, eski mekanizma yok
(function(){
  const src = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  ok(/MARKA_LIMIT\s*=\s*32/.test(src), "index.html: MARKA_LIMIT = 32 var");
  ok(src.indexOf("slice(0, MARKA_LIMIT)") !== -1, "index.html: brands.slice(0, MARKA_LIMIT) uygulanıyor");
  ok(src.indexOf("BRAND_COLLAPSED") === -1, "index.html: eski BRAND_COLLAPSED kaldırıldı");
  ok(src.indexOf("MIN_BRAND_HOME") === -1, "index.html: eski MIN_BRAND_HOME kaldırıldı");
  ok(src.indexOf("brandsExpanded") === -1, "index.html: eski brandsExpanded kaldırıldı");
  ok(src.indexOf("brand-more") === -1, "index.html: eski 'daha fazla göster' (brand-more) kaldırıldı");
})();

console.log("\nSONUÇ: " + pass + " geçti, " + fail + " kaldı.");
process.exit(fail === 0 ? 0 : 1);
