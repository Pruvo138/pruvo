# pruvo-onizleme — sari seri 3D onizleme (Faz C pilot)

Is paketi: `tools/paket-onizleme-3d.md`. Mimari: urun sayfasi "Onizle (3D)" →
`POST /api/onizleme/olustur` → Worker (sema kapisi + R2 onbellek + hiz siniri) →
DERLEYICI (Cloudflare Container'da OpenSCAD) → gzip binary STL → `jenerator/viewer.js`.

## Parcalar

| Parca | Yer | Not |
|---|---|---|
| Worker | `onizleme/src/index.js` | sema kapisi = konfigurator.js + shop/src/semalar.js (tek kaynak) |
| Derleyici adaptoru | `onizleme/src/derleyici.js` | Container'a gecis SADECE bu dosya + wrangler.toml |
| Derleme servisi | `onizleme/derleyici/server.py` | generic, sir icermez; Container iminda calisir |
| GIZLI eslem+scad paketi | R2 `pruvo-ozel/onizleme/paket-guncel.tar.gz` | `tools/onizleme-paket-yukle.py` yukler; yerelde gitignore'lu `onizleme/derleyici/eslem-ozel.json` |
| Viewer | `jenerator/viewer.js` | kutuphanesiz WebGL; deploy.yml beyaz listesinde |
| Musteri bayragi | `secenekler.js` `ONIZLEME_3D_ACIK` (+ `ONIZLEME_AILELER`) | bugun `false`; acilinca build.py butonu basar |
| Imaj CI | `.github/workflows/onizleme-imaj.yml` | SADECE elle tetik; paketi gizli R2'den ceker |

## Kabul testleri

```
node onizleme/test/kabul.js        # 4a 4b 4c 4d 4f (+yerel gecikme tablosu) — 27/27 olmali
python3 onizleme/derleyici/server.py --oz-test   # enjeksiyon ikinci savunmasi
```

4e (soguk/sicak p50-p95) ve 4g (canli sayfa) Container deploy'undan sonra kosulur.

## Canli durum (16 Tem aksam) + kalan tek adim

CANLI: Workers Paid acik, imaj registry'de (digest'e sabit), Container + Worker deploy
edildi (route pruvo3d.com/api/onizleme/*), KAPI-1 GECTI (soguk p95 2,7 sn), 4e + 4g
yesil. KALAN TEK ADIM: `secenekler.js` `ONIZLEME_3D_ACIK=true` (MIMAR karari) → push
(build.py butonu basar).

### Imaj guncelleme akisi (degisiklik oldugunda)

1. Gerekirse paket degisti ise: `python3 tools/onizleme-paket-yukle.py`
   (R2 + ONIZLEME_PAKET_B64 secret'ini birlikte tazeler).
2. Tetikle — ONCESINDE ELLE IS YOK:
   `gh workflow run onizleme-imaj.yml -f paket_anahtar=<R2 ANAHTARI> -f push_et=true`.
   Registry push'u CI'daki `CLOUDFLARE_API_TOKEN` yapar (Containers yetkisi 30 Tem
   2026'da eklendi, kosum 30544817485 ile dogrulandi). Eski "gecici registry
   kimligini elle secret'a koy" adimi KALDIRILDI: JWT ~15 dk'da doluyor ve her
   tetikten once elle tazeleme gerektiriyordu.
3. CI logundaki YENI digest'i `onizleme/wrangler.toml` `image = ...@sha256:...`
   satirina yaz (`:ci` tag'i MUTABLE — ayni tag'e push rollout tetiklemez, 16 Tem'de
   olculdu). **Registry yolundaki hesap kimligi izlenen dosyada YER TUTUCUDUR** (5 Agu
   2026; public depo): deploy dosyasini once uret, sonra ONU deploy et —
   `CLOUDFLARE_ACCOUNT_ID=<kimlik> python3 tools/onizleme-deploy-hazirla.py` →
   `npx wrangler deploy -c onizleme/wrangler.deploy.toml` (uretilen dosya git-DISI) →
   eski instance'i dusurmek icin
   `/api/onizleme/derleyici-kapat` (X-Kapat-Anahtar) → iki aileyle duman.

## Bilinen sapma (mimar karari bekliyor)

O-ring "pahli" profili: uretecin pah orani ile `jenerator/hacim.js` `oring()`
"pahli" katsayisi (0.875) farkli geometrilere kalibre — STL/formul sapmasi ~%6.3.
Secenekler: hacim.js katsayisini uretece gore guncelle (fiyat semantigi = mimar+Okan)
veya pahli profili pilotta tut. Kabul 4d bu profili SAYMAZ ama her kosumda raporlar.
