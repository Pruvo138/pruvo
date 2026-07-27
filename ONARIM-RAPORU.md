# ONARIM RAPORU — `ege-bilgi.md` tavan işi

Dal: `worktree-agent-a5a4c887dfb6f2dc6` · 27 Tem · MÜHENDİS (Opus)
Değişen dosya: **2** (`ege-bilgi.md`, `tools/ege-malzeme.py`) · `deploy.yml` **0 hunk**

---

## 0. 🔴 ÖNCE BUNU OKU — İŞİN PREMİSİ ÖLÇÜMLE ÇÜRÜDÜ

Spec şunu diyordu: *"canlı dosya 6334 karakter → son ~334 karakter (l.47-49) Ege'nin
promptuna HİÇ ulaşmıyor."*

**Bu yanlış. Hiçbir şey kesilmiyor ve hiç kesilmemiş.**

Canlı ucu okudum (salt-okunur, teşhis için — kapı hermetik kaldı):

| | değer |
|---|---|
| `https://pruvo3d.com/ege-bilgi.md` sha256 | `1008af8f…b261f1` |
| repo `ege-bilgi.md` sha256 | `1008af8f…b261f1` — **BAYT ÖZDEŞ** |
| **bayt** (UTF-8) | **6334** |
| Python `len()` (kod noktası) | **5761** |
| **UTF-16 kod birimi** (JS `.slice` bunu sayar) | **5761** |
| TAVAN | 6000 |
| **kesilen birim** | **0** |
| kalan boşluk | 239 |

**HocA'nın "6334 karakter"i bir BAYT sayısıdır.** Türkçe harfler (ş/ğ/ı/ç/ö/ü/İ) UTF-8'de
2 bayt tutar; 6334 − 5761 = **573 bayt** tam olarak bu farktır. `l.47-49` bloğu Ege'ye
**ulaşıyor** ve hiç ulaşmadığı bir gün olmamış: dosyanın tüm commit tarihçesinde ölçülen
en yüksek değer **5863** birimdir (`f9023fec`), yani tavanın 137 birim altı.

### Spec'in "en kritik nokta" dediği emoji ekseni bu dosyada YOK
Spec: *"emoji (⚠️ 🔴 ✅ …) surrogate pair = 2 birim → Python `len()` AZ sayar ve sahte
YEŞİL yakar."* Ölçtüm:

- `ege-bilgi.md`'de **BMP dışı (astral) karakter sayısı = 0** → Python `len()` ile UTF-16
  farkı **0**. Emoji bu dosyada hiç yok (⚠️/🔴 kapı `.py` dosyalarında ve CLAUDE.md'de).
- Ayrıca spec'in emoji listesi teknik olarak da karışık: **✅ (U+2705) ve ⚠️'nin iki kod
  noktası da BMP'dedir** — surrogate çifti değildirler, Python `len()` onları eksik
  saymaz. Gerçekten astral olan **🔴 (U+1F534)** gibi karakterlerdir.
- Yani hata sınıfı **ters yöndeydi**: sahte-YEŞİL (Python len) değil, **sahte-KIRMIZI**
  (bayt sayımı) gerçekleşti.

**Ve bu tam olarak nöbetçinin 21 Tem'de yazıp uyardığı sınıf** —
`tools/ege-bilgi-tavan-test.py:19`:
> `* bayt sayan bir kapi (wc -c) BUGUN 6349 > 6000 gorup SAHTE KIRMIZI yakardi.`

---

## 1. 🔴 NÖBETÇİ ZATEN VAR — KARAR 3 UYGULANMADI (bilinçli sapma, gerekçeli)

Spec kararı 3: *"kontrolü var olan `tools/ege-kabiliyet-kapisi.py` içine ekle."*
**Uygulamadım.** Sebep: istenen nöbetçi **zaten mevcut, CI'da bloklayıcı ve daha güçlü.**

| | durum |
|---|---|
| `tools/ege-bilgi-tavan-test.py` | VAR — UTF-16 ölçer, `TAVAN=6000`, `GUVENLIK_MARJI=400` |
| `deploy.yml:127-128` | `python3 tools/ege-bilgi-tavan-test.py` (bloklayıcı) |
| `deploy.yml:144-145` | `--ic-nobetci` (**30 fikstür**) |
| `tools/ege-bilgi-tavan-mutasyon.py` | ayrı kırmızı-mutasyon harness'ı |
| `tools/kapi-envanteri.py` | `7/7 kapi VAR+BAGLI+NOBETTE tam` |

Kararı uygulamak **spec'in kendi kuralını çiğnerdi**: *"TAVAN sabiti … Başka hiçbir yere
sayı GÖMME."* — `ege-kabiliyet-kapisi.py`'ye ikinci bir 6000 koymak, commit
**`8c6c99b0` "Ege-bilgi 6000 tavan kapisi TEKILLESTIRILDI"** ile bilinçli olarak
kaldırılmış olan kopyayı geri getirirdi. Kararın gerekçesi ("`deploy.yml`'e 0 hunk")
zaten karşılanıyor: mevcut kapı **deploy.yml'de kayıtlı** — bu daldan o dosyaya
**0 hunk** girdi.

Spec'in K3/K4 talebini yeni kod yazarak değil, **var olan nöbetçiyi mutasyonla sınayarak**
kapattım (aşağıda 3/3 ve 2/2).

---

## 2. NE YAPTIM (gerçek, ölçülmüş iş)

Premis çürüdü ama **gerçek bir bulgu kaldı**: pay **239 < `GUVENLIK_MARJI` 400** →
nöbetçi **21 Tem'den beri** `DAR PAY` uyarısı basıyordu (`YEŞİL (UYARILI)`).
Karar 1 ("tavan yükseltilmez, dosya küçültülür") + karar 5 ("şişkinlik üretilen bloktaysa
**üreticiyi** düzelt") doğrultusunda:

**Şişkinliğin yeri ölçüldü:** `FILAMENT-REF` bloğu dosyanın **%44.5**'i (2562/5761 birim);
içinde `standart sipariş akışında YOK, WhatsApp özel talebiyle değerlendirilir — üretim
kararıdır, koşulu netleştir` kuyruğu **3 kez** tekrar ediyordu (~122 birim ×3).

**Yapılan:** `tools/ege-malzeme.py` (ÜRETİCİ) düzeltildi → ortak kuyruk **grup başlığına
hoistlandı**, blok `python3 tools/ege-malzeme.py` ile **yeniden üretildi**.
Bloğa **elle dokunulmadı** (karar 5). **Yeniden sıralama yapılmadı** (karar 6).

### Kaldırılan/değişen HER satır — birebir alıntı (mimar okuyup yargılasın)

**ÇIKAN 4 satır:**
```
Mühendislik malzemeleri (standart ailenin dışında, üretim kararı gerektirir):
- **ABS** (Isıya dayanıklı) — ısı ~95-100°C — standart sipariş akışında YOK, WhatsApp özel talebiyle değerlendirilir — üretim kararıdır, koşulu netleştir + [DEVRET]
- **Karbon katkılı (PETG-CF/PA-CF)** (En yüksek mukavemet) — ısı taşıyıcıya göre — standart sipariş akışında YOK, WhatsApp özel talebiyle değerlendirilir — üretim kararıdır, koşulu netleştir + [DEVRET]
- **Daha yüksek ısı / mukavemet:** Naylon (PA) ve elyaf katkılı türler tedarik edilebilir — üretim kararıdır, koşulu netleştir + [DEVRET]
```
**GİREN 4 satır:**
```
Mühendislik malzemeleri — standart ailenin dışında; hepsi standart sipariş akışında YOK, WhatsApp özel talebiyle değerlendirilir, üretim kararıdır, koşulu netleştir:
- **ABS** (Isıya dayanıklı) — ısı ~95-100°C — [DEVRET]
- **Karbon katkılı (PETG-CF/PA-CF)** (En yüksek mukavemet) — ısı taşıyıcıya göre — [DEVRET]
- **Daha yüksek ısı / mukavemet:** Naylon (PA) ve elyaf katkılı türler tedarik edilebilir — [DEVRET]
```
`ege-bilgi.md`'de **başka hiçbir satıra dokunulmadı** (`git diff` tek hunk, 4 satır).

**"hepsi" kelimesi kasıtlı:** kuyruk kalemlerden kalkınca kapsam örtük bırakılmadı,
kuralın aşağıdaki HER kaleme uygulandığı açıkça yazıldı. **`+ [DEVRET]` her kalemde
BIRAKILDI** (başlığa taşınmadı) — jeton sayısı 7'de sabit kalsın ve devret refleksi
kalem düzeyinde görünür kalsın diye.

### DOKUNMADIĞIM, bilerek bıraktığım şişkinlik
`l.10` (464 birim, dosyanın en uzun satırı) `l.36`'daki yasak listesini (NBR, FKM/Viton,
EPDM, silikon, metal, cam) **tekrar ediyor** — ~30 birim kazanç mümkündü. **Almadım:**
`l.10` "KRİTİK … BAŞTA" bölümünde duruyor ve dosyanın tüm tasarım mantığı
(`l.3: "kritik olan BAŞTA"`) kesilme anında kritik yasakların hayatta kalması üzerine
kurulu. Üstteki kopyayı silip ~3600 birim aşağıdaki kopyaya güvenmek bu korumayı
**tersine çevirirdi**. Aynı sebeple `l.36`'daki *"sunulması yakışık almaz, yalan söz
olur"* gerekçesi de durdu: tekrar değil, modele **sebep** veren bir cümledir.

---

## 3. KABUL KRİTERLERİ — HEPSİ SAYIYLA (**29/29 kontrol geçti**)

### K1 — UTF-16 ölçümü (önce/sonra)
| | bayt | Python `len()` | **UTF-16** | fark | astral | kesilen | **kalan boşluk** |
|---|---|---|---|---|---|---|---|
| ÖNCE | 6334 | 5761 | **5761** | 0 | 0 | **0** | 239 |
| SONRA | 6145 | 5592 | **5592** | 0 | 0 | **0** | **408** |

Kazanç **169 birim**. Boşluk **239 → 408**: spec'in ≥200 barajını **2×** aşıyor ve
reponun kendi `GUVENLIK_MARJI=400` eşiğini de geçiyor → nöbetçi artık **tam sessiz yeşil**
(`DAR PAY` uyarısı kalktı). Python `len()` ile UTF-16 **yan yana yazıldı; fark 0** çünkü
astral karakter yok. NUL bayt: **0** (bayt sayımıyla ölçüldü, grep'e güvenilmedi).

### K2 — JETON KORUMA: **0 KAYIP**
9 eksende deterministik jeton envanteri (önce: **165 tekil / 249 geçiş**):

| EKSEN | önce tekil | sonra tekil | **KAYIP** |
|---|---|---|---|
| SAYI/PARA/SÜRE/ÖLÇÜ | 17 | 17 | **0** |
| MALZEME ADI | 30 | 30 | **0** |
| **[DEVRET]** | 1 (×**7**) | 1 (×**7**) | **0** |
| YASAK/OLUMSUZ EMİR | 23 | 23 | **0** |
| EMİR/REFLEKS FİİLİ | 21 | 21 | **0** |
| KATEGORİ | 14 | 14 | **0** |
| KANAL/ÖDEME/TESLİM | 26 | 26 | **0** |
| KİMLİK/İLETİŞİM | 9 | 9 | **0** |
| KOŞUL/KULLANIM | 24 | 24 | **0** |

Yalnız **tekrar sayıları** düştü (jeton DURUYOR): `YOK` 3→2, `değerlendirilir` 2→1,
`netleştir` 4→2, `WhatsApp` 4→3. **`[DEVRET]` ×7 → ×7, birebir korundu.**
⚠️ Kelime testi anlamı onaylamaz — bu yüzden §2'de kaldırılan her satır birebir alıntılandı.

### K3 — Nöbetçi kırmızı-mutasyon **3/3**
- **(a)** tavanı aşan dosya (6092 birim) → **KIRMIZI, exit 1**; mesajda `son 92 karakter`
  (doğru kesilen sayı) **ve** kesilen kuyruk satırı (`KUYRUK-NOBET-ISARETI…`) görünüyor.
- **(b)** TAVAN−150 (5850 birim) → `DAR PAY` + `YEŞİL (UYARILI)`, **exit 0**.
- **(c)** budanmış gerçek dosya → **exit 0, `SONUC: YESIL ✅`, hiç uyarı yok.**

> Not: spec "+400 birim ekle" diyordu; budama sonrası 5592+400 = 5992 **hâlâ tavanın
> altında** kalıyor. Sınıfı korumak için fikstür tavanı gerçekten aşacak şekilde (+500)
> kuruldu.

### K4 — 🔴 UTF-16 KANIT FİKSTÜRÜ **2/2**
Sentetik dosya: 200 adet **🔴 (U+1F534, astral)** → Python `len()` = **5900 (tavanın
ALTINDA)**, UTF-16 = **6100 (tavanın ÜSTÜNDE)**.

| | sonuç |
|---|---|
| GERÇEK kapı (UTF-16 sayar) | **KIRMIZI (exit 1)** ✅ |
| MUTANT (`return len(metin)`) | **YEŞİL (exit 0)** ✅ → fikstür hatayı gerçekten yakalıyor |
| MUTANT, gerçek (emojisiz) dosyada | YEŞİL → fikstür **ayırt edici**, "her yerde kırmızı" değil |

Mutasyon deseni benzersizliği de ölçüldü (adet=1). Ayrıca reponun kendi
`ege-bilgi-tavan-mutasyon.py` harness'ı koştu: **her mutant öldürüldü** (B2 = tam bu
`len(str)` mutantı).

### K5 — Kabiliyet kapısı
`ege-kabiliyet-kapisi.py` bayraksız → **exit 0**, `Bulgu YOK.`
`--ic-nobetci` → **exit 0, 73/73 fikstür** (önce de 73 — **düşmedi**).
Budama sırasında kapının tuzak fiilleri (`hallederiz`/`yapabiliriz`/`üretiriz` …)
**hiç kullanılmadı**; yeni başlık cümlesi PARA jetonu da taşımıyor.

### K6 — DRIFT denetimi (yargı bende, betik hüküm vermez)
`drift-sonda.py` koşturuldu. **YARGIM: budama Ege ↔ site arasında YENİ çelişki AÇMADI.**
Gerekçe: (1) hiçbir malzeme adı/sıcaklık/kural jetonu kaybolmadı (K2, 0 kayıp);
(2) site iddiaları ile Ege metni **aynı** `tools/filamentler.json`'dan üretiliyor ve o
dosyaya dokunulmadı; (3) `malzeme-dayanak-test.py` **175 gövdeyi** (site sayfaları +
JSON-LD + `ege-bilgi.md`) taradı → `dayanaksiz malzeme 0 / 175 govde, kara liste ihlali
yok, drift yok`.
⚠️ **Bildirilen sınır:** `drift-sonda.py` `ege-bilgi.md`'yi **canlı URL'den** çeker
(`https://pruvo3d.com/ege-bilgi.md`), yerel daldan değil — yani sondanın gördüğü metin
**merge öncesi (main) sürümüdür**. Merge'den sonra bir kez daha koşturulmalı.

### K7 — `FILAMENT-REF` bloğu
| | sha256 | u16 |
|---|---|---|
| ÖNCE | `625111fc42ca770c2b33ac776343ef1ccb605a609dad325a92e91e21e2b8d7ff` | 2561 |
| SONRA | `a92a2dd6ac41fd445dc142d5e5cd150e0860d5b97367ebcb3bc6d645be7ca208` | 2392 |

Blok **bilerek değişti** — spec'in izin verdiği yolla: **`tools/ege-malzeme.py` ile
YENİDEN ÜRETİLDİ**, elle düzenlenmedi. Kanıt: dosyadaki blok üreticinin bellekteki
çıktısıyla **BİREBİR** (drift nöbetinin kendi karşılaştırması) + üretici **idempotent**
(2. koşum: `zaten guncel (degisiklik yok)`).

### K8 — CI kapıları
| kapı | sonuç |
|---|---|
| `.github/workflows/deploy.yml` | **0 hunk** (`git diff --stat` boş) |
| `tools/ci-kapsam-test.py` | **exit 0** — *her kabul testi ya koşuluyor ya gerekçeli muaf* |
| `tools/kapi-envanteri.py` | **exit 0** — *7/7 kapı VAR+BAĞLI+NÖBETTE tam* |
| `tools/malzeme-dayanak-test.py` (DRIFT) | **exit 0** — *0/175, kara liste ihlali yok, drift yok* |
| `tools/ege-bilgi-tavan-test.py --ic-nobetci` | **exit 0** — **30 fikstür**, 0 başarısız |
| `tools/ege-bilgi-tavan-mutasyon.py` | **exit 0** — her mutant yakalandı |

### K9 — Determinizm
Nöbetçi **5 koşum → 5/5 aynı çıkış kodu + 5/5 aynı rapor metni** (yalnız `Kosum suresi`
satırı ayıklandı). Kapı **hermetiktir**: ağ/canlı uca **bağlanmaz**, fikstürler
`tempfile`'da üretilir. (Canlı ölçüm §0'da yalnız **teşhis** amaçlı, tek seferlik,
salt-okunur yapıldı; kapıya girmedi.)

---

## 4. BEYAN EDİLEN KÖR NOKTALAR
1. **Bu rapor prose'u ONAYLAMAZ.** `ege-kabiliyet-kapisi.py` kendi
   `ne_olculmedi()` bölümünde yazıyor: 30 bypass varyantının **25'i kaçtı**; anlamı
   tersine çeviren 25 mutasyonun **22'si** kelime testinden yeşil geçti. §2'deki birebir
   alıntılar tam bu yüzden var — **insan okuması hâlâ şart.**
2. **Semantik risk (en dürüst maddem):** tekrarı kaldırmak prompt mühendisliğinde
   *işlevsel* olabilir — kuyruk her kalemde yazılıyken kural kalem düzeyinde daha güçlü
   bağlanmış olabilir. "hepsi" kelimesiyle kapsamı açık yazarak ve `[DEVRET]`'i her
   kalemde bırakarak azalttım, ama **sıfırlamadım.** Bu, ölçülemeyen tek eksen.
3. **Pay 408, eşiğin 8 birim üstünde.** 9 birimlik bir ekleme `DAR PAY` uyarısını geri
   getirir (kırmızı değil — uyarı). Daha fazla pay için `l.10` tekrarını almadım
   (§2, gerekçeli). İsterse mimar o ~30 birimi ayrıca karar verebilir.
4. **Çapraz-repo bayatlık (kapatılamaz):** `TAVAN=6000` gerçeği
   `pruvo-bot/worker/src/index.js:2232`'de. HocA orayı değiştirirse bu sabit bayatlar ve
   kapı yanlış sayıya göre hüküm verir. Kapının kendi docstring'inde ilan edilmiş;
   `~/dev/pruvo-bot`'a **dokunmadım**.
5. **`drift-sonda.py` canlı URL okur** → dal metnini görmedi (K6'da yazılı).
6. **Worker/Notion/bot reposu/D1/R2/`urunler.json`/arama:** hiçbirine dokunulmadı.
   Yasaklı paralel-işçi dosyalarının **hiçbiri** değişmedi (`git status` = 2 dosya).

---

## 5. MİMARA AÇIK SORULAR (iş durmadı, karar bekliyor)
1. ❓ **HocA'ya "kesilme yok" bilgisi gitmeli mi?** Kardeş mimar yanlış bir ölçümle
   (bayt≠karakter) hareket etti ve "cap'i bump edeyim mi" diye sordu — **tavanı
   yükseltmesi için hiçbir sebep yok.** Posta kutusu notu senin kalemin.
2. ❓ **`l.10` ↔ `l.36` yasak listesi tekrarı** (~30 birim) kalsın mı? Ben **kalsın**
   dedim (kesilme sigortası); aksini istersen tek satırlık iş.

---

**KENDİ İDDİAM: MERGE EDİLEBİLİR.**
Değişiklik 4 satır, tamamı üreticiden yeniden üretilmiş, 0 jeton kaybı, 29/29 kontrol
yeşil, `deploy.yml` 0 hunk. ⚠️ Ama iddiamın kapsamı dar: **makine kapıları yeşil**
demektir, **"metin doğru" demek değildir** — §4.1 ve §4.2'yi okumadan kapatma.
