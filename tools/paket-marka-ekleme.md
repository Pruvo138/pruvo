# İŞ PAKETİ: Marka tarama + toplu ürün ekleme (MÜHENDİS talimatı)

Sen bu partinin MARABASISIN (varsayılan: Sonnet alt-ajanı — ürün yükleme maraba işidir;
CLAUDE.md KOMUTA ZİNCİRİ). Çağıran sana KAYNAK (Printables/Thingiverse/MakerWorld) ve MARKA
(ya da doğrudan ID listesi / satıcı URL'si) verdi. Repo: /Users/okan/dev/pruvo.
Uçtan uca sen koşarsın; mimara sadece rapor dönersin.
NOT (19 Tem kredi kapısı): ürün-bası Codex mini çağrıları varsayılan KAPALI. Sen Codex/model
ÇAĞIRMA ve `PRUVO_URUN_AI_IZNI` ayarlama. Araç kredi kapısında durursa partiyi yakmadan raporla;
yalnız Okan o parti için açık izin verirse AI yolu ayrı görev olarak açılır.
Teknik engel çıkarsa (script hatası, beklenmedik veri) onarmaya ÇALIŞMA — raporla; kod işi
Mühendis katının, zor onarım Usta katınındır (mimar yönlendirir).

## Aktif kaynaklar

### Printables
- Ara: `python3 tools/printables-ara.py "<MARKA>"`
- Ekle: `python3 tools/printables-ekle.py <id...>`

### Thingiverse
- Ara: `python3 tools/thing-ara.py "<MARKA>"`
- Ekle: `python3 tools/urun-ekle.py <id...>`

### MakerWorld
- Ara: `python3 tools/makerworld-ara.py "<MARKA>"`
- Ekle: `python3 tools/makerworld-ekle.py <design_id...>`

## Akış

1. ARA:
   - Çağıran doğrudan ID listesi verdiyse bu adımı atla.
   - Aday listesi üzerinde alakasızlık elemeyi uygula.

2. EKLE:
   - Kalan ID'leri tek komutta ver.
   - Araç STAGE eder, COMMIT ETMEZ.

3. OTOMATİK DENETİM:
   - `python3 tools/denetim-kapisi.py`

4. GÖZDEN GEÇİR ve DÜZELT:
   - Yalnız bu partide eklenen ürünlerde çalış.
   - HEAD'dekilere dokunma.

5. RAPOR:
   - `.thing-cache/parti-rapor.json` dosyasına işin bitiş çıktısını yaz.
   - Son mesaj tek satır özet olsun: `STAGED <N> | yargı <M>`.

6. KAPSAMA KAYDI:
   - `python3 tools/marka-kapsama.py kaydet --marka <MARKA> --platform <KAYNAK> --taranan <toplam_aday> --eklenen <staged> --elenen <elenen>`

## Yapma

- git commit / push YAPMA.
- `tools/duzelt.py` / guard / HEAD'deki ürünlere DOKUNMA.
- `.urun-kaynaklari.json`ı elle DÜZENLEME.
- Lisans kapısını gevşetme.
