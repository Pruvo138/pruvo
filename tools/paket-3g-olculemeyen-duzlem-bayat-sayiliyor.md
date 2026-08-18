# PAKET ③g — Sahiplik kapısı CI'da KIRMIZI: ölçülemeyen düzlemin satırlarını "BAYAT" sayıyor

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ · kabul MİMARDA.
③'ün CI kabulü **nihayet ölçüldü** (K178b sayesinde adım artık koşuyor) ve **kırmızı** geldi.
Kırmızının bir yarısı GERÇEK, bir yarısı KUSUR.

## 1. ÖLÇÜLEN OLGU (canlı koşum `32147516581`, `serit-b`, ham)

```
Cron evreni: OLCULEMEDI (sebep: CRON dizini yok (HOME/.claude/cron bulunamadi), yol=None)
EVREN=155 HARITADA=171 EKSIK=2 BAYAT=18 SAHIPSIZ=153 KABUL_DOLU=60 KABUL_YOK=111 KABUL_BOS=0
BAYAT (haritada var, evrende yok) — RED:
  satir 16  cron:cop-denetimi-kabul.py
  satir 17  cron:gozcu.py
  … (18 satırın TAMAMI `cron:` önekli)
rc=1
```

**Teşhis — kırmızı ikiye ayrılıyor:**

| Bulgu | Sayı | Hüküm |
|---|---|---|
| `BAYAT` sayılan `cron:` satırları | 18 | 🔴 **KUSUR** — düzlem ÖLÇÜLEMEDİ, satırlar yargılanamaz |
| `EKSIK` (evrende var, haritada yok) | 2 | ✅ **GERÇEK BULGU** — harita eksik, tamamlanmalı |

`BAYAT` tanımı "haritada var, evrende YOK". Ama CI'da cron evreni **hiç ölçülmedi**
(dizin yok, ki bu koşucuda BEKLENEN durumdur). Ölçülmemiş bir evrene göre "yok" demek,
**ölçülemeyeni kırmızı okumaktır** — bu depoda kapalı eksen
([[kapi-varlik-olcer-yokluk-olcmez]] · [[hukum-yanlis-birimde]]). Kapı kendi bastığı
`OLCULEMEDI` satırını kendi hükmünde KULLANMIYOR.

Sonuç: bu hâliyle kapı CI'da **her koşumda ve kalıcı olarak** kırmızı — yani ya susturulur
ya güvenilmez olur. İkisi de kabul edilemez.

## 2. HÜKÜM

**H1 — Ölçülemeyen düzlemin satırları YARGILANMAZ.** Bir düzlem (`cron:` / `tools/`)
`OLCULEMEDI` ise, o düzleme ait harita satırları `BAYAT` ve `EKSIK` hesabının **DIŞINDA**
kalır ve ayrı sayılır:
```
OLCULEMEYEN_DUZLEM=<ad> OLCULEMEYEN_SATIR=<n>
```
Bu sayı **yeşil değildir ama kırmızı da değildir**; hükmü ayrı verilir ve çıktıda sebebiyle
birlikte görünür.

**H2 — Hüküm ölçülen düzlemlere göre verilir.** `tools/` düzlemi ölçülebiliyorsa onun
`EKSIK`/`BAYAT`'ı hükmü belirler. Tüm düzlemler ölçülemezse → `rc=2 OLCULEMEDI`
(boş evren yeşil değildir).

**H3 — `EKSIK=2` GERÇEKTİR, kapatılacak.** Evrende olup haritada olmayan iki mekanizma
haritaya eklenir (bugün eklenen yeni kapılar). 🔴 `EV` **UYDURULMAZ**: bilinmiyorsa
`EV=BILINMIYOR`, `KABUL_KOMUTU` bilinmiyorsa `YOK`.

⛔ **YASAK ÇÖZÜMLER:** 18 `cron:` satırını haritadan SİLMEK · kapıyı muafiyete almak ·
CI adımını kaldırmak · `BAYAT`ı sessizce yok saymak. Amaç kırmızıyı yeşile boyamak değil,
**hükmü doğru vermek.**

## 3. KABUL (çalıştırılabilir) — İKİ ORTAMDAN

```
# (a) yerel: cron dizini VAR
python3 tools/sahiplik-kapisi.py
# (b) CI taklidi: cron dizini YOK (sentetik HOME, gerçek HOME'a YAZMAZ)
python3 tools/sahiplik-kapisi.py --kendini-test
```

* **(a)** `cron:` satırları normal yargılanır; `OLCULEMEYEN_SATIR=0`.
* **(b)** `OLCULEMEYEN_DUZLEM=cron OLCULEMEYEN_SATIR=18`, `BAYAT` bu 18'i **İÇERMEZ**,
  `tools/` düzlemi temizse **rc=0**.

son satır:
```
EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=<n> OLCULEMEYEN_SATIR=<n> SAHIPSIZ=<n> KABUL_BOS=0 MUTANT=<k>/<k> KONTROL=2/2
```

### Mutantlar (KIRMIZI olacak)
* **M1** — ölçülemeyen düzlemin satırlarını `BAYAT`a geri kat → (b) vakası DÜŞER.
  *(Bugünkü hatayı birebir yakalayan mutant budur.)*
* **M2** — tüm düzlemler ölçülemezken rc=0 döndür → batarya KIRMIZI.
* **M3** — `EKSIK`i sessizce yok say → DÜŞER.
* ③f'nin mevcut mutantları KORUNUR (hedef ağaç türetimi, `CRON_EVRENI` raporu).

### Kontroller (2/2 YEŞİL)
* **K1** — `tools/` düzleminde gerçek bir `BAYAT` satırı hâlâ RED üretir (H1 gerçek
  bulguyu gizlememeli).
* **K2** — `SAHIPSIZ` sayısı kapıyı KIRMIZI yakmaz (③ §2b kuralı korunur).

### 🔴 ASIL KABUL — canlı koşum
Merge sonrası SERİT B koşumunda `Sahiplik haritasi kapisi …` adımı **success** olacak ve
çıktısında `OLCULEMEYEN_DUZLEM=cron` görünecek. Adım `skipped` ise ölçüm YAPILMAMIŞTIR
([[kablo-da-kosuyor-demek-degil]]); kuyrukta `cancelled` olursa `OLCULEMEDI` yaz.

## 4. SINIRLAR

* Harita satırlarının `EV` içeriğine DOKUNULMAZ (171 satır `BILINMIYOR` kalır; sahip
  atama mimar hükmü, ayrı dilim).
* `cron:` satırları haritadan SİLİNMEZ — yerelde koşan hükümde onlara ihtiyaç var.
* Kardeş depolar kapsam dışı.

## 5. İŞÇİ TALİMATI

* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Bütçenin yarısında elindekini commit et, raporu kapat.
* Kaynak kod commit'i worktree'de; iş bitince worktree kaldırılır, `git worktree list` kanıt.
* Raporu ÖNCE oluştur; başka turun raporunun ÜZERİNE YAZMA, başa EKLE.
* **DOKUNMA:** `urunler.json` · `crontab` · `DEVAM.md` · `~/.claude/cron/` ·
  `.github/workflows/` (kapı adımı ZATEN bağlı, değiştirme).
