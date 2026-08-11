/* ONIZLEME GORUNURLUK KAPISI — "musterinin sectigi RENK onizlemeye ULASIYOR MU" +
   "kabartma YAZI ekranda GORUNUYOR MU" (olcum, goz karari degil).

   NEDEN VAR (Okan sikayeti + olculmus kok neden, 2026-07-29, olcuye-ozel-cerceve):
     1) Renk secici onizlemeyi HIC etkilemiyordu: sayfa scripti (tools/build.py
        ONIZLEME_JS) rengi YALNIZ aile bazli sabit tablodan (ONIZLEME_RENKLER)
        okuyordu; #renkSec degeri hicbir yoldan viewer'a gitmiyordu.
     2) Kabartma yazi geometrisi MESH'TE VARDI (canli olcum: ayni geometri,
        yazi='' -> 1304 ucgen / z<=5.2 ; yazi='ZZZZZZZZ' -> 1624 ucgen, yazi
        bbox y[-83.5..-77.1] z[5.2..6.4] = alt kenarda 1,2 mm KABARTMA) ama
        EKRANDA gorunmuyordu: yazinin UST yuzu cerceve on yuzuyle AYNI normale
        sahip (ayni ton), yalniz 1,2 mm yan duvarlar ayrisiyordu ve o fark koyu
        cerceve renginde ~15/255 seviyedeydi.

   NE OLCER (dar, dogru etiket):
     A) RENK: secenekler.js onizlemeRengi() 3 renk icin 3 FARKLI RGB verir;
        build.py'nin URETTIGI sayfa scripti bu fonksiyonu GERCEKTEN cagirir ve
        secim degisince viewer'i YENIDEN BOYAR (sahte DOM + sahte viewer ile
        uctan uca kosulur, kopya mantik yazilmaz); ve 3 rengin RENDER'i farkli
        piksel ortalamasi uretir.
     B) YAZI: ayni kamerada yazili/yazisiz gorsel FARKI — yazi bolgesindeki
        piksel sayisi + azami ton farki esigi gecer. Yazi BOSKEN render calisir.

   NE OLCMEZ (iddia edilmez):
     * Yazinin OKUNUR oldugunu (font/harf ayrimi) kanitlamaz — yalniz ekranda
       ayirt edilebilir bir sinyal urettigini olcer.
     * Gercek WebGL surucusunun cikisini kanitlamaz; ayni matematik CPU'da
       nokta-ornekli kosar (MSAA yok -> gercek ekrandan DAHA KOTUMSER tahmin).
     * Uretilen URUNUN gercekten o renkte basildigini kanitlamaz (uretim yolu).
     * 2-RENK (yazi ayri renk) akisini KAPSAMAZ — bu kapinin olctugu sey TEK
       govde/TEK renk yolu. 2-renk ekseni 29 Tem'de acildi ve AYRI kapiya baglandi:
       eslem/-D tarafi tools/iki-govde-kapisi.py, worker+viewer+sayfa tarafi
       onizleme/test/iki-govde-kabul.mjs.

   Kosum: node onizleme/test/renk-yazi-gorunurluk.mjs        (CI: deploy.yml)
          node onizleme/test/renk-yazi-gorunurluk.mjs --stl A.stl B.stl
              (A=yazisiz, B=yazili GERCEK mesh ile ayni olcumu tekrarlar) */
"use strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
/* Rasterlestirici + fikstur yardimcilari ORTAK cekirdekten gelir (ikinci kopya YOK;
   ayni cekirdegi onizleme/test/iki-govde-kabul.mjs de kullanir). */
import { ZEMIN, kutu, ucgenNormali, modelKutusu, stlOku, ciz, ortalama, fark, mat4Vek }
  from "./ortak/raster.mjs";
/* Sahte sayfa cekirdegi (WebGL kaydedicisi + GERCEK secici ayristirici) de ORTAK —
   iki kapi ayni taklidi kullanir, ikinci kopya YOK. */
import { sahteGl, sorgu, ogeFabrikasi } from "./ortak/sahte-dom.mjs";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");

// ---------------------------------------------------------------- yukleme
const kum = { window: {}, globalThis: undefined, module: undefined };
kum.globalThis = kum;
vm.createContext(kum);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), kum);
vm.runInContext(fs.readFileSync(path.join(KOK, "jenerator", "viewer.js"), "utf8"), kum);
const SECENEK = kum.window.PRUVO_SECENEK;
const VIEWER = kum.window.PRUVO_VIEWER;

let hata = 0;
const olcumler = [];
function iddia(ad, kosul, detay) {
  const ok = !!kosul;
  console.log((ok ? "  [OK ] " : "  [KIRMIZI] ") + ad + (detay ? " -> " + detay : ""));
  if (!ok) { hata++; }
}

// ---------------------------------------------------------------- STL fikstur
/* Fikstur olculeri CANLI mesh'ten alinmistir (POST /api/onizleme/olustur,
   aile=olcuye-ozel-cerceve, acilik 100x150, kenar 12, derinlik 5,2, chamfer):
     govde bbox x[-62,1..62,1] y[-87,1..87,1] z[0..5,2]
     yazi  bbox y[-83,5..-77,1] z[5,2..6,4]  -> kabartma 1,2 mm, harf boyu 6,4 mm
     yazi ust yuz alani 130,02 mm^2 / 8 harf ('ZZZZZZZZ') -> cizgi kalinligi ~1,2 mm
   Fikstur bu SAYILARI tasir; gercek harf konturu yerine ayni topolojide
   (ince, dik yan duvarli, kabartma) cubuklar kullanilir. --stl ile gercek
   mesh uzerinde ayni olcum tekrarlanabilir. */
const OLCU = {
  disEn: 124.2, disBoy: 174.2, derinlik: 5.2,
  acilikEn: 100, acilikBoy: 150,
  yaziY0: -83.5, yaziY1: -77.1, kabartma: 1.2, cizgi: 1.2, harfAdet: 8
};

function cerceveMesh(yaziVar) {
  const t = [];
  const dx = OLCU.disEn / 2, dy = OLCU.disBoy / 2;
  const ax = OLCU.acilikEn / 2, ay = OLCU.acilikBoy / 2;
  // Cerceve = 4 kenar cubugu (aciklik ortada bos)
  kutu(t, -dx, dx, ay, dy, 0, OLCU.derinlik);          // ust
  kutu(t, -dx, dx, -dy, -ay, 0, OLCU.derinlik);        // alt
  kutu(t, -dx, -ax, -ay, ay, 0, OLCU.derinlik);        // sol
  kutu(t, ax, dx, -ay, ay, 0, OLCU.derinlik);          // sag
  if (yaziVar) {
    const h = OLCU.yaziY1 - OLCU.yaziY0;               // harf boyu 6,4
    const c = OLCU.cizgi;
    const genislik = 4.5;                              // harf eni
    const aralik = 5.6;
    const basla = -((OLCU.harfAdet - 1) * aralik + genislik) / 2;
    const z0 = OLCU.derinlik, z1 = OLCU.derinlik + OLCU.kabartma;
    for (let i = 0; i < OLCU.harfAdet; i++) {
      const x0 = basla + i * aralik;
      kutu(t, x0, x0 + genislik, OLCU.yaziY1 - c, OLCU.yaziY1, z0, z1);   // ust cizgi
      kutu(t, x0, x0 + genislik, OLCU.yaziY0, OLCU.yaziY0 + c, z0, z1);   // alt cizgi
      kutu(t, x0 + (genislik - c) / 2, x0 + (genislik + c) / 2,
           OLCU.yaziY0, OLCU.yaziY0 + h, z0, z1);                          // dikey cizgi
    }
  }
  return t;
}

// ---------------------------------------------------------------- rasterlestirici
/* Rasterlestirici + STL okuma ORTAK cekirdekte (./ortak/raster.mjs) — burada KOPYA
   YOKTUR. Kamera ve golgeleme yine viewer.js'in KENDI fonksiyonlarindan gelir
   (VIEWER._gorunum / VIEWER._golge); cekirdege VIEWER disaridan verilir.
   Rasterlestirme nokta-ornekli + z-tamponlu; WebGL'in MSAA'si YOK (kotumser). */

// ---------------------------------------------------------------- sahte sayfa
/* build.py'nin urun sayfasina bastigi ONIZLEME_JS metnini SAHTE DOM'da kosar.
   DOM, CANLI /urun/olcuye-ozel-cerceve/ sayfasinin duzenini taklit eder:
   kart-secim (KART_SECIM=true) -> renk BUTONLARI (#renkButonlar .renk-btn),
   #renkSec YOK. Onden secili renk yok; test once Beyaz'i secer.

   🔴 VIEWER TAKLIT EDILMEZ: gercek jenerator/viewer.js ayni kum havuzunda
   kosar, altina yalniz WebGL cagrilarini KAYDEDEN sahte baglam konur. Olculen
   sey GPU'ya giden uRenk uniform'unun ta kendisidir. (Ilk turda viewer sahte
   bir kol ile taklit edilmisti: "kol renkAyarla dondurmuyor" mutasyonu testten
   SESSIZCE gecti — taklit, kapinin korumasi gereken sozlesmeyi maskeliyordu.) */
/** Gecerli minik binary STL (12 ucgenlik kup) — viewer'in stlCoz'u kabul etsin. */
function kupStl() {
  const t = cerceveMesh(false).slice(0, 12);
  const b = Buffer.alloc(84 + t.length * 50);
  b.write("PRUVO test", 0);
  b.writeUInt32LE(t.length, 80);
  let o = 84;
  for (const v of t) {
    const n = ucgenNormali(v);
    for (const c of n) { b.writeFloatLE(c, o); o += 4; }
    for (const p of v) { for (const c of p) { b.writeFloatLE(c, o); o += 4; } }
    o += 2;
  }
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
}

async function sayfaKos(script, markup) {
  const { oge } = ogeFabrikasi();
  // Kap id'si / buton sinifi / "secili" sinif adi build.py'nin KENDI markup'indan.
  const btnYap = (ad) => oge({ sinif: [markup.btnSinif], _oz: { "data-renk": ad } });
  const btnSiyah = btnYap("Siyah"), btnBeyaz = btnYap("Beyaz"), btnGri = btnYap("Gri");
  const renkBtnlar = [btnSiyah, btnBeyaz, btnGri];
  const kap = oge({ id: markup.kapId, sinif: ["renk-butonlar"], cocuk: renkBtnlar });
  // TUZAK: malzeme cipleri de canli sayfada ayni "secili" sinifini tasir —
  // kapsamini kaybeden bir secici (or. ".secili") yanlis ogeyi yakalar.
  const tuzakCip = oge({ sinif: ["fil-cip", markup.seciliSinif], _oz: { "data-renk": "TUZAK" } });
  const cipKap = oge({ id: "filCipler", cocuk: [tuzakCip] });
  let secili = btnBeyaz;           // musteri Beyaz sectti
  function seciliYap(b) {
    for (const x of renkBtnlar) {
      x.sinif = x.sinif.filter((c) => c !== markup.seciliSinif);
    }
    b.sinif = b.sinif.concat([markup.seciliSinif]);
    secili = b;
  }
  const ogeler = {
    onizleBtn: oge({ id: "onizleBtn" }), onizlemeKutu: oge({ id: "onizlemeKutu" }),
    onizlemeDurum: oge({ id: "onizlemeDurum" }), onizlemeTuval: oge({ id: "onizlemeTuval" })
  };
  seciliYap(btnBeyaz);
  // Belge koku: renk butonlari kabi + malzeme cipi tuzagi + tekil ogeler.
  const kokOge = oge({ id: "belge", cocuk: [kap, cipKap].concat(Object.values(ogeler)) });
  const kayit = {};                // GPU'ya giden uniform'lar (ortak/sahte-dom.mjs)
  const gl = sahteGl(kayit);
  const uRenkKayit = kayit.renkler; // uRenk degerleri (sirayla)
  ogeler.onizlemeTuval = Object.assign(ogeler.onizlemeTuval, {
    getContext: () => gl, clientWidth: 380, clientHeight: 320,
    width: 0, height: 0, style: {}, setPointerCapture: () => {}
  });
  let istekAdedi = 0;
  const govde = kupStl();
  const sahte = {
    console, Float32Array, ArrayBuffer, DataView, WeakMap, Map, Math, Infinity, NaN,
    // rAF SENKRON OLAMAZ: viewer'in cizim-planlama kilidi (cizimIste) once
    // atanir, sonra geri cagri gelir; senkron kosarsak kilit ASILI kalir ve
    // hicbir cizim olmaz (bu taklidin kusuru, urunun degil).
    requestAnimationFrame: (fn) => { Promise.resolve().then(fn); return 1; },
    devicePixelRatio: 1,
    addEventListener: () => {}, removeEventListener: () => {},
    document: {
      getElementById: (id) => ogeler[id] || null,
      querySelector: (s) => sorgu(kokOge, s, false),
      querySelectorAll: (s) => sorgu(kokOge, s, true),
      addEventListener: () => {}
    },
    URUN: { id: AILE },
    PRUVO_KONF: {
      hazir: () => true, gecerliMi: () => true,
      satiraYaz: () => ({ parametreler: { acilik_eni: 100 } })
    },
    fetch: () => {
      istekAdedi++;
      return Promise.resolve({
        ok: true, headers: { get: () => null },
        arrayBuffer: () => Promise.resolve(govde)
      });
    }
  };
  sahte.window = sahte;
  sahte.globalThis = sahte;
  vm.createContext(sahte);
  // GERCEK moduller (taklit yok): secenekler.js + viewer.js ayni kum havuzunda.
  vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), sahte);
  vm.runInContext(fs.readFileSync(path.join(KOK, "jenerator", "viewer.js"), "utf8"), sahte);
  vm.runInContext(script, sahte);
  ogeler.onizleBtn.atesle("click");
  for (let i = 0; i < 12; i++) { await Promise.resolve(); }   // fetch zincirini bosalt
  const ilkSayi = uRenkKayit.length;
  // Musteri rengi Gri'ye cevirir. SIRA CANLIDAKIYLE AYNI: build.py'nin kart
  // dinleyicisi sayfada ONCE kayitli oldugundan tiklamada once "secili" sinifi
  // tasinir, SONRA onizlemenin renkTazele'si okur. Burada da once tasinir.
  seciliYap(btnGri);
  btnGri.atesle("click");
  for (let i = 0; i < 6; i++) { await Promise.resolve(); }
  return {
    ilkRenk: ilkSayi ? uRenkKayit[ilkSayi - 1] : null,
    sonrakiRenk: uRenkKayit.length > ilkSayi ? uRenkKayit[uRenkKayit.length - 1] : null,
    istekAdedi,
    cizim: kayit.cizim || 0
  };
}

// ---------------------------------------------------------------- olcum
const AILE = "olcuye-ozel-cerceve";
// Gercek sayfa tuvali: genislik %100 (opsiyon sutunu ~380 CSS px), yukseklik 320 px;
// canvas.width = CSS * devicePixelRatio. dpr=1 EN KOTU (en az piksel) hali.
const TUVAL = [[380, 320, "dpr=1"], [760, 640, "dpr=2"]];
const TON_ESIGI = 6;    // 6/255 ton farki = ekranda ayirt edilebilir alt sinir

const argSTL = process.argv.indexOf("--stl");
let yazisiz, yazili, kaynakAdi;
if (argSTL > 0) {
  yazisiz = stlOku(process.argv[argSTL + 1]);
  yazili = stlOku(process.argv[argSTL + 2]);
  kaynakAdi = "GERCEK STL (" + path.basename(process.argv[argSTL + 1]) + " / " +
              path.basename(process.argv[argSTL + 2]) + ")";
} else {
  yazisiz = cerceveMesh(false);
  yazili = cerceveMesh(true);
  kaynakAdi = "fikstur (canli olculerden turetilmis)";
}
// Kamera IKI render'da da AYNI olmali: yazi bbox'i degistirdigi icin kamera
// yazili mesh'ten turetilseydi tum gorunti kayar, fark olcumu anlamsizlasirdi.
const KAMERA = modelKutusu(yazisiz);

console.log("== ONIZLEME GORUNURLUK KAPISI ==");
console.log("kaynak mesh: " + kaynakAdi +
            "  (yazisiz " + yazisiz.length + " ucgen / yazili " + yazili.length + " ucgen)");
console.log("isik modeli: " + JSON.stringify(VIEWER._ISIK));

// --- A) RENK ---------------------------------------------------------------
console.log("\n-- A) RENK: musteri secimi onizlemeye ULASIYOR MU --");
const RENKLER = ["Siyah", "Beyaz", "Gri"];
iddia("A0 secenekler.js onizlemeRengi() var",
      typeof SECENEK.onizlemeRengi === "function");
if (typeof SECENEK.onizlemeRengi !== "function") {
  console.log("\nSONUC: KIRMIZI (onizlemeRengi yok)");
  process.exit(1);
}
const rgb = {};
for (const r of RENKLER) { rgb[r] = SECENEK.onizlemeRengi(AILE, r); }
iddia("A1 3 renk -> 3 gecerli RGB",
      RENKLER.every((r) => Array.isArray(rgb[r]) && rgb[r].length === 3 &&
                    rgb[r].every((x) => typeof x === "number" && x >= 0 && x <= 1)),
      JSON.stringify(rgb));
iddia("A2 3 renk -> 3 FARKLI RGB",
      new Set(RENKLER.map((r) => JSON.stringify(rgb[r]))).size === 3);

// A3: RENDER PIKSELLERI — her renk gercekten farkli bir goruntu uretiyor mu
const [W0, H0] = TUVAL[0];
const renderler = {};
for (const r of RENKLER) { renderler[r] = ciz(VIEWER, yazili, rgb[r], KAMERA, W0, H0); }
const ort = {};
for (const r of RENKLER) { ort[r] = ortalama(renderler[r].luma); }
console.log("     render ortalama ton (0-255): " +
            RENKLER.map((r) => r + "=" + ort[r].toFixed(1)).join("  "));
olcumler.push("renk ortalama ton: " + RENKLER.map((r) => r + "=" + ort[r].toFixed(1)).join(" "));
let renkCiftOk = true, enKucukRenkFark = Infinity;
for (let i = 0; i < RENKLER.length; i++) {
  for (let j = i + 1; j < RENKLER.length; j++) {
    const f = fark(renderler[RENKLER[i]], renderler[RENKLER[j]], TON_ESIGI);
    enKucukRenkFark = Math.min(enKucukRenkFark, f.piksel);
    if (f.piksel < 1000) { renkCiftOk = false; }
  }
}
iddia("A3 her renk cifti RENDER'da ayrisir (>=1000 piksel, >=" + TON_ESIGI + " ton)",
      renkCiftOk, "en az ayrisan cift: " + enKucukRenkFark + " piksel");

// A4: sayfa scripti (build.py ONIZLEME_JS) rengi GERCEKTEN baglıyor mu — uctan uca.
// Olculen sey build.py'nin CANLI SAYFAYA BASTIGI metnin ta kendisi (kopya degil).
const buildPy = fs.readFileSync(path.join(KOK, "tools", "build.py"), "utf8");
const m = buildPy.match(/\nONIZLEME_JS = """\n([\s\S]*?)\n"""\n/);
iddia("A4a build.py ONIZLEME_JS blogu okundu", !!m);
/* SAHTE DOM'un capasi build.py'nin KENDI markup'i: kap id'si, buton sinifi ve
   "secili" sinif adi buradan okunur. Markup ile secici ayrisirsa (or. kap adi
   degisir, secici eski adda kalir) A4b/A4c kirmizi yanar — taklit artik
   "her seciciyi kabul eden" bir yastik DEGILDIR. */
const mKap = buildPy.match(/<div class="renk-butonlar" id="([A-Za-z0-9_-]+)">/);
/* 🔴 BUTON SINIFI ARTIK SABIT DEGIL, HESAPLANIYOR (11 Agu): onden secili renk geldiginden
   markup `class="%s"` basiyor ve degeri `_cls(r)` uretiyor. Eski capa markup'taki DUZ
   literale bakiyordu -> hicbir sey eslesmedi ve A4a2 kirmizi yandi (merge oncesi yesildi).
   Capa `_cls`'in KENDISINE tasindi: TABAN sinif else-dalindan, ONDEN SECILI varyant
   if-dalindan okunur. FAIL-CLOSED korunur — `_cls` sekil degistirirse eslesme yok, A4a2
   yine kirmizi. Duz literal kolu geride birakildi: markup sabite DONERSE de capa tutar. */
const mBtnDuz = buildPy.match(/<button type="button" class="([A-Za-z0-9_-]+)" data-renk=/);
/* BOSLUGA TOLERANSLI: capa BICIMLENDIRMEYE degil YAPIYA baksin. Ilk surumde `return`/`else`
   sonrasi TEK bosluk bekleniyordu; davranisi degistirmeyen cift bosluk kapiyi KIRMIZI
   yakiyordu (kontrol mutanti D5 ile olculdu) — yanlis-pozitif, bu depoda yayin durduran sinif. */
const mCls = buildPy.match(
  /def\s+_cls\s*\(\s*r\s*\)\s*:\s*\n\s*return\s+"([A-Za-z0-9_-]+(?:\s+[A-Za-z0-9_-]+)*)"\s+if\s[^\n]*?\selse\s+"([A-Za-z0-9_-]+)"/);
const mBtn = mBtnDuz || (mCls && { 1: mCls[2] });
const mSec = buildPy.match(/rbtnlar\[n\]\.classList\.toggle\("([A-Za-z0-9_-]+)"/);
iddia("A4a2 build.py renk markup capalari okundu (kap id / buton sinifi / secili sinifi)",
      !!(mKap && mBtn && mSec),
      JSON.stringify([mKap && mKap[1], mBtn && mBtn[1], mSec && mSec[1]]));
/* YENI EKSEN (11 Agu): onden secili sinif ile JS'in TOGGLE ettigi sinif ayrisirsa, buton
   SECILI GORUNUR ama script onu secili SAYMAZ (ya da tersi) -> kullanicinin gordugu ile
   durumun celistigi sessiz ariza. Ikisi tek kaynaktan turemeli: `_cls` if-dali TAM olarak
   "<taban> <secili>" olmali. `_cls` yoksa (markup sabite dondu) eksen ATLANMAZ, ölçülemez
   sayilmaz: taban+secili zaten ayrisamaz, iddia tautoloji olmadan gecer. */
/* Kiyas TEK kanonik normallestirmeden gecer (kabul araligi = kiyas araligi): sinif listesi
   bosluga gore bolunur, bos parcalar atilir. Boylece "renk-btn  secili" ile
   "renk-btn secili" AYNI sayilir; ayrisan tek sey SINIF ADLARIDIR. */
const sinifKume = (s) => String(s || "").trim().split(/\s+/).filter(Boolean).join(" ");
iddia("A4a3 onden secili buton sinifi = taban + JS'in toggle ettigi sinif (ikiz ayrismaz)",
      !!(mSec && (!mCls || sinifKume(mCls[1]) === sinifKume(mCls[2] + " " + mSec[1]))),
      mCls ? ("_cls secili-dali: " + JSON.stringify(sinifKume(mCls[1])) + " · beklenen: " +
              JSON.stringify(sinifKume((mCls[2] || "") + " " + (mSec ? mSec[1] : "?"))))
           : "_cls YOK (markup duz literal) -> ayrisma yuzeyi kapali");
if (m && mKap && mBtn && mSec) {
  const s = await sayfaKos(m[1],
    { kapId: mKap[1], btnSinif: mBtn[1], seciliSinif: mSec[1] });
  iddia("A4b sayfa scripti onizlemeyi SECILEN renkle boyar",
        s.ilkRenk && JSON.stringify(s.ilkRenk) === JSON.stringify(rgb.Beyaz),
        "viewer'a giden: " + JSON.stringify(s.ilkRenk) +
        " (secim 'Beyaz' -> " + JSON.stringify(rgb.Beyaz) + ")");
  iddia("A4c renk SECIMI degisince onizleme YENIDEN boyanir (yeniden indirmeden)",
        s.sonrakiRenk && JSON.stringify(s.sonrakiRenk) === JSON.stringify(rgb.Gri) &&
        s.istekAdedi === 1,
        "yeniden boyama: " + JSON.stringify(s.sonrakiRenk) +
        " (secim 'Gri' -> " + JSON.stringify(rgb.Gri) + ")" +
        " · derleyici istegi: " + s.istekAdedi + " (1 olmali)");
}

// --- C) EKRAN ile OLCUM AYNI ISIK MODELI Mi --------------------------------
/* ÖLÇÜLDÜ (bagimsiz curutme, 29 Tem): B eksenindeki tum sayilar viewer'in JS
   ikizinden (_golge/_carpan) geliyor; EKRANI boyayan sey ise GLSL parca
   golgelendiricisidir. GLSL'den parlaklik terimini silen mutasyon — canlida
   Okan'in "yazi gorunmuyor" sikayetini AYNEN geri getirir — kapidan SESSIZCE
   geciyordu: olcum parlak, ekran mat. Bu eksen GLSL METNINDEKI sayilarin
   ISIK tablosundan turedigini dogrular; ikisi ayrisirsa kirmizi yanar. */
console.log("\n-- C) GLSL (ekran) ile JS ikizi (olcum) ayni ISIK sayilarindan mi --");
const FS = VIEWER._FS, ISIK = VIEWER._ISIK;
function glSayi(re, ad, beklenen) {
  const mm = FS.match(re);
  const v = mm ? parseFloat(mm[1]) : null;
  iddia("C " + ad + " GLSL'de ISIK ile ayni", v !== null && Math.abs(v - beklenen) < 1e-9,
        "GLSL=" + v + " · ISIK=" + beklenen);
}
glSayi(/uRenk \* \(\s*([0-9.eE+-]+)/, "taban", ISIK.taban);
glSayi(/\+\s*([0-9.eE+-]+)\s*\* i1/, "k1", ISIK.k1);
glSayi(/\+\s*([0-9.eE+-]+)\s*\* i2/, "k2", ISIK.k2);
glSayi(/\+\s*([0-9.eE+-]+)\s*\* pow\(ip,/, "kParlak", ISIK.kParlak);
glSayi(/pow\(ip,\s*([0-9.eE+-]+)\)/, "us", ISIK.us);
const yonler = [...FS.matchAll(/normalize\(vec3\(([^)]*)\)\)/g)]
  .map((x) => x[1].split(",").map((t) => parseFloat(t)));
iddia("C GLSL'deki 3 isik yonu ISIK tablosuyla ayni",
      yonler.length === 3 &&
      JSON.stringify(yonler) === JSON.stringify([ISIK.yon1, ISIK.yon2, ISIK.yonParlak]),
      JSON.stringify(yonler));

// --- B) YAZI ---------------------------------------------------------------
console.log("\n-- B) YAZI: kabartma yazi EKRANDA gorunuyor mu --");
// Yazinin geometrisi mesh'te mi (bagimsiz on kosul)
const yaziUcgen = yazili.filter((v) => Math.max(...v.map((p) => p[2])) > OLCU.derinlik + 1e-4);
iddia("B0 yazi geometrisi mesh'te (z > govde derinligi)", yaziUcgen.length > 0,
      yaziUcgen.length + " ucgen kabartma");
iddia("B1 ayni geometri + farkli yazi -> FARKLI mesh",
      yazili.length !== yazisiz.length,
      yazisiz.length + " -> " + yazili.length + " ucgen");

// Yazi bolgesi ekran kutusu: yazi ucgenlerinin izdusumu
function ekranKutusu(ucgenler, kamera, W, H) {
  const g = VIEWER._gorunum(kamera, W / H, VIEWER._BASLANGIC.yaw,
                            VIEWER._BASLANGIC.pitch, VIEWER._BASLANGIC.zoom);
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const v of ucgenler) {
    for (const p of v) {
      const c = mat4Vek(g.proj, mat4Vek(g.goruntu, mat4Vek(g.donus, [p[0], p[1], p[2], 1])));
      if (c[3] <= 1e-6) { continue; }
      const x = (c[0] / c[3] * 0.5 + 0.5) * W, y = (0.5 - c[1] / c[3] * 0.5) * H;
      x0 = Math.min(x0, x); x1 = Math.max(x1, x);
      y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
  }
  return { x0, x1, y0, y1 };
}

let yaziOk = true;
for (const [W, H, etiket] of TUVAL) {
  const kutuE = ekranKutusu(yaziUcgen, KAMERA, W, H);
  const a = ciz(VIEWER, yazisiz, rgb.Siyah, KAMERA, W, H);
  const b = ciz(VIEWER, yazili, rgb.Siyah, KAMERA, W, H);
  // Yalniz yazi bolgesi (izdusum kutusu) sayilir
  let piksel = 0, azami = 0;
  for (let y = Math.max(0, Math.floor(kutuE.y0)); y <= Math.min(H - 1, Math.ceil(kutuE.y1)); y++) {
    for (let x = Math.max(0, Math.floor(kutuE.x0)); x <= Math.min(W - 1, Math.ceil(kutuE.x1)); x++) {
      const d = Math.abs(a.luma[y * W + x] - b.luma[y * W + x]);
      if (d > azami) { azami = d; }
      if (d >= TON_ESIGI) { piksel++; }
    }
  }
  const kutuAlan = (Math.ceil(kutuE.x1) - Math.floor(kutuE.x0) + 1) *
                   (Math.ceil(kutuE.y1) - Math.floor(kutuE.y0) + 1);
  console.log("     " + etiket + " tuval " + W + "x" + H +
              " · yazi bolgesi " + Math.round(kutuE.x1 - kutuE.x0) + "x" +
              Math.round(kutuE.y1 - kutuE.y0) + " px (" + kutuAlan + " px)" +
              " · esigi (>=" + TON_ESIGI + ") asan: " + piksel +
              " px · azami ton farki: " + azami.toFixed(1));
  olcumler.push(etiket + ": yazi bolgesinde " + piksel + " px degisiyor, azami " +
                azami.toFixed(1) + "/255");
  // EN AZ tuvalin yazi bolgesinin %8'i + 25 ton fark: siyah cercevede bile
  // yazinin ayirt edilebilmesi icin gereken alt sinir.
  const yeter = piksel >= Math.max(20, kutuAlan * 0.08) && azami >= 25;
  iddia("B2 " + etiket + " yazi EKRANDA ayirt edilebilir", yeter,
        piksel + " px (>= " + Math.max(20, Math.round(kutuAlan * 0.08)) + ") · " +
        "azami " + azami.toFixed(1) + " ton (>= 25)");
  if (!yeter) { yaziOk = false; }
}

// B3: yazi BOSKEN onizleme yine calisir (bos render zemin DISI piksel uretmeli)
const bosRender = ciz(VIEWER, yazisiz, rgb.Siyah, KAMERA, W0, H0);
const zeminTon = 255 * (0.2126 * ZEMIN[0] + 0.7152 * ZEMIN[1] + 0.0722 * ZEMIN[2]);
let govdePiksel = 0;
for (let i = 0; i < bosRender.luma.length; i++) {
  if (Math.abs(bosRender.luma[i] - zeminTon) > 1) { govdePiksel++; }
}
iddia("B3 yazi BOSKEN onizleme calisir (govde ciziliyor)", govdePiksel > 1000,
      govdePiksel + " piksel govde");

console.log("\n== OLCUMLER ==");
for (const o of olcumler) { console.log("   " + o); }
console.log("\nSONUC: " + (hata ? "KIRMIZI ❌ (" + hata + " iddia)" : "YESIL ✅"));
process.exit(hata ? 1 : 0);
