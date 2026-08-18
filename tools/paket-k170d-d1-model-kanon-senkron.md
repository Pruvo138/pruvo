# PAKET K170-D — K170 sonrası D1 `model_kanon` türetilmiş kolonu BAYAT, senkron gerekiyor

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Ağaç:** `/Users/okan/dev/pruvo` (ANA, main `69e6b83a`)

## DURUM (mimar ölçtü, merge SONRASI `d1-sync.py --durum`)

K170 main'e girdi (`69e6b83a`). Merge sonrası zorunlu D1 teyidi **DRIFT** buldu:

```
turetilmis kolon ekseni: konfigur=GUNCEL · taban_fiyat=GUNCEL · marka_kanon=GUNCEL
                         model_kanon=BAYAT(6) · marka_arama=GUNCEL
icerik ekseni (urun_hash): hash UYUSMAZ=0 · EKSIK=0 · FAZLA=0   ✅
SAYI ekseni: D1 == urunler.json == 29057                        ✅
SEQ / SEMA ekseni                                                ✅
```

🔴 **Sebep K170'in KENDİSİ ve bu beklenen bir sonuç, arıza değil:** `("Alfa Romeo","916")`
deny'e alınınca `916` artık Alfa tarafında bir MODEL jetonu değil; `model_kanon` türetimi
değişti. Bayat 6 satırın **5'i** `alfa-romeo-916-*` ürünleri (6.'sı `--durum` çıktısında
kesildi, işçi TAMAMINI listeleyecek). Beklenen yeni değerler:

```
alfa-romeo-916-gtv-spider-tavan-anahtari-kor-kapagi -> ["GTV","Spider"]
alfa-romeo-916-b-diregi-fitil-tutucusu              -> ["916 Spider","Spider"]
alfa-romeo-916-gtv-tweeter-destegi                  -> []
alfa-romeo-916-vites-baglanti-burcu                 -> ["916 Spider","Spider"]
alfa-romeo-916-silecek-ray-klipsi                   -> []
```

🔴 **NEDEN ACELE:** bu kolon `urun_hash` KAPSAMI DIŞINDADIR — SAYI, ŞEMA ve İÇERİK
eksenlerinin ÜÇÜ DE bu hale KÖRDÜR. Sonuç: **site bulur, Ege BULAMAZ**
([[ege-d1-bagimliligi]]). Müşteri, ürün varken kaybedilir ve hiçbir alarm çalmaz.

## İCRA

1. **ÖNCE tam listeyi bas** (6/6 satır, `--durum` çıktısı kesmişti) — id + D1'deki CANLI değer
   + urunler.json'dan TÜRETİLEN değer, yan yana. Ham çıktı rapora.
2. Kanonik senkronu koş: `python3 tools/d1-sync.py` (yerelde wrangler oturumu, token gerekmez).
   🔴 **Kendi yazıcını KURMA**, D1'e elle SQL yazma. Araç bu işi yapmıyorsa DUR ve mimara yaz.
3. **SONRA yeniden ölç:** `python3 tools/d1-sync.py --durum` → beş eksenin BEŞİ de yeşil,
   `model_kanon=GUNCEL`.
4. Doğrulayıcı kol: `python3 tools/model-kanon-d1-test.py` (aracın kendi tavsiyesi) rc=0.

## SINIR (ihlali merge'i geri aldırır)
- `urunler.json` ve gizli kaynak kayıt düzlemi **DOKUNULMAZ** (`git status --short` ile kanıtla).
- Ana ağaçta **commit ATMA, push ETME** — bu tur yalnız CANLI D1'i yerel gerçeğe hizalar.
- Başka bir eksende drift görürsen ONARMA, RAPORLA (kapsam K170-D'dir).

## KABUL
`--durum` çıktısının ÖNCESİ ve SONRASI **birebir** rapora; "senkron oldu" iddiası ikinci
ölçüm olmadan YAZILMAZ ([[silme-sayaci-diskten-dogrulanmali]]). `BAYAT(6)` → `GUNCEL`
geçişi iki çıktıda da görünmeli. Ölçemediğin ekseni `OLCULEMEDI` + sebep yaz.

## RAPOR
Ana ağaçta rapor dosyası BIRAKMA (izlenen ağaç) — özeti doğrudan tur çıktısına yaz:
her komutun rc'si + `--durum` öncesi/sonrası ham blokları. İş bitince geçici dosya bırakma.
