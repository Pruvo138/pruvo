function yay_dalga_degeri(form, faz, genlik) {
  var f = faz - Math.floor(faz);
  if (form === "sinus") return genlik * Math.sin(2 * Math.PI * faz);
  if (form === "ucgen") return genlik * (f < 0.5 ? 4 * f - 1 : 3 - 4 * f);
  if (form === "testere") return genlik * (2 * f - 1);
  if (form === "darbe") return genlik * (f < 0.3 ? 1 : -1);
  return genlik * (f < 0.5 ? 1 : -1);
}

function yay_dalga_yolu(form, boy) {
  // Uretim motorunun orneklemesi birebir: 240 ornek, faz kaymasi 0.125
  // (eslem sabiti Phase — ornekler dalga gecislerinin tam ustune dusmesin diye;
  // 0'da kalirsa uc nokta sin(1440°) yuvarlama gurultusune duser ve boy'a gore
  // fazladan bir sicrama olusur/olusmazdi). Form ofsetleri motorla ayni:
  // ucgen +0.25, testere +0.5.
  var genlik = 10;
  var cevrim = 4;
  var ornek = 240;
  var ofset = 0.125 + (form === "ucgen" ? 0.25 : form === "testere" ? 0.5 : 0);
  var ham = [];
  var i;
  for (i = 0; i <= ornek; i++) {
    ham.push([i * (boy / ornek),
      yay_dalga_degeri(form, cevrim * i / ornek + ofset, genlik)]);
  }

  // Dogrusal ara noktalari birlestir (kose sayimi icin sart).
  var yol = [ham[0]];
  for (i = 1; i < ham.length; i++) {
    var q = ham[i];
    if (yol.length >= 2) {
      var a = yol[yol.length - 2];
      var b = yol[yol.length - 1];
      if (Math.abs((b[0] - a[0]) * (q[1] - a[1]) -
                   (b[1] - a[1]) * (q[0] - a[0])) < 1e-9) {
        yol[yol.length - 1] = q;
        continue;
      }
    }
    yol.push(q);
  }

  // <0.7 mm araliktaki ic nokta cifti tek koseye iner: ucgen tepesindeki
  // orneklem duzlugu iki yakin 76°'lik kose yapar, bindirme kaybi tek keskin
  // kose gibi davranir — tek apekse indirmek kayip modelini dogru kurar.
  var sade = [yol[0]];
  i = 1;
  while (i < yol.length - 1) {
    if (i + 1 < yol.length - 1 &&
        Math.hypot(yol[i + 1][0] - yol[i][0], yol[i + 1][1] - yol[i][1]) < 0.7) {
      sade.push([(yol[i][0] + yol[i + 1][0]) / 2,
                 (yol[i][1] + yol[i + 1][1]) / 2]);
      i += 2;
    } else {
      sade.push(yol[i]);
      i += 1;
    }
  }
  sade.push(yol[yol.length - 1]);
  return sade;
}

function yay_dalga_hacmi(p) {
  // Serit = yolun stroke'u (genislik 2, uclar duz, eklemler yuvarlak).
  // Alan = kalinlik x yol boyu − kose bindirme kayiplari:
  // her donus acisi θ icin kayip (t²/4)(tan(θ/2) − θ/2) (miter kesisimi
  // eksi yuvarlak eklem yelpazesi). Motor renderlarina karsi olculdu:
  // kare/darbe/testere ≤%0.02, sinus ≤%0.6, ucgen ≤%1.7 (tum boy araligi).
  var seritKalinligi = 2;
  var seritYuksekligi = 8;
  var yol = yay_dalga_yolu(p.dalga_formu, p.dalga_boyu);
  var uzunluk = 0;
  var kayip = 0;
  for (var i = 1; i < yol.length; i++) {
    uzunluk += Math.hypot(yol[i][0] - yol[i - 1][0], yol[i][1] - yol[i - 1][1]);
    if (i < yol.length - 1) {
      var v1x = yol[i][0] - yol[i - 1][0];
      var v1y = yol[i][1] - yol[i - 1][1];
      var v2x = yol[i + 1][0] - yol[i][0];
      var v2y = yol[i + 1][1] - yol[i][1];
      var n1 = Math.hypot(v1x, v1y);
      var n2 = Math.hypot(v2x, v2y);
      if (n1 > 1e-12 && n2 > 1e-12) {
        var c = Math.max(-1, Math.min(1, (v1x * v2x + v1y * v2y) / (n1 * n2)));
        var donus = Math.acos(c);
        if (donus > 1e-9) {
          kayip += (seritKalinligi * seritKalinligi / 4) *
            (Math.tan(donus / 2) - donus / 2);
        }
      }
    }
  }
  var kesitAlani = seritKalinligi * uzunluk - kayip;
  return kesitAlani * seritYuksekligi;
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
