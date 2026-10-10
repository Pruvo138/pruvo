// FOTO CANLI GIZLI — istemci KARAR kosucusu (tools/foto-canli-gizli-kapisi.py cagirir; tek basina da kosar).
//
// Soru: YAYINDAKI foto-uretim.js, verilen `/acik` yanitiyla `#fotoUretim` bolumunu ACAR mi?
// foto-uretim.js saf karar fonksiyonu disari VERMEZ (karar acikYukle() icinde removeAttribute("hidden")),
// o yuzden KG1-3'un yolu kullanilir: veri + bolum kodu sahte DOM'da `vm` ile GERCEKTEN kosar, fetch saplanir,
// sonunda bolumun `hidden`i okunur. Sahte DOM shop/test/foto-uretim.mjs::sahteBelge ile ayni sozlesme.
//
// Kullanim: node foto-canli-gizli-karar.mjs --veri <foto-uretim-veri.js> --js <foto-uretim.js>
//             (--acik <yanit.json> [--ok 1|0] [--durum <http>] | --pozitif)
// --pozitif: /acik yaniti veri dosyasinin ILK ornekli turuyle "acik + 1 tur" kurulur (pozitif kontrol:
// kosucu bolumu ACABILIYOR mu — acamiyorsa "gizli" cevabi kordur).
// Cikti (stdout, tek satir JSON): {"gorunur": true|false, "istisna": <n>, "hata": null|"..."}; rc 0.
// Kosu kurulamazsa (dosya yok / senkron istisna) rc 2 + {"hata": "..."}.
import fs from "node:fs";
import vm from "node:vm";

function arg(ad) {
  const i = process.argv.indexOf(ad);
  return i >= 0 ? process.argv[i + 1] : null;
}
function bitir(nesne, rc) {
  process.stdout.write(JSON.stringify(nesne) + "\n");
  process.exit(rc);
}

function sahteBelge() {
  class Metin {
    constructor(t) { this.nodeType = 3; this.metin = String(t); this.parentNode = null; this.childNodes = []; }
    get textContent() { return this.metin; }
  }
  class Oge {
    constructor(etiket) {
      this.tagName = String(etiket).toUpperCase(); this.nodeType = 1; this.childNodes = []; this.parentNode = null;
      this.ozn = {}; this.className = ""; this.hidden = false; this.style = {};
      const o = this;
      this.classList = {
        contains: (c) => o.className.split(/\s+/).includes(c),
        add: (c) => { if (!o.classList.contains(c)) { o.className = (o.className + " " + c).trim(); } },
        remove: (c) => { o.className = o.className.split(/\s+/).filter((x) => x && x !== c).join(" "); },
      };
    }
    get firstChild() { return this.childNodes[0] || null; }
    appendChild(c) { if (c.parentNode) { c.parentNode.removeChild(c); } this.childNodes.push(c); c.parentNode = this; return c; }
    insertBefore(c, ref) {
      if (c.parentNode) { c.parentNode.removeChild(c); }
      const i = this.childNodes.indexOf(ref);
      this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, c); c.parentNode = this; return c;
    }
    removeChild(c) { const i = this.childNodes.indexOf(c); if (i >= 0) { this.childNodes.splice(i, 1); } c.parentNode = null; return c; }
    remove() { if (this.parentNode) { this.parentNode.removeChild(this); } }
    setAttribute(k, v) { this.ozn[k] = String(v); if (k === "hidden") { this.hidden = true; } }
    getAttribute(k) { return k in this.ozn ? this.ozn[k] : null; }
    removeAttribute(k) { delete this.ozn[k]; if (k === "hidden") { this.hidden = false; } }
    addEventListener(tip, fn) { (this.dinle = this.dinle || {})[tip] = ((this.dinle || {})[tip] || []).concat([fn]); }
    set textContent(v) { this.childNodes = [new Metin(v)]; }
    get textContent() { return this.childNodes.map((c) => c.textContent).join(""); }
    *agac() { for (const c of this.childNodes) { if (c.nodeType === 1) { yield c; yield* c.agac(); } } }
    querySelector(s) {
      for (const n of this.agac()) {
        if (s.startsWith(".") ? n.classList.contains(s.slice(1)) : n.tagName === s.toUpperCase()) { return n; }
      }
      return null;
    }
  }
  const head = new Oge("head");
  const body = new Oge("body");
  const bolum = new Oge("section"); bolum.id = "fotoUretim"; bolum.setAttribute("hidden", "");
  body.appendChild(bolum);
  const document = {
    readyState: "complete", head, body,
    createElement: (e) => new Oge(e),
    createTextNode: (t) => new Metin(t),
    getElementById: (id) => { for (const n of [...head.agac(), ...body.agac()]) { if (n.id === id) { return n; } } return null; },
    querySelector: () => null,
    addEventListener: () => {},
  };
  return { document, bolum };
}

// Bolum kodunun fetch geri cagrisinda firlayan istisna (yakalanmamis Promise reddi) kosucuyu COKERTMEZ, SAYILIR:
// karar (removeAttribute) istisnadan ONCE verildiyse yine olculur.
let istisna = 0;
process.on("unhandledRejection", () => { istisna++; });

const veriYol = arg("--veri");
const jsYol = arg("--js");
let veriKaynak, jsKaynak;
try {
  veriKaynak = fs.readFileSync(veriYol, "utf8");
  jsKaynak = fs.readFileSync(jsYol, "utf8");
} catch (e) {
  bitir({ gorunur: null, istisna: 0, hata: "dosya-okunamadi: " + String(e && e.message).slice(0, 200) }, 2);
}

const { document, bolum } = sahteBelge();
const kok = {
  document, setTimeout, clearTimeout, setInterval: () => 0, clearInterval: () => {}, console: { log() {}, warn() {}, error() {} },
  // secenekler.js taklidi: bolum kodu SECENEK yoksa erken doner (bolum gizli kalir) — saplama kosucuyu
  // MUHAFAZAKAR kilar (acma yolu kapanmaz, "gizli" cevabi SECENEK eksikliginden dogamaz).
  PRUVO_SECENEK: { kargoKurus: () => 25000, kurusMetni: (k) => (k / 100).toFixed(2) + " TL" },
  turnstile: { render: () => 1, remove() {}, reset() {} },
  sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  location: { href: "https://pruvo3d.com/" },
};
kok.window = kok;
try {
  vm.runInNewContext(veriKaynak, kok, { filename: "foto-uretim-veri.js" });
} catch (e) {
  bitir({ gorunur: null, istisna: 0, hata: "veri-kosmadi: " + String(e && e.message).slice(0, 200) }, 2);
}

let acikYanit, ok, durum;
if (process.argv.includes("--pozitif")) {
  const F = kok.PRUVO_FOTO;
  const tur = F && Array.isArray(F.turler)
    ? F.turler.find((t) => typeof F.ornekSayisi !== "function" || F.ornekSayisi(t.kod) > 0) : null;
  if (!tur) { bitir({ gorunur: null, istisna: 0, hata: "pozitif-tur-yok" }, 2); }
  acikYanit = { acik: true, turler: [{ kod: tur.kod, ad: tur.ad || tur.kod }] };
  ok = true; durum = 200;
} else {
  try {
    acikYanit = JSON.parse(fs.readFileSync(arg("--acik"), "utf8"));
  } catch (e) {
    acikYanit = null; // govdesiz/bozuk yanit: bolum kodunun json() reddi yolu (cb(ok, status, null))
  }
  ok = arg("--ok") !== "0";
  durum = Number(arg("--durum") || 200);
}
kok.fetch = async () => ({
  ok, status: durum,
  json: async () => { if (acikYanit === null) { throw new Error("govdesiz"); } return acikYanit; },
});

try {
  vm.runInNewContext(jsKaynak, kok, { filename: "foto-uretim.js" });
} catch (e) {
  bitir({ gorunur: null, istisna: 0, hata: "js-kosmadi: " + String(e && e.message).slice(0, 200) }, 2);
}
for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); }
bitir({ gorunur: !bolum.hidden, istisna, hata: null }, 0);
