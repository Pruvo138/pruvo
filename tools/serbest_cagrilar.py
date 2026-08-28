"""TEK KAYNAK — mimar elinde SERBEST python cagrilarinin CAGRI SEKILLERI.

=== NEDEN VAR (olculmus ariza, 28 Agu 2026 — K258/K168 SINIF ISI) ===
K320 (27 Agu) kapinin RED METNINI karar yapisindan TURETTI, ama turettigi sey yalnizca
ARAC ADLARIYDI. CAGRI SEKLI (bayraklar + konumsal argumanlar) hala HER TUKETICIDE ELLE
yaziliydi. Olculen taban (28 Agu, `tools/_taban_olcum_k258.py`):

  * `cip_dogum_bekcisi.py --teslim-karari` / `--teslim-kaydet` -> RED. Cip-dogum
    bekcisinin TESLIM KOLU (`tools/sabah-teslim/kos.py`) tam bu cagriyi yapar; hukum
    KIRMIZI ciktigi gun mimarin elinde ayni cagri KAPIDA OLUYORDU (K319/K332 sinifi).
    Kapinin serbest listesinde `cip_dogum_bekcisi` HIC gecmiyordu (0 satir).
  * `defter-rotasyon.py --tavan-kaynaktan --isaretciye-indir` (KONUMSUZ form) -> RED.
    Kutuda/careye atifta gecen bu kisa form kapida oluydu; yalniz iki-konumlu form
    geciyordu.
  * ELLE YAZILMIS cagri-sekli dizgesi UC tuketicide toplam 46 kez tekrarlaniyordu
    (mimar-icra-kapisi 17 · serbest-kume-tekkaynak-test 15 · defter-kota-kapisi 14).

Yani K320'nin kapattigi ariza (ad ekseni) kapaliydi, AYNI SINIFIN ikinci ekseni
(CAGRI SEKLI ekseni) acikti: kapi bir bayragi kesiyor, baska bir kapi ayni bayragi
CARE olarak basiyor, nobetci ucuncu bir kopyayla olcuyordu.

=== SINIF KURALI (tekil yama DEGIL) ===
Mimar elinde serbest olan HER python cagrisi — arac adi, konumsal argumanlari, izinli
bayraklari ve deger alan bayraklariyla — YALNIZ BURADA tanimlanir. Tuketiciler:

  1. `tools/mimar-icra-kapisi.py`      — KARAR (`_py_izinli`) + RED METNI
  2. `tools/defter-kota-kapisi.py`     — CARE satirlari
  3. `tools/serbest-kume-tekkaynak-test.py` — NOBETCI fikstuleri

Hicbir tuketici ikinci bir kopya TUTMAZ. Bir sekil buradan DUSERSE hepsinde birden
duser: cagri REDDEDILIR, adi RED METNINDEN silinir, CARE satiri degisir, nobetci
kirmizi yanar. Nobetci: `tools/serbest-kume-tekkaynak-test.py` (mutasyonlu, CI'da kosar).

Ilgili dersler: [[kapi-red-metni-ikinci-kopyadir]] · [[ikiz-tanim-sessiz-ayrisma]] ·
[[kapinin-menzili-cagri-yeridir]] · [[ucuncu-tekrar-sinif-kapisi]]
"""

REPO_ONEKI = "/Users/okan/dev/pruvo/"
CRON_ONEKI = "/Users/okan/.claude/cron/"

# Deger alan bayragin DEGERI icin kural (R2'yi delmemek icin ZORUNLU):
# deger YOL OLAMAZ ('/' iceremez, '.' ile baslayamaz) ve bayrak gibi gorunemez.
# Aksi halde '--task-id /private/tmp/x' repo-disi yol tasima anahtari olurdu.


class Sekil(object):
    """TEK bir serbest cagri SEKLI — arac + konumlar + bayraklar.

    etiket     : tuketicilerin bu sekli ADIYLA istemesi icin anahtar (dizge).
    arac       : arac betiginin MUTLAK kanonik yolu (TAM ESITLIK ile dogrulanir).
    konumlar   : beklenen konumsal argumanlarin MUTLAK kanonik yollari (sirali).
                 () = konumsal argüman ALMAZ.
    zorunlu    : bu seklin ESLESMESI icin BULUNMASI gereken bayraklar.
    serbest    : bulunabilir/bulunmayabilir bayraklar (bool bayrak).
    degerli    : '<bayrak> <deger>' seklinde deger alan bayraklar (opsiyonel).
    ornek      : CARE/ornek komut basilirken kullanilacak bayrak sirasi.
    repo_disi  : arac repo agacinin DISINDA mi (bilgi amacli; kapida PY_NODE kolu
                 eslesme halinde segmenti KAPATIR, R2/F'ye hic dusmez).
    """

    __slots__ = ("etiket", "arac", "konumlar", "zorunlu", "serbest",
                 "degerli", "ornek", "repo_disi")

    def __init__(self, etiket, arac, konumlar=(), zorunlu=(), serbest=(),
                 degerli=(), ornek=(), repo_disi=False):
        self.etiket = etiket
        self.arac = arac
        self.konumlar = tuple(konumlar)
        self.zorunlu = frozenset(zorunlu)
        self.serbest = frozenset(serbest)
        self.degerli = frozenset(degerli)
        self.ornek = tuple(ornek)
        self.repo_disi = repo_disi

    @property
    def tum_bayraklar(self):
        return self.zorunlu | self.serbest | self.degerli


# --- KANONIK YOLLAR (tek kaynak; tuketiciler bunlari BURADAN okur) -------------
DURUM_YOL = REPO_ONEKI + "tools/durum.py"
D1_YOL = REPO_ONEKI + "tools/d1-sync.py"
DEFTER_ROTASYON_YOL = REPO_ONEKI + "tools/defter-rotasyon.py"
DEFTER_ROTASYON_DEFTER = REPO_ONEKI + "DEVAM.md"
DEFTER_ROTASYON_ARSIV = REPO_ONEKI + "DEVAM-ARSIV.md"
KUTU_ARSIVLE_YOL = REPO_ONEKI + "tools/kutu-arsivle.py"
CIP_BEKCI_YOL = CRON_ONEKI + "cip_dogum_bekcisi.py"
ONARIM_DURUM_YOL = REPO_ONEKI + "tools/onarim-durum.py"

# Defter bakimi bayraklari — arac ADINA degil, SEKLE baglidir.
# 🔴 HER BAYRAK ADI TEK BIR YERDE YAZILIR. Ilk surumde '--tavan-kaynaktan' HEM
# ROTASYON_BAKIM_BAYRAKLARI'nda HEM 'rotasyon-kisa' seklinin `zorunlu`sunda ELLE
# yaziliydi; MX3 mutanti (bayrak formu degisir) o ikizligi YAKALADI — biri degisince
# oteki eski adi tasimaya devam etti ve metin ESKI bayragi gostermeyi surdurdu.
# Yani tek kaynagin KENDI ICINDE ikinci kopyasi vardi ([[ikiz-tanim-sessiz-ayrisma]]).
ROTASYON_TAVAN_BAYRAGI = "--tavan-kaynaktan"
ROTASYON_INDIRME_BAYRAGI = "--isaretciye-indir"
ROTASYON_BAKIM_BAYRAKLARI = (ROTASYON_TAVAN_BAYRAGI, ROTASYON_INDIRME_BAYRAGI)


# === SEKILLER — MIMAR ELINDE SERBEST OLAN HER SEY, TEK YERDE ==================
SEKILLER = (
    # 🔴 K344-B (28 Agu) — `--ne-olculmedi` TERS YONDEN BULUNDU. Taban olculdu:
    # `python3 tools/durum.py --ne-olculmedi` -> RED. Oysa `durum.py` OLCULEMEDI
    # gordugu her kosumda okuyana TAM BU KOMUTU CARE olarak basiyordu — yani arac
    # bir cagriyi tarif ediyor, kapi o cagriyi reddediyordu. Ariza `--kapanislari-isle`
    # ile AYNI SINIF (arac -> kaynak yonu), ve o yon 28 Agu sabahina kadar HIC
    # OLCULMUYORDU. Bayrak SALT-OKUR (yalniz ilan edilmis kor noktalari basar), arac
    # zaten bayraksiz SERBEST — kova genislemiyor, ayni aracin ikinci ciktisi aciliyor.
    Sekil("durum", DURUM_YOL, serbest=("--ne-olculmedi",)),

    Sekil("d1-durum", D1_YOL, zorunlu=("--durum",), ornek=("--durum",)),

    # K168 H1 (18 Agu): iki konumlu KLASIK form — bayrak YOK.
    Sekil("rotasyon-klasik", DEFTER_ROTASYON_YOL,
          konumlar=(DEFTER_ROTASYON_DEFTER, DEFTER_ROTASYON_ARSIV)),

    # K258 (20 Agu): DEFTER BAKIMI — iki konum + kova bayraklari. Kota kapisinin
    # bastigi CARE budur.
    Sekil("rotasyon-bakim", DEFTER_ROTASYON_YOL,
          konumlar=(DEFTER_ROTASYON_DEFTER, DEFTER_ROTASYON_ARSIV),
          serbest=ROTASYON_BAKIM_BAYRAKLARI,
          ornek=ROTASYON_BAKIM_BAYRAKLARI),

    # 🔴 28 AGU (bu is): KONUMSUZ KISA FORM. Kutuda/atifta gecen bicim buydu ve
    # KAPIDA OLUYDU (taban T2=RED). Aracin konumsal argumanlari artik BU TEK
    # KAYNAKTAN varsayilan alir (defter-rotasyon.py nargs='?'), yani kapinin
    # gecirdigi cagri gercekten KOSAR — kapi calismayan bir sey vaat etmez.
    Sekil("rotasyon-kisa", DEFTER_ROTASYON_YOL,
          zorunlu=(ROTASYON_TAVAN_BAYRAGI,),
          serbest=(ROTASYON_INDIRME_BAYRAGI,),
          ornek=ROTASYON_BAKIM_BAYRAKLARI),

    # K258 (20 Agu): ORTAK POSTA KUTUSU bakimi. Konumsal arg ALMAZ (yollar aracin
    # kendi tek kaynagindan gelir); ornekte '--kuru' YOK — CARE ISLEK bicimi basar.
    # 🔴 K344 (28 Agu) — `--kapanislari-isle` BURAYA SONRADAN EKLENDI, sebebi
    # OLCULDU: iki oksuz dal ayni gun BIRBIRINDEN HABERSIZ indi. Biri (K341)
    # araca YENI BIR KOL ekledi (`--kapanislari-isle`: kapanis jetonu cevrimi),
    # oteki (K258/K168) cagri SEKILLERINI bu tabloya tasidi. Tabloya yazilmayan
    # kol, ANA oturumda kapidan GECMEZ — yani defter/kutu kotasi kirmizi yandiginda
    # mimar, kapinin KENDI onerdigi careyi kosamazdi ([[kapi-red-metni-ikinci-kopyadir]]).
    # NOT — C3 kolu bu bosluğu GORMEZDI: C3 'kaynaktaki her bayrak aracin CLI'sinda
    # VAR mi' diye sorar (kaynak -> arac); buradaki eksiklik TERS yondeydi
    # (arac -> kaynak). 🔴 K344-B (28 Agu) o ekseni OLCUME BAGLADI: asagidaki
    # DISARIDA tablosu + nobetcinin C5/C6 kollari. Ayni sinifin ikinci vakasi
    # (`durum.py --ne-olculmedi`) o kol tarafindan BULUNDU.
    Sekil("kutu-arsivle", KUTU_ARSIVLE_YOL,
          serbest=("--kuru", "--kapanislari-isle")),

    # 🔴 28 AGU (bu is): CIP-DOGUM BEKCISININ TESLIM KOLU.
    # OLCULEN ARIZA: bekcinin teslim kolu (`tools/sabah-teslim/kos.py`) tam bu iki
    # cagriyi yapar; kapinin serbest listesinde `cip_dogum_bekcisi` HIC gecmiyordu
    # (0 satir) ve hukum KIRMIZI ciktigi gun mimar careyi ELIYLE kosamiyordu.
    # Arac ~/.claude/cron/ altinda, yani repo DISINDA: PY_NODE kolu eslesince
    # segmenti KAPATIR (continue), boylece R2/F kollarina hic dusmez. Kova ADLIDIR:
    # yalniz KANONIK yol, TAM ESITLIKLE — basename KABUL EDILMEZ.
    Sekil("bekci-teslim-karari", CIP_BEKCI_YOL,
          zorunlu=("--teslim-karari",), serbest=("--kuru",),
          ornek=("--teslim-karari",), repo_disi=True),
    Sekil("bekci-teslim-kaydet", CIP_BEKCI_YOL,
          zorunlu=("--teslim-kaydet",),
          degerli=("--anahtar", "--task-id", "--sebep"),
          ornek=("--teslim-kaydet",), repo_disi=True),

    # 🔴 28 AGU (bu is): `onarim-durum.py` — hattin onarim turu acmis mi diskten
    # okuyan SALT-OKUR arac. Konumsal arguman ALMAZ, hicbir bayrak TANIMAZ (aracin
    # CLI'si YOK). Mimar elinde SERBEST: Okan'in "terminale girmeden soracagim bir
    # sey yap" emri (28 Agu); taban canli ONARIM/GOZCU/KIRMIZI sayilarini cevap
    # olarak verir. Guvenli: dosya DEGISTIRMEZ, aga cikmaz, LLM/agent turu acmaz
    # — bu yuzden mimar katinda serbest birakilmasi SAKINCALI degil.
    Sekil("onarim-durum", ONARIM_DURUM_YOL),
)

SEKIL_ETIKETLERI = {s.etiket: s for s in SEKILLER}


# === 🔴 K344-B (28 AGU 2026) — TERS YON: ARAC -> KAYNAK =======================
# OLCULEN ARIZA. K320 (ad ekseni) ve K258/K168 (cagri sekli ekseni) kapandiktan
# SONRA da bir bosluk DURUYORDU ve nobetci onu GORMUYORDU:
#
#   Nobetcinin C3 kolu yalnizca `kaynak -> arac` yonunu olcer ("bu tablodaki her
#   bayrak aracin CLI'sinda VAR MI"). Ters yon — `arac -> kaynak` — yani ARACA
#   EKLENMIS ama TABLOYA YAZILMAMIS bir bayrak, hicbir kolun menzilinde degildi.
#
# Bu bosluktan IKI ariza dustu (ikisi de ayni gun olculdu):
#   * `kutu-arsivle.py --kapanislari-isle` (K341'de araca eklendi) — tabloya
#     yazilmadigi icin ANA oturumda kapidan GECMIYORDU; kutu kotasi kirmizi
#     yandiginda mimar kapinin KENDI bastigi CAREYI kosamiyordu. Elle kapatildi
#     (`a5fc8f22`), yani ariza ONARILDI ama OLCUM eklenmedi.
#   * `durum.py --ne-olculmedi` — TABAN RED (olculdu). `durum.py`, OLCULEMEDI gordugu
#     her kosumda okuyana bu komutu CARE olarak basiyordu; kapi onu reddediyordu.
#     Bu ikincisi, ters yon kolu icin cikarilan CLI ENVANTERINDE gorundu — yani
#     araniyor degildi, olcumun kendisi ortaya cikardi. Nobetcinin MB3 mutanti bu
#     vakayi GERI SARAR (bayragi tablodan dusurur) ve C5'in onu KIRMIZI yaktigini
#     kanitlar; ayrica toplayicinin `sys.argv` kolunu olcer (durum.py argparse
#     KULLANMAZ — yalniz add_argument okuyan bir toplayici bu vakada SESSIZ kalirdi).
#
# 🔴 SINIF KURALI: bu tablo, hukum verdigi HER ARACIN CLI'sindaki HER bayrak
# hakkinda BIR HUKUM tasir — ya bir SEKILDE serbesttir, ya BURADA gerekcesiyle
# DISARIDADIR. Ucuncu bir hal ("tablo bu bayragi hic duymamis") KIRMIZIDIR:
# nobetcinin ters yon kolu (C5) onu yakalar ve karar MIMARDAN istenir. Bu, sessiz
# ayrismanin tek fail-closed caresidir — [[kapi-red-metni-ikinci-kopyadir]] ·
# [[tuketici-yazilirken-tum-okuyucular-sayilir]].
#
# DISARIDA olmak "bu bayrak kotu" demek DEGIL; "mimarin ELINDE serbest DEGIL"
# demek — cogu isci/CI kolu, yazan kol ya da ayar bayragidir.
DISARIDA = {
    DURUM_YOL: {},

    D1_YOL: {
        # D1'e YAZAN / sema kuran kollar: deploy sinifi, OKAN KAPISI.
        "--sema": "semayi KURAR (yazar) — deploy sinifi",
        "--seq-normalize": "D1'de seq kolonunu YAZAR",
        "--karantina-damgasi": "deger YOL alir; silme karantinasini yonetir",
        "--adim": "CI senkron adiminin ikamesi — CI kolu, mimar eli degil",
        # Olcum/test kollari: iscinin isi (K318 rol ekseni).
        "--kuru": "senkron PLANI basar — senkron kolunun provasi, isci isi",
        "--kendini-test": "offline kabul testi — test kosumu iscinin isi",
        "--bayatlik": "CI on-kosulu; agac uc mu diye olcer — isci isi",
        "--hizli": "--durum'un ICERIK eksenini ATLAR: eksik olcum, mimar tam olcum ister",
        # Katalog KAYNAGINI degistirenler: sessiz kaynak degisimi riski.
        "--kaynak": "deger YOL alir; katalog kaynagini DEGISTIRIR",
        "--head": "katalogu HEAD'den okur — kaynak degistirir",
    },

    DEFTER_ROTASYON_YOL: {
        # Tavani ELLE veren bayraklar: kota kapisinin okudugu tek kaynagi bypass
        # eder. Nobetcinin B2 kolu `--tavan-sayi`nin RED KALDIGINI ayrica olcer.
        "--tavan-sayi": "tavani ELLE verir — kaynaktan turetmeyi bypass eder",
        "--tavan-bayt": "tavani ELLE verir — kaynaktan turetmeyi bypass eder",
        "--tarih": "rotasyon tarihini ELLE verir — fikstur/test kolu",
    },

    KUTU_ARSIVLE_YOL: {
        # Deger alan YOL bayraklari: repo-disi yol tasima anahtari olurlardi.
        "--kutu": "deger YOL alir — kutu dosyasini DEGISTIRIR",
        "--arsiv": "deger YOL alir — arsiv dosyasini DEGISTIRIR",
        "--kilit": "deger YOL alir — kilit dosyasini DEGISTIRIR",
        "--yaz-sonrasi": "deger YOL alir — duzenlenen dosyayi DEGISTIRIR",
        # Sayisal ayar bayraklari: esikleri ELLE oynatir.
        "--tavan": "tavani ELLE verir — esigi oynatir",
        "--koru": "korunan kalem sayisini ELLE verir",
        "--su-seviye-orani": "su seviyesi oranini ELLE verir",
        "--arsiv-kuyruk": "arsiv kuyruk boyunu ELLE verir",
    },

    CIP_BEKCI_YOL: {},

    # `onarim-durum.py` SALT-OKUR: konumsal arguman YOK, hicbir bayrak TANIMAZ
    # (aracin CLI'si yok). Dolayisiyla DISARIDA'da hicbir bayrak gerekceli degil.
    ONARIM_DURUM_YOL: {},
}


def araclar():
    """Bu tablonun hukum verdigi ARAC yollari (tekil, sirali)."""
    return sorted({s.arac for s in SEKILLER})


def serbest_bayraklar(arac):
    """Bir ARAC icin tablodaki TUM sekillerin izin verdigi bayraklarin birlesimi."""
    kume = set()
    for s in SEKILLER:
        if s.arac == arac:
            kume |= set(s.tum_bayraklar)
    return kume


def disarida_bayraklar(arac):
    """Bir ARAC icin BILINCLI olarak disarida birakilmis bayraklar (ad -> gerekce)."""
    return dict(DISARIDA.get(arac, {}))


def hukumlu_bayraklar(arac):
    """Tablonun bu arac icin BIR HUKUM tasidigi bayraklar (serbest ∪ disarida).

    Ters yon kolu (nobetci C5) aracin CLI'sini bu kumeye karsi olcer: kumede
    OLMAYAN her CLI bayragi, tablonun HIC DUYMADIGI bir koldur -> KIRMIZI."""
    return serbest_bayraklar(arac) | set(DISARIDA.get(arac, {}))


def _deger_guvenli(deger):
    """Deger alan bayragin DEGERI yol/bayrak OLAMAZ — R2 bu koldan delinmesin."""
    if not deger or deger.startswith("-"):
        return False
    if "/" in deger or deger.startswith("."):
        return False
    return True


def eslesen_sekil(argumanlar, coz, cwd):
    """python3 SONRASINDAKI tokenlari SEKILLERE karsi cozer.

    Doner: eslesen Sekil, yoksa None (fail-closed).
    `coz(yol, cwd)` cagirana aittir — yol cozumu IKINCI KEZ yazilmaz
    ([[ikiz-tanim-sessiz-ayrisma]]).

    Dizge eslemesi YAPILMAZ: arac ve konumlar COZULMUS MUTLAK yolla TAM ESITLIK
    ile karsilastirilir ([[n2b-kapisi-dizge-olcer]]). '=' li yazim (--tavan-sayi=130)
    hicbir kumeye TAM ESIT olmadigi icin RED kalir.
    """
    if not argumanlar:
        return None
    arac_cozulmus = coz(argumanlar[0], cwd)
    adaylar = [s for s in SEKILLER if s.arac == arac_cozulmus]
    if not adaylar:
        return None
    for sekil in adaylar:
        if _sekil_uyuyor(sekil, argumanlar[1:], coz, cwd):
            return sekil
    return None


def _sekil_uyuyor(sekil, kalan, coz, cwd):
    bayraklar = []
    konumlar = []
    i = 0
    while i < len(kalan):
        t = kalan[i]
        if t.startswith("-"):
            if t not in sekil.tum_bayraklar:
                return False
            bayraklar.append(t)
            if t in sekil.degerli:
                # Deger alan bayrak: SONRAKI token degerdir ve yol OLAMAZ.
                if i + 1 >= len(kalan) or not _deger_guvenli(kalan[i + 1]):
                    return False
                i += 2
                continue
            i += 1
            continue
        konumlar.append(t)
        i += 1

    if len(bayraklar) != len(set(bayraklar)):
        return False                       # tekrarlanan bayrak = RED
    if not sekil.zorunlu.issubset(set(bayraklar)):
        return False                       # zorunlu bayrak eksik = bu sekil DEGIL
    if len(konumlar) != len(sekil.konumlar):
        return False
    for verilen, beklenen in zip(konumlar, sekil.konumlar):
        if coz(verilen, cwd) != beklenen:
            return False
    return True


# === TURETILMIS METINLER — HICBIR TUKETICI BUNLARI ELLE YAZMAZ ================
def _kisa(yol):
    """Mutlak yolu okunur kisa ada indirger (repo -> 'tools/x.py', cron -> '~/...')."""
    if yol.startswith(REPO_ONEKI):
        return yol[len(REPO_ONEKI):]
    if yol.startswith(CRON_ONEKI):
        return "~/.claude/cron/" + yol[len(CRON_ONEKI):]
    return yol


def sekil_metni(sekil):
    """TEK bir seklin insan-okur cagri metni ('python3 tools/x.py A B [--f]')."""
    parcalar = ["python3 " + _kisa(sekil.arac)]
    parcalar.extend(_kisa(k) for k in sekil.konumlar)
    parcalar.extend(sorted(sekil.zorunlu))
    parcalar.extend("[" + b + "]" for b in sorted(sekil.serbest))
    parcalar.extend("[" + b + " <deger>]" for b in sorted(sekil.degerli))
    return " ".join(parcalar)


def serbest_python_metni():
    """RED metninde gecen SERBEST cagri listesi — SEKILLER'den TURETILIR.

    Bir sekil kumeden DUSERSE hem cagri REDDEDILIR hem de bu metinden DUSER; ikisi
    ayni yapidan beslendigi icin AYRISAMAZLAR ([[kapi-red-metni-ikinci-kopyadir]])."""
    return " · ".join("'" + sekil_metni(s) + "'" for s in SEKILLER)


def cagri_ornegi(etiket):
    """CARE satirlari icin CALISTIRILABILIR ornek komut (MUTLAK yollarla).

    `defter-kota-kapisi.py` bu fonksiyonu cagirir; CARE metnini ELLE YAZMAZ. Deger
    alan bayraklar ornege GIRMEZ (degerleri cagri anina aittir)."""
    sekil = SEKIL_ETIKETLERI[etiket]
    parcalar = ["python3", sekil.arac]
    parcalar.extend(sekil.konumlar)
    parcalar.extend(b for b in sekil.ornek if b not in sekil.degerli)
    return " ".join(parcalar)


def arac_adlari():
    """SEKILLER'deki araclarin kisa adlari (nobetci A1 kolu bunu okur)."""
    return {s.arac.rsplit("/", 1)[-1] for s in SEKILLER}


def bayrak_kumesi(etiket):
    """Bir seklin izinli bayrak kumesi — tuketici ELLE saymaz."""
    return SEKIL_ETIKETLERI[etiket].tum_bayraklar
