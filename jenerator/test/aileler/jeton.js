function jeton(p) {
  var pah = 0.8;
  var yaricap = p.cap / 2;
  var ustYaricap = yaricap - pah;
  var govdeYuksekligi = p.kalinlik - 2 * pah;

  // SCAD gövdesi: tam yarıçaplı silindir ve üstte 2*pah yüksekliğinde kesik koni.
  var govde = Math.PI * yaricap * yaricap * govdeYuksekligi;
  var ustPah = Math.PI * 2 * pah / 3 *
    (yaricap * yaricap + yaricap * ustYaricap + ustYaricap * ustYaricap);
  var hacim = govde + ustPah;

  if (p.kenar_deseni === "segmentli") {
    // Sekiz adet 22 derecelik halka diliminin pahlı disk dışında kalan bölümü.
    var aciOrani = 8 * 22 / 360;
    var disKenar = yaricap + 0.2;
    var duzBolum = (p.kalinlik - 2 * pah) *
      (disKenar * disKenar - yaricap * yaricap);
    var pahBolumu = yaricap * pah * pah / 2 - pah * pah * pah / 12;
    hacim += Math.PI * aciOrani * (duzBolum + pahBolumu);
  }

  // Varsayılan "100" yazısı ve dekoratif halkanın ölçeklenen 2B alanı.
  var yaziBoyutu = p.cap * 0.34;
  var isaretAlani = Math.PI * (p.cap * 0.82 - 1) + 0.67 * yaziBoyutu * yaziBoyutu;
  var yuzler = p.yuz_sayisi === "cift" ? 2 : 1;

  if (p.yazi_stili === "kabartma") {
    hacim += isaretAlani * 0.69 * yuzler;
  } else {
    hacim -= isaretAlani * (yuzler === 2 ? 1.39 : 0.69);
  }

  return hacim;
}
