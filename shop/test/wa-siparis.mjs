#!/usr/bin/env node
/**
 * PRUVO shop — POST /api/shop/yonet/wa-siparis KABUL TESTLERI (WhatsApp/Ege kanali).
 *
 *   node shop/test/wa-siparis.mjs
 *
 * yonet.js'i DOGRUDAN import eder (wrangler/ag/D1 ISTEMEZ — ref-route.mjs deseni).
 * env.KATALOG mock'lanir; SQL + bind parametreleri yakalanip iddia edilir.
 *
 * KAPSAM (kabul kapisi):
 *   A. YETKI      — anahtarsiz 404, yanlis anahtar 404, EGE_ANAHTAR yalniz BU ucu acar
 *                   (/liste, /durum, /kargo, /stl onunla 404), YONET_ANAHTAR da calisir.
 *   B. YAZMA      — gecerli siparis INSERT olur: siparis_no PR-yyMMdd-HHmmss-XXX,
 *                   kanal='whatsapp', dis_no yazilir, token NULL, durum kurallara uyar.
 *   C. DOGRULAMA  — zorunlu alan eksik/bozuksa 400 + ALAN ADLI hata, INSERT YOK.
 *   D. GORUNURLUK — /liste ayni satiri dondurur: kanal + dis_no + urun linki + WhatsApp
 *                   baski notu (uydurma malzeme onerisi YOK).
 *   E. GERIYE UYUM— (1) kanal/dis_no kolonu YOKKEN /liste ve /durum bugunku gibi calisir
 *                   (kolon merdiveni), (2) YAZMA o halde FAIL-CLOSED 503 verir,
 *                   (3) SITE siparisinde olcum kapisi ACIK kalir (regresyon yok),
 *                   (4) WhatsApp siparisinde 'odendi' gecisi olcum TETIKLEMEZ.
 *   F. IDEMPOTENS — dis_no ZORUNLU (yoksa 400); ayni dis_no ikinci kez -> yeni INSERT
 *                   YOK, mevcut numara doner; SELECT ile INSERT arasindaki YARIS
 *                   (UNIQUE ihlali) 500 DEGIL 200 {tekrar:true} verir.
 *   G. PARA       — KDV kargoyu ICERIR, yuvarlama round'dur (floor DEGIL), kalem
 *                   tutar_kurus/birim_kurus TAM DEGERLE iddia edilir.
 *
 * ONCE-KIRMIZI (elle kanitlanabilir mutasyonlar):
 *   - yonet.js'te EGE_ANAHTAR kolu /liste'ye de aciliyor yapilirsa -> A kirmizi.
 *   - egeAnahtarGecerli'ye `url.searchParams.get("ege_anahtar")` geri konursa -> A kirmizi.
 *   - INSERT'ten `kanal` dusurulurse -> B/D kirmizi.
 *   - waSiparis'te `durum` beyaz listesi kaldirilirsa -> C kirmizi.
 *   - durumDegistir'deki KANAL kapisi silinirse -> E(4) kirmizi.
 *   - kolonMerdiveni kaldirilirsa -> E(1) kirmizi.
 *   - dis_no yeniden OPSIYONEL yapilirsa -> F kirmizi.
 *   - yaris kolu (waKisitlamaIhlali/waTekrarYaniti) silinirse -> F kirmizi.
 *   - KDV `tutarKurus + kargoKurus` yerine `tutarKurus`ten hesaplanirsa -> G kirmizi.
 *   - secenekler.js kdvAyristir'da Math.round -> Math.floor olursa -> G kirmizi.
 *   - waKalemleriCoz'da tutar_kurus <-> birim_kurus takas edilirse -> G kirmizi.
 */

// ---- JSON IMPORT KOPRUSU (test altyapisi, uretim kodunu ETKILEMEZ) -------------
// yonet.js -> semalar.js -> jenerator/urunler/*.json zinciri, JSON'lari import
// ATTRIBUTE'suz alir (`with { type: "json" }` YOK). wrangler/esbuild bunu sorunsuz
// bundle'lar; CIPLAK NODE ise ERR_IMPORT_ATTRIBUTE_MISSING ile duser. semalar.js
// URETILMIS bir dosyadir (tools/sema-bundle-kapisi.py --yaz) — elle degistirilemez.
// Cozum: yalniz BU testin surecinde calisan bir resolve kancasi attribute'u ekler.
// Kanca data: URL olarak gomulur — shop/test/ altinda ikinci bir dosya acilsaydi
// tools/ci-kapsam-test.py onu "kosulmayan kabul testi" sayip CI'yi kirmizi yakardi.
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) { return { ...r, importAttributes: { type: 'json' } }; }" +
  "  return r; }"));
// KDV/adet kurallari TEK KAYNAK: /secenekler.js (IIFE, globalThis.PRUVO_SECENEK'e yazar).
// Worker'da bunu giris dosyasi (index.js) import eder; testte yonet.js'i TEK BASINA
// yukledigimiz icin ayni yan etkiyi burada uretiriz — yoksa KDV dokumu sessizce 0 kalir
// ve test uretimden FARKLI bir davranisi olcerdi.
import { createRequire } from "node:module";
import path from "node:path";
const req = createRequire(import.meta.url);
req(path.join(path.dirname(new URL(import.meta.url).pathname), "..", "..", "secenekler.js"));

const { yonet } = await import("../src/yonet.js");

let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

const YONET_ANAHTAR = "y".repeat(48);
const EGE_ANAHTAR = "e".repeat(48);

// ---------------------------------------------------------------- D1 mock

/**
 * Basit D1 taklidi. secenek:
 *   kolonYok      : true -> kanal/dis_no gecen HER sorgu "no such column: kanal" firlatir
 *   kolonluHata   : kanal/dis_no gecen sorgu "no such column" DISI bir hata firlatir
 *                   (D1 down / bind hatasi taklidi). Kolonsuz kol SAGLAMDIR: merdiven
 *                   hatayi yutup ona duserse istek sessizce basarili olur -> iddia yakalar.
 *   listeSatir    : /liste SELECT'inin dondurecegi satir(lar)
 *   siparis       : siparisGetir SELECT'inin dondurecegi satir
 *   disNoKayit    : dis_no aramasinin dondurecegi satir (idempotens testi)
 *   disNoSirasi   : dis_no aramasinin SIRAYLA dondurecegi satirlar (yaris durumu:
 *                   1. arama null, INSERT patlar, 2. arama satiri bulur). Son eleman
 *                   tukendikten sonra tekrarlanir.
 *   insertCakismasi: true -> `INSERT INTO siparisler` gercek D1 UNIQUE hata metniyle
 *                   firlatir; string verilirse O metinle firlatir (hata-metni saglamligi).
 *
 * `env.denemeler`: DENENEN her INSERT/UPDATE (patlayan dahil). `env.yazmalar`: yalniz
 * BASARIYLA tamamlananlar. Ikisinin ayri olmasi "INSERT denendi ama yazilmadi" halini
 * olculebilir kilar.
 */
function mockEnv(secenek) {
  secenek = secenek || {};
  const sorgular = [];   // {sql, args}
  const yazmalar = [];   // yalniz BASARILI INSERT/UPDATE
  const denemeler = [];  // DENENEN INSERT/UPDATE (patlayan dahil)
  const sayac = { disNoAramasi: 0 };
  const env = {
    sorgular, yazmalar, denemeler, sayac,
    YONET_ANAHTAR: secenek.yonetAnahtar === null ? undefined : YONET_ANAHTAR,
    EGE_ANAHTAR: secenek.egeAnahtar === false ? undefined : EGE_ANAHTAR,
    SITE_URL: "https://ornek-site.test",
    KATALOG: {
      prepare(sql) {
        const kayit = { sql, args: [] };
        const calistir = async (kip) => {
          if (secenek.kolonYok && /\bkanal\b|\bdis_no\b/.test(sql)) {
            throw new Error("D1_ERROR: no such column: kanal");
          }
          // "no such column" DISI D1 arizasi (D1 down / bind hatasi): kolonMerdiveni
          // bunu YUTMAMALI. `kolonluHata` yalniz kolonlu (kanal/dis_no gecen) sorguda
          // patlar; kolonsuz kol calisir durumdadir -> merdiven yanlislikla ona duserse
          // istek SESSIZCE basarili olur ve iddia bunu yakalar.
          if (secenek.kolonluHata && /\bkanal\b|\bdis_no\b/.test(sql)) {
            throw new Error(typeof secenek.kolonluHata === "string"
              ? secenek.kolonluHata : "D1_ERROR: network error while connecting to D1");
          }
          sorgular.push(kayit);
          if (/^\s*(INSERT|UPDATE)/i.test(sql)) {
            denemeler.push(kayit);
            if (secenek.insertCakismasi && /^INSERT INTO siparisler/.test(sql)) {
              throw new Error(typeof secenek.insertCakismasi === "string"
                ? secenek.insertCakismasi
                : "D1_ERROR: UNIQUE constraint failed: siparisler.kanal, " +
                  "siparisler.dis_no: SQLITE_CONSTRAINT_PRIMARYKEY");
            }
            yazmalar.push(kayit);
          }
          if (/FROM siparisler WHERE siparis_no = \?$/.test(sql) ||
              /SELECT 1 AS v FROM siparisler/.test(sql)) {
            // numara benzersizlik on-kontrolu -> daima bos (numara uretilebilsin)
            if (/SELECT 1 AS v/.test(sql)) { return null; }
          }
          if (/WHERE kanal = \? AND dis_no = \?/.test(sql)) {
            sayac.disNoAramasi++;
            if (Array.isArray(secenek.disNoSirasi)) {
              const i = Math.min(sayac.disNoAramasi - 1, secenek.disNoSirasi.length - 1);
              return secenek.disNoSirasi[i] || null;
            }
            return secenek.disNoKayit || null;
          }
          // Baski/parametrik zenginlestirme sorgusu (liste): katalog kaydi YOK varsayimi.
          if (/FROM urunler/.test(sql)) { return { results: [] }; }
          if (/^SELECT siparis_no, tarih, durum, durum_gecmisi/.test(sql)) {
            return secenek.siparis || null;
          }
          if (kip === "all") { return { results: secenek.listeSatir || [] }; }
          if (/^INSERT|^UPDATE/i.test(sql)) { return { meta: { changes: 1 } }; }
          return null;
        };
        return {
          bind(...args) { kayit.args = args; return this; },
          async run() { return calistir("run"); },
          async all() { return calistir("all"); },
          async first() { return calistir("first"); },
        };
      },
    },
  };
  return env;
}

function istek(govde, baslik, method) {
  const H = baslik || {};
  return {
    method: method || "POST",
    headers: { get: (h) => (H[h] !== undefined ? H[h] : null) },
    json: async () => {
      if (govde === "BOZUK") { throw new Error("gecersiz json"); }
      return govde;
    },
  };
}
const URL_BOS = new URL("https://ornek-site.test/api/shop/yonet/wa-siparis");
const ctxSahte = { waitUntil() {} };

function egeBaslik() { return { "X-Ege-Anahtar": EGE_ANAHTAR }; }
function yonetBaslik() { return { "X-Yonet-Anahtar": YONET_ANAHTAR }; }

const GECERLI = {
  dis_no: "PR-260801-110139",
  musteri: { ad: "Test Müşteri", tel: "05451386526", adres: "Örnek Mah. 1/2 Fethiye/Muğla" },
  odeme: "havale",
  urunler: [
    { ad: "Kırık kapı kolu (özel üretim)", link: "https://ornek-site.test/urun/ozel-kol/",
      adet: 2, tutar_kurus: 90000 },
  ],
};

async function cagir(govde, baslik, env, altYol, method) {
  return yonet(istek(govde, baslik, method), env, URL_BOS,
               ctxSahte, altYol || "/wa-siparis", undefined);
}

// ---------------------------------------------------------------- A. YETKI

async function setA() {
  console.log("\nA. YETKI (en az yetki + varlik sizmasi)");
  {
    const env = mockEnv();
    const c = await cagir(GECERLI, {}, env);
    ol("anahtarsiz -> 404", c.status === 404, "kod=" + c.status);
    ol("anahtarsiz -> D1'e yazma YOK", env.yazmalar.length === 0);
  }
  {
    const env = mockEnv();
    const c = await cagir(GECERLI, { "X-Ege-Anahtar": "x".repeat(48) }, env);
    ol("yanlis Ege anahtari -> 404", c.status === 404, "kod=" + c.status);
  }
  {
    const env = mockEnv({ egeAnahtar: false });
    const c = await cagir(GECERLI, egeBaslik(), env);
    ol("EGE_ANAHTAR secret'i tanimsiz -> 404 (fail-closed)", c.status === 404);
  }
  {
    const env = mockEnv();
    const c = await cagir(GECERLI, egeBaslik(), env);
    ol("gecerli Ege anahtari -> 201", c.status === 201, "kod=" + c.status);
  }
  {
    const env = mockEnv();
    const c = await cagir(GECERLI, yonetBaslik(), env);
    ol("yonetim anahtari da calisir -> 201", c.status === 201, "kod=" + c.status);
  }
  // EN AZ YETKI: Ege anahtari BASKA hicbir ucu acmaz.
  // NOT: panel KOKU ("/", GET) bu listede DEGIL — cunku main'de yetkisiz `GET /yonet`
  // artik 404 degil 200 SIFRE KUTUSU (cerez oturumu gecisi). Kok icin duz bir kod
  // beklentisi yerine ASIL NIYETI olcen ayri bir blok var (asagida): Ege anahtari
  // anonimden FAZLA hicbir sey almiyor. Iddia zayiflatilmadi, GUCLENDIRILDI.
  for (const [yol, yontem] of [["/liste", "GET"], ["/durum", "POST"], ["/kargo", "POST"],
                               ["/stl", "GET"], ["/stl-liste", "GET"]]) {
    const env = mockEnv();
    const c = await yonet(istek({}, egeBaslik(), yontem), env,
                          new URL("https://ornek-site.test/api/shop/yonet" + yol),
                          ctxSahte, yol, undefined);
    ol("Ege anahtari " + yol + " (" + yontem + ") ucunu ACMAZ -> 404", c.status === 404,
       "kod=" + c.status);
  }
  {
    // GET /wa-siparis: yalniz POST kabul -> Ege anahtariyla bile 404.
    const env = mockEnv();
    const c = await yonet(istek({}, egeBaslik(), "GET"), env, URL_BOS, ctxSahte,
                          "/wa-siparis", undefined);
    ol("GET /wa-siparis -> 404 (yalniz POST)", c.status === 404, "kod=" + c.status);
  }
  // ---- PANEL KOKU: Ege anahtari anonimden FAZLA hicbir sey ALMIYOR ----------------
  // main (`9716c204`+`59914f0a`) yetkisiz `GET /yonet`i 404'ten 200 sifre kutusuna
  // cevirdi; bu bilincli ve kendi mutasyon bataryasiyla korunuyor. Dalin ESKI "-> 404"
  // beklentisi bayatti. Ama dalin NIYETI (Ege anahtari paneli ACMASIN) hala gecerli, o
  // yuzden beklenti "200'e cevrildi" diye tek satirda gecistirilmiyor; niyet UC AYRI
  // eksende olculuyor. Ayirt edici mutant: "Ege anahtari `anahtarGecerli`yi true yapar".
  {
    const kokUrl = new URL("https://ornek-site.test/api/shop/yonet/");
    const envAnonim = mockEnv();
    const cAnonim = await yonet(istek({}, {}, "GET"), envAnonim, kokUrl, ctxSahte, "/", undefined);
    const envEge = mockEnv();
    const cEge = await yonet(istek({}, egeBaslik(), "GET"), envEge, kokUrl, ctxSahte, "/", undefined);
    const govdeEge = await cEge.text();

    // (1) AYNI SINIF: Ege anahtarli yanit anonim yanitla ayni -> anahtar FAZLADAN yetki vermiyor.
    ol("KOK: Ege anahtarli GET / yaniti ANONIM yanitla AYNI kodda (fazladan yetki YOK)",
       cEge.status === cAnonim.status && cEge.status === 200,
       "ege=" + cEge.status + " anonim=" + cAnonim.status);

    // (2) YETKILI VERI YOK: giris ekraninda panel govdesi / siparis verisi / PII bulunmaz.
    ol("KOK: Ege anahtarli yanitta YETKILI VERI YOK (siparis/PII/panel govdesi)",
       !/siparis_no|musteri_tel|kalemler|durum_gecmisi/.test(govdeEge));
    ol("KOK: Ege anahtarli yanitta D1'e okuma/yazma YOK",
       envEge.yazmalar.length === 0 && envEge.sorgular.length === 0);

    // (3) anahtarGecerli FALSE: yanit SIFRE KUTUSU, PANEL DEGIL. `anahtarGecerli` true
    // olsaydi kod `sayfa()`yi (SAYFA_HTML) dondururdu; ayirt edici isaret basliktir —
    // giris ekrani bilerek ipucusuz ("PRUVO"), panel "Sipariş Yönetimi" diyor.
    ol("KOK: yanit SIFRE KUTUSU (anahtarGecerli Ege basliginda FALSE)",
       /type="password"/.test(govdeEge));
    ol("KOK: yanit PANEL DEGIL (baslikta 'Sipariş Yönetimi' ipucu YOK)",
       !/Sipariş Yönetimi/.test(govdeEge));
  }
  // ---- OZELLIK-KAPALI: YONET_ANAHTAR yoksa YAZMA YOLU da KAPALI ------------------
  // Kapi sirasi iddiasi: `if (!env.YONET_ANAHTAR) return yon404()` /wa-siparis blogunun
  // ONUNDE durur. Ayarlanmamis bir secret'in arkasinda acik kalan bir yazma ucu bu
  // depodaki sessiz-hata sinifidir -> supheda KAPALI taraf. Ayirt edici mutant: kapiyi
  // /wa-siparis blogunun ARKASINA tasi; bu blok tek basina KIRMIZI yanar.
  {
    const env = mockEnv({ yonetAnahtar: null });
    const c = await cagir(GECERLI, egeBaslik(), env);
    ol("OZELLIK KAPALI: YONET_ANAHTAR yokken gecerli Ege anahtariyla bile -> 404",
       c.status === 404, "kod=" + c.status);
    ol("OZELLIK KAPALI: YONET_ANAHTAR yokken INSERT YOK (yazma yolu da kapali)",
       env.yazmalar.length === 0 && env.denemeler.length === 0);
  }
  // ANAHTAR SIZINTISI: query param yolu KAPALI. URL'ler Cloudflare erisim loglarina,
  // referrer'a ve proxy kayitlarina duz metin girer; basliklar girmez. DOGRU anahtari
  // ?ege_anahtar= ile vermek ARTIK yetmemeli.
  {
    const env = mockEnv();
    const urlParamli = new URL("https://ornek-site.test/api/shop/yonet/wa-siparis" +
                               "?ege_anahtar=" + EGE_ANAHTAR);
    const c = await yonet(istek(GECERLI, {}, "POST"), env, urlParamli, ctxSahte,
                          "/wa-siparis", undefined);
    ol("DOGRU anahtar ?ege_anahtar= query param'inda -> 404 (baslik ZORUNLU)",
       c.status === 404, "kod=" + c.status);
    ol("query param anahtariyla INSERT YOK", env.yazmalar.length === 0);
  }
  {
    // Ayni URL + DOGRU baslik -> 201: yukaridaki 404 "URL bozuk" degil, ANAHTAR
    // YOLUNUN kapali olmasindan geliyor (kontrol kolu).
    const env = mockEnv();
    const urlParamli = new URL("https://ornek-site.test/api/shop/yonet/wa-siparis" +
                               "?ege_anahtar=" + EGE_ANAHTAR);
    const c = await yonet(istek(GECERLI, egeBaslik(), "POST"), env, urlParamli, ctxSahte,
                          "/wa-siparis", undefined);
    ol("ayni URL + X-Ege-Anahtar basligi -> 201 (kontrol kolu)", c.status === 201,
       "kod=" + c.status);
  }
}

// ---------------------------------------------------------------- B. YAZMA

const NO_KALIBI = /^PR-\d{6}-\d{6}-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{3}$/;

async function setB() {
  console.log("\nB. YAZMA (siparis kaydi + ID semasi)");
  const env = mockEnv();
  const c = await cagir(GECERLI, egeBaslik(), env);
  const govde = JSON.parse(await c.text());
  ol("201 + ok:true", c.status === 201 && govde.ok === true);
  ol("siparis_no PANEL semasinda (PR-yyMMdd-HHmmss-XXX)", NO_KALIBI.test(govde.siparis_no),
     govde.siparis_no);
  ol("Ege'nin kendi numarasi siparis_no OLARAK ALINMADI",
     govde.siparis_no !== GECERLI.dis_no);
  ol("dis_no yanitta korunur", govde.dis_no === "PR-260801-110139");
  ol("kanal yanitta 'whatsapp'", govde.kanal === "whatsapp");

  const ins = env.yazmalar.filter((y) => /^INSERT INTO siparisler/.test(y.sql));
  ol("TEK INSERT", ins.length === 1, "adet=" + ins.length);
  const sql = ins[0] ? ins[0].sql : "";
  const args = ins[0] ? ins[0].args : [];
  ol("INSERT kanal + dis_no kolonlarini tasir", /kanal, dis_no\)/.test(sql));
  ol("token NULL yazilir (iyzico donusu bu satiri bulamaz)", /\(\?, NULL, /.test(sql));
  ol("bind: kanal='whatsapp'", args.includes("whatsapp"));
  ol("bind: dis_no", args.includes("PR-260801-110139"));
  ol("bind: durum varsayilani 'havale-bekliyor'", args[2] === "havale-bekliyor");
  ol("bind: odeme_yontemi='havale'", args[6] === "havale");
  ol("bind: tutar kalemlerden toplanir (90000)", args[3] === 90000);
  ol("bind: KDV dokumu hesaplanir (0 DEGIL)", args[5] > 0, "kdv=" + args[5]);
  ol("bind: musteri ad/tel/adres", args[8] === "Test Müşteri" &&
     args[9] === "05451386526" && args[11].startsWith("Örnek Mah."));
  ol("bind: eposta verilmediyse ''", args[10] === "");
  const satirlar = JSON.parse(args[7]);
  ol("kalem katalog id'sini LINKTEN turetir", satirlar[0].id === "ozel-kol", satirlar[0].id);
  ol("kalem linki satirda saklanir", satirlar[0].url === GECERLI.urunler[0].link);
  ol("kalem kanal isareti tasir", satirlar[0].kanal === "whatsapp");
  ol("kalem malzeme/renk BOS (uydurma beyan yok)",
     satirlar[0].malzeme === "" && satirlar[0].renk === "");
  const gecmis = JSON.parse(args[12]);
  ol("durum gecmisi ilk kaydi yazilir", Array.isArray(gecmis) && gecmis[0].d === "havale-bekliyor");

  // 'odendi' de yazilabilir; kargolandi/tamamlandi YAZILAMAZ.
  {
    const e2 = mockEnv();
    const c2 = await cagir({ ...GECERLI, dis_no: "WA-ODENDI-1", durum: "odendi" },
                           egeBaslik(), e2);
    ol("durum='odendi' kabul", c2.status === 201, "kod=" + c2.status);
  }
  {
    const e3 = mockEnv();
    const c3 = await cagir({ ...GECERLI, durum: "kargolandi" }, egeBaslik(), e3);
    ol("durum='kargolandi' RED (takip kodsuz kargo damgasi uretilemez)", c3.status === 400);
    ol("red edilen istekte INSERT YOK", e3.yazmalar.length === 0);
  }
  // Link YOKSA sentetik id "wa-" onekli olur (katalog id'siyle carpismaz).
  {
    const e4 = mockEnv();
    await cagir({ ...GECERLI, dis_no: "WA-LINKSIZ-1",
                  urunler: [{ ad: "Bulaşık makinesi sepet tekerleği", adet: 1 }] },
                egeBaslik(), e4);
    const s = JSON.parse(e4.yazmalar[0].args[7]);
    ol("linksiz kalem id'si 'wa-' onekli", s[0].id.startsWith("wa-"), s[0].id);
    ol("sentetik id yalniz [a-z0-9-]", /^[a-z0-9-]+$/.test(s[0].id), s[0].id);
  }
}

// ---------------------------------------------------------------- C. DOGRULAMA

async function setC() {
  console.log("\nC. DOGRULAMA (zorunlu alan / bicim)");
  const durumlar = [
    ["bozuk JSON", "BOZUK", "gecersiz-json"],
    ["musteri adi yok", { ...GECERLI, musteri: { tel: "05451386526", adres: "Adres 1" } }, "musteri-ad"],
    ["telefon kisa", { ...GECERLI, musteri: { ...GECERLI.musteri, tel: "0545" } }, "musteri-tel"],
    ["adres yok", { ...GECERLI, musteri: { ad: "Ad Soyad", tel: "05451386526" } }, "musteri-adres"],
    ["eposta bozuk", { ...GECERLI, musteri: { ...GECERLI.musteri, eposta: "abc-def" } }, "musteri-eposta"],
    ["odeme yontemi yok", { ...GECERLI, odeme: undefined }, "gecersiz-odeme"],
    ["odeme yontemi taninmiyor", { ...GECERLI, odeme: "kripto" }, "gecersiz-odeme"],
    ["urun listesi bos", { ...GECERLI, urunler: [] }, "gecersiz-urunler"],
    ["urun adi yok", { ...GECERLI, urunler: [{ adet: 1 }] }, "urun-ad"],
    ["urun linki https degil", { ...GECERLI, urunler: [{ ad: "Parça", link: "javascript:alert(1)" }] }, "urun-link"],
    ["adet 0", { ...GECERLI, urunler: [{ ad: "Parça", adet: 0 }] }, "urun-adet"],
    ["adet 100", { ...GECERLI, urunler: [{ ad: "Parça", adet: 100 }] }, "urun-adet"],
    ["tutar ondalikli (kurus tamsayi degil)", { ...GECERLI, tutar_kurus: 12.5 }, "gecersiz-tutar"],
    ["tutar negatif", { ...GECERLI, tutar_kurus: -1 }, "gecersiz-tutar"],
    ["dis_no bicimsiz", { ...GECERLI, dis_no: "PR 260801 / 110139" }, "gecersiz-dis-no"],
    // dis_no ZORUNLU (idempotens anahtari) — uc bicimde de "yok" sayilir.
    ["dis_no hic verilmemis", { ...GECERLI, dis_no: undefined }, "dis-no-yok"],
    ["dis_no bos string", { ...GECERLI, dis_no: "" }, "dis-no-yok"],
    ["dis_no null", { ...GECERLI, dis_no: null }, "dis-no-yok"],
    ["dis_no 3 karakterden kisa", { ...GECERLI, dis_no: "ab" }, "gecersiz-dis-no"],
    ["dis_no 40 karakterden uzun", { ...GECERLI, dis_no: "A".repeat(41) }, "gecersiz-dis-no"],
    ["durum beyaz liste disi", { ...GECERLI, durum: "tamamlandi" }, "gecersiz-durum"],
  ];
  for (const [ad, govde, beklenen] of durumlar) {
    const env = mockEnv();
    const c = await cagir(govde, egeBaslik(), env);
    const j = JSON.parse(await c.text());
    ol(ad + " -> 400 " + beklenen, c.status === 400 && j.hata === beklenen,
       "kod=" + c.status + " hata=" + j.hata);
    ol(ad + " -> INSERT YOK", env.yazmalar.length === 0);
  }
  // Tutar OPSIYONEL: hic tutar yoksa da siparis acilir (Okan elle fiyatlandirir).
  {
    const env = mockEnv();
    const c = await cagir({ ...GECERLI, dis_no: "WA-TUTARSIZ-1", tutar_kurus: undefined,
                            urunler: [{ ad: "Ölçüye özel parça" }] }, egeBaslik(), env);
    ol("tutar BOS -> 201 (fiyat sonra elle girilir)", c.status === 201, "kod=" + c.status);
    ol("tutar BOS -> tutar_kurus 0 yazilir", env.yazmalar[0].args[3] === 0);
  }
}

// ---------------------------------------------------------------- D. GORUNURLUK

async function setD() {
  console.log("\nD. GORUNURLUK (/liste ayni kaydi dondurur)");
  const satir = {
    id: 7, siparis_no: "PR-260801-110200-ABC", tarih: "2026-08-01T11:02:00.000Z",
    durum: "havale-bekliyor", tutar_kurus: 90000, kargo_kurus: 0, kdv_kurus: 15000,
    odeme_yontemi: "havale", kargo_firma: "", kargo_kodu: "", durum_gecmisi: "[]",
    musteri_ad: "Test Müşteri", musteri_tel: "05451386526", musteri_eposta: "",
    musteri_adres: "Örnek Mah. 1/2",
    kanal: "whatsapp", dis_no: "PR-260801-110139",
    urunler: JSON.stringify([{ id: "wa-ozel-parca", baslik: "Kırık kapı kolu",
      malzeme: "", renk: "", adet: 2, kanal: "whatsapp",
      url: "https://ornek-site.test/urun/ozel-kol/" }]),
  };
  const env = mockEnv({ listeSatir: [satir] });
  const c = await yonet(istek(null, yonetBaslik(), "GET"), env,
                        new URL("https://ornek-site.test/api/shop/yonet/liste"),
                        ctxSahte, "/liste", undefined);
  const j = JSON.parse(await c.text());
  const s = j.siparisler[0];
  ol("/liste 200", c.status === 200);
  ol("kanal alani doner", s.kanal === "whatsapp");
  ol("dis_no alani doner", s.dis_no === "PR-260801-110139");
  ol("kalem urun_url'i KALEM LINKI olur", s.kalemler[0].urun_url ===
     "https://ornek-site.test/urun/ozel-kol/", s.kalemler[0].urun_url);
  ol("baski notu WhatsApp'a ozel (uydurma malzeme onerisi YOK)",
     /WhatsApp siparişi/.test(s.kalemler[0].baski_oneri) &&
     !/doluluk/.test(s.kalemler[0].baski_oneri), s.kalemler[0].baski_oneri);

  // SITE siparisi: kanal 'site' + link yok -> bugunku davranis (urun sayfasi linki).
  const siteSatir = { ...satir, kanal: "site", dis_no: "",
    urunler: JSON.stringify([{ id: "kapi-kolu", baslik: "Kapı kolu", malzeme: "PETG",
      renk: "Siyah", adet: 1 }]) };
  const env2 = mockEnv({ listeSatir: [siteSatir] });
  const c2 = await yonet(istek(null, yonetBaslik(), "GET"), env2,
                         new URL("https://ornek-site.test/api/shop/yonet/liste"),
                         ctxSahte, "/liste", undefined);
  const s2 = JSON.parse(await c2.text()).siparisler[0];
  ol("SITE siparisi urun_url'i DEGISMEDI",
     s2.kalemler[0].urun_url === "https://ornek-site.test/urun/kapi-kolu/",
     s2.kalemler[0].urun_url);
  ol("SITE siparisi baski onerisi DEGISMEDI (PETG fallback)",
     /PETG|doluluk/.test(s2.kalemler[0].baski_oneri), s2.kalemler[0].baski_oneri);
}

// ---------------------------------------------------------------- E. GERIYE UYUM

async function setE() {
  console.log("\nE. GERIYE UYUM (goc kosmadan once + site akisi regresyonu)");
  // (1) kanal/dis_no kolonu YOKKEN /liste calismaya devam eder (kolon merdiveni).
  {
    const satir = {
      id: 3, siparis_no: "PR-260731-101010-XYZ", tarih: "2026-07-31T10:10:10.000Z",
      durum: "odendi", tutar_kurus: 50000, kargo_kurus: 25000, kdv_kurus: 12500,
      odeme_yontemi: "kart", kargo_firma: "", kargo_kodu: "", durum_gecmisi: "[]",
      musteri_ad: "A", musteri_tel: "0", musteri_eposta: "", musteri_adres: "B",
      urunler: JSON.stringify([{ id: "kapi-kolu", baslik: "Kapı kolu", malzeme: "PLA",
        renk: "Beyaz", adet: 1 }]),
    };
    const env = mockEnv({ kolonYok: true, listeSatir: [satir] });
    const c = await yonet(istek(null, yonetBaslik(), "GET"), env,
                          new URL("https://ornek-site.test/api/shop/yonet/liste"),
                          ctxSahte, "/liste", undefined);
    const j = JSON.parse(await c.text());
    ol("kolon YOKKEN /liste 200 (panel dusmuyor)", c.status === 200, "kod=" + c.status);
    ol("kolon YOKKEN kanal 'site' varsayilanina duser", j.siparisler[0].kanal === "site");
    ol("kolon YOKKEN dis_no ''", j.siparisler[0].dis_no === "");
  }
  // (1b) 🔴 MERDIVEN YALNIZ "no such column" YUTAR — baska hata YUKARI FIRLAR.
  // USTA denetiminde bulundu: yonet.js'teki bu yorum NOBETCISIZDI. `if (false) { throw e; }`
  // mutantiyla merdiven HER hatayi yutuyordu ve hem dar test hem genis tur YESIL kaliyordu.
  // Sonucu sessiz KORLUK: gercek bir D1 arizasinda /liste hata vermeden kolonsuz sorguya
  // duser, panel kanal rozetsiz liste basar ve kimse arizadan haberdar olmaz.
  {
    const satir = { id: 9, siparis_no: "PR-260731-101011-QWE",
      tarih: "2026-07-31T10:10:11.000Z", durum: "odendi", tutar_kurus: 1000,
      kargo_kurus: 0, kdv_kurus: 0, odeme_yontemi: "kart", kargo_firma: "",
      kargo_kodu: "", durum_gecmisi: "[]", musteri_ad: "A", musteri_tel: "0",
      musteri_eposta: "", musteri_adres: "B", urunler: "[]" };
    const env = mockEnv({ kolonluHata: true, listeSatir: [satir] });
    let yakalanan = null;
    try {
      await yonet(istek(null, yonetBaslik(), "GET"), env,
                  new URL("https://ornek-site.test/api/shop/yonet/liste"),
                  ctxSahte, "/liste", undefined);
    } catch (e) { yakalanan = e; }
    ol("merdiven: 'no such column' DISI D1 hatasi YUKARI FIRLAR (yutulmaz)", !!yakalanan);
    ol("merdiven: firlatilan hata ORIJINAL D1 hatasi",
       !!yakalanan && /network error/.test(String(yakalanan && yakalanan.message)),
       String(yakalanan && yakalanan.message).slice(0, 90));
    ol("merdiven: hata yutulup KOLONSUZ kola DUSULMEDI (kolonsuz sorgu hic kosmadi)",
       !env.sorgular.some((s) => /FROM siparisler/.test(s.sql) && !/\bkanal\b/.test(s.sql)),
       "sorgu=" + env.sorgular.length);
  }
  // (2) kolon YOKKEN yazma FAIL-CLOSED (sessizce kanalsiz kayit acilmaz).
  {
    const env = mockEnv({ kolonYok: true });
    const c = await cagir(GECERLI, egeBaslik(), env);
    const j = JSON.parse(await c.text());
    ol("kolon YOKKEN /wa-siparis 503", c.status === 503, "kod=" + c.status);
    ol("kolon YOKKEN hata 'sema-goc-gerekli'", j.hata === "sema-goc-gerekli");
    ol("kolon YOKKEN INSERT YOK", env.yazmalar.length === 0);
  }
  // (3) SITE siparisinde 'havale-bekliyor' -> 'odendi' olcumu HALA tetiklenir.
  {
    const env = mockEnv({ siparis: { siparis_no: "PR-1", durum: "havale-bekliyor",
      durum_gecmisi: "[]", urunler: "[]", tutar_kurus: 1000, kargo_kurus: 0, kdv_kurus: 0,
      odeme_yontemi: "havale", atif: "", tarih: "2026-08-01T00:00:00.000Z",
      musteri_ad: "A", musteri_eposta: "", musteri_adres: "B", kanal: "site" } });
    const c = await yonet(istek({ siparis_no: "PR-1", durum: "odendi" }, yonetBaslik(), "POST"),
                          env, new URL("https://ornek-site.test/api/shop/yonet/durum"),
                          ctxSahte, "/durum", undefined);
    ol("SITE: odendi gecisi 200", c.status === 200, "kod=" + c.status);
    const upd = env.yazmalar.find((y) => /^UPDATE siparisler SET durum/.test(y.sql));
    ol("SITE: olcum izi {\"o\":1} YAZILIR (regresyon yok)",
       !!upd && /"o":1/.test(upd.args[1]), upd && upd.args[1]);
  }
  // (4) WHATSAPP siparisinde ayni gecis olcum TETIKLEMEZ.
  {
    const env = mockEnv({ siparis: { siparis_no: "PR-2", durum: "havale-bekliyor",
      durum_gecmisi: "[]", urunler: "[]", tutar_kurus: 1000, kargo_kurus: 0, kdv_kurus: 0,
      odeme_yontemi: "havale", atif: "", tarih: "2026-08-01T00:00:00.000Z",
      musteri_ad: "A", musteri_eposta: "", musteri_adres: "B", kanal: "whatsapp" } });
    const c = await yonet(istek({ siparis_no: "PR-2", durum: "odendi" }, yonetBaslik(), "POST"),
                          env, new URL("https://ornek-site.test/api/shop/yonet/durum"),
                          ctxSahte, "/durum", undefined);
    ol("WHATSAPP: odendi gecisi yine 200 (durum ilerler)", c.status === 200, "kod=" + c.status);
    const upd = env.yazmalar.find((y) => /^UPDATE siparisler SET durum/.test(y.sql));
    ol("WHATSAPP: olcum izi {\"o\":1} YAZILMAZ (GA4/Meta'ya gitmez)",
       !!upd && !/"o":1/.test(upd.args[1]), upd && upd.args[1]);
  }
  // (5) kanal kolonu YOKKEN /durum bugunku gibi olcer (merdiven -> kapi ACIK).
  {
    const env = mockEnv({ kolonYok: true, siparis: { siparis_no: "PR-3",
      durum: "havale-bekliyor", durum_gecmisi: "[]", urunler: "[]", tutar_kurus: 1000,
      kargo_kurus: 0, kdv_kurus: 0, odeme_yontemi: "havale", atif: "",
      tarih: "2026-08-01T00:00:00.000Z", musteri_ad: "A", musteri_eposta: "",
      musteri_adres: "B" } });
    const c = await yonet(istek({ siparis_no: "PR-3", durum: "odendi" }, yonetBaslik(), "POST"),
                          env, new URL("https://ornek-site.test/api/shop/yonet/durum"),
                          ctxSahte, "/durum", undefined);
    const upd = env.yazmalar.find((y) => /^UPDATE siparisler SET durum/.test(y.sql));
    ol("kolon YOKKEN /durum 200 + olcum izi yazilir", c.status === 200 &&
       !!upd && /"o":1/.test(upd.args[1]), "kod=" + c.status);
  }
}

// ---------------------------------------------------------------- F. IDEMPOTENS

// Mevcut satir fikstürlerinde `musteri_tel` ARTIK ZORUNLU: idempotent yanit yalniz
// AYNI musteriye verilir (capraz-musteri savunmasi, waMevcutYaniti).
const TEL = "05451386526";              // GECERLI.musteri.tel'in normallesmis hali
const BASKA_TEL = "05321112233";

async function setF() {
  console.log("\nF. IDEMPOTENS (Ege yeniden denerse ikiz siparis olusmaz)");
  const env = mockEnv({ disNoKayit: { siparis_no: "PR-260801-110200-ABC",
                                      durum: "havale-bekliyor", musteri_tel: TEL } });
  const c = await cagir(GECERLI, egeBaslik(), env);
  const j = JSON.parse(await c.text());
  ol("ayni dis_no -> 200 (201 DEGIL)", c.status === 200, "kod=" + c.status);
  ol("mevcut siparis numarasi doner", j.siparis_no === "PR-260801-110200-ABC");
  ol("tekrar isareti", j.tekrar === true);
  ol("ikinci INSERT YOK", env.yazmalar.length === 0, "yazma=" + env.yazmalar.length);

  // ---- (F2) dis_no'SUZ CAGRI ARTIK ACILMIYOR --------------------------------------
  // 🔴 IDDIA TERSINE CEVRILDI (KraL denetimi). ESKI test "dis_no yoksa yeni siparis
  // acilir (201)" diyerek SINIRSIZ MUKERRER SIPARISI KURAL sayiyordu: dis_no'suz N cagri
  // = N ayri siparis, hicbir tekillik anahtari yok, kismi UNIQUE indeks de (WHERE
  // dis_no <> '') o satirlari kapsamiyor. Ege'nin agi koptugunda panelde ikiz siparis
  // olusuyordu. Artik uc dis_no'yu ZORUNLU tutar.
  {
    const env2 = mockEnv({ disNoKayit: { siparis_no: "X", durum: "odendi" } });
    const c2 = await cagir({ ...GECERLI, dis_no: undefined }, egeBaslik(), env2);
    const j2 = JSON.parse(await c2.text());
    ol("dis_no YOKSA siparis ACILMAZ -> 400 dis-no-yok",
       c2.status === 400 && j2.hata === "dis-no-yok", "kod=" + c2.status + " hata=" + j2.hata);
    ol("dis_no YOKSA INSERT YOK", env2.yazmalar.length === 0,
       "yazma=" + env2.yazmalar.length);
  }
  // MUKERRER OLCUMU: dis_no'suz 4 art arda cagri -> 0 INSERT (eskiden 4 INSERT idi).
  {
    const env3 = mockEnv();
    for (let i = 0; i < 4; i++) {
      await cagir({ ...GECERLI, dis_no: undefined }, egeBaslik(), env3);
    }
    ol("dis_no'suz 4 cagri -> 0 INSERT (eskiden 4 idi)", env3.yazmalar.length === 0,
       "insert=" + env3.yazmalar.length);
  }
  // AYNI dis_no ile 4 art arda cagri -> tek INSERT, kalan 3'u idempotent 200.
  {
    const env4 = mockEnv({ disNoSirasi: [null, { siparis_no: "PR-260801-110300-QWE",
                                                 durum: "havale-bekliyor",
                                                 musteri_tel: TEL }] });
    const kodlar = [];
    for (let i = 0; i < 4; i++) {
      const c4 = await cagir(GECERLI, egeBaslik(), env4);
      kodlar.push(c4.status);
    }
    const ins4 = env4.yazmalar.filter((y) => /^INSERT INTO siparisler/.test(y.sql));
    ol("ayni dis_no 4 cagri -> TEK INSERT", ins4.length === 1, "insert=" + ins4.length);
    ol("ayni dis_no 4 cagri -> kodlar 201,200,200,200",
       kodlar.join(",") === "201,200,200,200", kodlar.join(","));
  }

  // ---- (F3) YARIS DURUMU (TOCTOU) -------------------------------------------------
  // On-SELECT bos donduktan SONRA baska bir cagri ayni dis_no ile yazdi -> INSERT
  // kismi UNIQUE indekse takilir. BEYAN EDILEN sozlesme: 200 {tekrar:true, siparis_no}.
  // ESKIDEN: hata yakalanmiyordu -> index.js genel catch -> 500 sunucu-hatasi.
  {
    const env5 = mockEnv({
      insertCakismasi: true,
      disNoSirasi: [null, { siparis_no: "PR-260801-110400-RTY", durum: "odendi",
                            musteri_tel: TEL }],
    });
    const c5 = await cagir(GECERLI, egeBaslik(), env5);
    const j5 = JSON.parse(await c5.text());
    ol("YARIS: UNIQUE ihlali -> 200 (500 DEGIL)", c5.status === 200, "kod=" + c5.status);
    ol("YARIS: tekrar:true", j5.tekrar === true);
    ol("YARIS: rakibin actigi siparis numarasi doner",
       j5.siparis_no === "PR-260801-110400-RTY", j5.siparis_no);
    ol("YARIS: rakibin durumu doner", j5.durum === "odendi", j5.durum);
    ol("YARIS: kanal + dis_no yanitta",
       j5.kanal === "whatsapp" && j5.dis_no === GECERLI.dis_no);
    ol("YARIS: INSERT DENENDI ama yazilmadi",
       env5.denemeler.filter((y) => /^INSERT INTO siparisler/.test(y.sql)).length === 1 &&
       env5.yazmalar.length === 0,
       "deneme=" + env5.denemeler.length + " yazma=" + env5.yazmalar.length);
    ol("YARIS: kurtarma SELECT'i kosuldu (2 dis_no aramasi)",
       env5.sayac.disNoAramasi === 2, "arama=" + env5.sayac.disNoAramasi);
  }
  // Hata metni BASKA sekilde gelirse de calisir (D1 metnine string-bagimli olmayalim).
  {
    const env6 = mockEnv({
      insertCakismasi: "D1_ERROR: SQLITE_CONSTRAINT: constraint failed",
      disNoSirasi: [null, { siparis_no: "PR-260801-110500-UIO", durum: "havale-bekliyor",
                            musteri_tel: TEL }],
    });
    const c6 = await cagir(GECERLI, egeBaslik(), env6);
    ol("YARIS: farkli D1 hata metniyle de 200", c6.status === 200, "kod=" + c6.status);
  }
  // 🔴 KARSI KOL: kisitlama hatasi geldi AMA satir GERCEKTEN YOK -> 200 UYDURULMAZ.
  // (Yaris kolu "her kisitlama hatasini 200 yap" demek DEGIL; kanit SELECT'i sart.)
  // ⚠️ "firlatti mi" DEMEK YETMEZ: kanit kolu atlanirsa waTekrarYaniti(null) da
  // firlatir (TypeError) ve iddia yesil kalirdi — olculdu, mutant kacmisti. Bu yuzden
  // ORIJINAL D1 hatasinin AYNEN yukari ciktigini iddia ediyoruz.
  {
    const env7 = mockEnv({ insertCakismasi: true, disNoSirasi: [null, null] });
    let yakalanan7 = null;
    try { await cagir(GECERLI, egeBaslik(), env7); } catch (e) { yakalanan7 = e; }
    ol("YARIS: satir yoksa hata YUTULMAZ (yeniden firlatilir -> 500 kalir)", !!yakalanan7);
    ol("YARIS: firlatilan hata ORIJINAL D1 hatasi (TypeError degil)",
       !!yakalanan7 && /UNIQUE constraint failed/.test(String(yakalanan7 && yakalanan7.message)),
       String(yakalanan7 && yakalanan7.message).slice(0, 90));
  }
  // 🔴 KARSI KOL: kisitlama DISI bir hata 200'e cevrilmez — ve AYNEN yukari cikar.
  {
    const env8 = mockEnv({ insertCakismasi: "D1_ERROR: network timeout",
                           disNoSirasi: [null, { siparis_no: "PR-X", durum: "odendi",
                                                 musteri_tel: TEL }] });
    let yakalanan8 = null;
    try { await cagir(GECERLI, egeBaslik(), env8); } catch (e) { yakalanan8 = e; }
    ol("YARIS: kisitlama DISI hata 200'e cevrilmez", !!yakalanan8);
    ol("YARIS: kisitlama DISI hata AYNEN yukari cikar",
       !!yakalanan8 && /network timeout/.test(String(yakalanan8 && yakalanan8.message)),
       String(yakalanan8 && yakalanan8.message).slice(0, 90));
  }

  // ---- (F4) CAPRAZ-MUSTERI CAKISMASI ----------------------------------------------
  // 🔴 USTA denetiminde bulundu. Idempotens anahtari yalniz `dis_no`; Ege'nin numara
  // bicimi (PR-yyMMdd-HHmmss, SANIYE cozunurluklu, SONEK YOK) iki FARKLI musterinin
  // ayni saniyede ayni numarayi uretmesini dusuk ama SIFIR OLMAYAN ihtimal birakiyor.
  // Eski davranis: ikinci musteriye BASKA MUSTERININ siparis numarasi 200 {tekrar:true}
  // ile donuyor, ikinci siparis D1'e HIC yazilmiyordu -> sessiz siparis kaybi + PII
  // karisimi. Artik telefon eslesmiyorsa 409 dis-no-cakismasi.
  {
    const env9 = mockEnv({ disNoKayit: { siparis_no: "PR-260801-110600-ZXC",
                                         durum: "odendi", musteri_tel: BASKA_TEL } });
    const c9 = await cagir(GECERLI, egeBaslik(), env9);
    const j9 = JSON.parse(await c9.text());
    ol("CAPRAZ: ayni dis_no BASKA musteri -> 409 (200 DEGIL)", c9.status === 409,
       "kod=" + c9.status);
    ol("CAPRAZ: hata 'dis-no-cakismasi'", j9.hata === "dis-no-cakismasi", j9.hata);
    ol("CAPRAZ: BASKA musterinin siparis numarasi SIZMAZ",
       !JSON.stringify(j9).includes("PR-260801-110600-ZXC"), JSON.stringify(j9).slice(0, 90));
    ol("CAPRAZ: tekrar isareti YOK", j9.tekrar === undefined);
    ol("CAPRAZ: INSERT YOK (ikiz de acilmaz)", env9.yazmalar.length === 0,
       "yazma=" + env9.yazmalar.length);
  }
  // FAIL-CLOSED: telefon dogrulanamiyorsa (bos/eksik satir) da 409 — "dogrulayamadim"
  // hali TEKRAR sayilip siparis kaybedilmez. (Bu uc yazdigi her satira dogrulanmis
  // telefon koyar, yani bu hal bu kanalda olusamaz; kapi yine de kapali.)
  {
    const env10 = mockEnv({ disNoKayit: { siparis_no: "PR-BOS", durum: "odendi",
                                          musteri_tel: "" } });
    const c10 = await cagir(GECERLI, egeBaslik(), env10);
    ol("CAPRAZ: satirda telefon YOKSA da 409 (fail-closed)", c10.status === 409,
       "kod=" + c10.status);
  }
  // YARIS kolunda da ayni savunma gecerli: rakip satir baska musteriye aitse 409.
  {
    const env11 = mockEnv({
      insertCakismasi: true,
      disNoSirasi: [null, { siparis_no: "PR-RAKIP", durum: "odendi",
                            musteri_tel: BASKA_TEL }],
    });
    const c11 = await cagir(GECERLI, egeBaslik(), env11);
    const j11 = JSON.parse(await c11.text());
    ol("CAPRAZ+YARIS: rakip satir BASKA musteri -> 409", c11.status === 409,
       "kod=" + c11.status);
    ol("CAPRAZ+YARIS: rakibin numarasi SIZMAZ",
       !JSON.stringify(j11).includes("PR-RAKIP"), JSON.stringify(j11).slice(0, 90));
  }
  // KONTROL KOLU: telefon ESLESIYORSA idempotens BOZULMADI (409 her seye donmuyor).
  {
    const env12 = mockEnv({ disNoKayit: { siparis_no: "PR-AYNI", durum: "odendi",
                                          musteri_tel: TEL } });
    const c12 = await cagir(GECERLI, egeBaslik(), env12);
    const j12 = JSON.parse(await c12.text());
    ol("CAPRAZ kontrol kolu: AYNI musteri -> 200 tekrar (idempotens korundu)",
       c12.status === 200 && j12.tekrar === true && j12.siparis_no === "PR-AYNI",
       "kod=" + c12.status);
  }
  // Telefon KARSILASTIRMASI normallesmis deger uzerinden: govdede bicimli yazilsa da
  // (bosluk/parantez/tire) ayni satirla eslesir — yanlis 409 uretilmez.
  {
    const env13 = mockEnv({ disNoKayit: { siparis_no: "PR-BICIM", durum: "odendi",
                                          musteri_tel: TEL } });
    const c13 = await cagir({ ...GECERLI,
      musteri: { ...GECERLI.musteri, tel: "(0545) 138 65 26" } }, egeBaslik(), env13);
    ol("CAPRAZ: telefon BICIMLI yazilsa da ayni musteri sayilir -> 200",
       c13.status === 200, "kod=" + c13.status);
  }
}

// ---------------------------------------------------------------- G. PARA EKSENI

/**
 * 🔴 BEKLENEN DEGERLER ELLE HESAPLANMIS SABITTIR — `SECENEK.kdvAyristir` cagirilarak
 * URETILMEZ. Sebep olculdu: uretimin kullandigi AYNI fonksiyonla beklenen degeri
 * hesaplayan bir iddia, o fonksiyondaki yuvarlama mutasyonuna (Math.round -> Math.floor)
 * KORDUR; iki taraf birlikte kayar ve test yesil kalir. Sabitler KDV_YUZDE=20 icindir;
 * asagida oran kontrol ediliyor ki oran degisirse test "yanlis sabit" diye degil
 * "oran degisti" diye kirilsin.
 *
 * FIKSTUR (WA-PARA-1):  kalem tutar 90001 kurus, adet 3, kargo 4999 kurus
 *   brut = 90001 + 4999 = 95000
 *   net  = round(95000 * 100 / 120) = round(79166,666...) = 79167
 *   kdv  = 95000 - 79167 = 15833
 * Ayirt edicilik:
 *   - KDV kargo HARIC hesaplanirsa -> kdvAyristir(90001) -> kdv = 15000  (!= 15833)
 *   - round yerine floor -> net 79166 -> kdv = 15834                     (!= 15833)
 *   - kalem tutar/birim takasi -> birim 90001, tutar 30000 (asagida TAM DEGER iddiasi)
 * Not: eski TEK para fikstürü 90000 kurustu; 90000*100/120 = 75000 TAM bolunuyordu,
 * yani round ile floor AYNI sonucu veriyordu -> yuvarlama ekseni HIC olculmuyordu.
 */
const PARA_BAZ = {
  musteri: GECERLI.musteri,
  odeme: "havale",
};

async function setG() {
  console.log("\nG. PARA EKSENI (KDV kargoyu icerir · yuvarlama round · kalem tam degeri)");
  const SECENEK = globalThis.PRUVO_SECENEK;
  ol("KDV orani beklenen sabitlerle ayni (KDV_YUZDE=20)",
     SECENEK && SECENEK.KDV_YUZDE === 20, "oran=" + (SECENEK && SECENEK.KDV_YUZDE));

  // (G1) KARGOLU fikstür — kargo KDV matrahina GIRER.
  const env = mockEnv();
  const c = await cagir({ ...PARA_BAZ, dis_no: "WA-PARA-1", kargo_kurus: 4999,
                          urunler: [{ ad: "Ölçüye özel dişli", adet: 3,
                                      tutar_kurus: 90001 }] }, egeBaslik(), env);
  ol("kargolu siparis 201", c.status === 201, "kod=" + c.status);
  const args = env.yazmalar[0].args;
  ol("bind: tutar_kurus TAM 90001", args[3] === 90001, "tutar=" + args[3]);
  ol("bind: kargo_kurus TAM 4999 (fikstürde kargo VAR)", args[4] === 4999,
     "kargo=" + args[4]);
  ol("bind: kdv_kurus TAM 15833 (matrah = tutar + KARGO, yuvarlama round)",
     args[5] === 15833, "kdv=" + args[5]);
  ol("kdv 15000 DEGIL (kargo matraha dahil edilmemis olurdu)", args[5] !== 15000,
     "kdv=" + args[5]);
  ol("kdv 15834 DEGIL (floor'a kaymis olurdu)", args[5] !== 15834, "kdv=" + args[5]);
  // Kalem tam degerleri: takas mutantinin TEK nobetcisi.
  const kalem = JSON.parse(args[7])[0];
  ol("kalem tutar_kurus TAM 90001 (birim ile TAKAS EDILMEMIS)",
     kalem.tutar_kurus === 90001, "tutar_kurus=" + kalem.tutar_kurus);
  ol("kalem birim_kurus TAM 30000 (= floor(90001/3), tutar ile TAKAS EDILMEMIS)",
     kalem.birim_kurus === 30000, "birim_kurus=" + kalem.birim_kurus);
  ol("kalem adet TAM 3", kalem.adet === 3, "adet=" + kalem.adet);

  // (G2) AYNI kalem, KARGO YOK -> KDV kucululur. Kargonun matraha girdiginin
  // ikinci, farktan gelen kaniti (tek sabite bakip "tesaduf" demek imkansiz olsun).
  {
    const e2 = mockEnv();
    await cagir({ ...PARA_BAZ, dis_no: "WA-PARA-2", kargo_kurus: 0,
                  urunler: [{ ad: "Ölçüye özel dişli", adet: 3, tutar_kurus: 90001 }] },
                egeBaslik(), e2);
    const a2 = e2.yazmalar[0].args;
    ol("kargosuz ayni kalem: kdv TAM 15000", a2[5] === 15000, "kdv=" + a2[5]);
    ol("kargo KDV'yi GERCEKTEN degistiriyor (15833 != 15000)", args[5] !== a2[5],
       args[5] + " vs " + a2[5]);
  }

  // (G3) IKINCI yuvarlama fikstürü — govde tutari, tam bolunmeyen baska bir sayi.
  //      33333 -> net = round(27777,5) = 27778 -> kdv = 5555 ; floor olsa 27777/5556.
  {
    const e3 = mockEnv();
    await cagir({ ...PARA_BAZ, dis_no: "WA-PARA-3", tutar_kurus: 33333, kargo_kurus: 0,
                  urunler: [{ ad: "Parça", adet: 1, tutar_kurus: 0 }] }, egeBaslik(), e3);
    const a3 = e3.yazmalar[0].args;
    ol("govde tutari 33333 -> kdv TAM 5555 (round, .5 yukari)", a3[5] === 5555,
       "kdv=" + a3[5]);
    ol("kdv 5556 DEGIL (floor'a kaymis olurdu)", a3[5] !== 5556, "kdv=" + a3[5]);
  }

  // (G3b) 🔴 CEIL NOBETCISI — round ile ceil'i ayiran TEK fikstur.
  // USTA denetiminde olculdu: mevcut dort para fiksturunun (95000, 33333, 19135, 90001)
  // HEPSINDE ondalik kisim >= 0,5 idi, yani round == ceil; `Math.round -> Math.ceil`
  // mutanti 11/12 kirmizinin arasindan TEK BASINA KACIYORDU. Ayirt eden sart:
  // ondalik kisim < 0,5. brut = 100000 -> 100000*100/120 = 83333,333...
  //   round = 83333 -> kdv 16667   (DOGRU)
  //   ceil  = 83334 -> kdv 16666   (mutant)
  //   floor = 83333 -> kdv 16667   (floor'u AYIRMAZ; onu yukaridaki fiksturler ayiriyor)
  {
    const e3b = mockEnv();
    await cagir({ ...PARA_BAZ, dis_no: "WA-PARA-3B", tutar_kurus: 100000, kargo_kurus: 0,
                  urunler: [{ ad: "Parça", adet: 1, tutar_kurus: 0 }] }, egeBaslik(), e3b);
    const a3b = e3b.yazmalar[0].args;
    ol("govde tutari 100000 -> kdv TAM 16667 (ondalik .333, round ASAGI)",
       a3b[5] === 16667, "kdv=" + a3b[5]);
    ol("kdv 16666 DEGIL (ceil'e kaymis olurdu)", a3b[5] !== 16666, "kdv=" + a3b[5]);
  }

  // (G4) COK KALEMLI: toplam kalemlerden gelir, her kalem TAM degerle yazilir.
  {
    const e4 = mockEnv();
    await cagir({ ...PARA_BAZ, dis_no: "WA-PARA-4", kargo_kurus: 1,
                  urunler: [{ ad: "Parça A", adet: 2, tutar_kurus: 12345 },
                            { ad: "Parça B", adet: 7, tutar_kurus: 6789 }] },
                egeBaslik(), e4);
    const a4 = e4.yazmalar[0].args;
    ol("cok kalem: tutar TAM 19134 (12345 + 6789)", a4[3] === 19134, "tutar=" + a4[3]);
    const k4 = JSON.parse(a4[7]);
    ol("kalem A tutar 12345 / birim 6172 (= floor(12345/2))",
       k4[0].tutar_kurus === 12345 && k4[0].birim_kurus === 6172,
       k4[0].tutar_kurus + "/" + k4[0].birim_kurus);
    ol("kalem B tutar 6789 / birim 969 (= floor(6789/7))",
       k4[1].tutar_kurus === 6789 && k4[1].birim_kurus === 969,
       k4[1].tutar_kurus + "/" + k4[1].birim_kurus);
    // brut = 19134 + 1 = 19135 -> net = round(15945,833) = 15946 -> kdv = 3189
    ol("cok kalem: kdv TAM 3189 (kargo 1 kurus DAHIL)", a4[5] === 3189, "kdv=" + a4[5]);
  }
}

// ---------------------------------------------------------------- kosum

(async () => {
  console.log("PRUVO shop — /api/shop/yonet/wa-siparis kabul testleri");
  await setA();
  await setB();
  await setC();
  await setD();
  await setE();
  await setF();
  await setG();
  console.log("\n" + (kalan === 0 ? "✅ HEPSI GECTI" : "❌ KIRMIZI") +
              " — gecen: " + gecen + ", kalan: " + kalan);
  process.exit(kalan === 0 ? 0 : 1);
})();
