# PAKET ③e (2. tur) — `kral/paket3f-kapisi-tasima` (`d36450a1`) → main MERGE dilimi

Mimar: KraL · 18 Ağu 2026 · hedef kat: **İZOLE OLMAYAN İŞÇİ** (ana checkout'ta çalışan tur).
İzole worktree ajanı ana checkout'a `git -C` yapamaz; merge işi izole OLMAYAN tura verilir.

⚠️ **1. tur KIRMIZI kapandı ve iki kırmızısından biri BENİM kabul jetonumun hatasıydı.**
Bu sürüm o hatayı düzeltiyor. Aşağıdaki §1'i atlamadan oku.

## 0. MİMARIN ÖN ÖLÇÜMÜ (git objelerinden; tekrarlama, teyit et)

```
git merge-base main kral/paket3f-kapisi-tasima  → c6ddede69b6f0a25ee27da07318b339de4f67040
git log --oneline <merge-base>..kral/paket3f-kapisi-tasima
    d36450a1 paket ③f: sahiplik kapisi tasinabilir — H1/H2/H3 sabit mutlak kokten kurtarildi
    8691487a paket3d: tek _anahtar() + KABUL_BOS=0 + BAYAT/EKSIK temizligi + SERIT B baglantisi
    dfc7eb5a WIP paket3b: sahiplik evreni 28 -> 171 mekanizma
git diff --stat <merge-base> kral/paket3f-kapisi-tasima → 4 dosya, +381/-57
    .github/workflows/nobet.yml +9 · tools/ci-kapsam-test.py 22± ·
    tools/sahiplik-haritasi.tsv 167± · tools/sahiplik-kapisi.py 240±
git merge-tree --write-tree --name-only main kral/paket3f-kapisi-tasima
    → 2a470998147ec99fbf8425809bfc4ca2800ba785   (yalnız ağaç OID → ÇAKIŞMA YOK)
```

Kapsam spec'e uygun; başka dosya YOK. Taşınabilirlik onarımı git objesinden teyit edildi:
`CANON`/`CRON` sabitleri varsayılan hedef olmaktan çıkmış, `_repo_kok_turetilmis()` +
`_cron_yolu_turetilmis()` eklenmiş, `--repo default=None`, `CRON_EVRENI` yazılıyor.

⚠️ `nobet.yml`e başka bir oturum (K166 inişi) dokunmuştu. Merge'den hemen önce tekrar bak:
```
git -C /Users/okan/dev/pruvo log --oneline -3 -- .github/workflows/nobet.yml
```
Taban ölçümünden sonra yeni bir dokunuş varsa **DUR** ve rapora yaz.

## 1. 🔴 ÖNCE OKU — 1. turun iki kırmızısı ve gerçek sebepleri

**(a) `HARITADA=28` sahteydi.** Kapı, `--repo` verilmezse hedefini sabit mutlak kökten
(`CANON`) alıyordu; doğru worktree'de koşulsa bile **ana checkout'u** ölçüyordu. ③f bunu
onardı. Bu turda kapı **`--repo` BAYRAĞI VERİLMEDEN** koşacak ve kendi ağacının sayılarını
vermek ZORUNDA.

**(b) `grep -c R_SAHIPLIK == 0` kabul jetonu YANLIŞTI (mimarın hatası).** Ölçüm 3 verdi ama
muafiyet gerçekten kalkmıştı: `R_SAHIPLIK = (...)` tanımı yoruma alınmış, `IZIN_LISTESI`'ndeki
`"tools/sahiplik-kapisi.py": R_SAHIPLIK` girdisi **silinmişti**; üç isabet yorum metinlerinde.
**Jeton adı sayan kabul davranış ölçmez** ([[jeton-listesi-kapsam-kaniti-degildir]]).
Bu jeton KALDIRILDI; yerine §2.2'deki davranışsal kontrol geçti.

Genel kural (bugün ölçüldü): **kapı DALIN ağacında koşar VE kapının hedefi çağrıldığı ağaç
olmalıdır** — ikisi ayrı eksendir, biri diğerini kapatmaz →
[[kapi-sabit-kok-yanlis-agaci-olcer]].

## 2. ADIM 1 — dalı çıkar, kapıları DALIN ağacında koş

```
git -C /Users/okan/dev/pruvo worktree add /Users/okan/dev/pruvo/.claude/worktrees/p3e2-merge kral/paket3f-kapisi-tasima
```

⚖️ Worktree tavanı (2) uyarı basacak — bloklamaz, mimar kararı; aynı turda kaldırılacak.
`k166b-yayin-sinyali` ağacına DOKUNMA (başka oturumun canlı ağacı).

### 2.1 Kapı, o dizinden, **`--repo` VERMEDEN** (her komutun `pwd`'si rapora)
```
python3 tools/sahiplik-kapisi.py --kendini-test
python3 tools/sahiplik-kapisi.py
```
Beklenen (③f raporu; **bağımsız yeniden ölçülecek**):
`EVREN=171 · CRON_EVRENI=18 · EKSIK=0 · BAYAT=0 · KABUL_BOS=0 · MUTANT=4/4 · KONTROL=2/2 · rc=0`

🔴 **AYRICA (b) ekseni — sahte yeşili yakalayan tek ölçüm:** aynı kapıyı **ana checkout'tan**
da `--repo` vermeden koş. İki koşumun `EVREN`/`HARITADA` değerleri **FARKLI** olmalı (ana
checkout'un haritası 42 satır, dalınki 185). **Aynı çıkarlarsa H1 tutmamıştır → MERGE ETME.**

### 2.2 Davranışsal muafiyet kontrolü (`grep` DEĞİL)
```
python3 tools/ci-kapsam-test.py
```
rc=0 **ve** çıktıda `tools/sahiplik-kapisi.py` **muaf listesinde GÖRÜNMEZ**. Raporda muaf
listesinin ilgili bölümü alıntılanır.

### 2.3 Kablo kontrolü
`.github/workflows/nobet.yml` SERİT B'de `sahiplik-kapisi.py` adımı var (grep ≥1) **ve**
adımın hangi job altında olduğu rapora yazılır (SERİT B mi, başka job mu — göz kararı değil,
alıntı).

🔴 Herhangi biri tutmazsa **MERGE ETME**, raporla, dur.

## 3. ADIM 2 — merge + push (ANA checkout'tan)

```
git -C /Users/okan/dev/pruvo fetch origin
git -C /Users/okan/dev/pruvo status -sb
git -C /Users/okan/dev/pruvo merge kral/paket3f-kapisi-tasima -m "3 KAPANDI: sahiplik haritasi 171 mekanizma, kapi tasinabilir (sabit mutlak kok kalkti), muafiyet yerine SERIT B kablosu"
git -C /Users/okan/dev/pruvo push origin main
```

* Ağaçta **yabancı** ` M` / untracked varsa DOKUNMA.
* `push --force` ASLA. Reddedilirse `fetch` + merge, rebase DEĞİL.
* Push D1 kolunda "YAZICI UÇUŞTA" derse **geçicidir** (K176) — 5-10 dk sonra tekrar dene,
  `--no-verify` ARAMA.

## 4. ADIM 3 — merge SONRASI kapılar

```
python3 /Users/okan/dev/pruvo/tools/d1-sync.py --durum
python3 /Users/okan/dev/pruvo/tools/sahiplik-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/ci-kapsam-test.py
```
(Merge'den SONRA ana checkout dalın dosyalarını taşıdığı için bu üç komut artık doğru ağaçta.)

CI teyidi — "en son koşum yeşildi" kanıt DEĞİL, **SHA'yı içeren** koşum:
```
gh -R Pruvo138/pruvo run list --limit 20 --json headSha,status,conclusion,databaseId,createdAt
git -C /Users/okan/dev/pruvo merge-base --is-ancestor <merge-SHA> <kosumun-headSha>
```
rc=0 vermiyorsa o yeşil senin işini derlememiştir. Koşum `in_progress` ise
**"ÖLÇÜLEMEDİ + sebep"** yaz, yeşil yazma.

🔴 **SERİT B'nin İLK koşumu bu paketin ASIL kabulüdür:** kapı gerçek koşucuda (macOS/Linux,
`/Users/okan/...` YOK) koşacak. Beklenen: çökme YOK, `CRON_EVRENI=OLCULEMEDI`, `tools/`
düzlemi ölçülür. Koşum bitmediyse `OLCULEMEDI` yaz; sonraki tur bakar.

## 5. ADIM 4 — temizlik

```
git -C /Users/okan/dev/pruvo worktree remove --force /Users/okan/dev/pruvo/.claude/worktrees/p3e2-merge
git -C /Users/okan/dev/pruvo branch -D kral/paket3f-kapisi-tasima
git -C /Users/okan/dev/pruvo branch -D kral/paket3d-anahtar
git -C /Users/okan/dev/pruvo branch -D kral/paket3b-evren
git -C /Users/okan/dev/pruvo worktree list
```
Silmeden önce: worktree porcelain temiz mi · dalın İÇERİĞİ gerçekten main'de mi
(`git branch --merged` YETMEZ) · ana ağaçta o işe benzeyen commit'siz değişiklik var mı.
Son `worktree list` çıktısı rapora BİREBİR.

## 6. RAPOR

Nöbet/dal kanonik mühendis rapor dosyasına, BAŞA ekle (üzerine YAZMA). İçinde:
* her kabul komutunun ham son satırı + rc'si + koştuğu `pwd`,
* **iki konumdan koşumun FARKLI sayı verdiği** kanıtı (H1'in çalıştığının tek kanıtı budur),
* muaf listesi alıntısı + `nobet.yml` adım alıntısı,
* merge SHA'sı, push sonucu, D1 durum satırı, CI teyidi (ya da `OLCULEMEDI` + sebep),
* son satır `TEMIZ=EVET` + `worktree list` çıktısı.

## 7. İŞÇİ TALİMATI

* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Kırmızı adımın üstünden atlayıp merge etme; herhangi bir adım kırmızıysa DUR.
* **DOKUNMA:** `urunler.json` · `crontab` · `~/.claude/cron/gozcu.py` · `~/.claude/cron/kilit.py`
  · `k166b-yayin-sinyali` worktree'si.
