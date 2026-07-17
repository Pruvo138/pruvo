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
          cokgen.push([sinirlar[kenar], a[1] + t * (b[1] - a[1])]);
        } else {
          t = (sinirlar[kenar] - a[1]) / (b[1] - a[1]);
          cokgen.push([a[0] + t * (b[0] - a[0]), sinirlar[kenar]]);
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

function petek_desen_cokgeni(desen, goz) {
  // Uretim motorunun desen sekilleri (yaricap/aci duzeni birebir):
  // petek: 6-gen r=goz/2 spin 0; sekizgen: cevrel 8-gen r/cos22.5, KOSELER
  // 0°'da (BOSL2 circum kendi 22.5° dondurur + motorun 22.5 spin'i toplam
  // koseyi 0'a getirir — render dokumuyle dogrulandi, bbox=2r/cos22.5);
  // besgen: 5-gen -18°; ucgen: 3-gen 0°; yuvarlak: cember; kare: kare.
  var r = goz / 2;
  var noktalar = [];
  var adet;
  var yaricap = r;
  var faz = 0;
  if (desen === "kare") {
    return [[-r, -r], [r, -r], [r, r], [-r, r]];
  }
  if (desen === "petek") {
    adet = 6;
  } else if (desen === "sekizgen") {
    adet = 8;
    yaricap = r / Math.cos(Math.PI / 8);
  } else if (desen === "besgen") {
    adet = 5;
    faz = -18 * Math.PI / 180;
  } else if (desen === "ucgen") {
    adet = 3;
  } else {
    adet = 180; // yuvarlak
  }
  for (var i = 0; i < adet; i++) {
    var aci = faz + 2 * Math.PI * i / adet;
    noktalar.push([yaricap * Math.cos(aci), yaricap * Math.sin(aci)]);
  }
  return noktalar;
}

function petek(p) {
  var noktalar = petek_desen_cokgeni(p.desen, p.goz_boyutu);
  var minX = Infinity;
  var maxX = -Infinity;
  var minY = Infinity;
  var maxY = -Infinity;
  var tamIkiAlan = 0;
  for (var n = 0; n < noktalar.length; n++) {
    var q = noktalar[n];
    var s = noktalar[(n + 1) % noktalar.length];
    tamIkiAlan += q[0] * s[1] - s[0] * q[1];
    minX = Math.min(minX, q[0]);
    maxX = Math.max(maxX, q[0]);
    minY = Math.min(minY, q[1]);
    maxY = Math.max(maxY, q[1]);
  }
  var tamAlan = Math.abs(tamIkiAlan) / 2;

  // Motor lattice'i: SABIT 40x40 kopya, merkezde, SASIRTMASIZ; adim = desen
  // sinir kutusu (0.1'e yuvarlanir) + 4 mm. Kopya ofsetleri yarim-adimli
  // ((k-19.5)*adim). Taban disina tasan kopyalar delikli modda kirpilir.
  var bboxEn = Math.round((maxX - minX) * 10) / 10;
  var bboxBoy = Math.round((maxY - minY) * 10) / 10;
  var adimX = bboxEn + 4;
  var adimY = bboxBoy + 4;
  var yariEn = p.en / 2;
  var yariBoy = p.boy / 2;

  var desenAlani = 0;
  for (var satir = 0; satir < 40; satir++) {
    var cy = (satir - 19.5) * adimY;
    if (cy + minY > yariBoy || cy + maxY < -yariBoy) continue;
    for (var sutun = 0; sutun < 40; sutun++) {
      var cx = (sutun - 19.5) * adimX;
      if (cx + minX > yariEn || cx + maxX < -yariEn) continue;
      if (cx + minX >= -yariEn && cx + maxX <= yariEn &&
          cy + minY >= -yariBoy && cy + maxY <= yariBoy) {
        desenAlani += tamAlan;
      } else {
        var tasinmis = [];
        for (var v = 0; v < noktalar.length; v++) {
          tasinmis.push([cx + noktalar[v][0], cy + noktalar[v][1]]);
        }
        desenAlani += petek_kirp_alani(
          tasinmis, -yariEn, yariEn, -yariBoy, yariBoy);
      }
    }
  }

  var tabanAlani = p.en * p.boy;
  if (p.mod === "kabartma") {
    // Uretim motorunda bu semayla DUZGUN karsiligi yok (desen kopyalari
    // tabana kirpilmadan 20 mm kolon dikiyor) — fiyat, urunun NIYETINE gore
    // (panel + desen kadar kabartma) korunur; onizleme sema kapisinda kapali.
    var kabartma = Math.max(p.kalinlik * 0.4, 1);
    return tabanAlani * p.kalinlik + desenAlani * kabartma;
  }
  // delikli: desen tam derinlikte panelden cikarilir.
  return (tabanAlani - desenAlani) * p.kalinlik;
}
