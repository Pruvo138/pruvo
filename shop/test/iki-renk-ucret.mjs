#!/usr/bin/env node
/**
 * 2-RENK YAZI EK UCRETI KABUL TESTI — "karsiligi olmayan +75 TL tahsil edilmiyor" kapisi.
 *
 *   node shop/test/iki-renk-ucret.mjs
 *
 * NEDEN VAR (para duzlemi, 2026-07-29): cerceve ailesinde yazi rengi cerceve renginden farkli
 * secilince fiyata +7500 kurus ekleniyordu (gerekce: ayri govde / AMS 2. filaman). OLCUM bunu
 * curuttu: canli derleyiciye AYNI geometriyle yazi='' / 'OKAN' / 'WWWWWWWWWWWW' gonderildi,
 * ucunun ciktisi da 65284 bayt / 1304 ucgen / SHA-256 BIREBIR AYNI (uctu de taze derleme).
 * Yazi uretilen STL'e HIC girmiyor -> ek maliyet yok -> ucretin karsiligi yok. Ucret
 * secenekler.js IKI_RENK_EK_KURUS tek kaynagindan 0'a cekildi.
 *
 * NASIL (OFFLINE — wrangler/ag/gercek odeme YOK; shop/test/konfigur-fail-closed.mjs deseni):
 * shop/src/index.js'in KENDISI Node'a yuklenir, D1 ve iyzico yerine bellek-ici sahteleri
 * konur. Fiyat, Worker'in D1'e YAZDIGI siparis satirindan okunur — yani GERCEK para yolundan.
 * Hicbir dis servise istek gitmez, hicbir siparis olusmaz, hicbir kalici dosya degismez.
 * "ESKI" fiyatlar git HEAD kaynaklarindan AYNI yolla olculur (tahmin/sabit sayi YOK).
 *
 * AYNA (mirror) DUZENI: her surum (ESKI/YENI/MUTANT) icin gecici dizine kendi kaynak agaci
 * yazilir — <tmp>/secenekler.js, <tmp>/konfigur.js, <tmp>/jenerator/{konfigurator,hacim}.js,
 * <tmp>/shop/src/*.js — boylece goreli import'lar (../../secenekler.js) O SURUMUN dosyalarina
 * coozulur ve ayni kosumda eski ile yeni yan yana yuklenebilir. JSON import'lari (Node surum
 * farki yaratan import nitelikleri) icerige gomulur; package.json YAZILMAZ (gercek repoda da
 * yok — .js dosyalari Node'un sozdizimi tespitiyle ESM/CJS ayrilir, konfigurator.js CJS kalir).
 *
 * KOSTUGU 5 SET (hepsi bloklayici):
 *   (1) PARA KANITI  — (a) 2-renk kalem: YENI fiyat == ESKI fiyat - 7500 (tam), (b) yazisiz
 *       kalem DEGISMEDI, (c) yazi var ama yazi_renk == renk: DEGISMEDI (zaten ucret yoktu),
 *       (d) 3x tavan davranisi DEGISMEDI, (e) dar kenar (kenar<10mm) 2-renk REDDI DEGISMEDI.
 *   (2) PARITE      — ayni senaryolarda ON YUZ (jenerator/konfigurator.js, sahte DOM ile
 *       GERCEK satiraYaz) ile WORKER kurusu kurusuna esit. Esit degilse suite KIRMIZI.
 *   (3) REGRESYON   — 23 parametrik ailenin varsayilan olculerinde (2-renk YOK) YENI == ESKI.
 *   (4) VAKUM       — degisiklik geri alinirsa (IKI_RENK_EK_KURUS=7500) (1a) ESKI fiyata doner
 *       ve iddia KIRMIZI yanar; donmezse bu test OLU nobetcidir -> suite KIRMIZI.
 *   (5) TEK KAYNAK  — ne front ne Worker kaynaginda ikinci bir 7500 sabiti kalmamis olmali
 *       (iki taraf ayrisirsa gosterilen fiyat != tahsil edilen fiyat).
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath, pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const SRC = path.join(SHOP, "src");
const URUN_SEMA_DIZIN = path.join(KOK, "jenerator", "urunler");

const ESKI_EK_KURUS = 7500;          // kaldirilan ucret (kanit icin; kaynaktan DEGIL, iddiadan)
const CERCEVE = "olcuye-ozel-cerceve";

// ---------------------------------------------------------------- kaynak okuyucular

function diskten(rel) { return fs.readFileSync(path.join(KOK, rel), "utf8"); }
function headden(rel) {
  return execFileSync("git", ["-C", KOK, "show", "HEAD:" + rel],
                      { encoding: "utf8", maxBuffer: 1 << 28 });
}

/** `import X from "...json";` -> `const X = <json icerigi>;` (fail-closed: bozuk JSON patlar). */
function jsonGom(kaynak, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(SRC, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ") — desen guncellenmeli");
  }
  return cikti;
}

const KOK_DOSYALAR = ["secenekler.js", "konfigur.js",
                      "jenerator/konfigurator.js", "jenerator/hacim.js"];
const SRC_DOSYALAR = fs.readdirSync(SRC).filter((a) => a.endsWith(".js"));

const GECICI_KOK = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-iki-renk-"));
process.on("exit", () => { fs.rmSync(GECICI_KOK, { recursive: true, force: true }); });

/**
 * Bir surumun kaynak aynasini kurar.
 * @param {string} ad        ayna adi (dizin)
 * @param {(rel:string)=>string} oku   kaynak okuyucu (diskten / headden)
 * @param {(kaynak:string,rel:string)=>string} [yama]  istege bagli mutasyon
 */
function aynaKur(ad, oku, yama) {
  const taban = path.join(GECICI_KOK, ad);
  fs.mkdirSync(path.join(taban, "jenerator"), { recursive: true });
  fs.mkdirSync(path.join(taban, "shop", "src"), { recursive: true });
  const yaz = (rel, ham) => {
    const metin = yama ? yama(ham, rel) : ham;
    fs.writeFileSync(path.join(taban, rel), metin);
  };
  for (const rel of KOK_DOSYALAR) { yaz(rel, oku(rel)); }
  for (const dosya of SRC_DOSYALAR) {
    const rel = "shop/src/" + dosya;
    yaz(rel, jsonGom(oku(rel), ad + ":" + dosya));
  }
  return taban;
}

// ---------------------------------------------------------------- sahte cevre (D1 + iyzico)

let iyzicoCagri = 0;
globalThis.fetch = async function sahteFetch(hedef) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (u.includes("iyzico.test")) {
    iyzicoCagri += 1;
    return new Response(JSON.stringify({
      status: "success", token: "test-token-" + iyzicoCagri,
      paymentPageUrl: "https://odeme.test/sayfa",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  throw new Error("TESTTE BEKLENMEYEN AG ISTEGI: " + u);
};

function d1Sahte(satirlar, kayitlar) {
  const harita = new Map(satirlar.map((u) => [u.id, u]));
  return {
    prepare(sql) {
      return {
        bind(...arg) {
          return {
            async all() { return { results: arg.map((id) => harita.get(id)).filter(Boolean) }; },
            async first() { return null; },
            async run() { kayitlar.push({ sql, arg }); return { meta: { changes: 1 } }; },
          };
        },
      };
    },
  };
}

const ENV = {
  SITE_URL: "https://pruvo3d.com",
  IYZICO_BASE_URL: "https://iyzico.test",
  IYZICO_API_KEY: "test-api-key",
  IYZICO_SECRET_KEY: "test-secret-key",
};

/** /api/shop/baslat'i GERCEK worker kodundan cagirir; D1'e yazilan satiri dondurur. */
async function baslat(mod, d1Satirlari, kalem) {
  const kayitlar = [];
  const env = Object.assign({}, ENV, { KATALOG: d1Sahte(d1Satirlari, kayitlar) });
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sozlesme_onay: true, odeme: "kart",
      musteri: { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
                 adres: "Test mahallesi test sokak no 1", sehir: "Mugla" },
      sepet: [kalem],
    }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  const insert = kayitlar.find((k) => /INSERT INTO siparisler/.test(k.sql));
  let birimKurus = null, detay = null;
  if (insert) {
    const dizi = insert.arg.find((x) => typeof x === "string" && x.startsWith("["));
    const satir = dizi ? JSON.parse(dizi)[0] : null;
    birimKurus = satir ? satir.birim_kurus : null;
    detay = satir ? (satir.parametre_detay || null) : null;
  }
  return { kod: cevap.status, hata: govde.hata || null, birimKurus, detay };
}

// ---------------------------------------------------------------- minimal DOM taklidi
// (jenerator/test/vitrin-kabul.js + shop/test/sepet-panel.js deseninin konfiguratore
//  uyarlanmis, kucultulmus hali — gercek konfigurator.js kodu kosar, kopya hesap YOK.)

function eleman(tag) {
  const el = {
    tagName: String(tag || "div").toUpperCase(),
    children: [], parentNode: null, attrs: {},
    id: "", className: "", textContent: "", value: "", type: "", tabIndex: 0,
    style: {}, dataset: {},
  };
  el.classList = {
    add(c) { if (!this.contains(c)) { el.className = (el.className + " " + c).trim(); } },
    remove(c) { el.className = el.className.split(/\s+/).filter((x) => x !== c).join(" "); },
    contains(c) { return el.className.split(/\s+/).indexOf(c) !== -1; },
    toggle(c, zorla) {
      const v = (zorla === undefined) ? !this.contains(c) : !!zorla;
      if (v) { this.add(c); } else { this.remove(c); }
    },
  };
  el.appendChild = (c) => { el.children.push(c); c.parentNode = el; return c; };
  el.setAttribute = (k, v) => { el.attrs[k] = String(v); };
  el.getAttribute = (k) => (k in el.attrs ? el.attrs[k] : null);
  el.addEventListener = () => {};
  return el;
}

function belgeKur() {
  const kimlikler = new Map();
  return {
    createElement: (tag) => eleman(tag),
    getElementById(id) {
      if (!kimlikler.has(id)) { const e = eleman("div"); e.id = id; kimlikler.set(id, e); }
      return kimlikler.get(id);
    },
  };
}

/** Agactaki id'li elemanlari haritalar (konfigurator "konf_<ad>" id'si verir). */
function idHarita(kok, harita) {
  harita = harita || new Map();
  if (kok.id) { harita.set(kok.id, kok); }
  for (const c of kok.children) { idHarita(c, harita); }
  return harita;
}

/** Bir aynanin ON YUZ dunyasini (secenekler + hacim + konfigurator) kurar. */
function frontKur(ayna) {
  const ctx = { console: { log() {}, error() {}, warn() {} } };
  ctx.self = ctx; ctx.window = ctx;
  ctx.document = belgeKur();
  vm.createContext(ctx);
  const kos = (rel) => vm.runInContext(fs.readFileSync(path.join(ayna, rel), "utf8"), ctx,
                                       { filename: rel });
  kos("secenekler.js");
  kos("jenerator/hacim.js");
  kos("jenerator/konfigurator.js");
  if (!ctx.PRUVO_KONF || !ctx.PRUVO_SECENEK) { throw new Error("front yuklenemedi: " + ayna); }
  return ctx;
}

/** GERCEK konfigurator.satiraYaz ile sepet satirini uretir (front fiyati). */
function frontSatir(ctx, sema, degerler, secim) {
  const kok = ctx.document.createElement("div");
  ctx.PRUVO_KONF.kur(sema, kok, function () {});
  const harita = idHarita(kok);
  for (const ad of Object.keys(degerler)) {
    const el = harita.get("konf_" + ad);
    if (!el) { throw new Error("alan yok: " + ad); }
    el.value = String(degerler[ad]);
  }
  if (secim.yazi_renk && harita.has("konf_yazi_renk")) {
    harita.get("konf_yazi_renk").value = secim.yazi_renk;
  }
  const satir = ctx.PRUVO_SECENEK.bosSatir(sema.id);
  satir.malzeme = secim.malzeme;
  satir.renk = secim.renk;
  satir.adet = 1;
  return ctx.PRUVO_KONF.satiraYaz(satir);
}

// ---------------------------------------------------------------- veri / senaryolar

const SEMALAR = {};
for (const dosya of fs.readdirSync(URUN_SEMA_DIZIN).filter((f) => f.endsWith(".json"))) {
  const s = JSON.parse(fs.readFileSync(path.join(URUN_SEMA_DIZIN, dosya), "utf8"));
  SEMALAR[s.id] = s;
}
const CERCEVE_SEMA = SEMALAR[CERCEVE];
if (!CERCEVE_SEMA) { throw new Error("cerceve semasi bulunamadi"); }

/** D1 katalog satiri (d1-sync.py'nin yazdigi alanlar) — parametrik urun. */
function d1Satiri(id) {
  return { id, baslik: "Test " + id, kategori: "Jeneratör", fiyat: "", parametrik: 1,
           gorsel: "" };
}

const NORMAL = { acilik_eni: 100, acilik_boyu: 150, kenar_genisligi: 12, derinlik: 5.2,
                 kenar_stili: "chamfer" };
const BUYUK = { acilik_eni: 250, acilik_boyu: 300, kenar_genisligi: 30, derinlik: 15,
                kenar_stili: "flat" };
const DAR = { acilik_eni: 100, acilik_boyu: 150, kenar_genisligi: 9, derinlik: 5.2,
              kenar_stili: "chamfer" };

const SENARYOLAR = [
  { ad: "a) 2-RENK yazi (yazi=OKAN, yazi_renk=Beyaz != renk=Siyah)",
    kod: "a", parametreler: Object.assign({}, NORMAL, { yazi: "OKAN" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: "Beyaz", ikiRenk: true },
  { ad: "b) yazisiz (yazi='')",
    kod: "b", parametreler: Object.assign({}, NORMAL, { yazi: "" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: null, ikiRenk: false },
  { ad: "c) yazi var ama yazi_renk == renk (Siyah/Siyah)",
    kod: "c", parametreler: Object.assign({}, NORMAL, { yazi: "OKAN" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: "Siyah", ikiRenk: false },
  { ad: "d1) 3x TAVAN + 2-renk (buyuk cerceve, PLA/Siyah)",
    kod: "d", parametreler: Object.assign({}, BUYUK, { yazi: "OKAN" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: "Beyaz", ikiRenk: true },
  { ad: "d2) 3x TAVAN tek renk (buyuk cerceve, PLA/Siyah)",
    kod: "d", parametreler: Object.assign({}, BUYUK, { yazi: "" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: null, ikiRenk: false },
  { ad: "d3) 3x TAVAN + 2-renk, ASA/Diger (tavan malzeme+renk DAHIL)",
    kod: "d", parametreler: Object.assign({}, BUYUK, { yazi: "OKAN" }),
    malzeme: "ASA", renk: "Diğer", renk_ozel: "mor", yazi_renk: "Beyaz", ikiRenk: true },
];

const RED_SENARYO = { ad: "e) 2-renk DAR kenar (9 mm < 10 mm) -> RED",
                      parametreler: Object.assign({}, DAR, { yazi: "OKAN" }),
                      malzeme: "PLA", renk: "Siyah", yazi_renk: "Beyaz" };

function kalemYap(s) {
  const k = { id: CERCEVE, malzeme: s.malzeme, renk: s.renk, adet: 1,
              parametreler: s.parametreler };
  if (s.renk_ozel) { k.renk_ozel = s.renk_ozel; }
  if (s.yazi_renk) { k.yazi_renk = s.yazi_renk; }
  return k;
}

// ---------------------------------------------------------------- kosum

const ham = [];
const hatalar = [];
const not = (s) => ham.push(s);

not("Node: " + process.version + " (CI tabani: 20.x — daha yeni API KULLANMA)");
let kapsam = "";
try {
  kapsam = execFileSync("git", ["-C", KOK, "diff", "--name-only", "HEAD"],
                        { encoding: "utf8" }).trim();
} catch (e) { kapsam = "(git diff okunamadi)"; }
not("Calisma agaci farki (HEAD'e gore): " + (kapsam ? kapsam.split("\n").join(", ") : "(yok)"));
not("");

const ESKI_AYNA = aynaKur("eski", headden);
const YENI_AYNA = aynaKur("yeni", diskten);
const MUTANT_AYNA = aynaKur("mutant", diskten, (kaynak, rel) =>
  (rel === "secenekler.js"
    ? kaynak.replace("var IKI_RENK_EK_KURUS = 0;", "var IKI_RENK_EK_KURUS = " + ESKI_EK_KURUS + ";")
    : kaynak));

// Mutasyonun GERCEKTEN uygulandigini dogrula (sessiz no-op mutant = sahte VAKUM kaniti).
const mutantMetin = fs.readFileSync(path.join(MUTANT_AYNA, "secenekler.js"), "utf8");
if (!/var IKI_RENK_EK_KURUS = 7500;/.test(mutantMetin)) {
  hatalar.push("VAKUM mutanti uygulanamadi (secenekler.js deseni degismis) — test OLU olurdu");
}

const eskiMod = await import(pathToFileURL(path.join(ESKI_AYNA, "shop/src/index.js")).href);
const yeniMod = await import(pathToFileURL(path.join(YENI_AYNA, "shop/src/index.js")).href);
const mutantMod = await import(pathToFileURL(path.join(MUTANT_AYNA, "shop/src/index.js")).href);

const eskiFront = frontKur(ESKI_AYNA);
const yeniFront = frontKur(YENI_AYNA);

// ---- SET 1 + 2: para kaniti + parite
not("== SET 1) PARA KANITI (Worker /baslat -> D1'e yazilan birim_kurus) + SET 2) PARITE ==");
not("  senaryo                                              | ESKI worker | YENI worker |  fark | YENI front | parite");
const kat = SEMALAR[CERCEVE];
for (const s of SENARYOLAR) {
  const kalem = kalemYap(s);
  const eski = await baslat(eskiMod, [d1Satiri(CERCEVE)], kalem);
  const yeni = await baslat(yeniMod, [d1Satiri(CERCEVE)], kalem);
  const front = frontSatir(yeniFront, kat, s.parametreler,
                           { malzeme: s.malzeme, renk: s.renk, yazi_renk: s.yazi_renk });
  const frontKurus = front.parametrik_fiyat_kurus;
  const fark = (eski.birimKurus == null || yeni.birimKurus == null)
    ? null : yeni.birimKurus - eski.birimKurus;
  const pariteOk = frontKurus === yeni.birimKurus;
  not("  " + s.ad.padEnd(52) + " | " + String(eski.birimKurus).padStart(11) + " | " +
      String(yeni.birimKurus).padStart(11) + " | " + String(fark).padStart(5) + " | " +
      String(frontKurus).padStart(10) + " | " + (pariteOk ? "ESIT" : "AYRIK"));

  if (eski.kod !== 200 || yeni.kod !== 200) {
    hatalar.push("(1" + s.kod + ") 200 bekleniyordu: eski=" + eski.kod + "/" + eski.hata +
                 " yeni=" + yeni.kod + "/" + yeni.hata + " [" + s.ad + "]");
    continue;
  }
  const beklenenFark = s.ikiRenk ? -ESKI_EK_KURUS : 0;
  if (fark !== beklenenFark) {
    hatalar.push("(1" + s.kod + ") fark " + fark + ", beklenen " + beklenenFark + " [" + s.ad + "]");
  }
  if (!pariteOk) {
    hatalar.push("(2) PARITE KIRIK: front " + frontKurus + " != worker " + yeni.birimKurus +
                 " [" + s.ad + "]");
  }
  // ESKI tarafta da parite vardi (kaymayi biz yaratmadik) — bilgi + capa.
  const eskiFrontKurus = frontSatir(eskiFront, kat, s.parametreler,
    { malzeme: s.malzeme, renk: s.renk, yazi_renk: s.yazi_renk }).parametrik_fiyat_kurus;
  if (eskiFrontKurus !== eski.birimKurus) {
    hatalar.push("(2) ESKI tarafta parite zaten kirikmis: front " + eskiFrontKurus +
                 " != worker " + eski.birimKurus + " [" + s.ad + "]");
  }
  // 2-renk kaleminde satir detayi ucret YALANI soylememeli.
  if (s.ikiRenk) {
    if (!/2 renk/.test(yeni.detay || "")) {
      hatalar.push("(1" + s.kod + ") 2-renk detayi kayboldu: " + yeni.detay);
    }
    if (/\+75 TL/.test(yeni.detay || "")) {
      hatalar.push("(1" + s.kod + ") detay hala '+75 TL' diyor: " + yeni.detay);
    }
    if (front.parametre_detay !== yeni.detay) {
      hatalar.push("(2) detay metni ayristi: front '" + front.parametre_detay +
                   "' != worker '" + yeni.detay + "'");
    }
  }
}

// 3x TAVAN degerinin GERCEKTEN tavan oldugunu kanitla (yoksa (d) bos yere yesil yanar).
const tavanKurus = Math.round(CERCEVE_SEMA.tabanFiyatTL * 100 * 3);
const dTek = await baslat(yeniMod, [d1Satiri(CERCEVE)],
  kalemYap(SENARYOLAR.find((x) => x.ad.startsWith("d2"))));
not("  3x tavan kontrolu: taban " + CERCEVE_SEMA.tabanFiyatTL + " TL -> tavan " + tavanKurus +
    " kurus; d2 olculen " + dTek.birimKurus + (dTek.birimKurus === tavanKurus ? " (TAVANDA)" : " (TAVANDA DEGIL)"));
if (dTek.birimKurus !== tavanKurus) {
  hatalar.push("(1d) buyuk cerceve tavana carpmiyor (" + dTek.birimKurus + " != " + tavanKurus +
               ") — tavan iddiasi bos olurdu");
}

// (e) dar kenar reddi degismedi mi
const eskiRed = await baslat(eskiMod, [d1Satiri(CERCEVE)], kalemYap(RED_SENARYO));
const yeniRed = await baslat(yeniMod, [d1Satiri(CERCEVE)], kalemYap(RED_SENARYO));
not("  " + RED_SENARYO.ad.padEnd(52) + " | eski " + eskiRed.kod + "/" + eskiRed.hata +
    " | yeni " + yeniRed.kod + "/" + yeniRed.hata);
if (eskiRed.kod !== 400 || eskiRed.hata !== "iki-renk-kenar-dar" ||
    yeniRed.kod !== yeniRed.kod || yeniRed.kod !== 400 || yeniRed.hata !== "iki-renk-kenar-dar") {
  hatalar.push("(1e) dar kenar reddi degisti: eski " + eskiRed.kod + "/" + eskiRed.hata +
               " yeni " + yeniRed.kod + "/" + yeniRed.hata);
}
not("");

// ---- SET 3: regresyon (tum parametrik aileler, 2-renk YOK)
not("== SET 3) REGRESYON — 23 parametrik ailenin varsayilan olcusu (2-renk YOK) ==");
const aileler = Object.keys(SEMALAR).sort();
let regOk = 0, regFark = 0;
const regSatir = [];
for (const id of aileler) {
  const sema = SEMALAR[id];
  const degerler = yeniFront.PRUVO_KONF.varsayilanDegerler(sema);
  const kalem = { id, malzeme: "PETG", renk: "Siyah", adet: 1, parametreler: degerler };
  const eski = await baslat(eskiMod, [d1Satiri(id)], kalem);
  const yeni = await baslat(yeniMod, [d1Satiri(id)], kalem);
  if (eski.kod === yeni.kod && eski.birimKurus === yeni.birimKurus) {
    regOk += 1;
  } else {
    regFark += 1;
    hatalar.push("(3) " + id + ": eski " + eski.kod + "/" + eski.birimKurus +
                 " -> yeni " + yeni.kod + "/" + yeni.birimKurus);
  }
  regSatir.push(id + "=" + yeni.birimKurus);
}
not("  " + regOk + "/" + aileler.length + " aile BIREBIR ayni (fark: " + regFark + ")");
not("  fiyatlar (PETG/Siyah, varsayilan olcu, kurus): " + regSatir.join(" · "));

// 13 KONFIGURLU (dekor konfiguratoru) urun — 2-renk yolu bu kolda HIC yok; degismedigi
// SAYIYLA gosterilir (mimar kabul maddesi 3).
const { KONFIGURLAR } = await import(
  pathToFileURL(path.join(YENI_AYNA, "shop/src/konfigurlar.js")).href);
const konfigurIdler = [...KONFIGURLAR.keys()].sort();
const konfigurDenemeler = [[150, "PLA"], [300, "ASA"], [60, "PLA"]];
let kOk = 0, kFark = 0;
const kSatir = [];
for (const id of konfigurIdler) {
  const fiyatlar = [];
  for (const [boy, malzeme] of konfigurDenemeler) {
    const d1 = { id, baslik: "Test " + id, kategori: "Skan Art", fiyat: "500 TL",
                 parametrik: 0, gorsel: "" };
    const kalem = { id, malzeme, renk: "Siyah", adet: 1, parametreler: { boy_mm: boy } };
    const eski = await baslat(eskiMod, [d1], kalem);
    const yeni = await baslat(yeniMod, [d1], kalem);
    if (eski.kod === yeni.kod && eski.birimKurus === yeni.birimKurus && yeni.kod === 200) {
      kOk += 1;
    } else {
      kFark += 1;
      hatalar.push("(3-konfigur) " + id + " " + boy + "mm/" + malzeme + ": eski " + eski.kod +
                   "/" + eski.birimKurus + " -> yeni " + yeni.kod + "/" + yeni.birimKurus);
    }
    fiyatlar.push(yeni.birimKurus);
  }
  kSatir.push(id.replace("-serit-dekoratif-figur", "") + "=" + fiyatlar.join("/"));
}
not("  " + kOk + "/" + (konfigurIdler.length * konfigurDenemeler.length) +
    " konfigur kalemi (" + konfigurIdler.length + " urun x 150/PLA,300/ASA,60/PLA) BIREBIR ayni (fark: " +
    kFark + ")");
not("  konfigur fiyatlari (150PLA/300ASA/60PLA, kurus): " + kSatir.join(" · "));
not("");

// ---- SET 4: VAKUM (degisikligi geri al -> (1a) KIRMIZI yanmali)
not("== SET 4) VAKUM — IKI_RENK_EK_KURUS 7500'e geri alinirsa ==");
const aKalem = kalemYap(SENARYOLAR[0]);
const mutantSonuc = await baslat(mutantMod, [d1Satiri(CERCEVE)], aKalem);
const eskiA = await baslat(eskiMod, [d1Satiri(CERCEVE)], aKalem);
const yeniA = await baslat(yeniMod, [d1Satiri(CERCEVE)], aKalem);
const vakumFark = mutantSonuc.birimKurus - eskiA.birimKurus;
not("  mutant birim=" + mutantSonuc.birimKurus + " · eski birim=" + eskiA.birimKurus +
    " · yeni birim=" + yeniA.birimKurus);
not("  mutant-eski farki=" + vakumFark + " (0 olmali: geri alinca ESKI fiyata doner)");
const vakumIddiaKirmizi = (mutantSonuc.birimKurus - eskiA.birimKurus) !== -ESKI_EK_KURUS;
not("  (1a) iddiasi mutantta " + (vakumIddiaKirmizi ? "KIRMIZI yanar ✅ (nobetci CANLI)"
                                                    : "YESIL kalir ❌ (nobetci OLU)"));
if (vakumFark !== 0) {
  hatalar.push("(4) mutant ESKI fiyata donmedi (fark " + vakumFark + ") — vakum kaniti gecersiz");
}
if (!vakumIddiaKirmizi) {
  hatalar.push("(4) OLU NOBETCI: degisiklik geri alindiginda (1a) iddiasi yine de yesil kaliyor");
}
if (!/\+75 TL/.test(mutantSonuc.detay || "")) {
  hatalar.push("(4) mutant detayinda '+75 TL' yok — metin sabitten turemiyor olabilir: " +
               mutantSonuc.detay);
}
not("  mutant detay metni: " + mutantSonuc.detay);
not("  yeni  detay metni: " + yeniA.detay);
not("");

// ---- SET 5: tek kaynak (ikinci sabit kalmadi mi)
not("== SET 5) TEK KAYNAK — front/Worker kaynaginda ikinci 7500 sabiti ==");
const tekKaynakDosya = ["jenerator/konfigurator.js", "shop/src/parametrik.js"];
for (const rel of tekKaynakDosya) {
  const metin = diskten(rel);
  const kacak = metin.split("\n")
    .map((satir, i) => ({ satir, no: i + 1 }))
    .filter((x) => /7500/.test(x.satir) && !/^\s*(\/\/|\*|\/\*)/.test(x.satir));
  not("  " + rel + ": kod satirinda '7500' gecisi = " + kacak.length);
  for (const k of kacak) { hatalar.push("(5) " + rel + ":" + k.no + " ikinci sabit: " + k.satir.trim()); }
}
const sec = diskten("secenekler.js");
const tekTanim = (sec.match(/var IKI_RENK_EK_KURUS\s*=/g) || []).length;
not("  secenekler.js: IKI_RENK_EK_KURUS tanimi = " + tekTanim + " (1 olmali)");
if (tekTanim !== 1) { hatalar.push("(5) secenekler.js'te IKI_RENK_EK_KURUS tanimi " + tekTanim); }
not("");

// ---------------------------------------------------------------- rapor
console.log(ham.join("\n"));
if (hatalar.length) {
  console.log("❌ KALDI — " + hatalar.length + " iddia:");
  hatalar.forEach((h) => console.log("   ❌ " + h));
  process.exit(1);
}
console.log("✅ GECTI — 5 setin hepsi yesil (para kaniti + parite + regresyon + vakum + tek kaynak)");
