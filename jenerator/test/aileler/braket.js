function braket_delik_alani(fn, cap) {
  // OpenSCAD circle(d, $fn) içe çizili çokgen alanı
  var r = cap / 2;
  return 0.5 * fn * r * r * Math.sin(2 * Math.PI / fn);
}

function braket_delik_sayisi(bas, son, n) {
  // scad _delik_s ile birebir: bas>=son ya da n==1 → tek (üst üste biner)
  if (n <= 0) return 0;
  if (bas >= son || n === 1) return 1;
  return n;
}

function braket_izgara_alani(icinde, xmin, xmax, ymin, ymax) {
  var hucre = Math.max(0.15, (xmax - xmin) / 640);
  var Nx = Math.ceil((xmax - xmin) / hucre);
  var Ny = Math.ceil((ymax - ymin) / hucre);
  var say = 0;
  for (var i = 0; i < Nx; i++) {
    var x = xmin + (i + 0.5) * hucre;
    for (var j = 0; j < Ny; j++) {
      if (icinde(x, ymin + (j + 0.5) * hucre)) say++;
    }
  }
  return say * hucre * hucre;
}

function braket(p) {
  // v2 geometrisi (2026-07-16): angle = tek profil çokgeni × genişlik;
  // l/t/y = merkezli yarım şeritler + merkez diski; corner = 3 dik plaka.
  // esleme sabitleri: M4 (4.5 mm), delik_fn=32, kolon=1, radyus=0, payanda yok.
  var t = Math.max(p.kalinlik, 1.2);
  var w = p.genislik;
  var L = p.uzunluk;
  var hd = 4.5;
  var Ad = braket_delik_alani(32, hd);
  var kenarPay = Math.max(hd + 2, w * 0.3);

  if (p.tip === "duz") {
    var kd = braket_delik_sayisi(kenarPay, L - kenarPay, p.delik_adet);
    return L * w * t - kd * Ad * t;
  }

  if (p.tip === "acili") {
    var a = p.ic_aci * Math.PI / 180;
    var ux = Math.cos(a), uz = Math.sin(a);
    var nx = uz, nz = -ux;
    var pts = [[0, 0], [L, 0], [L, t], [t * (1 + ux) / uz, t],
               [L * ux + nx * t, L * uz + nz * t], [L * ux, L * uz]];
    var alan2 = 0;
    for (var i = 0; i < pts.length; i++) {
      var q1 = pts[i], q2 = pts[(i + 1) % pts.length];
      alan2 += q1[0] * q2[1] - q2[0] * q1[1];
    }
    var bas1 = Math.max(w * 0.5, t * (1 + ux) / uz + hd, hd + 3);
    var ka = braket_delik_sayisi(bas1, L - kenarPay, p.delik_adet);
    return Math.abs(alan2) / 2 * w - 2 * ka * Ad * t;
  }

  if (p.tip === "kose") {
    var bk = Math.max(w * 0.6, hd + t + 2);
    var kk = braket_delik_sayisi(bk, L - kenarPay, p.delik_adet);
    return 3 * L * w * t - L * t * t - 2 * w * t * t + t * t * t -
      3 * kk * Ad * t;
  }

  // l / t / y: 2B ızgara (yarım şeritler + merkez diski)
  var acilar = p.tip === "l" ? [0, 90] :
               p.tip === "t" ? [0, 180, 270] : [90, 210, 330];
  var yonler = [];
  for (var m = 0; m < acilar.length; m++) {
    var th = acilar[m] * Math.PI / 180;
    yonler.push([Math.cos(th), Math.sin(th)]);
  }
  var r0 = w / 2;
  var alan = braket_izgara_alani(function (x, y) {
    if (x * x + y * y <= r0 * r0) return true;
    for (var k = 0; k < yonler.length; k++) {
      var s = x * yonler[k][0] + y * yonler[k][1];
      if (s >= 0 && s <= L &&
          Math.abs(-x * yonler[k][1] + y * yonler[k][0]) <= r0) return true;
    }
    return false;
  }, -(L + r0), L + r0, -(L + r0), L + r0);
  var icBosluk = Math.max(w * 0.65, hd + 3);
  var kp = braket_delik_sayisi(icBosluk, L - kenarPay, p.delik_adet);
  return alan * t - acilar.length * kp * Ad * t;
}
