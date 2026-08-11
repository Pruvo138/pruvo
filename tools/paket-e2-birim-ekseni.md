# SPEC — `tools/devam-sinif-kapisi.py` E2 ekseni: KELIME degil BOYUT

**Mimar:** KraL · **Dal:** `claude/jolly-lederberg-e2a0ee` · **Kabul:** calistirilabilir (asagida).

## 1. OLCULEN ARIZA (sinif, tekil vaka DEGIL)

Bugunku kural (satir 188-191):

```python
E2_KONU = re.compile(r"\b(iskonto|(?<!guvenlik )marj|...)\b")
E2_SAYI = re.compile(r"\d")
...
if E2_KONU.search(norm) and E2_SAYI.search(norm):
    bulgular.append(("E2 oran-marj", "oran-konusu+sayi"))
```

Yani hukum = **konu kelimesi + satirda HERHANGI BIR RAKAM**. Iki ayri kusur:

1. **Konu kelimesi anlami tasimiyor.** `marj` hem ticari (iskonto/kar) hem muhendislik
   (yerlesim payi, karakter butcesi) buyuklugudur. 11 Agu turunda `DEVAM.md`'ye yazilan
   CTA/WhatsApp **yerlesim payi** notu E2 sanildi ve iki satirda KIRMIZI yandi; yazar
   kapiyi gecmek icin notu **yeniden ADLANDIRDI** (`MARJ NOTU` -> `GENISLIK TOLERANSI
   NOTU`). Kapi sizintiyi degil KELIMEYI kovaladi.
2. **Muafiyet elle yazilmis tek kelime.** `(?<!guvenlik )marj` — ayni sinifin ONCEKI
   ornegi de tekil yamayla kapatilmis. Ucuncu ornek geldiginde ayni sey tekrarlanir
   -> `[[envanter-drift-parti-basina]]`, `[[tekil-yama-sinifi-kapatmaz]]`.

Ek olarak **`\d` = rakam** olculdu ki miktar degildir: `CTA-A1`, `serit-a2`, `364095f6`
gibi TANIMLAYICILARIN icindeki rakam da kapiyi tetikliyordu (gercek satir 106'nin
yanma nedeni budur).

Kapi `deploy.yml:406` + `deploy.yml:1204`'te **BLOKLAYICI** kosar (`build` -> `deploy`
-> `yayin` zinciri). Yanlis-pozitif = **tum ekibin yayini durur**.

## 2. TURETILEN KURAL — AYIRT EDICI SAYININ **BOYUTU**DUR

Uc parcali, fail-closed hiyerarsi:

| # | Kosul (satir duzeyi) | Hukum |
|---|---|---|
| 0 | Satirda **bagimsiz sayi jetonu** yok | YESIL (E2 aday degil) |
| 1 | **TICARI KONU** var (iskonto/komisyon/kar payi/alis-alim-maliyet-tedarik fiyati/kur farki/doviz kuru) | **KIRMIZI** — muafiyet YOK |
| 2 | **BELIRSIZ KONU** (`marj`) + satirda **PARA BOYUTU** (TL/TRY/USD/EUR/GBP/lira/kurus/dolar/euro/sterlin veya ₺ $ € £) | **KIRMIZI** — para her zaman ticaridir, muhendislik kaniti GECERSIZ |
| 3 | **BELIRSIZ KONU** + miktar bir **MUHENDISLIK BIRIMI** tasiyor (px/mm/ms/bayt/karakter/adet...) | YESIL — boyut KANITLANDI |
| 4 | **BELIRSIZ KONU** + miktar **BOYUTSUZ** (ciplak sayi, katsayi, `%`) | **KIRMIZI** — "olcemedim" YESIL DEGILDIR |

### 🔴 `%` KANIT DEGILDIR (bu spec'in en onemli olcumu)

Istekte `%` "ticari" tarafa onerilmisti. **Gercek yanlis-pozitif satirin kendisi
`~%5 (~7 px)` yaziyor** (`DEVAM.md:94`). `%` ticari sayilsaydi, bu isi baslatan satir
YINE yanardi. `%` **boyutsuzdur**: ne ticari kanit ne muhendislik kanitidir. Ticari
hukum ya **PARA BIRIMINDEN** ya **TICARI KONUDAN** gelir. (Boyutsuz miktar zaten
madde 4'te KIRMIZI kalir — yani `%` fail-closed tarafta durur, sadece px/mm gibi bir
boyut ayni satirda kanit sunarsa yesile doner.)

### Kume neden "kanonik", neden allow-list degil

`E2_BIRIM` bir **olcu birimi** kumesidir (uzunluk · sure · veri · frekans · kutle ·
metin/sayim). Uyeligi bir CUMLE KALIBI degil bir **BOYUT** belirler. Yeni bir birim
(`µs`, `dpi`) girebilir; yeni bir **kelime kalibi** (`yerlesim payi`, `denge marji`)
GIREMEZ — o satirlar birim yazarak yesillenir.

`E2_DONMUS_ONEKLER` = boyut ekseninden onceki donemden **TEK** kalinti
(`guvenlik marji`; `GUVENLIK_MARJI=400` bir KARAKTER butcesidir ve gercek defter
metninde ciplak sayiyla gecer). **Dondurulmustur**: kabul testi A2 iddiasi bu kumenin
BUYUMESINI kirmizi yakar.

## 3. UYGULANACAK DEGISIKLIK (birebir)

### 3.1 Modul basligi — E2 satiri (satir 69)

```
  E2 oran-marj        — TICARI oran/iskonto/komisyon/alis-maliyet fiyati + MIKTAR.
                        AYIRT EDICI KELIME DEGIL SAYININ BOYUTUDUR: "marj" gibi
                        BELIRSIZ konu ancak miktar bir MUHENDISLIK birimi
                        (px/mm/ms/bayt/karakter...) tasirsa YESIL; para birimi
                        HER ZAMAN ticaridir; boyutsuz miktar (ciplak sayi, %)
                        KIRMIZI kalir (fail-closed).
```

### 3.2 `E2_*` blogu (satir 185-191'in TAMAMI bununla degisir)

```python
# --- E2: ticari oran / marj — BIRIM (BOYUT) EKSENLI ------------------------
# 🔴 NEDEN BOYUT (olculdu 11 Agu 2026, DEVAM.md CTA blogu): kural "oran konusu +
# HERHANGI BIR RAKAM" idi. Bir MUHENDISLIK notu (CTA butonu ile WhatsApp hapi
# arasindaki YERLESIM payi) iki satirda KIRMIZI yandi; yazar kapiyi gecmek icin
# notu yeniden ADLANDIRDI. Kapi sizintiyi degil KELIMEYI kovaladi. Ayni sinifin
# onceki ornegi de tekil kelime yamasiyla ("guvenlik marji") kapatilmisti ->
# [[tekil-yama-sinifi-kapatmaz]] · [[envanter-drift-parti-basina]].
#
# AYIRT EDICI = SAYININ BOYUTU:
#   * TICARI KONU tek basina KIRMIZIDIR; boyut muafiyeti ONA ULASMAZ (bir ticari
#     oran, yaninda px yazarak aklanamaz).
#   * BELIRSIZ KONU ("marj") ancak MUHENDISLIK BOYUTU KANITLANIRSA yesildir.
#   * PARA BOYUTU satirda gorunurse muhendislik kaniti GECERSIZDIR (ustunluk).
#   * Boyutsuz miktar KIRMIZI kalir — "olcemedim" YESIL DEGILDIR.
# ⚠️ `%` KANIT DEGILDIR, BOYUTSUZDUR: bu isi baslatan gercek satirin kendisi
#    "~%5 (~7 px)" yaziyordu; `%` ticari sayilsaydi o satir YINE yanardi.
# ⚠️ MIKTAR = BAGIMSIZ SAYI JETONU, "herhangi bir rakam" DEGIL. Olculdu:
#    `CTA-A1` / `serit-a2` / `364095f6` icindeki rakam miktar degildir.

# 🧊 DONMUS KELIME MUAFIYETI — BUYUTULEMEZ (kabul testi A2 olcer). Boyut
# ekseninden onceki donemin TEK kalintisi: "guvenlik marji" bir KARAKTER butcesi
# sabitidir (tools/ege-bilgi-tavan-test.py GUVENLIK_MARJI=400) ve gercek defter
# metninde CIPLAK sayiyla gecer. YENI ornek buraya EKLENMEZ; birim yazilir.
E2_DONMUS_ONEKLER = ("guvenlik",)
E2_DONMUS = re.compile(r"\b(?:%s) marj\w*\b" % "|".join(E2_DONMUS_ONEKLER))

# TICARI KONU: tek basina yeterli (belirsizlik YOK).
E2_TICARI_KONU = re.compile(
    r"\b(iskonto|kar payi|karpayi|komisyon|alis fiyati|alim fiyati|"
    r"maliyet fiyati|tedarik fiyati|kur farki|doviz kuru)\b")
# BELIRSIZ KONU: ticari de olabilir muhendislik de — boyut karar verir.
E2_BELIRSIZ_KONU = re.compile(r"\bmarj\w*\b")

# MIKTAR / BOYUT olcumleri HAM metinde yapilir: normalize() `1,35`i `1 35`e boler,
# `%` ve `₺` gibi isaretleri SILER ve birim bitisikligini (`7 px`) korur ama para
# sembolunu kaybederdi -> [[olcum-birimi-bayt-utf16]] sinifi bir birim hatasi.
E2_SAYI = re.compile(r"(?<![0-9A-Za-z])\d[\d.,]*(?![0-9A-Za-z])")
E2_PARA = re.compile(
    r"(?:(?<![0-9A-Za-z])\d[\d.,]*\s*(?:tl|try|usd|eur|gbp|lira|kurus|"
    r"dolar|euro|sterlin)\b)|(?:[₺$€£]\s*\d)|(?:\d\s*[₺$€£])", re.I)
# KANONIK BIRIM KUMESI (uzunluk · sure · veri · frekans · kutle · metin/sayim).
# Uyelik olcutu BOYUTTUR, cumle kalibi DEGIL.
E2_BIRIM = re.compile(
    r"(?<![0-9A-Za-z])\d[\d.,]*\s*"
    r"(?:px|piksel|pt|rem|em|ch|vw|vh|dp|"
    r"mm|cm|km|um|inc|mikron|m|"
    r"ms|sn|saniye|dakika|dk|saat|hz|khz|mhz|fps|dpi|"
    r"bayt|byte|bit|kb|mb|gb|tb|"
    r"karakter|hane|satir|adet|derece|"
    r"gr|gram|kg|ml)\b", re.I)


def e2_bulgusu(ham, norm):
    """E2 hukmu -> desen etiketi ya da None (bkz. ustteki blok).

    FAIL-CLOSED: belirsiz konuda MUHENDISLIK BOYUTU KANITLANMADIKCA KIRMIZI."""
    if not E2_SAYI.search(ham):
        return None
    if E2_TICARI_KONU.search(norm):
        return "ticari-konu+miktar"
    if not E2_BELIRSIZ_KONU.search(E2_DONMUS.sub(" ", norm)):
        return None
    if E2_PARA.search(ham):
        return "belirsiz-konu+para-boyutu"
    if E2_BIRIM.search(ham):
        return None
    return "belirsiz-konu+boyutsuz-miktar"
```

### 3.3 `satir_eksenleri()` icindeki E2 blogu (satir 314-316)

```python
    # E2 — ticari oran / marj (BOYUT ekseni)
    _e2 = e2_bulgusu(ham, norm)
    if _e2:
        bulgular.append(("E2 oran-marj", _e2))
```

### 3.4 Fikstur — `_KIRMIZI`'ya EKLE (mevcutlar KALIR)

```python
    ("- Aracilik marji islem basina 4500 TL; 12 adet uzerinden hesaplandi.",
     "E2 oran-marj"),                      # para boyutu > muhendislik kaniti
    ("- Anlasilan marj %18 seviyesinde tutuldu.", "E2 oran-marj"),   # % BOYUTSUZ
    ("- MARJ_ORANI=0.22 sabiti panelden okunuyor.", "E2 oran-marj"), # kod adi aklamaz
    ("- Iskonto 7 px kadar kucuk gorunse de uygulandi.", "E2 oran-marj"),
    # ^ TICARI konu, yanindaki muhendislik birimiyle AKLANAMAZ.
```

### 3.5 Fikstur — `_YESIL`'e EKLE (mevcutlar KALIR)

```python
    # --- 11 Agu: E2 BOYUT ekseni. Bu satirlar ESKI kuralda KIRMIZI yaniyordu.
    "- Masaustunde elde kalan marj ~%5 (~7 px); yerlesim toleransi.",
    "- CTA marji 12 px daraldi; esik 250 ms.",
    "- Ege tavan payi 400 karakter marjinda kaldi.",
    "- Genislik marji CTA-A1 ekseninde izlenecek.",   # rakam VAR, MIKTAR YOK
```

### 3.6 `kendini_test()` — B blogunun HEMEN ARDINA iki iddia

```python
    # ---- A2) DONMUS KELIME MUAFIYETI BUYUYEMEZ ([[envanter-drift-parti-basina]])
    kontrol += 1
    if E2_DONMUS_ONEKLER != ("guvenlik",):
        hatalar.append("A2 DONMUS MUAFIYET DEGISTI -> %r. Yeni muhendislik marji "
                       "BOYUT eksenine (E2_BIRIM) girer, kelime listesine DEGIL."
                       % (E2_DONMUS_ONEKLER,))

    # ---- A3) IKIZ VAKA: iki satir arasindaki TEK fark BIRIMDIR. Hukum kelimeden
    #      degil BOYUTTAN geliyorsa bu uclu ayrisir ([[kabul-araligi-karsilastirma-araligi]]).
    for satir, kirmizi_beklenen in (
            ("- Elde kalan marj 7 px olarak olculdu.", False),
            ("- Elde kalan marj 7 TL olarak olculdu.", True),
            ("- Elde kalan marj 7 olarak olculdu.", True)):
        kontrol += 1
        kirmizi = "E2 oran-marj" in _eksenler(satir)
        if kirmizi != kirmizi_beklenen:
            hatalar.append("A3 IKIZ VAKA: %r -> %s (beklenen %s)"
                           % (satir, "KIRMIZI" if kirmizi else "YESIL",
                              "KIRMIZI" if kirmizi_beklenen else "YESIL"))
```

### 3.7 `_MUTANTLAR` — M1'i TAZELE (capasi olecek) + alti YENI mutant

```python
    ("M1 E2 ticari konuyu oldur", "E2_TICARI_KONU = re.compile(",
     'E2_TICARI_KONU = re.compile(r"(?!x)x")  #', True),
    ...
    ("M17 E2 boyut ekseni OLDUR", "E2_BIRIM = re.compile(",
     'E2_BIRIM = re.compile(r"(?!x)x")  #', True),
    ("M18 E2 boyut ekseni SINIRSIZ GENISLET", "E2_BIRIM = re.compile(",
     'E2_BIRIM = re.compile(r"")  #', True),
    ("M19 E2 para ustunlugunu OLDUR", "E2_PARA = re.compile(",
     'E2_PARA = re.compile(r"(?!x)x")  #', True),
    ("M20 E2 miktarini `herhangi bir rakam`a geri al", "E2_SAYI = re.compile(",
     'E2_SAYI = re.compile(r"\\d")  #', True),
    ("M21 belirsiz konuyu TICARI say",
     '    if not E2_BELIRSIZ_KONU.search(E2_DONMUS.sub(" ", norm)):\n        return None',
     '    if E2_BELIRSIZ_KONU.search(norm):\n        return "ticari-konu+miktar"', True),
    ("M22 DONMUS muafiyeti BUYUT", 'E2_DONMUS_ONEKLER = ("guvenlik",)',
     'E2_DONMUS_ONEKLER = ("guvenlik", "yerlesim", "genislik")', True),
```

Beklenen olum sebepleri (her biri **ayri** bir fikstur yuzunden olmeli):
M17 -> yeni YESIL px satirlari yanar · M18 -> `1,35 katsayi` / `MARJ_ORANI=0.22`
kacar · M19 -> `4500 TL ... 12 adet` satiri `adet` sayesinde kacar ·
M20 -> `CTA-A1` satiri yanar · M21 -> tum px satirlari yanar · M22 -> A2 iddiasi.

## 4. KABUL (calistirilabilir — hepsi ZORUNLU)

```
python3 tools/devam-sinif-kapisi.py                 -> rc 0 (gercek defterler TEMIZ)
python3 tools/devam-sinif-kapisi.py --kendini-test  -> rc 0, 0 hata
python3 tools/devam-sinif-kapisi.py --mutasyon      -> rc 0, TUM oldurucu KIRMIZI,
                                                       M11/M12 (ilgisiz) YESIL,
                                                       canli dosya sha256 TAM
python3 tools/ci-kapsam-test.py                     -> rc 0 (kapi envanteri bozulmadi)
```

**GEVSETME YASAK:** bir fikstur kirmizi verirse **fiksturu degil KURALI** duzelt.
`_KIRMIZI`/`_YESIL`'den satir SILINMEZ. `DEVAM.md`/`DEVAM-ARSIV.md` metnine
DOKUNULMAZ. Fiksturlerde gercek tedarikci adi/uyelik/oran YOKTUR (uydurma deger).
