"use strict";

var fs = require("fs");
var vm = require("vm");
var path = require("path");
var MODULE = fs.readFileSync(path.join(__dirname, "..", "attribution-ref.js"), "utf8");
var CANONICAL = /^REF:GS-[A-Z0-9]{2,4}-[A-Z0-9]{4}$/;
var passed = 0;

function assert(value, message) {
  if (!value) { throw new Error(message); }
}

function Storage(initial) {
  this.data = Object.assign({}, initial || {});
}
Storage.prototype.getItem = function (key) {
  return Object.prototype.hasOwnProperty.call(this.data, key) ? this.data[key] : null;
};
Storage.prototype.setItem = function (key, value) { this.data[key] = String(value); };
Storage.prototype.removeItem = function (key) { delete this.data[key]; };

function SessionStorage(initial) {
  this.data = Object.assign({}, initial || {});
}
SessionStorage.prototype.getItem = function (key) {
  return Object.prototype.hasOwnProperty.call(this.data, key) ? this.data[key] : null;
};
SessionStorage.prototype.setItem = function (key, value) { this.data[key] = String(value); };
SessionStorage.prototype.removeItem = function (key) { delete this.data[key]; };

function Anchor(href) {
  this.attrs = { href: href };
  this.tagName = "A";
  this.parentNode = null;
}
Anchor.prototype.getAttribute = function (name) { return this.attrs[name] || null; };
Anchor.prototype.setAttribute = function (name, value) { this.attrs[name] = String(value); };

function randomSource() {
  var call = 0;
  return {
    getRandomValues: function (bytes) {
      call += 1;
      for (var i = 0; i < bytes.length; i++) { bytes[i] = (call * 17 + i * 53) % 256; }
      return bytes;
    }
  };
}

// Yardimci: attribution-ref.js IKI ayri beacon yolu tasir (ref + inis). Eski senaryolar
// ref'e odaklanir; gclid iceren sorgularda inis de 1 ekledigi icin ref-only filtresi sart.
function refOnly(res) {
  return res.beacons.filter(function (b) { return b.url === "/api/shop/ref"; });
}

// navigator.sendBeacon stub: cagrilari yakalar. Blob yerine partlari saklayan sahte yapi ->
// govde (JSON dizesi) SENKRON okunabilir (gercek Blob.text() async'ti, testi zorlastirirdi).
function FakeBlob(parts, opts) {
  this.parts = parts;
  this.type = (opts && opts.type) || "";
}

function run(search, storage, hrefs, random, options) {
  options = options || {};
  var anchors = (hrefs || []).map(function (href) { return new Anchor(href); });
  var listeners = {};
  var document = {
    readyState: "complete",
    referrer: options.referrer || "",
    querySelectorAll: function () { return anchors; },
    addEventListener: function (name, handler) { listeners[name] = handler; }
  };
  var location = { search: search, href: "https://example.test/" + search };
  var gtagCalls = options.gtagCalls || [];
  var dlPushCalls = options.dlPushCalls || [];
  var spyDataLayer = {
    push: function () {
      dlPushCalls.push(Array.prototype.slice.call(arguments));
      return dlPushCalls.length;
    },
    length: 0
  };
  var window = {
    gtag: function () { gtagCalls.push(Array.prototype.slice.call(arguments)); },
    dataLayer: spyDataLayer
  };
  // I8: modulun gtag/dataLayer cagiri sayisi 0 olmali. Spy, modul kosana kadar bos
  // (testin warm-up cagrisi yok); moduldan gelen HER push/call diziye eklenir.
  var beacons = [];
  var navigator = {
    sendBeacon: function (url, data) {
      var body, type;
      if (typeof data === "string") { body = data; type = "text/plain"; }
      else if (data && data.parts) { body = data.parts[0]; type = data.type; }
      beacons.push({ url: url, type: type, body: body });
      return options.beaconFails ? false : true;
    }
  };
  var sessionStorage = options.sessionStorage || new SessionStorage();
  window.sessionStorage = sessionStorage;
  var context = {
    window: window,
    document: document,
    localStorage: storage,
    location: location,
    navigator: navigator,
    Blob: FakeBlob,
    crypto: random || randomSource(),
    URL: URL,
    URLSearchParams: URLSearchParams,
    Uint8Array: Uint8Array,
    Date: Date,
    JSON: JSON,
    String: String,
    sessionStorage: sessionStorage
  };
  vm.runInNewContext(MODULE, context, { filename: "attribution-ref.js" });
  return { window: window, anchors: anchors, listeners: listeners, context: context,
           beacons: beacons, storage: storage, sessionStorage: sessionStorage,
           gtagCalls: gtagCalls, dlPushCalls: dlPushCalls };
}

// Bir click olayini dogrudan yakalayici handler'a ver (event.target = anchor).
function click(result, index) {
  result.listeners.click({ target: result.anchors[index || 0] });
}

function message(anchor) {
  return new URL(anchor.getAttribute("href")).searchParams.get("text");
}

function scenario(name, fn) {
  try {
    fn();
    passed += 1;
  } catch (error) {
    console.error("FAIL " + name + ": " + error.message);
    process.exit(1);
  }
}

scenario("paid grup", function () {
  var result = run("?gclid=TEST&pg=BYP", new Storage(), [
    "https://wa.me/905451386526?text=Merhaba"
  ]);
  var ref = result.window.pruvoRef();
  assert(/^REF:GS-BYP-[A-Z0-9]{4}$/.test(ref), "BYP REF gecersiz");
  assert(message(result.anchors[0]).slice(-ref.length) === ref, "mesaj REF ile bitmiyor");
  var override = run("?gclid=TEST&pg=BYP&s=ab", new Storage(), []);
  assert(/^REF:AB-BYP-[A-Z0-9]{4}$/.test(override.window.pruvoRef()), "kaynak override gecersiz");
});

scenario("organik temiz", function () {
  var href = "https://wa.me/905451386526?text=Merhaba";
  var result = run("", new Storage(), [href]);
  assert(!result.window.pruvoRef(), "organikte REF var");
  assert(result.anchors[0].getAttribute("href") === href, "organik link degisti");
});

scenario("grup fallback", function () {
  // ONCUL: "G0" fallback idi; spec guncellendikten sonra paid yolda pg yoksa KAMPANYA_GRUP'a
  // duser, utm_campaign YOK ise "GY" (gclid-yalniz) olur. Eski "G0" artik URETILMEZ.
  var result = run("?gclid=X", new Storage(), []);
  assert(/^REF:GS-GY-[A-Z0-9]{4}$/.test(result.window.pruvoRef()), "G0 fallback degil, GY (gclid-yalniz) olmali");
});

scenario("grup normalize", function () {
  var result = run("?gclid=X&pg=byp", new Storage(), []);
  assert(/^REF:GS-BYP-[A-Z0-9]{4}$/.test(result.window.pruvoRef()), "kucuk grup normalize olmadi");
});

scenario("gecersiz grup", function () {
  // ONCUL: G0'a dusuyordu; gecersiz pg (GROUP_RE basarisiz) -> paidGroupFromCampaign'a duser,
  // utm_campaign YOK ise "GY". pg uzunlugunu GEYSEN bile "GY" artik beklenen sonuc.
  var result = run("?gclid=X&pg=cok-uzun-slug", new Storage(), []);
  assert(/^REF:GS-GY-[A-Z0-9]{4}$/.test(result.window.pruvoRef()), "gecersiz grup GY olmali (gclid-yalniz)");
});

// === ref-grup-17eki: paid REF grubu pg yoksa kampanyadan turesin ====================
// ONCUL: paid yolda grup yalniz pg'den turuyordu ("G0" fallback). OPAK 22:1x Figür arama
// kampanyasi son ekini ("utm_campaign=figur-arama") tasidigi halde PMax ile ayni sepete
// (REF:GS-G0-) dusuyordu. Yeni: pg varsa AYNEN, yoksa KAMPANYA_GRUP'a duser; utm_campaign
// degeri hicbir yere yazilmaz (yalniz sinif turesin). Ayni davranis Figur haric kampanya
// (UC) ve gclid-yalniz (GY) icin de.
scenario("R1 Figür arama son eki -> FIG", function () {
  var result = run("?gclid=X&utm_campaign=figur-arama", new Storage(), []);
  assert(/^REF:GS-FIG-[A-Z0-9]{4}$/.test(result.window.pruvoRef()),
    "Figur arama son eki FIG vermedi: " + result.window.pruvoRef());
});

scenario("R2 gclid-yalniz -> GY", function () {
  var result = run("?gclid=X", new Storage(), []);
  assert(/^REF:GS-GY-[A-Z0-9]{4}$/.test(result.window.pruvoRef()),
    "gclid-yalniz GY vermedi: " + result.window.pruvoRef());
});

scenario("R3 gbraid-yalniz -> GY", function () {
  var result = run("?gbraid=X", new Storage(), []);
  assert(/^REF:GS-GY-[A-Z0-9]{4}$/.test(result.window.pruvoRef()),
    "gbraid-yalniz GY vermedi: " + result.window.pruvoRef());
});

scenario("R4 bilinmeyen kampanya -> UC", function () {
  var result = run("?gclid=X&utm_campaign=baska", new Storage(), []);
  assert(/^REF:GS-UC-[A-Z0-9]{4}$/.test(result.window.pruvoRef()),
    "bilinmeyen kampanya UC vermedi: " + result.window.pruvoRef());
});

scenario("R8 yeniden-pazarlama son eki -> YP (UC'ye DUSMEZ)", function () {
  // 27 Eki 2026: inis sayaci "google yeniden-pazarlama"yi ayri sayiyordu, REF ise UC tasiyordu
  // -> siparis satirinda kampanya sinifi okunamiyordu (tools/siparis-kampanya-oku.py YP okur).
  var result = run("?gclid=X&utm_campaign=yeniden-pazarlama", new Storage(), []);
  assert(/^REF:GS-YP-[A-Z0-9]{4}$/.test(result.window.pruvoRef()),
    "yeniden-pazarlama YP vermedi: " + result.window.pruvoRef());
});

scenario("R5 pg önceliği (pg + kampanya birlikte) -> pg", function () {
  // pg=AB12 + utm_campaign=figur-arama + gclid. ONCELIK pg'de; FIG'i ezmis olmali.
  var result = run("?gclid=X&pg=AB12&utm_campaign=figur-arama", new Storage(), []);
  var ref = result.window.pruvoRef();
  assert(/^REF:GS-AB12-[A-Z0-9]{4}$/.test(ref),
    "pg onceligi FIG'i ezmeli: " + ref);
  assert(ref.indexOf("FIG") === -1, "FIG'e dusmus: " + ref);
});

scenario("R6 click-id yoksa paid REF URETILMEZ", function () {
  // utm_campaign=figur-arama var ama gclid/gbraid/wbraid yok -> paid yol SKIP, ref bos.
  // ONCUL davranis (organik/ref-yok semantics'i bozmamak icin KORUNUR; sadece paid REF
  // uretim kosulu "hasClickId" ile sinirli, kampanyanin paid kapisina BOS YOL acmaz).
  var result = run("?utm_campaign=figur-arama", new Storage(), []);
  assert(!result.window.pruvoRef(),
    "click-id yokken paid REF uretildi: " + result.window.pruvoRef());
});

scenario("R7 kayitta utm_campaign DEGERI YOK", function () {
  // utm_campaign=figur-arama olmali, ama localStorage kaydinda DEGERI yer almamali;
  // yalniz sinif (FIG) turemeli (kvkk: ham deger hicbir yere yazilmaz).
  var storage = new Storage();
  run("?gclid=X&utm_campaign=figur-arama", storage, []);
  var raw = storage.getItem("pruvo_ref");
  assert(raw !== null, "pruvo_ref kaydi yok");
  assert(raw.indexOf("figur-arama") === -1,
    "kayitta utm_campaign DEGERI sizdi: " + raw);
  var record = JSON.parse(raw);
  assert(/^REF:GS-FIG-/.test(record.ref), "kayit ref FIG degil: " + record.ref);
  var tumAnahtar = Object.keys(record).join(",");
  assert(tumAnahtar.indexOf("ampaign") === -1,
    "kayitta 'ampaign' (utm_campaign) anahtari gecti: " + tumAnahtar);
});

scenario("sayfalar arasi tekrar kullanim", function () {
  var storage = new Storage();
  var first = run("?gclid=X&pg=NUM", storage, []);
  var second = run("", storage, []);
  assert(second.window.pruvoRef() === first.window.pruvoRef(), "REF degisti");
});

scenario("yeni paid tik", function () {
  var storage = new Storage();
  var random = randomSource();
  var first = run("?gclid=X&pg=NUM", storage, [], random);
  var second = run("?gclid=Y&pg=DIS", storage, [], random);
  assert(second.window.pruvoRef() !== first.window.pruvoRef(), "REF yenilenmedi");
  assert(/^REF:GS-DIS-[A-Z0-9]{4}$/.test(second.window.pruvoRef()), "yeni grup kaydedilmedi");
});

scenario("idempotent", function () {
  var storage = new Storage();
  var result = run("?gclid=X&pg=MAK", storage, [
    "https://wa.me/905451386526?text=Merhaba"
  ]);
  vm.runInNewContext(MODULE, result.context, { filename: "attribution-ref.js" });
  var matches = message(result.anchors[0]).match(/REF:[A-Z]{2}-[A-Z0-9]{2,4}-[A-Z0-9]{4}/g) || [];
  assert(matches.length === 1, "REF birden fazla eklendi");
});

scenario("helper", function () {
  assert(CANONICAL.test(run("?gclid=X&pg=OTO", new Storage(), []).window.pruvoRef()), "paid helper bos");
  assert(!run("", new Storage(), []).window.pruvoRef(), "organik helper dolu");
});

scenario("fuzz", function () {
  var storage = new Storage();
  var random = randomSource();
  for (var i = 0; i < 200; i++) {
    var result = run("?gclid=F" + i + "&pg=G0", storage, [], random);
    assert(CANONICAL.test(result.window.pruvoRef()), "fuzz REF gecersiz: " + result.window.pruvoRef());
  }
});

scenario("api link", function () {
  var result = run("?gclid=X&pg=CON", new Storage(), [
    "https://api.whatsapp.com/send?phone=905451386526&text=Merhaba",
    "https://wa.me/905451386526"
  ]);
  assert(message(result.anchors[0]).slice(-result.window.pruvoRef().length) === result.window.pruvoRef(),
    "api link zenginlesmedi");
  assert(message(result.anchors[1]) === result.window.pruvoRef(), "text parametresi eklenmedi");
});

scenario("TTL", function () {
  var old = {
    ref: "REF:GS-BYP-AB12",
    gclid: "OLD",
    grup: "BYP",
    src: "GS",
    ts: Date.now() - 91 * 24 * 60 * 60 * 1000
  };
  var href = "https://wa.me/905451386526?text=Merhaba";
  var result = run("", new Storage({ pruvo_ref: JSON.stringify(old) }), [href]);
  assert(!result.window.pruvoRef(), "eski kayit kullanildi");
  assert(result.anchors[0].getAttribute("href") === href, "eski kayit linki degistirdi");
});

// ---- OCI #1: wa.me lead beacon (sendBeacon) ----

var WA = "https://wa.me/905451386526?text=Merhaba";

scenario("lead beacon paid", function () {
  var result = run("?gclid=TEST&pg=BYP", new Storage({ pruvo_onay_analitik: "kabul" }), [WA]);
  click(result);
  var refs = refOnly(result);
  assert(refs.length === 1, "ref beacon tam 1 kez gonderilmedi: " + refs.length);
  assert(refs[0].url === "/api/shop/ref", "beacon ucu yanlis: " + refs[0].url);
  assert(refs[0].type === "application/json", "beacon content-type yanlis");
  var p = JSON.parse(refs[0].body);
  assert(p.ref === result.window.pruvoRef(), "payload ref aktif REF degil");
  assert(p.gclid === "TEST", "payload gclid yanlis: " + p.gclid);
  assert(p.grup === "BYP" && p.src === "GS" && typeof p.ts === "number", "payload grup/src/ts eksik");
  assert(!("gbraid" in p) && !("wbraid" in p), "bos click-id alanlari atilmadi");
});

scenario("lead organik gonderilmez", function () {
  // Organik ziyaret (click-id yok) -> REF hic uretilmez -> beacon YOK (riza olsa bile).
  var result = run("", new Storage({ pruvo_onay_analitik: "kabul" }), [WA]);
  click(result);
  assert(result.beacons.length === 0, "organik tikta beacon gonderildi");
});

scenario("lead idempotent ayni sayfa", function () {
  var result = run("?gclid=X&pg=MAK", new Storage({ pruvo_onay_analitik: "kabul" }), [WA]);
  click(result);
  click(result);
  click(result);
  assert(refOnly(result).length === 1, "ayni sayfada tekrar gonderildi: " + refOnly(result).length);
});

scenario("lead idempotent sayfalar arasi", function () {
  var storage = new Storage({ pruvo_onay_analitik: "kabul" });
  var first = run("?gclid=X&pg=NUM", storage, [WA]);
  click(first);
  assert(refOnly(first).length === 1, "ilk sayfada beacon gitmedi");
  // Ayni tarayici, sonraki sayfa (organik don): record.logged kalicidir -> tekrar gonderilmez.
  var second = run("", storage, [WA]);
  click(second);
  assert(refOnly(second).length === 0, "logged kayit ikinci sayfada tekrar gonderdi");
});

scenario("lead riza yok", function () {
  // Riza kapisi: pruvo_onay_analitik !== 'kabul' -> gonderilmez (varsayilan riza-kapili).
  var result = run("?gclid=X&pg=BYP", new Storage(), [WA]);
  click(result);
  assert(refOnly(result).length === 0, "riza olmadan ref beacon gonderildi");
  var reddedilmis = run("?gclid=X&pg=BYP", new Storage({ pruvo_onay_analitik: "red" }), [WA]);
  click(reddedilmis);
  assert(refOnly(reddedilmis).length === 0, "riza 'red' iken ref beacon gonderildi");
});

scenario("lead gbraid wbraid", function () {
  // gclid yok, gbraid+wbraid var: record'a yakalanir, payload'a ikisi girer, gclid girmez.
  var storage = new Storage({ pruvo_onay_analitik: "kabul" });
  var result = run("?gbraid=GB123&wbraid=WB456&pg=DIS", storage, [WA]);
  var kayit = JSON.parse(storage.getItem("pruvo_ref"));
  assert(kayit.gbraid === "GB123" && kayit.wbraid === "WB456", "gbraid/wbraid record'a yakalanmadi");
  assert(kayit.gclid === null, "gclid null degil");
  click(result);
  var refs = refOnly(result);
  assert(refs.length === 1, "gbraid/wbraid lead gonderilmedi");
  var p = JSON.parse(refs[0].body);
  assert(p.gbraid === "GB123" && p.wbraid === "WB456", "payload gbraid/wbraid yanlis");
  assert(!("gclid" in p), "bos gclid alani atilmadi");
});

scenario("lead beacon basarisizsa loglanmaz", function () {
  // sendBeacon false donerse (basarisiz): record.logged yazilmaz -> sonraki firsatta tekrar denenir.
  var storage = new Storage({ pruvo_onay_analitik: "kabul" });
  var result = run("?gclid=X&pg=OTO", storage, [WA], null, { beaconFails: true });
  click(result);
  // OCI #2 (21 Eyl): paid kol artik SAYFA ACILISINDA da deniyor -> basarisiz acilis denemesi
  // `logged` YAZMADIGI icin lead tiki ikinci kez dener. Iki deneme, iki AYRI cagri yeri.
  // Sayi ZAYIFLATILMADI (>=1 degil, TAM 2): "basarisizsa tekrar denenir" iddiasi tam da
  // ikinci denemenin VARLIGIYLA olculur.
  // (Inis-v2 sonrasi: URL'de click-id var -> inis de gonderilebilir; sadece /api/shop/ref'e bak.)
  var refs = refOnly(result);
  assert(refs.length === 2,
         "basarisiz ref beacon iki cagri yerinden denenmedi: " + refs.length);
  var kayit = JSON.parse(storage.getItem("pruvo_ref"));
  assert(!kayit.logged, "basarisiz beacon logged=true yazdi");
});

// ---- OCI #2: SATIN ALMA YOLU — paid kalicilik wa.me tikini BEKLEMEZ ----

scenario("OCI#2 paid: wa.me'ye HIC tiklanmadan ref->gclid kalicilasir", function () {
  // Olculen ariza (ArTisT, 21 Eyl): reklamdan gelip odemeye giden ziyaretci beacon
  // atesLEMIYORdu -> reklam_ref_gclid bos -> siparisin atif.ref'i JOIN'de karsiliksiz
  // -> Ads'e OCI yuklenemiyor. Bu vaka TIK OLMADAN beacon'i olcer.
  var storage = new Storage({ pruvo_onay_analitik: "kabul" });
  var result = run("?gclid=ABC123&pg=OTO", storage, [WA]);   // click() CAGRILMIYOR
  var refs = refOnly(result);
  assert(refs.length === 1,
         "tik olmadan ref beacon gonderilmedi (OCI#2 kolu olu): " + refs.length);
  var p = JSON.parse(refs[0].body);
  assert(p.gclid === "ABC123", "payload gclid yanlis: " + p.gclid);
  assert(/^REF:GS-OTO-[A-Z0-9]{4}$/.test(p.ref), "payload REF gecersiz: " + p.ref);
  var kayit = JSON.parse(storage.getItem("pruvo_ref"));
  assert(kayit.logged === true, "basarili beacon logged yazmadi");
});

scenario("OCI#2 paid: acilis beacon'i sonra gelen wa.me tikinda TEKRARLANMAZ", function () {
  // Idempotence: acilista logged=true yazildi -> lead tiki ikinci satir URETMEZ.
  var storage = new Storage({ pruvo_onay_analitik: "kabul" });
  var result = run("?gclid=ABC123&pg=OTO", storage, [WA]);
  click(result);
  assert(refOnly(result).length === 1,
         "ayni REF icin ikinci ref beacon gonderildi: " + refOnly(result).length);
});

scenario("OCI#2 NEGATIF: riza yokken acilis beacon'i GONDERILMEZ", function () {
  // Gizlilik regresyonu kolu — OCI#2 yeni bir alan TOPLAMAZ, yalniz ZAMANI degistirir.
  var result = run("?gclid=ABC123&pg=OTO", new Storage(), [WA]);
  assert(refOnly(result).length === 0, "rizasiz acilis ref beacon gonderildi");
  var red = run("?gclid=ABC123&pg=OTO",
                new Storage({ pruvo_onay_analitik: "red" }), [WA]);
  assert(refOnly(red).length === 0, "riza 'red' iken acilis ref beacon gonderildi");
});

scenario("OCI#2 NEGATIF: ORGANIK (OG) kol acilista beacon GONDERMEZ", function () {
  // Kapsam BILEREK dar: OG'yi her acilista yazmak lead tablosunu ZIYARET LOGUNA cevirirdi.
  // OG kolu bugunku "lead ani" anlaminda KALIR — bu vaka o siniri civiler.
  var result = run("", new Storage({ pruvo_onay_analitik: "kabul" }), [WA], null,
                   { referrer: "https://www.google.com/search?q=pruvo" });
  assert(refOnly(result).length === 0,
         "organik REF acilista ref beacon gonderdi (kapsam genisledi): " + refOnly(result).length);
  click(result);
  assert(refOnly(result).length === 1, "organik lead tiki ref beacon gondermedi");
});

// ---- ORGANIK ATIF (YENI): arama motoru referrer -> src=OG ----

scenario("organik arama REF + wa.me zenginlesir", function () {
  var result = run("", new Storage(), [WA], null,
    { referrer: "https://www.google.com/search?q=pruvo" });
  var ref = result.window.pruvoRef();
  assert(/^REF:OG-G0-[A-Z0-9]{4}$/.test(ref), "organik OG REF gecersiz: " + ref);
  assert(message(result.anchors[0]).slice(-ref.length) === ref, "wa.me OG REF ile bitmedi");
});

scenario("organik arama alt-domain + tld varyanti", function () {
  var a = run("", new Storage(), [], null, { referrer: "https://google.com.tr/" });
  assert(/^REF:OG-/.test(a.window.pruvoRef() || ""), "google.com.tr OG uretmedi");
  var b = run("", new Storage(), [], null, { referrer: "https://r.search.yahoo.com/x" });
  assert(/^REF:OG-/.test(b.window.pruvoRef() || ""), "yahoo alt-domain OG uretmedi");
  var c = run("", new Storage(), [], null, { referrer: "https://duckduckgo.com/" });
  assert(/^REF:OG-/.test(c.window.pruvoRef() || ""), "duckduckgo OG uretmedi");
});

scenario("dogrudan (referrer yok) -> REF YOK", function () {
  var href = "https://wa.me/905451386526?text=Merhaba";
  var result = run("", new Storage(), [href], null, { referrer: "" });
  assert(!result.window.pruvoRef(), "dogrudan ziyarette REF uretildi");
  assert(result.anchors[0].getAttribute("href") === href, "dogrudan link degisti");
});

scenario("ic gezinme (pruvo3d.com) -> REF YOK", function () {
  var result = run("", new Storage(), [WA], null, { referrer: "https://pruvo3d.com/urun/x/" });
  assert(!result.window.pruvoRef(), "ic gezinmede REF uretildi");
});

scenario("baska site referrer -> REF YOK", function () {
  var result = run("", new Storage(), [WA], null, { referrer: "https://forum.example.com/thread" });
  assert(!result.window.pruvoRef(), "arama-disi site REF uretti");
  // "notgoogle.com" etiket-tam eslesmeye takilmamali (alt-dize degil).
  var sahte = run("", new Storage(), [WA], null, { referrer: "https://notgoogle.com/" });
  assert(!sahte.window.pruvoRef(), "notgoogle.com yanlislikla OG uretti");
});

scenario("organik arama beacon (src=OG, click-id yok)", function () {
  var result = run("", new Storage({ pruvo_onay_analitik: "kabul" }), [WA], null,
    { referrer: "https://www.google.com/search?q=pruvo" });
  click(result);
  assert(result.beacons.length === 1, "organik beacon gitmedi: " + result.beacons.length);
  assert(result.beacons[0].url === "/api/shop/ref", "beacon ucu yanlis");
  var p = JSON.parse(result.beacons[0].body);
  assert(p.ref === result.window.pruvoRef() && /^REF:OG-/.test(p.ref), "payload OG ref yanlis: " + p.ref);
  assert(p.src === "OG", "payload src OG degil: " + p.src);
  assert(!("gclid" in p) && !("gbraid" in p) && !("wbraid" in p), "organik payload click-id tasidi");
});

scenario("organik beacon rizadan bagimsiz (PII yok)", function () {
  // OG kaydi click-id/PII tasimaz -> analitik rizasi olmasa da beacon gider (organik olcum).
  var result = run("", new Storage(), [WA], null, { referrer: "https://bing.com/search?q=x" });
  click(result);
  assert(result.beacons.length === 1, "rizasiz organik beacon gitmedi: " + result.beacons.length);
  var p = JSON.parse(result.beacons[0].body);
  assert(p.src === "OG" && !("gclid" in p), "rizasiz organik payload yanlis");
});

scenario("organik OG REF sayfalar arasi surer", function () {
  var storage = new Storage();
  var first = run("", storage, [WA], null, { referrer: "https://www.google.com/" });
  var ilk = first.window.pruvoRef();
  assert(/^REF:OG-/.test(ilk || ""), "ilk sayfada OG uretilmedi");
  // Sonraki sayfa ic gezinme (pruvo referrer): yeni OG uretmez, ayni REF surer.
  var second = run("", storage, [WA], null, { referrer: "https://pruvo3d.com/" });
  assert(second.window.pruvoRef() === ilk, "OG REF sayfalar arasi degisti/silindi");
});

scenario("paid arama referrer'inda bile OG'ye donmez", function () {
  // gclid + google referrer: paid yol kazanir, src=GS (OG DEGIL) -> paid davranis birebir.
  var result = run("?gclid=X&pg=BYP", new Storage(), [], null,
    { referrer: "https://www.google.com/" });
  assert(/^REF:GS-BYP-[A-Z0-9]{4}$/.test(result.window.pruvoRef()), "paid REF OG'ye kaydi");
});

// ---- INIS-V2 (17 Eki 2026): site geneli inis beacon'i ----

var INIS_SESSION_KEY = "pruvo_inis";

function inisErisim(ss) { return ss && ss.data && ss.data[INIS_SESSION_KEY]; }

scenario("I1 utm_source'lü ilk yukleme -> beacon {s:'google', c:'figur'}", function () {
  var session = new SessionStorage();
  var result = run("?utm_source=Google&utm_campaign=figur", new Storage(), [], null,
    { sessionStorage: session });
  var inis = result.beacons.filter(function (b) { return b.url === "/api/shop/inis"; });
  assert(inis.length === 1, "inis beacon tam 1 kez gonderilmedi: " + JSON.stringify(inis));
  var p = JSON.parse(inis[0].body);
  assert(p.s === "google" && p.c === "figur", "inis payload s/c yanlis: " + JSON.stringify(p));
  assert(JSON.stringify(Object.keys(p)) === JSON.stringify(["s", "c"]),
    "gövdede fazla alan: " + JSON.stringify(Object.keys(p)));
  assert(inisErisim(session) === "1", "sessionStorage isareti konmadi");
});

scenario("I2 gclid -> {s:'google', c:'gclid'}; govdede deger YOK", function () {
  var session = new SessionStorage();
  var result = run("?gclid=ABC123xyz", new Storage(), [], null,
    { sessionStorage: session });
  var inis = result.beacons.filter(function (b) { return b.url === "/api/shop/inis"; });
  assert(inis.length === 1, "gclid icin inis beacon yok: " + JSON.stringify(inis));
  var p = JSON.parse(inis[0].body);
  assert(p.s === "google" && p.c === "gclid", "gclid payload yanlis: " + JSON.stringify(p));
  assert(inis[0].body.indexOf("ABC123xyz") === -1, "govdeye gclid DEGERI sizdi: " + inis[0].body);
});

scenario("I3 gbraid -> {s:'google', c:'gbraid'} (wbraid da benzer)", function () {
  var session = new SessionStorage();
  var result = run("?gbraid=Q1", new Storage(), [], null,
    { sessionStorage: session });
  var inis = result.beacons.filter(function (b) { return b.url === "/api/shop/inis"; });
  assert(inis.length === 1, "gbraid icin inis beacon yok");
  var p = JSON.parse(inis[0].body);
  assert(p.s === "google" && p.c === "gbraid", "gbraid payload yanlis: " + JSON.stringify(p));
  assert(inis[0].body.indexOf("Q1") === -1, "govdeye gbraid DEGERI sizdi");
});

scenario("I4 fbclid -> {s:'facebook', c:'fbclid'}; govdede F9 yok", function () {
  var session = new SessionStorage();
  var result = run("?fbclid=F9", new Storage(), [], null,
    { sessionStorage: session });
  var inis = result.beacons.filter(function (b) { return b.url === "/api/shop/inis"; });
  assert(inis.length === 1, "fbclid icin inis beacon yok");
  var p = JSON.parse(inis[0].body);
  assert(p.s === "facebook" && p.c === "fbclid", "fbclid payload yanlis: " + JSON.stringify(p));
  assert(inis[0].body.indexOf("F9") === -1, "govdeye fbclid DEGERI sizdi");
});

scenario("I5 parametresiz -> 0 inis beacon", function () {
  var session = new SessionStorage();
  var result = run("", new Storage(), [], null, { sessionStorage: session });
  var inis = result.beacons.filter(function (b) { return b.url === "/api/shop/inis"; });
  assert(inis.length === 0, "parametresiz halde inis beacon gonderildi: " + JSON.stringify(inis));
  assert(!inisErisim(session), "parametresiz halde session isareti kondu");
});

scenario("I6 ikinci yukleme ayni sessionStorage -> 0 inis beacon", function () {
  var session = new SessionStorage();
  run("?utm_source=meta&utm_campaign=akut", new Storage(), [], null,
    { sessionStorage: session });
  var once = inisErisim(session);
  assert(once === "1", "birinci yukleme sonrasi session isareti yok: " + once);
  var result = run("?utm_source=meta&utm_campaign=akut", new Storage(), [], null,
    { sessionStorage: session });
  var inis = result.beacons.filter(function (b) { return b.url === "/api/shop/inis"; });
  assert(inis.length === 0, "ikinci yuklemede de inis beacon gonderildi: " + JSON.stringify(inis));
});

scenario("I7 riza YOK iken de I2 -> 1 inis beacon (PII yok, riza bagimsiz)", function () {
  // riza YOK (storage bos) + gclid var -> inis beacon YINE gider (KVKK: PII = 0, riza gerekmez).
  var session = new SessionStorage();
  var result = run("?gclid=ABC123xyz", new Storage(), [], null,
    { sessionStorage: session });
  var inis = result.beacons.filter(function (b) { return b.url === "/api/shop/inis"; });
  assert(inis.length === 1, "rizasiz inis beacon gitmedi: " + JSON.stringify(inis));
});

scenario("I8 gtag/dataLayer cagrisi 0 (inis akisi bunlara DOKUNMAZ)", function () {
  var session = new SessionStorage();
  var result = run("?utm_source=meta&utm_campaign=akut&gclid=ABC", new Storage(), [], null,
    { sessionStorage: session });
  assert(result.gtagCalls.length === 0,
    "modul gtag cagirisi yapti: " + JSON.stringify(result.gtagCalls));
  assert(result.dlPushCalls.length === 0,
    "modul dataLayer.push cagirisi yapti: " + JSON.stringify(result.dlPushCalls));
});

// ---- MUTANT'LAR: gecici kopya uzerinde metinsel mutasyon ----

var fsMut = require("fs");
var osMut = require("os");
var pathMut = require("path");

/* Modulun gecici bir kopyasini mutate et, vm ile calistir, sonra sil. Tek ortam: /tmp. */
function mutantKos(mutantKod, search, session) {
  var dosya = pathMut.join(osMut.tmpdir(), "pruvo-attribution-mutant-" +
    Date.now() + "-" + Math.random().toString(36).slice(2, 8) + ".js");
  fsMut.writeFileSync(dosya, mutantKod, "utf8");
  try {
    var anchors = [];
    var beacons = [];
    var gtagCalls = [];
    var dlPushCalls = [];
    var dlProxy = {
      push: function () {
        dlPushCalls.push(Array.prototype.slice.call(arguments));
        return dlPushCalls.length;
      }, length: 0
    };
    var document = {
      readyState: "complete", referrer: "",
      querySelectorAll: function () { return anchors; },
      addEventListener: function () {}
    };
    var location = { search: search, href: "https://example.test/" + search };
    var window = {
      gtag: function () { gtagCalls.push(Array.prototype.slice.call(arguments)); },
      dataLayer: dlProxy
    };
    var navigator = {
      sendBeacon: function (url, data) {
        var body, type;
        if (typeof data === "string") { body = data; type = "text/plain"; }
        else if (data && data.parts) { body = data.parts[0]; type = data.type; }
        beacons.push({ url: url, type: type, body: body });
        return true;
      }
    };
    var context = {
      window: window, document: document, location: location,
      localStorage: new Storage(), navigator: navigator, Blob: FakeBlob,
      crypto: randomSource(), URL: URL, URLSearchParams: URLSearchParams,
      Uint8Array: Uint8Array, Date: Date, JSON: JSON, String: String,
      sessionStorage: session || new SessionStorage()
    };
    vm.runInNewContext(fsMut.readFileSync(dosya, "utf8"), context,
      { filename: dosya });
    return { beacons: beacons, gtagCalls: gtagCalls, dlPushCalls: dlPushCalls };
  } finally {
    try { fsMut.unlinkSync(dosya); } catch (e) {}
  }
}

function inisBekir(res) {
  return res.beacons.filter(function (b) { return b.url === "/api/shop/inis"; });
}

scenario("M1 govdeye click-id DEGERI eklenir -> I2 KIRMIZI (sizinti)", function () {
  // MUTANT: govde {s, c, gid} eklenir; gclid degeri "ABC123xyz" yine ele verir.
  var mutated = MODULE.replace(
    'JSON.stringify({ s: s, c: c })',
    'JSON.stringify({ s: s, c: c, gid: (params.get("gclid") || params.get("gbraid") ' +
      '|| params.get("wbraid") || params.get("fbclid") || "") })'
  );
  assert(mutated !== MODULE, "M1 metinsel mutasyon uygulanamadi");
  var res = mutantKos(mutated, "?gclid=ABC123xyz");
  var inis = inisBekir(res);
  assert(inis.length === 1 && inis[0].body.indexOf("ABC123xyz") !== -1,
    "M1 gclid degerini sizdirmadi; regress muaf olmus olabilir");
  // I2 KIRMIZI yakalandi: deger GEZEGENDE, davranis kabul edilebilir degil.
  // Bu vaka PASS ettigi AN mutant DEVAM ediyor demektir; testin KENDISI gecti,
  // mutant REGRESS'i I2'nin reddedilmesiyle hukmen cogu.
});

scenario("M2 riza kapisi eklenir -> I7 KIRMIZI (riza=0 iken hala gider)", function () {
  // MUTANT: inisSay() basina `if (!hasConsent()) { return; }` enjekte et.
  // hasConsent localStorage'a bakar; riza yokken 'kabul' degilse early-return.
  var mutated = MODULE.replace(
    "function inisSay() {",
    'function inisSay() { if (typeof hasConsent === "function" && !hasConsent()) { return; }'
  );
  assert(mutated !== MODULE, "M2 metinsel mutasyon uygulanamadi");
  var res = mutantKos(mutated, "?gclid=ABC123xyz");
  var inis = inisBekir(res);
  // I7 beklentisi: riza yokken de 1 inis beacon. MUTANT bunu KIRMIZI yapar (0 beacon).
  // Test gecmezse mutant yakalanmis demektir.
  assert(inis.length === 0,
    "M2 riza kapisi inis'i durdurmadi -> I7 hala GECTI; mutant algilanamadi");
});

scenario("M3 oturum isareti kalkar -> I6 KIRMIZI (ayni oturumda iki beacon)", function () {
  // MUTANT: `if (depo && depo.getItem("pruvo_inis")) { return; }` satirini sil.
  // (Iki mock'lu sessionStorage ayarliyor; ilk kosudan sonra "pruvo_inis"=1 var,
  // mutant'li kopya YINE bir beacon gonderir.)
  var mutated = MODULE.replace(
    'if (depo && depo.getItem("pruvo_inis")) { return; }', ""
  );
  assert(mutated !== MODULE, "M3 metinsel mutasyon uygulanamadi");
  var session = new SessionStorage();
  mutantKos(mutated, "?utm_source=meta&utm_campaign=akut", session);
  var res = mutantKos(mutated, "?utm_source=meta&utm_campaign=akut", session);
  var inis = inisBekir(res);
  // I6 beklentisi: ayni oturumda 2. yukleme 0 inis. MUTANT 1 uretir.
  assert(inis.length === 1,
    "M3 oturum isareti olmadan 2. beacon gondermedi -> I6 hala GECTI");
});

scenario("M4 gclid kolu silinir -> I2 KIRMIZI (gclid ile hic inis yok)", function () {
  // MUTANT: gclid|gbraid|wbraid dalini sil. ?gclid=... ile inis uretilmez.
  var mutated = MODULE.replace(
    '} else if (params.has("gclid") || params.has("gbraid") || params.has("wbraid")) {',
    '} else if (false) {'
  );
  assert(mutated !== MODULE, "M4 metinsel mutasyon uygulanamadi");
  var res = mutantKos(mutated, "?gclid=ABC123xyz");
  var inis = inisBekir(res);
  // I2 beklentisi: gclid ile 1 inis beacon. MUTANT 0 uretir.
  assert(inis.length === 0,
    "M4 gclid kolu silinmis ama inis uretiyor -> I2 KIRMIZI degil");
});

// Mutant icin run() muadili: pruvoRef() sonucunu ve storage'i da disari ver (M5-M7 icin).
function runMutant(mutated, search, storage) {
  storage = storage || new Storage();
  var anchors = [];
  var beacons = [];
  var gtagCalls = [];
  var dlPushCalls = [];
  var dlProxy = {
    push: function () {
      dlPushCalls.push(Array.prototype.slice.call(arguments));
      return dlPushCalls.length;
    }, length: 0
  };
  var document = {
    readyState: "complete", referrer: "",
    querySelectorAll: function () { return anchors; },
    addEventListener: function () {}
  };
  var location = { search: search, href: "https://example.test/" + search };
  var window = {
    gtag: function () { gtagCalls.push(Array.prototype.slice.call(arguments)); },
    dataLayer: dlProxy
  };
  var navigator = {
    sendBeacon: function (url, data) {
      var body, type;
      if (typeof data === "string") { body = data; type = "text/plain"; }
      else if (data && data.parts) { body = data.parts[0]; type = data.type; }
      beacons.push({ url: url, type: type, body: body });
      return true;
    }
  };
  var sessionStorage = new SessionStorage();
  window.sessionStorage = sessionStorage;
  var context = {
    window: window, document: document, location: location,
    localStorage: storage, navigator: navigator, Blob: FakeBlob,
    crypto: randomSource(), URL: URL, URLSearchParams: URLSearchParams,
    Uint8Array: Uint8Array, Date: Date, JSON: JSON, String: String,
    sessionStorage: sessionStorage
  };
  vm.runInNewContext(mutated, context, { filename: "attribution-ref-mutant.js" });
  return { window: window, storage: storage, beacons: beacons };
}

scenario("M5 KAMPANYA_GRUP bosaltilir -> R1 KIRMIZI (Figur arama FIG vermez)", function () {
  // MUTANT: haritayi bosalt. ?gclid=X&utm_campaign=figur-arama artik "UC" tasir, R1 FIG bekliyordu.
  var mutated = MODULE.replace(
    'KAMPANYA_GRUP = { "figur-arama": "FIG", "yeniden-pazarlama": "YP" }',
    'KAMPANYA_GRUP = {}'
  );
  assert(mutated !== MODULE, "M5 metinsel mutasyon uygulanamadi");
  var res = runMutant(mutated, "?gclid=X&utm_campaign=figur-arama");
  var ref = res.window.pruvoRef() || "";
  // Testin KENDISI gecmezse mutant yakalanmis demektir (R1 KIRMIZI oldu).
  assert(ref.indexOf("FIG") === -1,
    "M5 KAMPANYA_GRUP bos ama hala FIG uretiyor: " + ref);
});

scenario("M6 GY -> G0 doner -> R2 KIRMIZI (gclid-yalniz GY vermez)", function () {
  // MUTANT: utm_campaign YOK ise "GY" yerine "G0" don. ?gclid=X artik REF:GS-G0-... uretir,
  // R2 "GY" bekliyordu. gclid-yalniz PMax ile ayni sepete duserse ayrim yapilamaz.
  var mutated = MODULE.replace(
    'if (raw === "") { return "GY"; }',
    'if (raw === "") { return "G0"; }'
  );
  assert(mutated !== MODULE, "M6 metinsel mutasyon uygulanamadi");
  var res = runMutant(mutated, "?gclid=X");
  var ref = res.window.pruvoRef() || "";
  assert(ref.indexOf("GY") === -1,
    "M6 gclid-yalniz G0'a dondu ama test GY bekliyordu: " + ref);
});

scenario("M7 pg onceligi tersine (utm once) -> R5 KIRMIZI (pg ezilir)", function () {
  // MUTANT: pg dali kaldir. utm_campaign FIG olan her tik pg'yi ezer; R5 (pg=AB12) FIG'e dusmeli.
  var mutated = MODULE.replace(
    'var group = GROUP_RE.test(pgNormalized) ? pgNormalized : paidGroupFromCampaign(params);',
    'var group = paidGroupFromCampaign(params);'
  );
  assert(mutated !== MODULE, "M7 metinsel mutasyon uygulanamadi");
  var res = runMutant(mutated, "?gclid=X&pg=AB12&utm_campaign=figur-arama");
  var ref = res.window.pruvoRef() || "";
  // R5 AB12 bekliyordu; mutant FIG uretip AB12'yi ezmeli. Gecip gecmedigini kontrol et.
  assert(ref.indexOf("AB12") === -1 && ref.indexOf("FIG") !== -1,
    "M7 pg onceligi kalkmamis: " + ref);
});

scenario("M8 YP haritadan duser -> R8 KIRMIZI (yeniden-pazarlama UC'ye doner)", function () {
  var mutated = MODULE.replace(', "yeniden-pazarlama": "YP" }', " }");
  assert(mutated !== MODULE, "M8 metinsel mutasyon uygulanamadi");
  var res = runMutant(mutated, "?gclid=X&utm_campaign=yeniden-pazarlama");
  var ref = res.window.pruvoRef() || "";
  assert(ref.indexOf("-YP-") === -1 && ref.indexOf("-UC-") !== -1,
    "M8 YP haritadan dustu ama hala YP uretiyor: " + ref);
});

// Payda SABIT YAZILMAZ — 21 Eyl 2026'da 32 senaryo kosarken "/28" basiyordu (4 tur bayat).
// Kaynaktan sayilir: ust duzey `scenario(` cagrilari BEYAN, `passed` KOSAN. Ikisi ayrisirsa
// KIRMIZI — bir senaryo blok icine gomulup hic kosmazsa (ya da iki kez sayilirsa) burada yakalanir.
var beyanEdilen = (
  require("fs").readFileSync(__filename, "utf8").match(/^scenario\(/gm) || []
).length;
if (passed !== beyanEdilen) {
  console.error("FAIL sayac: kosan " + passed + " != kaynakta beyan edilen " + beyanEdilen);
  process.exit(1);
}
console.log("PASS " + passed + "/" + beyanEdilen);
