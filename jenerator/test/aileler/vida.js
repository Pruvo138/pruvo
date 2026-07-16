function vida_dis_kesit_alani(cap, adim) {
  var h = adim * Math.sqrt(3) / 2;
  var temelSapma = -(15 + 11 * adim) / 1000;
  var capToleransi = (180 * Math.pow(adim, 2 / 3) - 3.15 / Math.sqrt(adim)) / 1000;
  var aralikOrtasi = Math.sqrt(2.8 * 5.6);
  var hatveToleransi = 90 * Math.pow(adim, 0.4) * Math.pow(aralikOrtasi, 0.1) / 1000;
  var enAzDuzluk = adim / 8;
  var aci = (60 - Math.acos(1 - hatveToleransi / (4 * enAzDuzluk)) * 180 / Math.PI) * Math.PI / 180;
  var enCokDuzluk = h / 4 - enAzDuzluk * (1 - Math.cos(aci)) + hatveToleransi / 2;
  var buyukCap = cap + temelSapma - capToleransi / 2;
  var hatveCapi = cap - 3 * h / 4 + temelSapma - hatveToleransi / 2;
  var kucukCap = cap - 2 * h + enAzDuzluk + enCokDuzluk + temelSapma;
  var derinlik = (buyukCap - kucukCap) / (2 * adim);
  var tepeOrani = 0.5 - (buyukCap - hatveCapi) / (Math.sqrt(3) * adim);
  var dipOrani = 1 - tepeOrani - 2 * derinlik / Math.sqrt(3);
  var disOrani = 2 * derinlik / Math.sqrt(3);
  var yariCap = buyukCap / 2;
  var radyalDerinlik = adim * derinlik;
  var ortalamaYariCapKare =
    dipOrani * Math.pow(yariCap - radyalDerinlik, 2) +
    tepeOrani * yariCap * yariCap +
    disOrani * (yariCap * yariCap - yariCap * radyalDerinlik + radyalDerinlik * radyalDerinlik / 3);

  // BOSL2'nin helisel VNF süpürmesinin kapalı-form kesite göre küçük farkı.
  return Math.PI * ortalamaYariCapKare * 0.9996837955691371;
}

// [cap, değer] tablosunda doğrusal enterpolasyon; uçların dışı uca sabitlenir.
// Tablolar üretim motorunun standart M ölçülerinde ölçülmüş STL hacimlerinden
// (jenerator/test/vida-referans-uret.py fixture'ı); ara/yarım ölçüler üretim
// eşleminde yok, fiyatları komşu ölçülerden enterpolasyonla türetilir.
function vida_tablo(tablo, cap) {
  if (cap <= tablo[0][0]) return tablo[0][1];
  for (var i = 1; i < tablo.length; i++) {
    if (cap <= tablo[i][0]) {
      var a = tablo[i - 1], b = tablo[i];
      return a[1] + (b[1] - a[1]) * (cap - a[0]) / (b[0] - a[0]);
    }
  }
  return tablo[tablo.length - 1][1];
}

// ISO kaba diş adımı (üretim motoru Spec/Pitch tablosuyla aynı).
function vida_adim(cap) {
  return vida_tablo([[3, 0.5], [4, 0.7], [5, 0.8], [6, 1], [8, 1.25], [10, 1.5],
    [12, 1.75], [14, 2], [16, 2], [18, 2.5], [20, 2.5]], cap);
}

function vida(p) {
  if (p.urun_tipi === "pul") {
    // Üretim motoru pul ölçülerini ISO tablosundan alır; tolerans hacme etkimez.
    return vida_tablo([[3, 15.220877], [4, 39.275085], [5, 56.473602],
      [6, 129.4657], [8, 232.9843], [10, 455.0458], [12, 798.9804],
      [14, 1097.3710], [16, 1439.3425], [18, 1872.7943], [20, 2186.1044]], p.cap);
  }

  if (p.urun_tipi === "somun") {
    return vida_tablo([[3, 41.328161], [4, 88.017602], [5, 157.0542],
      [6, 288.4025], [8, 630.2322], [10, 1170.7777], [12, 1777.5389],
      [14, 2889.8934], [16, 4368.3563], [18, 5932.0266], [20, 8352.0079]], p.cap);
  }

  if (p.urun_tipi === "mil") {
    // Dişli mil kesiti cıvatadan dolgun (toleranssız tam profil) — ölçülen eğim.
    return vida_tablo([[3, 5.731007], [4, 10.087264], [5, 16.071114],
      [6, 22.950125], [8, 41.352869], [10, 65.132137], [12, 94.288675],
      [14, 128.8242], [16, 172.1133], [18, 214.0304], [20, 268.9270]], p.cap) *
      p.boy +
      vida_tablo([[3, -0.393487], [4, -1.025488], [5, -1.667223],
        [6, -3.141889], [8, -6.529187], [10, -11.772693], [12, -19.226843],
        [14, -29.455120], [16, -33.883159], [18, -59.345327],
        [20, -66.178036]], p.cap);
  }

  // Cıvata: 6g diş kesiti (kapalı form, ölçülen eğime <=%0.09) × boy + kafa.
  // Altıgen kafa üretim motorunda M5'ten başlar; M3/M4 üretilemez (mimar
  // raporunda) — fiyat sürekliliği için kafa M5'ten cap^3 ile küçültülür.
  var kafa = p.cap >= 5 ?
    vida_tablo([[5, 187.9174], [6, 334.3135], [8, 749.5829], [10, 1550.3620],
      [12, 2260.9221], [14, 3558.6445], [16, 4820.3839], [18, 7001.0908],
      [20, 9415.1648]], p.cap) :
    187.9174 * Math.pow(p.cap / 5, 3);
  return vida_dis_kesit_alani(p.cap, vida_adim(p.cap)) * p.boy + kafa;
}
