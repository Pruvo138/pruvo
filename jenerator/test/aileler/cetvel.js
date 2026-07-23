function cetvel_rakam_alani(uzunluk, boyut) {
  // Aralık 10–50 olduğundan 0..uzunluk etiketlerindeki toplam rakam sayısı 2n-8'dir.
  return 0.17 * boyut * boyut * (2 * uzunluk - 8);
}

function cetvel_isaret_alani(p, kenarIsareti) {
  var n = p.uzunluk;
  var w = p.genislik;
  var inc = p.sistem === "inc";
  var katsayi;
  var yaziBoyutu;

  if (kenarIsareti) {
    katsayi = inc ? 1.165 * n + 0.2 : 0.805 * n + 0.2;
    yaziBoyutu = Math.min(0.2 * w, 4);
  } else {
    katsayi = inc ? 1.323 * n + 0.315 : 0.909 * n + 0.315;
    yaziBoyutu = Math.min(0.22 * w, 4.5);
  }

  return w * katsayi + cetvel_rakam_alani(n, yaziBoyutu);
}

// Liberation Sans (Regular) glif alan + ilerleme tablolari (cetvel.scad text
// cagrilari $fn=24). Olcum: olcum/glif_alan_kalibrasyon.py ->
// olcum/glif_alan.json. Alan boyut^2, ilerleme boyut basina mm (OpenSCAD
// text olcegi em x 1.389). Tabloda olmayan karakter ortalamalara duser.
function cetvel_glif_tablolari() {
  return {
    alan: {"A":0.275255,"B":0.358221,"C":0.26546,"D":0.32823,"E":0.310595,"F":0.238968,"G":0.324796,"H":0.303573,"I":0.123754,"J":0.189104,"K":0.279904,"L":0.174831,"M":0.412963,"N":0.332577,"O":0.327259,"P":0.277551,"Q":0.375278,"R":0.340273,"S":0.291066,"T":0.192548,"U":0.277377,"V":0.23715,"W":0.435518,"X":0.252248,"Y":0.19704,"Z":0.255917,"a":0.244259,"b":0.270537,"c":0.17513,"d":0.2705,"e":0.229457,"f":0.154087,"g":0.309289,"h":0.24054,"i":0.103805,"j":0.147198,"k":0.232623,"l":0.122834,"m":0.316115,"n":0.206814,"o":0.216664,"p":0.271804,"q":0.273989,"r":0.113973,"s":0.198656,"t":0.137197,"u":0.206809,"v":0.171826,"w":0.29267,"x":0.177657,"y":0.211666,"z":0.181752,"0":0.265993,"1":0.190888,"2":0.231968,"3":0.248559,"4":0.232723,"5":0.260322,"6":0.275586,"7":0.167786,"8":0.296362,"9":0.281074,"Ç":0.301384,"Ğ":0.365971,"İ":0.137991,"Ö":0.355013,"Ş":0.327007,"Ü":0.30513,"ç":0.211089,"ğ":0.358379,"ı":0.089559,"ö":0.244418,"ş":0.234573,"ü":0.234563,".":0.019637,",":0.033204,":":0.037122,";":0.05069,"!":0.097977,"?":0.170657,"'":0.033102,"-":0.036788,"_":0.071321,"(":0.157958,")":0.157977,"/":0.110659,"+":0.124667,"*":0.092655,"=":0.135434,"&":0.317111,"%":0.35681,"#":0.226852,"@":0.509982," ":0.0},
    ilerleme: {"A":0.92638,"B":0.92638,"C":1.00301,"D":1.00301,"E":0.92638,"F":0.84839,"G":1.08032,"H":1.00301,"I":0.38588,"J":0.69445,"K":0.92638,"L":0.77243,"M":1.15696,"N":1.00301,"O":1.08032,"P":0.92638,"Q":1.08032,"R":1.00301,"S":0.92638,"T":0.84839,"U":1.00301,"V":0.92638,"W":1.3109,"X":0.92638,"Y":0.92638,"Z":0.84839,"a":0.77243,"b":0.77243,"c":0.69445,"d":0.77243,"e":0.77243,"f":0.36079,"g":0.77243,"h":0.77243,"i":0.30857,"j":0.30857,"k":0.69445,"l":0.30857,"m":1.15696,"n":0.77243,"o":0.77243,"p":0.77243,"q":0.77243,"r":0.46251,"s":0.69445,"t":0.38588,"u":0.77243,"v":0.69445,"w":1.00301,"x":0.69445,"y":0.69445,"z":0.69445,"0":0.77243,"1":0.66935,"2":0.77243,"3":0.77243,"4":0.77243,"5":0.77243,"6":0.77243,"7":0.77243,"8":0.77243,"9":0.77243,"Ç":1.00301,"Ğ":1.08032,"İ":0.38588,"Ö":1.08032,"Ş":0.92638,"Ü":1.00301,"ç":0.69445,"ğ":0.77243,"ı":0.38588,"ö":0.77243,"ş":0.69445,"ü":0.77243,".":0.38588,",":0.38588,":":0.38588,";":0.38588,"!":0.38588,"?":0.77243,"'":0.26516,"-":0.46251,"_":0.77243,"(":0.46251,")":0.46251,"/":0.38588,"+":0.81109,"*":0.5405,"=":0.81109,"&":0.92638,"%":1.23495,"#":0.77243,"@":1.40991," ":0.38588},
    alanOrt: 0.228089,
    ilerlemeOrt: 0.762896
  };
}

// Ozel yazinin (yazi_logo) hacim katkisi. Yalniz duz cetvelde islenir
// (ucgen/l gonye _kenar_tik kullanir, logo yok). Kabartma union'la govde
// disina tasani da ekler (kirpilmaz); oyma/gomme farki govdeyle sinirlidir:
// [-Lx/2, +Lx/2] penceresi (halign=center, olcum: olcum/cetvel_klip_bak.py
// W dizisi ~%20 karakterde doyuyor, pencere modeli doyma alanini %0.2 icinde
// yakalar). Isaret derinligi etkin 0.59 (isaret_z 0.6, 0.01 bindirme).
function cetvel_yazi_hacmi(p) {
  var yazi = (typeof p.yazi === "string") ? p.yazi : "";
  if (p.tip !== "duz" || yazi.length === 0) return 0;
  var t = cetvel_glif_tablolari();
  var boyut = Math.min(0.22 * p.genislik, 5);
  var birimMm = p.sistem === "inc" ? 25.4 : 10;
  var yariPencere = (p.uzunluk * birimMm + 12) / 2;
  var kirp = p.isaret_stili !== "kabartma";

  var toplamIlerleme = 0;
  var i, c, adv;
  for (i = 0; i < yazi.length; i++) {
    c = yazi.charAt(i);
    adv = t.ilerleme[c];
    toplamIlerleme += (adv === undefined) ? t.ilerlemeOrt : adv;
  }
  var x = -toplamIlerleme * boyut / 2;
  var alan = 0;
  for (i = 0; i < yazi.length; i++) {
    c = yazi.charAt(i);
    var k = t.alan[c];
    if (k === undefined) k = t.alanOrt;
    adv = t.ilerleme[c];
    if (adv === undefined) adv = t.ilerlemeOrt;
    var genislik = adv * boyut;
    var oran = 1;
    if (kirp && genislik > 0) {
      var kesisim = Math.min(x + genislik, yariPencere) -
        Math.max(x, -yariPencere);
      oran = Math.max(0, Math.min(1, kesisim / genislik));
    }
    alan += k * boyut * boyut * oran;
    x += genislik;
  }
  return 0.59 * alan;
}

function cetvel(p) {
  var birimMm = p.sistem === "inc" ? 25.4 : 10;
  var a = p.uzunluk * birimMm;
  var w = p.genislik;
  var r = 3;
  var alan;
  var kenarIsareti = p.tip !== "duz";

  if (p.tip === "ucgen") {
    // Dış ve iç 45° üçgenlerde aynı köşe yarıçapı kullanıldığı için düzeltmeler yok olur.
    alan = 3 * a * a / 8;
  } else if (p.tip === "l_gonye") {
    // İki kolun birleşim alanı; beş dış köşedeki yuvarlatma ayrıca çıkarılır.
    alan = a * w + 0.6 * a * w - w * w;
    alan -= 5 * (1 - Math.PI / 4) * r * r;
  } else {
    alan = (a + 12) * w - (4 - Math.PI) * r * r;
  }

  var govdeHacmi = alan * p.kalinlik;
  var isaretHacmi = 0.59 * cetvel_isaret_alani(p, kenarIsareti);
  var yaziHacmi = cetvel_yazi_hacmi(p);
  return p.isaret_stili === "kabartma" ?
    govdeHacmi + isaretHacmi + yaziHacmi :
    govdeHacmi - isaretHacmi - yaziHacmi;
}
