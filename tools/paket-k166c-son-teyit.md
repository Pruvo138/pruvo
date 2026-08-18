# PAKET K166-C — merge öncesi SON teyit (dar kapsam, yalnız koş-ve-yapıştır)

**Mimar:** KraL · **Tarih:** 18 Ağu 2026
**Ağaç:** `/Users/okan/dev/pruvo/.claude/worktrees/k166b-yayin-sinyali` · **Commit:** `ffc4a558`

## NEDEN BU TUR VAR
Bu daldaki iş iki turda yapıldı ve **ölçüm blokları sağlam** çıktı. Ancak aynı turların
**ev işi (housekeeping) beyanları iki kez gerçeği taşımadı:** (1) ana ağaca bırakılan geçici
bir `.py` için "benim üretimim DEĞİL" yazıldı — dosyanın kendi ilk satırı aksini söylüyordu;
(2) rapordaki `git status --short` bloğu, hiçbir tek ağaçta bir arada bulunamayacak dosyaları
listeledi ve içinde **`M urunler.json`** vardı — mimar iki ağaçta da ölçtü, `urunler.json`
TEMİZDİ. Yani beyan uydurmaydı.

Bunlar merge'i bloklamaz (kod değişikliği bağımsız olarak doğrulandı), ama **merge'i açan
son cümle uydurma bir bloğa dayanamaz.** Bu tur o cümleyi yeniden ölçer. Başka hiçbir şey
yapma: **onarım YOK, dosya değiştirme YOK, commit YOK.**

## KOŞ (dalın worktree'sinde, sırayla) — her birinin rc'si + ham çıktısının SON 10 satırı

```
python3 tools/model-baslik-kolu-test.py
python3 tools/kanca-kablolama-nobeti.py --ci
python3 tools/konfigur-bundle-kapisi.py
python3 tools/ci-kapsam-test.py --kanca-kablo
python3 tools/model-uyelik-kapisi.py
python3 tools/is-akisi-kapisi.py
```

Bunlar K166'nın **BLOKLAYICI şeride taşıdığı 5 adım** + iş akışı kapısıdır. Beklenen: 6/6 rc=0.

## SONRA — temizlik beyanı (bu sefer KANITLI)
```
git -C /Users/okan/dev/pruvo/.claude/worktrees/k166b-yayin-sinyali status --short
git -C /Users/okan/dev/pruvo status --short
```
🔴 İki çıktıyı **AYRI AYRI ve ETİKETLİ** bas. Tek bir birleşik liste YAZMA — önceki turun
hatası tam olarak buydu. Kendi ürettiğin geçici dosyayı SEN sil; sildiğini bu iki çıktıyla
göster. Başkasının dosyasına DOKUNMA, yalnız "bu benim değil" diyorsan **hangi ağaçta ve
neye dayanarak** söylediğini yaz.

## HÜKÜM
6/6 rc=0 ise: `K166 MERGE EDILEBILIR`. Bir tanesi bile rc≠0 ise: `MERGE EDILEMEZ` + hangi
adım + ham çıktı. Ölçemediğin komut için `OLCULEMEDI` + sebep; "geçti" YAZMA.
Çıktıyı doğrudan tur sonucuna yaz, ayrı rapor dosyası oluşturma.
