# SPEC — K286 KABUL TURU (yalnız KOŞTUR ve HAM ÇIKTIYI YAZ)

Sen bu turda **kod YAZMAYACAKSIN**. Görevin: aşağıdaki komutları **birebir**, **verilen
sırayla** koşturmak ve **ham çıktılarını** tek dosyaya yazmaktır. Yorum katma, özetleme,
"düzelttim" deme. Bir komut kırmızı dönerse **olduğu gibi bırak ve devam et** — kırmızı
da bir ölçümdür ve bana lazımdır.

## KAPSAM ÖN-ÖLÇÜMÜ
Çalışma ağacı: `/Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531`
Bu **ana checkout DEĞİL**. Bütün komutlar bu tam yolla yazılmıştır; yolu kısaltma,
`cd` kullanma, göreli yola çevirme. Yanlış ağaçta ölçüm bu turu geçersiz kılar.

## ÇIKTI DOSYASI
Hepsini şuraya yaz (üzerine yaz, ekleme yapma):
`/Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/olcum-k286.txt`

Her komut için sırasıyla:
1. `=== KOMUT: <komutun kendisi>`
2. komutun **tam stdout+stderr** çıktısı (kırpma yok)
3. `=== RC=<komutun gerçek çıkış kodu>`

🔴 `rc` değerini **borudan okuma**. `| tee`, `| grep`, `| head` ile ölçülen rc borunun
rc'sidir, komutun değil — bu depoda ölçüldü ve yanlış "0" raporlandı. Komutu **çıplak**
koştur, çıkış kodunu ayrıca al.

## KOŞULACAK KOMUTLAR

### K1 — K286 bataryası (asıl kabul)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/k80-yorum-cagri-test.py
```

### K2 — taban çürütme (kusur main'de gerçekten var mı)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/k80-yorum-cagri-test.py --taban-curutme origin/main
```

### K3 — UÇTAN UCA: kapının kendisi, kendi commit'i üzerinde
Bu koşumda kapı `HEAD^..HEAD` aralığını ölçer; o commit `nobet.yml`'e GERÇEKTEN yeni bir
adım eklemiştir, dolayısıyla kapı onu yakalayıp geçici bir ağaçta KOŞTURMALIDIR.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/is-akisi-kapisi.py
```

### K4 — kapının öz-testi (regresyon)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/is-akisi-kapisi.py --kendini-test
```

### K5 — CI kapsam kapısı
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/ci-kapsam-test.py
```

### K6 — ağaç temiz mi (yalnız `olcum-k286.txt` izlenmeyen kalmalı)
```
git -C /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531 status --short
```

## KABUL SATIRI
Çıktı dosyasının **en son satırına** birebir şunu yaz (sayıları K1–K6'nın **gerçek**
çıkış kodlarından doldur, uydurma):

```
KABUL_BITTI K1=<rc> K2=<rc> K3=<rc> K4=<rc> K5=<rc> K6=<rc>
```

## YASAK
- Kaynak dosyaya (`.py`, `.yml`) **dokunma** — bu tur salt ölçümdür.
- `git commit` / `git push` / `git checkout` / `git reset` / `git stash` **YOK**.
- Çıktıyı "temizleme", kısaltma, yeniden yazma yok; ham metin.
- Kırmızıyı yeşile çevirmeye çalışma; raporla ve dur.
