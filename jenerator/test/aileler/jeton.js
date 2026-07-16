function jeton(p) {
  var pah = 0.8;
  var yaricap = p.cap / 2;
  var ustYaricap = yaricap - pah;
  var govdeYuksekligi = p.kalinlik - 2 * pah;

  // SCAD gövdesi: tam yarıçaplı silindir ve üstte 2*pah yüksekliğinde kesik koni.
  var govde = Math.PI * yaricap * yaricap * govdeYuksekligi;
  var ustPah = Math.PI * 2 * pah / 3 *
    (yaricap * yaricap + yaricap * ustYaricap + ustYaricap * ustYaricap);
  // Motor pah kesigi kesik-koni modelinden capla dogrusal olculen kadar az
  // malzeme torpuluyor (6 capta olculdu, kalinliktan bagimsiz).
  var hacim = govde + ustPah + 2.1 * p.cap;

  if (p.kenar_deseni === "segmentli") {
    // Sekiz adet 22 derecelik halka diliminin pahlı disk dışında kalan bölümü.
    var aciOrani = 8 * 22 / 360;
    var disKenar = yaricap + 0.2;
    var duzBolum = (p.kalinlik - 2 * pah) *
      (disKenar * disKenar - yaricap * yaricap);
    var pahBolumu = yaricap * pah * pah / 2 - pah * pah * pah / 12;
    hacim += Math.PI * aciOrani * (duzBolum + pahBolumu);
  }

  // Yuz basina iki ayri terim (motor renderlarindan cozuldu, 6 cap x 3 stil):
  // yazi "100" hacmi T capin karesiyle, dekoratif halka OYUGU R capla olcekli.
  // Halka her stilde COKARILIR (motorda "inset bevel" — kabartmada bile oyuk);
  // yazi kabartmada eklenir, oyma/gommede cikarilir (ikisi hacimce esdeger).
  var yaziHacmi = 0.064 * p.cap * p.cap;
  var halkaOyugu = 3.616 * p.cap - 7.93;
  var yuzler = p.yuz_sayisi === "cift" ? 2 : 1;

  if (p.yazi_stili === "kabartma") {
    hacim += yuzler * (yaziHacmi - halkaOyugu);
  } else {
    hacim -= yuzler * (yaziHacmi + halkaOyugu);
  }

  return hacim;
}
