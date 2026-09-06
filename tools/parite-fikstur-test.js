#!/usr/bin/env node
"use strict";
/**
 * PARITE KARAR-CEKIRDEGI KABUL FIKSTURU — AGSIZ, deterministik, canliya SIFIR istek.
 *
 *   node tools/parite-fikstur-test.js          # tum senaryolar
 *   node tools/parite-fikstur-test.js 3        # yalniz 3. senaryo (hizli teshis)
 *
 * NE OLCER: parite-test.js / parite-ege.js'in
 *   (a) "gurultu (katalog farki)" ile "gercek kirilma"yi ayirt edip etmedigini,
 *   (b) YONETICI ILKEYE uyup uymadigini: 1 (KIRMIZI) > 3 (OLCULEMEDI) > 0 (YESIL).
 *       Bulunmus TEK bir aciklanamayan ayrisim varsa, sonradan WAF/429/zaman asimi/tavan
 *       gelse bile sonuc 1 OLMALIDIR; hicbir ariza yolu 0 URETEMEZ.
 *
 * NASIL: yerel HTTP sunucusu sahte bir "D1 /ara + /katalog" ucu kurar ve uzerine ARIZA
 * ENJEKTE eder (403 duvari, 429 hiz siniri, susan uc, /katalog?ids= hatasi, sayim hatasi,
 * /ara'dan urun gizleme). Sahte ucun arama mantigi ELLE KOPYA DEGIL — parite-test.js'in
 * referans fonksiyonlari (site) ve bot'un gercek urunAra'si (Ege) ice aktarilir.
 *
 * ⚠️ FIKSTUR MODU: bu harness PARITE_URUNLER + ARA_UC (ve bazi senaryolarda esik env'leri)
 * verir. Mimar karari (27 Tem): test-only env verilmis bir kosum pariteyi ASLA
 * BELGELENDIREMEZ -> cikis en iyi ihtimalle 3'tur, 0 OLAMAZ. Bu yuzden "yesil" senaryolarin
 * beklentisi `cikis 3 + ACIKLANAMAYAN 0 + ACIKLANAN 0 + 'FIKSTUR: BIREBIR ESLESTI'`dir.
 * (Eskiden S0 cikis 0 bekliyordu; o beklenti PARITE_URUNLER baypasinin ta kendisiydi — A15.)
 *
 * VERI CAPASI YOK: katalog sentetiktir, sayilar kosum aninda uretilir; hicbir gercek urun
 * id'si / sabit katalog sayisi / SHA / tarih YOKTUR.
 */

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const TOOLS = __dirname;
const REF = require("./parite-test.js");          // norm/haystack/filtered — GERCEK referans
const EGE_MOD = require("./parite-ege.js");       // egeKodu() — GERCEK bot kodu
const SINIF = require("./parite-marka-sinifi.js"); // `marka=` yuklemi (index.html govdesi)
const PARITE_SITE = path.join(TOOLS, "parite-test.js");
const PARITE_EGE = path.join(TOOLS, "parite-ege.js");

const TUMU = "Tümü";
const IDS_TAVANI = 100;   // gercek /katalog ucunun kendi tavani
const SORGU = "220";      // her cocuk kosumda sorgu sayisi (hiz; havuz deterministik kirpilir)

// ── Sentetik katalog ─────────────────────────────────────────────────────────
const MARKALAR = ["Audi", "Volvo", "Bmw"];
const KATEGORILER = ["Otomobil", "Marin", "Tamirat", "Ev"];
const PARCALAR = ["menteşe", "conta", "braket", "pervane", "kapak", "klips"];
const SIFATLAR = ["ön", "arka", "sağ", "sol", "üst"];

// ⚠️ KATALOG BOYU: sorgu ureticileri (her iki testte) `kelimeler[i % 90]` gibi indeksler
// kullanir; sozluk 90 AYRI kelimeden kucukse undefined sorgu uretir ve test COKER. Bu
// yuzden her urune BENZERSIZ bir model kelimesi verilip katalog >= 140 tutulur.
function urunUret(n, onek) {
  const liste = [];
  for (let i = 0; i < n; i++) {
    const marka = MARKALAR[i % MARKALAR.length];
    const parca = PARCALAR[i % PARCALAR.length];
    const sifat = SIFATLAR[i % SIFATLAR.length];
    const model = onek + "model" + i;   // BENZERSIZ kelime -> sozluk yeterince genis
    liste.push({
      id: onek + "-" + i + "-" + parca,
      kategori: KATEGORILER[i % KATEGORILER.length],
      marka: [marka],
      baslik: marka + " " + model + " " + sifat + " " + parca + " tutucu",
      aciklama: "Özel üretim " + parca + " parçası " + model + ". Yaklaşık dış ölçüler: " +
        (20 + i) + " × " + (30 + i) + " × " + (10 + i) + " mm.",
      fiyat: (100 + i) + " TL",
      gorseller: [],
    });
  }
  return liste;
}

/**
 * MARKA CAPA KATALOGU — serbest metin ile `marka_arama` UYELIGININ AYRISTIGI urunler.
 * 🔴 VERI CAPASI YOK: hicbir gercek urun id'si / sayisi yok; ayrisma URUN SEKLINDEN dogar:
 *   · alias yazimi  : marka[] "Opel" -> uyelik {Opel, Vauxhall} (ham katalogda "Vauxhall"
 *                     GECMEDEN de `?q=Vauxhall` Opel'in TAMAMINI dondurmeli)
 *   · baslik jetonu : marka[] "Volvo" ama BASLIK "Opel ..." -> uyelik Opel'i de tasir
 *                     (ham marka[] esitligi bunu KACIRIR)
 *   · serbest metin tuzagi: "Havalandirma" urunu `?q=haval` SERBEST METINDE eslesir,
 *                     marka dalinda ESLESMEZ (uc bu yuzden gecti; olculen kusur buydu)
 * Filler urunler sozlugu 90 ayri kelimenin uzerinde tutar (sorgu ureteci sarti).
 */
function markaKatalogUret() {
  const capa = [
    { marka: ["Opel"], baslik: "Opel kapı kolu klipsi" },
    { marka: ["Opel"], baslik: "Opel far braketi" },
    // Alias yazimi BASLIKTA, ham `marka[]`de HIC YOK: `?q=Vauxhall` sorgu havuzuna
    // baslik kelimesi olarak girer, ama "ham marka evrenine suz" mutanti onu DUSURUR.
    { marka: ["Opel"], baslik: "Vauxhall pervane kapağı" },
    { marka: ["Volvo"], baslik: "Opel menteşe tutucu" },
    { marka: [], baslik: "Audi kapı stoperi" },
    { marka: ["Audi"], baslik: "Audi conta seti" },
    { marka: ["Haval"], baslik: "Haval jant göbeği" },
    { marka: [], baslik: "Havalandırma ızgarası kapağı" },
    { marka: [], baslik: "Havalandırma kanalı klipsi" },
  ];
  const liste = capa.map((c, i) => ({
    id: "capa-" + i + "-" + i,
    kategori: "Otomobil",
    marka: c.marka,
    baslik: c.baslik,
    aciklama: "Özel üretim parça capa" + i + ". Yaklaşık dış ölçüler: 20 × 30 × 10 mm.",
    fiyat: (100 + i) + " TL",
    gorseller: [],
  }));
  return liste.concat(urunUret(140, "mfx"));
}

/**
 * KLON — kurbanin ARANABILIR metnini AYNEN tasiyan, id'si kurbanin id'sini ONEK olarak
 * iceren yeni "D1'e sonradan giren" urun. Site tarafinda haystack(klon) =
 * haystack(kurban) + " klonN", Ege tarafinda vocab UST KUMESI -> klon, kurbanin eslestigi
 * HER sorguda eslesir. Boylece "kaybedilen 1 yerel, kazanilan 1 yeniyle TELAFI EDILIYOR"
 * hali birebir uretilir: sayi kapisi susar, kurban kuyrukta oldugu icin onek kapisi da
 * susar (8. yutma senaryosu).
 */
function klonla(kurban, n) {
  const out = [];
  for (let i = 0; i < n; i++) out.push(Object.assign({}, kurban, { id: kurban.id + "-klon" + i }));
  return out;
}

// ── MARKA EKSENI: sahte ucun MARKA DALI + BAGIMSIZ GERCEK ────────────────────
/**
 * 🔴 NEDEN BURADA IKINCI BIR URETEC CAGRISI VAR (bilerek, kopya DEGIL — BAGIMSIZLIK):
 * Fikstur, tools/ege-marka-referansi.js'e mutasyon uygulanmis KOPYADAN kosar (mutasyon
 * harness'i dosyalari gecici dizine kopyalar). Sahte ucun "gercek"i o modulden alinsaydi
 * mutant HER IKI tarafi birden bozar ve SESSIZCE HAYATTA KALIRDI
 * ([[beyan-edilmis-survivor]]: katman ancak TEK BASINA kirmizi yakilabiliyorsa kanittir).
 * Bu yuzden ucun tarafi ureticiyi KENDI cagirir; yuklem yine YAZILMAZ, KOSTURULUR.
 */
const MARKA_GERCEK_PY = [
  "import importlib.util, json, os, sys",
  "kok, katalog = sys.argv[1], sys.argv[2]",
  "sys.path.insert(0, os.path.join(kok, 'tools'))",
  "spec = importlib.util.spec_from_file_location('d1sync', os.path.join(kok, 'tools', 'd1-sync.py'))",
  "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)",
  "harita, sebep = mod.marka_arama_haritasi(json.load(open(katalog, encoding='utf-8')))",
  "print(json.dumps({'sebep': sebep, 'harita': {k: json.loads(v) for k, v in harita.items()}}))",
].join("\n");

/**
 * Sahte ucun marka dali icin GERCEK: {kanon(q), uyeMi(id, deger)}.
 * kanon = ucun KENDI yargisi (bot markaSorguKanonu'su, sahte D1 uzerinde) — burada da
 * elle bir "marka mi" kurali yazilmaz. Kurulamazsa senaryo KURULAMAZ (fail-closed):
 * sessizce serbest metne dusseydi marka ekseni HIC olculmeden yesil gorunurdu.
 */
function markaGercegiKur(EGE, urunler) {
  const kok = process.env.PARITE_INDEX_KOK || path.dirname(TOOLS);
  const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "parite-marka-gercek-"));
  const katalog = path.join(gecici, "urunler.json");
  fs.writeFileSync(katalog, JSON.stringify(urunler));
  let j;
  try {
    const p = require("child_process").spawnSync("python3",
      ["-c", MARKA_GERCEK_PY, kok, katalog],
      { encoding: "utf8", timeout: 600000, maxBuffer: 256 * 1024 * 1024 });
    if (p.status !== 0) {
      throw new Error("uretec rc=" + p.status + ": " + ((p.stderr || "") + (p.stdout || "")).slice(-300));
    }
    j = JSON.parse(p.stdout);
  } finally {
    fs.rmSync(gecici, { recursive: true, force: true });
  }
  if (j.sebep) throw new Error("uretec FAIL-CLOSED atladi: " + j.sebep);

  const uyelik = new Map();          // id -> Set(marka)
  const evren = new Set();
  for (const id of Object.keys(j.harita)) {
    uyelik.set(id, new Set(j.harita[id]));
    for (const m of j.harita[id]) evren.add(m);
  }
  if (!evren.size) throw new Error("marka evreni BOS — senaryo marka ekseni OLCEMEZ");
  const satirlar = [...evren].sort().map((m) => ({ m }));
  const env = { KATALOG: { prepare: () => ({ all: async () => ({ results: satirlar }) }) } };
  return {
    kanon: (q) => EGE.markaSorguKanonu(env, q),
    uyeMi: (id, deger) => (uyelik.get(id) || new Set()).has(deger),
    evrenBoyu: evren.size,
  };
}

// ── Sahte "D1" ucu + ARIZA ENJEKSIYONU ───────────────────────────────────────
/**
 * mod403        : her istek 403 (WAF duvari — on-kosuldan itibaren)
 * wafSonraAra   : ilk N /ara isteginden SONRA 403 (KOSUM ORTASINDA duvar)
 * r429SonraAra  : ilk N /ara isteginden SONRA daima 429 (deneme tukenir)
 * r429IlkKere   : ilk N istegi 429, sonra normal (GECICI 429 -> yeniden deneme tutmali)
 * susSonraAra   : ilk N /ara isteginden SONRA hic cevap verme (zaman asimi)
 * idsHata       : /katalog?ids= daima HTTP 500 (supurme KANITI uretilemez)
 * sayimHata     : /katalog?sayfa= daima HTTP 500 (on-kosul sayimi olculemez)
 * gizliAra      : Set<id> — /ara sonuclarindan (ve toplam'dan) DUSURULUR; /katalog'da DURUR
 *                 ("D1'in arama metni/indeksi farkli" = D1 EKSIK eslesme uretici)
 * sayiSapma     : /katalog toplam'ina eklenen sapma (bayat KV sayaci / yetim satir taklidi)
 * araToplamSapma: /ara'nin ILAN ETTIGI toplam'a eklenen sapma — donen SATIR sayisi degismez.
 *                 Boylece pencere, ucun ilan ettigi toplami KAPSAMAZ: pencere disi
 *                 OLCULMEMISTIR -> cikti kesin hukum BASMAMALIDIR (durustluk kapisi).
 */
/*
 * 🔴 SAHTE UC KENDI KATALOGUNU OLCER (6 Eyl 2026 — OLCULDU; S8 ve SM1'in ORTAK koku).
 * `parite-marka-sinifi.js` katalog yolunu MODUL YUKLENIRKEN cozuyordu; harness surecinde
 * `PARITE_URUNLER` olmadigi icin sentetik katalogun `marka_kanon` haritasi 20 bin urunluk
 * URETIM katalogundan turuyordu. Tek kok, iki ariza dogurdu:
 *   · SM1: sentetik katalogtan `capa-3-3 -> ["Volvo","Opel"]`, uretimden `capa-3-3 -> null`
 *     (29.298 kayit, sentetik id'lerin HICBIRI yok) -> `uyeMi` sahte ucta FALSE, cocukta
 *     TRUE -> `?q=Opel&marka=Opel` ucta 3 / yerelde 4 -> "gerileme" RAPOR EDILDI.
 *   · S8: `marka-kanon-uret.py` SENKRON kosar; uretim katalogunda ~22 sn. Bedel ILK
 *     ISTEGIN ISLEYICISINDE odeniyordu ve sunucu TEK IS PARCACIKLI oldugu icin ilk
 *     partideki 8 eszamanli istek onun arkasinda kuyruga giriyordu:
 *         288ms ISTEK /ara?q=&marka=Bmw  ->  21860ms YANIT   (sonrakiler ~1 ms)
 *     Zaman asimi esigi 22 sn'nin ALTINDA olan her senaryo (S8: 400 ms) TEK SORGU
 *     siniflandirilmadan olurdu: `ACIKLANAMAYAN: 0` + `0/220 sorgu` -> cikis 3. Bu yuzden
 *     `susSonraAra` esigini 25->120 yapmak da, zaman asimini 400->15.000 ms buyutmek de
 *     ISE YARAMADI: olculen sey ucun ENJEKTE EDILEN sessizligi degil, fiksturun KENDI
 *     soguk baslangicidir. Nobetci: tools/parite-fikstur-olcum-ortami-mutasyon.py
 */
function sunucuKur(secenek) {
  const { canli, EGE, mod403, wafSonraAra, r429SonraAra, r429IlkKere, susSonraAra,
    idsHata, sayimHata, gizliAra, sayiSapma, araToplamSapma, markaGercek } = secenek;
  // 🔴 SAHTE UC KENDI D1'INI MODELLER: `marka_kanon` haritasi SENARYONUN `canli`
  // katalogundan turemeli. Harness surecinde `PARITE_URUNLER` yoktu -> harita URETIM
  // katalogundan cozuluyor, sentetik id'lerin hicbiri orada olmadigi icin `uyeMi`nin
  // `marka_kanon` kolu SESSIZCE hep FALSE donuyordu (SM1: uc 3 / yerel 4). Cocuga
  // gecen `PARITE_URUNLER` AYRICA ve ACIKCA veriliyor (kostur), bu satir onu ETKILEMEZ.
  const kanonGecici = fs.mkdtempSync(path.join(os.tmpdir(), "parite-fikstur-kanon-"));
  const kanonKatalog = path.join(kanonGecici, "urunler.json");
  fs.writeFileSync(kanonKatalog, JSON.stringify(canli));
  const oncekiUrunlerEnv = process.env.PARITE_URUNLER;
  process.env.PARITE_URUNLER = kanonKatalog;
  const envGeriAl = () => {
    if (oncekiUrunlerEnv === undefined) { delete process.env.PARITE_URUNLER; }
    else { process.env.PARITE_URUNLER = oncekiUrunlerEnv; }
    fs.rmSync(kanonGecici, { recursive: true, force: true });
  };
  // 🔴 AYRICA BIR "ISITMA" CAGRISI YOK — OLCULDU, TASIMIYOR. Once eklenmisti (soguk
  // baslangici istek yolunun disina almak icin); yukaridaki yol duzeltmesinden SONRA
  // geri alinip olculdu: isitmasiz S8 **7 iddia / 0 KALDI, 1,1 sn**. Sebep: bedel
  // katalogun BUYUKLUGUNDEN geliyordu (uretim katalogu ~22 sn), sentetik senaryo
  // katalogunda ~0. Tasimayan kod kapsam yanilsamasidir; bu yuzden BIRAKILMADI.
  const idx = EGE ? EGE.katalogIndeksle(canli) : null;
  const canliIdHarita = new Map(canli.map((p) => [p.id, p]));
  const gizli = gizliAra || new Set();
  let araSayaci = 0;
  let toplamSayac = 0;
  const asiliYanitlar = [];
  // 🔴 UC DAGILIMI (6 Eyl 2026): "kosum ERKEN DURDU: 0/220 sorgu" + "canli istek: 9" ikilisi
  // TEK BASINA teshis etmez — 9 istegin HANGI UCA gittigi bilinmeden esik/zaman asimi
  // ayarlamak korlemesine atistir (S8'de tam bu yasandi: esik 25->120 ve zaman asimi
  // 400->15.000 ms denendi, sayi DEGISMEDI cunku istekler /ara'ya HIC gelmiyordu).
  // Sayac ucu ADIYLA ayirir ve senaryo basliginda SAYIYLA basilir.
  const ucSayaci = new Map();
  const ucSay = (ad) => ucSayaci.set(ad, (ucSayaci.get(ad) || 0) + 1);

  const sunucu = http.createServer((req, res) => {
    const u = new URL(req.url, "http://127.0.0.1");
    const gonder = (obj, durum) => {
      const g = JSON.stringify(obj);
      res.writeHead(durum || 200, { "content-type": "application/json; charset=utf-8" });
      res.end(g);
    };
    const duvar = (kod) => {
      // Cloudflare taklidi: JSON bile degil, duz metin (gercek duvarin davranisi).
      res.writeHead(kod, { "content-type": "text/html" });
      res.end("<html>error code: " + (kod === 429 ? "1015" : "1010") + "</html>");
    };
    toplamSayac++;
    // Uc adi: yolun KENDISI + ayirt edici parametre (ids/sayfa/mod) — sorgu metni DEGIL.
    if (u.pathname === "/katalog") ucSay((u.searchParams.get("ids") || "") ? "/katalog?ids=" : "/katalog?sayfa=");
    else if (u.pathname === "/ara") ucSay("/ara" + ((u.searchParams.get("mod") || "") ? "?mod=" + u.searchParams.get("mod") : ""));
    else ucSay(u.pathname + " (BILINMEYEN)");
    if (mod403) return duvar(403);
    if (r429IlkKere && toplamSayac <= r429IlkKere) return duvar(429);

    let limit = parseInt(u.searchParams.get("limit") || "", 10);
    if (!Number.isFinite(limit) || limit < 1) limit = 20;

    if (u.pathname === "/katalog") {
      const ham = (u.searchParams.get("ids") || "").split(",").map((s) => s.trim()).filter(Boolean);
      if (ham.length) {
        if (idsHata) return gonder({ hata: "ids ucu coktu (fikstur)" }, 500);
        const idler = ham.slice(0, IDS_TAVANI);
        const bulunan = idler.map((i) => canliIdHarita.get(i)).filter(Boolean);
        return gonder({ toplam: bulunan.length, urunler: bulunan.map((p) => ({ id: p.id })) });
      }
      if (sayimHata) return gonder({ hata: "sayim ucu coktu (fikstur)" }, 500);
      return gonder({ toplam: canli.length + (sayiSapma || 0), sayfa: 1, urunler: [] });
    }

    if (u.pathname === "/ara") {
      araSayaci++;
      if (wafSonraAra && araSayaci > wafSonraAra) return duvar(403);
      if (r429SonraAra && araSayaci > r429SonraAra) return duvar(429);
      if (susSonraAra && araSayaci > susSonraAra) { asiliYanitlar.push(res); return; }

      const q = u.searchParams.get("q") || "";
      const mod = u.searchParams.get("mod") || "";
      const suz = (liste) => (gizli.size ? liste.filter((p) => !gizli.has(p.id)) : liste);
      const sap = (n) => n + (araToplamSapma || 0);
      if (mod === "ege") {
        if (!q.trim()) return gonder({ hata: "q gerekli", toplam: 0, urunler: [] }, 400);
        // `marka=` FILTRE EKSENI (10 Agu): /ara?mod=ege bu parametreyi TASIR (egeMarkaSarti,
        // /katalog marka dalinin ikizi). Sahte uc onu YOK SAYSAYDI, korpusa yeni giren
        // marka ekseni fiksturde SAHTE KIRMIZI yakardi ve harness'in kendi hukmu
        // gurultuye gomulurdu ([[kardes-fikstur-yeni-kanca-adiminda-kirilir]]).
        // Yuklem index.html'in KENDI `markaUyeMi`si — ikinci kopya YOK.
        const markaF = u.searchParams.get("marka") || "";
        const markaSuz = (liste) => (markaF
          ? liste.filter((p) => SINIF.markaSinifi(canli).uyeMi(p, markaF)) : liste);
        const serbest = () => {
          const hepsi = markaSuz(suz(EGE.urunAra(idx, q, Infinity)));
          return gonder({ toplam: sap(hepsi.length),
            urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
        };
        // MARKA DALI — canli ucla AYNI sira: marka adi sorgusu serbest metinden ONCE.
        // Sonuc `marka_arama` uyeligi, sira KATALOG sirasi (uc: skor SABIT + seq DESC).
        if (!markaGercek) return serbest();
        return markaGercek.kanon(q).then((deger) => {
          if (!deger) return serbest();
          const hepsi = markaSuz(suz(canli.filter((p) => markaGercek.uyeMi(p.id, deger))));
          return gonder({ toplam: sap(hepsi.length),
            urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
        }).catch((e) => gonder({ hata: "marka dali: " + String(e) }, 500));
      }
      const kat = u.searchParams.get("kategori") || "";
      const marka = u.searchParams.get("marka") || "";
      if (!q.trim() && !kat && !marka) {
        return gonder({ hata: "q, kategori veya marka gerekli", toplam: 0, urunler: [] }, 400);
      }
      const hepsi = suz(REF.filtered(canli, q, kat || TUMU, marka || TUMU));
      return gonder({ toplam: sap(hepsi.length), urunler: hepsi.slice(0, limit).map((p) => ({ id: p.id })) });
    }
    return gonder({ hata: "bilinmeyen yol" }, 404);
  });

  return new Promise((cozul) => {
    sunucu.listen(0, "127.0.0.1", () => cozul({
      sunucu,
      port: sunucu.address().port,
      /** Fiksturun GORDUGU istek dagilimi: "uc=sayi" ciftleri, cok isteklisi ONDE. */
      ucDagilimi() {
        return Array.from(ucSayaci.entries())
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
          .map(([ad, n]) => ad + "=" + n).join(" ") || "(istek YOK)";
      },
      kapat() {
        for (const r of asiliYanitlar) { try { r.destroy(); } catch (e) { /* yok */ } }
        if (typeof sunucu.closeAllConnections === "function") sunucu.closeAllConnections();
        sunucu.close();
        envGeriAl();
      },
    }));
  });
}

// ── Cocuk kosum ──────────────────────────────────────────────────────────────
// 🔴 SURE SINIRI (27 Tem, curutucu notu): olculen kosum suresi 29 senaryo icin ~6,5 sn
// (senaryo basi ~0,25 sn). Ama uc SUSTURULAN senaryolarda (susSonraAra) kosum yalnizca
// parite-ortak.js'in AbortSignal.timeout'u sayesinde bitiyor. O savunma bozulursa (M14
// mutanti) cocuk surec SONSUZA KADAR bekler ve harness'i ASAR -> CI'da timeout'suz bir
// job ASILIR: "asilan kapi OLU kapidir" ilkesine aykiri, ustelik mutant TEMIZ KIRMIZI
// yerine ASILMA ile "yakalanmis" sayilirdi. Sinir 240x pay birakir; asilirsa cocuk
// OLDURULUR ve senaryo GORUNUR sekilde kirmizi yanar (kod 124).
const COCUK_SURE_SINIRI_MS = (() => {
  const n = parseInt(process.env.PARITE_FIKSTUR_SURE_MS || "", 10);
  return Number.isFinite(n) && n >= 1000 ? n : 60000;
})();

function kostur(dosya, { araUc, urunlerYolu, argv, ekEnv }) {
  return new Promise((cozul) => {
    const c = spawn(process.execPath, [dosya].concat(argv || []), {
      env: Object.assign({}, process.env, { ARA_UC: araUc, PARITE_URUNLER: urunlerYolu },
        ekEnv || {}),
      cwd: path.dirname(TOOLS),
    });
    let cikti = "";
    let hataAkisi = "";
    let bitti = false;
    const zamanlayici = setTimeout(() => {
      if (bitti) return;
      const not = "\n🔴 SURE SINIRI ASILDI (" + COCUK_SURE_SINIRI_MS + " ms): cocuk surec " +
        "OLDURULDU. Kosum ASILDI -> ariza yolu zaman asimiyla KAPANMIYOR.\n";
      cikti += not;
      hataAkisi += not;
      try { c.kill("SIGKILL"); } catch (e) { /* yok */ }
    }, COCUK_SURE_SINIRI_MS);
    c.stdout.on("data", (d) => { cikti += d; });
    c.stderr.on("data", (d) => { cikti += d; hataAkisi += d; });
    c.on("close", (kod, sinyal) => {
      bitti = true;
      clearTimeout(zamanlayici);
      // SIGKILL ile oldurulduyse cikis kodu null gelir -> 124 (kabuk gelenegi: zaman asimi)
      cozul({ kod: kod === null ? 124 : kod, cikti, hataAkisi });
    });
  });
}

// ── Iddia toplayici ──────────────────────────────────────────────────────────
let gecen = 0, kalan = 0;
let aktifSenaryo = "";
const kalanSenaryolar = new Set();
function ONA(kosul, ad, ek) {
  if (kosul) { gecen++; console.log("   ✅ " + ad); return; }
  kalan++;
  kalanSenaryolar.add(aktifSenaryo);
  console.log("   ❌ " + ad + (ek ? "\n      " + String(ek).replace(/\n/g, "\n      ") : ""));
}
function sayiOku(cikti, etiket) {
  const m = new RegExp(etiket.replace(/[()]/g, "\\$&") + ":\\s*(\\d+)").exec(cikti);
  return m ? parseInt(m[1], 10) : null;
}
// ⚠️ Node coken bir surec de exit 1 doner -> "cikis 1 KIRMIZI" iddiasi COKME ile SAHTE
// yesil yanabilir (yasanan tuzak: S8 boyle gecmis gorunuyordu). Her senaryoda aranir.
function cokmusMu(cikti) {
  return /\bNode\.js v\d/.test(cikti) || /^\s*(TypeError|ReferenceError|SyntaxError):/m.test(cikti);
}
/** "Yesil karsiligi" (fikstur modunda): cikis 3 + hic ayrisim yok. */
function fiksturYesil(r) {
  return r.kod === 3 && sayiOku(r.cikti, "ACIKLANAMAYAN") === 0 &&
    sayiOku(r.cikti, "ACIKLANAN(senkron)") === 0 && /FIKSTUR: BIREBIR ESLESTI/.test(r.cikti);
}

// ── BIRIM OLCUMU: siniflandir() DOGRUDAN cagrilir (surec/ag YOK) ─────────────
// NEDEN AYRI: cocuk-surec senaryolari LIMIT=1000 ile kosar ve sentetik katalog 140
// urundur -> PENCERE HIC DOLMAZ. Oysa gercek kosumda pencere DOLUYOR (olculdu 27 Tem:
// site sorgu havuzundaki 1199 sorgunun 74'u LIMIT'e dayaniyor). Pencere DOLUYKEN
// yeni urunler yerel satirlari pencereden ITER — bu MESRU'dur. Uzunluk kapisi bu iki hali
// AYIRMAK ZORUNDA; "suzulmus.length < min(bekIds.length, limit)" gibi butceyi saymayan
// bir kapi burada MESRU gecikmeyi KIRMIZI yakardi (yanlis-pozitif).
const ORTAK = require("./parite-ortak.js");
function birimOlc() {
  aktifSenaryo = "BIRIM siniflandir() — pencere DOLU/DOLMAMIS + telafi";
  console.log("\n▶ " + aktifSenaryo);
  const L = (n, onek) => Array.from({ length: n }, (_, i) => (onek || "L") + i);
  const kume = (a) => new Set(a);
  const cagir = (o) => ORTAK.siniflandir(o);

  // B1 PENCERE DOLU + MESRU yer degistirme: 2 yeni urun 2 yereli pencereden itiyor.
  //    (butceyi saymayan bir kapi burayi KIRMIZI yakar -> yanlis-pozitif)
  const yerel12 = L(12);
  const b1 = cagir({
    bekIds: yerel12, alinan: ["N0", "N1"].concat(yerel12.slice(0, 8)), toplam: 14, limit: 10,
    yerelIdKume: kume(yerel12), gecikmeModu: true,
  });
  ONA(b1.sinif === ORTAK.SINIF_ACIKLANAN,
    "B1 pencere DOLU + mesru itilme -> ACIKLANAN (yanlis-pozitif YOK)", JSON.stringify(b1));
  ONA(b1.kesin === false, "B1 pencere toplami KAPSAMIYOR -> kesin=false (hukum verilemez)");

  // B2 PENCERE DOLU + KURBAN: 3 yeni gorunuyor ama butce yalniz 2 -> en az 1 yerel YOK.
  const b2 = cagir({
    bekIds: yerel12, alinan: ["N0", "N1", "N2"].concat(yerel12.slice(0, 7)), toplam: 14,
    limit: 10, yerelIdKume: kume(yerel12), gecikmeModu: true,
  });
  ONA(b2.sinif === ORTAK.SINIF_ACIKLANAMAYAN,
    "B2 pencere DOLU + butce ASILDI -> ACIKLANAMAYAN (kurban yakalandi)", JSON.stringify(b2));
  ONA(/en az 1 urun/.test(b2.sebep), "B2 kayip sayisi ALT SINIR olarak yazili");

  // B3 8. YUTMA'nin birimi: kurban KUYRUKTA + 1 telafi, pencere DOLMADI.
  const yerel10 = L(10);
  const b3 = cagir({
    bekIds: yerel10, alinan: ["N0"].concat(yerel10.slice(0, 9)), toplam: 10, limit: 1000,
    yerelIdKume: kume(yerel10), gecikmeModu: true,
  });
  ONA(b3.sinif === ORTAK.SINIF_ACIKLANAMAYAN,
    "B3 kurban KUYRUKTA + telafi -> ACIKLANAMAYAN (8. yutma kapali)", JSON.stringify(b3));
  ONA(b3.sebep.indexOf("L9") !== -1, "B3 KAYIP id ADIYLA yazili (L9)");
  ONA(b3.kesin === true, "B3 pencere toplami kapsiyor -> kesin=true");

  // B4 KONTROL: ayni desen, kurban YOK -> ACIKLANAN.
  const b4 = cagir({
    bekIds: yerel10, alinan: ["N0"].concat(yerel10), toplam: 11, limit: 1000,
    yerelIdKume: kume(yerel10), gecikmeModu: true,
  });
  ONA(b4.sinif === ORTAK.SINIF_ACIKLANAN, "B4 KONTROL: kurban YOK -> ACIKLANAN",
    JSON.stringify(b4));

  // B5 gecikme modu KAPALI: her ayrisim ACIKLANAMAYAN, kesin DAIMA true (eski katilik).
  const b5 = cagir({
    bekIds: yerel10, alinan: yerel10.slice(0, 9), toplam: 9, limit: 1000,
    yerelIdKume: kume(yerel10), gecikmeModu: false,
  });
  ONA(b5.sinif === ORTAK.SINIF_ACIKLANAMAYAN && b5.kesin === true,
    "B5 gecikme modu KAPALI -> ACIKLANAMAYAN + kesin=true");

  // B6 TAM PARITE (gecikme modunda bile) -> GECTI, kesin=true.
  const b6 = cagir({
    bekIds: yerel10, alinan: yerel10, toplam: 10, limit: 1000,
    yerelIdKume: kume(yerel10), gecikmeModu: true,
  });
  ONA(b6.sinif === ORTAK.SINIF_GECTI && b6.kesin === true, "B6 tam parite -> GECTI + kesin");

  // ── B7 BEYAN EDILEN KOR NOKTA (kapatilmadi — GIZLENMEDI de) ──────────────────────
  // Pencere DOLU + kurban VAR, ama pencereye giren yeni urun sayisi butcenin ALTINDA
  // (yeniler pencerenin disinda kalmis). Uzunluk kapisi burayi YAKALAMAZ: disaridan
  // olculebilen hicbir sayi "yerel satir pencereden mi dusdu yoksa D1'de mi yok"
  // sorusunu ayirmaz. TEK dogru davranis KESIN HUKUM BASMAMAK'tir -> kesin=false
  // uretilir ve nihai cikti "hicbir ayrisim tehlikeli yonde DEGIL" DEMEZ.
  // Bu iddia CIFT YONLU nobettir: (a) kor noktayi kayit altina alir, (b) birisi kapiyi
  // "her fazlaligi kirmizi say" diye gevsetirse (yanlis-pozitif) burasi KIRMIZI yanar.
  const yerel20 = L(20);
  const b7 = cagir({
    bekIds: yerel20, alinan: ["N0"].concat(yerel20.slice(0, 9)), toplam: 24, limit: 10,
    yerelIdKume: kume(yerel20), gecikmeModu: true,
  });
  ONA(b7.sinif === ORTAK.SINIF_ACIKLANAN,
    "B7 KOR NOKTA: pencere DOLU + yeniler pencere disinda -> kapi YAKALAMAZ (beyan edildi)",
    JSON.stringify(b7));
  ONA(b7.kesin === false,
    "B7 KOR NOKTA GIZLENMIYOR: kesin=false -> cikti KESIN HUKUM BASMAZ");
}

// ── Senaryo kosucu ───────────────────────────────────────────────────────────
async function senaryoKos(s) {
  // MARKA EKSENI senaryolari: sahte uc marka dalini da tasir (canli ucla AYNI sozlesme).
  // Kurulamazsa senaryo COKER — sessizce serbest metne dusmek ekseni olculmemis halde
  // yesil gosterirdi.
  if (s.markaEkseni) s.markaGercek = markaGercegiKur(s.EGE, s.canli);
  const sunucu = await sunucuKur(s);
  const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "parite-fikstur-"));
  const urunlerYolu = path.join(gecici, "urunler.json");
  fs.writeFileSync(urunlerYolu, JSON.stringify(s.yerel));
  aktifSenaryo = s.ad;
  try {
    const r = await kostur(s.dosya, {
      araUc: "http://127.0.0.1:" + sunucu.port + "/ara",
      urunlerYolu, argv: s.argv || [SORGU], ekEnv: s.ekEnv,
    });
    console.log("\n▶ " + s.ad + "  (yerel=" + s.yerel.length + " canli=" + s.canli.length +
      " -> cikis " + r.kod + ")");
    console.log("   UC DAGILIMI: " + sunucu.ucDagilimi());
    ONA(!cokmusMu(r.cikti), "surec COKMEDI (cikis kodu gercek hukum)",
      cokmusMu(r.cikti) ? r.cikti.slice(-700) : "");
    ONA(r.kod !== 124, "surec SURE SINIRINA TAKILMADI (asilan kapi olu kapidir)",
      r.kod === 124 ? r.cikti.slice(-700) : "");
    // A15 nobeti: fikstur modu uyarisi HER kosumda hem stdout hem STDERR'e dusmeli.
    ONA(/FIKSTUR MODU/.test(r.hataAkisi), "fikstur uyarisi STDERR'e de dustu (yutulamaz)");
    ONA(r.kod !== 0, "cikis 0 DEGIL (PARITE_URUNLER ile parite BELGELENEMEZ)");
    s.dogrula(r);
    return r;
  } finally {
    sunucu.kapat();
    fs.rmSync(gecici, { recursive: true, force: true });
  }
}

async function main() {
  const yalniz = parseInt(process.argv[2] || "", 10);
  const EGE = fs.existsSync(EGE_MOD.BOT) ? await EGE_MOD.egeKodu() : null;

  const TABAN = urunUret(140, "fx");
  const EK = urunUret(9, "yeni");
  const YETIM = urunUret(1, "yetim");                 // yerelde HIC olmayan tek D1 satiri
  // KIRMIZI URETICI: yerel katalogda VAR olan urunlerin yarisini D1'in ARAMASINDAN gizle
  // (/katalog'da DURURLAR) -> her ilgili sorgu "D1 EKSIK eslesme"/ayrisma verir.
  const GIZLI = new Set(TABAN.filter((p, i) => i % 2 === 0).map((p) => p.id));
  // 8. YUTMA URETICISI: kurban = katalogun SON urunu -> eslestigi HER sorguda yerel
  // listenin KUYRUGUNDA yer alir (site: dizi sirasi · Ege: skor esitliginde katalog sirasi).
  // /katalog'da DURUR (supurme "yerel ⊆ D1" kanitini uretir), yalniz /ara'dan gizlenir.
  const KURBAN = TABAN[TABAN.length - 1];
  const KURBAN_GIZLI = new Set([KURBAN.id]);
  // Zaman asimi senaryolari: kisa esik + tek deneme (yoksa fikstur dakikalarca surer).
  const HIZLI_ZA = { PARITE_ZAMAN_ASIMI_MS: "400", PARITE_DENEME: "1", PARITE_BEKLEME_MS: "1" };
  const HIZLI_429 = { PARITE_DENEME: "2", PARITE_BEKLEME_MS: "1" };

  const senaryolar = [];

  // 0) SAGLAMA — fikstur dogru mu? yerel == canli ise ayrisim SIFIR olmak ZORUNDA.
  senaryolar.push({
    ad: "S0 SAGLAMA: yerel == canli -> ayrisim 0 (fikstur'un kendi dogrulugu) + cikis 3",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(),
    dogrula: (r) => {
      ONA(fiksturYesil(r), "cikis 3 + ayrisim 0 + 'FIKSTUR: BIREBIR ESLESTI'", r.cikti.slice(-600));
      ONA(!/PARITE YOK/.test(r.cikti), "KIRMIZI yazmiyor");
      ONA(/siniflandirma KAPALI/.test(r.cikti), "sayilar esit -> siniflandirma KAPALI (eski katilik)");
    },
  });

  // 1) K4 — BAYAT CHECKOUT: canli ILERIDE (yeni urunler katalogun BASINDA).
  senaryolar.push({
    ad: "S1 (K4) BAYAT CHECKOUT: canli = yerel + yeni urunler -> cikis 3, KIRMIZI DEGIL",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN),
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-800));
      ONA(/SENKRON GEC/.test(r.cikti), "gorunur 'SENKRON GECİKMESİ' imzasi");
      ONA(!/PARITE YOK/.test(r.cikti), "KIRMIZI (PARITE YOK) YAZMIYOR");
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0");
      ONA(sayiOku(r.cikti, "ACIKLANAN(senkron)") > 0,
        "aciklanan > 0 (ayrisimlar SAYILDI, susturulmadi)");
      ONA(/D1 FAZLALIGI: yerel=\d+ < canli=\d+/.test(r.cikti), "kanit SAYIYLA yazili");
    },
  });

  // 2) K4-a — TEHLIKELI YON: yerelde VAR, D1'de YOK -> KIRMIZI.
  senaryolar.push({
    ad: "S2 (K4-a) YERELDE VAR / D1'DE YOK -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN,
    canli: EK.concat(TABAN.filter((p, i) => i !== 7)),
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YERELDE VAR \/ D1'DE YOK/.test(r.cikti), "sebep: yerelde var / D1'de yok");
      ONA(/Ege GOREMEZ/.test(r.cikti), "sonucun bedeli yazili (Ege goremez)");
      ONA(!/SENKRON GEC/.test(r.cikti), "katalog farkina YUVARLANMADI");
    },
  });

  // 3) K4-b — SIRA farki, gecikme modu ACIK iken + AYNI kosumda aciklanan gurultu.
  const sirasiBozuk = EK.concat(TABAN.slice());
  const a = EK.length + 1, b = EK.length + 4;
  const tut = sirasiBozuk[a]; sirasiBozuk[a] = sirasiBozuk[b]; sirasiBozuk[b] = tut;
  senaryolar.push({
    ad: "S3 (K4-b) SIRA farki + katalog gurultusu AYNI kosumda -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, canli: sirasiBozuk,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(/SIRA farki/.test(r.cikti), "sebep: SIRA farki (katalog farkiyla aciklanamaz)");
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "aciklanamayan > 0");
      ONA(sayiOku(r.cikti, "ACIKLANAN(senkron)") > 0, "ayni kosumda aciklanan > 0 — MASKELEMEDI");
      ONA(/MASKELEMEZ/.test(r.cikti), "cikti maskelenmedigini acikca yaziyor");
    },
  });

  // 4) Yetim satir kapisi: gorulen D1 fazlasi > sayi acigi -> aciklama coker -> KIRMIZI.
  senaryolar.push({
    ad: "S4 YETIM SATIR: gorulen D1 fazlasi > sayi acigi -> aciklama coker, cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), sayiSapma: -(EK.length - 1),
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
      ONA(/YETIM satir/.test(r.cikti) || /ACIKLAMAZ/.test(r.cikti),
        "sebep: sayi acigi fazlaligi ACIKLAMIYOR (yetim satir imzasi)");
    },
  });

  // 5) WAF/UA: 403 duvari "ayrisma" degil "olculemedi".
  senaryolar.push({
    ad: "S5 WAF/UA 403 (on-kosul) -> cikis 3 + 'ÖLÇÜLEMEDİ: WAF/UA', ayrisma SAYILMAZ",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), mod403: true,
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-600));
      ONA(/ÖLÇÜLEMEDİ: WAF\/UA/.test(r.cikti), "gorunur 'ÖLÇÜLEMEDİ: WAF/UA'");
      ONA(!/PARITE YOK/.test(r.cikti), "KIRMIZI yazmiyor");
      ONA(!/ACIKLANAMAYAN: [1-9]/.test(r.cikti), "ayrisma SAYILMADI");
      ONA(/0\/\d+ sorgu olculdu/.test(r.cikti), "kac sorgunun olculdugu GORUNUR");
    },
  });

  // ── 🔴 KOK SEBEP (B1 / A13 / A14): kosum ORTASINDA ariza, KIRMIZI BULUNMUSKEN ──────
  // Eski kod `if (wafHatasi) process.exit(wafYaz(...))` ile hatalar[]'a HIC BAKMADAN
  // cikiyordu -> 118 (B1) ve 11 (A13/A14) gercek kirmizi SILINIP 3 yaziliyordu.
  senaryolar.push({
    ad: "S6 (K2/KOK SEBEP) KIRMIZI + kosum ortasinda WAF 403 -> cikis 1 (ariza SILEMEZ)",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI, wafSonraAra: 25,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (3'e yuvarlanmadi)", r.cikti.slice(-900));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "bulunan kirmizilar SAYILDI");
      ONA(/OLCUM ARIZASI VAR/.test(r.cikti), "ariza da GORUNUR (yutulmadi)");
      ONA(/WAF\/UA/.test(r.cikti), "arizanin turu yazili (WAF/UA)");
      ONA(/KIRMIZI KAZANIR/.test(r.cikti), "oncelik kurali ciktiya yazili (1 > 3 > 0)");
    },
  });
  senaryolar.push({
    ad: "S7 (K2) KIRMIZI + kosum ortasinda 429 (deneme tukendi) -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI,
    // 🔴 ESIK 25 -> 120 (6 Eyl 2026, OLCULDU). Senaryonun ONCULU "once KIRMIZI BULUNUR,
    // SONRA ariza gelir"dir; hukum de bunun uzerine kuruludur (1 > 3). Esik 25'te ariza
    // supurme HICBIR SEYI SINIFLANDIRAMADAN vuruyordu -> `ACIKLANAMAYAN: 0`, `kosum ERKEN
    // DURDU: 0/220 sorgu olculdu` -> "1 > 3" kuralinin degerlendirecegi kirmizi HIC
    // DOGMUYORDU ve senaryo cikis 3 verip kirmizi yaniyordu. Yani olculen sey uretici
    // arizasi DEGIL, fikstur oncululunun kurulamamasiydi.
    // OLCUM: esik 250 (ariza hic vurmaz) -> cikis 1 + kirmizilar SAYILDI ✅ ama "429
    // GORUNUR" duser; esik 120 -> UCU DE gecer (cikis 1 · kirmizilar SAYILDI · 429
    // GORUNUR). 120 supurmenin (220 sorgu) ORTASINDADIR: ariza hala KOSUM ORTASINDA vurur,
    // yani senaryonun adi ve iddiasi AYNEN korunur — beklenti GEVSETILMEDI, oncul KURULDU.
    r429SonraAra: 120, ekEnv: HIZLI_429,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "bulunan kirmizilar SAYILDI");
      ONA(/HIZ SINIRI \(429\)/.test(r.cikti), "429 arizasi GORUNUR");
    },
  });
  senaryolar.push({
    ad: "S8 (K2) KIRMIZI + uc SUSUYOR (zaman asimi) -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI,
    susSonraAra: 25, ekEnv: HIZLI_ZA,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "bulunan kirmizilar SAYILDI");
      ONA(/ZAMAN ASIMI/.test(r.cikti), "zaman asimi arizasi GORUNUR");
    },
  });
  senaryolar.push({
    // 🔴 IDDIA TERSINE CEVRILDI (6 Agu 2026, mimar hukmu). ESKI beklenti "cikis 1"di ve
    // TAVAN'i gercek bir gerileme gibi raporluyordu. Olculdu: tavan SABIT oldugu icin
    // katalog 20.212'ye cikinca asildi ve katalog farkiyla ACIKLANABILIR sapmalar KIRMIZI
    // yandi (526 sahte kirmizi). Tavan BIZIM istek butcemizdir; asilmasi "uc bozuk" degil
    // "kaniti URETEMEDIK" demektir -> hukum ACIK OLCULEMEDI (3) birimindedir
    // ([[hukum-yanlis-birimde]] · [[test-hatali-davranisi-kutsar]]).
    // AF YOK: 3 de BLOKE eder (sozlesme: 3 yayin yolunda gecirilmez); asil iddia
    // "0 URETILMEZ"dir ve asagida AYRICA olculur.
    ad: "S9 (K2) ayrisim VAR + supurme TAVANI asildi -> cikis 3 (dayanaksiz KIRMIZI YOK, 0 da YOK)",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), gizliAra: GIZLI,
    ekEnv: { PARITE_SUPURME_TAVANI: "1" },
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3 OLCULEMEDI", r.cikti.slice(-900));
      ONA(r.kod !== 0, "AF YOK: tavan asimi hicbir kosulda 0 URETMEZ");
      ONA(/TAVANI asildi/.test(r.cikti), "tavan asimi GORUNUR");
      ONA(/SUPURME TAVANI/.test(r.cikti), "sebep ADIYLA yazili");
      ONA(/0\/\d+ sorgu olculdu/.test(r.cikti),
        "kanitsiz sorgu OLCULMEDI (dayanaksiz kirmizi uretilmedi)");
    },
  });
  senaryolar.push({
    ad: "S10 (K2) KIRMIZI + on-kosul SAYIMI olculemedi -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI, sayimHata: true,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
      ONA(/canli katalog sayisi OLCULEMEDI/.test(r.cikti), "sayim arizasi GORUNUR");
    },
  });

  // ── M5 MUTANT NOBETI: supurme hatasinda FAIL-OPEN olursa yakalanmali ──────────────
  senaryolar.push({
    ad: "S11 (M5) SUPURME HATASI (ids ucu 500) + ayrisim -> kanit YOK, cikis 1 (fail-closed)",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), idsHata: true,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (fail-OPEN olsaydi 3 olurdu)", r.cikti.slice(-900));
      ONA(/id supurmesi TAMAMLANAMADI/.test(r.cikti), "supurme hatasi GORUNUR");
      ONA(/kanit yok, siniflandirma KAPALI/.test(r.cikti), "kanit yoksa siniflandirma ACILMAZ");
      ONA(!/SENKRON GEC/.test(r.cikti), "kanitsiz 'senkron gecikmesi' damgasi VURULMADI");
    },
  });

  // ── M6 MUTANT NOBETI: "D1 EKSIK eslesme" kapisi kaldirilirsa yakalanmali ──────────
  // gecikmeModu ACIK (yerel ⊂ canli, supurme kaniti var) ama D1 bazi yerel urunleri
  // ARAMADA gostermiyor -> toplam < yerel. Bu, katalog farkiyla ACIKLANAMAZ.
  senaryolar.push({
    ad: "S12 (M6) gecikme modu ACIK + D1 EKSIK eslesme -> cikis 1",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), gizliAra: GIZLI,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (kapi kaldirilsaydi 3 olurdu)", r.cikti.slice(-900));
      ONA(/D1 EKSIK eslesme/.test(r.cikti), "sebep: D1 EKSIK eslesme (yerel ⊆ D1 kanitina aykiri)");
    },
  });

  // ── A8: TESHIS DURUSTLUGU — tek yetim satir, checkout TAZE ───────────────────────
  senaryolar.push({
    ad: "S13 (A8) D1'de TEK YETIM satir, checkout TAZE -> cikis 3 ama YANLIS teshis BASMAZ",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.concat(YETIM),
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3 (0 DEGIL)", r.cikti.slice(-900));
      ONA(!/checkout BAYAT: yerel=/.test(r.cikti),
        "OLGUSAL YANLIS teshis ('checkout BAYAT: yerel=N < canli=M') BASILMIYOR");
      ONA(/AYIRT EDILEMEDI/.test(r.cikti), "belirsizlik ACIKCA yazili (AYIRT EDILEMEDI)");
      ONA(/YETIM satir/.test(r.cikti), "ikinci olasilik ADIYLA sayiliyor (D1'de YETIM satir)");
      ONA(/D1 FAZLALIGI: yerel=\d+ < canli=\d+ \| fazla=\d+/.test(r.cikti),
        "teshis metni OLCULEN kanittan turetilmis (sayilar)");
    },
  });

  // ── B2: GECICI 429 -> yeniden deneme TUTMALI (kapi susmamali) ────────────────────
  senaryolar.push({
    ad: "S14 (B2) GECICI 429 (ilk istekler) -> yeniden deneme TUTAR, ayrisim 0",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), r429IlkKere: 2,
    ekEnv: { PARITE_DENEME: "3", PARITE_BEKLEME_MS: "5" },
    dogrula: (r) => {
      ONA(fiksturYesil(r), "cikis 3 + ayrisim 0 (429 kosumu OLDURMEDI)", r.cikti.slice(-700));
      ONA(/429: [1-9]/.test(r.cikti), "429 SAYILDI ve raporlandi (sessizce yutulmadi)");
      ONA(/yeniden deneme: [1-9]/.test(r.cikti), "yeniden deneme SAYILDI");
    },
  });

  // ── Arizalar TEK BASINA (kirmizi yokken): asla 0, daima 3 ────────────────────────
  senaryolar.push({
    ad: "S15 kirmizi YOK + zaman asimi -> cikis 3 (asla 0), erken durma GORUNUR",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), susSonraAra: 20, ekEnv: HIZLI_ZA,
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-700));
      ONA(/ZAMAN ASIMI/.test(r.cikti), "zaman asimi GORUNUR");
      ONA(/kosum ERKEN DURDU: \d+\/\d+/.test(r.cikti), "kac sorgunun olculdugu SAYIYLA yazili");
    },
  });
  senaryolar.push({
    // canli == yerel (sorgular birebir eslesir) ama /katalog SAYIMI sapiyor -> supurme
    // tetiklenir, TAVAN asilir. Hicbir ayrisim yok: eski kod burada 0 verirdi. AF YOK -> 3.
    ad: "S16 kirmizi YOK + supurme TAVANI asildi -> cikis 3 (asla 0)",
    dosya: PARITE_SITE, yerel: TABAN, canli: TABAN.slice(), sayiSapma: 5,
    ekEnv: { PARITE_SUPURME_TAVANI: "1" },
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-700));
      ONA(/TAVANI asildi/.test(r.cikti), "tavan asimi GORUNUR");
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "hic ayrisim YOK ama yine de 0 verilmedi");
    },
  });

  // 17-21) Ege tarafi AYNI kurala tabi mi? (bot kaynagi yoksa atlanir)
  if (EGE) {
    senaryolar.push({
      ad: "S17 EGE SAGLAMA: yerel == canli -> ayrisim 0 + cikis 3",
      dosya: PARITE_EGE, yerel: TABAN, canli: TABAN.slice(),
      dogrula: (r) => {
        ONA(fiksturYesil(r), "cikis 3 + ayrisim 0 + FIKSTUR: BIREBIR ESLESTI", r.cikti.slice(-700));
      },
    });
    senaryolar.push({
      ad: "S18 (K4/ege) BAYAT CHECKOUT -> cikis 3, KIRMIZI DEGIL",
      dosya: PARITE_EGE, yerel: TABAN, canli: EK.concat(TABAN),
      dogrula: (r) => {
        ONA(r.kod === 3, "cikis 3", r.cikti.slice(-900));
        ONA(/SENKRON GEC/.test(r.cikti), "'SENKRON GECİKMESİ' imzasi");
        ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0");
      },
    });
    senaryolar.push({
      ad: "S19 (K4-a/ege) YERELDE VAR / D1'DE YOK -> cikis 1 KIRMIZI",
      dosya: PARITE_EGE, yerel: TABAN, canli: EK.concat(TABAN.filter((p, i) => i !== 7)),
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-800));
        ONA(/YERELDE VAR \/ D1'DE YOK/.test(r.cikti), "sebep dogru");
      },
    });
    senaryolar.push({
      ad: "S20 (K2/ege) KIRMIZI + kosum ortasinda 429 -> cikis 1",
      dosya: PARITE_EGE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI,
      r429SonraAra: 20, ekEnv: HIZLI_429,
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI (ariza kirmiziyi SILEMEZ)", r.cikti.slice(-900));
        ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "bulunan kirmizilar SAYILDI");
        ONA(/HIZ SINIRI \(429\)/.test(r.cikti), "429 arizasi GORUNUR");
      },
    });
    senaryolar.push({
      ad: "S21 (K2/ege) KIRMIZI + kosum ortasinda WAF 403 -> cikis 1",
      dosya: PARITE_EGE, yerel: TABAN, canli: TABAN.slice(), gizliAra: GIZLI, wafSonraAra: 20,
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-900));
        ONA(/OLCUM ARIZASI VAR/.test(r.cikti), "ariza GORUNUR ama KIRMIZI kazandi");
      },
    });
  } else {
    console.log("\n⚪ Ege senaryolari ATLANDI: bot kaynagi yok (" + EGE_MOD.BOT + ")");
  }

  // ══ 🔴 8. YUTMA (27 Tem, bagimsiz curutme C6/C7/C12) — KALICI NOBET ══════════════
  // Kurban yerel listenin KUYRUGUNDA + D1'e giren yeni urun(ler) SAYIYI TELAFI ediyor.
  // Onek kapisi (kurban kuyrukta) ve sayi kapisi (telafi) BIRLIKTE susuyordu ->
  // "yerelde VAR / D1 aramasinda YOK" (Ege GOREMEZ) ayrisimi ACIKLANAN damgasi yiyip
  // cikis 3 uretiyor, cikti "hicbir ayrisim tehlikeli yonde DEGIL" diye OLGUSAL YANLIS
  // basiyordu. Taban 45753c1f ayni girdide 1 veriyordu -> REGRESYONDU.
  senaryolar.push({
    ad: "S22 (8. YUTMA) kurban KUYRUKTA + 1 yeni urun TELAFI -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, canli: klonla(KURBAN, 1).concat(TABAN),
    gizliAra: KURBAN_GIZLI,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI (telafi edilmis sayi ayrisimi GIZLEYEMEZ)",
        r.cikti.slice(-1100));
      ONA(/YERELDE VAR \/ D1 ARAMASINDA YOK/.test(r.cikti), "sebep: yerelde var / D1'de yok");
      ONA(/Ege GOREMEZ/.test(r.cikti), "sonucun bedeli yazili (Ege goremez)");
      ONA(new RegExp(KURBAN.id + "(\\D|$)").test(r.cikti), "KURBAN id'si ADIYLA yazili");
      ONA(!/PARITE KIRIK DEGIL/.test(r.cikti), "'PARITE KIRIK DEGIL' kesin hukmu BASILMIYOR");
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "aciklanamayan > 0 (ACIKLANAN'a yuvarlanmadi)");
    },
  });
  senaryolar.push({
    ad: "S23 (8. YUTMA) kurban KUYRUKTA + 3 yeni urun TELAFI -> cikis 1 KIRMIZI",
    dosya: PARITE_SITE, yerel: TABAN, canli: klonla(KURBAN, 3).concat(TABAN),
    gizliAra: KURBAN_GIZLI,
    dogrula: (r) => {
      ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-1100));
      ONA(/YERELDE VAR \/ D1 ARAMASINDA YOK/.test(r.cikti), "sebep dogru");
      ONA(/katalog farki butcesi=\d+/.test(r.cikti), "butce SAYIYLA yazili (olculen kanit)");
      ONA(!/SENKRON GECİKMESİ \/ KATALOG FARKI/.test(r.cikti),
        "senkron gecikmesine YUVARLANMADI");
    },
  });
  // KONTROL (K5): AYNI telafi deseni, ama kurban YOK -> mesru gecikme, KIRMIZI DEGIL.
  // Bu kontrol olmadan yeni kapi "her fazlaligi kirmizi say" diye gevsetilebilirdi.
  senaryolar.push({
    ad: "S24 KONTROL(K5) ayni telafi deseni ama KURBAN YOK -> cikis 3 SENKRON GECIKMESI",
    dosya: PARITE_SITE, yerel: TABAN, canli: klonla(KURBAN, 3).concat(TABAN),
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3 (yanlis-pozitif YOK)", r.cikti.slice(-900));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0");
      ONA(/SENKRON GEC/.test(r.cikti), "'SENKRON GECİKMESİ' imzasi");
      ONA(!/YERELDE VAR \/ D1 ARAMASINDA YOK/.test(r.cikti), "yeni kapi BOS YERE atesmiyor");
    },
  });
  // DURUSTLUK KAPISI: pencere, ucun ilan ettigi toplami KAPSAMIYOR -> pencere disi
  // OLCULMEDI -> "hicbir ayrisim tehlikeli yonde DEGIL" KESIN HUKMU basilamaz.
  senaryolar.push({
    ad: "S25 (DURUSTLUK) /ara toplami pencereyi ASIYOR -> 3 ama KESIN HUKUM BASMAZ",
    dosya: PARITE_SITE, yerel: TABAN, canli: EK.concat(TABAN), araToplamSapma: 2,
    dogrula: (r) => {
      ONA(r.kod === 3, "cikis 3", r.cikti.slice(-900));
      ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0 (kirmizi degil)");
      ONA(/KESIN HUKUM VERILEMEZ/.test(r.cikti), "olculemeyen pencere ACIKCA ilan ediliyor");
      ONA(/OLCULMEDI/.test(r.cikti), "neyin olculmedigi yazili");
      ONA(!/Hicbir ayrisim 'yerelde var\/D1'de yok'/.test(r.cikti),
        "OLGUSAL HUKUM cumlesi ('hicbir ayrisim ... DEGIL') BASILMIYOR");
    },
  });
  if (EGE) {
    senaryolar.push({
      ad: "S26 (8. YUTMA/ege) kurban KUYRUKTA + 3 telafi -> cikis 1 KIRMIZI",
      dosya: PARITE_EGE, yerel: TABAN, canli: klonla(KURBAN, 3).concat(TABAN),
      gizliAra: KURBAN_GIZLI,
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI (Ege yolu da kapali)", r.cikti.slice(-1100));
        ONA(/YERELDE VAR \/ D1 ARAMASINDA YOK/.test(r.cikti), "sebep dogru");
        ONA(!/PARITE KIRIK DEGIL/.test(r.cikti), "kesin hukum BASILMIYOR");
      },
    });
    senaryolar.push({
      ad: "S27 (8. YUTMA/ege) kurban KUYRUKTA + 1 telafi -> cikis 1 KIRMIZI",
      dosya: PARITE_EGE, yerel: TABAN, canli: klonla(KURBAN, 1).concat(TABAN),
      gizliAra: KURBAN_GIZLI,
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI", r.cikti.slice(-1100));
        ONA(/YERELDE VAR \/ D1 ARAMASINDA YOK/.test(r.cikti), "sebep dogru");
      },
    });
    senaryolar.push({
      ad: "S28 KONTROL(K5/ege) ayni telafi ama KURBAN YOK -> cikis 3",
      dosya: PARITE_EGE, yerel: TABAN, canli: klonla(KURBAN, 3).concat(TABAN),
      dogrula: (r) => {
        ONA(r.kod === 3, "cikis 3 (yanlis-pozitif YOK)", r.cikti.slice(-900));
        ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") === 0, "aciklanamayan = 0");
      },
    });

    // ══ MARKA EKSENI (06 Agu) — referans `marka_arama` UYELIGINDEN turuyor mu? ═══════
    // Uc 05 Agu'da marka adi sorgusunu uyelige bagladi; referans serbest metinde kaldigi
    // icin test KENDI bayatligini "gerileme" diye rapor ediyordu (37/847, tamami marka
    // sorgusu). Asagidaki uc senaryo o ekseni OLCER; mutantlar (parite-mutasyon-test.js
    // M26-M29) referansi eski/ikiz yukleme dondurdugunde SM1 kirmizi yanar.
    // 🔴 argv=[] (TUM sorgu havuzu): marka adlari havuzun ORTASINDA; 220'lik dilim
    // capalari (Vauxhall/Haval) DISARIDA birakabilirdi -> eksen sessizce olculmezdi.
    const MARKA_KATALOG = markaKatalogUret();
    senaryolar.push({
      ad: "SM1 MARKA EKSENI: referans `marka_arama` uyeliginden turer -> ayrisim 0 + cikis 3",
      dosya: PARITE_EGE, yerel: MARKA_KATALOG, canli: MARKA_KATALOG.slice(),
      markaEkseni: true, argv: [],
      dogrula: (r) => {
        ONA(fiksturYesil(r), "cikis 3 + ayrisim 0 + FIKSTUR: BIREBIR ESLESTI", r.cikti.slice(-1200));
        ONA(/marka referansi: \d+ marka/.test(r.cikti),
          "marka referansi FIILEN KURULDU (sessizce serbest metne dusulmedi)");
      },
    });
    senaryolar.push({
      ad: "SM2 KORELME NOBETI: marka dalinda GERCEK uc gerilemesi (bir urun eksik) -> cikis 1",
      dosya: PARITE_EGE, yerel: MARKA_KATALOG, canli: MARKA_KATALOG.slice(),
      markaEkseni: true, argv: [],
      // Uc, marka kumesinden TEK urunu dusuruyor (Ege GOREMEZ = sessiz satis kaybi).
      // Onarim bayat referansi susturdu; bu senaryo GERCEK alarmin hala caldigini olcer.
      gizliAra: new Set([MARKA_KATALOG[0].id]),
      dogrula: (r) => {
        ONA(r.kod === 1, "cikis 1 KIRMIZI (gercek gerileme hala yakalaniyor)", r.cikti.slice(-1200));
        ONA(sayiOku(r.cikti, "ACIKLANAMAYAN") > 0, "ayrisim SAYILDI");
        ONA(!/PARITE KIRIK DEGIL/.test(r.cikti), "kesin hukum BASILMIYOR");
      },
    });
    senaryolar.push({
      ad: "SM3 FAIL-CLOSED: kanonik uretec YOKKEN cikis 3 (ASLA 0, eski referansa DUSMEZ)",
      dosya: PARITE_EGE, yerel: MARKA_KATALOG, canli: MARKA_KATALOG.slice(),
      markaEkseni: true, argv: [],
      // Cocuk kosuma BOZUK bir agac koku verilir -> tools/d1-sync.py bulunamaz. Sahte uc
      // (ebeveyn) GERCEK koku kullanmaya devam eder, yani uc DOGRU, referans OLCULEMEZ.
      ekEnv: { PARITE_INDEX_KOK: path.join(os.tmpdir(), "pruvo-yok-boyle-bir-kok") },
      dogrula: (r) => {
        ONA(r.kod === 3, "cikis 3 OLCULEMEDI", r.cikti.slice(-1200));
        ONA(/marka referansi KURULAMADI/.test(r.cikti), "sebep ADIYLA yazili");
        ONA(sayiOku(r.cikti, "gecti") === 0, "0 sorgu olculdu (eski referansla DEVAM ETMEDI)");
      },
    });
  }

  console.log("═".repeat(78));
  console.log("PARITE KARAR-CEKIRDEGI FIKSTURU — %d senaryo (ag YOK, canliya 0 istek)",
    senaryolar.length);
  console.log("═".repeat(78));

  if (!Number.isFinite(yalniz)) birimOlc();

  for (let i = 0; i < senaryolar.length; i++) {
    if (Number.isFinite(yalniz) && yalniz !== i) continue;
    await senaryoKos(Object.assign({ EGE }, senaryolar[i]));
  }

  console.log("\n" + "═".repeat(78));
  console.log("IDDIA: %d gecti | %d KALDI", gecen, kalan);
  // Makine-okunur ozet (mutasyon harness'i bunu ayristirir: hangi senaryo yakaladi).
  for (const ad of kalanSenaryolar) console.log("KALAN-SENARYO: " + ad);
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
