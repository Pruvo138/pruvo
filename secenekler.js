/* PRUVO — Malzeme/Renk/Boy seçenekleri + fiyat hesaplama + sepet veri modeli.
   index.html VE tools/build.py'nin ürettiği urun/<id>/index.html sayfaları bu dosyayı
   ORTAK kullanır (tek kaynak — ikisine ayrı ayrı kopyalanmaz, drift riski kalmaz).
   Kategori listesi değişirse tools/build.py'deki FONKSIYONEL_KATEGORILER ile BİRLİKTE
   güncelle (build.py hangi ürün sayfasına seçici HTML'i basacağını bu listeyle karar verir). */
(function (root) {
  "use strict";

  // PLA taban (fark yok); yüzdeler PLA fiyatına göre ek maliyet.
  var FILAMENT_FARK = { "PLA": 0, "PETG": 30, "ASA": 60, "Karbon Katkılı": 100, "ABS": 50, "TPU": 55 };
  var FILAMENT_SIRA = ["PLA", "PETG", "ASA", "Karbon Katkılı", "ABS", "TPU"];
  var RENK_SECENEKLERI = ["Siyah", "Beyaz", "Gri", "Diğer"];
  var RENK_DIGER_YUZDE = 15;
  var FONKSIYONEL_KATEGORILER = ["Otomobil", "Motosiklet", "Tamirat", "Elektronik", "Ev", "Marin", "Bisiklet", "Bahçe", "Ofis", "Kamera"];

  function fiyatSayisi(fiyat) {
    if (!fiyat) { return null; }
    var d = String(fiyat).replace(/[^0-9]/g, "");
    return d ? parseInt(d, 10) : null;
  }

  function fonksiyonelMi(kategori) {
    return FONKSIYONEL_KATEGORILER.indexOf(kategori) !== -1;
  }

  function boyFarki(urun, boyEtiket) {
    var secenekler = (urun && urun.boy_secenekleri) || [];
    if (!boyEtiket) { return 0; }
    for (var i = 0; i < secenekler.length; i++) {
      if (secenekler[i].etiket === boyEtiket) { return secenekler[i].fark_tl || 0; }
    }
    return 0;
  }

  function hesaplaFiyat(temelFiyatTL, malzeme, renk, boyFarkTL) {
    if (temelFiyatTL == null) { return null; }
    var yuzde = FILAMENT_FARK.hasOwnProperty(malzeme) ? FILAMENT_FARK[malzeme] : 0;
    var ara = temelFiyatTL * (1 + yuzde / 100);
    if (renk === "Diğer") { ara = ara * (1 + RENK_DIGER_YUZDE / 100); }
    return Math.round(ara) + (boyFarkTL || 0);
  }

  // ---- sepet satırı ----
  function bosSatir(id) {
    return { id: id, malzeme: "PLA", renk: "Siyah", renk_ozel: "", boy_etiket: null };
  }

  function satirAnahtari(satir) {
    return [satir.id, satir.malzeme, satir.renk, satir.renk_ozel || "", satir.boy_etiket || ""].join("|");
  }

  // Sepet/WhatsApp mesajında ürün+seçim satırının metnini ve hesaplanan fiyatını üretir.
  // fonksiyonel OLMAYAN kategorilerde (Dekorasyon, Oyun/Hobi...) seçici hiç gösterilmediği
  // için detay boş döner — mevcut (öncesi) davranış korunur, mesaj kirlenmez.
  function satirOzeti(urun, satir) {
    var fonksiyonel = fonksiyonelMi(urun && urun.kategori);
    var parcalar = [];
    if (fonksiyonel) {
      var mYuzde = FILAMENT_FARK.hasOwnProperty(satir.malzeme) ? FILAMENT_FARK[satir.malzeme] : 0;
      parcalar.push("Malzeme: " + satir.malzeme + (mYuzde ? " (+%" + mYuzde + ")" : ""));
      if (satir.renk === "Diğer") {
        parcalar.push("Renk: " + (satir.renk_ozel || "özel renk") + " (özel, +%" + RENK_DIGER_YUZDE + ")");
      } else {
        parcalar.push("Renk: " + satir.renk);
      }
      if (satir.boy_etiket) { parcalar.push("Boy: " + satir.boy_etiket); }
    }
    var temel = fiyatSayisi(urun && urun.fiyat);
    var bf = fonksiyonel ? boyFarki(urun, satir.boy_etiket) : 0;
    var hesap = fonksiyonel ? hesaplaFiyat(temel, satir.malzeme, satir.renk, bf) : temel;
    var fiyatMetni;
    if (hesap != null) { fiyatMetni = hesap + " TL"; }
    else if (urun && urun.parametrik) { fiyatMetni = "Ölçüye özel fiyat — teklif için sipariş verin"; }
    else { fiyatMetni = "Fiyat için sipariş verin"; }
    return { detay: parcalar.join(" · "), fiyat: hesap, fiyatMetni: fiyatMetni };
  }

  // ---- sepet (localStorage) ----
  var CART_KEY = "pruvo_sepet";

  // Eski format (düz id dizisi) otomatik migrate edilir: varsayılan PLA/Siyah satırına çevrilir.
  function sepetYukle() {
    var ham;
    try { ham = JSON.parse(localStorage.getItem(CART_KEY) || "[]"); }
    catch (e) { ham = []; }
    if (!Array.isArray(ham)) { return []; }
    return ham.map(function (x) {
      if (typeof x === "string") { return bosSatir(x); }
      if (x && typeof x === "object" && x.id) {
        return {
          id: x.id, malzeme: x.malzeme || "PLA", renk: x.renk || "Siyah",
          renk_ozel: x.renk_ozel || "", boy_etiket: x.boy_etiket || null
        };
      }
      return null;
    }).filter(Boolean);
  }

  function sepetKaydet(sepet) {
    try { localStorage.setItem(CART_KEY, JSON.stringify(sepet)); } catch (e) { }
  }

  root.PRUVO_SECENEK = {
    FILAMENT_FARK: FILAMENT_FARK,
    FILAMENT_SIRA: FILAMENT_SIRA,
    RENK_SECENEKLERI: RENK_SECENEKLERI,
    RENK_DIGER_YUZDE: RENK_DIGER_YUZDE,
    FONKSIYONEL_KATEGORILER: FONKSIYONEL_KATEGORILER,
    fiyatSayisi: fiyatSayisi,
    fonksiyonelMi: fonksiyonelMi,
    boyFarki: boyFarki,
    hesaplaFiyat: hesaplaFiyat,
    bosSatir: bosSatir,
    satirAnahtari: satirAnahtari,
    satirOzeti: satirOzeti,
    CART_KEY: CART_KEY,
    sepetYukle: sepetYukle,
    sepetKaydet: sepetKaydet
  };
})(window);
