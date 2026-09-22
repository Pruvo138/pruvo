#!/usr/bin/env node
"use strict";
/**
 * ADAPTIF HIZ FRENI KABUL TESTI — parite-ortak.js `canliGetir` 429 kolu.
 *
 *   node tools/parite-hiz-freni-test.js         # 0 = gecti, 1 = kirmizi
 *
 * AGSIZ: global `fetch` sahte bir fonksiyonla degistirilir; hicbir canli istek ATILMAZ,
 * hicbir dosya YAZILMAZ. Bu yuzden CI'da bloklayici kosabilir.
 *
 * NE OLCER (sekiz AYRI eksen — biri otekini maskelemesin):
 *   V1 VARSAYILAN YOL DOKUNULMADI: 429 gorulmeyen kosumda fren ARALIGI 0 kalir ve
 *      HICBIR ek bekleme uretilmez. Bu, "bloklayici testi yavaslatma" sartinin
 *      calistirilabilir karsiligidir — yorumda degil, OLCUMDE.
 *   V2 FREN DEVREYE GIRER: tek 429 goruldugunde aralik TABAN'a ciker ve istek
 *      yeniden denenerek BASARIYLA doner (eski kod da bunu yapardi, ama 3 hakla).
 *   V3 HAK ARTTI: 3'ten fazla ardisik 429'dan SONRA gelen 200 hala YAKALANIR.
 *      Eski DENEME=3 ile bu vaka KIRMIZI olurdu (olculen ariza sinifi budur).
 *   V4 HAK FAIL-CLOSED: 429 hakki (DENEME_429) tukendiginde ESKISI GIBI OlcumHatasi("429")
 *      olur -> kosum sonsuza surtuklenmez, "olcemedim" YESILE donusmez.
 *   V5 ESZAMANLI ISCILER TEK ARALIKTAN gecer: fren aciktayken 4 paralel istek
 *      birbirinin uzerine binmez (rezervasyon senkron).
 *   V6 429 DISINDAKI KOLLARIN HAKKI DEGISMEDI: zaman asimi hala DENEME kez denenir
 *      (fren, baska bir arizanin suresini uzatmaya ALET EDILMEZ).
 *   V7 YAKINSAMA (olculen kusurun nobetcisi): donusumlu 429/200 akisinda aralik TAVANA
 *      cikar ve basarilar onu GERI INDIRMEZ. Ilk surum burada SALINIYORDU -> canli
 *      kosum 141/1334 sorguda durmustu.
 *   ⚠️ FRENIN KADEMELERI (taban/tavan) `BEKLEME_MS`TEN TURER ve o knob FIKSTUR_ENV'dedir.
 *      Bu baginin nobetcisi BURASI DEGIL, tools/parite-fikstur-test.js S14'tur ("GECICI
 *      429", `PARITE_BEKLEME_MS=5`): kademeler sabit yazilirsa o cocuk kosum 60 sn'lik
 *      sure sinirini asar ve S14'un 4 iddiasi duser (21 Eyl'de tam olarak bu olculdu).
 *   V8 BUTCE DUVAR SAATIDIR (ikinci olculen kusurun nobetcisi): butce, ESZAMANLI
 *      iscilerin beklemelerini TOPLAMAZ. Ara surum topluyordu; 8 isciyle butce gercek
 *      zamandan ~8 kat hizli tukendi (cikti "frende harcanan 1509 sn" derken kosum
 *      288,2 sn surmustu) ve kosum 539/1334 sorguda durdu.
 */
const ortak = require("./parite-ortak.js");

let kalan = 0;
function ona(kosul, ad, ek) {
  console.log("  %s %s%s", kosul ? "✅" : "❌", ad, ek ? " — " + ek : "");
  if (!kosul) kalan++;
}

const GERCEK_FETCH = global.fetch;
/** Sirayla verilen durum kodlarini donduren sahte uc. Her cagri anini kaydeder. */
function sahteUc(durumlar) {
  const anlar = [];
  let i = 0;
  global.fetch = async () => {
    anlar.push(Date.now());
    const d = durumlar[Math.min(i++, durumlar.length - 1)];
    if (d === "ZAMAN_ASIMI") { const e = new Error("abort"); e.name = "TimeoutError"; throw e; }
    return {
      status: d,
      async text() { return ""; },
      async json() { return { toplam: 0, urunler: [] }; },
    };
  };
  return { anlar, sayi: () => i };
}

(async () => {
  const D = ortak.hizFreniDurumu();
  console.log("ADAPTIF HIZ FRENI — taban %d ms · tavan %d ms · 429 hakki %d · butce %d sn",
    D.tabanMs, D.tavanMs, D.deneme429, Math.round(D.butceMs / 1000));

  // ── V1: 429 YOKSA fren KAPALI, ek bekleme YOK ─────────────────────────────────────
  console.log("\nV1) 429 gorulmeyen kosum: fren aralik 0, ek bekleme 0");
  ortak.hizFreniSifirla();
  {
    const u = sahteUc([200]);
    const sayac = ortak.sayacYeni();
    const t0 = Date.now();
    for (let k = 0; k < 25; k++) await ortak.canliGetir("http://x/" + k, sayac, ortak.DENEME);
    const sure = Date.now() - t0;
    const d = ortak.hizFreniDurumu();
    ona(d.araMs === 0, "fren araligi 0 kaldi", "aralik=" + d.araMs + " ms");
    ona(d.frenSuresiMs === 0, "fren HIC devreye girmedi", "frenSuresi=" + d.frenSuresiMs + " ms");
    ona(sure < 250, "25 istek ek beklemesiz tamamlandi", sure + " ms");
    ona(sayac.istek === 25 && sayac.r429 === 0 && sayac.yenidenDeneme === 0,
      "sayaclar bozulmadi", JSON.stringify(sayac));
    ona(u.sayi() === 25, "tam 25 fetch atildi", "fetch=" + u.sayi());
  }

  // ── V2: TEK 429 -> fren TABAN'a ciker, istek basariyla doner ──────────────────────
  console.log("\nV2) tek 429: fren TABAN'a cikar, istek BASARIYLA doner");
  ortak.hizFreniSifirla();
  {
    sahteUc([429, 200]);
    const sayac = ortak.sayacYeni();
    const c = await ortak.canliGetir("http://x/v2", sayac, ortak.DENEME);
    const d = ortak.hizFreniDurumu();
    ona(c && c.durum === 200, "200 alindi");
    ona(d.araMs === D.tabanMs, "aralik TABAN'a cikti", "aralik=" + d.araMs + " ms");
    ona(sayac.r429 === 1 && sayac.yenidenDeneme === 1, "sayaclar dogru", JSON.stringify(sayac));
  }

  // ── V3: 4 ardisik 429 -> ESKI 3 HAK ile KIRMIZI olurdu; yeni hak YAKALAR ──────────
  console.log("\nV3) 4 ardisik 429 sonrasi 200 (eski 3 hakla OLCULEMEDI olurdu)");
  ortak.hizFreniSifirla();
  {
    sahteUc([429, 429, 429, 429, 200]);
    const sayac = ortak.sayacYeni();
    let c = null, hata = null;
    try { c = await ortak.canliGetir("http://x/v3", sayac, ortak.DENEME); } catch (e) { hata = e; }
    ona(!hata, "hata ATILMADI", hata && hata.message);
    ona(c && c.durum === 200, "200 alindi (5. denemede)");
    ona(sayac.r429 === 4, "4 kez 429 sayildi", "r429=" + sayac.r429);
    ona(ortak.DENEME < 5, "eski hak (DENEME=" + ortak.DENEME + ") bu vakaya YETMEZDI");
  }

  // ── V4: BUTCE bitince 429 ESKISI GIBI OlcumHatasi -> fail-closed ──────────────────
  console.log("\nV4) 429 hakki tukendiginde -> OlcumHatasi('429') (fail-closed, cikis 3)");
  ortak.hizFreniSifirla();
  {
    sahteUc([429]);
    const sayac = ortak.sayacYeni();
    let hata = null;
    try { await ortak.canliGetir("http://x/v4", sayac, ortak.DENEME); } catch (e) { hata = e; }
    ona(!!hata && hata.olcum === true, "OlcumHatasi atildi", hata && hata.tur);
    ona(!!hata && hata.tur === "429", "tur 429");
    ona(sayac.r429 === ortak.DENEME_429, "429 hakki TAM kullanildi",
      "r429=" + sayac.r429 + " hak=" + ortak.DENEME_429);
    const not = ortak.olcumNotu(hata, "test");
    ona(not.indexOf("HIZ SINIRI") !== -1 && not.indexOf("429") !== -1,
      "olcumNotu 'HIZ SINIRI'/'429' imzasini KORUYOR (tuketici eslemesi)", not.slice(0, 60));
  }

  // ── V5: eszamanli isciler TEK kuresel araliktan gecer ─────────────────────────────
  console.log("\nV5) fren aciktayken 4 eszamanli istek TEK araliktan gecer");
  ortak.hizFreniSifirla();
  {
    const u = sahteUc([429, 200]);          // ilk istek freni acar, sonrakiler 200
    const sayac = ortak.sayacYeni();
    await ortak.canliGetir("http://x/v5-0", sayac, ortak.DENEME);   // freni ac
    const t0 = Date.now();
    u.anlar.length = 0;
    await Promise.all([0, 1, 2, 3].map((k) =>
      ortak.canliGetir("http://x/v5-" + k, sayac, ortak.DENEME)));
    const sure = Date.now() - t0;
    const d = ortak.hizFreniDurumu();
    const enAz = 3 * d.araMs;               // 4 istek -> aralarinda 3 aralik
    ona(sure >= enAz - 40, "4 eszamanli istek en az " + enAz + " ms surdu", sure + " ms");
    ona(sure < enAz + 400, "aralik KATLANMADI (isciler ust uste binmedi)", sure + " ms");
  }

  // ── V6: 429 DISINDAKI kol eski hakkinda kaldi ────────────────────────────────────
  console.log("\nV6) zaman asimi kolu: hak hala DENEME (" + ortak.DENEME + ")");
  ortak.hizFreniSifirla();
  {
    const u = sahteUc(["ZAMAN_ASIMI"]);
    const sayac = ortak.sayacYeni();
    let hata = null;
    try { await ortak.canliGetir("http://x/v6", sayac, ortak.DENEME); } catch (e) { hata = e; }
    ona(!!hata && hata.tur === "ZAMAN_ASIMI", "ZAMAN_ASIMI atildi", hata && hata.tur);
    ona(u.sayi() === ortak.DENEME, "tam DENEME kez denendi (429 hakki SIZMADI)",
      "fetch=" + u.sayi() + " DENEME=" + ortak.DENEME);
    ona(ortak.hizFreniDurumu().araMs === 0, "fren zaman asiminda DEVREYE GIRMEDI");
  }

  // ── V7: YAKINSAMA — olculen KUSURUN regresyon nobetcisi ──────────────────────────
  // 🔴 21 Eyl 2026: frenin ILK surumu "N ardisik basaridan sonra gevse" diyordu ve
  // TABAN'da SALINIYORDU (429 -> 200 ms, basari serisi -> 0, yine 429 -> 200...).
  // Tavana hic cikmadigi icin sunulan hiz sinirin ~2,5 kati kaldi: canli kosumda 651
  // istegin 131'i 429 oldu, kosum 141/1334 sorguda DURDU. Bu eksen tam o hali olcer:
  // 429/200 DONUSUMLU akista aralik TAVANA cikmali ve basarilar onu GERI INDIRMEMELI.
  console.log("\nV7) donusumlu 429/200 akisi: fren TAVANA yakinsar, basari GERI INDIRMEZ");
  ortak.hizFreniSifirla();
  {
    // Her cagri sirayla 429/200 doner -> her istek 1 kez 429 yiyip sonra gecer.
    const durumlar = [];
    for (let k = 0; k < 40; k++) { durumlar.push(429); durumlar.push(200); }
    sahteUc(durumlar);
    const sayac = ortak.sayacYeni();
    const araliklar = [];
    for (let k = 0; k < 12; k++) {
      await ortak.canliGetir("http://x/v7-" + k, sayac, ortak.DENEME);
      araliklar.push(ortak.hizFreniDurumu().araMs);
    }
    const son = ortak.hizFreniDurumu().araMs;
    ona(son === D.tavanMs, "aralik TAVANA ulasti", "aralik=" + son + " ms (tavan " + D.tavanMs + ")");
    const geriDusen = araliklar.some((a, i) => i > 0 && a < araliklar[i - 1]);
    ona(!geriDusen, "hicbir adimda GERI DUSMEDI (fren TEK YONLU)", araliklar.join(" -> "));
    ona(araliklar.indexOf(D.tavanMs) <= 3,
      "en gec 3. istekte tavana cikti (yakinsama HIZLI)", araliklar.join(" -> "));
  }

  // ── V8: BUTCE DUVAR SAATI — ikinci olculen kusurun regresyon nobetcisi ───────────
  // 🔴 21 Eyl 2026 (2. kusur): butce "beklemelerin TOPLAMI" idi ve her ISCI icin ayri
  // sayiliyordu. 8 eszamanli isciyle toplam, gercek zamandan ~8 KAT hizli buyudu:
  // cikti "frende harcanan 1509 sn / butce 1500 sn" derken kosum 288,2 SANIYE surmustu.
  // Butce tukenince 429 yeniden denemesi kapandi ve kosum 539/1334 sorguda DURDU.
  // Bu eksen olcer: fren suresi EN COK gecen duvar saati kadar olabilir.
  console.log("\nV8) butce DUVAR SAATI: eszamanli iscilerin beklemeleri TOPLANMAZ");
  ortak.hizFreniSifirla();
  {
    const durumlar = [429].concat(Array.from({ length: 60 }, () => 200));
    sahteUc(durumlar);
    const sayac = ortak.sayacYeni();
    await ortak.canliGetir("http://x/v8-ac", sayac, ortak.DENEME);   // freni ac
    const t0 = Date.now();
    const ESZ = 8;
    await Promise.all(Array.from({ length: ESZ }, (_, k) =>
      ortak.canliGetir("http://x/v8-" + k, sayac, ortak.DENEME)));
    const duvar = Date.now() - t0;
    const fren = ortak.hizFreniDurumu().frenSuresiMs;
    // Fren suresi frenin ACILDIGI andan beri sayar, yani bu blogun duvar saatinden
    // biraz BUYUK olabilir; ama ESZ katina ASLA cikmamalidir.
    ona(fren < duvar * 2 + 500, "fren suresi DUVAR SAATIYLE ayni mertebede",
      "fren=" + fren + " ms · duvar=" + duvar + " ms");
    const toplamVarsayim = duvar * ESZ;
    ona(fren < toplamVarsayim / 2,
      "fren suresi eszamanli beklemelerin TOPLAMI DEGIL (eski kusur)",
      "fren=" + fren + " ms · toplam-varsayimi≈" + toplamVarsayim + " ms");
  }

  global.fetch = GERCEK_FETCH;
  ortak.hizFreniSifirla();
  console.log("\n%s", kalan ? "KIRMIZI: " + kalan + " iddia dustu" : "GECTI: 8 eksen, tum iddialar");
  process.exit(kalan ? 1 : 0);
})();
