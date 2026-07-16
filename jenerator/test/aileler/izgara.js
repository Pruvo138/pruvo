function izgara_cokgen_alani(cokgen) {
  var ikiAlan = 0;
  for (var i = 0; i < cokgen.length; i++) {
    var a = cokgen[i];
    var b = cokgen[(i + 1) % cokgen.length];
    ikiAlan += a[0] * b[1] - b[0] * a[1];
  }
  return Math.abs(ikiAlan) / 2;
}

function izgara_cokgen_kirp(konu, kirp) {
  var sonuc = konu;
  for (var k = 0; k < kirp.length; k++) {
    var bas = kirp[k];
    var son = kirp[(k + 1) % kirp.length];
    var ex = son[0] - bas[0];
    var ey = son[1] - bas[1];
    var giris = sonuc;
    sonuc = [];
    if (giris.length === 0) break;

    for (var i = 0; i < giris.length; i++) {
      var a = giris[i];
      var b = giris[(i + 1) % giris.length];
      var da = ex * (a[1] - bas[1]) - ey * (a[0] - bas[0]);
      var db = ex * (b[1] - bas[1]) - ey * (b[0] - bas[0]);
      var aIceride = da >= -1e-9;
      var bIceride = db >= -1e-9;
      if (aIceride !== bIceride) {
        var t = da / (da - db);
        sonuc.push([
          a[0] + t * (b[0] - a[0]),
          a[1] + t * (b[1] - a[1])
        ]);
      }
      if (bIceride) sonuc.push(b);
    }
  }
  return sonuc;
}

function izgara_dikdortgen_kirp_alani(cokgen, yariEn, yariBoy) {
  var sinir = [
    [-yariEn, -yariBoy],
    [yariEn, -yariBoy],
    [yariEn, yariBoy],
    [-yariEn, yariBoy]
  ];
  return izgara_cokgen_alani(izgara_cokgen_kirp(cokgen, sinir));
}

function izgara_desen_noktalari(sekil, boyut) {
  if (sekil === "kare") {
    return [
      [-boyut / 2, -boyut / 2],
      [boyut / 2, -boyut / 2],
      [boyut / 2, boyut / 2],
      [-boyut / 2, boyut / 2]
    ];
  }

  var adet = 180;
  var yaricap = boyut / 2;
  if (sekil === "sekizgen") {
    adet = 8;
    yaricap = boyut / (2 * Math.cos(Math.PI / 8));
  } else if (sekil === "petek") {
    adet = 6;
    yaricap = boyut / (2 * Math.cos(Math.PI / 6));
  } else if (sekil === "besgen") {
    adet = 5;
  } else if (sekil === "ucgen") {
    adet = 3;
  }

  var noktalar = [];
  for (var i = 0; i < adet; i++) {
    var aci = 2 * Math.PI * i / adet;
    noktalar.push([yaricap * Math.cos(aci), yaricap * Math.sin(aci)]);
  }
  return noktalar;
}

function izgara_delik_alani(p, icEn, icBoy) {
  var boyut = 8;
  var aralik = 3;
  var pitch = boyut + aralik;
  var dy = p.delik_sekli === "petek" ? pitch * 0.866 : pitch;
  var yariEn = icEn / 2 - 1;
  var yariBoy = icBoy / 2 - 1;
  var temel = izgara_desen_noktalari(p.delik_sekli, boyut);
  var tamAlan = izgara_cokgen_alani(temel);
  var minX = Infinity;
  var maxX = -Infinity;
  var minY = Infinity;
  var maxY = -Infinity;
  for (var n = 0; n < temel.length; n++) {
    minX = Math.min(minX, temel[n][0]);
    maxX = Math.max(maxX, temel[n][0]);
    minY = Math.min(minY, temel[n][1]);
    maxY = Math.max(maxY, temel[n][1]);
  }

  var nx = Math.ceil(p.en / pitch) + 1;
  var ny = Math.ceil(p.boy / dy) + 1;
  var toplam = 0;
  for (var j = -ny; j <= ny; j++) {
    var cxKaydir = j % 2 === 0 ? 0 : pitch / 2;
    var cy = j * dy;
    for (var i = -nx; i <= nx; i++) {
      var cx = i * pitch + cxKaydir;
      if (cx + maxX <= yariEn && cx + minX >= -yariEn &&
          cy + maxY <= yariBoy && cy + minY >= -yariBoy) {
        toplam += tamAlan;
      } else if (cx + maxX > -yariEn && cx + minX < yariEn &&
                 cy + maxY > -yariBoy && cy + minY < yariBoy) {
        var tasinmis = [];
        for (var q = 0; q < temel.length; q++) {
          tasinmis.push([cx + temel[q][0], cy + temel[q][1]]);
        }
        toplam += izgara_dikdortgen_kirp_alani(tasinmis, yariEn, yariBoy);
      }
    }
  }
  return toplam;
}

function izgara_slat_cokgeni(y, z, aci) {
  var c = Math.cos(aci);
  var s = Math.sin(aci);
  var yerel = [[-4.5, -0.8], [4.5, -0.8], [4.5, 0.8], [-4.5, 0.8]];
  var sonuc = [];
  for (var i = 0; i < yerel.length; i++) {
    var v = yerel[i][0];
    var w = yerel[i][1];
    sonuc.push([y + v * c - w * s, z + v * s + w * c]);
  }
  return sonuc;
}

function izgara_panjur_alani(boy, derinlik, derece) {
  var aci = derece * Math.PI / 180;
  var pitch = 6.5;
  var ny = Math.ceil(boy / pitch) + 1;
  var sinir = [
    [-boy / 2, 0],
    [boy / 2, 0],
    [boy / 2, derinlik],
    [-boy / 2, derinlik]
  ];
  var slatlar = [];
  var toplam = 0;
  for (var j = -ny; j <= ny; j++) {
    var slat = izgara_slat_cokgeni(j * pitch, derinlik / 2, aci);
    slatlar.push(slat);
    toplam += izgara_cokgen_alani(izgara_cokgen_kirp(slat, sinir));
  }

  for (var k = 0; k + 1 < slatlar.length; k++) {
    var ortak = izgara_cokgen_kirp(slatlar[k], slatlar[k + 1]);
    ortak = izgara_cokgen_kirp(ortak, sinir);
    toplam -= izgara_cokgen_alani(ortak);
  }
  return toplam;
}

function izgara_erozyon_alani(en, boy, yaricap, mesafe) {
  var yeniEn = en - 2 * mesafe;
  var yeniBoy = boy - 2 * mesafe;
  var yeniR = Math.max(yaricap - mesafe, 0);
  return yeniEn * yeniBoy - (4 - Math.PI) * yeniR * yeniR;
}

function izgara(p) {
  var cerceveEn = 6;
  var koseR = 3;
  var icEn = p.en - 2 * cerceveEn;
  var icBoy = p.boy - 2 * cerceveEn;
  var disAlan = izgara_erozyon_alani(p.en, p.boy, koseR, 0);
  var icAlan = icEn * icBoy;
  var cerceveAlani = disAlan - icAlan;

  var etekDis = izgara_erozyon_alani(p.en, p.boy, koseR, 0.4);
  var etekIc = izgara_erozyon_alani(p.en, p.boy, koseR, 2.2);
  var etekHacmi = (etekDis - etekIc) * 8;
  var hacim = cerceveAlani * p.derinlik + etekHacmi;

  if (p.tip === "kor") {
    hacim += icAlan * p.derinlik;
  } else if (p.tip === "delikli") {
    var delikAlani = izgara_delik_alani(p, icEn, icBoy);
    hacim += (icAlan - delikAlani) * Math.min(p.derinlik, 3);
  } else {
    hacim += icEn * izgara_panjur_alani(icBoy, p.derinlik, p.panjur_acisi);
  }
  return hacim;
}
