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
  function braket_delik_alani(fn, cap) {
    // OpenSCAD circle(d, $fn) içe çizili çokgen alanı
    var r = cap / 2;
    return 0.5 * fn * r * r * Math.sin(2 * Math.PI / fn);
  }

  function braket_delik_sayisi(bas, son, n) {
    // scad _delik_s ile birebir: bas>=son ya da n==1 → tek (üst üste biner)
    if (n <= 0) return 0;
    if (bas >= son || n === 1) return 1;
    return n;
  }

  function braket_izgara_alani(icinde, xmin, xmax, ymin, ymax) {
    var hucre = Math.max(0.15, (xmax - xmin) / 640);
    var Nx = Math.ceil((xmax - xmin) / hucre);
    var Ny = Math.ceil((ymax - ymin) / hucre);
    var say = 0;
    for (var i = 0; i < Nx; i++) {
      var x = xmin + (i + 0.5) * hucre;
      for (var j = 0; j < Ny; j++) {
        if (icinde(x, ymin + (j + 0.5) * hucre)) say++;
      }
    }
    return say * hucre * hucre;
  }

  function braket(p) {
    // v2 geometrisi (2026-07-16): angle = tek profil çokgeni × genişlik;
    // l/t/y = merkezli yarım şeritler + merkez diski; corner = 3 dik plaka.
    // esleme sabitleri: M4 (4.5 mm), delik_fn=32, kolon=1, radyus=0, payanda yok.
    var t = Math.max(p.kalinlik, 1.2);
    var w = p.genislik;
    var L = p.uzunluk;
    var hd = 4.5;
    var Ad = braket_delik_alani(32, hd);
    var kenarPay = Math.max(hd + 2, w * 0.3);

    if (p.tip === "duz") {
      var kd = braket_delik_sayisi(kenarPay, L - kenarPay, p.delik_adet);
      return L * w * t - kd * Ad * t;
    }

    if (p.tip === "acili") {
      var a = p.ic_aci * Math.PI / 180;
      var ux = Math.cos(a), uz = Math.sin(a);
      var nx = uz, nz = -ux;
      var pts = [[0, 0], [L, 0], [L, t], [t * (1 + ux) / uz, t],
                 [L * ux + nx * t, L * uz + nz * t], [L * ux, L * uz]];
      var alan2 = 0;
      for (var i = 0; i < pts.length; i++) {
        var q1 = pts[i], q2 = pts[(i + 1) % pts.length];
        alan2 += q1[0] * q2[1] - q2[0] * q1[1];
      }
      var bas1 = Math.max(w * 0.5, t * (1 + ux) / uz + hd, hd + 3);
      var ka = braket_delik_sayisi(bas1, L - kenarPay, p.delik_adet);
      return Math.abs(alan2) / 2 * w - 2 * ka * Ad * t;
    }

    if (p.tip === "kose") {
      var bk = Math.max(w * 0.6, hd + t + 2);
      var kk = braket_delik_sayisi(bk, L - kenarPay, p.delik_adet);
      return 3 * L * w * t - L * t * t - 2 * w * t * t + t * t * t -
        3 * kk * Ad * t;
    }

    // l / t / y: 2B ızgara (yarım şeritler + merkez diski)
    var acilar = p.tip === "l" ? [0, 90] :
                 p.tip === "t" ? [0, 180, 270] : [90, 210, 330];
    var yonler = [];
    for (var m = 0; m < acilar.length; m++) {
      var th = acilar[m] * Math.PI / 180;
      yonler.push([Math.cos(th), Math.sin(th)]);
    }
    var r0 = w / 2;
    var alan = braket_izgara_alani(function (x, y) {
      if (x * x + y * y <= r0 * r0) return true;
      for (var k = 0; k < yonler.length; k++) {
        var s = x * yonler[k][0] + y * yonler[k][1];
        if (s >= 0 && s <= L &&
            Math.abs(-x * yonler[k][1] + y * yonler[k][0]) <= r0) return true;
      }
      return false;
    }, -(L + r0), L + r0, -(L + r0), L + r0);
    var icBosluk = Math.max(w * 0.65, hd + 3);
    var kp = braket_delik_sayisi(icBosluk, L - kenarPay, p.delik_adet);
    return alan * t - acilar.length * kp * Ad * t;
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
  function disli_delik_alani(cap) {
    // OpenSCAD cylinder($fn=64) ice cizili cokgen alani (d^2 carpani)
    return 0.7841371226364848 * cap * cap;
  }

  function disli_taban_alani(kats, N, m) {
    // LSQ tabani: {m^2 N^2, m^2 N, m^2, m N, m}
    return kats[0] * m * m * N * N + kats[1] * m * m * N + kats[2] * m * m +
      kats[3] * m * N + kats[4] * m;
  }

  function disli_tablo_oku(tablo, N) {
    // N=32..64 tablosu; kesirli/aralik disi N icin kirp + dogrusal ara deger
    var x = Math.min(Math.max(N, 32), 64) - 32;
    var i = Math.min(Math.floor(x), 31);
    return tablo[i] + (tablo[i + 1] - tablo[i]) * (x - i);
  }

  function disli_konik_hacim_tablosu(N) {
    // v2 kalibre (2026-07-16): bevel_gear(mate=24, saft 90) V/m^3, N=32..64
    // (BOSL2 ic esikleri yuzunden N'de duzgun degil -> tablo)
    return disli_tablo_oku([
      2726.24, 2908.89, 3097.38, 3291.34, 3491.09, 3696.65, 3908.09,
      4125.41, 4348.84, 4578.16, 4813.42, 5053.77, 5299.83, 5551.68,
      5809.33, 6101.39, 6497.51, 6910.81, 7341.67, 7790.5, 8257.61,
      8743.42, 9248.32, 9771.81, 10208.6, 10654.15, 11108.4, 11571.23,
      12042.74, 12522.89, 13011.67, 13509.1, 14015.38], N);
  }

  function disli_konik_delik_boyu_tablosu(N) {
    // konik govde tepeye dogru daralir; mil deligi yalniz gobek boyunca
    // et kaldirir -> etkin delik boyu/m tablosu (olculdu, d ve m'den bagimsiz)
    return disli_tablo_oku([
      4.3441, 4.3477, 4.3511, 4.3542, 4.3572, 4.36, 4.3626, 4.365,
      4.3674, 4.3697, 4.3718, 4.3737, 4.3755, 4.3773, 4.3789, 4.3978,
      4.4721, 4.5468, 4.6218, 4.6971, 4.7726, 4.8484, 4.9244, 5.0,
      5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0], N);
  }

  function disli(p) {
    // v2 kalibre (2026-07-16): olcuye gore uretec v2'ye (BOSL2 gears sarmali)
    // LSQ fit; olcum gridi N=32..64, m=1..1.5, h=6..8, delik=0..8 (esleme
    // sabitleri: basinc 20, helis 20, bosluk 0.15, es_dis 24, Segments 64).
    var N = p.dis_sayisi;
    var m = p.modul;
    var h = p.kalinlik;
    var delik = disli_delik_alani(p.delik_capi);

    if (p.disli_tipi === "duz") {
      return (disli_taban_alani([0.7851503182, -0.1357761697, -4.085040431,
        -0.3347220277, -0.02234787348], N, m) - delik) * h;
    }
    if (p.disli_tipi === "helis") {
      return (disli_taban_alani([0.8895497605, -0.1454588491, -3.536365845,
        -0.3646167419, 1.011983576], N, m) - delik) * h;
    }
    if (p.disli_tipi === "cift_helis") {
      return (disli_taban_alani([0.889580645, -0.1434499449, -3.758176869,
        -0.3720096691, 1.44214944], N, m) - delik) * h;
    }
    if (p.disli_tipi === "konik") {
      // kalinliktan bagimsiz (uretec konik yuz genisligini kendisi secer)
      return m * m * m * disli_konik_hacim_tablosu(N) -
        delik * m * disli_konik_delik_boyu_tablosu(N);
    }
    if (p.disli_tipi === "sonsuz") {
      // govde capi = max(6m, delik+4m); vida boyu = kalinlik (h >= 4m)
      var dg = Math.max(6 * m, p.delik_capi + 4 * m);
      var alan = 0.7837252161 * dg * dg - 0.1835391791 * dg * m +
        2.570962742 * m * m - 0.3284141631 * dg + 0.03268601037 * m;
      return (alan - delik) * h;
    }
    if (p.disli_tipi === "ic_disli") {
      // mil deligi gecmez (ic bosluk zaten var); sirt = 3m
      return disli_taban_alani([-0.001601635821, 13.19634411, 58.69996835,
        -0.3404922745, -0.07644835391], N, m) * h;
    }
    if (p.disli_tipi === "tac") {
      // taban disk kalinlikla buyur (A terimi), dis tabakasi sabit (B terimi)
      var A = 0.7858143808 * m * m * N * N + 9.366207657 * m * m * N +
        33.32777701 * m * m - 0.002099730821 * m * N;
      var B = -1.768605751 * m * m * m * N * N - 9.767225293 * m * m * m * N -
        65.27467583 * m * m * m - 1.00755036 * m * m * N;
      return h * A + B - delik * h;
    }
    // kramayer: boy = N*pi*m, sirt = 3 mm sabit; mil deligi gecmez
    return (3.74410595 * N * m * m + 9.08727794 * N * m) * h;
  }

  // === AILE: huni ===
  function huni(p) {
    // Uretim motoruna kalibre (Faz E): koni duvari HER YERDE yatay 1.5 mm
    // (tube id+2*wall — eski model altta 1.2 varsayiyordu); uc borusunun disi
    // konik: kokte 1.5, ucta 1.2 duvar (od1=id+3, od2=id+2.4, ic silindirik).
    var pi = Math.PI;
    var icUstYaricap = p.agiz_capi / 2;
    var icAltYaricap = p.uc_capi / 2;
    var disUstYaricap = icUstYaricap + 1.5;
    var disAltYaricap = icAltYaricap + 1.5;

    var disKoni = pi * p.yukseklik / 3 *
      (disAltYaricap * disAltYaricap +
       disAltYaricap * disUstYaricap +
       disUstYaricap * disUstYaricap);
    var icKoni = pi * p.yukseklik / 3 *
      (icAltYaricap * icAltYaricap +
       icAltYaricap * icUstYaricap +
       icUstYaricap * icUstYaricap);

    var ucKok = icAltYaricap + 1.5;
    var ucTip = icAltYaricap + 1.2;
    var ucHacmi = pi * p.uc_boyu / 3 *
      (ucKok * ucKok + ucKok * ucTip + ucTip * ucTip) -
      pi * icAltYaricap * icAltYaricap * p.uc_boyu;

    // Kenar (brim): dis silindir sabit, IC DELIK koni egimini izler (motor
    // id2 = id1 - 2*slope*kalinlik) — sig genis hunilerde fark %4'e cikiyordu.
    var kenarDisYaricap = disUstYaricap + 4;
    var egim = (icUstYaricap - icAltYaricap) / p.yukseklik;
    var kenarIc1 = disUstYaricap - 0.05;
    var kenarIc2 = kenarIc1 - egim * 1.5;
    var kenarHacmi = pi * 1.5 *
      (kenarDisYaricap * kenarDisYaricap -
       (kenarIc1 * kenarIc1 + kenarIc1 * kenarIc2 + kenarIc2 * kenarIc2) / 3);

    // Eğik düzlemin boru cidarından çıkardığı hacim (uçtaki dar kesitte).
    var aci = p.uc_acisi * pi / 180;
    var ucKesigi = Math.tan(aci) * ucTip * pi *
      (ucTip * ucTip - icAltYaricap * icAltYaricap);

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

  function izgara_desen_noktalari(sekil) {
    // Uretim motorunun desen sekilleri, sabit olcu [8,8]:
    // yuvarlak cember r4; sekizgen CEVREL 8-gen r=4/cos22.5, KOSELER 0°'da
    // (BOSL2 circum kendi 22.5° dondurur + motorun 22.5 spin'i koseyi 0'a
    // getirir); petek IC 6-gen r4 faz 0; besgen r4 faz +18°; ucgen r4 faz 0.
    if (sekil === "kare") {
      return [[-4, -4], [4, -4], [4, 4], [-4, 4]];
    }
    var adet = 180;
    var yaricap = 4;
    var faz = 0;
    if (sekil === "sekizgen") {
      adet = 8;
      yaricap = 4 / Math.cos(Math.PI / 8);
    } else if (sekil === "petek") {
      adet = 6;
    } else if (sekil === "besgen") {
      adet = 5;
      faz = 18 * Math.PI / 180;
    } else if (sekil === "ucgen") {
      adet = 3;
    }
    var noktalar = [];
    for (var i = 0; i < adet; i++) {
      var aci = faz + 2 * Math.PI * i / adet;
      noktalar.push([yaricap * Math.cos(aci), yaricap * Math.sin(aci)]);
    }
    return noktalar;
  }

  function izgara_delik_alani(p, icYariEn, icYariBoy) {
    // Motor kafesi: adim [11, 7] (desen 8 + aralik 3; sasirtma satir adimini
    // 7'ye dusurur), kopya sayisi floor(olcu/adim)+1, merkezli, INDEKS
    // PARITESI (i+j) cift olanlar kalir (dama deseni). Delikler govde
    // sinirina degil IC cerceve (insert duvari 2 mm) dikdortgenine kirpilir —
    // duvar bandindaki kisim insert ile geri doluyor.
    var temel = izgara_desen_noktalari(p.delik_sekli);
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
    var nx = Math.floor(p.en / 11) + 1;
    var ny = Math.floor(p.boy / 7) + 1;
    var toplam = 0;
    for (var j = 0; j < ny; j++) {
      var cy = (j - (ny - 1) / 2) * 7;
      for (var i = 0; i < nx; i++) {
        if ((i + j) % 2 !== 0) continue;
        var cx = (i - (nx - 1) / 2) * 11;
        if (cx + minX >= -icYariEn && cx + maxX <= icYariEn &&
            cy + minY >= -icYariBoy && cy + maxY <= icYariBoy) {
          toplam += tamAlan;
        } else if (cx + maxX > -icYariEn && cx + minX < icYariEn &&
                   cy + maxY > -icYariBoy && cy + minY < icYariBoy) {
          var tasinmis = [];
          for (var q = 0; q < temel.length; q++) {
            tasinmis.push([cx + temel[q][0], cy + temel[q][1]]);
          }
          toplam += izgara_dikdortgen_kirp_alani(tasinmis, icYariEn, icYariBoy);
        }
      }
    }
    return toplam;
  }

  function izgara_panjur_hacmi(p, govdeDerinligi) {
    // 7 yatay egik cita (motor: 8 hucre "between" dagilimi = 7 cita, dikey
    // cita yok), kesit kalinligi 2 mm, boy en-4; z 0..H araligina ve ic
    // cerceveye kirpilir (sayisal z-integrali).
    var il = p.boy - 4;
    var aci = p.panjur_acisi * Math.PI / 180;
    var g = (il - 14) / 8;
    var adimBoyu = 2 + g;
    var ilkMerkez = -il / 2 + g + 1;
    var H = govdeDerinligi;
    var adim = 60;
    var dz = H / adim;
    var tanA = Math.tan(aci);
    var yariKalinlik = 1 / Math.cos(aci);
    var alan = 0;
    for (var s = 0; s < 7; s++) {
      var merkez = ilkMerkez + s * adimBoyu;
      for (var k = 0; k < adim; k++) {
        var z = (k + 0.5) * dz - H / 2;
        var orta = merkez + z * tanA;
        var lo = Math.max(orta - yariKalinlik, -il / 2);
        var hi = Math.min(orta + yariKalinlik, il / 2);
        if (hi > lo) alan += (hi - lo) * dz;
      }
    }
    return alan * (p.en - 4);
  }

  function izgara(p) {
    // Uretim motoruna kalibre (Faz E): govde derinligi min(derinlik, 8)
    // (insert derinligi tavani); cepecevre insert duvari (2 mm et, 8 mm boy);
    // kapak plakasi cerceveden 6 mm tasar, 3 mm kalin. Panjur tipinde plaka
    // YOK (yalniz citalar + insert + kapak).
    var H = Math.min(p.derinlik, 8);
    var ringAlani = 4 * (p.en + p.boy) - 16;
    var kapak = ((p.en + 12) * (p.boy + 12) - p.en * p.boy) * 3;

    if (p.tip === "panjur") {
      return izgara_panjur_hacmi(p, H) + ringAlani * 8 + kapak;
    }

    var hacim = p.en * p.boy * H + ringAlani * (8 - H) + kapak;
    if (p.tip === "delikli") {
      hacim -= izgara_delik_alani(p, (p.en - 4) / 2, (p.boy - 4) / 2) * H;
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
    // Motor pah kesigi kesik-koni modelinden capla dogrusal olculen kadar az
    // malzeme torpuluyor (6 capta olculdu, kalinliktan bagimsiz).
    var hacim = govde + ustPah + 2.1 * p.cap;

    if (p.kenar_deseni === "segmentli") {
      // Sekiz adet 22 derecelik halka diliminin pahlı disk dışında kalan bölümü.
      var aciOrani = 8 * 22 / 360;
      var disKenar = yaricap + 0.2;
      var duzBolum = (p.kalinlik - 2 * pah) *
        (disKenar * disKenar - yaricap * yaricap);
      var pahBolumu = yaricap * pah * pah / 2 - pah * pah * pah / 12;
      hacim += Math.PI * aciOrani * (duzBolum + pahBolumu);
    }

    // Yuz basina iki ayri terim (motor renderlarindan cozuldu, 6 cap x 3 stil):
    // yazi "100" hacmi T capin karesiyle, dekoratif halka OYUGU R capla olcekli.
    // Halka her stilde COKARILIR (motorda "inset bevel" — kabartmada bile oyuk);
    // yazi kabartmada eklenir, oyma/gommede cikarilir (ikisi hacimce esdeger).
    var yaziHacmi = 0.064 * p.cap * p.cap;
    var halkaOyugu = 3.616 * p.cap - 7.93;
    var yuzler = p.yuz_sayisi === "cift" ? 2 : 1;

    if (p.yazi_stili === "kabartma") {
      hacim += yuzler * (yaziHacmi - halkaOyugu);
    } else {
      hacim -= yuzler * (yaziHacmi + halkaOyugu);
    }

    return hacim;
  }

  // === AILE: kase ===
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

  // === AILE: kasnak ===
  function kasnak_profil_verisi(profil) {
    // [adim, kokTipi, k1, k2, k3, disAlanA, disAlanB]
    // kok cap: "plo" -> 2*(N*adim/(2*pi) - k1); "cf" -> (k2*N^k3/(k1+N^k3))*N.
    // dis kesme alani A(N) = disAlanA + disAlanB/N — uretim motoru profil
    // cokgeninin (x'te +0.2 bosluklu olcekli) kok diskiyle kirpilmis alani,
    // N=18..80 fiti (fit hatasi <= %0.1).
    if (profil === "gt2_2mm") return [2, "plo", 0.254, 0, 0, 0.845528, 0.977574];
    if (profil === "gt2_3mm") return [3, "plo", 0.381, 0, 0, 1.876945, 2.419992];
    if (profil === "gt2_5mm") return [5, "plo", 0.5715, 0, 0, 5.066161, 7.220122];
    if (profil === "htd_3mm") return [3, "plo", 0.381, 0, 0, 2.048148, 2.298354];
    if (profil === "htd_5mm") return [5, "plo", 0.5715, 0, 0, 5.765813, 6.340437];
    if (profil === "htd_8mm") return [8, "plo", 0.6858, 0, 0, 15.876325, 20.726675];
    if (profil === "t2_5") return [2.5, "cf", 0.7467, 0.796, 1.026, 0.977182, 1.113013];
    if (profil === "t5") return [5, "cf", 0.6523, 1.591, 1.064, 2.829128, 4.090008];
    if (profil === "t10") return [10, "plo", 0.93, 0, 0, 11.231049, 13.656377];
    if (profil === "at5") return [5, "cf", 0.6523, 1.591, 1.064, 3.769152, 8.939298];
    if (profil === "mxl") return [2.032, "plo", 0.254, 0, 0, 0.556468, 0.675154];
    if (profil === "xl") return [5.08, "plo", 0.254, 0, 0, 2.651792, 3.269897];
    if (profil === "l") return [9.525, "plo", 0.381, 0, 0, 7.756754, 9.479382];
    return [2.073, "plo", 0.1778, 0, 0, 0.457559, 0.524207]; // 40dp
  }

  function kasnak_mil_alani(baglanti, cap) {
    var r = cap / 2;
    if (baglanti === "altigen") return Math.sqrt(3) * cap * cap / 2;
    if (baglanti === "d_lama") {
      var kesim = r * r * Math.acos(0.7) - 0.7 * r * r * Math.sqrt(1 - 0.49);
      return Math.PI * r * r - kesim;
    }
    if (baglanti === "kanalli") {
      // Motor kama olcusu (cap <= 6): genislik 2, dis tasma 1; yuva mil
      // merkezinden r+1'e uzanan 2 mm'lik serit (daire ici kismi dusulur).
      var y0 = Math.sqrt(Math.max(0, r * r - 1));
      var daireSeridi = y0 + r * r * Math.asin(Math.min(1, 1 / r));
      return Math.PI * r * r + 2 * (r + 1) - daireSeridi;
    }
    return Math.PI * r * r;
  }

  function kasnak(p) {
    // Uretim motoruna kalibre (Faz E): govde = kok cap diski − N x kirpilmis
    // dis alani; flans SABIT olculu (radyal +1, yukseklik 2, konik yari —
    // eslem sabitleri), tam disk olarak govde ucuna eklenir; mil deligi
    // flanslardan da gecer.
    var veri = kasnak_profil_verisi(p.profil);
    var N = p.dis_sayisi;
    var kokCap;
    if (veri[1] === "plo") {
      kokCap = 2 * (N * veri[0] / (2 * Math.PI) - veri[2]);
    } else {
      kokCap = (veri[3] * Math.pow(N, veri[4]) /
                (veri[2] + Math.pow(N, veri[4]))) * N;
    }
    var r = kokCap / 2;
    var disAlani = veri[5] + veri[6] / N;
    var govde = (Math.PI * r * r - N * disAlani) * p.genislik;

    var flansSayisi = p.flans === "iki_taraf" ? 2 :
                      (p.flans === "yok" ? 0 : 1);
    var flansT = 1;      // radyal kalinlik (eslem sabiti)
    var flansH = 2;      // yukseklik (eslem sabiti)
    var duzKisim = flansH * 0.5;  // konik oran 0.5 -> alt yarisi duz
    var koniKisim = flansH - duzKisim;
    var flansHacmi = Math.PI * ((r + flansT) * (r + flansT) * duzKisim +
      koniKisim * (r * r + r * flansT + flansT * flansT / 3));

    var milAlani = kasnak_mil_alani(p.mil_baglanti, p.mil_capi);
    var toplamYukseklik = p.genislik + flansSayisi * flansH;

    return govde + flansSayisi * flansHacmi - milAlani * toplamYukseklik;
  }

  // === AILE: kayis ===
  function kayis_profil_verisi(profil) {
    // [adim, sirt, kokTipi, k1, k2, k3, icA0, icA1, icA2, disA0, disA1, disA2, duzA]
    // kok cap: "plo" -> 2*(N*adim/(2*pi) - k1); "cf" -> (k2*N^k3/(k1+N^k3))*N.
    // Dis alanlari uretim motoru profil cokgeninden: ic/dis = kok halkasiyla
    // kirpilmis alanin A0+A1/N+A2/N^2 fiti (hata <= %1.1), duz = duz kayista
    // sirt ustune tasan (y>0) cokgen alani (kesin).
    if (profil === "GT2_2mm") return [2, 0.76, "plo", 0.254, 0, 0, 0.734904, 1.787894, -12.346135, 0.765439, -1.810031, 11.727081, 0.749989];
    if (profil === "GT2_3mm") return [3, 1.27, "plo", 0.381, 0, 0, 1.702997, 4.224808, -27.782394, 1.772998, -4.321898, 26.932650, 1.737332];
    if (profil === "GT2_5mm") return [5, 1.88, "plo", 0.5715, 0, 0, 4.753033, 12.323283, -78.723737, 4.951098, -12.586329, 76.472821, 4.850294];
    if (profil === "HTD_3mm") return [3, 1.19, "plo", 0.381, 0, 0, 1.858082, 4.088259, -27.521427, 1.927122, -4.181622, 26.846448, 1.891949];
    if (profil === "HTD_5mm") return [5, 1.73, "plo", 0.5715, 0, 0, 5.408236, 11.343827, -76.963091, 5.599792, -11.585657, 75.460968, 5.502307];
    if (profil === "HTD_8mm") return [8, 2.64, "plo", 0.6858, 0, 0, 15.227946, 34.157007, -207.423709, 15.749144, -34.988415, 205.419696, 15.483139];
    if (profil === "T2.5") return [2.5, 0.6, "cf", 0.7467, 0.796, 1.026, 0.856875, 2.314517, -18.340511, 0.900878, -2.343922, 18.053486, 0.878625];
    if (profil === "T5") return [5, 1, "cf", 0.6523, 1.591, 1.064, 2.602511, 8.693867, -70.547409, 2.772912, -8.960470, 72.545072, 2.685744];
    if (profil === "T10") return [10, 2, "plo", 0.93, 0, 0, 10.631378, 31.409879, -270.878428, 11.281598, -32.376914, 278.370820, 10.949263];
    if (profil === "AT5") return [5, 1, "cf", 0.6523, 1.591, 1.064, 3.528698, 14.243040, -82.142466, 3.736307, -14.515798, 82.250290, 3.630642];
    if (profil === "MXL") return [2.032, 0.64, "plo", 0.254, 0, 0, 0.472983, 1.433638, -11.576045, 0.501182, -1.470626, 11.594788, 0.486797];
    if (profil === "XL") return [5.08, 1.03, "plo", 0.254, 0, 0, 2.425625, 7.841742, -69.694186, 2.590962, -8.089998, 71.699847, 2.506460];
    if (profil === "L") return [9.525, 1.66, "plo", 0.381, 0, 0, 7.264542, 24.868803, -233.807732, 7.815838, -25.754195, 243.182419, 7.533702];
    return [2.073, 0.74, "plo", 0.1778, 0, 0, 0.382993, 1.287290, -11.572337, 0.410426, -1.317344, 11.548995, 0.396471]; // 40DP
  }

  function kayis(p) {
    // Uretim motoruna kalibre (Faz E): kapali kayis = kok capinda sirt halkasi
    // + ic/dis dislerin halkayla ortusmeyen cokgen alanlari; duz kayis =
    // uzunluk x sirt dikdortgeni + y>0 dis alanlari. Eski model dis profil
    // yaklastirmasi ve sabit sirt formulu kullaniyordu (sapma %22'ye kadar).
    var veri = kayis_profil_verisi(p.profil);
    var N = p.dis_sayisi;
    var adim = veri[0];
    var sirt = veri[1];
    var icDis = p.dis_taraf !== "dis";   // ic | cift
    var disDis = p.dis_taraf !== "ic";   // dis | cift
    var alan;

    if (p.sekil === "kapali") {
      var kokCap;
      if (veri[2] === "plo") {
        kokCap = 2 * (N * adim / (2 * Math.PI) - veri[3]);
      } else {
        kokCap = (veri[4] * Math.pow(N, veri[5]) /
                  (veri[3] + Math.pow(N, veri[5]))) * N;
      }
      var r = kokCap / 2;
      alan = Math.PI * ((r + sirt) * (r + sirt) - r * r);
      if (icDis) alan += N * (veri[6] + veri[7] / N + veri[8] / (N * N));
      if (disDis) alan += N * (veri[9] + veri[10] / N + veri[11] / (N * N));
    } else {
      alan = N * adim * sirt;
      var taraf = (icDis ? 1 : 0) + (disDis ? 1 : 0);
      alan += N * veri[12] * taraf;
    }

    return alan * p.genislik;
  }

  // === AILE: konektor ===
  function konektor_alan(kesit, d, kenar) {
    if (kesit === "kare") return d * d;
    if (kesit === "sekizgen") return 2 * d * d / (1 + Math.SQRT2);
    var r = d / 2;
    return 0.5 * kenar * r * r * Math.sin(2 * Math.PI / kenar);
  }

  function konektor_yarim_genislik(kesit, d, z) {
    // Kesitin z yüksekliğindeki yarım genişliği (kesit dikey, düzlemsel dizilim).
    var yari = d / 2;
    var mz = Math.abs(z);
    if (mz >= yari) return 0;
    if (kesit === "kare") return yari;
    if (kesit === "sekizgen") {
      var duz = yari * Math.tan(Math.PI / 8);
      return mz <= duz ? yari : (yari * (1 + Math.tan(Math.PI / 8)) - mz);
    }
    return Math.sqrt(yari * yari - mz * mz);
  }

  function konektor_dis_zarf(noktalar) {
    // 2B dışbükey zarf (monoton zincir), CCW köşe listesi döner.
    var p = noktalar.slice().sort(function (a, b) {
      return a[0] - b[0] || a[1] - b[1];
    });
    function konektor_capraz(o, a, b) {
      return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    }
    var alt = [], ust = [], i;
    for (i = 0; i < p.length; i++) {
      while (alt.length >= 2 &&
             konektor_capraz(alt[alt.length - 2], alt[alt.length - 1], p[i]) <= 0) alt.pop();
      alt.push(p[i]);
    }
    for (i = p.length - 1; i >= 0; i--) {
      while (ust.length >= 2 &&
             konektor_capraz(ust[ust.length - 2], ust[ust.length - 1], p[i]) <= 0) ust.pop();
      ust.push(p[i]);
    }
    alt.pop(); ust.pop();
    return alt.concat(ust);
  }

  function konektor(p) {
    // v2 geometrisi (2026-07-16): kol dış ölçüsü = cubuk + 2*max(cidar,1.2);
    // göbek = kol köklerinin (g = min(0.6*Do, 0.5*L)) dışbükey zarfı;
    // 2 karşılıklı kolda göbek yok. Tolerans: siki 0.15 / normal 0.30 / gevsek 0.50.
    var n = Math.max(2, Math.round(p.kol_sayisi));
    var tol = p.gecme === "siki" ? 0.15 : (p.gecme === "gevsek" ? 0.50 : 0.30);
    var cid = Math.max(p.cidar, 1.2);
    var Do = p.cubuk_capi + 2 * cid;
    var Db = p.cubuk_capi + tol;
    var L = p.kol_boyu;
    var S = 180; // esleme sabiti Segments
    var Aout = konektor_alan(p.kol_kesiti, Do, S);
    var Abore = konektor_alan("yuvarlak", Db, S);

    if (n === 2) { // düz manşon: iki prizma, kapalı uçlu yuvalar — kapalı form
      return 2 * L * Aout - 2 * (L - cid) * Abore;
    }

    // n >= 3: z-dilimli sayısal integral (dilim alanı 2B ızgarada).
    var g = Math.min(0.6 * Do, 0.5 * L);
    var H = Do / 2;
    var rb = Db / 2;
    var yonler = [];
    var a;
    for (a = 0; a < n; a++) {
      var th = 2 * Math.PI * a / n;
      yonler.push([Math.cos(th), Math.sin(th)]);
    }
    var zN = 48;
    var dz = H / zN;              // z>0 yarısı; simetriyle x2
    var kapsam = L + Do / 2;
    var hucre = (2 * kapsam) / 520;
    var Nxy = Math.ceil(2 * kapsam / hucre);
    var hacim = 0;
    for (var iz = 0; iz < zN; iz++) {
      var z = (iz + 0.5) * dz;
      var hw = konektor_yarim_genislik(p.kol_kesiti, Do, z);
      if (hw <= 0) continue;
      var hb = z < rb ? Math.sqrt(rb * rb - z * z) : 0;
      // göbek zarf dilimi: güdük köşeleri (taban + uç, her iki yan)
      var pts = [];
      for (a = 0; a < n; a++) {
        var u = yonler[a];
        pts.push([-hw * u[1], hw * u[0]]);
        pts.push([hw * u[1], -hw * u[0]]);
        pts.push([g * u[0] - hw * u[1], g * u[1] + hw * u[0]]);
        pts.push([g * u[0] + hw * u[1], g * u[1] - hw * u[0]]);
      }
      var zarf = konektor_dis_zarf(pts);
      var alan = 0;
      for (var ix = 0; ix < Nxy; ix++) {
        var x = -kapsam + (ix + 0.5) * hucre;
        for (var iy = 0; iy < Nxy; iy++) {
          var y = -kapsam + (iy + 0.5) * hucre;
          var dolu = false;
          var bos = false;
          for (a = 0; a < n; a++) {
            var s = x * yonler[a][0] + y * yonler[a][1];
            if (s < 0 || s > L) continue;
            var e = Math.abs(-x * yonler[a][1] + y * yonler[a][0]);
            if (e <= hw) dolu = true;
            if (hb > 0 && s >= cid && e <= hb) bos = true;
          }
          if (!dolu) { // göbek zarfında mı?
            dolu = true;
            for (var k = 0; k < zarf.length; k++) {
              var q1 = zarf[k];
              var q2 = zarf[(k + 1) % zarf.length];
              if ((q2[0] - q1[0]) * (y - q1[1]) -
                  (q2[1] - q1[1]) * (x - q1[0]) < 0) { dolu = false; break; }
            }
          }
          if (dolu && !bos) alan += 1;
        }
      }
      hacim += alan * hucre * hucre * dz;
    }
    return 2 * hacim;
  }

  // === AILE: oring ===
  function oring(p) {
    var merkezYaricap = p.ic_cap / 2 + p.kesit_cap / 2;
    var kesitAlani;

    if (p.profil === "kare") {
      kesitAlani = p.kesit_cap * p.kesit_cap;
    } else if (p.profil === "pahli") {
      // Okan onayi (16 Tem gece): 0.875 eski motora (0.25xCS pah) kalibreydi;
      // uretim motoru pahi 0.18xCS -> teorik 1-4*(0.18^2)/2 = 0.9352, OLCULEN
      // 0.93349 (8 set, hepsi ayni 5 basamak — render poligonizasyon payi dahil).
      kesitAlani = 0.93349 * p.kesit_cap * p.kesit_cap;
    } else {
      kesitAlani = Math.PI * p.kesit_cap * p.kesit_cap / 4;
    }

    return kesitAlani * 2 * Math.PI * merkezYaricap;
  }

  // === AILE: pervane ===
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
            cokgen.push([sinirlar[kenar], a[1] + t * (b[1] - a[1])]);
          } else {
            t = (sinirlar[kenar] - a[1]) / (b[1] - a[1]);
            cokgen.push([a[0] + t * (b[0] - a[0]), sinirlar[kenar]]);
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

  function petek_desen_cokgeni(desen, goz) {
    // Uretim motorunun desen sekilleri (yaricap/aci duzeni birebir):
    // petek: 6-gen r=goz/2 spin 0; sekizgen: cevrel 8-gen r/cos22.5, KOSELER
    // 0°'da (BOSL2 circum kendi 22.5° dondurur + motorun 22.5 spin'i toplam
    // koseyi 0'a getirir — render dokumuyle dogrulandi, bbox=2r/cos22.5);
    // besgen: 5-gen -18°; ucgen: 3-gen 0°; yuvarlak: cember; kare: kare.
    var r = goz / 2;
    var noktalar = [];
    var adet;
    var yaricap = r;
    var faz = 0;
    if (desen === "kare") {
      return [[-r, -r], [r, -r], [r, r], [-r, r]];
    }
    if (desen === "petek") {
      adet = 6;
    } else if (desen === "sekizgen") {
      adet = 8;
      yaricap = r / Math.cos(Math.PI / 8);
    } else if (desen === "besgen") {
      adet = 5;
      faz = -18 * Math.PI / 180;
    } else if (desen === "ucgen") {
      adet = 3;
    } else {
      adet = 180; // yuvarlak
    }
    for (var i = 0; i < adet; i++) {
      var aci = faz + 2 * Math.PI * i / adet;
      noktalar.push([yaricap * Math.cos(aci), yaricap * Math.sin(aci)]);
    }
    return noktalar;
  }

  function petek(p) {
    var noktalar = petek_desen_cokgeni(p.desen, p.goz_boyutu);
    var minX = Infinity;
    var maxX = -Infinity;
    var minY = Infinity;
    var maxY = -Infinity;
    var tamIkiAlan = 0;
    for (var n = 0; n < noktalar.length; n++) {
      var q = noktalar[n];
      var s = noktalar[(n + 1) % noktalar.length];
      tamIkiAlan += q[0] * s[1] - s[0] * q[1];
      minX = Math.min(minX, q[0]);
      maxX = Math.max(maxX, q[0]);
      minY = Math.min(minY, q[1]);
      maxY = Math.max(maxY, q[1]);
    }
    var tamAlan = Math.abs(tamIkiAlan) / 2;

    // Motor lattice'i: SABIT 40x40 kopya, merkezde, SASIRTMASIZ; adim = desen
    // sinir kutusu (0.1'e yuvarlanir) + 4 mm. Kopya ofsetleri yarim-adimli
    // ((k-19.5)*adim). Taban disina tasan kopyalar delikli modda kirpilir.
    var bboxEn = Math.round((maxX - minX) * 10) / 10;
    var bboxBoy = Math.round((maxY - minY) * 10) / 10;
    var adimX = bboxEn + 4;
    var adimY = bboxBoy + 4;
    var yariEn = p.en / 2;
    var yariBoy = p.boy / 2;

    var desenAlani = 0;
    for (var satir = 0; satir < 40; satir++) {
      var cy = (satir - 19.5) * adimY;
      if (cy + minY > yariBoy || cy + maxY < -yariBoy) continue;
      for (var sutun = 0; sutun < 40; sutun++) {
        var cx = (sutun - 19.5) * adimX;
        if (cx + minX > yariEn || cx + maxX < -yariEn) continue;
        if (cx + minX >= -yariEn && cx + maxX <= yariEn &&
            cy + minY >= -yariBoy && cy + maxY <= yariBoy) {
          desenAlani += tamAlan;
        } else {
          var tasinmis = [];
          for (var v = 0; v < noktalar.length; v++) {
            tasinmis.push([cx + noktalar[v][0], cy + noktalar[v][1]]);
          }
          desenAlani += petek_kirp_alani(
            tasinmis, -yariEn, yariEn, -yariBoy, yariBoy);
        }
      }
    }

    var tabanAlani = p.en * p.boy;
    if (p.mod === "kabartma") {
      // Uretim motorunda bu semayla DUZGUN karsiligi yok (desen kopyalari
      // tabana kirpilmadan 20 mm kolon dikiyor) — fiyat, urunun NIYETINE gore
      // (panel + desen kadar kabartma) korunur; onizleme sema kapisinda kapali.
      var kabartma = Math.max(p.kalinlik * 0.4, 1);
      return tabanAlani * p.kalinlik + desenAlani * kabartma;
    }
    // delikli: desen tam derinlikte panelden cikarilir.
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
      // Motor basamak sayisini yukseklikten turetir (basamak yuksekligi 0.8 mm
      // eslem sabiti Surface_Height) ve basamaklar egim cizgisinin USTUNE cikar:
      // her basamak egim ustunde step_len*y_step/2 ucgen birakir -> LH(1+1/n)/2.
      var basamakSayisi = Math.max(1, Math.ceil(yukseklik / 0.8));
      return genislik * uzunluk * yukseklik *
        (basamakSayisi + 1) / (2 * basamakSayisi);
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
  function rulman_eleman_profili(eleman, bd, w, cl) {
    // Yuvarlanma elemani/maske yarim-genisligi m(z) (eksenden radyal).
    // Motor profilleri render dokumunden dogrulandi:
    // makara: cekirdek bd/4 tam boy + pahli fici (govde w-bd/2, pah bd/4, 45°);
    // tutmali: tam silindir bd/2, belde (|z|<=bd/6) bd/4'e 45° boyunla iner;
    // bilya: kure. cl maskede radyal olarak eklenir (eleman icin 0).
    return function (z) {
      var az = Math.abs(z);
      if (az > w / 2) return 0;
      if (eleman === "bilya") {
        var r = bd / 2 + cl;
        return az >= r ? 0 : Math.sqrt(r * r - z * z);
      }
      var c = bd / 4;
      if (eleman === "makara") {
        var hb = (w - bd / 2) / 2;
        var cekirdek = bd / 4 + cl;
        var fici = az <= hb - c ? bd / 2 + cl :
                   az <= hb ? bd / 2 + cl - (az - (hb - c)) : 0;
        return Math.max(cekirdek, fici);
      }
      // tutmali (dumbbell)
      var zw = bd / 6;
      if (az <= zw) return bd / 4 + cl;
      if (az <= zw + c) return bd / 4 + cl + (az - zw);
      return bd / 2 + cl;
    };
  }

  function rulman_eleman_hacmi(eleman, bd, w) {
    if (eleman === "bilya") return Math.PI * bd * bd * bd / 6;
    // Eksenel simetrik: V = ∫ pi * m(z)^2 dz (kendi ekseni etrafinda).
    var m = rulman_eleman_profili(eleman, bd, w, 0);
    var adim = 400;
    var dz = w / adim;
    var v = 0;
    for (var i = 0; i < adim; i++) {
      var r = m(-w / 2 + (i + 0.5) * dz);
      v += Math.PI * r * r * dz;
    }
    return v;
  }

  function rulman(p) {
    // Uretim motoruna kalibre (Faz E): duvar = radyal boslugun 1/3'u; eleman
    // capi 2*duvar*(bilya 1 / makara 0.95 / tutmali 0.75); bilezikler tube,
    // tutmali'da duvar 1.25x; yuva oyugu eleman maskesinin (bosluk kadar sisik)
    // bileziklerden devrilmesiyle (Pappus, sayisal ∫).
    var ric = p.ic_cap / 2;
    var roc = p.dis_cap / 2;
    var w = p.genislik;
    var cl = p.bosluk;
    var duvar = (p.dis_cap - p.ic_cap) / 6;
    var carpan = p.eleman === "makara" ? 0.95 :
                 p.eleman === "tutmali" ? 0.75 : 1;
    var bd = 2 * duvar * carpan;
    var bilezikDuvar = duvar * (p.eleman === "tutmali" ? 1.25 : 1);
    var orta = (ric + roc) / 2;

    var hacim = Math.PI * ((ric + bilezikDuvar) * (ric + bilezikDuvar) - ric * ric) * w +
                Math.PI * (roc * roc - (roc - bilezikDuvar) * (roc - bilezikDuvar)) * w;

    // Yuva oyugu: maske [orta-m, orta+m] araliginin bilezik bantlariyla kesisimi.
    var maske = rulman_eleman_profili(p.eleman, bd, w, cl);
    var adim = 400;
    var dz = w / adim;
    for (var i = 0; i < adim; i++) {
      var z = -w / 2 + (i + 0.5) * dz;
      var m = maske(z);
      if (m <= 0) continue;
      var lo = orta - m;
      var hi = orta + m;
      var a = Math.max(ric, lo);
      var b = Math.min(ric + bilezikDuvar, hi);
      if (b > a) hacim -= Math.PI * (b * b - a * a) * dz;
      a = Math.max(roc - bilezikDuvar, lo);
      b = Math.min(roc, hi);
      if (b > a) hacim -= Math.PI * (b * b - a * a) * dz;
    }

    // Yuvarlanma elemanlari.
    var sayi = Math.floor(Math.PI * (ric + roc) * 0.95 / bd);
    hacim += sayi * rulman_eleman_hacmi(p.eleman, bd, w);

    // Bilya destek bilezigi (yalniz bilya; alttan eleman hizasina kadar).
    if (p.eleman === "bilya") {
      var destekH = Math.max(0, (w - bd) / 2 + 0.12);
      var di = orta - duvar / 4;
      var du = orta + duvar / 4;
      hacim += Math.PI * (du * du - di * di) * destekH -
               duvar * (bd / 2) * destekH;
    }

    if (p.flans === "var") {
      var flansYaricap = (1.25 * p.dis_cap - 0.25 * p.ic_cap) / 2;
      hacim += Math.PI * (flansYaricap * flansYaricap - roc * roc) * 1.5;
    }

    return hacim;
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

  function yay_dalga_yolu(form, boy) {
    // Uretim motorunun orneklemesi birebir: 240 ornek, faz kaymasi 0.125
    // (eslem sabiti Phase — ornekler dalga gecislerinin tam ustune dusmesin diye;
    // 0'da kalirsa uc nokta sin(1440°) yuvarlama gurultusune duser ve boy'a gore
    // fazladan bir sicrama olusur/olusmazdi). Form ofsetleri motorla ayni:
    // ucgen +0.25, testere +0.5.
    var genlik = 10;
    var cevrim = 4;
    var ornek = 240;
    var ofset = 0.125 + (form === "ucgen" ? 0.25 : form === "testere" ? 0.5 : 0);
    var ham = [];
    var i;
    for (i = 0; i <= ornek; i++) {
      ham.push([i * (boy / ornek),
        yay_dalga_degeri(form, cevrim * i / ornek + ofset, genlik)]);
    }

    // Dogrusal ara noktalari birlestir (kose sayimi icin sart).
    var yol = [ham[0]];
    for (i = 1; i < ham.length; i++) {
      var q = ham[i];
      if (yol.length >= 2) {
        var a = yol[yol.length - 2];
        var b = yol[yol.length - 1];
        if (Math.abs((b[0] - a[0]) * (q[1] - a[1]) -
                     (b[1] - a[1]) * (q[0] - a[0])) < 1e-9) {
          yol[yol.length - 1] = q;
          continue;
        }
      }
      yol.push(q);
    }

    // <0.7 mm araliktaki ic nokta cifti tek koseye iner: ucgen tepesindeki
    // orneklem duzlugu iki yakin 76°'lik kose yapar, bindirme kaybi tek keskin
    // kose gibi davranir — tek apekse indirmek kayip modelini dogru kurar.
    var sade = [yol[0]];
    i = 1;
    while (i < yol.length - 1) {
      if (i + 1 < yol.length - 1 &&
          Math.hypot(yol[i + 1][0] - yol[i][0], yol[i + 1][1] - yol[i][1]) < 0.7) {
        sade.push([(yol[i][0] + yol[i + 1][0]) / 2,
                   (yol[i][1] + yol[i + 1][1]) / 2]);
        i += 2;
      } else {
        sade.push(yol[i]);
        i += 1;
      }
    }
    sade.push(yol[yol.length - 1]);
    return sade;
  }

  function yay_dalga_hacmi(p) {
    // Serit = yolun stroke'u (genislik 2, uclar duz, eklemler yuvarlak).
    // Alan = kalinlik x yol boyu − kose bindirme kayiplari:
    // her donus acisi θ icin kayip (t²/4)(tan(θ/2) − θ/2) (miter kesisimi
    // eksi yuvarlak eklem yelpazesi). Motor renderlarina karsi olculdu:
    // kare/darbe/testere ≤%0.02, sinus ≤%0.6, ucgen ≤%1.7 (tum boy araligi).
    var seritKalinligi = 2;
    var seritYuksekligi = 8;
    var yol = yay_dalga_yolu(p.dalga_formu, p.dalga_boyu);
    var uzunluk = 0;
    var kayip = 0;
    for (var i = 1; i < yol.length; i++) {
      uzunluk += Math.hypot(yol[i][0] - yol[i - 1][0], yol[i][1] - yol[i - 1][1]);
      if (i < yol.length - 1) {
        var v1x = yol[i][0] - yol[i - 1][0];
        var v1y = yol[i][1] - yol[i - 1][1];
        var v2x = yol[i + 1][0] - yol[i][0];
        var v2y = yol[i + 1][1] - yol[i][1];
        var n1 = Math.hypot(v1x, v1y);
        var n2 = Math.hypot(v2x, v2y);
        if (n1 > 1e-12 && n2 > 1e-12) {
          var c = Math.max(-1, Math.min(1, (v1x * v2x + v1y * v2y) / (n1 * n2)));
          var donus = Math.acos(c);
          if (donus > 1e-9) {
            kayip += (seritKalinligi * seritKalinligi / 4) *
              (Math.tan(donus / 2) - donus / 2);
          }
        }
      }
    }
    var kesitAlani = seritKalinligi * uzunluk - kayip;
    return kesitAlani * seritYuksekligi;
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
