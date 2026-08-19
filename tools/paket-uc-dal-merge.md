# PAKET — üç hazır dalı main'e alma (N1 · N2 · K184)

> Mimar (KraL) hazırladı, 20 Ağu 2026. **İcra chip'te, ölçüm işçide.**
> Prosedürün tek kaynağı: **skill: merge-kapisi** — bu paket onun yerine geçmez, girdisidir.

## 0. Mimarın ana oturumda ÖLÇTÜĞÜ taban (git düzlemi — tekrar ölçmene gerek yok, ama çeliştiğini görürsen DUR)

- `main` = `origin/main` = **75395a0d** (senkron), ana ağaç **porcelain temiz**, worktree **1** (yalnız ana checkout).
- Üç dalın hiçbirinin dosyası main'de YOK (`ls-tree` boş) → mükerrer merge riski yok.
- Çakışma ön-testi (`merge-tree --write-tree --name-only main <dal>`) üçünde de **yalnız ağaç OID** → çakışma YOK.
- D1 beş eksen **YEŞİL** (`d1-sync.py --durum`: SAYI 29573 · SEQ · ŞEMA · TÜRETİLMİŞ KOLON · İÇERİK; hash uyuşmaz 0 / eksik 0 / fazla 0).
- Yayın hattı 🟢 AKIYOR (rc 0), bekleyen 2 commit / 17 dk, eşiklerin altında.

| Dal | Uç | merge-base | Kapsam |
|---|---|---|---|
| `kral/n1-gozcu-kablolama` | `fd6b6d8d` | `df7425ea` | 2 dosya, +23/−3 (`DEVAM.md`, `tools/kancalar/pre-push`) |
| `kral/n2-kirleten-onarir` | `a87f1809` | `df7425ea` | 9 dosya, +3111/−12 (`nobet.yml`, `devir-kapisi.py`, `ev-sahip-kapisi.py`, `ev-serit-haritasi.tsv`, `mimar-kapi-kur.py`, `n2-kabul.py`, `parti-borc-kapisi.py`, `parti-kapisi.py`, `sahiplik-haritasi.tsv`) |
| `kral/k184-talep-sihirbazi` | `8719aad0` | 9 dosya, +2359/−104 (`nobet.yml`, `index.html`, `jenerator/test/kabul.py`, `talep-alanlari.js`, `build.py`, `is-akisi-kapisi.py`, `talep-sihirbazi-test.py`, `vitrin-siralama-test.js`, `yayin-topla.py`) |

🔴 Üçü de `.github/workflows/nobet.yml`'e ya da paylaşılan araçlara dokunuyor → **sıralı merge, her merge'den sonra ön-test TEKRAR**.

## 1. SIRA (bağlayıcı)

**N1 → N2 → K184.** Gerekçe: N1 en dar kapsam ve kablolaması zaten CANLI (repo dışı cron), N2 yalnız yeni dosya ekliyor, K184 `index.html` + `build.py` + `yayin-topla.py` ile **site yüzeyine** dokunan tek dal → en sona, canlı doğrulaması ayrı.

Her dal için, merge-kapisi §1–§7 sırayla. Kısayol YOK.

## 2. Her dal için ZORUNLU adımlar

1. `git -C /Users/okan/dev/pruvo fetch origin` + `status -sb` (yabancı ` M` varsa DOKUNMA, kutuda dosya adını ara).
2. Dalı **worktree'ye çıkar** — kapılar dalın kendi ağacında koşar, ana checkout'ta koşan kapı dalın yeni nöbetçisini GÖRMEZ:
   `git -C /Users/okan/dev/pruvo worktree add /Users/okan/dev/pruvo/.claude/worktrees/<kisa-ad> <dal>`
3. `python3 /Users/okan/.claude/skills/merge-kapisi/scripts/dal-olc.py <dal>` — bastığı kapı komutlarının **hepsini** koş.
4. Dalın kendi kabul bataryası (öz-rapora GÜVENME, sayıyı KENDİN gör):
   - N1: `gozcu-test` · `gozcu-mutasyon` · `nobet-kabul` · `nobet-tetik-test` (chip beyanı: 112/112 · 16/16 IDDIA=16 ISTASYON=0 · 45/45 · VAKA=38 DUSEN=0 KABLO=19/19 — **doğrula, kopyalama**)
   - N2: `python3 tools/n2-kabul.py`
   - K184: `python3 tools/talep-sihirbazi-test.py` (chip beyanı: batarya 42/42, kontrol 19/19 — VAKA 36 bu dalda onarıldı)
5. Yeni nöbetçi geldiği için **her üçünde**: `python3 tools/ci-kapsam-test.py` + `python3 tools/kapi-envanteri.py`.
6. K184 `index.html` + `build.py`'ye dokunuyor → **TAM parite, ana checkout'tan, güncel main üstünde**:
   `node tools/parite-test.js` ve `node tools/parite-ege.js` · ayrıca `python3 tools/yasal-sayfa-drift-kapisi.py`.
7. Merge + push (onay isteme, isimsiz Türkçe mesaj):
   `git -C /Users/okan/dev/pruvo merge <dal> -m "..."` → `git -C /Users/okan/dev/pruvo push origin main`
8. Merge SONRASI: `python3 tools/d1-sync.py --durum` (HER merge'de) · K184'ten sonra ayrıca canlı doğrulama —
   koşumun SHA'yı **İÇERDİĞİNİ** kanıtla (`gh run list --json headSha,...` + `git merge-base --is-ancestor <SHA> <kosum-headSha>`), sonra **cache-bust'SIZ** kanonik URL'den ölç.
9. Temizlik: worktree kaldır + dal sil — ama önce `python3 tools/durum.py` ile içeriğin main'de olduğunu sınıflandırt ("ucu main'de" ≠ içerik main'de).

## 3. KABUL (chip bunları SAYIYLA kapatır)

- `git log --oneline origin/main` üçünün de merge commit'ini/uçlarını içerir; `main == origin/main`.
- Üç dalın kabul bataryası **dalın kendi ağacında** koşuldu, exit kodları raporda.
- `ci-kapsam-test.py` + `kapi-envanteri.py` merge SONRASI main'de rc=0.
- `d1-sync.py --durum` beş eksen YEŞİL (merge öncesi tabanla aynı: 29573).
- K184 sonrası: SHA'yı içeren koşum `conclusion=success` **ve** cache-bust'sız canlı teyit.
- Worktree tavanı ≤ rol sınırı, zombi dal bırakılmadı.
- ÖLÇEMEDİĞİN her şey için "ÖLÇÜLEMEDİ + sebep" yaz — "yeşil görünüyor" YASAK.

## 4. DUR koşulları (merge ETME, mimara dön)

- `dal-olc.py` `KESIF EKSENI OLCULEMEDI` ya da `OLCULEMEDI: kapi ANA agacta kosulacakti` basarsa.
- Dalın bataryası kırmızıysa — "baseline" diye kabul ETME, suçluyu tarihle bul.
- Diff'te spec dışı dosya, `urunler.json` / `.urun-kaynaklari.json` teması, ya da sızıntı (tedarikçi/tasarımcı adı, üyelik, kova adı, `RAPOR-*`, telefon) görürsen.
- Parite bayat tabanda koşulduysa sonucu SAYMA — karar güncel main'deki ana checkout'tan.
