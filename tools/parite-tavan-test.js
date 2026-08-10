#!/usr/bin/env node
"use strict";
/**
 * SUPURME TAVANI OLCEK KAPISI — tavan SABIT DEGIL, KATALOG BOYUTUNDAN TURER.
 *
 *   node tools/parite-tavan-test.js                # kabul iddialari
 *   node tools/parite-tavan-test.js --kendini-test # kabul + MUTASYON bataryasi
 *
 * NEDEN VAR (olculdu 5-6 Agu 2026): `SUPURME_TAVANI` sabit 200 parti = 20.000 id idi.
 * Katalog 20.212'ye cikinca tavan ASILDI. Yerel ve canli sayilar ESITKEN supurme hic
 * kosmadigi icin bu gorunmuyordu; sayilar ayristigi ANDA "yerel ⊆ D1" kaniti uretilemedi,
 * siniflandirma kapandi ve katalog farkiyla ACIKLANABILIR her sapma KIRMIZI yandi
 * (bir kosumda 526 sahte kirmizi). Yani sabit sayi, katalog buyudugu icin testin KENDISINI
 * bozan bir zaman bombasiydi ([[katalog-olcek-siniri]] · [[hukum-yanlis-birimde]]).
 *
 * 🔴 KAPININ KENDI OLCEK BAYATLAMASI (olculdu 10 Agu 2026) — ESKI K2 KALDIRILDI.
 * Eski K2 ekseni "katalog IKI KATINA cikarilmis fiksturde de supurme EKSIKSIZ" diyordu.
 * Bu iddia kapinin KENDI ust-sinir iddialariyla CELISIYORDU: katalog 25.008 id'ye cikinca
 * 2x = 50.016 id = 501 parti istedi, 500 partilik MUTLAK sinir bunu kapatti -> TAVAN
 * carpti, 0/501 parti kosuldu, K2 KIRMIZI yandi. Sebep REGRESYON DEGIL OLCEK'ti: katalog
 * mutlak sinirin YARISINI gectigi an "2x bugun" matematiksel olarak imkansiz hale geldi
 * ([[katalog-olcek-siniri]] · [[bayat-kabul-testi]]). (Bu tarihli bir OLCUMDUR, capa
 * DEGIL: bugunku katalog boyu asagida KOSUM ANINDA okunur.)
 *
 * 🔴 MUTLAK PARTI BANDI ([50..1000]) DENENDI ve GERI CEKILDI (mimar karari, 10 Agu 2026).
 * Once "mutlak sinir sabit bir parti bandinda kalmali" diye olculuyordu. YANLIS
 * INVARYANTTI: "yerel ⊆ D1" kaniti DOGASI GEREGI ceil(n/IDS_PARTI) istek ISTER; katalogun
 * ALTINDA bir tavan, buyuk katalogda pariteyi ASLA kanitlayamamak demektir — 526 sahte
 * kirmiziyi ureten bomba tam olarak buydu. Tavan artik KATALOG-GORELIDIR (parite-ortak.js:
 * `mutlakTavan()`), ve bu sinifi KOKTEN kapatir.
 * KAYBEDILMEMESI GEREKEN UC SEY ise burada olculmeye DEVAM eder:
 *   (1) tavan FIILEN UYGULANIYOR (K3'un "bir parti otesi" ekseni),
 *   (2) tavan DOYUYOR — kaldirilirsa yakalanir (K2 DOYMA; kat orani bunu YAKALAYAMAZ,
 *       cunku sinir kalkinca oran 1,0'a duser ve banttan GECER),
 *   (3) butce katalogla ORANTILI kaliyor, kat kat PATLAMIYOR (K3 kat orani, ust KAT_UST).
 *
 * 🔴 IDDIA BOLUNDU (celiski boyle kalkti — [[hukum-yanlis-birimde]]): "tavan sabit degil"
 * ile "supurme eksiksiz" AYRI onermelerdir ve AYRI birimlerde olculur.
 *   · "TAVAN SABIT DEGIL" = supurmeTavani'nin TUREVI hakkinda bir onerme. SAF fonksiyon;
 *     canliya da sahte uca da 0 istek, hic supurme yok. Olcum noktalari BUTCE
 *     PENCERESINDEN turer (mutlak sinirin ceyregi/yarisi), bugunku katalogdan DEGIL ->
 *     bu eksen bir daha ASLA bayatlamaz.
 *   · "SUPURME EKSIKSIZ" = butcenin IZIN VERDIGI her katalog icin gecerli olmali; dogru
 *     sinav noktasi "2x bugun" degil TAM SINIR (mutlak x IDS_PARTI id) ve sinirin BIR
 *     PARTI otesidir. Bu, eski K2'den DAHA GUCLU: "2x bugun" rastgele bir noktaydi, tam
 *     sinir butce SOZLESMESININ KENDISIDIR.
 *   · Katalog buyumesi ise AYRI ve DURUST bir eksende olculur: tavan katalogun ALTINA
 *     dusmus mu (K3), katalogun kac katina cikmis (K3 kat orani), tek kanit kosumunun
 *     CANLI MALIYETI ne (K7 erken uyarisi).
 *
 * BU KAPININ IDDIALARI:
 *   K1  BUGUNKU katalog boyunda supurme EKSIKSIZ (tavan carpMAZ, tum partiler kosar),
 *   K1b POZITIF TANIMA: uc birkac id'yi BILEREK gizlerse supurme onlari YAKALAR. "Eksik
 *       0" tek basina FAIL-OPEN'dir (hic istek atilmasa da 0 gelir); ayrica "TUM partiler
 *       kosuldu" da bolme aritmetigidir — bu yuzden her supurme ekseninde FIILEN atilan
 *       /katalog?ids= istegi (idsIstek) AYRICA olculur ([[beyan-edilmis-survivor]]),
 *   K2  TAVAN SABIT DEGIL + DOYUYOR: supurmeTavani pencere icinde BIREBIR ceil(n/IDS_PARTI)
 *       ve n buyudukce BUYUYOR, ama MUTLAK sinirda DOYAR (iki noktada olculur; SAF, 0 istek),
 *   K3  BUTCE ORANI: tavan katalogun ALTINA dusMEZ (yoksa parite ASLA kanitlanamaz) ve
 *       katalogun KAT_UST katini ASMAZ (yoksa sinir degil sinirsiz butcedir); TAM SINIRDA
 *       supurme EKSIKSIZ, BIR PARTI OTESINDE ust sinir DURUYOR ve butce PATLAMIYOR,
 *   K4  tavan asildiginda hukum ACIK OLCULEMEDI'dir, sessiz yanlis-kirmizi DEGIL,
 *   K5  MUTLAK SINIRIN KENDISI de katalogdan TURER: gercek katalogu FIILEN okur, testin
 *       BAGIMSIZ sayimiyla ayni sayiyi gorur ve turetimin SONUCUNA BIREBIR esittir,
 *   K6  FAIL-CLOSED TABAN: katalog OKUNAMAZSA sinir TABANA duser (sinirsiz butce ACILMAZ)
 *       ve taban KULLANILABILIR kalir (kabul tabani boyundaki katalog yine kanitlanabilir),
 *   K7  (IDDIA DEGIL, ERKEN UYARI) tek kanit kosumunun CANLI MALIYETI basilir; esigi
 *       gecerse uyarir ama deploy'u DURDURMAZ ([[kapi-birikimi-yayin-gecikmesi]]).
 *
 * 🔴 SIRA ONEMLI (K3): oran asilmissa supurme eksenleri KOSULMAZ — tavani katalogun 400
 * katina ceken bir mutant testi milyonlarca istege suruklerdi. Atlama SESSIZ DEGIL:
 * imzaya "K3 oran=ASILDI" yazilir ve ilgili iddialar KIRMIZI sayilir.
 *
 * 🔴 VERI CAPASI YOK: hicbir gercek urun id'si yok; id'ler kosum aninda uretilir. Bugunku
 * katalog boyu KOSUM ANINDA katalogdan okunur, butce penceresi ise OLCULEN YOLUN kendi
 * sabitlerinden turer — ikisi de dosyaya SABIT YAZILMAZ.
 *
 * 🔴 MUTASYON KOPYAYA UYGULANIR: canli tools/parite-ortak.js'e ASLA yazilmaz (bir kesinti
 * canliya mutant birakirdi — [[mutasyon-diske-yazma-tuzagi]]). Kabul cikis kodu DEGIL,
 * OLCULEN IMZA'dir; cokme kirmiziyla KARISTIRILMAZ ([[mutasyon-kaniti-yeniden-uretilebilir]]).
 *
 * 🔴 SABITLER OLCULEN YOLDAN OKUNUR: IDS_PARTI / SUPURME_MUTLAK_TAVAN degerleri canli
 * dosyadan DEGIL, `sabitler(ortakYolu)` ile o an olculen KOPYADAN alinir. Aksi halde
 * sabiti degistiren bir mutant (M4) KOR kalirdi.
 */

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");

const ORTAK = path.join(__dirname, "parite-ortak.js");

let _gecti = 0;
const _kaldi = [];
function ONA(kosul, ad, ek) {
  if (kosul) { _gecti++; console.log("   ✅ " + ad); return; }
  _kaldi.push(ad);
  console.log("   ❌ " + ad + (ek ? "\n      " + String(ek).slice(0, 400) : ""));
}

// ── SAHTE /katalog UCU — yalniz supurmenin ihtiyaci kadar ─────────────────────────────
// `ids=` gelen id'leri AYNEN dondurur (hepsi D1'de VAR demektir); `boy=1` toplam sayar.
// 🔴 `gizli` kumesindeki id'ler BILEREK DUSURULUR: "D1'de YOK" halini uretir. Bu, kapinin
// POZITIF TANIMA izidir — `eksik === 0` tek basina FAIL-OPEN'dir (hicbir istek atilmasa
// da 0 gelir), supurmenin FIILEN AYIRT ETTIGI ancak gizlenen id'ler YAKALANINCA kanitlanir
// ([[beyan-edilmis-survivor]] · [["Olculdu" diyen hukum kaniti]]).
function sunucuKur(toplam, gizli) {
  const gizliKume = gizli || new Set();
  const durum = { istek: 0, idsIstek: 0 };
  const s = http.createServer((req, res) => {
    durum.istek++;
    const u = new URL(req.url, "http://127.0.0.1");
    const ids = u.searchParams.get("ids");
    let govde;
    if (ids) {
      durum.idsIstek++;
      govde = { urunler: ids.split(",").filter((id) => !gizliKume.has(id)).map((id) => ({ id })) };
    } else {
      govde = { toplam, urunler: [] };
    }
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(govde));
  });
  return new Promise((c) => s.listen(0, "127.0.0.1", () => c({
    kapat: () => new Promise((k) => s.close(k)),
    uc: "http://127.0.0.1:" + s.address().port + "/ara",
    durum,
  })));
}

function idlerUret(n) {
  const l = new Array(n);
  for (let i = 0; i < n; i++) l[i] = "u" + i;
  return l;
}

/**
 * TEK KOSUM = tek olcum imzasi. Mutant da taban da AYNI fonksiyondan gecer.
 * Doner: { tavan, parti, eksik, idsIstek, hataTur, cokme }
 */
async function olc(ortakYolu, idAdedi, ekEnv, gizleAdedi) {
  const eski = {};
  for (const a of Object.keys(ekEnv || {})) { eski[a] = process.env[a]; process.env[a] = ekEnv[a]; }
  delete require.cache[require.resolve(ortakYolu)];
  const o = require(ortakYolu);
  const idler = idlerUret(idAdedi);
  // `gizleAdedi` kadar id'yi uc BILEREK gizler (idlerUret AYNI oneki urettigi icin
  // gizlenenler daima korpusun ICINDEDIR) -> supurme onlari YAKALAMALI.
  const sunucu = await sunucuKur(idAdedi, new Set(idlerUret(gizleAdedi || 0)));
  const sayac = o.sayacYeni();
  const cikti = { tavan: null, parti: 0, eksik: null, idsIstek: 0, hataTur: null, cokme: null };
  try {
    cikti.tavan = o.supurmeTavani(idAdedi);
    const eksik = await o.d1deOlmayanlar(sunucu.uc, idler, sayac, o.nonceUret());
    cikti.eksik = eksik.length;
  } catch (e) {
    if (e && e.olcum) cikti.hataTur = e.tur;
    else cikti.cokme = String((e && e.message) || e).slice(0, 200);
  } finally {
    cikti.parti = sayac.supurmeParti || 0;
    cikti.idsIstek = sunucu.durum.idsIstek;
    await sunucu.kapat();
    for (const a of Object.keys(ekEnv || {})) {
      if (eski[a] === undefined) delete process.env[a]; else process.env[a] = eski[a];
    }
    delete require.cache[require.resolve(ortakYolu)];
  }
  return cikti;
}

/** On-kosul ekseni: tavan asilinca `durdu` (ACIK OLCULEMEDI) doner mi? */
async function olcOnKosul(ortakYolu, idAdedi, ekEnv) {
  const eski = {};
  for (const a of Object.keys(ekEnv || {})) { eski[a] = process.env[a]; process.env[a] = ekEnv[a]; }
  delete require.cache[require.resolve(ortakYolu)];
  const o = require(ortakYolu);
  // canliSayi != yerelSayi olsun ki supurme FIILEN tetiklensin (esitse hic kosmaz).
  const sunucu = await sunucuKur(idAdedi + 5);
  const cikti = { durdu: null, kirmizi: null, olculemedi: 0, cokme: null };
  try {
    const r = await o.onKosulOlc({
      uc: sunucu.uc, yerelIdler: idlerUret(idAdedi), sayac: o.sayacYeni(), nonce: o.nonceUret(),
    });
    cikti.durdu = r.durdu || null;
    cikti.kirmizi = r.kirmizi || null;
    cikti.olculemedi = (r.olculemedi || []).length;
  } catch (e) {
    cikti.cokme = String((e && e.message) || e).slice(0, 200);
  } finally {
    await sunucu.kapat();
    for (const a of Object.keys(ekEnv || {})) {
      if (eski[a] === undefined) delete process.env[a]; else process.env[a] = eski[a];
    }
    delete require.cache[require.resolve(ortakYolu)];
  }
  return cikti;
}

// ── OLCEK EKSENLERI ───────────────────────────────────────────────────────────────────
// BUGUNKU boy kosum aninda katalogdan OKUNUR (sabit yazilsaydi kapinin kendisi bayatlardi:
// katalog buyuyunce iddia yine 20.212'yi olcerdi). Katalog okunamazsa eksen ATLANMAZ,
// mimarin kabul olcutundeki sayi TABAN olarak kullanilir ve bu ACIKCA yazilir.
const KABUL_TABANI = 20212;
function bugunkuBoy() {
  try {
    const j = JSON.parse(fs.readFileSync(path.join(path.dirname(__dirname), "urunler.json"),
      "utf8"));
    const n = new Set(j.map((u) => u && u.id).filter(Boolean)).size;
    return { n: Math.max(n, KABUL_TABANI), ham: n,
             kaynak: "urunler.json (" + n + " benzersiz id)" };
  } catch (e) {
    return { n: KABUL_TABANI, ham: null,
             kaynak: "katalog OKUNAMADI -> kabul olcutu tabani" };
  }
}

// Butce/tavan fikstur env'leri. SABITLER ve SAF TUREV bu degiskenlerden ETKILENMEZ:
// kanonik degerler daima TEMIZ env'le okunur (K4 kendi env'ini olc/olcOnKosul icinde
// verir ve geri alir).
const SABIT_ENV = ["PARITE_SUPURME_MUTLAK", "PARITE_SUPURME_TAVANI"];

function temizEnvde(is) {
  const eski = {};
  for (const a of SABIT_ENV) { eski[a] = process.env[a]; delete process.env[a]; }
  try {
    return is();
  } finally {
    for (const a of SABIT_ENV) {
      if (eski[a] === undefined) delete process.env[a]; else process.env[a] = eski[a];
    }
  }
}

/**
 * OLCULEN YOLUN sabitleri + saf turevi. Doner:
 *   { IDS_PARTI, SUPURME_MUTLAK_TAVAN, supurmeTavani }
 * 🔴 DAIMA `ortakYolu`ndan okunur (mutant KOPYASI dahil): canli dosyadan sabit okuyup
 * mutant kopyayi olcmek sabiti degistiren mutanti KOR EDERDI. `require.cache` hem oncesinde
 * hem sonrasinda temizlenir; donen `supurmeTavani` da temiz env'le cagrilir.
 */
function sabitler(ortakYolu) {
  return temizEnvde(() => {
    delete require.cache[require.resolve(ortakYolu)];
    const o = require(ortakYolu);
    const s = {
      IDS_PARTI: o.IDS_PARTI,
      SUPURME_MUTLAK_TAVAN: o.SUPURME_MUTLAK_TAVAN,
      supurmeTavani: (n) => temizEnvde(() => o.supurmeTavani(n)),
      // MUTLAK sinirin KENDI turetimi (main'in yeni yuzeyi). Yoksa null -> iddia kirmizi.
      katalogIdAdedi: typeof o.katalogIdAdedi === "function" ? o.katalogIdAdedi : null,
      MUTLAK_KAT: o.MUTLAK_KAT === undefined ? null : o.MUTLAK_KAT,
      MUTLAK_TABAN_PARTI: o.MUTLAK_TABAN_PARTI === undefined ? null : o.MUTLAK_TABAN_PARTI,
    };
    delete require.cache[require.resolve(ortakYolu)];
    return s;
  });
}

/**
 * FAIL-CLOSED AYAGI (K6): modulu KATALOGUN BULUNAMAYACAGI bir kokte yukler.
 * `katalogYolunuBul()` hem `__dirname`den hem `process.cwd()`den yukari yurudugu icin
 * IKISINI BIRDEN repo disina almak gerekir: kopya /tmp'ye yazilir VE cwd oraya cekilir.
 * Doner: { mutlak, n, taban, cokme }. Kosum bittiginde cwd ve memo GERI ALINIR.
 */
function olcKataloksuz(ortakYolu) {
  const kok = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-tavan-koksuz-"));
  const kopya = path.join(kok, "parite-ortak.js");
  fs.writeFileSync(kopya, fs.readFileSync(ortakYolu, "utf8"));
  const eskiCwd = process.cwd();
  const eskiMemo = globalThis.__PRUVO_PARITE_KATALOG_SAYIM;
  const cikti = { mutlak: null, n: null, taban: null, cokme: null };
  try {
    delete globalThis.__PRUVO_PARITE_KATALOG_SAYIM;   // bayat memo sizdirmasin
    process.chdir(kok);
    temizEnvde(() => {
      delete require.cache[require.resolve(kopya)];
      const o = require(kopya);
      cikti.mutlak = o.SUPURME_MUTLAK_TAVAN === undefined ? null : o.SUPURME_MUTLAK_TAVAN;
      cikti.n = typeof o.katalogIdAdedi === "function" ? o.katalogIdAdedi() : null;
      cikti.taban = o.MUTLAK_TABAN_PARTI === undefined ? null : o.MUTLAK_TABAN_PARTI;
      delete require.cache[require.resolve(kopya)];
    });
  } catch (e) {
    cikti.cokme = String((e && e.message) || e).slice(0, 200);
  } finally {
    process.chdir(eskiCwd);
    if (eskiMemo === undefined) delete globalThis.__PRUVO_PARITE_KATALOG_SAYIM;
    else globalThis.__PRUVO_PARITE_KATALOG_SAYIM = eskiMemo;
    fs.rmSync(kok, { recursive: true, force: true });
  }
  return cikti;
}

// ── BUTCE ORANI — K3'un ilk kapisi (gerekce dosya basinda) ────────────────────────────
// 🔴 MUTLAK PARTI BANDI ([50..1000]) KALDIRILDI (mimar karari, 10 Agu 2026). Yanlis
// invaryantti: "yerel ⊆ D1" kaniti dogasi geregi ceil(n/IDS_PARTI) istek ISTER; katalogun
// ALTINDA bir tavan, buyuk katalogda pariteyi ASLA kanitlayamamak demektir — 526 sahte
// kirmiziyi ureten bomba tam olarak buydu. Katalog-goreli tavan bu sinifi KOKTEN kapatir.
// Korunan sey artik sinirin DEGERI degil, ORANI: tavan katalogun KAT_UST katini asiyorsa
// o artik "ariza isareti yakalayan sinir" degil SINIRSIZ BUTCEDIR (1 parti = 1 canli
// istek). Alt ucta ise tavan katalogun ALTINA dusemez, yoksa kanit uretilemez.
const KAT_UST = 10;

// K7 CANLI MALIYET esigi: tek kanit kosumunun atacagi canli istek sayisi. Iddia DEGIL.
const CANLI_MALIYET_UYARI = 1000;

// POZITIF TANIMA kosumunda ucun BILEREK gizledigi id sayisi (bkz. K1b).
const GIZLI_ADET = 3;

async function kabulKos(ortakYolu, sessiz) {
  const yaz = sessiz ? () => {} : (s) => console.log(s);
  const boy = bugunkuBoy();
  const sbt = sabitler(ortakYolu);
  const IDS = sbt.IDS_PARTI;
  const MUTLAK = sbt.SUPURME_MUTLAK_TAVAN;
  const gerekliBugun = Math.ceil(boy.n / IDS);
  const imza = [];

  // K1 — BUGUNKU katalog: supurme EKSIKSIZ. ("Katalog butceye SIGIYOR" iddiasi K3'e
  // TASINDI: orada `MUTLAK >= gerekliBugun` olarak, kat orani ile AYNI eksende olculur.)
  const bugun = await olc(ortakYolu, boy.n, {});
  imza.push("K1 tavan=" + bugun.tavan + " parti=" + bugun.parti + " idsIstek=" + bugun.idsIstek +
    " eksik=" + bugun.eksik +
    " hata=" + bugun.hataTur + " cokme=" + (bugun.cokme ? "VAR" : "yok") +
    " gerekli=" + gerekliBugun + " mutlak=" + MUTLAK);
  yaz("\n▶ K1 BUGUNKU KATALOG (" + boy.n + " id · " + boy.kaynak + ") -> supurme EKSIKSIZ");
  if (!sessiz) {
    ONA(bugun.cokme === null, "surec COKMEDI", bugun.cokme);
    ONA(bugun.hataTur === null, "TAVAN carpMADI (sabit 200 parti burada patliyordu)");
    ONA(bugun.parti === gerekliBugun,
      "TUM partiler kosuldu: " + bugun.parti + "/" + gerekliBugun);
    // 🔴 ICRA IZI: `parti` sayaci supurme DONGUSUNDEN ONCE artar (parite-ortak.js) —
    // yani tek basina bolme aritmetigidir, ISTEK ATILDIGININ kaniti DEGILDIR. Hukmu
    // FIILEN atilan /katalog?ids= istegine capaliyoruz ([[beyan-edilmis-survivor]]).
    ONA(bugun.idsIstek === gerekliBugun, "supurme FIILEN KOSTU: " + bugun.idsIstek + "/" +
      gerekliBugun + " /katalog?ids= istegi ATILDI (parti sayaci TEK BASINA kanit degil)");
    ONA(bugun.eksik === 0, "'yerel ⊆ D1' kaniti URETILDI (eksik 0)");
  }

  // K1b — POZITIF TANIMA (kontrol kosumu): uc GIZLI_ADET id'yi BILEREK gizler, supurme
  // onlari YAKALAMALI. 🔴 NEDEN VAR: "eksik === 0" tek basina FAIL-OPEN'dir — eksik
  // listesini hic doldurmayan bir mutant da, hic istek atmayan bir mutant da 0 uretir.
  // Temiz hukum ("eksik yok") ancak POZITIF TANIMA IZIYLE kanit olur.
  const pozitif = await olc(ortakYolu, boy.n, {}, GIZLI_ADET);
  imza.push("K1b idsIstek=" + pozitif.idsIstek + " eksik=" + pozitif.eksik +
    " gizli=" + GIZLI_ADET + " hata=" + pozitif.hataTur +
    " cokme=" + (pozitif.cokme ? "VAR" : "yok"));
  yaz("\n▶ K1b POZITIF TANIMA (uc " + GIZLI_ADET + " id'yi BILEREK gizliyor) -> supurme " +
    "YAKALAMALI");
  if (!sessiz) {
    ONA(pozitif.cokme === null, "surec COKMEDI", pozitif.cokme);
    ONA(pozitif.hataTur === null, "TAVAN carpMADI (ayni katalog boyu)");
    ONA(pozitif.idsIstek === gerekliBugun, "supurme FIILEN KOSTU: " + pozitif.idsIstek + "/" +
      gerekliBugun + " istek ATILDI");
    ONA(pozitif.eksik === GIZLI_ADET, "GIZLENEN id'ler YAKALANDI: eksik=" + pozitif.eksik +
      " (beklenen " + GIZLI_ADET + ") -> 'eksik 0' hukmu POZITIF TANIMA IZINE dayaniyor");
  }

  // K2 — TAVAN SABIT DEGIL (SAF TUREV). Olcum noktalari BUTCE PENCERESINDEN turer,
  // bugunku katalogdan DEGIL -> bu eksen bir daha bayatlamaz. Sunucu KURULMAZ, 0 istek.
  const p1 = Math.max(2, Math.floor(MUTLAK / 4));
  const p2 = Math.max(p1 + 1, Math.floor(MUTLAK / 2));
  const n1 = p1 * IDS;
  const n2 = p2 * IDS;
  const t1 = sbt.supurmeTavani(n1);
  const t2 = sbt.supurmeTavani(n2);
  const tBugun = sbt.supurmeTavani(boy.n);
  const tBugunBeklenen = Math.min(gerekliBugun, MUTLAK);
  // 🔴 DOYMA — GUARD'IN BIRINCI SAVUNMASI. Katalog-goreli tavanda "kat orani" bandi
  // "sinir tamamen kaldirildi"yi YAKALAYAMAZ: kaldirilinca oran 1,0'a duser ve banttan
  // GECER. Ust sinirin FIILEN DURDUGUNU yalniz bu SAF iddia gosterir. Ayrica K3'un
  // supurme ekseni oran kapisina TABIDIR (asilinca ATLANIR) — off-by-one bir mutant o an
  // KOR kalirdi ([[kapi-yan-etkisi-gizli-onkosul]]). IKI NOKTADA olculur (sinirin hemen
  // otesi + cok otesi), ikisi de 0 istek.
  const nDoygun1 = (MUTLAK + 1) * IDS;
  const nDoygun2 = MUTLAK * IDS * 3;
  const tDoygun1 = sbt.supurmeTavani(nDoygun1);
  const tDoygun2 = sbt.supurmeTavani(nDoygun2);
  imza.push("K2 p1=" + p1 + " t1=" + t1 + " p2=" + p2 + " t2=" + t2 +
    " tBugun=" + tBugun + " beklenen=" + tBugunBeklenen +
    " tDoygun1=" + tDoygun1 + " tDoygun2=" + tDoygun2);
  yaz("\n▶ K2 TAVAN SABIT DEGIL (saf turev · butce penceresi " + n1 + " -> " + n2 +
    " id · canliya ve sahte uca 0 istek)");
  if (!sessiz) {
    ONA(t1 === p1, "pencere icinde formul BIREBIR ceil(n/" + IDS + "): t(" + n1 + ")=" +
      t1 + " (beklenen " + p1 + ")");
    ONA(t2 === p2, "pencere icinde formul BIREBIR ceil(n/" + IDS + "): t(" + n2 + ")=" +
      t2 + " (beklenen " + p2 + ")");
    ONA(t2 > t1, "tavan SABIT DEGIL: " + t1 + " -> " + t2 + " (katalogla BIRLIKTE buyuyor)");
    ONA(tBugun === tBugunBeklenen, "turev BUGUNKU katalogda da gecerli: t(" + boy.n + ")=" +
      tBugun + " (beklenen " + tBugunBeklenen + ")");
    ONA(tDoygun1 === MUTLAK, "DOYMA (sinirin hemen otesi): t(" + nDoygun1 + ")=" + tDoygun1 +
      " (beklenen " + MUTLAK + ")");
    ONA(tDoygun2 === MUTLAK, "DOYMA (sinirin 3 KATI otesi): t(" + nDoygun2 + ")=" + tDoygun2 +
      " (beklenen " + MUTLAK + ") -> ust sinir FIILEN DURUYOR; oran bandi bunu YAKALAYAMAZ " +
      "(sinir kalkinca oran 1,0'a duser ve banttan GECER)");
  }

  // K3 — BUTCE SINIRI (kanonik; fikstur env'i YOK). ONCE BANT, SONRA SUPURME: bant
  // asilmissa supurme KOSULMAZ, aksi halde tavani 100.000'e ceken bir mutant testi
  // milyonlarca istege suruklerdi. Atlama SESSIZ DEGIL — imzaya yazilir, iddia KIRMIZI.
  const kanitlanabilir = MUTLAK >= gerekliBugun;
  const kat = MUTLAK / gerekliBugun;
  const katYazi = kat.toFixed(1).replace(".", ",");
  const oranTamam = kanitlanabilir && kat <= KAT_UST;
  yaz("\n▶ K3 BUTCE ORANI (mutlak=" + MUTLAK + " parti · gerekli=" + gerekliBugun +
    " parti · kat=" + katYazi + " · ust " + KAT_UST + ")");
  if (!sessiz) {
    ONA(kanitlanabilir, "BUGUNKU KATALOG KANITLANABILIR: tavan katalogun ALTINA dusmedi (" +
      MUTLAK + " >= " + gerekliBugun + " parti)",
      "TAVAN KATALOGUN ALTINDA: " + MUTLAK + " < " + gerekliBugun + " parti. 'Yerel ⊆ D1' " +
      "kaniti dogasi geregi ceil(n/" + IDS + ") istek ISTER; bu haliyle parite bu katalogda " +
      "ASLA kanitlanamaz — 526 sahte kirmiziyi ureten sinif budur.");
    ONA(kat <= KAT_UST, "butce katalogla ORANTILI: kat=" + katYazi + " <= " + KAT_UST,
      "BUTCE KAT KAT PATLADI: tavan katalogun " + katYazi + " kati (ust " + KAT_UST + "). " +
      "1 parti = 1 canli istek; tavan katalogun " + KAT_UST + " katini asiyorsa artik " +
      "'ariza isareti yakalayan sinir' degil SINIRSIZ BUTCEDIR.");
  }
  if (!oranTamam) {
    imza.push("K3 oran=ASILDI mutlak=" + MUTLAK + " gerekli=" + gerekliBugun);
    yaz("   ⛔ ORAN ASILDI -> supurme eksenleri KOSULMADI (butce korumasi), iddialar KIRMIZI");
    if (!sessiz) {
      ONA(false, "TAM SINIRDA supurme OLCULEMEDI (oran asildi -> kosum ATLANDI)");
      ONA(false, "SINIRIN BIR PARTI OTESI OLCULEMEDI (oran asildi -> kosum ATLANDI)");
    }
  } else {
    // Butcenin izin verdigi EN BUYUK katalog: supurme EKSIKSIZ olmali.
    const tam = await olc(ortakYolu, MUTLAK * IDS, {});
    // Sinirin BIR PARTI otesi: ust sinir DURMALI ve butce PATLAMAMALI (0 istek).
    const otesi = await olc(ortakYolu, MUTLAK * IDS + IDS, {});
    imza.push("K3 oran=" + MUTLAK + "/" + gerekliBugun + " tam(tavan=" + tam.tavan +
      " parti=" + tam.parti +
      " idsIstek=" + tam.idsIstek + " eksik=" + tam.eksik + " hata=" + tam.hataTur +
      " cokme=" + (tam.cokme ? "VAR" : "yok") + ")" +
      " otesi(hata=" + otesi.hataTur + " tavan=" + otesi.tavan + " parti=" + otesi.parti +
      " idsIstek=" + otesi.idsIstek + ")");
    yaz("   tam sinir=" + (MUTLAK * IDS) + " id · bir parti otesi=" +
      (MUTLAK * IDS + IDS) + " id");
    if (!sessiz) {
      ONA(tam.cokme === null, "TAM SINIR: surec COKMEDI", tam.cokme);
      ONA(tam.hataTur === null, "TAM SINIR: TAVAN carpMADI (butcenin izin verdigi EN BUYUK " +
        "katalog)");
      ONA(tam.tavan === MUTLAK, "TAM SINIR: tavan = mutlak sinir (" + tam.tavan + ")");
      ONA(tam.parti === MUTLAK, "TAM SINIR: TUM partiler kosuldu " + tam.parti + "/" + MUTLAK);
      // ICRA IZI (bkz. K1): `parti` bolme aritmetigidir, `idsIstek` FIILEN atilan istektir.
      ONA(tam.idsIstek === MUTLAK, "TAM SINIR: supurme FIILEN KOSTU " + tam.idsIstek + "/" +
        MUTLAK + " /katalog?ids= istegi ATILDI");
      ONA(tam.eksik === 0, "TAM SINIR: 'yerel ⊆ D1' kaniti URETILDI (eksik 0)");
      ONA(otesi.hataTur === "TAVAN", "BIR PARTI OTESI: TAVAN hatasi ADIYLA atildi (tur=" +
        otesi.hataTur + ")");
      ONA(otesi.tavan === MUTLAK, "BIR PARTI OTESI: tavan MUTLAK sinirda kapandi (" +
        otesi.tavan + ") — sinirsiz buyume YOK");
      ONA(otesi.parti === 0, "BIR PARTI OTESI: hicbir parti kosulmadi (" + otesi.parti + ")");
      ONA(otesi.idsIstek === 0, "BIR PARTI OTESI: butce PATLAMADI (0 supurme istegi)");
    }
  }

  // K4 — ON-KOSUL: tavan asilinca ACIK OLCULEMEDI ('durdu'), sessiz yanlis-kirmizi DEGIL.
  // Mutlak sinir fikstur env'iyle KUCULTULUR (kosum suresi; env FIKSTUR_ENV listesindedir,
  // yani boyle bir kosum zaten pariteyi belgelendiremez).
  const dar = { PARITE_SUPURME_MUTLAK: "3" };
  const ok = await olcOnKosul(ortakYolu, 1000, dar);
  imza.push("K4 durdu=" + (ok.durdu ? "VAR" : "yok") + " kirmizi=" + (ok.kirmizi ? "VAR" : "yok") +
    " olculemedi=" + ok.olculemedi);
  yaz("\n▶ K4 ON-KOSUL: tavan asildi -> ACIK OLCULEMEDI (sessiz yanlis-kirmizi DEGIL)");
  if (!sessiz) {
    ONA(ok.cokme === null, "surec COKMEDI", ok.cokme);
    ONA(!!ok.durdu, "kosum ACIKCA DURDU (sorgular olculmeden)");
    ONA(ok.kirmizi === null, "KIRMIZI hukmu BASILMADI (dayanaksiz olurdu)");
    ONA(ok.olculemedi > 0, "sebep OLCULEMEDI listesine yazildi -> cikis 3");
    ONA(/SUPURME TAVANI/.test(String(ok.durdu)), "sebep ADIYLA yazili");
  }

  // K5 — MUTLAK SINIRIN KENDISI de KATALOGDAN TURER (elle tutulan sabit DEGIL).
  // 🔴 BU EKSEN 10 Agu'da YAYINI DURDURAN KUSURU DOGRUDAN OLCER: mutlak sinir `500` sabiti
  // iken katalog 25.010'a cikinca gereken parti sayisi sinira carpti ve `deploy` SKIPPED
  // oldu. Sabiti buyutmek sinifi kapatmaz, sadece erteler — bu yuzden olculen sey sinirin
  // DEGERI degil, KATALOGLA BIRLIKTE BUYUYOR OLMASIDIR.
  // 🔴 IMZAYA yalniz OLCULEN DAVRANIS girer (mutlak + okunan katalog); `kat`/`taban`
  // dogrudan girseydi davranis degistirmeyen bir KONTROL mutanti sahte kirmizi yakardi.
  const n5 = sbt.katalogIdAdedi ? sbt.katalogIdAdedi() : null;
  const ustSinirOlculen = (sbt.MUTLAK_KAT === null || sbt.MUTLAK_TABAN_PARTI === null ||
    n5 === null) ? null
    : Math.max(sbt.MUTLAK_TABAN_PARTI, sbt.MUTLAK_KAT * Math.ceil(n5 / IDS));
  imza.push("K5 mutlak=" + MUTLAK + " n=" + n5);
  yaz("\n▶ K5 MUTLAK SINIR KATALOGDAN TURUYOR (bugun gerekli " + gerekliBugun + " parti)");
  if (!sessiz) {
    ONA(n5 !== null && n5 > 0,
      "FAIL-CLOSED: MUTLAK sinir GERCEK katalogu FIILEN okudu (n=" + n5 + ")");
    ONA(boy.ham === null || n5 === boy.ham,
      "okunan katalog testin BAGIMSIZ sayimiyla ayni (kapi=" + n5 + " test=" + boy.ham + ")");
    ONA(MUTLAK !== null && MUTLAK >= 2 * gerekliBugun,
      "MUTLAK sinir kapinin EN GENIS eksenini (katalog x2 = " + (2 * gerekliBugun) +
      " parti) KAPSIYOR — mutlak=" + MUTLAK);
    ONA(ustSinirOlculen !== null && MUTLAK === ustSinirOlculen,
      "MUTLAK sinir SONLU ve TURETIMDEN geliyor: mutlak=" + MUTLAK + " = max(taban=" +
      sbt.MUTLAK_TABAN_PARTI + ", kat=" + sbt.MUTLAK_KAT + " x " +
      (n5 === null ? "?" : Math.ceil(n5 / IDS)) + ") = " + ustSinirOlculen);
  }

  // K6 — FAIL-CLOSED TABAN: katalog OKUNAMAZSA sinir TABANA duser, sinirsiz butce ACILMAZ.
  // 🔴 MAIN'IN YENI YUZEYI: mutlakTavan() artik gercek katalogu okuyor; okuyamadigi kolu
  // hicbir eksen olcmuyordu. Bu eksen modulu KATALOGUN BULUNAMADIGI bir kokte yukler
  // (kopya /tmp'de + cwd oraya cekili) ve tabanin FIILEN kullanildigini olcer.
  // Taban SADECE "esit mi" diye olculmez — KULLANILABILIR de olmali: taban 1'e cekilirse
  // esitlik yine tutar ama kabul tabani boyundaki bir katalog ASLA kanitlanamaz.
  const k6 = olcKataloksuz(ortakYolu);
  const tabanAlt = Math.ceil(KABUL_TABANI / IDS);
  imza.push("K6 mutlak=" + k6.mutlak + " n=" + k6.n + " taban=" + k6.taban +
    " cokme=" + (k6.cokme ? "VAR" : "yok"));
  yaz("\n▶ K6 FAIL-CLOSED TABAN (katalog OKUNAMAZ kokte yuklendi)");
  if (!sessiz) {
    ONA(k6.cokme === null, "surec COKMEDI", k6.cokme);
    ONA(k6.n === null, "katalog FIILEN OKUNAMAZ hale geldi (n=" + k6.n + ") -> fail-closed " +
      "ayagi GERCEKTEN kosuldu (pozitif tanima izi)");
    ONA(k6.taban !== null && k6.mutlak === k6.taban,
      "katalog okunamayinca sinir TABANA dustu (mutlak=" + k6.mutlak + " = taban=" +
      k6.taban + ") -> okunamayan katalog SINIRSIZ BUTCE ACMAZ");
    ONA(k6.mutlak !== null && k6.mutlak >= tabanAlt,
      "taban KULLANILABILIR: kabul tabani boyundaki katalog (" + KABUL_TABANI + " id = " +
      tabanAlt + " parti) yine de KANITLANABILIR (taban=" + k6.mutlak + ")",
      "TABAN COK KUCUK: " + k6.mutlak + " < " + tabanAlt + " parti. Katalog okunamadiginda " +
      "kapi hicbir gercek katalog icin kanit URETEMEZ; 'fail-closed' bu degil, OLU KAPIDIR.");
  }

  // K7 — CANLI MALIYET: ERKEN UYARI, IDDIA DEGIL. 🔴 ONA CAGRILMAZ, deploy'u DURDURMAZ
  // ([[kapi-birikimi-yayin-gecikmesi]]).
  // 🔴 NEDEN "BUTCE PAYI" DEGIL: tavan katalog-goreli olunca pay MUTLAK_KAT'in tersine
  // (%25) CAKILIR ve hicbir zaman yanmaz — OLU UYARI olurdu. Uyarilmasi gereken sey oran
  // degil MUTLAK MALIYET: tek kanit kosumu `gerekliBugun` canli istek atar.
  imza.push("K7 canliMaliyet=" + gerekliBugun);
  yaz("\n▶ K7 CANLI MALIYET (erken uyari — iddia DEGIL, deploy'u DURDURMAZ)");
  yaz("   bugun=" + boy.n + " id -> tek kanit kosumu " + gerekliBugun +
    " canli /katalog?ids= istegi atar (uyari esigi " + CANLI_MALIYET_UYARI + ")");
  if (gerekliBugun > CANLI_MALIYET_UYARI) {
    yaz("   ⚠️ TEK KOSUMUN CANLI MALIYETI " + CANLI_MALIYET_UYARI + " ISTEGI GECTI: 429 " +
      "butcesi ve kosum suresi artik ciddi kalemler — kanit yontemi (tam supurme) " +
      "ORNEKLEMEYE cevrilmeli mi, mimar karari.");
  }

  return imza.join(" | ");
}

// ── MUTASYON BATARYASI ────────────────────────────────────────────────────────────────
/**
 * Mutant listesi SABIT DIZI DEGIL, OLCULEN SABITTEN TURETILIR.
 * 🔴 NEDEN (olculdu 10 Agu 2026): M4'un capasinda mutlak sinir LITERAL yaziliydi
 * (`..., 500,`). Kardes bir oturum sinira 1000 yazdiginda capa kaynakta 0 kez gecti ->
 * `capa-yok=1`, `oldurucu=4/5`: "sinir sessizce yukseltildi" kacisini kapatan mutant, tam
 * da sinir yukseltildigi an KORELIYORDU. Envanter, defterden degil OLCULEN DEGERDEN
 * turemeli ([[mutasyon-kaniti-yeniden-uretilebilir]] · [[envanter-drift-parti-basina]]).
 * Bu yuzden SABIT DEGERE bakan her capa YAPISALDIR: sabitin ADI + env ADI'na dayanir,
 * varsayilan ifadeye (literal mi, turetim cagrisi mi) DAYANMAZ.
 */
function mutantlar(mutlak) {
  return [
  {
    id: "M1", oldurucu: true,
    ad: "TAVAN YENIDEN SABITLENDI (200 parti = 20.000 id — regresyonun ta kendisi)",
    eski: "  const gerekli = Math.ceil(Math.max(0, idAdedi) / IDS_PARTI);\n" +
      "  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN);",
    yeni: "  return 200;",
  },
  {
    id: "M2", oldurucu: true,
    ad: "MUTLAK UST SINIR KALDIRILDI (tavan sonsuz — istek/429 butcesi patlar)",
    eski: "  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN);",
    yeni: "  return Math.max(1, gerekli);",
  },
  {
    id: "M3", oldurucu: true,
    ad: "ACIK OLCULEMEDI KALKTI: tavan asimi yine siniflandirma-KAPALI'ya duser",
    eski: "    if (e && e.tur === \"TAVAN\") {",
    yeni: "    if (false && e.tur === \"TAVAN\") {",
  },
  {
    id: "M4", oldurucu: true,
    ad: "MUTLAK SINIR YENIDEN ELLE SABITLENDI (turetim yerine " +
      Math.max(1, Math.floor(mutlak / 2)) + " literali — 10 Agu'da YAYINI DURDURAN SINIF)",
    // 🔴 CAPA YAPISALDIR, DEGERE BAGLI DEGIL: yalniz SABITIN ADI + ENV ADI'na dayanir.
    // Varsayilan ifade LITERAL (500) de olabilir, TURETEN BIR CAGRI (mutlakTavan()) de —
    // ikisinde de tutar. Deger capasi (".., 500,") olculdu ve KORELDI: kardes oturum
    // varsayilani `mutlakTavan()`e cevirince desen 0 kez gecti -> capa-yok=1.
    // Kalan sinir ifadesi ikinci (kullanilmayan) bagta durur; okunan sabit MUTANTTIR.
    // Deger OLCULEN mutlagin yarisidir: turetimden DAIMA farkli (mutlak >= 2 oldukca),
    // ama kat orani bandindan GECER -> hukmu K5 (turetim) verir, oran kapisi DEGIL.
    eski: "const SUPURME_MUTLAK_TAVAN = sayiEnv(\"PARITE_SUPURME_MUTLAK\", ",
    yeni: "const SUPURME_MUTLAK_TAVAN = " + Math.max(1, Math.floor(mutlak / 2)) +
      ";\nconst SUPURME_MUTLAK_TAVAN_KULLANILMAYAN = sayiEnv(\"PARITE_SUPURME_MUTLAK\", ",
  },
  {
    id: "M5", oldurucu: true,
    ad: "SINIRDA BIR PARTILIK SIZINTI (off-by-one: ust sinir bir parti fazla gecirir)",
    eski: "  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN);",
    yeni: "  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN + 1);",
  },
  {
    id: "M6", oldurucu: true,
    ad: "SUPURME HIC KOSMADI (isci sayisi 0 — tek bir /katalog?ids= istegi bile atilmaz, " +
      "ama parti sayaci 'TUM partiler kosuldu' demeye devam eder)",
    eski: "Array.from({ length: Math.min(IDS_ESZAMAN, partiler.length) }, isci)",
    yeni: "Array.from({ length: 0 }, isci)",
  },
  {
    id: "M7", oldurucu: true,
    ad: "EKSIK LISTESI HIC DOLDURULMAZ (D1'de OLMAYAN id sessizce YUTULUR -> 'yerel ⊆ D1' " +
      "kaniti SAHTE)",
    eski: "      for (const id of parti) if (!bulunan.has(id)) eksik.push(id);",
    yeni: "      for (const id of parti) if (false && !bulunan.has(id)) eksik.push(id);",
  },
  {
    id: "M8", oldurucu: true,
    ad: "FAIL-CLOSED TABAN ISE YARAMAZ HALE GETIRILDI (taban 1 partiye cekildi: katalog " +
      "okunamayinca hicbir gercek katalog KANITLANAMAZ — 'fail-closed' degil OLU KAPI)",
    // Bugunku katalogda turetim (kat x gerekli) tabani ZATEN baskilar, yani bu mutant
    // ANCAK K6'nin katalogsuz kokunde gorunur: tek eksende ayirt edici.
    eski: "const MUTLAK_TABAN_PARTI = 500;",
    yeni: "const MUTLAK_TABAN_PARTI = 1;",
  },
  {
    id: "M9", oldurucu: true,
    ad: "BUTCE KAT KAT PATLADI (MUTLAK_KAT 4 -> 400: tavan katalogun 400 kati, 1 parti = " +
      "1 canli istek oldugu icin bu ARTIK SINIR DEGIL)",
    eski: "const MUTLAK_KAT = 4;",
    yeni: "const MUTLAK_KAT = 400;",
  },
  {
    id: "M10", oldurucu: true,
    ad: "FAIL-CLOSED IHLALI: katalog OKUNAMAYINCA tabana dusulmuyor, DEV bir sinir " +
      "aciliyor (okunamayan katalog SINIRSIZ BUTCE aciyor)",
    eski: "  const n = katalogIdAdedi();\n  if (!n) return MUTLAK_TABAN_PARTI;",
    yeni: "  const n = katalogIdAdedi();\n  if (!n) return 100000;",
  },
  {
    id: "K_A", oldurucu: false,
    ad: "KONTROL: davranis degistirmeyen yeniden adlandirma (gerekli -> gerekliParti)",
    eski: "  const gerekli = Math.ceil(Math.max(0, idAdedi) / IDS_PARTI);\n" +
      "  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN);",
    yeni: "  const gerekliParti = Math.ceil(Math.max(0, idAdedi) / IDS_PARTI);\n" +
      "  return Math.min(Math.max(1, gerekliParti), SUPURME_MUTLAK_TAVAN);",
  },
  {
    id: "K_B", oldurucu: false,
    ad: "KONTROL: ILGISIZ sabit eklendi (kimse okumuyor)",
    eski: "function supurmeTavani(idAdedi) {",
    yeni: "function supurmeTavani(idAdedi) {\n  const kullanilmayan = 42; void kullanilmayan;",
  },
  {
    id: "K_C", oldurucu: false,
    ad: "KONTROL: supurme ESZAMANLILIGI degisti (4 -> 2; hicbir iddianin konusu DEGIL)",
    eski: "const IDS_ESZAMAN = 4;",
    yeni: "const IDS_ESZAMAN = 2;",
  },
  ];
}

async function kendiniTest() {
  const kaynak = fs.readFileSync(ORTAK, "utf8");
  // 🔴 Capalar OLCULEN YOLUN sabitlerinden turer (bkz. mutantlar()): sabit degistiginde
  // mutant SUSMAZ, capasini yeniden hesaplar.
  const MUTANTLAR = mutantlar(sabitler(ORTAK).SUPURME_MUTLAK_TAVAN);
  const kok = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-tavan-"));
  console.log("\n" + "=".repeat(78));
  console.log("MUTASYON BATARYASI — mutant KOPYAYA uygulanir, canli dosyaya ASLA");
  console.log("=".repeat(78));

  const tabanYolu = path.join(kok, "taban-parite-ortak.js");
  fs.writeFileSync(tabanYolu, kaynak);
  const taban = await kabulKos(tabanYolu, true);
  console.log("\nTABAN IMZA: " + taban);

  let oldurucuKirmizi = 0, oldurucuTop = 0, kontrolYesil = 0, kontrolTop = 0;
  let sapan = 0, capaYok = 0, cokme = 0;

  for (const m of MUTANTLAR) {
    if (m.oldurucu) oldurucuTop++; else kontrolTop++;
    const kez = kaynak.split(m.eski).length - 1;
    if (kez !== 1) {
      capaYok++;
      console.log("\n❌ " + m.id + " CAPA-YOK: desen kaynakta " + kez + " kez gecti (1 olmali) — " +
        "sonuc YESIL SAYILMAZ");
      continue;
    }
    const yol = path.join(kok, m.id + "-parite-ortak.js");
    fs.writeFileSync(yol, kaynak.replace(m.eski, m.yeni));
    let imza;
    try {
      imza = await kabulKos(yol, true);
    } catch (e) {
      cokme++;
      console.log("\n💥 " + m.id + " COKME (kirmiziyla KARISTIRILMAZ): " +
        String((e && e.message) || e).slice(0, 200));
      continue;
    }
    const farkli = imza !== taban;
    if (m.oldurucu) {
      if (farkli) { oldurucuKirmizi++; console.log("\n✅ " + m.id + " " + m.ad); }
      else { sapan++; console.log("\n❌ SAPAN " + m.id + " " + m.ad + " — imza DEGISMEDI"); }
      console.log("   taban : " + taban);
      console.log("   mutant: " + imza);
    } else {
      if (!farkli) { kontrolYesil++; console.log("\n✅ " + m.id + " " + m.ad + " -> imza AYNI"); }
      else {
        sapan++;
        console.log("\n❌ ASIRI-HASSAS " + m.id + " " + m.ad);
        console.log("   taban : " + taban);
        console.log("   mutant: " + imza);
      }
    }
  }

  fs.rmSync(kok, { recursive: true, force: true });
  console.log("\n" + "-".repeat(78));
  console.log("BATARYA_OZET oldurucu=" + oldurucuKirmizi + "/" + oldurucuTop +
    " kontrol=" + kontrolYesil + "/" + kontrolTop + " sapan=" + sapan +
    " capa-yok=" + capaYok + " cokme=" + cokme);
  return oldurucuKirmizi === oldurucuTop && kontrolYesil === kontrolTop &&
    sapan === 0 && capaYok === 0 && cokme === 0;
}

(async () => {
  console.log("=".repeat(78));
  console.log("SUPURME TAVANI OLCEK KAPISI — tavan katalogdan TURER, sabit DEGIL");
  console.log("=".repeat(78));
  await kabulKos(ORTAK, false);

  let bataryaTemiz = true;
  if (process.argv.includes("--kendini-test")) bataryaTemiz = await kendiniTest();

  console.log("\n" + "-".repeat(78));
  console.log("IDDIA: %d gecti | %d KALDI", _gecti, _kaldi.length);
  if (_kaldi.length || !bataryaTemiz) {
    if (_kaldi.length) for (const k of _kaldi) console.log("  ❌ " + k);
    if (!bataryaTemiz) console.log("  ❌ MUTASYON BATARYASI TEMIZ DEGIL");
    console.log("SONUC: KIRMIZI ❌");
    process.exit(1);
  }
  console.log("SONUC: YESIL ✅ — tavan katalogdan TURUYOR ve DOYUYOR, butce katalogla " +
    "ORANTILI, tam sinirda supurme EKSIKSIZ (istek izi capali), katalog okunamazsa TABANA " +
    "duser; sinir asilirsa ACIK OLCULEMEDI");
})().catch((e) => { console.error("COKME:", e); process.exit(1); });
