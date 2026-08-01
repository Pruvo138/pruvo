#!/usr/bin/env node
/**
 * FIYAT ESDEGERLIGI + PROVA (yan etkisiz fiyat sorgusu) KABUL TESTI.
 *
 *   node shop/test/fiyat-prova.mjs
 *
 * NE KANITLAR:
 *   1) ESDEGERLIK — konfigur aynasi (elle bakimli konfigurlar.js) URETILMIS artefakta
 *      cevrildi ve fiyat hesabi sepetiFiyatla()'ya cikarildi. ESKI kod (git HEAD: eski index
 *      + ELLE yazilmis ayna) ile YENI kod (yeni index + URETILMIS artefakt) 14 konfigur
 *      urununun 6 kombinasyonunda AYNI kurusu uretmeli — FARK 0.
 *   2) TAVAN — 3x tavan (150000 kurus) hala uygulaniyor (kapaksiz formul asiyor, sonuc kirpik).
 *   3) PROVA == TAHSILAT — /fiyat ucu, /baslat'in D1'e YAZDIGI tutarin AYNISINI doner.
 *   4) PROVA YAN ETKISIZ — YAPISAL kanit: D1 `run()` (yazma) sayaci ve global `fetch`
 *      (iyzico/Telegram/e-posta) sayaci prova cagrilarinda 0; ayni kosumda /baslat cagrisi
 *      ikisini de ARTIRIYOR (sayaclarin OLU olmadigi kaniti).
 *   5) PROVA SIZINTI YUZEYI — cevap beyaz-liste; katalog ic alanlari (baslik/kategori/gorsel),
 *      uretim verisi (hacim_mm3), siparis no / IBAN / token DONMEZ.
 *   6) PROVA FAIL-CLOSED — artefaktta olmayan konfigur urunu provada da 400 (sabit fiyata
 *      DUSMEZ); /baslat ile AYNI davranis.
 *   7) HIZ SINIRI = EN IYI CABA MALIYET FRENI (set 9) — /fiyat'in hiz siniri ISOLATE-YEREL bir
 *      Map DEGIL, native Cloudflare rate limiting binding'i (FIYAT_RATE_LIMIT). Bu set
 *      binding'in KOD TARAFINDAN DOGRU KULLANILDIGINI kanitlar (her isolate binding'i cagirir,
 *      verdigi karara uyar, 429 yolu bedava, fail-closed, mesru davranis 429 yemez).
 *      🔴 NE KANITLAMAZ: "IP basina N istek" diye GARANTILI/sert bir ust sinir. 29 Tem canli
 *      olcumu (worker version 60f56ffb-…) sayacin baglanti uc-noktasi/kolo basina BOLUNDUGUNU
 *      gosterdi: 60 yapilandirmasinda her istekte yeni baglanti acan istemcide ilk 429 ancak
 *      265. istekte geldi (efektif tavan ~4,4x). O eksen DETERMINISTIK DEGIL -> burada iddia
 *      EDILMEZ, set 9.2'de "ÖLÇÜLEMEDİ" olarak isaretlenir (bkz. GECEN/ILK_RED sabitleri).
 *   8) 9 KIRMIZI-MUTASYON (M1..M9) — bkz. asagidaki set 8.
 *   9) YANLIS-GUVENCE NOBETCISI (set 9.6) — repoda "sert tavan / kesin sinir / IP basina
 *      garanti" anlamina gelen ifadelerin GERI KONMASINI bloklar (mutant M8).
 *
 * OFFLINE: ag YOK (fetch sahtelenir; beklenmeyen adres HATA), D1 sahte, hicbir siparis
 * olusmaz, depo dosyasi DEGISMEZ (gecici dizinler kosum sonunda silinir).
 *
 * NODE 20 (CI runner tabani): module.registerHooks (Node 22+) KULLANILMAZ. Worker kaynaklari
 * shop/ ALTINDA AYNI DERINLIKTE gecici dizinlere yazilir (goreli ../../secenekler.js aynen
 * cozulur), JSON import satirlari icerige gomulur.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const SRC = path.join(SHOP, "src");
const require = createRequire(import.meta.url);

// ------------------------------------------------------------------ yukleyici
const TEMP_ONEK = "src-fiyat-tmp-";

function tempSupur() {
  for (const ad of fs.readdirSync(SHOP)) {
    if (ad.startsWith(TEMP_ONEK)) {
      fs.rmSync(path.join(SHOP, ad), { recursive: true, force: true });
    }
  }
}

/** `import X from "...json";` -> `const X = <json icerigi>;` (Node surumunden bagimsiz). */
function jsonGom(kaynak, kaynakDizin, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(kaynakDizin, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ") — desen guncellenmeli");
  }
  return cikti;
}

const dizinler = [];
/** Verilen {dosyaAdi: kaynak} haritasini shop/ altinda gecici bir dizine yazar, yolu doner. */
function dizinKur(etiket, dosyalar) {
  const yol = path.join(SHOP, TEMP_ONEK + etiket + "-" + process.pid);
  fs.rmSync(yol, { recursive: true, force: true });
  fs.mkdirSync(yol, { recursive: true });
  for (const [ad, kaynak] of Object.entries(dosyalar)) {
    fs.writeFileSync(path.join(yol, ad), jsonGom(kaynak, SRC, etiket + "/" + ad));
  }
  dizinler.push(yol);
  return yol;
}

tempSupur();
process.on("exit", () => {
  for (const d of dizinler) { fs.rmSync(d, { recursive: true, force: true }); }
});

function guncelKaynaklar() {
  const d = {};
  for (const ad of fs.readdirSync(SRC)) {
    if (ad.endsWith(".js")) { d[ad] = fs.readFileSync(path.join(SRC, ad), "utf8"); }
  }
  return d;
}

function headKaynaklari() {
  const liste = execFileSync("git", ["-C", KOK, "ls-tree", "--name-only", "HEAD", "shop/src/"],
                             { encoding: "utf8" }).trim().split("\n");
  const d = {};
  for (const yol of liste) {
    if (!yol.endsWith(".js")) { continue; }
    d[path.basename(yol)] = execFileSync("git", ["-C", KOK, "show", "HEAD:" + yol],
                                         { encoding: "utf8" });
  }
  return d;
}

let sayac = 0;
async function modulYukle(dizin) {
  sayac += 1;
  // Cache-buster: ayni dosya adiyla ikinci kez import edilirse Node onbellekten donerdi.
  return await import(pathToFileURL(path.join(dizin, "index.js")).href + "?s=" + sayac);
}

// ------------------------------------------------------------------ sahte cevre
const ag = { iyzico: 0, telegram: 0, diger: 0, toplam: 0, istekler: [] };
globalThis.fetch = async function sahteFetch(hedef, ayar) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  ag.toplam += 1;
  // GOVDE KAYDI (set 11 fis ekseni): iyzico kalem adi ve Telegram metni ancak istegin
  // govdesinden okunabilir. Yalniz OLCUM — hicbir karar bu kayda BAKMAZ.
  ag.istekler.push({ url: u, govde: (ayar && typeof ayar.body === "string") ? ayar.body : "" });
  if (u.includes("iyzico.test")) {
    ag.iyzico += 1;
    return new Response(JSON.stringify({
      status: "success", token: "test-token-" + ag.iyzico,
      paymentPageUrl: "https://odeme.test/sayfa",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  if (u.includes("telegram")) {
    ag.telegram += 1;
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  }
  ag.diger += 1;
  return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
};

/** @param {string[]} [yasakKolonlar] D1 semasinda OLMAYAN kolonlar: SELECT'te gecerlerse
 *  gercek D1 gibi "no such column" ile PATLAR (index.js'teki kolon merdiveni olculebilsin). */
function d1Sahte(satirlar, sayaclar, yasakKolonlar) {
  const harita = new Map(satirlar.map((u) => [u.id, u]));
  return {
    prepare(sql) {
      // Gercek D1 gibi PROJEKSIYON: satir yalniz SECILEN kolonlari tasir. (Aksi halde SELECT'ten
      // dusen bir kolon testte sessizce "hala var" gorunur -> kolon merdiveni OLCULEMEZ.)
      const secilen = ((/SELECT ([^]*?) FROM /.exec(sql) || [])[1] || "")
        .split(",").map((a) => a.trim()).filter(Boolean);
      const yasak = (yasakKolonlar || []).find((c) => secilen.includes(c));
      const izdusum = (u) => {
        if (!u || !secilen.length || secilen.includes("*")) { return u; }
        const o = {};
        for (const c of secilen) { if (c in u) { o[c] = u[c]; } }
        return o;
      };
      return {
        bind(...arg) {
          return {
            async all() {
              sayaclar.select += 1;
              if (yasak) { throw new Error("no such column: " + yasak); }
              return { results: arg.map((id) => harita.get(id)).filter(Boolean).map(izdusum) };
            },
            async first() { sayaclar.first += 1; return null; },
            async run() {
              sayaclar.run += 1;
              sayaclar.yazilan.push({ sql, arg });
              return { meta: { changes: 1 } };
            },
          };
        },
      };
    },
  };
}

const ENV_TABAN = {
  SITE_URL: "https://pruvo3d.com",
  IYZICO_BASE_URL: "https://iyzico.test",
  IYZICO_API_KEY: "test-api-key",
  IYZICO_SECRET_KEY: "test-secret-key",
  TELEGRAM_TOKEN: "test-telegram-token",
  TELEGRAM_CHAT: "1",
  TELEGRAM_API: "https://telegram.test",
  // HAVALE kolu (set 11 fis ekseni): Telegram bildirimi /baslat'ta YALNIZ havale yolunda
  // cikar (kart yolunda bildirim /donus'tadir). Bu iki var olmadan uc 503 doner.
  HAVALE_IBAN: "TR090006701000000059703630",
  HAVALE_UNVAN: "Test Unvan",
};

// ------------------------------------------- native rate-limit binding (beyan + sahte)
/**
 * wrangler.toml'daki `[[unsafe.bindings]]` bloklarini ayristir (harici TOML kutuphanesi YOK —
 * repo kurali: bagimlilik eklenmez). Her blok icin {name, type, namespace_id, limit, period}.
 * Blok govdesi bir sonraki satir-basi `[` tablosuna kadar surer; yorum satirlari `^anahtar =`
 * desenine uymadigi icin kendiliginden elenir.
 */
function unsafeBindingler(metin) {
  const parcalar = metin.split("[[unsafe.bindings]]").slice(1);
  return parcalar.map((p) => {
    const kes = p.search(/^\[/m);
    const govde = kes === -1 ? p : p.slice(0, kes);
    const al = (a) => {
      const m = govde.match(new RegExp("^" + a + "\\s*=\\s*(.+)$", "m"));
      return m ? m[1].trim().replace(/"/g, "") : null;
    };
    const simple = al("simple") || "";
    const sayi = (a) => {
      const m = simple.match(new RegExp("\\b" + a + "\\s*=\\s*(\\d+)"));
      return m ? Number(m[1]) : null;
    };
    return { name: al("name"), type: al("type"), namespace_id: al("namespace_id"),
             limit: sayi("limit"), period: sayi("period") };
  });
}

/** <ad> isimli [[unsafe.bindings]] blogunu metinden CIKAR (M6 mutanti). */
function bindingBlogunuSil(metin, ad) {
  const parcalar = metin.split("[[unsafe.bindings]]");
  let cikti = parcalar[0];
  for (const p of parcalar.slice(1)) {
    const kes = p.search(/^\[/m);
    const govde = kes === -1 ? p : p.slice(0, kes);
    if (new RegExp('name\\s*=\\s*"' + ad + '"').test(govde)) {
      cikti += (kes === -1 ? "" : p.slice(kes));      // blogu at, kuyrugu (sonraki tablo) koru
    } else {
      cikti += "[[unsafe.bindings]]" + p;
    }
  }
  return cikti;
}

const WRANGLER_YOL = path.join(SHOP, "wrangler.toml");
const WRANGLER = fs.readFileSync(WRANGLER_YOL, "utf8");
const FIYAT_BEYAN = unsafeBindingler(WRANGLER).find((b) => b.name === "FIYAT_RATE_LIMIT") || {};
// CAP = wrangler.toml'da BEYAN EDILEN limit. Testin hicbir yerinde sabit sayi capasi YOK:
// limit degistiginde iddialar kendiliginden kayar (beyanin KENDISI set 9.1'de denetlenir).
// Beyan yoksa 60'a duser — o hal ZATEN set 9.1'i kirmizi yakar, diger setler anlamli kalsin.
const CAP = FIYAT_BEYAN.limit > 0 ? FIYAT_BEYAN.limit : 60;

/**
 * 🔴 OLCULEN LIMITER SEMANTIGI (29 Tem canli, worker version 60f56ffb-…; curl, ayni cikis IP'si,
 * KALICI TEK BAGLANTI): binding yapilandirilan `limit` degerinden BIR FAZLASINI gecirir —
 * limit=60 iken 61 istek 200 dondu ve ilk 429 62. istekte geldi. Iddialar bu OLCULEN sayilara
 * capalidir; "tam limit kadar gecer" varsayimina DEGIL.
 * (M9 mutanti: limiter eski/yanlis semantige donduruldugunde set 9.2 KIRMIZI yanmali.)
 */
const GECEN = CAP + 1;        // 200 donen istek sayisi (olculen: 61)
const ILK_RED = GECEN + 1;    // ilk 429'un sira numarasi (olculen: 62)

/**
 * Cloudflare `ratelimit` binding'inin sahtesi: ANAHTAR (IP) BASINA sayar, periyot ici,
 * `limit`+1 gecirir (yukaridaki olculen semantik).
 *
 * 🔴 BU SAHTE NEYI MODELLER: TEK bir sayac. Worker kodunun kac ayri modul ornegi (isolate)
 * olursa olsun hepsi AYNI sayaci gorur. Boylece set 9.2 sunu deterministik olarak olcer:
 * "kod her isolate'te binding'i CAGIRIYOR ve verdigi karara UYUYOR" (isolate-yerel Map'in
 * yapamadigi sey). Kanit ekseni KODUN BINDING'I KULLANIMI'dir.
 *
 * ⚠️ BU SAHTE NEYI MODELLEMEZ: gercek dunyada sayacin TEK olmasi. 29 Tem canli olcumunde
 * sayacin baglanti uc-noktasi/kolo basina BOLUNDUGU olculdu (her istekte yeni baglanti ->
 * 300 istek/11,2 sn, ilk 429 265. istekte; efektif tavan ~4,4x). Bolunmenin carpani istemcinin
 * baglanti davranisina ve CF yonlendirmesine bagli -> DETERMINISTIK DEGIL, CI'da iddia
 * EDILEMEZ (edilirse tum ekibin yayini rastgele durur). Set 9.2 bunu "ÖLÇÜLEMEDİ" der.
 * Zaman penceresi YOK (kosum saniyeler surer) -> deterministik, CI'da kararsiz kirmizi uretmez.
 */
function limiterKur(cap) {
  const sayac = new Map();
  return {
    cap: cap,
    cagri: 0,
    patlat: false,
    sifirla() { sayac.clear(); this.cagri = 0; this.patlat = false; },
    async limit(arg) {
      this.cagri += 1;
      if (this.patlat) { throw new Error("limiter down (sahte)"); }
      const k = (arg && arg.key) || "yok";
      const n = (sayac.get(k) || 0) + 1;
      sayac.set(k, n);
      return { success: n <= cap + 1 };   // olculen: limit+1 gecer (bkz. GECEN)
    },
  };
}
const LIMITER = limiterKur(CAP);
ENV_TABAN.FIYAT_RATE_LIMIT = LIMITER;

function yeniSayac() { return { select: 0, first: 0, run: 0, yazilan: [] }; }

const MUSTERI = { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
                  adres: "Test mahallesi test sokak no 1", sehir: "Mugla" };

/** /baslat — GERCEK worker kodundan; cevabi + D1'e yazilan satiri + sayaclari dondurur.
 *  yasakKolonlar: D1 semasinda olmayan kolonlar (bkz. d1Sahte). */
async function baslat(mod, d1Satirlari, sepet, yasakKolonlar, odeme) {
  const sayaclar = yeniSayac();
  const agOnce = ag.toplam;
  const istekOnce = ag.istekler.length;
  const env = Object.assign({}, ENV_TABAN,
                            { KATALOG: d1Sahte(d1Satirlari, sayaclar, yasakKolonlar) });
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sozlesme_onay: true, odeme: odeme || "kart",
                           musteri: MUSTERI, sepet }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  const insert = sayaclar.yazilan.find((k) => /INSERT INTO siparisler/.test(k.sql));
  let satir = null, tutarKurus = null;
  if (insert) {
    const dizi = insert.arg.find((x) => typeof x === "string" && x.startsWith("["));
    satir = dizi ? JSON.parse(dizi)[0] : null;
    tutarKurus = insert.arg.find((x) => typeof x === "number" && x > 0) ?? null;
  }
  return { kod: cevap.status, govde, satir, birimKurus: satir ? satir.birim_kurus : null,
           tutarKurus, d1Yazma: sayaclar.run, agCagri: ag.toplam - agOnce, sayaclar,
           // FIS EKSENI (set 11): D1 INSERT'in HAM argumanlari (filament/renk kolonlari dahil)
           // + bu cagrida cikan ag istekleri (iyzico kalem adi, Telegram metni).
           insertArg: insert ? insert.arg : null,
           istekler: ag.istekler.slice(istekOnce) };
}

let ipSayaci = 0;
/** /fiyat (prova) — GERCEK worker kodundan; cevabi + sayaclari dondurur.
 *  limiter: undefined -> paylasilan LIMITER (varsayilan, canli konfigurasyon)
 *           null      -> binding HIC YOK (fail-closed olcumu)
 *           nesne     -> verilen sahte binding (bozuk obje / patlayan limiter) */
async function prova(mod, d1Satirlari, sepet, sabitIp, limiter, yasakKolonlar) {
  const sayaclar = yeniSayac();
  const agOnce = ag.toplam;
  const env = Object.assign({}, ENV_TABAN,
                            { KATALOG: d1Sahte(d1Satirlari, sayaclar, yasakKolonlar) });
  if (limiter === null) { delete env.FIYAT_RATE_LIMIT; }
  else if (limiter !== undefined) { env.FIYAT_RATE_LIMIT = limiter; }
  ipSayaci += 1;
  const ip = sabitIp || ("10." + Math.floor(ipSayaci / 65536) % 256 + "." +
                         Math.floor(ipSayaci / 256) % 256 + "." + (ipSayaci % 256));
  const istek = new Request("https://pruvo3d.com/api/shop/fiyat", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": ip },
    body: JSON.stringify({ sepet }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  let govde = {};
  let hamMetin = "";
  try { hamMetin = await cevap.clone().text(); govde = JSON.parse(hamMetin); } catch (e) { govde = {}; }
  return { kod: cevap.status, govde, ham: hamMetin, d1Yazma: sayaclar.run,
           d1Okuma: sayaclar.select, d1First: sayaclar.first,
           agCagri: ag.toplam - agOnce, sayaclar };
}

// ------------------------------------------------------------------ veri
require(path.join(KOK, "secenekler.js"));
const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi"); }
const FRONT = require(path.join(KOK, "konfigur.js"));

const URUNLER = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));
const KONFIGUR_URUNLER = URUNLER.filter((u) => u.konfigur);

/** Anahtar sirasindan bagimsiz kanonik JSON (d1-sync.py konfigur_kanonik aynasi). */
function kanonik(o) {
  if (o === null || typeof o !== "object") { return JSON.stringify(o); }
  if (Array.isArray(o)) { return "[" + o.map(kanonik).join(",") + "]"; }
  return "{" + Object.keys(o).sort().map((k) => JSON.stringify(k) + ":" + kanonik(o[k]))
    .join(",") + "}";
}

/** D1 satiri — `konfigur` KOLONU dahil: FAZ 4'ten beri konfigur fiyati BU KOLONDAN
 *  hesaplanir (bundle'dan degil), kolonsuz satir kurulursa kalem fail-closed 400 alir. */
function d1Satiri(u) {
  return { id: u.id, baslik: u.baslik || "", kategori: u.kategori || "",
           fiyat: u.fiyat || "", parametrik: u.parametrik ? 1 : 0,
           gorsel: (u.gorseller && u.gorseller[0]) || "",
           konfigur: u.konfigur ? kanonik(u.konfigur) : "",
           // `tur` kolonu (canli D1'de 2026-07-31'den beri TEXT NOT NULL DEFAULT ''):
           // katalogdaki degeri AYNEN tasinir — "fiziksel" = hazir ticari mal.
           tur: u.tur || "" };
}

// Artefaktta OLMAYAN konfigur urunu (D1'e girmis, Worker deploy edilmemis penceresi).
const YENI_KONFIGUR = { id: "ejderha-serit-dekoratif-figur", baslik: "Ejderha Heykeli — Şerit",
                        kategori: "Skan Art", fiyat: "500 TL", parametrik: 0, gorsel: "" };

// 6 kombinasyon (boy mm / malzeme) — aralik ucu + orta + tavan bolgesi.
const KOMBIN = [[60, "PLA"], [150, "PLA"], [150, "PETG"], [220, "PETG"], [300, "PLA"],
                [300, "ASA"]];

const ham = [];
let kirmizi = 0;
let setSayisi = 0;
function baslik(s) { setSayisi += 1; ham.push(""); ham.push(s); }
function not(s) { ham.push("    " + s); }

ham.push("Node: " + process.version + " (CI tabani: 20.x — daha yeni API KULLANMA)");

const YENI_DIZIN = dizinKur("yeni", guncelKaynaklar());
const YENI = await modulYukle(YENI_DIZIN);

// =================================================================== 1a) SPEC (referanssiz)
baslik("== 1a) FIYAT SPEC'i — SABIT beklenen kuruslar + bagimsiz orakil (/konfigur.js) ==");
{
  // KALICI ve REFERANSSIZ iddia: [[60,500],[300,2500]] capali urunlerde 6 kombinasyonun kurusu
  // SPEC'ten SABIT yazilir (kaydirma yakalansin) + AYRICA front cekirdegi (/konfigur.js)
  // bagimsiz orakil olarak dogrular. Boylece bu set HEAD'e (kendi commit'ime) BAGIMLI DEGIL:
  // hem worker hem front cekirdegi birlikte kaysa bile SABIT sayilar KIRMIZI yanar.
  const SPEC = { "60/PLA": 50000, "150/PLA": 73600, "150/PETG": 95700, "220/PETG": 150000,
                 "300/PLA": 150000, "300/ASA": 150000 };
  const hatalar = [];
  let specOlcum = 0, orakilOlcum = 0;
  for (const u of KONFIGUR_URUNLER) {
    const kf = u.konfigur;
    const standartCapa = JSON.stringify(kf.fiyatCapalari) === JSON.stringify([[60, 500], [300, 2500]]);
    for (const [boy, malzeme] of KOMBIN) {
      const kat = (kf.malzemeler.find((m) => m.ad === malzeme) || {}).katsayi;
      const r = await baslat(YENI, [d1Satiri(u)],
        [{ id: u.id, malzeme, renk: "Siyah", adet: 1, parametreler: { boy_mm: boy } }]);
      const orakil = FRONT.fiyatKurus(kf, FRONT.boyDuzelt(kf, boy), kat);
      orakilOlcum += 1;
      if (r.birimKurus !== orakil) {
        hatalar.push("orakil " + u.id + " " + boy + "/" + malzeme + ": worker=" + r.birimKurus +
                     " front=" + orakil);
      }
      if (standartCapa) {
        specOlcum += 1;
        if (r.birimKurus !== SPEC[boy + "/" + malzeme]) {
          hatalar.push("SPEC " + u.id + " " + boy + "/" + malzeme + ": " + r.birimKurus +
                       " != " + SPEC[boy + "/" + malzeme]);
        }
      }
    }
  }
  not("SPEC iddiasi: " + specOlcum + " kombinasyon (standart capali urunler); bagimsiz orakil " +
      "(/konfigur.js) iddiasi: " + orakilOlcum + "; uyusmazlik: " + hatalar.length);
  if (hatalar.length) {
    kirmizi += 1;
    hatalar.slice(0, 6).forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — fiyat spec'i");
  } else { ham.push("  ✅ GECTI — kuruslar SPEC ve bagimsiz orakille birebir"); }
}

// =================================================================== 1b) ESDEGERLIK
baslik("== 1b) FIYAT ESDEGERLIGI — git HEAD kodu vs CALISMA AGACI kodu ==");
let eskiMod = null;
const headIndex = (() => {
  try {
    return execFileSync("git", ["-C", KOK, "show", "HEAD:shop/src/index.js"], { encoding: "utf8" });
  } catch (e) { return null; }
})();
const calismaIndex = fs.readFileSync(path.join(SRC, "index.js"), "utf8");
const headKonf = (() => {
  try {
    return execFileSync("git", ["-C", KOK, "show", "HEAD:shop/src/konfigurlar.js"],
                        { encoding: "utf8" });
  } catch (e) { return null; }
})();
const calismaKonf = fs.readFileSync(path.join(SRC, "konfigurlar.js"), "utf8");
// DURUST ETIKET (bayat-kabul-testi dersi): HEAD ile calisma agaci AYNIYSA bu set totolojidir —
// "yesil" demek yerine ÖLÇÜLEMEDİ denir. Dalda (kod degismisken) GERCEK karsilastirma yapar.
const ayniMi = headIndex === calismaIndex && headKonf === calismaKonf;
if (ayniMi) {
  not("ÖLÇÜLEMEDİ ⚪: HEAD:shop/src/index.js + konfigurlar.js calisma agaciyla BIREBIR " +
      "(degisiklik commit'lenmis) -> karsilastirma totolojiye doner. Kalici koruma 1a'dadir.");
} else {
  try {
    eskiMod = await modulYukle(dizinKur("eski", headKaynaklari()));
  } catch (e) {
    kirmizi += 1;
    not("❌ ÖLÇÜLEMEDİ: HEAD kaynaklari yuklenemedi — " + e.message);
  }
}
if (eskiMod) {
  const basliklar = KOMBIN.map(([b, m]) => b + "/" + m);
  not("urun".padEnd(42) + basliklar.map((s) => s.padStart(9)).join("") + "     fark");
  let farkToplam = 0, olcum = 0;
  for (const u of KONFIGUR_URUNLER) {
    const hucre = [];
    let fark = 0;
    for (const [boy, malzeme] of KOMBIN) {
      const kalem = { id: u.id, malzeme, renk: "Siyah", adet: 1, parametreler: { boy_mm: boy } };
      const e = await baslat(eskiMod, [d1Satiri(u)], [kalem]);
      const y = await baslat(YENI, [d1Satiri(u)], [kalem]);
      olcum += 1;
      if (e.birimKurus !== y.birimKurus || e.kod !== y.kod) {
        fark += 1; farkToplam += 1;
        ham.push("    ❌ " + u.id + " " + boy + "/" + malzeme + ": eski=" + e.birimKurus +
                 "(" + e.kod + ") yeni=" + y.birimKurus + "(" + y.kod + ")");
      }
      hucre.push(String(y.birimKurus));
    }
    not(u.id.padEnd(42) + hucre.map((s) => s.padStart(9)).join("") + fark.toString().padStart(9));
  }
  not("olculen kombinasyon: " + olcum + " (14 urun x 6) — TOPLAM FARK: " + farkToplam);
  if (farkToplam !== 0) { kirmizi += 1; ham.push("  ❌ KALDI — fiyat esdegerligi"); }
  else { ham.push("  ✅ GECTI — eski ve yeni kod BIREBIR ayni kurusu uretti (fark 0)"); }
}

// =================================================================== 2) TAVAN
baslik("== 2) 3x TAVAN (shop/src/konfigur.js:59 — 3 x fiyatCapalari[0][1]) hala uygulaniyor ==");
{
  const hatalar = [];
  let tavanVuran = 0;
  for (const u of KONFIGUR_URUNLER) {
    const kf = u.konfigur;
    const tavan = 3 * kf.fiyatCapalari[0][1] * 100;
    const kat = (kf.malzemeler.find((m) => m.ad === "ASA") || {}).katsayi;
    const m = FRONT.fiyatModeli(kf);
    const kapaksizTl = (m.sabit + m.birim * (FRONT.hacimMm3(kf, 300) / 1000)) * kat;
    const r = await baslat(YENI, [d1Satiri(u)],
      [{ id: u.id, malzeme: "ASA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 300 } }]);
    if (Math.round(kapaksizTl) * 100 <= tavan) {
      hatalar.push(u.id + ": kapaksiz fiyat tavani ASMIYOR (test anlamsiz)");
    }
    if (r.birimKurus !== tavan) {
      hatalar.push(u.id + ": 300mm/ASA = " + r.birimKurus + " != tavan " + tavan);
    } else { tavanVuran += 1; }
  }
  not("300mm/ASA'da tavana kirpilan urun: " + tavanVuran + "/" + KONFIGUR_URUNLER.length +
      " (tavan = 3 x 500 TL = 150000 kurus)");
  if (hatalar.length) {
    kirmizi += 1;
    hatalar.slice(0, 5).forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — tavan");
  } else { ham.push("  ✅ GECTI — tavan 14/14 urunde uygulaniyor"); }
}

// =================================================================== 3) PROVA == TAHSILAT
baslik("== 3) PROVA == TAHSILAT — /fiyat, /baslat'in D1'e YAZDIGI tutarin AYNISINI doner ==");
{
  const hatalar = [];
  let olcum = 0;
  for (const u of KONFIGUR_URUNLER) {
    for (const [boy, malzeme] of KOMBIN) {
      const kalem = { id: u.id, malzeme, renk: "Siyah", adet: 1, parametreler: { boy_mm: boy } };
      const b = await baslat(YENI, [d1Satiri(u)], [kalem]);
      const p = await prova(YENI, [d1Satiri(u)], [kalem]);
      olcum += 1;
      const pb = p.govde.satirlar && p.govde.satirlar[0] ? p.govde.satirlar[0].birim_kurus : null;
      const beklenenTahsilat = b.tutarKurus + SECENEK.kargoKurus(b.tutarKurus);
      if (p.kod !== 200 || pb !== b.birimKurus) {
        hatalar.push(u.id + " " + boy + "/" + malzeme + ": prova=" + pb + "(" + p.kod +
                     ") baslat=" + b.birimKurus);
      }
      if (p.govde.tahsilat_kurus !== beklenenTahsilat) {
        hatalar.push(u.id + " " + boy + "/" + malzeme + ": prova tahsilat=" +
                     p.govde.tahsilat_kurus + " != " + beklenenTahsilat);
      }
    }
  }
  // Sabit fiyatli urunlerden orneklem (konfigur DISI kol da provada birebir mi).
  const sabitAday = URUNLER.filter((u) => !u.konfigur && !u.parametrik && u.fiyat &&
                                          /[0-9]/.test(String(u.fiyat)));
  const adim = Math.max(1, Math.floor(sabitAday.length / 40));
  let sabitOlcum = 0;
  for (let i = 0; i < sabitAday.length && sabitOlcum < 40; i += adim) {
    const u = sabitAday[i];
    const kalem = { id: u.id, malzeme: "PETG", renk: "Siyah", adet: 3 };
    const b = await baslat(YENI, [d1Satiri(u)], [kalem]);
    const p = await prova(YENI, [d1Satiri(u)], [kalem]);
    sabitOlcum += 1;
    const pb = p.govde.satirlar && p.govde.satirlar[0] ? p.govde.satirlar[0].birim_kurus : null;
    if (b.kod !== 200 || p.kod !== 200 || pb !== b.birimKurus ||
        p.govde.urun_kurus !== b.tutarKurus) {
      hatalar.push("sabit " + u.id + ": baslat=" + b.birimKurus + "/" + b.tutarKurus +
                   " prova=" + pb + "/" + p.govde.urun_kurus);
    }
  }
  not("konfigur kombinasyonu: " + olcum + "; sabit-fiyatli orneklem: " + sabitOlcum +
      "; uyusmazlik: " + hatalar.length);
  if (hatalar.length) {
    kirmizi += 1;
    hatalar.slice(0, 5).forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — prova/tahsilat esitligi");
  } else { ham.push("  ✅ GECTI — prova tutari tahsilat tutariyla BIREBIR"); }
}

// =================================================================== 4) YAN ETKISIZLIK
baslik("== 4) PROVA YAN ETKISIZ — D1 yazma + ag cagri SAYACLARI (yapisal kanit) ==");
{
  const hatalar = [];
  let toplamYazma = 0, toplamAg = 0, toplamOkuma = 0, toplamFirst = 0;
  const vaka = [
    ["konfigur 300/ASA", [d1Satiri(KONFIGUR_URUNLER[0])],
     [{ id: KONFIGUR_URUNLER[0].id, malzeme: "ASA", renk: "Siyah", adet: 2,
        parametreler: { boy_mm: 300 } }]],
    ["konfigur 60/PLA", [d1Satiri(KONFIGUR_URUNLER[1])],
     [{ id: KONFIGUR_URUNLER[1].id, malzeme: "PLA", renk: "Siyah", adet: 1,
        parametreler: { boy_mm: 60 } }]],
    ["sabit fiyatli", [d1Satiri(URUNLER.find((u) => !u.konfigur && !u.parametrik && u.fiyat &&
                                                   /[0-9]/.test(String(u.fiyat))))],
     [{ id: URUNLER.find((u) => !u.konfigur && !u.parametrik && u.fiyat &&
                                /[0-9]/.test(String(u.fiyat))).id,
        malzeme: "PLA", renk: "Siyah", adet: 1 }]],
    ["artefaktta YOK (fail-closed)", [YENI_KONFIGUR],
     [{ id: YENI_KONFIGUR.id, malzeme: "PLA", renk: "Siyah", adet: 1,
        parametreler: { boy_mm: 300 } }]],
    ["bilinmeyen urun", [], [{ id: "olmayan-urun-xyz", malzeme: "PLA", renk: "Siyah", adet: 1 }]],
  ];
  for (const [ad, satirlar, sepet] of vaka) {
    const p = await prova(YENI, satirlar, sepet);
    toplamYazma += p.d1Yazma; toplamAg += p.agCagri;
    toplamOkuma += p.d1Okuma; toplamFirst += p.d1First;
    if (p.d1Yazma !== 0) { hatalar.push(ad + ": D1'e " + p.d1Yazma + " YAZMA yapildi"); }
    if (p.agCagri !== 0) { hatalar.push(ad + ": " + p.agCagri + " AG cagrisi yapildi"); }
    if (p.d1First !== 0) { hatalar.push(ad + ": siparis_no sorgusu (first) " + p.d1First); }
    if (p.sayaclar.yazilan.length) { hatalar.push(ad + ": SQL yazma: " + p.sayaclar.yazilan[0].sql.slice(0, 40)); }
  }
  not("prova x" + vaka.length + " -> D1 YAZMA=" + toplamYazma + " (0 olmali), AG cagri=" +
      toplamAg + " (0 olmali), siparis_no sorgusu=" + toplamFirst + " (0 olmali), D1 SALT-OKUMA=" +
      toplamOkuma);

  // SAYAC OLU MU? Ayni kosumda /baslat ikisini de ARTIRMALI (yoksa yukaridaki 0'lar anlamsiz).
  const b = await baslat(YENI, [d1Satiri(KONFIGUR_URUNLER[0])],
    [{ id: KONFIGUR_URUNLER[0].id, malzeme: "ASA", renk: "Siyah", adet: 2,
       parametreler: { boy_mm: 300 } }]);
  not("KONTROL (/baslat ayni sepet) -> D1 YAZMA=" + b.d1Yazma + " (>0 olmali), AG cagri=" +
      b.agCagri + " (>0 olmali) — sayaclarin OLU olmadigi kaniti");
  if (!(b.d1Yazma > 0)) { hatalar.push("KONTROL: /baslat D1'e yazmadi -> yazma sayaci OLU"); }
  if (!(b.agCagri > 0)) { hatalar.push("KONTROL: /baslat ag cagrisi yapmadi -> ag sayaci OLU"); }

  if (hatalar.length) {
    kirmizi += 1;
    hatalar.forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — yan etkisizlik");
  } else { ham.push("  ✅ GECTI — prova hicbir yazma/bildirim uretmiyor, sayaclar canli"); }
}

// =================================================================== 5) SIZINTI YUZEYI
baslik("== 5) PROVA SIZINTI YUZEYI — beyaz liste + yasak alan taramasi ==");
{
  const hatalar = [];
  const UST_IZIN = new Set(["prova", "satirlar", "urun_kurus", "kargo_kurus", "tahsilat_kurus",
                            "tutar", "net_kurus", "kdv_kurus", "kdv_yuzde"]);
  const SATIR_IZIN = new Set(["id", "adet", "birim_kurus", "tutar_kurus", "parametre_detay"]);
  const urun = KONFIGUR_URUNLER[0];
  const p = await prova(YENI, [d1Satiri(urun)],
    [{ id: urun.id, malzeme: "PETG", renk: "Siyah", adet: 1, parametreler: { boy_mm: 220 } }]);
  const ustFazla = Object.keys(p.govde).filter((k) => !UST_IZIN.has(k));
  if (ustFazla.length) { hatalar.push("cevapta izinsiz UST alan: " + ustFazla.join(",")); }
  for (const s of (p.govde.satirlar || [])) {
    const f = Object.keys(s).filter((k) => !SATIR_IZIN.has(k));
    if (f.length) { hatalar.push("satirda izinsiz alan: " + f.join(",")); }
  }
  // Icerik taramasi: katalog basligi / gorsel URL'i / hacim ham metinde GECMEMELI.
  const gorselUrl = (urun.gorseller && urun.gorseller[0]) || "";
  const yasak = [["baslik", urun.baslik], ["kategori", urun.kategori], ["gorsel", gorselUrl],
                 ["hacim_mm3", "hacim"], ["iban", "iban"], ["token", "token"],
                 ["siparis no", "PR-"]];
  for (const [ad, deger] of yasak) {
    if (deger && p.ham.toLowerCase().includes(String(deger).toLowerCase())) {
      hatalar.push("cevap govdesinde '" + ad + "' izi var");
    }
  }
  not("cevap alanlari: " + Object.keys(p.govde).join(",") + " | satir alanlari: " +
      Object.keys((p.govde.satirlar || [{}])[0]).join(","));
  not("yasak iz taramasi (baslik/kategori/gorsel/hacim/iban/token/siparis-no): " +
      (hatalar.length ? "IHLAL" : "TEMIZ"));

  // PII: govdeye musteri konsa bile cevaba SIZMAZ ve yazma OLMAZ.
  const sayaclar = yeniSayac();
  const env = Object.assign({}, ENV_TABAN, { KATALOG: d1Sahte([d1Satiri(urun)], sayaclar) });
  const agOnce = ag.toplam;
  const istek = new Request("https://pruvo3d.com/api/shop/fiyat", {
    method: "POST", headers: { "Content-Type": "application/json", "CF-Connecting-IP": "10.9.9.9" },
    body: JSON.stringify({ musteri: MUSTERI, sozlesme_onay: true, atif: { fbp: "fb.1.x" },
                           sepet: [{ id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                                     parametreler: { boy_mm: 150 } }] }),
  });
  const cev = await mod_fetch(YENI, istek, env);
  const metin = await cev.text();
  if (metin.includes(MUSTERI.eposta) || metin.includes(MUSTERI.tel) ||
      metin.includes("fb.1.x")) { hatalar.push("PII/atif cevaba yansidi"); }
  if (sayaclar.run !== 0) { hatalar.push("musterili prova D1'e YAZDI"); }
  if (ag.toplam !== agOnce) { hatalar.push("musterili prova AG cagrisi yapti"); }
  not("PII testi: govdede musteri+atif verildi -> cevapta iz=" +
      (metin.includes(MUSTERI.eposta) ? "VAR" : "YOK") + ", D1 yazma=" + sayaclar.run +
      ", ag=" + (ag.toplam - agOnce));

  // Yontem/uc yuzeyi: GET /fiyat kabul EDILMEZ.
  const getCev = await mod_fetch(YENI, new Request("https://pruvo3d.com/api/shop/fiyat"),
                                 Object.assign({}, ENV_TABAN,
                                   { KATALOG: d1Sahte([], yeniSayac()) }));
  if (getCev.status !== 404) { hatalar.push("GET /fiyat " + getCev.status + " (404 olmali)"); }
  not("GET /fiyat -> " + getCev.status + " (404 beklenir; uc yalniz POST)");

  if (hatalar.length) {
    kirmizi += 1;
    hatalar.forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — sizinti yuzeyi");
  } else { ham.push("  ✅ GECTI — cevap beyaz-liste; ic alan/PII/uc yuzeyi temiz"); }
}

async function mod_fetch(mod, istek, env) {
  return await mod.default.fetch(istek, env, { waitUntil() {} });
}

// =================================================================== 6) DOGRULAMA + HIZ SINIRI
baslik("== 6) PROVA DOGRULAMASI /baslat ILE AYNI + hiz siniri ==");
{
  const hatalar = [];
  const urun = KONFIGUR_URUNLER[0];
  const satirlar = [d1Satiri(urun)];
  const vaka = [
    ["bilinmeyen malzeme", { id: urun.id, malzeme: "TITANYUM", renk: "Siyah", adet: 1 }],
    ["bilinmeyen renk", { id: urun.id, malzeme: "PLA", renk: "Neon", adet: 1 }],
    ["adet 500", { id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 500 }],
    ["adet 0", { id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 0 }],
    ["id bicimi bozuk", { id: "BUYUK HARF!", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    ["boy_etiket (D1'de yok)", { id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                                 boy_etiket: "L" }],
  ];
  for (const [ad, kalem] of vaka) {
    const b = await baslat(YENI, satirlar, [kalem]);
    const p = await prova(YENI, satirlar, [kalem]);
    if (b.kod !== p.kod || b.govde.hata !== p.govde.hata) {
      hatalar.push(ad + ": baslat=" + b.kod + "/" + b.govde.hata + " prova=" + p.kod + "/" +
                   p.govde.hata);
    }
  }
  const bosSepet = await prova(YENI, satirlar, []);
  if (bosSepet.kod !== 400) { hatalar.push("bos sepet " + bosSepet.kod); }
  const cokKalem = await prova(YENI, satirlar,
    Array.from({ length: 31 }, () => ({ id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1 })));
  if (cokKalem.kod !== 400 || cokKalem.govde.hata !== "gecersiz-sepet") {
    hatalar.push("31 kalem " + cokKalem.kod + "/" + cokKalem.govde.hata);
  }
  not("dogrulama paritesi: " + vaka.length + " vaka + bos sepet(" + bosSepet.kod +
      ") + 31 kalem(" + cokKalem.govde.hata + ") -> uyusmazlik " + hatalar.length);

  // HIZ SINIRI (native binding): ayni IP'den ILK_RED kadar istek -> sonuncusu 429; farkli IP
  // etkilenmez; yazma YOK. Sahte binding wrangler.toml'da BEYAN EDILEN limiti OLCULEN semantikle
  // (limit+1 gecer) uygular -> iddia sabit sayiya degil beyan + olcume capalidir.
  // Pencere/zaman yok -> tur tekrarina gerek kalmadi (deterministik).
  const sepet = [{ id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                   parametreler: { boy_mm: 150 } }];
  LIMITER.sifirla();
  let ilk429 = 0, yazma = 0;
  for (let i = 1; i <= ILK_RED; i++) {
    const r = await prova(YENI, satirlar, sepet, "203.0.113.7");
    yazma += r.d1Yazma;
    if (r.kod === 429 && !ilk429) { ilk429 = i; }
  }
  const baskaIp = await prova(YENI, satirlar, sepet, "203.0.113.8");
  not("hiz siniri: beyan edilen cap=" + CAP + "/dk (olculen: " + GECEN + " gecer); ayni IP'de " +
      "ilk 429 = " + ilk429 + ". istek (" + ILK_RED + ". beklenir); baska IP -> " + baskaIp.kod +
      "; sinir sirasinda D1 yazma=" + yazma);
  if (ilk429 !== ILK_RED) {
    hatalar.push("hiz siniri " + ILK_RED + ". istekte devreye girmedi (ilk429=" + ilk429 + ")");
  }
  if (baskaIp.kod !== 200) { hatalar.push("baska IP de kisitlandi: " + baskaIp.kod); }
  if (yazma !== 0) { hatalar.push("hiz siniri yolunda D1 yazma: " + yazma); }

  if (hatalar.length) {
    kirmizi += 1;
    hatalar.forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — dogrulama/hiz siniri");
  } else { ham.push("  ✅ GECTI — prova dogrulamasi tahsilatla ayni; hiz siniri calisiyor"); }
}

// =================================================================== 7) FAIL-CLOSED IDDIALARI
/** Artefaktta OLMAYAN konfigur urunu icin FAIL-CLOSED iddialari (hem /baslat hem /fiyat).
 *  Mutasyon altinda bu iddialarin KIRMIZI yanmasi beklenir (vakum olcumu). */
async function failClosedIddialari(mod) {
  const sonuc = [];
  for (const [boy, malzeme] of [[60, "PLA"], [150, "PLA"], [300, "PLA"], [300, "ASA"]]) {
    const kalem = { id: YENI_KONFIGUR.id, malzeme, renk: "Siyah", adet: 1,
                    parametreler: { boy_mm: boy } };
    const b = await baslat(mod, [YENI_KONFIGUR], [kalem]);
    const p = await prova(mod, [YENI_KONFIGUR], [kalem]);
    const et = boy + "mm/" + malzeme;
    sonuc.push({ ad: "baslat " + et + " kod=400", ok: b.kod === 400, olculen: b.kod });
    sonuc.push({ ad: "baslat " + et + " hata=konfigur-urun", ok: b.govde.hata === "konfigur-urun",
                 olculen: b.govde.hata });
    sonuc.push({ ad: "baslat " + et + " SABIT FIYAT HESAPLANMADI", ok: b.birimKurus === null,
                 olculen: b.birimKurus });
    sonuc.push({ ad: "baslat " + et + " D1'e YAZILMADI", ok: b.d1Yazma === 0, olculen: b.d1Yazma });
    sonuc.push({ ad: "prova " + et + " kod=400", ok: p.kod === 400, olculen: p.kod });
    sonuc.push({ ad: "prova " + et + " hata=konfigur-urun", ok: p.govde.hata === "konfigur-urun",
                 olculen: p.govde.hata });
    sonuc.push({ ad: "prova " + et + " FIYAT DONMEDI",
                 ok: !p.govde.satirlar && p.govde.tahsilat_kurus === undefined,
                 olculen: JSON.stringify(p.govde.tahsilat_kurus) });
  }
  return sonuc;
}

baslik("== 7) FAIL-CLOSED — artefaktta olmayan konfigur urunu (baslat + prova) ==");
{
  const iddia = await failClosedIddialari(YENI);
  const kalan = iddia.filter((i) => !i.ok);
  not("iddia: " + iddia.length + " (4 kombinasyon x 7) — kalan: " + kalan.length);
  kalan.slice(0, 10).forEach((i) => ham.push("    ❌ " + i.ad + " (olculen: " + i.olculen + ")"));
  if (kalan.length) { kirmizi += 1; ham.push("  ❌ KALDI — fail-closed"); }
  else { ham.push("  ✅ GECTI — 28/28 iddia; sabit fiyat HESAPLANMIYOR, prova da 400 doner"); }
}

// ====================================== 10) FIZIKSEL URUN — MALZEME/RENK CARPANI YOK
/**
 * NEDEN VAR (para yolu; canli /api/shop/fiyat prova ucuyla OLCULDU, 2026-08-01):
 *   `tur == "fiziksel"` kayit HAZIR TICARI MALDIR (tekne boyasi, vernik...). 3D baski
 *   malzemesi/rengi KARSILIKSIZDIR. 31 Tem'de secici UI'i urun SAYFASINDAN kaldirildi, ama
 *   SUNUCU fiyatlama fonksiyonu `tur`-KORDU. 1.000 TL'lik fiziksel urunde OLCULEN (onarim
 *   ONCESI): PLA/Siyah 100000 · PLA/"Diğer" 115000 (+%15) · ASA/"Diğer" 184000 (+%84).
 *   Sepet localStorage'da YASADIGI icin onarim oncesi kaydedilmis BAYAT bir satir hala fazla
 *   tahsil edilirdi -> istemcide secici gizlemek bu deligi KAPATMAZ.
 *
 * ONARIM (secenekler.js hesaplaFiyatKurus 5. parametre `tur` + satirOzeti; shop/src/index.js
 *   SELECT'e `tur` kolonu + satirOzeti'ye aktarim): fiziksel uruntde malzeme ve renk carpani
 *   1,00'e SABITLENIR -> tutar DAIMA liste fiyati. RED (400) DEGIL — cunku kalemleriCoz her
 *   satirda malzeme+renk ZORUNLU tutar ve fiziksel sayfada bunlari DEGISTIRECEK bir UI YOKTUR:
 *   red, musterinin ONARAMAYACAGI olu bir sepet birakirdi. Liste fiyati zaten sayfada,
 *   feed'de ve JSON-LD'de BEYAN EDILEN tutardir; sessiz degil, DOGRU olandir.
 *
 * IDDIALAR — hepsi KURUS (HTML jetonu sayilmaz):
 *   POZITIF  (yon="fiziksel")  : 3 secim x (baslat+prova) + gercek katalogdan 3 urun
 *   NEGATIF  (yon="3d")        : `tur`suz 3D urunde ONARIM ONCESI OLCULEN sayilar BIREBIR
 *   FAIL-CLOSED (yon="fail-closed"): `tur` YOK / bos / taninmayan deger -> 3D gibi davranir
 */
const FIZ_LISTE_KURUS = 100000;                       // "1.000 TL" liste fiyati
const FIZ_TABAN = { baslik: "Sinama urunu", kategori: "Marin", fiyat: "1.000 TL",
                    parametrik: 0, gorsel: "", konfigur: "" };
const FIZ_URUN = Object.assign({ id: "sinama-fiziksel-boya" }, FIZ_TABAN, { tur: "fiziksel" });
const UCB_URUN = Object.assign({ id: "sinama-3d-parca" }, FIZ_TABAN, { tur: "" });
const FIZ_SECIMLER = [["PLA", "Siyah", ""], ["PLA", "Diğer", "turuncu"],
                      ["ASA", "Diğer", "turuncu"]];
// 🔴 ONARIM ONCESI OLCULEN sayilar (regresyon capasi — 3D fiyatlamasi DEGISMEMELI).
const UCB_SPEC = { "PLA/Siyah": 100000, "PLA/Diğer": 115000, "ASA/Diğer": 184000 };
// `tur` alaninin TAM dize esitligiyle okundugunu kanitlayan degerler (fail-closed ekseni).
const FIZ_TANINMAYAN = ["", "Fiziksel", "FIZIKSEL", " fiziksel", "fiziksel ", "3d", "fiziksell",
                        0, 1, null, []];
const FIZ_GERCEK = URUNLER.filter((u) => u.tur === "fiziksel" && (u.fiyat || "").trim() &&
                                         !u.parametrik && !u.konfigur).slice(0, 3);

function fizKalem(id, malzeme, renk, ozel) {
  return { id: id, malzeme: malzeme, renk: renk, renk_ozel: ozel || "", adet: 1 };
}
function provaBirim(p) {
  return p.govde.satirlar && p.govde.satirlar[0] ? p.govde.satirlar[0].birim_kurus : null;
}

/** Fiziksel urun iddialari. Mutasyon altinda ILGILI yonun KIRMIZI yanmasi beklenir. */
async function fizikselIddialari(mod) {
  const s = [];
  for (const [malzeme, renk, ozel] of FIZ_SECIMLER) {
    const et = malzeme + "/" + renk;
    const k = [fizKalem(FIZ_URUN.id, malzeme, renk, ozel)];
    const b = await baslat(mod, [FIZ_URUN], k);
    const p = await prova(mod, [FIZ_URUN], k);
    s.push({ yon: "fiziksel", ad: "fiziksel " + et + " baslat = LISTE (" + FIZ_LISTE_KURUS + ")",
             ok: b.kod === 200 && b.birimKurus === FIZ_LISTE_KURUS, olculen: b.birimKurus });
    s.push({ yon: "fiziksel", ad: "fiziksel " + et + " prova = LISTE",
             ok: p.kod === 200 && provaBirim(p) === FIZ_LISTE_KURUS, olculen: provaBirim(p) });
  }
  for (const u of FIZ_GERCEK) {
    const liste = SECENEK.fiyatSayisi(u.fiyat) * 100;
    const b = await baslat(mod, [d1Satiri(u)],
                           [fizKalem(u.id, "ASA", "Diğer", "turuncu")]);
    s.push({ yon: "fiziksel", ad: "GERCEK katalog " + u.id + " ASA/Diğer = " + liste,
             ok: b.kod === 200 && b.birimKurus === liste, olculen: b.birimKurus });
  }
  for (const [malzeme, renk, ozel] of FIZ_SECIMLER) {
    const et = malzeme + "/" + renk;
    const k = [fizKalem(UCB_URUN.id, malzeme, renk, ozel)];
    const b = await baslat(mod, [UCB_URUN], k);
    const p = await prova(mod, [UCB_URUN], k);
    s.push({ yon: "3d", ad: "3D " + et + " baslat = " + UCB_SPEC[et] + " (DEGISMEDI)",
             ok: b.kod === 200 && b.birimKurus === UCB_SPEC[et], olculen: b.birimKurus });
    s.push({ yon: "3d", ad: "3D " + et + " prova = " + UCB_SPEC[et],
             ok: p.kod === 200 && provaBirim(p) === UCB_SPEC[et], olculen: provaBirim(p) });
  }
  // id kalibi /^[a-z0-9-]{1,120}$/ ile SINIRLI (kalemleriCoz) -> id'yi SIRA NUMARASINDAN uret;
  // `tur` degerinin kendisini id'ye gomsek kalem "gecersiz-kalem" ile reddedilir ve iddia
  // yanlis sebepten yesil/kirmizi olurdu.
  for (let i = 0; i < FIZ_TANINMAYAN.length; i += 1) {
    const t = FIZ_TANINMAYAN[i];
    const satir = Object.assign({ id: "sinama-tur-" + i }, FIZ_TABAN, { tur: t });
    const b = await baslat(mod, [satir], [fizKalem(satir.id, "ASA", "Diğer", "turuncu")]);
    s.push({ yon: "fail-closed", ad: "tur=" + JSON.stringify(t) + " -> 3D gibi (" +
                                     UCB_SPEC["ASA/Diğer"] + ")",
             ok: b.kod === 200 && b.birimKurus === UCB_SPEC["ASA/Diğer"], olculen: b.birimKurus });
  }
  {   // `tur` ALANI HIC YOK (kolon eklenmeden onceki D1 satiri)
    const satir = Object.assign({ id: "sinama-tursuz" }, FIZ_TABAN);
    const b = await baslat(mod, [satir], [fizKalem(satir.id, "ASA", "Diğer", "turuncu")]);
    s.push({ yon: "fail-closed", ad: "tur ALANI YOK -> 3D gibi",
             ok: b.kod === 200 && b.birimKurus === UCB_SPEC["ASA/Diğer"], olculen: b.birimKurus });
  }
  {   // `tur` KOLONU D1 semasinda YOK -> SELECT patlar, merdiven daralir. IKI iddia:
      //   (a) fiziksel urun BUGUNKU davranisa duser (regresyon 0, fail-closed),
      //   (b) `konfigur` kolonu YAN HASAR GORMEZ (konfigur kalemi hala DOGRU fiyatlanir) —
      //       tek listede olsalardi konfigur kalemleri de 400'e duserdi.
    const b = await baslat(mod, [FIZ_URUN], [fizKalem(FIZ_URUN.id, "ASA", "Diğer", "turuncu")],
                           ["tur"]);
    s.push({ yon: "fail-closed", ad: "`tur` KOLONU YOK -> bugunku davranis (" +
                                     UCB_SPEC["ASA/Diğer"] + ")",
             ok: b.kod === 200 && b.birimKurus === UCB_SPEC["ASA/Diğer"], olculen: b.birimKurus });
    const ku = KONFIGUR_URUNLER[0];
    const kb = await baslat(mod, [d1Satiri(ku)],
                            [{ id: ku.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                               parametreler: { boy_mm: 150 } }], ["tur"]);
    const beklenen = FRONT.fiyatKurus(ku.konfigur, FRONT.boyDuzelt(ku.konfigur, 150),
                                      (ku.konfigur.malzemeler.find((m) => m.ad === "PLA") || {}).katsayi);
    s.push({ yon: "fail-closed", ad: "`tur` kolonu yokken KONFIGUR kalemi hala dogru (" +
                                     beklenen + ")",
             ok: kb.kod === 200 && kb.birimKurus === beklenen, olculen: kb.birimKurus });
  }
  return s;
}

baslik("== 10) FIZIKSEL URUN — malzeme/renk carpani UYGULANMAZ (tutar = LISTE fiyati) ==");
{
  if (FIZ_GERCEK.length === 0) {
    kirmizi += 1;
    ham.push("    ❌ ÖLÇÜLEMEDİ: katalogda `tur:\"fiziksel\"` urun YOK — iddia OLU kalir");
  }
  const iddia = await fizikselIddialari(YENI);
  const kalan = iddia.filter((i) => !i.ok);
  const say = (y) => iddia.filter((i) => i.yon === y).length;
  not("katalogda fiziksel urun: " + URUNLER.filter((u) => u.tur === "fiziksel").length +
      " (iddiada ornek: " + FIZ_GERCEK.length + ")");
  not("iddia: " + iddia.length + " (POZITIF fiziksel " + say("fiziksel") + " · NEGATIF 3D " +
      say("3d") + " · FAIL-CLOSED " + say("fail-closed") + ") — kalan: " + kalan.length);
  kalan.slice(0, 12).forEach((i) => ham.push("    ❌ " + i.ad + " (olculen: " + i.olculen + ")"));
  if (kalan.length) { kirmizi += 1; ham.push("  ❌ KALDI — fiziksel urun carpani"); }
  else {
    ham.push("  ✅ GECTI — fiziksel urun DAIMA " + FIZ_LISTE_KURUS + " krs; 3D fiyatlamasi " +
             "onarim oncesiyle BIREBIR (100000/115000/184000)");
  }
}

// ============================ 11) FIS EKSENI — fiziksel siparis "ASA / turuncu" DEMEZ
/**
 * NEDEN VAR (bagimsiz curutucu bulgusu, 1 Agu): fiyat duzeltildikten SONRA bile siparis
 * ARTEFAKTLARI malzeme/renk beyanini tasiyordu — D1 INSERT `..., "ASA", "turuncu", ...`,
 * iyzico kalem adi "Tekne boyasi (ASA, turuncu)", Telegram "— ASA / turuncu", e-posta
 * hucresi "ASA / turuncu". Yani FIS, tahsil edilen liste fiyatiyla CELISIYORDU. Metin
 * susturmasi (satirOzeti) yalniz SEPET PANELINE ulasiyordu; siparis kaydina ULASMIYORDU
 * ve o iddia OLU idi (susturmayi geri alan mutant TUM kapilardan yesil geciyordu).
 *
 * KARAR TEK NOKTADA: shop/src/index.js sepetiFiyatla fiziksel kalemde satira malzeme/renk
 * YAZMAZ + `tur:"fiziksel"` isaretini koyar; asagi akistaki yuzeyler yalnizca BICIMLEYICIDIR.
 * Bu set o karari DORT YUZEYDE birden olcer ve 3D siparisinde alanlarin AYNEN durdugunu
 * ayrica iddia eder (regresyon nobetcisi).
 */
const FIS_MALZEME = "ASA";
const FIS_RENK_OZEL = "turuncu";

/** Verilen dizinden (temp modul agaci) eposta.js — fis metninin DORDUNCU yuzeyi. */
async function epostaYukle(dizin) {
  sayac += 1;
  return await import(pathToFileURL(path.join(dizin, "eposta.js")).href + "?s=" + sayac);
}
const EPOSTA_DOKUM = { tutarKurus: 100000, kargoKurus: 25000, tahsilatKurus: 125000,
                       kdvKurus: 20833 };
const EPOSTA_SIPARIS = { siparis_no: "PR-TEST-FIS", musteri_ad: "Test",
                         musteri_adres: "Test adres", musteri_eposta: "t@pruvo3d.com" };

/** `insertArg` icinde metnin ARGUMAN olarak (kolon degeri) gecip gecmedigi. `urunler` JSON
 *  dizesi de bir argumandir; onu AYIRIRIZ, cunku satir JSON'u ayrica iddia edilir. */
function kolonArgIceriyorMu(insertArg, metin) {
  return (insertArg || []).some((x) => typeof x === "string" && !x.startsWith("[") &&
                                       x.split("+").includes(metin));
}
function istekIceriyorMu(istekler, parca, metin) {
  return (istekler || []).some((i) => i.url.includes(parca) && i.govde.includes(metin));
}

async function fisIddialari(mod, epostaMod) {
  const s = [];
  const vakalar = [
    { yon: "fis-fiziksel", ad: "FIZIKSEL", urun: FIZ_URUN, beyanVar: false },
    { yon: "fis-3d", ad: "3D", urun: UCB_URUN, beyanVar: true },
  ];
  for (const v of vakalar) {
    const b = await baslat(mod, [v.urun],
      [fizKalem(v.urun.id, FIS_MALZEME, "Diğer", FIS_RENK_OZEL)]);
    const satir = b.satir || {};
    const bekle = (ad, olculen, dogru) =>
      s.push({ yon: v.yon, ad: v.ad + " " + ad, ok: olculen === dogru, olculen: olculen });
    // 1) D1 `siparisler.urunler` (satir JSON'u) — uretim/yonetim ekraninin kaynagi
    bekle("satir.malzeme", satir.malzeme, v.beyanVar ? FIS_MALZEME : "");
    bekle("satir.renk_ozel", satir.renk_ozel, v.beyanVar ? FIS_RENK_OZEL : "");
    bekle("satir.renk", satir.renk, v.beyanVar ? "Diğer" : "");
    bekle("satir.tur isareti", satir.tur || "", v.beyanVar ? "" : "fiziksel");
    // 2) D1 `siparisler.filament` / `.renk` KOLONLARI
    bekle("D1 filament kolonu", kolonArgIceriyorMu(b.insertArg, FIS_MALZEME), v.beyanVar);
    bekle("D1 renk kolonu", kolonArgIceriyorMu(b.insertArg, FIS_RENK_OZEL), v.beyanVar);
    // 3) iyzico basketItems kalem ADI (musterinin dekontunda gordugu metin)
    bekle("iyzico kalem adi malzeme", istekIceriyorMu(b.istekler, "iyzico", FIS_MALZEME),
          v.beyanVar);
    bekle("iyzico kalem adi renk", istekIceriyorMu(b.istekler, "iyzico", FIS_RENK_OZEL),
          v.beyanVar);
    // 4) Telegram bildirimi — /baslat'ta YALNIZ havale kolunda cikar (kart yolunda bildirim
    //    /donus'tadir). AYRI bir cagri gerekir; havaleMesaji ve siparisMesaji AYNI
    //    bicimleyiciyi (kalemSecimi) kullanir, o yuzden havale kolu ikisini de temsil eder.
    const h = await baslat(mod, [v.urun],
      [fizKalem(v.urun.id, FIS_MALZEME, "Diğer", FIS_RENK_OZEL)], undefined, "havale");
    s.push({ yon: v.yon, ad: v.ad + " havale kolu 200 (telegram olculebilsin)",
             ok: h.kod === 200, olculen: h.kod });
    s.push({ yon: v.yon, ad: v.ad + " telegram bildirimi CIKTI (olu iddia degil)",
             ok: (h.istekler || []).some((i) => i.url.includes("telegram")),
             olculen: (h.istekler || []).map((i) => i.url.split("/")[2]).join(",") });
    bekle("telegram metni malzeme", istekIceriyorMu(h.istekler, "telegram", FIS_MALZEME),
          v.beyanVar);
    bekle("telegram metni renk", istekIceriyorMu(h.istekler, "telegram", FIS_RENK_OZEL),
          v.beyanVar);
    // 5) e-posta satir tablosu (GERCEK eposta.js, ayni satir objesiyle)
    const html = epostaMod.onayEpostasiHtml(EPOSTA_SIPARIS, [satir], EPOSTA_DOKUM, false);
    bekle("e-posta malzeme", html.includes(FIS_MALZEME), v.beyanVar);
    bekle("e-posta renk", html.includes(FIS_RENK_OZEL), v.beyanVar);
    // Fiziksel fisin BOS degil, ANLASILIR olmasi: hucre "—" ile doldurulur (yarim beyan yok)
    if (!v.beyanVar) {
      bekle("e-posta hucresi '—' (yarim beyan yok)", html.includes(">—</td>"), true);
      bekle("e-posta 'ASA / ' yarim beyan YOK", html.includes(FIS_MALZEME + " / "), false);
    }
    // Tutar her iki halde de DEGISMEZ (fis ekseni fiyati ETKILEMEZ)
    bekle("tutar (krs)", b.birimKurus, v.beyanVar ? UCB_SPEC["ASA/Diğer"] : FIZ_LISTE_KURUS);
  }
  return s;
}

// ==================== 11b) BICIM IDDIALARI — "kelime var mi" DEGIL "yapiya uyuyor mu"
/**
 * 🔴 NOBETCI BORCU (1 Agu, kayitli): set 11'in UC ekseni KELIME ariyordu, BICIM degil —
 * (1) iyzico kalem adi, (2) D1 filament/renk kolonlari, (3) yonetim ekraninin fiziksel kolu
 * icin HIC iddia yoktu. Bugunku davranis DOGRUYDU; korumasiz olan GELECEK regresyondu.
 *
 * KELIME IDDIASININ KOR NOKTASI (olculdu, asagidaki M15/M16/M17 mutantlari):
 *   · "ASA" hala govdede geciyor ama ayrac ", " -> " / " oldu           -> kelime YESIL
 *   · fiziksel kalemde bos parantez basiliyor ("Sinama urunu ()")       -> kelime YESIL
 *   · kolon "ASA+" oluyor (bos beyan elenmiyor) ya da "ASA+ASA"         -> kelime YESIL
 *   · filament ve renk KOLONLARI YER DEGISTIRIYOR                        -> kelime YESIL
 *   · yonetim ekraninda `tur` alani JSON'dan tamamen dusuyor             -> iddia YOKTU
 * Hepsi de siparis kaydini/fisi/uretim ekranini BOZAR. Asagidaki iddialar SEKLE bakar:
 * tam dize esitligi, parantez yapisi, kolon dilimlenmesi, alan TIPI ve alanlar arasi
 * TUTARLILIK (isaret <-> bos beyan). "Icinde su kelime var mi" HICBIR yerde kullanilmaz.
 */
const BICIM_BASLIK = FIZ_TABAN.baslik;          // "Sinama urunu" — fikstur basligi
const UCB_URUN2 = Object.assign({ id: "sinama-3d-parca-iki" }, FIZ_TABAN, { tur: "" });
const YONET_ANAHTAR = "test-bicim-yonet-anahtari";
/** Baski (uretim) onerisi SEKLI — yonet.js BASKI_FALLBACK + genel cumle. Fiziksel kalemde
 *  bu SEKILDE bir metin cikmasi "boya kutusunu URETIYORUZ" demektir. */
const BASKI_ONERI_SEKLI = /^Genel öneri:|^Malzemeye uygun genel/;
/** kolonBirlestir sozlesmesi: BOS ya da "+" ile birlesmis BOS OLMAYAN parcalar. */
const KOLON_SEKLI = /^$|^[^+]+(\+[^+]+)*$/;

function kalem(id, malzeme, renk, ozel, adet) {
  return { id: id, malzeme: malzeme, renk: renk, renk_ozel: ozel || "", adet: adet || 1 };
}

/** iyzico'ya GIDEN govdeden basketItems (urun kalemleri; kargo kalemi ELENIR). */
function iyzicoUrunKalemleri(istekler) {
  const i = (istekler || []).find((x) => x.url.includes("iyzico"));
  if (!i) { return null; }
  let g = null;
  try { g = JSON.parse(i.govde); } catch (e) { return null; }
  return (g.basketItems || []).filter((b) => b.id !== "gonderim");
}

/** INSERT'in filament/renk KOLONLARI — POZISYONDAN okunur (satir JSON'unun hemen ardindaki
 *  iki arguman; bkz. shop/src/index.js INSERT kolon sirasi). Kolonlarin YER DEGISTIRMESI
 *  ancak boyle yakalanir: "govdede su kelime geciyor mu" taramasi bunu GORMEZ. */
function insertKolonlari(insertArg) {
  const i = (insertArg || []).findIndex((x) => typeof x === "string" && x.startsWith("["));
  if (i < 0) { return null; }
  return { filament: insertArg[i + 1], renk: insertArg[i + 2] };
}

/** Yonetim ekraninin (/yonet/liste) D1'i: siparis satiri + urun satiri ayri SELECT'ler. */
function d1Yonet(siparisSatirlari, urunSatirlari) {
  return {
    prepare(sql) {
      const siparisMi = /FROM siparisler/.test(sql);
      return {
        bind(...arg) {
          return {
            async all() {
              return { results: siparisMi ? siparisSatirlari
                : (urunSatirlari || []).filter((u) => arg.includes(u.id)) };
            },
            async first() { return siparisMi ? (siparisSatirlari[0] || null) : null; },
            async run() { return { meta: { changes: 1 } }; },
          };
        },
      };
    },
  };
}

/** GERCEK akis: /baslat siparis satirini kurar -> ayni satir JSON'u yonetim ekranina girer. */
async function yonetKalemleri(mod, urun, k) {
  const b = await baslat(mod, [urun], [k]);
  const urunlerJson = (b.insertArg || []).find((x) => typeof x === "string" && x.startsWith("["));
  const env = Object.assign({}, ENV_TABAN, {
    YONET_ANAHTAR: YONET_ANAHTAR,
    KATALOG: d1Yonet([{ id: 1, siparis_no: "PR-TEST-YONET", tarih: "2026-08-01T00:00:00.000Z",
                        durum: "bekliyor", tutar_kurus: 100000, kargo_kurus: 0, kdv_kurus: 0,
                        odeme_yontemi: "kart", urunler: urunlerJson || "[]", kargo_firma: "",
                        kargo_kodu: "", durum_gecmisi: "[]", musteri_ad: "T", musteri_tel: "0",
                        musteri_eposta: "t@pruvo3d.com", musteri_adres: "A" }],
                     [{ id: urun.id, baski: "", parametrik: 0 }]),
  });
  const cevap = await mod.default.fetch(
    // Anahtar SORGU DIZESINDE DEGIL, X-Yonet-Anahtar BASLIGINDA gider: `?anahtar=` yolu
    // kaldirildi (tam URL erisim loglarina/gecmise/Referer'a yaziliyordu). Sorgu ile
    // cagrilirsa bu uc artik 404 doner ve BICIM ekseni sahte kirmizi yanar.
    new Request("https://pruvo3d.com/api/shop/yonet/liste",
                { headers: { "X-Yonet-Anahtar": YONET_ANAHTAR } }),
    env, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  const s = (govde.siparisler || [])[0] || {};
  return { kod: cevap.status, kalemler: s.kalemler || [] };
}

/** UC EKSENIN BICIM IDDIALARI. yon: "bicim-iyzico" | "bicim-kolon" | "bicim-yonet". */
async function bicimIddialari(mod) {
  const s = [];
  const ekle = (yon, ad, olculen, dogru) =>
    s.push({ yon: yon, ad: ad, ok: olculen === dogru, olculen: JSON.stringify(olculen) });

  // ---------- EKSEN 1: iyzico basketItems[].name BICIMI ----------
  // Sozlesme (shop/src/index.js): baslik + " (" + [secim, adet].join(", ") + ")".
  // secim = malzeme + ", " + renk; fiziksel kalemde secim YOK -> parantez YALNIZ adet icin
  // acilir, adet 1 ise parantez HIC acilmaz. TAM DIZE esitligi ile olculur.
  {
    const vaka = [
      ["3D adet=1", UCB_URUN, kalem(UCB_URUN.id, "ASA", "Diğer", "turuncu", 1),
       BICIM_BASLIK + " (ASA, turuncu)"],
      ["3D adet=3", UCB_URUN, kalem(UCB_URUN.id, "ASA", "Diğer", "turuncu", 3),
       BICIM_BASLIK + " (ASA, turuncu, 3 adet)"],
      ["FIZIKSEL adet=1", FIZ_URUN, kalem(FIZ_URUN.id, "ASA", "Diğer", "turuncu", 1),
       BICIM_BASLIK],
      ["FIZIKSEL adet=3", FIZ_URUN, kalem(FIZ_URUN.id, "ASA", "Diğer", "turuncu", 3),
       BICIM_BASLIK + " (3 adet)"],
    ];
    for (const [ad, urun, k, beklenen] of vaka) {
      const b = await baslat(mod, [urun], [k]);
      const kalemler = iyzicoUrunKalemleri(b.istekler);
      ekle("bicim-iyzico", "iyzico kalem sayisi (" + ad + ")",
           kalemler ? kalemler.length : null, 1);
      const ad_ = kalemler && kalemler[0] ? kalemler[0].name : null;
      ekle("bicim-iyzico", "iyzico ad TAM BICIM (" + ad + ")", ad_, beklenen);
      // YAPISAL (baslik metninden BAGIMSIZ) iddia: parantez ici virgul-parcalari.
      const m = /\(([^()]*)\)\s*$/.exec(ad_ || "");
      const parcalar = m ? m[1].split(", ") : [];
      ekle("bicim-iyzico", "parantez ici parca sayisi (" + ad + ")", parcalar.length,
           ad.indexOf("FIZIKSEL") === 0 ? (ad.indexOf("adet=3") > 0 ? 1 : 0)
                                        : (ad.indexOf("adet=3") > 0 ? 3 : 2));
      // BOS PARANTEZ YASAK: "()" hem musteriye anlamsiz hem bicim bozuk.
      ekle("bicim-iyzico", "bos parantez YOK (" + ad + ")", /\(\s*\)/.test(ad_ || ""), false);
      // Fiziksel kalemde parantez YALNIZ adet tasiyabilir (beyan parcasi GIREMEZ).
      if (ad.indexOf("FIZIKSEL") === 0) {
        ekle("bicim-iyzico", "fiziksel parantezinde YALNIZ adet parcasi (" + ad + ")",
             parcalar.every((p) => /^\d+ adet$/.test(p)), true);
      }
    }
  }

  // ---------- EKSEN 2: D1 siparisler.filament / .renk KOLON BICIMI ----------
  // Sozlesme (kolonBirlestir): BENZERSIZ + BOS OLMAYAN beyanlar, "+" ile. Kolonlar
  // POZISYONEL okunur -> yer degistirme de yakalanir.
  {
    const vaka = [
      ["yalniz FIZIKSEL", [FIZ_URUN], [kalem(FIZ_URUN.id, "ASA", "Diğer", "turuncu", 1)],
       "", ""],
      ["yalniz 3D", [UCB_URUN], [kalem(UCB_URUN.id, "ASA", "Diğer", "turuncu", 1)],
       "ASA", "turuncu"],
      // KARMA sepet: fiziksel satir kolona HICBIR SEY katmaz -> "ASA+" gibi ucu acik
      // dize OLUSMAZ. (Kelime taramasi "ASA+"yi da YESIL gecirirdi.)
      ["KARMA (fiziksel + 3D)", [FIZ_URUN, UCB_URUN],
       [kalem(FIZ_URUN.id, "PLA", "Siyah", "", 1),
        kalem(UCB_URUN.id, "ASA", "Diğer", "turuncu", 1)], "ASA", "turuncu"],
      // IKI 3D satiri: malzemeler AYRI -> "+" ile birlesir; renkler AYNI -> TEKRARLANMAZ.
      ["iki 3D (ayri malzeme, ayni renk)", [UCB_URUN, UCB_URUN2],
       [kalem(UCB_URUN.id, "ASA", "Diğer", "turuncu", 1),
        kalem(UCB_URUN2.id, "PLA", "Diğer", "turuncu", 1)], "ASA+PLA", "turuncu"],
    ];
    for (const [ad, urunler_, kalemler, bekFil, bekRenk] of vaka) {
      const b = await baslat(mod, urunler_, kalemler);
      const kol = insertKolonlari(b.insertArg) || {};
      ekle("bicim-kolon", "filament kolonu TAM BICIM (" + ad + ")", kol.filament, bekFil);
      ekle("bicim-kolon", "renk kolonu TAM BICIM (" + ad + ")", kol.renk, bekRenk);
      for (const [kad, deger] of [["filament", kol.filament], ["renk", kol.renk]]) {
        ekle("bicim-kolon", kad + " kolonu TIPI dize (" + ad + ")", typeof deger, "string");
        ekle("bicim-kolon", kad + " kolonu SEKLI (bos ya da '+' ile dolu parcalar) (" + ad + ")",
             KOLON_SEKLI.test(String(deger == null ? " " : deger)), true);
        const parca = String(deger || "").split("+").filter((x) => x !== "");
        ekle("bicim-kolon", kad + " kolonunda TEKRAR YOK (" + ad + ")",
             parca.length, new Set(parca).size);
      }
    }
  }

  // ---------- EKSEN 3: YONETIM EKRANI (/yonet/liste) fiziksel kolu ----------
  // 🔴 Bu eksende ONCEDEN HIC IDDIA YOKTU. Ekran, bos malzeme/renk hucresini "veri kayip"
  // mi "secim yok" mu diye AYIRT ETMEK icin `tur` alanina bakar -> alanin TIPI ve alanlar
  // arasi TUTARLILIGI bicim iddiasidir.
  {
    const vaka = [
      ["FIZIKSEL", FIZ_URUN, kalem(FIZ_URUN.id, "ASA", "Diğer", "turuncu", 1), "fiziksel"],
      ["3D", UCB_URUN, kalem(UCB_URUN.id, "ASA", "Diğer", "turuncu", 1), ""],
    ];
    for (const [ad, urun, k, bekTur] of vaka) {
      const y = await yonetKalemleri(mod, urun, k);
      ekle("bicim-yonet", "liste HTTP (" + ad + ")", y.kod, 200);
      ekle("bicim-yonet", "kalem sayisi (" + ad + ")", y.kalemler.length, 1);
      const kk = y.kalemler[0] || {};
      // (a) ALAN VAR MI + TIPI DIZE MI (JSON'dan dusen alan "veri kayip" gibi okunur)
      ekle("bicim-yonet", "tur alani VAR (" + ad + ")", Object.prototype.hasOwnProperty.call(kk, "tur"), true);
      ekle("bicim-yonet", "tur alani TIPI dize (" + ad + ")", typeof kk.tur, "string");
      // (b) DEGERI IKI KANONIK HALDEN BIRI + dogru olan
      ekle("bicim-yonet", "tur kanonik deger (" + ad + ")", kk.tur, bekTur);
      // (c) TUTARLILIK: isaret <-> bos beyan. Ikisi ayrisirsa ekran YANLIS okur.
      ekle("bicim-yonet", "isaret <-> bos beyan TUTARLI (" + ad + ")",
           (kk.tur === "fiziksel") === (kk.malzeme === "" && kk.renk === ""), true);
      // (d) URETIM ONERISI hangi DALDAN geldi: fiziksel kalemde baski onerisi SEKLI CIKMAZ.
      ekle("bicim-yonet", "baski onerisi SEKLI (" + ad + ")",
           BASKI_ONERI_SEKLI.test(String(kk.baski_oneri || "")), bekTur !== "fiziksel");
    }
  }
  return s;
}

baslik("== 11) FIS EKSENI — fiziksel siparis kaydi/e-postasi malzeme-renk BEYAN ETMEZ ==");
{
  const epostaMod = await epostaYukle(YENI_DIZIN);
  const iddia = await fisIddialari(YENI, epostaMod);
  const kalan = iddia.filter((i) => !i.ok);
  not("iddia: " + iddia.length + " (fiziksel " + iddia.filter((i) => i.yon === "fis-fiziksel").length +
      " · 3D regresyon " + iddia.filter((i) => i.yon === "fis-3d").length + ") — kalan: " +
      kalan.length);
  not("olculen yuzeyler: D1 satir JSON'u · D1 filament/renk kolonlari · iyzico kalem adi · " +
      "Telegram metni · e-posta satir tablosu (gercek eposta.js)");
  kalan.slice(0, 12).forEach((i) => ham.push("    ❌ " + i.ad + " (olculen: " + i.olculen + ")"));
  if (kalan.length) { kirmizi += 1; ham.push("  ❌ KALDI — fis ekseni"); }
  else {
    ham.push("  ✅ GECTI — fiziksel siparis hicbir yuzeyde 'ASA'/'turuncu' demiyor; " +
             "3D siparisinde DORT yuzeyde de AYNEN duruyor");
  }
}

baslik("== 11b) BICIM EKSENI — iyzico kalem adi · D1 kolonlari · yonetim ekrani (KELIME DEGIL) ==");
{
  const iddia = await bicimIddialari(YENI);
  const kalan = iddia.filter((i) => !i.ok);
  const say = (y) => iddia.filter((i) => i.yon === y).length;
  not("iddia: " + iddia.length + " (iyzico ad " + say("bicim-iyzico") + " · D1 kolon " +
      say("bicim-kolon") + " · yonetim ekrani " + say("bicim-yonet") + ") — kalan: " +
      kalan.length);
  not("olcum SEKLE bakar: tam dize esitligi · parantez parca sayisi · kolon dilimlenmesi " +
      "(tekrar/bos parca/pozisyon) · alan tipi · isaret<->bos beyan tutarliligi");
  kalan.slice(0, 12).forEach((i) => ham.push("    ❌ " + i.ad + " (olculen: " + i.olculen + ")"));
  if (kalan.length) { kirmizi += 1; ham.push("  ❌ KALDI — bicim ekseni"); }
  else {
    ham.push("  ✅ GECTI — uc yuzeyin de BICIMI sozlesmeye uyuyor (M15/M16/M17 bunu olcer)");
  }
}

// ============================================================ 9) SERT TAVAN (yardimcilar)
const TAVAN_URUN = KONFIGUR_URUNLER[0];
const TAVAN_SATIR = [d1Satiri(TAVAN_URUN)];
const TAVAN_SEPET = [{ id: TAVAN_URUN.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                       parametreler: { boy_mm: 150 } }];

// ------------------------------------------------- 9.6 YANLIS-GUVENCE NOBETCISI (metin)
/**
 * 🔴 NE KORUR: 29 Tem'de olculen gercek sudur — native ratelimit sayaci IP basina TEK sayac
 * tutmaz, baglanti uc-noktasi/kolo basina BOLUNUR; efektif tavan yapilandirilan degerin birkac
 * kati olabilir (60 yapilandirmasinda ilk 429 265. istekte). Bu nobetci, dokumana/yorumlara
 * "sert tavan / kesin sinir / IP basina garanti" gibi CURUTULMUS guvencelerin GERI KONMASINI
 * bloklar. Bu depoda "kapi var sanip korumasiz kalma" sinifi defalarca olculdu.
 *
 * KURAL (basit ve yazili): yasak kaliplardan biri gectiginde, IDDIANIN KENDISINE YAKIN bir
 * yerde acik OLUMSUZLAMA sozcugu bulunmalidir (or. "GARANTILI ust sinir DEGILDIR"). Yoksa
 * bulgudur. "Yakin" = asagidaki MUAF_* penceresi (iddianin onunde 1 satir/120 karakter,
 * ardinda 2 satir/200 karakter) — 29 Tem curutmesinde olculdu ki CUMLE geneli ("." ayraci)
 * wrangler.toml'da 1059 karakterlik bloklar uretiyor ve blogun HERHANGI bir yerindeki tek bir
 * "DEGIL" tum blogu muaf kiliyordu (dosya SONUNA eklenen "IP basina SERT TAVAN" sessiz gecti).
 *
 * ⚠️ SINIR — DURUSTCE: bu ORUNTU TABANLI bir DISIPLIN cihazidir, guvenlik siniri DEGIL ve TAM
 * KAPSAMA GARANTI ETMEZ. Yasak anlami listede olmayan bir esanlamla yazan, ya da iddianin
 * yanina "degil" iliştiren metin gecer. Amaci: kazara/iyi niyetli yanlis guvencenin geri
 * sizmasini durdurmak. Recall sonsuza kadar kovalanmaz — olculen kacaklar kapatilir, kalani
 * bu notta ve 9.6 ciktisinda YAZILI kalir.
 */
const YASAK_GUVENCE = [
  // \bsert: "INSERT" alt-dizesi yanlis-pozitif uretmesin (INSERT ... tavan).
  { ad: "sert tavan iddiasi", re: /\bsert[^.\n]{0,14}tavan|\btavan[^.\n]{0,14}\bsert/i },
  { ad: "kesin/garantili tavan-sinir iddiasi",
    re: /(kesin|garanti\w*)[^.\n]{0,20}(tavan|sinir)|(tavan|sinir)[^.\n]{0,20}garanti\w*/i },
  { ad: "hesap duzeyinde TEK sayac iddiasi (29 Tem'de CURUTULDU)",
    re: /hesap\s+duzeyinde\s+say/i },
  { ad: "IP basina tek sayac / en fazla N iddiasi",
    re: /\bIP\s+basina\s+(TEK|en\s+fazla|kesin|sert|garanti)/i },
  // --- asagidakiler 29 Tem curutmesinde OLCULEN kacaklardir (bagimsiz curutucu buldu) ---
  { ad: "IP -> ust sinir / en fazla / tavan iddiasi (\"Her IP icin ust sinir N\")",
    re: /\bIP\b[^.\n]{0,20}(ust\s+sinir|en\s+fazla|tavan)/i },
  { ad: "TEK/global sayac iddiasi (olculen gercek: sayac BOLUNUYOR)",
    re: /\b(tek|global)\s+sayac|global\s+olarak\s+say/i },
  { ad: "kota/limit GARANTI ALTINA ALMA iddiasi",
    re: /garanti\s+altina\s+al/i },
];

/**
 * IKINCI AILE — IKI FAKTORLU YAKINLIK (30 Tem, S2).
 *
 * OLCULEN KUSUR: yukaridaki liste TEK FAKTORLU (tek bir kalip). 20 gercekci esanlam
 * cumlesi denendi -> RECALL 0/20. Kacan ornekler: "Dakikada 60 istekle sinirlidir,
 * asilamaz." · "Istek sayisi 60'i gecemez." · "Hicbir istemci 60 istegi asamaz." ·
 * "Rate limit hesap genelinde tek BIR sayac kullanir." (araya giren "bir" kelimesi
 * `tek\s+sayac` kalibini kiriyor) · "IP basina dakikada 60 istek GARANTI edilir."
 * Liste uzatarak kapatmak PARSER TAKLIDI olurdu (bkz. [[kapi-disiplin-ilkesi]]:
 * sonsuz liste tutulmaz).
 *
 * COZUM: kalip EZBERLEMEK yerine IKI FAKTOR ARANIR:
 *   (1) MUTLAKLIK sozcugu  ("asilamaz", "gecemez", "kesin", "garanti", "mutlak",
 *       "en cok", "ust sinir", "tavan", "tek sayac", "bolunmez", ...)
 *   (2) HIZ SINIRI KONUSU  (IP / istek / sayac / rate limit / limiter / kota / dk)
 * IKISI DE AYNI SATIRDA ve birbirine YAKIN (<=IKILI_YAKINLIK karakter) olacak.
 * Tek basina "en cok 4 gorsel" ya da "fiyat tavani 150000 kurus" YANMAZ (konu yok);
 * tek basina "istek sayisi" da yanmaz (mutlaklik yok). Muafiyet (olumsuzlama) penceresi
 * BIRINCI aile ile AYNI — "garantili ust sinir DEGILDIR" gecmeye devam eder.
 *
 * ⚠️ SINIR — DURUSTCE: bu da TAM KAPSAMA DEGIL. Iki faktorden birini de kullanmayan bir
 * yazim (or. yalnizca sayi vererek "60/dk" demek) gecer. Amac degismedi: kazara/iyi niyetli
 * yanlis guvencenin geri sizmasini durdurmak.
 */
const MUTLAKLIK = [
  { ad: "asilamaz/gecemez sinifi", re: /\b(asilamaz|asilmaz|asamaz|asamazsiniz|gecemez|gecilemez|asilmasi\s+mumkun\s+olmayan|imkansiz)\b/i },
  { ad: "mutlak/kesin/kati sinifi", re: /\b(mutlak|mutlaka|kesin|kesindir|kesinlikle|kati)\b/i },
  { ad: "garanti sinifi", re: /\bgaranti\w*/i },
  { ad: "sert/ust-sinir/tavan sinifi", re: /\b(sert|ust\s+sinir|tavan|en\s+cok|en\s+fazla)\b/i },
  { ad: "tek/ortak/bolunmez sayac sinifi", re: /\b(tek\s+\w+\s+sayac|tek\s+sayac|ortak\w*|global|bolunmez|paylasir|tek\s+merkez\w*)\b/i },
  { ad: "her kosulda sinifi", re: /\b(her\s+kosulda|hicbir\s+kosulda|her\s+zaman|degismez)\b/i },
];
/** Konu = HIZ SINIRI. Bu terimlerden biri yoksa mutlaklik sozcugu MASUMDUR (sepet kalemi,
 *  gorsel sayisi, fiyat tavani, metin uzunlugu...). */
const HIZ_KONUSU = /(\bIP\b|iste[gkl]\w*|sayac\w*|limit\w*|kota\w*|\/\s*dk\b|dakikada|dakika\s+basina)/i;
const IKILI_YAKINLIK = 60;
// YOKTUR: 30 Tem'de OLCULEN yanlis-pozitif — "sert tavan YOKTUR" (dogru ifade!) bulgu
// sayiliyordu, cunku listede yalniz YOK ve YOKTU vardi.
const OLUMSUZ = /\b(DEGIL|DEGILDIR|DEGILDI|YOK|YOKTU|YOKTUR|YAPILAMAZ|EDILMEZ|EDILEMEZ|TUTMAZ|TUTMUYOR|OLMAZ)\b/i;

// Muafiyet penceresi: olumsuzlama IDDIAYA YAKIN olmali. Hem karakter hem SATIR tavani var —
// karakter tavani tek basina dosya icerigine bagli kazalar uretir (dosya sonundaki alakasiz
// bir "DEGIL" iddiayi muaf kilabilir), satir tavani onu sinirlar.
const MUAF_GERI_KARAKTER = 120, MUAF_GERI_SATIR = 1;
const MUAF_ILERI_KARAKTER = 200, MUAF_ILERI_SATIR = 2;

/** Iddianin cevresindeki muafiyet penceresini dondurur (karakter VE satir tavaniyla kirpilmis). */
function muafPencere(metin, bas, son) {
  let i = bas, geriSatir = 0;
  const dip = Math.max(0, bas - MUAF_GERI_KARAKTER);
  while (i > dip) {
    if (metin[i - 1] === "\n") {
      if (geriSatir >= MUAF_GERI_SATIR) { break; }
      geriSatir += 1;
    }
    i -= 1;
  }
  let j = son, ileriSatir = 0;
  const tepe = Math.min(metin.length, son + MUAF_ILERI_KARAKTER);
  while (j < tepe) {
    if (metin[j] === "\n") {
      if (ileriSatir >= MUAF_ILERI_SATIR) { break; }
      ileriSatir += 1;
    }
    j += 1;
  }
  return metin.slice(i, j);
}

/** Eslesmenin cevresindeki AYNI SATIR penceresi (+-cap karakter, satir sinirinda durur).
 *  Iki faktorlu kural bunu kullanir: mutlaklik sozcugu ile hiz-sinir konusu AYNI satirda
 *  ve yakin olmali; satir atlayan tesadufi eslesme bulgu sayilmaz. */
function ayniSatirPencere(metin, bas, son, cap) {
  let i = bas;
  const dip = Math.max(0, bas - cap);
  while (i > dip && metin[i - 1] !== "\n") { i -= 1; }
  let j = son;
  const tepe = Math.min(metin.length, son + cap);
  while (j < tepe && metin[j] !== "\n") { j += 1; }
  return metin.slice(i, j);
}

/** dosyalar: [{ad, metin}] — M8 mutanti AYNI fonksiyonu mutant metinle cagirir.
 *  Metin BUTUN halde taranir (cumleye bolunmez); muafiyet yalnizca muafPencere kadar genistir. */
function yanlisGuvenceTara(dosyalar) {
  const bulgu = [];
  for (const d of dosyalar) {
    // --- IKINCI AILE: MUTLAKLIK x HIZ KONUSU yakinligi (tek faktorlu liste kacaklari) ---
    for (const p of MUTLAKLIK) {
      const re = new RegExp(p.re.source, "gi");
      let m;
      while ((m = re.exec(d.metin)) !== null) {
        if (m[0].length === 0) { re.lastIndex += 1; continue; }
        const son = m.index + m[0].length;
        if (!HIZ_KONUSU.test(ayniSatirPencere(d.metin, m.index, son, IKILI_YAKINLIK))) { continue; }
        if (OLUMSUZ.test(muafPencere(d.metin, m.index, son))) { continue; }
        bulgu.push(d.ad + " — iki-faktorlu (" + p.ad + " + hiz sinir konusu): \"" +
                   ayniSatirPencere(d.metin, m.index, son, 30)
                     .replace(/\s+/g, " ").trim().slice(0, 80) + "\"");
      }
    }
    for (const p of YASAK_GUVENCE) {
      const re = new RegExp(p.re.source, "gi");
      let m;
      while ((m = re.exec(d.metin)) !== null) {
        if (m[0].length === 0) { re.lastIndex += 1; continue; }
        if (OLUMSUZ.test(muafPencere(d.metin, m.index, m.index + m[0].length))) { continue; }
        bulgu.push(d.ad + " — " + p.ad + ': "' +
                   m[0].replace(/\s+/g, " ").trim().slice(0, 60) + '"');
      }
    }
  }
  return { taranan: dosyalar.length, bulgu };
}

/** Taranan dosyalar: worker kaynagi + wrangler beyani + shop dokumani.
 *  Bu test dosyasi TARANMAZ — yasak kaliplari VERI olarak tasir (kendini yakalardi). */
function guvenceDosyalari() {
  const liste = [{ ad: "shop/wrangler.toml", metin: WRANGLER }];
  for (const ad of fs.readdirSync(SRC)) {
    if (ad.endsWith(".js")) {
      liste.push({ ad: "shop/src/" + ad, metin: fs.readFileSync(path.join(SRC, ad), "utf8") });
    }
  }
  const kurulum = path.join(SHOP, "KURULUM.md");
  if (fs.existsSync(kurulum)) {
    liste.push({ ad: "shop/KURULUM.md", metin: fs.readFileSync(kurulum, "utf8") });
  }
  return liste;
}
const GUVENCE_DOSYALARI = guvenceDosyalari();

// ---- KAPSAM KORPUSU (set 9.7 + mutant M10 AYNI diziyi kullanir; ikinci kopya YOK) --------
// NEDEN: 9.6 uzun sure "oruntu tabanli, esanlam gecer" diye YAZILI bir acik tasidi ama
// ACIGIN BUYUKLUGU HIC OLCULMEDI. 30 Tem'de olculdu: tek-faktorlu (eski) haliyle asagidaki
// 20 gercekci esanlam cumlesinin 20'si de GECIYORDU -> recall 0/20. Iki faktorlu aile
// eklendikten sonra 17/20. Bu korpus o sayiyi CI'da SABITLER: recall duserse KIRMIZI.
const YANLIS_KORPUS = [
  "Her IP dakikada en cok 60 istek yapabilir.",
  "Dakikada 60 istekle sinirlidir, asilamaz.",
  "Bu ayar 60 istegi asmayi imkansiz kilar.",
  "Sayac tum kolo'larda ORTAKTIR.",
  "60/dk kesin olarak uygulanir.",
  "IP basina dakikada 60 istek GARANTI edilir.",
  "Rate limit hesap genelinde tek bir sayac kullanir.",
  "Istek sayisi 60'i gecemez.",
  "Kati bir ust sinir uygular.",                          // KACIYOR (hiz-sinir konusu yok)
  "Native limiter mutlak tavani zorlar.",
  "Ust sinir asilmaz.",                                   // KACIYOR (hiz-sinir konusu yok)
  "60 istek/dk kotasi kesindir.",
  "Sayac bolunmez, tek merkezde tutulur.",
  "Hicbir istemci 60 istegi asamaz.",
  "Limiter her IP icin ayni sayaci paylasir.",
  "Bu deger asilmasi mumkun olmayan bir siniridir.",      // KACIYOR (hiz-sinir konusu yok)
  "60 istek/dk her kosulda uygulanir.",
  "Istekler IP bazinda kesin sekilde sayilir.",
  "Dakika basina 60 istek tavani DEGISMEZ.",
  "Cloudflare bu limiti global olarak uygular.",
];
// MASUM: bu depoda GERCEKTEN gecen, dogru ve alakasiz ifadeler. Biri bile yanarsa kapi
// sahte kirmizi verir ve TUM EKIBIN yayini durur -> 0 olmak ZORUNDA.
const MASUM_KORPUS = [
  "Sepette en fazla 30 kalem olabilir (AYAR.sepet_en_cok_kalem).",
  "click-id en cok 512 karakter olabilir; daha uzunu reddedilir.",
  "Fiyat tavani 150000 kurus; kapaksiz formul asarsa sonuc kirpilir.",
  "Adet 1-99 araliginda; aralik disi istek REDDEDILIR.",
  "Bu uc bir guvenlik siniri DEGILDIR; yapilandirilan deger GARANTILI ust sinir DEGIL.",
  "Limiter sayaci baglanti uc-noktasi basina BOLUNUYOR; sert tavan YOKTUR.",
  "Metin en fazla 24 karakter olabilir (yazi alani siniri).",
  "Kargo 250,00 TL; 2.500,00 TL ustu bedava.",
  "INSERT OR IGNORE ayni ref'i tekillestirir; tavan iddiasi burada YOK.",
  "En cok 4 gorsel gosterilir.",
  "Bu bir en iyi caba maliyet frenidir, garantili tavan DEGIL.",
  "Boy 60-300 mm araligina kirpilir; ust sinir disina cikilamaz.",
];
const RECALL_EN_AZ = 17;   // olculen deger; DUSURULMEZ (dusurmek = nobetciyi gevsetmek)

// ---- KACAK KIMLIGI (31 Tem 2026) — SAYI YETMEZ, HANGI CUMLE oldugu da SABITLENIR ----
// NEDEN: `yakalanan >= 17` esigi yalniz SAYIYI korur. Bir degisiklik bu uc kacaktan birini
// kapatip BASKA bir cumleyi acsa recall yine 17 kalir ve kapi hicbir sey demez — nobetci
// "17" derken korumadigi kume SESSIZCE degisir. Artik KACAN KUMENIN KENDISI beyan edilir.
//
// 🔴 31 TEM OLCUMU — bu uc kacak KAPATILAMADI, uc yol da SAYIYLA CURUTULDU (kopyada
// olculdu, canli dosyaya mutasyon uygulanmadi):
//   (A) HIZ_KONUSU'na "sinir\w*" eklemek -> recall 20/20 AMA masum korpus 2/12 yandi
//       ("...(yazi alani siniri)." ve "Boy 60-300 mm ... ust sinir disina cikilamaz.").
//   (B) "ayni satirda IKI FARKLI MUTLAKLIK sinifi" ailesi -> recall 19/20, masum 0/12,
//       AMA GERCEK dosyalarda 2 bulgu: shop/src/index.js ve shop/KURULUM.md'deki
//       KDV satiri ("Okan KESIN %20 ... tahsilat DEGISMEZ") — hiz siniriyla ILGISIZ.
//   (C) (B)'nin dar hali (ciftin bir uyesi "ust sinir/tavan" sinifi olmak zorunda) ->
//       recall 19/20, gercek dosyalar 0, masum 0/12; AMA dusmanca masum kumede 6
//       gercekci mesru cumlenin 3'u yandi ("Sepette en fazla 30 kalem olabilir; bu deger
//       kesindir." · "En cok 4 gorsel gosterilir, bu her zaman boyledir." · "Yazi alani
//       en fazla 24 karakter; bu sinir degismez.").
// KOK SEBEP: uc kacak da hiz siniri KONUSUNU hic anmiyor; izole bir cumle olarak MESRU bir
// tavan cumlesinden AYIRT EDILEMEZLER. Ayirt edici tek sey BAGLAM (hangi dosya/bolum), onu
// da korpus fiksturu bilerek soyuyor. Bu kapi deploy.yml'de `continue-on-error`SUZ kosuyor:
// yanlis-pozitif TUM EKIBIN yayinini durdurur -> 2 korpus cumlesi icin o riski almiyoruz.
// [[kapi-disiplin-ilkesi]] · [[kapi-kapsam-genisletme-tuzagi]]
const KACAK_BEYAN = [
  "Kati bir ust sinir uygular.",
  "Ust sinir asilmaz.",
  "Bu deger asilmasi mumkun olmayan bir siniridir.",
];

/** wrangler.toml beyan iddialari (M6 mutanti AYNI fonksiyonu mutant metinle cagirir). */
function beyanIddialari(tomlMetin, kodPencere) {
  const liste = unsafeBindingler(tomlMetin);
  const f = liste.find((b) => b.name === "FIYAT_RATE_LIMIT");
  const r = liste.find((b) => b.name === "REF_RATE_LIMIT");
  return [
    { ad: "wrangler.toml'da FIYAT_RATE_LIMIT BEYAN EDILMIS", ok: !!f,
      olculen: f ? "var" : "YOK" },
    { ad: "type = ratelimit (native binding)", ok: !!f && f.type === "ratelimit",
      olculen: f && f.type },
    { ad: "limit POZITIF ve SONLU", ok: !!f && f.limit > 0 && f.limit <= 10000,
      olculen: f && f.limit },
    { ad: "period 10 ya da 60 (CF baska deger kabul etmez)",
      ok: !!f && (f.period === 10 || f.period === 60), olculen: f && f.period },
    { ad: "/ref ile AYNI namespace_id DEGIL (kota paylasilmiyor)",
      ok: !!f && !!r && f.namespace_id !== r.namespace_id,
      olculen: (f && f.namespace_id) + " vs ref " + (r && r.namespace_id) },
    { ad: "/ref ile AYNI binding adi DEGIL", ok: !!f && !!r && f.name !== r.name,
      olculen: (f && f.name) + " vs " + (r && r.name) },
    { ad: "koddaki Retry-After (PROVA_PENCERE_SN) beyan edilen period ile AYNI",
      ok: !!f && Number.isFinite(kodPencere) && kodPencere === f.period,
      olculen: kodPencere + " vs beyan " + (f && f.period) },
  ];
}

/**
 * 🔴 COK-ISOLATE SENARYOSU — 29 Tem canli kirmizisinin birebir yeniden kurulumu.
 * HER istek AYRI bir modul ornegine gider (import cache-buster -> modul-duzeyi state SIFIR =
 * taze isolate); rate-limit binding'i ise TEK ve PAYLASILIR. Isolate-yerel Map sayaci bu
 * senaryoda HICBIR ZAMAN tetiklenmez (canlida olculen 40/40 HTTP 200); native binding tetikler.
 * OLCTUGU EKSEN: kodun binding'i her isolate'te cagirip kararina uymasi. Gercek dunyada
 * sayacin kolo basina bolunmesi BU SETIN KONUSU DEGIL (bkz. limiterKur dokumani + 9.2 notu).
 */
async function cokIsolate(dizin, adet, ip, limiter) {
  const kodlar = [];
  let yazma = 0, okuma = 0, agCagri = 0;
  for (let i = 0; i < adet; i++) {
    const mod = await modulYukle(dizin);           // TAZE ISOLATE
    const r = await prova(mod, TAVAN_SATIR, TAVAN_SEPET, ip, limiter);
    kodlar.push(r.kod);
    yazma += r.d1Yazma; okuma += r.d1Okuma; agCagri += r.agCagri;
  }
  return { kodlar, yazma, okuma, agCagri,
           ikiyuz: kodlar.filter((k) => k === 200).length,
           redd: kodlar.filter((k) => k === 429).length };
}

/** 429 YOLUNUN UCUZLUGU: cap tuketilir, sonraki 5 istegin sayaclari olculur (M7 ayni fonksiyon). */
async function ucuzlukOlcumu(mod, ip) {
  LIMITER.sifirla();
  for (let i = 0; i < GECEN; i++) { await prova(mod, TAVAN_SATIR, TAVAN_SEPET, ip); }
  const kodlar = [];
  let yazma = 0, okuma = 0, agCagri = 0, first = 0;
  for (let i = 0; i < 5; i++) {
    const r = await prova(mod, TAVAN_SATIR, TAVAN_SEPET, ip);
    kodlar.push(r.kod);
    yazma += r.d1Yazma; okuma += r.d1Okuma; agCagri += r.agCagri; first += r.d1First;
  }
  return { kodlar, yazma, okuma, agCagri, first };
}

// M5/M7 mutant kaynaklari — capa TEK YERDE (kod satiri degisirse mutasyon UYGULANAMADI der).
const TAVAN_CAPA =
  "  if (await provaHizSiniriAsildi(request, env)) { return cokIstek(env); }";
const TAVAN_M7 =
  "  if (await provaHizSiniriAsildi(request, env)) {\n" +
  "    await env.KATALOG.prepare(\"INSERT INTO siparisler (siparis_no) VALUES (?)\")" +
  ".bind(\"PR-M7\").run();\n" +
  "    await env.KATALOG.prepare(\"SELECT id FROM urunler WHERE id IN (?)\").bind(\"x\").all();\n" +
  "    await telegram(env, \"mutant 429 bildirimi\");\n" +
  "    return cokIstek(env);\n" +
  "  }";

const KOD_PENCERE = Number((calismaIndex.match(/const PROVA_PENCERE_SN = (\d+);/) || [])[1]);

baslik("== 9) HIZ SINIRI — native rate-limit binding DOGRU KULLANILIYOR (EN IYI CABA) ==");
{
  const hatalar = [];

  // ---- 9.1 BEYAN + KOD/BEYAN DRIFT ----
  const beyan = beyanIddialari(WRANGLER, KOD_PENCERE);
  const beyanKalan = beyan.filter((i) => !i.ok);
  not("9.1 BEYAN: " + beyan.length + " iddia — kalan " + beyanKalan.length +
      " | olculen: ad=FIYAT_RATE_LIMIT tur=" + FIYAT_BEYAN.type + " ns=" +
      FIYAT_BEYAN.namespace_id + " limit=" + FIYAT_BEYAN.limit + "/" +
      FIYAT_BEYAN.period + " sn, koddaki Retry-After=" + KOD_PENCERE);
  beyanKalan.forEach((i) => hatalar.push("9.1 " + i.ad + " (olculen: " + i.olculen + ")"));

  // ---- 9.2 COK-ISOLATE (asil kusur) ----
  LIMITER.sifirla();
  const ci = await cokIsolate(YENI_DIZIN, ILK_RED, "198.51.100.2");
  const ilk40 = ci.kodlar.slice(0, 40);
  not("9.2 COK-ISOLATE (her istek TAZE isolate, ayni IP, PAYLASILAN sahte sayac): " +
      ILK_RED + " istek -> 200:" + ci.ikiyuz + " / 429:" + ci.redd +
      " | ilk 429 = " + (ci.kodlar.indexOf(429) + 1) + ". istek (" + ILK_RED + " beklenir; " +
      "olculen semantik: limit " + CAP + " -> " + GECEN + " gecer)" +
      " | canlidaki 40-istek dilimi: 200=" + ilk40.filter((k) => k === 200).length +
      " 429=" + ilk40.filter((k) => k === 429).length);
  if (ci.ikiyuz !== GECEN) { hatalar.push("9.2 200 sayisi " + ci.ikiyuz + " != " + GECEN); }
  if (ci.redd !== 1) { hatalar.push("9.2 429 sayisi " + ci.redd + " != 1"); }
  if (ci.kodlar.indexOf(429) !== GECEN) {
    hatalar.push("9.2 ilk 429 " + (ci.kodlar.indexOf(429) + 1) + ". istekte (beklenen " +
                 ILK_RED + ")");
  }
  // 🔴 DURUST ETIKET — iddia EDILMEYEN eksen (bayat-kabul-testi + kapi-disiplin dersi):
  not("9.2 ÖLÇÜLEMEDİ ⚪: 'sayac gercekten TEK mi' (kolo/baglanti basina bolunme) ekseni burada " +
      "iddia EDILMEZ — 29 Tem canli olcumu bolundugunu gosterdi (her istekte yeni baglanti: " +
      "300 istek/11,2 sn, ilk 429 265. istekte; efektif tavan ~4,4x). Carpan istemcinin " +
      "baglanti davranisina bagli = DETERMINISTIK DEGIL -> CI'ya bloklayici baglanamaz.");

  // ---- 9.3 429 YOLU UCUZ ----
  const uc = await ucuzlukOlcumu(YENI, "198.51.100.3");
  not("9.3 429 YOLU: cap tuketildikten sonra 5 istek -> kodlar " + uc.kodlar.join(",") +
      "; D1 YAZMA=" + uc.yazma + " D1 OKUMA=" + uc.okuma + " AG=" + uc.agCagri +
      " siparis_no sorgusu=" + uc.first + " (hepsi 0 olmali)");
  if (uc.kodlar.some((k) => k !== 429)) { hatalar.push("9.3 429 disi kod: " + uc.kodlar.join(",")); }
  if (uc.yazma !== 0) { hatalar.push("9.3 429 yolunda D1 YAZMA=" + uc.yazma); }
  if (uc.okuma !== 0) { hatalar.push("9.3 429 yolunda D1 OKUMA=" + uc.okuma); }
  if (uc.agCagri !== 0) { hatalar.push("9.3 429 yolunda AG cagrisi=" + uc.agCagri); }
  if (uc.first !== 0) { hatalar.push("9.3 429 yolunda siparis_no sorgusu=" + uc.first); }

  // ---- 9.4 FAIL-CLOSED (binding yok / bozuk / patliyor) ----
  const patlayan = limiterKur(CAP); patlayan.patlat = true;
  const fc = [
    ["binding HIC YOK", null],
    ["binding BOZUK (limit fonksiyon degil)", {}],
    ["limiter PATLIYOR (exception)", patlayan],
  ];
  const fcSatir = [];
  for (const [ad, lim] of fc) {
    const r = await prova(YENI, TAVAN_SATIR, TAVAN_SEPET, "198.51.100.4", lim);
    fcSatir.push(ad + " -> " + r.kod + " (D1 okuma " + r.d1Okuma + ", ag " + r.agCagri + ")");
    if (r.kod !== 429) { hatalar.push("9.4 FAIL-OPEN: " + ad + " -> " + r.kod + " (429 olmali)"); }
    if (r.d1Okuma !== 0 || r.d1Yazma !== 0 || r.agCagri !== 0) {
      hatalar.push("9.4 " + ad + ": fail-closed yolu D1/ag'a dokundu");
    }
  }
  not("9.4 FAIL-CLOSED: " + fcSatir.join(" | "));

  // ---- 9.5 YANLIS-POZITIF (normal musteri davranisi 429 YEMEZ) ----
  // Her senaryo TAZE pencerede kosar (LIMITER.sifirla) — gercek hayatta da her dakika
  // yeni pencere baslar. Senaryolar mesru kullanimin EN YOGUN makul hallerini kapsar.
  const senaryolar = [
    ["konfiguratorde 10-15 sn'de 8 olcu denemesi (tek musteri)", 8, 1],
    ["malzeme gezme: 6 malzeme ust uste (tek musteri)", 6, 1],
    ["3 kalemlik sepet, 6 kez yeniden hesap", 6, 1],
    ["slider debounce patlamasi: 3 sn'de 12 istek", 12, 1],
    ["kararsiz musteri: dakika boyunca 40 istek", 40, 1],
    ["5 ayri musteri (FARKLI IP) x 20 istek", 20, 5],
    ["ofis NAT'i: AYNI IP arkasinda 2 musteri x 25 istek", 50, 1],
  ];
  let yanlisPozitif = 0, ypIstek = 0;
  const ypSatir = [];
  for (const [ad, adet, ipAdet] of senaryolar) {
    LIMITER.sifirla();
    let redd = 0;
    for (let m = 0; m < ipAdet; m++) {
      const ip = "192.0.2." + (10 + m);
      for (let i = 0; i < adet; i++) {
        const r = await prova(YENI, TAVAN_SATIR, TAVAN_SEPET, ip);
        ypIstek += 1;
        if (r.kod === 429) { redd += 1; }
      }
    }
    yanlisPozitif += redd;
    ypSatir.push(ad + " -> 429:" + redd);
  }
  not("9.5 YANLIS-POZITIF (" + senaryolar.length + " senaryo, " + ypIstek + " istek): " +
      ypSatir.join(" | "));
  not("9.5 TOPLAM 429 = " + yanlisPozitif + " (0 olmali; yapilandirma " + CAP + "/dk, olculen " +
      GECEN + " gecer). NOT: gercekte sayac bolundugu icin mesru musteri buradakinden DAHA AZ " +
      "429 riski tasir — bu set yanlis-pozitifin UST sinirini olcer.");
  if (yanlisPozitif !== 0) { hatalar.push("9.5 mesru davranis " + yanlisPozitif + " kez 429 yedi"); }

  // ---- 9.6 YANLIS-GUVENCE NOBETCISI (metin) ----
  const yg = yanlisGuvenceTara(GUVENCE_DOSYALARI);
  not("9.6 YANLIS-GUVENCE TARAMASI: " + yg.taranan + " dosya, " + YASAK_GUVENCE.length +
      " desen + " + MUTLAKLIK.length + " iki-faktorlu sinif -> bulunan " + yg.bulgu.length +
      ". ⚠️ Bu kontrol ORUNTU TABANLIDIR ve TAM KAPSAMA GARANTI ETMEZ (olculen kapsam icin " +
      "9.7'ye bak); muafiyet penceresi iddianin " + MUAF_GERI_SATIR + " satir/" +
      MUAF_GERI_KARAKTER + " karakter oncesi + " + MUAF_ILERI_SATIR + " satir/" +
      MUAF_ILERI_KARAKTER + " karakter sonrasidir (cumle geneli DEGIL). Disiplin cihazi, " +
      "guvenlik siniri degil.");
  yg.bulgu.slice(0, 8).forEach((b) => hatalar.push("9.6 " + b));

  // ---- 9.7 KAPSAM OLCUMU (30 Tem, S2): nobetcinin RECALL'u SAYIYLA beyan edilir ----
  const yakalanan = YANLIS_KORPUS.filter(
    (c, i) => yanlisGuvenceTara([{ ad: "korpus-" + i, metin: c }]).bulgu.length > 0).length;
  const yanan = MASUM_KORPUS.filter(
    (c, i) => yanlisGuvenceTara([{ ad: "masum-" + i, metin: c }]).bulgu.length > 0);
  not("9.7 KAPSAM OLCUMU: yanlis-guvence korpusu " + yakalanan + "/" + YANLIS_KORPUS.length +
      " yakalandi (esik " + RECALL_EN_AZ + "; tek-faktorlu eski hal 0/20 idi) · masum korpus " +
      yanan.length + "/" + MASUM_KORPUS.length + " yandi (0 olmali). BEYAN EDILEN KACAK: hiz " +
      "siniri KONUSU (IP/istek/sayac/limit/kota/dk) hic gecmeyen cumleler — or. \"Ust sinir " +
      "asilmaz.\" Konuyu da kapsama almak Y12 tipi mesru ifadeleri yakardi; recall sonsuza " +
      "kadar kovalanmaz.");
  if (yakalanan < RECALL_EN_AZ) {
    hatalar.push("9.7 RECALL DUSTU: " + yakalanan + "/" + YANLIS_KORPUS.length +
                 " (esik " + RECALL_EN_AZ + ") — nobetci gevsetilmis");
  }
  yanan.forEach((c) => hatalar.push("9.7 YANLIS-POZITIF (masum ifade yandi): " + c));

  // ---- 9.8 KACAK KIMLIGI (31 Tem): KACAN KUME beyan edilenle BIREBIR ayni mi ----
  // Sayi korunurken kumenin degismesi = korunmadigi sanilan sey degisti, kimse gormedi.
  const kacan = YANLIS_KORPUS.filter(
    (c, i) => yanlisGuvenceTara([{ ad: "kacak-" + i, metin: c }]).bulgu.length === 0);
  const beklenmeyen = kacan.filter((c) => !KACAK_BEYAN.includes(c));
  const kapanan = KACAK_BEYAN.filter((c) => !kacan.includes(c));
  not("9.8 KACAK KIMLIGI: kacan " + kacan.length + " cumle, beyan edilen " +
      KACAK_BEYAN.length + " (kume birebir esit olmali; sayinin korunmasi YETMEZ).");
  beklenmeyen.forEach((c) => hatalar.push(
    "9.8 BEYAN DISI KACAK (nobetci sessizce gevsedi): " + c));
  kapanan.forEach((c) => hatalar.push(
    "9.8 BEYAN BAYAT (bu kacak artik yakalaniyor — KACAK_BEYAN'dan CIKAR): " + c));

  if (hatalar.length) {
    kirmizi += 1;
    hatalar.slice(0, 12).forEach((h) => ham.push("    ❌ " + h));
    ham.push("  ❌ KALDI — hiz siniri / yanlis guvence");
  } else {
    ham.push("  ✅ GECTI — kod binding'i her isolate'te kullaniyor; 429 yolu bedava; " +
             "fail-closed; 0 yanlis-pozitif; yanlis-guvence ifadesi YOK");
  }
}

// =================================================================== 8) MUTANTLAR
baslik("== 8) KIRMIZI-MUTASYON (M1..M9) ==");
{
  const KAYNAKLAR = guncelKaynaklar();

  // ---- M1: ARTEFAKT BAYAT (urunler.json'da var, artefaktta yok) ----
  ham.push("  -- M1: artefakt bayat (yeni konfigurlu urun uretilmedi) --");
  const gecici = path.join(SHOP, TEMP_ONEK + "m1-" + process.pid);
  fs.mkdirSync(gecici, { recursive: true });
  dizinler.push(gecici);
  // MUTANT KATALOG = GERCEK urunler.json BAYTLARI + basa eklenmis YENI konfigurlu urun.
  // (Katalogu JS'te yeniden serilestirmek sayi YAZIMINI degistirir — mutasyon o gurultuye
  // degil, YENI URUNE dayansin.)
  const hamKatalog = fs.readFileSync(path.join(KOK, "urunler.json"), "utf8");
  const yeniUrunMetni = JSON.stringify({ id: YENI_KONFIGUR.id, kategori: "Skan Art",
    baslik: "Ejderha", fiyat: "500 TL", gorseller: [],
    konfigur: KONFIGUR_URUNLER[0].konfigur });
  const miniYol = path.join(KOK, "urunler.json");            // KONTROL: gercek katalog
  const miniArtiYol = path.join(gecici, "urunler-arti.json");  // MUTANT: +1 konfigurlu urun
  fs.writeFileSync(miniArtiYol,
    hamKatalog.replace(/^\s*\[/, "[" + yeniUrunMetni + ","));
  function kapiKos(urunlerYolu) {
    try {
      execFileSync("python3", [path.join(KOK, "tools", "konfigur-bundle-kapisi.py"),
                               "--urunler", urunlerYolu,
                               "--dosya", path.join(SRC, "konfigurlar.js")],
                   { encoding: "utf8", stdio: "pipe" });
      return 0;
    } catch (e) { return e.status; }
  }
  const rcGuncel = kapiKos(miniYol);
  const rcBayat = kapiKos(miniArtiYol);
  not("M1 kapi: guncel katalog rc=" + rcGuncel + " (0 olmali) | +1 konfigurlu urun rc=" +
      rcBayat + " (1 olmali)");
  // Calisma zamani sonucu — FAZ 4'te YON DEGISTI: artefakttan bir urun dusurulurse fiyat
  // artik D1 `konfigur` kolonundan hesaplandigi icin kalem DOGRU kurusla 200 doner
  // (bayat artefakt penceresi KAPANDI; eskiden burasi 400 = satis kaybiydi). Fail-closed
  // iddiasi ayni mutantta ikinci vakayla korunur: artefakt DA bos, D1 DA bos -> 400.
  // Artefakt id'ye gore SIRALI: ilk kaydi secmek blok deseninin (virgulle biten) tutmasini
  // garanti eder (son kayitta kapanis virgulsuzdur).
  let eksikKaynak = KAYNAKLAR["konfigurlar.js"];
  const dusen = [...KONFIGUR_URUNLER].sort((a, b) => (a.id < b.id ? -1 : 1))[0];
  const blok = new RegExp('\\n  "' + dusen.id + '": \\{[\\s\\S]*?\\n  \\},');
  const kesildi = blok.test(eksikKaynak);
  eksikKaynak = eksikKaynak.replace(blok, "");
  const m1Mod = await modulYukle(dizinKur("m1src",
    Object.assign({}, KAYNAKLAR, { "konfigurlar.js": eksikKaynak })));
  const m1r = await baslat(m1Mod, [d1Satiri(dusen)],
    [{ id: dusen.id, malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 300 } }]);
  const m1p = await prova(m1Mod, [d1Satiri(dusen)],
    [{ id: dusen.id, malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 300 } }]);
  const m1Beklenen = FRONT.fiyatKurus(dusen.konfigur,
    FRONT.boyDuzelt(dusen.konfigur, 300),
    (dusen.konfigur.malzemeler.find((m) => m.ad === "PLA") || {}).katsayi);
  // IKINCI VAKA: artefakt DA bos, D1 kolonu DA bos -> tek kaynak da kalmadi -> FAIL-CLOSED.
  const m1bos = await baslat(m1Mod, [Object.assign(d1Satiri(dusen), { konfigur: "" })],
    [{ id: dusen.id, malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 300 } }]);
  not("M1 calisma zamani (" + dusen.id + " artefakttan silindi, kesildi=" + kesildi + "): " +
      "baslat=" + m1r.kod + "/" + m1r.govde.hata + " fiyat=" + m1r.birimKurus +
      " (D1 semasindan beklenen " + m1Beklenen + ") | prova=" + m1p.kod + "/" + m1p.govde.hata);
  not("M1 fail-closed vakasi (artefakt DA bos, D1 kolonu DA bos): baslat=" + m1bos.kod + "/" +
      m1bos.govde.hata + " tahsilat=" + (m1bos.birimKurus == null ? "YOK" : m1bos.birimKurus));
  const m1Ok = rcGuncel === 0 && rcBayat === 1 && kesildi &&
               m1r.kod === 200 && m1r.birimKurus === m1Beklenen && m1p.kod === 200 &&
               m1bos.kod === 400 && m1bos.govde.hata === "konfigur-urun" &&
               m1bos.birimKurus === null;
  if (!m1Ok) { kirmizi += 1; ham.push("    ❌ M1 KALDI"); }
  else {
    ham.push("    ✅ M1: bayat artefakt CI'da rc=1; calisma zamani D1'den DOGRU fiyatliyor " +
             "(" + m1Beklenen + "), iki kaynak da bosken fail-closed 400");
  }

  // ---- M2: FAIL-CLOSED KOLU SILINDI (sabit fiyata dusurulmus) ----
  ham.push("  -- M2: fail-closed kol silindi (kalem sabit fiyata duser) --");
  // FAZ 4: kapi artik ayri bir `else if` dali degil, `konfigurluMu` sinyalinin BIR TERIMI.
  // Terim silinince D1'de konfiguru olmayan + artefaktin tanimadigi seri urunu SABIT FIYAT
  // koluna duser -> tam olarak olculmek istenen sessiz eksik tahsilat.
  const DESEN = / \|\| konfigurBeklenirMi\(u\)/;
  const mutantKaynak = KAYNAKLAR["index.js"].replace(DESEN, "");
  const m2Uygulandi = DESEN.test(KAYNAKLAR["index.js"]) &&
                      !/konfigurBeklenirMi\(u\)/.test(mutantKaynak);
  let m2Kalan = [];
  if (!m2Uygulandi) {
    kirmizi += 1;
    ham.push("    ❌ M2 mutasyonu UYGULANAMADI (kol deseni degismis — desen guncellenmeli)");
  } else {
    const m2Mod = await modulYukle(dizinKur("m2src",
      Object.assign({}, KAYNAKLAR, { "index.js": mutantKaynak })));
    const iddia = await failClosedIddialari(m2Mod);
    m2Kalan = iddia.filter((i) => !i.ok);
    not("M2 VAKUM: " + iddia.length + " iddiadan " + m2Kalan.length + " tanesi KIRMIZI yandi " +
        "(>=10 olmali)");
    m2Kalan.slice(0, 12).forEach((i) => ham.push("    · yakalandi: " + i.ad +
                                                 " (olculen: " + i.olculen + ")"));
    if (m2Kalan.length < 10) {
      kirmizi += 1;
      ham.push("    ❌ M2 KALDI — kol silindi ama iddialar sessiz kaldi (OLU NOBETCI)");
    } else { ham.push("    ✅ M2: " + m2Kalan.length + " iddia KIRMIZI"); }
  }

  // ---- M3: KAPININ CAGRI SATIRI deploy.yml'den SILINDI ----
  ham.push("  -- M3: kapinin CI cagri satiri silindi --");
  const deployYol = path.join(KOK, ".github", "workflows", "deploy.yml");
  const deploy = fs.readFileSync(deployYol, "utf8");
  const cagriDeseni = /^.*python3 tools\/konfigur-bundle-kapisi\.py\s*$/m;
  const cagriVar = cagriDeseni.test(deploy);
  const mutantDeploy = deploy.replace(/^.*konfigur-bundle-kapisi\.py.*$/gm, "");
  const mutantDeployYol = path.join(gecici, "deploy-mutant.yml");
  fs.writeFileSync(mutantDeployYol, mutantDeploy);
  function kapsamKos(yol) {
    try {
      execFileSync("python3", [path.join(KOK, "tools", "ci-kapsam-test.py"), "--deploy", yol],
                   { encoding: "utf8", stdio: "pipe" });
      return 0;
    } catch (e) { return e.status; }
  }
  const rcGercek = kapsamKos(deployYol);
  const rcMutant = kapsamKos(mutantDeployYol);
  not("M3: deploy.yml'de kapi cagrisi=" + (cagriVar ? "VAR" : "YOK") +
      "; ci-kapsam gercek rc=" + rcGercek + " (0 olmali), cagri silinmis rc=" + rcMutant +
      " (1 olmali)");
  if (!(cagriVar && rcGercek === 0 && rcMutant === 1)) {
    kirmizi += 1;
    ham.push("    ❌ M3 KALDI — kapi CI'dan silinince kimse uyarmiyor");
  } else { ham.push("    ✅ M3: cagri satiri silinince ci-kapsam-test.py KIRMIZI"); }

  // ---- M4: PROVA YAN ETKI URETIYOR (D1 yazma + Telegram) ----
  ham.push("  -- M4: prova yan etki uretiyor (D1 INSERT + Telegram) --");
  const capa = "  const kargoKurus = SECENEK.kargoKurus(toplamKurus);\n" +
               "  const tahsilatKurus = toplamKurus + kargoKurus;\n" +
               "  const kdv = SECENEK.kdvAyristir(tahsilatKurus);\n\n  return json({\n    prova: true,";
  const enjekte = "  const kargoKurus = SECENEK.kargoKurus(toplamKurus);\n" +
    "  const tahsilatKurus = toplamKurus + kargoKurus;\n" +
    "  const kdv = SECENEK.kdvAyristir(tahsilatKurus);\n" +
    "  await env.KATALOG.prepare(\"INSERT INTO siparisler (siparis_no) VALUES (?)\")" +
    ".bind(\"PR-MUTANT\").run();\n" +
    "  await telegram(env, \"mutant prova bildirimi\");\n\n  return json({\n    prova: true,";
  const m4Kaynak = KAYNAKLAR["index.js"].replace(capa, enjekte);
  const m4Uygulandi = m4Kaynak !== KAYNAKLAR["index.js"];
  if (!m4Uygulandi) {
    kirmizi += 1;
    ham.push("    ❌ M4 mutasyonu UYGULANAMADI (capa metni degismis)");
  } else {
    const m4Mod = await modulYukle(dizinKur("m4src",
      Object.assign({}, KAYNAKLAR, { "index.js": m4Kaynak })));
    const urun = KONFIGUR_URUNLER[0];
    const p = await prova(m4Mod, [d1Satiri(urun)],
      [{ id: urun.id, malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: { boy_mm: 150 } }]);
    const yakalanan = [];
    if (p.d1Yazma !== 0) { yakalanan.push("D1 yazma=" + p.d1Yazma); }
    if (p.agCagri !== 0) { yakalanan.push("ag cagri=" + p.agCagri); }
    if (p.sayaclar.yazilan.length) { yakalanan.push("SQL=" + p.sayaclar.yazilan[0].sql.slice(0, 30)); }
    not("M4: mutant provada yakalanan yan etki -> " + (yakalanan.join(", ") || "HICBIRI"));
    if (yakalanan.length < 2) {
      kirmizi += 1;
      ham.push("    ❌ M4 KALDI — yan etki sayaclari OLU (mutant sessiz gecti)");
    } else { ham.push("    ✅ M4: " + yakalanan.length + " sayac KIRMIZI yandi"); }
  }

  // ---- M5: HIZ SINIRI KONTROLU SILINDI (29 Tem canli kirmizisinin ta kendisi) ----
  ham.push("  -- M5: /fiyat hiz siniri kontrolu SILINDI --");
  const m5Kaynak = KAYNAKLAR["index.js"].replace(TAVAN_CAPA + "\n", "");
  const m5Uygulandi = KAYNAKLAR["index.js"].includes(TAVAN_CAPA) &&
                      !m5Kaynak.includes(TAVAN_CAPA);
  if (!m5Uygulandi) {
    kirmizi += 1;
    ham.push("    ❌ M5 mutasyonu UYGULANAMADI (capa metni degismis — TAVAN_CAPA'yi guncelle)");
  } else {
    const m5Dizin = dizinKur("m5src", Object.assign({}, KAYNAKLAR, { "index.js": m5Kaynak }));
    LIMITER.sifirla();
    const m5ci = await cokIsolate(m5Dizin, CAP + 1, "198.51.100.9");
    const ilk40 = m5ci.kodlar.slice(0, 40);
    not("M5 COK-ISOLATE: " + (CAP + 1) + " istek -> 200:" + m5ci.ikiyuz + " / 429:" + m5ci.redd +
        " | 40-istek dilimi 200=" + ilk40.filter((k) => k === 200).length + "/40 " +
        "(29 Tem canlida olculen: 40/40 200)");
    const m5Yakalandi = (m5ci.ikiyuz !== CAP) || (m5ci.redd !== 1);
    if (!(m5Yakalandi && m5ci.ikiyuz === CAP + 1 && m5ci.redd === 0)) {
      kirmizi += 1;
      ham.push("    ❌ M5 KALDI — tavan silindi ama set 9.2 sessiz kaldi (OLU NOBETCI)");
    } else {
      ham.push("    ✅ M5: tavansiz kodda " + m5ci.ikiyuz + "/" + (CAP + 1) +
               " istek 200 (429=0) -> set 9.2 KIRMIZI yanar");
    }
  }

  // ---- M6: wrangler.toml'dan BINDING BEYANI SILINDI (sessiz fail-open avi) ----
  ham.push("  -- M6: wrangler.toml'dan FIYAT_RATE_LIMIT beyani silindi --");
  const m6Toml = bindingBlogunuSil(WRANGLER, "FIYAT_RATE_LIMIT");
  const m6Var = unsafeBindingler(m6Toml).some((b) => b.name === "FIYAT_RATE_LIMIT");
  const m6Ref = unsafeBindingler(m6Toml).some((b) => b.name === "REF_RATE_LIMIT");
  const m6Uygulandi = FIYAT_BEYAN.name === "FIYAT_RATE_LIMIT" && !m6Var;
  const m6Beyan = beyanIddialari(m6Toml, KOD_PENCERE).filter((i) => !i.ok);
  // Calisma zamani yarisi: binding gelmeyince uc SESSIZCE sinirsiza DONMEMELI -> 429.
  const m6r = await prova(YENI, TAVAN_SATIR, TAVAN_SEPET, "198.51.100.11", null);
  not("M6: mutant toml'da FIYAT_RATE_LIMIT=" + (m6Var ? "VAR" : "YOK") + " (YOK olmali), " +
      "REF_RATE_LIMIT korundu=" + m6Ref + "; set 9.1 iddialarindan KIRMIZI yanan=" +
      m6Beyan.length + " (>=1 olmali); binding'siz calisma zamani -> " + m6r.kod +
      " (429 = fail-closed; D1 okuma " + m6r.d1Okuma + ", ag " + m6r.agCagri + ")");
  const m6Ok = m6Uygulandi && m6Ref && m6Beyan.length >= 1 && m6r.kod === 429 &&
               m6r.d1Okuma === 0 && m6r.d1Yazma === 0 && m6r.agCagri === 0;
  if (!m6Ok) {
    kirmizi += 1;
    ham.push("    ❌ M6 KALDI — beyan silinince ya kapi susuyor ya uc sessizce sinirsiza donuyor");
  } else {
    ham.push("    ✅ M6: beyan silinince " + m6Beyan.length +
             " iddia KIRMIZI + uc fail-closed 429 (sessiz fail-open YOK)");
  }

  // ---- M7: 429 YOLUNA D1 + AG ENJEKTE EDILDI ----
  ham.push("  -- M7: 429 yoluna D1 yazma/okuma + Telegram enjekte edildi --");
  const m7Kaynak = KAYNAKLAR["index.js"].replace(TAVAN_CAPA, TAVAN_M7);
  if (m7Kaynak === KAYNAKLAR["index.js"]) {
    kirmizi += 1;
    ham.push("    ❌ M7 mutasyonu UYGULANAMADI (capa metni degismis)");
  } else {
    const m7Mod = await modulYukle(dizinKur("m7src",
      Object.assign({}, KAYNAKLAR, { "index.js": m7Kaynak })));
    const m7 = await ucuzlukOlcumu(m7Mod, "198.51.100.12");
    const yakalanan7 = [];
    if (m7.yazma !== 0) { yakalanan7.push("D1 yazma=" + m7.yazma); }
    if (m7.okuma !== 0) { yakalanan7.push("D1 okuma=" + m7.okuma); }
    if (m7.agCagri !== 0) { yakalanan7.push("ag cagri=" + m7.agCagri); }
    not("M7: 429 yolunda yakalanan yan etki -> " + (yakalanan7.join(", ") || "HICBIRI") +
        " (kodlar " + m7.kodlar.join(",") + ")");
    if (yakalanan7.length < 3) {
      kirmizi += 1;
      ham.push("    ❌ M7 KALDI — 429 yolu sayaclari OLU (mutant sessiz gecti)");
    } else { ham.push("    ✅ M7: " + yakalanan7.length + " sayac KIRMIZI yandi"); }
  }

  // ---- M8: "SERT TAVAN" GUVENCESI GERI KONDU (CAPASIZ — BAS/ORTA/SON konumlarina enjekte) ----
  // (29 Tem'de olculerek curutulen iddianin sessizce geri sizmasi — set 9.6 yakalamali.)
  //
  // 🔴 NEDEN CAPA YOK: onceki surum mutanti "/**\n * PROVA HIZ SINIRI" METIN CAPASIYLA uretiyordu
  // ve capa tutmayinca `m8Uygulandi=false` -> KIRMIZI verirdi. Yani o JSDoc basligina masum bir
  // satir eklemek / basligi yeniden bicimlendirmek / tasimak TUM EKIBIN yayinini durdururdu.
  // Bu nobetci bir DISIPLIN cihazi, guvenlik siniri DEGIL: yanlis-pozitifin bedeli (herkesin
  // deploy'u kirmizi) yanlis-negatifin bedelinden (yanlis yorum metni bir sure kalir) AGIR basar
  // -> supheli durumda GEVSET. Mutant artik gercek kaynagin BASINA / ORTASINA / SONUNA enjekte
  // edilerek uretilir: hicbir metin bicimine bagli degil, her zaman uygulanabilir.
  ham.push("  -- M8: yanlis guvence gercek kaynaga 3 konumdan (BAS/ORTA/SON) enjekte edildi --");
  const M8_IDDIA =
    " * PROVA HIZ SINIRI — IP basina SERT TAVAN; native binding hesap duzeyinde sayar,\n" +
    " * bu yuzden IP basina en fazla 60 istek/dk kesin sinirdir.\n";
  const m8Kaynak = KAYNAKLAR["index.js"];
  const m8Satirlar = m8Kaynak.split("\n");
  const m8Orta = m8Satirlar.slice(0, Math.floor(m8Satirlar.length / 2)).join("\n").length + 1;
  const m8Konumlar = [["BAS", 0], ["ORTA", m8Orta], ["SON", m8Kaynak.length]];
  const m8Temiz = yanlisGuvenceTara([{ ad: "index.js (mutantsiz)", metin: m8Kaynak }]);
  const m8Sonuc = m8Konumlar.map(([etiket, konum]) => {
    const metin = m8Kaynak.slice(0, konum) + M8_IDDIA + m8Kaynak.slice(konum);
    return { etiket, sayi: yanlisGuvenceTara([{ ad: "index.js (M8/" + etiket + ")", metin }])
                             .bulgu.length };
  });
  const m8Zayif = m8Sonuc.filter((s) => s.sayi < 2);
  not("M8: mutantsiz bulgu=" + m8Temiz.bulgu.length + " (0 olmali); enjeksiyon konumlari -> " +
      m8Sonuc.map((s) => s.etiket + ":" + s.sayi).join(", ") + " (her biri >=2 olmali)");
  if (m8Temiz.bulgu.length !== 0 || m8Zayif.length) {
    kirmizi += 1;
    ham.push("    ❌ M8 KALDI — yanlis-guvence nobetcisi OLU (curutulmus iddia sessizce geri konabilir)");
  } else {
    ham.push("    ✅ M8: 3/3 konumda geri konan yanlis guvence set 9.6'da KIRMIZI yanar");
  }

  // ---- M10: IKI FAKTORLU AILE NO-OP YAPILDI (S2 nobeti yuk tasiyor mu?) ----
  // 9.7'nin olctugu recall'un GERCEKTEN yeni aileden geldigini kanitlar. Mutant, BU DOSYANIN
  // KENDI KAYNAK METNINDEN uretilir (ikinci kopya olculmez): `MUTLAKLIK` listesi bosaltilir ve
  // nobetci blogu ayri bir kapsamda calistirilir. Beklenen: recall COKER (tek-faktorlu hal).
  ham.push("  -- M10: MUTLAKLIK listesi bosaltildi (iki-faktorlu aile no-op) --");
  const M10_KAYNAK = fs.readFileSync(path.join(BURASI, "fiyat-prova.mjs"), "utf8");
  const M10_BAS = "const YASAK_GUVENCE = [";
  const M10_SON = "/** Taranan dosyalar:";
  const M10_CAPA = "const MUTLAKLIK = [";
  // NOT: capa/sinir dizeleri BU BLOKTA da metin olarak geciyor; bu yuzden arama nobetci
  // blogunun ICINDE yapilir (indexOf ilk = gercek tanim, blok M10'dan ONCE gelir).
  const i10 = M10_KAYNAK.indexOf(M10_BAS), j10 = M10_KAYNAK.indexOf(M10_SON);
  const m10Blok = (i10 >= 0 && j10 > i10) ? M10_KAYNAK.slice(i10, j10) : "";
  if (!m10Blok || m10Blok.split(M10_CAPA).length !== 2) {
    kirmizi += 1;
    ham.push("    ❌ M10 OLCULEMEDI — nobetci blogu/capasi bulunamadi (kaldirilmis ya da " +
             "yeniden yazilmis): " + M10_BAS + " / " + M10_CAPA);
  } else {
    const m10Mutant = m10Blok.replace(M10_CAPA, "const MUTLAKLIK_OLU = [];\nconst MUTLAKLIK = [];\nconst MUTLAKLIK_YEDEK = [");
    /* eslint-disable no-new-func */
    const m10Tara = new Function(m10Mutant + "\nreturn yanlisGuvenceTara;")();
    const m10Yakalanan = YANLIS_KORPUS.filter(
      (c, i) => m10Tara([{ ad: "m10-" + i, metin: c }]).bulgu.length > 0).length;
    const RECALL_OLCULEN = YANLIS_KORPUS.filter(
      (c, i) => yanlisGuvenceTara([{ ad: "m10-ger-" + i, metin: c }]).bulgu.length > 0).length;
    not("M10: MUTLAKLIK bosken korpus recall = " + m10Yakalanan + "/" + YANLIS_KORPUS.length +
        " (gercek kodda " + RECALL_OLCULEN + "; mutantta ANLAMLI OLCUDE dusmeli)");
    if (m10Yakalanan >= RECALL_OLCULEN) {
      kirmizi += 1;
      ham.push("    ❌ M10 KALDI — iki faktorlu aile OLU: bosaltilinca bile ayni recall, " +
               "9.7 sayisi bu koddan gelmiyor");
    } else {
      ham.push("    ✅ M10: aile bosaltilinca recall " + RECALL_OLCULEN + " -> " +
               m10Yakalanan + " (nobet YUK TASIYOR)");
    }
  }

  // ---- M11/M12: FIZIKSEL URUN GARDI (secenekler.js fizikselMi) NO-OP EDILDI ----
  /**
   * Gard `secenekler.js`tedir (TEK KAYNAK) ve worker onu `../../secenekler.js` ile cagirir.
   * Mutant kosturmak icin SAHTE bir depo koku kurulur:
   *   <tmp>/secenekler.js          <- MUTANT (../../ buraya cikar)
   *   <tmp>/konfigur.js, <tmp>/jenerator  <- gercege sembolik bag (degistirilmez)
   *   <tmp>/shop/src/*.js          <- gercek worker kaynaklari (JSON gomulu)
   * Depo dosyalarina DOKUNULMAZ; dizin kosum sonunda silinir.
   */
  async function mutantSecenekModulu(etiket, capa, yerine) {
    const kokDizin = path.join(SHOP, TEMP_ONEK + etiket + "-" + process.pid);
    fs.rmSync(kokDizin, { recursive: true, force: true });
    fs.mkdirSync(path.join(kokDizin, "shop", "src"), { recursive: true });
    dizinler.push(kokDizin);
    const hamSecenek = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");
    if (hamSecenek.split(capa).length - 1 !== 1) {
      return { hata: "capa kayip/coklu: " + capa };
    }
    fs.writeFileSync(path.join(kokDizin, "secenekler.js"), hamSecenek.replace(capa, yerine));
    for (const ad of ["konfigur.js", "jenerator"]) {
      fs.symlinkSync(path.join(KOK, ad), path.join(kokDizin, ad));
    }
    for (const [ad, kaynak] of Object.entries(KAYNAKLAR)) {
      fs.writeFileSync(path.join(kokDizin, "shop", "src", ad),
                       jsonGom(kaynak, SRC, etiket + "/" + ad));
    }
    // 🔴 BULASMA KORUMASI (olculdu — bu tuzak once ISIRDI): secenekler.js bir IIFE'dir ve
    // `globalThis.PRUVO_SECENEK`e YAZAR. Mutant kopya import edilince o global TUM surec icin
    // mutanta doner; SONRAKI mutantlar (M13/M14) worker'i import ettiginde `SECENEK`i
    // mutant halinden okur ve iddialar YANLIS eksende kirmizi yanar (M13 kosumunda 3D fikstur
    // "fiziksel" gibi fiyatlandi). Modul import ANINDA kendi referansini kaptigi icin globali
    // HEMEN geri koymak mutanti bozmaz, yalnizca sizintiyi keser.
    const oncekiSecenek = globalThis.PRUVO_SECENEK;
    sayac += 1;
    const mod = await import(
      pathToFileURL(path.join(kokDizin, "shop", "src", "index.js")).href + "?s=" + sayac);
    globalThis.PRUVO_SECENEK = oncekiSecenek;
    // KANARYA: global gercekten geri geldi mi? (Gelmezse sonraki setler sessizce yanlis
    // olcerdi — "yesil ama olctugu sey baska" sinifi.)
    if (globalThis.PRUVO_SECENEK.fizikselMi("fiziksel") !== true ||
        globalThis.PRUVO_SECENEK.fizikselMi("baska") !== false) {
      return { hata: "global PRUVO_SECENEK mutant halde kaldi (bulasma korumasi calismadi)" };
    }
    return { mod };
  }
  const FIZ_CAPA = 'function fizikselMi(tur) { return tur === TUR_FIZIKSEL; }';

  // M11: gard DAIMA YANLIS -> fiziksel urun yine +%15/+%84 alir (kusurun ta kendisi).
  // DAR PROBE: yalniz "fiziksel" yonu KIRMIZI yanmali; 3D ve fail-closed yonleri YESIL
  // kalmali (kalsalar bile iddia bos degil — kirmizi yanan sey tam olarak bu gardin isidir).
  ham.push("  -- M11: fizikselMi() DAIMA false (gard no-op) --");
  {
    const m = await mutantSecenekModulu("m11", FIZ_CAPA,
                                        'function fizikselMi(tur) { return false; }');
    if (m.hata) {
      kirmizi += 1;
      ham.push("    ❌ M11 mutasyonu UYGULANAMADI — " + m.hata);
    } else {
      const iddia = await fizikselIddialari(m.mod);
      const kalan = iddia.filter((i) => !i.ok);
      const fizKirmizi = kalan.filter((i) => i.yon === "fiziksel").length;
      const digerKirmizi = kalan.filter((i) => i.yon !== "fiziksel").length;
      // ESIK 7, 9 DEGIL — DURUST SINIR: PLA/Siyah kombinasyonu (baslat+prova, 2 iddia) gard
      // olsa da olmasa da LISTE fiyati verir (carpan zaten 1,00); o iki iddia bu mutantla
      // AYIRT EDILEMEZ. Kalan 7 iddia ("Diğer" renk / ASA malzeme + 3 gercek katalog urunu)
      // yalnizca gard sayesinde yesildir.
      not("M11: gard no-op -> POZITIF(fiziksel) iddialardan " + fizKirmizi + " KIRMIZI " +
          "(>=7 olmali; PLA/Siyah'in 2 iddiasi carpansiz oldugu icin ayirt edilemez), " +
          "diger yonlerde " + digerKirmizi + " (0 olmali — probe DAR)");
      kalan.filter((i) => i.yon === "fiziksel").slice(0, 4)
        .forEach((i) => ham.push("    · yakalandi: " + i.ad + " (olculen: " + i.olculen + ")"));
      if (fizKirmizi < 7 || digerKirmizi !== 0) {
        kirmizi += 1;
        ham.push("    ❌ M11 KALDI — gard no-op edildi ama iddia sessiz kaldi (OLU IDDIA) " +
                 "ya da probe DAR degil");
      } else {
        ham.push("    ✅ M11: gard no-op -> " + fizKirmizi + " POZITIF iddia KIRMIZI, " +
                 "3D/fail-closed yonleri etkilenmedi");
      }
    }
  }

  // M12: gard DAIMA DOGRU -> her urun "fiziksel" sayilir; 15.930 baski urununde carpan
  // sessizce kaybolur (EKSIK tahsilat). 3D REGRESYON iddiasi KIRMIZI yanmali.
  ham.push("  -- M12: fizikselMi() DAIMA true (gard her urunde acik) --");
  {
    const m = await mutantSecenekModulu("m12", FIZ_CAPA,
                                        'function fizikselMi(tur) { return true; }');
    if (m.hata) {
      kirmizi += 1;
      ham.push("    ❌ M12 mutasyonu UYGULANAMADI — " + m.hata);
    } else {
      const iddia = await fizikselIddialari(m.mod);
      const kalan = iddia.filter((i) => !i.ok);
      const ucbKirmizi = kalan.filter((i) => i.yon === "3d").length;
      const fizKirmizi = kalan.filter((i) => i.yon === "fiziksel").length;
      not("M12: gard her urunde acik -> NEGATIF(3D regresyon) iddialardan " + ucbKirmizi +
          " KIRMIZI (>=4 olmali), POZITIF(fiziksel) " + fizKirmizi + " (0 olmali)");
      kalan.filter((i) => i.yon === "3d").slice(0, 4)
        .forEach((i) => ham.push("    · yakalandi: " + i.ad + " (olculen: " + i.olculen + ")"));
      if (ucbKirmizi < 4 || fizKirmizi !== 0) {
        kirmizi += 1;
        ham.push("    ❌ M12 KALDI — 3D regresyon nobetcisi OLU (gard her urunde acikken bile " +
                 "yesil kaliyor)");
      } else {
        ham.push("    ✅ M12: gard her urunde acikken " + ucbKirmizi +
                 " 3D regresyon iddiasi KIRMIZI");
      }
    }
  }

  // ---- M13/M14: FIS EKSENI (siparis artefaktlarina beyan yazma karari) ----
  /** shop/src/index.js'i mutasyona ugratip index + eposta modullerini birlikte yukler. */
  async function fisMutanti(etiket, capa, yerine) {
    if (KAYNAKLAR["index.js"].split(capa).length - 1 !== 1) {
      return { hata: "capa kayip/coklu" };
    }
    const dizin = dizinKur(etiket, Object.assign({}, KAYNAKLAR,
      { "index.js": KAYNAKLAR["index.js"].replace(capa, yerine) }));
    return { mod: await modulYukle(dizin), eposta: await epostaYukle(dizin) };
  }

  // M13 = curutucunun C5'i: metin susturmasi GERI ALINIR, fiyat DOGRU kalir. Kusurun ta
  // kendisi: liste fiyati tahsil edilirken fis "ASA / turuncu" der. Bu mutant onarim
  // ONCESINDE TUM kapilardan YESIL geciyordu -> iddia OLU idi.
  ham.push("  -- M13: fiziksel satira malzeme/renk YINE yaziliyor (fiyat dogru kalir) --");
  {
    const m = await fisMutanti("m13src",
      'malzeme: fizikselKalem ? "" : k.malzeme,\n      renk: fizikselKalem ? "" : k.renk,\n' +
      '      renk_ozel: fizikselKalem ? "" : k.renk_ozel,',
      "malzeme: k.malzeme,\n      renk: k.renk,\n      renk_ozel: k.renk_ozel,");
    if (m.hata) {
      kirmizi += 1;
      ham.push("    ❌ M13 mutasyonu UYGULANAMADI — " + m.hata);
    } else {
      const iddia = await fisIddialari(m.mod, m.eposta);
      const kalan = iddia.filter((i) => !i.ok);
      const fizKirmizi = kalan.filter((i) => i.yon === "fis-fiziksel").length;
      const ucbKirmizi = kalan.filter((i) => i.yon === "fis-3d").length;
      // Fiyat iddialari (tutar) mutantta YESIL kalmali: probe FIS eksenine DAR.
      const tutarKirmizi = kalan.filter((i) => i.ad.includes("tutar (krs)")).length;
      not("M13: susturma geri alindi -> FIZIKSEL fis iddialarindan " + fizKirmizi +
          " KIRMIZI (>=8 olmali), 3D " + ucbKirmizi + " (0 olmali), tutar iddialari " +
          tutarKirmizi + " (0 olmali — probe fis eksenine DAR)");
      kalan.filter((i) => i.yon === "fis-fiziksel").slice(0, 5)
        .forEach((i) => ham.push("    · yakalandi: " + i.ad + " (olculen: " + i.olculen + ")"));
      if (fizKirmizi < 8 || ucbKirmizi !== 0 || tutarKirmizi !== 0) {
        kirmizi += 1;
        ham.push("    ❌ M13 KALDI — fis iddiasi OLU (susturma geri alininca kimse uyarmiyor)");
      } else {
        ham.push("    ✅ M13: " + fizKirmizi + " fis iddiasi KIRMIZI, fiyat ekseni etkilenmedi");
      }
    }
  }

  // M14: karar HER kalemde "fiziksel" saylir -> 3D siparisinde malzeme/renk beyani SESSIZCE
  // kaybolur (uretim neyi basacagini bilemez). 3D regresyon nobetcisi KIRMIZI yanmali.
  ham.push("  -- M14: her kalem fiziksel sayiliyor (3D beyani kayboluyor) --");
  {
    const m = await fisMutanti("m14src",
      "const fizikselKalem = SECENEK.fizikselMi(u.tur);",
      "const fizikselKalem = true;");
    if (m.hata) {
      kirmizi += 1;
      ham.push("    ❌ M14 mutasyonu UYGULANAMADI — " + m.hata);
    } else {
      const iddia = await fisIddialari(m.mod, m.eposta);
      const kalan = iddia.filter((i) => !i.ok);
      const ucbKirmizi = kalan.filter((i) => i.yon === "fis-3d").length;
      not("M14: gard her kalemde acik -> 3D fis regresyon iddialarindan " + ucbKirmizi +
          " KIRMIZI (>=8 olmali)");
      kalan.filter((i) => i.yon === "fis-3d").slice(0, 5)
        .forEach((i) => ham.push("    · yakalandi: " + i.ad + " (olculen: " + i.olculen + ")"));
      if (ucbKirmizi < 8) {
        kirmizi += 1;
        ham.push("    ❌ M14 KALDI — 3D beyan regresyon nobetcisi OLU");
      } else {
        ham.push("    ✅ M14: " + ucbKirmizi + " 3D fis regresyon iddiasi KIRMIZI");
      }
    }
  }

  // ---- M15/M16/M17: BICIM EKSENI — "kelime AYNI, BICIM BOZUK" ONCE-KIRMIZI KANITI ----
  /**
   * 🔴 BU BLOK NE KANITLAR: her mutant, yasak/beklenen KELIMEYI oldugu gibi birakir ve
   * yalnizca YAPIYI bozar. Olculen iki sayi:
   *   ESKI (set 11, kelime arayan iddialar) -> 0 KIRMIZI olmali (yani gecirir; borcun sebebi)
   *   YENI (set 11b, bicim iddialari)       -> >=1 KIRMIZI olmali (yani yakalar)
   * Ikisi birden tutmazsa bu blok KIRMIZI yanar. Boylece "bicim iddiasi gercekten yuk
   * tasiyor mu" sorusu her kosumda YENIDEN olculur, bir kereye mahsus rapor cumlesi degil.
   */
  /** shop/src altindaki HERHANGI bir dosyayi mutasyona ugratip modulleri birlikte yukler. */
  async function srcMutanti(etiket, dosya, capa, yerine) {
    if ((KAYNAKLAR[dosya] || "").split(capa).length - 1 !== 1) {
      return { hata: "capa kayip/coklu (" + dosya + ")" };
    }
    const yeni = Object.assign({}, KAYNAKLAR);
    yeni[dosya] = KAYNAKLAR[dosya].replace(capa, yerine);
    const dizin = dizinKur(etiket, yeni);
    return { mod: await modulYukle(dizin), eposta: await epostaYukle(dizin) };
  }

  const BICIM_MUTANTLARI = [
    { kod: "M15a", yon: "bicim-iyzico", dosya: "index.js",
      ad: "iyzico kalem adinda beyan ayraci ', ' -> ' / ' (kelimeler AYNI)",
      capa: 'const secim = kalemSecimi(s, ", ");',
      yerine: 'const secim = kalemSecimi(s, " / ");' },
    { kod: "M15b", yon: "bicim-iyzico", dosya: "index.js",
      ad: "parantez KOSULSUZ acilir -> fiziksel kalem adi 'Sinama urunu ()' olur",
      capa: '(parantez ? " (" + parantez + ")" : "")',
      yerine: '(" (" + parantez + ")")' },
    { kod: "M15c", yon: "bicim-iyzico", dosya: "index.js",
      ad: "parantez HIC acilmaz -> beyan ada bitisik yazilir (kelimeler AYNI)",
      capa: '(parantez ? " (" + parantez + ")" : "")',
      yerine: '(parantez ? " " + parantez : "")' },
    { kod: "M16a", yon: "bicim-kolon", dosya: "index.js",
      ad: "kolonda BOS beyan elenmiyor -> karma sepette '+ASA' (ucu acik dize)",
      capa: 'return [...new Set((satirlar || []).map(sec).filter(Boolean))].join("+");',
      yerine: 'return [...new Set((satirlar || []).map(sec))].join("+");' },
    { kod: "M16b", yon: "bicim-kolon", dosya: "index.js",
      ad: "kolonda BENZERSIZLIK yok -> iki satirda 'turuncu+turuncu'",
      capa: 'return [...new Set((satirlar || []).map(sec).filter(Boolean))].join("+");',
      yerine: 'return (satirlar || []).map(sec).filter(Boolean).join("+");' },
    { kod: "M16c", yon: "bicim-kolon", dosya: "index.js",
      ad: "filament ve renk KOLONLARI YER DEGISTIRDI (kart yolu; her iki kelime de govdede)",
      capa: '    kolonBirlestir(satirlar, (s) => s.malzeme),\n' +
            '    // "Diğer" renkte musterinin yazdigi renk kaydedilir (uretim bunu okur), yoksa liste rengi\n' +
            '    kolonBirlestir(satirlar, (s) => s.renk_ozel || s.renk),',
      yerine: '    kolonBirlestir(satirlar, (s) => s.renk_ozel || s.renk),\n' +
              '    // MUTANT: kolonlar yer degistirdi\n' +
              '    kolonBirlestir(satirlar, (s) => s.malzeme),' },
    { kod: "M17a", yon: "bicim-yonet", dosya: "yonet.js",
      ad: "yonetim kaleminde `tur` ham gecirilir -> 3D'de alan JSON'dan DUSER",
      capa: '        tur: k.tur === "fiziksel" ? "fiziksel" : "",',
      yerine: '        tur: k.tur,' },
    { kod: "M17b", yon: "bicim-yonet", dosya: "yonet.js",
      ad: "yonetim kaleminde `tur` DAIMA bos -> hazir ticari mal isareti kaybolur",
      capa: '        tur: k.tur === "fiziksel" ? "fiziksel" : "",',
      yerine: '        tur: "",' },
    { kod: "M17c", yon: "bicim-yonet", dosya: "yonet.js",
      ad: "baskiOnerisi'nin fiziksel dali silindi -> boya kutusuna URETIM onerisi basilir",
      capa: '  if (satir && satir.tur === "fiziksel") {\n' +
            '    return "Hazır ticari ürün — 3D baskı YOK, stoktan gönderilir.";\n' +
            '  }\n',
      yerine: "" },
  ];

  for (const mt of BICIM_MUTANTLARI) {
    ham.push("  -- " + mt.kod + ": " + mt.ad + " --");
    const m = await srcMutanti(mt.kod.toLowerCase() + "src", mt.dosya, mt.capa, mt.yerine);
    if (m.hata) {
      kirmizi += 1;
      ham.push("    ❌ " + mt.kod + " mutasyonu UYGULANAMADI — " + m.hata);
      continue;
    }
    const eski = (await fisIddialari(m.mod, m.eposta)).filter((i) => !i.ok).length;
    const yeni = (await bicimIddialari(m.mod)).filter((i) => !i.ok);
    const icKirmizi = yeni.filter((i) => i.yon === mt.yon);
    const disKirmizi = yeni.length - icKirmizi.length;
    not(mt.kod + ": ESKI (kelime arayan set 11) kirmizi=" + eski + " (0 olmali — borcun " +
        "sebebi tam olarak bu) · YENI (bicim, " + mt.yon + ") kirmizi=" + icKirmizi.length +
        " (>=1 olmali) · eksen disi bicim kirmizi=" + disKirmizi);
    icKirmizi.slice(0, 3).forEach(
      (i) => ham.push("    · yakalandi: " + i.ad + " (olculen: " + i.olculen + ")"));
    if (eski !== 0 || icKirmizi.length < 1) {
      kirmizi += 1;
      ham.push("    ❌ " + mt.kod + " KALDI — " + (icKirmizi.length < 1
        ? "bicim iddiasi bu bozulmayi GORMUYOR (iddia olu)"
        : "eski kelime iddiasi da yandi: once-kirmizi kaniti bu mutantla ARTIK kurulamaz, " +
          "mutant ya da iddia guncellenmeli"));
    } else {
      ham.push("    ✅ " + mt.kod + ": kelime iddiasi GECIRDI (0), bicim iddiasi YAKALADI (" +
               icKirmizi.length + ")");
    }
  }

  // ---- M9: LIMITER ESKI (YANLIS) SEMANTIGE DONDURULDU: tam `limit` kadar gecirir ----
  // 29 Tem olcumu: gercek binding limit+1 gecirir (ilk 429 = 62. istek). Iddia bu OLCUME
  // capali olmali; "tam limit kadar gecer" varsayimina donulurse set 9.2 KIRMIZI yanmali.
  ham.push("  -- M9: sahte limiter 'tam limit kadar gecer' varsayimina donduruldu --");
  const m9Sayac = new Map();
  const m9Limiter = {
    cagri: 0, patlat: false,
    sifirla() { m9Sayac.clear(); },
    async limit(arg) {
      const k = (arg && arg.key) || "yok";
      const n = (m9Sayac.get(k) || 0) + 1;
      m9Sayac.set(k, n);
      return { success: n <= CAP };            // ESKI/YANLIS semantik (limit+1 DEGIL)
    },
  };
  const m9ci = await cokIsolate(YENI_DIZIN, ILK_RED, "198.51.100.13", m9Limiter);
  const m9Ilk = m9ci.kodlar.indexOf(429) + 1;
  // Set 9.2'nin iddialarini AYNEN mutant sonuca uygula:
  const m9Kirmizi = (m9ci.ikiyuz !== GECEN) || (m9ci.redd !== 1) ||
                    (m9ci.kodlar.indexOf(429) !== GECEN);
  not("M9: eski semantikle " + ILK_RED + " istek -> 200:" + m9ci.ikiyuz + " / 429:" + m9ci.redd +
      "; ilk 429 = " + m9Ilk + ". istek (olculen gercek: " + ILK_RED + ".) -> set 9.2 iddialari " +
      (m9Kirmizi ? "KIRMIZI" : "YESIL"));
  if (!m9Kirmizi || m9Ilk !== CAP + 1) {
    kirmizi += 1;
    ham.push("    ❌ M9 KALDI — 9.2 iddiasi olculen limit+1 semantigine CAPALI DEGIL");
  } else {
    ham.push("    ✅ M9: semantik " + ILK_RED + ". -> " + m9Ilk +
             ". kaydirilinca set 9.2 KIRMIZI yanar");
  }
}

// ------------------------------------------------------------------ kosum sonu
console.log(ham.join("\n"));
console.log("");
console.log(kirmizi === 0 ? "✅ HEPSI GECTI (" + setSayisi + "/" + setSayisi + " set)"
                          : "❌ " + kirmizi + "/" + setSayisi + " set KALDI");
process.exit(kirmizi === 0 ? 0 : 1);
