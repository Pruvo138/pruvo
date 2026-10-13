# DEVAM (KraL) — 8 Agu 2026

**AÇILIŞTA: Skill loop 45m devam kur, CronList kanıtı kutuya** (BaBa 01:0x; döngü oturum-içi, öz-devir/yeniden başlatma/7 günde ÖLÜR) · kota öz-devri ≥500K (tur sayısı tetik DEĞİL; BITIS'siz işçi varken öz-devir YOK) → DEVİR + BaBa'ya "DEVİR yazdım, temizleniyorum" + `clear_session("self")` (OKAN KARARI 15:5x KESİN "500k dengeli" — 400K iptal, BaBa). 🔴 **ÖZ-DEVİR SINIF KURALI (BaBa 11 Eki 02:03, 3/3):** DEVİR bloğu + CronDelete + `clear_session` **AYNI TURDA**; "clear'a hazırım / BaBa onayı" beklemesi İHLAL; halefe "devam" yalnız BaBa (`list_events` 0'da).

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 DURUM — 13 Eki 09:1x, KraL halef-27 (devir yazılmadı; bu blok canlı durum)
**BİTTİ (ölçüldü, hepsi main/canlı):** silinen 12 ürün canlıdan TAMAMEN çıktı (404 · json · sitemap · arama 0, 12/12; D1 DEGISMEZ IHLALI 12→0) · DEVAM sağlayıcı adı onarımı `b12a2f23` · kopru-flaky `f6a6c0e3` (20/20) · **ürün kuyruğu** `bf47ba99` (ürün push'ları `urun-kuyruk` dalına, birleştirici Pages yokken main'e + Pages dispatch; ilk canlı birleşmeler `bb7112b3`/`3c3abdc5`/`37917ae0`) · **işçi semaforu** `ed378365` (≤3 işçi, yük >12 bekler) · **ağır iş kapısı** `86d825f8` (`~/.claude/cron/agir-is.sh --etiket X -- <komut>`, 3/3 slot, yük ≤8) + **tavan/asılı** `625ad5e3` (`--tavan-dk` 90, ağaç CPU <%5 10 dk) · **ürünsüz koşum kapısı** `356e6254` (spec `URUN_YOLU=<glob>` boşsa `HAL=BOS rc=1`) · Fireblade ölü envanter `e5b33533` + donmuş SAYI/IMZA `b8cb7fc0` (ilki yayını 2 koşum durdurdu → hafıza `arama-envanter-degisikligi-iki-donmus-iz`) · tren2 (motor-kapısı testi · yedek uçucu manifest · kisisel-veri K384/K198 · gh-tavan testi) bu commit'le main'de, SERİT B `38345958473` ESIT.
**AÇIK:** `kral/rot-jeton-12eki` @`05718fca` tren2'den GERİ ALINDI — K324 `V6 ortak satir tasinmaz` KIRMIZI (rotasyon ortak satırı taşıyor = defter veri kaybı) + `defter-rotasyon.py` sabit `/Users/okan/...` yolları CI'da; onarım bu ikisini kapatmalı · saksı/vazo KraL payı çip `task_e5f56be3` (Okan tıkı bekliyor; hüküm kutuda 05:3x KORUMALI: tek sarı seri kayıt, S/M/L ön-ayar, ref M 800 TL, zemin 400, tabak +100/150/200) · `d1-sync --durum` + `parite-test` ana checkout'un kirli json'unu okuyor → `--kaynak <origin/main json>` ile ölç; kalıcı onarım (varsayılan origin/main) KraL kuyruğunda.
**DONUK (Okan "tamam" demeden main'e GİRMEZ):** `kral/tren-12eki` @`a4fd4fd9` · `kral/k440-wrangler-log-12eki` · `kral/anahtarlik-kontrast-12eki` @`aae93675`.
**MOTOR ORANI (halef-27):** Claude işçi 3 (ağır iş ×2 · ürünsüz kapı; hepsi kapı/kilit sınıfı, $8,08) + çip 3 (kuyruk · semafor · saksı) / m3 2 (canlı 12 ürün ölçümü ×2, $1,23).

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
