#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SINIF KAPISI — "tools/ icindeki bir YORUM bir .py dosyasini NOBETCI diye aniyorsa o
dosya VAR OLMALI".

🔴 BU DOSYADA HAYALI ADLAR BILEREK CIPLAK YAZILIR (backtick YOK, "tools/" oneki YOK).
Sebep olculdu (11 Eyl, ilk canli kosum): gerekce blogunda adlari kaynak biciminde yazinca
KAPI KENDINI 5 IHLALLE KIRMIZI YAKTI. Kendini DISLAYAN bir istisna eklenmedi — istisna,
"ihlali bu dosyaya tasi" diye acik bir delik olurdu ([[kurucu-kendi-kapisina-takilir]]).

=== NEDEN VAR (olculmus ariza, 11 Eyl 2026 — BaBa ⑤ hukmu) ===
serbest-kume-tekkaynak-test.py dosyasi ca8c3815 ile SILINDI (28 Agu denetim-kucultme
supurmesi, 48 kapi/nobetci/batarya). Dosya gitti; onu NOBETCI diye anan YORUMLAR KALDI ve
ucu birden "CI'da kosar" diyordu (mimar-icra-kapisi.py:495 · serbest_cagrilar.py:28,32 ·
defter-rotasyon.py:905 -- sonuncusu "C3/C4 kaynak ile araci BIREBIR esitler; drift CI'da
KIRMIZI yanar" diyordu, oysa olcen KOD YOKTU).

BEDELI: yorum, okuyana OLMAYAN bir korumayi VAR gosterir. Bir mimar "o eksen nobetcide
olculuyor" diye okur, olcmez ve gecer. Bu, yesil yanan olu testle AYNI SINIFTIR — yalnizca
bir kat daha ucuzdur, cunku kod bile kosmaz ([[ci-disi-kabul-sarti-yorumda-yasarsa-koruma-
degildir]] · [[capa-cokmesi-arkasindaki-capalari-gizler]]).

Ayni turda ayni sinifin UC vakasi daha olculdu ve HICBIR nobetci gormuyordu:
  * motor-tek-kaynak-kapisi.py  <- mimar_kimlik.py hem YORUMDA anar hem de KURULAN kapi
    blogunun ICINE "Sapma nobetcisi: python3 ~/dev/pruvo/tools/ + o ad" satirini BASAR —
    yani yalan, kurulu kopyalara da tasiniyordu.
  * kapi-dagitim-kur.py + kapi-dagitim-test.py  <- kapi_dagitim.py "kurucu ... ve kabul
    testi ... UCU DE bu modulu cagirir" der; ikisi de YOK.

=== NE OLCER ===
tools/*.py icindeki YORUM ve UCLU-TIRNAK govdelerinde gecen `X.py` jetonlari taranir.
Bir jeton IHLAL sayilir ancak ve ancak:
  (a) jeton backtick icinde ya da `tools/` (veya `~/dev/pruvo/tools/`) onekiyle yazilmis
      -- yani bir DOSYAYA isaret ediyor, cumle icinde gecen bir kelime degil;
  (b) jetonun KENDI SATIRINDA ya da +-1 satirinda bir ROL sozcugu var (nobetci / kabul
      testi / batarya / mutasyonlu / ...) -- yani metin ona bir KORUMA ROLU yukluyor;
  (c) dosya ARAMA_KOK'lerin HICBIRINDE yok (tools/, repo koku, shop/, onizleme/,
      ~/.claude/cron/ ve sabah-teslim/ -- nobetci tools/ DISINDA da yasayabilir, dar
      cozucu SAHTE KIRMIZI uretirdi [[ortak-onbellekte-arac-evreni-onekle-ayrilir]]);
  (d) jeton, onu anan dosyanin KENDI adi degil.

🔴 NON-GROWTH: hukum SAYI DEGIL ARTIS uzerinedir. Bugunku ihlal sayisi TAVAN'dir; kapi
yalnizca tavan ASILIRSA kirmizi yanar. Sebep: tabandaki kalemlerin bir kismi TARIHSEL
ANLATIDIR (silinmis bir araci "o gun soyle olculmustu" diye anan cumle) ya da FIKSTUR
ORNEGIDIR; onlari toptan kirmizi yakmak kapiyi ilk gunde gurultuye bogar ve kapatilir.
Artisi durdurmak, mevcut kalemi tek tek temizlemekten AYRI ve daha degerli istir.

TAVAN dusurulebilir, YUKSELTILEMEZ: bir kalem temizlenince TAVAN yeni sayiya CEKILIR
(kapi bunu `--tavan-dusur` ile sayiyla soyler). Yukseltmek yeni ihlali mesrulastirir.

=== NE OLCMEZ (durust sinir) ===
* Dosya VAR ama ICI BOS / CI'da KOSMUYOR ise bu kapi YESIL yanar. "CI'da kosuyor mu"
  ekseni `tools/ci-kapsam-test.py`nin isidir; bu kapi yalniz VARLIK eksenini olcer.
* `.md` / `.mjs` / `.sh` nobetci atiflari KAPSAM DISI (bu turda olculmedi).

KOSUM: `python3 tools/hayali-nobetci-kapisi.py` (offline, ag ISTEMEZ, dosya YAZMAZ, ~0,4 s)
KABUL: `python3 tools/hayali-nobetci-kapisi.py --kendini-test`
CI:    `.github/workflows/nobet.yml::serit-b`
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🔴 TAVAN — 11 Eyl 2026'da OLCULEREK kondu (asagidaki temizlikten SONRA yeniden olculdu).
# Tabandaki kalemler ve NEDEN durduklari:
#   kok-cozum-taramasi.py (git_ortami.py)  — TARIHSEL ANLATI: 6 Agu curutucu
#       olcumunun anlatiminda gecer, koruma IDDIASI degil. Silinirse anlatinin kanit
#       zinciri kopar; bu yuzden BIRAKILDI.
#   x-test.py (ci-kapsam-test.py, 2 satir)  — FIKSTUR ORNEGI: o dosyanin gerekcesinde
#       gecen UYDURMA ornek addir ("... satirini silip yerine yorum birakinca kapi
#       SAHTE-YESIL kaliyordu"); gercek bir dosyaya isaret ETMEZ.
#   🔴 SINIR (durust): jeton BACKTICK ya da "tools/" oneki ister. Adi CIPLAK yazan bir
#       yalanci koruma cumlesi ("nobetci foo.py'dir") bu kapinin MENZILINDE DEGILDIR.
#       Genisletilmedi cunku ciplak ad ekseni SAHTE KIRMIZI uretiyordu (olculdu: normal
#       Turkce cumlelerdeki "test.py"/"kapisi.py" parcalari 18 hedefe sisiyordu).
TAVAN = 2

ROL_SOZCUKLERI = ("nobetci", "nöbetçi", "nobetcide", "nobetciye", "nobetcisi", "nobetcidir",
                  "nobetcinin", "kabul testi", "batarya", "mutasyonlu")

# (a) backtick'li `X.py` / `tools/X.py` YA DA (b) `tools/X.py` / `~/dev/pruvo/tools/X.py`.
JETON = re.compile(r"(?:`(?:tools/)?([A-Za-z0-9_][A-Za-z0-9_.-]*\.py)`"
                   r"|(?<![\w/`])(?:~/dev/pruvo/tools/|tools/)([A-Za-z0-9_][A-Za-z0-9_.-]*\.py))")


def arama_kokleri(kok):
    """Bir nobetci tools/ DISINDA da yasayabilir — cozucu dar olursa SAHTE KIRMIZI basar."""
    return (os.path.join(kok, "tools"), kok, os.path.join(kok, "shop"),
            os.path.join(kok, "onizleme"), os.path.expanduser("~/.claude/cron"),
            os.path.expanduser("~/.claude/cron/sabah-teslim"))


def metin_satirlari(yol):
    """{satir_no: metin} — YALNIZ yorum ve uclu-tirnak govdeleri (kod satirlari HARIC)."""
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except OSError:
        return {}
    cikti = {}
    try:
        for tok in tokenize.tokenize(io.BytesIO(ham).readline):
            if tok.type == tokenize.COMMENT:
                cikti[tok.start[0]] = tok.string
            elif tok.type == tokenize.STRING and tok.string[:3] in ('"""', "'''"):
                for i, s in enumerate(tok.string.splitlines()):
                    cikti[tok.start[0] + i] = s
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Ayristirilamayan dosya SESSIZCE YESIL SAYILMAZ: cagiran taraf bunu ayri sayar.
        return {"__AYRISTIRILAMADI__": True}
    return cikti


def tara(kok):
    """[(hedef, 'dosya:satir'), ...] — ihlaller. Ayrica ayristirilamayan dosya listesi."""
    tools = os.path.join(kok, "tools")
    kokler = arama_kokleri(kok)
    onbellek = {}

    def cozulur(ad):
        if ad not in onbellek:
            onbellek[ad] = any(os.path.exists(os.path.join(k, ad)) for k in kokler)
        return onbellek[ad]

    ihlaller = []
    ayristirilamayan = []
    for ad in sorted(os.listdir(tools)):
        if not ad.endswith(".py"):
            continue
        satirlar = metin_satirlari(os.path.join(tools, ad))
        if satirlar.get("__AYRISTIRILAMADI__"):
            ayristirilamayan.append(ad)
            continue
        for no, s in sorted(satirlar.items()):
            jetonlar = [a or b for a, b in JETON.findall(s)]
            if not jetonlar:
                continue
            # (b) ROL SOZCUGU JETONUN MENZILINDE: kendi satiri ya da +-1. Blok ekseni
            # SECILMEDI cunku 300 satirlik bir gerekce blogunda gecen HER ad rol
            # yuklenmis sayilirdi ([[nobetci-tabani-ucun-yukleminden-dar-kalirsa-
            # daraltma-olur]] tersi: cok GENIS taban da hukumsuzdur).
            cevre = " ".join(satirlar.get(no + d, "") for d in (-1, 0, 1)).lower()
            if not any(r in cevre for r in ROL_SOZCUKLERI):
                continue
            for hedef in jetonlar:
                # 🔴 "hedef == ad" (kendi adini anma) AYRI BIR KOL DEGILDIR ve bilerek
                # YAZILMADI: bir dosya kendi adini aniyorsa o dosya ZATEN vardir, yani
                # cozulur() onu kesiyor. Kol eklenseydi mutantla OLDURULEMEZDI — onu
                # oldurmenin hicbir vakayi kirmizi yakmadigi olculdu (11 Eyl kabul
                # kosumu, M4). Kapsam yanilsamasi yerine BOSLUK: bu satir yok.
                if cozulur(hedef):
                    continue
                ihlaller.append((hedef, "%s:%d" % (ad, no)))
    return ihlaller, ayristirilamayan


def main(argv):
    if "--kendini-test" in argv:
        return kendini_test()
    kok = KOK
    for i, a in enumerate(argv):
        if a == "--kok" and i + 1 < len(argv):
            kok = argv[i + 1]
    ihlaller, ayristirilamayan = tara(kok)
    hedefler = sorted({h for h, _ in ihlaller})
    for h in hedefler:
        yerler = [y for hh, y in ihlaller if hh == h]
        print("HAYALI %-42s %d atif  %s" % (h, len(yerler), " ".join(yerler)))
    for ad in ayristirilamayan:
        print("AYRISTIRILAMADI %s (OLCULEMEDI — tokenize coktu)" % ad)
    print("")
    print("HAYALI_HEDEF=%d  ATIF_SATIRI=%d  TAVAN=%d  AYRISTIRILAMAYAN=%d"
          % (len(hedefler), len(ihlaller), TAVAN, len(ayristirilamayan)))
    if len(hedefler) > TAVAN:
        print("SONUC: KIRMIZI — hayali nobetci atfi TAVANI ASTI (%d > %d). Yeni eklenen "
              "atfi ya GERCEK bir nobetciye baglayin ya 'NOBETCI YOK (acik kalem)' diye "
              "DURUST yazin." % (len(hedefler), TAVAN))
        return 1
    if ayristirilamayan:
        print("SONUC: OLCULEMEDI — %d dosya ayristirilamadi; tavan hukmu GUVENILIR DEGIL."
              % len(ayristirilamayan))
        return 2
    if len(hedefler) < TAVAN:
        print("SONUC: YESIL — ihlal TAVANIN ALTINDA (%d < %d). TAVAN'i %d'e CEKIN "
              "(non-growth ancak tavan dusurulurse ilerler)." % (len(hedefler), TAVAN,
                                                                 len(hedefler)))
        return 0
    print("SONUC: YESIL — %d hayali hedef (TAVAN=%d, artis YOK)." % (len(hedefler), TAVAN))
    return 0


# ===========================================================================
# KENDINI TEST — fikstur + mutasyon bataryasi.
# 🔴 HICBIR MUTANT CANLI GOVDEDE KOSMAZ: her mutant, gecici dizine cikarilmis IZOLE bir
# KOPYAYA uygulanir ve o kopya alt surec olarak kosturulur ([[mutant-canli-govdede-
# yasamaz]]). Fiksturler tempfile.mkdtemp() altinda dogar; GERCEK ev yoluna YAZILMAZ,
# gercek ev yolunda HICBIR SEY SILINMEZ (BaBa FILO DERSI ①).
# ===========================================================================

FIKSTURLER = {
    # ad: (tools/ altina yazilacak dosyalar, beklenen ihlal HEDEF sayisi, aciklama)
    "F1-hayali": ({"a.py": '# Nobetci: tools/yok-boyle-bir-sey.py (CI\'da kosar).\n'},
                  1, "rol sozcugu + var olmayan hedef -> IHLAL"),
    "F2-var": ({"a.py": '# Nobetci: tools/gercek.py (CI\'da kosar).\n',
                "gercek.py": "# ben varim\n"},
               0, "hedef VAR -> ihlal YOK"),
    "F3-uzak": ({"a.py": '# Nobetci listesi asagida.\n#\n#\n# tools/uzak-hedef.py\n'},
                0, "rol sozcugu +-1 MENZIL DISINDA -> ihlal YOK"),
    "F4-docstring": ({"a.py": '"""Baslik.\n\nNobetci: `tools/ds-hedefi.py` (mutasyonlu).\n"""\n'},
                     1, "UCLU-TIRNAK govdesi de taranir"),
    "F5-kendi-adi": ({"a.py": '# Nobetci: tools/a.py (kendi adi).\n'},
                     0, "dosya KENDI adini anar -> ihlal YOK (cozulur() keser, ayri kol YOK)"),
    "F6-kod-satiri": ({"a.py": 'YOL = "tools/kod-icinde.py"  # nobetci degil, veri\n'},
                      0, "KOD satirindaki dizge yorum DEGIL -> ihlal YOK"),
    "F7-rolsuz": ({"a.py": '# Ilgili dosya: `tools/rolsuz-hedef.py` (sadece anilir).\n'},
                  0, "ROL sozcugu YOK -> ihlal YOK"),
    "F8-iki-hedef": ({"a.py": '# Nobetci: tools/bir.py\n# Kabul testi: tools/iki.py\n'},
                     2, "iki ayri hayali hedef ayri ayri sayilir"),
}


def _fikstur_kur(kok, dosyalar):
    tools = os.path.join(kok, "tools")
    os.makedirs(tools, exist_ok=True)
    for ad, govde in dosyalar.items():
        with open(os.path.join(tools, ad), "w", encoding="utf-8") as f:
            f.write(govde)


# Mutantlar: (ad, eski_parca, yeni_parca, hedef_fikstur, komsu_fikstur, aciklama)
# HEDEF fikstur mutantla YANLIS cevap vermeli; KOMSU fikstur DOGRU kalmali
# ([[mutant-yardimcisi-neyi-yamadigi-imzasindan-okunmaz]] — her mutant IKI sey kanitlar).
MUTANTLAR = (
    ("M1-docstring-kolu-olur",
     'elif tok.type == tokenize.STRING and tok.string[:3] in (\'"""\', "\'\'\'"):',
     'elif False:',
     "F4-docstring", "F1-hayali",
     "uclu-tirnak kolu olurse docstring atfi GORUNMEZ olur"),
    ("M2-menzil-tum-dosyaya-acilir",
     'cevre = " ".join(satirlar.get(no + d, "") for d in (-1, 0, 1)).lower()',
     'cevre = " ".join(satirlar.values()).lower()',
     "F3-uzak", "F1-hayali",
     "menzil tum dosyaya acilirsa UZAK atif da ihlal sayilir (sahte kirmizi)"),
    ("M3-cozucu-daralir",
     'onbellek[ad] = any(os.path.exists(os.path.join(k, ad)) for k in kokler)',
     'onbellek[ad] = os.path.exists(os.path.join(kok, "tools", ad)) and False',
     "F2-var", "F3-uzak",
     "cozucu daralirsa VAR OLAN hedef de 'yok' sayilir"),
    ("M5-rol-kapisi-duser",
     'if not any(r in cevre for r in ROL_SOZCUKLERI):',
     'if False:',
     # 🔴 KOMSU F3 SECILEMEZ: F3'u koruyan sey de AYNI satirdir (menzil kontrolu rol
     # kapisinin icinde yasar), yani "komsu YESIL kaldi" iddiasi YAPISAL OLARAK
     # imkansizdi (11 Eyl kabul kosumunda olculdu). Komsu, BASKA bir kolla korunan
     # F6 olmali ([[mutant-yardimcisi-neyi-yamadigi-imzasindan-okunmaz]]).
     "F7-rolsuz", "F6-kod-satiri",
     "rol kapisi duserse ROLSUZ her atif ihlal sayilir"),
    ("M6-yorum-kolu-olur",
     'if tok.type == tokenize.COMMENT:',
     'if False:',
     "F1-hayali", "F4-docstring",
     "yorum kolu olurse YORUMDAKI atif gorunmez"),
    ("MK-KONTROL-bicimsel",
     'print("HAYALI %-42s %d atif  %s"',
     'print("HAYALI %-42s %d atif %s"',
     None, None,
     "KONTROL: yalniz bicim degisir -> HICBIR fikstur bozulmamali"),
)

# META MUTANT — cikis kodu kolunu duzlestirir. ①'in ta kendisi: govde KIRMIZI derken
# rc=0 donmek FAIL-OPEN'dir ([[vaka-sayisi-ekseni-cikis-kodu-eksenini-olcmez]]).
META_MUTANTLARI = (
    ("ME1-rc-kolu-duzlesir",
     '        return 1\n    if ayristirilamayan:',
     '        return 0\n    if ayristirilamayan:',
     "TAVAN ASILDI ama rc=0 -> yakalanmali"),
)


def _kopya_kur(dizin, eski=None, yeni=None):
    """Bu dosyanin IZOLE kopyasini uretir; istenirse tek parca degistirilir."""
    with open(os.path.abspath(__file__), "r", encoding="utf-8") as f:
        govde = f.read()
    if eski is not None:
        # 🔴 CAPA YALNIZ ICRA EDILEN GOVDEDE ARANIR: mutant TABLOSU capa dizgesinin
        # IKINCI KOPYASINI tasir; tum dosyada arayan bir replace() tabloyu da bozar ve
        # "capa tek degil" diye coker ([[mutant-capasi-giris-noktasinin-okumadigi-
        # degerde-olmez]] — capa, kosan kolun TA KENDISINDE olmali).
        ayrac = "\nMUTANTLAR = ("
        if ayrac not in govde:
            raise AssertionError("MUTANT TABLOSU AYRACI BULUNAMADI")
        icra, tablo = govde.split(ayrac, 1)
        if icra.count(eski) != 1:
            raise AssertionError("MUTANT CAPASI ICRA GOVDESINDE TEK DEGIL (%d): %r"
                                 % (icra.count(eski), eski[:60]))
        govde = icra.replace(eski, yeni) + ayrac + tablo
    yol = os.path.join(dizin, "kapi-kopya.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde)
    return yol


def _kos(kapi_yolu, fikstur_kok):
    proc = subprocess.run([sys.executable, kapi_yolu, "--kok", fikstur_kok],
                          capture_output=True, text=True)
    hedef = 0
    for s in proc.stdout.splitlines():
        if s.startswith("HAYALI_HEDEF="):
            hedef = int(s.split("HAYALI_HEDEF=")[1].split()[0])
    return hedef, proc.returncode, proc.stdout


def kendini_test():
    gecici = tempfile.mkdtemp(prefix="hayali-nobetci-kabul-")
    basarisiz = []
    iddia = 0
    try:
        fikstur_kok = {}
        for ad, (dosyalar, _bek, _acik) in FIKSTURLER.items():
            k = os.path.join(gecici, "fx", ad)
            _fikstur_kur(k, dosyalar)
            fikstur_kok[ad] = k

        taban_kapi = _kopya_kur(gecici)

        # --- A: TABAN (mutantsiz) her fiksturu DOGRU okumali ---
        for ad, (_d, beklenen, aciklama) in FIKSTURLER.items():
            hedef, _rc, _c = _kos(taban_kapi, fikstur_kok[ad])
            iddia += 1
            tamam = hedef == beklenen
            print("A %-14s beklenen=%d olculen=%d  %s  %s"
                  % (ad, beklenen, hedef, "GECTI" if tamam else "❌", aciklama))
            if not tamam:
                basarisiz.append("A/" + ad)

        # --- B: CIKIS KODU IKI YONLU CIVILI (①) ---
        # B1: ihlal TAVAN'i asarsa rc MUTLAKA != 0.
        asan = os.path.join(gecici, "fx-asan")
        _fikstur_kur(asan, {"a.py": "".join(
            "# Nobetci: tools/hayali-%d.py\n" % i for i in range(TAVAN + 2))})
        hedef, rc, _c = _kos(taban_kapi, asan)
        iddia += 1
        tamam = hedef > TAVAN and rc != 0
        print("B1 tavan-asan   hedef=%d>TAVAN=%d rc=%d  %s  (govde KIRMIZI ise rc!=0)"
              % (hedef, TAVAN, rc, "GECTI" if tamam else "❌"))
        if not tamam:
            basarisiz.append("B1-rc-kirmizi")
        # B2: ihlal YOKSA rc MUTLAKA 0.
        temiz = os.path.join(gecici, "fx-temiz")
        _fikstur_kur(temiz, {"a.py": "# hicbir sey yok\n"})
        hedef, rc, _c = _kos(taban_kapi, temiz)
        iddia += 1
        tamam = hedef == 0 and rc == 0
        print("B2 temiz        hedef=%d rc=%d  %s  (govde YESIL ise rc=0)"
              % (hedef, rc, "GECTI" if tamam else "❌"))
        if not tamam:
            basarisiz.append("B2-rc-yesil")

        # --- C: MUTASYON BATARYASI (hedef OLUR + komsu YASAR) ---
        for ad, eski, yeni, hedef_fx, komsu_fx, aciklama in MUTANTLAR:
            mut_dizin = os.path.join(gecici, "mut", ad)
            os.makedirs(mut_dizin, exist_ok=True)
            mut_kapi = _kopya_kur(mut_dizin, eski, yeni)
            if hedef_fx is None:
                # KONTROL MUTANTI: hicbir fiksturu bozmamali.
                bozulan = []
                for fx, (_d, beklenen, _a) in FIKSTURLER.items():
                    h, _rc, _c = _kos(mut_kapi, fikstur_kok[fx])
                    if h != beklenen:
                        bozulan.append(fx)
                iddia += 1
                tamam = not bozulan
                print("C %-26s KONTROL bozulan=%d  %s  %s"
                      % (ad, len(bozulan), "GECTI" if tamam else "❌", aciklama))
                if not tamam:
                    basarisiz.append("C/" + ad)
                continue
            h_hedef, _rc, _c = _kos(mut_kapi, fikstur_kok[hedef_fx])
            h_komsu, _rc2, _c2 = _kos(mut_kapi, fikstur_kok[komsu_fx])
            oldu = h_hedef != FIKSTURLER[hedef_fx][1]
            komsu_yasadi = h_komsu == FIKSTURLER[komsu_fx][1]
            iddia += 1
            tamam = oldu and komsu_yasadi
            print("C %-26s hedef(%s)=%s komsu(%s)=%s  %s  %s"
                  % (ad, hedef_fx, "OLDU" if oldu else "YASADI",
                     komsu_fx, "YESIL" if komsu_yasadi else "BOZULDU",
                     "GECTI" if tamam else "❌", aciklama))
            if not tamam:
                basarisiz.append("C/" + ad)

        # --- D: META MUTANT — rc kolunu duzlestiren mutant YAKALANMALI ---
        for ad, eski, yeni, aciklama in META_MUTANTLARI:
            mut_dizin = os.path.join(gecici, "meta", ad)
            os.makedirs(mut_dizin, exist_ok=True)
            mut_kapi = _kopya_kur(mut_dizin, eski, yeni)
            h, rc, _c = _kos(mut_kapi, asan)
            iddia += 1
            # Mutant rc'yi duzlestirdi -> B1 iddiasi ONU YAKALAMALI (rc==0 iken hedef>TAVAN).
            yakalandi = h > TAVAN and rc == 0
            print("D %-26s hedef=%d rc=%d  %s  %s"
                  % (ad, h, rc, "GECTI (B1 bu mutanti yakalar)" if yakalandi else "❌",
                     aciklama))
            if not yakalandi:
                basarisiz.append("D/" + ad)
    finally:
        # Gecici dizin tempfile.mkdtemp() ile DOGDU; gercek ev yolu MENZILDE DEGIL.
        shutil.rmtree(gecici, ignore_errors=True)

    print("")
    if basarisiz:
        print("SONUC: KIRMIZI — %d/%d iddia dustu: %s"
              % (len(basarisiz), iddia, ", ".join(basarisiz)))
        return 1
    print("SONUC: YESIL — %d iddia kosuldu (%d fikstur + 2 cikis-kodu kolu + %d mutant "
          "(1'i KONTROL) + %d meta mutant)."
          % (iddia, len(FIKSTURLER), len(MUTANTLAR), len(META_MUTANTLARI)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
