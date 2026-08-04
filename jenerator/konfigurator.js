/* PRUVO — Ölçüye özel (parametrik) ürün konfigüratörü.
   Ürün sayfasında URUN_SEMA (üreteç inline eder) + /jenerator/hacim.js (PRUVO_HACIM)
   + /secenekler.js (PRUVO_SECENEK) ile çalışır. Parametre alanlarını kurar, canlı
   hacim + fiyat hesaplar (kuruş korunur, TL'ye yuvarlama yok), sınır dışı girişte
   alanı işaretler ve sepete eklemeyi kilitler. Fiyat, taban fiyat girilene kadar
   "—" gösterilir (tabanFiyatTL=null — altyapı hazır bekler).
   Saf JS, bağımlılıksız; doğrulama/fiyat fonksiyonları test edilebilirlik için saftır. */
(function (root) {
  "use strict";

  // Cerceve 2-renk yazi basilabilirlik esigi + beyaz liste. Min kenar 10 mm
  // (olculdu: 9mm sapta duvar 0.69mm kirilgan, 10mm'de 0.89mm saglam);
  // beyaz liste = derleyici sunucusunun METIN_BEYAZ_LISTE kumesiyle AYNI (harf/rakam + . , - _).
  //
  // 2-RENK EK UCRETI BURADA SABIT DEGIL: TEK KAYNAK /secenekler.js IKI_RENK_EK_KURUS —
  // Worker (parametrik kol) AYNI degeri okur, ikinci kopya YOK. Ayri sabit tutulursa
  // biri degisip digeri kalir ve musteriye gosterilen fiyat ile tahsil edilen fiyat ayrisir.
  var IKI_RENK_MIN_KENAR = 10;

  // Ek ucret + satir detay eki: DAIMA tek kaynaktan. secenekler.js yuklenmemisse 0/ucretsiz
  // metin — Worker'in fail-closed dali ile AYNI yon (asimetri = sessiz yanlis tahsilat).
  function ikiRenkEkKurus() {
    var S = root.PRUVO_SECENEK;
    var v = S ? S.IKI_RENK_EK_KURUS : null;
    return (typeof v === "number" && isFinite(v) && v > 0) ? v : 0;
  }
  function ikiRenkDetayEki(yaziRenk) {
    var S = root.PRUVO_SECENEK;
    return (S && typeof S.ikiRenkDetayEki === "function")
      ? S.ikiRenkDetayEki(yaziRenk)
      : (" · Yazı rengi: " + yaziRenk + " (2 renk)");
  }
  // TUM `metin` parametreleri icin gecerli (cerceve `yazi`, kase `metin`, jeton `yazi` ...):
  // sunucu (derleyici metin_temizle) beyaz liste DISI her karakteri
  // SESSIZCE DUSURUR — musteri "AHMET & OGULLARI" yazip "AHMET  OGULLARI" basilmis urun
  // alirdi, hicbir uyari cikmadan. Kural bu yuzden dogrula() yolunda (parametreHatasi ->
  // `metin` dali): hem sayfa (ciz/gecerliMi/satiraYaz) hem WORKER (parametrik kol
  // KONF.dogrula) ayni kapiyi kullanir. Sunucu tavani/beyaz listesi GEVSEMEZ — bu istemci
  // uyarisi onun YERINE gecmez, sadece kusuru GORUNUR kilar (sunucu hala fail-closed).
  var YAZI_BEYAZ_LISTE = /^[A-Za-z0-9ğüşıöçĞÜŞİÖÇ .,\-_]*$/;
  var YAZI_KIRLI_MESAJ = "Yalnızca harf, rakam ve  . , - _  kullanın";

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
      var metin = String(deger == null ? "" : deger);
      if (p.maksUzunluk && metin.length > p.maksUzunluk) {
        return "En çok " + p.maksUzunluk + " karakter";
      }
      // Beyaz liste DISI karakter (& / ( ) : ...) sunucuda SESSIZCE dusuyor -> burada
      // gorunur hata. Bos metin gecerli (regex `*`), Turkce harfler gecerli.
      if (!YAZI_BEYAZ_LISTE.test(metin)) { return YAZI_KIRLI_MESAJ; }
      return null;
    }
    return "Bilinmeyen parametre tipi";
  }

  // ---- kisit alt siniri -------------------------------------------------
  // `min` IKI bicimde yazilabilir:
  //   1) SAYI            -> sabit alt sinir (or. vida: civatada cap >= 5)
  //   2) DOGRUSAL BICIM  -> {terimler: {param: katsayi, ...}, sabit: c}
  //                         alt sinir = c + Σ katsayi * degerler[param]
  // (2) BASKA parametrelere bagli sinirlar icindir (or. rulman: yuvarlanma
  // elemani cap farkindan turer, genislik ondan kucuk olamaz). Sozluk
  // (terimler/sabit) uretim eslemindeki `sayisal` bloklariyla AYNIDIR — ikinci
  // bir kisit dili UYDURULMAZ.
  //
  // TOLERANS NEDEN VAR (olculmus muhendislik karari): dogrusal bicim katsayilari
  // ucte-birlerin ondalik yaklasimidir (0.95/3, 1/3). Sinir bir izgara noktasina
  // TAM oturabildigi icin (or. dis-ic=30, makara -> sinir tam 9,5 mm ve o genislik
  // URETILEBILIR olculdu) yuvarlama artigi toleranssiz kiyasta SATILABILIR bir
  // rulmani reddederdi. Izgarada sinira en yakin ESIT-OLMAYAN nokta >= 0,0073 mm
  // uzakta oldugundan 1e-6 tolerans yanlislikla KABUL edemez.
  var KISIT_TOLERANS = 1e-6;

  function kisitAltSinir(min, degerler) {
    if (typeof min === "number") { return isFinite(min) ? min : null; }
    if (!min || typeof min !== "object") { return null; }
    var toplam = (typeof min.sabit === "number") ? min.sabit : 0;
    var terimler = min.terimler || {};
    for (var ad in terimler) {
      if (!terimler.hasOwnProperty(ad)) { continue; }
      var v = degerler[ad];
      v = (typeof v === "number") ? v : parseFloat(String(v).replace(",", "."));
      // Referans parametre sayi degilse kisit OLCULEMEZ -> uygulanmaz. O
      // parametrenin KENDI min/max/adim hatasi zaten seti gecersiz kilar; burada
      // uydurma bir sinirla ikinci bir hata uretilmez.
      if (typeof v !== "number" || !isFinite(v)) { return null; }
      toplam += terimler[ad] * v;
    }
    return isFinite(toplam) ? toplam : null;
  }

  // Mesajda {min} varsa hesaplanan sinirla degistirilir. Yuvarlama YUKARI: gosterilen
  // deger daima gercek sinirin >='i olsun ki musteri onu yazinca set GECERLI olsun.
  function kisitMesaji(ks, altSinir) {
    var m = ks.mesaj || "En az {min} olmalı";
    if (m.indexOf("{min}") < 0) { return m; }
    var yuvarlak = Math.ceil(altSinir * 100) / 100;
    return m.replace("{min}", String(yuvarlak).replace(".", ","));
  }

  // ---- kisit BICIM tanimasi (fail-closed) --------------------------------
  // 🔴 2026-08-03, OLCULDU: taninmayan/okunamayan bir kisit kaydi eskiden SESSIZCE
  // ATLANIYORDU — kural yokmus gibi davranilip SIPARIS/ODEME yolunda fiyat
  // uretiliyordu (olcum: bozuk `kisitlar` bicimlerinde `parametrikHesapla`
  // 10.000 ve 29.116 kurus DONDURDU; kural saglamken ayni setler reddediliyor).
  // Kisit bir URETILEBILIRLIK kapisidir: "olculemedi" ile "gecerli" AYNI SEY DEGIL.
  // Artik taninmayan kayit seti GECERSIZ kilar -> tutar uretilmez, kalem teklif
  // kanalina duser (siparis kaybetmek yanlis tahsilattan iyidir).
  //
  // KAPSAM DAR: `kisitlar` HIC YOKSA (bugun 21/23 sema, satistaki ailelerin HEPSI)
  // tek satir bile degismez -> o ailelerde regresyon 0 (olculdu: kurus imzasi birebir).
  //
  // IKIZ TANIM YOK: tanima, UYGULAYAN kodun okudugu alanlarin AYNISINA bakar
  // (eger/parametre/min.terimler/min.sabit) — ikinci bir kisit dili uydurulmaz.
  //
  // IKI AYRI KOL, HER BIRI TEK BASINA KIRMIZI YAKILABILIR (savunma derinligi ancak
  // boyle KANITTIR — kabul takimindaki mutantlar ikisini ayri ayri olcer):
  //   1) YAPISAL tanima (asagidaki kisitTanindiMi) — deger-BAGIMSIZ. Tek basina
  //      yakaladigi ornek: `eger` bozuk (or. metin) -> kayit HICBIR sette uygulanmaz,
  //      koruma sessizce yok olurdu.
  //   2) OLCULEMEDI kolu (dogrula icinde) — deger-BAGIMLI. Tek basina yakaladigi
  //      ornek: `terimler` semada olmayan/sayisal olmayan bir parametreye bakiyor ->
  //      alt sinir hesaplanamaz; ya da kisit sayisal olmayan bir parametreye baglanmis
  //      -> kiyas degeri NaN. Ikisi de eskiden "kisit yok" sayiliyordu.
  var KISIT_ALANI = "__kisit";
  var KISIT_BICIM_MESAJI = "Ürün kısıt tanımı okunamadı";

  function kisitTanindiMi(ks) {
    if (!ks || typeof ks !== "object" || Array.isArray(ks)) { return false; }
    if (!ks.eger || typeof ks.eger !== "object" || Array.isArray(ks.eger)) { return false; }
    if (typeof ks.parametre !== "string" || ks.parametre === "") { return false; }
    var min = ks.min;
    if (typeof min === "number") { return isFinite(min); }
    if (!min || typeof min !== "object" || Array.isArray(min)) { return false; }
    if (min.sabit !== undefined && !(typeof min.sabit === "number" && isFinite(min.sabit))) {
      return false;
    }
    if (min.terimler === undefined) { return min.sabit !== undefined; }
    if (!min.terimler || typeof min.terimler !== "object" || Array.isArray(min.terimler)) {
      return false;
    }
    var terimSayisi = 0;
    for (var ad in min.terimler) {
      if (!min.terimler.hasOwnProperty(ad)) { continue; }
      terimSayisi++;
      var katsayi = min.terimler[ad];
      if (typeof katsayi !== "number" || !isFinite(katsayi)) { return false; }
    }
    return terimSayisi > 0 || min.sabit !== undefined;
  }

  // Tüm set doğrulaması -> {gecerli: bool, hatalar: {ad: mesaj}}
  // sema.kisitlar: koşullu üretilebilirlik kuralları — [{eger: {ad: deger},
  // parametre, min, mesaj}]. "eger"deki tüm eşitlikler tutuyorsa parametrenin
  // alt sınırı yükselir (örn. altıgen başlı cıvata üretim motorunda M5'ten başlar;
  // rulmanda genişlik alt sınırı iç/dış çaptan türer — bkz. kisitAltSinir).
  function dogrula(sema, degerler) {
    var hatalar = {}, gecerli = true, parametreHatasiVar = false;
    for (var i = 0; i < sema.parametreler.length; i++) {
      var p = sema.parametreler[i];
      var h = parametreHatasi(p, degerler[p.ad]);
      if (h) { hatalar[p.ad] = h; gecerli = false; parametreHatasiVar = true; }
    }
    var kisitlar = sema.kisitlar;
    if (kisitlar !== undefined && kisitlar !== null && !Array.isArray(kisitlar)) {
      // `kisitlar` VAR ama dizi degil: eski kod `.length` undefined okuyup donguyu HIC
      // kosmuyordu -> koruma sessizce yok olurdu. Artik gorunur red.
      hatalar[KISIT_ALANI] = KISIT_BICIM_MESAJI;
      gecerli = false;
      kisitlar = [];
    }
    for (var k = 0; k < (kisitlar || []).length; k++) {
      var ks = kisitlar[k];
      if (!kisitTanindiMi(ks)) {
        hatalar[KISIT_ALANI] = KISIT_BICIM_MESAJI;
        gecerli = false;
        continue;
      }
      var uygulanir = true;
      for (var ad2 in ks.eger) {
        if (!ks.eger.hasOwnProperty(ad2)) { continue; }
        if (degerler[ad2] !== ks.eger[ad2]) { uygulanir = false; break; }
      }
      if (!uygulanir || hatalar[ks.parametre]) { continue; }
      var kv = degerler[ks.parametre];
      kv = typeof kv === "number" ? kv : parseFloat(String(kv).replace(",", "."));
      var altSinir = kisitAltSinir(ks.min, degerler);
      // Kayit TANINDI ama alt sinir bu degerlerle HESAPLANAMADI (referans parametrenin
      // degeri sayiya cevrilemiyor) ya da kiyas edilecek deger NaN: kural OLCULEMEDI ->
      // fail-closed. Eskiden ikisi de sessizce "kisit yok" sayiliyordu.
      //
      // 🔴 YALNIZ SET BASKA TURLU GECERLIYKEN: kullanicinin girdigi bir olcu ZATEN
      // hataliysa (or. ic_cap "abc") alt sinir dogal olarak hesaplanamaz — o durumda
      // teshis O PARAMETRENIN hatasidir; ustune "kisit okunamadi" yazmak musteriye
      // ALAKASIZ bir tani gosterirdi. Set zaten gecersiz oldugu icin tutar yine
      // uretilmez, yani fail-closed KAYBEDILMIYOR; degisen sadece hangi hatanin
      // konustugu.
      if (altSinir == null || isNaN(kv)) {
        if (!parametreHatasiVar) {
          hatalar[KISIT_ALANI] = KISIT_BICIM_MESAJI;
          gecerli = false;
        }
        continue;
      }
      if (kv < altSinir - KISIT_TOLERANS) {
        hatalar[ks.parametre] = kisitMesaji(ks, altSinir);
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

  /* ÇAPA BAĞLAMI — `parametrikFiyatKurus`in çap çapalı ailelerde (bugün: rulman)
     ihtiyaç duyduğu tek şey. Fiyat kuralı secenekler.js'te TEKTİR; burada yalnız
     ona ŞEMAYI, seçilen ölçüleri, ŞEMANIN VARSAYILANLARINI ve AYNI hacim motorunu
     taşırız (referans hacim çalışma anında hesaplanır, sabit tablo YOK).
     🔴 TEK ÜRETİCİ: dört çağrı yerinin (bu dosyadaki 3 + Worker parametrik.js)
     hepsi bu fonksiyonu kullanır; ikinci bir bağlam kurucu YAZILMAZ. */
  function fiyatBaglami(sema, degerler, hacimModulu) {
    return {
      sema: sema,
      parametreler: hacimGirdisi(sema, degerler),
      varsayilanlar: hacimGirdisi(sema, varsayilanDegerler(sema)),
      hacimFn: function (p) { return hacimMm3(sema, p, hacimModulu); }
    };
  }

  function fiyatKurus(sema, degerler, malzeme, renk, moduller) {
    var SECENEK = (moduller && moduller.secenek) || root.PRUVO_SECENEK;
    var hacimModulu = moduller && moduller.hacim;
    var h = hacimMm3(sema, degerler, hacimModulu);
    if (h == null) { return null; }
    return SECENEK.parametrikFiyatKurus(sema.hacimFormulu, sema.tabanFiyatTL,
                                        sema.tabanHacimMm3, h, malzeme, renk,
                                        fiyatBaglami(sema, degerler, hacimModulu));
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
      durum.alanlar.yazi.hataEl.textContent = YAZI_KIRLI_MESAJ;
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
            sema.hacimFormulu, sema.tabanFiyatTL, sema.tabanHacimMm3, h, malzeme, renk,
            fiyatBaglami(sema, d));
      // 2-renk yazi ek ucreti: front gosterimi Worker (parametrik.js) ile AYNI olmali,
      // yoksa musteri 600 gorup 675 tahsil edilirdi (clamp DISI ek ucret). Tutar tek
      // kaynaktan (secenekler.js); bugun 0 -> gosterilen fiyat degismez.
      if (kurus != null && cer && cer.ikiRenk) { kurus += ikiRenkEkKurus(); }
      // Sari kural (isletme): taban fiyat girilmemis ailede (vida) "Olcuye ozel fiyat"
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
    // Kisit BICIM hatasinin `hatalar` anahtari — TEK KAYNAK. Worker (parametrik.js)
    // teshisi bu anahtardan turer; ikinci bir sabit tutulursa iki taraf ayrisir ve
    // musteri "aralik disi" gibi ALAKASIZ bir tani gorur.
    KISIT_ALANI: KISIT_ALANI,
    kisitTanindiMi: kisitTanindiMi,
    parametreHatasi: parametreHatasi,
    varsayilanDegerler: varsayilanDegerler,
    hacimGirdisi: hacimGirdisi,
    hacimMm3: hacimMm3,
    fiyatBaglami: fiyatBaglami,
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
            durum.sema.hacimFormulu, durum.sema.tabanFiyatTL, durum.sema.tabanHacimMm3,
            h, satir.malzeme, satir.renk, fiyatBaglami(durum.sema, d));
      // 2-renk yazi: yazi_renk satira yazilir (ayri-satir anahtari + Worker teyidi) + ek ucret
      // (clamp DISI, tutar+metin secenekler.js'ten — Worker parametrik.js ile AYNI kaynak).
      // Tek-renkte alan hic yazilmaz.
      if (cer && cer.ikiRenk && kurus != null) {
        satir.yazi_renk = cer.yaziRenk;
        kurus += ikiRenkEkKurus();
        satir.parametre_detay += ikiRenkDetayEki(cer.yaziRenk);
      }
      satir.parametrik_fiyat_kurus = kurus;
      return satir;
    }
  };

  if (typeof module === "object" && module.exports) { module.exports = KONF; }
  else { root.PRUVO_KONF = KONF; }
})(typeof self !== "undefined" ? self : this);
