# DEVAM (KraL) — 8 Agu 2026

## 14 Agu 2026 (aksam) — MOTOR KARARI VE K103 KAPANISI (sikistirilmis)

- Motor olcumu: rc=0 oranlari 15/15 · 15/15 · 4/4; ortalama sure 343 sn · 1451 sn · 451 sn. A/B kalite olcumu YOK; olculen farklar yaklasik 4x maliyet, 4,2x hiz ve 1M sikistirma lehine.
- Gerceklesen maliyet: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar. Kalan kredi $1,27; satin alma karari OKAN'DA.
- Tarife karsilastirmasi: $20 kesin; $50 ve $19 kota OLCULEMEDI; $18 icin 187-378M TAHMIN. 13 resmi kaynak ve tam gerekce ARSIVDE.
- Arama paritesi KAPANDI: 20808/20808/20808; kontrol 365, testler 400+400. Canli surum 3daadb79; K103 KAPANDI, merge 86e3bba3, kapsam +155/-61, olculmeyen gun 1.
- K103 kabul: kapi rc=0; iki mutasyon KIRMIZI; CI kapsam rc=0; envanter rc=0; parite rc=0; katalog 27078=27078, hash sapma 0; gecici agac ve dal temiz.
- Ayrintili asil blok tam metniyle ARSIVDE.

## 14 Agu 2026 (aksam) — YAYIN VE IKI KALEM (sikistirilmis)

- Yayin 5 kosum boyunca 14:08'den beri bayatti; onarim 8b6620a9, kosum 31817146407 SUCCESS. Canli alan sayimlari 1+1; onbellek HIT, age 22, max-age 14400.
- Odeme etiketi 10 yuzeyde tasindi; eski dize 0. Merge 4a495a4a; kapi 11/11, yasal drift 0/4, oz-test 18/18, kapsam rc=0, envanter 7/7, iki sozdizimi testi gecti; uc mutasyon beklendigi gibi yargilandi.
- 🔴 OKAN DUZELTMESI (`f6404b95`, main'de): istek bastan beri TEK HARF idi (Guvenle→Guvenli);
  ben butondaki havale onekini de silmisim, geri alindi. Nihai etiket: "Havale/EFT veya Kartla
  Guvenli Ode", 10 yuzey birlikte, oneksiz dize 0. Kabul: odeme kapisi 11/11 rc=0 · mutasyon
  rc=1 · yasal drift 0/4 (tek kosumda; paralel iki kosum uretim dizininde yarisirsa build
  Errno 66 verir — ENGEL, ariza degil) · ic dil rc=0 · sozdizimi 2/2 · kapsam rc=0 ·
  not alani inputlari 1+1 YERINDE · kontrol 11 (havale beyani kilidi) KORUNDU.
- Malzeme etiketi istegi teknik yanlis beyan riski nedeniyle IPTAL; veri DOKUNULMADI.
- K101 KAPANDI: 36 tur; 15/15 rc=0 ve 343 sn, 15/15 rc=0 ve 1451 sn, 4/4 rc=0 ve 451 sn. Kalan risk: haftalik kota %45, yedek $1,27.
- Ayrintili asil blok tam metniyle ARSIVDE.

## 15 Agu 2026 (gece) — KIMI MOTORU HATTA BAGLANDI (Okan uyelik aldi)

- Dorduncu motor (aylik uyelik) isci hattina eklendi; uc, model listesi ve plan ayrintisi
  ARSIVDE. Olculen baglam 262144 — saglayicinin afisindeki daha buyuk sayi bu ucta
  DOGRULANMADI; olcum afisi yener.
- Baglama noktasi: `isci.sh` 3 + `nobet-kapi.py` 1 (hafizadaki "3+3" tahmindi). Anahtar
  dosyasi izin 600, repo DISI. M3'e ozel 1M kollari yeni motora UYGULANMADI.
- Duman testi BAGIMSIZ dogrulandi (`isci.log`): rc=0 · sure 21 sn. Isci oz-raporu DEGIL,
  hattin kendi logu okundu.
- Nobet zinciri M3 → yeni motor → DS-pro → DS-flash. Kabul `nobet-kabul-test.py` rc=0
  (VAKA=24 DUSEN=0). Gerekce: DS kredisi $1,27 ve 16 Agu'da zam → M3 kotasi dolarsa
  GERCEK yedek yoktu, artik var.
- Yeni motor gorsel okuyabiliyor (`supports_image_in`) → gorsel-okumali is verilebilir.
- Ucuncu taraf baglayicilari (belge/depo/e-posta) KURULMADI: hat yalniz API ucundan MODEL
  cagirir; gerekce ARSIVDE.
- Ikiz taramasi 1 BAYAT belge buldu — nobet gorev metni nobetciye eski zinciri anlatiyordu
  (2 satir), ikisi de olculen gercege esitlendi; sinif [[ikiz-tanim-sessiz-ayrisma]].
- Temizlik: gecici sonda dosyasi (sir tasiyordu) + 3 yedek SILINDI, mimar `ls` ile teyit etti.

## ACIK / KAPALI DURUM

- K91 KAPANDI (mimar OLCUMUYLE teyit, isci iddiasi degil): bayatlik nabzi is akisi son IKI
  kosumda da SUCCESS (`f6404b95` + `269553d5`); canli surum 34d4db64, yayinlanmamis commit 0.
- K99 ACIK: bag kolonu icin spec hazirlaniyor; uygulama kollari bekliyor.
- K100 ACIK: defter sinifinda satir-sonu muafiyet kusuru; iki yonlu vaka ile sinif onarimi BENDE.
- K101 KAPANDI: 36 turluk motor x rc/sure olcumu tamam.
- K102 ACIK: nobet yazicisi kok deftere yasakli ic dosya adini uretiyor; genel ifadeye cevrilecek.
- K103 KAPANDI: merge 86e3bba3; kabul ve temizlik tamam. (HocA'nin "kapi 13 Agu'dan beri
  cokuyor" bildirimi BAYAT cikti: onarim `a13da9df` main'de, dosya kanonik sozlesmeyi cagiriyor.)
- 🔴 K104 ACIK (bu turda OLCULDU): nobet is akisi (`nobet.yml`) son 200 kosumda 11 success /
  77 failure / 110 cancelled; son 60 kosumda 0 success; son yesil 2026-08-12T11:17Z =
  yaklasik 54 saat once. Bu surede seritteki kapilar HUKUM URETMEDI. Teshis Codex'te
  (kirmizi adim dagilimi · iptallerin kaynagi · sure ekseni); gerekce ARSIVDE; hukum MIMARDA.
- OKAN'DA: yeni tarife satin alma karari; eski yedek klasorunu backup-v2 icine surukle-birak; K89 olcum eylemi silme karari.
- 🔧 TARIFE KARAR KURALI (olculdu, Okan onayina hazir): mevcut $20 plan KALIR. Kota dolmaya
  yaklasirsa (haftalik %80 esigi mimar tarafindan izlenir) → ikinci saglayicinin $39 basamagi
  TERCIH EDILIR, cunku ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota
  duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici
  riski surer. Ikinci saglayici hala bekleme listesindeyse tek uygulanabilir yol $50 basamak
  (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi (kendi kendine ilerleyen hedef
  modu · tek tikla ajan dagitimi) bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API
  ucundan MODEL cagiriyoruz; orkestrasyon + kabul kapisi bizim tarafta. Kota sayilari iki
  adayda da yayimlanmiyor → secimi fiyat degil CESITLILIK belirliyor; sayi ancak kullanimla
  olculur. Ekleme bedeli motor basina 6 kod noktasi.

*(Arsive TASINDI — 18:07Z saatlik CI nobeti blogu, 14 Agu aksam.)*
*(Arsive TASINDI — 21:07Z saatlik CI nobeti blogu, 14 Agu gece.)*

## ARSIVE TASINAN BLOKLAR

*(Arsive TASINDI — parite kok neden ve merge blogu, 14 Agu aksam.)*
*(Arsive TASINDI — oturum kapanisi blogu, 14 Agu aksam.)*
*(Arsive TASINDI — emir 4/4 ve canli yayin blogu, 14 Agu aksam.)*
*(Arsive TASINDI — 17:37Z saatlik nobet blogu, 14 Agu aksam.)*
*(Arsive TASINDI — 15:07Z saatlik nobet blogu, 14 Agu aksam.)*
*(Arsive TASINDI — 18:40 saatlik nobet blogu, 14 Agu aksam.)*
*(Arsive TASINDI — 19:10 saatlik nobet blogu, 14 Agu aksam.)*
*(Arsive TASINDI — 17:07 saatlik nobet blogu, 14 Agu aksam.)*
*(Arsive TASINDI — 19:40 saatlik nobet blogu, 14 Agu aksam.)*

## 14 Agu 2026 (gece) — 23:07Z saatlik CI nobeti turu (sikistirilmis)
- supurme BULUNAN=2 TASINAN=2 CIKAN=2 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=378:2026-08-14T23:07:48 HUKUM=SUPURULDU; silinenler: `Run failed: Nobet seridi (SERIT B — yayini BLOKLAMAZ) - main (9e62b93)` (CS_kwDOTQTiEc8AAAAUGr2cBQ/1786736542) + `Run failed: Paket tazeligi alarmi (canli fiyat yolu) - main (c165986)` (CS_kwDOTQTiEc8AAAAUG9uDxw/1786736269). 4.7 SUPURME kapsaminda; tek duz `mail-supurme-kos.sh` rc=0; ikinci kosumda BULUNAN=0 (zaten temiz, HUKUM=TEMIZ, RC=0).
- cop denetimi (sweep-sonrasi, salt okuma): MESRU=146 YANLIS=0 KAPSAM=146 ATFEDILMEYEN=31 — 11 Agu tabani (MESRU>=140, YANLIS=0) korunuyor; sweep'in 4 fail-closed alarmindan hicbiri ateslenmedi.
- bagimsiz teyit (gh run list --limit 15): 2 failure + 1 in_progress. Kirmizilar: 31834081242 Paket tazeligi alarmi (19:37:13Z, head c165986) + 31833812927 Odeme yolu bayatlik nabzi (19:33:43Z, head c165986) — ikisi de `Olcum — canli shop worker nesli` step'i, ikisi de DURUM=BAYAT (rc=1) ve `CANLI ODEME WORKER'I BAYAT. Yayin: shop dizininden npx wrangler deploy (DEPLOY = OKAN/mimar karari)`; workflow basliklari ve step basliklari "yayini DURDURMAZ" yaziyor → 4.5 + 3.5 sinif kurali: zinciri DURDURMAZ. In_progress 31833813183 Nobet seridi (SERIT B), 19:33:44Z — SERIT B BLOKLAMAZ zaten. Build & deploy 31833812860 **SUCCESS** (head c165986, 19:33:43Z) → site canli, zincir yatay/duz. 19:33Z sonrasi **YENI kosum YOK** (son kosum 20:00:08Z D1 sapma alarmi SUCCESS); K104 Codex'te, degisiklik yok.
- DEPLOY OKAN KAPISI (4. tur, 22:37Z ile AYNI alarm): `shop-bayatlik-kapisi.py` BAYAT (rc=1). Canli `34d4db64-5b96-4294-853a-cd17e94c48a9` (14:30:20Z), bundle AYNI 2 commit (4a495a4a 16:23Z "Kartla Guvenli Ode"; f6404b95 17:22Z "Havale/EFT veya Kartla Guvenli Ode"). En eski yayinlanmamis commit yasi yeni olculunce **~257 dk** > esik 120 dk (buyume devam — 22:07Z 166 dk, 22:37Z 195 dk). `npx wrangler deploy` shop dizininden — 4.7.1 tablosu: `merge/deploy HUKMU · Okan yetkisi` → **DAGITILMAZ**, Okan kalemi; Codex da gitmez (mimarin §5 kapisi).
- 🔧 (acik-kalemler.md, son durum): onceki tur ile AYNI — K49, K53, K55 (kanama devam, Tamirci sirasi); K59, K69, K71, K77, K80, K84, K86, K96, K97 (rutin dev); K99, K100, K102 (rutin dev); K104 (54 saat, teşhis Codex'te); **DEPLOY (Okan)**. **Bu turda yeni 🔧 yok, dagitim yok, kapanan yok.**
- Okan cikisi: §5 sessiz — deploy kalemi 4 turdur ayni ve Okan-kapisi acik; defter bunu zaten tasimakta. Yeni karar isteyen durum yok.

*(Arsive TASINDI — 21:37Z saatlik CI nobeti blogu, 14 Agu gece.)*

## 14 Agu 2026 (gece) — 22:07Z saatlik CI nobeti turu (sikistirilmis)
- supurme BULUNAN=1 TASINAN=1 CIKAN=1 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=375:2026-08-14T22:07:32 HUKUM=SUPURULDU; silinen: `Run failed: Nobet seridi (SERIT B — yayini BLOKLAMAZ) - main (1ff9292)` (CS_kwDOTQTiEc8AAAAUGljx7w/1786733146). 4.7 SUPURME kapsaminda; tek duz `mail-supurme-kos.sh` rc=0.
- cop denetimi (sweep-sonrasi, salt okuma): MESRU=143 YANLIS=0 KAPSAM=143 ATFEDILMEYEN=30 — 11 Agu tabani (MESRU>=140, YANLIS=0) korunuyor; sweep'in 4 fail-closed alarmindan hiçbiri ateslenmedi.
- bagimsiz teyit (gh run list --limit 30): son kosum 31831681420 (D1 uzlastirici, 19:05:21Z success, head 9e62b93); 1 failure (31829139923 Paket tazeligi, 18:32Z — 21:37Z turunda sweep'lenmisti) + 1 in_progress (31827482236, 18:11Z, head 9e62b93) = **2 job in_progress**: `marka-bolum-bataryasi` + `model-uyelik-bataryasi` 3+ saat hareketsiz (model-uyelik normalde ~34m23s, 4.5 olcusu); serit-b failure eski — yayini BLOKLAMAZ, 3.5 sinif kurali. **19:05Z sonrasi YENI kosum YOK** — zincir aktif ama tetikleyici yok; K104 Codex'te, degisiklik yok.
- DEPLOY OKAN KAPISI: `shop-bayatlik-kapisi.py` BAYAT (rc=1), eski yas 166.4 dk > esik 120 dk. Canli `34d4db64` (14:30:20Z), bundle 2 commit (4a495a4a, f6404b95) — 21:37Z ile AYNI, degisim yok. §5 sessiz.
*(Arsive TASINDI — 22:07Z defter sinif kapisi satiri, 14 Agu gece.)*
- Okan cikisi: §5 sessiz — ne Okan karar isteyen (deploy zaten Okan-kapisi acik) ne haber-degerli durum var.

## 14 Agu 2026 (gece) — 22:37Z saatlik CI nobeti turu (sikistirilmis)
- supurme BULUNAN=1 TASINAN=1 CIKAN=1 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=376:2026-08-14T22:37:30 HUKUM=SUPURULDU; silinen: `Run failed: Odeme yolu bayatlik nabzi (push seridi) - main (c165986)` (CS_kwDOTQTiEc8AAAAUG8_3XQ/1786736055). 4.7 SUPURME kapsaminda; tek duz `mail-supurme-kos.sh` rc=0.
- cop denetimi (sweep-sonrasi, salt okuma): MESRU=144 YANLIS=0 KAPSAM=144 ATFEDILMEYEN=30 — 11 Agu tabani (MESRU>=140, YANLIS=0) korunuyor; sweep'in 4 fail-closed alarmindan hicbiri ateslenmedi.
*(Arsive TASINDI — 22:37Z defter sinif kapisi satiri, 14 Agu gece.)*
- DEPLOY OKAN KAPISI (22:07Z ile AYNI alarm, 3. tur): `shop-bayatlik-kapisi.py` BAYAT (rc=1), yeni olculen yas **194.7 dk** > esik 120 dk. Canli `34d4db64-5b96-4294-853a-cd17e94c48a9` (14:30:20Z), bundle AYNI 2 commit (4a495a4a, f6404b95). `npx wrangler deploy` ile shop yeniden yayinlanmali — 4.7.1 tablosu: `merge/deploy HUKMU · Okan yetkisi` → DAGITILMAZ, Okan kalemi; Codex da gitmez.
- 🔧 (acik-kalemler.md, son durum): onceki tur ile AYNI — K49, K53, K55 (kanama devam, Tamirci sirasi); K99, K100, K102 (rutin dev); K104 (54 saat, teşhis Codex'te); DEPLOY (Okan). **Bu turda yeni 🔧 yok, dagitim yok, kapanan yok.**
- Okan cikisi: §5 sessiz — deploy kalemi 3 turdur ayni ve Okan-kapisi acik; defter bunu zaten tasimakta. Yeni karar isteyen durum yok.

## 15 Agu 2026 — Kaynak yedegi ve ayri kasa
- Yedek sinifi fail-closed sertlesti: 0 bayt + %50'den buyuk bayt/kayit dususu RED;
  kanonik ad korunuyor, degisen dosya basina 20 tarihli surum tutuluyor.
- Davranis 3/3; oldurucu mutasyon 2/2 KIRMIZI. Ayri D1 kasa 27.939/27.939 kayit,
  icerik farki 0. Worker/wrangler izolasyonu 17 yuzeyde ihlal 0; sahte binding mutasyonu
  3 ihlalle KIRMIZI. CI kapsam kapisi rc=0.
