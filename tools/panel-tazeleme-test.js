#!/usr/bin/env node
/* KABUL TESTI (D7) — MARKA PANELI OTOMATIK TAZELEME arama/filtre/siralamayi BOZMUYOR.
 *
 * Neden: <meta http-equiv="refresh"> sayfayi bastan yukler ve kullanicinin arama
 * kutusunu / "sadece yapilacaklar" filtresini / siralamasini SIFIRLAR. Panel bunun
 * yerine /veri ucundan periyodik fetch edip TABLOYU YENIDEN CIZER. Bu testin kilitledigi
 * sey tam olarak sudur: tazeleme sonrasi (1) arama metni, (2) filtre kutusu, (3) siralama
 * KORUNUR ve (4) tablo GERCEKTEN yeni veriyi gosterir (tazeleme no-op degil).
 *
 * Deterministik: gercek tarayici/timer YOK. setInterval saplamasi callback'i YAKALAR,
 * test onu ELLE cagirir; fetch saplamasi sabit yeni veri dondurur.
 *
 * Kullanim: node tools/panel-tazeleme-test.js <panel.html yolu>
 * Cikis: 0 = gecti, 1 = kaldi
 */
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');

const yol = process.argv[2];
if (!yol) { console.error('KULLANIM: node tools/panel-tazeleme-test.js <panel.html>'); process.exit(1); }
const html = fs.readFileSync(yol, 'utf8');

const FAILS = [];
function kontrol(ad, kosul) {
  console.log((kosul ? '  PASS  ' : '  FAIL  ') + ad);
  if (!kosul) FAILS.push(ad);
}

// ---- panel script'ini AYIKLA -------------------------------------------------
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('FAIL: <script> blogu bulunamadi'); process.exit(1); }
const src = m[1];
kontrol('panel <script> ayiklandi', src.length > 200);
// Negatif eksen: meta refresh KULLANILMAMALI (filtreyi sifirlar).
// Tarama SCRIPT BLOGU DISINDA yapilir: script icindeki aciklama satiri metni de
// icerebilir ve nobetci kendi belgesinden yanlis-pozitif uretir
// ([[nobetci-kendi-dosyasinda-sizinti]]). Gercek <meta> daima <head>'de, script disinda.
const isaretleme = html.replace(/<script>[\s\S]*?<\/script>/g, '');
kontrol('sayfada (script disi) meta refresh YOK',
        !/<meta\b[^>]*http-equiv\s*=\s*["']?\s*refresh/i.test(isaretleme));
// ... ve nobetci OLU degil: ayni bulucu gercek bir meta refresh'i YAKALIYOR mu
kontrol('nobetci canli: enjekte edilen meta refresh YAKALANIYOR',
        /<meta\b[^>]*http-equiv\s*=\s*["']?\s*refresh/i.test(
          isaretleme.replace('<head>', '<head><meta http-equiv="refresh" content="30">')));
kontrol('tazeleme fetch ile yapiliyor', /fetch\(/.test(src) && /setInterval\(/.test(src));

// ---- MINI DOM ----------------------------------------------------------------
function El(id) {
  this.id = id; this._html = ''; this.textContent = ''; this.value = '';
  this.checked = false; this.children = []; this.dataset = {}; this.onclick = null;
}
Object.defineProperty(El.prototype, 'innerHTML', {
  get() { return this._html; },
  set(v) {
    this._html = String(v);
    // thead icin: data-k tasiyan <th>'leri sahte cocuk olarak uret
    this.children = [];
    const re = /<th\b[^>]*data-k="([^"]+)"[^>]*>/g;
    let mm;
    while ((mm = re.exec(this._html)) !== null) {
      const th = new El(null); th.dataset.k = mm[1]; this.children.push(th);
    }
  },
});
El.prototype.querySelectorAll = function (sel) {
  return sel === 'th' ? this.children : [];
};

const kayit = {};
function el(id) { if (!kayit[id]) kayit[id] = new El(id); return kayit[id]; }
['tm', 'ty', 'tk', 'ts2', 'tsx', 'canli', 'q', 'onlytodo'].forEach(el);
const thead = new El('thead'), tbody = new El('tbody');

const document = {
  getElementById: (id) => el(id),
  querySelector: (sel) => (sel === '#t thead' ? thead : sel === '#t tbody' ? tbody : null),
};

let araliklar = [];
let fetchCevabi = null;
let fetchSayaci = 0;
const ctx = {
  document,
  console,
  setInterval: (fn) => { araliklar.push(fn); return araliklar.length; },
  fetch: async () => {
    fetchSayaci++;
    if (fetchCevabi === null) return { ok: false };
    return { ok: true, json: async () => fetchCevabi };
  },
};
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'panel-inline.js' });

kontrol('setInterval ile tazeleme kaydedildi', araliklar.length === 1);
kontrol('ilk render tabloyu cizdi', tbody.innerHTML.length > 0);

// ilk veride kac satir var (baslangic durumu)
function satirMarkalari() {
  const out = [];
  const re = /<td class="m">([^<]*)<\/td>/g;
  let mm;
  while ((mm = re.exec(tbody.innerHTML)) !== null) out.push(mm[1]);
  return out;
}

// ---- SENARYO -----------------------------------------------------------------
// Panel HTML'i gercek defterden uretilir; CI'da defter YOK -> tum satirlar null.
// Bu yuzden testin verisi SENTETIK: tazeleme cevabini biz veriyoruz, ilk veriyi de
// ayni sekilde enjekte ediyoruz (ilk fetch'i "eski", ikincisini "yeni" yaparak).
const plats = JSON.parse(html.match(/"plats":\s*(\[[^\]]*\])/)[1]);
function satir(m, cells, kirmizi, sari) {
  return { m, cells, t: cells.reduce((s, v) => s + (v || 0), 0), durum: '',
           kirmizi, sari, yapilacak: (kirmizi + sari) > 0 };
}
const bos = plats.map(() => null);
const ESKI = { plats, azOran: 0.5, azMin: 10, ts: 'ESKI-TS', rows: [
  satir('Toyota', plats.map((_, i) => (i === 0 ? 100 : null)), plats.length - 1, 0),
  satir('Toyonaka', bos, plats.length, 0),
  satir('Ford', plats.map(() => 5), 0, 0),
] };
const YENI = { plats, azOran: 0.5, azMin: 10, ts: 'YENI-TS', rows: [
  satir('Toyota', plats.map((_, i) => (i === 0 ? 700 : null)), plats.length - 1, 0),
  satir('Toyonaka', plats.map(() => 1), 0, 0),
  satir('Ford', plats.map(() => 5), 0, 0),
] };

const tazele = araliklar[0];

async function calis() {
  // 1) ESKI veriyi yukle (tazeleme yoluyla) — baslangic zemini
  fetchCevabi = ESKI;
  await tazele();
  kontrol('zemin: tazeleme ESKI veriyi cizdi (3 satir)', satirMarkalari().length === 3);
  kontrol('zemin: ts ESKI-TS', el('tsx').textContent === 'ESKI-TS');

  // 2) KULLANICI DURUMU: arama "toyo", filtre acik degil, siralama Marka'ya (artan) cevrildi
  el('q').value = 'toyo';
  const thMarka = thead.children.find((t) => t.dataset.k === 'm');
  kontrol('Marka basligi tiklanabilir', !!thMarka && typeof thMarka.onclick === 'function');
  thMarka.onclick();                       // sortKey='m', sortDir=1 (artan)
  const oncekiSira = satirMarkalari();
  kontrol('arama uygulandi (yalniz Toyo* satirlari)',
          oncekiSira.length === 2 && oncekiSira.every((x) => x.toLowerCase().startsWith('toyo')));
  kontrol('siralama uygulandi (marka artan): Toyonaka once',
          oncekiSira[0] === 'Toyonaka' && oncekiSira[1] === 'Toyota');

  el('onlytodo').checked = true;
  ctx.document.getElementById('onlytodo');  // no-op, sadece erisim
  // filtreyi uygulamak icin render'i onchange uzerinden tetikle
  // (panel onchange=render baglar; burada tazeleme ile ayni yoldan gecirecegiz)

  // 3) TAZELEME — YENI veri gelir
  fetchCevabi = YENI;
  const fetchOnce = fetchSayaci;
  await tazele();
  kontrol('tazeleme fetch etti', fetchSayaci === fetchOnce + 1);

  // 4) KORUNUM
  kontrol('KORUNDU: arama kutusu metni ("toyo")', el('q').value === 'toyo');
  kontrol('KORUNDU: "sadece yapilacaklar" kutusu isaretli', el('onlytodo').checked === true);
  const sonra = satirMarkalari();
  kontrol('KORUNDU: arama filtresi hala uygulaniyor (yalniz Toyo*)',
          sonra.length >= 1 && sonra.every((x) => x.toLowerCase().startsWith('toyo')));
  // YENI veride Toyonaka yapilacak DEGIL -> "sadece yapilacaklar" ile dusmeli
  kontrol('KORUNDU: filtre YENI veriye uygulandi (Toyonaka dustu)',
          sonra.length === 1 && sonra[0] === 'Toyota');
  // siralama korunumu: filtre tek satira dusurdugu icin ayrica filtresiz kontrol
  el('onlytodo').checked = false;
  await tazele();
  const sonra2 = satirMarkalari();
  kontrol('KORUNDU: siralama (marka artan) tazeleme sonrasi ayni',
          sonra2.length === 2 && sonra2[0] === 'Toyonaka' && sonra2[1] === 'Toyota');

  // 5) TAZELEME GERCEKTEN VERIYI DEGISTIRDI (no-op degil)
  kontrol('TAZE: ts YENI-TS oldu', el('tsx').textContent === 'YENI-TS');
  kontrol('TAZE: Toyota hucresi 100 -> 700', /(^|[^0-9])700([^0-9]|$)/.test(tbody.innerHTML));
  kontrol('TAZE: eski deger (100) tabloda YOK', !/>100</.test(tbody.innerHTML));

  // 6) SUNUCU YOKSA (dosya modu) SESSIZ NO-OP — cokme yok, tablo durur
  fetchCevabi = null;
  const oncekiHtml = tbody.innerHTML;
  await tazele();
  kontrol('fetch basarisizsa tablo BOZULMAZ (sessiz no-op)', tbody.innerHTML === oncekiHtml);

  if (FAILS.length) {
    console.log('\nSONUC: KIRMIZI (%d kontrol kaldi)', FAILS.length);
    process.exit(1);
  }
  console.log('\nSONUC: YESIL');
  process.exit(0);
}
calis().catch((e) => { console.error('COKTU:', e && e.stack || e); process.exit(1); });
