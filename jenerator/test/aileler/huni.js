function huni(p) {
  // Uretim motoruna kalibre (Faz E): koni duvari HER YERDE yatay 1.5 mm
  // (tube id+2*wall — eski model altta 1.2 varsayiyordu); uc borusunun disi
  // konik: kokte 1.5, ucta 1.2 duvar (od1=id+3, od2=id+2.4, ic silindirik).
  var pi = Math.PI;
  var icUstYaricap = p.agiz_capi / 2;
  var icAltYaricap = p.uc_capi / 2;
  var disUstYaricap = icUstYaricap + 1.5;
  var disAltYaricap = icAltYaricap + 1.5;

  var disKoni = pi * p.yukseklik / 3 *
    (disAltYaricap * disAltYaricap +
     disAltYaricap * disUstYaricap +
     disUstYaricap * disUstYaricap);
  var icKoni = pi * p.yukseklik / 3 *
    (icAltYaricap * icAltYaricap +
     icAltYaricap * icUstYaricap +
     icUstYaricap * icUstYaricap);

  var ucKok = icAltYaricap + 1.5;
  var ucTip = icAltYaricap + 1.2;
  var ucHacmi = pi * p.uc_boyu / 3 *
    (ucKok * ucKok + ucKok * ucTip + ucTip * ucTip) -
    pi * icAltYaricap * icAltYaricap * p.uc_boyu;

  // Kenar (brim): dis silindir sabit, IC DELIK koni egimini izler (motor
  // id2 = id1 - 2*slope*kalinlik) — sig genis hunilerde fark %4'e cikiyordu.
  var kenarDisYaricap = disUstYaricap + 4;
  var egim = (icUstYaricap - icAltYaricap) / p.yukseklik;
  var kenarIc1 = disUstYaricap - 0.05;
  var kenarIc2 = kenarIc1 - egim * 1.5;
  var kenarHacmi = pi * 1.5 *
    (kenarDisYaricap * kenarDisYaricap -
     (kenarIc1 * kenarIc1 + kenarIc1 * kenarIc2 + kenarIc2 * kenarIc2) / 3);

  // Eğik düzlemin boru cidarından çıkardığı hacim (uçtaki dar kesitte).
  var aci = p.uc_acisi * pi / 180;
  var ucKesigi = Math.tan(aci) * ucTip * pi *
    (ucTip * ucTip - icAltYaricap * icAltYaricap);

  return ucHacmi + disKoni - icKoni + kenarHacmi - ucKesigi;
}
