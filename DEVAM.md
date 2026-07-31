# DEVAM (KraL) — 31 Tem 2026. Onceki her sey DEVAM-ARSIV.md'de (git disi, lossless).

## 🔴 HESAP TASINMASI (Okan tasiniyor — devralan ONCE bunu okusun)
- **Envanter: `scratchpad/TASINMA-ENVANTERI.md`** — 117 kalem, 10 asamali tasinma gunu sirasi,
  her kalemde KIM SAGLAR / SAGLANMAZSA NE KIRILIR / DOGRULAMA KOMUTU. Okan'dan elle gereken 19.
  ⚠️ Bu dosya SCRATCHPAD'de = oturumla birlikte KAYBOLUR. Devralan ilk isi: kalici yere tasi.
- **Yedek TAMAM ve dogrulandi:** 2630 dosya / 745.316.384 B; eksik 0, boyut farki 0, 8/8 sha256
  esit. Once 153 dosyaydi — 4 kardes mimar + BaBa + eski arsivin **128 hafiza dosyasi** hicbir
  yerde yedekli DEGILDI, kapatildi. Arac commit `f795ff2b` main'e PUSH EDILDI.
- **`.git/hooks` klonlamayla GELMEZ** (pre-push D1 senkronu → kurulmazsa site gosterir Ege
  GOREMEZ, sessiz). Geri yukleme: `python3 tools/yedek-hook-kur.py --geri-yukle`,
  `--kendini-test` 11/11 — bos klonda kapilarin ATESLEDIGI icrayla kanitlandi.
- **YOL BAGIMLILIGI:** depolar `~/dev/pruvo{,-pazarlama,-bot,-hasat,-jenerator}` disina
  kurulursa hafiza namespace yolu + izin satirlari + launchd plist kirilir; dosyalar durur ama
  hicbir ajan OKUYAMAZ. Ayni yolu kur.
- **Diger 4 mimara tasinma talimati Okan tarafindan iletildi** (hafiza yedegi, izlenmeyen
  degerli dosyalar, sir envanteri, hook geri yukleme, dal itme, yol bagimliligi).
- 🟡 **KAYDA GECTI, DOKUNULMADI (Okan karari 31 Tem):** tasinma bitince yapilacak
  bir temizlik + anahtar yenileme isi var; ayrinti ve gerekce DEVAM-ARSIV.md'de (git disi).

## 🔴 DEVRALAN ILK 3 IS (31 Tem, oturum kota ile kapandi)
1. **CI `serit-b` KIRMIZI** — sebebi KraL'in `f795ff2b` push'u: `tools/yedekle.py` degisikligi
   `durum-yedek-test.py` capasini kirdi. **`build`+`deploy`+`yayin` SUCCESS, yayin ACIK.**
   Onarim koşuyordu, bitmediyse devam ettir. 🔴 KAPIYI GEVSETME (`continue-on-error` yok,
   iddia silme yok): capa BAYAT ise yeni gercege tasi + mutasyonla kanitla; arac BOZUKSA araci
   duzelt. Yedek kapsami DARALMASIN (taban 2630 dosya / 745.316.384 B).
2. **Scratchpad dosyalarini KALICI YAP** — `TASINMA-ENVANTERI.md`, `RAPOR-MIMARA-M-yedek.md`,
   `PLAN-metin-temizligi.json`+`d9-plan.py` `raporlar/` altina kopyalanip `yedekle.py`
   kosturulacakti. Hedefte VAR mi diye ÖLÇ; yoksa tekrarla. (Okan'a dosya olarak da gonderildi.)
3. **DEVAM.md tavani** — ≤130 satir / ≤12288 B. Tasan bloklar `DEVAM-ARSIV.md` SONUNA TASINIR
   (silme YOK). En ustteki TASINMA + FIZIKSEL URUN + bu blok KALIR.

## 🔴 YARIM IS — FIZIKSEL URUN HATTI (31 Tem 2026)
Fiziksel urun + ilk tedarikci isi: verilen kararlar, olculen durum, kapanmamis kusurlar ve
siradaki adimlar **DEVAM-ARSIV.md'de** (git disi). Devralan ORADAN devam etsin.
🔴 OKAN KAPISI (kod ACILMADAN once): (a) cayma hakki ayrimi — `mesafeli-satis` +
`teslimat-iade` sayfalari su an TEK DIL konusuyor, ayrismadan yayina GIREMEZ (hukuki risk);
(b) tedarikci sozlesmesi/sartlari. Sonra sema + d1-sync sutunu + Ege'nin agzi.

## OKAN KARARI BEKLIYOR
- **Marin taban fiyati 200 TL, Okan'in 150/210 TL karariyla CELISIYOR.** Su an sessiz cunku
  diff tabani temiz; o kayitlar tekrar bir diff'e girerse YAYINI YINE DURDURUR. Ya taban ya
  fiyatlar degismeli.

## KUYRUKTA (isci verilmedi)
- 104 kayitlik METIN TEMIZLIGI — plan HAZIR ve kendini dogrulamis:
  `scratchpad/PLAN-metin-temizligi.json` (+ `d9-plan.py`, `RAPOR-MIMARA-H-temizlik-plani.md`).
  Uygulaninca kapi vurusu 113->0; olcu satiri kaybi 0; gramer nobetcisi 0; `id`'ye 0 dokunus.
  ISCIYE: plan `python3 d9-plan.py` ile YENIDEN URETILMELI (katalog degisti); 57 baslik
  degistigi icin sonrasinda parite SART. Ana agacta, yazma->kapi->commit tek kosuda.
- `yorum-soy2` merge — kapi engeli kalkti, ama dal main'den cok geride; yeniden senkron +
  yeniden olcum sart. Kazanc: yayin JS'i 168691->113972 bayt (%32,4), 760 yorum satiri.
- Bir yayin nobetcisinde daraltilmasi gereken desen var (yuzey 663 kayit; duzeltmede yeni
  SERT 0 / UYARI 1 / yanlis-pozitif 0). Ayrinti DEVAM-ARSIV.md'de. Net kacak bugun 0.
- KaaN teslimi: `teslimler/TESLIM-HACIM-KALIBRASYON-KRAL.md` — 10 dosya cifti + `secenekler.js`
  allowlist. KraL karari: "vida ailesi PUL-only mu". Su an 13 aile ACIK / 10 KAPALI.
- 136 kayitta baslikta cevrilmemis Ingilizce — 53 oneri hazir, 264 DOKUNMA.
- OLCULMEDI: guvenilir yayin-suresi medyani · gercek cron araligi · bir kapinin kaynak
  kapsam sayisi (ayrinti DEVAM-ARSIV.md'de, git disi).

## KARARLAR (KraL)
- Ustu cizili fiyat parametrik (sari) seride KAPALI; konfigur urunler (17) kapsam disi.
- Edge kartlarinda gosterim KISMI ama fail-closed -> kabul; tam kapsam HocA'nin duzlemi.
- JSON-LD'ye `priceSpecification` EKLENMEDI.
- Bayat UPSERT de bloklanir (bedel push basina 0,8 sn, yayin yolunda DEGIL).
- `iki-govde-kapisi.py` SERIT B'den A'ya alindi — yayinlanan `secenekler.js` paritesini olcuyor,
  drift olursa site URETILEMEYEN parca teklif eder (Okan'in 29 Tem olay sinifi).
- DEVAM.md git takibine ALINDI (Okan karari 31 Tem): buraya hassas satir YAZILMAZ.
  DEVAM-ARSIV.md git DISI kalir; tedarikci/oran/sir/zafiyet ayrintisi ORAYA yazilir.

## YENI TUZAKLAR (hafizada)
- Merge aninda olen kabul testi: referansini `merge-base HEAD origin/main` ile cozen test, dal
  main'e girince totolojiye duser -> her push'ta kirmizi, ama YERELDE YESIL yanar.
  -> [[anahat-referans-tautolojisi]]
- Diske yazan mutasyon kosumu geri alinmazsa dalda CANLI mutant birakir.
  -> [[mutasyon-diske-yazma-tuzagi]]
- Merge sirasinda `urunler.json` kalintisi Okan'in 3 fiyat duzeltmesini geri alacakti; urun
  verisi main HEAD'ine sabitlenerek onlendi. Veri dalla TASINMAZ.

## TABAN (yeniden OLC, ezberleme)
`d1-sync.py --durum` 15930 == 15930, hash/eksik/fazla 0/0/0 · `ci-kapsam` 136/100/muaf 36 ·
parite 1199+842 sapma 0 · `kapi-envanteri` 7/7 · `is-akisi` etkisizlestirilmis 0 / D_IZIN 0.
