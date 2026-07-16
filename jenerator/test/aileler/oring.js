function oring(p) {
  var merkezYaricap = p.ic_cap / 2 + p.kesit_cap / 2;
  var kesitAlani;

  if (p.profil === "kare") {
    kesitAlani = p.kesit_cap * p.kesit_cap;
  } else if (p.profil === "pahli") {
    // Okan onayi (16 Tem gece): 0.875 eski motora (0.25xCS pah) kalibreydi;
    // uretim motoru pahi 0.18xCS -> teorik 1-4*(0.18^2)/2 = 0.9352, OLCULEN
    // 0.93349 (8 set, hepsi ayni 5 basamak — render poligonizasyon payi dahil).
    kesitAlani = 0.93349 * p.kesit_cap * p.kesit_cap;
  } else {
    kesitAlani = Math.PI * p.kesit_cap * p.kesit_cap / 4;
  }

  return kesitAlani * 2 * Math.PI * merkezYaricap;
}
