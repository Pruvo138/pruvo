#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN GECIKME NOBETCISI — "canli, main'den NE KADAR geride?".

NEDEN VAR (1 Agu 2026, OLCULDU — bu nobetci bir olayin faturasidir)
====================================================================
Yayin hatti bir kapi yuzunden tikandi ve **20 commit birikene, 6 kosum ust uste
dusene ve canli ~1,5 saat bayatlayana kadar KIMSE FARK ETMEDI**. Fark edilis bicimi
TESADUFTU: parite testi "OLCULEMEDI" dedi, mimar sebebini kovaladi. O gunun kosum
tablosu (son 15 kosum): 3 success / 5 cancelled / 5 failure.

Ikinci risk ayni olcumde gorunur oldu: build ~28 dk surerken push'lar 3-8 dk arayla
geliyor; her yeni BEKLEYEN kosum onceki bekleyeni iptal ediyor. Yeterince sik push
gelirse hicbir kosum tamamlanamaz (**ACLIK**) — hat "kirmizi" bile yanmadan yayin
durur. Yani IKI ayri ariza sinifi var ve ikisi de sessizdir:

    TIKANMA : kosumlar DUSUYOR      (failure zinciri; hat kirmizi ama kimse bakmiyor)
    ACLIK   : kosumlar IPTAL EDILIYOR (cancelled zinciri; hicbiri tamamlanmiyor)

Bu nobetci ikisini de AYRI AYRI olcer ve tek bir soruya sayiyla cevap verir:
"canli yayin, main'in kac commit ve kac dakika gerisinde?"

🔴 "YAYIN INDI MI" IS DUZEYINDE OLCULUR — KOSUM DUZEYINDE DEGIL (1 Agu 2026, OLCULDU)
=====================================================================================
Bu nobetcinin ILK gercek kullaniminda YANLIS ALARM verdigi olculdu: "TIKALI, canli
main'den 3 commit geride, en eski bekleyen 85 dk" dedi; oysa canlinin `last-modified`
damgasi 20:50 idi ve o turda yayinlanan icerik CANLIDA GORUNUYORDU. Sebep: nobetci bir
kosumu "yayinladi" sayarken kosumun GENEL `conclusion`'ina bakiyordu.

Olculen govde (kosum 30716502665, sha aa114660): genel `conclusion` = **failure**,
CUNKU yayini bloklaMAYAN `serit-b` isi dustu. Ayni kosumda:
    build=success · deploy=**success** · yayin=**success**
Yani icerik INMISTI. Ayni gun ikinci ornek: kosum 30715829554 (d4806461) — yine genel
`failure`, yine deploy+yayin success.

Bu depoda `deploy.yml` BILEREK boyle kurulmustur: `serit-b` yayini bloklamaz
([[kapi-birikimi-yayin-gecikmesi]] — bloklayan kapi yayini 1,5 saat durdurdu). Yani
"genel conclusion = failure" bu hatta yayinin inmedigi ANLAMINA GELMEZ ve o alani
yayin kaniti saymak, aracin OLCMEDIGI bir sey hakkinda hukum vermesidir.

Onarim: her tamamlanmis kosum icin `.../actions/runs/<id>/jobs` sorulur ve
    ETKIN SONUC = "success"   <=> `deploy` isinin conclusion'i success
                = "yayinsiz"  <=> kosum success ama `deploy` success DEGIL (or. skipped)
                = kosumun kendi conclusion'i (failure/cancelled/...) aksi halde
Zincirler ve "son basarili yayin" ARTIK bu etkin sonuc uzerinden sayilir.

🔴 KORELME KARSI-OLCUMU (ayni gun, ayni veri): 17:01-17:43 arasi BES ardisik kosumda
`build` DUSTU ve `deploy` HIC KOSMADI (`deploy=skipped`) — 20 commit birikti. Onarimdan
sonra da bu senaryo TIKALI vermek ZORUNDADIR; fikstur `bugun-build-dustu.json` bunun
kanaridir. Iki fikstur bu iki ekseni birbirine kilitler: `bugun-serit-b-dustu.json`
(genel failure ama deploy=success -> AKIYOR) ve `bugun-build-dustu.json`
(genel failure, deploy=skipped -> TIKALI).

⚖️ `deploy` MI `yayin` MI YETKILIDIR: SITEYI canliya koyan is `deploy`'dur; `yayin` isi
deploy'dan SONRA kosar ve D1'deki taslaklari yayina alir ([[ege-d1-bagimliligi]]).
`yayin` duserse SITE CANLIDIR ama Ege yeni urunleri goremez. Bu yuzden "canli, main'in
kac commit gerisinde" sorusunun yetkilisi `deploy`'dur; `yayin` isinin sonucu OLCULUR ve
raporda AYRI bir bozulma satiri olarak GORUNUR — ama site tazeligi hakkinda hukum
vermez (aksi halde "site canli" iken TIKALI diyen YENI bir yanlis alarm sinifi dogardi).

IS SORGUSU BUTCESI (olculdu 1 Agu 2026): kosum listesi 1,7 sn · her `jobs` cagrisi
ort. 1,0 sn. Tarama ILK yayinlayan kosumda DURUR -> saglikli halde 1 ek cagri. Tavan
IS_SORGU_TAVANI=8 (=> ~9,7 sn ust sinir); tavana dayanilmasi zaten 8 ardisik
yayinlaMAYAN kosum demektir ve o hal her esigin USTUNDEDIR (TIKALI/ACLIK).

🔴 BAGIMSIZLIK — NEDEN CI'DA KOSMAZ
===================================
Bir yayin-gecikme nobetcisi YALNIZ CI icinde kosarsa, hat tikandigi anda O DA KOSAMAZ:
tam ihtiyac duyuldugu dakikada susar. Bu yuzden:
  * ELLE kosulur   : python3 tools/yayin-gecikme-nobeti.py
  * PANODA gorunur : tools/durum.py bolum 9 (pano zaten her oturum basi okunur)
  * deploy.yml'e BAGLANMAZ. deploy.yml'de yalniz bu dosyanin AGSIZ fikstur kabulu
    (`--kendini-test`) kosar — olcumun kendisi degil. Boylece nobetci, olctugu
    hattin saglikli olmasina BAGIMLI DEGILDIR ve bu betik hicbir kosulda yayini
    BLOKLAYAMAZ (bir kapi degil, bir NOBETCI'dir).

🔴 AG YOKSA YESIL DEME — VE TERSINI DE YAPMA
============================================
`gh` yoksa, yetki yoksa, API hata verirse ya da govde anlasilamazsa sonuc
**OLCULEMEDI**'dir (rc 2): YESIL DEGIL. Ama bu ev bunun TERSINI de olctu — bir kapi
"olculemedi"yi KIRMIZI sayip yayini 1,5 saat tikadi. O yuzden OLCULEMEDI burada:
  * asla "AKIYOR" uretmez (rc 0 vermez),
  * ama bir KAPI degildir: hicbir is akisini bloklamaz, panoda ⚪ olarak gorunur.

🔴 YAS TABANI KOSUMUN BASLANGICI DEGIL, YAYIN ANIDIR (2 Agu 2026, OLCULDU)
==========================================================================
Ilk hal tabani `son_basarili.run_started_at` (kosumun BASLADIGI an) aliyordu. Oysa
kosum baslar, ~24 dk build kosar ve ancak ondan SONRA yayinlar: olculen ornek — kosum
30750470532 13:41:34'te BASLADI, `deploy` isi 14:29:21'de BITTI (47,8 dk fark). Taban
baslangic olunca bir sonraki dongunun yasi, olcum baslamadan ONCE, onceki kosumun TUM
suresini tasiyor: yapisal alt sinir ~ (onceki kosum suresi + mevcut kosum suresi).

Olculen fatura (2 Agu, 40 yayin dongusu, ~27 saat — asagidaki taban olcumunun ta kendisi):
    ESKI taban (run_started_at) : ortanca 46,0 · p90 75,0 · max 491,7 dk
    YENI taban (yayin ani)      : ortanca 25,0 · p90 43,7 · max 464,5 dk
Ayni gunun en keskin ornegi: kosum 30747898143 dongusu ESKI tabanla 75,0 dk (= o gunun
TIKALI esigi, KIRMIZI), YENI tabanla 26,6 dk (YESIL). Hat bozuk DEGILDI. Fikstur
`bugunku-kuyruk-saglikli.json` bu dongunun GERCEK govdesidir ve bu ekseni kilitler.

Taban artik `deploy` isinin `completed_at`'idir: siteyi canliya koyan is bittiginde
icerik INMISTIR; o andan onceki bekleme o dongunun degil, ONCEKI dongunun hesabidir.

🔴 TABAN DUZELMESI BIR EKSENI KORELTIR — O YUZDEN IKINCI EKSEN VAR
==================================================================
Yas her yayinda sifirlanmaya basladigi icin "kosum BASLADI ama HIC BITMIYOR" sinifi
zayiflar; ustelik yas ekseninin TAMAMI `ahead_by > 0` kapisinin ARKASINDADIR (bekleyen
commit yoksa yas hic olculmez). Yani takilan bir kosum, bekleyen icerik olmadigi surece
yas ekseninde SONSUZA KADAR gorunmez.

Bu yuzden AYRI bir eksen olculur: KOSUM OMUR TAVANI — tamamlanmamis (kosan/bekleyen) bir
kosumun `run_started_at`'tan bu yana gecen omru. Bu eksen `ahead_by` kapisinin ONUNDEDIR
ve yas ekseninden BAGIMSIZ hukum verir; ikisi ayni siniftan (TIKALI) olsa bile gerekce
satirlari AYRIDIR ve `olcum["eksenler"]` her ekseni TEK BASINA raporlar
([[hukum-yanlis-birimde]]: toplu sonuc tekil ekseni gizlemesin).

ESIKLER — HEPSI 2 Agu 2026 OLCUMUNDEN (son 100 deploy kosumu, ~27 saat)
=======================================================================
Olculen taban (99 tamamlanmis kosum · 41 yayin (`deploy`=success) · 40 dongu):
  * YAYIN ANI TABANLI dongu yasi (n=40): min 18,9 · ortanca 25,0 · p90 43,7 dk.
    Kuyrugun tamami: 51,8 (17 commit'lik patlama) · 70,0 ve 76,9 (1 Agu'nun IKI GERCEK
    tikanmasi) · 464,5 (gece boyu push gelmeyen pencere — bkz. asagidaki kalinti sinif).
    Yani SAGLIKLI tepe 51,8'de biter, GERCEK olaylar 70 dk'dan baslar.
  * KOSUM OMRU (tamamlanmis 99 kosumun `updated_at - run_started_at`'i):
    ortanca 13,0 · p90 36,8 · max 49,1 dk. `build` isi (41 yayinlayan kosum):
    ortanca 22,6 · p90 23,5 · max 25,2 dk.
    ⚠️ BU SATIR ARTIK BAYATTIR — EKSEN 2 tabani 14 Agu 2026'da YENIDEN OLCULDU
    (asagidaki "EKSEN 2 TABANI BAYATLADI" bolumu). Tarihsel kayit olarak durur.
  * ZINCIR dagilimi (1 Agu olcumu, DEGISMEDI): IPTAL zincirleri [5,4,3,3,3,2,...] — 6 ve
    ustu HIC gorulmedi. HATA zincirleri [10,5,3,2,1,...] — 4 ve ustu yalniz IKI kez,
    ikisi de gercek tikanma.

Secilen degerler ve TEK CUMLE gerekceleri:
  GECIKME_YAS_DK   = 50  — olculen SAGLIKLI tepenin (51,8) hemen ALTI, p90'in (43,7)
                           USTU: UYARI seviyesi, alarm degil (40 dongunun 4'u asar).
  TIKALI_YAS_DK    = 65  — saglikli tepenin (51,8) USTUNDE, olculen GERCEK olaylarin
                           (70,0 · 76,9) ALTINDA: 40 dongunun 3'u asar, ucu de gercek
                           olay ya da beyan edilmis kalinti siniftir.
  KOSUM_OMUR_TAVANI_DK = 128 — NORMAL TABANA gore (14 Agu 2026 yeniden olcumu, Y1):
                           olculen post-olay normal omur max 86,6 dk'nin ~1,5 kati.
                           8-10 Agu olay penceresindeki GERCEK takilmalar (143,5 / 169,1
                           dk) hala yakalanir (128 < 143,5); normal kosumlar artik alarm
                           URETMEZ. Eski 75, 2 Agu'nun bayat 49,1 dk tabanindan turemisti.
  TIKALI_HATA_ZINCIR = 4 — olculen gurultu tavani 3 ardisik hata; gercek tikanmalar 5 ve
                           10 zincirdi.
  ACLIK_IPTAL_ZINCIR = 6 — 23 saatte olculen EN UZUN saglikli iptal zinciri 5; eszamanlilik
                           iptali NORMAL bir olaydir, alarm ancak zincir tavani asinca dogar.
  GECIKME_BIRIKME    = 12 — olculen dongu basi birikme: ortanca 3 · p90 7 · max 17;
                           12 saglikli p90'in cok ustu, olculen tepenin altidir.

🔴 EKSEN 2 TABANI BAYATLADI — SABIT DEGIL, TABAN YANLISTI (14 Agu 2026, OLCULDU)
==============================================================================
14 Agu'da nobetci EKSEN 2'den SAHTE KIRMIZI yakti: NORMAL (basarili) kosumlar 75 dk
esigini asiyordu (son 3 gunun her birinde 2-4 kosum; max 82,9-86,6 dk). Kok neden SABIT
degil TABANDI: 75, 2 Agu'da olculen `OLCULEN_KOSUM_OMRU_MAX_DK = 49,1` tabaninin ~1,5
katiydi; o tarihten sonra yayin zincirine `serit-a3`/`serit-a4` kollari eklendi, zincir
YAPISAL olarak uzadi, taban bayat kaldi.

YENIDEN OLCUM (14 Agu 2026, `gh api` ile deploy.yml/main, ~400 kosum cekildi):
  * PENCERE: son 7 gun tamamlanmis kosum; TABAN KUMESI = `conclusion == "success"` olan
    121 kosum (basarisiz/iptal kosum SAGLIKLI omur TANIMLAMAZ — eski tabanin kurali AYNI).
  * OMUR dagilimi (basarili, `updated_at - run_started_at`): post-olay NORMAL max 86,6 dk.
    Ham 7 gunluk basarili max 117,1 dk'dir ama o kosum 8-10 Agu OLAY PENCERESININ
    icindedir (kuyruk birikimi) — Y1 geregi taban NORMAL'e gore kurulur, olaya gore DEGIL.
  * GERCEK takilmalar (8-10 Agu olay penceresi): 143,5 ve 169,1 dk (olay aninda `simdi -
    run_started_at` ile gozlenen tamamlanmamis kosum omurleri).
  * TURETME (kural DEGISMEDI): 86,6 x ~1,5 = 129,9 -> KOSUM_OMUR_TAVANI_DK = 128.
    128 < 143,5 -> gercek takilmalar hala yakalanir; 128 > 86,6 -> normal kosumlar artik
    alarm URETMEZ. TAVAN ASAN NORMAL (yeni tavanla) = 0.

🔴 EKSEN 3 — YAYINSIZ ZINCIR (5 Agu 2026, OLCULEN SESSIZLIK: 74 DK YAYIN DURDU, ALARM YOK)
==========================================================================================
4/5 Agu gecesi `a1b50214` bir kapiyi kirmizi yakti; `deploy: needs` zinciri geregi IKI
ardisik kosumda `deploy` SKIPPED kaldi ve yayin 74 dakika durdu. Bu nobetci o gece HER 15
DAKIKADA bir kostu (paket-tazelik-alarmi.yml :: yayin-nabzi) ve **hicbir eksen atesmedi**.
Tik tik yeniden kuruldu (scratchpad/yz/tik-sim.py, gercek kosum govdeleri):

    tik      zincir  yas     zincir>=4 (TIKALI_HATA)   yas>=65 (TIKALI_YAS)
    23:58      0       0 dk    sessiz                   sessiz
    00:13      0       1 dk    sessiz                   sessiz
    00:28      1      16 dk    sessiz                   sessiz
    00:43      1      31 dk    sessiz                   sessiz
    00:58      1      46 dk    sessiz                   sessiz
    01:13      2      61 dk    sessiz                   sessiz     <- son tik; 01:16'da acildi

Yani iki hizli eksenin IKISI DE bu sinifi kaciriyordu: hata zinciri esigi (4) olaydan
IKI KAT buyuk, yas esigi (65 dk) ise olay 74 dk surerken ANCAK 01:17'de dolacakti — hat
01:16'da kendiliginden acildigi icin o tik hic gelmedi. "Esik dogru olay icin yandi" bile
denemez: HIC yanmadi.

🔴 IKI BIRIM KARISMISTI ([[hukum-yanlis-birimde]]): `OLCULEN_SAGLIKLI_HATA_TAVANI = 3`
1 Agu'da KOSUM DUZEYI `conclusion` uzerinden olculmustu; `ardisik_hata` ise 1 Agu'daki
is-duzeyi onarimindan beri ETKIN SONUC uzerinden sayiliyor (deploy=success ise kosum
`failure` olsa da zincir KIRILIR). Ham kosum zincirinde "gurultu" olan halkalarin cogu
etkin zincirde ZATEN YOK; yani 4 esigi, artik olcmedigi bir dagilimdan miras kalmisti.

OLCUM (5 Agu, son 7 gun: 607 deploy kosumu / 606 tamamlanmis / 348 yayin · 651 alarm tigi
yeniden kuruldu; `yz/cek.py` + `yz/tik-sim.py` sruculeri):
  * ETKIN sonuc dagilimi: success 348 · failure 90 · cancelled 168.
  * "yas >= 50 dk (bekleyen icerik yaslanmis)" olan HER tikte yayinsiz zincir ZATEN >= 2
    idi: zincir>=1 kurali ile zincir>=2 kurali AYNI 6 epizodu uretti. Yani 2 esigi
    KAPSAM KAYBETTIRMEZ ama tek gurultu kosumuna karsi ikinci bir teyit ISTER.
  * ALARM HACMI (651 tigin 579'unda bekleyen icerik vardi):
        zincir>=2 TEK BASINA          32 tik · 17 epizot (2,51/gun)  <- GURULTULU
        zincir>=2 VE yas>=50 dk        8 tik ·  6 epizot (0,89/gun)  <- SECILEN
        zincir>=4 (bugunku esik)       5 tik ·  3 epizot (0,44/gun)  <- bugunku olayi KACIRIR
        yas>=65 (bugunku esik)         2 tik ·  2 epizot (0,30/gun)  <- bugunku olayi KACIRIR
  * SAHTE ALARM: secilen kuralin urettigi 6 epizodun ALTISI DA gercek yayin durmasidir
    (her birinde >=2 ardisik yayinlaMAYAN kosum VE >=50 dk bekleyen icerik); is duzeyinde
    tek tek dogrulandi: 08-01 15:13 · 08-01 17:58 (bes ardisik build hatasi) ·
    08-02 08:28 (2 hata, 73 dk yayinsiz) · 08-02 19:28 (2 hata, 58 dk) · 08-04 00:43 ·
    08-05 01:13 (BU OLAY). **Sahte alarm: 0/6.**
  * zincir>=2'yi TEK BASINA almanin bedeli: 11 ek epizot, hepsinin yasi 50 dk'nin ALTINDA
    ve hepsi kendiliginden acildi -> hicbiri yeni bir gercek olay YAKALAMADI, yalnizca
    ayni 6 olayi daha erken ilan etti. Yanlis alarm = kapatilan nobetci
    ([[kapi-disiplin-ilkesi]]) oldugu icin VE kurali secildi.

  TIKALI_YAYINSIZ_ZINCIR = 2 — olculen SAGLIKLI (gercek tikanma OLMAYAN) yayinsiz zincir
                           tavani, "yas >= 50 dk" kosulu altinda 0'dir; tavan 1 ilan
                           edildi (tek gurultu kosumuna pay) ve esik onun USTUNDEDIR.

⚠️ EKSEN 3, `ardisik_hata` ekseninin YERINE GECMEZ: sinifi DAHA GENISTIR ("kostu ama
yayinlaMADI" = hata sonuclari + `yayinsiz`) ama yas kapisi ARKASINDADIR. `ardisik_hata`
(esik 4) yas'tan BAGIMSIZ hukum verir ve oyle KALIR; ikisi ayri satir uretir.

🔴 BEYAN EDILMIS KALINTI SINIF (olculdu 2 Agu; 26 Eyl'de KAPATILDI — asagiya bkz.): gece
boyu push gelmeyen pencerede (00:57 -> 08:41) sabah gelen commit'ler `--ff-only` ile ESKI
committer tarihi tasidi ve taban da 7,7 saat oncesinin yayin aniydi -> yas 464,5 dk.
Taban ucuncu bir alt sinir istiyordu: "bekleyen icerigin main'e GELDIGI an".

🔴 UCUNCU ALT SINIR — MAIN'E GIRIS ANI (26 Eyl 2026, OLCULEN YANLIS ALARM)
==========================================================================
`paket-tazelik-alarmi` zamanlanmis kosumu 36256612737 (16:45Z) "TIKALI, en eski bekleyen
commit 76 dk" dedi. Gercek: son yayin b3194e03 (`deploy` 15:29:51Z); 15:29-16:32 arasi
main'e HIC push yok (sessizlik); 16:32:24'te 7808fd50 push'landi (dal merge'u; en eski
commit'in committer tarihi 23 Eyl), deploy kosumu 36255819182 16:32:26'da basladi ve
success indi. Bekleyen icerik ~13 dk'likti -> YANLIS ALARM. Kok: taban "son yayin ani"
iken main SESSIZ kalinca yas, icerik main'de YOKKEN birikiyordu.

Giris ani git'te YOKTUR (committer tarihi dalda yazildigi an; ff-only/merge bunu korur).
Iki aday OLCULDU (26 Eyl, `gh api`):
  * push-tetikli deploy kosumunun `created_at`'i — push'tan ~2 sn sonra; AMA 100 main
    push'unun 4'u `github-actions[bot]`undu ve GITHUB_TOKEN push'u is akisi TETIKLEMEZ:
    o push'lar kosumsuzdur -> giris GEC okunur -> yas ALTTAN (fail-OPEN yon). REDDEDILDI.
  * `repos/<depo>/activity?ref=refs/heads/main` — HER push (bot dahil) `before`/`after`/
    `timestamp` ile. Bekleyen icerigi main'e getiren push TANIM GEREGI `before ==
    son yayinlanan sha` olan push'tur (sezgisel eslesme YOK). SECILDI.
Kural:
    giris_ani = min(timestamp | aktivite.before == son_basarili.head_sha)
    taban     = max(en_eski_commit_tarihi, yayin_ani, giris_ani)
Giris olculemezse (API hatasi / yetki / pencerede eslesen push yok / gelecek damga)
taban ESKI davranistir (max(commit, yayin ani)) ve rapor `OLCULEMEDI` notu tasir: eski
taban giris'ten ONCE ya da ESIT oldugu icin yas USTTEN olculur — sessiz yesil DOGMAZ.

🔴 TEK IPTAL ALARM DEGILDIR. Eszamanlilik iptali bu depoda BILINCLI bir tasarimin
(`cancel-in-progress: false` + tek bekleyen kuyrugu) normal sonucudur. ACLIK ancak
iptaller ART ARDA gelip HICBIR kosum tamamlanmayinca dogar — ve tek basina zincir de
yetmez, ayrica BEKLEYEN ICERIK yaslanmis olmalidir (zincir >= 6 VE yas >= 45 dk).
Fikstur `iptal-firtinasi-taze.json` bu ayrimin kanaridir: 6 ardisik iptal ama taze
yayin -> AKIYOR (alarm YOK).

🔴 ALARMLARIN HEPSI "BEKLEYEN ICERIK VAR MI" KAPISININ ARKASINDADIR. `ahead_by == 0`
ise canli main'in TA KENDISIDIR; kosum zincirleri ne olursa olsun sonuc AKIYOR
(fikstur `guncel-hic-bekleyen-yok.json`).

YAS NASIL OLCULUR (ve neden TABANLANIR)
=======================================
    yayin_ani          = son_basarili kosumun `deploy` isinin `completed_at`'i
    giris_ani          = son yayinlanan sha'dan SONRAKI ilk push (activity API)
    bekleme_baslangici = max(en_eski_bekleyen_commit_tarihi, yayin_ani, giris_ani)
    yas_dk             = simdi - bekleme_baslangici
Taban SART: bu depoda dallar `--ff-only` ile alinir ve commit'ler ORIJINAL committer
tarihini tasir. Tabansiz olcum, saatler once bir worktree'de yazilip bugun alinan bir
commit'i "saatlerdir bekliyor" sayar -> yanlis alarm. Bir commit son yayindan ONCE
bekliyor OLAMAZ (bekliyor olsaydi o yayinda inerdi), o yuzden taban YAYIN ANIDIR.
(Kosumun BASLANGICI degil: aradaki fark bu hatta 47,8 dk olcuLDU — bkz. yukarida.)

KOSUM OMRU NASIL OLCULUR (EKSEN 2)
==================================
    omur_dk = simdi - kosum.run_started_at        # YALNIZ status != "completed" kosumlar
    takilan = bu omurlerin EN BUYUGU
Tamamlanmis kosum bu ekseni ilgilendirmez (bitti = takilmadi). Kuyrukta BEKLEYEN kosum da
sayilir ve bu BILEREK boyledir: `cancel-in-progress: false` kuyrugunda sonsuza kadar
bekleyen bir kosum da "yayin inmiyor" demektir; olculen en uzun SAGLIKLI kosum omru
(14 Agu 2026: 86,6 dk) KUYRUK BEKLEMESINI ZATEN ICERIR, esik onun uzerinden secilmistir.

🔴 BAYAT DILIM — TEK BIR REST KESITINDEN KESIN HUKUM CIKMAZ (1 Eki 2026, K429, OLCULDU)
======================================================================================
`paket-tazelik-alarmi` :: `yayin-nabzi` son 100 kosumun 12'sinde KIRMIZI yandi; 12'si de
TIKALI (rc 3). 23-30 Eyl'deki 8 kirmizinin hepsinde AYNI imza: "son yayinlanan sha: 01dd81b6
(21 Eyl 21:07)" SABIT, "geride" 3 -> 4 -> 52 -> ... -> 133, "pencere: 40 kosum (40 tamamlandi,
0 kosuyor)". Oysa deploy+yayin o gunlerde defalarca success'ti. GitHub `runs` ucu AYNI URL'ye
ardisik cagrilarda once BAYAT sonra TAZE kesit dondu (ayni dakikada: total_count 1932 / en yeni
22 Eyl, sonra 2500 / en yeni 1 Eki; `&status=completed` varyanti 493). `tools/durum.py` bolum 9
ayni anda "TIKALI · 134 commit geride · 11687 dk" basti (gercek: 3 commit, deploy kosuyordu).
Kesit bazen HAFTALARCA eski gelir ve KENDI ICINDE TUTARLIDIR (40/40 tamamlandi, hatasiz) —
sayfa-doluluk/`total_count` testleri onu YAKALAMAZ ([[api-yaniti-kendi-icinde-tutarsizsa-kesin-hukum-cikmaz]]).

15-18 Eyl'deki 4 kirmizi da AYNI sinif cikti (SINIFLANDIRILDI, 1 Eki): "son yayinlanan sha"
c0301670 bir 17 AGUSTOS, b2d174aa bir 26 AGUSTOS commit'idir; o 4 gunun her birinde success
deploy kosumlari VARDI (16 Eyl icin 22 · 17 Eyl icin 7 · 18 Eyl icin 16) ve 16 Eyl kirmizisinin
kendi HEAD'i 5bf06d6e icin 18:46Z'de baslayan deploy kosumu success'ti. Yani 12 kirmizinin
12'si BAYAT DILIM; GERCEK tikanma 0. Fiksturler (c) `taze-gercek-tikanma` bu yonu (taze + gercekten
yayinsiz -> TIKALI KALIR) ayrica kilitler: onarim "bayat say, sus" DEGILDIR.

ONARIM (iki ayak; ikisi de TEK kanonik yerde: `kosumlari_cek`):
  1) FUZYON: runs sorgusu en az CEKIM_MIN (3) kez cekilir; her kosum id'si icin `updated_at`'i en
     YENI nesil kazanir. Bayat replika bir kosumu yalnizca GERI gosterebilir, ILERI uyduramaz
     -> fuzyon fail-open DEGILDIR (en kotu halde bayat nesil tazeyi yenemez). created_at azalan
     siralanir, PENCERE_KOSUM'a kesilir. URL her cekimde FARKLIDIR (per_page 40, 41, ...): URL'ye
     takili bir bayat yanit tekrarlanmasin.
  2) BAGIMSIZ TAZELIK KANITI: `repos/<depo>/commits?sha=<dal>` (git; Actions indeksinden
     BAGIMSIZ) en yeni commit'lerinden, bot/`[skip ci]` OLMAYAN (is akisi tetiklemez) en yenisi
     `aday`tir. Aday TAZELIK_TOLERANS_DK (5 dk) dan eskiyse ve pencerede o sha'nin kosumu YOKSA
     dilim BAYATTIR -> yeniden cekilir (CEKIM_TAVAN = 5 cekime kadar, ek cekimler arasi 3 sn).
     Tavan asilirsa hukum TIKALI/ACLIK/AKIYOR DEGIL OLCULEMEDI (rc 2) olur: bayat dilimden kesin
     hukum cikmaz. Satirda `⚙ BAYAT DILIM` notu + kacinci cekimde taze bulundugu GORUNUR.
  3) Commits API cevap vermezse / aday yoksa: hukum YALNIZ fuzyondan cikar ve `tazelik kaniti: YOK`
     satiri bunu ILAN eder (sessiz ikame yok). Aday 5 dk'dan taze ise bayatlik KANITLANMAZ
     (TOLERANS): kosum henuz listede olmayabilir — bu pencerede sahte OLCULEMEDI uretilmez.
  Fiksturler: `bayat-ilk-cekim-taze-ikinci` (a) · `bayat-tum-cekimler` (b) · `taze-gercek-tikanma`
  (c) · `komit-api-yok-fuzyon` (d) + sinir vakalari; kabul testi Y11, mutasyon M20-M27.

SINIFLAR ve CIKIS KODLARI (rc)
==============================
    AKIYOR      0   bekleyen yok ya da esiklerin altinda
    GECIKME     1   birikme var, hat calisiyor (UYARI)
    OLCULEMEDI  2   olculemedi — YESIL DEGIL, KIRMIZI DA DEGIL (fail-closed teshis)
    TIKALI      3   kosumlar dusuyor / icerik esigin uzerinde bayat
    ACLIK       4   kosumlar ust uste iptal, hicbiri tamamlanmiyor
Kodlar BILEREK ayridir: "olculemedi" hicbir kabuk kosulunda "yesil" ile karismaz.

KULLANIM
========
    python3 tools/yayin-gecikme-nobeti.py               # canli olcum (gh gerekir)
    python3 tools/yayin-gecikme-nobeti.py --kendini-test # AGSIZ fikstur kabulu
    python3 tools/yayin-gecikme-nobeti.py --fikstur bugun-tikali
    python3 tools/yayin-gecikme-nobeti.py --liste        # fiksturleri listeler
"""
import argparse
import copy
import datetime
import glob
import json
import os
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
FIKSTUR_DIZIN = os.path.join(TOOLS, "fikstur", "yayin-gecikme")
SEKIL_CAPASI = os.path.join(FIKSTUR_DIZIN, "sekil-capasi.json")

DEPO = os.environ.get("GITHUB_REPOSITORY") or "Pruvo138/pruvo"
IS_AKISI = "deploy.yml"
DAL = "main"

# Pencere: olculen en uzun hata zinciri 10, en uzun iptal zinciri 5 idi; 40 tamamlanmis
# kosum ~10 saatlik trafigi kapsar -> zincirler pencereye SIGAR (pencere kenarina
# dayanan zincir raporda ILAN EDILIR).
PENCERE_KOSUM = 40

GECIKME_YAS_DK = 50
TIKALI_YAS_DK = 65
TIKALI_HATA_ZINCIR = 4
ACLIK_IPTAL_ZINCIR = 6
GECIKME_BIRIKME = 12

# 🔴 EKSEN 3 — YAYINSIZ ZINCIR (5 Agu 2026). "Kostu ama YAYINLAMADI" siniftir ve
# `ardisik_hata`dan GENISTIR: `yayinsiz` (kosum yesil ama `deploy` success DEGIL) da
# sayilir. Sayinin GELDIGI YER modul basligindaki 7 gunluk tik simulasyonudur; bu esik
# TEK BASINA degil, `yas >= GECIKME_YAS_DK` kosuluyla BIRLIKTE hukum verir (bkz. baslik:
# zincir>=2 tek basina 2,51 alarm/gun, yas kosuluyla 0,89 alarm/gun ve 0 sahte alarm).
TIKALI_YAYINSIZ_ZINCIR = 2

# 🔴 EKSEN 2 — KOSUM OMUR TAVANI (dk). "Kosum basladi ama HIC bitmiyor" sinifinin TEK
# olcusu budur ve `ahead_by` kapisinin ONUNDEDIR (bkz. baslik). Sayinin GELDIGI YER
# (Y1, 14 Agu 2026 yeniden olcumu): NORMAL TABANA gore kurulur, olay penceresine gore
# DEGIL. 128 = olculen post-olay normal omur max (86,6 dk) x ~1,5. Gerekce: 8-10 Agu
# olay penceresindeki GERCEK takilmalar (143,5 / 169,1 dk) hala yakalanir (128 < 143,5),
# normal kosumlar artik alarm URETMEZ. Eski 75, 2 Agu'nun bayat 49,1 dk tabanindan
# turetilmisti ve 14 Agu'da SAHTE TIKANMA ALARMI uretti (bkz. "EKSEN 2 TABANI BAYATLADI").
KOSUM_OMUR_TAVANI_DK = 128

# 🔴 OLCULEN SAGLIKLI TAVANLAR (zincirler: 1 Agu 2026 / 100 kosum · yas: 2 Agu 2026 /
# 100 kosum · KOSUM OMRU: 14 Agu 2026 / son 7 gun / 121 BASARILI kosum — bkz. baslik
# "ESIKLER" ve "EKSEN 2 TABANI BAYATLADI"). Esikler bu tavanlarin USTUNDE olmak
# ZORUNDADIR: altina cekilen bir esik NORMAL eszamanlilik iptallerine, gurultu
# hatalarina ya da NORMAL SUREN bir kosuma alarm verir (yanlis alarm = kapatilan
# nobetci). Sozlesme nobeti bunu `kendini_test` icinde olcer; fikstur kanarilari
# `iptal-zinciri-bayat-saglikli.json` (zincir) ve `takilan-kosum-normal.json` (omur).
OLCULEN_SAGLIKLI_IPTAL_TAVANI = 5
OLCULEN_SAGLIKLI_HATA_TAVANI = 3
# 🔴 OLCULEN KOSUM OMRU MAX (dk) — 14 Agu 2026 yeniden olcumu (Y2): pencere = son 7 gun
# (deploy.yml/main, 399 kosum cekildi), TABAN = o pencerede `conclusion == "success"`
# olan 121 kosum. Post-olay (8-10 Agu olay penceresi DISI) NORMAL omur max = 86,6 dk.
# Eski 49,1 (2 Agu) bayatti: `serit-a3`/`serit-a4` kollari eklendikten sonra yayin
# zinciri yapisal olarak uzadi ve 14 Agu'da sahte kirmizi uretti. Arsivin 85,0'i bugunku
# 86,6'yi kucumsuyordu.
OLCULEN_KOSUM_OMRU_MAX_DK = 86.6
OLCULEN_SAGLIKLI_YAS_TAVANI_DK = 51.8
# 5 Agu 2026 / 7 gun / 651 alarm tigi: "bekleyen icerik >= 50 dk yaslanmis" olan HER tikte
# yayinsiz zincir >= 2 idi ve o tiklerin HEPSI gercek yayin durmasiydi -> saglikli tavan
# FIILEN 0 olculdu. 1 ILAN EDILIR (tek gurultu kosumuna pay); esik onun USTUNDE olmali.
OLCULEN_SAGLIKLI_YAYINSIZ_TAVANI = 1

# GitHub `conclusion` degerleri: hangisi "dustu" sayilir.
HATA_SONUCLARI = ("failure", "startup_failure", "timed_out", "action_required")
# 🔴 "KOSTU AMA YAYINLAMADI" sinifi = hata sonuclari + `yayinsiz` (etkin_sonuc: kosum
# YESIL ama `deploy` isi success DEGIL, or. skipped). `cancelled` BILEREK DISARIDA:
# kuyrukta iptal bu depoda NORMAL bir olaydir ve icerigi ayakta kalan kosum tasir
# (modul basligi (b) olcumu) -> iptali bu sinifa katmak `dagilmis-hatalar-saglikli`
# kanarisini KIRMIZI yakardi (olculdu: iptal-notr varyanti 1 -> 4 zincir).
YAYINSIZ_SONUCLARI = HATA_SONUCLARI + ("yayinsiz",)
# "completed" DISI her status kosumun HALA CALISTIGI/BEKLEDIGI anlamina gelir; zincir
# sayiminda ATLANIR (kanit degil) ama raporda sayilir.
TAMAMLANDI = "completed"

# 🔴 YAYIN YETKILISI: siteyi canliya koyan is (deploy.yml :: jobs.deploy). "Yayin indi
# mi" YALNIZ bunun is-duzeyi sonucundan okunur; kosumun genel conclusion'indan DEGIL
# (modul basligindaki olcum). TASLAK_ISI (jobs.yayin) deploy'dan sonra kosar, OLCULUR
# ve raporda ayri satir olarak gorunur — site tazeligi hakkinda hukum VERMEZ.
YAYIN_ISI = "deploy"
TASLAK_ISI = "yayin"
# Is objesinde OKUNAN alanlar — biri yoksa OLCULEMEDI (fail-closed sekil dogrulamasi).
# `completed_at` YAS TABANIDIR (yayin ani): alani listeden dusurmek tabani sessizce
# kaybettirir, o yuzden sekil sozlesmesinde durur.
IS_ZORUNLU = ("name", "status", "conclusion", "completed_at")
# Tarama ilk yayinlayan kosumda DURUR; tavan yalnizca butce sinuridir (bkz. baslik).
IS_SORGU_TAVANI = 8

# 🔴 MAIN'E GIRIS ANI (26 Eyl 2026, bkz. baslik "UCUNCU ALT SINIR"). Aktivite objesinde
# OKUNAN alanlar — biri yoksa giris OLCULEMEDI (yas eski tabana duser, rapor ILAN eder).
AKTIVITE_ZORUNLU = ("before", "after", "ref", "timestamp", "activity_type")
# Pencere: olculen trafik ~20 push/gun (26 Eyl, 100 push ~5 gun) -> son yayin 5 gunden
# eskiyse eslesen push pencere DISINDA kalir ve giris OLCULEMEDI olur (eski taban).
AKTIVITE_PENCERE = 100
# Dal SILME aktivitesi main'e icerik GETIRMEZ.
AKTIVITE_ICERIKSIZ = ("branch_deletion",)
GIRIS_OLCULEMEDI = "OLCULEMEDI"

# 🔴 BAYAT DILIM (1 Eki 2026, K429 — bkz. baslik "BAYAT DILIM"). Runs ucu bazen haftalarca
# eski, kendi icinde TUTARLI bir kesit dondurur; tek cekimden KESIN hukum cikmaz.
#   CEKIM_MIN   : fuzyon icin en az cekim (bayat replika yalniz GERI kalir -> fail-open degil)
#   CEKIM_TAVAN : tazelik kaniti tutmazsa en cok bu kadar cekim (spec: 5); asilirsa OLCULEMEDI
#   CEKIM_ARASI_SN: YALNIZ ek cekimlerden once (CEKIM_MIN'den sonra) ve YALNIZ gercek ag kolunda
#   KOMIT_PENCERE: aday secimi icin bakilan en yeni commit sayisi (bot/skip-ci atlamasina pay)
#   TAZELIK_TOLERANS_DK: commit bundan TAZEYSE kosumu henuz listede olmayabilir (kanit aranmaz)
# Olculen: gercek aralik (commit.committer.date -> kosum.created_at) son 74 itme ucunda
# ortanca 2,3 dk · p90 3,2 dk · max 12,1 dk (3/74 > 5 dk: `--ff-only` ile gelen eski tarihli
# uc). 5 dk bu yuzden "kanit aranmaz" payidir; bayatlik EN FAZLA bu pay + CEKIM_TAVAN ek cekim
# kadar gec yakalanir ve OLCULEMEDI (sahte TIKALI degil) uretir.
CEKIM_MIN = 3
CEKIM_TAVAN = 5
CEKIM_ARASI_SN = 3
KOMIT_PENCERE = 5
TAZELIK_TOLERANS_DK = 5
# GitHub'in belgeli "bu itme is akisi tetiklemesin" isaretleri (commit mesajinda).
CI_ATLAMA_ISARETLERI = ("[skip ci]", "[ci skip]", "[no ci]", "[skip actions]",
                        "[actions skip]")

SINIF_RC ={"AKIYOR": 0, "GECIKME": 1, "OLCULEMEDI": 2, "TIKALI": 3, "ACLIK": 4}
SINIF_ISARET = {"AKIYOR": "🟢", "GECIKME": "🟡", "OLCULEMEDI": "⚪",
                "TIKALI": "🔴", "ACLIK": "🔴"}

# Kosum objesinde OKUNAN alanlar — biri yoksa OLCULEMEDI (fail-closed sekil dogrulamasi).
KOSUM_ZORUNLU = ("id", "status", "conclusion", "created_at", "run_started_at",
                 "updated_at", "head_sha", "event")


class OlcumHatasi(Exception):
    """Veri cekilemedi / anlasilamadi -> YESIL degil, OLCULEMEDI (rc 2)."""


# ---------------------------------------------------------------- zaman
def _iso(metin, ne="zaman damgasi"):
    if not isinstance(metin, str) or not metin:
        raise OlcumHatasi("%s okunamadi (bos/yanlis tur: %r)" % (ne, metin))
    ham = metin.strip()
    if ham.endswith("Z"):
        ham = ham[:-1] + "+00:00"
    try:
        d = datetime.datetime.fromisoformat(ham)
    except ValueError:
        raise OlcumHatasi("%s cozulemedi: %r" % (ne, metin))
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    return d.astimezone(datetime.timezone.utc)


def _simdi():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------- API
def kosum_yolu(depo=None, is_akisi=None, dal=DAL, pencere=None):
    return ("repos/%s/actions/workflows/%s/runs?branch=%s&per_page=%d"
            % (depo or DEPO, is_akisi or IS_AKISI, dal,
               PENCERE_KOSUM if pencere is None else pencere))


def karsilastirma_yolu(taban, dal=DAL, depo=None):
    return "repos/%s/compare/%s...%s" % (depo or DEPO, taban, dal)


def is_yolu(kosum_id, depo=None):
    return "repos/%s/actions/runs/%s/jobs?per_page=100" % (depo or DEPO, kosum_id)


def aktivite_yolu(depo=None, dal=DAL, pencere=None):
    return ("repos/%s/activity?ref=refs/heads/%s&per_page=%d"
            % (depo or DEPO, dal, AKTIVITE_PENCERE if pencere is None else pencere))


def komit_yolu(depo=None, dal=DAL):
    return "repos/%s/commits?sha=%s&per_page=%d" % (depo or DEPO, dal, KOMIT_PENCERE)


# `gh` stderr'i -> SABIT sinif etiketi. Anahtarlar kucuk harfe cevrilmis metinde ARANIR.
# Sira ONEMLI DEGIL: eslesen TUM siniflar bildirilir (biri digerini gizlemesin).
GH_HATA_SOZLUGU = (
    ("http 401", "yetkisiz (401)"),
    ("http 403", "yasak ya da kota (403)"),
    ("http 404", "bulunamadi (404)"),
    ("http 422", "islenemedi (422)"),
    ("http 5", "sunucu hatasi (5xx)"),
    ("rate limit", "kota siniri"),
    ("gh auth login", "oturum yok"),
    ("authentication", "kimlik dogrulanamadi"),
    ("could not resolve", "ag/DNS"),
    ("connection refused", "ag/baglanti"),
    ("timeout", "zaman asimi"),
)


def gh_hata_sinifi(ham):
    """`gh` stderr'ini SINIFA cevirir — HAM METIN DISARI CIKMAZ.

    NEDEN (olculdu): eski hal `hata[0][:160]` ile `gh`'in kendi stderr'ini oldugu gibi
    panoya basiyordu. Sentetik bir `gh` ile olculdu: URL/yol tasiyan bir hata metni
    oldugu gibi yakalanip panoya dusuyor ve pano "sir/kimlik bicimli dizgi basmasin"
    nobetini KIRIYOR (bu ev bu tuzaga iki kez dustu). Gercek `gh` dort senaryoda URL
    basmadi — yani sizinti bugun TEORIK; ama gecirgenlik gercek.

    Cikan bilgi: SABIT sozlukten gelen sinif etiketi (teshis KORUNUR) + olculen bayt
    sayisi. Hicbir kosulda cagrilan URL, jeton ya da yol basilmaz.
    """
    metin = (ham or "").strip()
    d = metin.lower()
    siniflar = []
    for anahtar, ad in GH_HATA_SOZLUGU:
        if anahtar in d and ad not in siniflar:
            siniflar.append(ad)
    if siniflar:
        return " · ".join(siniflar)
    if not metin:
        return "(cikti yok)"
    return "taninmayan hata metni (%d bayt — ICERIK BASILMAZ)" % len(metin)


def api_getir(yol, zaman_asimi=25, etiket="api"):
    """`gh api <yol>` -> JSON. HER ariza OlcumHatasi'dir (sessiz yesil YOK).

    `etiket`: cagri YERINI soyleyen SABIT dizgi (`runs` / `jobs` / `compare`), CAGRI
    YERINDE verilir. Yoldan DESENLE turetilMEZ. Gerekcesi olculdu: gercek `gh` ucuncu
    farkli uc icin de ayni metni basiyor (`gh: Not Found (HTTP 404)`), dolayisiyla
    etiket olmadan kirmizi yandiginda HANGI cagrinin dustugu anlasilmiyordu.
    """
    try:
        p = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", yol],
                           capture_output=True, text=True, timeout=zaman_asimi)
    except FileNotFoundError:
        raise OlcumHatasi("`gh` bulunamadi (PATH'te yok) — GitHub Actions durumu "
                          "sorulamadi [%s]" % etiket)
    except subprocess.TimeoutExpired:
        raise OlcumHatasi("`gh api` [%s] %d sn icinde yanit vermedi" % (etiket, zaman_asimi))
    if p.returncode != 0:
        raise OlcumHatasi("`gh api` [%s] rc=%d: %s"
                          % (etiket, p.returncode, gh_hata_sinifi(p.stderr or p.stdout)))
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise OlcumHatasi("`gh api` [%s] govdesi JSON degil (%d bayt)"
                          % (etiket, len(p.stdout or "")))


# ---------------------------------------------------------------- sekil dogrulama
def _sozluk(govde, ne):
    if not isinstance(govde, dict):
        raise OlcumHatasi("%s: sozluk bekleniyordu, %s geldi" % (ne, type(govde).__name__))
    return govde


def kosumlari_ayikla(govde):
    """API govdesinden kosum listesi — sekil FAIL-CLOSED dogrulanir."""
    g = _sozluk(govde, "kosum listesi govdesi")
    if "workflow_runs" not in g:
        raise OlcumHatasi("govdede `workflow_runs` YOK — API sekli degismis olabilir")
    kosumlar = g["workflow_runs"]
    if not isinstance(kosumlar, list):
        raise OlcumHatasi("`workflow_runs` liste degil (%s)" % type(kosumlar).__name__)
    if not kosumlar:
        raise OlcumHatasi("`workflow_runs` BOS — hicbir deploy kosumu gorulmedi; "
                          "bu bir yargi degil, olcum yoklugudur")
    for i, k in enumerate(kosumlar):
        _sozluk(k, "kosum[%d]" % i)
        eksik = [a for a in KOSUM_ZORUNLU if a not in k]
        if eksik:
            raise OlcumHatasi("kosum[%d] alanlari EKSIK: %s (API sekli degismis olabilir)"
                              % (i, ", ".join(eksik)))
    # Yeniden eskiye: API zaten boyle dondurur, yine de KENDIMIZ siralariz.
    return sorted(kosumlar, key=lambda k: _iso(k["created_at"], "created_at"), reverse=True)


def karsilastirmayi_ayikla(govde):
    """compare govdesi -> (geride, en_eski_bekleyen_tarih, kirpildi_mi)."""
    g = _sozluk(govde, "karsilastirma govdesi")
    for a in ("ahead_by", "commits", "total_commits"):
        if a not in g:
            raise OlcumHatasi("karsilastirma govdesinde `%s` YOK — API sekli degismis "
                              "olabilir" % a)
    geride = g["ahead_by"]
    if not isinstance(geride, int) or geride < 0:
        raise OlcumHatasi("`ahead_by` sayi degil: %r" % (geride,))
    commits = g["commits"]
    if not isinstance(commits, list):
        raise OlcumHatasi("`commits` liste degil (%s)" % type(commits).__name__)
    if geride == 0:
        return 0, None, False
    if not commits:
        raise OlcumHatasi("`ahead_by`=%d ama `commits` BOS — govde kendi icinde tutarsiz"
                          % geride)
    ilk = _sozluk(commits[0], "commits[0]")
    try:
        tarih = ilk["commit"]["committer"]["date"]
    except (KeyError, TypeError):
        raise OlcumHatasi("commits[0].commit.committer.date YOK — API sekli degismis "
                          "olabilir")
    # compare en fazla 250 commit dondurur: uzerinde yas ALTTAN olculur, ILAN EDILIR.
    return geride, _iso(tarih, "commits[0] committer.date"), geride > len(commits)


def giris_anini_ayikla(govde, taban_sha, simdi):
    """activity govdesi -> son yayinlanan sha'dan SONRAKI ilk push'un zamani. FAIL-CLOSED.

    Eslesme TANIMSALDIR, sezgisel DEGIL: bekleyen icerigi main'e getiren push `before`
    alani son yayinlanan sha olan push'tur (main dogrusal; bot push'lari DAHIL — deploy
    kosumu kaynagi onlari goremiyordu, bkz. baslik). Her ariza OlcumHatasi'dir; cagiran
    onu YUTMAZ, eski tabana dusup `OLCULEMEDI` notunu rapora tasir.
    """
    if not isinstance(govde, list):
        raise OlcumHatasi("aktivite govdesi liste degil (%s)" % type(govde).__name__)
    if not govde:
        raise OlcumHatasi("aktivite listesi BOS")
    taban = str(taban_sha or "").lower()
    if not taban:
        raise OlcumHatasi("son yayinlanan sha BOS — eslesecek push yok")
    adaylar = []
    for i, a in enumerate(govde):
        _sozluk(a, "aktivite[%d]" % i)
        eksik = [f for f in AKTIVITE_ZORUNLU if f not in a]
        if eksik:
            raise OlcumHatasi("aktivite[%d] alanlari EKSIK: %s (API sekli degismis olabilir)"
                              % (i, ", ".join(eksik)))
        if a["activity_type"] in AKTIVITE_ICERIKSIZ:
            continue
        if str(a["before"] or "").lower() == taban:
            adaylar.append(_iso(a["timestamp"], "aktivite[%d] timestamp" % i))
    if not adaylar:
        raise OlcumHatasi("son yayinlanan sha %s'den SONRAKI push aktivite penceresinde "
                          "(%d kayit) YOK" % (taban[:8], len(govde)))
    giris = min(adaylar)
    if giris > simdi:
        raise OlcumHatasi("giris ani (%s) simdiden (%s) SONRA — saat/govde tutarsiz"
                          % (giris.strftime("%H:%M:%S"), simdi.strftime("%H:%M:%S")))
    return giris


# ---------------------------------------------------------------- is (job) duzeyi
def isleri_ayikla(govde, kosum_id):
    """jobs govdesi -> ({is adi: conclusion}, {is adi: completed_at}). FAIL-CLOSED.

    IKI sozluk doner cunku iki AYRI soru sorulur ve karistirilmalari sessiz hatadir:
      conclusion  -> "yayin INDI mi"      (etkin_sonuc)
      completed_at-> "yayin NE ZAMAN indi" (yas tabani)

    BOS liste MESRUDUR ve olculmustur: bekleme kuyrugunda iptal edilen kosumlarda hic
    is yaratilmaz (`total_count: 0`) -> o kosum hicbir sey yayinlamamistir.
    """
    g = _sozluk(govde, "is listesi govdesi (kosum %s)" % kosum_id)
    if "jobs" not in g:
        raise OlcumHatasi("is govdesinde `jobs` YOK (kosum %s) — API sekli degismis "
                          "olabilir" % kosum_id)
    isler = g["jobs"]
    if not isinstance(isler, list):
        raise OlcumHatasi("`jobs` liste degil (%s, kosum %s)"
                          % (type(isler).__name__, kosum_id))
    cikti, bitisler = {}, {}
    for i, j in enumerate(isler):
        _sozluk(j, "kosum %s is[%d]" % (kosum_id, i))
        eksik = [a for a in IS_ZORUNLU if a not in j]
        if eksik:
            raise OlcumHatasi("kosum %s is[%d] alanlari EKSIK: %s (API sekli degismis "
                              "olabilir)" % (kosum_id, i, ", ".join(eksik)))
        if j.get("status") == TAMAMLANDI:
            cikti[str(j["name"])] = j["conclusion"]
            bitisler[str(j["name"])] = j["completed_at"]
    return cikti, bitisler


def etkin_sonuc(kosum, isler):
    """Kosumun YAYIN acisindan ETKIN sonucu (modul basligindaki olcum).

    Kosumun genel `conclusion`'i bu hatta yayin kaniti DEGILDIR: bloklaMAYAN bir isin
    (serit-b) dusmesi kosumu `failure` yapar, deploy+yayin basariyla kosmus olsa bile.
    """
    if isler.get(YAYIN_ISI) == "success":
        return "success"
    kosum_sonucu = kosum.get("conclusion")
    if kosum_sonucu == "success":
        # Kosum yesil ama SITEYI koyan is basarili degil (or. `skipped`): bu ne bir
        # yayindir ne de bir hata zinciri halkasidir -> kendi sinifi.
        return "yayinsiz"
    return kosum_sonucu


def yayin_taramasi(kosumlar, is_getir, tavan=IS_SORGU_TAVANI):
    """Tamamlanmis kosumlari YENIDEN geriye tarar, ILK YAYINLAYAN kosumda DURUR.

    Doner: (etkin_sonuclar, son_yayinlayan, son_isleri, son_bitisleri, taranan,
    tavana_dayandi). `etkin_sonuclar` taranan onekle AYNI sirada; zincirler bu onekten
    sayilir (bir zincir yayinlayan kosumu ASAMAZ, o yuzden onek yeterlidir).
    """
    etkin, son, son_isler, son_bitisler = [], None, None, None
    taranan, tavana_dayandi = 0, False
    for k in kosumlar:
        if k.get("status") != TAMAMLANDI:
            continue
        if taranan >= tavan:
            tavana_dayandi = True
            break
        isler, bitisler = isleri_ayikla(is_getir(k), k.get("id"))
        taranan += 1
        if k.get("conclusion") == "success" and YAYIN_ISI not in isler:
            # Kosum yesil ama bekledigimiz is ADI govdede HIC yok -> is akisinin
            # sekli degismis olabilir. Sessizce "yayinlamadi" saymak SAHTE KIRMIZI
            # uretirdi; bu bir yargi degil, olcum yoklugudur.
            raise OlcumHatasi("kosum %s YESIL ama `%s` isi govdede YOK (goruldu: %s) — "
                              "is akisi is adlari degismis olabilir"
                              % (k.get("id"), YAYIN_ISI,
                                 ", ".join(sorted(isler)) or "hic is yok"))
        e = etkin_sonuc(k, isler)
        etkin.append(e)
        if e == "success":
            son, son_isler, son_bitisler = k, isler, bitisler
            break
    return etkin, son, son_isler, son_bitisler, taranan, tavana_dayandi


def takilan_kosum(kosumlar, simdi):
    """EKSEN 2: en uzun suredir TAMAMLANMAMIS kosumun (omur_dk, id)'si — yoksa (None, None).

    Yalniz `status != "completed"` kosumlar sayilir. Bu eksen `ahead_by` kapisinin
    ONUNDEDIR (bkz. modul basligi): bekleyen commit olmasa da takilan kosum bir arizadir.
    """
    en_omur, en_id = None, None
    for k in kosumlar:
        if k.get("status") == TAMAMLANDI:
            continue
        basladi = _iso(k.get("run_started_at"), "run_started_at (kosum %s)" % k.get("id"))
        omur = max(0.0, (simdi - basladi).total_seconds() / 60.0)
        if en_omur is None or omur > en_omur:
            en_omur, en_id = omur, k.get("id")
    return en_omur, en_id


# ---------------------------------------------------------------- zincirler
def zincirler(kosumlar, etkin):
    """(ardisik_iptal, ardisik_hata, ardisik_yayinsiz, tamamlanan, calisan).

    Zincirler YALNIZ tamamlanmis kosumlarin ETKIN sonuclari uzerinde, EN YENIDEN geriye
    sayilir ve ilk FARKLI sonucta DURUR. Kosan/bekleyen kosum kanit degildir -> atlanir.

    `ardisik_yayinsiz` EKSEN 3'un olcusudur ve `ardisik_hata`nin USTKUMESIDIR
    (YAYINSIZ_SONUCLARI ⊇ HATA_SONUCLARI); ikisi AYRI raporlanir cunku ayri esikleri ve
    ayri kapilari vardir ([[hukum-yanlis-birimde]]).
    """
    tamam = [k for k in kosumlar if k.get("status") == TAMAMLANDI]
    calisan = len(kosumlar) - len(tamam)

    def zincir(kume):
        n = 0
        for e in etkin:
            if e in kume:
                n += 1
            else:
                break
        return n

    return (zincir(("cancelled",)), zincir(HATA_SONUCLARI), zincir(YAYINSIZ_SONUCLARI),
            len(tamam), calisan)


# ---------------------------------------------------------------- bayat dilim (K429)
def komitleri_ayikla(govde, simdi):
    """commits govdesi -> [{sha, tarih, yas_dk, atlanir}] (en yeni basta). FAIL-CLOSED.

    `atlanir` ("bot" | "ci-atla" | None): bu commit'in itilmesi is akisini TETIKLEMEZ
    (GITHUB_TOKEN itmesi is akisi baslatmaz; `[skip ci]` isareti), yani pencerede kosumu
    BEKLENMEZ ve tazelik adayi OLAMAZ. Aksi halde bot commit'i HEAD iken sonraki itmeye kadar
    KALICI sahte OLCULEMEDI dogardi.
    """
    if not isinstance(govde, list):
        raise OlcumHatasi("commit listesi govdesi liste degil (%s)" % type(govde).__name__)
    if not govde:
        raise OlcumHatasi("commit listesi BOS — tazelik kaniti alinamadi")
    cikti = []
    for i, c in enumerate(govde):
        _sozluk(c, "commits[%d]" % i)
        if "sha" not in c or "commit" not in c:
            raise OlcumHatasi("commits[%d] alanlari EKSIK (sha/commit) — API sekli degismis "
                              "olabilir" % i)
        ic = _sozluk(c["commit"], "commits[%d].commit" % i)
        try:
            ham_tarih = ic["committer"]["date"]
        except (KeyError, TypeError):
            raise OlcumHatasi("commits[%d].commit.committer.date YOK — API sekli degismis "
                              "olabilir" % i)
        tarih = _iso(ham_tarih, "commits[%d] committer.date" % i)
        sha = str(c["sha"] or "").lower()
        if not sha:
            raise OlcumHatasi("commits[%d].sha BOS" % i)
        bot = any(isinstance(c.get(r), dict) and str(c[r].get("login") or "").endswith("[bot]")
                  for r in ("author", "committer"))
        mesaj = str(ic.get("message") or "").lower()
        atla = "bot" if bot else ("ci-atla" if any(m in mesaj for m in CI_ATLAMA_ISARETLERI)
                                  else None)
        cikti.append({"sha": sha, "tarih": tarih, "atlanir": atla,
                      "yas_dk": max(0.0, (simdi - tarih).total_seconds() / 60.0)})
    return cikti


def tazelik_adayi(komitler):
    """Pencerede kosumu BEKLENEN en yeni commit (atlanmayan ilk) — yoksa None."""
    for k in komitler:
        if not k["atlanir"]:
            return k
    return None


def pencere_tazeligi(kosumlar, aday):
    """Bir kosum listesinin TAZELIGI -> TAZE | TOLERANS | BAYAT | KANIT_YOK.

    BAYAT = aday commit pencerede YOK ve TAZELIK_TOLERANS_DK'dan eski (git bilir, Actions
    indeksi bilmiyor). TOLERANS = commit cok taze: kosumu henuz listede olmayabilir, bayatlik
    KANITLANMADI (sahte OLCULEMEDI uretilmez).
    """
    if aday is None:
        return "KANIT_YOK"
    for k in kosumlar:
        if str(k.get("head_sha") or "").lower() == aday["sha"]:
            return "TAZE"
    if aday["yas_dk"] < TAZELIK_TOLERANS_DK:
        return "TOLERANS"
    return "BAYAT"


def kosumlari_fuzyonla(listeler):
    """Birden cok cekimi TEK pencereye birlestirir: id basina `updated_at`'i en YENI nesil kazanir.

    Bayat replika bir kosumu yalnizca GERI gosterebilir (eski status/conclusion, eksik yeni
    kosum), ILERI uyduramaz -> en yeni nesli secmek fail-open DEGILDIR: bayat nesil tazeyi
    asla yenemez. Sonuc created_at azalan (esitlikte id azalan) siralidir; KESME cagirana ait.
    """
    en_iyi = {}
    for liste in listeler:
        for k in liste:
            kimlik = str(k["id"])
            onceki = en_iyi.get(kimlik)
            if onceki is None or (_iso(k["updated_at"], "updated_at")
                                  > _iso(onceki["updated_at"], "updated_at")):
                en_iyi[kimlik] = k
    return sorted(en_iyi.values(),
                  key=lambda k: (_iso(k["created_at"], "created_at"), str(k["id"])),
                  reverse=True)


def _bayat_tavan_mesaji(cekim, basarili, hatali, aday, kosumlar, simdi):
    en_yeni = max(_iso(k["created_at"], "created_at") for k in kosumlar)
    return ("⚙ BAYAT DILIM: %d cekimin (%d basarili) HEPSI bayat — main HEAD %s (%.0f dk once, "
            "git) kosum penceresinde YOK; penceredeki en yeni kosum %s (%.1f sa once). Bayat "
            "dilimden KESIN hukum cikmaz: TIKALI/ACLIK/AKIYOR hukmu VERILMEDI (bu yesil de "
            "kirmizi da DEGIL). KAPATAN OLCUM: GitHub runs ucu taze kesiti dondurdugunde "
            "(sonraki tikte) hukum kendiliginden dogar; kesit KALICI bayat kalirsa yayin "
            "kaniti commits/activity API'ye tasinir (K429)%s"
            % (cekim, basarili, aday["sha"][:8], aday["yas_dk"],
               en_yeni.strftime("%Y-%m-%d %H:%MZ"),
               max(0.0, (simdi - en_yeni).total_seconds() / 3600.0),
               (" · %d cekim ayrica HATA verdi" % hatali) if hatali else ""))


def kosumlari_cek(getir, simdi, depo=None, dal=DAL, bekle=None):
    """Fuzyonlu + bagimsiz tazelik kanitli kosum penceresi -> (kosumlar, dilim).

    Sira: (1) commits API'den aday (git; Actions indeksinden BAGIMSIZ) · (2) runs >= CEKIM_MIN
    kez cekilir ve fuzyonlanir · (3) aday pencerede yoksa ve TAZELIK_TOLERANS_DK'dan eskiyse
    dilim BAYATTIR: CEKIM_TAVAN'a kadar yeniden cek · (4) tavan asilirsa OlcumHatasi
    (=> OLCULEMEDI, ASLA TIKALI/AKIYOR). Commits API cevap vermezse yalniz fuzyon kalir ve
    `dilim["komit_hata"]` bunu ILAN eder.

    `bekle`: ek cekimlerden once beklenen sure; varsayilan YALNIZ gercek ag kolunda
    (`getir is api_getir`) gercek bekler — fikstur/test beklemez.
    """
    if bekle is None:
        bekle = time.sleep if getir is api_getir else (lambda _sn: None)
    aday, komit_hata = None, None
    try:
        komitler = komitleri_ayikla(getir(komit_yolu(depo=depo, dal=dal), etiket="commits"),
                                    simdi)
        aday = tazelik_adayi(komitler)
        if aday is None:
            komit_hata = ("son %d commit'in HEPSI bot/[skip ci] — pencerede kosumu BEKLENEN "
                          "aday YOK" % len(komitler))
    except OlcumHatasi as e:
        komit_hata = str(e)

    cekimler, hatalar = [], []        # cekimler: [(cekim_no, kosum listesi)]
    n = 0
    while True:
        if n >= CEKIM_MIN:
            bekle(CEKIM_ARASI_SN)
        n += 1
        try:
            # URL her cekimde FARKLI (per_page 40, 41, ...): URL'ye takili bayat yanit
            # tekrarlanmasin. Fuzyondan sonra pencere PENCERE_KOSUM'a KESILIR.
            cekimler.append((n, kosumlari_ayikla(
                getir(kosum_yolu(depo=depo, dal=dal, pencere=PENCERE_KOSUM + n - 1),
                      etiket="runs"))))
        except OlcumHatasi as e:
            hatalar.append(e)
        if n < CEKIM_MIN:
            continue
        if not cekimler:
            raise hatalar[0]          # hicbir cekim basarili degil: ILK hata AYNEN yukari cikar
        kosumlar = kosumlari_fuzyonla([l for _, l in cekimler])[:PENCERE_KOSUM]
        durum = pencere_tazeligi(kosumlar, aday)
        if durum != "BAYAT":
            break
        if n >= CEKIM_TAVAN:
            raise OlcumHatasi(_bayat_tavan_mesaji(n, len(cekimler), len(hatalar), aday,
                                                  kosumlar, simdi))

    bayat_cekim, ilk_taze = None, None
    if aday is not None:
        durumlar = [(no, pencere_tazeligi(l, aday)) for no, l in cekimler]
        bayat_cekim = sum(1 for _, d in durumlar if d == "BAYAT")
        ilk_taze = next((no for no, d in durumlar if d == "TAZE"), None)
    return kosumlar, {
        "cekim": n, "basarili": len(cekimler), "hatali": len(hatalar),
        "hata_metni": str(hatalar[0]) if hatalar else None,
        "durum": durum, "bayat_cekim": bayat_cekim, "ilk_taze_cekim": ilk_taze,
        "aday_sha": aday["sha"][:8] if aday else None,
        "aday_yas_dk": aday["yas_dk"] if aday else None,
        "komit_hata": komit_hata,
        "pencere_en_yeni": max(_iso(k["created_at"], "created_at") for k in kosumlar),
    }


# ---------------------------------------------------------------- olcum
def olc(getir=api_getir, simdi=None, depo=None, dal=DAL):
    """Ham olcum sozlugu. HER ariza OlcumHatasi ile yukari cikar (fail-closed)."""
    simdi = simdi or _simdi()
    kosumlar, dilim = kosumlari_cek(getir, simdi, depo=depo, dal=dal)

    def is_getir(k):
        return getir(is_yolu(k.get("id"), depo=depo), etiket="jobs")

    (etkin, son_basarili, son_isler, son_bitisler,
     taranan, tavana_dayandi) = yayin_taramasi(kosumlar, is_getir)
    (ardisik_iptal, ardisik_hata, ardisik_yayinsiz,
     tamamlanan, calisan) = zincirler(kosumlar, etkin)
    takilan_dk, takilan_id = takilan_kosum(kosumlar, simdi)

    olcum = {
        "simdi": simdi,
        # BAYAT DILIM (K429): kac cekim, tazelik kaniti, bayat cekim sayisi — satirda GORUNUR.
        "dilim": dilim,
        "pencere": len(kosumlar),
        "tamamlanan": tamamlanan,
        "calisan": calisan,
        "taranan": taranan,
        "is_tavanina_dayandi": tavana_dayandi,
        "ardisik_iptal": ardisik_iptal,
        "ardisik_hata": ardisik_hata,
        # EKSEN 3 — "kostu ama yayinlaMADI" zinciri (hata + yayinsiz; iptal HARIC)
        "ardisik_yayinsiz": ardisik_yayinsiz,
        "son_basarili_sha": None,
        "son_basarili_baslangic": None,
        "son_basarili_bitis": None,
        "yayin_ani": None,
        "taslak_isi": None,
        "geride": None,
        "yas_dk": None,
        # UCUNCU ALT SINIR (26 Eyl): bekleyen icerigin main'e GIRIS ani + olcum durumu.
        "giris_ani": None,
        "giris_durum": None,
        "yas_tabani": None,
        "kirpildi": False,
        # EKSEN 2 — yas ekseninden BAGIMSIZ olculur, `ahead_by` kapisinin ONUNDE.
        "takilan_kosum_dk": takilan_dk,
        "takilan_kosum_id": takilan_id,
        "zincir_pencere_kenarinda": (tavana_dayandi
                                     or ardisik_iptal >= tamamlanan
                                     or ardisik_hata >= tamamlanan),
    }
    if son_basarili is None:
        return olcum

    olcum["son_basarili_sha"] = str(son_basarili["head_sha"])[:8]
    olcum["son_basarili_baslangic"] = _iso(son_basarili["run_started_at"], "run_started_at")
    olcum["son_basarili_bitis"] = _iso(son_basarili["updated_at"], "updated_at")
    # YAS TABANI: `deploy` isinin BITISI = icerigin CANLIYA INDIGI an (bkz. modul basligi).
    # Alan bos/None ise bu bir yargi degil, OLCUM YOKLUGUDUR -> OLCULEMEDI.
    yayin_ani_ham = (son_bitisler or {}).get(YAYIN_ISI)
    if not yayin_ani_ham:
        raise OlcumHatasi("kosum %s `%s` isi BASARILI ama `completed_at` YOK/bos — yayin "
                          "ani okunamadi, yas tabansiz kalirdi"
                          % (son_basarili.get("id"), YAYIN_ISI))
    olcum["yayin_ani"] = _iso(yayin_ani_ham, "`%s` isi completed_at" % YAYIN_ISI)
    # `yayin` isi OLCULUR ama site tazeligi hakkinda hukum VERMEZ (bkz. modul basligi).
    olcum["taslak_isi"] = (son_isler or {}).get(TASLAK_ISI)

    geride, en_eski, kirpildi = karsilastirmayi_ayikla(
        getir(karsilastirma_yolu(son_basarili["head_sha"], dal=dal, depo=depo),
              etiket="compare"))
    olcum["geride"] = geride
    olcum["kirpildi"] = kirpildi
    if geride > 0:
        # TABAN: bir commit son YAYINDAN once bekliyor olamaz (bekliyorsa o yayinda inerdi).
        # Kosumun BASLANGICI DEGIL — aradaki fark bu hatta 47,8 dk olculdu.
        baslangic = max(en_eski, olcum["yayin_ani"])
        taban_adi = "yayin ani" if olcum["yayin_ani"] >= en_eski else "commit tarihi"
        # UCUNCU ALT SINIR: icerik main'e GELMEDEN bekliyor olamaz (26 Eyl, bkz. baslik).
        # Olculemezse ESKI taban kalir (yas USTTEN) ve durum ILAN edilir — sessiz yesil YOK.
        try:
            giris = giris_anini_ayikla(
                getir(aktivite_yolu(depo=depo, dal=dal), etiket="activity"),
                son_basarili["head_sha"], simdi)
        except OlcumHatasi as e:
            olcum["giris_durum"] = "%s — %s" % (GIRIS_OLCULEMEDI, e)
            taban_adi += "; main'e giris ani %s" % GIRIS_OLCULEMEDI
        else:
            olcum["giris_ani"] = giris
            olcum["giris_durum"] = "OLCULDU"
            if giris > baslangic:
                taban_adi = "main'e giris ani"
            baslangic = max(baslangic, giris)
        olcum["yas_tabani"] = taban_adi
        olcum["yas_dk"] = max(0.0, (simdi - baslangic).total_seconds() / 60.0)
    else:
        olcum["yas_dk"] = 0.0
    return olcum


# ---------------------------------------------------------------- yargi
# Sinif AGIRLIGI (yalniz yargi birlestirme icin). SINIF_RC'den TURETILMEZ: orada
# OLCULEMEDI (2) TIKALI (3) ile GECIKME (1) ARASINDA durur ve bir agirlik SIRASI degildir.
SINIF_AGIRLIK = {"AKIYOR": 0, "GECIKME": 1, "TIKALI": 2, "ACLIK": 3}


def eksen_hukumleri(olcum):
    """HER EKSEN AYRI AYRI, TEK KANONIK YERDE olculur -> {eksen adi: bool}.

    🔴 IKIZ TANIM YASAGI ([[ikiz-tanim-sessiz-ayrisma]]): esik karsilastirmasi SADECE
    burada yazilir; `degerlendir` yalnizca bu sozlugu OKUR. Boylece "hangi eksen yandi"
    sorusunun cevabi, gerekce metniyle AYNI kaynaktan gelir ve sessizce ayrisamaz.

    Bu fonksiyon OLCER, KAPI UYGULAMAZ: "bekleyen icerik var mi" gibi kapilar hukmun
    (degerlendir) isidir. Boylece bir eksenin kapatilmasi eksenin OLCUMUNU yok etmez.
    """
    yas = olcum.get("yas_dk")
    geride = olcum.get("geride")
    takilan = olcum.get("takilan_kosum_dk")
    return {
        # EKSEN 1 — bekleyen icerigin YASI (tabani: yayin ani)
        "yas_gecikme": yas is not None and yas >= GECIKME_YAS_DK,
        "yas_tikali": yas is not None and yas >= TIKALI_YAS_DK,
        "hata_zinciri": olcum["ardisik_hata"] >= TIKALI_HATA_ZINCIR,
        "iptal_zinciri": olcum["ardisik_iptal"] >= ACLIK_IPTAL_ZINCIR,
        "birikme": geride is not None and geride >= GECIKME_BIRIKME,
        # EKSEN 3 — YAYINSIZ ZINCIR. IKI SART BIRDEN (bkz. modul basligi): zincir tek
        # basina 2,51 alarm/gun uretiyordu ve o alarmlarin hicbiri yeni bir gercek olay
        # yakalamiyordu; yas kosulu eklenince 0,89 alarm/gun ve 0 sahte alarm olculdu.
        # KOPYA YOK: yas karsilastirmasi yukaridaki `yas_gecikme` ile AYNI esikten gelir.
        "yayinsiz_zinciri": (olcum["ardisik_yayinsiz"] >= TIKALI_YAYINSIZ_ZINCIR
                             and yas is not None and yas >= GECIKME_YAS_DK),
        # EKSEN 2 — KOSUM OMRU (yas ekseninden BAGIMSIZ; `ahead_by` kapisinin ONUNDE)
        "sure_tavani": takilan is not None and takilan >= KOSUM_OMUR_TAVANI_DK,
    }


def degerlendir(olcum):
    """olcum -> (sinif, gerekce satirlari). Sira: ACLIK > TIKALI > GECIKME > AKIYOR.

    IKI EKSEN AYRI AYRI HUKUM VERIR: icerik ekseni (_icerik_hukmu) ve kosum omru ekseni.
    Ikisi ayni sinifi (TIKALI) uretebilir ama BIRI DIGERINI MASKELEMEZ: omur ekseni
    yandiysa gerekce satiri HER HALUKARDA eklenir, icerik ekseni ne derse desin
    ([[hukum-yanlis-birimde]]).
    """
    eksen = eksen_hukumleri(olcum)
    sinif, neden = _icerik_hukmu(olcum, eksen)

    if eksen["sure_tavani"]:
        neden = list(neden) + [
            "kosum %s %.0f dk'dir TAMAMLANMADI (omur tavani %d dk; olculen en uzun kosum "
            "omru %.1f dk) -> kosum basladi ama bitmiyor"
            % (olcum.get("takilan_kosum_id"), olcum["takilan_kosum_dk"],
               KOSUM_OMUR_TAVANI_DK, OLCULEN_KOSUM_OMRU_MAX_DK)]
        if SINIF_AGIRLIK[sinif] < SINIF_AGIRLIK["TIKALI"]:
            sinif = "TIKALI"
    return sinif, neden


def _icerik_hukmu(olcum, eksen):
    """EKSEN 1: bekleyen ICERIK ne kadar bayat / hat icerigi gecirebiliyor mu."""
    geride = olcum["geride"]
    yas = olcum["yas_dk"]
    ai = olcum["ardisik_iptal"]
    ah = olcum["ardisik_hata"]

    if olcum["son_basarili_sha"] is None:
        # Taranan onekte HIC yayinlayan kosum yok: olculdu, yargi verilebilir
        # (OLCULEMEDI DEGIL). "Yayinlayan" = `deploy` isi basarili olan kosum.
        kapsam = "taranan %d kosum (pencere %d)" % (olcum.get("taranan", 0),
                                                    olcum["pencere"])
        if eksen["iptal_zinciri"]:
            return "ACLIK", ["son %d tamamlanmis kosumun %d'si IPTAL, %s icinde `%s` isini "
                             "BASARIYLA kosan kosum YOK"
                             % (olcum["tamamlanan"], ai, kapsam, YAYIN_ISI)]
        return "TIKALI", ["%s icinde `%s` isini BASARIYLA kosan kosum YOK — canli, main'in "
                          "ne kadar gerisinde oldugu bile bu pencereden olculemiyor"
                          % (kapsam, YAYIN_ISI)]

    if not geride:
        return "AKIYOR", ["canli = main (bekleyen commit YOK); kosum zincirleri "
                          "(iptal %d · hata %d) icerik bekletMIYOR" % (ai, ah)]

    neden = []
    if eksen["iptal_zinciri"] and eksen["yas_gecikme"]:
        neden.append("%d ARDISIK iptal (esik %d) + en eski bekleyen commit %.0f dk "
                     "(esik %d) -> kosumlar ust uste iptal ediliyor, hicbiri tamamlanmiyor"
                     % (ai, ACLIK_IPTAL_ZINCIR, yas, GECIKME_YAS_DK))
        return "ACLIK", neden

    if eksen["hata_zinciri"]:
        neden.append("%d ARDISIK dusen kosum (esik %d)" % (ah, TIKALI_HATA_ZINCIR))
    # EKSEN 3 — AYRI SATIR: hata zinciri esigi (4) bu sinifi 5 Agu'da KACIRDI (2'de kaldi).
    # Iki eksen birbirini MASKELEMESIN diye gerekce her halukarda EKLENIR.
    if eksen["yayinsiz_zinciri"]:
        neden.append("%d ARDISIK kosum KOSTU ama YAYINLAMADI (`%s` isi success degil; "
                     "esik %d) + bekleyen icerik %.0f dk (esik %d dk) -> yayin DURMUS"
                     % (olcum["ardisik_yayinsiz"], YAYIN_ISI, TIKALI_YAYINSIZ_ZINCIR,
                        yas, GECIKME_YAS_DK))
    if eksen["yas_tikali"]:
        neden.append("en eski bekleyen commit %.0f dk (esik %d dk, taban: %s)"
                     % (yas, TIKALI_YAS_DK, olcum.get("yas_tabani") or "yayin ani"))
    if neden:
        return "TIKALI", neden

    if eksen["yas_gecikme"]:
        neden.append("en eski bekleyen commit %.0f dk (uyari esigi %d dk, taban: %s)"
                     % (yas, GECIKME_YAS_DK, olcum.get("yas_tabani") or "yayin ani"))
    if eksen["birikme"]:
        neden.append("%d commit birikti (uyari esigi %d)" % (geride, GECIKME_BIRIKME))
    if neden:
        return "GECIKME", neden

    return "AKIYOR", ["%d commit bekliyor, en eskisi %.0f dk (esiklerin altinda)"
                      % (geride, yas)]


def olc_ve_degerlendir(getir=api_getir, simdi=None, depo=None, dal=DAL):
    """(sinif, rc, satirlar). OLCULEMEDI burada dogar ve ASLA rc 0 vermez."""
    try:
        olcum = olc(getir=getir, simdi=simdi, depo=depo, dal=dal)
    except OlcumHatasi as e:
        return "OLCULEMEDI", SINIF_RC["OLCULEMEDI"], [str(e)], None
    except Exception as e:                 # beklenmeyen her sey de OLCULEMEDI'dir
        return ("OLCULEMEDI", SINIF_RC["OLCULEMEDI"],
                ["beklenmeyen olcum hatasi: %s: %s" % (type(e).__name__, e)], None)
    # Eksen hukumleri RAPORA ve KABUL TESTINE tasinir: "hangi eksen yandi" sorusu
    # cikti metninden AYIKLANMAZ, olcumden OKUNUR ([[hukum-yanlis-birimde]]).
    olcum["eksenler"] = eksen_hukumleri(olcum)
    sinif, satirlar = degerlendir(olcum)
    if sinif not in SINIF_RC or sinif == "OLCULEMEDI":
        # degerlendir() OLCULEMEDI URETEMEZ (o yalniz olcum ARIZASINDAN dogar); ureti-
        # yorsa sozlesme bozulmustur -> sessizce yesile dusmek yerine OLCULEMEDI de.
        return ("OLCULEMEDI", SINIF_RC["OLCULEMEDI"],
                ["sinif sozlesmesi bozuldu: degerlendir() %r dondurdu" % (sinif,)], olcum)
    return sinif, SINIF_RC[sinif], satirlar, olcum


# ---------------------------------------------------------------- cikti
def _dilim_satirlari(d):
    """K429: tazelik kaniti HER ZAMAN basilir ("kanit var" ile "kanit YOK" karismasin);
    bayat dilim / ek cekim / basarisiz cekim `⚙` notuyla ILAN edilir (sessiz ikame yok)."""
    if not d:
        return []
    s = []
    if d["durum"] == "TAZE":
        s.append("tazelik kaniti (commits API): TAZE — main HEAD %s (%.0f dk once) kosum "
                 "penceresinde · %d cekim fuzyonu"
                 % (d["aday_sha"], d["aday_yas_dk"], d["cekim"]))
    elif d["durum"] == "TOLERANS":
        s.append("tazelik kaniti (commits API): TOLERANS — main HEAD %s yalniz %.0f dk once "
                 "(< %d dk): kosumu henuz listede olmayabilir, bayatlik KANITLANMADI · %d "
                 "cekim fuzyonu" % (d["aday_sha"], d["aday_yas_dk"], TAZELIK_TOLERANS_DK,
                                    d["cekim"]))
    else:
        s.append("tazelik kaniti: YOK — %s -> hukum YALNIZ %d cekimlik fuzyondan cikti "
                 "(bayat dilim DOGRULANAMADI)" % (d.get("komit_hata") or "aday yok", d["cekim"]))
    if d.get("bayat_cekim") or d["cekim"] > CEKIM_MIN:
        s.append("⚙ BAYAT DILIM: %d cekimin %d'i bayat%s -> taze kesit %s; hukum fuzyon "
                 "penceresinden cikti"
                 % (d["basarili"], d.get("bayat_cekim") or 0,
                    (" (main HEAD %s pencerede YOK)" % d["aday_sha"]) if d["aday_sha"] else "",
                    ("%d. cekimde bulundu" % d["ilk_taze_cekim"]) if d.get("ilk_taze_cekim")
                    else "bulunamadi"))
    if d.get("hatali"):
        s.append("⚙ %d/%d cekim BASARISIZ (%s) — kalan %d cekimle devam edildi"
                 % (d["hatali"], d["cekim"], (d.get("hata_metni") or "")[:100], d["basarili"]))
    return s


def _ozet_satirlari(olcum):
    if olcum is None:
        return []
    s = []
    if olcum["geride"] is None:
        s.append("`%s` isini basariyla kosan kosum: taranan %d kosumda YOK (pencere %d)"
                 % (YAYIN_ISI, olcum.get("taranan", 0), olcum["pencere"]))
    else:
        s.append("canli main'den %d commit geride · en eski bekleyen %s"
                 % (olcum["geride"],
                    "yok" if not olcum["geride"] else "%.0f dk" % olcum["yas_dk"]))
        # YAS TABANI = `deploy` isinin bitisi. Kosumun bitisi AYRI basilir: ikisi bu
        # hatta 47,8 dk'ya kadar ayrisir ve tabani karistirmak yanlis alarm uretmisti.
        s.append("son yayinlanan sha: %s (`%s` isi %s'de BITTI = yayin ani · kosum %s'de "
                 "bitti · kosum %s'de basladi)"
                 % (olcum["son_basarili_sha"], YAYIN_ISI,
                    olcum["yayin_ani"].strftime("%H:%M UTC"),
                    olcum["son_basarili_bitis"].strftime("%H:%M"),
                    olcum["son_basarili_baslangic"].strftime("%H:%M")))
        if olcum["geride"]:
            # UCUNCU ALT SINIR HER ZAMAN BASILIR: "olculdu" ile "olculemedi, eski taban"
            # ayni satirda karismasin (sessiz yesil YOK).
            giris = olcum.get("giris_ani")
            s.append("main'e giris ani: %s · yas tabani: %s"
                     % (giris.strftime("%H:%M UTC (push aktivitesi)") if giris
                        else "%s (eski taban; yas USTTEN olculdu)"
                        % (olcum.get("giris_durum") or GIRIS_OLCULEMEDI),
                        olcum.get("yas_tabani")))
        taslak = olcum.get("taslak_isi")
        if taslak is not None and taslak != "success":
            # OLCULUR ama site tazeligi hakkinda hukum VERMEZ (bkz. modul basligi).
            s.append("⚠ o kosumda `%s` isi `%s` — SITE CANLI ama D1 taslaklari taslak "
                     "kalmis olabilir (Ege yeni urunleri goremez)" % (TASLAK_ISI, taslak))
    s.append("ardisik iptal: %d (aclik esigi %d) · ardisik hata: %d (tikanma esigi %d)"
             % (olcum["ardisik_iptal"], ACLIK_IPTAL_ZINCIR,
                olcum["ardisik_hata"], TIKALI_HATA_ZINCIR))
    # EKSEN 3 HER ZAMAN BASILIR (yandi ya da yanmadi): "olculdu ve temiz" ile "hic
    # olculmedi" ayni satirda karismasin. Esik karsilastirmasi TEK KANONIK YERDE.
    s.append("ardisik YAYINSIZ kosum: %d (esik %d, ayrica yas >= %d dk sarti) · eksen 3 %s"
             % (olcum["ardisik_yayinsiz"], TIKALI_YAYINSIZ_ZINCIR, GECIKME_YAS_DK,
                "KIRMIZI" if eksen_hukumleri(olcum)["yayinsiz_zinciri"] else "temiz"))
    # EKSEN 2 HER ZAMAN BASILIR (yandi ya da yanmadi): "olculdu ve temiz" ile "hic
    # olculmedi" ayni satirda karismasin.
    takilan = olcum.get("takilan_kosum_dk")
    s.append("en uzun KOSAN kosum omru: %s (omur tavani %d dk) · eksen 2 %s"
             % ("yok (kosan/bekleyen kosum YOK)" if takilan is None
                else "%.0f dk (kosum %s)" % (takilan, olcum.get("takilan_kosum_id")),
                KOSUM_OMUR_TAVANI_DK,
                # Esik karsilastirmasi TEK KANONIK YERDE: burada TEKRARLANMAZ.
                "KIRMIZI" if eksen_hukumleri(olcum)["sure_tavani"] else "temiz"))
    s.append("pencere: %d kosum (%d tamamlandi · %d kosuyor/bekliyor) · is duzeyi "
             "sorulan: %d kosum" % (olcum["pencere"], olcum["tamamlanan"],
                                    olcum["calisan"], olcum.get("taranan", 0)))
    s.extend(_dilim_satirlari(olcum.get("dilim")))
    if olcum.get("is_tavanina_dayandi"):
        s.append("⚠ is sorgu TAVANINA (%d) dayanildi — yayinlayan kosum daha geride "
                 "olabilir (alttan olcum)" % IS_SORGU_TAVANI)
    if olcum.get("zincir_pencere_kenarinda"):
        s.append("⚠ zincir PENCERE KENARINDA — gercek zincir daha uzun olabilir "
                 "(alttan olcum)")
    if olcum.get("kirpildi"):
        s.append("⚠ compare 250 commit'te kirpildi — bekleme yasi ALTTAN olculdu")
    return s


def satirlar(getir=api_getir, simdi=None):
    """tools/durum.py bolum 9 icin hazir satirlar (2 bosluk girintili)."""
    sinif, rc, gerekce, olcum = olc_ve_degerlendir(getir=getir, simdi=simdi)
    cikti = ["  %s %s (rc %d)" % (SINIF_ISARET[sinif], sinif, rc)]
    for g in gerekce:
        cikti.append("      %s" % g)
    for o in _ozet_satirlari(olcum):
        cikti.append("      %s" % o)
    if sinif == "OLCULEMEDI":
        cikti.append("      ('sorun yok' DEMEK DEGILDIR — yayin gecikmesi bu kosumda "
                     "OLCULMEDI)")
    return cikti


def rapor(sinif, rc, gerekce, olcum):
    print("=" * 72)
    print("YAYIN GECIKME NOBETCISI — %s" % _simdi().strftime("%Y-%m-%d %H:%M UTC"))
    print("depo: %s · is akisi: %s · dal: %s" % (DEPO, IS_AKISI, DAL))
    print("=" * 72)
    for o in _ozet_satirlari(olcum):
        print("  %s" % o)
    print("")
    print("SONUC: %s %s (cikis kodu %d)" % (SINIF_ISARET[sinif], sinif, rc))
    for g in gerekce:
        print("  - %s" % g)
    if sinif == "OLCULEMEDI":
        print("  ! OLCULEMEDI YESIL DEGILDIR ve KIRMIZI da degildir: bu nobetci hicbir "
              "is akisini bloklamaz.")


# ================================================================= FIKSTURLER
# GERCEK API govdesinin SEKLI tek bir yerde durur (sekil-capasi.json, 1 Agu 2026
# `gh api` ciktisindan uretildi; kisisel veri sabit fikstur degerleriyle degistirildi).
# Senaryo fiksturleri o capayi SABLON alir ve YALNIZ VAR OLAN alanlari ezer ->
# uydurma alan icat EDILEMEZ ([[nobetci-fikstur-sekli]], [[ikiz-tanim-sessiz-ayrisma]]).
def sekil_capasi(yol=None):
    yol = yol or SEKIL_CAPASI
    if not os.path.exists(yol):
        raise OlcumHatasi("sekil capasi YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        capa = json.load(f)
    for a in ("kosum", "karsilastirma", "isler"):
        if a not in capa:
            raise OlcumHatasi("sekil capasinda `%s` YOK" % a)
    if not (isinstance(capa["isler"].get("jobs"), list) and capa["isler"]["jobs"]):
        raise OlcumHatasi("sekil capasi: `isler.jobs` bos ya da liste degil — is duzeyi "
                          "fiksturleri SABLONSUZ kalir")
    return capa


def _bindir(sablon, ustyazim, iz="kok"):
    """Sablona derin bindirme. Var OLMAYAN alani ezmek YASAK (uydurma alan kapisi).

    `_sil`: sablonda VAR OLAN bir alani KALDIRIR (bozuk-sekil fiksturleri icin).
    """
    if not isinstance(ustyazim, dict):
        return copy.deepcopy(ustyazim)
    sonuc = copy.deepcopy(sablon)
    if not isinstance(sonuc, dict):
        raise OlcumHatasi("fikstur bindirme: %s sablonda sozluk degil" % iz)
    for silinecek in ustyazim.get("_sil", []):
        if silinecek not in sonuc:
            raise OlcumHatasi("fikstur `_sil`: %s.%s sablonda ZATEN yok"
                              % (iz, silinecek))
        del sonuc[silinecek]
    for k, v in ustyazim.items():
        if k.startswith("_"):
            continue
        if k not in sonuc:
            raise OlcumHatasi(
                "fikstur UYDURMA ALAN uretti: %s.%s sekil capasinda YOK — fikstur "
                "gercek API sekline uymak ZORUNDA" % (iz, k))
        sonuc[k] = _bindir(sonuc[k], v, "%s.%s" % (iz, k))
    return sonuc


# Fikstur dosyasinin TANINAN ust seviye anahtarlari (`fikstur_yukle(ust=...)` bunlarla sinirli).
FIKSTUR_ANAHTARLARI = frozenset((
    "_aciklama", "_beklenen", "_simdi", "_isler", "_hata", "_karsilastirma_tabani",
    "_aktivite_hata", "_komit_hata", "_cekimler", "karsilastirma",
    "karsilastirma_tabanlari", "komitler", "aktivite", "kosumlar"))


def fikstur_yolu(ad):
    return os.path.join(FIKSTUR_DIZIN, ad if ad.endswith(".json") else ad + ".json")


def fikstur_adlari():
    return sorted(os.path.basename(y)[:-5]
                  for y in glob.glob(os.path.join(FIKSTUR_DIZIN, "*.json"))
                  if os.path.basename(y) != "sekil-capasi.json")


def fikstur_yukle(ad, capa=None, ust=None):
    """Fikstur -> (getir, simdi, beklenen_sinif, aciklama).

    `ust` (K429): fikstur dosyasinin ust seviye anahtarlarini YUKLEMEDEN ONCE ezen/ekleyen
    sozluk — kabul testi bir senaryonun turevini (or. `_cekimler` farkli, `_komit_hata` var)
    DOSYA ACMADAN kurar. Yalniz FIKSTUR_ANAHTARLARI'ndaki anahtarlar kabul edilir (yazim
    hatasi sessizce yok sayilmaz: OlcumHatasi).
    """
    yol = fikstur_yolu(ad)
    if not os.path.exists(yol):
        raise OlcumHatasi("fikstur YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        f_ = json.load(f)
    for anahtar, deger in (ust or {}).items():
        if anahtar not in FIKSTUR_ANAHTARLARI:
            raise OlcumHatasi("fikstur %s: ust-yazim anahtari `%s` TANINMIYOR (izinli: %s)"
                              % (ad, anahtar, ", ".join(sorted(FIKSTUR_ANAHTARLARI))))
        f_[anahtar] = deger
    capa = capa or sekil_capasi()
    beklenen = f_.get("_beklenen")
    if beklenen not in SINIF_RC:
        raise OlcumHatasi("fikstur %s: `_beklenen` gecersiz (%r)" % (ad, beklenen))
    simdi = _iso(f_["_simdi"], "fikstur `_simdi`") if "_simdi" in f_ else None

    hata = f_.get("_hata")
    kosumlar = [_bindir(capa["kosum"], k, "kosum[%d]" % i)
                for i, k in enumerate(f_.get("kosumlar", []))]

    # ---- IS (job) duzeyi govdeleri -------------------------------------------------
    # `_isler` = {"<kosum id>": {"<is adi>": <deger>}} ve <deger> IKI bicimden biridir:
    #     "success"                                   -> yalniz conclusion
    #     {"conclusion": "...", "completed_at": "..."} -> conclusion + YAYIN ANI
    # Govde SABLONU sekil capasindan gelir -> alan adlari uydurulAMAZ.
    #
    # 🔴 `completed_at` BILDIRILMEMISSE kosumun `updated_at`'i kullanilir, yani "yayin
    # ani = kosum sonu" varsayimi. Bu varsayim GERCEK hatta YANLISTIR (olculen fark
    # 47,8 dk'ya cikti) ve yalnizca bu eksenden ONCE yazilmis fiksturlerin anlamini
    # KORUMAK icin vardir. Yas tabani ekseninin fiksturleri `completed_at`'i ACIKCA
    # bildirmek ZORUNDADIR — kabul testi Y7 bunu nobetler.
    #
    # `_isler` HIC verilmemisse ESKI anlam korunur: kosumun genel conclusion'i `deploy`
    # isine yansitilir (kosum duzeyi == is duzeyi). `_isler` VERILMISSE artik sozlesme
    # odur: sorulan bir kosum orada YOKSA fikstur OLCULEMEDI verir (sessiz varsayim YOK).
    is_ustyazim = f_.get("_isler")
    is_sablonu = capa["isler"]["jobs"][0]

    def _is_govdesi(adlar_degerler, varsayilan_bitis, iz):
        isler = []
        for is_adi, deger in adlar_degerler.items():
            if isinstance(deger, dict):
                bilinmeyen = sorted(set(deger) - {"conclusion", "completed_at"})
                if bilinmeyen:
                    raise OlcumHatasi("fikstur %s: %s.%s icinde bilinmeyen anahtar: %s "
                                      "(izinli: conclusion, completed_at)"
                                      % (ad, iz, is_adi, ", ".join(bilinmeyen)))
                son = deger.get("conclusion")
                bitis = deger.get("completed_at", varsayilan_bitis)
            else:
                son, bitis = deger, varsayilan_bitis
            isler.append(_bindir(is_sablonu,
                                 {"name": is_adi, "status": "completed",
                                  "conclusion": son, "completed_at": bitis},
                                 "%s.%s" % (iz, is_adi)))
        return {"total_count": len(isler), "jobs": isler}

    def _kosum(kosum_id):
        k = next((k for k in kosumlar if str(k.get("id")) == str(kosum_id)), None)
        if k is None:
            raise OlcumHatasi("fikstur %s: is sorulan kosum %s listede YOK"
                              % (ad, kosum_id))
        return k

    def _kosum_isleri(kosum_id):
        k = _kosum(kosum_id)
        varsayilan_bitis = k.get("updated_at")
        if is_ustyazim is None:
            return _is_govdesi({YAYIN_ISI: k.get("conclusion")}, varsayilan_bitis, "_miras")
        if str(kosum_id) not in is_ustyazim:
            raise OlcumHatasi("fikstur %s: kosum %s icin `_isler` TANIMSIZ ama nobetci "
                              "is duzeyini sordu" % (ad, kosum_id))
        return _is_govdesi(is_ustyazim[str(kosum_id)], varsayilan_bitis,
                           "_isler[%s]" % kosum_id)
    def _kars_govdesi(kars_ust, iz):
        commit_ust = kars_ust.get("commits")
        k = _bindir({a: v for a, v in capa["karsilastirma"].items() if a != "commits"},
                    {a: v for a, v in kars_ust.items() if a != "commits"}, iz)
        if commit_ust is None:
            k["commits"] = copy.deepcopy(capa["karsilastirma"]["commits"])
        else:
            sablon = capa["karsilastirma"]["commits"][0]
            k["commits"] = [_bindir(sablon, c, "%s.commits[%d]" % (iz, i))
                            for i, c in enumerate(commit_ust)]
        return k

    kars_ust = f_.get("karsilastirma")
    kars = None if kars_ust is None else _kars_govdesi(kars_ust, "karsilastirma")
    # 🔴 K429: compare govdesi SORULAN TABANA gore secilebilir. Bayat bir kesit baska bir
    # `son yayinlanan sha`ya (eski bir kosuma) baglanir; bu durumda compare AYNI sha icin
    # ayni gercegi (ahead_by 133 gibi) dondurur — sabit TEK govde bu iki dunyayi birlikte
    # temsil EDEMEZ. `karsilastirma_tabanlari` = {"<taban sha>": <karsilastirma govdesi>};
    # eslesmezse `karsilastirma` (varsa) kullanilir.
    kars_harita = {str(t).lower(): _kars_govdesi(u, "karsilastirma_tabanlari[%s]" % t)
                   for t, u in (f_.get("karsilastirma_tabanlari") or {}).items()}

    # ---- MAIN'E GIRIS ANI (activity) govdesi ---------------------------------------
    # `aktivite` = [{before, after, timestamp, ...}] (sablon: capa["aktivite"][0]).
    # VERILMEMISSE uc SORULUNCA OlcumHatasi doner = gercek hattaki "giris olculemedi" hali
    # (26 Eyl'den ONCE yazilmis fiksturler boylece ESKI tabanla, notlu, yargilanir).
    # `_aktivite_hata` = uc hata versin (yetki/ag): ayni sinif, ACIK beyanla.
    akt_ust = f_.get("aktivite")
    akt_hata = f_.get("_aktivite_hata")
    akt = None
    if akt_ust is not None:
        if not (isinstance(capa.get("aktivite"), list) and capa["aktivite"]):
            raise OlcumHatasi("fikstur %s `aktivite` veriyor ama sekil capasinda "
                              "`aktivite` sablonu YOK" % ad)
        akt = [_bindir(capa["aktivite"][0], a, "aktivite[%d]" % i)
               for i, a in enumerate(akt_ust)]

    # ---- BAYAT DILIM (K429): commit listesi + cekim senaryosu ----------------------------
    # `komitler` = [{sha, commit.committer.date, ...}] (sablon: capa["komitler"][0]; bagimsiz
    # TAZELIK KANITI). VERILMEMISSE uc SORULUNCA OlcumHatasi doner = "tazelik kaniti YOK"
    # hali (K429'dan ONCE yazilmis fiksturler boylece yalniz fuzyonla, notlu, yargilanir).
    # `_komit_hata` = commits ucu hata versin (ag/yetki): ayni sinif, ACIK beyanla.
    # `_cekimler` = ["taze" | "bayat:<N>" | "hata:<metin>", ...]: SIRAYLA her `runs`
    # cagrisinin donecegi kesit; liste bitince SON madde tekrarlanir. "bayat:N" gercek listenin
    # EN YENI N kosumunu GORMEYEN (geride kalmis replika) kesittir; VERILMEMISSE hep "taze".
    kom_ust = f_.get("komitler")
    kom_hata = f_.get("_komit_hata")
    kom = None
    if kom_ust is not None:
        if not (isinstance(capa.get("komitler"), list) and capa["komitler"]):
            raise OlcumHatasi("fikstur %s `komitler` veriyor ama sekil capasinda `komitler` "
                              "sablonu YOK" % ad)
        kom = [_bindir(capa["komitler"][0], c, "komitler[%d]" % i)
               for i, c in enumerate(kom_ust)]
    cekim_ust = f_.get("_cekimler")
    if cekim_ust is not None and not (isinstance(cekim_ust, list) and cekim_ust):
        raise OlcumHatasi("fikstur %s: `_cekimler` bos ya da liste degil" % ad)
    runs_sayaci = [0]

    def _runs_govdesi():
        spec = "taze" if cekim_ust is None else cekim_ust[min(runs_sayaci[0],
                                                              len(cekim_ust) - 1)]
        runs_sayaci[0] += 1
        tur, _, arg = str(spec).partition(":")
        if tur == "hata":
            raise OlcumHatasi(arg or "cekim hatasi (fikstur)")
        if tur == "bayat":
            if not arg.isdigit():
                raise OlcumHatasi("fikstur %s: `bayat:<N>` N sayi olmali (%r)" % (ad, spec))
            kesit = kosumlar[int(arg):]
        elif tur == "taze":
            kesit = kosumlar
        else:
            raise OlcumHatasi("fikstur %s: bilinmeyen cekim turu %r (taze|bayat:N|hata:..)"
                              % (ad, spec))
        return {"total_count": len(kesit), "workflow_runs": copy.deepcopy(kesit)}

    def getir(yol_, zaman_asimi=25, etiket="api"):  # noqa: ARG001 — imza api_getir ile AYNI
        if hata:
            raise OlcumHatasi(hata)
        if "/activity?" in yol_:
            if akt_hata:
                raise OlcumHatasi(akt_hata)
            if akt is None:
                raise OlcumHatasi("fikstur %s: aktivite govdesi TANIMSIZ" % ad)
            return copy.deepcopy(akt)
        if "/commits?" in yol_:
            if kom_hata:
                raise OlcumHatasi(kom_hata)
            if kom is None:
                raise OlcumHatasi("fikstur %s: commit listesi TANIMSIZ" % ad)
            return copy.deepcopy(kom)
        if "/actions/workflows/" in yol_:
            return _runs_govdesi()
        if "/actions/runs/" in yol_ and "/jobs" in yol_:
            return _kosum_isleri(yol_.split("/actions/runs/")[1].split("/")[0])
        if "/compare/" in yol_:
            taban = yol_.split("/compare/")[1].split("...")[0]
            govde = kars_harita.get(taban.lower(), kars)
            if govde is None:
                raise OlcumHatasi("fikstur %s: compare govdesi TANIMSIZ ama nobetci "
                                  "sordu (%s)" % (ad, yol_))
            # Fikstur, DOGRU tabani sorup sormadigimizi da nobetler: taban SHA'si son
            # basarili kosumun SHA'si olmali (yanlis taban = sessiz yanlis olcum).
            beklenen_taban = f_.get("_karsilastirma_tabani")
            if beklenen_taban and taban != beklenen_taban:
                raise OlcumHatasi("fikstur %s: compare TABANI yanlis — beklenen %s, "
                                  "sorulan %s" % (ad, beklenen_taban, taban))
            return copy.deepcopy(govde)
        raise OlcumHatasi("fikstur %s: bilinmeyen API yolu: %s" % (ad, yol_))

    return getir, simdi, beklenen, f_.get("_aciklama", "")


# ---------------------------------------------------------------- kendini test
def _fikstur_ham(ad):
    try:
        with open(fikstur_yolu(ad), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def yg_etkin_kusuru():
    """etkin_sonuc sozlesmesi: "yayinladi" YALNIZ `deploy` isinin success'inden dogar."""
    vakalar = (
        ({"conclusion": "failure"}, {YAYIN_ISI: "success"}, "success"),
        ({"conclusion": "failure"}, {YAYIN_ISI: "skipped"}, "failure"),
        ({"conclusion": "cancelled"}, {}, "cancelled"),
        ({"conclusion": "success"}, {YAYIN_ISI: "skipped"}, "yayinsiz"),
    )
    return any(etkin_sonuc(k, i) != b for k, i, b in vakalar)


def _fikstur_bitis_bildiriyor(ham):
    """Fikstur `_isler` icinde ACIK bir `completed_at` bildiriyor mu (yas tabani)."""
    for _, isler in (ham.get("_isler") or {}).items():
        for _, deger in (isler or {}).items():
            if isinstance(deger, dict) and deger.get("completed_at"):
                return True
    return False


# ================================================================= EKSEN NOBETLERI
# 🔴 TEK KAYNAK: her nobet SADECE burada yazilir; hem `--kendini-test` hem
# tools/yayin-gecikme-test.py bu listeleri OKUR. Ikinci bir kopya yazmak, kabul testiyle
# CI'nin sessizce ayrismasi demektir ([[ikiz-tanim-sessiz-ayrisma]]). Fonksiyonlar
# EKSEN BASINA ayridir: bir eksen kirmizi yandiginda HANGI eksen oldugu belirsiz kalmaz
# ([[hukum-yanlis-birimde]]).
def sozlesme_kusurlari():
    """Y2 — sinif/cikis kodu sozlesmesi + esiklerin OLCULEN tabana gore konumu."""
    kusur = []
    if SINIF_RC["OLCULEMEDI"] == 0:
        kusur.append("SOZLESME: OLCULEMEDI cikis kodu 0 (YESIL ile karisiyor)")
    if len(set(SINIF_RC.values())) != len(SINIF_RC):
        kusur.append("SOZLESME: iki sinif AYNI cikis kodunu paylasiyor")
    if not (0 < GECIKME_YAS_DK < TIKALI_YAS_DK):
        kusur.append("SOZLESME: yas esikleri sirali degil (%s/%s)"
                     % (GECIKME_YAS_DK, TIKALI_YAS_DK))
    if ACLIK_IPTAL_ZINCIR <= OLCULEN_SAGLIKLI_IPTAL_TAVANI:
        kusur.append("SOZLESME: aclik esigi (%d) OLCULEN saglikli iptal tavaninin (%d) "
                     "ustunde DEGIL — normal eszamanlilik iptali alarm uretir"
                     % (ACLIK_IPTAL_ZINCIR, OLCULEN_SAGLIKLI_IPTAL_TAVANI))
    if TIKALI_HATA_ZINCIR <= OLCULEN_SAGLIKLI_HATA_TAVANI:
        kusur.append("SOZLESME: tikanma esigi (%d) OLCULEN saglikli hata tavaninin (%d) "
                     "ustunde DEGIL — gurultu hatalari alarm uretir"
                     % (TIKALI_HATA_ZINCIR, OLCULEN_SAGLIKLI_HATA_TAVANI))
    if TIKALI_YAYINSIZ_ZINCIR <= OLCULEN_SAGLIKLI_YAYINSIZ_TAVANI:
        kusur.append("SOZLESME: yayinsiz zincir esigi (%d) OLCULEN saglikli tavanin (%d) "
                     "ustunde DEGIL — tek gurultu kosumu alarm uretir"
                     % (TIKALI_YAYINSIZ_ZINCIR, OLCULEN_SAGLIKLI_YAYINSIZ_TAVANI))
    if TIKALI_YAYINSIZ_ZINCIR >= TIKALI_HATA_ZINCIR:
        kusur.append("SOZLESME: yayinsiz zincir esigi (%d) hata zinciri esiginden (%d) "
                     "kucuk DEGIL — EKSEN 3 daha GENIS bir sinifi DAHA GEC yakalar, yani "
                     "5 Agu'da olculen kor nokta geri gelir"
                     % (TIKALI_YAYINSIZ_ZINCIR, TIKALI_HATA_ZINCIR))
    if set(HATA_SONUCLARI) - set(YAYINSIZ_SONUCLARI):
        kusur.append("SOZLESME: YAYINSIZ_SONUCLARI, HATA_SONUCLARI'nin USTKUMESI DEGIL — "
                     "EKSEN 3 hata zincirinin gordugunu goremez hale gelmis")
    if "cancelled" in YAYINSIZ_SONUCLARI:
        kusur.append("SOZLESME: `cancelled` YAYINSIZ_SONUCLARI'na girmis — kuyrukta iptal "
                     "bu depoda NORMAL bir olaydir, zincire katilmasi yanlis alarm uretir")
    # 🔴 EKSEN 3'un yas kapisi: zincir TEK BASINA yeterli OLMAMALI (olculen bedel:
    # 2,51 alarm/gun -> 0,89 alarm/gun; ek gercek olay 0).
    yalniz_zincir = {"geride": 3, "yas_dk": GECIKME_YAS_DK - 1.0, "ardisik_iptal": 0,
                     "ardisik_hata": 0, "ardisik_yayinsiz": TIKALI_YAYINSIZ_ZINCIR + 5,
                     "son_basarili_sha": "abc12345", "pencere": 1, "tamamlanan": 1,
                     "taranan": 1, "takilan_kosum_dk": None, "takilan_kosum_id": None}
    if eksen_hukumleri(yalniz_zincir)["yayinsiz_zinciri"]:
        kusur.append("SOZLESME: yayinsiz zincir ekseni YAS kapisini KAYBETMIS — zincir "
                     "tek basina alarm uretiyor (olculen bedel: 2,51 alarm/gun, ek gercek "
                     "olay 0; yanlis alarm = kapatilan nobetci)")
    if TIKALI_YAS_DK <= OLCULEN_SAGLIKLI_YAS_TAVANI_DK:
        kusur.append("SOZLESME: tikanma yas esigi (%d dk) OLCULEN saglikli tepe yasinin "
                     "(%.1f dk) ustunde DEGIL — normal kuyruk alarm uretir"
                     % (TIKALI_YAS_DK, OLCULEN_SAGLIKLI_YAS_TAVANI_DK))
    # OLCULEMEDI'nin HER kaynagi rc 2 vermeli (ag yok / yetki yok / govde bozuk).
    # 🔴 `OlcumHatasi` LISTEDE OLMAK ZORUNDA (2 Agu, mutasyonla OLCULDU): once yalnizca
    # FileNotFoundError/ValueError sinaniyordu ve ikisi de GENEL `except Exception`
    # kolundan doner. `except OlcumHatasi` kolunu "AKIYOR" dondurecek sekilde bozan bir
    # mutant bu nobetten SESSIZCE geciyordu — yani nobet, olcmedigi bir kolu kutsuyordu.
    # 🔴 SAHTE GETIRICININ IMZASI `api_getir` ILE BIREBIR AYNI OLMAK ZORUNDA (2 Agu,
    # mutasyonla OLCULDU): `etiket` parametresi `etiket_` diye yeniden adlandirilinca
    # gercek cagri (`getir(yol, etiket="runs")`) TypeError firlatti, TypeError de GENEL
    # `except Exception` kolundan dondu — yani nobet UC vakada da AYNI kolu olcuyordu ve
    # hedefledigi `except OlcumHatasi` kolu HIC SINANMIYORDU ([[nobetci-fikstur-sekli]]).
    for ne, patlat in (("gh yok", FileNotFoundError("gh")),
                       ("beklenmeyen tip", ValueError("bozuk")),
                       ("olcum hatasi", OlcumHatasi("sinama: govde anlasilmadi"))):
        def _patlayan(yol_, zaman_asimi=25, etiket="api", _e=patlat):   # noqa: ARG001
            raise _e
        sinif, rc, _, _ = olc_ve_degerlendir(getir=_patlayan)
        if not (sinif == "OLCULEMEDI" and rc == 2):
            kusur.append("FAIL-CLOSED: %s -> %s/rc %d (OLCULEMEDI olmaliydi)"
                         % (ne, sinif, rc))
    return kusur


def is_duzeyi_kusurlari(adlar=None):
    """Y5 — "yayin indi mi" YALNIZ `deploy` isinden okunur (kosum duzeyinden DEGIL)."""
    kusur = []
    if yg_etkin_kusuru():
        kusur.append("SOZLESME: etkin sonuc `%s` isinden DOGMUYOR (kosum duzeyine "
                     "geri donulmus olabilir)" % YAYIN_ISI)
    adlar = fikstur_adlari() if adlar is None else adlar
    if not any("_isler" in _fikstur_ham(a) for a in adlar):
        kusur.append("SOZLESME: HICBIR fikstur `_isler` bildirmiyor — is duzeyi ekseni "
                     "FIKSTURSUZ kalmis (sessizce kosum duzeyine donebilir)")
    return kusur


def yas_tabani_kusurlari(adlar=None):
    """Y7 — yas tabani YAYIN ANIDIR; ekseni fiiliyatta olcen fikstur var mi."""
    kusur = []
    adlar = fikstur_adlari() if adlar is None else adlar
    if not any(_fikstur_bitis_bildiriyor(_fikstur_ham(a)) for a in adlar):
        kusur.append("SOZLESME: HICBIR fikstur `%s.completed_at` bildirmiyor — YAS TABANI "
                     "ekseni fiiliyatta olculmuyor (taban sessizce kosum baslangicina "
                     "donebilir)" % YAYIN_ISI)
    return kusur


def omur_ekseni_kusurlari():
    """Y8 — kosum omur ekseni: `ahead_by` kapisinin ONUNDE ve yanlis alarm uretmiyor.

    Olcumu TAKLIT ETMEDEN dogrudan `degerlendir` uzerinde sinanir: eksenin kapiya gore
    KONUMU bir kod olgusudur, fiksturle degil birim iddiayla tutulur.
    """
    kusur = []
    bekleyensiz = {"geride": 0, "yas_dk": 0.0, "ardisik_iptal": 0, "ardisik_hata": 0,
                   "ardisik_yayinsiz": 0,
                   "son_basarili_sha": "abc12345", "pencere": 1, "tamamlanan": 1,
                   "taranan": 1, "takilan_kosum_dk": KOSUM_OMUR_TAVANI_DK + 1.0,
                   "takilan_kosum_id": 1}
    if degerlendir(bekleyensiz)[0] != "TIKALI":
        kusur.append("SOZLESME: kosum omur ekseni `ahead_by == 0` kapisinin ARKASINA "
                     "dusmus — takilan kosum bekleyen icerik yokken GORUNMEZ oluyor")
    normal = dict(bekleyensiz, takilan_kosum_dk=OLCULEN_KOSUM_OMRU_MAX_DK)
    if degerlendir(normal)[0] != "AKIYOR":
        kusur.append("SOZLESME: OLCULEN en uzun kosum omru (%.1f dk) bile alarm uretiyor "
                     "— eksen 2 yanlis alarm makinesi" % OLCULEN_KOSUM_OMRU_MAX_DK)
    if KOSUM_OMUR_TAVANI_DK <= OLCULEN_KOSUM_OMRU_MAX_DK:
        kusur.append("SOZLESME: kosum omur tavani (%d dk) OLCULEN en uzun kosum omrunun "
                     "(%.1f dk) ustunde DEGIL — normal suren kosum alarm uretir"
                     % (KOSUM_OMUR_TAVANI_DK, OLCULEN_KOSUM_OMRU_MAX_DK))
    return kusur


def sizinti_kusurlari():
    """Y6 — `gh` stderr'i disari SIZMAZ ama teshis SINIFI da yok edilmez."""
    kusur = []
    ornek = "gh: Not Found (HTTP 404) https://api.github.com/repos/X/actions/runs/1/jobs"
    ozet = gh_hata_sinifi(ornek)
    if "https://" in ozet or ornek in ozet:
        kusur.append("SIZINTI: `gh` stderr'i ozetten OLDUGU GIBI cikiyor")
    if "404" not in ozet:
        kusur.append("TESHIS: hata sinifi ozetten SILINMIS (teshis tamamen yok edilmis)")
    return kusur


def kendini_test(yazdir=True):
    """AGSIZ fikstur kabulu. 0 = hepsi gecti, 1 = en az bir kusur."""
    kusur = []
    gecen = 0
    adlar = fikstur_adlari()
    if not adlar:
        print("KUSUR: fikstur YOK (%s) — bu nobetcinin kabulu OLCULEMEZ" % FIKSTUR_DIZIN)
        return 1
    for ad in adlar:
        try:
            getir, simdi, beklenen, aciklama = fikstur_yukle(ad)
        except OlcumHatasi as e:
            kusur.append("%s: fikstur YUKLENEMEDI — %s" % (ad, e))
            continue
        sinif, rc, gerekce, _ = olc_ve_degerlendir(getir=getir, simdi=simdi)
        tamam = (sinif == beklenen and rc == SINIF_RC[beklenen])
        if tamam:
            gecen += 1
        else:
            kusur.append("%s: beklenen %s (rc %d), olculen %s (rc %d) — %s"
                         % (ad, beklenen, SINIF_RC[beklenen], sinif, rc,
                            "; ".join(gerekce)[:200]))
        if yazdir:
            print("  %s %-30s -> %-10s rc %d   %s"
                  % ("✔" if tamam else "✘", ad, sinif, rc, aciklama[:60]))

    # SOZLESME NOBETLERI — fiksturlerden BAGIMSIZ, kod icindeki iddialar.
    # KOPYA YOK: hepsi eksen basina ayrilmis TEK KAYNAK fonksiyonlardan gelir; kabul
    # testi (tools/yayin-gecikme-test.py) AYNI fonksiyonlari eksen koduyla okur.
    for _liste in (sozlesme_kusurlari(), is_duzeyi_kusurlari(adlar),
                   yas_tabani_kusurlari(adlar), omur_ekseni_kusurlari(),
                   sizinti_kusurlari()):
        kusur.extend(_liste)

    if yazdir:
        print("")
        print("fikstur: %d/%d gecti · sozlesme nobetleri: %s"
              % (gecen, len(adlar), "TEMIZ" if not kusur else "KUSURLU"))
        for k in kusur:
            print("  ✘ %s" % k)
    return 1 if kusur else 0


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="Yayin gecikme nobetcisi")
    ap.add_argument("--kendini-test", action="store_true",
                    help="AGSIZ fikstur kabulu (0 = hepsi gecti)")
    ap.add_argument("--fikstur", metavar="AD", help="tek fiksturu kostur ve raporla")
    ap.add_argument("--liste", action="store_true", help="fiksturleri listele")
    # 🔴 --alarm — ZAMANLANMIS EV ICIN CIKIS KODU ESLEMESI (3 Agu 2026).
    # Bu nobetci 2 Agu'da yazildi ama CANLI kolu HICBIR YERE BAGLANMAMISTI: yalniz
    # `tools/durum.py` (elle pano) cagiriyordu, deploy.yml'de ise SADECE agsiz fikstur
    # kabulu kosuyordu. Yani "yayin ne kadar suredir inmiyor" sorusunu SOREN kimse yoktu
    # ve 3 Agu'daki 142,1 dk'lik bosluk ancak parite testi kirmizi yaninca fark edildi.
    # Kablolamanin onundeki TEK engel cikis kodlariydi: GECIKME (rc 1) bir UYARIDIR ve
    # olculen tabanda 40 dongunun 4'u esigi asiyor -> zamanlanmis bir ev her ~3-4 saatte
    # bir kirmizi yanardi. Yanlis alarm = kapatilan nobetci ([[kapi-disiplin-ilkesi]]).
    # ESLEME BEYAN EDILMISTIR, kabukta cikis kodu YUTULMAZ (o yazim beyansiz fail-open
    # sayilir — is-akisi-kapisi Bolum D):
    #     AKIYOR (0) · GECIKME (1)          -> rc 0, satir GORUNUR kalir
    #     OLCULEMEDI (2) · TIKALI (3) · ACLIK (4) -> rc DEGISMEZ (kosum KIRMIZI yanar)
    # SINIF ADI ve rc'nin kendisi HER HALUKARDA basilir; --alarm hukmu SUSTURMAZ,
    # yalnizca UYARI seviyesini kosum kirmizisina cevirmez.
    ap.add_argument("--alarm", action="store_true",
                    help="zamanlanmis ev: GECIKME (rc 1) uyari sayilir, rc 0 doner; "
                         "OLCULEMEDI/TIKALI/ACLIK kendi rc'siyle KIRMIZI yakar")
    a = ap.parse_args(argv)

    if a.liste:
        for ad in fikstur_adlari():
            print(ad)
        return 0
    if a.kendini_test:
        return kendini_test()
    if a.fikstur:
        try:
            getir, simdi, beklenen, _ = fikstur_yukle(a.fikstur)
        except OlcumHatasi as e:
            print("FIKSTUR HATASI: %s" % e)
            return 2
        sinif, rc, gerekce, olcum = olc_ve_degerlendir(getir=getir, simdi=simdi)
        rapor(sinif, rc, gerekce, olcum)
        print("  (fikstur beklentisi: %s)" % beklenen)
        return rc

    sinif, rc, gerekce, olcum = olc_ve_degerlendir()
    rapor(sinif, rc, gerekce, olcum)
    if a.alarm and sinif == "GECIKME":
        print("  (--alarm: GECIKME UYARI seviyesidir, kosum kirmizi YAKILMADI; "
              "TIKALI/ACLIK/OLCULEMEDI kendi cikis koduyla kirmizi yakar)")
        return 0
    return rc


if __name__ == "__main__":
    sys.exit(main())
