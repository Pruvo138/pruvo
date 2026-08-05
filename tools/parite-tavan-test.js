#!/usr/bin/env node
"use strict";
/**
 * SUPURME TAVANI OLCEK KAPISI — tavan SABIT DEGIL, KATALOG BOYUTUNDAN TURER.
 *
 *   node tools/parite-tavan-test.js                # kabul iddialari
 *   node tools/parite-tavan-test.js --kendini-test # kabul + MUTASYON bataryasi
 *
 * NEDEN VAR (olculdu 5-6 Agu 2026): `SUPURME_TAVANI` sabit 200 parti = 20.000 id idi.
 * Katalog 20.212'ye cikinca tavan ASILDI. Yerel ve canli sayilar ESITKEN supurme hic
 * kosmadigi icin bu gorunmuyordu; sayilar ayristigi ANDA "yerel ⊆ D1" kaniti uretilemedi,
 * siniflandirma kapandi ve katalog farkiyla ACIKLANABILIR her sapma KIRMIZI yandi
 * (bir kosumda 526 sahte kirmizi). Yani sabit sayi, katalog buyudugu icin testin KENDISINI
 * bozan bir zaman bombasiydi ([[katalog-olcek-siniri]] · [[hukum-yanlis-birimde]]).
 *
 * BU KAPININ IDDIALARI (dordu de mimarin kabul olcutu):
 *   K1  bugunku katalog boyunda supurme EKSIKSIZ (tavan carpMAZ, tum partiler kosar),
 *   K2  katalog IKI KATINA cikarilmis fiksturde de EKSIKSIZ,
 *   K3  tavani SABITLEYEN mutant KIRMIZI (regresyon geri gelirse yakalanir),
 *   K4  tavani SONSUZ yapan mutant da KIRMIZI (ust sinir korunmali; 429/istek butcesi var)
 *       ve mutlak sinir asildiginda hukum ACIK OLCULEMEDI'dir, sessiz yanlis-kirmizi DEGIL.
 *
 * 🔴 VERI CAPASI YOK: hicbir gercek urun id'si yok; id'ler kosum aninda uretilir. Katalog
 * BOYU capa DEGIL OLCEK EKSENIDIR — mimarin kabul olcutu ("20.212 urunle eksiksiz") aynen
 * o eksende ifade edilir, ayrica "iki kati" ve "mutlak sinirin otesi" ayri ayri olculur.
 *
 * 🔴 MUTASYON KOPYAYA UYGULANIR: canli tools/parite-ortak.js'e ASLA yazilmaz (bir kesinti
 * canliya mutant birakirdi — [[mutasyon-diske-yazma-tuzagi]]). Kabul cikis kodu DEGIL,
 * OLCULEN IMZA'dir; cokme kirmiziyla KARISTIRILMAZ ([[mutasyon-kaniti-yeniden-uretilebilir]]).
 */

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");

const ORTAK = path.join(__dirname, "parite-ortak.js");

let _gecti = 0;
const _kaldi = [];
function ONA(kosul, ad, ek) {
  if (kosul) { _gecti++; console.log("   ✅ " + ad); return; }
  _kaldi.push(ad);
  console.log("   ❌ " + ad + (ek ? "\n      " + String(ek).slice(0, 400) : ""));
}

// ── SAHTE /katalog UCU — yalniz supurmenin ihtiyaci kadar ─────────────────────────────
// `ids=` gelen id'leri AYNEN dondurur (hepsi D1'de VAR demektir); `boy=1` toplam sayar.
function sunucuKur(toplam) {
  const durum = { istek: 0, idsIstek: 0 };
  const s = http.createServer((req, res) => {
    durum.istek++;
    const u = new URL(req.url, "http://127.0.0.1");
    const ids = u.searchParams.get("ids");
    let govde;
    if (ids) {
      durum.idsIstek++;
      govde = { urunler: ids.split(",").map((id) => ({ id })) };
    } else {
      govde = { toplam, urunler: [] };
    }
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(govde));
  });
  return new Promise((c) => s.listen(0, "127.0.0.1", () => c({
    kapat: () => new Promise((k) => s.close(k)),
    uc: "http://127.0.0.1:" + s.address().port + "/ara",
    durum,
  })));
}

function idlerUret(n) {
  const l = new Array(n);
  for (let i = 0; i < n; i++) l[i] = "u" + i;
  return l;
}

/**
 * TEK KOSUM = tek olcum imzasi. Mutant da taban da AYNI fonksiyondan gecer.
 * Doner: { tavan, parti, eksik, idsIstek, hataTur, cokme }
 */
async function olc(ortakYolu, idAdedi, ekEnv) {
  const eski = {};
  for (const a of Object.keys(ekEnv || {})) { eski[a] = process.env[a]; process.env[a] = ekEnv[a]; }
  delete require.cache[require.resolve(ortakYolu)];
  const o = require(ortakYolu);
  const idler = idlerUret(idAdedi);
  const sunucu = await sunucuKur(idAdedi);
  const sayac = o.sayacYeni();
  const cikti = { tavan: null, parti: 0, eksik: null, idsIstek: 0, hataTur: null, cokme: null };
  try {
    cikti.tavan = o.supurmeTavani(idAdedi);
    const eksik = await o.d1deOlmayanlar(sunucu.uc, idler, sayac, o.nonceUret());
    cikti.eksik = eksik.length;
  } catch (e) {
    if (e && e.olcum) cikti.hataTur = e.tur;
    else cikti.cokme = String((e && e.message) || e).slice(0, 200);
  } finally {
    cikti.parti = sayac.supurmeParti || 0;
    cikti.idsIstek = sunucu.durum.idsIstek;
    await sunucu.kapat();
    for (const a of Object.keys(ekEnv || {})) {
      if (eski[a] === undefined) delete process.env[a]; else process.env[a] = eski[a];
    }
    delete require.cache[require.resolve(ortakYolu)];
  }
  return cikti;
}

/** On-kosul ekseni: tavan asilinca `durdu` (ACIK OLCULEMEDI) doner mi? */
async function olcOnKosul(ortakYolu, idAdedi, ekEnv) {
  const eski = {};
  for (const a of Object.keys(ekEnv || {})) { eski[a] = process.env[a]; process.env[a] = ekEnv[a]; }
  delete require.cache[require.resolve(ortakYolu)];
  const o = require(ortakYolu);
  // canliSayi != yerelSayi olsun ki supurme FIILEN tetiklensin (esitse hic kosmaz).
  const sunucu = await sunucuKur(idAdedi + 5);
  const cikti = { durdu: null, kirmizi: null, olculemedi: 0, cokme: null };
  try {
    const r = await o.onKosulOlc({
      uc: sunucu.uc, yerelIdler: idlerUret(idAdedi), sayac: o.sayacYeni(), nonce: o.nonceUret(),
    });
    cikti.durdu = r.durdu || null;
    cikti.kirmizi = r.kirmizi || null;
    cikti.olculemedi = (r.olculemedi || []).length;
  } catch (e) {
    cikti.cokme = String((e && e.message) || e).slice(0, 200);
  } finally {
    await sunucu.kapat();
    for (const a of Object.keys(ekEnv || {})) {
      if (eski[a] === undefined) delete process.env[a]; else process.env[a] = eski[a];
    }
    delete require.cache[require.resolve(ortakYolu)];
  }
  return cikti;
}

// ── OLCEK EKSENLERI ───────────────────────────────────────────────────────────────────
// BUGUNKU boy kosum aninda katalogdan OKUNUR (sabit yazilsaydi kapinin kendisi bayatlardi:
// katalog buyuyunce iddia yine 20.212'yi olcerdi). Katalog okunamazsa eksen ATLANMAZ,
// mimarin kabul olcutundeki sayi TABAN olarak kullanilir ve bu ACIKCA yazilir.
const KABUL_TABANI = 20212;
function bugunkuBoy() {
  try {
    const j = JSON.parse(fs.readFileSync(path.join(path.dirname(__dirname), "urunler.json"),
      "utf8"));
    const n = new Set(j.map((u) => u && u.id)).size;
    return { n: Math.max(n, KABUL_TABANI), kaynak: "urunler.json (" + n + " benzersiz id)" };
  } catch (e) {
    return { n: KABUL_TABANI, kaynak: "katalog OKUNAMADI -> kabul olcutu tabani" };
  }
}

async function kabulKos(ortakYolu, sessiz) {
  const yaz = sessiz ? () => {} : (s) => console.log(s);
  const boy = bugunkuBoy();
  const imza = [];

  // K1 — BUGUNKU katalog: supurme EKSIKSIZ.
  const bugun = await olc(ortakYolu, boy.n, {});
  const gerekli = Math.ceil(boy.n / 100);
  imza.push("K1 tavan=" + bugun.tavan + " parti=" + bugun.parti + " eksik=" + bugun.eksik +
    " hata=" + bugun.hataTur + " cokme=" + (bugun.cokme ? "VAR" : "yok"));
  yaz("\n▶ K1 BUGUNKU KATALOG (" + boy.n + " id · " + boy.kaynak + ") -> supurme EKSIKSIZ");
  if (!sessiz) {
    ONA(bugun.cokme === null, "surec COKMEDI", bugun.cokme);
    ONA(bugun.hataTur === null, "TAVAN carpMADI (sabit 200 parti burada patliyordu)");
    ONA(bugun.parti === gerekli, "TUM partiler kosuldu: " + bugun.parti + "/" + gerekli);
    ONA(bugun.eksik === 0, "'yerel ⊆ D1' kaniti URETILDI (eksik 0)");
  }

  // K2 — IKI KATI katalog: hala EKSIKSIZ (tavan katalogla birlikte buyudu).
  const iki = await olc(ortakYolu, boy.n * 2, {});
  const gerekli2 = Math.ceil((boy.n * 2) / 100);
  imza.push("K2 tavan=" + iki.tavan + " parti=" + iki.parti + " eksik=" + iki.eksik +
    " hata=" + iki.hataTur);
  yaz("\n▶ K2 KATALOG IKI KATI (" + (boy.n * 2) + " id) -> supurme YINE EKSIKSIZ");
  if (!sessiz) {
    ONA(iki.cokme === null, "surec COKMEDI", iki.cokme);
    ONA(iki.hataTur === null, "TAVAN carpMADI (tavan katalogla BIRLIKTE buyudu)");
    ONA(iki.parti === gerekli2, "TUM partiler kosuldu: " + iki.parti + "/" + gerekli2);
    ONA(iki.tavan > bugun.tavan, "tavan SABIT DEGIL: " + bugun.tavan + " -> " + iki.tavan);
  }

  // K3 — MUTLAK SINIRIN OTESI: ust sinir DURUYOR ve hukum ACIK OLCULEMEDI.
  // Mutlak sinir fikstur env'iyle KUCULTULUR (kosum suresi; env FIKSTUR_ENV listesindedir,
  // yani boyle bir kosum zaten pariteyi belgelendiremez). Olculen sey sinirin DEGERI degil
  // VAR OLUSUDUR: kaldirilirsa asagidaki mutant kirmizi yanar.
  const dar = { PARITE_SUPURME_MUTLAK: "3" };
  const asan = await olc(ortakYolu, 1000, dar);
  imza.push("K3 tavan=" + asan.tavan + " parti=" + asan.parti + " idsIstek=" + asan.idsIstek +
    " hata=" + asan.hataTur);
  yaz("\n▶ K3 MUTLAK SINIRIN OTESI (1000 id · sinir 3 parti) -> ust sinir DURUYOR");
  if (!sessiz) {
    ONA(asan.cokme === null, "surec COKMEDI", asan.cokme);
    ONA(asan.hataTur === "TAVAN", "TAVAN hatasi ADIYLA atildi (tur=" + asan.hataTur + ")");
    ONA(asan.tavan === 3, "tavan MUTLAK sinirda kapandi (sinirsiz buyume YOK)");
    ONA(asan.idsIstek === 0, "butce PATLAMADI: hicbir supurme istegi atilmadi");
  }

  // K4 — ON-KOSUL: tavan asilinca ACIK OLCULEMEDI ('durdu'), sessiz yanlis-kirmizi DEGIL.
  const ok = await olcOnKosul(ortakYolu, 1000, dar);
  imza.push("K4 durdu=" + (ok.durdu ? "VAR" : "yok") + " kirmizi=" + (ok.kirmizi ? "VAR" : "yok") +
    " olculemedi=" + ok.olculemedi);
  yaz("\n▶ K4 ON-KOSUL: tavan asildi -> ACIK OLCULEMEDI (sessiz yanlis-kirmizi DEGIL)");
  if (!sessiz) {
    ONA(ok.cokme === null, "surec COKMEDI", ok.cokme);
    ONA(!!ok.durdu, "kosum ACIKCA DURDU (sorgular olculmeden)");
    ONA(ok.kirmizi === null, "KIRMIZI hukmu BASILMADI (dayanaksiz olurdu)");
    ONA(ok.olculemedi > 0, "sebep OLCULEMEDI listesine yazildi -> cikis 3");
    ONA(/SUPURME TAVANI/.test(String(ok.durdu)), "sebep ADIYLA yazili");
  }

  return imza.join(" | ");
}

// ── MUTASYON BATARYASI ────────────────────────────────────────────────────────────────
const MUTANTLAR = [
  {
    id: "M1", oldurucu: true,
    ad: "TAVAN YENIDEN SABITLENDI (200 parti = 20.000 id — regresyonun ta kendisi)",
    eski: "  const gerekli = Math.ceil(Math.max(0, idAdedi) / IDS_PARTI);\n" +
      "  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN);",
    yeni: "  return 200;",
  },
  {
    id: "M2", oldurucu: true,
    ad: "MUTLAK UST SINIR KALDIRILDI (tavan sonsuz — istek/429 butcesi patlar)",
    eski: "  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN);",
    yeni: "  return Math.max(1, gerekli);",
  },
  {
    id: "M3", oldurucu: true,
    ad: "ACIK OLCULEMEDI KALKTI: tavan asimi yine siniflandirma-KAPALI'ya duser",
    eski: "    if (e && e.tur === \"TAVAN\") {",
    yeni: "    if (false && e.tur === \"TAVAN\") {",
  },
  {
    id: "K_A", oldurucu: false,
    ad: "KONTROL: davranis degistirmeyen yeniden adlandirma (gerekli -> gerekliParti)",
    eski: "  const gerekli = Math.ceil(Math.max(0, idAdedi) / IDS_PARTI);\n" +
      "  return Math.min(Math.max(1, gerekli), SUPURME_MUTLAK_TAVAN);",
    yeni: "  const gerekliParti = Math.ceil(Math.max(0, idAdedi) / IDS_PARTI);\n" +
      "  return Math.min(Math.max(1, gerekliParti), SUPURME_MUTLAK_TAVAN);",
  },
  {
    id: "K_B", oldurucu: false,
    ad: "KONTROL: ILGISIZ sabit eklendi (kimse okumuyor)",
    eski: "function supurmeTavani(idAdedi) {",
    yeni: "function supurmeTavani(idAdedi) {\n  const kullanilmayan = 42; void kullanilmayan;",
  },
];

async function kendiniTest() {
  const kaynak = fs.readFileSync(ORTAK, "utf8");
  const kok = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-tavan-"));
  console.log("\n" + "=".repeat(78));
  console.log("MUTASYON BATARYASI — mutant KOPYAYA uygulanir, canli dosyaya ASLA");
  console.log("=".repeat(78));

  const tabanYolu = path.join(kok, "taban-parite-ortak.js");
  fs.writeFileSync(tabanYolu, kaynak);
  const taban = await kabulKos(tabanYolu, true);
  console.log("\nTABAN IMZA: " + taban);

  let oldurucuKirmizi = 0, oldurucuTop = 0, kontrolYesil = 0, kontrolTop = 0;
  let sapan = 0, capaYok = 0, cokme = 0;

  for (const m of MUTANTLAR) {
    if (m.oldurucu) oldurucuTop++; else kontrolTop++;
    const kez = kaynak.split(m.eski).length - 1;
    if (kez !== 1) {
      capaYok++;
      console.log("\n❌ " + m.id + " CAPA-YOK: desen kaynakta " + kez + " kez gecti (1 olmali) — " +
        "sonuc YESIL SAYILMAZ");
      continue;
    }
    const yol = path.join(kok, m.id + "-parite-ortak.js");
    fs.writeFileSync(yol, kaynak.replace(m.eski, m.yeni));
    let imza;
    try {
      imza = await kabulKos(yol, true);
    } catch (e) {
      cokme++;
      console.log("\n💥 " + m.id + " COKME (kirmiziyla KARISTIRILMAZ): " +
        String((e && e.message) || e).slice(0, 200));
      continue;
    }
    const farkli = imza !== taban;
    if (m.oldurucu) {
      if (farkli) { oldurucuKirmizi++; console.log("\n✅ " + m.id + " " + m.ad); }
      else { sapan++; console.log("\n❌ SAPAN " + m.id + " " + m.ad + " — imza DEGISMEDI"); }
      console.log("   taban : " + taban);
      console.log("   mutant: " + imza);
    } else {
      if (!farkli) { kontrolYesil++; console.log("\n✅ " + m.id + " " + m.ad + " -> imza AYNI"); }
      else {
        sapan++;
        console.log("\n❌ ASIRI-HASSAS " + m.id + " " + m.ad);
        console.log("   taban : " + taban);
        console.log("   mutant: " + imza);
      }
    }
  }

  fs.rmSync(kok, { recursive: true, force: true });
  console.log("\n" + "-".repeat(78));
  console.log("BATARYA_OZET oldurucu=" + oldurucuKirmizi + "/" + oldurucuTop +
    " kontrol=" + kontrolYesil + "/" + kontrolTop + " sapan=" + sapan +
    " capa-yok=" + capaYok + " cokme=" + cokme);
  return oldurucuKirmizi === oldurucuTop && kontrolYesil === kontrolTop &&
    sapan === 0 && capaYok === 0 && cokme === 0;
}

(async () => {
  console.log("=".repeat(78));
  console.log("SUPURME TAVANI OLCEK KAPISI — tavan katalogdan TURER, sabit DEGIL");
  console.log("=".repeat(78));
  await kabulKos(ORTAK, false);

  let bataryaTemiz = true;
  if (process.argv.includes("--kendini-test")) bataryaTemiz = await kendiniTest();

  console.log("\n" + "-".repeat(78));
  console.log("IDDIA: %d gecti | %d KALDI", _gecti, _kaldi.length);
  if (_kaldi.length || !bataryaTemiz) {
    if (_kaldi.length) for (const k of _kaldi) console.log("  ❌ " + k);
    if (!bataryaTemiz) console.log("  ❌ MUTASYON BATARYASI TEMIZ DEGIL");
    console.log("SONUC: KIRMIZI ❌");
    process.exit(1);
  }
  console.log("SONUC: YESIL ✅ — tavan katalogdan turuyor, ust sinir duruyor, " +
    "asilirsa ACIK OLCULEMEDI");
})().catch((e) => { console.error("COKME:", e); process.exit(1); });
