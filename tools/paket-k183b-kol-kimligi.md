# PAKET K183b — nöbet eşzamanlılık kollarının KİMLİĞİ ve HEDEF KOL KANITI

> MİMAR HÜKMÜ (18 Ağu 2026, KraL). İşçi bu dosyayı uygular, KARAR VERMEZ.
> Ev: `/Users/okan/dev/pruvo/.claude/worktrees/k183-dispatch-grubu` (dal `kral/k183-dispatch-grubu`).
> Dokunulacak TEK dosya: `tools/is-akisi-kapisi.py`. Başka dosya değiştirme, commit atma.

## NEDEN (ölçüldü, iddia değil)

`77bb3195` ile main'e giren K183 yaması iki kusur taşıyor:

1. **KİMLİK ÇAKIŞMASI.** `G8` artık İKİ AYRI iddiayı adlandırıyor:
   - `G8 ... needs LISTESI KUCULDU` (yayın job'unun `needs` listesi — ESKİ, doğru sahibi)
   - `G8 PUSH GRUBU BENZERSIZLESTIRILMIS` (K183 ile EKLENEN)
   Aynı kimlik iki iddiaya bağlanınca kırmızının SEBEBİ okunamaz; hedef kol kanıtı da
   imkânsızlaşır (`startswith("G8")` hangi iddia?).

2. **KOLLAR AYRI ÖLÇMÜYOR.** Yeni G8/G9/G10'un ÜÇÜ de aynı üç alt-dizgeye bakıyor
   (`workflow_dispatch` · `github.run_id` · `|| 'push'`). `run_id` dispatch kolundan
   kalkınca ÜÇÜ birden kırmızı yanıyor. Commit mesajı "üç iddiayı ayrı ölçer" diyor;
   ölçüm bunu DOĞRULAMIYOR.

3. **MUTANT HEDEF KOLU KANITLAMIYOR (K182 sınıfı).** `_g_kendini_test` yalnız
   "hiç hata üretildi mi" bakıyor (`bulgu` boş mu). Commit mesajındaki
   "mutant 3/3 hedef kolu öldürdüğü kanıtlı" iddiası ÖLÇÜLMEMİŞ.

## YAPILACAK

### 1) Yeni kolları YENİDEN NUMARALA (kimlik çakışmasını bitir)

`G8` ESKİ sahibinde (`needs` listesi) AYNEN kalır. K183 ile gelen üç kol:

| yeni kimlik | iddia |
|---|---|
| `G9`  | push kolu SABİT tek gruptadır (maliyet sözleşmesi) |
| `G10` | dispatch kolu `github.run_id` ile BENZERSİZDİR (SHA seçilebilir) |
| `G11` | iki kol AYRIDIR (koşul doğru + kollar birbirinden farklı) |

Mevcut `G9`/`G10` metinleri bu yeni numaralara taşınır. `G7` (kapsam) DOKUNULMAZ.

### 2) Kolları GERÇEKTEN ayır — dizge avı değil, İFADE AYRIŞTIRMASI

`concurrency.group` değerinden `${{ ... }}` içi alınır ve ÜÇ parçaya ayrılır:

```
kosul        = "&&" öncesi
dispatch_kolu = "&&" ile "||" arası
push_kolu     = "||" sonrası
```

Ayrıştırma başarısızsa (işaretlerden biri yok / `${{` yok) **ÜÇ KOL DA**
`OLCULEMEDI (fail-closed KIRMIZI)` verir — biri yeşil kalamaz.

Her kol YALNIZ kendi özelliğini ölçer:

- **G9**: `push_kolu` tırnaklı bir SABİT olmalı (`'...'`) **ve** `github.` İÇERMEMELİ.
  (Değilse: her push kendi grubunu alır → koşum maliyeti patlar.)
- **G10**: `dispatch_kolu` `github.run_id` İÇERMELİ.
  (Değilse: elle tetiklenen koşum push kuyruğunda ezilir — K183'ün ta kendisi.)
- **G11**: `kosul` boşluk normalize edildiğinde tam olarak
  `github.event_name == 'workflow_dispatch'` olmalı **ve** `dispatch_kolu != push_kolu`.

🔴 Bir kolun koşulu BAŞKA kolun ölçtüğü özelliği İÇERMEZ. Ölçüsü: aşağıdaki
mutant → hedef kol eşlemesi birebir tutmalı (M2 yalnız G10'u yakar).

### 3) Mutant HEDEF KOLU kanıtlar (K182 sınıfı, bu pakette kapanır)

`G_MUTANTLAR` demetine **5. alan** eklenir: `hedef_kollar` (tuple).

- `kirmizi_olmali=True` olan HER mutant en az bir hedef kol beyan eder.
  Beyan boşsa self-test `G-HEDEF BEYANI YOK` ile KIRMIZI (fail-closed) — muafiyet YOK.
- `kirmizi_olmali=False` (KONTROL) satırlarında hedef kol boş tuple `()` olur.
- Harness her beyan edilen kol için ölçer:
  `any(h.startswith(kol + " ") for h in bulgu)`. Yakmayan kol için hata:
  `G-HEDEF KOL OLMEDI: <mutant> -> <kol> yanmadi (kirmizi BASKA koldan geldi)`.

**Beyanlar MİMAR tarafından yazılmıştır — çıktıdan TÜRETİLMEZ.** Ölçüm beyana
uymuyorsa doğru olan BEYAN değil KODdur; kolu düzelt, beyanı değiştirme:

| mutant | hedef kol(lar) |
|---|---|
| bloklamayan alarm job'u yayına geri kondu | `G1` |
| `deploy: needs` listesinden serit düşürüldü | `G8` |
| `deploy: needs` bütünüyle silindi | `G8` |
| nöbetin `on.push` tetiği kaldırıldı | `G2` |
| nöbet job'u `continue-on-error: true` | `G4` |
| nöbet job'u `if: false` | `G4` |
| Pages yayını nöbet şeridine kaydırıldı | `G3` |
| nöbet `uses:` ile yayın grafiğine bağlandı | `G5` |
| K183-M1 `cancel-in-progress: true` | `G6` |
| K183-M2 dispatch kolundan `run_id` kaldırıldı | `G10` (YALNIZ) |
| K183-M3 push kolu da `run_id` ile benzersizleşti | `G9`, `G11` |
| nöbet iş akışı SİLİNDİ | `G2`, `G3`, `G4`, `G6` |

### 4) META-VAKA — atıf mekanizmasının kendisi ölü olmasın

`_g_kendini_test` içinde (TABLOYA GİRMEZ, yerel kalır) bir vaka koşulur:
K183-M2 mutasyonu uygulanır ama hedef kol KASTEN yanlış beyan edilir (`("G1",)`).
Harness `G-HEDEF KOL OLMEDI` üretmezse → `G-ATIF MEKANIZMASI OLU` hatası eklenir.
Bu vaka `iddia` sayacını da artırır.

### 5) Sayaç

`G_IDDIA_TABANI` yeni eksen sayısına göre AYNI değişiklikte güncellenir ve
satırın yanına NEDENİ yazılır (kaç eksen, neden değişti).

## KABUL (işçi KOŞAR, çıktıyı AYNEN yapıştırır — özet YAZMAZ)

```bash
python3 /Users/okan/dev/pruvo/.claude/worktrees/k183-dispatch-grubu/tools/is-akisi-kapisi.py --kendini-test
```
Beklenen: `rc=0` ve çıktıda `SONUC: YESIL`.

Sonra ÜÇ ÇÜRÜTME koşumu (her biri AYRI, dosyayı geri al):

1. `G10`'un gövdesini (dispatch benzersizlik ölçümü) `pass` ile öldür → `--kendini-test`
   **KIRMIZI** olmalı ve hata metni `G-HEDEF KOL OLMEDI` + `G10` içermeli.
2. 5. alandaki `K183-M3` beyanını `("G9",)` yap (yani `G11` beyanını düşür) → kapı
   YEŞİL kalmalı (beyan daralması yakalanmaz; bu BİLİNEN sınırdır, raporda YAZ).
3. `G_IDDIA_TABANI`'nı 1 artır → `--kendini-test` **KIRMIZI** (sayaç ekseni canlı).

Ayrıca gerçek ağaç üzerinde kapıyı koştur ve rc'yi RAPORLA:
```bash
python3 /Users/okan/dev/pruvo/.claude/worktrees/k183-dispatch-grubu/tools/is-akisi-kapisi.py
```

## RAPOR

Mühendis raporuna (dalın kökünde, kanonik ad; BAŞKA AD YASAK) şunları YAZ:
- yukarıdaki dört koşumun **ham çıktısı** (kırpma yok, "özet" yok),
- değiştirdiğin satır aralıkları,
- ölçemediğin/yapamadığın her şey için ayrı `OLCULEMEDI:` satırı.

🔴 Commit ATMA, push ETME, `git` komutu ÇALIŞTIRMA. Mimar commit eder.
🔴 Yeşil tablo UYDURMA: koşmadığın komutun çıktısını yazarsan iş REDDEDİLİR.
