"use strict";
/**
 * PARITE ORTAK — iki parite testinin (site + Ege) PAYLASTIGI karar cekirdegi.
 *
 * ╔═══════════════════════════════════════════════════════════════════════════════════╗
 * ║ CIKIS KODU SOZLESMESI — TEK KAYNAK. Dort tuketicinin DORDU de buraya referans      ║
 * ║ verir; baska hicbir yerde ikinci bir tablo YAZILMAZ.                                ║
 * ║                                                                                     ║
 * ║   0  CIKIS_GECTI       Birebir parite OLCULDU ve TAMDIR. Hicbir olcum arizasi yok.  ║
 * ║   1  CIKIS_KIRMIZI     ACIKLANAMAYAN ayrisim = GERCEK GERILEME:                     ║
 * ║                          - yerelde VAR / D1'de YOK (Ege GOREMEZ = sessiz satis kaybi)║
 * ║                          - SIRA farki (siralama iddiasi kirik)                       ║
 * ║                          - D1 EKSIK eslesme (yerel ⊆ D1 kanitina aykiri)            ║
 * ║                          - D1 fazlaligi sayi acigini ASIYOR (yetim satir imzasi)    ║
 * ║   2  CIKIS_KOSULAMADI  Bot kaynagi VAR ama SOZLESMESI KIRIK: index.js okundu, ama   ║
 * ║                        beklenen disa-aktarim (urunAra/katalogIndeksle/...) FONKSIYON ║
 * ║                        DEGIL — yeniden adlandirilmis/kaldirilmis. GERCEK GERILEME.  ║
 * ║   3  CIKIS_OLCULEMEDI  Olcum TAM DEGIL / hukum verilemedi. Sebepleri:               ║
 * ║                          WAF-UA duvari (403) · hiz siniri (429, deneme tukendi)     ║
 * ║                          zaman asimi · supurme TAVANI asildi · katalog sayilari     ║
 * ║                          ayri (senkron gecikmesi / D1'de yetim satir — AYIRT        ║
 * ║                          EDILEMEZ) · FIKSTUR MODU (test-only env verilmis)          ║
 * ║                          · BOT KAYNAGI YOK (kardes depo bu ortamda MEVCUT DEGIL)    ║
 * ║                                                                                     ║
 * ║ 🔴 2 ile 3'un AYRIMI — 6 Eyl 2026'da OLCULEN kok (iki kovali siniflama UCUNCU       ║
 * ║    sinifi yutuyordu). Eskiden "bot kaynagi YOK" da "fonksiyonu YOK" da tek exit 2   ║
 * ║    idi. Bot AYRI bir depodur (pruvo-bot, HocA) ve GitHub kosucusunun checkout'unda  ║
 * ║    HICBIR ZAMAN bulunmaz -> CI'da bu kol DAIMA kirmizi yandi, Okan'in makinesinde   ║
 * ║    ise kardes klasor VAR oldugu icin DAIMA yesildi: kirmizi, gelistiricinin         ║
 * ║    kostugu yerde HIC uretilemiyordu ([[prob-kendi-baglamini-olcer]]).               ║
 * ║    AYRIM SU: kaynak YOKSA bu bir ORTAM olgusudur (node yok / uc susuyor ile AYNI    ║
 * ║    sinif) -> 3, ADIYLA gorunur sebeple. Kaynak VARSA ve sozlesme kirilmissa bu bir  ║
 * ║    GERILEMEDIR -> 2, her ortamda KIRMIZI. Kapsam DARALMADI: kardes depo mevcutken   ║
 * ║    (Okan'in makinesi, HocA'nin evi) her iki kol da eskisi gibi olculur.             ║
 * ║                                                                                     ║
 * ║ 🔴 YONETICI ILKE (her seyin ustunde):  1 (KIRMIZI)  >  3 (OLCULEMEDI)  >  0 (YESIL) ║
 * ║    Bulunmus TEK bir aciklanamayan ayrisim varsa, sonradan ne olursa olsun (WAF,     ║
 * ║    429, zaman asimi, tavan asimi, fikstur modu) sonuc 1'dir. HICBIR ARIZA YOLU      ║
 * ║    0 URETEMEZ; olculemeyen hicbir sey YESILE donusemez. Karar TEK yerde verilir:    ║
 * ║    sonucYaz() — hatalar[] DEGERLENDIRILDIKTEN SONRA.                                 ║
 * ║                                                                                     ║
 * ║ TUKETICI ESLEMESI (dordu de bu bloga referans verir; degistiren burayi da degistirir)║
 * ║   tools/filament-test.py       exit 3 -> ATLANDI  (GORUNUR sebep, testi bloklamaz)  ║
 * ║   tools/edge-flip-hazirlik.py  exit 3 -> BLOKLU   (gerileme DEGIL; GO da VERMEZ)    ║
 * ║   tools/regresyon-kapisi.py    exit 3 -> BLOKE    (fail-closed; yayin-oncesi kapi)  ║
 * ║   dogrudan cagri (kabuk/CI)    exit kodu = yukaridaki tablo                          ║
 * ║   Kabul testi: tools/parite-sozlesme-test.py (4/4 eslemeyi TEK TEK olcer)           ║
 * ╚═══════════════════════════════════════════════════════════════════════════════════╝
 *
 * NEDEN VAR (olculdu, 27 Tem): parite testleri "yerel checkout'un katalogu" ile "canli D1"i
 * karsilastirir. Bir isci dali (worktree) main'den GERIDE kaldiginda D1 ilerlemis olur ->
 * testler AYRISMA sayar ve KIRMIZI yanar. Olculen imza: 108/300 ayrisim, 108/108'i SAYI
 * farki, 108/108'i "D1 fazla / yerel eksik" yonunde, 0 sira farki. Bu gurultu, GERCEK
 * kirilmayla ayni renkte yaniyordu -> teshis imkansizdi.
 *
 * AYIRIM (mimar karari):
 *   ACIKLANAN      = D1'de VAR / yerelde YOK  -> katalog farki -> cikis 3, KIRMIZI DEGIL
 *   ACIKLANAMAYAN  = yerelde VAR / D1'de YOK  -> Ege GOREMEZ = sessiz satis kaybi -> cikis 1
 *                  = SIRA farki               -> siralama iddiasi kirik           -> cikis 1
 * Karisik kosumda sonuc DAIMA KIRMIZI: aciklanan gurultu, aciklanamayani MASKELEMEZ.
 *
 * "ACIKLANAN" DAMGASI BEDAVA DEGIL — KANIT SART. Sayi farki gormek yetmez; on-kosul yerel
 * id'lerin TAMAMINI /katalog?ids= ile D1'e karsi SUPURUR ve "yerel ⊆ D1" onermesini
 * KANITLAR. Kanit yoksa siniflandirma ACILMAZ (fail-closed: her ayrisim KIRMIZI).
 *
 * ⚠️ TESHIS DURUSTLUGU (27 Tem onarimi): "yerel ⊂ canli" kaniti, FARKIN SEBEBINI
 * KANITLAMAZ. Ayni imza iki ayri olaydan cikar:
 *     (a) checkout/dal BAYAT (main ilerlemis, yeni urunler D1'de)
 *     (b) D1'de YETIM satir (yerelde SILINMIS urun D1'de duruyor -> Ege hala satiyor)
 * Disaridan olculebilen hicbir sinyal ikisini ayirmaz. Bu yuzden kod ARTIK "checkout
 * BAYAT" diye KESIN hukum BASMAZ: kaniti (sayilar + supurme) yazar, iki olasiligi ADIYLA
 * sayar ve ⚪ OLCULEMEDI (cikis 3) der. Eski metin tek-yetim durumunda OLGUSAL OLARAK
 * YANLIS teshis basiyordu (olculdu: A8).
 *
 * ⚠️ YAYIN PENCERESI (1 Agu onarimi) — "YAYIN GECIKMESI" ile "GERCEK KAYIP" AYRI SINIFTIR.
 * Atomik yayin geregi yeni satir D1'e TASLAK girer (yayinda=0) ve HER kesif sorgusu
 * `yayinda = 1` suzer -> taslak satir, uc icin "D1'de HIC YOK" satirdan AYIRT EDILEMEZ.
 * Bayragi deploy'un `yayin` isi cevirir; olculen pencere 29 dk 10 sn (push 12:09:22Z ->
 * yayin 12:38:32Z; tikanma `build` isinde). Eski kod bu pencerede supurmeyi "YERELDE VAR /
 * D1'DE YOK" diye KIRMIZI yakiyordu: her urun partisinden sonra yarim saat boyunca
 * 1199/844 sorgunun HICBIRI kosmuyordu (olculdu: butce 1 on-kosul + 166 supurme partisi
 * = 167 istekte tukeniyor, kapi on-kosulda dusuyordu). Bu YAPISALDI, her partide tekrar
 * ediyordu.
 * ONARIM: on-kosul, eksik cikan her id icin `yayinda` kolonunu FIILEN OKUR (yayinHaliOku
 * -> tools/yayin-kapisi.py --hal-json). Sinif SAYI FARKINDAN TUREMEZ:
 *   satir D1'de YOK          -> GERCEK KAYIP   -> KIRMIZI (kapinin var olma sebebi; gevsetilmez)
 *   satir VAR + yayinda=1    -> uc gostermiyor -> KIRMIZI (yayinda ama gorunmuyor = gerileme)
 *   satir VAR + yayinda=0    -> YAYIN GECIKMESI -> kirmizi DEGIL, ust sinira TABI (asagida)
 *   okuma BASARISIZ          -> KIRMIZI (fail-closed; "olcemedim" asla yesil sayilmaz)
 *
 * VERI CAPASI YOK: bu dosyada hicbir sabit urun sayisi/id/SHA/tarih yoktur — her sayi
 * kosum aninda olculur.
 */

const cp = require("child_process");
const path = require("path");
const fs = require("fs");

// Cloudflare WAF varsayilan urllib/python-requests UA'sina 403 verir (media.pruvo3d.com'da
// olculdu, 27 Tem'de CANLI /ara ucunda da dogrulandi: urllib UA -> 403, Chrome UA -> 200).
const TARAYICI_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " +
  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

const CIKIS_GECTI = 0;
const CIKIS_KIRMIZI = 1;
const CIKIS_KOSULAMADI = 2;
const CIKIS_OLCULEMEDI = 3;

const SINIF_GECTI = "gecti";
const SINIF_ACIKLANAN = "aciklanan";
const SINIF_ACIKLANAMAYAN = "aciklanamayan";

const IDS_PARTI = 100;        // /katalog?ids= ucunun kendi tavani (fazlasini kirpar)
const IDS_ESZAMAN = 4;

// ── TEST-ONLY ENV KAPISI ────────────────────────────────────────────────────────────
// Asagidaki degiskenler YALNIZ fikstur/kabul testi icindir. Herhangi biri set edilmisse
// kosum "kanonik" DEGILDIR: katalog, uc ya da esikler ELLE degistirilmistir. KARAR
// (mimar, 27 Tem): boyle bir kosum pariteyi ASLA BELGELENDIREMEZ -> en iyi ihtimalle 3.
// Bu, PARITE_URUNLER baypasinin (A15: alt kume ile kosup 3 alma) kapisidir; ayni kural
// esik degiskenlerine de uygulanir, aksi halde tavan/deneme/zaman-asimi env'i yeni bir
// baypas olurdu.
const FIKSTUR_ENV = [
  "PARITE_URUNLER",        // katalog yolu ELLE verildi (checkout'un katalogu okunmuyor)
  "PARITE_BOT",            // Ege referans kaynagi ELLE verildi
  "ARA_UC",                // canli uc ELLE degistirildi (kanonik uc olculmedi)
  "PARITE_ZAMAN_ASIMI_MS",
  "PARITE_DENEME",
  "PARITE_BEKLEME_MS",
  "PARITE_SUPURME_TAVANI",
  "PARITE_SUPURME_MUTLAK",       // supurme MUTLAK ust siniri ELLE degistirildi
  "PARITE_YAYIN_HALI",           // yayin hali komutu ELLE verildi (kanonik D1 okunmuyor)
  "PARITE_YAYIN_UST_SINIRI_SN",  // taslak yasi ust siniri (EKSEN A) ELLE degistirildi
  "PARITE_YAYIN_BEKLEME_UST_SINIRI_SN",  // bekleme ust siniri (EKSEN B) ELLE degistirildi
  "PARITE_YEREL_HEAD_YAS_SN",    // yerel HEAD commit yasi ELLE verildi (git OKUNMAZ)
];

/** Set edilmis test-only env degiskenleri (bos string sayilmaz). SAF. */
function fiksturBayraklari(env) {
  const e = env || process.env;
  return FIKSTUR_ENV.filter((a) => e[a] !== undefined && String(e[a]).trim() !== "");
}

function sayiEnv(ad, varsayilan, alt, ust) {
  const ham = process.env[ad];
  if (ham === undefined || String(ham).trim() === "") return varsayilan;
  const n = parseInt(ham, 10);
  if (!Number.isFinite(n) || n < alt || n > ust) return varsayilan;
  return n;
}

// Tek istek zaman asimi. Ucun susmasi sureci ASMAMALI: asilan kapi OLU kapidir.
const ZAMAN_ASIMI_MS = sayiEnv("PARITE_ZAMAN_ASIMI_MS", 20000, 50, 120000);
// Gecici hata (429 / zaman asimi / 5xx) icin sinirli yeniden deneme + ustel bekleme.
const DENEME = sayiEnv("PARITE_DENEME", 3, 1, 6);
const BEKLEME_MS = sayiEnv("PARITE_BEKLEME_MS", 400, 1, 5000);
// ── SUPURME TAVANI — SABIT DEGIL, KATALOG BOYUTUNDAN TURETILIR ──────────────────────
// /katalog?ids= parti sayisi ust siniri (1 parti = IDS_PARTI id). Tavan asilirsa
// "yerel ⊆ D1" kaniti URETILMEZ.
//
// 🔴 NEDEN SABIT DEGIL (olculdu 5-6 Agu 2026): tavan `200 parti = 20.000 id` diye SABIT
// yazilmisti ve katalog 20.212'ye cikinca ASILDI. Sayilar esitken supurme hic kosmadigi
// icin gorunmuyordu; sayilar ayristigi ANDA kanit uretilemedi, siniflandirma kapandi ve
// katalog farkiyla ACIKLANABILIR her sapma KIRMIZI yandi (bir kosumda 526 kirmizi). Yani
// sabit tavan, katalog buyudugu icin testin KENDISINI bozan bir zaman bombasiydi
// ([[katalog-olcek-siniri]] · [[hukum-yanlis-birimde]]).
//
// KURAL: tavan = katalogun GEREKTIRDIGI parti sayisi, MUTLAK bir ust sinirla kapatilmis.
//   · Katalog buyudukce tavan kendiliginden buyur -> sabit sayinin yarattigi sahte kirmizi
//     sinifi KOKTEN kalkar (kabul: 20.212'de de, iki katinda da supurme EKSIKSIZ).
//   · Ust sinir KALKMAZ: tavansiz birakmak istek/429 butcesini patlatir (500 parti =
//     ~500 ek canli istek). Bu yuzden MUTLAK sinir korunur ve asilirsa kosum SESSIZ
//     YANLIS-KIRMIZI degil ACIK OLCULEMEDI (cikis 3) uretir.
// 🔴 MUTLAK SINIR DA SABIT DEGIL — GERCEK KATALOGDAN TURER (10 Agu 2026 onarimi).
// OLCULEN KUSUR: mutlak sinir `500 parti = 50.000 id` diye ELLE yazilmisti. Katalog
// 25.008'e cikinca parite-tavan-test.js'in K2 ekseniyle (katalog IKI KATINA cikarilsa da
// supurme EKSIKSIZ olmali) carpisti: 2 x 25.008 = 50.016 id -> 501 parti > 500 -> kapi
// KIRMIZI (0/501), serit-a3 FAILURE, `deploy` SKIPPED, YAYIN DURDU. Sabiti 500 -> 1000
// yapmak ayni kolu katalog 50.000'e gelince YENIDEN dusururdu: elle tutulan defter her
// urun partisinde bayatlar ([[envanter-drift-parti-basina]] · [[katalog-olcek-siniri]]).
//
// KURAL: MUTLAK sinir = GERCEK katalogun gerektirdigi parti sayisinin MUTLAK_KAT kati,
// MUTLAK_TABAN_PARTI ile alttan sinirli.
//   · Katalog buyudukce sinir da buyur -> sinif BAYATLAMAZ (elle dokunulacak sayi YOK).
//   · Yine de MUTLAK'tir: supurme, GERCEK veri hacminin MUTLAK_KAT katini ASAMAZ. SINIRIN
//     KORUDUGU SEY BUDUR: tavansiz birakilirsa bir kosum sinirsiz /katalog?ids= istegi
//     atar (1 parti = 1 canli istek) ve istek/429 butcesi patlar; ayrica katalogun
//     kat kat otesinde bir id listesi zaten VERI degil ARIZA isaretidir.
//   · MUTLAK_KAT=4 secimi: kapinin kendi en genis ekseni katalogun IKI KATINI olcer;
//     4 kat, o eksene iki kat pay birakir ve yine sabit bir tavan verir.
//   · Katalog OKUNAMAZSA taban kullanilir (daha KUCUK sinir = daha erken ACIK OLCULEMEDI
//     = fail-closed; okunamayan katalog sinirsiz butce ACMAZ).
const MUTLAK_KAT = 4;
const MUTLAK_TABAN_PARTI = 500;

/** urunler.json'u __dirname'den VE cwd'den yukari yuruyerek bulur (mutant kopyasi /tmp'de
 *  kosarken __dirname repo disina duser; sabit mutlak yol yerelde yesil yanardi). */
function katalogYolunuBul() {
  const adaylar = [];
  const yukari = (baslangic) => {
    let d = baslangic;
    for (let i = 0; i < 8; i++) {
      adaylar.push(path.join(d, "urunler.json"));
      const ust = path.dirname(d);
      if (ust === d) return;
      d = ust;
    }
  };
  yukari(__dirname);
  yukari(process.cwd());
  for (const y of adaylar) {
    try { if (fs.statSync(y).isFile()) return y; } catch (e) { /* aday degil */ }
  }
  return null;
}

/** GERCEK katalogdaki benzersiz id adedi; okunamazsa null. mtime+boy anahtarli memo
 *  (require onbellegi silinse de tek parse yeter). */
function katalogIdAdedi() {
  const yol = katalogYolunuBul();
  if (!yol) return null;
  try {
    const st = fs.statSync(yol);
    const anahtar = yol + "|" + st.mtimeMs + "|" + st.size;
    const memo = globalThis.__PRUVO_PARITE_KATALOG_SAYIM;
    if (memo && memo.anahtar === anahtar) return memo.n;
    const j = JSON.parse(fs.readFileSync(yol, "utf8"));
    if (!Array.isArray(j)) return null;
    const n = new Set(j.map((u) => u && u.id).filter(Boolean)).size;
    globalThis.__PRUVO_PARITE_KATALOG_SAYIM = { anahtar, n };
    return n;
  } catch (e) {
    return null;
  }
}

/** MUTLAK ust sinir (parti). Katalogdan TURER; elle tutulan sabit YOK. */
function mutlakTavan() {
  const n = katalogIdAdedi();
  if (!n) return MUTLAK_TABAN_PARTI;
  return Math.max(MUTLAK_TABAN_PARTI, Math.ceil(n / IDS_PARTI) * MUTLAK_KAT);
}

const SUPURME_MUTLAK_TAVAN = sayiEnv("PARITE_SUPURME_MUTLAK", mutlakTavan(), 1, 100000);

/**
 * Bu katalog icin supurme tavani (parti). SAF fonksiyon — fikstur dogrudan olcer.
 * 🔴 Env override (PARITE_SUPURME_TAVANI) FIKSTUR_ENV listesindedir: verilirse kosum
 * pariteyi ASLA BELGELENDIREMEZ (en iyi ihtimalle 3).
 */
function supurmeTavani(idAdedi) {
  const elle = sayiEnv("PARITE_SUPURME_TAVANI", 0, 1, 100000);
  if (elle) return elle;
  const gerekli = Math.ceil(Math.max(0, idAdedi) / IDS_PARTI);
  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN);
}

// ── 🔴 TASLAK YASI UST SINIRI — "uzun sure taslak kalan satir sessizce YESIL GECMEZ" ──
// DEGER SECIMI (veri capasi DEGIL, OLCUME dayali sinir): push -> canli olculen pencere
// medyan 593 sn / azami 740 sn (yayin-kapisi.py dosya basi, son 8 basarili kosum) ve bu
// onarimi tetikleyen olayda 29 dk 10 sn. 1800 sn (30 dk) olculen AZAMI pencerenin ~2,4
// katidir ve `yayin` isinin kendi HTTP dogrulama turuna da pay birakir. Bunun otesi
// "pencere" degil TIKANMA'dir.
// IKI EKSENDE AYRI UYGULANIR (ikisi de FIILEN olculur, tahmin YOK):
//   EKSEN A — ZARARLI hal: satir TASLAK ama /urun/<id>/ CANLIDA 200. Site satiyor, Ege
//     GOREMEZ = tam da bu kapinin varlik sebebi olan sessiz satis kaybi. Saat: o sayfanin
//     kendi `date - last-modified`i (yayin adiminin elinde gecen sure). Sinir asilirsa
//     ya da OLCULEMEZSE -> KIRMIZI.
//   EKSEN B — ZARARSIZ hal: satir TASLAK ve sayfasi CANLI DEGIL. Gosterilseydi 404 veren
//     kart uretilirdi — atomik yayinin ONLEMEK ICIN VAR OLDUGU hal, yani gerileme DEGIL.
//     Bu eksende KIRMIZI YAKILMAZ (yanlis-pozitif kapinin kendi hastaligidir). Saat:
//     canli /urunler.json artefaktinin yasi = "site en son ne zaman deploy etti". Sinir
//     asilirsa ya da olculemezse kosum KIRMIZI olmaz ama KANONIK de sayilmaz -> cikis 3.
// 🔴 NEDEN B'DE KIRMIZI YOK: "taslak N dakikadir bekliyor" ifadesinin ALT SINIRI D1'den
// olculemez (semada zaman damgasi kolonu YOK) ve elde kalan tek vekil (artefakt yasi)
// "depo bir sure sessizdi, sonra push geldi" halinde YANLIS POZITIF uretir. Doktrin
// gereği cozulemeyen 3'tur, 1 DEGIL (1 > 3 > 0 sirasi bozulmaz: gercek kayip yine 1).
const YAYIN_UST_SINIRI_SN = sayiEnv("PARITE_YAYIN_UST_SINIRI_SN", 1800, 30, 86400);

// ── 🔴 EKSEN B'NIN KENDI SINIRI + KENDI TABANI (5 Agu 2026, OLCULDU) ────────────────
// ESKI HAL: eksen B de YAYIN_UST_SINIRI_SN'i (1800 sn) kullaniyordu ve OLCUSU "canli
// artefaktin yasi" idi. IKI KUSUR birden olculdu (surucu: scratchpad/yz/olcum.py,
// son 7 gun / 607 deploy kosumu / 348 yayin):
//
//   (1) ESIK BAYAT. Gerekce yorumu "olculen AZAMI pencere 740 sn, 1800 onun ~2,4 kati"
//       diyordu. BUGUN olculen push -> `deploy` isi bitisi: medyan 678 sn (11,3 dk) ·
//       p90 1914 sn (31,9 dk) · AZAMI 3078 sn (51,3 dk). Yani 1800 sn artik olculen
//       azaminin ALTINDA: 348 basarili yayinin 44'u (%12,6) tek basina esigi asiyor.
//   (2) OLCU YANLIS BIRIMDE. "Artefakt yasi" = "site en son ne zaman deploy etti";
//       bu sayi BOSTA GECEN pencereyi de tasir. Olculen ornek (2 Agu): 00:57'den
//       07:28'e kadar HIC push yok, 07:28'de push geldi -> o an artefakt yasi 6,5 SAAT
//       ve D1'de taslak VAR -> eksen B ANINDA yanardi, oysa hat SAGLIKLIYDI.
//       (Dosyanin kendi yorumu bu kusuru zaten ILAN EDIYORDU: "depo bir sure sessizdi,
//       sonra push geldi" halinde yanlis pozitif.)
//
// ONARIM — OLCU DEGISTI: eksen B artik "artefakt kac yasinda"yi degil "YEREL ICERIK NE
// KADARDIR YAYINSIZ BEKLIYOR"u olcer. Taban, yayin-gecikme nobetcisinin OLCULMUS
// doktriniyle AYNI: bir commit son yayindan ONCE bekliyor OLAMAZ ->
//     bekleme = simdi - max(son_yayin_ani, yerel_HEAD_commit_ani)
//             = min(artefakt_yasi, yerel_HEAD_yasi)
// HEAD yasi OKUNAMAZSA (git yok / govde bozuk) eski OLCUYE (artefakt yasi) DUSULUR:
// fail-closed, yeni bir YESIL yol acilmaz.
//
// ESIK SECIMI (veri capasi): bekleme suresinin olculen dagilimi = push -> deploy bitisi
// penceresidir (yukarida): AZAMI 3078 sn. 3600 sn = 1,17 x olculen azami.
//   * SAHTE ALARM: 348 basarili yayin dongusunun HICBIRI 3600 sn'yi asmadi -> 0/348.
//   * 4/5 Agu gecesinde OLCULEN GERCEK TIKANMA (yerel icerik 63 dk = 3780 sn bekledi)
//     esigin USTUNDE kalir -> o vaka HALA rc 3.
//   * Pay neden 2,4x DEGIL: 2,4 x 3078 = 7387 sn (123 dk) olurdu ve yakalanmasi
//     gereken 74 dk'lik olayi KACIRIRDI. Ayirt etme gucu artik CARPANDAN degil
//     TABANDAN gelir (bosta gecen pencere bekleme suresine girmez).
// M2 (kritik yol bolunmesi) bu pencereyi 17,3 dk -> 11,0 dk'ya cektigi icin pay
// zamanla BUYUR; daralirsa bu sabit YENIDEN OLCULEREK guncellenir.
const YAYIN_BEKLEME_UST_SINIRI_SN = sayiEnv("PARITE_YAYIN_BEKLEME_UST_SINIRI_SN",
  3600, 30, 86400);
// Yayin hali komutunun kendi sure siniri: asilan kapi OLU kapidir.
const YAYIN_HALI_ZAMAN_ASIMI_MS = 240000;
// HEAD commit anini okuma butcesi. Asilirsa OLCULEMEDI -> fail-closed (eski olcuye duser).
const HEAD_ZAMAN_ASIMI_MS = 10000;

/**
 * OLCUM ARIZASI — "ayrisma" DEGIL, "hukum veremedim". Asla KIRMIZI'ya (1) donusmez, ama
 * asla 0'a da izin vermez: sonucYaz() bunlari olculemedi[] listesine alir.
 *   tur: WAF | 429 | ZAMAN_ASIMI | TAVAN | FIKSTUR | AG
 */
class OlcumHatasi extends Error {
  constructor(tur, mesaj, kod) {
    super(mesaj);
    this.olcum = true;
    this.tur = tur;
    this.kod = kod;
  }
}

/** WAF/UA duvari (403). Geriye donuk ad: .waf alani korunuyor. */
class WafHatasi extends OlcumHatasi {
  constructor(kod, url) {
    super("WAF", "HTTP " + kod + " (WAF/UA) " + url, kod);
    this.waf = true;
  }
}

/** Ayni origin'deki kardes ucu turet: .../ara -> .../katalog (sabit URL yazmadan). */
function kardesUc(uc, ad) {
  const u = new URL(uc);
  u.search = "";
  u.hash = "";
  u.pathname = u.pathname.replace(/[^/]*$/, ad);
  return u.toString();
}

/**
 * Canli uca atilan TOPLAM istek sayaci (rapora yazilir — gereksiz yuk gorulebilsin).
 * BUTCE: hatasiz kosumda  istek = sorgu + 1 (on-kosul sayimi)
 *        sayilar ayriysa  istek = sorgu + 1 + min(ceil(n/100), SUPURME_TAVANI)
 *        her yeniden deneme +1 (429/zaman asimi/5xx; ust sinir DENEME).
 */
function sayacYeni(tavan) {
  return { istek: 0, r429: 0, yenidenDeneme: 0, supurmeParti: 0, tavan: tavan || 0 };
}

function bekle(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

function zamanAsimiMi(e) {
  if (!e) return false;
  const adlar = [e.name, e.cause && e.cause.name, e.code, e.cause && e.cause.code];
  return adlar.some((a) => a === "TimeoutError" || a === "AbortError" ||
    a === "ETIMEDOUT" || a === "UND_ERR_CONNECT_TIMEOUT" || a === "UND_ERR_HEADERS_TIMEOUT");
}

/**
 * Tarayici UA + no-cache + ZAMAN ASIMI ile GET.
 *   403      -> WafHatasi (duvar; denemek yalniz yuk bindirir)
 *   429      -> GECICI kabul edilir: ustel beklemeyle `deneme` kez tekrar; tukenirse
 *               OlcumHatasi("429")  (asla sessiz gecmez, asla KIRMIZI olmaz)
 *   zaman as.-> OlcumHatasi("ZAMAN_ASIMI") (tekrar denendikten sonra)
 *   5xx/JSON -> tekrar denenir, tukenirse duz Error (= AYRISMA sayilir, eski davranis)
 */
async function canliGetir(url, sayac, deneme) {
  const kere = Math.max(1, Math.min(deneme || 1, DENEME));
  let son = null;
  for (let i = 0; i < kere; i++) {
    if (sayac.tavan && sayac.istek >= sayac.tavan) {
      throw new OlcumHatasi("TAVAN", "istek TAVANI asildi (" + sayac.tavan + ") — " + url);
    }
    if (i > 0) sayac.yenidenDeneme++;
    sayac.istek++;
    let r;
    try {
      r = await fetch(url, {
        headers: {
          "user-agent": TARAYICI_UA,
          "cache-control": "no-cache",
          accept: "application/json",
        },
        signal: AbortSignal.timeout(ZAMAN_ASIMI_MS),
      });
    } catch (e) {
      son = zamanAsimiMi(e)
        ? new OlcumHatasi("ZAMAN_ASIMI", "zaman asimi (" + ZAMAN_ASIMI_MS + " ms): " + url)
        : e;
      if (i + 1 < kere) { await bekle(BEKLEME_MS * Math.pow(2, i)); continue; }
      throw son;
    }
    // WAF imzasi: govde JSON bile degildir; tekrar denemek yalniz yuk bindirir.
    if (r.status === 403) { await r.text().catch(() => {}); throw new WafHatasi(403, url); }
    if (r.status === 429) {
      await r.text().catch(() => {});
      sayac.r429++;
      son = new OlcumHatasi("429", "HTTP 429 (hiz siniri, " + kere + " deneme tukendi): " + url, 429);
      if (i + 1 < kere) { await bekle(BEKLEME_MS * Math.pow(2, i)); continue; }
      throw son;
    }
    let j;
    try {
      j = await r.json();
    } catch (e) {
      son = new Error("JSON degil (HTTP " + r.status + ")");
      if (i + 1 < kere) { await bekle(BEKLEME_MS * Math.pow(2, i)); continue; }
      throw son;
    }
    if (j && j.hata && r.status >= 500) {
      son = new Error(String(j.hata));
      if (i + 1 < kere) { await bekle(BEKLEME_MS * Math.pow(2, i)); continue; }
      throw son;
    }
    return { durum: r.status, govde: j };
  }
  throw son || new OlcumHatasi("AG", "istek yapilamadi: " + url);
}

/** Nonce: CDN onbellegi ISTEK'teki no-cache'i yok sayar; anahtari degistirmek SART. */
function nonceUret() {
  return Date.now().toString(36) + "-" + process.pid + "-" + Math.random().toString(36).slice(2, 8);
}

/** CANLI katalogdaki TOPLAM urun sayisi. Doner: tam sayi | null (alan okunamadi). */
async function canliKatalogSayisi(uc, sayac, nonce) {
  const u = new URL(kardesUc(uc, "katalog"));
  u.searchParams.set("sayfa", "1");
  u.searchParams.set("boy", "1");
  u.searchParams.set("_nonce", nonce);
  const { govde } = await canliGetir(u.toString(), sayac, DENEME);
  const n = govde && govde.toplam;
  return Number.isInteger(n) ? n : null;
}

/**
 * Verilen yerel id'lerden D1'de OLMAYANLARI dondurur (/katalog?ids= partiler halinde).
 * Bu, "yerel ⊆ D1" onermesinin KANITIDIR. TAVAN asilirsa kanit URETILMEZ -> OlcumHatasi.
 */
async function d1deOlmayanlar(uc, idler, sayac, nonce) {
  const temel = kardesUc(uc, "katalog");
  const partiler = [];
  for (let i = 0; i < idler.length; i += IDS_PARTI) partiler.push(idler.slice(i, i + IDS_PARTI));

  // Tavan KATALOGDAN turer (yukaridaki supurmeTavani): sabit sayi katalog buyuyunce
  // sahte kirmizi uretiyordu. Asilmasi ancak MUTLAK sinirin otesinde mumkundur.
  const tavan = supurmeTavani(idler.length);
  if (partiler.length > tavan) {
    throw new OlcumHatasi("TAVAN",
      "supurme TAVANI asildi: " + partiler.length + " parti > tavan " + tavan +
      " (katalog " + idler.length + " id, mutlak sinir " + SUPURME_MUTLAK_TAVAN +
      " parti) — 'yerel ⊆ D1' kaniti URETILMEDI");
  }
  sayac.supurmeParti += partiler.length;

  const eksik = [];
  let sirada = 0;
  async function isci() {
    while (sirada < partiler.length) {
      const parti = partiler[sirada++];
      const u = new URL(temel);
      u.searchParams.set("ids", parti.join(","));
      u.searchParams.set("_nonce", nonce + "-" + sirada);
      const { govde } = await canliGetir(u.toString(), sayac, DENEME);
      const bulunan = new Set(((govde && govde.urunler) || []).map((x) => x.id));
      for (const id of parti) if (!bulunan.has(id)) eksik.push(id);
    }
  }
  await Promise.all(Array.from({ length: Math.min(IDS_ESZAMAN, partiler.length) }, isci));
  return eksik;
}

/**
 * Yayin hali komutunun argv'si. Doner: string dizisi | null (komut YOK/bozuk).
 * PARITE_YAYIN_HALI (JSON argv dizisi) YALNIZ fikstur icindir ve FIKSTUR_ENV'dedir ->
 * verildigi kosum pariteyi ASLA BELGELENDIREMEZ. Fikstur modunda komut VERILMEMISSE
 * canli D1'e DOKUNULMAZ (null doner) — bir kabul fiksturu asla gercek katalogu okumaz.
 */
function yayinHaliArgv(env) {
  const e = env || process.env;
  const ham = e.PARITE_YAYIN_HALI;
  if (ham !== undefined && String(ham).trim() !== "") {
    let a = null;
    try { a = JSON.parse(ham); } catch (x) { return null; }
    if (Array.isArray(a) && a.length && a.every((s) => typeof s === "string" && s)) return a;
    return null;
  }
  if (fiksturBayraklari(e).length) return null;
  return ["python3", path.join(__dirname, "yayin-kapisi.py"), "--hal-json"];
}

/**
 * Verilen id'lerin D1'deki YAYIN HALINI oku (tek cagri, id'ler stdin'den).
 * Doner: { olculdu:true, yok[], yayinda[], taslak[{id,sayfa,yasSn}], sayfaOlculdu,
 *          artefaktYasSn } | { olculdu:false, sebep }
 *
 * 🔴 FAIL-CLOSED: komut yok / cikis sifir-disi / JSON bozuk / SORULAN BIR ID ICIN HAL
 * DONMEMIS -> olculdu:false. Cagiran taraf bunu KIRMIZI'ya cevirir; "olcemedim" hicbir
 * kolonda "iyi" degildir. Kismi cevap KABUL EDILMEZ: eksik kalan tek id, gercek kaybi
 * sessizce muaf yapardi.
 */
function yayinHaliOku(idler) {
  const argv = yayinHaliArgv();
  if (!argv) {
    return { olculdu: false, sebep: (process.env.PARITE_YAYIN_HALI ? "PARITE_YAYIN_HALI " +
      "cozulemedi (JSON argv dizisi bekleniyor)" : "FIKSTUR MODU: yayin hali komutu " +
      "VERILMEDI -> canli D1 OKUNMAZ") };
  }
  let r;
  try {
    r = cp.spawnSync(argv[0], argv.slice(1), {
      input: idler.join("\n"),
      encoding: "utf8",
      maxBuffer: 128 * 1024 * 1024,
      timeout: YAYIN_HALI_ZAMAN_ASIMI_MS,
    });
  } catch (e) {
    return { olculdu: false, sebep: "komut calistirilamadi: " + (e && e.message) };
  }
  if (r.error) return { olculdu: false, sebep: "komut calistirilamadi: " + r.error.message };
  const kuyruk = (s) => String(s || "").trim().slice(-300);
  if (r.status !== 0) {
    return { olculdu: false, sebep: "komut cikis " + r.status + " — " +
      kuyruk(r.stdout) + " | " + kuyruk(r.stderr) };
  }
  const satirlar = String(r.stdout || "").split("\n").map((s) => s.trim()).filter(Boolean);
  let j = null;
  try { j = JSON.parse(satirlar[satirlar.length - 1] || ""); } catch (e) { j = null; }
  if (!j || typeof j !== "object") {
    return { olculdu: false, sebep: "cikti JSON degil — " + kuyruk(r.stdout) };
  }
  if (j.olculdu !== true) {
    return { olculdu: false, sebep: String(j.sebep || "olculdu=false") };
  }
  const dizi = (x) => (Array.isArray(x) ? x.filter((s) => typeof s === "string" && s) : null);
  const yok = dizi(j.yok);
  const yayinda = dizi(j.yayinda);
  const hamTaslak = Array.isArray(j.taslak) ? j.taslak : null;
  if (!yok || !yayinda || !hamTaslak) {
    return { olculdu: false, sebep: "cikti sozlesmeye uymuyor (yok/yayinda/taslak dizi degil)" };
  }
  const taslak = [];
  for (const t of hamTaslak) {
    if (!t || typeof t.id !== "string" || !t.id) {
      return { olculdu: false, sebep: "taslak kaydinda id YOK" };
    }
    taslak.push({
      id: t.id,
      sayfa: Number.isInteger(t.sayfa) ? t.sayfa : null,
      yasSn: Number.isInteger(t.yas_sn) ? t.yas_sn : null,
    });
  }
  const kapsanan = new Set(yok.concat(yayinda, taslak.map((t) => t.id)));
  const eksikOlcum = idler.filter((id) => !kapsanan.has(id));
  if (eksikOlcum.length) {
    return { olculdu: false, sebep: eksikOlcum.length + " id icin hal DONMEDI (kismi olcum " +
      "KABUL EDILMEZ) — or. " + eksikOlcum.slice(0, 3).join(", ") };
  }
  return {
    olculdu: true, yok, yayinda, taslak,
    sayfaOlculdu: j.sayfa_olculdu === true,
    artefaktYasSn: Number.isInteger(j.artefakt_yas_sn) ? j.artefakt_yas_sn : null,
  };
}

/**
 * YEREL HEAD COMMIT'ININ YASI (saniye) — EKSEN B'nin ikinci tabani.
 * Doner: tam sayi >= 0 | null (OKUNAMADI -> cagiran FAIL-CLOSED davranir).
 *
 * 🔴 NE ISE YARAR: "artefakt yasi" bosta gecen pencereyi de tasir; yerel icerigin
 * bekleme suresi ise en fazla HEAD'in yasi kadardir (o commit'ten once bu icerik
 * ORTADA YOKTU). Ikisinin KUCUGU gercek bekleme suresidir.
 * ⚠️ `--ff-only` ile alinan dallarda committer tarihi ESKI olabilir; o halde HEAD yasi
 * BUYUK cikar ve olcu artefakt yasina geri duser — yani sapma DAIMA fail-closed yonde.
 * PARITE_YEREL_HEAD_YAS_SN YALNIZ fikstur icindir ve FIKSTUR_ENV'dedir (bir kabul
 * kosumu asla gercek git gecmisini okumaz, ayrica o kosum 0 URETEMEZ).
 */
function yerelHeadYasiSn(env) {
  const e = env || process.env;
  const ham = e.PARITE_YEREL_HEAD_YAS_SN;
  if (ham !== undefined && String(ham).trim() !== "") {
    const n = parseInt(String(ham).trim(), 10);
    return Number.isFinite(n) && n >= 0 ? n : null;   // cozulemedi -> OKUNAMADI
  }
  let r;
  try {
    r = cp.spawnSync("git", ["-C", __dirname, "log", "-1", "--format=%ct", "HEAD"],
      { encoding: "utf8", timeout: HEAD_ZAMAN_ASIMI_MS });
  } catch (x) {
    return null;
  }
  if (!r || r.error || r.status !== 0) return null;
  const t = parseInt(String(r.stdout || "").trim(), 10);
  if (!Number.isFinite(t) || t <= 0) return null;
  return Math.max(0, Math.floor(Date.now() / 1000) - t);
}

/**
 * EKSEN B'nin OLCUSU: yerel icerik NE KADARDIR yayinsiz bekliyor (saniye).
 * Doner: { beklemeSn, headYasSn, tabani } — beklemeSn null ise OLCULEMEDI.
 * SAF: girdi olarak artefakt yasi + HEAD yasi alir (fikstur bunlari verebilsin).
 */
function beklemeSuresi(artefaktYasSn, headYasSn) {
  if (artefaktYasSn === null || artefaktYasSn === undefined) {
    return { beklemeSn: null, headYasSn, tabani: "artefakt yasi OLCULEMEDI" };
  }
  if (headYasSn === null || headYasSn === undefined) {
    // FAIL-CLOSED: HEAD okunamadi -> ESKI olcuye (artefakt yasi) duseriz. Bu, bosta
    // gecen pencereyi tikanma sayan KATI davranistir; yeni bir YESIL yol acmaz.
    return { beklemeSn: artefaktYasSn, headYasSn: null,
      tabani: "yerel HEAD ani OKUNAMADI -> artefakt yasi (KATI/fail-closed)" };
  }
  return headYasSn < artefaktYasSn
    ? { beklemeSn: headYasSn, headYasSn, tabani: "yerel HEAD commit ani" }
    : { beklemeSn: artefaktYasSn, headYasSn, tabani: "son yayin ani" };
}

/** "1837 sn" -> "30,6 dk" (cikti insan okusun diye; hesap SANIYE uzerinden yapilir). */
function dk(sn) {
  return sn === null || sn === undefined ? "OLCULEMEDI" : (sn / 60).toFixed(1) + " dk";
}

/**
 * ON-KOSUL: checkout katalogu ile CANLI katalog ayni mi; degilse "katalog farki"
 * siniflandirmasi acilabilir mi?
 *
 * Doner: { gecikmeModu, kirmizi, notlar[], olculemedi[], canliSayi, yerelSayi, acik }
 *   gecikmeModu=false -> ESKI DAVRANIS: her ayrisim KIRMIZI (fail-closed).
 *   kirmizi (metin)   -> on-kosul ZATEN kirmizi (yerelde var/D1'de yok).
 *   olculemedi[]      -> sonucYaz bunlari 3'e cevirir (0'a ASLA izin vermez).
 * WAF (403) on-kosulda YUKARI ATILIR: duvar varken tum sorgu havuzunu atmak anlamsiz.
 */
async function onKosulOlc({ uc, yerelIdler, sayac, nonce }) {
  const notlar = [];
  const olculemedi = [];
  const yerelSayi = yerelIdler.length;
  // Kanitlanmis TASLAK id'ler: D1'de SATIRI VAR ama yayinda=0 -> uc onlari BILEREK
  // gizler. Karsilastirma korpusundan cikarilirlar (bkz. siniflandir()).
  let taslakIdler = new Set();
  const kapali = (n) => {
    notlar.push(n);
    olculemedi.push(n);
    return { gecikmeModu: false, kirmizi: null, notlar, olculemedi,
      canliSayi: null, yerelSayi, acik: 0, taslakIdler };
  };

  let canliSayi = null;
  try {
    canliSayi = await canliKatalogSayisi(uc, sayac, nonce);
  } catch (e) {
    if (e && e.waf) throw e;                       // duvar: yukari, kosum bosuna
    return kapali("canli katalog sayisi OLCULEMEDI (" + (e && e.message) +
      ") -> siniflandirma KAPALI, her ayrisim KIRMIZI");
  }
  if (canliSayi === null) {
    return kapali("/katalog 'toplam' alani okunamadi -> siniflandirma KAPALI, her ayrisim KIRMIZI");
  }
  if (canliSayi === yerelSayi) {
    notlar.push("checkout katalogu CANLI ile ayni (" + yerelSayi +
      ") -> siniflandirma KAPALI (her ayrisim KIRMIZI)");
    return { gecikmeModu: false, kirmizi: null, notlar, olculemedi, canliSayi, yerelSayi,
      acik: 0, taslakIdler };
  }

  // Sayilar farkli: "katalog farki" IDDIASI ancak yerel ⊆ D1 KANITLANIRSA acilir.
  let eksik;
  try {
    eksik = await d1deOlmayanlar(uc, yerelIdler, sayac, nonce);
  } catch (e) {
    if (e && e.waf) throw e;
    // 🔴 TAVAN, oteki supurme arizalarindan AYRI BIRIMDE hukum alir ([[hukum-yanlis-birimde]]).
    // Oteki arizalar = "uc cevap vermedi" -> eski kati davranis (siniflandirma KAPALI,
    // ayrisim varsa KIRMIZI) aynen surer. TAVAN = "BIZ istek butcemizi asmamayi sectik",
    // yani kanitin uretilmemesi UCUN degil OLCUM ARACININ halidir; orada bulunacak her
    // "kirmizi" katalog farkiyla aciklanabilir bir sapma olabilir ve DAYANAKSIZDIR.
    // O yuzden kosum sorgulari HIC olcmeden ACIK OLCULEMEDI ile durur (sessiz yanlis-kirmizi
    // YERINE). Sira korunur: on-kosul KIRMIZISI bu noktadan ONCE donmustur (1 > 3 > 0).
    if (e && e.tur === "TAVAN") {
      const n = "SUPURME TAVANI: " + (e && e.message) + " -> kanit URETILEMEDI, hicbir " +
        "ayrisim SINIFLANDIRILAMAZ. Bu kosum pariteyi BELGELENDIREMEZ (OLCULEMEDI); " +
        "katalog farkiyla aciklanabilir sapmalari KIRMIZI saymak DAYANAKSIZ olurdu.";
      notlar.push(n);
      olculemedi.push(n);
      return { gecikmeModu: false, kirmizi: null, durdu: n, notlar, olculemedi,
        canliSayi, yerelSayi, acik: 0, taslakIdler };
    }
    return kapali("id supurmesi TAMAMLANAMADI (" + (e && e.message) +
      ") -> kanit yok, siniflandirma KAPALI (her ayrisim KIRMIZI)");
  }

  if (eksik.length) {
    // ── EKSIK ID'LER: "YAYIN GECIKMESI" mi "GERCEK KAYIP" mi? ────────────────────
    // Sayi farkina BAKILMAZ; `yayinda` kolonu FIILEN okunur (dosya basi "YAYIN PENCERESI").
    const kirmiziBasi = "YERELDE VAR / D1'DE YOK: " + eksik.length + " urun. yerel=" +
      yerelSayi + " canli=" + canliSayi + " | ornek: " + eksik.slice(0, 5).join(", ");
    const kirmiziDon = (sebep) => ({
      gecikmeModu: false, kirmizi: kirmiziBasi + " | " + sebep,
      notlar, olculemedi, canliSayi, yerelSayi, acik: canliSayi - yerelSayi, taslakIdler,
    });

    const hal = yayinHaliOku(eksik);
    if (!hal.olculdu) {
      // 🔴 FAIL-CLOSED: hal OKUNAMADIYSA eski (kati) davranis aynen surer.
      return kirmiziDon("YAYIN HALI OKUNAMADI (" + hal.sebep + ") -> sinif AYIRT " +
        "EDILEMEDI, fail-closed KIRMIZI. 'Olcemedim' YESIL SAYILMAZ.");
    }
    if (hal.yok.length) {
      return kirmiziDon("GERCEK KAYIP: " + hal.yok.length + " id'nin D1'de SATIRI HIC YOK " +
        "(taslak DEGIL — senkron dusmus, Ege GOREMEZ = sessiz satis kaybi) | ornek: " +
        hal.yok.slice(0, 5).join(", "));
    }
    if (hal.yayinda.length) {
      return kirmiziDon("YAYINDA AMA GORUNMUYOR: " + hal.yayinda.length + " id D1'de " +
        "yayinda=1 oldugu HALDE /katalog?ids= dondurmedi (yayin gecikmesiyle ACIKLANAMAZ " +
        "— uc/indeks gerilemesi) | ornek: " + hal.yayinda.slice(0, 5).join(", "));
    }

    // Buradan sonra: eksik cikan HER id kanitlanmis TASLAK. Ust sinir uygulanir.
    // EKSEN A — ZARARLI: sayfasi CANLIDA 200 olan taslak (site satiyor, Ege goremez).
    const zararli = hal.taslak.filter((t) => t.sayfa === 200);
    const asan = zararli.filter((t) => t.yasSn === null || t.yasSn > YAYIN_UST_SINIRI_SN);
    if (asan.length) {
      return kirmiziDon("TASLAK ama SAYFASI CANLI: " + asan.length + " urun, yayin adimi " +
        "UST SINIRI (" + dk(YAYIN_UST_SINIRI_SN) + ") asti ya da yasi OLCULEMEDI (" +
        asan.map((t) => t.id + "=" + dk(t.yasSn)).slice(0, 3).join(", ") + "). Sayfa " +
        "CANLIDA 200 donerken satir TASLAK: bu pencere DEGIL TIKANMADIR -> KIRMIZI.");
    }

    taslakIdler = new Set(hal.taslak.map((t) => t.id));
    const gizliKalan = hal.taslak.length - zararli.length;
    notlar.push("⏳ YAYIN GECIKMESI: " + hal.taslak.length + " satir D1'de VAR ama TASLAK " +
      "(yayinda=0) -> uc onlari BILEREK gizliyor. KIRMIZI DEGIL. " + zararli.length +
      " tanesinin sayfasi CANLI (yayin adimi bekliyor, en yaslisi " +
      dk(zararli.reduce((a, t) => Math.max(a, t.yasSn || 0), 0)) + "), " + gizliKalan +
      " tanesinin sayfasi HENUZ CANLI DEGIL (gosterilseydi 404 veren kart olurdu). " +
      "Karsilastirma korpusundan CIKARILDI -> sorgular KOSAR. " +
      "Canli artefakt yasi: " + dk(hal.artefaktYasSn) +
      " | ornek: " + hal.taslak.slice(0, 3).map((t) => t.id).join(", "));

    // EKSEN B — ZARARSIZ taslaklarin ust siniri: KIRMIZI degil, ama KANONIK de degil.
    // 🔴 OLCU "artefakt yasi" DEGIL "YEREL ICERIGIN BEKLEME SURESI"dir (bkz. dosya basi
    // YAYIN_BEKLEME_UST_SINIRI_SN): bosta gecen pencere bekleme SAYILMAZ.
    // (Kosul AYRI degiskende: mutasyon nobeti bu satiri TEK TEK bozabilsin.)
    const bekleme = beklemeSuresi(hal.artefaktYasSn, yerelHeadYasiSn());
    const eksenBAsti = gizliKalan > 0 &&
      (bekleme.beklemeSn === null || bekleme.beklemeSn > YAYIN_BEKLEME_UST_SINIRI_SN);
    if (!hal.sayfaOlculdu) {
      const n = "TASLAK yigini sayfa probu TAVANINI asti -> hangi taslagin sayfasi canli " +
        "OLCULMEDI. Gerileme sayilmaz (KIRMIZI DEGIL) ama bu kosum pariteyi BELGELENDIREMEZ.";
      notlar.push(n);
      olculemedi.push(n);
    } else if (eksenBAsti) {
      // 🔴 SEBEP AYRISTIRILIR — iki hal AYNI kutuya konmaz ([[hukum-yanlis-birimde]]).
      const n = bekleme.beklemeSn === null
        ? "UST SINIR / OLCULEMEDI: " + gizliKalan + " taslagin sayfasi canli degil ve " +
          "site en son NE ZAMAN deploy etti OKUNAMADI (" + bekleme.tabani + ") -> bekleme " +
          "suresi hesaplanamadi. KIRMIZI DEGIL ama YESIL DE DEGIL."
        : "UST SINIR / TIKANMA: " + gizliKalan + " taslagin sayfasi canli degil ve YEREL " +
          "ICERIK " + dk(bekleme.beklemeSn) + " once yayina hazirdi (sinir " +
          dk(YAYIN_BEKLEME_UST_SINIRI_SN) + " · taban: " + bekleme.tabani + " · site en " +
          "son " + dk(hal.artefaktYasSn) + " once deploy etti · yerel HEAD " +
          dk(bekleme.headYasSn) + " once). Bekleme olculen azami yayin penceresinin " +
          "(51,3 dk) USTUNDE -> bu 'pencere' DEGIL, hat TIKANMIS olabilir. KIRMIZI DEGIL " +
          "ama YESIL DE DEGIL: bu kosum pariteyi BELGELENDIRMEZ.";
      notlar.push(n);
      olculemedi.push(n);
    } else if (gizliKalan > 0 && hal.artefaktYasSn !== null &&
               hal.artefaktYasSn > YAYIN_BEKLEME_UST_SINIRI_SN) {
      // BAYAT ARTEFAKT ama TIKANMA DEGIL: eski olcu burada KIRMIZI/rc3 uretirdi.
      // Olculen yanlis-pozitif sinifi (2 Agu 00:57 -> 07:28: 6,5 saat BOSTA, sonra push).
      notlar.push("BAYAT ARTEFAKT ama TIKANMA DEGIL: site en son " + dk(hal.artefaktYasSn) +
        " once deploy etti, ama yerel icerik yalnizca " + dk(bekleme.beklemeSn) +
        " once hazir oldu (" + bekleme.tabani + ") -> aradaki fark BOSTA GECEN penceredir, " +
        "bekleme suresi degildir. Eksen B YANMAZ.");
    }
  }

  // Taslaklar cikarildiktan sonraki ETKIN yerel korpus — canli sayiyla bu karsilastirilir.
  // 🔴 METIN SOZLESMESI: taslak YOKKEN cikti BIREBIR eski haliyle kalir ("yerel=N");
  // taslak varsa dusum ACIKCA yazilir. Kabul testleri (parite-fikstur-test.js S1/S13) bu
  // ifadeyi olcer — sessizce yeniden adlandirmak o kapilari OLU birakirdi.
  const yerelEtkin = yerelSayi - taslakIdler.size;
  const yerelYazi = taslakIdler.size
    ? "yerel=" + yerelSayi + " (taslak " + taslakIdler.size + " dusuldu -> etkin=" + yerelEtkin + ")"
    : "yerel=" + yerelSayi;
  if (canliSayi === yerelEtkin) {
    if (taslakIdler.size) {
      notlar.push("Taslaklar dusuldukten sonra korpuslar BIREBIR: " + yerelYazi +
        " = canli=" + canliSayi + " -> siniflandirma KAPALI (kati mod).");
    }
    return { gecikmeModu: false, kirmizi: null, notlar, olculemedi, canliSayi, yerelSayi,
      acik: 0, taslakIdler };
  }
  if (canliSayi < yerelEtkin) {
    // Tutarsiz: canli sayi daha kucuk ama her yerel id D1'de bulundu (sayi onbellegi bayat
    // olabilir, KV TTL 300 sn). Kanit celisik -> siniflandirma ACILMAZ.
    return kapali("TUTARSIZ olcum: canli=" + canliSayi + " < " + yerelYazi +
      " ama yerel id'lerin hepsi D1'de -> siniflandirma KAPALI (fail-closed)");
  }

  // ⚠️ TESHIS: kanit yalnizca "yerel ⊂ canli"yi soyler; SEBEBI SOYLEMEZ. Iki olasilik
  // ADIYLA sayilir, kesin hukum BASILMAZ (bkz. dosya basi "TESHIS DURUSTLUGU").
  const acik = canliSayi - yerelEtkin;
  const teshis = "D1 FAZLALIGI: " + yerelYazi + " < canli=" + canliSayi +
    " | fazla=" + acik + " satir; supurme kaniti: yerel id'lerin TAMAMI D1'de. " +
    "SEBEP AYIRT EDILEMEDI -> (a) dal/checkout BAYAT (main ilerlemis) ya da " +
    "(b) D1'de YETIM satir (yerelde silinmis urun D1'de duruyor). " +
    "Tam parite BELGELENDIRILEMEDI.";
  notlar.push(teshis);
  olculemedi.push(teshis);
  return { gecikmeModu: true, kirmizi: null, notlar, olculemedi, canliSayi, yerelSayi, acik,
    taslakIdler };
}

/**
 * TEK SORGU siniflandirmasi. SAF fonksiyon (ag yok) — fikstur bunu dogrudan olcer.
 * Doner: { sinif, sebep, fazla[], kesin }
 *
 * `kesin`: bu sorguda hukum TAM MI olculdu? Gecikme modunda /ara'nin dondurdugu pencere
 * kendi ilan ettigi `toplam`i KAPSAMIYORSA (limit'e dayanildi ya da uc daha az satir
 * dondurdu) pencere DISINDA kalan yerel id'ler HIC GORULMEDI -> o sorgu icin "tehlikeli
 * yon YOK" denemez. sonucYaz bunu sayar ve KESIN HUKUM cumlesini basmaz.
 */
function siniflandir({ bekIds: hamBekIds, alinan, toplam, limit, yerelIdKume, gecikmeModu,
  taslakKume }) {
  // 🔴 TASLAK SUZGECI — arama SEMANTIGINE DOKUNMAZ, KORPUSU daraltir.
  // Taslak satir D1'in HICBIR kesif yuzeyinde gorunmez (yayinda=1 sarti), yani onun
  // aranabilirligi OLCULEBILIR bir sey DEGILDIR. Yerel beklentide birakilirsa her sorgu
  // "sayi tutmuyor" diye kirmizi yanar ve gercek bir gerileme bu gurultuye gomulur.
  // Suzmek olcum KAYBI degildir: kume, `yayinda` kolonu FIILEN OKUNARAK kanitlanmis
  // id'lerden olusur (on-kosul); D1'de OLMAYAN bir id buraya ASLA giremez.
  // Sonuc listesinden cikarmak korpustan cikarmakla AYNIDIR: site tarafi saf bir
  // suzgectir (index.html filtered), Ege tarafinda skor korpus-BAGIMSIZDIR ve siralama
  // kararlidir -> kalan ogelerin BAGIL sirasi degismez.
  const bekIds = (taslakKume && taslakKume.size)
    ? hamBekIds.filter((id) => !taslakKume.has(id))
    : hamBekIds;
  const bekKirpik = bekIds.slice(0, limit);
  const ayniSayi = toplam === bekIds.length;
  const ayniListe = alinan.length === bekKirpik.length &&
    alinan.every((id, i) => id === bekKirpik[i]);
  // Pencere, ucun ilan ettigi toplami kapsiyor mu (yani D1'in TUM eslesme kumesi gorildu mu)?
  const kesin = !gecikmeModu || alinan.length >= toplam;
  if (ayniSayi && ayniListe) return { sinif: SINIF_GECTI, sebep: "", fazla: [], kesin };

  // Ham (siniflandirmasiz) sebep — eski ciktinin aynisi, teshis icin korunuyor.
  let hamSebep;
  if (!ayniSayi) {
    hamSebep = "sayi: /ara=" + toplam + " yerel=" + bekIds.length;
  } else {
    const ilk = alinan.findIndex((id, i) => id !== bekKirpik[i]);
    hamSebep = ilk !== -1
      ? "sira/icerik " + ilk + ". sirada: /ara=" + alinan[ilk] + " yerel=" + bekKirpik[ilk]
      : "uzunluk: /ara=" + alinan.length + " yerel=" + bekKirpik.length;
  }

  if (!gecikmeModu) return { sinif: SINIF_ACIKLANAMAYAN, sebep: hamSebep, fazla: [], kesin };

  // ── Katalog farki modu: YONE bak ────────────────────────────────────────────
  const fazla = alinan.filter((id) => !yerelIdKume.has(id));
  // Fazlaliklari suzunce kalan liste, yerel sonucun ONEKI olmak ZORUNDA: yeni urun
  // katalogun BASINA eklenir, mevcutlarin BAGIL sirasi degismez (seq korunur, Ege
  // skoru korpus-bagimsiz). Onek bozuluyorsa bu katalog farkiyla ACIKLANAMAZ.
  const suzulmus = fazla.length ? alinan.filter((id) => yerelIdKume.has(id)) : alinan;
  for (let i = 0; i < suzulmus.length; i++) {
    if (suzulmus[i] !== bekIds[i]) {
      return {
        sinif: SINIF_ACIKLANAMAYAN,
        sebep: "SIRA farki (katalog farkiyla aciklanamaz) " + i + ". sirada: /ara=" +
          suzulmus[i] + " yerel=" + bekIds[i] + " | " + hamSebep,
        fazla, kesin,
      };
    }
  }
  // yerel ⊆ D1 kanitlandigi icin D1 eslesmesi yerel eslesmesinden AZ OLAMAZ.
  if (toplam < bekIds.length) {
    return {
      sinif: SINIF_ACIKLANAMAYAN,
      sebep: "D1 EKSIK eslesme: /ara toplam=" + toplam + " < yerel=" + bekIds.length +
        " (yerel ⊆ D1 kanitina AYKIRI -> arama metni/indeks farki)",
      fazla, kesin,
    };
  }

  // ── 🔴 UZUNLUK KAPISI — 8. YUTMA (olculdu 27 Tem: C6/C7/C12, site VE Ege) ──────────
  // YUKARIDAKI IKI KAPI DA SUSABILIYOR:
  //   (a) ONEK kontrolu UZUNLUK OLCMEZ. Kurban (yerelde VAR / D1 aramasinda YOK) yerel
  //       listenin KUYRUGUNDA ise onek bozulmaz — dongu kurbandan ONCE biter.
  //   (b) Sayi kapisi (toplam < bekIds.length), D1'e yeni giren urunler sayiyi TELAFI
  //       ettiginde tetiklenmez (kaybedilen 1 yerel, kazanilan 1 yeniyle kapanir).
  // Ikisi birlikte susunca "Ege GOREMEZ" ayrisimi ACIKLANAN damgasi yiyip cikis 3
  // uretiyordu ve cikti "hicbir ayrisim tehlikeli yonde DEGIL" diye OLGUSAL YANLIS
  // basiyordu (taban 45753c1f ayni girdide 1 veriyordu -> REGRESYON).
  //
  // OLCU: pencerede gorunmesi GEREKEN yerel id sayisi = pencereye giren satir sayisi
  // eksi katalog farkinin ACIKLAYABILECEGI yeni urun BUTCESI (toplam - yerel). Pencerede
  // gorulen yerel id sayisi bunun ALTINA duserse aradaki fark, D1 aramasinda GORUNMEYEN
  // yerel urun sayisinin ALT SINIRIDIR — telafi bunu GIZLEYEMEZ.
  // Yanlis-pozitif YOK: saglikli gecikmede pencereye giren fazlalik butceyi ASAMAZ
  // (fazla ⊆ yeni eslesmeler), pencere DOLU olsa bile (olculdu: C18/C19 + birim B3/B4).
  const butce = Math.max(0, toplam - bekIds.length);
  const yerelBeklenen = alinan.length - butce;
  if (suzulmus.length < yerelBeklenen) {
    const gorulen = new Set(alinan);
    const kayip = bekIds.filter((id) => !gorulen.has(id));
    const enAz = yerelBeklenen - suzulmus.length;
    return {
      sinif: SINIF_ACIKLANAMAYAN,
      sebep: "YERELDE VAR / D1 ARAMASINDA YOK: en az " + enAz + " urun (Ege GOREMEZ = " +
        "sessiz satis kaybi). Pencerede yerel id " + suzulmus.length + " ama beklenen " +
        yerelBeklenen + " (/ara satir=" + alinan.length + " - katalog farki butcesi=" +
        butce + "); D1 fazlaligi SAYIYI TELAFI ETTIGI icin sayi kapisi susmustu | aday: " +
        (kayip.slice(0, 5).join(", ") || "(pencere disi)") + " | " + hamSebep,
      fazla, kesin,
    };
  }

  if (!fazla.length) {
    return { sinif: SINIF_ACIKLANAN, sebep: hamSebep + " (D1 fazlaligi pencere disinda)",
      fazla, kesin };
  }
  return { sinif: SINIF_ACIKLANAN, sebep: hamSebep + " | D1 fazlasi: " + fazla.length,
    fazla, kesin };
}

/**
 * TEK KARAR NOKTASI. Butun arizalar (WAF/429/zaman asimi/tavan/fikstur) buraya
 * `olculemedi` metin listesi olarak gelir; karar hatalar[] DEGERLENDIRILDIKTEN SONRA
 * verilir. Sira: 1 (kirmizi) > 3 (olculemedi/aciklanan) > 0.
 *
 * 🔴 REGRESYON NOBETI: bu fonksiyondan ONCE hicbir yerde process.exit() cagrilmamalidir.
 * Eskiden `if (wafHatasi) process.exit(wafYaz(...))` hatalar[]'dan ONCE calisiyordu ->
 * kosum ortasinda gelen 429/403, BULUNMUS gercek kirmizilari silip 3 yaziyordu
 * (olculdu: B1 118 kirmiziyken, A13/A14 11 kirmiziyken -> yeni kod 3, eski kod 1).
 */
function sonucYaz({ etiket, gecti, atlandi, hatalar, onKosul, sayac, sn, fazlaKume, olculemedi,
  olculemeyenPencere }) {
  const olc = []
    .concat((onKosul && onKosul.olculemedi) || [])
    .concat(olculemedi || []);
  const kirmiziLar = hatalar.filter((h) => h.sinif !== SINIF_ACIKLANAN);
  const aciklananLar = hatalar.filter((h) => h.sinif === SINIF_ACIKLANAN);

  console.log("");
  console.log("gecti: %d | ACIKLANAMAYAN: %d | ACIKLANAN(senkron): %d | atlandi: %d | %s sn",
    gecti, kirmiziLar.length, aciklananLar.length, atlandi || 0, sn);
  console.log("canli istek: %d (429: %d | yeniden deneme: %d | supurme partisi: %d)",
    sayac.istek, sayac.r429 || 0, sayac.yenidenDeneme || 0, sayac.supurmeParti || 0);

  const aciklananYaz = () => {
    console.log("\nAÇIKLANAN AYRISIMLAR (ilk 10) — hepsi 'D1 fazla / yerel eksik' yonunde:");
    for (const h of aciklananLar.slice(0, 10)) {
      // kat/marka DA yazilir: ayni sorgu metni farkli filtrelerle iki kez gecebilir; filtre
      // yazilmayinca cikti "ayni sorgu iki farkli sonuc verdi" gibi YANILTICI gorunuyordu.
      console.log("  q=%j%s -> %s", h.q,
        h.kat ? " kat=" + JSON.stringify(h.kat) + " marka=" + JSON.stringify(h.marka) : "",
        h.sebep);
    }
    if (fazlaKume) {
      console.log("  D1'de gorulen, yerelde olmayan AYRI id: %d (sayi acigi: %d)",
        fazlaKume.size, (onKosul && onKosul.acik) || 0);
    }
    // 🔴 DURUSTLUK KAPISI (27 Tem): "hicbir ayrisim tehlikeli yonde DEGIL" bir OLCUM
    // IDDIASIDIR — yalnizca gercekten olculduyse basilir. /ara'nin dondurdugu pencere,
    // ucun ilan ettigi toplami kapsamayan sorgularda pencere DISINDAKI yerel id'ler HIC
    // GORULMEDI; orada kesin hukum kurmak (eski metin) olgusal yanlis riski tasir.
    if (olculemeyenPencere) {
      console.log("⚪ KATALOG FARKI (%d ayrisim) — olculen ayrisimlar katalog farkiyla " +
        "UYUMLU. [%s]", aciklananLar.length, etiket);
      console.log("   ⚠️ AMA KESIN HUKUM VERILEMEZ: %d sorguda /ara'nin dondurdugu pencere " +
        "kendi ilan ettigi toplami KAPSAMADI -> pencere DISINDAKI yerel id'ler OLCULMEDI. " +
        "'Hicbir ayrisim yerelde-var/D1'de-yok yonunde DEGIL' DENEMEZ.", olculemeyenPencere);
    } else {
      console.log("⚪ SENKRON GECİKMESİ / KATALOG FARKI (%d ayrisim) — PARITE KIRIK DEGIL. " +
        "KIRMIZI DEGIL. [%s]", aciklananLar.length, etiket);
      console.log("   Hicbir ayrisim 'yerelde var/D1'de yok' ya da SIRA yonunde DEGIL.");
    }
    console.log("   Kontrol sirasi: (a) dali guncel main'e merge/rebase et; " +
      "(b) duzelmezse D1'de YETIM satir olabilir -> python3 tools/d1-sync.py --durum");
  };

  // 1) KIRMIZI DAIMA KAZANIR — ariza olsa da olmasa da.
  if (kirmiziLar.length) {
    console.log("\nAYRISAN SORGULAR — AÇIKLANAMAYAN (ilk 25):");
    for (const h of kirmiziLar.slice(0, 25)) {
      console.log("  q=%j%s\n    -> %s", h.q,
        h.kat ? " kat=" + JSON.stringify(h.kat) + " marka=" + JSON.stringify(h.marka) : "",
        h.sebep);
    }
    if (aciklananLar.length) {
      console.log("\n(ayrica %d AÇIKLANAN/senkron ayrisim var — gurultu, ama yukaridakini " +
        "MASKELEMEZ)", aciklananLar.length);
    }
    if (olc.length) {
      console.log("\n⚠️ AYRICA OLCUM ARIZASI VAR — ama KIRMIZI KAZANIR (1 > 3 > 0); " +
        "ariza bulunmus ayrisimi SILEMEZ:");
      for (const n of olc) console.log("   ⚪ " + n);
    }
    console.log("\nSONUC: PARITE YOK ❌ (%d aciklanamayan / %d sorgu) [%s]",
      kirmiziLar.length, gecti + hatalar.length, etiket);
    return CIKIS_KIRMIZI;
  }

  // 2) OLCUM ARIZASI -> 3 (asla 0)
  if (olc.length) {
    console.log("\n⚪ ÖLÇÜLEMEDİ — bu kosum pariteyi BELGELENDIRMEZ (cikis 3, KIRMIZI DEGIL) [%s]",
      etiket);
    for (const n of olc) console.log("   • " + n);
    if (aciklananLar.length) aciklananYaz();
    return CIKIS_OLCULEMEDI;
  }

  // 3) Yalniz aciklanan ayrisim -> 3
  if (aciklananLar.length) {
    aciklananYaz();
    return CIKIS_OLCULEMEDI;
  }

  return CIKIS_GECTI;
}

/** OLCUM ARIZASI metnini uret (sonucYaz'a `olculemedi` girdisi olarak verilir). */
function olcumNotu(e, etiket) {
  if (!e) return "OLCULEMEDI (sebep yok) [" + etiket + "]";
  if (e.tur === "WAF") {
    return "ÖLÇÜLEMEDİ: WAF/UA — canli uc HTTP " + e.kod + " dondu (" + etiket + "). " +
      "Tarayici UA gonderilmesine ragmen duvara carpildi: AYRISMA DEGIL, olcum yapilamadi.";
  }
  if (e.tur === "429") {
    return "ÖLÇÜLEMEDİ: HIZ SINIRI (429) — ustel beklemeyle " + DENEME +
      " deneme TUKENDI (" + etiket + "). Ayrisma SAYILMADI, ama parite de BELGELENMEDI.";
  }
  if (e.tur === "ZAMAN_ASIMI") {
    return "ÖLÇÜLEMEDİ: ZAMAN ASIMI (" + ZAMAN_ASIMI_MS + " ms/istek, " + DENEME +
      " deneme) — uc susuyor (" + etiket + "). Asilan kapi olu kapidir; sureç asilmadi.";
  }
  if (e.tur === "TAVAN") {
    return "ÖLÇÜLEMEDİ: TAVAN — " + e.message + " (af YOK: siniflandirma KAPALI)";
  }
  return "ÖLÇÜLEMEDİ: " + (e.message || String(e)) + " [" + etiket + "]";
}

/** Geriye donuk ad — artik yalniz metin uretir; KARARI sonucYaz verir. */
function wafYaz(e, sayac, etiket) {
  return olcumNotu(e, etiket);
}

/**
 * Kosum boyunca gorulen "D1 fazlasi" AYRI id sayisi, sayi acigini ASIYOR mu?
 * ASIYORSA aciklama COKER -> KIRMIZI (yetim satir imzasi).
 * ASMIYORSA hukum verilmez: sayilar iki olayi (bayat checkout / yetim satir) AYIRMAZ;
 * belirsizlik zaten on-kosulun olculemedi notunda yazilidir (3, asla 0).
 */
function fazlalikTeshis(fazlaKume, acik) {
  if (!fazlaKume || !fazlaKume.size) return { kirmizi: null };
  if (fazlaKume.size > (acik || 0)) {
    return {
      kirmizi: "D1'de yerelde OLMAYAN " + fazlaKume.size + " ayri id gorildu ama sayi acigi " +
        "yalniz " + (acik || 0) + " — katalog farki bunu ACIKLAMAZ (D1'de YETIM satir " +
        "imzasi: yerelde silinmis urun D1'de duruyor, Ege hala satiyor)",
    };
  }
  return { kirmizi: null };
}

/** ESKI AD (geriye donuk): {tutarli, sebep}. Yeni kod fazlalikTeshis kullanir. */
function fazlaKumeTutarli(fazlaKume, acik) {
  const t = fazlalikTeshis(fazlaKume, acik);
  return t.kirmizi ? { tutarli: false, sebep: t.kirmizi } : { tutarli: true, sebep: "" };
}

/**
 * FIKSTUR MODU notu (varsa). stdout + stderr'e BASILIR (A15: uyari tuketiciye
 * ulasmiyordu — filament-test.py ATLANDI'da stdout'u yutuyordu).
 */
function fiksturNotu() {
  const bayraklar = fiksturBayraklari();
  if (!bayraklar.length) return null;
  return "FIKSTUR MODU: test-only env verildi (" + bayraklar.join(", ") + ") -> kanonik " +
    "katalog/uc OLCULMEDI. Bu kosum pariteyi ASLA BELGELENDIREMEZ (en iyi ihtimalle 3).";
}

module.exports = {
  TARAYICI_UA, CIKIS_GECTI, CIKIS_KIRMIZI, CIKIS_KOSULAMADI, CIKIS_OLCULEMEDI,
  SINIF_GECTI, SINIF_ACIKLANAN, SINIF_ACIKLANAMAYAN,
  ZAMAN_ASIMI_MS, DENEME, BEKLEME_MS, SUPURME_MUTLAK_TAVAN, supurmeTavani, IDS_PARTI,
  mutlakTavan, katalogIdAdedi, MUTLAK_KAT, MUTLAK_TABAN_PARTI,
  FIKSTUR_ENV,
  OlcumHatasi, WafHatasi, kardesUc, sayacYeni, canliGetir, nonceUret,
  canliKatalogSayisi, d1deOlmayanlar, onKosulOlc, siniflandir,
  sonucYaz, wafYaz, olcumNotu, fazlaKumeTutarli, fazlalikTeshis,
  fiksturBayraklari, fiksturNotu,
  YAYIN_UST_SINIRI_SN, YAYIN_BEKLEME_UST_SINIRI_SN,
  yayinHaliArgv, yayinHaliOku, yerelHeadYasiSn, beklemeSuresi, dk,
};
