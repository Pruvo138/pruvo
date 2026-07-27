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
 * ║   2  CIKIS_KOSULAMADI  Test KOSULAMADI (parite-ege.js: bot kaynagi/fonksiyonu yok). ║
 * ║   3  CIKIS_OLCULEMEDI  Olcum TAM DEGIL / hukum verilemedi. Sebepleri:               ║
 * ║                          WAF-UA duvari (403) · hiz siniri (429, deneme tukendi)     ║
 * ║                          zaman asimi · supurme TAVANI asildi · katalog sayilari     ║
 * ║                          ayri (senkron gecikmesi / D1'de yetim satir — AYIRT        ║
 * ║                          EDILEMEZ) · FIKSTUR MODU (test-only env verilmis)          ║
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
 * VERI CAPASI YOK: bu dosyada hicbir sabit urun sayisi/id/SHA/tarih yoktur — her sayi
 * kosum aninda olculur.
 */

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
// SUPURME TAVANI: /katalog?ids= parti sayisi ust siniri (1 parti = 100 id).
// Tavansizdi: 25k katalogda tek kosumda 250 ek istek atilirdi. Tavan asilirsa "yerel ⊆ D1"
// kaniti URETILMEZ -> siniflandirma KAPALI, AF YOK (ayrisim varsa 1, yoksa 3; asla 0).
// DEGER SECIMI (veri capasi DEGIL, olcek siniri): 200 parti = 20.000 id. Ege'nin bellek
// modeli zaten ~20-25k'da 128 MB'i asiyor ([[katalog-olcek-siniri]]), yani bu tavanin
// carpildigi nokta "kanit yontemi katalogu buyuttu" degil "katalog Ege'yi asti" noktasidir.
// Tavan carpilirsa cikti bunu ACIKCA yazar (sessiz zayiflama yok).
const SUPURME_TAVANI = sayiEnv("PARITE_SUPURME_TAVANI", 200, 1, 100000);

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

  if (partiler.length > SUPURME_TAVANI) {
    throw new OlcumHatasi("TAVAN",
      "supurme TAVANI asildi: " + partiler.length + " parti > tavan " + SUPURME_TAVANI +
      " (katalog " + idler.length + " id) — 'yerel ⊆ D1' kaniti URETILMEDI");
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
  const kapali = (n) => {
    notlar.push(n);
    olculemedi.push(n);
    return { gecikmeModu: false, kirmizi: null, notlar, olculemedi,
      canliSayi: null, yerelSayi, acik: 0 };
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
    return { gecikmeModu: false, kirmizi: null, notlar, olculemedi, canliSayi, yerelSayi, acik: 0 };
  }

  // Sayilar farkli: "katalog farki" IDDIASI ancak yerel ⊆ D1 KANITLANIRSA acilir.
  let eksik;
  try {
    eksik = await d1deOlmayanlar(uc, yerelIdler, sayac, nonce);
  } catch (e) {
    if (e && e.waf) throw e;
    return kapali("id supurmesi TAMAMLANAMADI (" + (e && e.message) +
      ") -> kanit yok, siniflandirma KAPALI (her ayrisim KIRMIZI)");
  }

  if (eksik.length) {
    return {
      gecikmeModu: false,
      kirmizi: "YERELDE VAR / D1'DE YOK: " + eksik.length + " urun (Ege GOREMEZ = sessiz " +
        "satis kaybi). yerel=" + yerelSayi + " canli=" + canliSayi +
        " | ornek: " + eksik.slice(0, 5).join(", "),
      notlar, olculemedi, canliSayi, yerelSayi, acik: canliSayi - yerelSayi,
    };
  }
  if (canliSayi < yerelSayi) {
    // Tutarsiz: canli sayi daha kucuk ama her yerel id D1'de bulundu (sayi onbellegi bayat
    // olabilir, KV TTL 300 sn). Kanit celisik -> siniflandirma ACILMAZ.
    return kapali("TUTARSIZ olcum: canli=" + canliSayi + " < yerel=" + yerelSayi +
      " ama yerel id'lerin hepsi D1'de -> siniflandirma KAPALI (fail-closed)");
  }

  // ⚠️ TESHIS: kanit yalnizca "yerel ⊂ canli"yi soyler; SEBEBI SOYLEMEZ. Iki olasilik
  // ADIYLA sayilir, kesin hukum BASILMAZ (bkz. dosya basi "TESHIS DURUSTLUGU").
  const acik = canliSayi - yerelSayi;
  const teshis = "D1 FAZLALIGI: yerel=" + yerelSayi + " < canli=" + canliSayi +
    " | fazla=" + acik + " satir; supurme kaniti: yerel id'lerin TAMAMI D1'de. " +
    "SEBEP AYIRT EDILEMEDI -> (a) dal/checkout BAYAT (main ilerlemis) ya da " +
    "(b) D1'de YETIM satir (yerelde silinmis urun D1'de duruyor). " +
    "Tam parite BELGELENDIRILEMEDI.";
  notlar.push(teshis);
  olculemedi.push(teshis);
  return { gecikmeModu: true, kirmizi: null, notlar, olculemedi, canliSayi, yerelSayi, acik };
}

/**
 * TEK SORGU siniflandirmasi. SAF fonksiyon (ag yok) — fikstur bunu dogrudan olcer.
 * Doner: { sinif, sebep, fazla[] }
 */
function siniflandir({ bekIds, alinan, toplam, limit, yerelIdKume, gecikmeModu }) {
  const bekKirpik = bekIds.slice(0, limit);
  const ayniSayi = toplam === bekIds.length;
  const ayniListe = alinan.length === bekKirpik.length &&
    alinan.every((id, i) => id === bekKirpik[i]);
  if (ayniSayi && ayniListe) return { sinif: SINIF_GECTI, sebep: "", fazla: [] };

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

  if (!gecikmeModu) return { sinif: SINIF_ACIKLANAMAYAN, sebep: hamSebep, fazla: [] };

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
        fazla,
      };
    }
  }
  // yerel ⊆ D1 kanitlandigi icin D1 eslesmesi yerel eslesmesinden AZ OLAMAZ.
  if (toplam < bekIds.length) {
    return {
      sinif: SINIF_ACIKLANAMAYAN,
      sebep: "D1 EKSIK eslesme: /ara toplam=" + toplam + " < yerel=" + bekIds.length +
        " (yerel ⊆ D1 kanitina AYKIRI -> arama metni/indeks farki)",
      fazla,
    };
  }
  if (!fazla.length) {
    return { sinif: SINIF_ACIKLANAN, sebep: hamSebep + " (D1 fazlaligi pencere disinda)", fazla };
  }
  return { sinif: SINIF_ACIKLANAN, sebep: hamSebep + " | D1 fazlasi: " + fazla.length, fazla };
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
function sonucYaz({ etiket, gecti, atlandi, hatalar, onKosul, sayac, sn, fazlaKume, olculemedi }) {
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
    console.log("⚪ SENKRON GECİKMESİ / KATALOG FARKI (%d ayrisim) — PARITE KIRIK DEGIL. " +
      "KIRMIZI DEGIL. [%s]", aciklananLar.length, etiket);
    console.log("   Hicbir ayrisim 'yerelde var/D1'de yok' ya da SIRA yonunde DEGIL.");
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
  ZAMAN_ASIMI_MS, DENEME, BEKLEME_MS, SUPURME_TAVANI, IDS_PARTI, FIKSTUR_ENV,
  OlcumHatasi, WafHatasi, kardesUc, sayacYeni, canliGetir, nonceUret,
  canliKatalogSayisi, d1deOlmayanlar, onKosulOlc, siniflandir,
  sonucYaz, wafYaz, olcumNotu, fazlaKumeTutarli, fazlalikTeshis,
  fiksturBayraklari, fiksturNotu,
};
