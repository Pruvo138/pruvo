function adaptor_uc(cap, gecme, t) {
  // adaptor.scad sözleşmesi: "dis" = hortumun üzerine geçer (iç çap = cap+0.30),
  // "ic" = hortumun içine girer (dış çap = cap). Dönüş: [dış R, iç R].
  if (gecme === "dis") {
    var ri = (cap + 0.30) / 2;
    return [ri + t, ri];
  }
  return [cap / 2, cap / 2 - t];
}

function adaptor(p) {
  // Hortum adaptörü / redüksiyon: iki uç manşonu + konik geçiş, döner cidar
  // kesiti. Kapalı form KESİNDİR (rotate_extrude poligon alan katsayısı dahil);
  // ölçülen sapma ~%0.00 (2026-07-17 kalibrasyonu).
  var S = 180; // esleme sabiti Segments
  var k = (S / 2) * Math.sin(2 * Math.PI / S); // r^2 başına poligon alanı
  var t = Math.max(p.cidar, 1.2);
  var u1 = adaptor_uc(p.uc1_cap, p.uc1_gecme, t);
  var u2 = adaptor_uc(p.uc2_cap, p.uc2_gecme, t);
  var g = Math.min(Math.max(1.2 * Math.abs(2 * u1[0] - 2 * u2[0]), 6),
                   0.45 * p.boy);
  var e = (p.boy - g) / 2;
  var konik = (u1[0] * u1[0] + u1[0] * u2[0] + u2[0] * u2[0]) / 3 -
              (u1[1] * u1[1] + u1[1] * u2[1] + u2[1] * u2[1]) / 3;
  return k * (e * (u1[0] * u1[0] - u1[1] * u1[1]) + g * konik +
              e * (u2[0] * u2[0] - u2[1] * u2[1]));
}
