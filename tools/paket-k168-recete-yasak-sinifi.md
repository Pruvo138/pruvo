# PAKET K168 — Bir kapının REÇETE ETTİĞİ çare, başka kapıda YASAK (SINIF kalemi)

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ (kod `tools/`de; mimar eli sürmez).
K168'in halefi değil, **sınıf hâline getirilmiş hâli**. Tekil yama artık YASAK.

## 1. ÖLÇÜLEN OLGU — YEDİNCİ tekrar

`DEVAM.md` kota tavanını (130 satır) aşınca commit kapısı şunu basıyor:

```
!! DEFTER KOTASI ASILDI — DEVAM.md <n> satir (tavan 130).
!! CARE: python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py DEVAM.md DEVAM-ARSIV.md
```

Kotayı aşan rol **MİMAR**'dır (defteri mimar yazar). Ve mimar bu çareyi **KOŞAMAZ**:
`mimar-icra-kapisi.py` mimara yalnız `python3 tools/durum.py` ve
`python3 tools/d1-sync.py --durum` izni verir. Sonuç: kapı bir çare yazıyor, ikinci kapı o
çareyi reddediyor; mimar her seferinde rotasyonu **elle taklit** ediyor.

**Sayım (arşiv kayıtlarından):** 18 Ağu 08:2xZ'deki taşıma ALTINCI, bugün 10:5xZ'deki
YEDİNCİ elle taklit. Üçüncü tekrarda tekil yama zaten yasaklanmıştı
([[ucuncu-tekrar-sinif-kapisi]]); dördü de yasağa rağmen yapıldı.

🔴 **ELLE TAKLİDİN GERÇEK BEDELİ ölçülebilir bir risktir, estetik değil:** rotasyon bir
1:1 taşımadır; elle yapıldığında komşu satırı silme ([[indeks-ile-silme-komsuyu-siler]]) ve
kapanmış kalemi diriltme riski her turda yeniden doğar. Araç bunu deterministik yapıyor —
ama koşturulamıyor.

## 2. HÜKÜM — iki kol, ikisi de aynı dilimde

### H1 — Reçete edilen çare mimara AÇILIR (dar kapsam)

`tools/mimar-icra-kapisi.py`'nin mimar serbest kümesine **tam olarak şu çağrı şekli** eklenir:

```
python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py <DEVAM.md yolu> <DEVAM-ARSIV.md yolu>
```

* **Serbest bırakılan şey betiktir, `python3` DEĞİL.** Argüman sayısı ve ilk argümanın
  kanonik yolu doğrulanır; serbest-biçim argüman, ek bayrak, kabuk operatörü REDDEDİLİR.
* Bu bir muafiyet DEĞİL, **kapının kendi reçetesinin tanınmasıdır**. Gerekçe koda yorum
  olarak yazılır ve bu paketin adını taşır.

### H2 — SINIF KAPISI: reçete edilen her çare, koşulabilir olmalı

Yeni nöbetçi `tools/recete-kapisi.py`:

1. `tools/` altındaki kapı/nöbetçi betiklerinin **insana bastığı metinlerde** reçete
   satırlarını bulur — `CARE:` / `COZUM:` / `Duzeltip tekrar` gibi öneklerden sonra gelen
   `python3 …` komutları.
2. Bulduğu her komutu `mimar-icra-kapisi`'ne **kuru** sorar (gerçek çalıştırma YOK).
3. Reddedilen bir reçete varsa **RED**, reçeteyi basan dosya ve satırıyla birlikte.

🔴 **Kapsam evreni ad desenine DEĞİL ölçülebilir bir ölçüte bağlanır** ve ölçüt KODA yazılır
([[kapsam-evrenini-cagri-grafindan-turet]]). Evren boş çıkarsa **YEŞİL DÖNMEZ** —
`OLCULEMEDI`, rc≠0. Boş evren yeşil değildir.

⚠️ H2 bulduğu her şeyi H1 gibi otomatik AÇMAZ — yalnızca **çelişkiyi RAPORLAR**. Hangi
reçetenin açılacağı mimar hükmüdür; kapı sessizce yetki genişletemez.

## 3. KABUL (çalıştırılabilir)

```
python3 /Users/okan/dev/pruvo/tools/recete-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/mimar-kilit-test.py
```

son satırlar + rc=0:

```
RECETE=<n> REDDEDILEN=0 EVREN=<n> MUTANT=3/3 KONTROL=2/2
```

### Mutantlar (3/3 KIRMIZI)

* **M1** — H1'i geri al (`defter-rotasyon.py`yi serbest kümeden çıkar) → `REDDEDILEN=1`,
  reçeteyi basan dosya adıyla RED.
* **M2** — reçete tarayıcısının evrenini boş kümeye indir → `EVREN=0` ile YEŞİL DÖNMEMELİ.
* **M3** — H1'i serbest-biçim argümana genişlet (`defter-rotasyon.py <herhangi bir şey>`)
  → **RED** (yetki genişlemesi kapıyı kırmızı yakmalı, sessizce geçmemeli).

### Kontroller (2/2 YEŞİL)

* **K1** — Bugün mimara serbest olan iki komut (`durum.py`, `d1-sync.py --durum`) AYNEN
  serbest kalır; kapsam daralmaz.
* **K2** — Bugün mimara YASAK olan ölçüm komutları (`wc`, `sort`, `head`, `sed`, serbest
  `python3`) YASAK kalır. H1 bir delik AÇMAMALI ([[kapi-kapsam-genisletme-tuzagi]]).

## 4. CI KABLOSU (aynı dilimde — muafiyet YOK)

`tools/recete-kapisi.py` **hijyen şeridine** (`nobet.yml` SERİT B) bağlanır; kırmızısı
müşteriye para ödetmez / veri sızdırmaz / siteyi durdurmaz. Kabul satırına `CI_KAPSAM_RC=0`
yazılır. **İZİN LİSTESİ'ne muafiyet EKLENMEZ** — muafiyet "koşuyor" demek değildir.

## 5. SINIRLAR

* `defter-rotasyon.py`'nin KENDİ gövdesine DOKUNULMAZ (mutasyonla yeşil olduğu 17 Ağu'da
  ölçüldü: 7/7).
* Kota tavanı (130) DEĞİŞTİRİLMEZ; bu paket kotayı değil **çareye erişimi** onarır.
* `mimar-icra-kapisi.py` üzerindeki başka hiçbir kural değiştirilmez.
* Kaynak kod commit'i worktree'de; iş bitince worktree KALDIRILIR ve `git worktree list`
  ile kanıtlanır. Şu an tavan 2/2 dolu — yeni worktree açmadan önce boşluk ölç.

## 6. İŞÇİ TALİMATI

* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Raporu ÖNCE oluştur; başka turun raporunun ÜZERİNE YAZMA, başa EKLE.
* Her sayının `grep -c` kanıtı raporun İÇİNDE.
* **DOKUNMA:** `urunler.json` · `crontab` · `~/.claude/cron/gozcu.py` · `DEVAM.md`.
