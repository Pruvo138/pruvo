# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## OTURUM — 1 Agu 2026 aksam (KraL · yayin hatti + ikinci denetim turu)

### 🔴 CANLIYA GITTI — YAYIN HATTI TIKANMISTI, ACILDI (`89a72022`)
Olculdu: son basarili deploy 19:17'de kalmis; o saatten sonra main'e **20 commit** gitmis ve
**6 kosum ust uste dusmus**. Canli site ~1,5 saat bayat kaldi, 36 urun D1'de VAR ama sayfalari
**HTTP 404** veriyordu (parite testleri bu yuzden "OLCULEMEDI" donuyordu — kirmizi degil).
Sebep urun verisi DEGIL, bu oturumun kendi kapisiydi: `ticari-hal-kapisi.py` "duzeltme ONCESI
davranis"i **HEAD**'den okuyordu; duzeltme main'e girince HEAD artik duzeltilmis dosya oldu ve
kapi **kendi kapattigi deligi "hala acik" sanip** kirmizi yandi. Bu, 31 Tem'deki ayni sinifin
IKINCI vakasi — o zamanki ders "ana hat kolunu ayir" idi, yeni kapi baska yoldan ayni yere dustu.
Onarim: ONCE kanit artik git gecmisinden degil **repoya gomulu fiksturden** turuyor (sha256 pinli;
gecmis erisilebildiginde gercek tarihsel dosyayla bayt-esit dogrulaniyor). Sabit commit hash'i
cozum DEGILDI: `--depth 1` klonda kapi fail-closed dusuyordu, olculdu. Is akisina DOKUNULMADI.
Olcme gucu azalmadi, artti: **32 -> 34 iddia** (sig klonda 33), mutasyon 8/8, once-kirmizi
26 bulgu; fikstur silinince/kurcalaninca/bugunku kodla degistirilince ucunde de kirmizi.
Kabul: run 30711392211 build+deploy+yayin ucu de basarili · D1 **16873, yayinda 16873, TASLAK 0** ·
bagimsiz canli teyit: 404 veren urun sayfasi artik **200**, ana sayfa damgasi taze.
Ayni tuzak diger kapilarda arandi: dort kapidaki `git show HEAD:` kullanimi **mesru baska desen**
(calisma agaci ↔ HEAD tabani); bu hata sinifinin ikinci ornegi YOK.

### CANLIYA GITTI — OLCUM ARACI ARTIK YANLIS SUCLAMIYOR (`09b76410` + `467f8fa8`)
Iki kardes faz3 araci ayni sebebe (uc cevap vermiyor) FARKLI hukum veriyordu: biri durustce
"OLCULEMEDI", digeri "SAYFALAMA/SIRA BOZUK" diye kirmizi yakiyordu. Yanlis suclama sinifi —
ve bugun bedeli olculdu: yayin hatti tam da "olculemedi"yi kirmizi sayan bir kapi yuzunden
tikandi. Onarim: ariza sinifi TEK yerde belirleniyor, kardes aracin cikis kodu sozlesmesi
birebir alindi (tasima hatasi/JSON olmayan yanit/eksik alan -> OLCULEMEDI 2; ucun kendi
bildirdigi hata -> 1 ama "sayfalama" diye raporlanmaz; mukerrer/sayi/sira ayrismasi -> BOZUK 1).
Kabul UC senaryoyla olculdu: uc yok -> rc=2 ve ciktida "BOZUK" kelimesi HIC gecmiyor (ilk
kosumda banner sizdiriyordu, nobetci yakaladi) · dogru uc -> rc=0, gercek canli uca karsi
7 gorunum/16873 urun · **bozuk uc -> rc=1**, uc ayri bozukluk (sayfa sinirinda urun atlama,
sira takasi, mukerrer id) ayri ayri yakalandi. Kismi halde OLCULMUS ayrisma baskin: 1 gorunum
olculemedi + 6 ayristi -> rc=1; "olculemedi" hicbir yolla yesil uretmiyor. Yeni nobetci CI
kapsam kapisinda kapsamsiz yaniyordu, serit B'ye baglandi ve beyan edildi. Kardes arac
DEGISMEDI (kendi nobetcisi 6/6).

### CANLIYA GITTI — ALTKATEGORI: IZINLI KUME + SESSIZ AYRISMA KAPISI (`235fb25a` + `d379ffb7`)
Okan onayiyla izinli altkategori kumesine `Elektrik` eklendi (**11 -> 12**); kardes mimarin
30 urunluk hazir partisi bunu bekliyordu, ayni gece yazildi ve senkron teyit edildi.
Kume TEK kaynakta, ikiz tanim yok. Kapi gevsemedi: yakin yazimlar (`Elektrikk`, `elektrik`)
hala rc=5, once-kirmizi gercek (ayni cagri eskiden rc=5 ile reddediliyordu).
Is sirasinda **daha eski, sessiz bir kusur** bulundu ve kapatildi: uyelik testi `strip()`
sonrasi yapildigi icin bosluklu deger KABUL ediliyordu, ama yazma yolu kataloga HAM,
D1 yolu KIRPILMIS metin gonderiyordu — yani katalog ile D1 sessizce ayrisabiliyordu (site ile
bot ayni urunu farkli yazimla gorebilirdi). Bu, kume genislemesiyle gelmedi, 11 degerin
hepsinde vardi. Secilen yol **fail-closed**: kanonik olmayan deger artik REDDEDILIYOR
(sessizce duzeltilmiyor), ve iki yol tek fonksiyondan turuyor -> ayrisma insaatan imkansiz.
Mevcut veri kesilmedi (935 dolu kayitta 0 bosluklu). Kapi **35 -> 42 iddia**, mutasyon **17/17**.
Ikinci kalem: bir mutasyon capasi BAYATLAMISTI (gorselsiz urun isi izinli kumeye alan ekleyince
capa kaydi) ve bir eksenin oldurucu gucu ARTIK OLCULMUYORDU — sessiz degil gurultulu
basarisizlik verdigi icin "yakalandi" sanilabilirdi. Capalar desene cevrildi; capa kayarsa
tur artik ADLI hatayla kirmizi yaniyor (`CAPA BAYAT` / `MUTANT UYGULANMADI` + fiilen-uygulandi
sayaci), uc ayri bozma denemesinin ucunde de rc=1.

### KARARLAR (bu tur)
- Ege kapisinda sirket sesi birinci cogulun da yanmasi KABUL EDILDI: o metin Ege'ye kendi
  bilgisi olarak besleniyor, orada "belirleriz" demek Ege'ye vaat ettirmektir. Kapi
  musteriye gorunen sayfalari okumaz; yasal metinlerde olcum 0.
- Iade kargo bedeli metne YAZILMADI — ticari karar Okan'da; kapi, cevap gelmeden o cumlenin
  yazilmasini kirmizi yakiyor.
- Is bolumu (Okan kurali): is kimin duzlemindeyse o yapar; baskalarini da etkileyen
  degisiklikte karar verici mimar devam eder. Siparis ucunun olcum ekseni kardes mimara
  devredildi, Ege tarafi sahibinde kaldi, sema/odeme/merge bende.

### BEKLIYOR
⚠️ Budama turu bu bolumu de arsive tasidi (lossless, kayip 0 — ayrinti arsivde). ACIK olan
kalem arsive inmez; guncel hal mimar eliyle asagiya yeniden yazildi.

- 🔴 **HESAP TASINMASI ACIK.** 23 Tem'deki MAKINE gocu bitti; envanterdeki is AYRI:
  **hesap devirleri** (kod deposu, edge saglayici, calisma alani, odeme, mesajlasma,
  not/CRM, model saglayici). Migration Assistant hesap devretmez. Olculdu: mevcut
  oturumlar hala eski hesapta -> **hic baslamamis.**
  ⚠️ Ozet listedeki "19" EKSIK SAYIM: tablolardaki atamalar **24 ayri eyleme** iniyor.
  ✅ Bloklayici **6 -> 5**: "yedeksiz gizli dosyalari eski makineden aktar" KAPANDI
  (19 kalemin 19'u da bu makinede; 13'u goc oncesi tarihli, icerik ACILMADI).
  🔴 Yerine gecen risk: iki sigorta paketi (~33 MB) YALNIZ bu makinede. **Karar:**
  paylasilan yedege GIRMEYECEK (temizlik oncesi icerik tasiyorlar) — otomatik yedegin
  degil, tasinmanin **ELLE** kalemidir, sifreli elden gecirilir.
  Envanter + yedek raporu `raporlar/` altinda: gitignore'lu, yedek kapsaminda, sha256
  ozdesligi ve yedek tazeligi dogrulandi.
  ✅ Envanterin "yedekte YOK" hukmu ve goc dogrulayicisinin yanlis alarmi bu oturumda
  KAPANDI: dogrulayici artik **rc=0**, ev sayisi **4 -> 6** (iki ev hic dogrulanmiyordu),
  yesil 62 -> 80, hic dusmedi. Kayit disi kancanin yeni makine tasinabilirligiyle ilgili
  risk kapatildi; ayrintisi git disi arsive tasindi.
  ⚠️ Kalan tek kalinti: eski bir `pre-push` yedegi — siniflandirmasi bende, icerigi acilmadi.

### 🔴 OKAN'DA BEKLEYEN
- **Hesap tasinmasinin 5 bloklayici kalemi** (yukarida) — hicbiri kodla acilamaz.
- **Siparis onay e-postasinin gercek govdesi** hic goruLMEDI: yan etkisiz yolu yok,
  dusuk tutarli GERCEK bir siparis gerekir. Uretilen mantik offline rc=0, ama uctan uca
  "musteriye giden metin" **olculmemistir** — yesil demiyorum.
- ✅ KARAR ALINDI: iade kargo bedeli icin sozlesmeye CUMLE YAZILMAYACAK; sonucu bilincli,
  bedel yasal olarak bizde. Eksiklik DEGIL, karardir — "unutulmus" diye tamamlanmasin.

### KARDES MIMARLARDA
- **HocA — UCUNCU denetim yapildi, MERGE YINE YOK (dal `wa-siparis-onarim`).** Uc ESKI acik
  bagimsiz olcumde KAPANDI: bos dis kimlikte 12/12 cagri reddediliyor ve **0 siparis** aciliyor
  (eskiden 4 cagri = 4 siparis) · 5'li GERCEK yarista tek satir, 500 yok · benim kacirdigim uc
  para mutantinin ucu de artik yakalaniyor. Site kanali regresyonsuz, yetki 8 senaryoda fail-closed.
  🔴 **Ama bu teslimin EKLEDIGI savunma yeni delik acti:** telefon genis kabul edilip (onekli/
  oneksiz/bosluklu hepsi gecerli) kimlik TAM DIZE karsilastiriliyor — 7 yazimin 4'u ayni musteriyi
  yabanci sayip reddediyor ve onerilen care izlenince **ayni musteriye 2 siparis** aciliyor.
  Yani mukerrer siparisi onlemek icin eklenen savunma mukerrer siparis uretiyor; bu girdide yeni
  kod eskisinden KOTU. Recete verildi (kanonik karsilastirma + onek farki fiksturu). Ayrica bir
  para mutanti hala kaciyor (govde ve kalem tutari ayni anda sifirdan buyuk olan tek fikstur yeter).
  Kapanip mutant yakalama tam olunca merge + sema gocu + deploy sirasi BENDE.
- **HocA (ikinci kalem, ONCELIKLI):** kategori sayfasindaki altkategori filtresi icin uc kart
  sozlesmesi genisleyecek — Okan'in bekledigi gorunur is. Sema isi YOK, D1 kolonu var ve dolu.
- **ArTisT:** WhatsApp kanalinin GA4 olcum ekseni devredildi; beni bloklamiyor.
- **MaCiT:** gorselsiz parti icin YESIL verildi (`ed135702`); katalogda henuz gorselsiz
  urun YOK, yani ilk parti bu yolun canli ilk kullanicisi olacak.

### KOSUYOR
- Bu oturumun delege ettigi TUM isler kapandi, merge edildi, dal/worktree temizlendi.
  Kalan iki worktree BASKA OTURUMLARIN — dokunulmadi.

## TABAN (yeniden olc, ezberleme)
Bu bolume SAYI YAZMA — gun icinde bayatliyor ve bayat sayi yanlis guven veriyor
(bugun olculdu: katalog tek oturumda 16589 -> 16672 hareket etti, elle tutulan agac
listesi de tutmuyordu). Tek dogruluk kaynagi kosulan komut:
- Katalog / D1: `python3 tools/d1-sync.py --durum`
- Calisma alani: `git -C /Users/okan/dev/pruvo worktree list`
- Kapilar: `python3 tools/durum.py`
