/**
 * pruvo-shop — OLCUM BILETI: tarayici Purchase olayinin SUNUCU DOGRULAMASI.
 *
 * NEDEN VAR (olculmus kusur — ArTisT, kampanya plani ADIM 1):
 *   index.html `odemeDonusuIsle()` Purchase'i YALNIZCA URL'ye bakarak atiyordu:
 *       /?siparis=ok&no=<siparis_no>&t=<kurus>   ->  fbq("track","Purchase",{value:t/100})
 *   Uc ayri sahte-satis yolu vardi ve UCU DE tek yonlu sapma uretir (piksel >= gercek):
 *     1) URL UYDURULABILIR: ziyaretci/bot `https://pruvo3d.com/?siparis=ok&no=X&t=900000`
 *        yazinca 9.000 TL'lik Purchase Meta'ya gider. Siparis YOK, para YOK.
 *     2) TUTAR UYDURULABILIR: `value` dogrudan URL'deki `t`'den okunuyordu — gercek tahsilat
 *        degil, ziyaretcinin yazdigi sayi. Ciro ogretimi bozulur.
 *     3) TEKRAR: donus sayfasi geri tusuyla / gecmisten / paylasilan linkle yeniden acilinca
 *        olay TEKRAR atiliyordu. Sunucu tarafi ayni siparisi idempotent kapatir (changes=0 ->
 *        CAPI olayi TEKRARLANMAZ), ama tarayici kolu bu freni TANIMIYORDU.
 *   Olculen sonuc: 30 gunde piksel 9 satis, D1 gercek 5.
 *
 * COZUM — TEK KULLANIMLIK BILET (tarayiciya "kanit" tasitma, sunucuya SOR):
 *   a) `donus()` iyzico retrieve'i dogrular, tutari karsilastirir ve siparisi 'odendi'ye
 *      ATOMIK ve IDEMPOTENT gecirir. YALNIZ o gecis GERCEKTEN olduysa (changes > 0) rastgele
 *      bir bilet uretilir ve AYNI UPDATE icinde durum_gecmisi'ne yazilir ({"pb":"<bilet>"}).
 *      Ayri bir yazma turu EKLENMEZ — ikinci UPDATE yaris penceresi acardi (yonet.js'teki
 *      olcum izi karariyla AYNI desen).
 *   b) Bilet donus URL'sine `&b=` olarak eklenir. Bilet OPAK ve RASTGELEDIR: uydurulamaz.
 *   c) Tarayici olayi ATMADAN ONCE bu ucu cagirir. Bilet burada DOGRULANIR ve YAKILIR (CAS).
 *      Yakma basarisizsa (bilet yok / zaten yanmis / yaris kaybedildi) -> ok:false -> OLAY YOK.
 *
 * BUNUN SONUCU (kapanis kriterinin karsiligi):
 *   - Dogrulanmamis donus  -> bilet YOK        -> olay ATILMAZ.
 *   - Dogrulanmis siparis  -> bilet BIR KEZ yanar -> olay BIR KEZ atilir.
 *   - Ayni siparis 2. cagri -> bilet ZATEN YANMIS -> olay ATILMAZ.
 *   Yani tarayici olayi, sunucunun CAPI olayiyla ayni kapidan gecer; ikisi de event_id =
 *   siparis_no tasir, Meta dedup eder. Piksel sayisi D1 'odendi' sayisini ASAMAZ.
 *
 * 🔒 GIZLILIK (kisisel-veri-test.py CI'da BLOKLAYICIDIR):
 *   Bu ucun cevabi YALNIZ { ok, value, currency } tasir. Ad/telefon/e-posta/adres/token
 *   OKUNMAZ ve DONMEZ. SELECT bile musteri kolonlarini istemez. Hata kollari SEBEP SIZDIRMAZ
 *   (hepsi ayni `{ok:false}`) — siparis numarasi deneyerek "bu siparis var mi / odendi mi"
 *   sorusu cevaplanamasin.
 */

import { kurusTRY } from "./olcum.js";

/** Bilet uzunluk siniri: uydurma/sisirilmis girdi D1'e hic gitmesin. */
export const BILET_ENAZ = 16;
export const BILET_ENCOK = 100;
/** Siparis no uzunluk siniri (siparis-no.js formatindan cok daha genis, yine de sinirli). */
export const SIPARIS_NO_ENCOK = 64;

/**
 * Tek kullanimlik bilet uret. Tahmin edilemez olmak ZORUNDA: bilet, "bu odeme gercekten
 * dogrulandi" iddiasinin TEK kanitidir. crypto.randomUUID Workers'ta ve Node 19+'ta vardir;
 * yoksa getRandomValues'a duser. İkisi de yoksa BOS doner -> bilet URL'ye EKLENMEZ ve
 * tarayici olayi atmaz (FAIL-CLOSED: kanit uretemiyorsak sahte satis saymaktansa hic sayma).
 */
export function biletUret(kripto) {
  const c = kripto || (typeof crypto !== "undefined" ? crypto : null);
  if (!c) { return ""; }
  if (typeof c.randomUUID === "function") { return c.randomUUID().replace(/-/g, ""); }
  if (typeof c.getRandomValues === "function") {
    const b = new Uint8Array(16);
    c.getRandomValues(b);
    return Array.from(b).map((x) => x.toString(16).padStart(2, "0")).join("");
  }
  return "";
}

/** durum_gecmisi JSON'unu diziye cevir (bozuksa bos dizi). */
function gecmisCoz(gecmisJson) {
  let g = [];
  try { g = JSON.parse(gecmisJson) || []; } catch (e) { g = []; }
  return Array.isArray(g) ? g : [];
}

/**
 * Gecmiste `pb === bilet` tasiyan kaydi bul ve YAK: `pb` SILINIR, yerine `pk:1` (piksel
 * olayi bu bilet icin verildi) konur. Kayit BULUNAMAZSA {bulundu:false} doner.
 *
 * `pb`'nin SILINMESI kritiktir: kalsaydi ayni bilet ikinci kez dogrulanir, mukerrer koruma
 * COKERDI. `pk` yalnizca teshis izidir ("bu siparisin tarayici olayi verilmisti").
 *
 * DIKKAT: bos/gecersiz bilet HICBIR zaman eslesmemeli — aksi halde `pb` alani olmayan
 * kayitlar (undefined === undefined) eslesir ve her donus "dogrulanmis" sayilirdi.
 */
export function biletYak(gecmisJson, bilet) {
  if (typeof bilet !== "string" || bilet.length < BILET_ENAZ) {
    return { bulundu: false, yeni: gecmisJson };
  }
  const g = gecmisCoz(gecmisJson);
  const i = g.findIndex((k) => k && typeof k.pb === "string" && k.pb === bilet);
  if (i < 0) { return { bulundu: false, yeni: gecmisJson }; }
  const kayit = { ...g[i] };
  delete kayit.pb;
  kayit.pk = 1;
  const yeniG = g.slice();
  yeniG[i] = kayit;
  return { bulundu: true, yeni: JSON.stringify(yeniG) };
}

/**
 * Tarayici Purchase'i icin SUNUCU HUKMU.
 *
 * @param env  { KATALOG: D1 }
 * @param no   siparis_no (tarayicinin URL'den okudugu)
 * @param bilet donus URL'sindeki `b` parametresi
 * @returns { ok:boolean, sebep:string, value?:number, currency?:string }
 *          `sebep` YALNIZ sunucu logu icindir — HTTP cevabina KONMAZ (bilgi sizmasin).
 *
 * FAIL-CLOSED: her belirsizlik ok:false'tur. "Emin degilsek saymayiz" — yanlis satis saymak,
 * satisi hic saymamaktan pahalidir (reklam butcesi yanlis ogrenir ve veri geri alinamaz).
 */
export async function biletDogrula(env, no, bilet) {
  const s = typeof no === "string" ? no.trim() : "";
  const b = typeof bilet === "string" ? bilet.trim() : "";
  if (!s || s.length > SIPARIS_NO_ENCOK) { return { ok: false, sebep: "siparis-no-gecersiz" }; }
  if (b.length < BILET_ENAZ || b.length > BILET_ENCOK) { return { ok: false, sebep: "bilet-gecersiz" }; }
  if (!env || !env.KATALOG) { return { ok: false, sebep: "d1-yok" }; }

  // Musteri kolonlari BILEREK istenmiyor (gizlilik): olay icin ad/telefon/adres GEREKMEZ.
  const siparis = await env.KATALOG.prepare(
    "SELECT siparis_no, durum, durum_gecmisi, tutar_kurus, kargo_kurus" +
    " FROM siparisler WHERE siparis_no = ?"
  ).bind(s).first();
  if (!siparis) { return { ok: false, sebep: "siparis-yok" }; }

  // Ikinci kemer: bilet yalniz 'odendi' gecisinde uretilir, ama durum yine de dogrulanir.
  // Boylece siparis sonradan 'iade'/'iptal'e cekilirse bekleyen bilet de olu dogar.
  if (siparis.durum !== "odendi") { return { ok: false, sebep: "durum-odendi-degil" }; }

  const eski = siparis.durum_gecmisi;
  const yakma = biletYak(eski, b);
  if (!yakma.bulundu) { return { ok: false, sebep: "bilet-yok-veya-yanmis" }; }

  // CAS (compare-and-swap): durum_gecmisi OKUDUGUMUZ HALDEYSE yaz. Ayni bilet iki es zamanli
  // istekle gelirse (cift sekme / hizli yenileme) YALNIZ BIRI changes>0 alir; digeri kaybeder
  // ve olay ATMAZ. Bu, yonet.js'te olculmus (T24) ayni idiomdur — "SELECT sonra UPDATE"
  // arasindaki yaris penceresini kapatir.
  const g = await env.KATALOG.prepare(
    "UPDATE siparisler SET durum_gecmisi = ? WHERE siparis_no = ? AND durum_gecmisi = ?"
  ).bind(yakma.yeni, s, eski).run();
  if (!g || !g.meta || !(g.meta.changes > 0)) {
    return { ok: false, sebep: "yaris-kaybedildi" };
  }

  // Tutar SUNUCUDAN doner — tarayicidaki `t` parametresinden DEGIL. Tahsilat = urun + kargo
  // (donus() icindeki `beklenenTahsilat` ile AYNI formul; iyzico paidPrice ile zaten
  // kurusuna kadar karsilastirilmis ve uyusmazsa siparis 'odendi' OLMAMISTI).
  const tahsilatKurus = (Number(siparis.tutar_kurus) || 0) + (Number(siparis.kargo_kurus) || 0);
  return { ok: true, sebep: "dogrulandi", value: kurusTRY(tahsilatKurus), currency: "TRY" };
}
