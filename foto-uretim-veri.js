/* PRUVO — "fotoğrafından özel üretim" bölümünün TEK KAYNAK verisi.
 *
 * Bu dosyayı İKİ taraf okur, ikinci kopya YOKTUR:
 *   - ana sayfa bölümü (/foto-uretim.js) örnekleri, türleri ve onay metnini buradan çizer;
 *   - sipariş sunucusu (shop worker) aynı dosyayı import eder: bir türün sipariş/önizleme
 *     alabilmesi için burada en az BİR gerçek örneği olmalı ve onay metni onaylı olmalı.
 *
 * DÜRÜST BEKLENTİ KURALI (Okan, 5 Eki 2026: "müşteri abartılı hayallere kapılmasın"):
 *   - `ornekler` yalnız GERÇEK işlerdir: müşteri fotoğrafı → önizleme → BASILMIŞ ürünün
 *     gerçek fotoğrafı. Render ya da üretilmiş "baskı" görseli bu listeye GİRMEZ.
 *   - Gerçek örneği olmayan tür AÇILMAZ (bölümde sipariş formu o tür için çıkmaz, sunucu da
 *     o türe önizleme üretmez). Görseller R2 medya kovasında durur; buraya yalnız adres yazılır.
 *
 * Örnek kaydı: { tur, olcu_mm, foto, onizleme, baski, not }
 *   tur      : turler[].kod
 *   foto     : müşteri fotoğrafı (izinli/kendi fotoğrafımız) — https://media.pruvo3d.com/...
 *   onizleme : o fotoğraftan üretilen önizleme görseli
 *   baski    : aynı işin BASILMIŞ hâlinin gerçek fotoğrafı
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
    onay_onayli: false,
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
    turler: [
      {
        kod: "plaket",
        ad: "Kabartma plaket",
        aciklama: "Fotoğrafındaki konunun kabartmalı plaketi; ayağıyla masada durur."
      }
    ],

    // GERÇEK ÖRNEKLER — boşsa bölüm görünmez. Kaynak: TeKiN'in basılmış işleri.
    ornekler: [],

    // Ziyaretçi başına 24 saatte en çok kaç önizleme (sunucu da AYNI sayıyı uygular).
    sinir_ziyaretci_24s: 3,

    // Önizleme kaç saat içinde siparişe dönüşebilir (sunucu sınırı; bölüm müşteriye söyler).
    gecerlilik_saat: 48
  };

  // Bir türün gerçek örnek sayısı — bölüm ve sunucu AYNI fonksiyonu kullanır.
  VERI.ornekSayisi = function (tur) {
    var n = 0;
    for (var i = 0; i < VERI.ornekler.length; i++) {
      var o = VERI.ornekler[i];
      if (o && o.tur === tur && o.foto && o.onizleme && o.baski) { n++; }
    }
    return n;
  };
  VERI.turBul = function (kod) {
    for (var i = 0; i < VERI.turler.length; i++) {
      if (VERI.turler[i].kod === kod) { return VERI.turler[i]; }
    }
    return null;
  };

  kok.PRUVO_FOTO = VERI;
})(typeof globalThis !== "undefined" ? globalThis : this);
