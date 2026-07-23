/* PRUVO — Konfigüre edilebilir DEKOR ürünü modülü (renk seçimi + boy kaydırıcı).
   tools/build.py, urunler.json'da "konfigur" alanı taşıyan ürünün sayfasına bu dosyayı
   basar; sayfadaki inline URUN_KONFIGUR objesi + /secenekler.js (PRUVO_SECENEK) ile
   çalışır. "konfigur" alanı OLMAYAN ürün sayfasına bu dosya HİÇ girmez (geri uyumluluk
   kabulü: tools/konfigur-test.py, konfigur'suz sayfanın bayt-eşit kaldığını doğrular).

   FİYAT ÇARKI YENİ DEĞİL: secenekler.js parametrikFiyatKurus AYNEN kullanılır —
   fiyat = tabanFiyat × max(1, hacim/tabanHacim) (PLA katsayı 1.00; Siyah/Beyaz/Gri
   standart renk, ek yüzde yok). Hacim, referans modelden küple ölçeklenir:
   hacim(boy) = refHacimCm3 × 1000 × (boy/refYükseklik)³ (mm³). Taban hacim = EN KÜÇÜK
   boyun hacmi -> en küçük boyda fiyat tam taban fiyattır (zemin) ve boy büyüdükçe
   SÜREKLİ artar (sarı seri kuralıyla aynı ilke; basamak yok).

   SEPET/SİPARİŞ TAŞIMA: seçimler mevcut parametrik satır kanalıyla taşınır
   (satir.parametreler/parametre_detay/hacim_mm3/parametrik_fiyat_kurus) + satir.konfigur
   bayrağı. Bayrak, secenekler.js parametrikSatirOzeti'nde kart-ödeme kanalını FAIL-CLOSED
   kapatır (Worker bu fiyatı sunucuda yeniden hesaplayamıyor; kanal WhatsApp).
   Saf JS, bağımlılıksız; çekirdek fonksiyonlar node testlerinden çağrılabilir. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) { module.exports = factory(root); }
  else { root.PRUVO_KONFIGUR = factory(root); }
})(typeof self !== "undefined" ? self : this, function (root) {
  "use strict";

  // ---- saf çekirdek (tools/konfigur-test.py node ile bunları koşar) ----

  // Referans modelden küple ölçeklenmiş malzeme hacmi (mm³). İşlem sırası
  // tools/build.py konfigur_hacim_mm3 ile BİREBİR aynı (çift hassasiyet eşleniği:
  // JS öncesi basılan başlangıç fiyatı ile canlı hesap ayrışmasın).
  function hacimMm3(konfigur, boyMm) {
    var h = konfigur.hacim;
    var oran = boyMm / h.refYukseklikMm;
    return h.refHacimCm3 * 1000 * oran * oran * oran;
  }

  // Taban hacim = en küçük boyun hacmi -> min boyda çarpan 1 (fiyat = taban, ZEMİN).
  function tabanHacimMm3(konfigur) {
    return hacimMm3(konfigur, konfigur.boyutMm.min);
  }

  // Birim fiyat (kuruş). Çark TEK KAYNAK: secenekler.js parametrikFiyatKurus.
  // Malzeme PLA sabittir (katsayı 1.00); renk Siyah/Beyaz/Gri -> ek yüzde yok.
  function fiyatKurus(konfigur, boyMm, renk, secenekModulu) {
    var SECENEK = secenekModulu || root.PRUVO_SECENEK;
    if (!SECENEK || konfigur.tabanFiyatTL == null) { return null; }
    return SECENEK.parametrikFiyatKurus(
      konfigur.tabanFiyatTL, tabanHacimMm3(konfigur), hacimMm3(konfigur, boyMm),
      "PLA", renk || "");
  }

  // Serbest girilen boyu aralığa kırpar + adıma oturtur (mm). Geçersiz girişte
  // varsayılana döner -> sayfada her an geçerli bir boy vardır (hata durumu yok).
  function boyDuzelt(konfigur, boyMm) {
    var b = konfigur.boyutMm;
    var v = (typeof boyMm === "number") ? boyMm
      : parseFloat(String(boyMm).replace(",", "."));
    if (isNaN(v)) { return b.varsayilan; }
    if (v < b.min) { v = b.min; }
    if (v > b.max) { v = b.max; }
    v = b.min + Math.round((v - b.min) / b.adim) * b.adim;
    return v > b.max ? b.max : v;
  }

  function cmMetni(boyMm) {
    return String(boyMm / 10).replace(".", ",");
  }

  // ---- sayfa entegrasyonu ----
  var durum = { konfigur: null, cb: null, seciliRenk: "", boyMm: 0,
                sayiEl: null, kaydiriciEl: null, renkKok: null };

  // Fiyat göstergesi: kart-seçim sayfasıyla aynı dil — adet DAHİL toplam, kuruşuyla.
  function fiyatYaz() {
    var el = document.getElementById("opsiyonFiyat");
    if (!el || !durum.konfigur) { return; }
    var SECENEK = root.PRUVO_SECENEK;
    var kurus = fiyatKurus(durum.konfigur, durum.boyMm, durum.seciliRenk);
    if (kurus == null || !SECENEK) { el.textContent = "Fiyat için sipariş verin"; return; }
    var adetEl = document.getElementById("adetSec");
    var adet = adetEl ? SECENEK.adetDuzelt(adetEl.value) : 1;
    el.textContent = SECENEK.kurusMetni(kurus * adet);
  }

  // Renk seçimi görseli de değiştirir: ana görsel + küçük resim (thumb) aktifliği.
  function gorselSec(url) {
    if (!url) { return; }
    var ana = document.getElementById("mainImg");
    if (ana) { ana.src = url; }
    var t = document.querySelectorAll(".thumb");
    for (var i = 0; i < t.length; i++) {
      t[i].className = (t[i].getAttribute("src") === url) ? "thumb active" : "thumb";
    }
  }

  var KONFIGUR = {
    // saf çekirdek
    hacimMm3: hacimMm3,
    tabanHacimMm3: tabanHacimMm3,
    fiyatKurus: fiyatKurus,
    boyDuzelt: boyDuzelt,

    // sayfa API'si — build.py şablonundaki kancalar çağırır
    kur: function (konfigur, urun, degisimCb) {
      durum.konfigur = konfigur; durum.cb = degisimCb || null;
      durum.boyMm = konfigur.boyutMm.varsayilan;
      durum.sayiEl = document.getElementById("konfigurBoy");
      durum.kaydiriciEl = document.getElementById("konfigurKaydirici");
      durum.renkKok = document.getElementById("renkButonlar");
      var degisim = function () { fiyatYaz(); if (durum.cb) { durum.cb(); } };

      // Renk butonları: seçim + görsel değişimi (data-gorsel build.py'den gelir).
      if (durum.renkKok) {
        var btnlar = durum.renkKok.querySelectorAll(".renk-btn");
        var sec = function () {
          durum.seciliRenk = this.getAttribute("data-renk") || "";
          for (var n = 0; n < btnlar.length; n++) {
            btnlar[n].classList.toggle("secili", btnlar[n] === this);
          }
          gorselSec(this.getAttribute("data-gorsel"));
          degisim();
        };
        for (var i = 0; i < btnlar.length; i++) {
          btnlar[i].addEventListener("click", sec);
        }
      }

      // Boy: sayı kutusu (cm) + kaydırıcı (cm) birbirine bağlı; iç durum mm.
      var oku = function (ham) {
        var cm = parseFloat(String(ham).replace(",", "."));
        if (!isNaN(cm)) { durum.boyMm = boyDuzelt(konfigur, cm * 10); }
      };
      if (durum.kaydiriciEl) {
        durum.kaydiriciEl.addEventListener("input", function () {
          oku(durum.kaydiriciEl.value);
          if (durum.sayiEl) { durum.sayiEl.value = durum.kaydiriciEl.value; }
          degisim();
        });
      }
      if (durum.sayiEl) {
        durum.sayiEl.addEventListener("input", function () {
          oku(durum.sayiEl.value);
          if (durum.kaydiriciEl && durum.sayiEl.value !== "" &&
              !isNaN(parseFloat(durum.sayiEl.value))) {
            durum.kaydiriciEl.value = String(durum.boyMm / 10);
          }
          degisim();
        });
        // Elle girilen aralık dışı/adım dışı değer, alan bırakılınca kurala çekilir.
        durum.sayiEl.addEventListener("change", function () {
          durum.sayiEl.value = String(durum.boyMm / 10);
          if (durum.kaydiriciEl) { durum.kaydiriciEl.value = String(durum.boyMm / 10); }
          degisim();
        });
      }
      fiyatYaz();
    },
    hazir: function () { return !!durum.konfigur; },
    // Sepete ekleme şartı: renk seçilmiş olmalı (boy her an geçerli — boyDuzelt kırpar).
    gecerliMi: function () { return !!(durum.konfigur && durum.seciliRenk); },
    tazele: function () { fiyatYaz(); },
    // Renk seçilmeden "Sepete Ekle": renk butonları titrer + kırmızı vurgu (kart-seçim deseni).
    eksikVurgula: function () {
      var kok = durum.renkKok;
      if (!kok) { return; }
      kok.classList.remove("titre", "hata-vurgu");
      void kok.offsetWidth;
      kok.classList.add("titre", "hata-vurgu");
      setTimeout(function () { kok.classList.remove("titre", "hata-vurgu"); }, 500);
      try { kok.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) { }
      var ilk = kok.querySelector(".renk-btn");
      if (ilk) { ilk.focus(); }
    },
    // Sepet satırına seçimleri yazar (satır: PRUVO_SECENEK.bosSatir çıktısı).
    // Mevcut parametrik satır kanalı kullanılır -> satirAnahtari boyları ayrı satır sayar,
    // parametrikSatirOzeti detay + fiyatı üretir, WhatsApp mesajına aynen girer.
    // satir.konfigur bayrağı kart-ödeme kanalını FAIL-CLOSED kapatır (kanal WhatsApp).
    satiraYaz: function (satir) {
      if (!durum.konfigur) { return satir; }
      var k = durum.konfigur;
      satir.renk = durum.seciliRenk || "";
      satir.konfigur = true;
      satir.parametreler = { boy_mm: durum.boyMm };
      satir.parametre_detay = (k.boyutMm.etiket || "Boy") + ": " + cmMetni(durum.boyMm) + " cm";
      satir.hacim_mm3 = hacimMm3(k, durum.boyMm);
      satir.parametrik_fiyat_kurus = fiyatKurus(k, durum.boyMm, satir.renk);
      return satir;
    }
  };

  return KONFIGUR;
});
