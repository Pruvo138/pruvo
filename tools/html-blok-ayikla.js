"use strict";
/**
 * PRUVO — HTML metninden inline <script> gövdesi ayıklama (ORTAK yardımcı).
 *
 * NEDEN VAR: shop/test/sepet-panel.js ve jenerator/test/vitrin-kabul.js aynı işi
 * (index.html'in inline sepet/vitrin scriptini node:vm'de GERÇEKTEN çalıştırmak için
 * gövdesini çıkarma) yapıyordu. İki ayrı kırılgan çapa denemesi — "son <script>" ve
 * "cartLines'tan geriye en yakın <script>" — aynı sınıf hatayla (bir YORUM içinde geçen
 * "<script>" metni çapayı kaydırır) kırıldı. Desen üçüncü kez tekrarlamasın diye tek
 * robust ayıklama burada tutulur (4fdfa9b7'de vitrin-kabul.js'te giderilen kırılmanın
 * kalıcı, paylaşılan hâli).
 *
 * ROBUSTLUK: <script ...>...</script> çiftleri TAM tag olarak (tembel gövde) eşleşir.
 * Bir yorum içinde geçen "<script>" METNİ yeni bir eşleşme AÇISI başlatmaz: o metin,
 * kendisini içeren gerçek bloğun gövdesi olarak yutulur (blok ilk gerçek </script>'te
 * kapanır, matchAll bir sonraki aramaya oradan devam eder). Konum/sıra değil, İÇERİK
 * İMZASI ile seçilir → body sonuna başka inline script (çerez banner'ı vb.) eklenmesi
 * ya da bir yorumda "<script>" geçmesi kabulü BOZMAZ.
 */

const INLINE_SCRIPT_RE = /<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g;

/** Verilen HTML'deki TÜM inline <script> bloklarının gövdelerini (dosyadaki sırayla) döndürür. */
function inlineScriptGovdeleri(html) {
  return [...String(html).matchAll(INLINE_SCRIPT_RE)].map((m) => m[1]);
}

/**
 * İÇİNDE `imza` dizgesi geçen İLK inline <script> gövdesini döndürür; yoksa null.
 * @param {string} html  index.html metni
 * @param {string} imza  bloğu benzersiz ayırt eden dizge (ör. "cartLines", "renderGrid")
 * @returns {string|null}
 */
function inlineScriptBul(html, imza) {
  if (!imza) { throw new Error("inlineScriptBul: imza zorunlu (blogu ayirt eden dizge)"); }
  const govde = inlineScriptGovdeleri(html).find((s) => s.includes(imza));
  return govde == null ? null : govde;
}

module.exports = { inlineScriptBul, inlineScriptGovdeleri, INLINE_SCRIPT_RE };
