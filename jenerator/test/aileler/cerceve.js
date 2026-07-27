function cerceve(p) {
  // Olcuye-ozel CERCEVE (Koolm Frame Maker tureviyle uretilir): cerceve.scad
  // sozlesmesi. Musteri 5 param: acilik_eni/boyu, kenar_genisligi, derinlik,
  // kenar_stili. caption KAPALI, mounting/lip/retainer YOK (guvenli varsayilan).
  //
  // Cerceve OYUK dikdortgen prizma:  V = (Aout - Aopen)*D - kenar_kesinti.
  //   Aout  = dis rounded-rect alani (Outer_Rounding=4 sabit): Wx*Hy-(4-pi)rOut^2
  //   Aopen = dikdortgen acilik (Opening_Rounding=0): (OW+2ocl)(OH+2ocl)
  //   kenar_kesinti = c_stil * M * e ; M = e-genisligindeki dis halka alani
  // c_stil olculen izgaradan fit (2026-07-27, olcum/cerceve_katsayi_fit.py; her
  // konfigde yayilim <=0.005, teoriyle ortusur). flat analitik taban sapmasi
  // %0.004; tam izgara (44 nokta) en kotu sapma <=%1 (olcum/cerceve_kalibre.py).
  var OCL = 0.1;          // Opening_Clearance (sabit)
  var K = 4 - Math.PI;    // rounded-rect kose alan terimi katsayisi
  var EDGE = 1.6;         // Edge_Size (sabit)
  var MINWALL = 1;        // _Minimum_Wall (sabit)

  var OW = p.acilik_eni, OH = p.acilik_boyu, B = p.kenar_genisligi, D = p.derinlik;
  var Wx = OW + 2 * OCL + 2 * B;
  var Hy = OH + 2 * OCL + 2 * B;
  var rOut = Math.min(4.0, Math.min(Wx, Hy) / 2.0);          // constrain(Outer_Rounding)
  // _Resolved_Edge_Size = constrain(Edge_Size, 0, min(D-0.02, rail-minwall)); rail=B (lip yok)
  var e = Math.max(0.0, Math.min(EDGE, Math.min(D - 0.02, B - MINWALL)));

  var Aout = Wx * Hy - K * rOut * rOut;
  var Aopen = (OW + 2 * OCL) * (OH + 2 * OCL);
  var rt = Math.max(0.0, rOut - e);
  var Atre = (Wx - 2 * e) * (Hy - 2 * e) - K * rt * rt;
  var M = Aout - Atre;                                        // dis halka alani (e genis)

  var C = {
    flat: 0.0, chamfer: 0.50158, rounded: 0.21951,
    concave: 0.78239, ogee: 0.50203, stepped: 0.98750
  };
  var c = C[p.kenar_stili];
  if (c === undefined) c = 0.0;                               // bilinmeyen stil -> flat (guvenli)

  return (Aout - Aopen) * D - c * M * e;
}
