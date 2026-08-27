# K320 — GERİ YÜKLEME KANITI (yedekler gerçekten geri yüklenebiliyor mu)

Kural: canlı dosyalara **DOKUNMA**. Yedekler yalnız **geçici dizine** açılır,
orada doğrulanır ve geçici dizin **silinir**. Borusuz koş, hepsini koştur.

### 1) Geçici dizin
```
mkdir -p /Users/okan/.claude/cron/tmp/k320-geri
```

### 2) Yedekleri geçici dizine geri yükle (canlıya DEĞİL)
```
cp /Users/okan/.claude/cron/gozcu.py.yedek-nobetturu-20260827T153500Z /Users/okan/.claude/cron/tmp/k320-geri/gozcu.py
```
```
cp /Users/okan/.claude/cron/nobet-kapi.py.yedek-nobetturu-20260827T153500Z /Users/okan/.claude/cron/tmp/k320-geri/nobet-kapi.py
```
```
cp /Users/okan/.claude/cron/isci-karantina-karar.py.yedek-nobetturu-20260827T153500Z /Users/okan/.claude/cron/tmp/k320-geri/isci-karantina-karar.py
```
```
cp /Users/okan/.claude/cron/ci-nobeti.sh.yedek-nobetturu-20260827T153500Z /Users/okan/.claude/cron/tmp/k320-geri/ci-nobeti.sh
```

### 3) Geri yüklenen kopyalar ÇALIŞABİLİR Mİ (bozuk yedek = yedek değildir)
```
python3 -m py_compile /Users/okan/.claude/cron/tmp/k320-geri/gozcu.py /Users/okan/.claude/cron/tmp/k320-geri/nobet-kapi.py /Users/okan/.claude/cron/tmp/k320-geri/isci-karantina-karar.py > /Users/okan/.claude/cron/tmp/k320-geri-sozdizimi.txt 2>&1
```
```
zsh -n /Users/okan/.claude/cron/tmp/k320-geri/ci-nobeti.sh > /Users/okan/.claude/cron/tmp/k320-geri-zsh.txt 2>&1
```

### 4) Geri yüklenen kopya YAMASIZ TABAN mı (yamalı canlıdan FARKLI olmalı)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py --durum > /Users/okan/.claude/cron/tmp/k320-geri-durum-canli.txt 2>&1
```
```
env PRUVO_NOBET_KOK=/Users/okan/.claude/cron/tmp/k320-geri python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py --durum > /Users/okan/.claude/cron/tmp/k320-geri-durum-yedek.txt 2>&1
```

### 5) Fark satır sayısı (yamanın büyüklüğü)
```
diff /Users/okan/.claude/cron/tmp/k320-geri/gozcu.py /Users/okan/.claude/cron/gozcu.py > /Users/okan/.claude/cron/tmp/k320-geri-fark-gozcu.txt 2>&1
```
```
diff /Users/okan/.claude/cron/tmp/k320-geri/ci-nobeti.sh /Users/okan/.claude/cron/ci-nobeti.sh > /Users/okan/.claude/cron/tmp/k320-geri-fark-sh.txt 2>&1
```

### 6) TEMİZLİK — geçici dizini SİL (disk izi bırakma kuralı)
```
rm -rf /Users/okan/.claude/cron/tmp/k320-geri
```
```
ls /Users/okan/.claude/cron/tmp > /Users/okan/.claude/cron/tmp/k320-geri-temizlik.txt 2>&1
```

## BİTİRİNCE
Tek satır: `K320-GERI ADIMLAR=<n>/11`. Başka hiçbir şey yazma.
