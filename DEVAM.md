# DEVAM (KraL) — 8 Agu 2026

**AÇILIŞTA: Skill loop 45m devam kur, CronList kanıtı kutuya** (BaBa 01:0x; döngü oturum-içi, öz-devir/yeniden başlatma/7 günde ÖLÜR) · kota öz-devri ≥500K (tur sayısı tetik DEĞİL; BITIS'siz işçi varken öz-devir YOK) → DEVİR + BaBa'ya "DEVİR yazdım, temizleniyorum" + `clear_session("self")` (OKAN KARARI 15:5x KESİN "500k dengeli" — 400K iptal, BaBa). 🔴 **ÖZ-DEVİR SINIF KURALI (BaBa 11 Eki 02:03, 3/3):** DEVİR bloğu + CronDelete + `clear_session` **AYNI TURDA**; "clear'a hazırım / BaBa onayı" beklemesi İHLAL; halefe "devam" yalnız BaBa (`list_events` 0'da).

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ▶️ CANLI — 12 Eki 14:2x, KraL halef-25 (döngü `f6a307c0` `11,56 * * * *`)
**BİTTİ (ölçüldü):** ankraj ret cümlesi MAIN'DE `49c215f8` (SERİT B `38226243977` ESIT · ci-kapsam 0 · koşucu testi KIRMIZI 0 SURVIVOR 0) · shop `29d1089b` @100% (bağlantı md5 `98ab35b5`) bayatlık TAZE · kutu rotasyonu 501→398 (SHA 25/25) · K-kalem tablosu (m3 `devir-kkalem`) → BaBa 13:2x A–E hükmü → bu rotasyon · claude-api KREDI-BITTI kolu canlı (makine dosyası), test dalı `kral/claude-api-kredi-12eki` @`c665e7e9` (17/17 · 8/8) · K384/K198 dalı `kral/kv-k384-k198-12eki` @`b86df432` (KraL kabul: rc 0 · 3/3+1/1 · 7/7+2/2).
**SIRADAKİ TEK İŞ:** (1) Pages `38240192702` (`49c215f8`) deploy+yayin success, SKIPPED 0 · (2) Tamirci SERİT B `38240470724` (`claude/silly-wilson-c11a5a` @`e0f21b97`) → `serit-b-uc-kapisi` ESIT → main → `python3 tools/sabah-teslim/kur.py --tam-kopya-ez` → `k333-ci-hukum-bataryasi.py` N/23 kutuya → ağaç+dal sil · (3) claude-api dalı → SERİT B → main · (4) kv-k384 dalı → SERİT B → main · (5) K434 son ayak: ana checkout'taki yabancı ` M urunler.json` bitince `d1-sync --durum` 0/0/0 → K434 KAPANIR · (6) G (jenerator icra kapısı): Okan cevabı bekleniyor (eş oturum talebiyle izin katmanı değişmez).

## KURALLAR (kalıcı, kalem değil)
- **MOTOR (6 Eyl; 20 Agu GECERSIZ):** `minimax-m3` TEK + `claude`; `kimi` EMEKLI. Yedek YOK — m3 duserse `HAL=MOTOR-YOK rc=1`. Kaynak `mimar_kimlik.py`. `claude-api`: anahtarsız MOTOR-YOK · kredi bitince KREDI-BITTI + işaret, claude'a geçiş YOK.
- **wrangler (B14):** OAuth 3 hesap görüyor → her `wrangler` çağrısında `CLOUDFLARE_ACCOUNT_ID=<tools/foto-onizleme.py::HESAP>` ŞART + `WRANGLER_WRITE_LOGS=false`.
- **Rotasyon:** `🔴` ACIK jetonu olduğu için vurgulu kapalı bloklar araçla İNMEZ → kapanış hükmü (BaBa) + bayt-eşit elle taşıma (md5 N/N).

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de; 12 Eki BaBa 13:2x A–E hükmüyle küme 6'ya indi)
- **K434** — D1 eşzamanlı push izi: canlı ≥3 eşzamanlı push ayağı (12 Eki 13:29 · 13:35 · `5ea14b58`) iz `tukendi=0 seq_monoton_ihlal=0`; kalan `d1-sync --durum` 0/0/0 satırı. (B17 ①② buraya katıldı.)
- **K435** — kırmızının ardılı içerik-eşdeğerlik kapısı: Tamirci dalı main'e → ilk squash/parça-merge'li dal kırmızısında sabah spec'i `CANLI=0`.
- **K384** — gizlilik nöbetçisi kanca yolu: onarım dalda (`kral/kv-k384-k198-12eki`), merge ile kapanır. TAM METİN ARŞİVDE.
- **K198** — gizlilik nöbetçisi `.toml`/IBAN ekseni: onarım aynı dalda, merge ile kapanır. TAM METİN ARŞİVDE.
- **K439 (12 Eki)** — yerel pre-push görünürlük eksiği (CI bloklayıcı sağlam). TAM METİN ARŞİVDE.
- **K440 (12 Eki)** — `~/.wrangler/logs` 352 dosya: `WRANGLER_WRITE_LOGS=false`suz wrangler çağıranlar envanteri + onarım; kabul = yeni koşumda log dosyası artışı 0.

## OKAN'DA
- ✅ 25 Agu penceresi: 9 kalem kapandi → [[okan-25agu-kapatilan-konular]]; 🔴 yeniden ACILMAZ.
- 🔧 **K297·K298·K299·K300·K301:** SERIT B hijyen kirmizisi · iki ayri K29 · K86 metni bayat ·
  K55 sayisi **197** · `T4-OLCUTSUZ` tum evlerde. Tam metinler KUTUDA.
- 🔧 **K329 (28 Agu, CI nobeti):** iki kapi dosyasi kanonik `git_ortami.sentetik_git`'e gecirildi, yerelde YESIL olculdu; main'e INEMEDI — kutu 306>300, 6 blok `ARŞİVLENEBİLİRİM` bekliyor (**Okan arsivi**), is `ci-nobet-git-ortami` dalinda stage'li.

## ARSIVDE — 14-20 Agu `DEVAM-ARSIV.md`'de.
