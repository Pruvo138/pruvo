#!/usr/bin/env node
/* KABUL TESTI — ANA SAYFA KATEGORI PANELI ASGARI CIP ESIGI (Okan emri, 5 Eyl:
 * "3'un altinda alt kategorisi olan ana sayfada olmaz").
 *
 * NE OLCER: index.html'deki GERCEK `renderKatPanelleri` govdesini, GERCEK cip indeksiyle
 * (tools/cip-indeks.py --yazdir, gercek urunler.json'dan) kosturur ve ANA SAYFAYA FIILEN
 * CIZILEN panelleri sayar. Sabit bir beklenen liste TASIMAZ: hangi kategorinin cizilecegi
 * esikten ve indeksten TURER.
 *
 * NEDEN GEREKLI: esik `index.html` icinde tek bir `if` satiridir. O satir silinse ya da
 * KAT_PANEL_MIN_CIP 0 yapilsa hicbir kapi kirmizi yanmiyordu — panel sessizce 12
 * kategoriye geri donerdi (5'i tek cipli ya da tamamen bos).
 *
 * MUTANT KOLU (--mutant <N>): esigi N'e cevirip AYNI olcumu tekrarlar. Testin kendisi
 * degil, olcumun ESIGE DUYARLI oldugu boyle kanitlanir — mutant taban ile ayni sonucu
 * verirse iddia esigi olcmuyor demektir ve test KIRMIZI yanar.
 *
 * 🔴 KAYNAK DOSYAYA YAZMAZ. Mutant YALNIZ bellekteki metin kopyasinda uygulanir
 * (repo dosyasi acilmaz bile — okuma disinda dokunulmaz).
 *
 * Kullanim:
 *   node tools/kat-panel-test.js
 * Cikis: 0 = gecti, 1 = kaldi.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');

const TOOLS = __dirname;
const KOK = path.dirname(TOOLS);
const INDEX = path.join(KOK, 'index.html');

const FAILS = [];
function kontrol(ad, kosul, detay) {
  console.log((kosul ? '  GECTI ' : '  KALDI ') + ad
              + (kosul || detay === undefined ? '' : ' — ' + JSON.stringify(detay)));
  if (!kosul) FAILS.push(ad);
}
function bildir(ad, deger) { console.log('  RAPOR ' + ad + ' = ' + deger); }

// ---- kaynak ayiklama (FAIL-LOUD: bulunamayan parca sessizce atlanmaz) --------
const html = fs.readFileSync(INDEX, 'utf8');

function eslesenParantez(src, acilisIx, ac, kapa) {
  let d = 0;
  for (let i = acilisIx; i < src.length; i++) {
    if (src[i] === ac) d++;
    else if (src[i] === kapa) { d--; if (d === 0) return i; }
  }
  throw new Error('parantez kapanmadi @' + acilisIx);
}

function fnAl(ad) {
  const i = html.indexOf('function ' + ad + '(');
  if (i === -1) { console.error('FAIL: index.html icinde `function ' + ad + '` YOK'); process.exit(1); }
  const g = html.indexOf('{', i);
  return html.slice(i, eslesenParantez(html, g, '{', '}') + 1);
}

function varAl(ad) {
  const re = new RegExp('var\\s+' + ad + '\\s*=', 'g');
  const m = re.exec(html);
  if (!m) { console.error('FAIL: index.html icinde `var ' + ad + '` YOK'); process.exit(1); }
  let i = m.index + m[0].length;
  while (i < html.length && /\s/.test(html[i])) i++;
  let son;
  if (html[i] === '{') son = eslesenParantez(html, i, '{', '}');
  else if (html[i] === '[') son = eslesenParantez(html, i, '[', ']');
  else { son = html.indexOf(';', i) - 1; }
  return 'var ' + ad + ' = ' + html.slice(i, son + 1) + ';';
}

const PARCALAR = {
  CATEGORIES: varAl('CATEGORIES'),
  GIZLI_KATEGORILER: varAl('GIZLI_KATEGORILER'),
  KATEGORI_GORUNUR: varAl('KATEGORI_GORUNUR'),
  ALTKATEGORILER: varAl('ALTKATEGORILER'),
  KAT_PANEL_MARKA_TAVANI: varAl('KAT_PANEL_MARKA_TAVANI'),
  KAT_PANEL_MIN_CIP: varAl('KAT_PANEL_MIN_CIP'),
  gorunurKategori: fnAl('gorunurKategori'),
  altListesi: fnAl('altListesi'),
  cipIndeks: fnAl('cipIndeks'),
  _ixKat: fnAl('_ixKat'),
  // 🔴 ENVANTER, RENDER GOVDESININ OKUDUGU HER ADI TASIMALI: `renderKatPanelleri`
  // 9 Eyl'de baslik sayisi icin `_ixKatSayisi`i cagirmaya basladi; ad burada YOKKEN
  // govde ReferenceError ile DUSTU (fail-loud calisti, sessiz gecmedi)
  // ([[cagri-yeri-envanterden-duserse-onarildi-sanilir]]).
  _ixKatSayisi: fnAl('_ixKatSayisi'),
  _altAnahtar: fnAl('_altAnahtar'),
  indeksMarkalar: fnAl('indeksMarkalar'),
  indeksGruplar: fnAl('indeksGruplar'),
  katPanelUrl: fnAl('katPanelUrl'),
  katPanelCip: fnAl('katPanelCip'),
  katPanelSatir: fnAl('katPanelSatir'),
  renderKatPanelleri: fnAl('renderKatPanelleri'),
};

// ---- gercek cip indeksi (gercek urunler.json'dan) ----------------------------
function cipIndeksiUret() {
  const r = spawnSync('python3', [path.join(TOOLS, 'cip-indeks.py'), '--yazdir', '--kok', KOK],
                      { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (r.error || r.status !== 0 || !r.stdout) {
    console.error('FAIL: cip indeksi URETILEMEDI (cip-indeks.py --yazdir).');
    console.error('  status=%s error=%s', r.status, r.error && r.error.message);
    console.error((r.stderr || '').slice(-2000));
    process.exit(1);
  }
  return JSON.parse(r.stdout);
}

// ---- minimal DOM sapmasi -----------------------------------------------------
function domKur() {
  function el(tag) {
    return {
      tagName: tag, className: '', href: '', textContent: '', children: [],
      appendChild: function (c) { this.children.push(c); return c; },
    };
  }
  const kap = el('div');
  return {
    kap: kap,
    document: {
      createElement: el,
      getElementById: function (id) { return id === 'katPanels' ? kap : null; },
    },
  };
}

/* Cizilen panelin DEGER cipleri: her satirdaki ilk cip "Tumu" (katPanelSatir kosulsuz
   basar) — sayima GIRMEZ, cunku esigin sordugu soru "kac DARALTMA kolu var". */
function panelOlc(indeks, minCipMutant) {
  const dom = domKur();
  let kaynak = Object.keys(PARCALAR).map(function (k) { return PARCALAR[k]; }).join('\n');
  if (minCipMutant !== undefined) {
    kaynak = kaynak.replace(/var KAT_PANEL_MIN_CIP = \d+;/,
                            'var KAT_PANEL_MIN_CIP = ' + minCipMutant + ';');
  }
  const ctx = {
    window: { PRUVO_CIP_INDEKS: indeks },
    document: dom.document,
    URLSearchParams: URLSearchParams,
    Object: Object, String: String, Number: Number, console: console,
  };
  vm.createContext(ctx);
  vm.runInContext(kaynak + '\nrenderKatPanelleri();', ctx, { timeout: 20000 });

  const paneller = dom.kap.children.map(function (b) {
    const bas = b.children[0];
    const satirlar = b.children.slice(1);
    let deger = 0;
    satirlar.forEach(function (s) {
      // s.children: [etiket, "Tumu" cipi, ...deger cipleri]
      deger += Math.max(0, s.children.length - 2);
    });
    return { baslik: bas ? bas.textContent : '(BASLIKSIZ)', cip: deger };
  });
  return paneller;
}

// ---- olcum -------------------------------------------------------------------
console.log('=== KATEGORI PANELI ASGARI CIP ESIGI (kok: ' + KOK + ')');
const indeks = cipIndeksiUret();
const esik = Number((PARCALAR.KAT_PANEL_MIN_CIP.match(/=\s*(\d+)/) || [])[1]);

console.log('\n[A] ESIK SABITI');
kontrol('A1 esik ADLANDIRILMIS sabit olarak VAR (sihirli sayi gomulu degil)',
        Number.isInteger(esik) && esik > 0, PARCALAR.KAT_PANEL_MIN_CIP);
kontrol('A2 render govdesi sabiti ADIYLA kullaniyor (kopya sayi degil)',
        /KAT_PANEL_MIN_CIP/.test(PARCALAR.renderKatPanelleri));
kontrol('A3 render govdesinde KATEGORI ADI gomulu DEGIL (ozel-durum satiri yok)',
        !/(Bisiklet|Tamirat|Ofis|Kamera|Bahçe|Oyun\/Hobi)/.test(PARCALAR.renderKatPanelleri),
        PARCALAR.renderKatPanelleri.match(/(Bisiklet|Tamirat|Ofis|Kamera|Bahçe|Oyun\/Hobi)/g));

console.log('\n[B] CIZILEN PANELLER (gercek indeks · esik ' + esik + ')');
const taban = panelOlc(indeks);
taban.forEach(function (p) { console.log('   ' + p.baslik + '  cip=' + p.cip); });
bildir('B0 cizilen panel sayisi', taban.length);

kontrol('B1 cizilen HER panel esigi geciyor (cip >= ' + esik + ')',
        taban.every(function (p) { return p.cip >= esik; }),
        taban.filter(function (p) { return p.cip < esik; }));

const cizilen = taban.map(function (p) { return p.baslik; });
/* 🔴 TURKCE BUYUTME: panel basligi `toLocaleUpperCase("tr")` ile yazilir, yani
   "Bisiklet" -> "BİSİKLET" (NOKTALI İ), "Tamirat" -> "TAMİRAT". Beklenen adlar ASCII
   "BISIKLET"/"TAMIRAT" yazilirsa hicbiri eslesmez ve kollar YANLIS-NEGATIF kirmizi
   yanar (ilk kosumda tam bunu yaptilar). Adlar BILEREK elle yazildi: `gorunurKategori`
   + `toLocaleUpperCase` zincirinden TURETILSEYDI iddia tautoloji olurdu ("panel neyi
   basiyorsa o dogrudur") ve basliktaki bir bozulmayi olcemezdi.

   🔴 BEKLENTI DEFTERI (19 Eyl 2026) — TEK bir "cizilmez" listesi yerine kategori basina
   ELLE yazilmis BEKLENTI tasinir:
     'kalkan'      = DOGAL cipi esigin ALTINDA, ana sayfada panel ACMAMALI
     'dogal-gecen' = esigi OZEL-DURUM SATIRI OLMADAN gecti, panel ACMALI
   Neden iki kova: veri buyudukce bir kategori kovadan kovaya GECER. Eski tek liste bunu
   "B2 KALDI — [KAMERA]" diye YALNIZCA kirmizi yakiyordu; okuyan kisi bunun bir GERILEME
   mi yoksa BUYUME mu oldugunu ciktidan ayirt edemiyordu. Artik B2b/B4b kollari hangi
   kategorinin HANGI kovaya tasinacagini ADIYLA soyler. Kova degisimi TEKIL YAMA DEGILDIR
   (veri gercekten degismistir); degisimin gerekcesi asagida yorumda KALIR. */
const DEFTER = [
  { ad: 'TAMİRAT',   beklenti: 'kalkan' },
  { ad: 'OFİS',      beklenti: 'kalkan' },
  { ad: 'BAHÇE',     beklenti: 'kalkan' },
  { ad: 'OYUN/HOBİ', beklenti: 'kalkan' },
  /* 5 Eyl 2026'da 0 cipliydi (kalkan). 19 Eyl 2026: Canon/Nikon/Sony kamera partileri
     KAMERA'yi 3 MARKA cipine cikardi ve esigi DOGAL gecti — Bisiklet emsali, koda
     hicbir kategori adi gomulmedi (A3 bunu ayrica olcer). */
  { ad: 'KAMERA',    beklenti: 'dogal-gecen' },
  /* 5 Eyl 2026: 16 alt kategorisiyle esigi ozel-durum satiri OLMADAN gecti. */
  { ad: 'BİSİKLET',  beklenti: 'dogal-gecen' },
];
const kalkan = DEFTER.filter(function (x) { return x.beklenti === 'kalkan'; })
                     .map(function (x) { return x.ad; });
const dogalGecen = DEFTER.filter(function (x) { return x.beklenti === 'dogal-gecen'; })
                         .map(function (x) { return x.ad; });

/* ESIKSIZ KOSUM (esik 0): HER kategori cizilir, yani KALKAN kategorilerin DOGAL cip
   sayisi ancak burada gorunur (esik altinda kalan panel DOM'a hic girmedigi icin taban
   kosumunda sayilamaz). Ayni olcum [C]'de C1/C2 mutanti olarak da kullanilir. */
const m0 = panelOlc(indeks, 0);
const m0Adlar = m0.map(function (p) { return p.baslik; });
const dogalCip = {};
m0.forEach(function (p) { dogalCip[p.baslik] = p.cip; });

/* 🔴 YAZIM HATASI BEDAVAYA GECEMEZ: "panel acmiyor" iddiasi, ad YANLIS yazildiginda da
   dogrudur (hicbir panel o adla cizilmez). Defterdeki her ad esiksiz kosumda GERCEKTEN
   bulunmalidir; bulunmazsa kalkan kollari BOSA olcuyor demektir. */
function defterYabancilari(adlar) {
  return adlar.filter(function (a) { return m0Adlar.indexOf(a) === -1; });
}
kontrol('B0b DEFTER\'deki HER ad esiksiz kosumda GERCEKTEN var (yazim hatasi/kategori '
        + 'yeniden adlandirmasi kalkan kolunu BOSA dusuremez)',
        defterYabancilari(DEFTER.map(function (x) { return x.ad; })).length === 0,
        { yabanci: defterYabancilari(DEFTER.map(function (x) { return x.ad; })), evren: m0Adlar });

kontrol('B2 DEFTER kalkan kategorileri (' + kalkan.length + ') ana sayfada panel ACMIYOR',
        kalkan.every(function (k) { return cizilen.indexOf(k) === -1; }),
        kalkan.filter(function (k) { return cizilen.indexOf(k) !== -1; }));

const buyuyen = kalkan.filter(function (k) { return (dogalCip[k] || 0) >= esik; });
kontrol('B2b DEFTER kalkan kategorilerinin DOGAL cipi esigin ALTINDA (BUYUME ALARMI)',
        buyuyen.length === 0,
        buyuyen.map(function (k) {
          return k + ' esigi DOGAL gecti (cip=' + dogalCip[k] + ' >= ' + esik
                 + ') — DEFTER\'de beklenti\'yi "dogal-gecen" yap (gerekce: hangi urun '
                 + 'partisi buyuttu)';
        }));

const acilmayan = dogalGecen.filter(function (k) { return cizilen.indexOf(k) === -1; });
kontrol('B3 DEFTER dogal-gecen kategorilerinin paneli ana sayfada DURUYOR '
        + '(ozel-durum satiri DEGIL, alt kategori/marka cipiyle)',
        acilmayan.length === 0,
        acilmayan.map(function (k) {
          return k + ' paneli KAYBOLDU (dogal cip=' + (dogalCip[k] === undefined ? '?' : dogalCip[k])
                 + ', esik=' + esik + ') — veri kuculduyse DEFTER\'de "kalkan" yap, '
                 + 'kuculmediyse GERILEME: render govdesini olc';
        }));

const zayif = dogalGecen.filter(function (k) {
  const p = taban.filter(function (x) { return x.baslik === k; })[0];
  return !p || p.cip < esik;
});
kontrol('B4 DEFTER dogal-gecen kategorilerinde >=' + esik + ' cip RENDER EDILIYOR '
        + '(ayri iddia: esigi ne kadar gectigi)', zayif.length === 0, zayif);
dogalGecen.forEach(function (k) {
  const p = taban.filter(function (x) { return x.baslik === k; })[0];
  bildir('B4-r ' + k + ' panel cipi', p ? p.cip : 0);
});

console.log('\n[C] MUTANT — olcum esige DUYARLI mi (K182: her mutant HEDEF KOLU oldurmeli)');
kontrol('C1 esik 0 yapilinca CIZILEN PANEL SAYISI ARTIYOR (taban ' + taban.length
        + ' -> mutant ' + m0.length + ') — "panel ' + taban.length
        + '" iddiasi esigi FIILEN olcuyor',
        m0.length > taban.length, { taban: taban.length, mutant: m0.length });
kontrol('C2 esik 0 mutantinda ' + kalkan.length
        + ' kalkan kategorisi GERI GELIYOR (B2 kolu mutantla KIRMIZI)',
        kalkan.every(function (k) { return m0Adlar.indexOf(k) !== -1; }), m0Adlar);

const mYuksek = panelOlc(indeks, 999);
kontrol('C3 esik 999 yapilinca HICBIR panel cizilmiyor (esik tek yonlu degil, FIILEN suzuyor)',
        mYuksek.length === 0, mYuksek.length);

/* C4 DEFTER MUTANTI — kalkan iddiasinin YAZIM HATASINA karsi bagisikligi. Burada mutant
   esige degil DEFTER'e uygulanir: sahte bir ada ('KAMERAX') hicbir panel cizilmez, yani
   B2 kolu bedavaya YESIL kalir; onu yakalayacak olan B0b kolu KIRMIZI yanmalidir. Mutant
   B0b'yi OLDURMUYORSA B2'nin yesili bir sey KANITLAMIYOR demektir. */
const SAHTE = 'KAMERAX';
const sahteDefter = kalkan.concat([SAHTE]);
kontrol('C4 DEFTER\'e SAHTE ad eklenince B0b kolu KIRMIZI yanar '
        + '(kalkan iddiasi yazim hatasiyla bedavaya gecilemez)',
        sahteDefter.every(function (k) { return cizilen.indexOf(k) === -1; })
        && defterYabancilari(sahteDefter).length === 1
        && defterYabancilari(sahteDefter)[0] === SAHTE,
        { b2SahteyleYesil: sahteDefter.every(function (k) { return cizilen.indexOf(k) === -1; }),
          b0bYabanci: defterYabancilari(sahteDefter) });

console.log('\n' + (FAILS.length ? 'SONUC: KIRMIZI — kalan ' + FAILS.length : 'SONUC: YESIL'));
process.exit(FAILS.length ? 1 : 0);
