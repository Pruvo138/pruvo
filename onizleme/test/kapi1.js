#!/usr/bin/env node
/* KAPI-1 + KABUL 4e — canli soguk/sicak/onbellek gecikme olcumu.
   (tools/paket-onizleme-3d.md adim 1 kapisi: soguk p95 > 10 sn VE onbellekle
   maskelenemiyorsa DUR.)

   Kosum: KAPAT_ANAHTAR=... node onizleme/test/kapi1.js [taban_url]
   Varsayilan taban: https://pruvo3d.com/api/onizleme
   - soguk: POST /derleyici-kapat (X-Kapat-Anahtar) -> container olur -> benzersiz
     parametreyle /olustur = imaj boot + derleme dahil uctan uca soguk sure.
   - sicak: container ayakta, benzersiz parametre -> saf derleme yolu.
   - onbellek: ayni parametre tekrar -> R2 isabeti.
   Hiz siniri 10 derleme/dk oldugu icin derleme istekleri ~8/dk'ya paslanir
   (dongu basi en az 8 sn); onbellek isabetleri muaf, paslanmaz. */
"use strict";

const TABAN = process.argv[2] || "https://pruvo3d.com/api/onizleme";
const ANAHTAR = process.env.KAPAT_ANAHTAR || "";
const SOGUK_N = 12, SICAK_N = 10, ONBELLEK_N = 10;
const KAPI_SOGUK_P95_MS = 10000;

function bekle(ms) { return new Promise((r) => setTimeout(r, ms)); }

function pXX(dizi, oran) {
  const s = [...dizi].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor(oran * s.length))];
}

// Taban Date.now'dan: onceki KOSULARIN urettigi setlerle cakisip R2 onbellegine
// dusmesin (16 Tem'de yasandi: 2. kosum tum "soguk" orneklerini onbellekten aldi).
// Faz D: olcum 5 aile uzerinde DONUSUMLU — her istek sirayla baska aileden gider,
// boylece p50/p95 tek ailenin degil, tum onizleme yuzeyinin sayisidir.
let sayac = Date.now() % 1000000;
const AILELER = [
  ["olcuye-ozel-profil-beam", (s) => ({
    kesit: "kutu", yukseklik: 20 + ((s * 7) % 181), genislik: 30,
    et_kalinligi: 3, uzunluk: 20 + (s % 981), ic_yapi: "bos" })],
  ["olcuye-ozel-oring-conta", (s) => ({
    ic_cap: 5 + ((s * 3) % 391) * 0.5, kesit_cap: 1 + (s % 141) * 0.1,
    profil: "yuvarlak" })],
  ["olcuye-ozel-baglanti-konektor", (s) => ({
    kol_sayisi: 2 + (s % 3), kol_kesiti: "yuvarlak",
    cubuk_capi: 6 + ((s * 5) % 29) * 0.5, kol_boyu: 20 + (s % 41),
    cidar: 2 + (s % 5) * 0.5, gecme: "normal" })],
  ["olcuye-ozel-montaj-braketi", (s) => ({
    tip: "acili", ic_aci: 60 + (s % 13) * 5, kalinlik: 3 + (s % 7) * 0.5,
    genislik: 20 + ((s * 11) % 21), uzunluk: 40 + (s % 81),
    delik_adet: 1 + (s % 3) })],
  ["ozel-disli-kramayer-uretimi", (s) => ({
    disli_tipi: "duz", dis_sayisi: 32 + (s % 33), modul: 1 + ((s * 3) % 11) * 0.05,
    kalinlik: 6 + (s % 5) * 0.5, delik_capi: 2 + ((s * 7) % 13) * 0.5 })],
  // Faz E: nihai liste 17 aile — olcum tum yuzeyde donusumlu.
  ["olcuye-ozel-yay-dalga-flexure", (s) => ({
    tip: "dalga", dalga_formu: ["sinus", "kare", "ucgen", "testere", "darbe"][s % 5],
    serbest_boy: 40 + (s % 81), dis_cap: 15 + ((s * 3) % 46),
    tel_capi: 1.5 + (s % 6) * 0.5, dalga_boyu: 40 + ((s * 7) % 81) })],
  ["kisiye-ozel-jeton-cip-madalyon", (s) => ({
    cap: 20 + (s % 61), kalinlik: 2.5 + ((s * 3) % 56) * 0.1,
    yazi_stili: ["gomme", "oyma", "kabartma"][s % 3],
    yuz_sayisi: s % 2 ? "cift" : "tek",
    kenar_deseni: s % 2 ? "segmentli" : "duz" })],
  ["olcuye-ozel-ramp-sim-takoz", (s) => ({
    genislik: 10 + ((s * 3) % 191), uzunluk: 20 + (s % 281),
    yukseklik: 2 + ((s * 7) % 149), egim_yontemi: "yukseklik",
    egim_acisi: 4 + (s % 57), ust_yuzey: ["duz", "tirtikli", "basamakli"][s % 3] })],
  ["olcuye-ozel-cetvel", (s) => ({
    tip: "duz", sistem: s % 2 ? "inc" : "metrik", uzunluk: 10 + (s % 41),
    genislik: 20 + ((s * 3) % 21), kalinlik: 2 + (s % 9) * 0.5,
    isaret_stili: ["kabartma", "oyma", "gomme"][s % 3] })],
  ["olcuye-ozel-huni", (s) => ({
    agiz_capi: 40 + ((s * 7) % 161), yukseklik: 30 + (s % 121),
    uc_capi: 4 + ((s * 3) % 49) * 0.5, uc_boyu: 54 + (s % 107),
    uc_acisi: (s % 13) * 5 })],
  ["olcuye-ozel-damga-kase", (s) => ({
    metin: "PRUVO", yazi_boyutu: 6 + (s % 17) * 0.5, dolgu: 3 + ((s * 3) % 15) * 0.5,
    bicim: "dikdortgen", kabartma_derinligi: 0.8 + (s % 15) * 0.1, sap: "sapsiz" })],
  ["olcuye-ozel-rulman", (s) => ({
    // eleman capi genislige sigacak bolge (bd = (dis-ic)/3 * carpan < genislik)
    ic_cap: 10 + (s % 10) * 0.5, dis_cap: 28 + (s % 9),
    genislik: 12 + ((s * 3) % 7) * 0.5,
    eleman: ["bilya", "makara", "tutmali"][s % 3],
    bosluk: 0.1 + (s % 5) * 0.05, flans: s % 2 ? "var" : "yok" })],
  ["olcuye-ozel-triger-kasnagi", (s) => ({
    profil: ["gt2_2mm", "htd_5mm", "t5", "xl"][s % 4], dis_sayisi: 18 + (s % 63),
    genislik: 4 + ((s * 3) % 53) * 0.5, mil_baglanti: s % 2 ? "altigen" : "duz",
    mil_capi: 3 + (s % 5) * 0.5,
    flans: ["iki_taraf", "ust", "alt", "yok"][s % 4] })],
  ["olcuye-ozel-triger-kayisi", (s) => ({
    profil: ["GT2_2mm", "HTD_5mm", "T5", "XL"][s % 4],
    sekil: s % 2 ? "kapali" : "duz", dis_sayisi: 20 + ((s * 7) % 281),
    genislik: 3 + (s % 95) * 0.5, dis_taraf: ["ic", "dis", "cift"][s % 3] })],
  ["olcuye-ozel-petek-delikli-panel", (s) => ({
    mod: "delikli", desen: ["petek", "yuvarlak", "kare", "sekizgen", "besgen", "ucgen"][s % 6],
    en: 30 + ((s * 3) % 171), boy: 30 + (s % 171),
    kalinlik: 1.5 + (s % 14) * 0.5, goz_boyutu: 3 + ((s * 7) % 13) })],
  ["olcuye-ozel-pervane-fan-cark", (s) => ({
    cap: 60 + ((s * 7) % 241), kanat_sayisi: 2 + (s % 5),
    mil_capi: 3 + (s % 19) * 0.5,
    mil_baglanti: ["duz", "kanalli", "altigen", "d_lama"][s % 4],
    burun_konisi: ["yok", "ogiv", "parabolik"][s % 3],
    dis_ring: s % 2 ? "var" : "yok" })],
  ["olcuye-ozel-izgara-menfez-kapak", (s) => ({
    tip: ["panjur", "delikli", "kor"][s % 3],
    delik_sekli: ["petek", "elips", "kare", "sekizgen", "ucgen", "besgen"][s % 6],
    en: 40 + ((s * 3) % 211), boy: 40 + (s % 211),
    derinlik: 3 + (s % 35) * 0.5, panjur_acisi: (s % 91) - 45 })],
];
function benzersizIstek() {
  sayac += 1;
  const [aile, uret] = AILELER[sayac % AILELER.length];
  // kesirli adimlarin float artigi izgarayi bozmasin
  const p = uret(sayac);
  for (const k of Object.keys(p)) {
    if (typeof p[k] === "number") p[k] = Math.round(p[k] * 100) / 100;
  }
  return { aile, parametreler: p };
}

async function olustur(istek) {
  const t0 = performance.now();
  const c = await fetch(TABAN + "/olustur", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(istek),
  });
  const govde = await c.arrayBuffer();
  return { ms: performance.now() - t0, kod: c.status, aile: istek.aile,
           kaynak: c.headers.get("X-Kaynak"), boyut: govde.byteLength,
           hata: c.status !== 200 ? Buffer.from(govde).toString("utf-8").slice(0, 200) : "" };
}

async function kapat() {
  const c = await fetch(TABAN + "/derleyici-kapat", {
    method: "POST", headers: { "X-Kapat-Anahtar": ANAHTAR } });
  if (c.status !== 200) throw new Error("kapat basarisiz: " + c.status + " " + await c.text());
}

async function main() {
  if (!ANAHTAR) { console.error("KAPAT_ANAHTAR ortam degiskeni gerekli"); process.exit(2); }
  console.log("KAPI-1 olcumu — taban: " + TABAN);

  const soguk = [], sicak = [], onbellek = [];

  console.log("\n-- SOGUK (" + SOGUK_N + " dongu: kapat -> benzersiz derleme, 5 aile donusumlu) --");
  for (let i = 0; i < SOGUK_N; i++) {
    const dt0 = Date.now();
    await kapat();
    await bekle(1500); // kapatma otursun
    const s = await olustur(benzersizIstek());
    console.log("  soguk %d: %d ms kod=%d kaynak=%s aile=%s %s",
                i + 1, Math.round(s.ms), s.kod, s.kaynak, s.aile, s.hata);
    if (s.kod === 200 && s.kaynak === "derleyici") soguk.push(s.ms);
    const gecen = Date.now() - dt0;
    if (gecen < 8000) await bekle(8000 - gecen); // <=8 derleme/dk
  }

  console.log("\n-- SICAK (" + SICAK_N + " benzersiz derleme, container ayakta, 5 aile donusumlu) --");
  const sicakIstekler = [];
  for (let i = 0; i < SICAK_N; i++) {
    const dt0 = Date.now();
    const istek = benzersizIstek();
    sicakIstekler.push(istek);
    const s = await olustur(istek);
    console.log("  sicak %d: %d ms kod=%d kaynak=%s aile=%s %s",
                i + 1, Math.round(s.ms), s.kod, s.kaynak, s.aile, s.hata);
    if (s.kod === 200 && s.kaynak === "derleyici") sicak.push(s.ms);
    const gecen = Date.now() - dt0;
    if (gecen < 8000) await bekle(8000 - gecen);
  }

  console.log("\n-- ONBELLEK (" + ONBELLEK_N + " tekrar, hiz sinirindan muaf) --");
  for (let i = 0; i < ONBELLEK_N; i++) {
    const s = await olustur(sicakIstekler[i % sicakIstekler.length]);
    console.log("  onbellek %d: %d ms kod=%d kaynak=%s", i + 1, Math.round(s.ms), s.kod, s.kaynak);
    if (s.kod === 200 && s.kaynak === "onbellek") onbellek.push(s.ms);
    await bekle(300);
  }

  console.log("\n== KAPI-1 / 4e TABLO (uctan uca, istemciden olculdu) ==");
  console.log("  tur       n    p50(ms)  p95(ms)");
  for (const [ad, d] of [["soguk", soguk], ["sicak", sicak], ["onbellek", onbellek]]) {
    if (!d.length) { console.log("  " + ad.padEnd(10) + "OLCUM YOK"); continue; }
    console.log("  " + ad.padEnd(10) + String(d.length).padEnd(5) +
                String(Math.round(pXX(d, 0.5))).padEnd(9) +
                String(Math.round(pXX(d, 0.95))));
  }

  const tam = soguk.length >= 10 && sicak.length >= 8 && onbellek.length >= 8;
  const p95 = soguk.length ? pXX(soguk, 0.95) : Infinity;
  if (!tam) { console.log("\nKAPI-1: OLCUM EKSIK (yukarida hatalara bak)"); process.exit(1); }
  if (p95 > KAPI_SOGUK_P95_MS) {
    console.log("\nKAPI-1: KIRMIZI — soguk p95 %d ms > %d ms. DUR, mimara rapor.",
                Math.round(p95), KAPI_SOGUK_P95_MS);
    process.exit(1);
  }
  console.log("\nKAPI-1: GECTI — soguk p95 %d ms <= %d ms.", Math.round(p95), KAPI_SOGUK_P95_MS);
}

main().catch((e) => { console.error("olcum coktu:", e); process.exit(2); });
