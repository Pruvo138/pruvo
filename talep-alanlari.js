/* PRUVO — Eksik Parça Talebi sözleşmesi.
   Tarayıcı ve shop Worker aynı tabloyu kullanır; ikinci tavan/allow-list tanımı yoktur. */
(function (root) {
  "use strict";

  root.PRUVO_TALEP_GOVDE_TAVANI = 4096;
  root.PRUVO_TALEP_ALANLARI = {
    kategori: { tavan: 40, zorunlu: true },
    marka: { tavan: 60, zorunlu: true },
    model: { tavan: 60, zorunlu: true },
    yil: { tavan: 20, zorunlu: false },
    parca_adi: { tavan: 120, zorunlu: true },
    notu: { tavan: 500, zorunlu: false },
    website: { honeypot: true }
  };
})(typeof window !== "undefined" ? window : globalThis);
