# PAKET ③f — Sahiplik kapısı HANGİ AĞAÇTA koşarsa koşsun AYNI ağacı ölçüyor (sabit mutlak kök)

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ · kabul MİMARDA.
③c ve ③e'nin kırmızıları BURADAN geliyor. ③d'nin yeşili de buradan.

## 1. MİMARIN KENDİ ÖLÇÜMÜ (git objelerinden — worktree'den, işçiden BAĞIMSIZ)

```
git show kral/paket3d-anahtar:tools/sahiplik-haritasi.tsv | grep -c ""   → 186   (185 veri satiri)
git show kral/paket3b-evren:tools/sahiplik-haritasi.tsv   | grep -c ""   → 186
git show main:tools/sahiplik-haritasi.tsv                 | grep -c ""   →  43
git show kral/paket3d-anahtar:tools/sahiplik-haritasi.tsv | grep -c "cron:"  → 18
git show kral/paket3d-anahtar:tools/sahiplik-kapisi.py | grep -n "CANON\|repo_kok"
    47:  CANON = "/Users/okan/dev/pruvo"
    48:  CRON  = "/Users/okan/.claude/cron"
   566:  repo_kok = os.path.abspath(args.repo)
```

**Kök neden:** kapının hedefi **sabit mutlak yol**. `--repo` verilmezse, hangi worktree'den
çağrılırsa çağrılsın **ana checkout'u** ölçer. Bu yüzden:

| Tur | Nerede koştu | `--repo` | Sonuç | Neden |
|---|---|---|---|---|
| ③c | ana checkout | yok | `HARITADA=28 EKSIK=142` | main'in 43 satırlık TSV'si |
| ③e | dalın worktree'si | yok | `HARITADA=28 EKSIK=143` | **yine main'in TSV'si** |
| ③d | dalın worktree'si | (verilmiş) | `HARITADA=171 EKSIK=0` | dalın 186 satırlık TSV'si |

Üç tur da doğru koştu; **kapı yanlış yere baktı.** ③c'de "anahtar ekseni bozuk" teşhisim de,
③e'nin "143 satır dalda kayıp" teşhisi de bu yüzden yanlıştı. Dosya yerinde, 185 satır.
Sınıf hafızada var: [[sabit-mutlak-yol-yerelde-yesil]] · [[parite-testi-olculemedi-basiyor]].

## 2. 🔴 BU KAPI BUGÜNKÜ HÂLİYLE CI'DA KOŞAMAZ

③d kapıyı `nobet.yml` SERİT B'ye bağladı (teyit ettim: `grep -c "sahiplik-kapisi"` → **1**).
Ama GitHub koşucusunda `/Users/okan/dev/pruvo` ve `/Users/okan/.claude/cron` **YOKTUR**.
Merge edilirse SERİT B her koşumda ya çöker ya boş evren ölçer. **Kabloyu bağlamak,
kapının taşınabilir olmasını gerektirir** — bu paketin asıl işi budur.

## 3. MİMARIN DÜZELTMESİ — ③e'nin bir kırmızısı BENİM HATAMDI

③e'ye kabul jetonu olarak `grep -c R_SAHIPLIK == 0` yazmıştım; ölçüm **3** verdi ve tur
"muafiyet tam kalkmamış" dedi. Diff'e baktım: muafiyet **gerçekten kalkmış** —
`R_SAHIPLIK = (...)` tanımı yorum satırına alınmış ve `IZIN_LISTESI`'ndeki
`"tools/sahiplik-kapisi.py": R_SAHIPLIK` girdisi **kaldırılmış**. Üç isabet yorum metinlerinde.
**Jeton adı sayan kabul, davranış ölçmez** ([[jeton-listesi-kapsam-kaniti-degildir]]).
Bu eksende dal TEMİZ; kabul kriteri aşağıda davranışsal olanla DEĞİŞTİRİLDİ.

## 4. HÜKÜM

**H1 — Hedef ağaç, kapının çağrıldığı yerden türetilir.** Varsayılan repo kökü
`__file__`'ın konumundan hesaplanır (betik `tools/` altında olduğuna göre bir üst dizin).
`--repo` bir OVERRIDE olarak KALIR. `CANON` sabiti **varsayılan hedef olmaktan çıkar**;
tutulacaksa yalnız açıkça loglanan bir son çare olur — **sessiz geri düşüş YASAK.**

**H2 — `cron:` düzlemi opsiyonel, yokluğu `0` DEĞİL `OLCULEMEDI`.** Dizin yoksa (CI koşucusu)
kapı `CRON_EVRENI=OLCULEMEDI` yazar ve o düzlemi hükümden düşürür; `tools/` düzlemi
ölçülmeye devam eder. **Ölçülemeyen düzlemi 0 saymak bu depoda yasak eksen** (K163/K175
ile aynı sınıf). Boş evren yeşil değildir.

**H3 — Kapı taşınabilir olmalı.** Repo kökü dışında hiçbir mutlak yol, hedef belirlemede
kullanılmaz.

## 5. KABUL (çalıştırılabilir) — **İKİ KONUMDAN**, bu sefer şart

```
# (a) ana checkout'tan
cd /Users/okan/dev/pruvo && python3 tools/sahiplik-kapisi.py --kendini-test
# (b) dalın worktree'sinden — --repo BAYRAĞI VERMEDEN
cd <worktree> && python3 tools/sahiplik-kapisi.py --kendini-test
```

🔴 (b), `--repo` olmadan **kendi ağacının** sayılarını vermeli. İki koşumun `EVREN`/`HARITADA`
değerleri kendi ağaçlarına göre doğru olmalı; ikisi de rapora `pwd` ile birlikte yazılır.

Son satır + rc=0 (dalın ağacında):
```
EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=0 SAHIPSIZ=<n> KABUL_BOS=0 MUTANT=<n>/<n> KONTROL=2/2
```

### 5.1 CI GERÇEĞİ VAKASI (yeni, zorunlu)
Sentetik bir kökte (`tempfile` altında `tools/` + TSV kopyası), `CANON` ve `CRON` yollarının
**var olmadığı** koşullar taklit edilerek kapı koşulur. Beklenen: çökme YOK,
`CRON_EVRENI=OLCULEMEDI`, `tools/` düzlemi ölçülür, hüküm sebep taşır.
Bu vaka yoksa kablo bağlanmaz.

### 5.2 Davranışsal muafiyet kontrolü (`grep` DEĞİL)
```
python3 tools/ci-kapsam-test.py
```
rc=0 **ve** çıktısında `tools/sahiplik-kapisi.py` **muaf listesinde GÖRÜNMEZ**. Jeton sayma yok.

### 5.3 Mutantlar
* **M1** — H1'i geri al (hedefi `CANON`a sabitle) → **(b) koşumu (a) ile aynı sayıyı verir**
  → vaka DÜŞER. (Bugünkü hatayı birebir yakalayan mutant budur.)
* **M2** — `CRON` yokluğunda `0` döndür → 5.1 DÜŞER.
* **M3** — boş evrende rc=0 döndür → batarya KIRMIZI.
* ③d'nin bataryasındaki mevcut mutantlar KORUNUR; ③e'de `MUTANT=3/4 KONTROL=1/2` çıkmasının
  sebebi de H1 olabilir — **önce H1'i onar, sonra bataryayı yeniden ölç.** Batarya hâlâ
  eksikse mutantı daralt, **vakayı gevşetme** ([[test-hatali-davranisi-kutsar]]).

## 6. SONRA — merge

Yeşilse `tools/paket-3e-merge.md` yordamı YENİDEN koşulur (bu sefer §2'deki kabul jetonu
davranışsal olanla). Merge'ü İZOLE OLMAYAN tur yapar.

## 7. SINIRLAR / İŞÇİ TALİMATI

* Taban dal `kral/paket3d-anahtar` (`8691487a`) — sıfırdan başlama, üstüne çık.
* Harita İÇERİĞİNE ve `EV` kolonuna DOKUNULMAZ (171 satır `BILINMIYOR` kalır; sahip atama mimarda).
* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Worktree: bir tane aç, aynı turda kaldır; `k166b-yayin-sinyali`'ye DOKUNMA.
* Raporu ÖNCE oluştur; başka turun raporunun ÜZERİNE YAZMA, başa EKLE. Her sayının yanında
  onu üreten komut ve `pwd`.
* **DOKUNMA:** `urunler.json` · `crontab` · `~/.claude/cron/gozcu.py` · `~/.claude/cron/kilit.py`.
