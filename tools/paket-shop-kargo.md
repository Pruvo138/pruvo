# PAKET — Sepet: kargo ücreti + ödeme butonu düzeni
## (Okan kararı, 16 Tem gece — ekran görüntülü tespit)

**Kat:** Claude Mühendis (ödeme sınıfı — para hesabı, Codex'e verilmez).
**Çalışma şekli:** worktree; `urunler.json`'a dokunma. İki-yazar uyarısı: Faz D mühendisi
`build.py`/`secenekler.js`/ürün sayfası şablonunda çalışıyor — bu paket SADECE sepet
(index.html sepet paneli) + `shop/` worker + D1 şeması + shop kabul testlerine dokunur;
ürün sayfası şablonuna ve Faz D dosyalarına GİRME. `secenekler.js`'e yeni sabit gerekiyorsa
(KARGO_*) küçük ve ekleme-niteliğinde tut (çakışma riski düşük), mimara bildir.
**Önce oku:** `DEVAM.md` "Shop (self-servis odeme)" bölümü, `shop/KURULUM.md`,
`tools/paket-shop-odeme.md`.

## Kural (Okan, KESİN — değişiklik sadece Okan'dan)
- Sepet ürün toplamı (kuruşta) **< 2.500,00 TL → kargo 250,00 TL** eklenir.
- **≥ 2.500,00 TL → kargo 0** (tam 2.500 dahil bedava; Ege/Sheet akışındaki mevcut
  kuralla birebir aynı).
- Yuvarlama YOK (mevcut kuruş kuralı aynen); kargo ayrı kalem, ürün fiyatlarına yedirilmez.

## İş kalemleri
1. **Sunucu (asıl hesap):** `shop/` worker `/api/shop/baslat` kargoyu D1'den hesaplanan
   ürün toplamına göre KENDİSİ ekler — istemciden kargo tutarı OKUNMAZ (yollarsa yok
   sayılır). iyzico sepet kalemleri toplamı = ödenen tutar kuralına uygun biçimde kargo
   ayrı kalem olarak geçer. D1 `siparisler` kaydına kargo ayrı kolonda kuruş olarak yazılır
   (şema değişikliği `tools/d1-sema.sql`'e; mevcut satırları bozmayan ekleme).
2. **Sepet paneli (index.html):**
   - Ara toplam + "Gönderim: 250,00 TL" (ya da "Gönderim: Bedava") satırı + genel toplam.
     Görünen toplam = sunucunun tahsil edeceği tutarla AYNI (tek kuruş sapma kabul reddi).
   - Teşvik uyarısı: toplam < 2.500 iken "2.500,00 TL üzeri kargo bedava — bedava kargoya
     X TL kaldı" (X kuruşuyla doğru); ≥ 2.500 olunca "Kargo bedava ✓".
   - **Buton düzeni:** `ODEME_ACIK=true` iken birincil buton ödeme ("Güvenli Ödeme" /
     iyzico akışı), WhatsApp İKİNCİL buton olarak KALIR (kanal yaşıyor). `ODEME_ACIK=false`
     iken bugünkü gibi WhatsApp birincil. İki durum da build/görsel olarak kanıtlanır.
3. **WhatsApp sipariş metni:** sepetten WhatsApp'a gidilirse metne kargo satırı ve genel
   toplam da yazılır (müşteri iki kanalda aynı rakamı görsün).
4. Sitedeki "2.500 TL üzeri kargo ücretsiz" metinleri bu kuralla tutarlı mı tara; değilse
   düzelt (metin nerede geçiyorsa listele, rapora yaz).

## Kabul testleri (mimar koşacak)
1. `node shop/test/kabul.js` → mevcut testler yeşil + YENİ kargo testleri:
   a) ürün toplamı 2.499,99 TL → kargo 250,00 TL, tahsilat = 2.749,99 TL (kuruş birebir);
   b) tam 2.500,00 TL → kargo 0;
   c) 2.500,01 TL → kargo 0;
   d) istemci sahte kargo/tutar yollar → yok sayılır (sunucu değeri kazanır);
   e) D1 satırında kargo kolonu doğru kuruşla.
   Testlerin en az biri önce MEVCUT kodda KIRMIZI yanar (test tesiri kanıtı).
2. Sepet paneli görsel kanıt: <2.500 (kargo satırı + "X TL kaldı"), ≥2.500 ("Bedava"),
   ödeme kapalı/açık iki buton durumu — 4 ekran görüntüsü.
3. `node tools/parite-test.js` + `node tools/parite-ege.js` yeşil (dokunulmadı kanıtı).

## Rapor
Ölçülen/kanıtlanan her madde + "2.500 üzeri bedava" metninin geçtiği yerler listesi +
DEVAM.md güncellemesi. Yargı soruları mimara (KraL), Okan'a değil.
