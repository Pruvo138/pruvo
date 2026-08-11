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

/**
 * 🔴 CAPA BOSLUGA DUYARSIZ (12 Agu 2026, curutucu bulgusu). Eski capa duz dize
 * ("function ozetAc(d){") idi: `function ozetAc (d){` gibi DAVRANISI HIC DEGISTIRMEYEN
 * bir bosluk, ayiklamayi "capa YOK" diye fail-closed dusuruyordu. Sonuc SAHTE KIRMIZI —
 * ve mutasyon bataryasi bu rc'yi "mutant yakalandi" diye kredilendiriyordu (sahte kredi).
 * Gevseme DEGIL: fonksiyon GERCEKTEN yoksa/yeniden adlandirilmissa capa yine tutmaz ve
 * ISTISNA atilir.
 */
const CAPA_DESEN = /function\s+ozetAc\s*\(\s*[A-Za-z_$][\w$]*\s*\)\s*\{/;
const CAPA = "function ozetAc(d){";     // insan okunur etiket (hata metni + belge)

/** Kaynak metinden `ozetAc` govdesini (fonksiyon metni) suslu parantez sayarak ayiklar. */
function ozetAcKaynagi(html) {
  const m = CAPA_DESEN.exec(String(html));
  if (!m) {
    throw new Error("OLCULEMEDI: index.html'de `" + CAPA + "` capasi YOK — ozet cozucusu " +
      "yeniden adlandirilmis/kaldirilmis olabilir.");
  }
  const bas = m.index;
  let derinlik = 0;
  for (let i = bas + m[0].length - 1; i < html.length; i++) {
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

module.exports = { ozetAcAl, ozetAcKaynagi, CAPA, CAPA_DESEN };

/**
 * CLI KOLU — Python tarafindaki nobetciler (tools/edge-kart-kapisi.py) ozet artefaktini
 * CANLI istemci cozucusunden gecirebilsin diye:
 *     node tools/ozet-ac-ayikla.js --ac <artefakt.json> [--index <index.html>]
 * stdout'a {"parametrik":[...],"bloklar":{...},"yeni":[...],"yeniCozulemeyen":n} basar.
 * IKINCI KOPYA ACMAMAK icin burada durur: cozucu yine canli dosyadan ayiklanir.
 * Hata halinde exit 2 (OLCULEMEDI) — "cozemedim = sorun yok" sessiz gecisi YOK.
 */
if (require.main === module) {
  const arg = (ad) => {
    const i = process.argv.indexOf(ad);
    return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : null;
  };
  const acYol = arg("--ac");
  if (!acYol) {
    console.error("kullanim: node tools/ozet-ac-ayikla.js --ac <artefakt.json> [--index <yol>]");
    process.exit(2);
  }
  try {
    const ac = ozetAcAl(arg("--index") || undefined);
    const d = ac(JSON.parse(fs.readFileSync(acYol, "utf8")));
    process.stdout.write(JSON.stringify({
      parametrik: d.parametrik || [],
      bloklar: d.bloklar || {},
      yeni: d.yeni || [],
      yeniCozulemeyen: d.yeniCozulemeyen || 0,
    }));
  } catch (e) {
    console.error("OLCULEMEDI: " + (e && e.message ? e.message : String(e)));
    process.exit(2);
  }
}
