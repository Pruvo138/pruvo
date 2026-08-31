/**
 * pruvo-shop — SIPARIS KANALI + REKLAM ATFI SINIFLAMASI (TEK KAYNAK).
 *
 * NEDEN AYRI DOSYA: ayni yargi IKI YUZEYDE lazim —
 *   (1) YONETIM PANELI  — kartin "Kaynak" satiri (shop/src/yonet.js /liste -> kartHtml),
 *   (2) KANAL KIRILIM RAPORU — tools/kanal-kirilim-raporu.py (adet + ciro kovalari).
 * Iki yerde iki kopya tutulsaydi panelin ETIKETI ile raporun KOVASI sessizce ayrisirdi:
 * ekran "organik" der, rapor ayni siparisi "atif yok" sayar, ikisi de kendince "dogru"
 * gorunur ve kimse olcmez ([[ayni-alan-iki-hukum-biri-sessiz]]). Bu dosya o tek karardir;
 * panel de rapor da BURADAN turer, ikinci sozluk YOKTUR.
 *
 * 🔴 NEDEN `.mjs` (ve `.js` DEGIL): bu modulu Worker (wrangler bundle) DISINDA node da
 * dogrudan calistirir (rapor CLI'i + shop/test/panel-atif.mjs). Uzantisi `.js` olsaydi
 * modul turu en yakin package.json'a bagli olurdu — depoda package.json YOK, CI node 20
 * (`.github/workflows/deploy.yml`) ise `.js` icindeki ESM sozdizimini KENDILIGINDEN
 * ALGILAMAZ (o davranis node 22.7+). `.mjs` her node surumunde tek anlamlidir.
 *
 * 🔒 GIZLILIK — PANELE/RAPORA BASILMAYAN ALANLAR (Okan/mimar karari):
 *   ga_client_id · fbp · fbc   → KISIYE BAGLANAN reklam-eslestirme kimlikleri.
 * Bunlar `siparisler.atif` icinde DURUR (Meta CAPI / GA4 olcumu shop/src/olcum.js'te
 * onlari kullanir — orasi kendi beyaz-listesini uygular) ama YONETIM EKRANINDA ve
 * RAPORDA operasyonel degerleri YOKTUR: Okan'in "bu siparis hangi reklamdan geldi"
 * sorusunu utm alanlari + ref zaten cevaplar. Ekrana basilan her kimlik omuz-ustu okunabilen,
 * ekran goruntusuyle disari cikabilen bir kimliktir; degeri olmayan bir alani basmak
 * sizinti yuzeyini bedava buyutur. Ayni gerekce `gclid`/`gbraid`/`wbraid` icin de
 * gecerlidir (tiklama kimlikleri) — `ref` zaten o kayda goturur, click-id'nin kendisi
 * panelde ise yaramaz. Bu yuzden asagidaki beyaz-liste POZITIFTIR: yeni bir atif alani
 * eklendiginde varsayilan olarak BASILMAZ (fail-closed), acikca eklenmesi gerekir.
 */

// ---- KANAL degerleri (siparisler.kanal) ---------------------------------------
// 'site'     -> pruvo3d.com self-servis akisi (index.js /baslat). D1 kolonunun DEFAULT'u.
// 'whatsapp' -> Ege'nin (WhatsApp botu) kapattigi siparis (yonet.js /wa-siparis).
export const KANAL_SITE = "site";
export const WA_KANAL = "whatsapp";

// ---- KOVALAR ------------------------------------------------------------------
// 🔴 IKI KOVA YETMEZ. "site mi degil mi" seklinde iki kovali bir siniflama, tanimadigi
// her degeri VARSAYILAN kovaya iter ve o kovanin sayisini sahte sisirir
// ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]). Bu yuzden asagida DORT is kovasinin
// yaninda IKI GORUNUR "bilmiyorum" kovasi vardir; ikisi de site/whatsapp kovalarina
// KATILMAZ ve raporda kendi satiriyla basilir.
export const KOVA_SITE_UCRETLI = "site-ucretli";
export const KOVA_SITE_ORGANIK = "site-organik";
export const KOVA_WHATSAPP = "whatsapp";
/** Site siparisi ama atif YOK ya da atif var/COZULEMEDI. 🔴 Bu kova organige KATLANMAZ:
 *  "atfi olmayan" ile "atfi organik olan" ayri seylerdir; ikisini toplamak raporun
 *  TAMAMINI yalan yapar (organik ROI oldugundan buyuk gorunur). */
export const KOVA_ATIF_YOK = "atif-yok/siniflanamaz";
/** `kanal` kolonu DOLU ama degeri ne 'site' ne 'whatsapp' (ileride eklenecek bir kanal,
 *  ya da bozuk veri). Site'ye de WhatsApp'a da YAZILMAZ — gorunur kalir. */
export const KOVA_KANAL_BILINMIYOR = "kanal-bilinmiyor";
/** `kanal` kolonu YOK / bos. 🔴 "Kolon yok, demek hepsi site" cikarimi YASAKTIR: goc
 *  kosmadan once WhatsApp siparisleri de bu tabloda olabilir ve hepsi 'site' sayilirsa
 *  site ROI'si sessizce sisirilir. Rapor bu kovayi gorunce OLCULEMEDI hukmu verir. */
export const KOVA_KANAL_OLCULEMEDI = "kanal-olculemedi";

/** Rapor/panel gosterim sirasi. Rapor TAMAMINI basar (sayi 0 olsa bile) — basilmayan
 *  kova, var olmayan kovadan ayirt edilemez. */
export const KOVALAR = [
  KOVA_SITE_UCRETLI, KOVA_SITE_ORGANIK, KOVA_WHATSAPP,
  KOVA_ATIF_YOK, KOVA_KANAL_BILINMIYOR, KOVA_KANAL_OLCULEMEDI,
];

export const KOVA_ETIKET = {
  [KOVA_SITE_UCRETLI]: "site · ücretli",
  [KOVA_SITE_ORGANIK]: "site · organik",
  [KOVA_WHATSAPP]: "WhatsApp (Ege)",
  [KOVA_ATIF_YOK]: "kaynak kaydı yok",
  [KOVA_KANAL_BILINMIYOR]: "kanal tanınmıyor",
  [KOVA_KANAL_OLCULEMEDI]: "kanal ölçülemedi (göç koşmadı)",
};

// ---- ATIF beyaz-listesi -------------------------------------------------------
/** Panelde/raporda GORUNEN atif alanlari. POZITIF liste (fail-closed): burada olmayan
 *  hicbir atif alani hicbir yuzeye cikmaz. Yukaridaki gizlilik gerekcesine bak. */
export const GORUNUR_ATIF_ALANLARI = [
  "utm_source", "utm_medium", "utm_campaign", "utm_id", "ref",
];
/** 🔒 ACIKCA BASILMAYANLAR — belge + nobetci capasi. shop/test/panel-atif.mjs bu
 *  adlarin cikti HTML'inde ve rapor ciktisinda GECMEDIGINI ayri ayri olcer. */
export const BASILMAYAN_ATIF_ALANLARI = ["ga_client_id", "fbp", "fbc"];

/** `siparisler.atif` (kompakt JSON metni ya da nesne) -> beyaz-listeli DUZ nesne.
 *  Bozuk/bos JSON -> {} (fail-closed; ham metin HICBIR yuzeye tasinmaz). */
export function atifAlanlari(atifHam) {
  let a = atifHam;
  if (typeof a === "string") {
    try { a = JSON.parse(a); } catch (e) { a = null; }
  }
  if (!a || typeof a !== "object" || Array.isArray(a)) { return {}; }
  const cikti = {};
  for (const alan of GORUNUR_ATIF_ALANLARI) {
    const d = a[alan];
    if (typeof d === "string" && d.trim()) { cikti[alan] = d.trim(); }
  }
  return cikti;
}

/** REF:<SRC>-<GRUP>-<RND4> -> {src, grup}; kalibi tutmayan deger -> null.
 *  🔴 REGEX IKIZI YAZILMADI: kalibin kendisi shop/src/ref.js REF_KALIBI'dir ve
 *  index.js atifTemizle o kalibi GECMEYEN ref'i D1'e HIC yazmaz (fail-closed). Buradaki
 *  is dogrulama degil AYRISTIRMADIR; beklenmedik sekil null doner ve cagiran
 *  "siniflanamaz" kovasina duser (sessizce bir kovaya YAZILMAZ).
 *  RND4 (p[2]) BILEREK DONDURULMEZ: rastgele sonek, ekranda bilgi tasimaz. */
export function refParcala(ref) {
  const s = typeof ref === "string" ? ref : "";
  if (s.indexOf("REF:") !== 0) { return null; }
  const p = s.slice(4).split("-");
  if (p.length !== 3 || !p[0] || !p[1] || !p[2]) { return null; }
  return { src: p[0], grup: p[1] };
}

// REF src sinifi (landing attribution-ref.js kanonigi): GS = Google/paid tik,
// OG = organik oturum (click-id yok). Baska bir src -> siniflanamaz (yutulmaz).
const REF_SRC_UCRETLI = "GS";
const REF_SRC_ORGANIK = "OG";

// utm_medium YEDEK ekseni — REF halkasi kopmus/eski siparisler icin. DAR ve ACIK
// tutulur: listede olmayan medium "organik" SAYILMAZ, siniflanamaz kovasina duser
// (genis bir "kalan her sey organiktir" kolu tam da raporu yalan yapan seydir).
const UCRETLI_MEDIUM = new Set([
  "cpc", "ppc", "paid", "paidsearch", "paid-search", "paid_search",
  "paidsocial", "paid-social", "paid_social", "display", "banner",
  "retargeting", "remarketing",
]);
const ORGANIK_MEDIUM = new Set([
  "organic", "organic-search", "organic_search", "referral", "social", "email", "e-mail",
]);

/**
 * TEK KARAR — bir siparis satirini kovasina yerlestirir.
 *
 * @param kanalHam  `siparisler.kanal` HAM degeri. ⚠️ Cagiran BURAYA 'site' VARSAYILANI
 *                  UYGULAMADAN vermelidir: undefined/'' -> KOVA_KANAL_OLCULEMEDI.
 * @param atifHam   `siparisler.atif` (JSON metni ya da nesne).
 * @return {{kova, sebep, atif, ref_src, ref_grup}} — `sebep` teshis icindir (hangi
 *         eksenden karar cikti); ekranda da basilir ki bos bir kova "neden bos"
 *         sorusuna cevap versin.
 */
export function kanalKovasi(kanalHam, atifHam) {
  const atif = atifAlanlari(atifHam);
  const parca = refParcala(atif.ref);
  const temel = {
    atif: atif,
    ref_src: parca ? parca.src : "",
    ref_grup: parca ? parca.grup : "",
  };
  const kanal = typeof kanalHam === "string" ? kanalHam.trim() : "";
  if (!kanal) {
    return { ...temel, kova: KOVA_KANAL_OLCULEMEDI, sebep: "kanal-kolonu-yok" };
  }
  if (kanal === WA_KANAL) {
    return { ...temel, kova: KOVA_WHATSAPP, sebep: "kanal:" + WA_KANAL };
  }
  if (kanal !== KANAL_SITE) {
    return { ...temel, kova: KOVA_KANAL_BILINMIYOR, sebep: "kanal:" + kanal };
  }
  // --- site kanali: atif ekseni ---
  if (parca && parca.src === REF_SRC_UCRETLI) {
    return { ...temel, kova: KOVA_SITE_UCRETLI, sebep: "ref:" + REF_SRC_UCRETLI };
  }
  if (parca && parca.src === REF_SRC_ORGANIK) {
    return { ...temel, kova: KOVA_SITE_ORGANIK, sebep: "ref:" + REF_SRC_ORGANIK };
  }
  const medium = (atif.utm_medium || "").toLowerCase();
  if (medium && UCRETLI_MEDIUM.has(medium)) {
    return { ...temel, kova: KOVA_SITE_UCRETLI, sebep: "utm_medium:" + medium };
  }
  if (medium && ORGANIK_MEDIUM.has(medium)) {
    return { ...temel, kova: KOVA_SITE_ORGANIK, sebep: "utm_medium:" + medium };
  }
  // Atif tamamen bos mu, yoksa var ama cozulemedi mi — kova AYNI, teshis FARKLI.
  const bos = Object.keys(atif).length === 0;
  return { ...temel, kova: KOVA_ATIF_YOK, sebep: bos ? "atif-bos" : "atif-cozulemedi" };
}

/**
 * PANEL/RAPOR ozeti — `/liste` JSON'una BU nesne konur, panel onu OLDUGU GIBI basar.
 * 🔴 Tarayiciya ikinci bir siniflama gonderilmez: panel karar VERMEZ, karari GOSTERIR
 * (tarayicida yasayan bir kopya, bu dosya degistiginde sessizce eskirdi).
 */
export function kaynakOzeti(kanalHam, atifHam) {
  const k = kanalKovasi(kanalHam, atifHam);
  return {
    kova: k.kova,
    etiket: KOVA_ETIKET[k.kova] || k.kova,
    sebep: k.sebep,
    kanal: typeof kanalHam === "string" ? kanalHam.trim() : "",
    utm_source: k.atif.utm_source || "",
    utm_medium: k.atif.utm_medium || "",
    utm_campaign: k.atif.utm_campaign || "",
    utm_id: k.atif.utm_id || "",
    ref: k.atif.ref || "",
    grup: k.ref_grup,
    src: k.ref_src,
  };
}

// ---- CIRO KAPSAMI (rapor + panel ayni kural) ----------------------------------
/**
 * 🔴 CIROYA GIREN DURUMLAR — 'odendi' VE SONRASI. Karar acikca yazilir ve rapor
 * ciktisinda BEYAN EDILIR (beyansiz bir ciro sayisi, hangi soruyu cevapladigi
 * bilinmeyen bir sayidir).
 *   GIRER  : odendi · uretimde · kargolandi · tamamlandi   (para TAHSIL EDILDI)
 *   GIRMEZ : bekliyor (odeme baslamis, bitmemis) · havale-bekliyor (para gelmedi) ·
 *            incele (dogrulanmadi) · basarisiz · iptal
 * `bekliyor`/`iptal`in ciroya girmesi ciroyu terk edilmis sepetlerle sisirirdi.
 */
export const CIRO_DURUMLARI = new Set(["odendi", "uretimde", "kargolandi", "tamamlandi"]);

/** Bu satir ciroya sayilir mi? (durum ekseni; kanal/atif ile ILGISIZ) */
export function ciroyaGirer(durum) {
  return CIRO_DURUMLARI.has(typeof durum === "string" ? durum.trim() : "");
}

/** Tahsil edilen tutar (kurus) = urun toplami + kargo. shop/src/index.js
 *  `beklenenTahsilat` ile BIREBIR ayni formul (musterinin odedigi para). */
export function tahsilatKurus(satir) {
  const t = Number(satir && satir.tutar_kurus) || 0;
  const k = Number(satir && satir.kargo_kurus) || 0;
  return t + k;
}
