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
 * ═══════════════════════════════════════════════════════════════════════════════
 * 🔴 KARAR HANGI SAYIYA GORE VERILIR (25 Tem 2026 duzeltmesi — HocA bildirimi)
 * ═══════════════════════════════════════════════════════════════════════════════
 * Bu betik ESKIDEN uctan uca RTT'yi butceyle karsilastiriyordu. Fethiye→Cloudflare
 * ag gecikmesi tek basina 300 ms'i asabildigi icin SAGLIKLI bir sistemde KIRMIZI
 * yaniyordu (YANLIS POZITIF), ve tersi de mumkundu: hizli agda yavas bir Worker
 * (ic sure buyuk, RTT kucuk) YESIL yanabiliyordu (YANLIS NEGATIF).
 *
 * ARTIK: karar YALNIZ Worker-ici sureye gore verilir — yanit govdesindeki "ms"
 * alani (Worker'in kendi olctugu D1 + islem suresi; kaynak: pruvo-bot worker/src
 * /ara ve /katalog uclari `ms: Date.now() - basla`). Geriye donuk/ileriye donuk
 * uyum icin "ic" adi da kabul edilir.
 *
 * RTT olculmeye DEVAM EDER ve raporlanir (ag payi = RTT - ic) ama CIKIS KODUNA
 * KARAR VERMEZ. RTT yuksek + ic dusuk ise ekrana bilgi notu duser: sorun agda.
 *
 * ⚠️ OLCULEMEDI, "yesil" DEGILDIR: yanitta ic sure alani yoksa (eski Worker surumu,
 * farkli uc, govde degisimi) ya da uc hic cevap vermiyorsa betik sessizce YESIL de
 * yakmaz, sessizce KIRMIZI da yakmaz — AYRI bir cikis kodu (2) basar. Gerekce: bu
 * bir PERFORMANS nobetcisidir, guvenlik siniri degil; "olcemedim"i "gerileme var"
 * diye raporlamak nobetciyi guvenilmez yapar, "sorun yok" diye raporlamak ise
 * nobetciyi sessizce oldururdu. Cagiran taraf iki durumu AYIRT edebilmelidir.
 *   0 = olculdu, butce icinde
 *   1 = olculdu, WORKER-ICI sure butceyi asti (gercek gerileme) veya istek hatasi
 *   2 = OLCULEMEDI (uc cevap vermedi / yanitta ic sure alani yok)
 * ═══════════════════════════════════════════════════════════════════════════════
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
 */

const EDGE = process.env.EDGE_UC || "http://127.0.0.1:8787";
const BUTCE_P95 = 300;           // ms — WORKER-ICI sure butcesi (RTT'nin degil)

// Ornek buyuklugu. KANONIK = 20. FAZ3_ISTEK_SAYISI YALNIZ fikstur/hata ayiklama
// icindir; kucultuldugunde ciktinin basina UYARI basilir ki kucuk ornekli bir kosum
// "yesil yandi" diye kanonik kabul edilmesin. Kanonik kapi (edge-flip-hazirlik.py)
// bu degiskeni SET ETMEZ.
const N_KANONIK = 20;
const N = (() => {
  const h = parseInt(process.env.FAZ3_ISTEK_SAYISI || "", 10);
  return Number.isFinite(h) && h > 0 ? h : N_KANONIK;
})();

// Cikis kodlari — "olculemedi" ile "butce asildi" AYRI durumlardir.
const CIK_OK = 0;
const CIK_ASIM = 1;
const CIK_OLCULEMEDI = 2;

// Adim durumlari. ASIM ile HATA'nin ikisi de cikis 1'dir ama SEBEPLERI farklidir ve
// raporda KARISTIRILMAZ: "butce asildi" demek varken "istek hata verdi" demek yanlis
// suclamadir (yanlis yere bakilir).
const OK = "OK";
const ASIM = "ASIM";              // worker-ici p95 butceyi asti
const HATA = "HATA";              // istekler kismen hata verdi (uc bozuk)
const OLCULEMEDI = "OLCULEMEDI";

function yuzdelik(dizi, y) {
  const s = [...dizi].sort((a, b) => a - b);
  const i = Math.min(s.length - 1, Math.ceil((y / 100) * s.length) - 1);
  return s[Math.max(0, i)];
}

/** Worker-ici sureyi yanittan cikar. Kanonik alan "ms"; "ic" ileri/geri uyum icin. */
function icSureAl(j) {
  if (j && typeof j.ms === "number" && Number.isFinite(j.ms)) return j.ms;
  if (j && typeof j.ic === "number" && Number.isFinite(j.ic)) return j.ic;
  return null;
}

async function istek(urlYap, i) {
  const u = new URL(urlYap(i));
  u.searchParams.set("_nonce", Date.now().toString(36) + "-" + process.pid + "-" + i);
  const t0 = Date.now();
  const r = await fetch(u, { headers: { "cache-control": "no-cache" } });
  const j = await r.json();
  if (j.hata) throw new Error(j.hata);
  return { rtt: Date.now() - t0, ic: icSureAl(j) };
}

async function olc(ad, urlYap) {
  // ISINMA (sayilmaz): ilk istek TLS el sikismasi + baglanti kurulumu oder. Tarayici da
  // baglantiyi acik tutar; bu maliyeti her istege yaymak olcumu YANLIS gosterirdi.
  // Disarida birakildigi burada ACIKCA yaziyor — sayiyi guzellestirmek icin degil.
  try { await istek(urlYap, -1); } catch (e) { /* isinma hatasi asagida zaten yakalanir */ }

  const rttler = [];       // toplam RTT (kullanicinin hissettigi) — BILGI, karar degil
  const icSureler = [];    // Worker'in kendi olcusu (D1 + islem) — KARAR BUNA GORE
  let hata = 0;
  for (let i = 0; i < N; i++) {
    try {
      const r = await istek(urlYap, i);
      rttler.push(r.rtt);
      if (r.ic !== null) icSureler.push(r.ic);
    } catch (e) {
      hata++;
    }
  }
  // NOT: Node'un console.log'u printf dolgusunu (%-34s) DESTEKLEMEZ — elle hizala.
  const etiket = ad.padEnd(32);
  const s = (n) => String(n).padStart(4);

  // ── OLCULEMEDI 1: uc hic cevap vermedi ────────────────────────────────────────
  // "Kismen hatali" DEGIL "hic veri yok" hali. Uc kapali/deploy edilmemis olmasi
  // bir GECIKME gerilemesi degildir; kirmizi yakmak yanlis suclama olurdu.
  if (!rttler.length) {
    console.log("  ⚪ " + etiket + " OLCULEMEDI — tum istekler hatali (uc cevap vermiyor)");
    return OLCULEMEDI;
  }

  const rttP50 = yuzdelik(rttler, 50), rttP95 = yuzdelik(rttler, 95);

  // ── OLCULEMEDI 2: yanit geldi ama ic sure alani YOK ───────────────────────────
  // Eski Worker surumu / farkli uc / govde degisimi. RTT elimizde ama RTT ile karar
  // VERMIYORUZ (bu betigin duzeltilme sebebi buydu) — o yuzden hukum vermiyoruz.
  if (!icSureler.length) {
    console.log("  ⚪ " + etiket + " OLCULEMEDI — yanitta ic sure alani (\"ms\") yok" +
      "   [bilgi RTT p50/p95=" + rttP50 + "/" + rttP95 + " ms]" +
      (hata ? "  (HATA: " + hata + ")" : ""));
    return OLCULEMEDI;
  }

  const icP50 = yuzdelik(icSureler, 50), icP95 = yuzdelik(icSureler, 95);
  // KARAR: yalnizca ic sure. Istek hatasi (kismi) ayrica kirmizidir — bozuk uc,
  // gecikme hukmunden bagimsiz gercek bir arizadir.
  const butceAsti = icP95 >= BUTCE_P95;
  const gecti = !butceAsti && hata === 0;

  // Ag payi = RTT - ic. "ic" buyukse sorun BIZDE (D1/sorgu), "ag payi" buyukse
  // sorun AGDA (mesafe/TLS) — ve ag payi CIKIS KODUNU ETKILEMEZ.
  console.log("  " + (gecti ? "✅ " : "❌ ") + etiket +
    " ic(p50/p95)=" + s(icP50) + "/" + s(icP95) + " ms" +
    "   [bilgi RTT p50/p95=" + s(rttP50) + "/" + s(rttP95) + " ms" +
    "  ag payi p95≈" + s(Math.max(0, rttP95 - icP95)) + " ms]" +
    (hata ? "  (HATA: " + hata + ")" : ""));

  if (gecti && rttP95 >= BUTCE_P95) {
    console.log("     ℹ️  RTT butcenin ustunde ama WORKER-ICI sure icinde → asim AGDAN" +
      " (mesafe/TLS), kodda gerileme yok.");
  }
  if (gecti) return OK;
  return butceAsti ? ASIM : HATA;
}

(async () => {
  console.log("Gecikme testi | uc: %s | %d ardisik istek | butce: WORKER-ICI p95 < %d ms",
    EDGE, N, BUTCE_P95);
  console.log("(RTT bilgi olarak raporlanir, CIKIS KODUNA KARAR VERMEZ)\n");
  if (N !== N_KANONIK) {
    console.log("⚠️  ORNEK KANONIK DEGIL: N=%d (kanonik %d). Bu kosum kapi kanitı SAYILMAZ.\n",
      N, N_KANONIK);
  }
  const sorgular = ["audi", "far", "kapi kolu", "motor", "yamaha", "conta", "braket", "vida"];
  const kategoriler = ["Otomobil", "Marin", "Motosiklet", "Elektronik"];
  const durumlar = [];

  durumlar.push(await olc("/ara?q= (tek kelime)",
    (i) => EDGE + "/ara?q=" + encodeURIComponent(sorgular[i % sorgular.length]) + "&limit=24"));
  durumlar.push(await olc("/ara?q= (cok kelimeli)",
    (i) => EDGE + "/ara?q=" + encodeURIComponent(sorgular[i % sorgular.length] + " " + sorgular[(i + 3) % sorgular.length]) + "&limit=24"));
  durumlar.push(await olc("/katalog (Tumu, sayfa 1)",
    () => EDGE + "/katalog?sayfa=1&boy=24"));
  durumlar.push(await olc("/katalog (kategori, sayfa 1)",
    (i) => EDGE + "/katalog?kategori=" + encodeURIComponent(kategoriler[i % kategoriler.length]) + "&sayfa=1&boy=24"));
  durumlar.push(await olc("/katalog (derin sayfa, OFFSET)",
    (i) => EDGE + "/katalog?kategori=Otomobil&sayfa=" + (200 + i) + "&boy=24"));
  durumlar.push(await olc("/katalog?ids= (sepet)",
    () => EDGE + "/katalog?ids=yamaha-d-tan-takma-motor-burcu-90386-10m16"));

  // ONCELIK: gercek ariza (ASIM/HATA) her seyi bastirir — olculemeyen bir kardes adim
  // olculmus bir asimi MASKELEMEZ. Sonra OLCULEMEDI. Ucu de yoksa yesil.
  const asim = durumlar.filter((d) => d === ASIM).length;
  const hatali = durumlar.filter((d) => d === HATA).length;
  const olculemedi = durumlar.filter((d) => d === OLCULEMEDI).length;

  if (asim || hatali) {
    if (asim) {
      console.log("\nSONUC: GECIKME BUTCESI ASILDI ❌ (%d adim; worker-ici p95 >= %d ms)",
        asim, BUTCE_P95);
    }
    if (hatali) {
      console.log((asim ? "" : "\n") +
        "SONUC: ISTEK HATASI ❌ (%d adim) — butce DEGIL, uc hata donduruyor.", hatali);
    }
    if (olculemedi) console.log("       (ayrica %d adim OLCULEMEDI)", olculemedi);
    process.exit(CIK_ASIM);
  }
  if (olculemedi) {
    console.log("\nSONUC: OLCULEMEDI ⚪ (%d adim) — ne yesil ne kirmizi. Cikis %d.",
      olculemedi, CIK_OLCULEMEDI);
    console.log("       Sebep: uc cevap vermiyor VEYA yanitta worker-ici sure alani (\"ms\") yok.");
    process.exit(CIK_OLCULEMEDI);
  }
  console.log("\nSONUC: GECIKME BUTCESI ICINDE ✅ (worker-ici p95 < %d ms)", BUTCE_P95);
  process.exit(CIK_OK);
})();
