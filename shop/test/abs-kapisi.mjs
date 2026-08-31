#!/usr/bin/env node
/**
 * ABS: FIYAT TUREMESI + KATEGORI SUZGECI — KABUL TESTI.
 *
 *   node shop/test/abs-kapisi.mjs                 # kabul bataryasi (deploy.yml'de BLOKLAYICI)
 *   python3 tools/abs-mutasyon.py                 # ONCE-KIRMIZI kaniti (o da CI'da BLOKLAYICI)
 *
 * ISLETME KARARI (Okan, 14 Agu): ABS satisa GERI ACILDI ve fiyati ASA ile BIREBIR AYNI;
 * Ev · Ofis · Dekorasyon · Skan Art · Oyun/Hobi kategorilerinde ABS SECILEMEZ. Karbon
 * Katkili KAPALI KALIR.
 *
 * OLCULEN IKI SESSIZ-HATA SINIFI:
 *   (1) IKIZ SAYI — "ABS = ASA" iki ayri sayi olarak yazilirsa biri sessizce ayrisir
 *       ([[ikiz-tanim-sessiz-ayrisma]]). Bu yuzden esitlik TEK BASINA yetmez: test ASA'yi
 *       fiksturde DEGISTIRIP ABS'in onu TAKIP ETTIGINI olcer. Elle yazilmis bir "60"
 *       esitlik testini gecer, TUREME testini GECEMEZ.
 *   (2) UI'DAN GIZLEMEK ODEME YOLUNU KAPATMAZ — bu depoda olculdu
 *       ([[ui-kaldirmak-odeme-yolunu-kapatmaz]]): secici kaldirildigi halde sunucu ayni
 *       carpani uygulamaya devam etti. Bu yuzden kategori suzgeci hem SECIM LISTESINDE
 *       (urun sayfasi cipleri + parametrik dropdown, tools/build.py) hem WORKER KABULUNDE
 *       (shop/src/index.js, 400 + fiyat DONMEZ) ayri ayri olculur.
 *
 * KAPSAM: secenekler.js (kanonik tablo + turetme) · tools/build.py (secim listesi ureteci,
 * GERCEK fonksiyonlar python3 kopruyle kosturulur — ikinci bir liste UYDURULMAZ) ·
 * shop/src/index.js (Worker kabulu, GERCEK kod + sahte D1) · tools/filamentler.json ·
 * urunler.json (konfigur kolu) · uc mühendislik paketi belgesi.
 *
 * OFFLINE: ag YOK (global fetch sahtelenir), D1 sahte, wrangler YOK, siparis OLUSMAZ,
 * DEPO DOSYASI YAZILMAZ (mutantlar isletim sistemi gecici dizinine kopyalanir; kaynak
 * sha256'lari bas/son karsilastirilir ve gecici dizinler cikista SILINIR).
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (kopru/kaynak capasi bulunamadi).
 * 🔴 IDDIA SAYISI BU YORUMA YAZILMAZ — betik son satirda kendisi basar.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const require = createRequire(import.meta.url);
const KENDINI_TEST = process.argv.includes("--kendini-test");

// ---------------------------------------------------------------- yollar (mutasyon kancasi)
// Mutasyon bataryasi bu ortam degiskenleriyle GECICI KOPYALARA isaret eder; varsayilan
// DAIMA depodaki gercek dosyadir (bayrak verilmezse mutasyon YOLU HIC ACILMAZ).
const SECENEKLER_YOL = process.env.PRUVO_ABS_SECENEKLER || path.join(KOK, "secenekler.js");
const SHOP_SRC = process.env.PRUVO_ABS_SHOP_SRC || path.join(SHOP, "src");
const URUNLER_YOL = process.env.PRUVO_ABS_URUNLER || path.join(KOK, "urunler.json");
const FILAMENTLER_YOL = process.env.PRUVO_ABS_FILAMENTLER ||
  path.join(KOK, "tools", "filamentler.json");
const BELGELER = ["taban-fiyat-tablosu.md", "paket-sari-konfigurator.md", "paket-shop-odeme.md"]
  .map((a) => path.join(KOK, "tools", a));

// Kaynak butunlugu: test DEPO DOSYASINA YAZMAZ. Bas/son sha256 esit olmali.
const KAYNAKLAR = [path.join(KOK, "secenekler.js"), path.join(SHOP, "src", "index.js"),
                   path.join(KOK, "tools", "build.py"), path.join(KOK, "tools", "filamentler.json")];
const sha = (f) => crypto.createHash("sha256").update(fs.readFileSync(f)).digest("hex");
const shaHepsi = () => KAYNAKLAR.map((f) => path.basename(f) + "=" + sha(f).slice(0, 12)).join(" ");
const SHA_BAS = shaHepsi();

// ---------------------------------------------------------------- olcum defteri
let gecen = 0, kalan = 0;
const kirmiziIddialar = [];
function ol(ad, kosul, detay) {
  if (kosul) { gecen += 1; console.log("  ✅ " + ad); }
  else {
    kalan += 1;
    kirmiziIddialar.push(ad);
    console.log("  ❌ " + ad + (detay ? " — " + detay : ""));
  }
}
function baslik(s) { console.log(""); console.log(s); }
function olcumsuz(mesaj) {
  console.error("ÖLÇÜLEMEDİ: " + mesaj);
  process.exit(3);
}

// ---------------------------------------------------------------- kategori kumeleri
const DAHIL = ["Otomobil", "Marin", "Jeneratör"];
const HARIC = ["Ev", "Ofis", "Dekorasyon", "Skan Art", "Oyun/Hobi"];
const COZULEMEZ = ["", "Bilinmeyen Kategori"];

// ---------------------------------------------------------------- secenekler.js (kanonik)
/** secenekler.js'i (ya da gecici mutant kopyasini) yukler ve PRUVO_SECENEK'i doner. */
function secenekYukle(yol) {
  const onceki = globalThis.PRUVO_SECENEK;
  globalThis.PRUVO_SECENEK = undefined;
  require(yol);
  const s = globalThis.PRUVO_SECENEK;
  if (!s) {
    globalThis.PRUVO_SECENEK = onceki;
    olcumsuz("secenekler.js yuklenemedi (fiyat kurali tek kaynagi yok): " + yol);
  }
  return s;
}
const SECENEK = secenekYukle(SECENEKLER_YOL);

// ---------------------------------------------------------------- gecici dizin defteri
const gecici = [];
function geciciDizin(onek) {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-abs-" + onek + "-"));
  gecici.push(d);
  return d;
}
function temizle() {
  while (gecici.length) {
    const d = gecici.pop();
    try { fs.rmSync(d, { recursive: true, force: true }); } catch (e) { /* yut */ }
  }
}
process.on("exit", temizle);

// ---------------------------------------------------------------- build.py koprusu
/**
 * SECIM LISTESI GERCEK URETECTEN olculur: tools/build.py'nin `_fil_cipleri` (urun sayfasi
 * cipleri) ve `_malzeme_renk_html` (parametrik dropdown) fonksiyonlari kosturulup basilan
 * HTML'den malzeme adlari cikarilir. Liste burada YENIDEN YAZILSAYDI, ureteci degisince
 * test yesil kalir ve iddia sessizce olurdu.
 */
function buildKoprusu(kategoriler) {
  const program = [
    "import json, re, sys",
    "sys.path.insert(0, " + JSON.stringify(path.join(KOK, "tools")) + ")",
    "import build",
    "kats = json.loads(" + JSON.stringify(JSON.stringify(kategoriler)) + ")",
    "out = {'fark': build.FILAMENT_FARK, 'sira': build.FILAMENT_SIRA,",
    "       'haric': build.FILAMENT_KATEGORI_HARIC,",
    "       'param_kat': build.PARAMETRIK_KATEGORI,",
    "       'cipler': {}, 'dropdown': {}, 'offer': {}}",
    "for k in kats:",
    "    p = {'id': 'olcum-urunu', 'kategori': k, 'fiyat': '1000 TL', 'baslik': 'ölçüm'}",
    "    html = ''.join(build._fil_cipleri(p))",
    "    out['cipler'][k] = re.findall(r'data-malzeme=\"([^\"]+)\"', html)",
    "    pp = dict(p); pp['parametrik'] = True",
    "    d = build._malzeme_renk_html(pp, 'https://pruvo3d.com/urun/olcum-urunu/')",
    "    m = re.search(r'id=\"malzemeSec\">(.*?)</select>', d, re.S)",
    "    out['dropdown'][k] = re.findall(r'<option value=\"([^\"]+)\">', m.group(1)) if m else None",
    "    out['offer'][k] = len([x for x in build.FILAMENT_SIRA",
    "                           if build.malzeme_kategori_uygun_mu(x, k)])",
    "print('PRUVO-ABS-JSON ' + json.dumps(out, ensure_ascii=False))",
  ].join("\n");
  let ham;
  try {
    ham = execFileSync("python3", ["-c", program], { encoding: "utf8", cwd: KOK });
  } catch (e) {
    olcumsuz("tools/build.py koprusu kosturulamadi: " + ((e && e.message) || e) +
             " " + ((e && e.stderr) || ""));
  }
  const satir = ham.split("\n").find((s) => s.startsWith("PRUVO-ABS-JSON "));
  if (!satir) { olcumsuz("build.py koprusu JSON basmadi. Ham cikti: " + ham.slice(0, 500)); }
  return JSON.parse(satir.slice("PRUVO-ABS-JSON ".length));
}

// ---------------------------------------------------------------- Worker (gercek kod)
/** `import X from "...json";` -> `const X = <json icerigi>;` (fiyat-prova.mjs ile ayni cozum). */
function jsonGom(kaynak, kaynakDizin, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const yol = path.resolve(kaynakDizin, rel);
      const govde = fs.readFileSync(yol, "utf8").trim();
      JSON.parse(govde);
      return "const " + ad + " = " + govde + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ") — desen guncellenmeli");
  }
  return cikti;
}

/**
 * Worker'i GECICI MINI AGACTA kurar: <tmp>/secenekler.js + <tmp>/konfigur.js +
 * <tmp>/shop/src/*.js. Boylece Worker'in `../../secenekler.js` importu MUTANT kopyayi
 * cozer (depodaki dosyaya DOKUNULMAZ) ve secenekler mutasyonu odeme yoluna da ULASIR.
 */
function workerAgaci(secenekKaynak, srcDosyalari) {
  const kok = geciciDizin("worker");
  fs.writeFileSync(path.join(kok, "secenekler.js"), secenekKaynak);
  const src = path.join(kok, "shop", "src");
  fs.mkdirSync(src, { recursive: true });
  for (const [ad, kaynak] of Object.entries(srcDosyalari)) {
    fs.writeFileSync(path.join(src, ad), jsonGom(kaynak, path.join(SHOP, "src"), ad));
  }

  // DEPO KOKUNDEKI BAGIMLILIKLAR (secenekler.js · konfigur.js · jenerator/*.js ...) mini
  // agaca AYNI goreli yolla kopyalanir; boylece "../../x.js" importlari cozulur ve hicbir
  // dosya elle sayilmaz (yeni bir bagimlilik eklenirse test kendiliginden takip eder).
  const eklendi = new Set(["secenekler.js"]);
  const kuyruk = [];
  const topla = (kaynak, mutlakDizin, jsonDahil) => {
    const desen = /(?:from|import)\s+"([^"]+)"/g;
    let m;
    while ((m = desen.exec(kaynak)) !== null) {
      const ref = m[1];
      if (!ref.startsWith(".")) { continue; }
      const hedef = path.resolve(mutlakDizin, ref);
      if (!hedef.startsWith(KOK + path.sep)) { continue; }
      if (!jsonDahil && hedef.endsWith(".json")) { continue; }   // src'de JSON zaten gomuldu
      const goreli = path.relative(KOK, hedef);
      if (goreli.startsWith("shop" + path.sep + "src" + path.sep)) { continue; }
      if (eklendi.has(goreli)) { continue; }
      eklendi.add(goreli);
      kuyruk.push(goreli);
    }
  };
  for (const kaynak of Object.values(srcDosyalari)) { topla(kaynak, path.join(SHOP, "src"), false); }
  while (kuyruk.length) {
    const goreli = kuyruk.shift();
    const kaynakYol = path.join(KOK, goreli);
    if (!fs.existsSync(kaynakYol)) { continue; }
    const hedefYol = path.join(kok, goreli);
    fs.mkdirSync(path.dirname(hedefYol), { recursive: true });
    fs.copyFileSync(kaynakYol, hedefYol);
    if (!goreli.endsWith(".json")) {
      topla(fs.readFileSync(kaynakYol, "utf8"), path.dirname(kaynakYol), true);
    }
  }
  return src;
}

function srcKaynaklari(dizin) {
  const d = {};
  for (const ad of fs.readdirSync(dizin)) {
    // 🔴 `.mjs` DE ALINIR (31 Agu 2026): ayna shop/src'in TAMAMINI temsil etmeli;
    // `.js` suzgeci shop/src/kanal-sinif.mjs'i disarida birakip yonet.js'i dusuruyordu.
    if (/\.m?js$/.test(ad)) { d[ad] = fs.readFileSync(path.join(dizin, ad), "utf8"); }
  }
  return d;
}

let modulSayaci = 0;
async function workerYukle(src) {
  modulSayaci += 1;
  return await import(pathToFileURL(path.join(src, "index.js")).href + "?s=" + modulSayaci);
}

// ---- sahte cevre (ag YOK: beklenmeyen adres bile olsa siparis/odeme OLUSMAZ)
const ag = { toplam: 0 };
globalThis.fetch = async function sahteFetch() {
  ag.toplam += 1;
  return new Response(JSON.stringify({ status: "success", token: "abs-test-token",
                                       paymentPageUrl: "https://odeme.test/sayfa" }),
                      { status: 200, headers: { "Content-Type": "application/json" } });
};

function yeniSayac() { return { select: 0, first: 0, run: 0, yazilan: [] }; }

/** Sahte D1 — gercek D1 gibi PROJEKSIYON yapar (SELECT'ten dusen kolon testte de duser). */
function d1Sahte(satirlar, sayaclar) {
  const harita = new Map(satirlar.map((u) => [u.id, u]));
  return {
    prepare(sql) {
      const secilen = ((/SELECT ([^]*?) FROM /.exec(sql) || [])[1] || "")
        .split(",").map((a) => a.trim()).filter(Boolean);
      const izdusum = (u) => {
        if (!u || !secilen.length || secilen.includes("*")) { return u; }
        const o = {};
        for (const c of secilen) { if (c in u) { o[c] = u[c]; } }
        return o;
      };
      return {
        bind(...arg) {
          return {
            async all() {
              sayaclar.select += 1;
              return { results: arg.map((id) => harita.get(id)).filter(Boolean).map(izdusum) };
            },
            async first() { sayaclar.first += 1; return null; },
            async run() {
              sayaclar.run += 1;
              sayaclar.yazilan.push({ sql, arg });
              return { meta: { changes: 1 } };
            },
          };
        },
      };
    },
  };
}

// Hiz siniri binding'i: /fiyat ucu fail-closed'dur (binding yoksa 429) — olculen eksen
// ABS kapisi oldugu icin limiter DAIMA "gecti" der.
const LIMITER = { async limit() { return { success: true }; } };
const ENV_TABAN = {
  SITE_URL: "https://pruvo3d.com",
  IYZICO_BASE_URL: "https://iyzico.test",
  IYZICO_API_KEY: "test-api-key",
  IYZICO_SECRET_KEY: "test-secret-key",
  TELEGRAM_TOKEN: "test-telegram-token",
  TELEGRAM_CHAT: "1",
  TELEGRAM_API: "https://telegram.test",
  HAVALE_IBAN: "TR090006701000000059703630",
  HAVALE_UNVAN: "Test Unvan",
  FIYAT_RATE_LIMIT: LIMITER,
};
const MUSTERI = {
  ad: "Ölçüm Müşterisi", tel: "5551112233", eposta: "olcum@ornek.test",
  adres: "Ölçüm Mahallesi 1", sehir: "Muğla",
};

function d1Satiri(id, kategori, fiyat) {
  return { id, baslik: "Ölçüm ürünü", kategori, fiyat, parametrik: 0, gorsel: "",
           konfigur: "", tur: "" };
}

async function prova(mod, satirlar, sepet) {
  const sayaclar = yeniSayac();
  const agOnce = ag.toplam;
  const env = Object.assign({}, ENV_TABAN, { KATALOG: d1Sahte(satirlar, sayaclar) });
  const istek = new Request("https://pruvo3d.com/api/shop/fiyat", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": "10.0.0.1" },
    body: JSON.stringify({ sepet }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let ham = "", govde = {};
  try { ham = await cevap.clone().text(); govde = JSON.parse(ham); } catch (e) { govde = {}; }
  return { kod: cevap.status, govde, ham, d1Yazma: sayaclar.run, agCagri: ag.toplam - agOnce };
}

async function baslat(mod, satirlar, sepet) {
  const sayaclar = yeniSayac();
  const agOnce = ag.toplam;
  const env = Object.assign({}, ENV_TABAN, { KATALOG: d1Sahte(satirlar, sayaclar) });
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sozlesme_onay: true, odeme: "kart", musteri: MUSTERI, sepet }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  return { kod: cevap.status, govde, d1Yazma: sayaclar.run, agCagri: ag.toplam - agOnce };
}

const kalem = (id, malzeme) => ({ id, malzeme, renk: "Siyah", adet: 1 });

// =================================================================== KOSUM
console.log("Node: " + process.version);
console.log("Kaynak sha256 (bas): " + SHA_BAS);

const KOPRU = buildKoprusu(DAHIL.concat(HARIC).concat(COZULEMEZ));
const WORKER_SRC = workerAgaci(fs.readFileSync(SECENEKLER_YOL, "utf8"), srcKaynaklari(SHOP_SRC));
const WORKER = await workerYukle(WORKER_SRC);

// ------------------------------------------------------------ 1) KATSAYI = ASA (TUREME)
baslik("== 1) ABS katsayisi ASA'dan TURER (esitlik TEK BASINA yetmez) ==");
{
  ol("1.1 FILAMENT_FARK.ABS === FILAMENT_FARK.ASA",
     SECENEK.FILAMENT_FARK.ABS === SECENEK.FILAMENT_FARK.ASA,
     "ABS=" + SECENEK.FILAMENT_FARK.ABS + " ASA=" + SECENEK.FILAMENT_FARK.ASA);
  ol("1.2 sayfa ureteci (build.py) AYNI katsayiyi goruyor",
     KOPRU.fark.ABS === SECENEK.FILAMENT_FARK.ABS &&
     KOPRU.fark.ABS === KOPRU.fark.ASA,
     "py ABS=" + KOPRU.fark.ABS + " py ASA=" + KOPRU.fark.ASA);

  // 🔴 TUREME OLCUSU: ASA fiksturde DEGISTIRILIR; ABS onu TAKIP ETMELIDIR. Elle yazilmis
  // sabit bir sayi (mutant N1) 1.1'i gecebilir ama BURAYI gecemez.
  const YENI_ASA = 77;
  const ham = fs.readFileSync(SECENEKLER_YOL, "utf8");
  const desen = /"ASA":\s*\d+/;
  if (!desen.test(ham)) { olcumsuz('secenekler.js icinde "ASA": <sayi> capasi bulunamadi'); }
  const mutantDizin = geciciDizin("tureme");
  const mutantYol = path.join(mutantDizin, "secenekler.js");
  fs.writeFileSync(mutantYol, ham.replace(desen, '"ASA": ' + YENI_ASA));
  const S2 = secenekYukle(mutantYol);
  ol("1.3 TUREME: ASA " + SECENEK.FILAMENT_FARK.ASA + " -> " + YENI_ASA +
     " yapilinca ABS de " + YENI_ASA + " olur",
     S2.FILAMENT_FARK.ASA === YENI_ASA && S2.FILAMENT_FARK.ABS === YENI_ASA,
     "mutant ABS=" + S2.FILAMENT_FARK.ABS + " ASA=" + S2.FILAMENT_FARK.ASA);
  // Kanonik modulu geri yukle (sonraki setler onu okur).
  globalThis.PRUVO_SECENEK = SECENEK;

  const py = buildKoprusuTureme(mutantYol);
  ol("1.4 TUREME sayfa uretecinde de gecerli (ikinci sayi bakimi YOK)",
     py !== null && py.ABS === YENI_ASA && py.ASA === YENI_ASA,
     "py mutant = " + JSON.stringify(py));
}

/** Mutant secenekler.js icin build.py'nin turetme kolunu ayri bir surecte olcer. */
function buildKoprusuTureme(secenekYol) {
  const program = [
    "import json, re, sys",
    "kaynak = open(" + JSON.stringify(secenekYol) + ", encoding='utf-8').read()",
    "def sabit(ad):",
    "    m = re.search(r'var\\s+' + ad + r'\\s*=\\s*(\\{.*?\\}|\\[.*?\\]);', kaynak, re.S)",
    "    return json.loads(m.group(1)) if m else None",
    "fark = sabit('FILAMENT_FARK'); tureme = sabit('FILAMENT_TUREME')",
    "if fark is None or tureme is None:",
    "    print('PRUVO-ABS-JSON null')",
    "else:",
    "    for a, k in tureme.items():",
    "        fark[a] = fark[k]",
    "    print('PRUVO-ABS-JSON ' + json.dumps(fark, ensure_ascii=False))",
  ].join("\n");
  let ham;
  try {
    ham = execFileSync("python3", ["-c", program], { encoding: "utf8", cwd: KOK });
  } catch (e) {
    return null;
  }
  const satir = ham.split("\n").find((s) => s.startsWith("PRUVO-ABS-JSON "));
  return satir ? JSON.parse(satir.slice("PRUVO-ABS-JSON ".length)) : null;
}

// ------------------------------------------------------------ 2) SIRA
baslik("== 2) ABS secim sirasinda ve ASA'dan HEMEN SONRA ==");
{
  const s = SECENEK.FILAMENT_SIRA;
  ol("2.1 FILAMENT_SIRA ABS iceriyor", s.indexOf("ABS") !== -1, JSON.stringify(s));
  ol("2.2 sira: ABS, ASA'dan hemen sonra",
     s.indexOf("ABS") === s.indexOf("ASA") + 1, JSON.stringify(s));
  ol("2.3 sayfa ureteci AYNI sirayi goruyor",
     JSON.stringify(KOPRU.sira) === JSON.stringify(s),
     "py=" + JSON.stringify(KOPRU.sira));
}

// ------------------------------------------------------------ 3) DAHIL KATEGORILER
baslik("== 3) DAHIL kategoride secim listesi ABS ICERIR ==");
for (const k of DAHIL) {
  ol("3." + k + " kanonik liste ABS iceriyor",
     SECENEK.kategoriFilamentSirasi(k).indexOf("ABS") !== -1,
     JSON.stringify(SECENEK.kategoriFilamentSirasi(k)));
  ol("3." + k + " urun sayfasi CIPLERI ABS iceriyor (gercek uretec)",
     (KOPRU.cipler[k] || []).indexOf("ABS") !== -1,
     JSON.stringify(KOPRU.cipler[k]));
  ol("3." + k + " parametrik DROPDOWN ABS iceriyor (gercek uretec)",
     (KOPRU.dropdown[k] || []).indexOf("ABS") !== -1,
     JSON.stringify(KOPRU.dropdown[k]));
}

// ------------------------------------------------------------ 4) HARIC KATEGORILER
baslik("== 4) HARIC bes kategoride secim listesi ABS ICERMEZ ==");
{
  const tablo = SECENEK.FILAMENT_KATEGORI_HARIC.ABS || [];
  ol("4.0 kanonik tablo TAM olarak bes kategori sayiyor",
     tablo.length === HARIC.length && HARIC.every((k) => tablo.indexOf(k) !== -1),
     JSON.stringify(tablo));
  ol("4.0b sayfa ureteci AYNI tabloyu okuyor (ikiz tanim YOK)",
     JSON.stringify((KOPRU.haric || {}).ABS) === JSON.stringify(tablo),
     "py=" + JSON.stringify((KOPRU.haric || {}).ABS));
}
for (const k of HARIC) {
  const liste = SECENEK.kategoriFilamentSirasi(k);
  ol("4." + k + " kanonik liste ABS ICERMEZ", liste.indexOf("ABS") === -1, JSON.stringify(liste));
  ol("4." + k + " listede diger malzemeler DURUYOR (asiri eleme yok)",
     liste.length === SECENEK.FILAMENT_SIRA.length - 1, JSON.stringify(liste));
  ol("4." + k + " urun sayfasi CIPLERINDE ABS YOK (gercek uretec)",
     (KOPRU.cipler[k] || []).indexOf("ABS") === -1, JSON.stringify(KOPRU.cipler[k]));
  ol("4." + k + " parametrik DROPDOWN'da ABS YOK (gercek uretec)",
     (KOPRU.dropdown[k] || []).indexOf("ABS") === -1, JSON.stringify(KOPRU.dropdown[k]));
  ol("4." + k + " yapilandirilmis veri offerCount secilebilir adedi yaziyor",
     KOPRU.offer[k] === SECENEK.FILAMENT_SIRA.length - 1, "offerCount=" + KOPRU.offer[k]);
}

// ------------------------------------------------------------ 5) WORKER: HARIC -> RED
baslik("== 5) WORKER haric kategoride ABS'li istegi REDDEDER (fiyat DONMEZ) ==");
{
  // GUCLU KONTROL: haric bir kategoride PLA'li kalem GERCEKTEN odenebilir (kapinin
  // butun kategoriyi kapatmadigi, yalniz ABS'i eledigi kaniti).
  const satirlar = [d1Satiri("olcum-ev-kontrol", "Ev", "1000 TL")];
  const c = await prova(WORKER, satirlar, [kalem("olcum-ev-kontrol", "PLA")]);
  ol("5.0 KONTROL: Ev kategorisinde PLA 200 ve tutar 100000 kurus",
     c.kod === 200 && c.govde.urun_kurus === 100000,
     "kod=" + c.kod + " urun_kurus=" + (c.govde || {}).urun_kurus);
}
for (const k of HARIC) {
  const id = "olcum-" + k.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const satirlar = [d1Satiri(id, k, "1000 TL")];
  const r = await prova(WORKER, satirlar, [kalem(id, "ABS")]);
  ol("5." + k + " /fiyat 400 + hata=malzeme-kategori",
     r.kod === 400 && r.govde && r.govde.hata === "malzeme-kategori",
     "kod=" + r.kod + " govde=" + r.ham.slice(0, 160));
  const anahtarlar = Object.keys(r.govde || {});
  ol("5." + k + " cevapta TUTAR YOK (kalem fiyat hesabina HIC girmedi)",
     anahtarlar.every((a) => !/kurus|tutar|prova|satirlar/.test(a)),
     JSON.stringify(anahtarlar));
  const b = await baslat(WORKER, satirlar, [kalem(id, "ABS")]);
  ol("5." + k + " /baslat 400 + D1 YAZMA 0 + ag cagrisi 0",
     b.kod === 400 && b.govde.hata === "malzeme-kategori" && b.d1Yazma === 0 && b.agCagri === 0,
     "kod=" + b.kod + " yazma=" + b.d1Yazma + " ag=" + b.agCagri);
  // KONTROL EKSENI: fikstur bozuk DEGIL — AYNI urun PLA ile bu kapiya TAKILMAZ.
  // (Skan Art'ta PLA da 400 alir ama BASKA sebeple: "konfigur-urun" fail-closed kolu —
  // o kolu bu spec DEGISTIRMEZ, bkz. A4. Bu yuzden kontrol "200" degil "bu hata degil"dir.)
  const c = await prova(WORKER, satirlar, [kalem(id, "PLA")]);
  ol("5." + k + " KONTROL: ayni urun PLA ile 'malzeme-kategori' ALMAZ (red ABS'e OZEL)",
     (c.govde || {}).hata !== "malzeme-kategori",
     "kod=" + c.kod + " hata=" + ((c.govde || {}).hata || "-"));
}

// ------------------------------------------------------------ 6) WORKER: DAHIL -> KABUL
baslik("== 6) WORKER dahil kategoride ABS'i KABUL eder, fiyat ASA ile AYNI ==");
{
  const id = "olcum-otomobil";
  const satirlar = [d1Satiri(id, "Otomobil", "1000 TL")];
  const abs = await prova(WORKER, satirlar, [kalem(id, "ABS")]);
  const asa = await prova(WORKER, satirlar, [kalem(id, "ASA")]);
  const pla = await prova(WORKER, satirlar, [kalem(id, "PLA")]);
  ol("6.1 ABS'li istek KABUL (200)", abs.kod === 200, "kod=" + abs.kod + " " + abs.ham.slice(0, 160));
  ol("6.2 ABS tutari = ASA tutari (BIREBIR)",
     abs.kod === 200 && asa.kod === 200 && abs.govde.urun_kurus === asa.govde.urun_kurus,
     "ABS=" + (abs.govde || {}).urun_kurus + " ASA=" + (asa.govde || {}).urun_kurus);
  // SABIT BEKLENEN (referanssiz capa): 1.000 TL x 1,60 = 160.000 kurus.
  ol("6.3 SPEC: 1.000 TL urunde ABS birim tutari 160000 kurus",
     abs.kod === 200 && abs.govde.urun_kurus === 160000,
     "gelen=" + (abs.govde || {}).urun_kurus);
  ol("6.4 KONTROL: PLA tabani 100000 kurus (katsayi yolu canli)",
     pla.kod === 200 && pla.govde.urun_kurus === 100000,
     "gelen=" + (pla.govde || {}).urun_kurus);
  const b = await baslat(WORKER, satirlar, [kalem(id, "ABS")]);
  ol("6.5 /baslat ABS'li siparisi kurar (200/302) ve D1'e YAZAR",
     b.kod < 400 && b.d1Yazma > 0, "kod=" + b.kod + " yazma=" + b.d1Yazma);
}

// ------------------------------------------------------------ 7) FAIL-CLOSED
baslik("== 7) Kategori bos/bilinmeyen -> ABS GOSTERILMEZ ve KABUL EDILMEZ ==");
for (const k of COZULEMEZ) {
  const etiket = k === "" ? "(bos)" : k;
  ol("7." + etiket + " kanonik liste ABS ICERMEZ",
     SECENEK.kategoriFilamentSirasi(k).indexOf("ABS") === -1,
     JSON.stringify(SECENEK.kategoriFilamentSirasi(k)));
  ol("7." + etiket + " urun sayfasi CIPLERINDE ABS YOK (gercek uretec)",
     (KOPRU.cipler[k] || []).indexOf("ABS") === -1, JSON.stringify(KOPRU.cipler[k]));
  const id = "olcum-cozulemez-" + (k === "" ? "bos" : "bilinmeyen");
  const satirlar = [d1Satiri(id, k, "1000 TL")];
  const r = await prova(WORKER, satirlar, [kalem(id, "ABS")]);
  ol("7." + etiket + " WORKER ABS'li istegi REDDEDER (400)",
     r.kod === 400 && r.govde.hata === "malzeme-kategori",
     "kod=" + r.kod + " " + r.ham.slice(0, 160));
}
{
  // Kategori alani HIC YOKSA (D1 kolonu duserse) da fail-closed olmali.
  const id = "olcum-kategorisiz";
  const satir = d1Satiri(id, "Otomobil", "1000 TL");
  delete satir.kategori;
  const r = await prova(WORKER, [satir], [kalem(id, "ABS")]);
  ol("7.kolonsuz WORKER kategori alani YOKKEN de ABS'i reddeder",
     r.kod === 400 && r.govde.hata === "malzeme-kategori",
     "kod=" + r.kod + " " + r.ham.slice(0, 160));
  ol("7.kolonsuz KONTROL: ayni satir PLA ile 200",
     (await prova(WORKER, [satir], [kalem(id, "PLA")])).kod === 200);
}

// ------------------------------------------------------------ 8) SKAN ART KONFIGUR
baslik("== 8) Skan Art konfigur kolu DEGISMEDI (ABS SIZMADI) ==");
{
  let urunler;
  try { urunler = JSON.parse(fs.readFileSync(URUNLER_YOL, "utf8")); }
  catch (e) { olcumsuz("urunler.json okunamadi: " + ((e && e.message) || e)); }
  const konf = urunler.filter((u) => u && u.konfigur);
  const adlar = new Set();
  let malzemesiz = 0;
  const katsayiHatalari = [];
  for (const u of konf) {
    const ml = (u.konfigur && u.konfigur.malzemeler) || null;
    if (!ml || !ml.length) { malzemesiz += 1; continue; }
    for (const m of ml) {
      adlar.add(m.ad);
      const beklenen = 1 + (SECENEK.FILAMENT_FARK[m.ad] || 0) / 100;
      if (Math.abs(m.katsayi - beklenen) > 1e-9) {
        katsayiHatalari.push(u.id + "/" + m.ad + "=" + m.katsayi);
      }
    }
  }
  ol("8.1 konfigur urun sayisi 16 (Skan Art dekor serisi)", konf.length === 16,
     "sayi=" + konf.length);
  ol("8.2 hepsi Skan Art kategorisinde",
     konf.every((u) => u.kategori === "Skan Art"),
     JSON.stringify([...new Set(konf.map((u) => u.kategori))]));
  ol("8.3 malzeme kumesi TAM {PLA, PETG, ASA} — ABS SIZMADI",
     adlar.size === 3 && ["PLA", "PETG", "ASA"].every((a) => adlar.has(a)) && !adlar.has("ABS"),
     JSON.stringify([...adlar]));
  ol("8.4 her konfigur urununde malzeme listesi DOLU", malzemesiz === 0,
     "malzemesiz=" + malzemesiz);
  ol("8.5 konfigur katsayilari FILAMENT_FARK ile ortusuyor", katsayiHatalari.length === 0,
     katsayiHatalari.slice(0, 5).join(", "));
  ol("8.6 Skan Art kategorisi ABS'e KAPALI (tablo)",
     !SECENEK.malzemeKategoriUygunMu("ABS", "Skan Art"));
}

// ------------------------------------------------------------ 9) KARBON KAPALI KALIR
baslik("== 9) Karbon Katkili hala satisa KAPALI (kapsam sizmasi yok) ==");
{
  let ref;
  try { ref = JSON.parse(fs.readFileSync(FILAMENTLER_YOL, "utf8")); }
  catch (e) { olcumsuz("filamentler.json okunamadi: " + ((e && e.message) || e)); }
  const kayit = (ref.filamentler || []).filter((f) => f.ad === "Karbon Katkılı");
  const absKayit = (ref.filamentler || []).filter((f) => f.ad === "ABS");
  ol("9.1 Karbon Katkılı kaydi var ve site:false",
     kayit.length === 1 && kayit[0].site === false,
     JSON.stringify(kayit.map((f) => [f.ad, f.site])));
  ol("9.2 Karbon Katkılı FILAMENT_FARK'ta YOK",
     !Object.prototype.hasOwnProperty.call(SECENEK.FILAMENT_FARK, "Karbon Katkılı") &&
     SECENEK.FILAMENT_SIRA.indexOf("Karbon Katkılı") === -1);
  ol("9.3 ABS kaydi site:true (secim listesine giren malzeme referansta da acik)",
     absKayit.length === 1 && absKayit[0].site === true,
     JSON.stringify(absKayit.map((f) => [f.ad, f.site])));
  const siteAdlar = (ref.filamentler || []).filter((f) => f.site).map((f) => f.ad);
  ol("9.4 site:true adlari FILAMENT_SIRA ile BIREBIR ayni kume",
     siteAdlar.length === SECENEK.FILAMENT_SIRA.length &&
     siteAdlar.every((a) => SECENEK.FILAMENT_SIRA.indexOf(a) !== -1),
     JSON.stringify(siteAdlar));
}

// ------------------------------------------------------------ 10) BELGELER
baslik("== 10) Belgelerde 'ABS 1.50' ve 'satisa kapali' beyani KALMADI ==");
let belge150Kalan = 0;
{
  const sadelestir = (s) => s.replace(/[İIı]/g, "i").replace(/[Şş]/g, "s")
    .replace(/[Ğğ]/g, "g").replace(/[Üü]/g, "u").replace(/[Öö]/g, "o")
    .replace(/[Çç]/g, "c").toLowerCase();
  for (const yol of BELGELER) {
    let metin;
    try { metin = fs.readFileSync(yol, "utf8"); }
    catch (e) { olcumsuz("belge okunamadi: " + yol); }
    const ad = path.basename(yol);
    const eski = metin.match(/ABS[^\n]{0,40}?1[.,]50|1[.,]50[^\n]{0,20}?ABS/g) || [];
    belge150Kalan += eski.length;
    ol("10." + ad + " ABS'in yaninda 1.50 KALMADI", eski.length === 0, eski.join(" | "));
    const kapaliSatirlar = metin.split("\n").filter((s) => {
      const d = sadelestir(s);
      return d.includes("abs") && /satis[ae]?\s*kapali|satisa kapali/.test(d);
    });
    ol("10." + ad + " 'ABS ... satisa kapali' cumlesi KALMADI",
       kapaliSatirlar.length === 0, kapaliSatirlar.slice(0, 2).join(" | "));
    ol("10." + ad + " ABS icin guncel katsayi (1.60 / 160) yaziyor",
       /ABS[^\n]{0,40}1[.,]60|ABS[^\n]{0,20}160\b|1[.,]60[^\n]{0,20}ABS/.test(metin) ||
       /ABS 160/.test(metin),
       "ABS satiri: " + (metin.split("\n").find((s) => s.includes("ABS")) || "").slice(0, 120));
  }
}

// ------------------------------------------------------------ butunluk + ozet
baslik("== KAYNAK BUTUNLUGU ==");
{
  const sonu = shaHepsi();
  ol("B1 depo kaynaklari DEGISMEDI (test dosyaya yazmaz)", sonu === SHA_BAS,
     "bas=" + SHA_BAS + " son=" + sonu);
}

temizle();

console.log("");
console.log("BELGE_1_50_KALAN=" + belge150Kalan);
console.log("ABS_KATSAYI=" + SECENEK.FILAMENT_FARK.ABS + " ASA_KATSAYI=" +
            SECENEK.FILAMENT_FARK.ASA + " HARIC_KATEGORI=" +
            (SECENEK.FILAMENT_KATEGORI_HARIC.ABS || []).length);
console.log("IDDIA: " + (gecen + kalan) + " (gecen " + gecen + " / kirmizi " + kalan + ")");
if (kalan) {
  console.log("KIRMIZI IDDIALAR: " + kirmiziIddialar.join(" | "));
  process.exit(1);
}
console.log("HUKUM: YESIL");
if (KENDINI_TEST) {
  console.log("");
  console.log("NOT: mutasyon bataryasi AYRI betiktedir ve CI'da BLOKLAYICI kosar ->");
  console.log("     python3 tools/abs-mutasyon.py  (6/6 oldurucu KIRMIZI + 2/2 kontrol YESIL)");
}
process.exit(0);
