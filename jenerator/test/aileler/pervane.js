function pervane_kanat_tablosu(cap) {
  // Kanat hacmi motor renderlarindan OLCULMUS tablo (cap 60..300, 15'er mm;
  // kanat sayisindan/milden bagimsizligi olculdu, dogrusal ara deger).
  // Kapali-form NACA modeli motorun kanat kirpma/fairing zinciriyle buyuk
  // capta ayrisiyordu (%28'e kadar) — disli konik tablosu deseni uygulanir.
  var tablo = [118.3, 243.2, 433.2, 703.1, 1065.0, 1477.6, 1958.0, 2507.9,
    3125.6, 3810.9, 4562.2, 5382.0, 6265.4, 7212.5, 8222.1, 9293.0, 10422.9];
  var x = (Math.min(Math.max(cap, 60), 300) - 60) / 15;
  var i = Math.min(Math.floor(x), tablo.length - 2);
  return tablo[i] + (tablo[i + 1] - tablo[i]) * (x - i);
}

function pervane_delik_alani(baglanti, cap) {
  // Mil yuvasi kesit alani (motor bore maskeleriyle birebir kapali formlar).
  var r = cap / 2;
  if (baglanti === "altigen") return Math.sqrt(3) * cap * cap / 2;
  if (baglanti === "d_lama") {
    var kesim = r * r * Math.acos(0.7) - 0.7 * r * r * Math.sqrt(1 - 0.49);
    return Math.PI * r * r - kesim;
  }
  if (baglanti === "kanalli") {
    // DIN kama tablosu: cap<=6 [2,1.0], <=8 [2,1.2], <=10 [3,1.4], <=12 [3,1.8].
    var kw = cap <= 6 ? [2, 1.0] : cap <= 8 ? [2, 1.2] :
             cap <= 10 ? [3, 1.4] : [3, 1.8];
    var yariW = kw[0] / 2;
    var seritIci = yariW * Math.sqrt(Math.max(0, r * r - yariW * yariW)) +
      r * r * Math.asin(Math.min(1, yariW / r));
    return Math.PI * r * r + kw[0] * (r + kw[1]) - seritIci;
  }
  return Math.PI * r * r;
}

function pervane(p) {
  // Uretim motoruna kalibre (Faz E): govde SABIT (cap 14, boy 16 — mil
  // capina bagli degil); mil yuvasi yalniz govde boyunca; burun konisi
  // SABIT parca (govde ustune oturur, hacimler renderdan olculdu); dis ring
  // = ic capi pervane capinda, 1.8 duvarli, 10 mm boy, 0.4 pahli boru.
  var gobek = Math.PI * 49 * 16;
  var delik = pervane_delik_alani(p.mil_baglanti, p.mil_capi) * 16;
  var toplam = gobek - delik + p.kanat_sayisi * pervane_kanat_tablosu(p.cap);
  if (p.burun_konisi === "ogiv") toplam += 1796.2;
  if (p.burun_konisi === "parabolik") toplam += 1706.9;
  if (p.dis_ring === "var") {
    var r = p.cap / 2;
    toplam += Math.PI * ((r + 1.8) * (r + 1.8) - r * r) * 10 -
      2 * Math.PI * 0.16 * (2 * r + 1.8);
  }
  return toplam;
}
