/**
 * PRUVO shop — FANTOM PURCHASE: TARAYICI KOLU KABUL TESTI.
 *
 * NEDEN AYRI DOSYA (mimar hukmu, 20 Agu): shop/test/olcum-donus-bileti.mjs SUNUCU kolunu
 * (shop/src/olcum-bilet.js) 30+ vakayla civiliyor. Ama fantom Purchase'in TAMAMI TARAYICI
 * kolundan geliyordu: olayi atan kod index.html `odemeDonusuIsle()` icindeydi ve YALNIZCA
 * URL'ye bakiyordu. Onarimin kanitsiz kalan 20 satiri, kusurun TAM OLARAK YASADIGI yerdir.
 * Sunucuyu civileyip kusurun evini kod okumasina birakmak bu deponun olculmus sahte-yesil
 * sinifidir ([[kapinin-menzili-cagri-yeridir]]).
 *
 * NE OLCER (dordu de CALISTIRILABILIR vaka, iddia degil):
 *   N) `fetch` REJECT eder (ag yok / uc cevap vermedi) -> Purchase CAGRILMAZ (fail-closed).
 *   R) Sunucu `{ok:false}` der (bilet yanmis/uydurma) -> Purchase CAGRILMAZ.
 *   Y) Sunucu `{ok:true, value}` der -> Purchase BIR KEZ cagrilir ve `value` SUNUCUNUNKIDIR
 *      (URL'deki `t` BILEREK farkli bir sayidir: 9.000 TL. Olayda o sayi gorunurse KIRMIZI).
 *   B) URL'de bilet YOK (eski tip `/?siparis=ok&no=X&t=900000`) -> uca HIC gidilmez, olay YOK.
 *   J) Cevap JSON'u cozulemez -> olay YOK (fail-closed).
 *   S) `siparis=basarisiz` donusu -> uca gidilmez, olay YOK.
 *
 * NASIL (sahte-DOM deseni, depo idiomu): index.html'in KENDI `odemeDonusuIsle()` govdesi
 * capalarla CIKARILIR ve enjekte edilmis bir ortamda (`location`, `fetch`, `window`,
 * `PRUVO_SECENEK`, `alert`, `history`) kosturulur. Yani olculen sey uretim kaynaginin
 * KENDISIDIR — kopyasi ya da yeniden yazimi DEGIL. Capa bulunamazsa test KIRMIZI yanar
 * ("atlandi" diye bir sonuc YOKTUR — [[capa-cokmesi-arkasindaki-capalari-gizler]]).
 *
 * ⚠️ AG'A CIKMAZ, D1'E DOKUNMAZ, GERCEK PIKSELE BASMAZ, DOSYA YAZMAZ: `fetch` her vakada
 * enjekte edilen sahtedir, `window.pruvoMetaTrack` cagrilari yalnizca diziye kaydedilir.
 *
 * KOSUM:  node shop/test/olcum-donus-tarayici.mjs         (rc=0 yesil, rc=1 kirmizi)
 * MUTANT: node shop/test/olcum-donus-tarayici-mutant.mjs  (her kolu bozar, sebebini kanitlar)
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const INDEX_HTML = path.join(BURASI, "..", "..", "index.html");

/* Mutant kosumu bu degiskenle BASKA (mutasyona ugramis) bir govde metni verir; varsayilan
   index.html'in GERCEK govdesidir. Boylece mutant harness index.html'i DEGISTIRMEDEN
   (repoya iz birakmadan) ayni kabul tablosunu mutasyona karsi kosturur. */
const KAYNAK_USTU = process.env.PRUVO_TARAYICI_KAYNAK || "";

let gecen = 0;
const kalanlar = [];
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalanlar.push(ad); console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

/* ---------------------------------------------------------------------------------------
 * 1) GOVDEYI URETIM KAYNAGINDAN CIKAR
 * ------------------------------------------------------------------------------------ */
const BAS_CAPA = "function odemeDonusuIsle(){";
const SON_CAPA = "\n  }\n";

/** index.html'den `odemeDonusuIsle` govdesini capalarla cikar. FAIL-LOUD. */
function govdeyiCikar() {
  const ham = fs.readFileSync(INDEX_HTML, "utf8");
  const b = ham.indexOf(BAS_CAPA);
  if (b < 0) { return { hata: "BAS CAPA YOK (" + BAS_CAPA + ") — index.html degismis." }; }
  const s = ham.indexOf(SON_CAPA, b);
  if (s < 0) { return { hata: "SON CAPA YOK — fonksiyon kapanisi bulunamadi." }; }
  return { metin: ham.slice(b, s + SON_CAPA.length) };
}

const cikarma = KAYNAK_USTU
  ? { metin: fs.readFileSync(KAYNAK_USTU, "utf8") }
  : govdeyiCikar();

console.log("\n=== FANTOM PURCHASE — TARAYICI KOLU (kaynak: " +
  (KAYNAK_USTU ? "MUTANT" : "index.html gercek govdesi") + ") ===");

console.log("\nX) Cikarma nobetcisi (olculen sey URETIM kaynagi mi?)");
if (cikarma.hata) {
  console.log("  ❌ X0 govde CIKARILAMADI — " + cikarma.hata);
  console.log("\n=== SONUC: 0 gecti / 1 kaldi ===");
  console.log("KALAN_IDDIALAR: X0 govde cikarilamadi");
  process.exit(1);
}
const GOVDE = cikarma.metin;
/* Cikarilan metin GERCEKTEN olay kolunu tasiyor mu? Tasimiyorsa asagidaki "olay atilmadi"
   iddialari TAUTOLOJI olurdu (kod hic yoksa olay da yok). [[sahte-bagimlilik-sekli...]] */
const ZORUNLU = ["/olcum-donus", "pruvoMetaTrack", ".catch(", "q.get(\"b\")"];
const eksikJeton = ZORUNLU.filter((j) => GOVDE.indexOf(j) < 0);
ol("X0 cikarilan govde olay kolunu TASIYOR (" + ZORUNLU.join(", ") + ")",
  eksikJeton.length === 0, "eksik jeton: " + eksikJeton.join(", "));
if (eksikJeton.length) {
  console.log("\n=== SONUC: " + gecen + " gecti / " + kalanlar.length + " kaldi ===");
  console.log("KALAN_IDDIALAR: " + kalanlar.join(" | "));
  process.exit(1);
}

/* ---------------------------------------------------------------------------------------
 * 2) SAHTE ORTAM — index.html'in govdesi bunun icinde kosar
 * ------------------------------------------------------------------------------------ */
const fabrika = new Function("ortam", `
  const location = ortam.location;
  const PRUVO_SECENEK = ortam.PRUVO_SECENEK;
  const pruvoFeedId = ortam.pruvoFeedId;
  const SHOP_UC = ortam.SHOP_UC;
  const fetch = ortam.fetch;
  const window = ortam.window;
  const alert = ortam.alert;
  const history = ortam.history;
  const saveCart = ortam.saveCart;
  const updateCartFab = ortam.updateCartFab;
  let cart = ortam.cart;
  ${GOVDE}
  return odemeDonusuIsle;
`);

/** Tek vaka ortami. `fetchKolu` vakaya gore Promise doner ya da reject eder. */
function ortamKur(sorgu, fetchKolu) {
  const olaylar = [];
  const fetchCagrilari = [];
  const ortam = {
    location: { search: sorgu, pathname: "/" },
    PRUVO_SECENEK: {
      sepetYukle() { return [{ id: "urun-a" }, { id: "urun-b" }]; },
      kurusMetni(k) { return String(k); },
      KDV_YUZDE: 20,
    },
    pruvoFeedId(id) { return "PRUVO-" + id; },
    SHOP_UC: "/api/shop",
    fetch(url, secenek) {
      fetchCagrilari.push({ url: url, secenek: secenek });
      return fetchKolu(url, secenek);
    },
    window: {
      pruvoMetaTrack(olay, veri, ek) { olaylar.push({ olay, veri, ek }); },
    },
    alert() {},
    history: { replaceState() {} },
    saveCart() {},
    updateCartFab() {},
    cart: [{ id: "urun-a" }],
  };
  return { ortam, olaylar, fetchCagrilari, kos: fabrika(ortam) };
}

/** Promise zincirinin (fetch -> json -> then/catch) tamamen bosalmasini bekle. */
async function bosalt() {
  for (let i = 0; i < 12; i++) { await new Promise((r) => setTimeout(r, 0)); }
}

/* URL'deki `t` BILEREK sunucu degerinden FARKLI: 900000 kurus = 9.000 TL.
   Sunucu ise 47790 kurus -> 477.9 TL doner. Olayda 9000 gorunurse `value` URL'den geliyordur. */
const BILET = "b".repeat(32);
const SORGU_OK = "?siparis=ok&no=PR-2026-0001&t=900000&kdv=79650&b=" + BILET;
const SORGU_BILETSIZ = "?siparis=ok&no=PR-2026-0001&t=900000&kdv=79650";
const SORGU_BASARISIZ = "?siparis=basarisiz&no=PR-2026-0001";
const SUNUCU_DEGERI = 477.9;

const cevapVer = (govde) => () => Promise.resolve({ json: () => Promise.resolve(govde) });

/* ---- N) AG HATASI -> OLAY YOK ------------------------------------------------------- */
console.log("\nN) AG HATASI (fetch reject) -> Purchase CAGRILMAZ");
{
  const v = ortamKur(SORGU_OK, () => Promise.reject(new Error("ag yok")));
  let patladi = "";
  try { v.kos(); } catch (e) { patladi = (e && e.message) || String(e); }
  await bosalt();
  ol("N1 ag hatasinda Purchase ATILMADI (fail-closed)", v.olaylar.length === 0,
    "olay=" + JSON.stringify(v.olaylar));
  ol("N2 handler patlamadi (musteri sayfasi kirilmiyor)", patladi === "", patladi);
}

/* ---- R) SUNUCU ok:false -> OLAY YOK -------------------------------------------------- */
console.log("\nR) SUNUCU {ok:false} (bilet yanmis/uydurma) -> Purchase CAGRILMAZ");
{
  const v = ortamKur(SORGU_OK, cevapVer({ ok: false }));
  v.kos();
  await bosalt();
  ol("R1 sunucu ok:false iken Purchase ATILMADI", v.olaylar.length === 0,
    "olay=" + JSON.stringify(v.olaylar));
  ol("R2 uca GERCEKTEN soruldu (sessizce atlanmadi)", v.fetchCagrilari.length === 1,
    "fetch=" + v.fetchCagrilari.length);
}

/* ---- Y) SUNUCU ok:true -> TEK OLAY, value SUNUCUDAN ---------------------------------- */
console.log("\nY) SUNUCU {ok:true,value} -> Purchase BIR KEZ, value SUNUCUDAN");
{
  const v = ortamKur(SORGU_OK, cevapVer({ ok: true, value: SUNUCU_DEGERI, currency: "TRY" }));
  v.kos();
  await bosalt();
  ol("Y1 dogrulanmis donuste Purchase BIR KEZ atildi", v.olaylar.length === 1,
    "olay=" + v.olaylar.length);
  const o = v.olaylar[0] || { veri: {}, ek: {} };
  ol("Y2 value SUNUCUDAN (" + SUNUCU_DEGERI + "), URL'deki t'den (9000) DEGIL",
    o.veri.value === SUNUCU_DEGERI, "value=" + o.veri.value);
  ol("Y3 olay sozlesmesi: ad=Purchase · eventID=siparis no · currency=TRY · content_ids sepetten",
    o.olay === "Purchase" && o.ek && o.ek.eventID === "PR-2026-0001" &&
    o.veri.currency === "TRY" &&
    JSON.stringify(o.veri.content_ids) === JSON.stringify(["PRUVO-urun-a", "PRUVO-urun-b"]),
    JSON.stringify(o));
  ol("Y4 uca TEK istek gitti", v.fetchCagrilari.length === 1, "fetch=" + v.fetchCagrilari.length);
  ol("Y5 istek govdesi {no,b} tasiyor (POST /olcum-donus)",
    (v.fetchCagrilari[0] || {}).url === "/api/shop/olcum-donus" &&
    ((v.fetchCagrilari[0] || {}).secenek || {}).method === "POST" &&
    JSON.parse(((v.fetchCagrilari[0] || {}).secenek || {}).body || "{}").b === BILET,
    JSON.stringify(v.fetchCagrilari[0]));
}

/* ---- B) BILETSIZ URL -> UCA HIC GIDILMEZ --------------------------------------------- */
console.log("\nB) BILETSIZ URL (eski tip /?siparis=ok&no=X&t=900000) -> uca gidilmez, olay YOK");
{
  const v = ortamKur(SORGU_BILETSIZ,
    cevapVer({ ok: true, value: SUNUCU_DEGERI, currency: "TRY" }));
  v.kos();
  await bosalt();
  ol("B1 bilet YOKKEN uca HIC gidilmedi", v.fetchCagrilari.length === 0,
    "fetch=" + v.fetchCagrilari.length);
  ol("B2 bilet YOKKEN Purchase ATILMADI (uydurma URL satis saymaz)", v.olaylar.length === 0,
    "olay=" + JSON.stringify(v.olaylar));
}

/* ---- J) BOZUK CEVAP -> OLAY YOK ------------------------------------------------------ */
console.log("\nJ) CEVAP JSON'U COZULEMEZ -> olay YOK");
{
  const v = ortamKur(SORGU_OK,
    () => Promise.resolve({ json: () => Promise.reject(new Error("bozuk json")) }));
  v.kos();
  await bosalt();
  ol("J1 bozuk cevapta Purchase ATILMADI", v.olaylar.length === 0,
    "olay=" + JSON.stringify(v.olaylar));
}

/* ---- S) BASARISIZ DONUS -> UCA GIDILMEZ ---------------------------------------------- */
console.log("\nS) siparis=basarisiz donusu -> uca gidilmez, olay YOK");
{
  const v = ortamKur(SORGU_BASARISIZ,
    cevapVer({ ok: true, value: SUNUCU_DEGERI, currency: "TRY" }));
  v.kos();
  await bosalt();
  ol("S1 basarisiz donuste uca gidilmedi", v.fetchCagrilari.length === 0,
    "fetch=" + v.fetchCagrilari.length);
  ol("S2 basarisiz donuste Purchase ATILMADI", v.olaylar.length === 0,
    "olay=" + JSON.stringify(v.olaylar));
}

/* ---- T0) TAUTOLOJI NOBETCISI --------------------------------------------------------- */
/* "Olay atilmadi" diyen bes vaka, kod HIC KOSMADIGI icin de yesil yanabilirdi. Y blogu
   AYNI govdenin olayi GERCEKTEN atabildigini gosterir; atmiyorsa negatif vakalar kanit
   degildir ([[sahte-bagimlilik-sekli-negatif-blogu-kutsar]]). */
console.log("\nT0) Tautoloji nobetcisi (govde olayi ATABILIYOR mu?)");
{
  const v = ortamKur(SORGU_OK, cevapVer({ ok: true, value: SUNUCU_DEGERI, currency: "TRY" }));
  v.kos();
  await bosalt();
  ol("T0a ayni govde POZITIF kolda olay ATIYOR (negatif vakalar bos-kosum degil)",
    v.olaylar.length === 1, "olay=" + v.olaylar.length);
}

/* ---- SONUC --------------------------------------------------------------------------- */
console.log("\n=== SONUC: " + gecen + " gecti / " + kalanlar.length + " kaldi ===");
if (kalanlar.length) {
  console.log("KALAN_IDDIALAR: " + kalanlar.join(" | "));
}
process.exit(kalanlar.length ? 1 : 0);
