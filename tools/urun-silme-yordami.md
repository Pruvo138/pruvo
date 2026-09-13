# TEKİL ÜRÜN SİLME + GERİ YÜKLEME YORDAMI (Okan emri 2 Eyl 2026, BaBa çerçevesi ①–⑤)

> Kapsam: panelden **TEKİL** manuel silme. **Toplu silme ucu YOKTUR ve AÇILMAZ**
> (`okan-hukmu-urun-silinmez` toplu düzlemde geçerli kalır). "Gizle" ile karışmaz:
> `gizli:true` ürünü yayından düşürür ama TABANDA bırakır; "Sil (arşive)" kaydı
> tabandan **arşiv düzlemine taşır** (yok etmez).

## Silme akışı (tek yazım yolu — ikinci yol yok)

1. **Panel** (`/api/shop/yonet` → Ürünler → kart → **Sil (arşive)**): çift onay —
   ürün id'si AYNEN yazdırılır + zorunlu kısa gerekçe. UI, `POST /urun-sil`
   (`{urun_id, onay, gerekce}`) çağırır; sunucu `onay === urun_id`'yi AYRICA doğrular.
2. **Worker** (`shop/src/yonet.js panelUrunSil`): yönetim anahtarı arkasında
   (EGE anahtarı açamaz). Ürünün R2 `stl/<id>/` parçaları varsa ÖNCE
   `arsiv/stl/<id>/<ts>-<dosya>` anahtarına **arşiv-teyitli taşınır** (put→head
   teyit→delete; teyit düşerse 502, silme kuyruğa YAZILMAZ). Sonra D1
   `panel_ustyazim` kuyruğuna `alan='sil', deger=<gerekçe>` satırı yazılır.
3. **Uygulayıcı** (`tools/panel-uygulayici.py`, CI, concurrency=1): satırı
   `duzelt.py --toplu {"id","sil":gerekçe}` ile tabana işler (guard sil-manifesti
   duzelt'ten miras), **TAM taban kaydını `arsiv/urunler-arsiv.json`'a ekler**
   (aynı commit) ve push'tan SONRA satırı `islendi` damgalar. Aynı ürünün bekleyen
   alan düzenlemesi `URUN_SILINECEK` sebebiyle hata kovasına düşer (sessiz değil).
4. **Senkron (otomatik, mevcut raylar):** `build.py` ürün sayfası/sitemap/feed'i
   tabandan yeniden üretir (silinen düşer); `d1-sync` silinen satırı D1'den DELETE
   eder (6 eksen tutarlı); uygulayıcı deploy'u `workflow_dispatch` ile tetikler.

## Silme kapısı (13 Eyl 2026) — panel dışı yol ve dürüst sınır

- **Varsayılan çare silme DEĞİL, gizlemedir:** `python3 tools/duzelt.py <id> --alan gizli --deger true`.
- `duzelt.py --sil` ve `--toplu` içindeki `"sil"` işlemi `PRUVO_URUN_SIL_IZNI=OKAN` olmadan
  **rc 8** ile reddedilir, hiçbir şey yazılmaz. Panel yolu bu izni `panel-uygulayici.py`'de
  verir (Okan'ın çift-onaylı yönetim ucu). Panel dışı izinli tekil silme (yalnız Okan kararı):
  `PRUVO_URUN_SIL_IZNI=OKAN python3 tools/duzelt.py <id> --sil "gerekçe"` → kayıt
  `arsiv/urunler-arsiv.json`'a **taşınır** (`yazan: duzelt.py`); commit'e iki dosya birlikte girer.
- `tools/urun-silme-kapisi.py` (pre-commit adım 9 + CI `serit-a3`, son 20 first-parent commit
  penceresi): düşen her id ya ID-RENAME ya da **tam içeriği birebir aynı** YENİ arşiv girişi
  taşımalı; aksi KIRMIZI. Kırmızı çıktı izin reçetesini basmaz.
- **SINIR (gizlenmez):** izin yerel ortam değişkenidir, bir ajan kendine verebilir. Kapı kazayı
  ve "kapıyı yeşile çevirmek için katalog budama" refleksini durdurur, kötü niyeti değil. İzinli
  silme görünür iz bırakır: arşiv girişi + CI `ARSIVLI_SILME <id> (yazan=...)` satırı + guard logu.

## Gizlilik kuralları

- **GEREKÇE public repoya YAZILMAZ** (repo PUBLIC): yalnız D1 kuyruk satırında
  (`panel_ustyazim.deger`, `kuyruk_id` ile bulunur) ve yerel `.urunler-guard.log`'da
  yaşar. Arşiv kaydı yalnız `{silinme_ts, yazan, kuyruk_id, kayit}` taşır.
- Gerekçeye tedarikçi/kişi adı yazmamak yine de en temizi (D1 satırı panel kuyruk
  ekranında görünür).
- **R2 görselleri SİLİNMEZ** (mevcut kural). Gizli kaynak defteri
  (`.urun-kaynaklari.json`) SİLME sırasında TEMİZLENMEZ — Okan'ın "istediğimde
  hemen bulunacak" intern kaydı korunur (`--kaynak-temizle` KULLANILMAZ).

## Geri yükleme (BaBa ②: geri-getirme yolu tanımlı)

```
python3 tools/urun-geri-yukle.py <id> --gerekce "kisa gerekce"
git add urunler.json .diriltme-izin.json
git commit -m "<id>: arsivden geri yuklendi"
git push
```

- Araç arşivdeki **en yeni** kaydı `urunler.json`'un BAŞINA ekler (yeni ürün
  kuralı), `.diriltme-izin.json`'a id-düzeyinde beyan yazar — `diriltme-kapisi`
  EKSEN 1 bu beyanla YEŞİL kalır (kapı GEVŞETİLMEZ, kendi beyan yolu kullanılır).
- Arşiv kaydına dokunulmaz (append-only tarih). STL'i geri istersen R2'de
  `arsiv/stl/<id>/...` anahtarından `stl/<id>/<dosya>`'ya kopyala (panel
  "STL/3MF yükle" de kullanılabilir).
- Push sonrası D1 (pre-push senkronu) ve site (CI deploy) kendiliğinden döner.

## Sınırlar / bilinçli kararlar

- Eski `/urun/<id>/` URL'si için yönlendirme YOK → doğal 404 (940-gizleme SEO
  hükmüyle aynı sınıf; `duzelt.py --yeni-id` kolundaki bilinen boşlukla aynı).
- `panel_ustyazim` şeması DEĞİŞMEDİ (`alan` serbest metin) → canlıda migration
  gerekmez; worker deploy'u yeterli (deploy = Okan kapısı).
- Testler: worker yüzeyi `shop/test/urunler-panel.mjs` (M bölümü), uygulayıcı
  `tools/panel-uygulayici.py --kendini-test` (V13–V15 + M4/M5 mutantları),
  geri yükleme `tools/urun-geri-yukle.py --kendini-test`.
