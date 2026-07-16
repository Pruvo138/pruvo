function kayis_profil_verisi(profil) {
  if (profil === "GT2_3mm") return [3, 1.169, 2.310, 0.940, 1];
  if (profil === "GT2_5mm") return [5, 1.968, 3.952, 1.636, 1];
  if (profil === "HTD_3mm") return [3, 1.289, 2.270, 1.068, 1];
  if (profil === "HTD_5mm") return [5, 2.199, 3.781, 1.670, 1];
  if (profil === "HTD_8mm") return [8, 3.607, 6.603, 2.879, 1];
  if (profil === "T2.5") return [2.5, 0.700, 1.679, 1.058, 0];
  if (profil === "T5") return [5, 1.190, 3.264, 1.898, 0];
  if (profil === "T10") return [10, 2.500, 6.130, 3.758, 0];
  if (profil === "AT5") return [5, 1.190, 4.268, 2.574, 0];
  if (profil === "MXL") return [2.032, 0.508, 1.321, 0.834, 0];
  if (profil === "XL") return [5.08, 1.270, 3.051, 1.467, 0];
  if (profil === "L") return [9.525, 1.905, 5.359, 3.439, 0];
  if (profil === "40DP") return [2.073, 0.457, 1.226, 0.655, 0];
  return [2, 0.764, 1.494, 0.716, 1];
}

function kayis_dis_alani(veri) {
  var derinlik = veri[1];
  var taban = veri[2];
  var tepe = veri[3];

  if (!veri[4]) {
    return derinlik * (taban + tepe) / 2;
  }

  // SCAD'daki yuvarlak diş, 0,02 mm'lik taban dikdörtgeni ile tepe
  // çemberinin dışbükey zarfıdır. Aşağıdaki ifade bu zarfın analitik alanıdır.
  var yariTaban = taban / 2;
  var yariTepe = tepe / 2;
  var merkezY = derinlik - yariTepe - 0.01;
  var uzaklik2 = yariTaban * yariTaban + merkezY * merkezY;
  var teget = Math.sqrt(uzaklik2 - yariTepe * yariTepe);
  var birimX = (yariTepe * yariTaban + teget * merkezY) / uzaklik2;
  var birimY = (-yariTepe * merkezY + teget * yariTaban) / uzaklik2;
  var tegetY = merkezY + yariTepe * birimY;
  var aci = Math.atan2(birimY, birimX);
  var kubbe = yariTaban * tegetY +
    yariTepe * yariTepe * (Math.PI - 2 * aci) / 2 +
    merkezY * yariTepe * birimX;

  // Taban karesinin sırtla çakışan yarısı çıkarılmış net diş alanı.
  return kubbe + taban * 0.01;
}

function kayis(p) {
  var veri = kayis_profil_verisi(p.profil);
  var adim = veri[0];
  var derinlik = veri[1];
  var sirt = Math.max(derinlik * 0.7, 0.8);
  var uzunluk = p.dis_sayisi * adim;
  var sirtAlani = uzunluk * sirt;

  if (p.sekil === "kapali") {
    if (p.dis_taraf === "ic") sirtAlani += Math.PI * sirt * sirt;
    if (p.dis_taraf === "dis") sirtAlani -= Math.PI * sirt * sirt;
  }

  var tarafSayisi = p.dis_taraf === "cift" ? 2 : 1;
  var disAlani = p.dis_sayisi * tarafSayisi * kayis_dis_alani(veri);
  return (sirtAlani + disAlani) * p.genislik;
}
