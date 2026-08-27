# K320 — NÖBET HATTI ÜÇ KOL: KOŞUM SPEC'İ (işçi katı)

Sen bu turda **hiçbir tasarım kararı vermiyorsun**. Yalnız aşağıdaki komutları
**SIRAYLA** koşturuyorsun ve **ham çıktıyı** belirtilen dosyalara döküyorsun.
Sayı uydurma, tablo yazma, özet çıkarma — mimar sayıları dosyadan kendisi okuyacak.

## KURALLAR
- Komutları **BORUSUZ** koştur (`| tee`, `| grep` YOK) — boru rc'yi yalanlar.
- `MUTANT ...` ve `[DUSTU] ...` satırları **NORMAL TEŞHİS ÇIKTISIDIR**, hata değildir.
  **`rc=1` görürsen DURMA**, sonraki maddeye geç, **HEPSİNİ** koştur.
- Hiçbir dosyayı **elle düzenleme**. Yalnız listelenen komutlar.
- Çıktı yolları **git dışıdır** (`/Users/okan/.claude/cron/tmp/`); repoya dosya bırakma.

## ADIMLAR

### 1) TABAN (yamadan ÖNCE — kırmızı BEKLENİR, bu normaldir)
```
mkdir -p /Users/okan/.claude/cron/tmp
```
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-kabul.py > /Users/okan/.claude/cron/tmp/k320-1-taban.txt 2>&1
```

### 2) YAMA DURUMU (yamadan önce — hepsi `EKSIK` bekleniyor)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py --durum > /Users/okan/.claude/cron/tmp/k320-2-durum-once.txt 2>&1
```

### 3) KURU KOŞUM (yazmadan farkı bas)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py --kuru > /Users/okan/.claude/cron/tmp/k320-3-kuru.txt 2>&1
```

### 4) UYGULA (yedek otomatik alınır)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py > /Users/okan/.claude/cron/tmp/k320-4-uygula.txt 2>&1
```

### 5) SÖZDİZİMİ (yamalı dosyalar hâlâ çalışabilir mi)
```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/gozcu.py /Users/okan/.claude/cron/isci-karantina-karar.py > /Users/okan/.claude/cron/tmp/k320-5-sozdizimi.txt 2>&1
```
```
zsh -n /Users/okan/.claude/cron/ci-nobeti.sh > /Users/okan/.claude/cron/tmp/k320-5b-zsh.txt 2>&1
```

### 6) YAMA DURUMU (yamadan SONRA — hepsi `KURULU` bekleniyor)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-yama.py --durum > /Users/okan/.claude/cron/tmp/k320-6-durum-sonra.txt 2>&1
```

### 7) KABUL (yamadan SONRA — asıl ölçüm)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zealous-chatterjee-4e19cc/tools/nobet-uc-kol-kabul.py > /Users/okan/.claude/cron/tmp/k320-7-kabul.txt 2>&1
```

### 8) MEVCUT BATARYALAR — REGRESYON (bu dosyalara dokunduk, eski kabuller hâlâ yeşil mi)
```
python3 /Users/okan/.claude/cron/isci-karantina-test.py > /Users/okan/.claude/cron/tmp/k320-8a-karantina.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py > /Users/okan/.claude/cron/tmp/k320-8b-tetik.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/gozcu-test.py > /Users/okan/.claude/cron/tmp/k320-8c-gozcu.txt 2>&1
```
```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py > /Users/okan/.claude/cron/tmp/k320-8d-nobet.txt 2>&1
```

## BİTİRİNCE
Tek satır yaz: `K320 ADIMLAR=<kaç adım koştu>/10`. Başka hiçbir şey yazma.
Dosyaları okuma, yorumlama, özetleme.
