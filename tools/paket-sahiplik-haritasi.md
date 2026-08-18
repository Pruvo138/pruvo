# PAKET ③ — SAHIPLIK HARITASI (BaBa hukmu 18 Agu, GH-KIRMIZI duzeni)

Mimar: KraL · 18 Agu 2026 · hedef kat: ISCI (ucuz), kabul MIMARDA.
BaBa sirasi: **③ ILK** — T3 (kirleten-onarir yonlendirmesi) bu haritanin USTUNE kurulur.

## 0. KABUL PROTOKOLU (BaBa doktrini, 18 Agu — HER pakette AYNEN gecerli)

1. 🔴 **JETON KANITI RAPORUN ICINDE.** Rapora yazdigin HER sayi icin, onu ureten
   `grep -c` / komut satirini **raporun kendi icine** yapistir. Ham dosyaya atif YETMEZ.
2. 🔴 **KABUL GREP'INI MIMAR KENDI KOSAR.** Raporundaki sayilar mimarin bagimsiz
   `grep -c` kosumuyla uyusmazsa o satirin hukmu DUSER (18 Agu vakasi: bir isci
   `KILIT_ALINDI=1` yazdi, ham dosyada `grep -c` → 0).
3. 🔴 **VARLIK DAVRANIS DEGILDIR.** `dir()`, `ls`, "dosya var" ciktisi TATBIKAT SAYILMAZ.
4. 🔴 **BIRIMLER ACIK YAZILIR:** `48 SAAT`, `4 SAAT` — `48s`/`4s` kisaltmasi YASAK.
5. Olculemeyen eksene `0` yazma → `OLCULEMEDI`, rc≠0.
6. Son adim TEMIZLIK: gecici dosyalar silinir, `TEMIZ=EVET/HAYIR` raporun son satirinda.

## 1. NEDEN (olculdu, 18 Agu)

Uc ayri arama (dosya adi · icerik jetonu · esanlamli jeton) sonucu: **sahiplik haritasi YOK.**
`build.py`'deki "harita" marka-slug haritasidir, sahiplik degil. Sonuc: bir kapi kirmizi
yandiginda "bu kimin isi" sorusunun MAKINE cevabi yok; kirmizi sahipsiz kaliyor
(canli ornek: `is-akisi-kapisi.py` main'de gunlerce "acik kalem, sahibi yok" diye durdu).

## 2. TESLIM EDILECEK

### 2a. `tools/sahiplik-haritasi.tsv` (IZLENEN, sekmeyle ayrilmis)

Kolonlar: `MEKANIZMA` · `YOL` · `EV` · `SERIT` · `KABUL_KOMUTU`

* `MEKANIZMA` — kanonik ad (dosya adindan turetilmez, ELLE verilir).
* `YOL` — repo-goreli yol; `~/.claude/cron/` altindakiler `cron:` onekiyle.
* `EV` — `KraL` · `MaCiT` · `TeKiN` · `ArTisT` · `HocA` · `BaBa` · `ORTAK`.
* `SERIT` — `yayin` · `veri` · `nobet` · `hijyen` · `arac`.
* `KABUL_KOMUTU` — o mekanizmayi olcen calistirilabilir komut, ya da `YOK`.

🔴 `EV` ve `KABUL_KOMUTU` icin **tahmin YASAK**. Bilinmiyorsa `EV=BILINMIYOR`
ve satir raporun "SAHIPSIZ" listesine yazilir — bos birakma, uydurma.

### 2b. `tools/sahiplik-kapisi.py`

Invaryant: **`tools/` ve `~/.claude/cron/` altindaki her KAPI/NOBET betigi haritada
BIR satira sahiptir.** Kapsam evreni ad desenine DEGIL, olculebilir bir olcute baglanir
(oneri: dosya icinde `sys.exit(1)` ile RED ureten ya da `permissionDecision` yazan betikler;
olcutu spec'e degil KODA yaz ve raporda gerekcelendir → [[kapsam-evrenini-cagri-grafindan-turet]]).

* Haritada olmayan betik → **RED**, betigin adiyla.
* Haritada olup diskte olmayan satir → **RED** (bayat satir).
* `EV=BILINMIYOR` satiri → RED DEGIL, ama sayilir ve basilir (`SAHIPSIZ=<n>`).

## 3. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/sahiplik-kapisi.py --kendini-test
```
son satir + rc=0:
```
EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=0 SAHIPSIZ=<n> MUTANT=3/3 KONTROL=2/2
```

### Mutantlar (3/3 KIRMIZI)
* **M1** — haritadan bir satiri sil → o betik `EKSIK` olarak RED almali.
* **M2** — haritaya var olmayan bir yol ekle → `BAYAT` RED.
* **M3** — kapsam evrenini bos kumeye indir → `EVREN=0` ile YESIL DONMEMELI
  (`OLCULEMEDI`, rc≠0). Bos evren yesil degildir.

### Kontroller (2/2 YESIL)
* **K1** — haritadaki normal bir satir RED uretmez.
* **K2** — `EV=BILINMIYOR` satiri kapiyi KIRMIZI yakmaz (yalniz sayilir).

## 4. RAPOR (dalda, kanonik rapor dosyasinda)

Yukaridaki son satir + **jeton kanit blogu** (her sayinin `grep -c` komutu ve ciktisi) +
`SAHIPSIZ` listesi (mekanizma adlariyla). Sahipsiz satirlar mimarin hukmune kalir; isci
sahip ATAMAZ.

## 5. SINIRLAR

* Kardes depolar (`pruvo-hasat`/`-bot`/`-pazarlama`/`-jenerator`) BU dilimde kapsam DISI;
  harita yalnizca bu evi ve `~/.claude/cron/`u kapsar. Genisletme ayri dilim.
* Kaynak kod commit'i **worktree'de** (`mimar-kod-kilidi`); is bitince worktree KALDIRILIR
  ve kaldirildigi `git worktree list` ciktisiyla kanitlanir.
