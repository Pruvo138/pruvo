# PAKET — `deploy` kritik yolunu kısalt: mutasyon bataryalarını gating şeritten SERIT B'ye taşı

> Yazan: KraL (baş mimar) · 9 Ağu 2026 ~09:5xZ · Sınıf: MÜHENDİS işi (CI topolojisi, sessiz kapsam kaybı riski)
> Bu paket **ölçümle** doğdu; hiçbir sayısı beyandan alınmadı.

## 1) NEDEN — ölçülen problem

Yayın 9 saattir inmedi (son başarılı deploy `3e7f1b24`, 2026-08-09T00:45:56Z; o günden bu yana
`origin/main` **27 commit** ilerledi). Sebep İKİ katmanlı; bu paket **yalnız 2. katmanı** kapatır.

**Katman 1 (bu paketin işi DEĞİL):** gating şeritlerde gerçek kırmızı (`serit-a2` A4 model ikizi —
MaCiT düzlemi). Kırmızı dururken `deploy` zaten `skipped`.

**Katman 2 (BU PAKET):** zincir süresi push kadansından uzun → her onarım turu ~1 saate mal oluyor
ve kuyruktaki koşumlar sürekli düşüyor.

Kaynaktan (YAML) ve ADIM biriminden ölçüldü — yorum satırına GÜVENİLMEDİ:

| Eksen | Ölçülen |
|---|---|
| `deploy: needs` (deploy.yml:2155) | `[build, serit-a2, serit-a3, serit-a4]` — dördü de push'tan paralel, gizli needs-zinciri YOK |
| `yayin: needs` (deploy.yml:2199) | `deploy` |
| `concurrency` (deploy.yml:33-35) | `group: pages` · `cancel-in-progress: false` — **literal YAML, bilerek** |
| Zincir toplam (koşum `31286873618`, son gerçek success) | push `00:45:56Z` → `yayin` bitiş `01:48:31Z` = **3755 sn (62m35s)** |
| **Tavan job** | `serit-a4` **3621 sn (60m21s)** |
| **Tavan ADIM** | `serit-a4` / "Model uyeligi mutasyon bataryasi" = `model-uyelik-kapisi.py --kendini-test` → **2725 sn (~45 dk)** |
| Push kadansı (son 20 koşum, 19 aralık) | ortalama **28,1 dk** · **medyan 17,1 dk** |
| Son 19 koşumda `cancelled` | **14** (survivor'lar arası boşluk 89,7 dk'ya kadar) |

**Hüküm:** zincir (62,6 dk) push kadansının (medyan 17,1 dk) **~3,7 katı.** `cancel-in-progress:
false` altında KOŞAN koşum korunur, yalnız KUYRUKTAKİ düşer → yeni push gelen her ~17 dk'da
kuyruktaki koşum devriliyor ve yayın ancak ~62 dk'da bir pencere buluyor. Bu pencereye denk gelen
koşumların çoğu da gating kırmızısı taşıdığı için 9 saattir hiç inmedi.

⚠️ **`cancelled` yığınını ARIZA SAYMA** → [[cancelled-yigini-yayin-tavani]]. Bu paketin gerekçesi
`cancelled` sayısı değil, ADIM biriminden ölçülen **SÜRE**dir.

## 2) NE YAPILACAK

`serit-a4`'ün **mutasyon bataryası** adımlarını `deploy`'u gating eden şeritten çıkar,
`nobet.yml` içindeki **SERIT B** (yayını BLOKLAMAZ) koluna taşı.

Taşınacak adımlar (`serit-a4`, deploy.yml):
1. "Model uyeligi mutasyon bataryasi (34+7)" → `python3 tools/model-uyelik-kapisi.py --kendini-test` — **2725 sn**
2. "Model baslik kolu mutasyon bataryasi (4+3)" → `python3 tools/model-baslik-kolu-test.py --kendini-test`

`serit-a4`'te KALACAK: "Yedek glob kod yolu — hermetik alt kume" (`tools/yedekle-test.py --hermetik`, ~4 sn).

**Emsal var, uydurma değil:** `nobet.yml` başlığı "SERIT B — yayını BLOKLAMAZ" ve dosyanın kendi
yorumu bu ayrımın **5 Ağu'da bilerek** yapıldığını yazıyor (envanter · cron-nabzi · d1-kadans ·
mesaj-nobeti · serit-b · hacim-tam-takim deploy.yml'den O ZAMAN çıkarıldı). Bu paket aynı kararı
kalan iki bataryaya uyguluyor.

**Beklenen kazanç:** tavan `serit-a4` 3621 sn → gating tavanı bir sonraki en uzun gating job'a
düşer (`serit-a2` ~21 dk mertebesinde). Zincir ~62 dk → ~22-25 dk; push kadansının (17,1 dk)
biraz üstünde kalır ama onarım turu maliyeti **~1 saatten ~25 dk'ya** iner.

## 3) 🚫 YASAK — bunlardan biri gerekiyorsa DUR ve KraL'a yaz

- Adım **SİLME**. Batarya `serit-b`'de AYNI komutla, AYNI argümanlarla koşmaya devam edecek.
- `continue-on-error` ekleme, `if:` ile atlatma, iddia sayısını/eşiğini düşürme.
- `model-uyelik-kapisi.py` / `model-baslik-kolu-test.py` **içeriğine** dokunma (bu paket yalnız
  ADIMIN HANGİ JOB'DA koştuğunu değiştirir).
- `urunler.json` · `.urun-kaynaklari.json` · secret · `.r2-credentials.json` · `CNAME`.
- `deploy: needs` listesinden `serit-a2`/`serit-a3`/`build` çıkarma — YALNIZ `serit-a4`'ün
  KENDİSİ boşalırsa `needs`'ten düşürülür; boşalmıyorsa `serit-a4` needs'te KALIR.
- force push / geçmiş yeniden yazma / alt görev açma.

## 4) KABUL — çalıştırılabilir, "bakıldı iyi" DEĞİL

Hepsi AYNI commit'te yeşil olacak:

1. `python3 tools/is-akisi-kapisi.py` **rc=0** — yeni adımlar `serit-b`'ye **DÜZ TEK KOMUTLA**
   kablolu ve `SERIT_B` beyanı AYNI commit'te. (Kayıtlı tuzak: beyan ile fiili kablolama ayrışır.)
2. `python3 tools/ci-kapsam-kapisi.py` **rc=0** ve **keşfedilen kapı çağrısı sayısı DÜŞMEDİ** —
   çıkış kodunu değil **BASTIĞI SAYIYI** taşınmadan önceki değerle karşılaştır.
   → [[kapi-yan-etkisi-gizli-onkosul]] · [[hukum-yanlis-birimde]]
3. `python3 tools/varlik-test.py` **rc=0**.
4. `python3 tools/kapi-envanteri.py` (varsa) — envanter sayısı DÜŞMEDİ.
5. **DAVRANIŞSAL doğrulama (beyan yetmez)** → [[kapi-beyanin-dogrulugunu-degil-varligini-olcer]]:
   taşıma sonrası ilk koşumda
   - `gh run view <id> --json jobs` ile **`serit-b` job'ında** "Model uyeligi mutasyon bataryasi"
     adımı **ADIYLA** görünüyor ve `success` (yokluğu kanıt SAYILMAZ — pozitif iz şart);
   - `serit-a4` job'ının süresi **< 300 sn**;
   - `deploy` job'ı bu iki adımı **BEKLEMİYOR** (başlama zamanı `serit-b`'nin bitişinden ÖNCE
     olabiliyor — zaman damgasıyla kanıtla).
6. **KONTROL MUTANTI (şart):** `model-uyelik-kapisi.py`'ye ayırt edici bir mutant enjekte et ve
   `serit-b` kolunun onu **KIRMIZI yaktığını** göster. Bu olmadan taşıma, ekseni sessizce
   **no-op**'a çevirmiş olabilir ve fark edilmez. → [[beyan-edilmis-survivor]]
7. Taşınan bataryanın **ölçtüğü iddia sayısı** taşımadan önce ve sonra AYNI (öldürülen mutant
   sayısı dahil). Sayıyı rapora YAZ.

## 5) RAPOR

Dalda mühendis raporunda (kanonik ad için CLAUDE.md İLETİŞİM PROTOKOLÜ; başka ad YASAK). Son satırlar:

```
TASINAN_ADIMLAR=<liste>
SERIT_A4_SURE_ONCE_SN=3621
SERIT_A4_SURE_SONRA_SN=<ölçülen>
ZINCIR_SURE_SONRA_SN=<ölçülen>
CI_KAPSAM_SAYI_ONCE=<n> / SONRA=<n>
BATARYA_IDDIA_ONCE=<n> / SONRA=<n>
KONTROL_MUTANTI=<KIRMIZI_YANDI / YANMADI>
YENI_KOSUM=<id>:<conclusion>
```

## 6) SIRALAMA UYARISI — ne zaman merge edilir

`serit-a2` (A4 model ikizi, MaCiT düzlemi) **KIRMIZI iken bu dal main'e ALINMAZ.** Gerekçe ölçüm:
kırmızı dururken `deploy` `skipped` olacağı için 5. maddedeki davranışsal doğrulama
**yapılamaz** ve her push kuyruğa bir koşum daha ekleyip açlığı artırır. Dal hazırlanır,
lokal kapılar yeşillenir, **A4 kapandığı an** merge → **skill: merge-kapisi**.
