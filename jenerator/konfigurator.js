/* PRUVO — Ölçüye özel (parametrik) ürün konfigüratörü.
   Ürün sayfasında URUN_SEMA (build.py inline eder) + /jenerator/hacim.js (PRUVO_HACIM)
   + /secenekler.js (PRUVO_SECENEK) ile çalışır. Parametre alanlarını kurar, canlı
   hacim + fiyat hesaplar (kuruş korunur, TL'ye yuvarlama yok), sınır dışı girişte
   alanı işaretler ve sepete eklemeyi kilitler. Fiyat, taban fiyat girilene kadar
   "—" gösterilir (tabanFiyatTL=null — altyapı hazır bekler).
   Saf JS, bağımlılıksız; doğrulama/fiyat fonksiyonları test edilebilirlik için saftır. */
(function (root) {
  "use strict";

  // Cerceve 2-renk yazi ek ucreti (kurus) + basilabilirlik esigi + beyaz liste.
  // TEK KAYNAK degerleri: +75 TL = shop/src/parametrik.js ile AYNI; min kenar 9 mm
  // (KAAN-RENDER-DOGRULA: TASLAK, SCAD assert render'iyla kesinlesecek); beyaz liste
  // = onizleme/derleyici/server.py METIN_BEYAZ_LISTE kumesiyle AYNI (harf/rakam + . , - _).
  var IKI_RENK_EK_KURUS = 7500;
  var IKI_RENK_MIN_KENAR = 9;
  var YAZI_BEYAZ_LISTE = /^[A-Za-z0-9ğüşıöçĞÜŞİÖÇ .,\-_]*$/;

  // ---- saf yardımcılar (node testlerinde de kullanılır) ----

  function parametreBul(sema, ad) {
    for (var i = 0; i < sema.parametreler.length; i++) {
      if (sema.parametreler[i].ad === ad) { return sema.parametreler[i]; }
    }
    return null;
  }

  function varsayilanDegerler(sema) {
    var d = {};
    for (var i = 0; i < sema.parametreler.length; i++) {
      d[sema.parametreler[i].ad] = sema.parametreler[i].varsayilan;
    }
    return d;
  }

  // Tek parametre doğrulaması: null dönerse geçerli, string dönerse hata mesajı.
  function parametreHatasi(p, deger) {
    var tip = p.tip || "sayi";
    if (tip === "sayi") {
      var v = typeof deger === "number" ? deger : parseFloat(String(deger).replace(",", "."));
      if (deger === "" || deger == null || isNaN(v)) { return "Sayı girin"; }
      if (v < p.min || v > p.max) { return p.min + "–" + p.max + (p.birim ? " " + p.birim : "") + " aralığında olmalı"; }
      var adim = p.adim || 1;
      var kalan = Math.abs((v - p.min) / adim - Math.round((v - p.min) / adim));
      if (kalan > 1e-6) { return "Adım " + adim + (p.birim ? " " + p.birim : "") + " olmalı"; }
      // İzin listesi (gecerliDegerler): üretim motoru aralığın tamamını değil
      // yalnız belirli değerleri destekliyorsa (vida M ölçüleri) onun dışı reddedilir.
      if (p.gecerliDegerler) {
        for (var gi = 0; gi < p.gecerliDegerler.length; gi++) {
          if (Math.abs(v - p.gecerliDegerler[gi]) < 1e-9) { return null; }
        }
        return "Üretilebilir değerler: " + p.gecerliDegerler.join(", ") +
          (p.birim ? " " + p.birim : "");
      }
      return null;
    }
    if (tip === "secim") {
      for (var i = 0; i < p.secenekler.length; i++) {
        var s = p.secenekler[i];
        if ((typeof s === "object" ? s.deger : s) === deger) { return null; }
      }
      return "Geçersiz seçim";
    }
    if (tip === "metin") {
      if (p.maksUzunluk && String(deger || "").length > p.maksUzunluk) {
        return "En çok " + p.maksUzunluk + " karakter";
      }
      return null;
    }
    return "Bilinmeyen parametre tipi";
  }

  // Tüm set doğrulaması -> {gecerli: bool, hatalar: {ad: mesaj}}
  // sema.kisitlar: koşullu üretilebilirlik kuralları — [{eger: {ad: deger},
  // parametre, min, mesaj}]. "eger"deki tüm eşitlikler tutuyorsa parametrenin
  // alt sınırı yükselir (örn. altıgen başlı cıvata üretim motorunda M5'ten başlar).
  function dogrula(sema, degerler) {
    var hatalar = {}, gecerli = true;
    for (var i = 0; i < sema.parametreler.length; i++) {
      var p = sema.parametreler[i];
      var h = parametreHatasi(p, degerler[p.ad]);
      if (h) { hatalar[p.ad] = h; gecerli = false; }
    }
    for (var k = 0; k < (sema.kisitlar || []).length; k++) {
      var ks = sema.kisitlar[k], uygulanir = true;
      for (var ad in ks.eger) {
        if (!ks.eger.hasOwnProperty(ad)) { continue; }
        if (degerler[ad] !== ks.eger[ad]) { uygulanir = false; break; }
      }
      if (!uygulanir || hatalar[ks.parametre]) { continue; }
      var kv = degerler[ks.parametre];
      kv = typeof kv === "number" ? kv : parseFloat(String(kv).replace(",", "."));
      if (ks.min != null && !isNaN(kv) && kv < ks.min) {
        hatalar[ks.parametre] = ks.mesaj || ("En az " + ks.min + " olmalı");
        gecerli = false;
      }
    }
    return { gecerli: gecerli, hatalar: hatalar };
  }

  // Sayısal değerleri number'a çevirip hacim fonksiyonuna verilecek seti üretir
  // (metin parametreleri hacme girmez).
  function hacimGirdisi(sema, degerler) {
    var g = {};
    for (var i = 0; i < sema.parametreler.length; i++) {
      var p = sema.parametreler[i], tip = p.tip || "sayi";
      if (tip === "metin") { continue; }
      var v = degerler[p.ad];
      g[p.ad] = (tip === "sayi") ? parseFloat(String(v).replace(",", ".")) : v;
    }
    return g;
  }

  function hacimMm3(sema, degerler, hacimModulu) {
    var HACIM = hacimModulu || root.PRUVO_HACIM;
    var fn = HACIM && HACIM[sema.hacimFormulu];
    if (typeof fn !== "function") { return null; }
    var h = fn(hacimGirdisi(sema, degerler));
    return (typeof h === "number" && isFinite(h) && h > 0) ? h : null;
  }

  function fiyatKurus(sema, degerler, malzeme, renk, moduller) {
    var SECENEK = (moduller && moduller.secenek) || root.PRUVO_SECENEK;
    var h = hacimMm3(sema, degerler, moduller && moduller.hacim);
    if (h == null) { return null; }
    return SECENEK.parametrikFiyatKurus(sema.tabanFiyatTL, sema.tabanHacimMm3, h, malzeme, renk);
  }

  // "İç çap: 32 mm · Kesit: 4 mm · Üzerindeki yazı: AHŞAP" — sepet/WhatsApp satır detayı.
  function detayMetni(sema, degerler) {
    var parcalar = [];
    for (var i = 0; i < sema.parametreler.length; i++) {
      var p = sema.parametreler[i], v = degerler[p.ad], tip = p.tip || "sayi";
      if (tip === "metin" && !v) { continue; }
      if (tip === "secim") {
        for (var j = 0; j < p.secenekler.length; j++) {
          var s = p.secenekler[j];
          if (typeof s === "object" && s.deger === v) { v = s.etiket; break; }
        }
      }
      parcalar.push((p.etiket || p.ad) + ": " + v + (tip === "sayi" && p.birim ? " " + p.birim : ""));
    }
    return parcalar.join(" · ");
  }

  function hacimMetni(mm3) {
    if (mm3 == null) { return ""; }
    var cm3 = mm3 / 1000;
    var m = cm3 >= 100 ? Math.round(cm3) : Math.round(cm3 * 10) / 10;
    return "Malzeme hacmi: ~" + String(m).replace(".", ",") + " cm³";
  }

  // ---- sayfa entegrasyonu ----
  var durum = { sema: null, alanlar: {}, degisimCb: null, yaziRenkEl: null };

  // Cerceve = "yazi" (metin) parametresi olan sema. Bu urunde 2. renk (yazi rengi)
  // secici + 2-renk basilabilirlik/beyaz-liste kurallari devreye girer; digerlerinde
  // (yalniz sayi/secim, veya kase gibi "metin" adli param) bu kod SESSIZ kalir.
  function cerceveMi(sema) { return !!parametreBul(sema, "yazi"); }

  // Cerceve renginin (1. renk) sayfadaki secim kaynagi — hesaplama ciz() ile AYNI.
  function frameRengi() {
    var secim = durum.secimKaynagi ? durum.secimKaynagi() : null;
    var renkEl = (typeof document !== "undefined") ? document.getElementById("renkSec") : null;
    return (secim && secim.renk) || (renkEl ? renkEl.value : "Siyah") || "Siyah";
  }

  // Cerceve 2-renk durumu: {ikiRenk, yaziKirli, kenarDar}. frameRenk disaridan verilir
  // (ciz -> sayfa secimi; satiraYaz -> satir.renk). Yalniz cerceve semasinda anlamli.
  function cerceveDurumu(sema, d, frameRenk) {
    if (!cerceveMi(sema)) { return null; }
    var yazi = String(d.yazi || "");
    var yaziRenk = durum.yaziRenkEl ? durum.yaziRenkEl.value : null;
    var ikiRenk = !!yazi && !!yaziRenk && yaziRenk !== frameRenk;
    var kenar = parseFloat(String(d.kenar_genisligi).replace(",", "."));
    return {
      ikiRenk: ikiRenk,
      yaziRenk: yaziRenk,
      yaziKirli: !!yazi && !YAZI_BEYAZ_LISTE.test(yazi),
      kenarDar: ikiRenk && !(kenar >= IKI_RENK_MIN_KENAR)
    };
  }

  // Yazi rengi (2. renk) secicisini kurar — yalniz cerceve sayfasinda cagrilir.
  function yaziRenkKur(kok, degisim) {
    var SEC = root.PRUVO_SECENEK;
    var renkler = (SEC && SEC.RENK_SECENEKLERI) || ["Siyah", "Beyaz", "Gri", "Diğer"];
    var satir = document.createElement("div");
    satir.className = "opsiyon-row konf-row konf-yazi-renk";
    var etiket = document.createElement("label");
    etiket.textContent = "Yazı rengi (2. renk)";
    etiket.htmlFor = "konf_yazi_renk";
    satir.appendChild(etiket);
    var sel = document.createElement("select");
    sel.id = "konf_yazi_renk";
    for (var i = 0; i < renkler.length; i++) {
      var o = document.createElement("option");
      o.value = renkler[i]; o.textContent = renkler[i];
      sel.appendChild(o);
    }
    sel.value = "Siyah";   // varsayilan cerceve rengiyle ayni -> ek ucret yok
    sel.addEventListener("change", degisim);
    satir.appendChild(sel);
    var not = document.createElement("div");
    not.className = "konf-hata konf-yazi-renk-not";
    satir.appendChild(not);
    kok.appendChild(satir);
    durum.yaziRenkEl = sel;
  }

  function alanKur(p, kok, degisim) {
    var satir = document.createElement("div");
    satir.className = "opsiyon-row konf-row";
    var etiket = document.createElement("label");
    etiket.textContent = p.etiket || p.ad;
    etiket.htmlFor = "konf_" + p.ad;
    satir.appendChild(etiket);

    var tip = p.tip || "sayi", girdi, kaydirici = null;
    if (tip === "sayi" && p.gecerliDegerler) {
      // İzin listeli sayı: üretilemez ara değer hiç seçilemesin diye serbest
      // giriş yerine seçim kutusu (doğrulama kuralı yine de asıl kapı —
      // sunucu/sepet yolunda dogrula() aynı listeyi uygular).
      girdi = document.createElement("select");
      for (var gd = 0; gd < p.gecerliDegerler.length; gd++) {
        var og = document.createElement("option");
        og.value = p.gecerliDegerler[gd];
        og.textContent = p.gecerliDegerler[gd] + (p.birim ? " " + p.birim : "");
        girdi.appendChild(og);
      }
      girdi.value = p.varsayilan;
      girdi.addEventListener("change", degisim);
      satir.appendChild(girdi);
    } else if (tip === "sayi") {
      girdi = document.createElement("input");
      girdi.type = "number";
      girdi.min = p.min; girdi.max = p.max; girdi.step = p.adim || 1;
      girdi.value = p.varsayilan;
      girdi.className = "konf-sayi";
      girdi.inputMode = "decimal";
      kaydirici = document.createElement("input");
      kaydirici.type = "range";
      kaydirici.min = p.min; kaydirici.max = p.max; kaydirici.step = p.adim || 1;
      kaydirici.value = p.varsayilan;
      kaydirici.className = "konf-kaydirici";
      kaydirici.setAttribute("aria-hidden", "true");
      kaydirici.tabIndex = -1;
      kaydirici.addEventListener("input", function () { girdi.value = kaydirici.value; degisim(); });
      girdi.addEventListener("input", function () {
        if (girdi.value !== "" && !isNaN(parseFloat(girdi.value))) { kaydirici.value = girdi.value; }
        degisim();
      });
      if (p.birim) {
        var birim = document.createElement("span");
        birim.className = "konf-birim"; birim.textContent = p.birim;
        satir.appendChild(girdi); satir.appendChild(birim);
      } else { satir.appendChild(girdi); }
    } else if (tip === "secim") {
      girdi = document.createElement("select");
      for (var i = 0; i < p.secenekler.length; i++) {
        var s = p.secenekler[i];
        var o = document.createElement("option");
        o.value = (typeof s === "object") ? s.deger : s;
        o.textContent = (typeof s === "object") ? s.etiket : s;
        girdi.appendChild(o);
      }
      girdi.value = p.varsayilan;
      girdi.addEventListener("change", degisim);
      satir.appendChild(girdi);
    } else { // metin
      girdi = document.createElement("input");
      girdi.type = "text";
      girdi.value = p.varsayilan || "";
      if (p.maksUzunluk) { girdi.maxLength = p.maksUzunluk; }
      girdi.addEventListener("input", degisim);
      satir.appendChild(girdi);
    }
    girdi.id = "konf_" + p.ad;

    var hata = document.createElement("div");
    hata.className = "konf-hata";
    satir.appendChild(hata);
    kok.appendChild(satir);
    if (kaydirici) {
      var kaySatir = document.createElement("div");
      kaySatir.className = "konf-kaydirici-satir";
      kaySatir.appendChild(kaydirici);
      kok.appendChild(kaySatir);
    }
    return { girdi: girdi, hataEl: hata, satirEl: satir };
  }

  function degerler() {
    var d = {};
    for (var ad in durum.alanlar) {
      if (!durum.alanlar.hasOwnProperty(ad)) { continue; }
      var p = parametreBul(durum.sema, ad);
      var ham = durum.alanlar[ad].girdi.value;
      d[ad] = ((p.tip || "sayi") === "sayi" && ham !== "" && !isNaN(parseFloat(ham)))
        ? parseFloat(ham) : ham;
    }
    return d;
  }

  function ciz() {
    var sema = durum.sema, d = degerler();
    var sonuc = dogrula(sema, d);
    for (var ad in durum.alanlar) {
      if (!durum.alanlar.hasOwnProperty(ad)) { continue; }
      var alan = durum.alanlar[ad];
      var mesaj = sonuc.hatalar[ad] || "";
      alan.hataEl.textContent = mesaj;
      alan.girdi.classList.toggle("hatali", !!mesaj);
    }
    // Cerceve 2-renk ek dogrulama (yalniz "yazi" parametreli sema): yazi beyaz-listesi
    // + 2-renk dar-kenar. Hatalar ilgili alanin hataEl'ine yazilir; add butonu gecerliMi()
    // ile zaten kilitlenir. Diger urunlerde cer=null -> hicbir etki yok.
    var cer = cerceveDurumu(sema, d, frameRengi());
    var cerHata = false;
    if (cer && cer.yaziKirli && durum.alanlar.yazi) {
      durum.alanlar.yazi.hataEl.textContent = "Yalnızca harf, rakam ve  . , - _  kullanın";
      durum.alanlar.yazi.girdi.classList.add("hatali");
      cerHata = true;
    }
    if (cer && cer.ikiRenk && cer.kenarDar && durum.alanlar.kenar_genisligi) {
      durum.alanlar.kenar_genisligi.hataEl.textContent =
        "2 renk yazı için kenar en az " + IKI_RENK_MIN_KENAR + " mm olmalı";
      durum.alanlar.kenar_genisligi.girdi.classList.add("hatali");
      cerHata = true;
    }
    var hacimEl = document.getElementById("konfHacim");
    var fiyatEl = document.getElementById("opsiyonFiyat");
    var h = sonuc.gecerli ? hacimMm3(sema, d) : null;
    if (hacimEl) { hacimEl.textContent = (h == null) ? "" : hacimMetni(h); }
    if (fiyatEl) {
      // Malzeme/renk secimi: once dis kaynak (F kalemi — kart-secim sayfasi
      // secimKaynagi ile baglar), yoksa eski dropdown'lar (geri donus), o da
      // yoksa taban PLA/Siyah. Secim henuz yapilmamissa taban fiyat uzerinden
      // "...'den baslayan" mantigi satirOzeti tarafinda; burada taban gosterilir.
      var secim = durum.secimKaynagi ? durum.secimKaynagi() : null;
      var malzemeEl = document.getElementById("malzemeSec");
      var renkEl = document.getElementById("renkSec");
      var malzeme = (secim && secim.malzeme) ||
        (malzemeEl ? malzemeEl.value : "PLA") || "PLA";
      var renk = (secim && secim.renk) || (renkEl ? renkEl.value : "Siyah") || "Siyah";
      var kurus = (h == null || cerHata) ? null
        : root.PRUVO_SECENEK.parametrikFiyatKurus(
            sema.tabanFiyatTL, sema.tabanHacimMm3, h, malzeme, renk);
      // 2-renk yazi ek ucreti: front gosterimi Worker (parametrik.js) ile AYNI olmali,
      // yoksa musteri 600 gorup 675 tahsil edilirdi (clamp DISI +75 TL).
      if (kurus != null && cer && cer.ikiRenk) { kurus += IKI_RENK_EK_KURUS; }
      // Sari kural (Okan): taban fiyat girilmemis ailede (vida) "Olcuye ozel fiyat"
      // ("—" degil — musteriye fiyatin sonradan teklif edilecegini soyler). Taban
      // fiyati DOLU ailede kart-secim kalibi (normal sayfayla ayni, F kalemi):
      // malzeme+renk secilene kadar "X TL'den baslayan", ikisi de secilince kesin.
      var secimEksik = !!durum.secimKaynagi &&
        (!(secim && secim.malzeme) || !(secim && secim.renk));
      fiyatEl.textContent = (kurus == null)
        ? "Ölçüye özel fiyat"
        : root.PRUVO_SECENEK.kurusMetni(kurus) + (secimEksik ? "'den başlayan" : "");
    }
    return sonuc.gecerli && !cerHata;
  }

  var KONF = {
    // saf çekirdek (testler bunları çağırır)
    dogrula: dogrula,
    parametreHatasi: parametreHatasi,
    varsayilanDegerler: varsayilanDegerler,
    hacimGirdisi: hacimGirdisi,
    hacimMm3: hacimMm3,
    fiyatKurus: fiyatKurus,
    detayMetni: detayMetni,
    hacimMetni: hacimMetni,

    // sayfa API'si
    kur: function (sema, kokEl, degisimCb) {
      durum.sema = sema; durum.alanlar = {}; durum.degisimCb = degisimCb || null;
      durum.yaziRenkEl = null;
      var degisim = function () { ciz(); if (durum.degisimCb) { durum.degisimCb(); } };
      for (var i = 0; i < sema.parametreler.length; i++) {
        durum.alanlar[sema.parametreler[i].ad] = alanKur(sema.parametreler[i], kokEl, degisim);
      }
      // Cerceve: yazi rengi (2. renk) secicisi param alanlarindan SONRA eklenir.
      if (cerceveMi(sema)) { yaziRenkKur(kokEl, degisim); }
      ciz();
    },
    hazir: function () { return !!durum.sema; },
    // Malzeme/renk seçici gibi DIŞ girdiler değişince fiyat göstergesini tazeler
    // (sayfa render()'ı çağırır; parametre alanları kendi input olaylarıyla zaten çizer).
    tazele: function () { if (durum.sema) { ciz(); } },
    // F kalemi: kart-secim sayfasi secili malzeme/rengi buradan saglar —
    // fn() -> {malzeme, renk} (bos degerler taban PLA/Siyah'a duser).
    secimKaynagi: function (fn) { durum.secimKaynagi = fn; },
    gecerliMi: function () {
      if (!durum.sema) { return false; }
      var d = degerler();
      if (!dogrula(durum.sema, d).gecerli) { return false; }
      // Cerceve 2-renk: yazi beyaz-liste veya dar-kenar hatasi add'i kilitler.
      var cer = cerceveDurumu(durum.sema, d, frameRengi());
      if (cer && (cer.yaziKirli || cer.kenarDar)) { return false; }
      return true;
    },
    // Sepet satırına parametrik alanları yazar (satır: PRUVO_SECENEK.bosSatir çıktısı).
    satiraYaz: function (satir) {
      if (!durum.sema) { return satir; }
      var d = degerler();
      if (!dogrula(durum.sema, d).gecerli) { return satir; }
      // Cerceve 2-renk (satir.renk = 1. renk): frameRenk olarak SATIRIN rengini kullan.
      var cer = cerceveDurumu(durum.sema, d, satir.renk);
      if (cer && (cer.yaziKirli || cer.kenarDar)) { return satir; }   // gecersiz -> parametrik yazma
      var h = hacimMm3(durum.sema, d);
      satir.parametreler = d;
      satir.parametre_detay = detayMetni(durum.sema, d);
      satir.hacim_mm3 = h;
      var kurus = (h == null) ? null
        : root.PRUVO_SECENEK.parametrikFiyatKurus(
            durum.sema.tabanFiyatTL, durum.sema.tabanHacimMm3, h, satir.malzeme, satir.renk);
      // 2-renk yazi: yazi_renk satira yazilir (ayri-satir anahtari + Worker teyidi) + +75 TL
      // (clamp DISI, Worker parametrik.js ile AYNI). Tek-renkte alan hic yazilmaz.
      if (cer && cer.ikiRenk && kurus != null) {
        satir.yazi_renk = cer.yaziRenk;
        kurus += IKI_RENK_EK_KURUS;
        satir.parametre_detay += " · Yazı rengi: " + cer.yaziRenk + " (2 renk, +75 TL)";
      }
      satir.parametrik_fiyat_kurus = kurus;
      return satir;
    }
  };

  if (typeof module === "object" && module.exports) { module.exports = KONF; }
  else { root.PRUVO_KONF = KONF; }
})(typeof self !== "undefined" ? self : this);
