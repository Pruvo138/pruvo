# PAKET K174 — H2F çapası K170 ile ÖLDÜ, ÇAPA TAŞINACAK (beklenti çevrilmeyecek)

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Ağaç:** `kral/k166b-yayin-sinyali` (`a50337d7`)

## MİMAR HATASI — ÖNCE BU KAYDA GEÇSİN
K170'i merge etmeden önce koşturduğum kabul bataryasını **elle listeledim** ve
`tools/model-baslik-kolu-test.py` o listede YOKTU. Test, değiştirdiğim iki tabloyu
(`ROZET_DISI_CIFT` / `ROZET_CAPRAZ_IZINLI`) okuyan bir kapının kabul kolu; yani bataryaya
**girmesi gerekiyordu.** Doğru kural bu depoda zaten yazılı ve ben uygulamadım:
**kabul evreni elle sayılmaz, "bu tabloyu KİM OKUYOR" sorusundan TÜRETİLİR**
([[kapsam-evrenini-cagri-grafindan-turet]]). Sonuç: K170 main'e bloklamayan şeritte
duran bir kırmızıyla girdi. Yayın durmadı (deny'ler canlıda doğru: 3×404 / 3×200 / ürün 200),
ama K166 o adımı bloklayıcı şeride taşıyacağı için **şimdi kapatılması gerekiyor.**
⚠️ İşçinin raporundaki "K170-D'de bu test ölçüldü yeşildir diye geçirilmiş" cümlesi YANLIŞ —
öyle bir iddia hiç yazılmadı; test hiç koşulmadı. Kusur atlama değil, EKSİK EVREN.

---

## TEŞHİS

`tools/model-baslik-kolu-test.py:738-742`:
```python
_ak   = evren.model_anahtari("Alfa Romeo", "916")
_alfa = kova.get(("Alfa Romeo", _ak))
dogrula("H2F ALFA ROMEO|916 değişiklik SONRASI AÇILDI (H1)",
        bool(_alfa) and _alfa[1], ...)
```
H2F, H1 kolunun (çıplak sayı + `marka[]` üyeliği) bir kovayı **YAYINA** açtığını iddia eder ve
bunun için `Alfa Romeo|916`yı çapa seçmiştir. K170 o çifti **deny**'e aldı → kova artık
hiçbir koşulda yayına açılmaz → iddia kalıcı olarak yanlış.

## 🔴 HÜKÜM: BEKLENTİYİ `False`'A ÇEVİRMEK YASAK
En kolay "düzeltme" H2F'yi `alfa yayın=False` bekler hale getirmektir. **YAPILMAYACAK:** deny
zaten `False` üretir, dolayısıyla H1 kolunu ÖLDÜREN bir mutant da `False` verir ve iddia
yeşil kalır. Bu, çapayı ölü kola nişanlamaktır
([[mutasyon-capasi-olu-kola-nisanlanir]] · [[test-hatali-davranisi-kutsar]]).

## İCRA — ÇAPAYI TAŞI

1. **Aday çapa ARA ve ÖLÇ** (tahmin etme): şu üç koşulu BİRDEN sağlayan bir `(marka, jeton)`:
   - jeton **çıplak sayı** ve kova H1 kolundan (`marka[]` üyeliği) sahipleniyor,
   - çift `ROZET_DISI_CIFT`te **DEĞİL** (deny yok) ve `ROZET_CAPRAZ_IZINLI`de yargısı VAR,
   - kova bugün gerçekten **YAYINDA** (`_alfa[1]` karşılığı `True`).
   Bakılacak ilk adaylar `Mazda|5` ve `Renault|5` (ikisi de ROZET, çıplak sayı) — ama
   **ölçerek** seç; sağlamıyorlarsa evrenden başka aday türet ve hangilerini neden elediğini yaz.
2. H2F'yi o çapaya taşı; iddia metnini de güncelle (içinde `916` KALMASIN, yanıltır).
3. `Alfa Romeo|916` için AYRI ve YENİ bir iddia ekle — **H2H**: *"deny yazılan çift H1 kolundan
   SAHİPLENİLSE BİLE yayına açılmaz"* (`jeton_sahibi` 'alfaromeo' döner **VE** kova yayın=False).
   Bu, K170'in davranışını kilitler ve deny'i sessizce kaldıran bir mutantı yakalar.

## KABUL (hepsi ZORUNLU)

```
python3 tools/model-baslik-kolu-test.py            → rc=0, KALDI=0
python3 tools/model-baslik-kolu-test.py --mutasyon → N1..N5 + kontrol: hepsi beklenen renkte
python3 tools/model-uyelik-kapisi.py               → rc=0 (K170 yargısı bozulmadı)
```

🔴 **ÇAPA CANLILIK KANITI (bu paketin asıl kapanışı):** yeni H2F çapası GERÇEKTEN H1 kolunu
ölçüyor mu? Kanıtla: H1 kolunu öldüren mutantı (N1) koş ve **H2F'nin de kırmızı yandığını**
göster. Yanmıyorsa çapa yine ölüdür → başka çapa seç, "geçti" YAZMA.
Aynı şekilde H2H için: deny kolunu öldüren bir mutant (`ROZET_DISI_CIFT`ten
`("Alfa Romeo","916")` satırını sil) H2H'yi KIRMIZI yakmalı.

## SONRA — K166 hükmünü yenile
Bu düzeltme yeşile dönünce, K166-B'nin **5 terfi adımını** yeniden koş ve rc tablosunu bas
(1-4 zaten rc=0'dı; 5. bu paketle kapanmalı). Hepsi rc=0 ise hüküm: **MERGE EDİLEBİLİR**.
Bir tanesi bile rc≠0 ise **MERGE EDİLEMEZ** yaz ve DUR.

## SINIR
`tools/arama.py`'deki K170 yargısına DOKUNMA — çift deny'de KALACAK (canlıda doğrulandı:
`/marka/alfa-romeo/916/` 404, ürün adresi 200). Bu paket TESTİ onarır, hükmü değil.
`urunler.json` / gizli kaynak düzlemi DOKUNULMAZ.

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla; her komutun rc'si + ham çıktı.
Elediğin aday çapaları GEREKÇESİYLE yaz. Geçici dosya bırakma, `git status --short` ile kanıtla.
