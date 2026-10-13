function saksi(p) {
  // Ölçüye özel saksı/vazo: üretim modeli geometri sözleşmesinin KAPALI FORMU.
  // Döner kesit: dış kesik koni (alt_cap/2 -> ust_cap/2, Z 0..yukseklik) eksi iç
  // kesik koni (yatay duvar `duvar`, Z taban..yukseklik) eksi taban plakasındaki
  // merkez drenaj silindiri.
  // Kalibrasyon (13 Eki, 17 gerçek render seti): en kötü sapma %0,07 — fark
  // üretimdeki çokgen yaklaşımıdır; formül bilerek ANALİTİK tutulur (fiyat
  // referansı da bu formülden çıkar).
  // parca === "tabak" -> alt tabak: dolu tabanlı silindir kap, dış çap alt_cap+6,
  // yükseklik tabak_yuksekligi, duvar `duvar`, taban `taban`. Ürün şemasında
  // `parca` parametresi YOKTUR (sipariş saksıyı fiyatlar, tabak ayrı kademe ekidir);
  // tabak hacmi bu kolla, aynı aile fonksiyonundan okunur.
  if (p.parca === "tabak") { return saksi_tabak(p); }
  var R1 = p.alt_cap / 2;
  var R2 = p.ust_cap / 2;
  var r1 = Math.max(0.5, R1 - p.duvar);
  var r2 = Math.max(0.5, R2 - p.duvar);
  var H = p.yukseklik;
  var t = p.taban;
  var dis = Math.PI * H / 3 * (R1 * R1 + R1 * R2 + R2 * R2);
  var ic = Math.PI * (H - t) / 3 * (r1 * r1 + r1 * r2 + r2 * r2);
  var drenaj = (p.drenaj === "var" || p.drenaj === 1)
    ? Math.PI * (p.drenaj_capi / 2) * (p.drenaj_capi / 2) * t : 0;
  return dis - ic - drenaj;
}

function saksi_tabak(p) {
  var Rt = (p.alt_cap + 6) / 2;
  var ri = Rt - p.duvar;
  var h = p.tabak_yuksekligi;
  return Math.PI * Rt * Rt * h - Math.PI * ri * ri * (h - p.taban);
}
