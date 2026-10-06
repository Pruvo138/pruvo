/*
 * foto-uretim.js — PRUVO ana sayfa "Fotoğrafından özel üretim" bölümü ekranı.
 *
 * - Veri: window.PRUVO_FOTO (foto-uretim-veri.js) — turler, ornekler, onay.
 * - API'ler: GET /api/shop/foto/acik, POST /api/shop/foto/onizleme,
 *   GET /api/shop/foto/durum, POST /api/shop/baslat.
 * - Bot: Cloudflare Turnstile (sitekey, script URL).
 * - Durum makinesi: kapali (bolum kapali) · S1 (form) · S2 (onizleme bekleniyor)
 *   · S3 (onizleme hazir) · S4 (siparis formu).
 * - ES5 IIFE; template literal yok, regex literal yok (yayin minifier uyumu);
 *   dis kutuphane yok. DOM yalniz createElement + textContent ile.
 */
(function () {
  "use strict";

  /* ============== SABITLER ============== */
  var ACIK_URL = "/api/shop/foto/acik";
  var ONIZLEME_URL = "/api/shop/foto/onizleme";
  var DURUM_URL = "/api/shop/foto/durum";
  var LITOFAN_URL = "/api/shop/foto/litofan";
  // LITOFAN (deterministik kol): gri ton -> kalınlık (koyu = kalın), arkadan ışık benzetimi.
  var LITOFAN_KALINLIK_EN_AZ = 0.6;
  var LITOFAN_KALINLIK_EN_COK = 3.0;
  var LITOFAN_KENAR_PX = 1200;
  var LITOFAN_ORAN_EN_COK = 5;
  var LITOFAN_ONIZLEME_PX = 320;
  var LITOFAN_DURUSTLUK =
    "Önizleme, ışığa tutulduğunda görünecek görüntünün yaklaşık benzetimidir; birebir aynısı değildir.";
  var BASLAT_URL = "/api/shop/baslat";
  var TURNS_SITEKEY = "0x4AAAAAAE6AA20ln7MIOR9k";
  var TURNS_KAYNAK = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
  var MAKS_DOSYA_BAYT = 15 * 1024 * 1024;
  var MAKS_KENAR = 1600;
  var MIN_ADET = 1;
  var MAKS_ADET = 5;
  var YOKLAMA_MS = 3000;
  var YOKLAMA_TAVAN = 80;
  var WA = "https://wa.me/905451386526";
  var GIZLILIK_URL = "/gizlilik/";
  var TESLIMAT_URL = "/teslimat-iade/";
  var MESAFELI_URL = "/mesafeli-satis/";
  var ANA_BOLUM_ID = "fotoUretim";
  var STIL_ID = "fotoUretimStil";
  var SS_IS = "pruvo_foto_is";
  var SS_SIPARIS = "pruvo_foto_siparis";
  // Render orneginin altindaki cumle TUR KAYDINDA (`ornek_notu`, mimar karari 7 Eki; AYNEN).
  // D/R turunde siparis oncesi onizleme YOKSA ornek render + bu cumle gosterilir.
  var ONIZLEME_SONRA = "Önizleme, ödeme sonrası üretim dosyasıyla birlikte hazırlanır.";
  // Uretec kimligi -> tarayicida siparis oncesi onizleme cizen kol (yalniz litofan bugun).
  var TARAYICI_ONIZLEYICI = { litofan_uret: true };
  var PARAMETRE_HATA = {
    "parametre-aralik": "Değer izinli aralığın dışında.",
    "parametre-adim": "Değer izinli adıma uymuyor.",
    "parametre-secim": "Listeden bir seçenek seç.",
    "parametre-metin": "Metin alanını doldur (izinli uzunlukta).",
    "parametre-url": "Bağlantı https:// ile başlamalı."
  };
  /* Dürüstlük kutusu metni TÜR BAZLI: manifest `durustluk` (seçili türünki; durustlukGuncelle). */
  /* ============== REFERANSLAR ============== */
  var kok = typeof window !== "undefined" ? window :
    (typeof globalThis !== "undefined" ? globalThis : this);
  var F = kok.PRUVO_FOTO || null;
  var SECENEK = kok.PRUVO_SECENEK || null;

  /* ============== DOGRULAMA KALIPLARI (RegExp literal YOK) ============== */
  var isKalibi = new RegExp("^[a-f0-9]{32}$");
  var rakDisi = new RegExp("[^0-9]", "g");
  var epostaKalibi = new RegExp("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$");

  /* ============== DURUM ============== */
  var S = {
    adim: "kapali",
    acikVeri: null,
    tur: null,
    olcu: null,
    adet: 1,
    dosya: null,
    hakOnay: false,
    aktarimOnay: false,
    captchaToken1: "",
    captchaToken2: "",
    is: null,
    gorsel: null,
    gecerlilik: null,
    ilerleme: null,
    bildirim: "",
    bildirimHata: false,
    yoksIs: null,
    yoksSayac: 0,
    alan: null,
    adimCubugu: null,
    alanTur: null,
    alanOlcu: null,
    alanForm: null,
    alanOnizlemeSonra: null,
    ornekBlok: null,
    parametre: {},
    alanDosya: null,
    alanOnay: null,
    alanCap1: null,
    alanNotu: null,
    alanButon: null,
    alanAd: null,
    alanTel: null,
    alanEposta: null,
    alanAdres: null,
    alanSehir: null,
    alanNotM: null,
    alanSoz: null,
    alanCap2: null,
    alanOde: null,
    sozlesme: false,
    ad: "",
    tel: "",
    eposta: "",
    adres: "",
    sehir: "",
    musteriNotu: ""
  };

  /* ============== DOM YARDIMCILAR ============== */
  function el(etiket, sinif, metin) {
    var n = document.createElement(etiket);
    if (sinif) n.className = sinif;
    if (metin != null) n.textContent = String(metin);
    return n;
  }
  function ek(parent) {
    for (var i = 1; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null) continue;
      if (typeof c === "string") parent.appendChild(document.createTextNode(c));
      else parent.appendChild(c);
    }
    return parent;
  }
  function tlMetni(kurus) {
    if (SECENEK && typeof SECENEK.kurusMetni === "function") return SECENEK.kurusMetni(kurus);
    if (kurus == null) return "";
    var t = (kurus / 100).toFixed(2);
    return t.replace(".", ",") + " TL";
  }
  function kargoUcreti(urunToplamKurus) {
    if (SECENEK && typeof SECENEK.kargoKurus === "function") return SECENEK.kargoKurus(urunToplamKurus);
    if (!(urunToplamKurus > 0)) return 0;
    return urunToplamKurus >= 250000 ? 0 : 25000;
  }
  function yerelSaat(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    var gun = String(d.getDate());
    var ay = String(d.getMonth() + 1);
    var saat = String(d.getHours());
    var dak = String(d.getMinutes());
    if (gun.length < 2) gun = "0" + gun;
    if (ay.length < 2) ay = "0" + ay;
    if (saat.length < 2) saat = "0" + saat;
    if (dak.length < 2) dak = "0" + dak;
    return gun + "." + ay + "." + d.getFullYear() + " " + saat + ":" + dak;
  }

  /* ============== STIL ENJEKSIYONU ============== */
  function stilEnjeket() {
    if (document.getElementById(STIL_ID)) return;
    var stil = document.createElement("style");
    stil.id = STIL_ID;
    stil.textContent = cssMetin;
    document.head.appendChild(stil);
  }
  var cssMetin =
    ".foto-uretim{margin:0 -20px 22px;padding:28px 20px;min-height:100vh;" +
    "min-height:100svh;background:var(--navy);color:#fff;" +
    "box-shadow:0 0 0 100vmax var(--navy);clip-path:inset(0 -100vmax);}" +
    ".foto-uretim[hidden]{display:none!important;}" +
    ".foto-uretim-icerik{max-width:1100px;margin:0 auto;}" +
    ".foto-uretim-baslik{font-size:24px;font-weight:700;margin:0 0 8px;" +
    "color:#fff;line-height:1.3;}" +
    ".foto-uretim-alt{font-size:15px;margin:0 0 18px;color:#cfd6e0;line-height:1.5;}" +
    ".foto-uretim-durustluk{background:#fff;color:var(--navy);border-radius:8px;" +
    "padding:14px 18px;margin:0 0 20px;font-size:14px;line-height:1.5;}" +
    ".foto-uretim-durustluk p{margin:0;}" +
    ".foto-uretim-blok{background:#fff;color:var(--navy);border-radius:8px;" +
    "padding:16px;margin:0 0 14px;}" +
    ".foto-uretim-blok-baslik{font-size:16px;font-weight:700;margin:0 0 12px;}" +
    ".foto-uretim-ornek-grup{margin:0 0 16px;}" +
    ".foto-uretim-ornek-grup:last-child{margin-bottom:0;}" +
    ".foto-uretim-ornek-gorseller{display:flex;gap:10px;margin:0 0 6px;}" +
    ".foto-uretim-ornek-gorsel{flex:1;aspect-ratio:1/1;width:100%;" +
    "height:auto;max-width:100%;object-fit:cover;border-radius:6px;" +
    "background:#eef0f3;display:block;}" +
    ".foto-uretim-ornek-baslik{font-size:13px;color:var(--navy);line-height:1.4;}" +
    ".foto-uretim-ornek-etiket{font-size:11px;color:#5b6573;margin-top:2px;}" +
    ".foto-uretim-ornek-not{font-size:12px;color:#5b6573;line-height:1.45;margin:4px 0 0;}" +
    ".foto-uretim-adimlar{display:flex;align-items:center;gap:8px;margin:14px 0;" +
    "flex-wrap:wrap;}" +
    ".foto-uretim-adim{flex:1 1 120px;padding:8px 10px;background:rgba(255,255,255,0.12);" +
    "border-radius:6px;text-align:center;font-size:13px;color:#fff;font-weight:600;}" +
    ".foto-uretim-adim.aktif{background:#d1332e;}" +
    ".foto-uretim-adim-ok{color:#fff;font-size:16px;}" +
    ".foto-uretim-alani{background:#fff;color:var(--navy);border-radius:8px;" +
    "padding:18px;margin-top:6px;}" +
    ".foto-uretim-durum{padding:8px 12px;border-radius:6px;background:#eef0f3;" +
    "font-size:14px;margin:0 0 12px;}" +
    ".foto-uretim-durum.hata{background:#fde7e7;color:#a3261e;}" +
    ".foto-uretim-form-grup{margin:0 0 14px;}" +
    ".foto-uretim-form-etiket{display:block;font-size:14px;font-weight:600;" +
    "margin:0 0 6px;}" +
    ".foto-uretim-form-secenek{display:block;padding:8px 10px;border:1px solid #d4dae3;" +
    "border-radius:6px;margin:0 0 6px;cursor:pointer;font-size:14px;}" +
    ".foto-uretim-form-secenek-girdi{display:block;width:100%;max-width:100%;" +
    "padding:8px 10px;border:1px solid #d4dae3;border-radius:6px;font-size:14px;" +
    "box-sizing:border-box;margin:0 0 6px;}" +
    ".foto-uretim-form-secenek-inline{display:flex;align-items:flex-start;" +
    "gap:8px;padding:8px 10px;border:1px solid #d4dae3;border-radius:6px;" +
    "margin:0 0 6px;cursor:pointer;font-size:14px;}" +
    ".foto-uretim-form-secenek-inline input{flex-shrink:0;margin-top:3px;}" +
    ".foto-uretim-buton-birincil{background:#d1332e;color:#fff;border:none;" +
    "padding:11px 22px;border-radius:6px;font-size:15px;font-weight:600;" +
    "cursor:pointer;max-width:100%;}" +
    ".foto-uretim-buton-birincil[disabled]{background:#b0b8c0;cursor:not-allowed;}" +
    ".foto-uretim-buton-ikincil{background:transparent;color:var(--navy);" +
    "border:1px solid var(--navy);padding:9px 18px;border-radius:6px;" +
    "font-size:14px;cursor:pointer;max-width:100%;margin-top:8px;}" +
    ".foto-uretim-captcha{margin:14px 0;}" +
    ".foto-uretim-onizleme-img{display:block;max-width:100%;height:auto;" +
    "border-radius:6px;margin:10px 0;background:#eef0f3;}" +
    ".foto-uretim-ozet{background:#eef0f3;padding:12px;border-radius:6px;" +
    "font-size:14px;margin:10px 0;line-height:1.6;}" +
    ".foto-uretim-ayrinti{font-size:13px;color:#5b6573;margin:8px 0;line-height:1.5;}" +
    ".foto-uretim-aydinlatma{margin:8px 0;font-size:13px;}" +
    ".foto-uretim-aydinlatma summary{cursor:pointer;font-weight:600;}" +
    ".foto-uretim-aydinlatma p{margin:6px 0;}" +
    ".foto-uretim-kapat-a{color:#d1332e;text-decoration:underline;}" +
    ".foto-uretim-iliskili{display:flex;flex-wrap:wrap;gap:10px;align-items:center;" +
    "margin:8px 0;}" +
    ".foto-uretim-ilerleme-dis{height:8px;background:#eef0f3;border-radius:4px;" +
    "overflow:hidden;margin:8px 0;}" +
    ".foto-uretim-ilerleme-ic{height:100%;background:#d1332e;width:0;}" +
    ".foto-uretim-s1-buton-sira{margin-top:8px;}" +
    "img,input,button,textarea,select{max-width:100%;}" +
    ".foto-uretim *{overflow-wrap:anywhere;}" +
    "@media (max-width:640px){" +
    ".foto-uretim-ornek-gorseller{flex-direction:column;}" +
    "}";

  /* ============== TURNSTILE ============== */
  function turnsYukle(cb) {
    if (kok.turnstile && typeof kok.turnstile.render === "function") { cb(true); return; }
    var mevcut = document.querySelector('script[src*="challenges.cloudflare.com/turnstile"]');
    if (mevcut) {
      var deneme = 0;
      var id = setInterval(function () {
        deneme++;
        if (kok.turnstile || deneme > 30) { clearInterval(id); cb(!!kok.turnstile); }
      }, 100);
      return;
    }
    var s = document.createElement("script");
    s.src = TURNS_KAYNAK;
    s.async = true;
    s.onload = function () { cb(true); };
    s.onerror = function () { cb(false); };
    document.head.appendChild(s);
  }
  function turnsRender(kutu, cb) {
    if (!kutu) { cb(""); return; }
    turnsYukle(function (ok) {
      if (!ok || !kok.turnstile) { cb(""); return; }
      try {
        var wid = kok.turnstile.render(kutu, {
          sitekey: TURNS_SITEKEY,
          callback: function (t) { cb(t || ""); },
          "error-callback": function () { cb(""); },
          "expired-callback": function () { cb(""); }
        });
        kutu.setAttribute("data-wid", String(wid));
      } catch (e) { cb(""); }
    });
  }
  function turnsTemizle(kutu) {
    if (!kutu) return;
    var wid = kutu.getAttribute("data-wid");
    if (wid && kok.turnstile && typeof kok.turnstile.remove === "function") {
      try { kok.turnstile.remove(wid); } catch (e) { }
    }
    kutu.removeAttribute("data-wid");
    while (kutu.firstChild) kutu.removeChild(kutu.firstChild);
  }
  function turnsSifirla(kutu) {
    if (!kutu) return;
    var wid = kutu.getAttribute("data-wid");
    if (wid && kok.turnstile && typeof kok.turnstile.reset === "function") {
      try { kok.turnstile.reset(wid); } catch (e) { }
    }
  }

  /* ============== GORSEL KUCULTME ============== */
  function kucultGorsel(dosya, cb) {
    if (!dosya) { cb(new Error("yok"), null); return; }
    if (dosya.size > MAKS_DOSYA_BAYT) { cb(new Error("boyut-buyuk"), null); return; }
    if (dosya.size < 100) { cb(new Error("boyut-kucuk"), null); return; }
    var okuyucu = new FileReader();
    okuyucu.onload = function (e) {
      var img = new Image();
      img.onload = function () {
        var w = img.width, h = img.height;
        if (!w || !h) { cb(new Error("boyut"), null); return; }
        var enUzun = w > h ? w : h;
        var olcek = enUzun > MAKS_KENAR ? MAKS_KENAR / enUzun : 1;
        var nw = Math.round(w * olcek), nh = Math.round(h * olcek);
        var tuval = document.createElement("canvas");
        tuval.width = nw; tuval.height = nh;
        var ctx = tuval.getContext("2d");
        ctx.drawImage(img, 0, 0, nw, nh);
        try {
          var dataUrl = tuval.toDataURL("image/jpeg", 0.9);
          cb(null, dataUrl);
        } catch (er) { cb(er, null); }
      };
      img.onerror = function () { cb(new Error("okuma"), null); };
      img.src = e.target.result;
    };
    okuyucu.onerror = function () { cb(new Error("dosya"), null); };
    okuyucu.readAsDataURL(dosya);
  }

  /* ============== AG ============== */
  function jsonGetir(url, cb) {
    fetch(url, { credentials: "same-origin" }).then(function (r) {
      var ok = r.ok;
      r.json().then(function (d) { cb(ok, r.status, d); }, function () { cb(ok, r.status, null); });
    }, function () { cb(false, 0, null); });
  }
  function jsonPost(url, govde, cb) {
    fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(govde)
    }).then(function (r) {
      var ok = r.ok;
      r.json().then(function (d) { cb(ok, r.status, d); }, function () { cb(ok, r.status, null); });
    }, function () { cb(false, 0, null); });
  }

  /* ============== OTURUM DEPOSU ============== */
  function ssIsKaydet() {
    if (!S.is) return;
    var kayit = { is: S.is, tur: S.tur, olcu: S.olcu };
    if (litofanSecili() && S.secim) kayit.secim = S.secim;
    try { sessionStorage.setItem(SS_IS, JSON.stringify(kayit)); }
    catch (e) { }
  }
  function ssIsSil() {
    try { sessionStorage.removeItem(SS_IS); } catch (e) { }
    S.is = null;
  }
  function ssIsOku() {
    try {
      var ham = sessionStorage.getItem(SS_IS);
      if (!ham) return null;
      var p = JSON.parse(ham);
      if (!p || typeof p.is !== "string" || !isKalibi.test(p.is)) return null;
      return p;
    } catch (e) { return null; }
  }

  /* ============== YOKLAMA DURDURMA ============== */
  function yoksDurdur() {
    if (S.yoksIs) { clearInterval(S.yoksIs); S.yoksIs = null; }
    S.yoksSayac = 0;
  }

  /* ============== ADIM CUBUGU ============== */
  function adimGoster(n) {
    if (!S.adimCubugu) return;
    var dugumler = S.adimCubugu.childNodes;
    for (var i = 0; i < dugumler.length; i++) {
      var node = dugumler[i];
      if (node && node.nodeType === 1 && node.classList && node.classList.contains("foto-uretim-adim")) {
        var no = parseInt(node.getAttribute("data-no"), 10);
        if (no === n) node.classList.add("aktif"); else node.classList.remove("aktif");
      }
    }
  }

  /* ============== DURUM CUBUGU (siparis alani ustunde) ============== */
  function durumCubuguGoster() {
    if (!S.alan) return;
    var eski = S.alan.querySelector(".foto-uretim-durum");
    if (eski && eski.parentNode) eski.parentNode.removeChild(eski);
    if (!S.bildirim) return;
    var d = el("div", "foto-uretim-durum" + (S.bildirimHata ? " hata" : ""), S.bildirim);
    if (S.alan.firstChild) S.alan.insertBefore(d, S.alan.firstChild); else S.alan.appendChild(d);
  }

  /* ============== ANA YAPISI ============== */
  // Adım 2 etiketi tür SAYISINA göre: F = veri dosyası ya da /acik yanıtı (ikisi de .turler taşır).
  function adim2Etiketi(F) { return F.turler.length > 1 ? "Tür ve ölçü" : "Ölçü"; }

  /* ============== LITOFAN (deterministik kol) ============== */
  // Deterministik kol + tarayıcı önizleyicisi kayıtlı üreteç (bugün litofan).
  function litofanSecili() {
    var t = F && typeof F.turBul === "function" && S.tur ? F.turBul(S.tur) : null;
    return !!(t && F.kolu(S.tur) === "deterministik" && TARAYICI_ONIZLEYICI[t.uretec] === true);
  }
  // Deterministik kol, sipariş öncesi önizleme YOK: örnek render + ONIZLEME_SONRA gösterilir.
  function onizlemeSonraSecili() {
    var t = F && typeof F.turBul === "function" && S.tur ? F.turBul(S.tur) : null;
    return !!(t && F.kolu(S.tur) === "deterministik" && TARAYICI_ONIZLEYICI[t.uretec] !== true);
  }
  function litofanKaydi() { return F && typeof F.turBul === "function" ? F.turBul(S.tur) : null; }
  // Kayıttan varsayılan seçim: her malzeme bölgesinin ilk malzemesi, her renk bölgesinin ilk rengi.
  function litofanSecimKur() {
    var t = litofanKaydi();
    var sec = {};
    if (!t) return sec;
    var mb = t.malzemeler || {};
    for (var b in mb) {
      if (Object.prototype.hasOwnProperty.call(mb, b) && mb[b] && mb[b].length) {
        sec[b + "_malzeme"] = S.secim && mb[b].indexOf(S.secim[b + "_malzeme"]) >= 0 ? S.secim[b + "_malzeme"] : mb[b][0];
      }
    }
    var rb = t.renk_bolgeleri || [];
    for (var i = 0; i < rb.length; i++) {
      var r = rb[i].renkler || [];
      if (!r.length) continue;
      sec[rb[i].kod + "_renk"] = S.secim && r.indexOf(S.secim[rb[i].kod + "_renk"]) >= 0 ? S.secim[rb[i].kod + "_renk"] : r[0];
    }
    return sec;
  }
  function radyoGrubu(kutu, etiket, ad, liste, secili, cb) {
    var g = el("div", "foto-uretim-litofan-secim");
    g.appendChild(el("span", "foto-uretim-form-etiket", etiket));
    for (var i = 0; i < liste.length; i++) {
      var lbl = el("label", "foto-uretim-form-secenek-inline");
      var inp = el("input");
      inp.type = "radio"; inp.name = ad; inp.value = liste[i];
      if (secili === liste[i]) inp.checked = true;
      (function (deger) {
        inp.addEventListener("change", function (e) { if (e.target.checked) cb(deger); });
      })(liste[i]);
      ek(lbl, inp, " " + liste[i]);
      g.appendChild(lbl);
    }
    kutu.appendChild(g);
  }
  // Renk (ayak) + malzeme (panel/ayak) seçimi — kayıttan çizilir; tek seçenekli bölge yazıyla gösterilir.
  function doldurS1Litofan() {
    if (!S.alanSecim || !S.alanLitofan) return;
    while (S.alanSecim.firstChild) S.alanSecim.removeChild(S.alanSecim.firstChild);
    var t = litofanKaydi();
    var secimVar = !!(t && t.renk_bolgeleri && t.renk_bolgeleri.length);
    S.alanSecim.hidden = !secimVar;
    S.alanLitofan.hidden = !litofanSecili();
    doldurS1OnizlemeSonra();
    if (!secimVar) { if (litofanSecili()) litofanOnizle(); else guncelleS1Buton(); return; }
    S.secim = litofanSecimKur();
    S.alanSecim.appendChild(el("label", "foto-uretim-form-etiket", "Malzeme ve renk"));
    var rb = (t && t.renk_bolgeleri) || [];
    var mb = (t && t.malzemeler) || {};
    for (var i = 0; i < rb.length; i++) {
      (function (bolge) {
        var ml = mb[bolge.kod] || [];
        if (ml.length > 1) {
          radyoGrubu(S.alanSecim, bolge.ad + " — malzeme", "foto-litofan-" + bolge.kod + "-malzeme", ml,
            S.secim[bolge.kod + "_malzeme"], function (d) { S.secim[bolge.kod + "_malzeme"] = d; });
        }
        var rl = bolge.renkler || [];
        if (rl.length > 1) {
          radyoGrubu(S.alanSecim, bolge.ad + " — renk", "foto-litofan-" + bolge.kod + "-renk", rl,
            S.secim[bolge.kod + "_renk"], function (d) { S.secim[bolge.kod + "_renk"] = d; });
        } else if (rl.length === 1) {
          S.alanSecim.appendChild(el("p", "foto-uretim-ayrinti", bolge.ad + ": " + rl[0] +
            (ml.length === 1 ? " · " + ml[0] : "")));
        }
      })(rb[i]);
    }
    if (litofanSecili()) litofanOnizle(); else guncelleS1Buton();
  }
  // D/R türünde sipariş öncesi önizleme yoksa: türün örnek render'ı + ONIZLEME_SONRA.
  function doldurS1OnizlemeSonra() {
    if (!S.alanOnizlemeSonra) return;
    while (S.alanOnizlemeSonra.firstChild) S.alanOnizlemeSonra.removeChild(S.alanOnizlemeSonra.firstChild);
    var acik = onizlemeSonraSecili();
    S.alanOnizlemeSonra.hidden = !acik;
    if (!acik) return;
    var t = litofanKaydi();
    for (var i = 0; i < F.ornekler.length; i++) {
      var o = F.ornekler[i];
      if (o && o.tur === S.tur && F.ornekGecerli(o) && (o.render || o.baski)) {
        S.alanOnizlemeSonra.appendChild(el("p", "foto-uretim-form-etiket", "Örnek"));
        var img = el("img", "foto-uretim-ornek-gorsel");
        img.src = o.render || o.baski; img.alt = t.ad + " örnek";
        img.width = 300; img.height = 300; img.loading = "lazy"; img.decoding = "async";
        S.alanOnizlemeSonra.appendChild(img);
        break;
      }
    }
    S.alanOnizlemeSonra.appendChild(el("p", "foto-uretim-ayrinti", ONIZLEME_SONRA));
  }

  // FORM ALANLARI — türün `form` şemasından (sayi/secim/metin/url); doğrulama sunucuyla AYNI
  // fonksiyon (F.parametreDogrula). Şema boşsa alan gizli, gövdeye `parametreler` girmez.
  function formSemasi() {
    var t = litofanKaydi();
    return t && t.form && typeof t.form === "object" ? t.form : {};
  }
  function parametreGovde() {
    var form = formSemasi(), g = {};
    for (var a in form) {
      if (Object.prototype.hasOwnProperty.call(form, a) && S.parametre[a] !== undefined) g[a] = S.parametre[a];
    }
    return g;
  }
  function formDogrula() {
    if (!Object.keys(formSemasi()).length) return { ok: true };
    return F.parametreDogrula(S.tur, parametreGovde());
  }
  function formHataGoster() {
    if (!S.alanForm || !S.formHata) return;
    var d = formDogrula();
    S.formHata.textContent = d.ok ? "" : (PARAMETRE_HATA[d.hata] || "Bu alanları kontrol et.");
    S.formHata.hidden = d.ok;
  }
  function doldurS1Form() {
    if (!S.alanForm) return;
    while (S.alanForm.firstChild) S.alanForm.removeChild(S.alanForm.firstChild);
    var form = formSemasi(), alanlar = Object.keys(form);
    S.alanForm.hidden = !alanlar.length;
    if (!alanlar.length) return;
    for (var i = 0; i < alanlar.length; i++) {
      (function (a, sema) {
        var id = "foto-param-" + a;
        var lbl = el("label", "foto-uretim-form-etiket",
          (sema.etiket || a) + (sema.tip === "sayi" && sema.birim ? " (" + sema.birim + ")" : ""));
        lbl.setAttribute("for", id);
        S.alanForm.appendChild(lbl);
        var g;
        if (sema.tip === "secim") {
          g = el("select", "foto-uretim-form-secenek-girdi");
          var ss = sema.secenekler || [];
          for (var j = 0; j < ss.length; j++) {
            var op = el("option", null, String(ss[j]));
            op.value = String(ss[j]);
            g.appendChild(op);
          }
          if (S.parametre[a] === undefined && ss.length) S.parametre[a] = ss[0];
          if (S.parametre[a] !== undefined) g.value = String(S.parametre[a]);
        } else {
          g = el("input", "foto-uretim-form-secenek-girdi");
          if (sema.tip === "sayi") {
            g.type = "number"; g.min = String(sema.min); g.max = String(sema.max);
            g.step = String(sema.adim > 0 ? sema.adim : 1);
            if (S.parametre[a] === undefined) S.parametre[a] = sema.min;
          } else if (sema.tip === "url") {
            g.type = "url"; g.placeholder = "https://";
          } else {
            g.type = "text";
            if (sema.max > 0) g.maxLength = sema.max;
          }
          if (S.parametre[a] !== undefined) g.value = String(S.parametre[a]);
        }
        g.id = id; g.name = id;
        var degis = function (e) {
          var v = e.target.value;
          if (sema.tip === "sayi") S.parametre[a] = v === "" ? undefined : Number(v);
          else if (sema.tip === "secim") {
            var ss2 = sema.secenekler || [], bul;
            for (var k = 0; k < ss2.length; k++) { if (String(ss2[k]) === v) { bul = ss2[k]; break; } }
            S.parametre[a] = bul;
          } else S.parametre[a] = v === "" ? undefined : v;
          formHataGoster();
          guncelleS1Buton();
        };
        g.addEventListener("input", degis);
        g.addEventListener("change", degis);
        S.alanForm.appendChild(g);
      })(alanlar[i], form[alanlar[i]] || {});
    }
    S.formHata = el("p", "foto-uretim-ayrinti");
    S.alanForm.appendChild(S.formHata);
    formHataGoster();
  }
  // Seçilen fotoğraftan ANINDA önizleme (tarayıcıda; fotoğraf hiçbir yere gönderilmez).
  function litofanOnizle() {
    if (!S.alanLitofan) return;
    while (S.alanLitofan.firstChild) S.alanLitofan.removeChild(S.alanLitofan.firstChild);
    S.litofanHarita = null;
    S.litofanOnizleme = null;
    if (!litofanSecili()) { guncelleS1Buton(); return; }
    S.alanLitofan.appendChild(el("p", "foto-uretim-ayrinti",
      "Litofan önizlemesi tarayıcında çizilir: fotoğrafın sunucuya ya da hizmet sağlayıcıya gönderilmez; " +
      "siparişte yalnız ondan çıkarılan gri kalınlık haritası alınır."));
    if (!S.dosya) { guncelleS1Buton(); return; }
    var okuyucu = new FileReader();
    okuyucu.onload = function (e) {
      var img = new Image();
      img.onload = function () { litofanCiz(img); };
      img.onerror = function () { litofanUyari("Fotoğraf okunamadı (JPEG, PNG ya da WEBP)."); };
      img.src = e.target.result;
    };
    okuyucu.onerror = function () { litofanUyari("Fotoğraf okunamadı."); };
    okuyucu.readAsDataURL(S.dosya);
  }
  function litofanUyari(metin) {
    S.alanLitofan.appendChild(el("p", "foto-uretim-bildirim foto-uretim-bildirim-hata", metin));
    guncelleS1Buton();
  }
  function litofanCiz(img) {
    var en = img.naturalWidth || img.width, boy = img.naturalHeight || img.height;
    if (!en || !boy) { litofanUyari("Fotoğraf okunamadı."); return; }
    if (Math.max(en, boy) > LITOFAN_ORAN_EN_COK * Math.min(en, boy)) {
      litofanUyari("Bu fotoğraf çok uzun ya da çok dar (en/boy oranı 5:1'den büyük); litofan için başka bir fotoğraf seç.");
      return;
    }
    var o = Math.min(1, LITOFAN_KENAR_PX / Math.max(en, boy));
    var hw = Math.max(1, Math.round(en * o)), hh = Math.max(1, Math.round(boy * o));
    var harita = document.createElement("canvas");
    harita.width = hw; harita.height = hh;
    var hc = harita.getContext("2d");
    hc.drawImage(img, 0, 0, hw, hh);
    var veri = hc.getImageData(0, 0, hw, hh);
    var d = veri.data;
    for (var i = 0; i < d.length; i += 4) {
      var g = Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
      d[i] = g; d[i + 1] = g; d[i + 2] = g; d[i + 3] = 255;
    }
    hc.putImageData(veri, 0, 0);
    S.litofanHarita = harita.toDataURL("image/png");
    // Arkadan ışık: kalınlık 0,6–3,0 mm (koyu = kalın); geçen ışık kalınlıkla üstel azalır.
    var po = Math.min(1, LITOFAN_ONIZLEME_PX / Math.max(hw, hh));
    var pw = Math.max(1, Math.round(hw * po)), ph = Math.max(1, Math.round(hh * po));
    var tuval = document.createElement("canvas");
    tuval.width = pw; tuval.height = ph;
    tuval.className = "foto-uretim-onizleme-img";
    var tc = tuval.getContext("2d");
    tc.drawImage(harita, 0, 0, pw, ph);
    var pv = tc.getImageData(0, 0, pw, ph);
    var pd = pv.data;
    var aralik = LITOFAN_KALINLIK_EN_COK - LITOFAN_KALINLIK_EN_AZ;
    for (var j = 0; j < pd.length; j += 4) {
      var kalinlik = LITOFAN_KALINLIK_EN_AZ + (1 - pd[j] / 255) * aralik;
      var isik = Math.exp(-1.25 * (kalinlik - LITOFAN_KALINLIK_EN_AZ));
      pd[j] = Math.round(255 * isik); pd[j + 1] = Math.round(236 * isik); pd[j + 2] = Math.round(200 * isik); pd[j + 3] = 255;
    }
    tc.putImageData(pv, 0, 0);
    S.litofanOnizleme = tuval.toDataURL("image/png");
    var kap = el("div", "foto-uretim-litofan-onizleme");
    kap.appendChild(el("p", "foto-uretim-form-etiket", "Önizleme"));
    kap.appendChild(tuval);
    kap.appendChild(el("p", "foto-uretim-ayrinti", LITOFAN_DURUSTLUK));
    S.alanLitofan.appendChild(kap);
    guncelleS1Buton();
  }
  // "Siparişe geç": gri haritayı gönder, dönen iş numarasıyla ödeme adımına geç.
  function litofanGonder() {
    if (!S.litofanHarita) { adimKoy("S1", "Önce fotoğrafını seç; önizleme çizilsin.", true); return; }
    if (!S.hakOnay) { adimKoy("S1", "Fotoğraf hakkı onayını işaretlemelisin.", true); return; }
    if (!S.captchaToken1) { adimKoy("S1", "Lütfen doğrulama kutusunu işaretle.", true); return; }
    if (!S.tur || !S.olcu) { adimKoy("S1", "Ölçü seçmelisin.", true); return; }
    var onizleme = S.litofanOnizleme;
    var govde = {
      tur: S.tur,
      olcu_mm: S.olcu,
      gorsel: S.litofanHarita,
      hak_onay: true,
      onay_surum: F.onay_surum,
      turnstile_token: S.captchaToken1
    };
    if (Object.keys(formSemasi()).length) govde.parametreler = parametreGovde();
    jsonPost(LITOFAN_URL, govde, function (ok, kod, veri) {
      turnsSifirla(S.alanCap1);
      if (kod === 200 && veri && veri.is) {
        S.is = veri.is;
        S.gorsel = onizleme;
        S.gecerlilik = veri.gecerlilik_bitis || null;
        S.adet = 1;
        ssIsKaydet();
        adimKoy("S3");
        return;
      }
      var h = veri && veri.hata;
      var m = h === "onizleme-siniri" ? "Bugünkü önizleme hakkın doldu; yarın yeniden deneyebilirsin."
        : (h === "gorsel-gecersiz" ? "Bu fotoğraftan litofan haritası çıkarılamadı; başka bir fotoğraf dene."
        : (h === "bot-dogrulama" ? "Doğrulama tamamlanamadı; kutuyu yeniden işaretle."
        : (h === "onay-surumu-eski" ? "Onay metni güncellendi; sayfayı yenileyip yeniden dene."
        : "Şu an sipariş başlatılamıyor, biraz sonra yeniden dene.")));
      adimKoy("S1", m, true);
    });
  }

  function cizAna(bolum) {
    while (bolum.firstChild) bolum.removeChild(bolum.firstChild);
    var ic = el("div", "foto-uretim-icerik");

    ek(ic, el("h2", "foto-uretim-baslik", "Fotoğrafından özel üretim"));
    ek(ic, el("p", "foto-uretim-alt",
      "Fotoğrafını yükle, ölçüsünü seç, önizlemeyi gör; beğenirsen sipariş ver."));

    var durust = el("div", "foto-uretim-durustluk");
    S.durustP = el("p", null, "");
    durust.appendChild(S.durustP);
    durustlukGuncelle();
    ic.appendChild(durust);

    /* ornekler — /foto/acik gelince yalniz ACIK turlerinki yeniden cizilir (ornekCiz) */
    var ornekBlok = el("div", "foto-uretim-blok");
    S.ornekBlok = ornekBlok;
    ornekCiz(ornekBlok, null);
    ic.appendChild(ornekBlok);

    /* 4 adim cubugu */
    cizAdimlar(ic);

    /* siparis alani */
    var alan = el("div", "foto-uretim-alani");
    alan.setAttribute("aria-live", "polite");
    S.alan = alan;
    ic.appendChild(alan);

    bolum.appendChild(ic);
  }

  /* ornekler — kanitina gore (baski: gercek fotograf · render: onizleme + uretim dosyasi).
     acikKodlar: /foto/acik turleri; null = henuz bilinmiyor/kapali (gecerli tum ornekler). */
  function ornekCiz(ornekBlok, acikKodlar) {
    while (ornekBlok.firstChild) ornekBlok.removeChild(ornekBlok.firstChild);
    var liste = [];
    for (var i = 0; i < F.turler.length && liste.length < 4; i++) {
      var t = F.turler[i];
      if (F.ornekSayisi(t.kod) === 0) continue;
      if (acikKodlar && acikKodlar.indexOf(t.kod) < 0) continue;
      for (var j = 0; j < F.ornekler.length && liste.length < 4; j++) {
        var o = F.ornekler[j];
        // Render ornegi turun dürüstlük cümlesi (ornek_notu) olmadan CIZILMEZ (fail-closed).
        if (o && o.tur === t.kod && F.ornekGecerli(o) && (F.ornekKaniti(o) !== "render" || t.ornek_notu)) {
          liste.push({ tur: t, ornek: o, kanit: F.ornekKaniti(o) });
        }
      }
    }
    var renderSay = 0;
    for (var r = 0; r < liste.length; r++) { if (liste[r].kanit === "render") renderSay++; }
    // Baslik kanittan: hepsi basilmis urunse "Gerçek örnekler"; render varsa render oldugu yazar.
    ornekBlok.appendChild(el("h3", "foto-uretim-blok-baslik",
      !liste.length || renderSay === 0 ? "Gerçek örnekler"
        : (renderSay === liste.length ? "Örnekler (önizleme/render)" : "Örnekler")));
    function gorsel(src, alt) {
      var img = el("img", "foto-uretim-ornek-gorsel");
      img.src = src; img.alt = alt;
      img.width = 300; img.height = 300;
      img.loading = "lazy"; img.decoding = "async";
      return img;
    }
    if (!liste.length) {
      ornekBlok.appendChild(el("p", "foto-uretim-ayrinti", "Henüz gerçek örnek yayınlanmadı."));
    } else {
      for (var k = 0; k < liste.length; k++) {
        var it = liste[k];
        var grup = el("div", "foto-uretim-ornek-grup");
        grup.setAttribute("data-kanit", it.kanit);
        var satir = el("div", "foto-uretim-ornek-gorseller");
        if (it.kanit === "render") {
          // Ozgun fotograf yayinlanmaz: onizleme + uretim dosyasinin render'i (ayni gorselse TEK kez).
          if (it.ornek.onizleme !== it.ornek.render) {
            satir.appendChild(gorsel(it.ornek.onizleme, it.tur.ad + " önizleme"));
          }
          satir.appendChild(gorsel(it.ornek.render, it.tur.ad + " üretim dosyası render"));
        } else {
          satir.appendChild(gorsel(it.ornek.foto, it.tur.ad + " fotoğraf"));
          satir.appendChild(gorsel(it.ornek.onizleme, it.tur.ad + " önizleme"));
          satir.appendChild(gorsel(it.ornek.baski, it.tur.ad + " basılmış ürün"));
        }
        grup.appendChild(satir);
        var baslikMetni = it.tur.ad + " · " + it.ornek.olcu_mm + " mm" +
          (it.ornek.not ? " · " + it.ornek.not : "");
        grup.appendChild(el("div", "foto-uretim-ornek-baslik", baslikMetni));
        if (it.kanit === "render") {
          grup.appendChild(el("div", "foto-uretim-ornek-etiket", "önizleme/render"));
          grup.appendChild(el("p", "foto-uretim-ornek-not", it.tur.ornek_notu));
        } else {
          grup.appendChild(el("div", "foto-uretim-ornek-etiket",
            "Fotoğraf → Önizleme → Basılmış ürün (gerçek fotoğraf)"));
        }
        ornekBlok.appendChild(grup);
      }
    }
  }

  function cizAdimlar(ic) {
    var cubuk = el("div", "foto-uretim-adimlar");
    function adim(no, ad) {
      var a = el("div", "foto-uretim-adim", no + ". " + ad);
      a.setAttribute("data-no", String(no));
      cubuk.appendChild(a);
    }
    adim(1, "Fotoğraf yükle");
    cubuk.appendChild(el("span", "foto-uretim-adim-ok", "→"));
    // Tek tür sunuluyorsa tür seçimi YOK: adım yalnız ölçüdür (açık tür listesi gelince yeniden yazılır).
    adim(2, adim2Etiketi(S.acikVeri || F));
    S.adim2El = cubuk.childNodes[cubuk.childNodes.length - 1];
    cubuk.appendChild(el("span", "foto-uretim-adim-ok", "→"));
    adim(3, "Önizleme");
    cubuk.appendChild(el("span", "foto-uretim-adim-ok", "→"));
    adim(4, "Ödeme");
    S.adimCubugu = cubuk;
    ic.appendChild(cubuk);
  }

  /* ============== KAPALI ============== */
  function cizKapali() {
    if (!S.alan) return;
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);
    var kutu = el("div", "foto-uretim-blok");
    var p = el("p");
    p.appendChild(document.createTextNode(
      "Şu an fotoğraftan sipariş alınamıyor. Örnekleri inceleyebilir, sorunu "));
    var a = el("a", "foto-uretim-kapat-a", "WhatsApp'tan yaz");
    a.href = WA; a.target = "_blank"; a.rel = "noopener";
    p.appendChild(a);
    p.appendChild(document.createTextNode("abilirsin."));
    kutu.appendChild(p);
    S.alan.appendChild(kutu);
  }

  /* ============== S1 ============== */
  function cizS1() {
    if (!S.alan) return;
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);

    S.alanTur = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanTur);
    doldurS1Tur();

    S.alanOlcu = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanOlcu);
    doldurS1Olcu();

    S.alanForm = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanForm);
    doldurS1Form();

    S.alanDosya = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanDosya);
    doldurS1Dosya();

    S.alanSecim = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanSecim);
    S.alanLitofan = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanLitofan);
    S.alanOnizlemeSonra = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanOnizlemeSonra);
    doldurS1Litofan();

    S.alanOnay = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanOnay);
    doldurS1Onay();

    S.alanCap1 = el("div", "foto-uretim-captcha");
    S.alan.appendChild(S.alanCap1);
    turnsRender(S.alanCap1, function (t) {
      S.captchaToken1 = t;
      guncelleS1Buton();
    });

    S.alanNotu = el("p", "foto-uretim-ayrinti",
      "Günde en çok " + F.sinir_ziyaretci_24s + " önizleme hakkın var.");
    S.alan.appendChild(S.alanNotu);

    S.alanButon = el("div", "foto-uretim-s1-buton-sira");
    var btn = el("button", "foto-uretim-buton-birincil", "Önizleme oluştur");
    btn.type = "button";
    btn.id = "foto-onizle-buton";
    btn.disabled = true;
    btn.addEventListener("click", onizleOlustur);
    S.alanButon.appendChild(btn);
    S.alan.appendChild(S.alanButon);
    guncelleS1Buton();
  }

  function seciliTurBul() {
    if (!S.acikVeri || !S.acikVeri.turler) return null;
    for (var i = 0; i < S.acikVeri.turler.length; i++) {
      if (S.acikVeri.turler[i].kod === S.tur) return S.acikVeri.turler[i];
    }
    return null;
  }

  /* Üst dürüstlük kutusu seçili türün manifest metnini basar (tür yoksa ilk türünkini). */
  function durustlukGuncelle() {
    if (!S.durustP || !F) return;
    var t = (S.tur && F.turBul(S.tur)) || (F.turler && F.turler[0]) || null;
    S.durustP.textContent = t && t.durustluk ? t.durustluk : "";
  }

  function doldurS1Tur() {
    while (S.alanTur.firstChild) S.alanTur.removeChild(S.alanTur.firstChild);
    // TEK TÜR: seçim adımı çizilmez (radyo düğmesi 0), tür kendiliğinden seçilir.
    if (S.acikVeri.turler.length === 1) {
      S.tur = S.acikVeri.turler[0].kod;
      durustlukGuncelle();
      S.alanTur.hidden = true;
      return;
    }
    S.alanTur.hidden = false;
    S.alanTur.appendChild(el("label", "foto-uretim-form-etiket", "Tür"));
    for (var i = 0; i < S.acikVeri.turler.length; i++) {
      var t = S.acikVeri.turler[i];
      var rid = "foto-tur-" + t.kod;
      var lbl = el("label", "foto-uretim-form-secenek-inline");
      lbl.setAttribute("for", rid);
      var inp = el("input");
      inp.type = "radio"; inp.name = "foto-tur"; inp.value = t.kod; inp.id = rid;
      if (S.tur === t.kod) inp.checked = true;
      (function (kod) {
        inp.addEventListener("change", function (e) {
          if (!e.target.checked) return;
          S.tur = kod;
          durustlukGuncelle();
          var nt = null;
          for (var j = 0; j < S.acikVeri.turler.length; j++) {
            if (S.acikVeri.turler[j].kod === kod) { nt = S.acikVeri.turler[j]; break; }
          }
          S.olcu = nt && nt.olculer && nt.olculer[0] ? nt.olculer[0].mm : null;
          S.parametre = {};
          doldurS1Olcu();
          doldurS1Form();
          doldurS1Onay();
          doldurS1Litofan();
          guncelleS1Buton();
        });
      })(t.kod);
      ek(lbl, inp);
      ek(lbl, " " + t.ad);
      if (t.aciklama) ek(lbl, " — " + t.aciklama);
      S.alanTur.appendChild(lbl);
    }
  }

  function doldurS1Olcu() {
    while (S.alanOlcu.firstChild) S.alanOlcu.removeChild(S.alanOlcu.firstChild);
    var nt = seciliTurBul();
    var tekTur = S.acikVeri.turler.length === 1;
    S.alanOlcu.appendChild(el("label", "foto-uretim-form-etiket",
      tekTur && nt ? nt.ad + " — ölçü (uzun kenar)" : "Ölçü"));
    if (tekTur && nt && nt.aciklama) {
      S.alanOlcu.appendChild(el("p", "foto-uretim-ayrinti", nt.aciklama));
    }
    if (!nt || !nt.olculer || !nt.olculer.length) {
      S.alanOlcu.appendChild(el("p", "foto-uretim-ayrinti",
        "Bu tür için ölçü seçeneği yok."));
      return;
    }
    // LITOFAN: fiyatlı ölçüler üzerinde sürgü (adım = fiyat satırı).
    if (litofanSecili()) {
      var sira = 0;
      for (var x = 0; x < nt.olculer.length; x++) { if (nt.olculer[x].mm === S.olcu) sira = x; }
      S.olcu = nt.olculer[sira].mm;
      var surgu = el("input", "foto-uretim-surgu");
      surgu.type = "range"; surgu.id = "foto-olcu-surgu";
      surgu.min = "0"; surgu.max = String(nt.olculer.length - 1); surgu.step = "1"; surgu.value = String(sira);
      var yazi = el("p", "foto-uretim-ayrinti", nt.olculer[sira].mm + " mm — " + tlMetni(nt.olculer[sira].fiyat_kurus));
      surgu.addEventListener("input", function (e) {
        var o2 = nt.olculer[parseInt(e.target.value, 10)] || nt.olculer[0];
        S.olcu = o2.mm;
        yazi.textContent = o2.mm + " mm — " + tlMetni(o2.fiyat_kurus);
        guncelleS1Buton();
      });
      S.alanOlcu.appendChild(surgu);
      S.alanOlcu.appendChild(yazi);
      return;
    }
    for (var j = 0; j < nt.olculer.length; j++) {
      var o = nt.olculer[j];
      var oid = "foto-olcu-" + o.mm;
      var lbl = el("label", "foto-uretim-form-secenek-inline");
      lbl.setAttribute("for", oid);
      var inp = el("input");
      inp.type = "radio"; inp.name = "foto-olcu"; inp.value = String(o.mm); inp.id = oid;
      if (S.olcu === o.mm) inp.checked = true;
      (function (mm) {
        inp.addEventListener("change", function (e) {
          if (!e.target.checked) return;
          S.olcu = mm;
          guncelleS1Buton();
        });
      })(o.mm);
      // Radyo düğmesi etikete EKLENİR (eksikti: ölçü seçilemiyor, hep ilk ölçü gidiyordu).
      ek(lbl, inp, " ");
      ek(lbl, o.mm + " mm — " + tlMetni(o.fiyat_kurus));
      S.alanOlcu.appendChild(lbl);
    }
  }

  function doldurS1Dosya() {
    while (S.alanDosya.firstChild) S.alanDosya.removeChild(S.alanDosya.firstChild);
    S.alanDosya.appendChild(el("label", "foto-uretim-form-etiket",
      "Fotoğraf (JPEG, PNG veya WEBP — en çok 15 MB)"));
    var inp = el("input", "foto-uretim-form-secenek-girdi");
    inp.type = "file";
    inp.accept = "image/jpeg,image/png,image/webp";
    inp.id = "foto-dosya";
    inp.addEventListener("change", function (e) {
      var f = e.target.files && e.target.files[0] ? e.target.files[0] : null;
      S.dosya = f || null;
      if (litofanSecili()) { litofanOnizle(); }
      guncelleS1Buton();
    });
    S.alanDosya.appendChild(inp);
  }

  function doldurS1Onay() {
    while (S.alanOnay.firstChild) S.alanOnay.removeChild(S.alanOnay.firstChild);
    S.alanOnay.appendChild(el("label", "foto-uretim-form-etiket", "Onaylar"));

    var hakLbl = el("label", "foto-uretim-form-secenek-inline");
    hakLbl.setAttribute("for", "foto-hak");
    var hakInp = el("input");
    hakInp.type = "checkbox"; hakInp.id = "foto-hak";
    hakInp.checked = !!S.hakOnay;
    hakInp.addEventListener("change", function (e) {
      S.hakOnay = !!e.target.checked;
      guncelleS1Buton();
    });
    ek(hakLbl, hakInp);
    ek(hakLbl, " " + F.onay.hak);
    S.alanOnay.appendChild(hakLbl);

    var aktLbl = el("label", "foto-uretim-form-secenek-inline");
    aktLbl.setAttribute("for", "foto-aktarim");
    var aktInp = el("input");
    aktInp.type = "checkbox"; aktInp.id = "foto-aktarim";
    aktInp.checked = !!S.aktarimOnay;
    aktInp.addEventListener("change", function (e) {
      S.aktarimOnay = !!e.target.checked;
      guncelleS1Buton();
    });
    ek(aktLbl, aktInp);
    ek(aktLbl, " " + F.onay.aktarim);
    // Aktarım kutusu yalnız M motorlu türde (manifest): D/R türünde fotoğraf hiçbir hizmet
    // sağlayıcıya aktarılmaz, aktarım rızası istenmez.
    aktLbl.hidden = !F.aktarimGerekir(S.tur);
    S.alanOnay.appendChild(aktLbl);

    var det = el("details", "foto-uretim-aydinlatma");
    det.appendChild(el("summary", null, "Aydınlatma metni"));
    // Maddeler türün motoruna göre (manifest `kol` etiketi): D türünde aktarım maddesi GÖRÜNMEZ.
    var maddeler = F.aydinlatmaMaddeleri(S.tur);
    for (var p = 0; p < maddeler.length; p++) {
      det.appendChild(el("p", null, maddeler[p]));
    }
    var sonP = el("p");
    sonP.appendChild(document.createTextNode("Kişisel verilerinle ilgili haklar için "));
    var glnk = el("a", null, "Gizlilik Politikası");
    glnk.href = GIZLILIK_URL;
    sonP.appendChild(glnk);
    sonP.appendChild(document.createTextNode(" sayfasına bakabilirsin."));
    det.appendChild(sonP);
    S.alanOnay.appendChild(det);
  }

  function guncelleS1Buton() {
    if (!S.alanButon) return;
    var btn = S.alanButon.querySelector("button");
    if (!btn) return;
    var lit = litofanSecili();
    // Önizlemesiz D/R türünün sipariş ucu henüz yok: buton açılmaz (yanlış uca gönderim YOK).
    var sonra = onizlemeSonraSecili();
    var tam = !!S.dosya && !!S.hakOnay && (!!S.aktarimOnay || !F.aktarimGerekir(S.tur)) &&
      !!S.captchaToken1 && !!S.tur && !!S.olcu && (!lit || !!S.litofanHarita) &&
      formDogrula().ok && !sonra;
    btn.disabled = !tam;
    btn.textContent = lit || sonra ? "Siparişe geç" : "Önizleme oluştur";
  }

  /* ============== S2 ============== */
  function cizS2() {
    if (!S.alan) return;
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);
    S.alan.appendChild(el("p", null,
      "Önizlemen hazırlanıyor… (genelde 1 dakika)"));
    if (typeof S.ilerleme === "number") {
      var dis = el("div", "foto-uretim-ilerleme-dis");
      var ic = el("div", "foto-uretim-ilerleme-ic");
      var yuzde = S.ilerleme;
      if (yuzde < 0) yuzde = 0;
      if (yuzde > 100) yuzde = 100;
      ic.style.width = yuzde + "%";
      dis.appendChild(ic);
      S.alan.appendChild(dis);
    }
    var btn = el("button", "foto-uretim-buton-ikincil", "Yeniden kontrol et");
    btn.type = "button";
    btn.addEventListener("click", function () {
      if (!S.is) return;
      S.ilerleme = null;
      yoksBaslat(S.is);
      cizS2();
    });
    S.alan.appendChild(btn);
  }

  /* ============== S3 ============== */
  function cizS3() {
    if (!S.alan) return;
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);

    S.alan.appendChild(el("p", "foto-uretim-ayrinti", litofanSecili() ? LITOFAN_DURUSTLUK :
      "Önizleme — ürün bunun en çok 4 renkli kabartma yorumu olur; birebir aynısı değildir."));
    if (litofanSecili() && S.secim) {
      var secMetin = [];
      for (var sa in S.secim) {
        if (Object.prototype.hasOwnProperty.call(S.secim, sa)) secMetin.push(S.secim[sa]);
      }
      S.alan.appendChild(el("p", "foto-uretim-ayrinti", "Seçimin: " + secMetin.join(" · ")));
    }

    if (S.gorsel) {
      var img = el("img", "foto-uretim-onizleme-img");
      img.src = S.gorsel; img.alt = "Önizleme";
      img.width = 300; img.height = 300;
      img.loading = "lazy"; img.decoding = "async";
      S.alan.appendChild(img);
    }

    var nt = seciliTurBul();

    /* olcu degistirme */
    if (nt && nt.olculer && nt.olculer.length > 1) {
      var olcuG = el("div", "foto-uretim-form-grup");
      olcuG.appendChild(el("label", "foto-uretim-form-etiket", "Ölçü"));
      for (var j = 0; j < nt.olculer.length; j++) {
        var o = nt.olculer[j];
        var oid = "foto-olcu-s3-" + o.mm;
        var lbl = el("label", "foto-uretim-form-secenek-inline");
        lbl.setAttribute("for", oid);
        var inp = el("input");
        inp.type = "radio"; inp.name = "foto-olcu-s3";
        inp.value = String(o.mm); inp.id = oid;
        if (S.olcu === o.mm) inp.checked = true;
        (function (mm) {
          inp.addEventListener("change", function (e) {
            if (!e.target.checked) return;
            S.olcu = mm;
            ssIsKaydet();
            cizS3();
          });
        })(o.mm);
        ek(lbl, inp, " ");
        ek(lbl, o.mm + " mm — " + tlMetni(o.fiyat_kurus));
        olcuG.appendChild(lbl);
      }
      S.alan.appendChild(olcuG);
    }

    /* adet */
    var adetG = el("div", "foto-uretim-form-grup");
    adetG.appendChild(el("label", "foto-uretim-form-etiket", "Adet (1-5)"));
    var adetInp = el("input", "foto-uretim-form-secenek-girdi");
    adetInp.type = "number";
    adetInp.min = String(MIN_ADET);
    adetInp.max = String(MAKS_ADET);
    adetInp.step = "1";
    adetInp.value = String(S.adet);
    adetInp.id = "foto-adet";
    adetInp.addEventListener("change", function (e) {
      var n = parseInt(e.target.value, 10);
      if (!isFinite(n) || n < MIN_ADET || n > MAKS_ADET) {
        e.target.value = String(S.adet); return;
      }
      S.adet = n;
      cizS3();
    });
    adetG.appendChild(adetInp);
    S.alan.appendChild(adetG);

    /* ozet */
    var fiyat = null;
    if (nt && nt.olculer) {
      for (var k = 0; k < nt.olculer.length; k++) {
        if (nt.olculer[k].mm === S.olcu) { fiyat = nt.olculer[k].fiyat_kurus; break; }
      }
    }
    if (fiyat != null) {
      var urunToplam = fiyat * S.adet;
      var kargo = kargoUcreti(urunToplam);
      var genel = urunToplam + kargo;
      var ozet = el("div", "foto-uretim-ozet");
      ozet.appendChild(el("div", null, "Ürün: " + tlMetni(urunToplam)));
      ozet.appendChild(el("div", null, "Gönderim: " + tlMetni(kargo)));
      ozet.appendChild(el("div", null, "Toplam: " + tlMetni(genel)));
      S.alan.appendChild(ozet);
    }

    if (S.gecerlilik) {
      S.alan.appendChild(el("p", "foto-uretim-ayrinti",
        "Bu önizleme " + yerelSaat(S.gecerlilik) +
        " saatine kadar siparişe dönüşebilir."));
    }

    var butonG = el("div", "foto-uretim-iliskili");
    var sipBtn = el("button", "foto-uretim-buton-birincil", "Sipariş ver");
    sipBtn.type = "button";
    sipBtn.addEventListener("click", function () {
      S.ad = ""; S.tel = ""; S.eposta = ""; S.adres = "";
      S.sehir = ""; S.musteriNotu = ""; S.sozlesme = false;
      S.captchaToken2 = "";
      adimKoy("S4");
    });
    butonG.appendChild(sipBtn);
    var baskaBtn = el("button", "foto-uretim-buton-ikincil", "Başka fotoğraf dene");
    baskaBtn.type = "button";
    baskaBtn.style.marginTop = "0";
    baskaBtn.addEventListener("click", function () {
      yoksDurdur();
      ssIsSil();
      S.dosya = null;
      S.hakOnay = false;
      S.aktarimOnay = false;
      S.gorsel = null;
      S.gecerlilik = null;
      S.adet = 1;
      adimKoy("S1");
    });
    butonG.appendChild(baskaBtn);
    S.alan.appendChild(butonG);
  }

  /* ============== S4 ============== */
  function cizS4() {
    if (!S.alan) return;
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);

    S.alanAd = el("div", "foto-uretim-form-grup");
    S.alanAd.appendChild(el("label", "foto-uretim-form-etiket", "Ad soyad"));
    var adInp = el("input", "foto-uretim-form-secenek-girdi");
    adInp.type = "text"; adInp.id = "foto-ad";
    adInp.value = S.ad || "";
    adInp.maxLength = 120;
    adInp.addEventListener("input", function (e) { S.ad = e.target.value; guncelleS4Buton(); });
    S.alanAd.appendChild(adInp);
    S.alan.appendChild(S.alanAd);

    S.alanTel = el("div", "foto-uretim-form-grup");
    S.alanTel.appendChild(el("label", "foto-uretim-form-etiket", "Telefon"));
    var telInp = el("input", "foto-uretim-form-secenek-girdi");
    telInp.type = "tel"; telInp.id = "foto-tel";
    telInp.value = S.tel || "";
    telInp.maxLength = 13;
    telInp.inputMode = "tel";
    telInp.addEventListener("input", function (e) { S.tel = e.target.value; guncelleS4Buton(); });
    S.alanTel.appendChild(telInp);
    S.alan.appendChild(S.alanTel);

    S.alanEposta = el("div", "foto-uretim-form-grup");
    S.alanEposta.appendChild(el("label", "foto-uretim-form-etiket", "E-posta"));
    var epInp = el("input", "foto-uretim-form-secenek-girdi");
    epInp.type = "email"; epInp.id = "foto-eposta";
    epInp.value = S.eposta || "";
    epInp.maxLength = 200;
    epInp.inputMode = "email";
    epInp.addEventListener("input", function (e) { S.eposta = e.target.value; guncelleS4Buton(); });
    S.alanEposta.appendChild(epInp);
    S.alan.appendChild(S.alanEposta);

    S.alanAdres = el("div", "foto-uretim-form-grup");
    S.alanAdres.appendChild(el("label", "foto-uretim-form-etiket", "Açık adres"));
    var adrInp = el("textarea", "foto-uretim-form-secenek-girdi");
    adrInp.id = "foto-adres";
    adrInp.value = S.adres || "";
    adrInp.maxLength = 500;
    adrInp.rows = 3;
    adrInp.addEventListener("input", function (e) { S.adres = e.target.value; guncelleS4Buton(); });
    S.alanAdres.appendChild(adrInp);
    S.alan.appendChild(S.alanAdres);

    S.alanSehir = el("div", "foto-uretim-form-grup");
    S.alanSehir.appendChild(el("label", "foto-uretim-form-etiket", "Şehir"));
    var sehInp = el("input", "foto-uretim-form-secenek-girdi");
    sehInp.type = "text"; sehInp.id = "foto-sehir";
    sehInp.value = S.sehir || "";
    sehInp.maxLength = 60;
    sehInp.addEventListener("input", function (e) { S.sehir = e.target.value; guncelleS4Buton(); });
    S.alanSehir.appendChild(sehInp);
    S.alan.appendChild(S.alanSehir);

    S.alanNotM = el("div", "foto-uretim-form-grup");
    S.alanNotM.appendChild(el("label", "foto-uretim-form-etiket",
      "Not (en çok 500 karakter)"));
    var notInp = el("textarea", "foto-uretim-form-secenek-girdi");
    notInp.id = "foto-not";
    notInp.value = S.musteriNotu || "";
    notInp.maxLength = 500;
    notInp.rows = 3;
    notInp.addEventListener("input", function (e) {
      if (e.target.value.length > 500) e.target.value = e.target.value.slice(0, 500);
      S.musteriNotu = e.target.value;
    });
    S.alanNotM.appendChild(notInp);
    S.alan.appendChild(S.alanNotM);

    var sozG = el("div", "foto-uretim-form-grup");
    var sozLbl = el("label", "foto-uretim-form-secenek-inline");
    sozLbl.setAttribute("for", "foto-sozlesme");
    var sozInp = el("input");
    sozInp.type = "checkbox"; sozInp.id = "foto-sozlesme";
    sozInp.checked = !!S.sozlesme;
    sozInp.addEventListener("change", function (e) {
      S.sozlesme = !!e.target.checked;
      guncelleS4Buton();
    });
    ek(sozLbl, sozInp);
    ek(sozLbl, " ");
    var a1 = el("a", null, "Ön Bilgilendirme Formu");
    a1.href = TESLIMAT_URL; a1.target = "_blank"; a1.rel = "noopener";
    var a2 = el("a", null, "Mesafeli Satış Sözleşmesi");
    a2.href = MESAFELI_URL; a2.target = "_blank"; a2.rel = "noopener";
    ek(sozLbl, a1);
    ek(sozLbl, "'nu ve ");
    ek(sozLbl, a2);
    ek(sozLbl, "'ni okudum, onaylıyorum.");
    sozG.appendChild(sozLbl);
    S.alan.appendChild(sozG);

    S.alanCap2 = el("div", "foto-uretim-captcha");
    S.alan.appendChild(S.alanCap2);
    turnsRender(S.alanCap2, function (t) {
      S.captchaToken2 = t;
      guncelleS4Buton();
    });

    var odeG = el("div", "foto-uretim-s1-buton-sira");
    var btn = el("button", "foto-uretim-buton-birincil", "Kartla öde");
    btn.type = "button";
    btn.id = "foto-kartla-ode";
    btn.disabled = true;
    btn.addEventListener("click", siparisVer);
    odeG.appendChild(btn);
    S.alan.appendChild(odeG);

    S.alan.appendChild(el("p", "foto-uretim-ayrinti",
      "Kart bilgilerin iyzico'nun güvenli sayfasında alınır."));
    guncelleS4Buton();
  }

  function guncelleS4Buton() {
    var btn = document.getElementById("foto-kartla-ode");
    if (!btn) return;
    var ad = S.ad || "";
    var tel = (S.tel || "").replace(rakDisi, "");
    var eposta = S.eposta || "";
    var adres = S.adres || "";
    var sehir = S.sehir || "";
    var tam = ad.length >= 3 && tel.length >= 10 &&
      epostaKalibi.test(eposta) && adres.length >= 10 &&
      sehir.length >= 2 && !!S.sozlesme && !!S.captchaToken2;
    btn.disabled = !tam;
  }

  /* ============== ADIM GECISI ============== */
  function adimKoy(adim, bildirim, hata) {
    S.adim = adim;
    if (bildirim != null) {
      S.bildirim = bildirim;
      S.bildirimHata = !!hata;
    } else {
      S.bildirim = "";
      S.bildirimHata = false;
    }
    var no = 1;
    if (adim === "S1") no = 2;
    else if (adim === "S2" || adim === "S3") no = 3;
    else if (adim === "S4") no = 4;
    adimGoster(no);

    if (adim === "kapali") cizKapali();
    else if (adim === "S1") cizS1();
    else if (adim === "S2") cizS2();
    else if (adim === "S3") cizS3();
    else if (adim === "S4") cizS4();
    durumCubuguGoster();
  }

  /* ============== /acik ============== */
  function acikYukle() {
    jsonGetir(ACIK_URL, function (ok, kod, veri) {
      if (!ok || !veri) { adimKoy("kapali"); return; }
      if (veri.acik !== true || !veri.turler || !veri.turler.length) {
        adimKoy("kapali");
        return;
      }
      S.acikVeri = veri;
      if (S.adim2El) S.adim2El.textContent = "2. " + adim2Etiketi(veri);
      // Açık olmayan türün örneği ÇİZİLMEZ (/foto/acik tür listesi süzer).
      if (S.ornekBlok) ornekCiz(S.ornekBlok, veri.turler.map(function (x) { return x.kod; }));
      var kayit = ssIsOku();
      if (kayit) {
        S.is = kayit.is;
        S.tur = kayit.tur || S.tur || (veri.turler[0] ? veri.turler[0].kod : null);
        S.olcu = kayit.olcu || null;
        if (kayit.secim && typeof kayit.secim === "object") S.secim = kayit.secim;
        durumSorgula(kayit.is, true);
        return;
      }
      if (!S.tur && veri.turler[0]) S.tur = veri.turler[0].kod;
      if (S.tur) {
        var nt = null;
        for (var i = 0; i < veri.turler.length; i++) {
          if (veri.turler[i].kod === S.tur) { nt = veri.turler[i]; break; }
        }
        if (!S.olcu && nt && nt.olculer && nt.olculer[0]) {
          S.olcu = nt.olculer[0].mm;
        }
      }
      adimKoy("S1");
    });
  }

  /* ============== /durum ============== */
  function durumSorgula(isNo, ilk) {
    jsonGetir(DURUM_URL + "?is=" + encodeURIComponent(isNo),
      function (ok, kod, veri) {
        if (!ok || !veri) {
          if (ilk) { adimKoy("S1"); }
          return;
        }
        var a = veri.asama;
        if (a === "hazir") {
          S.is = isNo;
          S.gorsel = veri.gorsel || S.gorsel;
          if (typeof veri.olcu_mm === "number") S.olcu = veri.olcu_mm;
          if (veri.tur) S.tur = veri.tur;
          S.gecerlilik = veri.gecerlilik_bitis || S.gecerlilik;
          S.adet = 1;
          yoksDurdur();
          ssIsKaydet();
          adimKoy("S3");
          return;
        }
        if (a === "basarisiz") {
          yoksDurdur();
          ssIsSil();
          var m = veri.hata === "gorsel-uygun-degil"
            ? "Bu fotoğraftan önizleme üretilemedi. Konusu net, tek kişi/hayvan/araç olan başka bir fotoğraf dene."
            : "Önizleme üretilemedi; başka bir fotoğrafla dene.";
          adimKoy("S1", m, true);
          return;
        }
        if (a === "suresi-doldu") {
          yoksDurdur();
          ssIsSil();
          adimKoy("S1", "Önizlemenin süresi doldu; yeni önizleme oluştur.", true);
          return;
        }
        if (ilk) {
          ssIsKaydet();
          S.ilerleme = typeof veri.ilerleme === "number" ? veri.ilerleme : null;
          adimKoy("S2");
        } else {
          S.ilerleme = typeof veri.ilerleme === "number" ? veri.ilerleme : null;
          cizS2();
        }
      });
  }
  function yoksBaslat(isNo) {
    yoksDurdur();
    S.yoksSayac = 0;
    S.yoksIs = setInterval(function () {
      S.yoksSayac++;
      if (S.yoksSayac >= YOKLAMA_TAVAN) {
        yoksDurdur();
        S.ilerleme = null;
        cizS2();
        S.bildirim = "Önizleme hazırlanması beklenenden uzun sürdü.";
        S.bildirimHata = true;
        durumCubuguGoster();
        return;
      }
      durumSorgula(isNo, false);
    }, YOKLAMA_MS);
  }

  /* ============== /onizleme ============== */
  function onizleOlustur() {
    if (litofanSecili()) { litofanGonder(); return; }
    if (!S.dosya) { adimKoy("S1", "Lütfen fotoğrafını seç.", true); return; }
    if (S.dosya.size > MAKS_DOSYA_BAYT) {
      adimKoy("S1", "Fotoğraf 15 MB'dan büyük olamaz.", true);
      return;
    }
    if (!S.hakOnay || !S.aktarimOnay) {
      adimKoy("S1", "Her iki onayı da işaretlemelisin.", true);
      return;
    }
    if (!S.captchaToken1) {
      adimKoy("S1", "Lütfen doğrulama kutusunu işaretle.", true);
      return;
    }
    if (!S.tur || !S.olcu) {
      adimKoy("S1", "Tür ve ölçü seçmelisin.", true);
      return;
    }
    adimKoy("S2", "Fotoğrafın yükleniyor…", false);
    kucultGorsel(S.dosya, function (err, dataUrl) {
      if (err || !dataUrl) {
        turnsSifirla(S.alanCap1);
        adimKoy("S1", "Fotoğraf okunamadı (JPEG, PNG ya da WEBP).", true);
        return;
      }
      var govde = {
        tur: S.tur,
        olcu_mm: S.olcu,
        gorsel: dataUrl,
        hak_onay: true,
        aktarim_onay: true,
        onay_surum: F.onay_surum,
        turnstile_token: S.captchaToken1
      };
      if (Object.keys(formSemasi()).length) govde.parametreler = parametreGovde();
      jsonPost(ONIZLEME_URL, govde, function (ok, kod, veri) {
        turnsSifirla(S.alanCap1);
        if (!ok || !veri) {
          adimKoy("S1", "Şu an önizleme üretilemiyor, biraz sonra yeniden dene.", true);
          return;
        }
        if (kod === 200 && veri.is) {
          S.is = veri.is;
          ssIsKaydet();
          S.ilerleme = null;
          adimKoy("S2");
          yoksBaslat(S.is);
          return;
        }
        if (kod === 429 && veri.hata === "onizleme-siniri") {
          var sinir = typeof veri.sinir === "number" ? veri.sinir : F.sinir_ziyaretci_24s;
          adimKoy("S1",
            "Bugünkü önizleme hakkın doldu (günde " + sinir + "). Yarın yeniden deneyebilirsin.",
            true);
          return;
        }
        if (kod === 403) {
          adimKoy("S1", "Doğrulama tamamlanamadı, kutucuğu yeniden işaretleyip dene.", true);
          return;
        }
        if (kod === 422) {
          adimKoy("S1",
            "Bu fotoğraftan önizleme üretilemedi. Konusu net, tek kişi/hayvan/araç olan başka bir fotoğraf dene.",
            true);
          return;
        }
        if (kod === 400 && veri.hata === "gorsel-gecersiz") {
          adimKoy("S1", "Fotoğraf okunamadı (JPEG, PNG ya da WEBP).", true);
          return;
        }
        if (kod === 409) {
          adimKoy("S1", "Metin güncellendi, sayfayı yenile.", true);
          return;
        }
        adimKoy("S1", "Şu an önizleme üretilemiyor, biraz sonra yeniden dene.", true);
      });
    });
  }

  /* ============== /baslat ============== */
  function siparisVer() {
    if (!S.is || !S.olcu || S.adet < MIN_ADET || S.adet > MAKS_ADET) {
      adimKoy("S3", "Adet 1-5 arasında olmalı.", true); return;
    }
    if (!S.captchaToken2) {
      adimKoy("S4", "Lütfen doğrulama kutusunu işaretle.", true); return;
    }
    var ad = (S.ad || "").trim();
    var tel = (S.tel || "").replace(rakDisi, "");
    var eposta = (S.eposta || "").trim();
    var adres = (S.adres || "").trim();
    var sehir = (S.sehir || "").trim();
    var notu = (S.musteriNotu || "").trim();
    if (ad.length < 3) { adimKoy("S4", "Adını yaz.", true); return; }
    if (tel.length < 10 || tel.length > 13) { adimKoy("S4", "Telefon numaranı yaz.", true); return; }
    if (!epostaKalibi.test(eposta)) { adimKoy("S4", "E-posta adresini yaz.", true); return; }
    if (adres.length < 10) { adimKoy("S4", "Açık adresini yaz.", true); return; }
    if (sehir.length < 2) { adimKoy("S4", "Şehir yaz.", true); return; }
    if (!S.sozlesme) { adimKoy("S4", "Sözleşmeyi onaylamalısın.", true); return; }
    var atif = (typeof kok.pruvoAtifTopla === "function") ? kok.pruvoAtifTopla() : {};
    var govde = {
      sepet: [litofanSecili() && S.secim
        ? { foto_is: S.is, olcu_mm: S.olcu, adet: S.adet, secim: S.secim }
        : { foto_is: S.is, olcu_mm: S.olcu, adet: S.adet }],
      musteri: { ad: ad, tel: tel, eposta: eposta, adres: adres, sehir: sehir },
      musteri_notu: notu,
      sozlesme_onay: true,
      odeme: "kart",
      turnstile_token: S.captchaToken2,
      atif: atif
    };
    jsonPost(BASLAT_URL, govde, function (ok, kod, veri) {
      turnsSifirla(S.alanCap2);
      if (kod === 200 && veri && veri.url) {
        try { sessionStorage.setItem(SS_SIPARIS, veri.no || ""); } catch (e) { }
        ssIsSil();
        kok.location.href = veri.url;
        return;
      }
      if (kod === 400 && veri && veri.hata === "foto-onizleme-suresi-doldu") {
        ssIsSil();
        adimKoy("S1", "Önizlemenin süresi doldu; yeni önizleme oluştur.", true);
        return;
      }
      if (kod === 400 && veri) {
        var h = veri.hata || "";
        if (h === "musteri-ad") { adimKoy("S4", "Adını yaz.", true); return; }
        if (h === "musteri-tel") { adimKoy("S4", "Telefon numaranı yaz.", true); return; }
        if (h === "musteri-eposta") { adimKoy("S4", "E-posta adresini yaz.", true); return; }
        if (h === "musteri-adres") { adimKoy("S4", "Açık adresini yaz.", true); return; }
        if (h === "musteri-sehir") { adimKoy("S4", "Şehir yaz.", true); return; }
      }
      adimKoy("S4", "Ödeme başlatılamadı; biraz sonra dene ya da WhatsApp'tan yaz.", true);
    });
  }

  /* ============== BASLANGIC ============== */
  function basla() {
    if (!F || !F.turler || !F.turler.length) return;
    var ornekVar = false;
    for (var i = 0; i < F.turler.length; i++) {
      if (F.ornekSayisi(F.turler[i].kod) > 0) { ornekVar = true; break; }
    }
    if (!ornekVar) return;
    if (!SECENEK || typeof SECENEK.kargoKurus !== "function" ||
        typeof SECENEK.kurusMetni !== "function") return;
    var bolum = document.getElementById(ANA_BOLUM_ID);
    if (!bolum) return;
    stilEnjeket();
    cizAna(bolum);
    bolum.removeAttribute("hidden");
    cizKapali();
    adimGoster(1);

    if (typeof IntersectionObserver !== "undefined") {
      var io = new IntersectionObserver(function (entries) {
        for (var j = 0; j < entries.length; j++) {
          if (entries[j].isIntersecting) { acikYukle(); io.disconnect(); break; }
        }
      }, { rootMargin: "200px" });
      io.observe(bolum);
    } else {
      acikYukle();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", basla);
  } else {
    basla();
  }
})();