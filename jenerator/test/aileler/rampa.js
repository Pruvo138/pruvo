function rampa(p) {
  var uzunluk = p.uzunluk;
  var genislik = p.genislik;
  var yukseklik = p.egim_yontemi === "aci" ?
    uzunluk * Math.tan(p.egim_acisi * Math.PI / 180) : p.yukseklik;

  if (p.ust_yuzey === "basamakli") {
    var basamakSayisi = 8;
    return genislik * uzunluk * yukseklik *
      (basamakSayisi - 1) / (2 * basamakSayisi);
  }

  var hacim = genislik * uzunluk * yukseklik / 2;
  if (p.ust_yuzey === "tirtikli") {
    var egimBoyu = Math.sqrt(uzunluk * uzunluk + yukseklik * yukseklik);
    var tirtikSayisi = Math.floor(egimBoyu / 3);
    var etkinTirtik = 0;
    for (var k = 1; k <= tirtikSayisi; k++) {
      var x = k * 3 * uzunluk / egimBoyu;
      if (x < uzunluk - 1.6) etkinTirtik++;
    }
    // Her tırtık gövde üstünde 1,6 mm x 1 mm net kesit oluşturur.
    hacim += etkinTirtik * 1.6 * genislik;
  }

  return hacim;
}
