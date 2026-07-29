/* ORTAK OLCUM CEKIRDEGI — onizleme render kapilarinin PAYLASILAN rasterlestiricisi.
   (Kosulabilir test DEGIL: alt dizinde durur, tools/ci-kapsam-test.py kesfi yalnizca
    onizleme/test'in DOGRUDAN altina bakar. Burada iddia yok, yalniz olcum araci.)

   NEDEN AYRI DOSYA: ayni rasterlestirici iki kapida kullaniliyor
     onizleme/test/renk-yazi-gorunurluk.mjs   (renk secimi + kabartma yazi gorunurlugu)
     onizleme/test/iki-govde-kabul.mjs        (2-renk: iki govde, iki renk)
   Ikinci bir KOPYA tutulsaydi biri degisip digeri kalir ve iki kapi ayni ekrani
   olctugunu SANIP farkli seyler olcerdi.

   Kamera ve golgeleme DAIMA disaridan verilen GERCEK viewer'in kendi fonksiyonlarindan
   gelir (VIEWER._gorunum / VIEWER._golge) — burada ikinci bir matematik YOKTUR.
   Rasterlestirme nokta-ornekli + z-tamponlu; WebGL'in MSAA'si YOK (kotumser tahmin). */
"use strict";
import fs from "node:fs";

export const ZEMIN = [0.956, 0.965, 0.973];

/** Eksen hizali kutuyu 12 ucgen olarak `t` listesine ekler (fikstur kurucusu). */
export function kutu(t, x0, x1, y0, y1, z0, z1) {
  const k = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
             [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]];
  const yuz = [[0, 3, 2], [0, 2, 1], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
               [2, 3, 7], [2, 7, 6], [1, 2, 6], [1, 6, 5], [3, 0, 4], [3, 4, 7]];
  for (const [a, b, c] of yuz) { t.push([k[a], k[b], k[c]]); }
}

export function ucgenNormali(v) {
  const u = [v[1][0] - v[0][0], v[1][1] - v[0][1], v[1][2] - v[0][2]];
  const w = [v[2][0] - v[0][0], v[2][1] - v[0][1], v[2][2] - v[0][2]];
  const n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
  const b = Math.hypot(n[0], n[1], n[2]) || 1;
  return [n[0] / b, n[1] / b, n[2] / b];
}

export function modelKutusu(ucgenler) {
  const az = [Infinity, Infinity, Infinity], cok = [-Infinity, -Infinity, -Infinity];
  for (const v of ucgenler) {
    for (const p of v) {
      for (let k = 0; k < 3; k++) {
        if (p[k] < az[k]) { az[k] = p[k]; }
        if (p[k] > cok[k]) { cok[k] = p[k]; }
      }
    }
  }
  return {
    az, cok,
    merkez: [(az[0] + cok[0]) / 2, (az[1] + cok[1]) / 2, (az[2] + cok[2]) / 2],
    yaricap: Math.max(0.001, Math.hypot(cok[0] - az[0], cok[1] - az[1], cok[2] - az[2]) / 2)
  };
}

/** Binary STL dosyasi -> ucgen listesi. */
export function stlOku(yol) {
  const ham = fs.readFileSync(yol);
  const adet = ham.readUInt32LE(80);
  const t = [];
  let o = 84;
  for (let i = 0; i < adet; i++) {
    o += 12;
    const v = [];
    for (let k = 0; k < 3; k++) {
      v.push([ham.readFloatLE(o), ham.readFloatLE(o + 4), ham.readFloatLE(o + 8)]);
      o += 12;
    }
    o += 2;
    t.push(v);
  }
  return t;
}

/** Ucgen listesini binary STL ArrayBuffer'a cevirir (viewer'in stlCoz'u kabul etsin). */
export function stlYaz(ucgenler) {
  const b = Buffer.alloc(84 + ucgenler.length * 50);
  b.write("PRUVO test", 0);
  b.writeUInt32LE(ucgenler.length, 80);
  let o = 84;
  for (const v of ucgenler) {
    const n = ucgenNormali(v);
    for (const c of n) { b.writeFloatLE(c, o); o += 4; }
    for (const p of v) { for (const c of p) { b.writeFloatLE(c, o); o += 4; } }
    o += 2;
  }
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
}

/** COK GOVDELI cizim: parcalar = [{ucgenler, renk}]. Kamera TUM parcalarin ORTAK
 *  kutusundan gelir — viewer.js'in yukle()'si de tam olarak boyle yapar (govdeler
 *  ayni koordinat sisteminde; hicbiri tek basina merkezlenmez).
 *  {luma: Float32Array(W*H), W, H} doner (0..255 gri). */
export function cizCok(VIEWER, parcalar, W, H) {
  const hepsi = [];
  for (const p of parcalar) { for (const v of p.ucgenler) { hepsi.push(v); } }
  return cizCokKamerali(VIEWER, parcalar, modelKutusu(hepsi), W, H);
}

/** TEK govdeli cizim (eski cagri bicimi korunur). Kamera verilmezse govdenin kendi
 *  kutusu; verilirse O kamera (yazili/yazisiz mesh'i AYNI kameradan kiyaslamak icin). */
export function ciz(VIEWER, ucgenler, renk, kamera, W, H) {
  return cizCokKamerali(VIEWER, [{ ucgenler, renk }],
                        kamera || modelKutusu(ucgenler), W, H);
}

/** Kamerasi DISARIDAN verilen cok govdeli cizim. */
export function cizCokKamerali(VIEWER, parcalar, kamera, W, H) {
  const g = VIEWER._gorunum(kamera, W / H, VIEWER._BASLANGIC.yaw,
                            VIEWER._BASLANGIC.pitch, VIEWER._BASLANGIC.zoom);
  return _cizIc(VIEWER, parcalar, g, W, H);
}

function _cizIc(VIEWER, parcalar, g, W, H) {
  const zemin = 0.2126 * ZEMIN[0] + 0.7152 * ZEMIN[1] + 0.0722 * ZEMIN[2];
  const luma = new Float32Array(W * H).fill(zemin * 255);
  const derinlik = new Float32Array(W * H).fill(Infinity);
  const D = g.donus;
  for (const parca of parcalar) {
    for (const v of parca.ucgenler) {
      const n = ucgenNormali(v);
      const nd = [D[0] * n[0] + D[4] * n[1] + D[8] * n[2],
                  D[1] * n[0] + D[5] * n[1] + D[9] * n[2],
                  D[2] * n[0] + D[6] * n[1] + D[10] * n[2]];
      const rgb = VIEWER._golge(nd, parca.renk);
      const ton = 255 * (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]);
      const ek = [];
      let atla = false;
      for (const p of v) {
        const c = mat4Vek(g.proj, mat4Vek(g.goruntu, mat4Vek(D, [p[0], p[1], p[2], 1])));
        if (c[3] <= 1e-6) { atla = true; break; }
        ek.push([(c[0] / c[3] * 0.5 + 0.5) * W, (0.5 - c[1] / c[3] * 0.5) * H, c[2] / c[3]]);
      }
      if (atla) { continue; }
      const x0 = Math.max(0, Math.floor(Math.min(ek[0][0], ek[1][0], ek[2][0])));
      const x1 = Math.min(W - 1, Math.ceil(Math.max(ek[0][0], ek[1][0], ek[2][0])));
      const y0 = Math.max(0, Math.floor(Math.min(ek[0][1], ek[1][1], ek[2][1])));
      const y1 = Math.min(H - 1, Math.ceil(Math.max(ek[0][1], ek[1][1], ek[2][1])));
      const alan = (ek[1][0] - ek[0][0]) * (ek[2][1] - ek[0][1]) -
                   (ek[2][0] - ek[0][0]) * (ek[1][1] - ek[0][1]);
      if (Math.abs(alan) < 1e-12) { continue; }
      for (let y = y0; y <= y1; y++) {
        for (let x = x0; x <= x1; x++) {
          const px = x + 0.5, py = y + 0.5;
          const w0 = ((ek[1][0] - ek[0][0]) * (py - ek[0][1]) -
                      (px - ek[0][0]) * (ek[1][1] - ek[0][1])) / alan;
          const w1 = ((px - ek[0][0]) * (ek[2][1] - ek[0][1]) -
                      (ek[2][0] - ek[0][0]) * (py - ek[0][1])) / alan;
          if (w0 < 0 || w1 < 0 || w0 + w1 > 1) { continue; }
          const z = ek[0][2] + w1 * (ek[1][2] - ek[0][2]) + w0 * (ek[2][2] - ek[0][2]);
          const i = y * W + x;
          if (z < derinlik[i]) { derinlik[i] = z; luma[i] = ton; }
        }
      }
    }
  }
  return { luma, W, H };
}

export function mat4Vek(m, v) {
  return [
    m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12] * v[3],
    m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13] * v[3],
    m[2] * v[0] + m[6] * v[1] + m[10] * v[2] + m[14] * v[3],
    m[3] * v[0] + m[7] * v[1] + m[11] * v[2] + m[15] * v[3]];
}

export function ortalama(a) {
  let t = 0;
  for (let i = 0; i < a.length; i++) { t += a[i]; }
  return t / a.length;
}

/** Iki render arasindaki fark: {piksel: esigi asan piksel sayisi, azami: en buyuk fark} */
export function fark(a, b, esik) {
  let piksel = 0, azami = 0;
  for (let i = 0; i < a.luma.length; i++) {
    const d = Math.abs(a.luma[i] - b.luma[i]);
    if (d > azami) { azami = d; }
    if (d >= esik) { piksel++; }
  }
  return { piksel, azami };
}
