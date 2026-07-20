(function () {
  "use strict";

  var STORAGE_KEY = "pruvo_ref";
  var TARGET_PHONE = "905451386526";
  var TTL_MS = 90 * 24 * 60 * 60 * 1000;
  var ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  var GROUP_RE = /^[A-Z0-9]{2,4}$/;
  var SOURCE_RE = /^[A-Z]{2}$/;
  var REF_RE = /^REF:[A-Z]{2}-[A-Z0-9]{2,4}-[A-Z0-9]{4}$/;
  var LEAD_ENDPOINT = "/api/shop/ref";
  var CONSENT_KEY = "pruvo_onay_analitik";
  // Kayitta tiklama kimligi tasiyan alanlar: riza YOKKEN yazilmaz, yazilmissa SILINIR.
  var CLICK_FIELDS = ["gclid", "gbraid", "wbraid"];
  var activeRef = null;
  // Ayni sayfada ikinci tik gonderimini kes (kalici idempotent = kayittaki record.logged).
  var leadSent = false;

  function normalize(value, pattern, fallback) {
    var normalized = String(value || "").toUpperCase();
    return pattern.test(normalized) ? normalized : fallback;
  }

  function randomPart() {
    var bytes = new Uint8Array(4);
    crypto.getRandomValues(bytes);
    var result = "";
    for (var i = 0; i < bytes.length; i++) {
      result += ALPHABET.charAt(bytes[i] % ALPHABET.length);
    }
    return result;
  }

  function makeRef(source, group) {
    var candidate = "REF:" + source + "-" + group + "-" + randomPart();
    return REF_RE.test(candidate) ? candidate : null;
  }

  function readRecord(now) {
    var record = null;
    try {
      record = JSON.parse(localStorage.getItem(STORAGE_KEY));
    } catch (error) {}
    var valid = record && typeof record === "object" &&
      typeof record.ts === "number" && now - record.ts <= TTL_MS &&
      SOURCE_RE.test(record.src) && GROUP_RE.test(record.grup) &&
      REF_RE.test(record.ref) &&
      record.ref.indexOf("REF:" + record.src + "-" + record.grup + "-") === 0;
    if (valid) { return record; }
    try { localStorage.removeItem(STORAGE_KEY); } catch (error) {}
    return null;
  }

  function writeRecord(record) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(record)); } catch (error) {}
  }

  // RIZA KAPISI (KVKK): riza 'kabul' degilken kayitta duran click-id'leri null'a cek.
  // Geriye donuk temizlik (once yazilmis) + riza geri cekme, ayni tek yol. REF/grup/src
  // dokunulmaz -> WhatsApp REF akisi aynen calisir.
  function stripClickIds(record) {
    var changed = false;
    for (var i = 0; i < CLICK_FIELDS.length; i++) {
      if (record[CLICK_FIELDS[i]] !== null && record[CLICK_FIELDS[i]] !== undefined) {
        record[CLICK_FIELDS[i]] = null;
        changed = true;
      }
    }
    return changed;
  }

  function urlClickIds() {
    var params = new URLSearchParams(location.search);
    // iOS/gizlilik tiklamalari gclid yerine gbraid (app) / wbraid (web) tasir — ucunu de oku.
    return {
      gclid: params.has("gclid") ? String(params.get("gclid") || "") : null,
      gbraid: params.has("gbraid") ? String(params.get("gbraid") || "") : null,
      wbraid: params.has("wbraid") ? String(params.get("wbraid") || "") : null
    };
  }

  function initialize() {
    var params = new URLSearchParams(location.search);
    var url = urlClickIds();
    var hasClickId = !!(url.gclid || url.gbraid || url.wbraid);
    var consent = hasConsent();
    var now = Date.now();
    var record = readRecord(now);

    // Riza yoksa once VAR OLAN kayittaki click-id'leri sil (geriye donuk temizlik).
    if (record && !consent && stripClickIds(record)) { writeRecord(record); }

    if (!hasClickId && !record) { return; }
    if (record && (!hasClickId || record.gclid === url.gclid)) {
      activeRef = record.ref;
      return;
    }

    var group = normalize(params.get("pg"), GROUP_RE, "G0");
    var source = normalize(params.get("s"), SOURCE_RE, "GS");
    var ref = makeRef(source, group);
    if (!ref) { return; }
    // Click-id'ler YALNIZ riza varken kayda girer; REF her hâlükârda uretilir.
    record = { ref: ref, gclid: consent ? url.gclid : null,
               gbraid: consent ? url.gbraid : null, wbraid: consent ? url.wbraid : null,
               grup: group, src: source, ts: now };
    writeRecord(record);
    activeRef = ref;
  }

  // Riza sayfa yuklendikten SONRA verilirse (banner "Kabul Et"), URL'de hâlâ duran click-id
  // o andan itibaren saklanabilir. Yenileme beklemeden lead tikinda cagrilir.
  function captureClickIds() {
    if (!hasConsent()) { return; }
    var url = urlClickIds();
    if (!(url.gclid || url.gbraid || url.wbraid)) { return; }
    var record = readRecord(Date.now());
    if (!record || record.ref !== activeRef) { return; }
    if (record.gclid || record.gbraid || record.wbraid) { return; }
    record.gclid = url.gclid;
    record.gbraid = url.gbraid;
    record.wbraid = url.wbraid;
    writeRecord(record);
  }

  function isTarget(url) {
    var path = url.pathname.replace(/\/+$/, "");
    return (url.hostname === "wa.me" && path === "/" + TARGET_PHONE) ||
      (url.hostname === "api.whatsapp.com" && path === "/send" &&
       url.searchParams.get("phone") === TARGET_PHONE);
  }

  function enrich(anchor) {
    if (!activeRef || !anchor || !anchor.getAttribute) { return; }
    var href = anchor.getAttribute("href") || "";
    if (href.indexOf("wa.me/" + TARGET_PHONE) === -1 &&
        href.indexOf("api.whatsapp.com/send") === -1) { return; }
    var url;
    try { url = new URL(href, location.href); } catch (error) { return; }
    if (!isTarget(url)) { return; }
    var message = url.searchParams.get("text") || "";
    if (/REF:[A-Z]{2}-[A-Z0-9]{2,4}-[A-Z0-9]{4}$/.test(message)) {
      return;
    }
    url.searchParams.set("text", message ? message + "\n" + activeRef : activeRef);
    anchor.setAttribute("href", url.toString());
  }

  function enrichAll() {
    var anchors = document.querySelectorAll("a[href]");
    for (var i = 0; i < anchors.length; i++) { enrich(anchors[i]); }
  }

  function hasConsent() {
    try {
      return localStorage.getItem(CONSENT_KEY) === "kabul";
    } catch (error) {
      return false;
    }
  }

  // Lead aninda (wa.me tikinda) REF->click-id'yi sunucuya kalicilastir. Guard'lar (HEPSI
  // saglanmali): tiklanan link wa.me hedefi, activeRef set, analitik rizasi 'kabul', kayitta
  // >=1 click-id (organik gonderilmez), REF daha once loglanmamis. Fire-and-forget: yanit
  // beklenmez, hata yutulur.
  function sendLead(anchor) {
    if (leadSent || !activeRef || !anchor || !anchor.getAttribute) { return; }
    var href = anchor.getAttribute("href") || "";
    var url;
    try { url = new URL(href, location.href); } catch (error) { return; }
    if (!isTarget(url)) { return; }
    if (!hasConsent()) { return; }
    // Riza sayfa acildiktan sonra verilmis olabilir -> click-id'yi simdi yakala (riza kapili).
    captureClickIds();
    var record = readRecord(Date.now());
    if (!record || record.ref !== activeRef) { return; }
    if (!(record.gclid || record.gbraid || record.wbraid)) { return; }
    if (record.logged) { leadSent = true; return; }

    var payload = { ref: record.ref, grup: record.grup, src: record.src, ts: record.ts };
    if (record.gclid) { payload.gclid = record.gclid; }
    if (record.gbraid) { payload.gbraid = record.gbraid; }
    if (record.wbraid) { payload.wbraid = record.wbraid; }

    var ok = false;
    try {
      if (navigator && typeof navigator.sendBeacon === "function") {
        var blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
        ok = navigator.sendBeacon(LEAD_ENDPOINT, blob);
      }
    } catch (error) {
      ok = false;
    }
    if (ok) {
      leadSent = true;
      record.logged = true;
      writeRecord(record);
    }
  }

  initialize();
  window.pruvoRef = function () { return activeRef; };
  // Riza degisince (banner Kabul/Reddet, baska sekme) cagrilabilir: kabul -> URL'deki click-id
  // yakalanir, ret/geri cekme -> saklanmis click-id'ler silinir. Sayfa yenilemesi gerekmez.
  window.pruvoRefRiza = function () {
    if (hasConsent()) { captureClickIds(); return; }
    var record = readRecord(Date.now());
    if (record && stripClickIds(record)) { writeRecord(record); }
  };
  try {
    window.addEventListener("storage", function (event) {
      if (!event || !event.key || event.key === CONSENT_KEY) { window.pruvoRefRiza(); }
    });
  } catch (error) {}

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enrichAll);
  } else {
    enrichAll();
  }
  document.addEventListener("click", function (event) {
    var anchor = event.target;
    while (anchor && anchor.tagName !== "A") { anchor = anchor.parentNode; }
    enrich(anchor);
    sendLead(anchor);
  }, true);
})();
