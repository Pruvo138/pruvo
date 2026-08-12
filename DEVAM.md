# DEVAM (KraL) — 8 Agu 2026

## 13 Agu 2026 — GOC: ISCI KATI M3/DEEPSEEK'E TASINDI (KraL)

**Okan karari:** 3 x 20x hesap -> 1. Hedef %66, tasarim %80'e gore. **Once olctum, sonra
tasidim.** 7 gunluk Claude yuku **32,26 milyar**; **%78,3'u ALT-AJAN**, %21,7 ana oturum.
Ev: **MaCiT %51,3 · KraL %35,1** · ArTisT %6,9 · KaaN %3,7 · HocA %1,8 · BaBa %0,9.
Model **opus %91** (KraL evinde). Nobetler kotanin yalniz **%0,32**'si — cron gocunun
kota etkisi ihmal edilebilir, degeri altyapiyi kurmasiydi.
🔴 Iki hipotezim CURUTULDU: yuk ana oturumda DEGIL; "Codex'e veriyorum temizim" de yanlis —
**saatlik nobetlerim 527 alt-ajan aciyordu** (KraL yukunun %26,6'si).

**Kurulan altyapi** (hepsi `~/.claude/cron/`): `isci.sh <motor> <ev> <spec> [etiket]` —
motorlar `minimax-m3` (1M baglam, olcum 9sn) · `deepseek-flash` (11sn) · `deepseek-pro`
(31sn, akil yurutme) · `claude`. Ev+motor basina KALICI izole profil, OAuth temizligi,
**geri donus kolu** (anahtar yok/bossa Claude'a duser, sessizce OLMEZ), `MOTOR=`+`sure=`
log. Eski `m3-isci.sh` adi yonlendirme olarak KORUNDU (MaCiT'in CLAUDE.md'sinde yazili).
Isci baglam dosyalari `isci-baglam/ORTAK.md`+`<motor>.md` prompt'a eklenir; isci `ONERI=`
yazarsa `isci-onerileri.md` defterine duser (defter KURAL KAYNAGI DEGIL — mimar olcup isler).
🔴 Olculdu: isci ev CLAUDE.md'sini GORUYOR ve **proje hook'lari ISLIYOR** (kapilar isci
uzerinde de gecerli); skill'leri ve hafizayi GORMUYOR.

**Tasinan kat:** olcum/teshis (%38,8) + mekanik (%18,9) = **%57,7**. **CLAUDE'DA KALAN
(%12,3):** kapi/nobetci/olcum KODU · odeme-fiyat · secret · gizlilik · sema ·
lisans/satilabilirlik · merge/deploy hukmu. Gerekce: 12 Agu'da yayini 8,5 saat kapatan
alti kirmizinin HEPSI bu siniftaydi ve hepsi `rc=0` verirken YANLIS SEYI olcuyordu.
Kural yazildi: `AGENTS.md` (KOMUTA ZINCIRI) · `~/.claude/cron/ci-nobeti-gorev.md` §2.9 ·
MaCiT'in `CLAUDE.md`'si.

**KOTA OLCUM NOBETI KURULDU** — `kota-olcum.py`, gunluk `41 6 * * *`, **Claude cagrisi 0**
(kendi olctugu kotayi yakmaz). Rapor `kota-raporu.md`, trend `kota-gecmis.tsv` (silinmez).
Alarm: E1 toplam bir onceki olcume gore +%25 · E2 alt-ajan payi >%50 -> kutuya TEK satir
(alarm yoksa sessiz). Ilk kosum **E2 TETIKLENDI (%78,04)** — DOGRU: goc henuz kagit uzerinde.
🔴 **GOCUN KABUL TESTI BU:** alt-ajan payi onumuzdeki gunlerde %78'den DUSMELI. Dusmezse
tasima gerceklesmemistir. Motor secimi izlenimle DEGIL `isci.log`'daki `MOTOR=`/`sure=` +
kapi rc'siyle revize edilir (kalite = kapi rc'si, hiz = sure).

**SIRADAKI TEK IS:** ArTisT'in isci katini gecir (%6,9), sonra KaaN/HocA/BaBa; ardindan
BaBa'nin kalici-duzen kanit cevabi (3-serit -> korumali main -> merge kuyrugu).

## 13 Agu 2026 — YAYIN ZINCIRI KAPANDI (KraL)

**Deploy YESIL:** kosum `31632478625` success, headSha `07e01284` (SHA eslesmesiyle
dogrulandi, "son kosum yesildi" degil). Yayin gun boyu kapaliydi; alti kirmizi sirayla
olculup kapandi:
- **Model kanon D1** — uretim DOGRU, kirmizi yanan BAYAT AYNA. (d) jeton sahipligi +
  gurultu sinifi kollari aynaya tasindi; B7 sapmasi **39 -> 0**, mutasyon **12/12**.
- **FAZ3 bayrak** — iddia veri-bagimliydi ve uyelik ekseni KORDU (mutant yakalanmiyordu).
  Iddia sayfanin kanonik `aramaPlaniEsler` yuklemine baglandi, batarya **3/3**.
- **Ic rapor kaydi** — dalda izlenen ic rapor kaydi izlemeden cikarildi.
- **build cokmesi** — 30 kayitta `fiyat` SAYI (`AttributeError: 'int' ... strip`).
  String'e cevrildi (deger degismedi) + `katalog-alan-kapisi.py`'ye TIP ekseni kuruldu
  (bos fiyat parametrik seri icin gecerli kalir, 23 kayit olculdu).
- **Marka invaryant** — IKIZ TANIM: filtre ham marka esitligi, sayfa+arama kanonik
  uyelik. Yuklem kanonik kaynaktan turetildi; kayip **7 -> 0**, taban **4 -> 0**
  (Volvo 109 dahil borc kapandi).
- **Cip indeks** — ayni sinifin AYNASI bayat kaldi (uretim kanonige gecmisti).
  Ayna uretim kaynagindan turetildi, **123/123**, mutant kirmizi.

**🔴 CI KAPSAM KAPISI YANLIS-POZITIFI KAPANDI (gunun en pahali sinifi).** Kapi push'un
ICERIGINI degil CALISMA AGACINI yarguluyordu: `git add` edilmemis YABANCI bir dosya
BASKASININ push'unu blokluyordu. Bugun **4 kez** oldu, ucu MaCiT'in urun partilerini +
KaaN'in commit'ini durdurdu. Kapsam artik pre-push'un verdigi ref/SHA araligindan
turuyor; aralik olculemezse ESKI KATI davranis (fail-closed). Kati kol mutasyonla
korundu, muafiyet listesine satir EKLENMEDI.

**Ayrica:** `duzelt.py` `tavsiyeFilament` alanini kabul ediyor (tip dogrulamali, 185
iddia) -> KaaN'in ASA tavsiyesi canliya indi (`a3d5cae1`). Kusurlu `--yeni-id` calismasi
(hal kapisi eski id ile cagriliyor + gizli kayitta hedef id kontrolu eksik) main'e
ALINMADI, yamasi arsivde. Worktree **4 -> 1** (bundle verify rc=0, 103+102 ref; dallar
SILINMEDI). K20 `son-zorunlu` kanit sha `cb35de6f` ile KAPALI.

**K82 M3 PILOTU KURULDU:** 4 cron nobeti MiniMax M3'e gecti (`MOTOR=minimax-m3`,
tur testi rc=0/18sn, sizinti 0). Kok neden Claude Code'un OAuth/keychain kimliginin
MiniMax anahtarini EZMESIYDI; cozum izole `CLAUDE_CONFIG_DIR` profili (kalici dizin,
700) + o cagrida OAuth jetonunun temizlenmesi. `--bare` SECILMEDI (nobetlerin arac
kabiliyetini kaybettirirdi). Geri donus kolu var: anahtar yok/bossa nobet Claude'a duser.

**SIRADAKI TEK IS:** BaBa'nin sirasindan ③ — K81 yayin kabulu (Codex iscisinden gelince
olc), sonra kalici-duzen kanit cevabi (3-serit -> korumali main -> merge kuyrugu).

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
