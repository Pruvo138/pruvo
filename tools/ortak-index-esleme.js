/**
 * ORTAK — index.html'deki GORUNEN-ETIKET eslemesinin AYIKLANMASI (tek kaynak).
 *
 * NEDEN VAR (11 Agu 2026, olculdu): gizli seri adi musteriye gorunen yuzeylerden
 * kaldirilinca `syncUrl()` `?kategori=` yazarken `gorunurKategori(activeCat)` cagirmaya
 * basladi. index.html'in bir DILIMINI sandbox'ta kosturan testler bu bagimliligi
 * tanimadigi icin ham `ReferenceError: gorunurKategori is not defined` ile COKTU
 * (tools/url-senkron-test.js ve tools/reklam-url-test.js — ikisi de ayni gun).
 *
 * 🔴 BAGIMLILIK STUB'LANMAZ: index.html'deki GERCEK tablo + fonksiyon ayiklanip sandbox
 * govdesinin basina konur. Stub konsaydi esleme bozuldugunda test YESIL kalirdi; gercegi
 * ayiklaninca test eslemenin kendisini de olcer.
 *
 * 🔴 IKINCI KOPYA YOK: bu ayiklama once iki teste AYRI AYRI yazilmisti. Ayni sinif bu
 * depoda daha once de tekrarladi (onizleme/ kapilarindaki ikiz renk-markup capasi ayni
 * gun IKI kapiyi birden kirdi) -> [[ikiz-tanim-sessiz-ayrisma]]. Capa TEK yerde durur.
 *
 * FAIL-CLOSED: ayiklanamazsa null doner; cagiran test bunu KIRMIZI bir iddiaya cevirmek
 * ZORUNDADIR (sessizce bos onek eklemek, esleme kaybolunca testi yesil birakirdi).
 * BOSLUGA TOLERANSLI: capa bicimlendirmeye degil YAPIYA bakar.
 */
"use strict";

/**
 * @param {string} INDEX index.html'in tam metni
 * @returns {string|null} `var KATEGORI_GORUNUR = {...}; ... function gorunurKategori(c){...}`
 *   dilimi, ya da ayiklanamazsa null.
 */
function gorunurKategoriKaynagi(INDEX) {
  const m = String(INDEX).match(
    /var\s+KATEGORI_GORUNUR\s*=\s*\{[^;]*\};[\s\S]{0,600}?function\s+gorunurKategori\s*\(\s*c\s*\)\s*\{[\s\S]*?\n {2}\}/);
  return m ? m[0] : null;
}

/** Sandbox govdesinin basina konacak onek (kaynak + noktali virgul + satir sonu). */
function gorunurKategoriOneki(INDEX) {
  const src = gorunurKategoriKaynagi(INDEX);
  return src === null ? null : src + ";\n";
}

module.exports = { gorunurKategoriKaynagi, gorunurKategoriOneki };
