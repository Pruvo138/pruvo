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

Hicbir tuketici ikinci bir kopya TUTMAZ. Bir sekil buradan DUSERSE hepsinde birden
duser: cagri REDDEDILIR, adi RED METNINDEN silinir, CARE satiri degisir.

🔴 NOBETCI YOK (ACIK KALEM, 11 Eyl 2026) — burada eskiden ucuncu bir tuketici olarak
serbest-kume-tekkaynak-test.py sayiliyor ve "mutasyonlu, CI'da kosar" deniyordu. O dosya
ca8c3815 ile SILINDI (28 Agu supurmesi); yerine hicbir sey konmadi. Yani "bir sekil
duserse nobetci kirmizi yanar" cumlesi 28 Agu'dan beri YALANDI. Bugun canli olan tek
komsu kol `tools/serbest-kume-ev-ekseni-test.py`dir ve BASKA bir ekseni olcer (EV koku +
kabuk yonlendirme eki); RED METNI / CARE SATIRI turetilmis mi eksenini OLCEN KOD YOK.

Ilgili dersler: [[kapi-red-metni-ikinci-kopyadir]] · [[ikiz-tanim-sessiz-ayrisma]] ·
[[kapinin-menzili-cagri-yeridir]] · [[ucuncu-tekrar-sinif-kapisi]]
"""

# === 🔴 10 EYL 2026 — EV EKSENI: KOK ARTIK SABIT DEGIL, PARAMETRE ==============
# OLCULEN ARIZA (BaBa hukmu 10 Eyl 23:2x, KraL kalem ③; taban bu turda KOSULARAK
# dogrulandi — GERCEK kurulu shim'ler uzerinden, kanonik govde uzerinden DEGIL):
#
#   ev        arac       'defter-rotasyon.py --tavan-kaynaktan'   'tools/... DEVAM.md ...'
#   KraL      VAR        ALLOW                                     ALLOW
#   ArTisT    VAR        DENY   <-- ARIZA                          DENY   <-- ARIZA
#   TeKiN     VAR        DENY   <-- ARIZA                          DENY   <-- ARIZA
#   MaCiT     YOK        (KAPSAM DISI — arac yoklugu)
#   HocA      YOK        (KAPSAM DISI — arac yoklugu)
#
# KOK NEDEN — mekanizma ucundan uca olculdu:
#   `tools/kapi_dagitim.py` kardes evlere bir SHIM kurar; shim yalnizca
#   `mimar-icra-kapisi.py`nin KENDI `REPO_ONEKI` capasini o evin kokune cevirir
#   (`kapi_dagitim.py:CAPA_REPO`). Ama kapi hemen ardindan
#   `DURUM_YOL = SC.DURUM_YOL ...` (mimar-icra-kapisi.py:248-254) diyerek o dogru
#   degerleri BU MODULDEN gelen KraL'a civili yollarla EZIYORDU. Yani shim dogru
#   cevirdigi seyi bu dosya geri aliyordu: ArTisT'in evinde kapi ArTisT'in
#   DEVAM.md'sini degil KraL'inkini bekliyor, cagri TAM ESITLIKTE dusuyor, RED.
#   OLCULEN BEDEL: ArTisT/MaCiT/TeKiN defterlerini UC TURDUR ELLE kisaltti; ArTisT
#   bunu kendi devir blogunda ENGEL olarak yazdi.
#
# SINIF: turetilebilir/canli bir deger ELLE KOPYALANMIS ve kaynagindan AYRISMIS.
# Care TEKIL YAMA DEGIL: kok artik bu tabloda SABIT olarak YASAMAZ — cagri aninda
# PARAMETRE olarak verilir (`eslesen_sekil(..., kok=...)`). Tablonun kendisi TEK
# yerde durur; `eve_gore()` onu saf bir DONUSUMLE yeniden koklendirir, yani ikinci
# bir tablo kopyasi olusmaz ([[ikiz-tanim-sessiz-ayrisma]]).
#
# Ilgili dersler: [[tuketici-yazilirken-tum-okuyucular-sayilir]] ·
# [[kopya-turetilemiyorsa-bayatlik-olculemez]] · [[arac-adi-onek-eslesmesi-komsu-araci-keser]]
import os
import re

# Govdenin KENDI evi. Bu bir "her evin koku" DEGIL, yalnizca (a) tablonun kurulu
# oldugu taban ve (b) ev OLCULEMEDIGINDE dusulecek FAIL-CLOSED degerdir. Olculemeyen
# ev "izinli" sayilmaz: taban kok, cagiran evin agacini ACMAZ, bugunku DAR davranis
# aynen surer ([[olculemedi-bypass-degil-menzil-daraltmasi]]).
KANONIK_KOK = "/Users/okan/dev/pruvo"
REPO_ONEKI = KANONIK_KOK + "/"
CRON_ONEKI = "/Users/okan/.claude/cron/"


def ev_kokleri():
    """Kapali EV KUMESI — TEK KAYNAK `tools/kapi_dagitim.py:EVLER`.

    Burada ELLE bir ev listesi TUTULMAZ; ikinci bir kume sessizce ayrisirdi.
    FAIL-CLOSED: modul yoksa/okunamazsa yalnizca kanonik kok doner (mutant
    dizinlerinde `kapi_dagitim.py` KOPYALANMAZ — orada kume daralir, GENISLEMEZ)."""
    try:
        import kapi_dagitim as _KD
        kokler = {os.path.normpath(k[1]) for k in _KD.EVLER if k and k[1]}
        if kokler:
            return kokler
    except Exception:
        pass
    return {KANONIK_KOK}


def _proje_damgasi(yol):
    """Claude Code proje-dizini damgasi — `mimar_kimlik._proje_damgasi` ile AYNI kural.

    Ayni tek satirlik kural iki yerde yasiyor; ikisi de ayni CI kosumunda olculur
    (`serbest-kume-ev-ekseni-test.py` :: E0) — ayrisirlarsa KIRMIZI yanar."""
    return "".join(k if k.isalnum() else "-" for k in yol)


def ev_koku_turet(damga, kokler=None):
    """🔴 OTURUM DAMGASINDAN (transcript_path) EV KOKU. Eslesme yoksa ``None``.

    NEDEN `transcript_path`, NEDEN `cwd` DEGIL: cwd KAYDIRILABILIR bir sinyaldir
    (`cd <ev>` tek komutluk bir anahtar olurdu); damga oturum ACILIRKEN yazilir ve
    oturumun kostugu hicbir komut onu oynatamaz. Ayni gerekce
    `mimar_kimlik.rol_ekseni`nin bas yorumunda OLCULMUS olarak duruyor.

    🔴 EN UZUN EslESME KAZANIR — ONEK TUZAGI: `-Users-okan-dev-pruvo` damgasi
    `-Users-okan-dev-pruvo-pazarlama`nin ONEKIDIR. Kisa eslesme once alinirsa
    ArTisT'in oturumu KraL'a cozulur ve ariza YER DEGISTIRIR (ayni sinif:
    [[arac-adi-onek-eslesmesi-komsu-araci-keser]]). Bu yuzden TUM adaylar taranir
    ve EN UZUN damga secilir; sinir da denetlenir (tam esitlik ya da damga + '-')."""
    if not isinstance(damga, str) or not damga.strip():
        return None
    if kokler is None:
        kokler = ev_kokleri()
    bilesenler = [b for b in damga.split("/") if b]
    if not bilesenler:
        return None
    en_iyi = None
    for kok in sorted(kokler):
        kok = os.path.normpath(kok)
        adaylar = {_proje_damgasi(kok)}
        try:
            adaylar.add(_proje_damgasi(os.path.realpath(kok)))
        except OSError:
            pass
        for aday in adaylar:
            if not aday:
                continue
            for b in bilesenler:
                if b == aday or b.startswith(aday + "-"):
                    if en_iyi is None or len(aday) > en_iyi[0]:
                        en_iyi = (len(aday), kok)
    return None if en_iyi is None else en_iyi[1]

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
HAFIZA_ARSIVLE_YOL = REPO_ONEKI + "tools/hafiza-indeks-arsivle.py"
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
    # 🔴 9 EYL 2026 (kalem ①): `--sha-dogrula` SALT-OKUR bir DOGRULAMA kolu ve
    # MIMARIN ELINDE SERBEST olmasi gerekir — BaBa'nin HAFTALIK korumali-blok
    # supurmesi bloklari ELLE tasitir, o tasimanin kayipsizligini olcen tek kol
    # budur. Tabloya yazilmazsa kapinin "once olc" dedigi komut ana oturumda
    # REDDEDILIRDI ([[kapi-red-metni-ikinci-kopyadir]] — `--kapanislari-isle`
    # 28 Agu'da tam bu sebeple eklenmisti).
    Sekil("kutu-arsivle", KUTU_ARSIVLE_YOL,
          serbest=("--kuru", "--kapanislari-isle", "--sha-dogrula")),

    # 🔴 5 EYL 2026 (K366): HAFIZA INDEKSI (MEMORY.md) BAKIMI. Kota kapisinin
    # ucuncu ekseni tavan ustunde CARE olarak TAM BU CAGRIYI basar; sekil buraya
    # YAZILMAZSA kapi, ana oturumda KOSULAMAYAN bir care vaat ederdi (K319/K332
    # sinifi, [[kapi-red-metni-ikinci-kopyadir]]). Konumsal arguman ALMAZ —
    # yollarin tek kaynagi aracin kendisidir (HAFIZA_VARSAYILAN/ARSIV_VARSAYILAN).
    Sekil("hafiza-arsivle", HAFIZA_ARSIVLE_YOL, serbest=("--kuru",)),

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
    # okuyan SALT-OKUR arac. Konumsal arguman ALMAZ; tek bayragi `--kendini-test`
    # DISARIDADIR (kabul kosumu). Mimar elinde SERBEST olan BAYRAKSIZ haldir:
    # Okan'in "terminale girmeden soracagim bir sey yap" emri (28 Agu); taban canli
    # ONARIM/GOZCU/KIRMIZI sayilarini cevap olarak verir. Guvenli: dosya DEGISTIRMEZ,
    # aga cikmaz, LLM/agent turu acmaz — bu yuzden mimar katinda serbest birakilmasi
    # SAKINCALI degil.
    Sekil("onarim-durum", ONARIM_DURUM_YOL),
)

SEKIL_ETIKETLERI = {s.etiket: s for s in SEKILLER}


# === 🔴 10 EYL 2026 — TABLOYU BASKA BIR EVE KOKLENDIR (SAF DONUSUM) ===========
def _yeniden_kokle(yol, kok):
    """Kanonik koke bagli bir yolu BASKA bir eve tasir; disaridakine DOKUNMAZ."""
    if not yol.startswith(REPO_ONEKI):
        return yol                       # repo DISI (cron) — ev degistirmez
    return kok.rstrip("/") + "/" + yol[len(REPO_ONEKI):]


def eve_gore(kok=None):
    """SEKILLER tablosunun `kok` evine koklendirilmis hali (tuple).

    🔴 IKINCI TABLO DEGIL: tek tablonun SAF DONUSUMUDUR. Bir sekil kaynaktan
    duserse burada da duser — ayrisma YAPISAL OLARAK imkansiz
    ([[ikiz-tanim-sessiz-ayrisma]]). `kok` yoksa/kanonikse tablo AYNEN doner."""
    if not kok:
        return SEKILLER
    kok = os.path.normpath(kok)
    if kok == KANONIK_KOK:
        return SEKILLER
    return tuple(
        Sekil(s.etiket, _yeniden_kokle(s.arac, kok),
              konumlar=tuple(_yeniden_kokle(k, kok) for k in s.konumlar),
              zorunlu=s.zorunlu, serbest=s.serbest, degerli=s.degerli,
              ornek=s.ornek, repo_disi=s.repo_disi)
        for s in SEKILLER
    )


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
        "--beyan-dosya": "deger YOL alir — yedek dusus beyanini DEGISTIRIR (fikstur "
                         "kolu; canli beyan yolu `yedekle.py`den TURETILIR)",
        # Sayisal ayar bayraklari: esikleri ELLE oynatir.
        "--tavan": "tavani ELLE verir — esigi oynatir",
        "--koru": "korunan kalem sayisini ELLE verir",
        "--su-seviye-orani": "su seviyesi oranini ELLE verir",
        "--arsiv-kuyruk": "arsiv kuyruk boyunu ELLE verir",
    },

    HAFIZA_ARSIVLE_YOL: {
        # Deger alan YOL bayraklari: repo-disi yol tasima anahtari olurlardi.
        "--hafiza": "deger YOL alir — indeks dosyasini DEGISTIRIR",
        "--arsiv": "deger YOL alir — arsiv dosyasini DEGISTIRIR",
        "--kilit": "deger YOL alir — kilit dosyasini DEGISTIRIR",
        # Esikleri ELLE oynatanlar: kapinin okudugu TEK KAYNAGI bypass eder.
        "--tavan-bayt": "tavani ELLE verir — sahipten turetmeyi bypass eder",
        "--tavan-satir": "tavani ELLE verir — sahipten turetmeyi bypass eder",
        "--su-seviye-orani": "su seviyesi oranini ELLE verir",
        "--tarih": "arsiv baslik tarihini ELLE verir — fikstur/test kolu",
    },

    CIP_BEKCI_YOL: {},

    # `onarim-durum.py` SALT-OKUR: konumsal arguman YOK. TEK bayragi
    # `--kendini-test`tir (K347, 28 Agu 2026) ve DISARIDADIR: kabul kosumu,
    # isci kosturur. Mimarin serbest cagrisi BAYRAKSIZ haldir.
    ONARIM_DURUM_YOL: {
        "--kendini-test": "kabul kosumu — mimar elinde degil, isci kosturur",
    },
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


# === 🔴 10 EYL 2026 — IKINCI EKSEN: KABUK YONLENDIRME EKI ====================
# OLCULEN ARIZA (ANA oturumda, EV EKSENINDEN AYRI — ayni dosyada yasayan IKINCI
# kor nokta; tek yama ikisini birden kapatmaz):
#   `python3 tools/defter-rotasyon.py --tavan-kaynaktan`        -> GECTI
#   `python3 tools/defter-rotasyon.py --tavan-kaynaktan 2>&1`   -> RED
# Yani serbest listede BIREBIR yazili olan komut, kabuk yonlendirme eki yuzunden
# reddediliyordu.
#
# MEKANIZMA (tahmin degil — `segmentlere_ayir` + `parcala` ile OLCULDU):
# kapinin segmentleyicisi '&' uzerinden boler, bu yuzden `... --tavan-kaynaktan 2>&1`
# IKI parcaya duser:  ['python3','tools/defter-rotasyon.py','--tavan-kaynaktan','2>']
# ve yetim bir ['1'] segmenti. Yetim segment ZARARSIZ (olculdu: 'git status 2>&1',
# '1' -> ALLOW). Suclu TEK sey, '-' ile baslamadigi icin KONUMSAL ARGUMAN sayilan
# '2>' ARTIGIDIR: konum sayisi sismis olur ve sekil TAM ESITLIKTE duser.
#
# 🔴 KAPI DELINMEDI — NORMALIZE EDILEN KUME OLCUMLE SECILDI, TAHMINLE DEGIL:
# yalnizca DOSYA ADI TASIMAYAN, SEGMENTIN SONUNDAKI fd-cogaltma artigi soyulur
# ('2>&1' -> '2>' · '1>&2' -> '1>' · '>&2' -> '>'). Bunlar hicbir yere YAZMAZ.
# Olculen ve BILEREK RED BIRAKILAN formlar:
#   '2>/dev/null' -> tek token '2>/dev/null' (YOL tasir)      -> RED KALIR
#   '> /tmp/x'    -> ['>', '/tmp/x'] ('>' SON token DEGIL)    -> RED KALIR
#   '>/tmp/x'     -> tek token '>/tmp/x' (YOL tasir)          -> RED KALIR
# '>' yonlendirme ve '$(...)' / '$VAR' yasaklari `tools/komut-stili-kapisi.py`nin
# AYRI hukmudur ve DELINMEDI (o kapi '2>&1'i zaten muaf tutar: `(?<![0-9<>])>(?!&)\s`).
_YONLENDIRME_ARTIGI = re.compile(r"^\d*>$")


def yonlendirme_ekini_soy(argumanlar):
    """SEGMENT SONUNDAKI fd-cogaltma artigini soyar. Baska HICBIR seyi soymaz.

    Yalnizca SON token ve yalnizca `^\\d*>$` kalibi: dosya adi tasiyan hicbir
    yonlendirme bu kalibi tutturamaz."""
    if len(argumanlar) >= 2 and _YONLENDIRME_ARTIGI.match(argumanlar[-1]):
        return argumanlar[:-1]
    return argumanlar


def eslesen_sekil(argumanlar, coz, cwd, kok=None):
    """python3 SONRASINDAKI tokenlari SEKILLERE karsi cozer.

    Doner: eslesen Sekil, yoksa None (fail-closed).
    `coz(yol, cwd)` cagirana aittir — yol cozumu IKINCI KEZ yazilmaz
    ([[ikiz-tanim-sessiz-ayrisma]]).

    `kok`: cagiran EVIN koku. Verilmezse tablo KANONIK evde kalir — yani
    olculemeyen ev bugunku DAR davranisi alir, GENIS degil.

    Dizge eslemesi YAPILMAZ: arac ve konumlar COZULMUS MUTLAK yolla TAM ESITLIK
    ile karsilastirilir ([[n2b-kapisi-dizge-olcer]]). '=' li yazim (--tavan-sayi=130)
    hicbir kumeye TAM ESIT olmadigi icin RED kalir.
    """
    if not argumanlar:
        return None
    argumanlar = yonlendirme_ekini_soy(list(argumanlar))
    if not argumanlar:
        return None
    arac_cozulmus = coz(argumanlar[0], cwd)
    adaylar = [s for s in eve_gore(kok) if s.arac == arac_cozulmus]
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
def _kisa(yol, kok=None):
    """Mutlak yolu okunur kisa ada indirger (repo -> 'tools/x.py', cron -> '~/...').

    `kok` verilirse O EVIN oneki de soyulur: ArTisT'in evinde metin
    '/Users/okan/dev/pruvo-pazarlama/tools/...' degil 'tools/...' basar."""
    if kok:
        ev_oneki = os.path.normpath(kok).rstrip("/") + "/"
        if yol.startswith(ev_oneki):
            return yol[len(ev_oneki):]
    if yol.startswith(REPO_ONEKI):
        return yol[len(REPO_ONEKI):]
    if yol.startswith(CRON_ONEKI):
        return "~/.claude/cron/" + yol[len(CRON_ONEKI):]
    return yol


def sekil_metni(sekil, kok=None):
    """TEK bir seklin insan-okur cagri metni ('python3 tools/x.py A B [--f]')."""
    parcalar = ["python3 " + _kisa(sekil.arac, kok)]
    parcalar.extend(_kisa(k, kok) for k in sekil.konumlar)
    parcalar.extend(sorted(sekil.zorunlu))
    parcalar.extend("[" + b + "]" for b in sorted(sekil.serbest))
    parcalar.extend("[" + b + " <deger>]" for b in sorted(sekil.degerli))
    return " ".join(parcalar)


def serbest_python_metni(kok=None):
    """RED metninde gecen SERBEST cagri listesi — SEKILLER'den TURETILIR.

    Bir sekil kumeden DUSERSE hem cagri REDDEDILIR hem de bu metinden DUSER; ikisi
    ayni yapidan beslendigi icin AYRISAMAZLAR ([[kapi-red-metni-ikinci-kopyadir]]).

    `kok`: KARAR hangi eve gore veriliyorsa METIN de o eve gore uretilir — ikisi
    AYRI koke baglanirsa metin yine ikinci kopya olurdu."""
    return " · ".join("'" + sekil_metni(s, kok) + "'" for s in eve_gore(kok))


def cagri_ornegi(etiket, kok=None):
    """CARE satirlari icin CALISTIRILABILIR ornek komut (MUTLAK yollarla).

    `defter-kota-kapisi.py` bu fonksiyonu cagirir; CARE metnini ELLE YAZMAZ. Deger
    alan bayraklar ornege GIRMEZ (degerleri cagri anina aittir).

    `kok`: CARE, okuyanin KENDI evinde kosabilecegi bir komut basmali — kapinin
    onerdigi carenin o evde REDDEDILMESI K319/K332 sinifidir
    ([[kapi-red-metni-ikinci-kopyadir]])."""
    sekil = {s.etiket: s for s in eve_gore(kok)}[etiket]
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
