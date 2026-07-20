#!/usr/bin/env node
/**
 * KABUL TESTI 4 — /ara ve /katalog gecikme butcesi (FAZ 3).
 *
 *   node tools/faz3-gecikme.js
 *   EDGE_UC=https://pruvo-whatsapp-bot.gmlmz.workers.dev node tools/faz3-gecikme.js
 *
 * BUTCE: p95 < 300 ms (is paketi). Bugunku YEREL arama 15-27 ms — yani edge'e tasimak
 * kullaniciya bir gerileme; butce bu gerilemenin kabul sinirini cizer.
 *
 * ONBELLEK KIRICI SART: iki uc da "max-age=60" ile doner. Nonce olmadan olculen sey
 * CDN/onbellek olur (~5 ms) ve test her zaman YESIL yanar — yani hicbir sey olcmez.
 * Her istek BENZERSIZ nonce alir: her biri Worker'a + D1'e kadar gider.
 *
 * NOT: derin sayfa (OFFSET) ayrica olculur — OFFSET sayfalamasinin bilinen maliyeti;
 * 20k'da bozulursa cozum seq-imleci (WHERE seq < ?), o zaman bu sayi kirmizi yanar.
 *
 * ⚠️ BLOKE (20 Tem 2026): /katalog ucu canlida YOK (Worker ayri repo ~/dev/pruvo-bot).
 * Bu test uc deploy edilene kadar KOSMAZ. "Atlandi" ≠ "yesil".
 *
 * ⚠️ RTT TUZAGI ([[d1-arama-tuzaklari]]): Fethiye→Cloudflare RTT'si tek basina p95'i 300 ms
 * butcesinin ustune itebiliyor (16 Tem: /ara p95 442-468 ms ama Worker-ici 31-53 ms).
 * Karar Worker-ici "ms" sayisina gore verilir; kalibrasyon icin DEGISMEMIS production
 * /ara ucu de olculur — o da kirmizi yaniyorsa asim senin kodundan degil.
 */

const EDGE = process.env.EDGE_UC || "http://127.0.0.1:8787";
const N = 20;                    // is paketi: 20 ardisik istek
const BUTCE_P95 = 300;           // ms

function yuzdelik(dizi, y) {
  const s = [...dizi].sort((a, b) => a - b);
  const i = Math.min(s.length - 1, Math.ceil((y / 100) * s.length) - 1);
  return s[Math.max(0, i)];
}

async function istek(urlYap, i) {
  const u = new URL(urlYap(i));
  u.searchParams.set("_nonce", Date.now().toString(36) + "-" + process.pid + "-" + i);
  const t0 = Date.now();
  const r = await fetch(u, { headers: { "cache-control": "no-cache" } });
  const j = await r.json();
  if (j.hata) throw new Error(j.hata);
  return { rtt: Date.now() - t0, ms: typeof j.ms === "number" ? j.ms : null };
}

async function olc(ad, urlYap) {
  // ISINMA (sayilmaz): ilk istek TLS el sikismasi + baglanti kurulumu oder. Tarayici da
  // baglantiyi acik tutar; bu maliyeti her istege yaymak olcumu YANLIS gosterirdi.
  // Disarida birakildigi burada ACIKCA yaziyor — sayiyi guzellestirmek icin degil.
  try { await istek(urlYap, -1); } catch (e) { /* isinma hatasi asagida zaten yakalanir */ }

  const sureler = [];      // toplam RTT (kullanicinin hissettigi)
  const icSureler = [];    // Worker'in kendi olcusu (D1 + islem) — yanittaki "ms"
  let hata = 0;
  for (let i = 0; i < N; i++) {
    try {
      const r = await istek(urlYap, i);
      sureler.push(r.rtt);
      if (r.ms !== null) icSureler.push(r.ms);
    } catch (e) {
      hata++;
    }
  }
  // NOT: Node'un console.log'u printf dolgusunu (%-34s) DESTEKLEMEZ — elle hizala.
  const etiket = ad.padEnd(32);
  if (!sureler.length) {
    console.log("  ❌ " + etiket + " TUM ISTEKLER HATALI");
    return false;
  }
  const p50 = yuzdelik(sureler, 50), p95 = yuzdelik(sureler, 95);
  const ok = p95 < BUTCE_P95 && hata === 0;
  const s = (n) => String(n).padStart(4);
  // ic = Worker'in kendi suresi. Butce RTT'ye bakar ama iki sayiyi AYIRMAK sart:
  // "ic" buyukse sorun BIZDE (D1/sorgu), "RTT - ic" buyukse sorun AGDA (mesafe/TLS).
  const ic = icSureler.length
    ? "   ic(p50/p95)=" + yuzdelik(icSureler, 50) + "/" + yuzdelik(icSureler, 95) + " ms"
    : "";
  console.log("  " + (ok ? "✅ " : "❌ ") + etiket +
    " p50=" + s(p50) + " ms  p95=" + s(p95) + " ms  max=" + s(Math.max(...sureler)) +
    ic + (hata ? "  (HATA: " + hata + ")" : ""));
  return ok;
}

(async () => {
  console.log("Gecikme testi | uc: %s | %d ardisik istek | butce p95 < %d ms\n", EDGE, N, BUTCE_P95);
  const sorgular = ["audi", "far", "kapi kolu", "motor", "yamaha", "conta", "braket", "vida"];
  const kategoriler = ["Otomobil", "Marin", "Motosiklet", "Elektronik"];
  let hepsi = true;

  hepsi &= await olc("/ara?q= (tek kelime)",
    (i) => EDGE + "/ara?q=" + encodeURIComponent(sorgular[i % sorgular.length]) + "&limit=24");
  hepsi &= await olc("/ara?q= (cok kelimeli)",
    (i) => EDGE + "/ara?q=" + encodeURIComponent(sorgular[i % sorgular.length] + " " + sorgular[(i + 3) % sorgular.length]) + "&limit=24");
  hepsi &= await olc("/katalog (Tumu, sayfa 1)",
    () => EDGE + "/katalog?sayfa=1&boy=24");
  hepsi &= await olc("/katalog (kategori, sayfa 1)",
    (i) => EDGE + "/katalog?kategori=" + encodeURIComponent(kategoriler[i % kategoriler.length]) + "&sayfa=1&boy=24");
  hepsi &= await olc("/katalog (derin sayfa, OFFSET)",
    (i) => EDGE + "/katalog?kategori=Otomobil&sayfa=" + (200 + i) + "&boy=24");
  hepsi &= await olc("/katalog?ids= (sepet)",
    () => EDGE + "/katalog?ids=yamaha-d-tan-takma-motor-burcu-90386-10m16");

  if (!hepsi) {
    console.log("\nSONUC: GECIKME BUTCESI ASILDI ❌");
    process.exit(1);
  }
  console.log("\nSONUC: GECIKME BUTCESI ICINDE ✅ (p95 < %d ms)", BUTCE_P95);
})();
