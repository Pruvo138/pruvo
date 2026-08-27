#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-kota-kapisi.py — defter + ORTAK POSTA KUTUSU kota kapisi.

Kullanim:
    python3 tools/defter-kota-kapisi.py [depo-koku]
    python3 tools/defter-kota-kapisi.py --kendini-test

IKI YUZEY, TEK KAPI (K253, 20 Agu 2026):
    (A) DEFTER ekseni — repo ICINDEKI DEVAM.md (K178 + K195b).
    (B) KUTU ekseni   — repo DISINDAKI ortak posta kutusu
        `~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md`.

🔴 KUTU EKSENI NEDEN BURAYA EKLENDI (SINIF, 3. TEKRAR — olculdu):
Kutu esigi 19 Agu'da elle 333 -> 245 satira indirildi, ertesi gun 363'e cikti.
Her hafta ayni el isi. SEBEP: kota kapisi pre-commit'te kosuyor ve YALNIZ
DEVAM.md'yi olcuyordu; kutu repo DISINDA duruyor -> yalniz kutu buyudugunde
HICBIR kapi tetiklenmiyordu, tasma ancak insan bakinca goruluyordu. Tekil budama
YASAK ([[ucuncu-tekrar-sinif-kapisi]]) -> IKINCI BIR ESIK SAHIBI ACILMADI, AYNI
kapi kutuyu da MUTLAK YOLLA olcuyor.

🔴 KUTUNUN ZATEN BIR KAPISI VARDI — AMA CAGIRANI YOKTU (olculdu, 20 Agu):
`tools/kutu-esik-kapisi.py` (K188) kutuyu tavana gore olcer, rotasyonu tetikler,
indiremezse yazmayi REDDEDER; 11 vaka + 8 mutantla CI'da YESIL. Yine de kutu
tasmaya devam etti, cunku o kapi bir **PreToolUse** kancasidir ve kablosu
`.claude/settings.json`tedir — o dosya GITIGNORE'DA, yani kablo COMMIT EDILEMEZ ve
bu makineye hic kurulmamisti (`tools/paket-k188-kanca-kablolamasi.md`: "kapı
main'de ama CANLI DEĞİL"). Kapi yesil, menzil BOS
([[kapinin-menzili-cagri-yeridir]]). K253'un farki cagri yeridir: kutu ekseni
COMMIT'LENEBILEN ve her makinede `tools/kanca-kur.py` ile kurulan
`tools/kancalar/pre-commit` adim 8'e baglidir. Iki kapi CAKISMAZ — biri YAZMA
yolunda (kurulursa), digeri COMMIT yolunda; ikisi de AYNI tavan sahibinden okur.

🔴 KUTU TAVANI TURETILIR, YAZILMAZ: kutunun mevcut tavan sahibi
`tools/kutu-arsivle.py::VARSAYILAN_TAVAN`dir (LOSSLESS rotasyon araci onu
kullanir). Kapi o sayiyi SAHIPTEN okur. Kapi ile arac ayni sayidan beslenmezse
kapi "asildi" derken arac "is yok" derdi = sessiz ayrisma.

🔴 KAPI KUTUYU OKUR, ASLA YAZMAZ/KIRPMAZ: kutu bir HAFIZA dosyasidir. Otomatik
silme YASAK; kapi yalnizca CARE satiri basar, LOSSLESS tasimayi insan ya da
rotasyon araci (`tools/kutu-arsivle.py`) yapar — hicbir sey silinmez, en eski
bloklar `*-arsiv.md`'ye TASINIR.

KUTU HUKUM KOVALARI (BES KOVA — ucuncu kovanin yutulmamasi icin AYRI jetonlar,
[[iki-kovali-siniflama-ucuncu-sinifi-yutar]]):
    KUTU_SAHIPSIZ     rc 0  — <kok>/tools/kutu-arsivle.py YOK. Bu checkout kutuyu
                              SAHIPLENMIYOR (sentetik fikstur deposu, kardes depo).
    KUTU_MAKINEDE_YOK rc 0  — sahip VAR ama kutunun HAFIZA DIZINI bu makinede HIC
                              yok (GitHub kosucusu). Kusur DEGIL, kapsam disi.
    KUTU_OLCULEMEDI   rc 1  — hafiza dizini VAR ama kutu dosyasi yok/okunamiyor,
                              ya da sahip modul/tavan/yol cozulemedi. FAIL-CLOSED:
                              "bakamadim" YESIL DEGILDIR.
    KUTU_ASILDI       rc 1  — olculdu, tavan asildi VE rotasyon araci hala is
                              yapabiliyor. CARE satiri basilir.
    KUTU_YESIL        rc 0  — olculdu, tavanin altinda.
    KUTU_TAVAN_USTU_KORUMA_NEDENIYLE
                      rc 0  — (K318 KOL-3) tavan asildi AMA sahip arac
                              `HUKUM=KORUMA_TUTTU` + `tasinabilir=0` diyor: bekleyen
                              kapanis blogu rotasyona GIRMEZ, yani yapilacak is YOK.
                              Hal GIZLENMEZ, sayilariyla BASILIR; commit BLOKLANMAZ.
    KUTU_HUKUM_ALINAMADI
                      rc 1  — (K318 KOL-3) tavan asildi ve sahip aracin HUKMU
                              ALINAMADI (arac kosmadi / sifir-disi rc / jeton yok).
                              FAIL-CLOSED: fail-open bu kolda YASAK.

🔴 K318 KOL-3 — KAPI HUKMU TUKETIR, SATIRI TEK BASINA OKUMAZ (27 Agu 2026):
Olculen delik: kutu 518 satir (tavan 300) iken `kutu-arsivle.py` `HUKUM=KORUMA_TUTTU`
`tasinabilir=0` basiyordu — arac "yapilacak is YOK, bu BILINCLI bir duraklama" hukmunu
vermisti. Kapi o hukmu HIC OKUMUYORDU: yalnizca 518 > 300 diye TEK GUNDE DORT ayri
commit'i durdurdu, iki dal (13 dosya) commit'lenemedi. Iki karar mercii ayni olguya
bakip celisiyordu ([[ayni-alan-iki-hukum-biri-sessiz]]). Celiski ARACIN HUKMU LEHINE
kapatildi — kapi tavani da tavan SAHIBINDEN okuyor, hukmu de SAHIPTEN okur.

🔴 EKSEN `kok`TUR: sahip dosyasi YARGILANAN DEPO KOKUNDEN cozulur, kapinin kendi
konumundan DEGIL. Aksi halde sentetik fikstur depolarini yargilarken de GERCEK
makinenin kutusu olculur ve komsu kabul testleri ambiyans yuzunden kirmiziya
yanardi ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).

TEK KAYNAK NOBETI (K253 M2): kota ekseni dosyalarinda esik DEGERININ ikinci bir
sabite KOPYALANMASI RED'dir. Sahipli olanlar disinda modul duzeyinde ayni sayiyi
tasiyan bir tamsayi atamasi bulunursa kapi KIRMIZI yanar.

DEFTER EKSENI (IK EKSEN, pre-commit; K178 + K195b):
    * DEVAM.md INDEX'te (staged) yoksa: **SESSIZCE GECMEZ** (K195b, 19 Agu).
      INDEX blob'u yine de OLCULUR ve hukum adiyla basilir —
      `KAPSAM_DISI_OLCULDU ... ASIM=YOK` / `KAPSAM_DISI_ASIM` (sayaca yazilir) /
      `KAPSAM_DISI_OLCULEMEDI` + sebep. Her uc halde de defter kolu 0 doner: bu
      commit defteri DEGISTIRMIYOR, durdurmak kapsam disi olurdu.
    * DEVAM.md INDEX'te varsa ve (satir > 130 VEYA bayt > 12288) ise:
        - stderr'e iki satirlik RED mesaji basar (ASAN_EKSEN=...).
        - sayac dosyasina `RED` satiri yazar.
        - defter kolu 1 doner.

    TAVAN DEGERLERI: tools/defter-kota-taban.py'dan okunur (TEK KAYNAK).
    Aşan eksen stderr'de adıyla yazılır (SATIR/BAYT/IKISI).

🔴 BYPASS KOLU (`--bypass-kontrol`, pre-push'ta cagrilir) — NEDEN AYRI VAR:
`--no-verify` ile atlanan bir kanca HIC KOSMAZ, yani kendi atlanisini KAYDEDEMEZ.
"RED sayisi" bypass sayisi DEGILDIR (RED, kapinin CALISTIGI haldir). Bypass ancak
SONUCUNDAN anlasilir: kota asilmis bir DEVAM.md **commit'lenmis** ve push'a gelmisse,
kapi ya atlanmistir ya hic kosmamistir. Bu kol o hali sayar:
    * HEAD'deki DEVAM.md (satir > 130 VEYA bayt > 12288) ise sayac dosyasina
      `BYPASS` satiri yazar.
    * 🔴 BLOKLAMAZ (her zaman exit 0): Okan hukmu "yasaklanamaz ama SAYILIR".
Sayac repo DISINDADIR (`~/.claude/cron/defter-kota-bypass.tsv`) — commit'e girmez,
gunluk 15:00 olcumune `DEFTER_KOTA_BYPASS` ekseni olarak okunur.

CI'da (nobet.yml) yalniz `--bypass-kontrol` kolu kosar; ZORLAYICI hukum
kancalar/pre-commit adim 8'dedir (INDEX) + kancalar/pre-push (bypass).

KENDINI-TEST (--kendini-test):
    * Sentetik fiksturlerle M1 (BAYT asimi) + M2 (SATIR asimi) + 2 KONTROL
      (ikisi de tavan altinda, tam tavanda) + M3 (byte kolu mutanti) + M4
      (byte karak olarak sayisi) kosar. Cıktı son satırı:
          FIKSTUR=<n>/<n> MUTANT=<n>/<n>
          DUSEN=<n>
    * Tum vakalar yesil ise DUSEN=0, rc=0.
    * KUTU ekseninin kabul/mutant tablosu AYRI dosyadadir (tally karistirilmadi):
          python3 tools/kutu-kota-kapisi-test.py
"""
import ast
import datetime
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

# Tek kaynaktan türet: tools/defter-kota-taban.py (kebab-case repo kurali;
# importlib ile yukle). Ikiz [[ikiz-tanim-sessiz-ayrisma]] kapatir.
import importlib.util as _ilu
_TABAN_YOL = os.path.join(TOOLS, "defter-kota-taban.py")
_tab = _ilu.spec_from_file_location("defter_kota_taban", _TABAN_YOL)
_mod = _ilu.module_from_spec(_tab)
_tab.loader.exec_module(_mod)
TAVAN_SATIR = _mod.TAVAN_SATIR
TAVAN_BAYT = _mod.TAVAN_BAYT
tavan_asi_mi = _mod.tavan_asi_mi

SAYAC_YOLU = os.environ.get("PRUVO_DEFTER_KOTA_SAYAC",
                            os.path.expanduser("~/.claude/cron/defter-kota-bypass.tsv"))

# --- KUTU EKSENI JETONLARI (BES KOVA; hicbiri digerini YUTMAZ) -------------
# 🔴 JETONLARDA `KAPSAM_DISI` GECMEZ: defter ekseninin K195b jetonlari o dizeyi
# tasiyor ve komsu kabul testi (defter-kota-kapsam-disi-test.py :: K1/K2) tam
# olarak "ciktida KAPSAM_DISI GECMEMELI" diye olcuyor. Ayni dizeyi kutu kolunda
# kullanmak o testi ambiyansla kirmiziya yakardi.
KUTU_SAHIPSIZ = "KUTU_SAHIPSIZ"
KUTU_MAKINEDE_YOK = "KUTU_MAKINEDE_YOK"
KUTU_OLCULEMEDI = "KUTU_OLCULEMEDI"
KUTU_ASILDI = "KUTU_ASILDI"
KUTU_YESIL = "KUTU_YESIL"

# --- K318 KOL-3: TAVAN USTU ama SEBEBI KORUMA olan hal (iki AYRI jeton) ----
# 🔴 Bu iki jeton yukaridaki BES KOVANIN ICINE DUSURULEMEZ: "tavan asildi ve
# yapilacak is var" ile "tavan asildi ama arac ISI KASITLI OLARAK yapmiyor"
# AYNI SEY DEGILDIR ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]). Ilkinde
# commit'i durdurmak dogru (birinin rotasyonu kosturmasi gerek), ikincisinde
# durdurmak Okan kurali ⑤'in bedelini masum bir commit'e odetmektir.
KUTU_KORUMA_USTU = "KUTU_TAVAN_USTU_KORUMA_NEDENIYLE"
KUTU_HUKUM_ALINAMADI = "KUTU_HUKUM_ALINAMADI"

KUTU_RC = {
    KUTU_SAHIPSIZ: 0,
    KUTU_MAKINEDE_YOK: 0,
    KUTU_OLCULEMEDI: 1,
    KUTU_ASILDI: 1,
    KUTU_YESIL: 0,
    KUTU_KORUMA_USTU: 0,
    KUTU_HUKUM_ALINAMADI: 1,
}

# Kota ekseninde esik sabiti TASIMASINA IZIN VERILEN (dosya, ad) ciftleri.
# Baska her yerde ayni SAYI'yi tasiyan modul-duzeyi tamsayi atamasi = ikinci
# esik sahibi = TEK KAYNAK IHLALI.
KOTA_EKSENI_DOSYALARI = (
    "defter-kota-taban.py",
    "defter-kota-kapisi.py",
    "defter-rotasyon.py",
    "kutu-arsivle.py",
    "kutu-esik-kapisi.py",
)
ESIK_SAHIPLERI = frozenset({
    ("defter-kota-taban.py", "TAVAN_SATIR"),
    ("defter-kota-taban.py", "TAVAN_BAYT"),
    ("kutu-arsivle.py", "VARSAYILAN_TAVAN"),
})


def _git(args, kok):
    r = subprocess.run(["git", "-C", kok] + list(args),
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def _devam_stage_de(kok):
    rc, out, _ = _git(["diff", "--cached", "--name-only",
                        "--diff-filter=ACMR", "-z"], kok)
    if rc != 0:
        return None  # OLCULEMEDI
    return "DEVAM.md" in (out.split("\0") if out else [])


def _devam_index_ham(kok):
    """DEVAM.md'nin INDEX blob'unu ham bayt olarak okur.

    UTF-8 bayt sayisi len(ham) ile; satir sayisi splitlines() ile.
    """
    rc, out, _ = _git(["cat-file", "blob", ":DEVAM.md"], kok)
    if rc != 0:
        return None
    if isinstance(out, str):
        return out.encode("utf-8")
    return out


def _devam_olcu_index(kok):
    """(satir, bayt) — biri None ise OLCULEMEDI."""
    ham = _devam_index_ham(kok)
    if ham is None:
        return None, None
    return len(ham.splitlines()), len(ham)


def _sayaç_yaz(kok, satir, bayt, sinif="RED"):
    """Sayac satiri: <ISO>\\t<sinif>\\t<depo>\\t<satir>\\t<bayt>."""
    try:
        os.makedirs(os.path.dirname(SAYAC_YOLU), exist_ok=True)
        with open(SAYAC_YOLU, "a", encoding="utf-8") as f:
            f.write("%s\t%s\t%s\t%d\t%d\n" % (
                datetime.datetime.now().isoformat(), sinif, kok, satir, bayt))
        return True
    except Exception:                                       # noqa: BLE001
        return False


def _devam_head_olcu(kok):
    rc, out, _ = _git(["cat-file", "blob", "HEAD:DEVAM.md"], kok)
    if rc != 0:
        return None, None
    ham = out.encode("utf-8") if isinstance(out, str) else out
    return len(ham.splitlines()), len(ham)


def bypass_kontrol(kok):
    """PUSH kolu — kota asilmis bir DEVAM.md commit'lenmisse BYPASS say. BLOKLAMAZ.

    🔴 Neden bloklamiyor: Okan hukmu "`--no-verify` yasaklanamaz ama SAYILIR".
    Bloklamak, kapiyi zaten atlamis birine ikinci bir duvar cikarmak olurdu; olculen
    ihtiyac SAYIDIR (gunluk 15:00 olcumun `DEFTER_KOTA_BYPASS`)."""
    satir, bayt = _devam_head_olcu(kok)
    if satir is None:
        # Defteri olmayan depo (kardes evler) ya da okunamadi -> sessiz gec, BLOKLAMA.
        return 0
    asi, eksen, _, _ = tavan_asi_mi(satir, bayt)
    if asi:
        _sayaç_yaz(kok, satir, bayt, sinif="BYPASS")
        print("!! DEFTER KOTASI BYPASS SAYILDI — HEAD'deki DEVAM.md %d satir / "
              "%d bayt (tavan satir=%d bayt=%d, ASAN_EKSEN=%s). Push DURDURULMADI, "
              "yalnizca sayildi: %s"
              % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT, eksen, SAYAC_YOLU),
              file=sys.stderr)
    return 0


def _kapsam_disi_olc(kok):
    """K195(b) — DEVAM.md stage'de DEGILKEN de OLCER; sessizce gecmez.

    OLCULEN DELIK (19 Agu 2026): eski kol burada ciplak `return 0` doner ve
    kapinin yesili "olctum, temiz" degil "BAKMADIM" demekti. Kapi HIC olcmeden
    yesil donerse kota asimi kapinin GOZUNDEN kacar; elle rotasyon dongusu
    (bir gunde 4 kez) tam da bu koru noktada yasadi.

    YENI DAVRANIS (iki hal, ikisi de SESSIZ DEGIL):
      * INDEX blob'u okunabiliyorsa OLCULUR ve hukum ADIYLA basilir.
        - Asim VARSA: `KAPSAM_DISI_ASIM` sinifiyla sayaca yazilir + stderr.
        - Asim YOKSA: `KAPSAM_DISI_OLCULDU ... ASIM=YOK` stdout'a basilir.
      * Blob okunamiyorsa `KAPSAM_DISI_OLCULEMEDI` + SEBEP basilir.

    🔴 BLOKLAMA SEMANTIGI DEGISMEDI (her zaman 0): bu commit defteri
    DEGISTIRMIYOR; onu durdurmak kapinin kapsami disidir. Okan doktrini
    (`bypass_kontrol` ile ayni): "yasaklanamaz ama SAYILIR". Burada olculen
    sey commit'in kendisi degil, deftere BAKILDIGI gercegidir.
    """
    satir, bayt = _devam_olcu_index(kok)
    if satir is None:
        print("!! KAPSAM_DISI_OLCULEMEDI — DEVAM.md stage'de yok VE INDEX blob'u "
              "okunamadi. SEBEP: `git cat-file blob :DEVAM.md` sifir-disi dondu "
              "(defter izlenmiyor ya da depo kokü yanlis: %s). Kota OLCULMEDI."
              % kok, file=sys.stderr)
        return 0

    asi, eksen, _, _ = tavan_asi_mi(satir, bayt)
    if asi:
        _sayaç_yaz(kok, satir, bayt, sinif="KAPSAM_DISI_ASIM")
        # Jeton ALT CIZGILI ve sayac sinifiyla AYNI ("KAPSAM_DISI_ASIM"):
        # bu satirlar grep'lenir; bosluklu "KAPSAM DISI" yazmak jetonu
        # makine-aranamaz yapar (K195b kabulunde V2 bu yuzden kirmizi yandi).
        print("!! KAPSAM_DISI_ASIM — DEFTER KOTASI ASILDI ama DEVAM.md bu commit'te "
              "stage'de DEGIL. INDEX blob'u %d satir / %d bayt (tavan satir=%d "
              "bayt=%d, ASAN_EKSEN=%s). Commit DURDURULMADI (defteri "
              "degistirmiyor), yalnizca SAYILDI: %s"
              % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT, eksen, SAYAC_YOLU),
              file=sys.stderr)
        return 0

    print("KAPSAM_DISI_OLCULDU satir=%d bayt=%d tavan_satir=%d tavan_bayt=%d ASIM=YOK"
          % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT))
    return 0


def _hukum_red(satir, bayt, eksen, kok):
    """RED ciktisi; sayac yaz + 1 dondur (defter kolu)."""
    print("!! DEFTER KOTASI ASILDI — DEVAM.md %d satir / %d bayt "
          "(tavan satir=%d bayt=%d, ASAN_EKSEN=%s)."
          % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT, eksen), file=sys.stderr)
    # 🔴 CARE'IN ESKI HALI CALISMIYORDU (K195, 19 Agu — 4. tekrar): bayraksiz
    # cagri TEK GECIS yapar, tavani HIC OKUMAZ. Kapali madde kalmadiginda
    # "TASINAN=0" deyip rc=0 ile cikiyor, defter ise tavanin USTUNDE kaliyordu;
    # sonuc her oturumda ELLE cumle budamaktı. Tavanli + isaretciye indirmeli
    # bicim yaziliyor ve tavan sayisi komuta ELLE YAZILMIYOR (--tavan-kaynaktan
    # ayni TEK KAYNAKTAN okur; yordama yazilan sayi ikinci kopya olurdu).
    print("!! CARE: python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py "
          "/Users/okan/dev/pruvo/DEVAM.md /Users/okan/dev/pruvo/DEVAM-ARSIV.md "
          "--tavan-kaynaktan --isaretciye-indir", file=sys.stderr)
    print("!!   (K258, 20 Agu: bu cagri artik MIMARIN elinde de SERBEST — kapinin "
          "adlandirilmis DEFTER BAKIMI kovasi iki bayragi TAM ESITLIKLE gecirir. "
          "Kume disi bayrak (--tavan-sayi / --tarih) RED kalir.)", file=sys.stderr)
    _sayaç_yaz(kok, satir, bayt)
    return 1


# ---------------------------------------------------------------------------
# KUTU EKSENI (K253) — SAF HUKUM + IO KOLU
# ---------------------------------------------------------------------------
def kutu_hali(sahip_var, dizin_var, dosya_var, satir, tavan):
    """SAF fonksiyon: BES kovadan birini dondurur. IO YOK, ortam YOK.

    Ana yol ve kabul testi AYNI fonksiyonu cagirir — ikiz tanim ACILMAZ
    ([[ikiz-tanim-sessiz-ayrisma]]). Kovalar sirayla ELENIR ve hicbiri
    digerini YUTMAZ ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]):

      1. sahip YOK              -> KUTU_SAHIPSIZ      (bu checkout kutuyu sahiplenmiyor)
      2. sahip var, DIZIN yok   -> KUTU_MAKINEDE_YOK  (kosucu/kardes makine)
      3. dizin var, DOSYA yok   -> KUTU_OLCULEMEDI    (FAIL-CLOSED, gercek kusur)
      4. olculdu, satir > tavan -> KUTU_ASILDI
      5. olculdu, satir <= tavan-> KUTU_YESIL

    🔴 3. KOVA 2.'NIN ICINE DUSURULEMEZ: "dosya yok" ile "makinede hic yok"
    ayni sey degildir. Ilki kutunun SILINMESI/YENIDEN ADLANDIRILMASIDIR ve
    kapinin gormesi gereken tam da odur.
    """
    if not sahip_var:
        return KUTU_SAHIPSIZ
    if not dizin_var:
        return KUTU_MAKINEDE_YOK
    if not dosya_var or satir is None or tavan is None:
        return KUTU_OLCULEMEDI
    if satir > tavan:
        return KUTU_ASILDI
    return KUTU_YESIL


def _jeton_degeri(ham, onek):
    """Cikti metninde `<onek><deger>` bicimindeki BOSLUKLA AYRILMIS jetonu okur.

    Tam eslesmeli onek arar (`tasinabilir=` -> `tasinabilir=3`); satir icinde
    nerede durdugu onemsizdir. Bulunamazsa None — "okuyamadim" 0 DEGILDIR.
    """
    for satir in ham.splitlines():
        for parca in satir.split():
            if parca.startswith(onek):
                return parca[len(onek):]
    return None


def kutu_hukmu_al(sahip_yolu, kutu_yolu, calistir=None):
    """(hukum, tasinabilir, korumali, ham, hata) — SAHIP ARACIN KURU KOSUMUNDAN.

    🔴 K318 KOL-3 — KAPI ARTIK SATIR SAYISINA TEK BASINA BAKMAZ. Olculen delik
    (27 Agu): kutu tavanin ustundeydi, `kutu-arsivle.py` `HUKUM=KORUMA_TUTTU`
    `tasinabilir=0` diyordu — yani arac "yapilacak is YOK, bu bilincli bir
    duraklama" hukmunu vermisti — ama kapi o hukmu HIC OKUMUYORDU ve yalnizca
    518 > 300 diye DORT ayri commit'i durdurdu. Iki karar mercii ayni olguya
    bakip celisiyordu; celiskiyi kapatmanin dogru yonu, HUKMU TUKETMEKTIR
    ([[ayni-alan-iki-hukum-biri-sessiz]]).

    🔴 FAIL-CLOSED: hukum ALINAMAZSA (arac kosmadi / sifir-disi rc / jeton yok)
    bu fonksiyon HATA dondurur ve cagiran BLOKLAR. "Olcemedim" YESIL DEGILDIR
    ([[olculemedi-bypass-degil-menzil-daraltmasi]]); fail-open bu kolda YASAK.

    `calistir`: kabul testinin arac kosumunu DEGISTIRMEDEN gozleyebilmesi icin
    enjeksiyon noktasi (varsayilan: gercek subprocess).
    """
    if calistir is None:
        def calistir(komut):
            return subprocess.run(komut, capture_output=True, text=True, timeout=180)
    komut = [sys.executable, sahip_yolu, "--kutu", kutu_yolu, "--kuru"]
    try:
        r = calistir(komut)
    except Exception as e:                                    # noqa: BLE001
        return None, None, None, "", "sahip arac KOSTURULAMADI: %s" % e
    ham = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        return None, None, None, ham, ("sahip arac SIFIR-DISI rc=%d dondu — hukum "
                                       "GUVENILIR DEGIL" % r.returncode)
    hukum = None
    for satir in ham.splitlines():
        if satir.startswith("HUKUM="):
            parcalar = satir[len("HUKUM="):].split()
            hukum = parcalar[0] if parcalar else ""
            break
    ham_tasinabilir = _jeton_degeri(ham, "tasinabilir=")
    ham_korumali = _jeton_degeri(ham, "KORUMALI_BEKLEYEN=")
    if hukum is None:
        return None, None, None, ham, "ciktida `HUKUM=` satiri YOK"
    try:
        tasinabilir = int(ham_tasinabilir)
    except (TypeError, ValueError):
        return None, None, None, ham, "ciktida `tasinabilir=<sayi>` jetonu YOK/OKUNAMADI"
    try:
        korumali = int(ham_korumali)
    except (TypeError, ValueError):
        korumali = None            # RAPOR ekseni; hukmu BELIRLEMEZ
    return hukum, tasinabilir, korumali, ham, None


def koruma_gecirir_mi(hukum, tasinabilir):
    """SAF HUKUM (IO YOK) — kapi tavan ustu kutuyu GECIRSIN mi?

    Spec K318 KOL-3, birebir: `HUKUM=KORUMA_TUTTU` **ve** `tasinabilir=0`.
    Iki sart da gerekli:
      * yalniz HUKUM'e bakmak KISMI hali de gecirirdi. Arac o hal icin AYRI bir
        jeton basar (`KORUMA_TUTTU_KISMI`, bosluklu degil) — orada arac HALA is
        yapabiliyor demektir ve gecirmek kilidi kalicilastirir.
      * yalniz `tasinabilir=0`a bakmak `KORU_TUTTU` halini de gecirirdi; o hal
        korumayla ILGISIZDIR (`--koru` cok buyuk) ve gorunurluk gerekcesi YOKTUR.

    🔴 KOTA OLDURULMEZ: bu kol YALNIZCA "arac ISI KASITLI OLARAK yapmiyor" halini
    gecirir. Koruma YOKKEN tavan asimi BLOKLAMAYA DEVAM EDER — aksi halde kota
    butunuyle olurdu (olculdu 27 Agu: paralel cipler yazdikca kutu satiri asagi
    degil YUKARI gidiyor; 668 -> 548 -> 570). Kabul testi bunu IKI YONLU mutantla
    (M4/M5) olcer.
    """
    return hukum == "KORUMA_TUTTU" and tasinabilir == 0


def _kutu_olc(yol):
    """(satir, bayt) — okunamazsa (None, None)."""
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except OSError:
        return None, None
    return len(ham.splitlines()), len(ham)


def kutu_kontrol(kok, kol_no_op=False):
    """KUTU ekseni — OKUR, hukum basar, rc dondurur. ASLA YAZMAZ/KIRPMAZ.

    kol_no_op=True: M1 mutanti (kutu kolu KALDIRILMIS gibi davran). Hedef kol
    olmeli, defter ekseni (yan eksen) YASAMALI.
    """
    if kol_no_op:
        return 0

    sahip_coz = getattr(_mod, "kutu_sahibi", None)
    if sahip_coz is None:
        print("!! %s — tavan tabani (defter-kota-taban.py) kutu sahibini cozemiyor "
              "(kutu_sahibi YOK: bayat/eksik kopya). Kutu OLCULMEDI; olculemeyen "
              "sey yesil sayilmaz." % KUTU_OLCULEMEDI, file=sys.stderr)
        return KUTU_RC[KUTU_OLCULEMEDI]

    mod, sahip_yolu, hata = sahip_coz(kok)
    if mod is None and hata is None:
        print("%s — kutu tavan/yol sahibi bu depoda YOK (%s). Bu checkout ortak "
              "posta kutusunu sahiplenmiyor; kutu ekseni bu kok icin kapsam disidir."
              % (KUTU_SAHIPSIZ, sahip_yolu))
        return KUTU_RC[KUTU_SAHIPSIZ]
    if mod is None:
        print("!! %s — kutu tavan sahibi (%s) VAR ama YUKLENEMEDI. SEBEP: %s. "
              "Kutu OLCULMEDI; olculemeyen sey yesil sayilmaz."
              % (KUTU_OLCULEMEDI, sahip_yolu, hata), file=sys.stderr)
        return KUTU_RC[KUTU_OLCULEMEDI]

    tavan = _mod.kutu_tavan_satir(mod)
    kutu_yolu = os.environ.get("PRUVO_KUTU_YOLU") or _mod.kutu_dosya_yolu(mod)
    arsiv_yolu = _mod.kutu_arsiv_yolu(mod)
    if tavan is None or not kutu_yolu:
        print("!! %s — sahip modulunde tavan (VARSAYILAN_TAVAN) ya da kutu yolu "
              "(KUTU_VARSAYILAN) cozulemedi: %s. Kutu OLCULMEDI."
              % (KUTU_OLCULEMEDI, sahip_yolu), file=sys.stderr)
        return KUTU_RC[KUTU_OLCULEMEDI]

    dizin = os.path.dirname(kutu_yolu)
    dizin_var = os.path.isdir(dizin)
    satir, bayt = (_kutu_olc(kutu_yolu) if dizin_var else (None, None))
    dosya_var = satir is not None

    hal = kutu_hali(True, dizin_var, dosya_var, satir, tavan)

    if hal == KUTU_MAKINEDE_YOK:
        print("%s — kutunun hafiza dizini bu makinede HIC yok (%s). Kusur DEGIL "
              "(kosucu/kardes makine); kutu ekseni kapsam disidir. Sahip: %s"
              % (KUTU_MAKINEDE_YOK, dizin, sahip_yolu))
        return KUTU_RC[KUTU_MAKINEDE_YOK]

    if hal == KUTU_OLCULEMEDI:
        print("!! %s — hafiza dizini (%s) VAR ama kutu dosyasi YOK/OKUNAMIYOR: %s. "
              "Kutu OLCULMEDI; olculemeyen sey YESIL SAYILMAZ (fail-closed). "
              "Kutu silinmis/yeniden adlandirilmis olabilir."
              % (KUTU_OLCULEMEDI, dizin, kutu_yolu), file=sys.stderr)
        return KUTU_RC[KUTU_OLCULEMEDI]

    if hal == KUTU_ASILDI:
        # 🔴 K318 KOL-3 — SATIR SAYISI TEK BASINA HUKUM DEGILDIR: rotasyon aracinin
        # KENDI hukmu TUKETILIR. Hukum alinamazsa BLOKLANIR (fail-open YASAK).
        hukum, tasinabilir, korumali, ham, hhata = kutu_hukmu_al(sahip_yolu, kutu_yolu)
        if hhata is not None:
            print("!! %s — kutu tavanin USTUNDE (%d satir > %d) ve sahip aracin "
                  "(%s) HUKMU ALINAMADI: %s. Fail-closed: hal belirsizken commit "
                  "GECIRILMEZ; 'olcemedim' YESIL DEGILDIR."
                  % (KUTU_HUKUM_ALINAMADI, satir, tavan, sahip_yolu, hhata),
                  file=sys.stderr)
            if ham.strip():
                print("!!   arac ciktisi (son 5 satir): %s"
                      % " | ".join(ham.strip().splitlines()[-5:]), file=sys.stderr)
            return KUTU_RC[KUTU_HUKUM_ALINAMADI]
        if koruma_gecirir_mi(hukum, tasinabilir):
            # HAL GIZLENMEZ, SAYILARIYLA BASILIR — gorunurluk kota kirmizisina
            # tercih edilir (Okan kurali ⑤), ama tercih HER KOSUMDA yeniden soylenir.
            print("%s once_satir=%d tavan=%d korumali_bekleyen=%s tasinabilir=%d "
                  "HUKUM=%s kutu=%s"
                  % (KUTU_KORUMA_USTU, satir, tavan,
                     "OLCULEMEDI" if korumali is None else korumali,
                     tasinabilir, hukum, kutu_yolu))
            print("   (Kutu tavanin USTUNDE ama rotasyon araci ISI KASITLI OLARAK "
                  "yapmiyor: bekleyen kapanis blogu rotasyona GIRMEZ. Commit "
                  "BLOKLANMADI — kilidi acan sey Okan'in o cip(ler)i arsivlemesi ve "
                  "jetonun cevrilmesidir; ARA komut: python3 %s)" % sahip_yolu)
            return KUTU_RC[KUTU_KORUMA_USTU]
        print("!! %s — ORTAK POSTA KUTUSU KOTASI ASILDI: %s %d satir / %d bayt "
              "(tavan satir=%d, TAVAN SAHIBI=%s::VARSAYILAN_TAVAN)."
              % (KUTU_ASILDI, kutu_yolu, satir, bayt, tavan, sahip_yolu),
              file=sys.stderr)
        print("!! CARE: python3 /Users/okan/dev/pruvo/tools/kutu-arsivle.py",
              file=sys.stderr)
        print("!!   (LOSSLESS: hicbir sey SILINMEZ — en eski bloklar %s dosyasina "
              "TASINIR. Kapi kutuyu YALNIZ OKUR; tasimayi insan ya da rotasyon "
              "araci yapar. Once kuru kosum: --kuru. K258, 20 Agu: iki bicim de "
              "mimarin elinde SERBEST — kapinin DEFTER BAKIMI kovasi yalnizca "
              "'--kuru' bayragini gecirir, baska bayrak RED.)"
              % (arsiv_yolu or "<kutu>-arsiv.md"), file=sys.stderr)
        return KUTU_RC[KUTU_ASILDI]

    print("%s satir=%d bayt=%d tavan=%d kutu=%s" % (KUTU_YESIL, satir, bayt,
                                                    tavan, kutu_yolu))
    return KUTU_RC[KUTU_YESIL]


# ---------------------------------------------------------------------------
# TEK KAYNAK NOBETI (K253 M2) — esik SAYISI ikinci bir sabite kopyalanamaz
# ---------------------------------------------------------------------------
def izlenen_esikler(kok):
    """Izlenmesi gereken esik DEGERLERI (owner'lardan TURETILIR, yazilmaz)."""
    degerler = {TAVAN_SATIR, TAVAN_BAYT}
    sahip_coz = getattr(_mod, "kutu_sahibi", None)
    if sahip_coz is None:
        return degerler
    mod, _, hata = sahip_coz(kok)
    if mod is not None and hata is None:
        t = _mod.kutu_tavan_satir(mod)
        if isinstance(t, int) and not isinstance(t, bool):
            degerler.add(t)
    return degerler


def tek_kaynak_ihlalleri(kok, degerler=None):
    """Kota ekseni dosyalarinda IKINCI ESIK SAHIBI arar.

    Modul duzeyinde `<AD> = <tamsayi>` atamalarina bakilir. Deger izlenen esik
    kumesindeyse ve (dosya, ad) cifti ESIK_SAHIPLERI'nde DEGILSE -> ihlal.
    Yalnizca modul duzeyi taranir: fonksiyon icindeki yerel hesaplar (or.
    `satir = max(1, TAVAN_SATIR - 30)`) sabit DEGILDIR, tarama disidir.

    Donus: [(dosya, ad, deger, satir_no), ...]. Bos liste = TEK KAYNAK SAGLAM.
    """
    if degerler is None:
        degerler = izlenen_esikler(kok)
    ihlaller = []
    tools = os.path.join(kok, "tools")
    for ad in KOTA_EKSENI_DOSYALARI:
        yol = os.path.join(tools, ad)
        if not os.path.isfile(yol):
            continue
        try:
            with open(yol, "r", encoding="utf-8") as f:
                agac = ast.parse(f.read(), filename=yol)
        except (OSError, SyntaxError):
            continue
        for dugum in agac.body:
            if not isinstance(dugum, ast.Assign):
                continue
            if not isinstance(dugum.value, ast.Constant):
                continue
            deger = dugum.value.value
            if not isinstance(deger, int) or isinstance(deger, bool):
                continue
            if deger not in degerler:
                continue
            for hedef in dugum.targets:
                if not isinstance(hedef, ast.Name):
                    continue
                if (ad, hedef.id) in ESIK_SAHIPLERI:
                    continue
                ihlaller.append((ad, hedef.id, deger, dugum.lineno))
    return ihlaller


def tek_kaynak_kontrol(kok):
    """Tek kaynak nobeti — ihlal varsa 1, yoksa 0."""
    ihlaller = tek_kaynak_ihlalleri(kok)
    if not ihlaller:
        return 0
    print("!! TEK_KAYNAK_IHLALI — kota esik SAYISI ikinci bir sabite KOPYALANMIS. "
          "Esik tek sahiptedir; kopya, kapi ile rotasyon aracinin SESSIZCE "
          "ayrismasina yol acar.", file=sys.stderr)
    for dosya, ad, deger, no in ihlaller:
        print("!!   tools/%s:%d  %s = %d  (sahipli DEGIL)" % (dosya, no, ad, deger),
              file=sys.stderr)
    print("!! CARE: sabiti SIL ve degeri sahibinden oku — satir/bayt tavani "
          "tools/defter-kota-taban.py, kutu tavani "
          "tools/kutu-arsivle.py::VARSAYILAN_TAVAN.", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# ANA AKIS
# ---------------------------------------------------------------------------
def _defter_kolu(kok):
    """DEFTER ekseni (K178 + K195b) — govde AYNEN korundu."""
    stage_de = _devam_stage_de(kok)
    if stage_de is None:
        print("!! COMMIT DURDURULDU — DEVAM.md stage kontrolu OLCULEMEDI.",
              file=sys.stderr)
        return 1
    if not stage_de:
        return _kapsam_disi_olc(kok)

    satir, bayt = _devam_olcu_index(kok)
    if satir is None:
        print("!! COMMIT DURDURULDU — DEVAM.md INDEX blob'u okunamadi.",
              file=sys.stderr)
        return 1

    asi, eksen, _, _ = tavan_asi_mi(satir, bayt)
    if not asi:
        return 0
    return _hukum_red(satir, bayt, eksen, kok)


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--kendini-test" in argv:
        return _kendini_test()
    if "--bypass-kontrol" in argv:
        argv = [a for a in argv if a != "--bypass-kontrol"]
        return bypass_kontrol(argv[1] if len(argv) > 1 else ROOT)
    kok = argv[1] if argv and len(argv) > 1 else ROOT

    # 🔴 IKI EKSEN DE HER ZAMAN KOSAR, sonra rc BIRLESTIRILIR. Kisa devre YOK:
    # biri kirmizi diye digeri OLCULMEDEN gecerse hangi eksenin saglam oldugunu
    # kimse bilemez, ve bir sonraki turda "zaten kirmiziydi" diye yutulur.
    kutu_rc = kutu_kontrol(kok)
    kaynak_rc = tek_kaynak_kontrol(kok)
    defter_rc = _defter_kolu(kok)
    if kutu_rc or kaynak_rc or defter_rc:
        return 1
    return 0


# ---------------------------------------------------------------------------
# KENDINI-TEST (K178)
# ---------------------------------------------------------------------------
def _kendini_test():
    """Sentetik fiksturlerle M1/M2 + 2 KONTROL + M3 + M4.

    K2 (tam tavan) asagidaki yoruma gorunmez sekilde RED sinifina dahildir
    (tavan DAHIL <=). M3 (byte kolu no-op) ile M1 fiksturu YEŞIL donmeli
    (yani byte kolu gercekten olculuyor). M4 (byte/char karisikligi) icin
    Turkce fikstur gerekir.
    """
    import tempfile

    sonuclar = []
    gecen = 0

    # ---- K1: satir altinda + bayt altinda → YESIL -------------------------
    fikstur = _fikstur_satir_bayt(50, 1000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"])
    sonuclar.append(("K1 YESIL", rc == 0, "satir=%d bayt=%d rc=%d (0 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- K2: satir tam tavanda + bayt altinda → YESIL (tavan DAHIL) -------
    fikstur = _fikstur_satir_bayt(TAVAN_SATIR, 2000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"])
    sonuclar.append(("K2 TAM_TAVAN", rc == 0, "satir=%d bayt=%d rc=%d (0 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- M1: satir altinda + bayt asimda → KIRMIZI, ASAN_EKSEN=BAYT -------
    # M1'in BAYT-OVER satir-UNDER VAKASI burada. M3 izolasyonu icin M1
    # alternatifi (`M1_LOOSE` satir OVER + bayt OVER) asagida; M3 kolu
    # ORADA satir yedek sigortasi ile RED kalir.
    fikstur = _fikstur_satir_bayt(50, TAVAN_BAYT + 1000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"])
    sonuclar.append(("M1 BAYT", rc == 1 and satir <= TAVAN_SATIR and bayt > TAVAN_BAYT,
                      "satir=%d bayt=%d rc=%d (1 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- M2: satir asimda + bayt altinda → KIRMIZI, ASAN_EKSEN=SATIR ------
    fikstur = _fikstur_satir_bayt(TAVAN_SATIR + 5, 2000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"])
    sonuclar.append(("M2 SATIR", rc == 1 and satir > TAVAN_SATIR and bayt <= TAVAN_BAYT,
                      "satir=%d bayt=%d rc=%d (1 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- M3: byte kolu OLDURULMUS → M1 fiksturu YESIL'e donmeli ----------
    # Bayt kontrolu no-op edilince M1 (byte over, line under) YESIL'e doner;
    # donduyse byte kolu gercekten OLCULDU demektir ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).
    fikstur = _fikstur_satir_bayt(50, TAVAN_BAYT + 1000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"], bayt_no_op=True)
    sonuclar.append(("M3 BAYT_NO_OP", rc == 0 and satir <= TAVAN_SATIR and bayt > TAVAN_BAYT,
                      "satir=%d bayt=%d rc=%d (mutant yesil; 0 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- M4: byte yerine karak sayisi → Turkce fikstur YESIL'e donmeli ----
    # Turkce 'ş' UTF-8'de 2 bayt, 1 karakter. Byte > tavan, karak < tavan.
    # Karak kolu ile sayinca YESIL; byte kolu ile sayinca KIRMIZI.
    fikstur = _fikstur_turkce(TAVAN_BAYT + 200)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"], byte_yerine_karakter=True)
    sonuclar.append(("M4 KARAK", rc == 0,
                      "satir=%d bayt=%d rc=%d (mutant yesil; 0 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    dusen = 0
    for ad, gecti, detay in sonuclar:
        if gecti:
            gecen += 1
        else:
            dusen += 1
            print("  ✗ %s: %s" % (ad, detay), file=sys.stderr)

    toplam = len(sonuclar)
    print("FIKSTUR=%d/%d MUTANT=%d/%d" % (gecen, toplam, dusen, toplam))
    print("DUSEN=%d" % dusen)
    return 0 if dusen == 0 else 1


def _fikstur_satir_bayt(satir_hedef, bayt_hedef):
    """Hedef satir + bayt sayisina yakin fikstur uretir (yol dict)."""
    import tempfile
    if satir_hedef <= 0:
        raise ValueError("satir_hedef > 0 olmali")
    if bayt_hedef < satir_hedef * 2:
        ortalama = 2
    else:
        ortalama = max(2, (bayt_hedef + satir_hedef - 1) // satir_hedef)
    genis = ortalama - 1  # -1 cunku newline = +1
    if genis < 1:
        genis = 1
    icerik = ("a" * genis + "\n") * satir_hedef
    fd, yol = tempfile.mkstemp(suffix=".md", prefix="k178-fikstur-")
    with os.fdopen(fd, "wb") as f:
        f.write(icerik.encode("utf-8"))
    return {"yol": yol, "satir": satir_hedef, "bayt": len(icerik.encode("utf-8"))}


def _fikstur_turkce(bayt_hedef):
    """Bayt hedefine ulasan Turkce karakterli fikstur. 'ş' 2 bayt.

    Satir sayisi TAVAN_SATIR'in ALTINDA tutulur ki satir ekseni M4 icin
    yalniz bayt eksenindeki fark gorulsun; byte > tavan, char < tavan.
    """
    import tempfile
    satir = max(1, TAVAN_SATIR - 30)  # TAVAN_SATIR-30 = 100
    # 80 'ş' + newline = 160 + 1 = 161 bayt/satir
    icerik = ("ş" * 80 + "\n") * satir
    fd, yol = tempfile.mkstemp(suffix=".md", prefix="k178-fikstur-tr-")
    with os.fdopen(fd, "wb") as f:
        f.write(icerik.encode("utf-8"))
    return {"yol": yol, "satir": satir, "bayt": len(icerik.encode("utf-8"))}


def _fikstur_sil(fikstur):
    try:
        os.unlink(fikstur["yol"])
    except OSError:
        pass


def _olcule_yardimci(yol, byte_yerine_karakter=False, bayt_no_op=False):
    """Dosyayi olc, kapinin ayni hukmu uygula.

    byte_yerine_karakter=True: bayt karsilastirmasi karakter sayisi ile yapilmis
        gibi davran (M4 mutanti).
    bayt_no_op=True: bayt karsilastirmasi >= her zaman True (M3 mutanti).
    """
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except OSError:
        return None, None, 1
    satir = len(ham.splitlines())
    bayt = len(ham)

    satir_as = satir > TAVAN_SATIR
    if bayt_no_op:
        bayt_as = False
    elif byte_yerine_karakter:
        try:
            metin = ham.decode("utf-8")
        except UnicodeDecodeError:
            metin = ""
        bayt_as = len(metin) > TAVAN_BAYT
    else:
        bayt_as = bayt > TAVAN_BAYT

    if satir_as or bayt_as:
        return satir, bayt, 1
    return satir, bayt, 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
