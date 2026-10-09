/**
 * PRUVO shop — PANEL YETKI YUZEYININ CIVILI TABANI (TEK KAYNAK).
 *
 * Bu dosya TEST DEGILDIR, iddia KOSMAZ; iki kabul testinin AYNI ekseni olcerken
 * kullandigi sayilari tutar:
 *   · shop/test/uretim-kaynak.mjs  K40/K41
 *   · shop/test/panel-kaynak.mjs   V9d/V9e
 *
 * 🔴 NEDEN AYRI DOSYA (olculmus ariza, 2-3 Eyl 2026): iki test bu sayilari AYRI AYRI
 * bildiriyordu ve yorumlari "ikisi ayni sayiyi olcer" diyordu — yani es olmalari
 * YAZILI KURALDI ama ZORLAYICISI YOKTU. `e35f092d` (tekil urun silme, Okan emri
 * 2 Eyl) 22. yonlendirici kolunu ekledi, panel-kaynak.mjs'in tabanini 21->22
 * tazeledi, uretim-kaynak.mjs'inkini 21'de BIRAKTI. Sonuc: `Nöbet şeridi (SERIT B)`
 * is akisinda IKI ADIM birden kirmizi yandi ve kirmizi CI kuyrugunda birikti
 * ([[ayni-alan-iki-hukum-biri-sessiz]]). Sayi TEK YERDE durursa sapma YAPISAL
 * OLARAK imkansizdir; tazeleyen tek satir tazeler.
 *
 * TABANI DEGISTIRMEK: yeni bir panel ucu BILEREK eklendiginde sayiyi burada artir ve
 * ALTINA tarih + gerekce dus. Sayiyi "testi yesile boyamak icin" artirmak, kapinin
 * OLCTUGU seyi (yetki yuzeyi sessizce genisledi mi?) ortadan kaldirir.
 *
 * TARIHCE:
 *   11  — taban (siparis paneli)
 *   15  — "Urunler" sekmesi 4 uc ekledi (GET /urunler, GET /urunler-kuyruk,
 *         POST /urunler-ustyazim, POST /urunler-ustyazim-sil)
 *   21  — 30 Agu 2026 (T2, Okan emri): gorsel/STL/kaynak link, 6 uc
 *   22  — 2 Eyl 2026 (`e35f092d`, Okan emri): tekil urun silme `/urun-sil`
 *   23  — 6 Eyl 2026 (Okan emri): hata satirini KAPAT `POST /urunler-kuyruk-kapat`
 *         — ayni yonetim anahtarinin arkasinda, SILMEZ: yalniz hal='hata' -> 'kapandi'
 *         damgasi (deger/sebep/ts dokunulmaz). Kurallari shop/test/urunler-panel.mjs
 *         O bolumunde olculur; burada YALNIZ kol sayilir.
 *   26  — 5 Eki 2026 (Okan karari, fotograftan ozel uretim): GET /foto-dosya (3MF/GLB/
 *         onizleme indirme), GET /foto-ozet (tur basina sayim + kredi), POST /foto-fiyat
 *         (fiyat tablosu) — ucu de ayni yonetim anahtarinin ARKASINDA, bot anahtari acamaz.
 *         ⚠️ /foto-dosya'nin Content-Disposition'i shop/src/foto.js'te durur; CD_TABANI
 *         yalniz yonet.js'i saydigi icin DEGISMEDI (sayacin menzili yonet.js'tir).
 *   31  — 6 Eki 2026 (BaBa, panel "Örnek üret" — Okan'in kendi fotografindan odemesiz
 *         vitrin ornegi): POST /foto/ornek-onizleme, GET /foto/ornek-durum, GET
 *         /foto/ornek-gorsel, POST /foto/ornek-uret, GET /foto/ornekler — besi de ayni
 *         yonetim anahtarinin ARKASINDA (anahtarsiz 404), bot anahtari acamaz. Ayrim ve
 *         yetki kurallari shop/test/foto-uretim.mjs O bolumu + OM1..OM6 mutantlarinda
 *         olculur; burada YALNIZ kol sayilir. Yeni indirme akisi YOK: ornek 3MF/GLB mevcut
 *         /foto-dosya ucundan iner -> CD_TABANI DEGISMEDI.
 *   30  — 6 Eki 2026 (Okan karari "Ege ve HocA yok" + "temizle"): WhatsApp botunun
 *         POST siparis kolu yonet.js'ten SILINDI (yuzey DARALDI, genislemedi). O yol
 *         artik her anahtarla 404 + D1'e yazmaz — shop/test/urunler-panel.mjs A6.
 *   32  — 6 Eki 2026 (litofan deterministik kolu, KraL tasarimi): GET /foto/uretec-girdi
 *         (uretecin girdisi = musterinin gri kalinlik haritasi PNG) + POST /foto/uretec-yukle
 *         (bizim uretecin 3MF'i; yalniz 'uretec-bekliyor' satirina, CAS ile 'hazir') — ikisi de
 *         ayni yonetim anahtarinin ARKASINDA (anahtarsiz 404). Yetki/imza/asama kurallari
 *         shop/test/foto-litofan.mjs L6 + M4 (uc kapinin onune alininca L6 KIRMIZI) olcer.
 *         Content-Disposition shop/src/foto.js'te -> CD_TABANI DEGISMEDI.
 *   36  — 8 Eki 2026 (kral/kopru-15; foto fiyat TEK formul + 2D konsept + onizleme olcumu):
 *         -1 POST /foto-fiyat (fiyat tablosu kalkti, `b23f26d3`) · +1 POST /foto-acik (acilis
 *         anahtari, fail-closed) · +3 /foto/ornek-konsept, -konsept-durum, -konsept-gorsel
 *         ("Nasil olsun?" -> 2D konsept, `b74e776e`) · +1 POST /foto/uretim-tik — YALNIZ
 *         onizlemeMi(env) ise (canlida 404; `9b4f6583`). Besi de yonetim anahtari kapisinin
 *         ARKASINDA (anahtarsiz 404). Onizleme makine anahtari (`acc32ce1`) yalniz ONIZLEME=1 +
 *         sabit MAKINE_UCLARI listesinde gecer — canli yuzeyi genisletmez. Yeni indirme akisi
 *         YOK -> CD_TABANI DEGISMEDI.
 *   33  — 9 Eki 2026 (Okan "2D konsept bunu tamamen sil"): -3 /foto/ornek-konsept,
 *         -konsept-durum, -konsept-gorsel SILINDI (yuzey DARALDI). CD_TABANI DEGISMEDI.
 */

/** `altYol === "` yonlendirici kolu sayisi — yetki yuzeyi genisledi mi? */
export const KOL_TABANI = 33;

/** `Content-Disposition` gecisi — yeni indirme/proxy/zip akisi acildi mi? */
export const CD_TABANI = 2;
