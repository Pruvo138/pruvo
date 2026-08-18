# PAKET ③c — SAHİPLİK HARİTASI: bağımsız KABUL + muafiyetin gerçek KABLOYA çevrilmesi

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ (**çürütücü** — ③b'yi YAZAN turdan BAŞKA tur).
③'ün (`tools/paket-sahiplik-haritasi.md`) kapanış dilimidir.

## 1. ÖLÇÜLEN DURUM

* Dal `kral/paket3b-evren` · tek commit `dfc7eb5a` ("sahiplik evreni 28 → 171 mekanizma;
  tohum 6/6 içeride, M4 çapası eklendi"). Ağaç TEMİZ, main dışı commit 1.
  Kapsam: `tools/sahiplik-haritasi.tsv` (+167/-…) · `tools/sahiplik-kapisi.py` (+111/-…).
* **Kabul KOŞULMADI.** ③'ün kabul satırı (`--kendini-test` → `EKSIK=0 BAYAT=0 MUTANT=3/3
  KONTROL=2/2`, rc=0) hiçbir turda ham çıktıyla kanıtlanmadı.
* main'de `c6ddede6`: `tools/ci-kapsam-test.py` İZİN LİSTESİ'ne **`R_SAHIPLIK` muafiyeti**
  eklendi (gerekçe: "elle + merge-kapısı sırasında koşulur, deploy.yml'e ayrı bağlanmaz").

🔴 **MUAFİYET, KOŞUYOR DEMEK DEĞİLDİR.** Bu evde ölçülmüş kural (16 Ağu): yeni bir kapı
üreten iş, onu CI'a bağlamayı da AYNI dilimde yapar; muafiyet eklemek kapıyı hiçbir makinenin
koşmadığı bir dosyaya çevirir. "merge-kapısı sırasında koşulur" gerekçesi bir MAKİNE değil bir
YORDAM'a atıftır — kimse koşmuyor. Sahiplik haritası koşmayan bir kapıyla **sessizce bayatlar**
([[envanter-drift-parti-basina]] · [[kapi-varlik-olcer-yokluk-olcmez]]). Muafiyeti ben (KraL)
ekletmiştim; hüküm geri alınıyor.

## 1b. ADIM 0 — K175'in ÖLÇÜM BORCU (bu turda kapatılır, 2 dakika)

K175 turu onarımı uyguladı ve kabulü geçti, ama **ADIM 1 ölçümünün ham çıktısı hiçbir yere
yazılmadı** — prob betiği diskte duruyor, sonucu yok. Özet ham dosyayla desteklenmeden hüküm
sayılmaz. Bu turda:

```
python3 /Users/okan/.claude/cron/k175-prob.py
```

Tek satırlık çıktı (`SEBEP_CRON=… WHICH_CRON=… KOSUM_CRON=… SEBEP_TAM=… WHICH_TAM=… KOSUM_TAM=…`)
rapora **BİREBİR** yapıştırılır. ⚠️ Bu ölçüm ONARIMDAN SONRA alınıyor; `SEBEP_CRON` artık
`IKILI_YOK` DEĞİL de `TAMAM` çıkarsa bu, K175'in H2 kolunun (PATH genişletmesi) prob sürecine
de sızdığı anlamına gelir — o zaman raporda AÇIKÇA belirt, "onarım öncesi durum ölçüldü" DEME.
Sonra prob dosyası **SİLİNİR** ve silindiği `ls` çıktısıyla kanıtlanır (K175'in temizlik borcu).

## 2. ADIM 1 — BAĞIMSIZ ÇÜRÜTME (önce bu; onarım sonra)

Çalışma ağacı (ZATEN AÇIK, yeni worktree AÇMA):
`/Users/okan/dev/pruvo/.claude/worktrees/kral-paket3b-evren` — dal `kral/paket3b-evren`.
Orada koş, **ham çıktıyı birebir** rapora yapıştır:

```
python3 /Users/okan/dev/pruvo/tools/sahiplik-kapisi.py --kendini-test
```

Beklenen son satır ve rc=0:

```
EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=0 SAHIPSIZ=<n> MUTANT=3/3 KONTROL=2/2
```

🔴 **ÖZETİN HAM DOSYADA DESTEKLENDİĞİ AYRICA ÖLÇÜLÜR** (18 Ağu dersi: bir işçi
`KILIT_ALINDI=1` yazdı, ham çıktıda `grep -c` → 0). Bu yüzden `EVREN` ve `HARITADA`
sayıları **kapının kendi çıktısından BAĞIMSIZ** ikinci bir komutla da ölçülür:

* haritanın satır sayısı: `grep -c` ile `tools/sahiplik-haritasi.tsv` (başlık satırı düşülür)
* `EV=BILINMIYOR` satır sayısı: `grep -c` → `SAHIPSIZ` ile **birebir** aynı olmalı

İki ölçüm ayrışıyorsa hüküm DÜŞER, onarıma GEÇME, rapora yaz ve dur.

⚠️ **M3 mutantı özellikle denetlenir:** "kapsam evrenini boş kümeye indir → `EVREN=0` ile
YEŞİL DÖNMEMELİ". Mutant yalnız kendi kolunu düşürmeli; sayıyı/imzayı da yakıyorsa hedef kol
ölü olsa bile kırmızı gelirdi ve kanıt saymaz ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

## 3. ADIM 2 — MUAFİYET KALDIRILIR, KAPI KABLOLANIR

Aynı dalda (`kral/paket3b-evren`):

1. `tools/ci-kapsam-test.py`'den **`R_SAHIPLIK` muafiyeti ve İZİN LİSTESİ girdisi SİLİNİR**
   (`c6ddede6`'nın eklediği 9 satır).
2. `tools/sahiplik-kapisi.py` **hijyen şeridine** bağlanır: `.github/workflows/nobet.yml`
   **SERİT B**. Gerekçe (şerit seçimi kuralı): bu kapının kırmızısı müşteriye yanlış para
   ödetmez, veri sızdırmaz, siteyi durdurmaz → bloklayıcı şerit DEĞİL, hijyen şeridi.
3. Adım komutu: `python3 tools/sahiplik-kapisi.py` (kendini-test değil, canlı invaryant).

✅ **ÇAKIŞMA DURUMU ÖLÇÜLDÜ:** `nobet.yml` üzerindeki K166 inişi main'e GİRDİ (`e70c89d7`),
`k166b-yayin-sinyali` worktree'sinin main dışı commit'i 0. Dosya artık serbest. Yine de
düzenlemeden ÖNCE `git -C /Users/okan/dev/pruvo log --oneline -3 -- .github/workflows/nobet.yml`
ile son dokunuşu teyit et; başka bir tur araya girdiyse DUR ve rapora yaz.

## 4. KABUL (çalıştırılabilir; iki komut birden)

```
python3 /Users/okan/dev/pruvo/tools/sahiplik-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/ci-kapsam-test.py
```

Rapora son satırlar birebir + rc'ler:

```
EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=0 SAHIPSIZ=<n> MUTANT=3/3 KONTROL=2/2
CI_KAPSAM_RC=0
```

`CI_KAPSAM_RC=0`, muafiyet SİLİNDİKTEN **sonra** alınmış olacak. Muafiyet dururken alınan
yeşil kanıt değildir.

## 5. RAPOR

Nöbet/dal kanonik mühendis rapor dosyasına; içinde:

* iki kabul komutunun **ham** son satırları + rc'leri,
* jeton kanıt bloğu (her sayının `grep -c` komutu ve çıktısı **raporun içinde**),
* `SAHIPSIZ` listesi mekanizma adlarıyla — **işçi sahip ATAMAZ**, hüküm mimarda,
* `nobet.yml`'e eklenen adımın diff'i (3-5 satır),
* son satır: `TEMIZ=EVET` (geçici dosya kalmadı).

## 6. SINIRLAR

* Harita İÇERİĞİNE (hangi ev hangi mekanizmanın sahibi) DOKUNULMAZ; bu dilim yalnız
  **kabulü koşar** ve **kapıyı kabloya bağlar**.
* `EV=BILINMIYOR` satırları olduğu gibi kalır; sahip atama mimarın işi.
* Kardeş depolar kapsam dışı (③ §5).
* Merge main'e **mimar** tarafından, merge kapısı yordamıyla yapılır; işçi merge ETMEZ.
* İş bitince worktree KALDIRILIR ve kaldırıldığı `git worktree list` çıktısıyla kanıtlanır
  (13 Ağu disk emri). Şu an worktree SAYI=3 / TAVAN=2 — bu dilim tavanı da geri indirir.

## 7. İŞÇİ TALİMATI

* **Tavan:** ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Raporu ÖNCE oluştur, ilerledikçe doldur; başka turun raporunun ÜZERİNE YAZMA, başa EKLE.
* **DOKUNMA:** `urunler.json` · `crontab` · `~/.claude/cron/gozcu.py` (K175 turu orada çalışıyor).
