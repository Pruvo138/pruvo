#!/usr/bin/env node
/**
 * KANAL SINIFLAMASI — PYTHON TARAFI ICIN INCE KOPRU (mantik TASIMAZ).
 *
 *   node tools/kanal-sinif-cli.mjs --sozluk        -> kova listesi + etiket + ciro durumlari
 *   node tools/kanal-sinif-cli.mjs --sinifla       -> stdin JSON dizisi -> stdout JSON dizisi
 *
 * NEDEN VAR: `tools/kanal-kirilim-raporu.py` (Python) ile yonetim paneli (Worker/JS) AYNI
 * kovalari kullanmak ZORUNDA. Python'a kova listesi/siniflama kurali elle yazilsaydi ikinci
 * bir hukum dogardi ve ilk degisiklikte panel ile rapor sessizce ayrisirdi
 * ([[ayni-alan-iki-hukum-biri-sessiz]]). Bu dosya KARAR VERMEZ — yalnizca
 * shop/src/kanal-sinif.mjs'i cagirir ve JSON'a cevirir. Kova adlari, etiketler ve ciro
 * durumlari da BURADAN degil, o modulden gelir.
 *
 * Rapor bu koprüyu SIPARIS BASINA DEGIL, TUM SATIRLAR ICIN BIR KEZ cagirir (tek node
 * sureci): satir basina process acmak binlerce sipariste raporun kendisini olcum
 * araci olmaktan cikarirdi.
 *
 * CIKIS KODU: 0 basarili · 2 kullanim/girdi hatasi (Python tarafi bunu OLCULEMEDI sayar).
 */
import fs from "node:fs";

import {
  KOVALAR, KOVA_ETIKET, CIRO_DURUMLARI, KOVA_KANAL_OLCULEMEDI,
  BASILMAYAN_ATIF_ALANLARI, GORUNUR_ATIF_ALANLARI,
  kaynakOzeti, ciroyaGirer, tahsilatKurus,
} from "../shop/src/kanal-sinif.mjs";

const kip = process.argv[2] || "";

function cik(kod, mesaj) {
  process.stderr.write(mesaj + "\n");
  process.exit(kod);
}

if (kip === "--sozluk") {
  process.stdout.write(JSON.stringify({
    kovalar: KOVALAR,
    etiketler: KOVA_ETIKET,
    ciro_durumlari: [...CIRO_DURUMLARI].sort(),
    kova_kanal_olculemedi: KOVA_KANAL_OLCULEMEDI,
    gorunur_atif_alanlari: GORUNUR_ATIF_ALANLARI,
    basilmayan_atif_alanlari: BASILMAYAN_ATIF_ALANLARI,
  }, null, 1) + "\n");
} else if (kip === "--sinifla") {
  let ham = "";
  try {
    ham = fs.readFileSync(0, "utf8");
  } catch (e) {
    cik(2, "stdin okunamadi: " + (e && e.message));
  }
  let satirlar;
  try {
    satirlar = JSON.parse(ham);
  } catch (e) {
    cik(2, "stdin JSON degil: " + (e && e.message));
  }
  if (!Array.isArray(satirlar)) { cik(2, "stdin JSON DIZISI olmali"); }
  // ⚠️ `kanal` alani YOKSA undefined gecer -> kanalKovasi onu 'kanal-olculemedi'
  // yapar. Burada 'site' varsayilani UYGULANMAZ (raporun tum fail-closed kolu buna dayanir).
  const cikti = satirlar.map((s) => {
    const ozet = kaynakOzeti(s ? s.kanal : undefined, s ? s.atif : "");
    return {
      kova: ozet.kova,
      etiket: ozet.etiket,
      sebep: ozet.sebep,
      ciroya_girer: ciroyaGirer(s ? s.durum : ""),
      tahsilat_kurus: tahsilatKurus(s || {}),
    };
  });
  process.stdout.write(JSON.stringify(cikti) + "\n");
} else {
  cik(2, "kullanim: node tools/kanal-sinif-cli.mjs --sozluk | --sinifla");
}
