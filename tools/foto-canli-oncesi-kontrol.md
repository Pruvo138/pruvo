# Fotoğraftan özel üretim — CANLI AÇILIŞ ÖNCESİ KONTROL LİSTESİ (tek dosya)

Ne zaman: Okan "aç" dediğinde, panelden tür açmadan ÖNCE. Bu liste bugün SORULMAZ; açılış
günü sırayla koşulur. Her satır bir komut + beklenen çıktıdır; çıktı yazılmadan satır kapanmaz.
Sahibi: KraL (mimar). Para/şifre kalemleri (Okan kapısı) ayrıca işaretlidir.

Bugünkü hal (8 Eki 2026): canlı D1'de `foto_acik` tablosu var ve **0 satır** — tüm türler
KAPALI (fail-closed). Kod `kral/kopru-15` ile main'de. Önizleme ortamı ayrı (ayrı D1 + kova).

## 1. Üretim koşucusu — Mac uyursa sipariş bekler
Sipariş akışında 3MF onarım kuyruğu (`onarim-bekliyor`) ve üreteç işleri Mac'teki launchd
koşucusuyla ilerler. Mac uyursa sipariş o aşamada bekler; Worker cron'u 6 saati geçen
`onarim-bekliyor` satırını bildirir (NB1–NB3).
- [ ] Koşucu kurulu mu: `python3 tools/foto-kosucu-kur.py --kuru` → plist basılır; `launchctl list | grep foto` → 1 satır.
- [ ] Hüküm (tek seçim, açılıştan önce): (a) sunucuda koşucu, ya da (b) Mac'te uyku yasağı
      (`pmset -g` → `sleep 0`) + Worker nöbeti. Seçim deftere yazılır.
- [ ] Nöbet canlı: Worker cron'u son 24 saatte koştu (`npx wrangler tail` ya da cron log satırı).

## 2. Bot koruması (Turnstile) — ŞİFRE: Okan kapısı
Turnstile sırrı önizleme turunda bir işçi transkriptine basıldı → canlıdan önce DÖNDÜRÜLÜR.
- [ ] Okan Cloudflare panelinden yeni Turnstile sırrını üretir (şifre = Okan).
- [ ] `python3 tools/turnstile-secret-yukle.py` ile shop worker'a `secret put` (repoya GİRMEZ).
- [ ] Kabul: `/baslat` jetonsuz → RED; geçerli jetonla → 200 (shop testleri `node shop/test/*.mjs` yeşil).

## 3. Yönetim anahtarı döndürme — ŞİFRE: Okan kapısı
- [ ] `YONET_ANAHTAR` yeni değerle `npx wrangler secret put YONET_ANAHTAR` (`shop/` dizininden, hesap kimliğiyle).
- [ ] Önizleme makine anahtarı (`ONIZLEME_MAKINE_ANAHTARI`) yalnız önizlemede; canlı worker'da
      TANIMSIZ olmalı: `npx wrangler secret list` çıktısında YOK.
- [ ] Kabul: eski anahtarla `/yonet/foto-ozet` → 404; yenisiyle → 200.

## 4. Taze zincir kabulü — o gün, o kodla
- [ ] Önizlemede uçtan uca: `python3 tools/foto-ornek-uc-uca.py --hepsi --kol D --kredi-tavani <N>`
      → açılacak her tür için ①–⑥ HAZIR (kredi harcaması ≤ N).
- [ ] Canlı D1 şeması: `foto_acik` tablosu + `foto_isler.uretim_notu/onay_tarih/onay_surum`
      + `foto_uretim.onay_tarih/onay_surum` var (`PRAGMA table_info`).
- [ ] Ek renk göçü (8 Eki): `tools/d1-goc/2026-10-08-foto-renk.sql` shop worker deploy'undan ÖNCE canlı D1'e
      uygulandı → `PRAGMA table_info(foto_uretim)` içinde `renk_sayisi` (INTEGER, varsayılan 0) + `renkler`
      (TEXT, varsayılan '') VAR. Yoksa ödenen sipariş üretim kuyruğuna YAZILAMAZ (fail-closed 500).
- [ ] Canlı shop worker sürümü = main'deki `shop/` (ödeme nabzı şeridi son push'ta `success`).

## 5. O günün kredi tavanı — PARA: Okan kapısı
Tavanlar KODDA sabittir (panel ayarı değil): `shop/src/foto.js` `GUNLUK_ONIZLEME_TAVANI` (tüm
ziyaretçiler, 24 sa önizleme) · `HAVUZ_ESIK_KREDI` / `URETIM_PAYI_KREDI` (bakiye eşiği → bölüm kapanır).
- [ ] Okan o günün tavanını tek sayı olarak verir; farklıysa sabit değişir → shop testleri → deploy.
- [ ] Kabul: tavan aşımında yeni önizleme 503 (fail-closed), ödenmiş siparişler etkilenmez.

## 6. Açılış
- [ ] Panelden tür tür "Aç" (yönetim panelindeki açma düğmesi) → `foto_acik` satırı `acik=1`.
- [ ] Canlı `GET /api/shop/foto/acik` → yalnız açılan türler; 375 px ekranda bölüm çiziliyor, konsol hatası 0.
- [ ] Kapatma yolu denendi: "Kapat" → bölüm "şu an sipariş alınamıyor" der.
