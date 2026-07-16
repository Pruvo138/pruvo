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

let sayac = 0;
function benzersizSet() {
  // Sema izgarasinda gecerli, her cagrida benzersiz (onbellege takilmasin):
  // uzunluk 20-1000 adim 1, yukseklik 20-200 adim 1 -> bol kombinasyon.
  sayac += 1;
  return { kesit: "kutu", yukseklik: 20 + (sayac % 180), genislik: 30,
           et_kalinligi: 3, uzunluk: 100 + sayac, ic_yapi: "bos" };
}

async function olustur(parametreler) {
  const t0 = performance.now();
  const c = await fetch(TABAN + "/olustur", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aile: "olcuye-ozel-profil-beam", parametreler }),
  });
  const govde = await c.arrayBuffer();
  return { ms: performance.now() - t0, kod: c.status,
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

  console.log("\n-- SOGUK (" + SOGUK_N + " dongu: kapat -> benzersiz derleme) --");
  for (let i = 0; i < SOGUK_N; i++) {
    const dt0 = Date.now();
    await kapat();
    await bekle(1500); // kapatma otursun
    const s = await olustur(benzersizSet());
    console.log("  soguk %d: %d ms kod=%d kaynak=%s %s",
                i + 1, Math.round(s.ms), s.kod, s.kaynak, s.hata);
    if (s.kod === 200 && s.kaynak === "derleyici") soguk.push(s.ms);
    const gecen = Date.now() - dt0;
    if (gecen < 8000) await bekle(8000 - gecen); // <=8 derleme/dk
  }

  console.log("\n-- SICAK (" + SICAK_N + " benzersiz derleme, container ayakta) --");
  const sicakSetler = [];
  for (let i = 0; i < SICAK_N; i++) {
    const dt0 = Date.now();
    const p = benzersizSet();
    sicakSetler.push(p);
    const s = await olustur(p);
    console.log("  sicak %d: %d ms kod=%d kaynak=%s %s",
                i + 1, Math.round(s.ms), s.kod, s.kaynak, s.hata);
    if (s.kod === 200 && s.kaynak === "derleyici") sicak.push(s.ms);
    const gecen = Date.now() - dt0;
    if (gecen < 8000) await bekle(8000 - gecen);
  }

  console.log("\n-- ONBELLEK (" + ONBELLEK_N + " tekrar, hiz sinirindan muaf) --");
  for (let i = 0; i < ONBELLEK_N; i++) {
    const s = await olustur(sicakSetler[i % sicakSetler.length]);
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
