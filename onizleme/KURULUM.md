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

## Canliya alma sirasi (kalan is — plan kapisi)

1. Workers Paid aktif (Okan onayladi; Codex panelden yukseltecek).
2. GitHub secrets: `R2_ERISIM_ID`/`R2_GIZLI_ANAHTAR` (pruvo-ozel okuma yetkili R2 S3
   token — Cloudflare panelinden uretilir) (+ mevcut `CLOUDFLARE_API_TOKEN`'a
   containers yetkisi).
3. `onizleme-imaj.yml` workflow'unu `push_et=true` ile tetikle → imaj registry'de.
4. `onizleme/wrangler.toml` containers blogunu ac + `src/index.js`'e Container sinifi
   (adaptor sozlesmesi: `src/derleyici.js` basligi) → `npx wrangler deploy`.
5. KAPI-1 olcumu: soguk baslatma p50/p95 (>=10 istek) + sicak istek. p95 > 10 sn ve
   onbellek maskeleyemiyorsa DUR → mimara rapor.
6. Kabul 4e + 4g kos, yesilse `secenekler.js` `ONIZLEME_3D_ACIK=true` (MIMAR karari)
   → push (build.py butonu basar).

## Bilinen sapma (mimar karari bekliyor)

O-ring "pahli" profili: uretecin pah orani ile `jenerator/hacim.js` `oring()`
"pahli" katsayisi (0.875) farkli geometrilere kalibre — STL/formul sapmasi ~%6.3.
Secenekler: hacim.js katsayisini uretece gore guncelle (fiyat semantigi = mimar+Okan)
veya pahli profili pilotta tut. Kabul 4d bu profili SAYMAZ ama her kosumda raporlar.
