/* sema.kisitlar KABUL VAKALARI — TEK KAYNAK.
   Hem jenerator/test/fiyat-test.js (CI kapisi) hem jenerator/test/kisit-mutasyon.js
   (mutasyon surucusu) AYNI tabloyu kosar; ikinci kopya YOK.

   RULMAN VAKALARININ DAYANAGI = OLCUM, turetme degil. Her satir uretim motoruna
   gercek openscad render'i atilarak dogrulandi (601 render, 0 ayrisma; ayrica
   378 renderlik genislik izgarasi taramasi). "uretilebilir" = render cikis kodu 0,
   "uretilemez" = motor assert'i (musteriye 422).

   OLCULEN KAPALI FORM (uretim motoru):
     eleman_capi = (dis_cap - ic_cap) / 3 * k,   k: bilya 1,00 · makara 0,95 · tutmali 0,75
       makara  uretilir  <=>  eleman_capi <= genislik
       bilya   uretilir  <=>  eleman_capi <  genislik + 0,24
       tutmali uretilir  <=>  DAIMA (sema araliginda hic reddedilmedi)
   Semadaki `kisitlar` bunu genislik ALT SINIRI olarak yazar (bkz. konfigurator.js
   kisitAltSinir). Ilan edilen izgaranin %33,9'u motorda uretilemezdi.

   🔴 IKI YON ZORUNLU: her sinirin HEM reddedilen HEM kabul edilen komsusu pinlenir.
   Tek yon pinlemek olu nobetcidir — her seye "gecersiz" (ya da "gecerli") diyen bir
   dogrula da yesil yanar. */
"use strict";

// {kod, sema, set, gecerli(beklenen), not}
var VAKALAR = [
  // ---- RULMAN: brief'in bildirdigi kombinasyon (OLCULDU: motorda uretilemez) ----
  { kod: "RK01", sema: "rulman", gecerli: false,
    set: { ic_cap: 9.5, dis_cap: 59.0, genislik: 9.0, eleman: "makara", bosluk: 0.1, flans: "yok" },
    not: "brief seti (makara) — motor assert'i, flans'tan bagimsiz" },
  { kod: "RK02", sema: "rulman", gecerli: false,
    set: { ic_cap: 9.5, dis_cap: 59.0, genislik: 9.0, eleman: "makara", bosluk: 0.1, flans: "var" },
    not: "brief seti, flansli — ayni ret" },
  { kod: "RK03", sema: "rulman", gecerli: false,
    set: { ic_cap: 9.5, dis_cap: 59.0, genislik: 9.0, eleman: "bilya", bosluk: 0.1, flans: "yok" },
    not: "brief seti, bilya — o da uretilemez" },
  { kod: "RK04", sema: "rulman", gecerli: true,
    set: { ic_cap: 9.5, dis_cap: 59.0, genislik: 9.0, eleman: "tutmali", bosluk: 0.1, flans: "yok" },
    not: "AYNI olculer tutmali ile URETILIR — kisit elemana bagli, capa degil" },

  // ---- RULMAN: makara siniri, iki yon (esik tam izgara noktasina oturuyor) ----
  { kod: "RK05", sema: "rulman", gecerli: true,
    set: { ic_cap: 10, dis_cap: 40, genislik: 9.5, eleman: "makara", bosluk: 0.15, flans: "yok" },
    not: "makara: eleman_capi TAM 9,5 = sinir -> KAPSAYICI, uretilir (tolerans nobetcisi)" },
  { kod: "RK06", sema: "rulman", gecerli: false,
    set: { ic_cap: 10, dis_cap: 40, genislik: 9.0, eleman: "makara", bosluk: 0.15, flans: "yok" },
    not: "makara: bir izgara adim asagisi -> uretilemez" },
  { kod: "RK07", sema: "rulman", gecerli: true,
    set: { ic_cap: 5, dis_cap: 44, genislik: 12.5, eleman: "makara", bosluk: 0.2, flans: "yok" },
    not: "makara: sinirin (12,35) hemen ustu -> uretilir" },
  { kod: "RK08", sema: "rulman", gecerli: false,
    set: { ic_cap: 5, dis_cap: 44, genislik: 12.0, eleman: "makara", bosluk: 0.2, flans: "yok" },
    not: "makara: sinirin hemen alti -> uretilemez" },

  // ---- RULMAN: bilya siniri, iki yon + 0,24 payinin BUYUKLUGU ----
  { kod: "RK09", sema: "rulman", gecerli: true,
    set: { ic_cap: 10, dis_cap: 40, genislik: 10.0, eleman: "bilya", bosluk: 0.15, flans: "yok" },
    not: "bilya: eleman_capi 10,0 = genislik -> uretilir" },
  { kod: "RK10", sema: "rulman", gecerli: false,
    set: { ic_cap: 10, dis_cap: 40, genislik: 9.5, eleman: "bilya", bosluk: 0.15, flans: "yok" },
    not: "bilya: bir adim asagisi -> uretilemez" },
  { kod: "RK11", sema: "rulman", gecerli: true,
    set: { ic_cap: 5, dis_cap: 32.5, genislik: 9.0, eleman: "bilya", bosluk: 0.15, flans: "yok" },
    not: "bilya: eleman_capi genisligi 0,167 ASIYOR ama 0,24 payi icinde -> URETILIR. "
       + "Naif 'eleman_capi <= genislik' kurali burada SATILABILIR rulmani bloke ederdi" },
  { kod: "RK12", sema: "rulman", gecerli: false,
    set: { ic_cap: 5, dis_cap: 31.5, genislik: 8.5, eleman: "bilya", bosluk: 0.15, flans: "yok" },
    not: "bilya: asim 0,333 > 0,24 payi -> uretilemez (payin BUYUKLUGUNU pinler)" },

  // ---- RULMAN: uc noktalar ve varsayilan ----
  { kod: "RK13", sema: "rulman", gecerli: true,
    set: { ic_cap: 10, dis_cap: 30, genislik: 9, eleman: "bilya", bosluk: 0.15, flans: "yok" },
    not: "sema VARSAYILANI gecerli kalmali (vitrin/fiyat yolu kirilmasin)" },
  { kod: "RK14", sema: "rulman", gecerli: true,
    set: { ic_cap: 20, dis_cap: 28, genislik: 5.0, eleman: "bilya", bosluk: 0.15, flans: "yok" },
    not: "en dar cap farki + en dar genislik -> uretilir (kisit fazla genis degil)" },
  { kod: "RK15", sema: "rulman", gecerli: false,
    set: { ic_cap: 5, dis_cap: 60, genislik: 5.0, eleman: "bilya", bosluk: 0.15, flans: "yok" },
    not: "en genis cap farki + en dar genislik -> uretilemez" },
  { kod: "RK16", sema: "rulman", gecerli: true,
    set: { ic_cap: 5, dis_cap: 60, genislik: 5.0, eleman: "tutmali", bosluk: 0.15, flans: "yok" },
    not: "AYNI uc set tutmali ile URETILIR — tutmali'ya kisit KONULMAMALI" },
  { kod: "RK17", sema: "rulman", gecerli: true,
    set: { ic_cap: 9.5, dis_cap: 28.0, genislik: 9.0, eleman: "makara", bosluk: 0.1, flans: "yok" },
    not: "dar cap farkinda makara uretilir (kisit dis_cap'e bagli, sabit degil)" },

  // ---- VIDA: mevcut SABIT-min kisiti (regresyon capasi) ----
  { kod: "VK01", sema: "vida", gecerli: false,
    set: { urun_tipi: "civata", cap: 3, boy: 20, tolerans: 0.2 },
    not: "civata M3 reddedilir (sabit min=5 kolu bozulmadi)" },
  { kod: "VK02", sema: "vida", gecerli: true,
    set: { urun_tipi: "civata", cap: 5, boy: 20, tolerans: 0.2 },
    not: "civata M5 gecerli (sabit min sinirinda KAPSAYICI)" },
  { kod: "VK03", sema: "vida", gecerli: true,
    set: { urun_tipi: "somun", cap: 3, boy: 20, tolerans: 0.2 },
    not: "somun M3 gecerli — kisit yalnizca civataya uygulanir (`eger` kolu)" },

  // ---- REFERANS PARAMETRE BOZUKKEN: kisit UYDURMA hata uretmemeli ----
  // `gecerli` bu vakalarda tek basina KOR: bozuk parametrenin kendi hatasi zaten
  // seti gecersiz kilar. Bu yuzden HATA ANAHTARLARI da pinlenir — aksi halde
  // "referans deger yoksa 0 say" gibi bir sessiz hata olculemez kalir.
  { kod: "RK18", sema: "rulman", gecerli: false, hataAnahtarlari: ["ic_cap"],
    set: { ic_cap: "abc", dis_cap: 59.0, genislik: 9.0, eleman: "makara", bosluk: 0.15, flans: "yok" },
    not: "ic_cap bozuk -> YALNIZ ic_cap hatasi; genislik'e uydurma sinir yazilmaz" },
  { kod: "RK19", sema: "rulman", gecerli: false, hataAnahtarlari: ["dis_cap"],
    set: { ic_cap: 10, dis_cap: null, genislik: 9.0, eleman: "makara", bosluk: 0.15, flans: "yok" },
    not: "dis_cap bozuk -> YALNIZ dis_cap hatasi (kisit olculemez, fail-open degil sessiz)" }
];

/* KONF + semalar verilir, her vakayi kosar. Donus: [{kod, ok, beklenen, gercek, not}]
   `hataAnahtarlari` tanimliysa yalnizca `gecerli` degil HATA ANAHTARLARI da kiyaslanir. */
function kosu(KONF, semalar) {
  return VAKALAR.map(function (v) {
    var sema = semalar[v.sema];
    if (!sema) { throw new Error("kisit-vakalar: sema yok: " + v.sema); }
    var s = KONF.dogrula(sema, v.set);
    var gercek, beklenen;
    if (v.hataAnahtarlari) {
      gercek = { gecerli: s.gecerli, hatalar: Object.keys(s.hatalar).sort() };
      beklenen = { gecerli: v.gecerli, hatalar: v.hataAnahtarlari.slice().sort() };
    } else {
      gercek = s.gecerli;
      beklenen = v.gecerli;
    }
    return { kod: v.kod, ok: JSON.stringify(gercek) === JSON.stringify(beklenen),
             beklenen: beklenen, gercek: gercek, not: v.not, sema: v.sema };
  });
}

module.exports = { VAKALAR: VAKALAR, kosu: kosu };
