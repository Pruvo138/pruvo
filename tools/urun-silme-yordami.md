# TEKİL ÜRÜN SİLME YORDAMI (Okan emri 2 Eyl 2026; Okan kuralı 6 Eki 2026)

> **OKAN KURALI (6 Eki 2026, tüm kuralların üstünde):** ① eklenen ürün GİZLENMEZ
> (`gizli` alanı yok) · ② gizlenmesi gerekecek ürün EKLENMEZ · ③ Okan'ın "sil" dediği
> ürün **TAMAMEN silinir** — gizleme / taslak / **arşiv YOK** · ④ Okan'ın sözü birebir
> icra edilir, ajan kural uydurmaz. 17 Ağu "ürün silinmez / gizle" hükmü GEÇERSİZ.
>
> Kapsam: panelden **TEKİL** manuel silme. Toplu silme ucu YOKTUR. Silinen ürünün
> içeriği (ad, açıklama, görsel listesi, fiyat, kaynak) repoda **HİÇBİR dosyada
> tutulmaz**; geri yükleme yolu YOKTUR (K437, 8 Eki 2026: `arsiv/urunler-arsiv.json`
> kaldırıldı, `tools/urun-geri-yukle.py` emekli).

## Silme akışı (tek yazım yolu — ikinci yol yok)

1. **Panel** (`/api/shop/yonet` → Ürünler → kart → **Sil**): çift onay — ürün id'si
   AYNEN yazdırılır + zorunlu kısa gerekçe. UI, `POST /urun-sil`
   (`{urun_id, onay, gerekce}`) çağırır; sunucu `onay === urun_id`'yi AYRICA doğrular.
2. **Worker** (`shop/src/yonet.js panelUrunSil`): yönetim anahtarı arkasında. Ürünün
   R2 `stl/<id>/` parçaları varsa ÖNCE `arsiv/stl/<id>/<ts>-<dosya>` anahtarına
   teyitli taşınır (teyit düşerse 502, silme kuyruğa YAZILMAZ). Sonra D1
   `panel_ustyazim` kuyruğuna `alan='sil', deger=<gerekçe>` satırı yazılır.
3. **Uygulayıcı** (`tools/panel-uygulayici.py`, CI, concurrency=1): satırı
   `duzelt.py --toplu {"id","sil":gerekçe}` ile tabandan TAMAMEN çıkarır,
   `urun-silme-defteri.json`'a **yalnız `{"id","silinme_ts","yazan"}`** ekler (aynı
   commit) ve push'tan SONRA satırı `islendi` damgalar. Aynı ürünün bekleyen alan
   düzenlemesi `URUN_SILINECEK` sebebiyle hata kovasına düşer (sessiz değil).
4. **Aramadan anında düşüş (K430, Okan emri 1 Eki 2026):** push BAŞARILI olduktan
   SONRA uygulayıcı silinen id'leri D1'de `yayinda=0`'a indirir (`d1_gizle`; SQL tek
   kaynak `yayin-kapisi.gizle_sql`, istemci `d1-sync`). Küme **alan-bağlıdır**: yalnız
   push'lanan commit'te (a) `urunler.json`'dan düşen VE (b) aynı commit'te silme
   defterine yeni giriş olarak eklenen id'ler — keyfi id listesiyle indirme YOKTUR.
   Push düşerse D1'e dokunulmaz. İndirme düşerse commit main'de kalır, satır `islendi`
   olur, çıktı `D1_GIZLE=HATA:<…>` basar ve koşum rc=1 (kırmızı); başarıda `D1_GIZLE=<n>`.
5. **Senkron (otomatik, mevcut raylar):** `build.py` ürün sayfası/sitemap/feed'i
   tabandan yeniden üretir (silinen düşer); `d1-sync` silinen satırı D1'den DELETE
   eder; uygulayıcı deploy'u `workflow_dispatch` ile tetikler.

**İkinci "Sil" idempotenttir (K430):** ürün tabanda yok ama silme defterinde varsa satır
hata DEĞİL `islendi` + sebep `ZATEN_SILINDI` olur (8 Eki öncesi satırlarda eski adı
`ZATEN_ARSIVDE`; panelde "Geçmiş"e iner; D1'e dokunmaz). Defterde de yoksa `URUN_YOK`
hata kalır.

## Silme defteri (`urun-silme-defteri.json`, K437)

- Dizi; her giriş **yalnız** `id` · `silinme_ts` (`YYYY-MM-DDTHH:MM:SSZ`) · `yazan`
  (`duzelt.py` / `panel-uygulayici`). Ürün içeriği, gerekçe, kuyruk no YAZILMAZ.
- Ne işe yarar: (1) izinli silmenin görünür izi — silme kapısı düşen id için YENİ defter
  girişi arar; (2) panel D1 indirme kümesinin (b) bacağı; (3) ikinci "Sil" tıkının
  `ZATEN_SILINDI` sınıflaması.
- Diriltme koruması (silinen id'nin tekrar eklenmesi) defterden DEĞİL git geçmişinden
  beslenir: `tools/diriltme-kapisi.py` EKSEN 1 (id ekseni) + pre-commit adım 4.

## Silme kapısı (13 Eyl 2026; içerik ekseni K437)

- `duzelt.py --sil` ve `--toplu` içindeki `"sil"` işlemi `PRUVO_URUN_SIL_IZNI=OKAN` olmadan
  **rc 8** ile reddedilir, hiçbir şey yazılmaz. Panel yolu bu izni `panel-uygulayici.py`'de
  verir (Okan'ın çift-onaylı yönetim ucu). Panel dışı izinli tekil silme (yalnız Okan'ın
  "sil" kararı): `PRUVO_URUN_SIL_IZNI=OKAN python3 tools/duzelt.py <id> --sil "gerekçe"` →
  kayıt tamamen çıkar, deftere yalnız id yazılır (`yazan: duzelt.py`); commit'e
  `urunler.json` + `urun-silme-defteri.json` birlikte girer.
- `tools/urun-silme-kapisi.py` (pre-commit adım 9 + CI `serit-a3`, son 20 first-parent commit
  penceresi): düşen her id ya ID-RENAME ya da YENİ defter girişi taşımalı; aksi KIRMIZI.
  Deftere üç alan dışında alan/biçim dışı değer yazmak ya da emekli
  `arsiv/urunler-arsiv.json`'u yazmak da KIRMIZI (`ICERIK_TASIYAN_SILME_KAYDI`).
- **SINIR (gizlenmez):** izin yerel ortam değişkenidir, bir ajan kendine verebilir. Kapı kazayı
  ve "kapıyı yeşile çevirmek için katalog budama" refleksini durdurur, kötü niyeti değil. İzinli
  silme görünür iz bırakır: defter girişi + CI `DEFTERLI_SILME <id> (yazan=...)` satırı + guard logu.
- **SINIR (gizlenmez):** repo PUBLIC ve git geçmişi yeniden yazılmaz — silinen ürünün eski
  hâli geçmiş commit'lerde (`urunler.json` ve 8 Eki öncesi arşiv) okunabilir kalır.

## Gizlilik kuralları

- **GEREKÇE public repoya YAZILMAZ** (repo PUBLIC): yalnız D1 kuyruk satırında
  (`panel_ustyazim.deger`) ve yerel `.urunler-guard.log`'da yaşar.
- Gerekçeye tedarikçi/kişi adı yazmamak yine de en temizi (D1 satırı panel kuyruk
  ekranında görünür).
- **R2 görselleri SİLİNMEZ** (mevcut kural). Gizli kaynak defteri
  (`.urun-kaynaklari.json`, git dışı) SİLME sırasında TEMİZLENMEZ — Okan'ın "istediğimde
  hemen bulunacak" intern kaydı korunur (`--kaynak-temizle` KULLANILMAZ).

## Sınırlar / bilinçli kararlar

- Eski `/urun/<id>/` URL'si için yönlendirme YOK → doğal 404.
- `panel_ustyazim` şeması DEĞİŞMEDİ (`alan` serbest metin) → migration gerekmez.
- Testler: worker yüzeyi `shop/test/urunler-panel.mjs` (M bölümü), uygulayıcı
  `tools/panel-uygulayici.py --kendini-test` (V13–V22 + M4–M13 mutantları), silme kapısı
  `tools/urun-silme-kapisi-test.py` (V1–V27 + M1–M17).
