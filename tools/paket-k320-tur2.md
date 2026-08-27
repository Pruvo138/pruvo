# K320 TUR-2 — yeniden ölçüm (yama ZATEN kurulu)

Kurallar önceki turla aynı: **borusuz** koş, `MUTANT`/`[DUSTU]` satırları
**normal teşhis çıktısıdır**, `rc=1` görürsen **DURMA**, hepsini koştur.
Hiçbir dosyayı elle düzenleme.

### 1) Yama durumu (hepsi `KURULU` bekleniyor)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py --durum > /Users/okan/.claude/cron/tmp/k320-t2-durum.txt 2>&1
```

### 2) Kabul bataryası
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-kabul.py > /Users/okan/.claude/cron/tmp/k320-t2-kabul.txt 2>&1
```

### 3) Mevcut bataryalar — regresyon
```
python3 /Users/okan/.claude/cron/isci-karantina-test.py > /Users/okan/.claude/cron/tmp/k320-t2-karantina.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py > /Users/okan/.claude/cron/tmp/k320-t2-tetik.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/gozcu-test.py > /Users/okan/.claude/cron/tmp/k320-t2-gozcu.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py > /Users/okan/.claude/cron/tmp/k320-t2-nobet.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/isci-karantina-mutasyon.py > /Users/okan/.claude/cron/tmp/k320-t2-karmutasyon.txt 2>&1
```

## BİTİRİNCE
Tek satır: `K320-T2 ADIMLAR=<n>/7`. Başka hiçbir şey yazma.
