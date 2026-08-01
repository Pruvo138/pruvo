#!/usr/bin/env node
"use strict";
/**
 * PARITE MUTASYON NOBETI — "kabul testi gercekten NOBET TUTUYOR mu?"
 *
 *   node tools/parite-mutasyon-test.js            # 8 mutant + pozitif kontrol
 *   node tools/parite-mutasyon-test.js 5          # yalniz M5
 *
 * NEDEN VAR (olculdu, 27 Tem): parite karar cekirdeginin (tools/parite-ortak.js) tasiyici
 * savunmalarindan IKISI NOBETSIZDI — kaldirildiklarinda TUM fikstur senaryolari yesil
 * kaliyordu (M5 supurme hatasinda fail-OPEN, M6 "D1 EKSIK eslesme" kapisinin kaldirilmasi).
 * "Test var" != "test nobet tutuyor". Bu harness her savunmayi TEK TEK bozar ve
 * tools/parite-fikstur-test.js'in KIRMIZI yanmasini SART kosar; ayrica MUTANTI HANGI
 * SENARYONUN yakaladigini ADIYLA raporlar.
 *
 * NASIL (ana checkout'a DOKUNMADAN): dort dosya (parite-ortak / parite-test / parite-ege /
 * parite-fikstur-test) gecici bir dizine KOPYALANIR, kopya uzerinde metin mutasyonu
 * uygulanir, fikstur oradan kosturulur. Gercek repo dosyalari HIC degismez — mutasyon
 * yarida kesilse bile calisma agaci kirlenemez.
 *
 * KABUL: pozitif kontrol (mutasyonsuz kopya) YESIL + her mutant KIRMIZI. Biri bile
 * yesil kalirsa exit 1 ve "NOBETSIZ MUTANT" yazilir.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const TOOLS = __dirname;
const DOSYALAR = ["parite-ortak.js", "parite-test.js", "parite-ege.js", "parite-fikstur-test.js",
  "parite-yayin-fikstur-test.js"];
const VARSAYILAN_FIKSTUR = "parite-fikstur-test.js";

/**
 * Her mutant: hedef dosyada `ara` metnini `yaz` ile degistirir (TEK sefer, birebir).
 * `ara` bulunamazsa mutant ANLAMSIZDIR -> harness KIRMIZI yanar (kod degisti, nobet bayat).
 * `fikstur` (opsiyonel): mutanti yakalamasi BEKLENEN kabul fiksturu. Yayin penceresi
 * savunmalari AYRI fiksturdedir (parite-yayin-fikstur-test.js) — varsayilan fikstur o
 * senaryolari HIC kosmaz, yani mutant orada "yakalanmamis" gorunurdu.
 */
const MUTANTLAR = [
  {
    ad: "M1 SIRA (onek) kapisi kaldirildi — sira farki artik ACIKLANAN sayilir",
    dosya: "parite-ortak.js",
    ara: "    if (suzulmus[i] !== bekIds[i]) {",
    yaz: "    if (false) {",
  },
  {
    ad: "M2 'yerelde var / D1'de yok' on-kosul kirmizisi kaldirildi",
    dosya: "parite-ortak.js",
    ara: "  if (eksik.length) {",
    yaz: "  if (false && eksik.length) {",
  },
  {
    ad: "M3 fazlalik/yetim kapisi kaldirildi (size > acik daima tutarli)",
    dosya: "parite-ortak.js",
    ara: "  if (fazlaKume.size > (acik || 0)) {",
    yaz: "  if (false) {",
  },
  {
    ad: "M4 on-kosul SAYIM hatasinda fail-OPEN (kanitsiz siniflandirma acilir)",
    dosya: "parite-ortak.js",
    ara: "    return kapali(\"canli katalog sayisi OLCULEMEDI (\" + (e && e.message) +\n" +
      "      \") -> siniflandirma KAPALI, her ayrisim KIRMIZI\");",
    yaz: "    return { gecikmeModu: true, kirmizi: null, notlar, olculemedi,\n" +
      "      canliSayi: null, yerelSayi, acik: 0 };",
  },
  {
    ad: "M5 SUPURME hatasinda fail-OPEN (kanit yokken 'senkron gecikmesi' damgasi)",
    dosya: "parite-ortak.js",
    ara: "    return kapali(\"id supurmesi TAMAMLANAMADI (\" + (e && e.message) +\n" +
      "      \") -> kanit yok, siniflandirma KAPALI (her ayrisim KIRMIZI)\");",
    yaz: "    return { gecikmeModu: true, kirmizi: null, notlar, olculemedi,\n" +
      "      canliSayi, yerelSayi, acik: 0 };",
  },
  {
    ad: "M6 'D1 EKSIK eslesme' kapisi kaldirildi (toplam < yerel artik ACIKLANAN)",
    dosya: "parite-ortak.js",
    ara: "  if (toplam < bekIds.length) {",
    yaz: "  if (false) {",
  },
  {
    ad: "M7 OLCUM ARIZASI (WAF/429/zaman asimi) 3 yerine 0 uretir",
    dosya: "parite-ortak.js",
    ara: "  if (olc.length) {\n    console.log(\"\\n⚪ ÖLÇÜLEMEDİ",
    yaz: "  if (false) {\n    console.log(\"\\n⚪ ÖLÇÜLEMEDİ",
  },
  {
    ad: "M8 KOK SEBEP GERI GELDI: ariza kararı hatalar[]'dan ONCE verilir (kirmizi silinir)",
    dosya: "parite-ortak.js",
    ara: "  // 1) KIRMIZI DAIMA KAZANIR — ariza olsa da olmasa da.\n  if (kirmiziLar.length) {",
    yaz: "  if (olc.length) {\n    for (const n of olc) console.log(\"   ⚪ \" + n);\n" +
      "    return CIKIS_OLCULEMEDI;\n  }\n  if (kirmiziLar.length) {",
  },
  // ── 8. YUTMA (27 Tem) savunmalari: her biri TEK TEK nobetli mi? ────────────────────
  {
    ad: "M9 UZUNLUK KAPISI kaldirildi (kurban kuyrukta + telafi yine ACIKLANAN sayilir)",
    dosya: "parite-ortak.js",
    ara: "  if (suzulmus.length < yerelBeklenen) {",
    yaz: "  if (false) {",
  },
  {
    ad: "M10 UZUNLUK KAPISI telafi BUTCESINI saymiyor (onek kontrolunu uzunluk sanan surum)",
    dosya: "parite-ortak.js",
    ara: "  const yerelBeklenen = alinan.length - butce;",
    yaz: "  const yerelBeklenen = Math.min(bekIds.length, limit);",
  },
  {
    ad: "M11 TELAFI mantigi gevsetildi: butce = tum pencere (kapi hicbir zaman atesmez)",
    dosya: "parite-ortak.js",
    ara: "  const butce = Math.max(0, toplam - bekIds.length);",
    yaz: "  const butce = alinan.length;",
  },
  {
    ad: "M12 DURUSTLUK: olculemeyen pencerede yine KESIN HUKUM basiliyor",
    dosya: "parite-ortak.js",
    ara: "    if (olculemeyenPencere) {",
    yaz: "    if (false) {",
  },
  {
    ad: "M13 'kesin' bayragi DAIMA true (olculemeyen pencere gorunmez olur)",
    dosya: "parite-ortak.js",
    ara: "  const kesin = !gecikmeModu || alinan.length >= toplam;",
    yaz: "  const kesin = true;",
  },
  {
    // 🔴 ASILMA NOBETI (curutucu notu, 27 Tem): bu mutant eskiden TEMIZ KIRMIZI vermiyor,
    // harness'i ASIYORDU (uc susuyor + zaman asimi yok = sonsuz bekleme). Artik fikstur'un
    // cocuk-sure-siniri devreye girer, senaryo GORUNUR sekilde kirmizi yanar (kod 124).
    ad: "M14 ISTEK ZAMAN ASIMI kaldirildi (susan uc kosumu ASAR)",
    dosya: "parite-ortak.js",
    ara: "        signal: AbortSignal.timeout(ZAMAN_ASIMI_MS),",
    yaz: "        // signal KALDIRILDI (mutant): sonsuz bekleme",
  },
  // ── YAYIN PENCERESI (1 Agu) savunmalari — hepsi AYRI fiksturde nobetli mi? ─────────
  // Her biri "muafiyet fazla genisletildi" hatasinin bir yuzudur: muafiyetin GERCEK
  // kaybi yutmadigini kanitlayan sey, bu mutantlarin TEK TEK kirmizi yakmasidir.
  {
    ad: "M15 GERCEK KAYIP kapisi kaldirildi (D1'de HIC olmayan satir da muaf olur)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "    if (hal.yok.length) {",
    yaz: "    if (false) {",
  },
  {
    ad: "M16 'yayinda ama gorunmuyor' kapisi kaldirildi (uc gerilemesi muaf olur)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "    if (hal.yayinda.length) {",
    yaz: "    if (false) {",
  },
  {
    ad: "M17 KISMI OLCUM kabul edilir (hal donmeyen id sessizce muaf olur)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "  if (eksikOlcum.length) {",
    yaz: "  if (false) {",
  },
  {
    ad: "M18 UST SINIR EKSEN A kaldirildi (saatlerdir taslak + sayfasi canli satir muaf)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "    const asan = zararli.filter((t) => t.yasSn === null || t.yasSn > YAYIN_UST_SINIRI_SN);",
    yaz: "    const asan = [];",
  },
  {
    ad: "M19 UST SINIR EKSEN B kaldirildi (tikanmis deploy sessizce KANONIK sayilir)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "    } else if (eksenBAsti) {",
    yaz: "    } else if (false) {",
  },
  {
    ad: "M20 SAYFA PROBU TAVANI notu dusuruldu (olculmemis yigin KANONIK sayilir)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "    if (!hal.sayfaOlculdu) {",
    yaz: "    if (false) {",
  },
  {
    ad: "M21 TASLAK SUZGECI korpus yerine HER SORGUDA uygulanmaz (kok sikayet geri gelir)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "  const bekIds = (taslakKume && taslakKume.size)\n" +
      "    ? hamBekIds.filter((id) => !taslakKume.has(id))\n" +
      "    : hamBekIds;",
    yaz: "  const bekIds = hamBekIds;",
  },
  {
    ad: "M22 FIKSTUR KACAGI: fikstur modunda canli D1 komutu yine kosar",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "  if (fiksturBayraklari(e).length) return null;",
    yaz: "  // fikstur kapisi KALDIRILDI (mutant)",
  },
];

function kopyaKur() {
  const dizin = fs.mkdtempSync(path.join(os.tmpdir(), "parite-mutasyon-"));
  for (const d of DOSYALAR) fs.copyFileSync(path.join(TOOLS, d), path.join(dizin, d));
  return dizin;
}

// 🔴 BACKSTOP SURE SINIRI: fikstur'un KENDI cocuk-sinir'i (COCUK_SURE_SINIRI_MS) birincil
// savunmadir; bu, o savunmayi da bozan bir mutanta karsi ikinci kattir. Olculen normal
// fikstur suresi ~6,5 sn -> 600 sn ~90x pay. Asilirsa mutant "yakalandi" SAYILMAZ:
// asilma temiz kirmizi degildir, CI job'ini kilitler.
const FIKSTUR_SURE_SINIRI_MS = (() => {
  const n = parseInt(process.env.PARITE_MUTASYON_SURE_MS || "", 10);
  return Number.isFinite(n) && n >= 5000 ? n : 600000;
})();

function fiksturKos(dizin, ad) {
  return new Promise((cozul) => {
    const c = spawn(process.execPath, [path.join(dizin, ad || VARSAYILAN_FIKSTUR)], {
      env: process.env, cwd: os.tmpdir(),
    });
    let cikti = "";
    let bitti = false;
    const zamanlayici = setTimeout(() => {
      if (bitti) return;
      cikti += "\n🔴 BACKSTOP SURE SINIRI ASILDI (" + FIKSTUR_SURE_SINIRI_MS + " ms)\n";
      try { c.kill("SIGKILL"); } catch (e) { /* yok */ }
    }, FIKSTUR_SURE_SINIRI_MS);
    c.stdout.on("data", (d) => { cikti += d; });
    c.stderr.on("data", (d) => { cikti += d; });
    c.on("close", (kod) => {
      bitti = true;
      clearTimeout(zamanlayici);
      cozul({ kod: kod === null ? 124 : kod, cikti });
    });
  });
}

function yakalayanlar(cikti) {
  const out = [];
  const re = /^KALAN-SENARYO: (.+)$/gm;
  let m;
  while ((m = re.exec(cikti)) !== null) out.push(m[1]);
  return out;
}

async function main() {
  const yalniz = parseInt(process.argv[2] || "", 10);
  console.log("═".repeat(78));
  console.log("PARITE MUTASYON NOBETI — %d mutant + 1 pozitif kontrol (ag YOK)", MUTANTLAR.length);
  console.log("═".repeat(78));

  const hatalar = [];

  // ── POZITIF KONTROL: mutasyonsuz kopya YESIL olmali (yoksa mutant sonuclari anlamsiz) ──
  // KULLANILAN HER FIKSTUR ayri ayri kontrol edilir: biri bastan kirmiziysa o fiksturle
  // olculen mutantlarin "yakalandi" sonucu SAHTEDIR.
  const kullanilanFiksturler = [...new Set([VARSAYILAN_FIKSTUR]
    .concat(MUTANTLAR.map((m) => m.fikstur || VARSAYILAN_FIKSTUR)))];
  for (const f of kullanilanFiksturler) {
    const temiz = kopyaKur();
    try {
      const r = await fiksturKos(temiz, f);
      if (r.kod === 0) {
        console.log("\n✅ POZITIF KONTROL (%s): mutasyonsuz kopya YESIL (exit 0)", f);
      } else {
        console.log("\n❌ POZITIF KONTROL BASARISIZ (%s): exit %d", f, r.kod);
        console.log(r.cikti.slice(-1500));
        hatalar.push("pozitif kontrol kirmizi (" + f + ") — mutant sonuclari YORUMLANAMAZ");
      }
    } finally {
      fs.rmSync(temiz, { recursive: true, force: true });
    }
  }

  for (let i = 0; i < MUTANTLAR.length; i++) {
    const m = MUTANTLAR[i];
    if (Number.isFinite(yalniz) && yalniz !== i + 1) continue;
    const dizin = kopyaKur();
    try {
      const yol = path.join(dizin, m.dosya);
      const ham = fs.readFileSync(yol, "utf8");
      if (!ham.includes(m.ara)) {
        console.log("\n❌ %s\n   MUTASYON UYGULANAMADI: capa metni bulunamadi (kod degisti " +
          "-> nobet BAYAT, guncelle)", m.ad);
        hatalar.push(m.ad + " — capa bulunamadi");
        continue;
      }
      fs.writeFileSync(yol, ham.replace(m.ara, m.yaz));
      const r = await fiksturKos(dizin, m.fikstur);
      const yak = yakalayanlar(r.cikti);
      if (r.kod === 1 && yak.length) {
        console.log("\n✅ %s\n   -> fikstur KIRMIZI (exit 1). Yakalayan senaryo(lar):", m.ad);
        for (const s of yak.slice(0, 4)) console.log("      • " + s);
        if (yak.length > 4) console.log("      • (+%d senaryo daha)", yak.length - 4);
      } else if (r.kod === 124) {
        console.log("\n❌ %s\n   -> fikstur ASILDI (backstop sure siniri): mutant TEMIZ " +
          "KIRMIZI vermedi. Asilma yakalama SAYILMAZ — CI job'ini kilitler.", m.ad);
        hatalar.push(m.ad + " — fikstur ASILDI (sure siniri)");
      } else if (r.kod === 2) {
        console.log("\n❌ %s\n   -> fikstur COKTU (exit 2): mutant sozdizimi bozdu, " +
          "nobet KANITLANMADI", m.ad);
        console.log(r.cikti.slice(-800));
        hatalar.push(m.ad + " — fikstur coktu (exit 2)");
      } else {
        console.log("\n❌ NOBETSIZ MUTANT: %s\n   -> fikstur exit %d (yakalayan senaryo: %d)",
          m.ad, r.kod, yak.length);
        hatalar.push(m.ad + " — YAKALANMADI (fikstur exit " + r.kod + ")");
      }
    } finally {
      fs.rmSync(dizin, { recursive: true, force: true });
    }
  }

  console.log("\n" + "═".repeat(78));
  if (hatalar.length) {
    for (const h of hatalar) console.log("  ❌ " + h);
    console.log("SONUC: KIRMIZI ❌ (%d/%d mutant nobetsiz ya da harness bayat)",
      hatalar.length, MUTANTLAR.length);
    process.exit(1);
  }
  console.log("SONUC: YESIL ✅ — %d/%d mutant fikstur tarafindan YAKALANDI",
    MUTANTLAR.length, MUTANTLAR.length);
  process.exit(0);
}

main().catch((e) => { console.error(e); process.exit(2); });
