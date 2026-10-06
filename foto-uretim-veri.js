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
    onay_onayli: true, // Okan onayladı 6 Eki 2026 (metin taslak-1 ile birebir; değişirse sürüm de değişir)
    onay_surum: "2026-10-05-taslak-1",
    onay: {
      hak: "Yüklediğim fotoğrafın bana ait olduğunu ya da kullanma hakkım olduğunu beyan ederim.",
      aktarim: "Fotoğrafımın önizleme ve üretim dosyasının hazırlanması için yurt dışındaki " +
        "hizmet sağlayıcıya aktarılmasına açık rıza veriyorum.",
      aydinlatma: [
        "Fotoğrafını yüklediğinde fotoğraf, önizleme görselinin ve üretim dosyasının hazırlanması " +
          "için yurt dışında bulunan bir hizmet sağlayıcıya aktarılır. Bu aktarım için açık rızan " +
          "gerekir; rıza vermezsen bu hizmeti kullanamazsın, sitenin geri kalanı etkilenmez.",
        "Fotoğrafın PRUVO'da saklanmaz. Hizmet sağlayıcı yüklenen fotoğrafı ve ondan üretilen " +
          "dosyaları en geç 3 gün içinde siler.",
        "Önizleme görseli sipariş vermezsen en geç 3 gün içinde silinir; sipariş verirsen üretim " +
          "ve teslim tamamlanana kadar saklanır.",
        "Başkasına ait fotoğraf, marka, logo ya da telifli görsel yükleme; yüklenen görselden " +
          "doğan sorumluluk yükleyene aittir.",
        "Önizleme, fotoğrafının stilize bir yorumudur. Ürün bu önizlemenin en çok 4 renkli " +
          "kabartma yorumu olarak üretilir; birebir aynısı değildir, küçük yazı ve ince " +
          "ayrıntılar sadeleşir.",
        "Kişisel verilerinle ilgili haklar ve başvuru yolu için Gizlilik Politikası sayfasına bakabilirsin."
      ]
    },

    // TÜRLER — açılışta TEK tür: kabartma PLAKET (Okan, 5 Eki 21:4x: "plaket yapalım";
    // yalnız plastik üretiyoruz — metal halka/mıknatıs gerektiren tür SUNULMAZ). Ölçü = uzun
    // kenar (mm). Ayak ayrı parça, plaketle birlikte basılıp gönderilir. Figür ikinci dilimdir.
    // Tek tür varken bölümde tür seçimi adımı GÖRÜNMEZ (fotoğraf → ölçü → önizleme → ödeme).
    // Ölçü SEÇENEKLERİ ve fiyatı burada DEĞİL: sipariş panelindeki fiyat tablosundan gelir
    // (tür × ölçü). Tabloda satırı olmayan ölçü sunulmaz.
    //
    // KATEGORİ KAYDI (6 Eki 2026) — her türün akışı bu alanlardan okunur, kodda ikinci liste YOK:
    //   girdi          : "foto-1" = müşteriden tek fotoğraf
    //   kol            : "saglayici" = önizleme+üretim dış hizmetle (kredi harcar);
    //                    "deterministik" = önizleme tarayıcıda çizilir, üretim dosyasını bizim
    //                    üretecimiz çıkarır (sağlayıcı çağrısı 0, kredi 0)
    //   olcu_mm        : {en_az, en_cok} — fiyat satırı bu aralık dışında YAZILAMAZ
    //   renk_bolgeleri : müşterinin renk seçtiği bölgeler; [] = seçim yok (plaket: önizlemenin 4 renkli yorumu)
    //   malzemeler     : bölge -> izinli filament listesi; {} = satır "PLA" (plaket)
    //   ornek_kanit_izni: türü AÇAN örnek kanıtları; listede olmayan kanıt o türde SAYILMAZ
    //                    (alan yoksa/boşsa hiçbir örnek sayılmaz — fail-closed)
    // Litofan, gerçek örneği ve fiyat satırı olmadıkça AÇILMAZ (fail-closed, plaketle aynı kural).
    turler: [
      {
        kod: "plaket",
        ad: "Kabartma plaket",
        aciklama: "Fotoğrafındaki konunun kabartmalı plaketi; ayağıyla masada durur.",
        girdi: "foto-1",
        kol: "saglayici",
        olcu_mm: { en_az: 50, en_cok: 300 },
        renk_bolgeleri: [],
        malzemeler: {},
        // Okan kararı 7 Eki 2026: plaket gerçek baskı beklemeden önizleme + render ile açılır.
        ornek_kanit_izni: ["baski", "render"]
      },
      {
        kod: "litofan",
        ad: "Işıklı fotoğraf paneli (litofan)",
        aciklama: "Fotoğrafın ince bir panele kalınlık farkıyla işlenir; arkadan ışık gelince görünür. Ayağıyla masada durur.",
        girdi: "foto-1",
        kol: "deterministik",
        olcu_mm: { en_az: 80, en_cok: 200 },
        renk_bolgeleri: [
          { kod: "panel", ad: "Işık geçen panel", renkler: ["Beyaz"] },
          { kod: "ayak", ad: "Ayak", renkler: ["Beyaz", "Siyah", "Gri"] }
        ],
        // ABS YOK: litofan Dekorasyon sınıfıdır (secenekler.js FILAMENT_KATEGORI_HARIC).
        malzemeler: { panel: ["PLA", "PETG"], ayak: ["PLA", "PETG", "ASA"] },
        // Litofan kuralı DEĞİŞMEDİ: yalnız basılmış ürünün gerçek fotoğrafı açar.
        ornek_kanit_izni: ["baski"]
      }
    ],

    // ÖRNEKLER — boşsa bölüm görünmez. Kaynak: TeKiN'in işleri (kanıtı kayıtta yazılı).
    ornekler: [
      {
        tur: "plaket",
        kanit: "render",
        olcu_mm: 120,
        onizleme: "https://media.pruvo3d.com/foto/ornek/plaket-1-onizleme.webp",
        render: "https://media.pruvo3d.com/foto/ornek/plaket-1-render.webp",
        not: "120 mm, 4 renk, ayağıyla"
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

  // Türün akış kolu ("saglayici" | "deterministik"); bilinmeyen tür -> "" (hiçbir kola girmez).
  VERI.kolu = function (kod) {
    var t = VERI.turBul(kod);
    return t && (t.kol === "saglayici" || t.kol === "deterministik") ? t.kol : "";
  };
  // Türün ölçü aralığı (mm, uzun kenar); bilinmeyen tür -> null. Bölüm ve sunucu AYNI fonksiyon.
  VERI.olcuAraligi = function (kod) {
    var t = VERI.turBul(kod);
    if (!t || !t.olcu_mm || !(t.olcu_mm.en_az > 0) || !(t.olcu_mm.en_cok >= t.olcu_mm.en_az)) { return null; }
    return { en_az: t.olcu_mm.en_az, en_cok: t.olcu_mm.en_cok };
  };

  kok.PRUVO_FOTO = VERI;
})(typeof globalThis !== "undefined" ? globalThis : this);
