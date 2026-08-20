/**
 * PRUVO shop — FANTOM PURCHASE / TARAYICI KOLU: MUTASYON KANITI.
 *
 * NE ISPATLAR: shop/test/olcum-donus-tarayici.mjs'in yesili TAUTOLOJI DEGIL. index.html
 * `odemeDonusuIsle()` icindeki HER koruma kolu tek tek bozulur ve (a) testin KIRMIZI yandigi,
 * (b) kirmizinin sebebinin TAM O KOL oldugu AYRI AYRI olculur ([[K182]] — "kirmizi geldi"
 * tek basina kanit degildir; kirmizi bozulmadan/gurultuden de gelebilir).
 *
 * 🔴 KONTROL MUTANTI: davranisi DEGISTIRMEYEN (yalniz yorum ekleyen) bir duzenleme YESIL
 * kalmak ZORUNDADIR. Kalmazsa harness guvenilmezdir ve bu betik rc=1 doner.
 *
 * 🔴 CAPA TEKILLIGI: her capa cikarilan govdede TAM 1 KEZ gecmelidir. Birden fazla gecerse
 * mutasyon yanlis yere uygulanabilir ve "kol olculdu" hukmu atfedilemez hale gelir
 * ([[capa-cokmesi-arkasindaki-capalari-gizler]] · [[ad-iki-rolde-mutanti-golgeler]]).
 *
 * 🔴 NEDEN "KOLU SILMEK" DEGIL "FAIL-OPEN'A CEVIRMEK": ag hatasi kolunda `.catch`'i silmek
 * yakalanmamis bir reddetme birakirdi ve test yine "olay atilmadi" gorurdu — mutant YASAR,
 * yani kol OLCULMEMIS sayilirdi. Kusurun gercek hali FAIL-OPEN'di (onarim oncesi kod olayi
 * kosulsuz atiyordu); mutant o hali geri getirir. Duyarlilik ancak boyle olculur.
 *
 * DISK KURALI: mutant kopyalar gecici dizine yazilir ve finally'de SILINIR; index.html'e ve
 * repoya HIC dokunulmaz (mutasyon yalniz cikarilan METIN uzerinde yapilir).
 * Kosum: node shop/test/olcum-donus-tarayici-mutant.mjs    (rc=0 = mutasyon kanitlandi)
 */

import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const INDEX_HTML = path.join(BURASI, "..", "..", "index.html");
const TEST = path.join(BURASI, "olcum-donus-tarayici.mjs");

/* Test dosyasiyla AYNI capalar (IKIZ TANIM riski bilerek kabul edildi: capa degisirse ikisi de
   FAIL-LOUD verir, sessiz kayma olmaz). */
const BAS_CAPA = "function odemeDonusuIsle(){";
const SON_CAPA = "\n  }\n";

const hamHtml = fs.readFileSync(INDEX_HTML, "utf8");
const b0 = hamHtml.indexOf(BAS_CAPA);
const s0 = b0 < 0 ? -1 : hamHtml.indexOf(SON_CAPA, b0);
if (b0 < 0 || s0 < 0) {
  console.log("❌ GOVDE CIKARILAMADI — index.html capalari degismis (bas=" + b0 + " son=" + s0 + ").");
  process.exit(1);
}
const ham = hamHtml.slice(b0, s0 + SON_CAPA.length);

/**
 * MUTANT TABLOSU. Her biri TARAYICI kolunun AYRI bir korumasini bozar.
 * `bekle`: bu kol bozulunca DUSMESI ZORUNLU olan iddia onekleri. Dusmezse kol OLCULMUYOR.
 */
const MUTANTLAR = [
  {
    ad: "MT1 ag-hatasi kolu FAIL-OPEN'a cevrildi",
    kol: "`.catch(...)` — fetch reject oldugunda olay ATILMAMALI",
    ara: ".catch(function(){",
    yaz: '.catch(function(){ window.pruvoMetaTrack("Purchase", ' +
         '{ content_ids: pIds, content_type: "product", currency: "TRY" }, { eventID: no });',
    bekle: ["N1"],
  },
  {
    ad: "MT2 sunucu hukmu kapisi kaldirildi (ok:false yutuluyor)",
    kol: "`if(!c || c.ok !== true){ return; }` — sunucu ok demediyse olay YOK",
    ara: "if(!c || c.ok !== true){ return; }",
    yaz: "if(false){ return; }",
    bekle: ["R1"],
  },
  {
    ad: "MT3 value SUNUCU yerine URL'den okunuyor (eski kusur geri geldi)",
    kol: '`pVeri.value = c.value` — tutar SUNUCUDAN gelmeli, URL\'deki `t`\'den DEGIL',
    ara: 'if(typeof c.value === "number" && c.value > 0){ pVeri.value = c.value; }',
    yaz: 'pVeri.value = parseInt(q.get("t"), 10) / 100;',
    bekle: ["Y2"],
  },
  {
    ad: "MT4 bilet kapisi kaldirildi (biletsiz URL de uca gidiyor)",
    kol: "`no && pBilet && ...` — bilet yoksa uca HIC gidilmemeli",
    ara: 'if(no && pBilet && typeof window.pruvoMetaTrack === "function"){',
    yaz: 'if(no && typeof window.pruvoMetaTrack === "function"){',
    bekle: ["B1", "B2"],
  },
];

/** Davranisi DEGISTIRMEYEN kontrol: yalniz yorum eklenir. YESIL kalmak ZORUNDA. */
const KONTROL = {
  ad: "K0 KONTROL (yalniz yorum — davranis degismez)",
  ara: 'var pBilet = q.get("b") || "";',
  yaz: 'var pBilet = q.get("b") || "";\n        /* mutant harness kontrol satiri (davranissiz) */',
};

const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-tarayici-mutant-"));
let hata = 0;

/** Kere sayisi (capa tekilligi nobetcisi). */
function kacKez(metin, parca) {
  let n = 0, i = 0;
  for (;;) {
    const k = metin.indexOf(parca, i);
    if (k < 0) { return n; }
    n++; i = k + parca.length;
  }
}

/** Mutant govdeyi gecici dosyaya yaz ve kabul testini ONA KARSI kostur. */
function kostur(etiket, govdeMetni) {
  const dosya = path.join(gecici, "govde-" + etiket.replace(/[^A-Za-z0-9_-]/g, "_") + ".js");
  fs.writeFileSync(dosya, govdeMetni, "utf8");
  const r = spawnSync(process.execPath, [TEST], {
    encoding: "utf8",
    env: { ...process.env, PRUVO_TARAYICI_KAYNAK: dosya },
  });
  const cikti = (r.stdout || "") + (r.stderr || "");
  const m = /KALAN_IDDIALAR: (.*)/.exec(cikti);
  const kalanlar = m ? m[1].split(" | ").map((s) => s.trim()).filter(Boolean) : [];
  return { rc: r.status, kalanlar, cikti };
}

try {
  // ---- 0) TABAN: mutasyonsuz govde YESIL olmali ----------------------------------
  console.log("\n=== 0) TABAN (mutasyonsuz, index.html'in GERCEK govdesi) ===");
  const taban = kostur("taban", ham);
  console.log("   rc=" + taban.rc + "  kalan=" + taban.kalanlar.length);
  if (taban.rc !== 0) {
    console.log("❌ TABAN KIRMIZI — mutasyon olcumu ANLAMSIZ (once tabani yesile cek).");
    console.log(taban.cikti);
    hata++;
  } else {
    console.log("✅ taban yesil — mutant kirmizilari mutasyona ATFEDILEBILIR.");
  }

  // ---- 1) KONTROL MUTANTI ---------------------------------------------------------
  console.log("\n=== 1) KONTROL MUTANTI (kirmizi 'her duzenlemede' gelmiyor mu?) ===");
  if (kacKez(ham, KONTROL.ara) !== 1) {
    console.log("❌ " + KONTROL.ad + " — CAPA TEKIL DEGIL (" + kacKez(ham, KONTROL.ara) +
      " kez). FAIL-LOUD.");
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

  // ---- 2) MUTANTLAR ---------------------------------------------------------------
  console.log("\n=== 2) MUTANTLAR (tarayici kolunun her korumasi tek tek bozulur) ===");
  const kumeler = [];
  for (const mut of MUTANTLAR) {
    console.log("\n-- " + mut.ad);
    console.log("   kol: " + mut.kol);
    const kez = kacKez(ham, mut.ara);
    if (kez !== 1) {
      console.log("   ❌ CAPA TEKIL DEGIL (" + kez + " kez) — bu kol OLCULEMEDI. FAIL-LOUD.");
      hata++;
      kumeler.push({ ad: mut.ad, kalanlar: null });
      continue;
    }
    const mutasyonlu = ham.replace(mut.ara, mut.yaz);
    if (mutasyonlu === ham) {
      console.log("   ❌ MUTASYON UYGULANMADI (metin ayni) — FAIL-LOUD.");
      hata++;
      kumeler.push({ ad: mut.ad, kalanlar: null });
      continue;
    }
    const r = kostur(mut.ad.split(" ")[0], mutasyonlu);
    console.log("   rc=" + r.rc + "  dusen iddia: " + (r.kalanlar.join(" | ") || "(yok)"));

    if (r.rc === 0) {
      console.log("   ❌ MUTANT YASADI — bu kol test tarafindan OLCULMUYOR " +
        "(yasamak 'kol saglam' degil 'kol olculemedi' demektir).");
      hata++;
    } else {
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

  // ---- 3) GOLGELEME ---------------------------------------------------------------
  console.log("\n=== 3) GOLGELEME KONTROLU (kollar birbirini gizliyor mu?) ===");
  let golge = 0;
  for (let i = 0; i < kumeler.length; i++) {
    for (let j = i + 1; j < kumeler.length; j++) {
      const a = kumeler[i], b = kumeler[j];
      if (!a.kalanlar || !b.kalanlar) { continue; }
      const ayni = a.kalanlar.length === b.kalanlar.length &&
        a.kalanlar.every((x) => b.kalanlar.includes(x));
      if (ayni) {
        console.log("   ❌ " + a.ad + " ile " + b.ad + " AYNI iddialari dusuruyor — " +
          "kollardan biri BAGIMSIZ olculmuyor.");
        hata++; golge++;
      }
    }
  }
  if (!golge) {
    console.log("   ✅ her kolun dusurdugu iddia kumesi FARKLI — kollar bagimsiz olculuyor.");
  }
} finally {
  // DISK KURALI: ureten temizler.
  fs.rmSync(gecici, { recursive: true, force: true });
  console.log("\n[temizlik] gecici dizin silindi: " + gecici +
    " (mevcut mu? " + (fs.existsSync(gecici) ? "EVET — HATA" : "hayir") + ")");
  if (fs.existsSync(gecici)) { hata++; }
  // index.html'e DOKUNULMADIGININ kaniti: bayt uzunlugu ve capa konumu degismedi.
  const sonHtml = fs.readFileSync(INDEX_HTML, "utf8");
  const bozuldu = sonHtml.length !== hamHtml.length || sonHtml.indexOf(BAS_CAPA) !== b0;
  console.log("[kaynak] index.html DEGISMEDI mi? " + (bozuldu ? "HAYIR — HATA" : "evet"));
  if (bozuldu) { hata++; }
}

console.log("\n=== TARAYICI KOLU MUTASYON KANITI: " +
  (hata ? "KIRMIZI (" + hata + " sorun)" : "YESIL") + " ===");
process.exit(hata ? 1 : 0);
