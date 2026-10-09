/*
 * foto-sepet.mjs — FOTO KALEMI NORMAL SEPETTE (sayfa-3adim K1), ISTEMCI tarafi.
 *
 * Foto bolumunun ③ "Sepete ekle"si kalemi sitenin normal sepetine koyar; ayri foto odeme yolu YOK.
 * Sunucu tarafi (istemci fiyati yok sayilir, tur/renk_sayisi denetimi, karma sepet tek odeme, kuyruk)
 * shop/test/foto-uretim.mjs "SP)" bolumunde. Burada:
 *   C1 /baslat kalemi 7/7 alan {foto_is, tur, olcu_mm, renkler, renk_sayisi, onizleme_ref, atif} + adet 1,
 *      gosterim fiyati / baslik / onay kaleme GIRMEZ (fiyat sunucuda)
 *   C2 sepet yeniden yukleme (localStorage) foto satirini BOZMAZ; karma sepette katalog satiri da durur
 *   C3 foto satirinin adedi SABIT 1 (adet 5 yazilsa da)
 *   C4 aydinlatma onaysiz / surumsuz foto satiri odenebilir DEGIL; onayli satir odenebilir
 *   C5 ayni onizleme ikinci kez -> ayni anahtar (satir yenilenir), farkli onizleme -> ayri satir
 *   C6 ayri foto odeme yolu SILINDI: foto-uretim.js /baslat cagirmaz, musteri formu (S4) yok,
 *      kalemi window.pruvoSepeteFotoEkle ile normal sepete verir; index.html o kapiyi tanimlar ve
 *      odemede foto satirini fotoKalemi ile + aydinlatma onayini govdede gonderir
 * Mutantlar secenekler.js'in GECICI kopyasi uzerinde (vm; disk yazimi YOK): her biri TAM OLARAK
 * beklenen iddiayi kirmizi yakar; kontrol mutanti hicbirini.
 * CIKIS KODU: 0 yesil · 1 kirmizi.
 */
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const KOK = path.join(path.dirname(url.fileURLToPath(import.meta.url)), "..", "..");
const SECENEK_KAYNAK = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");
const BOLUM = fs.readFileSync(path.join(KOK, "foto-uretim.js"), "utf8");
const INDEX = fs.readFileSync(path.join(KOK, "index.html"), "utf8");

let kirmizi = 0;
const ol = (ad, kosul, ek) => {
  console.log((kosul ? "  ✅ " : "  ❌ ") + ad + (kosul ? "" : " — " + (ek || "")));
  if (!kosul) { kirmizi++; }
};

function secenekKur(kaynak) {
  const depo = {};
  const kok = {
    localStorage: {
      getItem: (a) => (Object.prototype.hasOwnProperty.call(depo, a) ? depo[a] : null),
      setItem: (a, b) => { depo[a] = String(b); },
      removeItem: (a) => { delete depo[a]; },
    },
  };
  kok.window = kok;
  vm.runInNewContext(kaynak, kok, { filename: "secenekler.js" });
  return kok.PRUVO_SECENEK;
}

const IS1 = "a".repeat(32), IS2 = "b".repeat(32);
const ham = (ek) => ({
  foto_is: IS1, tur: "plaket", olcu_mm: 100, renkler: ["Beyaz", "Siyah"], renk_sayisi: 2,
  onizleme_ref: "/api/shop/foto/gorsel?is=" + IS1, atif: { utm_source: "test" }, adet: 1,
  baslik: "Fotoğrafından özel üretim — Plaket (100 mm)", gosterim_kurus: 110000,
  aydinlatma_onay: true, onay_surum: "2026-10-07-taslak-2", ...(ek || {}),
});
const YEDI = ["foto_is", "tur", "olcu_mm", "renkler", "renk_sayisi", "onizleme_ref", "atif"];

function senaryolar(S) {
  const s = {};
  const satir = S.fotoSatirSuz(ham());
  const k = satir ? S.fotoKalemi(satir) : {};
  const anahtarlar = Object.keys(k).sort();
  s.C1 = !!satir && YEDI.every((a) => Object.prototype.hasOwnProperty.call(k, a)) && k.adet === 1 &&
    JSON.stringify(anahtarlar) === JSON.stringify([...YEDI, "adet"].sort()) &&
    k.foto_is === IS1 && k.tur === "plaket" && k.olcu_mm === 100 && JSON.stringify(k.renkler) === '["Beyaz","Siyah"]' &&
    k.renk_sayisi === 2 && k.onizleme_ref === "/api/shop/foto/gorsel?is=" + IS1 && k.atif.utm_source === "test";

  const katalog = { id: "ornek-urun", malzeme: "PLA", renk: "Siyah", renk_ozel: "", boy_etiket: null, adet: 2 };
  S.sepetKaydet([katalog, satir]);
  const geri = S.sepetYukle();
  const fotoGeri = geri.find((x) => x && x.foto_is === IS1);
  s.C2 = geri.length === 2 && geri[0].id === "ornek-urun" && geri[0].adet === 2 && !!fotoGeri &&
    JSON.stringify(fotoGeri) === JSON.stringify(satir) &&
    JSON.stringify(S.fotoKalemi(fotoGeri)) === JSON.stringify(k);

  const coklu = S.fotoSatirSuz(ham({ adet: 5 }));
  s.C3 = !!coklu && coklu.adet === 1 && S.fotoKalemi(coklu).adet === 1 && S.satirOzeti(null, coklu).adet === 1;

  const onaysiz = S.fotoSatirSuz(ham({ aydinlatma_onay: false }));
  const surumsuz = S.fotoSatirSuz(ham({ onay_surum: "" }));
  const ozet = S.satirOzeti(null, satir);
  s.C4 = ozet.odenebilir === true && ozet.kurus === 110000 && S.satirOzeti(null, onaysiz).odenebilir === false &&
    S.satirOzeti(null, surumsuz).odenebilir === false;

  const ayni = S.fotoSatirSuz(ham({ olcu_mm: 140 }));
  const baska = S.fotoSatirSuz(ham({ foto_is: IS2 }));
  s.C5 = S.satirAnahtari(ayni) === S.satirAnahtari(satir) && S.satirAnahtari(baska) !== S.satirAnahtari(satir);
  return s;
}

console.log("C) FOTO KALEMI NORMAL SEPETTE (istemci)");
{
  const s = senaryolar(secenekKur(SECENEK_KAYNAK));
  ol("C1 /baslat kalemi 7/7 alan + adet 1; gosterim fiyati/baslik/onay kaleme GIRMEZ", s.C1, JSON.stringify(s));
  ol("C2 sepet yeniden yukleme foto satirini bozmaz (karma sepet, katalog satiri da durur)", s.C2, JSON.stringify(s));
  ol("C3 foto satiri adedi SABIT 1", s.C3, JSON.stringify(s));
  ol("C4 aydinlatma onaysiz/surumsuz foto satiri odenebilir DEGIL, onayli odenebilir", s.C4, JSON.stringify(s));
  ol("C5 ayni onizleme ayni satir, farkli onizleme ayri satir", s.C5, JSON.stringify(s));
}

console.log("C6) AYRI FOTO ODEME YOLU SILINDI");
{
  const odeme = INDEX.slice(INDEX.indexOf("async function odemeBaslat(){"), INDEX.indexOf("havaleEkraniGoster(veri);"));
  ol("C6a foto-uretim.js /api/shop/baslat cagirmaz, musteri formu (S4/siparisVer) YOK",
     !BOLUM.includes("/api/shop/baslat") && !/function (cizS4|siparisVer)\b/.test(BOLUM) && !BOLUM.includes('"S4"'), "");
  ol("C6b foto-uretim.js kalemi window.pruvoSepeteFotoEkle ile normal sepete verir; onaysiz ekleme reddedilir",
     BOLUM.includes("kok.pruvoSepeteFotoEkle") && /!S\.aydinlatmaOnay\) \{\s*adimKoy\("S3"/.test(BOLUM), "");
  ol("C6c index.html kapiyi tanimlar (window.pruvoSepeteFotoEkle = sepeteFotoEkle, secenekler suzgeci)",
     INDEX.includes("window.pruvoSepeteFotoEkle = sepeteFotoEkle") && INDEX.includes("PRUVO_SECENEK.fotoSatirSuz(ham)"), "");
  ol("C6d odeme: foto satiri fotoKalemi ile gider + aydinlatma onayi govdede",
     odeme.includes("return PRUVO_SECENEK.fotoKalemi(L.satir);") &&
     odeme.includes("aydinlatma_onay: fotoOnay.aydinlatma_onay, onay_surum: fotoOnay.onay_surum"), "");
}

console.log("CM) MUTANTLAR (secenekler.js gecici kopyasi, vm)");
const MUTANTLAR = [
  ["CM1 /baslat kalemine gosterim fiyati sizar",
   ["renk_sayisi: satir.renk_sayisi, onizleme_ref: satir.onizleme_ref || \"\", atif: satir.atif || {}, adet: 1 };",
    "renk_sayisi: satir.renk_sayisi, onizleme_ref: satir.onizleme_ref || \"\", atif: satir.atif || {}, adet: 1, gosterim_kurus: satir.gosterim_kurus };"],
   ["C1"]],
  ["CM2 yeniden yuklemede foto satiri dusurulur",
   ["      if (fotoSatirMi(x)) { return fotoSatirSuz(x); }\n", ""], ["C2"]],
  ["CM3 foto adedi istemciden okunur",
   ["      adet: 1,\n      baslik:", "      adet: x.adet || 1,\n      baslik:"], ["C3"]],
  ["CM4 aydinlatma onayi odenebilirlikten kalkar",
   ["      odenebilir: k != null && satir.aydinlatma_onay === true && !!satir.onay_surum", "      odenebilir: k != null"], ["C4"]],
  ["CM5 foto satir anahtari katalog anahtarina duser",
   ["    if (satir && satir.foto_is !== undefined) { return \"foto|\" + satir.foto_is; }\n", ""], ["C5"]],
  ["CM-K KONTROL",
   ["// ---- FOTOĞRAFTAN ÖZEL ÜRETİM kalemi", "// ---- fotoğraftan özel üretim kalemi"], []],
];
for (const [ad, [capa, yerine], olmeli] of MUTANTLAR) {
  if (SECENEK_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, "capa kayip/coklu"); continue; }
  let s;
  try { s = senaryolar(secenekKur(SECENEK_KAYNAK.replace(capa, yerine))); }
  catch (e) { s = { hata: String(e) }; }
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

console.log(kirmizi ? "\n❌ " + kirmizi + " iddia KIRMIZI" : "\n✅ HEPSI GECTI");
process.exit(kirmizi ? 1 : 0);
