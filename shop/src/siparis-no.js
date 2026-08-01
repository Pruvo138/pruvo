/**
 * pruvo-shop — SIPARIS NUMARASI URETIMI (TEK KAYNAK).
 *
 * NEDEN AYRI DOSYA (1 Agu 2026, WhatsApp siparis ucu): numara ureteci 16 Tem'den beri
 * index.js'in ICINDE yasiyordu. WhatsApp kanali (yonet.js /wa-siparis) de AYNI aileden
 * numara uretmek zorunda — orada ikinci bir kopya acilsaydi iki uretec zamanla AYRISIR
 * (sonek alfabesi, saat dilimi, uzunluk) ve panelde iki farkli ID semasi olusurdu.
 * index.js <-> yonet.js dogrudan import'u DAIRESEL olurdu (index.js zaten yonet.js'i
 * import ediyor) -> ortak modul.
 *
 * DAVRANIS DEGISMEDI: fonksiyon govdeleri index.js'ten BIREBIR tasindi (Europe/Istanbul,
 * h23, 2 haneli parcalar, 0/O ve 1/I disi 32 harflik sonek alfabesi, 3 karakter sonek,
 * 5 denemelik D1 carpisma on-kontrolu). Bicim: PR-yyMMdd-HHmmss-XXX.
 */

/** Siparis numarasi (kalem 5): Ege/Sheet akisiyla AYNI aile — PR-yyMMdd-HHmmss
 *  (Europe/Istanbul saati) + ayni-saniye carpismasina karsi kisa rastgele sonek.
 *  Musteriye gorunur (donus sayfasi, havale ekrani, Telegram); iyzico
 *  conversationId/basketId ile eslesir. */
export function siparisNoUret() {
  const p = {};
  new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Istanbul", hourCycle: "h23",
    year: "2-digit", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).formatToParts(new Date()).forEach((x) => { p[x.type] = x.value; });
  // 0/O ve 1/I alfabede yok: numara telefonda/dekont aciklamasinda yanlis okunmasin.
  const ABC = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let sonek = "";
  for (let i = 0; i < 3; i++) { sonek += ABC[Math.floor(Math.random() * ABC.length)]; }
  return "PR-" + p.year + p.month + p.day + "-" + p.hour + p.minute + p.second + "-" + sonek;
}

/** Benzersiz numara: rastgele sonek carpismayi zaten kilar; yine de INSERT oncesi D1
 *  on-kontrolu yapilir (kart akisinda numara once iyzico'ya conversationId olarak gider —
 *  INSERT'te UNIQUE patlasa numara degistirilemezdi). UNIQUE kisiti son savunma olarak durur. */
export async function yeniSiparisNo(env) {
  for (let i = 0; i < 5; i++) {
    const no = siparisNoUret();
    const varMi = await env.KATALOG.prepare(
      "SELECT 1 AS v FROM siparisler WHERE siparis_no = ?").bind(no).first();
    if (!varMi) { return no; }
  }
  throw new Error("siparis numarasi uretilemedi (ust uste carpisma)");
}
