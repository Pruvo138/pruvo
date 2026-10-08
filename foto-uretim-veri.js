/* PRUVO — "fotoğrafından özel üretim" bölümünün TEK KAYNAK verisi.
 *
 * Bu dosyayı İKİ taraf okur, ikinci kopya YOKTUR:
 *   - ana sayfa bölümü (/foto-uretim.js) örnekleri, türleri ve onay metnini buradan çizer;
 *   - sipariş sunucusu (shop worker) aynı dosyayı import eder: bir türün sipariş/önizleme
 *     alabilmesi için burada en az BİR sayılan örneği olmalı ve onay metni onaylı olmalı.
 *
 * DÜRÜST BEKLENTİ KURALI (Okan, 5 Eki 2026: "müşteri abartılı hayallere kapılmasın"):
 *   - `ornekler` yalnız GERÇEK işlerdir. Her kaydın KANITI açıkça yazılır ve müşteriye
 *     kanıtıyla birlikte gösterilir (render "gerçek fotoğraf" diye SUNULMAZ).
 *   - 5 Eki kuralı: "render ya da üretilmiş baskı görseli bu listeye GİRMEZ". 7 Eki 2026'da
 *     PLAKET için Okan kararıyla değişti ("bu dosya ok · baskı yapmayacağım böyle tamam":
 *     ilk örnek plaketin üretim dosyası hatasız dilimlendi, fiziksel baskı istenmedi) →
 *     plakette `kanit: "render"` kaydı da sayılır; bölüm onu "önizleme/render" etiketiyle ve
 *     abartı cümlesiyle gösterir. Diğer türlerde kural AYNEN durur (yalnız basılmış ürün).
 *   - Sayılan örneği olmayan tür AÇILMAZ (bölümde sipariş formu o tür için çıkmaz, sunucu da
 *     o türe önizleme üretmez). Görseller R2 medya kovasında durur; buraya yalnız adres yazılır.
 *   - Render kaydında müşterinin / Okan'ın ÖZGÜN fotoğrafı YAYINLANMAZ: `foto` boş ya da yok
 *     olabilir (örnek, özgün fotoğraf yayına çıkmadan önizleme + render ile gösterilir).
 *
 * Örnek kaydı: { tur, kanit, olcu_mm, foto, onizleme, baski, render, not }
 *   tur      : turler[].kod
 *   kanit    : "baski"  = basılmış ürünün gerçek fotoğrafı (5 Eki anlamı; alan yoksa bu sayılır)
 *              "render" = önizleme + üretim dosyasının render'ı (Okan kararı 7 Eki; yalnız
 *                         `ornek_kanit_izni` "render" içeren türde sayılır)
 *              başka değer -> hiçbir türde SAYILMAZ (fail-closed)
 *   foto     : müşteri fotoğrafı (izinli/kendi fotoğrafımız) — https://media.pruvo3d.com/...
 *              (baski kanıtında ŞART; render kanıtında boş olabilir)
 *   onizleme : o fotoğraftan üretilen önizleme görseli (her kanıtta ŞART)
 *   baski    : aynı işin BASILMIŞ hâlinin gerçek fotoğrafı (baski kanıtında ŞART)
 *   render   : üretim dosyasının (3MF, ayağıyla) render görseli (render kanıtında ŞART)
 *   not      : kısa açıklama (ör. "40 mm, 4 renk")
 */
(function (kok) {
  "use strict";
  var VERI = {
    surum: 1,

    // ONAY METNİ — OKAN KAPISI: metin onaylanmadan `onay_onayli` true YAPILMAZ ve bölüm
    // önizleme/sipariş almaz. Metin değişirse `onay_surum` da değişir: sunucu, müşterinin
    // gördüğü sürümle buradaki sürüm aynı değilse isteği reddeder (eski sayfadan gelen onay
    // yeni metne sayılmaz).
    // Metin onayı 6 Eki 2026 (taslak-1). 7 Eki 2026 20:5x kararı: iki onay cümlesi aydınlatma
    // metnine, tek onay kutusu (taslak-2; metin bununla birebir, değişirse sürüm de değişir).
    onay_onayli: true,
    onay_surum: "2026-10-07-taslak-2",
    onay: {
      // TEK ONAY KUTUSU: müşteri aşağıdaki aydınlatma metnini (gördüğü maddelerin tamamı, hak
      // beyanı ve aktarım rızası cümleleri dahil) tek kutuyla onaylar; ayrı onay metni YOK.
      // Her madde { kol, metin }: kol "M" = yalniz saglayici (M) kolunda gosterilir (aktarim/
      // saglayici cumleleri); "" = her kolda. METIN DEGISMEZ, yalniz gosterim kosulu (onay_surum ayni).
      aydinlatma: [
        { kol: "M", metin: "Fotoğrafını yüklediğinde fotoğraf, önizleme görselinin ve üretim dosyasının hazırlanması " +
            "için yurt dışında bulunan bir hizmet sağlayıcıya aktarılır. Bu aktarım için açık rızan " +
            "gerekir; rıza vermezsen bu hizmeti kullanamazsın, sitenin geri kalanı etkilenmez." },
        { kol: "M", metin: "Fotoğrafın PRUVO'da saklanmaz. Hizmet sağlayıcı yüklenen fotoğrafı ve ondan üretilen " +
            "dosyaları en geç 3 gün içinde siler." },
        { kol: "", metin: "Önizleme görseli sipariş vermezsen en geç 3 gün içinde silinir; sipariş verirsen üretim " +
            "ve teslim tamamlanana kadar saklanır." },
        { kol: "", metin: "Başkasına ait fotoğraf, marka, logo ya da telifli görsel yükleme; yüklenen görselden " +
            "doğan sorumluluk yükleyene aittir." },
        { kol: "M", metin: "Önizleme, fotoğrafının stilize bir yorumudur. Ürün bu önizlemenin en çok 4 renkli " +
            "kabartma yorumu olarak üretilir; birebir aynısı değildir, küçük yazı ve ince " +
            "ayrıntılar sadeleşir." },
        { kol: "", metin: "Yüklediğim fotoğrafın bana ait olduğunu ya da kullanma hakkım olduğunu beyan ederim." },
        { kol: "M", metin: "Fotoğrafımın önizleme ve üretim dosyasının hazırlanması için yurt dışındaki hizmet sağlayıcıya aktarılmasına açık rıza veriyorum." },
        { kol: "", metin: "Kişisel verilerinle ilgili haklar ve başvuru yolu için Gizlilik Politikası sayfasına bakabilirsin." }
      ]
    },

    // TÜRLER — açılışta TEK tür: kabartma PLAKET (Okan, 5 Eki 21:4x: "plaket yapalım";
    // yalnız plastik üretiyoruz — metal halka/mıknatıs gerektiren tür SUNULMAZ). Ölçü = uzun
    // kenar (mm). Ayak ayrı parça, plaketle birlikte basılıp gönderilir. Figür ikinci dilimdir.
    // Tek tür varken bölümde tür seçimi adımı GÖRÜNMEZ (fotoğraf → ölçü → önizleme → ödeme).
    // FİYAT = TEK FORMÜL (Okan 7 Eki 15:4x): fiyat_kurus = en uzun boyut (mm) × 1000 (= cm × 100 TL),
    // TABAN 600 TL (Okan 8 Eki: fiyat = max(600 TL, mm × 10 TL), tür kaydında fiyat.taban_tl).
    // kategori farkı YOK, fiyat TABLOSU YOK. Formül YALNIZ aşağıdaki VERI.fiyatKurus'ta; bölüm, sunucu
    // ve araçlar onu çağırır. Ölçü = nesnenin sınır kutusunun EN UZUN boyutu (x/y/z hangisi büyükse,
    // ayak/çerçeve dahil). Türün AÇIK/KAPALI hali fiyatta DEĞİL: D1 `foto_acik` anahtarı (varsayılan KAPALI).
    //
    // KATEGORİ KAYDI (6 Eki 2026) — her türün akışı bu alanlardan okunur, kodda ikinci liste YOK:
    // ŞEMA = tools/foto-uretec-sozlesmesi.md §6 (KATEGORİ MOTORU, 7 Eki 2026: kategori eklemek =
    // üreteç + bu satır; bölüm, sunucu, fiyat üreteci ve üreteç köprüsü YALNIZ bu satırı okur).
    //   girdi          : [GIRDI_TURLERI anahtarı...] — "foto-1" tek fotoğraf, "foto-1-3" 1–3 fotoğraf,
    //                    "metin", "url", "svg", "form"; "ses"/"konum"/"tarih" şemada ama YAKINDA
    //   motor          : "M" = önizleme+üretim dış hizmetle (kredi harcar; kol "saglayici");
    //                    "D" / "R" = deterministik / ölçüden üretim — önizleme tarayıcıda ya da
    //                    üreteçte, üretim dosyasını bizim üretecimiz çıkarır (kol "deterministik")
    //   uretec         : üreteç komut kimliği (D/R'de DOLU, M'de "")
    //   form           : parametre şeması { anahtar: {tip:"sayi",min,max,adim,birim} |
    //                    {tip:"secim",secenekler:[..]} | {tip:"metin",max} | {tip:"url"} |
    //                    {tip:"bool",etiket,varsayilan} | {tip:"ses"|"konum"|"tarih"} }; {} = parametre yok
    //                    TeKiN köprü türlerinin (kopru_kayitlari.json) satırları ELLE YAZILMAZ: TÜRETİLEN
    //                    alanlar (girdi, uretec, olcu_mm, renk_bolgeleri, malzemeler, form, fiyat.adim_mm)
    //                    tools/kopru-manifest-uret.py --yaz ile üretilir, --denetle sapmayı KIRMIZI yakar;
    //                    sözlük (olcu->form, tam->adim 1, sayi->adim 0.01, renk->bölge, kosul aynen) orada.
    //                    kosul: [{alan, degerler}] — alan YALNIZ her koşul sağlanınca vardır (VERI.alanAktif)
    //   fiyat          : { formul: "mm_x_10tl", adim_mm, taban_tl, ek_renk_tl, renk_tavani } — formül adı
    //                    VERI.FIYAT_FORMULLERI'nde olmalı (bilinmeyen formül -> fiyat yok, tür sunulmaz); adim_mm =
    //                    sürgü adımı; taban_tl = en düşük fiyat (Okan 8 Eki: 600), yoksa fiyat yok, tür sunulmaz;
    //                    ek_renk_tl = ilk renkten sonraki HER renk (Okan 8 Eki 13:3x: "ilk renk ücretsiz, her + renk
    //                    için +100 TL"); renk_tavani = 1–4 (AMS 4 yuva) — ikisi de yoksa/bozuksa fiyat yok, tür sunulmaz
    //   renk_secimi    : "palet" = müşteri VERI.PLA_RENKLERI'nden 1..renk_tavani renk seçer (Okan 8 Eki 14:2x:
    //                    plaket/figür/büst "Müşteri 1–4 renk seçsin"); alan yoksa renk sayısı = renk_bolgeleri'nde
    //                    seçilen FARKLI renk sayısı (bölge yoksa 1)
    //   olcu_mm        : {en_az, en_cok} — en uzun boyut (mm); bu aralık dışı ölçü RED
    //   olcu_ekseni    : "sabit" (sürgü = hedef ölçü) | "turetilmis" (köprü kaydında belirleyen parametre YOK:
    //                    sürgü YOK, ölçü form parametrelerinden doğar; fiyat = önizlemede ÖLÇÜLEN uzun kenar ×
    //                    formül — köprü ölçüyü D1 foto_isler.olcu_mm'ye yazar, sunucu ORADAN hesaplar; alan
    //                    yoksa "sabit"). TeKiN köprü türlerinde kopru-manifest-uret.py ÜRETİR.
    //   renk_bolgeleri : müşterinin renk seçtiği bölgeler; [] = seçim yok (plaket: önizlemenin 4 renkli yorumu)
    //   malzemeler     : bölge -> izinli filament listesi; {} = satır "PLA" (plaket)
    //   ornek_kanit_izni: türü AÇAN örnek kanıtları; listede olmayan kanıt o türde SAYILMAZ
    //                    (alan yoksa/boşsa hiçbir örnek sayılmaz — fail-closed)
    //   durustluk      : bölümün üst dürüstlük kutusu (tür bazlı, ZORUNLU; seçili türün metni basılır)
    //   ornek_notu     : render örneğinin altındaki dürüstlük cümlesi (tür bazlı; mimar kararı 7 Eki,
    //                    AYNEN). Boşsa bölüm o türün render örneğini ÇİZMEZ; yeni tür doldurmak ZORUNDA.
    // Litofan, gerçek örneği ve açılış anahtarı olmadıkça AÇILMAZ (fail-closed, plaketle aynı kural).
    turler: [
      {
        kod: "plaket",
        ad: "Kabartma plaket",
        aciklama: "Fotoğrafındaki konunun kabartmalı plaketi; ayağıyla masada durur.",
        girdi: ["foto-1"],
        motor: "M",
        uretec: "",
        // Okan 6 Eki 2026: "min 60 max 300".
        olcu_mm: { en_az: 10, en_cok: 300 },
        renk_bolgeleri: [],
        renk_secimi: "palet",
        malzemeler: {},
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        // Okan kararı 7 Eki 2026: plaket gerçek baskı beklemeden önizleme + render ile açılır.
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Önizleme, fotoğrafının stilize bir yorumudur. Ürün en çok 4 renkle kabartma olarak üretilir — önizlemenin 4 renkli yorumu; birebir aynısı değildir, küçük yazı ve ince ayrıntılar sadeleşir.",
        ornek_notu: "Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun kabartmalı hâlidir, birebir aynısı değildir."
      },
      // FIGÜR — sağlayıcı kolunda İKİNCİ tür (24 kategori programı, kategori listesi #8; plaketle aynı
      // motor/zincir; 1–3 fotoğraf). Örnek görseli henüz yoksa AÇILMAZ (fail-closed: VERI.ornekSayisi 0
      // -> tür sunulmaz). Fiyat tüm türlerle aynı formül (mm × 10 TL); yeni fiyat kararı değildir.
      {
        kod: "figur",
        ad: "Figür",
        aciklama: "Fotoğrafından üretilen, en çok 4 renkle sadeleştirilmiş üç boyutlu figür; stilize bir yorum.",
        // Girdi 1–3 fotoğraf: VERI.GIRDI_TURLERI["foto-1-3"].en_cok = 3; ikincisi/üçüncüsü isteğe bağlı
        // (sunucu bu girdi tipini foto-1 ile aynı doğrulamadan geçirir; foto-uretim-veri.js GIRDI_TURLERI).
        girdi: ["foto-1-3"],
        motor: "M",
        uretec: "",
        // 60–200 mm (figür en uzun boyutu; plaketin 300 üst sınırı figürde destek/süre yüzünden dar tutuldu).
        olcu_mm: { en_az: 10, en_cok: 200 },
        renk_bolgeleri: [],
        renk_secimi: "palet",
        malzemeler: {},
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        // Plaketle AYNI izin (render gerçek baskı olmadan açılır; Okan 7 Eki kararı).
        ornek_kanit_izni: ["baski", "render"],
        // Dürüstlük: figür metni — stilize yorum, en çok 4 renk, birebir değil, insan yüzünde benzerlik zayıf.
        durustluk: "Önizleme, fotoğrafının stilize bir yorumudur. Ürün bu önizlemenin en çok 4 renkli, sadeleştirilmiş figür yorumu olarak üretilir; birebir aynısı değildir, küçük ayrıntılar sadeleşir, insan yüzünde benzerlik zayıf olabilir.",
        ornek_notu: "Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun sadeleştirilmiş hâlidir, birebir aynısı değildir."
      },
      {
        kod: "litofan",
        ad: "Işıklı fotoğraf paneli (litofan)",
        aciklama: "Fotoğrafın ince bir panele kalınlık farkıyla işlenir; arkadan ışık gelince görünür. Ayağıyla masada durur.",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "litofan_uret",
        olcu_mm: { en_az: 10, en_cok: 200 },
        renk_bolgeleri: [
          { kod: "panel", ad: "Işık geçen panel", renkler: ["Beyaz"] },
          { kod: "ayak", ad: "Ayak", renkler: ["Beyaz", "Siyah", "Gri"] }
        ],
        // ABS YOK: litofan Dekorasyon sınıfıdır (secenekler.js FILAMENT_KATEGORI_HARIC).
        malzemeler: { panel: ["PLA", "PETG"], ayak: ["PLA", "PETG", "ASA"] },
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        // Okan kararı 7 Eki 2026 (24 kategori 1 hafta, G1 "motor + litofan canlı"): litofan da
        // render örneğiyle açılır (sentetik görselden üretilen 3MF'in arkadan ışıklı render'ı).
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Litofan tek renkli ince bir paneldir; görüntü arkadan ışık geldiğinde belirir. İnce ayrıntılar ve küçük yazılar sadeleşir.",
        ornek_notu: "Üretim dosyasının arkadan ışıkla görüntüsüdür; basılmış panel ışık geldiğinde bu görüntüyü verir, birebir aynısı değildir."
      },
      // G2 (7 Eki 2026, mimar kararı) — 6 D türü; üreteçler pruvo-jenerator (G1-SEMA/G2-SEMA).
      // Tarayıcı önizleyicisi YOK -> sipariş öncesi önizlemeyi üreteç koşucusu çıkarır. Renk adı ->
      // filament hex'i RENK_HEX'ten (tek tablo). Malzeme TÜM ürün için tek seçimdir (ilk bölgenin
      // anahtarıyla): yığılı gövdelerde karışık malzeme yapışmaz. Örneği olmadıkça tür AÇILMAZ.
      {
        kod: "isimlik",
        ad: "İsimlik / kapı tabelası",
        aciklama: "Yazdığın ad ya da yazı plakanın üzerinde kabartma olarak üretilir; ölçüsünü sen seçersin.",
        girdi: ["form"],
        motor: "D",
        uretec: "isimlik_uret",
        olcu_mm: { en_az: 10, en_cok: 250 },
        renk_bolgeleri: [
          { kod: "plaka", ad: "Plaka", renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"] },
          { kod: "yazi", ad: "Yazı", renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"] }
        ],
        malzemeler: { plaka: ["PLA", "PETG", "ASA"] },
        form: {
          satirlar: { tip: "metin", etiket: "Yazı (1–3 satır)", max: 122, satir_en_cok: 3, satir_max: 40 },
          kisa_kenar_mm: { tip: "sayi", etiket: "Kısa kenar", min: 20, max: 250, adim: 1, birim: "mm" },
          yazi_tipi: { tip: "secim", etiket: "Yazı tipi", secenekler: ["Düz", "Tırnaklı"] },
          plaka_sekli: { tip: "secim", etiket: "Plaka şekli", secenekler: ["Dikdörtgen", "Yuvarlak köşe", "Oval"] },
          montaj_delikleri: { tip: "secim", etiket: "Montaj delikleri", secenekler: ["Yok", "Var"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Yazı plakanın üzerinde kabartmadır. Uzun metin küçülür; en küçük harf 6 mm'dir, sığmayan metin için sipariş alınmaz.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; isimlik bu yazı ve ölçüyle üretilir, renk tonu filamente göre biraz değişebilir."
      },
      {
        kod: "qr",
        ad: "QR kodlu plaka",
        aciklama: "Verdiğin bağlantı ya da metin, plakanın üzerinde kabartma QR kod olarak üretilir.",
        girdi: ["form"],
        motor: "D",
        uretec: "qr_plaket_uret",
        olcu_mm: { en_az: 10, en_cok: 150 },
        renk_bolgeleri: [
          { kod: "plaka", ad: "Plaka", renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"] },
          { kod: "kod", ad: "Kod", renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"] }
        ],
        malzemeler: { plaka: ["PLA", "PETG", "ASA"] },
        form: {
          metin: { tip: "metin", etiket: "Bağlantı ya da metin", max: 150, bayt_max: 150 },
          alt_yazi: { tip: "metin", etiket: "Alt yazı (isteğe bağlı)", max: 40, zorunlu: false },
          cerceve: { tip: "secim", etiket: "Çerçeve", secenekler: ["Yok", "Var"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Kodu göndermeden önce telefonla okutarak kontrol ederiz. Bağlantının çalışması verdiğin adrese bağlıdır.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; plakadaki kod bu düzende üretilir."
      },
      {
        kod: "logo",
        ad: "Logodan kabartma",
        aciklama: "Yüklediğin SVG çiziminin dolu alanları kabartma olarak üretilir.",
        girdi: ["svg"],
        motor: "D",
        uretec: "svg_ekstruzyon_uret",
        olcu_mm: { en_az: 10, en_cok: 200 },
        renk_bolgeleri: [
          { kod: "taban", ad: "Taban", renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"] },
          { kod: "logo", ad: "Logo", renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"] }
        ],
        malzemeler: { taban: ["PLA", "PETG"] },
        form: {
          taban: { tip: "secim", etiket: "Taban plakası", secenekler: ["Var", "Yok"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Yalnız düz renkli alanlar üretilir; gölge ve renk geçişi çıkmaz. 0,8 mm'den ince çizgiler siparişi durdurur.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; logonun dolu alanları kabartma olarak üretilir."
      },
      {
        kod: "muhur",
        ad: "Logo mühür / damga",
        aciklama: "Yüklediğin siyah-beyaz görselden saplı, kabartma yüzlü bir damga üretilir.",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "muhur_uret",
        olcu_mm: { en_az: 10, en_cok: 100 },
        renk_bolgeleri: [
          { kod: "govde", ad: "Gövde", renkler: ["Mavi", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Gri", "Beyaz", "Sarı", "Ahşap"] },
          { kod: "sap", ad: "Sap", renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"] }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          sap: { tip: "secim", etiket: "Sap", secenekler: ["Silindir", "Topuz"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Plastik gövdeli bir damgadır; resmî kurum mührü yerine geçmez. 0,6 mm'den ince çizgiler kalınlaştırılır.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; damga yüzü ayna görüntüsüdür, kâğıda bastığında logonun kendisi çıkar."
      },
      {
        kod: "sablon",
        ad: "Silüet şablon",
        aciklama: "Yüklediğin görselin silüeti ince bir plakaya delik ya da dolu biçim olarak işlenir.",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "siluet_sablon_uret",
        olcu_mm: { en_az: 10, en_cok: 250 },
        renk_bolgeleri: [
          { kod: "sablon", ad: "Şablon", renkler: ["Gri", "Beyaz", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Sarı", "Ahşap"] }
        ],
        malzemeler: { sablon: ["PLA", "PETG"] },
        form: {
          mod: { tip: "secim", etiket: "Şablon türü", secenekler: ["Delikli", "Dolu silüet"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Şablon 1,2–2 mm kalınlığında bir plakadır; içteki adalar ince köprülerle tutturulur ve bu köprüler boyamada iz bırakır.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; açık alanlar delik, koyu alanlar plakadır."
      },
      {
        kod: "yapboz",
        ad: "Fotoğraftan kabartma yapboz",
        aciklama: "Fotoğrafının açık-koyu tonları kabartmaya çevrilir ve geçmeli yapboz parçalarına bölünür.",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "yapboz_uret",
        olcu_mm: { en_az: 10, en_cok: 190 },
        renk_bolgeleri: [
          { kod: "yapboz", ad: "Yapboz", renkler: ["Ahşap", "Beyaz", "Gri", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"] }
        ],
        malzemeler: { yapboz: ["PLA", "PETG"] },
        form: {
          parca: { tip: "secim", etiket: "Parça sayısı", secenekler: ["12", "20", "30"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Yapboz tek renkli kabartmadır; renkli baskı değildir. Parçalar elle takılır; çocuk oyuncağı olarak belgelendirilmemiştir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; fotoğrafın açık-koyu tonları kabartma yüksekliğine çevrilir."
      },
      {
        kod: "kutu",
        ad: "Düzenleyici kutu",
        aciklama: "Düzenleyici kutu — ölçüye özel üretim.",
        girdi: ["form"],
        motor: "D",
        uretec: "ozel_uret:kutu",
        olcu_mm: { en_az: 40, en_cok: 300 },
        renk_bolgeleri: [],
        malzemeler: { govde: ["PLA", "PETG", "ASA"] },
        form: {
          en_mm: {
            tip: "sayi",
            etiket: "En (dış)",
            min: 30,
            max: 300,
            adim: 0.01,
            varsayilan: 100,
            birim: "mm",
            ornek: 100
          },
          boy_mm: {
            tip: "sayi",
            etiket: "Boy (dış)",
            min: 30,
            max: 300,
            adim: 0.01,
            varsayilan: 60,
            birim: "mm",
            ornek: 60
          },
          yukseklik_mm: {
            tip: "sayi",
            etiket: "Yükseklik (dış)",
            min: 15,
            max: 200,
            adim: 0.01,
            varsayilan: 40,
            birim: "mm",
            ornek: 40
          },
          bolme_x: {
            tip: "sayi",
            etiket: "Bölme sayısı (en yönü)",
            min: 1,
            max: 8,
            adim: 1,
            varsayilan: 2,
            birim: "adet",
            ornek: 2
          },
          bolme_y: {
            tip: "sayi",
            etiket: "Bölme sayısı (boy yönü)",
            min: 1,
            max: 8,
            adim: 1,
            varsayilan: 2,
            birim: "adet",
            ornek: 2
          },
          duvar_mm: {
            tip: "sayi",
            etiket: "Duvar kalınlığı",
            min: 1.2,
            max: 4,
            adim: 0.01,
            varsayilan: 1.6,
            birim: "mm",
            ornek: 1.6
          },
          taban_mm: {
            tip: "sayi",
            etiket: "Taban kalınlığı",
            min: 1.2,
            max: 5,
            adim: 0.01,
            varsayilan: 1.6,
            birim: "mm",
            ornek: 1.6
          },
          kose_yaricap_mm: {
            tip: "sayi",
            etiket: "Köşe yarıçapı",
            min: 0,
            max: 30,
            adim: 0.01,
            varsayilan: 3,
            birim: "mm",
            ornek: 3
          },
          kapak: {
            tip: "bool",
            etiket: "Oturaklı kapak (ayrı gövde, boşluk 0,25 mm)",
            varsayilan: false,
            ornek: true
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 1 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; düzenleyici kutu bu parametrelerle üretilir.",
        olcu_ekseni: "turetilmis"
      },
      {
        kod: "adaptor",
        ad: "Adaptör / burç / pul",
        aciklama: "Adaptör / burç / pul — ölçüye özel üretim.",
        girdi: ["form"],
        motor: "D",
        uretec: "ozel_uret:adaptor",
        olcu_mm: { en_az: 6, en_cok: 150 },
        renk_bolgeleri: [],
        malzemeler: { govde: ["PLA", "PETG", "ASA"] },
        form: {
          mod: {
            tip: "secim",
            etiket: "Parça türü",
            secenekler: ["pul", "burc", "adaptor"],
            varsayilan: "burc",
            ornek: "burc"
          },
          ic_cap_mm: {
            tip: "sayi",
            etiket: "İç çap (delik)",
            min: 2,
            max: 140,
            adim: 0.01,
            varsayilan: 10,
            birim: "mm",
            ornek: 10
          },
          dis_cap_mm: {
            tip: "sayi",
            etiket: "Dış çap (alt kademe)",
            min: 6,
            max: 150,
            adim: 0.01,
            varsayilan: 20,
            birim: "mm",
            ornek: 20
          },
          yukseklik_mm: {
            tip: "sayi",
            etiket: "Yükseklik (toplam)",
            min: 0.8,
            max: 150,
            adim: 0.01,
            varsayilan: 15,
            birim: "mm",
            ornek: 15
          },
          kademe_cap_mm: {
            tip: "sayi",
            etiket: "Üst kademe dış çapı",
            min: 6,
            max: 150,
            adim: 0.01,
            varsayilan: 14,
            birim: "mm",
            kosul: [{ alan: "mod", degerler: ["adaptor"] }]
          },
          kademe_yukseklik_mm: {
            tip: "sayi",
            etiket: "Üst kademe yüksekliği",
            min: 2,
            max: 148,
            adim: 0.01,
            varsayilan: 8,
            birim: "mm",
            kosul: [{ alan: "mod", degerler: ["adaptor"] }]
          },
          ic_cap2_mm: {
            tip: "sayi",
            etiket: "Üst kademe iç çapı (0 = aynı delik)",
            min: 0,
            max: 140,
            adim: 0.01,
            varsayilan: 0,
            birim: "mm",
            kosul: [{ alan: "mod", degerler: ["adaptor"] }]
          },
          flans: {
            tip: "bool",
            etiket: "Flanş (alt)",
            varsayilan: false,
            kosul: [{ alan: "mod", degerler: ["burc", "adaptor"] }]
          },
          flans_cap_mm: {
            tip: "sayi",
            etiket: "Flanş çapı",
            min: 8,
            max: 150,
            adim: 0.01,
            varsayilan: 30,
            birim: "mm",
            kosul: [
              { alan: "mod", degerler: ["burc", "adaptor"] },
              { alan: "flans", degerler: [true] }
            ]
          },
          flans_kalinlik_mm: {
            tip: "sayi",
            etiket: "Flanş kalınlığı",
            min: 1.2,
            max: 10,
            adim: 0.01,
            varsayilan: 2,
            birim: "mm",
            kosul: [
              { alan: "mod", degerler: ["burc", "adaptor"] },
              { alan: "flans", degerler: [true] }
            ]
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 1 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; adaptör / burç / pul bu parametrelerle üretilir.",
        olcu_ekseni: "turetilmis"
      },
      {
        kod: "disli",
        ad: "Dişli / kasnak",
        aciklama: "Dişli / kasnak — ölçüye özel üretim.",
        girdi: ["form"],
        motor: "D",
        uretec: "ozel_uret:disli",
        olcu_mm: { en_az: 8, en_cok: 200 },
        renk_bolgeleri: [],
        malzemeler: { govde: ["PLA", "PETG", "ASA"] },
        form: {
          tip: {
            tip: "secim",
            etiket: "Parça türü",
            secenekler: ["duz_disli", "gt2_kasnak", "v_kasnak"],
            varsayilan: "duz_disli",
            ornek: "duz_disli"
          },
          mil_capi_mm: {
            tip: "sayi",
            etiket: "Mil deliği çapı",
            min: 2,
            max: 40,
            adim: 0.01,
            varsayilan: 5,
            birim: "mm",
            ornek: 5
          },
          mil_tipi: {
            tip: "secim",
            etiket: "Mil deliği tipi",
            secenekler: ["yuvarlak", "d_mil", "kama"],
            varsayilan: "yuvarlak",
            ornek: "yuvarlak"
          },
          duz_kesim_mm: {
            tip: "sayi",
            etiket: "D-mil düz kesim derinliği",
            min: 0.3,
            max: 3,
            adim: 0.01,
            varsayilan: 0.5,
            birim: "mm",
            kosul: [{ alan: "mil_tipi", degerler: ["d_mil"] }]
          },
          modul_mm: {
            tip: "sayi",
            etiket: "Modül",
            min: 0.5,
            max: 5,
            adim: 0.01,
            varsayilan: 1.5,
            birim: "mm",
            kosul: [{ alan: "tip", degerler: ["duz_disli"] }],
            ornek: 1.5
          },
          dis_sayisi: {
            tip: "sayi",
            etiket: "Diş sayısı (dişli 8-120, GT2 kasnak 16-80)",
            min: 8,
            max: 120,
            adim: 1,
            varsayilan: 20,
            birim: "adet",
            kosul: [{ alan: "tip", degerler: ["duz_disli", "gt2_kasnak"] }],
            ornek: 20
          },
          kalinlik_mm: {
            tip: "sayi",
            etiket: "Dişli kalınlığı",
            min: 3,
            max: 40,
            adim: 0.01,
            varsayilan: 8,
            birim: "mm",
            kosul: [{ alan: "tip", degerler: ["duz_disli"] }],
            ornek: 8
          },
          dis_boslugu_mm: {
            tip: "sayi",
            etiket: "Diş boşluğu (backlash, çift toplamı)",
            min: 0.05,
            max: 0.5,
            adim: 0.01,
            varsayilan: 0.2,
            birim: "mm",
            kosul: [{ alan: "tip", degerler: ["duz_disli"] }],
            ornek: 0.2
          },
          es_dis_sayisi: {
            tip: "sayi",
            etiket: "Eşleşen dişli diş sayısı (0 = yalnız tek dişli)",
            min: 0,
            max: 120,
            adim: 1,
            varsayilan: 0,
            birim: "adet",
            kosul: [{ alan: "tip", degerler: ["duz_disli"] }],
            ornek: 0
          },
          es_mil_capi_mm: {
            tip: "sayi",
            etiket: "Eşleşen dişli mil çapı (0 = aynı)",
            min: 0,
            max: 40,
            adim: 0.01,
            varsayilan: 0,
            birim: "mm",
            kosul: [{ alan: "tip", degerler: ["duz_disli"] }],
            ornek: 0
          },
          kemer_genislik_mm: {
            tip: "secim",
            etiket: "Kemer genişliği",
            secenekler: [6, 9, 10],
            varsayilan: 6,
            birim: "mm",
            kosul: [{ alan: "tip", degerler: ["gt2_kasnak"] }]
          },
          dis_cap_mm: {
            tip: "sayi",
            etiket: "V kasnak dış çapı",
            min: 16,
            max: 100,
            adim: 0.01,
            varsayilan: 40,
            birim: "mm",
            kosul: [{ alan: "tip", degerler: ["v_kasnak"] }]
          },
          v_kanal_genislik_mm: {
            tip: "sayi",
            etiket: "V kanal üst genişliği",
            min: 6,
            max: 17,
            adim: 0.01,
            varsayilan: 10,
            birim: "mm",
            kosul: [{ alan: "tip", degerler: ["v_kasnak"] }]
          },
          v_kalinlik_mm: {
            tip: "sayi",
            etiket: "V kasnak kalınlığı",
            min: 10,
            max: 40,
            adim: 0.01,
            varsayilan: 16,
            birim: "mm",
            kosul: [{ alan: "tip", degerler: ["v_kasnak"] }]
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 1 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; dişli / kasnak bu parametrelerle üretilir.",
        olcu_ekseni: "turetilmis"
      },
      {
        kod: "kapak",
        ad: "Kapak / tıpa",
        aciklama: "Kapak / tıpa — ölçüye özel üretim.",
        girdi: ["form"],
        motor: "D",
        uretec: "ozel_uret:kapak",
        olcu_mm: { en_az: 10, en_cok: 150 },
        renk_bolgeleri: [],
        malzemeler: { govde: ["PLA", "PETG", "ASA"] },
        form: {
          mod: {
            tip: "secim",
            etiket: "Parça türü",
            secenekler: ["kapak", "tipa"],
            varsayilan: "kapak",
            ornek: "kapak"
          },
          ic_cap_mm: {
            tip: "sayi",
            etiket: "İç çap (kapatılan ağız / tıpanın gireceği delik)",
            min: 6,
            max: 140,
            adim: 0.01,
            varsayilan: 20,
            birim: "mm",
            ornek: 20
          },
          dis_cap_mm: {
            tip: "sayi",
            etiket: "Dış çap (kapak gövdesi / tıpa başlığı)",
            min: 10,
            max: 150,
            adim: 0.01,
            varsayilan: 26,
            birim: "mm",
            ornek: 26
          },
          yukseklik_mm: {
            tip: "sayi",
            etiket: "Kapak yüksekliği",
            min: 4,
            max: 100,
            adim: 0.01,
            varsayilan: 15,
            birim: "mm",
            kosul: [{ alan: "mod", degerler: ["kapak"] }],
            ornek: 15
          },
          tipa_boyu_mm: {
            tip: "sayi",
            etiket: "Tıpa boyu",
            min: 4,
            max: 60,
            adim: 0.01,
            varsayilan: 12,
            birim: "mm",
            kosul: [{ alan: "mod", degerler: ["tipa"] }]
          },
          ust_kalinlik_mm: {
            tip: "sayi",
            etiket: "Üst plaka / başlık kalınlığı",
            min: 1.2,
            max: 6,
            adim: 0.01,
            varsayilan: 2,
            birim: "mm",
            ornek: 2
          },
          gecme_bosluk_mm: {
            tip: "sayi",
            etiket: "Geçme boşluğu (her yüzde)",
            min: 0.2,
            max: 0.4,
            adim: 0.01,
            varsayilan: 0.3,
            birim: "mm",
            ornek: 0.3
          },
          cekme_acisi_derece: {
            tip: "sayi",
            etiket: "Tıpa çekme açısı (0 = silindirik)",
            min: 0,
            max: 5,
            adim: 0.01,
            varsayilan: 0,
            birim: "derece",
            kosul: [{ alan: "mod", degerler: ["tipa"] }]
          },
          topuz: {
            tip: "bool",
            etiket: "Tutma topuzu",
            varsayilan: false,
            ornek: false
          },
          topuz_cap_mm: {
            tip: "sayi",
            etiket: "Topuz çapı",
            min: 6,
            max: 40,
            adim: 0.01,
            varsayilan: 12,
            birim: "mm",
            kosul: [{ alan: "topuz", degerler: [true] }]
          },
          topuz_yukseklik_mm: {
            tip: "sayi",
            etiket: "Topuz yüksekliği",
            min: 3,
            max: 30,
            adim: 0.01,
            varsayilan: 8,
            birim: "mm",
            kosul: [{ alan: "topuz", degerler: [true] }]
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 1 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; kapak / tıpa bu parametrelerle üretilir.",
        olcu_ekseni: "turetilmis"
      },
      {
        kod: "dugme",
        ad: "Düğme / topuz",
        aciklama: "Düğme / topuz — ölçüye özel üretim.",
        girdi: ["form"],
        motor: "D",
        uretec: "ozel_uret:dugme",
        olcu_mm: { en_az: 12, en_cok: 80 },
        renk_bolgeleri: [],
        malzemeler: { govde: ["PLA", "PETG", "ASA"] },
        form: {
          cap_mm: {
            tip: "sayi",
            etiket: "Çap",
            min: 12,
            max: 80,
            adim: 0.01,
            varsayilan: 30,
            birim: "mm",
            ornek: 30
          },
          yukseklik_mm: {
            tip: "sayi",
            etiket: "Yükseklik",
            min: 6,
            max: 80,
            adim: 0.01,
            varsayilan: 18,
            birim: "mm",
            ornek: 18
          },
          tirtil_sayisi: {
            tip: "sayi",
            etiket: "Tırtıl (dikey kanal) sayısı",
            min: 0,
            max: 60,
            adim: 1,
            varsayilan: 0,
            birim: "adet",
            ornek: 0
          },
          tirtil_derinlik_mm: {
            tip: "sayi",
            etiket: "Tırtıl derinliği",
            min: 0.4,
            max: 3,
            adim: 0.01,
            varsayilan: 1,
            birim: "mm",
            ornek: 1
          },
          isaret_cizgisi: {
            tip: "bool",
            etiket: "İşaret çizgisi (üst yüz)",
            varsayilan: false,
            ornek: false
          },
          mil_tipi: {
            tip: "secim",
            etiket: "Mil tipi",
            secenekler: ["yuvarlak", "d_mil", "yivli"],
            varsayilan: "d_mil",
            ornek: "d_mil"
          },
          mil_capi_mm: {
            tip: "sayi",
            etiket: "Mil çapı",
            min: 3,
            max: 12,
            adim: 0.01,
            varsayilan: 6,
            birim: "mm",
            ornek: 6
          },
          duz_kesim_mm: {
            tip: "sayi",
            etiket: "D-mil düz kesim derinliği",
            min: 0.2,
            max: 2,
            adim: 0.01,
            varsayilan: 0.5,
            birim: "mm",
            kosul: [{ alan: "mil_tipi", degerler: ["d_mil"] }],
            ornek: 0.5
          },
          yiv_sayisi: {
            tip: "sayi",
            etiket: "Yiv sayısı (çift)",
            min: 8,
            max: 36,
            adim: 1,
            varsayilan: 18,
            birim: "adet",
            kosul: [{ alan: "mil_tipi", degerler: ["yivli"] }]
          },
          set_vida: {
            tip: "bool",
            etiket: "M3 set vidası kanalı",
            varsayilan: false,
            ornek: false
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 1 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; düğme / topuz bu parametrelerle üretilir.",
        olcu_ekseni: "turetilmis"
      },
      {
        kod: "klips",
        ad: "Klips / kelepçe / menteşe",
        aciklama: "Klips / kelepçe / menteşe — ölçüye özel üretim.",
        girdi: ["form"],
        motor: "D",
        uretec: "ozel_uret:klips",
        olcu_mm: { en_az: 10, en_cok: 200 },
        renk_bolgeleri: [],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          alt_tur: {
            tip: "secim",
            etiket: "Parça türü",
            secenekler: ["boru_kelepcesi", "u_klips", "mentese"],
            varsayilan: "boru_kelepcesi",
            ornek: "boru_kelepcesi"
          },
          boru_cap_mm: {
            tip: "sayi",
            etiket: "Boru dış çapı",
            min: 6,
            max: 120,
            adim: 0.01,
            varsayilan: 25,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["boru_kelepcesi"] }],
            ornek: 25
          },
          agiz_payi_mm: {
            tip: "sayi",
            etiket: "Açık ağız payı (ağız = boru çapı − pay)",
            min: 0.5,
            max: 60,
            adim: 0.01,
            varsayilan: 3,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["boru_kelepcesi"] }],
            ornek: 3
          },
          vida: {
            tip: "secim",
            etiket: "Vida deliği",
            secenekler: ["M3", "M4", "M5"],
            varsayilan: "M4",
            kosul: [{ alan: "alt_tur", degerler: ["boru_kelepcesi"] }],
            ornek: "M4"
          },
          u_aralik_mm: {
            tip: "sayi",
            etiket: "U iç aralığı (kavranan kalınlık)",
            min: 1,
            max: 60,
            adim: 0.01,
            varsayilan: 4,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["u_klips"] }]
          },
          kol_boyu_mm: {
            tip: "sayi",
            etiket: "Kol boyu",
            min: 8,
            max: 80,
            adim: 0.01,
            varsayilan: 20,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["u_klips"] }]
          },
          kanca_mm: {
            tip: "sayi",
            etiket: "Kol ucu kancası (0 = yok)",
            min: 0,
            max: 3,
            adim: 0.01,
            varsayilan: 0.8,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["u_klips"] }]
          },
          genislik_mm: {
            tip: "sayi",
            etiket: "Genişlik (eksen boyu)",
            min: 6,
            max: 40,
            adim: 0.01,
            varsayilan: 12,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["boru_kelepcesi", "u_klips"] }],
            ornek: 12
          },
          kalinlik_mm: {
            tip: "sayi",
            etiket: "Duvar kalınlığı",
            min: 1.6,
            max: 6,
            adim: 0.01,
            varsayilan: 3,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["boru_kelepcesi", "u_klips"] }],
            ornek: 3
          },
          yukseklik_mm: {
            tip: "sayi",
            etiket: "Menteşe yüksekliği (pim ekseni)",
            min: 12,
            max: 120,
            adim: 0.01,
            varsayilan: 40,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["mentese"] }]
          },
          kanat_genislik_mm: {
            tip: "sayi",
            etiket: "Kanat genişliği",
            min: 10,
            max: 80,
            adim: 0.01,
            varsayilan: 30,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["mentese"] }]
          },
          kanat_kalinlik_mm: {
            tip: "sayi",
            etiket: "Kanat kalınlığı",
            min: 2,
            max: 6,
            adim: 0.01,
            varsayilan: 3,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["mentese"] }]
          },
          pim_cap_mm: {
            tip: "sayi",
            etiket: "Pim çapı",
            min: 3,
            max: 8,
            adim: 0.01,
            varsayilan: 4,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["mentese"] }]
          },
          eklem_sayisi: {
            tip: "secim",
            etiket: "Boğum sayısı",
            secenekler: [3, 5, 7],
            varsayilan: 3,
            birim: "adet",
            kosul: [{ alan: "alt_tur", degerler: ["mentese"] }]
          },
          bosluk_mm: {
            tip: "sayi",
            etiket: "Menteşe boşluğu (radyal ve dikey)",
            min: 0.25,
            max: 0.45,
            adim: 0.01,
            varsayilan: 0.3,
            birim: "mm",
            kosul: [{ alan: "alt_tur", degerler: ["mentese"] }]
          },
          vida_deligi: {
            tip: "bool",
            etiket: "Kanatlarda M3 vida delikleri",
            varsayilan: false,
            kosul: [{ alan: "alt_tur", degerler: ["mentese"] }]
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 1 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; klips / kelepçe / menteşe bu parametrelerle üretilir.",
        olcu_ekseni: "turetilmis"
      },
      {
        kod: "saksi",
        ad: "Saksı / vazo",
        aciklama: "Saksı / vazo — ölçüye özel üretim.",
        girdi: ["form"],
        motor: "D",
        uretec: "ozel_uret:saksi",
        olcu_mm: { en_az: 40, en_cok: 300 },
        renk_bolgeleri: [],
        malzemeler: { govde: ["PLA", "PETG", "ASA"] },
        form: {
          tur: {
            tip: "secim",
            etiket: "Parça türü",
            secenekler: ["saksi", "vazo"],
            varsayilan: "saksi",
            ornek: "saksi"
          },
          cap_mm: {
            tip: "sayi",
            etiket: "Ağız dış çapı",
            min: 40,
            max: 300,
            adim: 0.01,
            varsayilan: 100,
            birim: "mm",
            ornek: 100
          },
          yukseklik_mm: {
            tip: "sayi",
            etiket: "Yükseklik",
            min: 40,
            max: 300,
            adim: 0.01,
            varsayilan: 100,
            birim: "mm",
            ornek: 100
          },
          duvar_mm: {
            tip: "sayi",
            etiket: "Duvar kalınlığı (vazo >= 1,6)",
            min: 1.2,
            max: 6,
            adim: 0.01,
            varsayilan: 2,
            birim: "mm",
            ornek: 2
          },
          taban_mm: {
            tip: "sayi",
            etiket: "Taban kalınlığı",
            min: 2,
            max: 10,
            adim: 0.01,
            varsayilan: 3,
            birim: "mm",
            ornek: 3
          },
          profil: {
            tip: "secim",
            etiket: "Profil",
            secenekler: ["silindir", "konik", "oval", "bombeli"],
            varsayilan: "silindir",
            ornek: "silindir"
          },
          alt_cap_mm: {
            tip: "sayi",
            etiket: "Taban dış çapı (konik)",
            min: 20,
            max: 300,
            adim: 0.01,
            varsayilan: 70,
            birim: "mm",
            kosul: [{ alan: "profil", degerler: ["konik"] }]
          },
          oval_orani: {
            tip: "sayi",
            etiket: "Oval küçük/büyük eksen oranı",
            min: 0.5,
            max: 0.95,
            adim: 0.01,
            varsayilan: 0.7,
            birim: "oran",
            kosul: [{ alan: "profil", degerler: ["oval"] }]
          },
          bombe_mm: {
            tip: "sayi",
            etiket: "Bombe payı (bombeli)",
            min: 2,
            max: 40,
            adim: 0.01,
            varsayilan: 8,
            birim: "mm",
            kosul: [{ alan: "profil", degerler: ["bombeli"] }]
          },
          kanal_sayisi: {
            tip: "sayi",
            etiket: "Dikey kanal sayısı",
            min: 0,
            max: 40,
            adim: 1,
            varsayilan: 0,
            birim: "adet",
            ornek: 0
          },
          kanal_derinlik_mm: {
            tip: "sayi",
            etiket: "Kanal derinliği",
            min: 0.5,
            max: 4,
            adim: 0.01,
            varsayilan: 1.5,
            birim: "mm",
            ornek: 1.5
          },
          bukum_derece: {
            tip: "sayi",
            etiket: "Spiral büküm (tepeye kadar)",
            min: 0,
            max: 120,
            adim: 0.01,
            varsayilan: 0,
            birim: "derece",
            ornek: 0
          },
          drenaj_cap_mm: {
            tip: "sayi",
            etiket: "Drenaj deliği çapı",
            min: 5,
            max: 40,
            adim: 0.01,
            varsayilan: 10,
            birim: "mm",
            kosul: [{ alan: "tur", degerler: ["saksi"] }],
            ornek: 10
          },
          tabak: {
            tip: "bool",
            etiket: "Altlık tabağı (ayrı gövde)",
            varsayilan: false,
            ornek: false
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 1 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; saksı / vazo bu parametrelerle üretilir.",
        olcu_ekseni: "turetilmis"
      },
      {
        kod: "rolyef",
        ad: "Yukseklik rolyefi",
        aciklama: "Yukseklik rolyefi — ölçüye özel üretim.",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "rolyef_uret",
        olcu_mm: { en_az: 60, en_cok: 250 },
        renk_bolgeleri: [
          {
            kod: "taban",
            ad: "Taban",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          },
          {
            kod: "rolyef",
            ad: "Rolyef",
            renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
          }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          uzun_kenar_mm: {
            tip: "sayi",
            etiket: "Uzun kenar (plaka)",
            min: 60,
            max: 250,
            adim: 0.01,
            varsayilan: 120,
            birim: "mm",
            ornek: 120
          },
          rolyef_yuksekligi_mm: {
            tip: "sayi",
            etiket: "Rolyef yuksekligi",
            min: 1,
            max: 8,
            adim: 0.01,
            varsayilan: 4,
            birim: "mm",
            ornek: 4
          },
          gamma: {
            tip: "sayi",
            etiket: "Gamma (deger^gamma)",
            min: 0.2,
            max: 5,
            adim: 0.01,
            varsayilan: 1,
            birim: "",
            ornek: 1
          },
          otomatik_seviye: {
            tip: "bool",
            etiket: "Otomatik seviye (%1/%99)",
            varsayilan: true,
            ornek: true
          },
          ters: {
            tip: "bool",
            etiket: "Ters (negatif) mod",
            varsayilan: false,
            ornek: false
          },
          iki_renk: {
            tip: "bool",
            etiket: "Iki renk kolonu",
            varsayilan: false,
            ornek: false
          },
          esik: {
            tip: "sayi",
            etiket: "Esik (0,05..0,95)",
            min: 0.05,
            max: 0.95,
            adim: 0.01,
            varsayilan: 0.5,
            birim: ""
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; yukseklik rolyefi bu parametrelerle üretilir.",
        olcu_ekseni: "sabit"
      },
      {
        kod: "ses",
        ad: "Ses dalgasi",
        aciklama: "Ses dalgasi — ölçüye özel üretim.",
        girdi: ["ses"],
        motor: "D",
        uretec: "ses_dalgasi_uret",
        olcu_mm: { en_az: 80, en_cok: 300 },
        renk_bolgeleri: [
          {
            kod: "plaka",
            ad: "Plaka",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          },
          {
            kod: "cubuk",
            ad: "Cubuk",
            renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
          },
          {
            kod: "yazi",
            ad: "Yazi",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          genlik: {
            tip: "ses",
            etiket: "Hazir genlik dizisi (64..4000)"
          },
          cubuk_sayisi: {
            tip: "sayi",
            etiket: "Cubuk sayisi",
            min: 40,
            max: 400,
            adim: 1,
            varsayilan: 100,
            birim: "adet",
            ornek: 100
          },
          uzun_kenar_mm: {
            tip: "sayi",
            etiket: "Uzun kenar",
            min: 80,
            max: 300,
            adim: 0.01,
            varsayilan: 160,
            birim: "mm",
            ornek: 160
          },
          dalga_yuksekligi_mm: {
            tip: "sayi",
            etiket: "Dalga yuksekligi",
            min: 15,
            max: 150,
            adim: 0.01,
            varsayilan: 40,
            birim: "mm",
            ornek: 40
          },
          cubuk_yuksekligi_mm: {
            tip: "sayi",
            etiket: "Cubuk yuksekligi (kabartma)",
            min: 1.5,
            max: 2.5,
            adim: 0.01,
            varsayilan: 2,
            birim: "mm",
            ornek: 2
          },
          cubuk_genislik_mm: {
            tip: "sayi",
            etiket: "Cubuk genislik (0=oto)",
            min: 0,
            max: 10,
            adim: 0.01,
            varsayilan: 0,
            birim: "mm",
            ornek: 0
          },
          mod: {
            tip: "secim",
            etiket: "Mod",
            secenekler: ["simetrik", "alttan"],
            varsayilan: "simetrik",
            ornek: "simetrik"
          },
          normalizasyon: {
            tip: "secim",
            etiket: "Normalizasyon",
            secenekler: ["tepe", "tam_olcek"],
            varsayilan: "tepe",
            ornek: "tepe"
          },
          baslik: {
            tip: "metin",
            etiket: "Baslik metni (ops.)",
            varsayilan: "",
            max: 40,
            zorunlu: false
          },
          yazi_tipi: {
            tip: "secim",
            etiket: "Yazi tipi",
            secenekler: ["sans-kalin", "serif-kalin"],
            varsayilan: "sans-kalin"
          },
          yazi_yuksekligi_mm: {
            tip: "sayi",
            etiket: "Yazi yuksekligi",
            min: 6,
            max: 30,
            adim: 0.01,
            varsayilan: 8,
            birim: "mm"
          },
          kenar_mm: {
            tip: "sayi",
            etiket: "Plaka kenari",
            min: 4,
            max: 20,
            adim: 0.01,
            varsayilan: 6,
            birim: "mm",
            ornek: 6
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; ses dalgasi bu parametrelerle üretilir.",
        olcu_ekseni: "sabit"
      },
      {
        kod: "braille",
        ad: "Braille",
        aciklama: "Braille — ölçüye özel üretim.",
        girdi: ["metin"],
        motor: "D",
        uretec: "braille_uret",
        olcu_mm: { en_az: 40, en_cok: 250 },
        renk_bolgeleri: [
          {
            kod: "plaka",
            ad: "Plaka",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          },
          {
            kod: "yazi",
            ad: "Yazi",
            renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
          },
          {
            kod: "nokta",
            ad: "Nokta",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          metin: {
            tip: "metin",
            etiket: "Turkce metin (Grade-1)",
            zorunlu: true,
            max: 400,
            ornek: "Pruvo test 2026"
          },
          ust_yazi: {
            tip: "metin",
            etiket: "Ust duz yazi (ops.)",
            varsayilan: "",
            max: 40,
            zorunlu: false
          },
          yazi_tipi: {
            tip: "secim",
            etiket: "Yazi tipi",
            secenekler: ["sans-kalin", "serif-kalin"],
            varsayilan: "sans-kalin",
            ornek: "sans-kalin"
          },
          yazi_yuksekligi_mm: {
            tip: "sayi",
            etiket: "Yazi yuksekligi",
            min: 6,
            max: 40,
            adim: 0.01,
            varsayilan: 10,
            birim: "mm",
            ornek: 10
          },
          genislik_mm: {
            tip: "sayi",
            etiket: "Genislik (0=oto)",
            min: 0,
            max: 250,
            adim: 0.01,
            varsayilan: 0,
            birim: "mm",
            ornek: 0
          },
          satir_kir: {
            tip: "bool",
            etiket: "Kelime sinirinda kir",
            varsayilan: false,
            ornek: false
          },
          hizalama: {
            tip: "secim",
            etiket: "Hizalama",
            secenekler: ["sol", "orta"],
            varsayilan: "sol",
            ornek: "sol"
          },
          kenar_mm: {
            tip: "sayi",
            etiket: "Plaka kenari",
            min: 6,
            max: 20,
            adim: 0.01,
            varsayilan: 6,
            birim: "mm",
            ornek: 6
          },
          buyuk_harf: {
            tip: "secim",
            etiket: "Buyuk harf",
            secenekler: ["kucult", "isaretle"],
            varsayilan: "kucult"
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; braille bu parametrelerle üretilir.",
        olcu_ekseni: "sabit"
      },
      {
        kod: "topo",
        ad: "Topografya",
        aciklama: "Topografya — ölçüye özel üretim.",
        girdi: ["konum"],
        motor: "D",
        uretec: "topo_uret",
        olcu_mm: { en_az: 60, en_cok: 250 },
        renk_bolgeleri: [
          {
            kod: "rolyef",
            ad: "Rolyef",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          },
          {
            kod: "yazi",
            ad: "Yazi",
            renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
          }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          enlem: {
            tip: "sayi",
            etiket: "Enlem",
            min: -80,
            max: 80,
            adim: 0.000001,
            zorunlu: true,
            ornek: 40.15
          },
          boylam: {
            tip: "sayi",
            etiket: "Boylam",
            min: -180,
            max: 180,
            adim: 0.000001,
            zorunlu: true,
            ornek: 29.1
          },
          yaricap_km: {
            tip: "sayi",
            etiket: "Yaricap (km)",
            min: 1,
            max: 300,
            adim: 0.01,
            zorunlu: true,
            ornek: 25
          },
          plaka_sekli: {
            tip: "secim",
            etiket: "Plaka sekli",
            secenekler: ["kare", "daire"],
            varsayilan: "kare",
            ornek: "kare"
          },
          olcu_mm: {
            tip: "sayi",
            etiket: "Olcu (mm)",
            min: 60,
            max: 250,
            adim: 0.01,
            varsayilan: 120,
            birim: "mm",
            ornek: 120
          },
          dikey_abartma: {
            tip: "sayi",
            etiket: "Dikey abartma",
            min: 1,
            max: 5,
            adim: 0.01,
            varsayilan: 2,
            birim: "kat",
            ornek: 3
          },
          deniz_duz: {
            tip: "bool",
            etiket: "Deniz duzeyinde kirp",
            varsayilan: false,
            ornek: false
          },
          cerceve_mm: {
            tip: "sayi",
            etiket: "Cerceve",
            min: 2,
            max: 10,
            adim: 0.01,
            varsayilan: 3,
            birim: "mm",
            ornek: 3
          },
          etiket: {
            tip: "metin",
            etiket: "Etiket metni (ops.)",
            varsayilan: "",
            max: 40,
            zorunlu: false,
            ornek: ""
          },
          yazi_tipi: {
            tip: "secim",
            etiket: "Yazi tipi",
            secenekler: ["sans-kalin", "serif-kalin"],
            varsayilan: "sans-kalin"
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; topografya bu parametrelerle üretilir.",
        olcu_ekseni: "sabit"
      },
      {
        kod: "sehir",
        ad: "Sehir silueti",
        aciklama: "Sehir silueti — ölçüye özel üretim.",
        girdi: ["konum"],
        motor: "D",
        uretec: "sehir_uret",
        olcu_mm: { en_az: 60, en_cok: 250 },
        renk_bolgeleri: [
          {
            kod: "plaka",
            ad: "Plaka",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          },
          {
            kod: "bina",
            ad: "Bina",
            renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
          },
          {
            kod: "yol",
            ad: "Yol",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          enlem: {
            tip: "sayi",
            etiket: "Enlem",
            min: -80,
            max: 80,
            adim: 0.000001,
            zorunlu: true,
            ornek: 41.0256
          },
          boylam: {
            tip: "sayi",
            etiket: "Boylam",
            min: -180,
            max: 180,
            adim: 0.000001,
            zorunlu: true,
            ornek: 28.9742
          },
          yaricap_m: {
            tip: "sayi",
            etiket: "Yaricap (m)",
            min: 200,
            max: 3000,
            adim: 0.01,
            zorunlu: true,
            ornek: 400
          },
          mod: {
            tip: "secim",
            etiket: "Mod",
            secenekler: ["harita", "siluet"],
            varsayilan: "harita",
            ornek: "harita"
          },
          bakis: {
            tip: "secim",
            etiket: "Bakis yonu",
            secenekler: ["kuzey", "guney", "dogu", "bati"],
            varsayilan: "kuzey",
            ornek: "kuzey"
          },
          plaka_sekli: {
            tip: "secim",
            etiket: "Plaka sekli",
            secenekler: ["kare", "daire"],
            varsayilan: "kare",
            ornek: "kare"
          },
          olcu_mm: {
            tip: "sayi",
            etiket: "Olcu (mm)",
            min: 60,
            max: 250,
            adim: 0.01,
            varsayilan: 120,
            birim: "mm",
            ornek: 120
          },
          plaka_yuksekligi_mm: {
            tip: "sayi",
            etiket: "Plaka yuksekligi (siluet; 0=oto)",
            min: 0,
            max: 250,
            adim: 0.01,
            varsayilan: 0,
            birim: "mm"
          },
          yukseklik_abartma: {
            tip: "sayi",
            etiket: "Yukseklik abartma",
            min: 1,
            max: 10,
            adim: 0.01,
            varsayilan: 3,
            birim: "kat",
            ornek: 3
          },
          varsayilan_yukseklik_m: {
            tip: "sayi",
            etiket: "Varsayilan yukseklik (m)",
            min: 3,
            max: 30,
            adim: 0.01,
            varsayilan: 9,
            birim: "m",
            ornek: 9
          },
          yollar: {
            tip: "bool",
            etiket: "Yollari ciz (harita)",
            varsayilan: false,
            ornek: false
          },
          yol_genislik_mm: {
            tip: "sayi",
            etiket: "Yol genislik",
            min: 1,
            max: 2,
            adim: 0.01,
            varsayilan: 1.2,
            birim: "mm"
          },
          cerceve_mm: {
            tip: "sayi",
            etiket: "Cerceve",
            min: 2,
            max: 8,
            adim: 0.01,
            varsayilan: 3,
            birim: "mm",
            ornek: 3
          },
          etiket: {
            tip: "metin",
            etiket: "Etiket metni (ops.)",
            varsayilan: "",
            max: 40,
            zorunlu: false
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; sehir silueti bu parametrelerle üretilir.",
        olcu_ekseni: "sabit"
      },
      {
        kod: "yildiz",
        ad: "Yildiz haritasi",
        aciklama: "Yildiz haritasi — ölçüye özel üretim.",
        girdi: ["konum", "tarih"],
        motor: "D",
        uretec: "yildiz_uret",
        olcu_mm: { en_az: 80, en_cok: 250 },
        renk_bolgeleri: [
          {
            kod: "plaka",
            ad: "Plaka",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          },
          {
            kod: "yildiz",
            ad: "Yildiz",
            renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
          }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          tarih_saat: {
            tip: "metin",
            etiket: "Tarih/saat (yerel)",
            zorunlu: true,
            max: 20,
            ornek: "2026-10-07 21:30"
          },
          utc_ofset_saat: {
            tip: "sayi",
            etiket: "UTC ofset (saat)",
            min: -12,
            max: 14,
            adim: 0.01,
            zorunlu: true,
            ornek: 3
          },
          enlem: {
            tip: "sayi",
            etiket: "Enlem",
            min: -90,
            max: 90,
            adim: 0.000001,
            zorunlu: true,
            ornek: 41.0082
          },
          boylam: {
            tip: "sayi",
            etiket: "Boylam",
            min: -180,
            max: 180,
            adim: 0.000001,
            zorunlu: true,
            ornek: 28.9784
          },
          izdusum: {
            tip: "secim",
            etiket: "Iz dusum",
            secenekler: ["stereografik", "esit_alan"],
            varsayilan: "stereografik",
            ornek: "stereografik"
          },
          olcu_mm: {
            tip: "sayi",
            etiket: "Olcu (mm, daire)",
            min: 80,
            max: 250,
            adim: 0.01,
            varsayilan: 150,
            birim: "mm",
            ornek: 150
          },
          kadir_esigi: {
            tip: "sayi",
            etiket: "Kadir esigi",
            min: 2,
            max: 6,
            adim: 0.01,
            varsayilan: 4,
            ornek: 2
          },
          yildiz_sekli: {
            tip: "secim",
            etiket: "Yildiz sekli",
            secenekler: ["silindir", "kubbe"],
            varsayilan: "silindir",
            ornek: "silindir"
          },
          ufuk_halkasi: {
            tip: "bool",
            etiket: "Ufuk halkasi",
            varsayilan: true,
            ornek: true
          },
          ekliptik: {
            tip: "bool",
            etiket: "Ekliptik cizgisi",
            varsayilan: false,
            ornek: false
          },
          meridyen: {
            tip: "bool",
            etiket: "Meridyen cizgisi",
            varsayilan: false,
            ornek: false
          },
          cizgi_mm: {
            tip: "sayi",
            etiket: "Cizgi genislik",
            min: 0.8,
            max: 2,
            adim: 0.01,
            varsayilan: 1.2,
            birim: "mm",
            ornek: 1.2
          },
          otomatik_yazi: {
            tip: "bool",
            etiket: "Otomatik alt yazi",
            varsayilan: true,
            ornek: true
          },
          alt_yazi: {
            tip: "metin",
            etiket: "Alt yazi (ops.)",
            varsayilan: "",
            max: 40,
            zorunlu: false
          },
          yazi_tipi: {
            tip: "secim",
            etiket: "Yazi tipi",
            secenekler: ["sans-kalin", "serif-kalin"],
            varsayilan: "sans-kalin"
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; yildiz haritasi bu parametrelerle üretilir.",
        olcu_ekseni: "sabit"
      },
      {
        kod: "koordinat",
        ad: "Koordinat / tarih",
        aciklama: "Koordinat / tarih — ölçüye özel üretim.",
        girdi: ["konum"],
        motor: "D",
        uretec: "koordinat_uret",
        olcu_mm: { en_az: 60, en_cok: 250 },
        renk_bolgeleri: [
          {
            kod: "plaka",
            ad: "Plaka",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          },
          {
            kod: "yazi",
            ad: "Yazi",
            renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
          }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          enlem: {
            tip: "sayi",
            etiket: "Enlem",
            min: -90,
            max: 90,
            adim: 0.000001,
            zorunlu: true,
            ornek: 41.0082
          },
          boylam: {
            tip: "sayi",
            etiket: "Boylam",
            min: -180,
            max: 180,
            adim: 0.000001,
            zorunlu: true,
            ornek: 28.9784
          },
          bicim: {
            tip: "secim",
            etiket: "Koordinat bicimi",
            secenekler: ["ondalik", "dms"],
            varsayilan: "ondalik",
            ornek: "ondalik"
          },
          ondalik_hane: {
            tip: "sayi",
            etiket: "Ondalik hane",
            min: 2,
            max: 6,
            adim: 1,
            varsayilan: 4,
            birim: "hane",
            ornek: 4
          },
          koordinat_satiri: {
            tip: "secim",
            etiket: "Koordinat satiri",
            secenekler: ["cift", "tek"],
            varsayilan: "cift",
            ornek: "cift"
          },
          tarih: {
            tip: "metin",
            etiket: "Tarih (YYYY-AA-GG, ops.)",
            varsayilan: "",
            max: 10,
            zorunlu: false,
            ornek: "2026-10-07"
          },
          tarih_bicimi: {
            tip: "secim",
            etiket: "Tarih bicimi",
            secenekler: ["gg_aa_yyyy", "uzun"],
            varsayilan: "gg_aa_yyyy",
            ornek: "gg_aa_yyyy"
          },
          serbest_metin: {
            tip: "metin",
            etiket: "Serbest satir",
            varsayilan: "",
            max: 40,
            zorunlu: false,
            ornek: ""
          },
          isaret: {
            tip: "secim",
            etiket: "Isaret",
            secenekler: ["yok", "arti", "pusula"],
            varsayilan: "yok",
            ornek: "yok"
          },
          plaka_sekli: {
            tip: "secim",
            etiket: "Plaka sekli",
            secenekler: ["dikdortgen", "yuvarlak-kose", "oval"],
            varsayilan: "dikdortgen",
            ornek: "dikdortgen"
          },
          genislik_mm: {
            tip: "sayi",
            etiket: "Genislik (zorunlu)",
            min: 20,
            max: 400,
            adim: 0.01,
            varsayilan: 160,
            birim: "mm",
            ornek: 160
          },
          yukseklik_mm: {
            tip: "sayi",
            etiket: "Yukseklik (zorunlu)",
            min: 10,
            max: 400,
            adim: 0.01,
            varsayilan: 90,
            birim: "mm",
            ornek: 90
          },
          kose_yaricap_mm: {
            tip: "sayi",
            etiket: "Kose yaricap",
            min: 1,
            max: 30,
            adim: 0.01,
            varsayilan: 5,
            birim: "mm"
          },
          kenar_payi_mm: {
            tip: "sayi",
            etiket: "Kenar payi",
            min: 2,
            max: 20,
            adim: 0.01,
            varsayilan: 4,
            birim: "mm"
          },
          yazi_tipi: {
            tip: "secim",
            etiket: "Yazi tipi",
            secenekler: ["sans-kalin", "serif-kalin"],
            varsayilan: "sans-kalin"
          },
          hizalama: {
            tip: "secim",
            etiket: "Hizalama",
            secenekler: ["sol", "orta"],
            varsayilan: "sol"
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Ölçüye özel üretilir; üretim dosyasının görüntüsüdür, basılmış ürün bu yorumun kabartmalı hâlidir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; koordinat / tarih bu parametrelerle üretilir.",
        olcu_ekseni: "sabit"
      },
      {
        kod: "bust",
        ad: "Bust/madalyon (rolyef)",
        aciklama: "Fotoğraftan kabartma büst/madalyon (ters/iki renk opsiyonel).",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "rolyef_uret",
        olcu_mm: { en_az: 60, en_cok: 250 },
        renk_bolgeleri: [],
        renk_secimi: "palet",
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          uzun_kenar_mm: {
            tip: "sayi",
            etiket: "Boyut",
            min: 60,
            max: 250,
            adim: 0.01,
            varsayilan: 120,
            birim: "mm",
            ornek: 120
          },
          rolyef_yuksekligi_mm: {
            tip: "sayi",
            etiket: "Kabartma yuksekligi",
            min: 1,
            max: 8,
            adim: 0.01,
            varsayilan: 4,
            birim: "mm",
            ornek: 4
          },
          ters: {
            tip: "bool",
            etiket: "Ters (negatif)",
            varsayilan: false,
            ornek: false
          },
          iki_renk: {
            tip: "bool",
            etiket: "Iki renk",
            varsayilan: false,
            ornek: false
          }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Fotoğraf gri-ton yükseklik haritasına çevrilir; kabartma büst/madalyon olarak üretilir, ince ayrıntılar sadeleşir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; kabartma büst bu parametrelerle üretilir.",
        olcu_ekseni: "sabit"
      }
    ],

    // PLAKA SINIRI (sözleşme §3, mm): üretim dosyasının tabla kutusu x ve y bundan büyük olamaz.
    // 7 Eki 2026 mimar kararı: 250 -> 300 (H2D paylaşılan bant X 25–325; yapboz raf düzeni 190 mm'de
    // 284×192 ölçüldü). TEK kaynak: koşucu (tools/foto-uretec-kosucu.py) ve sunucu (shop/src/foto.js)
    // buradan okur; ikinci kopya YOK.
    PLAKA_MM: 300,

    // FİLAMENT RENKLERİ — renk ADI -> üreteçteki hex (TEK tablo; mimar kararı 7 Eki 2026). Bir türün
    // `renk_bolgeleri[].renkler` listesinde yalnız buradaki adlar olabilir; üreteç köprüsü
    // (tools/foto-uretec-kosucu.py) adı buradan hex'e çevirir. Başka renk YOK.
    RENK_HEX: {
      "Beyaz": "#F2F2F2", "Siyah": "#1A1A1A", "Gri": "#818184", "Lacivert": "#12294D",
      "Kırmızı": "#B3262E", "Sarı": "#E8B923", "Yeşil": "#2E7D4F", "Mavi": "#2E5E8C", "Ahşap": "#C8B89A"
    },

    // ÜRETEÇ REDDİ -> müşteriye gösterilen metin. Koşucu reddi `uretec-red:<kod>` diye yazar
    // (kod üretecin RET cümlesinden köprüde çıkarılır); tabloda olmayan kod -> `""` (genel metin).
    URETEC_RED_METIN: {
      "": "Bu girdiyle üretim dosyası hazırlanamadı; girdiyi ya da ölçüyü değiştirip tekrar deneyebilirsin.",
      "kontrast": "Seçtiğin renkler birbirine çok yakın; daha belirgin iki renk seç.",
      "metin-sigmadi": "Yazı bu ölçüye sığmadı; yazıyı kısalt ya da ölçüyü büyüt.",
      "ince-cizgi": "Çizimde çok ince çizgiler var; daha kalın çizgili bir görsel dene.",
      "karakter": "Yazıda üretemediğimiz bir karakter var (ör. emoji); onu çıkarıp tekrar dene.",
      "kisa-kenar": "Kısa kenar uzun kenardan büyük olamaz.",
      "olcu-aralik-disi": "Bu değerlerle ürünün en uzun boyutu bu türün ölçü aralığının dışında kalıyor; değerleri değiştirip tekrar dene.",
      "qr-uzun": "QR koda girecek metin çok uzun; daha kısa bir bağlantı kullan.",
      "svg": "SVG dosyası okunamadı ya da desteklemediğimiz öğeler içeriyor (yazı, görsel, maske); şekle çevrilmiş düz bir SVG dene.",
      "gorsel": "Görsel okunamadı ya da içinde belirgin bir şekil bulunamadı; net, koyu bir şekil içeren PNG ya da JPEG dene.",
      "oran": "Görselin en/boy oranı bu ürün için çok uzun; daha dengeli bir kırpım dene.",
      "parca": "Bu ölçüde seçtiğin parça sayısı çok küçük parçalar çıkarıyor; ölçüyü büyüt ya da daha az parça seç.",
      "kopru": "Görseldeki iç adalar şablona bağlanamadı; daha sade bir silüet dene."
    },

    // ÖRNEKLER — boşsa bölüm görünmez. Kaynak: TeKiN'in işleri (kanıtı kayıtta yazılı).
    ornekler: [
      {
        tur: "plaket",
        kanit: "render",
        olcu_mm: 120,
        onizleme: "https://media.pruvo3d.com/foto/ornek/plaket-1-onizleme.webp",
        render: "https://media.pruvo3d.com/foto/ornek/plaket-1-render.webp",
        not: "120 mm, 4 renk, ayağıyla"
      },
      {
        tur: "litofan",
        kanit: "render",
        olcu_mm: 140,
        // Sentetik çizim (deniz + güneş + yelkenli); kişi/marka/telifli görsel YOK. Önizleme =
        // aynı render (litofanın önizlemesi tarayıcıda çizilir; örnek kartında render gösterilir).
        onizleme: "https://media.pruvo3d.com/foto/ornek/litofan-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/litofan-1-render.webp",
        not: "140 mm, arkadan ışıkla"
      },
      {
        tur: "isimlik",
        kanit: "render",
        olcu_mm: 160,
        // G2b (7 Eki 2026): GERÇEK üreteç çıktısının (3MF) render'ı; girdiler nötr ve çizilmiş —
        // "Ada & Deniz", pruvo3d.com QR, çember+dalga amblem, "AD" monogram, kuş silüeti, sentetik deniz.
        // Kişi/marka/telifli görsel YOK. Önizleme = aynı render.
        onizleme: "https://media.pruvo3d.com/foto/ornek/isimlik-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/isimlik-1-render.webp",
        not: "160 mm, 2 renk, montaj delikli"
      },
      {
        tur: "qr",
        kanit: "render",
        olcu_mm: 90,
        onizleme: "https://media.pruvo3d.com/foto/ornek/qr-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/qr-1-render.webp",
        not: "90 mm, 2 renk, çerçeveli"
      },
      {
        tur: "logo",
        kanit: "render",
        olcu_mm: 100,
        onizleme: "https://media.pruvo3d.com/foto/ornek/logo-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/logo-1-render.webp",
        not: "100 mm, 2 renk, tabanlı"
      },
      {
        tur: "muhur",
        kanit: "render",
        olcu_mm: 40,
        onizleme: "https://media.pruvo3d.com/foto/ornek/muhur-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/muhur-1-render.webp",
        not: "40 mm yüz, 2 renk, topuz saplı"
      },
      {
        tur: "sablon",
        kanit: "render",
        olcu_mm: 150,
        onizleme: "https://media.pruvo3d.com/foto/ornek/sablon-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/sablon-1-render.webp",
        not: "150 mm, delikli şablon"
      },
      {
        tur: "yapboz",
        kanit: "render",
        olcu_mm: 150,
        onizleme: "https://media.pruvo3d.com/foto/ornek/yapboz-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/yapboz-1-render.webp",
        not: "150 mm, 20 parça"
      },
      {
        tur: "kutu",
        kanit: "render",
        olcu_mm: 100,
        onizleme: "https://media.pruvo3d.com/foto/ornek/kutu-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/kutu-1-render.webp",
        not: "100x60x40 mm, kapaklı"
      },
      {
        tur: "adaptor",
        kanit: "render",
        olcu_mm: 60,
        onizleme: "https://media.pruvo3d.com/foto/ornek/adaptor-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/adaptor-1-render.webp",
        not: "60 mm burç"
      },
      {
        tur: "disli",
        kanit: "render",
        olcu_mm: 60,
        onizleme: "https://media.pruvo3d.com/foto/ornek/disli-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/disli-1-render.webp",
        not: "60 mm düz dişli"
      },
      {
        tur: "kapak",
        kanit: "render",
        olcu_mm: 60,
        onizleme: "https://media.pruvo3d.com/foto/ornek/kapak-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/kapak-1-render.webp",
        not: "60 mm kapak"
      },
      {
        tur: "dugme",
        kanit: "render",
        olcu_mm: 40,
        onizleme: "https://media.pruvo3d.com/foto/ornek/dugme-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/dugme-1-render.webp",
        not: "40 mm düz düğme"
      },
      {
        tur: "klips",
        kanit: "render",
        olcu_mm: 60,
        onizleme: "https://media.pruvo3d.com/foto/ornek/klips-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/klips-1-render.webp",
        not: "60 mm boru kelepçesi"
      },
      {
        tur: "saksi",
        kanit: "render",
        olcu_mm: 100,
        onizleme: "https://media.pruvo3d.com/foto/ornek/saksi-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/saksi-1-render.webp",
        not: "100 mm saksı"
      },
      {
        tur: "rolyef",
        kanit: "render",
        olcu_mm: 120,
        onizleme: "https://media.pruvo3d.com/foto/ornek/rolyef-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/rolyef-1-render.webp",
        not: "120 mm kabartma rölyef"
      },
      {
        tur: "ses",
        kanit: "render",
        olcu_mm: 160,
        onizleme: "https://media.pruvo3d.com/foto/ornek/ses-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/ses-1-render.webp",
        not: "160 mm ses dalgası"
      },
      {
        tur: "braille",
        kanit: "render",
        olcu_mm: 160,
        onizleme: "https://media.pruvo3d.com/foto/ornek/braille-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/braille-1-render.webp",
        not: "160 mm Braille tabela"
      },
      {
        tur: "topo",
        kanit: "render",
        olcu_mm: 120,
        onizleme: "https://media.pruvo3d.com/foto/ornek/topo-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/topo-1-render.webp",
        not: "120 mm topografya"
      },
      {
        tur: "sehir",
        kanit: "render",
        olcu_mm: 120,
        onizleme: "https://media.pruvo3d.com/foto/ornek/sehir-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/sehir-1-render.webp",
        not: "120 mm şehir silueti"
      },
      {
        tur: "yildiz",
        kanit: "render",
        olcu_mm: 160,
        onizleme: "https://media.pruvo3d.com/foto/ornek/yildiz-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/yildiz-1-render.webp",
        not: "160 mm yıldız haritası"
      },
      {
        tur: "koordinat",
        kanit: "render",
        olcu_mm: 120,
        onizleme: "https://media.pruvo3d.com/foto/ornek/koordinat-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/koordinat-1-render.webp",
        not: "120 mm koordinat/tarih"
      },
      {
        tur: "bust",
        kanit: "render",
        olcu_mm: 100,
        onizleme: "https://media.pruvo3d.com/foto/ornek/bust-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/bust-1-render.webp",
        not: "100 mm büst/madalyon"
      },
      {
        tur: "figur",
        kanit: "render",
        olcu_mm: 130,
        // kopru-15 (8 Eki 2026): GERÇEK sağlayıcı önizlemesi (tools/saglayici-ornek.py); girdi SENTETİK çizim
        // (oyuncak kedi silueti) — kişi/marka/telifli görsel YOK. Önizleme = aynı render.
        onizleme: "https://media.pruvo3d.com/foto/ornek/figur-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/figur-1-render.webp",
        not: "130 mm, kaideli figür"
      }
    ],

    // Ziyaretçi başına 24 saatte en çok kaç önizleme (sunucu da AYNI sayıyı uygular).
    sinir_ziyaretci_24s: 3,

    // Önizleme kaç saat içinde siparişe dönüşebilir (sunucu sınırı; bölüm müşteriye söyler).
    gecerlilik_saat: 48,

    // 2D KONSEPT (Okan 7 Eki 14:5x: "Nasıl olsun?" notu → 2D sonuç nota göre). TEK KAYNAK: sunucu
    // (shop/src/foto.js) model/sınır/tavanı YALNIZ buradan okur, bölüm deneme sayısını buradan yazar.
    //   model              : görsel+metin → görsel modeli (en ucuzu; değişirse kredi_tahmini de değişir)
    //   kredi_tahmini      : model başına bir konseptin kredisi (günlük tavan bu sayıyla sayar)
    //   deneme_is_basi     : bir önizleme işinde en çok kaç konsept (Okan: ≤3)
    //   sinir_ziyaretci_24s: ziyaretçi başına 24 saatte en çok konsept (3 iş × 3 deneme)
    //   gunluk_kredi_tavani: tüm ziyaretçilerin 24 saatteki konsept kredisi tavanı (aşılınca 429)
    konsept: {
      model: "nano-banana",
      kredi_tahmini: 3,
      deneme_is_basi: 3,
      sinir_ziyaretci_24s: 9,
      gunluk_kredi_tavani: 120
    }
  };

  // Örneğin kanıtı: alan yoksa 5 Eki anlamı ("baski"); bilinmeyen değer -> "" (sayılmaz).
  VERI.ornekKaniti = function (o) {
    var k = o && o.kanit == null ? "baski" : (o && o.kanit);
    return k === "baski" || k === "render" ? k : "";
  };
  // Kayıt TÜRÜNDE sayılır mı: kanıt türün `ornek_kanit_izni`nde VE kanıtın görselleri dolu.
  // Bölüm (hangi örnek çizilir) ve sunucu (tür açık mı) AYNI fonksiyonu kullanır.
  VERI.ornekGecerli = function (o) {
    if (!o) { return false; }
    var t = VERI.turBul(o.tur);
    var k = VERI.ornekKaniti(o);
    var izin = t && Array.isArray(t.ornek_kanit_izni) ? t.ornek_kanit_izni : [];
    if (!k || izin.indexOf(k) < 0) { return false; }
    if (k === "baski") { return !!(o.foto && o.onizleme && o.baski); }
    return !!(o.onizleme && o.render);
  };
  // Bir türün sayılan örnek sayısı — bölüm ve sunucu AYNI fonksiyonu kullanır.
  VERI.ornekSayisi = function (tur) {
    var n = 0;
    for (var i = 0; i < VERI.ornekler.length; i++) {
      var o = VERI.ornekler[i];
      if (o && o.tur === tur && VERI.ornekGecerli(o)) { n++; }
    }
    return n;
  };
  VERI.turBul = function (kod) {
    for (var i = 0; i < VERI.turler.length; i++) {
      if (VERI.turler[i].kod === kod) { return VERI.turler[i]; }
    }
    return null;
  };

  // MOTOR -> akış kolu. Kol TÜRETİLİR (satırda ayrı `kol` alanı yazılmaz; ikinci kaynak yok).
  VERI.MOTOR_KOLU = { M: "saglayici", D: "deterministik", R: "deterministik" };
  // Türün akış kolu ("saglayici" | "deterministik"); bilinmeyen tür/motor -> "" (hiçbir kola girmez).
  VERI.kolu = function (kod) {
    var t = VERI.turBul(kod);
    var m = t && typeof t.motor === "string" ? t.motor : "";
    return Object.prototype.hasOwnProperty.call(VERI.MOTOR_KOLU, m) ? VERI.MOTOR_KOLU[m] : "";
  };
  // Üreteç kimliği -> tarayıcıda sipariş öncesi önizleme çizen kol (bugün yalnız litofan). Bölüm
  // ve sunucu AYNI tablo: burada OLMAYAN D/R türünün sipariş öncesi önizlemesini üreteç koşucusu
  // çıkarır (/foto/onizleme -> foto_isler 'uretec-onizleme' -> koşucu -> 'onizleme-hazir').
  VERI.TARAYICI_ONIZLEYICI = { litofan_uret: true };
  // Aydınlatma maddeleri türün motoruna göre: kol "M" maddesi yalnız M motorlu türde gösterilir.
  VERI.aydinlatmaMaddeleri = function (kod) {
    var t = VERI.turBul(kod);
    var m = t ? t.motor : "";
    return VERI.onay.aydinlatma.filter(function (x) { return !x.kol || x.kol === m; })
      .map(function (x) { return x.metin; });
  };
  // Üreteç reddinin müşteri metni: hata "uretec-red:<kod>" -> tablo; bilinmeyen kod -> genel metin.
  VERI.uretecRedMetni = function (hata) {
    var m = /^uretec-red:([a-z0-9-]{1,40})$/.exec(typeof hata === "string" ? hata : "");
    var k = m && Object.prototype.hasOwnProperty.call(VERI.URETEC_RED_METIN, m[1]) ? m[1] : "";
    return VERI.URETEC_RED_METIN[k];
  };

  // GİRDİ TÜRLERİ — `acik:false` = şemada tanımlı, YAKINDA (bölüm göstermez, sunucu 400; G5'te açılır).
  VERI.GIRDI_TURLERI = {
    "foto-1": { acik: true }, "foto-1-3": { acik: true, en_cok: 3 },
    metin: { acik: true }, url: { acik: true, en_cok: 512 }, svg: { acik: true, en_cok_bayt: 200 * 1024 },
    form: { acik: true }, ses: { acik: true }, konum: { acik: true }, tarih: { acik: true }
  };
  VERI.FORM_TIPLERI = { sayi: true, secim: true, metin: true, url: true, ses: true, konum: true, tarih: true, bool: true };

  function utf8Bayt(s) {
    return typeof TextEncoder !== "undefined" ? new TextEncoder().encode(s).length : unescape(encodeURIComponent(s)).length;
  }
  VERI.urlDogrula = function (s) {
    return typeof s === "string" && s.length <= VERI.GIRDI_TURLERI.url.en_cok &&
      /^https:\/\/[^\s\/?#@]+(?:[\/?#][^\s]*)?$/.test(s);
  };
  // SVG: <= 200 KB, kök <svg>; script / olay özniteliği / foreignObject / ENTITY / harici
  // referans (href, url(...) içinde "#" dışı) RED. Dönüş "" = geçerli, aksi sebep kodu.
  VERI.svgDogrula = function (s) {
    if (typeof s !== "string" || !s.length) { return "svg-bos"; }
    var bayt = typeof TextEncoder !== "undefined" ? new TextEncoder().encode(s).length : s.length * 3;
    if (bayt > VERI.GIRDI_TURLERI.svg.en_cok_bayt) { return "svg-buyuk"; }
    if (!/^\s*(<\?xml[^>]*\?>\s*)?<svg[\s>]/i.test(s)) { return "svg-degil"; }
    if (/<\s*script/i.test(s) || /\son[a-z]+\s*=/i.test(s) || /javascript:/i.test(s)) { return "svg-script"; }
    if (/<\s*foreignObject/i.test(s) || /<!ENTITY|<!DOCTYPE/i.test(s)) { return "svg-yasak-oge"; }
    if (/(?:xlink:)?href\s*=\s*["']\s*[^"'#\s]/i.test(s) || /url\(\s*["']?\s*[^"'#\s)]/i.test(s) ||
        /@import/i.test(s)) { return "svg-harici-referans"; }
    return "";
  };
  // PARAMETRELER — türün `form` şemasına karşı. Şema dışı anahtar, YAKINDA tipi, aralık/adım dışı
  // sayı, listede olmayan seçim, boş/uzun metin, geçersiz url -> {ok:false, hata}. Bölüm ve sunucu AYNI.
  // BİLEŞEN TİPLER (ses/konum/tarih — BaBa 8 Eki 00:3x hüküm 1(e)):
  //   ses    : değer = sayı dizisi (genlik); uzunluk 64..4000, her eleman sonlu sayı 0..1.
  //   konum  : değer = {enlem:-90..90, boylam:-180..180}; ikisi de sonlu sayı.
  //   tarih  : değer = "YYYY-AA-GG" veya (şema.saat:true) {tarih,saat:"SS:DD",utc_ofset_saat:-12..14}.
  //            Yıl 1900..2100, takvim geçerli (2023-02-29 ✓, 2023-02-30 ✗).
  //   bool   : değer YALNIZ true/false (JSON boolean); "true"/"1"/1/null dize-sayı biçimi RED.
  // KOŞULLU ALAN (kopru-15 DILIM-2): şema alanı `kosul: [{alan, degerler}]` taşıyorsa alan YALNIZ her
  // koşulun `alan`ı gönderilmiş VE değeri `degerler` içindeyse VARDIR (zorunlu); değilse çıktıya GİRMEZ,
  // gönderilirse `sema-disi-parametre`. Bölüm aynı fonksiyonla koşulu sağlanmayan alanı gizler.
  VERI.alanAktif = function (form, a, p) {
    var k = (form && form[a] || {}).kosul;
    if (k === undefined) { return true; }
    if (!Array.isArray(k) || !p || typeof p !== "object") { return false; }
    for (var i = 0; i < k.length; i++) {
      var c = k[i] || {};
      if (!Array.isArray(c.degerler) || !Object.prototype.hasOwnProperty.call(p, c.alan) ||
          c.degerler.indexOf(p[c.alan]) < 0) { return false; }
    }
    return true;
  };
  VERI.parametreDogrula = function (kod, p) {
    var t = VERI.turBul(kod);
    if (!t) { return { ok: false, hata: "tur-yok" }; }
    var form = t.form && typeof t.form === "object" ? t.form : {};
    if (p === undefined || p === null) { p = {}; }
    if (typeof p !== "object" || Array.isArray(p)) { return { ok: false, hata: "parametre-bicimi" }; }
    var cikti = {};
    var anahtarlar = Object.keys(p);
    for (var i = 0; i < anahtarlar.length; i++) {
      if (!Object.prototype.hasOwnProperty.call(form, anahtarlar[i])) { return { ok: false, hata: "sema-disi-parametre" }; }
    }
    var alanlar = Object.keys(form);
    for (var j = 0; j < alanlar.length; j++) {
      var a = alanlar[j], sema = form[a] || {}, v = p[a];
      if (VERI.FORM_TIPLERI[sema.tip] !== true) { return { ok: false, hata: "parametre-yakinda" }; }
      if (!VERI.alanAktif(form, a, p)) {
        if (Object.prototype.hasOwnProperty.call(p, a)) { return { ok: false, hata: "sema-disi-parametre" }; }
        continue;
      }
      // `zorunlu: false` (yalnız metin): boş/yok -> alan çıktıya GİRMEZ (üreteç varsayılanı).
      if (sema.zorunlu === false && sema.tip === "metin" && (v === undefined || v === "")) { continue; }
      if (sema.tip === "sayi") {
        if (typeof v !== "number" || !isFinite(v) || v < sema.min || v > sema.max) { return { ok: false, hata: "parametre-aralik" }; }
        var adim = sema.adim > 0 ? sema.adim : 1;
        var k = (v - sema.min) / adim;
        // Tolerans adımın milyonda biri: enlem/boylam adımı 0.000001'de (v-min)/adim ~1e8 olur ve kayan nokta
        // hatası 1e-9'u aşar (geçerli 41.0082 RED olurdu); ızgara dışı her değer yine RED.
        if (Math.abs(k - Math.round(k)) > 1e-6) { return { ok: false, hata: "parametre-adim" }; }
      } else if (sema.tip === "secim") {
        if (!Array.isArray(sema.secenekler) || sema.secenekler.indexOf(v) < 0) { return { ok: false, hata: "parametre-secim" }; }
      } else if (sema.tip === "metin") {
        if (typeof v !== "string" || !v.trim() || v.length > (sema.max || 0)) { return { ok: false, hata: "parametre-metin" }; }
        // `bayt_max`: UTF-8 bayt tavanı (QR kapasitesi); `satir_en_cok`/`satir_max`: "\n" ile satırlar.
        if (sema.bayt_max > 0 && utf8Bayt(v) > sema.bayt_max) { return { ok: false, hata: "parametre-metin" }; }
        if (sema.satir_en_cok > 0) {
          var satirlar = v.split("\n");
          if (satirlar.length > sema.satir_en_cok) { return { ok: false, hata: "parametre-metin" }; }
          for (var s = 0; s < satirlar.length; s++) {
            if (!satirlar[s].trim() || satirlar[s].length > (sema.satir_max || 0)) { return { ok: false, hata: "parametre-metin" }; }
          }
        } else if (v.indexOf("\n") >= 0) { return { ok: false, hata: "parametre-metin" }; }
      } else if (sema.tip === "url") {
        if (!VERI.urlDogrula(v)) { return { ok: false, hata: "parametre-url" }; }
      } else if (sema.tip === "bool") {
        if (v !== true && v !== false) { return { ok: false, hata: "parametre-bool" }; }
      } else if (sema.tip === "ses") {
        if (!Array.isArray(v)) { return { ok: false, hata: "parametre-ses" }; }
        if (v.length < 64 || v.length > 4000) { return { ok: false, hata: "parametre-ses" }; }
        for (var g = 0; g < v.length; g++) {
          if (typeof v[g] !== "number" || !isFinite(v[g]) || v[g] < 0 || v[g] > 1) { return { ok: false, hata: "parametre-ses" }; }
        }
      } else if (sema.tip === "konum") {
        if (!v || typeof v !== "object" || Array.isArray(v)) { return { ok: false, hata: "parametre-konum" }; }
        if (typeof v.enlem !== "number" || !isFinite(v.enlem) || v.enlem < -90 || v.enlem > 90) {
          return { ok: false, hata: "parametre-konum" };
        }
        if (typeof v.boylam !== "number" || !isFinite(v.boylam) || v.boylam < -180 || v.boylam > 180) {
          return { ok: false, hata: "parametre-konum" };
        }
      } else if (sema.tip === "tarih") {
        var trh, satStr;
        if (typeof v === "string") { trh = v; satStr = undefined; }
        else if (v && typeof v === "object" && !Array.isArray(v)) { trh = v.tarih; satStr = v.saat; }
        else { return { ok: false, hata: "parametre-tarih" }; }
        var trhSonuc = VERI.tarihCozumle(trh);
        if (trhSonuc.hata) { return { ok: false, hata: "parametre-tarih" }; }
        var saatGerekli = sema.saat === true;
        if (saatGerekli) {
          if (typeof satStr !== "string" || !/^([01]\d|2[0-3]):[0-5]\d$/.test(satStr)) { return { ok: false, hata: "parametre-tarih" }; }
          if (!v || typeof v !== "object" || Array.isArray(v)) { return { ok: false, hata: "parametre-tarih" }; }
          var utcf = v.utc_ofset_saat;
          if (typeof utcf !== "number" || !isFinite(utcf) || utcf < -12 || utcf > 14) { return { ok: false, hata: "parametre-tarih" }; }
          cikti[a] = { tarih: trhSonuc.iso, saat: satStr, utc_ofset_saat: utcf };
        } else {
          cikti[a] = trhSonuc.iso;
        }
        continue;
      }
      cikti[a] = v;
    }
    return { ok: true, deger: cikti };
  };
  // "YYYY-AA-GG" -> {iso, hata}; takvim geçerli (1900..2100). Hata varsa iso boş.
  VERI.tarihCozumle = function (s) {
    if (typeof s !== "string") { return { hata: "tarih-bicim" }; }
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (!m) { return { hata: "tarih-bicim" }; }
    var y = +m[1], ay = +m[2], g = +m[3];
    if (y < 1900 || y > 2100) { return { hata: "tarih-yil" }; }
    if (ay < 1 || ay > 12) { return { hata: "tarih-ay" }; }
    if (g < 1 || g > 31) { return { hata: "tarih-gun" }; }
    var d = new Date(Date.UTC(y, ay - 1, g));
    if (d.getUTCFullYear() !== y || d.getUTCMonth() !== ay - 1 || d.getUTCDate() !== g) {
      return { hata: "tarih-gecersiz" };
    }
    return { iso: s };
  };
  // Türün ölçü aralığı (mm, uzun kenar); bilinmeyen tür -> null. Bölüm ve sunucu AYNI fonksiyon.
  VERI.olcuAraligi = function (kod) {
    var t = VERI.turBul(kod);
    if (!t || !t.olcu_mm || !(t.olcu_mm.en_az > 0) || !(t.olcu_mm.en_cok >= t.olcu_mm.en_az)) { return null; }
    return { en_az: t.olcu_mm.en_az, en_cok: t.olcu_mm.en_cok };
  };

  // ---- FİYAT: TEK FORMÜL (Okan 7 Eki 15:4x) — istemci, sunucu ve araçlar YALNIZ bunu çağırır ----
  // Formül adı -> mm başına kuruş. "mm_x_10tl" = mm × 10 TL = cm × 100 TL.
  VERI.FIYAT_FORMULLERI = { mm_x_10tl: 1000 };
  // Türün sürgü adımı (mm); kayıt yoksa/bozuksa null.
  VERI.olcuAdimi = function (kod) {
    var t = VERI.turBul(kod);
    var adim = t && t.fiyat ? t.fiyat.adim_mm : null;
    return Number.isInteger(adim) && adim > 0 ? adim : null;
  };
  // TÜRETİLMİŞ ölçü ekseni (kopru-15 dilim-3): sürgü yok, ölçü önizlemede ÖLÇÜLÜR (kayıt alanı olcu_ekseni).
  VERI.olcuTuretilmis = function (kod) {
    var t = VERI.turBul(kod);
    return !!t && t.olcu_ekseni === "turetilmis";
  };
  // Ölçülen uzun kenar (mm, ondalıklı) -> fiyatlanan ölçü (tam mm, yarım yukarı). Köprü D1'e BUNU yazar.
  VERI.olculenMm = function (uk) {
    return typeof uk === "number" && isFinite(uk) && uk > 0 ? Math.floor(uk + 0.5) : null;
  };
  // Bölüm metni: türetilmiş türde fiyatın kaynağı (dürüstlük; sürgünün yerinde ve önizlemeyle birlikte).
  VERI.OLCULEN_FIYAT_NOTU = "Bu türde ölçüyü sen seçmezsin: girdiğin değerlerden önizleme üretilir, fiyat " +
    "önizlemede ölçülen en uzun boyuttan (mm × 10 TL, en az 600 TL) hesaplanır ve önizlemeyle birlikte gösterilir.";
  // Ölçü (en uzun boyut, mm) bu türde seçilebilir mi: tam sayı, aralıkta, adım ızgarasında
  // (türetilmiş eksende ölçü ölçülür, seçilmez -> ızgara aranmaz; aralık yine şart).
  VERI.olcuGecerli = function (kod, mm) {
    var a = VERI.olcuAraligi(kod), adim = VERI.olcuAdimi(kod);
    if (!a || !adim || !Number.isInteger(mm) || mm < a.en_az || mm > a.en_cok) { return false; }
    return VERI.olcuTuretilmis(kod) || (mm - a.en_az) % adim === 0 || mm === a.en_cok;
  };
  // TABAN (Okan 8 Eki 13:2x: "tüm ürünlerde min fiyat 600 olmalı" — kapsam foto programı, Okan teyidi):
  // türün fiyat.taban_tl'si kuruşa; yoksa/bozuksa null -> tür FİYATSIZ kalır, sunulmaz (fail-closed: tabansız
  // satış yok).
  VERI.fiyatTabanKurus = function (kod) {
    var t = VERI.turBul(kod);
    var tl = t && t.fiyat ? t.fiyat.taban_tl : null;
    return Number.isInteger(tl) && tl > 0 ? tl * 100 : null;
  };
  // EK RENK (Okan 8 Eki 13:3x: "4 renk seçimi olmalı, ilk renk ücretsiz, her + renk için +100 TL"):
  // türün fiyat.ek_renk_tl'si kuruşa; yoksa/bozuksa null -> tür FİYATSIZ (fail-closed, taban ile aynı desen).
  VERI.ekRenkKurus = function (kod) {
    var t = VERI.turBul(kod);
    var tl = t && t.fiyat ? t.fiyat.ek_renk_tl : null;
    return Number.isInteger(tl) && tl >= 0 ? tl * 100 : null;
  };
  // Türde seçilebilecek en çok renk (1–4, AMS 4 yuva); yoksa/bozuksa null -> tür FİYATSIZ.
  VERI.renkTavani = function (kod) {
    var t = VERI.turBul(kod);
    var n = t && t.fiyat ? t.fiyat.renk_tavani : null;
    return Number.isInteger(n) && n >= 1 && n <= 4 ? n : null;
  };
  // Müşteri renkleri paletten mi seçer (renk_secimi "palet"), yoksa bölge seçimlerinden mi sayılır.
  VERI.renkPaleti = function (kod) {
    var t = VERI.turBul(kod);
    return !!t && t.renk_secimi === "palet";
  };
  // Palet = manifestteki bölge renk listelerinin birleşimi (mevcut PLA paleti; ikinci liste değil, aynı 9 renk).
  VERI.PLA_RENKLERI = ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"];
  // fiyat_kurus = max(taban, en uzun boyut (mm) × formülün mm başı kuruşu) + (renk − 1) × ek_renk.
  // renk verilmezse 1 (vitrin "₺N'dan itibaren" ve sürgü satırı). Geçersiz ölçü / bilinmeyen formül / taban
  // yok / ek renk ya da tavan yok / renk tam sayı değil, 1'den küçük ya da tavandan büyük -> null.
  VERI.fiyatKurus = function (kod, mm, renk) {
    var t = VERI.turBul(kod);
    var f = t && t.fiyat && Object.prototype.hasOwnProperty.call(VERI.FIYAT_FORMULLERI, t.fiyat.formul)
      ? VERI.FIYAT_FORMULLERI[t.fiyat.formul] : null;
    var taban = VERI.fiyatTabanKurus(kod), ek = VERI.ekRenkKurus(kod), tavan = VERI.renkTavani(kod);
    var n = renk === undefined ? 1 : renk;
    if (!f || taban === null || ek === null || tavan === null || !VERI.olcuGecerli(kod, mm)) { return null; }
    if (!Number.isInteger(n) || n < 1 || n > tavan) { return null; }
    return Math.max(mm * f, taban) + (n - 1) * ek;
  };
  // Sürgünün seçebildiği ölçüler: en_az..en_cok, adım adım (en_cok her zaman dahil).
  VERI.olcuSecenekleri = function (kod) {
    var a = VERI.olcuAraligi(kod), adim = VERI.olcuAdimi(kod), c = [];
    if (!a || !adim) { return c; }
    for (var mm = a.en_az; mm <= a.en_cok; mm += adim) { c.push(mm); }
    if (c[c.length - 1] !== a.en_cok) { c.push(a.en_cok); }
    return c;
  };
  // Kuruş -> "1.200 TL" (TR biçim, binlik nokta; kuruş varsa ",50").
  VERI.tlMetni = function (kurus) {
    if (!Number.isInteger(kurus) || kurus < 0) { return ""; }
    var tl = Math.floor(kurus / 100), k = kurus % 100;
    var s = String(tl).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return s + (k ? "," + (k < 10 ? "0" : "") + k : "") + " TL";
  };
  // Sürgü yazısı: "120 mm → 1.200 TL"; geçersiz ölçüde "".
  VERI.fiyatSatiri = function (kod, mm) {
    var k = VERI.fiyatKurus(kod, mm);
    return k == null ? "" : mm + " mm → " + VERI.tlMetni(k);
  };

  kok.PRUVO_FOTO = VERI;
})(typeof globalThis !== "undefined" ? globalThis : this);
