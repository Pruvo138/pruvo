function toka(p) {
  // TOKA v6 — yan-birakmali toka (YENI mekanizma: rijit merkez ray + iki esnek
  // prong/barb). parca="ikisi" = erkek + disi TAM urun (musterinin aldigi cift), mm3.
  //
  // ESKI MODEL EMEKLI: eski 3-param (kemer_kalinligi yuvasi) geometrisi + hinge
  // modeli ARTIK GECERSIZ; scad sifirdan yazildi. Yeni parametreler:
  //   W = kemer_genisligi (12..45, vars 25) ; H = kalinlik (8..14, vars 10.8)
  //   kayis_baglanti = "dikis" | "triglide"  (triglide = ikinci strap yuvasi)
  //
  // OLCUM: 56 GERCEK OpenSCAD render (fn=48, parca="ikisi"), 2026-07-26.
  //   W(kemer_genisligi) = 12,16,20,25,30,37,45  x  H = 8,10.8,12,14  x  {dikis,triglide}
  //   Uretici: olcum/toka_v6_izgara_olcum.py -> olcum/toka_v6_izgara.json
  //            olcum/toka_v6_model_uydur.py  (agirlikli 1/V Householder QR)
  //   BAGIMSIZ dogrulama (fit izgarasinda OLMAYAN 40 nokta,
  //   W=13,14,22,33,41 x H=8.6,9.4,11.4,13.2): olcum/toka_v6_model_dogrula.py
  //   EN KOTU SAPMA (56 fit + 40 bagimsiz): |sapma| < 1e-6% — geometri KAPALI-FORM
  //   olarak parca-parca DOGRUSAL_EXTRUDE oldugundan hacim (W,H)'de TAM iki-dogrusal.
  //
  // NEDEN "d" (rail-doyma dizi) TERIMI VAR: erkek merkez rayinin yarim genisligi
  //   rail_half = min(ray_genislik/2, (W+1.2)/2 - prong_et - 1.5)
  // W buyudukce ray_genislik/2'de SATURE olur. Doyma noktasi (diz) UYDURULMAZ,
  // toka.scad sabitlerinden TURETILIR:
  //   (W+1.2)/2 - prong_et - 1.5 = ray_genislik/2
  //   => W_DIZ = ray_genislik + 2*prong_et + 3.0 - 1.2 = 6.2 + 5.0 + 3.0 - 1.2 = 13.0
  // W < W_DIZ'de (izgarada yalniz W=12; sema adim=1 min=12 -> tek alt-diz deger)
  // ray inceldigi icin hacim dogrudan azalir; d = max(0, 13 - W) + d*H bu eksigi
  // (H'de dogrusal, erkek_h = H-4) TAM tasir. ray_genislik/prong_et degisirse
  // 13.0 sabiti YENIDEN turetilir (olcum/toka_v6_model_dogrula.py makine denetler).
  //
  // triglide: t*{1,W,H,W*H} — ikinci strap yuvasi ~ (W-0.8) x 4.2 kesit x H;
  // hakim terim t*W*H (yuva alani x yukseklik). dikis'te t=0, capayi ETKILEMEZ.
  //
  // CAPA: W=25,H=10.8,dikis -> 13039.492563026683 mm3 = tabanHacimMm3 (TAM esitlik).
  // Sabit terim, diger katsayilar 6 basamaga YUVARLANDIKTAN SONRA capayi tam
  // tutacak sekilde cozuldu; bu yuzden tam basamakli yazilir (yuvarlanirsa capa kayar).
  var W = p.kemer_genisligi;
  var H = p.kalinlik;
  var t = (p.kayis_baglanti === "triglide") ? 1 : 0;
  var d = Math.max(0, 13.0 - W);   // rail-doyma dizi (W_DIZ scad'den turev, yukari bak)

  return -934.9112469733172
    + 77.038 * W
    + 500.597575 * H
    + 24.6 * W * H
    + 113.58 * d
    - 28.02 * d * H
    - 0.444699 * t
    + 0.58 * t * W
    + 4.446992 * t * H
    - 5.8 * t * W * H;
}
