#!/usr/bin/env node
/**
 * METIN BEYAZ LISTE KAPISI — "musteri metnindeki karakter SESSIZCE dusmesin".
 *
 *   node jenerator/test/metin-beyaz-liste.mjs
 *
 * NEDEN VAR (olculmus sessiz kusur, 2026-07-29):
 *   Sunucu tarafi derleyici (onizleme/derleyici/server.py `metin_temizle`) SIKI BEYAZ
 *   LISTE uygular: harf/rakam + bosluk + . , - _ DISINDAKI her karakteri (& / ( ) : ; %
 *   + " \ ...) SESSIZCE DUSURUR. Konfiguratorde bu uyari yalniz `cerceveDurumu()`
 *   yoluna (cerceve ailesinin `yazi` alanina) bagliydi; `dogrula()`nin generic `metin`
 *   dalina DEGIL. Sonuc olculdu: kase alanina "AHMET & OGULLARI", jeton yuzune
 *   "A/B (1)" HICBIR UYARI CIKMADAN geciyordu ve musteri "AHMET  OGULLARI" / "AB 1"
 *   basilmis urun aliyordu. Kusur sessiz: ne sayfa, ne sepet, ne Worker bagiriyordu.
 *
 * NE KANITLAR (dar, dogru etiket):
 *   (A) KESIF: jenerator/urunler/*.json DIZIN TARAMASI ile `tip: "metin"` parametresi
 *       olan HER aile bulunur (elle liste YOK -> yeni aile sessizce kapsam disi kalmaz).
 *   (B) KIRLI: o ailelerin metin alanina beyaz liste DISI karakter (& / ( ) : ve
 *       olculmus iki gercek vaka) konunca KONF.dogrula() GECERSIZ doner ve hata TAM O
 *       ALANIN adinda olur -> sayfa uyariyi basar, "Sepete ekle" kilitlenir.
 *   (C) YANLIS-POZITIF: temiz metinler ("", "AHMET OGULLARI", "A1", "PRUVO",
 *       "Cinar-Oz_Sik" turevleri, "12.5", "100") GECERLI kalir — sifir yanlis-pozitif.
 *       Bu eksen olmadan kapi "her metni reddet" diye sakatlanip yesil kalabilirdi.
 *   (D) SUNUCU FAIL-CLOSED: shop/src/parametrik.js (Worker'in para yolu) AYNI
 *       KONF.dogrula'yi cagirdigi icin kirli metin orada da REDDEDILIR
 *       ("parametre-araligi") — istemci uyarisi sunucu kapisinin YERINE gecmez,
 *       sunucu kapisi GEVSEMEZ, tersine bugun sizdirdigi sinif kapanir.
 *
 * NE KANITLAMAZ (iddia edilmez):
 *   * Metnin uretilen govdeye DOGRU islendigini kanitlamaz (o ayri kapi:
 *     tools/metin-eslem-test.py + onizleme-imaj.yml gercek STL duman adimi).
 *   * Sunucunun beyaz listesiyle bu regex'in KUME OLARAK ayni kaldigini surekli
 *     kanitlamaz (iki dosya, iki dil); burada olculen sey istemci/Worker yolunun
 *     kirliyi GORUNUR reddetmesidir.
 *   * OpenSCAD render'i CAGRILMAZ (bu makinede SIGABRT) -> geometri iddiasi YOK.
 *
 * KIRMIZI-MUTASYON (kanit muhendis raporunda ham cikti):
 *   (a) konfigurator.js `metin` dalindaki beyaz-liste satiri silinir -> (B) KIRMIZI.
 *   (b) kontrol no-op yapilir (`if (false)`)                        -> (B) KIRMIZI.
 *   (c) kontrol "her metni reddet" yapilir                          -> (C) KIRMIZI.
 *
 * OFFLINE: ag YOK, wrangler YOK, openscad YOK, dosya YAZMAZ, urunler.json OKUNMAZ.
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

import KONF from "../konfigurator.js";
import { parametrikHesapla } from "../../shop/src/parametrik.js";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");
const SEMA_DIZIN = path.join(KOK, "jenerator", "urunler");

// secenekler.js tarayici-IIFE'si: fiyat-test.js deseniyle vm sandbox'inda yuklenir.
const kum = { window: {} };
vm.createContext(kum);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), kum);
const SECENEK = kum.window.PRUVO_SECENEK;

let hata = 0;
let calisanIddia = 0;
function iddia(ad, kosul, ek) {
  calisanIddia++;
  if (kosul) {
    console.log("  ✅ " + ad);
  } else {
    hata++;
    console.log("  ❌ " + ad + (ek ? "  -> " + ek : ""));
  }
}

// ---- (A) KESIF: `tip: "metin"` parametresi olan aileler ---------------------
function metinAileleri() {
  const bulunan = [];
  for (const dosya of fs.readdirSync(SEMA_DIZIN).sort()) {
    if (!dosya.endsWith(".json")) { continue; }
    const sema = JSON.parse(fs.readFileSync(path.join(SEMA_DIZIN, dosya), "utf8"));
    for (const p of sema.parametreler || []) {
      if ((p.tip || "sayi") === "metin") {
        bulunan.push({ dosya: dosya, sema: sema, param: p });
      }
    }
  }
  return bulunan;
}

// Beyaz liste DISI vakalar. Hepsi KISA (<= 16) -> maksUzunluk hatasi maskeleyemez;
// yani kirmizi TAM OLARAK beyaz listeden gelir.
const KIRLI = [
  ["& (ampersan)", "A&B"],
  ["/ (bolu)", "A/B"],
  ["( (parantez ac)", "A(B"],
  [") (parantez kapa)", "A)B"],
  [": (iki nokta)", "A:B"],
  ["olculmus vaka — kase", "AHMET & OGULLARI"],
  ["olculmus vaka — jeton", "A/B (1)"],
];

// Temiz vakalar (yanlis-pozitif ekseni). Hepsi <= 20 karakter -> en dar
// maksUzunluk (jeton 20) altinda kalir, uzunluk hatasi karismaz.
const TEMIZ = [
  ["bos", ""],
  ["ad + bosluk", "AHMET OGULLARI"],
  ["kisa alfanumerik", "A1"],
  ["marka", "PRUVO"],
  ["ondalik nokta", "12.5"],
  ["virgul + tire + alt tire", "Ay,Bir-Iki_Uc"],
  ["Turkce harfler", "ÇINAR ÖZ ŞIK ğüşıöç"],
  ["sayi", "100"],
];

function degerlerle(sema, ad, deger) {
  const d = KONF.varsayilanDegerler(sema);
  d[ad] = deger;
  return d;
}

console.log("PRUVO metin beyaz-liste kabul testi (jenerator/konfigurator.js dogrula)\n");

const aileler = metinAileleri();
console.log("(A) KESIF — `tip: \"metin\"` parametresi olan aile/alan: " + aileler.length);
for (const a of aileler) {
  console.log("      • " + a.sema.id + " . " + a.param.ad +
              " (maksUzunluk=" + (a.param.maksUzunluk == null ? "-" : a.param.maksUzunluk) + ")");
}
// OLU NOBETCI KORUMASI: hicbir aile bulunmazsa asagidaki tum donguler bos doner ve
// test SESSIZ YESIL olurdu. Kesif bos ise KIRMIZI.
iddia("kesif bos degil (olu nobetci korumasi)", aileler.length > 0);

// TABAN: varsayilan degerler GECERLI olmali — degilse (B)'nin kirmizisi beyaz listeden
// degil bozuk fikstürden gelirdi ve iddia anlamsizlasirdi.
console.log("\n(A2) TABAN — her ailenin varsayilan degerleri gecerli mi");
for (const a of aileler) {
  const s = KONF.dogrula(a.sema, KONF.varsayilanDegerler(a.sema));
  iddia("taban gecerli: " + a.sema.id, s.gecerli === true, JSON.stringify(s.hatalar));
}

// ---- (B) KIRLI metin UYARI URETMELI ---------------------------------------
console.log("\n(B) KIRLI — beyaz liste disi karakter GORUNUR hata uretmeli");
let kirliKosum = 0;
for (const a of aileler) {
  for (const [etiket, metin] of KIRLI) {
    const s = KONF.dogrula(a.sema, degerlerle(a.sema, a.param.ad, metin));
    kirliKosum++;
    iddia(a.sema.id + " . " + a.param.ad + "  " + etiket + "  " + JSON.stringify(metin),
          s.gecerli === false && !!s.hatalar[a.param.ad],
          "gecerli=" + s.gecerli + " hatalar=" + JSON.stringify(s.hatalar));
  }
}
iddia("kirli vaka kosum sayisi > 0", kirliKosum > 0, "kosum=" + kirliKosum);
console.log("      kirli vaka kosumu: " + kirliKosum +
            " (" + aileler.length + " alan × " + KIRLI.length + " vaka)");

// ---- (C) TEMIZ metin UYARI URETMEMELI (yanlis-pozitif = 0) -----------------
console.log("\n(C) YANLIS-POZITIF — temiz metin gecerli kalmali");
let yanlisPozitif = 0;
let temizKosum = 0;
for (const a of aileler) {
  for (const [etiket, metin] of TEMIZ) {
    const s = KONF.dogrula(a.sema, degerlerle(a.sema, a.param.ad, metin));
    temizKosum++;
    const ok = s.gecerli === true && !s.hatalar[a.param.ad];
    if (!ok) { yanlisPozitif++; }
    iddia(a.sema.id + " . " + a.param.ad + "  " + etiket + "  " + JSON.stringify(metin),
          ok, "hatalar=" + JSON.stringify(s.hatalar));
  }
}
iddia("YANLIS-POZITIF SAYISI = 0", yanlisPozitif === 0, "yanlis-pozitif=" + yanlisPozitif);
console.log("      temiz vaka kosumu: " + temizKosum + " · yanlis-pozitif: " + yanlisPozitif);

// ---- (D) SUNUCU (Worker) FAIL-CLOSED --------------------------------------
// shop/src/parametrik.js AYNI KONF.dogrula'yi cagirir. Kirli metin orada
// "parametre-araligi" ile REDDEDILMELI; temiz metin bu hatayi ALMAMALI.
// (Temiz metinde "taban-fiyat-yok" gibi baska bir sonuc cikabilir — iddia yalniz
// "parametre-araligi DEGIL" uzerinedir; boylece taban fiyat politikasina bagimli degil.)
console.log("\n(D) SUNUCU FAIL-CLOSED — Worker (shop/src/parametrik.js) kirliyi reddediyor");
let workerKosum = 0;
for (const a of aileler) {
  const kirli = parametrikHesapla(
    { parametreler: degerlerle(a.sema, a.param.ad, "AHMET & OGULLARI"),
      malzeme: "PLA", renk: "Siyah" }, SECENEK, a.sema);
  workerKosum++;
  iddia("Worker REDDEDIYOR: " + a.sema.id, kirli.hata === "parametre-araligi",
        JSON.stringify(kirli).slice(0, 160));

  const temiz = parametrikHesapla(
    { parametreler: degerlerle(a.sema, a.param.ad, "AHMET OGULLARI"),
      malzeme: "PLA", renk: "Siyah" }, SECENEK, a.sema);
  workerKosum++;
  iddia("Worker temizde parametre-araligi DEMIYOR: " + a.sema.id,
        temiz.hata !== "parametre-araligi", JSON.stringify(temiz).slice(0, 160));
}
iddia("worker kosum sayisi > 0", workerKosum > 0, "kosum=" + workerKosum);

// ---- OZET -----------------------------------------------------------------
console.log("\n----------------------------------------------------------------------");
console.log("Aile/alan: " + aileler.length +
            " · kirli vaka: " + kirliKosum +
            " · temiz vaka: " + temizKosum +
            " · worker vaka: " + workerKosum +
            " · yanlis-pozitif: " + yanlisPozitif);
console.log("Iddia: " + calisanIddia + " · KIRMIZI: " + hata);
console.log(hata === 0 ? "SONUC: YESIL ✅" : "SONUC: KIRMIZI ❌");
process.exit(hata === 0 ? 0 : 1);
