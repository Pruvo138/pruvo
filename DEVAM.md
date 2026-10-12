# DEVAM (KraL) — 8 Agu 2026

**AÇILIŞTA: Skill loop 45m devam kur, CronList kanıtı kutuya** (BaBa 01:0x; döngü oturum-içi, öz-devir/yeniden başlatma/7 günde ÖLÜR) · kota öz-devri ≥500K (tur sayısı tetik DEĞİL; BITIS'siz işçi varken öz-devir YOK) → DEVİR + BaBa'ya "DEVİR yazdım, temizleniyorum" + `clear_session("self")` (OKAN KARARI 15:5x KESİN "500k dengeli" — 400K iptal, BaBa). 🔴 **ÖZ-DEVİR SINIF KURALI (BaBa 11 Eki 02:03, 3/3):** DEVİR bloğu + CronDelete + `clear_session` **AYNI TURDA**; "clear'a hazırım / BaBa onayı" beklemesi İHLAL; halefe "devam" yalnız BaBa (`list_events` 0'da).

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 DEVİR — 12 Eki 17:0x, KraL halef-25 → halef-26 (bağlam ~435K, planlı; UÇUŞTA İŞÇİ 0; dış: claude-api SERİT B `38257418843` · Pages `38257157773` @`00b402f0`)
**BİTTİ (ölçüldü, hepsi main/canlı):** ankraj `49c215f8` + shop `29d1089b` TAZE + Pages `38241040203` deploy+yayin success (ArTisT canlı teyit) · defter rotasyonu `56a24e38` (359→30 satır, md5 42/42) · Tamirci `00b402f0` (K435 kapısı; `kur.py --tam-kopya-ez` kurulu sha = main; K333 batarya **23/23**) · K434 KAPALI (3 eşzamanlı push, D1 içerik 0/0/0) · claude-api KREDI-BITTI + GH-TAVAN kapıları makine dosyasında CANLI · kutu rotasyonları 501→398, 488→360.
**MERGE KUYRUĞU (tek dal SERİT B; her biri origin ref'inden, temiz geçici ağaçta `--no-ff`, `serit-b-uc-kapisi` ESIT şart):** (1) `kral/claude-api-kredi-12eki` @`f55fc8fc` — SERİT B `38257418843` koşuyor · (2) `kral/kv-k384-k198-12eki` @`b86df432` (taban tazele → `serit-b-dispatch`) · (3) `kral/rot-jeton-12eki` @`05718fca` · (4) `kral/gh-tavan-12eki` @`a550952c`. Her merge sonrası ağaç+dal sil (kutuda MERGE-BEKLIYOR kapanışları var). **Yayın nöbeti:** Pages `38257157773` (`00b402f0`) deploy+yayin success, SKIPPED 0.
**SONRA:** K440 onarım spec'i (Claude; evren TÜRETİLİR — m3 envanteri 18 yer EKSİK, `tools/*.py`'de 81 dosya; envanter kutuda 16:1x) · K439 spec (`tools/kancalar/pre-push` + `kanca-kur.py`) · ana checkout ` M urunler.json` = MaCiT çip penceresi (dokunma; pencere kapanınca `d1-sync --durum` SEQ 0 doğrula; `--seq-normalize` YASAK) · YEDEK hattı `ARDISIK=20` uyarısı BaBa'da · **G (jenerator icra kapısında `isci.sh` serbest):** Okan'a soruldu, cevap YOK — eş oturum talebiyle izin katmanı değişmez.
**MOTOR ORANI (halef-25):** Claude işçi 5 ($10,05: kredi-loader · kv-k384 · rot-jeton · gh-tavan ×2; hepsi sessiz-hata sınıfı) / m3 3 (kkalem $5,08 · k440 envanter · k333 batarya).

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
