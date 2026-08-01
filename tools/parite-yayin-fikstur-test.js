#!/usr/bin/env node
"use strict";
/**
 * YAYIN PENCERESI KABUL FIKSTURU — AGSIZ, deterministik, canliya SIFIR istek,
 * canli D1'e SIFIR sorgu (yayin hali komutu SAHTE bir betiktir).
 *
 *   node tools/parite-yayin-fikstur-test.js        # tum senaryolar
 *   node tools/parite-yayin-fikstur-test.js 3      # yalniz 3. senaryo
 *
 * NE OLCER: on-kosulun "YAYIN GECIKMESI" (gecici) ile "GERCEK KAYIP" (kalici) sinifini
 * AYIRIP ayirmadigini. Atomik yayin geregi yeni satir D1'e TASLAK girer (yayinda=0) ve
 * her kesif sorgusu `yayinda = 1` suzer -> taslak satir, uc icin "D1'de HIC YOK" satirdan
 * AYIRT EDILEMEZ. Fikstur tam bu hali canlandirir: satir yerel katalogda VAR, sahte ucun
 * HICBIR yuzeyinde YOK; ayrimi kuran TEK sey yayin hali okumasidir.
 *
 * 🔴 IKI YONLU: her "muafiyet" senaryosunun karsisinda AYNI GIRDIYLE bir FAIL-CLOSED
 * senaryosu vardir. Muafiyetin gercek kaybi YUTMADIGINI kanitlayan tek sey budur.
 *
 * ⚠️ FIKSTUR MODU: PARITE_URUNLER + ARA_UC + PARITE_YAYIN_HALI verilir -> hicbir kosum
 * cikis 0 URETEMEZ (parite-ortak.js FIKSTUR_ENV kurali). "Yesil karsiligi" = cikis 3 +
 * ayrisim 0. Bu yuzden iddialar CIKIS KODU + AYRISIM SAYISI + SEBEP METNI uzerinden
 * kurulur, "yesil yandi" uzerinden DEGIL.
 *
 * VERI CAPASI YOK: katalog sentetiktir, id/sayi/SHA/tarih sabiti YOKTUR.
 */

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const TOOLS = __dirname;
const REF = require("./parite-test.js");     // filtered() — GERCEK site referansi
const EGE_MOD = require("./parite-ege.js");  // egeKodu()  — GERCEK bot kodu
const ORTAK = require("./parite-ortak.js");
const PARITE_SITE = path.join(TOOLS, "parite-test.js");
const PARITE_EGE = path.join(TOOLS, "parite-ege.js");

const TUMU = "Tümü";
const IDS_TAVANI = 100;
const SORGU = "180";
const COCUK_SURE_SINIRI_MS = (() => {
  const n = parseInt(process.env.PARITE_FIKSTUR_SURE_MS || "", 10);
  return Number.isFinite(n) && n >= 1000 ? n : 90000;
})();

// ── Sentetik katalog (sorgu ureticileri >= 90 AYRI kelime ister -> katalog >= 140) ──
const MARKALAR = ["Audi", "Volvo", "Bmw"];
const KATEGORILER = ["Otomobil", "Marin", "Tamirat", "Ev"];
const PARCALAR = ["menteşe", "conta", "braket", "pervane", "kapak", "klips"];
const SIFATLAR = ["ön", "arka", "sağ", "sol", "üst"];

function urunUret(n, onek) {
  const liste = [];
  for (let i = 0; i < n; i++) {
    const marka = MARKALAR[i % MARKALAR.length];
    const parca = PARCALAR[i % PARCALAR.length];
    const model = onek + "model" + i;
    liste.push({
      id: onek + "-" + i + "-" + parca,
      kategori: KATEGORILER[i % KATEGORILER.length],
      marka: [marka],
      baslik: marka + " " + model + " " + SIFATLAR[i % SIFATLAR.length] + " " + parca + " tutucu",
      aciklama: "Özel üretim " + parca + " parçası " + model + ". Yaklaşık dış ölçüler: " +
        (20 + i) + " × " + (30 + i) + " × " + (10 + i) + " mm.",
      fiyat: (100 + i) + " TL",
      gorseller: [],
    });
  }
  return liste;
}

// ── Sahte "D1" ucu ───────────────────────────────────────────────────────────
// GIZLI kume = TASLAK satirin canli davranisi: satir D1'de DURUR ama `yayinda = 1`
// sarti yuzunden /ara'da DA /katalog?ids='de DA /katalog sayiminda DA GORUNMEZ.
// (Gercek uc bunu WHERE ile yapar; fikstur ayni GORUNUR sonucu uretir.)
function sunucuKur({ yerel, gizli, EGE }) {
  const gorunur = yerel.filter((p) => !gizli.has(p.id));
  // EGE null olabilir: bot deposu (AYRI checkout) CI'da YOKTUR. O halde Ege senaryolari
  // ATLANIR; site senaryolari tam olculur. Testi komple 2 ile dusurmek, site eksenini de
  // olculmez kilardi (kapinin CI'da OLU kalmasi = onarilmamis kapi).
  const idx = EGE ? EGE.katalogIndeksle(gorunur) : null;
  const harita = new Map(gorunur.map((p) => [p.id, p]));

  const sunucu = http.createServer((req, res) => {
    const u = new URL(req.url, "http://127.0.0.1");
    const gonder = (obj, durum) => {
      res.writeHead(durum || 200, { "content-type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(obj));
    };
    let limit = parseInt(u.searchParams.get("limit") || "", 10);
    if (!Number.isFinite(limit) || limit < 1) limit = 20;

    if (u.pathname === "/katalog") {
      const ham = (u.searchParams.get("ids") || "").split(",").map((s) => s.trim()).filter(Boolean);
      if (ham.length) {
        const bulunan = ham.slice(0, IDS_TAVANI).map((i) => harita.get(i)).filter(Boolean);
        return gonder({ toplam: bulunan.length, urunler: bulunan.map((p) => ({ id: p.id })) });
      }
      return gonder({ toplam: gorunur.length, sayfa: 1, urunler: [] });
    }
    if (u.pathname === "/ara") {
      const q = u.searchParams.get("q") || "";
      if (u.searchParams.get("mod") === "ege") {
        if (!q.trim()) return gonder({ hata: "q gerekli", toplam: 0, urunler: [] }, 400);
        const hepsi = EGE.urunAra(idx, q, Infinity);
        return gonder({ toplam: hepsi.length, urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
      }
      const kat = u.searchParams.get("kategori") || "";
      const marka = u.searchParams.get("marka") || "";
      if (!q.trim() && !kat && !marka) {
        return gonder({ hata: "q, kategori veya marka gerekli", toplam: 0, urunler: [] }, 400);
      }
      const hepsi = REF.filtered(gorunur, q, kat || TUMU, marka || TUMU);
      return gonder({ toplam: hepsi.length, urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
    }
    return gonder({ hata: "bilinmeyen yol" }, 404);
  });

  return new Promise((cozul) => {
    sunucu.listen(0, "127.0.0.1", () => cozul({
      port: sunucu.address().port,
      kapat() {
        if (typeof sunucu.closeAllConnections === "function") sunucu.closeAllConnections();
        sunucu.close();
      },
    }));
  });
}

// ── SAHTE yayin hali komutu ──────────────────────────────────────────────────
// Gercek komut (tools/yayin-kapisi.py --hal-json) ile AYNI sozlesme: stdin'den id
// listesi, stdout'a TEK JSON. Boylece kapinin okudugu SEKIL gercek ciktiyla ayni olur.
const SAHTE_BETIK = `"use strict";
const fs = require("fs");
const s = JSON.parse(process.env.SAHTE_HAL_SPEC || "{}");
let ham = "";
try { ham = fs.readFileSync(0, "utf8"); } catch (e) { ham = ""; }
const idler = ham.split(/[\\n,]/).map((x) => x.trim()).filter(Boolean);
if (s.patla) { process.stderr.write("sahte yayin-hali arizasi\\n"); process.exit(1); }
if (s.bozukJson) { process.stdout.write("bu JSON degil\\n"); process.exit(0); }
if (s.olculemedi) {
  process.stdout.write(JSON.stringify({ olculdu: false, sebep: "sahte: D1 okunamadi" }) + "\\n");
  process.exit(0);
}
const taslak = new Set(s.taslak || []);
const yok = new Set(s.yok || []);
const yayinda = new Set(s.yayinda || []);
const cikti = { olculdu: true, yok: [], yayinda: [], taslak: [],
  sayfa_olculdu: s.sayfaOlculdu !== false,
  artefakt_yas_sn: s.artefaktYas === null ? null : (s.artefaktYas === undefined ? 300 : s.artefaktYas) };
for (const id of idler) {
  if (s.eksikBirak && s.eksikBirak.indexOf(id) !== -1) continue;   // HIC kolona koyma
  if (yok.has(id)) { cikti.yok.push(id); continue; }
  if (yayinda.has(id)) { cikti.yayinda.push(id); continue; }
  if (taslak.has(id)) {
    cikti.taslak.push({ id: id,
      sayfa: s.sayfa === undefined ? 404 : s.sayfa,
      yas_sn: s.yasSn === undefined ? null : s.yasSn });
    continue;
  }
  cikti.yok.push(id);
}
process.stdout.write(JSON.stringify(cikti) + "\\n");
`;

// ── Cocuk kosum ──────────────────────────────────────────────────────────────
function kostur(dosya, { araUc, urunlerYolu, argv, ekEnv }) {
  return new Promise((cozul) => {
    const c = spawn(process.execPath, [dosya].concat(argv || []), {
      env: Object.assign({}, process.env, { ARA_UC: araUc, PARITE_URUNLER: urunlerYolu }, ekEnv || {}),
      cwd: path.dirname(TOOLS),
    });
    let cikti = "", hataAkisi = "", bitti = false;
    const zamanlayici = setTimeout(() => {
      if (bitti) return;
      const not = "\n🔴 SURE SINIRI ASILDI (" + COCUK_SURE_SINIRI_MS + " ms): cocuk OLDURULDU.\n";
      cikti += not; hataAkisi += not;
      try { c.kill("SIGKILL"); } catch (e) { /* yok */ }
    }, COCUK_SURE_SINIRI_MS);
    c.stdout.on("data", (d) => { cikti += d; });
    c.stderr.on("data", (d) => { cikti += d; hataAkisi += d; });
    c.on("close", (kod) => {
      bitti = true; clearTimeout(zamanlayici);
      cozul({ kod: kod === null ? 124 : kod, cikti, hataAkisi });
    });
  });
}

// ── Iddia toplayici ──────────────────────────────────────────────────────────
let gecen = 0, kalan = 0, aktifSenaryo = "";
const kalanSenaryolar = new Set();
function ONA(kosul, ad, ek) {
  if (kosul) { gecen++; console.log("   ✅ " + ad); return; }
  kalan++; kalanSenaryolar.add(aktifSenaryo);
  console.log("   ❌ " + ad + (ek ? "\n      " + String(ek).replace(/\n/g, "\n      ") : ""));
}
function sayiOku(cikti, etiket) {
  const m = new RegExp(etiket.replace(/[()]/g, "\\$&") + ":\\s*(\\d+)").exec(cikti);
  return m ? parseInt(m[1], 10) : null;
}
function cokmusMu(cikti) {
  return /\bNode\.js v\d/.test(cikti) || /^\s*(TypeError|ReferenceError|SyntaxError):/m.test(cikti);
}
/** Sorgular GERCEKTEN kostu mu? (asil sikayet: 1199 sorgunun HICBIRI kosmuyordu) */
function kosanSorgu(cikti) {
  const g = sayiOku(cikti, "gecti");
  const a = sayiOku(cikti, "ACIKLANAMAYAN");
  const b = sayiOku(cikti, "ACIKLANAN\\(senkron\\)");
  return g === null ? 0 : g + (a || 0) + (b || 0);
}

// ── BIRIM OLCUMU: siniflandir()'in taslak suzgeci (surec/ag YOK) ─────────────
function birimOlc() {
  console.log("\n▶ BIRIM: siniflandir() taslak suzgeci");
  aktifSenaryo = "BIRIM";
  const yerel = new Set(["a", "b", "c"]);
  // B1 Taslak yerel beklentide DURURSA sayi tutmaz -> ACIKLANAMAYAN (onarim ONCESI hal).
  const b1 = ORTAK.siniflandir({ bekIds: ["a", "b"], alinan: ["a"], toplam: 1, limit: 10,
    yerelIdKume: yerel, gecikmeModu: false });
  ONA(b1.sinif === ORTAK.SINIF_ACIKLANAMAYAN, "B1 taslak SUZULMEZSE ayrisim KIRMIZI (kok sikayet)", b1);
  // B2 AYNI girdi + taslak kumesi -> GECTI.
  const b2 = ORTAK.siniflandir({ bekIds: ["a", "b"], alinan: ["a"], toplam: 1, limit: 10,
    yerelIdKume: yerel, gecikmeModu: false, taslakKume: new Set(["b"]) });
  ONA(b2.sinif === ORTAK.SINIF_GECTI, "B2 taslak SUZULUNCE ayni girdi GECER", b2);
  // B3 FAIL-CLOSED: suzgec YALNIZ verilen id'yi kaldirir; baska bir kayip HALA kirmizi.
  const b3 = ORTAK.siniflandir({ bekIds: ["a", "b", "c"], alinan: ["a"], toplam: 1, limit: 10,
    yerelIdKume: yerel, gecikmeModu: false, taslakKume: new Set(["b"]) });
  ONA(b3.sinif === ORTAK.SINIF_ACIKLANAMAYAN,
    "B3 taslak DISI kayip suzgecten SONRA da KIRMIZI (muafiyet gercek kaybi yutmaz)", b3);
  // B4 Bos/verilmemis taslak kumesi eski davranisi BIREBIR korur.
  const b4 = ORTAK.siniflandir({ bekIds: ["a"], alinan: ["a"], toplam: 1, limit: 10,
    yerelIdKume: yerel, gecikmeModu: false, taslakKume: new Set() });
  ONA(b4.sinif === ORTAK.SINIF_GECTI, "B4 bos taslak kumesi eski davranisi bozmaz", b4);
  // B5 SIRA farki taslak suzgeciyle ORTULEMEZ.
  const b5 = ORTAK.siniflandir({ bekIds: ["a", "b", "c"], alinan: ["c", "a"], toplam: 2, limit: 10,
    yerelIdKume: yerel, gecikmeModu: false, taslakKume: new Set(["b"]) });
  ONA(b5.sinif === ORTAK.SINIF_ACIKLANAMAYAN, "B5 SIRA farki suzgecten SONRA da KIRMIZI", b5);
  // B6 Ust sinir sonlu ve makul (sessiz "sinirsiz muafiyet" nobeti).
  ONA(ORTAK.YAYIN_UST_SINIRI_SN > 0 && ORTAK.YAYIN_UST_SINIRI_SN <= 86400,
    "B6 taslak yasi UST SINIRI sonlu (sinirsiz muafiyet YOK)", ORTAK.YAYIN_UST_SINIRI_SN);
  // B7 Fikstur modunda komut VERILMEZSE canli D1'e DOKUNULMAZ (argv null).
  ONA(ORTAK.yayinHaliArgv({ PARITE_URUNLER: "/x" }) === null,
    "B7 FIKSTUR modunda yayin hali komutu YOK -> canli D1 okunmaz");
  ONA(Array.isArray(ORTAK.yayinHaliArgv({})),
    "B8 kanonik kosumda varsayilan komut (yayin-kapisi.py --hal-json) kullanilir");
  ONA(ORTAK.yayinHaliArgv({ PARITE_YAYIN_HALI: "duz-metin" }) === null,
    "B9 bozuk PARITE_YAYIN_HALI sessizce YOK SAYILMAZ (null -> fail-closed)");
  ONA(ORTAK.FIKSTUR_ENV.indexOf("PARITE_YAYIN_HALI") !== -1 &&
      ORTAK.FIKSTUR_ENV.indexOf("PARITE_YAYIN_UST_SINIRI_SN") !== -1,
    "B10 yeni env'ler FIKSTUR_ENV'de (baypas olarak kullanilamaz)");
}

// ── Senaryo kosucu ───────────────────────────────────────────────────────────
async function senaryoKos(s) {
  const sunucu = await sunucuKur(s);
  const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "parite-yayin-"));
  const urunlerYolu = path.join(gecici, "urunler.json");
  const betikYolu = path.join(gecici, "sahte-hal.js");
  fs.writeFileSync(urunlerYolu, JSON.stringify(s.yerel));
  fs.writeFileSync(betikYolu, SAHTE_BETIK);
  aktifSenaryo = s.ad;
  const ekEnv = Object.assign({
    SAHTE_HAL_SPEC: JSON.stringify(s.spec || {}),
  }, s.spec ? { PARITE_YAYIN_HALI: JSON.stringify([process.execPath, betikYolu]) } : {},
  s.ekEnv || {});
  try {
    const r = await kostur(s.dosya, {
      araUc: "http://127.0.0.1:" + sunucu.port + "/ara",
      urunlerYolu, argv: [SORGU], ekEnv,
    });
    console.log("\n▶ " + s.ad + "  (yerel=" + s.yerel.length + " gizli=" + s.gizli.size +
      " -> cikis " + r.kod + ")");
    ONA(!cokmusMu(r.cikti), "surec COKMEDI (cikis kodu gercek hukum)",
      cokmusMu(r.cikti) ? r.cikti.slice(-700) : "");
    ONA(r.kod !== 124, "surec SURE SINIRINA TAKILMADI", r.kod === 124 ? r.cikti.slice(-700) : "");
    ONA(r.kod !== 0, "cikis 0 DEGIL (fikstur modu pariteyi BELGELENDIREMEZ)");
    s.dogrula(r);
    return r;
  } finally {
    sunucu.kapat();
    fs.rmSync(gecici, { recursive: true, force: true });
  }
}

async function main() {
  const yalniz = parseInt(process.argv[2] || "", 10);
  const EGE = fs.existsSync(EGE_MOD.BOT) ? await EGE_MOD.egeKodu() : null;

  const TABAN = urunUret(150, "fx");
  // TASLAK ADAYLARI: katalogun BASINDAN (yeni urun katalogun BASINA eklenir) — gercek
  // partinin imzasi. Ucun HICBIR yuzeyinde gorunmezler.
  const TASLAKLAR = TABAN.slice(0, 6).map((p) => p.id);
  const GIZLI = new Set(TASLAKLAR);
  const BOS = new Set();
  const TAZE = 120;                                  // ust sinirin ALTINDA (sn)
  const YASLI = ORTAK.YAYIN_UST_SINIRI_SN + 60;      // ust sinirin USTUNDE (sn)

  const senaryolar = [];

  // ── 0) YANLIS-POZITIF NOBETI: pencere YOKKEN hicbir sey degismemeli ─────────
  senaryolar.push({
    ad: "Y0 SAGLAMA: taslak YOK -> on-kosul yayin hali OKUMAZ, ayrisim 0",
    dosya: PARITE_SITE, yerel: TABAN, gizli: BOS, spec: { patla: true },
    dogrula: (r) => {
      // spec.patla verildi ama taslak olmadigi icin komut HIC cagrilmamali.
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "ayrisim 0 (yesil karsiligi)", r.cikti.slice(-500));
      ONA(!/YAYIN HALI OKUNAMADI/.test(r.cikti), "sayilar esitken yayin hali HIC OKUNMADI");
      ONA(!/YAYIN GECIKMESI/.test(r.cikti), "gereksiz muafiyet metni BASILMADI");
    },
  });

  // ── 1) ASIL VAKA: taslak satirlar -> KIRMIZI DEGIL + SORGULAR KOSAR ─────────
  senaryolar.push({
    ad: "Y1 YAYIN GECIKMESI: satir D1'de VAR + yayinda=0 -> KIRMIZI DEGIL, sorgular KOSAR",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, sayfa: 404, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod !== 1, "cikis 1 DEGIL (yayin gecikmesi gerileme SAYILMAZ)", r.cikti.slice(-800));
      ONA(/YAYIN GECIKMESI/.test(r.cikti), "sinif ADIYLA basildi");
      ONA(/KIRMIZI DEGIL/.test(r.cikti), "kirmizi olmadigi ACIKCA yazildi");
      ONA(kosanSorgu(r.cikti) > 0, "SORGULAR KOSTU (kok sikayet: 0 sorgu kosuyordu)",
        r.cikti.slice(-500));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "hicbir sorgu ayrismadi", r.cikti.slice(-800));
    },
  });

  // ── 2) FAIL-CLOSED: AYNI girdi, satir D1'de GERCEKTEN YOK -> KIRMIZI ────────
  senaryolar.push({
    ad: "Y2 FAIL-CLOSED (GERCEK KAYIP): satir D1'de HIC YOK -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { yok: TASLAKLAR, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/GERCEK KAYIP/.test(r.cikti), "sinif ADIYLA basildi");
      ONA(/YERELDE VAR \/ D1'DE YOK/.test(r.cikti), "eski (kati) sebep metni KORUNDU");
    },
  });

  // ── 3) FAIL-CLOSED: hal OKUNAMADI -> eski kati davranis AYNEN surer ─────────
  senaryolar.push({
    ad: "Y3 FAIL-CLOSED (OKUNAMADI): yayin hali komutu patlar -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI, spec: { patla: true },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI ('olcemedim' YESIL SAYILMAZ)", r.cikti.slice(-800));
      ONA(/YAYIN HALI OKUNAMADI/.test(r.cikti), "sebep: hal okunamadi");
      ONA(kosanSorgu(r.cikti) === 0, "on-kosulda durdu (eski davranisla AYNI)");
    },
  });
  senaryolar.push({
    ad: "Y4 FAIL-CLOSED (olculdu=false): komut 'olcemedim' derse -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI, spec: { olculemedi: true },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YAYIN HALI OKUNAMADI/.test(r.cikti), "sebep: hal okunamadi");
    },
  });
  senaryolar.push({
    ad: "Y5 FAIL-CLOSED (bozuk JSON): cikti ayristirilamaz -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI, spec: { bozukJson: true },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YAYIN HALI OKUNAMADI/.test(r.cikti), "sebep: hal okunamadi");
    },
  });

  // ── 4) KISMI OLCUM: tek bir id icin hal donmezse TUM okuma gecersiz ─────────
  senaryolar.push({
    ad: "Y6 FAIL-CLOSED (KISMI OLCUM): 1 id icin hal donmez -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, eksikBirak: [TASLAKLAR[0]], artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (kismi cevap KABUL EDILMEZ)", r.cikti.slice(-800));
      ONA(/hal DONMEDI/.test(r.cikti), "sebep: eksik olcum");
    },
  });

  // ── 5) KARISIK: 5 taslak + 1 GERCEK KAYIP -> muafiyet kaybi YUTMAZ ─────────
  senaryolar.push({
    ad: "Y7 KARISIK: 5 taslak + 1 gercek kayip -> muafiyet kaybi YUTMAZ, cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR.slice(1), yok: [TASLAKLAR[0]], sayfa: 404, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/GERCEK KAYIP/.test(r.cikti), "gercek kayip ADIYLA basildi (taslaklar gizlemedi)");
    },
  });

  // ── 6) YAYINDA AMA GORUNMUYOR: yayinda=1 iken uc dondurmuyor -> gerileme ────
  senaryolar.push({
    ad: "Y8 YAYINDA AMA GORUNMUYOR: yayinda=1 satir uc'ta yok -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { yayinda: TASLAKLAR, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YAYINDA AMA GORUNMUYOR/.test(r.cikti), "uc/indeks gerilemesi ADIYLA basildi");
    },
  });

  // ── 7) UST SINIR — EKSEN A (ZARARLI): sayfa CANLI + satir TASLAK ────────────
  senaryolar.push({
    ad: "Y9 UST SINIR A (ZARARLI/TAZE): sayfa 200 + taslak, yas sinir ALTINDA -> KIRMIZI DEGIL",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, sayfa: 200, yasSn: TAZE, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod !== 1, "cikis 1 DEGIL (yayin adimi henuz kosuyor)", r.cikti.slice(-800));
      ONA(kosanSorgu(r.cikti) > 0, "sorgular KOSTU");
    },
  });
  senaryolar.push({
    ad: "Y10 UST SINIR A (ZARARLI/YASLI): sayfa 200 + taslak, yas sinir USTUNDE -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, sayfa: 200, yasSn: YASLI, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (pencere degil TIKANMA)", r.cikti.slice(-800));
      ONA(/TIKANMADIR/.test(r.cikti), "tikanma ADIYLA basildi");
    },
  });
  senaryolar.push({
    ad: "Y11 UST SINIR A (YAS OLCULEMEDI): sayfa 200 + yas null -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, sayfa: 200, artefaktYas: TAZE },   // yasSn verilmedi -> null
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (zararli sinifta 'olcemedim' YESIL DEGIL)",
        r.cikti.slice(-800));
    },
  });

  // ── 8) UST SINIR — EKSEN B (ZARARSIZ): sayfa canli DEGIL ────────────────────
  senaryolar.push({
    ad: "Y12 UST SINIR B (ZARARSIZ/YASLI): artefakt sinir USTUNDE -> KIRMIZI DEGIL ama cikis 3",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, sayfa: 404, artefaktYas: YASLI },
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3 (KIRMIZI DEGIL ama KANONIK de DEGIL)", r.cikti.slice(-900));
      ONA(/UST SINIR/.test(r.cikti), "ust sinir notu basildi");
      ONA(/BELGELENDIRMEZ/.test(r.cikti), "sessiz yesil YOK — belgelendirmedigi yazildi");
      ONA(kosanSorgu(r.cikti) > 0, "sorgular yine de KOSTU");
    },
  });
  senaryolar.push({
    ad: "Y13 UST SINIR B (ARTEFAKT YASI OLCULEMEDI): -> KIRMIZI DEGIL ama cikis 3",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, sayfa: 404, artefaktYas: null },
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-900));
      ONA(/BELGELENDIRMEZ/.test(r.cikti), "belgelendirmedigi yazildi");
    },
  });
  senaryolar.push({
    ad: "Y14 SAYFA PROBU TAVANI: sayfa hali olculmediyse -> KIRMIZI DEGIL ama cikis 3",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, sayfaOlculdu: false, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-900));
      ONA(/TAVANINI asti/.test(r.cikti), "tavan notu basildi");
    },
  });

  // ── 8b) FIKSTUR KAPISI: komut VERILMEZSE canli D1'e DOKUNULMAZ ─────────────
  // (spec YOK -> PARITE_YAYIN_HALI verilmez. Kapi dusserse kabul fiksturu gercek
  // katalogu okumaya baslar: sessiz, pahali ve olcumu KIRLETIR.)
  senaryolar.push({
    ad: "Y18 FIKSTUR KAPISI: yayin hali komutu VERILMEDI -> canli D1 OKUNMAZ, cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, gizli: GIZLI,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (fail-closed)", r.cikti.slice(-800));
      ONA(/FIKSTUR MODU: yayin hali komutu VERILMEDI/.test(r.cikti),
        "canli D1'e DOKUNULMADIGI sebep metninde ADIYLA yazili", r.cikti.slice(-800));
    },
  });

  // ── 9) EGE tarafi: AYNI kural, AYNI iki yon ────────────────────────────────
  senaryolar.push({
    ad: "Y15 (ege) YAYIN GECIKMESI -> KIRMIZI DEGIL, sorgular KOSAR",
    dosya: PARITE_EGE, yerel: TABAN, gizli: GIZLI,
    spec: { taslak: TASLAKLAR, sayfa: 404, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod !== 1, "cikis 1 DEGIL", r.cikti.slice(-800));
      ONA(/YAYIN GECIKMESI/.test(r.cikti), "sinif ADIYLA basildi");
      ONA(kosanSorgu(r.cikti) > 0, "SORGULAR KOSTU", r.cikti.slice(-500));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "hicbir sorgu ayrismadi", r.cikti.slice(-900));
    },
  });
  senaryolar.push({
    ad: "Y16 (ege) FAIL-CLOSED (GERCEK KAYIP) -> cikis 1 KIRMIZI",
    dosya: PARITE_EGE, yerel: TABAN, gizli: GIZLI,
    spec: { yok: TASLAKLAR, artefaktYas: TAZE },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/GERCEK KAYIP/.test(r.cikti), "sinif ADIYLA basildi");
    },
  });
  senaryolar.push({
    ad: "Y17 (ege) FAIL-CLOSED (OKUNAMADI) -> cikis 1 KIRMIZI",
    dosya: PARITE_EGE, yerel: TABAN, gizli: GIZLI, spec: { patla: true },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YAYIN HALI OKUNAMADI/.test(r.cikti), "sebep: hal okunamadi");
    },
  });

  const atlanan = EGE ? 0 : senaryolar.filter((s) => s.dosya === PARITE_EGE).length;
  console.log("YAYIN PENCERESI FIKSTURU — %d senaryo (ag YOK, canli D1'e 0 sorgu)%s",
    senaryolar.length - atlanan,
    atlanan ? "  [" + atlanan + " Ege senaryosu ATLANDI: bot deposu yok — " +
      EGE_MOD.BOT + "]" : "");
  console.log("═".repeat(78));
  if (!Number.isFinite(yalniz)) birimOlc();

  for (let i = 0; i < senaryolar.length; i++) {
    if (Number.isFinite(yalniz) && yalniz !== i) continue;
    if (!EGE && senaryolar[i].dosya === PARITE_EGE) continue;
    await senaryoKos(Object.assign({ EGE }, senaryolar[i]));
  }

  console.log("\n" + "═".repeat(78));
  console.log("IDDIA: %d gecti | %d KALDI", gecen, kalan);
  for (const ad of kalanSenaryolar) console.log("KALAN-SENARYO: " + ad);
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
