#!/usr/bin/env node
/**
 * KABUL TESTI 5 — /katalog sayfalama dogrulugu + SIRA KORUNUMU (FAZ 3).
 *
 *   node tools/faz3-sayfalama.js                    # yerel wrangler dev (127.0.0.1:8787)
 *   KATALOG_UC=https://.../katalog node tools/faz3-sayfalama.js
 *
 * NE OLCER (iki ayri iddia, ikisi de sessiz hata sinifi):
 *  1) SAYFALAMA: bir gorunumun TUM sayfalari birlestiginde eksik/mukerrer urun YOK ve
 *     toplam sayisi ile birebir tutuyor. (OFFSET sayfalamasinda klasik hata: sinirdaki
 *     urunun atlanmasi/iki kez gelmesi. Gozle bakinca fark edilmez.)
 *  2) SIRA KORUNUMU: D1'in "ORDER BY seq DESC" sirasi, urunler.json DIZI sirasiyla AYNI mi?
 *     Bu bir VARSAYIM, garanti degil — d1-sync.py seq'i urun D1'e ILK girdiginde veriyor
 *     ve bir daha degistirmiyor. Yeni urun urunler.json'un BASINA eklendigi surece seq
 *     dizi sirasiyla ortusuyor. Ama dizinin ORTASINA urun sokulursa (ya da eski bir urun
 *     silinip yeniden eklenirse) D1 sirasi dosya sirasindan AYRISIR ve site "en yeni ustte"
 *     iddiasini sessizce kaybeder. Bayragi acmadan once bu testin YESIL olmasi SART.
 *
 * ONBELLEK: /katalog "max-age=60" ile doner. Nonce olmadan bu test CDN'i olcer, Worker'i
 * degil ([[d1-arama-tuzaklari]] — parite testinde yasandi, bozuk kod YESIL yanmisti).
 *
 * ⚠️ BLOKE (20 Tem 2026): /katalog ucu canlida YOK (Worker ayri repo ~/dev/pruvo-bot,
 * main'de degil; canli Worker /katalog istegine 403 doner). Bu test uc deploy edilene
 * kadar KOSMAZ — "atlandi" demek "yesil" demek DEGILDIR. Bayragi acmadan once bu test
 * gercek uce karsi YESIL olmali (sayfalama + sira korunumu ikisi de sessiz hata sinifi).
 */

const fs = require("fs");
const path = require("path");

const KOK = path.dirname(__dirname);
const UC = process.env.KATALOG_UC || "http://127.0.0.1:8787/katalog";
const BOY = 100;                 // /katalog sayfa boyu tavani
const NONCE = Date.now().toString(36) + "-" + process.pid;

const PRODUCTS = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));

async function sayfaCek(kategori, marka, sayfa) {
  const u = new URL(UC);
  if (kategori && kategori !== "Tümü") u.searchParams.set("kategori", kategori);
  if (marka && marka !== "Tümü") u.searchParams.set("marka", marka);
  u.searchParams.set("sayfa", String(sayfa));
  u.searchParams.set("boy", String(BOY));
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

/** Bir gorunumun butun sayfalarini gezip id listesini sirasiyla toplar. */
async function tumSayfalar(kategori, marka) {
  const ids = [];
  let sayfa = 1, toplam = null, sonSayfa = null;
  while (true) {
    const d = await sayfaCek(kategori, marka, sayfa);
    if (toplam === null) { toplam = d.toplam; sonSayfa = d.sonSayfa; }
    ids.push(...d.urunler.map((u) => u.id));
    if (sayfa >= d.sonSayfa || d.urunler.length === 0) break;
    sayfa++;
    if (sayfa > 5000) throw new Error("sayfa dongusu bitmedi (guvenlik freni)");
  }
  return { ids, toplam, sonSayfa, sayfaSayisi: sayfa };
}

/** urunler.json'un o gorunum icin BEKLENEN sirasi (dosya sirasi = en yeni ustte). */
function beklenen(kategori, marka) {
  return PRODUCTS.filter((p) => {
    const katOk = !kategori || kategori === "Tümü" || p.kategori === kategori;
    const markaOk = !marka || marka === "Tümü" || (p.marka || []).indexOf(marka) !== -1;
    return katOk && markaOk;
  }).map((p) => p.id);
}

const gorunumler = [
  { kategori: "Tümü", marka: "Tümü" },
  { kategori: "Marin", marka: "Tümü" },
  { kategori: "Otomobil", marka: "Tümü" },   // en buyuk kume (20 Tem: 6.626) — derin OFFSET
  { kategori: "Tamirat", marka: "Tümü" },
  { kategori: "Elektronik", marka: "Tümü" },
  { kategori: "Tümü", marka: "Yamaha" },
  { kategori: "Otomobil", marka: "Toyota" },
];

(async () => {
  console.log("Sayfalama + sira testi | uc: %s | %d urun\n", UC, PRODUCTS.length);
  let kaldi = 0;

  for (const g of gorunumler) {
    const ad = "kategori=" + g.kategori + " marka=" + g.marka;
    let r;
    try {
      r = await tumSayfalar(g.kategori, g.marka);
    } catch (e) {
      console.log("  %s -> ISTEK HATASI: %s", ad, e.message);
      kaldi++;
      continue;
    }
    const bek = beklenen(g.kategori, g.marka);
    const hatalar = [];

    // 1) mukerrer yok
    const benzersiz = new Set(r.ids);
    if (benzersiz.size !== r.ids.length) {
      hatalar.push("MUKERRER: " + (r.ids.length - benzersiz.size) + " tekrar eden id");
    }
    // 2) toplam tutuyor
    if (r.toplam !== bek.length) {
      hatalar.push("SAYI: /katalog=" + r.toplam + " urunler.json=" + bek.length);
    }
    // 3) butun sayfalar birlesince kume tam (eksik yok)
    if (r.ids.length !== bek.length) {
      hatalar.push("TOPLANAN: " + r.ids.length + " kart geldi, beklenen " + bek.length);
    }
    // 4) SIRA: dosya sirasiyla birebir (en yeni ustte)
    const ilkFark = r.ids.findIndex((id, i) => id !== bek[i]);
    if (ilkFark !== -1 && r.ids.length === bek.length) {
      hatalar.push("SIRA " + ilkFark + ". kartta ayristi: /katalog=" + r.ids[ilkFark] +
                   " urunler.json=" + bek[ilkFark]);
    }

    if (hatalar.length) {
      kaldi++;
      console.log("  ❌ %s (%d sayfa)", ad, r.sayfaSayisi);
      for (const h of hatalar) console.log("       " + h);
    } else {
      console.log("  ✅ %s — %d urun / %d sayfa, sira ve kume birebir", ad, r.toplam, r.sayfaSayisi);
    }
  }

  if (kaldi) {
    console.log("\nSONUC: SAYFALAMA/SIRA BOZUK ❌ (%d gorunum ayristi)", kaldi);
    process.exit(1);
  }
  console.log("\nSONUC: SAYFALAMA + SIRA KORUNUMU TAM ✅ (%d gorunum)", gorunumler.length);
})();
