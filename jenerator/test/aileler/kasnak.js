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
