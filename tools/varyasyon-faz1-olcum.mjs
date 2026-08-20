/* VARYASYON PROGRAMI — FAZ 1 CANLI ZINCIR OLCUMU (paket-varyasyon-programi.md §FAZ 1)
 *
 * NE OLCER: `boy_secenekleri` rayinin BUGUN calistigi. ONARIM DEGIL, OLCUM.
 * Bes eksen, hepsi SAYIYLA. Cache-bust YOK (`?cb=`/`?v=` EKLENMEZ).
 *
 *   (1) kanonik adreste secici GORUNUYOR      -> canli HTML sayimi
 *   (2) secim degisince gosterilen fiyat +100 -> istemci kolu (secenekler.js boyFarki) + MUTANT
 *   (3) sepete/siparise giden istek ETIKET tasiyor -> canli sayfa varligi + canli /fiyat ucu
 *   (4) shop ucu ayni farki SUNUCUDA hesapliyor -> canli POST /api/shop/fiyat, istemci fiyatina
 *       guvenilmedigi TAMPER vakasiyla civilenir
 *   (5) D1 kolonu bu iki urun icin DOLU        -> (4)'un cevabindan TURETILIR (sunucu kolonu
 *       YALNIZ D1'den okur: shop/src/index.js:278 EK_KOLONLAR + :350) + d1-sync --durum
 *
 * ANTI-TAUTOLOJI: her iddia OKUDUGU HAM DEGERI basar; (2) hedef kolu olduren MUTANT ve onu
 * oldurmeyen KONTROL mutantiyla civilenir; (4) negatif vakalar + TAMPER vakasi tasir.
 *
 * KULLANIM:  node tools/varyasyon-faz1-olcum.mjs            (tam olcum)
 *            node tools/varyasyon-faz1-olcum.mjs --ic <mod> (ic alt-surec; elle cagirma)
 *
 * YAN ETKI: YOK. Yalniz GET (canli sayfa) + POST /api/shop/fiyat (uc "yan etkisiz prova"
 * olarak tasarlandi: siparis olusmaz, D1 yazmasi yoktur — shop/src/index.js:732-747).
 * Gecici dosya: os.tmpdir() altinda, tur sonunda SILINIR (disk kurali).
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const KOK = path.resolve(BURASI, "..");
const BU_DOSYA = fileURLToPath(import.meta.url);

const SITE = "https://pruvo3d.com";
const FIYAT_UC = SITE + "/api/shop/fiyat";

const HEDEF = [
  { id: "vw-t5-dugme-yuvasi-kor-kapagi", taban: "Tekli", varyant: "Uzun", fark_tl: 100 },
  { id: "pr634138-volvo-besik-burcu-takma-aleti", taban: "Kovan", varyant: "Pimli", fark_tl: 235 },
];

let GECTI = 0, KALDI = 0, OLCULEMEDI = 0;
const SATIRLAR = [];

function yaz(s) { SATIRLAR.push(s); console.log(s); }

/** Tek iddia. `ham` = OKUNAN deger (tautoloji kalkani: iddia adi degil SAYI kalir). */
function iddia(ad, kosul, ham) {
  if (kosul) { GECTI += 1; yaz("  OK   " + ad + "  |  ham=" + ham); }
  else { KALDI += 1; yaz("  RED  " + ad + "  |  ham=" + ham); }
  return kosul;
}
function olculemedi(ad, sebep, kapatan) {
  OLCULEMEDI += 1;
  yaz("  OLCULEMEDI  " + ad);
  yaz("      sebep : " + sebep);
  yaz("      kapatan: " + kapatan);
}

function kacKez(govde, parca) {
  if (!parca) return 0;
  let n = 0, i = 0;
  for (;;) { const k = govde.indexOf(parca, i); if (k < 0) break; n += 1; i = k + parca.length; }
  return n;
}

async function getir(url) {
  const c = await fetch(url, { headers: { "User-Agent": "pruvo-faz1-olcum" } });
  return { kod: c.status, govde: await c.text() };
}

async function fiyatSor(sepet) {
  const c = await fetch(FIYAT_UC, {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": "pruvo-faz1-olcum" },
    body: JSON.stringify({ sepet }),
  });
  let veri = null;
  const metin = await c.text();
  try { veri = JSON.parse(metin); } catch (e) { /* ham metin asagida rapor edilir */ }
  return { kod: c.status, veri, metin };
}

const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

/* ============================ IC ALT-SUREC: istemci kolu ============================
 * Ayri surecte kosar: secenekler.js bir IIFE olup globalThis'e yazar, modul onbellegi
 * mutant ile taban arasinda TASINAMAZ. `--ic taban` gercek dosyayi, `--ic mutant-hedef`
 * ve `--ic mutant-kontrol` yamali kopyayi yukler; STDOUT'a tek satir JSON basar. */
function icKolCalistir(mod, dosya) {
  const cikti = execFileSync(process.execPath, [BU_DOSYA, "--ic", mod, dosya], {
    encoding: "utf8", timeout: 60000,
  });
  return JSON.parse(cikti.trim().split("\n").pop());
}

function icKol(secenekYolu) {
  const require = createRequire(import.meta.url);
  require(secenekYolu);                       // IIFE -> globalThis.PRUVO_SECENEK
  const S = globalThis.PRUVO_SECENEK;
  const urunler = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));
  const cikti = {};
  for (const h of HEDEF) {
    const u = urunler.find((x) => x.id === h.id);
    if (!u) { cikti[h.id] = { hata: "urun-yok" }; continue; }
    const urun = { kategori: u.kategori, fiyat: u.fiyat, parametrik: false,
                   boy_secenekleri: u.boy_secenekleri || [], tur: u.tur };
    const oz = (etiket) => S.satirOzeti(urun,
      { id: u.id, malzeme: "PLA", renk: "Siyah", renk_ozel: "", boy_etiket: etiket, adet: 1 });
    const a = oz(h.taban), b = oz(h.varyant);
    cikti[h.id] = {
      taban_kurus: a.birimKurus, varyant_kurus: b.birimKurus,
      delta_kurus: b.birimKurus - a.birimKurus,
      taban_metin: a.birimMetni, varyant_metin: b.birimMetni,
      detay_taban: a.detay, detay_varyant: b.detay,
      // KONTROL EKSENI: malzeme farki hala calisiyor mu? (kontrol mutantinin hedefi)
      petg_delta: oz(h.taban) && S.satirOzeti(urun,
        { id: u.id, malzeme: "PETG", renk: "Siyah", renk_ozel: "", boy_etiket: h.taban, adet: 1 }
      ).birimKurus - a.birimKurus,
    };
  }
  console.log(JSON.stringify(cikti));
}

/* mutant agaci: secenekler.js'in TEK satirini degistirip gecici kopyaya yazar */
function mutantYaz(tmp, ad, eski, yeni) {
  const kaynak = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");
  const n = kacKez(kaynak, eski);
  if (n !== 1) return { hata: "capa tekil degil (bulunan=" + n + ")", capa: eski };
  const yol = path.join(tmp, "secenekler-" + ad + ".js");
  fs.writeFileSync(yol, kaynak.replace(eski, yeni), "utf8");
  return { yol };
}

/* ================================== EKSENLER ================================== */

async function eksen1ve3Sayfa(h) {
  yaz("");
  yaz("EKSEN (1) + (3-istemci) — kanonik adres: " + SITE + "/urun/" + h.id + "/");
  let s;
  try { s = await getir(SITE + "/urun/" + h.id + "/"); }
  catch (e) {
    olculemedi("(1) canli sayfa " + h.id,
      "ag hatasi: " + e.message,
      "aglı bir kabuktan ayni komutu kosmak");
    return null;
  }
  iddia("(1a) HTTP 200", s.kod === 200, "kod=" + s.kod + " bayt=" + s.govde.length);
  if (s.kod !== 200) return null;
  iddia("(1b) <select id=\"boySec\"> sayfada TEK",
        kacKez(s.govde, 'id="boySec"') === 1, kacKez(s.govde, 'id="boySec"'));
  const optTaban = '<option value="' + h.taban + '">' + h.taban + "</option>";
  const optVar = '<option value="' + h.varyant + '">' + h.varyant + " (+" + h.fark_tl + " TL)</option>";
  iddia("(1c) taban option '" + h.taban + "' birebir",
        kacKez(s.govde, optTaban) === 1, kacKez(s.govde, optTaban) + " x " + JSON.stringify(optTaban));
  iddia("(1d) varyant option '" + h.varyant + " (+" + h.fark_tl + " TL)' birebir",
        kacKez(s.govde, optVar) === 1, kacKez(s.govde, optVar) + " x " + JSON.stringify(optVar));
  iddia("(1e) etiket govdede geciyor (taban/varyant)",
        kacKez(s.govde, h.taban) >= 1 && kacKez(s.govde, h.varyant) >= 1,
        h.taban + "=" + kacKez(s.govde, h.taban) + " · " + h.varyant + "=" + kacKez(s.govde, h.varyant));

  // (3) istemci yarisi: sayfanin YUKLEDIGI varlik JS'i etiketi satira yaziyor mu?
  const m = s.govde.match(/\/varlik\/urun-[0-9a-f]+\.js/);
  if (!m) {
    olculemedi("(3a) sayfa varlik JS'i", "sayfada /varlik/urun-*.js referansi bulunamadi",
      "sayfa govdesinde script src desenini yeniden turetmek");
    return s;
  }
  let js;
  try { js = await getir(SITE + m[0]); }
  catch (e) {
    olculemedi("(3a) varlik JS indirilemedi", "ag hatasi: " + e.message, "agli kabuk");
    return s;
  }
  iddia("(3a) varlik JS 200 (" + m[0] + ")", js.kod === 200, "kod=" + js.kod + " bayt=" + js.govde.length);
  iddia("(3b) canli JS #boySec'i OKUYOR",
        kacKez(js.govde, 'getElementById("boySec")') === 1,
        kacKez(js.govde, 'getElementById("boySec")'));
  iddia("(3c) canli JS secilen etiketi SATIRA yaziyor (s.boy_etiket = boySec.value)",
        kacKez(js.govde, "s.boy_etiket = boySec.value") === 1,
        kacKez(js.govde, "s.boy_etiket = boySec.value"));
  iddia("(3d) canli JS boySec DEGISIMINI dinliyor (yeniden render)",
        kacKez(js.govde, "[malzemeSec, renkSec, boySec]") === 1,
        kacKez(js.govde, "[malzemeSec, renkSec, boySec]"));
  return s;
}

function eksen2Istemci(tmp) {
  yaz("");
  yaz("EKSEN (2) — istemci kolu: secim degisince gosterilen fiyat (secenekler.js boyFarki)");
  let taban;
  try { taban = icKolCalistir("taban", path.join(KOK, "secenekler.js")); }
  catch (e) {
    olculemedi("(2) istemci kolu", "alt surec dustu: " + String(e.message).slice(0, 300),
      "node ile secenekler.js'i yukleyip satirOzeti cagirmak");
    return;
  }
  for (const h of HEDEF) {
    const r = taban[h.id] || {};
    iddia("(2a) " + h.id + ": '" + h.taban + "' -> '" + h.varyant + "' delta = +" + h.fark_tl + " TL",
          r.delta_kurus === h.fark_tl * 100,
          "taban=" + r.taban_kurus + "kr (" + r.taban_metin + ") varyant=" + r.varyant_kurus +
          "kr (" + r.varyant_metin + ") delta=" + r.delta_kurus + "kr");
    iddia("(2b) " + h.id + ": secilen etiket satir DETAYINDA gorunuyor",
          typeof r.detay_varyant === "string" && r.detay_varyant.indexOf("Boy: " + h.varyant) >= 0,
          JSON.stringify(r.detay_varyant));
  }

  // MUTANT (hedef kol): boyFarki her zaman 0 dondursun -> (2a) KIRMIZI olmali.
  const mh = mutantYaz(tmp, "hedef",
    "if (secenekler[i].etiket === boyEtiket) { return secenekler[i].fark_tl || 0; }",
    "if (secenekler[i].etiket === boyEtiket) { return 0; }");
  if (mh.hata) {
    olculemedi("(2c) HEDEF mutant", mh.hata + " capa=" + JSON.stringify(mh.capa),
      "secenekler.js:281 capasini tekil hale getirip mutanti yeniden kosmak");
  } else {
    let mr;
    try { mr = icKolCalistir("mutant-hedef", mh.yol); }
    catch (e) { mr = null; }
    if (!mr) {
      olculemedi("(2c) HEDEF mutant", "mutant alt sureci dustu", "mutant agacini elle kosmak");
    } else {
      const hepsiOldu = HEDEF.every((h) => (mr[h.id] || {}).delta_kurus === 0);
      iddia("(2c) HEDEF mutant (boyFarki->0) iddiayi OLDURUYOR",
            hepsiOldu,
            HEDEF.map((h) => h.id + ".delta=" + (mr[h.id] || {}).delta_kurus + "kr").join(" · "));
      // ATIF: mutant HEDEF kolu oldurdu mu, yoksa her seyi mi bozdu? malzeme farki YASAMALI.
      const kontrolYasadi = HEDEF.every((h) =>
        (mr[h.id] || {}).petg_delta === (taban[h.id] || {}).petg_delta &&
        (mr[h.id] || {}).petg_delta > 0);
      iddia("(2d) HEDEF mutant IZOLE (malzeme farki bozulmadi)",
            kontrolYasadi,
            HEDEF.map((h) => h.id + " petg taban=" + (taban[h.id] || {}).petg_delta +
                             " mutant=" + (mr[h.id] || {}).petg_delta).join(" · "));
    }
  }

  // KONTROL mutant: ilgisiz kolu boz (renk "Diger" yuzdesi) -> (2a) YESIL KALMALI.
  const mk = mutantYaz(tmp, "kontrol",
    'var renkCarpan = (!fiziksel && renk === "Diğer") ? (100 + RENK_DIGER_YUZDE) : 100;',
    'var renkCarpan = (!fiziksel && renk === "__ASLA__") ? (100 + RENK_DIGER_YUZDE) : 100;');
  if (mk.hata) {
    olculemedi("(2e) KONTROL mutant", mk.hata, "secenekler.js:655 capasini tekil hale getirmek");
  } else {
    let kr;
    try { kr = icKolCalistir("mutant-kontrol", mk.yol); }
    catch (e) { kr = null; }
    if (!kr) olculemedi("(2e) KONTROL mutant", "alt surec dustu", "mutant agacini elle kosmak");
    else iddia("(2e) KONTROL mutant (ilgisiz kol) iddiayi OLDURMUYOR",
               HEDEF.every((h) => (kr[h.id] || {}).delta_kurus === h.fark_tl * 100),
               HEDEF.map((h) => h.id + ".delta=" + (kr[h.id] || {}).delta_kurus + "kr").join(" · "));
  }
}

/* (2f) — (2a..2e) YEREL secenekler.js'i olctu. Iddia CANLI sayfaya dair oldugu icin
 * canlida kosan govdenin AYNI oldugu ayrica olculur: iki fiyat kolu (boyFarki +
 * hesaplaFiyatKurus) BAYT-ESIT mi. Esit degilse (2a..2e) canli icin gecersizdir. */
async function eksen2Canli() {
  yaz("");
  yaz("EKSEN (2f) — canlida kosan fiyat cekirdegi YERELLE bayt-esit mi: " + SITE + "/secenekler.js");
  let c;
  try { c = await getir(SITE + "/secenekler.js"); }
  catch (e) {
    olculemedi("(2f) canli secenekler.js", "ag hatasi: " + e.message,
      "agli kabuktan GET " + SITE + "/secenekler.js");
    return;
  }
  iddia("(2f-a) canli secenekler.js 200", c.kod === 200, "kod=" + c.kod + " bayt=" + c.govde.length);
  if (c.kod !== 200) return;
  const yerel = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");
  const kes = (govde, bas) => {
    const i = govde.indexOf(bas);
    if (i < 0) return null;
    const j = govde.indexOf("\n  }", i);
    return j < 0 ? null : govde.slice(i, j + 4);
  };
  for (const [ad, capa] of [["boyFarki", "function boyFarki(urun, boyEtiket) {"],
                            ["hesaplaFiyatKurus", "function hesaplaFiyatKurus(temelFiyatTL,"]]) {
    const a = kes(yerel, capa), b = kes(c.govde, capa);
    if (a === null || b === null) {
      olculemedi("(2f) " + ad + " govdesi", "capa bulunamadi (yerel=" + (a !== null) +
        " canli=" + (b !== null) + ")", "capa desenini iki uctan yeniden turetmek");
      continue;
    }
    // YORUM SOYULMUS KIYAS: canliya giden varlik yorumsuz servis edilebiliyor. Anlam ekseni
    // yorumla degil KODLA tasinir -> ikinci kiyas yorum+bosluk soyulmus halde yapilir.
    const soy = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "")
                        .replace(/\s+/g, " ").trim();
    const esitHam = a === b, esitSoyulu = soy(a) === soy(b);
    iddia("(2f-" + ad + ") canli govde YERELLE ayni (yorum soyulmus KOD ekseni)", esitSoyulu,
          "ham: yerel=" + a.length + "B canli=" + b.length + "B esit=" + esitHam +
          " | soyulmus: yerel=" + soy(a).length + "B canli=" + soy(b).length + "B esit=" + esitSoyulu +
          (esitSoyulu ? "" : "\n      YEREL-SOYULMUS: " + soy(a) + "\n      CANLI-SOYULMUS: " + soy(b)));
    if (esitSoyulu && !esitHam) {
      yaz("       not: ham bayt farki YALNIZ yorum/bosluk (canli varlik yorumsuz servis ediliyor)");
    }
  }
}

async function eksen4ve5Sunucu(h) {
  yaz("");
  yaz("EKSEN (4) + (5) — SUNUCU hesabi: POST " + FIYAT_UC + "  [" + h.id + "]");
  const kalem = (ek) => Object.assign(
    { id: h.id, malzeme: "PLA", renk: "Siyah", adet: 1 }, ek);

  let a, b, t, y, z;
  try {
    a = await fiyatSor([kalem({ boy_etiket: h.taban })]);      await bekle(400);
    b = await fiyatSor([kalem({ boy_etiket: h.varyant })]);    await bekle(400);
    // TAMPER: istemci KENDI fiyatini yollasin — sunucu OKUMAMALI.
    t = await fiyatSor([kalem({ boy_etiket: h.taban, fiyat: "1 TL", birim_kurus: 1,
                               tutar_kurus: 1, fark_tl: 99999,
                               boy_secenekleri: [{ etiket: h.taban, fark_tl: 99999 }] })]);
    await bekle(400);
    y = await fiyatSor([kalem({ boy_etiket: h.varyant + "XX" })]);  await bekle(400);
    z = await fiyatSor([kalem({})]);
  } catch (e) {
    olculemedi("(4) sunucu hesabi " + h.id, "ag hatasi: " + e.message,
      "agli bir kabuktan POST " + FIYAT_UC + " kosmak");
    return;
  }

  if (a.kod === 429 || b.kod === 429) {
    olculemedi("(4) sunucu hesabi " + h.id, "hiz siniri (429) — uc 60/60sn",
      "bir dakika bekleyip yeniden kosmak");
    return;
  }

  const ok = (r) => r.veri && Array.isArray(r.veri.satirlar) ? r.veri.urun_kurus : null;
  iddia("(4a) taban '" + h.taban + "' 200 + fiyatli",
        a.kod === 200 && ok(a) > 0, "kod=" + a.kod + " urun_kurus=" + ok(a) +
        " ham=" + a.metin.slice(0, 200));
  iddia("(4b) varyant '" + h.varyant + "' 200 + fiyatli",
        b.kod === 200 && ok(b) > 0, "kod=" + b.kod + " urun_kurus=" + ok(b));
  iddia("(4c) 🔴 SUNUCU farki hesapliyor: delta = +" + h.fark_tl + " TL",
        ok(a) !== null && ok(b) !== null && (ok(b) - ok(a)) === h.fark_tl * 100,
        "taban=" + ok(a) + "kr varyant=" + ok(b) + "kr delta=" + (ok(b) - ok(a)) + "kr");
  iddia("(4d) 🔴 TAMPER: istemcinin yolladigi fiyat/fark OKUNMUYOR",
        t.kod === a.kod && ok(t) === ok(a),
        "tamper kod=" + t.kod + " urun_kurus=" + ok(t) + " | temiz=" + ok(a));
  const hataAdi = (r) => (r.veri && (r.veri.hata && r.veri.hata.hata || r.veri.hata)) || null;
  iddia("(4e) gecersiz etiket REDDEDILIYOR (400 gecersiz-boy)",
        y.kod === 400 && hataAdi(y) === "gecersiz-boy",
        "kod=" + y.kod + " hata=" + JSON.stringify(hataAdi(y)) + " ham=" + y.metin.slice(0, 160));
  iddia("(4f) etiketsiz istek REDDEDILIYOR (400 boy-secimi-zorunlu)",
        z.kod === 400 && hataAdi(z) === "boy-secimi-zorunlu",
        "kod=" + z.kod + " hata=" + JSON.stringify(hataAdi(z)) + " ham=" + z.metin.slice(0, 160));

  // (5) D1: sunucu boy_secenekleri'ni YALNIZ D1 kolonundan okur (index.js:278 + :350).
  // Kolon bos/'[]'olsaydi (4b) 400 "boy-desteklenmiyor" donerdi; (4f) de 200 donerdi.
  iddia("(5a) D1 kolonu " + h.id + " icin DOLU (sunucu cevabindan TURETILDI)",
        b.kod === 200 && z.kod === 400 && hataAdi(z) === "boy-secimi-zorunlu",
        "varyant kod=" + b.kod + " (kolon bos olsaydi 400 boy-desteklenmiyor) · " +
        "etiketsiz kod=" + z.kod + "/" + JSON.stringify(hataAdi(z)) +
        " (kolon bos olsaydi 200 donerdi)");
}

/* ==================================== SURUCU ==================================== */

const arg = process.argv.slice(2);
if (arg[0] === "--ic") { icKol(arg[2]); process.exit(0); }

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "faz1-varyasyon-"));
try {
  yaz("VARYASYON FAZ 1 — CANLI ZINCIR OLCUMU");
  yaz("site=" + SITE + "  ·  cache-bust YOK  ·  yan etki YOK");
  yaz("hedef=" + HEDEF.map((h) => h.id + "(" + h.taban + "/" + h.varyant + " +" + h.fark_tl + "TL)").join("  "));

  for (const h of HEDEF) { await eksen1ve3Sayfa(h); }
  eksen2Istemci(tmp);
  await eksen2Canli();
  for (const h of HEDEF) { await eksen4ve5Sunucu(h); }

  yaz("");
  yaz("================ OZET ================");
  yaz("IDDIA GECTI    = " + GECTI);
  yaz("IDDIA KALDI    = " + KALDI);
  yaz("OLCULEMEDI     = " + OLCULEMEDI);
  yaz("HUKUM          = " + (KALDI === 0 && OLCULEMEDI === 0 ? "YESIL"
                            : KALDI > 0 ? "KIRMIZI" : "KISMI (OLCULEMEDI var)"));
  fs.writeFileSync(path.join(KOK, "FAZ1-OLCUM.txt"), SATIRLAR.join("\n") + "\n", "utf8");
  yaz("ham cikti -> FAZ1-OLCUM.txt");
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });   // disk kurali: ureten temizler
}
process.exit(KALDI > 0 ? 1 : 0);
