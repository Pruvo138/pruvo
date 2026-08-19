# PAKET K188 TUR 2 — KAPI ÖLÇEMEDİĞİ YERDE İZİN VERİYOR (fail-open sınıfı)

Tur 1'de `tools/kutu-esik-kapisi.py` + `tools/kutu-esik-kapisi-mutasyon.py` yazıldı ve
6/6 + 3/3 yeşil raporlandı. **Kabul REDDEDİLDİ.** Mimar okudu, üç delik ölçtü.

Sınıf: kapı, **ölçemediği her noktada `return 0` (İZİN) veriyor.** Oysa kapının varlık sebebi
"kutu tavanı aşmışken yazılmasın". Ölçemiyorsak aşıp aşmadığını BİLMİYORUZ → izin vermek
kapıyı sessizce yok eder ve elle-rotasyon sınıfı geri gelir. Bu tam olarak
`fail-slow fail-open'dır` + `düzeltme fail-loud'u fail-open'a çevirebilir` dersidir.

---

## D1 — 🔴 EŞİK KAYNAĞI YÜKLENEMEZSE KAPI TAMAMEN KAYBOLUYOR
`kanca_main()` satır 151-155: `arsiv_modulu_yukle()` patlarsa `return 0`.
Ve bu yükleme **hedef kontrolünden ÖNCE** koşuyor. Yani `tools/kutu-arsivle.py` taşınır,
adı değişir ya da sözdizimi bozulursa kapı **hiç kimseye** hiçbir şey demeden yok olur —
tam da "kimse fark etmiyor" arızasının kendisi.

**HÜKÜM:**
1. Modül yüklemesini **hedef kontrolünden SONRAYA** al. Sıra: araç adı → `file_path` →
   `hedef_kutu_mu()` → *(hedef DEĞİLSE `return 0`, modül HİÇ yüklenmez)* → modül yükle.
2. **Hedef kutuya yazılıyorken** modül yüklenemezse → **`return 2` (FAIL-CLOSED)**, stderr:
   `KUTU ESIK KAPISI (fail-closed): esik kaynagi (<yol>) yuklenemedi (<hata>) -> esik OLCULEMEDI, yazma REDDEDILDI.`
3. Hedef DEĞİLSE davranış değişmez (`return 0`), modül yükleme hiç denenmez.

## D2 — 🔴 HEDEF KUTU ÖLÇÜLEMEZSE İZİN VERİYOR
Satır 97-103: hedef kutu ama `kutu_satir_sayisi()` patladı → `return 0`.
**HÜKÜM:** `return 2` (fail-closed). stderr:
`KUTU ESIK KAPISI (fail-closed): hedef kutu olculemedi (<hata>) -> yazma REDDEDILDI.`

## D3 — kutu YOKSA izin (BU DOĞRU, DEĞİŞTİRME)
Satır 95-96: kutu diskte yoksa `return 0` **KALIR** — kutunun ilk kez yaratılması meşrudur.
Yanına gerekçe yorumu yaz: *"dosya YOK = ilk yaratim; tavan kavrami yok, fail-open MESRU"*.

## D4 — 🔴 M3'ÜN ÇAPASI KENDİ DİKTİĞİ YORUM
Satır 136: `return 2  # M3_FAIL_CLOSED`. Bu işaret **mutasyon bataryası için eklenmiş**.
Çapa, ölçtüğü kodun kendisi olmalı; araç kendi nişan tahtasını boyamaz.
**HÜKÜM:** `# M3_FAIL_CLOSED` yorumunu SİL. M3'ü gerçek koda çapala (ör. `rotasyon_ciktisini_yaz(sonuc)`
çağrısını izleyen `return 2`'yi, çevresindeki BENZERSİZ bağlamıyla birlikte — çok satırlı dizge kullan).
Aynı kural yeni mutantlar için de geçerli: **kaynağa işaret yorumu EKLEME.**

## D5 — 🔴 İKİ FAIL-CLOSED KOLU HİÇ ÖLÇÜLMÜYOR (beyan edilmiş survivor)
`return 2` üç yerde: satır **115** (rotasyon istisna attı), satır **124** (rotasyon sonrası
ölçüm patladı), satır **136** (rotasyon indiremedi). Tur 1'de **yalnız 136** ölçüldü.
115 ve 124 ne bir vakayla, ne bir mutantla ölçülüyor → beyan edilmiş, ölçülmemiş kol.
**HÜKÜM:** her fail-closed kolunun KENDİ vakası ve KENDİ mutantı olacak.

---

## YENİ TEST KOŞUMU (bunu mümkün kılan iki test-yalnız kanca)
Kapıya iki ortam değişkeni ekle (üretimde set edilmez, davranış değişmez):
* `PRUVO_KUTU_ESIK_ARSIV_ARACI` — hem modül yüklemesinin hem `subprocess` çağrısının
  kullandığı araç yolunu ezer. Set değilse `TOOLS/kutu-arsivle.py`.
* `PRUVO_KUTU_ESIK_ZAMAN_ASIMI` — `subprocess` timeout saniyesi (varsayılan 60).

Bu ikisi sayesinde her kol **gerçek** koşumla tetiklenir; sahte dallanma/monkeypatch YOK.

### YENİ VAKALAR (V7..V10) — mevcut V1..V6 AYNEN KALIR
| # | Kurgu | Beklenen |
|---|-------|----------|
| V7 | `ARSIV_ARACI` → stub script: modül olarak `VARSAYILAN_TAVAN = 300` tanımlar, `__main__` olarak `time.sleep(5)`. `ZAMAN_ASIMI=1`. Kutu tavan üstünde, hedef. | **rc=2**, stderr `fail-closed` + `rotasyon istisna`, kutu **DEĞİŞMEDİ** |
| V8 | Stub: `VARSAYILAN_TAVAN = 300` tanımlar, `__main__` olarak **kutu dosyasını SİLER** ve `exit 0`. Kutu tavan üstünde, hedef. | **rc=2**, stderr `fail-closed` + `rotasyon sonrasi ... olculemedi` |
| V9 | `ARSIV_ARACI` → **var olmayan yol**. Hedef kutu, tavan üstünde. | **rc=2**, stderr `esik kaynagi ... yuklenemedi`, kutu **DEĞİŞMEDİ** |
| V10 | Aynı var olmayan yol, ama `file_path` **BAŞKA bir dosya** (hedef değil). | **rc=0** — hedef olmayan yol ETKİLENMEZ (D1/3) |

V10 KRİTİKTİR: D1 düzeltmesi "her şeyi reddet"e kaymadığını ölçer.

### YENİ MUTANTLAR (M4..M6) — M1..M3 AYNEN KALIR, toplam 6
| Mutant | Kırılan | HEDEF | YAN (yeşil kalmalı) |
|--------|---------|-------|---------------------|
| M4 ROTASYON-ISTISNA KOLU ÖLÜ | satır 115 `return 2` → `return 0` | **V7** | V1,V2,V3,V4,V5,V6,V8,V9,V10 |
| M5 ROTASYON-SONRASI-OLCUM KOLU ÖLÜ | satır 124 `return 2` → `return 0` | **V8** | diğer 9 |
| M6 ESIK-KAYNAGI FAIL-CLOSED ÖLÜ | D1'de yazdığın `return 2` → `return 0` | **V9** | diğer 9 (özellikle **V10 YEŞİL**) |

🔴 **HEDEF-KOL ATIFI ZORUNLU** (tur 1'deki kuralın aynısı, 6 mutant için):
(a) hedef vaka(lar) KIRMIZI · (b) **yan vakaların TAMAMI YEŞİL** · (c) aranan dizge kaynakta
**tam 1 kez** bulundu (0 ya da >1 ise mutant KIRMIZI raporlanır, sessizce "uygulandı" sayılmaz) ·
(d) mutantsız taban 10/10 YEŞİL.
Bir mutant yan vakaları da kırmızı yakıyorsa o mutant hedef kolu ÖLÇMÜYOR → daraltılır.

---

## KABUL (koşulacak, uydurma yeşil YASAK)
```
python3 tools/kutu-esik-kapisi.py --kendini-test      # rc=0, 10/10 YESIL
python3 tools/kutu-esik-kapisi-mutasyon.py            # rc=0, 6/6 OLDURDU
```
Ek iddia (bataryanın sonunda basılacak): gerçek `mimar-posta-kutusu.md` **bayt-bayt
değişmedi** ve `PRUVO_KUTU_ESIK_ARSIV_ARACI` **set DEĞİLKEN** kapı tur-1 davranışını korur.

## RAPOR
Dal kökündeki kanonik mühendis raporunu **ÜSTÜNE YAZ** (tur 2 raporu): iki komutun TAM çıktısı +
D1..D5'in her biri için "nasıl kapatıldı" tek satır + `OLCULEMEDI: <sebep>` (varsa).

## YASAKLAR
`git add`/`git commit` ATMA · `tools/kutu-arsivle.py`'ye DOKUNMA · `.claude/settings.json`'a
DOKUNMA · gerçek posta kutusuna test sırasında YAZMA · kaynağa mutasyon işaret yorumu EKLEME.
