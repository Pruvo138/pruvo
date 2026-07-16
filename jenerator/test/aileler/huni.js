function huni(p) {
  var pi = Math.PI;
  var icUstYaricap = p.agiz_capi / 2;
  var icAltYaricap = p.uc_capi / 2;
  var disAltYaricap = icAltYaricap + 1.2;
  var disUstYaricap = icUstYaricap + 1.5;

  var ucHacmi = pi * p.uc_boyu *
    (disAltYaricap * disAltYaricap - icAltYaricap * icAltYaricap);

  var disKoni = pi * p.yukseklik / 3 *
    (disAltYaricap * disAltYaricap +
     disAltYaricap * disUstYaricap +
     disUstYaricap * disUstYaricap);
  var icKoni = pi * p.yukseklik / 3 *
    (icAltYaricap * icAltYaricap +
     icAltYaricap * icUstYaricap +
     icUstYaricap * icUstYaricap);

  var kenarDisYaricap = disUstYaricap + 4;
  var kenarHacmi = pi * 1.5 *
    (kenarDisYaricap * kenarDisYaricap -
     disUstYaricap * disUstYaricap);

  // Eğik düzlemin boru cidarından çıkardığı hacim; aralıklar kesimi uçta tutar.
  var aci = p.uc_acisi * pi / 180;
  var ucKesigi = Math.tan(aci) * disAltYaricap * pi *
    (disAltYaricap * disAltYaricap - icAltYaricap * icAltYaricap);

  return ucHacmi + disKoni - icKoni + kenarHacmi - ucKesigi;
}
