/* ORTAK SAHTE SAYFA CEKIRDEGI — WebGL kaydedicisi + GERCEK secici ayristirici.
   (Kosulabilir test DEGIL: alt dizinde durur, tools/ci-kapsam-test.py kesfi yalnizca
    onizleme/test'in DOGRUDAN altina bakar. Burada iddia yok, yalniz olcum araci.)

   Iki kapi bunu kullanir:
     onizleme/test/renk-yazi-gorunurluk.mjs   (renk secimi ekrana ulasiyor mu)
     onizleme/test/iki-govde-kabul.mjs        (2-renk: iki govde, iki renk)
   Ikinci kopya tutulsaydi biri sertlesip digeri gevser, iki kapi ayni sayfayi
   olctugunu SANIP farkli seyler olcerdi.

   🔴 VIEWER TAKLIT EDILMEZ: gercek jenerator/viewer.js kum havuzunda kosar, altina
   yalnizca WebGL cagrilarini KAYDEDEN sahte baglam konur. Olculen sey GPU'ya giden
   uniform'larin ta kendisidir. (Bir turda viewer sahte bir kol ile taklit edilmisti;
   "kol renkAyarla dondurmuyor" mutasyonu testten SESSIZCE gecti — taklit, kapinin
   korumasi gereken sozlesmeyi maskeliyordu.)

   SECICI GERCEKTEN AYRISTIRILIR (olculmus maskeleme deligi, 29 Tem): onceki hal
   querySelector'a gelen seciciyi hic ayristirmiyor, ".secili" alt-dizesini gorunce
   dogru butonu donduruyordu -> seciciyi "#YOKBOYLEBIRKAP .renk-btn.secili" yapan
   mutasyon (canlida Okan'in sikayetini AYNEN geri getirir) kapidan SESSIZCE gecti. */
"use strict";

/** WebGL kaydedici. kayit.renkler: uRenk uniform'lari, kayit.donusler: uDonus
 *  matrisleri, kayit.cizim: drawArrays adedi, kayit.tamponlar: bufferData boylari. */
export function sahteGl(kayit) {
  const S = (ad) => ({ _tur: ad, _no: (kayit.tamponSayaci = (kayit.tamponSayaci || 0) + 1) });
  kayit.renkler = kayit.renkler || [];
  kayit.donusler = kayit.donusler || [];
  kayit.cizimler = kayit.cizimler || [];   // [{renk, adet}] — cizim BASINA
  return {
    VERTEX_SHADER: 1, FRAGMENT_SHADER: 2, COMPILE_STATUS: 3, LINK_STATUS: 4,
    ARRAY_BUFFER: 5, STATIC_DRAW: 6, FLOAT: 7, TRIANGLES: 8, DEPTH_TEST: 9,
    COLOR_BUFFER_BIT: 16, DEPTH_BUFFER_BIT: 32,
    createShader: () => S("shader"), shaderSource: () => {}, compileShader: () => {},
    getShaderParameter: () => true, getShaderInfoLog: () => "",
    createProgram: () => S("prog"), attachShader: () => {}, linkProgram: () => {},
    getProgramParameter: () => true, getProgramInfoLog: () => "",
    useProgram: () => {}, enable: () => {}, viewport: () => {},
    getUniformLocation: (p, ad) => ad, getAttribLocation: (p, ad) => (ad === "aNor" ? 1 : 0),
    createBuffer: () => S("buf"), deleteBuffer: () => {},
    bindBuffer: () => {}, bufferData: () => {},
    enableVertexAttribArray: () => {}, vertexAttribPointer: () => {},
    uniformMatrix4fv: (yer, aktar, m) => {
      if (yer === "uDonus") { kayit.donusler.push(Array.from(m)); }
    },
    clearColor: () => {}, clear: () => {},
    uniform3fv: (yer, deger) => {
      if (yer === "uRenk") { kayit._sonRenk = Array.from(deger); kayit.renkler.push(kayit._sonRenk); }
    },
    drawArrays: (mod, bas, adet) => {
      kayit.cizim = (kayit.cizim || 0) + 1;
      kayit.cizimler.push({ renk: kayit._sonRenk, adet: adet });
    }
  };
}

// ---- GERCEK (dar kapsamli) CSS secici ayristirici -------------------------
export function ayrastirSecici(s) {
  return String(s).trim().split(/\s+/).map((p) => ({
    id: (p.match(/#([A-Za-z0-9_-]+)/) || [])[1] || null,
    sinif: (p.match(/\.[A-Za-z0-9_-]+/g) || []).map((x) => x.slice(1))
  }));
}

export function ogeUyar(el, p) {
  if (p.id && el.id !== p.id) { return false; }
  return p.sinif.every((c) => el.sinif.includes(c));
}

export function zincirUyar(atalar, parcalar) {
  let i = 0;
  for (const a of atalar) { if (i < parcalar.length && ogeUyar(a, parcalar[i])) { i++; } }
  return i === parcalar.length;
}

export function sorgu(kok, secici, hepsi) {
  const parc = ayrastirSecici(secici);
  const son = parc[parc.length - 1], onceki = parc.slice(0, -1);
  const bulunan = [];
  (function gez(el, atalar) {
    for (const c of el.cocuk || []) {
      if (ogeUyar(c, son) && zincirUyar(atalar, onceki)) { bulunan.push(c); }
      gez(c, atalar.concat([c]));
    }
  })(kok, []);
  return hepsi ? bulunan : (bulunan[0] || null);
}

/** Oge fabrikasi + olay defteri. oge(ek) -> sahte DOM dugumu; .atesle(tur) tetikler. */
export function ogeFabrikasi() {
  const dinleyici = new Map();
  function oge(ek) {
    return Object.assign({
      id: "", sinif: [], cocuk: [],
      hidden: true, disabled: false, textContent: "", value: "",
      _oz: {},
      getAttribute(a) { return this._oz[a] === undefined ? null : this._oz[a]; },
      addEventListener(tur, fn) {
        if (!dinleyici.has(this)) { dinleyici.set(this, {}); }
        const d = dinleyici.get(this);
        (d[tur] = d[tur] || []).push(fn);
      },
      atesle(tur) {
        const d = dinleyici.get(this);
        if (d && d[tur]) { for (const fn of d[tur]) { fn.call(this); } }
      },
      dinleyiciVarMi(tur) {
        const d = dinleyici.get(this);
        return !!(d && d[tur] && d[tur].length);
      }
    }, ek);
  }
  return { oge, dinleyici };
}
