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

console.log('=== ANA SAYFA <main> DUZEN SIRASI (kok: ' + KOK + ')');

const cocuk = mainCocuklari(html);
console.log('\n[D] SIRA');
bildir('D0-r <main> ust duzey cocuklari', cocuk.join(' -> ') || '(BOS)');
kontrol('D0 tarama CANLI: <main> ust duzey cocugu bulundu (bos liste = girinti ekseni '
        + 'kirilmis, D1 tautolojik yesil yanardi)', cocuk.length >= 2, cocuk);

kontrol('D1 #bannerRow <main>in ILK cocugu (index 0)', cocuk[0] === 'bannerRow', cocuk[0]);
kontrol('D2 #katPanels hemen ARDINDAN geliyor (index 1)', cocuk[1] === 'katPanels', cocuk[1]);

console.log('\n[E] BANNER GOVDESI — tasima SIRA degisikligiydi, ICERIK degil');
const banBas = html.indexOf('<div id="bannerRow"');
const banSon = html.indexOf('\n  </div>', banBas);
const ban = html.slice(banBas, banSon);
kontrol('E0 #bannerRow govdesi ayiklandi', banBas !== -1 && banSon !== -1 && ban.length > 200,
        ban.length);
kontrol('E1 iki banner da DURUYOR (#jenBanner "Olcuye Ozel Uretim" + Skan Art)',
        /id="jenBanner"/.test(ban) && /skan-banner/.test(ban),
        [/id="jenBanner"/.test(ban), /skan-banner/.test(ban)]);

const yuksek = (ban.match(/fetchpriority="high"/g) || []).length;
bildir('E2-r #bannerRow icindeki fetchpriority="high" sayisi', yuksek);
kontrol('E2 🔴 LCP: #bannerRow icinde fetchpriority="high" YOK (banner artik gorus '
        + 'alaninin EN USTUNDE; yuksek oncelik LCP bandini yerdi)', yuksek === 0, yuksek);

console.log('\n[F] renderGrid GOSTER/GIZLE KOLU — sira degisti, kol DEGISMEDI');
kontrol('F1 renderGrid hala #bannerRow display kolunu tasiyor (banner yalniz ana sayfa '
        + 'gorunumunde; kategori/arama/marka gorunumunde GIZLI)',
        /bannerRow[\s\S]{0,200}?display/.test(html)
        || /getElementById\("bannerRow"\)/.test(html), null);

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
          mc[0] !== 'bannerRow' && mc[0] === 'katPanels', mc[0]);
}

console.log('\n' + (FAILS.length ? 'SONUC: KIRMIZI — kalan ' + FAILS.length : 'SONUC: YESIL'));
process.exit(FAILS.length ? 1 : 0);
