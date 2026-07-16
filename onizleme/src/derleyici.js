/**
 * DERLEYICI adaptoru — Worker'in derleme arka ucuyla tek konusma noktasi.
 *
 * Arka uc SOYUT: index.js yalnizca bu fonksiyonu cagirir. Bugun iki yol var,
 * Cloudflare Container'a gecis TEK BU DOSYADA degisiklik gerektirir:
 *
 *  1) env.DERLEYICI  (service/container binding, fetch'lenebilir): uretim hedefi.
 *     Cloudflare Containers baglandiginda binding'in stub'i buraya gelir
 *     (gerekirse getContainer(env.DERLEYICI).fetch sarmalayicisi da buraya yazilir).
 *  2) env.DERLEYICI_URL (duz HTTP adresi): yerel gelistirme/kabul testleri —
 *     onizleme/derleyici/server.py (mock veya gercek openscad) ile konusur.
 *
 * HTTP sozlesmesi (server.py ile birebir):
 *   POST {url}/derle {"aile","parametreler"} -> 200 binary STL | 4xx/5xx JSON {hata}
 */

/* Istek butcesi 60 sn: DERLEME'nin kendisi server.py icinde 5 sn ile sinirli
   (subprocess timeout); kalan pay Container SOGUK BASLATMASINI (imaj cekme + boot,
   kapi-1 olcumu) emmek icin — DO sarmali ~55 sn dener, adaptor 60 sn'de keser.
   Sicak istekte fiilen derleme suresi kadar surer. */
export const ISTEK_ZAMAN_ASIMI_MS = 60000;

/** @returns {{kod:number, govde:ArrayBuffer}|{kod:number, hata:string}} */
export async function derleyiciCagir(env, aile, parametreler) {
  const istek = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aile: aile, parametreler: parametreler }),
    signal: AbortSignal.timeout(ISTEK_ZAMAN_ASIMI_MS),
  };
  let cevap;
  try {
    if (env.DERLEYICI && typeof env.DERLEYICI.idFromName === "function") {
      // Cloudflare Container (Durable Object sarmali, index.js OnizlemeDerleyici).
      // Tek isimli instance = pilot icin tek konteyner; olceklerken isim anahtari
      // (or. aile ya da rastgele N'den biri) burada cesitlendirilir.
      const stub = env.DERLEYICI.get(env.DERLEYICI.idFromName("derleyici"));
      cevap = await stub.fetch("http://derleyici/derle", istek);
    } else if (env.DERLEYICI && typeof env.DERLEYICI.fetch === "function") {
      cevap = await env.DERLEYICI.fetch("http://derleyici/derle", istek);
    } else if (env.DERLEYICI_URL) {
      cevap = await fetch(env.DERLEYICI_URL.replace(/\/$/, "") + "/derle", istek);
    } else {
      return { kod: 503, hata: "derleyici-yok" };
    }
  } catch (e) {
    // AbortSignal timeout dahil: derleme sunucusuna ulasilamadi/zaman asti.
    const zamanAsimi = e && (e.name === "TimeoutError" || e.name === "AbortError");
    return { kod: zamanAsimi ? 504 : 502,
             hata: zamanAsimi ? "derleme-zaman-asimi" : "derleyici-ulasilamiyor" };
  }
  if (cevap.status !== 200) {
    let hata = "derleme-hatasi";
    try { hata = (await cevap.json()).hata || hata; } catch (e) { /* JSON degilse jenerik */ }
    // 4xx istemci kombinasyon hatasi aynen tasinir (422 gecersiz-geometri gibi);
    // 5xx derleyici ic hatasi 502'ye katlanir (arka ucun ic kodlari sizmasin).
    return { kod: cevap.status < 500 ? cevap.status : 502, hata: hata };
  }
  return { kod: 200, govde: await cevap.arrayBuffer() };
}
