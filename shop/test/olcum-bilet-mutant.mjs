/**
 * PRUVO shop — FANTOM PURCHASE KAPISI: MUTASYON KANITI.
 *
 * NE ISPATLAR: shop/test/olcum-donus-bileti.mjs'in yesili TAUTOLOJI DEGIL. Kapinin her
 * dogrulama KOLU tek tek bozulur ve testin (a) KIRMIZI yandigi, (b) kirmizinin sebebinin
 * TAM O KOL oldugu ayri ayri olculur.
 *
 * 🔴 NEDEN KONTROL MUTANTI VAR (K182 dersi + [[ad-iki-rolde-mutanti-golgeler]]):
 *   "Mutasyon uyguladim, test kirmizi yandi" TEK BASINA KANIT DEGILDIR — kirmizi, mutasyonun
 *   yakalanmasindan degil, dosyanin bozulmasindan/harness gurultusunden de gelebilir. Bu yuzden
 *   burada bir KONTROL MUTANTI kosar: davranisi DEGISTIRMEYEN (yalniz yorum satiri ekleyen) bir
 *   duzenleme. Kontrol mutanti YESIL kalmak ZORUNDADIR. Kalmazsa harness'in kendisi guvenilmezdir
 *   ve bu betik rc=1 doner — "mutantlar kirmizi yandi" diye YESIL RAPOR VERMEZ.
 *
 * 🔴 AYRICA: her mutantin DUSURDUGU IDDIA KUMESI karsilastirilir. Iki farkli kol bozuldugunda
 *   ayni iddialar dusuyorsa, o kollardan biri OLCULMUYOR demektir (ad-iki-rolde tuzagi) — bu da
 *   KIRMIZI sayilir.
 *
 * DISK KURALI: mutant kopyalar gecici dizine yazilir ve finally'de SILINIR; repoya iz BIRAKMAZ.
 * Kosum: node shop/test/olcum-bilet-mutant.mjs    (rc=0 = mutasyon kanitlandi)
 */

import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const KAYNAK = path.join(BURASI, "..", "src", "olcum-bilet.js");
const TEST = path.join(BURASI, "olcum-donus-bileti.mjs");
const OLCUM_JS = pathToFileURL(path.join(BURASI, "..", "src", "olcum.js")).href;

const ham = fs.readFileSync(KAYNAK, "utf8");

/**
 * MUTANT TABLOSU. Her biri kapinin AYRI bir dogrulama kolunu bozar.
 * `bekle`: bu kol bozulunca DUSMESI ZORUNLU olan iddia onekleri. Dusmezse kol OLCULMUYOR.
 */
const MUTANTLAR = [
  {
    ad: "M1 bilet-eslesmesi (biletYak: her kayit eslessin)",
    kol: "biletYak icindeki `k.pb === bilet` esitligi",
    ara: 'const i = g.findIndex((k) => k && typeof k.pb === "string" && k.pb === bilet);',
    yaz: "const i = g.findIndex((k) => !!k);",
    bekle: ["A1", "A5"],
  },
  {
    ad: "M2 durum kapisi ('odendi' sarti kaldirildi)",
    kol: "biletDogrula icindeki `siparis.durum !== 'odendi'` kapisi",
    ara: 'if (siparis.durum !== "odendi") { return { ok: false, sebep: "durum-odendi-degil" }; }',
    yaz: "/* mutant: durum kapisi kaldirildi */",
    bekle: ["A4", "A4b"],
  },
  {
    // NOT: bu mutant C2/C3'u DUSURMEZ ve bu BEKLENEN haldir — bilet yakma (pb silme) hâlâ
    // calistigi icin ardisik 2. cagri zaten bileti bulamaz. CAS'in TEK basina korudugu sey
    // ESZAMANLI iki isteğin ikisinin birden kazanmasidir; olculebilir izi D blogudur.
    // Bekcisini "C2 de dusmeli" diye yazmak, mutanti YANLIS kola atfetmek olurdu.
    ad: "M3 CAS yakma (es zamanli iki istek de kazanir)",
    kol: "biletDogrula icindeki CAS UPDATE `changes > 0` hukmu",
    ara: "!(g.meta.changes > 0)",
    yaz: "false",
    bekle: ["D1"],
  },
];

/** Davranisi DEGISTIRMEYEN kontrol: yalniz yorum eklenir. YESIL kalmak ZORUNDA. */
const KONTROL = {
  ad: "K0 KONTROL (yalniz yorum — davranis degismez)",
  ara: "import { kurusTRY } from \"./olcum.js\";",
  yaz: "import { kurusTRY } from \"./olcum.js\";\n// mutant harness kontrol satiri (davranissiz)",
};

const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-bilet-mutant-"));
let hata = 0;

/** Mutant kopyayi yaz (goreli import mutlak URL'ye cevrilir) ve testi ona karsi kostur. */
function kostur(etiket, kaynakMetin) {
  const dosya = path.join(gecici, "olcum-bilet-" + etiket + ".js");
  fs.writeFileSync(dosya,
    kaynakMetin.replace('from "./olcum.js"', 'from "' + OLCUM_JS + '"'), "utf8");
  const r = spawnSync(process.execPath, [TEST], {
    encoding: "utf8",
    env: { ...process.env, PRUVO_BILET_MODUL: pathToFileURL(dosya).href },
  });
  const cikti = (r.stdout || "") + (r.stderr || "");
  const m = /KALAN_IDDIALAR: (.*)/.exec(cikti);
  const kalanlar = m ? m[1].split(" | ").map((s) => s.trim()).filter(Boolean) : [];
  return { rc: r.status, kalanlar, cikti };
}

try {
  // ---- 0) TABAN: mutasyonsuz kaynak YESIL olmali ---------------------------------
  console.log("\n=== 0) TABAN (mutasyonsuz) ===");
  const taban = kostur("taban", ham);
  console.log("   rc=" + taban.rc + "  kalan=" + taban.kalanlar.length);
  if (taban.rc !== 0) {
    console.log("❌ TABAN KIRMIZI — mutasyon olcumu ANLAMSIZ (once tabani yesile cek).");
    console.log(taban.cikti);
    hata++;
  } else {
    console.log("✅ taban yesil — mutant kirmizilari mutasyona ATFEDILEBILIR.");
  }

  // ---- 1) KONTROL MUTANTI: davranissiz duzenleme YESIL kalmali -------------------
  console.log("\n=== 1) KONTROL MUTANTI (kirmizi 'her duzenlemede' gelmiyor mu?) ===");
  if (ham.indexOf(KONTROL.ara) < 0) {
    console.log("❌ " + KONTROL.ad + " — CAPA BULUNAMADI (kaynak degismis). FAIL-LOUD.");
    hata++;
  } else {
    const k = kostur("kontrol", ham.replace(KONTROL.ara, KONTROL.yaz));
    if (k.rc === 0) {
      console.log("✅ " + KONTROL.ad + " -> rc=0 YESIL (harness gurultu uretmiyor)");
    } else {
      console.log("❌ " + KONTROL.ad + " -> rc=" + k.rc + " KIRMIZI. Harness GUVENILMEZ: " +
        "davranissiz duzenleme de kirmizi yakiyor, yani mutant kirmizilari KANIT DEGIL.");
      console.log("   kalan: " + k.kalanlar.join(" | "));
      hata++;
    }
  }

  // ---- 2) MUTANTLAR: her kol ayri ayri --------------------------------------------
  console.log("\n=== 2) MUTANTLAR (her dogrulama kolu tek tek bozulur) ===");
  const kumeler = [];
  for (const mut of MUTANTLAR) {
    console.log("\n-- " + mut.ad);
    console.log("   kol: " + mut.kol);
    if (ham.indexOf(mut.ara) < 0) {
      console.log("   ❌ CAPA BULUNAMADI — kaynak degismis, bu kol OLCULEMEDI. FAIL-LOUD.");
      hata++;
      kumeler.push({ ad: mut.ad, kalanlar: null });
      continue;
    }
    const mutasyonlu = ham.replace(mut.ara, mut.yaz);
    if (mutasyonlu === ham) {
      console.log("   ❌ MUTASYON UYGULANMADI (metin ayni) — FAIL-LOUD.");
      hata++;
      continue;
    }
    const r = kostur(mut.ad.split(" ")[0], mutasyonlu);
    console.log("   rc=" + r.rc + "  dusen iddia: " + (r.kalanlar.join(" | ") || "(yok)"));

    if (r.rc === 0) {
      console.log("   ❌ MUTANT YASADI — bu kol test tarafindan OLCULMUYOR " +
        "(yasamak 'kol saglam' degil 'kol olculemedi' demektir).");
      hata++;
    } else {
      // Kirmizi YETMEZ: dusen iddialar TAM O KOLUN bekcileri mi?
      const eksik = mut.bekle.filter(
        (on) => !r.kalanlar.some((k) => k.split(" ")[0] === on));
      if (eksik.length) {
        console.log("   ❌ KIRMIZI ama SEBEP ATFEDILEMIYOR — beklenen bekci iddialar dusmedi: " +
          eksik.join(", ") + ". Kirmizi baska bir yerden geliyor olabilir.");
        hata++;
      } else {
        console.log("   ✅ KIRMIZI ve sebep ATFEDILDI — dusen iddialar (" +
          mut.bekle.join(", ") + ") tam bu kolun bekcileri.");
      }
    }
    kumeler.push({ ad: mut.ad, kalanlar: r.kalanlar });
  }

  // ---- 3) GOLGELEME: iki kol AYNI iddialari dusuruyorsa biri olculmuyordur --------
  console.log("\n=== 3) GOLGELEME KONTROLU (kollar birbirini gizliyor mu?) ===");
  for (let i = 0; i < kumeler.length; i++) {
    for (let j = i + 1; j < kumeler.length; j++) {
      const a = kumeler[i], b = kumeler[j];
      if (!a.kalanlar || !b.kalanlar) { continue; }
      const ayni = a.kalanlar.length === b.kalanlar.length &&
        a.kalanlar.every((x) => b.kalanlar.includes(x));
      if (ayni) {
        console.log("   ❌ " + a.ad + " ile " + b.ad + " AYNI iddialari dusuruyor — " +
          "kollardan biri BAGIMSIZ olculmuyor.");
        hata++;
      }
    }
  }
  if (!hata) { console.log("   ✅ her kolun dusurdugu iddia kumesi FARKLI — kollar bagimsiz olculuyor."); }
} finally {
  // DISK KURALI: ureten temizler.
  fs.rmSync(gecici, { recursive: true, force: true });
  console.log("\n[temizlik] gecici dizin silindi: " + gecici +
    " (mevcut mu? " + (fs.existsSync(gecici) ? "EVET — HATA" : "hayir") + ")");
  if (fs.existsSync(gecici)) { hata++; }
}

console.log("\n=== MUTASYON KANITI: " + (hata ? "KIRMIZI (" + hata + " sorun)" : "YESIL") + " ===");
process.exit(hata ? 1 : 0);
