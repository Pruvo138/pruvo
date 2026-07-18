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

function run(search, storage, hrefs, random) {
  var anchors = (hrefs || []).map(function (href) { return new Anchor(href); });
  var listeners = {};
  var document = {
    readyState: "complete",
    querySelectorAll: function () { return anchors; },
    addEventListener: function (name, handler) { listeners[name] = handler; }
  };
  var location = { search: search, href: "https://example.test/" + search };
  var window = {};
  var context = {
    window: window,
    document: document,
    localStorage: storage,
    location: location,
    crypto: random || randomSource(),
    URL: URL,
    URLSearchParams: URLSearchParams,
    Uint8Array: Uint8Array,
    Date: Date,
    JSON: JSON,
    String: String
  };
  vm.runInNewContext(MODULE, context, { filename: "attribution-ref.js" });
  return { window: window, anchors: anchors, listeners: listeners, context: context };
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

console.log("PASS " + passed + "/12");
