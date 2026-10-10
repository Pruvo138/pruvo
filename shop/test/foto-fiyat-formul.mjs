#!/usr/bin/env node
/**
 * FOTO FIYAT — TEK FORMUL kabul testi (Okan 7 Eki 15:4x: "fiyat bu ürünlerin tamamında aynı per cm/100tl
 * fiyatlistesi yazmayın ... hangisi uzunsa ona göre belirlenir"). PARA sinifi: hata SESSIZ olur (yanlis
 * formul canliya cikarsa siparis normal akar, fiyat yanlis tahsil edilir). Eski tablo ureteci
 * (tools/foto-fiyat-uret.py + testi) EMEKLI: fiyat tablosu yok, formul foto-uretim-veri.js VERI.fiyatKurus.
 *
 *   node shop/test/foto-fiyat-formul.mjs
 *
 *   F1 FORMUL      : manifestteki HER kategori × 3 olcu (en_az · orta · en_cok) -> fiyat_kurus = max(60000, mm × 1000)
 *                    (kategori farki YOK); sayi manifestten (uydurma yok), tablo stdout'a basilir
 *   F2 RED         : aralik disi (en_az − adim, en_cok + adim), adim disi, tam sayi olmayan olcu -> null;
 *                    bilinmeyen formul adi -> null (tur fiyatsiz kalir, sunulmaz)
 *   F3 BASLANGIC   : "₺N'dan itibaren" = en_az formulu (sürgünün ilk duragi = en_az)
 *   F4 TEK KAYNAK  : sunucu (shop/src/foto.js acikTurler) her olcuyu VERI.fiyatKurus ile ayni tutarda verir;
 *                    istemci (foto-uretim.js) fiyati F.fiyatKurus/F.fiyatSatiri'dan alir, kendi katsayisi YOK;
 *                    `foto_fiyat` tablo atfi shop/src/*.js + foto-uretim*.js'te 0
 *   F5 ANAHTAR     : acilis anahtari okunamaz / bos -> acik tur 0 (fail-closed)
 *   F6 TABAN       : (Okan 8 Eki) HER tur, sürgünün HER duragi >= 600 TL; taban gercekten basan tur >= 1
 *   F7 TABANSIZ    : tur kaydinda fiyat.taban_tl yoksa fiyat null (tur sunulmaz, fail-closed)
 *   F9 RENK+MALZEME: (Okan 9 Eki) round(max(600, mm × 10) × (Renkli ? 1,15 : 1) × (PETG ? 1,30 : 1)); renk adedi
 *                    fiyata GIRMEZ (ek_renk_tl 0); malzeme YALNIZ PLA/PETG (ASA/ABS RED); 3 ana renk; renk_tavani'siz
 *                    tur fiyatsiz. (Eski F9 "ek renk +100 TL" Okan 9 Eki emriyle KALKTI.)
 * MUTANTLAR (veri dosyasinin BELLEKTEKI kopyasi / foto.js'in GECICI kopyasi; agaca yazim YOK):
 *   FM1 formul ×100 · FM2 en_az yerine en_cok · FM3 adim izgarasi silindi · FM4 anahtar fail-open ·
 *   FM6 taban kalkti (F1/F3/F6) · FM7 tabansiz tur fail-open (F7) · FM9 Renkli carpani dustu · FM10 PETG carpani
 *   dustu · FM11 ASA secilebilir · FM12 renk adedi yeniden ucretlenir (F9)
 *   -> hedef grup KIRMIZI; FM0 (yalniz yorum) -> hicbiri. Olcu EKSENI (X/Y'ye bakan olcum) mutanti
 *   shop/test/foto-uretim.mjs OZ-M1'de (sentetik 3MF orada).
 * CIKIS: 0 yesil · 1 kirmizi. Son satir `SURVIVOR=<n>`.
 */
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");
const SHOP = path.join(KOK, "shop");
const VERI_YOL = path.join(KOK, "foto-uretim-veri.js");
const VERI_KAYNAK = fs.readFileSync(VERI_YOL, "utf8");

// TABAN (Okan 8 Eki 13:2x): fiyat = max(600 TL, mm × 10 TL). Bagimsiz carpim — VERI'den OKUNMAZ.
const TABAN_KURUS = 60000;
const beklenenKurus = (mm) => Math.max(mm * 1000, TABAN_KURUS);
const PLAKET_FIYAT = 'fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, renk_tavani: 4 },\n        // Okan kararı 7 Eki 2026: plaket';

let kirmizi = 0;
const ol = (ad, kosul, ek) => {
  if (kosul) { console.log("  ✅ " + ad); } else { kirmizi++; console.log("  ❌ " + ad + (ek ? " — " + ek : "")); }
};

/** Veri dosyasini (ya da mutantini) ayri vm baglaminda yukler. */
function veriYukle(kaynak) {
  const k = {};
  vm.runInNewContext(kaynak, k, { filename: "foto-uretim-veri.js" });
  return k.PRUVO_FOTO;
}

/** Formul senaryolari: V = veri nesnesi, kaynak = V'nin kaynak metni (F6 kontrol kolu kopyasi). Donus {F1, F2, F3, sayi, tablo}. */
function formulSenaryolar(V, kaynak) {
  const s = { F1: true, F2: true, F3: true, F6: true, sayi: 0, gecen: 0, tablo: [], tabanli: [], enDusuk: [] };
  for (const t of V.turler) {
    const a = t.olcu_mm || {};
    const sec = V.olcuSecenekleri(t.kod);
    const orta = sec.length ? sec[Math.floor((sec.length - 1) / 2)] : null;
    const satir = { kod: t.kod, olculer: [] };
    for (const mm of [a.en_az, orta, a.en_cok]) {
      s.sayi++;
      const k = V.fiyatKurus(t.kod, mm);
      const dogru = Number.isInteger(mm) && k === beklenenKurus(mm);
      if (dogru) { s.gecen++; } else { s.F1 = false; }
      satir.olculer.push({ mm, kurus: k, metin: V.fiyatSatiri(t.kod, mm), dogru });
    }
    s.tablo.push(satir);
    const adim = (t.fiyat || {}).adim_mm;
    // TURETILMIS eksen (kopru-15 dilim-3): olcu OLCULUR, secilmez -> izgara aranmaz (en_az + 1 GECERLI,
    // ayni formul); aralik disi ve kesirli olcu her turde RED.
    const tu = t.olcu_ekseni === "turetilmis";
    const disarida = [a.en_az - adim, a.en_cok + adim, a.en_az + 0.5].concat(adim > 1 && !tu ? [a.en_az + 1] : []);
    if (disarida.some((mm) => V.fiyatKurus(t.kod, mm) !== null)) { s.F2 = false; }
    const ar = V.olcuAraligi(t.kod);
    if (tu && ar && ar.en_cok > ar.en_az + 1 && V.fiyatKurus(t.kod, ar.en_az + 1) === null) { s.F2 = false; }
    if (!tu && adim > 1 && V.olcuTuretilmis(t.kod)) { s.F2 = false; }
    // Baslangic fiyati: sürgünün ilk duragi en_az, fiyati max(600 TL, en_az × 10 TL).
    if (sec[0] !== a.en_az || V.fiyatKurus(t.kod, sec[0]) !== beklenenKurus(a.en_az)) { s.F3 = false; }
    // F6 TABAN: surgunun HER duragi >= 600 TL; en dusuk durak tam 600 TL ya da en_az × 10 TL.
    const fiyatlar = sec.map((mm) => V.fiyatKurus(t.kod, mm));
    const enDusuk = fiyatlar.length && fiyatlar.every((k) => Number.isInteger(k)) ? Math.min(...fiyatlar) : null;
    if (enDusuk === null || enDusuk < TABAN_KURUS || enDusuk !== beklenenKurus(a.en_az)) { s.F6 = false; }
    s.enDusuk.push(enDusuk);
    if (a.en_az * 1000 < TABAN_KURUS) { s.tabanli.push(t.kod); }
  }
  if (s.sayi === 0 || s.enDusuk.length === 0) { s.F1 = false; s.F6 = false; }
  // Kontrol kolu: tabanin GERCEKTEN bastigi tur yoksa F6 hicbir seyi olcmuyor demektir. Okan 10 Eki ~13:4x
  // (anahtarlik 60, plaket 60) sonrasi gercek veride HER turun alt siniri >= 60 (60 mm × 10 TL = taban): taban
  // hicbir durakta basmayabilir -> kol KOPYADA olculur (plaket alt siniri 10'a cekilir; 10/50 mm = 600 TL, 70 mm = 700 TL).
  s.tabanKopya = s.tabanli.length === 0 ? tabanKopyadaBasar(kaynak) : null;
  if (s.tabanli.length === 0 && s.tabanKopya !== true) { s.F6 = false; }
  return s;
}

/** F6 kontrol kolu (kopya): plaketin alt siniri 10'a cekilince 10/50 mm = 600 TL (taban basar), 70 mm = 700 TL. */
function tabanKopyadaBasar(kaynak) {
  const re = /(kod: "plaket",[\s\S]*?olcu_mm: \{ en_az: )\d+(, en_cok: \d+ \})/;
  if (typeof kaynak !== "string" || !re.test(kaynak)) { return false; }
  const K = veriYukle(kaynak.replace(re, (m, a, b) => a + "10" + b));
  return K.fiyatKurus("plaket", 10) === TABAN_KURUS && K.fiyatKurus("plaket", 50) === TABAN_KURUS &&
    K.fiyatKurus("plaket", 70) === 70000;
}

/** F7: tur kaydindan taban_tl silinince o tur fiyatsiz (null), digerleri etkilenmez. */
function tabansizSenaryo(kaynak) {
  if (kaynak.split(PLAKET_FIYAT).length !== 2) { return false; }
  const V = veriYukle(kaynak.replace(PLAKET_FIYAT, PLAKET_FIYAT.replace(", taban_tl: 600", "")));
  // K3a (8 Eki 2026): 15 tür silindi. 4 kalan türün hepsi foto; plaket taban_tl'siz -> null,
  // yapboz (en_az 10) 120 mm = 120000 etkilenmez.
  return V.fiyatKurus("plaket", 120) === null && V.fiyatKurus("yapboz", 120) === 120000;
}

// F8 (Okan 8 Eki 14:0x "slider 10 mm'den baslasin ama min fiyat 600 TL kalsin"): KraL'in elle tuttugu
// (kopru-disi) sabit eksenli turlerde surgu alt siniri 10 mm ve 10 mm = 600 TL.
// K3a (8 Eki 2026): 15 tür silindi; hiçbir tür türetilmiş eksen DEĞİL -> "türetilmiş 59/61 mm" kolu YOK.
// K3d: elle tür kümesi MANIFESTTEN türetilir (sabit liste yazılmaz): köprü kaydı (kopru-manifest-uret.py)
// `olcu_ekseni` taşır; taşımayan tür KraL'in elle tuttuğu türdür. Küme boşsa ya da plaket yoksa F8 KIRMIZI.
// Okan 10 Eki 12:4x: "slider figürlerde 60mm den başlasın" -> figürün alt sınırı 60 (60 mm = 600 TL); diğerleri 10.
const SURGU_ALT_ISTISNA = { figur: 60 };
const surguAlt = (k) => SURGU_ALT_ISTISNA[k] || 10;
const elleSurgu = (V) => V.turler.filter((t) => !("olcu_ekseni" in t)).map((t) => t.kod);
function surguSenaryo(V) {
  const elle = elleSurgu(V);
  const alt = elle.filter((k) => { const a = V.olcuAraligi(k), m = surguAlt(k); return a && a.en_az === m && V.olcuSecenekleri(k)[0] === m; });
  const on = elle.filter((k) => V.fiyatKurus(k, surguAlt(k)) === TABAN_KURUS);
  return { F8: elle.includes("plaket") && alt.length === elle.length && on.length === elle.length, elle, alt, on, tu: null, sinir: true };
}

// F9 (Okan 9 Eki 17:0x): "renk seçimi 3 ana renkte (siyah beyaz veya gri) yapılsın veya renkli seçeneği olsun %15
// farkla" + "malzeme seçiminde sadece pla ve petg … petg %30 fiyata eklensin". fiyat = round(max(600, mm × 10) ×
// (Renkli ? 1,15 : 1) × (PETG ? 1,30 : 1)); renk ADEDI fiyata girmez. Beklenen sayilar BAGIMSIZ (spec ornekleri) —
// VERI'den OKUNMAZ. Eski F9 (ek renk +100 TL) bu emirle KALKTI.
const SPEC_ORNEKLERI = [
  [100, {}, 100000], [100, { malzeme: "PETG" }, 130000], [100, { renkli: true }, 115000],
  [100, { renkli: true, malzeme: "PETG" }, 149500], [40, {}, 60000], [40, { renkli: true, malzeme: "PETG" }, 89700],
];
const MALZEME_KARTLARI = [["PLA", "~55-60°C", "Ev içi"], ["PETG", "~70-75°C", "Dış mekân / genel amaçlı"]];
// K3d: palet türleri MANIFESTTEN (`renk_secimi: "palet"` ham alanı); VERI.renkPaleti fonksiyonu buna uymalı.
const paletTurleri = (V) => V.turler.filter((t) => t.renk_secimi === "palet").map((t) => t.kod);
function renkSenaryo(V, kaynak) {
  const PALET_TURLERI = paletTurleri(V);
  const tumAlan = V.turler.every((t) => t.fiyat && !("ek_renk_tl" in t.fiyat) &&
    Number.isInteger(t.fiyat.renk_tavani) && t.fiyat.renk_tavani >= 1 && t.fiyat.renk_tavani <= 4);
  const p = (sc) => V.fiyatKurus("plaket", 120, sc);
  const ornek = SPEC_ORNEKLERI.map(([mm, sc, k]) => ({ mm, sc, k, v: V.fiyatKurus("plaket", mm, sc) }));
  const carpan = ornek.every((o) => o.v === o.k) && p(undefined) === beklenenKurus(120) &&
    p({ renkli: false, malzeme: "PLA" }) === beklenenKurus(120) &&
    V.turler.every((t) => { const o = V.olcuSecenekleri(t.kod)[0];
      return V.fiyatKurus(t.kod, o, { renkli: true, malzeme: "PETG" }) === Math.round(beklenenKurus(o) * 1.15 * 1.3); });
  // Bilinmeyen deger RED: ASA/ABS/kucuk harf/bos malzeme · bool olmayan renkli · eski renk ADEDI (sayi) · null.
  const redler = [{ malzeme: "ASA" }, { malzeme: "ABS" }, { malzeme: "pla" }, { malzeme: "" }, { renkli: "evet" },
    { renkli: 1 }, 1, 2, 4, null, []].every((sc) => p(sc) === null);
  const malz = JSON.stringify((V.MALZEMELER || []).map((m) => [m.kod, m.sicaklik, m.kullanim])) === JSON.stringify(MALZEME_KARTLARI) &&
    V.VARSAYILAN_MALZEME === "PLA" &&
    V.turler.every((t) => Object.values(t.malzemeler || {}).every((l) => l.every((m) => m === "PLA" || m === "PETG")));
  const anaRenk = JSON.stringify(V.ANA_RENKLER) === JSON.stringify(["Siyah", "Beyaz", "Gri"]) && V.VARSAYILAN_RENK === "Beyaz" &&
    V.RENKLI_ETIKET === "Renkli (+%15)";
  // Renkli YALNIZ fotografli turde (yazili anahtarlik "metin" girdisi -> Renkli yok).
  const renkliTur = V.turler.every((t) => V.renkliSecilebilir(t.kod) === (t.girdi || []).some((g) => /^foto-/.test(g))) &&
    V.renkliSecilebilir("anahtarlik") === false && V.renkliSecilebilir("plaket") === true;
  const palet = PALET_TURLERI.length > 0 && PALET_TURLERI.includes("plaket") && PALET_TURLERI.every((k) => V.renkPaleti(k)) &&
    V.turler.filter((t) => V.renkPaleti(t.kod)).length === PALET_TURLERI.length && V.PLA_RENKLERI.length === 9;
  let eksik = false;
  if (kaynak.split(PLAKET_FIYAT).length === 2) {
    const E = veriYukle(kaynak.replace(PLAKET_FIYAT, PLAKET_FIYAT.replace(", renk_tavani: 4", "")));
    eksik = E.fiyatKurus("plaket", 120) === null && E.fiyatKurus("yapboz", 120) === 120000;
  }
  return { F9: tumAlan && carpan && redler && malz && anaRenk && renkliTur && palet && eksik,
           tumAlan, carpan, redler, malz, anaRenk, renkliTur, palet, eksik, paletTurleri: PALET_TURLERI,
           ornek: ornek.map((o) => o.mm + ":" + o.v) };
}

console.log("F1-F3) TEK FORMUL — fiyat_kurus = max(600 TL, en uzun boyut (mm) × 10 TL), kategori farki YOK");
const VERI = veriYukle(VERI_KAYNAK);
const fs1 = formulSenaryolar(VERI, VERI_KAYNAK);
const kategori = VERI.turler.length;
for (const t of fs1.tablo) {
  console.log("     " + t.kod.padEnd(8) + " " + t.olculer.map((o) => (o.metin || (o.mm + " mm → ?")) + (o.dogru ? "" : " ✗")).join(" · "));
}
ol("F1 formul " + fs1.gecen + "/" + fs1.sayi + " (manifestte " + kategori + " kategori × 3 olcu)", fs1.F1 && fs1.gecen === kategori * 3, "");
ol("F2 aralik disi / adim disi / kesirli olcu -> fiyat YOK (null)", fs1.F2, "");
ol("F3 baslangic fiyati (₺N'dan itibaren) = en_az formulu, sürgü ilk duragi en_az", fs1.F3, "");
console.log("F6-F7) TABAN 600 TL — her tur, her surgu duragi");
ol("F6 taban: " + fs1.enDusuk.filter((k) => k >= TABAN_KURUS).length + "/" + kategori + " tur en dusuk fiyat >= 600 TL (" +
   fs1.tabanli.length + " turde taban basiyor: " + fs1.tabanli.join(",") + (fs1.tabanKopya === null ? "" : " · kopyada plaket 10 mm: " + fs1.tabanKopya) + ")", fs1.F6 && fs1.enDusuk.length === kategori, "");
ol("F7 taban_tl'siz tur -> fiyat null (sunulmaz), diger turler etkilenmez", tabansizSenaryo(VERI_KAYNAK), "");
{
  const sg = surguSenaryo(VERI);
  const kopruAlt = VERI.turler.filter((t) => !elleSurgu(VERI).includes(t.kod) && t.olcu_ekseni === "sabit")
    .map((t) => t.kod + ":" + t.olcu_mm.en_az);
  ol("F8 surgu alt siniri 10 mm (figur 60): " + sg.alt.length + "/" + sg.elle.length + " elle tur (" + sg.elle.join(",") + ") · alt sinir = 600 TL " + sg.on.length + "/" +
     sg.elle.length + " · turetilmis " + sg.tu + " 59 mm = 600 TL, 61 mm = 610 TL", sg.F8, JSON.stringify(sg));
  console.log("     bilgi: kopru (TeKiN kaydi) sabit turlerin alt siniri: " + kopruAlt.join(" "));
}
console.log("F9) RENK + MALZEME — round(max(600, mm × 10) × (Renkli 1,15) × (PETG 1,30)); renk adedi fiyatsiz");
{
  const rs = renkSenaryo(VERI, VERI_KAYNAK);
  for (const [mm, sc, k] of SPEC_ORNEKLERI) {
    console.log("     " + mm + " mm " + (sc.malzeme || "PLA") + " " + (sc.renkli ? "Renkli" : "Beyaz") + " = " +
      VERI.tlMetni(VERI.fiyatKurus("plaket", mm, sc)) + " (beklenen " + VERI.tlMetni(k) + ")");
  }
  ol("F9 renk+malzeme: " + VERI.turler.length + " turde ek_renk_tl YOK + tavan 1..4 · 6 spec ornegi + her tur Renkli+PETG " +
     "carpani · ASA/ABS/pla/bos/renkli\"evet\"/renk adedi(sayi) null · kartlar PLA/PETG metni AYNEN · 3 ana renk (Beyaz) · " +
     "Renkli yalniz fotografli turde · palet turleri " + rs.paletTurleri.join(",") + " · renk_tavani'siz tur fiyatsiz", rs.F9, JSON.stringify(rs));
}
{
  if (VERI_KAYNAK.split(PLAKET_FIYAT).length !== 2) { ol("F2b capa bulundu (tek)", false, PLAKET_FIYAT); }
  const bilinmeyen = veriYukle(VERI_KAYNAK.replace(PLAKET_FIYAT, PLAKET_FIYAT.replace("mm_x_10tl", "mm_x_99tl")));
  // K3a: litofan silindi. 4 kalan tur: plaket bilinmeyen formul -> null; yapboz (en_az 10) 120 mm = 120000.
  ol("F2b bilinmeyen formul adi -> fiyat null (plaket sunulmaz), diger turler etkilenmez",
     bilinmeyen.fiyatKurus("plaket", 120) === null && bilinmeyen.fiyatKurus("yapboz", 120) === 120000, "");
  ol("F2c TR bicim: 120 mm → 1.200 TL · 1234567 kurus → 12.345,67 TL",
     VERI.fiyatSatiri("plaket", 120) === "120 mm → 1.200 TL" && VERI.tlMetni(1234567) === "12.345,67 TL", VERI.fiyatSatiri("plaket", 120));
}

console.log("F4) TEK KAYNAK — sunucu = istemci = VERI.fiyatKurus; tablo atfi 0");
const foto = await import(url.pathToFileURL(path.join(SHOP, "src", "foto.js")).href);
async function sunucuSenaryo(fm) {
  const hepsi = new Set(globalThis.PRUVO_FOTO.turler.map((t) => t.kod));
  const turler = fm.acikTurler(hepsi);
  let n = 0, ayni = 0;
  for (const t of turler) {
    for (const o of t.olculer) { n++; if (o.fiyat_kurus === VERI.fiyatKurus(t.kod, o.mm) && o.fiyat_kurus === beklenenKurus(o.mm)) { ayni++; } }
  }
  const okunamaz = await fm.acikAnahtari({ KATALOG: { prepare() { throw new Error("D1_ERROR: no such table: foto_acik"); } } });
  const bos = await fm.acikAnahtari({ KATALOG: { prepare() { return { all: async () => ({ results: [] }) }; } } });
  return { SUNUCU: turler.length > 0 && n > 0 && n === ayni, n, ayni, turSayisi: turler.length,
           ANAHTAR: okunamaz.size === 0 && bos.size === 0 && fm.acikTurler(okunamaz).length === 0 && fm.acikTurler(bos).length === 0 };
}
const ss = await sunucuSenaryo(foto);
ol("F4a sunucu acikTurler: " + ss.ayni + "/" + ss.n + " olcu fiyati VERI.fiyatKurus ile AYNI (" + ss.turSayisi + " tur)", ss.SUNUCU, JSON.stringify(ss));
const ISTEMCI = fs.readFileSync(path.join(KOK, "foto-uretim.js"), "utf8");
// K3b (tek kutu 4 pencere): "₺…'dan itibaren" vitrini KALKTI; fiyat ③'te canlı (canliFiyatGuncelle) + ④ özetinde (cizS3),
// ikisi de AYNI ifade F.fiyatKurus(nt.kod, S.olcu, fiyatSecimi()) (Okan 9 Eki: renkli + malzeme; renk adedi YOK);
// turetilmis eksende sunucunun fiyatina AYNI carpan F.secimliKurus(S.fiyatKurus, fiyatSecimi()).
ol("F4b istemci fiyati TEK formulden: F.fiyatSatiri (sürgü) + F.fiyatKurus (③ canli + ④ toplam, 2 yer); vitrin 0; kendi katsayisi yok",
   /F\.fiyatSatiri\(nt\.kod/.test(ISTEMCI) && (ISTEMCI.match(/F\.fiyatKurus\(nt\.kod, S\.olcu, fiyatSecimi\(\)\)/g) || []).length === 2 &&
   !/renkSayisi\(nt\)\)/.test(ISTEMCI.replace(/var rs = renkSayisi\(nt\);/g, "")) && !/ekRenk/.test(ISTEMCI) &&
   (ISTEMCI.match(/F\.secimliKurus\(S\.fiyatKurus, fiyatSecimi\(\)\)/g) || []).length === 2 &&
   !/vitrinGuncelle|'dan itibaren/.test(ISTEMCI) && !/VITRIN_TL_MM/.test(ISTEMCI) &&
   // TURETILMIS eksen: bolum fiyati HESAPLAMAZ, yalniz sunucunun durum yanitindaki fiyat_kurus'u okur (tek satir).
   (ISTEMCI.match(/fiyat_kurus/g) || []).length === 2 &&
   /S\.fiyatKurus = typeof veri\.fiyat_kurus === "number" \? veri\.fiyat_kurus : null;/.test(ISTEMCI), "");
const tabloAtfi = [...fs.readdirSync(path.join(SHOP, "src")).filter((d) => d.endsWith(".js")).map((d) => path.join(SHOP, "src", d)),
  path.join(KOK, "foto-uretim.js"), VERI_YOL].map((y) => ({ y: path.relative(KOK, y), n: (fs.readFileSync(y, "utf8").match(/foto_fiyat/g) || []).length }))
  .filter((x) => x.n > 0);
ol("F4c `foto_fiyat` tablo atfi shop/src/*.js + foto-uretim*.js'te 0", tabloAtfi.length === 0, JSON.stringify(tabloAtfi));
console.log("F5) ACILIS ANAHTARI — okunamaz / bos -> acik tur 0 (fail-closed)");
ol("F5 anahtar okunamaz ya da bos -> acik tur 0", ss.ANAHTAR, "");

// ================================================================ MUTANTLAR
console.log("MUTANTLAR (bellekteki veri kopyasi / gecici foto.js kopyasi; calisma agacina yazilmaz)");
let survivor = 0;
const VERI_MUTANTLAR = [
  ["FM0 KONTROL (yorum)", "// Formül adı -> mm başına kuruş.", "// Formül  adı -> mm başına kuruş.", []],
  ["FM1 FORMUL ×100", "VERI.FIYAT_FORMULLERI = { mm_x_10tl: 1000 };", "VERI.FIYAT_FORMULLERI = { mm_x_10tl: 100000 };", ["F1", "F3", "F6", "F7", "F8", "F9"]],
  ["FM2 EN_AZ YERINE EN_COK", "return { en_az: t.olcu_mm.en_az, en_cok: t.olcu_mm.en_cok };",
   "return { en_az: t.olcu_mm.en_cok, en_cok: t.olcu_mm.en_cok };", ["F1", "F3", "F6", "F7", "F8", "F9"]],
  ["FM3 ADIM IZGARASI SILINDI", "return VERI.olcuTuretilmis(kod) || (mm - a.en_az) % adim === 0 || mm === a.en_cok;",
   "return true;", ["F2"]],
  // K3a: FM5 (TURETILMIS DE IZGARAYA BAGLI) SİLİNDİ. Kalan 4 türün TAMAMI foto, hiçbiri türetilmiş değil.
  // VERI.olcuTuretilmis(kod) her zaman false → mutant no-op olurdu. null/no-op mutant YASAK.
  // Okan 8 Eki tabani: taban kalkinca 60 mm alti turler 600 TL'nin altina iner -> F1/F3/F6 KIRMIZI.
  ["FM6 TABAN KALKTI", "return VERI.secimliKurus(Math.max(mm * f, taban), secim);", "return VERI.secimliKurus(mm * f, secim);",
   ["F1", "F3", "F6", "F8", "F9"]],
  // Tabansiz tur fail-open (taban yoksa 0 sayilir) -> F7 KIRMIZI.
  // Okan 14:0x: surgu alti 60'a geri cekilirse F8 KIRMIZI.
  // Capa plaketin kendi yorum satirini tasir: ayni olcu_mm satiri dinamik-min ile ses turunde de gecer (tek capa sarti).
  ["FM8 PLAKET SURGU ALTI 60", "        // Okan 6 Eki 2026: \"min 60 max 300\".\n        olcu_mm: { en_az: 10, en_cok: 300 },",
   "        // Okan 6 Eki 2026: \"min 60 max 300\".\n        olcu_mm: { en_az: 60, en_cok: 300 },", ["F8", "F9"]],
  ["FM7 TABANSIZ TUR FAIL-OPEN", "if (!f || taban === null || tavan === null || !VERI.olcuGecerli(kod, mm)) { return null; }",
   "if (!f || tavan === null || !VERI.olcuGecerli(kod, mm)) { return null; }", ["F7"]],
  // Okan 9 Eki: Renkli carpani (%15) duserse F9 KIRMIZI.
  ["FM9 RENKLI CARPANI DUSTU", "VERI.RENKLI_EK_YUZDE = 15;", "VERI.RENKLI_EK_YUZDE = 0;", ["F9"]],
  // Okan 9 Eki: PETG carpani (%30) duserse F9 KIRMIZI.
  ["FM10 PETG CARPANI DUSTU", 'kullanim: "Dış mekân / genel amaçlı", ek_yuzde: 30 }', 'kullanim: "Dış mekân / genel amaçlı", ek_yuzde: 0 }', ["F9"]],
  // Okan 9 Eki "sadece pla ve petg": ASA secilebilir olursa F9 KIRMIZI.
  ["FM11 ASA SECILEBILIR", 'kullanim: "Dış mekân / genel amaçlı", ek_yuzde: 30 }',
   'kullanim: "Dış mekân / genel amaçlı", ek_yuzde: 30 },\n    { kod: "ASA", sicaklik: "~95°C", kullanim: "Dış", ek_yuzde: 0 }', ["F9"]],
  // Eski ek renk modeli geri gelirse (sayi = renk adedi kabul edilir, adet basi +100 TL) F9 KIRMIZI.
  ["FM12 RENK ADEDI UCRETLENIR", "    if (s === undefined) { return { renkli: false, malzeme: VERI.VARSAYILAN_MALZEME }; }",
   "    if (s === undefined) { return { renkli: false, malzeme: VERI.VARSAYILAN_MALZEME }; }\n" +
   "    if (Number.isInteger(s) && s >= 1) { return { renkli: s > 1, malzeme: VERI.VARSAYILAN_MALZEME }; }", ["F9"]],
];
for (const [ad, capa, yerine, olmeli] of VERI_MUTANTLAR) {
  if (VERI_KAYNAK.split(capa).length !== 2) { ol(ad + " capa bulundu (tek)", false, capa); continue; }
  const mutant = VERI_KAYNAK.replace(capa, yerine);
  const s = formulSenaryolar(veriYukle(mutant), mutant);
  s.F7 = tabansizSenaryo(mutant);
  s.F8 = surguSenaryo(veriYukle(mutant)).F8;
  s.F9 = renkSenaryo(veriYukle(mutant), mutant).F9;
  const kir = ["F1", "F2", "F3", "F6", "F7", "F8", "F9"].filter((x) => s[x] !== true);
  const tam = JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort());
  if (olmeli.length && !kir.length) { survivor++; }
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", tam, JSON.stringify(kir));
}
const GECICI = path.join(SHOP, "foto-fiyat-test-tmp-" + process.pid);
process.on("exit", () => { fs.rmSync(GECICI, { recursive: true, force: true }); });
const FOTO_ASIL = fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8");
const FOTO_MUTANTLAR = [
  ["FM4 ANAHTAR FAIL-OPEN (okunamazsa hepsi acik)", "    return new Set();\n  }\n}",
   "    return new Set(VERI.turler.map((t) => t.kod));\n  }\n}", "ANAHTAR"],
  ["FM5 SUNUCU KENDI KATSAYISI (×100)", ".map((mm) => ({ mm, fiyat_kurus: VERI.fiyatKurus(t.kod, mm) }))",
   ".map((mm) => ({ mm, fiyat_kurus: mm * 100 }))", "SUNUCU"],
];
for (const [ad, capa, yerine, hedef] of FOTO_MUTANTLAR) {
  if (FOTO_ASIL.split(capa).length !== 2) { ol(ad + " capa bulundu (tek)", false, capa); continue; }
  fs.mkdirSync(GECICI, { recursive: true });
  const dosya = path.join(GECICI, "foto-" + hedef + ".js");
  // Goreli import ("../../foto-uretim-veri.js") gecici dizinden de KOK'e cozulsun diye mutlak yola cevrilir.
  fs.writeFileSync(dosya, FOTO_ASIL.replace(capa, yerine).replace('import "../../foto-uretim-veri.js";',
    "import " + JSON.stringify(url.pathToFileURL(VERI_YOL).href) + ";")
    .replace(/from "\.\/([a-z-]+\.js)"/g, (m, d) => "from " + JSON.stringify(url.pathToFileURL(path.join(SHOP, "src", d)).href)));
  const fm = await import(url.pathToFileURL(dosya).href);
  const s = await sunucuSenaryo(fm);
  if (s[hedef] === true) { survivor++; }
  ol(ad + " -> " + hedef + " KIRMIZI", s[hedef] === false, JSON.stringify({ SUNUCU: s.SUNUCU, ANAHTAR: s.ANAHTAR }));
}

console.log((kirmizi ? "❌ KIRMIZI: " + kirmizi : "✅ HEPSI GECTI") + " · SURVIVOR=" + survivor);
console.log("SURVIVOR=" + survivor);
process.exit(kirmizi ? 1 : 0);
