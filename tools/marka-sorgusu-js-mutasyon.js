#!/usr/bin/env node
"use strict";
// ============================================================================
// MUTASYON KANITI — marka-sorgusu-js-test.js gerçekten ölçüyor mu?
//   node tools/marka-sorgusu-js-mutasyon.js
// ----------------------------------------------------------------------------
// K133'ün kabul kırmızısı tam buydu: index.html değiştirildi ama değişikliği ölçen
// test yoktu, yani mutantlar hayatta kalıyordu. Bu sürücü index.html'in GEÇİCİ BİR
// KOPYASINA mutasyon uygular ve testi o kopyaya karşı koşar.
//
// 🔴 MUTASYON DAİMA KOPYAYA: çalışma ağacındaki index.html'e DOKUNULMAZ
// ([[mutasyon-diske-yazma-tuzagi]]). Kopya işin sonunda SİLİNİR ([[diskte-iz-birakma-yasagi]]).
// KONTROL koşumu (mutasyonsuz kopya) YEŞİL olmalı — aksi halde kırmızılar mutasyondan
// değil kopyalama kusurundan gelirdi ve kanıt sahte olurdu ([[fikstur-degeri-mutasyon-koru]]).
// ============================================================================
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.dirname(__dirname);
const INDEX = path.join(ROOT, "index.html");
const TEST = path.join(ROOT, "tools", "marka-sorgusu-js-test.js");

const kaynak = fs.readFileSync(INDEX, "utf8");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-marka-mut-"));

function kos(icerik) {
  const yol = path.join(tmp, "index.html");
  fs.writeFileSync(yol, icerik, "utf8");
  try {
    execFileSync("node", [TEST], {
      env: Object.assign({}, process.env, { PRUVO_INDEX_YOLU: yol }),
      stdio: "pipe"
    });
    return 0;
  } catch (e) {
    return typeof e.status === "number" ? e.status : 99;
  }
}

// --- mutantlar: [ad, uygula(kaynak) → yeni kaynak | null] --------------------
const MUTANTLAR = [
  ["M1 yedek liste ham uyelige geri (`:4389` sinifi)", function (s) {
    // Son `markaSorgusuEsler(p, hedefMarka);` çağrısını ham üyeliğe döndür.
    const ix = s.lastIndexOf("return markaSorgusuEsler(p, hedefMarka);");
    if (ix === -1) { return null; }
    return s.slice(0, ix) +
      "return (p.marka || []).some(function(b){ return markaKatla(b) === hedefMarka; });" +
      s.slice(ix + "return markaSorgusuEsler(p, hedefMarka);".length);
  }],
  ["M2 uzun-once etkisiz (azami kelime 3 → 1)", function (s) {
    if (s.indexOf("var MARKA_BASLIK_AZAMI_KELIME = 3;") === -1) { return null; }
    return s.replace("var MARKA_BASLIK_AZAMI_KELIME = 3;", "var MARKA_BASLIK_AZAMI_KELIME = 1;");
  }],
  ["M3 baslik kolu tek govdeden sokuldu", function (s) {
    const eski = "return markaUyeMi(p, hedefMarka) || baslikMarkalari(p).indexOf(hedefMarka) !== -1;";
    if (s.indexOf(eski) === -1) { return null; }
    return s.replace(eski, "return markaUyeMi(p, hedefMarka);");
  }],
  ["M4 cip filtresi ham uyelige geri (`:3574` sinifi)", function (s) {
    const eski = "var brandOk = !hedefMarka || markaSorgusuEsler(p, hedefMarka);";
    if (s.indexOf(eski) === -1) { return null; }
    return s.replace(eski, "var brandOk = !hedefMarka || markaUyeMi(p, hedefMarka);");
  }]
];

console.log("MUTASYON KANITI — marka-sorgusu-js-test.js");

// KONTROL: mutasyonsuz kopya YEŞİL olmalı (kopyalama kusuru kırmızıyı taklit etmesin)
const kontrolRc = kos(kaynak);
console.log("  KONTROL (mutasyonsuz kopya) rc=" + kontrolRc + (kontrolRc === 0 ? " ✅" : " ❌"));

let olen = 0;
const hayatta = [];
MUTANTLAR.forEach(function (m) {
  const yeni = m[1](kaynak);
  if (yeni === null) {
    hayatta.push(m[0] + " (CAPA BULUNAMADI — mutant uygulanamadi)");
    console.log("  " + m[0] + ": CAPA YOK ❓");
    return;
  }
  const rc = kos(yeni);
  if (rc === 1) {
    olen += 1;
    console.log("  " + m[0] + ": OLDU (rc=1) ✅");
  } else {
    hayatta.push(m[0] + " (rc=" + rc + ")");
    console.log("  " + m[0] + ": HAYATTA (rc=" + rc + ") ❌");
  }
});

// TEMİZLİK — üreten temizler ([[diskte-iz-birakma-yasagi]])
fs.rmSync(tmp, { recursive: true, force: true });
console.log("  TEMIZLIK: gecici kopya silindi (" + tmp + " var mi: " +
  (fs.existsSync(tmp) ? "EVET" : "hayir") + ")");

console.log("");
console.log("MUTANT=" + olen + "/" + MUTANTLAR.length + "  KONTROL=" +
  (kontrolRc === 0 ? "YESIL" : "KIRMIZI"));
if (kontrolRc !== 0 || olen !== MUTANTLAR.length) {
  hayatta.forEach(function (h) { console.log("  HAYATTA: " + h); });
  console.log("SONUC: KALDI ❌");
  process.exit(1);
}
console.log("SONUC: GECTI ✅");
process.exit(0);
