# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ✅ K164 KAPANDI — YAYIN ACILDI (18 Agu, `f5671d37` + `0ab9dcde`) — tam metin ARSIVDE
Kok neden sitemap DEGIL: `kart_ozeti` 11 Agu'da karta `boy_secenekleri` yaziyordu ama
`OZET_KART_ALANLARI`na eklenmemisti (ikiz tanim) — alan tele HIC cikmiyor, konum capasi KOR.
Kusur alani tasiyan ILK urun dogana kadar 6 gun uyudu. `PATOLOJIK_KAYIT=1`.
Onarim: alan sozlugun SONUNA · konum capasi artik "kartta VAR sozlukte YOK"u ALAN ADIYLA
reddediyor · yeni statik sinif kapisi `tools/ozet-alan-ikiz-test.py` (AST + mutasyon,
`serit-a3`) → alan eklendigi GUN kirmizi yanar. 🔴 Ders: ilk kirmizi ayni sinifin IKINCI
yuzeyini (`vitrin-kabul.js::edgeKart`) MASKELEMISTI — bir job'da ilk kirmizi duzelince
KALAN adimlari yeniden olc.
Kabul: `IKIZ=0 (KENDINI_TEST=5/5) OZET=0 EDGE=0 ESKIFIYAT=0 TEMSIL=0 CIKAPSAM=0` · mutasyon
`M1_IKIZ=1 M1_BUILD=1 M2=1`. CI (`0ab9dcde`): `build`+`serit-a2/a3/a4`+`hijyen-build`+
**`deploy`**+**`yayin`** success; kirmizi yalniz hijyen (K140 Rover + M3b) → yayini DURDURMAZ.
CANLI (cache-bust'SIZ): `SITE_HTTP=200 URUN_HTTP=200 OZET_SURUM=3 ALAN_SAYISI=13
SON_ALAN=boy_secenekleri BOY_KONUM=12 BOY_DEGER_VAR=EVET CANLI_TOPLAM=29038` (=`origin/main`,
EDGE BAYAT DEGIL). D1 5/5 eksen YESIL (29038, ICERIK uyusmaz=0).
ℹ️ Yerel main olcum aninda 1 commit ILERIDE (`a6246722`, baska oturumun 24 urunu, itilmemis)
— 29062 ↔ 29038 farkinin sebebi budur. Itme sahibinin.
**BEKLIYOR:** dal `k152-link-temiz` (`56269db4`) merge bekliyor · `tools/marka-uyelik-test.py`
bes oturumdur commit'siz (K136).
**OKAN'DA:** 22 Agu kimi/codex motor karari · $100 plan karari (once yanma olcumu) ·
Navlungo `il-ilce-dilim1` merge'i.
**AYRICA CANLIYA GITTI (KraL/amazing-hamilton, bu bloktan IKI KEZ dusuruldu):** K150 rc=5 ERTELENDI + kapsam kapisi (`ed47d317`) + `--mutasyon` CI kablosu (`2f87a8bc`; kosum `32071071340` `cron-nabzi` adim 7 **success**) · K148 gozcu faz-2 · K160 kilit govdesi TEK KAYNAK (repo disi, capraz 5/5). ⚠️ `b180fa1a` da "K160" diye anilmisti; K160 = BaBa'nin KILIT hukmu.

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)

- 🟠 **K165 (18 Agu — K164 teshisinin YAN BULGUSU; yayini BLOKLAMAZ ama SESSIZ):** sitemap
  `lastmod` git taramasi sure butcesini (`VARSAYILAN_SURE_BUTCESI=240.0`,
  `sitemap_damga.py:66`) dolduruyor; asimda **fail-loud DEGIL** (`:242-244` yalnizca `break`),
  cozulemeyen kayit `lastmod`SIZ kaliyor (`build.py:4153-4155`); kirmizi kosumda 13. Olcek
  buyudukce SESSIZCE buyur. Yon: esigi BUYUTMEDEN fail-loud'a bagla. `kabul:` BOS.
- 🔧 **K134 (defter kotasi SINIF kalemi; BaBa 3. kez kirmizi dedi, SPEC HAZIR):** care (`defter-rotasyon.py`) mimar kod kilidinde YASAK.
  Tam metin ARSIVDE.
  kabul: `python3 /Users/okan/dev/pruvo/tools/defter-rotasyon-test.py`
- 🔧 **K135 (17 Agu, MaCiT→KraL):** `cgt-ekle.py::fetch()` tek satir UA ile CGTrader WAF'ina takiliyor (HTTP 202 + placeholder);
  Tam metin ARSIVDE.
  Kalici `--yerel` yolu KraL'da, sonraki dilim oncesi. `kabul:` alani BOS.
- 🔵 **K136 (17 Agu, KAYIT):** ana agacta `tools/marka-uyelik-test.py` DORT oturumdur
  commit'siz (K126 "tek govde" yuklemini ham donguye geri aliyor). DOKUNULMADI.
- 🔵 **K132 (17 Agu, KAYIT — yayini BLOKLAMAZ):** `isci-tur-tavani-test.py` tek basina
  KALDI, `testler.py` icinden GECTI; celiski uretilemedi. Tam metin + kabul ARSIVDE.
- 🟠 **K139 (17 Agu, Okan emri — CANLI DURUM, ekip bilmeli):** crontab'ta 3 gorev
  yorumlandi; 181 → **25 atesleme/gun**. 🔴 ETKI: posta kutusu OTOMATIK izlenmiyor **ve
  urun partileri kendiliginden ILERLEMIYOR**. Tam metin ARSIVDE. `kabul:` alani BOS.
- 🟠 **K144 (UCUSTAKI KOSUM):** ardarda push'lar build'i `cancelled` ediyor (ARIZA DEGIL);
  hukum her turda guncel uca tasiniyor. Tam metin ARSIVDE.
  kabul: guncel ucu ICEREN kosum `conclusion=success` **VE** cache-bust'SIZ canli teyit.
- 🔧 **K140 (17 Agu — ACIK SORU MIMARCA KAPATILDI, icra kaldi):** hukum **kapinin MODEL hatasi degil, EVREN KAYNAGI hatasi**: 185 urunun 184'unde model jetonu gercek markanin YANINDA, ve `index.html:3148` cip evreni KURATORLU (model kodu CIP OLMAZ) → kapi sitede OLMAYAN bir baglanti icin sayfa istiyor.
  Tam metin ARSIVDE.
  kabul: `python3 tools/marka-invaryant-kapisi.py` — 7 model jetonu DUSMUS **VE** `Rover` DURUYOR **VE** mutasyon 4/4.
- 🔧 **K163 (17 Agu — K149'un ARTIGI; ayni fail-silent sinifi SURUYOR):** `isci-temizlik.py`
  satir **168-169'da hala ciplak `except OSError: pass`**; ayrica 45/63/125'te listeleme
  hatasi `return 0` ile **"olculemedi"yi 0 okuyor** — bu depoda yasak eksen. Yon: her kol
  ya `atlanan`'a yazsin ya fail-loud dursun; `0` yalnizca OLCULEN sifir icin.
  kabul: `grep -c "except OSError: pass" ~/.claude/cron/isci-temizlik.py` → **0** VE
  listeleme hatasinda sayac `OLCULEMEDI` isaretlesin (vaka + mutant).
- 🔴 **K162 (17 Agu — CANLI TURUN PROFILI "CANLI" SAYILMIYOR; tur cokme riski):**
  profil dizini `profil-<MODEL>-<ETIKET>` adlanirken canli kontrol `pgrep -fl isci.sh`
  ciktisinin SON token'ini (`<ETIKET>`) karsilastiriyor → eslesmiyor. Su an tek koruma
  **2 saatlik tazelik penceresi**; 2 saati asan bir tur profilini kaybedip COKER.
  Bugun tetiklenmedi (`CANLI_ETIKET=0`) ama kosul rastlantisal.
  kabul: canli tur fiksturuyle profil silinmez (vaka) **VE** mutant (eslesmeyi bozan)
  KIRMIZI yakar.
- 🔴 **K157 (17 Agu — KIMI HATTI KOK NEDEN BULUNDU, karar OKAN'DA):** `max_tokens=1`'in 200'u
  SAHTE (icerik bos, `stop_reason=null`) → gercek uretim SIFIR; `>=2` daima 403
  `permission_error`. Girdi ekseni · anahtar sinifi/uc · baslik · model/stream · hiz penceresi ·
  aylik tavan ELENDI. Kimlik ucu anahtarin Okan'in KENDI hesabinda oldugunu dogruladi.
  🔴 "Haftalik dilim doldu" teshisi CURUDU: panelde `5 saatlik Kod %0` · `7 gunluk Kod %0`
  → **panel ile kapi AYNI SAYACI GOSTERMIYOR**. Kalan hukum: saglayici tarafinda hesap/kota
  durumu ya da hatasi → hamle PARA DEGIL, ekranla birlikte destege sormak (Okan kapisi).
  Yanlislanabilir kanit AYAKTA: `~/.claude/cron/kimi-nabiz.py` gunde 2x GERCEK is atar
  (5/5 vaka, 2/2 mutasyon); ilk olcum `2026-08-17T15:51Z SAGLIK=KIRMIZI 403`. Tam metin
  ARSIVDE + DEVAM.md git gecmisinde.
  kabul: 22 Agu'da `kimi-nabiz.log` **SAGLIK=YESIL** → kalem kapanir; hala KIRMIZI ise
  saglayici arizasi teyitlenir, karar Okan'a doner. ⚖️ Okan emri (17 Agu): kimi kalemi kapali,
  **yeni olcum turu ACILMAZ**; motor plani 20 Agu'ya kadar codex (alt model), sonra m3.
- 🔵 **K158 (17 Agu, TASARIM ACIGI — KAYIT):** isci tarayicisi YALNIZ kimi motorunda var
  (m3'te yok) → kimi dustugunde paneli okuyacak yol da kapaniyor; tek tarayicili motorun
  dususu TESHIS yolunu da kesiyor. Yon: tarayiciyi motordan bagimsiz kola tasi. `kabul:` BOS.
- 🔧 **K146 (17 Agu — nobet dosyalari YEDEKSIZ):** `~/.claude/cron/` versiyon kontrolu
  DISINDA → curutucu, iscinin kabul-testi fiksturunu MESRU mu degistirdi OLCEMEDI
  (eksen KOR). Yon: otomatik yedek + `yedekle.py` kapsam teyidi. `kabul:` alani BOS.
- 🔴 **K141 (17 Agu — OLCULEMEYEN NOBET, sinif kalemi):** `kapi-envanteri.py` main'de DE kirmizi: `mimar-icra-kapisi` + `mimar-kod-kilidi` "NOBETTE degil — reddetmesi gerekeni REDDETMEDI".
  Tam metin ARSIVDE.
  muafiyet kolundan BAGIMSIZ altsurecte kossun. `kabul:` alani BOS.
- 🔧 **K142 (17 Agu, KraL olctu → MaCiT):** pre-push kapak taramasi **14 R2 anahtari `NoSuchKey`** buldu, hepsi `c3d*` onekli (Cults3D partisi).
  Tam metin ARSIVDE.
  kutuya yazildi. Sahibi veri seridi. `kabul:` alani BOS.
- 🔧 **K118:** pre-push sizinti kapisi bicim-kaydiran urun partisinde butceyi yapisal
  asiyor (tam-dosya diff). Yon: butce buyutmek DEGIL, `urunler.json`'u icerik ekseninde
  AYRI ele almak. `kabul:` alani BOS.
- 🟠 **Navlungo dilim-1 MERGE BEKLIYOR:** dal `il-ilce-dilim1` (`5d57c918`); Okan kapisi.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🟠 **K152 (17 Agu — ⚖️ OKAN KARARI KAPSAMI BELIRLEDI; onceki iki hukum de DUSTU):** Okan (birebir): **"sitede bulunan tum urunler satilabilir.
  Tam metin ARSIVDE.
  kabul: `python3 tools/koken-bul.py --eksik` → `EKSIK` DUSER **VE** `--kendini-test` rc=0.
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle
  evreniyle AYNI DEGIL; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti `norm`/`ham`
  ekseninde ayrisiyor. · 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR — peer'in dusurulen commitsiz isi
  (deploy.yml serit tasima · marka-uyelik-test.py · kalibrasyon 4 dosya). Sahibi uygulayacak.
- 🟡 **Kosum sinyali kirli (olculdu):** `hijyen-a2`/`a3` yayin zincirinde DEGIL ama genel
  `conclusion`'i `failure` yapiyor. Kural: genel hukme degil **is bazinda** bakilir
  (hijyen kirmizisi gurultu DEGIL — K125'i o buldu). Tam metin ARSIVDE.
- 🔧 **K151 (yedek dusus beyani her rotasyonda ELLE yeniden yaziliyor; sinif):** karantina
  cozuldu (dususler MESRU olcuLdu, arsivler dususten FAZLA buyudu). Beyan TAM boyuta bagli
  → 3. tekrar. **Yon:** ROTASYON CIFTI invaryanti. Tam metin ARSIVDE.
- 🔧 **K161 (17 Agu — marka dili KIP ekseni KAPANDI, KALINTI ayri parti):** kapi kapsaminda ama Okan onayli kalip tablosu DISINDA kalan **ELLE=10** kayit + karma cumle yuzunden bilerek atlanan 1 kayit. Kural dokumu, id'ler ve gerekce POSTA KUTUSUNDA. kabul: `python3 tools/denetim-kapisi.py --tum-katalog --envanter` vurus ≤21.



## OKAN'DA

- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
  (16 Agu: rotasyon bu maddeyi bir kez arsive supurdu — parantezdeki kapali kalem atfi
  yuzunden; geri konuldu, sinif kusuru K128.)
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.

## KOSUYOR (baska mimarlar)

K152: `xenodochial-bardeen` TEK YAZICI (gizli kayit duzlemi, flock + public sha256 nobeti);
worktree'sinde main'de OLMAYAN 1 commit var → temizlikte bilerek ATLANDI, bundle ister.
(`musing-shaw` ve MaCiT'in peugeot/chevy worktree'leri kapandi; K153 blokeri kalkti.)
## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali · 17 Agu ROTASYON-2 (K147 · K154 · K155 · K156 · K133 · K91 · K101 · K103 · K113-119 · K120 · K123-125 · K128 · K121 · K127 · K138 · K137).