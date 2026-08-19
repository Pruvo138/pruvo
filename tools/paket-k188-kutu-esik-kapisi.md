# PAKET K188 — ORTAK KUTU EŞİK KAPISI (kalıcı, sınıf kalemi)

## NEDEN (ölçüldü)
`~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md` tavanı **300 satır**.
18 Ağu 22:45'te ELLE rotasyon koştu; **16 dakika sonra 333 satıra yeniden taştı**. Bu, elle
rotasyonun **BEŞİNCİ** tekrarıdır → tekil yama YASAK, sınıf kapısı gerekir.

Sınıf teşhisi: eşik yalnız **rotasyon aracının** (`tools/kutu-arsivle.py`) içinde biliniyor;
kutuya **YAZAN** yol (mimar oturumu, `Write`/`Edit`/`MultiEdit` aracı) eşiği HİÇ ölçmüyor.
Yani taşma ancak biri elle bakınca fark ediliyor. Çare: **yazan yola** eşiği ölçtür.

## HÜKÜM
`tools/kutu-esik-kapisi.py` yaz: Claude Code **PreToolUse** kancası. Kutuya yazma girişiminde
eşiği KENDİSİ ölçer ve aşılmışsa **yazmadan ÖNCE** rotasyonu tetikler; rotasyon başarısızsa
**fail-closed** yazmayı REDDEDER. Elle rotasyon bir daha gerekmemeli.

## DOSYALAR (hepsi bu worktree'de, tam yol)
Kök: `/Users/okan/dev/pruvo/.claude/worktrees/unruffled-kowalevski-880aa4`
1. `tools/kutu-esik-kapisi.py`            — kapı (YENİ)
2. `tools/kutu-esik-kapisi-mutasyon.py`   — mutasyon bataryası (YENİ)

`tools/kutu-arsivle.py`'ye **DOKUNMA**. `.claude/settings.json`'a DOKUNMA (kablolamayı mimar yapar).

## 1) `tools/kutu-esik-kapisi.py` — SÖZLEŞME

### Girdi
stdin'den Claude Code kanca JSON'u:
`{"tool_name":"Write","tool_input":{"file_path":"/...","content":"..."}}`
`Edit`/`MultiEdit` için de `tool_input.file_path` vardır.

### Çıkış kodları (Claude Code PreToolUse sözleşmesi)
* `0` = İZİN VER (yazma devam eder)
* `2` = REDDET (yazma bloklanır); gerekçe **stderr**'e yazılır

### Akış (sırayla)
1. stdin JSON parse edilemezse → `0` (kapı yazma yolunu kilitlemez; bu bir ölçüm kapısı,
   girdisi bozuksa sessiz geçer ve stderr'e `UYARI:` basar).
2. `tool_name` ∈ {`Write`,`Edit`,`MultiEdit`,`NotebookEdit`} değilse → `0`.
3. `tool_input.file_path` yoksa → `0`.
4. **HEDEF EŞLEŞMESİ**: `os.path.realpath(file_path)` == `os.path.realpath(KUTU_YOLU)`
   değilse → `0`. (Sembolik link/`~` genişletmesi realpath ile normalleşsin. Dosya henüz
   yoksa realpath yine karşılaştırılabilir — string karşılaştırması YETMEZ, realpath kullan.)
5. **EŞİK OKUMA — TEK KAYNAK**: eşiği **kendi dosyanda YENİDEN TANIMLAMA**.
   `tools/kutu-arsivle.py`'yi modül olarak yükle (`importlib.util.spec_from_file_location`,
   dosya adında tire var, düz `import` çalışmaz) ve `VARSAYILAN_TAVAN` sabitini ORADAN oku.
   🔴 Bu ikiz tanım yasağıdır: `300` sayısını bu dosyaya YAZMA.
6. Kutu diskte yoksa → `0`.
7. Kutunun **mevcut** satır sayısını ölç (`open(...,"rb").read().decode("utf-8").splitlines()`).
   `satir <= tavan` ise → `0` (stdout'a tek satır `ESIK ALTI satir=<n> tavan=<t>`).
8. `satir > tavan` ise **ROTASYONU TETİKLE**:
   `subprocess.run([sys.executable, <tam yol>/tools/kutu-arsivle.py], capture_output=True, timeout=60)`
9. Rotasyon sonrası kutuyu **YENİDEN ÖLÇ**.
   * rotasyon rc==0 **ve** yeni satır <= tavan → `0`, stdout: `ROTASYON TETIKLENDI once=<a> sonra=<b> tavan=<t>`
   * aksi halde → **FAIL-CLOSED**: `2`, stderr'e:
     `KUTU ESIK KAPISI (fail-closed): kutu <b> satir, tavan <t>. Rotasyon rc=<rc> ile tavani indiremedi -> yazma REDDEDILDI.`
     ardından rotasyon aracının stdout/stderr son 20 satırı.
10. Rotasyon çağrısı istisna fırlatırsa (timeout/OSError) → yine **`2`** (fail-closed).

### Bayraklar
* `--kendini-test` : aşağıdaki kabul testini koşar, rc=0 yeşil / rc=1 kırmızı.
* `--kutu <yol>`   : hedef kutu yolunu ezer (yalnız test içindir).
  Ortam değişkeni `PRUVO_KUTU_ESIK_KUTU` da aynı işi görür — kanca stdin ile koştuğu
  için testler bunu kullanır.

## 2) KABUL TESTİ (`--kendini-test`) — EN AZ 6 VAKA
Her vaka geçici dizinde (`tempfile.mkdtemp`) SAHTE kutu + SAHTE arşiv üretir; gerçek kutuya
**ASLA** dokunmaz. Fikstür `## ` bloklarından oluşsun, frontmatter'lı olsun (gerçek şekli
taklit etsin), ve blok sayısı `--koru 3`'ten fazla olsun ki rotasyon iş yapabilsin.

| # | Vaka | Beklenen |
|---|------|----------|
| V1 | `tool_name="Bash"` (alakasız araç), kutu tavanın ÇOK üstünde | rc=0, kutu **bayt-bayt DEĞİŞMEDİ** |
| V2 | `file_path` başka bir dosya, kutu tavanın üstünde | rc=0, kutu **DEĞİŞMEDİ** |
| V3 | Hedef kutu, satır **tavanın ALTINDA** | rc=0, kutu **DEĞİŞMEDİ**, çıktıda `ESIK ALTI` |
| V4 | Hedef kutu, satır **tavanın ÜSTÜNDE**, rotasyon indirebilir | rc=0, kutu satır **<= tavan**, arşiv **BÜYÜDÜ**, çıktıda `ROTASYON TETIKLENDI` |
| V5 | Hedef kutu, tavan üstünde ama **rotasyon indiremez** (tüm bloklar korunan bölgede: tek dev blok) | **rc=2**, stderr'de `fail-closed`, kutu **DEĞİŞMEDİ** |
| V6 | Hedef kutu, tavan üstünde, rotasyon aracı **KİLİTLİ** (kilit dosyasını test `flock` ile tutar → `kutu-arsivle.py` rc=3) | **rc=2**, stderr'de `fail-closed` |

Ek iddia (V4): rotasyon LOSSLESS — taşınan satırlar arşivde birebir. `kutu_once_bayt ==
kutu_sonra_bayt + tasinan_bayt` ve `arsiv_sonra_bayt - arsiv_once_bayt >= tasinan_bayt`.

Her vaka `V<n> YESIL/KIRMIZI  <ölçülen sayılar>` diye TEK SATIR bassın. Sonda
`KENDINI-TEST: <yesil>/<toplam>`.

## 3) MUTASYON BATARYASI (`tools/kutu-esik-kapisi-mutasyon.py`) — 3 MUTANT
🔴 **DİSKE YAZMA YASAK**: mutantlar kaynağın **KOPYASINA** uygulanır (temp dizin), asıl
`tools/kutu-esik-kapisi.py` DEĞİŞMEZ. Bytecode önbelleğine takılmamak için kopya farklı bir
dosya adıyla ve `sys.dont_write_bytecode = True` ile koşulsun.

| Mutant | Ne kırılır (kaynakta ARANAN dizge → YERİNE) | HEDEF KOL | Beklenen |
|--------|---------------------------------------------|-----------|----------|
| M1 EŞİK OKUNMUYOR | `VARSAYILAN_TAVAN` okuma satırı → sabit `10**9` | adım 5+7 | **V4 KIRMIZI** (rotasyon hiç tetiklenmez, kutu tavan üstünde kalır) |
| M2 ROTASYON TETİKLENMİYOR | `subprocess.run([...kutu-arsivle.py...])` çağrısı → hiç çağırmayan, rc=0 taklit eden sahte | adım 8 | **V4 KIRMIZI** |
| M3 FAIL-CLOSED KOLU ÖLÜ | fail-closed dalındaki `return 2` → `return 0` | adım 9-else + 10 | **V5 ve V6 KIRMIZI** |

### 🔴 HEDEF-KOL ATIFI (ölçülmüş tuzak — bunu ATLAMA)
"Batarya kırmızı yandı" YETMEZ. Her mutant için AYRICA kanıtla:
* **(a) HEDEF VAKA KIRMIZI**: M1/M2 → V4 kırmızı; M3 → V5 **ve** V6 kırmızı.
* **(b) YAN VAKALAR YEŞİL KALDI**: M1/M2 için V1,V2,V3 hâlâ YEŞİL; M3 için V1..V4 hâlâ YEŞİL.
  Eğer bir mutant TÜM vakaları kırmızı yakıyorsa o mutant **hedef kolu ölçmüyor** (çöküyor
  ya da yan ekseni tetikliyor) → mutantı daralt, öyle bırakma.
* **(c) DİZGE BULUNDU**: aranan dizge kaynakta bulunamadıysa mutant **KIRMIZI RAPOR EDİLİR**
  (sessizce "uygulandı" sayma). Bulunan satır numarası+metni rapora yazılsın.
* **(d) MUTANTSIZ TABAN YEŞİL**: batarya önce mutasyonsuz kopyayla koşup 6/6 YEŞİL almalı;
  taban kırmızıysa mutant sonuçları anlamsızdır → hemen rc=1.

Çıktı biçimi (her satır):
`M<k> <ad>: hedef=<vaka listesi> hedef_kirmizi=EVET/HAYIR yan_yesil=EVET/HAYIR dizge_satir=<n> HUKUM=OLDURDU/OLDURMEDI`
Sonda: `MUTASYON: <n>/3 OLDURDU`. Hepsi öldürmediyse rc=1.

## KOD STİLİ
* Python 3, stdlib YALNIZ (`json`,`os`,`sys`,`subprocess`,`tempfile`,`importlib.util`,`shutil`,`fcntl`,`argparse`,`re`).
* Türkçe yorum, ASCII-güvenli kod (repo geleneği: yorumlarda Türkçe serbest).
* Modül başlığında NEDEN VAR bölümü: yukarıdaki "16 dakikada yeniden taştı" ölçümü yazılı olsun.
* `tools/kutu-arsivle.py`'nin sözleşmesini DEĞİŞTİRME; yalnız çağır.

## KABUL (bunlar koşulacak, uydurma çıktı YASAK)
```
python3 tools/kutu-esik-kapisi.py --kendini-test      # rc=0, 6/6 YESIL
python3 tools/kutu-esik-kapisi-mutasyon.py            # rc=0, 3/3 OLDURDU
```
Gerçek kutu bu iki koşumda **bayt-bayt değişmemeli** — bataryanın sonunda bunu da ölç ve bas.

## RAPOR
Dal kökündeki kanonik mühendis raporuna yaz (ad için CLAUDE.md İLETİŞİM PROTOKOLÜ; başka ad
YASAK): iki komutun TAM çıktısı + ölçemediğin şey varsa `OLCULEMEDI: <sebep>`.

## YASAKLAR
* `git commit`/`git add` **ATMA** — commit'i mimar atar (zaten `index.lock`'a yazamazsın).
* `.claude/settings.json`, `urunler.json`, `DEVAM.md`, `tools/kutu-arsivle.py` — DOKUNMA.
* Gerçek `mimar-posta-kutusu.md`'ye test sırasında yazma.
