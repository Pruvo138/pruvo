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
 */

const fs = require("fs");
const path = require("path");

const KOK = path.dirname(__dirname);
const UC = process.env.ARA_UC || "https://pruvo-whatsapp-bot.gmlmz.workers.dev/ara";
const LIMIT = 1000;          // /ara'nin azami limiti; ustu sorgular sadece sayidan karsilastirilir
const ESZAMANLI = 8;

// ─── index.html'den BIREBIR KOPYA (referans — degistirme) ────────────────────
function norm(s) {
  return (s || "").toLocaleLowerCase("tr")
    .replace(/ı/g, "i").replace(/İ/g, "i")
    .replace(/ç/g, "c").replace(/ğ/g, "g").replace(/ö/g, "o")
    .replace(/ş/g, "s").replace(/ü/g, "u").replace(/â/g, "a").replace(/î/g, "i");
}
function haystack(p) {
  if (p._hs === undefined) {
    p._hs = norm([p.baslik, p.aciklama, (p.marka || []).join(" "),
                  p.kategori, (p.id || "").replace(/-/g, " ")].join(" "));
  }
  return p._hs;
}
function filtered(PRODUCTS, query, activeCat, activeBrand) {
  var tokens = norm(query).split(/\s+/).filter(Boolean);
  return PRODUCTS.filter(function (p) {
    var catOk = activeCat === "Tümü" || p.kategori === activeCat;
    var brandOk = activeBrand === "Tümü" || (p.marka && p.marka.indexOf(activeBrand) !== -1);
    if (!catOk || !brandOk) { return false; }
    if (tokens.length === 0) { return true; }
    var hs = haystack(p);
    for (var i = 0; i < tokens.length; i++) { if (hs.indexOf(tokens[i]) === -1) { return false; } }
    return true;
  });
}
// ─────────────────────────────────────────────────────────────────────────────

const PRODUCTS = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));

/** Gercekci sorgu havuzu: katalogun kendi kelimeleri + markalar + kategoriler + kenar durumlar. */
function sorgulariUret(hedef) {
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
const NONCE = Date.now().toString(36) + "-" + process.pid;

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
  for (let deneme = 0; deneme < 3; deneme++) {
    try {
      const r = await fetch(u, { headers: { "cache-control": "no-cache" } });
      const j = await r.json();
      if (j.hata) throw new Error(j.hata);
      return j;
    } catch (e) {
      if (deneme === 2) throw e;
      await new Promise((res) => setTimeout(res, 400 * (deneme + 1)));
    }
  }
}

(async () => {
  const hedef = parseInt(process.argv[2] || "", 10);
  const sorgular = sorgulariUret(Number.isFinite(hedef) ? hedef : 0);
  console.log("Parite testi: %d sorgu | %d urun | uc: %s\n", sorgular.length, PRODUCTS.length, UC);

  let gecti = 0, kaldi = 0, atlandi = 0;
  const hatalar = [];
  let sirada = 0;

  async function isci() {
    while (sirada < sorgular.length) {
      const s = sorgular[sirada++];
      // Referans: sitenin BUGUNKU sonucu
      const bek = filtered(PRODUCTS, s.q, s.kat, s.marka);
      const bekIds = bek.map((p) => p.id);

      // /ara boş sorgu + filtresiz durumu bilerek reddediyor (tum katalogu dokmemek icin)
      if (!s.q.trim() && s.kat === "Tümü" && s.marka === "Tümü") { atlandi++; continue; }

      let g;
      try { g = await araSor(s); } catch (e) {
        kaldi++; hatalar.push({ ...s, sebep: "istek hatasi: " + e.message }); continue;
      }

      if (g.toplam !== bekIds.length) {
        kaldi++;
        hatalar.push({ ...s, sebep: `sayi: /ara=${g.toplam} site=${bekIds.length}` });
        continue;
      }
      const alinan = g.urunler.map((u) => u.id);
      const bekKirpik = bekIds.slice(0, LIMIT);
      if (alinan.length !== bekKirpik.length || alinan.some((id, i) => id !== bekKirpik[i])) {
        const ilk = alinan.findIndex((id, i) => id !== bekKirpik[i]);
        kaldi++;
        hatalar.push({ ...s, sebep: `sira/icerik ${ilk}. sirada: /ara=${alinan[ilk]} site=${bekKirpik[ilk]}` });
        continue;
      }
      gecti++;
    }
  }

  const t0 = Date.now();
  await Promise.all(Array.from({ length: ESZAMANLI }, isci));
  const sn = ((Date.now() - t0) / 1000).toFixed(1);

  console.log("gecti: %d | KALDI: %d | atlandi: %d | %s sn", gecti, kaldi, atlandi, sn);
  if (hatalar.length) {
    console.log("\nAYRISAN SORGULAR (ilk 25):");
    for (const h of hatalar.slice(0, 25)) {
      console.log("  q=%j kat=%j marka=%j\n    -> %s", h.q, h.kat, h.marka, h.sebep);
    }
    console.log("\nSONUC: PARITE YOK ❌ (%d/%d ayristi)", kaldi, gecti + kaldi);
    process.exit(1);
  }
  console.log("\nSONUC: BIREBIR PARITE ✅ (%d sorgu, site ile ayni)", gecti);
})();
