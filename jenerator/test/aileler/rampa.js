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
    // Motor tirtigi AYRIK bir prizma DEGIL: egim cizgisinin normali boyunca
    // uygulanan surekli sinus dalgasi (tepe = eslem sabiti Surface_Height 0,8 mm;
    // Rib_Profile = 1). Tam periyot sayisinca uygulandigi icin dalganin ortalama
    // yuksekligi tam olarak tepe/2'dir -> egim cizgisinin her mm'sine eklenen
    // kesit 0,8/2 = 0,4 mm2. Tirtik SAYISI ve araligi hacme GIRMEZ.
    //
    // 🔴 BIRIM UYARISI (olculdu 3 Agu 2026, 42 nokta + 300'luk supurme):
    // eski kod hacmi "tirtik basina sabit kesit" olarak yazmisti. O birimde
    // geri hesaplanan kesit 1,193-1,424 mm2 arasinda SALINIR ve tek bir sabit
    // TUTMAZ; cunku ek malzeme EGIM boyu ile, tirtik sayisi ise X ekseninde
    // (round(uzunluk/3)) tanimli. Salinimin kapali formu 0,4*egim/round(L/3)
    // (artik %0,000018) — yani salinim olcum gurultusu degil BIRIM HATASIYDI.
    // Dogru birimde (egim-mm basina) sabit 0,400000 ve yayilim 1,2e-07'dir.
    var egimBoyu = Math.sqrt(uzunluk * uzunluk + yukseklik * yukseklik);
    hacim += genislik * 0.4 * egimBoyu;
  }

  return hacim;
}
