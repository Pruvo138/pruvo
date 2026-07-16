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
