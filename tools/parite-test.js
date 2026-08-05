#!/usr/bin/env node
/**
 * PARITE TESTI — D1 /ara ucu, sitenin bugunku aramasiyla BIREBIR ayni mi?
 *
 *   node tools/parite-test.js            # ~1200 sorgu
 *   node tools/parite-test.js 300        # daha az sorgu (hizli)
 *
 * NEDEN BOYLE: referans, index.html'deki norm()+haystack()+filtered()
 * fonksiyonlarinin BIREBIR KOPYASI (asagida). Kendi yorumumuzu degil, sitenin
 * BUGUN calisan davranisini olcuyoruz — "yeni indeks eskisine karsi dogrulanabilsin"
 * diye arama edge'e simdi tasiniyor (DEVAM.md, Okan karari 15 Tem).
 *
 * Bu test ayni anda arama metninin (hs) dogrulugunu da kanitlar: D1'e Python
 * (tools/arama.py) yaziyor, referans JS uretiyor. Turkce kucultme farki olsaydi
 * (or. "İ") sonuclar ayrisirdi -> test kirmizi yanardi.
 *
 * Karsilastirilan: (1) toplam eslesme sayisi, (2) donen id listesi SIRASIYLA
 * (seq DESC = katalog sirasi iddiasi da boylece sinanir).
 *
 * ⚠️ CIKIS KODLARI: TEK KAYNAK -> tools/parite-ortak.js dosya basindaki
 *   "CIKIS KODU SOZLESMESI" blogu. Burada IKINCI BIR TABLO YAZILMAZ (ucuncu bir surum
 *   olusmasin diye). Ozet: 0 = parite · 1 = aciklanamayan ayrisim · 3 = OLCULEMEDI.
 *   Yonetici ilke: 1 > 3 > 0; hicbir ariza yolu 0 uretemez.
 * Bu test YEREL checkout'un urunler.json'unu okur; bayat bir worktree'de kosarsa eskiden
 * KIRMIZI yaniyordu (olculdu: 108/300, tamami "D1 fazla" yonunde). Artik ayirt ediliyor.
 */

const fs = require("fs");
const path = require("path");
const ortak = require("./parite-ortak.js");

const KOK = path.dirname(__dirname);
// Katalog yolu: DAIMA bu checkout'un kendisi. PARITE_URUNLER yalniz fikstur/kabul testi
// icin vardir (tools/parite-fikstur.js) — normal kosumda verilmez.
const URUNLER_YOLU = process.env.PARITE_URUNLER || path.join(KOK, "urunler.json");
const UC = process.env.ARA_UC || "https://pruvo-whatsapp-bot.gmlmz.workers.dev/ara";
const LIMIT = 1000;          // /ara'nin azami limiti; ustu sorgular sadece sayidan karsilastirilir
const ESZAMANLI = 8;

// ─── REFERANS = index.html'in GERCEK KODU (kopya DEGIL) ──────────────────────
// 🔴 5 AGU 2026 — BURADA ELLE KOPYA TUTULMAZ, OKUMADAN DOKUNMA:
// Bu dosya eskiden index.html'in norm()+haystack()+filtered() uclusunu ELLE KOPYALIYORDU.
// index.html "marka adiyla yapilan sorgu"yu UYELIK ∪ BASLIKTA TAM KELIME yuklemine
// baglayinca (8913db28) ve uc da ayni kurala gecince (`marka_arama` uyeligi), kopya
// sessizce BAYAT AYNA'ya dondu: test 33/1199 ayrisim basiyordu ama SITE ile UC ARASINDA
// KUSUR YOKTU — sapan taraf testin kendisiydi (olculdu: mini 69/69, haval 2/2, rover 9/9,
// mercedes 1037/1037, seat 90/90, citroën 413/413; kopya sirasiyla 1134/600/91/1041/120/69
// veriyordu). [[ikiz-tanim-sessiz-ayrisma]]
//
// Referans artik tools/index-arama-referansi.js uzerinden index.html'den AYIKLANIP
// CALISTIRILIR: musterinin tarayicisinda kosan yuklemin TA KENDISI. Ikinci bir govde
// olmadigi icin yapisal olarak bayatlayamaz; capa tutmazsa (blok yeniden adlandi,
// cip indeksi uretilemedi) HATA atilir -> OLCULEMEDI (cikis 3), sessiz YESIL DEGIL.
//
// KAPSAM: bu test "site (index.html) ile uc (/ara) ayni kumeyi mi veriyor" olcer.
// Marka sorgusunun IKI GOVDESI (index.html ↔ tools/arama.py) arasindaki parite AYRICA
// tools/marka-liste-test.py'de olculur (68 sorgu, gercek katalog).
const REFERANS = require("./index-arama-referansi.js");
// TEMBEL: modul `require` edildiginde (fikstur/mutasyon harness'i) index.html okunmaz.
function ref() { return REFERANS.referans(); }
function norm(s) { return ref().norm(s); }
function aramaKok(w) { return ref().aramaKok(w); }
function haystack(p) { return ref().haystack(p); }
function filtered(PRODUCTS, query, activeCat, activeBrand) {
  const R = ref();
  // Arama yuklemi: index.html'in TEK ARAMA PLANI (marka sorgusu -> uyelik ∪ baslikta tam
  // kelime; marka olmayan sorgu -> serbest metin). Ikinci kez yazilmaz.
  const plan = R.aramaPlani(query);
  // Marka cipi: index.html filtered() ile AYNI GOVDE (markaUyeMi, KATLAMALI). Duz
  // `indexOf(activeBrand)` yazsaydik "Mercedes" cipi "Mercedes-Benz"li urunu kacirirdi
  // ve cip ile arama sessizce ayrisirdi.
  const hedefMarka = activeBrand === "Tümü" ? null : R.markaKatla(activeBrand);
  return PRODUCTS.filter(function (p) {
    if (activeCat !== "Tümü" && p.kategori !== activeCat) { return false; }
    if (hedefMarka && !R.markaUyeMi(p, hedefMarka)) { return false; }
    return R.aramaPlaniEsler(p, plan);
  });
}
// ─────────────────────────────────────────────────────────────────────────────

// TEMBEL YUKLEME: bu dosya `require` edildiginde (fikstur/mutasyon harness'i) 11 MB'lik
// katalogu OKUMAK GEREKMEZ — ve izole bir temp dizinde kopyasi kosarken orada urunler.json
// olmadigi icin ANINDA COKERDI. Katalog yalniz gercekten gerektiginde okunur.
let _URUNLER_ONBELLEK = null;
function urunleriYukle() {
  if (!_URUNLER_ONBELLEK) {
    _URUNLER_ONBELLEK = JSON.parse(fs.readFileSync(URUNLER_YOLU, "utf8"));
  }
  return _URUNLER_ONBELLEK;
}

/** Gercekci sorgu havuzu: katalogun kendi kelimeleri + markalar + kategoriler + kenar durumlar. */
function sorgulariUret(hedef, urunler) {
  const PRODUCTS = urunler || urunleriYukle();
  const sorgular = [];
  const ekle = (q, kat, marka) => sorgular.push({ q, kat: kat || "Tümü", marka: marka || "Tümü" });

  const markalar = [...new Set(PRODUCTS.flatMap((p) => p.marka || []))];
  const kategoriler = [...new Set(PRODUCTS.map((p) => p.kategori))];

  // Kelime sikligi (basliklardan) — musterinin yazacagi kelimeler
  const sayac = new Map();
  for (const p of PRODUCTS) {
    for (const w of norm(p.baslik || "").split(/\s+/)) {
      if (w.length >= 2) sayac.set(w, (sayac.get(w) || 0) + 1);
    }
  }
  const kelimeler = [...sayac.entries()].sort((a, b) => b[1] - a[1]).map((e) => e[0]);

  // 1) Tek kelime (sik -> nadir)
  for (const w of kelimeler.slice(0, 400)) ekle(w);
  // 2) Marka adlari (kisa marka gurultusu dahil: "opel" vb.)
  for (const m of markalar.slice(0, 150)) ekle(m);
  // 3) Kategori adlari
  for (const k of kategoriler) ekle(k);
  // 4) Cok kelimeli (marka + parca) — asil kullanim
  for (let i = 0; i < 200 && i < markalar.length * 2; i++) {
    const m = markalar[i % markalar.length];
    const w = kelimeler[(i * 7) % Math.min(kelimeler.length, 200)];
    ekle(m + " " + w);
  }
  // 5) Baslik ikilileri (gercek ifadeler)
  for (let i = 0; i < 200; i++) {
    const p = PRODUCTS[(i * 31) % PRODUCTS.length];
    const ws = (p.baslik || "").split(/\s+/).filter(Boolean);
    if (ws.length >= 2) {
      const j = i % Math.max(1, ws.length - 1);
      ekle(ws[j] + " " + ws[j + 1]);
    }
  }
  // 6) Kategori/marka filtresi + arama (FAZ 3 icin)
  for (let i = 0; i < 100; i++) {
    ekle(kelimeler[i % 60], kategoriler[i % kategoriler.length]);
    ekle(kelimeler[(i * 3) % 60], "Tümü", markalar[i % markalar.length]);
  }
  // 7) KENAR DURUMLAR — asil kirilma noktalari
  const kenar = [
    "menteşe", "MENTEŞE", "Menteşe",        // Turkce buyuk/kucuk (İ/I tuzagi)
    "ıspanak", "Işık", "İzmir", "IŞIK",     // noktali/noktasiz I
    "çğöşüâî", "ÇĞÖŞÜ",
    "a4", "x5", "e46", "s3",                // 2 harfli (trigram indeksi kullanamaz)
    "a", "b", "1",                          // tek harf
    "ring", "ing", "pel", "raket",          // ALT-DIZE (kelime basi degil) — FTS5 prefix bunu kaciririrdi
    "o-ring", "o ring",
    "%", "_", "%%", "a%b", "a_b", "100%",   // LIKE joker karakterleri
    "'", "''", "' OR 1=1 --",               // tirnak / enjeksiyon
    "audi   a4",                            // coklu bosluk
    "  bosluk  ",
    "yokboylebirsey12345",                  // sonuc yok
    "audi a4 kapi kolu klips",              // uzun cok kelimeli
  ];
  for (const q of kenar) ekle(q);

  // Karistir (deterministik) ve hedefe kirp
  for (let i = sorgular.length - 1; i > 0; i--) {
    const j = (i * 2654435761) % (i + 1);
    [sorgular[i], sorgular[j]] = [sorgular[j], sorgular[i]];
  }
  return hedef ? sorgular.slice(0, hedef) : sorgular;
}

// Her calisma icin benzersiz — asagiya bak.
const NONCE = ortak.nonceUret();
const SAYAC = ortak.sayacYeni();

async function araSor({ q, kat, marka }) {
  const u = new URL(UC);
  u.searchParams.set("q", q);
  u.searchParams.set("limit", String(LIMIT));
  if (kat !== "Tümü") u.searchParams.set("kategori", kat);
  if (marka !== "Tümü") u.searchParams.set("marka", marka);
  // ONBELLEK KIRICI — SART. /ara "cache-control: public, max-age=60" ile doner; Cloudflare
  // edge'i ISTEK'teki "cache-control: no-cache"i YOK SAYAR (asagidaki header tek basina
  // ISE YARAMIYOR). Bu olmadan test Worker'i degil CDN'i olcer — bozuk bir surum, 60 sn
  // once onbellege girmis DOGRU cevapla YESIL yanabilir. FAZ 2'de yasandi (15 Tem),
  // ayni hata bu dosyada da vardi; parite-ege.js ile ayni cozum.
  u.searchParams.set("_nonce", NONCE);
  // UA: Cloudflare WAF varsayilan urllib/requests UA'sina 403 verir; 403/429 "ayrisma"
  // DEGIL "olculemedi" olarak yukari atilir (ortak.WafHatasi).
  const { govde } = await ortak.canliGetir(u.toString(), SAYAC, ortak.DENEME);
  if (govde && govde.hata) throw new Error(govde.hata);
  return govde;
}

// Referans fonksiyonlari DISA VER: kabul fikstur'u (tools/parite-fikstur.js) sahte "D1"
// ucunu BU fonksiyonlarla kurar. Elle kopya olsaydi fikstur zamanla ESKI davranisi
// dogrulamaya devam ederdi. `require.main` kapisi: import etmek testi KOSTURMAZ.
module.exports = { norm, aramaKok, haystack, filtered, sorgulariUret, urunleriYukle, KOK, LIMIT };

if (require.main === module) (async () => {
  const t0 = Date.now();
  const OLCULEMEDI = [];
  const bitir = (kod) => process.exit(kod);
  // ── REFERANS KURULUMU: HICBIR SEY OLCULMEDEN once ([[hukum-yanlis-birimde]]) ──
  // Referans index.html'den turer; capa tutmazsa (blok yeniden adlandi / cip indeksi
  // uretilemedi) hata sorgu URETIMINDE ya da dongude patlar ve kosum "ayrisma buldu"
  // (cikis 1) ya da ham cokme gibi gorunurdu — halbuki hicbir sey OLCULMEMISTIR.
  // Ariza KENDI biriminde, OLCULEMEDI (cikis 3) olarak raporlanir.
  // 🔴 SIRA ONEMLI: sorgulariUret() norm() cagirir, norm() referansa gider. Bu blok
  // sorgu uretiminden SONRAYA alinirsa fail-closed yol yeniden cikis 1'e duser.
  try {
    ref();
  } catch (e) {
    OLCULEMEDI.push("site arama referansi KURULAMADI (" + (e && e.message) +
      ") -> 0 sorgu olculdu");
    console.log("⚪ " + OLCULEMEDI[0]);
    return bitir(ortak.sonucYaz({
      etiket: "site", gecti: 0, atlandi: 0, hatalar: [], onKosul: null,
      sayac: SAYAC, sn: ((Date.now() - t0) / 1000).toFixed(1),
      fazlaKume: null, olculemedi: OLCULEMEDI,
    }));
  }

  const PRODUCTS = urunleriYukle();
  const YEREL_IDLER = [...new Set(PRODUCTS.map((p) => p.id))];
  const YEREL_ID_KUME = new Set(YEREL_IDLER);
  const hedef = parseInt(process.argv[2] || "", 10);
  const sorgular = sorgulariUret(Number.isFinite(hedef) ? hedef : 0, PRODUCTS);
  console.log("Parite testi: %d sorgu | %d urun (%s) | uc: %s",
    sorgular.length, PRODUCTS.length, URUNLER_YOLU, UC);
  console.log("ISTEK BUTCESI: sorgu(%d) + on-kosul(1) [+ sayilar ayriysa supurme " +
    "min(ceil(%d/%d), tavan %d) = %d parti] | zaman asimi %d ms/istek, deneme %d\n",
    sorgular.length, YEREL_IDLER.length, ortak.IDS_PARTI, ortak.SUPURME_TAVANI,
    Math.min(Math.ceil(YEREL_IDLER.length / ortak.IDS_PARTI), ortak.SUPURME_TAVANI),
    ortak.ZAMAN_ASIMI_MS, ortak.DENEME);

  // Sessiz baypas olmasin: test-only env verildiyse HEM stdout HEM stderr'e (A15).
  const fikstur = ortak.fiksturNotu();
  if (fikstur) {
    console.log("⚠️ " + fikstur);
    console.error("⚠️ " + fikstur);
    OLCULEMEDI.push(fikstur);
  }

  // ── ON-KOSUL: checkout katalogu CANLI ile ayni mi? (gurultu imzasini ayirmak icin) ──
  let onKosul;
  try {
    onKosul = await ortak.onKosulOlc({ uc: UC, yerelIdler: YEREL_IDLER, sayac: SAYAC, nonce: NONCE });
  } catch (e) {
    if (e && e.olcum) {
      // Duvar/ariza on-kosulda: hicbir sorgu OLCULMEDI -> hatalar bos, karar yine
      // TEK noktada verilir (kirmizi bulunsaydi 1 olurdu).
      OLCULEMEDI.push(ortak.olcumNotu(e, "site"));
      OLCULEMEDI.push("on-kosul basarisiz -> 0/" + sorgular.length + " sorgu olculdu");
      return bitir(ortak.sonucYaz({
        etiket: "site", gecti: 0, atlandi: 0, hatalar: [], onKosul: null,
        sayac: SAYAC, sn: ((Date.now() - t0) / 1000).toFixed(1),
        fazlaKume: null, olculemedi: OLCULEMEDI,
      }));
    }
    throw e;
  }
  for (const n of onKosul.notlar) console.log("  " + n);
  if (onKosul.kirmizi) {
    console.log("\nSONUC: PARITE YOK ❌ — %s", onKosul.kirmizi);
    console.log("   (Bu yon katalog farkiyla ACIKLANAMAZ: site gosterir, Ege GOREMEZ.)");
    console.log("canli istek: %d", SAYAC.istek);
    return bitir(ortak.CIKIS_KIRMIZI);
  }

  let gecti = 0, atlandi = 0;
  const hatalar = [];
  const fazlaKume = new Set();
  let sirada = 0;
  let olcumArizasi = null;
  // Pencere ucun ilan ettigi toplami KAPSAMAYAN sorgu sayisi: o sorgularda pencere
  // disindaki yerel id'ler OLCULMEDI -> nihai metin kesin hukum BASMAZ (durustluk kapisi).
  let olculemeyenPencere = 0;

  async function isci() {
    while (sirada < sorgular.length && !olcumArizasi) {
      const s = sorgular[sirada++];
      // Referans: sitenin BUGUNKU sonucu
      const bek = filtered(PRODUCTS, s.q, s.kat, s.marka);
      const bekIds = bek.map((p) => p.id);

      // /ara boş sorgu + filtresiz durumu bilerek reddediyor (tum katalogu dokmemek icin)
      if (!s.q.trim() && s.kat === "Tümü" && s.marka === "Tümü") { atlandi++; continue; }

      let g;
      try { g = await araSor(s); } catch (e) {
        // OLCUM ARIZASI (WAF/429/zaman asimi/tavan) ayrisma DEGIL -> kosumu durdur,
        // ama BULUNMUS kirmizilar silinmez: karar sonucYaz'da verilir.
        if (e && e.olcum) { olcumArizasi = olcumArizasi || e; return; }
        hatalar.push({ ...s, sinif: ortak.SINIF_ACIKLANAMAYAN, sebep: "istek hatasi: " + e.message });
        continue;
      }

      const k = ortak.siniflandir({
        bekIds,
        alinan: (g.urunler || []).map((u) => u.id),
        toplam: g.toplam,
        limit: LIMIT,
        yerelIdKume: YEREL_ID_KUME,
        gecikmeModu: onKosul.gecikmeModu,
        // Kanitlanmis TASLAK (D1'de VAR, yayinda=0) id'ler yerel beklentiden DUSULUR:
        // uc onlari BILEREK gizler, aranabilirlikleri olculebilir bir sey degildir.
        taslakKume: onKosul.taslakIdler,
      });
      for (const id of k.fazla) fazlaKume.add(id);
      if (!k.kesin) olculemeyenPencere++;
      if (k.sinif === ortak.SINIF_GECTI) { gecti++; continue; }
      hatalar.push({ ...s, sinif: k.sinif, sebep: k.sebep });
    }
  }

  await Promise.all(Array.from({ length: ESZAMANLI }, isci));
  const sn = ((Date.now() - t0) / 1000).toFixed(1);

  // 🔴 KOK SEBEP ONARIMI: ariza BURADA cikis vermez, yalnizca NOT olur. Karar
  // hatalar[] degerlendirildikten SONRA sonucYaz()'da verilir (1 > 3 > 0).
  if (olcumArizasi) {
    OLCULEMEDI.push(ortak.olcumNotu(olcumArizasi, "site"));
    OLCULEMEDI.push("kosum ERKEN DURDU: " + (gecti + hatalar.length + atlandi) + "/" +
      sorgular.length + " sorgu olculdu");
  }

  // Aciklama GORULEN fazlaligi tasiyabiliyor mu? Tasimiyorsa (yetim satir) COKER -> KIRMIZI.
  const t = ortak.fazlalikTeshis(fazlaKume, onKosul.acik);
  if (t.kirmizi) {
    hatalar.push({ q: "(kosum geneli)", kat: "-", marka: "-",
      sinif: ortak.SINIF_ACIKLANAMAYAN, sebep: t.kirmizi });
  }

  const kod = ortak.sonucYaz({
    etiket: "site", gecti, atlandi, hatalar, onKosul, sayac: SAYAC, sn, fazlaKume,
    olculemedi: OLCULEMEDI, olculemeyenPencere,
  });
  if (kod === ortak.CIKIS_GECTI) {
    console.log("\nSONUC: BIREBIR PARITE ✅ (%d sorgu, site ile ayni)", gecti);
  } else if (kod === ortak.CIKIS_OLCULEMEDI && !hatalar.length && !OLCULEMEDI.length) {
    console.log("\n(hicbir ayrisim yok)");
  }
  if (kod === ortak.CIKIS_OLCULEMEDI && fikstur && !hatalar.length) {
    // Fikstur modunda "yesil" karsiligi: ayrisim SAYISI sifir. Cikis yine 3.
    console.log("\nFIKSTUR: BIREBIR ESLESTI (%d sorgu) — cikis 0 VERILMEZ (fikstur modu)", gecti);
  }
  return bitir(kod);
})();
