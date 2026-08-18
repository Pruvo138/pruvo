# PAKET T2 — SENTETİK YARIŞ TATBİKATI: kilit mekanizması VAR, KANITI YOK

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ · kabul MİMARDA.
BaBa'nın "GH-kırmızı düzeni" 6 tatbikatından T2'nin icrası. Sayaç bugün **0/6**; bu paket
geçerse **1/6** olur ve BaBa'ya sunulacak ilk gerçek "kuruldu" bu olur.

## 0. KABUL PROTOKOLÜ (③ §0 ile AYNI, tekrarlanmıyor — bağlayıcı)

Jeton kanıtı raporun İÇİNDE · kabul grep'ini MİMAR koşar · **varlık davranış değildir** ·
birimler açık · ölçülemeyene `0` değil `OLCULEMEDI` · son adım temizlik.

🔴 **BU PAKETİN VAR OLMA SEBEBİ TAM DA BU KURALIN İHLALİDİR.** 18 Ağu'da bir işçi T2'yi
"KURULDU · `KILIT_ALINDI=1 ONCEKI_TUR_SURUYOR=1 devir=1 birak=1`" diye yazdı; ham çıktıda
üç jetonun `grep -c` sonucu **0/0/0** çıktı. Kaydedilen tek komut `kilit.dir()` idi — yani
fonksiyonların VAR olduğunu gösteren bir liste. **Varlık davranış değildir.**

## 1. MEKANİZMA (ölçüldü — duruyor, tatbikatsız)

`~/.claude/cron/kilit.py` (K160 dilim-1, TEK KAYNAK): `karar()` → `AL|DOLU|BAYAT` ·
`al()` → `(alindi, hüküm)` · `birak()` → sahiplik denetimli silme.
Gövde `gozcu.py` K148 referansından taşınmış: `O_EXCL`-önce + `FileExistsError`'da TAZE
okuma + "DOLU ÇALINMAZ, artık kilit TEK KEZ devralınır".

🔴 **MİMARIN ÖLÇTÜĞÜ AÇIK (bu turda kapanacak):** `al()`'ın sözleşmesi (docstring, satır 13
ve 57) dört hüküm vaat ediyor — `KILIT_ALINDI` · `ONCEKI_TUR_SURUYOR` · **`DEVRALINDI`** ·
`YAZILAMADI`. Gövdede `DEVRALINDI` **hiçbir dönüş yolunda YOK**: artık kilit devralındıktan
sonra da akış `return True, "KILIT_ALINDI"`e düşüyor (satır 93-102). Yani **temiz başlangıç
ile "başkasının cesedini temizleyip başlama" ayırt edilemiyor**; nöbet günlüğü ikisini aynı
jetonla yazıyor. Beyan edilen ama üretilmeyen jeton, deliği gizler
([[beyan-edilmis-survivor]] · [[ikiz-tanim-sessiz-ayrisma]]).
**HÜKÜM: `DEVRALINDI` docstring'den silinmez, KODA eklenir.** Devralma maddi olarak farklı
bir olaydır; sicilde ayrı görünmelidir.

## 2. TESLİM — `~/.claude/cron/kilit-tatbikat.py`

Tek betik; **gerçek iki SÜREÇ** (thread DEĞİL, `subprocess`/`fork` ile) aynı kilit yolunda
yarıştırılır. Geçici kilit yolu `tempfile` altında; **canlı nöbet kilidine DOKUNULMAZ.**

### Vaka T2-A — canlı rakip REDDEDİLİR

1. P1 `al()` → `KILIT_ALINDI`, sonra kilidi **5 SANİYE** tutar (uyur).
2. P1 kilidi tutarken P2 `al()` → `alindi=False`, hüküm **`ONCEKI_TUR_SURUYOR`**.
3. P1 `birak()` → `True`.
4. P2 tekrar `al()` → `KILIT_ALINDI`.

🔴 **ÇAKIŞMA KANITI ZORUNLU.** P1'in alış damgası `t1`, P2'nin ret damgası `t2`, P1'in
bırakış damgası `t3` kaydedilir ve **`t1 < t2 < t3`** iddiası betikçe DOĞRULANIR.
Bu doğrulama olmadan aynı jetonlar **sıralı** koşumda da üretilir ve tatbikat tiyatro olur;
o hâlde `CAKISMA_KANITI=HAYIR` yazılır ve batarya KIRMIZI biter.

### Vaka T2-B — artık kilit TEK KEZ devralınır

1. Kilit dosyası **ölü** bir PID ile elle yazılır (`pid_canli_mi` fikstürü o pid'e `False`
   der; gerçek süreç öldürülmez).
2. P1 `al()` → `alindi=True`, hüküm **`DEVRALINDI`** (bugün: `KILIT_ALINDI`).
3. Dosyadaki `PID=` artık P1'in pid'i.
4. **DOLU ÇALINMAZ kontrolü:** kilit CANLI bir pid ile yazılırsa `al()` → `ONCEKI_TUR_SURUYOR`
   ve dosya **DEĞİŞMEZ** (içerik hash'i aynı kalır).

### Vaka T2-C — `birak()` sahiplik denetimi

Başkasının pid'iyle yazılmış kilitte `birak()` → `False` ve **dosya DURUR** (silinmez).

## 3. HAM KANIT DOSYASI (mimarın grep'leyeceği yer)

Betik `~/.claude/cron/kilit-tatbikat-ham.log` yazar; her adım tek satır:

```
<ISO damga> VAKA=<T2-A|T2-B|T2-C> ADIM=<n> SUREC=<P1|P2> HUKUM=<jeton> ALINDI=<0|1>
```

Rapora bu dosyadan **`grep -c` çıktılarıyla birlikte** alıntı yapılır. Mimar aynı grep'i
bağımsız koşar; sayı tutmazsa o satırın hükmü DÜŞER.

## 4. KABUL (çalıştırılabilir)

```
python3 /Users/okan/.claude/cron/kilit-tatbikat.py
```

son satır + rc=0:

```
T2A_IKINCI=ONCEKI_TUR_SURUYOR T2A_BIRAK=1 T2A_TEKRAR=KILIT_ALINDI CAKISMA_KANITI=EVET T2B_HUKUM=DEVRALINDI T2B_DOLU_CALINMADI=1 T2C_BIRAK=0 T2C_DOSYA_DURUYOR=1 DUSEN=0 MUTANT=3/3
```

### Mutantlar (3/3 KIRMIZI)

* **M1** — `al()`'daki "DOLU ise reddet" kolunu kaldır → **T2-A adım 2 DÜŞER** (ikinci süreç
  kilidi çalar).
* **M2** — artık kilit yolundaki TAZE okumayı kaldır (kör silme) → **T2-B adım 4 DÜŞER**
  (canlı rakibin kilidi çalınır).
* **M3** — `birak()`'taki sahiplik denetimini kaldır → **T2-C DÜŞER**.

⚠️ Her mutant nişanlandığı vakayı TEK BAŞINA düşürmeli; birden çok ekseni yakan mutant
kanıt saymaz ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

### Kontroller (yanlış-pozitif nöbetçisi)

* **K1** — `gozcu-test.py` ve `nobet-kabul-test.py` bu değişiklikten SONRA da rc=0 kalır.
  `DEVRALINDI` eklemesi mevcut vakaları kırıyorsa **kırılan vakayı düzeltme**: hükmü
  mimara getir (mevcut vaka `KILIT_ALINDI` bekliyorsa, o beklenti bilinçli miydi
  ölçülmeli — [[test-hatali-davranisi-kutsar]]).
* **K2** — `epok_bicimi` `"%.3f"`/`"%.0f"` ayrımına DOKUNULMAZ (kilit.py:17-19 uyarısı).

## 5. CI KABLOSU (aynı dilimde — muafiyet YOK)

`kilit-tatbikat.py` `~/.claude/cron/testler.py` bataryasına eklenir (nöbet dosyaları repo
dışı olduğu için `nobet.yml` yerine kanonik yerel batarya). Raporda `testler.py` rc'si
yazılır. **Muafiyet listesine ekleme YAPILMAZ** — muafiyet "koşuyor" demek değildir.

## 6. SINIRLAR

* Canlı nöbet kilidine (`~/.claude/cron/` altındaki gerçek kilit dosyaları) DOKUNULMAZ;
  tatbikat `tempfile` altında koşar.
* `karar()` eşiği `KILIT_BAYATLIK_SN=3600` DEĞİŞTİRİLMEZ.
* `gozcu.py` bu turda DEĞİŞMEZ (K175 orada çalıştı; çakışma yok).
* Yedek zorunlu: `kilit.py` → `kilit.py.yedek-T2` (bu dizin versiyon kontrolü dışında, K146).
* Temizlik: geçici dosyalar silinir; **`kilit-tatbikat-ham.log` KALIR** (kanıt dosyasıdır),
  son satırda `TEMIZ=EVET`.

## 7. İŞÇİ TALİMATI

* **Tavan:** ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Raporu ÖNCE oluştur; başka turun raporunun ÜZERİNE YAZMA, başa EKLE.
* **Süre birimleri AÇIK:** "5 SANİYE" saniyedir. Kısaltma (`5s`) YAZMA.
* **DOKUNMA:** `urunler.json` · `crontab` · `gozcu.py` · `.github/workflows/`.
