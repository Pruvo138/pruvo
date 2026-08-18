# PAKET K168b — `kral/k168-recete-yasak` (`01404b8f`) → main MERGE dilimi

Mimar: KraL · 18 Ağu 2026 · hedef kat: **İZOLE OLMAYAN İŞÇİ** (ana checkout'ta çalışan tur).

## 0. MİMARIN ÖN ÖLÇÜMÜ (git objelerinden; teyit et, tekrarlama)

```
git show --stat kral/k168-recete-yasak → 3 dosya, +600/-5
    .github/workflows/nobet.yml  +16   tools/mimar-icra-kapisi.py  +39/-5
    tools/recete-kapisi.py       +550 (yeni)
git show kral/k168-recete-yasak:.github/workflows/nobet.yml | grep -c "recete-kapisi.py"   → 2
git show kral/k168-recete-yasak:tools/ci-kapsam-test.py     | grep -c "recete-kapisi"      → 0  (muafiyet YOK ✅)
git show kral/k168-recete-yasak:tools/recete-kapisi.py | grep -c '^CANON\|= "/Users/okan'  → 0  (sabit kok YOK ✅)
```

Kapsam spec'e uygun; muafiyet eklenmemiş, kablo iki adım olarak SERİT B'de, kapı taşınabilir
(③f dersi uygulanmış).

⚠️ `nobet.yml`e başka oturumlar dokunuyor. Merge'den hemen ÖNCE:
```
git -C /Users/okan/dev/pruvo fetch origin
git -C /Users/okan/dev/pruvo log --oneline -3 -- .github/workflows/nobet.yml
git -C /Users/okan/dev/pruvo merge-tree --write-tree --name-only main kral/k168-recete-yasak
```
Çakışma varsa (yalnız ağaç OID'i dönmüyorsa) **DUR** ve rapora yaz.

## 1. ADIM 1 — kapıları DALIN ağacında koş

Worktree ZATEN AÇIK: `/Users/okan/dev/pruvo/.claude/worktrees/k168-recete-yasak`.
Yeni worktree AÇMA. Oradan (her komutun `pwd`'si rapora):

```
python3 tools/recete-kapisi.py --kendini-test
python3 tools/recete-kapisi.py
python3 tools/ci-kapsam-test.py
python3 tools/mimar-kilit-test.py
```

Beklenen (önceki tur; **bağımsız yeniden ölçülecek**):
`RECETE=<n> REDDEDILEN=0 EVREN=<n> MUTANT=3/3 KONTROL=2/2 rc=0` ·
`ci-kapsam-test` YEŞİL ve `recete-kapisi.py` muaf listesinde YOK · `mimar-kilit-test` 290/290.

🔴 **H1'in fiilen açıldığının davranışsal kanıtı (bu turun en önemli ölçümü):** worktree'nin
ağacındaki `mimar-icra-kapisi.py` ile şu iki çağrının hükmünü **kuru** ölç ve rapora yaz:
* `python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py /Users/okan/dev/pruvo/DEVAM.md /Users/okan/dev/pruvo/DEVAM-ARSIV.md` → **allow**
* aynı komut sonuna `--tavan-sayi 130` eklenmiş hâli → **deny**
İkincisi allow çıkarsa yetki genişlemiştir → **MERGE ETME.**

## 2. ADIM 2 — merge + push (ANA checkout'tan)

```
git -C /Users/okan/dev/pruvo merge kral/k168-recete-yasak -m "K168: kapinin recete ettigi care artik kosulabilir + recete-kapisi nobetcisi SERIT B'de"
git -C /Users/okan/dev/pruvo push origin main
```
Yabancı ` M` / untracked'a DOKUNMA. `push --force` ASLA. D1 kolunda "YAZICI UÇUŞTA" derse
geçicidir (K176) — bekle, tekrar dene, `--no-verify` ARAMA.

## 3. ADIM 3 — merge sonrası

```
python3 /Users/okan/dev/pruvo/tools/d1-sync.py --durum
python3 /Users/okan/dev/pruvo/tools/recete-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/ci-kapsam-test.py
```

CI teyidi — SHA'yı **İÇEREN** koşum (en son yeşil kanıt DEĞİL):
```
gh -R Pruvo138/pruvo run list --limit 20 --json headSha,name,status,conclusion,databaseId
git -C /Users/okan/dev/pruvo merge-base --is-ancestor <merge-SHA> <kosumun-headSha>
```
SERİT B koşumu bitmediyse **`OLCULEMEDI` + sebep** yaz; yeşil YAZMA.

## 4. ADIM 4 — temizlik

```
git -C /Users/okan/dev/pruvo worktree remove --force /Users/okan/dev/pruvo/.claude/worktrees/k168-recete-yasak
git -C /Users/okan/dev/pruvo branch -D kral/k168-recete-yasak
git -C /Users/okan/dev/pruvo worktree list
```
Silmeden önce: porcelain temiz mi · dalın İÇERİĞİ gerçekten main'de mi · ana ağaçta o işe
benzeyen commit'siz değişiklik var mı. `k166b-yayin-sinyali`'ye DOKUNMA.

## 5. RAPOR

Kanonik mühendis rapor dosyasına BAŞA ekle. İçinde: her komutun ham son satırı + rc + `pwd` ·
**H1 allow/deny çifti** · merge SHA · push sonucu · D1 satırı · CI teyidi (ya da OLCULEMEDI +
sebep) · son satır `TEMIZ=EVET` + `worktree list`.

## 6. İŞÇİ TALİMATI

* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Bütçenin yarısında elindekini kaydet, raporu kapat.
* Kırmızı adımın üstünden atlayıp merge etme.
* **DOKUNMA:** `urunler.json` · `crontab` · `DEVAM.md` · `~/.claude/cron/` · `k166b` worktree'si.
