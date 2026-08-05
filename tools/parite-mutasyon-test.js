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
 * KABUL: pozitif kontrol (mutasyonsuz kopya) YESIL + her OLDURUCU mutant KIRMIZI +
 * her KONTROL mutanti (`kontrol: true`) YESIL. Oldurucu yesil kalirsa "NOBETSIZ MUTANT",
 * kontrol kirmizi yanarsa "ASIRI-HASSAS NOBET" yazilir; ikisi de exit 1.
 * 🔴 KONTROL SINIFI NEDEN VAR ([[beyan-edilmis-survivor]]): kontrol yoksa DAIMA KIRMIZI
 * bir fikstur butun oldurucuLERI "yakalar" ve nobet ile gurultu ayirt edilemez.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const TOOLS = __dirname;
const DOSYALAR = ["parite-ortak.js", "parite-test.js", "parite-ege.js", "parite-fikstur-test.js",
  "parite-yayin-fikstur-test.js", "index-arama-referansi.js", "ege-marka-referansi.js"];
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
  {
    ad: "M23 EKSEN B ESIGI ETKISIZ: bekleme ust siniri 24 saate cikarildi (5 Agu'da " +
      "olculen 63 dk'lik GERCEK tikanma sessizce KANONIK sayilir)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "const YAYIN_BEKLEME_UST_SINIRI_SN = sayiEnv(\"PARITE_YAYIN_BEKLEME_UST_SINIRI_SN\",\n" +
      "  3600, 30, 86400);",
    yaz: "const YAYIN_BEKLEME_UST_SINIRI_SN = sayiEnv(\"PARITE_YAYIN_BEKLEME_UST_SINIRI_SN\",\n" +
      "  86400, 30, 86400);",
  },
  {
    ad: "M24 BEKLEME TABANI KALDIRILDI: olcu yine 'artefakt yasi' (bosta gecen pencere " +
      "tikanma sayilir — 2 Agu'da olculen YANLIS POZITIF geri gelir)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "  return headYasSn < artefaktYasSn\n" +
      "    ? { beklemeSn: headYasSn, headYasSn, tabani: \"yerel HEAD commit ani\" }\n" +
      "    : { beklemeSn: artefaktYasSn, headYasSn, tabani: \"son yayin ani\" };",
    yaz: "  return { beklemeSn: artefaktYasSn, headYasSn, tabani: \"son yayin ani\" };",
  },
  {
    ad: "M25 FAIL-OPEN: yerel HEAD ani OKUNAMAYINCA bekleme 0 sayiliyor (olcemedigi " +
      "hal sessizce YESILE dusuyor)",
    dosya: "parite-ortak.js", fikstur: "parite-yayin-fikstur-test.js",
    ara: "    return { beklemeSn: artefaktYasSn, headYasSn: null,\n" +
      "      tabani: \"yerel HEAD ani OKUNAMADI -> artefakt yasi (KATI/fail-closed)\" };",
    yaz: "    return { beklemeSn: 0, headYasSn: null,\n" +
      "      tabani: \"yerel HEAD ani OKUNAMADI -> artefakt yasi (KATI/fail-closed)\" };",
  },

  // ══ MARKA EKSENI (06 Agu) — referans KANONIK URETICIDEN mi turuyor? ═══════════════
  // Kapatilan kusur: `?q=<marka>` ucta `marka_arama` UYELIGINE baglandi, referans serbest
  // metinde kaldi -> test KENDI bayatligini "gerileme" diye raporladi (37/847). Asagidaki
  // mutantlar referansi eski/ikiz yukleme dondurur; SM1 (ve SM3) KIRMIZI yakmali.
  {
    ad: "M26 referans ham `marka[]` esitligine dondu (kanonik uretec BYPASS)",
    dosya: "ege-marka-referansi.js",
    ara: "  const { harita } = haritaUret(kok, urunlerYolu);",
    yaz: "  const harita = {};\n" +
      "  for (const u of urunler) { if (u && u.id && (u.marka || []).length) harita[u.id] = u.marka; }",
  },
  {
    ad: "M27 ALIAS COZUMU DUSTU (kolon degeri ham marka evrenine suzuldu -> Vauxhall 0)",
    dosya: "ege-marka-referansi.js",
    ara: "  const satirlar = [...yayinda.keys()].sort().map((m) => ({ m }));",
    yaz: "  const hamEvren = new Set();\n" +
      "  for (const u of urunler) for (const m of (u && u.marka) || []) hamEvren.add(m);\n" +
      "  for (const m of [...yayinda.keys()]) if (!hamEvren.has(m)) yayinda.delete(m);\n" +
      "  const satirlar = [...yayinda.keys()].sort().map((m) => ({ m }));",
  },
  {
    ad: "M28 referans KENDI marka yuklemini yazdi (hicbir sorgu marka sayilmiyor)",
    dosya: "ege-marka-referansi.js",
    ara: "  const kanon = (q) => EGE.markaSorguKanonu(env, q);",
    yaz: "  const kanon = async () => null;",
  },
  {
    ad: "M29 FAIL-CLOSED KALKTI: uretec yokken SESSIZCE eski serbest-metin referansi kosar",
    dosya: "parite-ege.js",
    ara: "  } catch (e) {\n" +
      "    OLCULEMEDI.push(ortak.olcumNotu(e, \"ege\"));\n" +
      "    OLCULEMEDI.push(\"marka referansi KURULAMADI -> 0/\" + sorgular.length + \" sorgu olculdu\");",
    yaz: "  } catch (e) {\n" +
      "    MARKA = { kanon: async () => null, kume: () => [] };\n" +
      "  }\n" +
      "  if (false) {\n" +
      "    OLCULEMEDI.push(\"olu dal\");",
  },

  // ══ KONTROL MUTANTLARI — YESIL KALMALI ═══════════════════════════════════════════
  // 🔴 NEDEN SART ([[beyan-edilmis-survivor]]): kontrol yoksa DAIMA KIRMIZI bir fikstur
  // butun oldurucuLERI "yakalar" ve ayirt edilemez. Bunlar davranisi DEGISTIRMEYEN
  // degisikliklerdir; fikstur YESIL kalmazsa nobet asiri-hassastir (yanlis-pozitif).
  {
    ad: "K1 KONTROL: sorgu havuzunun SIRASI degisti (kume ayni) -> YESIL kalmali",
    kontrol: true,
    dosya: "parite-ege.js",
    ara: "    const j = (i * 2654435761) % (i + 1);",
    yaz: "    const j = (i * 2246822519) % (i + 1);",
  },
  {
    ad: "K2 KONTROL: davranis degistirmeyen yeniden adlandirma -> YESIL kalmali",
    kontrol: true,
    dosya: "ege-marka-referansi.js",
    ara: "    kume: (deger) => yayinda.get(deger) || [],",
    yaz: "    kume: (markaAdi) => yayinda.get(markaAdi) || [],",
  },
  {
    ad: "K3 KONTROL: ILGISIZ alan eklendi (kimse okumuyor) -> YESIL kalmali",
    kontrol: true,
    dosya: "ege-marka-referansi.js",
    ara: "    evrenBoyu: satirlar.length,",
    yaz: "    evrenBoyu: satirlar.length,\n    olculmeyenIlgisizAlan: 0,",
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
    // PARITE_INDEX_KOK: kopya GECICI dizinde kosar, orada index.html YOKTUR. Site arama
    // referansi (tools/index-arama-referansi.js) index.html'i GERCEK agactan okumalidir —
    // verilmezse referans fail-closed HATA atar ve pozitif kontrol de kirmizi yanar
    // (mutant "yakalandi" sanilirdi, halbuki hicbir sey olculmemis olurdu).
    const c = spawn(process.execPath, [path.join(dizin, ad || VARSAYILAN_FIKSTUR)], {
      env: Object.assign({}, process.env, { PARITE_INDEX_KOK: path.dirname(TOOLS) }),
      cwd: os.tmpdir(),
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

  const kosan = { oldurucu: 0, kontrol: 0 };
  for (let i = 0; i < MUTANTLAR.length; i++) {
    const m = MUTANTLAR[i];
    if (Number.isFinite(yalniz) && yalniz !== i + 1) continue;
    if (m.kontrol) kosan.kontrol++; else kosan.oldurucu++;
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
      // KONTROL MUTANTI: beklenti TERSTIR — fikstur YESIL kalmali. Kirmizi yanarsa nobet
      // asiri-hassastir ve "oldurucu yakalandi" sonuclari da anlamini kaybeder.
      if (m.kontrol) {
        if (r.kod === 0) {
          console.log("\n✅ %s\n   -> fikstur YESIL kaldi (exit 0): nobet yanlis-pozitif URETMIYOR", m.ad);
        } else {
          console.log("\n❌ ASIRI-HASSAS NOBET: %s\n   -> fikstur exit %d (yakalayan senaryo: %d)",
            m.ad, r.kod, yak.length);
          for (const s of yak.slice(0, 4)) console.log("      • " + s);
          console.log(r.cikti.slice(-600));
          hatalar.push(m.ad + " — KONTROL KIRMIZI YANDI (fikstur exit " + r.kod + ")");
        }
      } else if (r.kod === 1 && yak.length) {
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
  // 🔴 KOSAN sayilir, TANIMLI degil ([[hukum-yanlis-birimde]]): tek mutantlik teshis
  // kosumu "32/32 kanitlandi" diye OLGUSAL YANLIS basmasin.
  console.log("SONUC: YESIL ✅ — %d/%d oldurucu YAKALANDI + %d/%d kontrol YESIL KALDI" +
    " (tanimli: %d oldurucu + %d kontrol)",
    kosan.oldurucu, kosan.oldurucu, kosan.kontrol, kosan.kontrol,
    MUTANTLAR.filter((m) => !m.kontrol).length, MUTANTLAR.filter((m) => m.kontrol).length);
  process.exit(0);
}

main().catch((e) => { console.error(e); process.exit(2); });
