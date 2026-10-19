/* PRUVO — Konfigüre edilebilir DEKOR ürünü modülü (renk seçimi + boy kaydırıcı).
   Sayfa üreteci, urunler.json'da "konfigur" alanı taşıyan ürünün sayfasına bu dosyayı
   basar; sayfadaki inline URUN_KONFIGUR objesi + /secenekler.js (PRUVO_SECENEK) ile
   çalışır. "konfigur" alanı OLMAYAN ürün sayfasına bu dosya HİÇ girmez (geri uyumluluk
   kabulü: konfigür kabul testi, konfigur'suz sayfanın bayt-eşit kaldığını doğrular).

   FİYAT MODELİ (mimar kararı, işletme onaylı band — TUR-3): iki ÇAPA noktasından çözülen
   AFİN model: fiyat_TL = sabit + birim × hacim_cm3(boy). Çapalar şemada
   `fiyatCapalari: [[boyMm1, TL1], [boyMm2, TL2]]` (pilot: [[60,150],[300,1300]] →
   birim ≈ 1,2306 TL/cm³, sabit ≈ 140,72 TL) — sabit/birim ELLE YAZILMAZ, çapadan
   ÇÖZÜLÜR (ileride tek çapa sayısı değişince eğri kendiliğinden türesin).
   Hacim, referans modelden küple ölçeklenir: hacim(boy) = refHacimCm3 × 1000 ×
   (boy/refYükseklik)³ (mm³) — doğrusallık fiyat↔hacim ilişkisindedir. Fiyat en küçük
   boydan itibaren KESİN ARTAN (düz-bölge artefaktı yok); görünen fiyat TAM TL'ye
   yuvarlanır. Standart renkler (Siyah/Beyaz/Gri) fiyatı değiştirmez.

   DOĞRUSAL MOD (işletme kararı, 18 Eki 2026 — Figür): şemada `fiyatModu: "dogrusal"` varsa AYNI iki
   çapa boyun kendisine doğrusal okunur: fiyat_TL = sabit + birim × boy_mm (Figür:
   [[60,600],[250,2500]] -> 100 TL/cm, sabit 0) ve 3× TAVAN UYGULANMAZ. Alan yoksa ya da
   "hacim" ise davranış bugünküyle BİREBİR (geri uyumluluk). Bilinmeyen mod -> fiyat YOK
   (null) = FAIL-CLOSED (Worker kalemi reddeder; yanlış tahsilat yerine sipariş kaybı).

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

  // ---- saf çekirdek (konfigür kabul testi node ile bunları koşar) ----

  // Referans modelden küple ölçeklenmiş malzeme hacmi (mm³). İşlem sırası
  // sayfa üreteci konfigur_hacim_mm3 ile BİREBİR aynı (çift hassasiyet eşleniği:
  // JS öncesi basılan başlangıç fiyatı ile canlı hesap ayrışmasın).
  // Doğrusal modda hacim OPSİYONEL (Figür/Fidget: ücretli kaynakta dosya yok) -> alan yoksa
  // null (sipariş satırında hacim_mm3 null; uydurma değer YOK). Sayfa üreteci aynı (None).
  function hacimMm3(konfigur, boyMm) {
    var h = konfigur.hacim;
    if (!h || typeof h !== "object") { return null; }
    var oran = boyMm / h.refYukseklikMm;
    return h.refHacimCm3 * 1000 * oran * oran * oran;
  }

  // Fiyat modu: alan yok / "hacim" -> afin-hacim (bugünkü), "dogrusal" -> boya doğrusal;
  // başka her değer null (FAIL-CLOSED). Sayfa üreteci _konfigur_fiyat_modu ile BİREBİR.
  function fiyatModu(konfigur) {
    var m = konfigur.fiyatModu;
    if (m === undefined || m === "hacim") { return "hacim"; }
    return m === "dogrusal" ? "dogrusal" : null;
  }

  // Modun fiyat ekseni: hacim modunda hacim_cm3(boy), doğrusal modda boy_mm'nin kendisi.
  function fiyatEkseni(konfigur, mod, boyMm) {
    if (mod === "dogrusal") { return boyMm; }
    var v = hacimMm3(konfigur, boyMm);
    return v === null ? null : v / 1000;   // hacim modunda hacimsiz şema -> fiyat YOK
  }

  // Afin modeli çapa çiftinden çözer: fiyat_TL = sabit + birim × eksen (eksen = hacim_cm3,
  // doğrusal modda boy_mm). İşlem sırası sayfa üreteci _konfigur_fiyat_modeli ile BİREBİR
  // (drift nöbeti testte).
  function fiyatModeli(konfigur) {
    var c = konfigur.fiyatCapalari;
    var mod = fiyatModu(konfigur);
    if (!c || c.length !== 2 || !mod) { return null; }
    var v1 = fiyatEkseni(konfigur, mod, c[0][0]);
    var v2 = fiyatEkseni(konfigur, mod, c[1][0]);
    if (v1 === null || v2 === null) { return null; }   // FAIL-CLOSED (Worker reddeder)
    // TEK BOY (19 Eki 2026, değişiklik izni olmayan tasarım): iki çapa AYNI boyda -> eğri
    // yok, fiyat çapanın kendisi (boyDuzelt zaten min=max'a kırpar). Çapa fiyatları farklıysa
    // şema çelişkili -> FAIL-CLOSED (null; (v2-v1)=0 bölümü NaN'a da düşmez). Koşul BOYDA
    // (eksen değerinde DEĞİL): eksen null/0'a kayarsa bu kol üstteki korkulukları MASKELERDİ.
    if (c[0][0] === c[1][0]) {
      if (c[0][1] !== c[1][1]) { return null; }
      return { birim: 0, sabit: c[0][1], mod: mod };
    }
    var birim = (c[1][1] - c[0][1]) / (v2 - v1);
    return { birim: birim, sabit: c[0][1] - birim * v1, mod: mod };
  }

  // Birim fiyat (kuruş): afin model × malzeme katsayısı, görünen fiyat TAM TL'ye yuvarlanır
  // (mimar kararı) — kuruş = round(afin_TL × katsayi) × 100; sepet/WhatsApp aynı değeri taşır
  // (ikinci hesap yok). katsayi verilmezse/geçersizse 1 (PLA / malzemesiz) => malzeme-öncesi
  // kodla BİREBİR aynı (geri uyumluluk). Çapalar tanım gereği tam tutar (katsayi=1'de).
  // 3× tavan YALNIZ hacim modunda (doğrusal modda işletme kararıyla tavan YOK).
  function fiyatKurus(konfigur, boyMm, katsayi) {
    var m = fiyatModeli(konfigur);
    if (!m) { return null; }
    var k = (typeof katsayi === "number" && isFinite(katsayi) && katsayi > 0) ? katsayi : 1;
    var tl = (m.sabit + m.birim * fiyatEkseni(konfigur, m.mod, boyMm)) * k;
    if (m.mod === "hacim") {
      var tavan = 3 * konfigur.fiyatCapalari[0][1];   // 3× TAVAN (işletme kuralı)
      if (tl > tavan) { tl = tavan; }
    }
    return Math.round(tl) * 100;
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
                sayiEl: null, kaydiriciEl: null, renkKok: null,
                malzemeAcik: false, seciliMalzeme: "", seciliKatsayi: 1, malzemeKok: null };

  // Fiyat göstergesi: kart-seçim sayfasıyla aynı dil — adet DAHİL toplam, kuruşuyla.
  function fiyatYaz() {
    var el = document.getElementById("opsiyonFiyat");
    if (!el || !durum.konfigur) { return; }
    var SECENEK = root.PRUVO_SECENEK;
    var kurus = fiyatKurus(durum.konfigur, durum.boyMm, durum.seciliKatsayi);
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
    fiyatModeli: fiyatModeli,
    fiyatKurus: fiyatKurus,
    boyDuzelt: boyDuzelt,

    // sayfa API'si — üreteç şablonundaki kancalar çağırır
    kur: function (konfigur, urun, degisimCb) {
      durum.konfigur = konfigur; durum.cb = degisimCb || null;
      durum.boyMm = konfigur.boyutMm.varsayilan;
      durum.sayiEl = document.getElementById("konfigurBoy");
      durum.kaydiriciEl = document.getElementById("konfigurKaydirici");
      durum.renkKok = document.getElementById("renkButonlar");
      durum.malzemeKok = document.getElementById("malzemeButonlar");
      durum.malzemeAcik = false;
      durum.seciliMalzeme = "";
      durum.seciliKatsayi = 1;
      var degisim = function () { fiyatYaz(); if (durum.cb) { durum.cb(); } };

      // Malzeme butonları (opsiyonel): varsayılan önden 'secili'; her butonun data-katsayi'si
      // fiyatı çarpar. Alan yoksa (buton kökü yok) fiyat PLA sabit (katsayi=1, geri uyumluluk).
      if (durum.malzemeKok) {
        var mbtnlar = durum.malzemeKok.querySelectorAll(".malzeme-btn");
        var mSec = function () {
          durum.seciliMalzeme = this.getAttribute("data-malzeme") || "";
          durum.seciliKatsayi = parseFloat(this.getAttribute("data-katsayi")) || 1;
          for (var q = 0; q < mbtnlar.length; q++) {
            mbtnlar[q].classList.toggle("secili", mbtnlar[q] === this);
          }
          degisim();
        };
        for (var mi = 0; mi < mbtnlar.length; mi++) {
          mbtnlar[mi].addEventListener("click", mSec);
        }
        // Başlangıç seçimi: sunucunun 'secili' işaretlediği (varsayılan) buton; yoksa ilki.
        var ilkM = durum.malzemeKok.querySelector(".malzeme-btn.secili") || mbtnlar[0];
        if (ilkM) {
          durum.malzemeAcik = true;
          durum.seciliMalzeme = ilkM.getAttribute("data-malzeme") || "";
          durum.seciliKatsayi = parseFloat(ilkM.getAttribute("data-katsayi")) || 1;
        }
      }

      // Renk butonları: seçim + görsel değişimi (data-gorsel üreteçten gelir).
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
        // 🔴 BASLANGIC SECIMI (11 Agu) — malzeme ekseniyle AYNI kural: üreteç hangi butona
        // `secili` bastıysa durum odur. Bu satır olmadan buton SEÇİLİ GÖRÜNÜR ama
        // durum.seciliRenk boş kalır; gecerliMi() false döner ve "Sepete Ekle" seçili bir
        // renge rağmen çalışmaz — kullanıcının gördüğüyle çelişen SESSİZ arıza.
        // gorselSec BİLEREK çağrılmaz: üreteç varsayılan olarak ana görselin rengini
        // işaretler (varsayılan renk kuralı üreteç tarafında), görüntü zaten doğrudur.
        var ilkR = durum.renkKok.querySelector(".renk-btn.secili");
        if (ilkR) { durum.seciliRenk = ilkR.getAttribute("data-renk") || ""; }
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
    // Malzeme ekseni açıksa varsayılan önden seçili -> seciliMalzeme daima dolu; yine de
    // savunmacı kontrol edilir (malzeme açıkken boş kalmışsa eklemeyi kilitle).
    gecerliMi: function () {
      return !!(durum.konfigur && durum.seciliRenk &&
                (!durum.malzemeAcik || durum.seciliMalzeme));
    },
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
      // Malzeme ekseni açıksa seçili malzeme siparişe (sepet/WhatsApp "Malzeme: PETG") taşınır;
      // kapalıysa satir.malzeme DEFAULT ("PLA", bosSatir) kalır -> mevcut davranış korunur.
      if (durum.malzemeAcik && durum.seciliMalzeme) { satir.malzeme = durum.seciliMalzeme; }
      satir.konfigur = true;
      satir.parametreler = { boy_mm: durum.boyMm };
      satir.parametre_detay = (k.boyutMm.etiket || "Boy") + ": " + cmMetni(durum.boyMm) + " cm";
      satir.hacim_mm3 = hacimMm3(k, durum.boyMm);
      satir.parametrik_fiyat_kurus = fiyatKurus(k, durum.boyMm, durum.seciliKatsayi);
      return satir;
    }
  };

  return KONFIGUR;
});
