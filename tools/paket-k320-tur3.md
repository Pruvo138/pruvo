# K320 TUR-3 — A3 temizlik yaması + yeniden ölçüm

Kurallar aynı: **borusuz** koş, `MUTANT`/`[DUSTU]` satırları **normal teşhis
çıktısıdır**, `rc=1` görürsen **DURMA**, hepsini koştur. Elle düzenleme YOK.

### 1) Uygula (yalnız eksik kol uygulanır; kurulu olanlar `ZATEN_KURULU` der)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py > /Users/okan/.claude/cron/tmp/k320-t3-uygula.txt 2>&1
```

### 2) Sözdizimi
```
zsh -n /Users/okan/.claude/cron/ci-nobeti.sh > /Users/okan/.claude/cron/tmp/k320-t3-zsh.txt 2>&1
```

### 3) Durum (hepsi `KURULU` bekleniyor)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py --durum > /Users/okan/.claude/cron/tmp/k320-t3-durum.txt 2>&1
```

### 4) Kabul bataryası
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-kabul.py > /Users/okan/.claude/cron/tmp/k320-t3-kabul.txt 2>&1
```

### 5) Regresyon
```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py > /Users/okan/.claude/cron/tmp/k320-t3-tetik.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/gozcu-test.py > /Users/okan/.claude/cron/tmp/k320-t3-gozcu.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py > /Users/okan/.claude/cron/tmp/k320-t3-nobet.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/isci-karantina-test.py > /Users/okan/.claude/cron/tmp/k320-t3-karantina.txt 2>&1
```

## BİTİRİNCE
Tek satır: `K320-T3 ADIMLAR=<n>/8`. Başka hiçbir şey yazma.
