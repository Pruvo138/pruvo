#!/usr/bin/env node
/**
 * ONBELLEK SURUM KAPISI — `ONBELLEK_SURUM` bump'i GERCEKTEN onbellek anahtarini
 * degistiriyor mu (onizleme/src/index.js).
 *
 * NEDEN VAR (olculmus sessiz hata, 29 Tem 2026):
 *   Musterinin girdigi metin uretilen govdeye HIC girmiyordu; kase her musteriye
 *   sabit "PRUVO" basiyordu (canli olcum: ayni geometriyle 'AAA135253' vs 'ZZZ135253'
 *   -> AYNI SHA-256, 228584 bayt). Eslem onarildi, AMA onarim TEK BASINA yetmez:
 *   /olustur once R2 onbelleginden servis eder (X-Kaynak: onbellek). Surum
 *   yukseltilmezse ONCEDEN onizlenmis her parametre seti YAZISIZ mesh'i servis
 *   etmeye devam eder. Emsal: v4 bump'i jeton metni icin tam bu sebeple yapildi.
 *
 * NE OLCER (dar, dogru etiket):
 *   1) GERCEK worker kodu (default.fetch -> anahtarUret) ile uretilen onbellek
 *      anahtari, kaynaktaki ONBELLEK_SURUM sabitini TASIR.
 *   2) Sabit degisince ayni parametrelerin anahtari DEGISIR; anahtarin geri kalani
 *      (aile + parametre ozeti) AYNI kalir -> fark GERCEKTEN surumden gelir.
 *      Olcum kaynagin GECICI kopyasinda yapilir; kopya mantik yazilmaz, hash elle
 *      hesaplanmaz.
 *   3) Cari surum "v5" DEGILDIR (yazisiz mesh'lerin yazildigi surum). Bump geri
 *      alinirsa bu iddia KIRMIZI yanar.
 *   4) Ayni surum + ayni parametre -> AYNI anahtar (2. iddia totoloji olmasin).
 *   5) YALNIZ musteri metni degisince de anahtar DEGISIR (onbellek iki farkli
 *      yaziyi ayni kovaya dusurmez — sessiz teslimat hatasinin onbellek kanadi).
 *
 * NE OLCMEZ: metnin STL'e dogru basildigini (o, onizleme-imaj.yml "metin
 * farklilasma" dumani + tools/metin-eslem-test.py isi), worker'in deploy edildigini,
 * R2'deki ESKI anahtarlarin silindigini (silinmez; bump onlari ERISILMEZ kilar).
 *
 * NODE 20 UYUMU (yasanmis ariza, shop/test/konfigur-fail-closed.mjs basligi):
 *   Worker kaynaklari bare JSON import kullanir (esbuild bundle'lar; Node import
 *   NITELIGI ister). module.registerHooks gibi Node 22+ API'si KULLANILMAZ —
 *   JSON import'lari gomulu `const`a cevrilip gecici bir dizine yazilir; geriye
 *   surume duyarli hicbir sozdizimi kalmaz.
 *
 * KIRMIZI-MUTASYON: index.js'te ONBELLEK_SURUM "v6" -> "v5" -> iddia 3 KIRMIZI.
 * Kosum: node onizleme/test/onbellek-surum.mjs      (CI: Node 20)
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const ONIZLEME = path.dirname(TEST_DIR);
const KOK = path.dirname(ONIZLEME);
const SRC = path.join(ONIZLEME, "src");
const SHOP_SRC = path.join(KOK, "shop", "src");

// Gecici dizin onizleme/src ILE AYNI DERINLIKTE: index.js'in depo-koku import'lari
// (../../secenekler.js, ../../jenerator/konfigurator.js) GERCEK dosyalara cozulur.
const TEMP_ONEK = "src-test-tmp-";
const TEMP_DIZIN = path.join(ONIZLEME, TEMP_ONEK + process.pid);

function tempSupur() {
  for (const ad of fs.readdirSync(ONIZLEME)) {
    if (ad.startsWith(TEMP_ONEK)) {
      fs.rmSync(path.join(ONIZLEME, ad), { recursive: true, force: true });
    }
  }
}

/** `import X from "...json";` -> `const X = <json icerigi>;` (fail-closed: bozuk JSON patlar). */
function jsonGom(kaynak, kaynakDizin, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(kaynakDizin, rel), "utf8").trim();
      JSON.parse(ham);                       // bozuk JSON sessizce sizmasin
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ") — desen guncellenmeli");
  }
  return cikti;
}

/** index.js kaynagini gecici dizine yazilabilir hale getirir (semalar yolu yerele doner). */
function indexHazirla(kaynak) {
  const yeni = kaynak.replace('from "../../shop/src/semalar.js"', 'from "./semalar.js"');
  if (yeni === kaynak) {
    throw new Error("semalar.js import yolu bulunamadi — yukleyici bayat, guncelle");
  }
  return jsonGom(yeni, SRC, "index.js");
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

tempKur();
process.on("exit", () => { fs.rmSync(TEMP_DIZIN, { recursive: true, force: true }); });

const AILE = "olcuye-ozel-cerceve";
const PARAM = { acilik_eni: 100, acilik_boyu: 150, kenar_genisligi: 12,
                derinlik: 5.2, kenar_stili: "chamfer", yazi: "OKAN" };
const PARAM_B = { ...PARAM, yazi: "ZZZZZZZZ" };   // geometri AYNI, yalniz metin farkli
// v5 = yazisiz/"PRUVO"lu mesh'lerin yazildigi surum; anahtar bu surume DONEMEZ.
const YASAK_SURUM = "v5";

const hatalar = [];
function dg(ad, kosul, ek) {
  console.log((kosul ? "  [OK ] " : "  [HATA] ") + ad + (ek ? " — " + ek : ""));
  if (!kosul) { hatalar.push(ad); }
}

/** Kaynaktaki ONBELLEK_SURUM sabiti (fail-closed: bulunamazsa null -> KIRMIZI). */
function kaynakSurumu(kaynak) {
  const m = kaynak.match(/ONBELLEK_SURUM\s*=\s*"([^"]+)"/);
  return m ? m[1] : null;
}

let sayac = 0;
/** Verilen index.js kaynagini yukleyip GERCEK worker'a istek atar; sorulan
 *  R2 onbellek anahtarini yakalar (derleyici baglanmaz — anahtar zaten oncesinde uretilir). */
async function anahtarYakala(kaynak, parametreler) {
  sayac += 1;
  const yol = path.join(TEMP_DIZIN, "index-" + sayac + ".js");
  fs.writeFileSync(yol, indexHazirla(kaynak));
  const mod = await import(pathToFileURL(yol).href);
  const yakalanan = [];
  const env = {
    SITE_URL: "https://pruvo3d.com",
    ONBELLEK: {
      async get(anahtar) { yakalanan.push(anahtar); return null; },
      async put() { /* derleyici yok -> buraya gelinmez */ },
    },
  };
  const istek = new Request("https://pruvo3d.com/api/onizleme/olustur", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aile: AILE, parametreler }),
  });
  const yanit = await mod.default.fetch(istek, env);
  return { anahtar: yakalanan[0], durum: yanit.status, sayi: yakalanan.length };
}

async function main() {
  const kaynak = fs.readFileSync(path.join(SRC, "index.js"), "utf8");
  const surum = kaynakSurumu(kaynak);
  dg("kaynakta ONBELLEK_SURUM sabiti bulundu", !!surum, String(surum));
  if (!surum) { return; }

  const a = await anahtarYakala(kaynak, PARAM);
  dg("(1) worker onbellege TEK anahtar sordu", a.sayi === 1,
     "anahtar=" + a.anahtar + " http=" + a.durum);
  const parca = String(a.anahtar).split("/");
  dg("(1) anahtar bicimi onizleme/<surum>/<aile>/<ozet>.stl.gz",
     parca.length === 4 && parca[0] === "onizleme" && parca[2] === AILE,
     String(a.anahtar));
  dg("(1) anahtarin surum bolumu kaynak sabitiyle AYNI", parca[1] === surum,
     "anahtar=" + parca[1] + " kaynak=" + surum);

  // (3) Yasak surum kapisi — bump geri alinirsa KIRMIZI.
  dg("(3) cari surum yazisiz-mesh surumu (" + YASAK_SURUM + ") DEGIL",
     surum !== YASAK_SURUM,
     "cari=" + surum + (surum === YASAK_SURUM
       ? " -> onceden onizlenmis parametrelerde musteri YAZISIZ govde gorur"
       : ""));

  // (4) Kontrol grubu: ayni surum + ayni parametre -> AYNI anahtar.
  const a2 = await anahtarYakala(kaynak, PARAM);
  dg("(4) ayni surum + ayni parametre -> AYNI anahtar", a.anahtar === a2.anahtar,
     String(a2.anahtar));

  // (5) Yalniz musteri metni degisince anahtar DEGISIR.
  const b = await anahtarYakala(kaynak, PARAM_B);
  dg("(5) yalniz `yazi` degisince anahtar DEGISIYOR", a.anahtar !== b.anahtar,
     "OKAN -> " + a.anahtar + " | ZZZZZZZZ -> " + b.anahtar);

  // (2) Surum sabiti degisince anahtar degisir, geri kalani AYNI kalir.
  const sahteSurum = "vTEST" + Date.now();
  const mutant = kaynak.replace(/ONBELLEK_SURUM\s*=\s*"[^"]+"/,
                                'ONBELLEK_SURUM = "' + sahteSurum + '"');
  dg("(2) mutant uretildi (yalniz surum sabiti degistirildi)", mutant !== kaynak);
  const m = await anahtarYakala(mutant, PARAM);
  dg("(2) surum degisince anahtar DEGISIYOR", m.anahtar !== a.anahtar,
     a.anahtar + " -> " + m.anahtar);
  const mp = String(m.anahtar).split("/");
  dg("(2) FARK YALNIZ surum bolumunde (aile + parametre ozeti AYNI)",
     mp[1] === sahteSurum && mp[2] === parca[2] && mp[3] === parca[3],
     "mutant surum=" + mp[1] + " | ozet ayni mi=" + (mp[3] === parca[3]));
}

main().then(() => {
  console.log(hatalar.length
    ? "SONUC: KIRMIZI (" + hatalar.length + " iddia dustu)"
    : "SONUC: YESIL");
  process.exit(hatalar.length ? 1 : 0);
}).catch((e) => {
  console.error("SONUC: KIRMIZI — kosum patladi: " + ((e && e.stack) || e));
  process.exit(1);
});
