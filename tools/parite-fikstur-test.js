#!/usr/bin/env node
"use strict";
/**
 * PARITE KARAR-CEKIRDEGI KABUL FIKSTURU — AGSIZ, deterministik, canliya SIFIR istek.
 *
 *   node tools/parite-fikstur-test.js          # tum senaryolar
 *   node tools/parite-fikstur-test.js 3        # yalniz 3. senaryo (hizli teshis)
 *
 * NE OLCER: parite-test.js / parite-ege.js'in
 *   (a) "gurultu (katalog farki)" ile "gercek kirilma"yi ayirt edip etmedigini,
 *   (b) YONETICI ILKEYE uyup uymadigini: 1 (KIRMIZI) > 3 (OLCULEMEDI) > 0 (YESIL).
 *       Bulunmus TEK bir aciklanamayan ayrisim varsa, sonradan WAF/429/zaman asimi/tavan
 *       gelse bile sonuc 1 OLMALIDIR; hicbir ariza yolu 0 URETEMEZ.
 *
 * NASIL: yerel HTTP sunucusu sahte bir "D1 /ara + /katalog" ucu kurar ve uzerine ARIZA
 * ENJEKTE eder (403 duvari, 429 hiz siniri, susan uc, /katalog?ids= hatasi, sayim hatasi,
 * /ara'dan urun gizleme). Sahte ucun arama mantigi ELLE KOPYA DEGIL — parite-test.js'in
 * referans fonksiyonlari (site) ve bot'un gercek urunAra'si (Ege) ice aktarilir.
 *
 * ⚠️ FIKSTUR MODU: bu harness PARITE_URUNLER + ARA_UC (ve bazi senaryolarda esik env'leri)
 * verir. Mimar karari (27 Tem): test-only env verilmis bir kosum pariteyi ASLA
 * BELGELENDIREMEZ -> cikis en iyi ihtimalle 3'tur, 0 OLAMAZ. Bu yuzden "yesil" senaryolarin
 * beklentisi `cikis 3 + ACIKLANAMAYAN 0 + ACIKLANAN 0 + 'FIKSTUR: BIREBIR ESLESTI'`dir.
 * (Eskiden S0 cikis 0 bekliyordu; o beklenti PARITE_URUNLER baypasinin ta kendisiydi — A15.)
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
const SORGU = "220";      // her cocuk kosumda sorgu sayisi (hiz; havuz deterministik kirpilir)

// ── Sentetik katalog ─────────────────────────────────────────────────────────
const MARKALAR = ["Audi", "Volvo", "Bmw"];
const KATEGORILER = ["Otomobil", "Marin", "Tamirat", "Ev"];
const PARCALAR = ["menteşe", "conta", "braket", "pervane", "kapak", "klips"];
const SIFATLAR = ["ön", "arka", "sağ", "sol", "üst"];

// ⚠️ KATALOG BOYU: sorgu ureticileri (her iki testte) `kelimeler[i % 90]` gibi indeksler
// kullanir; sozluk 90 AYRI kelimeden kucukse undefined sorgu uretir ve test COKER. Bu
// yuzden her urune BENZERSIZ bir model kelimesi verilip katalog >= 140 tutulur.
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

// ── Sahte "D1" ucu + ARIZA ENJEKSIYONU ───────────────────────────────────────
/**
 * mod403        : her istek 403 (WAF duvari — on-kosuldan itibaren)
 * wafSonraAra   : ilk N /ara isteginden SONRA 403 (KOSUM ORTASINDA duvar)
 * r429SonraAra  : ilk N /ara isteginden SONRA daima 429 (deneme tukenir)
 * r429IlkKere   : ilk N istegi 429, sonra normal (GECICI 429 -> yeniden deneme tutmali)
 * susSonraAra   : ilk N /ara isteginden SONRA hic cevap verme (zaman asimi)
 * idsHata       : /katalog?ids= daima HTTP 500 (supurme KANITI uretilemez)
 * sayimHata     : /katalog?sayfa= daima HTTP 500 (on-kosul sayimi olculemez)
 * gizliAra      : Set<id> — /ara sonuclarindan (ve toplam'dan) DUSURULUR; /katalog'da DURUR
 *                 ("D1'in arama metni/indeksi farkli" = D1 EKSIK eslesme uretici)
 * sayiSapma     : /katalog toplam'ina eklenen sapma (bayat KV sayaci / yetim satir taklidi)
 */
function sunucuKur(secenek) {
  const { canli, EGE, mod403, wafSonraAra, r429SonraAra, r429IlkKere, susSonraAra,
    idsHata, sayimHata, gizliAra, sayiSapma } = secenek;
  const idx = EGE ? EGE.katalogIndeksle(canli) : null;
  const canliIdHarita = new Map(canli.map((p) => [p.id, p]));
  const gizli = gizliAra || new Set();
  let araSayaci = 0;
  let toplamSayac = 0;
  const asiliYanitlar = [];

  const sunucu = http.createServer((req, res) => {
    const u = new URL(req.url, "http://127.0.0.1");
    const gonder = (obj, durum) => {
      const g = JSON.stringify(obj);
      res.writeHead(durum || 200, { "content-type": "application/json; charset=utf-8" });
      res.end(g);
    };
    const duvar = (kod) => {
      // Cloudflare taklidi: JSON bile degil, duz metin (gercek duvarin davranisi).
      res.writeHead(kod, { "content-type": "text/html" });
      res.end("<html>error code: " + (kod === 429 ? "1015" : "1010") + "</html>");
    };
    toplamSayac++;
    if (mod403) return duvar(403);
    if (r429IlkKere && toplamSayac <= r429IlkKere) return duvar(429);

    let limit = parseInt(u.searchParams.get("limit") || "", 10);
    if (!Number.isFinite(limit) || limit < 1) limit = 20;

    if (u.pathname === "/katalog") {
      const ham = (u.searchParams.get("ids") || "").split(",").map((s) => s.trim()).filter(Boolean);
      if (ham.length) {
        if (idsHata) return gonder({ hata: "ids ucu coktu (fikstur)" }, 500);
        const idler = ham.slice(0, IDS_TAVANI);
        const bulunan = idler.map((i) => canliIdHarita.get(i)).filter(Boolean);
        return gonder({ toplam: bulunan.length, urunler: bulunan.map((p) => ({ id: p.id })) });
      }
      if (sayimHata) return gonder({ hata: "sayim ucu coktu (fikstur)" }, 500);
      return gonder({ toplam: canli.length + (sayiSapma || 0), sayfa: 1, urunler: [] });
    }

    if (u.pathname === "/ara") {
      araSayaci++;
      if (wafSonraAra && araSayaci > wafSonraAra) return duvar(403);
      if (r429SonraAra && araSayaci > r429SonraAra) return duvar(429);
      if (susSonraAra && araSayaci > susSonraAra) { asiliYanitlar.push(res); return; }

      const q = u.searchParams.get("q") || "";
      const mod = u.searchParams.get("mod") || "";
      const suz = (liste) => (gizli.size ? liste.filter((p) => !gizli.has(p.id)) : liste);
      if (mod === "ege") {
        if (!q.trim()) return gonder({ hata: "q gerekli", toplam: 0, urunler: [] }, 400);
        const hepsi = suz(EGE.urunAra(idx, q, Infinity));
        return gonder({ toplam: hepsi.length, urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
      }
      const kat = u.searchParams.get("kategori") || "";
      const marka = u.searchParams.get("marka") || "";
      if (!q.trim() && !kat && !marka) {
        return gonder({ hata: "q, kategori veya marka gerekli", toplam: 0, urunler: [] }, 400);
      }
      const hepsi = suz(REF.filtered(canli, q, kat || TUMU, marka || TUMU));
      return gonder({ toplam: hepsi.length, urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
    }
    return gonder({ hata: "bilinmeyen yol" }, 404);
  });

  return new Promise((cozul) => {
    sunucu.listen(0, "127.0.0.1", () => cozul({
      sunucu,
      port: sunucu.address().port,
      kapat() {
        for (const r of asiliYanitlar) { try { r.destroy(); } catch (e) { /* yok */ } }
        if (typeof sunucu.closeAllConnections === "function") sunucu.closeAllConnections();
        sunucu.close();
      },
    }));
  });
}

// ── Cocuk kosum ──────────────────────────────────────────────────────────────
function kostur(dosya, { araUc, urunlerYolu, argv, ekEnv }) {
  return new Promise((cozul) => {
    const c = spawn(process.execPath, [dosya].concat(argv || []), {
      env: Object.assign({}, process.env, { ARA_UC: araUc, PARITE_URUNLER: urunlerYolu },
        ekEnv || {}),
      cwd: path.dirname(TOOLS),
    });
    let cikti = "";
    let hataAkisi = "";
    c.stdout.on("data", (d) => { cikti += d; });
    c.stderr.on("data", (d) => { cikti += d; hataAkisi += d; });
    c.on("close", (kod) => cozul({ kod, cikti, hataAkisi }));
  });
}

// ── Iddia toplayici ──────────────────────────────────────────────────────────
let gecen = 0, kalan = 0;
let aktifSenaryo = "";
const kalanSenaryolar = new Set();
function ONA(kosul, ad, ek) {
  if (kosul) { gecen++; console.log("   ✅ " + ad); return; }
  kalan++;
  kalanSenaryolar.add(aktifSenaryo);
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
/** "Yesil karsiligi" (fikstur modunda): cikis 3 + hic ayrisim yok. */
function fiksturYesil(r) {
  return r.kod === 3 && sayiOku(r.cikti, "ACIKLANAMAYAN") === 0 &&
    sayiOku(r.cikti, "ACIKLANAN(senkron)") === 0 && /FIKSTUR: BIREBIR ESLESTI/.test(r.cikti);
}

// ── Senaryo kosucu ───────────────────────────────────────────────────────────
async function senaryoKos(s) {
  const sunucu = await sunucuKur(s);
  const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "parite-fikstur-"));
  const urunlerYolu = path.join(gecici, "urunler.json");
  fs.writeFileSync(urunlerYolu, JSON.stringify(s.yerel));
  aktifSenaryo = s.ad;
  try {
    const r = await kostur(s.dosya, {
      araUc: "http://127.0.0.1:" + sunucu.port + "/ara",
      urunlerYolu, argv: s.argv || [SORGU], ekEnv: s.ekEnv,
    });
    console.log("\n▶ " + s.ad + "  (yerel=" + s.yerel.length + " canli=" + s.canli.length +
      " -> cikis " + r.kod + ")");
    ONA(!cokmusMu(r.cikti), "surec COKMEDI (cikis kodu gercek hukum)",
      cokmusMu(r.cikti) ? r.cikti.slice(-700) : "");
    // A15 nobeti: fikstur modu uyarisi HER kosumda hem stdout hem STDERR'e dusmeli.
    ONA(/FIKSTUR MODU/.test(r.hataAkisi), "fikstur uyarisi STDERR'e de dustu (yutulamaz)");
    ONA(r.kod !== 0, "cikis 0 DEGIL (PARITE_URUNLER ile parite BELGELENEMEZ)");
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

  const TABAN = urunUret(140, "fx");
  const EK = urunUret(9, "yeni");
  const YETIM = urunUret(1, "yetim");                 // yerelde HIC olmayan tek D1 satiri
  // KIRMIZI URETICI: yerel katalogda VAR olan urunlerin yarisini D1'in ARAMASINDAN gizle
  // (/katalog'da DURURLAR) -> her ilgili sorgu "D1 EKSIK eslesme"/ayrisma verir.
  const GIZLI = new Set(TABAN.filter((p, i) => i % 2 === 0).map((p) => p.id));
  // Zaman asimi senaryolari: kisa esik + tek deneme (yoksa fikstur dakikalarca surer).
  const HIZLI_ZA = { PARITE_ZAMAN_ASIMI_MS: "400", PARITE_DENEME: "1", PARITE_BEKLEME_MS: "1" };
  const HIZLI_429 = { PARITE_DENEME: "2", PARITE_BEKLEME_MS: "1" };

  const senaryolar = [];

  // 0) SAGLAMA — fikstur dogru mu? yerel == canli ise ayrisim SIFIR olmak ZORUNDA.
  senaryolar.push({
    ad: "S0 SAGLAMA: yerel == canli -> ayrisim 0 (fikstur'un kendi dogrulugu) + cikis 3",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(),
    dogrula: (r) => {
      ONA(fiksturYesil(r), "cikis 3 + ayrisim 0 + 'FIKSTUR: BIREBIR ESLESTI'", r.cikti.slice(-600));
      ONA(!/PARITE YOK/.test(r.cikti), "KIRMIZI yazmiyor");
      ONA(/siniflandirma KAPALI/.test(r.cikti), "sayilar esit -> siniflandirma KAPALI (eski katilik)");
    },
  });

  // 1) K4 — BAYAT CHECKOUT: canli ILERIDE (yeni urunler katalogun BASINDA).
  senaryolar.push({
    ad: "S1 (K4) BAYAT CHECKOUT: canli = yerel + yeni urunler -> cikis 3, KIRMIZI DEGIL",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN),
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-800));
      ONA(/SENKRON GEC/.test(r.cikti), "gorunur 'SENKRON GECİKMESİ' imzasi");
      ONA(!/PARITE YOK/.test(r.cikti), "KIRMIZI (PARITE YOK) YAZMIYOR");
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0");
      ONA(sayiOku(r.cikti, "ACIKLANAN(senkron)") > 0,
        "aciklanan > 0 (ayrisimlar SAYILDI, susturulmadi)");
      ONA(/D1 FAZLALIGI: yerel=\d+ < canli=\d+/.test(r.cikti), "kanit SAYIYLA yazili");
    },
  });

  // 2) K4-a — TEHLIKELI YON: yerelde VAR, D1'de YOK -> KIRMIZI.
  senaryolar.push({
    ad: "S2 (K4-a) YERELDE VAR / D1'DE YOK -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN,
    canli: EK.concat(TABAN.filter((p, i) => i !== 7)),
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YERELDE VAR \/ D1'DE YOK/.test(r.cikti), "sebep: yerelde var / D1'de yok");
      ONA(/Ege GOREMEZ/.test(r.cikti), "sonucun bedeli yazili (Ege goremez)");
      ONA(!/SENKRON GEC/.test(r.cikti), "katalog farkina YUVARLANMADI");
    },
  });

  // 3) K4-b — SIRA farki, gecikme modu ACIK iken + AYNI kosumda aciklanan gurultu.
  const sirasiBozuk = EK.concat(TABAN.slice());
  const a = EK.length + 1, b = EK.length + 4;
  const tut = sirasiBozuk[a]; sirasiBozuk[a] = sirasiBozuk[b]; sirasiBozuk[b] = tut;
  senaryolar.push({
    ad: "S3 (K4-b) SIRA farki + katalog gurultusu AYNI kosumda -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, canli: sirasiBozuk,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(/SIRA farki/.test(r.cikti), "sebep: SIRA farki (katalog farkiyla aciklanamaz)");
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "aciklanamayan > 0");
      ONA(sayiOku(r.cikti, "ACIKLANAN(senkron)") > 0, "ayni kosumda aciklanan > 0 — MASKELEMEDI");
      ONA(/MASKELEMEZ/.test(r.cikti), "cikti maskelenmedigini acikca yaziyor");
    },
  });

  // 4) Yetim satir kapisi: gorulen D1 fazlasi > sayi acigi -> aciklama coker -> KIRMIZI.
  senaryolar.push({
    ad: "S4 YETIM SATIR: gorulen D1 fazlasi > sayi acigi -> aciklama coker, cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), sayiSapma: -(EK.length - 1),
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YETIM satir/.test(r.cikti) || /ACIKLAMAZ/.test(r.cikti),
        "sebep: sayi acigi fazlaligi ACIKLAMIYOR (yetim satir imzasi)");
    },
  });

  // 5) WAF/UA: 403 duvari "ayrisma" degil "olculemedi".
  senaryolar.push({
    ad: "S5 WAF/UA 403 (on-kosul) -> cikis 3 + 'ÖLÇÜLEMEDİ: WAF/UA', ayrisma SAYILMAZ",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), mod403: true,
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-600));
      ONA(/ÖLÇÜLEMEDİ: WAF\/UA/.test(r.cikti), "gorunur 'ÖLÇÜLEMEDİ: WAF/UA'");
      ONA(!/PARITE YOK/.test(r.cikti), "KIRMIZI yazmiyor");
      ONA(!/ACIKLANAMAYAN: [1-9]/.test(r.cikti), "ayrisma SAYILMADI");
      ONA(/0\/\d+ sorgu olculdu/.test(r.cikti), "kac sorgunun olculdugu GORUNUR");
    },
  });

  // ── 🔴 KOK SEBEP (B1 / A13 / A14): kosum ORTASINDA ariza, KIRMIZI BULUNMUSKEN ──────
  // Eski kod `if (wafHatasi) process.exit(wafYaz(...))` ile hatalar[]'a HIC BAKMADAN
  // cikiyordu -> 118 (B1) ve 11 (A13/A14) gercek kirmizi SILINIP 3 yaziliyordu.
  senaryolar.push({
    ad: "S6 (K2/KOK SEBEP) KIRMIZI + kosum ortasinda WAF 403 -> cikis 1 (ariza SILEMEZ)",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI, wafSonraAra: 25,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (3'e yuvarlanmadi)", r.cikti.slice(-900));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "bulunan kirmizilar SAYILDI");
      ONA(/OLCUM ARIZASI VAR/.test(r.cikti), "ariza da GORUNUR (yutulmadi)");
      ONA(/WAF\/UA/.test(r.cikti), "arizanin turu yazili (WAF/UA)");
      ONA(/KIRMIZI KAZANIR/.test(r.cikti), "oncelik kurali ciktiya yazili (1 > 3 > 0)");
    },
  });
  senaryolar.push({
    ad: "S7 (K2) KIRMIZI + kosum ortasinda 429 (deneme tukendi) -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI,
    r429SonraAra: 25, ekEnv: HIZLI_429,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "bulunan kirmizilar SAYILDI");
      ONA(/HIZ SINIRI \(429\)/.test(r.cikti), "429 arizasi GORUNUR");
    },
  });
  senaryolar.push({
    ad: "S8 (K2) KIRMIZI + uc SUSUYOR (zaman asimi) -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI,
    susSonraAra: 25, ekEnv: HIZLI_ZA,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "bulunan kirmizilar SAYILDI");
      ONA(/ZAMAN ASIMI/.test(r.cikti), "zaman asimi arizasi GORUNUR");
    },
  });
  senaryolar.push({
    ad: "S9 (K2) KIRMIZI + supurme TAVANI asildi -> cikis 1 (tavan AF vermez)",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), gizliAra: GIZLI,
    ekEnv: { PARITE_SUPURME_TAVANI: "1" },
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(/TAVANI asildi/.test(r.cikti), "tavan asimi GORUNUR");
      ONA(/siniflandirma KAPALI/.test(r.cikti), "kanit yok -> siniflandirma KAPALI (fail-closed)");
    },
  });
  senaryolar.push({
    ad: "S10 (K2) KIRMIZI + on-kosul SAYIMI olculemedi -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI, sayimHata: true,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(/canli katalog sayisi OLCULEMEDI/.test(r.cikti), "sayim arizasi GORUNUR");
    },
  });

  // ── M5 MUTANT NOBETI: supurme hatasinda FAIL-OPEN olursa yakalanmali ──────────────
  senaryolar.push({
    ad: "S11 (M5) SUPURME HATASI (ids ucu 500) + ayrisim -> kanit YOK, cikis 1 (fail-closed)",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), idsHata: true,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (fail-OPEN olsaydi 3 olurdu)", r.cikti.slice(-900));
      ONA(/id supurmesi TAMAMLANAMADI/.test(r.cikti), "supurme hatasi GORUNUR");
      ONA(/kanit yok, siniflandirma KAPALI/.test(r.cikti), "kanit yoksa siniflandirma ACILMAZ");
      ONA(!/SENKRON GEC/.test(r.cikti), "kanitsiz 'senkron gecikmesi' damgasi VURULMADI");
    },
  });

  // ── M6 MUTANT NOBETI: "D1 EKSIK eslesme" kapisi kaldirilirsa yakalanmali ──────────
  // gecikmeModu ACIK (yerel ⊂ canli, supurme kaniti var) ama D1 bazi yerel urunleri
  // ARAMADA gostermiyor -> toplam < yerel. Bu, katalog farkiyla ACIKLANAMAZ.
  senaryolar.push({
    ad: "S12 (M6) gecikme modu ACIK + D1 EKSIK eslesme -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), gizliAra: GIZLI,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (kapi kaldirilsaydi 3 olurdu)", r.cikti.slice(-900));
      ONA(/D1 EKSIK eslesme/.test(r.cikti), "sebep: D1 EKSIK eslesme (yerel ⊆ D1 kanitina aykiri)");
    },
  });

  // ── A8: TESHIS DURUSTLUGU — tek yetim satir, checkout TAZE ───────────────────────
  senaryolar.push({
    ad: "S13 (A8) D1'de TEK YETIM satir, checkout TAZE -> cikis 3 ama YANLIS teshis BASMAZ",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.concat(YETIM),
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3 (0 DEGIL)", r.cikti.slice(-900));
      ONA(!/checkout BAYAT: yerel=/.test(r.cikti),
        "OLGUSAL YANLIS teshis ('checkout BAYAT: yerel=N < canli=M') BASILMIYOR");
      ONA(/AYIRT EDILEMEDI/.test(r.cikti), "belirsizlik ACIKCA yazili (AYIRT EDILEMEDI)");
      ONA(/YETIM satir/.test(r.cikti), "ikinci olasilik ADIYLA sayiliyor (D1'de YETIM satir)");
      ONA(/D1 FAZLALIGI: yerel=\d+ < canli=\d+ \| fazla=\d+/.test(r.cikti),
        "teshis metni OLCULEN kanittan turetilmis (sayilar)");
    },
  });

  // ── B2: GECICI 429 -> yeniden deneme TUTMALI (kapi susmamali) ────────────────────
  senaryolar.push({
    ad: "S14 (B2) GECICI 429 (ilk istekler) -> yeniden deneme TUTAR, ayrisim 0",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), r429IlkKere: 2,
    ekEnv: { PARITE_DENEME: "3", PARITE_BEKLEME_MS: "5" },
    dogrula: (r) => {
      ONA(fiksturYesil(r), "cikis 3 + ayrisim 0 (429 kosumu OLDURMEDI)", r.cikti.slice(-700));
      ONA(/429: [1-9]/.test(r.cikti), "429 SAYILDI ve raporlandi (sessizce yutulmadi)");
      ONA(/yeniden deneme: [1-9]/.test(r.cikti), "yeniden deneme SAYILDI");
    },
  });

  // ── Arizalar TEK BASINA (kirmizi yokken): asla 0, daima 3 ────────────────────────
  senaryolar.push({
    ad: "S15 kirmizi YOK + zaman asimi -> cikis 3 (asla 0), erken durma GORUNUR",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), susSonraAra: 20, ekEnv: HIZLI_ZA,
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-700));
      ONA(/ZAMAN ASIMI/.test(r.cikti), "zaman asimi GORUNUR");
      ONA(/kosum ERKEN DURDU: \d+\/\d+/.test(r.cikti), "kac sorgunun olculdugu SAYIYLA yazili");
    },
  });
  senaryolar.push({
    // canli == yerel (sorgular birebir eslesir) ama /katalog SAYIMI sapiyor -> supurme
    // tetiklenir, TAVAN asilir. Hicbir ayrisim yok: eski kod burada 0 verirdi. AF YOK -> 3.
    ad: "S16 kirmizi YOK + supurme TAVANI asildi -> cikis 3 (asla 0)",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), sayiSapma: 5,
    ekEnv: { PARITE_SUPURME_TAVANI: "1" },
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-700));
      ONA(/TAVANI asildi/.test(r.cikti), "tavan asimi GORUNUR");
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "hic ayrisim YOK ama yine de 0 verilmedi");
    },
  });

  // 17-21) Ege tarafi AYNI kurala tabi mi? (bot kaynagi yoksa atlanir)
  if (EGE) {
    senaryolar.push({
      ad: "S17 EGE SAGLAMA: yerel == canli -> ayrisim 0 + cikis 3",
      dosya: PARITE_EGE, yerel: TABAN, canli: TABAN.slice(),
      dogrula: (r) => {
        ONA(fiksturYesil(r), "cikis 3 + ayrisim 0 + FIKSTUR: BIREBIR ESLESTI", r.cikti.slice(-700));
      },
    });
    senaryolar.push({
      ad: "S18 (K4/ege) BAYAT CHECKOUT -> cikis 3, KIRMIZI DEGIL",
      dosya: PARITE_EGE, yerel: TABAN, canli: EK.concat(TABAN),
      dogrula: (r) => {
        ONA(r.kod === 3, "cikis 3", r.cikti.slice(-900));
        ONA(/SENKRON GEC/.test(r.cikti), "'SENKRON GECİKMESİ' imzasi");
        ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0");
      },
    });
    senaryolar.push({
      ad: "S19 (K4-a/ege) YERELDE VAR / D1'DE YOK -> cikis 1 KIRMIZI",
      dosya: PARITE_EGE, yerel: TABAN, canli: EK.concat(TABAN.filter((p, i) => i !== 7)),
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
        ONA(/YERELDE VAR \/ D1'DE YOK/.test(r.cikti), "sebep dogru");
      },
    });
    senaryolar.push({
      ad: "S20 (K2/ege) KIRMIZI + kosum ortasinda 429 -> cikis 1",
      dosya: PARITE_EGE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI,
      r429SonraAra: 20, ekEnv: HIZLI_429,
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI (ariza kirmiziyi SILEMEZ)", r.cikti.slice(-900));
        ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "bulunan kirmizilar SAYILDI");
        ONA(/HIZ SINIRI \(429\)/.test(r.cikti), "429 arizasi GORUNUR");
      },
    });
    senaryolar.push({
      ad: "S21 (K2/ege) KIRMIZI + kosum ortasinda WAF 403 -> cikis 1",
      dosya: PARITE_EGE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI, wafSonraAra: 20,
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
        ONA(/OLCUM ARIZASI VAR/.test(r.cikti), "ariza GORUNUR ama KIRMIZI kazandi");
      },
    });
  } else {
    console.log("\n⚪ Ege senaryolari ATLANDI: bot kaynagi yok (" + EGE_MOD.BOT + ")");
  }

  console.log("═".repeat(78));
  console.log("PARITE KARAR-CEKIRDEGI FIKSTURU — %d senaryo (ag YOK, canliya 0 istek)",
    senaryolar.length);
  console.log("═".repeat(78));

  for (let i = 0; i < senaryolar.length; i++) {
    if (Number.isFinite(yalniz) && yalniz !== i) continue;
    await senaryoKos(Object.assign({ EGE }, senaryolar[i]));
  }

  console.log("\n" + "═".repeat(78));
  console.log("IDDIA: %d gecti | %d KALDI", gecen, kalan);
  // Makine-okunur ozet (mutasyon harness'i bunu ayristirir: hangi senaryo yakaladi).
  for (const ad of kalanSenaryolar) console.log("KALAN-SENARYO: " + ad);
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
