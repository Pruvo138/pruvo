#!/usr/bin/env node
/**
 * KABUL TESTI 5 — /katalog sayfalama dogrulugu + SIRA KORUNUMU (FAZ 3).
 *
 *   node tools/faz3-sayfalama.js                    # yerel wrangler dev (127.0.0.1:8787)
 *   KATALOG_UC=https://.../katalog node tools/faz3-sayfalama.js
 *
 * NE OLCER (iki ayri iddia, ikisi de sessiz hata sinifi):
 *  1) SAYFALAMA: bir gorunumun TUM sayfalari birlestiginde eksik/mukerrer urun YOK ve
 *     toplam sayisi ile birebir tutuyor. (OFFSET sayfalamasinda klasik hata: sinirdaki
 *     urunun atlanmasi/iki kez gelmesi. Gozle bakinca fark edilmez.)
 *  2) SIRA KORUNUMU: D1'in "ORDER BY seq DESC" sirasi, urunler.json DIZI sirasiyla AYNI mi?
 *     Bu bir VARSAYIM, garanti degil — d1-sync.py seq'i urun D1'e ILK girdiginde veriyor
 *     ve bir daha degistirmiyor. Yeni urun urunler.json'un BASINA eklendigi surece seq
 *     dizi sirasiyla ortusuyor. Ama dizinin ORTASINA urun sokulursa (ya da eski bir urun
 *     silinip yeniden eklenirse) D1 sirasi dosya sirasindan AYRISIR ve site "en yeni ustte"
 *     iddiasini sessizce kaybeder. Bayragi acmadan once bu testin YESIL olmasi SART.
 *
 * ONBELLEK: /katalog "max-age=60" ile doner. Nonce olmadan bu test CDN'i olcer, Worker'i
 * degil ([[d1-arama-tuzaklari]] — parite testinde yasandi, bozuk kod YESIL yanmisti).
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 * 🔴 "OLCULEMEDI" ILE "BOZUK" AYRI SINIFTIR (1 Agu 2026 onarimi)
 * ═══════════════════════════════════════════════════════════════════════════════
 * Bu betik ESKIDEN her istek arizasini (uc kapali, DNS, TLS, WAF 403, bos govde)
 * "gorunum ayristi" sayiyordu ve sonunda "SAYFALAMA/SIRA BOZUK ❌" basip cikis 1
 * veriyordu. Olculdu (1 Agu): yerel wrangler kosmuyorken 7/7 gorunum "fetch failed"
 * verdi ve betik SAYFALAMANIN BOZUK OLDUGUNU iddia etti — oysa hicbir sayfa hic
 * gorulmemisti. Bu YANLIS SUCLAMADIR: olculmemis bir sey hakkinda hukum vermek.
 * Kardes arac faz3-gecikme.js bu ayrimi zaten yapiyordu; ikizler AYRISMISTI.
 *
 * CIKIS KODU SOZLESMESI — kardes arac tools/faz3-gecikme.js ile AYNI
 * (tuketici eslemesi tek kaynak: tools/parite-ortak.js "CIKIS KODU SOZLESMESI";
 *  edge-flip-hazirlik.py exit 2 -> BLOKLU, yani ne GO ne suclama):
 *   0 = OLCULDU, sayfalama + sira TAM
 *   1 = OLCULDU ve AYRISTI (gercek gerileme) VEYA uc kendi hatasini bildirdi
 *   2 = OLCULEMEDI (uc cevap vermiyor / yanit JSON degil / yanitta sayfalama
 *       alanlari yok) — ne yesil ne kirmizi
 *
 * 🔴 FAIL-OPEN YASAK: "olculemedi" HICBIR yolla cikis 0 uretmez. Olculemeyen bir
 * eksen yesile donusemez (yonetici ilke: parite-ortak.js).
 * 🔴 KISMI HALDE KIRMIZI BASKIN: 3 gorunum ulasilamadi + 4 gorunum ayristi ise
 * sonuc KIRMIZI'dir (cikis 1). Gerekce: olculemeyen bir kardes gorunum, OLCULMUS
 * bir ayrismayi MASKELEYEMEZ — tersi olsaydi uc bir gorunumde susarak gercek bir
 * sira kirilmasini "olculemedi" diye yutturabilirdi.
 *
 * ⚠️ BLOKE (20 Tem 2026): /katalog ucu canlida YOK (Worker ayri repo ~/dev/pruvo-bot,
 * main'de degil; canli Worker /katalog istegine 403 doner). Bu test uc deploy edilene
 * kadar KOSMAZ — "atlandi" demek "yesil" demek DEGILDIR. Bayragi acmadan once bu test
 * gercek uce karsi YESIL olmali (sayfalama + sira korunumu ikisi de sessiz hata sinifi).
 */

const fs = require("fs");
const path = require("path");

const KOK = path.dirname(__dirname);
const UC = process.env.KATALOG_UC || "http://127.0.0.1:8787/katalog";
const BOY = 100;                 // /katalog sayfa boyu tavani
const NONCE = Date.now().toString(36) + "-" + process.pid;

const PRODUCTS = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));

// Cikis kodlari — kardes arac faz3-gecikme.js ile BIREBIR ayni sozlesme.
const CIK_OK = 0;
const CIK_KIRMIZI = 1;
const CIK_OLCULEMEDI = 2;

// Gorunum durumlari. BOZUK ile HATA'nin ikisi de cikis 1'dir ama SEBEPLERI farklidir
// ve raporda KARISTIRILMAZ: uc hata donduruyorken "sayfalama bozuk" demek yanlis
// suclamadir (yanlis yere bakilir).
const OK = "OK";
const BOZUK = "BOZUK";            // sayfalama/sira GERCEKTEN ayristi (olculdu)
const HATA = "HATA";              // uc AYAKTA ve kendi arizasini bildirdi
const OLCULEMEDI = "OLCULEMEDI";  // uc susuyor / yanit anlamli degil -> hukum YOK

/** Siniflandirilmis olcum hatasi. `sinif` = OLCULEMEDI | HATA | BOZUK. */
class OlcumHatasi extends Error {
  constructor(sinif, mesaj) {
    super(mesaj);
    this.sinif = sinif;
  }
}

/** Tek istek. Ariza SINIFINI belirleyen tek yer burasi. */
async function birDeneme(u) {
  let r;
  try {
    r = await fetch(u, { headers: { "cache-control": "no-cache" } });
  } catch (e) {
    // TASIMA katmani: uc dinlemiyor / DNS / TLS / zaman asimi. Tek bir sayfa bile
    // gormedik -> sayfalama hakkinda soyleyecek HICBIR seyimiz yok.
    throw new OlcumHatasi(OLCULEMEDI, "uca ulasilamadi (" + (e.message || e) + ")");
  }
  let j;
  try {
    j = await r.json();
  } catch (e) {
    // 403 WAF sayfasi / HTML hata sayfasi / bos govde. Uc konusuyor ama BIZIM
    // protokolumuzu konusmuyor -> yine hukum YOK.
    throw new OlcumHatasi(OLCULEMEDI,
      "HTTP " + r.status + " — yanit JSON degil (WAF/hata sayfasi?)");
  }
  if (j && j.hata) {
    // Uc AYAKTA ve KENDI arizasini bildiriyor (D1 baglantisi yok vb.). Gercek bir
    // ariza -> kirmizi; ama sebebi "sayfalama" DEGIL (kardes arac: "ISTEK HATASI").
    throw new OlcumHatasi(HATA, "uc hata bildirdi: " + j.hata);
  }
  if (!r.ok) {
    throw new OlcumHatasi(OLCULEMEDI,
      "HTTP " + r.status + " — uc bu istegi karsilamiyor (deploy/erisim yok)");
  }
  if (!j || !Array.isArray(j.urunler) ||
      typeof j.toplam !== "number" || typeof j.sonSayfa !== "number") {
    // Eski/farkli uc surumu ya da govde degisimi. Alan yoksa sayfalamayi OLCEMEYIZ;
    // eskiden `d.urunler.map` cakiyor ve bu "BOZUK" diye raporlaniyordu.
    throw new OlcumHatasi(OLCULEMEDI,
      "yanitta sayfalama alanlari (urunler/toplam/sonSayfa) yok");
  }
  return j;
}

async function sayfaCek(kategori, marka, sayfa) {
  const u = new URL(UC);
  if (kategori && kategori !== "Tümü") u.searchParams.set("kategori", kategori);
  if (marka && marka !== "Tümü") u.searchParams.set("marka", marka);
  u.searchParams.set("sayfa", String(sayfa));
  u.searchParams.set("boy", String(BOY));
  u.searchParams.set("_nonce", NONCE);
  let son = null;
  for (let deneme = 0; deneme < 3; deneme++) {
    try {
      return await birDeneme(u);
    } catch (e) {
      son = (e instanceof OlcumHatasi) ? e
        : new OlcumHatasi(OLCULEMEDI, "beklenmeyen hata: " + (e.message || e));
      if (deneme === 2) throw son;
      await new Promise((res) => setTimeout(res, 400 * (deneme + 1)));
    }
  }
  throw son;
}

/** Bir gorunumun butun sayfalarini gezip id listesini sirasiyla toplar. */
async function tumSayfalar(kategori, marka) {
  const ids = [];
  let sayfa = 1, toplam = null, sonSayfa = null;
  while (true) {
    const d = await sayfaCek(kategori, marka, sayfa);
    if (toplam === null) { toplam = d.toplam; sonSayfa = d.sonSayfa; }
    ids.push(...d.urunler.map((u) => u.id));
    if (sayfa >= d.sonSayfa || d.urunler.length === 0) break;
    sayfa++;
    // Fren ATESLENDIYSE uc hala urun donduruyor ama sonSayfa/toplam ile tutmuyor:
    // bu OLCULMUS bir sayfalama tutarsizligidir -> BOZUK (olculemedi DEGIL).
    if (sayfa > 5000) {
      throw new OlcumHatasi(BOZUK,
        "SAYFA DONGUSU BITMEDI: 5000 sayfa asildi, sonSayfa=" + sonSayfa +
        " toplam=" + toplam + " ile tutmuyor (guvenlik freni)");
    }
  }
  return { ids, toplam, sonSayfa, sayfaSayisi: sayfa };
}

/** urunler.json'un o gorunum icin BEKLENEN sirasi (dosya sirasi = en yeni ustte). */
function beklenen(kategori, marka) {
  return PRODUCTS.filter((p) => {
    const katOk = !kategori || kategori === "Tümü" || p.kategori === kategori;
    const markaOk = !marka || marka === "Tümü" || (p.marka || []).indexOf(marka) !== -1;
    return katOk && markaOk;
  }).map((p) => p.id);
}

const gorunumler = [
  { kategori: "Tümü", marka: "Tümü" },
  { kategori: "Marin", marka: "Tümü" },
  { kategori: "Otomobil", marka: "Tümü" },   // en buyuk kume (20 Tem: 6.626) — derin OFFSET
  { kategori: "Tamirat", marka: "Tümü" },
  { kategori: "Elektronik", marka: "Tümü" },
  { kategori: "Tümü", marka: "Yamaha" },
  { kategori: "Otomobil", marka: "Toyota" },
];

(async () => {
  console.log("Sayfalama + sira testi | uc: %s | %d urun", UC, PRODUCTS.length);
  // NOT: bu satir hukum KELIMELERINI (bozuk/olculemedi) ICERMEZ — cikti uzerinden
  // hukum arayan cagiranlar/kabul testleri banner'i "sonuc" saymasin.
  console.log("(uca ulasilamazsa hukum VERILMEZ -> cikis %d; olculmus ayrisma -> cikis %d)\n",
    CIK_OLCULEMEDI, CIK_KIRMIZI);
  const durumlar = [];

  for (const g of gorunumler) {
    const ad = "kategori=" + g.kategori + " marka=" + g.marka;
    let r;
    try {
      r = await tumSayfalar(g.kategori, g.marka);
    } catch (e) {
      const sinif = (e instanceof OlcumHatasi) ? e.sinif : OLCULEMEDI;
      if (sinif === BOZUK) {
        console.log("  ❌ %s -> %s", ad, e.message);
      } else if (sinif === HATA) {
        console.log("  ❌ %s -> ISTEK HATASI: %s", ad, e.message);
      } else {
        // Hicbir sayfa gorulmedi ya da yanit anlamsiz: SUCLAMA YOK, hukum de YOK.
        console.log("  ⚪ %s -> OLCULEMEDI: %s", ad, e.message);
      }
      durumlar.push(sinif);
      continue;
    }
    const bek = beklenen(g.kategori, g.marka);
    const hatalar = [];

    // 1) mukerrer yok
    const benzersiz = new Set(r.ids);
    if (benzersiz.size !== r.ids.length) {
      hatalar.push("MUKERRER: " + (r.ids.length - benzersiz.size) + " tekrar eden id");
    }
    // 2) toplam tutuyor
    if (r.toplam !== bek.length) {
      hatalar.push("SAYI: /katalog=" + r.toplam + " urunler.json=" + bek.length);
    }
    // 3) butun sayfalar birlesince kume tam (eksik yok)
    if (r.ids.length !== bek.length) {
      hatalar.push("TOPLANAN: " + r.ids.length + " kart geldi, beklenen " + bek.length);
    }
    // 4) SIRA: dosya sirasiyla birebir (en yeni ustte)
    const ilkFark = r.ids.findIndex((id, i) => id !== bek[i]);
    if (ilkFark !== -1 && r.ids.length === bek.length) {
      hatalar.push("SIRA " + ilkFark + ". kartta ayristi: /katalog=" + r.ids[ilkFark] +
                   " urunler.json=" + bek[ilkFark]);
    }

    if (hatalar.length) {
      durumlar.push(BOZUK);
      console.log("  ❌ %s (%d sayfa)", ad, r.sayfaSayisi);
      for (const h of hatalar) console.log("       " + h);
    } else {
      durumlar.push(OK);
      console.log("  ✅ %s — %d urun / %d sayfa, sira ve kume birebir", ad, r.toplam, r.sayfaSayisi);
    }
  }

  // ONCELIK (kardes arac ile ayni): olculmus ariza (BOZUK/HATA) her seyi bastirir —
  // olculemeyen bir gorunum, olculmus bir ayrismayi MASKELEMEZ. Sonra OLCULEMEDI.
  const bozuk = durumlar.filter((d) => d === BOZUK).length;
  const hatali = durumlar.filter((d) => d === HATA).length;
  const olculemedi = durumlar.filter((d) => d === OLCULEMEDI).length;

  if (bozuk || hatali) {
    if (bozuk) {
      console.log("\nSONUC: SAYFALAMA/SIRA BOZUK ❌ (%d gorunum ayristi)", bozuk);
    }
    if (hatali) {
      console.log((bozuk ? "" : "\n") +
        "SONUC: ISTEK HATASI ❌ (%d gorunum) — sayfalama DEGIL, uc hata donduruyor.", hatali);
    }
    if (olculemedi) console.log("       (ayrica %d gorunum OLCULEMEDI)", olculemedi);
    process.exit(CIK_KIRMIZI);
  }
  if (olculemedi) {
    console.log("\nSONUC: OLCULEMEDI ⚪ (%d gorunum) — ne yesil ne kirmizi. Cikis %d.",
      olculemedi, CIK_OLCULEMEDI);
    console.log("       Sebep: uc cevap vermiyor VEYA yanit anlamli JSON degil " +
      "(sayfalama alanlari yok). Hicbir sayfa gorulmeden AYRISMA hukmu VERILMEZ.");
    process.exit(CIK_OLCULEMEDI);
  }
  console.log("\nSONUC: SAYFALAMA + SIRA KORUNUMU TAM ✅ (%d gorunum)", gorunumler.length);
  process.exit(CIK_OK);
})();
