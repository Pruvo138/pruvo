# PAKET — `uyum` yazma yolu (`tools/duzelt.py`) + K5 ikiz tanımı tek kaynaktan

**Mimar:** KraL · **Kat:** Opus (sessiz-hata sınıfı: veri yazma kapısı + şema + ikiz tanım)
**Bloke ettiği iş:** MaCiT'te 13.040 temiz `uyum` kaydı, 9 parti dosyası hazır, yazamıyor.
**Neden Codex değil:** hatası sessiz — yanlış türetilmiş `marka` arama metnini bozar, kimse görmez.

## 0. BAĞLAM (ölçülmüş, tekrar ölçme)

- `tools/duzelt.py:144` `DEGISTIRILEBILIR` 12 alan: `aciklama, altkategori, baslik, eski_fiyat,
  fiyat, gorseller, gorselsiz, kategori, konfigur, lisans, marka, tur`. **`uyum` YOK** → MaCiT'in
  1500'lük ilk partisi `rc=2` aldı, atomik doğrulama yüzünden **hiçbir şey yazılmadı** (doğru davranış).
- `tools/arama.py` gerekli her şeyi zaten veriyor: `uyum_sebebi(u)` · `marka_uyumdan_turet(u)` ·
  `uyum_kanonik(u)`. **YENİDEN YAZMA, İÇE AKTAR.** ([[ikiz-tanim-sessiz-ayrisma]])
- Katalog geneli eksen `tools/uyum-kapisi.py`'de (29 iddia, 13/13 mutant) ve KALICI. Bu paket
  yalnız **yazma yolunu** açar; katalog taraması bu paketin işi DEĞİL.
- K5 kuralı: `marka == marka_uyumdan_turet(u)` — `uyum` DOLU olan kayıtlar için. `uyum` yoksa
  eski kayıt şekli geçerli (`uyum_sebebi` None döner). Bu ayrım korunacak.

## 1. YAPILACAK

`altkategori` desenini birebir izle (`_altkategori_ihlalleri` / `_altkategori_rapor` /
`RC_ALTKATEGORI`, çağrı noktaları `duzelt.py:681` toplu ve `:854` tekil):

1. `DEGISTIRILEBILIR`'e **`uyum`** eklenir.
2. `RC_UYUM = 7` — mevcut kodlardan AYRI (görsel-köken 4 · `RC_ALTKATEGORI` 5 · `RC_TICARI_HAL` 6).
   Çağıran hangi kapının reddettiğini çıkış kodundan ayırt edebilmeli.
3. **`marka` `uyum`'dan TÜRETİLİR, elle verilmez.** Bir işlem `uyum` yazıyorsa `duzelt.py`
   `marka`yı `arama.marka_uyumdan_turet()` ile AYNI işlemde kendisi hesaplar ve yazar.
4. **Aynı çağrıda hem `uyum` hem `marka` verilmesi REDDEDİLİR** (`RC_UYUM`). İki kaynak yarışamaz.
5. `_uyum_ihlalleri(urunler, idler)` — **yazımdan HEMEN ÖNCE, YAZIM SONRASI durumda**, yalnız bu
   çağrının dokunduğu kayıtlar için `arama.uyum_sebebi(u)` koşulur; ihlal varsa çağrının TAMAMI
   atomik reddedilir, dosyaya hiçbir şey yazılmaz. Toplu ve tekil yolun İKİSİNE de bağlanır.
6. `--alan-sil uyum` GEÇERLİ kalır ve `marka`ya DOKUNMAZ (eski kayıt şekline dönüş meşrudur).

## 2. KABUL TESTİ (çalıştırılabilir, repoda kalır)

`tools/duzelt-uyum-test.py` — her madde AYRI iddia, her iddianın TEK-KIRMIZI mutantı olacak:

| # | İddia |
|---|---|
| D1 | `uyum` toplu VE tekil yolun ikisinde de kabul ediliyor (rc=0, disk değişti) |
| D2 | Yazımdan sonra `marka == marka_uyumdan_turet(u)` — türetim gerçekten koştu |
| D3 | Aynı çağrıda `uyum`+`marka` → **rc=RC_UYUM**, disk sha256 DEĞİŞMEDİ |
| D4 | `uyum_sebebi` kırmızı veren tek kayıt, 1500'lük partinin içindeyken bile TÜM partiyi reddediyor (atomik), disk sha256 DEĞİŞMEDİ |
| D5 | `uyum`u DOLU bir kayıtta yalnız `marka` değiştirmek → REDDEDİLİR (K5 sessiz ayrışması burada yakalanır) |
| D6 | `--alan-sil uyum` rc=0, `marka` aynen duruyor, `uyum_sebebi` yeşil |
| D7 | Çağrının DOKUNMADIĞI, `uyum`u zaten kirli bir kayıt çağrıyı DÜŞÜRMÜYOR (kapsam = dokunulan kayıtlar; katalog ekseni `uyum-kapisi.py`'de) |
| D8 | Dört çıkış kodu (4/5/6/7) birbirinden AYRI — her biri kendi ihlaliyle üretiliyor |

**Fikstür disiplini** ([[fikstur-degeri-mutasyon-koru]]): `marka`nın `uyum`dan türetilmişi ile
elle yazılabilecek "makul" değer AYRIŞSIN (ör. `uyum` içinde model varken yalnız markadan
türetim yanlış sonuç versin) — aksi halde "türetim hiç koşmadı" mutantı yeşil geçer.
Gerçek tedarikçi adı / firma numarası fikstüre GİRMEZ, docstring örnekleri de uydurma olacak.

**Mutasyon sürücüsü** `tools/duzelt-uyum-mutasyon.py` — repoda kalır ([[mutasyon-kaniti-yeniden-uretilebilir]]):
- Her mutant kaydında `olcut` alanı **ESIT** (kırmızı küme == beyan; fazlalık KUSUR).
  `KAPSAR` yalnız gerekçesi yazılmışsa kullanılır.
- **Beyan edilmiş SURVIVOR YASAK** ([[beyan-edilmis-survivor]]) — her eksenin TEK BAŞINA
  kırmızı yakılabilir bir mutantı olacak; yoksa o eksen ayrı iddia sayılmaz.
- En az **3 kontrol mutantı** (yeşil kalması beklenen) — çökme kırmızıyla karışmasın.
- Kaynak `sha256` başta ve sonda AYNI olacak (mutant diske sızmadı) ([[mutasyon-diske-yazma-tuzagi]]).
- Kabul = çıkış kodu DEĞİL, **ölçülen iddia sayısı + işaret şartı**.

## 3. CI BAĞI (atlanamaz)

Bu depoda bugün üç ayrı yerde "kapı var ama koşmuyor" yakalandı. Bu yüzden:
- `tools/duzelt-uyum-test.py` `.github/workflows/deploy.yml`'ye **bloklayıcı** bağlanır
  (`continue-on-error` YOK), **tam takım** çağrılır — `--kendini-test` DEĞİL.
- `python3 tools/ci-kapsam-test.py` rc=0 ve yeni dosyayı **keşfedilen + koşulan** sayacak.
- `python3 tools/kapi-envanteri.py` rc=0, envanter 7/7'den DÜŞMEYECEK (yeni kapı eklenecekse 8/8).

## 4. KAPSAM DIŞI (bu dalda YAPMA)

- Mercedes-Benz→Mercedes kanonikleştirmesi — AYRI tur, ayrı kabul testi (aşağıda karar var).
- 576 kirli kaydın kanonikleştirilmesi — AYRI tur, arama paritesi ÖNCE/SONRA ölçülmeden kapanmaz.
- 736 "marka-başı-kanonik-değil" kovası — ayrı karar turu.
- `urunler.json`'a VERİ YAZMA. Bu dal yalnız YOLU açar; 13.040 kaydı MaCiT yazar.
- D1 `uyum` kolonu (`--sema` önce) — bende, ayrı kalem.

## 5. TESLİM

Dalda `RAPOR-MIMARA.md` (başka ad YASAK, izlenen bırakılma): her iddianın ölçülen sayısı, mutant
tablosu (mutant → yakan iddia), koşulan komutların çıkış kodları, `sha256` başta/sonda,
`ci-kapsam-test.py` + `kapi-envanteri.py` rc'leri. Kırmızı varsa **commit atmadan** dur ve yaz.
