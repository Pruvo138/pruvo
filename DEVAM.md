# DEVAM (KraL) — 8 Agu 2026

## 🕐 CI NOBETI — 12 Agu 2026 05:37 yerel / 02:37Z turu (KraL / Tamirci)

**Ev kontrolu:** `pwd` = `git rev-parse --show-toplevel` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=TEMIZ.** Sabit kosucu isciye kosturuldu; betik YAZILMADI/DUZENLENMEDI.
Betigin bastigi satirlar: `GITHUB_BILDIRIM_INBOX=0 · BULUNAN=0 · TASINAN=0 · ATLANAN=0 · CIKAN=0 ·
KOMSU_KAYIP=0 · KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=4:2026-08-12T04:05:51 · HUKUM=TEMIZ`.
Uc fail-closed alarmin ucu de sessiz. **Sayac 0 iken hukum TEMIZ yazilabildi cunku POZITIF
tanima izi var:** aranan dizenin AYNISI Cop'te 4 kayit tutuyor, en yenisi ayni gun 04:05 →
esleştirici fiilen tutuyor, onceki turlarin supurmesi calismis (aksi halde `OLCULEMEDI` yazilirdi).

**🟠 Cop denetimi (salt okuma): MESRU=4, YANLIS=0.** Dordu de `Run failed` bildirimi. Onceki turun
`YANLIS=4` kalemi Cop'te artik yok. Siparis/odeme ekseninde kayit YOK → para kaybi sinifi DEGIL.

**✅ CI KIRMIZISI KENDI KENDINE DEGIL, ONCEKI COMMIT'LE KAPANMIS — teshis dogrulandi.** Iki
basarisiz kosum bulundu: `31549865286` (`Build & deploy`, `81b2592f`) ve `31549231125`
(`Nobet seridi SERIT B`, `faa7148a`). Birincinin kok nedeni logdan ALINTILANDI: ic rapor adi
kapisi izlenen kok defterde **2 muafiyet-disi isabet** bulup `serit-a3`'u rc=1 ile durdurmus
(`deploy`+`yayin` SKIPPED). O sinif `3383aa90` ile kapanmis. Bu turda onarim GEREKMEDI, ama
"yesil" iddiasi beyandan degil JOB birimiyle olculdu: son deploy kosumu `31553100074`
→ `build:success · deploy:success · yayin:success`, ata testi `merge-base --is-ancestor` **rc=0**.
`cancelled` 2 kosum ariza SAYILMADI (§4.5 kuyruk davranisi).

**✅ K61 KAPANDI — dal aranirken "yok" cikti, cunku ICERIGI ZATEN MAIN'DE.** Merge kapisi acildi,
on-olcum isciye kosturuldu ve `DAL_YOK` dondu; bagimsiz eksen bunu duzeltti:
`git branch -r --contains 20cd51c3` → **`origin/main`** (merge `9fdd100a`, kardes oturum icra
etmis). **Davranissal kanit (oz-rapor DEGIL):** ayni workflow'un `9fdd100a`'yi ata olarak tasiyan
ilk tam kosumu `31553100206` (head `cc727e6a`) **success**; ondan onceki iki kosum
(`31549231125`, `31542119603`) **failure** idi → kirmizi→yesil gecisi duzeltmenin SHA'sina
HIZALI, sabit pencere kaymasi degil. Ayrinti + sinif dersi acik kalem defterinde.

**🔧 TAMIRCI TURU (§4.7).** Defterde tur basinda **10 acik 🔧** (K49·K53·K54·K55·K56·K58·K59·K61·
K62·K66); en eskisi K49 (11 Agu). Bu turda **K61 KAPANDI → 9 kaldi.**
- **🔴 GECEN TURUN DAGITIMI ARTEFAKT BIRAKMAMIS (K49).** Spec diskte (01:45Z) ama dal ne yerelde
  ne origin'de, worktree'si de YOK — kardes dagitim K66 ayni dakikada canli agac + dal uretmisti.
  Isci dogmadan olmus. **Sinif dersi: dagitim "spec yazildi" ile kapanmaz, kabul iscinin
  ARTEFAKTIDIR** (dal/worktree/rapor). Ayni turda YENIDEN DAGITILDI (MUHENDIS/Opus, izole agac).
- **K62 ve K66 uctusta**, ikisinin de canli agaci ve dali var; K65 ikinci turunda.

**📏 WORKTREE TAVANI: SAYI=5, KraL'in KENDI agaci 0.** Dordu uctusta mühendis/ajan agaci
(`kral/marka-sayac-esitleme` · `kral/k66-ic-rapor-kanca` · `kral/k62-dayanak` + bir ajan agaci),
biri ana agac. **SILME YOK** — canliligi olculmemis agac silinmez (K52 dersi); tavan mimarin
KENDI actigi agaclari sayar ve o sayi 0.

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · kapi/nobetci GEVSETILMEDI · merge YAPILMADI (gerekmedi) ·
yabanci ` M`/`??` dosyalara DOKUNULMADI · baskasinin worktree'sine DOKUNULMADI.
Codex'e 4 cagri (mail supurme+Cop · CI olcumu · sinif teyidi · defter kotasi), MUHENDIS'e 1 dal
(K49 yeniden). Okan'a CIKILMADI (rutin onarim yok, insan karari gerekmedi; §5).

**Sonraki turun ILK ISI:** (a) K49 mühendis dalinin artefakti GERCEKTEN dogdu mu — dal + worktree
ekseninden olc, "spec var" ile kapatma; (b) K66 ve K62 dallarinin kabul sayilarini tart;
(c) K65'in ikinci turundaki uc iade maddesi kapandi mi.

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
