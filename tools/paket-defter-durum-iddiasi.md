# PAKET K167 — Defterdeki DURUM iddiasi olculmeden yaziliyor (SINIF kalemi)

> ⚠️ Bu paket once K166 diye acildi; posta kutusunda baska bir oturum K166'yi (`is-akisi-kapisi.py`
> yayin sinyali safligi) 01:2xZ'de ALMISTI — numara K167'ye cevrildi. Kalem numarasi tahsisi
> paylasilan defterde YARISIYOR (K161 iki kez, K164 iki kez, "K160" iki farkli is, K166 iki kez);
> bu kapinin OLCTUGU eksen DEGIL, ayri kalem.

Mimar: KraL · 18 Agu 2026 · hedef kat: MUHENDIS (kapi kodu Claude katinda kalir, ama
yazimi mimar eli DEGIL — `tools/` altina mühendis koyar).

## 1. OLCULEN OLGU (yeniden uretilebilir)

Uc komut, uc olgu:

```
git -C /Users/okan/dev/pruvo show 1c741e54:DEVAM.md   # satir 11-12
git -C /Users/okan/dev/pruvo show 1c741e54^:DEVAM.md  # K150/K148/K160 HIC GECMIYOR
git -C /Users/okan/dev/pruvo log --oneline main..f3d5a2c3   # BOS
```

1. `1c741e54:DEVAM.md:11-12` sunu yaziyor:
   `KOSUYOR (baska oturumlar — DOKUNMA): ... BaBa kalemleri K150+K148 (worktree
   competent-dijkstra-754039)`.
2. Ayni anda `DEVAM-ARSIV.md:34-40` ayni uc kalemi **KAPANDI** olarak, SHA'lariyla tasiyor
   (`ed47d317`, `2f87a8bc`, `b180fa1a`).
3. `main..competent-dijkstra-754039` **BOS** — o worktree'de main disi commit YOK. Ayni sey
   `amazing-hamilton-c45e91` icin de olculdu (`10ae08d1` main'in ATASI).

Yani defter, **kapali** bir isi **kosuyor** diye ve **bos** bir worktree'ye atfederek
ilan etti. Devralan oturum icin bu iki kayipli sinyal: mukerrer tur acar, ya da bos bir
worktree'de is arar.

## 2. KOK NEDEN — VE ONERILEN CARENIN NEDEN YETMEDIGI

Kutuya yazilan oneri "ust blok birikimli olsun / her oturum yalniz kendi satirini eklesin"
idi. **Bu, olculen zarari onlemezdi:** `1c741e54` bir satiri SILMEDI, **yanlis bir satir
EKLEDI** (`1c741e54^`'de kalemler defterde hic yok). Ekleme-yalniz bir disiplin, yanlis
KOSUYOR iddiasini oldugu gibi korurdu.

Kok neden ekleme/silme ekseni degil, **kaynak** ekseni: bir oturum, BASKA oturumun kaleminin
durumunu **kendi hafizasindan** yaziyor; defterde bu iddiayi bir olcume baglayan hicbir sey
yok. `23b37efc`'nin ayni satirlari dusurmesi AYRI ve daha hafif bir kusurdur — icerik
`DEVAM-ARSIV.md`'de duruyordu, yani kayipsizlik kurali ([[defter-kotasi-kapanista-1e1]])
zaten islemisti; sinifi o degil, (1) tasiyor.

Ikinci mekanik bulgu: `defter-rotasyon.py` bir maddeyi ancak **ilk anlamli jeton** kapanis
isaretcisiyse tasir (K128 korumasi). `**K150** rc=5 ...` biciminde yazilan kapanis ozeti bu
olcutu gecemez → kalem canli defterde **takili kalir**, ve takili kaldigi yer ust bloktur;
ust blok da her oturumda elle yeniden yazilir. Yani bicim, kalemi tam da en cok ezilen yere
cakiyor. Bu kod degisikligi ISTEMEZ, YAZIM KURALI ister (§4).

## 3. INVARYANT (kapinin olcecegi tek sey)

> **DEVAM.md'de bir kalem hakkindaki DURUM iddiasi, iddia edilen kaynakta dogrulanabilir
> olmalidir.** Iki kol:
>
> * **Kol A (capraz kaynak):** `DEVAM-ARSIV.md`'de KAPANIS kaydi bulunan bir `K<n>` id'si,
>   `DEVAM.md`'de `KOSUYOR` / acik isaretci ile yazilamaz. Kalem gercekten yeniden acildiysa
>   satir `YENIDEN ACILDI` jetonu **ve** gerekce tasir; jeton varsa kapi susar.
> * **Kol B (worktree iddiasi):** `DEVAM.md`'de bir worktree adi `KOSUYOR`/`DOKUNMA`
>   baglaminda aniliyorsa, o worktree `git worktree list` ciktisinda BULUNMALI **ve**
>   `git log --oneline main..<ref>` **BOS OLMAMALI**. Ikisinden biri tutmuyorsa RED.

Kapsam bilerek DARDIR ([[kapi-kapsam-genisletme-tuzagi]]): kapi, kalemin *dogru* kapanip
kapanmadigini yargilamaz; yalnizca **iddia ile kaynagin ayrismasini** olcer.

## 4. YAZIM KURALI (kod degil, disiplin — mimar bu turda uyguladi)

* Kapanis ozeti maddesi/blogu **kapanis isaretcisiyle BASLAR** (`## ✅ K150 ... KAPANDI`,
  `- ✅ **K150** ...`), boylece `defter-rotasyon.py` onu tasiyabilir ve canli defterde
  cakili kalmaz.
* **KARMA BLOK YASAK:** ayni `## ` blogu hem `✅ KAPANDI` hem `BEKLIYOR`/`OKAN'DA`/`KOSUYOR`
  tasimaz. Karma blok rotasyon icin fail-closed'dir → sonsuza kadar elle yeniden yazilir.
  Acik satirlar `## ACIK KALEMLER` / `## OKAN'DA` bolumlerine gider.

## 5. KABUL (calistirilabilir; "bakildi iyi" DEGIL)

Mühendis `tools/defter-durum-kapisi.py` yazar; `kancalar/pre-commit`'e **DEVAM.md staged
ise** kolu baglanir (CI'da kosmaz — worktree ekseni yerel olgudur).

```
python3 /Users/okan/dev/pruvo/tools/defter-durum-kapisi.py --kendini-test
```

son satiri sunu basar ve rc=0 verir:

```
VAKA=<n> DUSEN=0 MUTANT=4/4 KONTROL=2/2
```

### 5.1 Gercek-tarih fiksturleri (uydurma fikstur YASAK — [[nobetci-fikstur-sekli]])

| # | Fikstur | Beklenen |
|---|---------|----------|
| V1 | `git show 1c741e54:DEVAM.md` + o andaki arsiv kapanis kaydi | **RED**, gerekce Kol A, `K150` ve `K148` ADIYLA |
| V2 | `git show 1c741e54:DEVAM.md`, worktree ekseni | **RED**, gerekce Kol B, `competent-dijkstra-754039` ADIYLA (`main..` bos) |
| V3 | `git show 10dca711:DEVAM.md` (duzeltilmis hal) | **rc=0** |
| V4 | Kalem `YENIDEN ACILDI` jetonuyla acik yazilmis | **rc=0** (kacis yolu calisiyor) |

### 5.2 Mutasyon bataryasi (4/4 KIRMIZI olacak)

* **M1** — Kol A karsilastirmasini kaldir → V1 yesile doner (kapi kor).
* **M2** — Kol B'de `main..<ref>` bosluk kontrolunu kaldir, yalnizca "worktree var mi"ya bak
  → V2 yesile doner (bu tam olarak `1c741e54`'un yaptigi hata: worktree VARDI, isi YOKTU).
* **M3** — `YENIDEN ACILDI` kacis jetonunu her satirda gecerli say → V1 yesile doner.
* **M4** — Arsiv okunamadiginda `0` don (fail-open) → **RED kalmali**; okunamayan kaynak
  `OLCULEMEDI` olup rc≠0 verir ([[fail-slow-fail-opendir]], `0` yalnizca OLCULEN sifirdir).

### 5.3 Kontrol mutantlari (2/2 YESIL kalacak — yanlis-pozitif nobetcisi)

* **K1** — Acik bir maddenin DEVAM satirinda parantez ici `(... KAPANDI: ...)` atfi
  gecen gercek vaka (K128'in canli vakasi) → kapi **susmali**.
* **K2** — Siradan bir defter duzenlemesi (yeni acik kalem eklemek, metin duzeltmek) → rc=0.

## 6. SINIRLAR / BILINEN ACIKLAR

* Kapi **yerel** olgudur: `git worktree list` CI runner'inda anlamsizdir. CI'a BAGLANMAZ;
  baglanirsa Kol B daima kirmizi/anlamsiz olur.
* `DEVAM-ARSIV.md` git DISIDIR → kapi arsivi diskten okur. Arsiv yoksa (kardes evler,
  taze klon) kapi **kapsam disi** deyip sessiz gecer, `0` demez (M4).
* Kalem NUMARASI cakismasi (K161 iki kez, K164 iki kez, "K160" iki farkli ise) ayri bir
  kusurdur; bu kapi onu OLCMEZ. Ayri kalem olarak durur.
