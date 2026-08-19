# ODEV — uc dal merge'inin OKAN KAPISI kolu (tek yapistirma / dal)

> Mimar (KraL) hazirladi, 20 Agu 2026. **Prosedurun tek kaynagi `tools/paket-uc-dal-merge.md`**;
> bu dosya onun yerine gecmez, yalniz *kim koşturacak* sorusunu kapatir.

## NEDEN OKAN KAPISI (olculdu, tahmin degil)

- Merge kapisinin kabul bataryalari `python3` istiyor. Mimar icra kapisi bunu ana oturumda
  **REDDEDIYOR** — 20 Agu'da olculdu: `python3 tools/ci-kapsam-test.py` cagrisi kapiya carpti
  (*"Mimar tarafinda SERBEST yalniz iki komut: durum.py ve d1-sync.py --durum"*).
- Alt-ajan / `Agent` / `isci.sh claude` yolu **AGENT-KAPISI** ile yasak.
- Chip sinyali gelmedi (Okan, 20 Agu).
- Mimar kod-kilidi `.py` yazmayi da yasakliyor → tek komutluk kosucu betik YAZILAMADI.
- Geriye hafizadaki tek uygulanabilir yol kaliyor: **Okan'in kendi kabugu.**
  ([[mimar-kapisi-muafiyeti-agent-id-ye-bagli]])

## MIMARIN ELIYLE ZATEN OLCULDUGU (tekrar olcme)

- `main == origin/main`, agac TEMIZ, worktree **1**.
- Kapsam `merge-base...uc` ile olculdu ve spec tablosuyla **birebir**:
  N1 2 dosya +23/−3 · N2 9 dosya +3111/−12 · K184 9 dosya +2359/−104.
- `urunler.json` / `.urun-kaynaklari.json` temasi **YOK**, sizinti (tedarikci/uyelik/telefon/
  `RAPOR-*`) **YOK** → spec §4 DUR kosullarinin diff ekseni **temiz**.
- Cakisma on-testi guncel main'de ucunde de **temiz**.
- N1'in kabul bataryasi **repo DISI** (`~/.claude/cron/`), dordu de diskte VAR; N1'in repo
  delta'si yalnizca `DEVAM.md` + `tools/kancalar/pre-push` (20 satir, **RAPOR-ONLY**, blokta
  `exit` YOK, olculen maliyet 0,045 sn) — mimar gozuyle satir satir okundu, temiz.

## 🔴 KOSMA KURALI

Her blok **tek `&&` zinciri**: bir adim kirmizi olursa zincir **orada durur** ve
`git push` satirina **hic gelmez** → yayina bir sey gitmez. Blogun ciktisini oldugu gibi
mimara ver; mimar hukmu ondan verir. **Bloklari SIRAYLA kos, atlamadan.**

Bir blok yarida kirmizi bitip **merge satiri gecilmisse**, ana checkout'ta itilmemis bir merge
kalir — o hâlde baska is yapmadan mimara haber ver (komsunun push'u onu yayina tasiyabilir).

---

## BLOK 1 — N1 (`kral/n1-gozcu-kablolama`)

```
cd /Users/okan/dev/pruvo && python3 ~/.claude/cron/gozcu-test.py && python3 ~/.claude/cron/gozcu-mutasyon.py && python3 ~/.claude/cron/nobet-kabul-test.py && python3 ~/.claude/cron/nobet-tetik-test.py && git merge origin/kral/n1-gozcu-kablolama -m "merge: N1 — gozcu kablolamasi (pre-push'a RAPOR-ONLY kalp nobeti; nobet turu artik kosulsuz degil, gozcunun kararina bagli)" && python3 tools/ci-kapsam-test.py && python3 tools/kapi-envanteri.py && python3 tools/d1-sync.py --durum && git push origin main
```

Beklenen (chip beyani — **dogrula, kopyalama**): `gozcu-test` 112/112 · `gozcu-mutasyon` 16/16
`IDDIA=16 ISTASYON=0` · `nobet-kabul-test` 45/45 · `nobet-tetik-test` `VAKA=38 DUSEN=0 KABLO=19/19`.
Worktree gerekmez: N1'in bataryasi repo disinda.

## BLOK 2 — N2 (`kral/n2-kirleten-onarir`)

```
cd /Users/okan/dev/pruvo && git worktree add --detach .claude/worktrees/n2-kirleten origin/kral/n2-kirleten-onarir && cd /Users/okan/dev/pruvo/.claude/worktrees/n2-kirleten && python3 tools/n2-kabul.py && cd /Users/okan/dev/pruvo && git merge origin/kral/n2-kirleten-onarir -m "merge: N2 — kirleten onarir (ev/sahiplik kapilari, parti kapisi, devir kapisi, mimar-kapi-kur)" && python3 tools/mimar-kapi-kur.py --parti-kapisi --uygula && python3 tools/kanca-kur.py && python3 tools/ci-kapsam-test.py && python3 tools/kapi-envanteri.py && python3 tools/d1-sync.py --durum && git push origin main && git worktree remove --force /Users/okan/dev/pruvo/.claude/worktrees/n2-kirleten
```

🔴 `mimar-kapi-kur.py` + `kanca-kur.py` kosmadan N2 merge'i **YARIM**: N1 raporundaki ⑨ kanca
nobetcisi kirmizisi ancak bundan sonra yesile doner (BaBa, 20 Agu). Zincirde o yuzden var.

## BLOK 3 — K184 (`kral/k184-talep-sihirbazi`)

```
cd /Users/okan/dev/pruvo && git worktree add --detach .claude/worktrees/k184-talep origin/kral/k184-talep-sihirbazi && cd /Users/okan/dev/pruvo/.claude/worktrees/k184-talep && python3 tools/talep-sihirbazi-test.py && cd /Users/okan/dev/pruvo && git merge origin/kral/k184-talep-sihirbazi -m "merge: K184 — talep sihirbazi (vitrin formu, yayin-topla, is-akisi kapisi; VAKA 36 onarildi)" && node tools/parite-test.js && node tools/parite-ege.js && python3 tools/yasal-sayfa-drift-kapisi.py && python3 tools/ci-kapsam-test.py && python3 tools/kapi-envanteri.py && python3 tools/d1-sync.py --durum && git push origin main && git worktree remove --force /Users/okan/dev/pruvo/.claude/worktrees/k184-talep
```

K184 `index.html` + `build.py` + `yayin-topla.py` ile **site yuzeyine** dokunan tek dal → parite
**merge EDILMIS main uzerinde, ana checkout'tan** kosuyor (spec §4: bayat tabanda kosulan pariteyi
SAYMA). Bu yuzden parite satirlari merge'den SONRA, push'tan ONCE.

---

## BLOK 3'TEN SONRA (mimar yapar, Okan'dan is istemez)

- Kosumun SHA'yi **ICERDIGINI** kanitla (`gh run list --json headSha` + `git merge-base --is-ancestor`),
  sonra **cache-bust'SIZ** kanonik URL'den canli teyit — spec §2.8.
- `python3 tools/durum.py` ile ucunun de **icerigi** main'de mi siniflandir ("ucu main'de" ≠ icerik main'de),
  ancak ondan sonra dal silme.
- Olculemeyen her sey icin deftere `OLCULEMEDI + sebep` yaz; "yesil gorunuyor" YASAK.
