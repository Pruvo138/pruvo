# PAKET K178 — SERİT B'nin 126 adımından 114'ü KOŞMUYOR: ilk kırmızı geri kalanı maskeliyor

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ · kabul MİMARDA.
🔴 **Bu, "kabloya bağladık" diyen her paketin sessiz yalanıdır.**

## 1. ÖLÇÜLEN OLGU (mimar, `gh` ile — 18 Ağu, koşum `32133861890`, head `96268b7c`)

```
gh run view 32133861890 --json jobs --jq '[.jobs[]|select(.name=="serit-b")|.steps[]|.conclusion]
                                          | group_by(.) | map({durum:.[0], sayi:length})'
→ [{"durum":"failure","sayi":1},{"durum":"skipped","sayi":114},{"durum":"success","sayi":11}]
```

126 adımdan **11'i koştu, 1'i kırmızı, 114'ü SKIPPED.** Kırmızı adım listenin başlarında:
`Sentetik git fiksturu sizinti kapisi`. GitHub varsayılanı gereği bir adım `failure` olunca
job'un **kalan tüm adımları atlanır**.

**Somut sonuç (bu oturumun iki paketi):** ③'ün `Sahiplik haritasi kapisi — envanter + invaryant
(hijyen, SERIT B)` adımı listenin **EN SONUNDA** ve durumu `skipped`. Yani ③'ü "SERİT B'ye
bağladık" dedik, kapı main'de, adım `nobet.yml`'de — **ama hiç koşmadı ve koşmayacak.**
K168'in `recete-kapisi.py` adımı da aynı yerde.

## 2. HÜKÜM SINIFI — "kablo ≠ koşuyor"

Bu evde ölçülmüş bir kural vardı: **muafiyet "koşuyor" demek değildir.** Bugün kardeşi
ölçüldü: **kablo da "koşuyor" demek değildir.** `ci-kapsam-test.py` bir testin iş akışında
GÖRÜNDÜĞÜNÜ ölçüyor; **ERİŞİLEBİLİR** olduğunu ölçmüyor. Kırmızı bir adımın arkasına
eklenen nöbetçi, envanterde "kapsanmış" görünür ve hiç koşmaz
([[kirmizi-adim-sonrakini-maskeler]] · [[kapi-varlik-olcer-yokluk-olcmez]]).

⚠️ Bu bir yayın blokeri DEĞİL (SERİT B `deploy: needs`'te değil, adı da "yayını BLOKLAMAZ").
Zarar **geri bildirim körlüğü**: 114 nöbetçinin kırmızısı hiç görünmüyor. Bir kapı bozulsa
kimse öğrenmez.

## 3. HÜKÜM

**H1 — SERİT B'de bir adımın kırmızısı diğerlerini KÖRLEŞTİREMEZ.** `serit-b` job'undaki
**her kapı adımı** birbirinden bağımsız koşar: adım düzeyinde `continue-on-error: true`
(job sonucu yine de kırmızı raporlar) ya da eşdeğer `if: always()` düzeni.
🔴 Şerit **yayını bloklamadığı için** bu bir gevşetme DEĞİLDİR: bugün 114 kapı hiç
konuşmuyor; sonrasında 126'sı da konuşacak. Kırmızı sayısı ARTACAK — bu beklenen ve
istenen sonuçtur, gizli kırmızıların görünür olmasıdır.

**H2 — Değişiklik yalnız SERİT B'ye.** Bloklayıcı şeritlerde (`serit-a2`/`a3`, `deploy`
zinciri) **hiçbir şey değişmez**; orada fail-fast doğru davranıştır. Kapsamı karıştırma
([[kapi-kapsam-genisletme-tuzagi]]).

**H3 — Önce/sonra sayısı ölçülür ve rapora yazılır.** Onarımdan sonraki ilk SERİT B
koşumunda adım durum dağılımı yeniden alınır; `skipped` sayısı **114'ten belirgin şekilde
düşmüş** olmalı. Düşmüyorsa onarım tutmamıştır.

## 4. KABUL (çalıştırılabilir)

### 4.1 Yerel — iş akışı sözleşmesi nöbetçisi
`serit-b` job'unun **her kapı adımının** bağımsız koştuğunu ölçen bir kabul testi
(`tools/serit-b-maskeleme-test.py`, ad işçinin): `nobet.yml`'i okur, `serit-b` job'undaki
kapı adımlarını sayar ve **bağımsızlık işareti taşımayan** adımı RED eder.

```
python3 tools/serit-b-maskeleme-test.py
```
son satır + rc=0:
```
ADIM=<n> BAGIMSIZ=<n> MASKELEYEN=0 MUTANT=3/3 KONTROL=2/2
```

**Mutantlar (3/3 KIRMIZI):**
* **M1** — bir adımdan bağımsızlık işaretini kaldır → `MASKELEYEN=1`, adım adıyla RED.
* **M2** — evreni boş kümeye indir (`ADIM=0`) → YEŞİL DÖNMEMELİ, rc≠0 `OLCULEMEDI`.
* **M3** — nöbetçiyi bloklayıcı şeride de uygula (kapsam genişletme) → RED.

**Kontroller (2/2 YEŞİL):** **K1** `serit-a2`/`a3` adımları DEĞİŞMEMİŞ sayılır (kapsam
dışı). **K2** kapı olmayan altyapı adımları (`checkout`, `setup-python`, `Post Run …`)
maskeleyen sayılmaz — yanlış-pozitif nöbetçisi.

### 4.2 CI kablosu — muafiyet YOK
Bu yeni nöbetçi de `serit-b`ye kendi adımıyla bağlanır ve `ci-kapsam-test.py` rc=0 verir;
`serit-b-maskeleme-test.py` **muaf listesinde GÖRÜNMEZ** (davranışsal kontrol, `grep` değil).

### 4.3 🔴 ASIL KABUL — canlı koşum (elle koşum SAYILMAZ)
Merge'den sonraki ilk SERİT B koşumunda:
```
gh -R Pruvo138/pruvo run view <run_id> --json jobs --jq '[.jobs[]|select(.name=="serit-b")|.steps[]|.conclusion] | group_by(.) | map({durum:.[0], sayi:length})'
```
`skipped` sayısı **114'ten belirgin düşmüş** ve ③'ün `Sahiplik haritasi kapisi …` adımı
artık `skipped` DEĞİL. Bu iki şey ölçülmeden paket KAPANMAZ.
⚠️ Koşum kuyrukta `cancelled` olursa **`OLCULEMEDI` yaz**, yeşil yazma; ard arda push
gelmeyen bir pencerede tekrar ölç.

## 5. SINIRLAR

* Kapıların KENDİ mantığına DOKUNULMAZ; bu paket yalnız **çalışma sırasını/bağımsızlığını**
  onarır. Kırmızı bir kapıyı susturmak YASAK — amaç tam tersi, konuşturmak.
* `Sentetik git fiksturu sizinti kapisi`nin kırmızısı bu pakette ÇÖZÜLMEZ (ayrı kalem);
  yalnız artık diğer 114'ü körleştirmeyecek.
* Bloklayıcı şeritler kapsam dışı (H2).
* Worktree: bir tane aç, aynı turda kaldır.

## 6. İŞÇİ TALİMATI

* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Bütçenin yarısında elindekini commit et, raporu kapat — yarım ama kayıtlı iyidir.
* Raporu ÖNCE oluştur; başka turun raporunun ÜZERİNE YAZMA, başa EKLE. Her sayının yanında
  onu üreten komut.
* Yeni nöbetçi sabit mutlak kök KULLANMAZ ([[kapi-sabit-kok-yanlis-agaci-olcer]]).
* **DOKUNMA:** `urunler.json` · `crontab` · `DEVAM.md` · `~/.claude/cron/` ·
  bloklayıcı şerit tanımları.
