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
