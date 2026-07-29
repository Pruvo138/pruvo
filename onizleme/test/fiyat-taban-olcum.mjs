/* FIYAT REGRESYON OLCUMU (yardimci arac — kabul kapisi DEGIL).

   Amac: 2-renk govde ayrimi calismasinin fiyat yoluna SIFIR dokundugunu sayiyla
   gostermek. TUM parametrik aileler (jenerator/urunler/*.json) x malzeme/renk
   kombinasyonlari icin kurus tutarini hesaplar ve JSON dokum verir.

   Hesap GERCEK kodla yapilir (kopya mantik yok):
     /secenekler.js  -> parametrikFiyatKurus
     /jenerator/hacim.js -> hacim formulleri
     /jenerator/konfigurator.js -> KONF.fiyatKurus

   Kullanim:
     node onizleme/test/fiyat-taban-olcum.mjs --yaz <cikti.json>   # dokum yaz
     node onizleme/test/fiyat-taban-olcum.mjs --karsilastir <taban.json>
        -> taban ile fark ADEDINI basar; fark varsa exit 1 (KIRMIZI). */
"use strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");

const kum = { window: {}, console, Math, JSON, parseFloat, isNaN, isFinite,
              String, Number, Object, Array };
kum.globalThis = kum;
kum.self = kum;
vm.createContext(kum);
for (const rel of [["secenekler.js"], ["jenerator", "hacim.js"],
                   ["jenerator", "konfigurator.js"]]) {
  vm.runInContext(fs.readFileSync(path.join(KOK, ...rel), "utf8"), kum);
}
const SECENEK = kum.window.PRUVO_SECENEK || kum.PRUVO_SECENEK;
const KONF = kum.window.PRUVO_KONF || kum.PRUVO_KONF;
if (!SECENEK || !KONF) { throw new Error("secenekler.js / konfigurator.js yuklenemedi"); }

const MALZEMELER = ["PLA", "PETG", "TPU", "ASA"];
const RENKLER = ["Siyah", "Beyaz", "Gri", "Diğer"];

const dizin = path.join(KOK, "jenerator", "urunler");
const cikti = {};
for (const ad of fs.readdirSync(dizin).sort()) {
  if (!ad.endsWith(".json")) { continue; }
  const sema = JSON.parse(fs.readFileSync(path.join(dizin, ad), "utf8"));
  const d = KONF.varsayilanDegerler(sema);
  const satir = {};
  for (const m of MALZEMELER) {
    for (const r of RENKLER) {
      const k = KONF.fiyatKurus(sema, d, m, r,
        { secenek: SECENEK, hacim: kum.window.PRUVO_HACIM || kum.PRUVO_HACIM });
      satir[m + "/" + r] = (k == null) ? null : k;
    }
  }
  cikti[ad.replace(/\.json$/, "")] = satir;
}

const arg = process.argv.slice(2);
if (arg[0] === "--karsilastir") {
  const taban = JSON.parse(fs.readFileSync(arg[1], "utf8"));
  let sapma = 0, toplam = 0;
  for (const aile of Object.keys(taban)) {
    for (const kombin of Object.keys(taban[aile])) {
      toplam++;
      const a = taban[aile][kombin];
      const b = (cikti[aile] || {})[kombin];
      if (a !== b) {
        sapma++;
        console.log("SAPMA " + aile + " " + kombin + ": " + a + " -> " + b);
      }
    }
  }
  for (const aile of Object.keys(cikti)) {
    if (!taban[aile]) { sapma++; console.log("YENI AILE: " + aile); }
  }
  console.log("aile=" + Object.keys(cikti).length + " kombinasyon=" + toplam +
              " SAPMA=" + sapma);
  process.exit(sapma ? 1 : 0);
} else if (arg[0] === "--yaz") {
  fs.writeFileSync(arg[1], JSON.stringify(cikti, null, 1));
  console.log("yazildi: " + arg[1] + " (aile=" + Object.keys(cikti).length + ")");
} else {
  console.log(JSON.stringify(cikti, null, 1));
}
