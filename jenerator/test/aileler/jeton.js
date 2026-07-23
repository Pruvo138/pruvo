// Liberation Sans Bold glif alan + ilerleme tablolari ($fn=96 sozlesme
// baglami; jeton.scad _yuz2d $fn=96 pinli — eski $fn'siz tesselasyonda "100"
// katsayisi cap 20->80 arasinda 0.969->1.028 geziyordu). Olcum:
// olcum/glif_alan_kalibrasyon.py -> olcum/glif_alan.json. Alan boyut^2,
// ilerleme boyut basina mm (OpenSCAD text olcegi em x 1.389). Tabloda
// olmayan karakter ortalamalara duser.
function jeton_glif_tablolari() {
  return {
    alan: {"A":0.39286,"B":0.531008,"C":0.381789,"D":0.472175,"E":0.444764,"F":0.344743,"G":0.465826,"H":0.45118,"I":0.191144,"J":0.290963,"K":0.424581,"L":0.270406,"M":0.600179,"N":0.486681,"O":0.467561,"P":0.403865,"Q":0.543763,"R":0.493259,"S":0.418138,"T":0.286657,"U":0.417619,"V":0.34041,"W":0.635236,"X":0.376115,"Y":0.289144,"Z":0.362284,"a":0.328552,"b":0.393759,"c":0.259531,"d":0.393801,"e":0.30393,"f":0.235793,"g":0.446432,"h":0.363309,"i":0.166568,"j":0.232099,"k":0.346705,"l":0.191768,"m":0.472108,"n":0.310734,"o":0.319515,"p":0.397864,"q":0.396915,"r":0.174653,"s":0.284135,"t":0.210512,"u":0.310852,"v":0.260551,"w":0.425371,"x":0.266467,"y":0.316534,"z":0.250064,"0":0.377523,"1":0.281619,"2":0.34688,"3":0.351378,"4":0.338063,"5":0.37411,"6":0.391073,"7":0.253472,"8":0.416585,"9":0.398715,"Ç":0.42725,"Ğ":0.520815,"İ":0.217891,"Ö":0.506938,"Ş":0.463548,"Ü":0.456996,"ç":0.305021,"ğ":0.506768,"ı":0.139812,"ö":0.36292,"ş":0.329554,"ü":0.354257,".":0.040535,",":0.065,":":0.074562,";":0.098969,"!":0.154192,"?":0.248947,"'":0.057689,"-":0.05835,"_":0.042214,"(":0.245393,")":0.24516,"/":0.168658,"+":0.190594,"*":0.141701,"=":0.209691,"&":0.43712,"%":0.493788,"#":0.295697,"@":0.551746," ":0.0},
    ilerleme: {"A":1.00301,"B":1.00301,"C":1.00301,"D":1.00301,"E":0.92638,"F":0.84839,"G":1.08032,"H":1.00301,"I":0.38588,"J":0.77243,"K":1.00301,"L":0.84839,"M":1.15696,"N":1.00301,"O":1.08032,"P":0.92638,"Q":1.08032,"R":1.00301,"S":0.92638,"T":0.84839,"U":1.00301,"V":0.92638,"W":1.3109,"X":0.92638,"Y":0.92638,"Z":0.84839,"a":0.77243,"b":0.84839,"c":0.77243,"d":0.84839,"e":0.77243,"f":0.46251,"g":0.84839,"h":0.84839,"i":0.38588,"j":0.38588,"k":0.77243,"l":0.38588,"m":1.23495,"n":0.84839,"o":0.84839,"p":0.84839,"q":0.84839,"r":0.5405,"s":0.77243,"t":0.46251,"u":0.84839,"v":0.77243,"w":1.08032,"x":0.77243,"y":0.77243,"z":0.69445,"0":0.77243,"1":0.6958,"2":0.77243,"3":0.77243,"4":0.77243,"5":0.77243,"6":0.77243,"7":0.77243,"8":0.77243,"9":0.77243,"Ç":1.00301,"Ğ":1.08032,"İ":0.38588,"Ö":1.08032,"Ş":0.92638,"Ü":1.00301,"ç":0.77243,"ğ":0.84839,"ı":0.38588,"ö":0.84839,"ş":0.77243,"ü":0.84839,".":0.38588,",":0.38588,":":0.46251,";":0.46251,"!":0.46251,"?":0.84839,"'":0.33027,"-":0.46251,"_":0.77243,"(":0.46251,")":0.46251,"/":0.38588,"+":0.81109,"*":0.5405,"=":0.81109,"&":1.00301,"%":1.23495,"#":0.77243,"@":1.3543," ":0.38588},
    alanOrt: 0.33099,
    ilerlemeOrt: 0.794611
  };
}

// Metnin 2B alani (mm2). yariPencere null -> tam alan (kabartma union'la
// disk disina tasani da ekler). Sayi ise oyma/gomme kirpilmasi: govdeden
// cikarma yalniz [-yariPencere, +yariPencere] araliginda etkilidir
// (halign=center; glif basina dogrusal kesisim orani).
function jeton_yazi_alani(yazi, ts, yariPencere) {
  var t = jeton_glif_tablolari();
  var toplamIlerleme = 0;
  var i, c, adv;
  for (i = 0; i < yazi.length; i++) {
    c = yazi.charAt(i);
    adv = t.ilerleme[c];
    toplamIlerleme += (adv === undefined) ? t.ilerlemeOrt : adv;
  }
  var x = -toplamIlerleme * ts / 2;
  var alan = 0;
  for (i = 0; i < yazi.length; i++) {
    c = yazi.charAt(i);
    var k = t.alan[c];
    if (k === undefined) k = t.alanOrt;
    adv = t.ilerleme[c];
    if (adv === undefined) adv = t.ilerlemeOrt;
    var genislik = adv * ts;
    var oran = 1;
    if (yariPencere !== null && genislik > 0) {
      var kesisim = Math.min(x + genislik, yariPencere) -
        Math.max(x, -yariPencere);
      oran = Math.max(0, Math.min(1, kesisim / genislik));
    }
    alan += k * ts * ts * oran;
    x += genislik;
  }
  return alan;
}

function jeton(p) {
  var pah = 0.8;
  var yaricap = p.cap / 2;
  var ustYaricap = yaricap - pah;
  var govdeYuksekligi = p.kalinlik - 2 * pah;

  // SCAD gövdesi: tam yarıçaplı silindir ve üstte 2*pah yüksekliğinde kesik koni.
  var govde = Math.PI * yaricap * yaricap * govdeYuksekligi;
  var ustPah = Math.PI * 2 * pah / 3 *
    (yaricap * yaricap + yaricap * ustYaricap + ustYaricap * ustYaricap);
  var hacim = govde + ustPah;

  if (p.kenar_deseni === "segmentli") {
    // Sekiz adet 22 derecelik halka diliminin pahlı disk dışında kalan bölümü.
    var aciOrani = 8 * 22 / 360;
    var disKenar = yaricap + 0.2;
    var duzBolum = (p.kalinlik - 2 * pah) *
      (disKenar * disKenar - yaricap * yaricap);
    var pahBolumu = yaricap * pah * pah / 2 - pah * pah * pah / 12;
    hacim += Math.PI * aciOrani * (duzBolum + pahBolumu);
  }

  // Yazi siparis metnidir; gelmezse sema varsayilani (taban sozlesmesi).
  // scad: ts = min(cap*0.34, cap*0.9/max(len,1)*1.3) — uzun metinde kuculur.
  // Eski model metni yok sayip "100" katsayisini sabit ts=0.34*cap ile
  // kullaniyordu: metin-izgara olcumunde -%8.6..+%3.7 sapma
  // (olcum/metin_etki_olcum.json).
  var yazi = (typeof p.yazi === "string") ? p.yazi : "100";
  var yaziBoyutu = Math.min(p.cap * 0.34,
                            p.cap * 0.9 / Math.max(yazi.length, 1) * 1.3);
  var halkaAlani = Math.PI * (p.cap * 0.82 - 1);
  var yuzler = p.yuz_sayisi === "cift" ? 2 : 1;

  if (p.yazi_stili === "kabartma") {
    var tamAlan = halkaAlani + jeton_yazi_alani(yazi, yaziBoyutu, null);
    hacim += tamAlan * 0.69 * yuzler;
  } else {
    var kirpikAlan = halkaAlani +
      jeton_yazi_alani(yazi, yaziBoyutu, p.cap / 2);
    hacim -= kirpikAlan * (yuzler === 2 ? 1.39 : 0.69);
  }

  return hacim;
}
