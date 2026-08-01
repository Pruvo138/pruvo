# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## 🔴 HESAP TASINMASI
- Envanter + yedek raporu kalici yerde ve Drive kopyalariyla sha256 esit dogrulandi.
  Envanter 117 kalem, 10 asamali tasinma gunu sirasi; Okan'dan elle gereken 19.
- Yedek 2645 dosya / 745824642 bayt; eksik 0, boyut farki 0.
- Yeni kurulumda yerel otomasyon ve yol bagimliliklari geri yukleme rehberine gore
  kurulup kendini-test ile dogrulanmali.
- Diger 4 mimara tasinma talimati Okan tarafindan iletildi.
- Tasinma sonrasina birakilan temizlik ve yenileme isi var; ayrinti DEVAM-ARSIV.md'de.

## 🔴 YARIM IS — FIZIKSEL URUN HATTI
- Verilen kararlar, olculen durum, kapanmamis kusurlar ve siradaki adimlar
  DEVAM-ARSIV.md'de. Devralan oradan devam etsin.
- Kod acilmadan once cayma hakki ayrimi ile ticari sozlesme/sartlar Okan kapisinda.
  Ardindan sema, katalog senkronu ve Ege entegrasyonu tamamlanacak.

## KUYRUKTA (isci verilmedi)
- Metin temizligi plani kardes mimara devredildi.
- Denetim kapisinin rapor kolunda 8 `auto_sil` ve 6 eskalasyon adayi var; bunlar
  urun verisi duzleminde.
- Parite korpusu uc ve uzeri kelimeli sorgulara yapisal olarak KOR; korpus uretimi
  gozden gecirilmeli.
- Arama maliyet kapisi su an bloklamayan seritte; Serit A'ya tasima karari acik.
- Vida ailesi icin PUL-only karari verildi; teslim kardes mimarda.

## KARARLAR
- 200 TL taban tum urunlerde gecerli; parametrik sari seri haric.
- Ustu cizili fiyat parametrik sari seride kapali; konfigur urunler kapsam disi.
- Edge kartlarinda gosterim kismi fakat fail-closed; tam kapsam kardes mimarin duzlemi.
- JSON-LD'ye `priceSpecification` eklenmedi.
- Bayat UPSERT bloklanir; yayinlanan konfigur paritesi bloklayici seritte olculur.
- DEVAM.md public ve git takibinde (`b28051b3`, 31 Tem — bilincli karar, gitignore'da tek
  istisna); DEVAM-ARSIV.md git DISI kalir. Ticari kimlik/oran/kur/sir, gizli dosya adi ve
  ic mimari ayrinti YALNIZ arsive yazilir. Ayni kural CLAUDE.md "BILGI NEREDE"
  satirinda birebir yazili; iki metin CELISIRSE olculen git durumu hakemdir.
- 1 Agu icerik denetimi: DEVAM.md'de kalan 4 sinifli blok
  maskeleme nobetcisi karsilastirmasi, kanca hata davranisi, temizlik oncesi gecmise
  isaretciler) DEVAM-ARSIV.md'ye BIREBIR tasindi, yerlerine notr isaretci birakildi.

## OTURUM KAPANISI — 1 Agu 2026 (KraL)

### CANLIYA GITTI
- `7da1124a` — toplu ekleme yolunda altkategori dogrulamasi + cikis kodu kabul testi.
  Iki commit guncel main uzerine cherry-pick ile alindi (duz merge YOK: dal tabani
  yeniden yazilmis gecmisin oncesindeydi). Kapsam 2 dosya / +286 satir; urun verisi
  dosyasi diffte YOK. Bagimsiz kosulan kabul: dal testi rc=0 / 180 iddia · altkategori
  kapisi rc=0 / 35 iddia · CI kapsam rc=0 · kapi envanteri rc=0 / 21 iddia · is akisi
  rc=0 · kisisel veri rc=0 · kanca nobeti rc=0. Eklenen 286 satir 8 desen sinifina
  karsi tarandi, 0 vurus.
- `204a076d` — izlenen kok belgeler icin icerik sinifi nobetcisi; CI `build` isinde iki
  adim. Nobetci ad-BAGIMSIZ (kok seviyedeki izlenen belge uzantilari), muafiyet listesi
  TUTMAZ. Kendini-test 62 kontrol. Kaynak daldaki metin tasimasi bayat taban uzerindeydi;
  tasima bu kayitta guncel metin uzerinde YENIDEN yapildi (asagida).
- Bu kayit — DEVAM.md tavan tazelemesi: 253 satir arsive BIREBIR tasindi (kayip 0),
  nobetci ayni agacta rc=0.

### KOSUYOR (dokunulmadi)
- `claude/exciting-hodgkin-91ec53` — muafiyet capa ekseni; oturum aktif.
- `claude/priceless-leakey-21ffb7` — mesaj nobetcisi maskeleme ekseni; ayni isin EN GUNCEL
  surumu bu dalda, oturum aktif.
- `claude/quirky-goldberg-eccb5a` — tedarikci partisi dilimi; urun verisi duzlemi, oturum aktif.
- `claude/infallible-ishizaka-004812` — oturum aktif; ucu main'de.
- `worktree-agent-afa00ca5cf9f4d429` — geri-donus kapisi CI kolu; worktree kilitli.
- `claude/muafiyet-govde-ekseni` — worktree'sinde commit'siz is duruyor; DOKUNULMADI.
- `claude/lucid-kowalevski-d55b94` · `worktree-agent-a58a9edefc8743899` ·
  `worktree-agent-a374f4375e63c16c3` — ayni nobetci isinin ESKI kopyalari; guncel superset
  yukarida. Icerik kaybi riski yok, temizlik o isin sahibine birakildi.
- `codex/toka-jenerator` · `toka-listeleme` — jenerator duzlemi, bu evin isi DEGIL.
- `koru/faz3-edge-arama` — bayrak kapali, park edilmis.
- `g2-yedek-333ac826` — onizleme kapisinin eski yedek dali; ayni is main'de iki onarim
  turu ILERIDE, yine de yedek oldugu icin silinmedi.

### BEKLIYOR
- OKAN: fiziksel urun hattinda cayma hakki ayrimi + ticari sozlesme/sartlar.
- OKAN: hesap tasinmasinda elle gereken 19 kalem.
- MIMAR KARARI: arama maliyet kapisinin bloklayan serite tasinmasi.
- ISCI VERILMEDI: denetim kapisi rapor kolundaki adaylar (urun verisi duzlemi).
- KARDES MIMAR: vida ailesi PUL-only teslimi, metin temizligi plani.

## TABAN (yeniden olc, ezberleme)
- Katalog: D1 sayi ekseni 16542 == 16542; icerik ekseni birebir, uyusmaz 0 / eksik 0 / fazla 0.
- Calisma alani: 6 worktree, 13 yerel dal (kapanista 3 worktree + 8 olu dal temizlendi).

## EK — mesaj-nobeti kirmizisi: geri-donus kapisi kapandi (1 Agu, kapanis ek kaydi)

- mesaj-nobeti kirmizisinin ikinci sebebi kapandi: geri-donus kapisi taban cozumu
  onarildi (`f85ca982`, S1).
- Kok sebep: force-push sonrasi olay yukundeki `before` nesnesi YETIM kaliyordu;
  `fetch-depth: 0` yetmez (nesne hicbir ref'te degil). Cozum: `cat-file -e` patlayinca
  yedege dusmeden once `git fetch --no-tags <uzak> <sha>` ile nesneyi kurtar (yalniz CI;
  kanca kolu bu yola girmez). Fetch basarisizsa davranis aynen eskisi.
- Olculen: yedek 50 commit penceresi 231140 aday = butcenin %154'u (yapisal asim);
  dogru menzil 18 commit / 67998 aday (%45,3). Gercek itmeler: medyan 1, p95 4, maks 45.
- Kirpma (`f416842d`, paralel oturum) KORUNDU ama artik SESSIZ DEGIL: kirpildiginde
  taranmayan commit + aday sayisi basiliyor, "temiz" hukmu EKSIK OLCUMLU oldugunu soyluyor.
- Kabul: kapinin kendini-testi 49 vaka / 0 hata (40 -> +9); mutasyon bataryasi 17/17
  olduruculu OLDU, 3/3 ilgisiz yesil.
- CI teyidi: kosum 30695623857, `mesaj-nobeti` **success**, taban COZULDU
  (yedege dusmedi), taranan 1 commit / 1789 aday = butcenin %1,2'si.
- NOT: o kosumda `before` yetim DEGILDI (saglikli hal); yetim-kurtarma yolunun gercek
  GH Actions ortaminda calistigi ayni job'un kendini-test adiminda goruldu (vaka 12c).
- Butce (150000) ve yedek pencere (50) BILEREK degistirilmedi.


## MERGE — marka muafiyeti kayitli alan adi govdesinden (1 Agu, olculdu)

- Merge `f6840e3f` (taban `11334fef`, dal tek commit `b85f5b4b`). Kapsam TAM 2 dosya,
  +259 / -4. Cakisma YOK. Kendi sizinti taramam: 6 desen sinifinda 0 vurus.
- **Sorun:** muafiyet host'un ILK etiketinden okunuyordu. Olculdu (n=1294 katalog
  markasi, alan adi ekseni tek basina): marka etiketi one alinmis bayi bicimi
  **1294/1294 gecer** (kacak tamamen acik), on ekli mesru marka adresleri
  **1293/1294 durur** (yanlis-pozitif). Batarya bu ekseni HIC olcmuyordu.
- **Cozum:** muafiyet kayitli govde etiketinden turer; ikinci seviye kayit ekleri
  icin bir ust etikete bakilir. Kacak yonu **1294 -> 0**, cok parcali uzantili
  bicimde **1294 -> 0**, yanlis-pozitif **1293 -> 0**, duz marka tabani
  **1294/1294 degismedi**.
- **Beyan edilmis takas:** ters bicim (alt alan marka sahibinin kayitli alani
  altinda) **1/1294 -> 1294/1294**, cok parcali uzantida **0 -> 1294/1294**. Gerekce
  kodda: o alan yalniz marka sahibinin tekelinde; ad ozet artefaktindaysa ikinci hat
  tutar. Ikinci hattin iki ekseni ve tireli yazimdaki kalinti olcumle yazildi.
- **Dokunulmayan:** maskeleme ve desen dilim taramasi fonksiyonlarinin govdeleri main
  ile **birebir ayni** (sha256 karsilastirildi); degisen tek kod satiri muafiyet kolu.
- **Kabul:** kendini-test **84 -> 95** iddia rc=0; mutasyon **28/28 oldurucu OLDU**,
  3/3 ilgisiz kontrol yesil, sag kalan 0, canli dosya sha256 esitligi TAM.
  Yedi kapi rc=0 (kendini-test, kaynak-tara, ci-kapsam 149/113/36, kapi envanteri 7/7,
  kanca nobeti 12 eksen 12 yesil, kisisel veri testi, mutasyon).
- **D1 teyidi:** sayi ekseni 16542 == 16542; icerik ekseni 16542 urun_hash birebir,
  uyusmaz 0 / eksik 0 / fazla 0.
- **Temizlik:** merge edilen worktree + dali silindi (uc on kontrol temiz). Baska bir
  oturumun aktif agaci ve dali KORUNDU, dokunulmadi.
- 🔴 **OLU DAL — DIRILTMEYIN:** bu isin ILK turu eski taban uzerinde kurulmus bir dalda
  yapilmisti ve **merge EDILMEDI**. Sebep: (a) taban gecmis yeniden yaziminin
  oncesindeydi, duz merge temizlenmis adlari public gecmise geri getirirdi; (b) o dalin
  maskeleme onarimi main'de zaten VARDI ve main surumu daha guclu (fail-closed) idi,
  merge GERILEME olurdu. Is guncel main uzerine YENIDEN turetildi; alinan surum budur.
  O dal artik ISLEVSIZ.
