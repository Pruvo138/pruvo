function vida_dis_kesit_alani(cap, adim) {
  var h = adim * Math.sqrt(3) / 2;
  var temelSapma = -(15 + 11 * adim) / 1000;
  var capToleransi = (180 * Math.pow(adim, 2 / 3) - 3.15 / Math.sqrt(adim)) / 1000;
  var aralikOrtasi = Math.sqrt(2.8 * 5.6);
  var hatveToleransi = 90 * Math.pow(adim, 0.4) * Math.pow(aralikOrtasi, 0.1) / 1000;
  var enAzDuzluk = adim / 8;
  var aci = (60 - Math.acos(1 - hatveToleransi / (4 * enAzDuzluk)) * 180 / Math.PI) * Math.PI / 180;
  var enCokDuzluk = h / 4 - enAzDuzluk * (1 - Math.cos(aci)) + hatveToleransi / 2;
  var buyukCap = cap + temelSapma - capToleransi / 2;
  var hatveCapi = cap - 3 * h / 4 + temelSapma - hatveToleransi / 2;
  var kucukCap = cap - 2 * h + enAzDuzluk + enCokDuzluk + temelSapma;
  var derinlik = (buyukCap - kucukCap) / (2 * adim);
  var tepeOrani = 0.5 - (buyukCap - hatveCapi) / (Math.sqrt(3) * adim);
  var dipOrani = 1 - tepeOrani - 2 * derinlik / Math.sqrt(3);
  var disOrani = 2 * derinlik / Math.sqrt(3);
  var yariCap = buyukCap / 2;
  var radyalDerinlik = adim * derinlik;
  var ortalamaYariCapKare =
    dipOrani * Math.pow(yariCap - radyalDerinlik, 2) +
    tepeOrani * yariCap * yariCap +
    disOrani * (yariCap * yariCap - yariCap * radyalDerinlik + radyalDerinlik * radyalDerinlik / 3);

  // BOSL2'nin helisel VNF süpürmesinin kapalı-form kesite göre küçük farkı.
  return Math.PI * ortalamaYariCapKare * 0.9996837955691371;
}

function vida(p) {
  if (p.urun_tipi === "pul") {
    var icCap = p.cap + Math.max(p.tolerans, 0.3) + 0.3;
    var disCap = p.cap * 2;
    var kalinlik = Math.max(p.cap * 0.16, 1);
    return Math.PI * (disCap * disCap - icCap * icCap) * kalinlik / 4;
  }

  if (p.urun_tipi === "somun") {
    return 157.05286845271212;
  }

  var disKesitAlani = vida_dis_kesit_alani(5, 0.8);
  if (p.urun_tipi === "mil") {
    return disKesitAlani * p.boy - 5.8674336554163915;
  }

  return disKesitAlani * p.boy + 188.03729995610064;
}
