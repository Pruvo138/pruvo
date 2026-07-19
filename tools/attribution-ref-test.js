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
    querySelectorAll: function () { return anchors; },
    addEventListener: function (name, handler) { listeners[name] = handler; }
  };
  var location = { search: search, href: "https://example.test/" + search };
  var window = {};
  var beacons = [];
  var navigator = {
    sendBeacon: function (url, blob) {
      beacons.push({ url: url, type: blob && blob.type, body: blob && blob.parts && blob.parts[0] });
      return options.beaconFails ? false : true;
    }
  };
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
    String: String
  };
  vm.runInNewContext(MODULE, context, { filename: "attribution-ref.js" });
  return { window: window, anchors: anchors, listeners: listeners, context: context,
           beacons: beacons, storage: storage };
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
  var result = run("?gclid=X", new Storage(), []);
  assert(/^REF:GS-G0-[A-Z0-9]{4}$/.test(result.window.pruvoRef()), "G0 fallback yok");
});

scenario("grup normalize", function () {
  var result = run("?gclid=X&pg=byp", new Storage(), []);
  assert(/^REF:GS-BYP-[A-Z0-9]{4}$/.test(result.window.pruvoRef()), "kucuk grup normalize olmadi");
});

scenario("gecersiz grup", function () {
  var result = run("?gclid=X&pg=cok-uzun-slug", new Storage(), []);
  assert(/^REF:GS-G0-[A-Z0-9]{4}$/.test(result.window.pruvoRef()), "gecersiz grup G0 olmadi");
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
  assert(result.beacons.length === 1, "beacon tam 1 kez gonderilmedi: " + result.beacons.length);
  assert(result.beacons[0].url === "/api/shop/ref", "beacon ucu yanlis: " + result.beacons[0].url);
  assert(result.beacons[0].type === "application/json", "beacon content-type yanlis");
  var p = JSON.parse(result.beacons[0].body);
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
  assert(result.beacons.length === 1, "ayni sayfada tekrar gonderildi: " + result.beacons.length);
});

scenario("lead idempotent sayfalar arasi", function () {
  var storage = new Storage({ pruvo_onay_analitik: "kabul" });
  var first = run("?gclid=X&pg=NUM", storage, [WA]);
  click(first);
  assert(first.beacons.length === 1, "ilk sayfada beacon gitmedi");
  // Ayni tarayici, sonraki sayfa (organik don): record.logged kalicidir -> tekrar gonderilmez.
  var second = run("", storage, [WA]);
  click(second);
  assert(second.beacons.length === 0, "logged kayit ikinci sayfada tekrar gonderdi");
});

scenario("lead riza yok", function () {
  // Riza kapisi: pruvo_onay_analitik !== 'kabul' -> gonderilmez (varsayilan riza-kapili).
  var result = run("?gclid=X&pg=BYP", new Storage(), [WA]);
  click(result);
  assert(result.beacons.length === 0, "riza olmadan beacon gonderildi");
  var reddedilmis = run("?gclid=X&pg=BYP", new Storage({ pruvo_onay_analitik: "red" }), [WA]);
  click(reddedilmis);
  assert(reddedilmis.beacons.length === 0, "riza 'red' iken beacon gonderildi");
});

scenario("lead gbraid wbraid", function () {
  // gclid yok, gbraid+wbraid var: record'a yakalanir, payload'a ikisi girer, gclid girmez.
  var storage = new Storage({ pruvo_onay_analitik: "kabul" });
  var result = run("?gbraid=GB123&wbraid=WB456&pg=DIS", storage, [WA]);
  var kayit = JSON.parse(storage.getItem("pruvo_ref"));
  assert(kayit.gbraid === "GB123" && kayit.wbraid === "WB456", "gbraid/wbraid record'a yakalanmadi");
  assert(kayit.gclid === null, "gclid null degil");
  click(result);
  assert(result.beacons.length === 1, "gbraid/wbraid lead gonderilmedi");
  var p = JSON.parse(result.beacons[0].body);
  assert(p.gbraid === "GB123" && p.wbraid === "WB456", "payload gbraid/wbraid yanlis");
  assert(!("gclid" in p), "bos gclid alani atilmadi");
});

scenario("lead beacon basarisizsa loglanmaz", function () {
  // sendBeacon false donerse (basarisiz): record.logged yazilmaz -> sonraki firsatta tekrar denenir.
  var storage = new Storage({ pruvo_onay_analitik: "kabul" });
  var result = run("?gclid=X&pg=OTO", storage, [WA], null, { beaconFails: true });
  click(result);
  assert(result.beacons.length === 1, "basarisiz beacon denenmedi");
  var kayit = JSON.parse(storage.getItem("pruvo_ref"));
  assert(!kayit.logged, "basarisiz beacon logged=true yazdi");
});

console.log("PASS " + passed + "/19");
