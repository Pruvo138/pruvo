# P1 — Üst-marka sayfası mobil ilk ekran: ÖLÇÜM PAKETİ

Bu dosya, `claude/sad-neumann-462e89` dalındaki değişikliğin **kabul ölçümünü** koşturmak
içindir. Kod hazır. Bu dosyayı bir işçiye ver; başka bir şey yazmana gerek yok.

---

## 0. İŞÇİ TALİMATI — ÖNCE BUNU OKU (bağlayıcı)

**GÖREVİN: ÖLÇMEK. Kod YAZMA, kusur DÜZELTME, commit/push YAPMA.** Bir kapı kırmızı
dönerse onarma — kırmızıyı RAPORLA. `git add`, `git commit`, `git push`, `git checkout`,
`git reset` YASAK. `urunler.json` ve `.urun-kaynaklari.json` dosyalarına DOKUNMA.
`tools/build.py`'yi ÇALIŞTIRMA (repo kuralı: lokalde koşmaz, CI'da koşar).

**🔴 SAYI UYDURMA.** Bu deponun ölçülmüş dersi: ucuz kat "hepsi geçti" tablosu üretip
altındaki ölçümü boşaltıyor. Kurallar:
- Koşmadığın hiçbir komutu rapora YAZMA.
- Her komut için **tam komut metni + çıkış kodu (rc) + çıktının son satırları** ver.
- Koşamadığın her şeye birebir `ÖLÇÜLEMEDİ` + tam sebep yaz. "Muhtemelen geçer",
  "beklenen sonuç yeşil" gibi cümleler YASAK.
- Çıktıyı boru (`| tee`, `| grep`) ARKASINDAN okuma: ölçtüğün rc borunun rc'si olur,
  gerçek rc'yi yalanlar. Komutu düz koş, rc'yi ayrıca yazdır.

**Sıra:** §3.a (sözdizimi) → §3.b → §3.c → §3.d (taban ayrımı) → §3.e (tarayıcı).
§3.a düşerse DUR ve yalnız onu raporla; gerisi anlamsızdır.

**Rapor biçimi (son çıktın):** her kapı için tek satır
`<kapı adı> :: rc=<n> :: <YEŞİL|KIRMIZI> :: <DEĞİŞİKLİKTEN|TABAN DA KIRMIZI|-> :: <sayı>`
sonra kırmızıların ham çıktısı, sonra §2'nin piksel tablosu (ÖNCE ve SONRA ayrı).

---

## 1. NE DEĞİŞTİ

Tek dosya: `tools/marka_model_build.py` (+117 / −3). Yalnız `_marka_sayfasi` (üst-marka
sayfası, `/marka/<slug>/`). Alt-model sayfası (`_model_sayfasi`) ve marka dizini
(`_marka_index`) DEĞİŞMEDİ.

Üç yüzey **saf CSS** ile katlandı (JS YOK, `<a>`/`<li>` etiketleri BİREBİR korundu):

| yüzey | sabit | önce | sonra |
|---|---|---|---|
| model çipleri | `KATLA_MODEL_N = 12` | 104 çip hepsi açık | ilk 12 açık + "Tümünü gör (104 model)" |
| düz bağ listesi | `KATLA_KALAN_N = 24` | 536 girdi hepsi açık | ilk 24 açık + "Listenin tamamını aç (536 parça)" |
| giriş metni | `KATLA_GIRIS_SATIR = 4` | ~12 satır (mobil) | 4 satır + "Devamını oku" (YALNIZ ≤640 px) |

**Neden çipe sınıf eklenmedi:** dört kapı (`marka-cip-kapisi.py:61`,
`marka-kapsam-test.py:223`, `marka-sayac-kapisi.py:103-104`, `marka-artim-test.py:38`)
çip/li etiketini attribute SIRASI dahil katı regex ile ayrıştırıyor; ayrıca artım JS'i
(`cipleriIsaretle`) her tıklamada `className`'i komple yeniden yazıyor. Katlama bu yüzden
kapsayıcıda `:nth-child` ile kuruldu.

---

## 2. KABUL ÖLÇÜTÜ (ArTisT çiviledi — DEĞİŞTİRME, BÜYÜTME)

> **375 px genişlikte, üst-marka sayfalarının her birinde ilk 1624 px içinde ≥4 ürün kartı
> (görsel + fiyat) görünür. Ölçüm: en çok modelli 3 marka sayfasında 3/3.**

"Görünür kart" kesin tanımı (buna uy, gevşetme):
- `.card` sınıfı taşır **ve** içinde `img.card-img` **ve** `.card-price` vardır,
- `rect.bottom + window.scrollY ≤ 1624`,
- `display:none` / `visibility:hidden` / `offsetParent === null` DEĞİL.

Rapora yazılacak: marka adı · URL · çip sayısı · 1.–4. kartın üst+alt piksel değeri ·
1624 px içine sığan kart sayısı · GEÇTİ/KALDI.

**En çok modelli 3 markayı VARSAYMA — ölç:** `https://pruvo3d.com/marka/` her satırda
"<N> model · <M> parça" yazıyor; N'si en yüksek 3'ü al ve hangilerini aldığını yaz.

---

## 3. KOŞULACAKLAR

Ağaç: `/Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89`

### 3.a Sözdizimi (ÖNCE bu — düşerse gerisi anlamsız)
```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/marka_model_build.py
```

🔴 **YOLLAR MUTLAK VE DEĞİŞTİRİLEMEZ.** Ölçülecek iş `main`'de DEĞİL, aşağıdaki
worktree'de duruyor. Kısaltma/yer tutucu kullanma, `/Users/okan/dev/pruvo/tools/...`
diye koşma — o ana ağaçtır ve değişikliği GÖRMEZ, ölçüm bayat sayıyla yeşil yanar
([[spec-mutlak-yol-yanlis-agaci-olcer]]).

### 3.b Marka/model kapıları
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/marka-model-test.py
python3 /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/marka-cip-kapisi.py
python3 /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/marka-sayac-kapisi.py
python3 /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/marka-kapsam-test.py
python3 /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/marka-artim-test.py
python3 /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/marka-sayfa-mutasyon.py
```

### 3.c Spec'in zorunlu kıldığı kapılar
```
node /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/parite-test.js
node /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/parite-ege.js
python3 /Users/okan/dev/pruvo/.claude/worktrees/sad-neumann-462e89/tools/kategori-parite-test.py
```

### 3.d 🔴 TABAN ÖLÇÜMÜ — ATLANMAZ
Kırmızı dönen HER kapıyı değişikliğin OLMADIĞI kopyada da koş, kırmızıyı AYIR.
Taban = `origin/main` (dal onun ÜZERİNDE tek commit; başka hiçbir iş taşımıyor):
```
git -C /Users/okan/dev/pruvo worktree add /private/tmp/pruvo-taban-olcum origin/main
```
Her kırmızı için hüküm: `DEĞİŞİKLİKTEN` mi `TABAN DA KIRMIZI` mı.
Bitince (disk kuralı, zorunlu):
```
git -C /Users/okan/dev/pruvo worktree remove /private/tmp/pruvo-taban-olcum --force
```

### 3.e Tarayıcı ölçümü (§2)

🔴 **HİÇBİR ŞEY KURMA.** İlk ölçüm turu (`kabul-p1-ilk-ekran`) burada düştü: Chrome'u
**PATH'te** aradı, bulamadı, "sistemde Chrome/Chromium yok" hükmü verdi ve Playwright
kurmaya çalışıp zaman aşımına uğradı. **Hüküm YANLIŞTI** — Chrome kuruludur, sadece
PATH'te değildir:
```
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
```
🔴 **`--window-size=375` LAYOUT VIEWPORT'U VERMEZ — ölçülmüş, iki tur yaktı.** Chrome
headless bu argümanı yok sayıp iç viewport'u 485 px'te tuttu; ekran görüntüsü 375 px
çıktığı için ölçüm *doğru görünüyordu*. İkinci tur bunu "eşik viewport'tan bağımsız"
diye rasyonalize edip "GEÇTİ" yazdı — **yanlıştı**: kart ızgarası `@media (max-width:520px)`
altında farklı, çip sarması tamamen genişliğe bağlı.

**ÇALIŞAN YÖNTEM — 375 px'i iframe ile çivile:** sayfa, genişliği tam 375 px olan bir
`<iframe>`e konur; iframe içindeki `documentElement.clientWidth` kesinlikle 375 olur.
İki bayrak ZORUNLU, yoksa Chrome iç scrollbar'a 15 px ayırıp **360** verir:
```
--allow-file-access-from-files --hide-scrollbars
```
ve iframe'e `overflow:hidden`. Sarmalayıcı sayfa, ölçüm sonucunu iframe'den okuyup
kendi DOM'una metin olarak basar ve 1624 px'e kırmızı bir çizgi çizer; tek koşum:
```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-first-run --allow-file-access-from-files --hide-scrollbars --virtual-time-budget=20000 --window-size=900,2400 --screenshot=<yol>.png file:///.../olc-<faz>-<slug>.html
```
🔴 **TEK KANAL ZORUNLU:** sayı ve görüntü AYNI koşumdan çıkar. Bir turda PNG ile JSON ayrı
Chrome koşumlarından toplandı ve ikisi çelişti (PNG'de kartlar iki kolon, JSON'da tek
kolon). Sayılar PNG'nin içine basılırsa bu sınıf hata YAPISAL OLARAK imkânsızlaşır.

- **ÖNCE/baseline:** `curl -s https://pruvo3d.com/marka/<slug>/` → `<head>` ardına
  `<base href="https://pruvo3d.com/">` ekle (CSS/JS canlıdan gelsin) → scripti enjekte et.
- **SONRA:** 🚫 `tools/build.py` LOKALDE KOŞULMAZ. Sayfayı modülden üret —
  `marka-kapsam-test.py` / `marka-sayac-kapisi.py` zaten `marka_model_build`'i çağırıp
  gerçek HTML üretiyor; oradaki `ctx` kurulumunu örnek al.
  🔴 **CSS TUZAĞI:** `_shell` stili `ctx["stil_bloklari"](_MM_CSS)` ile **içerik-adresli**
  `/varlik/sayfa-<hash>.css`'e gönderir; o dosya ne yerelde ne canlıda vardır (hash yeni)
  → naif üretilen sayfa CSS'SİZ açılır, ölçüm ANLAMSIZ olur. `<link rel="stylesheet">`
  etiketini gerçek CSS metnini taşıyan satır içi `<style>` ile DEĞİŞTİR
  (`build.PAGE_CSS` + `marka_model_build._MM_CSS`).

**GEÇERLİLİK KAPISI (fail-closed, atlanamaz).** SONRA sayfasında şu üçü birden
doğrulanmadan sayı YAZILMAZ: (1) `getComputedStyle(.mm-model-btn).borderRadius === "9px"`
(CSS gerçekten uygulandı), (2) `document.documentElement.clientWidth === 375`,
(3) görünür çip sayısı **12** ve toplam çip sayısı markanın gerçek model sayısı
(`gorunur == toplam` çıkarsa katlama CSS'i uygulanmamıştır). ÖNCE sayfasında beklenen
tersidir: `gorunur == toplam` (katlama canlıda henüz yok).

- Bitince `/private/tmp/pruvo-p1-kanit/` altındaki profil + ara HTML'ler silinir,
  silindiği `ls -A` ile kanıtlanır; PNG kanıtları mimar bakana kadar bırakılır.

---

## 4. ÖLÇÜM SONUCU — KABUL 3/3 GEÇTİ

Ölçüm **yapıldı**. Koşum: `isci.sh minimax-m3 … kabul-p1-375px-tur2`
(N2B parti kapısı muafiyeti: etiket `kabul-` öneki → hüküm satırı `KOL=N2B-MUAF`).

**SONRA (dal) — 375 px iframe'e çivili, sayı+görüntü tek Chrome koşumundan:**

| marka | genişlik | çip görünür/toplam | CSS | grid | kart1-2 alt | kart3-4 alt | **1624 içi** | hüküm |
|---|---|---|---|---|---|---|---|---|
| honda | 375 | 12 / 110 | 9px | 160.5+160.5 | 1264 | 1556 | **4** | GEÇTİ |
| bmw | 375 | 12 / 104 | 9px | 160.5+160.5 | 1264 | 1556 | **4** | GEÇTİ |
| yamaha | 375 | 12 / 93 | 9px | 160.5+160.5 | 1264 | 1556 | **4** | GEÇTİ |

**ÖNCE (canlı, kusurun ölçülmüş kanıtı):** üç markada da çip katlaması YOK
(`gorunur == toplam`) ve **ilk kart 3585–4007 px'te** — yani ilk 1624 px'de **0 kart**.
ArTisT'in "ilk ekranda sıfır ürün kartı" teşhisi sayıyla doğrulandı.

Pay: 4. kart 1556'da bitiyor, eşik 1624 → **68 px**.

🔴 **Ara ölçüm (kayda geçsin, ölçüt gevşetilmedi):** ilk katlama turunda sonuç
`KART_1624_ICI = 2` idi — ikinci kart sırası **1640** px'de bitiyordu, eşiği **16 px** ile
kaçırıyordu. Kart yüzeyi küçültülmedi (görsel+fiyat okunaklılığı düşerdi); bunun yerine
mobil başlık/kutu ARALIKLARI daraltıldı ve giriş katlaması 4→3 satıra indi. Ölçüt hiç
değişmedi; kod ölçüte uyduruldu.

Üç `SONRA` PNG'sinin üçü de mimar tarafından **tek tek açılıp gözle doğrulandı** (sayılar
görüntünün içinde, 1624 çizgisi görüntüye çizili) — işçi raporuna güvenilerek kapatılmadı.
Gerekçe: aynı işçi üç ayrı turda kendi sayısı eşiği tutmazken "GEÇTİ" hükmü yazdı
(`KART_1624_ICI=2` iken "3/3 GEÇTİ"; `genislik=485` iken "kapı tuttu"). **Sayılar doğruydu,
HÜKÜM yanlıştı** — bu paketle çalışan herkes hükmü kendisi kursun.

---

## 5. MERGE ÖNCESİ ZORUNLU

**K184 BAĞIMLILIĞI KALDIRILDI (ölçüldü).** Dal ilk halinde `a15cfc83` (K184 merge)
üzerine kurulmuştu ve K184'ün TAMAMINI sürüklüyordu (`index.html` +299,
`tools/yayin-topla.py`, `talep-alanlari.js` …). KraL mimarı K184'ü `parite-ege.js`
kırmızısı yüzünden geri sarınca (`SONUC: PARITE YOK, 47 açıklanamayan / 1331 sorgu`)
`a15cfc83` ULAŞILAMAZ hale geldi. Dal `git rebase --onto origin/main a15cfc83` ile
taşındı — K184 `tools/marka_model_build.py`'ye HİÇ dokunmadığı için çakışma YOK.

Taşıma sonrası ölçüm: `origin/main...HEAD` = **0 geride / 1 ileride**, değişen dosya
**2** (`tools/marka_model_build.py`, `tools/paket-p1-marka-ilk-ekran-olcum.md`),
`index.html` / `yayin-topla.py` / `talep-alanlari.js` farkı **BOŞ**. Yani bu dal artık
K184'ü arka kapıdan yayına taşımaz ve K184'ün inmesini BEKLEMEZ.

Merge için kalan tek şart:
- §3'ün tamamı yeşil **+** §2 ölçümü 3 markada 3/3. İkisi olmadan merge YOK.
- Sıra: skill `merge-kapisi`; yeşil ışığı KraL mimarından al (başka chip'ler de aday).

## 6. AÇIK BULGU (bu iş kapsamı DIŞI, kalem sahibine)

Defterdeki **K75** aynı yüzeyi ölçüyor: `/marka/hyundai/` çipleri eksik/dağınık/kırık link
(11 çip 281 topluyor, marka 593). Bu değişiklik çip ÜRETİMİNE dokunmadı — yalnız kaçının
GÖRÜNDÜĞÜNE. K75 kapanmadan bu sayfada çip doğruluğu düzelmez; ikisi AYRI eksen.
