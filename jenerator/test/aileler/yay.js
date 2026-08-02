function yay_dalga_degeri(form, faz, genlik) {
  var f = faz - Math.floor(faz);
  if (form === "sinus") return genlik * Math.sin(2 * Math.PI * faz);
  if (form === "ucgen") return genlik * (f < 0.5 ? 4 * f - 1 : 3 - 4 * f);
  if (form === "testere") return genlik * (2 * f - 1);
  if (form === "darbe") return genlik * (f < 0.3 ? 1 : -1);
  return genlik * (f < 0.5 ? 1 : -1);
}

// KOD KAYNAGI: kalibrasyon kaynagindaki ayni aile fonksiyonu. Kod govdesi (yorum
// disi her satir) BAYT-OZDES tutulur; kalibrasyon senkron testi ayrismayi DAVRANIS
// ekseninde olcer. Yorumlar farklidir: yayin ic-dil kapisi bu dosyada ic yol/arac
// adi tasinmasina izin vermez. Yorumlardaki sayilar BU depoda olculmustur.
// 3 Agu 2026 — IKIZ TANIM AYRISMASI: kalibrasyon kaynagi bu modeli tasirken bu
// depodaki kopya eski (240 ornekli, faz kaymali, bandi duz kabul eden) surumde
// kalmisti; kalibrasyon senkron testinin aile listesinde `yay` YOKTU, yani
// ayrisma hicbir kapiyi yakmiyordu. Duzeltmeyle birlikte `yay` o listeye eklendi.

// Uretim geometrisi seridi 16 kenarli DUZGUN COKGEN ile suprur, cember ile DEGIL.
// Bir segmentin suprudugu bandin genisligi cokgenin o dogrultudaki destek
// genisligidir:
// 2r*cos(delta), delta = dogrultunun en yakin kose acisina uzakligi (0..11.25 derece).
// Yataya/dikeye paralel segmentte tam 2r, 11.25 derecede en dar (2r*0.98079).
// (Tepelerin 22,5° katlarinda oldugu render ile olculdu: yatay stadyumun alani
// L*2r + A16'ya, 11,25°'lik stadyumunki L*1,96157r'ye birebir oturuyor.)
function yay_16gen_genislik(aci, r, dilim) {
  var d = ((aci % dilim) + dilim) % dilim;
  return 2 * r * Math.cos(Math.min(d, dilim - d));
}

// Dalga govdesi: N segmentlik poligon zinciri; her segment iki komsu ornekteki
// 16-genin disbukey ortusu (hull); hepsinin BIRLESIMI dogrusal supurulur.
//
// Alan = SUM(kol_boyu * kol_genisligi) + A16 - SUM_kose(fazla_ortusme)
//
//   A16            : 16-gen alani — iki uctaki yarim baslik bir tam 16-gen eder.
//   fazla_ortusme  : komsu iki hull, paylastiklari 16-gen'in OTESINDE de ortusur.
//                    Iki kolun bandi (yari genislik a ve b) alfa ic acisiyla
//                    kesisir; kesisim bolgesi bir UCURTMA'dir, alani
//                    ((a+b)/2)^2 * cot(alfa/2). Bundan zaten sayilan 16-gen
//                    diliminin (A16 * sapma / 2pi) dususu gerekir.
//
// ORNEKLEME URETIM GEOMETRISIYLE BIREBIR: N = max(cevrim*40, 40), faz = cevrim*i/N.
// FAZ KAYMASI YOKTUR — bu depodaki eski surum 240 ornek + 0.125/0.25/0.5 ofset
// kullaniyordu; o ornekleme hicbir uretim yolunda YOK ve ucgen tepesini iki ornek
// ARASINA dusurup yolu kisaltiyordu (hacim eksik tahmin -> eksik tahsilat).
//
// OLCULDU (aile tarama surucusu, 810 noktalik deterministik sema izgarasi,
// 3 Agu 2026; gercek geometri olcumune karsi dal basina EN KOTU sapma, %):
//   ONCE  ucgen 3.800 · testere 1.192 · sinus 0.907 · kare 0.419 · darbe 0.419 · spiral 0.066
//   SONRA ucgen 0.004 · testere 0.002 · sinus 0.824 · kare 0.001 · darbe 0.001 · spiral 0.066
// Kalan sinus sapmasi (en kotu dalga_boyu=40'ta) MODELIN BILINEN SINIRIDIR: dik
// sinus tepesinde egrilik yaricapi serit yari kalinligindan kucuk dusuyor,
// komsu-OLMAYAN segmentler de ortusuyor; ardisik-cift bindirme modeli o fazlaligi
// dusmedigi icin hacim bir miktar FAZLA tahmin ediliyor.
function yay_dalga_hacmi(p) {
  var genlik = 10;
  var cevrim = 4;
  var seritKalinligi = 2;
  var seritYuksekligi = 8;
  var parcaSayisi = Math.max(cevrim * 40, 40); // uretim: N = max(cevrim*40, 40)
  var kenarSayisi = 16;                        // uretim: 16 kenarli kesit
  var r = seritKalinligi / 2;
  var dilim = 2 * Math.PI / kenarSayisi;
  var a16 = 0.5 * kenarSayisi * r * r * Math.sin(dilim);

  var dx = p.dalga_boyu / parcaSayisi;
  var alan = a16;
  // Ardisik DOGRUDAS segmentler tek "kol"da toplanir: kose duzeltmesi yalniz
  // gercek geometrik koselere uygulanmali (ucgen/kare/testere dalgasinin duz
  // kenari 20 alt-segmente bolunmustur; her birine kose saymak yanlis olur).
  var kolAci = [], kolBoy = [], kolGenislik = [];
  var onceki = yay_dalga_degeri(p.dalga_formu, 0, genlik);

  for (var i = 1; i <= parcaSayisi; i++) {
    var simdiki = yay_dalga_degeri(p.dalga_formu, cevrim * i / parcaSayisi, genlik);
    var dy = simdiki - onceki;
    onceki = simdiki;
    var boy = Math.sqrt(dx * dx + dy * dy);
    var aci = Math.atan2(dy, dx);
    var w = yay_16gen_genislik(aci + Math.PI / 2, r, dilim);
    alan += boy * w;
    var n = kolAci.length;
    if (n > 0 && Math.abs(aci - kolAci[n - 1]) < 1e-9) {
      kolBoy[n - 1] += boy;
    } else {
      kolAci.push(aci);
      kolBoy.push(boy);
      kolGenislik.push(w);
    }
  }

  for (var k = 1; k < kolAci.length; k++) {
    var sap = kolAci[k] - kolAci[k - 1];
    while (sap > Math.PI) sap -= 2 * Math.PI;
    while (sap < -Math.PI) sap += 2 * Math.PI;
    var sapma = Math.abs(sap);
    if (sapma < 1e-9) continue;
    var alfa = Math.PI - sapma;                       // iki kol arasi ic aci
    var abar = (kolGenislik[k - 1] + kolGenislik[k]) / 4;
    var ucurtma = alfa > 1e-9 ? abar * abar / Math.tan(alfa / 2) : Infinity;
    // KILIT: alfa -> 0 (tam katlanma) cot'u patlatir. Ortusme hicbir zaman kisa
    // komsu kolun KENDI bant alanini asamaz — bu geometrik ust siniri dayat.
    // Uretimde erisilmez (en sivri hal ucgen+dalga_boyu=40 -> alfa 0.49 rad,
    // ucurtma 4.0 mm2, tavan 41.2 mm2); yine de NaN/negatif hacim uretilemesin.
    var tavan = 2 * abar * Math.min(kolBoy[k - 1], kolBoy[k]);
    if (!(ucurtma <= tavan)) ucurtma = tavan;
    alan -= ucurtma - a16 * sapma / (2 * Math.PI);
  }

  return Math.max(alan, a16) * seritYuksekligi;
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
