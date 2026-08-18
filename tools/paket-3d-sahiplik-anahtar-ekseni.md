# PAKET ③d — SAHİPLİK HARİTASI: eksik olan İÇERİK değil ANAHTAR (birleştirme ekseni tutmuyor)

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ · kabul MİMARDA (bağımsız çürütücü turuyla).
③b'nin (`dfc7eb5a`) iddiası ③c'de ÇÜRÜDÜ; bu paket kırmızıyı kapatır.
Kabul protokolü ③ §0 ile AYNI (jeton kanıtı raporun içinde · varlık davranış değildir ·
ölçülemeyene `0` değil `OLCULEMEDI` · son adım temizlik).

## 1. ÖLÇÜLEN OLGU (③c, bağımsız tur — ham)

```
tools/sahiplik-kapisi.py            → EVREN=170 HARITADA=28 EKSIK=142 BAYAT=0 SAHIPSIZ=28 KABUL_DOLU=0   rc=1
tools/sahiplik-kapisi.py --kendini-test → MUTANT=3/4 KONTROL=1/2   rc=1  (M4 ve K1 TUTMADI)
awk 'NR>1 && NF' sahiplik-haritasi.tsv           | wc -l → 185
awk -F'\t' 'NR>1 && $3=="BILINMIYOR"' ...        | wc -l → 171
awk -F'\t' 'NR>1 && $3!="BILINMIYOR"' ...        | wc -l → 14
```

🔴 **ÇELİŞKİ BURADA:** haritada **185** veri satırı var, evrende **170** mekanizma var, ama
eşleşen yalnız **28** — ve `BAYAT=0`. `BAYAT`, "haritada olup diskte olmayan satır" demek.
Eğer 157 harita satırı hiçbir evren üyesiyle eşleşmiyorsa, ya bunların **BAYAT sayılması**
gerekirdi ya da eşleşmeleri. İkisi de olmuyor → **iki taraf aynı anahtarla konuşmuyor.**
Sayı eksikliği değil, **eksen** hatası ([[hukum-yanlis-birimde]] ·
[[nobetci-kanonik-kaynagi-tek-eksende]]).

Ayrıca `KABUL_DOLU=0`: `KABUL_KOMUTU` kolonu **hiçbir satırda dolu değil**. ③ §2a o kolonu
"o mekanizmayı ölçen çalıştırılabilir komut ya da `YOK`" diye tanımlıyordu; bugünkü hâliyle
harita "bu kimin işi" sorusuna da "nasıl ölçülür" sorusuna da cevap veremiyor.

## 2. ADIM 1 — ANAHTARI ÖLÇ (önce bu; onarım ÖLÇÜMDEN SONRA)

Geçici tek betikle (repo'ya commit EDİLMEZ, iş bitince silinir) şu üç kümeyi **yazdır**:

1. `EVREN` üyelerinin kapı tarafından üretilen anahtarları — **ilk 10 örnek, birebir**.
2. `sahiplik-haritasi.tsv`'nin `YOL` kolonundan üretilen anahtarlar — **ilk 10 örnek, birebir**.
3. Kesişim / yalnız-evrende / yalnız-haritada sayıları:
   `KESISIM=<n> YALNIZ_EVREN=<n> YALNIZ_HARITA=<n>`

Rapora bu üç blok **birebir** girer. Beklenen ayrışma eksenleri (hangisi olduğunu ÖLÇÜM
söyleyecek, ben SEÇMİYORUM):

* mutlak yol ↔ repo-göreli yol
* `cron:` öneki ↔ `~/.claude/cron/` ↔ `/Users/okan/.claude/cron/`
* `tools/x.py` ↔ `x.py` (dizin öneki)
* sondaki boşluk / `\r` / sekme sayısı kayması

🔴 **`BAYAT=0` ÇELİŞKİSİ AYRICA AÇIKLANACAK.** 157 eşleşmeyen harita satırı neden BAYAT
yazmıyor? Ya bayatlık kolu hiç koşmuyor ya da o da aynı bozuk anahtarla bakıyor. Bu iki
şıktan hangisi olduğu ÖLÇÜLECEK; "muhtemelen" yazan rapor kabul edilmez.

## 3. ADIM 2 — HÜKÜM

**H1 — TEK ANAHTAR NORMALİZASYONU, TEK YERDE.** Hem evren tarafı hem `YOL` kolonu **aynı**
fonksiyondan geçer (`_anahtar(yol)`); iki ayrı normalizasyon yazılmaz
([[ikiz-tanim-sessiz-ayrisma]]). Kanonik biçim ③ §2a'da zaten yazılı: repo-göreli yol,
`~/.claude/cron/` altındakiler `cron:` önekiyle. Kod bu biçime uyar, biçim koda uydurulmaz.

**H2 — `BAYAT` kolu gerçekten koşar.** Normalizasyondan sonra hâlâ eşleşmeyen harita satırı
**BAYAT** sayılır ve adıyla basılır. `BAYAT=0`, ölçülen sıfır olmadıkça yazılmaz.

**H3 — `KABUL_KOMUTU` boş bırakılamaz.** Her satır ya çalıştırılabilir bir komut taşır ya
açıkça `YOK` yazar. Boş hücre → **RED** (`KABUL_BOS=<n>` ile). 🔴 İşçi komut **UYDURMAZ**:
bilmiyorsa `YOK` yazar. Uydurulmuş kabul komutu, olmayan bir ölçümü var gösterir — bu evde
en pahalı hata sınıfı.

**H4 — mutasyon bataryası onarılır.** ③c'de **M4 ve K1 tutmadı**; batarya kendisi ölçmüyor.
Her mutant nişanlandığı vakayı TEK BAŞINA düşürmeli
([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]); düşüremiyorsa mutant daraltılır, vaka
gevşetilmez. **Vakayı mutanta uydurmak YASAK** ([[test-hatali-davranisi-kutsar]]).

**H5 — `EV` ataması YAPILMAZ.** 171 `BILINMIYOR` satırı olduğu gibi kalır; sahip atamak
mimar hükmüdür, işçi tahmin etmez (③ §2a).

## 4. ADIM 3 — MUAFİYET KALDIRILIR, KAPI KABLOLANIR (③c §3'ten devralındı)

1. `tools/ci-kapsam-test.py`'den `R_SAHIPLIK` muafiyeti ve İZİN LİSTESİ girdisi **SİLİNİR**.
2. `tools/sahiplik-kapisi.py` **hijyen şeridine** (`nobet.yml` SERİT B) bağlanır; adım komutu
   `python3 tools/sahiplik-kapisi.py`.
3. Bu adım **ancak §5 yeşilken** yapılır; kırmızı kapıyı kabloya bağlamak yayını durdurur.

## 5. KABUL (çalıştırılabilir)

```
python3 /Users/okan/dev/pruvo/tools/sahiplik-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/sahiplik-kapisi.py
python3 /Users/okan/dev/pruvo/tools/ci-kapsam-test.py
```

son satırlar + rc'ler:

```
EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=<olculen> SAHIPSIZ=<n> KABUL_BOS=0 MUTANT=4/4 KONTROL=2/2
CI_KAPSAM_RC=0
```

`EKSIK=0` **normalizasyonla** gelmeli — haritaya 142 satır çakıp `EKSIK`i sıfırlamak ÇÖZÜM
DEĞİLDİR. Raporda `KESISIM/YALNIZ_EVREN/YALNIZ_HARITA` sayıları **onarım öncesi ve sonrası**
ayrı ayrı yazılır; ikisi de diskten.

## 6. SINIRLAR

* Dal `kral/paket3b-evren` (`dfc7eb5a`) KORUNDU ve TABANDIR — sıfırdan başlama, üstüne çık.
* Harita satırlarının `EV` içeriğine DOKUNULMAZ (H5).
* Kardeş depolar kapsam dışı.
* Worktree tavanı şu an **2/2 DOLU**; yeni worktree açmadan önce `git worktree list` ile
  boşluk ölç, yoksa mimara bildir — tavanı kendi başına aşma.
* Merge main'e MİMAR tarafından; işçi merge ETMEZ.

## 7. İŞÇİ TALİMATI

* Sıra: ADIM 1 (ölç) → ADIM 2 (onar) → ADIM 3 (kablo, yalnız yeşilse) → KABUL.
  Ölçüm çelişkiyi açıklamıyorsa ADIM 2'ye GEÇME, raporla ve DUR.
* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Raporu ÖNCE oluştur; başka turun raporunun ÜZERİNE YAZMA, başa EKLE.
* **DOKUNMA:** `urunler.json` · `crontab` · `~/.claude/cron/gozcu.py` · `~/.claude/cron/kilit.py`.
