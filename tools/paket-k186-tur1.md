# K186 — TUR 1 TALİMATI (işçi)

Çalışma ağacın: `/Users/okan/dev/pruvo/.claude/worktrees/zen-lehmann-d54167`
(git worktree, dal `kral/k186-talep-hatti`). TÜM yollar bu ağacın İÇİNDE olacak;
`/Users/okan/dev/pruvo` ana ağacına **TEK BAYT** yazma.

## ÖNCE OKU
- `tools/paket-k186-talep-hatti.md` — senin spec'in, **hükümdür**, tartışma yok.
- Desen kaynağı: `shop/src/ref.js` ve `shop/test/ref-route.mjs`.

## BU TUR (TUR 1) KAPSAMI — yalnız şunlar
1. `tools/d1-sema.sql` **SONUNA** `talepler` tablosu + indeksi EKLE (spec §2, aynen).
   Mevcut satırlara DOKUNMA.
2. `shop/src/talep.js` YAZ (spec §1 kod üreteci + §3 savunma sırası + yanıt şekilleri).
   Saf modül, `wrangler` importu yok.
3. `shop/src/index.js` içine **TEK** router satırı ekle (spec §3).
4. `shop/test/talep.mjs` YAZ — davranış ekseni (spec §5 tablosundaki B1–B5, D1–D4,
   E1–E2). D1 çağrısını sahte bir `env.KATALOG` ile **say**.
5. `tools/talep-hatti-test.py` YAZ — `shop/test/talep.mjs`'i alt süreç olarak koşturur
   + spec §5 C1–C5 kaynak taramasını **KENDİ** yapar (ayrıştırma, `grep` değil)
   + A1–A4 kod üreteci eksenini ölçer.
   **İki kollu:** `--sizinti` bayrağı yalnız B1–B5 + C1–C5 koşar; bayraksız TAM batarya.
   Çıktı biçimi tek satır: `IDDIA=n DUSEN=n MUTANT=k/k KONTROL=n/n`
6. `tools/talep-temizlik.py` YAZ (spec §4; varsayılan KURU koşum, `--uygula` olmadan
   DELETE yok, `--kendini-test` kolu).

## BU TURDA YAPMA
- CI kablolama (`deploy.yml` / `nobet.yml` / `ci-kapsam-test.py`) — **TUR 2**.
- `git commit` ATMA (sandbox `.git` kilidine yazamaz, boşa iş). `git push` YAPMA.
- `wrangler deploy` YAPMA. `python3 tools/d1-sync.py --sema` KOŞTURMA.
- `urunler.json` ve `index.html`'e DOKUNMA (K184 chip'i orada çalışıyor).

## KOMUT STİLİ
Dolar-işaretli değişken, dolar-parantez, `for`, `while`, `cd`, çıktı yönlendirme,
heredoc **YASAK**. Betikleri doğrudan dosyaya yaz, sonra düz `python3 /tam/yol.py` ile koş.

## TESLİM
Yazdığın her dosyayı **GERÇEKTEN koştur**, ham çıktıyı ve çıkış kodunu gör.
Son mesajında şu sayıları ver:
- `talep-hatti-test.py` bayraksız kolun IDDIA/DUSEN sayıları + çıkış kodu
- `talep-hatti-test.py --sizinti` kolun IDDIA/DUSEN sayıları + çıkış kodu
- `shop/test/talep.mjs` düşen sayısı
- `talep-temizlik.py --kendini-test` sonucu

Ölçemediğin hiçbir şeye "geçti" deme; ölçemediğine `OLCULEMEDI` + sebep yaz.
**Sayı uydurma.**
