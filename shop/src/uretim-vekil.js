/**
 * URETIM SAGLAYICI VEKIL UCU (Okan 20 Eki 2026: "anahtar isini tekine devret" -> pencere
 * secimi "KraL araci kursun"). Saglayici anahtari (`URETIM_API_ANAHTAR`) YALNIZ bu Worker'in
 * secret'idir; CF geri okutmaz, makinede duz kopyasi yoktur. TeKiN'in tek seferlik uretim
 * isleri anahtari GORMEDEN saglayiciya bu uctan gider.
 *
 *   GET  /api/shop/ic/uretim-vekil/balance
 *   GET  /api/shop/ic/uretim-vekil/retexture/<gorev>
 *   POST /api/shop/ic/uretim-vekil/multi-color   {model_url, max_colors, siparis_no?}
 *   GET  /api/shop/ic/uretim-vekil/multi-color/<gorev>
 *
 * YETKI: `X-Vekil-Jeton` == env.URETIM_VEKIL_JETON (sabit zamanli kiyas). Secret YOKSA ya da
 * jeton yanlissa cevap genel 404 (`bulunamadi`) — ucun varligi sizdirilmaz, fail-closed.
 * IZIN KUMESI yalniz bu 4 islem; baska her yol 404. POST govdesi yeniden KURULUR (istemcinin
 * fazladan alanlari saglayiciya GITMEZ): model_url yalniz https + saglayicinin KOK alan adi
 * (env.URETIM_API_TABAN host'unun son iki etiketi; taban yoksa her adres RED — saglayici adi
 * kaynakta GECMEZ, repo public),
 * max_colors 1..8 tamsayi, printer_brand sabit "bambu". Gunluk tavan GUNLUK_POST_TAVANI
 * (kredi harcayan tek islem); her basarili POST `foto_kredi` defterine `adim='vekil-renk'`
 * olarak yazilir (panel aylik kredi toplamina girer, harcama gorunur kalir).
 * Cevap saglayicinin {kod, govde}'si; anahtar HICBIR cevapta yer almaz.
 */
import { saglayici, gorevKimligi } from "./foto.js";
import { sabitEsit } from "./yonet.js";

export const VEKIL_ONEK = "/ic/uretim-vekil/";
export const GUNLUK_POST_TAVANI = 1;
export const VEKIL_RENK_MAX = 8;
export const VEKIL_KREDI_TAHMINI = 10;
const GOREV_KALIBI = /^[A-Za-z0-9-]{8,80}$/;
const SIPARIS_KALIBI = /^PR-\d{6}-\d{6}-[A-Z0-9]{3}$/;

function yanit(govde, durum) {
  return new Response(JSON.stringify(govde), {
    status: durum,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

const BULUNAMADI = () => yanit({ hata: "bulunamadi" }, 404);

export function vekilYetkiliMi(request, env) {
  const beklenen = env && typeof env.URETIM_VEKIL_JETON === "string" ? env.URETIM_VEKIL_JETON : "";
  if (beklenen.length < 32) { return false; }
  return sabitEsit(request.headers.get("X-Vekil-Jeton") || "", beklenen);
}

export function saglayiciKokAlani(env) {
  let u;
  try { u = new URL(String((env && env.URETIM_API_TABAN) || "")); } catch (e) { return ""; }
  const etiket = u.hostname.toLowerCase().split(".").filter(Boolean);
  return etiket.length >= 2 ? etiket.slice(-2).join(".") : "";
}

export function modelAdresiGecerliMi(adres, env) {
  const kok = saglayiciKokAlani(env);
  if (!kok) { return false; }
  let u;
  try { u = new URL(String(adres || "")); } catch (e) { return false; }
  if (u.protocol !== "https:") { return false; }
  const h = u.hostname.toLowerCase();
  return h === kok || h.endsWith("." + kok);
}

async function bugunPostSayisi(env, simdi) {
  const gun = new Date(simdi).toISOString().slice(0, 10);
  const r = await env.KATALOG.prepare(
    "SELECT COUNT(*) AS n FROM foto_kredi WHERE adim = 'vekil-renk' AND substr(tarih, 1, 10) = ?"
  ).bind(gun).first();
  return Number(r && r.n) || 0;
}

function sonuc(c) {
  // Ag hatasi {kod:0} -> 502; saglayicinin kendi kodu aynen yansitilir.
  return yanit({ kod: c.kod, govde: c.govde }, c.kod > 0 ? c.kod : 502);
}

export async function uretimVekil(request, env, yol, simdi) {
  if (!vekilYetkiliMi(request, env)) { return BULUNAMADI(); }
  const alt = yol.slice(VEKIL_ONEK.length);
  const parca = alt.split("/");
  const yontem = request.method;

  if (yontem === "GET" && alt === "balance") {
    return sonuc(await saglayici(env, "GET", "/v1/balance", null));
  }
  if (yontem === "GET" && parca.length === 2 && parca[0] === "retexture") {
    if (!GOREV_KALIBI.test(parca[1])) { return yanit({ hata: "gorev-gecersiz" }, 400); }
    return sonuc(await saglayici(env, "GET", "/v1/retexture/" + parca[1], null));
  }
  if (yontem === "GET" && parca.length === 2 && parca[0] === "multi-color") {
    if (!GOREV_KALIBI.test(parca[1])) { return yanit({ hata: "gorev-gecersiz" }, 400); }
    return sonuc(await saglayici(env, "GET", "/v1/print/multi-color/" + parca[1], null));
  }
  if (yontem === "POST" && alt === "multi-color") {
    let g = null;
    try { g = await request.json(); } catch (e) { g = null; }
    if (!g || typeof g !== "object") { return yanit({ hata: "govde-gecersiz" }, 400); }
    if (!modelAdresiGecerliMi(g.model_url, env)) { return yanit({ hata: "model-adresi-gecersiz" }, 400); }
    const n = g.max_colors;
    if (!(Number.isInteger(n) && n >= 1 && n <= VEKIL_RENK_MAX)) {
      return yanit({ hata: "renk-sayisi-gecersiz" }, 400);
    }
    const siparisNo = typeof g.siparis_no === "string" && SIPARIS_KALIBI.test(g.siparis_no) ? g.siparis_no : "";
    if (await bugunPostSayisi(env, simdi) >= GUNLUK_POST_TAVANI) {
      return yanit({ hata: "gunluk-tavan" }, 429);
    }
    const c = await saglayici(env, "POST", "/v1/print/multi-color",
                              { model_url: String(g.model_url), max_colors: n, printer_brand: "bambu" });
    const gorev = gorevKimligi(c.govde);
    if (c.kod >= 200 && c.kod < 300 && gorev) {
      await env.KATALOG.prepare(
        "INSERT OR IGNORE INTO foto_kredi (tarih, adim, is_no, siparis_no, gorev, kredi)" +
        " VALUES (?, 'vekil-renk', 'vekil', ?, ?, ?)"
      ).bind(new Date(simdi).toISOString(), siparisNo, gorev, VEKIL_KREDI_TAHMINI).run();
    }
    return sonuc(c);
  }
  return BULUNAMADI();
}
