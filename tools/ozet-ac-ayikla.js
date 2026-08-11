"use strict";
/**
 * PRUVO — index.html'in CANLI `ozetAc` cozucusunu ayiklama (ORTAK yardimci).
 *
 * NEDEN VAR ([[ikiz-tanim-sessiz-ayrisma]]): ozet.json'un kart temsilini ACAN kod
 * index.html icinde YASAR. Testler o cozucunun KOPYASINI tutarsa (tools/vitrin-siralama-
 * test.js'te tuttugu gibi) temsil degistigi gun iki taraf SESSIZCE ayrisir: test kendi
 * kopyasiyla dogru acar, ziyaretcinin tarayicisi yanlis acar ve ekranda hata gorunmez.
 * Bu yardimci CANLI dosyanin kendi fonksiyonunu calistirilabilir olarak dondurur —
 * ikinci kopya YOK.
 *
 * FAIL-CLOSED: capa bulunamaz ya da govde ayristirilamazsa ISTISNA atar. "Cozemedim =
 * eski cozucuye don" sessiz gecisi YASAK (o hal, degisen temsili olcmeden yesil verirdi).
 */

const fs = require("node:fs");
const path = require("node:path");

const CAPA = "function ozetAc(d){";

/** Kaynak metinden `ozetAc` govdesini (fonksiyon metni) suslu parantez sayarak ayiklar. */
function ozetAcKaynagi(html) {
  const bas = String(html).indexOf(CAPA);
  if (bas === -1) {
    throw new Error("OLCULEMEDI: index.html'de `" + CAPA + "` capasi YOK — ozet cozucusu " +
      "yeniden adlandirilmis/kaldirilmis olabilir.");
  }
  let derinlik = 0;
  for (let i = bas + CAPA.length - 1; i < html.length; i++) {
    const c = html[i];
    if (c === "{") { derinlik++; } else if (c === "}") {
      derinlik--;
      if (derinlik === 0) { return html.slice(bas, i + 1); }
    }
  }
  throw new Error("OLCULEMEDI: `ozetAc` govdesi kapanmadi (index.html bozuk?).");
}

/**
 * @param {string} [indexYolu] varsayilan: depo kokundeki index.html
 * @returns {(d:any)=>any} canli ozetAc
 */
function ozetAcAl(indexYolu) {
  const yol = indexYolu || path.join(path.dirname(__dirname), "index.html");
  const kaynak = ozetAcKaynagi(fs.readFileSync(yol, "utf8"));
  // eslint-disable-next-line no-new-func
  return new Function("\"use strict\";" + kaynak + "\nreturn ozetAc;")();
}

module.exports = { ozetAcAl, ozetAcKaynagi, CAPA };
