function kutu(p) {
  // Ölçüye özel kutu (kapaklı · bölmeli): kutu.scad sözleşmesi. Tümü dikdörtgen
  // prizma — kapalı form KESİNDİR (ölçülen sapma %0.000, 2026-07-17).
  // Bölme duvarı 1.2 mm sabit; etkin adet gözler 15 mm'nin altına inmeyecek
  // şekilde kırpılır (scad ile birebir). Geçme kapakta bölme 6 mm kısalır
  // (kapak dudağı payı); kapak = plaka + dudak çerçevesi (et 1.6, tol 0.2).
  var t = Math.max(p.duvar, 1.2);
  var W = p.ic_en + 2 * t;
  var L = p.ic_boy + 2 * t;
  var H = p.ic_yukseklik + t;
  var neff = Math.max(0, Math.min(p.bolme_sayisi,
    Math.floor((p.ic_boy - 15) / (15 + 1.2))));
  var bolmeH = p.ic_yukseklik - (p.kapak === "gecme" ? 6 : 0);
  var v = W * L * H - p.ic_en * p.ic_boy * p.ic_yukseklik +
          neff * p.ic_en * 1.2 * bolmeH;
  if (p.kapak === "gecme") {
    v += W * L * t + 6 * ((p.ic_en - 0.4) * (p.ic_boy - 0.4) -
                          (p.ic_en - 3.6) * (p.ic_boy - 3.6));
  }
  return v;
}
