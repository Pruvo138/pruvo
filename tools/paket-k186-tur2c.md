# K186 — TUR 2c (KAPANIŞ TURU): üç açık kalem

TUR 2b bağımsız doğrulandı: `IDDIA=50 DUSEN=0 MUTANT=50/50 KONTROL=50/50` rc=0 ·
`--sizinti` `14/14` rc=0 · `ci-kapsam-test.py` **YEŞİL** rc=0 · temizlik `F1..F5 + R1` rc=0.
CI kablosu ölçüldü: `deploy.yml:818` **`serit-a3`** job'unda (sınırlar: `build:38` ·
`serit-a2:349` · `serit-a3:790` · `serit-a4:1310`), `deploy: needs:` listesinde geçiyor →
yayını **gerçekten** blokluyor. `nobet.yml:366/368/370` üç SERIT B adımı.

Üç kalem kaldı. Sıra önemli değil, üçü de kapanacak.

---

## 1. 🔴🔴 MUTANT İZOLASYONU **BEYAN, ÖLÇÜM DEĞİL** — en ağır kalem

Bağımsız doğrulama tespit etti (`talep-hatti-test.py:305-306, 319-320, 212-215, 351-360`):
her mutant **yalnız kendi hedef iddiasını** `--only=<ad>` ile koşuyor. Basılan
`dusen_liste=[hedef]` satırı bir **tam küme karşılaştırması DEĞİL**; `tek_iddia`
koşuluna göre yazdırılan bir etiket.

**Zarar:** çıktı "bu mutant tam olarak bir iddia düşürdü" diye OKUNUYOR, ama bu
ölçülmedi. K182'nin bütün mesele ettiği şey tam olarak bu. Somut örnek: **A4** mutantı
(`crypto.getRandomValues` → `Math.random`) **A1**'i de düşürüyor olabilir — kod A4
mutantında A1'i hiç koşturmadığı için `ÖLÇÜLEMEDİ`. Yani bugün elimizde "her mutant bir
iddia" iddiasının **hiçbir kanıtı yok**, yalnızca öyle görünen bir satır var.

**HÜKÜM:** her mutant için **TÜM** iddialar değerlendirilecek ve düşen kümenin tam
olarak `{hedef}` olduğu **ölçülecek**.
- Mutant kaynağıyla **tam batarya** koşulacak (`--only` YOK), düşen iddia kümesi
  toplanacak, `dusen_kume` AYNEN basılacak (etiket değil, gerçek küme).
- `dusen_kume == {hedef}` ise `IZOLE=EVET`; değilse `IZOLE=HAYIR yan=[...]`.
- 🔴 **İzole olmayan mutant sessizce geçmeyecek.** İki yoldan biri:
  (a) mutantı hedefi izole edecek şekilde yeniden yaz; ya da
  (b) izole edilemiyorsa **GEREKÇELİ İSTİSNA olarak BEYAN et** — kaynakta adı geçen bir
      istisna listesine gerekçesiyle koy, çıktıda `IZOLE=HAYIR (BEYANLI: <gerekce>)` bas,
      ve rapora yaz. **Beyansız istisna YASAK.**
- Maliyet: 50 mutant × tam batarya. Ölçtüğün süreyi rapora yaz; SERIT B'de kabul edilebilir
  (bloklayıcı kol yalnız 14 iddia koşuyor ve orada `--sizinti` bataryası kullanılacak).

**Kabul:** çıktıda her mutant satırı `dusen_kume=[...]` **ve** `IZOLE=EVET|HAYIR(...)`
taşıyacak; özet satırına `IZOLE=<n>/<toplam>` eklenecek. `IZOLE` sayısı toplamdan
küçükse ve beyanlı istisna yoksa **sıfır-dışı çıkış**.

---

## 2. ŞERİT DÜZELTMESİ — MİMAR HÜKMÜ: ÜÇÜ **TEK KOVAYA KONMAZ**

Bugünkü bloklayıcı kol: `--sizinti` = `[B1..B5, C1..C5, D6, D7, D8, D11]` = 14.

### 2.1 `G6` + `G7` → `--sizinti` EKSENİNİN **İÇİNE** (14 → **16**)

Gerekçe (rapora AYNEN geçir): `C5` (telefon numarası sızıntı taraması) bloklayıcı kolda.
G6 (bağlamsız sayı dizisi TETİKLEMEZ) ve G7 (gerçek ihlal TETİKLER) onun
yanlış-pozitif / yanlış-negatif güvenceleridir. **İkiz iddiaları ayrı şeride bölmek
"aynı alan, iki hüküm — biri sessiz" sınıfıdır.**
🔴 Asıl ağırlık **G7**'dedir: C5 zayıflarsa hata **SESSİZDİR** — gerçek numara
yakalanmaz, yayın yeşil akar, PII public repoya iner. **Sessiz hata bloklayıcı kola
aittir.** G6 gürültülü hatadır (sebepsiz kırmızı) ama ikizinden ayrılmaz.

`BEKLENEN_IDDIA_SIZINTI` **14 → 16**, aynı turda.

### 2.2 `G5` → BLOKLAYICI ama `--sizinti` İÇİNE **DEĞİL**, **KENDİ ADIMI** olarak

G5 bir sızıntı iddiası değil; bloklayıcı kümenin **ÜSTÜNDE** duran bir meta-invaryanttır.
Sızıntı bayrağının içine tıkılırsa **eksenin adı yalan olur** ve `--sizinti` sayısı iki
farklı şeyi sayar.

Uygulama: `tools/talep-hatti-test.py`'ye **ayrı bayrak** (ör. `--capa`) ve
`deploy.yml` `serit-a3`'e **kendi adımı**:
```yaml
      - name: "Talep hatti iddia-capa invaryanti (BLOKLAYICI)"
        run: python3 tools/talep-hatti-test.py --capa
```

🔴 **ŞART — ÇAPA SAYI OLMADAN G5 KAPI DEĞİLDİR.** "Bir `iddia()` silinince `OLCULEMEDI`"
ancak **beklenen sayı yazılıysa** ölçülebilir. Çapasız hâlde iddia silinince kapı
yalnızca **daha az iddia sayar ve YEŞİL yanar** — K189'un aynısı: *kapı varlığı ölçer,
yokluğu ölçmez*.
- Çapa **TEK KAYNAKTAN** gelecek (kapının kendi ürettiği sayı). **İkiz tanım YASAK** —
  sayıyı iki yere yazma.
- Mutant, kırmızının **SEBEBİNİN silinen iddia olduğunu AYRICA** kanıtlayacak (K182):
  yalnız "rc=1 geldi" yetmez, çıktı `OLCULEMEDI: <beklenen> bekleniyordu, <gerceklesen>
  kosdu` satırını taşıyacak ve mutant o satırı üretecek.

### 2.3 Kalan G'ler SERIT B'de KALIR — **SEBEP SATIRI ZORUNLU**

`G1` (ürün çalışıyor — sızıntı değil) · `G2/G3/G4` (DoS sertleştirmesi) ·
`G8/G9/G10` (origin / ürün çalışıyor) · `G11` (tek kaynak hijyeni) ·
`A*`, `D1..D5`, `D9`, `D10`, `D12`, `E*`, `K*`, `F5`, `R1`.
🔴 **Sebep satırı olmayan iddia SERIT B'ye İNMEZ.** Her biri için rapora tek cümlelik
gerekçe yaz; boş bırakılan varsa iş TESLİM EDİLMEZ.

Ölçüt: **bloklayıcı kol = veri sızıntısı riski + müşteriye yanlış davranan kollar +
o kolların yanlış-pozitif/negatif güvenceleri.** Meta-invaryant ayrı adımda. Kalanı SERIT B.

### 2.4 🔴 G6/G7 FİKSTÜRÜ **GERÇEK NUMARA TAŞIMAZ**

Kabul fikstüründe deponun gerçek numaraları **kullanılmayacak**; desene uyan **SENTETİK**
numara üretilecek. Ve nöbetçinin (`kisisel-veri-test.py` / C5) **muafiyet listesini
fikstürü geçirmek için GENİŞLETME** — muafiyetle geçirilen test kapıyı **fail-open**
yapar. (Bu kural mimarın kendi kusurundan çıktı: paket dosyasında gerçek arama numarası
yazılıydı, nöbetçi haklı olarak kırmızı yaktı, numara çıkarılarak düzeltildi — muafiyet
eklenerek DEĞİL. Kalıcı hâli budur.)

---

## 3. `shop/test/kabul.js` REGRESYONU — `OLCULEMEDI` KAPATILACAK

TUR 2b raporunda: `node --test shop/test/` Node 25'te "Cannot find module" ile düştü
(dizin girişi bu runtime'da suite değil), `shop/test/kabul.js` başlatıldı ama kapanış
kodu ALINAMADI.

🔴 **MİMAR HÜKMÜ: bu evde `OLCULEMEDI` FAIL-CLOSED'dır (K141/K177).** "Riski düşük"
diyerek kapatılmaz. `shop/src/index.js`'e router satırı ekledik; merge ÖNCESİ ölçülecek.

- Dizin girişi yerine **AÇIK DOSYA YOLUYLA** koştur:
  `node --test /Users/okan/dev/pruvo/.claude/worktrees/zen-lehmann-d54167/shop/test/kabul.js`
  ya da deponun kanonik koşucusunu kullan (`shop/KURULUM.md` ve `shop/test/kabul.js`
  başındaki yorumlara bak).
- Koş, **çıkış kodunu ve son özet satırını** al. Düşen varsa **adlarını** ver.
- 🔴 **Node 25'te gerçekten düşüyorsa bu bir BULGUDUR, dipnot değil.** O zaman:
  `.github/workflows/deploy.yml` ve `nobet.yml` içindeki `actions/setup-node` sürümünü
  **ölç** (`node-version` satırını dosya:satır ile ver), yerelde `node --version` ölç ve
  **yerel/CI farkını rapora yaz**. Sebep: bu turda alınan **bütün yerel rc=0'lar o farkın
  altındadır** — CI başka bir Node sürümünde koşuyorsa yeşilimiz o sürümde ölçülmemiştir.
- Ölçemezsen `KAPSAM DISI` **DEĞİL**, `OLCULEMEDI` + **sebep** + denediğin komut diye ilan
  et ve rapora "deftere kalem açılacak" notu düş. Sebepsiz `OLCULEMEDI` KABUL DEĞİL.

Ayrıca şunu da koş ve sonucunu rapora yaz (mimar kendi paket dosyasındaki bir ihlali
düzeltti, teyit gerekiyor):
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-lehmann-d54167/tools/kisisel-veri-test.py
```

---

## TESLİM
Raporu (worktree kökündeki mevcut mühendis raporu dosyası) **GÜNCELLE**, yeni dosya açma.
Şu altı komutun ham çıktısı ve çıkış kodu bulunacak:
```
node shop/test/talep.mjs
python3 tools/talep-hatti-test.py
python3 tools/talep-hatti-test.py --sizinti
python3 tools/talep-temizlik.py --kendini-test
python3 tools/ci-kapsam-test.py
python3 tools/kisisel-veri-test.py
```
artı `shop/test/kabul.js` koşumu (ya da gerekçeli `OLCULEMEDI`).

**YASAK:** `git commit` · `git push` · `wrangler deploy` · `d1-sync.py --sema` ·
`urunler.json` ve `index.html`'e dokunmak · `shop/wrangler.toml`'a cron/KV/trigger
eklemek (R2 = **K190**, bu paketin kapsamı DEĞİL).
**Komut stili:** dolar-değişken, dolar-parantez, `for`, `while`, `cd`, çıktı yönlendirme,
heredoc YASAK.
**Sayı uydurma.** Ölçemediğine `OLCULEMEDI` + sebep.
