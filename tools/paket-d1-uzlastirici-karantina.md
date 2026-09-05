# PAKET — D1 uzlastirici SILME kolunun karantinaya alinmasi (KraL spec'i, MUHENDIS icrasi)

> **KAT: MUHENDIS (Claude Opus).** Bu bir SESSIZ-HATA sinifidir (olcum + veri SILME) —
> `skill: isci-devri` merdiveninde emekli motor'e VERILMEZ. Kabul kapisi calistirilabilir testtir.
> Spec sahibi KraL. Urun VERISI (`urunler.json`) bu iste DEGISMEZ.

## 1. OLCULEN ZARAR (iddia degil, 11 Agu 2026 kosumu)

Kosum **31532464176** — workflow "D1 uzlastirici (katalog sapmasi)", head `c8b0451e`.
Dusen adimlar: "Teyit — onarimdan sonra sapma SIFIR mi" + "ONARILAMADI: sapma KAPANMADI".

Logdan alinti:

```
hash UYUSMAZ: 0 | D1'de EKSIK: 0 | D1'de FAZLA: 37
silinen: 37
GERI-OKUMA DOGRULANDI: 37 satirin ... silinmesi D1'de teyit edildi
D1 urun sayisi: 25827
icerik ekseni (urun_hash): 25864 D1 satiri
```

**Ne oldu:** uzlastirici, calisma agacini uzak main ucuna (`c8b0451e`, 25827 urun) tazeledi,
D1'de 25864 satir gordu, aradaki **37 satiri "FAZLA" sayip SILDI** ve silmeyi geri-okumayla
dogruladi. Teyit adiminda sapma yine acikti (D1 tekrar ilerlemisti) → kosum KIRMIZI.

**Silinen 37 satir COP DEGILDI:** esZAMANLI bir urun partisinin D1'e yazdigi MESRU
satirlardi; o partinin git push'u henuz uca inmemisti. Yani uzlastirici, katalogun
**ilerisini** "sapma" sanip geri aldi. Bu tam olarak `[[d1-bayat-yazici-silme]]` sinifidir,
bu kez SILEN taraf emniyet aginin KENDISI.

**Neden mevcut kapi tutmadi:** `d1-sync.py --bayatlik` kapisi agacin **git'e** gore bayat
olmasini olcer. Buradaki hal farkli: agac git ucundaydi ama **D1 git'ten ILERIDEYDI**.
Bu yon mevcut kapinin ekseninde YOK → kapi dogru calisti, YANLIS SORUYU sordu.

**Yeni sinif degil:** `31502177931` kosumunda da `D1'de FAZLA: 41` gorulmus, uc tazelenince
`FAZLA: 0` olmustu. Yani "FAZLA" olcumu duzenli olarak GECICI bir yaris penceresini olcuyor.

## 2. ASIMETRI — iki yonun riski AYNI DEGIL

| Yon | Anlami | Yanlis hukmun bedeli |
|---|---|---|
| `EKSIK` (D1'de yok, agacta var) | senkron kacmis | **Ekleme** — yanlissa fazladan satir, Ege gosterir, zarar KUCUK |
| `FAZLA` (D1'de var, agacta yok) | ya gercek oksuz ya **ucustaki parti** | **Silme** — yanlissa canli katalog satiri gider, Ege GOREMEZ = satis kaybi |

Emniyet agi bu iki yonu AYNI cesaretle isliyor. Silme kolu, ekleme koluyla ayni esikte
olmamalidir.

## 3. ISTENEN DAVRANIS — KARANTINA (silmeyi kaldirmak DEGIL)

🔴 Silme kolunu tamamen kapatmak COZUM DEGIL: gercek oksuz satirlar birikirse D1 ile katalog
kalici ayrisir. Istenen, silmeyi **iki gozleme** yaymaktir:

1. **Ilk gozlem — SILME YOK.** Bir id ilk kez `FAZLA` gorulduğunde SILINMEZ; kimligi
   (id + gozlem zamani + o anki `origin/main` SHA'si) bir **karantina damgasina** yazilir
   (artifact — depoya PUSH ETME; gerekce d1-uzlastirici.yml'deki damga blogunda yazili:
   damga mekanizmasi olcmesi gereken hastaligi URETEMEZ).
2. **Ikinci gozlem — SILME.** Bir id, **farkli bir `origin/main` SHA'sinda** ikinci kez
   `FAZLA` gorulurse artik ucustaki parti aciklamasi CURUR (o parti inmis olurdu) → SILINIR.
3. **Karantinadaki id, agacta belirirse** karantinadan DUSER (silinmez, kayit temizlenir).
4. Karantina damgasi okunamiyorsa (artifact yok/bozuk/suresi dolmus) hukum **fail-closed**:
   **SILME YAPILMAZ**, adim `OLCULEMEDI` basar. "Okuyamadim → sil" yolu ACILMAZ.

`EKSIK` ve `hash UYUSMAZ` kollari **DEGISMEZ** — onlar ekleme/guncelleme, karantinaya
girmez.

## 4. HUKUM BIRIMI — "FAZLA var" ile "onarilamadi" ayrilir

Bugun `FAZLA:37` → sil → teyit hala sapmali → **ONARILAMADI (KIRMIZI)**. Karantina sonrasi
ilk gozlem "onarilamadi" DEGILDIR; ayri bir hukumdur:

- `KARANTINA_ACILDI=<n>` → kosum **KIRMIZI DEGIL** (gorunurluk adimi bilgi basar; sapma
  `d1-sapma-damgasi` kanalindan zaten alarm yakar).
- `KARANTINA_SILINDI=<n>` → ikinci gozlemde silindi, teyit gecti → yesil.
- Teyit gecmezse **ONARILAMADI** hukmu AYNEN kalir (mevcut adim `steps.teyit.outcome !=
  'success'` kosuluyla dogru calisiyor, DOKUNMA).

## 5. YASAK (spec sinirlari)

- `urunler.json` / `.urun-kaynaklari.json` icerigine DOKUNMA.
- Adim SILEREK ya da `continue-on-error` ekleyerek yesile boyama YOK.
- `d1-uzlastirici.yml`'deki uc gorunurluk adiminin AYRILIGINI bozma (`cron-nabiz-kapisi.py`
  `::kadans_kablosu` ekseni bunu olcer, yigarsan KIRMIZI yanar).
- `concurrency` grubunu (`d1-uzlastirici`) ve `cancel-in-progress: false` degerini degistirme.
- Bayatlik kapisini (`d1-sync.py --bayatlik`) GEVSETME — bu is onun YERINE gecmez, YANINA
  ikinci bir eksen koyar.
- force push / gecmis yeniden yazma YOK.

## 6. KABUL — calistirilabilir test (yesil cumle DEGIL)

Mühendis repoya **`tools/uzlastirici-karantina-test.py`** ve **`tools/uzlastirici-karantina-
mutasyon.py`** koyar; ikisi de rc=0 vermeden is KAPANMAZ.

Kabul testinin ZORUNLU vakalari (fikstur GERCEK cikti seklini taklit etsin →
`[[nobetci-fikstur-sekli]]`):

| # | Girdi | Beklenen |
|---|---|---|
| K1 | id ilk kez FAZLA | SILINMEZ · karantinaya yazilir · rc=0 |
| K2 | ayni id, **ayni** origin/main SHA'sinda ikinci gozlem | SILINMEZ (SHA ilerlemedi) |
| K3 | ayni id, **farkli** origin/main SHA'sinda ikinci gozlem | SILINIR |
| K4 | karantinadaki id agacta belirdi | SILINMEZ · karantinadan DUSER |
| K5 | karantina damgasi YOK/bozuk | SILME YOK · `OLCULEMEDI` · fail-closed |
| K6 | `EKSIK` satirlar | karantinadan ETKILENMEZ, aynen eklenir |
| K7 | 11 Agu vakasinin birebir yeniden oynatimi (37 id, tek gozlem) | **silinen: 0** |

Mutasyon bataryasi (fail-closed alarmlarin sokulmesi dahil) su mutantlarin HEPSINDE KIRMIZI
yakmali; en az **2 kontrol mutanti YESIL** kalmali (batarya tautoloji olmasin →
`[[mutasyon-kaniti-yeniden-uretilebilir.md]]`):
- karantina kosulunu `>=1` yerine `>=0` yapmak (ilk gozlemde silme),
- SHA karsilastirmasini kaldirmak (K2'yi silmeye cevirir),
- damga okunamadiginda `OLCULEMEDI` yerine silmeye devam etmek (K5 fail-open),
- karantinadan dusme kolunu (K4) sokmek.

Ek kapi: `python3 tools/cron-nabiz-kapisi.py --kendini-test` rc=0 (kadans kablosu bozulmadi).

## 7. RAPOR

Dalda, mimar iletisim protokolundeki kanonik muhendis raporu adiyla (bkz. CLAUDE.md
"ILETISIM PROTOKOLU") bir rapor birakilir; son satirlar:

```
KARANTINA_TESTI=<rc>:<vaka sayisi>
KARANTINA_MUTASYON=<MUTANT=n/n>:<KONTROL=YESIL|KIRMIZI>
NABIZ_KAPISI=<rc>
DEGISEN_DOSYALAR=<liste>
```
