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

## 2. ŞERİT DÜZELTMESİ — G5, G6, G7 BLOKLAYICI KOLA

Bugünkü bloklayıcı kol: `[B1..B5, C1..C5, D6, D7, D8, D11]` = 14.
**Şunlar eklenecek → 17:** `G5`, `G6`, `G7`.

Gerekçe (rapora AYNEN geçir):
- **G6/G7**: `C5` (telefon numarası sızıntı taraması) **bloklayıcı** kolda. Ham alt-dizge
  taraması yanlış-pozitife açıktır; G6 (bağlamsız sayı dizisi TETİKLEMEZ) ve G7 (gerçek
  ihlal TETİKLER) tam olarak C5'in yanlış-pozitif güvencesidir. **Bloklayıcı bir iddianın
  yanlış-pozitif güvencesi bloklamayan şeritte durursa**, C5 bir gün sebepsiz kırmızı
  yakar, TÜM ekibin yayını durur, ve o anda "haklı mı" sorusunu ölçecek test SERIT B'de
  sessizce yeşil bekler. Kapının kendi doğruluğu, kapının şeridinde ölçülmelidir.
- **G5**: "bir `iddia()` çağrısı silinince kapı `OLCULEMEDI` + sıfır-dışı verir"
  invaryantı, bloklayıcı koldaki **diğer bütün iddiaları** koruyor. Bloklamayan şeritte
  durursa, bloklayıcı kolun sessizce eksilmesi yayın öncesi görülemez.

**Bloklayıcıya ALINMAYANLAR ve SEBEBİ** (rapora yaz, boş bırakma):
`G1` (ürün çalışıyor — sızıntı değil) · `G2/G3/G4` (DoS sertleştirmesi) ·
`G8/G9/G10` (origin/ürün çalışıyor) · `G11` (tek kaynak hijyeni) ·
`A*`, `D1..D5`, `D9`, `D10`, `D12`, `E*`, `K*`, `F5`, `R1`.
Chip ölçütü: **bloklayıcı kol = ödeme/veri sızıntısı riski + müşteriye yanlış davranan
kollar + o kolların yanlış-pozitif güvenceleri.** Kalanı SERIT B.

`BEKLENEN_IDDIA_SIZINTI` sabitini **aynı turda** 14'ten 17'ye güncelle (G5 invaryantı
yoksa kendi kapımız kırmızı yanar — bu doğru davranış, ama sabit güncellenmezse gürültü).

---

## 3. `shop/test/kabul.js` REGRESYONU — `OLCULEMEDI` KAPATILACAK

TUR 2b raporunda: `node --test shop/test/` Node 25'te "Cannot find module" ile düştü
(dizin girişi bu runtime'da suite değil), `shop/test/kabul.js` başlatıldı ama kapanış
kodu ALINAMADI.

`shop/src/index.js`'e bir router satırı ekledik; riski düşük ama **ölçmeden "yok"
denmez**. Yap:
- Deponun gerçek koşum satırını bul (`shop/KURULUM.md` ve `shop/test/kabul.js` başındaki
  yorumlara bak) ve **onu** kullan.
- Koş, **çıkış kodunu ve son özet satırını** al.
- Uzun sürüyorsa süreyi ölç ve yaz; düşen varsa **düşenlerin adını** ver.
- Gerçekten koşturulamıyorsa (ör. ağ/secret istiyor) `OLCULEMEDI` + **sebep** + hangi
  komutu denediğin. Sebepsiz `OLCULEMEDI` KABUL DEĞİL.

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
