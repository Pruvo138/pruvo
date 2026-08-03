# DEVİR KONTROL LİSTESİ — hesap rotasyonu (her 2-3 günde bir)

Yeni Claude hesabına geçerken **her mimar** bunu kendi evinde koşar. 5 dakika sürer.

## ⚠️ ÖNCE: NE DEĞİŞMİYOR (boşuna uğraşma)
Claude hesabı değişiyor, **başka hiçbir şey değişmiyor**:
- git / GitHub / dallar / commit'ler — etkilenmez
- Cloudflare, D1, R2, wrangler oturumu — etkilenmez
- `~/.claude/projects/.../memory/` (hafıza + posta kutusu) — **diskte, aynen kalır**
- `DEVAM.md`, `DEVAM-ARSIV.md`, `CLAUDE.md` — diskte, aynen kalır
- Notion, kayıtlı sırlar, `.r2-credentials.json` — etkilenmez

**Kaybolan tek şey:** oturumun kendi bağlamı ve **o an koşan arka plan işçileri**.
Devir hazırlığının tamamı bu iki şeye karşıdır.

---

## 6 ADIM

### 1. Arka plan işçilerini KAPAT
Koşan her işçi rotasyonda ölür ve **işi yarım kalır** — dalında commit'siz kod bırakabilir.
- Biten var mı diye bekle; bitmeyecekse `TaskStop` ile **açıkça** kapat.
- Kapattığın işçinin worktree'sinde commit'siz iş kaldıysa **2. adım onu yakalar.**
- Bir işçi merge'in ortasındaysa **bitmesini bekle** — yarım merge en kötüsüdür.

### 2. Commit'siz iş bırakma — hiçbir yerde
Ana ağaç **ve her worktree** için:
```
git -C <yol> status --porcelain --untracked-files=all
```
Boş değilse **commit et**. Atomik yaz, `add` ayrı çağrı yapma:
```
git -C <yol> commit -F <mesaj-dosyasi> -- <yollar>
```
🔴 **`git stash` / `git checkout --` / `git restore` YASAK.** Bu depoda commit'lenmemiş bir dosya
tam bu yolla kayboldu, `fsck` ile bile kurtarılamadı. Şüphedeysen commit et, silme.

### 3. Dalları push et
Yerel dal diskte kalır ama push edilmiş dal **kaybolmaz**. Yarım işi de push et — yeni oturum
kaldığı yerden alır.
```
git -C <yol> push -u origin <dal>
```

### 4. `DEVAM.md`'ye kapanış bloğu
Yeni oturumun ilk okuyacağı yer burası. **Yalnız ölçülen sayı yaz**, tahmin yazma;
ölçemediğine "ÖLÇÜLEMEDİ + sebep" yaz. Dört başlık:
- **CANLIYA GİTTİ:** SHA + ölçülen sonuç
- **KOŞUYOR:** hangi dal, hangi aşamada, nerede duruyor
- **BEKLİYOR:** kim neyle bloke
- **BENDE:** sıradaki açık kalemler

### 5. Posta kutusuna tek blok
`memory/mimar-posta-kutusu.md` en üste: **hangi kalem kimde.** Rotasyondan sonra
"bu iş kimde?" sorusu sorulmasın. Kutu 300 satırı aşmasın — aşıyorsa en eski **kapalı**
blokları `mimar-posta-kutusu-arsiv.md`'ye taşı (açık kalem taşınmaz).

### 6. Kapanış ölçümü — üçü de temiz olmalı
```
git -C <yol> status --short
git -C <yol> worktree list
python3 <yol>/tools/durum.py
```
- `status --short` **boş**
- Kendi worktree'lerin **≤2** (başkalarınınkine dokunma)
- Biten dalların worktree'si silinmiş

---

## YENİ HESAPTA İLK OTURUM
1. `CLAUDE.md`'yi oku (kimlik klasörden gelir).
2. `memory/MEMORY.md` + `memory/mimar-posta-kutusu.md` oku.
3. `DEVAM.md`'nin **KOŞUYOR** ve **BENDE** başlıklarını oku.
4. `git status` + `worktree list` + `durum.py` ile **gerçek durumu ölç** — DEVAM.md bayat olabilir.
5. Yarım kalmış dal varsa: önce ölç (`merge-base --is-ancestor` ile içeriği main'de mi),
   sonra devam et.

## ASLA
Devir sırasında merge/deploy başlatma · commit'siz iş bırakma · koşan işçiyi kapatmadan çıkma ·
"nasılsa diskte" diye push'suz dal bırakma · başka mimarın worktree'sine dokunma.
