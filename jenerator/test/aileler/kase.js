function kase(p) {
  // Uretim motoruna kalibre (Faz E): taban, "PRUVO" yazisinin OLCULEN
  // textmetrics kutusundan turer (genislik 4.78806 x yazi, satir 1.27767 x
  // yazi), dolgu TOPLAM eklenir (+2 kenar payi), taban 15x10 alt sinirli
  // kesik piramit (ust-alt fark 4, yukseklik 8). Sabitler motor renderlarina
  // 12 sette +-2 mm3 oturdu.
  var en2 = Math.max(15, 4.78806 * p.yazi_boyutu + p.dolgu + 2);
  var boy2 = Math.max(15, 1.27767 * p.yazi_boyutu + p.dolgu + 2);
  if (p.bicim !== "dikdortgen") {
    // kare/yuvarlak: uretim motorunda karsiligi YOK (taban hep yazi
    // kutusundan dikdortgen) — fiyat icin dikdortgen esdegeri kullanilir,
    // uretilebilirlik karari mimar/Okan'da.
    var kenar = Math.max(en2, boy2);
    en2 = kenar;
    boy2 = kenar;
  }
  var en1 = Math.max(10, en2 - 4);
  var boy1 = Math.max(10, boy2 - 4);
  var yukseklik = 8;
  var prizma = yukseklik / 6 * (en1 * boy1 + en2 * boy2 +
    (en1 + en2) * (boy1 + boy2));

  // Dis yuvasi (sap vidasi icin her govdede acilir) + ust kenar pahi.
  var disYuvasi = 306.9;
  var kenarPahi = 0.55 * 2 * (en2 + boy2);

  // Kabartma yazi: olculen 2B glif alani 2.1232 x yazi^2.
  var rolyef = 2.1232 * p.yazi_boyutu * p.yazi_boyutu * p.kabartma_derinligi;

  var toplam = prizma - disYuvasi - kenarPahi + rolyef;

  if (p.sap === "sapli") {
    // Motor sapi parametreden bagimsiz TEK sabit parcadir (ayri basilir,
    // vidalanir); hacmi renderdan olculdu.
    toplam += 10337.2;
  }

  return toplam;
}
