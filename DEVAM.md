# DEVAM (KraL) — 8 Agu 2026

## 14 Agu 2026 ~03:38Z-t9 — SAATLIK CI NOBETI (KraL, cron, ev=DOGRU)

SUPURME: `mail-supurme-kos.sh` → rc=0 · BULUNAN=4 · TASINAN=4 · ATLANAN=0 · CIKAN=4 · KOMSU_KAYIP=0 · KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=76:2026-08-14T06:34 · HUKUM=SUPURULDU. 7ba6287 zinciri için 3 + eski 3519254 zinciri için 1 (toplam 4 mail).
COP_DENETIM: Pruvo hesabı MESRU=61 / YANLIS=0 (süpürme temiz); gmlmz/gemalmaz/dio hesapları YANLIS=15 K92 bilinen sınıfı (süpürme dışı yol); sipariş/ödeme kaybı YOK.
GH SON_1H (HEAD 7ba6287 "ekle: Audi+Mercedes x Cults3D dilim-1 14 urun canliya"): 4 failure aynı head'de — Build&deploy `31766288494` (serit-a3 marka-sayac: 60 düşen, ürün `kategori` alanları `CLAUDE.md` `CATEGORIES` listesinde YOK) + Spec güvenlik taraması `31766288497` (K94 sınıfı — bilinen, SERIT-B BLOKLAMAZ) + Odeme yolu `31766288498` (shop worker bayat 144,7 dk, K91 sınıfı, `DEPLOY = OKAN kapısı`). Yeni koşumlar `31767204268` D1 sapma alarmi success + `31766288630` Nöbet şeridi SERIT B pending. Build & deploy durumu: 3 iş serit-a3/a2/build failure → `deploy`+`yayin` SKIPPED → yeni 14 ürün canlıya inmedi (yayın BLOKLU yeni ürün için).
K93 YARIM İŞ: önceki tur raporu "Codex lokal commit `710dd8df` push olmadı" diyordu; bu turda **710dd8df main + origin/main'de** (`branch -r --contains` → origin/main ✅, `merge-base --is-ancestor` rc=0). Çekirdek kök neden `SERIT B'DE BEYANSIZ KAPI: tools/onarim-commit-test.py` 710dd8df ile çözüldü.
TAMIRCI: açık-kalemler.md'den 🔧 okundu (17 kalem: K49·K53·K55·K59·K69·K70·K71·K72·K77·K78·K80·K84·K85·K86·K88·K90·K93). K49/K53/K55 → ESKALASYON=OKAN (geri-iz.json). K59/K69/K70/K71 → DAGITILDI (işçide, tur kapanmadı). K72/K77/K78/K80/K84/K85/K86/K88/K90/K93 → SIRADA (kapı H2 fan-out'u tur=9 dağıtacak). K93 bu turda **KAPANDI** (kabul: `python3 tools/is-akisi-kapisi.py` YESIL ✅ — 5 B iddiası · 320 kapı çağrısı · 111 SERIT_B beyanı · 1 BLOKLAYICI beyan · 11 zorunlu adım · 205 kendini-test · etkisizleştirilmiş 0; "BEYANSIZ KAPI" mesajı çıktıda yok).
ONARIM PAKETİ (yeni kalem açmadan): 7ba6287 ile gelen 14 Audi+Mercedes ürününün `kategori` alanları `CLAUDE.md` `CATEGORIES` listesinde YOK → serit-a3 marka-sayac 60 düşen, Build & deploy zinciri kırmızı. KraL/MaCiT koordinasyon sınıfı: ürün verisi = MaCiT tek-yazar, kategori listesi = KraL. Tek-yazar ilkesi bozulmaz: Tamirci teşhis + yama önerisi hazırlar, MaCiT defterine bırakır (merge/deploy almaz). K94 zaten 🔧 açık ve codex dağıtım SIRADA. Yeni K96/K97 açmıyorum — K94 (aynı serit-B güvenlik taraması) ve K95 (marka/model uyelik K19 ÇAPRAZ-MARKA farklı kök neden) mevcut kalemler bu arızayı kapsar. Tam detay için DEVAM-ARSIV.md bkz.
TEMİZLİK: /tmp/kalem_durum_oku.py SİLİNDİ (13 Ağu kuralı).
OKAN'A ÇIKIŞ: YOK (§5 — K93 kendi kabul testiyle kapandı, K91 zaten OKAN-KAPISI, K94 zaten Okan kararı bekliyordu, yeni onarım paketi MaCiT düzleminde — mimar kararı gerektirmez).

## 13 Agu 2026 — OTURUM KAPANISI (KraL, interaktif)

**YAYIN ACIK.** CI `31722405771`, HEAD `69b77c5f`, **6/6 job yesil**. Gun boyu kapaliydi;
zincir bes sinif onarimi + iki veri duzeltmesiyle acildi.

**CANLIYA GIDEN (SHA):**
`6a3409ad` uc sinif onarimi bir arada — (a) **ozyineleme kilidi** `test-skan-art.py`
(gecici kok kendi icine 33 kez kopyalanip **188 GB** uretmisti; derinlik tavani ·
zaten-varsa-yeni-seviye-acmama · kopyaya sir tasimama · `ignore_errors` kaldirildi = fail-closed
temizlik · temp-altinda kalkani), (b) **mukerrer kapisi** artik **commit icerigini** (index+HEAD)
yargiliyor, calisma agacini degil — yabanci yarim parti alakasiz commit'i kilitlemiyor,
(c) **katalog tip ekseni** tek alandan (`fiyat`) **kanonik semaya**: 15/15 alan, tam katalog
**0 sapma**, yanlis-pozitif 0.
`e03cc879` **id-rename yolu**: isci kimlik ekseni (`PRUVO_ISCI_KOSUMU`) ortak kaynaga
(`tools/mimar_kimlik.py`) alindi ve kod-kilidi + icra kapisi ayni tablodan okuyor (ikiz tanim
kapandi) · `urunler-guard --id-rename` (duplicate uretmiyor) · `duzelt.py` URL-guvenli id destegi.
Uc yeni kabul testi CI'da **bloklayici**: `skan-art-ozyineleme` 6/6 · `mukerrer-kapsam` 5/5 ·
`katalog-tip-sinifi` 9/9 · `id-rename` 6/6; toplam **13 oldurucu mutant** kirmizi.
Veri tarafi (MaCiT, benim actigim araclarla): `a317b8c7` id ASCII rename · `69b77c5f` gorsel
anahtari alt-cizgi→tire.

**DISK (Okan sikayeti kapandi):** bos alan **68 GB → 272 GB**. Tek buyuk sebep bir uretim
isinin kacak ozyinelemesiydi: **188 GB · 1.542.633 dosya · 33 kat** — ve icinde **99 sir dosyasi**
(uc ayri kimlik turu, her biri ×33; adlar arsivde) sistem temp'ine cogaltilmisti;
silindi, kalinti 0. Ayrica `/private/tmp` 85 eski dizin · `.thing-cache` 36G→360M ·
`urun/`+`marka/` 828 MB build ciktisi · eski worktree'ler. 🔴 Kacagi ureten betik KraL evindeydi
(`tools/test-skan-art.py`) — TeKiN'e kestigim fatura GERI ALINDI, kutuya duzeltme yazildi.

**STL KURTARMA (Okan "Son Kullanilanlar"dan 10bin+ dosya sildi):** repo dosyalari etkilenmedi,
R2 etkilenmedi (yukleyicide silme cagrisi YOK). Drive copundeki **5.772** STL'nin **877'si
R2'de YOKTU** → turlar halinde kurtarildi. Kapanista **R2'de 11.888 STL** (12.394 model, 39,4 GB).
**Okan kurali olculdu** ("her STL Drive'da VE R2'de"): yerel 580 dosyada
`HER_IKISINDE` 251→**571** · `SADECE_R2` 301→**0** · `SADECE_DRIVE` 28→**9** ·
🔴 `HICBIRINDE`=**0** (tek-kopya risk yok). Kalan 9 = 113 baytlik hasat stub'i, gercek STL degil.
`.bundle` yedekleri Okan onayiyla silindi (main gecmisi repoda mevcuttu).

**KOSUYOR (kapanista devam):**
- `d1-senkron-ac` (isci, `SPEC-d1-senkron-ac.md`) — D1 136 kayit geri; **MaCiT bunu bekliyor**
  (Toyota dilim-5 bloklu). Senkron koşumu + parite/Ege teyidi bu turda.

**BEKLIYOR / DEVREDILDI:**
- **MaCiT:** D1 senkron sonucu · 53 yerel STL'in kaynak-id'si gizli kaynak kaydinda
  eslenmemis · 9 stub dosya yeniden hasat · `pruvo-hasat/olcum/*-cgtrader-cache` **git'e
  commit'lenmis** (1.455 dosya / 214 MB) → gitignore + gecmis temizligi karari.
- **HocA:** `/ara` Worker bayat — `db96c380` site tarafina INDI (`audi araba` 0→455) ama
  Worker'a inmedi; Ege'ye soran musteri bulamiyor. `parite-test.js` adi "site" der ama fiilen
  **o Worker'i** olcer (kirmizi saatlerce yanlis eve yazildi).
- **ArTisT:** `pruvo-pazarlama/gorseller` 576 MB, R2'de kopyasi **YOK** (0/194) — silinmedi,
  sahibine birakildi.
- **Bende (siradaki):** D sinifi 13 kova (5'i haksiz kapali gercek model: Fiat Scudo ·
  Mazda B-Serisi · Peugeot Jumpy · Nissan Primastar · Alfa 916) · `serit-a2` R2 anahtar
  kapisini **aktif-referans eksenine** cekme karari (whitelist REDDEDILDI) ·
  uc-kopya nobetcisi (`tools/stl-uc-kopya-nobet.py` onerisi) · `mimar-commit-kapisi` isci
  eksenini tanimiyor · katalog sayisi **DUSUSUNU** olcen nobetci YOK (93 urun sessizce silinmisti).

**OKAN'DA BEKLEYEN KARAR:** yok. (Disk temizligi, `.bundle`/`stl`/gorsel silme karari ve R2
token'i verildi; token uretildi ve kullanildi.)

**🔴 GUNUN DERSI (bes onarimin ortak kaliba):** kural bir kapiya kurulup **kardesine
kurulmuyor** — tip ekseni tek alana, isci kimligi tek kapiya, mukerrer kapsami tek yere,
R2 anahtar yargisi yanlis birime. Dordu de ayni gun yayini durdurdu. Panzehir: kapsami
**elle listeden degil kanonik kaynaktan TURET** + kardes kapilari ayni turda tara.
