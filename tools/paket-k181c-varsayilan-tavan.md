# PAKET K181c — ikinci kol ULAŞILAMAZ: bayraklar `None` varsayılanlı, reçete edilen çağrı onu hiç çağırmıyor

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **K181'in ARTIĞI, aynı sınıf**

## OLGU (mimar ölçtü, main `d4cdd67a`)
K181'in ikinci kolu **çalışıyor** (fikstür: 136 satır/13883 bayt → 115/11664). Ama gerçek
defterde ATEŞLEMEDİ:
```
python3 tools/defter-rotasyon.py DEVAM.md DEVAM-ARSIV.md
  → TASINAN=0 TASINAN_MADDE=0 DEFTER_SATIR=133      (tavan 130, kapanmis madde YOK)
```
Sebep koddan okundu: `--tavan-sayi` ve `--tavan-bayt` **`default=None`** (satır 610/614) ve
ikinci kol yalnızca `if a.tavan_sayi is not None or a.tavan_bayt is not None` ise devreye
giriyor (satır 628). Dosya `TAVAN_SATIR`/`TAVAN_BAYT`'ı tek kaynaktan **zaten import ediyor**
(satır 294-295) ama **varsayılan olarak KULLANMIYOR**.

🔴 **İKİNCİ VE DAHA KESKİN OLGU:** kota kapısının bastığı reçete satırı bayraksızdır:
`CARE: python3 tools/defter-rotasyon.py DEVAM.md DEVAM-ARSIV.md`
ve **mimar icra kapısı yalnız o bayraksız biçimi serbest bırakıyor** — bayraklı çağrıyı
REDDEDİYOR (ölçüldü). Yani mimarın koşmasına izin verilen TEK biçim, sorunu ÇÖZMEYEN biçim.
Bu, bu depoda adı konmuş sınıf: [[kapinin-recete-ettigi-care-baska-kapida-yasak]]. K168 bu
sınıfı bir kez kapattı; K181 aynı sınıfı **yeniden açtı**, çünkü çare bayrağa bağlandı.

## MİMAR HÜKMÜ
1. `--tavan-sayi` ve `--tavan-bayt` **varsayılanları TEK KAYNAKTAN gelir**:
   `default=TAVAN_SATIR` / `default=TAVAN_BAYT` (dosyanın zaten import ettiği değerler).
   İkinci tablo AÇMA, sayıyı elle yazma ([[ikiz-tanim-sessiz-ayrisma]]).
2. Böylece **BAYRAKSIZ** çağrı iki ekseni de gözetir ve gerekiyorsa ikinci kolu çalıştırır.
   Reçete edilen komut, reçete edildiği gibi ÇALIŞMALIDIR.
3. Ekseni bilerek kapatmak isteyen için açık kapı: `--tavan-sayi 0` / `--tavan-bayt 0`
   (ya da `--tavan-yok`) o ekseni devre dışı bırakır. Kapatma **açık niyet** ister;
   varsayılan asla "ölçme" olamaz.
4. Davranış değişmeyen tek yer: tavan altındaki defter — bayraksız çağrı onu YİNE
   değiştirmemeli (bayt birebir).

## KABUL
```
python3 tools/defter-rotasyon.py --kendini-test   → DUSEN=0   (mevcut 7 vaka KORUNUR)
python3 tools/defter-kota-kapisi.py --kendini-test → DUSEN=0  (K178 bozulmadi)
```
🔴 **BELİRLEYİCİ YENİ FİKSTÜR (bu paketin varlık sebebi):** tavanı aşan, **hiç kapanmış
maddesi olmayan** bir defter üzerinde **BAYRAKSIZ** çağrı — `python3 defter-rotasyon.py
<defter> <arsiv>` — defteri iki eksende de tavan altına indirmeli. Bugün bu vaka
`TASINAN=0` dönüyor; fikstür ÖNCE kırmızı, onarımdan SONRA yeşil olmalı ve raporda
ÖNCE/SONRA satır-bayt sayıları yan yana yazılmalı.

**MUTASYON (2, ikisi de KIRMIZI yakmalı):**
- M1 varsayılanları `None`a geri çevir → yukarıdaki bayraksız fikstür tavan üstünde kalır.
- M2 tavan altındaki deftere de dokundur → "tavan altında bayt birebir" kontrolü kırmızı.
🔴 Yalıtılamayan mutant `YALITILAMADI` yazılır, "geçti" YAZILMAZ.

## SINIR VE ÇALIŞMA BİÇİMİ
- **Sana verilen ağaçta çalış. Mutlak yol (`/Users/okan/dev/pruvo/...`) KULLANMA, göreli
  yol kullan. ANA AĞACA YAZMA.** Tur sonunda kendi ağacının `git status --short` çıktısını bas.
- Docstring'i ÖNDEN yazma; önce kod + fikstür, belge en sonda.
- Bu dilim DAR: yalnız varsayılan düzeltmesi + belirleyici fikstür + 2 mutant. Kapsamı
  kendiliğinden genişletme.
- `DEVAM.md`ye DOKUNMA (araç onarılıyor, defter değil). `urunler.json` DOKUNULMAZ.
- 🔴 **DALDA COMMIT ET**, SHA'yı rapora yaz. Main'e push ETME.

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla. Son satır:
`K181c KENDINI_TEST=<rc> KOTA_TEST=<rc> BAYRAKSIZ_ONCE=<satir>/<bayt> BAYRAKSIZ_SONRA=<satir>/<bayt> MUTANT=<n>/2`
