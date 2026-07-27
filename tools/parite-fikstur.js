#!/usr/bin/env node
"use strict";
/**
 * PARITE GURULTU-AYIRIMI KABUL FIKSTURU — AGSIZ, deterministik, canliya SIFIR istek.
 *
 *   node tools/parite-fikstur.js          # tum senaryolar
 *   node tools/parite-fikstur.js 3        # yalniz 3. senaryo (hizli teshis)
 *
 * NE OLCER: parite-test.js / parite-ege.js'in "gurultu (bayat checkout)" ile "gercek
 * kirilma"yi ayirt edip edemedigini. 27 Tem'de olculen olay: bayat bir worktree'de
 * parite-test.js 108/300 ayrisim sayip KIRMIZI yandi; ayrisimlarin 108/108'i "D1 fazla /
 * yerel eksik" yonundeydi, 0'i sira farkiydi. Yani kod saglikliydi, checkout bayatti.
 *
 * NASIL: yerel HTTP sunucusu sahte bir "D1 /ara + /katalog" ucu kurar. Sahte ucun arama
 * mantigi ELLE KOPYA DEGIL — parite-test.js'in referans fonksiyonlari (site) ve bot'un
 * gercek urunAra'si (Ege) ice aktarilir; yalnizca hangi KATALOGA baktigi degisir. Boylece
 * "yerel katalog == canli katalog" senaryosunda test YESIL yanmak ZORUNDADIR (fikstur'un
 * kendi dogrulugunun kontrolu), ayrisma ancak katalogu bilerek KAYDIRDIGIMIZDA cikar.
 *
 * VERI CAPASI YOK: katalog sentetiktir, sayilar kosum aninda uretilir; hicbir gercek urun
 * id'si / sabit katalog sayisi / SHA / tarih YOKTUR.
 */

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const TOOLS = __dirname;
const REF = require("./parite-test.js");          // norm/haystack/filtered — GERCEK referans
const EGE_MOD = require("./parite-ege.js");       // egeKodu() — GERCEK bot kodu
const PARITE_SITE = path.join(TOOLS, "parite-test.js");
const PARITE_EGE = path.join(TOOLS, "parite-ege.js");

const TUMU = "Tümü";
const IDS_TAVANI = 100;   // gercek /katalog ucunun kendi tavani

// ── Sentetik katalog ─────────────────────────────────────────────────────────
const MARKALAR = ["Audi", "Volvo", "Bmw"];
const KATEGORILER = ["Otomobil", "Marin", "Tamirat", "Ev"];
const PARCALAR = ["menteşe", "conta", "braket", "pervane", "kapak", "klips"];
const SIFATLAR = ["ön", "arka", "sağ", "sol", "üst"];

// ⚠️ KATALOG BOYU: sorgu ureticileri (her iki testte) `kelimeler[i % 90]` gibi indeksler
// kullanir; sozluk 90 AYRI kelimeden kucukse undefined sorgu uretir ve test COKER. Bu
// yuzden her urune BENZERSIZ bir model kelimesi verilip katalog >= 140 tutulur (gercek
// katalogda sozluk on binlerce kelime — bu yalniz fikstur icin gerekli bir alt sinir).
function urunUret(n, onek) {
  const liste = [];
  for (let i = 0; i < n; i++) {
    const marka = MARKALAR[i % MARKALAR.length];
    const parca = PARCALAR[i % PARCALAR.length];
    const sifat = SIFATLAR[i % SIFATLAR.length];
    const model = onek + "model" + i;   // BENZERSIZ kelime -> sozluk yeterince genis
    liste.push({
      id: onek + "-" + i + "-" + parca,
      kategori: KATEGORILER[i % KATEGORILER.length],
      marka: [marka],
      baslik: marka + " " + model + " " + sifat + " " + parca + " tutucu",
      aciklama: "Özel üretim " + parca + " parçası " + model + ". Yaklaşık dış ölçüler: " +
        (20 + i) + " × " + (30 + i) + " × " + (10 + i) + " mm.",
      fiyat: (100 + i) + " TL",
      gorseller: [],
    });
  }
  return liste;
}

// ── Sahte "D1" ucu: /ara (site + ege) ve /katalog (sayfa + ids) ───────────────
function sunucuKur({ canli, EGE, mod403, sayiSapma }) {
  const idx = EGE ? EGE.katalogIndeksle(canli) : null;
  const canliIdHarita = new Map(canli.map((p) => [p.id, p]));

  const sunucu = http.createServer((req, res) => {
    const u = new URL(req.url, "http://127.0.0.1");
    const gonder = (obj, durum) => {
      const g = JSON.stringify(obj);
      res.writeHead(durum || 200, { "content-type": "application/json; charset=utf-8" });
      res.end(g);
    };
    if (mod403) {
      // Cloudflare WAF taklidi: JSON bile degil, duz metin (gercek duvarin davranisi).
      res.writeHead(403, { "content-type": "text/html" });
      res.end("<html>error code: 1010</html>");
      return;
    }
    let limit = parseInt(u.searchParams.get("limit") || "", 10);
    if (!Number.isFinite(limit) || limit < 1) limit = 20;

    if (u.pathname === "/katalog") {
      const ham = (u.searchParams.get("ids") || "").split(",").map((s) => s.trim()).filter(Boolean);
      if (ham.length) {
        const idler = ham.slice(0, IDS_TAVANI);
        const bulunan = idler.map((i) => canliIdHarita.get(i)).filter(Boolean);
        return gonder({ toplam: bulunan.length, urunler: bulunan.map((p) => ({ id: p.id })) });
      }
      // sayiSapma: bayat KV sayim onbellegi / yetim satir taklidi.
      return gonder({ toplam: canli.length + (sayiSapma || 0), sayfa: 1, urunler: [] });
    }

    if (u.pathname === "/ara") {
      const q = u.searchParams.get("q") || "";
      const mod = u.searchParams.get("mod") || "";
      if (mod === "ege") {
        if (!q.trim()) return gonder({ hata: "q gerekli", toplam: 0, urunler: [] }, 400);
        const hepsi = EGE.urunAra(idx, q, Infinity);
        return gonder({ toplam: hepsi.length, urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
      }
      const kat = u.searchParams.get("kategori") || "";
      const marka = u.searchParams.get("marka") || "";
      if (!q.trim() && !kat && !marka) {
        return gonder({ hata: "q, kategori veya marka gerekli", toplam: 0, urunler: [] }, 400);
      }
      const hepsi = REF.filtered(canli, q, kat || TUMU, marka || TUMU);
      return gonder({ toplam: hepsi.length, urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
    }
    return gonder({ hata: "bilinmeyen yol" }, 404);
  });

  return new Promise((cozul) => {
    sunucu.listen(0, "127.0.0.1", () => cozul({ sunucu, port: sunucu.address().port }));
  });
}

// ── Cocuk kosum ──────────────────────────────────────────────────────────────
function kostur(dosya, { araUc, urunlerYolu, argv }) {
  return new Promise((cozul) => {
    const c = spawn(process.execPath, [dosya].concat(argv || []), {
      env: Object.assign({}, process.env, { ARA_UC: araUc, PARITE_URUNLER: urunlerYolu }),
      cwd: path.dirname(TOOLS),
    });
    let cikti = "";
    c.stdout.on("data", (d) => { cikti += d; });
    c.stderr.on("data", (d) => { cikti += d; });
    c.on("close", (kod) => cozul({ kod, cikti }));
  });
}

// ── Iddia toplayici ──────────────────────────────────────────────────────────
let gecen = 0, kalan = 0;
function ONA(kosul, ad, ek) {
  if (kosul) { gecen++; console.log("   ✅ " + ad); return; }
  kalan++;
  console.log("   ❌ " + ad + (ek ? "\n      " + String(ek).replace(/\n/g, "\n      ") : ""));
}
function sayiOku(cikti, etiket) {
  const m = new RegExp(etiket.replace(/[()]/g, "\\$&") + ":\\s*(\\d+)").exec(cikti);
  return m ? parseInt(m[1], 10) : null;
}
// ⚠️ Node coken bir surec de exit 1 doner -> "cikis 1 KIRMIZI" iddiasi COKME ile SAHTE
// yesil yanabilir (yasanan tuzak: S8 boyle gecmis gorunuyordu). Her senaryoda aranir.
function cokmusMu(cikti) {
  return /\bNode\.js v\d/.test(cikti) || /^\s*(TypeError|ReferenceError|SyntaxError):/m.test(cikti);
}

// ── Senaryolar ───────────────────────────────────────────────────────────────
async function senaryoKos({ ad, yerel, canli, EGE, mod403, sayiSapma, dosya, argv, dogrula }) {
  const { sunucu, port } = await sunucuKur({ canli, EGE, mod403, sayiSapma });
  const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "parite-fikstur-"));
  const urunlerYolu = path.join(gecici, "urunler.json");
  fs.writeFileSync(urunlerYolu, JSON.stringify(yerel));
  try {
    const r = await kostur(dosya, {
      araUc: "http://127.0.0.1:" + port + "/ara", urunlerYolu, argv,
    });
    console.log("\n▶ " + ad + "  (yerel=" + yerel.length + " canli=" + canli.length +
      " -> cikis " + r.kod + ")");
    ONA(!cokmusMu(r.cikti), "surec COKMEDI (cikis kodu gercek hukum)",
      cokmusMu(r.cikti) ? r.cikti.slice(-700) : "");
    dogrula(r);
    return r;
  } finally {
    sunucu.close();
    fs.rmSync(gecici, { recursive: true, force: true });
  }
}

async function main() {
  const yalniz = parseInt(process.argv[2] || "", 10);
  const EGE = fs.existsSync(EGE_MOD.BOT) ? await EGE_MOD.egeKodu() : null;

  const TABAN = urunUret(140, "fx");
  const EK = urunUret(9, "yeni");

  const senaryolar = [];

  // 0) SAGLAMA — fikstur dogru mu? yerel == canli ise test YESIL yanmak ZORUNDA.
  senaryolar.push({
    ad: "S0 SAGLAMA: yerel == canli -> cikis 0 (fikstur'un kendi dogrulugu)",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(),
    dogrula: (r) => {
      ONA(r.kod === 0, "cikis 0", r.cikti.slice(-500));
      ONA(/BIREBIR PARITE/.test(r.cikti), "BIREBIR PARITE yaziyor");
      ONA(/siniflandirma KAPALI/.test(r.cikti), "sayilar esit -> siniflandirma KAPALI (eski katilik)");
    },
  });

  // 1) K2 — BAYAT CHECKOUT: canli ILERIDE (yeni urunler katalogun BASINDA). Bugunku
  //    108/300 imzasinin ta kendisi: yalniz "D1 fazla / yerel eksik" yonu.
  senaryolar.push({
    ad: "S1 (K2) BAYAT CHECKOUT: canli = yerel + yeni urunler -> cikis 3, KIRMIZI DEGIL",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN),
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-800));
      ONA(/SENKRON GEC/.test(r.cikti), "gorunur 'SENKRON GECİKMESİ' imzasi");
      ONA(!/PARITE YOK/.test(r.cikti), "KIRMIZI (PARITE YOK) YAZMIYOR");
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0");
      ONA(sayiOku(r.cikti, "ACIKLANAN(senkron)") > 0, "aciklanan > 0 (ayrisimlar SAYILDI, susturulmadi)");
      ONA(/checkout BAYAT/.test(r.cikti), "sebep GORUNUR: checkout BAYAT (yerel N < canli M)");
    },
  });

  // 2) K3-a — TEHLIKELI YON: yerelde VAR, D1'de YOK. Sayilar ESIT DEGIL (gecikme
  //    modunun aciklamaya kalkismasi gereken durum) ama yon TEHLIKELI -> KIRMIZI.
  senaryolar.push({
    ad: "S2 (K3-a) YERELDE VAR / D1'DE YOK (sayilar esit DEGIL) -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN,
    canli: EK.concat(TABAN.filter((p, i) => i !== 7)),
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YERELDE VAR \/ D1'DE YOK/.test(r.cikti), "sebep: yerelde var / D1'de yok");
      ONA(/Ege GOREMEZ/.test(r.cikti), "sonucun bedeli yazili (Ege goremez)");
      ONA(!/SENKRON GEC/.test(r.cikti), "senkron gecikmesine YUVARLANMADI");
    },
  });

  // 3) K3-b — SIRA farki, gecikme modu ACIK iken (en zor durum: gurultu modu sirayi
  //    maskeleyebilir mi?). 4) K4 — AYNI kosumda hem aciklanan hem aciklanamayan var.
  const sirasiBozuk = EK.concat(TABAN.slice());
  const a = EK.length + 1, b = EK.length + 4;
  const tut = sirasiBozuk[a]; sirasiBozuk[a] = sirasiBozuk[b]; sirasiBozuk[b] = tut;
  senaryolar.push({
    ad: "S3 (K3-b + K4) SIRA farki + senkron gurultusu AYNI kosumda -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, canli: sirasiBozuk,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(/SIRA farki/.test(r.cikti), "sebep: SIRA farki (senkronla aciklanamaz)");
      const kirmizi = sayiOku(r.cikti, "ACIKLANAMAYAN");
      const beyaz = sayiOku(r.cikti, "ACIKLANAN(senkron)");
      ONA(kirmizi > 0, "aciklanamayan > 0 (kirmizi=" + kirmizi + ")");
      ONA(beyaz > 0, "K4: ayni kosumda aciklanan > 0 (beyaz=" + beyaz + ") — MASKELEMEDI");
      ONA(/MASKELEMEZ/.test(r.cikti), "cikti maskelenmedigini acikca yaziyor");
    },
  });

  // 4) Yetim satir kapisi: canli'da yerelde OLMAYAN cok id var ama bildirilen sayi
  //    acigi kucuk -> "senkron gecikmesi" aciklamasi TASIMAZ -> KIRMIZI.
  senaryolar.push({
    ad: "S4 YETIM SATIR: gorulen D1 fazlasi > sayi acigi -> aciklama coker, cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), sayiSapma: -(EK.length - 1),
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/yetim satir/.test(r.cikti) || /ACIKLAMAZ/.test(r.cikti),
        "sebep: sayi acigi fazlaligi ACIKLAMIYOR");
    },
  });

  // 5) K7 — WAF/UA: 403 duvari "ayrisma" degil "olculemedi".
  senaryolar.push({
    ad: "S5 (K7) WAF/UA 403 -> cikis 3 + 'ÖLÇÜLEMEDİ: WAF/UA', ayrisma SAYILMAZ",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), mod403: true,
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-600));
      ONA(/ÖLÇÜLEMEDİ: WAF\/UA/.test(r.cikti), "gorunur 'ÖLÇÜLEMEDİ: WAF/UA'");
      ONA(!/PARITE YOK/.test(r.cikti), "KIRMIZI yazmiyor");
      ONA(!/ACIKLANAMAYAN: [1-9]/.test(r.cikti), "ayrisma SAYILMADI");
    },
  });

  // 6-8) Ege tarafi AYNI kurala tabi mi? (bot kaynagi yoksa atlanir)
  if (EGE) {
    senaryolar.push({
      ad: "S6 EGE SAGLAMA: yerel == canli -> cikis 0",
      dosya: PARITE_EGE, yerel: TABAN, canli: TABAN.slice(),
      dogrula: (r) => {
        ONA(r.kod === 0, "cikis 0", r.cikti.slice(-700));
        ONA(/BIREBIR PARITE/.test(r.cikti), "BIREBIR PARITE");
      },
    });
    senaryolar.push({
      ad: "S7 (K2/ege) BAYAT CHECKOUT -> cikis 3, KIRMIZI DEGIL",
      dosya: PARITE_EGE, yerel: TABAN, canli: EK.concat(TABAN),
      dogrula: (r) => {
        ONA(r.kod === 3, "cikis 3", r.cikti.slice(-900));
        ONA(/SENKRON GEC/.test(r.cikti), "'SENKRON GECİKMESİ' imzasi");
        ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0");
      },
    });
    senaryolar.push({
      ad: "S8 (K3-a/ege) YERELDE VAR / D1'DE YOK -> cikis 1 KIRMIZI",
      dosya: PARITE_EGE, yerel: TABAN, canli: EK.concat(TABAN.filter((p, i) => i !== 7)),
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
        ONA(/YERELDE VAR \/ D1'DE YOK/.test(r.cikti), "sebep dogru");
      },
    });
  } else {
    console.log("\n⚪ Ege senaryolari ATLANDI: bot kaynagi yok (" + EGE_MOD.BOT + ")");
  }

  console.log("═".repeat(74));
  console.log("PARITE GURULTU-AYIRIMI FIKSTURU — %d senaryo (ag YOK, canliya 0 istek)",
    senaryolar.length);
  console.log("═".repeat(74));

  for (let i = 0; i < senaryolar.length; i++) {
    if (Number.isFinite(yalniz) && yalniz !== i) continue;
    await senaryoKos(Object.assign({ EGE }, senaryolar[i]));
  }

  console.log("\n" + "═".repeat(74));
  console.log("IDDIA: %d gecti | %d KALDI", gecen, kalan);
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
