#!/usr/bin/env node
/**
 * PRUVO — ozet.json KART TEMSILI KABUL TESTI (v3: gorsel oneki + `yeni` referansi)
 *
 *   node tools/ozet-temsil-test.js
 *   node tools/ozet-temsil-test.js --mutasyon          # kapinin yuk tasidigini kanitla
 *   node tools/ozet-temsil-test.js --index <yol> --build <yol>   # mutant kaynak sec
 *
 * NE OLCER (tek cumle): ozet.json'un KUCULTULMUS temsili KAYIPSIZ mi — istemcinin ACTIGI
 * kart, bugunku kartla BIREBIR ayni mi?
 *
 * NEDEN VAR (hatanin SESSIZLIGI): ozet.json bir ILK BOYAMA is paketidir; edge modunda
 * sepet paneli urun objesini urunler.json'dan DEGIL bu karttan alir. Temsil kuculdugunde
 * bir deger yanlis geri acilirsa ekranda hata mesaji CIKMAZ — kart cizilir, fiyat/beyan
 * sessizce baska turlu gorunur ve WhatsApp mesajina o tutar yazilir. Bu yuzden kabul
 * "bayt dustu" DEGIL, "geri acilan kart kaynagiyla BIREBIR ESIT"tir.
 *
 * IKI TARAF, TEK KAYNAK:
 *   DERLEME  — GERCEK tools/build.py (--sadece-ozet --katalog/--cikti) uretir; kural
 *              JS'e KOPYALANMAZ.
 *   ISTEMCI  — GERCEK index.html `ozetAc` fonksiyonu (tools/ozet-ac-ayikla.js ile canli
 *              dosyadan ayiklanir). Cozucunun test kopyasi TUTULMAZ; kopya tutulsaydi
 *              temsil degistigi gun test dogru, tarayici yanlis acardi
 *              ([[ikiz-tanim-sessiz-ayrisma]]).
 *   BEKLENTI — `beklenenKart()`: fikstur urununden kart kurallarini BAGIMSIZ uygulayan
 *              capa. build.py'nin kendi tersinden TURETILMEZ; turetilseydi sikistirma ile
 *              acmanin AYNI hatayi paylasmasi yesil verirdi ([[anahat-referans-tautolojisi]]).
 *
 * IDDIALAR (her biri ayri satir basar):
 *   1  KAYIPSIZ — karisik fikstur (havuzda OLAN + OLMAYAN kartlar bir arada)
 *   2  KUCULME GERCEKTEN OLDU — ham artefaktta onek tekrari YOK, `yeniRef` referans TASIR
 *   3  SURUM 3 + `gorselOnek` basligi VAR (bump dusmedi)
 *   4  SIFIR ORTUSME — havuzsuz kategoriden gelen `yeni` kartlari TAM kart olarak dogru
 *   5  TAM ORTUSME — hepsi referans, geri acilis yine BIREBIR
 *   6  IKI SURUM — AYNI canli cozucu v2 (dizi) ve v1 (sozluk) artefakti da dogru acar
 *   7  BAYAT ISTEMCI — 11 Agu cozucusu v3'u alirsa BOS KART cizmez (olcum + sinir beyani)
 *
 * NE IDDIA EDILMEZ: vitrin SIRASI/blok kurali (tools/vitrin-siralama-test.js), bayt
 * BUTCESI (tools/faz3-yuk.js), kart ALAN SOZLESMESI (tools/edge-kart-kapisi.py),
 * arama semantigi (tools/parite-test.js).
 *
 * Cikis: 0 = yesil · 1 = kirmizi · 2 = OLCULEMEDI (altyapi; "yesil" DEGIL).
 */

"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const KOK = path.dirname(__dirname);
function _bayrak(ad, varsayilan) {
  const i = process.argv.indexOf(ad);
  return i !== -1 && process.argv[i + 1] ? path.resolve(process.argv[i + 1]) : varsayilan;
}
const INDEX_YOL = _bayrak("--index", path.join(KOK, "index.html"));
const BUILD_YOL = _bayrak("--build", path.join(KOK, "tools", "build.py"));

const GECICI = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-ozet-temsil-"));
let _no = 0;

function olculemedi(mesaj) {
  console.error("OLCULEMEDI: " + mesaj);
  process.exit(2);
}

// --------------------------------------------------------------- canli istemci cozucusu
let ozetAc;
try {
  ozetAc = require(path.join(KOK, "tools", "ozet-ac-ayikla.js")).ozetAcAl(INDEX_YOL);
} catch (e) {
  olculemedi("index.html ozetAc ayiklanamadi: " + e.message);
}

// -------------------------------------------------------------------- blok kurali (havuz)
// Beklenen havuz UZUNLUGU icin gerekli; blok KURALI bu testin ekseni DEGIL.
const INDEX_KAYNAK = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const VITRIN_BLOKLAR = (function () {
  const m = INDEX_KAYNAK.match(/var\s+VITRIN_BLOKLAR\s*=\s*(\[[\s\S]*?\])\s*;/);
  if (!m) { olculemedi("index.html'de VITRIN_BLOKLAR bulunamadi."); }
  try { return JSON.parse(m[1]); } catch (e) { return olculemedi("VITRIN_BLOKLAR JSON degil: " + e.message); }
})();
const OZET_YENI = (function () {
  const src = fs.readFileSync(path.join(KOK, "tools", "build.py"), "utf8");
  const m = src.match(/^OZET_YENI\s*=\s*(\d+)/m);
  if (!m) { olculemedi("build.py'de OZET_YENI bulunamadi."); }
  return Number(m[1]);
})();

// --------------------------------------------------------------------------- fiksturler
const ONEK = "https://media.pruvo3d.com/urunler/";
let _sira = 0;
function urun(kategori, ek) {
  const i = _sira++;
  return Object.assign({
    id: "fx-" + i + "-" + kategori.toLocaleLowerCase("tr").replace(/[^a-z]/g, ""),
    kategori,
    marka: [],
    baslik: "Fikstur urun " + i + " " + kategori,
    aciklama: "Fikstur aciklama " + i,
    fiyat: "100 TL",
    gorseller: [ONEK + "fx-" + i + "-1.jpg"],
  }, ek || {});
}
function coklu(liste, kategori, adet, ek) {
  for (let n = 0; n < adet; n++) { liste.push(urun(kategori, ek)); }
  return liste;
}

/** 🔴 BAGIMSIZ CAPA — build.py kart_ozeti kuralinin JS karsiligi (kaynaktan TURETILMEZ). */
function beklenenKart(p) {
  const k = {
    id: p.id,
    baslik: p.baslik || "",
    kategori: p.kategori || "",
    marka: p.marka || [],
    fiyat: p.fiyat || "",
    // Python `(p.get("gorseller") or [None])[0]` ile AYNI: BOS dizi de None verir
    // (JS'te [] dogrudur, bire bir cevirmek `undefined` uretirdi).
    gorsel: (p.gorseller && p.gorseller.length) ? p.gorseller[0] : null,
    parametrik: !!p.parametrik,
    aciklama: (p.aciklama || "").slice(0, 160),
  };
  if (p.tur === "fiziksel") { k.tur = "fiziksel"; }
  if (p.tavsiyeFilament) { k.tavsiyeFilament = p.tavsiyeFilament; }
  if (p.konfigur) { k.konfigur = p.konfigur; }
  return k;
}

/** Anahtar SIRASINDAN bagimsiz derin esitlik (JSON metni sira duyarli olurdu). */
function kanon(v) {
  if (Array.isArray(v)) { return "[" + v.map(kanon).join(",") + "]"; }
  if (v && typeof v === "object") {
    return "{" + Object.keys(v).sort().map((k) => JSON.stringify(k) + ":" + kanon(v[k])).join(",") + "}";
  }
  return JSON.stringify(v === undefined ? null : v);
}
const esit = (a, b) => kanon(a) === kanon(b);

// KENAR DURUMLAR tek fiksturde toplanir: kapaksiz urun · baska konaktan mutlak URL ·
// onegin TAM KENDISI olan URL · kosullu alanlarin (tur/tavsiyeFilament/konfigur) hepsi.
const KENAR = [
  { gorseller: [] },                                            // kapak YOK -> null
  { gorseller: ["https://ornek-baska-konak.example/x/y-1.jpg"] }, // onek TASIMAZ
  { gorseller: [ONEK] },                                        // onegin TAM KENDISI
  { tur: "fiziksel", tavsiyeFilament: "PETG" },
  { konfigur: { aile: "fx", olcu: { a: 10, b: 20 } }, tur: "fiziksel" },
];

/** KARISIK: `yeni` kesitinde hem havuzda OLAN hem OLMAYAN kartlar bulunur. */
function fiksturKarisik() {
  const l = [];
  KENAR.forEach((ek, i) => l.push(urun(i % 2 ? "Kamera" : "Marin", ek)));
  coklu(l, "Kamera", 15);          // havuzu YOK -> `yeni`de TAM kart
  coklu(l, "Marin", 30);           // havuzda VAR -> referans
  coklu(l, "Otomobil", 30);
  coklu(l, "Jeneratör", 4, { parametrik: true, fiyat: "" });
  coklu(l, "Ev", 6);
  return l;
}
/** SIFIR ORTUSME: `yeni` kartlarinin HICBIRI havuzlarda yok. */
function fiksturSifirOrtusme() {
  const l = [];
  coklu(l, "Kamera", 20);
  coklu(l, "Ev", 20);
  coklu(l, "Ofis", 20);
  return l;                        // Marin/Otomobil/parametrik stogu YOK -> havuzlar bos
}
/** TAM ORTUSME: `yeni`nin tamami havuzlarda. */
function fiksturTamOrtusme() {
  const l = [];
  coklu(l, "Marin", 60);
  return l;
}

// --------------------------------------------------------- GERCEK build.py ile uretim
function ozetUret(urunler) {
  const no = ++_no;
  const katalogYol = path.join(GECICI, "katalog-" + no + ".json");
  const ciktiYol = path.join(GECICI, "ozet-" + no + ".json");
  fs.writeFileSync(katalogYol, JSON.stringify(urunler), "utf8");
  const r = spawnSync("python3", [BUILD_YOL, "--sadece-ozet", "--katalog", katalogYol,
    "--cikti", ciktiYol], { encoding: "utf8" });
  if (r.error) { return { hata: "build.py calistirilamadi: " + r.error.message }; }
  if (r.status !== 0) {
    return { hata: "build.py exit " + r.status + " -> " + String(r.stderr || r.stdout || "").trim().slice(-300) };
  }
  if (!fs.existsSync(ciktiYol)) { return { hata: "build.py ozet yazmadi" }; }
  const ham = fs.readFileSync(ciktiYol, "utf8");
  return { ham, ozet: JSON.parse(ham), bayt: Buffer.byteLength(ham, "utf8") };
}

/** Artefaktin BEKLENEN kart kesitleri (fikstur + blok kuralindan turetilir). */
function beklenenKesitler(urunler) {
  const parametrik = urunler.filter((p) => p.parametrik).map(beklenenKart);
  const bloklar = {};
  VITRIN_BLOKLAR.forEach((kural) => {
    if (kural.kaynak === "parametrik") { return; }
    const aday = urunler.filter((p) => (p.kategori || "") === kural.kategori);
    const n = Number(kural.havuz || 0);
    bloklar[kural.kategori] = (n ? aday.slice(0, n) : aday).map(beklenenKart);
  });
  return { parametrik, bloklar, yeni: urunler.slice(0, OZET_YENI).map(beklenenKart) };
}

// --------------------------------------------------------------------------- raporlama
let kirmizi = 0;
let gecti = 0;
function rapor(ad, tamam, detay) {
  if (tamam) { gecti++; } else { kirmizi++; }
  console.log("  %s %s%s", tamam ? "✔" : "✘", ad, detay ? "  — " + detay : "");
}

/** Bir artefaktin GERI ACILISI kaynak kartlarla BIREBIR esit mi? */
function kayipsizMi(sonuc, urunler, etiket) {
  if (sonuc.hata) { olculemedi(etiket + ": " + sonuc.hata); }
  const beklenen = beklenenKesitler(urunler);
  const acik = ozetAc(JSON.parse(sonuc.ham));       // CANLI istemci cozucusu
  const sapmalar = [];
  if (!esit(acik.parametrik || [], beklenen.parametrik)) { sapmalar.push("parametrik"); }
  Object.keys(beklenen.bloklar).forEach((kat) => {
    if (!esit((acik.bloklar || {})[kat] || [], beklenen.bloklar[kat])) { sapmalar.push("bloklar/" + kat); }
  });
  if (!esit(acik.yeni || [], beklenen.yeni)) { sapmalar.push("yeni"); }
  const kartSayisi = beklenen.parametrik.length + beklenen.yeni.length
    + Object.keys(beklenen.bloklar).reduce((t, k) => t + beklenen.bloklar[k].length, 0);
  return { sapmalar, kartSayisi, acik, beklenen };
}

// ------------------------------------------------------------------ BAYAT ISTEMCI KOPYASI
/* 🔴 DONDURULMUS KOPYA — 11 Agu 2026 index.html'indeki `ozetAc` (v2 cozucusu). Burada
   BILEREK kopyadir: olculen sey "ziyaretcinin tarayicisinda ONBELLEKTE DURAN ESKI kod
   yeni artefakti alirsa ne cizer" sorusudur; canli dosyadan okunsaydi soru sorulmus
   olmazdi. Guncellenmez — tarih damgasi ile birlikte durur. */
function bayatIstemciOzetAc(d) {
  var alanlar = (d && d.kartAlanlari) || [];
  if (!alanlar.length) { return d; }
  function kartAc(k) {
    if (Object.prototype.toString.call(k) !== "[object Array]") { return k; }
    var out = {};
    k.forEach(function (deger, i) {
      if (i < alanlar.length && (i < 8 || deger !== null)) { out[alanlar[i]] = deger; }
    });
    return out;
  }
  d.parametrik = (d.parametrik || []).map(kartAc);
  Object.keys(d.bloklar || {}).forEach(function (kat) {
    d.bloklar[kat] = (d.bloklar[kat] || []).map(kartAc);
  });
  d.yeni = (d.yeni || []).map(kartAc);
  return d;
}

// --------------------------------------------------------------------------- kosum
function kosum() {
  console.log("=== ozet.json KART TEMSILI KABUL TESTI");
  console.log("    index: %s", path.relative(KOK, INDEX_YOL) || INDEX_YOL);
  console.log("    build: %s", path.relative(KOK, BUILD_YOL) || BUILD_YOL);

  // ---- 1/2/3: KARISIK fikstur
  const karisikUrun = fiksturKarisik();
  const karisik = ozetUret(karisikUrun);
  const k1 = kayipsizMi(karisik, karisikUrun, "karisik fikstur");
  rapor("1 KAYIPSIZ (karisik fikstur): geri acilan kart == kaynak kart",
    k1.sapmalar.length === 0 && k1.kartSayisi >= 60,
    "karsilastirilan kart " + k1.kartSayisi + (k1.sapmalar.length ? " | SAPAN: " + k1.sapmalar.join(", ") : ""));

  // Onegin TAM KENDISI olan deger BILEREK kirpilmaz (kalan bos dize olurdu) — sayimda
  // "onek + devami" aranir.
  const hamGorseller = (karisik.ozet.bloklar.Marin || []).map((k) => k[5]);
  const onekliHam = hamGorseller.filter((g) => typeof g === "string"
    && g.indexOf(ONEK) === 0 && g.length > ONEK.length).length;
  const refSayisi = (karisik.ozet.yeniRef || []).filter((x) => typeof x === "string").length;
  const tamSayisi = (karisik.ozet.yeniRef || []).filter((x) => Array.isArray(x)).length;
  rapor("2 KUCULME GERCEK: ham artefaktta onek tekrari YOK ve `yeniRef` referans tasiyor",
    onekliHam === 0 && refSayisi > 0 && tamSayisi > 0,
    "onekli ham kapak " + onekliHam + " | referans " + refSayisi + " | tam kart " + tamSayisi);

  rapor("3 SURUM BUMP: surum=3 ve `gorselOnek` basligi VAR",
    karisik.ozet.surum === 3 && karisik.ozet.gorselOnek === ONEK,
    "surum=" + JSON.stringify(karisik.ozet.surum) + " gorselOnek=" + JSON.stringify(karisik.ozet.gorselOnek));

  // ---- 4: SIFIR ORTUSME (yarin ortusme 0 olursa da dogru cizilmeli)
  const sifirUrun = fiksturSifirOrtusme();
  const sifir = ozetUret(sifirUrun);
  const k4 = kayipsizMi(sifir, sifirUrun, "sifir ortusme fiksturu");
  const sifirRef = (sifir.ozet.yeniRef || []).filter((x) => typeof x === "string").length;
  const sifirTam = (sifir.ozet.yeniRef || []).filter((x) => Array.isArray(x)).length;
  rapor("4 SIFIR ORTUSME: havuzsuz kartlar TAM kart olarak tasinir ve BIREBIR acilir",
    k4.sapmalar.length === 0 && sifirRef === 0 && sifirTam === Math.min(OZET_YENI, sifirUrun.length),
    "referans " + sifirRef + " | tam kart " + sifirTam
    + (k4.sapmalar.length ? " | SAPAN: " + k4.sapmalar.join(", ") : ""));

  // ---- 5: TAM ORTUSME
  const tamUrun = fiksturTamOrtusme();
  const tam = ozetUret(tamUrun);
  const k5 = kayipsizMi(tam, tamUrun, "tam ortusme fiksturu");
  const tamRef = (tam.ozet.yeniRef || []).filter((x) => typeof x === "string").length;
  rapor("5 TAM ORTUSME: hepsi referans, geri acilis yine BIREBIR",
    k5.sapmalar.length === 0 && tamRef === Math.min(OZET_YENI, tamUrun.length),
    "referans " + tamRef + "/" + Math.min(OZET_YENI, tamUrun.length)
    + (k5.sapmalar.length ? " | SAPAN: " + k5.sapmalar.join(", ") : ""));

  // ---- 6: IKI SURUM — AYNI canli cozucu eski artefaktlari da acar
  const bek = beklenenKesitler(karisikUrun);
  const alanlar = karisik.ozet.kartAlanlari;
  function v2Dizi(kart) {          // v2: onek YOK, tam URL, sondaki bos alanlar kirpik
    const dizi = alanlar.map((a) => (a in kart ? kart[a] : null));
    let son = -1;
    alanlar.forEach((a, i) => { if (a in kart) { son = i; } });
    return dizi.slice(0, son + 1);
  }
  const v2 = {
    surum: 2, kartAlanlari: alanlar, toplam: karisikUrun.length,
    kategoriler: {}, markalar: {},
    parametrik: bek.parametrik.map(v2Dizi),
    bloklar: Object.fromEntries(Object.keys(bek.bloklar).map((k) => [k, bek.bloklar[k].map(v2Dizi)])),
    yeni: bek.yeni.map(v2Dizi), vitrin: {},
  };
  const v2Acik = ozetAc(JSON.parse(JSON.stringify(v2)));
  const v2Tamam = esit(v2Acik.parametrik, bek.parametrik) && esit(v2Acik.yeni, bek.yeni)
    && Object.keys(bek.bloklar).every((k) => esit(v2Acik.bloklar[k], bek.bloklar[k]));
  const v1 = {
    surum: 1, toplam: 2, kategoriler: {}, markalar: {},
    parametrik: [], bloklar: {}, yeni: [bek.yeni[0], bek.yeni[1]], vitrin: {},
  };
  const v1Acik = ozetAc(JSON.parse(JSON.stringify(v1)));
  const v1Tamam = esit(v1Acik.yeni, [bek.yeni[0], bek.yeni[1]]);
  rapor("6 IKI SURUM: canli cozucu v2 (dizi) ve v1 (sozluk) artefakti da BIREBIR acar",
    v2Tamam && v1Tamam, "v2 " + (v2Tamam ? "OK" : "SAPTI") + " | v1 " + (v1Tamam ? "OK" : "SAPTI"));

  // ---- 7: BAYAT ISTEMCI (onbellekteki eski kod + yeni artefakt) — BOS KART cizmemeli
  const bayat = bayatIstemciOzetAc(JSON.parse(karisik.ham));
  const bayatKartlar = []
    .concat(bayat.parametrik || [])
    .concat(Object.keys(bayat.bloklar || {}).reduce((t, k) => t.concat(bayat.bloklar[k]), []))
    .concat(bayat.yeni || []);
  const bosKart = bayatKartlar.filter((k) => !k || typeof k !== "object" || !k.id).length;
  const bozukKapak = bayatKartlar.filter((k) => k && typeof k.gorsel === "string"
    && k.gorsel && k.gorsel.indexOf("://") === -1).length;
  const degerBozulan = bayatKartlar.filter((k) => {
    const kaynak = karisikUrun.find((p) => p.id === k.id);
    if (!kaynak) { return true; }
    const b = beklenenKart(kaynak);
    return k.baslik !== b.baslik || k.fiyat !== b.fiyat || k.kategori !== b.kategori
      || (k.tur || "") !== (b.tur || "");
  }).length;
  rapor("7 BAYAT ISTEMCI: 11 Agu cozucusu v3'u alirsa BOS KART yok, fiyat/beyan BOZULMAZ",
    bosKart === 0 && degerBozulan === 0,
    "kart " + bayatKartlar.length + " | bos kart " + bosKart + " | fiyat/beyan sapmasi "
    + degerBozulan + " | kapagi kisalan (yer tutucuya duser) " + bozukKapak
    + " | `yeni` kuyrugu " + (bayat.yeni || []).length + " kart");

  console.log("");
  console.log("OLCUM: karisik fikstur ozet.json %d B | sifir-ortusme %d B | tam-ortusme %d B",
    karisik.bayt, sifir.bayt, tam.bayt);
  if (kirmizi) {
    console.log("\nSONUC: KIRMIZI ❌ — %d iddia dustu (%d gecti).", kirmizi, gecti);
    return 1;
  }
  console.log("\nSONUC: YESIL ✅ — %d iddia gecti.", gecti);
  return 0;
}

// --------------------------------------------------------------------------- mutasyon
// Her mutant DAR: yalnizca bu testin olctugu eksenin yakalayabilecegi bir bozulma.
// Mutant DAIMA KOPYAYA uygulanir; gercek agac degismez.
const MUTANTLAR = [
  ["M-A istemci: gorsel onegini GERI EKLEMEZ", "index",
    "        out.gorsel = onek + out.gorsel;", "        out.gorsel = out.gorsel;",
    "onek dusuruldu ama geri eklenmezse kapak URL'si KISA kalir (kart yer tutucuya duser)"],
  ["M-B istemci: `yeniRef` kolu HIC calismaz", "index",
    "    if(d.yeniRef){", "    if(false){",
    "referansli kesit acilmazsa `yeni` kuyrugu BOSALIR (ilk boyama kart kaybeder)"],
  ["M-C istemci: referans cozer ama TAM karti dusurur", "index",
    "        var kart = (typeof oge === \"string\") ? havuz[oge] : kartAc(oge);",
    "        var kart = (typeof oge === \"string\") ? havuz[oge] : null;",
    "sifir-ortusme halinde (yarin) `yeni` bosalir — bugunku %100 ortusmede gorunmez"],
  ["M-D derleme: SURUM BUMP dusuruldu (v3 alani basiliyor, surum 2)", "build",
    "            \"surum\": OZET_SURUM,", "            \"surum\": 2,",
    "bayat istemciye yeni temsil 'eski surum' etiketiyle verilirse kimse fark etmez"],
  ["M-E derleme: onek dusuruldu ama `gorselOnek` basligi BASILMADI", "build",
    "            \"gorselOnek\": OZET_GORSEL_ONEK,", "",
    "kendini tanimlamayan artefakt: istemci onegi geri EKLEYEMEZ"],
  ["M-F derleme: referans havuz uyelugu DOGRULANMADAN verilir", "build",
    "            s_yeni.append(kimlik if (kimlik is not None\n"
    + "                                     and havuz_dizin.get(kimlik) == dizi) else dizi)",
    "            s_yeni.append(kimlik if kimlik is not None else dizi)",
    "havuzda OLMAYAN karta referans = istemcide DUSEN kart (sessiz kayip)"],
];

function mutasyonKosumu() {
  console.log("=== MUTASYON: test GERCEKTEN yuk tasiyor mu? (hepsi KIRMIZI yanmali)\n");
  const indexKaynak = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
  const buildKaynak = fs.readFileSync(path.join(KOK, "tools", "build.py"), "utf8");
  let tut = 0;
  for (const [ad, hedef, eski, yeni, gerekce] of MUTANTLAR) {
    const kaynak = hedef === "index" ? indexKaynak : buildKaynak;
    if (kaynak.split(eski).length - 1 !== 1) {
      olculemedi("MUTASYON CAPASI KAYIP/COKLU (" + ad + "): " + JSON.stringify(eski.slice(0, 60)));
    }
    const mutant = kaynak.replace(eski, yeni);
    let argv;
    let temizle = null;
    if (hedef === "index") {
      const yol = path.join(GECICI, "mutant-index-" + (++_no) + ".html");
      fs.writeFileSync(yol, mutant, "utf8");
      argv = ["--index", yol];
    } else {
      // build.py ROOT'u KENDI konumundan turetir -> mutant kopya tools/ icinde durmali.
      const yol = path.join(KOK, "tools", "_mutant-ozet-build.py");
      fs.writeFileSync(yol, mutant, "utf8");
      temizle = yol;
      argv = ["--build", yol];
    }
    const r = spawnSync(process.execPath, [__filename].concat(argv), { encoding: "utf8" });
    if (temizle) { try { fs.unlinkSync(temizle); } catch (e) { /* yok */ } }
    const kirmiziMi = r.status === 1 || r.status === 2;
    tut += kirmiziMi ? 1 : 0;
    console.log("  %s %s", kirmiziMi ? "✔ KIRMIZI (rc=" + r.status + ")" : "✘ YESIL KALDI", ad);
    console.log("      gerekce: %s", gerekce);
    const dusen = String(r.stdout || "").split("\n").filter((s) => s.indexOf("✘") !== -1);
    if (dusen.length) { console.log("      yakalandi:%s", dusen[0].slice(0, 140)); }
    else if (kirmiziMi) { console.log("      yakalandi: %s", String(r.stderr || r.stdout || "").trim().split("\n").pop().slice(0, 140)); }
  }
  console.log("");
  if (tut !== MUTANTLAR.length) {
    console.log("MUTASYON: KALDI — %d/%d mutant kirmizi yandi, test OLU IDDIA tasiyor",
      tut, MUTANTLAR.length);
    return 1;
  }
  console.log("MUTASYON: GECTI — %d/%d mutant KIRMIZI (iddia CANLI).", tut, MUTANTLAR.length);
  return 0;
}

let rc = 2;
try {
  rc = process.argv.indexOf("--mutasyon") !== -1 ? mutasyonKosumu() : kosum();
} finally {
  try { fs.rmSync(GECICI, { recursive: true, force: true }); } catch (e) { /* yok */ }
}
process.exit(rc);
