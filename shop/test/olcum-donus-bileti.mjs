/**
 * PRUVO shop — FANTOM PURCHASE KABUL TESTI (kampanya plani ADIM 1, ArTisT kalemi).
 *
 * OLCULEN KUSUR (onarim oncesi): index.html odemeDonusuIsle() Purchase'i YALNIZCA URL'ye
 * bakarak atiyordu (`?siparis=ok&no=..&t=..`). Odeme iyzico hosted/redirect oldugu icin
 * donus URL'si KANIT DEGILDIR: uydurulabilir, elle acilabilir, yenilenebilir, geri tusuyla
 * tekrarlanabilir. 30 gunluk olcum: piksel 9 satis, D1 gercek 5 — sapma TEK YONLU (piksel >=
 * gercek), yani vazgecilen/basarisiz odemeler de satis sayiliyordu.
 *
 * ONARIM: olay artik SUNUCU HUKMUYLE atilir (shop/src/olcum-bilet.js). Worker, siparisi
 * iyzico retrieve ile dogrulayip 'odendi'ye GERCEKTEN gecirdiginde (changes>0) tek kullanimlik
 * bir bilet uretip AYNI atomik UPDATE icinde durum_gecmisi'ne yazar ve donus URL'sine `&b=`
 * koyar. Tarayici olayi atmadan once POST /olcum-donus ile bileti YAKTIRIR.
 *
 * BU DOSYANIN OLCTUGU UC KABUL VAKASI (ArTisT civisi):
 *   A) Dogrulanmamis donus  -> olay ATILMAZ
 *   B) Dogrulanmis siparis  -> olay BIR KEZ atilir
 *   C) Ayni siparis 2. cagri -> olay ATILMAZ (mukerrer korumasi)
 *
 * KOSUM:  node shop/test/olcum-donus-bileti.mjs        (rc=0 yesil, rc=1 kirmizi)
 * MUTANT: node shop/test/olcum-bilet-mutant.mjs        (dogrulama kolunu bozar, sebebi kanitlar)
 *
 * ⚠️ BU DOSYA AG'A CIKMAZ, D1'E DOKUNMAZ, GERCEK PIKSELE BASMAZ: butun D1 erisimi asagidaki
 * sahteD1() uzerindendir, Meta/GA4 cagrisi HIC yoktur (bilet kolu fetch kullanmaz).
 */

import * as nodeModule from "node:module";
import * as path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP_SRC = path.join(BURASI, "..", "src");

/* Mutant kosumu bu degiskenle BASKA bir olcum-bilet.js kopyasini olcturur (varsayilan: gercek
   kaynak). Boylece mutant harness kaynak dosyayi DEGISTIRMEDEN (repoya iz birakmadan) ayni
   kabul tablosunu mutasyona karsi kosturabilir. */
const MODUL_YOLU = process.env.PRUVO_BILET_MODUL ||
  pathToFileURL(path.join(SHOP_SRC, "olcum-bilet.js")).href;

let gecen = 0;
const kalanlar = [];
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalanlar.push(ad); console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

/* yonet.js (gecmiseEkle = biletin D1'e YAZILDIGI yer) .json import eder; duz node'da cozulsun
   diye olcum.mjs ile AYNI loader hook'u kurulur. FAIL-CLOSED: hook/import patlarsa SUSMAYIZ,
   ilgili kapilar KIRMIZI yanar (bu dosyada "atlandi" diye bir sonuc YOKTUR). */
const JSON_IMPORT_HOOK =
  "export async function resolve(s, c, n) {" +
  "  const r = await n(s, c);" +
  "  return r.url.endsWith('.json')" +
  "    ? { ...r, format: 'json', importAttributes: { type: 'json' } }" +
  "    : r;" +
  "}";

let BILET = null, YONET = null, MODUL_HATA = null;
try {
  if (typeof nodeModule.register === "function") {
    nodeModule.register("data:text/javascript," + encodeURIComponent(JSON_IMPORT_HOOK));
  }
  BILET = await import(MODUL_YOLU);
  YONET = await import(pathToFileURL(path.join(SHOP_SRC, "yonet.js")).href);
} catch (e) {
  MODUL_HATA = (e && e.message) || String(e);
}
if (MODUL_HATA) {
  console.log("\n❌ MODUL YUKLENEMEDI — KAPI OLCUM YAPAMADI: " + MODUL_HATA);
  console.log("   (node " + process.version + ") — bu KIRMIZIDIR, 'atlandi' DEGIL.");
  process.exit(1);
}
const { biletUret, biletDogrula, biletYak } = BILET;
const { gecmiseEkle } = YONET;

/**
 * Sahte D1 — TEK SATIR. SELECT (first) + CAS UPDATE (run) semantigini GERCEGI GIBI uygular:
 * UPDATE ... WHERE siparis_no = ? AND durum_gecmisi = ?  -> durum_gecmisi ESKI HALIYSE yazar
 * (changes=1), degilse YAZMAZ (changes=0). Mukerrer/yaris korumasinin olculdugu yer burasi.
 */
function sahteD1(satir) {
  const iz = { secmeSql: [], guncelleme: 0 };
  // 🔴 ENV BICIMI: biletDogrula(env, ...) `env.KATALOG`'u bekler. Bu sarmalayici ILK YAZIMDA
  // UNUTULMUSTU ve butun cagrilar `sebep="d1-yok"` ile ok:false donuyordu. A blogu (hepsi
  // "ok:false olmali" diyor) o halde de YESIL yaniyordu — yani kapiyi degil, kendi kurulum
  // hatasini olcuyordu. Bunu mutasyon harness'inin KONTROL MUTANTI yakaladi ([[K182]]:
  // "kirmizi geldi" tek basina kanit degil; "yesil geldi" de degil). Tekrarina karsi asagida
  // her A vakasi SEBEBI de dogrular ve T0 global nobetcisi "d1-yok" gorulmesini yasaklar.
  const db = {
    satir,
    iz,
    prepare(sql) {
      return {
        bind(...arg) {
          return {
            async first() {
              iz.secmeSql.push(sql);
              return satir.siparis_no === arg[0] ? { ...satir } : null;
            },
            async run() {
              const [yeni, no, eski] = arg;
              if (satir.siparis_no !== no || satir.durum_gecmisi !== eski) {
                return { meta: { changes: 0 } };
              }
              satir.durum_gecmisi = yeni;
              iz.guncelleme++;
              return { meta: { changes: 1 } };
            },
          };
        },
      };
    },
  };
  // env sozlesmesi: Worker'da `env.KATALOG` D1 baglayicisidir. `iz`/`satir` test gozlemi icin
  // ayni nesnede tasinir (uretim kodu bunlara BAKMAZ).
  return { KATALOG: db, iz, satir };
}

/** Vakanin DOGRU sebeple dustugunu de olc: ok:false YETMEZ, sebep BEKLENEN kol olmali.
 *  (Aksi halde kurulum hatasi / alakasiz bir erken donus vakayi yesil gosterir.) */
function olRed(ad, r, beklenenSebep) {
  ol(ad, r.ok === false && r.sebep === beklenenSebep,
    "ok=" + r.ok + " sebep=" + r.sebep + " (beklenen sebep=" + beklenenSebep + ")");
  return r;
}

/** Bu kosumda gorulen TUM sebepler — T0 nobetcisi kurulum hatasini yakalar. */
const GORULEN_SEBEPLER = [];

/** Gercek akisi taklit et: donus() 'odendi'ye gecerken bileti AYNI gecmise yazar. */
function odenmisSiparis(bilet, ekstra) {
  return {
    siparis_no: "PR-2026-0001",
    durum: "odendi",
    durum_gecmisi: gecmiseEkle("[]", "odendi", { olcumDenendi: true, pikselBileti: bilet }),
    tutar_kurus: 43290,
    kargo_kurus: 4500,
    // Musteri kolonlari BILEREK burada: uc bunlari SELECT ETMEMELI (gizlilik olcumu, blok E).
    musteri_ad: "TEST MUSTERI",
    musteri_tel: "0000000000",
    musteri_eposta: "test@example.invalid",
    musteri_adres: "Test adres",
    ...(ekstra || {}),
  };
}

console.log("\n=== FANTOM PURCHASE — BILET KAPISI (modul: " +
  (process.env.PRUVO_BILET_MODUL ? "MUTANT" : "gercek kaynak") + ") ===");

// ---- 0) BILET URETIMI: tahmin edilemez olmali ------------------------------------
console.log("\n0) Bilet uretimi");
{
  const b1 = biletUret(), b2 = biletUret();
  ol("0a bilet uretiliyor", typeof b1 === "string" && b1.length >= 16, "len=" + (b1 || "").length);
  ol("0b iki bilet FARKLI (sabit/tahmin edilebilir degil)", b1 !== b2);
  ol("0c bilet yalniz [0-9a-f] (bicim sabit)", /^[0-9a-f]+$/.test(b1), b1);
}

// ---- A) DOGRULANMAMIS DONUS -> OLAY ATILMAZ ---------------------------------------
// Bu blok, 9-vs-5 sapmasini URETEN yollarin HER BIRINI ayri ayri kapatir.
console.log("\nA) DOGRULANMAMIS DONUS -> olay ATILMAZ");
{
  const gercek = biletUret();

  // A1: URL UYDURULDU — siparis var, 'odendi' bile, ama bilet uydurma.
  const d1 = sahteD1(odenmisSiparis(gercek));
  const r1 = olRed("A1 uydurma bilet -> ok:false (olay ATILMAZ)",
    await biletDogrula(d1, "PR-2026-0001", "f".repeat(32)), "bilet-yok-veya-yanmis");
  ol("A1b uydurma bilet D1'i DEGISTIRMEDI", d1.iz.guncelleme === 0);

  // A2: BILET HIC YOK (eski tip URL: /?siparis=ok&no=X&t=900000 elle yazilmis).
  const r2 = olRed("A2 bilet YOK -> ok:false",
    await biletDogrula(sahteD1(odenmisSiparis(gercek)), "PR-2026-0001", ""), "bilet-gecersiz");

  // A3: SIPARIS HIC YOK — tamamen uydurma siparis no.
  const r3 = olRed("A3 siparis YOK -> ok:false",
    await biletDogrula(sahteD1(odenmisSiparis(gercek)), "PR-UYDURMA-9999", gercek), "siparis-yok");

  // A4: 🔴 VAZGECILEN/BASARISIZ ODEME — sapmanin ASIL kaynagi. Siparis var, bilet de var
  // gorunuyor ama durum 'odendi' DEGIL (kart reddi / retrieve hatasi / tutar uyusmazligi).
  const r4 = olRed("A4 durum 'basarisiz' -> ok:false (vazgecilen odeme SATIS SAYILMAZ)",
    await biletDogrula(sahteD1(odenmisSiparis(gercek, { durum: "basarisiz" })),
      "PR-2026-0001", gercek), "durum-odendi-degil");
  const r4b = olRed("A4b durum 'incele' -> ok:false (tutar guvenilmez)",
    await biletDogrula(sahteD1(odenmisSiparis(gercek, { durum: "incele" })),
      "PR-2026-0001", gercek), "durum-odendi-degil");

  // A5: 🔴 BILET D1'E HIC YAZILMAMIS. donus() bileti YALNIZ changes>0 halinde yazar; ayni token
  // 2. kez gelince (geri tusu/yenileme) yazilmaz. O halde bilet dogrulanamamalidir.
  const yazilmamis = sahteD1(odenmisSiparis(""));   // gecmiste pb YOK
  const r5 = olRed("A5 bilet D1'e YAZILMAMIS -> ok:false",
    await biletDogrula(yazilmamis, "PR-2026-0001", gercek), "bilet-yok-veya-yanmis");

  // A6: BOS `pb` alani, bos bilet ile ESLESMEMELI (undefined===undefined tuzagi).
  const bosGecmis = sahteD1(odenmisSiparis(""));
  const r6 = olRed("A6 bos bilet, pb'siz kayitla ESLESMEZ",
    await biletDogrula(bosGecmis, "PR-2026-0001", "   "), "bilet-gecersiz");

  GORULEN_SEBEPLER.push(r1.sebep, r2.sebep, r3.sebep, r4.sebep, r4b.sebep, r5.sebep, r6.sebep);
}

// ---- B) DOGRULANMIS SIPARIS -> OLAY BIR KEZ ---------------------------------------
console.log("\nB) DOGRULANMIS SIPARIS -> olay BIR KEZ");
{
  const gercek = biletUret();
  const db = sahteD1(odenmisSiparis(gercek));
  const r = await biletDogrula(db, "PR-2026-0001", gercek);
  ol("B1 gecerli bilet -> ok:true (olay ATILIR)", r.ok === true, "sebep=" + r.sebep);
  ol("B2 value SUNUCUDAN gelir = (tutar + kargo)/100",
    r.value === (43290 + 4500) / 100, "value=" + r.value);
  ol("B3 currency TRY", r.currency === "TRY");
  ol("B4 bilet YAKILDI (D1 guncellendi)", db.iz.guncelleme === 1, "guncelleme=" + db.iz.guncelleme);
  ol("B5 yakilan gecmiste `pb` KALMADI", db.satir.durum_gecmisi.indexOf(gercek) < 0);
  ol("B6 yakma izi `pk` dusuldu", db.satir.durum_gecmisi.indexOf('"pk":1') >= 0);
}

// ---- C) AYNI SIPARIS IKINCI CAGRI -> OLAY ATILMAZ ---------------------------------
console.log("\nC) MUKERRER KORUMASI — ayni siparis 2. cagri");
{
  const gercek = biletUret();
  const db = sahteD1(odenmisSiparis(gercek));
  const birinci = await biletDogrula(db, "PR-2026-0001", gercek);
  const ikinci = await biletDogrula(db, "PR-2026-0001", gercek);
  ol("C1 1. cagri ok:true", birinci.ok === true, "sebep=" + birinci.sebep);
  ol("C2 2. cagri ok:false (sayfa yenileme / geri tusu SATIS SAYMAZ)",
    ikinci.ok === false, "sebep=" + ikinci.sebep);
  const atilan = [birinci, ikinci].filter((x) => x.ok).length;
  ol("C3 TOPLAM atilan olay sayisi = 1 (cift ciro imzasi yok)", atilan === 1, "atilan=" + atilan);

  // C4: ucuncu, dorduncu cagri da atmamali (kalici yanma).
  const ucuncu = await biletDogrula(db, "PR-2026-0001", gercek);
  ol("C4 3. cagri da ok:false", ucuncu.ok === false, "sebep=" + ucuncu.sebep);
}

// ---- D) ESZAMANLILIK: ayni bilet iki paralel istekle -> TEK olay -------------------
console.log("\nD) ESZAMANLILIK (cift sekme / hizli yenileme)");
{
  const gercek = biletUret();
  const db = sahteD1(odenmisSiparis(gercek));
  // Ikisi de AYNI eski gecmisi okur; CAS yalniz birine changes=1 verir.
  const [a, b] = await Promise.all([
    biletDogrula(db, "PR-2026-0001", gercek),
    biletDogrula(db, "PR-2026-0001", gercek),
  ]);
  const atilan = [a, b].filter((x) => x.ok).length;
  ol("D1 es zamanli iki istekten TEK olay atildi", atilan === 1, "atilan=" + atilan);
  ol("D2 D1'e TEK yazma gitti", db.iz.guncelleme === 1, "guncelleme=" + db.iz.guncelleme);
}

// ---- E) GIZLILIK: kisisel veri OKUNMAZ ve DONMEZ ----------------------------------
console.log("\nE) GIZLILIK (kisisel-veri-test.py CI'da bloklayicidir)");
{
  const gercek = biletUret();
  const db = sahteD1(odenmisSiparis(gercek));
  const r = await biletDogrula(db, "PR-2026-0001", gercek);
  const sql = db.iz.secmeSql.join(" ");
  ol("E1 SELECT musteri_ad ISTEMIYOR", sql.indexOf("musteri_ad") < 0);
  ol("E2 SELECT musteri_tel/eposta/adres ISTEMIYOR",
    sql.indexOf("musteri_tel") < 0 && sql.indexOf("musteri_eposta") < 0 &&
    sql.indexOf("musteri_adres") < 0);
  ol("E3 SELECT token ISTEMIYOR (odeme sirri tarayiciya yaklasmaz)", sql.indexOf("token") < 0);
  const metin = JSON.stringify(r);
  ol("E4 cevapta ad/telefon/e-posta/adres YOK",
    metin.indexOf("TEST MUSTERI") < 0 && metin.indexOf("0000000000") < 0 &&
    metin.indexOf("test@example.invalid") < 0 && metin.indexOf("Test adres") < 0, metin);
  ol("E5 cevap alanlari yalniz {ok,sebep,value,currency}",
    Object.keys(r).sort().join(",") === "currency,ok,sebep,value", Object.keys(r).join(","));
}

// ---- F) biletYak birim davranisi ---------------------------------------------------
console.log("\nF) biletYak birim davranisi");
{
  const g = gecmiseEkle("[]", "odendi", { olcumDenendi: true, pikselBileti: "a".repeat(32) });
  const y1 = biletYak(g, "a".repeat(32));
  ol("F1 dogru bilet bulundu", y1.bulundu === true);
  const y2 = biletYak(y1.yeni, "a".repeat(32));
  ol("F2 yanmis bilet TEKRAR bulunmaz", y2.bulundu === false);
  const y3 = biletYak(g, "b".repeat(32));
  ol("F3 yanlis bilet bulunmaz", y3.bulundu === false);
  ol("F4 bulunmayinca gecmis DEGISMEZ", y3.yeni === g);
  const y4 = biletYak("BOZUK-JSON", "a".repeat(32));
  ol("F5 bozuk gecmis JSON'u -> bulunmaz (patlamaz)", y4.bulundu === false);
}

// ---- T0) TAUTOLOJI NOBETCISI -------------------------------------------------------
// 🔴 ILK YAZIMDA GERCEKTEN OLDU: sahteD1() `{KATALOG: ...}` yerine D1'i dogrudan donuyordu,
// biletDogrula her cagrida `d1-yok` ile erken cikiyordu ve "ok:false olmali" diyen A blogu
// TAMAMEN YESIL yaniyordu — kapi hic olculmemisti. Bu nobetci o sinifi kalici olarak kapatir:
// kurulum hatasindan dogan bir reddi, kapinin verdigi red SANMAYALIM.
console.log("\nT0) Tautoloji nobetcisi (A blogu DOGRU sebeple mi redde dusuyor?)");
{
  const kurulumHatasi = GORULEN_SEBEPLER.filter(
    (s) => s === "d1-yok" || s === "siparis-no-gecersiz");
  ol("T0a hicbir A vakasi KURULUM hatasindan (d1-yok) redde dusmedi",
    kurulumHatasi.length === 0, "gorulen=" + JSON.stringify(GORULEN_SEBEPLER));
  ol("T0b A blogu EN AZ 3 FARKLI sebep uretti (tek kola cokmus degil)",
    new Set(GORULEN_SEBEPLER).size >= 3, "sebepler=" + [...new Set(GORULEN_SEBEPLER)].join(","));
}

// ---- SONUC -------------------------------------------------------------------------
console.log("\n=== SONUC: " + gecen + " gecti / " + kalanlar.length + " kaldi ===");
if (kalanlar.length) {
  // Mutant harness bu satirlari okuyup HANGI iddialarin duztugunu karsilastirir.
  console.log("KALAN_IDDIALAR: " + kalanlar.join(" | "));
}
process.exit(kalanlar.length ? 1 : 0);
