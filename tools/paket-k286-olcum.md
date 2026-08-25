# SPEC — K286 ÖLÇÜM TURU (yalnız KOŞTUR ve HAM ÇIKTIYI YAZ)

Sen bu turda **kod YAZMAYACAKSIN**. Görevin: aşağıdaki komutları **birebir**, **verilen
sırayla** koşturmak ve **ham çıktılarını** tek dosyaya yazmaktır. Yorum katma, özetleme,
"düzelttim" deme. Bir komut kırmızı dönerse **olduğu gibi bırak ve devam et** — kırmızı
da bir ölçümdür ve bana lazımdır.

## KAPSAM ÖN-ÖLÇÜMÜ (önce bunu doğrula)
Çalışma ağacı: `/Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531`
Bu **ana checkout DEĞİL**. Bütün komutlar bu tam yolla yazılmıştır; yolu kısaltma,
`cd` kullanma, göreli yola çevirme. Yanlış ağaçta ölçüm bu turu geçersiz kılar.

## ÇIKTI DOSYASI
Hepsini şuraya yaz (üzerine yaz, ekleme yapma):
`/Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/olcum-k286.txt`

Her komut için sırasıyla şu üç şeyi yaz:
1. `=== KOMUT: <komutun kendisi>`
2. komutun **tam stdout+stderr** çıktısı (kırpma yok)
3. `=== RC=<komutun gerçek çıkış kodu>`

🔴 `rc` değerini **borudan okuma**. `| tee`, `| grep`, `| head` ile ölçülen rc borunun
rc'sidir, komutun değil — bu depoda ölçüldü ve yanlış "0" raporlandı. Komutu **çıplak**
koştur, çıkış kodunu ayrıca al.

## KOŞULACAK KOMUTLAR

### K1 — taban çürütme (kusur main'de gerçekten var mı)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/k80-yorum-cagri-test.py --taban-curutme origin/main
```

### K2 — K286 bataryası (asıl kabul)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/k80-yorum-cagri-test.py
```

### K3 — kapının kendi öz-testi (regresyon: yamadan sonra taban sağlam mı)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/is-akisi-kapisi.py --kendini-test
```

### K4 — CI kapsam kapısı (yeni test bir iş akışından koşuyor mu)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/ci-kapsam-test.py
```

### K5 — nöbetçi mutasyon bataryası (kapının kapı-nöbetçisi)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/admiring-taussig-065531/tools/nobetci-mutasyon-test.py
```

## KABUL SATIRI
Çıktı dosyasının **en son satırına** birebir şunu yaz (sayıları K1–K5'in **gerçek**
çıkış kodlarından doldur, uydurma):

```
OLCUM_BITTI K1=<rc> K2=<rc> K3=<rc> K4=<rc> K5=<rc>
```

## YASAK
- Kaynak dosyaya (`.py`, `.yml`) **dokunma** — bu tur salt ölçümdür.
- `git commit` / `git push` / `git checkout` / `git reset` **YOK**.
- Çıktıyı "temizleme", kısaltma, yeniden yazma yok; ham metin.
- Kırmızıyı yeşile çevirmeye çalışma; raporla ve dur.
