#!/usr/bin/env node
/**
 * PRUVO shop — K252 SIPARIS DURUM SECICI KABUL KAPISI.
 *
 *   node shop/test/siparis-durum-secici.mjs
 *
 * OLCTUGU HUKUM (tools/paket-siparis-durum-secici.md §2, Okan karari 20 Agu 2026):
 *   (A) OPERASYON  — 'uretimde' · 'tamamlandi' · 'iptal' her mevcut durumdan secilir,
 *                    GERI ALMA dahil ('tamamlandi' -> 'uretimde' GECERLI).
 *   (B) 'kargolandi' ISTISNA — /yonet/durum onu 400 'kargo-ucunu-kullan' ile reddeder;
 *                    tek yol firma+kod isteyen AYRI KARGO ucudur. Panel secicisinde YOK.
 *   (C) ODEME durumlari elle setlenemez; TEK istisna 'odendi'ye GERI ALMA.
 *   (D) Panelin sundugu kume SUNUCUNUN kabul kumesinden TURETILIR (ikinci liste YASAK).
 *
 * NASIL: iki AYRI eksen, iki AYRI teknik — bilerek.
 *   SUNUCU ekseni : shop/src/yonet.js DOGRUDAN import edilir ve GERCEK `yonet()` router'i
 *                   sahte Request/env ile cagrilir (wa-siparis.mjs deseni). Yani olculen
 *                   sey ucun KENDISIDIR; saf fonksiyonun kopyasi DEGIL.
 *   PANEL ekseni  : sayfa JS'i HAM KAYNAK olarak cekilip vm'de kosturulur
 *                   (panel-kaynak.mjs deseni). KOPYA YAZILMAZ.
 *   TURETME ⑦    : panelin bastigi <option> kumesi, AYNI mevcut durum icin ucun
 *                   GERCEKTEN 200 dondurdugu hedefler kumesiyle karsilastirilir. Kume
 *                   uc uzerinden UCTAN UCA olculur — `izinliHedefler`in donduruguyle
 *                   kendi kendini dogrulamaz (tautoloji olurdu).
 *
 * 🔴 SEBEP DE DOGRULANIR: 400 gormek YETMEZ ([[sahte-bagimlilik-sekli-negatif-blogu-
 * kutsar]]). Her negatif iddia hem KODU hem `hata` ALANINI iddia eder; ayrica D1'e
 * YAZMA OLMADIGI olculur (yazma sayaci), yoksa "reddetti" derken satir degismis olabilirdi.
 *
 * 🔴 FIKSTUR UYDURMADIR: gercek musteri verisi/telefon/adres bu dosyaya YAZILMAZ.
 *
 * ONCE-KIRMIZI KANITI (mutantlar, tools/siparis-durum-mutasyon.py — gecici AYNAYA
 * uygulanir, calisma agacina YAZMAZ):
 *   M1 DARLIK    : /durum'daki 'kargolandi' reddi kaldirilir      -> ③ OLUR, ①②④ YASAR
 *   M2 TAHSILAT  : 'odendi' "yalniz geri alma" sarti kaldirilir   -> ④ OLUR, ⑤ YASAR
 *   M3 IKIZ LISTE: panele elle fazladan bir durum eklenir         -> ⑦ OLUR, ①②③ YASAR
 *   K0 KONTROL   : ilgisiz kol (rozet rengi) bozulur              -> HICBIRI OLMEZ
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (kaynak capasi bulunamadi).
 */

// ---- JSON IMPORT KOPRUSU (test altyapisi; uretim kodunu ETKILEMEZ) -------------
// Gerekce birebir shop/test/wa-siparis.mjs'teki gibidir: yonet.js -> semalar.js ->
// jenerator/urunler/*.json zinciri import attribute'suz alir; ciplak node duser.
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) { return { ...r, importAttributes: { type: 'json' } }; }" +
  "  return r; }"));
// KDV/adet kurallari TEK KAYNAK /secenekler.js (IIFE). Worker'da index.js import eder;
// burada yonet.js'i TEK BASINA yukledigimiz icin ayni yan etkiyi uretiriz.
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const req = createRequire(import.meta.url);
req(path.join(BURASI, "..", "..", "secenekler.js"));

// Mutasyon harness'i gecici AYNAYA yazar ve bu degiskenle hedef gosterir.
const KAYNAK_YOL = process.env.PRUVO_YONET_KAYNAK || path.join(BURASI, "..", "src", "yonet.js");
const KAYNAK = fs.readFileSync(KAYNAK_YOL, "utf8");
const { yonet } = await import(url.pathToFileURL(KAYNAK_YOL).href);

let gecen = 0, kalan = 0;
const olen = new Set();            // KIRMIZI yanan iddia etiketleri (mutant atfi icin)
function ol(etiket, ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + etiket + " " + ad); }
  else {
    kalan++; olen.add(etiket);
    console.log("  ❌ " + etiket + " " + ad + (detay ? " — " + detay : ""));
  }
}

const YONET_ANAHTAR = "y".repeat(48);

// ---------------------------------------------------------------- D1 taklidi
/**
 * `siparis` : siparisGetir'in dondurecegi satir.
 * `env.yazmalar` : BASARIYLA kosan INSERT/UPDATE kayitlari {sql, args}.
 * UPDATE'in bind parametreleri saklanir — ① icin durum_gecmisi'ne satir dustugu ve
 * kargo kolonlarina DOKUNULMADIGI oradan okunur.
 */
function mockEnv(siparis, listeSatirlari) {
  const yazmalar = [];
  return {
    yazmalar,
    YONET_ANAHTAR,
    SITE_URL: "https://ornek-site.test",
    KATALOG: {
      prepare(sql) {
        const kayit = { sql, args: [] };
        const calistir = async (kip) => {
          if (/^\s*(INSERT|UPDATE)/i.test(sql)) {
            yazmalar.push(kayit);
            return { meta: { changes: 1 } };
          }
          // Zenginlestirme sorgulari: katalog kaydi / kaynak kaydi YOK varsayimi.
          // 🔴 Bu iki kol GENEL `all` kolundan ONCE gelmeli, yoksa /liste satirlari
          // yanlis sorguya dondurulur ve fikstur sessizce anlamsizlasir.
          if (/FROM urunler/.test(sql)) { return { results: [] }; }
          if (/FROM urun_kaynak/.test(sql)) { return { results: [] }; }
          if (/^SELECT siparis_no, tarih, durum, durum_gecmisi/.test(sql)) {
            return siparis || null;
          }
          if (kip === "all") { return { results: listeSatirlari || [] }; }
          return null;
        };
        return {
          bind(...args) { kayit.args = args; return this; },
          async run() { return calistir("run"); },
          async all() { return calistir("all"); },
          async first() { return calistir("first"); },
        };
      },
    },
  };
}

/** BICIMI taklit eden fikstur — gercek veri DEGIL. */
function satir(durum, ekstra) {
  return {
    siparis_no: "PR-TEST-000001", tarih: "2026-08-20T10:00:00Z", durum: durum,
    durum_gecmisi: JSON.stringify([{ d: durum, z: "2026-08-20T10:00:00Z" }]),
    urunler: JSON.stringify([]), tutar_kurus: 125000, kargo_kurus: 9000, kdv_kurus: 22500,
    odeme_yontemi: "kart", atif: "", kanal: "site",
    musteri_ad: "Ornek Musteri", musteri_eposta: "", musteri_adres: "Ornek Mah. 1",
    kargo_firma: null, kargo_kodu: null,
    ...(ekstra || {}),
  };
}

const URL_YONET = new URL("https://ornek-site.test/api/shop/yonet/durum");
const ctxSahte = { waitUntil() {} };

function istek(govde) {
  return {
    method: "POST",
    headers: { get: (h) => (h === "X-Yonet-Anahtar" ? YONET_ANAHTAR : null) },
    json: async () => govde,
  };
}

/** POST /yonet/durum — GERCEK router uzerinden. Doner {kod, govde, env}. */
async function durumCagir(mevcut, hedef, ekstra) {
  const env = mockEnv(satir(mevcut, ekstra));
  const c = await yonet(istek({ siparis_no: "PR-TEST-000001", durum: hedef }),
                        env, URL_YONET, ctxSahte, "/durum", undefined);
  let govde = null;
  try { govde = await c.json(); } catch (e) { govde = null; }
  return { kod: c.status, govde: govde, env: env };
}

/** POST /yonet/kargo — firma+kod ile. */
async function kargoCagir(mevcut, firma, kod) {
  const env = mockEnv(satir(mevcut));
  const c = await yonet({
    method: "POST",
    headers: { get: (h) => (h === "X-Yonet-Anahtar" ? YONET_ANAHTAR : null) },
    json: async () => ({ siparis_no: "PR-TEST-000001", kargo_firma: firma, kargo_kodu: kod }),
  }, env, new URL("https://ornek-site.test/api/shop/yonet/kargo"), ctxSahte, "/kargo", undefined);
  let govde = null;
  try { govde = await c.json(); } catch (e) { govde = null; }
  return { kod: c.status, govde: govde, env: env };
}

const OPERASYON_MEVCUT = ["bekliyor", "odendi", "basarisiz", "incele", "havale-bekliyor",
                          "uretimde", "kargolandi", "tamamlandi"];

// ================================================================ ① KARGOSUZ TAMAMLAMA
console.log("\n① kargosuz tamamlama — 'uretimde' -> 'tamamlandi' (takip kodu ISTEMEZ)");
{
  const r = await durumCagir("uretimde", "tamamlandi");
  ol("①", "200 doner", r.kod === 200 && r.govde && r.govde.ok === true,
    "kod=" + r.kod + " govde=" + JSON.stringify(r.govde));
  const up = r.env.yazmalar.find((y) => /^UPDATE siparisler/.test(y.sql));
  ol("①a", "TEK bir UPDATE siparisler kostu", !!up && r.env.yazmalar.length === 1,
    "yazma=" + r.env.yazmalar.length);
  // 🔴 kargo kolonlari: UPDATE cumlesi onlara DEGMEMELI (NULL kalir).
  ol("①b", "UPDATE 'kargo_kodu'/'kargo_firma' kolonlarina DOKUNMUYOR (NULL kalir)",
    !!up && !/kargo_kodu/.test(up.sql) && !/kargo_firma/.test(up.sql),
    up ? up.sql : "(UPDATE yok)");
  // durum_gecmisi'ne satir DUSTU mu? (bind parametrelerinden okunur)
  const gecmisArg = up ? up.args.find((a) => typeof a === "string" && /"d":"tamamlandi"/.test(a)) : null;
  ol("①c", "durum_gecmisi'ne 'tamamlandi' satiri DUSTU",
    !!gecmisArg && JSON.parse(gecmisArg).some((k) => k.d === "tamamlandi"),
    up ? JSON.stringify(up.args) : "(UPDATE yok)");
  ol("①d", "CAS korunuyor: UPDATE ... WHERE siparis_no = ? AND durum = ?",
    !!up && /WHERE siparis_no = \? AND durum = \?/.test(up.sql), up ? up.sql : "-");
}

// ================================================================ ② GERI ALMA
console.log("\n② geri alma — 'tamamlandi' -> 'uretimde'");
{
  const r = await durumCagir("tamamlandi", "uretimde");
  ol("②", "200 doner (yanlis isaretleme GERI ALINABILIR)",
    r.kod === 200 && r.govde && r.govde.durum === "uretimde",
    "kod=" + r.kod + " govde=" + JSON.stringify(r.govde));
}

// ================================================================ ③ DARLIK
console.log("\n③ darlik — /durum hedef 'kargolandi' UC mevcut durumdan REDDEDILIR");
{
  for (const mevcut of ["odendi", "uretimde", "tamamlandi"]) {
    const r = await durumCagir(mevcut, "kargolandi");
    ol("③", "'" + mevcut + "' -> 'kargolandi' = 400 'kargo-ucunu-kullan'",
      r.kod === 400 && r.govde && r.govde.hata === "kargo-ucunu-kullan",
      "kod=" + r.kod + " hata=" + (r.govde && r.govde.hata));
    ol("③", "'" + mevcut + "' -> 'kargolandi' D1'e YAZMA YOK",
      r.env.yazmalar.length === 0, "yazma=" + r.env.yazmalar.length);
  }
  // POZITIF KONTROL: reddin sebebi "uc bozuk" DEGIL — /kargo ucu AYNI gecisi YAPAR.
  const k = await kargoCagir("uretimde", "Ornek Kargo", "TEST123456");
  ol("③k", "/kargo ucu firma+kod ile AYNI gecisi YAPIYOR (uc saglam, redde ozgu)",
    k.kod === 200 && k.env.yazmalar.some((y) => /kargo_kodu = \?/.test(y.sql)),
    "kod=" + k.kod);
  const kSiz = await kargoCagir("uretimde", "Ornek Kargo", "");
  ol("③k2", "/kargo takip kodu BOSSA 400 (kodsuz 'kargolandi' satiri OLUSAMAZ)",
    kSiz.kod === 400 && kSiz.govde && kSiz.govde.hata === "kargo-kodu" &&
    kSiz.env.yazmalar.length === 0, "kod=" + kSiz.kod);
}

// ================================================================ ④ ODEME EKSENI
console.log("\n④ odeme ekseni — elle 'odendi' setlenemez (tahsilat yalani kapisi)");
{
  for (const mevcut of ["bekliyor", "basarisiz", "havale-bekliyor", "incele"]) {
    const r = await durumCagir(mevcut, "odendi");
    ol("④", "'" + mevcut + "' -> 'odendi' = 400 'odeme-durumu-elle-setlenemez'",
      r.kod === 400 && r.govde && r.govde.hata === "odeme-durumu-elle-setlenemez",
      "kod=" + r.kod + " hata=" + (r.govde && r.govde.hata));
    ol("④", "'" + mevcut + "' -> 'odendi' D1'e YAZMA YOK (tahsilat satiri olusmadi)",
      r.env.yazmalar.length === 0, "yazma=" + r.env.yazmalar.length);
  }
  // Diger odeme durumlari da hedef olarak KAPALI (yalniz 'odendi' degil).
  for (const hedef of ["bekliyor", "basarisiz", "havale-bekliyor", "incele"]) {
    const r = await durumCagir("uretimde", hedef);
    ol("④b", "'uretimde' -> '" + hedef + "' = 400 (odeme ekseni elle setlenemez)",
      r.kod === 400 && r.govde && r.govde.hata === "odeme-durumu-elle-setlenemez",
      "kod=" + r.kod + " hata=" + (r.govde && r.govde.hata));
  }
}

// ================================================================ ⑤ GERI ALMA ISTISNASI
console.log("\n⑤ geri alma istisnasi — {uretimde, kargolandi, tamamlandi} -> 'odendi'");
{
  for (const mevcut of ["tamamlandi", "uretimde", "kargolandi"]) {
    const r = await durumCagir(mevcut, "odendi");
    ol("⑤", "'" + mevcut + "' -> 'odendi' = 200 (siparis zaten odenmisti)",
      r.kod === 200 && r.govde && r.govde.durum === "odendi",
      "kod=" + r.kod + " govde=" + JSON.stringify(r.govde));
  }
  // Kart siparisi geri alinip tekrar 'odendi' yapilirsa Purchase TEKRARLANMAMALI:
  // 3. katman (kalici iz "o":1) korunuyor mu?
  const izli = await durumCagir("uretimde", "odendi", {
    durum_gecmisi: JSON.stringify([{ d: "odendi", z: "2026-08-20T09:00:00Z", o: 1 },
                                   { d: "uretimde", z: "2026-08-20T09:30:00Z" }]),
  });
  const upIzli = izli.env.yazmalar.find((y) => /^UPDATE siparisler/.test(y.sql));
  const yeniGecmis = upIzli ? upIzli.args.find((a) => typeof a === "string" && /"d":"odendi"/.test(a)) : null;
  const yeniKayit = yeniGecmis ? JSON.parse(yeniGecmis).slice(-1)[0] : null;
  ol("⑤i", "onceden olcum izi ('o':1) VARSA geri alma turunda YENI iz YAZILMAZ "
    + "(Purchase tekrarlanmaz)",
    izli.kod === 200 && !!yeniKayit && yeniKayit.d === "odendi" && yeniKayit.o !== 1,
    "yeni kayit=" + JSON.stringify(yeniKayit));
}

// ================================================================ ⑥ IPTAL REGRESYONU
console.log("\n⑥ 'iptal' her durumdan (mevcut 'iptal' HARIC) — bugunku davranis AYNEN");
{
  let hepsi200 = true, detay = [];
  for (const mevcut of OPERASYON_MEVCUT) {
    const r = await durumCagir(mevcut, "iptal");
    if (!(r.kod === 200 && r.govde && r.govde.durum === "iptal")) {
      hepsi200 = false; detay.push(mevcut + "=" + r.kod);
    }
  }
  ol("⑥", "8 mevcut durumun HEPSINDEN 'iptal' = 200", hepsi200, detay.join(","));
  const r = await durumCagir("iptal", "iptal");
  ol("⑥a", "'iptal' -> 'iptal' = 400 'gecersiz-gecis' (kendi uzerine gecis YOK)",
    r.kod === 400 && r.govde && r.govde.hata === "gecersiz-gecis" &&
    r.env.yazmalar.length === 0, "kod=" + r.kod + " hata=" + (r.govde && r.govde.hata));
}

// ================================================================ ⑦ PANEL/SUNUCU TEK KAYNAK
console.log("\n⑦ panel/sunucu TEK KAYNAK — secici kumesi ucun kabul kumesinden TURER");

/** Kaynaktan [baslangic, bitis) dilimi. Capa yoksa null (fail-loud). */
function dilimAl(metin, baslangic, bitis) {
  const b = metin.indexOf(baslangic);
  const s = b >= 0 ? metin.indexOf(bitis, b + baslangic.length) : -1;
  return (b >= 0 && s > b) ? metin.slice(b, s) : null;
}
function sablonCoz(s) { return s.replace(/\\\\/g, "\\"); }

const panelKaynak = sablonCoz(dilimAl(KAYNAK, "function esc(s){", "async function yukle(){") || "");
if (!panelKaynak) {
  console.error("KAYNAK CAPASI BULUNAMADI (sayfa JS blogu) — yonet.js yapisi degisti mi?");
  process.exit(3);
}
const panel = { document: null };
vm.createContext(panel);
vm.runInContext(panelKaynak, panel, { filename: "yonet-sayfa.js" });
const kartHtml = panel.kartHtml;
if (typeof kartHtml !== "function") {
  console.error("SAYFA FONKSIYONU CEKILEMEDI (kartHtml) — OLCULEMEDI");
  process.exit(3);
}

/**
 * GET /yonet/liste uzerinden sunucunun O SIPARIS icin verdigi `izinli_gecisler`.
 * 🔴 `null` DONERSE bu "bos kume" DEGIL "OLCULEMEDI"dir — cagiran onu KIRMIZI sayar,
 * yoksa liste yuzeyi sessizce olculmeden ⑦ yesil yanabilirdi.
 */
async function listeIzinliGecisler(mevcut) {
  const env = mockEnv(satir(mevcut), [satir(mevcut)]);
  const c = await yonet(
    { method: "GET",
      headers: { get: (h) => (h === "X-Yonet-Anahtar" ? YONET_ANAHTAR : null) } },
    env, new URL("https://ornek-site.test/api/shop/yonet/liste"),
    ctxSahte, "/liste", undefined);
  if (c.status !== 200) { return null; }
  const g = await c.json();
  const s = (g.siparisler || [])[0];
  return (s && Array.isArray(s.izinli_gecisler)) ? s.izinli_gecisler : null;
}

function paneldekiSecenekler(html) {
  const blok = dilimAl(html, '<div class="durumsecici">', "</div>") || "";
  const out = [];
  const re = /<option value="([^"]*)">/g;
  let m;
  while ((m = re.exec(blok)) !== null) { out.push(m[1]); }
  return out;
}

function kartFikstur(mevcut, izinli) {
  return {
    siparis_no: "PR-TEST-" + mevcut, tarih: "2026-08-20T10:00:00Z", durum: mevcut,
    kanal: "site", dis_no: "", odeme_yontemi: "kart",
    tutar_kurus: 125000, kargo_kurus: 9000, kdv_kurus: 22500,
    kargo_firma: "", kargo_kodu: "", durum_gecmisi: [], izinli_gecisler: izinli,
    musteri: { ad: "Ornek Musteri", tel: "0500 000 00 00", eposta: "ornek@ornek.invalid",
               adres: "Ornek Mah. 1" },
    kalemler: [], musteri_notu: "", yazdir_komut: "python3 tools/yazdir.py PR-TEST",
  };
}

{
  // 🔴 UCTAN UCA TURETME: her mevcut durum icin (a) ucun GERCEKTEN 200 dondurdugu
  // hedefler, (b) /liste'nin verdigi `izinli_gecisler`, (c) panelin bastigi <option>
  // kumesi — UCU DE AYNI olmali. (a) ekseni kumeyi ucun DAVRANISINDAN olcer, yani
  // `izinliHedefler` kendi kendini dogrulamaz.
  let sapan = [], kargoluDurum = [];
  for (const mevcut of OPERASYON_MEVCUT.concat(["iptal"])) {
    const kabulEdilen = [];
    for (const hedef of ["bekliyor", "odendi", "basarisiz", "incele", "havale-bekliyor",
                         "uretimde", "kargolandi", "tamamlandi", "iptal"]) {
      const r = await durumCagir(mevcut, hedef);
      if (r.kod === 200) { kabulEdilen.push(hedef); }
    }
    const listeden = await listeIzinliGecisler(mevcut);
    if (listeden === null) {
      sapan.push(mevcut + ": /liste OLCULEMEDI (izinli_gecisler okunamadi)");
      continue;
    }
    const html = kartHtml(kartFikstur(mevcut, listeden));
    const panelden = paneldekiSecenekler(html);
    const a = JSON.stringify([...kabulEdilen].sort());
    const b = JSON.stringify([...listeden].sort());
    const c = JSON.stringify([...panelden].sort());
    if (!(a === b && b === c)) { sapan.push(mevcut + ": uc=" + a + " liste=" + b + " panel=" + c); }
    if (panelden.indexOf("kargolandi") >= 0) { kargoluDurum.push(mevcut); }
  }
  ol("⑦", "9 mevcut durumun HEPSINDE uc-kabul kumesi == /liste kumesi == panel <option> kumesi",
    sapan.length === 0, sapan.join(" | "));
  ol("⑦a", "'Kargolandi' secicide 0 kez geciyor (hicbir mevcut durumda)",
    kargoluDurum.length === 0, "gecen durumlar=" + kargoluDurum.join(","));
  // Panelde ELLE yazilmis ikinci bir durum listesi olmadigi KAYNAK ekseninde de olculur.
  // 🔴 MENZIL DAR TUTULUR: olculen sey SECENEK URETIMIDIR, kartin tamami degil. kartHtml
  // govdesinde bagimsiz ve MESRU durum literalleri vardir (kargo formu yalniz 'uretimde'de
  // basilir, kart yalniz 'odendi'de ACIK dogar) — onlari yasaklamak kapiyi ambiyans
  // olcumune cevirirdi ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).
  const secenekBlok = dilimAl(panelKaynak, " var secenekler=", " var eylem=") || "";
  if (!secenekBlok) {
    console.error("KAYNAK CAPASI BULUNAMADI (secenek uretimi) — kartHtml yapisi degisti mi?");
    process.exit(3);
  }
  const durumLiterali = (secenekBlok.match(
    /"(bekliyor|odendi|basarisiz|incele|havale-bekliyor|uretimde|kargolandi|tamamlandi|iptal)"/g) || []);
  ol("⑦b", "secenek uretiminde ELLE yazilmis durum literali YOK (kume TURETILIR)",
    durumLiterali.length === 0, "literaller=" + durumLiterali.join(","));
  ol("⑦b2", "secenek uretiminin TEK kaynagi `s.izinli_gecisler` (ikinci liste/concat YOK)",
    /s\.izinli_gecisler\.map\(/.test(secenekBlok) && !/concat\(|\[\s*"/.test(secenekBlok),
    secenekBlok.trim().slice(0, 200));
  ol("⑦c", "secici <select> + 'Uygula' butonu kartta VAR",
    /<select id="dd-/.test(kartHtml(kartFikstur("uretimde", ["tamamlandi", "iptal"]))) &&
    /durumUygula\(/.test(kartHtml(kartFikstur("uretimde", ["tamamlandi", "iptal"]))));
  ol("⑦d", "mevcut 'iptal' butonu ve kargo formu YERINDE",
    /class="sil" onclick="durumDegis\(/.test(kartHtml(kartFikstur("uretimde", ["tamamlandi", "iptal"]))) &&
    /Kargolandı olarak işaretle/.test(kartHtml(kartFikstur("uretimde", ["tamamlandi", "iptal"]))));
}

// ================================================================ SONUC
console.log("\nTOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
console.log("OLEN_IDDIALAR=" + (olen.size ? [...olen].sort().join(",") : "-"));
process.exit(kalan === 0 ? 0 : 1);
