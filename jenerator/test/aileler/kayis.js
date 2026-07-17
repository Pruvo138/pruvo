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
