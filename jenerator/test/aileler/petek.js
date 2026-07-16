function petek_kirp_alani(noktalar, xmin, xmax, ymin, ymax) {
  var cokgen = noktalar;
  var sinirlar = [xmin, xmax, ymin, ymax];

  for (var kenar = 0; kenar < 4; kenar++) {
    var giris = cokgen;
    cokgen = [];
    if (giris.length === 0) return 0;

    for (var i = 0; i < giris.length; i++) {
      var a = giris[i];
      var b = giris[(i + 1) % giris.length];
      var aIceride;
      var bIceride;
      if (kenar === 0) {
        aIceride = a[0] >= sinirlar[kenar];
        bIceride = b[0] >= sinirlar[kenar];
      } else if (kenar === 1) {
        aIceride = a[0] <= sinirlar[kenar];
        bIceride = b[0] <= sinirlar[kenar];
      } else if (kenar === 2) {
        aIceride = a[1] >= sinirlar[kenar];
        bIceride = b[1] >= sinirlar[kenar];
      } else {
        aIceride = a[1] <= sinirlar[kenar];
        bIceride = b[1] <= sinirlar[kenar];
      }

      if (aIceride !== bIceride) {
        var t;
        if (kenar < 2) {
          t = (sinirlar[kenar] - a[0]) / (b[0] - a[0]);
          var dikey = [sinirlar[kenar], a[1] + t * (b[1] - a[1])];
          if (aIceride) cokgen.push(dikey);
          else cokgen.push(dikey);
        }
        else {
          t = (sinirlar[kenar] - a[1]) / (b[1] - a[1]);
          var yatay = [a[0] + t * (b[0] - a[0]), sinirlar[kenar]];
          if (aIceride) cokgen.push(yatay);
          else cokgen.push(yatay);
        }
      }
      if (bIceride) cokgen.push(b);
    }
  }

  var ikiAlan = 0;
  for (var j = 0; j < cokgen.length; j++) {
    var c = cokgen[j];
    var d = cokgen[(j + 1) % cokgen.length];
    ikiAlan += c[0] * d[1] - d[0] * c[1];
  }
  return Math.abs(ikiAlan) / 2;
}

function petek(p) {
  var aralik = 4;
  var s = p.goz_boyutu;
  var pitch = s + aralik;
  var inset = s / 2 + 0.6;
  var yariEn = p.en / 2 - inset;
  var yariBoy = p.boy / 2 - inset;
  var noktalar = [];
  var adet;
  var yaricap;

  if (p.desen === "kare") {
    noktalar = [[-s / 2, -s / 2], [s / 2, -s / 2],
      [s / 2, s / 2], [-s / 2, s / 2]];
  } else {
    if (p.desen === "petek") {
      adet = 6;
      yaricap = s / (2 * Math.cos(Math.PI / 6));
    } else if (p.desen === "sekizgen") {
      adet = 8;
      yaricap = s / (2 * Math.cos(Math.PI / 8));
    } else if (p.desen === "besgen") {
      adet = 5;
      yaricap = s / 2;
    } else if (p.desen === "ucgen") {
      adet = 3;
      yaricap = s / 2;
    } else {
      adet = 180;
      yaricap = s / 2;
    }
    for (var k = 0; k < adet; k++) {
      var aci = 2 * Math.PI * k / adet;
      noktalar.push([yaricap * Math.cos(aci), yaricap * Math.sin(aci)]);
    }
  }

  var tamIkiAlan = 0;
  var minX = Infinity;
  var maxX = -Infinity;
  var minY = Infinity;
  var maxY = -Infinity;
  for (var n = 0; n < noktalar.length; n++) {
    var q = noktalar[n];
    var sonraki = noktalar[(n + 1) % noktalar.length];
    tamIkiAlan += q[0] * sonraki[1] - sonraki[0] * q[1];
    minX = Math.min(minX, q[0]);
    maxX = Math.max(maxX, q[0]);
    minY = Math.min(minY, q[1]);
    maxY = Math.max(maxY, q[1]);
  }
  var tamAlan = Math.abs(tamIkiAlan) / 2;
  var desenAlani = 0;

  if (yariEn > 0 && yariBoy > 0) {
    var dy = p.desen === "petek" ? pitch * 0.8660 : pitch;
    var nx = Math.ceil(p.en / pitch / 2) + 1;
    var ny = Math.ceil(p.boy / dy / 2) + 1;

    for (var satir = -ny; satir <= ny; satir++) {
      var xKaydir = satir % 2 === 0 ? 0 : pitch / 2;
      var cy = satir * dy;
      for (var sutun = -nx; sutun <= nx; sutun++) {
        var cx = sutun * pitch + xKaydir;
        if (cx + maxX <= yariEn && cx + minX >= -yariEn &&
            cy + maxY <= yariBoy && cy + minY >= -yariBoy) {
          desenAlani += tamAlan;
        } else if (cx + maxX > -yariEn && cx + minX < yariEn &&
                   cy + maxY > -yariBoy && cy + minY < yariBoy) {
          var tasinmis = [];
          for (var v = 0; v < noktalar.length; v++) {
            tasinmis.push([cx + noktalar[v][0], cy + noktalar[v][1]]);
          }
          desenAlani += petek_kirp_alani(
            tasinmis, -yariEn, yariEn, -yariBoy, yariBoy);
        }
      }
    }
  }

  var tabanAlani = p.en * p.boy;
  if (p.mod === "kabartma") {
    var kabartma = Math.max(p.kalinlik * 0.4, 1);
    return tabanAlani * p.kalinlik + desenAlani * (kabartma - 0.01);
  }
  return (tabanAlani - desenAlani) * p.kalinlik;
}
