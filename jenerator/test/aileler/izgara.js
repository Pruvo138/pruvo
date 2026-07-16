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

function izgara_desen_noktalari(sekil) {
  // Uretim motorunun desen sekilleri, sabit olcu [8,8]:
  // yuvarlak cember r4; sekizgen CEVREL 8-gen r=4/cos22.5, KOSELER 0°'da
  // (BOSL2 circum kendi 22.5° dondurur + motorun 22.5 spin'i koseyi 0'a
  // getirir); petek IC 6-gen r4 faz 0; besgen r4 faz +18°; ucgen r4 faz 0.
  if (sekil === "kare") {
    return [[-4, -4], [4, -4], [4, 4], [-4, 4]];
  }
  var adet = 180;
  var yaricap = 4;
  var faz = 0;
  if (sekil === "sekizgen") {
    adet = 8;
    yaricap = 4 / Math.cos(Math.PI / 8);
  } else if (sekil === "petek") {
    adet = 6;
  } else if (sekil === "besgen") {
    adet = 5;
    faz = 18 * Math.PI / 180;
  } else if (sekil === "ucgen") {
    adet = 3;
  }
  var noktalar = [];
  for (var i = 0; i < adet; i++) {
    var aci = faz + 2 * Math.PI * i / adet;
    noktalar.push([yaricap * Math.cos(aci), yaricap * Math.sin(aci)]);
  }
  return noktalar;
}

function izgara_delik_alani(p, icYariEn, icYariBoy) {
  // Motor kafesi: adim [11, 7] (desen 8 + aralik 3; sasirtma satir adimini
  // 7'ye dusurur), kopya sayisi floor(olcu/adim)+1, merkezli, INDEKS
  // PARITESI (i+j) cift olanlar kalir (dama deseni). Delikler govde
  // sinirina degil IC cerceve (insert duvari 2 mm) dikdortgenine kirpilir —
  // duvar bandindaki kisim insert ile geri doluyor.
  var temel = izgara_desen_noktalari(p.delik_sekli);
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
  var nx = Math.floor(p.en / 11) + 1;
  var ny = Math.floor(p.boy / 7) + 1;
  var toplam = 0;
  for (var j = 0; j < ny; j++) {
    var cy = (j - (ny - 1) / 2) * 7;
    for (var i = 0; i < nx; i++) {
      if ((i + j) % 2 !== 0) continue;
      var cx = (i - (nx - 1) / 2) * 11;
      if (cx + minX >= -icYariEn && cx + maxX <= icYariEn &&
          cy + minY >= -icYariBoy && cy + maxY <= icYariBoy) {
        toplam += tamAlan;
      } else if (cx + maxX > -icYariEn && cx + minX < icYariEn &&
                 cy + maxY > -icYariBoy && cy + minY < icYariBoy) {
        var tasinmis = [];
        for (var q = 0; q < temel.length; q++) {
          tasinmis.push([cx + temel[q][0], cy + temel[q][1]]);
        }
        toplam += izgara_dikdortgen_kirp_alani(tasinmis, icYariEn, icYariBoy);
      }
    }
  }
  return toplam;
}

function izgara_panjur_hacmi(p, govdeDerinligi) {
  // 7 yatay egik cita (motor: 8 hucre "between" dagilimi = 7 cita, dikey
  // cita yok), kesit kalinligi 2 mm, boy en-4; z 0..H araligina ve ic
  // cerceveye kirpilir (sayisal z-integrali).
  var il = p.boy - 4;
  var aci = p.panjur_acisi * Math.PI / 180;
  var g = (il - 14) / 8;
  var adimBoyu = 2 + g;
  var ilkMerkez = -il / 2 + g + 1;
  var H = govdeDerinligi;
  var adim = 60;
  var dz = H / adim;
  var tanA = Math.tan(aci);
  var yariKalinlik = 1 / Math.cos(aci);
  var alan = 0;
  for (var s = 0; s < 7; s++) {
    var merkez = ilkMerkez + s * adimBoyu;
    for (var k = 0; k < adim; k++) {
      var z = (k + 0.5) * dz - H / 2;
      var orta = merkez + z * tanA;
      var lo = Math.max(orta - yariKalinlik, -il / 2);
      var hi = Math.min(orta + yariKalinlik, il / 2);
      if (hi > lo) alan += (hi - lo) * dz;
    }
  }
  return alan * (p.en - 4);
}

function izgara(p) {
  // Uretim motoruna kalibre (Faz E): govde derinligi min(derinlik, 8)
  // (insert derinligi tavani); cepecevre insert duvari (2 mm et, 8 mm boy);
  // kapak plakasi cerceveden 6 mm tasar, 3 mm kalin. Panjur tipinde plaka
  // YOK (yalniz citalar + insert + kapak).
  var H = Math.min(p.derinlik, 8);
  var ringAlani = 4 * (p.en + p.boy) - 16;
  var kapak = ((p.en + 12) * (p.boy + 12) - p.en * p.boy) * 3;

  if (p.tip === "panjur") {
    return izgara_panjur_hacmi(p, H) + ringAlani * 8 + kapak;
  }

  var hacim = p.en * p.boy * H + ringAlani * (8 - H) + kapak;
  if (p.tip === "delikli") {
    hacim -= izgara_delik_alani(p, (p.en - 4) / 2, (p.boy - 4) / 2) * H;
  }
  return hacim;
}
