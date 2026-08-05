#!/usr/bin/env node
"use strict";
/**
 * EGE MARKA SORGUSU REFERANSI — ucun marka dalinin YEREL KARSILIGI, KOPYA DEGIL.
 *
 * NEDEN VAR (olculdu 6 Agu 2026): tools/parite-ege.js'in referansi bot deposundaki
 * bellek-ici `urunAra`ydi. `?q=<marka>` sorgusu 05 Agu'da SERBEST METIN olmaktan cikip
 * `marka_arama` UYELIGINE baglandi (site + uc, iki yuzey birlikte); `urunAra` o kurali
 * TASIMAZ ve bot deposunda 1 tanim / 0 cagri yeriyle OLU KODdur. Sonuc: parite testi
 * 38/848 kirmizi yakiyordu ve sapan taraf UC DEGIL, TESTIN KENDISIYDI — yon daima ayni,
 * referans FAZLA sayiyordu (haval 1423↔2, rover 92↔10, mercedes 1525↔1037, audi 354↔331).
 * Ayni sinif site tarafinda tools/index-arama-referansi.js ile kapatildi
 * ([[ikiz-tanim-sessiz-ayrisma]]).
 *
 * COZUM — IKINCI YUKLEM YAZILMAZ, IKI URETIM GOVDESI CALISTIRILIR:
 *   1. KUME  : `marka_arama` kolonunu CANLIDA dolduran uretici — tools/d1-sync.py
 *              `marka_arama_haritasi()` — alt surecte KOSTURULUR. Kolon urunler.json'dan
 *              yeniden HESAPLANAMAZ (ham `marka[]` esitligi capalarin ancak yarisini
 *              tutar; alias yazimi "Vauxhall" ham katalogda HIC gecmez), o yuzden
 *              "marka koluna gore onar" teknik olarak MUMKUN DEGIL.
 *   2. YARGI : "sorgunun TAMAMI marka adi mi?" karari ucun KENDI kodudur — bot
 *              index.js'inin `markaSorguKanonu()`u, sahte bir D1 uzerinde calistirilir.
 *              markaSorguNorm/aksan/ayirac kanonu, alfabetik determinizm ve CAKISMA
 *              davranisi boylece ucun kendi govdesinden gelir; buraya kopyalanmaz.
 * Kural bir gun degisirse (or. saf uyelige donulurse) referans KENDILIGINDEN izler;
 * bayatlayacak bir kopya kalmaz.
 *
 * 🔴 FAIL-CLOSED: uretici kosulamazsa / fail-closed sebep donerse / evren BOS cikarsa /
 * ucun yargisi evrene HIC bakmadan null donerse HATA atilir. Cagiran (parite-ege.js) bunu
 * OLCULEMEDI'ye (cikis 3) cevirir, SESSIZ YESILE degil. Sessiz dususte referans eski
 * serbest-metin haline donerdi = kapattigimiz bayatligin ta kendisi.
 *
 * ENV (yalniz izole kosumlar icin — normal kosumda VERILMEZ):
 *   PARITE_INDEX_KOK  gercek agacin koku (index.html + tools/); varsayilan bu betigin agaci.
 *                     tools/index-arama-referansi.js ile AYNI degisken: "gercek agac" tek
 *                     kavramdir, ikinci bir ad acmak mutasyon harness'ini ikiye bolerdi.
 */

const cp = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

/** Uretici cagrisi — YUKLEM BURADA YAZILMAZ, d1-sync.marka_arama_haritasi CALISTIRILIR. */
const URETEC_PY = [
  "import importlib.util, json, os, sys",
  "kok, katalog = sys.argv[1], sys.argv[2]",
  "tools = os.path.join(kok, 'tools')",
  "sys.path.insert(0, tools)",
  "spec = importlib.util.spec_from_file_location('d1sync', os.path.join(tools, 'd1-sync.py'))",
  "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)",
  "urunler = json.load(open(katalog, encoding='utf-8'))",
  "harita, sebep = mod.marka_arama_haritasi(urunler)",
  "print(json.dumps({'sebep': sebep, 'harita': {k: json.loads(v) for k, v in harita.items()}}," +
    " ensure_ascii=False))",
].join("\n");

/** Ureticinin girdileri — biri degisirse onbellek DUSMELI. */
const URETEC_GIRDILERI = ["index.html", "tools/d1-sync.py", "tools/arama.py",
  "tools/marka_model_build.py"];

class ReferansHatasi extends Error {
  constructor(mesaj) { super(mesaj); this.name = "ReferansHatasi"; this.olcum = true; }
}

function kokBul() {
  return process.env.PARITE_INDEX_KOK || path.dirname(__dirname);
}

/**
 * Onbellek anahtari: KATALOG ICERIGI (yol/mtime DEGIL) + uretici girdilerinin damgasi.
 * 🔴 NEDEN ICERIK: fikstur harness'leri her senaryo icin AYNI sentetik katalogu YENI bir
 * gecici yola yazar. Yol+mtime anahtarli onbellek her seferinde iskalar ve mutasyon
 * bataryasi (26 kosum x ~29 senaryo) ureticiyi yuzlerce kez calistirirdi
 * ([[fikstur-degeri-mutasyon-koru]] ile ayni sinif: yuk, gerilemeye benzer).
 */
function onbellekAnahtari(kok, katalogYolu) {
  const h = crypto.createHash("sha1");
  h.update(fs.readFileSync(katalogYolu));
  for (const ad of URETEC_GIRDILERI) {
    const yol = path.join(kok, ad);
    let s = null;
    try { s = fs.statSync(yol); } catch (e) { /* yoksa uretici zaten patlar */ }
    h.update("|" + ad + ":" + (s ? s.size + ":" + s.mtimeMs : "yok"));
  }
  return h.digest("hex").slice(0, 16);
}

/** {id: [marka, ...]} — uretim govdesinden. Fail-closed. */
function haritaUret(kok, katalogYolu) {
  const uretec = path.join(kok, "tools", "d1-sync.py");
  if (!fs.existsSync(uretec)) {
    throw new ReferansHatasi("marka_arama ureteci YOK: " + uretec +
      " (izole kosumda PARITE_INDEX_KOK verilmeli)");
  }
  let onbellek = null;
  try { onbellek = path.join(os.tmpdir(), "pruvo-marka-arama-" +
    onbellekAnahtari(kok, katalogYolu) + ".json"); } catch (e) { /* onbelleksiz devam */ }
  if (onbellek && fs.existsSync(onbellek)) {
    try { return JSON.parse(fs.readFileSync(onbellek, "utf8")); }
    catch (e) { /* bozuk onbellek: yok say, yeniden uret */ }
  }

  const p = cp.spawnSync("python3", ["-c", URETEC_PY, kok, katalogYolu],
    { encoding: "utf8", timeout: 600000, maxBuffer: 512 * 1024 * 1024 });
  if (p.error) {
    throw new ReferansHatasi("marka_arama ureteci kosulamadi: " + p.error.message);
  }
  if (p.status !== 0) {
    throw new ReferansHatasi("marka_arama ureteci SIFIR-DISI (rc=" + p.status + "): " +
      ((p.stderr || "") + (p.stdout || "")).slice(-400));
  }
  let j;
  try { j = JSON.parse(p.stdout); } catch (e) {
    throw new ReferansHatasi("marka_arama uretec ciktisi cozulemedi: " + e.message);
  }
  // Ureticinin KENDI fail-closed dali ("atla") burada YESILE cevrilmez.
  if (j.sebep) throw new ReferansHatasi("marka_arama ureteci FAIL-CLOSED atladi: " + j.sebep);
  if (!j.harita || typeof j.harita !== "object") {
    throw new ReferansHatasi("marka_arama uretec ciktisi sekli taninmadi (harita yok)");
  }
  if (onbellek) {
    try {
      const gecici = onbellek + "." + process.pid + ".tmp";
      fs.writeFileSync(gecici, JSON.stringify(j));
      fs.renameSync(gecici, onbellek);
    } catch (e) { /* onbellek yazilamadi: olcum yine dogru, yalniz yavas */ }
  }
  return j;
}

/**
 * Sahte D1 — ucun `markaEvreniGetir`i icin. SEKIL NOBETI FAIL-CLOSED: uc bir gun kolonu
 * baska bir kolonla BIRLESTIREREK okumaya baslarsa sahte D1 ayni satirlari dondurup
 * ayrismayi GIZLERDI. O yuzden gelen SQL'in sekli olculur.
 */
function sahteD1(satirlar, izleme) {
  return {
    KATALOG: {
      prepare(sql) {
        const t = String(sql || "");
        const kolonlar = (t.match(/json_each\s*\(\s*[a-z0-9_]*\.?([a-z_]+)\s*\)/g) || [])
          .map((s) => s.replace(/^json_each\s*\(\s*/, "").replace(/\s*\)$/, "")
            .replace(/^[a-z0-9_]*\./, ""));
        if (kolonlar.length !== 1 || kolonlar[0] !== "marka_arama") {
          throw new ReferansHatasi("uc marka evrenini `marka_arama` disindan okuyor " +
            "(bulunan: " + (kolonlar.join(", ") || "yok") + ") — referans KURULAMADI");
        }
        if (!/\byayinda\s*=\s*1\b/.test(t)) {
          throw new ReferansHatasi("uc evren SQL'inde `yayinda = 1` YOK — referans KURULAMADI");
        }
        izleme.sorgu++;
        return { all: async () => ({ results: satirlar }) };
      },
    },
  };
}

/**
 * Marka referansini kurar.
 * @param {object} a
 * @param {object} a.EGE           bot index.js modulu (markaSorguKanonu SART)
 * @param {Array}  a.urunler       yerel katalog (SIRA = katalog sirasi = uc `seq DESC`)
 * @param {string} a.urunlerYolu   ayni katalogun dosya yolu (uretici girdisi)
 * @param {Set}    [a.taslakKume]  KANITLANMIS taslak id'ler (ucun `yayinda=1` karsiligi)
 * @returns {Promise<{kanon:Function, kume:Function, evrenBoyu:number, kalem:number}>}
 */
async function markaReferansi({ EGE, urunler, urunlerYolu, taslakKume }) {
  if (!EGE || typeof EGE.markaSorguKanonu !== "function") {
    throw new ReferansHatasi("bot index.js'te markaSorguKanonu() YOK — marka dali OLCULEMEZ");
  }
  const kok = kokBul();
  const { harita } = haritaUret(kok, urunlerYolu);

  // TERS HARITA — SIRA katalogdan gelir (uc `ORDER BY u.seq DESC` = katalog sirasi).
  // Python sozluk sirasina GUVENILMEZ; urunler dizisi uzerinde yurunur.
  const taslak = taslakKume || new Set();
  const ters = new Map();
  let kalem = 0;
  for (const u of urunler) {
    const degerler = harita[u && u.id];
    if (!Array.isArray(degerler)) continue;
    for (const m of degerler) {
      if (!ters.has(m)) ters.set(m, []);
      ters.get(m).push(u.id);
      kalem++;
    }
  }

  // EVREN — ucunkiyle AYNI kural: `SELECT DISTINCT je.value ... WHERE yayinda = 1
  // ORDER BY je.value`. Taslak satirlar D1'in hicbir kesif yuzeyinde YOKTUR; yalniz
  // taslak satirlarda gecen bir marka ucta EVREN DISIDIR (sorgu serbest metne duser).
  const yayinda = new Map();
  for (const [m, idler] of ters) {
    const gorunur = idler.filter((id) => !taslak.has(id));
    if (gorunur.length) yayinda.set(m, gorunur);
  }
  const satirlar = [...yayinda.keys()].sort().map((m) => ({ m }));
  if (!satirlar.length) {
    throw new ReferansHatasi("marka evreni BOS — 'hic marka yok' bir parite KANITI DEGIL");
  }

  const izleme = { sorgu: 0 };
  const env = sahteD1(satirlar, izleme);
  const kanon = (q) => EGE.markaSorguKanonu(env, q);

  // 🔴 KENDINI SINAMA: yargi evrene FIILEN baksin. Uc `markaSorguKanonu`u bir gun evreni
  // okumadan null donerse (ya da sahte D1 hic cagrilmazsa) referans SESSIZCE eski
  // serbest-metin haline donerdi ve test yine yesil yanardi.
  const ornek = satirlar[0].m;
  const denek = await kanon(ornek);
  if (izleme.sorgu === 0) {
    throw new ReferansHatasi("uc yargisi marka evrenine HIC bakmadi (sahte D1 cagrilmadi)");
  }
  if (denek !== ornek) {
    throw new ReferansHatasi("kendini sinama TUTMADI: evrenin ilk degeri (" + ornek +
      ") marka adi sayilmadi -> " + JSON.stringify(denek));
  }

  return {
    kanon,
    kume: (deger) => yayinda.get(deger) || [],
    evrenBoyu: satirlar.length,
    kalem,
  };
}

module.exports = { markaReferansi, ReferansHatasi, URETEC_GIRDILERI };
