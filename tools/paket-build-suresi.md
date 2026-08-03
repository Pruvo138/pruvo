# PAKET — `build` işi duvar saati: 24,8 dk → hedef ≤ 12 dk

Mimar: KraL · Açılış: 3 Ağu 2026 · Dal tabanı: `claude/unruffled-bassi-3c18c4`

## Neden

Yayın tavanı `concurrency: group: pages` yüzünden **1 deploy / build süresi**. Ölçüldü
(koşum 30838521694): `build` **1487 sn (24,8 dk · 104 adım)**, `deploy` 34 sn, `yayin` 38 sn.
Parti sırasında push aralığı 2-5 dk → push'ların ~%85'i kendi deploy'unu alamıyor, yayın
gecikmesi 26-52 dk. Eşzamanlılık ayarı doğru ve **değişmeyecek** (bkz.
`tools/deploy-aclik-kapisi.py` başlığı); tek kaldıraç `build` süresidir.

## Ölçülen profil (aynı koşum, ≥3 sn olan adımlar)

    316  Statik sayfalari uret                    <- python3 tools/build.py (TEK gerçek üretim)
    306  Yasal sayfa drift kapisi                 <- build.py üretimini AYRICA koşar, tabanı HEAD
    299  Piksel <-> katalog parite kapisi         <- render_product + feed'i AYRICA üretir
    139  Yayin kopyasi fiyat paritesi (tam kume)  <- build.py ÇIKTISINA muhtaç (urun/ + _yayin/)
     58  Yayin ic-dil kapisi                      <- üretilen çıktının yorum yüzeyi
     46  Cip satirlari capraz daralma
     43  Alt kategori taksonomisi
     ... kalan ~97 adım toplam ~280 sn (checkout 11 · setup-node 5 · pip 3 dahil)

İlk dört adım **1060 sn = %71**.

## Yaklaşım — ÖNCE PARALELLEŞTİR, SONRA (belki) DEDUPLIKE ET

**Seçilen: `build` işini, `deploy`'un HEPSİNE `needs:` ile bağlı olduğu N şeride böl.**

Gerekçe: yayın sözleşmesi AYNEN korunur — herhangi bir şerit kırmızıysa `deploy` yine
atlanır (fail-closed). Kapıların semantiğine, sırasına, tabanına DOKUNULMAZ. Duvar saati
`max(şerit)`'e düşer; kabaca 3 şeritte ~10 dk.

**Reddedilen alternatif — "build.py çıktısını bir kez üretip artefakt olarak paylaş":**
`Yasal sayfa drift kapisi`nin tabanı bilerek HEAD'dir ve kapı sayfaları kendi koşumunda
geri koyup sha256 eşitliğini kendi ölçer (deploy.yml:1226-1229). Ona build.py'nin AZ ÖNCE
yazdığı ağacı vermek karşılaştırmayı **totolojiye** çevirir — kapının yakaladığı sınıf
(sessiz drift) tam olarak kaybolur. Aynı tuzak `piksel-katalog-parite-test.py` için de
geçerli: bağımsız ikinci üretim onun iddiasının TA KENDİSİDİR. Bu yüzden dedup **varsayılan
olarak YASAK**; ancak bir adımın süresinin üretimde DEĞİL kendi döngüsünde geçtiği
ÖLÇÜLÜRSE o adım kendi içinde iyileştirilebilir.

## Zorunlu kısıtlar (ihlali = yayın bütünlüğü kaybı)

1. **`build` adı korunacak.** `tools/yayin-gecikme-nobeti.py` (YAYIN_ISI/`build`) ve
   `tools/deploy-aclik-kapisi.py` (E2 zinciri) bu adları okur. build.py üretimini yapan
   şerit `build` kalır; Pages artefakt yüklemesi O şeritte kalır.
2. **`deploy.needs` HER şeridi içerecek.** Bir şerit `deploy.needs` dışında kalırsa o
   şeritteki kapıların kırmızısı yayını durdurmaz. Bu zaten ölçülüyor:
   `tools/is-akisi-kapisi.py::_serit_b_joblar` bloklayan kümeyi `deploy.needs`'ten
   GEÇİŞLİ türetir ve kümenin dışında kalan her kapı çağrısı için `SERIT_B` tablosunda
   GEREKÇELİ bir giriş ister. Yani orphan şerit sessizce geçemez — ama yine de
   `deploy.needs` listesini elle doğrula.
3. **Sıra bağımlılığı bozulmayacak.** `urun/`, `_yayin/`, `varlik/`,
   `_yayin-icerik-dizinleri.txt`, `ozet.json`, `merchant-feed.xml` çıktılarına muhtaç olan
   HER adım, build.py ile AYNI şeritte ve ONDAN SONRA kalır. Yorum satırlarında
   "build.py'den SONRA kosmak ZORUNDA" yazan adımların tamamı bu sınıftadır — grep'le
   çıkar, tek tek sınıflandır.
4. **`fetch-depth: 0` yalnız gerektiği şeritte.** `tools/diriltme-kapisi.py` silinmiş ürün
   kümesini `git log -p --first-parent -- urunler.json` ile türetir (deploy.yml:41-49) ve
   sığ checkout'ta OLCULEMEDI (rc 2) verip yayını durdurur. Diğer şeritler varsayılan sığ
   checkout kullanabilir — kazanç ölç, yazma.
5. **`continue-on-error` KULLANILMAYACAK.** Bu depoda beyansız `continue-on-error`
   fail-open sayılır (is-akisi-kapisi Bölüm D).
6. **Hiçbir kapının çağrı satırı, argümanı ya da sırası değişmeyecek** — yalnız hangi
   `job`'da koştuğu değişir. Bu iş bir TAŞIMA işidir, kapı düzenlemesi DEĞİL.

## Kabul (çalıştırılabilir; hepsi rc 0 olmadan merge YOK)

    python3 tools/is-akisi-kapisi.py            # şerit sınıflandırması + fail-open taraması
    python3 tools/ci-kapsam-test.py             # her kapı hâlâ bir iş akışında KOŞUYOR mu
    python3 tools/deploy-aclik-kapisi.py        # E2 yayın zinciri
    python3 tools/deploy-aclik-kapisi.py --kendini-test
    python3 tools/cron-nabiz-kapisi.py --kendini-test
    python3 tools/yayin-gecikme-test.py
    python3 tools/komut-stili-kapisi.py

**Ek olarak yazılacak yeni eksen** — `tools/deploy-aclik-kapisi.py :: E2`'ye:
"build.py üretimine muhtaç HER adım, üretimi yapan işle AYNI job'da ve ONDAN SONRA"
iddiası. Çapa: adım yorumundaki "build.py'den SONRA kosmak ZORUNDA" beyanı DEĞİL —
beyan yorumdur; çapa `urun/`, `_yayin/`, `varlik/` yollarına dokunan araçların LİSTESİDİR
(kayıt tablosu + mutasyon: bir adımı yanlış şeride taşı → eksen kırmızı yanmalı).

**Ölçülen kabul:** merge'den sonra ilk yeşil koşumda `build` (ve kardeş şeritler) job
süreleri `gh api` ile okunur; **max(şerit) ≤ 12 dk** değilse iş BİTMEMİŞTİR, şerit paketleme
yeniden dengelenir. Sayı `DEVAM.md`'ye yazılır.

## Dürüst bedel

Şerit başına checkout+setup tekrarı var (~25-35 sn × N). 3 şeritte toplam runner süresi
~1487 sn → ~1600 sn (+%8); duvar saati ~1487 sn → ~600 sn (−%60). Yayın bütünlüğü için
ödenmesi gereken bedel bu değil, tersi: bu bedel ucuzdur.
