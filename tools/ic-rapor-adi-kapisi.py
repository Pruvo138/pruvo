#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ic-rapor-adi-kapisi.py — IC ISCI-RAPORU PROTOKOL ADININ ("RAPOR-MIMARA.md")
IZLENEN dosyalarda YORUM/DOKUMANTASYON METNI olarak YENIDEN BELIRMESINI KIRMIZI yakan
regresyon nobetcisi.

NEDEN VAR (4 Agu 2026 olcumu): repo PUBLIC (Pruvo138/pruvo). Isci->mimar rapor
dosyasinin protokol adi (CLAUDE.md ILETISIM PROTOKOLU: "RAPOR ADI: yalniz
RAPOR-MIMARA.md") 20 izlenen dosyada 24 yerde yorum/docstring METNI icinde ATIF
olarak geciyordu ("kanit RAPOR-MIMARA.md'de", "bkz. RAPOR-MIMARA.md" vb.). Bu bir
KISISEL VERI sizintisi DEGIL (tools/kisisel-veri-test.py bu eksende zaten yesildi,
ic olcum/kapi-bypass detayi tasimiyor) — sadece ic is akisinin bir parcasi (rapor
dosyasinin adi) disariya GORUNUYORDU. Bu 24 yer o gun NOTRLESTIRILDI (dosya adi
yerine "muhendis raporunda" gibi anlamini KORUYAN genel ifade). Bu nobetci o
temizligin GERI GELMEMESI icin REGRESYON bekcisidir.

MUAF TUTULAN — 31 isabet, DOKUNULMADI, asagidaki _MUAFIYET_GOVDESI'nde KAYITLI:
  * tools/durum.py (2) — protokol adini FIILEN ARAYAN KOD (os.path.join) + ona
    bagli print etiketi; degistirilirse durum panosunun DAVRANISI degisir.
  * tools/kisisel-veri-test.py (22) — IC RAPOR SIZINTI nobetcisinin KENDI
    fikstur/hata-mesaji VERISI; bu string'ler o nobetcinin gercek KIRMIZI/YESIL
    davranisini ve kullaniciya yazdigi cozum metnini olusturur.
  * tools/olculmemis-siparis-test.py (1) — print() argumani: CALISAN KOD, yorum
    ya da docstring DEGIL.
  * tools/paket-*.md (6) — mimar->muhendis DELEGASYON spec'leri: "rapor adi
    ZORUNLU RAPOR-MIMARA.md" talimatinin KENDISI (protokolun tanimi); genel
    ifadeye cevrilirse gelecekteki iscilerin dogru rapor adini KAYBETMESINE yol
    acar.
  * tools/ic-rapor-adi-kapisi.py — BU DOSYANIN KENDISI: yukaridaki govde,
    docstring ornekleri ve kendini-test fiksturleri deseni DOGRUDAN tasir
    (nobetci deseni TANIMLAMAK icin onu YAZMAK ZORUNDADIR). KENDI_YOLU sabitiyle
    ana_tarama()'da TEK path olarak ELENIR — icerik-hash govdesine GIRMEZ.

Muafiyet GENEL bir desen kacisi DEGILDIR: her kayit (dosya, o SATIRIN TAM
METNININ sha256'si, gerekce) UCLUSUDUR. Satir tek karakter degisirse (baska bir
soze tasinsa/kirpilsa/genisletilse bile) ya da baska bir dosyaya kopyalansa
muafiyet ARTIK GECERSIZDIR ve o satir KIRMIZI yanar — muafiyet KAYITLI GOVDEDEN
turer, path bazli genel bir "bu dosyaya dokunma" kacisi DEGILDIR.

🔴 HANGI AGACI OLCER — 5 Agu 2026 OLCULEN KUSUR ("kapi yanlis agacta yesil yakiyor"):
Bu kapi taranacak kokunu ONCEDEN `git rev-parse --show-toplevel` ile CWD'den
turetiyordu. Sonuc: DALIN dosyalarini yargiladigi SANILAN kosum aslinda ANA
CHECKOUT'u tariyordu ve `exit 0` veriyordu. Olculen zarar: bir merge kapisi turunda
izlenen bir kaynak dosyada ic isci-raporu protokol adi sizmisken kapi ana
checkout'tan YESIL yandi; ayni dal yalniz `cwd=dal worktree` ile kosuldugunda rc=1
verdi. Kapi CI'da BLOKLAYICIDIR (continue-on-error YOK) -> sizinti merge edilseydi
yayinlanacakti.

ONARIM — KOK ARTIK CWD'DEN TUREMEZ:
  1. `--kok YOL` ile olculecek agac ACIKCA verilebilir (her yerden kosar).
  2. Bayraksiz varsayilan = BETIGIN KENDI AGACI (`__file__` -> `git -C ... --show-toplevel`),
     CWD DEGIL. CI'da betik zaten checkout edilen agacta yasar -> bayraksiz davranis
     DOGRUDUR; bir worktree'nin KENDI kopyasi da her zaman KENDI agacini olcer.
  3. BELIRSIZLIK FAIL-CLOSED'DIR: bayrak verilmemis VE cwd'nin agaci betigin
     agacindan FARKLIYSA hukum verilmez -> rc 2 (OLCULEMEDI). Cunku o an hangi
     agacin sorulduğu betikten ANLASILAMAZ; sessiz bir yesil/kirmizi YANLIS AGACA
     atfedilebilir. Cikis yolu susturma degil, `--kok` ile agaci SOYLEMEKTIR.
  4. Olculen kok + taranan dosya sayisi HER kosumda (yesilde de) BASILIR — bir
     yesil artik sessizce baska bir agaca atfedilemez.

🔴 KOK TURETIMI ORTAMDAN BAGIMSIZDIR (6 Agu 2026 onarimi, gizil kusur):
Kok `git -C <yol> rev-parse --show-toplevel` ile turer. Bir GIT KANCASI icinden
kosuldugunda cagiran surec git baglam degiskenlerini IHRAC EDER; linked worktree
kancasinda GIT_DIR MUTLAK gelir ve GIT_WORK_TREE bostur -> git depo KESFINI ATLAR,
CARI DIZINI agacin tepesi sayar ve ACIK `-C` hedefi SESSIZCE EZILIR. Olculdu (sentetik
depo + gercek `git worktree add` + gercek `git commit`): kanca icinden kosan bu kapi
"betik agaci = <worktree>/tools" bulup rc=2 OLCULEMEDI veriyordu — commit BLOKLANIR,
isci `--no-verify`ye itilir (yani kusur kapinin KENDISINI atlatmayi normallestirir).
CARE: git cagrilari miras alinan git baglami SILINMIS ortamda kosar; scrub'in TEK
tanimi tools/git_ortami.py'dir (FALLBACK YOK — modul yoksa cagri coker).
Kabul: IDDIA-6, mutant MUT-KOK-ORTAM.

Kullanim:
    python3 tools/ic-rapor-adi-kapisi.py                 # BETIGIN agacini tarar, exit 0/1
    python3 tools/ic-rapor-adi-kapisi.py --kok /yol/dal  # ACIKCA verilen agaci tarar
    python3 tools/ic-rapor-adi-kapisi.py --kendini-test   # offline kabul testi (izole git)

Cikis kodu: 0 = temiz (ihlal yok), 1 = en az bir IZLENEN dosyada muafiyet-disi
yeni bir "RAPOR-MIMARA" gecisi bulundu (harf-duyarsiz), 2 = OLCULEMEDI
(fail-closed: agac belirsiz / verilen yol git agaci degil).
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # SALT-OKUNUR tarama: hedef repoya __pycache__ yazma.

# Betigin KENDI dizini. Kok bundan turer -> CWD ne olursa olsun AYNI agac olculur.
BETIK_DIZINI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BETIK_DIZINI)
# 🔴 TEK KAYNAK ([[ikiz-tanim-sessiz-ayrisma]]): git baglam scrub'i ve onunla kok
# turetimi tools/git_ortami.py'de TANIMLIDIR. Burada `try/except ImportError -> yerel
# tanim` YAZILMAZ: o dusus yolu ikizin ta kendisidir ve gevsek yonde ayrisir.
from git_ortami import git_kok, git_ortami   # noqa: E402
from git_ortami import worktree_kanca_kok_olcumu   # noqa: E402

DESEN = "rapor-mimara"  # kucuk harfe cevrilmis satirda aranir (harf-duyarsiz)

RC_TEMIZ = 0
RC_IHLAL = 1
RC_OLCULEMEDI = 2  # fail-closed: hangi agacin sorulduğu belirsiz / yol git agaci degil

# KENDI DOSYASI ISTISNASI (govde-disi, TEK path, GEREKCELI): bu nobetci deseni
# TANIMLAMAK icin onu DOGRUDAN tasimak ZORUNDADIR (docstring ornekleri, asagidaki
# _MUAFIYET_GOVDESI'nin literal verisi, kendini-test fiksturleri). Aksi halde
# nobetci KENDI KENDINI kirmizi yakar (bkz. "Nobetci kendi dosyasinda sizdirir"
# dersi — tools/kisisel-veri-test.py de AYNI sebeple KENDI dosyasini tarima disi
# birakir, orada IC RAPOR AILESI regex'i disindaki kendi kaynagini gormez). Bu,
# _muaf_mi() icerik-hash mekanizmasindan TAMAMEN AYRI, tek path'e ozel bir
# kod-yolu istisnasidir — mutasyon eslemesini (IDDIA-1/IDDIA-2) ETKILEMEZ.
KENDI_YOLU = "tools/ic-rapor-adi-kapisi.py"

# ---------------------------------------------------------------------------
# KAYITLI MUAFIYET GOVDESI — 4 Agu 2026 olcumunden turer (31 mesru isabet).
# Her kayit: (repo-gorece dosya, satirin TAM METNI [\n haric], gerekce).
# sha256 asagida OTOMATIK hesaplanir (elle tutulan hash yok -> govde TEK KAYNAK).
# ---------------------------------------------------------------------------
_MUAFIYET_GOVDESI = [
    ('tools/durum.py', '    yol = os.path.join(worktree_yolu, "RAPOR-MIMARA.md")',
     "fiilen kullanilan kod: worktree'deki rapor dosyasini bu adla arar (durum panosu)"),
    ('tools/durum.py', '            print("      RAPOR-MIMARA.md: %s — %s"',
     "yukaridaki aramaya bagli print etiketi (kod, yorum degil)"),
    ('tools/kisisel-veri-test.py', "# KOK SEBEP: mimar spec'lerinde rapor adi standart DEGILDI (RAPOR-MIMARA /",
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '      KIRMIZI: RAPOR-MIMARA.md · CURUTME-RAPORU.md · curutme.md · ONARIM-RAPORU.md ·',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("RAPOR-MIMARA.md", "protokol adi — isci raporu"),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("RAPOR-MIMARA.txt", "uzanti degistirerek kacis"),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '#     CURUTME-RAPORU-TUR4.md, RAPOR-MIMARA.md).',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("RAPOR-MIMARA.md", "protokol adi; gitignore\'da ama IZLENIRSE B de yakalamali"),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', "    'RAPOR-MIMARA.md' gecirir -> substring testi HER mesaji RAPOR-MIMARA ihlali",
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '                     "CURUTME-RAPORU.md", "RAPOR-MIMARA.md"]',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '                           "CURUTME-RAPORU.md", "RAPOR-MIMARA.md"])',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            "kimlikleri / ic olcum). Cozum: git rm --cached \'%s\' + adi RAPOR-MIMARA.md yap."',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            "Cozum: (a) ic rapor ise \'git rm --cached %s\' + adi RAPOR-MIMARA.md yap "',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '# RAPOR-MIMARA.md hem tools/yedek-topolojisi-raporu.md icin True donuyor. Sorun TANIMA',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("protokol adi RAPOR-MIMARA.md dal push\'unda eklenmis",',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '     _gc(("a" * 40, ["tools/build.py", "RAPOR-MIMARA.md"])),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '     [("a" * 40, "RAPOR-MIMARA.md")]),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("MESRU 4: gitignore\'lu dosya (CLAUDE.md/DEVAM.md/RAPOR-MIMARA.md izlenmez) -> "',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            for ad, icerik in [("RAPOR-MIMARA.md", "ic rapor govdesi\\n"),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            os.remove(os.path.join(d, "RAPOR-MIMARA.md"))',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            elif isabet != [(ekleyen, "RAPOR-MIMARA.md")]:',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '                    "GECMIS KOLU OLU/BOZUK (GERCEK git): silinmis RAPOR-MIMARA.md "',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '                    % ([(ekleyen, "RAPOR-MIMARA.md")], isabet))',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            "IZLENMEYEN birak; ad protokolu: RAPOR-MIMARA.md + .gitignore."',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/olculmemis-siparis-test.py', '    print("      --- CANLI CIKTI (RAPOR-MIMARA.md\'ye aynen yapistir) ---")',
     "print() argumani (calisan kod, yorum/docstring degil)"),
    ('tools/paket-bilesik-marka.md', 'Dalda `RAPOR-MIMARA.md` (bu ad ZORUNLU): iddia sayısı önce/sonra, mutant tablosu',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-durum-panosu.md', '**Dal:** `claude/durum-panosu` (worktree). **Rapor:** `RAPOR-MIMARA.md` + `DEVAM.md`, mesaj YOK.',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-durum-panosu.md', '   `RAPOR-MIMARA.md` var mı (varsa mtime + ilk başlık satırı).',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-durum-panosu.md', '2. `RAPOR-MIMARA.md`: ne yapıldı, 2. madde kırmızı→yeşil kanıtı, araştırma kalemi sonucu,',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-kararsiz-jeton-sinif1.md', "- Dalını `git push -u origin <dal>` ile it, `RAPOR-MIMARA.md`'yi **dalda** bırak (izlenen",
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-uyum-yazma-yolu.md', 'Dalda `RAPOR-MIMARA.md` (başka ad YASAK, izlenen bırakılma): her iddianın ölçülen sayısı, mutant',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
]


def _satir_hash(satir_metni):
    return hashlib.sha256(satir_metni.encode("utf-8")).hexdigest()


def _muafiyet_kumesi_uret(govde):
    """(dosya, sha256(satir)) ciftlerinden KUME uretir — icerik-bagli karsilastirma."""
    return {(dosya, _satir_hash(satir)) for dosya, satir, _gerekce in govde}


def _desenler_bul(icerik):
    """Verilen metin icindeki (satir_no, satir_metni) ciftlerini, DESEN'i (harf-duyarsiz)
    tasiyanlar icin dondurur. Satir sonu \\n HARIC tutulur (hash karsilastirmasi buna gore)."""
    sonuc = []
    for i, satir in enumerate(icerik.splitlines(), start=1):
        if DESEN in satir.lower():
            sonuc.append((i, satir))
    return sonuc


def _muaf_mi(dosya, satir_metni, muafiyet_kumesi):
    """Icerik-bagli muafiyet: (dosya, satirin TAM METNININ hash'i) kayitli mi."""
    return (dosya, _satir_hash(satir_metni)) in muafiyet_kumesi


def tara(dosya_icerik_ciftleri, govde=_MUAFIYET_GOVDESI):
    """dosya_icerik_ciftleri: iterable[(repo-gorece yol, icerik_str)].
    Dondurur: [(yol, satir_no, satir_metni), ...] — muafiyet-disi TUM isabetler."""
    kume = _muafiyet_kumesi_uret(govde)
    ihlaller = []
    for yol, icerik in dosya_icerik_ciftleri:
        for satir_no, satir in _desenler_bul(icerik):
            if not _muaf_mi(yol, satir, kume):
                ihlaller.append((yol, satir_no, satir))
    return ihlaller


def _git_kok(dizin):
    """dizin'in AIT OLDUGU git agacinin kokunu doner ("" = git agaci degil).

    🔴 `-C dizin` ZORUNLU: argumansiz `git rev-parse --show-toplevel` CWD'ye bakar —
    5 Agu 2026'da olculen kusur tam olarak buydu. Burada cwd'nin HICBIR etkisi yoktur.
    🔴 ORTAM ACIKCA TEMIZ VERILIR: miras alinan GIT_DIR/GIT_WORK_TREE acik `-C` hedefini
    SESSIZCE ezer (kanca + linked worktree baglami; 6 Agu 2026 onarimi, IDDIA-6).
    Scrub'in TANIMI tools/git_ortami.py'dedir; burasi yalniz o secimi TASIR."""
    return git_kok(dizin, git_ortami())


def kok_coz(arg_kok, cwd, betik_dizini=BETIK_DIZINI):
    """Olculecek agaci belirler. Dondurur: (kok, hata).

    hata != None -> hukum VERILMEZ, rc RC_OLCULEMEDI (fail-closed).
      * arg_kok verilmisse O agac olculur (cwd de betik dizini de ETKISIZ).
      * verilmemisse BETIGIN agaci olculur; ancak cwd BASKA bir git agacindaysa
        hangi agacin soruldugu belirsizdir -> OLCULEMEDI (sessiz yanlis-atif yerine
        gurultulu durus)."""
    if arg_kok:
        k = _git_kok(arg_kok)
        if not k:
            return None, ("--kok ile verilen yol bir git agaci DEGIL: %s" % arg_kok)
        return k, None
    betik_kok = _git_kok(betik_dizini)
    if not betik_kok:
        return None, ("betigin bulundugu agac bir git deposu DEGIL: %s "
                      "(cozum: --kok ile olculecek agaci ver)" % betik_dizini)
    cwd_kok = _git_kok(cwd)
    if cwd_kok and os.path.realpath(cwd_kok) != os.path.realpath(betik_kok):
        return None, (
            "AGAC BELIRSIZ (fail-closed) — betigin agaci ile calisma dizininin agaci "
            "FARKLI:\n  betik agaci: %s\n  cwd  agaci : %s\n"
            "Hangi agacin olculecegi betikten anlasilamaz; sessiz bir YESIL yanlis "
            "agaca atfedilebilir (5 Agu 2026'da olculen kusur budur).\n"
            "COZUM: agaci ACIKCA soyle -> --kok %s" % (betik_kok, cwd_kok, cwd_kok))
    return betik_kok, None


def _git_izlenen_dosyalar(kok):
    # Ortam ayni sebeple temiz: kanca baglamindan kosuldugunda miras alinan GIT_DIR
    # `-C kok` hedefini ezip BASKA bir agacin indeksini listeleyebilir.
    r = subprocess.run(["git", "-C", kok, "ls-files", "-z"], capture_output=True,
                       text=True, env=git_ortami())
    if r.returncode != 0:
        sys.exit("git ls-files basarisiz: " + r.stderr.strip())
    return [y for y in r.stdout.split("\0") if y]


def _oku(kok, yol):
    tam = os.path.join(kok, yol)
    try:
        with open(tam, "r", encoding="utf-8") as f:
            return f.read()
    except (UnicodeDecodeError, OSError):
        return None  # binary / okunamayan dosya -> atla (bu desen yalniz metinde anlamli)


def ana_tarama(kok):
    """GERCEK repo taramasi: `kok` AGACINDA `git -C kok ls-files` ile IZLENEN dosyalar.
    KENDI_YOLU (bu betigin kendisi) HARIC tutulur — bkz. yukaridaki gerekce.
    Dondurur: (ihlaller, taranan_dosya_sayisi) — sayi cikti'da BASILIR ki bir
    "temiz" hukmu hangi agacta/kac dosyada olculdugu bilinmeden atfedilemesin."""
    ciftler = []
    for yol in _git_izlenen_dosyalar(kok):
        if yol == KENDI_YOLU:
            continue
        icerik = _oku(kok, yol)
        if icerik is not None:
            ciftler.append((yol, icerik))
    return tara(ciftler), len(ciftler)


# ===========================================================================
# KENDINI-TEST — izole gecici git deposunda offline kabul testi.
# IDDIA-1..IDDIA-6: mutasyon testinin "TEK KIRMIZI" hedefledigi, SABIT SAYIDA
# (6) DECLARE EDILMIS ana iddia — surucusu REPODA durur: `--mutasyon` kolu.
#   1-2 = desen/muafiyet ekseni · 3-5 = KOK ekseni (5 Agu 2026 olculen "yanlis agacta
#   yesil" kusuru) · 6 = WORKTREE+KANCA baglami (6 Agu 2026 olculen "kok ortamdan
#   turuyor" kusuru; DAVRANISSAL: gercek worktree + gercek commit + gercek kanca).
#   KONTROL-*: ek saglamlik/yanlis-pozitif kontrolleri; IDDIA kumesinin
# PARCASI DEGILDIR. KONTROL-C E2E oldugu icin IDDIA-2 ile AYNI alt fonksiyonu
# (_desenler_bul) paylasir — "desen kontrolunu no-op yap" mutantinda YAN ETKI
# olarak o da kirmizi yanabilir; bu, IDDIA kumesindeki TEK-KIRMIZI sartini
# BOZMAZ (mutasyon eslemesi yalniz IDDIA-* etiketlerine bakar).
# ===========================================================================
def _kendini_test():
    sonuclar = []  # [(etiket, gecti_mi, detay)]

    # --- Birim-seviyeli iddialar (tara() alt-fonksiyonlarini DOGRUDAN cagirir;
    #     boylece her mutant TEK bir fonksiyonu vurur, TEK bir iddiayi kirar.) ---
    kume = _muafiyet_kumesi_uret(_MUAFIYET_GOVDESI)

    # IDDIA-1 (icerik-bagli muafiyet): kayitli DOSYA + DEGISTIRILMIS satir ->
    # MUAF SAYILMAMALI (yalniz path'e degil, TAM ICERIGE bakar).
    kayitli_dosya, kayitli_satir, _g = _MUAFIYET_GOVDESI[0]
    degistirilmis = kayitli_satir + " EKSTRA-KELIME"
    iddia1 = not _muaf_mi(kayitli_dosya, degistirilmis, kume)
    sonuclar.append(("IDDIA-1 icerik-bagli-muafiyet", iddia1,
                      "ayni dosya, degistirilmis satir muaf SAYILMAMALI"))

    # IDDIA-2 (yeni ihlal yakalanir): daha once hic gorulmemis bir satirda,
    # KARISIK BUYUK/KUCUK harfle DESEN gecerse yakalanmali.
    yeni_satir_no_eslesme = _desenler_bul("bir satir\nkanit RaPoR-MiMaRa'da olculdu\nbaska satir")
    iddia2 = len(yeni_satir_no_eslesme) == 1 and yeni_satir_no_eslesme[0][0] == 2
    sonuclar.append(("IDDIA-2 yeni-ihlal-yakalanir", iddia2,
                      "harf-duyarsiz yeni gecis satir 2'de yakalanmali"))

    # --- KONTROL'ler: mutasyona hedef DEGIL, genel saglamlik/yanlis-pozitif nobeti. ---
    kontrol_a = _muaf_mi(kayitli_dosya, kayitli_satir, kume)
    sonuclar.append(("KONTROL-A kayitli-satir-yesil", kontrol_a,
                      "govdedeki satir BIREBIR ise muaf sayilmali"))

    kontrol_b = _desenler_bul("bu satirda ilgili desen yok\nbaska bir baslik ## Ozet") == []
    sonuclar.append(("KONTROL-B desensiz-satir-yesil", kontrol_b,
                      "desen gecmeyen metin hic isaretlenmemeli"))

    # KONTROL-C: uctan-uca (gercek gecici git deposu + `git ls-files`) — kayitli
    # muafiyet GERCEK bir tarama akisinda da yesil kalir; kayit-disi yeni satir
    # GERCEK akiste de kirmizi yanar. E2E oldugu icin mutasyon eslemesine DAHIL
    # EDILMEZ (birden fazla ic fonksiyonu birden aynı anda sinar).
    with tempfile.TemporaryDirectory() as d:
        g = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True)
        g("init", "-q")
        g("config", "user.email", "test@test.local")
        g("config", "user.name", "test")
        os.makedirs(os.path.join(d, "tools"), exist_ok=True)
        with open(os.path.join(d, "tools", "durum.py"), "w", encoding="utf-8") as f:
            f.write(kayitli_satir + "\n")
        with open(os.path.join(d, "yeni-dosya.py"), "w", encoding="utf-8") as f:
            f.write("# gordu: RAPOR-MIMARA.md burada YENI bir yerde geciyor\n")
        g("add", "-A")
        e2e, _sayi = ana_tarama(d)
        e2e_muaf_yesil = not any(y == "tools/durum.py" for y, _sn, _s in e2e)
        e2e_yeni_kirmizi = any(y == "yeni-dosya.py" for y, _sn, _s in e2e)
        kontrol_c = e2e_muaf_yesil and e2e_yeni_kirmizi
        sonuclar.append(("KONTROL-C uctan-uca-git-akisi", kontrol_c,
                          "e2e: kayitli satir yesil, yeni satir kirmizi (isabet=%r)" % (e2e,)))

    # --- KOK EKSENI (5 Agu 2026 olculen kusur: kapi YANLIS AGACTA yesil yakiyordu) ---
    # Ucu de kok_coz()/main() uzerinden AYRI birer davranisi olcer; her birinin
    # AYIRT EDICI mutanti vardir (bkz. tools/ic-rapor-adi-mutasyon.py).
    with tempfile.TemporaryDirectory() as kok_d:
        depo_a = os.path.join(kok_d, "depo-a")   # "betigin agaci"
        depo_b = os.path.join(kok_d, "depo-b")   # "cwd'nin agaci" (BASKA agac)
        for yol in (depo_a, depo_b):
            os.makedirs(os.path.join(yol, "tools"))
            subprocess.run(["git", "-C", yol, "init", "-q"], capture_output=True)
            subprocess.run(["git", "-C", yol, "config", "user.email", "t@t.local"],
                           capture_output=True)
            subprocess.run(["git", "-C", yol, "config", "user.name", "t"],
                           capture_output=True)
        a_tools = os.path.join(depo_a, "tools")

        # IDDIA-3 (--kok USTUNDUR): acikca verilen agac kazanir; cwd de betik dizini
        # de sonucu DEGISTIREMEZ.
        k3, h3 = kok_coz(depo_b, cwd=depo_a, betik_dizini=a_tools)
        iddia3 = h3 is None and k3 is not None and \
            os.path.realpath(k3) == os.path.realpath(depo_b)
        sonuclar.append(("IDDIA-3 acik-kok-ustundur", iddia3,
                          "--kok verilince O agac olculur (cwd=%r -> k=%r, hata=%r)"
                          % (depo_a, k3, h3)))

        # IDDIA-4 (BELIRSIZLIK FAIL-CLOSED): bayrak YOK ve cwd BASKA bir agacta ->
        # hukum VERILMEZ. Sessizce cwd'ye (ya da betige) dusmek, olculen kusurun ta
        # KENDISIDIR: yanlis agacta bir hukum uretilir ve dogru agaca atfedilir.
        k4, h4 = kok_coz(None, cwd=depo_b, betik_dizini=a_tools)
        iddia4 = h4 is not None and k4 is None
        sonuclar.append(("IDDIA-4 belirsizlik-fail-closed", iddia4,
                          "bayraksiz + cwd BASKA agac -> OLCULEMEDI olmali (k=%r)" % (k4,)))

        # IDDIA-5 (E2E: OLCULEN AGAC = BETIGIN AGACI, CWD DEGIL): kapinin bir kopyasi
        # depo-a'ya konur; IHLAL depo-a'dadir, depo-b TEMIZDIR. Kosum cwd=depo-a ile
        # yapilir (belirsizlik yok) ve rc=1 beklenir; kok CWD'den turetilseydi de ayni
        # sonucu verirdi -> AYIRT EDICI kosum ikincisidir: cwd GIT AGACI OLMAYAN bir
        # dizin iken kapi HALA depo-a'yi olcmeli (cwd tabanli kod burada COKER/yesil verir).
        kopya = os.path.join(a_tools, "ic-rapor-adi-kapisi.py")
        with open(os.path.abspath(__file__), "r", encoding="utf-8") as f:
            _kaynak = f.read()
        with open(kopya, "w", encoding="utf-8") as f:
            f.write(_kaynak)
        # Kopya TEK KAYNAK modulunu import eder -> modul de yaninda olmali (fallback YOK).
        shutil.copyfile(os.path.join(BETIK_DIZINI, "git_ortami.py"),
                        os.path.join(a_tools, "git_ortami.py"))
        with open(os.path.join(depo_a, "ihlal.md"), "w", encoding="utf-8") as f:
            # 🔴 FIKSTUR BILEREK KUCUK HARF: IDDIA-5 KOK eksenini olcer, harf-duyarsizligi
            # DEGIL. Buyuk harfle yazilsaydi harf-duyarsizlik mutanti (IDDIA-2'nin
            # oldurucusu) bu iddiayi da dusururdu ve "TEK KIRMIZI" sarti bozulurdu.
            f.write("bkz. rapor" + "-mimara.md (fikstur ihlali)\n")
        subprocess.run(["git", "-C", depo_a, "add", "-A"], capture_output=True)
        gitsiz = os.path.join(kok_d, "gitsiz")   # HICBIR git agacinda olmayan cwd
        os.makedirs(gitsiz)
        p5 = subprocess.run([sys.executable, kopya], cwd=gitsiz,
                            capture_output=True, text=True)
        iddia5 = p5.returncode == RC_IHLAL and "ihlal.md" in p5.stdout
        sonuclar.append(("IDDIA-5 e2e-olculen-agac-betigin-agaci", iddia5,
                          "gitsiz cwd'den kosulunca BETIGIN agacindaki ihlal bulunmali "
                          "(rc=%d)" % p5.returncode))

        # KONTROL-D: ACIKCA verilen TEMIZ agac yesil kalir (yanlis-pozitif nobeti) —
        # "her sey kirmizi" mutantini yakalar, IDDIA kumesinin PARCASI DEGILDIR.
        subprocess.run(["git", "-C", depo_b, "add", "-A"], capture_output=True)
        p6 = subprocess.run([sys.executable, kopya, "--kok", depo_b], cwd=gitsiz,
                            capture_output=True, text=True)
        kontrol_d = p6.returncode == RC_TEMIZ
        sonuclar.append(("KONTROL-D acik-temiz-agac-yesil", kontrol_d,
                          "--kok ile verilen TEMIZ agac rc=0 vermeli (rc=%d)" % p6.returncode))

    # --- IDDIA-6 (WORKTREE + KANCA BAGLAMI, DAVRANISSAL): kokun ORTAMDAN BAGIMSIZLIGI.
    # Sentetik depo + GERCEK `git worktree add` + GERCEK `git commit` ile tetiklenen
    # GERCEK pre-commit kancasi kurulur (ortam ELLE set edilip kanca TAKLIT EDILMEZ).
    # Kapinin bu KOPYASI iki baglamda kosar ve BASTIGI KOK olculur:
    #   (a) kancasiz, cwd = worktree koku      (b) kanca icinden (GIT_DIR MUTLAK miras)
    # 🔴 IDDIA BASILAN KOKE baglidir, ihlal SAYISINA degil: boylece desen/muafiyet
    # eksenlerinin mutantlarindan BAGIMSIZ duser ve "TEK KIRMIZI" sozlesmesi korunur.
    # Onarim ONCESI olculen davranis: (a) DOGRU kok, (b) rc=2 OLCULEMEDI + kok BASILMAZ
    # (betik agaci `<worktree>/tools` sanilir).
    try:
        s6 = worktree_kanca_kok_olcumu(os.path.abspath(__file__), "ic-rapor-adi-kapisi.py")
        iddia6 = s6["kanca_kosti"] and s6["kancasiz"][2] and s6["kanca"][2]
        detay6 = "wt=%s kancasiz=%r kanca=%r" % (s6["wt"], s6["kancasiz"], s6["kanca"])
    except Exception as e:                                   # pragma: no cover
        iddia6, detay6 = False, "sonda kurulamadi: %r" % (e,)
    sonuclar.append(("IDDIA-6 worktree-kanca-kok-ortamdan-bagimsiz", iddia6, detay6))

    basarisiz = [s for s in sonuclar if not s[1]]
    for etiket, gecti, detay in sonuclar:
        print("  [%s] %s — %s" % ("PASS" if gecti else "FAIL", etiket, detay))
    print("  TOPLAM: %d/%d gecti" % (len(sonuclar) - len(basarisiz), len(sonuclar)))
    return 0 if not basarisiz else 1


# ===========================================================================
# MUTASYON BATARYASI (`--mutasyon`) — [[mutasyon-kaniti-yeniden-uretilebilir]]:
# "batarya kostu" ANLATISI kanit DEGILDIR; surucu REPODA durur ve yeniden kosar.
# Kabul cikis kodu degil OLCULEN SAYIDIR: her mutant TEK bir IDDIA'yi dusurmeli,
# capa kaynakta TAM BIR KEZ eslesmelidir, KONTROL mutanti YESIL kalmalidir
# (yoksa batarya "hep kirmizi"dir ve hicbir sey ayirt etmez).
# 🔴 CANLI DOSYAYA YAZILMAZ: mutant GECICI dizindeki KOPYAYA uygulanir; kaynagin
# sha256'si once/sonra olculur ("yazmadim" iddiasi da OLCULUR).
# ===========================================================================
# (ad, eski_metin, yeni_metin, dusmesi_beklenen_TEK_iddia | None = KONTROL)
MUTANTLAR = (
    # --- KOK EKSENI: onarimi GERI ALAN mutantlar ---
    ("MUT-KOK-ARG-KOR", "    if arg_kok:\n        k = _git_kok(arg_kok)",
     "    if False:\n        k = _git_kok(arg_kok)", "IDDIA-3"),
    ("MUT-KOK-CWD-DUS",
     "    if cwd_kok and os.path.realpath(cwd_kok) != os.path.realpath(betik_kok):",
     "    if False:", "IDDIA-4"),
    # Onarimin TA KENDISINI geri alir: kok yine CWD'den turer.
    ("MUT-KOK-CWD-GERI", '    kok, hata = kok_coz(args.kok, os.getcwd())',
     '    kok, hata = _git_kok(os.getcwd()) or None, None', "IDDIA-5"),
    # 6 Agu 2026 onarimini geri alir: git cagrisi MIRAS ALINAN git baglamiyla kosar.
    # Kancasiz vaka (temiz ortam) etkilenmez -> yalniz KANCA ayagi duser: TEK KIRMIZI.
    ("MUT-KOK-ORTAM", "    return git_kok(dizin, git_ortami())",
     "    return git_kok(dizin, os.environ.copy())", "IDDIA-6"),
    # --- DESEN/MUAFIYET ekseni (onarim ONCESI de var olan iddialar) ---
    ("MUT-MUAF-YOL", "    return (dosya, _satir_hash(satir_metni)) in muafiyet_kumesi",
     "    return any(d == dosya for d, _h in muafiyet_kumesi)", "IDDIA-1"),
    # Harf-duyarsizligi oldurur: IDDIA-2'nin KARISIK harfli fiksturu kacar. IDDIA-5'in
    # fiksturu KUCUK harflidir -> ondan BAGIMSIZ duser (ayirt edici mutant).
    ("MUT-DESEN-HARF", "        if DESEN in satir.lower():",
     "        if DESEN in satir:", "IDDIA-2"),
    # --- KONTROL: davranisi DEGISTIRMEYEN degisiklik -> batarya YESIL kalmali.
    #     Bu mutant kirmizi yakarsa batarya ayirt edici degil, sadece hassastir.
    ("KONTROL-METIN", 'print("COZUM: yorum/docstring METNINDEN dosya adini kaldir, anlamini koruyarak")',
     'print("COZUM: yorum/docstring metninden dosya adini kaldir; anlami koru.")', None),
)


_TABLO_BAS = "MUTANTLAR = ("
_TABLO_SON = "def _mutasyon_bataryasi():"


def _tablo_disi(govde):
    """Kaynagi (tablo_oncesi, tablo, tablo_sonrasi) diye ayirir.

    🔴 NEDEN: MUTANTLAR tablosu capa metinlerini KENDISI tasir. Capalar ham kaynakta
    sayilirsa her biri EN AZ 2 kez eslesir ve "capa TAM BIR KEZ" sarti hicbir zaman
    saglanamaz; tabloyu sayimdan/degistirmeden HARIC tutmak sarttir (aksi halde
    mutant tablonun KENDISINI bozar, olculen kodu DEGIL)."""
    bas = govde.index(_TABLO_BAS)
    son = govde.index(_TABLO_SON, bas)
    return govde[:bas], govde[bas:son], govde[son:]


def _sha256_dosya(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _mutasyon_bataryasi():
    kaynak_yolu = os.path.abspath(__file__)
    modul_yolu = os.path.join(BETIK_DIZINI, "git_ortami.py")
    with open(kaynak_yolu, "r", encoding="utf-8") as f:
        govde = f.read()
    once_hash = hashlib.sha256(govde.encode("utf-8")).hexdigest()
    modul_once = _sha256_dosya(modul_yolu)
    _on, _tablo, _arka = _tablo_disi(govde)

    def kos(yol):
        r = subprocess.run([sys.executable, yol, "--kendini-test"],
                            capture_output=True, text=True)
        cikti = r.stdout + r.stderr
        dusen = set(re.findall(r"^\s*\[FAIL\]\s+(\S+?)\s", cikti, re.M))
        etiket = re.findall(r"^\s*\[(?:PASS|FAIL)\]\s+(\S+?)\s", cikti, re.M)
        return dusen, len(etiket), ("Traceback" in cikti)

    def iddialar(kume):
        """TEK-KIRMIZI hukmu YALNIZ beyan edilmis IDDIA-* etiketleri uzerinden verilir.
        KONTROL-* saglamlik nobetleridir ve bir mutantin YAN ETKISI olarak birlikte
        dusebilir (dosya basligindaki KONTROL-C notuyla ayni sozlesme)."""
        return {e for e in kume if e.startswith("IDDIA-")}

    hatalar = []
    with tempfile.TemporaryDirectory() as d:
        # Kopyalar TEK KAYNAK modulunu import eder; mutasyon YALNIZ kapi kopyasina
        # uygulanir, modul kopyasi DEGISTIRILMEZ (capa kapinin KENDI cagri yerindedir).
        shutil.copyfile(os.path.join(BETIK_DIZINI, "git_ortami.py"),
                        os.path.join(d, "git_ortami.py"))
        taban_yolu = os.path.join(d, "taban.py")
        with open(taban_yolu, "w", encoding="utf-8") as f:
            f.write(govde)
        t_dusen, t_sayi, t_cokme = kos(taban_yolu)
        print("TABAN: %d iddia, %d dusen, cokme=%s" % (t_sayi, len(t_dusen), t_cokme))
        if t_dusen or t_cokme:
            hatalar.append("TABAN temiz DEGIL: dusen=%s cokme=%s" % (sorted(t_dusen), t_cokme))

        beyan = [m[3] for m in MUTANTLAR if m[3]]
        if len(set(beyan)) != len(beyan):
            hatalar.append("IKI mutant AYNI iddiaya isaret ediyor: %s" % beyan)

        for ad, eski, yeni, bekle in MUTANTLAR:
            # 🔴 CAPA TAM BIR KEZ: 0 -> bayat tablo (sessiz yesil), >1 -> mutant
            # birden fazla yeri bozar, "TEK KIRMIZI" hukmu anlamini yitirir.
            n = _on.count(eski) + _arka.count(eski)
            if n != 1:
                hatalar.append("%s: capa %d kez eslesti (TAM 1 olmali)" % (ad, n))
                print("  [CAPA-HATASI] %-18s eslesme=%d" % (ad, n))
                continue
            m_yolu = os.path.join(d, "mutant.py")
            with open(m_yolu, "w", encoding="utf-8") as f:
                f.write(_on.replace(eski, yeni, 1) + _tablo + _arka.replace(eski, yeni, 1))
            dusen, sayi, cokme = kos(m_yolu)
            dusen = iddialar(dusen) if bekle else dusen
            if cokme:
                hatalar.append("%s COKTU (cokme kirmiziyla karisir)" % ad)
            if sayi != t_sayi:
                hatalar.append("%s: iddia sayisi %d, taban %d" % (ad, sayi, t_sayi))
            if bekle is None:
                ok = not dusen
                if not ok:
                    hatalar.append("KONTROL mutanti %s KIRMIZI yakti (dusen=%s) — batarya "
                                   "ayirt edici degil" % (ad, sorted(dusen)))
                print("  [%s] %-18s dusen=%s (KONTROL: YESIL kalmali)"
                      % ("YESIL" if ok else "SAPMA", ad, sorted(dusen)))
            else:
                ok = dusen == {bekle}
                if not ok:
                    hatalar.append("%s: dusen=%s, beyan={%s}" % (ad, sorted(dusen), bekle))
                print("  [%s] %-18s dusen=%s sayi=%d cokme=%s"
                      % ("OLDU" if ok else "SAPMA", ad, sorted(dusen), sayi, cokme))

    with open(kaynak_yolu, "r", encoding="utf-8") as f:
        sonra_hash = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
    modul_sonra = _sha256_dosya(modul_yolu)
    print("CANLI DOSYA sha256 once==sonra: %s" % (once_hash == sonra_hash))
    print("PAYLASILAN MODUL (git_ortami.py) sha256 once==sonra: %s"
          % (modul_once == modul_sonra))
    if once_hash != sonra_hash:
        hatalar.append("CANLI DOSYA DEGISTI — mutasyon kopyaya uygulanmali")
    if modul_once != modul_sonra:
        hatalar.append("PAYLASILAN MODUL DEGISTI — mutasyon yalniz KOPYAYA uygulanmali")
    print()
    if hatalar:
        print("MUTASYON BATARYASI KIRMIZI:")
        for h in hatalar:
            print("  - " + h)
        return 1
    oldurucu = len([m for m in MUTANTLAR if m[3]])
    print("MUTASYON BATARYASI YESIL: %d oldurucu mutant TEK KIRMIZI + beyana esit, "
          "%d KONTROL mutanti YESIL; iddia sayisi %d sabit; Traceback 0."
          % (oldurucu, len(MUTANTLAR) - oldurucu, t_sayi))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true",
                     help="offline kabul testi (izole gecici git deposu, ag YOK)")
    ap.add_argument("--kok", metavar="YOL", default=None,
                     help="OLCULECEK agac (varsayilan: BETIGIN kendi agaci; CWD ASLA)")
    ap.add_argument("--mutasyon", action="store_true",
                     help="kabul bataryasinin mutasyon kanitini kostur (kopyaya uygular)")
    args = ap.parse_args()

    if args.kendini_test:
        return _kendini_test()
    if args.mutasyon:
        return _mutasyon_bataryasi()

    kok, hata = kok_coz(args.kok, os.getcwd())
    if hata:
        print("IC RAPOR ADI KAPISI: OLCULEMEDI (fail-closed KIRMIZI)", file=sys.stderr)
        print(hata, file=sys.stderr)
        return RC_OLCULEMEDI
    ihlaller, dosya_sayisi = ana_tarama(kok)
    # 🔴 OLCULEN AGAC HER ZAMAN BASILIR (yesilde de): bir "temiz" ciktisi artik
    # sessizce BASKA bir agaca atfedilemez.
    print("IC RAPOR ADI KAPISI: olculen agac = %s (%d izlenen dosya tarandi)"
          % (kok, dosya_sayisi))
    if not ihlaller:
        print("IC RAPOR ADI KAPISI: temiz (0 muafiyet-disi isabet).")
        return RC_TEMIZ
    print("IC RAPOR ADI KAPISI: %d muafiyet-disi isabet bulundu:" % len(ihlaller))
    for yol, satir_no, satir in ihlaller:
        print("  %s:%d: %s" % (yol, satir_no, satir.strip()))
    print()
    print("COZUM: yorum/docstring METNINDEN dosya adini kaldir, anlamini koruyarak")
    print("genel ifadeyle yeniden yaz (or. 'muhendis raporunda'). Fiilen kullanilan")
    print("kod / delegasyon speci ise (bkz. bu dosyanin basligindaki MUAF listesi)")
    print("yukaridaki _MUAFIYET_GOVDESI'ne GEREKCEYLE ekle.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
