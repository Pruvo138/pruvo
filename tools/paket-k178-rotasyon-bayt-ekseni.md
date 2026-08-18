# PAKET K178 — defter kotasına BAYT ekseni bağlanacak (bugün satır ekseni tek başına ölçüyor)

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Emir:** Okan (15:00) · **Ağaç:** worktree

## SORUN (Okan ölçtü)
Kota kapısı **yalnız SATIR** sayıyor. Bugünkü sayılar:
- `DEVAM.md` 130 satır / **12.132 B** (tavan 12.288 → marj **156 B**)
- `CLAUDE.md` 89 satır / **12.043 B** (tavan 12.288 → marj **245 B**)

Satır ekseni rahat olduğu için rotasyon bayt aşımını **GÖRMÜYOR**. Bu, bu depoda adı konmuş
bir sınıf: bir eksende ölçüp başka eksende taşmak ([[olcum-birimi-bayt-utf16]] ·
[[kabul-araligi-karsilastirma-araligi]]). Satırları BİRLEŞTİREREK satır tavanında kalmak
bayt eksenini **gizler** — bugün ben tam bunu yaptım (satır kısaltarak 131→130'a indim),
yani kusuru üreten davranış zaten canlı.

## MİMAR HÜKMÜ
1. Kota kapısı **İKİ ekseni birden** ölçer: satır **VE** bayt. Hangisi aşarsa KIRMIZI.
   Tek eksende yeşil olmak yetmez; hüküm `satir<=TAVAN AND bayt<=TAVAN`.
2. Aşan eksen **adıyla** raporlanır (`ASAN_EKSEN=BAYT` / `=SATIR` / `=IKISI`) — "kota aşıldı"
   demek yetmez, hangi eksende olduğu yazılır, yoksa çare yanlış eksene uygulanır.
3. Bayt ölçüsü **dosyanın diskteki bayt sayısı** (UTF-8), karakter DEĞİL. Türkçe metinde ikisi
   ayrışır ve bu depoda daha önce yanlış birim kullanıldı.
4. Rotasyon aracı (çare kolu) da aynı iki ekseni gözetir: taşıma sonrası **her iki eksen de**
   tavanın altına inmelidir; yalnız satırı düşürüp baytı bırakan bir tur `EKSIK` sayılır.
5. **LOSSLESS (Okan kuralı 11):** taşınan blok arşive AYNEN eklenir. Kabul: defterin düşen
   baytı ≈ arşivin artan baytı. Fark varsa `KAYIP` yaz — silme YOK, taşıma VAR.

## İCRA
- Kota kapısını ve rotasyon aracını bul (kanonik ad için kancalara ve `defter-rotasyon.py`ye
  bak; ad EZBERDEN yazma, çağrı grafından TÜRET → [[kapsam-evrenini-cagri-grafindan-turet]]).
- İki ekseni de uygula; eşik değerlerini **tek kaynaktan** oku, ikinci bir tablo AÇMA
  ([[ikiz-tanim-sessiz-ayrisma]]).

## KABUL (hepsi ZORUNLU, sayıyla)
```
<kota kapisi> --kendini-test        → DUSEN=0
<rotasyon araci> --kendini-test     → DUSEN=0
```
**MUTASYON (4 vaka, hepsi KIRMIZI yakmalı):**
- M1 **BAYT AŞIMI**: satır tavanın ALTINDA, bayt tavanın ÜSTÜNDE bir fikstür → kapı KIRMIZI
  ve `ASAN_EKSEN=BAYT` yazmalı. 🔴 **Bu vaka bu paketin varlık sebebidir**; yeşil dönerse iş
  BİTMEMİŞTİR.
- M2 SATIR AŞIMI: bayt altında, satır üstünde → KIRMIZI, `ASAN_EKSEN=SATIR`.
- M3 bayt kolunu ÖLDÜR (karşılaştırmayı `<=` yerine daima True yap) → M1 vakası KIRMIZI kalmalı,
  kalmıyorsa kol ölçülmüyor demektir.
- M4 bayt ölçüsünü **karakter** sayısına çevir → Türkçe karakterli fikstürde hüküm DEĞİŞMELİ.
🔴 Mutant birden çok ekseni birden tetikliyorsa YALIT: sayaç/eşiği mutasyona uydur ki yalnız
hedef kol yanabilsin ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]). Yalıtılamazsa
`YALITILAMADI` yaz, "geçti" YAZMA.
**KONTROL (2 vaka, YEŞİL kalmalı):** iki eksen de tavanın altında → rc=0 · tam tavanda
(eşitlik) → rc=0 (tavan DAHİL, `<` değil `<=`).

## SINIR
`DEVAM.md` / `CLAUDE.md` **İÇERİĞİNE DOKUNMA** — bu paket ÖLÇÜYÜ onarır, defteri budamaz.
`urunler.json` ve gizli kaynak düzlemi DOKUNULMAZ. Main'e push ETME, merge ETME.

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla. Her komutun rc'si + ham çıktı.
Ölçemediğin ekseni `OLCULEMEDI` + sebep. Geçici dosyayı SEN sil, `git status --short` ile kanıtla.
