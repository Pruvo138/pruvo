# kabul-matrisi — dort bataryayi kos, rc'leri ve SAYILARI tek tabloya yaz

EV: /Users/okan/dev/pruvo/.claude/worktrees/keen-lewin-a2a3fb
KUTU (kanonik yol; SEN buraya YAZMAZSIN, yalniz okuyabilirsin):
  /Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md
CIKTI: mimar raporu (TEK dosya, cron kutusu yolu)

## BU TUR NE DEGIL
Kod DEGISTIRMEZSIN. Bu tur SALT OLCUMDUR: kosuyorsun, rc'yi ve sayilari YAZIYORSUN.
Bir batarya kirmizi yanarsa ONARMA — sayiyi yaz, gec.

## YAP (numarali, her adim tek komut; her komutun rc'sini AYRI yaz)
1. `cd /Users/okan/dev/pruvo/.claude/worktrees/keen-lewin-a2a3fb`
2. `python3 tools/tikayici-kaldirma-test.py` — rc'yi yaz; ciktidan su UC satiri AYNEN kopyala:
   `D1 KIRMIZI=...` · `D2 VAKA n/m GECTI` · `KIRMIZI: D1=... D2=... OLCULEMEDI=... TOPLAM=...`
   Ayrica `❌` ile BASLAYAN satirlari SAY ve `CIKTI_KIRMIZI=<n>` diye yaz.
3. 🔴 TUTARLILIK: adim 2'de `TOPLAM=` sayisi ile `CIKTI_KIRMIZI=` sayisi AYNI olmali ve
   (sayi>0 <=> rc!=0) olmali. Tutmuyorsa `TUTARLILIK=KIRMIZI` yaz ve farkı ADIYLA goster.
4. `env PRUVO_ISCI_KOSUMU=minimax-m3 python3 tools/tikayici-kaldirma-test.py` — AYNI uc satir + rc.
   🔴 BU ADIMIN AMACI: batarya artik KOSUCUNUN KIMLIGINE KOR mu? adim 2 ile adim 4'un
   `D2 VAKA` ve `CIKTI_KIRMIZI` sayilari BIREBIR AYNI olmali. Farkliysa `KIMLIK_CIVISI=KIRMIZI`.
5. `python3 tools/ci-kapsam-test.py` — rc + son `SONUC:` satiri.
6. `python3 tools/icra-kapisi-test.py` — rc + son `SONUC:` satiri.
7. `python3 tools/mimar-kilit-test.py` — rc + `SONUC: <gecen>/<toplam>` satiri.
   🔴 ONCUL: bu bataryanin HEDEF 92 vakasi bu turdan ONCE DE kirmiziydi (taban HEAD'de olculdu).
   Sen yalnizca BUGUNKU sayiyi yaz; "onarildi/bozuldu" HUKMU VERME.
8. `git -C /Users/okan/dev/pruvo/.claude/worktrees/keen-lewin-a2a3fb status --short` ciktisini AYNEN yapistir.
9. Son adim TEMIZLIK: urettigin gecici dosya varsa SIL ve `ls` ile sildigini KANITLA.

## YAPMA
- Hicbir kaynak dosyayi DEGISTIRME · `git add/commit/push` YOK · main'e merge YOK
- `urunler.json` / `arama.py` / `index.html` / `tools/build.py` ACMA · secret okuma YOK
- Kirmizi cikan bir bataryayi ONARMAYA CALISMA — bu turun isi OLCMEK
- Sayi UYDURMA: bir komut kosmadiysa `OLCULEMEDI` yaz, tahmin YAZMA

## KABUL
Rapor su alti satiri BIREBIR icerir (sayilar senin olcumun):

    TIKAYICI_RC=<n>
    TIKAYICI_KIRMIZI=<n>
    TIKAYICI_ISCI_ORTAM_KIRMIZI=<n>
    CI_KAPSAM_RC=<n>
    ICRA_KAPISI_RC=<n>
    MIMAR_KILIT_RC=<n>

ve `TUTARLILIK=` ile `KIMLIK_CIVISI=` satirlari YESIL/KIRMIZI degerinden BIRINI tasir.

## ONCUL
`tools/tikayici-kaldirma-test.py` ciktisinda `KIRMIZI: D1=` ile baslayan bir OZET SATIRI VARDIR
(bu tur eklendi). YANLISSA UYGULAMA — DUR ve gordugun gercek son uc satiri raporun basina yaz.
