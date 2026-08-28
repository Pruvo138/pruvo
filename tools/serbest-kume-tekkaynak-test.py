"""K320 + 28 AGU SINIF ISI — SERBEST CAGRI SEKILLERI GERCEKTEN TEK KAYNAK MI?

=== NEDEN VAR (iki katmanli olculmus ariza) ===
① 27 AGU 2026 (K320) — RED METNI IKINCI KOPYAYDI.
`mimar-icra-kapisi.py` red metninde "SERBEST / REDDEDILEN" kumelerini ELLE sayiyordu;
metin karari veren yapidan AYRISTI (TABAN DRIFT=9). Bedel yanlis kararla AYNIYDI: mimar
kendi kapisinin bastigi CAREYI okudu, metne inandi, "care oteki kapida olu" hukmunu verdi
ve defter UC KOSUM boyunca tavanin USTUNDE kaldi — oysa cagri O TARIHTE ZATEN GECIYORDU.

② 28 AGU 2026 (BU IS) — K320 yalniz ARAC ADINI turetmisti; CAGRI SEKLI (bayraklar +
konumsal argumanlar) her tuketicide ELLE yaziliydi. Olculen taban:
  * `cip_dogum_bekcisi.py --teslim-karari` / `--teslim-kaydet` -> RED. Bekcinin TESLIM
    KOLU tam bu cagriyi yapar; hukum KIRMIZI ciktigi gun mimar careyi ELIYLE kosamiyordu.
    Kapinin serbest listesinde `cip_dogum_bekcisi` HIC gecmiyordu (0 satir).
  * `defter-rotasyon.py --tavan-kaynaktan --isaretciye-indir` (KONUMSUZ kisa form) -> RED.
  * ELLE yazilmis cagri-sekli dizgesi UC tuketicide 46 kez tekrarlaniyordu.
Cozum SINIFSALDIR: `tools/serbest_cagrilar.py` TEK KAYNAK; KARAR, RED METNI ve CARE
satirlari oradan turer. Bu nobetci o tek kaynagi mutasyonla olcer.

=== NE OLCER ===
  A1  python ekseni: red metni, karar yapisindaki HER araci ADIYLA aniyor mu?
  A2  olcum ekseni: red metni, OLCUM_KOMUTLARI'nin HER uyesini aniyor mu?
  A3  🔴 TERS YON: red metninin python PARCASI turetilmise BIREBIR esit mi?
      (A1 yalniz `makine ⊆ metin` olcer; `metin ⊆ makine` olculmezse metne ELLE
      fazladan ad eklemek nobetciyi GECER — 28 Agu'da olculdu.)
  A4  A3'un olcum ekseni karsiligi.
  B1  CAGRI YERI: kota kapisinin bastigi CARE gercekten GECIYOR mu?
  B2  CAGRI YERI: kume DISI bayrak (--tavan-sayi) hala RED mi? (kova gevsemedi)
  B3  RED sebebi okuyana TAM kumeyi gosteriyor mu?
  B4  🔴 CIP-DOGUM BEKCISI teslim cagrilari GECIYOR mu? (28 Agu tabanda IKISI DE RED)
  B5  🔴 K332 EKSENI KORUNDU MU: ana oturumda OLCUM komutu HALA RED mi? Bu kol
      olmadan "bekciyi actim" bulgusu, kapiyi TOPTAN gevsetmekten ayirt EDILEMEZDI.
  B6  🔴 KONUMSUZ KISA FORM geciyor mu (28 Agu tabanda RED)?
  C1  TUKETICI #2 (defter-kota-kapisi.py): bastigi CARE satiri, turetilmis ornege
      BIREBIR esit mi?
  C2  🔴 TUKETICI GERCEKTEN OKUYOR MU: kaynaktan bir BAYRAK dusunce tuketicinin CARE
      satiri DEGISIYOR mu? (Sabit dizge tutan tuketicide DEGISMEZ — MX4 bunu kullanir.)

=== MUTANTLAR (her biri HEDEF KOL atfiyla) ===
  MX1 LISTE BOZULUR      : SEKILLER bosaltilir -> TUM serbest cagrilar RED + metin bosalir
  MX2 BIR OGE DUSER      : rotasyon sekilleri dusurulur -> CARE RED, adi metinden duser,
                           KOMSU (kutu-arsivle) YASAR (tek anahtar hepsini kapatmiyor)
  MX3 BAYRAK FORMU DEGISIR: kovadaki bayrak adi degistirilir -> ESKI form RED, metinde
                           YENI bayrak gorunur (sekil bayragi GERCEKTEN tasiyor)
  MX4 TUKETICI OKUMAYI BIRAKIR: kota kapisi CARE'i SABIT DIZGEYE cevirir -> C2 KIRMIZI
  M3  OLCUM kumesine uydurma komut eklenir -> metinde GORUNUR
  M5  TERS-YON: metne ELLE sahte arac eklenir -> A3 KIRMIZI, A1 YESIL kalir (kolun A3
      oldugunu KANITLAR — [[ad-iki-rolde-mutanti-golgeler]])
  M4  NEGATIF KONTROL: mutasyonsuz kopya HER kolda taban gibi davranir

Her mutant icin AYRICA "mutant kaynaga ULASTI MI" olculur (capa TEKIL ve kaynak
DEGISTI); ulasmayan mutant KIRMIZI sayilir, yesil DEGIL
([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).

Hukum UC DEGERLIDIR: GECTI / RED / COKTU. Coken bir kopya "RED" diye okunursa mutant
tablosu yalan soyler ([[capa-cokmesi-arkasindaki-capalari-gizler]]).

Gecici mutant kopyalari git-DISI tempdir'e yazilir (repo agacina iz birakilmaz).
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ARACLAR = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(ARACLAR, "mimar-icra-kapisi.py")
SERBEST = os.path.join(ARACLAR, "serbest_cagrilar.py")
KOTA = os.path.join(ARACLAR, "defter-kota-kapisi.py")
KOTA_TABAN = os.path.join(ARACLAR, "defter-kota-taban.py")
KIMLIK = os.path.join(ARACLAR, "mimar_kimlik.py")
ANA_TP = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/ana.jsonl"

# Mutant dizinine TASINACAK dosyalar — biri eksik kalirsa kopya import'ta COKER.
YAN_DOSYALAR = (KAPI, SERBEST, KOTA, KOTA_TABAN, KIMLIK)


# --- ALT-KOSUM MODU: verilen tools dizinindeki KOTA kapisinin CARE satirlarini bas.
# Ayri bir surucu betigi YAZILMAZ (repo agacina iz birakmamak icin); nobetci kendini
# cagirir ve o dizini sys.path'in BASINA koyar.
if len(sys.argv) > 2 and sys.argv[1] == "--kota-care":
    _dizin = sys.argv[2]
    sys.path.insert(0, _dizin)
    _spec = importlib.util.spec_from_file_location(
        "kota_kapisi_probu", os.path.join(_dizin, "defter-kota-kapisi.py"))
    _kota = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_kota)
    _tampon = io.StringIO()
    with tempfile.TemporaryDirectory(prefix="kota-care-") as _t:
        os.environ["PRUVO_DEFTER_KOTA_SAYAC"] = os.path.join(_t, "sayac.tsv")
        with contextlib.redirect_stderr(_tampon):
            _kota._hukum_red(999, 99999, "satir", _t)
    for _s in _tampon.getvalue().splitlines():
        if _s.startswith("!! CARE:"):
            print(_s[len("!! CARE:"):].strip())
    sys.exit(0)


sonuclar = []


def kaydet(ad, gecti, ayrinti=""):
    sonuclar.append((ad, gecti, ayrinti))


# 🔴 ONBELLEK TUZAGI (28 Agu, BU KOSUMDA OLCULDU): kapinin govdesi
# `import serbest_cagrilar` yapiyor. Ilk yuklemede modul `sys.modules`e girer ve
# SONRAKI mutant yuklemeleri o ONBELLEKTEN gelir — mutant kaynagi degistirmis olsa
# bile in-process metin kontrolu TABANI okur. Olculen sonuc: MX1 ve MX3 "ad dusmedi"
# diyerek KIRMIZI yandi; sessiz kalsalardi mutant ULASMADIGI halde YESIL sayilirdi
# ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]). Cozum: her yuklemede paylasilan
# modul adlarini onbellekten DUSUR.
ONBELLEK_DUSENLER = ("serbest_cagrilar", "mimar_kimlik")


def modul_yukle(yol, ad, dizin=None):
    ortam_yolu = list(sys.path)
    onbellek = {a: sys.modules.pop(a) for a in ONBELLEK_DUSENLER if a in sys.modules}
    sys.path.insert(0, dizin or ARACLAR)
    try:
        spec = importlib.util.spec_from_file_location(ad, yol)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul
    finally:
        sys.path[:] = ortam_yolu
        for a in ONBELLEK_DUSENLER:
            sys.modules.pop(a, None)
        sys.modules.update(onbellek)


# TEK KAYNAK — fikstuler BURADAN turer, ELLE YAZILMAZ.
SC = modul_yukle(SERBEST, "serbest_cagrilar_taban")

CARE = SC.cagri_ornegi("rotasyon-bakim")
CARE_KUTU = SC.cagri_ornegi("kutu-arsivle")
KISA_FORM = SC.cagri_ornegi("rotasyon-kisa")
BEKCI_KARAR = SC.cagri_ornegi("bekci-teslim-karari")
BEKCI_KAYDET = SC.cagri_ornegi("bekci-teslim-kaydet")
KUME_DISI = CARE + " --tavan-sayi 130"
OLCUM_CAGRISI = "tail -5 /Users/okan/dev/pruvo/DEVAM.md"


def kapi_kos(kapi_yolu, komut, dizin=None):
    """Kapiyi BETIK olarak kosar. Doner: ('GECTI'|'RED'|'COKTU', sebep_metni)."""
    girdi = {"tool_name": "Bash", "tool_input": {"command": komut},
             "cwd": "/Users/okan/dev/pruvo", "transcript_path": ANA_TP}
    ortam = dict(os.environ)
    ortam["PYTHONPATH"] = dizin or ARACLAR
    p = subprocess.run([sys.executable, kapi_yolu], input=json.dumps(girdi),
                       capture_output=True, text=True, env=ortam)
    cikti = p.stdout.strip()
    if cikti:
        try:
            veri = json.loads(cikti)
        except Exception:
            return "COKTU", "stdout JSON degil: " + cikti[:160]
        ozel = veri.get("hookSpecificOutput") or {}
        if ozel.get("permissionDecision") == "deny":
            return "RED", ozel.get("permissionDecisionReason", "")
        return "COKTU", "beklenmedik karar: " + str(ozel.get("permissionDecision"))
    if p.returncode != 0:
        satirlar = [s for s in p.stderr.strip().splitlines() if s.strip()]
        return "COKTU", (satirlar[-1] if satirlar else "rc=" + str(p.returncode))[:200]
    return "GECTI", ""


def kota_care(dizin):
    """Verilen tools dizinindeki KOTA kapisinin bastigi CARE satirlari."""
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--kota-care", dizin],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None, (p.stderr.strip().splitlines() or ["rc!=0"])[-1][:180]
    return [s for s in p.stdout.splitlines() if s.strip()], None


def evren_kur(tmp, hedef=None, eski=None, yeni=None):
    """Mutant evreni: YAN_DOSYALAR kopyalanir, istenirse BIRI mutasyona ugrar.

    Doner: (dizin, None) ya da (None, 'MUTANT ULASMADI — ...').
    ULASIM iki yonlu olculur: capa TEKIL olmali VE kaynak DEGISMIS olmali."""
    for kaynak in YAN_DOSYALAR:
        shutil.copy2(kaynak, os.path.join(tmp, os.path.basename(kaynak)))
    if hedef is None:
        return tmp, None
    yol = os.path.join(tmp, os.path.basename(hedef))
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    adet = govde.count(eski)
    if adet != 1:
        return None, ("MUTANT ULASMADI — capa %s icinde %d kez bulundu (1 bekleniyordu)"
                      % (os.path.basename(hedef), adet))
    mutant = govde.replace(eski, yeni, 1)
    if mutant == govde:
        return None, "MUTANT ULASMADI — kaynak DEGISMEDI"
    with open(yol, "w", encoding="utf-8") as f:
        f.write(mutant)
    return tmp, None


# --- TERS YON (A3/A4): metnin ILGILI PARCASI, turetilmis dizgeye BIREBIR esit mi?
# Parca, GEREKCE_SONU icindeki SABIT komsu metinlerle sinirlanir. Sinir bulunamazsa
# hukum "OLCULEMEDI"dir ve KIRMIZI sayilir (fail-closed) — bir gun metin yeniden
# yazilirsa kol sessizce yesile donmez.
PY_ON, PY_ARKA = "python YALNIZ şunlar: ", "; /.claude/worktrees/"
OLCUM_ON, OLCUM_ARKA = "filament, curl, ", ", node --check"


def parca(metin, on, arka):
    """on...arka arasindaki TEK parcayi dondurur; sinirlar tekil degilse None."""
    if metin.count(on) != 1 or metin.count(arka) != 1:
        return None
    bas = metin.index(on) + len(on)
    son = metin.index(arka)
    if son <= bas:
        return None
    return metin[bas:son]


def ters_yon(modul):
    """(py_uyumlu, olcum_uyumlu, ayrinti) — A3/A4'un ORTAK govdesi. M5 de bunu cagirir."""
    metin = modul.GEREKCE_SONU
    p_py = parca(metin, PY_ON, PY_ARKA)
    p_ol = parca(metin, OLCUM_ON, OLCUM_ARKA)
    b_py = modul.serbest_python_metni()
    b_ol = modul.olcum_komut_metni()
    ayrinti = []
    if p_py is None:
        ayrinti.append("py parcasi OLCULEMEDI (sinir metni tekil degil)")
    elif p_py != b_py:
        ayrinti.append("py FAZLASI/EKSIGI: " + repr(p_py.replace(b_py, "<TURETILMIS>"))[:110])
    if p_ol is None:
        ayrinti.append("olcum parcasi OLCULEMEDI (sinir metni tekil degil)")
    elif p_ol != b_ol:
        ayrinti.append("olcum FAZLASI/EKSIGI: " + repr(p_ol.replace(b_ol, "<TURETILMIS>"))[:110])
    return (p_py == b_py, p_ol == b_ol,
            " · ".join(ayrinti) or "parcalar TURETILMISE BIREBIR ESIT")


def arac_adlari(sc_modul):
    """Kararin okudugu yapidan serbest arac adlari — ikinci liste TUTULMAZ."""
    return sc_modul.arac_adlari()


# ---------------------------------------------------------------- A) TURETILMISLIK
K = modul_yukle(KAPI, "kapi_taban")
metin = K.GEREKCE_SONU

bekleyen_py = sorted(arac_adlari(SC))
eksik_py = [a for a in bekleyen_py if a not in metin]
kaydet("A1 python ekseni: makinedeki HER arac red metninde",
       not eksik_py,
       "makine=%d metinde_eksik=%s" % (len(bekleyen_py), eksik_py or "YOK"))

eksik_olcum = sorted(k for k in K.OLCUM_KOMUTLARI if k not in metin)
kaydet("A2 olcum ekseni: OLCUM_KOMUTLARI'nin HER uyesi red metninde",
       not eksik_olcum,
       "makine=%d metinde_eksik=%s" % (len(K.OLCUM_KOMUTLARI), eksik_olcum or "YOK"))

py_uyumlu, olcum_uyumlu, ters_ayrinti = ters_yon(K)
kaydet("A3 TERS YON: red metninin python parcasi TURETILMISE BIREBIR esit",
       py_uyumlu, ters_ayrinti)
kaydet("A4 TERS YON: red metninin olcum parcasi TURETILMISE BIREBIR esit",
       olcum_uyumlu, ters_ayrinti)

# ---------------------------------------------------------------- B) CAGRI YERI
hukum, _ = kapi_kos(KAPI, CARE)
kaydet("B1 CAGRI YERI: kota kapisinin bastigi CARE gecer", hukum == "GECTI", "hukum=" + hukum)

hukum_disi, _ = kapi_kos(KAPI, KUME_DISI)
kaydet("B2 CAGRI YERI: kume DISI bayrak (--tavan-sayi) RED kalir",
       hukum_disi == "RED", "hukum=" + hukum_disi)

hukum_olcum, sebep_olcum = kapi_kos(KAPI, OLCUM_CAGRISI)
turetilmis_gorunur = all(a in sebep_olcum for a in bekleyen_py)
kaydet("B3 RED sebebi okuyana TAM kumeyi gosterir (tail reddinde)",
       hukum_olcum == "RED" and turetilmis_gorunur,
       "hukum=%s tam_kume=%s" % (hukum_olcum, turetilmis_gorunur))

h_karar, _ = kapi_kos(KAPI, BEKCI_KARAR)
h_kaydet, _ = kapi_kos(KAPI, BEKCI_KAYDET)
kaydet("B4 CIP-DOGUM BEKCISI teslim cagrilari GECER (taban: ikisi de RED)",
       h_karar == "GECTI" and h_kaydet == "GECTI",
       "--teslim-karari=%s --teslim-kaydet=%s" % (h_karar, h_kaydet))

# 🔴 B5 — K332 EKSENI: bekci kovasi ACILDI diye kapi TOPTAN gevsemedi mi? Bu kol
# olmadan B4'un yesili "kapiyi actim" ile ayirt edilemezdi.
h_olcum2, _ = kapi_kos(KAPI, "du -sh /Users/okan/dev/pruvo")
h_genel_py, _ = kapi_kos(KAPI, "python3 /Users/okan/dev/pruvo/tools/build.py")
h_satir_ici, _ = kapi_kos(KAPI, "python3 -c 'print(1)'")
kaydet("B5 K332 EKSENI KORUNDU: ana oturumda olcum/genel-python/satir-ici HALA RED",
       h_olcum2 == "RED" and h_genel_py == "RED" and h_satir_ici == "RED",
       "du=%s genel_py=%s satir_ici=%s" % (h_olcum2, h_genel_py, h_satir_ici))

h_kisa, _ = kapi_kos(KAPI, KISA_FORM)
kaydet("B6 KONUMSUZ KISA FORM gecer (taban: RED)", h_kisa == "GECTI", "hukum=" + h_kisa)

# ---------------------------------------------------------------- C) TUKETICI #2
with tempfile.TemporaryDirectory(prefix="pruvo-tk-c1-") as _t:
    _d, _h = evren_kur(_t)
    care_satirlari, care_hata = kota_care(_d)
    if care_satirlari is None:
        kaydet("C1 TUKETICI #2 (kota kapisi) CARE satiri TURETILMISE BIREBIR esit",
               False, "OLCULEMEDI: " + str(care_hata))
        taban_care = None
    else:
        taban_care = care_satirlari
        kaydet("C1 TUKETICI #2 (kota kapisi) CARE satiri TURETILMISE BIREBIR esit",
               CARE in care_satirlari,
               "basilan=%r · turetilmis=%r" % (care_satirlari[:1], CARE[:60]))

# C2 — TUKETICI GERCEKTEN OKUYOR MU? Kaynaktan bir BAYRAK dusunce CARE DEGISMELI.
BAYRAK_DUSUR_ESKI = ("ROTASYON_BAKIM_BAYRAKLARI = (ROTASYON_TAVAN_BAYRAGI, "
                     "ROTASYON_INDIRME_BAYRAGI)\n")
BAYRAK_DUSUR_YENI = "ROTASYON_BAKIM_BAYRAKLARI = (ROTASYON_TAVAN_BAYRAGI,)\n"


def c2_olc(kota_mutasyonu=None):
    """Kaynaktan bayrak dusurulunce tuketicinin CARE'i DEGISIYOR mu?

    kota_mutasyonu verilirse TUKETICI de bozulur (MX4): sabit dizge tutan tuketici
    kaynagi okumadigi icin CARE DEGISMEZ ve bu kol KIRMIZI yanar."""
    with tempfile.TemporaryDirectory(prefix="pruvo-tk-c2-") as t:
        d, h = evren_kur(t, SERBEST, BAYRAK_DUSUR_ESKI, BAYRAK_DUSUR_YENI)
        if d is None:
            return None, h
        if kota_mutasyonu is not None:
            eski, yeni = kota_mutasyonu
            yol = os.path.join(d, os.path.basename(KOTA))
            with open(yol, encoding="utf-8") as f:
                g = f.read()
            if g.count(eski) != 1:
                return None, "MUTANT ULASMADI — kota capasi tekil degil"
            with open(yol, "w", encoding="utf-8") as f:
                f.write(g.replace(eski, yeni, 1))
        satirlar, hata = kota_care(d)
        if satirlar is None:
            return None, "OLCULEMEDI: " + str(hata)
        return satirlar, None


# 🔴 C3 — KAYNAK ile ARACIN KENDISI AYRISMASIN. Kaynak "bu bayrak serbest" der; araci
# o bayragi GERCEKTEN taniyor mu? Ikisi ayri yerlerde yasadigi icin (kaynak kapinin
# kararini, argparse aracin sozlesmesini tasir) sessizce ayrisabilirler: kapi gecirir,
# arac "unrecognized arguments" ile COKER — yani kapi CALISMAYAN bir sey vaat eder.
# Bu, K320'nin kapattigi arizanin arac tarafindaki yuzudur. Repo DISI araclar da
# okunur (bekci ~/.claude/cron altinda); dosya yoksa hukum OLCULEMEDI = KIRMIZI.
# 🔴 KANONIK YOL -> BU AGACIN YOLU. Kaynaktaki arac yollari ANA CHECKOUT'a capalidir
# (kapinin karari oyle olmali). Ama C3/C4 KAYNAK-ARAC TUTARLILIGINI olcer ve o olcum
# BU AGACIN gonderdigi dosyalar uzerinde yapilmalidir; ana checkout'u okumak, dalda
# yesillenemeyen (yalniz merge'den SONRA yesillenen) bir kol uretirdi — yani nobetci
# dalda ISE YARAMAZDI. Repo DISI araclar (bekci) tek nushadir, aynen okunur.
AGAC_KOKU = os.path.dirname(ARACLAR)


def yerel_arac(sc_modul, yol):
    if yol.startswith(sc_modul.REPO_ONEKI):
        return os.path.join(AGAC_KOKU, yol[len(sc_modul.REPO_ONEKI):])
    return yol


def c3_olc(sc_modul):
    """(eksik_bayraklar, okunamayan_araclar) — kaynak ile aracin CLI'si uyumlu mu?"""
    eksik, okunamayan = [], []
    for s in sc_modul.SEKILLER:
        arac = yerel_arac(sc_modul, s.arac)
        if not os.path.exists(arac):
            okunamayan.append(sc_modul._kisa(s.arac))
            continue
        with open(arac, encoding="utf-8") as f:
            govde = f.read()
        for b in sorted(s.tum_bayraklar):
            if ('"' + b + '"') not in govde and ("'" + b + "'") not in govde:
                eksik.append("%s::%s" % (s.etiket, b))
    return eksik, okunamayan


c3_eksik, c3_okunamayan = c3_olc(SC)
kaydet("C3 KAYNAK/ARAC UYUMU: kaynaktaki HER bayrak aracin CLI'sinda VAR",
       not c3_eksik and not c3_okunamayan,
       "eksik=%s · okunamayan_arac=%s" % (c3_eksik or "YOK", c3_okunamayan or "YOK"))


# 🔴 C4 — KANONIK KONUMSAL YOLLAR: KAYNAK ile ARACIN VARSAYILANI BIREBIR ESIT MI?
# `defter-rotasyon.py` KISA FORMU (konumsuz) desteklemek icin kanonik DEVAM.md /
# DEVAM-ARSIV.md yollarini KENDI sabitlerinde tutar. Bunlari calisma aninda bu
# kaynaktan OKUTMAK denendi ve GERI ALINDI: aracin govdesini gecici dizine
# kopyalayan YEDI harness birden kirildi (modul kopyanin yaninda olmadigi icin arac
# import'ta coktu). Bagimlilik TERSE cevrildi; ayrisma riski BURADA olculur.
# Karsilastirma DIZGE degil, AYRISTIRILMIS SABIT uzerinden yapilir; sabit
# bulunamazsa hukum OLCULEMEDI = KIRMIZI (fail-closed).
import ast as _ast


def c4_olc(sc_modul):
    """(uyum, ayrinti) — aracin _KANONIK_* sabitleri kaynagin konumlariyla esit mi?"""
    arac = yerel_arac(sc_modul, sc_modul.DEFTER_ROTASYON_YOL)
    if not os.path.exists(arac):
        return False, "arac OKUNAMADI: " + arac
    with open(arac, encoding="utf-8") as f:
        agac = _ast.parse(f.read(), filename=arac)
    bulunan = {}
    for dugum in _ast.walk(agac):
        if not isinstance(dugum, _ast.Assign):
            continue
        for hedef in dugum.targets:
            if isinstance(hedef, _ast.Name) and hedef.id in ("_KANONIK_DEFTER",
                                                             "_KANONIK_ARSIV"):
                try:
                    bulunan[hedef.id] = _ast.literal_eval(dugum.value)
                except (ValueError, TypeError, SyntaxError):
                    return False, "OLCULEMEDI: %s sabit bir deger degil" % hedef.id
    if len(bulunan) != 2:
        return False, ("OLCULEMEDI: _KANONIK_DEFTER/_KANONIK_ARSIV bulunamadi "
                       "(bulunan=%s)" % sorted(bulunan))
    beklenen = sc_modul.SEKIL_ETIKETLERI["rotasyon-bakim"].konumlar
    gercek = (bulunan["_KANONIK_DEFTER"], bulunan["_KANONIK_ARSIV"])
    if gercek != tuple(beklenen):
        return False, "AYRISTI: arac=%s kaynak=%s" % (gercek, tuple(beklenen))
    return True, "arac varsayilanlari kaynagin konumlariyla BIREBIR ESIT"


c4_uyum, c4_ayrinti = c4_olc(SC)
kaydet("C4 KANONIK YOL UYUMU: aracin varsayilani kaynagin konumlariyla ESIT",
       c4_uyum, c4_ayrinti)

c2_satirlar, c2_hata = c2_olc()
c2_degisti = (c2_satirlar is not None and taban_care is not None
              and c2_satirlar != taban_care)
kaydet("C2 TUKETICI OKUYOR: kaynaktan bayrak dusunce CARE DEGISIR",
       c2_degisti,
       (c2_hata or ("taban=%r mutant=%r" % (taban_care[:1] if taban_care else None,
                                            c2_satirlar[:1] if c2_satirlar else None)))[:150])

# ---------------------------------------------------------------- MUTASYONLAR
# (ad, hedef_dosya, eski, yeni, care_beklenen, dusen_ad, komsu_beklenen)
MUTANTLAR = (
    ("MX1 LISTE BOZULUR: SEKILLER bosaltilir",
     SERBEST, "SEKIL_ETIKETLERI = {s.etiket: s for s in SEKILLER}\n",
     "SEKILLER = ()  # MX1 MUTANT: liste bozuldu\n"
     "SEKIL_ETIKETLERI = {s.etiket: s for s in SEKILLER}\n",
     "RED", "defter-rotasyon.py", "RED"),
    ("MX2 BIR OGE DUSER: rotasyon sekilleri",
     SERBEST,
     '    Sekil("rotasyon-bakim", DEFTER_ROTASYON_YOL,\n'
     "          konumlar=(DEFTER_ROTASYON_DEFTER, DEFTER_ROTASYON_ARSIV),\n"
     "          serbest=ROTASYON_BAKIM_BAYRAKLARI,\n"
     "          ornek=ROTASYON_BAKIM_BAYRAKLARI),\n",
     "    # MX2 MUTANT: rotasyon-bakim sekli dusuruldu\n",
     "RED", None, "GECTI"),
)

with tempfile.TemporaryDirectory(prefix="pruvo-k320-") as gecici:
    for ad, hedef, eski, yeni, care_beklenen, dusen_ad, komsu_beklenen in MUTANTLAR:
        alt = os.path.join(gecici, ad[:3])
        os.makedirs(alt)
        d, hata = evren_kur(alt, hedef, eski, yeni)
        if d is None:
            kaydet(ad, False, hata)
            continue
        kapi_m = os.path.join(d, os.path.basename(KAPI))
        hukum_m, _ = kapi_kos(kapi_m, CARE, d)
        hukum_komsu, _ = kapi_kos(kapi_m, CARE_KUTU, d)
        mutant_modul = modul_yukle(kapi_m, "kapi_mutant_" + ad[:3], d)
        metin_m = mutant_modul.GEREKCE_SONU
        ad_dustu = True if dusen_ad is None else (dusen_ad not in metin_m)
        gecti = (hukum_m == care_beklenen and hukum_komsu == komsu_beklenen and ad_dustu)
        kaydet(ad, gecti,
               "CARE=%s (bekl %s) · KOMSU(kutu)=%s (bekl %s) · ad_dustu=%s"
               % (hukum_m, care_beklenen, hukum_komsu, komsu_beklenen, ad_dustu))

    # MX3 — BAYRAK FORMU DEGISIR. Sekil bayragi GERCEKTEN tasiyorsa: eski form RED,
    # yeni bayrak metinde GORUNUR. Sadece ad turetilseydi bu mutant YASARDI.
    alt3 = os.path.join(gecici, "MX3")
    os.makedirs(alt3)
    d3, hata3 = evren_kur(alt3, SERBEST,
                          'ROTASYON_TAVAN_BAYRAGI = "--tavan-kaynaktan"\n',
                          'ROTASYON_TAVAN_BAYRAGI = "--zzsahte-bayrak"\n')
    if d3 is None:
        kaydet("MX3 BAYRAK FORMU DEGISIR", False, hata3)
    else:
        kapi3 = os.path.join(d3, os.path.basename(KAPI))
        h3, _ = kapi_kos(kapi3, CARE, d3)
        m3mod = modul_yukle(kapi3, "kapi_mutant_MX3", d3)
        yeni_gorunur = "--zzsahte-bayrak" in m3mod.GEREKCE_SONU
        eski_dustu = "--tavan-kaynaktan" not in m3mod.GEREKCE_SONU
        # C3'un OLDURULDUGU de OLCULUR: uydurma bayrak aracin CLI'sinda YOKTUR,
        # dolayisiyla C3 kolu bu mutant altinda KIRMIZI yanmalidir. Boylece C3
        # "her zaman yesil" bir sus payi degil, gercekten yuk tasiyan bir koldur.
        m3sc = modul_yukle(os.path.join(d3, os.path.basename(SERBEST)),
                           "sc_mutant_MX3", d3)
        m3_eksik, _ = c3_olc(m3sc)
        kaydet("MX3 BAYRAK FORMU DEGISIR: eski form RED + metin yeni bayragi + C3 KIRMIZI",
               h3 == "RED" and yeni_gorunur and eski_dustu and bool(m3_eksik),
               "CARE=%s · yeni_bayrak_metinde=%s · eski_bayrak_dustu=%s · C3_eksik=%s"
               % (h3, yeni_gorunur, eski_dustu, m3_eksik or "YOK"))

    # MX4 — TUKETICI LISTEYI OKUMAYI BIRAKIR. Kota kapisi CARE'i SABIT DIZGEYE
    # cevirir; kaynaktan bayrak dusse bile CARE DEGISMEZ -> C2 kolu KIRMIZI yanmali.
    KOTA_ESKI = '    print("!! CARE: " + _SC.cagri_ornegi("rotasyon-bakim"), file=sys.stderr)\n'
    KOTA_YENI = ('    print("!! CARE: " + %r, file=sys.stderr)  # MX4: sabit dizge\n'
                 % CARE)
    mx4_satirlar, mx4_hata = c2_olc(kota_mutasyonu=(KOTA_ESKI, KOTA_YENI))
    if mx4_satirlar is None:
        kaydet("MX4 TUKETICI OKUMAYI BIRAKIR: C2 kolu KIRMIZI yanar", False,
               str(mx4_hata))
    else:
        # C2'nin mantigi: taban ile FARKLI olmali. Sabit dizgede AYNI kalir -> C2 KIRMIZI.
        c2_mx4_gecerdi = (taban_care is not None and mx4_satirlar != taban_care)
        kaydet("MX4 TUKETICI OKUMAYI BIRAKIR: C2 kolu KIRMIZI yanar",
               not c2_mx4_gecerdi,
               "C2 mutant altinda %s (KIRMIZI olmali) · basilan=%r"
               % ("YESIL" if c2_mx4_gecerdi else "KIRMIZI", mx4_satirlar[:1]))

    # 🔴 MX5 — BEKCI SEKLI DUSER (K344'te main'in K343 bataryasindan PORT EDILDI).
    # main'in M6/M7 mutantlari `_BILINEN_BAYRAK_HARITASI` / `BEKCI_BAYRAKLARI`
    # ELLE yazilmis sozluklerini hedefliyordu; K344 merge'inde o sozlukler
    # SEKILLER'den TURETILIR oldu, yani eski capalar COKERDI ([[capa-cokmesi-...]]).
    # Eksen SILINMEDI, YENI KAYNAGA TASINDI: bekci sekli dusunce (a) bekci cagrisi
    # RED olmali, (b) bekci adi turetilmis RED metninden DUSMELI, (c) KOMSU eksen
    # (defter CARE) ETKILENMEMELI — yani mutant DAR olmali, toptan degil.
    altM5b = os.path.join(gecici, "MX5")
    os.makedirs(altM5b)
    ESKI_BEKCI = ('    Sekil("bekci-teslim-karari", CIP_BEKCI_YOL,\n'
                  '          zorunlu=("--teslim-karari",), serbest=("--kuru",),\n'
                  '          ornek=("--teslim-karari",), repo_disi=True),\n')
    dM5b, hM5b = evren_kur(altM5b, SERBEST, ESKI_BEKCI,
                           "    # MX5 MUTANT: bekci-teslim-karari sekli dusuruldu\n")
    if dM5b is None:
        kaydet("MX5 BEKCI SEKLI DUSER: bekci RED + ad duser + KOMSU defter GECER",
               False, hM5b)
    else:
        kapi5b = os.path.join(dM5b, os.path.basename(KAPI))
        h5b_bekci, _ = kapi_kos(kapi5b, BEKCI_KARAR, dM5b)
        h5b_defter, _ = kapi_kos(kapi5b, CARE, dM5b)
        m5bmod = modul_yukle(kapi5b, "kapi_mutant_MX5", dM5b)
        # --teslim-karari kolu dustu; --teslim-kaydet kolu DURUYOR, dolayisiyla
        # arac ADI metinde kalir. Dusmesi gereken sey BAYRAGIN KENDISIDIR.
        bayrak_dustu = "--teslim-karari" not in m5bmod.GEREKCE_SONU
        kaydet("MX5 BEKCI SEKLI DUSER: bekci RED + bayrak metinden duser + KOMSU defter GECER",
               h5b_bekci == "RED" and bayrak_dustu and h5b_defter == "GECTI",
               "BEKCI=%s (bekl RED) · bayrak_dustu=%s · KOMSU(defter)=%s (bekl GECTI)"
               % (h5b_bekci, bayrak_dustu, h5b_defter))

    # M3 — olcum ekseni gercekten turetilmis mi?
    UYDURMA = "zzolcum"
    ara3 = "    \"wc\", \"head\", \"tail\", \"sed\", \"awk\", \"sort\", \"stat\", \"file\",\n"
    altM3 = os.path.join(gecici, "M3")
    os.makedirs(altM3)
    dM3, hM3 = evren_kur(altM3, KAPI, ara3, ara3.rstrip("\n") + " \"" + UYDURMA + "\",\n")
    if dM3 is None:
        kaydet("M3 OLCUM: kumeye eklenen komut metinde gorunur", False, hM3)
    else:
        m3 = modul_yukle(os.path.join(dM3, os.path.basename(KAPI)), "kapi_mutant_3", dM3)
        kaydet("M3 OLCUM: kumeye eklenen komut metinde gorunur",
               UYDURMA in m3.GEREKCE_SONU,
               "'%s' metinde=%s" % (UYDURMA, UYDURMA in m3.GEREKCE_SONU))

    # M5 — TERS-YON MUTANTI: makinenin izin VERMEDIGI bir arac adi red metnine ELLE
    # eklenir. A1/A2 bunu GECIRIR (makine ⊆ metin bozulmaz); oldurmesi gereken kol A3'tur.
    SAHTE = "python3 tools/sahte-arac.py"
    ara5 = ("\"gh, ls, grep, jq, echo, cat; python YALNIZ şunlar: \" "
            "+ serbest_python_metni() +\n")
    altM5 = os.path.join(gecici, "M5")
    os.makedirs(altM5)
    dM5, hM5 = evren_kur(altM5, KAPI, ara5,
                         ara5.rstrip("\n") + " \" · '" + SAHTE + "'\" +\n")
    if dM5 is None:
        kaydet("M5 TERS YON: metne elle eklenen sahte arac A3'u KIRMIZI yakar", False, hM5)
    else:
        m5 = modul_yukle(os.path.join(dM5, os.path.basename(KAPI)), "kapi_mutant_5", dM5)
        m5_py, _, m5_ayrinti = ters_yon(m5)
        m5_a1 = all(a in m5.GEREKCE_SONU for a in bekleyen_py)
        kaydet("M5 TERS YON: metne elle eklenen sahte arac A3'u KIRMIZI yakar",
               (not m5_py) and m5_a1,
               "A3=%s (KIRMIZI olmali) · A1=%s (yesil kalmali) · %s"
               % ("KIRMIZI" if not m5_py else "yesil", "yesil" if m5_a1 else "KIRMIZI",
                  m5_ayrinti[:90]))

    # M4 — NEGATIF KONTROL: kaynak degismeden AYNI duzenekle kosulur.
    altM4 = os.path.join(gecici, "M4")
    os.makedirs(altM4)
    dM4, _ = evren_kur(altM4)
    kapi4 = os.path.join(dM4, os.path.basename(KAPI))
    hukum4, _ = kapi_kos(kapi4, CARE, dM4)
    hukum4b, _ = kapi_kos(kapi4, BEKCI_KARAR, dM4)
    m4 = modul_yukle(kapi4, "kapi_kontrol", dM4)
    m4_py, m4_olcum, _ = ters_yon(m4)
    m4_care, _ = kota_care(dM4)
    m4_temiz = (hukum4 == "GECTI" and hukum4b == "GECTI"
                and all(a in m4.GEREKCE_SONU for a in bekleyen_py)
                and m4_py and m4_olcum
                and m4_care is not None and CARE in m4_care)
    kaydet("M4 KONTROL: mutasyonsuz kopya HER kolda taban gibi davranir",
           m4_temiz, "CARE=%s BEKCI=%s A3=%s A4=%s KOTA_CARE=%s"
           % (hukum4, hukum4b, m4_py, m4_olcum, m4_care is not None and CARE in m4_care))

# ---------------------------------------------------------------- HUKUM
print("")
gecen = 0
for ad, gecti, ayrinti in sonuclar:
    damga = "OK  " if gecti else "KIRMIZI"
    gecen += 1 if gecti else 0
    print("%-7s %-62s | %s" % (damga, ad, ayrinti))

print("")
print("SERBEST_KUME_TEKKAYNAK: VAKA=%d GECEN=%d KIRMIZI=%d"
      % (len(sonuclar), gecen, len(sonuclar) - gecen))
sys.exit(0 if gecen == len(sonuclar) else 1)
