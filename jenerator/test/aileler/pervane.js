function pervane_profil(cap, milCapi, istasyon) {
  var np = 48;
  var yaricap = cap / 2;
  var gobekYaricapi = (milCapi + 9) / 2;
  var kok = gobekYaricapi * 0.85;
  var r = kok + (yaricap - kok) * istasyon / 6;
  var oran = (r - kok) / (yaricap - kok);
  var kord = yaricap * (0.30 - 0.13 * oran);
  var beta = Math.min(Math.atan((cap * 0.9) / (2 * Math.PI * Math.max(r, 1))),
    58 * Math.PI / 180);
  var cb = Math.cos(-beta);
  var sb = Math.sin(-beta);
  var taban = (0.7 / 2) / Math.max(yaricap * 0.17, 0.1);
  var noktalar = [];
  var alt = [];
  var i;

  for (i = 0; i <= np; i++) {
    var x = 0.5 * (1 - Math.cos(Math.PI * i / np));
    var yt = Math.max(5 * 0.12 * (0.2969 * Math.sqrt(x) - 0.1260 * x -
      0.3516 * x * x + 0.2843 * x * x * x - 0.1036 * x * x * x * x), taban);
    var yc = x < 0.4 ? 0.02 / 0.16 * (0.8 * x - x * x) :
      0.02 / 0.36 * (0.2 + 0.8 * x - x * x);
    var dyc = x < 0.4 ? 0.02 / 0.16 * (0.8 - 2 * x) :
      0.02 / 0.36 * (0.8 - 2 * x);
    var th = Math.atan(dyc);
    var ux = x - yt * Math.sin(th);
    var uy = yc + yt * Math.cos(th);
    var lx = x + yt * Math.sin(th);
    var ly = yc - yt * Math.cos(th);
    var uKord = (ux - 0.25) * kord;
    var uKal = uy * kord;
    var lKord = (lx - 0.25) * kord;
    var lKal = ly * kord;
    noktalar.push([uKord * cb - uKal * sb, uKord * sb + uKal * cb]);
    alt.push([lKord * cb - lKal * sb, lKord * sb + lKal * cb]);
  }
  for (i = np; i >= 0; i--) noktalar.push(alt[i]);
  return noktalar;
}

function pervane_ara_profil(a, b, t) {
  var sonuc = [];
  for (var i = 0; i < a.length; i++) {
    sonuc.push([a[i][0] + (b[i][0] - a[i][0]) * t,
      a[i][1] + (b[i][1] - a[i][1]) * t]);
  }
  return sonuc;
}

function pervane_cokgen_alani(noktalar) {
  var ikiAlan = 0;
  for (var i = 0; i < noktalar.length; i++) {
    var j = (i + 1) % noktalar.length;
    ikiAlan += noktalar[i][0] * noktalar[j][1] - noktalar[j][0] * noktalar[i][1];
  }
  return Math.abs(ikiAlan) / 2;
}

function pervane_kirp(noktalar, eksen, sinir, kucukTaraf) {
  var sonuc = [];
  for (var i = 0; i < noktalar.length; i++) {
    var a = noktalar[i];
    var b = noktalar[(i + 1) % noktalar.length];
    var aIc = kucukTaraf ? a[eksen] <= sinir : a[eksen] >= sinir;
    var bIc = kucukTaraf ? b[eksen] <= sinir : b[eksen] >= sinir;
    if (aIc) sonuc.push(a);
    if (aIc !== bIc) {
      var t = (sinir - a[eksen]) / (b[eksen] - a[eksen]);
      sonuc.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
    }
  }
  return sonuc;
}

function pervane_kanat_hacmi(cap, milCapi) {
  var yaricap = cap / 2;
  var gobekYaricapi = (milCapi + 9) / 2;
  var kok = gobekYaricapi * 0.85;
  var dr = (yaricap - kok) / 6;
  var profiller = [];
  var toplam = 0;
  var i;
  for (i = 0; i <= 6; i++) profiller.push(pervane_profil(cap, milCapi, i));
  for (i = 0; i < 6; i++) {
    var orta = pervane_ara_profil(profiller[i], profiller[i + 1], 0.5);
    toplam += dr * (pervane_cokgen_alani(profiller[i]) +
      4 * pervane_cokgen_alani(orta) + pervane_cokgen_alani(profiller[i + 1])) / 6;
  }

  // Kanadın göbek silindiri içinde kalan kök parçasını kesit kırpmasıyla çıkar.
  var adimSayisi = 48;
  var ortusen = 0;
  for (i = 0; i < adimSayisi; i++) {
    var r = kok + (gobekYaricapi - kok) * (i + 0.5) / adimSayisi;
    var yer = (r - kok) / dr;
    var bolum = Math.min(5, Math.max(0, Math.floor(yer)));
    var t = yer - bolum;
    var kesit = pervane_ara_profil(profiller[bolum], profiller[bolum + 1], t);
    var ySinir = Math.sqrt(Math.max(0, gobekYaricapi * gobekYaricapi - r * r));
    kesit = pervane_kirp(kesit, 0, ySinir, true);
    kesit = pervane_kirp(kesit, 0, -ySinir, false);
    kesit = pervane_kirp(kesit, 1, 8, true);
    kesit = pervane_kirp(kesit, 1, -8, false);
    ortusen += pervane_cokgen_alani(kesit);
  }
  ortusen *= (gobekYaricapi - kok) / adimSayisi;
  return toplam - ortusen;
}

function pervane_delik_sinir(baglanti, cap, aci) {
  var r = cap / 2;
  if (baglanti === "altigen") {
    var donem = Math.PI / 3;
    var delta = ((aci + Math.PI / 6) % donem + donem) % donem - Math.PI / 6;
    return r / Math.cos(delta);
  }
  if (baglanti === "d_lama") {
    var ca = Math.cos(aci);
    return ca > 0.7 ? 0.7 * r / ca : r;
  }
  if (baglanti === "kanalli" && Math.sin(aci) > 0) {
    var kanal = cap <= 5 ? 2 : 3;
    var caMutlak = Math.abs(Math.cos(aci));
    var xSinir = caMutlak < 1e-9 ? Infinity : kanal / (2 * caMutlak);
    var ySinir = (r + kanal) / Math.sin(aci);
    return Math.max(r, Math.min(xSinir, ySinir));
  }
  return r;
}

function pervane_delik_alani(baglanti, cap, disYaricap) {
  var n = 96;
  var toplam = 0;
  for (var i = 0; i < n; i++) {
    var aci = 2 * Math.PI * (i + 0.5) / n;
    var sinir = Math.min(disYaricap, pervane_delik_sinir(baglanti, cap, aci));
    toplam += sinir * sinir;
  }
  return Math.PI * toplam / n;
}

function pervane_spinner_hacmi(tip, milBaglanti, milCapi, gobekYaricapi) {
  if (tip === "yok") return 0;
  var yukseklik = gobekYaricapi * 2 * 0.9;
  var toplam = 0;
  var delik = 0;
  for (var i = 0; i < 12; i++) {
    var t0 = i / 12;
    var t1 = (i + 1) / 12;
    var r0 = tip === "ogiv" ? gobekYaricapi * Math.sqrt(1 - t0 * t0) :
      gobekYaricapi * (1 - t0 * t0);
    var r1 = tip === "ogiv" ? gobekYaricapi * Math.sqrt(1 - t1 * t1) :
      gobekYaricapi * (1 - t1 * t1);
    var ic0 = gobekYaricapi * (1 - t0);
    var ic1 = gobekYaricapi * (1 - t1);
    var dz = yukseklik / 12;
    // SCAD profil çokgeni eğriyi başlangıç-bitiş kirişiyle kapatır.
    toplam += Math.PI * dz * (r0 * r0 + r0 * r1 + r1 * r1 -
      ic0 * ic0 - ic0 * ic1 - ic1 * ic1) / 3;
    for (var j = 0; j < 4; j++) {
      var u = (j + 0.5) / 4;
      var rAra = r0 + (r1 - r0) * u;
      var icAra = ic0 + (ic1 - ic0) * u;
      delik += (pervane_delik_alani(milBaglanti, milCapi, rAra) -
        pervane_delik_alani(milBaglanti, milCapi, icAra)) * dz / 4;
    }
  }
  return toplam - delik;
}

function pervane(p) {
  var gobekYaricapi = (p.mil_capi + 9) / 2;
  var gobek = Math.PI * gobekYaricapi * gobekYaricapi * 16;
  var delik = pervane_delik_alani(p.mil_baglanti, p.mil_capi, Infinity) * 16;
  var toplam = gobek - delik + p.kanat_sayisi * pervane_kanat_hacmi(p.cap, p.mil_capi);
  toplam += pervane_spinner_hacmi(p.burun_konisi, p.mil_baglanti,
    p.mil_capi, gobekYaricapi);
  if (p.dis_ring === "var") {
    var yaricap = p.cap / 2;
    var ringEni = Math.max(yaricap * 0.17 * 0.5, 2);
    toplam += 2 * Math.PI * (yaricap + ringEni / 2) * ringEni * 16 * 0.6;
  }
  return toplam;
}
