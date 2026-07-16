function konektor(p) {
  var n = Math.max(2, Math.min(4, Math.round(p.kol_sayisi)));
  var tol = p.gecme === "siki" ? 0.1 : (p.gecme === "gevsek" ? 0.5 : 0.3);
  var d = p.cubuk_capi + 2 * p.cidar;
  var delik = p.cubuk_capi + tol;
  var r = d * 0.6;
  var disAlan;
  if (p.kol_kesiti === "kare") {
    disAlan = d * d;
  } else if (p.kol_kesiti === "sekizgen") {
    disAlan = 2 * d * d / (1 + Math.SQRT2);
  } else {
    disAlan = Math.PI * d * d / 4;
  }
  var delikAlan = Math.PI * delik * delik / 4;

  // İki karşılıklı kolda dış gövde bir prizma, merkezde prizma dışında kalan
  // küre parçası ve iki ayrı yuva olarak tam ayrışır. Son katsayılar birim dış
  // ölçüdeki küre parçasının kesit integralleridir.
  if (n === 2) {
    var kureKatsayisi = p.kol_kesiti === "kare" ? 0.07120929525129341 :
      (p.kol_kesiti === "sekizgen" ? 0.1260016651969578 : 0.15281909978271654);
    return 2 * p.kol_boyu * (disAlan - delikAlan) +
      2 * delikAlan * p.cidar + kureKatsayisi * d * d * d;
  }

  // Küre ile kolların ve yuvaların kesiştiği merkez bölge sabit bir ızgarada
  // değerlendirilir; küre dışındaki düz kol bölümü analitik olarak eklenir.
  var adimSayisi = 40;
  var sinir = d * 1.11;
  var hucre = 2 * sinir / adimSayisi;
  var yari = d / 2;
  var delikYari2 = delik * delik / 4;
  var r2 = r * r;
  var yonX = [];
  var yonY = [];
  var a;
  for (a = 0; a < n; a++) {
    var aci = 2 * Math.PI * a / n;
    yonX.push(Math.cos(aci));
    yonY.push(Math.sin(aci));
  }

  var dolu = 0;
  var ix;
  var iy;
  var iz;
  for (ix = 0; ix < adimSayisi; ix++) {
    var x = -sinir + (ix + 0.5) * hucre;
    for (iy = 0; iy < adimSayisi; iy++) {
      var y = -sinir + (iy + 0.5) * hucre;
      for (iz = 0; iz < adimSayisi; iz++) {
        var z = -sinir + (iz + 0.5) * hucre;
        var dis = x * x + y * y + z * z <= r2;
        var bos = false;
        for (a = 0; a < n; a++) {
          var boyuna = x * yonX[a] + y * yonY[a];
          var enine = -x * yonY[a] + y * yonX[a];
          if (boyuna >= 0 && boyuna <= r) {
            var kesitte;
            if (p.kol_kesiti === "kare") {
              kesitte = Math.abs(enine) <= yari && Math.abs(z) <= yari;
            } else if (p.kol_kesiti === "sekizgen") {
              kesitte = Math.abs(enine) <= yari && Math.abs(z) <= yari &&
                Math.abs(enine) + Math.abs(z) <= d / Math.SQRT2;
            } else {
              kesitte = enine * enine + z * z <= yari * yari;
            }
            if (kesitte) dis = true;
            if (boyuna >= p.cidar && enine * enine + z * z <= delikYari2) bos = true;
          }
        }
        if (dis && !bos) dolu++;
      }
    }
  }

  var merkez = dolu * hucre * hucre * hucre;
  return merkez + n * (p.kol_boyu - r) * (disAlan - delikAlan);
}
