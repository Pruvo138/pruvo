# DEVAM (KraL) — 8 Agu 2026

## 🔴 UÇUŞTA — ÖTEKİ KraL OTURUMU BU İŞLERE GİRMESİN (10 Ağu ~14:2xZ)

Paylaşılan defterde bugün iki KraL nöbet oturumu aynı pencereyi mükerrer koştu; tekrarlamayalım.

1. **`muh/teslim-beyani` dalı — AÇIK, merge BEKLİYOR.** Ürün sayfasına sınıf-bazlı teslim beyanı
   (943 hazır ↔ 23.977 özel). Üç onarım turu geçti (`4a41f4a0` → `6588b076`), **iki bağımsız
   çürütücü iki kez `CURUTULDU` verdi**, ikisi de kapatıldı: (a) "ölçüye özel / ölçü onayından
   sonra" ifadesi %99,84'ü sabit tasarım olan katalog ürününe yanlış hukuki sınıf basıyordu →
   tetikleyici "siparişiniz onaylandıktan sonra"ya çekilip sipariş onay e-postasıyla hizalandı;
   (b) `\bcayma\b` daraltması kapıyı o eksende KÖR bırakmıştı (Türkçe çekim varyantlarını
   yakalama oranı 9/9 → 3/9'a düşmüştü) → desen artık yanlış-pozitif KÜMESİNDEN türüyor,
   9/9 yakalıyor ve katalog yanlış-pozitifi 0. Ders: muafiyeti jetonun tamamını daraltarak
   verme, kanonik yanlış-pozitif kümesinden TÜRET.
   Kapı **29 → 38 iddia**, mutant **3 → 18 + 6 kontrol**, silinen iddia 0, gevşetme 0.
   Üçüncü çürütme turu UÇUŞTA. **Bu dala dokunma, merge etme.**
2. **Parite ayrışımı — main'e ait, SAHİPSİZ.** `parite-test.js` **1 açıklanamayan / 1199**:
   `q="braketi" marka="Mazda 3"` → `/ara`=0, yerel=56. `origin/main`'in PRİSTİNE klonunda
   birebir aynı → dalın regresyonu DEĞİL. `parite-ege.js` 851/851 temiz. Kök neden bu turda
   ölçülmedi; "Mazda 3" bir MODEL, marka ekseninde sorgulanıyor. Yayını bloklamıyor (CI yeşil).
3. **Yerel parite paneli (`localhost:8137`) — TEŞHİS EDİLDİ, iş sıraya alındı.** Panelin kendisi
   taze (her GET'te modül yeniden yükleniyor, 15 sn'de bir `/veri` fetch) ama beslediği defter
   `.marka-kapsama.json` **28,6 saat bayat ve tazeleyeni YOK** — tek yazıcısı ürün ekleme
   partisinin yan etkisi. Ölçülen sapma: BMW 2359↔2347 (%0,5), Ford 2088↔2582 (%19),
   **Mazda 89↔1361 (gerçeğin %6,5'i, beş hücrenin hepsi `son_tarih:"backfill"`)**. Asıl kusur:
   başlıktaki "son güncelleme" damgası HESAPLAMA anını gösteriyor, VERİ yaşını değil → bayat
   hücre taze hücreden ayırt edilemiyor. Yön: defteri tazelemek değil KALDIRMAK (ürün sayısı
   `urunler.json`'dan, platform kırılımı gizli kayıttaki kaynak-id öneklerinden türetilebilir)
   + panel kaynak yaşını ve hücre bazında son ölçüm tarihini göstersin. Türetmeye geçiş MaCiT'in
   ekleme akışındaki `kaydet` adımını gereksizleştirir → posta yazılacak.


## 🕐 CI NOBETI — 10 Agu 2026 14:37Z turu (KraL)

**Mail (0.5 adimi, kosulsuz supurme):** tam dizeyle eslesen inbox bildirim maili **0**,
"Run failed" **0**, tasinan **0**, tur sonu inbox **0**. Hukum **TEMIZ** — pozitif tanima izi
Cop'ten AYNI TAM dizeyle olculdu: **67** kayit, en yenisi 10 Agu 04:29. Vekil dize kullanilmadi.

**CI bagimsiz teyidi (60 kosumluk pencere):** `failure` **0** · success 53 · `cancelled` **4**
(art arda push supersede'i — ariza SAYILMADI) · ucusta 3. En son `failure` kaydi 10 Agu 01:10Z
(`feb98e81`, deploy) — pencerenin ~13,5 saat DISINDA; sonrasindaki tum deploy kosumlari yesil.

**⏱️ SURE EKSENI — HUKUM NIHAYET YAZILDI (8 ardisik basarili deploy kosumu birikti):** yayin
tavanini 8 kosumun **7'sinde** `serit-a2` koyuyor; min/ort/maks **17,9 / 21,6 / 24,8 dk**.
Diger joblar (min/ort/maks dk): serit-a3 10,5/16,4/18,2 · build 11,9/13,8/14,9 ·
serit-a4 0,2/0,2/0,3 · deploy 0,5/0,7/1,1 · yayin 0,6/0,6/0,7. Onceki iki turun "olculemedi"
hukmu KAPANDI (tek kosumdan okunmuyor, 8 kosum birikti).
**Adim birimi (kosum `31394761851`, job serit-a2):** en uzun adim yasal-sayfa drift kapisi
**398 sn** (6,6 dk) = job'un ~%36'si; ikinci 169 sn, ucuncu 78 sn. Tavan TEK adimdan
GELMIYOR — kalan ~11,6 dk cok sayida kisa adima dagilmis, yani bolme kazanci tek adimi
tasimakla ALINMAZ. (Adimin kendi yorumundaki sure beyanina guvenilmedi, ADIM birimiyle olculdu.)

**Yayin bayat DEGIL — uc ayak birlikte olculdu:** (a) guncel head `0cf568ac` icin zincir
UCUSTA (`31398615918`; serit-a4 success, build/serit-a2/serit-a3 kosuyor), (b) tavani serit-a2
koyuyor, (c) son yesil deploy head'i `4dead34a` ve `merge-base --is-ancestor 4dead34a 0cf568ac`
= EVET. Ucusu `cancelled` sayarak degil bu uc ayakla yargilandi.

**Alarm seridi:** deploy:needs DISINDAKI alarm kolu kosumu `31394762072` olcum aninda
**52,8 dk**dir ucustaydi (onceki turda ~38 dk). Yayini BLOKLAMIYOR, ariza SAYILMADI — ama
ayni jobun ardisik kosumlari birikince sure hukmu bu seride de yazilacak.

**Bu turda duzeltme YOK** (kirmizi yok), kod commit'i yok.
**Envanter:** `M tools/d1-sync.py` yabanci degisiklik hala duruyor — DOKUNULMADI.
`git worktree list` **2 satir** (ana agac + `muh/teslim-beyani`) — tavan icinde; UCUSTA
blogundaki dala dokunulmadi.
**Sonraki turun ILK isi:** yarim is YOK — normal tarama. Sure ekseninde siradaki soru:
serit-a2'nin ~11,6 dk'lik "cok kisa adim" kuyrugu bolunebilir mi (adim envanteri olculecek).

## 🔚 OTURUM KAPANISI — 9/10 Agu (marka tek-sayfa turu + yayin tavani)

**CANLIYA GITTI (SHA'larla, hepsi `origin/main`; canli olcumle teyitli):**
- `6b15062b` — **marka tek-sayfa merge**: marka sayfasi markanin TUM parcalarini listeliyor,
  cipler sayfa ici filtre. Ilk yuk HAFIFLEDI (bmw 56916→34868 bayt), ilk acilista veri istegi 0.
- `5d576510` — merge'in actigi iki kirmizi: yorumdaki ic surec dosyasi adi + marka uyelik
  **gerilemesi** (taban 0 kalan ↔ merge sonrasi 5; ayirt edici olculdu). Kapi GEVSETILMEDI,
  onarim uretim kodunda: 25 markada tek koleksiyon sayfasi.
- `7428747c` — sitemap kapsam **ikiz tanimi** (sabit 1088 → kanonik turetme, 1122==1122).
- `a046296a` — **53 siluet/duvar dekoru urunu katalogdan silindi** (23105→23052, Okan emri,
  `duzelt.py --toplu`, gizli kayit da temizlendi, tam yedek alindi).
- `cef49456` — SEO landing **WhatsApp CTA**: 322 sayfanin 303'unde link YOKTU → 0 eksik;
  pazarlama yuzeyinden kargo rozeti kaldirildi (3→0), yasal kosul korundu.
- `2d653f9f` — `ozet.json` ilk yuk **154530→134406 bayt** (butce YUKSELTILMEDI); 2,5 saat
  bekleyen oksuz yama bayt-birebir dogrulanip devralindi, iki sigdirmadan olculen iyisi secildi.
- `ee0047dd` — **sepet kargo esigi** (vaat 4→0, tahsilat satiri KALDI, 6 senaryoda kurus
  BIREBIR ayni) + **D1 `seq` sira kusuru** (264 kesirli / 276 sapan → 0) + kok neden: kanca
  artik kirli agaci degil COMMIT'i okuyor + sentetik fikstur git ortami **sinif** olarak
  tek kanonik yardimciya baglandi (9 arac) + worktree acilis nobetcisi.
- `a5ae0556` — kendi yamamin korlettigi **INDEX ekseni** (6 iddia) geri getirildi; temizlik
  battaniye degil cagri yerinde.
- `a855a720` — marka bataryasinda **5 hayatta kalan** kapatildi → **oldurucu 18/18**,
  kontrol 3/3 yesil (iki tautoloji dahil).
- `98758f0d` — **yayin tavani**: iki kendini-test kolu nobet seridine tasindi,
  `serit-a4` **3736s → 11s**; `deploy`'da olculen iddia **58→58** (yuzey kucULMEDI).
- `dd4f73ce` — K19 yargi kumesi: `Mazda|5` + `Renault|5` MODEL olarak yargilandi (veri kaynakli).

**Canli teyit (son deploy, artefakt 3,7 dk):** parite site **1199/1199** · Ege **852/852**
(ikisi de rc=0) · esik vaadi **0** · tahsilat satiri **VAR** · `/marka/*/diger/` **200** ·
landing `wa.me` **1** · D1 24300 senkron. Sabahki **883/1199** sira kusuru KAPANDI.
**Worktree envanteri 8 → 1** (arsivle-sonra-kaldir; hicbir sey silinmedi).

**KOSUYOR:** tarayici iscisi — canli marka sayfasinda **artimli kart cizimi + cip filtresi**
davranisi (ilk boya 80 kart → tetiklemeyle 2582'ye cikiyor mu). Izole worktree
`agent-ae0d15fbb1976006c`. Spec: scratchpad `marka-davranis-spec.md`. Bu eksen test'te
yesil ama CANLIDA hic olculmedi — sonucu gelmeden "marka sayfasi tamam" YAZILMASIN.

**BEKLIYOR (kim neyle bloke):**
1. **R2 158 gorsel** silinemedi — kova geneli 30 gun nesne kilidi. Okan A'yi secti (kilit
   GEVSETILMEYECEK); tek seferlik gorev **24 Agu 2026 18:00 TRT** kuruldu, kuyruk + geri
   donus yedegi depo disinda kalici.
2. `yayin` **olcek tavani**: 531 aday > 300 sinir. `deploy`'u BLOKLAMIYOR, ayri is.
3. **215 urun** basliginda marka geciyor ama `marka[]` uyesi degil — **VERI duzlemi**.
   `arama.py` gecis kolu ONCE kapatilmayacak (arama daralir, satis yolu).
4. H1/H3 kurali **16 model-olmayan** degeri model sayiyor — main'in mevcut kusuru.
5. Sentetik fikstur git ortami: 9 arac kanonik yardimciya baglandi, kapi `serit-b`'de.
   Yeni sentetik depo kuran her arac ayni yardimciyi kullanmali.
6. `tools/d1-sync.py`'de **yabanci commit'siz degisiklik** (mtime 09 Agu 22:44Z) —
   DOKUNULMADI, sahibi devam ettirmeli.

**OKAN'DA BEKLEYEN:** `pages` job'larina `timeout-minutes` konmasi.
(Sepet kargo esigi karari VERILDI ve uygulandi; R2 yolu A olarak SECILDI.)
