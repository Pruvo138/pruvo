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
 *     plakette `kanit: "render"` kaydı da sayılır; bölüm onu "Örnek görsel (bilgisayar çizimi)" etiketiyle ve
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
            "olarak üretilir; tam kopyası değildir, küçük yazı ve ince " +
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
    //   girdi          : [GIRDI_TURLERI anahtarı...] — "foto-1" tek fotoğraf, "foto-1-3" 1–3 fotoğraf, "metin"
    //                    form'un metin alanları. Liste "EN AZ BİRİ" demektir (anahtarlık 9 Eki: foto VEYA yazı,
    //                    ikisi birden de olur): ② "İleri" ve sunucu girdi kapısı AYNI VERI.girdiYeterli'yi çağırır.
    //   motor          : "M" = önizleme+üretim dış hizmetle (kredi harcar; kol "saglayici");
    //                    "D" / "R" = deterministik / ölçüden üretim — önizleme tarayıcıda ya da
    //                    üreteçte, üretim dosyasını bizim üretecimiz çıkarır (kol "deterministik")
    //   uretec         : üreteç komut kimliği (D/R'de DOLU, M'de "")
    //   form           : parametre şeması { anahtar: {tip:"sayi",min,max,adim,birim} |
    //                    {tip:"secim",secenekler:[..]} | {tip:"bool",etiket,varsayilan} }; {} = parametre yok
    //                    (③ çizimi: sayi -> sürgü + canlı değer, bool -> aç/kapa düğmesi; isteğe bağlı `aciklama`
    //                    alanın altında yazar)
    //                    TeKiN köprü türlerinin (kopru_kayitlari.json) satırları ELLE YAZILMAZ: TÜRETİLEN
    //                    alanlar (girdi, uretec, olcu_mm, renk_bolgeleri, malzemeler, form, fiyat.adim_mm)
    //                    tools/kopru-manifest-uret.py --yaz ile üretilir, --denetle sapmayı KIRMIZI yakar;
    //                    sözlük (olcu->form, tam->adim 1, sayi->adim 0.01, renk->bölge, kosul aynen) orada.
    //                    kosul: [{alan, degerler}] — alan YALNIZ her koşul sağlanınca vardır (VERI.alanAktif)
    //   fiyat          : { formul: "mm_x_10tl", adim_mm, taban_tl, renk_tavani } — formül adı
    //                    VERI.FIYAT_FORMULLERI'nde olmalı (bilinmeyen formül -> fiyat yok, tür sunulmaz); adim_mm =
    //                    sürgü adımı; taban_tl = en düşük fiyat (Okan 8 Eki: 600), yoksa fiyat yok, tür sunulmaz;
    //                    renk_tavani = 1–4 (AMS 4 yuva) = "Renkli"de fotoğraftan seçilen en çok renk — yoksa/bozuksa
    //                    fiyat yok, tür sunulmaz. Renk ADEDİ fiyata GİRMEZ (Okan 9 Eki): renk 3 ana renkten biri
    //                    (tek renk) ya da "Renkli" (+%15); malzeme PLA ya da PETG (+%30) — VERI.RENK_SECENEKLERI/MALZEMELER.
    //   renk_secimi    : "palet" = renkler VERI.PLA_RENKLERI'nden 1..renk_tavani (ana renkte tek renk, Renkli'de
    //                    fotoğraftan otomatik); alan yoksa renkler renk_bolgeleri'nde (ana renkte tüm bölgeler o renk)
    //                    RENK TAVANI (BaBa 8 Eki 15:4x): renk_tavani = üretecin BOYANABİLİR renk_* parametre sayısı
    //                    (köprü türlerinde kopru-manifest-uret.py --denetle ölçer); palet türünde sağlayıcı kolu 4.
    //   renk_kosul     : {bölge: [{alan, degerler} | {alan, dolu: true}]} — bölge YALNIZ koşul sağlanınca üretilir;
    //                    pasif bölgenin rengi seçicide GİZLİ ve renk sayısına (para) GİRMEZ (VERI.renkBolgesiAktif).
    //                    Ücret alınan her renk üretime bağlı: tools/renk-esleme-test.py esle_<kod> dönüşüyle ölçer.
    //   palet_bolgeleri: palet türü deterministik üreteçle basılıyorsa renkler[i] -> palet_bolgeleri[i]
    //                    (K3a: kalan 4 türde kullanılmıyor; köprü türlerinde köprü ÜRETİR).
    //   olcu_mm        : {en_az, en_cok[, baslangic]} — en uzun boyut (mm); bu aralık dışı ölçü RED. baslangic =
    //                    sürgünün AÇILIŞ ölçüsü (yoksa en_az; VERI.olcuBaslangic). Anahtarlık (Okan 10 Eki 15:2x
    //                    "min 30 – max 300", açılış 60): kopru-manifest-uret PRUVO_ARALIK köprüyü yalnız DARALTIR
    //                    -> en_cok = min(300, köprü); köprü bugün 80 -> 80.
    //   olcu_ekseni    : "sabit" (sürgü = hedef ölçü) | "turetilmis" (köprü kaydında belirleyen parametre YOK:
    //                    sürgü YOK, ölçü form parametrelerinden doğar; fiyat = önizlemede ÖLÇÜLEN uzun kenar ×
    //                    formül — köprü ölçüyü D1 foto_isler.olcu_mm'ye yazar, sunucu ORADAN hesaplar; alan
    //                    yoksa "sabit"). TeKiN köprü türlerinde kopru-manifest-uret.py ÜRETİR.
    //   renk_bolgeleri : müşterinin renk seçtiği bölgeler; [] = seçim yok (plaket: önizlemenin 4 renkli yorumu)
    //   malzemeler     : bölge -> izinli filament listesi; {} = satır "PLA" (plaket)
    //   ornek_kanit_izni: türü AÇAN örnek kanıtları; listede olmayan kanıt o türde SAYILMAZ
    //                    (alan yoksa/boşsa hiçbir örnek sayılmaz — fail-closed)
    //   form_sunum     : {alan: {deger: "olcu" | "varsayilan"}} — alan ③'te ÇİZİLMEZ, değeri Ölçü sürgüsünden ya da
    //                    form varsayılanından gövdeye girer (köprü `form`u değişmeden sunum; VERI.formSunumDegeri)
    //   alan_aciklamalari: {renk, olcu, malzeme} — ③ ortak alanların altındaki tür cümlesi (yoksa genel cümle)
    //   durustluk      : bölümün üst dürüstlük kutusu (tür bazlı, ZORUNLU; seçili türün metni basılır)
    //   ornek_notu     : render örneğinin altındaki dürüstlük cümlesi (tür bazlı; mimar kararı 7 Eki,
    //                    AYNEN). Alan YOKSA bölüm o türün render örneğini ÇİZMEZ; yeni tür yazmak ZORUNDA.
    //                    "" = ayrı cümle YOK: ② dürüstlük kutusunda TEK cümle (`durustluk`; BaBa 10 Eki 14:0x,
    //                    figür + plaket — ArTisT stilize-yorum cümlesi render notunu da kapsar).
    // Litofan, gerçek örneği ve açılış anahtarı olmadıkça AÇILMAZ (fail-closed, plaketle aynı kural).
    turler: [
      {
        kod: "plaket",
        ad: "Kabartma plaket",
        aciklama: "Fotoğrafındaki konunun kabartmalı plaketi; ayağıyla masada durur.",
        girdi: ["foto-1"],
        motor: "M",
        uretec: "",
        // Okan 6 Eki 2026: "min 60 max 300"; Okan 10 Eki ~13:4x: "plaket de 60 mm olsun" (en_cok 300 aynen).
        olcu_mm: { en_az: 60, en_cok: 300 },
        renk_bolgeleri: [],
        renk_secimi: "palet",
        malzemeler: {},
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, renk_tavani: 4 },
        // Okan kararı 7 Eki 2026: plaket gerçek baskı beklemeden önizleme + render ile açılır.
        ornek_kanit_izni: ["baski", "render"],
        // ③ ortak alan açıklamaları — ArTisT 10 Eki 2026 AYNEN; yalnız plakette (büstün cümleleri değişmez).
        alan_aciklamalari: {
          renk: "Siyah, Beyaz ya da Gri seçersen plaket tek renk olur; Renkli seçersen renkler fotoğrafından otomatik seçilir (en çok 4 renk).",
          olcu: "Plaketin en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.",
          malzeme: "PLA ev içi kullanım içindir; PETG dış mekân ve genel amaçlı kullanım için daha yüksek sıcaklığa dayanır (+%30)."
        },
        // ② TEK cümle (BaBa 10 Eki 14:0x; ArTisT sayfa metni "② stilize-yorum dürüstlük cümlesi" AYNEN).
        durustluk: "Önizleme fotoğrafının stilize bir yorumudur; basılmış plaket en çok 4 renkli, kabartmalı ve sadeleştirilmiş bir hâlidir, tam kopyası değildir (küçük yazı ve ince ayrıntılar sadeleşir).",
        ornek_notu: ""
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
        // Okan 10 Eki 12:4x: "slider figürlerde 60mm den başlasın".
        olcu_mm: { en_az: 60, en_cok: 200 },
        renk_bolgeleri: [],
        renk_secimi: "palet",
        malzemeler: {},
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, renk_tavani: 4 },
        // Plaketle AYNI izin (render gerçek baskı olmadan açılır; Okan 7 Eki kararı).
        ornek_kanit_izni: ["baski", "render"],
        // Dürüstlük: figür metni — stilize yorum, en çok 4 renk, tam kopya değil (madde 5: insan/hayvan ortak, yüz benzerliği iddiası yok).
        durustluk: "Önizleme fotoğrafının stilize bir yorumudur; basılmış figür en çok 4 renkli, sadeleştirilmiş bir hâlidir ve tam kopyası değildir (küçük ayrıntılar sadeleşir).",
        ornek_notu: ""
      },
      
      // G2 (7 Eki 2026, mimar kararı) — 6 D türü; üreteçler pruvo-jenerator (G1-SEMA/G2-SEMA).
      // Tarayıcı önizleyicisi YOK -> sipariş öncesi önizlemeyi üreteç koşucusu çıkarır. Renk adı ->
      // filament hex'i RENK_HEX'ten (tek tablo). Malzeme TÜM ürün için tek seçimdir (ilk bölgenin
      // anahtarıyla): yığılı gövdelerde karışık malzeme yapışmaz. Örneği olmadıkça tür AÇILMAZ.
      
      
      
      
      
      // yapboz `alan_aciklamalari` (③ ortak alan açıklamaları) — ArTisT 10 Eki 2026 AYNEN; yalnız yapbozda
      // (büstün cümleleri değişmez). Satır içinde yorum tutulmaz: kopru-manifest-uret --yaz satırı bütün yeniden yazar.
      {
        kod: "yapboz",
        ad: "Fotoğraftan kabartma yapboz",
        aciklama: "Fotoğrafının açık-koyu tonları kabartmaya çevrilir ve geçmeli yapboz parçalarına bölünür.",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "yapboz_uret",
        olcu_mm: { en_az: 100, en_cok: 280 },
        renk_bolgeleri: [],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          uzun_kenar_mm: {
            tip: "sayi",
            etiket: "Uzun kenar (plaket)",
            min: 100,
            max: 280,
            adim: 0.01,
            varsayilan: 150,
            birim: "mm",
            zorunlu: true,
            ornek: 150
          },
          satir: {
            tip: "sayi",
            etiket: "Satır (parça sayısı dikey)",
            aciklama: "Yapbozun dikey kaç parçaya bölüneceği.",
            min: 3,
            max: 8,
            adim: 1,
            varsayilan: 3,
            birim: "adet",
            ornek: 3
          },
          sutun: {
            tip: "sayi",
            etiket: "Sütun (parça sayısı yatay)",
            aciklama: "Yapbozun yatay kaç parçaya bölüneceği.",
            min: 3,
            max: 8,
            adim: 1,
            varsayilan: 4,
            birim: "adet",
            ornek: 4
          },
          tohum: {
            tip: "sayi",
            etiket: "Tohum (kesim yönü/konumu)",
            min: 0,
            max: 2147483647,
            adim: 1,
            varsayilan: 1,
            ornek: 1
          },
          kabartma_yon: {
            tip: "secim",
            etiket: "Kabartma yönü",
            aciklama: "Fotoğrafın hangi tonlarının daha çok kabaracağını belirler.",
            secenekler: ["acik_yuksek", "koyu_yuksek"],
            varsayilan: "acik_yuksek",
            ornek: "acik_yuksek"
          }
        },
        fiyat: {
          formul: "mm_x_10tl",
          adim_mm: 10,
          taban_tl: 600,
          renk_tavani: 4
        },
        ornek_kanit_izni: ["baski", "render"],
        alan_aciklamalari: {
          renk: "Siyah, Beyaz ya da Gri seçersen tüm parçalar o renk olur; Renkli seçersen parça renkleri fotoğrafından otomatik belirlenir (en çok 4 renk).",
          olcu: "Yapbozun en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.",
          malzeme: "PLA ev içi kullanım içindir; PETG dış mekân ve genel amaçlı kullanım için daha yüksek sıcaklığa dayanır (+%30)."
        },
        form_sunum: {
          uzun_kenar_mm: { deger: "olcu" },
          tohum: { deger: "varsayilan" }
        },
        durustluk: "Her yapboz parçası tek renktir. Siyah, Beyaz ya da Gri seçersen tüm parçalar o renk olur; Renkli seçersen parça renkleri fotoğrafından otomatik belirlenir (en çok 4 renk).",
        ornek_notu: "Üretim dosyasının görüntüsüdür; fotoğrafın açık-koyu tonları kabartma yüksekliğine çevrilir.",
        olcu_ekseni: "sabit",
        renk_secimi: "palet",
        palet_bolgeleri: ["renk1", "renk2", "renk3", "renk4"]
      },
      // ANAHTARLIK (K3c; Okan 22:5x/23:0x: kulakçık, metal halka YOK, taban ₺600) — TeKiN köprü kaydı
      // (isimlik_uret, anahtarlik:true sabiti). Metinler ArTisT tür #5 + tür notu #5 BİREBİR. Örnek kaydı VAR
      // (TeKiN 9 Eki 10:58, render): sayılan örnek 1, tür /acik'e girer, kart normal çizilir. C2 (10 Eki):
      // alan_aciklamalari.olcu = ③ Ölçü cümlesi (iki çeşit ortak; ArTisT "③ Ölçü cümlesi — anahtarlık" AYNEN).
      {
        kod: "anahtarlik",
        ad: "Anahtarlık",
        aciklama: "Fotoğraf ya da metin/logodan anahtarlık. Metal halka ve zincir dahil değildir; zincir ya da halka takılan kulakçıklı plastik gövde (delik Ø 3,5–4 mm).",
        girdi: ["metin"],
        motor: "D",
        uretec: "isimlik_uret",
        olcu_mm: { en_az: 30, en_cok: 80, baslangic: 60 },
        renk_bolgeleri: [
          {
            kod: "plaka",
            ad: "Taban",
            renkler: ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
          },
          {
            kod: "yazi",
            ad: "Yazı",
            renkler: ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
          }
        ],
        malzemeler: { govde: ["PLA", "PETG"] },
        form: {
          satirlar: {
            tip: "metin",
            etiket: "Yazı (tek satır önerilir; en çok 3 satır)",
            liste: true,
            satir_max: 3,
            max: 40,
            zorunlu: true,
            ornek: ["Ayşe"]
          },
          yazi_tipi: {
            tip: "secim",
            etiket: "Yazı tipi",
            secenekler: ["sans-kalin", "script"],
            varsayilan: "script",
            ornek: "script"
          },
          hizalama: {
            tip: "secim",
            etiket: "Hizalama (çok satır)",
            secenekler: ["sol", "orta", "sag"],
            varsayilan: "orta"
          },
          genislik_mm: {
            tip: "sayi",
            etiket: "Uzun kenar (kulak dahil)",
            min: 30,
            max: 80,
            adim: 0.01,
            varsayilan: 60,
            birim: "mm",
            zorunlu: true,
            ornek: 60
          },
          anahtarlik_kulak_konum: {
            tip: "secim",
            etiket: "Kulak konumu",
            secenekler: ["sol-ust", "sag-ust", "ust-orta"],
            varsayilan: "sol-ust",
            ornek: "sol-ust"
          },
          kontur_tasma_mm: {
            tip: "sayi",
            etiket: "Taban taşma (yazı çevresi)",
            min: 1,
            max: 3,
            adim: 0.01,
            varsayilan: 1.5,
            birim: "mm",
            ornek: 1.5
          }
        },
        fiyat: {
          formul: "mm_x_10tl",
          adim_mm: 5,
          taban_tl: 600,
          renk_tavani: 2
        },
        ornek_kanit_izni: ["render"],
        alan_aciklamalari: {
          olcu: "Anahtarlığın kulakçık dahil en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır."
        },
        durustluk: "Metal halka ve zincir dahil değildir; zincir ya da halka takılan kulakçıklı plastik gövde (delik Ø 3,5–4 mm).",
        ornek_notu: "Üretim dosyasının görüntüsüdür; yazı, renk ve kulak konumu seçimine göre üretilir.",
        olcu_ekseni: "sabit",
        foto_kolu: {
          girdi: ["foto-1"],
          uretec: "figur_kulak",
          olcu_en_az: 60,
          olcu_en_cok: 72,
          renk_bolgesi: 0
        }
      },
      
      
      
      
      
      
      
      
      
      {
        kod: "bust",
        ad: "Bust/madalyon (rolyef)",
        aciklama: "Fotoğraftan kabartma büst/madalyon (ters opsiyonel).",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "rolyef_uret",
        olcu_mm: { en_az: 60, en_cok: 250 },
        renk_bolgeleri: [],
        renk_secimi: "palet",
        malzemeler: { govde: ["PLA", "PETG"] },
        // Okan 9 Eki 20:2x: "Boyut" alanı YOK (üretece Ölçü sürgüsünün olcu_mm'si gider, esle_rolyef) · "İki renk" YOK
        // (Renkli seçilince taban + kabartma iki renk OTOMATİK, esle_bust ödenen renklerden zorlar; tavan 2) ·
        // kabartma sürgü adımı 0,5 mm (1–8 aralığında 15 kademe; 0,01 sürgüde ayırt edilemez), varsayılan 3 mm (Okan ekranı).
        form: {
          rolyef_yuksekligi_mm: {
            tip: "sayi",
            etiket: "Kabartma yüksekliği",
            aciklama: "Yüzün yüzeyden ne kadar dışarı çıkacağı; yüksek değer daha belirgin, daha kırılgan.",
            min: 1,
            max: 8,
            adim: 0.5,
            varsayilan: 3,
            birim: "mm",
            ornek: 3
          },
          ters: {
            tip: "bool",
            etiket: "Ters (negatif)",
            aciklama: "Açıkken görüntü yüzeye kabartma yerine içe oyulur (kalıp/damga görünümü).",
            varsayilan: false,
            ornek: false
          }
        },
        fiyat: {
          formul: "mm_x_10tl",
          adim_mm: 10,
          taban_tl: 600,
          renk_tavani: 2
        },
        palet_bolgeleri: ["taban", "rolyef"],
        ornek_kanit_izni: ["baski", "render"],
        // ③ ortak alan açıklamaları + tür notu #4: ArTisT b25b2804 AYNEN (yalnız büstte; başka türün metni değişmez).
        alan_aciklamalari: {
          renk: "Siyah, Beyaz ya da Gri seçersen büst tek renk olur; Renkli seçersen renkler fotoğrafından otomatik seçilir (büstte en çok 2 renk).",
          olcu: "Büstün en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.",
          malzeme: "PLA ev içi kullanım içindir; PETG dış mekân ve genel amaçlı kullanım için daha yüksek sıcaklığa dayanır (+%30)."
        },
        durustluk: "Siyah, Beyaz ya da Gri seçilirse büst tek renktir; Renkli seçilirse taban + kabartma olmak üzere en çok 2 renk fotoğraftan otomatik belirlenir.",
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
      "kopru": "Görseldeki iç adalar şablona bağlanamadı; daha sade bir silüet dene.",
      // Anahtarlık FOTO kolu (plaket_kulak rc 2: plaket uzun kenarı >50 mm ya da kulak yerleşmedi) — BİREBİR.
      "anahtarlik-boyut": "Bu fotoğraftan anahtarlık boyutunda bir parça çıkmadı; daha sade bir fotoğraf ya da kısa bir yazı deneyin."
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
        tur: "yapboz",
        kanit: "render",
        olcu_mm: 150,
        onizleme: "https://media.pruvo3d.com/foto/ornek/yapboz-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/yapboz-1-render.webp",
        not: "150 mm, 20 parça"
      },
      
      
      
      
      
      
      
      
      
      {
        tur: "bust",
        kanit: "render",
        olcu_mm: 100,
        onizleme: "https://media.pruvo3d.com/foto/ornek/bust-2-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/bust-2-render.webp",
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
      },
      {
        tur: "anahtarlik",
        // Çeşit (Okan 10 Eki): ② "Önizlemeden sonra" Örnek'i yalnız bu çeşitte çizilir (yazı örneği figürde ÇIKMAZ).
        cesit: "yazi",
        kanit: "render",
        olcu_mm: 45,
        onizleme: "https://media.pruvo3d.com/foto/ornek/anahtarlik-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/anahtarlik-1-render.webp",
        not: "45 mm, kulakçıklı, metin: Ayşe"
      }
    ],

    // Ziyaretçi başına 24 saatte en çok kaç önizleme (sunucu da AYNI sayıyı uygular).
    sinir_ziyaretci_24s: 3,

    // Önizleme kaç saat içinde siparişe dönüşebilir (sunucu sınırı; bölüm müşteriye söyler).
    gecerlilik_saat: 48
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
    if (o.cesit !== undefined && !VERI.cesitKaydi(o.tur, o.cesit)) { return false; }
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
  // Aydınlatma maddeleri türün motoruna göre: kol "M" maddesi yalnız M motorlu türde gösterilir.
  VERI.aydinlatmaMaddeleri = function (kod) {
    var t = VERI.turBul(kod);
    var m = t ? t.motor : "";
    return VERI.onay.aydinlatma.filter(function (x) { return !x.kol || x.kol === m; })
      .map(function (x) { return x.metin; });
  };
  // Üreteç reddinin müşteri metni: hata "uretec-red:<kod>" -> tablo; bilinmeyen kod -> genel metin.
  VERI.uretecRedMetni = function (hata) {
    // DİNAMİK MİN (köprü türleri): koşucu köprü min-hesapla'dan `uretec-red:olcu-min-<N>` yazar.
    var d = /^uretec-red:olcu-min-([1-9][0-9]{0,3})$/.exec(typeof hata === "string" ? hata : "");
    if (d) { return "Bu içerik için en az " + d[1] + " mm gerekiyor; ölçüyü " + d[1] + " mm ya da üstüne çıkarıp tekrar dene."; }
    var m = /^uretec-red:([a-z0-9-]{1,40})$/.exec(typeof hata === "string" ? hata : "");
    var k = m && Object.prototype.hasOwnProperty.call(VERI.URETEC_RED_METIN, m[1]) ? m[1] : "";
    return VERI.URETEC_RED_METIN[k];
  };

  // GİRDİ TÜRLERİ — K3a: foto-* girdileri; K3c: metin (anahtarlık — yazı form alanından, fotoğraf YOK).
  VERI.GIRDI_TURLERI = {
    "foto-1": { acik: true }, "foto-1-3": { acik: true, en_cok: 3 }, metin: { acik: true }
  };
  VERI.FORM_TIPLERI = { sayi: true, secim: true, metin: true, bool: true };
  var FOTO_GIRDILERI = { "foto-1": true, "foto-1-3": true };
  // ÇEŞİTLER (Okan 22:0x anahtarlık "a yazı ile, b figür olarak"; TUR-C2a 10 Eki): türün ② başındaki çeşit seçimi.
  // Kalıcı yer D1 `foto_isler.cesit` ('' = türün varsayılan kolu). Metinler pazarlama sayfa metni satır 16–17 AYNEN.
  //   acik    : false = çeşit sunulmaz; sunucu müşteri isteğini `cesit-yakinda` ile AÇIKÇA reddeder (sessiz değil)
  //   girdi   : çeşidin girdi listesi (yoksa türün `girdi`si); figür = fotoğraf, yazı formu YOK (parametre 0)
  //   olcu_en_az  : çeşidin ölçü tabanı (tür en_az'ından büyükse). Figür: köprüden TÜRER = foto_kolu.olcu_en_az
  //                 (max(tür 30, köprü figür kolu min_mm 60) = 60; yerel prova 10 Eki: 30 mm z-yönelimli figürde
  //                 sırt kulak dahil 31,0 mm -> olcu-tutmadi). Okan "figür 30" köprü kolu inince açılır (TeKiN).
  //   olcu_en_cok : çeşidin ölçü tavanı. Figür: köprüden TÜRER (elle sayı YOK) = türün foto_kolu.olcu_en_cok
  //                 (kopru-manifest-uret kol_tavani: min(300, köprü kol max, figur_kulak çıplak ≤ 72 / kulak dahil
  //                 ≤ 80) -> bugün 72; sürgü adımı 5 ile fiilen 70). Sürgü = KULAKÇIK DAHİL en uzun boyut (KraL
  //                 10 Eki, BaBa 14:0x); sırt konumunda kulak uzun kenarı büyütmez -> çıplak tavana kadar HER figür
  //                 yöneliminde üretilir (tepe sığmazsa koşucu sırta düşer; VERI.olcekHedefMm). Kol tavanı yoksa 0
  //                 (fail-closed: figür ölçüsü sunulmaz). TeKiN köprüyü büyütünce yalnız snapshot tazelenir.
  //   saglayici_tur : önizleme+model sağlayıcıda bu türün yolundan (TUR_ORTAM); üretim sonrası `uretec` koşucuda
  // Foto kolunun köprüden türeyen ölçü sınırı (alan: olcu_en_az | olcu_en_cok); yoksa 0 (fail-closed).
  function kolSiniri(kod, alan) {
    var t = VERI.turBul(kod), fk = t && t.foto_kolu;
    return fk && Number.isInteger(fk[alan]) && fk[alan] > 0 ? fk[alan] : 0;
  }
  VERI.cesitler = {
    anahtarlik: {
      varsayilan: "yazi",
      secenekler: [
        { kod: "yazi", ad: "Yazı ile", aciklama: "Kısa bir isim ya da yazı, kabartma harflerle.", acik: true },
        { kod: "figur", ad: "Figür olarak", aciklama: "Yüklediğin fotoğraftan küçük bir figür, tepesinde kulakçık.",
          acik: true, girdi: ["foto-1"], olcu_en_az: kolSiniri("anahtarlik", "olcu_en_az"),
          olcu_en_cok: kolSiniri("anahtarlik", "olcu_en_cok"), saglayici_tur: "figur", uretec: "figur_kulak" }
      ]
    }
  };
  // Çeşidin kaydı (tür + kod; yoksa null).
  VERI.cesitKaydi = function (kod, c) {
    var k = Object.prototype.hasOwnProperty.call(VERI.cesitler, kod) ? VERI.cesitler[kod] : null;
    if (!k || typeof c !== "string") { return null; }
    for (var i = 0; i < k.secenekler.length; i++) { if (k.secenekler[i].kod === c) { return k.secenekler[i]; } }
    return null;
  };
  // ÖLÇEK HEDEFİ (B2, KraL 10 Eki — kuralın TEK yeri): sağlayıcı 3MF'inin en uzun kenarının ölçekleneceği değer.
  // Anahtarlık figür çeşidinde sürgü = kulakçık DAHİL en uzun boyut; kulak sırtta ya da XY-uzun figürde uzun kenarı
  // büyütmez -> çıplak hedef = ölçü (tepe ancak sığarsa; koşucu tools/foto-uretec-kosucu.py figur_kos tepe ->
  // sırt düşüşü + figur_olcu_kabul kulak dahil = ölçü ± tolerans). Diğer türlerde hedef = ölçü.
  VERI.olcekHedefMm = function (olcu) { return olcu; };
  // İstekteki çeşidi çözer (istemci + sunucu ORTAK): çeşitli türde yok -> varsayılan, küme içi -> kendisi,
  // küme dışı -> null; çeşitsiz türde yok -> "" , dolu -> null (kapalı küme, fail-closed).
  VERI.cesitCoz = function (kod, c) {
    var k = Object.prototype.hasOwnProperty.call(VERI.cesitler, kod) ? VERI.cesitler[kod] : null;
    if (!k) { return c === undefined ? "" : null; }
    if (c === undefined) { return k.varsayilan; }
    return VERI.cesitKaydi(kod, c) ? c : null;
  };
  // Çeşit sunuluyor mu (çeşitsiz tür "" -> true; kapalı çeşit -> false).
  VERI.cesitAcik = function (kod, c) {
    if (c === "") { return true; }
    var s = VERI.cesitKaydi(kod, c);
    return !!s && s.acik === true;
  };
  // Metinde yasak: C0/C1 kontrol karakterleri (satır sonu dahil), satır/paragraf ayırıcı, yön geçersiz kılıcıları.
  var METIN_KONTROL = /[\u0000-\u001f\u007f-\u009f\u2028\u2029\u202a-\u202e\u2066-\u2069]/;
  function metinOgeGecerli(x, max) {
    return typeof x === "string" && x.trim().length > 0 && x.length <= max && !METIN_KONTROL.test(x);
  }
  function pozitifTam(n) { return typeof n === "number" && Number.isInteger(n) && n >= 1; }
  // Tek metin alanının değeri şemaya uyuyor mu (parametreDogrula ve girdiYeterli AYNI kural).
  function metinDegerGecerli(sema, v) {
    if (!pozitifTam(sema.max)) { return false; }
    if (sema.liste === true) {
      if (!pozitifTam(sema.satir_max) || !Array.isArray(v)) { return false; }
      if (v.length < 1 || v.length > sema.satir_max) { return false; }
      for (var m = 0; m < v.length; m++) {
        if (!metinOgeGecerli(v[m], sema.max)) { return false; }
      }
      return true;
    }
    return sema.liste === undefined && metinOgeGecerli(v, sema.max);
  }

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
  // PARAMETRELER — türün `form` şemasına karşı: sayi/secim/bool + K3c metin.
  // METİN (FAIL-CLOSED, sunucu da bunu çağırır): `liste:true` -> dizi, 1..satir_max öğe; değilse tek dize. Her öğe
  // dize, trim sonrası boş değil, uzunluk <= max, kontrol karakteri yok. Şemada max / (liste'de) satir_max pozitif
  // tam sayı değilse HER değer RED. `zorunlu:false` iken boş/yok (""/[]) -> alan çıktıya GİRMEZ (üreteç varsayılanı).
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
  // FORM SUNUMU: ekranda çizilmeyen alanın değeri (yoksa undefined -> alan normal çizilir). olcu = Ölçü sürgüsü (mm).
  VERI.formSunumDegeri = function (kod, alan, olcu) {
    var t = VERI.turBul(kod), fs = t && t.form_sunum && t.form_sunum[alan], sema = t && t.form ? t.form[alan] : null;
    if (!fs || !sema) { return undefined; }
    if (fs.deger === "olcu") { return typeof olcu === "number" && isFinite(olcu) ? olcu : undefined; }
    if (fs.deger === "varsayilan") { return sema.varsayilan; }
    return undefined;
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
      if (sema.tip === "metin" && sema.zorunlu === false &&
          (v === undefined || v === "" || (Array.isArray(v) && v.length === 0))) { continue; }
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
        if (!metinDegerGecerli(sema, v)) { return { ok: false, hata: "parametre-metin" }; }
        if (sema.liste === true) { v = v.slice(); }
      } else if (sema.tip === "bool") {
        if (v !== true && v !== false) { return { ok: false, hata: "parametre-bool" }; }
      }
      cikti[a] = v;
    }
    return { ok: true, deger: cikti };
  };
  // GİRDİ YETERLİ Mİ (anahtarlık 9 Eki; ② "İleri" ve sunucu girdi kapısı AYNI fonksiyon): türün `girdi`
  // listesinden EN AZ BİRİ dolu olmalı. g = {foto: bool (fotoğraf verildi mi), parametreler}.
  // "foto-*" -> g.foto === true; "metin" -> formdaki AKTİF metin alanlarından biri dolu VE şemaya uygun.
  // Dönüş "" = yeterli, "girdi-eksik" = hiçbiri yok (fail-closed: liste boş/bilinmeyen girdi -> eksik).
  // ÇEŞİT (g.cesit, VERI.cesitCoz): çeşidin `girdi`si varsa liste ODUR ve yazı formu sayılmaz (figür = yalnız foto);
  // çözülemeyen çeşit -> "girdi-eksik".
  VERI.girdiYeterli = function (kod, g) {
    var t = VERI.turBul(kod);
    if (!t || !Array.isArray(t.girdi) || !t.girdi.length) { return "girdi-eksik"; }
    g = g && typeof g === "object" ? g : {};
    var cz = VERI.cesitCoz(kod, g.cesit);
    if (cz === null) { return "girdi-eksik"; }
    var ck = VERI.cesitKaydi(kod, cz);
    var liste = ck && Array.isArray(ck.girdi) ? ck.girdi : t.girdi;
    var p = g.parametreler && typeof g.parametreler === "object" && !Array.isArray(g.parametreler) ? g.parametreler : {};
    var form = t.form && typeof t.form === "object" ? t.form : {};
    for (var i = 0; i < liste.length; i++) {
      var x = liste[i];
      if (FOTO_GIRDILERI[x] === true && g.foto === true) { return ""; }
      if (x === "metin") {
        for (var a in form) {
          if (!Object.prototype.hasOwnProperty.call(form, a) || !form[a] || form[a].tip !== "metin") { continue; }
          if (VERI.alanAktif(form, a, p) && Object.prototype.hasOwnProperty.call(p, a) &&
              metinDegerGecerli(form[a], p[a])) { return ""; }
        }
      }
    }
    return "girdi-eksik";
  };
  // Türün ölçü aralığı (mm, uzun kenar); bilinmeyen tür -> null. Bölüm ve sunucu AYNI fonksiyon.
  VERI.olcuAraligi = function (kod) {
    var t = VERI.turBul(kod);
    if (!t || !t.olcu_mm || !(t.olcu_mm.en_az > 0) || !(t.olcu_mm.en_cok >= t.olcu_mm.en_az)) { return null; }
    return { en_az: t.olcu_mm.en_az, en_cok: t.olcu_mm.en_cok };
  };

  // SÜRGÜ AÇILIŞI (Okan 10 Eki 15:2x "60'tan başlasın, 30–300 aralık"): olcu_mm.baslangic seçilebilir bir ölçüyse
  // (aralıkta + adım ızgarasında) o; alan yoksa/geçersizse en_az (bugünkü davranış). Bilinmeyen tür -> null.
  VERI.olcuBaslangic = function (kod) {
    var a = VERI.olcuAraligi(kod);
    if (!a) { return null; }
    var b = VERI.turBul(kod).olcu_mm.baslangic;
    return b !== undefined && VERI.olcuGecerli(kod, b) ? b : a.en_az;
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
  // KOŞULLU RENK BÖLGESİ (BaBa 8 Eki 15:5x: "ücret alınan her ek renk üretime BAĞLI"): bölge YALNIZ türün
  // renk_kosul'u sağlanınca üretilir (köprü türleri için köprü ÜRETİR; K3a'da kalan 4 türde kullanılmıyor).
  // p = parametreler (sunucuda önizleme girdi.json'u, istemcide formun AKTİF değerleri). Koşul biçimi bozuksa
  // bölge PASİF (fail-closed: üretileceği kanıtlanmayan renk ücretlenmez).
  VERI.renkBolgesiAktif = function (kod, bolge, p) {
    var t = VERI.turBul(kod);
    var k = t && t.renk_kosul && typeof t.renk_kosul === "object" ? t.renk_kosul[bolge] : undefined;
    if (k === undefined) { return true; }
    if (!Array.isArray(k) || !p || typeof p !== "object") { return false; }
    for (var i = 0; i < k.length; i++) {
      var c = k[i] || {};
      if (typeof c.alan !== "string" || !Object.prototype.hasOwnProperty.call(p, c.alan)) { return false; }
      var v = p[c.alan];
      if (c.dolu === true) {
        if (typeof v !== "string" || !v.trim()) { return false; }
      } else if (!Array.isArray(c.degerler) || c.degerler.indexOf(v) < 0) { return false; }
    }
    return true;
  };
  // Seçimdeki bölge renklerinden YALNIZ aktif bölgelerinki ({bölge: renk}); renk sayısı ve üretim buradan.
  VERI.aktifBolgeRenkleri = function (kod, renk, p) {
    var c = {};
    for (var b in (renk || {})) {
      if (Object.prototype.hasOwnProperty.call(renk, b) && VERI.renkBolgesiAktif(kod, b, p)) { c[b] = renk[b]; }
    }
    return c;
  };
  // Palet türünü deterministik üreteç basıyorsa renkler[i] -> palet_bolgeleri[i] ({bölge: renk}); yoksa {}.
  VERI.paletBolgeRenkleri = function (kod, renkler) {
    var t = VERI.turBul(kod);
    var pb = t && Array.isArray(t.palet_bolgeleri) ? t.palet_bolgeleri : [];
    var c = {};
    for (var i = 0; i < pb.length && Array.isArray(renkler) && i < renkler.length; i++) { c[pb[i]] = renkler[i]; }
    return c;
  };
  // Palet = manifestteki bölge renk listelerinin birleşimi (mevcut PLA paleti; ikinci liste değil, aynı 9 renk).
  VERI.PLA_RENKLERI = ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"];
  // RENK + MALZEME (Okan 9 Eki 17:0x, AYNEN): "renk seçimi 3 ana renkte (siyah beyaz veya gri) yapılsın veya
  // renkli seçeneği olsun %15 farkla seçilsin. ürünün renk seçimini müşterinin eklediği resime otomatik yapılsın."
  // · "malzeme seçiminde sadece pla ve petg … petg %30 fiyata eklensin." Ana renkte ürün TEK renk (tüm bölgeler o
  // renk); "Renkli"de renkler fotoğraftan otomatik (VERI.fotoRenkleri), yalnız fotoğraflı akışta sunulur.
  VERI.ANA_RENKLER = ["Siyah", "Beyaz", "Gri"];
  VERI.VARSAYILAN_RENK = "Beyaz";
  VERI.RENKLI_EK_YUZDE = 15;
  VERI.RENKLI_ETIKET = "Renkli (+%15)";
  // 2. resimdeki iki kart (metinler AYNEN); ek_yuzde fiyata çarpan olarak girer (PETG ×1,30).
  VERI.MALZEMELER = [
    { kod: "PLA", sicaklik: "~55-60°C", kullanim: "Ev içi", ek_yuzde: 0 },
    { kod: "PETG", sicaklik: "~70-75°C", kullanim: "Dış mekân / genel amaçlı", ek_yuzde: 30 }
  ];
  VERI.VARSAYILAN_MALZEME = "PLA";
  VERI.malzemeBul = function (kod) {
    for (var i = 0; i < VERI.MALZEMELER.length; i++) { if (VERI.MALZEMELER[i].kod === kod) { return VERI.MALZEMELER[i]; } }
    return null;
  };
  // Fiyatı etkileyen seçim {renkli, malzeme}: verilmezse ana renk + PLA; alan verilip bilinmiyorsa null (RED).
  VERI.fiyatSecimi = function (s) {
    if (s === undefined) { return { renkli: false, malzeme: VERI.VARSAYILAN_MALZEME }; }
    if (!s || typeof s !== "object" || Array.isArray(s)) { return null; }
    var r = s.renkli === undefined ? false : s.renkli;
    var m = s.malzeme === undefined ? VERI.VARSAYILAN_MALZEME : s.malzeme;
    if (typeof r !== "boolean" || !VERI.malzemeBul(m)) { return null; }
    return { renkli: r, malzeme: m };
  };
  // Taban fiyata (kuruş) renk + malzeme çarpanları: round(k × (Renkli ? 1,15 : 1) × (PETG ? 1,30 : 1)).
  VERI.secimliKurus = function (kurus, secim) {
    var c = VERI.fiyatSecimi(secim);
    if (!Number.isInteger(kurus) || kurus < 0 || !c) { return null; }
    var ry = c.renkli ? VERI.RENKLI_EK_YUZDE : 0, my = VERI.malzemeBul(c.malzeme).ek_yuzde;
    return Math.round(kurus * (100 + ry) * (100 + my) / 10000);
  };
  // "Renkli" bu türde sunulabilir mi: türün girdisi fotoğraf ise (renkler fotoğraftan çıkar). Fotoğrafsız akışta
  // (yazılı anahtarlık, girdi "metin") Renkli GÖRÜNMEZ ve sunucu RED eder (aynı fonksiyon).
  // ÇEŞİT KOLU (Okan 10 Eki "renkli seçeneği yok"): çeşidin kendi üreteci varsa (figür anahtarlık -> figur_kulak)
  // karar O kolun: fotoğraflı VE köprü kolu en az 2 boyanabilir bölge taşıyorsa (foto_kolu.renk_bolgesi, köprüden
  // TÜRER); figur_kulak TEK gövde (0) -> Renkli YOK. Çeşit verilmezse/kolsuz çeşitte türün girdisi (aşağı).
  VERI.renkliSecilebilir = function (kod, cesit) {
    var t = VERI.turBul(kod);
    var ck = cesit === undefined ? null : VERI.cesitKaydi(kod, VERI.cesitCoz(kod, cesit));
    if (ck && ck.uretec) {
      var fk = t && t.foto_kolu, cg = ck.girdi || [], foto = false;
      for (var j = 0; j < cg.length; j++) { if (FOTO_GIRDILERI[cg[j]] === true) { foto = true; } }
      return foto && !!fk && fk.uretec === ck.uretec && fk.renk_bolgesi >= 2;
    }
    var g = t ? (t.girdi || []) : [];
    for (var i = 0; i < g.length; i++) { if (FOTO_GIRDILERI[g[i]] === true) { return true; } }
    return false;
  };
  // FOTOĞRAFTAN RENK (deterministik, kredi 0, harici API YOK): piksel dizisi (RGBA, Uint8 benzeri) -> filament
  // renklerine (RENK_HEX) en yakın eşleme -> en sık `tavan` farklı renk (çok sıktan aza). Saydam piksel sayılmaz;
  // %2'nin altındaki renk elenir (gürültü). Hiç renk çıkmazsa [] (bölüm Renkli'yi açmaz).
  VERI.fotoRenkleri = function (piksel, tavan) {
    var adlar = VERI.PLA_RENKLERI, hex = [], say = {}, top = 0, i, j;
    for (i = 0; i < adlar.length; i++) {
      var h = String(VERI.RENK_HEX[adlar[i]] || "").replace("#", "");
      hex.push([parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]);
    }
    for (i = 0; piksel && i + 3 < piksel.length; i += 4) {
      if (piksel[i + 3] < 128) { continue; }
      var en = -1, ed = Infinity;
      for (j = 0; j < hex.length; j++) {
        var dr = piksel[i] - hex[j][0], dg = piksel[i + 1] - hex[j][1], db = piksel[i + 2] - hex[j][2];
        var d = 2 * dr * dr + 4 * dg * dg + 3 * db * db;
        if (d < ed) { ed = d; en = j; }
      }
      say[adlar[en]] = (say[adlar[en]] || 0) + 1; top++;
    }
    var n = Number.isInteger(tavan) && tavan >= 1 ? Math.min(tavan, 4) : 1;
    return adlar.filter(function (a) { return say[a] && say[a] / top >= 0.02; })
      .sort(function (a, b) { return say[b] - say[a] || adlar.indexOf(a) - adlar.indexOf(b); }).slice(0, n);
  };
  // fiyat_kurus = round( max(taban, en uzun boyut (mm) × formülün mm başı kuruşu) × (Renkli ? 1,15 : 1)
  //               × (PETG ? 1,30 : 1) ) — TEK kaynak (bölüm, sunucu, araçlar). secim = {renkli, malzeme}; verilmezse
  // ana renk + PLA (vitrin "₺N'dan itibaren" ve sürgü satırı). Geçersiz ölçü / bilinmeyen formül / taban ya da
  // renk tavanı yok / bilinmeyen renk ya da malzeme -> null. Renk ADEDİ fiyata girmez.
  VERI.fiyatKurus = function (kod, mm, secim) {
    var t = VERI.turBul(kod);
    var f = t && t.fiyat && Object.prototype.hasOwnProperty.call(VERI.FIYAT_FORMULLERI, t.fiyat.formul)
      ? VERI.FIYAT_FORMULLERI[t.fiyat.formul] : null;
    var taban = VERI.fiyatTabanKurus(kod), tavan = VERI.renkTavani(kod);
    if (!f || taban === null || tavan === null || !VERI.olcuGecerli(kod, mm)) { return null; }
    return VERI.secimliKurus(Math.max(mm * f, taban), secim);
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
