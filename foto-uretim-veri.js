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
    //                    {tip:"secim",secenekler:[..]} | {tip:"metin",max} | {tip:"url"} }; {} = parametre yok
    //   fiyat          : { formul: "mm_x_10tl", adim_mm } — formül adı VERI.FIYAT_FORMULLERI'nde
    //                    olmalı (bilinmeyen formül -> fiyat yok, tür sunulmaz); adim_mm = sürgü adımı
    //   olcu_mm        : {en_az, en_cok} — en uzun boyut (mm); bu aralık dışı ölçü RED
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
        olcu_mm: { en_az: 60, en_cok: 300 },
        renk_bolgeleri: [],
        malzemeler: {},
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
        // Okan kararı 7 Eki 2026: plaket gerçek baskı beklemeden önizleme + render ile açılır.
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Önizleme, fotoğrafının stilize bir yorumudur. Ürün en çok 4 renkle kabartma olarak üretilir — önizlemenin 4 renkli yorumu; birebir aynısı değildir, küçük yazı ve ince ayrıntılar sadeleşir.",
        ornek_notu: "Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun kabartmalı hâlidir, birebir aynısı değildir."
      },
      {
        kod: "litofan",
        ad: "Işıklı fotoğraf paneli (litofan)",
        aciklama: "Fotoğrafın ince bir panele kalınlık farkıyla işlenir; arkadan ışık gelince görünür. Ayağıyla masada durur.",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "litofan_uret",
        olcu_mm: { en_az: 80, en_cok: 200 },
        renk_bolgeleri: [
          { kod: "panel", ad: "Işık geçen panel", renkler: ["Beyaz"] },
          { kod: "ayak", ad: "Ayak", renkler: ["Beyaz", "Siyah", "Gri"] }
        ],
        // ABS YOK: litofan Dekorasyon sınıfıdır (secenekler.js FILAMENT_KATEGORI_HARIC).
        malzemeler: { panel: ["PLA", "PETG"], ayak: ["PLA", "PETG", "ASA"] },
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
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
        olcu_mm: { en_az: 60, en_cok: 250 },
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
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
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
        olcu_mm: { en_az: 40, en_cok: 150 },
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
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
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
        olcu_mm: { en_az: 30, en_cok: 200 },
        renk_bolgeleri: [
          { kod: "taban", ad: "Taban", renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"] },
          { kod: "logo", ad: "Logo", renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"] }
        ],
        malzemeler: { taban: ["PLA", "PETG"] },
        form: {
          taban: { tip: "secim", etiket: "Taban plakası", secenekler: ["Var", "Yok"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
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
        olcu_mm: { en_az: 20, en_cok: 100 },
        renk_bolgeleri: [
          { kod: "govde", ad: "Gövde", renkler: ["Mavi", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Gri", "Beyaz", "Sarı", "Ahşap"] },
          { kod: "sap", ad: "Sap", renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"] }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          sap: { tip: "secim", etiket: "Sap", secenekler: ["Silindir", "Topuz"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
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
        olcu_mm: { en_az: 60, en_cok: 250 },
        renk_bolgeleri: [
          { kod: "sablon", ad: "Şablon", renkler: ["Gri", "Beyaz", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Sarı", "Ahşap"] }
        ],
        malzemeler: { sablon: ["PLA", "PETG"] },
        form: {
          mod: { tip: "secim", etiket: "Şablon türü", secenekler: ["Delikli", "Dolu silüet"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
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
        olcu_mm: { en_az: 100, en_cok: 190 },
        renk_bolgeleri: [
          { kod: "yapboz", ad: "Yapboz", renkler: ["Ahşap", "Beyaz", "Gri", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"] }
        ],
        malzemeler: { yapboz: ["PLA", "PETG"] },
        form: {
          parca: { tip: "secim", etiket: "Parça sayısı", secenekler: ["12", "20", "30"] }
        },
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Yapboz tek renkli kabartmadır; renkli baskı değildir. Parçalar elle takılır; çocuk oyuncağı olarak belgelendirilmemiştir.",
        ornek_notu: "Üretim dosyasının görüntüsüdür; fotoğrafın açık-koyu tonları kabartma yüksekliğine çevrilir."
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
  VERI.FORM_TIPLERI = { sayi: true, secim: true, metin: true, url: true, ses: true, konum: true, tarih: true };

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
      // `zorunlu: false` (yalnız metin): boş/yok -> alan çıktıya GİRMEZ (üreteç varsayılanı).
      if (sema.zorunlu === false && sema.tip === "metin" && (v === undefined || v === "")) { continue; }
      if (sema.tip === "sayi") {
        if (typeof v !== "number" || !isFinite(v) || v < sema.min || v > sema.max) { return { ok: false, hata: "parametre-aralik" }; }
        var adim = sema.adim > 0 ? sema.adim : 1;
        var k = (v - sema.min) / adim;
        if (Math.abs(k - Math.round(k)) > 1e-9) { return { ok: false, hata: "parametre-adim" }; }
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
  // Ölçü (en uzun boyut, mm) bu türde seçilebilir mi: tam sayı, aralıkta, adım ızgarasında.
  VERI.olcuGecerli = function (kod, mm) {
    var a = VERI.olcuAraligi(kod), adim = VERI.olcuAdimi(kod);
    if (!a || !adim || !Number.isInteger(mm) || mm < a.en_az || mm > a.en_cok) { return false; }
    return (mm - a.en_az) % adim === 0 || mm === a.en_cok;
  };
  // fiyat_kurus = en uzun boyut (mm) × formülün mm başı kuruşu. Geçersiz ölçü / bilinmeyen formül -> null.
  VERI.fiyatKurus = function (kod, mm) {
    var t = VERI.turBul(kod);
    var f = t && t.fiyat && Object.prototype.hasOwnProperty.call(VERI.FIYAT_FORMULLERI, t.fiyat.formul)
      ? VERI.FIYAT_FORMULLERI[t.fiyat.formul] : null;
    if (!f || !VERI.olcuGecerli(kod, mm)) { return null; }
    return mm * f;
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
