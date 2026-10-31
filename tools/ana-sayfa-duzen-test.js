#!/usr/bin/env node
/* KABUL TESTI — ANA SAYFA <main> DUZEN SIRASI (isletme karari, 5 Eyl:
 * "skan stil ve olcuye ozel bannerlarini eski yerine koy").
 *
 * NE OLCER: index.html'de `<main>`in UST DUZEY cocuklarinin SIRASINI. Banner satiri
 * (`#bannerRow`) `<main>`in ILK cocugu olmali, kategori panelleri (`#katPanels`) ondan
 * SONRA gelmeli.
 *
 * NEDEN GEREKLI: banner satiri BIR KEZ sessizce yer degistirdi. Foto-slider sokulup
 * `#katPanels` eklenirken (`63a48f7a^` -> `ebdfb059`) `#bannerRow` panellerin ALTINA
 * itildi; sayfa CALISIYORDU, hicbir test DOM SIRASINI olcmuyordu, kimse fark etmedi.
 * Olculen sessiz-hata sinifi: "her oge var, her oge calisiyor, SIRA yanlis, alarm YOK".
 *
 * 🔴 LCP KOLU: banner gorselleri gorus alaninin EN USTUNDE. `#bannerRow` icindeki hicbir
 * gorsel `fetchpriority="high"` TASIYAMAZ — tasirsa LCP bandini yer
 * ([[lazy-fetchpriority-gorus-alanindaki-gizli-gorseli-agdan-cikarmaz]]). Bu, tasima
 * anindaki "once == sonra" karsilastirmasinin KALICI karsiligidir: diff bir kez olculur,
 * bu kol her kosumda olcer.
 *
 * MUTANT kolu ayni kosumda: banner satiri panellerin ALTINA alininca D1 KIRMIZI yanmali.
 * Mutant YALNIZ bellekteki metin kopyasinda uygulanir — repo dosyasi ACILMAZ.
 *
 * Kullanim: node tools/ana-sayfa-duzen-test.js     · Cikis: 0 gecti, 1 kaldi.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const KOK = path.dirname(__dirname);
const INDEX = path.join(KOK, 'index.html');
const html = fs.readFileSync(INDEX, 'utf8');

const FAILS = [];
function kontrol(ad, kosul, detay) {
  console.log((kosul ? '  GECTI ' : '  KALDI ') + ad
              + (kosul || detay === undefined ? '' : ' — ' + JSON.stringify(detay)));
  if (!kosul) FAILS.push(ad);
}
function bildir(ad, deger) { console.log('  RAPOR ' + ad + ' = ' + deger); }

/* `<main>`in UST DUZEY cocuklari — DERINLIK SAYIMIYLA bulunur, GIRINTIYLE DEGIL.
   🔴 Girinti ekseni bu belgede seviye AYIRMIYOR: `#bannerRow`un icindeki `<a id="jenBanner">`
   ve `<a id="skanBanner">` de iki bosluk girintili yazilmis. Ilk surum girintiye
   guveniyordu ve `jenBanner`i `<main>`in ikinci cocugu SANDI — kol, olcmek istedigi
   seviyeyi degil METIN BICIMINI olcuyordu. Simdi yalnizca kap etiketleri (div/a/section)
   sayilarak gercek derinlik tutuluyor; derinlik 1'deki id'ler DONER. */
function mainCocuklari(metin) {
  const bas = metin.indexOf('<main>');
  if (bas === -1) { console.error('FAIL: <main> YOK'); process.exit(1); }
  const son = metin.indexOf('</main>', bas);
  if (son === -1) { console.error('FAIL: </main> YOK'); process.exit(1); }
  const govde = metin.slice(bas + '<main>'.length, son);
  const out = [];
  let derinlik = 0;
  const re = /<(\/?)(div|a|section|aside|nav)\b([^>]*)>/g;
  let m;
  while ((m = re.exec(govde)) !== null) {
    if (m[1] === '/') { derinlik = Math.max(0, derinlik - 1); continue; }
    if (derinlik === 0) {
      const kimlik = /\bid="([^"]+)"/.exec(m[3]);
      out.push(kimlik ? kimlik[1] : '(id-siz ' + m[2] + ')');
    }
    derinlik++;
  }
  return out;
}

/* D0b FIKSTURU — TARAMA EKSENI: derinlik mi, girinti mi?
   Burada olculen sey SAYFA DEGIL, `mainCocuklari`nin KENDISIDIR. Fikstur, girintinin ve
   derinligin BILEREK CELISTIGI bir <main> kurar: `ic1` nested'dir ama ust duzeyle AYNI
   iki bosluk girintiye sahiptir.
     derinlik sayan tarama -> ["ust1","ust2"]      (DOGRU)
     girintiye guvenen tarama -> ["ust1","ic1","ust2"]  (YANLIS)
   OLDUREN DEGISIKLIK (kol bunun icin var): `mainCocuklari` girinti eksenine GERI DONERSE
   bu kol KIRMIZI yanar.
   🔴 NEDEN D2 YETMEZ (kol neden totoloji degil): D2 bugun ayni hatayi yakalar, ama YALNIZCA
   `#jenBanner` BUGUN iki bosluk girintili oldugu icin — yani tesadufen. Biri jenBanner'i
   dort bosluga cekerse girinti-tabanli bir tarama D2'yi de YESIL yakar ve eksen SESSIZCE
   korlesir. D0b o belirsizligi tesadufe birakmaz, SENTETIK olarak kurar. */
const D0B_FIKSTUR = '<main>\n'
  + '  <div id="ust1">\n'
  + '  <div id="ic1"></div>\n'
  + '  </div>\n'
  + '  <div id="ust2"></div>\n'
  + '</main>';

console.log('=== ANA SAYFA <main> DUZEN SIRASI (kok: ' + KOK + ')');

const cocuk = mainCocuklari(html);
console.log('\n[D] SIRA');
bildir('D0-r <main> ust duzey cocuklari', cocuk.join(' -> ') || '(BOS)');
kontrol('D0 tarama CANLI: <main> ust duzey cocugu bulundu (bos liste = girinti ekseni '
        + 'kirilmis, D1 tautolojik yesil yanardi)', cocuk.length >= 2, cocuk);

const d0b = mainCocuklari(D0B_FIKSTUR);
const icBanner = cocuk.filter(function (k) { return k === 'jenBanner' || k === 'fotoBanner'; });
bildir('D0b-r celisen fiksturde tarama', (d0b.join(' -> ') || '(BOS)')
       + ' | gercek listede ic banner = ' + (icBanner.join(',') || 'YOK'));
kontrol('D0b tarama DERINLIK ekseninde: (a) fiksturde nested `ic1` ust duzeyle AYNI '
        + 'girintide olmasina ragmen listeye GIRMEDI, (b) gercek sayfada #bannerRow icindeki '
        + 'jenBanner/fotoBanner <main>in cocugu SAYILMADI — girinti eksenine donulurse KIRMIZI',
        d0b.length === 2 && d0b[0] === 'ust1' && d0b[1] === 'ust2' && icBanner.length === 0,
        { fikstur: d0b, icBanner: icBanner });

kontrol('D1 #bannerRow <main>in ILK cocugu (index 0)', cocuk[0] === 'bannerRow', cocuk[0]);
// Okan 5 Eki 2026: "fotoğrafından özel üretim" bölümü iki banner'ın ALTINA, kategorilerin
// ÜSTÜNE (#fotoUretim, varsayılan gizli). Sıra: bannerRow -> fotoUretim -> katPanels.
kontrol('D2 #bannerRow ARDINDAN #fotoUretim, sonra #katPanels (index 1, 2)',
        cocuk[1] === 'fotoUretim' && cocuk[2] === 'katPanels', cocuk.slice(1, 3).join(' -> '));

console.log('\n[E] BANNER GOVDESI — tasima SIRA degisikligiydi, ICERIK degil');
const banBas = html.indexOf('<div id="bannerRow"');
const banSon = html.indexOf('\n  </div>', banBas);
const ban = html.slice(banBas, banSon);
kontrol('E0 #bannerRow govdesi ayiklandi', banBas !== -1 && banSon !== -1 && ban.length > 200,
        ban.length);
kontrol('E1 iki banner da DURUYOR (#jenBanner "Olcuye Ozel Uretim" + foto banner)',
        /id="jenBanner"/.test(ban) && /id="fotoBanner"/.test(ban) && /foto-banner/.test(ban),
        [/id="jenBanner"/.test(ban), /id="fotoBanner"/.test(ban), /foto-banner/.test(ban)]);

const yuksek = (ban.match(/fetchpriority="high"/g) || []).length;
bildir('E2-r #bannerRow icindeki fetchpriority="high" sayisi', yuksek);
kontrol('E2 🔴 LCP: #bannerRow icinde fetchpriority="high" YOK (banner artik gorus '
        + 'alaninin EN USTUNDE; yuksek oncelik LCP bandini yerdi)', yuksek === 0, yuksek);

console.log('\n[F] renderGrid GOSTER/GIZLE KOLU — sira degisti, kol DEGISMEDI');
kontrol('F1 renderGrid hala #bannerRow display kolunu tasiyor (banner yalniz ana sayfa '
        + 'gorunumunde; kategori/arama/marka gorunumunde GIZLI)',
        /bannerRow[\s\S]{0,200}?display/.test(html)
        || /getElementById\("bannerRow"\)/.test(html), null);


console.log('\n[R] RESIMDEN URETIM ARA SAYFASI (/?sayfa=resimden-uretim)');
/* OZET: foto uretim bolumu ana sayfadan ayrildi; giris banner'i (#fotoBanner) bu ara
 * sayfaya baglanir. Bu bolum YAPISAL iddialari olcer; her biri icin bir MUTANT
 * (bellekteki metin kopyasi) vardir — mutant iddiayi KIRMIZIya dusurmezse olcum
 * tasidir, sessiz gecmez. */
function resimdenIddialari(h){
  var i = {};
  var banner = /<a\b[^>]*\bid="fotoBanner"[^>]*>/.exec(h);
  var blok = /<section\b[^>]*\bid="resimdenSayfaBas"[^>]*>[\s\S]*?<\/section>/.exec(h);
  i.R1_araBlok = !!blok && /<h1\b[^>]*>Resimden figür üret<\/h1>/.test(blok[0]) &&
                /id="fotoKapaliMesaj"/.test(blok[0]) && /WhatsApp'tan yazın/.test(blok[0]);
  i.R2_bannerHref = !!banner && /href="\/\?sayfa=resimden-uretim"/.test(banner[0]) &&
                    / hidden[\s>]/.test(banner[0]);
  i.R3_araBlokGizli = !!blok && /style="display:none"/.test(blok[0]);
  i.R4_adresParametresi = /params\.get\("sayfa"\)/.test(h) &&
                        /sayfa\s*===\s*RESIMDEN_SAYFA/.test(h);
  return i;
}
var temelIddia = resimdenIddialari(html);
Object.keys(temelIddia).forEach(function(ad){
  kontrol('R ' + ad + ' (temel sayfada dogrulanir)', temelIddia[ad], temelIddia[ad]);
});

console.log('\n[R-MUTANT] her yeni iddia icin bir mutant kirmizi yakar');
/* Mutantlar YALNIZ bellekteki metin kopyasinda uygulanir — repo dosyasi ACILMAZ. */
var mutantlar = [
  ['MR1 banner href degisti (sayfa parametresi bozuldu)',
   html.replace('href="/?sayfa=resimden-uretim"', 'href="/?kategori=Skan%20Art"'), 'R2_bannerHref'],
  ['MR2 bannerdan `hidden` kaldirildi (fail-closed kirildi)',
   html.replace('href="/?sayfa=resimden-uretim" hidden', 'href="/?sayfa=resimden-uretim"'), 'R2_bannerHref'],
  ['MR3 ara sayfa h1 metni degisti',
   html.replace('Resimden figür üret</h1>', 'Hemen başlayın</h1>'), 'R1_araBlok'],
  ['MR4 ara sayfa blogu varsayilan gorunur birakildi (display:none kaldirildi)',
   html.replace('class="resimden-sayfa-bas" style="display:none"', 'class="resimden-sayfa-bas"'), 'R3_araBlokGizli'],
  ['MR5 sayfa parametresi koddan silindi',
   html.replace('var sayfa = params.get("sayfa");', 'var sayfa = null;'), 'R4_adresParametresi'],
];
mutantlar.forEach(function(m){
  var uygulandi = m[1] !== html;
  kontrol('R-MUTANT ' + m[0] + ' — KURULABILDI', uygulandi, null);
  if(!uygulandi){ return; }
  var sonuc = resimdenIddialari(m[1]);
  kontrol('R-MUTANT ' + m[0] + ' -> ' + m[2] + ' KIRMIZI yanar',
          sonuc[m[2]] === false, sonuc[m[2]]);
});

console.log('\n[M] MUTANT — olcum SIRAYA duyarli mi (K182: mutant HEDEF KOLU oldurmeli)');
/* Banner blogunu panellerin ALTINA geri al (YALNIZ bellekte) ve D1'i yeniden olc. */
function bannerAltaAl(metin) {
  const satir = metin.split('\n');
  const iKat = satir.findIndex(function (s) { return /^ {2}<div id="katPanels"/.test(s); });
  const iBan = satir.findIndex(function (s) { return /^ {2}<div id="bannerRow"/.test(s); });
  if (iKat === -1 || iBan === -1 || iBan > iKat) { return null; }
  let iBanSon = -1;
  for (let i = iBan + 1; i < satir.length; i++) {
    if (satir[i] === '  </div>') { iBanSon = i; break; }
  }
  if (iBanSon === -1) { return null; }
  const ban = satir.slice(iBan, iBanSon + 1);
  const kat = satir.slice(iBanSon + 1, iKat + 1);
  satir.splice(iBan, iKat - iBan + 1, ...kat, ...ban);
  return satir.join('\n');
}
const mutant = bannerAltaAl(html);
kontrol('M0 mutant KURULABILDI (kurulamazsa mutant hedefe ULASMAMISTIR, sessiz gecmez)',
        mutant !== null && mutant !== html);
if (mutant) {
  const mc = mainCocuklari(mutant);
  bildir('M1-r mutant sirasi', mc.slice(0, 3).join(' -> '));
  kontrol('M1 mutantta D1 KIRMIZI: #bannerRow artik ILK cocuk DEGIL — D1 sirayi FIILEN olcuyor',
          mc[0] !== 'bannerRow' && mc.indexOf('bannerRow') > mc.indexOf('katPanels'), mc.slice(0, 3).join(' -> '));
}

console.log('\n[S] ESKI "?kategori=Skan Art" BAGLANTISI -> "Figur" (31 Eki tasima)');
/* Bu kol DAVRANIS olcer: index.html'deki applyUrlParams GERCEKTEN calistirilir (node:vm
 * sahte alan: location/history/URLSearchParams) ve "?kategori=Skan%20Art" girdisinde
 * activeCat "Figur" oluyor mu BAKILIR. Salt metin grep'i TEK BASINA totoloji olurdu —
 * satiri silmek iddiayi kirar ama KODUN davranisini olcemez — bu yuzden MUTANT kolu var.
 * 🔴 KATEGORI_ALIAS'A "Skan Art" EKLENMEZ: o harita `seri=true` (SARI SERI) kurar; Figur
 * sari seri DEGIL — eski baglanti NORMAL Figur gorunumunu acmali. Kendi haritasina
 * eklenirse mutant kolu (MS2) bu iddiayi KIRMIZIya dusurur.
 * Mutantlar YALNIZ bellekteki metin kopyasinda uygulanir — repo dosyasi ACILMAZ. */

/* `function <ad>(...){...}` govdesini SUSLU PARANTEZ SAYARAK ayikla (regex degil). */
function jsFonksiyon(metin, ad) {
  const m = new RegExp('function\\s+' + ad + '\\s*\\(').exec(metin);
  if (!m) { return null; }
  const i = metin.indexOf('{', m.index + m[0].length);
  if (i === -1) { return null; }
  let derinlik = 0;
  for (let k = i; k < metin.length; k++) {
    if (metin[k] === '{') { derinlik++; }
    else if (metin[k] === '}') {
      derinlik--;
      if (derinlik === 0) { return metin.slice(m.index, k + 1); }
    }
  }
  return null;
}

/* index.html'deki `var <ad> = <literal>` degerini literal olarak al (JSON olarak cozulur). */
function htmlSabit(h, ad) {
  const m = new RegExp('var\\s+' + ad + '\\s*=\\s*(\\[[^\\]]*\\]|\\{[^}]*\\}|"[^"]*")\\s*;').exec(h);
  return m ? m[1] : null;
}

/* applyUrlParams/syncUrl'un calistigi SAHTE ALAN. markaKatla yalnizca `marka` parametresi
   varken cagrilir — bu kol `kategori` parametresini olcer, o yol kimlik degildir. */
function sahaAlan(h) {
  const alan = {
    URLSearchParams: URLSearchParams,
    location: { hash: '', search: '', pathname: '/',
                replace: function () { throw new Error('beklenmedik yonlendirme'); } },
    history: { replaceState: function (a, b, c) { this.url = c; } },
    PRUVO_ATIF: { urlKorunan: function () { return []; } },
    activeCat: 'Tümü', activeSeri: false, activeAlt: 'Tümü', activeBrand: 'Tümü',
    activeModel: 'Tümü', query: '', searchEl: { value: '' }, clearEl: { className: '' },
    aktifSayfa: '', markaKatla: function (x) { return x; }
  };
  ['CATEGORIES', 'GIZLI_KATEGORILER', 'KATEGORI_ALIAS', 'KATEGORI_GORUNUR', 'RESIMDEN_SAYFA']
    .forEach(function (ad) {
      const ham = htmlSabit(h, ad);
      if (ham === null) { throw new Error('sabit bulunamadi: ' + ad); }
      alan[ad] = JSON.parse(ham);
    });
  return alan;
}

function fonksiyonlariYukle(alan, h, adlar) {
  const kaynak = adlar.map(function (ad) {
    const src = jsFonksiyon(h, ad);
    if (!src) { throw new Error('fonksiyon bulunamadi: ' + ad); }
    return src;
  }).join('\n');
  vm.createContext(alan);
  vm.runInContext(kaynak, alan);
  return alan;
}

/* Canli sayfa davranisi: verilen sorgu dizesiyle applyUrlParams calisir, activeCat/activeSeri
   okunur. Hata olursa null doner (harness kirildi = iddia KIRMIZI, sessiz gecmez). */
function kategoriAktif(h, search) {
  try {
    const alan = fonksiyonlariYukle(sahaAlan(h), h, ['applyUrlParams']);
    alan.location.search = search;
    alan.applyUrlParams();
    return { kat: alan.activeCat, seri: alan.activeSeri, hata: null };
  } catch (e) {
    return { kat: null, seri: null, hata: String((e && e.message) || e) };
  }
}

/* syncUrl'in YAZDIGI adres (adres cubugu "Figur" demeli, eski seri adini geri yazmamali). */
function syncUrlYaz(h, search) {
  const alan = fonksiyonlariYukle(sahaAlan(h), h,
    ['applyUrlParams', 'aktifKategoriEtiketi', 'gorunurKategori', 'syncUrl']);
  alan.location.search = search;
  alan.applyUrlParams();
  alan.syncUrl();
  return alan.history.url;
}

/* S kolunun iddialari — h metni UZERINDE yeniden calistirilabilir (mutant kollari icin). */
function sIddialari(h) {
  const i = {};
  const aliasIdx = h.indexOf('kat === "Skan Art"');
  const aliasKolIdx = h.indexOf('hasOwnProperty.call(KATEGORI_ALIAS, kat)');
  i.S1_aliasSatiriTEK = (h.match(/kat === "Skan Art"/g) || []).length === 1;
  i.S2_sira = aliasIdx !== -1 && aliasKolIdx !== -1 && aliasIdx < aliasKolIdx;
  const harita = JSON.parse(htmlSabit(h, 'KATEGORI_ALIAS'));
  i.S3_haritadaYOK = !Object.prototype.hasOwnProperty.call(harita, 'Skan Art');
  const canli = kategoriAktif(h, '?kategori=Skan%20Art');
  i.S4_figurdur = canli.hata === null && canli.kat === 'Figür';
  i.S4b_sariSeriYOK = canli.hata === null && canli.seri === false;
  const denetim = kategoriAktif(h, '?kategori=BoyleBirKategoriYok');
  i.S5_kontrolTumü = denetim.hata === null && denetim.kat === 'Tümü';
  let url = null, hata = null;
  try { url = syncUrlYaz(h, '?kategori=Skan%20Art'); } catch (e) { hata = String((e && e.message) || e); }
  const yazilan = url ? new URLSearchParams(url.split('?')[1] || '').get('kategori') : null;
  i.S6_syncUrlFigur = hata === null && yazilan === 'Figür';
  return i;
}

const sTemel = sIddialari(html);
Object.keys(sTemel).forEach(function (ad) {
  kontrol('S ' + ad + ' (canli index.html uzerinde dogrulanir)', sTemel[ad], sTemel[ad]);
});
const sCanli = kategoriAktif(html, '?kategori=Skan%20Art');
bildir('S-r "?kategori=Skan%20Art" -> activeCat', sCanli.kat + ' | activeSeri=' + sCanli.seri
       + (sCanli.hata ? ' | HATA: ' + sCanli.hata : ''));
bildir('S-r "?kategori=Figür" -> activeCat (yeni adres de calisiyor)',
       (function () { const c = kategoriAktif(html, '?kategori=Fig%C3%BCr');
                     return c.kat + (c.hata ? ' | HATA: ' + c.hata : ''); })());

console.log('\n[S-MUTANT] her yeni iddia icin bir mutant kirmizi yakar');
/* Mutantlar YALNIZ bellekteki metin kopyasinda uygulanir — repo dosyasi ACILMAZ. */
function aliasSatiriniSil(h) {
  return h.split('\n').filter(function (s) {
    return s.indexOf('kat === "Skan Art"') === -1;
  }).join('\n');
}
const sMutantlar = [
  ['MS1 alias satiri SILINDI (eski baglanti Figur\'u acmaz)', aliasSatiriniSil(html),
   ['S1_aliasSatiriTEK', 'S4_figurdur', 'S6_syncUrlFigur']],
  ['MS2 KATEGORI_ALIAS haritasina "Skan Art" eklendi (sari seri bayragi yanlis)',
   html.replace(/var KATEGORI_ALIAS = \{/, 'var KATEGORI_ALIAS = {"Skan Art":"Figür",'),
   ['S3_haritadaYOK']],
];
sMutantlar.forEach(function (m) {
  const uygulandi = m[1] !== html;
  kontrol('S-MUTANT ' + m[0] + ' — KURULABILDI', uygulandi, null);
  if (!uygulandi) { return; }
  const sonuc = sIddialari(m[1]);
  m[2].forEach(function (hedef) {
    kontrol('S-MUTANT ' + m[0] + ' -> ' + hedef + ' KIRMIZI yanar',
            sonuc[hedef] === false, sonuc[hedef]);
  });
});

console.log('\n' + (FAILS.length ? 'SONUC: KIRMIZI — kalan ' + FAILS.length : 'SONUC: YESIL'));
process.exit(FAILS.length ? 1 : 0);
