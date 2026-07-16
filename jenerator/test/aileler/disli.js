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
