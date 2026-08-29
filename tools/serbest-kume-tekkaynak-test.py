"""K320 + K258/K168 + K344 — SERBEST CAGRI SEKILLERI GERCEKTEN TEK KAYNAK MI?

=== NEDEN VAR (uc katmanli olculmus ariza) ===
① 27 AGU 2026 (K320) — RED METNI IKINCI KOPYAYDI.
`mimar-icra-kapisi.py` red metninde "SERBEST / REDDEDILEN" kumelerini ELLE sayiyordu;
metin karari veren yapidan AYRISTI (TABAN DRIFT=9). Bedel yanlis kararla AYNIYDI: mimar
kendi kapisinin bastigi CAREYI okudu, metne inandi, "care oteki kapida olu" hukmunu verdi
ve defter UC KOSUM boyunca tavanin USTUNDE kaldi — oysa cagri O TARIHTE ZATEN GECIYORDU.

② 28 AGU 2026 (K258/K168) — K320 yalniz ARAC ADINI turetmisti; CAGRI SEKLI (bayraklar +
konumsal argumanlar) her tuketicide ELLE yaziliydi. Cozum SINIFSALDIR:
`tools/serbest_cagrilar.py` TEK KAYNAK; KARAR, RED METNI ve CARE satirlari oradan turer.

③ 🔴 28 AGU 2026 (K344) — IKI EKSIK, IKISI DE BU KOSUMDA KAPANDI:
  K344-A  MUTANTLAR YANLIS EKSENE CIVILIYDI. Bir mutant "kirmizi yakti" demek, HEDEF
          KOLU oldurdugunu KANITLAMAZ: yanindaki baska bir kol da kirmizi yanmis
          olabilir, ya da mutant kapiyi TOPTAN devirmis olabilir. Artik her oldurucu
          mutant IKI seyi birden kanitlar: (a) HEDEF KOL kirmizi yandi, (b) KOMSU KOL
          YESIL kaldi. Mutantlar kollara ADIYLA civilidir; kol mantigi IKINCI KEZ
          YAZILMAZ — mutant, tabanin kostugu KOL FONKSIYONUNUN TA KENDISINI kosar
          ([[ad-iki-rolde-mutanti-golgeler]] · [[sinif-adi-kol-adi-olarak-basilirsa-
          yanlis-alan-dogrulanir]]).
  K344-B  TERS YON HIC OLCULMUYORDU. C3 kolu yalniz `kaynak -> arac` yonunu olcer
          ("tablodaki her bayrak aracin CLI'sinda VAR MI"). `arac -> kaynak` yonu —
          ARACA EKLENMIS ama TABLOYA YAZILMAMIS bayrak — hicbir kolun menzilinde
          degildi. `kutu-arsivle.py --kapanislari-isle` tam bu bosluktan dustu ve ELLE
          kapatildi (`a5fc8f22`): ariza ONARILDI, OLCUM EKLENMEDI. Yeni C5/C6 kollari
          o ekseni olcer — ve kol icin cikarilan CLI ENVANTERI ayni sinifin IKINCI
          vakasini ortaya cikardi: `durum.py --ne-olculmedi` TABAN=RED iken `durum.py`
          o komutu okuyana kendi CARE'i olarak basiyordu. MB3 mutanti o vakayi GERI
          SARAR ve C5'in onu kirmizi yaktigini KANITLAR.

=== NE OLCER (kol adlari mutant tablosunda ADIYLA gecer) ===
  A1  python ekseni: red metni, karar yapisindaki HER araci ADIYLA aniyor mu?
  A2  olcum ekseni: red metni, OLCUM_KOMUTLARI'nin HER uyesini aniyor mu?
  A3  🔴 TERS YON (metin): red metninin python PARCASI turetilmise BIREBIR esit mi?
  A4  A3'un olcum ekseni karsiligi.
  B1  CAGRI YERI: kota kapisinin bastigi defter CARE'i gercekten GECIYOR mu?
  B2  CAGRI YERI: kume DISI bayrak (--tavan-sayi) hala RED mi? (kova gevsemedi)
  B3  RED sebebi okuyana TAM kumeyi gosteriyor mu?
  B4  CIP-DOGUM BEKCISI teslim cagrilari GECIYOR mu? (28 Agu tabanda IKISI DE RED)
  B5  K332 EKSENI KORUNDU MU: ana oturumda OLCUM komutu HALA RED mi?
  B6  KONUMSUZ KISA FORM geciyor mu (28 Agu tabanda RED)?
  B7  KUTU-ARSIVLE CARE'i geciyor mu? (MX2'nin KOMSU kolu — tek anahtar hepsini
      kapatmiyor; ayrica `--kapanislari-isle` regresyonunu tutar)
  B8  🔴 K344-B ile ACILAN KOL: `durum.py --ne-olculmedi` geciyor mu? (TABAN=RED)
  C1  TUKETICI #2 (defter-kota-kapisi.py): bastigi CARE satiri turetilmise esit mi?
  C2  TUKETICI GERCEKTEN OKUYOR MU: kaynaktan bayrak dusunce CARE DEGISIYOR mu?
  C3  KAYNAK -> ARAC: kaynaktaki her bayrak aracin CLI'sinda VAR mi?
  C4  KANONIK YOL: aracin varsayilani kaynagin konumlariyla ESIT mi?
  C5  🔴 ARAC -> KAYNAK (K344-B): aracin CLI'sindaki her bayrak hakkinda tablo BIR
      HUKUM tasiyor mu (serbest YA DA gerekceli DISARIDA)? Hukumsuz bayrak KIRMIZI.
  C6  🔴 DISARIDA BAYAT MI: gerekceyle disarida birakilmis her bayrak aracin CLI'sinda
      HALA VAR mi? (Silinmis bayragin gerekcesi, okuyani olmayan bir kola inandirir.)

=== MUTANTLAR — HER OLDURUCU MUTANT HEDEF + KOMSU ILE CIVILI ===
  MX1 SEKILLER bosaltilir      -> HEDEF B1 olur · KOMSU A2 YESIL (olcum ekseni saglam)
  MX2 rotasyon-bakim sekli duser-> HEDEF B1 olur · KOMSU B7 YESIL (kutu acik kaldi)
  MX3 bayrak formu degisir     -> HEDEF C3 olur · KOMSU B4 YESIL (bekci acik kaldi)
  MX4 tuketici sabit dizgeye doner-> HEDEF C2 olur · KOMSU C1 YESIL (dizge esit KALIR;
                                  C1 tek basina bu arizayi GOREMEZ — C2 gorur)
  MX5 bekci sekli duser        -> HEDEF B4 olur · KOMSU B1 YESIL (defter acik kaldi)
  M5  metne ELLE sahte arac    -> HEDEF A3 olur · KOMSU A1 YESIL (makine ⊆ metin saglam)
  M6  metne ELLE sahte olcum   -> HEDEF A4 olur · KOMSU A2 YESIL
  MB1 🔴 ARACA sahte bayrak (tabloya EKLENMEZ) -> HEDEF C5 olur · KOMSU C3 YESIL
  MB3 🔴 GERCEK VAKA GERI SARILIR: `durum.py --ne-olculmedi` TABLODAN duser ->
      HEDEF C5 olur · KOMSU C3/B7 YESIL. Toplayicinin `sys.argv` kolunu olcer.
  MB2 🔴 KONTROL: ayni bayrak TABLOYA DA eklenir -> C5 YESILE DONER (ters yon kolu
      "hep kirmizi" bir sus payi degil; iki yon de VAKAYLA)
  M3  KONTROL/PROB: olcum kumesine uydurma komut eklenir -> metinde GORUNUR, A2/A4
      YESIL kalir (turetimin yonu; oldurucu DEGIL — boyle yazili)
  M4  NEGATIF KONTROL: mutasyonsuz kopya HER KOLDA tabanin verdiktini birebir tekrar
      eder ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]])

Her mutant icin AYRICA "mutant kaynaga ULASTI MI" olculur (capa TEKIL ve kaynak
DEGISTI); ulasmayan mutant KIRMIZI sayilir, yesil DEGIL.

Hukum UC DEGERLIDIR: GECTI / RED / COKTU. Coken bir kopya "RED" diye okunursa mutant
tablosu yalan soyler ([[capa-cokmesi-arkasindaki-capalari-gizler]]).

KAPSAM SAYIYLA CIVILI: `VAKA_TABANI` altina dusen kosum KIRMIZIDIR. Oran (22/22) hicbir
zaman kapsam kaybini gostermez ([[batarya-kapsam-tabani-sayiyla-civilenir]]). Her kol
KENDI try'inda kosar; coken kol `False` olarak SAYIYA GIRER, toplam KUCULMEZ.

Gecici mutant kopyalari git-DISI tempdir'e yazilir (repo agacina iz birakilmaz).
"""
import ast as _ast
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

# 🔴 KAPSAM TABANI (oran DEGIL SAYI). Buyutmek serbest, KUCULTMEK mimar kararidir.
# 28 Agu K344 kapanisi: 22 -> 30 (18 kol + 12 mutant/kontrol).
VAKA_TABANI = 30


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

_SAYAC = [0]


def modul_yukle(yol, ad, dizin=None):
    _SAYAC[0] += 1
    ad = "%s_%d" % (ad, _SAYAC[0])
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
DURUM_NE_OLCULMEDI = SC.cagri_ornegi("durum") + " --ne-olculmedi"
KUME_DISI = CARE + " --tavan-sayi 130"
OLCUM_CAGRISI = "tail -5 /Users/okan/dev/pruvo/DEVAM.md"
TABAN_ARAC_ADLARI = sorted(SC.arac_adlari())

# C2 capasi — kaynaktan BIR bayrak dusuren mutasyon (kol govdesinde kullanilir).
# 🔴 29 Agu (K351): capa, kaynagin SATIR BICIMINE bagli bir DIZGE kopyasidir; ucuncu
# bayrak (`--onlem`) eklenince tuple iki satira yayildi ve capa 0 kez eslesti —
# mutant SESSIZ degil, "MUTANT ULASMADI" ile GURULTULU dustu (bekci calisti,
# [[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]). Capa kaynakla birlikte
# TAZELENIR; kaynagin bicimi degisirse burasi da degisir.
BAYRAK_DUSUR_ESKI = ("ROTASYON_BAKIM_BAYRAKLARI = (ROTASYON_TAVAN_BAYRAGI, "
                     "ROTASYON_INDIRME_BAYRAGI,\n"
                     "                             ROTASYON_ONLEM_BAYRAGI)\n")
BAYRAK_DUSUR_YENI = "ROTASYON_BAKIM_BAYRAKLARI = (ROTASYON_TAVAN_BAYRAGI,)\n"


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


def _capala(yol, eski, yeni):
    """Tek bir dosyada TEKIL capayi degistirir. Doner: None ya da hata METNI.

    ULASIM iki yonlu olculur: capa TEKIL olmali VE kaynak DEGISMIS olmali."""
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    adet = govde.count(eski)
    if adet != 1:
        return ("MUTANT ULASMADI — capa %s icinde %d kez bulundu (1 bekleniyordu)"
                % (os.path.basename(yol), adet))
    mutant = govde.replace(eski, yeni, 1)
    if mutant == govde:
        return "MUTANT ULASMADI — kaynak DEGISMEDI (%s)" % os.path.basename(yol)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(mutant)
    return None


def evren_kur(tmp, mutasyonlar=(), kaynak_dizin=None):
    """Mutant evreni: YAN_DOSYALAR kopyalanir, istenen capalar degistirilir.

    Doner: (dizin, None) ya da (None, 'MUTANT ULASMADI — ...')."""
    kaynak_dizin = kaynak_dizin or ARACLAR
    for kaynak in YAN_DOSYALAR:
        ad = os.path.basename(kaynak)
        shutil.copy2(os.path.join(kaynak_dizin, ad), os.path.join(tmp, ad))
    for hedef, eski, yeni in mutasyonlar:
        hata = _capala(os.path.join(tmp, os.path.basename(hedef)), eski, yeni)
        if hata is not None:
            return None, hata
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
    """(py_uyumlu, olcum_uyumlu, ayrinti) — A3/A4'un ORTAK govdesi."""
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


# 🔴 KANONIK YOL -> BU AGACIN YOLU. Kaynaktaki arac yollari ANA CHECKOUT'a capalidir
# (kapinin karari oyle olmali). Ama C3/C4/C5/C6 KAYNAK-ARAC TUTARLILIGINI olcer ve o
# olcum BU AGACIN gonderdigi dosyalar uzerinde yapilmalidir; ana checkout'u okumak,
# dalda yesillenemeyen (yalniz merge'den SONRA yesillenen) bir kol uretirdi — yani
# nobetci dalda ISE YARAMAZDI. Repo DISI araclar (bekci) tek nushadir, aynen okunur.
AGAC_KOKU = os.path.dirname(ARACLAR)


def yerel_arac(sc_modul, yol):
    if yol.startswith(sc_modul.REPO_ONEKI):
        return os.path.join(AGAC_KOKU, yol[len(sc_modul.REPO_ONEKI):])
    return yol


# ================================================================= EVREN + KOLLAR
class Evren(object):
    """Bir olcum evreni: kapi/kaynak/tuketici kopyalarinin durdugu dizin.

    `arac_ustveri`, KANONIK arac yolunu BU EVRENDE okunacak dosyaya esler — ters yon
    mutantlari (MB1/MB2) araci mutasyona ugratirken bunu kullanir. Ustveri BOSSA arac
    bu agactan okunur."""

    def __init__(self, dizin, arac_ustveri=None, etiket="taban"):
        self.dizin = dizin
        self.arac_ustveri = dict(arac_ustveri or {})
        self.etiket = etiket
        self._onbellek = {}

    @property
    def kapi_yolu(self):
        return os.path.join(self.dizin, os.path.basename(KAPI))

    def kapi(self):
        if "kapi" not in self._onbellek:
            self._onbellek["kapi"] = modul_yukle(self.kapi_yolu, "kapi", self.dizin)
        return self._onbellek["kapi"]

    def sc(self):
        if "sc" not in self._onbellek:
            self._onbellek["sc"] = modul_yukle(
                os.path.join(self.dizin, os.path.basename(SERBEST)), "sc", self.dizin)
        return self._onbellek["sc"]

    def arac(self, kanonik_yol):
        if kanonik_yol in self.arac_ustveri:
            return self.arac_ustveri[kanonik_yol]
        return yerel_arac(self.sc(), kanonik_yol)


KOLLAR = {}
KOL_SIRASI = []


def kol(ad, baslik):
    """Bir olcum kolunu ADIYLA kaydeder. Mutantlar bu ADI hedef/komsu olarak anar —
    kol mantigi IKINCI KEZ YAZILMAZ ([[kapi-red-metni-ikinci-kopyadir]] sinifi)."""
    def sarmala(fn):
        KOLLAR[ad] = (baslik, fn)
        KOL_SIRASI.append(ad)
        return fn
    return sarmala


def kol_kos(ad, ev):
    """Bir kolu kosar; COKERSE False + 'COKTU: ...' doner (kol SAYIDAN DUSMEZ)."""
    baslik, fn = KOLLAR[ad]
    try:
        return fn(ev)
    except Exception as e:                                     # kol kapi degil, olcum
        return False, "COKTU: %s: %s" % (type(e).__name__, str(e)[:110])


# ---------------------------------------------------------------- A) TURETILMISLIK
@kol("A1", "python ekseni: makinedeki HER arac red metninde")
def _a1(ev):
    bekleyen = sorted(ev.sc().arac_adlari())
    metin = ev.kapi().GEREKCE_SONU
    eksik = [a for a in bekleyen if a not in metin]
    return not eksik, "makine=%d metinde_eksik=%s" % (len(bekleyen), eksik or "YOK")


@kol("A2", "olcum ekseni: OLCUM_KOMUTLARI'nin HER uyesi red metninde")
def _a2(ev):
    K = ev.kapi()
    eksik = sorted(k for k in K.OLCUM_KOMUTLARI if k not in K.GEREKCE_SONU)
    return not eksik, "makine=%d metinde_eksik=%s" % (len(K.OLCUM_KOMUTLARI),
                                                      eksik or "YOK")


@kol("A3", "TERS YON: red metninin python parcasi TURETILMISE BIREBIR esit")
def _a3(ev):
    py, _olcum, ayrinti = ters_yon(ev.kapi())
    return py, ayrinti


@kol("A4", "TERS YON: red metninin olcum parcasi TURETILMISE BIREBIR esit")
def _a4(ev):
    _py, olcum, ayrinti = ters_yon(ev.kapi())
    return olcum, ayrinti


# ---------------------------------------------------------------- B) CAGRI YERI
@kol("B1", "CAGRI YERI: kota kapisinin bastigi defter CARE'i gecer")
def _b1(ev):
    hukum, _ = kapi_kos(ev.kapi_yolu, CARE, ev.dizin)
    return hukum == "GECTI", "hukum=" + hukum


@kol("B2", "CAGRI YERI: kume DISI bayrak (--tavan-sayi) RED kalir")
def _b2(ev):
    hukum, _ = kapi_kos(ev.kapi_yolu, KUME_DISI, ev.dizin)
    return hukum == "RED", "hukum=" + hukum


@kol("B3", "RED sebebi okuyana TAM kumeyi gosterir (tail reddinde)")
def _b3(ev):
    hukum, sebep = kapi_kos(ev.kapi_yolu, OLCUM_CAGRISI, ev.dizin)
    tam = all(a in sebep for a in TABAN_ARAC_ADLARI)
    return hukum == "RED" and tam, "hukum=%s tam_kume=%s" % (hukum, tam)


@kol("B4", "CIP-DOGUM BEKCISI teslim cagrilari GECER (taban: ikisi de RED)")
def _b4(ev):
    h1, _ = kapi_kos(ev.kapi_yolu, BEKCI_KARAR, ev.dizin)
    h2, _ = kapi_kos(ev.kapi_yolu, BEKCI_KAYDET, ev.dizin)
    return h1 == "GECTI" and h2 == "GECTI", "--teslim-karari=%s --teslim-kaydet=%s" % (h1, h2)


@kol("B5", "K332 EKSENI KORUNDU: olcum/genel-python/satir-ici HALA RED")
def _b5(ev):
    h1, _ = kapi_kos(ev.kapi_yolu, "du -sh /Users/okan/dev/pruvo", ev.dizin)
    h2, _ = kapi_kos(ev.kapi_yolu, "python3 /Users/okan/dev/pruvo/tools/build.py", ev.dizin)
    h3, _ = kapi_kos(ev.kapi_yolu, "python3 -c 'print(1)'", ev.dizin)
    return (h1 == "RED" and h2 == "RED" and h3 == "RED",
            "du=%s genel_py=%s satir_ici=%s" % (h1, h2, h3))


@kol("B6", "KONUMSUZ KISA FORM gecer (taban: RED)")
def _b6(ev):
    hukum, _ = kapi_kos(ev.kapi_yolu, KISA_FORM, ev.dizin)
    return hukum == "GECTI", "hukum=" + hukum


@kol("B7", "KUTU-ARSIVLE CARE'i gecer (--kapanislari-isle dahil)")
def _b7(ev):
    hukum, _ = kapi_kos(ev.kapi_yolu, CARE_KUTU, ev.dizin)
    return hukum == "GECTI", "hukum=%s · cagri=%s" % (hukum, CARE_KUTU.split("/")[-1])


@kol("B8", "K344-B ILE ACILAN KOL: durum.py --ne-olculmedi gecer (taban: RED)")
def _b8(ev):
    hukum, _ = kapi_kos(ev.kapi_yolu, DURUM_NE_OLCULMEDI, ev.dizin)
    return hukum == "GECTI", "hukum=" + hukum


# ---------------------------------------------------------------- C) TUKETICI/ARAC
@kol("C1", "TUKETICI #2 (kota kapisi) CARE satiri TURETILMISE BIREBIR esit")
def _c1(ev):
    satirlar, hata = kota_care(ev.dizin)
    if satirlar is None:
        return False, "OLCULEMEDI: " + str(hata)
    return CARE in satirlar, "basilan=%r" % (satirlar[:1],)


@kol("C2", "TUKETICI OKUYOR: kaynaktan bayrak dusunce CARE DEGISIR")
def _c2(ev):
    taban, hata = kota_care(ev.dizin)
    if taban is None:
        return False, "OLCULEMEDI (taban): " + str(hata)
    with tempfile.TemporaryDirectory(prefix="pruvo-tk-c2-") as t:
        d, h = evren_kur(t, ((SERBEST, BAYRAK_DUSUR_ESKI, BAYRAK_DUSUR_YENI),), ev.dizin)
        if d is None:
            return False, h
        mutant, hata2 = kota_care(d)
    if mutant is None:
        return False, "OLCULEMEDI (bayraksiz): " + str(hata2)
    return mutant != taban, "taban=%r bayraksiz=%r" % (taban[:1], mutant[:1])


# 🔴 C3 — KAYNAK ile ARACIN KENDISI AYRISMASIN. Kaynak "bu bayrak serbest" der; araci
# o bayragi GERCEKTEN taniyor mu? Ikisi ayri yerlerde yasadigi icin sessizce
# ayrisabilirler: kapi gecirir, arac "unrecognized arguments" ile COKER — yani kapi
# CALISMAYAN bir sey vaat eder.
def c3_olc(ev):
    sc = ev.sc()
    eksik, okunamayan = [], []
    for s in sc.SEKILLER:
        arac = ev.arac(s.arac)
        if not os.path.exists(arac):
            okunamayan.append(sc._kisa(s.arac))
            continue
        with open(arac, encoding="utf-8") as f:
            govde = f.read()
        for b in sorted(s.tum_bayraklar):
            if ('"' + b + '"') not in govde and ("'" + b + "'") not in govde:
                eksik.append("%s::%s" % (s.etiket, b))
    return eksik, okunamayan


@kol("C3", "KAYNAK -> ARAC: kaynaktaki HER bayrak aracin CLI'sinda VAR")
def _c3(ev):
    eksik, okunamayan = c3_olc(ev)
    return (not eksik and not okunamayan,
            "eksik=%s · okunamayan_arac=%s" % (eksik or "YOK", okunamayan or "YOK"))


# 🔴 C4 — KANONIK KONUMSAL YOLLAR: KAYNAK ile ARACIN VARSAYILANI BIREBIR ESIT MI?
# `defter-rotasyon.py` KISA FORMU (konumsuz) desteklemek icin kanonik DEVAM.md /
# DEVAM-ARSIV.md yollarini KENDI sabitlerinde tutar. Bunlari calisma aninda bu
# kaynaktan OKUTMAK denendi ve GERI ALINDI: aracin govdesini gecici dizine kopyalayan
# YEDI harness birden kirildi. Bagimlilik TERSE cevrildi; ayrisma riski BURADA olculur.
# Karsilastirma DIZGE degil, AYRISTIRILMIS SABIT uzerinden yapilir; sabit bulunamazsa
# hukum OLCULEMEDI = KIRMIZI (fail-closed).
@kol("C4", "KANONIK YOL UYUMU: aracin varsayilani kaynagin konumlariyla ESIT")
def _c4(ev):
    sc = ev.sc()
    arac = ev.arac(sc.DEFTER_ROTASYON_YOL)
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
    beklenen = sc.SEKIL_ETIKETLERI["rotasyon-bakim"].konumlar
    gercek = (bulunan["_KANONIK_DEFTER"], bulunan["_KANONIK_ARSIV"])
    if gercek != tuple(beklenen):
        return False, "AYRISTI: arac=%s kaynak=%s" % (gercek, tuple(beklenen))
    return True, "arac varsayilanlari kaynagin konumlariyla BIREBIR ESIT"


# 🔴🔴 C5/C6 — TERS YON (K344-B): ARAC -> KAYNAK.
# Aracin CLI'sinda TANIMLI her bayrak hakkinda tablo BIR HUKUM tasimali: ya bir
# SEKILDE serbesttir, ya `DISARIDA`da gerekcesiyle disaridadir. Ucuncu hal
# ("tablo bu bayragi HIC DUYMAMIS") KIRMIZIDIR — `--kapanislari-isle` tam o haldeydi.
# CLI IKI bicimde yazilir ve IKISI DE okunur: argparse `add_argument("--x", ...)` ve
# elle `"--x" in sys.argv` (durum.py boyle). Sabit olmayan add_argument argumani
# OLCULEMEDI'dir ve KIRMIZI sayilir ([[prob-kendi-baglamini-olcer]] fail-closed).
def _argv_mi(dugum):
    if isinstance(dugum, _ast.Subscript):
        dugum = dugum.value
    return (isinstance(dugum, _ast.Attribute) and dugum.attr == "argv"
            and isinstance(dugum.value, _ast.Name) and dugum.value.id == "sys")


def arac_cli_bayraklari(yol):
    """(bayrak_kumesi, olculemedi_listesi) — aracin CLI'sinda TANIMLI bayraklar."""
    with open(yol, encoding="utf-8") as f:
        agac = _ast.parse(f.read(), filename=yol)
    bayraklar, olculemedi = set(), []
    for d in _ast.walk(agac):
        if (isinstance(d, _ast.Call) and isinstance(d.func, _ast.Attribute)
                and d.func.attr == "add_argument"):
            for a in d.args:
                if isinstance(a, _ast.Constant) and isinstance(a.value, str):
                    if a.value.startswith("-"):
                        bayraklar.add(a.value)
                else:
                    olculemedi.append("add_argument@%d sabit dizge DEGIL" % d.lineno)
        elif isinstance(d, _ast.Compare) and any(_argv_mi(c) for c in d.comparators):
            for t in [d.left] + list(d.comparators):
                if (isinstance(t, _ast.Constant) and isinstance(t.value, str)
                        and t.value.startswith("-")):
                    bayraklar.add(t.value)
    return bayraklar, olculemedi


def _arac_cli_tara(ev):
    """(arac -> cli_kumesi, okunamayan, olculemedi) — C5 ve C6'nin ORTAK govdesi."""
    sc = ev.sc()
    harita, okunamayan, olculemedi = {}, [], []
    for arac in sc.araclar():
        yol = ev.arac(arac)
        if not os.path.exists(yol):
            okunamayan.append(sc._kisa(arac))
            continue
        try:
            cli, sorun = arac_cli_bayraklari(yol)
        except SyntaxError:
            olculemedi.append("%s: AST cozulemedi" % sc._kisa(arac))
            continue
        harita[arac] = cli
        olculemedi.extend("%s: %s" % (sc._kisa(arac), s) for s in sorun)
    return harita, okunamayan, olculemedi


@kol("C5", "ARAC -> KAYNAK: aracin HER CLI bayragi hakkinda tablo HUKUM tasir")
def _c5(ev):
    sc = ev.sc()
    harita, okunamayan, olculemedi = _arac_cli_tara(ev)
    hukumsuz = []
    for arac, cli in harita.items():
        for b in sorted(cli - sc.hukumlu_bayraklar(arac)):
            hukumsuz.append("%s::%s" % (sc._kisa(arac), b))
    return (not hukumsuz and not okunamayan and not olculemedi,
            "tabloda_HUKUMSUZ=%s · okunamayan=%s · olculemedi=%s"
            % (sorted(hukumsuz) or "YOK", okunamayan or "YOK", olculemedi or "YOK"))


@kol("C6", "DISARIDA BAYAT DEGIL: her gerekceli bayrak aracin CLI'sinda HALA VAR")
def _c6(ev):
    sc = ev.sc()
    harita, okunamayan, olculemedi = _arac_cli_tara(ev)
    bayat = []
    for arac, cli in harita.items():
        for b in sorted(set(sc.disarida_bayraklar(arac)) - cli):
            bayat.append("%s::%s" % (sc._kisa(arac), b))
    return (not bayat and not okunamayan and not olculemedi,
            "BAYAT_gerekce=%s · okunamayan=%s · olculemedi=%s"
            % (sorted(bayat) or "YOK", okunamayan or "YOK", olculemedi or "YOK"))


# ================================================================= TABAN KOSUMU
TABAN_EVREN = Evren(ARACLAR)
TABAN_HUKUMLERI = {}
for _ad in KOL_SIRASI:
    _baslik, _fn = KOLLAR[_ad]
    _gecti, _ayrinti = kol_kos(_ad, TABAN_EVREN)
    TABAN_HUKUMLERI[_ad] = _gecti
    kaydet("%s %s" % (_ad, _baslik), _gecti, _ayrinti)


# ================================================================= MUTASYONLAR
class Mutant(object):
    """Bir mutant: capalar + HEDEF KOL + KOMSU KOLLAR.

    🔴 K344-A: "kirmizi geldi" KANIT DEGILDIR. Bir mutant, hedef kolunu oldurdugunu
    ancak KOMSU KOL YESIL KALARAK kanitlar; aksi halde mutant kapiyi toptan devirmis
    de olabilir ve hangi kolun yuk tasidigi OLCUSUZ kalir
    ([[ad-iki-rolde-mutanti-golgeler]])."""

    __slots__ = ("ad", "baslik", "mutasyonlar", "arac_mutasyonlari", "hedef",
                 "komsular", "ek", "taban_gibi")

    def __init__(self, ad, baslik, mutasyonlar=(), arac_mutasyonlari=(), hedef=None,
                 komsular=(), ek=None, taban_gibi=False):
        self.ad = ad
        self.baslik = baslik
        self.mutasyonlar = tuple(mutasyonlar)
        self.arac_mutasyonlari = tuple(arac_mutasyonlari)
        self.hedef = hedef
        self.komsular = tuple(komsular)
        self.ek = ek
        self.taban_gibi = taban_gibi


# --- capalar ------------------------------------------------------------------
MX1_ESKI = "SEKIL_ETIKETLERI = {s.etiket: s for s in SEKILLER}\n"
MX1_YENI = ("SEKILLER = ()  # MX1 MUTANT: liste bozuldu\n"
            "SEKIL_ETIKETLERI = {s.etiket: s for s in SEKILLER}\n")

MX2_ESKI = ('    Sekil("rotasyon-bakim", DEFTER_ROTASYON_YOL,\n'
            "          konumlar=(DEFTER_ROTASYON_DEFTER, DEFTER_ROTASYON_ARSIV),\n"
            "          serbest=ROTASYON_BAKIM_BAYRAKLARI,\n"
            "          ornek=ROTASYON_BAKIM_BAYRAKLARI),\n")
MX2_YENI = "    # MX2 MUTANT: rotasyon-bakim sekli dusuruldu\n"

MX3_ESKI = 'ROTASYON_TAVAN_BAYRAGI = "--tavan-kaynaktan"\n'
MX3_YENI = 'ROTASYON_TAVAN_BAYRAGI = "--zzsahte-bayrak"\n'

MX4_ESKI = '    print("!! CARE: " + _SC.cagri_ornegi("rotasyon-bakim"), file=sys.stderr)\n'
MX4_YENI = ('    print("!! CARE: " + %r, file=sys.stderr)  # MX4: sabit dizge\n' % CARE)

MX5_ESKI = ('    Sekil("bekci-teslim-karari", CIP_BEKCI_YOL,\n'
            '          zorunlu=("--teslim-karari",), serbest=("--kuru",),\n'
            '          ornek=("--teslim-karari",), repo_disi=True),\n')
MX5_YENI = "    # MX5 MUTANT: bekci-teslim-karari sekli dusuruldu\n"

SAHTE_ARAC = "python3 tools/sahte-arac.py"
M5_ESKI = ("\"gh, ls, grep, jq, echo, cat; python YALNIZ şunlar: \" "
           "+ serbest_python_metni() +\n")
M5_YENI = M5_ESKI.rstrip("\n") + " \" · '" + SAHTE_ARAC + "'\" +\n"

SAHTE_OLCUM = "zzsahteolcum"
M6_ESKI = 'olcum_komut_metni() + ", node --check'
M6_YENI = 'olcum_komut_metni() + "/' + SAHTE_OLCUM + '" + ", node --check'

UYDURMA_OLCUM = "zzolcum"
M3_ESKI = "    \"wc\", \"head\", \"tail\", \"sed\", \"awk\", \"sort\", \"stat\", \"file\",\n"
M3_YENI = M3_ESKI.rstrip("\n") + " \"" + UYDURMA_OLCUM + "\",\n"

# --- ters yon capalari (K344-B): ARAC mutasyonu -------------------------------
SAHTE_KOL = "--zzsahte-kol"
MB_ARAC_ESKI = '    ap.add_argument("--kuru", action="store_true",\n'
MB_ARAC_YENI = ('    ap.add_argument("%s", action="store_true")  # MB MUTANT\n'
                % SAHTE_KOL) + MB_ARAC_ESKI
MB2_TABLO_ESKI = '        serbest=("--kuru", "--kapanislari-isle")),\n'
MB2_TABLO_YENI = ('        serbest=("--kuru", "--kapanislari-isle", "%s")),\n' % SAHTE_KOL)

# 🔴 MB3 — GERCEK VAKAYI GERI SARAR (sentetik degil). `durum.py --ne-olculmedi`
# tablodan DUSURULUR: arac o bayragi HALA taniyor, tablo artik DUYMUYOR — yani
# 28 Agu sabahindaki TABAN HALI. C5 bunu KIRMIZI yakmalidir. Bu mutant ayrica
# CLI TOPLAYICISININ `sys.argv` KOLUNU olcer: `durum.py` argparse KULLANMAZ,
# bayragi `"--ne-olculmedi" in sys.argv` ile okur. Toplayici yalniz add_argument
# okusaydi C5 bu vakada SESSIZ kalirdi ve ters yon kolu YARIM olurdu — MB1 (argparse
# kolu) tek basina bunu ayirt EDEMEZDI ([[ad-iki-rolde-mutanti-golgeler]]).
MB3_ESKI = '    Sekil("durum", DURUM_YOL, serbest=("--ne-olculmedi",)),\n'
MB3_YENI = '    Sekil("durum", DURUM_YOL),  # MB3 MUTANT: bayrak tablodan dustu\n'


# --- ek kontroller (metin ekseni) ---------------------------------------------
def _ek_mx1(ev):
    metin = ev.kapi().GEREKCE_SONU
    dustu = "defter-rotasyon.py" not in metin
    return dustu, "arac_adi_metinden_dustu=%s" % dustu


def _ek_mx3(ev):
    metin = ev.kapi().GEREKCE_SONU
    yeni = "--zzsahte-bayrak" in metin
    eski = "--tavan-kaynaktan" not in metin
    return yeni and eski, "yeni_bayrak_metinde=%s eski_bayrak_dustu=%s" % (yeni, eski)


def _ek_mx5(ev):
    # --teslim-karari kolu dustu; --teslim-kaydet kolu DURUYOR, dolayisiyla arac ADI
    # metinde KALIR. Dusmesi gereken sey BAYRAGIN KENDISIDIR.
    dustu = "--teslim-karari" not in ev.kapi().GEREKCE_SONU
    return dustu, "bayrak_metinden_dustu=%s" % dustu


def _ek_m3(ev):
    var = UYDURMA_OLCUM in ev.kapi().GEREKCE_SONU
    return var, "'%s' metinde=%s (turetim kaynaktan METNE akiyor)" % (UYDURMA_OLCUM, var)


def _ek_mb1(ev):
    """Mutantin ARACA ULASTIGI ayrica olculur: sahte bayrak CLI taramasinda GORUNMELI."""
    harita, _okunamayan, _olculemedi = _arac_cli_tara(ev)
    sc = ev.sc()
    goruldu = any(SAHTE_KOL in cli for cli in harita.values())
    hukumsuz = any(SAHTE_KOL in (cli - sc.hukumlu_bayraklar(a))
                   for a, cli in harita.items())
    return goruldu and hukumsuz, "sahte_bayrak_CLIde=%s tabloda_hukumsuz=%s" % (
        goruldu, hukumsuz)


def _ek_mb3(ev):
    """OLEN KOLUN SEBEBI ADIYLA olculur: hukumsuz bayrak TAM OLARAK durum.py'nin
    `sys.argv` kolundan gelen bayrak olmali — baska bir aracin bayragi degil."""
    sc = ev.sc()
    harita, _okunamayan, _olculemedi = _arac_cli_tara(ev)
    hukumsuz = set()
    for arac, cli in harita.items():
        hukumsuz |= {"%s::%s" % (sc._kisa(arac), b)
                     for b in (cli - sc.hukumlu_bayraklar(arac))}
    beklenen = {"tools/durum.py::--ne-olculmedi"}
    return hukumsuz == beklenen, "hukumsuz=%s (beklenen=%s)" % (sorted(hukumsuz),
                                                               sorted(beklenen))


def _ek_mb2(ev):
    """Ayni bayrak TABLOYA da girdi: artik HUKUMLU (serbest) olmali."""
    sc = ev.sc()
    hukumlu = SAHTE_KOL in sc.serbest_bayraklar(sc.KUTU_ARSIVLE_YOL)
    return hukumlu, "sahte_bayrak_tabloda_SERBEST=%s" % hukumlu


MUTANTLAR = (
    Mutant("MX1", "SEKILLER bosaltilir",
           mutasyonlar=((SERBEST, MX1_ESKI, MX1_YENI),),
           hedef="B1", komsular=("A2",), ek=_ek_mx1),
    Mutant("MX2", "rotasyon-bakim sekli duser",
           mutasyonlar=((SERBEST, MX2_ESKI, MX2_YENI),),
           hedef="B1", komsular=("B7", "B8")),
    Mutant("MX3", "bayrak formu degisir",
           mutasyonlar=((SERBEST, MX3_ESKI, MX3_YENI),),
           hedef="C3", komsular=("B4",), ek=_ek_mx3),
    Mutant("MX4", "tuketici (kota kapisi) SABIT DIZGEYE doner",
           mutasyonlar=((KOTA, MX4_ESKI, MX4_YENI),),
           hedef="C2", komsular=("C1",)),
    Mutant("MX5", "bekci-teslim-karari sekli duser",
           mutasyonlar=((SERBEST, MX5_ESKI, MX5_YENI),),
           hedef="B4", komsular=("B1",), ek=_ek_mx5),
    Mutant("M5 ", "metne ELLE sahte ARAC eklenir",
           mutasyonlar=((KAPI, M5_ESKI, M5_YENI),),
           hedef="A3", komsular=("A1",)),
    Mutant("M6 ", "metne ELLE sahte OLCUM komutu eklenir",
           mutasyonlar=((KAPI, M6_ESKI, M6_YENI),),
           hedef="A4", komsular=("A2",)),
    Mutant("MB1", "ARACA sahte bayrak eklenir, TABLOYA eklenmez (ters yon)",
           arac_mutasyonlari=((SC.KUTU_ARSIVLE_YOL, MB_ARAC_ESKI, MB_ARAC_YENI),),
           hedef="C5", komsular=("C3",), ek=_ek_mb1),
    Mutant("MB3", "GERCEK VAKA: durum.py --ne-olculmedi TABLODAN duser (ters yon)",
           mutasyonlar=((SERBEST, MB3_ESKI, MB3_YENI),),
           hedef="C5", komsular=("C3", "B7"), ek=_ek_mb3),
    Mutant("MB2", "KONTROL: ayni bayrak TABLOYA da eklenir -> C5 YESILE doner",
           mutasyonlar=((SERBEST, MB2_TABLO_ESKI, MB2_TABLO_YENI),),
           arac_mutasyonlari=((SC.KUTU_ARSIVLE_YOL, MB_ARAC_ESKI, MB_ARAC_YENI),),
           hedef=None, komsular=("C5", "C3"), ek=_ek_mb2),
    Mutant("M3 ", "PROB: olcum kumesine uydurma komut -> metinde GORUNUR",
           mutasyonlar=((KAPI, M3_ESKI, M3_YENI),),
           hedef=None, komsular=("A2", "A4"), ek=_ek_m3),
    Mutant("M4 ", "NEGATIF KONTROL: mutasyonsuz kopya HER kolda taban gibi",
           taban_gibi=True),
)


def mutant_kos(m, gecici):
    alt = os.path.join(gecici, m.ad.strip())
    os.makedirs(alt)
    d, hata = evren_kur(alt, m.mutasyonlar)
    if d is None:
        return False, hata
    ustveri = {}
    for kanonik, eski, yeni in m.arac_mutasyonlari:
        kaynak = yerel_arac(SC, kanonik)
        if not os.path.exists(kaynak):
            return False, "MUTANT ULASMADI — arac OKUNAMADI: " + kaynak
        varis = os.path.join(alt, "arac-" + os.path.basename(kanonik))
        shutil.copy2(kaynak, varis)
        capa_hatasi = _capala(varis, eski, yeni)
        if capa_hatasi is not None:
            return False, capa_hatasi
        ustveri[kanonik] = varis
    ev = Evren(d, ustveri, etiket=m.ad.strip())

    parcalar, gecti = [], True
    if m.taban_gibi:
        sapan = []
        for ad in KOL_SIRASI:
            h, _ayrinti = kol_kos(ad, ev)
            if h != TABAN_HUKUMLERI[ad]:
                sapan.append("%s(%s!=%s)" % (ad, h, TABAN_HUKUMLERI[ad]))
        gecti = not sapan
        parcalar.append("KOL=%d sapan=%s" % (len(KOL_SIRASI), sapan or "YOK"))
    else:
        if m.hedef is not None:
            h, ayrinti = kol_kos(m.hedef, ev)
            gecti = gecti and (h is False)
            parcalar.append("HEDEF %s=%s (bekl KIRMIZI) [%s]"
                            % (m.hedef, "YESIL" if h else "KIRMIZI", ayrinti[:60]))
        for ad in m.komsular:
            h, ayrinti = kol_kos(ad, ev)
            gecti = gecti and (h is True)
            parcalar.append("KOMSU %s=%s (bekl YESIL)" % (ad, "YESIL" if h else "KIRMIZI"))
    if m.ek is not None:
        ek_gecti, ek_ayrinti = m.ek(ev)
        gecti = gecti and ek_gecti
        parcalar.append(ek_ayrinti)
    return gecti, " · ".join(parcalar)


with tempfile.TemporaryDirectory(prefix="pruvo-k344-") as _gecici:
    for _m in MUTANTLAR:
        try:
            _gecti, _ayrinti = mutant_kos(_m, _gecici)
        except Exception as e:                    # mutant kapi degil: sayidan DUSMEZ
            _gecti, _ayrinti = False, "COKTU: %s: %s" % (type(e).__name__, str(e)[:110])
        kaydet("%s %s" % (_m.ad, _m.baslik), _gecti, _ayrinti)


# ---------------------------------------------------------------- HUKUM
print("")
gecen = 0
for ad, gecti, ayrinti in sonuclar:
    damga = "OK  " if gecti else "KIRMIZI"
    gecen += 1 if gecti else 0
    print("%-7s %-62s | %s" % (damga, ad, ayrinti))

kapsam_hatasi = len(sonuclar) < VAKA_TABANI
print("")
if kapsam_hatasi:
    print("🔴 KAPSAM KAYBI: VAKA=%d < TABAN=%d — koşmayan kol paydadan da duser, "
          "oran yine 'hepsi gecti' basar." % (len(sonuclar), VAKA_TABANI))
print("SERBEST_KUME_TEKKAYNAK: VAKA=%d (taban %d) GECEN=%d KIRMIZI=%d"
      % (len(sonuclar), VAKA_TABANI, gecen, len(sonuclar) - gecen))
sys.exit(0 if (gecen == len(sonuclar) and not kapsam_hatasi) else 1)
