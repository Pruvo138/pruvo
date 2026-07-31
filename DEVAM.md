# DEVAM (KraL) — 31 Tem 2026. Onceki her sey DEVAM-ARSIV.md'de (git disi, lossless).

## 🔴 HESAP TASINMASI (Okan tasiniyor — devralan ONCE bunu okusun)
- **Envanter + yedek raporu KALICI:** ikisi de `raporlar/` altinda ve Drive kopyalariyla
  sha256 esitligi dogrulandi. Envanter 117 kalem, 10 asamali tasinma gunu sirasi;
  Okan'dan elle gereken 19.
- **Yedek TAMAM ve dogrulandi:** 2645 dosya / 745824642 B; eksik 0, boyut farki 0.
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
- `durum.py` dokuz artik dal listeliyor; temizlik karari verilmedi.
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

## OTURUM KAPANISI (31 Tem 2026)
- CI `serit-b` denetimi kapandi: merge `7ef7427d`; kabul 226 gecti, 0 kirmizi.
- Yedek imza dogrulamasi kapandi: merge `cdadc477`; kabul 236 gecti, 0 kirmizi;
  kill-mutant 5 kirmizi, ilgisiz degisiklik yesil; ortalama sure 0,480 sn, sinir 5 sn.
- Yedek dogrulamasi 2645 dosya / 745824642 bayt; eksik 0, boyut farki 0.
- D1'de bayat bulunan 56 kayit senkronlandi; kapanis 15930 == 15930,
  hash uyusmaz 0, eksik 0, fazla 0.
- Worktree kaydi 5'ten 1'e indi; kaldirilan uc worktree'nin commit'lenmemis isi
  yama ve tar olarak `raporlar/` altinda arsivlendi.
- Tasinma envanteri ve yedek raporu kalici yerde; Drive kopyalari sha256 esit dogrulandi.

## d1-sync HATA-YOLU MERGE'U (31 Tem 2026) — merge `7bebc166`
- Alinan dal `claude/exciting-hodgkin-91ec53` (3 commit). Kapsam merge-base `22ff3989`'dan
  OLCULDU: **1 dosya** `tools/d1-sync.py`, +431/-14. Cakisma yok, taban taze.
- Kok neden (CI run 30646713630): wrangler gercek `--json` yukunde kodu TIRNAKLI basiyor
  (`"code": 7429`); eski alt-dize tanisi 429/500/502/503/504 kollarini OLU birakmis, 7429
  listede HIC yokmus -> GECICI D1 CPU-reset KALICI islenmis, 3 denemeli retry HIC kosmamis
  ve hata zarfi parse edilemedigi icin kod ADIYLA basilamamisti.
- Kapilar (DALIN worktree'sinde, exit kodu goruldu): `--kendini-test` **104 gecti / 0 kaldi** ·
  `d1-sync-tani-test` 3/3 · `d1-sync-durum-test` 14/14 · `ci-kapsam-test` YESIL (kesfedilen 139 /
  kosulan 103 / muaf 36) · `kapi-envanteri` 7/7 · `mimar-kilit-test` 224/224 · `kod-kilidi-test`
  16/16. Hepsi exit 0.
- Merge sonrasi `d1-sync.py --durum`: D1 **15955 == 15955** benzersiz id; hash uyusmaz 0,
  eksik 0, fazla 0 (SAYI + ICERIK ekseni yesil).
- 🔴 **CI kosum 30654284096 (headSha `7bebc166`, `is-ancestor` exit 0) FAILURE** — `build` isi
  `tools/ara-maliyet-kapisi.py` adiminda dustu (`semantik sapma=3`: `%kapak`, `kapak_`, `50%`).
  `deploy` ve `yayin` SKIPPED -> bu commit YAYINLANMADI. **Sebep bu dal DEGIL**, uc ayri olcum:
  (1) dal yalniz `tools/d1-sync.py`'ye dokundu, kapi onu import etmiyor (yalniz yorum atfi);
  (2) ayni kapi yerelde merge ONCESI agacta (`e0a78925`) da merge SONRASI agacta (`7bebc166`)
  da **sapma=0 / exit 0**; (3) kapi CI'ya bir onceki commit `e0a78925` ile baglandi, onun
  kendi kosumu benim push'umla iptal olduğu icin kapinin CI'da ILK fiilen kostugu kosum bu.
  Sonuc: kapi ORTAM-BAGIMLI (yerel sqlite 3.53.3 / py3.14 YESIL, CI py3.12.13 KIRMIZI).
  Sahibi `/ara` maliyet kapisi isi (`0e0c30bd` + `e0a78925`); yayin ONUN duzeltilmesine bagli.
- OLCULEMEDI: canli site dogrulamasi (deploy SKIPPED, yayilacak yeni surum yok) · CI'daki
  sqlite surumu (kosum logu basmiyor).

## TABAN (yeniden OLC, ezberleme)
`d1-sync.py --durum` 15955 == 15955, hash/eksik/fazla 0/0/0 · `ci-kapsam` kesfedilen 139 /
kosulan 103 / muaf 36 · `kapi-envanteri` 7/7 · `mimar-kilit` 224/224 · `kod-kilidi` 16/16.
(Onceki taban satiri: 15930 == 15930 · ci-kapsam 136/100/36 · parite 1199+842 sapma 0 —
parite bu turda KOSULMADI: dal arama/worker duzlemine dokunmadi.)
