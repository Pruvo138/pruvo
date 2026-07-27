"use strict";
/**
 * PARITE ORTAK — iki parite testinin (site + Ege) PAYLASTIGI gurultu-imzasi ayirici.
 *
 * NEDEN VAR (olculdu, 27 Tem): parite testleri "yerel checkout'un katalogu" ile "canli D1"i
 * karsilastirir. Bir isci dali (worktree) main'den GERIDE kaldiginda D1 ilerlemis olur ->
 * testler AYRISMA sayar ve KIRMIZI yanar. Olculen imza: 108/300 ayrisim, 108/108'i SAYI
 * farki, 108/108'i "D1 fazla / yerel eksik" yonunde, 0 sira farki. Yani kod saglikli,
 * yalniz checkout BAYAT. Bu gurultu, GERCEK kirilmayla ayni renkte yaniyordu -> teshis
 * imkansizdi ("parite kirik mi, checkout bayat mi?").
 *
 * AYIRIM (mimar karari):
 *   AÇIKLANAN      = D1'de VAR / yerelde YOK  -> yalniz senkron gecikmesi -> cikis 3, KIRMIZI DEGIL
 *   AÇIKLANAMAYAN  = yerelde VAR / D1'de YOK  -> Ege GOREMEZ = sessiz satis kaybi -> cikis 1
 *                  = SIRA farki               -> siralama iddiasi kirik      -> cikis 1
 * Karisik kosumda (ikisi birlikte) sonuc DAIMA KIRMIZI: aciklanan gurultu, aciklanamayani
 * MASKELEMEZ.
 *
 * "AÇIKLANAN" DAMGASI BEDAVA DEGIL — KANIT SART. Sayi farki gormek yetmez; asagidaki
 * on-kosul yerel id'lerin TAMAMINI /katalog?ids= ile D1'e karsi SUPURUR ve "yerel ⊆ D1"
 * onermesini KANITLAR. Kanit yoksa siniflandirma ACILMAZ (fail-closed: her ayrisim KIRMIZI).
 * Boylece "D1'de yetim satir var" (yerelde silinmis urunu Ege hala satiyor) gibi GERCEK
 * hatalar gurultu diye yuvarlanamaz.
 *
 * VERI CAPASI YOK: bu dosyada hicbir sabit urun sayisi/id/SHA/tarih yoktur — her sayi
 * kosum aninda olculur.
 */

// Cloudflare WAF varsayilan urllib/python-requests UA'sina 403 verir (media.pruvo3d.com'da
// olculdu, 27 Tem'de CANLI /ara ucunda da dogrulandi: urllib UA -> 403, Chrome UA -> 200).
// Node fetch bugun geciyor; UA'yi YINE DE acik yaziyoruz ki uc siki kural uygularsa
// testler sessizce "site bozuk" raporlamasin.
const TARAYICI_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " +
  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

const CIKIS_GECTI = 0;        // birebir parite
const CIKIS_KIRMIZI = 1;      // aciklanamayan ayrisim (gerilemenin ta kendisi)
const CIKIS_OLCULEMEDI = 3;   // olcum yapilamadi / yalniz senkron gecikmesi — KIRMIZI DEGIL

const SINIF_GECTI = "gecti";
const SINIF_ACIKLANAN = "aciklanan";
const SINIF_ACIKLANAMAYAN = "aciklanamayan";

const IDS_PARTI = 100;        // /katalog?ids= ucunun kendi tavani (fazlasini kirpar)
const IDS_ESZAMAN = 4;

/** WAF/UA duvari — "ayrisma" DEGIL, "olculemedi". */
class WafHatasi extends Error {
  constructor(kod, url) {
    super("HTTP " + kod + " (WAF/UA) " + url);
    this.kod = kod;
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

/** Canli uca atilan TOPLAM istek sayaci (rapora yazilir — gereksiz yuk gorulebilsin). */
function sayacYeni() {
  return { istek: 0 };
}

/**
 * Tarayici UA + no-cache ile GET. 403/429 -> WafHatasi (DENENMEZ, ustteki katman
 * "OLCULEMEDI: WAF/UA" yazsin). Diger hatalarda `deneme` kez tekrar dener.
 */
async function canliGetir(url, sayac, deneme) {
  const kere = deneme || 1;
  let son;
  for (let i = 0; i < kere; i++) {
    sayac.istek++;
    let r;
    try {
      r = await fetch(url, {
        headers: {
          "user-agent": TARAYICI_UA,
          "cache-control": "no-cache",
          accept: "application/json",
        },
      });
    } catch (e) {
      son = e;
      if (i + 1 < kere) { await bekle(400 * (i + 1)); continue; }
      throw son;
    }
    // WAF imzasi: govde JSON bile degildir; tekrar denemek yalniz yuk bindirir.
    if (r.status === 403 || r.status === 429) throw new WafHatasi(r.status, url);
    let j;
    try {
      j = await r.json();
    } catch (e) {
      son = new Error("JSON degil (HTTP " + r.status + ")");
      if (i + 1 < kere) { await bekle(400 * (i + 1)); continue; }
      throw son;
    }
    if (j && j.hata && r.status >= 500) {
      son = new Error(String(j.hata));
      if (i + 1 < kere) { await bekle(400 * (i + 1)); continue; }
      throw son;
    }
    return { durum: r.status, govde: j };
  }
  throw son || new Error("istek yapilamadi");
}

function bekle(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

/** Nonce: CDN onbellegi ISTEK'teki no-cache'i yok sayar; anahtari degistirmek SART. */
function nonceUret() {
  return Date.now().toString(36) + "-" + process.pid + "-" + Math.random().toString(36).slice(2, 8);
}

/**
 * CANLI katalogdaki TOPLAM urun sayisi (/katalog?sayfa=1&boy=1 -> toplam).
 * Doner: tam sayi | null (olculemedi). WAF'ta ustteki katmana atar.
 */
async function canliKatalogSayisi(uc, sayac, nonce) {
  const u = new URL(kardesUc(uc, "katalog"));
  u.searchParams.set("sayfa", "1");
  u.searchParams.set("boy", "1");
  u.searchParams.set("_nonce", nonce);
  const { govde } = await canliGetir(u.toString(), sayac, 3);
  const n = govde && govde.toplam;
  return Number.isInteger(n) ? n : null;
}

/**
 * Verilen yerel id'lerden D1'de OLMAYANLARI dondurur (/katalog?ids= partiler halinde).
 * Bu, "yerel ⊆ D1" onermesinin KANITIDIR: bos donerse yerel katalogdaki her urun D1'de
 * VAR demektir; dolayisiyla sayi/fazlalik ayrisimlarinin tek aciklamasi D1'in ILERIDE
 * olmasidir. Dolu donerse Ege goremeyen urun var -> KIRMIZI.
 */
async function d1deOlmayanlar(uc, idler, sayac, nonce) {
  const temel = kardesUc(uc, "katalog");
  const partiler = [];
  for (let i = 0; i < idler.length; i += IDS_PARTI) partiler.push(idler.slice(i, i + IDS_PARTI));

  const eksik = [];
  let sirada = 0;
  async function isci() {
    while (sirada < partiler.length) {
      const parti = partiler[sirada++];
      const u = new URL(temel);
      u.searchParams.set("ids", parti.join(","));
      u.searchParams.set("_nonce", nonce + "-" + sirada);
      const { govde } = await canliGetir(u.toString(), sayac, 3);
      const bulunan = new Set(((govde && govde.urunler) || []).map((x) => x.id));
      for (const id of parti) if (!bulunan.has(id)) eksik.push(id);
    }
  }
  await Promise.all(Array.from({ length: Math.min(IDS_ESZAMAN, partiler.length) }, isci));
  return eksik;
}

/**
 * ON-KOSUL: checkout katalogu ile CANLI katalog ayni mi; degilse "senkron gecikmesi"
 * siniflandirmasi acilabilir mi?
 *
 * Doner: { gecikmeModu, kirmizi, notlar[], canliSayi, yerelSayi, acik }
 *   gecikmeModu=false -> ESKI DAVRANIS: her ayrisim KIRMIZI (fail-closed).
 *   kirmizi (metin)   -> on-kosul ZATEN kirmizi (yerelde var/D1'de yok); sorgu kosmaya gerek yok.
 */
async function onKosulOlc({ uc, yerelIdler, sayac, nonce }) {
  const notlar = [];
  const yerelSayi = yerelIdler.length;
  let canliSayi = null;
  try {
    canliSayi = await canliKatalogSayisi(uc, sayac, nonce);
  } catch (e) {
    if (e && e.waf) throw e;
    notlar.push("⚪ canli katalog sayisi OLCULEMEDI (" + (e && e.message) +
      ") -> siniflandirma KAPALI, her ayrisim KIRMIZI");
    return { gecikmeModu: false, kirmizi: null, notlar, canliSayi: null, yerelSayi, acik: 0 };
  }
  if (canliSayi === null) {
    notlar.push("⚪ /katalog toplam alani okunamadi -> siniflandirma KAPALI, her ayrisim KIRMIZI");
    return { gecikmeModu: false, kirmizi: null, notlar, canliSayi: null, yerelSayi, acik: 0 };
  }
  if (canliSayi === yerelSayi) {
    notlar.push("checkout katalogu CANLI ile ayni (" + yerelSayi +
      ") -> siniflandirma KAPALI (her ayrisim KIRMIZI)");
    return { gecikmeModu: false, kirmizi: null, notlar, canliSayi, yerelSayi, acik: 0 };
  }

  // Sayilar farkli: "senkron gecikmesi" IDDIASI ancak yerel ⊆ D1 KANITLANIRSA acilir.
  let eksik;
  try {
    eksik = await d1deOlmayanlar(uc, yerelIdler, sayac, nonce);
  } catch (e) {
    if (e && e.waf) throw e;
    notlar.push("⚪ id supurmesi TAMAMLANAMADI (" + (e && e.message) +
      ") -> kanit yok, siniflandirma KAPALI (her ayrisim KIRMIZI)");
    return { gecikmeModu: false, kirmizi: null, notlar, canliSayi, yerelSayi, acik: 0 };
  }

  if (eksik.length) {
    return {
      gecikmeModu: false,
      kirmizi: "YERELDE VAR / D1'DE YOK: " + eksik.length + " urun (Ege GOREMEZ = sessiz " +
        "satis kaybi). yerel=" + yerelSayi + " canli=" + canliSayi +
        " | ornek: " + eksik.slice(0, 5).join(", "),
      notlar, canliSayi, yerelSayi, acik: canliSayi - yerelSayi,
    };
  }
  if (canliSayi < yerelSayi) {
    // Tutarsiz: canli sayi daha kucuk ama her yerel id D1'de bulundu (sayi onbellegi bayat
    // olabilir, KV TTL 300 sn). Kanit celisik -> siniflandirma ACILMAZ.
    notlar.push("⚠️ TUTARSIZ olcum: canli=" + canliSayi + " < yerel=" + yerelSayi +
      " ama yerel id'lerin hepsi D1'de -> siniflandirma KAPALI (fail-closed)");
    return { gecikmeModu: false, kirmizi: null, notlar, canliSayi, yerelSayi, acik: 0 };
  }
  notlar.push("checkout BAYAT: yerel=" + yerelSayi + " < canli=" + canliSayi +
    " | yerel id'lerin TAMAMI D1'de (supurme kaniti) -> senkron gecikmesi siniflandirmasi ACIK");
  return {
    gecikmeModu: true, kirmizi: null, notlar, canliSayi, yerelSayi,
    acik: canliSayi - yerelSayi,
  };
}

/**
 * TEK SORGU siniflandirmasi. SAF fonksiyon (ag yok) — fikstur bunu dogrudan olcer.
 *
 *   bekIds     : referans (site/Ege kodu) sonucu, SIRALI, tam liste
 *   alinan     : /ara'dan donen id listesi (limit ile kirpik olabilir)
 *   toplam     : /ara'nin bildirdigi KIRPILMAMIS eslesme sayisi
 *   limit      : istenen limit (kirpma tespiti icin)
 *   yerelIdKume: yerel katalogdaki TUM id'ler (fazlaligi tespit icin)
 *   gecikmeModu: on-kosul "yerel ⊆ D1" kanitini verdiyse true
 *
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

  // ── Senkron gecikmesi modu: YONE bak ────────────────────────────────────────
  // D1'in dondurdugu, yerel katalogda HIC olmayan id'ler = gecikmenin kendisi.
  const fazla = alinan.filter((id) => !yerelIdKume.has(id));
  // Fazlaliklari suzunce kalan liste, yerel sonucun ONEKI olmak ZORUNDA: yeni urun
  // katalogun BASINA eklenir, mevcutlarin BAGIL sirasi degismez (seq korunur, Ege
  // skoru korpus-bagimsiz). Onek bozuluyorsa bu senkronla ACIKLANAMAZ.
  const suzulmus = fazla.length ? alinan.filter((id) => yerelIdKume.has(id)) : alinan;
  for (let i = 0; i < suzulmus.length; i++) {
    if (suzulmus[i] !== bekIds[i]) {
      return {
        sinif: SINIF_ACIKLANAMAYAN,
        sebep: "SIRA farki (senkronla aciklanamaz) " + i + ". sirada: /ara=" +
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
    // Sayi farki var ama D1 fazlaligi GORULMEDI (kirpik pencerede olabilir). Sayi
    // buyumesi yine de gecikmeyle uyumlu; degilse ustteki iki kapi yakalar.
    return { sinif: SINIF_ACIKLANAN, sebep: hamSebep + " (D1 fazlaligi pencere disinda)", fazla };
  }
  return { sinif: SINIF_ACIKLANAN, sebep: hamSebep + " | D1 fazlasi: " + fazla.length, fazla };
}

/**
 * Kosum sonucunu YAZ ve CIKIS KODUNU dondur. Tek karar noktasi:
 *   aciklanamayan>0 -> 1 (KIRMIZI; aciklanan gurultu MASKELEMEZ)
 *   yoksa aciklanan>0 -> 3 (⚪ SENKRON GECIKMESI)
 *   yoksa -> 0
 */
function sonucYaz({ etiket, gecti, atlandi, hatalar, onKosul, sayac, sn, fazlaKume }) {
  const kirmiziLar = hatalar.filter((h) => h.sinif !== SINIF_ACIKLANAN);
  const aciklananLar = hatalar.filter((h) => h.sinif === SINIF_ACIKLANAN);

  console.log("");
  console.log("gecti: %d | ACIKLANAMAYAN: %d | ACIKLANAN(senkron): %d | atlandi: %d | %s sn",
    gecti, kirmiziLar.length, aciklananLar.length, atlandi || 0, sn);
  console.log("canli istek: %d", sayac.istek);

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
    console.log("\nSONUC: PARITE YOK ❌ (%d aciklanamayan / %d sorgu) [%s]",
      kirmiziLar.length, gecti + hatalar.length, etiket);
    return CIKIS_KIRMIZI;
  }

  if (aciklananLar.length) {
    console.log("\nAÇIKLANAN AYRISIMLAR (ilk 10) — hepsi 'D1 fazla / yerel eksik' yonunde:");
    for (const h of aciklananLar.slice(0, 10)) {
      console.log("  q=%j -> %s", h.q, h.sebep);
    }
    if (fazlaKume) {
      console.log("  D1'de gorulen, yerelde olmayan AYRI id: %d (sayi acigi: %d)",
        fazlaKume.size, (onKosul && onKosul.acik) || 0);
    }
    console.log("\n⚪ SENKRON GECİKMESİ (%d ayrisim) — PARITE KIRIK DEGIL, checkout BAYAT. " +
      "KIRMIZI DEGIL. [%s]", aciklananLar.length, etiket);
    console.log("   Cozum: dali guncel main'e rebase/merge et (ya da ana checkout'ta kostur). " +
      "Hicbir ayrisim 'yerelde var/D1'de yok' ya da SIRA yonunde DEGIL.");
    return CIKIS_OLCULEMEDI;
  }

  return CIKIS_GECTI;
}

/** WAF/UA duvari raporu — cikis 3 (olculemedi), "ayrisma" SAYILMAZ. */
function wafYaz(e, sayac, etiket) {
  console.log("");
  console.log("⚪ ÖLÇÜLEMEDİ: WAF/UA — canli uc HTTP %s dondu (%s).", e.kod, etiket);
  console.log("   Tarayici UA gonderiliyor olmasina ragmen duvara carpildi: bu bir AYRISMA " +
    "DEGIL, olcum yapilamadi. Ayrisma SAYILMADI.");
  console.log("canli istek: %d", sayac.istek);
  return CIKIS_OLCULEMEDI;
}

/** Kosum boyunca gorulen "D1 fazlasi" AYRI id sayisi, sayi acigini ASIYOR mu? */
function fazlaKumeTutarli(fazlaKume, acik) {
  if (!fazlaKume || !acik) return { tutarli: true, sebep: "" };
  if (fazlaKume.size <= acik) return { tutarli: true, sebep: "" };
  return {
    tutarli: false,
    sebep: "D1'de yerelde OLMAYAN " + fazlaKume.size + " ayri id gorildu ama sayi acigi " +
      "yalniz " + acik + " — 'senkron gecikmesi' bunu ACIKLAMAZ (D1'de yetim satir olabilir)",
  };
}

module.exports = {
  TARAYICI_UA, CIKIS_GECTI, CIKIS_KIRMIZI, CIKIS_OLCULEMEDI,
  SINIF_GECTI, SINIF_ACIKLANAN, SINIF_ACIKLANAMAYAN,
  WafHatasi, kardesUc, sayacYeni, canliGetir, nonceUret,
  canliKatalogSayisi, d1deOlmayanlar, onKosulOlc, siniflandir,
  sonucYaz, wafYaz, fazlaKumeTutarli,
};
