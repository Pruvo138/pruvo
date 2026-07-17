# MÜHENDİS PAKETİ — Sipariş Yönetimi + E-posta (mimar spec, 2026-07-17 akşam)

Okan kararları: (1) yönetim = sitenin KENDİ mini yönetim sayfası (Sheet/Notion REDDEDİLDİ —
ikinci kaynak/senkron yok, tek doğru kaynak D1); (2) e-posta = Resend (hesabı Okan açacak;
RESEND_API_KEY canlıya Okan `wrangler secret put` ile girer — koda/dosyaya anahtar YAZILMAZ).

## Kapsam (tek dal, iki faz — ikisi de bu pakette)

### Faz 1 — Yönetim sayfası + uçlar (shop worker'a eklenir)
- `GET /api/shop/yonet` → tek dosyalık yönetim SAYFASI (inline HTML/CSS/JS, harici kütüphane
  YOK). Erişim: `?anahtar=<YONET_ANAHTAR>` query'si YA DA `X-Yonet-Anahtar` başlığı;
  `YONET_ANAHTAR` wrangler secret (yoksa uç 404 davransın — varlığı sızmasın). Sayfa mobil
  uyumlu (Okan telefondan kullanacak), lacivert/gri site diline uygun, süs yok.
- `GET /api/shop/yonet/liste?durum=...` → JSON sipariş listesi (D1'den; varsayılan son 50).
- `POST /api/shop/yonet/durum` → { siparis_no, durum } — izinli geçişler:
  odendi→uretimde→kargolandi→tamamlandi; havale-bekliyor→odendi (havale onayı — mevcut
  onay komutu neyse onunla ÇELİŞME, keşfet ve tek yola indir); her durum→iptal.
  Bilinmeyen durum/geçiş REDDEDİLİR. D1'e `durum_gecmisi` eklemek İSTEĞE BAĞLI değil:
  siparisler tablosuna `kargo_kodu TEXT NOT NULL DEFAULT ''` ve `kargo_firma TEXT NOT NULL
  DEFAULT ''` kolonları d1-sema.sql'e eklenir + tools/d1-sync.py GOC_KOLON_SIPARIS listesine
  işlenir + CANLIYA `--sema` koşulur (bugünkü 500 dersi: şema değişikliği canlı göçsüz
  YAYINLANMAZ — merge sırasına yaz).
- `POST /api/shop/yonet/kargo` → { siparis_no, kargo_firma, kargo_kodu } — durum
  'kargolandi'ya çeker + müşteriye kargo e-postası tetikler (Faz 2).
- STL İNDİRME:
  - Sarı (parametrik) satır: sipariş kaydındaki `parametreler` ile mevcut önizleme
    derleyicisinden STL üret (uç/akışı KEŞFET: onizleme worker'ının derleme yolu —
    yönetim sayfasında "STL indir" düğmesi buna gider; anahtar korumalı taraftan çağır,
    müşteri tarafı kotalarını yeme). İndirilen dosya adı: `<siparis_no>-<urun-id>.stl`.
  - Normal satır (OKAN GÜNCELLEMESİ 17 Tem akşam — HER üründe indirme linki istenir):
    üretim dosyaları ÖZEL R2 kovasına konur (public pruvo-media DEĞİL — ticari dosya
    sızmaz; mevcut ÖZEL kova pruvo-ozel, prefix `stl/<urun-id>.stl` ya da `.3mf`).
    Shop worker'a bu kovanın R2 BINDING'i eklenir (wrangler.toml, salt-okuma yeterli);
    `GET /api/shop/yonet/stl?id=<urun-id>` (yönetim anahtarlı) R2 nesnesini stream eder
    (Content-Disposition: `<siparis_no>-<urun-id>.stl|.3mf`; iki uzantıyı da dene).
    Dosya R2'de YOKSA sayfada açık not: "dosya R2 stl/ prefix'inde yok — stl/ klasörü /
    Drive / gizli kaynak kaydına bak (id: <urun-id>)". Gizli kaynak bilgisi (tedarikçi/
    link) sayfaya YAZILMAZ.
  - Toplu yükleme aracı: `tools/stl-r2-yukle.py` — yerel `stl/` klasöründeki dosyaları
    (`<urun-id>.stl|.3mf` adlandırması; farklı adlananları raporla, tahmin etme) özel
    kovanın `stl/` prefix'ine yükler (yerel wrangler oturumu `npx wrangler r2 object put`
    ile; idempotent — varsa ve boyut aynıysa atla). Kapsam gerçeği: her ürünün dosyası
    diskte yok (bazı ******** ürünleri sipariş anında kaynaktan indirilir) — araç sonunda
    "yüklendi/atlandı/eksik" sayımı basar, eksikler yönetim sayfasındaki nota düşer.
- GÜVENLİK ÇİZGİLERİ: yönetim uçları rate-limit'siz ama anahtarsız istekte 404; anahtar
  loglara/HATA metinlerine yazılmaz; PII (müşteri ad/tel/adres) sadece anahtarlı yanıtta;
  CORS'ta yönetim uçları site origin'ine AÇILMAZ (same-origin kullanım). Kart verisi zaten yok.

### Faz 2 — E-posta (Resend)
- Worker'a `epostaGonder(env, kime, konu, govdeHtml)` — `https://api.resend.com/emails`,
  `Authorization: Bearer env.RESEND_API_KEY`. Gönderen: `PRUVO <siparis@pruvo3d.com>`.
  `env.RESEND_API_KEY` YOKSA e-posta adımı SESSİZCE ATLANMAZ — Telegram'a "e-posta
  gönderilemedi (anahtar yok)" düşer, sipariş akışı BOZULMAZ (e-posta hatası ödemeyi asla
  düşürmez: try/catch + Telegram uyarı).
- Tetikler:
  1. Sipariş 'odendi' (kart callback) ve 'havale-bekliyor' (havale başlatma): müşteriye
     onay e-postası (sipariş no, satırlar + parametre detayı, tutar/kargo/KDV dökümü,
     teslimat adresi, "sorunuz için WhatsApp" linki) + `env.BILDIRIM_EPOSTA`'ya (vars,
     wrangler.toml: info@pruvo3d.com) satıcı kopyası.
  2. Kargo ucu çağrılınca: müşteriye "siparişiniz kargoda" (firma + takip kodu).
- Şablonlar Türkçe, sade HTML (tablo döküm); pazarlama dili yok; "3D baskı" DEME
  (CLAUDE.md kuralı — "özel üretim" de).

## Kabul (önce-KIRMIZI şart; mevcut düzenek: shop/test/kabul.js mock desenleri)
1. Yönetim yetkisi: anahtarsız/yanlış anahtar → 404; doğru anahtar → liste JSON (test
   fixture siparişleriyle). ÖNCE KIRMIZI: uçlar yokken 404'e karşı yeni beklentiler kırmızı.
2. Durum makinesi: izinli geçişler yeşil; izinsiz (ör. tamamlandi→odendi) 400.
3. Kargo ucu: D1'de kargo_kodu/kargo_firma + durum 'kargolandi' + MOCK Resend'e istek
   (kime=müşteri, gövdede takip kodu) — Resend mock'u kabul.js'in mock-iyzico deseniyle
   (env RESEND_URL override).
4. E-posta tetiği: mock callback 'odendi' akışında 2 e-posta (müşteri + BILDIRIM_EPOSTA);
   RESEND_API_KEY yokken sipariş yine 'odendi' + Telegram'a uyarı düştü (sessiz atlama YOK).
5. Regresyon: shop kabul TÜMÜ + sepet-panel + parite. Sır taraması (test 6) yeni uçların
   anahtar sızdırmadığını da kapsasın (YONET_ANAHTAR deseni).
6. Tarayıcı kanıtı: yerel wrangler dev'de yönetim sayfası — liste + durum değiştirme +
   kargo formu ekran görüntüleri.
7. STL indirme: yönetim STL ucu — sarı satırda derleyici çıktısı; normal satırda sahte/
   yerel R2 nesnesiyle (wrangler dev --local R2 taklidi) indirme + Content-Disposition
   adı; R2'de olmayan id'de "yok" notu. ÖNCE KIRMIZI: uç yokken beklentiler kırmızı.
   stl-r2-yukle.py: sahte küçük dosyalarla yükle/atla/eksik sayımı testi (canlı R2'ye
   toplu yükleme MERGE SONRASI mimar/maraba koşumu — testte canlıya yükleme YAPMA).

## Merge sırası (mimar koşar)
1. merge → 2. d1-sync.py --sema CANLIYA (yeni kolonlar) → 3. worker deploy → 4. push →
5. Okan: Resend hesabı + DNS + `wrangler secret put RESEND_API_KEY` + `YONET_ANAHTAR`
   (openssl rand -hex 24) → 6. canlı duman: yönetim sayfası + test e-postası.
