function profil(p) {
  var h = p.yukseklik;
  var b = p.genislik;
  var t = p.et_kalinligi;
  var alan;

  if (p.kesit === "t") {
    alan = b * t + t * (h - t);
  } else if (p.kesit === "l") {
    alan = t * h + b * t - t * t;
  } else if (p.kesit === "i" || p.kesit === "z" || p.kesit === "u") {
    alan = t * h + 2 * b * t - 2 * t * t;
  } else if (p.kesit === "kutu") {
    alan = b * h;
    if (p.ic_yapi === "bos") alan -= (b - 2 * t) * (h - 2 * t);
  } else if (p.kesit === "cokgen") {
    var kenar = 6;
    var katsayi = kenar * Math.sin(2 * Math.PI / kenar) / 2;
    var disYaricap = b / 2;
    alan = katsayi * disYaricap * disYaricap;
    if (p.ic_yapi === "bos") {
      var icYaricap = disYaricap - t;
      alan -= katsayi * icYaricap * icYaricap;
    }
  } else if (p.kesit === "elips") {
    alan = Math.PI * b * h / 4;
    if (p.ic_yapi === "bos") alan -= Math.PI * (b - 2 * t) * (h - 2 * t) / 4;
  } else {
    // Sabit 40 serisi sigma: yuvarlatılmış dış kareden merkez deliği ve dört T-slot çıkarılır.
    var sigmaBoyu = 40;
    var koseYaricapi = 1.5;
    var disAlan = sigmaBoyu * sigmaBoyu - (4 - Math.PI) * koseYaricapi * koseYaricapi;
    var merkezDeligi = Math.PI * 3.4 * 3.4;
    var tekSlot = 11 * 12.4 + 8 * 2.05 - 8 * 0.05;
    alan = disAlan - merkezDeligi - 4 * tekSlot;
  }

  return alan * p.uzunluk;
}
