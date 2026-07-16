# PAKET — Sepet: kargo ücreti + ödeme butonu düzeni + HAVALE seçeneği + sipariş numarası
## (Okan kararları, 16 Tem gece)

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
5. **SİPARİŞ NUMARASI (zorunlu, TÜM siparişlerde):** Ege/Sheet akışındaki desenle aynı
   aile: `PR-yyMMdd-HHmmss` + aynı-saniye çakışmasına karşı kısa rastgele sonek. Sunucuda
   üretilir (istemciden alınmaz), D1 `siparisler` satırına yazılır, iyzico conversationId /
   ödeme kaydıyla eşlenir, müşteriye dönüş (siparis=ok) sayfasında ve Telegram bildiriminde
   gösterilir. Benzersizlik D1'de kısıtla garanti (UNIQUE); test var (aşağıda).
6. **HAVALE/EFT SEÇENEĞİ:** ödeme adımında kartla ödemenin yanına "Havale/EFT" seçeneği:
   - Müşteri havaleyi seçince: sipariş D1'e `havale-bekliyor` durumunda + sipariş numarasıyla
     yazılır (kargo kuralı aynen uygulanır); müşteriye IBAN + alıcı unvanı + ödenecek TAM
     tutar + "açıklamaya sipariş numaranızı yazın" ekranı gösterilir; Telegram'a
     "HAVALE BEKLENİYOR: <no> <tutar>" bildirimi düşer.
   - IBAN + alıcı unvanı TEK yerden okunur (config/var; koda dağıtılmaz). Değerleri Okan
     verecek — MİMARDAN iste, placeholder ile geliştir, gerçek değer deploy'da girilir.
   - Para iyzico'dan geçmediği için otomatik doğrulama YOK: onay adımı manuel (Okan dekontu/
     hesabı görünce). Bu pakette onay = D1 durum güncellemesi için güvenli, TEK basit yol
     (ör. ADMIN anahtarlı uç ya da belgelenmiş wrangler d1 komutu) — panel/arayüz KURMA,
     kapsam şişirme; öneri varsa mimara yaz.
   - Havale siparişi 'ödendi' İŞARETLENMEDEN Telegram "ödeme geldi" DEMEZ (sandbox dersinin
     havale hali: para görülmeden üretim tetiklenmez).

7. **DÖNÜŞ DURUM AYRIMI (mimar onayladı — sandbox mühendisinin bulgusu):** /donus'ta
   iyzico retrieve ALTYAPI hatası verdiğinde (status:failure, ör. 1001/ağ) sipariş
   'basarisiz'e ÇEKİLMEZ — parası çekilmiş müşteri geçici hatada kaybolmasın. Yeni durum:
   `incele` + Telegram uyarısı ("RETRIEVE HATASI — elle kontrol: <sipariş no>").
   'basarisiz' YALNIZ iyzico paymentStatus=FAILURE dediğinde. Test: mock retrieve'e
   status:failure döndürt → D1'de 'incele' + uyarı bildirimi; paymentStatus=FAILURE →
   'basarisiz' (iki yol da ayrı test).

8. **KDV AYRIŞTIRMASI (Okan, 16 Tem gece):** Fiyatlar KDV DAHİL kalır (tahsil edilen
   tutar DEĞİŞMEZ — bu kalem yalnız gösterim + kayıt). Sepet/ödeme özetinde ve dönüş
   sayfasında döküm: "Ara toplam (KDV hariç) + KDV (%X) + Genel toplam (KDV dahil)".
   Hesap: net = brüt / (1 + oran), KDV = brüt − net; kuruşta, yuvarlama farkı toplamı
   BOZAMAZ (net + KDV = brüt birebir — fark çıkarsa KDV kalemine yedirilir). Kargo dahil
   genel toplam üzerinden tek döküm. Oran TEK yerden config (varsayılan %20 — Okan
   teyidi bekleniyor, değişirse tek satır). D1 siparişe kdv_kurus kolonu (fatura için).
   Test: brüt 325,00 → net 270,83 + KDV 54,17 (toplam birebir 325,00); kargolu senaryo.

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
4. SİPARİŞ NO testleri: format doğru; aynı saniyede iki sipariş → iki FARKLI numara
   (çakışma testi); iyzico siparişinde conversationId eşleşmesi; havale siparişinde
   müşteri ekranında ve Telegram metninde numara var.
5. HAVALE testleri: havale seçimi → D1'de `havale-bekliyor` + doğru kargo + doğru toplam;
   'ödendi' işareti ancak onay yoluyla değişir (istemciden değiştirilemez — negatif test);
   IBAN ekranındaki tutar = D1'deki tutar_kurus birebir.

## Rapor
Ölçülen/kanıtlanan her madde + "2.500 üzeri bedava" metninin geçtiği yerler listesi +
DEVAM.md güncellemesi. Yargı soruları mimara (KraL), Okan'a değil.
