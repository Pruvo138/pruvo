function toka(p) {
  // TOKA v6 — yan-birakmali toka. parca="ikisi" = erkek + disi TAM urun
  // (musterinin aldigi cift), mm3.
  //
  // GEOMETRI (2026-07-26 guncelleme): ERKEK kayis ucu artik DAIMA 2-yuvali
  //   weave-through + egimli surtunme bari (erkek referans modeli; isletme onayladi).
  //   Kilit mekanizmasi (ray/prong/barb/soket/pencere) DEGISMEDI.
  //   Parametreler:  W = kemer_genisligi (12..45, vars 25) ; H = kalinlik
  //   (8..14, vars 10.8) ; kayis_baglanti = "dikis" | "triglide".
  //
  //   DIKKAT — kayis_baglanti ARTIK YALNIZ DISI kayis ucunu degistirir:
  //   dikis = tek yuva, triglide = ikinci disi strap yuvasi (~ -833 mm3 ort,
  //   capada ~ -759 mm3). ERKEK her iki degerde de aynidir (daima 2-yuva).
  //   Bu yuzden t-terimi (eskiden erkek+disi ikinci yuva) KUCULDU (~yari):
  //   simdi yalniz disi ikinci yuvasini tasir. dikis'te t=0, capayi ETKILEMEZ.
  //
  // OLCUM: 56 GERCEK geometri render'i (fn=48, parca="ikisi"), 2026-07-26.
  //   W(kemer_genisligi) = 12,16,20,25,30,37,45  x  H = 8,10.8,12,14  x  {dikis,triglide}
  //   Uretici: toka v6 izgara olcumu -> izgara verisi
  //            model uydurma calismasi (agirlikli 1/V Householder QR)
  //   BAGIMSIZ dogrulama (fit izgarasinda OLMAYAN 40 nokta,
  //   W=13,14,22,33,41 x H=8.6,9.4,11.4,13.2): model dogrulama calismasi
  //   EN KOTU SAPMA (56 fit noktasi) = +0.0689%. Erkek egimli bar ~H^2 egrilik
  //   getirir ama H araligi (8..14) dar oldugundan iki-dogrusal+diz modeli
  //   0.07%'de sogurur (H^2 terimi GEREKMEZ).
  //
  // NEDEN "d" (rail-doyma dizi) TERIMI VAR: erkek merkez rayinin yarim genisligi
  //   rail_half = min(ray_genislik/2, (W+1.2)/2 - prong_et - 1.5)
  // W buyudukce ray_genislik/2'de SATURE olur. Doyma noktasi (diz) UYDURULMAZ,
  // toka uretim modelinin sabitlerinden TURETILIR (kilit DEGISMEDI -> diz AYNI):
  //   (W+1.2)/2 - prong_et - 1.5 = ray_genislik/2
  //   => W_DIZ = ray_genislik + 2*prong_et + 3.0 - 1.2 = 6.2 + 5.0 + 3.0 - 1.2 = 13.0
  // W < W_DIZ'de (izgarada yalniz W=12) ray inceldigi icin hacim azalir; d =
  //   max(0, 13 - W) + d*H bu eksigi (H'de dogrusal) TAM tasir. ray_genislik/
  //   prong_et degisirse 13.0 sabiti YENIDEN turetilir (model dogrulama calismasi denetler).
  //
  // CAPA: W=25,H=10.8,dikis -> 14877.48271244191 mm3 = tabanHacimMm3 (TAM esitlik).
  // Sabit terim, diger katsayilar 6 basamaga YUVARLANDIKTAN SONRA capayi tam
  // tutacak sekilde cozuldu; bu yuzden tam basamakli yazilir (yuvarlanirsa capa kayar).
  var W = p.kemer_genisligi;
  var H = p.kalinlik;
  var t = (p.kayis_baglanti === "triglide") ? 1 : 0;
  var d = Math.max(0, 13.0 - W);   // rail-doyma dizi (W_DIZ uretim modelinden turev, yukari bak)

  return -943.7117961580916
    + 79.989293 * W
    + 571.671042 * H
    + 28.323759 * W * H
    + 113.667211 * d
    - 28.028087 * d * H
    - 0.025902 * t
    + 0.001953 * t * W
    + 2.2259 * t * H
    - 2.900181 * t * W * H;
}
