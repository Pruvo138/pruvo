#!/usr/bin/env node
/**
 * 2-RENK YAZI EK UCRETI KABUL TESTI — "karsiligi olmayan +75 TL tahsil edilmiyor" kapisi.
 *
 *   node shop/test/iki-renk-ucret.mjs
 *
 * NEDEN VAR (para duzlemi, 2026-07-29): cerceve ailesinde yazi rengi cerceve renginden farkli
 * secilince fiyata +7500 kurus ekleniyordu (gerekce: ayri govde / 2. filaman). OLCUM bunu
 * curuttu: derleyiciye AYNI geometriyle yazi='' / 'OKAN' / 'WWWWWWWWWWWW' gonderildi, ucunun
 * ciktisi da 65284 bayt / 1304 ucgen / SHA-256 BIREBIR AYNI (ucu de taze derleme). Yazi
 * uretilen govdeye HIC girmiyor -> ek maliyet yok -> ucretin karsiligi yok. Ucret
 * secenekler.js IKI_RENK_EK_KURUS tek kaynagindan 0'a cekildi.
 *
 * NASIL (OFFLINE — wrangler/ag/gercek odeme YOK; shop/test/konfigur-fail-closed.mjs deseni):
 * shop/src/index.js'in KENDISI Node'a yuklenir, D1 ve iyzico yerine bellek-ici sahteleri
 * konur. Fiyat, Worker'in D1'e YAZDIGI siparis satirindan okunur — yani GERCEK para yolundan.
 * Hicbir dis servise istek gitmez, hicbir siparis olusmaz, hicbir kalici dosya degismez.
 *
 * ⚠️ TABAN SECIMI (bilerek git-GECMISI DEGIL): iddialar "git HEAD ile karsilastir" uzerine
 * kurulsaydi bu dal main'e girdigi anda HEAD == calisan kod olur, karsilastirma TOTOLOJIYE
 * doner ve nobetci SESSIZCE olurdu. Bu yuzden taban, AYNI calisma agacinin iki VARYANTIDIR:
 *   UCRETSIZ = kaynak oldugu gibi (IKI_RENK_EK_KURUS = 0)
 *   UCRETLI  = yalniz o sabit 7500 yapilmis hali (= degisiklik geri alinmis hali)
 * Ikisi de gecici bir kaynak aynasina yazilip ayni kosumda yan yana yuklenir. Boylece iddia
 * "bugun ucret alinmiyor + geri alinirsa 7500 alinirdi" seklinde KALICI olarak olculur.
 * (Tarihsel git HEAD karsilastirmasi en altta, YALNIZ BILGI olarak, HEAD hala ucretliyken.)
 *
 * AYNA (mirror) DUZENI: her varyant icin gecici dizine kendi kaynak agaci yazilir —
 * <tmp>/secenekler.js, <tmp>/konfigur.js, <tmp>/jenerator/{konfigurator,hacim}.js,
 * <tmp>/shop/src/*.js — boylece goreli import'lar (../../secenekler.js) O VARYANTIN
 * dosyalarina cozulur. JSON import'lari (Node surum farki yaratan import nitelikleri)
 * icerige gomulur; package.json YAZILMAZ (gercek repoda da yok — .js dosyalari Node'un
 * sozdizimi tespitiyle ESM/CJS ayrilir, konfigurator.js CJS kalir).
 *
 * KOSTUGU 5 SET (hepsi bloklayici):
 *   (1) PARA KANITI  — (a) 2-renk kalemin fiyati AYNI geometrinin tek-renk fiyatiyla ESIT
 *       (yani ek ucret 0) ve UCRETLI varyantta tam 7500 fazla; (b) yazisiz kalem bagimsiz
 *       fiyat orakiliyla birebir; (c) yazi var ama yazi_renk == renk -> yazisizla ayni;
 *       (d) 3x tavan davranisi korunuyor (2-renk artik tavani ASMIYOR, UCRETLI'de asiyordu);
 *       (e) dar kenar (kenar<10mm) 2-renk REDDI iki varyantta da AYNI (urun satista kalir).
 *   (2) PARITE      — ayni senaryolarda ON YUZ (jenerator/konfigurator.js, sahte DOM ile
 *       GERCEK satiraYaz) ile WORKER kurusu kurusuna esit; 2-renk detay metni de birebir.
 *       Esit degilse suite KIRMIZI (gosterilen != tahsil edilen olurdu).
 *   (3) REGRESYON   — 23 parametrik ailenin varsayilan olcusunde Worker fiyati BAGIMSIZ
 *       orakille (secenekler.js parametrikFiyatKurus + hacim.js) birebir; 13 konfigur
 *       urununun 39 kaleminde UCRETSIZ == UCRETLI (2-renk kolu o urunlere DOKUNMUYOR).
 *   (4) VAKUM       — "2-renk fiyati tek-renk fiyatina esit" iddiasi UCRETLI varyantta
 *       KIRMIZI yanmali; yanmiyorsa bu test OLU nobetcidir -> suite KIRMIZI.
 *   (5) TEK KAYNAK  — ne front ne Worker kaynaginda ikinci bir 7500 sabiti kalmamis olmali.
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

const EK_KURUS = 7500;               // kaldirilan ucret (UCRETLI varyantin degeri)
const CERCEVE = "olcuye-ozel-cerceve";
const SABIT_KAPALI = "var IKI_RENK_EK_KURUS = 0;";
const SABIT_ACIK = "var IKI_RENK_EK_KURUS = " + EK_KURUS + ";";

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
 * Bir varyantin kaynak aynasini kurar.
 * @param {string} ad   ayna dizini
 * @param {(rel:string)=>string} oku  kaynak okuyucu (diskten / headden)
 * @param {(kaynak:string,rel:string)=>string} [yama]  istege bagli sabit degisimi
 */
function aynaKur(ad, oku, yama) {
  const taban = path.join(GECICI_KOK, ad);
  fs.mkdirSync(path.join(taban, "jenerator"), { recursive: true });
  fs.mkdirSync(path.join(taban, "shop", "src"), { recursive: true });
  const yaz = (rel, ham) => fs.writeFileSync(path.join(taban, rel),
                                             yama ? yama(ham, rel) : ham);
  for (const rel of KOK_DOSYALAR) { yaz(rel, oku(rel)); }
  for (const dosya of SRC_DOSYALAR) {
    yaz("shop/src/" + dosya, jsonGom(oku("shop/src/" + dosya), ad + ":" + dosya));
  }
  return taban;
}

/** UCRETLI varyant yamasi: tek kaynaktaki sabiti 7500 yapar (= degisikligi geri alir). */
function ucretiAc(kaynak, rel) {
  return (rel === "secenekler.js") ? kaynak.replace(SABIT_KAPALI, SABIT_ACIK) : kaynak;
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
//  uyarlanmis, kucultulmus hali — GERCEK konfigurator.js kodu kosar, kopya hesap YOK.)

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

/** BAGIMSIZ fiyat orakili: secenekler.js formulu + hacim.js (2-renk kolundan TAMAMEN ayri). */
function orakil(ctx, sema, degerler, malzeme, renk) {
  const h = ctx.PRUVO_KONF.hacimMm3(sema, degerler, ctx.PRUVO_HACIM);
  if (h == null) { return null; }
  return ctx.PRUVO_SECENEK.parametrikFiyatKurus(
    sema.tabanFiyatTL, sema.tabanHacimMm3, h, malzeme, renk);
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
  return { id, baslik: "Test " + id, kategori: "Jeneratör", fiyat: "", parametrik: 1, gorsel: "" };
}

const NORMAL = { acilik_eni: 100, acilik_boyu: 150, kenar_genisligi: 12, derinlik: 5.2,
                 kenar_stili: "chamfer" };
const BUYUK = { acilik_eni: 250, acilik_boyu: 300, kenar_genisligi: 30, derinlik: 15,
                kenar_stili: "flat" };
const DAR = { acilik_eni: 100, acilik_boyu: 150, kenar_genisligi: 9, derinlik: 5.2,
              kenar_stili: "chamfer" };

// Her senaryonun "esi" (es), 2-renk kolunun DISINDAKI her seyi ayni tutan tek-renk kalemdir:
// ucretin sifir oldugu iddiasi = "2-renk fiyati esinin fiyatina ESIT".
const SENARYOLAR = [
  { ad: "a) 2-RENK yazi (yazi=OKAN, yazi_renk=Beyaz != renk=Siyah)",
    parametreler: Object.assign({}, NORMAL, { yazi: "OKAN" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: "Beyaz", ikiRenk: true },
  { ad: "b) yazisiz (yazi='')",
    parametreler: Object.assign({}, NORMAL, { yazi: "" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: null, ikiRenk: false },
  { ad: "c) yazi var ama yazi_renk == renk (Siyah/Siyah)",
    parametreler: Object.assign({}, NORMAL, { yazi: "OKAN" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: "Siyah", ikiRenk: false },
  { ad: "d1) 3x TAVAN + 2-renk (buyuk cerceve, PLA/Siyah)",
    parametreler: Object.assign({}, BUYUK, { yazi: "OKAN" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: "Beyaz", ikiRenk: true },
  { ad: "d2) 3x TAVAN tek renk (buyuk cerceve, PLA/Siyah)",
    parametreler: Object.assign({}, BUYUK, { yazi: "" }),
    malzeme: "PLA", renk: "Siyah", yazi_renk: null, ikiRenk: false },
  { ad: "d3) 3x TAVAN + 2-renk, ASA/Diger (tavan malzeme+renk DAHIL)",
    parametreler: Object.assign({}, BUYUK, { yazi: "OKAN" }),
    malzeme: "ASA", renk: "Diğer", renk_ozel: "mor", yazi_renk: "Beyaz", ikiRenk: true },
];

const RED_SENARYO = { ad: "e) 2-renk DAR kenar (9 mm < 10 mm) -> RED",
                      parametreler: Object.assign({}, DAR, { yazi: "OKAN" }),
                      malzeme: "PLA", renk: "Siyah", yazi_renk: "Beyaz" };

function kalemYap(s, yaziRenkiDusur) {
  const k = { id: CERCEVE, malzeme: s.malzeme, renk: s.renk, adet: 1,
              parametreler: s.parametreler };
  if (s.renk_ozel) { k.renk_ozel = s.renk_ozel; }
  if (s.yazi_renk && !yaziRenkiDusur) { k.yazi_renk = s.yazi_renk; }
  return k;
}

// ---------------------------------------------------------------- kurulum

const ham = [];
const hatalar = [];
const not = (s) => ham.push(s);

not("Node: " + process.version + " (CI tabani: 20.x — daha yeni API KULLANMA)");
not("Taban: git gecmisi DEGIL — ayni calisma agacinin iki varyanti (UCRETSIZ=0 / UCRETLI=7500).");
not("");

const KAYNAK_SEC = diskten("secenekler.js");
if (!KAYNAK_SEC.includes(SABIT_KAPALI)) {
  hatalar.push("KURULUM: secenekler.js'te '" + SABIT_KAPALI + "' bulunamadi — ucret geri " +
               "acilmis ya da sabit adi degismis olabilir (test bunu SESSIZ gecemez)");
}

const UCRETSIZ_AYNA = aynaKur("ucretsiz", diskten);
const UCRETLI_AYNA = aynaKur("ucretli", diskten, ucretiAc);

// UCRETLI varyantin GERCEKTEN yamandigini dogrula (no-op mutant = sahte vakum kaniti).
if (!fs.readFileSync(path.join(UCRETLI_AYNA, "secenekler.js"), "utf8").includes(SABIT_ACIK)) {
  hatalar.push("KURULUM: UCRETLI varyant yamasi uygulanamadi — (4) VAKUM kaniti gecersiz olurdu");
}

const ucretsizMod = await import(
  pathToFileURL(path.join(UCRETSIZ_AYNA, "shop/src/index.js")).href);
const ucretliMod = await import(
  pathToFileURL(path.join(UCRETLI_AYNA, "shop/src/index.js")).href);
const front = frontKur(UCRETSIZ_AYNA);

// ---------------------------------------------------------------- SET 1 + 2
not("== SET 1) PARA KANITI (Worker /baslat -> D1'e yazilan birim_kurus) + SET 2) PARITE ==");
not("  senaryo                                                   |  UCRETSIZ |   UCRETLI |  fark | tek-renk esi | front | parite");
for (const s of SENARYOLAR) {
  const kalem = kalemYap(s);
  const ucretsiz = await baslat(ucretsizMod, [d1Satiri(CERCEVE)], kalem);
  const ucretli = await baslat(ucretliMod, [d1Satiri(CERCEVE)], kalem);
  // "Esi": ayni kalem ama 2. renk YOK -> 2-renk kolunun disindaki her sey birebir ayni.
  const es = await baslat(ucretsizMod, [d1Satiri(CERCEVE)], kalemYap(s, true));
  const f = frontSatir(front, CERCEVE_SEMA, s.parametreler,
                       { malzeme: s.malzeme, renk: s.renk, yazi_renk: s.yazi_renk });
  const frontKurus = f.parametrik_fiyat_kurus;
  const fark = (ucretsiz.birimKurus == null || ucretli.birimKurus == null)
    ? null : ucretli.birimKurus - ucretsiz.birimKurus;
  const pariteOk = frontKurus === ucretsiz.birimKurus;
  not("  " + s.ad.padEnd(57) + " | " + String(ucretsiz.birimKurus).padStart(9) + " | " +
      String(ucretli.birimKurus).padStart(9) + " | " + String(fark).padStart(5) + " | " +
      String(es.birimKurus).padStart(12) + " | " + String(frontKurus).padStart(5) + " | " +
      (pariteOk ? "ESIT" : "AYRIK"));

  if (ucretsiz.kod !== 200 || ucretli.kod !== 200 || es.kod !== 200) {
    hatalar.push("(1) 200 bekleniyordu: ucretsiz=" + ucretsiz.kod + "/" + ucretsiz.hata +
                 " ucretli=" + ucretli.kod + " es=" + es.kod + " [" + s.ad + "]");
    continue;
  }
  // ASIL IDDIA: 2-renk kalemin fiyati, tek-renk esinin fiyatiyla BIREBIR ayni (ucret 0).
  if (ucretsiz.birimKurus !== es.birimKurus) {
    hatalar.push("(1) 2-renk kalemi hala ek ucret aliyor: " + ucretsiz.birimKurus +
                 " != tek-renk esi " + es.birimKurus + " [" + s.ad + "]");
  }
  // KALDIRILAN TUTAR: UCRETLI varyantta 2-renk kalemi tam 7500 fazla olmali (yoksa iddia bos).
  const beklenenFark = s.ikiRenk ? EK_KURUS : 0;
  if (fark !== beklenenFark) {
    hatalar.push("(1) UCRETLI-UCRETSIZ farki " + fark + ", beklenen " + beklenenFark +
                 " [" + s.ad + "]");
  }
  if (!pariteOk) {
    hatalar.push("(2) PARITE KIRIK: front " + frontKurus + " != worker " + ucretsiz.birimKurus +
                 " [" + s.ad + "]");
  }
  if (s.ikiRenk) {
    if (!/2 renk/.test(ucretsiz.detay || "")) {
      hatalar.push("(1) 2-renk detayi kayboldu: " + ucretsiz.detay);
    }
    if (/\+75 TL/.test(ucretsiz.detay || "")) {
      hatalar.push("(1) detay hala '+75 TL' diyor: " + ucretsiz.detay);
    }
    if (f.parametre_detay !== ucretsiz.detay) {
      hatalar.push("(2) detay metni ayristi: front '" + f.parametre_detay +
                   "' != worker '" + ucretsiz.detay + "'");
    }
  }
}

// 3x TAVAN degerinin GERCEKTEN tavan oldugunu kanitla (yoksa (d) bos yere yesil yanar).
const tavanKurus = Math.round(CERCEVE_SEMA.tabanFiyatTL * 100 * 3);
const dTek = await baslat(ucretsizMod, [d1Satiri(CERCEVE)],
  kalemYap(SENARYOLAR.find((x) => x.ad.startsWith("d2"))));
const dCift = await baslat(ucretsizMod, [d1Satiri(CERCEVE)],
  kalemYap(SENARYOLAR.find((x) => x.ad.startsWith("d1"))));
const dCiftUcretli = await baslat(ucretliMod, [d1Satiri(CERCEVE)],
  kalemYap(SENARYOLAR.find((x) => x.ad.startsWith("d1"))));
not("  3x tavan: taban " + CERCEVE_SEMA.tabanFiyatTL + " TL -> tavan " + tavanKurus +
    " kurus; tek-renk " + dTek.birimKurus + (dTek.birimKurus === tavanKurus ? " (TAVANDA)" : " (TAVANDA DEGIL)") +
    "; 2-renk " + dCift.birimKurus + " (UCRETLI'de " + dCiftUcretli.birimKurus + " = tavan ASILIYORDU)");
if (dTek.birimKurus !== tavanKurus) {
  hatalar.push("(1d) buyuk cerceve tavana carpmiyor (" + dTek.birimKurus + " != " + tavanKurus +
               ") — tavan iddiasi bos olurdu");
}
if (dCift.birimKurus !== tavanKurus) {
  hatalar.push("(1d) 2-renk kalem tavani asiyor: " + dCift.birimKurus + " != " + tavanKurus);
}
if (dCiftUcretli.birimKurus !== tavanKurus + EK_KURUS) {
  hatalar.push("(1d) UCRETLI varyantta tavan-disi ek beklenmiyordu: " + dCiftUcretli.birimKurus);
}

// (e) dar kenar reddi iki varyantta da AYNI (urun satista, kapi yerinde)
const redUcretsiz = await baslat(ucretsizMod, [d1Satiri(CERCEVE)], kalemYap(RED_SENARYO));
const redUcretli = await baslat(ucretliMod, [d1Satiri(CERCEVE)], kalemYap(RED_SENARYO));
not("  " + RED_SENARYO.ad.padEnd(57) + " | ucretsiz " + redUcretsiz.kod + "/" + redUcretsiz.hata +
    " | ucretli " + redUcretli.kod + "/" + redUcretli.hata);
if (redUcretsiz.kod !== 400 || redUcretsiz.hata !== "iki-renk-kenar-dar" ||
    redUcretli.kod !== 400 || redUcretli.hata !== "iki-renk-kenar-dar") {
  hatalar.push("(1e) dar kenar reddi degisti: ucretsiz " + redUcretsiz.kod + "/" +
               redUcretsiz.hata + " ucretli " + redUcretli.kod + "/" + redUcretli.hata);
}
not("");

// ---------------------------------------------------------------- SET 3
not("== SET 3) REGRESYON ==");
const aileler = Object.keys(SEMALAR).sort();
let regOk = 0;
const regSatir = [];
for (const id of aileler) {
  const sema = SEMALAR[id];
  const degerler = front.PRUVO_KONF.varsayilanDegerler(sema);
  const kalem = { id, malzeme: "PETG", renk: "Siyah", adet: 1, parametreler: degerler };
  const r = await baslat(ucretsizMod, [d1Satiri(id)], kalem);
  const beklenen = orakil(front, sema, degerler, "PETG", "Siyah");
  if (r.kod === 200 && r.birimKurus === beklenen) {
    regOk += 1;
  } else {
    hatalar.push("(3) " + id + ": worker " + r.kod + "/" + r.birimKurus +
                 " != bagimsiz orakil " + beklenen);
  }
  regSatir.push(id + "=" + r.birimKurus);
}
not("  " + regOk + "/" + aileler.length + " parametrik aile (varsayilan olcu, PETG/Siyah) " +
    "BAGIMSIZ orakille BIREBIR");
not("  fiyatlar (kurus): " + regSatir.join(" · "));

// 13 KONFIGURLU (dekor konfiguratoru) urun — 2-renk kolu bu urunlere HIC dokunmamali.
const { KONFIGURLAR } = await import(
  pathToFileURL(path.join(UCRETSIZ_AYNA, "shop/src/konfigurlar.js")).href);
const konfigurIdler = [...KONFIGURLAR.keys()].sort();
const konfigurDenemeler = [[150, "PLA"], [300, "ASA"], [60, "PLA"]];
let kOk = 0;
const kSatir = [];
for (const id of konfigurIdler) {
  const fiyatlar = [];
  for (const [boy, malzeme] of konfigurDenemeler) {
    // `konfigur` KOLONU sart: FAZ 4'ten beri konfigur fiyati D1'in bu kolonundan hesaplanir
    // (bundle'dan degil); kolonsuz satirda kalem fail-closed 400 alirdi.
    const d1 = { id, baslik: "Test " + id, kategori: "Skan Art", fiyat: "500 TL",
                 parametrik: 0, gorsel: "",
                 konfigur: JSON.stringify(KONFIGURLAR.get(id)) };
    const kalem = { id, malzeme, renk: "Siyah", adet: 1, parametreler: { boy_mm: boy } };
    const a = await baslat(ucretsizMod, [d1], kalem);
    const b = await baslat(ucretliMod, [d1], kalem);
    if (a.kod === 200 && a.kod === b.kod && a.birimKurus === b.birimKurus) {
      kOk += 1;
    } else {
      hatalar.push("(3-konfigur) " + id + " " + boy + "mm/" + malzeme + ": ucretsiz " + a.kod +
                   "/" + a.birimKurus + " != ucretli " + b.kod + "/" + b.birimKurus);
    }
    fiyatlar.push(a.birimKurus);
  }
  kSatir.push(id.replace("-serit-dekoratif-figur", "") + "=" + fiyatlar.join("/"));
}
not("  " + kOk + "/" + (konfigurIdler.length * konfigurDenemeler.length) + " konfigur kalemi (" +
    konfigurIdler.length + " urun x 150/PLA,300/ASA,60/PLA) iki varyantta BIREBIR ayni");
not("  konfigur fiyatlari (150PLA/300ASA/60PLA, kurus): " + kSatir.join(" · "));
not("");

// ---------------------------------------------------------------- SET 4 (VAKUM)
not("== SET 4) VAKUM — degisiklik geri alinirsa (IKI_RENK_EK_KURUS = 7500) ==");
const vaKalem = kalemYap(SENARYOLAR[0]);
const vaEs = kalemYap(SENARYOLAR[0], true);
const vUcretsiz = await baslat(ucretsizMod, [d1Satiri(CERCEVE)], vaKalem);
const vUcretsizEs = await baslat(ucretsizMod, [d1Satiri(CERCEVE)], vaEs);
const vUcretli = await baslat(ucretliMod, [d1Satiri(CERCEVE)], vaKalem);
const vUcretliEs = await baslat(ucretliMod, [d1Satiri(CERCEVE)], vaEs);
not("  UCRETSIZ: 2-renk=" + vUcretsiz.birimKurus + " tek-renk=" + vUcretsizEs.birimKurus +
    " -> fark " + (vUcretsiz.birimKurus - vUcretsizEs.birimKurus));
not("  UCRETLI : 2-renk=" + vUcretli.birimKurus + " tek-renk=" + vUcretliEs.birimKurus +
    " -> fark " + (vUcretli.birimKurus - vUcretliEs.birimKurus));
const vakumKirmizi = vUcretli.birimKurus !== vUcretliEs.birimKurus;
not("  (1) iddiasi ('2-renk == tek-renk') UCRETLI varyantta " +
    (vakumKirmizi ? "KIRMIZI yanar ✅ (nobetci CANLI)" : "YESIL kalir ❌ (nobetci OLU)"));
if (!vakumKirmizi) {
  hatalar.push("(4) OLU NOBETCI: ucret geri acildiginda (1) iddiasi yine de yesil kaliyor");
}
if (vUcretli.birimKurus - vUcretliEs.birimKurus !== EK_KURUS) {
  hatalar.push("(4) geri alinan tutar " + (vUcretli.birimKurus - vUcretliEs.birimKurus) +
               ", beklenen " + EK_KURUS);
}
if (!/\+75 TL/.test(vUcretli.detay || "")) {
  hatalar.push("(4) UCRETLI detayda '+75 TL' yok — metin sabitten turemiyor olabilir: " +
               vUcretli.detay);
}
not("  UCRETLI detay: " + vUcretli.detay);
not("  UCRETSIZ detay: " + vUcretsiz.detay);
not("");

// ---------------------------------------------------------------- SET 5 (tek kaynak)
not("== SET 5) TEK KAYNAK — front/Worker kaynaginda ikinci 7500 sabiti ==");
for (const rel of ["jenerator/konfigurator.js", "shop/src/parametrik.js"]) {
  const kacak = diskten(rel).split("\n")
    .map((satir, i) => ({ satir, no: i + 1 }))
    .filter((x) => /7500/.test(x.satir) && !/^\s*(\/\/|\*|\/\*)/.test(x.satir));
  not("  " + rel + ": kod satirinda '7500' gecisi = " + kacak.length);
  for (const k of kacak) {
    hatalar.push("(5) " + rel + ":" + k.no + " ikinci sabit: " + k.satir.trim());
  }
}
const tekTanim = (KAYNAK_SEC.match(/var IKI_RENK_EK_KURUS\s*=/g) || []).length;
not("  secenekler.js: IKI_RENK_EK_KURUS tanimi = " + tekTanim + " (1 olmali)");
if (tekTanim !== 1) { hatalar.push("(5) secenekler.js'te IKI_RENK_EK_KURUS tanimi " + tekTanim); }
not("");

// ---------------------------------------------------------------- BILGI: tarihsel karsilastirma
// git HEAD hala UCRETLI iken (yani bu degisiklik daha commit/merge edilmemisken) eski-yeni
// farkini SAYIYLA gosterir. HEAD ucretsizlestikten sonra karsilastirma totolojiye donecegi
// icin ATLANIR — iddia degil, BILGIDIR (bloklayici iddialar yukarida, tabani git'ten bagimsiz).
not("== BILGI) git HEAD ile tarihsel karsilastirma ==");
try {
  const headSec = headden("secenekler.js");
  if (headSec.includes(SABIT_ACIK) || /var IKI_RENK_EK_KURUS = 7500;/.test(headSec)) {
    const headAyna = aynaKur("head", headden);
    const headMod = await import(pathToFileURL(path.join(headAyna, "shop/src/index.js")).href);
    const h = await baslat(headMod, [d1Satiri(CERCEVE)], vaKalem);
    not("  HEAD hala ucretli: 2-renk kalem HEAD=" + h.birimKurus + " -> bugun=" +
        vUcretsiz.birimKurus + " (fark " + (vUcretsiz.birimKurus - h.birimKurus) + ")");
  } else {
    not("  ATLANDI — HEAD zaten ucretsiz (degisiklik commit/merge edilmis). Bloklayici " +
        "iddialar git gecmisine BAGLI DEGIL, iki-varyant tabaniyla olculur.");
  }
} catch (e) {
  not("  OLCULEMEDI: " + e.message);
}

// ---------------------------------------------------------------- rapor
console.log(ham.join("\n"));
if (hatalar.length) {
  console.log("❌ KALDI — " + hatalar.length + " iddia:");
  hatalar.forEach((h) => console.log("   ❌ " + h));
  process.exit(1);
}
console.log("✅ GECTI — 5 setin hepsi yesil (para kaniti + parite + regresyon + vakum + tek kaynak)");
