#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/spec-ifsa-kapisi.py — IZLENEN dosyalarin ANLATIM YUZEYINDE (md + yorum +
belge dizesi + konfigurasyon beyani) TASARIM/TOPOLOJI IFSASINI olcen nobetci.
Depo PUBLIC (Pruvo138/pruvo); bu kapi o yuzeyin ICERIGINE bakar.

NEDEN VAR (4 Agu 2026, iki ayri olcum)
───────────────────────────────────────
1) 21 izlenen mimar spec'i (1.979 satir) tarandi: 28 bulgu, 10'u YUKSEK. Dogrudan
   sir/anahtar DEGERI 0 — ifsa TASARIMDA ve TOPOLOJIDE.
2) Bagimsiz guvenlik turu olctu ki KAYNAK, BELGEDEN FAZLA IFSA EDIYOR: yonetim
   worker'inin bas yorum blogu tum uc envanterini, iki sir degisken adini, iki baslik
   adini ve cerez adini TEK yerde topluyor; konfigurasyon dosyasi ozel kova adini DUZ
   METIN tasiyor; bir yorum kabul edilmis ama KAPATILMAMIS bir zayifligi beyan ediyor.
   Yani yalniz `.md`ye bakan bir kapi EN BUYUK YUZEYI olcmeden yesil yanardi.

Ve bu yuzeyin ICERIGINI okuyan HICBIR KAPI YOKTU:
  * tools/kisisel-veri-test.py — bloklayici, ama ekseni DOSYA ADI; icerik taramasi
    KASITLA disarida (gerekcesinde "mesru mimar belgelerini yakma riski").
  * tools/mimar-kod-kilidi.py — `.md` her yerde kilit muafi.
Bosluk kaza degil, BILINCLI bir karardi ve yanlis-pozitif korkusu HAKLIYDI. Bu kapi o
korkuyu OLCUMLE cozer: gercek bulgudan turemis dar eksenler, olculmus yuzey ayrimi ve
YOL DEGIL ICERIK bagli muafiyet.

🔴 BU KAPI TEMIZLIK YAPMAZ. Bulunan satirlarin duzeltilmesi AYRI karardir (Okan).

DURUM (5 Agu 2026): kapi TEMIZ (0 isabet). Iki is birlikte yapildi:
  (1) KAYNAK ONARIMI — 4 gercek ifsa (F: yonetim kimlik yolundaki uzunluk-bagimli
      karsilastirma KAPATILDI; D: hesap tanimlayicisi 13/13 kaynaktan kaldirildi;
      E: iki belgedeki islem ayrintisi git-disi arsive tasindi) + 2 supheli yargilandi.
  (2) DESEN DARALTMASI — asagidaki EKO ELEMESI. Once 164 isabet vardi ve OLCULDU ki
      158'i (%96,3) "silsen de ifsa yerinde kalir" sinifindaydi; 4 gercek bulgu o
      gurultunun icinde saklanmisti. Daraltma jetonu ICRA yuzeyinde de gecen ANLATIM
      satirini ihlal saymaz — ama sentetik jeton sondasi ALTI EKSENDE de KIRMIZI yanar
      (fail-open kontrolu; IDDIA-EKO1 + MUT-EKO-GENIS bunu capalar).

🔴 YUZEY AYRIMI — ISLEVI GEREGI TASINAN AD KAPIYA GIRMEZ
─────────────────────────────────────────────────────────
Kaynak kod bir sir degiskeninin ADINI, bir ucun YOLUNU ve bir kovanin ADINI TASIMAK
ZORUNDADIR — worker'in calismasi buna baglidir. Bunu kirmizi yakmak her push'ta yayini
durdurur ve kapiyi cope atardi. Bu yuzden her satir IKI YUZEYDEN birine ayrilir:
  ICRA    — calisan ifade (`env.<AD>` okumasi, yonlendirme karsilastirmasi, dize
            yukleri). KACINILMAZ. KAPI BUNU HIC GORMEZ.
  ANLATIM — mekanizmayi ANLATAN metin: `.md` satirlari · `//`, `/* */`, `#` yorumlari ·
            Python BELGE DIZELERI (docstring). KACINILABILIR. KAPI BUNU OLCER.
  BEYAN   — konfigurasyon dosyasinin (`*.toml`) deger satirlari. Bir ozel kaynagin ADI
            (kova, hesap) PUBLIC bir konfigurasyonda durmak ZORUNDA DEGILDIR (baglama
            izlenmeyen dosyadan da verilebilir) -> YALNIZ A ve D ekseni buna bakar.
Ayrim OLCULDU (izlenen 489 dosya): ayni desenler ICRA yuzeyinde EZICI COGUNLUKTA
(or. uc yolu 299 icra / 77 anlatim; kimlik jetonu 322 icra / kapsam-ici cok az).
Kapsami ICRA'ya genisletmek toptan muafiyet demekti — yani kapinin OLUMU
([[kapi-kapsam-genisletme-tuzagi]]). Ayrim IDDIA-YUZEY1/YUZEY2 + iki AYIRT EDICI
mutantla (MUT-YUZEY-KOR / MUT-YUZEY-GENIS) KANITLANIR.
🔴 BEYAN EDILMIS SINIR (fail-open yon, bilincli): Python BELGE DIZESI `ast` ile
   belirlenir; degisken/sabit'e ATANMIS coklu-tirnak dizeler (mutasyon araclarinin
   kod yukleri) ANLATIM DEGILDIR ve olculmez — onlar kodun kendisidir. `.html`,
   `.json`, `.sql` yorumlari bu turda kapsam DISIDIR ve OLCULDUGU IDDIA EDILMEZ.

🔴 TESHIS MASKELI — CIKTI SIZDIRMAZ
────────────────────────────────────
Depo public => Actions gunlugu de public. Rapor YALNIZ `dosya:satir [EKSEN]` basar;
ESLESEN SATIRIN METNINI ASLA yazmaz — aksi halde nobetci ifsayi kendi eliyle public bir
loga kopyalardi ([[nobetci-kendi-dosyasinda-sizinti]]). Ayni disiplin bu dosyanin KENDI
metnine de uygulandi: hicbir gercek kova adi / uc yolu / sir degisken adi / cerez adi /
hesap kimligi burada GECMEZ — desenler JENERIK, fiksturler UYDURMA, muafiyet govdesi
HASH'LI (duz metin tasimaz).

6 EKSEN — HER BIRI AYRI IDDIA, HER BIRI GERCEK BULGUDAN TUREDI
───────────────────────────────────────────────────────────────
  A `depolama-kovasi`  ozel nesne deposu KOVA ADI / nesne prefixi.
      Koken: tools/paket-siparis-yonetimi.md:34-35 · tools/paket-onizleme-faz-d.md:100 ·
             shop/KURULUM.md:38 · onizleme/KURULUM.md:14 · shop/wrangler.toml (kova
             beyani; guvenlik turunun BEYAN yuzeyi bulgusu)          [bulgu C2, YUKSEK]
  B `yonetim-ucu`      yonetim/panel/dahili HTTP uc YOLU (anlatimda).
      Koken: tools/paket-siparis-yonetimi.md:10-18,26,37 · shop/KURULUM.md:12 ·
             onizleme/KURULUM.md:48 · shop/src/yonet.js:5-10 (uc ENVANTERI, guvenlik
             turunun asil bulgusu)                                    [bulgu C1, YUKSEK]
  C `sir-degisken-adi` PROJEYE OZGU sir/cerez/ozel baslik ADI.
      Koken: tools/paket-siparis-yonetimi.md:5,11-12 · shop/KURULUM.md:14,18 ·
             shop/src/yonet.js:13,17 · shop/wrangler.toml (sir kurulum satirlari)
             [bulgu C6+C1, ORTA-YUKSEK]
      🔴 SATICI-STANDART ad KAPSAM DISI: bulut/odeme/analitik saglayicisinin KENDI
      belgelenmis degisken adi (ilk parcasi SATICI_JETONLARI'nda) hedefi DARALTMAZ —
      o saglayiciyla calistigimiz zaten sitede gorunur. Projeye OZGU ad DARALTIR.
      Bu ayrim IDDIA-C2 ile olculur; kaldirilirsa 30'dan fazla saticiya-ait ad
      yanlis pozitif olurdu (olculdu).
  D `hesap-kimligi`    hesap/proje kimligi tasiyan opak tanimlayici (iki etiketli
      dagitim ana makinesi ya da TAM 32 haneli onaltilik kimlik).
      Koken: tools/faz3-onbellek-purge.md:40                          [C sinifi topoloji]
  E `islemcisiz-para`  para isleyiciden GECMEYEN kanal + ELLE onay yolunun tarifi.
      Koken: tools/paket-shop-kargo.md:54 · tools/paket-siparis-yonetimi.md:19
             [bulgu C3, YUKSEK]
  F `kapanmamis-acik`  BILINEN ama KAPATILMAMIS bir zayifligin/acigin yazili beyani.
      Koken: shop/src/yonet.js:99-100 (kabul edilmis artik zayiflik; guvenlik turunun
             ikinci bulgusu) · tools/paket-uyum-ekseni.md:107-111 (tarihli hukuki acik)
             · tools/paket-ara-cpu-onarimi.md:4-5 · tools/paket-shop-kargo.md:105-111
             [bulgu D1+C4+C5+C8, YUKSEK]

MUAFIYET — YOL DEGIL ICERIK BAGLI, HASH'LI
───────────────────────────────────────────
Kayit UCLUSU: (repo-gorece dosya, o SATIRIN TAM METNININ sha256'si, gerekce). Path bazli
genel bir "bu dosyaya dokunma" kacisi YOKTUR: satirin metni tek karakter degisirse
muafiyet DUSER ve satir KIRMIZI yanar. Hash saklanir (duz metin degil) cunku muaf satir
hassas olabilir — govde bu dosyayi bir ifsa kaynagina cevirmemelidir. Uretmek:
    python3 tools/spec-ifsa-kapisi.py --muafiyet-hash <dosya> <satir_no>
🔴 BUGUNKU BULGULARIN HICBIRI MUAF TUTULMADI ve tutulmayacak: temizlenene kadar KIRMIZI
   kalmalari DOGRU sonuctur (bkz. SERIT KARARI).

KENDI DOSYASI ISTISNASI (govde-disi, IKI path, GEREKCELI)
──────────────────────────────────────────────────────────
`tools/spec-ifsa-kapisi.py` ve `tools/spec-ifsa-mutasyon-test.py` taramadan ELENIR: bir
nobetci deseni TANIMLAMAK icin onu YAZMAK ZORUNDADIR (yukaridaki eksen anlatimi,
fiksturler, mutasyon hedef dizeleri). Aksi halde kapi KENDI KENDINI kirmizi yakardi —
tools/kisisel-veri-test.py ve tools/ic-rapor-adi-kapisi.py AYNI sebeple ayni istisnayi
tasir. Bu, icerik-hash muafiyet mekanizmasindan TAMAMEN AYRI bir kod-yolu istisnasidir
ve mutasyon eslemesini ETKILEMEZ.

SERIT KARARI — RAPOR EDEN (yayini DURDURMAZ), gerekcesi OLCULDU
────────────────────────────────────────────────────────────────
deploy.yml `serit-b` kurali: "yanlis/eksik/SIZINTILI icerik CANLIYA CIKMASIN" diyen her
kapi SERIT A'dadir, SUPHEDE A. Bu kapi o sinifa GIRMEZ ve bu OLCULDU:
  (a) YAYINA CIKMIYOR: Pages artefakti `_site` bir IZIN LISTESIDIR (deploy.yml:185-223);
      taranan yuzeyin (spec'ler, worker kaynagi, konfigurasyon, is akislari) HICBIRI
      oraya kopyalanmaz -> bu satirlar canliya CIKAN icerik degildir.
  (b) TAMIR DEGERI SIFIR: deploy.yml YALNIZ `push: branches:[main]` ile ve PUSH'TAN
      SONRA kosar; o an dosyalar ZATEN public remote'tadir. Yayini durdurmak ifsayi geri
      ALMAZ. Bu, deponun diger IKI sizinti nobetcisini (commit mesaji · gecmis
      geri-donusu) serit B'ye koyan AYNI olcuttur.
  (c) BEDEL OLCULDU ve KAPSAM BUYUDUKCE ARTTI: kapsam kaynak/konfigurasyon/is akisi
      yuzeyine genisletilince bugunku kirmizi sayisi `.md`-only halinin KAT KAT
      ustune cikti (sayilar muhendis raporunda). Serit A'ya konsaydi TUM EKIBIN yayini,
      yalniz Okan'in kapatabilecegi bir temizlik birikimi yuzunden DURURDU — bu depoda
      kapi birikmesi 6 SAATLIK canli 404 pencereleri acti
      ([[kapi-birikimi-yayin-gecikmesi]]).
  (d) GECIS MUAFIYETI SECILMEDI (alternatif (ii)): bugunku bulgulari serit A'da gecici
      muaf tutmak, muaf satirlarin METNINI ya da yuzlerce opak hash'i bu dosyaya
      yazmayi gerektirirdi — birincisi ifsanin ta kendisi, ikincisi DENETLENEMEZ bir
      liste. Rapor eden seritte HICBIR SEY muaf degildir; defter DURUSTTUR.
⚠️ `continue-on-error` KULLANILMADI: bloklamamak SESSIZ OLMAK DEGILDIR — job KIRMIZI
   yanar, bildirim duser, kirmizilik GORUNUR kalir.
🔴 SERIT A'YA TASIMA KOSULU (olculebilir, tek satir): ana dalda
       python3 tools/spec-ifsa-kapisi.py   ->   rc=0 ("temiz (0 muafiyet-disi isabet)")
   oldugu gun bayraksiz cagri `build` job'una (serit A) tasinir ve bu kapinin
   tools/is-akisi-kapisi.py::SERIT_B girisi SILINIR (taban 42 -> 41). Kosul rc'DIR,
   "bakildi temiz" DEGILDIR. ARA HEDEF olculebilir: `--dokum` ciktisindaki EKSEN-A ve
   EKSEN-F sayilari 0'a inince kalan eksenler icin ayri bir serit turu acilabilir.
   ✅ 5 Agu 2026: kosul DAL uzerinde SAGLANDI (rc=0, 6 eksenin hepsi 0). Serit tasimasi
   MIMAR KARARIDIR ve bu turda YAPILMADI: kosul "ANA DALDA rc=0" diyor, dal main'e
   girmeden ana dal olculmus olmaz — hukmu merge sonrasi ana dalda olcup vermek gerekir.
⚠️ BEYAN EDILMIS ISTISNA: taranan dosyalardan YALNIZ BIRI (`ege-bilgi.md`) fiilen
   `_site`'a kopyalanir (deploy.yml:200) — o dosya icin (a) gerekcesi GECERSIZDIR.
   Icerigi AYRICA kendi kabul testleriyle korunur (bkz. skill: ege-diyalog); serit hukmu
   ONA GORE verilmemistir. Bilincli, olculmus sinir.

Kullanim:
    python3 tools/spec-ifsa-kapisi.py                        # izlenen yuzeyi tara, 0/1
    python3 tools/spec-ifsa-kapisi.py --kendini-test          # offline kabul testi
    python3 tools/spec-ifsa-kapisi.py --dokum                 # eksen basina sayim
    python3 tools/spec-ifsa-kapisi.py --muafiyet-hash <d> <n> # muafiyet hash'i uret

Cikis kodu: 0 = temiz, 1 = en az bir muafiyet-disi isabet, 2 = OLCULEMEDI (fail-closed).
"""
import argparse
import ast
import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile
import tokenize

sys.dont_write_bytecode = True  # SALT-OKUNUR tarama: hedef repoya __pycache__ yazma.

# Kendi kaynagi + mutasyon aracinin kaynagi: deseni TANIMLAMAK icin tasirlar.
KENDI_YOLLARI = ("tools/spec-ifsa-kapisi.py", "tools/spec-ifsa-mutasyon-test.py")

ANLATIM, BEYAN, ICRA = "anlatim", "beyan", "icra"

_EGIK_UZANTI = (".js", ".mjs", ".cjs", ".ts")
_DIYEZ_UZANTI = (".yml", ".yaml", ".sh")
_TOML_UZANTI = (".toml",)


# ===========================================================================
# YUZEY AYIRICI — hangi satir ANLATIM, hangisi ICRA
# ===========================================================================
def _yuzey_md(satirlar):
    for i, s in enumerate(satirlar, 1):
        yield i, s, ANLATIM


def _yuzey_toml(satirlar):
    """TOML: tum satir BEYAN yuzeyidir; `#` sonrasi ayrica ANLATIM'dir."""
    for i, s in enumerate(satirlar, 1):
        yield i, s, BEYAN
        k = s.find("#")
        if k >= 0:
            yield i, s[k + 1:], ANLATIM


def _yuzey_diyez(satirlar):
    for i, s in enumerate(satirlar, 1):
        k = s.find("#")
        yield (i, s[k + 1:], ANLATIM) if k >= 0 else (i, s, ICRA)


def _yuzey_egik(satirlar):
    """JS ailesi: `/* ... */` bloklari ve `//` yorumlari ANLATIM.
    🔴 `://` (URL semasi) yorum SAYILMAZ — olculdu: sayilsaydi her `http://...`
    satiri anlatim gorunur ve ICRA yuzeyi sessizce kapiya sizardi."""
    blok = False
    for i, s in enumerate(satirlar, 1):
        d = s.strip()
        if blok:
            yield i, s, ANLATIM
            if "*/" in s:
                blok = False
            continue
        if d.startswith("/*"):
            yield i, s, ANLATIM
            if "*/" not in d[2:]:
                blok = True
            continue
        k = -1
        ara = 0
        while True:
            p = s.find("//", ara)
            if p < 0:
                break
            if p > 0 and s[p - 1] == ":":
                ara = p + 2
                continue
            k = p
            break
        yield (i, s[k + 2:], ANLATIM) if k >= 0 else (i, s, ICRA)


def _py_belge_dizesi_satirlari(icerik):
    """`ast` ile GERCEK belge dizelerinin (modul/sinif/fonksiyon docstring) satir
    numaralari. Degiskene ATANMIS coklu-tirnak dizeler (mutasyon yukleri) DAHIL
    DEGILDIR — onlar kodun kendisidir, anlatim degil."""
    try:
        agac = ast.parse(icerik)
    except (SyntaxError, ValueError):
        return None  # ayristirilamadi -> yalniz `#` yorumlari kullanilir
    kume = set()
    for dugum in ast.walk(agac):
        if not isinstance(dugum, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                  ast.AsyncFunctionDef)):
            continue
        govde = getattr(dugum, "body", None)
        if not govde:
            continue
        ilk = govde[0]
        if isinstance(ilk, ast.Expr) and isinstance(ilk.value, ast.Constant) \
                and isinstance(ilk.value.value, str):
            bas = ilk.value.lineno
            son = getattr(ilk.value, "end_lineno", bas)
            kume.update(range(bas, son + 1))
    return kume


def _yuzey_py(icerik, satirlar):
    belge = _py_belge_dizesi_satirlari(icerik)
    yorum = {}
    try:
        for jeton in tokenize.generate_tokens(io.StringIO(icerik).readline):
            if jeton.type == tokenize.COMMENT:
                no = jeton.start[0]
                yorum[no] = jeton.string.lstrip("#")
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        yorum = {}
    for i, s in enumerate(satirlar, 1):
        if belge is not None and i in belge:
            yield i, s, ANLATIM
        elif i in yorum:
            yield i, yorum[i], ANLATIM
        else:
            yield i, s, ICRA


def yuzeyler(yol, icerik):
    """(satir_no, metin, yuzey) uretir. TEK KAYNAK: kapsam karari buradan turer."""
    uz = os.path.splitext(yol)[1].lower()
    satirlar = icerik.splitlines()
    if uz == ".md":
        return _yuzey_md(satirlar)
    if uz in _TOML_UZANTI:
        return _yuzey_toml(satirlar)
    if uz == ".py":
        return _yuzey_py(icerik, satirlar)
    if uz in _DIYEZ_UZANTI:
        return _yuzey_diyez(satirlar)
    if uz in _EGIK_UZANTI:
        return _yuzey_egik(satirlar)
    return iter(())  # kapsam disi uzanti: hic satir uretilmez


# ===========================================================================
# EKSEN SOZLESMESI — TESPIT ile JETON TEK KAYNAKTAN TURER
# Her eksen fonksiyonu ya None (isabet YOK) ya da bir JETON DEMETI dondurur. Demet BOS
# olabilir: E ve F "jeton" degil CUMLE olcer (bir ad/yol/kimlik tasimazlar).
# 🔴 NEDEN BOYLE: eko elemesi (asagida) tetikleyen jetonu bilmek zorunda. Jetonu AYRI bir
# cikarici hesaplasaydi iki tanim SESSIZCE AYRISIRDI ([[ikiz-tanim-sessiz-ayrisma]]) ve
# ayrisma fail-OPEN yonde olurdu: yanlis cikarilmis jeton, ihlali muaf gosterirdi.
# Bugun "isabet var mi" sorusunun cevabi jeton demetinin KENDISIDIR.
# ===========================================================================
def _bulgu(jetonlar):
    """Jeton listesinden eksen sonucu: bos ise isabet YOK (None), degilse tekil demet."""
    return tuple(dict.fromkeys(jetonlar)) if jetonlar else None


def _iddia(vurdu):
    """Jetonsuz (cumle tabanli) eksen sonucu: isabet varsa BOS demet, yoksa None."""
    return () if vurdu else None


# ===========================================================================
# EKSEN A — OZEL NESNE DEPOSU KOVA ADI
# Ayirt edicilik DORT KATLI, dordu de OLCUMDEN dogdu:
#  (1) KOVA SOZU zorunlu ("kova"/"bucket" ve cekimleri). Ciplak "R2" TETIKLEMEZ:
#      olculdu ki R2 bu depoda gorsel/yedek/anahtar-turetme yorumlarinda 40'tan fazla
#      yerde geciyor ve hicbiri kova ADI tasimiyor (69 -> 28 vurus).
#  (2) Ad jetonu KOD ISARETI (backtick) icinde olmali. Turkce tuzagi olculdu: "kova"
#      bu depoda VERI kovasi anlaminda da kullaniliyor ve yanindaki tire-li kelime bir
#      SIFAT olabiliyor ("esik-oncesi kovasi", "fail-closed ... kova ayrimi",
#      "marka-basi kovasi"). Bu 14 yanlis poziti tek kural eledi: kova ADI bu depoda
#      DAIMA kod isaretiyle yazilir, Turkce sifat YAZILMAZ.
#  (3) Jeton kova sozune YAKIN olmali (±PENCERE karakter) — uzaktaki bir kod isareti
#      ayni cumlenin parcasi degildir.
#  (4) Jeton bir DOSYA ADIYSA (uzanti ekli) ya da YOL iceriyorsa ELENIR — aksi halde
#      `arac-adi.py` gibi her depo yolu yanlis pozitif olurdu.
# Ayrica KONFIGURASYON BEYANI ayri bir tetiktir: `bucket_name = "<ad>"`.
# 🔴 BEYAN EDILMIS SINIR (fail-open yon, olculdu): TIRNAKSIZ/ISARETSIZ yazilmis kova
#    adi (or. "mevcut ozel kova <ad>, prefix ...") YAKALANMAZ. Bugun bu 4 satira mal
#    oluyor ve dordunun de dosyasi baska satir/eksenden ZATEN kirmizi. Alternatifi
#    (isaretsiz jetonu kabul etmek) 14 yanlis pozitif getiriyordu — kapiyi cope atan
#    oran ([[kapi-disiplin-ilkesi]]).
# ===========================================================================
_A_PENCERE = 40
_A_KOVA_SOZU = re.compile(r"kova\w*|bucket\w*", re.I)
_A_JETON = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")
_A_BEYAN = re.compile(r"bucket[_\-]?name\s*=\s*[\"']([a-z][a-z0-9]*(?:-[a-z0-9]+)+)[\"']", re.I)


def _eksen_a(satir, _yuzey):
    """A: ozel nesne deposu KOVA ADI ifsasi (kova sozune YAKIN, isaretli ad jetonu)."""
    jetonlar = []
    for m in _A_BEYAN.finditer(satir):
        jetonlar.append(m.group(1))
    for m in _A_KOVA_SOZU.finditer(satir):
        bas = max(0, m.start() - _A_PENCERE)
        son = min(len(satir), m.end() + _A_PENCERE)
        for t in _A_JETON.finditer(satir[bas:son]):
            jetonlar.append(t.group(1))
    return _bulgu(jetonlar)


# ===========================================================================
# EKSEN B — YONETIM / PANEL / DAHILI UC YOLU
# Yalniz BAS EGIK BOLU ile baslayan (metinde URL YOLU olarak yazilmis) jetonlar
# sayilir; `dizin/dosya.js` bicimindeki KAYNAK YOLU sayilmaz (onun bolusu bir kelime
# karakterinden sonra gelir ve geriye-bakis onu eler). Musteriye donuk uclar isaret
# tasimadigi icin YESIL kalir — ayrim IDDIA-B2 ile olculur.
# ===========================================================================
_B_YOL = re.compile(r"(?<![A-Za-z0-9_.\-])(?:/[A-Za-z0-9_.<>{}\-]+)+")
_B_ISARET = frozenset(("yonet", "yönet", "yonetim", "yönetim", "admin", "panel",
                       "internal", "dahili", "kapat"))
_B_ONEK = ("ic-",)


def _eksen_b(satir, _yuzey):
    """B: yonetim/panel/dahili bir HTTP uc YOLUNUN ifsasi."""
    jetonlar = []
    for m in _B_YOL.finditer(satir):
        segmentler = m.group(0).strip("/").split("/")
        isaretli = False
        for segment in segmentler:
            s = segment.lower()
            if any(s.startswith(o) for o in _B_ONEK) or \
                    any(parca in _B_ISARET for parca in re.split(r"[-_.]", s)):
                isaretli = True
        # 🔴 JETON = yolun HER SEGMENTI, yalniz isaretli olan DEGIL (olculdu, 5 Agu 2026):
        # eko elemesine yalniz isaretli segment ("/yonet") verildiginde YEPYENI bir yonetim
        # yolu (`/sentetik9x/yonet/kapali-liste`) o tek ekonun sirtinda MUAF oluyordu —
        # sentetik jeton sondasi B ekseninde YESIL yaniyordu (fail-open). Her segment
        # istenince yeni AD kirmizi yakar; yalniz mevcut adlarin YENI DIZILIMI elenir.
        if isaretli:
            jetonlar.extend("/" + segment for segment in segmentler)
    return _bulgu(jetonlar)


# ===========================================================================
# EKSEN C — PROJEYE OZGU SIR / CEREZ / OZEL BASLIK ADI
# Sir ADI kimlik bilgisi DEGILDIR ama hedefi DARALTIR. Daraltma yalniz PROJEYE OZGU
# adlarda gerceklesir: saticinin KENDI belgelenmis degisken adi (bulut, odeme,
# analitik, kaynak platformlari) o saglayiciyla calistigimizi zaten sitede goruneni
# tekrar eder. SATICI_JETONLARI bu yuzden BEYAN EDILMIS ve DAR tutulur; genisletmek
# fail-open yondur ve GEREKCE ISTER.
# ===========================================================================
_SATICI_JETONLARI = frozenset((
    "CLOUDFLARE", "GITHUB", "AWS", "GOOGLE", "GA4", "META", "FACEBOOK",
    "IYZICO", "RESEND", "TELEGRAM", "OPENAI", "ANTHROPIC",
    "CULTS", "CULTS3D", "MMF", "THINGIVERSE", "PRINTABLES", "MAKERWORLD", "CGT",
    "GA", "FBP", "FBC", "UTM",
))
_C_SIR = re.compile(r"\b([A-Z][A-Z0-9]*)((?:_[A-Z0-9]+)*)_"
                    r"(?:ANAHTAR|KEY|SECRET|TOKEN|PAROLA|SIFRE|IBAN|PASSWORD|CREDENTIAL)\b")
_C_KIMLIK_SOZU = re.compile(r"anahtar|key|secret|token|parola|sifre|şifre|auth|imza", re.I)
_C_BASLIK = re.compile(r"\bX-[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+\b")
_C_CEREZ_SOZU = re.compile(r"çerez|cerez|cookie|httponly", re.I)
_C_TANIMLAYICI = re.compile(r"`([A-Za-z][A-Za-z0-9]*(?:[_\-][A-Za-z0-9]+)+)`")


def _projeye_ozgu_mu(ad):
    """Ilk parca SATICI jetonuysa satici-standart addir (kapsam disi)."""
    ilk = re.split(r"[_\-]", ad.strip("`"), maxsplit=1)[0].upper()
    return ilk not in _SATICI_JETONLARI


def _eksen_c(satir, _yuzey):
    """C: projeye OZGU sir / cerez / ozel baslik adinin ifsasi."""
    jetonlar = []
    for m in _C_SIR.finditer(satir):
        if _projeye_ozgu_mu(m.group(1)):
            jetonlar.append(m.group(0))
    for m in _C_BASLIK.finditer(satir):
        # Ozel baslik ancak KIMLIK tasiyorsa sayilir: bicim/teshis basliklari
        # (sikistirma, kaynak, boyut) ifsa degildir.
        if _C_KIMLIK_SOZU.search(m.group(0)) and _projeye_ozgu_mu(m.group(0)[2:]):
            jetonlar.append(m.group(0))
    if _C_CEREZ_SOZU.search(satir):
        for m in _C_TANIMLAYICI.finditer(satir):
            ad = m.group(1)
            # 🔴 AYIRT EDICI: tanimlayicinin KENDISI cerez sozunu tasiyorsa (or. bir
            # dal/adim adi) bu bir CEREZ ADI ifsasi DEGILDIR — olculdu, aksi halde
            # icinde "cerez" gecen her dal adi yanlis pozitif olurdu.
            if _C_CEREZ_SOZU.search(ad):
                continue
            if _projeye_ozgu_mu(ad):
                jetonlar.append(ad)
    return _bulgu(jetonlar)


# ===========================================================================
# EKSEN D — HESAP / PROJE KIMLIGI BENZERI OPAK TANIMLAYICI
# Dagitim ana makinesi ancak IKI etiketliyse sayilir: `<servis>.<hesap>.<...>` bicimi
# HESAP kimligini tasir; ciplak alan adinin kendisi (dokuman atfi) tasimaz.
# Onaltilik kimlik TAM 32 hane aranir — git nesne kimlikleri 40/64 hanedir ve YANLIS
# POZITIF olurdu (ayrim olculdu).
# ===========================================================================
_D_HOST = re.compile(r"\b[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9-]*\.(?:workers|pages)\.dev\b", re.I)
_D_DEPO_HOST = re.compile(r"\b[0-9a-f]{16,}\.r2\.cloudflarestorage\.com\b", re.I)
_D_HEX32 = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{32}(?![0-9a-fA-F])")


def _eksen_d(satir, _yuzey):
    """D: hesap/proje kimligi tasiyan opak tanimlayici ifsasi."""
    jetonlar = []
    for rx in (_D_HOST, _D_DEPO_HOST, _D_HEX32):
        for m in rx.finditer(satir):
            jetonlar.append(m.group(0))
    return _bulgu(jetonlar)


# ===========================================================================
# EKSEN E — PARA ISLEYICIDEN GECMEYEN KANAL + ELLE ONAY YOLU
# "Banka havalesi kabul ediyoruz" MUSTERIYE ZATEN GORUNUR bir gercektir ve tek basina
# ifsa DEGILDIR. Ifsa, o kanalin OTOMATIK DOGRULAMASI OLMADIGININ ve onayin ELLE bir
# durum guncellemesi oldugunun yazili olmasidir -> IKI isaret de ZORUNLU.
# ===========================================================================
_E_KANAL = re.compile(r"havale|\bEFT\b|dekont|\bIBAN\b|kapıda ödeme|kapida odeme", re.I)
_E_ELLE = re.compile(r"manuel|\belle\b|otomatik doğrulama|otomatik dogrulama|"
                     r"doğrulama YOK|dogrulama YOK|onay adımı|onay adimi|onay komutu|"
                     r"durum güncellemesi|durum guncellemesi", re.I)


def _eksen_e(satir, _yuzey):
    """E: para isleyiciden gecmeyen kanalin ELLE onay yolunun tarifi."""
    return _iddia(bool(_E_KANAL.search(satir) and _E_ELLE.search(satir)))


# ===========================================================================
# EKSEN F — BILINEN AMA KAPATILMAMIS ACIGIN BEYANI
# En pahali tek satir sinifi: bir uyusmazlikta ya da denetimde "biliyorduk ve
# kapatmadik" cumlesi HAZIR BELGEDIR; saldirgan icin de bir REÇETEDIR. Iki isaret de
# ZORUNLU: (1) zayiflik sozu, (2) KAPANMAMIS oldugunu soyleyen soz.
# ===========================================================================
_F_ZAYIFLIK = re.compile(
    r"sızdır|sizdir|sızıntı|sizinti|zayıflık|zayiflik|zafiyet|fail-open|"
    r"savunmasız|savunmasiz|istismar|korumasız|korumasiz|güvenlik açı|guvenlik aci|"
    r"hukuki açık|hukuki acik|açığı\b|acigi\b|doğrulama YOK|dogrulama YOK", re.I)
_F_KAPANMAMIS = re.compile(
    r"\bbilinen\b|henüz|henuz|uygulanmadı|uygulanmadi|çözülmedi|cozulmedi|"
    r"karar bekliyor|düşük öncelik|dusuk oncelik|zorunlu değil|zorunlu degil|"
    r"\bTODO\b|ertelendi|alınmayan|alinmayan|kapatılmadı|kapatilmadi|"
    r"bu tura alınmad|bu tura alinmad|bu tura ALINMAYAN", re.I)


def _eksen_f(satir, _yuzey):
    """F: bilinen ama kapatilmamis bir zayifligin/acigin yazili beyani."""
    return _iddia(bool(_F_ZAYIFLIK.search(satir) and _F_KAPANMAMIS.search(satir)))


# (kod, ad, tespit_fn, bakilan_yuzeyler)
EKSENLER = (
    ("A", "depolama-kovasi", _eksen_a, (ANLATIM, BEYAN)),
    ("B", "yonetim-ucu", _eksen_b, (ANLATIM,)),
    ("C", "sir-degisken-adi", _eksen_c, (ANLATIM,)),
    ("D", "hesap-kimligi", _eksen_d, (ANLATIM, BEYAN)),
    ("E", "islemcisiz-para", _eksen_e, (ANLATIM,)),
    ("F", "kapanmamis-acik", _eksen_f, (ANLATIM,)),
)


# ---------------------------------------------------------------------------
# KAYITLI MUAFIYET GOVDESI — (dosya, sha256(satir metni), gerekce).
# 🔴 BUGUN BOS: 4 Agu 2026 olcumlerinin bulgularindan HICBIRI muaf tutulmadi (serit
# karari (d) maddesi). Mekanizma IDDIA-MUAF1/MUAF2 ile SENTETIK govde uzerinde
# kanitlanir — bos govde mekanizmayi olduremez.
# ---------------------------------------------------------------------------
_MUAFIYET_GOVDESI = []


def _satir_hash(satir_metni):
    return hashlib.sha256(satir_metni.encode("utf-8")).hexdigest()


def _muafiyet_kumesi_uret(govde):
    return {(dosya, h) for dosya, h, _gerekce in govde}


def _muaf_mi(dosya, satir_metni, muafiyet_kumesi):
    """Icerik-bagli muafiyet: (dosya, satirin TAM METNININ hash'i) kayitli mi."""
    return (dosya, _satir_hash(satir_metni)) in muafiyet_kumesi


def _eksen_bulgulari(metin, yuzey):
    """[(eksen_kodu, jeton_demeti), ...] — O YUZEYDE tetiklenen eksenler + jetonlari."""
    return [(kod, jetonlar) for kod, _ad, fn, kapsam in EKSENLER
            if yuzey in kapsam
            for jetonlar in (fn(metin, yuzey),) if jetonlar is not None]


def _eksen_isabetleri(metin, yuzey):
    """Verilen metnin, O YUZEYDE tetikledigi eksen KODLARI (bulgulardan TURER)."""
    return [kod for kod, _jetonlar in _eksen_bulgulari(metin, yuzey)]


# ---------------------------------------------------------------------------
# EKO ELEMESI — "satiri silmek ifsayi KAPATIYOR MU?"
# ---------------------------------------------------------------------------
# 🔴 OLCULMUS DESEN KUSURU (5 Agu 2026, bagimsiz olcum): kapinin 164 isabetinin 158'inde
# (%96,3) tetikleyen jeton AYNI PUBLIC deponun CALISAN yuzeyinde ZATEN duruyordu — yonetim
# uc YOLU onu servis eden yonlendiricide, sir ADI `env.<AD>` okumasinda. Iki eksen tek
# basina %100 yanlis-pozitifti (B 76/76, C 70/70). O satirlari temizlemek ifsayi KAPATMAZ:
# jeton yerinde kalir. Gurultunun bedeli olculdu — 4 GERCEK bulgu 158 yanlis-pozitifin
# icinde saklaniyordu.
# KURAL: bir ANLATIM isabetinin TUM tetikleyici jetonlari deponun ICRA yuzeyinde de
# geciyorsa, o satir IHLAL SAYILMAZ. "TUM" bilincli ve fail-CLOSED: tek bir jeton bile
# yalniz anlatimda duruyorsa satir KIRMIZI kalir.
# 🔴 HAVUZ YALNIZ ICRA SATIRLARIDIR. ANLATIM (ve BEYAN) yuzeyleri havuza GIRSEYDI bir
# anlatim satiri KENDINI (ya da ikizini) muaf kilardi — kapinin fail-open olumu.
# 🔴 KAPSAM DISI DOSYALAR (.json/.html/...) da havuza ALINMADI, ve bu OLCUMLE secildi:
# havuza eklendiginde bugunku 157 elemenin 157'si ZATEN ICRA satirlarindan geliyordu, yani
# o bacak SIFIR eleme kazandiriyor ama 25 MB'lik bir fail-open yuzeyi aciyordu (or. urun
# verisinde tesadufen gecen bir jeton ihlali muaf gosterebilirdi). Bedeli olculdu, karsiligi
# olculdu, bacak ALINMADI.
# E ve F eksenleri JETONSUZDUR (bos demet) -> eko elemesi onlara UYGULANMAZ; cumle tabanli
# ifsa, bir jetonun baska yerde durmasiyla mesrulasmaz.
# NOBET: IDDIA-EKO1 (havuzda OLMAYAN sentetik jeton KIRMIZI kalir + anlatim ikizi eleme
# YAPMAZ) ve IDDIA-EKO2 (gercek ICRA ekosu elenir); mutantlari MUT-EKO-GENIS / MUT-EKO-KOR.
# ---------------------------------------------------------------------------
def _icra_havuzu(dosya_icerik_ciftleri):
    """Eko elemesinin arama yuzeyi (tek dize): YALNIZ ICRA satirlari.
    ANLATIM/BEYAN satirlari ve kapsam DISI dosya icerikleri BILEREK disaridadir."""
    parcalar = []
    for yol, icerik in dosya_icerik_ciftleri:
        for _no, metin, yuzey in yuzeyler(yol, icerik):
            if yuzey == ICRA:
                parcalar.append(metin)
    return "\n".join(parcalar)


def _eko_mu(jetonlar, havuz, onbellek=None):
    """Jetonlarin HEPSI ICRA havuzunda mi? (jetonsuz eksen DAIMA False = elenmez)"""
    if not jetonlar:
        return False
    for jeton in jetonlar:
        if onbellek is None:
            var = jeton in havuz
        else:
            var = onbellek.get(jeton)
            if var is None:
                var = jeton in havuz
                onbellek[jeton] = var
        if not var:
            return False
    return True


def tara(dosya_icerik_ciftleri, govde=None):
    """[(yol, satir_no, eksen_kodu), ...] — muafiyet-disi isabetler (sirali, tekil).
    Muafiyet HAM SATIR uzerinden olculur (yuzey parcasi uzerinden degil): boylece
    muafiyet kaydi dosyadaki gercek satirla birebir esler."""
    kume = _muafiyet_kumesi_uret(_MUAFIYET_GOVDESI if govde is None else govde)
    ciftler = list(dosya_icerik_ciftleri)
    havuz = _icra_havuzu(ciftler)
    onbellek = {}
    ihlaller = []
    for yol, icerik in ciftler:
        ham = icerik.splitlines()
        gorulen = set()
        for satir_no, metin, yuzey in yuzeyler(yol, icerik):
            for kod, jetonlar in _eksen_bulgulari(metin, yuzey):
                if (satir_no, kod) in gorulen:
                    continue
                gorulen.add((satir_no, kod))
                if _eko_mu(jetonlar, havuz, onbellek):
                    continue
                tam = ham[satir_no - 1] if 1 <= satir_no <= len(ham) else metin
                if _muaf_mi(yol, tam, kume):
                    continue
                ihlaller.append((yol, satir_no, kod))
    return ihlaller


def _rapor_satiri(yol, satir_no, kod, _satir_metni):
    """TESHIS MASKELI rapor satiri: konum + eksen, SATIR METNI ASLA YOK."""
    adlar = dict((k, a) for k, a, _f, _y in EKSENLER)
    return "  %s:%d  [EKSEN-%s %s]" % (yol, satir_no, kod, adlar[kod])


def _git_izlenen_dosyalar(kok):
    r = subprocess.run(["git", "-C", kok, "ls-files", "-z"], capture_output=True, text=True)
    if r.returncode != 0:
        print("OLCULEMEDI: git ls-files basarisiz: " + r.stderr.strip())
        sys.exit(2)
    return [y for y in r.stdout.split("\0") if y]


def _oku(kok, yol):
    try:
        with open(os.path.join(kok, yol), "r", encoding="utf-8") as f:
            return f.read()
    except (UnicodeDecodeError, OSError):
        return None


def ana_tarama(kok):
    """GERCEK repo taramasi: `git ls-files` ciktisindaki dosyalar (kendi kaynagi HARIC)."""
    ciftler = []
    for yol in _git_izlenen_dosyalar(kok):
        if yol in KENDI_YOLLARI:
            continue
        icerik = _oku(kok, yol)
        if icerik is not None:
            ciftler.append((yol, icerik))
    return tara(ciftler)


# ===========================================================================
# KENDINI-TEST — 24 BEYAN EDILMIS IDDIA (SABIT SAYI). Her eksen icin OLDURUCU
# (desen VAR -> KIRMIZI) + TEK DEGISKENLI KONTROL (benzer ama kapsam disi -> YESIL);
# ustune YUZEY ayrimi (4), BEYAN yuzeyi (2), KAPSAM (1), EKO ELEMESI (2), MUAFIYET (2),
# MASKE (1).
# Mutant<->iddia eslemesi TEK KAYNAK: tools/spec-ifsa-mutasyon-test.py :: MUTANTLAR.
# 🔴 TUM FIKSTURLER UYDURMADIR: hicbiri bu depodaki gercek bir kova/uc/sir/cerez/
# kimlik degildir (nobetci kendi dosyasinda sizdirmaz). Tek istisna IDDIA-C2'nin
# saticiya-ait ornegidir: o ad ZATEN _SATICI_JETONLARI'nda beyan edilmis, evrensel
# olarak belgelenmis bir addir — yeni bilgi TASIMAZ.
# ===========================================================================
# (etiket, metin, yuzey, eksen_kodu, beklenen)
_FIKSTURLER = (
    ("IDDIA-A1", "Uretim dosyalari ozel R2 kovasina konur: `deneme-ornek-kova`.",
     ANLATIM, "A", True),
    ("IDDIA-A2", "Marka kovasi ayrimi `deneme-yukleyici.py` ile yeniden olculecek.",
     ANLATIM, "A", False),
    ("IDDIA-B1", "Ornek uc: `GET /deneme/ornek/yonet/liste` sayfa dondurur.",
     ANLATIM, "B", True),
    ("IDDIA-B2", "Ornek uc: `GET /deneme/ornek/olustur` musteriye aciktir.",
     ANLATIM, "B", False),
    ("IDDIA-C1", "Erisim: DENEME_ORNEK_ANAHTAR sirri tanimli degilse uc kapalidir.",
     ANLATIM, "C", True),
    ("IDDIA-C2", "Erisim: GITHUB_TOKEN saglayicinin belgeledigi standart addir.",
     ANLATIM, "C", False),
    ("IDDIA-D1", "Onbellek notu: `deneme.ornekhesap.workers.dev` ayri alandadir.",
     ANLATIM, "D", True),
    ("IDDIA-D2", "Onbellek notu: `workers.dev` alt alan adi site alanindan ayridir.",
     ANLATIM, "D", False),
    ("IDDIA-E1", "Havale kanalinda otomatik dogrulama YOK: onay adimi manueldir.",
     ANLATIM, "E", True),
    ("IDDIA-E2", "Havale secenegi odeme adiminda musteriye gosterilir.",
     ANLATIM, "E", False),
    ("IDDIA-F1", "Uzunluk farkini sizdirir; bilinen ve bu tura ALINMAYAN kalem.",
     ANLATIM, "F", True),
    ("IDDIA-F2", "Uzunluk farkini sizdirir; bu turda kapatildi ve testi eklendi.",
     ANLATIM, "F", False),
    # Konfigurasyon BEYAN yuzeyi: kova adi beyanda KIRMIZI (ozel kaynak kimligi public
    # konfigurasyonda durmak ZORUNDA DEGIL); sir ADI beyanda YESIL (C ekseni BEYAN
    # yuzeyine BAKMAZ — kurulum/konfig o adi tasimak zorundadir).
    ("IDDIA-BEYAN1", 'bucket_name = "deneme-ornek-kova"', BEYAN, "A", True),
    ("IDDIA-BEYAN2", "  npx wrangler secret put DENEME_ORNEK_ANAHTAR", BEYAN, "C", False),
)

# YUZEY fiksturleri: ISLEVI GEREGI TASINAN AD ile ANLATILAN TOPOLOJI ayrimi.
_JS_FIKSTUR = (
    "/** Erisim: DENEME_ORNEK_ANAHTAR tanimli degilse uc kapalidir. */\n"   # 1: ANLATIM
    'if (!env.DENEME_ORNEK_ANAHTAR) { return dur(); }\n'                    # 2: ICRA
)
_PY_FIKSTUR = (
    '"""Erisim: DENEME_ORNEK_ANAHTAR tanimli degilse uc kapalidir."""\n'    # 1: ANLATIM
    'YUK = """Erisim: DENEME_ORNEK_ANAHTAR tanimli degilse uc kapalidir."""\n'  # 2: ICRA
)


def _yuzey_haritasi(yol, icerik):
    return {no: yuzey for no, _metin, yuzey in yuzeyler(yol, icerik)}


def _kendini_test():
    sonuclar = []

    for etiket, metin, yuzey, kod, beklenen in _FIKSTURLER:
        bulundu = kod in _eksen_isabetleri(metin, yuzey)
        sonuclar.append((etiket, bulundu == beklenen,
                         "eksen %s / yuzey %s beklenen=%s olculen=%s"
                         % (kod, yuzey, beklenen, bulundu)))

    # --- YUZEY ayrimi (4 iddia): AYNI cumle yorumda ANLATIM, calisan ifadede ICRA ---
    js = _yuzey_haritasi("uydurma/ornek.js", _JS_FIKSTUR)
    sonuclar.append(("IDDIA-YUZEY1 js-yorum-anlatim", js.get(1) == ANLATIM,
                     "blok yorum satiri ANLATIM olmali (olculen=%s)" % js.get(1)))
    sonuclar.append(("IDDIA-YUZEY2 js-ifade-icra", js.get(2) == ICRA,
                     "calisan ifade ICRA olmali — islevi geregi tasinan ad kapiya "
                     "GIRMEZ (olculen=%s)" % js.get(2)))
    py = _yuzey_haritasi("uydurma/ornek.py", _PY_FIKSTUR)
    sonuclar.append(("IDDIA-YUZEY3 py-belge-dizesi-anlatim", py.get(1) == ANLATIM,
                     "modul belge dizesi ANLATIM olmali (olculen=%s)" % py.get(1)))
    sonuclar.append(("IDDIA-YUZEY4 py-atanmis-dize-icra", py.get(2) == ICRA,
                     "degiskene ATANMIS coklu-tirnak dize ICRA olmali — mutasyon "
                     "araclarinin kod yukleri anlatim DEGILDIR (olculen=%s)" % py.get(2)))

    # --- IDDIA-KAPSAM (uctan uca, GERCEK git): kapsam ici uzanti yuzey URETIR, kapsam
    #     disi uzanti AYNI icerikle HIC yuzey uretmez ve taramada GORUNMEZ.
    #     🔴 EKSENDEN BAGIMSIZ kuruldu (bilerek): eksen fikstürüne dayansaydi her
    #     "eksen kor" mutanti bu iddiayi da dusurur ve TEK-KIRMIZI sarti bozulurdu.
    #     Gercek dosyaya YAZMA YOK (gecici depo). ---
    s_satir = "Uretim dosyalari ozel R2 kovasina konur: `deneme-ornek-kova`."
    ici_yuzey = len(list(yuzeyler("kapsam-ici.md", s_satir + "\n")))
    disi_yuzey = len(list(yuzeyler("kapsam-disi.json", s_satir + "\n")))
    with tempfile.TemporaryDirectory() as d:
        g = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True)
        g("init", "-q")
        g("config", "user.email", "test@test.local")
        g("config", "user.name", "test")
        for ad in ("kapsam-ici.md", "kapsam-disi.json"):
            with open(os.path.join(d, ad), "w", encoding="utf-8") as f:
                f.write(s_satir + "\n")
        g("add", "-A")
        disi = any(y == "kapsam-disi.json" for y, _n, _k in ana_tarama(d))
        sonuclar.append(("IDDIA-KAPSAM uzanti-kapsami",
                         ici_yuzey > 0 and disi_yuzey == 0 and not disi,
                         "kapsam ici .md yuzey=%d (>0), kapsam disi .json yuzey=%d (0), "
                         "uctan uca taramada gorunmuyor=%s"
                         % (ici_yuzey, disi_yuzey, not disi)))

    # --- IDDIA-EKO1 / IDDIA-EKO2 (uctan uca, GERCEK git): eko elemesi DARALTIR ama
    #     FAIL-OPEN YAPMAZ. Iki fikstur AYNI depoda, AYNI eksende (A/beyan deseni) ve
    #     AYNI yuzeyde (ANLATIM) durur; aralarindaki TEK degisken, jetonun ICRA yuzeyinde
    #     de gecip gecmedigidir.
    #       * eko-tek-kaynak.md : jeton SADECE anlatimda (ikizi de anlatimda) -> KIRMIZI
    #         kalmali. Anlatim ikizi BILEREK var: havuza anlatim sizsaydi bu iddia duserdi.
    #       * eko-eko.md        : ayni jeton hem bir .js hem bir .py ICRA satirinda ->
    #         ELENMELI. Eko IKI DILDEN verilir (bilincli redundans): tek dil olsaydi o
    #         dilin YUZEY mutanti (MUT-YUZEY-GENIS / MUT-PY-*) bu iddiayi da dusurur ve
    #         TEK-KIRMIZI sozlesmesi bozulurdu.
    #     Gercek dosyaya YAZMA YOK (gecici depo). ---
    with tempfile.TemporaryDirectory() as d:
        g = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True)
        g("init", "-q")
        g("config", "user.email", "test@test.local")
        g("config", "user.name", "test")
        dosyalar = {
            "eko-tek-kaynak.md": 'bucket_name = "eko-yok-kova"\n',
            "eko-anlatim-ikizi.md": 'bucket_name = "eko-yok-kova"\n',
            "eko-eko.md": 'bucket_name = "eko-var-kova"\n',
            "eko-icra.js": 'const kovaAdi = "eko-var-kova";\n',
            "eko-icra.py": 'KOVA_ADI = "eko-var-kova"\n',
        }
        for ad, govde_ in dosyalar.items():
            with open(os.path.join(d, ad), "w", encoding="utf-8") as f:
                f.write(govde_)
        g("add", "-A")
        eko_ihlaller = ana_tarama(d)
        tek_kaynak_var = ("eko-tek-kaynak.md", 1, "A") in eko_ihlaller
        eko_elendi = not any(y == "eko-eko.md" for y, _n, _k in eko_ihlaller)
    sonuclar.append(("IDDIA-EKO1 icra-disi-jeton-kirmizi-kalir", tek_kaynak_var,
                     "ICRA yuzeyinde OLMAYAN jeton (anlatim ikizi olsa bile) ihlal "
                     "SAYILMALI — eleme fail-open olamaz (olculen=%s)" % tek_kaynak_var))
    sonuclar.append(("IDDIA-EKO2 icra-ekosu-elenir", eko_elendi,
                     "jeton calisan kodda/kapsam disi public dosyada da geciyorsa anlatim "
                     "satirini silmek ifsayi KAPATMAZ -> ihlal DEGIL (olculen=%s)" % eko_elendi))

    # --- Muafiyet mekanizmasi: SENTETIK govde (gercek bulgu MUAF DEGIL) ---
    s_dosya = "uydurma/ornek-spec.md"
    s_govde = [(s_dosya, _satir_hash(s_satir), "kendini-test fiksturu")]

    muaf1 = not _muaf_mi(s_dosya, s_satir + " EK-SOZ", _muafiyet_kumesi_uret(s_govde))
    sonuclar.append(("IDDIA-MUAF1 icerik-bagli-muafiyet", muaf1,
                     "ayni dosya + DEGISTIRILMIS satir muaf SAYILMAMALI (yol bazli kacis yok)"))

    muaf2 = _muaf_mi(s_dosya, s_satir, _muafiyet_kumesi_uret(s_govde))
    sonuclar.append(("IDDIA-MUAF2 kayitli-satir-yesil", muaf2,
                     "govdedeki satir BIREBIR ise muaf sayilmali"))

    # --- IDDIA-MASKE: rapor satiri esleseni KONUMLA verir, METNI ASLA yazmaz ---
    rapor = _rapor_satiri("uydurma/ornek-spec.md", 7, "A", s_satir)
    maske = ("deneme-ornek-kova" not in rapor) and ("uydurma/ornek-spec.md:7" in rapor)
    sonuclar.append(("IDDIA-MASKE cikti-sizdirmaz", maske,
                     "rapor satiri konum+eksen tasir, eslesen METIN TASIMAZ"))

    basarisiz = [s for s in sonuclar if not s[1]]
    for etiket, gecti, detay in sonuclar:
        print("  [%s] %s — %s" % ("PASS" if gecti else "FAIL", etiket, detay))
    print("  TOPLAM: %d/%d gecti" % (len(sonuclar) - len(basarisiz), len(sonuclar)))
    return 0 if not basarisiz else 1


def _dokum(kok):
    """TESHIS: eksen basina isabet + dosya sayimi (satir METNI basilmaz)."""
    ihlaller = ana_tarama(kok)
    print("SPEC IFSA DOKUMU (yuzey: md + yorum + belge dizesi + toml beyani)")
    for kod, ad, _fn, _y in EKSENLER:
        alt = [x for x in ihlaller if x[2] == kod]
        dosyalar = sorted({y for y, _n, _k in alt})
        print("  EKSEN-%s %-18s isabet=%-4d dosya=%d" % (kod, ad, len(alt), len(dosyalar)))
        for y in dosyalar:
            print("      %s  (%d)" % (y, len([x for x in alt if x[0] == y])))
    print("  TOPLAM isabet: %d / dosya: %d"
          % (len(ihlaller), len({y for y, _n, _k in ihlaller})))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true",
                    help="offline kabul testi (ag YOK, gercek dosyaya yazma YOK)")
    ap.add_argument("--dokum", action="store_true", help="eksen basina sayim (teshis)")
    ap.add_argument("--muafiyet-hash", nargs=2, metavar=("DOSYA", "SATIR_NO"),
                    help="bir satirin muafiyet hash'ini uret (govdeye elle eklemek icin)")
    args = ap.parse_args()

    if args.kendini_test:
        return _kendini_test()

    kok = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    if not kok:
        print("OLCULEMEDI: git kok dizini bulunamadi (bu bir git deposu mu?)")
        return 2

    if args.muafiyet_hash:
        dosya, no = args.muafiyet_hash[0], int(args.muafiyet_hash[1])
        icerik = _oku(kok, dosya)
        if icerik is None:
            print("OLCULEMEDI: %s okunamadi" % dosya)
            return 2
        satirlar = icerik.splitlines()
        if not 1 <= no <= len(satirlar):
            print("OLCULEMEDI: %s dosyasinda %d numarali satir yok" % (dosya, no))
            return 2
        print("('%s', '%s', 'GEREKCE YAZ')" % (dosya, _satir_hash(satirlar[no - 1])))
        return 0

    if args.dokum:
        return _dokum(kok)

    ihlaller = ana_tarama(kok)
    if not ihlaller:
        print("SPEC IFSA KAPISI: temiz (0 muafiyet-disi isabet).")
        return 0
    print("SPEC IFSA KAPISI: %d muafiyet-disi isabet (%d dosya):"
          % (len(ihlaller), len({y for y, _n, _k in ihlaller})))
    for yol, satir_no, kod in ihlaller:
        print(_rapor_satiri(yol, satir_no, kod, None))
    print()
    print("COZUM: satiri ACIP oku (bu rapor metni BILEREK yazmaz — gunluk PUBLIC'tir).")
    print("Ifsa ise: mekanizmayi ADSIZ anlat (ad/yol/kimlik yerine ROLUNU yaz) ya da")
    print("satiri git-disi arsive tasi. Satir CALISAN KOD ise zaten kapsam disidir —")
    print("kapsama girdiyse ANLATIM yuzeyindedir. MESRU ise gerekceyle muaf tut:")
    print("  python3 tools/spec-ifsa-kapisi.py --muafiyet-hash <dosya> <satir_no>")
    return 1


if __name__ == "__main__":
    sys.exit(main())
