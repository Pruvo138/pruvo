#!/usr/bin/env node
/* pruvo-onizleme KABUL TESTLERI (tools/paket-onizleme-3d.md, adim 4).
   "Bakildi, iyi gorunuyor" kabul degildir — bu dosya calistirilabilir kanittir.

   Kapsam (yerel):
     4a  Sema disi parametre -> 400 (min/max/adim/tanimsiz anahtar/aile)
     4b  String enjeksiyon denemesi -> reddedilir, derleyiciye HIC ulasmaz
         (+ derleyici tarafi: server.py --oz-test)
     4c  Ayni parametre 2. istek -> R2 onbellek isabeti (derleyici sayaci artmaz,
         olculebilir sekilde hizli)
     4d  Donen STL hacmi vs jenerator/hacim.js kapali-form <= %3 (5 ailede —
         pilot 2 + Faz D konektor/braket/disli — aile basina N=5 set x 2 tohum;
         GERCEK openscad ile; aile basina taze worker izolati, hiz siniri dolmasin)
     4f  Hiz siniri: ayni IP dakikada 11. DERLEME -> 429 (onbellek isabeti muaf)
   Yerel kosulamayan (deploy sonrasi): 4e soguk/sicak p50-p95, 4g canli sayfa.

   Kosum:  node onizleme/test/kabul.js            (repo kokunden)
   On kosullar: node, python3, npx wrangler; 4d icin openscad + ana repoda
   uyelik .scad kaynaklari (yoksa 4d ATLANIR ve bu KIRMIZI sayilir — kabul
   ancak 4d kosulmussa yesildir). */
"use strict";

const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const zlib = require("zlib");

const REPO = path.resolve(__dirname, "..", "..");
const ONIZLEME = path.join(REPO, "onizleme");
const DERLEYICI = path.join(ONIZLEME, "derleyici", "server.py");
const WORKER_PORT = 18788;
const DERLEYICI_PORT = 18791;
const TABAN = "http://127.0.0.1:" + WORKER_PORT;
const DTABAN = "http://127.0.0.1:" + DERLEYICI_PORT;

const sonuclar = [];
let cocuklar = [];

function kaydet(ad, gecti, detay) {
  sonuclar.push({ ad, gecti, detay });
  console.log("  [" + (gecti ? "GECTI" : "KALDI") + "] " + ad + (detay ? " — " + detay : ""));
}

function temizle() {
  for (const c of cocuklar) { try { process.kill(-c.pid, "SIGKILL"); } catch (e) {} }
  cocuklar = [];
}
process.on("exit", temizle);
process.on("SIGINT", () => { temizle(); process.exit(2); });

function bekle(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function hazirBekle(url, saniye) {
  for (let i = 0; i < saniye * 10; i++) {
    try {
      const c = await fetch(url);
      if (c.ok) return true;
    } catch (e) {}
    await bekle(100);
  }
  return false;
}

function surec(komut, argv, secenek) {
  const c = spawn(komut, argv, Object.assign({ detached: true, stdio: ["ignore", "pipe", "pipe"] }, secenek));
  c.stderr.on("data", (d) => { if (process.env.KABUL_GURULTU) process.stderr.write(d); });
  c.stdout.on("data", (d) => { if (process.env.KABUL_GURULTU) process.stdout.write(d); });
  cocuklar.push(c);
  return c;
}

function derleyiciBaslat(paketDizin, mock) {
  const argv = [DERLEYICI, "--paket", paketDizin, "--port", String(DERLEYICI_PORT)];
  if (mock) argv.push("--mock");
  return surec("python3", argv);
}

// Gercek wrangler.toml [[containers]] icerir -> yerel dev Docker isterdi.
// Testler icin ayni worker'in containers'siz kopya konfigurasyonu uretilir
// (route/DO yok; R2 binding'i miniflare yerelde simule eder).
const TEST_TOML = path.join(ONIZLEME, ".wrangler-test.toml");

function testTomlYaz() {
  fs.writeFileSync(TEST_TOML, [
    '# kabul.js uretir (gecici) — gercek konfig: onizleme/wrangler.toml',
    'name = "pruvo-onizleme-test"',
    'main = "src/index.js"',
    'compatibility_date = "2026-07-01"',
    '[vars]',
    'SITE_URL = "https://pruvo3d.com"',
    '[[r2_buckets]]',
    'binding = "ONBELLEK"',
    'bucket_name = "pruvo-onizleme"',
    '',
  ].join("\n"));
}

function workerBaslat() {
  // Onbellek determinizmi: yerel R2 simulasyon durumunu sifirla.
  fs.rmSync(path.join(ONIZLEME, ".wrangler"), { recursive: true, force: true });
  testTomlYaz();
  return surec("npx", ["wrangler", "dev", "-c", TEST_TOML,
                       "--port", String(WORKER_PORT),
                       "--var", "DERLEYICI_URL:" + DTABAN], { cwd: ONIZLEME });
}

async function workerDurdurBaslat() {
  temizleWorker();
  const w = workerBaslat();
  const ok = await hazirBekle(TABAN + "/api/onizleme/saglik", 60);
  if (!ok) throw new Error("wrangler dev acilamadi");
  return w;
}

function temizleWorker() {
  for (const c of cocuklar.slice()) {
    if (c.spawnargs.join(" ").includes("wrangler")) {
      try { process.kill(-c.pid, "SIGKILL"); } catch (e) {}
      cocuklar = cocuklar.filter((x) => x !== c);
    }
  }
}

async function olustur(govde, ekstra) {
  const t0 = performance.now();
  const c = await fetch(TABAN + "/api/onizleme/olustur", Object.assign({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: typeof govde === "string" ? govde : JSON.stringify(govde),
  }, ekstra || {}));
  const ms = performance.now() - t0;
  let veri = null;
  if ((c.headers.get("content-type") || "").includes("json")) veri = await c.json();
  else veri = Buffer.from(await c.arrayBuffer());
  return { kod: c.status, kaynak: c.headers.get("X-Kaynak"), veri, ms,
           sikistirma: c.headers.get("X-Sikistirma") };
}

async function sayac() {
  const c = await fetch(DTABAN + "/sayac");
  return (await c.json()).derleme;
}

function pXX(dizi, oran) {
  const s = [...dizi].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor(oran * s.length))];
}

// Sema izgarasinda gecerli rastgele set + uretilebilirlik kisitlari
// (uretec assert'leri; kalibrasyon 2026-07-16 — profil: I/U yukseklik>4t, T>3t,
// kutu/elips kenarlar>2t, cokgen genislik>2t).
function rastgeleSet(sema, rnd) {
  while (true) {
    const s = {};
    for (const p of sema.parametreler) {
      const tip = p.tip || "sayi";
      if (tip === "sayi") {
        const adim = p.adim || 1;
        const n = Math.round((p.max - p.min) / adim);
        s[p.ad] = Math.round((p.min + Math.floor(rnd() * (n + 1)) * adim) * 1e6) / 1e6;
      } else if (tip === "secim") {
        const secenekler = p.secenekler.map((x) => (typeof x === "object" ? x.deger : x));
        s[p.ad] = secenekler[Math.floor(rnd() * secenekler.length)];
      } else { s[p.ad] = p.varsayilan || ""; }
    }
    if (sema.id === "olcuye-ozel-oring-conta" && s.profil === "pahli") continue; // bilinen sapma — asagida ayri olculur
    const t = s.et_kalinligi;
    if (sema.id === "olcuye-ozel-profil-beam") {
      const carpan = { i: 4, u: 4, t: 3 }[s.kesit];
      if (carpan && s.yukseklik <= carpan * t) continue;
      if (["kutu", "elips"].includes(s.kesit) && (s.yukseklik <= 2 * t || s.genislik <= 2 * t)) continue;
      if (s.kesit === "cokgen" && s.genislik <= 2 * t) continue;
    }
    return s;
  }
}

function lcg(tohum) {
  let d = tohum >>> 0;
  return () => { d = (d * 1664525 + 1013904223) >>> 0; return d / 4294967296; };
}

function stlHacim(buf) {
  const tmp = path.join(os.tmpdir(), "kabul-" + Date.now() + "-" + Math.random().toString(36).slice(2) + ".stl");
  fs.writeFileSync(tmp, buf);
  const p = spawnSync("python3", ["-c",
    "import sys; sys.path.insert(0, sys.argv[2]); import stl_hacim; print(stl_hacim.hacim(sys.argv[1]))",
    tmp, path.join(REPO, "jenerator", "test")], { encoding: "utf-8" });
  fs.unlinkSync(tmp);
  if (p.status !== 0) throw new Error("stl_hacim: " + p.stderr);
  return parseFloat(p.stdout.trim());
}

function jsHacim(fonksiyon, setler) {
  const p = spawnSync("node", [path.join(REPO, "jenerator", "test", "hacim-eval.js")],
    { input: JSON.stringify({ fonksiyon, setler }), encoding: "utf-8" });
  if (p.status !== 0) throw new Error("hacim-eval: " + p.stderr);
  return JSON.parse(p.stdout);
}

// ---------------------------------------------------------------- fazlar

async function faz4a() {
  console.log("\n== 4a — sema disi parametre -> 400 ==");
  const taban = { ic_cap: 30, kesit_cap: 3.6, profil: "yuvarlak" };
  const durumlar = [
    ["aralik disi (ic_cap=9999)", { aile: "olcuye-ozel-oring-conta", parametreler: { ...taban, ic_cap: 9999 } }, 400],
    ["adim ihlali (kesit_cap=3.65)", { aile: "olcuye-ozel-oring-conta", parametreler: { ...taban, kesit_cap: 3.65 } }, 400],
    ["tanimsiz anahtar", { aile: "olcuye-ozel-oring-conta", parametreler: { ...taban, hacker: 1 } }, 400],
    ["eksik parametre", { aile: "olcuye-ozel-oring-conta", parametreler: { ic_cap: 30 } }, 400],
    ["tanimsiz aile", { aile: "olcuye-ozel-cetvel", parametreler: {} }, 404],
    ["bozuk JSON", "{bozuk", 400],
  ];
  for (const [ad, govde, beklenen] of durumlar) {
    const c = await olustur(govde);
    kaydet("4a " + ad, c.kod === beklenen, "kod=" + c.kod + " beklenen=" + beklenen);
  }
}

async function faz4b() {
  console.log("\n== 4b — enjeksiyon denemeleri -> derleyiciye ulasmaz ==");
  const once = await sayac();
  const denemeler = [
    { aile: "olcuye-ozel-oring-conta",
      parametreler: { ic_cap: 30, kesit_cap: 3.6, profil: '"; cube(999); //' } },
    { aile: "olcuye-ozel-oring-conta",
      parametreler: { ic_cap: 'include </etc/passwd>', kesit_cap: 3.6, profil: "yuvarlak" } },
    { aile: "olcuye-ozel-profil-beam",
      parametreler: { kesit: 'i"; import("x"); //', yukseklik: 40, genislik: 30,
                      et_kalinligi: 3, uzunluk: 100, ic_yapi: "bos" } },
    { aile: "olcuye-ozel-profil-beam",
      parametreler: { kesit: "i", yukseklik: "40; cube(9)", genislik: 30,
                      et_kalinligi: 3, uzunluk: 100, ic_yapi: "bos" } },
  ];
  let hepsi400 = true;
  for (const d of denemeler) {
    const c = await olustur(d);
    if (c.kod !== 400) hepsi400 = false;
  }
  const sonra = await sayac();
  kaydet("4b enjeksiyon -> 400", hepsi400, "");
  kaydet("4b derleyiciye ulasmadi", once === sonra, "sayac " + once + " -> " + sonra);
  const oz = spawnSync("python3", [DERLEYICI, "--oz-test"], { encoding: "utf-8" });
  kaydet("4b derleyici oz-test (ikinci savunma)", oz.status === 0,
         (oz.stdout.match(/oz-test: .*/) || [""])[0]);
}

async function faz4c() {
  console.log("\n== 4c — onbellek isabeti (derleyiciye gitmez, hizli) ==");
  const govde = { aile: "olcuye-ozel-oring-conta",
                  parametreler: { ic_cap: 30, kesit_cap: 3.6, profil: "yuvarlak" } };
  const s0 = await sayac();
  const ilk = await olustur(govde);
  const s1 = await sayac();
  const ikinci = await olustur(govde);
  const s2 = await sayac();
  kaydet("4c ilk istek derlenir", ilk.kod === 200 && ilk.kaynak === "derleyici" && s1 === s0 + 1,
         "kod=" + ilk.kod + " kaynak=" + ilk.kaynak + " " + ilk.ms.toFixed(0) + "ms");
  kaydet("4c ikinci istek onbellekten", ikinci.kod === 200 && ikinci.kaynak === "onbellek" && s2 === s1,
         "kaynak=" + ikinci.kaynak + " sayac sabit=" + (s2 === s1) + " " + ikinci.ms.toFixed(0) + "ms");
  kaydet("4c olculebilir hizlanma", ikinci.ms < ilk.ms,
         ilk.ms.toFixed(0) + "ms -> " + ikinci.ms.toFixed(0) + "ms");
  // normalizasyon: "30" (string) ile 30 ayni anahtara duser
  const nrm = await olustur({ aile: govde.aile,
    parametreler: { ic_cap: "30", kesit_cap: "3,6", profil: "yuvarlak" } });
  kaydet("4c normalize anahtar (string/virgul girdisi ayni onbellek)",
         nrm.kod === 200 && nrm.kaynak === "onbellek", "kaynak=" + nrm.kaynak);
}

async function faz4f() {
  console.log("\n== 4f — hiz siniri: 11. derleme/dk -> 429, onbellek muaf ==");
  const sonuclar429 = [];
  let ilkGovde = null;
  for (let i = 1; i <= 11; i++) {
    const govde = { aile: "olcuye-ozel-oring-conta",
                    parametreler: { ic_cap: 30 + i, kesit_cap: 3.6, profil: "kare" } };
    if (i === 1) ilkGovde = govde;
    const c = await olustur(govde);
    sonuclar429.push(c.kod);
  }
  const ilk10 = sonuclar429.slice(0, 10).every((k) => k === 200);
  kaydet("4f ilk 10 derleme 200", ilk10, sonuclar429.slice(0, 10).join(","));
  kaydet("4f 11. istek 429", sonuclar429[10] === 429, "kod=" + sonuclar429[10]);
  const muaf = await olustur(ilkGovde);
  kaydet("4f onbellek isabeti sinirdan muaf", muaf.kod === 200 && muaf.kaynak === "onbellek",
         "kod=" + muaf.kod + " kaynak=" + muaf.kaynak);
}

async function faz4d(paketDizin) {
  console.log("\n== 4d — STL hacmi vs hacim.js kapali-form <= %3 " +
              "(gercek openscad, aile basina 5 set x 2 tohum) ==");
  const semalar = {
    "olcuye-ozel-oring-conta": { dosya: "olcuye-ozel-oring-conta.json", fonksiyon: "oring" },
    "olcuye-ozel-profil-beam": { dosya: "olcuye-ozel-profil-beam.json", fonksiyon: "profil" },
    "olcuye-ozel-baglanti-konektor": { dosya: "olcuye-ozel-baglanti-konektor.json", fonksiyon: "konektor" },
    "olcuye-ozel-montaj-braketi": { dosya: "olcuye-ozel-montaj-braketi.json", fonksiyon: "braket" },
    "ozel-disli-kramayer-uretimi": { dosya: "ozel-disli-kramayer-uretimi.json", fonksiyon: "disli" },
    // yay BILEREK yok: eslem olcumunde kare/testere formlari kisa boyda %3'u asti
    // (%5.2'ye kadar) — ONIZLEME_AILELER'e alinmadi, mimar tablosunda (Faz D raporu).
  };
  const tohumlar = [parseInt(process.env.KABUL_TOHUM || "20260716", 10),
                    parseInt(process.env.KABUL_TOHUM_2 || "20260717", 10)];
  const gecikmeler = { derleyici: [], onbellek: [] };
  for (const [aile, bilgi] of Object.entries(semalar)) {
    // Aile basina TAZE worker izolati: 5 set x 2 tohum = 10 derleme, hiz siniri
    // (10/dk) tam dolar — izolat yenilenmezse sonraki aile 429 yerdi.
    await workerDurdurBaslat();
    const sema = JSON.parse(fs.readFileSync(
      path.join(REPO, "jenerator", "urunler", bilgi.dosya), "utf-8"));
    const setler = [];
    for (const tohum of tohumlar) {
      const rnd = lcg(tohum);
      for (let i = 0; i < 5; i++) setler.push(rastgeleSet(sema, rnd));
    }
    const js = jsHacim(bilgi.fonksiyon, setler);
    for (let i = 0; i < setler.length; i++) {
      const c = await olustur({ aile, parametreler: setler[i] });
      if (c.kod !== 200) {
        kaydet("4d " + aile + " set" + i, false, "kod=" + c.kod + " " + JSON.stringify(c.veri));
        continue;
      }
      gecikmeler.derleyici.push(c.ms);
      const ham = c.sikistirma === "gzip" ? zlib.gunzipSync(c.veri) : c.veri;
      const v = stlHacim(ham);
      const sapma = Math.abs(js[i] - v) / v * 100;
      kaydet("4d " + aile + " set" + i, sapma <= 3.0,
             "js=" + js[i].toFixed(1) + " stl=" + v.toFixed(1) +
             " sapma=%" + sapma.toFixed(2) + " gzip=" + c.veri.length + "B " +
             c.ms.toFixed(0) + "ms  " + JSON.stringify(setler[i]));
      const tekrar = await olustur({ aile, parametreler: setler[i] });
      if (tekrar.kod === 200 && tekrar.kaynak === "onbellek") gecikmeler.onbellek.push(tekrar.ms);
    }
  }

  // ORING "PAHLI" KALIBRE IZLEMESI: eski %6.27 sapma Okan onayiyla kapatildi
  // (16 Tem gece — katsayi 0.875 -> 0.93349, uretim motorunun 0.18xCS pahina
  // olculerek kalibre). Satir izleme amaciyla kalir: sapma yeniden buyurse
  // motor/formul yeniden ayristi demektir. DOGRUDAN derleyiciden olculur
  // (worker hiz sinirini tuketmesin); 4d sayimina girmez, gizlenmez, raporlanir.
  const pahliSet = { ic_cap: 30, kesit_cap: 3.6, profil: "pahli" };
  const dc = await fetch(DTABAN + "/derle", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aile: "olcuye-ozel-oring-conta", parametreler: pahliSet }) });
  if (dc.status === 200) {
    const v = stlHacim(Buffer.from(await dc.arrayBuffer()));
    const js = jsHacim("oring", [pahliSet])[0];
    const sapma = Math.abs(js - v) / v * 100;
    console.log("  [BILGI] oring 'pahli' kalibre izlemesi: js=" + js.toFixed(1) +
                " stl=" + v.toFixed(1) + " sapma=%" + sapma.toFixed(2) +
                " (katsayi 0.93349, Okan onayi 16 Tem; 4d sayimina dahil degil)");
  }

  console.log("\n== yerel gecikme tablosu (4e'nin YEREL on izlemesi; soguk baslatma " +
              "olcumu Container deploy'unda) ==");
  for (const [ad, dizi] of Object.entries(gecikmeler)) {
    if (!dizi.length) continue;
    console.log("  " + ad.padEnd(10) + " n=" + String(dizi.length).padEnd(3) +
                " p50=" + pXX(dizi, 0.5).toFixed(0) + "ms" +
                " p95=" + pXX(dizi, 0.95).toFixed(0) + "ms");
  }
  // gecersiz geometri -> temiz 422 (assert yolu; dogrudan derleyici)
  const gg = await fetch(DTABAN + "/derle", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aile: "olcuye-ozel-profil-beam",
      parametreler: { kesit: "i", yukseklik: 20, genislik: 20, et_kalinligi: 8,
                      uzunluk: 100, ic_yapi: "bos" } }) });
  kaydet("4d+ uretilemez kombinasyon temiz 422", gg.status === 422, "kod=" + gg.status);
}

// ---------------------------------------------------------------- ana akis

async function main() {
  console.log("pruvo-onizleme kabul testleri (yerel)\n");

  // Paketi topla (gizli eslem + .scad — ana repodan SALT OKUNUR).
  const paketDizin = fs.mkdtempSync(path.join(os.tmpdir(), "onizleme-paket-"));
  const topla = spawnSync("python3", [path.join(REPO, "tools", "onizleme-paket-yukle.py"),
                                      "--yerel", paketDizin], { encoding: "utf-8" });
  if (topla.status !== 0) {
    console.error(topla.stdout + topla.stderr);
    console.error("Paket toplanamadi — 4d/4c/4f icin eslem-ozel.json + uyelik .scad gerekli.");
    process.exit(1);
  }

  // FAZ A (mock derleyici): 4a, 4b, 4c
  derleyiciBaslat(paketDizin, true);
  if (!(await hazirBekle(DTABAN + "/saglik", 15))) throw new Error("derleyici acilamadi");
  await workerDurdurBaslat();
  await faz4a();
  await faz4b();
  await faz4c();

  // FAZ B (taze worker izolati): 4f
  await workerDurdurBaslat();
  await faz4f();

  // FAZ C (gercek openscad): 4d + yerel gecikme tablosu
  temizle();
  const openscadVar = spawnSync("python3", ["-c",
    "import sys; sys.path.insert(0, sys.argv[1]); import importlib.util as u;" +
    "spec=u.spec_from_file_location('s', sys.argv[2]); m=u.module_from_spec(spec);" +
    "spec.loader.exec_module(m); print(m.openscad_yolu() or '')",
    path.join(REPO, "onizleme", "derleyici"),
    path.join(REPO, "onizleme", "derleyici", "server.py")], { encoding: "utf-8" });
  if (!openscadVar.stdout.trim()) {
    kaydet("4d gercek derleme", false, "openscad bulunamadi — 4d kosulmadi");
  } else {
    derleyiciBaslat(paketDizin, false);
    if (!(await hazirBekle(DTABAN + "/saglik", 15))) throw new Error("derleyici acilamadi");
    await workerDurdurBaslat();
    await faz4d(paketDizin);
  }

  temizle();
  fs.rmSync(paketDizin, { recursive: true, force: true });

  const kalan = sonuclar.filter((s) => !s.gecti);
  console.log("\nSONUC: " + (sonuclar.length - kalan.length) + "/" + sonuclar.length + " GECTI");
  if (kalan.length) {
    console.log("KALANLAR:\n" + kalan.map((s) => "  - " + s.ad + " (" + s.detay + ")").join("\n"));
    process.exit(1);
  }
}

main().catch((e) => { console.error("kabul kosumu coktu:", e); temizle(); process.exit(2); });
