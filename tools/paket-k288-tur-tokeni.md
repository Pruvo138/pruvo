# K288 — `TUR_TOKEN`: tur başına token `isci.log`'da görünür (ÖLÇÜM, tavan YOK)

> Okan kararı: *"ölçümü chip'e ver, tavanı sonra konuşuruz."* Bu kalem **eşik/uyarı/bloklama
> İÇERMEZ**. Tavan ayrı kalemdir. Buraya eşik eklemeyin.

**Kod git DIŞINDA:** `~/.claude/cron/isci.sh` + `~/.claude/cron/tur-token-olcum.py` +
`~/.claude/cron/tur-token-test.py`. `git log` bunları görmez; bu dosya beş evin ortak
sözleşme kaydıdır. Değiştiren, değişiklik ANINDA yedek alır ve buraya yazar.

## 🔴 ÖNCE ŞUNU OKU — sık tekrarlanan yanlış öncül
**"`isci.log` tur başına token taşımıyor" DOĞRU DEĞİL.** 16 Ağu 2026'dan beri her tur şu
satırı düşürüyor:

```
=== <utc> OLCUM motor=<m> model=<m> etiket=<e> butce=<b> butce_vuruldu=<0|1>
    oturum_sayisi=<n> TUR=<n> TOPLAM_GIRDI=<n> TEPE=<n> CIKTI=<n>
    EN_BUYUK_OKUMA=<n> TOPLAM_OKUMA=<n> MUKERRER_OKUMA=<n> ===
```

Eksik olan "sayı" değil, **kırılım** ve **dürüstlük** idi:
1. `TOPLAM_GIRDI = input + cache_read + cache_creation` diye katlanıyordu → kotanın ~%87–95'ini
   yakan `cache_read` ayrı okunamıyordu.
2. Üreticisi `baglam-olcum.py` **fail-open**: kaynak yoksa sıfır basıyor → "bedava tur" yanılgısı.

## Sözleşme — `TUR_TOKEN` satırı
Her turda, `OLCUM` satırının HEMEN ARDINDAN, `===` sarmalayıcısı **taşımadan** düşer:

```
TUR_TOKEN girdi=<n> cikti=<n> cache_read=<n> toplam=<n> motor=<ad> tur=<oturum-uuid>
```

- `girdi` = `input_tokens` toplamı (saf, cache hariç)
- `cache_read` = `cache_read_input_tokens` toplamı
- `toplam` = `girdi + cache_read + cache_creation_input_tokens` → **`OLCUM TOPLAM_GIRDI` ile
  birebir aynı tanım** (çapraz doğrulama buna dayanır)
- `cikti` = `output_tokens` toplamı → `OLCUM CIKTI` ile birebir aynı
- `tur` = turun BİRİNCİ oturum kimliği (UUID). Sayı değil, **kimlik**.

### 🔴 FAIL-CLOSED — sıfır UYDURULMAZ
Ölçülemeyen turda sayı yerine şu düşer:

```
TUR_TOKEN=OLCULEMEDI SEBEP=<tek-kelimelik-sebep> motor=<ad> tur=<id|yok>
```

`SEBEP` değerleri: `projeler-dizini-yok` · `oturum-dosyasi-bulunamadi` · `usage-kaydi-yok` ·
`okuma-hatasi` · `arguman-eksik` · `olcum-araci-cikti-vermedi` ·
`profil-yok-olcum-blogu-kosmadi`. Ölçüm aracının rc'si **her zaman 0**; tur rc'sini etkilemez.

**Kaynak:** motorun Anthropic-uyumlu yanıt gövdesindeki `usage`, `claude` CLI tarafından
oturum transcript'ine yazılıyor (`<PROFIL>/projects/**/<OTURUM_ID>.jsonl` → `message.usage`).
Tur başına ve **gecikmesiz**. Panelin API Usage tablosu saatlik + gecikmelidir; **tur başına
muhasebeye uygun değildir**, mutabakat dışında kullanmayın.

## Bilinen sınır — kapanmadı, gizlenmedi
Tur **log yazma bloğuna varmadan** ölürse (tur tavanı TERM/KILL, çökme) `TUR_TOKEN` satırı
HİÇ düşmez — ne sayı, ne `OLCULEMEDI`. Yani **satırın yokluğu** ile `OLCULEMEDI` farklı
şeylerdir; sayan araç ikisini ayırmalı. Kapatmak `trap` gerektirir, bu kalemin kapsamı dışı.

İkinci sınır: işçi raporu `isci.log`'a akıyor; bir işçi metninde `TUR_TOKEN` geçerse
`grep -c TUR_TOKEN isci.log` **şişer**. Sayarken satır başına çıpalayın:
`grep -cE "^TUR_TOKEN" isci.log`.

## Kabul
```
python3 ~/.claude/cron/tur-token-test.py             → KABUL=8/8 MUTANT=ATLANDI KONTROL=ATLANDI
python3 ~/.claude/cron/tur-token-test.py --mutasyon  → KABUL=8/8 MUTANT=2/2 KONTROL=YESIL
                                                        MUTANT m1 OLDU dusen_vakalar=T5,T6
                                                        MUTANT m2 OLDU dusen_vakalar=T3,T4
                                                        MUTANT m3 YESIL dusen_vakalar=yok
```

Mutasyon bataryası **sekiz vakanın tamamını mutant kopyaya karşı koşar** — mutantın çıktısına
bakıp "mutant mutant mı" diye sormaz, **bataryanın onu yakaladığını** ölçer. Çöken/sözdizimi
bozuk mutant `BOZUK` sayılır, **öldürme sayılmaz**; mutasyon çapası bayatlayıp değişiklik hiç
olmadıysa `CAPA_BAYAT` basar (sessiz "hayatta kaldı" YOK). Kontrol mutantı `SEBEP` metnini
değiştirir — batarya `OLCULEMEDI` jetonuna baktığı için yeşil kalması meşrudur.

🔴 **`ATLANDI` ≠ `0` ≠ `KIRMIZI`.** Bayraksız koşum mutant çalıştırmaz; özet satırı bu yüzden
`ATLANDI` yazar. Önceden `MUTANT=0/2 KONTROL=KIRMIZI` yazıyordu — **ölçülmemiş olanı başarısız
diye raporluyordu** (iki yönlü zarar: yanlış alarm + "hepsi hayatta kaldı" yanlış güveni).
`T8` bu regresyonu kilitler; T8 alt süreci `PRUVO_K288_T8=1` ile korunur (özyineleme yok).

## Ölçülen (25 Ağu 2026, canlı trafik — sentetik değil)
| tur | `OLCUM TOPLAM_GIRDI` | `TUR_TOKEN toplam` | cache_read payı |
|---|---|---|---|
| `2026-08-24T22:39:33Z` `ci-nobeti` | 880.238 | 880.238 | **%86,99** |
| `2026-08-24T22:48:54Z` `kabul-k288-2-dogrulama` | 8.025.896 | 8.025.896 | **%87,42** |

`OLCUM`'un sahte sıfır bastığı 12 turda `TUR_TOKEN=OLCULEMEDI` düştü; ters yönde sapma yok.

Beş turun beşinde `girdi + cache_read = toplam` (cache_creation = 0) ve `cikti` = `OLCUM CIKTI`.
Ölçülen cache-read aralığı **%86,99 – %93,90** (kimi turları dahil).

`isci.sh`: **30.633 → 31.130 bayt** (+7 satır, −0).
Yedek: `~/.claude/cron/isci.sh.yedek-k288-20260824T223100Z` — `cp -p` ile alındı, mtime
değişiklik ÖNCESİNİ (Ağu 20 16:51) taşıyor; git dışı dosyanın tek geri dönüş yolu.

## ⛔ KAPANMADI — panel mutabakatı
MiniMax panelinin oturumu **KAPALI** (`platform.minimax.io` → `account.minimax.io/unified-login`).
İşçi giriş DENEMEDİ, şifre GİRMEDİ (yasak). Dolayısıyla `PANEL_TOPLAM=OLCULEMEDI`.
Log tarafı hazır: **2026-08-24 22:00–23:00Z, minimax-m3, 5 sıfır-olmayan tur →
`LOG_GIRDI=14.632.999 LOG_CIKTI=113.453 LOG_TOPLAM=14.746.452`.**
Okan paneli açtığında mutabakat tek turda kapanır; beklenen fark kaynakları: panel kovayı
İSTEK anına, log ise BİTİŞ anına yazar (saat sınırını aşan tur kayar) + panel gecikmesi.
