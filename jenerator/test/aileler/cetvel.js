function cetvel_rakam_alani(uzunluk, boyut) {
  // Aralık 10–50 olduğundan 0..uzunluk etiketlerindeki toplam rakam sayısı 2n-8'dir.
  return 0.17 * boyut * boyut * (2 * uzunluk - 8);
}

function cetvel_isaret_alani(p, kenarIsareti) {
  var n = p.uzunluk;
  var w = p.genislik;
  var inc = p.sistem === "inc";
  var katsayi;
  var yaziBoyutu;

  if (kenarIsareti) {
    katsayi = inc ? 1.165 * n + 0.2 : 0.805 * n + 0.2;
    yaziBoyutu = Math.min(0.2 * w, 4);
  } else {
    katsayi = inc ? 1.323 * n + 0.315 : 0.909 * n + 0.315;
    yaziBoyutu = Math.min(0.22 * w, 4.5);
  }

  return w * katsayi + cetvel_rakam_alani(n, yaziBoyutu);
}

function cetvel(p) {
  var birimMm = p.sistem === "inc" ? 25.4 : 10;
  var a = p.uzunluk * birimMm;
  var w = p.genislik;
  var r = 3;
  var alan;
  var kenarIsareti = p.tip !== "duz";

  if (p.tip === "ucgen") {
    // Dış ve iç 45° üçgenlerde aynı köşe yarıçapı kullanıldığı için düzeltmeler yok olur.
    alan = 3 * a * a / 8;
  } else if (p.tip === "l_gonye") {
    // İki kolun birleşim alanı; beş dış köşedeki yuvarlatma ayrıca çıkarılır.
    alan = a * w + 0.6 * a * w - w * w;
    alan -= 5 * (1 - Math.PI / 4) * r * r;
  } else {
    alan = (a + 12) * w - (4 - Math.PI) * r * r;
  }

  var govdeHacmi = alan * p.kalinlik;
  var isaretHacmi = 0.59 * cetvel_isaret_alani(p, kenarIsareti);
  return p.isaret_stili === "kabartma" ? govdeHacmi + isaretHacmi : govdeHacmi - isaretHacmi;
}
