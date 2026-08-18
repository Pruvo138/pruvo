# PAKET ③e — `kral/paket3d-anahtar` (`8691487a`) → main MERGE dilimi

Mimar: KraL · 18 Ağu 2026 · hedef kat: **İZOLE OLMAYAN İŞÇİ** (ana checkout'ta çalışan tur).
İzole worktree ajanı ana checkout'a `git -C` yapamaz; merge işi izole OLMAYAN tura verilir.

## 0. MİMARIN ÖN ÖLÇÜMÜ (yapıldı, tekrarlama — teyit et)

```
git merge-base main kral/paket3d-anahtar          → c6ddede69b6f0a25ee27da07318b339de4f67040
git diff --stat <merge-base> kral/paket3d-anahtar → 4 dosya, +300/-46:
    .github/workflows/nobet.yml   +9
    tools/ci-kapsam-test.py       22 ±
    tools/sahiplik-haritasi.tsv   167 ±
    tools/sahiplik-kapisi.py      148 ±
git merge-tree --write-tree --name-only main kral/paket3d-anahtar
    → 1332f3d8cdb78465b946c6c756612b9f467ee4d5  (yalnız ağaç OID → ÇAKIŞMA YOK)
```

Kapsam spec'e uygun: harita + kapı + muafiyet kaldırma + SERİT B kablosu. Başka dosya YOK.

⚠️ `nobet.yml`e başka bir oturum (K166 inişi) dokunmuştu; taban `c6ddede6`, K166 `e70c89d7`
ile main'e girdi. Ön-test çakışma göstermiyor ama **merge'den hemen önce** tekrar bak:
```
git -C /Users/okan/dev/pruvo log --oneline -3 -- .github/workflows/nobet.yml
```
Taban ölçümünden sonra yeni bir dokunuş varsa **DUR** ve rapora yaz.

## 1. 🔴 ÖNCE OKU — ③c'de MİMARIN yaptığı hata, tekrarlanmayacak

③c turunda kabul komutlarını **`/Users/okan/dev/pruvo/tools/...` mutlak yoluyla** yazmıştım.
İşçi doğru worktree'de çalışıyordu ama komut **ANA CHECKOUT'un** dosyalarını koştu → dalın
getirdiği harita hiç görülmedi, `EKSIK=142` çıktı ve ben bunu "anahtar ekseni bozuk" diye
yorumladım. **Kırmızı sahteydi; kusur spec'teydi.**

Bu evde kural: **kapı DALIN ağacında koşar; ana checkout'ta koşulan kapı ÖLÇMEZ.** Bu turda
her kabul komutu **worktree yolundan** verilecek; `/Users/okan/dev/pruvo/tools/` ile başlayan
kabul komutu YAZMA. Raporda her komutun **hangi ağaçta** koştuğu `pwd` ile gösterilecek.

## 2. ADIM 1 — dalı çıkar, kapıları DALIN ağacında koş

```
git -C /Users/okan/dev/pruvo worktree add /Users/okan/dev/pruvo/.claude/worktrees/p3e-merge kral/paket3d-anahtar
```

⚖️ Worktree tavanı (2) uyarı basacak — **bloklamaz**, mimar kararı; aynı turda kaldırılacak.
`k166b-yayin-sinyali` ağacına DOKUNMA (başka oturumun canlı ağacı).

Sonra **o dizinden** (`pwd` çıktısı rapora):

```
python3 tools/sahiplik-kapisi.py --kendini-test
python3 tools/sahiplik-kapisi.py
python3 tools/ci-kapsam-test.py
```

Beklenen (③d raporu; **bağımsız yeniden ölçülecek**):
```
EVREN=171 HARITADA=171 EKSIK=0 BAYAT=0 SAHIPSIZ=171 KABUL_DOLU=60 KABUL_YOK=111 KABUL_BOS=0 MUTANT=4/4 KONTROL=2/2   rc=0
CI_KAPSAM_RC=0
```
🔴 Sayılar tutmazsa **MERGE ETME**, raporla ve dur. Ayrıca bağımsız `grep -c` ile teyit et:
* `R_SAHIPLIK` `tools/ci-kapsam-test.py`'de **0 kez** geçmeli (muafiyet gerçekten silindi mi),
* `sahiplik-kapisi.py` `.github/workflows/nobet.yml`'de **≥1 kez** geçmeli (kablo gerçekten var mı).
Bu ikisi bu dilimin ASIL işidir; sayılar rapora `grep -c` komutuyla birlikte yazılır.

## 3. ADIM 2 — merge + push (ANA checkout'tan)

```
git -C /Users/okan/dev/pruvo fetch origin
git -C /Users/okan/dev/pruvo status -sb
git -C /Users/okan/dev/pruvo merge kral/paket3d-anahtar -m "3 KAPANDI: sahiplik haritasi 171/171, R_SAHIPLIK muafiyeti kaldirildi, kapi SERIT B'ye baglandi"
git -C /Users/okan/dev/pruvo push origin main
```

* Ağaçta **yabancı** ` M` / untracked varsa DOKUNMA (başka oturumun işi olabilir).
* main'de `add`+`commit` ayrı çağrı YOK; merge zaten atomik.
* `push --force` ASLA. Reddedilirse `fetch` + merge, rebase DEĞİL.
* Push D1 kolunda "YAZICI UÇUŞTA" derse bu **geçici**dir (K176) — 5-10 dakika sonra tekrar
  dene, `--no-verify` ARAMA.

## 4. ADIM 3 — merge SONRASI kapılar

```
python3 /Users/okan/dev/pruvo/tools/d1-sync.py --durum
python3 /Users/okan/dev/pruvo/tools/sahiplik-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/ci-kapsam-test.py
```
(Merge'den SONRA ana checkout dalın dosyalarını taşıdığı için bu üç komut artık DOĞRU ağaçta.)

CI teyidi — "en son koşum yeşildi" kanıt DEĞİL, **SHA'yı içeren** koşum:
```
gh -R Pruvo138/pruvo run list --limit 20 --json headSha,status,conclusion,databaseId,createdAt
git -C /Users/okan/dev/pruvo merge-base --is-ancestor <merge-SHA> <kosumun-headSha>
```
İkinci komut rc=0 vermiyorsa o yeşil senin işini derlememiştir → SUCCESS sayma.
Koşum hâlâ `in_progress` ise **"ÖLÇÜLEMEDİ + sebep"** yaz, yeşil yazma.

## 5. ADIM 4 — temizlik

```
git -C /Users/okan/dev/pruvo worktree remove --force /Users/okan/dev/pruvo/.claude/worktrees/p3e-merge
git -C /Users/okan/dev/pruvo branch -D kral/paket3d-anahtar
git -C /Users/okan/dev/pruvo branch -D kral/paket3b-evren
git -C /Users/okan/dev/pruvo worktree list
```
Silmeden önce: worktree porcelain temiz mi · dalın İÇERİĞİ gerçekten main'de mi
(`git branch --merged` YETMEZ) · ana ağaçta o işe benzeyen commit'siz değişiklik var mı.
Son `worktree list` çıktısı rapora BİREBİR.

## 6. RAPOR

Nöbet/dal kanonik mühendis rapor dosyasına, BAŞA ekle (üzerine YAZMA). İçinde:
* her kabul komutunun **ham** son satırı + rc'si + koştuğu `pwd`,
* iki `grep -c` kanıtı (R_SAHIPLIK=0 · nobet.yml'de kapı ≥1),
* merge SHA'sı, push sonucu, D1 durum satırı, CI teyidi (ya da `OLCULEMEDI` + sebep),
* son satır `TEMIZ=EVET` + `worktree list` çıktısı.

## 7. İŞÇİ TALİMATI

* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Kırmızı adımın üstünden atlayıp merge etme; herhangi bir adım kırmızıysa DUR.
* **DOKUNMA:** `urunler.json` · `crontab` · `~/.claude/cron/gozcu.py` · `~/.claude/cron/kilit.py`
  · `k166b-yayin-sinyali` worktree'si.
