#!/usr/bin/env node
/**
 * IKI GOVDE (2-RENK YAZI) KABUL KAPISI — worker ucu + viewer + urun sayfasi.
 *
 * NEDEN VAR (Okan, canli, 29 Tem 2026): /urun/olcuye-ozel-cerceve/ sayfasi
 * "Yazı rengi (2. renk)" seceneğini SUNUYOR ama hicbir sey yapmiyordu — uretim
 * yolu tek govde donduruyor, yazi cerceveyle AYNI filamandan basiliyordu.
 * Site satiyor, uretim veremiyordu.
 *
 * NE OLCER (dar, dogru etiket — hepsi GERCEK kodla; taklit yalniz GL/DOM katmani):
 *  K) WORKER (onizleme/src/index.js, gercek default.fetch):
 *   K1 GERIYE DONUK UYUM: `parca` ALANI OLMAYAN istek, degisiklikten ONCEKI
 *      onbellek anahtarinin HARFI HARFINE AYNISINI uretir (donmus literal;
 *      literal HEAD~ kaynagindan olculmustur, bkz. DONMUS_TEK_GOVDE).
 *   K2 parcali anahtar: onizleme/<surum>/<aile>/<parca>/<ozet> — ozet bolumu
 *      tek govdelininkiyle AYNI (fark YALNIZ parca segmentinden gelir).
 *   K3 uc anahtar da BIRBIRINDEN farkli (parcalar ayni kovaya dusmez).
 *   K4 BELIRLENIMCILIK: ayni yazi -> ayni anahtar; farkli yazi -> farkli anahtar
 *      (her parca icin ayri ayri).
 *   K5 derleyiciye giden ESLEM AILESI "<aile>#<parca>" (parcasizda ailenin kendisi).
 *   K6 FAIL-CLOSED parca kapisi: liste disi/tip disi deger 400 `gecersiz-parca`;
 *      cok govdeli OLMAYAN ailede `parca` verilirse de 400.
 *   K7 ONBELLEK IZOLASYONU: bir parcaya yazilan govde DIGER parcada servis edilmez.
 *  V) VIEWER (jenerator/viewer.js, gercek kod + WebGL kaydedici):
 *   V1 iki govde -> IKI cizim, IKI FARKLI uRenk.
 *   V2 HIZALAMA: viewer govdeleri KAYDIRMAZ — kamera TUM govdelerin ORTAK
 *      kutusundan turer (uDonus ortak merkezi orijine tasir; 0. govdenin KENDI
 *      merkezini TASIMAZ). Govde basina merkezleme yapan bir viewer burada kirmizi yanar.
 *   V3 ESKI CAGRI BICIMI (tek ArrayBuffer + {renk}) aynen calisir: 1 cizim, 1 renk.
 *   V4 renklerAyarla() yeniden indirmeden iki rengi de degistirir.
 *  S) URUN SAYFASI (tools/build.py ONIZLEME_JS — canli sayfaya basilan metnin ta kendisi):
 *   S1 2-renk secilince IKI istek gider (parca=govde + parca=yazi) ve viewer'a
 *      IKI FARKLI renk ulasir.
 *   S2 yazi rengi YOKSA tek istek gider ve istekte `parca` alani HIC bulunmaz
 *      (geriye donuk yol).
 *   S3 yazi rengi GOVDE rengiyle AYNIYSA tek istek (tek filaman = tek govde).
 *   S4 yazi rengi temsil edilemiyorsa ("Diğer") tek istek — uydurma renk gosterilmez.
 *   S5 "Yazı rengi (2. renk)" secicisi onizlemeye BAGLI: degeri degisince ekrandaki
 *      yazi rengi degisir (Okan'in sikayetinin dogrudan ikizi).
 *  R) RENDER (CPU rasterlestirici, ortak/raster.mjs — viewer'in KENDI isik/kamera
 *     matematigi): 3 govde rengi x 2 yazi rengi = 6 kombinasyon; her cift
 *     BIRBIRINDEN piksel duzeyinde ayrisir.
 *
 * NE OLCMEZ (iddia edilmez):
 *   * Uretilen MESH'lerin gercekten ayristigini / ust uste oturdugunu (openscad
 *     gerekir -> onizleme/test/iki-govde-olcum.py, onizleme-imaj.yml'de kosar).
 *   * Eslem/-D tarafini (o eksen: tools/iki-govde-kapisi.py).
 *   * Gercek WebGL surucusunun cikisini (MSAA yok -> kotumser tahmin).
 *   * FIYATI (2-renk ucreti bu turda DEGISMEDI; sifir).
 *
 * KIRMIZI-MUTASYON (`--kendini-test`, ham cikti RAPOR-MIMARA.md'de):
 *   (a) anahtarUret'ten parca segmenti kaldirilir      -> K2/K3/K7 KIRMIZI
 *   (b) sayfa iki govdeyi AYNI renge boyar             -> S1 KIRMIZI
 *   (c) viewer govdeleri AYRI AYRI merkezler (hizalama kayar) -> V2 KIRMIZI
 *   (d) geriye donuk yol degisir (parcasiz istege de segment eklenir) -> K1 KIRMIZI
 *
 * NODE 20 UYUMU: worker kaynagi bare JSON import kullanir (esbuild bundle'lar);
 * JSON import'lari gomulu `const`a cevrilir. Node 22+ API'si KULLANILMAZ.
 *
 * Kullanim:
 *   node onizleme/test/iki-govde-kabul.mjs
 *   node onizleme/test/iki-govde-kabul.mjs --kendini-test
 *   node onizleme/test/iki-govde-kabul.mjs --index <yol> --viewer <yol> \
 *        --secenekler <yol> --build <yol>      (mutant kaynakla kosum)
 */
"use strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { kutu, ucgenNormali, modelKutusu, stlYaz, cizCok, fark, mat4Vek }
  from "./ortak/raster.mjs";
import { sahteGl, sorgu, ogeFabrikasi } from "./ortak/sahte-dom.mjs";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const ONIZLEME = path.dirname(TEST_DIR);
const KOK = path.dirname(ONIZLEME);
const SRC = path.join(ONIZLEME, "src");
const SHOP_SRC = path.join(KOK, "shop", "src");

// ---- kaynak yollari (mutant kosumlarda ezilir) ----
function bayrak(ad, varsayilan) {
  const i = process.argv.indexOf("--" + ad);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : varsayilan;
}
const YOL = {
  index: bayrak("index", path.join(SRC, "index.js")),
  viewer: bayrak("viewer", path.join(KOK, "jenerator", "viewer.js")),
  secenekler: bayrak("secenekler", path.join(KOK, "secenekler.js")),
  build: bayrak("build", path.join(KOK, "tools", "build.py")),
};

const AILE = "olcuye-ozel-cerceve";
const PARAM = { acilik_eni: 100, acilik_boyu: 150, kenar_genisligi: 12,
                derinlik: 5.2, kenar_stili: "chamfer", yazi: "OKAN" };
const PARAM_B = { ...PARAM, yazi: "ZZZZZZZZ" };

/* DONMUS TEK-GOVDE ANAHTARI — 2-renk calismasindan ONCEKI kaynakla (HEAD
   940373ac, onizleme/src/index.js) YUKARIDAKI PARAM icin OLCULMUS deger.
   Bu literal "geriye donuk uyum" iddiasinin CAPASIDIR: parcasiz cagrinin
   anahtari bir harf bile degisirse (or. parca segmenti kosulsuz eklenirse ya da
   ONBELLEK_SURUM oynarsa) canlida ONCEDEN onizlenmis her parametre seti
   onbellekten DUSER ve derleyici gereksiz yere yeniden yuklenir. */
const DONMUS_TEK_GOVDE =
  "onizleme/v7/olcuye-ozel-cerceve/" +
  "02de200ad769f77574ef7188d156b6a4d0030c5ab3523e96d55a276bd3689500.stl.gz";

const hatalar = [];
const olcumler = [];
function iddia(ad, kosul, detay) {
  console.log((kosul ? "  [OK ] " : "  [KIRMIZI] ") + ad + (detay ? " -> " + detay : ""));
  if (!kosul) { hatalar.push(ad); }
}

// ================================================================ K) WORKER
const TEMP_ONEK = "src-ikigovde-tmp-";
const TEMP_DIZIN = path.join(ONIZLEME, TEMP_ONEK + process.pid);

function jsonGom(kaynak, kaynakDizin, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(kaynakDizin, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ")");
  }
  return cikti;
}

function tempSupur() {
  for (const ad of fs.readdirSync(ONIZLEME)) {
    if (ad.startsWith(TEMP_ONEK)) {
      fs.rmSync(path.join(ONIZLEME, ad), { recursive: true, force: true });
    }
  }
}

function tempKur() {
  tempSupur();
  fs.mkdirSync(TEMP_DIZIN, { recursive: true });
  fs.writeFileSync(path.join(TEMP_DIZIN, "derleyici.js"),
                   fs.readFileSync(path.join(SRC, "derleyici.js"), "utf8"));
  fs.writeFileSync(path.join(TEMP_DIZIN, "semalar.js"),
                   jsonGom(fs.readFileSync(path.join(SHOP_SRC, "semalar.js"), "utf8"),
                           SHOP_SRC, "semalar.js"));
}

/** Gecerli minik binary STL (derleyici taklidi bunu dondurur). */
function kucukStl(kenar) {
  const t = [];
  kutu(t, 0, kenar, 0, kenar, 0, kenar);
  return stlYaz(t);
}

let sayac = 0;
/** GERCEK worker'i yukleyip istek atar. Doner:
 *  {durum, anahtar(lar), derleyiciAilesi, kova} — kova: sahte R2 icerigi. */
async function workerCagir(kaynak, govde, secenek) {
  sayac += 1;
  const yol = path.join(TEMP_DIZIN, "index-" + sayac + ".js");
  const hazir = kaynak.replace('from "../../shop/src/semalar.js"', 'from "./semalar.js"');
  if (hazir === kaynak) { throw new Error("semalar.js import yolu bulunamadi (yukleyici bayat)"); }
  fs.writeFileSync(yol, jsonGom(hazir, SRC, "index.js"));
  const mod = await import(pathToFileURL(yol).href);
  const sorulan = [];
  const yazilan = [];
  const kova = (secenek && secenek.kova) || new Map();
  const derleyiciAileleri = [];
  const env = {
    SITE_URL: "https://pruvo3d.com",
    ONBELLEK: {
      async get(anahtar) {
        sorulan.push(anahtar);
        const v = kova.get(anahtar);
        return v ? { body: v.govde, customMetadata: { hamBoyut: String(v.ham) } } : null;
      },
      async put(anahtar, govde, ust) {
        yazilan.push(anahtar);
        kova.set(anahtar, { govde, ham: (ust && ust.customMetadata &&
                                         ust.customMetadata.hamBoyut) || "0" });
      },
    },
    // DERLEYICI taklidi: gercek adaptor (src/derleyici.js) uzerinden gelir.
    // Sadece hangi ESLEM AILESI istendigini kaydeder ve gecerli bir STL doner.
    DERLEYICI: {
      async fetch(url, istek) {
        const g = JSON.parse(istek.body);
        derleyiciAileleri.push(g.aile);
        const stl = kucukStl(10 + derleyiciAileleri.length);
        return new Response(stl, { status: 200 });
      },
    },
  };
  const istek = new Request("https://pruvo3d.com/api/onizleme/olustur", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(govde),
  });
  const yanit = await mod.default.fetch(istek, env);
  let hata = null;
  if (yanit.status !== 200) { try { hata = (await yanit.clone().json()).hata; } catch (e) { /* */ } }
  return { durum: yanit.status, hata, anahtar: sorulan[0], sorulan, yazilan,
           kova, derleyiciAileleri,
           kaynakBasligi: yanit.headers.get("X-Kaynak") };
}

async function workerOlcumleri(kaynak) {
  console.log("\n-- K) WORKER: onbellek anahtari + parca kapisi --");
  const tek = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM });
  iddia("K1 parcasiz anahtar DEGISMEDI (bit-ayni, donmus capaya esit)",
        tek.anahtar === DONMUS_TEK_GOVDE,
        "cari=" + tek.anahtar + (tek.anahtar === DONMUS_TEK_GOVDE ? "" :
          " | beklenen=" + DONMUS_TEK_GOVDE));
  olcumler.push("tek govde anahtari: " + tek.anahtar);

  const g = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM, parca: "govde" });
  const y = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM, parca: "yazi" });
  const tp = String(tek.anahtar).split("/");     // onizleme/<v>/<aile>/<ozet>
  const gp = String(g.anahtar).split("/");       // onizleme/<v>/<aile>/<parca>/<ozet>
  const yp = String(y.anahtar).split("/");
  iddia("K2a govde anahtari bicimi onizleme/<surum>/<aile>/<parca>/<ozet>",
        gp.length === 5 && gp[0] === "onizleme" && gp[2] === AILE && gp[3] === "govde",
        g.anahtar);
  iddia("K2b yazi anahtari bicimi onizleme/<surum>/<aile>/<parca>/<ozet>",
        yp.length === 5 && yp[3] === "yazi", y.anahtar);
  iddia("K2c parametre OZETI tek govdelininkiyle AYNI (fark yalniz parca segmenti)",
        gp[4] === tp[3] && yp[4] === tp[3],
        "ozet=" + String(tp[3]).slice(0, 16) + "…");
  iddia("K2d surum bolumu ayni (ONBELLEK_SURUM bump'i GEREKMEDI)",
        gp[1] === tp[1] && yp[1] === tp[1], "surum=" + tp[1]);
  iddia("K3 uc anahtar da BIRBIRINDEN farkli",
        new Set([tek.anahtar, g.anahtar, y.anahtar]).size === 3);
  olcumler.push("parcali anahtarlar: " + g.anahtar + " | " + y.anahtar);

  // K4 belirlenimcilik
  const g2 = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM, parca: "govde" });
  iddia("K4a ayni yazi -> AYNI anahtar (govde)", g2.anahtar === g.anahtar, g2.anahtar);
  const gB = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM_B, parca: "govde" });
  const yB = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM_B, parca: "yazi" });
  iddia("K4b farkli yazi -> FARKLI anahtar (govde)", gB.anahtar !== g.anahtar,
        "OKAN vs ZZZZZZZZ");
  iddia("K4c farkli yazi -> FARKLI anahtar (yazi)", yB.anahtar !== y.anahtar);

  // K5 derleyiciye giden eslem ailesi
  iddia("K5a parcasiz istek -> derleyici ailesi = aile",
        tek.derleyiciAileleri.length === 1 && tek.derleyiciAileleri[0] === AILE,
        JSON.stringify(tek.derleyiciAileleri));
  iddia("K5b parca=govde -> derleyici ailesi '<aile>#govde'",
        g.derleyiciAileleri[0] === AILE + "#govde", JSON.stringify(g.derleyiciAileleri));
  iddia("K5c parca=yazi -> derleyici ailesi '<aile>#yazi'",
        y.derleyiciAileleri[0] === AILE + "#yazi", JSON.stringify(y.derleyiciAileleri));

  // K6 fail-closed parca kapisi
  const kotuler = ["kapak", "", "GOVDE", "govde/yazi", null, 5, true];
  let hepsi400 = true, ornekler = [];
  for (const p of kotuler) {
    const r = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM, parca: p });
    ornekler.push(JSON.stringify(p) + "->" + r.durum + "/" + r.hata);
    if (!(r.durum === 400 && r.hata === "gecersiz-parca")) { hepsi400 = false; }
  }
  iddia("K6a liste disi/tip disi `parca` -> 400 gecersiz-parca", hepsi400,
        ornekler.join("  "));
  // Cok govdeli OLMAYAN bir aile: parametreler kendi SEMASININ varsayilanlarindan
  // kurulur (elle yazilirsa sema kapisi once patlar ve olculen sey parca kapisi olmaz).
  const digerAile = "olcuye-ozel-oring-conta";
  const digerSema = JSON.parse(fs.readFileSync(
    path.join(KOK, "jenerator", "urunler", digerAile + ".json"), "utf8"));
  const digerParam = {};
  for (const p of digerSema.parametreler) { digerParam[p.ad] = p.varsayilan; }
  const r2 = await workerCagir(kaynak, {
    aile: digerAile, parametreler: digerParam, parca: "govde" });
  iddia("K6b cok govdeli OLMAYAN ailede `parca` -> 400",
        r2.durum === 400 && r2.hata === "gecersiz-parca",
        digerAile + " -> " + r2.durum + "/" + r2.hata);

  // K7 onbellek izolasyonu: paylasilan kova
  const kova = new Map();
  const p1 = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM, parca: "govde" }, { kova });
  const p2 = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM, parca: "yazi" }, { kova });
  const p3 = await workerCagir(kaynak, { aile: AILE, parametreler: PARAM, parca: "govde" }, { kova });
  iddia("K7a ilk govde istegi derleyiciye gitti", p1.kaynakBasligi === "derleyici",
        "X-Kaynak=" + p1.kaynakBasligi);
  iddia("K7b yazi istegi govde onbellegine DUSMEDI (derleyiciye gitti)",
        p2.kaynakBasligi === "derleyici" && p2.derleyiciAileleri[0] === AILE + "#yazi",
        "X-Kaynak=" + p2.kaynakBasligi + " aile=" + p2.derleyiciAileleri[0]);
  iddia("K7c ikinci govde istegi ONBELLEKTEN geldi (derleyici cagrilmadi)",
        p3.kaynakBasligi === "onbellek" && p3.derleyiciAileleri.length === 0,
        "X-Kaynak=" + p3.kaynakBasligi + " derleyici cagrisi=" + p3.derleyiciAileleri.length);
  iddia("K7d kovada IKI AYRI nesne var", kova.size === 2,
        [...kova.keys()].join("  "));
}

// ================================================================ fikstur mesh
/* Olculer CANLI mesh'ten (POST /api/onizleme/olustur, aile=olcuye-ozel-cerceve,
   acilik 100x150, kenar 12, derinlik 5,2, chamfer):
     govde bbox x[-62,1..62,1] y[-87,1..87,1] z[0..5,2]
     yazi  bbox y[-83,5..-77,1] z[5,2..6,4]  (kabartma 1,2 mm, harf boyu 6,4 mm) */
const OLCU = { disEn: 124.2, disBoy: 174.2, derinlik: 5.2, acilikEn: 100, acilikBoy: 150,
               yaziY0: -83.5, yaziY1: -77.1, kabartma: 1.2, cizgi: 1.2, harfAdet: 8 };

function govdeMesh() {
  const t = [];
  const dx = OLCU.disEn / 2, dy = OLCU.disBoy / 2;
  const ax = OLCU.acilikEn / 2, ay = OLCU.acilikBoy / 2;
  kutu(t, -dx, dx, ay, dy, 0, OLCU.derinlik);
  kutu(t, -dx, dx, -dy, -ay, 0, OLCU.derinlik);
  kutu(t, -dx, -ax, -ay, ay, 0, OLCU.derinlik);
  kutu(t, ax, dx, -ay, ay, 0, OLCU.derinlik);
  return t;
}

function yaziMesh() {
  const t = [];
  const h = OLCU.yaziY1 - OLCU.yaziY0, c = OLCU.cizgi;
  const genislik = 4.5, aralik = 5.6;
  const basla = -((OLCU.harfAdet - 1) * aralik + genislik) / 2;
  const z0 = OLCU.derinlik, z1 = OLCU.derinlik + OLCU.kabartma;
  for (let i = 0; i < OLCU.harfAdet; i++) {
    const x0 = basla + i * aralik;
    kutu(t, x0, x0 + genislik, OLCU.yaziY1 - c, OLCU.yaziY1, z0, z1);
    kutu(t, x0, x0 + genislik, OLCU.yaziY0, OLCU.yaziY0 + c, z0, z1);
    kutu(t, x0 + (genislik - c) / 2, x0 + (genislik + c) / 2,
         OLCU.yaziY0, OLCU.yaziY0 + h, z0, z1);
  }
  return t;
}

// ================================================================ V) VIEWER
function viewerKum() {
  const kum = { console, Math, JSON, Float32Array, ArrayBuffer, DataView,
                WeakMap, Map, Set, Infinity, NaN, Array, Object, String, Number, Boolean,
                Error, Promise, Buffer,
                requestAnimationFrame: (fn) => { Promise.resolve().then(fn); return 1; },
                devicePixelRatio: 1, addEventListener: () => {}, removeEventListener: () => {} };
  // viewer.js kokunu `window`dan alir; kum havuzunun KENDISI window olmali
  // (bos bir {} verilseydi root.addEventListener yok diye patlardi).
  kum.window = kum;
  kum.globalThis = kum;
  kum.self = kum;
  vm.createContext(kum);
  vm.runInContext(fs.readFileSync(YOL.viewer, "utf8"), kum);
  return kum.PRUVO_VIEWER;
}

function sahteTuval(kayit) {
  const gl = sahteGl(kayit);
  return { getContext: () => gl, clientWidth: 380, clientHeight: 320,
           width: 0, height: 0, style: {}, setPointerCapture: () => {},
           addEventListener: () => {}, removeEventListener: () => {} };
}

async function viewerOlcumleri(VIEWER, RGB) {
  console.log("\n-- V) VIEWER: cok govde, iki renk, HIZALAMA --");
  const govdeStl = stlYaz(govdeMesh());
  const yaziStl = stlYaz(yaziMesh());

  const k1 = {};
  const t1 = sahteTuval(k1);
  const kol = VIEWER.goster(t1, [{ buf: govdeStl, renk: RGB.Siyah },
                                 { buf: yaziStl, renk: RGB.Beyaz }]);
  await new Promise((c) => setTimeout(c, 0));
  iddia("V1a iki govde -> IKI cizim", k1.cizim === 2, "cizim=" + k1.cizim);
  const renkler = k1.cizimler.map((c) => JSON.stringify(c.renk));
  iddia("V1b iki cizim IKI FARKLI renkle yapildi", new Set(renkler).size === 2,
        renkler.join(" | "));
  iddia("V1c renkler musterinin sectikleri (govde=Siyah, yazi=Beyaz)",
        renkler[0] === JSON.stringify(RGB.Siyah) && renkler[1] === JSON.stringify(RGB.Beyaz));
  iddia("V1d cizim ucgen sayilari iki AYRI govdeye ait",
        k1.cizimler[0].adet === govdeMesh().length * 3 &&
        k1.cizimler[1].adet === yaziMesh().length * 3,
        "govde=" + k1.cizimler[0].adet / 3 + " ucgen · yazi=" + k1.cizimler[1].adet / 3 + " ucgen");

  // V2 HIZALAMA: uDonus ORTAK merkezi orijine tasir, 0. govdenin kendi merkezini DEGIL.
  const ortak = modelKutusu(govdeMesh().concat(yaziMesh())).merkez;
  const yalnizGovde = modelKutusu(govdeMesh()).merkez;
  const D = k1.donusler[k1.donusler.length - 1];
  const uygula = (p) => mat4Vek(D, [p[0], p[1], p[2], 1]);
  const oOrtak = uygula(ortak), oGovde = uygula(yalnizGovde);
  const uz = (v) => Math.hypot(v[0], v[1], v[2]);
  iddia("V2a uDonus ORTAK merkezi orijine tasiyor (govdeler KAYDIRILMAMIS)",
        uz(oOrtak) < 1e-3, "|T(ortak merkez)| = " + uz(oOrtak).toFixed(6));
  iddia("V2b 0. govdenin KENDI merkezi orijine TASINMIYOR (govde-basi merkezleme YOK)",
        uz(oGovde) > 1e-3, "|T(govde merkezi)| = " + uz(oGovde).toFixed(4) +
        " (ortak ile fark = " + Math.hypot(ortak[0] - yalnizGovde[0],
          ortak[1] - yalnizGovde[1], ortak[2] - yalnizGovde[2]).toFixed(4) + " mm)");
  olcumler.push("hizalama: |T(ortak)|=" + uz(oOrtak).toFixed(6) +
                " · |T(govde)|=" + uz(oGovde).toFixed(4));

  // V4 renklerAyarla — yeniden indirmeden iki rengi de degistir
  const oncekiCizim = k1.cizim;
  kol.renklerAyarla([RGB.Gri, RGB.Siyah]);
  await new Promise((c) => setTimeout(c, 0));
  const son2 = k1.cizimler.slice(-2).map((c) => JSON.stringify(c.renk));
  iddia("V4 renklerAyarla iki rengi birden tazeler (yeniden indirme YOK)",
        k1.cizim === oncekiCizim + 2 &&
        son2[0] === JSON.stringify(RGB.Gri) && son2[1] === JSON.stringify(RGB.Siyah),
        son2.join(" | "));

  // V3 eski cagri bicimi
  const k2 = {};
  const t2 = sahteTuval(k2);
  VIEWER.goster(t2, govdeStl, { renk: RGB.Beyaz });
  await new Promise((c) => setTimeout(c, 0));
  iddia("V3 ESKI cagri bicimi (tek ArrayBuffer + {renk}) -> 1 cizim, 1 renk",
        k2.cizim === 1 && JSON.stringify(k2.cizimler[0].renk) === JSON.stringify(RGB.Beyaz),
        "cizim=" + k2.cizim + " renk=" + JSON.stringify(k2.cizimler[0].renk));
}

// ================================================================ R) RENDER
function renderOlcumleri(VIEWER, RGB) {
  console.log("\n-- R) RENDER: 3 govde rengi x 2 yazi rengi = 6 kombinasyon --");
  const G = govdeMesh(), Y = yaziMesh();
  const GOVDE_RENKLER = ["Siyah", "Beyaz", "Gri"];
  const YAZI_RENKLER = ["Beyaz", "Gri"];
  const [W, H] = [380, 320];
  const kombin = [];
  for (const gr of GOVDE_RENKLER) {
    for (const yr of YAZI_RENKLER) {
      if (gr === yr) { continue; }        // ayni renk = 2-renk DEGIL (tek filaman)
      kombin.push({ ad: gr + "/" + yr,
                    render: cizCok(VIEWER, [{ ucgenler: G, renk: RGB[gr] },
                                            { ucgenler: Y, renk: RGB[yr] }], W, H) });
    }
  }
  // Ayni renk cifti atlandi -> Beyaz/Beyaz ve Gri/Gri yok. Yerine 2 gecerli cift daha:
  for (const [gr, yr] of [["Beyaz", "Siyah"], ["Gri", "Siyah"]]) {
    kombin.push({ ad: gr + "/" + yr,
                  render: cizCok(VIEWER, [{ ucgenler: G, renk: RGB[gr] },
                                          { ucgenler: Y, renk: RGB[yr] }], W, H) });
  }
  iddia("R0 6 gecerli 2-renk kombinasyonu olculdu", kombin.length === 6,
        kombin.map((k) => k.ad).join(", "));
  let enKucuk = Infinity, enKucukAd = "";
  let hepsiAyri = true;
  for (let i = 0; i < kombin.length; i++) {
    for (let j = i + 1; j < kombin.length; j++) {
      const f = fark(kombin[i].render, kombin[j].render, 6);
      if (f.piksel < enKucuk) { enKucuk = f.piksel; enKucukAd = kombin[i].ad + " vs " + kombin[j].ad; }
      if (!(f.piksel >= 100 && f.azami >= 6)) { hepsiAyri = false; }
    }
  }
  iddia("R1 her kombinasyon cifti RENDER'da ayrisir (>=100 piksel, >=6 ton)",
        hepsiAyri, "en az ayrisan cift: " + enKucukAd + " -> " + enKucuk + " piksel");
  olcumler.push("6 kombinasyon, en az ayrisan cift " + enKucuk + " piksel (" + enKucukAd + ")");

  // R2: YALNIZ yazi rengi degisince de ekran degisir (govde rengi SABIT).
  const a = cizCok(VIEWER, [{ ucgenler: G, renk: RGB.Siyah },
                            { ucgenler: Y, renk: RGB.Beyaz }], W, H);
  const b = cizCok(VIEWER, [{ ucgenler: G, renk: RGB.Siyah },
                            { ucgenler: Y, renk: RGB.Gri }], W, H);
  const f2 = fark(a, b, 6);
  iddia("R2 govde rengi SABIT, yalniz yazi rengi degisince ekran DEGISIR",
        f2.piksel >= 50 && f2.azami >= 6,
        f2.piksel + " piksel, azami " + f2.azami.toFixed(1) + " ton");
  olcumler.push("yalniz yazi rengi: " + f2.piksel + " piksel degisiyor");
}

// ================================================================ S) SAYFA
async function sayfaKos(script, markup, konfSatir, seciliRenk) {
  const { oge } = ogeFabrikasi();
  const btnYap = (ad) => oge({ sinif: [markup.btnSinif], _oz: { "data-renk": ad } });
  const btnlar = { Siyah: btnYap("Siyah"), Beyaz: btnYap("Beyaz"), Gri: btnYap("Gri") };
  const kap = oge({ id: markup.kapId, sinif: ["renk-butonlar"],
                    cocuk: Object.values(btnlar) });
  btnlar[seciliRenk].sinif = btnlar[seciliRenk].sinif.concat([markup.seciliSinif]);
  const yaziRenkSec = oge({ id: "konf_yazi_renk", value: konfSatir.yazi_renk || "" });
  const ogeler = {
    onizleBtn: oge({ id: "onizleBtn" }), onizlemeKutu: oge({ id: "onizlemeKutu" }),
    onizlemeDurum: oge({ id: "onizlemeDurum" }), onizlemeTuval: oge({ id: "onizlemeTuval" }),
    konf_yazi_renk: yaziRenkSec,
  };
  const kokOge = oge({ id: "belge", cocuk: [kap].concat(Object.values(ogeler)) });
  const kayit = {};
  const gl = sahteGl(kayit);
  ogeler.onizlemeTuval = Object.assign(ogeler.onizlemeTuval, {
    getContext: () => gl, clientWidth: 380, clientHeight: 320,
    width: 0, height: 0, style: {}, setPointerCapture: () => {} });
  const istekler = [];
  const govdeStl = stlYaz(govdeMesh()), yaziStl = stlYaz(yaziMesh());
  const sahte = {
    console, Float32Array, ArrayBuffer, DataView, WeakMap, Map, Math, Infinity, NaN,
    JSON, Promise, Object, Array, String, Number, Boolean,
    requestAnimationFrame: (fn) => { Promise.resolve().then(fn); return 1; },
    devicePixelRatio: 1, addEventListener: () => {}, removeEventListener: () => {},
    document: {
      getElementById: (id) => ogeler[id] || null,
      querySelector: (s) => sorgu(kokOge, s, false),
      querySelectorAll: (s) => sorgu(kokOge, s, true),
      addEventListener: () => {},
    },
    URUN: { id: AILE },
    PRUVO_KONF: {
      hazir: () => true, gecerliMi: () => true,
      // GERCEK konfigurator degil: bu kapinin olctugu sey sayfa scripti; konfigurator
      // 2-renk karari ayri kapida (jenerator/test + shop/test/iki-renk-ucret.mjs).
      satiraYaz: (satir) => {
        const y = yaziRenkSec.value;
        const cikti = { parametreler: { ...PARAM } };
        if (y && y !== satir.renk) { cikti.yazi_renk = y; }
        return cikti;
      },
    },
    fetch: (url, ayar) => {
      const g = JSON.parse(ayar.body);
      istekler.push(g);
      // Sunucu taklidi: `parcaHatasi` verilirse parcali istekler o hatayla 4xx doner
      // (derleyici imaji henuz parca ailelerini tasimiyor senaryosu).
      const hata = konfSatir.parcaHatasi;
      if (hata && g.parca) {
        return Promise.resolve({
          ok: false, headers: { get: () => null },
          json: () => Promise.resolve({ hata }),
        });
      }
      return Promise.resolve({
        ok: true, headers: { get: () => null },
        arrayBuffer: () => Promise.resolve(g.parca === "yazi" ? yaziStl : govdeStl),
      });
    },
  };
  sahte.window = sahte;
  sahte.globalThis = sahte;
  vm.createContext(sahte);
  vm.runInContext(fs.readFileSync(YOL.secenekler, "utf8"), sahte);
  vm.runInContext(fs.readFileSync(YOL.viewer, "utf8"), sahte);
  vm.runInContext(script, sahte);
  ogeler.onizleBtn.atesle("click");
  for (let i = 0; i < 25; i++) { await Promise.resolve(); }
  return { istekler, kayit, yaziRenkSec, ogeler, durumMetni: ogeler.onizlemeDurum.textContent };
}

async function sayfaOlcumleri(RGB) {
  console.log("\n-- S) URUN SAYFASI (build.py ONIZLEME_JS, uctan uca) --");
  const buildPy = fs.readFileSync(YOL.build, "utf8");
  const m = buildPy.match(/\nONIZLEME_JS = """\n([\s\S]*?)\n"""\n/);
  iddia("S0a build.py ONIZLEME_JS blogu okundu", !!m);
  const mKap = buildPy.match(/<div class="renk-butonlar" id="([A-Za-z0-9_-]+)">/);
  const mBtn = buildPy.match(/<button type="button" class="([A-Za-z0-9_-]+)" data-renk=/);
  const mSec = buildPy.match(/rbtnlar\[n\]\.classList\.toggle\("([A-Za-z0-9_-]+)"/);
  iddia("S0b build.py renk markup capalari okundu", !!(mKap && mBtn && mSec),
        JSON.stringify([mKap && mKap[1], mBtn && mBtn[1], mSec && mSec[1]]));
  if (!(m && mKap && mBtn && mSec)) { return; }
  const markup = { kapId: mKap[1], btnSinif: mBtn[1], seciliSinif: mSec[1] };

  // S1: 2-renk (govde Siyah, yazi Beyaz)
  const s1 = await sayfaKos(m[1], markup, { yazi_renk: "Beyaz" }, "Siyah");
  iddia("S1a 2-renk secilince IKI istek gider", s1.istekler.length === 2,
        "istek=" + s1.istekler.length);
  iddia("S1b istekler parca=govde ve parca=yazi tasiyor",
        s1.istekler.length === 2 && s1.istekler[0].parca === "govde" &&
        s1.istekler[1].parca === "yazi",
        JSON.stringify(s1.istekler.map((x) => x.parca)));
  const s1renk = (s1.kayit.cizimler || []).slice(-2).map((c) => JSON.stringify(c.renk));
  iddia("S1c viewer'a IKI FARKLI renk ulasti (govde=Siyah, yazi=Beyaz)",
        s1renk.length === 2 && new Set(s1renk).size === 2 &&
        s1renk[0] === JSON.stringify(RGB.Siyah) && s1renk[1] === JSON.stringify(RGB.Beyaz),
        s1renk.join(" | "));
  olcumler.push("sayfa 2-renk: " + s1.istekler.length + " istek, renkler " + s1renk.join(" / "));

  // S2: yazi rengi YOK -> tek istek, `parca` alani HIC yok (geriye donuk yol)
  const s2 = await sayfaKos(m[1], markup, {}, "Siyah");
  iddia("S2a yazi rengi yok -> TEK istek", s2.istekler.length === 1,
        "istek=" + s2.istekler.length);
  iddia("S2b istekte `parca` alani HIC YOK (geriye donuk govde)",
        s2.istekler.length === 1 && !("parca" in s2.istekler[0]),
        JSON.stringify(Object.keys(s2.istekler[0] || {})));

  // S3: yazi rengi GOVDE rengiyle ayni -> tek istek
  const s3 = await sayfaKos(m[1], markup, { yazi_renk: "Siyah" }, "Siyah");
  iddia("S3 yazi rengi = govde rengi -> TEK istek (tek filaman)",
        s3.istekler.length === 1 && !("parca" in s3.istekler[0]),
        "istek=" + s3.istekler.length);

  // S4: temsil edilemeyen renk ("Diğer")
  const s4 = await sayfaKos(m[1], markup, { yazi_renk: "Diğer" }, "Siyah");
  iddia("S4 temsil edilemeyen yazi rengi ('Diğer') -> TEK istek (uydurma renk YOK)",
        s4.istekler.length === 1 && !("parca" in s4.istekler[0]),
        "istek=" + s4.istekler.length);

  // S6: YAYIN SIRASI YEDEGI — derleyici imaji parca ailelerini henuz tasimiyorsa
  // onizleme BOS KALMAZ, tek govdeye duser. GERCEK musteri hatasi maskelenmez.
  const s6 = await sayfaKos(m[1], markup,
    { yazi_renk: "Beyaz", parcaHatasi: "aile-yok" }, "Siyah");
  iddia("S6a parca ailesi yoksa TEK GOVDEYE dusuluyor (ekran bos kalmiyor)",
        s6.istekler.length === 3 && !("parca" in s6.istekler[2]) &&
        (s6.kayit.cizim || 0) > 0,
        "istek=" + JSON.stringify(s6.istekler.map((x) => x.parca || "-")) +
        " cizim=" + (s6.kayit.cizim || 0));
  const s6b = await sayfaKos(m[1], markup,
    { yazi_renk: "Beyaz", parcaHatasi: "gecersiz-geometri" }, "Siyah");
  iddia("S6b GERCEK musteri hatasi (gecersiz-geometri) MASKELENMIYOR",
        s6b.istekler.every((x) => !!x.parca) && (s6b.kayit.cizim || 0) === 0 &&
        /üretilemiyor/.test(s6b.ogeler.onizlemeDurum.textContent),
        "istek=" + s6b.istekler.length + " cizim=" + (s6b.kayit.cizim || 0) +
        " mesaj=" + JSON.stringify(s6b.ogeler.onizlemeDurum.textContent));

  // S5: yazi rengi SECICISI onizlemeye bagli mi
  iddia("S5a '#konf_yazi_renk' secicisine change dinleyicisi BAGLANDI",
        s1.yaziRenkSec.dinleyiciVarMi("change"));
  const oncekiCizim = s1.kayit.cizim;
  s1.yaziRenkSec.value = "Gri";
  s1.yaziRenkSec.atesle("change");
  for (let i = 0; i < 10; i++) { await Promise.resolve(); }
  const yeni = (s1.kayit.cizimler || []).slice(-2).map((c) => JSON.stringify(c.renk));
  iddia("S5b yazi rengi degisince EKRANDAKI yazi rengi degisti (yeniden indirme YOK)",
        s1.kayit.cizim > oncekiCizim && yeni[1] === JSON.stringify(RGB.Gri) &&
        s1.istekler.length === 2,
        "yeni renkler=" + yeni.join(" | ") + " · toplam istek=" + s1.istekler.length);
}

// ================================================================ mutasyonlar
function mutantKos(etiket, degisiklikler) {
  const dizin = fs.mkdtempSync(path.join(ONIZLEME, "mutant-"));
  const args = [];
  for (const [anahtar, [kaynakYol, ara, yerine]] of Object.entries(degisiklikler)) {
    const ham = fs.readFileSync(kaynakYol, "utf8");
    if (!ham.includes(ara)) {
      console.log("  [KIRMIZI] mutasyon capasi bulunamadi (" + etiket + "): " + ara.slice(0, 60));
      fs.rmSync(dizin, { recursive: true, force: true });
      return { kod: -1, cikti: "capa yok" };
    }
    const hedef = path.join(dizin, path.basename(kaynakYol));
    fs.writeFileSync(hedef, ham.replace(ara, yerine));
    args.push("--" + anahtar, hedef);
  }
  const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url), ...args],
                      { encoding: "utf8" });
  fs.rmSync(dizin, { recursive: true, force: true });
  return { kod: r.status, cikti: (r.stdout || "") + (r.stderr || "") };
}

function kendiniTest() {
  console.log("== KIRMIZI-MUTASYON TURU (her biri KIRMIZI yanmali) ==");
  const mutasyonlar = [
    ["(a) anahtarUret'ten parca segmenti kaldirilir", {
      index: [path.join(SRC, "index.js"),
              'const ek = parca ? (parca + "/") : "";',
              'const ek = "";'] }],
    ["(b) sayfa iki govdeyi AYNI renge boyar", {
      build: [path.join(KOK, "tools", "build.py"),
              "[{ buf:buflar[0], renk:ik.govdeRenk }, { buf:buflar[1], renk:ik.yaziRenk }]",
              "[{ buf:buflar[0], renk:ik.govdeRenk }, { buf:buflar[1], renk:ik.govdeRenk }]"] }],
    ["(c) viewer kamerayi yalniz 0. govdeden turetir (hizalama kayar)", {
      viewer: [path.join(KOK, "jenerator", "viewer.js"),
               "          for (var k = 0; k < 3; k++) {\n" +
               "            if (veri.enKucuk[k] < az[k]) { az[k] = veri.enKucuk[k]; }\n" +
               "            if (veri.enBuyuk[k] > cok[k]) { cok[k] = veri.enBuyuk[k]; }\n" +
               "          }",
               "          for (var k = 0; i === 0 && k < 3; k++) {\n" +
               "            if (veri.enKucuk[k] < az[k]) { az[k] = veri.enKucuk[k]; }\n" +
               "            if (veri.enBuyuk[k] > cok[k]) { cok[k] = veri.enBuyuk[k]; }\n" +
               "          }"] }],
    ["(d) geriye donuk yol degisir (parcasiz istege de segment eklenir)", {
      index: [path.join(SRC, "index.js"),
              'const ek = parca ? (parca + "/") : "";',
              'const ek = parca ? (parca + "/") : "tek/";'] }],
    ["(e) parca kapisi FAIL-OPEN olur (tanimadigi parcayi yok sayar)", {
      index: [path.join(SRC, "index.js"),
              'return { hataYanit: json({ hata: "gecersiz-parca", alan: "parca" }, 400, env) };',
              "return { parca: null };"] }],
  ];
  let dusen = 0;
  for (const [etiket, deg] of mutasyonlar) {
    const r = mutantKos(etiket, deg);
    const kirmizi = r.kod !== 0;
    console.log((kirmizi ? "  [OK ] " : "  [KIRMIZI] ") + etiket +
                " -> cikis kodu " + r.kod + (kirmizi ? " (yakalandi)" : " (KACTI)"));
    // Hangi iddianin dustugunu goster (ham kanit).
    for (const satir of r.cikti.split("\n")) {
      if (satir.includes("[KIRMIZI]")) { console.log("        " + satir.trim()); }
    }
    if (!kirmizi) { dusen++; }
  }
  console.log(dusen ? "\nOZ-TEST KIRMIZI: " + dusen + "/" + mutasyonlar.length + " mutasyon KACTI"
                    : "\nOZ-TEST YESIL: " + mutasyonlar.length + "/" + mutasyonlar.length +
                      " mutasyon yakalandi");
  return dusen ? 1 : 0;
}

// ================================================================ ana
async function main() {
  if (process.argv.includes("--kendini-test")) { process.exit(kendiniTest()); }
  console.log("== IKI GOVDE (2-RENK) KABUL KAPISI ==");
  console.log("kaynaklar: index=" + path.relative(KOK, YOL.index) +
              " viewer=" + path.relative(KOK, YOL.viewer) +
              " secenekler=" + path.relative(KOK, YOL.secenekler) +
              " build=" + path.relative(KOK, YOL.build));

  const secKum = { window: {}, console, Math, JSON };
  secKum.globalThis = secKum; secKum.self = secKum;
  vm.createContext(secKum);
  vm.runInContext(fs.readFileSync(YOL.secenekler, "utf8"), secKum);
  const SECENEK = secKum.window.PRUVO_SECENEK;
  const RGB = {};
  for (const r of ["Siyah", "Beyaz", "Gri"]) { RGB[r] = SECENEK.onizlemeRengi(AILE, r); }
  iddia("0a secenekler.js ONIZLEME_PARCALAR cerceve ailesini tanimliyor",
        !!(SECENEK.ONIZLEME_PARCALAR && SECENEK.ONIZLEME_PARCALAR[AILE]),
        JSON.stringify(SECENEK.ONIZLEME_PARCALAR));
  iddia("0b onizlemeIkiRenk() tek kaynak fonksiyonu var",
        typeof SECENEK.onizlemeIkiRenk === "function");

  tempKur();
  try {
    await workerOlcumleri(fs.readFileSync(YOL.index, "utf8"));
  } finally {
    fs.rmSync(TEMP_DIZIN, { recursive: true, force: true });
  }

  const VIEWER = viewerKum();
  await viewerOlcumleri(VIEWER, RGB);
  renderOlcumleri(VIEWER, RGB);
  await sayfaOlcumleri(RGB);

  console.log("\n== OLCUMLER ==");
  for (const o of olcumler) { console.log("   " + o); }
  console.log(hatalar.length
    ? "\nSONUC: KIRMIZI (" + hatalar.length + " iddia dustu)"
    : "\nSONUC: YESIL ✅");
  process.exit(hatalar.length ? 1 : 0);
}

main().catch((e) => {
  console.error("SONUC: KIRMIZI — kosum patladi: " + ((e && e.stack) || e));
  process.exit(1);
});
