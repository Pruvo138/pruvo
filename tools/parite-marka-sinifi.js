#!/usr/bin/env node
"use strict";
/**
 * MARKA KATLAMA SINIFI — "markaKatla(V) !== V" olan marka degerleri, TEK GOVDEDEN.
 *
 * NEDEN VAR (olculdu 10 Agu 2026): index.html `markaKatla()` sorgu/cip degerini ONEK
 * kuraliyla katliyor ("Toyota 86" -> "Toyota", "KIA" -> "Kia", "Mercedes-Benz" ->
 * "Mercedes"). Uc (`/ara`) degeri HAM baglayinca bu degerlerde site ile uc AYRISIYOR.
 * Ayrisim parite testlerinde GORUNMUYORDU:
 *   · tools/parite-test.js  `marka=` eksenini `markalar.slice(0,150)` / `markalar[i % ...]`
 *     (i < 100) ile ornekluyordu -> sinifin 32 uyesinden 1'i ornege giriyordu (olculdu:
 *     uye indeksleri 27, 657, 660, 1080 ... 2571; ilk 100'de YALNIZ 1). Kapsam KATALOG
 *     SIRASINA bagliydi: bir urun partisi diziyi yeniden siralayinca alarm hicbir sey
 *     duzelmeden yesile donebiliyordu ([[pencere-goreli-alarm-kendini-sonduruyor]] ile
 *     ayni sinif: olculen yuzey tabana gore turuyordu).
 *   · tools/parite-ege.js korpusunda `marka=` FILTRE ekseni HIC YOKTU.
 *
 * 🔴 UYELIK ELLE LISTE DEGILDIR. Sinif `index.html`in GERCEK `markaKatla`sindan
 * (tools/index-arama-referansi.js uzerinden AYIKLANIP KOSTURULAN govde) TURETILIR ve
 * SIRALANIR: kapsam katalog sirasindan bagimsizdir, kural degisince sinif kendiliginde
 * degisir. Elle defter tutsaydik ikiz tanim sessizce ayrisirdi
 * ([[ikiz-tanim-sessiz-ayrisma]]) ve "32" gibi bir sabit ilk katalog partisinde bayatlardi
 * ([[envanter-drift-parti-basina]]).
 *
 * 🔴 FAIL-CLOSED: referans kurulamazsa (capa tutmadi / cip indeksi uretilemedi) HATA
 * atilir; cagiran bunu OLCULEMEDI'ye (cikis 3) cevirir, sessiz YESIL'e DEGIL.
 *
 * KONTROL CAPALARI: `markaKatla(V) === V` olan degerler sinifin DISINDADIR ve korpusta
 * BOZULMADAN kalmalidir — yoksa "her marka degeri kirmizi yaniyor" ile "sinif kirmizi
 * yaniyor" ayirt edilemez ([[beyan-edilmis-survivor]] / kontrol mutanti ilkesi).
 */

const REFERANS = require("./index-arama-referansi.js");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

/** Katalog yolu: PARITE_URUNLER verilirse o, yoksa bu agacin urunler.json'u. */
const URUNLER_YOLU = process.env.PARITE_URUNLER || path.join(__dirname, "..", "urunler.json");

/**
 * D1 uretim govdesinin urettigi marka_kanon haritasini al.
 * Uc bu kolonu OKUR; yerel model de AYNI turetmeyi kullanir — ikiz tanim YOK.
 * @param {string} urunlerYolu
 * @returns {Object}  {id: JSON metin}
 */
function markaKanonHaritasiAl(urunlerYolu) {
  const betik = path.join(__dirname, "marka-kanon-uret.py");
  const cikti = execFileSync("python3", [betik, "--urunler", urunlerYolu], {
    encoding: "utf8", maxBuffer: 64 * 1024 * 1024,
  });
  return JSON.parse(cikti);
}

/**
 * Kontrol capalari — KATLANMAYAN (markaKatla(V) === V) marka degerleri.
 * Bunlar SINIF UYELIGI DEFTERI DEGILDIR (uyelik markaKatla'dan turer); yanlis-pozitif
 * nobetidir: bu degerler bir gun KATLANIR hale gelirse capa BAYAT demektir ve
 * tools/parite-kapsam-test.js bunu fail-closed KIRMIZI yakar.
 */
const KONTROL_CAPALARI = ["Astra H", "Focus ST", "Golf 4", "Land Rover"];

/** Korpusta tutulacak asgari kontrol degeri sayisi (spec kabul 2b). */
const KONTROL_ASGARI = 10;

class SinifHatasi extends Error {
  constructor(mesaj) { super(mesaj); this.name = "SinifHatasi"; this.olcum = true; }
}

// 🔴 ONBELLEK ANAHTARI = DIZI KIMLIGI (uzunluk/ilk-id DEGIL). Fikstur harness'i TEK
// surecte birden cok SENTETIK katalog kurar; bunlar ayni uzunlukta ve ayni ilk id ile
// gelebilir. Deger-anahtarli bir onbellek o senaryolarda BASKA katalogun sinifini
// dondurur ve ayrisma sessizce gizlenirdi. WeakMap kimlige baglidir, sizdirmaz.
const _bellek = new WeakMap();

/**
 * Katalogun marka degeri evrenini SINIF / KONTROL diye ikiye ayirir.
 * @param {Array} urunler  katalog (urunler.json dizisi)
 * @returns {{evren:number, uyeler:string[], kontroller:string[],
 *            katla:Function, uyeMi:Function, kontrolDegerleri:string[]}}
 *   uyeler/kontroller SIRALIDIR -> katalog sirasindan BAGIMSIZ.
 */
function markaSinifi(urunler) {
  if (!Array.isArray(urunler)) {
    throw new SinifHatasi("marka sinifi: katalog dizi DEGIL -> sinif turetilemez");
  }
  if (_bellek.has(urunler)) { return _bellek.get(urunler); }

  let R;
  try { R = REFERANS.referans(); } catch (e) {
    throw new SinifHatasi("site arama referansi KURULAMADI (" + (e && e.message) +
      ") -> marka katlama sinifi TURETILEMEDI");
  }
  if (typeof R.markaKatla !== "function") {
    throw new SinifHatasi("referansta markaKatla YOK -> sinif turetilemez");
  }

  const markaKanon = markaKanonHaritasiAl(URUNLER_YOLU);

  const evren = [];
  const gorulen = new Set();
  for (const p of urunler) {
    for (const m of (p && p.marka) || []) {
      if (typeof m === "string" && m.length && !gorulen.has(m)) { gorulen.add(m); evren.push(m); }
    }
  }
  if (!evren.length) {
    throw new SinifHatasi("marka evreni BOS — 'hic marka yok' bir kapsam KANITI DEGIL");
  }

  const uyeler = [];
  const kontroller = [];
  for (const v of evren) { (R.markaKatla(v) !== v ? uyeler : kontroller).push(v); }
  // 🔴 SIRALAMA = KAPSAMIN KATALOG SIRASINDAN BAGIMSIZLIGI. Yeni bir urun partisi
  // evrenin GORULME sirasini degistirir; sirali kume degismez.
  uyeler.sort();
  kontroller.sort();

  // Kontrol degerleri: capalar (evrende olanlar) + sirali kuyruktan tamamlama.
  const kontrolKume = new Set(kontroller);
  const secilen = KONTROL_CAPALARI.filter((v) => kontrolKume.has(v));
  for (const v of kontroller) {
    if (secilen.length >= KONTROL_ASGARI) break;
    if (secilen.indexOf(v) === -1) secilen.push(v);
  }

  const sonuc = {
    evren: evren.length,
    uyeler,
    kontroller,
    kontrolDegerleri: secilen,
    markaKanon,
    katla: (v) => R.markaKatla(v),
    // Uc yuklemi: p.marka ∋ HAM(v) OR p.marka_kanon ∋ katla(v).
    // marka_kanon D1 uretim govdesi (d1-sync.py:1302) tarafindan doldurulur;
    // yerel model AYNI govdeden beslenir — ikiz tanim / ikinci kopya YOK.
    uyeMi: (p, deger) => {
      const ham = deger;
      const markaDizisi = (p && p.marka) || [];
      if (markaDizisi.indexOf(ham) !== -1) return true;
      const kanon = R.markaKatla(ham);
      const mk = markaKanon[p && p.id];
      if (!mk) return false;
      try { return JSON.parse(mk).indexOf(kanon) !== -1; } catch (_) { return false; }
    },
  };
  _bellek.set(urunler, sonuc);
  return sonuc;
}

/**
 * SINIF-BILINCLI KORPUS CEKIRDEGI — iki parite testinin de `marka=` ekseni buradan gelir.
 * Cekirdek `hedef` (sorgu sayisi) argumaniyla KIRPILMAZ: kirpilirsa kapsam yine orneklem
 * kazasina baglanirdi.
 *
 * SITE ekseni (kat/marka'li 3'lu):
 *   {q:"",         marka:V}  SAF `marka=` ekseni — en temiz olcum
 *   {q:katla(V),   marka:V}  kanonik ad + sinif uyesi filtre (iki dal birlikte)
 *   {q:V,          marka:"Tümü"}  serbest metin (spec 1A: "hem marka= hem q")
 * EGE ekseni: `/ara?mod=ege` BOS q'yu 400 ile reddeder -> q DAIMA katla(V).
 */
function cekirdekSorgular(urunler, yuzey) {
  const S = markaSinifi(urunler);
  const cikti = [];
  const degerler = S.uyeler.concat(S.kontrolDegerleri);
  for (const v of degerler) {
    if (yuzey === "ege") {
      cikti.push({ q: S.katla(v), marka: v });
    } else {
      cikti.push({ q: "", kat: "Tümü", marka: v });
      cikti.push({ q: S.katla(v), kat: "Tümü", marka: v });
      cikti.push({ q: v, kat: "Tümü", marka: "Tümü" });
    }
  }
  return { S, sorgular: cikti };
}

module.exports = { markaSinifi, cekirdekSorgular, KONTROL_CAPALARI, KONTROL_ASGARI,
  SinifHatasi };
