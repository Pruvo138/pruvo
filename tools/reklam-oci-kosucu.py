#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCI hattinin ZAMANLANMIS kosucusu — `.github/workflows/reklam-oci.yml` BUNU cagirir.

══════════════════════════════════════════════════════════════════════════════
NEDEN VAR — OLCULEN SESSIZLIK (22 Eyl 2026)
══════════════════════════════════════════════════════════════════════════════
`tools/reklam-oci-yukleyici.py` 22 Eyl'de main'e indi ve YAYINDA. Kapisi
(`tools/reklam-oci-kapisi.py`) `deploy.yml::serit-a3`te kosuyor — yani KOD olculuyor.
Ama aracin KENDISI hicbir zamanlayiciya BAGLI DEGILDI. Olcum (22 Eyl 20:3x):

    grep -rn "reklam-oci" .github/workflows/ ~/.claude/cron/
      -> .github/workflows/deploy.yml:1603   (yorum)
      -> .github/workflows/deploy.yml:1605   (KAPI)
      -> ~/.claude/cron/                     (HIC)

Sonuc: `--kuyrukla` HIC kosmuyordu (kuyruk hic dolmuyordu), `--yukle` HIC denenmiyordu.
Hat CANLI saniliyor ama OLUYDU. Bu, defterdeki "kirmizi gorunur ama okunmuyorsa kapi
degildir" dersinin kardesidir: **kosmayan bir adim YESIL GORUNUR.**

══════════════════════════════════════════════════════════════════════════════
🔴 NEDEN KARAR YAML `run:` GOVDESINDE DEGIL, BURADA
══════════════════════════════════════════════════════════════════════════════
Zarar esigi kabuk icinde (`if [ "$n" -gt 0 ]`) yasasaydi, kabul testi yalnizca YAML
METNINI okuyabilirdi ve "su dizge var mi" diye SAYARDI. Boyle bir kabul, kararin
kendisini HIC KOSMAZ -> alet KOR kalir
([[kabul-teslim-edilmeyen-iskeleyle-saglanirsa-alet-kor-kalir]]). `karar()` saf bir
fonksiyondur; `tools/reklam-oci-kosucu-test.py` onu GERCEKTEN cagirir ve mutant kolu
govdeyi bozunca KIRMIZI yanar.

══════════════════════════════════════════════════════════════════════════════
🔴 ZARAR ESIGI — HUKMUN KALBI
══════════════════════════════════════════════════════════════════════════════
"Kimlik yok" TEK BASINA KIRMIZI DEGILDIR. Bugun kimlik yok (4 alan SIFRE sinifi =
OKAN KAPISI) ve her kosum kirmizi yansaydi ekip bu kirmiziyi OKUMAYI BIRAKIRDI —
gurultu, fail-open'in en ucuz yoludur. Kirmizi sarti ZARARA baglanir:

    bekleyen > 0  ∧  kimlik YOK   ->  exit 1   (donusumler YASLANIYOR, gercek kayip)
    bekleyen = 0  ∧  kimlik YOK   ->  exit 0   + birebir `HAL=KIMLIK-BEKLIYOR BEKLEYEN=0`
    kimlik VAR                    ->  EL SIKISMA, sonra yukleme DENENIR
    kuyruk OLCULEMEDI             ->  exit 3   (YESIL DEGIL)

══════════════════════════════════════════════════════════════════════════════
🔴 EL SIKISMA — "KOSUM YESIL AMA istek=0" BOSLUGUNU KAPATIR
══════════════════════════════════════════════════════════════════════════════
Kimlikli ilk kosum (22 Eyl 2026, run 35776509904) `success` dondu ve birebir sunu
bastı:  `HAL=YESIL — kimlik TAM, yukleme DENENDI. BEKLEYEN(once)=0` /
        `YUKLEME: gonderilen=0 basarili=0 basarisiz=0 istek=0`
Bes alan da secret'ta KURULU, kosum YESIL — ve **istek=0**: gercek Google ucuna TEK
BIR ISTEK BILE CIKMADI. Kuyruk bos oldugu icin bu hal HAFTALARCA surebilirdi ve
**ilk gercek donusum ayni zamanda ilk testimiz** olurdu; kimlik kirikken ogrendigimiz
an KAYBEDILMIS bir donusumun ustunde olurdu.

Bu yuzden kimlik TAMken HER kosumda `reklam-oci-yukleyici.py::el_sikisma` kosar:
`googleAds:search` ile donusum eylemi SORGULANIR (SALT OKUMA) ve tek cagri uc seyi
birden kanitlar — OAuth takasi · hesap erisimi · donusum eyleminin kimligi+tipi.

🔴🔴 YAN ETKI YASAK: `uploadClickConversions` bu koldan CAGRILMAZ, `validateOnly`
ile BILE. Uretim donusum verisine / teklife / butceye HICBIR sey yazilmaz.

El sikisma hal sozlesmesi:
    200 + beklenen kayit    ->  `HAL=EL-SIKISMA-TAMAM`, kosum DEVAM eder
    kimlik EKSIK            ->  el sikisma ATLANIR (KIMLIK-BEKLIYOR kolu KORUNUR)
    401/403 / bulunamadi    ->  exit 1 KIRMIZI, metin `gizle()` suzgecinden GECER
    ag / zaman asimi / 5xx  ->  exit 3 OLCULEMEDI (YESIL DEGIL)

Ayrimi [[onarim-kolu-zarar-esiginin-arkasinda]] dersi zorunlu kilar: onarim kolu zarar
esiginin ARKASINDA durur, esigin ONUNDE degil.

══════════════════════════════════════════════════════════════════════════════
🔴 BAYRAK CAPRAZ KOLU — IKIZ TANIM SESSIZ AYRISIR
══════════════════════════════════════════════════════════════════════════════
Is akisi kimlik VARLIGINI `secrets.X != ''` karsilastirmasiyla bir `env` bayragina
indirir (`KIMLIK_BAYRAK`). Bu, aracin kendi `kimlik_coz()` olcumunun IKINCI bir
kopyasidir ve ikiz tanimlar bu depoda SESSIZCE AYRISIR. Bu yuzden bayrak KARAR VERMEZ,
yalnizca CAPRAZ OLCULUR: bayrak ile aracin olcumu ayrisirsa hal `OLCULEMEDI`dir (rc=3),
"secret eklendi ama is akisi gormuyor" ya da tersi SESSIZ KALAMAZ.

🔴 Bu arac SIFRE sinifi alanlari (CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN) URETMEZ,
ISTEMEZ, LOG'A YAZMAZ. Degerleri yalnizca ortamdan OKUNUR sayar; maskeleme
`reklam-oci-yukleyici.py::gizle` kolundadir (ikinci kopya YOK). Alan KUMESI de ikinci
kopya DEGILDIR: TEK KAYNAK `reklam-oci-yukleyici.py::KIMLIK_ALANLARI`. `DEVELOPER_TOKEN`
9 Eyl 2026'da Google tarafindan EMEKLI edildi -> ZORUNLU kumeden CIKTI (istege bagli).

Cikis kodlari (`reklam-oci-yukleyici.py` ile AYNI SOZLESME):
    0 YESIL       · 1 KIRMIZI · 2 KIMLIK-YOK (bu kolda 0/1'e indirgenir) · 3 OLCULEMEDI

Kullanim:
  python3 tools/reklam-oci-kosucu.py                 # canli D1, karar + (gerekirse) yukleme
  python3 tools/reklam-oci-kosucu.py --gh-ozet       # + $GITHUB_STEP_SUMMARY'ye yaz
  python3 tools/reklam-oci-kosucu.py --vt t.sqlite   # yerel sqlite kolu (tani/kabul)
  python3 tools/reklam-oci-kosucu.py --kuru          # yuklemeyi KURU kos (ag YOK)
"""

import argparse
import importlib.util
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
YUKLEYICI = os.path.join(TOOLS, "reklam-oci-yukleyici.py")

# ── Cikis kodlari — yukleyiciyle AYNI sozlesme (ikinci kopya degil, AYNI SAYILAR) ──
RC_YESIL = 0
RC_KIRMIZI = 1
RC_KIMLIK_YOK = 2
RC_OLCULEMEDI = 3

HAL_YESIL = "HAL=YESIL"
HAL_KIRMIZI = "HAL=KIRMIZI"
HAL_BEKLIYOR = "HAL=KIMLIK-BEKLIYOR"
HAL_OLCULEMEDI = "HAL=OLCULEMEDI"

# ── Eylemler — `karar()`in donusu. Test EYLEMI de dogrular, yalniz rc'yi DEGIL: ──
# rc tek basina ayirt etmez (BEKLE ve YUKLE'nin ikisi de 0 doner); eylem ekseni
# "hangi kol kosdu" sorusunu cevaplar.
EYLEM_BEKLE = "BEKLE"            # kimlik yok, zarar YOK  -> yesil, yukleme DENENMEZ
EYLEM_ZARAR = "ZARAR"            # kimlik yok, bekleyen>0 -> KIRMIZI
EYLEM_YUKLE = "YUKLE"            # kimlik var + el sikisma TAMAM -> yukleme DENENIR
EYLEM_EL_SIKISMA = "EL-SIKISMA"  # el sikisma DUSTU/OLCULEMEDI -> yukleme DENENMEZ
EYLEM_OLCULEMEDI = "OLCULEMEDI"  # kuyruk durumu okunamadi

BAYRAK_VAR = "VAR"
BAYRAK_YOK = "YOK"


# ══════════════════════════════════════════════════════════════════════════════
# SAF KARAR — testin GERCEKTEN kostugu govde. Disariya HICBIR bagimliligi yok.
# ══════════════════════════════════════════════════════════════════════════════
def karar(bekleyen, kimlik_tam):
    """ZARAR ESIGI. Doner: (eylem, rc).

    `bekleyen is None` => kuyruk OLCULEMEDI (yesil DEGIL, 3).
    🔴 Sira onemlidir: OLCULEMEDI once gelir — olculememis bir sayiyla zarar
    kiyaslamasi yapmak "bilinmeyeni 0 saymak"tir ve sessiz fail-open uretir.
    """
    if bekleyen is None:
        return EYLEM_OLCULEMEDI, RC_OLCULEMEDI
    bekleyen = int(bekleyen)
    if bekleyen < 0:
        # Negatif bir kuyruk uzunlugu FIZIKSEL OLARAK anlamsizdir; "0 gibi" saymak
        # zarar esigini sessizce kapatirdi.
        return EYLEM_OLCULEMEDI, RC_OLCULEMEDI
    if kimlik_tam:
        return EYLEM_YUKLE, RC_YESIL
    if bekleyen > 0:
        # 🔴 ZARAR ESIGI — mutant capasi BURADADIR. `>` `>=` olursa bekleyen=0
        # vakasi KIRMIZI yanar ve gurultu fail-open'i geri getirir.
        return EYLEM_ZARAR, RC_KIRMIZI
    return EYLEM_BEKLE, RC_YESIL


def bayrak_capraz(bayrak, kimlik_tam):
    """Is akisi `env` bayragi ile aracin kendi olcumu AYRISTI mi. Doner: ihlal|None."""
    if bayrak is None:
        return None
    b = str(bayrak).strip().upper()
    if not b:
        return None                      # bayrak verilmedi -> capraz kol KOSMAZ
    if b not in (BAYRAK_VAR, BAYRAK_YOK):
        return ("BAYRAK COZULEMEDI: KIMLIK_BAYRAK=%r (beklenen %s|%s)"
                % (bayrak, BAYRAK_VAR, BAYRAK_YOK))
    beklenen = BAYRAK_VAR if kimlik_tam else BAYRAK_YOK
    if b != beklenen:
        return ("BAYRAK AYRISMASI: is akisi bayragi %s, aracin kendi olcumu %s "
                "(secret kuruldu ama is akisi gormuyor — ya da tersi)" % (b, beklenen))
    return None


def ozet_satirlari(eylem, rc, bekleyen, eksik, yukleme_metni):
    """Insan-okunur hukum blogu. 🔴 BEKLEYEN sayisi HER kolda basilir."""
    s = []
    if eylem == EYLEM_OLCULEMEDI:
        s.append("%s — kuyruk durumu OKUNAMADI (BEKLEYEN olculemedi)." % HAL_OLCULEMEDI)
        s.append("  Neyi olcmek kapatir: `python3 tools/reklam-oci-yukleyici.py --durum`")
        s.append("  rc=0 dondurmeli; D1 kolu icin CLOUDFLARE_API_TOKEN + "
                 "CLOUDFLARE_ACCOUNT_ID gerekir.")
        return s
    if eylem == EYLEM_BEKLE:
        # 🔴 BIREBIR SATIR — kabul testi bunu DIZGE olarak dogrular.
        s.append("%s BEKLEYEN=0" % HAL_BEKLIYOR)
        s.append("  Kimlik EKSIK ama ZARAR YOK: gonderilmeyi bekleyen donusum satiri yok.")
        s.append("  Eksik alan (%d): %s" % (len(eksik), ", ".join(eksik) or "-"))
        s.append("  🔴 Bu alanlar SIFRE sinifidir (OKAN KAPISI); arac onlari URETMEZ/ISTEMEZ.")
        return s
    if eylem == EYLEM_ZARAR:
        s.append("%s — ZARAR ESIGI ASILDI: BEKLEYEN=%d ve kimlik EKSIK."
                 % (HAL_KIRMIZI, bekleyen))
        s.append("  Donusumler YASLANIYOR: Google Ads tiklama donusumlerini sinirli bir")
        s.append("  pencerede kabul eder; bekleyen satirlar gonderilemezse ATIF KAYBOLUR.")
        s.append("  Eksik alan (%d): %s" % (len(eksik), ", ".join(eksik) or "-"))
        # 🔴 SAYI YAZILMAZ, EKSIK LISTESINDEN OKUNUR: alan kumesi degistiginde
        # (ornek: `developer token` 9 Eyl 2026'da emekli edildi) elle yazilmis bir
        # sayi SESSIZCE bayatlar ve red metni yanlis yeri gosterir.
        s.append("  🔴 Kapatan sey: yukarida ADIYLA sayilan %d SIFRE alaninin repo "
                 "secret'ina kurulmasi (OKAN KAPISI)." % len(eksik))
        return s
    # EYLEM_YUKLE
    s.append("%s — kimlik TAM, yukleme DENENDI. BEKLEYEN(once)=%d"
             % (HAL_YESIL if rc == RC_YESIL else HAL_KIRMIZI, bekleyen))
    if yukleme_metni:
        for satir in str(yukleme_metni).splitlines():
            s.append("  %s" % satir)
    return s


# ══════════════════════════════════════════════════════════════════════════════
# KOSUM GOVDESI — uc kol da ENJEKTE edilir; kabul testi AG'A CIKMADAN kosar.
# ══════════════════════════════════════════════════════════════════════════════
def kos(durum_kolu, kimlik_kolu, yukle_kolu, bayrak=None, yaz=None,
        el_sikisma_kolu=None):
    """Doner: (rc, satirlar, eylem).

    durum_kolu()      -> bekleyen (int) | None (olculemedi)
    kimlik_kolu()     -> (kimlik_tam: bool, eksik: list[str])
    el_sikisma_kolu() -> (rc: int, satirlar: list[str]) — YALNIZ kimlik TAMken CAGRILIR
    yukle_kolu()      -> (rc: int, metin: str)   — YALNIZ el sikisma YESILSE CAGRILIR

    🔴 EL SIKISMA ZARAR ESIGININ ARKASINDADIR, ONUNDE DEGIL: kimlik EKSIKken
    (bugunku fail-closed hal) kol HIC CAGRILMAZ ve `KIMLIK-BEKLIYOR` bacagi aynen
    korunur. Esigin ONUNE konsaydi, kimliksiz gunlerde her kosum ag'a cikmaya
    calisirdi ve gurultu fail-open'i geri getirirdi
    ([[onarim-kolu-zarar-esiginin-arkasinda]]).
    """
    try:
        bekleyen = durum_kolu()
    except Exception as e:                      # noqa: BLE001 — her ariza OLCULEMEDI
        bekleyen = None
        _ = e

    kimlik_tam, eksik = kimlik_kolu()

    ihlal = bayrak_capraz(bayrak, kimlik_tam)
    if ihlal:
        satirlar = ["%s — %s" % (HAL_OLCULEMEDI, ihlal),
                    "  Karar VERILMEDI: ikiz tanim ayristi, hangisinin dogru oldugu",
                    "  bu kosumda OLCULEMEZ. Kapatan sey: is akisi `KIMLIK_BAYRAK`",
                    "  ifadesi ile `kimlik_coz()` alan kumesinin ayni olmasi."]
        if yaz:
            yaz(RC_OLCULEMEDI, satirlar)
        return RC_OLCULEMEDI, satirlar, EYLEM_OLCULEMEDI

    eylem, rc = karar(bekleyen, kimlik_tam)

    yukleme_metni = ""
    el_satirlari = []
    if eylem == EYLEM_YUKLE:
        # ── EL SIKISMA — YAN ETKISIZ, SALT-OKUMA; yuklemeden ONCE ───────────
        if el_sikisma_kolu is None:
            # 🔴 FAIL-CLOSED: kol KABLOLANMAMIS. "Adim yoksa gecmis say" yolu ACILMAZ —
            # bu aracin VAR OLMA SEBEBI tam olarak budur: kosmayan bir adim YESIL
            # GORUNUR. Kablolanmamis bir dogrulama OLCULEMEDI'dir, yesil DEGIL.
            satirlar = [
                "%s — EL SIKISMA KOLU KABLOLANMAMIS (kimlik TAM ama dogrulama YOK)."
                % HAL_OLCULEMEDI,
                "  Yukleme DENENMEDI: dogrulanmamis bir kimlikle uretim donusumu",
                "  gondermek, ilk gercek donusumu ayni zamanda ilk teste cevirir.",
                "  Neyi olcmek kapatir: `kos()` cagrisina `el_sikisma_kolu` gecilmesi",
                "  (uretim yolu `main()` icinde `gercek_el_sikisma_kolu` ile baglidir).",
            ]
            if yaz:
                yaz(RC_OLCULEMEDI, satirlar)
            return RC_OLCULEMEDI, satirlar, EYLEM_EL_SIKISMA

        el_rc, el_satirlari = el_sikisma_kolu()
        el_satirlari = list(el_satirlari or [])
        if el_rc != RC_YESIL:
            satirlar = el_satirlari + [
                "  🔴 YUKLEME DENENMEDI: el sikisma yesil donmeden uretim donusumu",
                "     gonderilmez. BEKLEYEN(once)=%s" % bekleyen,
            ]
            if yaz:
                yaz(el_rc, satirlar)
            return el_rc, satirlar, EYLEM_EL_SIKISMA

        rc, yukleme_metni = yukle_kolu()

    satirlar = el_satirlari + ozet_satirlari(eylem, rc, bekleyen, eksik, yukleme_metni)
    if yaz:
        yaz(rc, satirlar)
    return rc, satirlar, eylem


# ══════════════════════════════════════════════════════════════════════════════
# GERCEK KOLLAR — uretimde kullanilanlar. Kabul testi bunlari DEGISTIRIR.
# ══════════════════════════════════════════════════════════════════════════════
def yukleyici_modulu():
    """`tools/reklam-oci-yukleyici.py`yi yukle (ad tire tasir, duz import calismaz)."""
    spec = importlib.util.spec_from_file_location("reklam_oci_yukleyici_kosucu", YUKLEYICI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def gercek_durum_kolu(mod, vt_yolu=None):
    def _kol():
        try:
            vt = mod.vt_ac(vt_yolu)
        except Exception:                       # noqa: BLE001
            return None
        try:
            return int(mod.durum(vt)["bekleyen"])
        except Exception:                       # noqa: BLE001
            return None
        finally:
            try:
                vt.kapat()
            except Exception:                   # noqa: BLE001
                pass
    return _kol


def gercek_kimlik_kolu(mod):
    def _kol():
        kimlik, eksik = mod.kimlik_coz()
        return (kimlik is not None), list(eksik)
    return _kol


def gercek_el_sikisma_kolu(mod):
    """YAN ETKISIZ el sikisma kolu — `googleAds:search` (SALT OKUMA).

    🔴 Yukleme kolunun aksine AYRI SURECTE kosmaz: hicbir sey YAZMADIGI icin
    izole etmeye gerek yoktur ve rc dogrudan fonksiyondan gelir.
    🔴 `uploadClickConversions` BU KOLDAN CAGRILMAZ — `validateOnly` ile BILE.
    """
    def _kol():
        kimlik, eksik = mod.kimlik_coz()
        if kimlik is None:                       # pragma: no cover (savunma)
            # `kos()` bu kolu yalniz kimlik TAMken cagirir; buraya dusulurse
            # olcum ile kol ayrismis demektir -> YESIL DEGIL.
            return mod.RC_OLCULEMEDI, [
                "%s — EL SIKISMA: kol kimlik TAM sanilarak cagrildi ama %d alan EKSIK."
                % (mod.HAL_OLCULEMEDI, len(eksik))]
        return mod.el_sikisma(kimlik, mod.HttpTasiyici())
    return _kol


def secili_el_sikisma_kolu(mod, kuru=False):
    """Kosum kipine gore el sikisma kolunu SEC.

    🔴 `--kuru` KOLUNDA EL SIKISMA ATLANIR ve bu FAIL-OPEN DEGILDIR: el sikismanin
    kapattigi risk "bozuk kimlikle GERCEK yukleme"dir, kuru kosumda gercek yukleme
    YOKTUR (yukleyici govdeyi basar, ag'a CIKMAZ). Atlamanin URETIME sizmasini
    ONLEYEN sey bir yorum degil, OLCUMDUR: is akisi kosucuya `--kuru` GECEMEZ ve
    bunu `reklam-oci-kosucu-test.py::akis_kablolamasi` KIRMIZI yakarak zorlar.
    """
    if not kuru:
        return gercek_el_sikisma_kolu(mod)

    def _kuru_kol():
        return RC_YESIL, [
            "EL SIKISMA ATLANDI — `--kuru` kolu AG'A CIKMAZ (uretime hicbir sey",
            "  gonderilmez). CI kolu `--kuru` GECMEZ; bunu kabul testi OLCER.",
        ]
    return _kuru_kol


def gercek_yukle_kolu(vt_yolu=None, kuru=False, tavan=200):
    """Yuklemeyi AYRI SURECTE kosar — govde ikinci kez YAZILMAZ, rc DOGRUDAN okunur.

    🔴 Boru YOK: `| tail` rc'yi yutar ve olcumu yalanlar
    ([[boru-rc-isci-olcumunu-yalanlar]]). `capture_output` boru degildir, rc korunur.
    """
    def _kol():
        cmd = [sys.executable, YUKLEYICI, "--yukle", "--tavan", str(int(tavan))]
        if vt_yolu:
            cmd += ["--vt", vt_yolu]
        if kuru:
            cmd += ["--kuru"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        metin = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return p.returncode, metin.strip()
    return _kol


def gh_yazici(ortam=None):
    """$GITHUB_STEP_SUMMARY'ye ekler. Degisken yoksa SESSIZCE atlar (yerelde de kosar)."""
    ort = os.environ if ortam is None else ortam

    def _yaz(rc, satirlar):
        yol = ort.get("GITHUB_STEP_SUMMARY")
        if not yol:
            return
        baslik = {RC_YESIL: "### 🟢 Reklam OCI kosucu",
                  RC_KIRMIZI: "### 🔴 Reklam OCI kosucu: ZARAR ESIGI",
                  RC_OLCULEMEDI: "### 🔴 Reklam OCI kosucu: OLCULEMEDI"}.get(
                      rc, "### 🔴 Reklam OCI kosucu")
        with open(yol, "a", encoding="utf-8") as f:
            f.write(baslik + "\n\n")
            for s in satirlar:
                f.write("%s\n" % s)
            f.write("\n")
    return _yaz


# ══════════════════════════════════════════════════════════════════════════════
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vt", default=None,
                    help="yerel sqlite dosyasi (verilmezse CANLI D1)")
    ap.add_argument("--kuru", action="store_true",
                    help="yuklemeyi KURU kos (ag cikisi YOK)")
    ap.add_argument("--tavan", type=int, default=200,
                    help="tek kosumda en cok satir (yukleyiciye gecer)")
    ap.add_argument("--gh-ozet", action="store_true",
                    help="hukmu $GITHUB_STEP_SUMMARY'ye de yaz")
    a = ap.parse_args(argv)

    mod = yukleyici_modulu()
    rc, satirlar, eylem = kos(
        durum_kolu=gercek_durum_kolu(mod, a.vt),
        kimlik_kolu=gercek_kimlik_kolu(mod),
        el_sikisma_kolu=secili_el_sikisma_kolu(mod, kuru=a.kuru),
        yukle_kolu=gercek_yukle_kolu(a.vt, kuru=a.kuru, tavan=a.tavan),
        bayrak=os.environ.get("KIMLIK_BAYRAK"),
        yaz=gh_yazici() if a.gh_ozet else None,
    )
    for s in satirlar:
        print(s)
    print("EYLEM=%s rc=%d" % (eylem, rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
