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
