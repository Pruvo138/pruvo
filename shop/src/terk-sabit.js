/**
 * pruvo-shop — TERK SUPURMESI SABITLERI (ayrik modul).
 *
 * NEDEN AYRI: `shop/src/index.js` module-worker GIRIS modulu olarak workerd'ye baglanir;
 * workerd, modulu yuklerken ADLI exportlari (named exports) sirayla potential entrypoint
 * olarak dener ve `function or ExportedHandler` olmayan herhangi bir adli export
 * (ornegin `export const TERK_ESIK_SAAT = 24;`) icin yukaridaki
 * "Incorrect type for map entry ... not of type 'function or ExportedHandler'" hatasini
 * URETIR. Bu sabitler giris modulunde adli export OLARAK DURAMAZ.
 *
 * (workerd 4.131.1'de olculdu — adli export yorumlanmiyor, `default` zaten handler; bu
 * nedenle calisan tek sabit tasima yolu sabitleri ayrik bir `import` kaynagina
 * koymaktir. Bu dosya adli export TASIR — yasak GIRIS modulune ozgudur, ic modullerde
 * adli export serbesttir. index.js onu `import { TERK_ESIK_SAAT, TERK_KAYNAK_DURUM,
 * TERK_SEBEP } from "./terk-sabit.js"` ile ALIR ve RE-EXPORT ETMEZ — boylece giris
 * modulunde hicbir adli export kalmaz, workerd yalniz `default` handler'i gorur.)
 *
 * SABIT LISTESI (degistirildiginde `shop/test/terk-supurme.mjs`'in 6) TEK SABIT blogu
 * otomatik olarak yeni degerle eslesir; iddia SAYISI degismez):
 *   - TERK_ESIK_SAAT    : saat cinsinden esik (24)
 *   - TERK_KAYNAK_DURUM : supurme SELECT'inin hedef durumu ("bekliyor")
 *   - TERK_SEBEP        : gecmis'e dusen makine-okunur sebep kodu ("terk")
 *
 * TERK_TUR_TAVANI burada YOKTUR — module disariya ACILMAZ, index.js'de oyle kalir.
 */

/**
 * NEDEN 24 SAAT: iyzico'nun hosted odeme sayfasi bundan cok daha kisa surede olur; 24 saat
 * "musteri gercekten odedi ama callback dusmedi" ihtimaline comert bir pay birakir. Esigi
 * KISALTMAK, odemesi tamamlanmis ama callback'i gecikmis bir satiri erken degerlendirme
 * riskini buyutur — ve o satir zaten `retrieve` ile DOGRULANDIGI icin iptal degil 'odendi'
 * olur; yine de sabiti buyuk tutmak hatanin maliyetini dusurur.
 */
export const TERK_ESIK_SAAT = 24;

/**
 * 🔴 SUPURMENIN DOKUNABILECEGI TEK DURUM. Beyaz liste tektir ve TEK YERDE yazilidir:
 * asagidaki SELECT bunu bind eder, iki UPDATE'in CAS kosulu da BUNU bind eder.
 *   - 'havale-bekliyor' GERCEK SIPARISTIR (musteri banka havalesi gonderecek) — ne kadar
 *     eski olursa olsun DOKUNULMAZ. Adinin 'bekliyor' ile bitmesi bir tuzaktir: esitlik
 *     testi kullanilir, alt-dize/LIKE ASLA.
 *   - 'odendi' ve sonrasi (uretimde/kargolandi/tamamlandi), 'iptal', 'incele', 'basarisiz'
 *     de kapsam DISIDIR.
 */
export const TERK_KAYNAK_DURUM = "bekliyor";

/** `durum_gecmisi` kaydina dusen MAKINE-OKUNUR sebep (yonet.js gecmiseEkle -> {"s":"terk"}). */
export const TERK_SEBEP = "terk";
