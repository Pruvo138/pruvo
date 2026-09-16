# ONARIM EL KİTABI — kök neden sınıfı → araç → KABUL KOMUTU → kat

Nöbet kapısı (`nobet-kapi.py`) bu dosyayı **okur** ve dağıttığı SPEC'e ilgili satırın
`KABUL_KOMUTU` adayını yazar. İşçi de bu tabloya bakarak kaleminin kabul komutunu seçer.

🔴 **Bu dosya İKİNCİ BİR DOĞRULUK KAYNAĞI DEĞİLDİR.** Kural taşımaz, kural tekrarlamaz:
yalnız "hangi sınıf hangi araca ve hangi kabul komutuna gider" defteridir. Kabul komutunun
**biçim ve güvenlik kısıtları** (yorumlayıcı, beyaz liste kökü, metakarakter yasağı,
300 sn tavanı) tek kaynakta — `nobet-kapi.py::kabul_komutu_dogrula` — yaşar.
`kat` sütunu da türetilmiştir: `nobet-kapi.py::kat_sec` jeton tablosunun bu satırın
jetonlarına verdiği cevaptır; `nobet-kabul-test.py` her koşumda eşitliği ölçer (ayrışırsa
batarya KIRMIZI yanar). Elle değiştirme — jetonu değiştir, kat kendiliğinden gelsin.

**Satır sırası ANLAMLIDIR:** kapı ilk eşleşen satırı seçer, dar sınıflar üstte durur.

| sinif | jetonlar | arac | kabul komutu | kat |
|---|---|---|---|---|
| D1 senkron / sapma / drift | d1-sync, d1 senkron, d1 sapma, d1 drift, uzlastirici, katalog senkron | tools/d1-sync.py | `python3 /Users/okan/dev/pruvo/tools/d1-sync.py --durum` | minimax-m3 |
| Arama paritesi (site/Ege) | parite, arama paritesi, esanlam, ege arama | tools/parite-ege.js · tools/parite-test.js | `node /Users/okan/dev/pruvo/tools/parite-ege.js` | minimax-m3 |
| Katalog alan / tip sapmasi | katalog alan, alan tipi, tip sapmasi, sema gocu | tools/katalog-alan-kapisi.py | `python3 /Users/okan/dev/pruvo/tools/katalog-alan-kapisi.py` | MIMAR |
| Kisisel veri / gizlilik sizintisi | kisisel veri, gizlilik, sizinti, tedarikci adi | tools/kisisel-veri-test.py | `python3 /Users/okan/dev/pruvo/tools/kisisel-veri-test.py` | MIMAR |
| Shop / panel / odeme yuzeyi | shop, odeme, sepet, panel yuzeyi, konfigur | shop/test/kabul.js | `node /Users/okan/dev/pruvo/shop/test/kabul.js --paritesiz` | MIMAR |
| Yeni test CI'da kosmuyor | ci kapsam, ci'da kosmuyor, kancada yok, kabul testi cagrilmiyor, adim envanteri | tools/ci-kapsam-test.py | `python3 /Users/okan/dev/pruvo/tools/ci-kapsam-test.py` | MIMAR |
| Kaynak commit'i atilamiyor | commit atilamiyor, commit edilemedi, mimar commit kapisi, is agacta asili | tools/onarim-commit.py | `python3 /Users/okan/dev/pruvo/tools/onarim-commit.py --kuru --etiket kabul --mesaj-dosyasi /Users/okan/.claude/cron/onarim-el-kitabi.md --dosya tools/onarim-commit.py` | MIMAR |
| CI adimi yanlis seritte / beyansiz kapi | serit, is akisi, beyansiz kapi, kapi kirmizi, workflow adimi | tools/is-akisi-kapisi.py | `python3 /Users/okan/dev/pruvo/tools/is-akisi-kapisi.py` | MIMAR |
| STL R2/Drive kopya sapmasi | stl kopya, stl r2, stl drive, uc kopya, sadece drive, uretim dosyasi eksik | tools/stl-uc-kopya-nobet.py | `python3 /Users/okan/dev/pruvo/tools/stl-uc-kopya-nobet.py` | kimi |
| Kardes depo testi | kardes depo, kardes depo testi, kardes depodaki test, kardes repo testi | pruvo-hasat/test/hasat_denetim_kabul.py | `python3 /Users/okan/dev/pruvo-hasat/test/hasat_denetim_kabul.py` | minimax-m3 |

## ⚠ BEYAZ LİSTE KÖKLERİ (G1 ile çözüldü — 14 Ağu)

Kapı kabul komutunu G1 sonrası şu köklerin altından koşar (C4, tek kaynak
`nobet-kapi.py::BEYAZ_LISTE_KOKLERI`): `~/dev/pruvo/` · `~/.claude/cron/` ·
`~/dev/pruvo-hasat/` · `~/dev/pruvo-bot/` · `~/dev/pruvo-pazarlama/` ·
`~/dev/pruvo-jenerator/`. Kök listesi TEK yerde durur (ikinci kopya YASAK);
**beyaz listeyi işçi genişletmez** — genişletme mimar/Okan kararıdır.

## Kabul komutu nasıl seçilir (üç soru)

1. Kalem yeniden bozulursa bu komut KIRMIZI yanar mı? (yanmıyorsa yanlış komut)
2. Onarım geri alınırsa komut yine yeşil kalır mı? (kalıyorsa tautoloji — daralt)
3. Komut ağ/kimlik/uzak durum ister mi? İsterse 300 sn'de düşer ve `OLCULEMEDI` verir;
   ölçümü yerelleştirilmiş bir kabul testine indir.
