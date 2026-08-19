# PAKET T6c + KAPANIS DOGRULAMASI (TUR 2) — damga ureticisinin KAPSAMI genisler, sonra HER SEY gercek saatle YENIDEN olculur

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

---

## 0. 🔴🔴 EN ONEMLI KURAL — HANGI AGACI OLCTUGUNU KARISTIRMA

Bu paketin 1. turu **GECERSIZ SAYILDI**, cunku komutlar `/Users/okan/dev/pruvo/tools/...`
(yani **ANA AGAC**) yollarina yazilmisti. Bu isin butun ciktisi **DALDA**, ana agaca
**MERGE EDILMEDI**. Sonuc: rapor iki agacin KARISIMI oldu ve yanlis sayilar uretti
(`SAHIPSIZ=44` — dalda 24 · `merge-kanit --eksikler` "flag yok" — dalda VAR).

**OLCULEN FARK (chip olctu):**

| | ANA AGAC `/Users/okan/dev/pruvo` | DAL (bu worktree) |
|---|---|---|
| `tools/t1-kiyas.py` | **YOK** | VAR |
| `tools/okan-kapisi-penceresi.py` | **YOK** | VAR |
| `merge-kanit.py` icinde `eksikler` | **0 vurus** | 9 vurus |
| `t3-yonlendirme-kapisi.py` icinde `_icerikten_ev` | **0 vurus** | VAR |

🔴 **BU TURDA HER KOMUT SU KOKTEN KOSULACAK:**

```
/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442
```

🔴 `/Users/okan/dev/pruvo/tools/...` yolunu **HICBIR komutta KULLANMA.**
Kosmadan once bunu bir kez KANITLA (ve ciktisini rapora yaz):

```
grep -c eksikler /Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442/tools/merge-kanit.py
```

Sonuc **0 ise** yanlis agactasin: DUR, raporla, hicbir sey kosturma.

## 1. OLCULEN OLGU (T6c'nin isi)

T6 suzgeci gercek park yuzeylerine baglandi; `--gercek` artik `KALEM=6`. Ama:

```
T6 KALEM=6 DUSTU=0 PENCEREDE=0 OLCULEMEDI=6 ESIK_SAAT=24
```

Altisi da `OLCULEMEDI`: damga ureticisi (`durgun-kalem-kapisi.py --damga-uret`)
YALNIZ `ACIK KALEMLER` bolgesini tariyor; bu alti kalem `## OKAN'DA` ve
`## 🔻 KraL SON DURUM` bolgelerinde. Fail-closed DOGRU calisiyor (ARIZA DEGIL),
ama T6 canli veride hala `DUSTU`/`PENCEREDE` gosteremiyor.

## 2. HUKUM — URETICININ kapsami genisler, TUKETICILERIN listeleri DEGISMEZ

🔴 **TEK KAYNAK BOZULMAYACAK.** Ikinci bir damga uretici ACILMAZ.

* Bolge kumesi (`ACIK KALEMLER` + `OKAN'DA` + `KraL SON DURUM`) **TEK bir sabitte**
  tanimlanir; hem `--damga-uret` hem T6 parser'i AYNI sabiti kullanir. Iki ayri
  liste birakilirsa sessizce ayrisir ([[ikiz-tanim-sessiz-ayrisma]]) — KABUL KAPISI.
  🔴 Sabit **damga ureticisinin yaninda** (`durgun-kalem-kapisi.py`) durur; T6 onu
  import eder. Tersi DEGIL — uretici T6'ya bagimli olmaz.
* 🔴 **T5'in KENDI `--gercek`/`--rapor` tablosu DEGISMEMELI:** T5 siniflandirmasi
  `kalem_listesi` (yalniz `ACIK KALEMLER`) uzerinden kosmaya DEVAM eder. Uretici
  fazladan damga uretir; T5 onlari KULLANMAZ. K5 bunu pinler.
* Damgasi turetilemeyen kalem yine `OLCULEMEDI` KALIR. Fail-open YASAK.

### 2.1 T6 `--kendini-test` KARARSIZLIGI (1. tur beyani — once BUNU olc)

1. tur "T5 entegrasyon cagrisinda bazen rc=1" dedi. 🔴 Kararsiz kabul testi kabul
   DEGILDIR. `--kendini-test`i **PESPESE 5 KEZ** kos, rc'leri yaz:
   `RC_DIZISI=<rc1,rc2,rc3,rc4,rc5>`. Besi de 0 degilse kok nedeni bul ve
   **KARARSIZLIGI GIDER** (paylasilan gecici dizin / kalintili durum dosyasi /
   sira bagimliligi). Gideremezsen `OLCULEMEDI` + SEBEP yaz, uydurma.

### 2.2 Kabul (T6c)

```
python3 <KOK>/tools/durgun-kalem-kapisi.py --kendini-test
python3 <KOK>/tools/durgun-kalem-kapisi.py --curutme
python3 <KOK>/tools/okan-kapisi-penceresi.py --kendini-test
python3 <KOK>/tools/okan-kapisi-penceresi.py --curutme
```

Mevcut sayilar **AYNEN gecmeye devam etmeli** (gerileme nobeti). Uzerine:

| # | Mutasyon | Dusmesi gereken |
|---|---|---|
| M8 | Genisletilmis bolge kumesini `ACIK KALEMLER`e geri daralt | T6'nin damga ekseni KIRMIZI; T5'in kendi tablosu YESIL kalmali |
| M9 | Uretici, damgasi turetilemeyen kaleme `simdi` yazsin (fail-open) | `OLCULEMEDI` kolu KIRMIZI; `DURGUN`/`TAZE` kollari YESIL kalmali |

🔴 **K182:** her mutant hedef kolu AYRICA kanitlar; `HEDEF_KOL_ATFI=<EVET|HAYIR>`.

| # | Kontrol | YESIL kalmali |
|---|---|---|
| K5 | T5'in `--gercek` kalem KUMESI genislemeden ONCE ve SONRA **AYNI** |
| K6 | Bolge kumesi TEK tanimdan geliyor (tanim degisince ikisi BIRLIKTE degisir) |

## 3. 🔴 SONRA: HER SEY GERCEK SAATLE YENIDEN OLCULUR (kod DEGISTIRMEZ)

Once gercek UTC saati ol ve rapora yaz:

```
python3 -c "import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())"
```

🔴 Asagidaki iki komut **`--simdi` VERILMEDEN** kosulacak. Onceki bir turda
`--simdi 2026-08-19T10:00:00Z` (gercek simdi'den ~11,5 SAAT ILERIDE) kullanilmis,
4 SAAT esigi karsisinda her kalem bayagi "durgun" cikmisti: `durgun=8 taze=0` bir
**FIKSTUR ARTIFAKTIYDI**, canli olcum DEGILDI.

```
python3 <KOK>/tools/durgun-kalem-kapisi.py --gercek
python3 <KOK>/tools/okan-kapisi-penceresi.py --gercek
```

🔴 `--gercek` kolu YOKSA aracin gercek-veri kolunun ADI NE ise onu kullan ve
**hangi kolu kullandigini yaz**; `--rapor` ile `--gercek` AYNI SEY DEGILSE bunu
belirt (1. turda bu ikisi karistirildi).

Her iki ham cikti rapora **BIREBIR**. Ayrica bir cumleyle: T5 tablosu sahte saatle
alinan `durgun=8 taze=0`'dan NE KADAR farkli; T6'da `OLCULEMEDI=6` kaca dustu.

### 3.1 Tam kabul supurgesi (hepsi; biri kirmizi olsa da digerleri kosar)

Her komut icin **komut satiri + rc + ham ciktinin son 20 satiri**:

```
python3 <KOK>/tools/t3-yonlendirme-kapisi.py --kendini-test
python3 <KOK>/tools/t3-yonlendirme-kapisi.py --sahipsiz-listele
python3 <KOK>/tools/merge-kanit.py --kendini-test
python3 <KOK>/tools/merge-kanit.py --eksikler
python3 <KOK>/tools/t1-kiyas.py --kendini-test
python3 <KOK>/tools/t1-kiyas.py --gercek
python3 <KOK>/tools/ci-kapsam-test.py
python3 <KOK>/tools/kisisel-veri-test.py
```

🔴 **BEKLENEN (dalda olculmus; SAPMA VARSA SAPMAYI YAZ, sayiyi UYDURMA):**
`t3 --sahipsiz-listele` → `SAHIPSIZ=24` (44 DEGIL; 44 gorursen YANLIS AGACTASIN) ·
`merge-kanit --eksikler` → `BIRLESIM=27 KANITLI=0 KANITSIZ=27` (flag "yok" derse
YANLIS AGACTASIN).

## 4. YAN ETKI YASAGI + TEMIZLIK

```
git -C <KOK> status --short
git -C /Users/okan/dev/pruvo status --short
git -C <KOK> reflog -n 10
```

🔴 Ana agacta BASKA oturumlarin commit'siz isi olabilir — **DOKUNMA**,
`git checkout`/`restore`/`stash` ile geri ALMA. KABUL KAPISI
([[isci-merge-blokunu-checkoutla-cozer]]). Reflog'da `checkout`/`reset` OLMAYACAK.

Defter/kutu md5 oncesi-sonrasi: `DEFTER_DEGISMEDI=<EVET|HAYIR>` ·
`KUTU_DEGISMEDI=<EVET|HAYIR>`.

🔴 **TEMIZLIK (13 Agu disk emri):** uretilen HER gecici dosya SILINIR. Onceki bir
turda `tools/.t6b-rc.py` ve `tools/.t6b-t5-kt.py` calisma agacinda BIRAKILMISTI;
tekrarlanmayacak. Kapanista `git status --short` bunu KANITLAR.

## 5. SON SATIR (makine-okunur)

```
KAPANIS AGAC=DAL KOMUT=<n> YESIL=<n> KIRMIZI=<n> OLCULEMEDI=<n> RC_DIZISI=<...> YAN_ETKI=<YOK|VAR> DEFTER_DEGISMEDI=<EVET|HAYIR> TEMIZ=<EVET|HAYIR>
```

## 6. ISCI TALIMATI (baglayici)

* Calisma agaci **YALNIZ** `<KOK>` = `/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442`.
  Ana agaca **YAZMA** ([[isci-worktree-yerine-ana-agaca-yazar]]).
* **COMMIT ATMA** — commit'i chip atar.
* `.github/workflows/nobet.yml`'e DOKUNMA · `DEVAM.md`'ye YAZMA.
* Rapor: dalda **kanonik muhendis raporu dosyasi** (bu evde tek ad, izlenmez);
  varsa BASINA damgayla EKLE, uzerine YAZMA.
* Olcemedigine `OLCULEMEDI` + SEBEP; sessiz yesil YASAK.
* Tavan ~35 tur, tek dilim. Alt ajan / paralel gorev ACMA.
