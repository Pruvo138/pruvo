# PAKET — Edge kart alan kapsamı: `konfigur` + `tavsiyeFilament` (11 Ağu 2026)

MİMAR KARARI (KraL). Bu dosya spec'tir; icra İŞÇİNİN.

## OLAY

`0b27be8f` merge'i `tools/edge-kart-kapisi.py`'yi kırmızı yaptı (temiz export, aynı
`urunler.json`): 7fb90f71 rc=0 / alan evreni 5 → 0b27be8f rc=1 / alan evreni 7
(+`konfigur`, +`tavsiyeFilament`). Adım `serit-a3` job'unda, `continue-on-error` YOK,
`serit-a3 ∈ deploy.needs` → deploy SKIPPED.

Sebep: kapı, "sepet fiyatını/beyanını etkileyen alan" evrenini `secenekler.js`
KAYNAĞINDAN çıkarır (elle liste DEĞİL — mutant M-C bunu kanıtlıyor). Yeni
`onSecimMalzeme()` `urun.tavsiyeFilament` (293 ürün) ve `urun.konfigur` (16 ürün)
okuyor; bu iki alan `kart_ozeti`de YOKTU.

## HÜKÜM: **(b) — edge kart özetine iki alan EKLENİR.** (a) ve (c) REDDEDİLDİ.

### Kapı HAKLI, bulgu GERÇEK
Bugün davranış sapması YOK (`ONERI_ONSECIM_ACIK = false`, `onSecimMalzeme` okumalardan
ÖNCE erken dönüyor; çıktı bayt-eşit ölçüldü). Ama bayrak AÇILDIĞI gün edge modunda:
- `urun.konfigur` kartta yoksa → falsy → ölçüye özel üründe ön-seçim güvenli
  varsayılana DÜŞMEZ, panel taban tutarı kaydırır (16 ürün);
- `urun.tavsiyeFilament` kartta yoksa → ürünün kendi önerisi yerine KATEGORİ haritası
  kullanılır → başka malzeme ön-seçilir → panel sunucudan FARKLI tutar gösterir
  (293 ürün).
Bu, `tur` vakasının (ölçülen 53.270.280 krs) birebir sınıfıdır. Mühendisin raporundaki
"AÇIK KALEMLER #2 (bayrak açılırsa D1/Ege ayrışır)" ile aynı sınıftan **İKİNCİ** bir
bayrak-açma engeli. Doğru alarmı susturarak deploy açmak bu deponun defalarca ısırıldığı
desendir.

### (a) kapıyı bayrak-duyarlı yapmak — RED
1. Kapının BÜTÜN değeri evrenin KAYNAKTAN türemesi; elle/koşullu daraltma yarınki alanı
   sessizce kapsam dışı bırakır.
2. "Bu okuma ölü kod yolunda" hükmü JS'te sözdiziminde KARAR VERİLEMEZ — bu depoda
   ölçüldü ([[hukum-ezme-sozdiziminde-karar-verilemez]]: 7 AST daraltmasının hepsi ya
   sahte-kırmızı ya sahte-yeşil).
3. Daraltma TAM DA önemli olduğu anda ölür: bayrağın açıldığı gün, bu sapmayı yakalayacak
   olan kapı bizim devre dışı bıraktığımız kapıdır.
4. Gizli ön koşul üretir ("bayrağı açmadan önce kapıyı bayrak-açık modda koştur") —
   [[kapi-yan-etkisi-gizli-onkosul]] sınıfı.

### (c) `0b27be8f` revert — RED
Çıktı bugün bayt-eşit; revert CANLI riski SIFIR azaltır. Bedeli bir yeniden-merge, ve
(b) işi zaten geriye kalır. Kazanç yok.

## KAPSAM — İKİ YÜZEY, YALNIZ BİRİ BU DEPODA

**Y1 — bu depo (KraL, kapıyı yeşile çeviren):** `tools/build.py`
`kart_ozeti()` + `OZET_KART_ALANLARI`. Değer BİREBİR kopyalanır (normalize/kırpma/
sıralama YOK); değer taşımayan üründe alan HİÇ yazılmaz (`tur`/`eski_fiyat` emsali —
`ozet.json` bir bütçe dosyasıdır).
> DURUM: bu değişiklik ana ağaçta **COMMIT'SİZ** duruyor (canlı oturum yazıyor).
> Başka yazıcı build.py'ye DOKUNMAZ — "tek kritik dosyada tek yazar".

**Y2 — kardeş depo (HocA, `~/dev/pruvo-bot/worker/src/index.js` `KART_ALANLARI`):**
Kapı burayı YALNIZ ÖLÇER, asla kırmızı yakmaz (CI fresh checkout'ta ağaç yok).
🔴 Yalnız Y1 inerse kapı YEŞİL yanar ama edge modunda **Worker'dan gelen** kart hâlâ
alansızdır — aynı sapma, bu sefer CI'nın GÖREMEDİĞİ yerde. Bu, hükmü yanlış birimde
verme sınıfıdır ([[hukum-yanlis-birimde]]): Y1'in yeşili Y2'nin kapandığı anlamına
GELMEZ. Y2 yazılı açık kalem olarak HocA'ya düşer; **bayrak Y2 kapanmadan AÇILMAZ.**

## KABUL (çalıştırılabilir — hepsi ana ağaçta, çalışma ağacı hâliyle)

```
python3 tools/edge-kart-kapisi.py               # rc=0
python3 tools/edge-kart-kapisi.py --mutasyon    # 3/3 mutant KIRMIZI (M-A/M-B/M-C canlı)
python3 tools/onsecim-parite-kapisi.py          # rc=0, 54 iddia
python3 tools/sepet-secim-kapisi.py             # rc=0, 68 iddia
```
Ek ölçüm (şekil + bütçe — `OZET_KART_ALANLARI` UZADI):
- `ozet.json` boyutu `OZET_BUTCE` / `ILK_YUK_BUTCE` (500 KB) altında mı — sayıyla.
- `ozet_karti_sikistir` sondaki koşullu alanları taşımadığı için alan TAŞIMAYAN kartın
  dizi uzunluğu DEĞİŞMEMELİ (regresyon: 25.498 kartın tamamı uzarsa bütçe patlar).
- İstemci sözlükten açtığı için `index.html` kart çizimi değişmemeli — `node
  tools/parite-test.js` ve `node tools/parite-ege.js` hâlâ yeşil.
- `jenerator/test/vitrin-kabul.js` (test 8 bu ekseni ölçüyordu) hâlâ yeşil.

Y2 için kabul HocA'nın düzleminde; buradan yalnız ÖLÇÜLÜR:
`edge-kart-kapisi.py` çıktısındaki "edge Worker KART_ALANLARI ... eksik alan(lar)" satırı
`YOK` demeli.

---

# ÖLÇÜM SONUCU (11 Ağu 2026, iki turda ölçüldü — Codex işçi)

Y1 **KAPANDI**: canlı oturum `3298f1be` ile commit+push etti (`kart_ozeti` + `OZET_KART_ALANLARI`).

| kalem | sonuç |
|---|---|
| `edge-kart-kapisi.py` | **rc=0** · alan evreni 7 (boy_secenekleri, fiyat, kategori, konfigur, parametrik, tavsiyeFilament, tur) · KIRMIZI satır yok |
| `edge-kart-kapisi.py --mutasyon` | **3/3 KIRMIZI** (M-A/M-B/M-C canlı — kapsam daralmadı) |
| `onsecim-parite-kapisi.py` | rc=0 · 54 iddia |
| `sepet-secim-kapisi.py` | rc=0 · 68 iddia |
| `parite-test.js` | rc=0 · 1328/1328 |
| `parite-ege.js` | rc=0 · 894/894 |
| `jenerator/test/vitrin-kabul.js` | rc=0 · 9/9 |
| `ozet.json` bütçe | 127.324 → **127.401 bayt** (+77, %0,06) · bütçe 153.600 · **ALTINDA** |
| şekil dağılımı | 8:24.249 · 10:940 · **11:293 · 12:16** — yalnız 309 kart uzadı, kitle uzamadı |

⚠️ ÖLÇÜM TUZAĞI (tur 1'de iki kalem YANLIŞ BİRİMDE çıktı, tur 2'de düzeltildi):
- `parite-test.js` / `parite-ege.js` sandbox ağı kapalıyken `fetch failed` → rc=1 verir.
  Bu ARIZA DEĞİL, **ÖLÇÜLEMEDİ**'dir. Ağ açık koşumda ikisi de rc=0.
- `ozet.json` katalogun TAMAMI değildir (parametrik ürünler + vitrin blok havuzları + ilk 48
  kart — `tools/build.py:3803-3808, 3965-4018`). Tüm katalogu serileştirip `OZET_BUTCE` ile
  kıyaslamak 9,3 MB vs 153,6 KB gibi anlamsız bir "60 kat aşım" üretir. Doğru birim: build'in
  gerçekten yazdığı alt küme.

## AÇIK KALEM — Y2 (HocA, `~/dev/pruvo-bot`)
Ölçülen satır: `edge Worker KART_ALANLARI ... eksik alan(lar): konfigur, tavsiyeFilament, tur`.
🔴 **`tur` de eksik** — 103 fiziksel üründe 53.270.280 krş'lik o vakanın alanı, Worker
tarafında HÂLÂ kapanmamış. Bizim taraf 1 Ağu'da kapanmıştı; kapı Worker'ı kırmızı
yakmadığı için sessiz kaldı ([[hukum-yanlis-birimde]]).
Posta: `memory/mimar-posta-kutusu.md`, 11 Ağu "KraL → HocA".
**Bayrak (`ONERI_ONSECIM_ACIK`) Y2 kapanmadan AÇILMAZ.**
