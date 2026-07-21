# Yedek Topolojisi Teyidi — SALT-OKUNUR ölçüm (2026-07-21)

Paket: `G3-yedek-topolojisi`. Bu rapor **hiçbir yedek çalıştırmadı, hiçbir şey yazmadı/silmedi**.
Ölçümler salt-okuma listeleme + dosya metadatası ile alındı. Ölçülemeyen her şey açıkça
"ÖLÇÜLEMEDİ + neden" olarak işaretlidir; **tahmin/uydurma sayı yoktur**.

Sır dosyalarının yalnızca **varlık/konum** durumu ölçüldü; **içerik okunmadı ve bu rapora yazılmadı**.

---

## 0. Ölçüm yöntemi ve ÖNCE-KIRMIZI kanıtı

Yöntemin "sessizce boş/0 dönme" riskine karşı mutasyon testi koşuldu (ham çıktı):

```
== M1: karsilastirici kendi kendine 0 eksik vermeli (kontrol) ==
   canli vs canli eksik = 0 (0 bekleniyor)
== M2: MUTASYON — 3 dosya silinmis sahte yedek; eksik 3 CIKMALI (kirmizi) ==
   eksik = 3 ['3mf-olcu-rotasyon-tuzagi.md', 'MEMORY.md', 'agents-md-tek-kaynak.md']
   -> mutasyon KIRMIZI yakti (karsilastirici gercekten eksik buluyor)
== M3: MUTASYON — olmayan R2 kovasi 0 GB DEMEMELI, HATA vermeli ==
   HATA (beklenen): AccessDenied ... ListObjectsV2 ...
   -> olculemeyen kova sessizce 0 GB olarak raporlanmaz
ONCE-KIRMIZI TAMAM
```

Yani: "yedekte yok" listesi gerçekten eksikliği yakalıyor, "ölçülemedi" gerçekten hata
üzerine yazılıyor (0 GB diye raporlanmıyor).

---

## 1. `tools/yedekle.py` en son ne zaman koştu, neyi kapsadı?

**Kesin çalışma zamanı ÖLÇÜLEMEDİ** — sebep: `yedekle.py` hiçbir yere zaman damgası/koşum
günlüğü yazmıyor (yalnız stdout'a basıyor), `crontab -l` boş, zsh geçmişinde `yedekle.py`
geçmiyor (`grep -c` = **0**). Kalan tek delil: Drive'daki kopyaların mtime'ları
(`shutil.copy2` kaynak mtime'ını korur).

Drive hedefi: `~/Library/CloudStorage/GoogleDrive-info@pruvo3d.com/Ortak Drive'lar/PRUVO/Pruvo/backup`
(mount doğrulandı, `.stl-backup-dir` taze). Toplam yedek boyutu: **3.4 MB**.

| Yedekteki dosya | Yedek boyut / mtime | Canlı boyut / mtime | Gecikme |
|---|---|---|---|
| `.urun-kaynaklari.json` | 2.915.677 B · 19 Tem 14:01 | 2.800.358 B · 20 Tem 22:55 | **~1 gün 9 sa** |
| `CLAUDE.md` | 36.011 B · 19 Tem 12:05 | 15.040 B · 20 Tem 17:54 | **~1 gün 6 sa** |
| `DEVAM.md` | 159.888 B · 19 Tem 13:57 | 27.166 B · 21 Tem 06:17 | **~1 gün 16 sa** |
| `memory/` | 81 dosya · en yeni kaynak mtime 20 Tem 21:05 | 89 dosya · en yeni 21 Tem 06:27 | **~9 sa** |
| sırlar (`--sirlar`) | 5 dosya · 8–17 Tem | — | (aşağıda) |

**Sonuç (sayıyla):** son koşumun kanıtlanabilir alt sınırı **2026-07-20 21:05**
(memory kopyasındaki en yeni kaynak mtime). Ancak aynı koşum `.urun-kaynaklari.json` /
`CLAUDE.md` / `DEVAM.md`'yi 19 Tem sürümünde bırakmış → **koşum(lar) KISMİ/TUTARSIZ**.
Bu tutarsızlığın sebebi ölçülemedi (script günlük tutmuyor); en olası açıklama Drive
kopyalamasının yarıda kesilmesi/kısmi hata (copytree Drive throttling altında kısmen kopyalar).
→ **Bu tek başına bir bulgu: "yedek alındı" iddiası bugün doğrulanabilir değil.**

### memory/ kapsamı — sayılarla
- Canlı: **89** dosya · Yedek: **81** dosya
- **Yedekte HİÇ YOK: 17 dosya** (19 Tem 20:49 – 21 Tem 06:27 arası doğanlar), aralarında:
  `halef-devir-mektubu.md`, `bas-mimar-eli-surmez.md`, `mimar-posta-kutusu-arsiv.md`,
  `kapi-disiplin-ilkesi.md`, `yedi-altin-kural.md`, `kota-denetim-onerileri-20tem.md`,
  `hoca-artist-kota-delikleri-20tem.md`, `kral-macit-urun-jenerator-devir-20tem.md`,
  `bayat-kabul-testi.md`, `coklu-tur-curutme-deseni.md`, `mimar-kapi-parser-taklidi.md`,
  `deploy-cache-purge-yarisi.md`, `dosya-teslim-bicimi.md`, `kota-bitince-devret.md`,
  `is-baslamadan-kutu-oku.md`, `kapi-kapsam-genisletme-tuzagi.md`,
  `gitignore-worktree-auto-cleanup.md`
- **Yedekte BAYAT (boyut/mtime farklı): 10 dosya** — `MEMORY.md` (indeks!),
  `mimar-posta-kutusu.md`, `d1-arama-tuzaklari.md`, `ege-d1-bagimliligi.md`,
  `filament-fiyat-katsayilari.md`, `codex-kredi-orkestrasyon.md`, `codex-panel-kimlik-once.md`,
  `cikti-kisa-temiz.md`, `proje-ayrimi.md`, `pruvo-jenerator-projesi.md`
- **Yedekte ÖLÜ (canlıda silinmiş, yedekte duran): 9 dosya** — `copytree` asla silmez;
  geri yükleme anında **silinmiş kuralların dirilme riski** var
  (`mimar-is-yapmaz.md`, `urun-ekleme-akisi.md`, `gemini-yardimcisi.md`, … )

---

## 2. Kapsam listesi — hangileri EKSİK?

| Varlık | Yedekte mi? | Ölçüm |
|---|---|---|
| pruvo hafıza `.md`'leri | 🟡 KISMİ | 81/89 dosya; 17 yok, 10 bayat, 9 ölü |
| mimar posta kutusu (aktif) | 🟡 BAYAT | yedek 20 Tem 21:05 · canlı 21 Tem 06:18 |
| mimar posta kutusu ARŞİV | 🔴 YOK | `mimar-posta-kutusu-arsiv.md` (75.770 B) hiç yedeklenmemiş |
| pruvo `DEVAM.md` | 🟡 BAYAT | 19 Tem 13:57 sürümü |
| pruvo `DEVAM-ARSIV.md` (213.533 B) | 🔴 YOK | `yedekle.py` listesinde YOK (yalnız CLAUDE.md + DEVAM.md) |
| pruvo `CLAUDE.md` | 🟡 BAYAT | 19 Tem 12:05 sürümü |
| **pruvo-bot** DEVAM.md (10.864 B) | 🔴 YOK | `yedekle.py` yalnız `~/dev/pruvo` kökünü tarıyor |
| **pruvo-pazarlama** DEVAM.md (23.913 B) + DEVAM-ARSIV.md (46.960 B) | 🔴 YOK | aynı sebep |
| **pruvo-jenerator** DEVAM.md (3.082 B) | 🔴 YOK | aynı sebep |
| Kardeş repo hafızaları (`-pruvo-bot`, `-pruvo-pazarlama`, `-pruvo-jenerator`, eski `-Documents-pruvo` = **4 ayrı memory dizini**) | 🔴 YOK | hiçbirinde `yedekle.py` muadili yok (`tools/` grep → 0 sonuç) |
| `.urun-kaynaklari.json` | 🟡 BAYAT | 19 Tem 14:01 kopyası (canlı 20 Tem 22:55) |
| `.r2-credentials.json` | 🟢 VAR (aynı Drive, `--sirlar`) | 291 B · 8 Tem 19:15 — canlı ile aynı boyut/mtime → güncel. İçerik **okunmadı** |
| `.thingiverse-token`, `.stl-backup-dir`, `.onizleme-kapat-anahtar`, `.mukerrer-istisna.json` | 🟢 VAR (sır ayağı) | 11–17 Tem; canlı boyut/mtime ile eşleşiyor |
| Site kodu / `urunler.json` | 🟢 VAR | GitHub `Pruvo138/pruvo` (uzak kopya doğrulandı) |
| **pruvo-pazarlama repo'su** | 🔴 **UZAK KOPYA YOK** | `git remote -v` → **BOŞ ÇIKTI**; bot/jenerator/pruvo'da origin var. Bu repo **tek kopya** (yalnız bu makinede) |

**Sır saklama notu:** sırların yedeği ürün verisiyle **aynı Drive klasöründe**
(`backup/.r2-credentials.json` vb.). Klasör paylaşılırsa sır sızar — `yedekle.py` docstring'i de
uyarıyor. Ayrı, paylaşılmayan klasöre (ya da 1Password/Keychain'e) taşınması önerilir; **karar Okan'ın**.

---

## 3. 🔴 R2 ürün görselleri — Advisor bulgusu DOĞRULANDI

Salt-okuma listeleme (`list_objects_v2`, yazma yok):

```
KOVA pruvo-media: nesne=20514  toplam=2.55 GB (2.549.098.686 bayt)
   onek urunler   nesne=20513   2.55 GB
   onek logo      nesne=1       0.00 GB
```

- **20.514 nesne / 2,55 GB** ve bunların **hiçbiri hiçbir yedekte görünmüyor**
  (Drive `backup/` toplamı 3,4 MB; içinde görsel yok, git'te görsel yok — kural gereği).
- Yani **görseller TEK KOPYA**: tek bir yanlış `delete-objects` / token ele geçirme /
  kova silme → **7.9k ürünün tüm görselleri gider**, yeniden üretimi ancak kaynak
  platformlardan tek tek indirmeyle mümkün (bazı kaynaklar emekli/silinmiş olabilir).
- `list_buckets` **AccessDenied** → kova envanteri ÖLÇÜLEMEDİ (token kova-kapsamlı).

### Öneri (haftalık ikinci kopya) — iki seçenek, sayıyla
1. **Ayrı R2 kovası (`pruvo-media-yedek`) — ÖNERİLEN.**
   - Maliyet: R2 depolama ~$0,015/GB-ay → 2,55 GB ≈ **~$0,04/ay**. R2→R2 kopyalamada
     çıkış ücreti yok; A-sınıfı yazma 20.5k istek ≈ ihmal edilebilir.
   - Uygulama: `rclone copy r2:pruvo-media r2:pruvo-media-yedek` (**rclone KURULU DEĞİL** —
     `which rclone` → not found; `brew install rclone` gerekir) ya da boto3 ile
     `copy_object` döngüsü (yeni/değişmiş anahtar bazlı, ETag karşılaştırmalı).
   - 🔴 Kimlik ayrımı şart: yedek kovasının anahtarı **ayrı ve yalnız-yazma/okuma**;
     ana kovanın silme yetkisi olan anahtarla yedek kovası silinebilmemeli
     (aksi halde "tek kaza" ikisini birden götürür).
   - Ek olarak Cloudflare R2 **Object Versioning + Lifecycle** açılırsa yanlışlıkla üzerine
     yazma/silme geri alınabilir (kova ayarı, panel işi → Okan/Codex kapısı).
2. **Drive'a rclone ile ayna.** 2,55 GB Drive'a sığar, ama 20.5k küçük dosya Drive'da
   yavaş/kırılgan ve ürün görselleri Drive kotasını STL ile paylaşır. Ancak "farklı sağlayıcı"
   avantajı var (Cloudflare hesabı komple kaybolursa kurtarır) → **3-2-1 için ideali: ikisi de**
   (R2-R2 haftalık + Drive'a aylık tam ayna).

---

## 4. STL: Drive ayağının kaderi

| Yer | Ölçüm |
|---|---|
| Drive `Pruvo/STL` | **11.053 girdi**, `du -sh` → **1,6 GB** (⚠️ Drive dosyaları "online-only" olabildiği için `du` gerçek boyutu OLDUĞUNDAN KÜÇÜK gösterebilir — gerçek bulut boyutu ÖLÇÜLEMEDİ, sebep: Drive kota API'si/panel erişimi yok) |
| Yerel `~/dev/pruvo/stl` | **2.336 girdi**, **11 GB** |
| R2 `pruvo-ozel` (`stl/` öneki, MaCiT'in taşıdığı yeni birincil arşiv) | **ÖLÇÜLEMEDİ** — `.r2-credentials.json` anahtarı bu kovaya **AccessDenied** (anahtar `pruvo-media` kapsamlı); ölçüm için ayrı okuma anahtarı gerekir |

**Öneri:** R2 `pruvo-ozel` **birincil** olduğu doğrulanana kadar (nesne sayısı ≥ Drive'daki
STL sayısı + rastgele 20 dosyada bayt-bayt eşleşme) **Drive STL ayağı SİLİNMEZ**. Doğrulama
yeşil olduğunda Drive STL'i **soğuk ikinci kopya** olarak bırakmak en ucuz seçenek
(1,6 GB, 45 GB kotayı zorlamıyor → *bugün çıkarmak için sebep yok*). Asıl yer darlığı
Drive'da değil **yerel diskte** (11 GB): yerel `stl/` R2 doğrulaması sonrası budanabilir.
Çıkarma kararı ancak "R2 birincil doğrulandı" raporu geldikten sonra, ve o zaman bile
**Drive'da bırakmayı** öneririm (farklı sağlayıcı = tek-sağlayıcı riskini kırar).

---

## 5. Cron önerisi (Okan'ın eli değmeden)

Makinede `crontab` **yok** (`crontab -l` → "no crontab for okan"), ama çalışan bir launchd
deseni **var** (`~/Library/LaunchAgents/com.pruvo.parity-panel.plist`) → aynı deseni kullan.

**Somut plan (uygulanmadı — bu paket salt-okunur):**

1. `~/Library/LaunchAgents/com.pruvo.yedek.plist` oluştur:
   - `ProgramArguments`: `/opt/homebrew/bin/python3` + `/Users/okan/dev/pruvo/tools/yedekle.py` + `--sirlar`
   - `StartCalendarInterval`: **Pazar 03:00** (haftalık) — `Weekday 0`, `Hour 3`, `Minute 0`
   - `RunAtLoad` **false**, `StandardOutPath` `/tmp/pruvo-yedek.log`,
     `StandardErrorPath` `/tmp/pruvo-yedek.err`
   - Yükleme: `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.pruvo.yedek.plist`
   - **Sıklık gerekçesi:** hafıza günde ~4-8 dosya değişiyor (ölçüm: 20 Tem'de 4, 19 Tem'de 7
     dosya) → haftalık pencerede en kötü kayıp ~1 haftalık hafıza. Kritik dosya
     (`.urun-kaynaklari.json`) günlük değişiyor → **onun için günlük** ayrı bir tetik daha
     doğru olur.
2. **Başarısızlıkta ne olur — bugünkü davranış tehlikeli:** `yedekle.py` Drive yolu
   çözülemezse "Yedek ALINMADI" **basıp exit 0** dönüyor; kısmi kopyalama da (bugün olduğu gibi)
   sessizce geçiyor. Otomatiğe bağlamadan ÖNCE üç küçük değişiklik şart
   (kod işi — ayrı paket, bu pakette YAPILMADI):
   - Drive yoksa / kopya hata verirse **exit 1**;
   - koşum sonunda `backup/.yedek-son.json` (zaman damgası + kopyalanan dosya sayısı) yaz →
     "en son ne zaman koştu" bir daha tahminle cevaplanmasın;
   - kaynakta olmayanı yedekte de sil (ayna) ya da en azından "ölü dosya" sayısını raporla.
3. **Sessiz başarısızlık alarmı:** `tools/durum.py` panosuna "yedek yaşı > 8 gün → KIRMIZI"
   satırı; ayrıca launchd `.err` boş değilse pano uyarısı. (Bugün alarm YOK → 2 gün bayat
   yedek fark edilmemiş.)

---

## Özet — Okan'a tek bakışta

| Risk | Durum |
|---|---|
| R2 ürün görselleri (20.514 nesne / 2,55 GB) | 🔴 **TEK KOPYA** — haftalık ikinci kova ~$0,04/ay |
| `pruvo-pazarlama` reposu | 🔴 **TEK KOPYA** — git uzak sunucusu yok |
| 3 kardeş repo DEVAM + 4 hafıza dizini + DEVAM-ARSIV + posta arşivi | 🔴 hiç yedeklenmiyor |
| pruvo hafızası / DEVAM / kaynak haritası | 🟡 var ama **1–2 gün bayat, 17 dosya eksik** |
| Sırlar | 🟢 yedekte, ama ürün verisiyle **aynı klasörde** |
| Otomatik koşum | 🔴 yok (cron/launchd yok, alarm yok, koşum günlüğü yok) |
