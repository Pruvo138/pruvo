/**
 * Resend e-posta istemcisi + PRUVO siparis sablonlari (siparis yonetimi paketi, Faz 2).
 *
 * KIRMIZI CIZGILER (tools/paket-siparis-yonetimi.md):
 *  - env.RESEND_API_KEY YOKSA e-posta SESSIZCE ATLANMAZ: cagiran Telegram'a "anahtar yok"
 *    duser. E-posta HATASI ODEMEYI ASLA DUSURMEZ — gonderim ctx.waitUntil icinde, try/catch'li.
 *  - Anahtar loglara/hata metnine yazilmaz.
 *  - Metinler Turkce, sade HTML tablo. Pazarlama dili yok. "3D baski" DENMEZ ("ozel uretim").
 *  - RESEND_URL env ile ezilebilir (kabul testi mock'u; varsayilan https://api.resend.com).
 *  - 🔴 SINIF BEYANI (tuketici hukuku, 1 Agu): siparis onay metni SEPETIN SINIFINA gore
 *    yazilir. HAZIR/STOK kalemde URETIM DILI KULLANILMAZ ve 14 gunluk cayma hakki
 *    hatirlatilir; OZEL URETIMDE bugunku dil AYNEN korunur; KARMA sepette ikisi de
 *    soylenir ve hangi kalemin hangi sinifta oldugu KALEM BAZINDA gorunur.
 *    Cumleler ve sinif karari TEK KAYNAK /secenekler.js BEYAN + fizikselMi — burada
 *    TEKRARLANMAZ. Nobetci: tools/cayma-beyani-kapisi.py (BOLUM A).
 */

import "../../secenekler.js";   // yan etkili: globalThis.PRUVO_SECENEK'i kurar (tek kaynak)

const GONDEREN = "PRUVO <siparis@pruvo3d.com>";
const WHATSAPP = "905451386526"; // sipariş/WhatsApp linki bot numarasina gider (CLAUDE.md)
const SITE = "https://pruvo3d.com"; // urun kalici sayfalari: SITE/urun/<id>/

/** Kurusu "1.234,56 TL" bicimine cevirir (tamsayi aritmetigi; sunucu tarafiyla ayni mantik). */
function kurusTL(kurus) {
  const k = Math.max(0, Math.floor(Number(kurus) || 0));
  const tam = Math.floor(k / 100);
  const kur = String(k % 100).padStart(2, "0");
  // binlik ayirici
  const tamMetin = String(tam).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return tamMetin + "," + kur + " TL";
}

/** HTML kacisi — musteri adi/adresi/urun basligi gibi metinler govdeye guvenle girsin. */
function kac(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/**
 * Resend'e tek e-posta gonderir. @returns {{ok:boolean, hata?:string}}.
 * Anahtar YOKSA {ok:false, hata:"anahtar-yok"} (cagiran Telegram uyarir; istisna atmaz).
 */
export async function epostaGonder(env, kime, konu, govdeHtml) {
  if (!env.RESEND_API_KEY) { return { ok: false, hata: "anahtar-yok" }; }
  const taban = (env.RESEND_URL || "https://api.resend.com").replace(/\/$/, "");
  const c = await fetch(taban + "/emails", {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + env.RESEND_API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ from: GONDEREN, to: [kime], subject: konu, html: govdeHtml }),
  });
  if (c.status >= 200 && c.status < 300) { return { ok: true }; }
  // Anahtari ASLA log/hata metnine koyma: yalnizca HTTP kodu + Resend'in kisa hata mesaji.
  let mesaj = "";
  try { mesaj = ((await c.json()) || {}).message || ""; } catch (e) { /* JSON degil */ }
  return { ok: false, hata: "resend-" + c.status + (mesaj ? " " + mesaj.slice(0, 120) : "") };
}

// ---------------------------------------------------------------- sinif beyani

/** secenekler.js tek kaynagi. Yuklenemezse null — cagiran FAIL-CLOSED "ozel"e duser
 *  (bugunku metin), yani e-posta sablonu bir modul kazasinda beyan UYDURMAZ.
 *  Not: Worker index.js zaten ayni dosyayi import eder ve yoksa acilista PATLAR. */
function _sec() {
  const S = globalThis.PRUVO_SECENEK;
  return (S && typeof S.fizikselMi === "function") ? S : null;
}

/** Sepetin sinifi: "hazir" | "ozel" | "karma".
 *
 *  Sinif KARARI BURADA VERILMEZ — satirin `tur` alani (sepetiFiyatla'nin yazdigi POZITIF
 *  isaret) oldugu gibi secenekler.js sepetSinifi'ye verilir. Yerel bir `tur == "fiziksel"`
 *  karsilastirmasi YAZILMAZ: ikinci karar noktasi, para yoluyla beyan yolunun sessizce
 *  ayrismasi demektir. Bos sepet / modul kazasi -> "ozel" (bugunku metin, fail-closed). */
function sepetSinifi(satirlar) {
  const S = _sec();
  if (!S) { return "ozel"; }
  return S.sepetSinifi((satirlar || []).map((s) => (s || {}).tur));
}

// ---------------------------------------------------------------- sablonlar

/**
 * @param sinif  undefined -> kalem etiketi HIC basilmaz (kargo e-postasi + eski cagrilar
 *               BAYT-BAYT bugunku ciktisini korur). "ozel" -> yine basilmaz: 15.930 ozel
 *               uretim kaydinin siparis e-postasi degismez (regresyon butcesi).
 *               "hazir" / "karma" -> HER satir KENDI sinif etiketini tasir; karma sepet
 *               tek cumleye INDIRGENMEZ, musteri hangi kalemin hangi sinifta oldugunu
 *               kalemin kendi satirinda gorur.
 */
function satirTablosu(satirlar, sinif) {
  const S = _sec();
  const etiketBas = (sinif === "hazir" || sinif === "karma") && !!S;
  const govde = (satirlar || []).map((s) => {
    const sinifEtiketi = etiketBas
      ? "<br><small style='color:#6b7280'>" + kac(S.satirBeyani(s && s.tur)) + "</small>"
      : "";
    const detay = s.parametre_detay ? "<br><small>" + kac(s.parametre_detay) + "</small>" : "";
    const renk = s.renk_ozel || s.renk || "";
    const baslikMetin = kac(s.baslik);
    // Baslik urunun kalici sayfasina link (id varsa) — mail istemcisi resmi engellese de link
    // her zaman calisir (img'ye bagimli degil). id/baslik kac() ile kacisli (XSS yok).
    const baslikHtml = s.id
      ? "<a href='" + SITE + "/urun/" + kac(s.id) + "/' " +
        "style='color:#12294d;text-decoration:none'>" + baslikMetin + "</a>"
      : baslikMetin;
    // Kapak resmi VARSA kucuk thumbnail (gorseller[0]); YOKSA hic img basma (eski siparislerde
    // gorsel yok — zarifce link'le devam). src/alt kac() ile kacisli.
    const resim = s.gorsel
      ? "<img src='" + kac(s.gorsel) + "' width='56' alt='" + baslikMetin + "' " +
        "style='max-width:56px;border-radius:6px;vertical-align:middle;margin-right:8px'>"
      : "";
    return "<tr>" +
      "<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>" +
        resim + baslikHtml + detay + sinifEtiketi + "</td>" +
      // MALZEME / RENK hucresi = BEYAN. Karar bu dosyada VERILMEZ: shop/src/index.js
      // sepetiFiyatla fiziksel urunde (hazir ticari mal) bu alanlari BOS yazar; burasi yalniz
      // bos hali bicimlendirir — "ASA / " ya da " / turuncu" gibi yarim beyan basilmaz,
      // beyan hic yoksa "—" konur (bir boya kutusu icin dogru olan budur).
      "<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>" +
        ((s.malzeme && renk) ? kac(s.malzeme) + " / " + kac(renk)
                             : (kac(s.malzeme || renk) || "—")) + "</td>" +
      "<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:center'>" +
        kac(s.adet) + "</td>" +
      "<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right'>" +
        kurusTL(s.tutar_kurus) + "</td>" +
      "</tr>";
  }).join("");
  return "<table style='border-collapse:collapse;width:100%;font-size:14px'>" +
    "<thead><tr style='background:#12294d;color:#fff'>" +
    "<th style='padding:6px 8px;text-align:left'>Ürün</th>" +
    "<th style='padding:6px 8px;text-align:left'>Malzeme / Renk</th>" +
    "<th style='padding:6px 8px'>Adet</th>" +
    "<th style='padding:6px 8px;text-align:right'>Tutar</th>" +
    "</tr></thead><tbody>" + govde + "</tbody></table>";
}

function cerceve(baslikMetin, icerik) {
  return "<div style='font-family:Arial,Helvetica,sans-serif;color:#1f2937;max-width:640px;" +
    "margin:0 auto'>" +
    "<h2 style='color:#12294d;margin:0 0 4px'>PRUVO</h2>" +
    "<p style='color:#6b7280;margin:0 0 16px;font-size:13px'>Endüstriyel Parça Üretimi · Fethiye</p>" +
    "<h3 style='color:#12294d'>" + kac(baslikMetin) + "</h3>" +
    icerik +
    "<p style='margin-top:20px;font-size:13px;color:#6b7280'>Sorularınız için " +
    "<a href='https://wa.me/" + WHATSAPP + "' style='color:#12294d'>WhatsApp</a> üzerinden " +
    "bize ulaşabilirsiniz.</p>" +
    "</div>";
}

/**
 * Siparis onay e-postasi govdesi (tetik 1: odendi / havale-bekliyor).
 * @param dokum {tutarKurus, kargoKurus, kdvKurus, tahsilatKurus}
 */
export function onayEpostasiHtml(siparis, satirlar, dokum, havale, satici = false) {
  const dokumTablo = "<table style='margin-top:12px;font-size:14px'>" +
    "<tr><td style='padding:2px 12px 2px 0'>Ara toplam</td><td style='text-align:right'>" +
      kurusTL(dokum.tutarKurus) + "</td></tr>" +
    "<tr><td style='padding:2px 12px 2px 0'>Gönderim</td><td style='text-align:right'>" +
      (dokum.kargoKurus > 0 ? kurusTL(dokum.kargoKurus) : "Bedava") + "</td></tr>" +
    "<tr><td style='padding:2px 12px 2px 0'><b>Genel toplam</b></td>" +
      "<td style='text-align:right'><b>" + kurusTL(dokum.tahsilatKurus) + "</b></td></tr>" +
    "<tr><td style='padding:2px 12px 2px 0;color:#6b7280'>KDV (%20 dahil)</td>" +
      "<td style='text-align:right;color:#6b7280'>" + kurusTL(dokum.kdvKurus) + "</td></tr>" +
    "</table>";
  // 🔴 SINIF BEYANI: metin sepetin sinifina gore secilir. TEK KAYNAK secenekler.js BEYAN;
  // "ozel" kolu bugunku iki cumleyi AYNEN verir -> 15.930 ozel uretim kaydinda regresyon 0.
  // Cerceve/renk kutusu DEGISMEZ, yalnizca cumle sinifa gore gelir.
  const S = _sec();
  const sinif = sepetSinifi(satirlar);
  const durumMetni = S ? S.epostaDurumBeyani(sinif, !!havale)
                       : (havale ? "Siparişiniz alındı. Havale/EFT ödemeniz hesabımıza "
                                   + "geçtiğinde üretime başlanır."
                                 : "Ödemeniz alındı, siparişiniz onaylandı. Ürünleriniz "
                                   + "özel olarak üretilip gönderilecektir.");
  const durumNot = havale
    ? "<p style='background:#fef9c3;padding:10px;border-radius:6px'>" + kac(durumMetni) + "</p>"
    : "<p style='background:#dcfce7;padding:10px;border-radius:6px'>" + kac(durumMetni) + "</p>";
  // Cayma hatirlatmasi: OZEL sepette BOS doner (sozlesmenin hukmu degismiyor, bugunku
  // e-posta bayt-bayt korunuyor). HAZIR/KARMA sepette 14 gunluk hak yazili hale gelir.
  // ⚠️ Iade kargo bedelinin kime ait oldugu Okan'a soruldu, cevap BEKLENIYOR -> o cumle
  //    BURAYA YAZILMAZ; yeri secenekler.js BEYAN.IADE_KARGO_YER'dir ve BOS durur.
  const caymaMetni = S ? S.caymaBeyani(sinif) : "";
  const caymaNot = caymaMetni
    ? "<p style='font-size:13px;color:#374151;margin:8px 0'>" + kac(caymaMetni) + "</p>"
    : "";
  const musteriNotu = satici && siparis.musteri_notu
    ? "<p style='margin-top:12px;font-size:14px;white-space:pre-wrap'><b>Müşteri notu:</b><br>" +
      kac(siparis.musteri_notu) + "</p>"
    : "";
  const icerik =
    "<p>Sipariş numaranız: <b>" + kac(siparis.siparis_no) + "</b></p>" +
    durumNot +
    caymaNot +
    satirTablosu(satirlar, sinif) +
    dokumTablo +
    musteriNotu +
    "<p style='margin-top:12px;font-size:14px'><b>Teslimat adresi:</b><br>" +
    kac(siparis.musteri_ad) + "<br>" + kac(siparis.musteri_adres) + "</p>";
  return cerceve("Sipariş Onayı", icerik);
}

/** Kargo e-postasi govdesi (tetik 2: /yonet/kargo). */
export function kargoEpostasiHtml(siparis, satirlar, firma, kod) {
  const icerik =
    "<p>Sipariş numaranız: <b>" + kac(siparis.siparis_no) + "</b></p>" +
    "<p style='background:#dbeafe;padding:10px;border-radius:6px'>Siparişiniz kargoya verildi.</p>" +
    "<table style='margin:12px 0;font-size:15px'>" +
    "<tr><td style='padding:4px 16px 4px 0'>Kargo firması</td><td><b>" + kac(firma) + "</b></td></tr>" +
    "<tr><td style='padding:4px 16px 4px 0'>Takip kodu</td><td><b>" + kac(kod) + "</b></td></tr>" +
    "</table>" +
    satirTablosu(satirlar);
  return cerceve("Siparişiniz Kargoda", icerik);
}

/**
 * Bir siparis olayinin TUM e-postalarini (musteri + satici kopyasi) gonderir; anahtar yoksa
 * veya gonderim patlarsa Telegram'a uyarir, ASLA istisna sizdirmaz (cagiran ctx.waitUntil'a
 * sarar). @param olaylar [{kime, konu, html, etiket}]
 */
export async function epostaAkisi(env, telegram, siparisNo, olaylar) {
  try {
    if (!env.RESEND_API_KEY) {
      await telegram(env, "⚠️ PRUVO e-posta gönderilemedi (anahtar yok) — " + siparisNo +
        " (RESEND_API_KEY tanımlı değil; sipariş akışı etkilenmedi)");
      return;
    }
    for (const o of olaylar) {
      const r = await epostaGonder(env, o.kime, o.konu, o.html);
      if (!r.ok) {
        await telegram(env, "⚠️ PRUVO e-posta hatası — " + siparisNo + " (" +
          (o.etiket || o.kime) + "): " + r.hata);
      }
    }
  } catch (e) {
    await telegram(env, "⚠️ PRUVO e-posta istisnası — " + siparisNo +
      " (sipariş akışı etkilenmedi)");
  }
}
