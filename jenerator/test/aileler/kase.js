function kase_knob_hacmi(cap) {
  var yaricap = 6;
  var yukseklik = 18;
  var altYaricap = cap * 0.3;
  var ustYaricap = cap * 0.5;
  var dx = ustYaricap - altYaricap;
  var uzunluk = Math.sqrt(dx * dx + yukseklik * yukseklik);
  var ux = dx / uzunluk;
  var uz = yukseklik / uzunluk;
  var aci = Math.acos(ux);
  var teget = yaricap / Math.tan(aci / 2);
  var z1 = yukseklik / 2 - uz * teget;
  var r1 = ustYaricap - ux * teget;
  var merkezX = ustYaricap - teget;
  var merkezZ = yukseklik / 2 - yaricap;
  var ilkYukseklik = z1 + yukseklik / 2;
  var konik = Math.PI * ilkYukseklik *
    (altYaricap * altYaricap + altYaricap * r1 + r1 * r1) / 3;
  var u1 = z1 - merkezZ;
  var u2 = yaricap;

  function kase_knob_ilkel(u) {
    var kok = Math.sqrt(Math.max(0, yaricap * yaricap - u * u));
    return merkezX * merkezX * u +
      merkezX * (u * kok + yaricap * yaricap * Math.asin(u / yaricap)) +
      yaricap * yaricap * u - u * u * u / 3;
  }

  return konik + Math.PI * (kase_knob_ilkel(u2) - kase_knob_ilkel(u1));
}

function kase(p) {
  var yukseklik = 8;
  var pah = 2.5;
  var en = 3.1 * p.yazi_boyutu + 2 * p.dolgu;
  var boy = p.bicim === "dikdortgen" ?
    2.6 * p.yazi_boyutu + 2 * p.dolgu : en;
  var taban;

  if (p.bicim === "yuvarlak") {
    var altYaricap = en / 2;
    var ustYaricap = altYaricap - 2;
    var egimUzunlugu = Math.sqrt(yukseklik * yukseklik + 4);
    var araYaricap = ustYaricap + pah * 2 / egimUzunlugu;
    var araYukseklik = yukseklik - pah * yukseklik / egimUzunlugu;
    var tepeYaricap = ustYaricap - pah;
    taban = Math.PI * araYukseklik *
      (altYaricap * altYaricap + altYaricap * araYaricap + araYaricap * araYaricap) / 3;
    taban += Math.PI * (yukseklik - araYukseklik) *
      (araYaricap * araYaricap + araYaricap * tepeYaricap + tepeYaricap * tepeYaricap) / 3;
  } else {
    taban = yukseklik * (en * boy - 2 * en - 2 * boy + 16 / 3) -
      2 * pah * pah * yukseklik;
  }

  // Varsayılan kalın yazının ölçülen 2B alanı, yazı boyutunun karesiyle ölçeklenir.
  var rolyef = 2.1218677380952453 * p.yazi_boyutu * p.yazi_boyutu *
    p.kabartma_derinligi;
  var toplam = taban + rolyef;

  if (p.sap === "sapli") {
    var topuzCapi = Math.max(en * 0.7, 22);
    // Dişli mil, gövde yuvası ve topuzla örtüşen bölümün kalibre edilmiş net etkisi.
    toplam += kase_knob_hacmi(topuzCapi) - 210.720722018491;
  }

  return toplam;
}
