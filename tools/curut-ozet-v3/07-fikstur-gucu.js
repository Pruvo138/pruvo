#!/usr/bin/env node
/**
 * CURUTME 07 — EKSEN 4: `gorsel` onek fiksturu yeterince guclu mu?
 *
 * Kabul testindeki KENAR fiksturu bugun sunlari tasiyor:
 *   (a) onegi HIC tasimayan MUTLAK URL      ✔ var
 *   (b) degeri TAM OLARAK onek olan kart    ✔ var
 *   (c) kapaksiz urun (null)                ✔ var
 *   (d) onege BENZEYEN ama farkli konak      ✘ YOK
 * Ayrica hic denenmemis siniflar: GORELI URL ("://" tasimayan), PROTOKOL-GORELI ("//..."),
 * onekten sonra "://" tasiyan deger, dize OLMAYAN kapak.
 *
 * Her sinif GERCEK build.py (v2 ve v3) + CANLI ozetAc ile kosulur. Beklenen: her sinif ya
 * KAYIPSIZ acilir ya da build FAIL-CLOSED kirmizi yanar. "build yesil + deger BOZUK" hali
 * SESSIZ VERI BOZULMASIDIR.
 */
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const KOK = path.dirname(path.dirname(__dirname));
const BUILD = path.join(KOK, "tools", "build.py");
const ozetAc = require(path.join(KOK, "tools", "ozet-ac-ayikla.js")).ozetAcAl();
const GEC = fs.mkdtempSync(path.join(os.tmpdir(), "curut-fikstur-"));
const ONEK = "https://media.pruvo3d.com/urunler/";

let no = 0;
function uret(urunler, surum) {
  no += 1;
  const kat = path.join(GEC, "k" + no + ".json");
  const cik = path.join(GEC, "o" + no + ".json");
  fs.writeFileSync(kat, JSON.stringify(urunler), "utf8");
  const r = spawnSync("python3", [BUILD, "--sadece-ozet", "--katalog", kat, "--cikti", cik,
    "--ozet-surum", String(surum)], { encoding: "utf8" });
  if (r.status !== 0) {
    return { hata: String(r.stderr || r.stdout).trim().split("\n").pop().slice(0, 150) };
  }
  return { ozet: JSON.parse(fs.readFileSync(cik, "utf8")) };
}

const SINIFLAR = [
  ["(a) onegi HIC tasimayan mutlak URL", "https://ornek-baska-konak.example/x/y-1.jpg"],
  ["(b) deger TAM OLARAK onek", ONEK],
  ["(c) kapak YOK (bos dizi)", null],
  ["(d) onege BENZEYEN farkli konak", "https://media.pruvo3d.com.ornek.example/urunler/z.jpg"],
  ["(d2) ayni konak farkli yol", "https://media.pruvo3d.com/urunlerler/z.jpg"],
  ["(e) GORELI URL ('://' YOK)", "urunler/goreli-1.jpg"],
  ["(f) PROTOKOL-GORELI URL", "//media.pruvo3d.com/urunler/pg-1.jpg"],
  ["(g) onekten SONRA '://' tasiyan deger", ONEK + "https://tuzak.example/z.jpg"],
  ["(h) kapak DIZE degil (sayi)", 12345],
];

console.log("=== CURUTME 07 — `gorsel` onek fikstur gucu\n");
let bozuk = 0;
for (const [ad, deger] of SINIFLAR) {
  const l = [];
  l.push({
    id: "fx-hedef", kategori: "Marin", marka: [], baslik: "Hedef", aciklama: "a",
    fiyat: "1 TL", gorseller: deger === null ? [] : [deger],
  });
  for (let i = 0; i < 5; i++) {
    l.push({
      id: "fx-" + i, kategori: "Marin", marka: [], baslik: "D" + i, aciklama: "a",
      fiyat: "1 TL", gorseller: [ONEK + "d" + i + ".jpg"],
    });
  }
  const beklenen = deger === null ? null : deger;   // kart_ozeti gorseli BIREBIR tasir
  const satirlar = [];
  let sinifBozuk = false;
  for (const surum of [2, 3]) {
    const r = uret(l, surum);
    if (r.hata) { satirlar.push("v" + surum + " BUILD KIRMIZI: " + r.hata); continue; }
    const a = ozetAc(JSON.parse(JSON.stringify(r.ozet)));
    const kart = (a.bloklar.Marin || []).find((k) => k && k.id === "fx-hedef") || {};
    const g = ("gorsel" in kart) ? kart.gorsel : undefined;
    const es = JSON.stringify(g) === JSON.stringify(beklenen);
    if (!es) { sinifBozuk = true; }
    satirlar.push("v" + surum + " build YESIL | acilan gorsel=" + JSON.stringify(g)
      + " | beklenen=" + JSON.stringify(beklenen) + (es ? " ✔" : "  ✘ SESSIZ BOZULMA"));
  }
  if (sinifBozuk) { bozuk += 1; }
  console.log("  %s", ad);
  satirlar.forEach((s) => console.log("      %s", s));
}
fs.rmSync(GEC, { recursive: true, force: true });
console.log("\nSONUC: build YESIL iken degeri BOZULAN sinif %d/%d -> %s",
  bozuk, SINIFLAR.length, bozuk ? "KIRILDI" : "SAGLAM (kalan siniflar fail-closed)");
process.exit(bozuk ? 1 : 0);
