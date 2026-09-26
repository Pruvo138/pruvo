# JEV-ENVANTER — PRUVO (KraL + tüm PRUVO evleri)

Hüküm J1 (Okan kararı 25 Eyl 2026 23:2x; tam metin `~/dev/otel-advisor/hazirlik/hukum-jev-ortak-karar-2026-09-25.md`)
+ Okan hedefi 26 Eyl: *"jev'in önünde engel olmasın, komut beklemeden kendiliğinden çalışsın, tüm evler rahatça kullansın."*
Metinden verilen HER karar (kova · puan · evet) Jev'e gider. "Dışında" yalnız §1.3 sınıflarıyla gerekçelenir.

## Nasıl kullanılır (her PRUVO evi, tam yol)
- **Ortak istemci** (Jev'e giden TEK yol, bakımı EyLüL): `python3 /Users/okan/.claude/jev/jev.py karar|toplu|saglik …` — skill `jev`.
- **PRUVO hazır kalıpları** (soru + seçenekler + eşik, tek kaynak `tools/jev-kaliplar.json`):
  `python3 /Users/okan/dev/pruvo/tools/jev_karar.py --kaliplar` · `--kalip <ad> --metin "…"` ·
  Python: `sys.path.insert(0, "/Users/okan/dev/pruvo/tools"); import jev_karar; jev_karar.kalip_karar(ad, metin)`.
- Kimlik: makinedeki wrangler oturumu → Cloudflare Workers AI (`typesafe/jev`); anahtar/ödeme = Okan kapısı, bugün GEREKMİYOR.
- Eşik: kalıpta `esik: null` = altın küme ölçülmedi ⇒ karar alınır ama DAİMA insan onayına düşer. Ev ≥30 gerçek örnekle
  eşiği ölçünce `jev-kaliplar.json`'a yazar ve aşağıdaki tabloya isabeti düşer.
- Kayıt: her çağrı `/Users/okan/.claude/jev-kayit/<YYYY-MM>.jsonl` (metinsiz); OTeLLa haftalık sayar.

## Durum (26 Eyl 2026)
- ✅ Jev canlı: Workers AI REST üstünden `hoca-niyet` → `urun_sorusu`, güven 1, 569 giriş token, ~0,9 sn (ölçüldü).
- ✅ `tools/jev_karar.py --kendini-test` 7 iddia / 0 kırmızı; 2 izole mutant (insan bandı · seçenek adı) ÖLDÜ.
- ✅ ENGEL 1 KAPANDI (26 Eyl 15:2x) — ortak istemci CF REST dış zarfını açmıyordu; EyLüL onardı (jev-testi 65/65,
  mutant 10/10). KraL canlı ölçümü: `hoca-niyet` → `urun_sorusu` 1,0 (656 ms) · `macit-kategori` → `otomobil` 0,93 ·
  `hoca-aciliyet` → 1,98/2 (0,97) — üçü de `motor=jev`.
- 🔴 ENGEL 2 — PRUVO mimar icra kapısı repo-dışı `jev.py` yolunu ANA oturumda reddediyor (5 evde). Çip
  `KraL-JevKapi-26Eyl` (`task_6d71d37a`): `serbest_cagrilar.SEKILLER`e Jev şekilleri + 5 ev vakası + mutant.
  Kapatan: çip dalı merge + `.claude/mimar-kapi-kur.py` ile 5 eve kurulum + her evde `jev.py saglik` serbest.
- 🟡 Worker'da (Ege, çalışma zamanı) Jev: `pruvo-bot` worker'ına `[ai]` bağlaması + FaR `motor/src/karar.mjs`
  sözleşmesi + `tools/jev-kaliplar.json` → HocA'ya paket olarak bildirildi.

## Adaylar

| # | Ev | Aday (kalıp · tip) | Durum | Tarih | Kapatan |
|---|---|---|---|---|---|
| P1 | HocA | Ege/WhatsApp gelen mesaj niyeti (`hoca-niyet` · secim 7) | ✅ **Jev'de, kendiliğinden, KALİBRE eşik 0,85** | 26 Eyl | Ege worker her gelen mesajı Jev damgalı niyetle KV `jev:<numara>:<wamid>`'e yazar (pruvo-bot canlı `5df2354f`); altın küme 60: argmax 42/60, net 33/36, t=0,85 net 26/0. Canlı gerçek mesaj OLCULEMEDI (Ege 26 Ağu'dan beri mesaj almıyor) |
| P2 | HocA | mesaj aciliyeti (`hoca-aciliyet` · puan 3) | Jev'de, kendiliğinden — KALİBRE DEĞİL | 26 Eyl | P1 ile aynı kayıtta `aciliyet{puan,etiket}`; etiketlenmedi, güven ort 0,44 ⇒ eşik yok (insan) |
| P3 | KraL | site formu / e-posta triyajı (`kral-eposta-triyaj` · secim 6) | aday · kalıp hazır | 26 Eyl | gelen kanal (Mail uygulaması / site formu) okuyucusu + altın küme 30 |
| P4 | KraL | "cevap gerekli mi" (`kral-cevap-gerekli` · evet) | aday · kalıp hazır | 26 Eyl | P3 ile aynı |
| P5 | MaCiT | ürün kategori ikinci görüşü (`macit-kategori` · secim 12) | ✅ **Jev'de, KALİBRE eşik 0,8** | 26 Eyl | `hasat_ekle` kancası kendiliğinden (pruvo-hasat `97a75454`); altın küme 88: p≥0,8 %96,2 (25/26), yanlış alarm 1/88. Açık: `tamirat` çekici, `dekorasyon`→`ev` kayıyor — seçenek metni düzeltilirse eşik YENİDEN ölçülür |
| P6 | MaCiT | RED gerekçesi sınıfı (`macit-red-gerekcesi` · secim 5) | Jev'de — yalnız kayıt, KALİBRE DEĞİL | 26 Eyl | altın küme 60 (7 seçenekle): argmax %33,3 ⇒ eşik yok (insan). `mukerrer_islev` (katalog) + `logo_tasiyor` (görsel) metinden seçilemediği için kalıptan ÇIKARILDI (26 Eyl); yeniden ölçüm 5 seçenekle, logo/mükerrer örnekleri altın kümeden düşülerek |
| P7 | ArTisT | arama/içerik niyeti (`artist-seo-niyet` · secim 6) | aday · kalıp hazır | 26 Eyl | GSC sorgu listesi 30 etiketli |
| P8 | TeKiN | üretim/jeneratör hata sınıfı (`tekin-uretim-hatasi` · secim 6) | aday · kalıp hazır | 26 Eyl | jeneratör hata kaydından 30 örnek |

## Dışında (§1.3 — Jev KAYIT YAZMAZ, SAYI ÜRETMEZ)
| Sınıf | Gerekçe |
|---|---|
| fiyat · taban fiyat · ödeme · iyzico · havale eşleşmesi | para — deterministik (`taban-fiyatlar.js`, shop worker) |
| D1 senkron · katalog paritesi · arama sıralaması | senkron/ölçüm — `d1-sync.py`, `parite-test.js` |
| kapı/nöbet hükümleri · CI | ölçüm — çalıştırılabilir test, model yargısı değil |
| şema · `urunler.json` alan doğrulama | şema — `denetim-kapisi.py` |
| lisans (CC-NC reddi) | hukuk/para — lisans alanı deterministik okunur; Jev yalnız serbest metinden ÖNERİ verebilir, karar kapıda |
