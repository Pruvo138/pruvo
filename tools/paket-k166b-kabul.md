# PAKET K166-B — K166'nın geri inişi + K170'in CANLI doğrulaması (iki iş, tek tur)

**Mimar:** KraL · **Tarih:** 18 Ağu 2026
**Ağaç:** `/Users/okan/dev/pruvo/.claude/worktrees/k166b-yayin-sinyali` · **Commit:** `a50337d7`

---

## İŞ 1 — K170'in CANLI doğrulaması (ÖNCE bunu koş, merge'den bağımsız)

K170 main'de (`69e6b83a`) ve `deploy`+`yayin` **success** aldı. Ama CI'daki yeşil
canlı kanıt DEĞİLDİR. Ölç — 🔴 **cache-bust'SIZ, kanonik adresten** (`?cb=` DAİMA
origin'i gösterir ve YANILTIR):

| adres | beklenen |
|---|---|
| `https://pruvo3d.com/` | 200 |
| `https://pruvo3d.com/marka/vespa/px/` | **200** (ALLOW — doğdu) |
| `https://pruvo3d.com/marka/citroen/c1/` | **200** (ALLOW) |
| `https://pruvo3d.com/marka/ducati/916/` | **200** (ALLOW) |
| `https://pruvo3d.com/marka/piaggio/px/` | **404** (DENY — kapandı) |
| `https://pruvo3d.com/marka/peugeot/c1/` | **404** (DENY) |
| `https://pruvo3d.com/marka/alfa-romeo/916/` | **404** (DENY) |

Her satır için HTTP kodunu BAS. 🔴 Bir deny adresi hâlâ 200 dönüyorsa bu **edge
bayatlığı da olabilir, gerçek başarısızlık da** — ikisini ayır: `age`/`cf-cache-status`
başlıklarını da bas, hüküm verme, RAPORLA.
🔴 Bir allow adresi 404 dönüyorsa **DUR ve hemen mimara yaz** — K170 ürün gizlemiş olur.

Ayrıca ürün kaybolmadığını canlıda teyit et: yukarıdaki deny kovalarından bir ürünün
kanonik ürün adresi (`/urun/<id>/`) **200** dönmeli. Kullanılacak id (K170 raporundan):
`alfa-romeo-916-gtv-tweeter-destegi`.

---

## İŞ 2 — K166'nın kabulü (dalın kendi worktree'sinde)

```
python3 tools/is-akisi-kapisi.py
python3 tools/is-akisi-kapisi.py --kendini-test
python3 tools/ci-kapsam-test.py
python3 tools/kapi-envanteri.py
```

Beklenen: ilk üçü **rc=0**. `kapi-envanteri.py` K141 nedeniyle kırmızıdır — main
ucunda da koş, iki rc'yi yan yana bas ([[anahat-referans-tautolojisi]]).

### KAYIP YOK invaryantı (K166'nın asıl riski — taşıma sırasında adım düşmesi)
`deploy.yml` + `nobet.yml` toplamında ölç, ÖNCE (main) ve SONRA (dal) yan yana:
- toplam `- name:` adım sayısı → **değişmemeli**
- `python3 tools/` geçen komut satırı sayısı → **değişmemeli**
- `continue-on-error: true` sayısı → **artmamalı** (susturma yasak)
- `deploy: needs` listesi → **AYNEN** korunmalı, eleman DÜŞÜRÜLMEMELİ

### 🔴 YENİ ZORUNLU EKSEN — K166'yı ilk turda yaktıran şey buydu
İlk turda kimse şunu sormadı: **"bloklamayan şeritten BLOKLAYAN şeride geçen adım var mı?"**
Toplamlar korunduğu için terfi görünmez kaldı ve yayın kapandı.
Bu turda: `deploy.yml`'de **yeni** bloklayıcı işlere (`serit-a2`/`serit-a3`/`serit-a4`)
giren HER adımı **tek tek listele**, ve her biri için o komutu KOŞ, rc'sini yaz.
Bilinen dört aday: `konfigur-bundle-kapisi` · `kanca-kablosu-davranis` ·
`model-uyelik-kapisi` · `model-baslik-kolu`. Liste bu dörtle SINIRLI DEĞİL — iş
akışından TÜRET, ezberden yazma.
🔴 **Bu listede rc≠0 olan TEK bir adım varsa: MERGE EDİLEMEZ yaz, sebebini bas, DUR.**
K170 `model-uyelik-kapisi`yi yeşile çevirdi; diğer üçü ÖLÇÜLMEDİ, varsayma.

---

## SINIR
- Kaynak kodu ONARMA. Kırmızı bulursan raporla, düzeltme (kapsam iş akışı taşımasıdır).
- `urunler.json` / gizli kaynak düzlemi DOKUNULMAZ.
- Merge ETME, main'e push ETME — merge hükmü mimarındır.

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla. Her komutun rc'si + ham çıktısının son
15 satırı; her tablo satırının ham çıktıda karşılığı olacak. Ölçemediğin ekseni
`OLCULEMEDI` + sebep yaz, "geçti" YAZMA. İş bitince geçici dosya bırakma —
ürettiğin her dosyayı SEN sil, `git status --short` ile kanıtla.
