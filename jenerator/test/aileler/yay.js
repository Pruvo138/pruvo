function yay_dalga_degeri(form, faz, genlik) {
  var f = faz - Math.floor(faz);
  if (form === "sinus") return genlik * Math.sin(2 * Math.PI * faz);
  if (form === "ucgen") return genlik * (f < 0.5 ? 4 * f - 1 : 3 - 4 * f);
  if (form === "testere") return genlik * (2 * f - 1);
  if (form === "darbe") return genlik * (f < 0.3 ? 1 : -1);
  return genlik * (f < 0.5 ? 1 : -1);
}

function yay_dalga_hacmi(p) {
  var genlik = 10;
  var cevrim = 4;
  var seritKalinligi = 2;
  var seritYuksekligi = 8;
  var parcaSayisi = 160;
  var dx = p.dalga_boyu / parcaSayisi;
  var uzunluk = 0;
  var onceki = yay_dalga_degeri(p.dalga_formu, 0, genlik);

  for (var i = 1; i <= parcaSayisi; i++) {
    var faz = cevrim * i / parcaSayisi;
    var simdiki = yay_dalga_degeri(p.dalga_formu, faz, genlik);
    var dy = simdiki - onceki;
    uzunluk += Math.sqrt(dx * dx + dy * dy);
    onceki = simdiki;
  }

  var yaricap = seritKalinligi / 2;
  var kesitAlani = seritKalinligi * uzunluk + Math.PI * yaricap * yaricap;
  // SCAD şeridi 16 kenarlı çemberlerin dışbükey zarflarından oluşur.
  return 0.98 * kesitAlani * seritYuksekligi;
}

function yay(p) {
  if (p.tip === "dalga") return yay_dalga_hacmi(p);

  var sarimSayisi = 8;
  var yaricap = (p.dis_cap - p.tel_capi) / 2;
  var eksenBoyu = Math.max(p.serbest_boy - p.tel_capi, p.tel_capi);
  var cevreBoyu = 2 * Math.PI * yaricap * sarimSayisi;
  var yolBoyu = Math.sqrt(eksenBoyu * eksenBoyu + cevreBoyu * cevreBoyu);
  var telAlani = Math.PI * p.tel_capi * p.tel_capi / 4;
  return telAlani * yolBoyu;
}
