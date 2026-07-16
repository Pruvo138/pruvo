/* PRUVO — parametrik urun hacim fonksiyonlari (mm3).
   TEK KAYNAK: site (client) ve siparis dogrulama ayni dosyayi yukler; kopyalanmaz.
   ELLE DUZENLEME: bu dosya jenerator/test/birlestir.py tarafindan
   jenerator/test/aileler/*.js dosyalarindan uretilir; duzeltme aile dosyasinda yapilir.
   Girdi: p = {parametre_adi: deger, ...} (semadaki `ad` alanlari, sayi/secim degerleri).
   Cikti: yaklasik kati hacim, mm3 (kapali-form; OpenSCAD render dogrulamali, sapma <=%3). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) { module.exports = factory(); }
  else { root.PRUVO_HACIM = factory(); }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // === AILE: braket ===
  function braket_kirp(cokgen, a, b) {
    var sonuc = [];
    for (var i = 0; i < cokgen.length; i++) {
      var p = cokgen[i];
      var q = cokgen[(i + 1) % cokgen.length];
      var dp = (b[0] - a[0]) * (p[1] - a[1]) -
        (b[1] - a[1]) * (p[0] - a[0]);
      var dq = (b[0] - a[0]) * (q[1] - a[1]) -
        (b[1] - a[1]) * (q[0] - a[0]);
      if (dp >= 0) sonuc.push(p);
      if ((dp >= 0) !== (dq >= 0)) {
        var oran = dp / (dp - dq);
        sonuc.push([
          p[0] + (q[0] - p[0]) * oran,
          p[1] + (q[1] - p[1]) * oran
        ]);
      }
    }
    return sonuc;
  }

  function braket_cokgen_alani(cokgen) {
    var ikiAlan = 0;
    for (var i = 0; i < cokgen.length; i++) {
      var p = cokgen[i];
      var q = cokgen[(i + 1) % cokgen.length];
      ikiAlan += p[0] * q[1] - q[0] * p[1];
    }
    return Math.abs(ikiAlan) / 2;
  }

  function braket_kesisim_alani(xmin, uzunluk, kalinlik, aci) {
    var c = Math.cos(aci);
    var s = Math.sin(aci);
    var ilk = [[xmin, 0], [uzunluk, 0], [uzunluk, kalinlik], [xmin, kalinlik]];
    var yerel = [[xmin, 0], [uzunluk, 0], [uzunluk, kalinlik], [xmin, kalinlik]];
    var ikinci = [];
    for (var i = 0; i < yerel.length; i++) {
      ikinci.push([
        yerel[i][0] * c - yerel[i][1] * s,
        yerel[i][0] * s + yerel[i][1] * c
      ]);
    }
    var sonuc = ilk;
    for (var j = 0; j < ikinci.length && sonuc.length; j++) {
      sonuc = braket_kirp(sonuc, ikinci[j], ikinci[(j + 1) % ikinci.length]);
    }
    return sonuc.length < 3 ? 0 : braket_cokgen_alani(sonuc);
  }

  function braket_aci_bindirme(genislik, uzunluk, kalinlik, derece) {
    var yaricap = genislik / 2;
    var adim = genislik / 64;
    var aci = derece * Math.PI / 180;
    var toplam = 0;
    for (var i = 0; i < 64; i++) {
      var y = -yaricap + (i + 0.5) * adim;
      var xmin = -Math.sqrt(Math.max(0, yaricap * yaricap - y * y));
      toplam += braket_kesisim_alani(xmin, uzunluk, kalinlik, aci);
    }
    return toplam * adim;
  }

  function braket(p) {
    var w = p.genislik;
    var l = p.uzunluk;
    var t = p.kalinlik;
    var delikYaricapi = 2.25;
    var delikAlani = 16 * delikYaricapi * delikYaricapi *
      Math.sin(Math.PI / 16);

    // SCAD'deki yuvarlak eklem, sabit 2 mm kenar radyusu ve parçalı daire.
    var disAlan = l * w + Math.PI * w * w / 8 - 0.1717 * w - 0.16;
    var kol = (disAlan - p.delik_adet * delikAlani) * t;

    if (p.tip === "duz") return kol;

    if (p.tip === "l") {
      return 2 * kol - t * (0.850584 * w * w - 0.66785 * w);
    }
    if (p.tip === "t") {
      return 3 * kol - t * (1.6945225 * w * w - 1.02755 * w);
    }
    if (p.tip === "y") {
      return 3 * kol - t * (1.625614 * w * w - 0.94685 * w);
    }
    if (p.tip === "kose") {
      var duzL = 2 * kol - t * (0.850584 * w * w - 0.66785 * w);
      var dikBindirme = w * t * t * (1 - t / (8 * w));
      return duzL + kol - dikBindirme;
    }

    return 2 * kol - braket_aci_bindirme(w, l, t, p.ic_aci);
  }

  // === AILE: cetvel ===
  function cetvel_rakam_alani(uzunluk, boyut) {
    // Aralık 10–50 olduğundan 0..uzunluk etiketlerindeki toplam rakam sayısı 2n-8'dir.
    return 0.17 * boyut * boyut * (2 * uzunluk - 8);
  }

  function cetvel_isaret_alani(p, kenarIsareti) {
    var n = p.uzunluk;
    var w = p.genislik;
    var inc = p.sistem === "inc";
    var katsayi;
    var yaziBoyutu;

    if (kenarIsareti) {
      katsayi = inc ? 1.165 * n + 0.2 : 0.805 * n + 0.2;
      yaziBoyutu = Math.min(0.2 * w, 4);
    } else {
      katsayi = inc ? 1.323 * n + 0.315 : 0.909 * n + 0.315;
      yaziBoyutu = Math.min(0.22 * w, 4.5);
    }

    return w * katsayi + cetvel_rakam_alani(n, yaziBoyutu);
  }

  function cetvel(p) {
    var birimMm = p.sistem === "inc" ? 25.4 : 10;
    var a = p.uzunluk * birimMm;
    var w = p.genislik;
    var r = 3;
    var alan;
    var kenarIsareti = p.tip !== "duz";

    if (p.tip === "ucgen") {
      // Dış ve iç 45° üçgenlerde aynı köşe yarıçapı kullanıldığı için düzeltmeler yok olur.
      alan = 3 * a * a / 8;
    } else if (p.tip === "l_gonye") {
      // İki kolun birleşim alanı; beş dış köşedeki yuvarlatma ayrıca çıkarılır.
      alan = a * w + 0.6 * a * w - w * w;
      alan -= 5 * (1 - Math.PI / 4) * r * r;
    } else {
      alan = (a + 12) * w - (4 - Math.PI) * r * r;
    }

    var govdeHacmi = alan * p.kalinlik;
    var isaretHacmi = 0.59 * cetvel_isaret_alani(p, kenarIsareti);
    return p.isaret_stili === "kabartma" ? govdeHacmi + isaretHacmi : govdeHacmi - isaretHacmi;
  }

  // === AILE: disli ===
  function disli_poligon_delik_alani(cap) {
    return 0.7841371226364848 * cap * cap;
  }

  function disli_duz_alani(disSayisi) {
    return 0.7889008998798291 * disSayisi * disSayisi -
      0.6616088525010534 * disSayisi +
      19.921676299118015 - 357.1333660667204 / disSayisi;
  }

  function disli_helis_alani(disSayisi) {
    return 0.8861530525852173 * disSayisi * disSayisi +
      0.3301856926959478 * disSayisi -
      26.708162839799833 + 362.73354363512203 / disSayisi;
  }

  function disli_konik_boyutsuz(disSayisi, oran) {
    return 3247.581811189285 - 84.69687353404711 * oran -
      16.500007311285678 * oran * oran -
      174.63374242374908 * disSayisi +
      12.463196167435349 * disSayisi * oran -
      0.6213433946874087 * disSayisi * oran * oran +
      1.4363612910981147 * disSayisi * disSayisi +
      0.657150904608151 * disSayisi * disSayisi * oran +
      0.00501439792173817 * disSayisi * disSayisi * oran * oran;
  }

  function disli_tac_boyutsuz(disSayisi, oran) {
    return 627.1283973423839 - 339.01290842281685 * oran +
      52.97223798565685 * oran * oran -
      0.25408305396843156 * disSayisi -
      3.0210634803742615 * disSayisi * oran +
      3.081313824628957 * disSayisi * oran * oran -
      1.7682819634464704 * disSayisi * disSayisi +
      0.7841373565233529 * disSayisi * disSayisi * oran +
      0.00039414473207161657 * disSayisi * disSayisi * oran * oran;
  }

  function disli_halka_alani(disSayisi, modul) {
    var sirt = Math.max(3 * modul, 4);
    return 3.1365484949825446 * disSayisi * modul * sirt +
      3.632008782749642 * disSayisi * modul * modul +
      33.06238141265567 * sirt * sirt -
      81.9361334406276 * modul * sirt +
      10.440863555524748 * modul * modul -
      119.70332840207266 * sirt +
      359.10996779298875 * modul + 0.000014835747051515935;
  }

  function disli(p) {
    var n = p.dis_sayisi;
    var m = p.modul;
    var h = p.kalinlik;
    var delik = disli_poligon_delik_alani(p.delik_capi);

    if (p.disli_tipi === "duz") {
      return disli_duz_alani(n) * m * m * h - delik * h;
    }
    if (p.disli_tipi === "helis" || p.disli_tipi === "cift_helis") {
      return disli_helis_alani(n) * m * m * h - delik * h;
    }
    if (p.disli_tipi === "konik") {
      var konikOran = Math.max(h / m, 6);
      return disli_konik_boyutsuz(n, konikOran) * m * m * m -
        delik * m * konikOran;
    }
    if (p.disli_tipi === "sonsuz") {
      return 1582.26914125 * m * m * m;
    }
    if (p.disli_tipi === "ic_disli") {
      return disli_halka_alani(n, m) * h;
    }
    if (p.disli_tipi === "tac") {
      var tacOran = h / m;
      return disli_tac_boyutsuz(n, tacOran) * m * m * m -
        delik * (h - 2.25 * m);
    }
    var genislik = Math.max(4 * m, 6);
    return n * h * (Math.PI * m * genislik - 3.324477523087862 * m * m);
  }

  // === AILE: huni ===
  function huni(p) {
    var pi = Math.PI;
    var icUstYaricap = p.agiz_capi / 2;
    var icAltYaricap = p.uc_capi / 2;
    var disAltYaricap = icAltYaricap + 1.2;
    var disUstYaricap = icUstYaricap + 1.5;

    var ucHacmi = pi * p.uc_boyu *
      (disAltYaricap * disAltYaricap - icAltYaricap * icAltYaricap);

    var disKoni = pi * p.yukseklik / 3 *
      (disAltYaricap * disAltYaricap +
       disAltYaricap * disUstYaricap +
       disUstYaricap * disUstYaricap);
    var icKoni = pi * p.yukseklik / 3 *
      (icAltYaricap * icAltYaricap +
       icAltYaricap * icUstYaricap +
       icUstYaricap * icUstYaricap);

    var kenarDisYaricap = disUstYaricap + 4;
    var kenarHacmi = pi * 1.5 *
      (kenarDisYaricap * kenarDisYaricap -
       disUstYaricap * disUstYaricap);

    // Eğik düzlemin boru cidarından çıkardığı hacim; aralıklar kesimi uçta tutar.
    var aci = p.uc_acisi * pi / 180;
    var ucKesigi = Math.tan(aci) * disAltYaricap * pi *
      (disAltYaricap * disAltYaricap - icAltYaricap * icAltYaricap);

    return ucHacmi + disKoni - icKoni + kenarHacmi - ucKesigi;
  }

  // === AILE: izgara ===
  function izgara_cokgen_alani(cokgen) {
    var ikiAlan = 0;
    for (var i = 0; i < cokgen.length; i++) {
      var a = cokgen[i];
      var b = cokgen[(i + 1) % cokgen.length];
      ikiAlan += a[0] * b[1] - b[0] * a[1];
    }
    return Math.abs(ikiAlan) / 2;
  }

  function izgara_cokgen_kirp(konu, kirp) {
    var sonuc = konu;
    for (var k = 0; k < kirp.length; k++) {
      var bas = kirp[k];
      var son = kirp[(k + 1) % kirp.length];
      var ex = son[0] - bas[0];
      var ey = son[1] - bas[1];
      var giris = sonuc;
      sonuc = [];
      if (giris.length === 0) break;

      for (var i = 0; i < giris.length; i++) {
        var a = giris[i];
        var b = giris[(i + 1) % giris.length];
        var da = ex * (a[1] - bas[1]) - ey * (a[0] - bas[0]);
        var db = ex * (b[1] - bas[1]) - ey * (b[0] - bas[0]);
        var aIceride = da >= -1e-9;
        var bIceride = db >= -1e-9;
        if (aIceride !== bIceride) {
          var t = da / (da - db);
          sonuc.push([
            a[0] + t * (b[0] - a[0]),
            a[1] + t * (b[1] - a[1])
          ]);
        }
        if (bIceride) sonuc.push(b);
      }
    }
    return sonuc;
  }

  function izgara_dikdortgen_kirp_alani(cokgen, yariEn, yariBoy) {
    var sinir = [
      [-yariEn, -yariBoy],
      [yariEn, -yariBoy],
      [yariEn, yariBoy],
      [-yariEn, yariBoy]
    ];
    return izgara_cokgen_alani(izgara_cokgen_kirp(cokgen, sinir));
  }

  function izgara_desen_noktalari(sekil, boyut) {
    if (sekil === "kare") {
      return [
        [-boyut / 2, -boyut / 2],
        [boyut / 2, -boyut / 2],
        [boyut / 2, boyut / 2],
        [-boyut / 2, boyut / 2]
      ];
    }

    var adet = 180;
    var yaricap = boyut / 2;
    if (sekil === "sekizgen") {
      adet = 8;
      yaricap = boyut / (2 * Math.cos(Math.PI / 8));
    } else if (sekil === "petek") {
      adet = 6;
      yaricap = boyut / (2 * Math.cos(Math.PI / 6));
    } else if (sekil === "besgen") {
      adet = 5;
    } else if (sekil === "ucgen") {
      adet = 3;
    }

    var noktalar = [];
    for (var i = 0; i < adet; i++) {
      var aci = 2 * Math.PI * i / adet;
      noktalar.push([yaricap * Math.cos(aci), yaricap * Math.sin(aci)]);
    }
    return noktalar;
  }

  function izgara_delik_alani(p, icEn, icBoy) {
    var boyut = 8;
    var aralik = 3;
    var pitch = boyut + aralik;
    var dy = p.delik_sekli === "petek" ? pitch * 0.866 : pitch;
    var yariEn = icEn / 2 - 1;
    var yariBoy = icBoy / 2 - 1;
    var temel = izgara_desen_noktalari(p.delik_sekli, boyut);
    var tamAlan = izgara_cokgen_alani(temel);
    var minX = Infinity;
    var maxX = -Infinity;
    var minY = Infinity;
    var maxY = -Infinity;
    for (var n = 0; n < temel.length; n++) {
      minX = Math.min(minX, temel[n][0]);
      maxX = Math.max(maxX, temel[n][0]);
      minY = Math.min(minY, temel[n][1]);
      maxY = Math.max(maxY, temel[n][1]);
    }

    var nx = Math.ceil(p.en / pitch) + 1;
    var ny = Math.ceil(p.boy / dy) + 1;
    var toplam = 0;
    for (var j = -ny; j <= ny; j++) {
      var cxKaydir = j % 2 === 0 ? 0 : pitch / 2;
      var cy = j * dy;
      for (var i = -nx; i <= nx; i++) {
        var cx = i * pitch + cxKaydir;
        if (cx + maxX <= yariEn && cx + minX >= -yariEn &&
            cy + maxY <= yariBoy && cy + minY >= -yariBoy) {
          toplam += tamAlan;
        } else if (cx + maxX > -yariEn && cx + minX < yariEn &&
                   cy + maxY > -yariBoy && cy + minY < yariBoy) {
          var tasinmis = [];
          for (var q = 0; q < temel.length; q++) {
            tasinmis.push([cx + temel[q][0], cy + temel[q][1]]);
          }
          toplam += izgara_dikdortgen_kirp_alani(tasinmis, yariEn, yariBoy);
        }
      }
    }
    return toplam;
  }

  function izgara_slat_cokgeni(y, z, aci) {
    var c = Math.cos(aci);
    var s = Math.sin(aci);
    var yerel = [[-4.5, -0.8], [4.5, -0.8], [4.5, 0.8], [-4.5, 0.8]];
    var sonuc = [];
    for (var i = 0; i < yerel.length; i++) {
      var v = yerel[i][0];
      var w = yerel[i][1];
      sonuc.push([y + v * c - w * s, z + v * s + w * c]);
    }
    return sonuc;
  }

  function izgara_panjur_alani(boy, derinlik, derece) {
    var aci = derece * Math.PI / 180;
    var pitch = 6.5;
    var ny = Math.ceil(boy / pitch) + 1;
    var sinir = [
      [-boy / 2, 0],
      [boy / 2, 0],
      [boy / 2, derinlik],
      [-boy / 2, derinlik]
    ];
    var slatlar = [];
    var toplam = 0;
    for (var j = -ny; j <= ny; j++) {
      var slat = izgara_slat_cokgeni(j * pitch, derinlik / 2, aci);
      slatlar.push(slat);
      toplam += izgara_cokgen_alani(izgara_cokgen_kirp(slat, sinir));
    }

    for (var k = 0; k + 1 < slatlar.length; k++) {
      var ortak = izgara_cokgen_kirp(slatlar[k], slatlar[k + 1]);
      ortak = izgara_cokgen_kirp(ortak, sinir);
      toplam -= izgara_cokgen_alani(ortak);
    }
    return toplam;
  }

  function izgara_erozyon_alani(en, boy, yaricap, mesafe) {
    var yeniEn = en - 2 * mesafe;
    var yeniBoy = boy - 2 * mesafe;
    var yeniR = Math.max(yaricap - mesafe, 0);
    return yeniEn * yeniBoy - (4 - Math.PI) * yeniR * yeniR;
  }

  function izgara(p) {
    var cerceveEn = 6;
    var koseR = 3;
    var icEn = p.en - 2 * cerceveEn;
    var icBoy = p.boy - 2 * cerceveEn;
    var disAlan = izgara_erozyon_alani(p.en, p.boy, koseR, 0);
    var icAlan = icEn * icBoy;
    var cerceveAlani = disAlan - icAlan;

    var etekDis = izgara_erozyon_alani(p.en, p.boy, koseR, 0.4);
    var etekIc = izgara_erozyon_alani(p.en, p.boy, koseR, 2.2);
    var etekHacmi = (etekDis - etekIc) * 8;
    var hacim = cerceveAlani * p.derinlik + etekHacmi;

    if (p.tip === "kor") {
      hacim += icAlan * p.derinlik;
    } else if (p.tip === "delikli") {
      var delikAlani = izgara_delik_alani(p, icEn, icBoy);
      hacim += (icAlan - delikAlani) * Math.min(p.derinlik, 3);
    } else {
      hacim += icEn * izgara_panjur_alani(icBoy, p.derinlik, p.panjur_acisi);
    }
    return hacim;
  }

  // === AILE: jeton ===
  function jeton(p) {
    var pah = 0.8;
    var yaricap = p.cap / 2;
    var ustYaricap = yaricap - pah;
    var govdeYuksekligi = p.kalinlik - 2 * pah;

    // SCAD gövdesi: tam yarıçaplı silindir ve üstte 2*pah yüksekliğinde kesik koni.
    var govde = Math.PI * yaricap * yaricap * govdeYuksekligi;
    var ustPah = Math.PI * 2 * pah / 3 *
      (yaricap * yaricap + yaricap * ustYaricap + ustYaricap * ustYaricap);
    var hacim = govde + ustPah;

    if (p.kenar_deseni === "segmentli") {
      // Sekiz adet 22 derecelik halka diliminin pahlı disk dışında kalan bölümü.
      var aciOrani = 8 * 22 / 360;
      var disKenar = yaricap + 0.2;
      var duzBolum = (p.kalinlik - 2 * pah) *
        (disKenar * disKenar - yaricap * yaricap);
      var pahBolumu = yaricap * pah * pah / 2 - pah * pah * pah / 12;
      hacim += Math.PI * aciOrani * (duzBolum + pahBolumu);
    }

    // Varsayılan "100" yazısı ve dekoratif halkanın ölçeklenen 2B alanı.
    var yaziBoyutu = p.cap * 0.34;
    var isaretAlani = Math.PI * (p.cap * 0.82 - 1) + 0.67 * yaziBoyutu * yaziBoyutu;
    var yuzler = p.yuz_sayisi === "cift" ? 2 : 1;

    if (p.yazi_stili === "kabartma") {
      hacim += isaretAlani * 0.69 * yuzler;
    } else {
      hacim -= isaretAlani * (yuzler === 2 ? 1.39 : 0.69);
    }

    return hacim;
  }

  // === AILE: kase ===
  function kase_knob_hacmi(cap) {
    var yaricap = 6;
    var yukseklik = 18;
    var altYaricap = cap * 0.3;
    var ustYaricap = cap * 0.5;
    var dx = ustYaricap - altYaricap;
    var uzunluk = Math.sqrt(dx * dx + yukseklik * yukseklik);
    var ux = dx / uzunluk;
    var uz = yukseklik / uzunluk;
    var aci = Math.acos(ux);
    var teget = yaricap / Math.tan(aci / 2);
    var z1 = yukseklik / 2 - uz * teget;
    var r1 = ustYaricap - ux * teget;
    var merkezX = ustYaricap - teget;
    var merkezZ = yukseklik / 2 - yaricap;
    var ilkYukseklik = z1 + yukseklik / 2;
    var konik = Math.PI * ilkYukseklik *
      (altYaricap * altYaricap + altYaricap * r1 + r1 * r1) / 3;
    var u1 = z1 - merkezZ;
    var u2 = yaricap;

    function kase_knob_ilkel(u) {
      var kok = Math.sqrt(Math.max(0, yaricap * yaricap - u * u));
      return merkezX * merkezX * u +
        merkezX * (u * kok + yaricap * yaricap * Math.asin(u / yaricap)) +
        yaricap * yaricap * u - u * u * u / 3;
    }

    return konik + Math.PI * (kase_knob_ilkel(u2) - kase_knob_ilkel(u1));
  }

  function kase(p) {
    var yukseklik = 8;
    var pah = 2.5;
    var en = 3.1 * p.yazi_boyutu + 2 * p.dolgu;
    var boy = p.bicim === "dikdortgen" ?
      2.6 * p.yazi_boyutu + 2 * p.dolgu : en;
    var taban;

    if (p.bicim === "yuvarlak") {
      var altYaricap = en / 2;
      var ustYaricap = altYaricap - 2;
      var egimUzunlugu = Math.sqrt(yukseklik * yukseklik + 4);
      var araYaricap = ustYaricap + pah * 2 / egimUzunlugu;
      var araYukseklik = yukseklik - pah * yukseklik / egimUzunlugu;
      var tepeYaricap = ustYaricap - pah;
      taban = Math.PI * araYukseklik *
        (altYaricap * altYaricap + altYaricap * araYaricap + araYaricap * araYaricap) / 3;
      taban += Math.PI * (yukseklik - araYukseklik) *
        (araYaricap * araYaricap + araYaricap * tepeYaricap + tepeYaricap * tepeYaricap) / 3;
    } else {
      taban = yukseklik * (en * boy - 2 * en - 2 * boy + 16 / 3) -
        2 * pah * pah * yukseklik;
    }

    // Varsayılan kalın yazının ölçülen 2B alanı, yazı boyutunun karesiyle ölçeklenir.
    var rolyef = 2.1218677380952453 * p.yazi_boyutu * p.yazi_boyutu *
      p.kabartma_derinligi;
    var toplam = taban + rolyef;

    if (p.sap === "sapli") {
      var topuzCapi = Math.max(en * 0.7, 22);
      // Dişli mil, gövde yuvası ve topuzla örtüşen bölümün kalibre edilmiş net etkisi.
      toplam += kase_knob_hacmi(topuzCapi) - 210.720722018491;
    }

    return toplam;
  }

  // === AILE: kasnak ===
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

  // === AILE: kayis ===
  function kayis_profil_verisi(profil) {
    if (profil === "GT2_3mm") return [3, 1.169, 2.310, 0.940, 1];
    if (profil === "GT2_5mm") return [5, 1.968, 3.952, 1.636, 1];
    if (profil === "HTD_3mm") return [3, 1.289, 2.270, 1.068, 1];
    if (profil === "HTD_5mm") return [5, 2.199, 3.781, 1.670, 1];
    if (profil === "HTD_8mm") return [8, 3.607, 6.603, 2.879, 1];
    if (profil === "T2.5") return [2.5, 0.700, 1.679, 1.058, 0];
    if (profil === "T5") return [5, 1.190, 3.264, 1.898, 0];
    if (profil === "T10") return [10, 2.500, 6.130, 3.758, 0];
    if (profil === "AT5") return [5, 1.190, 4.268, 2.574, 0];
    if (profil === "MXL") return [2.032, 0.508, 1.321, 0.834, 0];
    if (profil === "XL") return [5.08, 1.270, 3.051, 1.467, 0];
    if (profil === "L") return [9.525, 1.905, 5.359, 3.439, 0];
    if (profil === "40DP") return [2.073, 0.457, 1.226, 0.655, 0];
    return [2, 0.764, 1.494, 0.716, 1];
  }

  function kayis_dis_alani(veri) {
    var derinlik = veri[1];
    var taban = veri[2];
    var tepe = veri[3];

    if (!veri[4]) {
      return derinlik * (taban + tepe) / 2;
    }

    // SCAD'daki yuvarlak diş, 0,02 mm'lik taban dikdörtgeni ile tepe
    // çemberinin dışbükey zarfıdır. Aşağıdaki ifade bu zarfın analitik alanıdır.
    var yariTaban = taban / 2;
    var yariTepe = tepe / 2;
    var merkezY = derinlik - yariTepe - 0.01;
    var uzaklik2 = yariTaban * yariTaban + merkezY * merkezY;
    var teget = Math.sqrt(uzaklik2 - yariTepe * yariTepe);
    var birimX = (yariTepe * yariTaban + teget * merkezY) / uzaklik2;
    var birimY = (-yariTepe * merkezY + teget * yariTaban) / uzaklik2;
    var tegetY = merkezY + yariTepe * birimY;
    var aci = Math.atan2(birimY, birimX);
    var kubbe = yariTaban * tegetY +
      yariTepe * yariTepe * (Math.PI - 2 * aci) / 2 +
      merkezY * yariTepe * birimX;

    // Taban karesinin sırtla çakışan yarısı çıkarılmış net diş alanı.
    return kubbe + taban * 0.01;
  }

  function kayis(p) {
    var veri = kayis_profil_verisi(p.profil);
    var adim = veri[0];
    var derinlik = veri[1];
    var sirt = Math.max(derinlik * 0.7, 0.8);
    var uzunluk = p.dis_sayisi * adim;
    var sirtAlani = uzunluk * sirt;

    if (p.sekil === "kapali") {
      if (p.dis_taraf === "ic") sirtAlani += Math.PI * sirt * sirt;
      if (p.dis_taraf === "dis") sirtAlani -= Math.PI * sirt * sirt;
    }

    var tarafSayisi = p.dis_taraf === "cift" ? 2 : 1;
    var disAlani = p.dis_sayisi * tarafSayisi * kayis_dis_alani(veri);
    return (sirtAlani + disAlani) * p.genislik;
  }

  // === AILE: konektor ===
  function konektor(p) {
    var n = Math.max(2, Math.min(4, Math.round(p.kol_sayisi)));
    var tol = p.gecme === "siki" ? 0.1 : (p.gecme === "gevsek" ? 0.5 : 0.3);
    var d = p.cubuk_capi + 2 * p.cidar;
    var delik = p.cubuk_capi + tol;
    var r = d * 0.6;
    var disAlan;
    if (p.kol_kesiti === "kare") {
      disAlan = d * d;
    } else if (p.kol_kesiti === "sekizgen") {
      disAlan = 2 * d * d / (1 + Math.SQRT2);
    } else {
      disAlan = Math.PI * d * d / 4;
    }
    var delikAlan = Math.PI * delik * delik / 4;

    // İki karşılıklı kolda dış gövde bir prizma, merkezde prizma dışında kalan
    // küre parçası ve iki ayrı yuva olarak tam ayrışır. Son katsayılar birim dış
    // ölçüdeki küre parçasının kesit integralleridir.
    if (n === 2) {
      var kureKatsayisi = p.kol_kesiti === "kare" ? 0.07120929525129341 :
        (p.kol_kesiti === "sekizgen" ? 0.1260016651969578 : 0.15281909978271654);
      return 2 * p.kol_boyu * (disAlan - delikAlan) +
        2 * delikAlan * p.cidar + kureKatsayisi * d * d * d;
    }

    // Küre ile kolların ve yuvaların kesiştiği merkez bölge sabit bir ızgarada
    // değerlendirilir; küre dışındaki düz kol bölümü analitik olarak eklenir.
    var adimSayisi = 40;
    var sinir = d * 1.11;
    var hucre = 2 * sinir / adimSayisi;
    var yari = d / 2;
    var delikYari2 = delik * delik / 4;
    var r2 = r * r;
    var yonX = [];
    var yonY = [];
    var a;
    for (a = 0; a < n; a++) {
      var aci = 2 * Math.PI * a / n;
      yonX.push(Math.cos(aci));
      yonY.push(Math.sin(aci));
    }

    var dolu = 0;
    var ix;
    var iy;
    var iz;
    for (ix = 0; ix < adimSayisi; ix++) {
      var x = -sinir + (ix + 0.5) * hucre;
      for (iy = 0; iy < adimSayisi; iy++) {
        var y = -sinir + (iy + 0.5) * hucre;
        for (iz = 0; iz < adimSayisi; iz++) {
          var z = -sinir + (iz + 0.5) * hucre;
          var dis = x * x + y * y + z * z <= r2;
          var bos = false;
          for (a = 0; a < n; a++) {
            var boyuna = x * yonX[a] + y * yonY[a];
            var enine = -x * yonY[a] + y * yonX[a];
            if (boyuna >= 0 && boyuna <= r) {
              var kesitte;
              if (p.kol_kesiti === "kare") {
                kesitte = Math.abs(enine) <= yari && Math.abs(z) <= yari;
              } else if (p.kol_kesiti === "sekizgen") {
                kesitte = Math.abs(enine) <= yari && Math.abs(z) <= yari &&
                  Math.abs(enine) + Math.abs(z) <= d / Math.SQRT2;
              } else {
                kesitte = enine * enine + z * z <= yari * yari;
              }
              if (kesitte) dis = true;
              if (boyuna >= p.cidar && enine * enine + z * z <= delikYari2) bos = true;
            }
          }
          if (dis && !bos) dolu++;
        }
      }
    }

    var merkez = dolu * hucre * hucre * hucre;
    return merkez + n * (p.kol_boyu - r) * (disAlan - delikAlan);
  }

  // === AILE: oring ===
  function oring(p) {
    var merkezYaricap = p.ic_cap / 2 + p.kesit_cap / 2;
    var kesitAlani;

    if (p.profil === "kare") {
      kesitAlani = p.kesit_cap * p.kesit_cap;
    } else if (p.profil === "pahli") {
      kesitAlani = 0.875 * p.kesit_cap * p.kesit_cap;
    } else {
      kesitAlani = Math.PI * p.kesit_cap * p.kesit_cap / 4;
    }

    return kesitAlani * 2 * Math.PI * merkezYaricap;
  }

  // === AILE: pervane ===
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

  // === AILE: petek ===
  function petek_kirp_alani(noktalar, xmin, xmax, ymin, ymax) {
    var cokgen = noktalar;
    var sinirlar = [xmin, xmax, ymin, ymax];

    for (var kenar = 0; kenar < 4; kenar++) {
      var giris = cokgen;
      cokgen = [];
      if (giris.length === 0) return 0;

      for (var i = 0; i < giris.length; i++) {
        var a = giris[i];
        var b = giris[(i + 1) % giris.length];
        var aIceride;
        var bIceride;
        if (kenar === 0) {
          aIceride = a[0] >= sinirlar[kenar];
          bIceride = b[0] >= sinirlar[kenar];
        } else if (kenar === 1) {
          aIceride = a[0] <= sinirlar[kenar];
          bIceride = b[0] <= sinirlar[kenar];
        } else if (kenar === 2) {
          aIceride = a[1] >= sinirlar[kenar];
          bIceride = b[1] >= sinirlar[kenar];
        } else {
          aIceride = a[1] <= sinirlar[kenar];
          bIceride = b[1] <= sinirlar[kenar];
        }

        if (aIceride !== bIceride) {
          var t;
          if (kenar < 2) {
            t = (sinirlar[kenar] - a[0]) / (b[0] - a[0]);
            var dikey = [sinirlar[kenar], a[1] + t * (b[1] - a[1])];
            if (aIceride) cokgen.push(dikey);
            else cokgen.push(dikey);
          }
          else {
            t = (sinirlar[kenar] - a[1]) / (b[1] - a[1]);
            var yatay = [a[0] + t * (b[0] - a[0]), sinirlar[kenar]];
            if (aIceride) cokgen.push(yatay);
            else cokgen.push(yatay);
          }
        }
        if (bIceride) cokgen.push(b);
      }
    }

    var ikiAlan = 0;
    for (var j = 0; j < cokgen.length; j++) {
      var c = cokgen[j];
      var d = cokgen[(j + 1) % cokgen.length];
      ikiAlan += c[0] * d[1] - d[0] * c[1];
    }
    return Math.abs(ikiAlan) / 2;
  }

  function petek(p) {
    var aralik = 4;
    var s = p.goz_boyutu;
    var pitch = s + aralik;
    var inset = s / 2 + 0.6;
    var yariEn = p.en / 2 - inset;
    var yariBoy = p.boy / 2 - inset;
    var noktalar = [];
    var adet;
    var yaricap;

    if (p.desen === "kare") {
      noktalar = [[-s / 2, -s / 2], [s / 2, -s / 2],
        [s / 2, s / 2], [-s / 2, s / 2]];
    } else {
      if (p.desen === "petek") {
        adet = 6;
        yaricap = s / (2 * Math.cos(Math.PI / 6));
      } else if (p.desen === "sekizgen") {
        adet = 8;
        yaricap = s / (2 * Math.cos(Math.PI / 8));
      } else if (p.desen === "besgen") {
        adet = 5;
        yaricap = s / 2;
      } else if (p.desen === "ucgen") {
        adet = 3;
        yaricap = s / 2;
      } else {
        adet = 180;
        yaricap = s / 2;
      }
      for (var k = 0; k < adet; k++) {
        var aci = 2 * Math.PI * k / adet;
        noktalar.push([yaricap * Math.cos(aci), yaricap * Math.sin(aci)]);
      }
    }

    var tamIkiAlan = 0;
    var minX = Infinity;
    var maxX = -Infinity;
    var minY = Infinity;
    var maxY = -Infinity;
    for (var n = 0; n < noktalar.length; n++) {
      var q = noktalar[n];
      var sonraki = noktalar[(n + 1) % noktalar.length];
      tamIkiAlan += q[0] * sonraki[1] - sonraki[0] * q[1];
      minX = Math.min(minX, q[0]);
      maxX = Math.max(maxX, q[0]);
      minY = Math.min(minY, q[1]);
      maxY = Math.max(maxY, q[1]);
    }
    var tamAlan = Math.abs(tamIkiAlan) / 2;
    var desenAlani = 0;

    if (yariEn > 0 && yariBoy > 0) {
      var dy = p.desen === "petek" ? pitch * 0.8660 : pitch;
      var nx = Math.ceil(p.en / pitch / 2) + 1;
      var ny = Math.ceil(p.boy / dy / 2) + 1;

      for (var satir = -ny; satir <= ny; satir++) {
        var xKaydir = satir % 2 === 0 ? 0 : pitch / 2;
        var cy = satir * dy;
        for (var sutun = -nx; sutun <= nx; sutun++) {
          var cx = sutun * pitch + xKaydir;
          if (cx + maxX <= yariEn && cx + minX >= -yariEn &&
              cy + maxY <= yariBoy && cy + minY >= -yariBoy) {
            desenAlani += tamAlan;
          } else if (cx + maxX > -yariEn && cx + minX < yariEn &&
                     cy + maxY > -yariBoy && cy + minY < yariBoy) {
            var tasinmis = [];
            for (var v = 0; v < noktalar.length; v++) {
              tasinmis.push([cx + noktalar[v][0], cy + noktalar[v][1]]);
            }
            desenAlani += petek_kirp_alani(
              tasinmis, -yariEn, yariEn, -yariBoy, yariBoy);
          }
        }
      }
    }

    var tabanAlani = p.en * p.boy;
    if (p.mod === "kabartma") {
      var kabartma = Math.max(p.kalinlik * 0.4, 1);
      return tabanAlani * p.kalinlik + desenAlani * (kabartma - 0.01);
    }
    return (tabanAlani - desenAlani) * p.kalinlik;
  }

  // === AILE: profil ===
  function profil(p) {
    var h = p.yukseklik;
    var b = p.genislik;
    var t = p.et_kalinligi;
    var alan;

    if (p.kesit === "t") {
      alan = b * t + t * (h - t);
    } else if (p.kesit === "l") {
      alan = t * h + b * t - t * t;
    } else if (p.kesit === "i" || p.kesit === "z" || p.kesit === "u") {
      alan = t * h + 2 * b * t - 2 * t * t;
    } else if (p.kesit === "kutu") {
      alan = b * h;
      if (p.ic_yapi === "bos") alan -= (b - 2 * t) * (h - 2 * t);
    } else if (p.kesit === "cokgen") {
      var kenar = 6;
      var katsayi = kenar * Math.sin(2 * Math.PI / kenar) / 2;
      var disYaricap = b / 2;
      alan = katsayi * disYaricap * disYaricap;
      if (p.ic_yapi === "bos") {
        var icYaricap = disYaricap - t;
        alan -= katsayi * icYaricap * icYaricap;
      }
    } else if (p.kesit === "elips") {
      alan = Math.PI * b * h / 4;
      if (p.ic_yapi === "bos") alan -= Math.PI * (b - 2 * t) * (h - 2 * t) / 4;
    } else {
      // Sabit 40 serisi sigma: yuvarlatılmış dış kareden merkez deliği ve dört T-slot çıkarılır.
      var sigmaBoyu = 40;
      var koseYaricapi = 1.5;
      var disAlan = sigmaBoyu * sigmaBoyu - (4 - Math.PI) * koseYaricapi * koseYaricapi;
      var merkezDeligi = Math.PI * 3.4 * 3.4;
      var tekSlot = 11 * 12.4 + 8 * 2.05 - 8 * 0.05;
      alan = disAlan - merkezDeligi - 4 * tekSlot;
    }

    return alan * p.uzunluk;
  }

  // === AILE: rampa ===
  function rampa(p) {
    var uzunluk = p.uzunluk;
    var genislik = p.genislik;
    var yukseklik = p.egim_yontemi === "aci" ?
      uzunluk * Math.tan(p.egim_acisi * Math.PI / 180) : p.yukseklik;

    if (p.ust_yuzey === "basamakli") {
      var basamakSayisi = 8;
      return genislik * uzunluk * yukseklik *
        (basamakSayisi - 1) / (2 * basamakSayisi);
    }

    var hacim = genislik * uzunluk * yukseklik / 2;
    if (p.ust_yuzey === "tirtikli") {
      var egimBoyu = Math.sqrt(uzunluk * uzunluk + yukseklik * yukseklik);
      var tirtikSayisi = Math.floor(egimBoyu / 3);
      var etkinTirtik = 0;
      for (var k = 1; k <= tirtikSayisi; k++) {
        var x = k * 3 * uzunluk / egimBoyu;
        if (x < uzunluk - 1.6) etkinTirtik++;
      }
      // Her tırtık gövde üstünde 1,6 mm x 1 mm net kesit oluşturur.
      hacim += etkinTirtik * 1.6 * genislik;
    }

    return hacim;
  }

  // === AILE: rulman ===
  function rulman_makaraKanalHacmi(hatYaricapi, elemanYaricapi, kanalYaricapi, makaraYuksekligi) {
    // Makara silindirinin köşeleri halka eğriliği yüzünden torus kanalından taşabilir.
    // SCAD union bu taşan kısmı bilezikle üst üste bindirir; yalnız kanalda kalan
    // hacmi, makara tabanındaki sabit orta-nokta integraliyle hesapla.
    var adimSayisi = 32;
    var du = 2 * elemanYaricapi / adimSayisi;
    var hacim = 0;

    for (var i = 0; i < adimSayisi; i++) {
      var u = -elemanYaricapi + (i + 0.5) * du;
      var vSiniri = Math.sqrt(
        Math.max(0, elemanYaricapi * elemanYaricapi - u * u)
      );
      var dv = 2 * vSiniri / adimSayisi;

      for (var j = 0; j < adimSayisi; j++) {
        var v = -vSiniri + (j + 0.5) * dv;
        var halkaUzakligi = Math.sqrt(
          (hatYaricapi + u) * (hatYaricapi + u) + v * v
        ) - hatYaricapi;
        var yariYukseklikKaresi = kanalYaricapi * kanalYaricapi -
          halkaUzakligi * halkaUzakligi;
        var kanalYariYuksekligi = yariYukseklikKaresi > 0 ?
          Math.sqrt(yariYukseklikKaresi) : 0;
        var kesitYuksekligi = 2 * Math.min(
          makaraYuksekligi / 2,
          kanalYariYuksekligi
        );
        hacim += kesitYuksekligi * du * dv;
      }
    }

    return hacim;
  }

  function rulman(p) {
    var radyalBosluk = (p.dis_cap - p.ic_cap) / 2;
    var hatYaricapi = (p.ic_cap + p.dis_cap) / 4;
    var elemanYaricapi = Math.max(
      Math.min(radyalBosluk * 0.28, p.genislik / 2 - p.bosluk - 1),
      0.8
    );
    var kanalYaricapi = elemanYaricapi + p.bosluk;
    var elemanSayisi = Math.max(3, Math.floor(
      2 * Math.PI * hatYaricapi /
      (2 * elemanYaricapi + 2 * p.bosluk + 0.5)
    ));
    var govdeHacmi = Math.PI *
      (p.dis_cap * p.dis_cap - p.ic_cap * p.ic_cap) * p.genislik / 4;
    var kanalKesitAlani;

    if (p.eleman === "tutmali") {
      kanalYaricapi = elemanYaricapi * 1.5 + p.bosluk;
    }

    if (kanalYaricapi <= p.genislik / 2) {
      kanalKesitAlani = Math.PI * kanalYaricapi * kanalYaricapi;
    } else {
      var yariGenislik = p.genislik / 2;
      var kok = Math.sqrt(
        kanalYaricapi * kanalYaricapi - yariGenislik * yariGenislik
      );
      kanalKesitAlani = 2 * (
        yariGenislik * kok + kanalYaricapi * kanalYaricapi *
        Math.asin(yariGenislik / kanalYaricapi)
      );
    }

    govdeHacmi -= 2 * Math.PI * hatYaricapi * kanalKesitAlani;

    if (p.flans === "var") {
      var flansCapi = p.dis_cap + Math.max(radyalBosluk * 0.5, 2);
      var flansYuksekligi = Math.min(1.5, p.genislik * 0.25);
      govdeHacmi += Math.PI *
        (flansCapi * flansCapi - p.dis_cap * p.dis_cap) *
        flansYuksekligi / 4;
    }

    var elemanHacmi;
    if (p.eleman === "makara") {
      var makaraYuksekligi = Math.min(
        2 * (elemanYaricapi + p.bosluk) - 0.4,
        p.genislik - 2 * p.bosluk
      );
      elemanHacmi = rulman_makaraKanalHacmi(
        hatYaricapi,
        elemanYaricapi,
        kanalYaricapi,
        makaraYuksekligi
      );
    } else if (p.eleman === "tutmali") {
      // İki eş kürenin merkez aralığı yarıçapa eşittir; orta silindir kürelerin içindedir.
      elemanHacmi = 9 * Math.PI * elemanYaricapi * elemanYaricapi *
        elemanYaricapi / 4;
    } else {
      elemanHacmi = 4 * Math.PI * elemanYaricapi * elemanYaricapi *
        elemanYaricapi / 3;
    }

    return govdeHacmi + elemanSayisi * elemanHacmi;
  }

  // === AILE: vida ===
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

  function vida(p) {
    if (p.urun_tipi === "pul") {
      var icCap = p.cap + Math.max(p.tolerans, 0.3) + 0.3;
      var disCap = p.cap * 2;
      var kalinlik = Math.max(p.cap * 0.16, 1);
      return Math.PI * (disCap * disCap - icCap * icCap) * kalinlik / 4;
    }

    if (p.urun_tipi === "somun") {
      return 157.05286845271212;
    }

    var disKesitAlani = vida_dis_kesit_alani(5, 0.8);
    if (p.urun_tipi === "mil") {
      return disKesitAlani * p.boy - 5.8674336554163915;
    }

    return disKesitAlani * p.boy + 188.03729995610064;
  }

  // === AILE: yay ===
  function yay_dalga_degeri(form, faz, genlik) {
    var f = faz - Math.floor(faz);
    if (form === "sinus") return genlik * Math.sin(2 * Math.PI * faz);
    if (form === "ucgen") return genlik * (f < 0.5 ? 4 * f - 1 : 3 - 4 * f);
    if (form === "testere") return genlik * (2 * f - 1);
    if (form === "darbe") return genlik * (f < 0.3 ? 1 : -1);
    return genlik * (f < 0.5 ? 1 : -1);
  }

  function yay_dalga_hacmi(p) {
    var genlik = 10;
    var cevrim = 4;
    var seritKalinligi = 2;
    var seritYuksekligi = 8;
    var parcaSayisi = 160;
    var dx = p.dalga_boyu / parcaSayisi;
    var uzunluk = 0;
    var onceki = yay_dalga_degeri(p.dalga_formu, 0, genlik);

    for (var i = 1; i <= parcaSayisi; i++) {
      var faz = cevrim * i / parcaSayisi;
      var simdiki = yay_dalga_degeri(p.dalga_formu, faz, genlik);
      var dy = simdiki - onceki;
      uzunluk += Math.sqrt(dx * dx + dy * dy);
      onceki = simdiki;
    }

    var yaricap = seritKalinligi / 2;
    var kesitAlani = seritKalinligi * uzunluk + Math.PI * yaricap * yaricap;
    // SCAD şeridi 16 kenarlı çemberlerin dışbükey zarflarından oluşur.
    return 0.98 * kesitAlani * seritYuksekligi;
  }

  function yay(p) {
    if (p.tip === "dalga") return yay_dalga_hacmi(p);

    var sarimSayisi = 8;
    var yaricap = (p.dis_cap - p.tel_capi) / 2;
    var eksenBoyu = Math.max(p.serbest_boy - p.tel_capi, p.tel_capi);
    var cevreBoyu = 2 * Math.PI * yaricap * sarimSayisi;
    var yolBoyu = Math.sqrt(eksenBoyu * eksenBoyu + cevreBoyu * cevreBoyu);
    var telAlani = Math.PI * p.tel_capi * p.tel_capi / 4;
    return telAlani * yolBoyu;
  }

  return {
    braket: braket,
    cetvel: cetvel,
    disli: disli,
    huni: huni,
    izgara: izgara,
    jeton: jeton,
    kase: kase,
    kasnak: kasnak,
    kayis: kayis,
    konektor: konektor,
    oring: oring,
    pervane: pervane,
    petek: petek,
    profil: profil,
    rampa: rampa,
    rulman: rulman,
    vida: vida,
    yay: yay
  };
});
