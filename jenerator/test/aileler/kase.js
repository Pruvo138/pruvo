function kase_knob_hacmi(cap) {
  var yaricap = 6;
  var yukseklik = 18;
  var altYaricap = cap * 0.3;
  var ustYaricap = cap * 0.5;
  var dx = ustYaricap - altYaricap;
  var uzunluk = Math.sqrt(dx * dx + yukseklik * yukseklik);
  var ux = dx / uzunluk;
  var uz = yukseklik / uzunluk;
  var aci = Math.acos(ux);
  var teget = yaricap / Math.tan(aci / 2);
  var z1 = yukseklik / 2 - uz * teget;
  var r1 = ustYaricap - ux * teget;
  var merkezX = ustYaricap - teget;
  var merkezZ = yukseklik / 2 - yaricap;
  var ilkYukseklik = z1 + yukseklik / 2;
  var konik = Math.PI * ilkYukseklik *
    (altYaricap * altYaricap + altYaricap * r1 + r1 * r1) / 3;
  var u1 = z1 - merkezZ;
  var u2 = yaricap;

  function kase_knob_ilkel(u) {
    var kok = Math.sqrt(Math.max(0, yaricap * yaricap - u * u));
    return merkezX * merkezX * u +
      merkezX * (u * kok + yaricap * yaricap * Math.asin(u / yaricap)) +
      yaricap * yaricap * u - u * u * u / 3;
  }

  return konik + Math.PI * (kase_knob_ilkel(u2) - kase_knob_ilkel(u1));
}

// Liberation Sans Bold glif alanlari / boyut^2 (scad'de font SABIT; $fn=96
// sozlesme baglami). Olcum: olcum/glif_alan_kalibrasyon.py -> olcum/
// glif_alan.json (glif basina h=1 ekstruzyon; union = toplam, katkisallik
// farki %1e-8; sum(PRUVO)=2.122714 vs eski kd-farki katsayisi 2.122713403,
// fark %0.00003). Tabloda olmayan karakter ortalamaya duser.
function kase_glif_alani(metin) {
  var tablo = {"A":0.39286,"B":0.531008,"C":0.381789,"D":0.472175,"E":0.444764,"F":0.344743,"G":0.465826,"H":0.45118,"I":0.191144,"J":0.290963,"K":0.424581,"L":0.270406,"M":0.600179,"N":0.486681,"O":0.467561,"P":0.403865,"Q":0.543763,"R":0.493259,"S":0.418138,"T":0.286657,"U":0.417619,"V":0.34041,"W":0.635236,"X":0.376115,"Y":0.289144,"Z":0.362284,"a":0.328552,"b":0.393759,"c":0.259531,"d":0.393801,"e":0.30393,"f":0.235793,"g":0.446432,"h":0.363309,"i":0.166568,"j":0.232099,"k":0.346705,"l":0.191768,"m":0.472108,"n":0.310734,"o":0.319515,"p":0.397864,"q":0.396915,"r":0.174653,"s":0.284135,"t":0.210512,"u":0.310852,"v":0.260551,"w":0.425371,"x":0.266467,"y":0.316534,"z":0.250064,"0":0.377523,"1":0.281619,"2":0.34688,"3":0.351378,"4":0.338063,"5":0.37411,"6":0.391073,"7":0.253472,"8":0.416585,"9":0.398715,"Ç":0.42725,"Ğ":0.520815,"İ":0.217891,"Ö":0.506938,"Ş":0.463548,"Ü":0.456996,"ç":0.305021,"ğ":0.506768,"ı":0.139812,"ö":0.36292,"ş":0.329554,"ü":0.354257,".":0.040535,",":0.065,":":0.074562,";":0.098969,"!":0.154192,"?":0.248947,"'":0.057689,"-":0.05835,"_":0.042214,"(":0.245393,")":0.24516,"/":0.168658,"+":0.190594,"*":0.141701,"=":0.209691,"&":0.43712,"%":0.493788,"#":0.295697,"@":0.551746," ":0.0};
  var ortalama = 0.33099;
  var toplam = 0;
  for (var i = 0; i < metin.length; i++) {
    var k = tablo[metin.charAt(i)];
    toplam += (k === undefined) ? ortalama : k;
  }
  return toplam;
}

function kase(p) {
  // Metin siparis metnidir; gelmezse sema varsayilani (taban sozlesmesi).
  var metin = (typeof p.metin === "string") ? p.metin : "PRUVO";
  var ys = p.yazi_boyutu;
  var yukseklik = 8;
  var pah = 2.5;
  // scad oto-boyut: _wc = max(len*ys*0.62, 2*ys); _hc = 2.6*ys (texticon 2
  // satir sayilir). Eski model _wc'yi 3.1*ys'e (len=5, "PRUVO") sabitlemisti —
  // metin-izgara olcumunde -%93.6..+%50 sapma (olcum/metin_etki_olcum.json).
  // face_w2=max(...,15) kelepcesi sema araliginda pasif (ys>=6, dolgu>=3 -> >=18).
  var icerikEn = Math.max(0.62 * metin.length, 2) * ys;
  var icerikBoy = 2.6 * ys;
  var en, boy;
  if (p.bicim === "dikdortgen") {
    en = icerikEn + 2 * p.dolgu;
    boy = icerikBoy + 2 * p.dolgu;
  } else {
    en = Math.max(icerikEn, icerikBoy) + 2 * p.dolgu;
    boy = en;
  }
  var taban;

  if (p.bicim === "yuvarlak") {
    var altYaricap = en / 2;
    var ustYaricap = altYaricap - 2;
    var egimUzunlugu = Math.sqrt(yukseklik * yukseklik + 4);
    var araYaricap = ustYaricap + pah * 2 / egimUzunlugu;
    var araYukseklik = yukseklik - pah * yukseklik / egimUzunlugu;
    var tepeYaricap = ustYaricap - pah;
    taban = Math.PI * araYukseklik *
      (altYaricap * altYaricap + altYaricap * araYaricap + araYaricap * araYaricap) / 3;
    taban += Math.PI * (yukseklik - araYukseklik) *
      (araYaricap * araYaricap + araYaricap * tepeYaricap + tepeYaricap * tepeYaricap) / 3;
  } else {
    taban = yukseklik * (en * boy - 2 * en - 2 * boy + 16 / 3) -
      2 * pah * pah * yukseklik;
  }

  // Rolyef union'la eklenir; taban ayak izinden tasan glif de hacme sayilir
  // (kirpilma YOK) -> tam glif alani x derinlik.
  var rolyef = kase_glif_alani(metin) * ys * ys * p.kabartma_derinligi;
  var toplam = taban + rolyef;

  if (p.sap === "sapli") {
    var topuzCapi = Math.max(en * 0.7, 22);
    // Dişli mil, gövde yuvası ve topuzla örtüşen bölümün kalibre edilmiş net etkisi.
    toplam += kase_knob_hacmi(topuzCapi) - 210.720722018491;
  }

  return toplam;
}
