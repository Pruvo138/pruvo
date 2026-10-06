/* PRUVO — "fotoğrafından özel üretim" bölümünün TEK KAYNAK verisi.
 *
 * Bu dosyayı İKİ taraf okur, ikinci kopya YOKTUR:
 *   - ana sayfa bölümü (/foto-uretim.js) örnekleri, türleri ve onay metnini buradan çizer;
 *   - sipariş sunucusu (shop worker) aynı dosyayı import eder: bir türün sipariş/önizleme
 *     alabilmesi için burada en az BİR sayılan örneği olmalı ve onay metni onaylı olmalı.
 *
 * DÜRÜST BEKLENTİ KURALI (Okan, 5 Eki 2026: "müşteri abartılı hayallere kapılmasın"):
 *   - `ornekler` yalnız GERÇEK işlerdir. Her kaydın KANITI açıkça yazılır ve müşteriye
 *     kanıtıyla birlikte gösterilir (render "gerçek fotoğraf" diye SUNULMAZ).
 *   - 5 Eki kuralı: "render ya da üretilmiş baskı görseli bu listeye GİRMEZ". 7 Eki 2026'da
 *     PLAKET için Okan kararıyla değişti ("bu dosya ok · baskı yapmayacağım böyle tamam":
 *     ilk örnek plaketin üretim dosyası hatasız dilimlendi, fiziksel baskı istenmedi) →
 *     plakette `kanit: "render"` kaydı da sayılır; bölüm onu "önizleme/render" etiketiyle ve
 *     abartı cümlesiyle gösterir. Diğer türlerde kural AYNEN durur (yalnız basılmış ürün).
 *   - Sayılan örneği olmayan tür AÇILMAZ (bölümde sipariş formu o tür için çıkmaz, sunucu da
 *     o türe önizleme üretmez). Görseller R2 medya kovasında durur; buraya yalnız adres yazılır.
 *   - Render kaydında müşterinin / Okan'ın ÖZGÜN fotoğrafı YAYINLANMAZ: `foto` boş ya da yok
 *     olabilir (örnek, özgün fotoğraf yayına çıkmadan önizleme + render ile gösterilir).
 *
 * Örnek kaydı: { tur, kanit, olcu_mm, foto, onizleme, baski, render, not }
 *   tur      : turler[].kod
 *   kanit    : "baski"  = basılmış ürünün gerçek fotoğrafı (5 Eki anlamı; alan yoksa bu sayılır)
 *              "render" = önizleme + üretim dosyasının render'ı (Okan kararı 7 Eki; yalnız
 *                         `ornek_kanit_izni` "render" içeren türde sayılır)
 *              başka değer -> hiçbir türde SAYILMAZ (fail-closed)
 *   foto     : müşteri fotoğrafı (izinli/kendi fotoğrafımız) — https://media.pruvo3d.com/...
 *              (baski kanıtında ŞART; render kanıtında boş olabilir)
 *   onizleme : o fotoğraftan üretilen önizleme görseli (her kanıtta ŞART)
 *   baski    : aynı işin BASILMIŞ hâlinin gerçek fotoğrafı (baski kanıtında ŞART)
 *   render   : üretim dosyasının (3MF, ayağıyla) render görseli (render kanıtında ŞART)
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
    onay_onayli: true, // Okan onayladı 6 Eki 2026 (metin taslak-1 ile birebir; değişirse sürüm de değişir)
    onay_surum: "2026-10-05-taslak-1",
    onay: {
      hak: "Yüklediğim fotoğrafın bana ait olduğunu ya da kullanma hakkım olduğunu beyan ederim.",
      aktarim: "Fotoğrafımın önizleme ve üretim dosyasının hazırlanması için yurt dışındaki " +
        "hizmet sağlayıcıya aktarılmasına açık rıza veriyorum.",
      // Her madde { kol, metin }: kol "M" = yalniz saglayici (M) kolunda gosterilir (aktarim/
      // saglayici cumleleri); "" = her kolda. METIN DEGISMEZ, yalniz gosterim kosulu (onay_surum ayni).
      aydinlatma: [
        { kol: "M", metin: "Fotoğrafını yüklediğinde fotoğraf, önizleme görselinin ve üretim dosyasının hazırlanması " +
            "için yurt dışında bulunan bir hizmet sağlayıcıya aktarılır. Bu aktarım için açık rızan " +
            "gerekir; rıza vermezsen bu hizmeti kullanamazsın, sitenin geri kalanı etkilenmez." },
        { kol: "M", metin: "Fotoğrafın PRUVO'da saklanmaz. Hizmet sağlayıcı yüklenen fotoğrafı ve ondan üretilen " +
            "dosyaları en geç 3 gün içinde siler." },
        { kol: "", metin: "Önizleme görseli sipariş vermezsen en geç 3 gün içinde silinir; sipariş verirsen üretim " +
            "ve teslim tamamlanana kadar saklanır." },
        { kol: "", metin: "Başkasına ait fotoğraf, marka, logo ya da telifli görsel yükleme; yüklenen görselden " +
            "doğan sorumluluk yükleyene aittir." },
        { kol: "M", metin: "Önizleme, fotoğrafının stilize bir yorumudur. Ürün bu önizlemenin en çok 4 renkli " +
            "kabartma yorumu olarak üretilir; birebir aynısı değildir, küçük yazı ve ince " +
            "ayrıntılar sadeleşir." },
        { kol: "", metin: "Kişisel verilerinle ilgili haklar ve başvuru yolu için Gizlilik Politikası sayfasına bakabilirsin." }
      ]
    },

    // TÜRLER — açılışta TEK tür: kabartma PLAKET (Okan, 5 Eki 21:4x: "plaket yapalım";
    // yalnız plastik üretiyoruz — metal halka/mıknatıs gerektiren tür SUNULMAZ). Ölçü = uzun
    // kenar (mm). Ayak ayrı parça, plaketle birlikte basılıp gönderilir. Figür ikinci dilimdir.
    // Tek tür varken bölümde tür seçimi adımı GÖRÜNMEZ (fotoğraf → ölçü → önizleme → ödeme).
    // Ölçü SEÇENEKLERİ ve fiyatı burada DEĞİL: sipariş panelindeki fiyat tablosundan gelir
    // (tür × ölçü). Tabloda satırı olmayan ölçü sunulmaz.
    //
    // KATEGORİ KAYDI (6 Eki 2026) — her türün akışı bu alanlardan okunur, kodda ikinci liste YOK:
    // ŞEMA = tools/foto-uretec-sozlesmesi.md §6 (KATEGORİ MOTORU, 7 Eki 2026: kategori eklemek =
    // üreteç + bu satır; bölüm, sunucu, fiyat üreteci ve üreteç köprüsü YALNIZ bu satırı okur).
    //   girdi          : [GIRDI_TURLERI anahtarı...] — "foto-1" tek fotoğraf, "foto-1-3" 1–3 fotoğraf,
    //                    "metin", "url", "svg", "form"; "ses"/"konum"/"tarih" şemada ama YAKINDA
    //   motor          : "M" = önizleme+üretim dış hizmetle (kredi harcar; kol "saglayici");
    //                    "D" / "R" = deterministik / ölçüden üretim — önizleme tarayıcıda ya da
    //                    üreteçte, üretim dosyasını bizim üretecimiz çıkarır (kol "deterministik")
    //   uretec         : üreteç komut kimliği (D/R'de DOLU, M'de "")
    //   form           : parametre şeması { anahtar: {tip:"sayi",min,max,adim,birim} |
    //                    {tip:"secim",secenekler:[..]} | {tip:"metin",max} | {tip:"url"} }; {} = parametre yok
    //   fiyat          : { formul: "mm_x_10tl", adim_mm } — foto_fiyat satırları buradan üretilir
    //                    (tools/foto-fiyat-uret.py; fiyat_kurus = mm × 1000), elle satır YAZILMAZ
    //   olcu_mm        : {en_az, en_cok} — fiyat satırı bu aralık dışında YAZILAMAZ
    //   renk_bolgeleri : müşterinin renk seçtiği bölgeler; [] = seçim yok (plaket: önizlemenin 4 renkli yorumu)
    //   malzemeler     : bölge -> izinli filament listesi; {} = satır "PLA" (plaket)
    //   ornek_kanit_izni: türü AÇAN örnek kanıtları; listede olmayan kanıt o türde SAYILMAZ
    //                    (alan yoksa/boşsa hiçbir örnek sayılmaz — fail-closed)
    //   durustluk      : bölümün üst dürüstlük kutusu (tür bazlı, ZORUNLU; seçili türün metni basılır)
    //   ornek_notu     : render örneğinin altındaki dürüstlük cümlesi (tür bazlı; mimar kararı 7 Eki,
    //                    AYNEN). Boşsa bölüm o türün render örneğini ÇİZMEZ; yeni tür doldurmak ZORUNDA.
    // Litofan, gerçek örneği ve fiyat satırı olmadıkça AÇILMAZ (fail-closed, plaketle aynı kural).
    turler: [
      {
        kod: "plaket",
        ad: "Kabartma plaket",
        aciklama: "Fotoğrafındaki konunun kabartmalı plaketi; ayağıyla masada durur.",
        girdi: ["foto-1"],
        motor: "M",
        uretec: "",
        // Okan 6 Eki 2026: "min 60 max 300" (canli fiyat tablosu 60–300, 25 satir).
        olcu_mm: { en_az: 60, en_cok: 300 },
        renk_bolgeleri: [],
        malzemeler: {},
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
        // Okan kararı 7 Eki 2026: plaket gerçek baskı beklemeden önizleme + render ile açılır.
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Önizleme, fotoğrafının stilize bir yorumudur. Ürün en çok 4 renkle kabartma olarak üretilir — önizlemenin 4 renkli yorumu; birebir aynısı değildir, küçük yazı ve ince ayrıntılar sadeleşir.",
        ornek_notu: "Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun kabartmalı hâlidir, birebir aynısı değildir."
      },
      {
        kod: "litofan",
        ad: "Işıklı fotoğraf paneli (litofan)",
        aciklama: "Fotoğrafın ince bir panele kalınlık farkıyla işlenir; arkadan ışık gelince görünür. Ayağıyla masada durur.",
        girdi: ["foto-1"],
        motor: "D",
        uretec: "litofan_uret",
        olcu_mm: { en_az: 80, en_cok: 200 },
        renk_bolgeleri: [
          { kod: "panel", ad: "Işık geçen panel", renkler: ["Beyaz"] },
          { kod: "ayak", ad: "Ayak", renkler: ["Beyaz", "Siyah", "Gri"] }
        ],
        // ABS YOK: litofan Dekorasyon sınıfıdır (secenekler.js FILAMENT_KATEGORI_HARIC).
        malzemeler: { panel: ["PLA", "PETG"], ayak: ["PLA", "PETG", "ASA"] },
        form: {},
        fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
        // Okan kararı 7 Eki 2026 (24 kategori 1 hafta, G1 "motor + litofan canlı"): litofan da
        // render örneğiyle açılır (sentetik görselden üretilen 3MF'in arkadan ışıklı render'ı).
        ornek_kanit_izni: ["baski", "render"],
        durustluk: "Litofan tek renkli ince bir paneldir; görüntü arkadan ışık geldiğinde belirir. İnce ayrıntılar ve küçük yazılar sadeleşir.",
        ornek_notu: "Üretim dosyasının arkadan ışıkla görüntüsüdür; basılmış panel ışık geldiğinde bu görüntüyü verir, birebir aynısı değildir."
      }
    ],

    // ÖRNEKLER — boşsa bölüm görünmez. Kaynak: TeKiN'in işleri (kanıtı kayıtta yazılı).
    ornekler: [
      {
        tur: "plaket",
        kanit: "render",
        olcu_mm: 120,
        onizleme: "https://media.pruvo3d.com/foto/ornek/plaket-1-onizleme.webp",
        render: "https://media.pruvo3d.com/foto/ornek/plaket-1-render.webp",
        not: "120 mm, 4 renk, ayağıyla"
      },
      {
        tur: "litofan",
        kanit: "render",
        olcu_mm: 140,
        // Sentetik çizim (deniz + güneş + yelkenli); kişi/marka/telifli görsel YOK. Önizleme =
        // aynı render (litofanın önizlemesi tarayıcıda çizilir; örnek kartında render gösterilir).
        onizleme: "https://media.pruvo3d.com/foto/ornek/litofan-1-render.webp",
        render: "https://media.pruvo3d.com/foto/ornek/litofan-1-render.webp",
        not: "140 mm, arkadan ışıkla"
      }
    ],

    // Ziyaretçi başına 24 saatte en çok kaç önizleme (sunucu da AYNI sayıyı uygular).
    sinir_ziyaretci_24s: 3,

    // Önizleme kaç saat içinde siparişe dönüşebilir (sunucu sınırı; bölüm müşteriye söyler).
    gecerlilik_saat: 48
  };

  // Örneğin kanıtı: alan yoksa 5 Eki anlamı ("baski"); bilinmeyen değer -> "" (sayılmaz).
  VERI.ornekKaniti = function (o) {
    var k = o && o.kanit == null ? "baski" : (o && o.kanit);
    return k === "baski" || k === "render" ? k : "";
  };
  // Kayıt TÜRÜNDE sayılır mı: kanıt türün `ornek_kanit_izni`nde VE kanıtın görselleri dolu.
  // Bölüm (hangi örnek çizilir) ve sunucu (tür açık mı) AYNI fonksiyonu kullanır.
  VERI.ornekGecerli = function (o) {
    if (!o) { return false; }
    var t = VERI.turBul(o.tur);
    var k = VERI.ornekKaniti(o);
    var izin = t && Array.isArray(t.ornek_kanit_izni) ? t.ornek_kanit_izni : [];
    if (!k || izin.indexOf(k) < 0) { return false; }
    if (k === "baski") { return !!(o.foto && o.onizleme && o.baski); }
    return !!(o.onizleme && o.render);
  };
  // Bir türün sayılan örnek sayısı — bölüm ve sunucu AYNI fonksiyonu kullanır.
  VERI.ornekSayisi = function (tur) {
    var n = 0;
    for (var i = 0; i < VERI.ornekler.length; i++) {
      var o = VERI.ornekler[i];
      if (o && o.tur === tur && VERI.ornekGecerli(o)) { n++; }
    }
    return n;
  };
  VERI.turBul = function (kod) {
    for (var i = 0; i < VERI.turler.length; i++) {
      if (VERI.turler[i].kod === kod) { return VERI.turler[i]; }
    }
    return null;
  };

  // MOTOR -> akış kolu. Kol TÜRETİLİR (satırda ayrı `kol` alanı yazılmaz; ikinci kaynak yok).
  VERI.MOTOR_KOLU = { M: "saglayici", D: "deterministik", R: "deterministik" };
  // Türün akış kolu ("saglayici" | "deterministik"); bilinmeyen tür/motor -> "" (hiçbir kola girmez).
  VERI.kolu = function (kod) {
    var t = VERI.turBul(kod);
    var m = t && typeof t.motor === "string" ? t.motor : "";
    return Object.prototype.hasOwnProperty.call(VERI.MOTOR_KOLU, m) ? VERI.MOTOR_KOLU[m] : "";
  };
  // Üreteç kimliği -> tarayıcıda sipariş öncesi önizleme çizen kol (bugün yalnız litofan). Bölüm
  // ve sunucu AYNI tablo: burada OLMAYAN D/R türünün sipariş öncesi önizlemesini üreteç koşucusu
  // çıkarır (/foto/onizleme -> foto_isler 'uretec-onizleme' -> koşucu -> 'onizleme-hazir').
  VERI.TARAYICI_ONIZLEYICI = { litofan_uret: true };
  // Aydınlatma maddeleri türün motoruna göre: kol "M" maddesi yalnız M motorlu türde gösterilir.
  VERI.aydinlatmaMaddeleri = function (kod) {
    var t = VERI.turBul(kod);
    var m = t ? t.motor : "";
    return VERI.onay.aydinlatma.filter(function (x) { return !x.kol || x.kol === m; })
      .map(function (x) { return x.metin; });
  };
  // Aktarım rızası (sağlayıcıya aktarım kutusu) yalnız M motorunda istenir/gösterilir.
  VERI.aktarimGerekir = function (kod) { var t = VERI.turBul(kod); return !!t && t.motor === "M"; };

  // GİRDİ TÜRLERİ — `acik:false` = şemada tanımlı, YAKINDA (bölüm göstermez, sunucu 400; G5'te açılır).
  VERI.GIRDI_TURLERI = {
    "foto-1": { acik: true }, "foto-1-3": { acik: true, en_cok: 3 },
    metin: { acik: true }, url: { acik: true, en_cok: 512 }, svg: { acik: true, en_cok_bayt: 200 * 1024 },
    form: { acik: true }, ses: { acik: false }, konum: { acik: false }, tarih: { acik: false }
  };
  VERI.FORM_TIPLERI = { sayi: true, secim: true, metin: true, url: true, ses: false, konum: false, tarih: false };

  VERI.urlDogrula = function (s) {
    return typeof s === "string" && s.length <= VERI.GIRDI_TURLERI.url.en_cok &&
      /^https:\/\/[^\s\/?#@]+(?:[\/?#][^\s]*)?$/.test(s);
  };
  // SVG: <= 200 KB, kök <svg>; script / olay özniteliği / foreignObject / ENTITY / harici
  // referans (href, url(...) içinde "#" dışı) RED. Dönüş "" = geçerli, aksi sebep kodu.
  VERI.svgDogrula = function (s) {
    if (typeof s !== "string" || !s.length) { return "svg-bos"; }
    var bayt = typeof TextEncoder !== "undefined" ? new TextEncoder().encode(s).length : s.length * 3;
    if (bayt > VERI.GIRDI_TURLERI.svg.en_cok_bayt) { return "svg-buyuk"; }
    if (!/^\s*(<\?xml[^>]*\?>\s*)?<svg[\s>]/i.test(s)) { return "svg-degil"; }
    if (/<\s*script/i.test(s) || /\son[a-z]+\s*=/i.test(s) || /javascript:/i.test(s)) { return "svg-script"; }
    if (/<\s*foreignObject/i.test(s) || /<!ENTITY|<!DOCTYPE/i.test(s)) { return "svg-yasak-oge"; }
    if (/(?:xlink:)?href\s*=\s*["']\s*[^"'#\s]/i.test(s) || /url\(\s*["']?\s*[^"'#\s)]/i.test(s) ||
        /@import/i.test(s)) { return "svg-harici-referans"; }
    return "";
  };
  // PARAMETRELER — türün `form` şemasına karşı. Şema dışı anahtar, YAKINDA tipi, aralık/adım dışı
  // sayı, listede olmayan seçim, boş/uzun metin, geçersiz url -> {ok:false, hata}. Bölüm ve sunucu AYNI.
  VERI.parametreDogrula = function (kod, p) {
    var t = VERI.turBul(kod);
    if (!t) { return { ok: false, hata: "tur-yok" }; }
    var form = t.form && typeof t.form === "object" ? t.form : {};
    if (p === undefined || p === null) { p = {}; }
    if (typeof p !== "object" || Array.isArray(p)) { return { ok: false, hata: "parametre-bicimi" }; }
    var cikti = {};
    var anahtarlar = Object.keys(p);
    for (var i = 0; i < anahtarlar.length; i++) {
      if (!Object.prototype.hasOwnProperty.call(form, anahtarlar[i])) { return { ok: false, hata: "sema-disi-parametre" }; }
    }
    var alanlar = Object.keys(form);
    for (var j = 0; j < alanlar.length; j++) {
      var a = alanlar[j], sema = form[a] || {}, v = p[a];
      if (VERI.FORM_TIPLERI[sema.tip] !== true) { return { ok: false, hata: "parametre-yakinda" }; }
      if (sema.tip === "sayi") {
        if (typeof v !== "number" || !isFinite(v) || v < sema.min || v > sema.max) { return { ok: false, hata: "parametre-aralik" }; }
        var adim = sema.adim > 0 ? sema.adim : 1;
        var k = (v - sema.min) / adim;
        if (Math.abs(k - Math.round(k)) > 1e-9) { return { ok: false, hata: "parametre-adim" }; }
      } else if (sema.tip === "secim") {
        if (!Array.isArray(sema.secenekler) || sema.secenekler.indexOf(v) < 0) { return { ok: false, hata: "parametre-secim" }; }
      } else if (sema.tip === "metin") {
        if (typeof v !== "string" || !v.trim() || v.length > (sema.max || 0)) { return { ok: false, hata: "parametre-metin" }; }
      } else if (sema.tip === "url") {
        if (!VERI.urlDogrula(v)) { return { ok: false, hata: "parametre-url" }; }
      }
      cikti[a] = v;
    }
    return { ok: true, deger: cikti };
  };
  // Türün ölçü aralığı (mm, uzun kenar); bilinmeyen tür -> null. Bölüm ve sunucu AYNI fonksiyon.
  VERI.olcuAraligi = function (kod) {
    var t = VERI.turBul(kod);
    if (!t || !t.olcu_mm || !(t.olcu_mm.en_az > 0) || !(t.olcu_mm.en_cok >= t.olcu_mm.en_az)) { return null; }
    return { en_az: t.olcu_mm.en_az, en_cok: t.olcu_mm.en_cok };
  };

  kok.PRUVO_FOTO = VERI;
})(typeof globalThis !== "undefined" ? globalThis : this);
