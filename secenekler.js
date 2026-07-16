/* PRUVO — Malzeme/Renk/Boy seçenekleri + fiyat hesaplama + sepet veri modeli.
   index.html VE tools/build.py'nin ürettiği urun/<id>/index.html sayfaları bu dosyayı
   ORTAK kullanır (tek kaynak — ikisine ayrı ayrı kopyalanmaz, drift riski kalmaz).
   Kategori listesi değişirse tools/build.py'deki FONKSIYONEL_KATEGORILER ile BİRLİKTE
   güncelle (build.py hangi ürün sayfasına seçici HTML'i basacağını bu listeyle karar verir). */
(function (root) {
  "use strict";

  // PLA taban (fark yok); yüzdeler PLA fiyatına göre ek maliyet.
  // ABS ve Karbon katkılı KALDIRILDI (Okan, 16 Tem) — mühendislik malzemeleri WhatsApp'tan.
  var FILAMENT_FARK = { "PLA": 0, "PETG": 30, "ASA": 60, "TPU": 55 };
  var FILAMENT_SIRA = ["PLA", "PETG", "ASA", "TPU"];
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

  // ---- parametrik ("ölçüye özel") fiyat ----
  // Okan kuralı: fiyat = tabanFiyat × (hacim/tabanHacim) × filamentKatsayı × renkFaktör.
  // Kuruş cinsinden tutulur; yuvarlama YALNIZ kuruş basamağında (float artığı temizliği),
  // TL'ye yuvarlama yok — kusurat kuruşuyla gösterilir/tahsil edilir.
  function parametrikFiyatKurus(tabanFiyatTL, tabanHacimMm3, hacimMm3, malzeme, renk) {
    if (tabanFiyatTL == null || !tabanHacimMm3 || !hacimMm3) { return null; }
    var yuzde = FILAMENT_FARK.hasOwnProperty(malzeme) ? FILAMENT_FARK[malzeme] : 0;
    var kurus = tabanFiyatTL * 100 * (hacimMm3 / tabanHacimMm3) * (1 + yuzde / 100);
    if (renk === "Diğer") { kurus = kurus * (1 + RENK_DIGER_YUZDE / 100); }
    return Math.round(kurus);
  }

  function kurusMetni(kurus) {
    if (kurus == null) { return null; }
    var tl = Math.floor(kurus / 100), k = kurus % 100;
    return k ? (tl + "," + (k < 10 ? "0" : "") + k + " TL") : (tl + " TL");
  }

  function tlMetni(tutarTL) {
    if (tutarTL == null) { return null; }
    return kurusMetni(Math.round(tutarTL * 100));
  }

  // ---- sepet satırı ----
  function bosSatir(id) {
    return { id: id, malzeme: "PLA", renk: "Siyah", renk_ozel: "", boy_etiket: null };
  }

  function satirAnahtari(satir) {
    return [satir.id, satir.malzeme, satir.renk, satir.renk_ozel || "", satir.boy_etiket || "",
            satir.parametreler ? JSON.stringify(satir.parametreler) : ""].join("|");
  }

  // Sepet/WhatsApp mesajında ürün+seçim satırının metnini ve hesaplanan fiyatını üretir.
  // fonksiyonel OLMAYAN kategorilerde (Dekorasyon, Oyun/Hobi...) seçici hiç gösterilmediği
  // için detay boş döner — mevcut (öncesi) davranış korunur, mesaj kirlenmez.
  function satirOzeti(urun, satir) {
    if (satir && satir.parametreler) { return parametrikSatirOzeti(satir); }
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

  // Parametrik (sarı seri) satır: konfigüratörün yazdığı parametre detayı + kuruşlu fiyat.
  // Fiyat satıra eklenirken hesaplanıp satırda taşınır (taban fiyat yoksa null kalır);
  // sipariş tarafı istemci fiyatına güvenmez, kendi yeniden hesabını yapar.
  function parametrikSatirOzeti(satir) {
    var parcalar = [];
    if (satir.parametre_detay) { parcalar.push(satir.parametre_detay); }
    var mYuzde = FILAMENT_FARK.hasOwnProperty(satir.malzeme) ? FILAMENT_FARK[satir.malzeme] : 0;
    parcalar.push("Malzeme: " + satir.malzeme + (mYuzde ? " (+%" + mYuzde + ")" : ""));
    if (satir.renk === "Diğer") {
      parcalar.push("Renk: " + (satir.renk_ozel || "özel renk") + " (özel, +%" + RENK_DIGER_YUZDE + ")");
    } else {
      parcalar.push("Renk: " + satir.renk);
    }
    var kurus = (satir.parametrik_fiyat_kurus == null) ? null : satir.parametrik_fiyat_kurus;
    return {
      detay: parcalar.join(" · "),
      fiyat: (kurus == null) ? null : kurus / 100,
      fiyatMetni: (kurus == null) ? "Ölçüye özel fiyat — teklif için sipariş verin" : kurusMetni(kurus)
    };
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
        var s = {
          id: x.id, malzeme: x.malzeme || "PLA", renk: x.renk || "Siyah",
          renk_ozel: x.renk_ozel || "", boy_etiket: x.boy_etiket || null
        };
        if (x.parametreler && typeof x.parametreler === "object") {
          s.parametreler = x.parametreler;
          s.parametre_detay = x.parametre_detay || "";
          s.hacim_mm3 = x.hacim_mm3 || null;
          s.parametrik_fiyat_kurus = (x.parametrik_fiyat_kurus == null) ? null : x.parametrik_fiyat_kurus;
        }
        return s;
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
    parametrikFiyatKurus: parametrikFiyatKurus,
    kurusMetni: kurusMetni,
    tlMetni: tlMetni,
    bosSatir: bosSatir,
    satirAnahtari: satirAnahtari,
    satirOzeti: satirOzeti,
    CART_KEY: CART_KEY,
    sepetYukle: sepetYukle,
    sepetKaydet: sepetKaydet
  };
})(window);
