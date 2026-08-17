# PAKET K141 — Nobet probu FAIL-OPEN: bos ciktiyi `allow` sayiyor

Mimar: KraL · 18 Agu 2026 · hedef kat: MUHENDIS/ISCI (kod `tools/kapi-envanteri.py`'de;
mimar eli surmez). BaBa'nin K141 hukmunun icrasi.

## 1. OLCULEN OLGU (18 Agu, bagimsiz tur)

```
python3 /Users/okan/dev/pruvo/tools/kapi-envanteri.py          # rc=1
```
```
mimar-icra-kapisi      OK     OK      EKSIK     DUSUK
mimar-kod-kilidi       OK     OK      EKSIK     DUSUK
SONUC: 5/7 kapi TAM — EKSIKLER:
  - mimar-icra-kapisi: NOBETTE degil — reddetmesi gerekeni REDDETMEDI (reddetmeli=allow kabuletmeli=allow)
  - mimar-kod-kilidi:  NOBETTE degil — reddetmesi gerekeni REDDETMEDI (reddetmeli=allow kabuletmeli=allow)
```

🔴 **KARSI-KANIT — kapilar CANLI.** Ayni gun, ayni ana checkout'ta, mimar oturumunda bu iki
kapi fiilen REDDETTI: `wc -l` (icra kapisi) · `sort` (icra kapisi) · `>` yonlendirmesi ve
`$(...)` (komut stili) · repo disi yol · isci sarmalayicisinin yanlis argüman sayisi.
Yani "reddetmesi gerekeni REDDETMEDI" hukmu KAPI hakkinda DEGIL, PROB hakkinda bir olgudur.

## 2. KOK NEDEN — olcum aletinin kendisi fail-open

`tools/kapi-envanteri.py::_karar()`:

```
63:    cikti = (sonuc.stdout or "").strip()
64:    if not cikti:
65:        return "allow"
```

**Bos cikti `allow` sayiliyor.** Bu tek satir iki AYRI dunyayi ayni jetona esliyor:

| gercek durum | probun gordugu |
|---|---|
| kapi payload'i inceledi ve IZIN verdi | `allow` |
| kapi hic konusmadi (cokme / import hatasi / erken `return` / stderr'e yazip stdout'a yazmama) | `allow` |

Ikisi ayirt edilemedigi icin `reddetmeli=allow` satiri **teshis tasimiyor**; K141'in adi
("OLCULEMEYEN NOBET") tam olarak budur. Ayrica `sonuc.returncode` ve `sonuc.stderr`
HIC OKUNMUYOR (`:58-62`) — kapi patlasa bile prob sessizce `allow` der.
Ayni sinif ikinci kolda da var: `:69` `except ValueError: return "PARSE-HATASI"` en azindan
ayri bir jeton uretiyor, ama `_nobet_karar` (`:78`) onu yalnizca `kabul_ok`ta eliyor,
`red_ok` ekseninde `allow` ile ayni kovaya dusuyor.

🔴 **SIRA ONEMLI:** once ALET onarilir, SONRA teshis. Alet duzelmeden yazilacak her kok-neden
hipotezi (muafiyet kolu, kimlik ekseni, kablolama) OLCULMEMIS tahmindir. Bu depoda yasak:
[[tahmin-degil-olcum-okan-uyarisi]] · [[fail-slow-fail-opendir]] ·
[[kapi-varlik-olcer-yokluk-olcmez]].

ℹ️ Elenmis bir hipotez (yazilmasin diye kayda geciyor): "prob isci muafiyet kolundan geciyor"
DEGIL — `_karar` payload'i kendi kuruyor (`:49-55`) ve icinde `agent_id` YOK, yani
`mimar-icra-kapisi.py:1049`'daki `kimlik(girdi)=="ISCI"` erken cikisi TETIKLENMEZ. Kimlik
ekseni PAYLOAD'dan turuyor, ortamdan degil.

## 3. ISTENEN DAVRANIS

1. `_karar()` uc jeton dondurur: `deny` · `allow` · **`OLCULEMEDI`**.
   `OLCULEMEDI` = bos stdout **veya** ayristirilamaz stdout **veya** `returncode != 0`.
   `PARSE-HATASI` bu jetona katilir (ayri kova tutmak istersen tut, ama `allow` OLAMAZ).
2. `_nobet_karar()` gerekce satirina **rc ve stderr'in ilk satirini** basar:
   `reddetmeli=<jeton>(rc=<n>) kabuletmeli=<jeton>(rc=<n>) stderr=<ilk satir, 120 kar. kirpik>`
3. Herhangi bir eksende `OLCULEMEDI` varsa kapi **NOBETTE=OLCULEMEDI** yazar ve
   `kapi-envanteri.py` rc **0 DONDURMEZ**. `0` yalnizca OLCULEN sifirdir.
4. `_cikis()` kolu (`:82-100`) ayni kurala tabidir: cikis kodu okunamiyorsa `OLCULEMEDI`.

## 4. KABUL (calistirilabilir; "bakildi iyi" DEGIL)

Mühendis `tools/kapi-envanteri-test.py` yazar (yoksa) ve su tek komut kapatir:

```
python3 /Users/okan/dev/pruvo/tools/kapi-envanteri-test.py
```

son satiri ve rc=0:

```
VAKA=<n> DUSEN=0 MUTANT=3/3 KONTROL=2/2
```

### 4.1 Vakalar (sentetik betiklerle, ana kapilara DOKUNMADAN)

| # | Fikstur (sahte kapi betigi) | Beklenen jeton |
|---|---|---|
| V1 | stdout'a gecerli `deny` JSON basar | `deny` |
| V2 | stdout'a gecerli `allow` JSON basar | `allow` |
| V3 | **hicbir sey basmaz**, rc=0 | `OLCULEMEDI` (bugun: `allow`) |
| V4 | stderr'e yazar, stdout bos, rc=1 | `OLCULEMEDI`, gerekcede stderr ilk satiri GORUNUR |
| V5 | bozuk JSON basar | `OLCULEMEDI` (ya da ayri `PARSE-HATASI` kovasi; `allow` OLAMAZ) |

### 4.2 Mutasyon bataryasi (3/3 KIRMIZI olacak)

* **M1** — `:64-65`'i eski haline dondur (`if not cikti: return "allow"`) → V3 DUSER.
* **M2** — `returncode` kontrolunu kaldir → V4 DUSER.
* **M3** — `OLCULEMEDI` varken `kapi-envanteri.py`'yi rc=0 dondurecek sekilde degistir →
  batarya KIRMIZI yakar (fail-open geri gelmis olur).

### 4.3 Kontrol mutantlari (2/2 YESIL kalacak — yanlis-pozitif nobetcisi)

* **K1** — Gercekten `allow` donen bir kapi (V2) `OLCULEMEDI` diye ISARETLENMEZ.
* **K2** — Bugun GECER durumda olan 5 kapi (`komut-stili-kapisi`, `urunler-guard-hook`,
  `urunler-guard`, `mukerrer-kontrol`, `mimar-commit-kapisi`) GECER kalir — onarim
  kapsami genisletmez ([[kapi-kapsam-genisletme-tuzagi]]).

## 5. ONARIM SONRASI — IKINCI TUR (ayni is emrinde)

Alet duzeldikten sonra `kapi-envanteri.py` YENIDEN kosulur ve **gercek** jeton kutuya yazilir:
* `reddetmeli=deny` cikarsa → K141 KAPANIR (kusur yalnizca aletteymis).
* `reddetmeli=allow` (gercek) ya da `OLCULEMEDI(rc=…)` cikarsa → **yeni ve OLCULMUS** bir
  kok-neden satiri yazilir; K141 acik kalir ama artik teshis TASIR.
Ikinci turun ciktisi rapora BIREBIR yapistirilir.

## 6. SINIRLAR

* Bu paket kapilarin KENDI mantigina DOKUNMAZ — yalniz PROB'u onarir.
* `CANON = "/Users/okan/dev/pruvo"` sabiti (`:41`) kapsam disidir; degistirme.
* Kaynak kod commit'i **worktree'de** yapilir (`mimar-kod-kilidi`). Is bitince worktree
  KALDIRILIR (13 Agu disk emri) ve kaldirildigi `git worktree list` ciktisiyla kanitlanir.
