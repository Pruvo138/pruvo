/**
 * KONFIGUR GOLGE MODU — "D1'deki konfigur semasi, Worker bundle'indakiyle AYNI mi?"
 *
 * 🔴 GOLGE = MUSTERI DAVRANISI DEGISMEZ. Fiyat HALA bundle'dan (shop/src/konfigurlar.js)
 * hesaplanir ve tahsilat ondan yapilir. Bu modul D1'den gelen semayi YALNIZCA OLCER; dondugu
 * hicbir deger fiyata, tutara, siparise ya da cevaba KARISMAZ. Amac tek soruyu olculebilir
 * kilmak: "sema D1'e tasinsa BUGUN ayni parayi mi tahsil ederdik?"
 *
 * NEDEN (iki kaynak sorunu): urun eklendiginde katalog D1'e OTOMATIK gider (pre-push hook),
 * ama konfigur semasi Worker bundle'inda yasadigi icin ELLE artefakt uretimi + ELLE deploy
 * gerekir. 30 Tem'de ikisi de atlandi. FAZ 1+2 semayi D1'e tasidi (tools/d1-sync.py
 * konfigur_plan). FAZ 3 (bu dosya) iki kaynagi KIYASLAR; cevirme (FAZ 4) AYRI karardir ve
 * ancak buradaki fark 0 olculdukten sonra yapilir.
 *
 * FAIL-SAFE: bu modulun hicbir yolu ATMAZ (throw). Bozuk/eksik D1 JSON'u bir DURUM'a cevrilir
 * ("d1-bozuk"), istisnaya degil — golge olcumu para yolunu ASLA dusuremez.
 */

import { konfigurHesapla } from "./konfigur.js";

/** Golge durumlari (rapor + log sayaclarinin sabit anahtarlari). */
export const DURUM = {
  YOK: "yok",                   // ne bundle'da ne D1'de konfigur var -> normal urun
  AYNI: "ayni",                 // iki kaynak BIREBIR (hedeflenen hal)
  FARKLI: "farkli",             // ikisi de var ama ICERIK ayrisiyor -> F4'te fiyat degisirdi
  D1_EKSIK: "d1-eksik",         // bundle'da var, D1'de yok -> D1 senkronu kacmis
  BUNDLE_EKSIK: "bundle-eksik", // D1'de var, bundle'da yok -> BUGUNKU acik pencere (deploy bekliyor)
  D1_BOZUK: "d1-bozuk",         // D1 metni JSON olarak cozulemedi
};

/**
 * Iki degeri DERIN kiyaslar; ayrisan ALAN YOLLARINI dondurur (bos dizi = birebir).
 * Sayilar JSON round-trip sonrasi kiyaslandigi icin 1 ile 1.0 AYNIDIR (ikisi de IEEE754 double)
 * — kanonik yazim farki sahte fark uretmez.
 */
export function alanFarklari(a, b, yol = "", cikti = []) {
  if (a === b) { return cikti; }
  const tipA = a === null ? "null" : Array.isArray(a) ? "dizi" : typeof a;
  const tipB = b === null ? "null" : Array.isArray(b) ? "dizi" : typeof b;
  if (tipA !== tipB) { cikti.push(yol || "(kok)"); return cikti; }
  if (tipA === "dizi") {
    if (a.length !== b.length) { cikti.push((yol || "(kok)") + ".length"); return cikti; }
    for (let i = 0; i < a.length; i++) { alanFarklari(a[i], b[i], yol + "[" + i + "]", cikti); }
    return cikti;
  }
  if (tipA === "object") {
    const anahtarlar = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const k of anahtarlar) {
      alanFarklari(a[k], b[k], yol ? yol + "." + k : k, cikti);
    }
    return cikti;
  }
  cikti.push(yol || "(kok)");
  return cikti;
}

/** D1'in konfigur metnini objeye cevirir. Bos -> null; bozuk -> undefined (ATMAZ). */
export function d1Coz(metin) {
  if (typeof metin !== "string" || metin === "") { return null; }
  try {
    const o = JSON.parse(metin);
    return (o && typeof o === "object" && !Array.isArray(o)) ? o : undefined;
  } catch (e) { return undefined; }
}

/**
 * SEMA karsilastirmasi (fiyattan bagimsiz).
 * @returns {{durum: string, farklar: string[], d1Konfigur: object|null}}
 */
export function golgeDurum(bundleKonfigur, d1Metin) {
  const d1 = d1Coz(d1Metin);
  const bVar = Boolean(bundleKonfigur);
  if (d1 === undefined) { return { durum: DURUM.D1_BOZUK, farklar: ["(cozulemedi)"], d1Konfigur: null }; }
  if (!bVar && !d1) { return { durum: DURUM.YOK, farklar: [], d1Konfigur: null }; }
  if (bVar && !d1) { return { durum: DURUM.D1_EKSIK, farklar: [], d1Konfigur: null }; }
  if (!bVar && d1) { return { durum: DURUM.BUNDLE_EKSIK, farklar: [], d1Konfigur: d1 }; }
  const farklar = alanFarklari(bundleKonfigur, d1);
  return { durum: farklar.length ? DURUM.FARKLI : DURUM.AYNI, farklar, d1Konfigur: d1 };
}

/**
 * PARA EKSENI — asil olcum: "bu kalemi D1 semasiyla fiyatlasaydik kac kurus fark ederdi?"
 *
 * bundleKurus = BUGUN tahsil edilen (cagiran zaten hesapladi, buraya BILGI olarak gelir).
 * d1Kurus     = GOLGE hesap; hicbir yere yazilmaz/donmez, yalnizca farki olculur.
 *
 * @returns {{durum, farklar, bundleKurus, d1Kurus, farkKurus}}
 *   farkKurus = d1Kurus - bundleKurus (null = kiyaslanamadi). 0 = iki kaynak ayni parayi uretir.
 */
export function golgeKalem(kalem, secenek, bundleKonfigur, d1Metin, bundleKurus) {
  const s = golgeDurum(bundleKonfigur, d1Metin);
  const sonuc = { durum: s.durum, farklar: s.farklar, bundleKurus: bundleKurus ?? null,
                  d1Kurus: null, farkKurus: null };
  if (!s.d1Konfigur) { return sonuc; }
  const kh = konfigurHesapla(kalem, secenek, s.d1Konfigur);
  if (kh.hata) { sonuc.d1Hata = kh.hata; return sonuc; }
  sonuc.d1Kurus = kh.birimKurus;
  if (typeof bundleKurus === "number") { sonuc.farkKurus = kh.birimKurus - bundleKurus; }
  return sonuc;
}

/**
 * Tek satirlik, PII'siz golge kaydi (Worker log'u / `wrangler tail`).
 * "ayni" ve "yok" hallerinde null doner -> gurultu yok, yalnizca AYRISIM konusur.
 */
export function golgeLogSatiri(id, g) {
  if (!g || g.durum === DURUM.AYNI || g.durum === DURUM.YOK) { return null; }
  return "konfigur-golge " + JSON.stringify({
    id: id, durum: g.durum, fark_kurus: g.farkKurus,
    bundle_kurus: g.bundleKurus, d1_kurus: g.d1Kurus,
    alanlar: (g.farklar || []).slice(0, 8), d1_hata: g.d1Hata || null,
  });
}

/**
 * KATALOG DUZEYI RAPOR (kontrol kipi — /yonet/konfigur-golge bunu kullanir).
 * @param {Map} bundle       KONFIGURLAR (id -> konfigur)
 * @param {Array} d1Satirlar [{id, kategori, konfigur}] — D1'den okunan satirlar
 * @param {object} secenek   SECENEK (fiyat cekirdegi icin)
 * @param {Array} ornekler   [[boyMm, malzeme], ...] fiyat kiyas noktalari
 * @returns {{ozet: object, fark_kurus_toplam: number, kayitlar: Array}}
 */
export function golgeRaporu(bundle, d1Satirlar, secenek, ornekler) {
  const noktalar = ornekler && ornekler.length ? ornekler : [[150, "PLA"], [300, "ASA"]];
  const d1Harita = new Map((d1Satirlar || []).map((r) => [r.id, r]));
  const idler = new Set([...bundle.keys(), ...d1Harita.keys()]);
  const ozet = { ayni: 0, farkli: 0, "d1-eksik": 0, "bundle-eksik": 0, "d1-bozuk": 0, yok: 0 };
  const kayitlar = [];
  let farkToplam = 0;
  for (const id of [...idler].sort()) {
    const bK = bundle.get(id) || null;
    const satir = d1Harita.get(id);
    const s = golgeDurum(bK, satir ? satir.konfigur : "");
    ozet[s.durum] = (ozet[s.durum] || 0) + 1;
    if (s.durum === DURUM.AYNI || s.durum === DURUM.YOK) { continue; }
    const fiyatlar = [];
    for (const [boy, malzeme] of noktalar) {
      const kalem = { id, malzeme, renk: "Siyah", renk_ozel: "", adet: 1,
                      parametreler: { boy_mm: boy } };
      const bH = bK ? konfigurHesapla(kalem, secenek, bK) : { hata: "bundle-yok" };
      const g = golgeKalem(kalem, secenek, bK, satir ? satir.konfigur : "",
                           bH.hata ? undefined : bH.birimKurus);
      if (typeof g.farkKurus === "number") { farkToplam += Math.abs(g.farkKurus); }
      fiyatlar.push({ boy_mm: boy, malzeme,
                      bundle_kurus: bH.hata ? null : bH.birimKurus,
                      d1_kurus: g.d1Kurus, fark_kurus: g.farkKurus });
    }
    kayitlar.push({ id, durum: s.durum, alanlar: s.farklar.slice(0, 20), fiyatlar });
  }
  return { ozet, fark_kurus_toplam: farkToplam, kayitlar };
}

export default golgeKalem;
