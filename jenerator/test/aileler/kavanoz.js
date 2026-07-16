function kavanoz_poly() {
  // esleme sabiti Segments=64: silindir kesitleri 64-gen — r^2 katsayısı
  var S = 64;
  return (S / (2 * Math.PI)) * Math.sin(2 * Math.PI / S) * Math.PI;
}

function kavanoz_vrod_dis(d, p, l) {
  // BOSL2 generic_threaded_rod (bizim trapez profil: derinlik 0.5p, tepe 0.25p,
  // blunt_start) DIŞ diş hacmi. Model: diş dibi silindiri + sarmal fitil
  // (kesit alanı 0.3125p², ağırlık merkezi dip+0.2p); blunt_start uç
  // düzeltmesi 1.04 tur (2026-07-17 kalibrasyonu, 10 ölçümde en kötü %0.07).
  var k = kavanoz_poly();
  var rr = d / 2 - p / 2;
  return k * rr * rr * l +
         0.3125 * p * p * 2 * Math.PI * (rr + 0.2 * p) *
         Math.max(0, l / p - 1.04);
}

function kavanoz_kapak_maske(d, p, l) {
  // Kapağın içinden çıkarılan İÇ diş maskesi ($slop=0.15, BOSL2 internal
  // büyütmesi + kapak içinde kalan blunt bölgesi dahil) — sabitler kapak
  // ölçümüne fit edildi (28 ölçümde en kötü %0.46, 2026-07-17).
  var k = kavanoz_poly();
  var rr = (d + 0.56 + 0.02 * p) / 2 - p / 2;
  return k * rr * rr * l +
         1.05 * 0.3125 * p * p * 2 * Math.PI * (rr + 0.2 * p) *
         Math.max(0, l / p + 0.20);
}

function kavanoz(p) {
  // Vidalı kapaklı kavanoz / kör tapa: kavanoz.scad sözleşmesi.
  // Ölçülen sapma tam ürün ızgarasında en kötü %0.22 (2026-07-17).
  var k = kavanoz_poly();
  var D = p.govde_capi;
  var R = D / 2;
  var H = p.yukseklik;
  var pt = p.dis_adimi;
  var t = Math.max(p.cidar, 1.6);
  if (p.urun_tipi === "tapa") {
    var et = Math.max(t, pt / 2 + 1.2);
    return k * (R + 4) * (R + 4) * 5 +
           kavanoz_vrod_dis(D, pt, H) -
           k * (R - et) * (R - et) * H;
  }
  var boyun = Math.min(Math.max(8, 3 * pt), 0.4 * H);
  var rIc = R - t;
  var rAgiz = R - pt / 2 - t;
  var rKpk = R + 0.5 + t;
  var govde = k * R * R * t +
              k * (R * R - rIc * rIc) * (H - boyun - t) +
              kavanoz_vrod_dis(D, pt, boyun) -
              k * rAgiz * rAgiz * boyun;
  var kapak = k * rKpk * rKpk * (t + boyun) -
              kavanoz_kapak_maske(D, pt, boyun);
  return govde + kapak;
}
