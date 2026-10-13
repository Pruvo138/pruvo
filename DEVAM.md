# DEVAM (KraL) — 8 Agu 2026

**AÇILIŞTA: Skill loop 45m devam kur, CronList kanıtı kutuya** (BaBa 01:0x; döngü oturum-içi, öz-devir/yeniden başlatma/7 günde ÖLÜR) · kota öz-devri ≥500K (tur sayısı tetik DEĞİL; BITIS'siz işçi varken öz-devir YOK) → DEVİR + BaBa'ya "DEVİR yazdım, temizleniyorum" + `clear_session("self")` (OKAN KARARI 15:5x KESİN "500k dengeli" — 400K iptal, BaBa). 🔴 **ÖZ-DEVİR SINIF KURALI (BaBa 11 Eki 02:03, 3/3):** DEVİR bloğu + CronDelete + `clear_session` **AYNI TURDA**; "clear'a hazırım / BaBa onayı" beklemesi İHLAL; halefe "devam" yalnız BaBa (`list_events` 0'da).

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 DEVİR — 12 Eki 23:2x, KraL halef-26 → halef-27 (bağlam 503K kota RED; UÇUŞTA İŞÇİ 0; dış: tren2 SERİT B `38301943530` @`9214dc84`)
**BİTTİ (ölçüldü):** claude-api MAIN `3cc6aaaa` (Pages `38268345398` deploy+yayin success) · **④ görsel = sağlayıcı png AYNEN** MAIN `78d2d6e5` (Pages `38285489103` 6/6 success; canlı `foto-uretim.js?v=f2f7c9bd88` boyama fonksiyonları 0; Okan'a 3 görsel gitti) · **m3 motor kapısı CANLI** `~/.claude/cron/isci.sh` (claude yalnız `odeme-|guvenlik-|gizlilik-|sema-|olcum-canli-`; test `tools/isci-motor-kapisi-test.py` 7/7·2/2; dal tren2 içinde) · 23:00 raporu `ISCI_MOTOR` satırı (m3) · kimlik testi etiket+çapa (m3) · kredi sayımı kutuda (Okan'a GİTMEZ) · yedek ölçümü (MESRU_KUCULME_TABAN_BAYAT, veri kaybı 0).
**SIRADAKİ TEK İŞ:** tren2 SERİT B `38301943530` → `success` + `python3 tools/serit-b-uc-kapisi.py kral/tren2-12eki 38301943530` ESIT → temiz geçici ağaçta origin/main + `--no-ff origin/kral/tren2-12eki` → push → Pages yayın nöbeti (ELLE İPTAL YOK, E4) → ağaç/dal temizliği (kv-k384 · rot-jeton · gh-tavan · kopru-flaky · yedek-dusus · motor-kapisi · tren2). Kırmızı = MaCiT katalog silmesi yolda (K438 parite) olabilir → taban tazele + yeniden dispatch.
**DONUK (Okan "tamam" demeden main'e GİRMEZ):** `kral/tren-12eki` @`a4fd4fd9` (eski, foto karışık) · `kral/k440-wrangler-log-12eki` (foto dosyası 10) · `kral/anahtarlik-kontrast-12eki` @`aae93675` (iki-renk, KraL kabul 11/11). Okan son soru: renk sayısı/sağlayıcı 4 renk — cevaplandı, karar yok.
**SONRA:** 12 silinen ürün (7 `2db3a161` + MaCiT'in 5'li A sınıfı) canlı 404/410 + sitemap → m3 `olcum-canli-` (içeren Pages success SONRASI) · K439 (kv-k384 main'e girince) · ana checkout ` M urunler.json` yabancı, dokunma.
**halef-27 (13 Eki 00:2x):** Pages `38304372073` @`16b31974` serit-a3 KIRMIZI = DEVAM'da sağlayıcı adı (K markasız nöbeti) → bu commit onarır. Silinen 12 ürün D1'de yayinda=1 (yayin-kapisi DEGISMEZ IHLALI 12; `d1-sync --adim` DELETE uçta koşamadı). Ürün kuyruğu dalı `kral/urun-kuyruk-12eki` @`f59ba27f` MERGE-BEKLIYOR (BaBa YAYIN AÇLIĞI hükmü).
**MOTOR ORANI (halef-26):** Claude işçi ~13 (kapı/ödeme/görsel; 3'ü hüküm değişince durduruldu) / m3 3.

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
