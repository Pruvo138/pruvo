# PAKET — Durum panosu (`tools/durum.py`)

**Kat:** MÜHENDİS (Opus, yüksek efor) — kalıcı kaynak kod.
**Mimar:** KraL. **Talep eden:** Okan (17 Tem).
**Dal:** `claude/durum-panosu` (worktree). **Rapor:** `RAPOR-MIMARA.md` + `DEVAM.md`, mesaj YOK.

---

## İHTİYAÇ (Okan'ın sözüyle)

> "Hangi iş bitmiş hangisi devam ediyor bunları görebileceğim bir yöntem."

Uygulamada `/tasks` ve `/workflows` var ama **oturuma özel** — başka oturumun işini
göstermiyor (17 Tem'de ölçüldü: bu oturumda `TaskList` → "No tasks found", oysa başka
oturumda 3 görev koşmuş). Oturumlar-arası **tek pano yok**. Bu araç o boşluğu kapatır.

**KAPSAM = SADECE GÖRÜNÜRLÜK.** İş başlatma/dürtme bu aracın işi DEĞİL (o Agent/spawn_task
= mimarın işi). Araç **SALT-OKUNUR**: repoya, dala, DEVAM.md'ye, hiçbir şeye YAZMAZ.

## ÇIKTI (tek komut: `python3 tools/durum.py`)

Terminalde okunur, Türkçe, kısa. Bölümler:

1. **AKTİF WORKTREE'LER** — `git worktree list`: yol, dal, son commit zamanı,
   `RAPOR-MIMARA.md` var mı (varsa mtime + ilk başlık satırı).
2. **DALLAR** — her `claude/*` + diğer yerel dal: son commit tarihi/özeti, main'e göre
   kaç commit ileride, **içeriği main'e girmiş mi**.
3. **ARTIK DALLAR** — worktree'si olmayan + içeriği main'de olan dallar = temizlenebilir.
   **SİLME — sadece listele** ve silme komutunu çıktıya yaz (kararı Okan/mimar verir).
4. **DEVAM.md** — son güncelleme zamanı + açık başlıklar. **70 KB, İÇERİĞİ DÖKME** —
   sadece başlık düzeyinde özet.

## ZORUNLU KURALLAR (ihlali = kabul edilmez)

- **"Merged" görünümü TUZAK** ([[worktree-yol-hatasi]] hafızası). `git branch --merged`
  YETMEZ: squash-merge/cherry-pick/rebase edilmiş dalın ucu main'in atası değildir, araç
  onu "bitmemiş" sanar. **Patch-id bazlı kontrol kullan** (`git cherry main <dal>` ya da
  eşdeğeri) ve iki durumu ayır: *ucu main'de* vs *içeriği main'de*. Bu paketin ASIL
  teknik riski budur.
- **Repo PUBLIC** — `tools/durum.py` yayına girer. Kodda/yorumda tedarikçi adı, üyelik adı,
  kimlik, IBAN, telefon, sır YOK. Çıktı yerelde kalır ama **araç hiçbir sır dosyasını
  (`.r2-credentials.json`, `.urun-kaynaklari.json`) OKUMAZ/BASMAZ**.
- **SALT-OKUNUR** — `git fetch/pull/push/checkout/branch -d`, dosya yazma YOK. Sadece
  okuyan git komutları.
- **KOMUT STİLİ** (CLAUDE.md) — betiğin kendisi Python, serbest. Ama Bash'te `$VAR`, `cd`,
  `>` kullanma.
- Harici bağımlılık YOK — saf Python 3 stdlib + `git` çağrıları.
- Repo yolu sabit yazılmasın; betik kendi konumundan repo kökünü bulsun.

## ARAŞTIRMA KALEMİ (bulamazsan YAPMA, nedenini rapora yaz)

Claude Code oturumlarının **canlı/bitmiş görev durumu diskte okunabiliyor mu?**
(`~/.claude/projects/-Users-okan-dev-pruvo/` altındaki JSONL/oturum dosyaları). Okunabiliyorsa
5. bölüm olarak "OTURUMLAR: hangisi koşuyor, son aktivite" ekle. **Belgelenmemiş iç formata
kırılgan bağımlılık kurma** — format şüpheliyse bölümü ekleme, "şu yüzden eklenmedi" diye yaz.
Tahminle doldurma ("BU PROJE ÖLÇÜMLE YÜRÜR, TAHMİNLE DEĞİL").

## KABUL — `python3 tools/durum-test.py` YEŞİL (çalıştırılabilir test, zorunlu)

Testi de sen yaz. **Test GEÇİCİ repo kurar** (`tempfile` + `git init`) — gerçek repoda dal
açma/silme YOK (guard katmanı + eşzamanlı oturumlar bozulur). En az şunları kanıtla:

1. **Ucu main'de olan dal** → "içeriği main'de" sınıfına düşer.
2. **Squash-merge edilmiş dal** (uç main'in atası DEĞİL, içerik main'de) → yine
   "içeriği main'de". `git branch --merged` bunu kaçırır; testin bunu **yakaladığını göster**.
3. **Gerçekten bitmemiş dal** (main'de olmayan commit'i var) → "devam ediyor".
4. Aktif worktree'si olan dal "artık dal" listesine DÜŞMEZ.
5. `durum.py` gerçek repoda **exit 0** ve repo durumunu **değiştirmiyor**
   (`git status --porcelain` çalıştırma öncesi/sonrası aynı).

**Testi önce KIRMIZI gör** (CLAUDE.md: "Bir testin ilk denemede tam geçmesi şüphelidir:
bozup kırmızı yandığını gör"). Özellikle 2. maddeyi: `--merged` ile yaz → kırmızı yanmalı →
patch-id'ye geçir → yeşil. Bunu rapora yaz.

## BİTİRİŞ

1. `tools/durum.py` + `tools/durum-test.py` dala commit.
2. `RAPOR-MIMARA.md`: ne yapıldı, 2. madde kırmızı→yeşil kanıtı, araştırma kalemi sonucu,
   bilinen sınırlar.
3. `DEVAM.md`'ye kısa satır (**yazmadan önce dosyayı YENİDEN OKU** — bağlamındaki kopya bayat
   olabilir, başka oturum yazmış olabilir).
4. Mesaj atma. Mimar dalı ve raporu kendisi okur.

**Yargı/onay sorusu çıkarsa Okan'a değil MİMARA** — rapora yaz, iş DURMASIN.
