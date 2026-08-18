# PAKET DOGRULAMA — BAGIMSIZ KABUL KOSUMU (uygulayan isci DEGIL, BASKA isci kosar)

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

---

## 0. NEDEN — bu tur neden AYRI bir isciye veriliyor

Bu evde kural: *"isci ozeti ham dosyayla desteklenmeden HICBIR tabloya girmez ve
kabul grep'ini MIMAR kendi kosar."* Mimar bu oturumda kabul komutlarini kendi
kosturamiyor (icra kapisi), bu yuzden kabul **uygulamayi YAPMAMIS** bir isciye
kosturulur. Bu tur **HICBIR KOD DEGISTIRMEZ** — yalniz kosar ve ham ciktiyi yazar.

🔴 Bu turda gorulen bir kusuru **ONARMA**. Raporla ve DUR. Onarim ayri dilim.
🔴 Sayilari spec'ten KOPYALAMA. Ne cikarsa **O** yazilir; beklenen deger YOK.
🔴 Bir komut cokerse/kosmazsa `OLCULEMEDI` + SEBEP + tam hata metni yazilir;
   atlanip sessizce gecilmez.

## 1. KOSULACAK KOMUTLAR (SIRAYLA, hepsi; biri kirmizi olsa da digerleri kosar)

Her komut icin rapora: **komut satiri + rc + ham ciktinin SON 20 SATIRI** (kisa
ciktilarda tamami). Ozet tek basina kabul DEGILDIR.

```
python3 /Users/okan/dev/pruvo/tools/durgun-kalem-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/durgun-kalem-kapisi.py --curutme
python3 /Users/okan/dev/pruvo/tools/t3-yonlendirme-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/t3-yonlendirme-kapisi.py --sahipsiz-listele
python3 /Users/okan/dev/pruvo/tools/merge-kanit.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/t1-kiyas.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/t1-kiyas.py --gercek
python3 /Users/okan/dev/pruvo/tools/okan-kapisi-penceresi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/okan-kapisi-penceresi.py --curutme
python3 /Users/okan/dev/pruvo/tools/kisisel-veri-test.py
```

Bir arac HENUZ YOKSA (`t1-kiyas.py` / `okan-kapisi-penceresi.py` teslim edilmemis
olabilir): `YOK` yaz, `OLCULEMEDI` say, DIGERLERINE DEVAM ET.

## 2. 🔴 EN KRITIK ADIM — T5 CANLI TABLOSU **GERCEK SAATLE**

Onceki tur `--gercek` kolunu **`--simdi 2026-08-19T10:00:00Z`** ile kosmus. O damga
gercek simdi'den yaklasik **11,5 SAAT ILERIDE**; 4 SAAT esigi karsisinda her kalem
bayagi "durgun" cikar. Rapordaki `durgun=8 taze=0` bir **FIKSTUR ARTIFAKTIDIR**,
canli olcum DEGILDIR.

**YAPILACAK:** once gercek UTC saati ol, sonra `--gercek`'i **`--simdi` VERMEDEN**
(arac kendi saatini kullansin) kos:

```
python3 -c "import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())"
python3 /Users/okan/dev/pruvo/tools/durgun-kalem-kapisi.py --gercek
```

🔴 `--gercek` **`--simdi` kabul ediyor ve varsayilani gercek saat DEGILSE** bunu
`OLCULEMEDI` olarak raporla ve gerekcesini yaz — gelecege ayarli varsayilan bir
saat, kapinin canli olcumunu SESSIZCE gecersiz kilar (tam da bu turda yakalanan
kusur). Ham cikti + su son satir rapora BIREBIR girer:

```
DAMGA_URETILDI=<n> DAMGA_URETILEMEDI=<n> NEDEN_GIT_IZI_YOK=<n> NEDEN_DEFTER_GITSIZ=<n>
kalem_sayisi=<n> durgun=<n> taze=<n> olculemedi=<n>
```

Ayrica **GERCEK SAAT** ile **once kullanilan sahte saat** arasindaki farki ve
tablonun degisip degismedigini bir cumleyle yaz.

## 3. YAN ETKI YASAGI — kanitlanacak

Bu tur hicbir kalici dosyayi degistirmemeli. Kapanista **kanitla**:

```
git -C /Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442 status --short
git -C /Users/okan/dev/pruvo status --short
git -C /Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442 reflog -n 10
```

Beklenen: calisma agacinda **kod degisikligi YOK** (yalniz izlenmeyen rapor
dosyasi olabilir), ana agac **BOS**, reflog'da `checkout`/`reset` **YOK**.
Son satirda: `YAN_ETKI=YOK` ya da `YAN_ETKI=VAR` + tam liste.

Ayrica gercek defter ve gercek durum dosyasi degismedi mi:
`DEFTER_DEGISMEDI=<EVET|HAYIR>`.

## 4. SON SATIR (makine-okunur)

```
DOGRULAMA KOMUT=<n> YESIL=<n> KIRMIZI=<n> OLCULEMEDI=<n> YAN_ETKI=<YOK|VAR> DEFTER_DEGISMEDI=<EVET|HAYIR>
```

## 5. ISCI TALIMATI (baglayici)

* 🔴 **HICBIR KOD DEGISTIRME.** Kusur gorursen RAPORLA ve DUR.
* Calisma agaci `/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442`.
  Ana agaca (`/Users/okan/dev/pruvo`) **YAZMA**.
* **COMMIT ATMA.**
* Baska oturumun kirli dosyasina DOKUNMA; `git checkout`/`restore` ile kimsenin
  commit'siz isini geri ALMA — KABUL KAPISI ([[isci-merge-blokunu-checkoutla-cozer]]).
* Rapor: dalda **kanonik muhendis raporu dosyasi** (bu evde tek ad, izlenmez);
  varsa BASINA damgayla EKLE, uzerine YAZMA.
* Tavan ~25 tur. Alt ajan / paralel gorev ACMA.
