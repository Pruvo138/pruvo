# PAKET ⑤ — MERGE-KANIT TABLOSU (BaBa hukmu 18 Agu, GH-KIRMIZI duzeni)

Mimar: KraL · 18 Agu 2026 · hedef kat: ISCI (`minimax-m3` — BaBa "bagimsiz, paralel kosabilir"
dedi), kabul MIMARDA.

## 0. KABUL PROTOKOLU (BaBa doktrini, 18 Agu — AYNEN gecerli)

1. 🔴 **JETON KANITI RAPORUN ICINDE** — her sayinin `grep -c`/komut satiri raporun icine.
2. 🔴 **KABUL GREP'INI MIMAR KENDI KOSAR**; uyusmayan satirin hukmu DUSER.
3. 🔴 **VARLIK DAVRANIS DEGILDIR** — `dir()`/`ls`/"dosya var" TATBIKAT SAYILMAZ.
4. 🔴 **BIRIMLER ACIK:** `48 SAAT`, `4 SAAT`; `48s`/`4s` YASAK.
5. Olculemeyen eksene `0` yazma → `OLCULEMEDI`, rc≠0.
6. Son adim TEMIZLIK; `TEMIZ=EVET/HAYIR` raporun son satirinda.

## 1. NEDEN (olculdu, 18 Agu)

Uc arama: `merge-kanit*` dosyasi YOK · `kanit_tablosu`/`MERGE_KANIT_TABLOSU` jetonu YOK ·
bellekte yalniz K49'un "merge oncesi surucu kanit" **ILKE metni** var. Yani ilke SOZDE var,
TABLO/SISTEM olarak YOK. Sonuc: bir dal main'e alinirken hangi kabulun fiilen kostugu
hicbir yerde kayitli degil; "merge edildi" ile "kabul olculdu" ayni sey sanilyor
([[commit-mesaji-iddiasi-olcum-degildir]]).

## 2. TESLIM EDILECEK

### 2a. `tools/merge-kanit.py`

Iki kol:

* `--kaydet` — bir merge icin kanit satiri yazar. Alanlar:
  `TARIH` · `DAL` · `MERGE_SHA` · `MERGE_BASE` · `KABUL_KOMUTU` · `RC` · `SON_SATIR` · `MIMAR`.
  🔴 `RC` ve `SON_SATIR` **elle girilemez**: arac kabul komutunu KENDI kosturur ve ciktisini
  yazar. Elle deger kabul eden bir kol YAZILMAZ (beyan degil olcum).
* `--dogrula <dal>` — o dal icin kanit satiri VAR mi ve `RC=0` mi; yoksa rc≠0.

Kanit dosyasi **repo DISI**: `~/.claude/cron/merge-kanit.tsv` (public repoya girmez;
`[[diskte-iz-birakma-yasagi]]` istisnasi degil — bu KALICI is urunudur, kayit tutar).

### 2b. Kanca kolu (bu dilimde SADECE UYARI)

`kancalar/pre-push`e cagri: itilen dalin kanit satiri yoksa **stderr'e uyari basar,
BLOKLAMAZ**. Bloklayiciya cevirme karari OLCUMDEN SONRA mimarindir — bir kapiyi dogdugu
gun bloklayici yapmak kuyrukta bekleyen mesru isleri durdurur
([[kapi-birikimi-yayin-gecikmesi]]).

## 3. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/merge-kanit.py --kendini-test
```
son satir + rc=0:
```
VAKA=<n> DUSEN=0 MUTANT=3/3 KONTROL=2/2
```

### Mutantlar (3/3 KIRMIZI)
* **M1** — `--kaydet`e elle `RC` girisi kabul ettir → batarya KIRMIZI (beyan yolu acilmis olur).
* **M2** — `--dogrula` kanit satiri YOKKEN rc=0 dondursun → KIRMIZI.
* **M3** — kabul komutu kosturulamadiginda (`FileNotFoundError`) `RC=0` yazilsin → KIRMIZI;
  dogrusu `OLCULEMEDI` ve rc≠0.

### Kontroller (2/2 YESIL)
* **K1** — gercekten rc=0 uretmis bir kabul icin `--dogrula` YESIL.
* **K2** — kanit dosyasi HIC yoksa (taze makine) arac COKMEZ; `OLCULEMEDI` der, rc≠0 —
  ama `--kendini-test` bunu VAKA olarak sayar ve yesil kalir.

## 4. RAPOR (dalda, kanonik rapor dosyasinda)

Son satir + jeton kanit blogu + kanit dosyasinin ILK gercek satiri (bu dalin kendi merge'i
icin uretilmis olani) — yani arac kendi teslimini kendi tablosuna yazar.

## 5. SINIRLAR

* Bu dilim **geriye donuk** kanit URETMEZ; gecmis merge'ler icin satir uydurulmaz.
* Kardes depolar kapsam DISI.
* Kaynak kod commit'i worktree'de; is bitince worktree KALDIRILIR ve kanitlanir.
