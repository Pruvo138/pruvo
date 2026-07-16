function braket_kirp(cokgen, a, b) {
  var sonuc = [];
  for (var i = 0; i < cokgen.length; i++) {
    var p = cokgen[i];
    var q = cokgen[(i + 1) % cokgen.length];
    var dp = (b[0] - a[0]) * (p[1] - a[1]) -
      (b[1] - a[1]) * (p[0] - a[0]);
    var dq = (b[0] - a[0]) * (q[1] - a[1]) -
      (b[1] - a[1]) * (q[0] - a[0]);
    if (dp >= 0) sonuc.push(p);
    if ((dp >= 0) !== (dq >= 0)) {
      var oran = dp / (dp - dq);
      sonuc.push([
        p[0] + (q[0] - p[0]) * oran,
        p[1] + (q[1] - p[1]) * oran
      ]);
    }
  }
  return sonuc;
}

function braket_cokgen_alani(cokgen) {
  var ikiAlan = 0;
  for (var i = 0; i < cokgen.length; i++) {
    var p = cokgen[i];
    var q = cokgen[(i + 1) % cokgen.length];
    ikiAlan += p[0] * q[1] - q[0] * p[1];
  }
  return Math.abs(ikiAlan) / 2;
}

function braket_kesisim_alani(xmin, uzunluk, kalinlik, aci) {
  var c = Math.cos(aci);
  var s = Math.sin(aci);
  var ilk = [[xmin, 0], [uzunluk, 0], [uzunluk, kalinlik], [xmin, kalinlik]];
  var yerel = [[xmin, 0], [uzunluk, 0], [uzunluk, kalinlik], [xmin, kalinlik]];
  var ikinci = [];
  for (var i = 0; i < yerel.length; i++) {
    ikinci.push([
      yerel[i][0] * c - yerel[i][1] * s,
      yerel[i][0] * s + yerel[i][1] * c
    ]);
  }
  var sonuc = ilk;
  for (var j = 0; j < ikinci.length && sonuc.length; j++) {
    sonuc = braket_kirp(sonuc, ikinci[j], ikinci[(j + 1) % ikinci.length]);
  }
  return sonuc.length < 3 ? 0 : braket_cokgen_alani(sonuc);
}

function braket_aci_bindirme(genislik, uzunluk, kalinlik, derece) {
  var yaricap = genislik / 2;
  var adim = genislik / 64;
  var aci = derece * Math.PI / 180;
  var toplam = 0;
  for (var i = 0; i < 64; i++) {
    var y = -yaricap + (i + 0.5) * adim;
    var xmin = -Math.sqrt(Math.max(0, yaricap * yaricap - y * y));
    toplam += braket_kesisim_alani(xmin, uzunluk, kalinlik, aci);
  }
  return toplam * adim;
}

function braket(p) {
  var w = p.genislik;
  var l = p.uzunluk;
  var t = p.kalinlik;
  var delikYaricapi = 2.25;
  var delikAlani = 16 * delikYaricapi * delikYaricapi *
    Math.sin(Math.PI / 16);

  // SCAD'deki yuvarlak eklem, sabit 2 mm kenar radyusu ve parçalı daire.
  var disAlan = l * w + Math.PI * w * w / 8 - 0.1717 * w - 0.16;
  var kol = (disAlan - p.delik_adet * delikAlani) * t;

  if (p.tip === "duz") return kol;

  if (p.tip === "l") {
    return 2 * kol - t * (0.850584 * w * w - 0.66785 * w);
  }
  if (p.tip === "t") {
    return 3 * kol - t * (1.6945225 * w * w - 1.02755 * w);
  }
  if (p.tip === "y") {
    return 3 * kol - t * (1.625614 * w * w - 0.94685 * w);
  }
  if (p.tip === "kose") {
    var duzL = 2 * kol - t * (0.850584 * w * w - 0.66785 * w);
    var dikBindirme = w * t * t * (1 - t / (8 * w));
    return duzL + kol - dikBindirme;
  }

  return 2 * kol - braket_aci_bindirme(w, l, t, p.ic_aci);
}
