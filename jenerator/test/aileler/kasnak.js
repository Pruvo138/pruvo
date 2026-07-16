function kasnak_profil_verisi(profil) {
  if (profil === "gt2_3mm") return [3, 0.381, 1.169, 2.310, 0.940, "round"];
  if (profil === "gt2_5mm") return [5, 0.5715, 1.968, 3.952, 1.636, "round"];
  if (profil === "htd_3mm") return [3, 0.381, 1.289, 2.270, 1.068, "round"];
  if (profil === "htd_5mm") return [5, 0.5715, 2.199, 3.781, 1.670, "round"];
  if (profil === "htd_8mm") return [8, 0.6858, 3.607, 6.603, 2.879, "round"];
  if (profil === "t2_5") return [2.5, 0, 0.700, 1.679, 1.058, "trap"];
  if (profil === "t5") return [5, 0, 1.190, 3.264, 1.898, "trap"];
  if (profil === "t10") return [10, 0.93, 2.500, 6.130, 3.758, "trap"];
  if (profil === "at5") return [5, 0, 1.190, 4.268, 2.574, "trap"];
  if (profil === "mxl") return [2.032, 0.254, 0.508, 1.321, 0.834, "trap"];
  if (profil === "xl") return [5.08, 0.254, 1.270, 3.051, 1.467, "trap"];
  if (profil === "l") return [9.525, 0.381, 1.905, 5.359, 3.439, "trap"];
  if (profil === "40dp") return [2.073, 0.1778, 0.457, 1.226, 0.655, "trap"];
  return [2, 0.254, 0.764, 1.494, 0.716, "round"];
}

function kasnak_konveks_kabuk(noktalar) {
  noktalar.sort(function (a, b) {
    return a[0] === b[0] ? a[1] - b[1] : a[0] - b[0];
  });
  var alt = [];
  var ust = [];
  var i;

  function kasnak_capraz(o, a, b) {
    return (a[0] - o[0]) * (b[1] - o[1]) -
      (a[1] - o[1]) * (b[0] - o[0]);
  }

  for (i = 0; i < noktalar.length; i++) {
    while (alt.length >= 2 && kasnak_capraz(alt[alt.length - 2], alt[alt.length - 1], noktalar[i]) <= 0) {
      alt.pop();
    }
    alt.push(noktalar[i]);
  }
  for (i = noktalar.length - 1; i >= 0; i--) {
    while (ust.length >= 2 && kasnak_capraz(ust[ust.length - 2], ust[ust.length - 1], noktalar[i]) <= 0) {
      ust.pop();
    }
    ust.push(noktalar[i]);
  }
  alt.pop();
  ust.pop();
  return alt.concat(ust);
}

function kasnak_oluk_alani(veri, disYaricap) {
  var derinlik = veri[2];
  var taban = veri[3];
  var tepe = veri[4];
  var noktalar = [];
  var i;

  if (veri[5] === "round") {
    noktalar.push([disYaricap, -taban / 2]);
    noktalar.push([disYaricap + 0.4, -taban / 2]);
    noktalar.push([disYaricap + 0.4, taban / 2]);
    noktalar.push([disYaricap, taban / 2]);
    var merkez = disYaricap - derinlik + tepe / 2;
    for (i = 0; i < 28; i++) {
      var aci = 2 * Math.PI * i / 28;
      noktalar.push([
        merkez + tepe * Math.cos(aci) / 2,
        tepe * Math.sin(aci) / 2
      ]);
    }
  } else {
    noktalar.push([disYaricap + 0.2, taban / 2]);
    noktalar.push([disYaricap + 0.2, -taban / 2]);
    noktalar.push([disYaricap - derinlik, -tepe / 2]);
    noktalar.push([disYaricap - derinlik, tepe / 2]);
  }

  var kabuk = kasnak_konveks_kabuk(noktalar);
  var sol = disYaricap - derinlik;
  var adim = derinlik / 256;
  var alan = 0;

  for (i = 0; i < 256; i++) {
    var x = sol + (i + 0.5) * adim;
    var ustY = 0;
    for (var j = 0; j < kabuk.length; j++) {
      var a = kabuk[j];
      var b = kabuk[(j + 1) % kabuk.length];
      if (x >= Math.min(a[0], b[0]) && x <= Math.max(a[0], b[0]) && a[0] !== b[0]) {
        var y = a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]);
        if (y > ustY) ustY = y;
      }
    }
    var daireY = Math.sqrt(Math.max(0, disYaricap * disYaricap - x * x));
    alan += 2 * Math.min(ustY, daireY) * adim;
  }
  return alan;
}

function kasnak_mil_alani(baglanti, cap) {
  var r = cap / 2;
  if (baglanti === "altigen") return Math.sqrt(3) * cap * cap / 2;
  if (baglanti === "d_lama") {
    var kesim = r * r * Math.acos(0.7) - 0.7 * r * r * Math.sqrt(1 - 0.49);
    return Math.PI * r * r - kesim;
  }
  if (baglanti === "kanalli") {
    var kanal = cap <= 5 ? 2 : (cap <= 8 ? 3 : 4);
    var y0 = Math.sqrt(Math.max(0, r * r - kanal * kanal / 4));
    var daireSeridi = kanal * y0 / 2 + r * r * Math.asin(kanal / (2 * r));
    return Math.PI * r * r + kanal * (r + kanal * 0.6) - daireSeridi;
  }
  return Math.PI * r * r;
}

function kasnak(p) {
  var veri = kasnak_profil_verisi(p.profil);
  var adim = veri[0];
  var hatFarki = veri[1];
  var disYaricap = p.dis_sayisi * adim / (2 * Math.PI) - hatFarki;
  var flansYaricap = disYaricap + Math.max(adim * 0.6, 1.2);
  var flansKalinligi = Math.max(adim * 0.5, 1.2);
  var flansSayisi = p.flans === "iki_taraf" ? 2 : (p.flans === "yok" ? 0 : 1);
  var olukAlani = kasnak_oluk_alani(veri, disYaricap);
  var disliAlan = Math.PI * disYaricap * disYaricap - p.dis_sayisi * olukAlani;
  var milAlani = kasnak_mil_alani(p.mil_baglanti, p.mil_capi);
  var toplamYukseklik = p.genislik + flansSayisi * flansKalinligi;

  return disliAlan * p.genislik +
    flansSayisi * Math.PI * flansYaricap * flansYaricap * flansKalinligi -
    milAlani * toplamYukseklik;
}
