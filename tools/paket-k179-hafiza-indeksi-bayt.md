# PAKET K179 — hafıza indeksinin BAYTI düşecek (lossless, arşiv aynı kadar büyüyecek)

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Emir:** Okan (15:00, madde 2)

## SORUN (Okan ölçtü)
`~/.claude/projects/-Users-okan-dev-pruvo/memory/MEMORY.md` **39 satır / 19.105 B**.
Satır tavanı 40 ve altında, ama **bayt üç koşumda da büyüdü**: 17.454 → 18.230 → **19.105**.
Sebep açık: satırları BİRLEŞTİREREK 40'ın altında kalmak, bayt eksenini GİZLİYOR. Bu dosya
HER OTURUM bağlama yükleniyor, yani baytı doğrudan maliyet.

## MİMAR HÜKMÜ — NE TAŞINACAK (bu seçim MİMARINDIR, işçi DEĞİŞTİRMEZ)

Hedef dosya: **`memory/MEMORY-ARSIV.md`** (yoksa oluştur). Taşınacak olan **yalnız İNDEKS
SATIRLARI**; 🔴 **hafıza DOSYALARININ KENDİSİ SİLİNMEZ, TAŞINMAZ, DEĞİŞTİRİLMEZ.**

**"Kota, devir ve ajan orkestrasyonu" bölümünden ARŞİVE taşınacak girdiler** (emekli motorun
operasyonel ayrıntısı — kararlar kalıyor, trivia gidiyor):
`codex-emekli-hedefi-yetkinlik-kapisi` · `codex-kredi-orkestrasyon` ·
`kota-denetim-onerileri-20tem` · `hoca-artist-kota-delikleri-20tem` ·
`kral-macit-urun-jenerator-devir-20tem` · `kota-codex-yonlendirme` ·
`codex-canli-cikti-baglami-doldurur` · `codex-muhendis-pilotu` · `codex-panel-kimlik-once` ·
`codex-sandbox-git-yazamaz` · `codex-ana-agac-commit-kapisi-catismasi` · `gemini-kota-fiyat` ·
`ds-zam-penceresi` · `tasinma-iki-ayri-anlam`

**KALACAKLAR (dokunma, gerekçeleri var):** `codex-emekli-karari` ve `deepseek-emekli-karari`
(yürürlükteki KARAR) · `codex-tam-yol` (CLAUDE.md'de codex istisnası **20 Ağu'ya kadar AÇIK**) ·
`kimi-kota-amiral-gemisi-yakar` · `prob-gercek-isi-taklit-etmeli` · `isci-tarayici-kimi-playwright` ·
`isci-tur-tavani-1500sn` · `sabit-kota-vs-token-tarifesi` · `isci-raporsuz-duser-bekleyecegim-deyip` ·
`ucuz-isci-yesil-tablo-uydurur` · `silme-sayaci-diskten-dogrulanmali` · `kota-bitince-devret` ·
`is-bolumu-codex-claude` · `coklu-ajan-calismasi` · `motor-saglayici-resmi-adresler` ·
`models-200-uretim-yetkisi-degil` · `paylasilan-profilde-eszamanli-oturum-olcumu-kirletir`.

`MEMORY.md`'de o bölümün SONUNA tek bir işaretçi bırakılacak:
`Emekli motorların operasyonel ayrıntısı arşivde: [Kota arşivi](MEMORY-ARSIV.md)`

## KABUL — LOSSLESS KANITI (Okan kuralı 11; sayı ZORUNLU)
```
ONCE :  MEMORY.md = <bayt> / <satir>      MEMORY-ARSIV.md = <bayt> (yoksa 0)
SONRA:  MEMORY.md = <bayt> / <satir>      MEMORY-ARSIV.md = <bayt>
```
🔴 **Kabul çıtası:** `MEMORY.md` DÜŞEN baytı ile `MEMORY-ARSIV.md` ARTAN baytı **eşleşmeli**
(başlık/işaretçi satırlarının farkı kadar sapma normal — sapmayı SAYIYLA yaz ve gerekçelendir;
gerekçesiz fark **KAYIP**tır). Satır sayısı 40'ın altında kalmalı.
🔴 **İÇERİK KORUNDU KANITI:** taşınan 14 girdinin **hepsi** arşivde, aynı ad ve aynı bağlantı
metniyle bulunmalı — 14/14 diye SAY ve bas. Eksik varsa `KAYIP=<n>` yaz, iş BİTMEMİŞTİR.
🔴 **Bağlantı bütünlüğü:** taşınan her satırın işaret ettiği `.md` dosyası diskte HÂLÂ VAR mı
— 14/14 `ls` ile doğrula. Bir tanesi yoksa DUR.

## SINIR
- `memory/` altındaki **hiçbir `.md` içerik dosyası** açılıp değiştirilmeyecek, silinmeyecek.
- `MEMORY.md`'nin diğer bölümlerine (rol/iletişim/kapılar/test/git/…) DOKUNMA.
- Repo dosyalarına DOKUNMA; bu iş repo dışıdır, commit/push YOK.

## RAPOR
Tur çıktısına doğrudan yaz (ayrı rapor dosyası AÇMA): ÖNCE/SONRA bayt-satır tablosu ·
14/14 içerik sayımı · 14/14 bağlantı bütünlüğü · sapma varsa gerekçesi.
Geçici dosya bırakma.
