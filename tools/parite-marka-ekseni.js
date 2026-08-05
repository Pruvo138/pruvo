#!/usr/bin/env node
"use strict";
/**
 * MARKA ADI SORGUSU EKSENI — site kurali ↔ ucun `?q=<marka>` cevabi BIREBIR mi?
 *
 *   node tools/parite-marka-ekseni.js                # her iki yuzey (site + ege)
 *   node tools/parite-marka-ekseni.js --yuzey=site   # yalniz site yuzeyi (`?q=`)
 *   node tools/parite-marka-ekseni.js --yuzey=ege    # yalniz Ege yuzeyi (`?q=&mod=ege`)
 *   node tools/parite-marka-ekseni.js --ornek=20     # evrenin ilk 20 markasi (hizli)
 *   node tools/parite-marka-ekseni.js --kendini-test # MUTASYON BATARYASI (ag YOK)
 *
 * Ayni eksen iki parite testinden de cagrilabilir (IKINCI GOVDE YOK — ikisi de BU dosyayi
 * require eder):
 *   node tools/parite-test.js --marka-ekseni   -> site yuzeyi
 *   node tools/parite-ege.js  --marka-ekseni   -> ege yuzeyi
 *
 * ╔══════════════════════════════════════════════════════════════════════════════════╗
 * ║ NEDEN VAR (kapanan acik)                                                          ║
 * ║ Okan hukmu: "TUM markalarda marka SAYFASI ve ARAMA urun adetleri ayni olsun."     ║
 * ║ Site tarafi 8913db28 ile gecti (marka adiyla sorgu = UYELIK ∪ BASLIKTA TAM        ║
 * ║ KELIME), D1 tarafi f35c421f ile gecti (`marka_arama` kolonu canli+dolu). Kalan    ║
 * ║ adim UCTA: `?q=<marka>` HALA serbest-metin ALT-DIZE aramasi yapiyor               ║
 * ║ (`?q=MAN` -> "Mandali"/"manuel", `?q=Haval` -> "Havalandirma").                    ║
 * ║                                                                                    ║
 * ║ Mevcut iki parite testi bu ayrismayi GORMEZ ve GORMEMESI TASARIMDIR:              ║
 * ║ tools/parite-test.js icindeki referans `filtered()` BILEREK eski (serbest metin)   ║
 * ║ halinde birakildi — o test "uc ile UCUN SOZLESMESI" paritesini olcer. Yani uc      ║
 * ║ gecisi yaptigi gun site↔uc ayrismasi SESSIZ kalirdi. Bu eksen o sessizligi kapatir.║
 * ╚══════════════════════════════════════════════════════════════════════════════════╝
 *
 * ── OLCUM MIMARISI (uc kaynak, ucu de TURETILIR — hicbiri elle yazilmis liste DEGIL) ──
 *   EVREN     : D1 `SELECT DISTINCT value ... json_each(marka_arama) WHERE yayinda=1`
 *               🔴 `marka_arama` TEK BASINA okunur (birlesim GEREKSIZ ve YASAK) —
 *               `model_kanon`dan FARKLI, karistirma. SQL sekli sqlSekliDogrula() ile
 *               nobetlenir: birlesim/ikinci kolon girerse kosum FAIL-CLOSED duser.
 *   REFERANS  : ayni kolonun SATIR kumesi (`value = <marka>`, `ORDER BY seq DESC`).
 *               Bu, sitenin marka-sorgusu yukleminin D1'de MADDELESMIS halidir; uc onu
 *               okumak zorundadir. Canli-canli karsilastirma oldugu icin bayat worktree
 *               gurultusu (yerel katalog ≠ D1) bu eksende YAPISAL OLARAK YOK.
 *   CAPRAZ    : deponun TEK KANONIK GOVDESI (d1-sync.marka_arama_haritasi — yuklemi
 *               KOPYALAMAZ, CALISTIRIR). Kolonun bayat/ayrismis olma ihtimalini ayirir:
 *               capraz tutmuyorsa o marka OLCULEMEDI'dir, KIRMIZI DEGIL.
 *
 * ── UC SONUC AYRI TUTULUR ([[hukum-yanlis-birimde]]) ──────────────────────────────────
 *   GECTI       uc, referans kumeyle BIREBIR.
 *   AYRISAN     uc referanstan FARKLI -> gercek gerileme (cikis 1).
 *   OLCULEMEDI  uc cevap vermedi (403/429/zaman asimi) · D1/wrangler okunamadi · capraz
 *               kaynak tutmadi (senkron/yayin penceresi) · EVREN BOS.
 *   🔴 EVREN BOS = OLCULEMEDI, ASLA YESIL (fail-closed). "Hic marka bulamadim" bir
 *   parite KANITI degildir; eski kod sifir markayla "0 ayrisma" basip yesil yanardi.
 *   🔴 YONETICI ILKE (parite-ortak.js ile AYNI): 1 (KIRMIZI) > 3 (OLCULEMEDI) > 0.
 *
 * ── PENCERE: KABUL ARALIGI ILE KIYAS ARALIGI TEK KAYNAK ([[kabul-araligi-karsilastirma-araligi]]) ──
 * `/ara` azami 1000 satir doner; 1000'i asan markalar var (olculdu 5 Agu: Ford 2582,
 * BMW 2311, VW 1383, Toyota 1292, Mercedes 1037). Uca gonderilen `limit` ILE referansin
 * kirpildigi dilim AYNI sabitten (PENCERE) turer; ikisi ayri yazilsaydi 1000. sirada
 * baslayan bir ayrisma sessizce yesil gecerdi.
 *
 * ── SIRA IDDIASI YUZEYE GORE ─────────────────────────────────────────────────────────
 *   site yuzeyi: uc `ORDER BY u.seq DESC` doner -> SIRALI karsilastirma (parite-ortak.
 *                siniflandir, gecikmeModu=false). Katalog sirasi iddiasi da sinanir.
 *   ege yuzeyi : uc `ORDER BY skor DESC, seq DESC` doner (skor korpus-bagimli degil ama
 *                SIRA seq DESC DEGIL) -> KUME karsilastirmasi; sira iddiasi BU YUZEYDE
 *                YOKTUR ve olculmez. Iki dal AYNI pencereden gecer (tek govde).
 *
 * ── ZAMANLAMA: BU EKSEN BUGUN KIRMIZI YANAR, BU BEKLENEN ─────────────────────────────
 * Uc henuz gecmedigi icin eksen bugun ayrisma bulur; bu, calistiginin KANITIDIR.
 * 🔴 Bu yuzden BLOKLAYAN SERIDE DEGILDIR: ne parite-test.js'in ne parite-ege.js'in
 * varsayilan kosumuna girer, CI kapisina baglanmaz. Yalniz `--marka-ekseni` bayragiyla
 * ELLE kosulur. Gecis indikten sonra bagalanmasi MIMAR karariddir.
 *
 * ── MUTASYON KANITI ([[mutasyon-kaniti-yeniden-uretilebilir]]) ───────────────────────
 * `--kendini-test`: anlatilan batarya kanit DEGILDIR; surucu BU DOSYADA durur, ag/wrangler
 * kullanmaz (fikstur), ve kabul CIKIS KODU degil OLCULEN IMZA (olculen/gecti/ayrisan/
 * olculemedi) + isaret sartidir. Oldurucu VE kontrol mutantlari birlikte kosar: kontrol
 * yoksa "daima kirmizi" bir eksen butun oldurucileri gecer, ayirt edilemez.
 */

const cp = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const ortak = require("./parite-ortak.js");

const TOOLS = __dirname;
const KOK = path.dirname(TOOLS);
const UC = process.env.ARA_UC || "https://pruvo-whatsapp-bot.gmlmz.workers.dev/ara";

// 🔴 PENCERE — TEK KAYNAK. Uca gonderilen `limit` de, referansin kirpildigi dilim de
// BURADAN gelir (bkz. dosya basi). Ikinci bir sayi YAZILMAZ.
const PENCERE = 1000;

// D1 sayfa boyu (wrangler tek cevapta 18.5k satiri rahat tasisin diye parcalanir).
const D1_SAYFA = 6000;
const ESZAMAN = 6;

// ── D1 SORGULARI — SEKLI NOBETLENIR ────────────────────────────────────────────────
// 🔴 EVREN_SQL: `marka_arama` TEK BASINA. `marka`/`marka_kanon` ile BIRLESIM ALINMAZ —
// ham `marka[]` evreni model kodlariyla doludur (olculdu 5 Agu: 2288 ham deger, 2159'u
// marka DEGIL: "E46", "1 Serisi", "106", "190E"...). Birlesim, marka olmayan jetonlari
// marka sanip ekseni gurultuye bogardi.
const EVREN_SQL =
  "SELECT DISTINCT je.value AS m FROM urunler u, json_each(u.marka_arama) je " +
  "WHERE u.yayinda = 1 ORDER BY je.value";
// KUME_SQL: her markanin SATIR kumesi, ucun sirasiyla (seq DESC).
const KUME_SQL =
  "SELECT je.value AS m, u.id AS id FROM urunler u, json_each(u.marka_arama) je " +
  "WHERE u.yayinda = 1 ORDER BY je.value, u.seq DESC LIMIT %L OFFSET %O";

/**
 * SQL SEKIL NOBETCISI — fail-closed. Kolonun TEK BASINA okundugunu YAPISAL olarak olcer.
 * Doner: hata metni | null.
 * 🔴 Bu nobetci FIKSTUR MODUNDA DA kosar: sabitler saf metindir, agdan bagimsiz olcum.
 * Boylece "kolonu birlesimle oku" mutanti ag olmadan da KIRMIZI yakilir.
 */
function sqlSekliDogrula(sql, ad) {
  const t = String(sql || "");
  // Takma ad KALIBI DEGIL, KOLON ADI olculur: `u2.marka` gibi ikinci bir tablo takma adiyla
  // kacamak olmasin diye desen takma adi serbest birakir.
  const kolonlar = (t.match(/json_each\s*\(\s*[a-z0-9_]*\.?([a-z_]+)\s*\)/g) || [])
    .map((s) => s.replace(/^json_each\s*\(\s*/, "").replace(/\s*\)$/, "").replace(/^[a-z0-9_]*\./, ""));
  if (kolonlar.length !== 1) {
    return ad + ": json_each() TAM BIR KEZ ve YALNIZ bir kolonda gecmeli (bulunan: " +
      (kolonlar.join(", ") || "yok") + ")";
  }
  if (kolonlar[0] !== "marka_arama") {
    return ad + ": okunan kolon `" + kolonlar[0] + "` — `marka_arama` OLMALI";
  }
  if (/\bUNION\b|\bINTERSECT\b|\bEXCEPT\b/i.test(t)) {
    return ad + ": BIRLESIM/kume operatoru YASAK (`marka_arama` TEK BASINA okunur)";
  }
  if (/\bmarka_kanon\b/.test(t)) {
    return ad + ": `marka_kanon` bu eksende OKUNMAZ (ayri eksen, ayri hukum)";
  }
  if (!/\byayinda\s*=\s*1\b/.test(t)) {
    return ad + ": `yayinda = 1` suzgeci YOK (taslak satir ucta gorunmez -> sahte ayrisma)";
  }
  return null;
}

// ── D1 ERISIMI ─────────────────────────────────────────────────────────────────────

class EksenHatasi extends Error {
  constructor(sebep) { super(sebep); this.name = "EksenHatasi"; this.olcum = true; }
}

/** DB adi TEK KAYNAKTAN: tools/d1-sync.py'deki DB_AD. Ikinci literal YAZILMAZ. */
function dbAdi() {
  const kaynak = fs.readFileSync(path.join(TOOLS, "d1-sync.py"), "utf8");
  const m = kaynak.match(/^DB_AD\s*=\s*"([^"]+)"/m);
  if (!m) throw new EksenHatasi("tools/d1-sync.py icinde DB_AD bulunamadi (yeniden adlandirildi mi?)");
  return m[1];
}

/** wrangler d1 execute --json; SUPHELIYI BASARI SAYMAZ (fail-closed). */
function d1Sorgu(sql) {
  const p = cp.spawnSync("npx", ["--yes", "wrangler@4", "d1", "execute", dbAdi(),
    "--remote", "--json", "--command", sql],
    { encoding: "utf8", timeout: 300000, cwd: KOK });
  const ham = (p.stdout || "") + (p.stderr || "");
  if (p.status !== 0) {
    throw new EksenHatasi("wrangler SIFIR-DISI (rc=" + p.status + "): " + ham.slice(-400));
  }
  const bas = (p.stdout || "").indexOf("[");
  if (bas === -1) throw new EksenHatasi("wrangler JSON vermedi: " + ham.slice(-400));
  let j;
  try { j = JSON.parse((p.stdout || "").slice(bas)); } catch (e) {
    throw new EksenHatasi("wrangler ciktisi cozulemedi: " + e.message);
  }
  if (!Array.isArray(j) || !j.length || !j[0] || j[0].success !== true ||
      !Array.isArray(j[0].results)) {
    throw new EksenHatasi("wrangler BASARI sekli degil: " + JSON.stringify(j).slice(0, 300));
  }
  return j[0].results;
}

// ── KAYNAK 1: EVREN (D1) ───────────────────────────────────────────────────────────
/**
 * Marka adi evreni — D1'DEN TURETILIR, ELLE LISTE DEGIL.
 * Doner: { degerler[], sql, kaynak }.
 * 🔴 Buraya elle bir dizi yazilirsa: (a) sqlSekliDogrula ile beslenen SQL kaybolur,
 * (b) capraz kaynak (deponun kanonik govdesi) ile karsilastirma tutmaz -> OLCULEMEDI.
 * Ikisi de yesil VERMEZ.
 */
function evrenTuret(fikstur) {
  const sekilHatasi = sqlSekliDogrula(EVREN_SQL, "EVREN_SQL");
  if (sekilHatasi) throw new EksenHatasi(sekilHatasi);
  const satirlar = fikstur ? fikstur.evrenSatirlari() : d1Sorgu(EVREN_SQL);
  const degerler = satirlar.map((r) => r.m).filter((v) => typeof v === "string" && v);
  return { degerler, sql: EVREN_SQL, kaynak: fikstur ? "fikstur" : "d1" };
}

// ── KAYNAK 2: REFERANS KUMELER (D1, ayni kolon) ────────────────────────────────────
/** Map<marka, id[]> — id'ler ucun sirasiyla (seq DESC). Sayfalanir. */
function d1Kumeleri(fikstur) {
  const sekilHatasi = sqlSekliDogrula(KUME_SQL, "KUME_SQL");
  if (sekilHatasi) throw new EksenHatasi(sekilHatasi);
  if (fikstur) return fikstur.d1Kumeleri();
  const harita = new Map();
  let ofset = 0;
  for (;;) {
    const sql = KUME_SQL.replace("%L", String(D1_SAYFA)).replace("%O", String(ofset));
    const satirlar = d1Sorgu(sql);
    for (const r of satirlar) {
      if (!harita.has(r.m)) harita.set(r.m, []);
      harita.get(r.m).push(r.id);
    }
    if (satirlar.length < D1_SAYFA) break;
    ofset += D1_SAYFA;
    if (ofset > 2000000) throw new EksenHatasi("D1 sayfalama tavani asildi");
  }
  return harita;
}

// ── KAYNAK 3: CAPRAZ (deponun TEK KANONIK GOVDESI) ────────────────────────────────
// Yuklem BURADA YAZILMAZ: d1-sync.marka_arama_haritasi CALISTIRILIR (kolonu dolduran
// gercek uretim govdesi). Kopyalansaydi tam kapattigimiz ikiz-tanim ayrismasini geri
// getirirdik ([[ikiz-tanim-sessiz-ayrisma]]).
const CAPRAZ_PY = [
  "import importlib.util, json, os, sys",
  "kok = sys.argv[1]; tools = os.path.join(kok, 'tools')",
  "sys.path.insert(0, tools)",
  "spec = importlib.util.spec_from_file_location('d1sync', os.path.join(tools, 'd1-sync.py'))",
  "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)",
  "urunler = json.load(open(os.path.join(kok, 'urunler.json'), encoding='utf-8'))",
  "harita, sebep = mod.marka_arama_haritasi(urunler)",
  "ters = {}",
  "for uid, deger in harita.items():",
  "    for m in json.loads(deger):",
  "        ters.setdefault(m, []).append(uid)",
  "print(json.dumps({'sebep': sebep, 'kume': ters}, ensure_ascii=False))",
].join("\n");

/** Map<marka, Set<id>> — deponun kanonik govdesinden. Doner: {kume, sebep}. */
function caprazKumeler(fikstur) {
  if (fikstur) return fikstur.caprazKumeler();
  const p = cp.spawnSync("python3", ["-c", CAPRAZ_PY, KOK],
    { encoding: "utf8", timeout: 300000, maxBuffer: 256 * 1024 * 1024 });
  if (p.status !== 0) {
    throw new EksenHatasi("capraz kaynak kosulamadi (python3/d1-sync.py): " +
      ((p.stderr || "") + (p.stdout || "")).slice(-400));
  }
  let j;
  try { j = JSON.parse(p.stdout); } catch (e) {
    throw new EksenHatasi("capraz kaynak ciktisi cozulemedi: " + e.message);
  }
  if (j.sebep) throw new EksenHatasi("capraz kaynak FAIL-CLOSED atladi: " + j.sebep);
  const kume = new Map();
  for (const m of Object.keys(j.kume)) kume.set(m, new Set(j.kume[m]));
  return kume;
}

// ── UC ─────────────────────────────────────────────────────────────────────────────
const NONCE = ortak.nonceUret();

async function ucKumesi(marka, yuzey, sayac, fikstur) {
  // 🔴 KABUL ARALIGI. kiyasla()'daki KIYAS ARALIGI (pencereKirp) ile AYNI sabitten turer;
  // ikisi ayri yazilsaydi genis kabul + dar kiyas sessizce yesil verirdi
  // ([[kabul-araligi-karsilastirma-araligi]]). Fikstur yolu da AYNI degeri alir ki
  // mutasyon bataryasi bu ekseni agsiz olcebilsin.
  const limit = PENCERE;
  if (fikstur) return fikstur.ucCevabi(marka, yuzey, limit);
  const u = new URL(UC);
  u.searchParams.set("q", marka);
  u.searchParams.set("limit", String(limit));
  if (yuzey === "ege") u.searchParams.set("mod", "ege");
  // ONBELLEK KIRICI — SART: /ara "max-age=60" ile doner ve Cloudflare edge ISTEK'teki
  // no-cache'i YOK SAYAR. Bu olmadan uc degil CDN olculur (bozuk kod YESIL yanabilir).
  u.searchParams.set("_nonce", NONCE);
  const { govde } = await ortak.canliGetir(u.toString(), sayac, ortak.DENEME);
  if (govde && govde.hata) throw new Error(String(govde.hata));
  return { toplam: govde && Number.isInteger(govde.toplam) ? govde.toplam : 0,
           urunler: ((govde && govde.urunler) || []).map((x) => x.id) };
}

// ── KIYAS — TEK GOVDE, PENCERE TEK KAYNAK ─────────────────────────────────────────
/** 🔴 KIYAS ARALIGI — tek gecit. Kabul araligi (ucKumesi `limit`) ile AYNI sabitten turer. */
function pencereKirp(ids) { return ids.slice(0, PENCERE); }

/**
 * Doner: { gecti, sebep }.
 * `sirali=true`  -> parite-ortak.siniflandir (SIRA iddiasi dahil, gecikmeModu=false).
 * `sirali=false` -> KUME esitligi; sira iddiasi YOKTUR (Ege skorla siralar).
 * Iki dal da pencereyi PENCERE'den alir: kabul araligi = kiyas araligi.
 */
function kiyasla({ bekIds, alinan, toplam, sirali }) {
  const bekPencere = pencereKirp(bekIds);
  if (sirali) {
    // SIRALI dal: kanonik siniflandirici. Kendi kirpmasini `limit`ten yapar; o da PENCERE.
    const k = ortak.siniflandir({
      bekIds, alinan, toplam, limit: PENCERE,
      yerelIdKume: new Set(bekIds), gecikmeModu: false, taslakKume: null,
    });
    return { gecti: k.sinif === ortak.SINIF_GECTI, sebep: k.sebep };
  }
  if (toplam !== bekIds.length) {
    return { gecti: false, sebep: "sayi: uc=" + toplam + " referans=" + bekIds.length };
  }
  if (alinan.length !== bekPencere.length) {
    return { gecti: false,
      sebep: "pencere boyu: uc=" + alinan.length + " referans=" + bekPencere.length };
  }
  const bekKume = new Set(bekIds);
  const fazla = alinan.filter((id) => !bekKume.has(id));
  if (fazla.length) {
    return { gecti: false, sebep: "kumede OLMAYAN " + fazla.length + " kayit (or. " +
      fazla.slice(0, 3).join(", ") + ")" };
  }
  return { gecti: true, sebep: "" };
}

// ── EKSEN ──────────────────────────────────────────────────────────────────────────

/**
 * Tek yuzeyi olc. Doner: { yuzey, olculen, gecti, ayrisan[], olculemedi[], kalem }.
 * `kalem` = ayrisan markalardaki uc↔referans URUN-KALEMI farkinin toplami (kardes
 * mimarin gecis hedefi bu sayidir).
 */
async function yuzeyOlc({ yuzey, evren, d1, capraz, ornek, sayac, fikstur }) {
  const sirali = yuzey === "site";
  const markalar = ornek ? evren.slice(0, ornek) : evren;
  const ayrisan = [];
  const olculemedi = [];
  let gecti = 0, olculen = 0, kalem = 0;
  let sirada = 0;
  let ariza = null;

  async function isci() {
    while (sirada < markalar.length && !ariza) {
      const m = markalar[sirada++];
      const bekIds = d1.get(m) || [];
      const caprazKume = capraz.get(m);

      // CAPRAZ KAPISI: kolon (D1) ile deponun kanonik govdesi ayni seyi mi soyluyor?
      // Ayrisiyorsa sebep senkron/yayin penceresi olabilir -> O MARKA OLCULEMEDI,
      // KIRMIZI DEGIL ([[yayin-penceresi-taslak-satir]]).
      if (!caprazKume) {
        olculemedi.push(m + ": capraz kaynakta YOK (kolon evreni ile depo evreni ayristi)");
        continue;
      }
      const eksik = bekIds.filter((id) => !caprazKume.has(id)).length;
      if (eksik || caprazKume.size !== bekIds.length) {
        olculemedi.push(m + ": kolon(" + bekIds.length + ") ≠ depo kanonik(" +
          caprazKume.size + ") — senkron/yayin penceresi, hukum VERILMEZ");
        continue;
      }

      let g;
      try { g = await ucKumesi(m, yuzey, sayac, fikstur); } catch (e) {
        if (e && e.olcum) { ariza = ariza || e; return; }
        olculemedi.push(m + ": uc istegi basarisiz — " + e.message);
        continue;
      }
      olculen++;
      const k = kiyasla({ bekIds, alinan: g.urunler, toplam: g.toplam, sirali });
      if (k.gecti) { gecti++; continue; }
      kalem += Math.abs(g.toplam - bekIds.length);
      ayrisan.push({ marka: m, uc: g.toplam, referans: bekIds.length, sebep: k.sebep });
    }
  }
  await Promise.all(Array.from({ length: fikstur ? 1 : ESZAMAN }, isci));
  if (ariza) {
    olculemedi.push("olcum arizasi: " + ariza.message + " -> kosum ERKEN DURDU (" +
      olculen + "/" + markalar.length + " marka olculdu)");
  }
  return { yuzey, olculen, gecti, ayrisan, olculemedi, kalem, hedef: markalar.length };
}

/** Sonuclari bas + TEK karar noktasi (1 > 3 > 0). Doner: cikis kodu. */
function rapor(sonuclar, notlar) {
  let kirmizi = 0, olculemeyen = notlar.length;
  for (const s of sonuclar) {
    console.log("\n── YUZEY: %s ──", s.yuzey);
    console.log("  evren      : %d marka (hedef)", s.hedef);
    console.log("  OLCULEN    : %d", s.olculen);
    console.log("  GECTI      : %d", s.gecti);
    console.log("  AYRISAN    : %d marka | %d urun-kalemi", s.ayrisan.length, s.kalem);
    console.log("  OLCULEMEDI : %d", s.olculemedi.length);
    // NOT: console.log %-16s genislik belirtecini DESTEKLEMEZ (Node util.format) —
    // hizalama padEnd ile yapilir, yoksa cikti "%-16s" diye BASILIR.
    for (const a of s.ayrisan.slice(0, 20)) {
      console.log("    ❌ " + String(a.marka).padEnd(16) + " uc=" + String(a.uc).padEnd(6) +
        " referans=" + String(a.referans).padEnd(6) + "  " + a.sebep);
    }
    if (s.ayrisan.length > 20) console.log("    … +%d marka daha", s.ayrisan.length - 20);
    for (const o of s.olculemedi.slice(0, 10)) console.log("    ⚪ %s", o);
    if (s.olculemedi.length > 10) console.log("    … +%d not daha", s.olculemedi.length - 10);
    // 🔴 EVREN BOS / HIC OLCUM YOK = FAIL-CLOSED. "0 ayrisma" bir parite KANITI DEGILDIR.
    if (!s.olculen) {
      console.log("  ⚪ HICBIR MARKA OLCULMEDI -> hukum VERILEMEZ (fail-closed; yesil DEGIL)");
      olculemeyen++;
    }
    kirmizi += s.ayrisan.length;
    olculemeyen += s.olculemedi.length;
    // MAKINE OKUR SATIR — mutasyon surucusu CIKIS KODUNU degil BU SAYILARI okur.
    console.log("OZET yuzey=%s olculen=%d gecti=%d ayrisan=%d kalem=%d olculemedi=%d",
      s.yuzey, s.olculen, s.gecti, s.ayrisan.length, s.kalem, s.olculemedi.length);
  }
  for (const n of notlar) console.log("⚪ %s", n);
  if (kirmizi) {
    console.log("\nSONUC: AYRISMA VAR ❌ (%d marka) — cikis %d", kirmizi, ortak.CIKIS_KIRMIZI);
    return ortak.CIKIS_KIRMIZI;
  }
  if (olculemeyen) {
    console.log("\nSONUC: OLCULEMEDI ⚪ (%d not) — cikis %d", olculemeyen, ortak.CIKIS_OLCULEMEDI);
    return ortak.CIKIS_OLCULEMEDI;
  }
  console.log("\nSONUC: BIREBIR PARITE ✅ — cikis %d", ortak.CIKIS_GECTI);
  return ortak.CIKIS_GECTI;
}

/** Eksenin tamami. Doner: cikis kodu. */
async function calistir({ yuzeyler, ornek, fikstur }) {
  const notlar = [];
  const sayac = ortak.sayacYeni();
  console.log("MARKA ADI SORGUSU EKSENI | uc: %s | pencere: %d | yuzey: %s%s",
    fikstur ? "(fikstur)" : UC, PENCERE, yuzeyler.join("+"),
    ornek ? " | ornek: " + ornek : "");

  let evren, d1, capraz;
  try {
    const e = evrenTuret(fikstur);
    evren = e.degerler;
    console.log("EVREN kaynagi: %s | %d ayri deger | SQL: %s", e.kaynak, evren.length, e.sql);
    d1 = d1Kumeleri(fikstur);
    capraz = caprazKumeler(fikstur);
    console.log("CAPRAZ kaynak: depo kanonik govdesi (d1-sync.marka_arama_haritasi) | %d marka",
      capraz.size);
  } catch (e) {
    if (e && e.olcum) {
      console.log("⚪ %s", e.message);
      return rapor(yuzeyler.map((y) => ({ yuzey: y, olculen: 0, gecti: 0, ayrisan: [],
        olculemedi: [], kalem: 0, hedef: 0 })), [e.message]);
    }
    throw e;
  }

  // EVREN CAPRAZ KAPISI — kolon evreni ile depo evreni ayni mi? (elle-liste mutantinin
  // yakalandigi yer: turetilmemis bir evren burada FARKLI cikar -> OLCULEMEDI.)
  const caprazEvren = new Set(capraz.keys());
  const sadeceD1 = evren.filter((m) => !caprazEvren.has(m));
  const sadeceDepo = [...caprazEvren].filter((m) => !evren.includes(m));
  if (sadeceD1.length || sadeceDepo.length) {
    notlar.push("EVREN AYRISTI: yalniz kolonda " + sadeceD1.length + " (" +
      sadeceD1.slice(0, 5).join(", ") + "), yalniz depoda " + sadeceDepo.length + " (" +
      sadeceDepo.slice(0, 5).join(", ") + ") -> yalniz KESISIM olculur");
  }

  const sonuclar = [];
  for (const y of yuzeyler) {
    sonuclar.push(await yuzeyOlc({ yuzey: y, evren, d1, capraz, ornek, sayac, fikstur }));
  }
  if (!fikstur) console.log("\ncanli istek: %d (429: %d)", sayac.istek, sayac.r429);
  return rapor(sonuclar, notlar);
}

// ── FIKSTUR (ag YOK, wrangler YOK) ─────────────────────────────────────────────────
/**
 * PARITE_MARKA_FIKSTUR=<json yolu> verilirse tum dis kaynaklar o dosyadan okunur.
 * Sekil: { evren:[m], d1:{m:[id]}, capraz:{m:[id]}, uc:{site:{m:{toplam,urunler}}, ege:{...}} }
 * 🔴 Fikstur, GERCEK kiyas/pencere/nobetci govdesini kosturur — yalniz KAYNAKLARI degistirir.
 */
function fiksturYukle() {
  const yol = process.env.PARITE_MARKA_FIKSTUR;
  if (!yol) return null;
  const f = JSON.parse(fs.readFileSync(yol, "utf8"));
  return {
    evrenSatirlari: () => (f.evren || []).map((m) => ({ m })),
    d1Kumeleri: () => new Map(Object.keys(f.d1 || {}).map((m) => [m, f.d1[m]])),
    caprazKumeler: () => new Map(Object.keys(f.capraz || {}).map((m) => [m, new Set(f.capraz[m])])),
    // 🔴 `limit` FIILEN UYGULANIR: fikstur, ucun `?limit=` davranisini taklit eder
    // (canli uc de pencereyi kendisi kirpar). Boylece "kabul araligi daraldi" mutanti
    // agsiz olculebilir ([[nobetci-fikstur-sekli]] — fikstur gercek cikti seklini taklit etsin).
    ucCevabi: async (m, yuzey, limit) => {
      const c = ((f.uc || {})[yuzey] || {})[m];
      if (!c) throw new Error("fiksturde uc cevabi yok: " + yuzey + "/" + m);
      return { toplam: c.toplam, urunler: (c.urunler || []).slice(0, limit) };
    },
  };
}

// ── CLI ────────────────────────────────────────────────────────────────────────────
function argvCoz(argv) {
  const yuzeyArg = (argv.find((a) => a.startsWith("--yuzey=")) || "").split("=")[1];
  const ornekArg = parseInt((argv.find((a) => a.startsWith("--ornek=")) || "").split("=")[1], 10);
  const yuzeyler = yuzeyArg ? yuzeyArg.split(",").filter(Boolean) : ["site", "ege"];
  for (const y of yuzeyler) {
    if (y !== "site" && y !== "ege") { console.error("bilinmeyen yuzey: " + y); process.exit(2); }
  }
  return { yuzeyler, ornek: Number.isFinite(ornekArg) && ornekArg > 0 ? ornekArg : 0 };
}

/** parite-test.js / parite-ege.js buradan cagirir (IKINCI GOVDE YOK). */
async function calistirCLI({ yuzey }) {
  const { ornek } = argvCoz(process.argv.slice(2));
  return calistir({ yuzeyler: [yuzey], ornek, fikstur: fiksturYukle() });
}

module.exports = {
  PENCERE, EVREN_SQL, KUME_SQL, sqlSekliDogrula, pencereKirp, kiyasla, evrenTuret, d1Kumeleri,
  caprazKumeler, yuzeyOlc, calistir, calistirCLI, argvCoz, fiksturYukle,
};

if (require.main === module) {
  if (process.argv.includes("--kendini-test")) {
    require("./parite-marka-mutasyon.js").main();
  } else {
    const { yuzeyler, ornek } = argvCoz(process.argv.slice(2));
    calistir({ yuzeyler, ornek, fikstur: fiksturYukle() })
      .then((kod) => process.exit(kod))
      .catch((e) => { console.error(e); process.exit(2); });
  }
}
