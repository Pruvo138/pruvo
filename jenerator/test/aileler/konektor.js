function konektor_alan(kesit, d, kenar) {
  if (kesit === "kare") return d * d;
  if (kesit === "sekizgen") return 2 * d * d / (1 + Math.SQRT2);
  var r = d / 2;
  return 0.5 * kenar * r * r * Math.sin(2 * Math.PI / kenar);
}

function konektor_yarim_genislik(kesit, d, z) {
  // Kesitin z yüksekliğindeki yarım genişliği (kesit dikey, düzlemsel dizilim).
  var yari = d / 2;
  var mz = Math.abs(z);
  if (mz >= yari) return 0;
  if (kesit === "kare") return yari;
  if (kesit === "sekizgen") {
    var duz = yari * Math.tan(Math.PI / 8);
    return mz <= duz ? yari : (yari * (1 + Math.tan(Math.PI / 8)) - mz);
  }
  return Math.sqrt(yari * yari - mz * mz);
}

function konektor_dis_zarf(noktalar) {
  // 2B dışbükey zarf (monoton zincir), CCW köşe listesi döner.
  var p = noktalar.slice().sort(function (a, b) {
    return a[0] - b[0] || a[1] - b[1];
  });
  function konektor_capraz(o, a, b) {
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  }
  var alt = [], ust = [], i;
  for (i = 0; i < p.length; i++) {
    while (alt.length >= 2 &&
           konektor_capraz(alt[alt.length - 2], alt[alt.length - 1], p[i]) <= 0) alt.pop();
    alt.push(p[i]);
  }
  for (i = p.length - 1; i >= 0; i--) {
    while (ust.length >= 2 &&
           konektor_capraz(ust[ust.length - 2], ust[ust.length - 1], p[i]) <= 0) ust.pop();
    ust.push(p[i]);
  }
  alt.pop(); ust.pop();
  return alt.concat(ust);
}

function konektor(p) {
  // v2 geometrisi (2026-07-16): kol dış ölçüsü = cubuk + 2*max(cidar,1.2);
  // göbek = kol köklerinin (g = min(0.6*Do, 0.5*L)) dışbükey zarfı;
  // 2 karşılıklı kolda göbek yok. Tolerans: siki 0.15 / normal 0.30 / gevsek 0.50.
  var n = Math.max(2, Math.round(p.kol_sayisi));
  var tol = p.gecme === "siki" ? 0.15 : (p.gecme === "gevsek" ? 0.50 : 0.30);
  var cid = Math.max(p.cidar, 1.2);
  var Do = p.cubuk_capi + 2 * cid;
  var Db = p.cubuk_capi + tol;
  var L = p.kol_boyu;
  var S = 180; // esleme sabiti Segments
  var Aout = konektor_alan(p.kol_kesiti, Do, S);
  var Abore = konektor_alan("yuvarlak", Db, S);

  if (n === 2) { // düz manşon: iki prizma, kapalı uçlu yuvalar — kapalı form
    return 2 * L * Aout - 2 * (L - cid) * Abore;
  }

  // n >= 3: z-dilimli sayısal integral (dilim alanı 2B ızgarada).
  var g = Math.min(0.6 * Do, 0.5 * L);
  var H = Do / 2;
  var rb = Db / 2;
  var yonler = [];
  var a;
  for (a = 0; a < n; a++) {
    var th = 2 * Math.PI * a / n;
    yonler.push([Math.cos(th), Math.sin(th)]);
  }
  var zN = 48;
  var dz = H / zN;              // z>0 yarısı; simetriyle x2
  var kapsam = L + Do / 2;
  var hucre = (2 * kapsam) / 520;
  var Nxy = Math.ceil(2 * kapsam / hucre);
  var hacim = 0;
  for (var iz = 0; iz < zN; iz++) {
    var z = (iz + 0.5) * dz;
    var hw = konektor_yarim_genislik(p.kol_kesiti, Do, z);
    if (hw <= 0) continue;
    var hb = z < rb ? Math.sqrt(rb * rb - z * z) : 0;
    // göbek zarf dilimi: güdük köşeleri (taban + uç, her iki yan)
    var pts = [];
    for (a = 0; a < n; a++) {
      var u = yonler[a];
      pts.push([-hw * u[1], hw * u[0]]);
      pts.push([hw * u[1], -hw * u[0]]);
      pts.push([g * u[0] - hw * u[1], g * u[1] + hw * u[0]]);
      pts.push([g * u[0] + hw * u[1], g * u[1] - hw * u[0]]);
    }
    var zarf = konektor_dis_zarf(pts);
    var alan = 0;
    for (var ix = 0; ix < Nxy; ix++) {
      var x = -kapsam + (ix + 0.5) * hucre;
      for (var iy = 0; iy < Nxy; iy++) {
        var y = -kapsam + (iy + 0.5) * hucre;
        var dolu = false;
        var bos = false;
        for (a = 0; a < n; a++) {
          var s = x * yonler[a][0] + y * yonler[a][1];
          if (s < 0 || s > L) continue;
          var e = Math.abs(-x * yonler[a][1] + y * yonler[a][0]);
          if (e <= hw) dolu = true;
          if (hb > 0 && s >= cid && e <= hb) bos = true;
        }
        if (!dolu) { // göbek zarfında mı?
          dolu = true;
          for (var k = 0; k < zarf.length; k++) {
            var q1 = zarf[k];
            var q2 = zarf[(k + 1) % zarf.length];
            if ((q2[0] - q1[0]) * (y - q1[1]) -
                (q2[1] - q1[1]) * (x - q1[0]) < 0) { dolu = false; break; }
          }
        }
        if (dolu && !bos) alan += 1;
      }
    }
    hacim += alan * hucre * hucre * dz;
  }
  return 2 * hacim;
}
