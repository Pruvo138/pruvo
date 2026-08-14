# DEVAM (KraL) — 8 Agu 2026

## 14 Agu 2026 (aksam) — 🔴 PARITE KOK NEDENI OLCULDU: SOZLUK VAR, DAL BAGLI DEGIL (KraL, interaktif)

**KALEM KAPANDI (teshis): site paritesi 299/300'un kok nedeni bulundu, sinif KESIN.**
Olcum Codex isciye delege edildi (salt-okuma, `DEGISTIRILEN_DOSYA=0`); hukum bende.

**SAYILAR:** `parite-test.js` rc=1 · 1328 sorgu · 3 aciklanamayan (**ucu de TEK sinif**).
- `q="arac"`: yerel **20808** · `/ara` **7826** · `workers.dev/ara` **7826** · `/ara&mod=ege` **20890**
- Kontrol terimi `q="fren"` (es-anlamlisi YOK): yerel **365** = `/ara` **365** = `mod=ege` **365**
- Diger iki sapma ayni sinif: `q="Otomobil"` 20671/20808 · `q="MX-30 arac"` 0/2
- `/katalog` sorgu KABUL ETMIYOR (her terimde `toplam=27078`, `q=null`) → sorgulanabilir uc YOK

**KOK NEDEN:** es-anlamli sozlugu (`oto/otomobil/araba/arac`) Worker'da **VAR** ama SQL'e
yalniz `mod=ege` dalinda aktariliyor; parite testinin olctugu **varsayilan `/ara` dali
genisletme YAPMIYOR**. Site kolu genisletiyor. Yani sozlugun VARLIGI, dala BAGLI oldugunu
kanitlamaz → [[ikiz-tanim-sessiz-ayrisma]] sinifi.
**"Worker bayat" ekseni KESIN OLARAK ELENDI:** es-anlamlisi olmayan terim (`fren`) uc yuzeyde
de birebir esit; bayatlik/gecikme olsaydi o da sapardi. HocA'nin tazelik olcumu DOGRU'ydu —
eksen yanlisti.

**DEVREDILDI → HocA (Worker kolu, `pruvo-bot/worker/src/index.js`):** (1) varsayilan `/ara`
dalinda genisletmenin YOKLUGU **kasit mi eksik mi** — kasitsa testin olctugu uc degisir
(bende), eksikse tek sozluk iki dala baglanir; (2) **ikinci alt-eksen:** `mod=ege` dali da
yerelle TAM esmiyor (**20890 vs 20808, 82 fark**) → "mod=ege'yi olc" tek basina kirmiziyi
KAPATMAZ.
**BENDE KALAN:** `parite-test.js` ciktisi `[site]` etiketi basiyor ama olctugu uc Worker
(`pruvo-whatsapp-bot/ara`) — etiket/ad duzeltmesi, ayri kalem.

## 14 Agu 2026 — 🔚 OTURUM KAPANISI (KraL, interaktif)

**KOSUYOR:** yok. Tum Codex delegasyonlari kapandi (13 cagri), `worktree list` **tek satir**,
ana repo **push'lu**, calisma agaci temiz (yalniz cron'un DEVAM yazimlari).

**CANLIYA GIDEN (SHA):** `116128af` boy varyanti + D1 dagitik lease + 3 olu kapi ·
`89941482` K98 fikstur capasi · `b0203209` K80 silme push'u · `6ee9ead2` K85 fikstur
bagimliligi turetimi · `86e7a035` yedek geri geldi (`backup-v2`, kok adi tek sabit) ·
`5437cb1a` sinif kapisi is-akisi adi muafiyeti · `e566e5a8` sepet butonu havaleyi de
anlatiyor · `e084df00` K80 bos girdi kolu · `d6e8881e` musteri notu + panel gruplama ·
`adc45269` E6 deseninе olcum-sonucu istisnasi · `393d4c82` K27 defter budamasi.
**Shop worker DEPLOY: VERSION 34d4db64** (Okan onayi, bayatlik 0'a indi).

**BEKLIYOR / BLOKE:**
- ~~Site paritesi 299/300 kok neden~~ → **OLCULDU, en ustteki bloga bak** (HocA'ya devredildi).
- **K99** REF ↔ siparis bag kolonu yok — **spec ArTisT'te** (Okan karari), Worker/D1 tarafi bende.
- **Defter sinif kapisi, ucuncu mesru bicim:** "is akisi ADI + kosum ID" listesi hala kirmizi
  yakiyor (bugun iki mesru bicim muaf edildi: kapi adi + olcum sonucu; ucuncusu kaldi).
  Kapatilmadan once IKI YONLU vaka yazilacak. **BENDE.**
- **K91** shop worker bayatlik alarmi — deploy bugun kosuldu, alarmin taze olcumu sonraki turda.

**OKAN'DA BEKLEYEN (1):** Drive'da eski `<Pruvo>/backup` klasoru `backup-v2/` icine
surukle-birak ile tasinacak (`os.rename` EPERM; SILINMEDI, yerinde duruyor). Yedek zaten
TAM ve dogrulanmis — bu yalniz goz duzeni.

## 14 Agu 2026 — OKAN EMRI 4/4 + 3 IS CANLIDA + SHOP DEPLOY (KraL, interaktif)

**DEPLOY (Okan onayiyla, pencere):** `shop` worker → **VERSION 34d4db64**, agac `d6e8881e`,
bundle 317.73 KiB (gzip 79.24), rc=0. Canli surum 13 Agu'dan beri bayatti; **yayinlanmamis
commit 0**'a indi (`shop-bayatlik-kapisi` rc=0). Canli dogrulama (siparis YARATMADAN):
fiyat ucu **200** + `birim_kurus` VAR · **boy varyanti kolu CANLIDA** (uydurma etiket →
**400 `gecersiz-boy`**) · panel ucu anonim **200 ama yalnizca 967 baytlik GIRIS KABUGU**
(siparis no 0 · musteri anahtari YOK · e-posta kalibi 0), veri ucu `/yonet/liste` anonim
**404**, `yonet-cerez-mutasyon.py` rc=0 → **ifsa YOK**.

**CANLIYA GIDEN:** `e566e5a8` sepet butonu havaleyi de anlatiyor (etiket UCLU BAG: index.html
+ SSS gorunen + SSS JSON-LD; alti yuzey birlikte, `odeme-beyani-kapisi` rc=0) · `e084df00`
K80 **bos** pre-push girdisi de kapsam disi (kendi yamamin eksigi: canlida "PUSH DURDURULDU"
derken commit gitmisti) · `d6e8881e` **musteri notu** (D1 kolonu ONCE canliya, kod SONRA;
**3/3** INSERT yolu; panel+Telegram+satici e-postasi; kacislama iddiasi `<img onerror>` ham
GECMIYOR) + **panel duruma gore gruplandi** (sira: incele>havale-bekliyor>odendi>uretimde>
kargolandi>tamamlandi>iptal>bekliyor>basarisiz; siralama GORUNTU katmaninda — SQL'e koysaydim
`LIMIT` yeni siparisleri dusururdu; renk TEK KAYNAK `.rozet.*`; kapsam kapisi
`TUM_DURUMLAR`dan turer).

**OKAN EMRI 4/4:** K27 DEVAM **305→68 satir / 5324 B** (arsiv 16655→**16986**, 14 blok
TASINDI) · K20 "son-zorunlu" **0 isabet** (ls-files/dal/tag/log dorttu de 0) · K33 log
**12.096.174 B silindi** (kokte log 0), ikinci sir kopyasi `.ozel` **silindi** (kanonik 291 B
dogrulandi), 2 SPEC arsive · K34 kutu **348→271** satir (arsiv 27.208).
Koktekі 3 kimlik dosyasi OLCULDU → **ucu de CANLI** (ref 40/48/17), silinmedi.

**🔴 GUNUN DORDUNCU DERSI:** *devraldigin CIKARIMI kendi olcumun sanma.* Parite kirmizisini
defterden gelen "Worker bayat" cumlesiyle acikladim; sayi bendendi ama SEBEP degildi ve
yanlis cikti. Bugun ayni sinif dort kez tekrarladi (fikstur bagimliligi · alarm cikarimi ·
kapi kapsamı · devralinan atif). Kural: **sebebi kim olctu?** diye sor.

*(Arsive TASINDI — `DEVAM-ARSIV.md`, 14 Agu aksam budamasi: "🟢 KAPANIS: YAYIN ACILDI + YEDEK
GERI GELDI" blogu + 11:10Z ve 14:14Z saatlik CI nobetleri.)*

## 14 Agu 2026 ~17:37Z — SAATLIK CI NOBETI (KraL, cron, ev=DOGRU)

SUPURME: `mail-supurme-kos.sh` → rc=0 · `GITHUB_BILDIRIM_INBOX=2 BULUNAN=2 TASINAN=2 ATLANAN=0 CIKAN=2 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=366:2026-08-14T17:38:00 HUKUM=SUPURULDU`. 2 mail (Odeme yolu bayatlik nabzi `d6e8881` · Odeme yolu bayatlik nabzi `393d4c8`), ikisi de "yayini DURDURMAZ" alarm sınıfı.
COP_DENETIM: `MESRU=134 YANLIS=0 KAPSAM=134 ATFEDILMEYEN=26` → yanlis supurme izi YOK.

CI BAGIMSIZ TEYIT (HEAD `d6e8881` "siparis formuna musteri notu + panel duruma gore gruplandi"):
- ✅ `Build & deploy 31805905402` (e084df0) **6/6 yesil** (build 8m30s · serit-a4 13s · serit-a3 18m32s · serit-a2 18m38s · deploy 37s · yayin 38s) — K98 KANAMA DURDU.
- ⏳ `Build & deploy 31808089155` (393d4c8) **in_progress** (serit-a2 + serit-a3 parallel, build+serit-a4 yesil) — §4.5 beklenen concurrency zinciri.
- ⏸ `Build & deploy 31809494632` (d6e8881) **pending** — zincirin arkasına sırada, `cancel-in-progress:false` politikası.
- ✅ `D1 sapma alarmi 31809496034` (d6e8881) · `D1 uzlastirici 31807078803` (e084df0) · `spec-*-alarmi.yml 31809494609` (d6e8881) · `Yayin erisim alarmi 31806499608` (e084df0) · `Paket tazeligi alarmi 31810737308` yesil.
- 🔴 `Odeme yolu bayatlik nabzi 31809494594` (d6e8881) — "5 adet, canli koddan YENI, oldest 814.9 dk, BAYAT"; workflow adi "(yayini DURDURMAZ)" ve "DEPLOY = OKAN/mimar karari" → K91 OKAN-KAPISI aynı sınıf.
- ⏸ `Nöbet şeridi (SERIT B) 31809494860` (d6e8881) pending — beklenen davranış, blog degil.

§4.7.1 ONARIM KAPISI: `nobet-kapi.py --tur` PID 56840 BASLANGIC 17:37:00Z (kapı çalışıyor, model katı bu görev). H7 kilidi aktif, motor zinciri akıyor.

TAMIRCI BAKIM: bagimsiz kabul sayımı —
- **K95 KAPANDI**: `model-uyelik-kapisi.py` lokal SONUC=29/29 GECTI · YARGISIZ=[]. 3 cift yargilandi (Fiat|scudo · Nissan|primastar · Peugeot|scudo).
- **K97 KAPANDI**: `ic-rapor-adi-kapisi.py --uzak` "temiz (0 ic rapor dosyasi)" 31 uzak dal agaci tarandi.
- **K98 KAPANDI**: `e084df0` Build & deploy **6/6 yesil** + `Build & deploy 31808089155` (393d4c8) zinciri akıyor. K85+K80 kök nedeni zincirde tekrarlanmıyor.
- **K96 KAPANDI (cırcır):** `c3d-audi-q3-sis-farı-montaj-braketi` id'sinin `urunler.json:3638`'de ASCII `c3d-audi-q3-sis-fari-montaj-braketi` oldugu olculdu → URL-GUVENSIZ reddi gecersiz, zincir tum HEAD'lerden gecti (e084df0 393d4c8 d6e8881). MaCiT tek-yazar alaninda defter satırı OPR/ArTisT tarafından KAPANDI yazılabilir (bagimsiz teyit yerinde).
- **K91**: OKAN-KAPISI (acik) — `cd shop && npx wrangler deploy` bekliyor, 814.9 dk bayatlik.
- **K99**: ACIK (ArTisT spec uretiyor) — degisiklik yok.
- **K89**: OKAN-KAPISI (acik) — Ads'te `page_view` eylemi silme karari.
Bu tur dagıtılan: **YOK** (kapı dağıtıyor; K96 MaCiT alanı zaten ASCII norm ile kapandı, K95/K97/K98 onarımı oncesi gerceklesmis).
OKAN'A ÇIKIŞ: YOK (§5 — her kalem kendi sınıfında yargılandı; K91 zaten OKAN-KAPISI, routine).
