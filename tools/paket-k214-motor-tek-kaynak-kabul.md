# SPEC — K214 KABUL KOŞUMU (motor kümesi TEK KAYNAK)

> 🔴 **AĞAÇ:** Bütün komutlar **bu worktree'de** koşar:
> `/Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215`
> Ana checkout (`/Users/okan/dev/pruvo`) **ÖLÇÜM AĞACI DEĞİLDİR** — orada dalın işi YOK.
> (Hafıza: `spec-mutlak-yol-yanlis-agaci-olcer`.)

> 🔴 **YAZMA YASAĞI:** Gerçek tek kaynağa (`tools/mimar_kimlik.py`), gerçek kurulu
> kapılara (`/Users/okan/dev/pruvo-*/.claude/mimar-icra-kapisi.py`) ve `~/.claude/cron/`
> altına **DOKUNMA**. D/E vakaları **KOPYA ağaçta** koşar, iş bitince kopya SİLİNİR
> (DİSK KURALI: makinede iz bırakma).

## Ölçülen kusur (bağlam, tekrar ölçme)
`tools/mimar-kapi-kur.py` işçi motor kümesini kendi gövdesine GÖMÜYORDU
(main'de `mimar-kapi-kur.py:1329` = `("minimax-m3","deepseek-pro","deepseek-flash","claude")`
— **`kimi` YOK, emekli deepseek VAR**) ve 13 Ağu'da beş kardeş eve o donmuş kopyayı kurdu.
Dal bunu `mimar_kimlik.motor_blogu_kaynagi()` türetimine bağlıyor.

---

## A — ÜRETİM ÖLÇÜMÜ (6 ev)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/motor-tek-kaynak-kapisi.py
```
YAZ: rc + çıktının TAMAMI. Her ev için satırı ADIYLA yaz (EV YOK / KAPSAM DIŞI de ADIYLA sayılır).

## B — ÖZ-NÖBETÇİ (mutant + hedef kol atfı)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/motor-tek-kaynak-kapisi.py --kendini-test
```
KABUL: rc=0. YAZ: mutant sayacı satırını birebir + her mutantın `KOL=` atfını.

## C — ÇÜRÜTME (tautoloji kontrolü)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/motor-tek-kaynak-kapisi.py --curutme
```
KABUL: rc=0. Bu adım "kırmızı geldi = kol ölçüldü" yanılgısını kapatır (K182).

---

## D/E — TEK KAYNAK EKLE/ÇIKAR → KAPI KENDİLİĞİNDEN İZLİYOR MU?
🔴 **KOPYA AĞAÇTA.** Önce kopyala:
`cp -R <worktree>/tools /tmp/k214-kopya/tools`

Ölçülen yüzey: `tools/mimar-icra-kapisi.py`'nin motor kabul kolu
(`if motor not in ISCI_MOTORLARI`) — bu dosya kümeyi `mimar_kimlik`'ten **import eder**.

- **D (EKLEME):** kopyadaki `mimar_kimlik.py` `ISCI_MOTORLARI`'na `zzz-sinama-motoru`
  ekle → kapıya `PRUVO_ISCI_KOSUMU=zzz-sinama-motoru` kimliğiyle bir çağrı ver.
  **BEKLENEN: kapı bu motoru KABUL eder** (kimlik ekseni `sarmalayici:zzz-sinama-motoru`).
  Ekleme ÖNCESİ aynı çağrının kimlik ekseni `None` (MİMAR) olduğunu da yaz — yoksa
  "kabul etti" tautolojidir.
- **E (ÇIKARMA):** kopyadaki `ISCI_MOTORLARI`'ndan `kimi`'yi çıkar → `kimi` çağrısı
  **REDDEDİLMELİ** (kimlik ekseni `None`'a düşer). Çıkarma öncesi AYNI çağrının
  kabul edildiğini de yaz (önce/sonra farkı).

YAZ: dört ölçümün (D-önce, D-sonra, E-önce, E-sonra) rc'si + hüküm satırı.

## F — MUTANT: TEK KAYNAĞI BOZ
Kopyadaki `mimar_kimlik.py`'de `ISCI_MOTORLARI`'nı boz (ör. boş tuple) →
`motor-tek-kaynak-kapisi.py` **KIRMIZI** gelmeli.
🔴 **KIRMIZININ SEBEBİ AYRICA KANITLANIR:** çıktıdaki `KOL=` jetonunu yaz ve bunun
hedef kol olduğunu göster. Sadece "rc=1 geldi" **KANIT DEĞİLDİR** (K182 / `rc-hukmu-kapi-imzasini-ezer`).
İş bitince `rm -rf /tmp/k214-kopya` ve SİLİNDİĞİNİ `ls` ile kanıtla.

---

## G — BEŞ EVDE `isci.sh kimi` ARTIK REDDEDİLİYOR MU?
Her ev için kurulu kapının `kimi` hükmünü ölç:
`/Users/okan/dev/pruvo-hasat` (MaCiT) · `/Users/okan/dev/pruvo-jenerator` (TeKiN/KaaN) ·
`/Users/okan/dev/pruvo-pazarlama` (ArTisT) · `/Users/okan/dev/pruvo-bot` (HocA) ·
`/Users/okan/dev/pruvo-advisor` (BaBa) · ayrıca kaynak ev `/Users/okan/dev/pruvo` (KraL).

🔴 **KİMLİK EKSENİ SÖKÜLMELİ VE SÖKÜM DOĞRULANMALI** (hafıza: `prob-kendi-baglamini-olcer`):
sentetik çağrıyı **işçi kimliğiyle** kurarsan kapı seni muaf tutar ve ölçüm YALAN olur.
Ortamdan `PRUVO_ISCI_KOSUMU`'nu SİL, payload'da `agent_id` VERME, ve
`mimar_kimlik.kimlik_ekseni(...)` çağrısının `None` (MİMAR) döndüğünü **ayrıca yazdır**.
Sökemezsen o evi `MUAF_BAGLAM` diye işaretle, "YEŞİL" YAZMA.

YAZ: ev × (kurulu `ISCI_MOTORLARI` değeri, `ISCI_MOTOR_KAYNAK_IMZASI`, `kimi` hükmü, rc).

## H — DEFTER KOTASI
`DEVAM.md` bayt kotasını aşıyor (12737 / tavan 12288) ve merge commit'ini BLOKLUYOR:
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/defter-rotasyon.py /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/DEVAM.md /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/DEVAM-ARSIV.md
```
KABUL: rotasyon 1:1 KAYIPSIZ (taşınan satır sayısı = arşive eklenen satır sayısı) ve
`DEVAM.md` bayt sayısı ≤ 12288. YAZ: önce/sonra satır+bayt sayıları.
🔴 `DEVAM-ARSIV.md` git DIŞIDIR — commit'leme.

---

## RAPOR
Raporu, projenin mimar raporu için mandat ettiği kanonik adla bu worktree'nin köküne yaz
(ad CLAUDE.md İLETİŞİM PROTOKOLÜ bölümünde tanımlıdır; başka ad YASAK).
Her madde için **SAYI** yaz. Ölçemediğin her şey için `ÖLÇÜLEMEDİ + sebep` satırı bırak —
tahmin/“yeşil görünüyor” YASAK. Yeşil tablo uydurma: her satırın arkasında koştuğun
komut ve rc'si olsun.
