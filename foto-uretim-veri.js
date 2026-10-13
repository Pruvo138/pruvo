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
 * Örnek kaydı: { tur, alt, cesit, kanit, olcu_mm, foto, onizleme, baski, render, not }
 *   tur      : turler[].kod
 *   alt      : figür alt türü (türün `olcu_modelleri` anahtarı: insan|pet|model). Alt türlü kart ① yalnız
 *              `o.alt === kart.alt` örneği gösterir. Alan yoksa kayıt türde SAYILIR ama alt türlü karta düşmez;
 *              bilinmeyen değer / modelsiz türde alan -> SAYILMAZ (fail-closed)
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
    //                    surgu_etiketi: true (yalnız deger "olcu") = ③ sürgüsünün etiketi bu alanın `etiket`i olur
    //   alan_aciklamalari: {renk, olcu, malzeme} — ③ ortak alanların altındaki tür cümlesi (yoksa genel cümle)
    //   bolge_renk_secimi: {cesit, bolgeler, etiketler, varsayilan, kontrast_esigi} — ana renkte TEK seçici yerine her
    //                    bölgeye AYRI ana renk seçici (anahtarlık–yazı: Yazı rengi + Taban rengi; Okan 12 Eki). Bölge
    //                    çifti üreteç metriğiyle eşiğin altındaysa ③'te `kontrast` metni + ileri pasif; sunucu aynı
    //                    hükümle reddeder (VERI.bolgeRenkHukmu). Alan yoksa ana renkte TÜM bölgeler aynı renk.
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
        // ÖLÇÜ MODEL BAŞINA (BaBa 10 Eki 22:3x; eski tek aralık 60–200 GEÇERSİZ): figürün KAİDE DAHİL en uzun boyutu.
        // TEK kaynak `olcu_modelleri`: istemci sürgüsü (VERI.modelOlcuSecenekleri), sunucu önizleme + sipariş kabulü
        // (VERI.modelOlcuGecerli) ve tür zarfı (VERI.olcuAraligi = modellerin en_az min .. en_cok max) buradan TÜRER.
        // Tavan = TeKiN figur_denge `max_guvenli_mm` ölçümü (figur_duzelt sonrası gerçek sağlayıcı çıktısı; 10 Eki +
        // 11 Eki ek dilim `792ac60`, aşağı yuvarlanır): insan 105,4 -> 105 · pet 136,5 -> 136 · model (araç) 300 -> 300.
        // Taban: insan min_guvenli_mm 40,7 (ince_kesit) yukarı -> 41; pet/model 60 (Okan 10 Eki 12:4x "slider figürlerde
        // 60mm"). Sürgü açılışı 60 (baslangic). Tavan aşan iş koşucunun figur_denge kapısında da RED olur.
        olcu_mm: { baslangic: 60 },
        olcu_modelleri: {
          insan: { en_az: 41, en_cok: 105 },
          pet: { en_az: 60, en_cok: 136 },
          model: { en_az: 60, en_cok: 300 }
        },
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
        olcu_mm: { en_az: 30, en_cok: 300, baslangic: 60 },
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
            max: 300,
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
          olcu: "Anahtarlığın kulakçık dahil en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.",
          // ③ renk yardım cümlesi (iki seçici; ArTisT 19. okuma bu satırı değiştirir — TEK yer). Figür çeşidinin
          // kendi `renk` cümlesi bunun yerine basılır (alanAciklamasi çeşide öncelik verir).
          renk: "Yazı için bir, taban için bir renk seç; ikisi birbirinden belirgin olmalı ki yazı net okunsun."
        },
        // İKİ RENK (Okan 12 Eki, aynen "anahtarlıkta tek renk seçimi olmaz zaten minimum 2 renk olmalı"): yazı
        // çeşidinde ③'te Yazı rengi + Taban rengi, ikisi de VERI.ANA_RENKLER; varsayılan siyah taban + beyaz yazı.
        // kontrast_esigi = üreteç KONTRAST_MIN (pruvo-jenerator jeneratorler/foto/isimlik_uret.py: 3.0, plaka/yazi
        // RET'i); metrik VERI.kontrastOrani (aynı dosyanın bagil_parlaklik/kontrast_orani formülü). Fiyat değişmez.
        bolge_renk_secimi: {
          cesit: "yazi",
          bolgeler: ["yazi", "plaka"],
          etiketler: { yazi: "Yazı rengi", plaka: "Taban rengi" },
          varsayilan: { yazi: "Beyaz", plaka: "Siyah" },
          kontrast_esigi: 3.0
        },
        // ③'te TEK ölçü kontrolü (Okan 12 Eki 17:5x "tek"; BaBa 13 Eki 11:4x): ayrı "Uzun kenar" alanı çizilmez, değeri
        // sürgüden gelir ve sürgünün etiketi bu alanın etiketidir ("Uzun kenar (kulak dahil)"; ayrı "Ölçü" yok).
        // KULAK SOL ÜST SABİT (Okan 8 Eki 23:0x): "Kulak konumu" seçicisi çizilmez, gövdeye form varsayılanı
        // ("sol-ust") girer. Köprü `form`u değişmez (kopru-manifest-uret üretir); figür çeşidi formsuz -> etkisiz.
        form_sunum: {
          genislik_mm: { deger: "olcu", surgu_etiketi: true },
          anahtarlik_kulak_konum: { deger: "varsayilan" }
        },
        durustluk: "Metal halka ve zincir dahil değildir; zincir ya da halka takılan kulakçıklı plastik gövde (delik Ø 3,5–4 mm).",
        ornek_notu: "Üretim dosyasının görüntüsüdür; yazı, renk ve kulak konumu seçimine göre üretilir.",
        olcu_ekseni: "sabit",
        foto_kolu: {
          girdi: ["foto-1"],
          uretec: "figur_kulak",
          olcu_en_az: 30,
          olcu_en_cok: 291,
          renk_bolgesi: 0,
          renk_modlari: ["tek", "palet"]
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
      "kontrast": "Yazı ve taban rengi birbirine çok yakın; yazı okunmaz. Farklı bir renk seç.",
      "metin-sigmadi": "Yazı bu ölçüye sığmadı; yazıyı kısalt ya da ölçüyü büyüt.",
      // Anahtarlık–yazı ince çizgi (üreteç tasarım kapısı 0,8 mm; düz yazı kısa isimde ~40 mm ister, el yazısı 30 mm'de geçer).
      "yazi-ince": "Bu yazı bu genişlikte çok ince kalıyor; genişliği büyüt (kalın düz harflerde kısa bir isim için en az 40 mm) ya da El yazısı yazı tipini seç.",
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
      "anahtarlik-boyut": "Bu fotoğraftan anahtarlık boyutunda bir parça çıkmadı; daha sade bir fotoğraf ya da kısa bir yazı deneyin.",
      // Anahtarlık–figür tabla ankrajı reddi (figur_kulak 1.1) — ArTisT 18. okuma revize (11:5x): TeKiN 11:4x ölçümü,
      // figür BÜYÜDÜKÇE F_TEPE DÜŞER (K2b 60=32,8 · 66=30,7 · 72=29,0 N RED) -> geçiren yön KÜÇÜLTMEK; "ölçüyü büyüt" yanlış yöndü.
      "ankraj": "Bu fotoğraftan çıkan figür bu ölçüde sağlam bir anahtarlık olarak üretilemiyor; daha küçük bir ölçü ya da daha sade bir fotoğraf dene."
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
        // Alt tür pet (11 Eki): kedi örneği YALNIZ pet kartında; insan/model kartı kendi kaydını gösterir.
        alt: "pet",
        onizleme: "https://media.pruvo3d.com/foto/ornek/figur-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/figur-1-render.webp",
        not: "130 mm, kaideli figür"
      },
      {
        tur: "figur",
        alt: "insan",
        kanit: "render",
        // 105 = insan ürün tavanı (olcu_modelleri.insan.en_cok). Render ölçeksizdir (3MF bbox 130 mm); aynı geometri
        // 105 mm'de 0-kredi C provasında figur_zinciri DENGE=OK (106 RED) -> satılabilen ölçü yazılır, 130 YAZILMAZ.
        // Girdi SENTETİK çizim; gerçek kişi YOK (11 Eki render teslimi).
        olcu_mm: 105,
        onizleme: "https://media.pruvo3d.com/foto/ornek/insan-onizleme.webp",
        render: "https://media.pruvo3d.com/foto/ornek/insan-1-render.webp",
        not: "105 mm, 4 renk, kaideli insan figürü"
      },
      {
        tur: "figur",
        alt: "model",
        kanit: "render",
        // 130 = 3MF bbox (model aralığı 60–300 içinde). Girdi SENTETİK çizim (11 Eki render teslimi).
        olcu_mm: 130,
        onizleme: "https://media.pruvo3d.com/foto/ornek/model-onizleme.webp",
        render: "https://media.pruvo3d.com/foto/ornek/model-1-render.webp",
        not: "130 mm, 4 renk, kaideli araç modeli"
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
      },
      {
        tur: "anahtarlik",
        cesit: "figur",
        kanit: "render",
        // 60 mm (3MF bbox, halka dahil). Tek renk dosya -> notta renk iddiası YOK. Girdi SENTETİK çizim (TeKiN ed7c152, figur_kulak 1.1 hilal).
        olcu_mm: 60,
        onizleme: "https://media.pruvo3d.com/foto/ornek/anahtarlik-figur-hilal-onizleme.webp",
        render: "https://media.pruvo3d.com/foto/ornek/anahtarlik-figur-hilal-2-render.webp",
        not: "60 mm, başın arkasına gömülü yarım halkalı figür anahtarlık"
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
    // Alt tür: yalnız türün `olcu_modelleri` anahtarı; modelsiz türde ya da bilinmeyen değerde SAYILMAZ (fail-closed).
    if (o.alt !== undefined && !(t && t.olcu_modelleri && typeof o.alt === "string" &&
        Object.prototype.hasOwnProperty.call(t.olcu_modelleri, o.alt))) { return false; }
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
        { kod: "figur", ad: "Figür olarak", aciklama: "Yüklediğin fotoğraftan küçük bir figür; anahtarlık halkası başın arkasında, gömülü yarım halka olarak.",
          acik: true, girdi: ["foto-1"], olcu_en_az: kolSiniri("anahtarlik", "olcu_en_az"),
          olcu_en_cok: kolSiniri("anahtarlik", "olcu_en_cok"), saglayici_tur: "figur", uretec: "figur_kulak",
          // ② dürüstlük cümlesi (ArTisT 874b2a85 pazarlama metni ② "Anahtarlık – figür" AYNEN; figür/plaket'in TEK
          // stilize-yorum cümlesi). Bölüm türün `durustluk`unun altına çeşidinkini basar; yazı çeşidinde alan YOK.
          durustluk: "Önizleme fotoğrafının stilize bir yorumudur; basılmış anahtarlık en çok 4 renkli, sadeleştirilmiş bir hâlidir ve tam kopyası değildir (küçük ayrıntılar sadeleşir).",
          // ③ renk + ölçü cümleleri (ArTisT 17. okuma, KraL 12 Eki): Renkli yalnız köprü kolu `renk_modu` palet sunarken
          // çizilir. Ölçü çeşide ÖZEL: tür düzeyindeki "kulakçık dahil" cümlesi yazı çeşidi içindir (kulakçık DURUR); figür
          // çeşidinde halka gömülü olduğundan "halka dahil" ayrı cümle (tür cümlesinin YERİNE basılır, foto-uretim.js
          // alanAciklamasi çeşit alanına öncelik verir).
          alan_aciklamalari: {
            renk: "Siyah, Beyaz ya da Gri seçersen anahtarlık tek renk olur; Renkli seçersen renkler fotoğrafından otomatik seçilir (en çok 4 renk).",
            olcu: "Anahtarlığın, başın arkasındaki halka dahil en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır."
          } }
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
  // Model başına ölçülü türde (olcu_modelleri, figür) aralık = modellerin ZARFI (en küçük en_az .. en büyük en_cok);
  // bozuk model satırı -> null (fail-closed: tür fiyatsız, sunulmaz).
  VERI.olcuAraligi = function (kod) {
    var t = VERI.turBul(kod);
    if (t && t.olcu_modelleri) { return modelZarfi(t.olcu_modelleri); }
    if (!t || !t.olcu_mm || !(t.olcu_mm.en_az > 0) || !(t.olcu_mm.en_cok >= t.olcu_mm.en_az)) { return null; }
    return { en_az: t.olcu_mm.en_az, en_cok: t.olcu_mm.en_cok };
  };
  function aralikGecerli(a) {
    return !!a && Number.isInteger(a.en_az) && a.en_az > 0 && Number.isInteger(a.en_cok) && a.en_cok >= a.en_az;
  }
  function modelZarfi(m) {
    var z = null;
    for (var k in m) {
      if (!Object.prototype.hasOwnProperty.call(m, k)) { continue; }
      if (!aralikGecerli(m[k])) { return null; }
      z = z ? { en_az: Math.min(z.en_az, m[k].en_az), en_cok: Math.max(z.en_cok, m[k].en_cok) }
        : { en_az: m[k].en_az, en_cok: m[k].en_cok };
    }
    return z;
  }
  // MODEL BAŞINA ÖLÇÜ (BaBa 10 Eki 22:3x): türün `olcu_modelleri` satırı (alt = figür alt türü insan|pet|model).
  // Modelsiz tür -> türün kendi aralığı (alt okunmaz). Modelli türde bilinmeyen/boş alt ya da bozuk satır -> null.
  VERI.modelOlcuAraligi = function (kod, alt) {
    var t = VERI.turBul(kod);
    if (!t || !t.olcu_modelleri) { return VERI.olcuAraligi(kod); }
    if (!modelZarfi(t.olcu_modelleri) || typeof alt !== "string" ||
        !Object.prototype.hasOwnProperty.call(t.olcu_modelleri, alt)) { return null; }
    return { en_az: t.olcu_modelleri[alt].en_az, en_cok: t.olcu_modelleri[alt].en_cok };
  };
  // Modelin sürgü ölçüleri: en_az, aradaki adım KATLARI (sürgü adımıyla hizalı: 50, 60, ...), en_cok. Modelsiz tür ->
  // VERI.olcuSecenekleri (bugünkü ızgara AYNEN).
  VERI.modelOlcuSecenekleri = function (kod, alt) {
    var t = VERI.turBul(kod);
    if (!t || !t.olcu_modelleri) { return VERI.olcuSecenekleri(kod); }
    var a = VERI.modelOlcuAraligi(kod, alt), adim = VERI.olcuAdimi(kod), c = [];
    if (!a || !adim) { return c; }
    c.push(a.en_az);
    for (var mm = (Math.floor(a.en_az / adim) + 1) * adim; mm < a.en_cok; mm += adim) { c.push(mm); }
    if (a.en_cok !== a.en_az) { c.push(a.en_cok); }
    return c;
  };
  // Ölçü bu modelde satılır mı (sunucu önizleme + sipariş kapısı ve istemci sürgüsü AYNI fonksiyon).
  VERI.modelOlcuGecerli = function (kod, alt, mm) {
    return Number.isInteger(mm) && VERI.modelOlcuSecenekleri(kod, alt).indexOf(mm) >= 0;
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
    var t = VERI.turBul(kod);
    // Model başına ölçülü tür: herhangi bir modelin ızgarasında (fiyat formülü bu kümeye açık; modelin KENDİ kümesini
    // sunucu ayrıca VERI.modelOlcuGecerli ile ister).
    if (t && t.olcu_modelleri) {
      for (var m in t.olcu_modelleri) {
        if (Object.prototype.hasOwnProperty.call(t.olcu_modelleri, m) && VERI.modelOlcuGecerli(kod, m, mm)) { return true; }
      }
      return false;
    }
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
  // RENK KONTRASTI (üreteçle AYNI metrik — pruvo-jenerator jeneratorler/foto/isimlik_uret.py bagil_parlaklik +
  // kontrast_orani, WCAG bağıl parlaklık): renk ADLARI VERI.RENK_HEX'ten; ad bilinmiyorsa null.
  function bagilParlaklik(ad) {
    var h = Object.prototype.hasOwnProperty.call(VERI.RENK_HEX, ad) ? String(VERI.RENK_HEX[ad]) : "";
    if (!/^#[0-9a-fA-F]{6}$/.test(h)) { return null; }
    var lin = function (c) { c = c / 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    return 0.2126 * lin(parseInt(h.slice(1, 3), 16)) + 0.7152 * lin(parseInt(h.slice(3, 5), 16)) +
      0.0722 * lin(parseInt(h.slice(5, 7), 16));
  }
  VERI.kontrastOrani = function (a, b) {
    var la = bagilParlaklik(a), lb = bagilParlaklik(b);
    if (la === null || lb === null) { return null; }
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  };
  // Türün bölge renk seçimi kaydı (`bolge_renk_secimi`) — kayıt varsa ve (alan `cesit` diyorsa) çeşit uyuyorsa; yoksa null.
  VERI.bolgeRenkSecimi = function (kod, cesit) {
    var t = VERI.turBul(kod), k = t && t.bolge_renk_secimi;
    if (!k || typeof k !== "object" || !Array.isArray(k.bolgeler)) { return null; }
    return k.cesit === undefined || VERI.cesitCoz(kod, cesit) === k.cesit ? k : null;
  };
  // Bölge renk hükmü (istemci ③ + sunucu renkSayimi ORTAK): renkler {bölge: ad}. "" = geçer · "renk" = kayıttaki bir
  // bölgenin rengi yok ya da VERI.ANA_RENKLER dışında · "kontrast" = iki bölge üreteç eşiğinin altında (aynı/yakın).
  VERI.bolgeRenkHukmu = function (kod, renkler, cesit) {
    var k = VERI.bolgeRenkSecimi(kod, cesit), r = renkler || {}, i, j;
    if (!k) { return "renk"; }
    for (i = 0; i < k.bolgeler.length; i++) {
      if (VERI.ANA_RENKLER.indexOf(r[k.bolgeler[i]]) < 0) { return "renk"; }
    }
    for (i = 0; i < k.bolgeler.length; i++) {
      for (j = i + 1; j < k.bolgeler.length; j++) {
        var o = VERI.kontrastOrani(r[k.bolgeler[i]], r[k.bolgeler[j]]);
        if (o === null) { return "renk"; }
        if (o < k.kontrast_esigi) { return "kontrast"; }
      }
    }
    return "";
  };
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
      return foto && !!fk && fk.uretec === ck.uretec && (fk.renk_bolgesi >= 2 || VERI.cesitPaleti(kod, cesit));
    }
    var g = t ? (t.girdi || []) : [];
    for (var i = 0; i < g.length; i++) { if (FOTO_GIRDILERI[g[i]] === true) { return true; } }
    return false;
  };
  // ÇEŞİT PALETİ (renk = palet, BaBa 16:0x 2a): çeşidin üreteci köprü kolununki VE kolun `renk_modlari`nda "palet"
  // varsa (figur_kulak tek|palet; köprüden TÜRER, foto_kolu.renk_modlari) Renkli'de renkler fotoğraftan 1..tavan
  // (palet türüyle AYNI kural), üretim `renk_modu=palet` (sağlayıcı 3MF boyası korunur). Kol/mod yoksa false.
  VERI.cesitPaleti = function (kod, cesit) {
    var t = VERI.turBul(kod), fk = t && t.foto_kolu;
    var ck = cesit === undefined ? null : VERI.cesitKaydi(kod, VERI.cesitCoz(kod, cesit));
    return !!ck && !!ck.uretec && !!fk && fk.uretec === ck.uretec &&
      Array.isArray(fk.renk_modlari) && fk.renk_modlari.indexOf("palet") >= 0;
  };
  // Çeşit paletinin renk tavanı: köprü renk_modu "palet: … en çok 4 renk" (figur_kulak PALET_MAX_RENK 4 = AMS 4 yuva,
  // VERI.renkTavani üst sınırıyla AYNI); palet çeşidi değilse null.
  VERI.cesitRenkTavani = function (kod, cesit) { return VERI.cesitPaleti(kod, cesit) ? 4 : null; };
  // Üretime giden renk modu (sunucu satırı foto_renk_modu -> koşucu --renk-modu): palet çeşidinde Renkli -> "palet",
  // aksi HER durumda "tek" (eski sipariş/alan yok = tek; geriye uyum).
  VERI.renkModu = function (kod, cesit, renkli) {
    return renkli === true && VERI.cesitPaleti(kod, cesit) ? "palet" : "tek";
  };
  // Filament adları -> [r, g, b] (RENK_HEX; fotoRenkleri ve 4 renk simülasyonu ORTAK).
  function renkRgb(adlar) {
    return adlar.map(function (a) {
      var h = String(VERI.RENK_HEX[a] || "").replace("#", "");
      return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
    });
  }
  // FOTOĞRAFTAN RENK (deterministik, kredi 0, harici API YOK; KraL-FotoPalet 11 Eki): piksel dizisi (RGBA, Uint8
  // benzeri; w×h, verilmezse kare sayılır) -> en çok `tavan` (≤4) filament rengi, alanı büyükten küçüğe. Eski yol her
  // pikseli RGB'de en yakın renge sayıyordu: renderin ışığı/gölgesi doygunluğu düşürdüğü için denim ve koyu kahve saç
  // Gri'ye düşüyor, saç yarı Siyah yarı Gri bölünüyor, sarı gözlük kenarının karışık pikselleri Yeşil seçtiriyordu.
  // Yeni yol simülasyonun ADIMLARINI kullanır, palete bakmadan:
  //  (1) küçült + median (simKucult); KENARA BAĞLI AÇIK ARKA PLAN (açık, düşük kromalı, görüntü kenarından kesintisiz
  //      ulaşılan hücreler; PR_ARKA_*) ve saydam hücre renk SAYILMAZ — figürün içindeki beyaz tişört kenara
  //      değmediği için kalır;
  //  (2) kaynak BÖLGELERİ (simKaynakBolge: gölge/parlama bandı yüzeyi bölmez) -> her bölge ORTALAMA OKLab tonuyla
  //      TEK renge (prEsle) — saç tek bölge, tek renk;
  //  (3) alan oyu: opak alanın PR_PAY'ından küçük renk elenir (gürültü, kenar pikseli).
  // prEsle kuralları (her biri ölçülmüş bir hatayı kapatır; gerekçe sayıları KraL-FotoPalet kapanışında):
  //  · AYDINLATMA PAYI: nötr renklerin hedef açıklığı render aralığına sıkıştırılır (siyah plastik/saç renderde
  //    L≈0,35–0,5 ölçülür, Siyah filamentin L'si 0,22) — en koyu nötr PR_NOTR_ALT, en açık PR_NOTR_UST, aradakiler
  //    orantılı; bölgenin kroması nötr maliyetine PR_NOTR_W ile eklenir;
  //  · ARA NÖTR (Gri) yalnız GERÇEK NÖTR yüzeyde (kroma < PR_GRI_C): ışıklı denim / kahve saç / gölgeli ten Gri olmaz;
  //  · TON KAPISI: renkli adaya bölgenin kroması ≥ PR_C_MIN ve ton farkı ≤ PR_TON_MAX iken bakılır (görselde
  //    olmayan Yeşil seçilmez); renk maliyeti OKLab ΔL² + ΔC² + ΔH², bölge kroması PR_K ile büyütülmüş (render
  //    filamentten soluk: denim C≈0,03, Mavi 0,09);
  //  · KAHVE: sıcak tonlu (PR_KAHVE_TON) düşük kromalı yüzey (kahve saç, ten, ahşap; kroma < PR_KAHVE_C) canlı renge
  //    (Kırmızı/Sarı) gitmez — yalnız düşük kromalı renge (Ahşap) ya da nötre: paletin kahvesi yok, koyu kahve Siyah.
  // Hiç renk çıkmazsa [] (bölüm Renkli'yi açmaz). Müşterinin elle seçtiği palet bu fonksiyondan GEÇMEZ (istemci).
  var PR_ARKA_L = 0.8, PR_ARKA_C = 0.04, PR_PAY = 0.02, PR_NOTR_C = 0.01, PR_NOTR_ALT = 0.38, PR_NOTR_UST = 0.9,
    PR_NOTR_W = 3, PR_GRI_C = 0.015, PR_C_MIN = 0.018, PR_TON_MAX = 50, PR_K = 2, PR_KAHVE_C = 0.07, PR_KAHVE_TON = [20, 80], PR_UZAK = 0.08;
  VERI.FOTO_RENK_KENAR = 128;                            // istemci fotoğrafı bu kareye küçültüp verir
  // Palet girdileri (OKLab, nötr hedefi); `secili` verilirse yalnız o adlar, o sırayla (simülasyon: seçili palet;
  // nötr hedefi yine TÜM paletin nötr aralığından — aynı yüzey iki yolda aynı hedefe bakar). Bilinmeyen ad -> null.
  function prPalet(secili) {
    var T = linTablo(), adlar = VERI.PLA_RENKLERI, rgb = renkRgb(adlar), P = [], nL = [];
    for (var j = 0; j < adlar.length; j++) {
      var o = oklab(T[rgb[j][0]], T[rgb[j][1]], T[rgb[j][2]]), C = Math.sqrt(o[1] * o[1] + o[2] * o[2]);
      P.push({ ad: adlar[j], L: o[0], a: o[1], b: o[2], C: C, notr: C < PR_NOTR_C });
      if (C < PR_NOTR_C) { nL.push(o[0]); }
    }
    var lo = Math.min.apply(null, nL), hi = Math.max.apply(null, nL);
    P.forEach(function (p) {
      if (!p.notr) { return; }
      p.hedef = hi > lo ? PR_NOTR_ALT + (p.L - lo) / (hi - lo) * (PR_NOTR_UST - PR_NOTR_ALT) : p.L;
      p.ara = p.L > lo && p.L < hi;                      // ara nötr (Gri)
    });
    return secili ? secili.map(function (a) { return P[adlar.indexOf(a)] || null; }) : P;
  }
  // Bölge (ortalama OKLab L, a, b) -> palet rengi p maliyeti; kurallara takılan aday Infinity.
  function prMaliyet(p, L, a, b) {
    if (!p) { return Infinity; }
    var C = Math.sqrt(a * a + b * b), kC = PR_K * C, ton = (Math.atan2(b, a) * 180 / Math.PI + 360) % 360;
    if (p.notr) {
      if (p.ara && C >= PR_GRI_C) { return Infinity; }
      return (L - p.hedef) * (L - p.hedef) + PR_NOTR_W * kC * kC;
    }
    var cos = C > 0 ? (a * p.a + b * p.b) / (C * p.C) : 1;
    var kahve = C < PR_KAHVE_C && ton >= PR_KAHVE_TON[0] && ton <= PR_KAHVE_TON[1];
    if (C < PR_C_MIN || cos < Math.cos(PR_TON_MAX * Math.PI / 180) || (kahve && p.C >= PR_KAHVE_C)) { return Infinity; }
    return (L - p.L) * (L - p.L) + (p.C - kC) * (p.C - kC) + 2 * kC * p.C * (1 - cos);
  }
  function prEsle(P, L, a, b, cik) {
    var en = -1, ed = Infinity;
    for (var j = 0; j < P.length; j++) {
      var d = prMaliyet(P[j], L, a, b);
      if (d < ed) { ed = d; en = j; }
    }
    if (cik) { cik[0] = ed; }
    return en;
  }
  // AYNI YÜZEY AYNI RENK: ikisi de renkli (ya da ikisi de nötr; kroma PR_C_MIN eşiği — koyu denim gözlüğün Siyah'ını
  // almasın), tonu (a, b) PR_BIRLIK_AB'den, açıklığı PR_BIRLIK_L'den az farklı iki bölge yalnız ışıkla ayrışmış aynı
  // yüzeydir; iki palet renginin tam arasında kalan ton (turuncu: Sarı ile Kırmızı arası) ışığın küçük
  // farkıyla bir bölgeyi bir renge, öbürünü öbürüne atıyordu (pet: kafa Sarı, gövde Kırmızı). Büyükten küçüğe: bölge,
  // kendisine benzeyen daha büyük bir bölgenin rengini alır — o renk bu bölge için kurallardan geçiyor ve maliyeti
  // ≤ PR_UZAK ise. bol = [{ s, L, a, b }] (s = hücre sayısı, ortalamalar), renk = palet indeksleri (YERİNDE değişir).
  var PR_BIRLIK_AB = 0.025, PR_BIRLIK_L = 0.12;
  function prBirlik(bol, renk, P) {
    var sira = bol.map(function (x, i) { return i; }).filter(function (i) { return bol[i].s > 0 && renk[i] >= 0; })
      .sort(function (i, j) { return bol[j].s - bol[i].s || i - j; });
    for (var u = 1; u < sira.length; u++) {
      var i = sira[u], q = bol[i];
      for (var v = 0; v < u; v++) {
        var j = sira[v], o = bol[j];
        if (renk[j] === renk[i] || Math.abs(q.L - o.L) >= PR_BIRLIK_L ||
            (Math.sqrt(q.a * q.a + q.b * q.b) < PR_C_MIN) !== (Math.sqrt(o.a * o.a + o.b * o.b) < PR_C_MIN) ||
            Math.sqrt((q.a - o.a) * (q.a - o.a) + (q.b - o.b) * (q.b - o.b)) >= PR_BIRLIK_AB) { continue; }
        if (prMaliyet(P[renk[j]], q.L, q.a, q.b) <= PR_UZAK) { renk[i] = renk[j]; }
        break;
      }
    }
  }
  // Kenara bağlı açık arka plan: kenardaki uygun hücrelerden 4-komşu taşma; işaretli hücre saydam sayılır (say = 0).
  function prArkaSil(k0) {
    var sw = k0.sw, sh = k0.sh, say = k0.say, yigin = [], gor = new Uint8Array(sw * sh), k, x, y;
    function uygun(q) {
      return say[q] && k0.L[q] >= PR_ARKA_L && Math.sqrt(k0.A[q] * k0.A[q] + k0.B[q] * k0.B[q]) <= PR_ARKA_C;
    }
    for (y = 0; y < sh; y++) {
      for (x = 0; x < sw; x++) {
        k = y * sw + x;
        if ((x === 0 || y === 0 || x === sw - 1 || y === sh - 1) && uygun(k)) { gor[k] = 1; yigin.push(k); }
      }
    }
    while (yigin.length) {
      k = yigin.pop(); x = k % sw; y = (k - x) / sw;
      [x > 0 ? k - 1 : -1, x < sw - 1 ? k + 1 : -1, y > 0 ? k - sw : -1, y < sh - 1 ? k + sw : -1].forEach(function (q) {
        if (q >= 0 && !gor[q] && uygun(q)) { gor[q] = 1; yigin.push(q); }
      });
    }
    for (k = 0; k < sw * sh; k++) { if (gor[k]) { say[k] = 0; } }
  }
  VERI.fotoRenkleri = function (piksel, tavan, w, h) {
    var n = Number.isInteger(tavan) && tavan >= 1 ? Math.min(tavan, 4) : 1, adet = piksel ? Math.floor(piksel.length / 4) : 0;
    if (!(w > 0 && h > 0)) { w = Math.round(Math.sqrt(adet)); h = w; if (w * h !== adet) { w = adet; h = 1; } }
    var k0 = adet ? simKucult(piksel, w, h) : null;
    if (!k0) { return []; }
    prArkaSil(k0);
    var B = simKaynakBolge(k0, simOznitelik(k0, SIM_L_TABAN)), top = new Float64Array(B.nr * 4), k, r;
    for (k = 0; k < k0.sw * k0.sh; k++) {
      if ((r = B.bol[k]) < 0) { continue; }
      top[r * 4] += k0.L[k]; top[r * 4 + 1] += k0.A[k]; top[r * 4 + 2] += k0.B[k]; top[r * 4 + 3]++;
    }
    var P = prPalet(), say = new Float64Array(P.length), bol = [], renk = [];
    for (r = 0; r < B.nr; r++) {
      var s = top[r * 4 + 3], q = s ? { s: s, L: top[r * 4] / s, a: top[r * 4 + 1] / s, b: top[r * 4 + 2] / s } : { s: 0 };
      bol.push(q); renk.push(s ? prEsle(P, q.L, q.a, q.b) : -1);
    }
    prBirlik(bol, renk, P);
    for (r = 0; r < B.nr; r++) { if (renk[r] >= 0) { say[renk[r]] += bol[r].s; } }
    return P.map(function (p, i) { return i; }).filter(function (i) { return B.opak && say[i] / B.opak >= PR_PAY; })
      .sort(function (i, j) { return say[j] - say[i] || i - j; }).slice(0, n).map(function (i) { return P[i].ad; });
  };
  // ④ FİGÜR KOLU (Okan 11 Eki "bu 4 renkli bir figür değil" · 16:0x "4 renk simülasyonu"): basılacak dosyanın
  // çizimi (sunucu `render`) varsa O AYNEN gösterilir; yoksa sağlayıcı görselinin 4 RENK SİMÜLASYONU
  // (VERI.dortRenkSimule, aşağıda) + simülasyon cümlesi. Hangi görselin gösterildiği her durumda cümleyle söylenir.
  VERI.FIGUR_RENDER_NOTU = "Bu görüntü basılacak dosyadan çizildi: figür bu renk bölgeleriyle basılır.";
  VERI.FIGUR_SIMULASYON_RENKLI = "Önizleme: figürün seçtiğin renklerle (en çok 4 renk bölgesi) yaklaşık görünümü; " +
    "basılan figür sadeleştirilmiş hâlidir, tam kopyası değildir.";
  VERI.FIGUR_SIMULASYON_TEK = "Önizleme: figürün seçtiğin tek renkle yaklaşık görünümü; " +
    "basılan figür sadeleştirilmiş hâlidir, tam kopyası değildir.";
  // Simülasyon tarayıcıda çalışamazsa (tuval okunamadı vb.) sağlayıcı görseli AYNEN gösterilir; cümle bunu söyler.
  VERI.FIGUR_ORNEK_NOTU = "Örnek görünüm — renkler basılacak figürü göstermez.";
  // ④ 4 RENK SİMÜLASYONU (Okan 11 Eki 16:0x "4 renk simülasyonu"; figür render-yok kolu + plaket): sağlayıcının
  // dokulu görseli piksel piksel boyanmaz (eski indirgeme gölge/dokuyu benekli gri-bej postere çeviriyordu); düzgün
  // renk BÖLGELERİNE sadeleştirilir — deterministik, tarayıcıda, kredi 0, harici API YOK:
  //  (a) gürültü/doku: uzun kenar SIM_KENAR px'e kutu ortalamasıyla (doğrusal ışıkta) küçültülür + 3×3 median (kenar korur);
  //  (b) BÖLGE ÖNCE, PALET SONRA (KraL-Foto4Renk-2; müşteri paletinde saç yarı Siyah yarı Ahşap bölünüyordu):
  //      kaynak görsel palete BAKMADAN renk bölgelerine ayrılır (simKaynakBolge: süper-piksel + sınır ortalamalı
  //      bölge birleştirme; öznitelik OKLab (L, a/k, b/k) — gölge (doğrusal RGB × s) L, a, b'yi AYNI oranla küçültür,
  //      ton a/L, b/L'de kalır; açıklık AZ ağırlıklı -> gölge/parlama bandı bölgeyi bölmez), sonra HER BÖLGE BÜTÜN
  //      OLARAK ortalama tonuna en yakın TEK palet rengini alır (SIM_L_AGIRLIK) — bir kaynak bölge iki renge
  //      bölünmez; iki bölge aynı renge düşebilir, yalnız belirgin farklı iki büyük komşu bölge aynı renge düşerse
  //      ucuz olan bir sonraki renge geçer (simKontrastKoru: plaket saçı tenle aynı renge düşüp kayboluyordu);
  //  (c) adacık: 3×3 çoğunluk (mod) süzgeci + siluet parlaması şeridi (simKenarSeridi) + opak alanın SIM_ADACIK'inden
  //      küçük adacık en uzun sınırı paylaştığı komşu bölgeye katılır;
  //  (d) orijinal boyuta büyütülür (yumuşatılmış bölge üyeliği, merdivensiz); bölge sınırına ince koyu kontur;
  //  (e) İNCE AYRINTI (ağız, kaş, göz çevresi): tam çözünürlükte bulunan koyu ince çizgiler (simCizgi) bölgeye
  //      yutulmaz, bölgeden koyu palet rengiyle (yoksa kontur koyusu) çizilir; benek çizgi sayılmaz.
  // Tek renk Siyah/Beyaz/Gri: aynı (a) yumuşatmasından o rengin tonunda gri ölçek (gölge kalır, doku/benek kalmaz).
  // renkler = seçili filament adları (Renkli: fotoğraftan çıkan renkler; tek renk: [ana renk]). Saydam piksel
  // (alfa < 128) dokunulmaz. piksel YERİNDE değişir ve döner; boş palet / bilinmeyen renk / boyut uyuşmazlığı -> null
  // (çağıran kaynak görseli gösterir). Küçük ölçekteki bölge etiketleri VERI.simulasyonBolgeleri ile okunur (ölçüm).
  // Süre (node, 1024 px prova görselleri, soğuk ilk çağrı, makine yükü ~10 altında): 104–139 ms (Foto4Renk-1 aynı koşulda 50–81).
  var SIM_KENAR = 256, SIM_L_AGIRLIK = 0.3, SIM_L_TABAN = 0.6, SIM_L_TABAN_B = 0.3, SIM_ADACIK = 0.0015, SIM_SERIT = 2, SIM_KONTUR = 0.62, SIM_KONTUR_BANT = 0.3;
  var SIM_TAU = 0.08, SIM_TAVAN_W = 0.8, SIM_SP_MIN = 6, SIM_SINIR = 0.002, SIM_BOLGE_MIN = 0.002, SIM_L_BOLGE = 0.08, SIM_ORT_TAVAN = 0.006, SIM_KONTRAST_BOY = 0.003, SIM_AYRIK = 0.03, SIM_AYRIK_PAY = 0.03, SIM_CIZGI_FARK = 45, SIM_CIZGI_BOY = 5, SIM_CIZGI_DL = 0.12;
  var LIN = null;
  function linTablo() {
    if (!LIN) {
      LIN = new Float64Array(256);
      for (var i = 0; i < 256; i++) { var c = i / 255; LIN[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
    }
    return LIN;
  }
  function linSrgb(v) {
    var c = v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(Math.max(v, 0), 1 / 2.4) - 0.055;
    return Math.max(0, Math.min(255, Math.round(c * 255)));
  }
  // Doğrusal RGB -> OKLab (Ottosson 2020).
  function oklab(r, g, b) {
    var l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    var m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    var s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  // Öznitelik mesafesi (L, a/k, b/k): açıklık farkı SIM_L_AGIRLIK ile AZ ağırlıklı.
  function simMesafe(L1, u1, v1, L2, u2, v2) {
    var dL = L1 - L2, du = u1 - u2, dv = v1 - v2;
    return SIM_L_AGIRLIK * dL * dL + du * du + dv * dv;
  }
  // Kaynak bölgeleme mesafesi: açıklık daha da AZ ağırlıklı (SIM_L_BOLGE) — aynı yüzeyin ışık/gölge/parlama
  // bandı tek bölge kalsın; ayrım ton/kroma sınırından gelir (saç/ten, ten/zemin).
  function simBolgeMesafe(L1, u1, v1, L2, u2, v2) {
    var dL = L1 - L2, du = u1 - u2, dv = v1 - v2;
    return SIM_L_BOLGE * dL * dL + du * du + dv * dv;
  }
  function median9(v, n) {
    for (var i = 1; i < n; i++) { var x = v[i], j = i - 1; while (j >= 0 && v[j] > x) { v[j + 1] = v[j]; j--; } v[j + 1] = x; }
    return v[n >> 1];
  }
  // (a) küçült + median -> { sw, sh, olc, say, L, A, B }; boyut uyuşmazlığında null.
  function simKucult(piksel, w, h) {
    if (!piksel || !(w > 0) || !(h > 0) || w % 1 || h % 1 || piksel.length < w * h * 4) { return null; }
    var T = linTablo(), olc = Math.max(1, Math.ceil(Math.max(w, h) / SIM_KENAR));
    var sw = Math.ceil(w / olc), sh = Math.ceil(h / olc), n = sw * sh;
    var sr = new Float64Array(n), sg = new Float64Array(n), sb = new Float64Array(n), say = new Uint32Array(n);
    var x, y, k, i;
    for (y = 0; y < h; y++) {
      var sat = ((y / olc) | 0) * sw;
      for (x = 0; x < w; x++) {
        i = (y * w + x) * 4;
        if (piksel[i + 3] < 128) { continue; }
        k = sat + ((x / olc) | 0);
        sr[k] += T[piksel[i]]; sg[k] += T[piksel[i + 1]]; sb[k] += T[piksel[i + 2]]; say[k]++;
      }
    }
    var L0 = new Float64Array(n), A0 = new Float64Array(n), B0 = new Float64Array(n);
    for (k = 0; k < n; k++) {
      if (!say[k]) { continue; }
      var o = oklab(sr[k] / say[k], sg[k] / say[k], sb[k] / say[k]);
      L0[k] = o[0]; A0[k] = o[1]; B0[k] = o[2];
    }
    var L = new Float64Array(n), A = new Float64Array(n), B = new Float64Array(n);
    var vl = [], va = [], vb = [];
    for (y = 0; y < sh; y++) {
      for (x = 0; x < sw; x++) {
        k = y * sw + x;
        if (!say[k]) { continue; }
        var c = 0;
        for (var dy = -1; dy <= 1; dy++) {
          var yy = y + dy;
          if (yy < 0 || yy >= sh) { continue; }
          for (var dx = -1; dx <= 1; dx++) {
            var xx = x + dx, q = yy * sw + xx;
            if (xx < 0 || xx >= sw || !say[q]) { continue; }
            vl[c] = L0[q]; va[c] = A0[q]; vb[c] = B0[q]; c++;
          }
        }
        L[k] = median9(vl, c); A[k] = median9(va, c); B[k] = median9(vb, c);
      }
    }
    return { sw: sw, sh: sh, olc: olc, say: say, L: L, A: A, B: B };
  }
  // (b) + (c): küçük görüntüde palet etiketleri (-1 = saydam hücre). Öznitelik (L, a/k, b/k), k = max(L, taban):
  // ton a/L, b/L gölgede sabit; koyu renkte taban kromanın gürültüsünü bastırır. Kaynak bölgeleri (palete bakmadan)
  // -> bölge başına TEK palet rengi (ortalama ton, simMesafe) -> kontrast koruma -> (c) temizliği.
  function simOznitelik(k0, taban) {
    var n = k0.sw * k0.sh, U = new Float64Array(n), V = new Float64Array(n);
    for (var k = 0; k < n; k++) {
      if (!k0.say[k]) { continue; }
      var bol = Math.max(k0.L[k], taban);
      U[k] = k0.A[k] / bol; V[k] = k0.B[k] / bol;
    }
    return { L: k0.L, U: U, V: V };
  }
  // Bölgenin rengi (KraL-FotoPalet): fotoRenkleri ile AYNI kural (prEsle), seçili paletle sınırlı — otomatik palet
  // hangi yüzeye hangi rengi seçtiyse simülasyon da o yüzeyi o renge boyar (eski simMesafe en-yakını gözlüğü yarı
  // Ahşap yarı Mavi, kahve gözü tenle aynı yapıyordu). Seçili paletten hiçbir renk kurallardan geçmezse (ör. mavi
  // yüzey, palet Kırmızı+Sarı) ya da geçen en iyi renk çok uzaksa (maliyet > PR_UZAK; ör. Beyaz'sız palette beyaz
  // tişört -> Siyah) simMesafe en-yakını yedektir. Kontrast koruma simMesafe maliyetleriyle (D) çalışır.
  function simEtiketle(k0, hex, adlar) {
    var sw = k0.sw, sh = k0.sh, n = sw * sh, et = new Int8Array(n), F = simOznitelik(k0, SIM_L_TABAN), k, j, r;
    var T = linTablo(), P = hex.map(function (c) {
      var o = oklab(T[c[0]], T[c[1]], T[c[2]]), bp = Math.max(o[0], SIM_L_TABAN);
      return [o[0], o[1] / bp, o[2] / bp];
    });
    var B = simKaynakBolge(k0, F), nr = B.nr, top = new Float64Array(nr * 4), lab = new Float64Array(nr * 2), renk = new Int8Array(nr);
    for (k = 0; k < n; k++) {
      if ((r = B.bol[k]) < 0) { continue; }
      top[r * 4] += F.L[k]; top[r * 4 + 1] += F.U[k]; top[r * 4 + 2] += F.V[k]; top[r * 4 + 3]++;
      lab[r * 2] += k0.A[k]; lab[r * 2 + 1] += k0.B[k];
    }
    var np = P.length, D = new Float64Array(nr * np), PP = prPalet(adlar), bol = [], rk = [];
    for (r = 0; r < nr; r++) {                           // kaynak bölgenin ORTALAMA tonu -> TEK palet rengi
      var s = top[r * 4 + 3], en = 0;
      for (j = 0; j < np; j++) {
        D[r * np + j] = simMesafe(top[r * 4] / s, top[r * 4 + 1] / s, top[r * 4 + 2] / s, P[j][0], P[j][1], P[j][2]);
        if (D[r * np + j] < D[r * np + en]) { en = j; }
      }
      var q = { s: s, L: top[r * 4] / s, a: lab[r * 2] / s, b: lab[r * 2 + 1] / s }, pd = [Infinity];
      var pe = prEsle(PP, q.L, q.a, q.b, pd);
      bol.push(q); rk.push(pe >= 0 && pd[0] <= PR_UZAK ? pe : en);
    }
    prBirlik(bol, rk, PP);
    for (r = 0; r < nr; r++) { renk[r] = rk[r]; }
    simKontrastKoru(B, sw, sh, top, D, np, renk);
    for (k = 0; k < n; k++) { et[k] = B.bol[k] < 0 ? -1 : renk[B.bol[k]]; }
    simAdacik(et, sw, sh, P.length, B.opak);
    return et;
  }
  // KONTRAST KORUMA: sınır paylaşan iki BÜYÜK kaynak bölge (opak alanın ≥ SIM_KONTRAST_BOY'u) kaynakta belirgin
  // farklı tondaysa (ortalama farkı ≥ SIM_AYRIK) ama aynı palet rengine düştüyse (plaket: koyu saç ile ten ikisi de
  // Ahşap -> saç kaybolur), maliyet artışı küçük olan bölge (≤ SIM_AYRIK_PAY) bir sonraki en yakın renge geçer —
  // o renk başka bir belirgin komşusunda yoksa. Bölge yine TEK renktir (bütünlük bozulmaz); en uzun sınır önce.
  function simKontrastKoru(B, sw, sh, top, D, np, renk) {
    var nr = B.nr, bol = B.bol, sinir = new Map(), k, x, y, a, b, j;
    for (y = 0; y < sh; y++) {
      for (x = 0; x < sw; x++) {
        k = y * sw + x;
        if (bol[k] < 0) { continue; }
        for (var yon = 0; yon < 2; yon++) {
          var q = yon ? (y + 1 < sh ? k + sw : -1) : (x + 1 < sw ? k + 1 : -1);
          if (q < 0 || bol[q] < 0 || bol[q] === bol[k]) { continue; }
          var anahtar = Math.min(bol[k], bol[q]) * nr + Math.max(bol[k], bol[q]);
          sinir.set(anahtar, (sinir.get(anahtar) || 0) + 1);
        }
      }
    }
    var buyuk = Math.max(1, B.opak * SIM_KONTRAST_BOY), cift = [], kom = [];
    for (a = 0; a < nr; a++) { kom.push([]); }
    function fark(a1, b1) {
      var na = top[a1 * 4 + 3], nb = top[b1 * 4 + 3];
      return simMesafe(top[a1 * 4] / na, top[a1 * 4 + 1] / na, top[a1 * 4 + 2] / na,
        top[b1 * 4] / nb, top[b1 * 4 + 1] / nb, top[b1 * 4 + 2] / nb);
    }
    sinir.forEach(function (uz, anahtar) {
      a = Math.floor(anahtar / nr); b = anahtar % nr;
      if (top[a * 4 + 3] < buyuk || top[b * 4 + 3] < buyuk || fark(a, b) < SIM_AYRIK) { return; }
      cift.push([uz, a, b]); kom[a].push(b); kom[b].push(a);
    });
    cift.sort(function (p, q) { return q[0] - p[0] || p[1] - q[1] || p[2] - q[2]; });
    cift.forEach(function (c) {
      if (renk[c[1]] !== renk[c[2]]) { return; }
      var secR = -1, secJ = -1, secM = Infinity;
      [c[1], c[2]].forEach(function (r) {
        for (j = 0; j < np; j++) {
          if (j === renk[r] || kom[r].some(function (o) { return renk[o] === j; })) { continue; }
          var m = D[r * np + j] - D[r * np + renk[r]];
          if (m < secM) { secM = m; secR = r; secJ = j; }
        }
      });
      if (secR >= 0 && secM <= SIM_AYRIK_PAY) { renk[secR] = secJ; }
    });
  }
  // KAYNAK BÖLGELERİ (palete BAKMADAN). 1) Süper-piksel: graf tabanlı birleştirme (Felzenszwalb–Huttenlocher 2004);
  // kenar = 8-komşu hücre çifti, ağırlık = √simBolgeMesafe (L çok az ağırlıklı -> gölge geçişi ucuz, ton/kroma
  // sınırı pahalı); kenar ≤ min(iç fark + SIM_TAU/boy) ise birleşir, SIM_SP_MIN altı parça en benzer komşuya. Tek
  // zayıf kenardan sızabildiği için (saçın ışıklı yanı tene akıyordu) yalnız küçük parçalar üretir; 2) bölgeler
  // simSinirBirlestir ile kurulur. Bir kaynak bölge tek palet rengi alır (simEtiketle). -> { bol (-1 saydam), nr, opak }
  function simKaynakBolge(k0, F) {
    var sw = k0.sw, sh = k0.sh, n = sw * sh, say = k0.say, k, x, y, e, a, b, opak = 0;
    var ea = new Int32Array(n * 4), eb = new Int32Array(n * 4), ek = new Uint16Array(n * 4), ne = 0;
    var KOVA = 4096, kov = new Int32Array(KOVA + 1);
    for (y = 0; y < sh; y++) {
      for (x = 0; x < sw; x++) {
        k = y * sw + x;
        if (!say[k]) { continue; }
        opak++;
        for (var yon = 0; yon < 4; yon++) {              // sağ · alt · sağ-alt · sol-alt
          var nx = x + (yon === 0 || yon === 2 ? 1 : yon === 3 ? -1 : 0), ny = y + (yon ? 1 : 0);
          if (nx < 0 || nx >= sw || ny >= sh || !say[ny * sw + nx]) { continue; }
          var q = ny * sw + nx, w0 = Math.sqrt(simBolgeMesafe(F.L[k], F.U[k], F.V[k], F.L[q], F.U[q], F.V[q]));
          ea[ne] = k; eb[ne] = q; ek[ne] = Math.min(KOVA - 1, Math.floor(w0 * KOVA / SIM_TAVAN_W)); kov[ek[ne] + 1]++; ne++;
        }
      }
    }
    for (e = 1; e <= KOVA; e++) { kov[e] += kov[e - 1]; }     // kova sıralaması (ağırlık 1/KOVA çözünürlükte)
    var sira = new Int32Array(ne);
    for (e = 0; e < ne; e++) { sira[kov[ek[e]]++] = e; }
    var ana = new Int32Array(n), boy = new Int32Array(n), ic = new Float64Array(n);
    for (k = 0; k < n; k++) { ana[k] = k; boy[k] = 1; }
    function bul(p) { while (ana[p] !== p) { ana[p] = ana[ana[p]]; p = ana[p]; } return p; }
    function birles(p, q, w1) {
      if (boy[p] < boy[q]) { var t = p; p = q; q = t; }
      ana[q] = p; boy[p] += boy[q]; ic[p] = Math.max(ic[p], ic[q], w1);
    }
    for (e = 0; e < ne; e++) {
      var s = sira[e], w = (ek[s] + 0.5) * SIM_TAVAN_W / KOVA;
      a = bul(ea[s]); b = bul(eb[s]);
      if (a !== b && w <= Math.min(ic[a] + SIM_TAU / boy[a], ic[b] + SIM_TAU / boy[b])) { birles(a, b, w); }
    }
    for (e = 0; e < ne; e++) {
      a = bul(ea[sira[e]]); b = bul(eb[sira[e]]);
      if (a !== b && (boy[a] < SIM_SP_MIN || boy[b] < SIM_SP_MIN)) { birles(a, b, 0); }
    }
    var bol = new Int32Array(n).fill(-1), no = new Int32Array(n).fill(-1), nr = 0;
    for (k = 0; k < n; k++) {
      if (!say[k]) { continue; }
      a = bul(k);
      if (no[a] < 0) { no[a] = nr++; }
      bol[k] = no[a];
    }
    return simSinirBirlestir(bol, nr, sw, sh, F, simOznitelik(k0, SIM_L_TABAN_B), opak);
  }
  // Süper-piksel komşuluk grafiği: SINIR ADIMI = sınır boyunca, iki yandan birer hücre öteden simBolgeMesafe
  // ORTALAMASI (yumuşatılmış geçiş 1–2 hücre; öznitelik tabanı SIM_L_TABAN_B: koyu yüzeyin sert gölgesi de tonu
  // değiştirmez). En küçük adımlı çift (< SIM_SINIR) birleşir — iki bölgenin ORTALAMA tonları da yakınsa
  // (< SIM_ORT_TAVAN; çerçeve ile zemin kademeli pahla zincirlenmesin). Adım toplamları toplanabilir: birleşen bölgenin
  // sınırları yeniden ölçülmez. ORTALAMA ölçü tek zayıf kenardan sızmaz (saç ışıklı yanı tene akmaz); gölgenin yavaş
  // geçişi her sınırda küçük adımdır. Sonra opak alanın SIM_BOLGE_MIN'inden küçük bölge en küçük adımlı komşusuna.
  function simSinirBirlestir(bol, nr, sw, sh, F, Fb, opak) {
    var n = sw * sh, k, x, y, a, b, kom = [], boy = new Int32Array(nr), ort = new Float64Array(nr * 3);
    for (a = 0; a < nr; a++) { kom.push(new Map()); }
    for (k = 0; k < n; k++) {
      if ((a = bol[k]) < 0) { continue; }
      boy[a]++; ort[a * 3] += F.L[k]; ort[a * 3 + 1] += F.U[k]; ort[a * 3 + 2] += F.V[k];
    }
    function ortFark(a1, b1) {                           // iki bölgenin ORTALAMA ton farkı
      var na = boy[a1], nb = boy[b1];
      return simBolgeMesafe(ort[a1 * 3] / na, ort[a1 * 3 + 1] / na, ort[a1 * 3 + 2] / na,
        ort[b1 * 3] / nb, ort[b1 * 3 + 1] / nb, ort[b1 * 3 + 2] / nb);
    }
    for (y = 0; y < sh; y++) {
      for (x = 0; x < sw; x++) {
        k = y * sw + x;
        if (bol[k] < 0) { continue; }
        for (var yon = 0; yon < 2; yon++) {
          var q = yon ? (y + 1 < sh ? k + sw : -1) : (x + 1 < sw ? k + 1 : -1);
          if (q < 0 || bol[q] < 0 || bol[q] === bol[k]) { continue; }
          var ad1 = yon ? sw : 1, p = (yon ? y > 0 : x > 0) && bol[k - ad1] >= 0 ? k - ad1 : k;
          var s = (yon ? y + 2 < sh : x + 2 < sw) && bol[q + ad1] >= 0 ? q + ad1 : q;
          var d = simBolgeMesafe(Fb.L[p], Fb.U[p], Fb.V[p], Fb.L[s], Fb.U[s], Fb.V[s]);
          a = bol[k]; b = bol[q];
          var t = kom[a].get(b);
          if (!t) { t = [0, 0]; kom[a].set(b, t); kom[b].set(a, t); }
          t[0] += d; t[1]++;
        }
      }
    }
    var ana = new Int32Array(nr);
    for (a = 0; a < nr; a++) { ana[a] = a; }
    function katil(a1, b1) {                             // b1 -> a1
      kom[b1].forEach(function (t, c) {
        kom[c].delete(b1);
        if (c === a1) { return; }
        var u = kom[a1].get(c);
        if (u) { u[0] += t[0]; u[1] += t[1]; } else { kom[a1].set(c, t); kom[c].set(a1, t); }
      });
      kom[b1] = new Map(); ana[b1] = a1; boy[a1] += boy[b1]; boy[b1] = 0;
      for (var i = 0; i < 3; i++) { ort[a1 * 3 + i] += ort[b1 * 3 + i]; }
    }
    var esik = Math.max(1, Math.floor(opak * SIM_BOLGE_MIN));
    for (var tur = 0; tur < 2; tur++) {                  // tur 0: adım < SIM_SINIR · tur 1: küçük bölge
      for (;;) {
        var ea = -1, eb = -1, ed = Infinity;
        for (a = 0; a < nr; a++) {
          if (!boy[a] || (tur && boy[a] >= esik)) { continue; }
          kom[a].forEach(function (t, c) {
            var m = t[0] / t[1];
            if (m < ed && (tur || (c > a && ortFark(a, c) < SIM_ORT_TAVAN))) { ed = m; ea = a; eb = c; }
          });
        }
        if (ea < 0 || (!tur && !(ed < SIM_SINIR))) { break; }
        if (boy[ea] < boy[eb]) { katil(eb, ea); } else { katil(ea, eb); }
      }
    }
    var no = new Int32Array(nr).fill(-1), m2 = 0;
    for (k = 0; k < n; k++) {
      if (bol[k] < 0) { continue; }
      a = bol[k];
      while (ana[a] !== a) { a = ana[a]; }
      if (no[a] < 0) { no[a] = m2++; }
      bol[k] = no[a];
    }
    return { bol: bol, nr: m2, opak: opak };
  }
  function simAdacik(et, sw, sh, np, opak) {
    var n = sw * sh, k, j, x, y, tur;
    // 3×3 çoğunluk (mod) süzgeci, 2 tur: komşuların yarısından fazlası başka renkse hücre o renge geçer.
    var sayac = new Int32Array(np);
    for (tur = 0; tur < 2; tur++) {
      var yeni = et.slice();
      for (y = 0; y < sh; y++) {
        for (x = 0; x < sw; x++) {
          k = y * sw + x;
          if (et[k] < 0) { continue; }
          var e0 = et[k];                                // iç hücre, 8 komşu aynı: değişmez (kısa yol)
          if (x > 0 && y > 0 && x < sw - 1 && y < sh - 1 && et[k - 1] === e0 && et[k + 1] === e0 &&
              et[k - sw] === e0 && et[k + sw] === e0 && et[k - sw - 1] === e0 && et[k - sw + 1] === e0 &&
              et[k + sw - 1] === e0 && et[k + sw + 1] === e0) { continue; }
          sayac.fill(0);
          var top = 0;
          for (var dy = -1; dy <= 1; dy++) {
            var yy = y + dy;
            if (yy < 0 || yy >= sh) { continue; }
            for (var dx = -1; dx <= 1; dx++) {
              var xx = x + dx;
              if (xx < 0 || xx >= sw || et[yy * sw + xx] < 0) { continue; }
              sayac[et[yy * sw + xx]]++; top++;
            }
          }
          var en = et[k];
          for (j = 0; j < np; j++) { if (sayac[j] > sayac[en]) { en = j; } }
          if (sayac[en] * 2 > top) { yeni[k] = en; }
        }
      }
      et.set(yeni);
    }
    simKenarSeridi(et, sw, sh, np);
    // Adacık: 4-komşulu bileşen opak alanın SIM_ADACIK'inden küçükse en uzun sınırı paylaştığı komşu renge katılır.
    var esik = Math.max(1, Math.floor(opak * SIM_ADACIK)), bil = new Int32Array(n), yigin = new Int32Array(n);
    var sinir = new Int32Array(np);
    for (tur = 0; tur < 8; tur++) {
      bil.fill(-1);
      var degisti = false, no = 0;
      for (var s = 0; s < n; s++) {
        if (et[s] < 0 || bil[s] >= 0) { continue; }
        var renk = et[s], ust = 0, alt = 0;
        bil[s] = no; yigin[ust++] = s;
        sinir.fill(0);
        while (alt < ust) {
          var p = yigin[alt++], px = p % sw, py = (p / sw) | 0;
          for (j = 0; j < 4; j++) {
            var q = j === 0 ? (px > 0 ? p - 1 : -1) : j === 1 ? (px < sw - 1 ? p + 1 : -1) : j === 2 ? (py > 0 ? p - sw : -1) : (py < sh - 1 ? p + sw : -1);
            if (q < 0 || et[q] < 0) { continue; }
            if (et[q] === renk) { if (bil[q] < 0) { bil[q] = no; yigin[ust++] = q; } } else { sinir[et[q]]++; }
          }
        }
        no++;
        if (ust >= esik) { continue; }
        var hedef = -1;
        for (j = 0; j < np; j++) { if (sinir[j] > 0 && (hedef < 0 || sinir[j] > sinir[hedef])) { hedef = j; } }
        if (hedef < 0) { continue; }                     // komşusu yalnız saydam: ayrı parça, dokunulmaz
        for (j = 0; j < ust; j++) { et[yigin[j]] = hedef; }
        degisti = true;
      }
      if (!degisti) { break; }
    }
  }
  // Kenar şeridi: saydamlığa SIM_SERIT+1 hücreden yakın ve 2·SIM_SERIT+1 hücreden İNCE bölge parçası (stüdyo
  // ışığının siluet parlaması: saç kenarı tene, gövde kenarı açık renge düşüyordu) — açma (aşındır + genişlet)
  // işleminde kaybolan hücreler — kalın komşu bölgeye katılır. İç ayrıntı (kaş, kapı kolu) siluetten uzak: dokunulmaz.
  // Görüntü dışı saydam sayılır.
  function simKenarSeridi(et, sw, sh, np) {
    var n = sw * sh, r = SIM_SERIT, k, x, y, t, dx, dy, xx, yy, q;
    var ero = et.slice(), gec;
    for (t = 0; t < r; t++) {                            // aşındır: 8 komşunun hepsi aynı bölgeyse kalır
      gec = ero.slice();
      for (y = 0; y < sh; y++) {
        for (x = 0; x < sw; x++) {
          k = y * sw + x;
          if (gec[k] < 0) { continue; }
          if (x === 0 || y === 0 || x === sw - 1 || y === sh - 1) { ero[k] = -1; continue; }
          for (dy = -1; dy <= 1 && ero[k] >= 0; dy++) {
            for (dx = -1; dx <= 1; dx++) { if (gec[k + dy * sw + dx] !== gec[k]) { ero[k] = -1; break; } }
          }
        }
      }
    }
    for (t = 0; t < r; t++) {                            // genişlet: aynı bölgenin içinde, aşınmış çekirdekten
      gec = ero.slice();
      for (y = 0; y < sh; y++) {
        for (x = 0; x < sw; x++) {
          k = y * sw + x;
          if (gec[k] >= 0 || et[k] < 0) { continue; }
          for (dy = -1; dy <= 1 && ero[k] < 0; dy++) {
            yy = y + dy;
            if (yy < 0 || yy >= sh) { continue; }
            for (dx = -1; dx <= 1; dx++) {
              xx = x + dx;
              if (xx >= 0 && xx < sw && gec[yy * sw + xx] === et[k]) { ero[k] = et[k]; break; }
            }
          }
        }
      }
    }
    var yakin = new Uint8Array(n), on;                   // saydamlığa (ya da görüntü kenarına) ≤ r+1 hücre
    for (k = 0; k < n; k++) { yakin[k] = et[k] < 0 ? 1 : 0; }
    for (t = 0; t <= r; t++) {
      on = yakin.slice();
      for (y = 0; y < sh; y++) {
        for (x = 0; x < sw; x++) {
          k = y * sw + x;
          if (on[k]) { continue; }
          if (x === 0 || y === 0 || x === sw - 1 || y === sh - 1) { yakin[k] = 1; continue; }
          for (dy = -1; dy <= 1 && !yakin[k]; dy++) {
            for (dx = -1; dx <= 1; dx++) { if (on[k + dy * sw + dx]) { yakin[k] = 1; break; } }
          }
        }
      }
    }
    var ince = new Uint8Array(n), kalan = 0, sayac = new Int32Array(np), cozulen = new Int32Array(n), yeni;
    for (k = 0; k < n; k++) { if (et[k] >= 0 && ero[k] !== et[k] && yakin[k]) { ince[k] = 1; kalan++; } }
    for (t = 0; t < 4 * r + 4 && kalan; t++) {           // ince hücre, ince OLMAYAN komşularının en sık bölgesine
      var nc = 0;
      yeni = et.slice();
      for (y = 0; y < sh; y++) {
        for (x = 0; x < sw; x++) {
          k = y * sw + x;
          if (!ince[k]) { continue; }
          sayac.fill(0);
          var en = -1;
          for (dy = -1; dy <= 1; dy++) {
            yy = y + dy;
            if (yy < 0 || yy >= sh) { continue; }
            for (dx = -1; dx <= 1; dx++) {
              xx = x + dx;
              if (xx < 0 || xx >= sw) { continue; }
              q = yy * sw + xx;
              if (ince[q] || et[q] < 0 || et[q] === et[k]) { continue; }
              sayac[et[q]]++;
              if (en < 0 || sayac[et[q]] > sayac[en]) { en = et[q]; }
            }
          }
          if (en >= 0) { yeni[k] = en; cozulen[nc++] = k; }
        }
      }
      if (!nc) { break; }
      for (q = 0; q < nc; q++) { ince[cozulen[q]] = 0; }
      kalan -= nc;
      et.set(yeni);
    }
  }
  // Tek ana renk: yumuşatılmış açıklık (OKLab L; a = b = 0 gri) çift doğrusal büyütülür ve rengin tonuna oturtulur
  // (taban rengin %40'ı .. %105'i; beyaz figür açık zeminde silinmesin): gölge kalır, doku/benek kalmaz; r = g = b.
  function simGri(piksel, w, h, k0, taban) {
    var sw = k0.sw, sh = k0.sh, olc = k0.olc, gl = new Float64Array(sw * sh), x, y, k;
    for (k = 0; k < sw * sh; k++) { gl[k] = k0.say[k] ? linSrgb(k0.L[k] * k0.L[k] * k0.L[k]) / 255 : -1; }
    for (y = 0; y < h; y++) {
      var fy = (y + 0.5) / olc - 0.5, y0 = Math.floor(fy), ty = fy - y0;
      for (x = 0; x < w; x++) {
        var i = (y * w + x) * 4;
        if (piksel[i + 3] < 128) { continue; }
        var fx = (x + 0.5) / olc - 0.5, x0 = Math.floor(fx), tx = fx - x0, top = 0, ag = 0;
        for (var j = 0; j < 4; j++) {
          var ox = j & 1, oy = j >> 1, a = (ox ? tx : 1 - tx) * (oy ? ty : 1 - ty);
          var v = gl[Math.max(0, Math.min(sh - 1, y0 + oy)) * sw + Math.max(0, Math.min(sw - 1, x0 + ox))];
          if (v >= 0 && a > 0) { top += v * a; ag += a; }
        }
        var g = ag > 0 ? top / ag : Math.max(0, gl[((y / olc) | 0) * sw + ((x / olc) | 0)]);
        var c = Math.max(0, Math.min(255, Math.round(taban * (0.4 + 0.65 * g))));
        piksel[i] = c; piksel[i + 1] = c; piksel[i + 2] = c;
      }
    }
    return piksel;
  }
  // (d) büyütme: her hücrenin bölge ÜYELİĞİ küçük ölçekte 3×3 çadır süzgeciyle yumuşatılır (köşeler yuvarlanır),
  // piksele en yakın 4 hücre merkezinden çift doğrusal toplanır, en ağır bölge kazanır (en-yakın büyütmenin merdiveni
  // yok). İki opak bölge arasında kazanan ile ikincinin farkı SIM_KONTUR_BANT'tan küçükse piksel ince koyu konturdur
  // (bölgenin kendi renginin SIM_KONTUR katı; saydam komşu kontur üretmez).
  function simBuyut(piksel, w, h, k0, et, rgb, cz) {
    var sw = k0.sw, sh = k0.sh, olc = k0.olc, np = rgb.length, n = sw * sh, x, y, j, k;
    var koyu = rgb.map(function (c) { return c.map(function (v) { return Math.round(v * SIM_KONTUR); }); });
    var uy = new Float32Array(n * np), ag = new Float64Array(np);
    for (y = 0; y < sh; y++) {
      for (x = 0; x < sw; x++) {
        k = y * sw + x;
        if (et[k] < 0) { continue; }
        var top = 0;
        for (var dy = -1; dy <= 1; dy++) {
          var yy = y + dy;
          if (yy < 0 || yy >= sh) { continue; }
          for (var dx = -1; dx <= 1; dx++) {
            var xx = x + dx, q = yy * sw + xx;
            if (xx < 0 || xx >= sw || et[q] < 0) { continue; }
            var a0 = (dx ? 1 : 2) * (dy ? 1 : 2);
            uy[k * np + et[q]] += a0; top += a0;
          }
        }
        for (j = 0; j < np; j++) { uy[k * np + j] /= top; }
      }
    }
    for (y = 0; y < h; y++) {
      var fy = (y + 0.5) / olc - 0.5, y0 = Math.floor(fy), ty = fy - y0;
      for (x = 0; x < w; x++) {
        var i = (y * w + x) * 4;
        if (piksel[i + 3] < 128) { continue; }
        var fx = (x + 0.5) / olc - 0.5, x0 = Math.floor(fx), tx = fx - x0;
        for (j = 0; j < np; j++) { ag[j] = 0; }
        for (var c4 = 0; c4 < 4; c4++) {
          var ox = c4 & 1, oy = c4 >> 1, a = (ox ? tx : 1 - tx) * (oy ? ty : 1 - ty);
          if (a <= 0) { continue; }
          var b = (Math.max(0, Math.min(sh - 1, y0 + oy)) * sw + Math.max(0, Math.min(sw - 1, x0 + ox))) * np;
          for (j = 0; j < np; j++) { ag[j] += a * uy[b + j]; }
        }
        var en = -1, iki = 0;
        for (j = 0; j < np; j++) {
          if (ag[j] <= 0) { continue; }
          if (en < 0 || ag[j] > ag[en]) { if (en >= 0) { iki = ag[en]; } en = j; } else if (ag[j] > iki) { iki = ag[j]; }
        }
        if (en < 0) { en = simEnYakinEtiket(et, sw, sh, (x / olc) | 0, (y / olc) | 0); }
        if (en < 0) { continue; }
        var c = iki > 0 && ag[en] - iki < SIM_KONTUR_BANT ? koyu[en] : rgb[en];
        if (cz && cz.bil[y * w + x] >= 0) {               // ince koyu çizgi: bölgeye yutulmaz
          var cj = cz.renk[cz.bil[y * w + x] * np + en];
          c = cj >= 0 ? rgb[cj] : koyu[en];
        }
        piksel[i] = c[0]; piksel[i + 1] = c[1]; piksel[i + 2] = c[2];
      }
    }
    return piksel;
  }
  // İNCE AYRINTI (ağız, kaş, göz çevresi): küçültme 1 hücreden ince çizgiyi ortalayıp siler; bu yüzden çizgiler
  // TAM çözünürlükte bulunur. Açıklık (sRGB luma) üzerinde siyah top-hat: kapama (yarıçap r kare: önce en büyük,
  // sonra en küçük; saydam piksel hesaba girmez) − açıklık ≥ SIM_CIZGI_FARK olan piksel = çevresinden belirgin koyu
  // ve ≤ 2r px kalın. Siluete r+1 px'ten yakın piksel aday DEĞİL (kenar gölgesi çizgi sayılmaz). 8-komşu bileşen
  // ÇİZGİ ise korunur: uzun kenarı ≥ SIM_CIZGI_BOY·r ve ortalama kalınlığı (alan / uzun kenar) ≤ 2r+1 — 4×4 benek
  // çizgi DEĞİLDİR, adacık süzgecinin işidir. Çizgi rengi (simBuyut): bulunduğu bölgenin renginden en az
  // SIM_CIZGI_DL koyu palet renklerinden çizginin kendi tonuna en yakını; yoksa bölgenin kontur koyusu.
  // -> { bil (piksel başına bileşen, -1 yok), renk (bileşen × bölge rengi -> palet indeksi, -1 kontur) } | null.
  // (2r+1) kare en büyük süzgeci kay -> hed (kay ara bellek olarak bozulur); L = r+1'den büyük-eşit 2'nin kuvveti.
  function simGenislet(kay, hed, w, h, r, L) {
    var l, u, v, i1, i2, y, b0, b1, n = w * h;
    for (l = 1; l < L; l *= 2) {                         // yatay ikiye katlama: kay[i] = [i, i+2l) en büyüğü
      for (y = 0; y < h; y++) {
        b0 = y * w;
        for (u = 0; u < w; u++) { v = kay[b0 + (u + l < w ? u + l : w - 1)]; if (v > kay[b0 + u]) { kay[b0 + u] = v; } }
      }
    }
    for (y = 0; y < h; y++) {
      b0 = y * w;
      for (u = 0; u < w; u++) {
        i1 = u - r < 0 ? 0 : u - r; i2 = u + r - L + 1; i2 = i2 < 0 ? 0 : i2 > w - 1 ? w - 1 : i2;
        v = kay[b0 + i1]; hed[b0 + u] = kay[b0 + i2] > v ? kay[b0 + i2] : v;
      }
    }
    for (l = 1; l < L; l *= 2) {                         // dikey (satır satır, bellekte sürekli)
      for (y = 0; y < h; y++) {
        b0 = y * w; b1 = (y + l < h ? y + l : h - 1) * w;
        for (u = 0; u < w; u++) { v = hed[b1 + u]; if (v > hed[b0 + u]) { hed[b0 + u] = v; } }
      }
    }
    for (y = 0; y < h; y++) {
      i1 = (y - r < 0 ? 0 : y - r) * w; i2 = y + r - L + 1; i2 = (i2 < 0 ? 0 : i2 > h - 1 ? h - 1 : i2) * w;
      for (u = 0; u < w; u++) { v = hed[i1 + u]; kay[y * w + u] = hed[i2 + u] > v ? hed[i2 + u] : v; }
    }
    for (u = 0; u < n; u++) { hed[u] = kay[u]; }
  }
  function simCizgi(piksel, w, h, rgb) {
    var n = w * h, r = Math.max(2, Math.round(Math.max(w, h) * 3 / 1024)), x, y, i, k, t, d;
    // Kapama YARIM çözünürlükte (maliyet ~¼): 2×2 hücrenin EN KOYU opak pikseli (ince koyu çizgi küçültmede
    // kaybolmaz; opaksız hücre -1), yarıçap rh = ⌈r/2⌉. Aday testi TAM çözünürlükte piksel piksel: hücrenin kapama
    // değeri − pikselin açıklığı -> çizgi şekli piksel hassas kalır.
    var hw = (w + 1) >> 1, hh = (h + 1) >> 1, hn = hw * hh, rh = (r + 1) >> 1, L = 1;
    var Y = new Int16Array(n), A = new Int16Array(hn).fill(32767), B2 = new Int16Array(hn), sayd = new Int32Array((w + 1) * (h + 1));
    for (y = 0; y < h; y++) {
      var satir = 0, hs = (y >> 1) * hw;
      for (x = 0; x < w; x++) {
        k = y * w + x; i = k * 4;
        if (piksel[i + 3] < 128) { Y[k] = -1; satir++; } else {
          Y[k] = (77 * piksel[i] + 150 * piksel[i + 1] + 29 * piksel[i + 2]) >> 8;
          if (Y[k] < A[hs + (x >> 1)]) { A[hs + (x >> 1)] = Y[k]; }
        }
        sayd[(y + 1) * (w + 1) + x + 1] = sayd[y * (w + 1) + x + 1] + satir;
      }
    }
    for (k = 0; k < hn; k++) { if (A[k] === 32767) { A[k] = -1; } }
    // Kapama = −genişlet(−genişlet(Y)); genişlet = (2rh+1) kare en büyük süzgeci (simGenislet, piksel başı O(log r)).
    // Saydam (-1) en büyükte kendiliğinden kaybeder; ikinci genişletmede adayın komşuluğunda saydam yoktur (siluet
    // payı yk): sonuç adaylar için kesindir.
    while (L < rh + 1) { L *= 2; }
    simGenislet(A, B2, hw, hh, rh, L);
    for (k = 0; k < hn; k++) { A[k] = -B2[k]; }
    simGenislet(A, B2, hw, hh, rh, L);
    var aday = new Uint8Array(n), yk = 2 * rh + 2, adet = 0;
    for (y = yk; y < h - yk; y++) {
      for (x = yk; x < w - yk; x++) {
        k = y * w + x;
        if (Y[k] < 0 || -B2[(y >> 1) * hw + (x >> 1)] - Y[k] < SIM_CIZGI_FARK) { continue; }
        var x0 = x - yk, y0 = y - yk, x1 = x + yk + 1, y1 = y + yk + 1;
        if (sayd[y1 * (w + 1) + x1] - sayd[y0 * (w + 1) + x1] - sayd[y1 * (w + 1) + x0] + sayd[y0 * (w + 1) + x0]) { continue; }
        aday[k] = 1; adet++;
      }
    }
    if (!adet) { return null; }
    var bil = new Int32Array(n).fill(-1), yigin = new Int32Array(adet), T = linTablo(), ort = [], nb = 0;
    for (var s0 = 0; s0 < n; s0++) {
      if (!aday[s0] || bil[s0] !== -1) { continue; }
      var ust = 0, alt = 0, mnx = w, mxx = 0, mny = h, mxy = 0, lr = 0, lg = 0, lb = 0;
      bil[s0] = -2; yigin[ust++] = s0;
      while (alt < ust) {
        var p = yigin[alt++], px = p % w, py = (p / w) | 0;
        mnx = Math.min(mnx, px); mxx = Math.max(mxx, px); mny = Math.min(mny, py); mxy = Math.max(mxy, py);
        lr += T[piksel[p * 4]]; lg += T[piksel[p * 4 + 1]]; lb += T[piksel[p * 4 + 2]];
        for (d = 0; d < 9; d++) {
          var q = p + ((d / 3) | 0) * w - w + (d % 3) - 1, qx = px + (d % 3) - 1;
          if (d === 4 || qx < 0 || qx >= w || q < 0 || q >= n || !aday[q] || bil[q] !== -1) { continue; }
          bil[q] = -2; yigin[ust++] = q;
        }
      }
      var uzun = Math.max(mxx - mnx, mxy - mny) + 1, cizgi = uzun >= SIM_CIZGI_BOY * r && ust / uzun <= 2 * r + 1;
      for (t = 0; t < ust; t++) { bil[yigin[t]] = cizgi ? nb : -3; }
      if (cizgi) { ort.push(oklab(lr / ust, lg / ust, lb / ust)); nb++; }
    }
    if (!nb) { return null; }
    for (k = 0; k < n; k++) { if (bil[k] < -1) { bil[k] = -1; } }
    var np = rgb.length, P = rgb.map(function (c) { return oklab(T[c[0]], T[c[1]], T[c[2]]); });
    var renk = new Int8Array(nb * np).fill(-1);
    for (var b = 0; b < nb; b++) {
      var o = ort[b], ko = Math.max(o[0], SIM_L_TABAN);
      for (var en = 0; en < np; en++) {
        var ed = Infinity;
        for (var j = 0; j < np; j++) {
          if (P[j][0] > P[en][0] - SIM_CIZGI_DL) { continue; }
          var kp = Math.max(P[j][0], SIM_L_TABAN);
          var dd = simMesafe(o[0], o[1] / ko, o[2] / ko, P[j][0], P[j][1] / kp, P[j][2] / kp);
          if (dd < ed) { ed = dd; renk[b * np + en] = j; }
        }
      }
    }
    return { bil: bil, renk: renk };
  }
  // Opak piksel 4 komşusu da saydam hücrede kaldıysa: en yakın etiketli hücre (yarıçap ≤ 2), yoksa -1.
  function simEnYakinEtiket(et, sw, sh, cx, cy) {
    for (var r = 1; r < 3; r++) {
      for (var dy = -r; dy <= r; dy++) {
        for (var dx = -r; dx <= r; dx++) {
          var nx = cx + dx, ny = cy + dy;
          if (nx >= 0 && nx < sw && ny >= 0 && ny < sh && et[ny * sw + nx] >= 0) { return et[ny * sw + nx]; }
        }
      }
    }
    return -1;
  }
  function simPalet(renkler) {
    if (!Array.isArray(renkler) || !renkler.length || renkler.some(function (a) { return !VERI.RENK_HEX[a]; })) { return null; }
    return renkRgb(renkler);
  }
  // Ölçüm/test kapısı: aynı (a)–(c) adımlarının küçük görüntüdeki bölge etiketleri { sw, sh, olc, et } (null = geçersiz).
  VERI.simulasyonBolgeleri = function (piksel, w, h, renkler) {
    var rgb = simPalet(renkler), k0 = rgb && simKucult(piksel, w, h);
    return k0 ? { sw: k0.sw, sh: k0.sh, olc: k0.olc, et: simEtiketle(k0, rgb, renkler) } : null;
  };
  VERI.dortRenkSimule = function (piksel, w, h, renkler) {
    var rgb = simPalet(renkler), k0 = rgb && simKucult(piksel, w, h);
    if (!k0) { return null; }
    if (renkler.length === 1 && VERI.ANA_RENKLER.indexOf(renkler[0]) >= 0) { return simGri(piksel, w, h, k0, rgb[0][0]); }
    return simBuyut(piksel, w, h, k0, simEtiketle(k0, rgb, renkler), rgb, simCizgi(piksel, w, h, rgb));
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
    var t = VERI.turBul(kod);
    // Model başına ölçülü tür: modellerin ızgaralarının BİRLEŞİMİ (sıralı, tekrarsız); istemci modelinkine süzer.
    if (t && t.olcu_modelleri) {
      var b = [];
      for (var m in t.olcu_modelleri) {
        if (!Object.prototype.hasOwnProperty.call(t.olcu_modelleri, m)) { continue; }
        VERI.modelOlcuSecenekleri(kod, m).forEach(function (x) { if (b.indexOf(x) < 0) { b.push(x); } });
      }
      return b.sort(function (x, y) { return x - y; });
    }
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
