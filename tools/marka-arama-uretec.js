#!/usr/bin/env node
"use strict";
/**
 * MARKA_ARAMA URETECI — `marka_arama` kolonunu CANLIDA dolduran uretim govdesini
 * (tools/d1-sync.py `marka_arama_haritasi()`) alt surecte KOSTURUR; yuklem burada YAZILMAZ.
 *
 * Kokeni: tools/ege-marka-referansi.js'in `haritaUret` govdesi (6 Agu 2026). Ege (emekli
 * WhatsApp botu) referansi 6 Eki 2026'da kaldirildi; site marka ekseni
 * (tools/parite-marka-ekseni.js capraz kaynagi) bu govdeyi kullanmaya devam ettigi icin
 * govde TASINDI (kopya DEGIL — eski dosya silindi). Uretim yolunda ureticiyi kosturan
 * TEK govde budur; ikinci bir python parcasi yazilirsa iki fail-closed kurali ayrisir
 * ([[ikiz-tanim-sessiz-ayrisma]]). Fikstur tarafindaki bagimsiz cagri
 * (parite-fikstur-test.js) BILEREK buraya baglanmaz.
 *
 * 🔴 FAIL-CLOSED: uretici kosulamazsa / fail-closed sebep donerse / cikti sekli taninmazsa
 * ReferansHatasi atilir; cagiran bunu OLCULEMEDI'ye cevirir, SESSIZ YESILE degil.
 *
 * ENV (yalniz izole kosumlar icin — normal kosumda VERILMEZ):
 *   PARITE_INDEX_KOK  gercek agacin koku (index.html + tools/); varsayilan bu betigin agaci.
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
  // `gizli` kayitlar referans evrenine GIRMEZ: canli evren `yayinda=1` suzer ve
  // gizli urun kalici taslaktir (yayin-kapisi --gizle) — iki taraf ayni kumeyi olcer.
  "urunler = [u for u in json.load(open(katalog, encoding='utf-8')) if not u.get('gizli')]",
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

module.exports = { haritaUret, ReferansHatasi, URETEC_GIRDILERI, kokBul };
