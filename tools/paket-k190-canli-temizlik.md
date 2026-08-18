# K190 — SAKLAMA SÜRESİNİ CANLIDA YÜRÜRLÜĞE SOKMAK (`talep-temizlik.py` → D1)

Mimar: KraL · Okan onayı alındı (19 Ağu) · Dal: `kral/k186-talep-hatti`
Şart (Okan): **canlı hat açılmadan önce bitecek.**

## 🔴 GEREKÇE — SAKLAMA SÜRESİ BİR **MÜŞTERİ VAADİ** KARARIDIR (mimar hükmü)

90 gün **Okan'ın kararıdır ve değişmiyor**. Ama raporda gerekçesi **kota/bayatlık diye
yazılmayacak**; asıl gerekçe şudur:

> **"Müşteri kodunu 91. gün getirirse ona ne diyeceğiz?"**

Kota ve bayatlık bu kararın *yan faydalarıdır*, sebebi değil. Sebep, saklama süresinin
müşteriye verilmiş bir **söz** olması: o gün sonrası kod **çözülemez** ve Ege "kayıt yok"
durumuna düşer. HocA, Ege metnini **bu cümleye** dayanarak yazacak.

## SORUN (K186'da ölçüldü, rapora yazıldı)
`tools/talep-temizlik.py` `sqlite3.connect()` ile **yerel bir dosyaya** bağlanıyor; gerçek
depo Cloudflare **D1**'dir. Yani bugün **90 günlük saklama süresi hiçbir yerde yürürlükte
değil**; araç yalnız mantığı ve kendini testini taşıyor.
`talepler` tablosu `pruvo-katalog` D1'ini Ege + `d1-sync` + `reklam_ref_gclid` ile
**PAYLAŞIR**; sınırsız büyüyen tablo ortak kotayı yer.

---

## ADIM 0 🔴 ÖNCE ERİŞİMİ ÖLÇ — tahmin etme, iş buna göre dallanır

K186'da ölçüldü: `npx wrangler@4` **kurulum** denemesi ağ hatası verdi
(paket kayıt sunucusuna erişilemedi). Ama `gh` komutları **çalışıyor** (GitHub'a erişiliyor).
Yani ağ topluca kapalı DEĞİL; kısıt npm kayıt sunucusuna özgü olabilir.

Şunları **ölç** ve sonucu rapora yaz:
1. `wrangler` **kurulu mu** ve hangi sürüm? (`d1-sync.py` onu nasıl çağırıyorsa aynı yolu
   kullan — `tools/d1-sync.py` içindeki wrangler çağrı satırını **oku**, kopyalama.)
   🔴 **Kurulu değilse KURMA** (ağ + disk izi) → `OLCULEMEDI` + sebep yaz, dur.
2. **SALT OKUMA** bir D1 sorgusu geçiyor mu — 🔴 **gerçek bir D1 sorgusu olacak**,
   `--durum` özeti DEĞİL, ve **yazma yolu İÇERMEYECEK**:
   `SELECT name FROM sqlite_master WHERE type='table' AND name='talepler'`
   (Bu sorgu `talepler` tablosunun canlıda **var olup olmadığını** da söyler — şema henüz
   uygulanmadı, muhtemelen **YOK** çıkacak; bu beklenen sonuçtur, hata değildir.)

**Dallanma:**
- **Erişim VARSA** → ADIM 1'i tamamla, `--kuru` ölçümünü gerçek D1'e karşı koştur.
- **Erişim YOKSA** → kodu yine yaz (ADIM 1), fikstürle kanıtla, ve rapora
  `OLCULEMEDI: canli D1 erisimi yok (sebep: ...); --kuru olcumu CANLIYA KARSI
  KOSTURULAMADI` yaz. **Sayı uydurma, "muhtemelen çalışır" deme.**

---

## ADIM 1 — CANLI YOL (kod)

`talep-temizlik.py`'ye **D1 kolu** ekle. Kurallar:

1. **TEK KAYNAK, İKİZ TANIM YASAK.** Wrangler çağrı biçimi, veritabanı adı, `--remote`
   bayrağı vb. `tools/d1-sync.py`'de zaten var. Onu **oku** ve aynı yordamı kullan;
   ikinci bir çağrı sarmalayıcısı yazma. Mümkünse d1-sync'in ilgili fonksiyonunu
   **import et**.
2. **Sayan ve silen TEK yordam** (K186'nın F1/R1 dersi):
   `SELECT kod, olusturma FROM talepler` → Python'da ISO ayrıştır → eşikten eski `kod`
   listesi → `--uygula` ise **o listeyle** `DELETE ... WHERE kod IN (...)`.
   🔴 `sil_eski` listeyi **yeniden hesaplamayacak** (R1 zaten böyle kuruldu, D1 kolunda da
   aynı kalacak). Canlıda site + Faz-2 **eşzamanlı yazıyor**; iki hesap arası yarış demektir.
3. **Metin karşılaştırması YASAK.** `olusturma < esik` biçiminde SQL karşılaştırması
   yapma (F2 dersi: `Z` ekli kayıt metin sıralamasında `+00:00`'dan büyük çıkar).
   Ayrıştırma Python'da.
4. **Ayrıştırılamayan `olusturma` SİLİNMEZ** (F4, fail-closed).
5. **PARTİ TAVANI + KOTA KORUMASI** (mimar hükmü — bu karar **başka evin yayınını**
   etkilediği için mimarın kapısıdır, dört şartla onaylandı):
   - `DELETE`'ler parçalara bölünecek (mevcut 500'lük desen).
   - 🔴 **Tavan PARAMETRE olacak** (`--tavan`), **5.000 bir TAHMİNDİR**. Muhafazakâr
     varsayılanla başla ve her koşumda **fiilen etkilenen satır sayısını BAS**.
     **Gerçek maliyet ölçülmeden tavan yükseltilmez.**
   - 🔴 **SEÇİM DETERMİNİST**: `ORDER BY olusturma, kod` sabit olacak. Yoksa partiler
     arasında satır atlanır ve `KALAN=<n>` **yalan söyler**.
   - 🔴 **90 gün TEK KAYNAKTAN** gelecek (saklama sabiti), iki yere yazılmayacak.
     Bu turda ikiz tanımdan **iki kez** yandık.
   - 🔴 **İlk gerçek koşum mimarda/Okan'da.** `--kuru` çıktısı silinecek satır
     **SAYISINI** ve küçük bir **ÖRNEĞİNİ** göstersin (silme geri alınamaz).
   Gerekçe: D1 günlük yazma kotası Ege ve `d1-sync` ile PAYLAŞILIYOR; sınırsız silme
   başka bir evin yayınını durdurabilir.

5b. 🔴 **EVLER ARASI SONUÇ — `--kuru` RAPORUNDA AÇIKÇA YAZILACAK.**
   `talepler` kaydını silmek, o kodun **çözülemez** hâle gelmesi demektir. HocA'nın
   Faz-2'si gelen mesajda `PR-XXXXXX` yakalayıp kaydı arıyor; 90 günden eski bir kodla
   müşteri WhatsApp'tan yazarsa Ege **"kayıt yok"** durumuna düşer.
   Bu bir **kusur değil**, saklama sözünün doğal sonucudur — ama davranışın **TANIMLI**
   olması gerekir. `--kuru` çıktısına şu satır girecek:
   ```
   UYARI: silinen kod artik COZULEMEZ (Faz-2 'PR-...' aramasi bos doner).
   ```
   Ege'nin o hâlde ne diyeceği **HocA'nın kapsamı**; mimar ona ayrıca haber veriyor.
6. **VARSAYILAN HÂLÂ KURU.** `--uygula` olmadan **hiçbir** `DELETE` çalışmaz.
   🔴 Bu turda `--uygula` **KOŞTURULMAYACAK**.
7. **Yerel sqlite kolu KALACAK** (`--db` ile) — fikstür testleri onun üstünde koşuyor.
   İki kol **aynı yordamı** paylaşsın; SQL yürütücüsü değişsin, karar mantığı değişmesin.
   🔴 Karar mantığı iki kez yazılırsa bu paketin bütün dersi boşa gider.

---

## ADIM 2 — KABUL

`--kendini-test` genişleyecek. Mevcut `F1..F5` **bozulmayacak**, üstüne:

| # | İddia |
|---|---|
| L1 | 🔴 **DAVRANIŞSAL EŞDEĞERLİK (mimar: "en önemli madde"):** **AYNI fikstür verisi** üzerinde yerel sqlite yürütücüsü ile D1 yürütücüsü **BİREBİR AYNI kararı** üretir (aynı `kod` listesi, aynı sıra, aynı `KALAN`). Ayrışırlarsa **KIRMIZI**. Eksen taraması yetmez — davranış ölçülecek. (F1/R1'in dersi "sayan küme = silen küme" ancak böyle korunur.) |
| L1b | Karar fonksiyonu **tek tanımlı** (eksen taraması: ikinci bir kopya yok) |
| L7 | Parti seçimi **DETERMİNİST**: aynı veri iki kez koşulduğunda aynı parti, aynı sırada çıkar (`ORDER BY olusturma, kod`) |
| L8 | 90 günlük saklama sabiti **tek kaynakta**; ikinci bir tanım yok (eksen taraması) |
| L2 | Parti tavanı aşıldığında `KALAN=<n>` basılır ve fazlası **silinmez** |
| L3 | `--uygula` YOKKEN hiçbir `DELETE` yürütülmez (sahte yürütücüyle sayılır: DELETE sayısı **0**) |
| L4 | D1 kolunda da ayrıştırılamayan `olusturma` **silinmez** (F4'ün D1 ikizi) |
| L5 | D1 kolunda sayılan küme ile silinen küme **birebir aynı** (F1/R1'in D1 ikizi) |
| L6 | **NEGATİF:** eşiğin bir gün berisindeki kayıt (89 gün) **silinmez** — hem `Z` hem `+00:00` biçiminde |

Her iddia için mutant; her mutant **tam olarak bir** iddia düşürsün, düşen küme basılsın,
mutasyonun kaynağa girdiği ayrıca kanıtlansın. İzole edilemeyen `OLCULEMEDI` + sebep.

### 🔴 L9 — MUTASYON ARTIĞI: KABUL TESTİ KENDİ TEMİZLİĞİNİ **ÖLÇECEK** (mimar hükmü)

TUR 2e koşarken ağaçta bir mutasyon artığı görüldü (`tools/k186-mutant-*.py`).
**Hüküm: artık bırakan tur KABUL EDİLMEZ**, ve `finally` ile silmek **YETMEZ** — `finally`
atlanabilir, süreç öldürülebilir, istisna yutulabilir. Kapı **sonucu** ölçmeli, niyeti değil.

| # | İddia |
|---|---|
| L9 | Batarya koşumundan **SONRA** ağaç temiz: `git status --porcelain` çıktısı bataryanın kendi değiştirdiği dosyalar dışında **boş**, ve `tools/` altında `*mutant*` deseninde **hiçbir dosya yok** |

Bu iddia `tools/talep-hatti-test.py`'ye de eklenecek (aynı sınıf, aynı risk).
Disk kuralı üstündür: **üreten temizler, "sonra bakarız" YOK.**
🔴 L9'un kendisi de mutantla kanıtlanacak: temizliği kaldıran bir mutant L9'u düşürmeli.

**CI kablosu:** `talep-temizlik.py --kendini-test` **zaten** `nobet.yml` SERIT B'de koşuyor
— yeni iddialar oraya otomatik girer. `ci-kapsam-test.py` rc=**0** kalacak.

---

## YASAKLAR
- 🔴 `--uygula`yı **KOŞTURMA**. Canlı D1'e **tek satır** yazma.
- `wrangler deploy` YOK · `d1-sync.py --sema` YOK · `shop/wrangler.toml`'a cron/trigger
  EKLEME (zamanlanmış iş **Okan/mimar kapısı**).
- `git commit` / `git push` YOK (koordinatör atar).
- `urunler.json`, `index.html`, `talep-alanlari.js`'e dokunma.
- Komut stili: dolar-değişken, dolar-parantez, `for`, `while`, `cd`, çıktı yönlendirme,
  heredoc YASAK.

## TESLİM
Mühendis raporunu güncelle. İçinde:
- ADIM 0 ölçümü (wrangler var mı, sürüm, salt-okuma sorgusu geçti mi, `talepler` canlıda var mı)
- `--kendini-test` ham çıktısı + rc · mutant tablosu · `IZOLE` / `OLCULEMEDI` sayıları
- `ci-kapsam-test.py` rc
- Canlıya uygulama **yordamı** (hangi komut, hangi sırayla) — **UYGULANMADI**, onay bekliyor
- Parti tavanı kararı ve gerekçesi
- Ölçemediğin her şey: `OLCULEMEDI` + sebep. **Sayı uydurma.**
