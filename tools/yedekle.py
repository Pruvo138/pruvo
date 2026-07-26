#!/usr/bin/env python3
"""Makine olursa kaybolacak yeri-doldurulamaz yerel dosyalari Drive'a yedekler.
Drive yolu tools/drive_yolu.py ile cozulur (kayitli .stl-backup-dir bayatsa kendini duzeltir).
Hedef: <Pruvo>/backup/  (memory klasoru + global skill'ler + .urun-kaynaklari.json + baglam .md'leri).

SIRLAR — IKI AYRI REJIM, KARISTIRMA:
  1. REPO KOKUNDEKI SANCAKLI SIR LISTESI (.thingiverse-token, .r2-credentials.json, ...):
     VARSAYILAN yedeklenmez; "--sirlar" ile ayni ozel Drive'a dahil edilir (klasoru PAYLASMA!).
  2. ~/.claude/skills AGACI: burada sir OLMAMASI gerekir; agac vetted degil (elle duzenlenen,
     git disi bir alan) -> ad kara-listesi + ad deseni + ICERIK imzasi ile KOSULSUZ elenir.
     Bu filtre "--sirlar" ile ACILMAZ: sancakli liste bilinen 5 dosyadir, skills agaci degil.
     Elenen her dosya SEBEBIYLE raporlanir (sessiz atlamak yok). Icerik imzasi bulunursa
     yalniz IMZA SINIFI basilir — eslesen metin ASLA ekrana/loga yazilmaz.

BAYAT SIR NOBETI: bu filtre 26 Tem'de eklendi; ondan onceki surum skills agacini FILTRESIZ
copytree ile kopyaliyordu. Hedefte elenmis bir dosyanin ESKI kopyasi duruyorsa gurultulu
uyarilir; "--sir-temizle" ile silinir (varsayilan SILMEZ — yedekten veri silmek elle onaylanir).

TAZELIK DAMGASI (26 Tem): kosum sonunda `backup/.son-yedek.json` yazilir (zaman + sayilar).
NEDEN DAMGA, NEDEN MTIME DEGIL: shutil.copy2 KAYNAK mtime'ini korur -> yedekteki dosyanin
mtime'i "yedek ne zaman kosuldu"yu DEGIL "kaynak ne zaman duzenlendi"yi soyler. Tazeligi
mtime'dan olcmek yaniltir (26 Tem: Drive'daki dosyalar 21 Tem gorunuyordu cunku kaynak o
tarihliydi). Damgayi `tools/durum.py` panosu okur -> bayatlik GORUNUR olur.

KILIT (26 Tem, `.yedek.lock`): bu betik artik HER push'ta (pre-push hook) kosuyor ve bu
repoda paralel oturum NORMAL -> eszamanli iki kosum AYNI hedefe yazardi (yarim/karismis
yedek) ve sonda damga yine "tam" derdi = SESSIZ HATA. Cozum: ROOT/.yedek.lock uzerinde
flock (`.urunler.lock` deseni).
  - NON-BLOCKING (LOCK_NB): kilit doluysa BEKLEMEYIZ -> push ASLA yavaslamaz/durmaz
    (pre-push fail-open sozlesmesi). Ayni isi zaten oteki kosum yapiyor.
  - ATLANAN kosum damgada `son_atlama*` alanlarina yazilir; GUVEN alanlarina (zaman/
    tam/sayilar) DOKUNMAZ -> atlanan kosum ASLA "tam yedek aldim" demez.
  - ATLAMA ZARARSIZ MI: iki OLCUM birden gerekir, biri bile tutmazsa pano UYARIR.
    (1) `son_atlama_kapsandi` — kosan yedek BASLARKEN butun degisiklikler yerinde
        miydi (atlama_kapsandi_mi)?  (2) `son_atlama_sahip_baslangici` — beklenen o
    kosum damgayi GERCEKTEN yazdi mi? Tek basina (1) bir VARSAYIMDIR: sahip kilidi
    alip asilir/olurse dosya yedege hic girmez ve pano esige kadar (2 gun) "taze"
    der. Kilit imzasi bu yuzden TAM HASSAS (repr) yazilir ve damganin `baslangic`i
    kilit alis aniyla BIREBIR AYNI sayidir — cozum esitlikle yapilabilsin diye
    (`%.3f` yuvarlamasi olculdu: 10000 kararin ~%46'si yanlis, test %37 flake).
  - `baslangic` alani: damga artik kosumun BASLANGIC anini da tasir. Kopyalama atomik
    degil; kosum basladiktan SONRA degisen dosya yedege girmemis olabilir. Bu yuzden
    hem `--gerekliyse` karari hem panonun "atlama kapsandi mi" karari `zaman` (bitis)
    degil `baslangic` ile verilir. Yoksa "atlandi" uyarisi ya hic temizlenmez ya da
    kapsanmayan bir degisiklik "taze" sayilir.
  - KILIT NEDEN BAYATLAMAZ: flock cekirdek tarafindan tutulur, surec olunce (crash,
    kill -9) OTOMATIK birakilir -> pid-dosyasi kilitlerindeki "olu surec sonsuza dek
    bloklar" sinifi burada YOK. Geriye kalan `.yedek.lock` DOSYASI 0 bayttir, kilit
    degildir; bilerek SILMEYIZ (silmek iki surecin AYRI inode kilitlemesine yol acar).
    Geriye tek patolojik hal kalir: YASAYAN ama asilmis sahip (cevapsiz Drive mount).
    Onu KIRMAYIZ (yasayan yaziciyi kirmak tam da onlemeye calistigimiz bozulmadir);
    GORUNUR yapariz: kilit dosyasina pid+baslangic yazilir, atlayan kosum bunu basar,
    1 saati asan sahip icin gurultulu uyarir, damga tazelenmedigi icin pano esikte
    "YEDEK BAYAT" der.

Kullanim:
    python3 tools/yedekle.py              # sirsiz (memory + skills + kaynak haritasi + .md)
    python3 tools/yedekle.py --kuru       # KURU KOSUM: ne kopyalanacagini listeler, YAZMAZ
    python3 tools/yedekle.py --gerekliyse # UCUZ MOD: son damgadan beri degisiklik yoksa CIKAR
    python3 tools/yedekle.py --sirlar     # + token + r2 creds (repo kokundeki sancakli liste)
    python3 tools/yedekle.py --sir-temizle  # hedefteki bayat sir kopyalarini SIL
"""
import fcntl
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time


def ana_calisma_agaci(taban=None):
    """Repo koku — DAIMA ANA calisma agaci, worktree DEGIL.

    `taban` verilirse o dizinden cozer (test bir WORKTREE yolu verip ANA agaci
    dondurdugunu kanitlayabilsin diye; varsayilan betigin kendi konumu).

    🔴 NEDEN (F1, 26 Tem — "sahte tazelik" hatasi): kok eskiden __file__'dan
    cozuluyordu (dirname(__file__)/..). Hook ise `git rev-parse --show-toplevel`
    kullanir -> WORKTREE'den push edilince ROOT=WORKTREE oluyordu. Worktree'de
    .urun-kaynaklari.json ve DEVAM-ARSIV.md gitignore'lu (YOK) -> o iki dosya
    TAZELENMIYOR ama TAM GUVEN damgasi yaziliyor ve panonun saati sifirlaniyordu.
    Bu repoda normal push ZATEN worktree push'u (mühendisler worktree'de calisir)
    -> hata surekli tetiklenirdi. Olculdu: pano "14 dk once" derken
    .urun-kaynaklari.json yedegi ~21 saat, DEVAM-ARSIV.md ~2 gun bayatti.
    Ayrica worktree'nin CLAUDE.md/DEVAM.md fotografi ana kopyanin UZERINE yaziliyordu.

    --git-common-dir worktree'de de ANA .git'i gosterir (durum.py'nin ana_repo()
    ile ayni yontem). Git yoksa __file__ tabanina duser."""
    if taban is None:
        taban = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    try:
        p = subprocess.run(["git", "-C", taban, "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True)
        ortak = p.stdout.strip()
        if p.returncode == 0 and ortak:
            return os.path.dirname(ortak.rstrip("/"))
    except OSError:
        pass
    return taban


ROOT = ana_calisma_agaci()
MEMORY = os.path.expanduser("~/.claude/projects/-Users-okan-dev-pruvo/memory")
SKILLS = os.path.expanduser("~/.claude/skills")

# Repo kokunden BEKLENEN dosyalar. Biri eksikse yedek KISMIDIR -> tam guven
# damgasi ATILMAZ (bkz. damga_yaz "tam" alani). Ilke: eksik yedek, eksik oldugunu SOYLER.
REPO_BEKLENEN = (".urun-kaynaklari.json", "CLAUDE.md", "DEVAM.md", "DEVAM-ARSIV.md")
REPO_SIR = (".thingiverse-token", ".r2-credentials.json", ".stl-backup-dir",
            ".onizleme-kapat-anahtar", ".mukerrer-istisna.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_yolu

BAYRAKLAR = {"--kuru", "--dry-run", "--gerekliyse", "--sirlar", "--sir-temizle", "-h", "--help"}

# Tazelik damgasi — backup/ kokunde. durum.py panosu BU dosyayi okur (tek kaynak).
DAMGA_ADI = ".son-yedek.json"

# Eszamanlilik kilidi — ANA calisma agacinin kokunde (gitignore'lu).
# NEDEN ROOT: ROOT worktree'den de ANA agaci gosterir (ana_calisma_agaci), yani
# worktree push'u ile main push'u AYNI kilit dosyasinda yarisir. Kilidi worktree'ye
# koysaydik iki farkli worktree'den gelen push'lar birbirini HIC gormezdi.
# NEDEN HEDEFTE (Drive) DEGIL: CloudStorage/FUSE mount'ta flock semantigi garanti
# degil; kilit yerel diskte olmali. Hedef zaten makine basina tek.
KILIT_ADI = ".yedek.lock"
KILIT_UYARI_YASI = 3600.0   # sn. Bundan uzun tutulan kilit "asili surec" suphesi -> gurultu.

# ---- GURULTU (turetilmis; sir DEGIL, sadece yedege deger etmez) --------------
GURULTU_DIZIN = {"__pycache__", ".git", "node_modules", ".venv", ".mypy_cache", ".pytest_cache"}
GURULTU_DOSYA = ("*.pyc", "*.pyo", ".DS_Store")

# ---- SIR NOBETI (skills agacinda kosulsuz) ----------------------------------
# Tam ad kara listesi: repoda bilinen sir dosyalari + CNAME (mimar emri: yedek paketine girmez).
SIR_ADLARI = {
    ".r2-credentials.json", ".thingiverse-token", ".stl-backup-dir",
    ".onizleme-kapat-anahtar", "cname", ".env", ".netrc", ".npmrc", ".pypirc",
    "credentials", "id_rsa", "id_ed25519", "id_ecdsa",
}
# Ad desenleri (kucuk harfe indirgenmis ad uzerinde fnmatch).
SIR_DESENLERI = (
    "*credential*", "*secret*", "*token*", "*passwd*", "*password*", "*apikey*",
    "*api-key*", "*api_key*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "*.keystore", "*.ppk", ".env.*", "*.env", "id_rsa*", "id_ed25519*", "*.asc",
)
# Icerik imzalari: YUKSEK SINYAL olanlar (yanlis-pozitif ucuz degil ama fail-closed sectik).
# (etiket, regex) -- rapora YALNIZ etiket girer, eslesen metin GIRMEZ.
SIR_IMZALARI = (
    ("ozel anahtar blogu", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS/R2 erisim anahtari", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub jetonu", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("Slack jetonu", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Anthropic API anahtari", re.compile(r"sk-ant-api[0-9]{2}-[A-Za-z0-9_\-]{20,}")),
    ("Google API anahtari", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("Cloudflare global key alani", re.compile(
        r"\"(?:secret_access_key|access_key_id|api_token|apiToken)\"\s*:\s*\"[^\"]{16,}\"")),
)
ICERIK_TARAMA_SINIRI = 2 * 1024 * 1024  # 2 MiB'den buyuk dosyanin yalniz basi taranir


def _gurultu_mu(ad):
    return any(fnmatch.fnmatch(ad, d) for d in GURULTU_DOSYA)


def _icerik_imzasi(yol):
    """Dosya icinde yuksek-sinyal kimlik imzasi varsa ETIKETINI dondurur, yoksa None.
    Okunamayan dosya -> fail-closed: 'okunamadi' etiketi (yedege ALINMAZ)."""
    try:
        with open(yol, "rb") as f:
            ham = f.read(ICERIK_TARAMA_SINIRI)
    except Exception as e:
        return "okunamadi (%s)" % type(e).__name__
    if b"\0" in ham[:8192]:
        return None  # ikili dosya: imza taramasi anlamsiz (gurultu zaten elenmis olur)
    metin = ham.decode("utf-8", "ignore")
    for etiket, kalip in SIR_IMZALARI:
        if kalip.search(metin):
            return etiket
    return None


def sir_sebebi(yol, ad):
    """Dosya sir sayiliyorsa INSANA OKUNUR sebep, degilse None.
    Sebep metni ASLA sirrin kendisini icermez (yalniz kural/imza sinifi)."""
    dusuk = ad.lower()
    if dusuk in SIR_ADLARI:
        return "ad kara listede"
    for desen in SIR_DESENLERI:
        if fnmatch.fnmatch(dusuk, desen):
            return "ad deseni: %s" % desen
    imza = _icerik_imzasi(yol)
    if imza:
        return "icerik imzasi: %s" % imza
    return None


def skills_plani(kok=None):
    """~/.claude/skills agacini tarar.

    Doner: (dahil, haric, gurultu)
      dahil   : [koke gorece yol]           -> yedege GIRER
      haric   : [(gorece yol, sebep)]       -> SIR nobeti eledi
      gurultu : [gorece yol | "<dizin>/ (dizin budandi)"]  -> turetilmis, alinmaz

    F4 DUZELTMESI (26 Tem): budanan dizinler (__pycache__ ...) RAPORLANIR. Eskiden
    os.walk budamasi sessizce yutuyordu -> kuru kosum "[skills-gurultu] 0" diyordu
    ama agacta 2 .pyc vardi (15 dosya -> 13+0+0 raporlaniyordu). "Elenen her sey
    raporlanir" iddiasi tutmuyordu. Dizin ADIYLA raporlanir, ICI GEZILMEZ: .git /
    node_modules gibi devasa dizinlerde sayim icin yuruyus yapmak pahaliya patlar.
    """
    kok = SKILLS if kok is None else kok
    dahil, haric, gurultu = [], [], []
    if not os.path.isdir(kok):
        return dahil, haric, gurultu
    for dizin, altlar, dosyalar in os.walk(kok):
        for budanan in sorted(a for a in altlar if a in GURULTU_DIZIN):
            gurultu.append(os.path.relpath(os.path.join(dizin, budanan), kok)
                           + "/ (dizin budandi)")
        altlar[:] = sorted(a for a in altlar if a not in GURULTU_DIZIN)
        for ad in sorted(dosyalar):
            tam = os.path.join(dizin, ad)
            gor = os.path.relpath(tam, kok)
            if os.path.islink(tam):
                # symlink hedefi agac disina cikabilir (sir sizma yolu) -> alinmaz.
                haric.append((gor, "symlink (hedefi agac disina cikabilir)"))
                continue
            if _gurultu_mu(ad):
                gurultu.append(gor)
                continue
            sebep = sir_sebebi(tam, ad)
            if sebep:
                haric.append((gor, sebep))
                continue
            dahil.append(gor)
    return sorted(dahil), sorted(haric), sorted(gurultu)


def skills_yaz(kok, hedef, dahil, haric, sir_temizle=False):
    """Plani hedefe yazar (idempotent: ayni dosya uzerine yazilir, mukerrer yigilmaz).

    Doner: (yazilan_sayisi, bayat_sir_yollari)
    bayat_sir: ELENMIS bir dosyanin hedefte duran ESKI kopyasi (filtresiz surumden kalma).
    """
    yazilan = 0
    for gor in dahil:
        kaynak = os.path.join(kok, gor)
        varis = os.path.join(hedef, gor)
        os.makedirs(os.path.dirname(varis), exist_ok=True)
        shutil.copy2(kaynak, varis)
        yazilan += 1
    bayat = []
    for gor, _sebep in haric:
        varis = os.path.join(hedef, gor)
        if os.path.exists(varis):
            bayat.append(varis)
            if sir_temizle:
                os.remove(varis)
    return yazilan, bayat


def _agac_dosyalari(kok):
    """Kuru kosum listelemesi icin: kokun altindaki tum dosyalar (gorece, sirali)."""
    cikti = []
    if not os.path.isdir(kok):
        return cikti
    for dizin, _altlar, dosyalar in os.walk(kok):
        for ad in dosyalar:
            cikti.append(os.path.relpath(os.path.join(dizin, ad), kok))
    return sorted(cikti)


def _repo_dosyalari(sirlar):
    """Repo kokunden yedeklenecek dosya adlari — BULUNANLAR (varsayilan + --sirlar)."""
    adlar = list(REPO_BEKLENEN) + (list(REPO_SIR) if sirlar else [])
    return [a for a in adlar
            if os.path.exists(os.path.join(ROOT, a)) and not os.path.islink(os.path.join(ROOT, a))]


def repo_eksikleri():
    """BEKLENEN ama repo kokunde OLMAYAN dosyalar. Bos degilse yedek KISMIDIR.
    (Sir listesi burada sayilmaz: onlar zaten kosullu/istege bagli.)"""
    return [a for a in REPO_BEKLENEN if not os.path.exists(os.path.join(ROOT, a))]


def kilit_yolu():
    """Kilit dosyasinin tam yolu (ANA calisma agacinin kokunde)."""
    return os.path.join(ROOT, KILIT_ADI)


SAHIP_OKUMA_DENEME = 5        # x SAHIP_OKUMA_ARALIGI = en fazla 100 ms (kilidi BEKLEMEZ)
SAHIP_OKUMA_ARALIGI = 0.02


def _sahip_imzasi(baslangic, pid=None):
    """Kilit dosyasina yazilan sahip satiri.

    🔴 TAM HASSASIYET (repr): imza eskiden `%.3f` ile MILISANIYEYE YUVARLANIYORDU,
    karsilastirma (atlama_kapsandi_mi) ise tam hassas mtime ile yapiliyordu ->
    yuvarlama yonune gore karar YANLIS cikiyordu. Olculdu: 200 denemenin 94'u (%47)
    yanlis; yedekle-test.py 16 kosumun 6'sinda kirmizi yaniyordu (flake). repr(float)
    Python'da TAM tur-donusu garantiler: float(repr(x)) == x."""
    return "pid=%d baslangic=%s iso=%s\n" % (
        os.getpid() if pid is None else pid, repr(float(baslangic)),
        time.strftime("%Y-%m-%d %H:%M:%S"))


def _imza_coz(metin):
    """Sahip satirindan (pid, baslangic) ayiklar. Bozuk/eksikse None doner."""
    pid = baslangic = None
    for parca in (metin or "").split():
        if parca.startswith("baslangic="):
            try:
                baslangic = float(parca.split("=", 1)[1])
            except ValueError:
                baslangic = None
        elif parca.startswith("pid="):
            try:
                pid = int(parca.split("=", 1)[1])
            except ValueError:
                pid = None
    return pid, baslangic


def _kilit_sahibi_bilgisi(fd, deneme=None, aralik=None):
    """Kilidi TUTAN kosumun kendi yazdigi satiri (pid + baslangic) okur.
    Kilitsiz okuma -> BEST EFFORT: bos/bozuksa 'bilgi yok' der, ASLA patlamaz.
    Doner: (metin, yas_saniye | None, sahip_baslangici | None).

    NEDEN KISA TEKRAR: sahip once flock alir, imzasini MIKROSANIYELER SONRA yazar.
    Eszamanli iki push tam bu bosluga dusuyor (olculdu: 3 turun 2'sinde) -> sahip
    baslangici okunamadigi icin atlama "kapsama bilinmiyor" = fail-closed uyari
    uretiyordu; her paralel push'ta bosuna sari pano (gurultulu pano = olu pano).
    Burada KILIT BEKLENMIYOR, yalnizca teshis satiri icin en fazla 100 ms okunuyor."""
    deneme = SAHIP_OKUMA_DENEME if deneme is None else deneme
    aralik = SAHIP_OKUMA_ARALIGI if aralik is None else aralik
    ham = ""
    for i in range(max(1, deneme)):
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            ham = os.read(fd, 256).decode("utf-8", "replace").strip()
        except OSError:
            ham = ""
        if ham:
            break
        if i + 1 < deneme:
            time.sleep(aralik)
    if not ham:
        return "sahip bilgisi yok", None, None
    _pid, baslangic = _imza_coz(ham)
    yas = None if baslangic is None else (time.time() - baslangic)
    return ham.replace("\n", " "), yas, baslangic


def atlama_kapsandi_mi(sahip_baslangici, kaynak_mtime):
    """ATLANAN kosumun isini, KOSMAKTA OLAN yedek kapsiyor mu? (saf fonksiyon)

    Kosan yedek `sahip_baslangici`nda basladi -> o andan ONCE degismis her kaynak
    onun kopyasina girer. Demek ki en yeni kaynak mtime'i sahip baslangicindan
    kucuk/esitse atlanan kosumun yapacagi FAZLADAN bir is YOKTU: atlama zararsiz.
    Aksi halde (ya da olcemedigimiz her halde) FAIL-CLOSED: kapsanmadi say, pano uyarsin.

    NEDEN ZAMAN TOLERANSI DEGIL: eszamanli iki push'ta sahip baslangici ile atlama
    ani mikrosaniyelerle ayrilir; "atlama baslangictan sonra mi" diye bakmak yazi-tura
    olur ve pano her paralel push'ta bosuna sariya doner (gurultulu pano = olu pano).
    Burada karar OLCUMLE veriliyor: degisen bir sey var miydi?"""
    if not isinstance(sahip_baslangici, (int, float)):
        return False
    if not isinstance(kaynak_mtime, (int, float)):
        return False
    return kaynak_mtime <= sahip_baslangici


def kilit_al(yol=None):
    """Yedeklemeyi tek kosuma serilestirir. BEKLEMEZ (LOCK_NB).

    Doner: (hal, fd, bilgi)
      hal 'alindi'     -> fd ile kilit BIZDE; bilgi = KILIT ALIS ANI (float).
                          Bu an damgaya `baslangic` olarak yazilir; boylece kilit
                          dosyasindaki imza ile damga BIREBIR AYNI degeri tasir
                          (atlayan kosum "sahibim damgayi yazdi mi" karsilastirmasini
                          esitlikle yapabilsin; time.time() MONOTON DEGIL, iki ayri
                          okuma milisaniye altinda geriye gidebiliyor).
      hal 'mesgul'     -> baska kosum yediyor; bilgi = (sahip satiri, yas, baslangic).
      hal 'kurulamadi' -> kilit dosyasi bile acilamadi (ROOT yazilamiyor).
                          FAIL-OPEN: cagiran KILITSIZ devam eder — yedegin hic
                          alinmamasi, nadir bir yaris ihtimalinden daha pahali.
    """
    yol = kilit_yolu() if yol is None else yol
    try:
        fd = os.open(yol, os.O_CREAT | os.O_RDWR, 0o600)
    except OSError as e:
        return "kurulamadi", None, ("kilit dosyasi acilamadi: %s" % e)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        bilgi = _kilit_sahibi_bilgisi(fd)
        os.close(fd)
        return "mesgul", None, bilgi
    alis = time.time()
    try:                                    # sahip imzasi: atlayan kosum bunu basar
        os.ftruncate(fd, 0)
        os.write(fd, _sahip_imzasi(alis).encode("utf-8"))
    except OSError:
        pass                                # imza kolaylik; kilit yine gecerli
    return "alindi", fd, alis


def kilit_birak(fd):
    """Kilidi birakir. Dosyayi SILMEZ (silmek iki surecin ayri inode kilitlemesine
    yol acar); icerigi temizler ki bayat 'sahip' satiri kimseyi yaniltmasin."""
    if fd is None:
        return
    try:
        try:
            os.ftruncate(fd, 0)
        except OSError:
            pass
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def damga_oku(backup):
    """backup/.son-yedek.json -> dict, yoksa/bozuksa None (ASLA patlamaz)."""
    try:
        with open(os.path.join(backup, DAMGA_ADI), encoding="utf-8", errors="replace") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return None
    return veri if isinstance(veri, dict) else None


def _damga_dosyasi_yaz(backup, veri):
    """Damgayi ATOMIK yazar (tmp + os.replace).

    NEDEN ATOMIK: damgaya iki ayri surec yazabilir — kilidi TUTAN kosum (damga_yaz)
    ve kilidi ALAMAYIP atlayan kosum (atlama_kaydet, kilit tutmaz). Duz `open(...,"w")`
    ile yarim/karismis JSON kalabilirdi. os.replace ile okuyucu DAIMA butun bir dosya
    gorur. Kalan tek yaris: atlayan kosumun oku-degistir-yaz'i, arada tamamlanan bir
    kosumun damgasini ESKI zamanla geri yazabilir -> tazelik OLDUGUNDAN ESKI gorunur,
    asla daha TAZE gorunmez. Yon bilerek boyle: sahte-yesil yasak, gereksiz sari serbest
    (bir sonraki kosum kendi kendine duzeltir)."""
    try:
        os.makedirs(backup, exist_ok=True)
        gecici = os.path.join(backup, DAMGA_ADI + ".tmp-%d" % os.getpid())
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(gecici, os.path.join(backup, DAMGA_ADI))
        return True
    except OSError as e:
        print("NOT: tazelik damgasi yazilamadi (%s) — yedek YINE DE alindi." % e)
        return False


def damga_yaz(backup, sayilar, eksik=None, baslangic=None, kilitsiz=False):
    """Kosum sonunda tazelik damgasini yazar. Basarisiz olursa YEDEGI BOZMAZ
    (uyari basar, cikis kodunu degistirmez) — damga bir kolaylik, yedek asil is.

    F1: `eksik` doluysa damga "tam": False ile isaretlenir. TAM GUVEN damgasi
    yalniz gercekten eksiksiz kosumda atilir; pano kismi yedegi TAZE SAYMAZ.

    `baslangic`: bu kosumun BASLADIGI an. Kopyalama atomik degil -> baslangictan
    SONRA degisen kaynak yedege girmemis olabilir; pano ve --gerekliyse karari bunu
    referans alir (bkz. modul basligi).
    ATLAMA KAYDI KORUNUR: onceki damgadaki `son_atlama*` alanlari tasinir — yoksa
    tamamlanan kosum, kendisinden ONCE atlanmis (ve dolayisiyla kapsanmamis olabilecek)
    bir kosumun izini siler ve pano o kaybi hic gormezdi."""
    eksik = list(eksik or [])
    onceki = damga_oku(backup) or {}
    veri = {"surum": 3, "zaman": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "baslangic": baslangic if isinstance(baslangic, (int, float)) else time.time(),
            "tam": not eksik, "eksik": eksik, "kok": ROOT}
    if kilitsiz:
        veri["kilitsiz"] = True
    # ONEK ILE tasi, ELLE LISTELEME: sabit liste bir kez eksik kaldi ve pano her
    # paralel push'ta bosuna uyardi (kabul testi yakaladi). Yeni bir `son_atlama_*`
    # alani eklendiginde burayi guncellemek GEREKMEZ.
    for alan in onceki:
        if alan.startswith("son_atlama"):
            veri[alan] = onceki[alan]
    veri.update(sayilar)
    return _damga_dosyasi_yaz(backup, veri)


def atlama_kaydet(backup, sebep, kapsandi=False, sahip_baslangici=None):
    """Kilit alinamadigi icin ATLANAN kosumu damgaya isler.

    🔴 GUVEN ALANLARINA DOKUNMAZ (zaman/iso/baslangic/tam/eksik/sayilar): bu kosum
    HICBIR SEY yedeklemedi; tazelik iddiasi son GERCEK kosuma aittir. Atlama yalniz
    `son_atlama*` alanlarina yazilir.

    IKI ALAN, IKI AYRI SORU (ikisi de OLCUM, varsayim DEGIL):
      `son_atlama_kapsandi`         -> atlama_kapsandi_mi(): kosan yedek BASLARKEN
                                       butun degisiklikler yerinde miydi?
      `son_atlama_sahip_baslangici` -> hangi kosumun BITMESINI bekliyoruz? Panoda
                                       damganin `baslangic`i bu degerden KUCUKSE o
                                       kosum damgayi HIC yazmamistir (asildi/oldu)
                                       -> pano UYARIR.
    🔴 NEDEN IKISI BIRDEN (curutucu senaryosu, 26 Tem): tek basina `kapsandi=True`
    "kosan yedek BITECEK" VARSAYIMIDIR. Sahip kilidi aldiktan sonra asilir/olurse
    dosya yedege hic girmez; atlayan kosum "kapsandi" demistir ve pano esige kadar
    (2 gun) "taze" der = tam da kapatmaya calistigimiz sessiz-hata sinifi. Bekleyen
    sahibin baslangicini yazip panoda COZUMLEYEREK varsayim olcume cevrilir.
    Damga dosyasi VAR ama OKUNAMIYORSA hic yazmayiz — gecici bir okuma hatasi
    yuzunden saglam bir tazelik kaydini yok etmeyelim."""
    yol = os.path.join(backup, DAMGA_ADI)
    veri = damga_oku(backup)
    if veri is None and os.path.exists(yol):
        print("NOT: damga okunamadi — atlama kaydi YAZILMADI (mevcut damga korundu).")
        return False
    veri = dict(veri or {})
    veri["son_atlama"] = time.time()
    veri["son_atlama_iso"] = time.strftime("%Y-%m-%d %H:%M:%S")
    veri["son_atlama_sebep"] = sebep
    veri["son_atlama_kapsandi"] = bool(kapsandi)
    if isinstance(sahip_baslangici, (int, float)):
        veri["son_atlama_sahip_baslangici"] = sahip_baslangici
    else:               # sahibi tanimlayamadik -> COZULEMEZ; pano fail-closed uyarir
        veri.pop("son_atlama_sahip_baslangici", None)
    return _damga_dosyasi_yaz(backup, veri)


def en_yeni_kaynak_mtime(sirlar=False):
    """Yedeklenecek kaynaklardaki EN YENI mtime. Hicbiri okunamazsa None.
    Ucuz: ~130 stat cagrisi (memory + skills + birkac repo dosyasi)."""
    enyeni = None
    for kok in (MEMORY, SKILLS):
        if not os.path.isdir(kok):
            continue
        for dizin, altlar, dosyalar in os.walk(kok):
            altlar[:] = [a for a in altlar if a not in GURULTU_DIZIN]
            for ad in dosyalar:
                try:
                    m = os.path.getmtime(os.path.join(dizin, ad))
                except OSError:
                    continue
                if enyeni is None or m > enyeni:
                    enyeni = m
    for ad in _repo_dosyalari(sirlar):
        try:
            m = os.path.getmtime(os.path.join(ROOT, ad))
        except OSError:
            continue
        if enyeni is None or m > enyeni:
            enyeni = m
    return enyeni


def gerekli_mi(damga, kaynak_mtime):
    """--gerekliyse karari (saf fonksiyon). FAIL-OPEN: emin olamadigimiz her halde
    YEDEKLE (damga yok/bozuk, mtime olculemedi). Yalniz 'damga var VE kaynak ondan
    eski' halinde atlar — yani atlamak KANITA bagli, yedeklemek varsayilan.

    REFERANS = `baslangic` (kosumun BASLADIGI an), varsa. Bitis (`zaman`) ile
    karsilastirmak yaniltir: kopyalama atomik degil, kosum SIRASINDA degisen dosya
    yedege girmemis olabilir ama mtime'i bitisten KUCUK oldugu icin "guncel" sayilirdi.
    Eski surum damgalarinda `baslangic` yok -> `zaman`a duser (davranis degismez)."""
    if not isinstance(damga, dict):
        return True
    referans = damga.get("baslangic")
    if not isinstance(referans, (int, float)):
        referans = damga.get("zaman")
    if not isinstance(referans, (int, float)):
        return True
    if kaynak_mtime is None:
        return True
    return kaynak_mtime > referans


def main():
    # --help yedekleme BASLATMASIN (denetim 2026-07-15: --help dogrudan yaziyordu).
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__.strip())
        return 0
    # BILINMEYEN BAYRAK = FAIL-CLOSED. Yazim hatasi ("--kuruu") sessizce GERCEK yedek
    # baslatmasin; ayni sinif hata --help'te bir kez yasandi.
    bilinmeyen = [a for a in sys.argv[1:] if a not in BAYRAKLAR]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        print("Gecerli: " + ", ".join(sorted(BAYRAKLAR)), file=sys.stderr)
        return 2

    kuru = ("--kuru" in sys.argv) or ("--dry-run" in sys.argv)
    gerekliyse = "--gerekliyse" in sys.argv
    sirlar = "--sirlar" in sys.argv
    sir_temizle = "--sir-temizle" in sys.argv

    dahil, haric, gurultu = skills_plani()

    # ---- KURU KOSUM: hicbir sey yazma, sadece plani bas -------------------
    if kuru:
        pruvo_drive = drive_yolu.pruvo_dizini(sessiz=True)
        hedef = os.path.join(pruvo_drive, "backup") if pruvo_drive else None
        print("KURU KOSUM — hicbir dosya YAZILMADI.")
        print("Hedef: " + (hedef or "(Drive COZULEMEDI — gercek kosumda yedek ALINMAZ)"))
        mem = _agac_dosyalari(MEMORY)
        print("-" * 70)
        print("[memory] %d dosya  <- %s" % (len(mem), MEMORY))
        for g in mem:
            print("    memory/" + g)
        print("[skills] %d dosya  <- %s" % (len(dahil), SKILLS))
        for g in dahil:
            print("    skills/" + g)
        print("[skills-HARIC (sir nobeti)] %d dosya" % len(haric))
        for g, sebep in haric:
            print("    skills/%s   -> ELENDI: %s" % (g, sebep))
        print("[skills-gurultu (turetilmis)] %d giris" % len(gurultu))
        for g in gurultu:
            print("    skills/" + g)
        repo = _repo_dosyalari(sirlar)
        print("[repo] %d dosya  <- %s%s"
              % (len(repo), ROOT, "  (--sirlar ACIK)" if sirlar else ""))
        for a in repo:
            print("    " + a)
        eksik = repo_eksikleri()
        print("[repo-EKSIK (beklenen ama yok)] %d" % len(eksik))
        for a in eksik:
            print("    %s   -> KISMI YEDEK: damga 'tam: false' olur" % a)
        print("-" * 70)
        print("TOPLAM YEDEKLENECEK: %d dosya (memory %d + skills %d + repo %d)"
              % (len(mem) + len(dahil) + len(repo), len(mem), len(dahil), len(repo)))
        if haric:
            print("SIR NOBETI: %d dosya paket DISINDA birakilacak." % len(haric))
        damga = damga_oku(hedef) if hedef else None
        print("TAZELIK DAMGASI: %s" % (damga.get("iso") if damga else "(yok)"))
        print("--gerekliyse karari: %s"
              % ("YEDEKLE" if gerekli_mi(damga, en_yeni_kaynak_mtime(sirlar)) else "ATLA (guncel)"))
        # Kilit DENENMEZ: kuru kosumda kilidi bir an icin almak, o sirada kosan
        # GERCEK bir yedegi atlatirdi. Sadece dosya icerigine bakilir (best effort).
        tutuluyor = ""
        try:
            with open(kilit_yolu(), encoding="utf-8", errors="replace") as f:
                tutuluyor = f.read(256).strip()
        except OSError:
            pass
        print("KILIT: %s   %s" % (kilit_yolu(),
                                  ("(su an TUTULUYOR gorunuyor: %s)" % tutuluyor.replace("\n", " "))
                                  if tutuluyor else "(bos — tutulmuyor gorunuyor)"))
        return 0

    # ---- GERCEK KOSUM ----------------------------------------------------
    # Drive yolunu drive_yolu cozer: bayatsa kendi duzeltir, mount yoksa uyarip None doner.
    # None'da DURUYORUZ — eskiden makedirs Drive yerine sahte yerel klasor yaratip "yedeklendi" diyordu.
    pruvo_drive = drive_yolu.pruvo_dizini(sessiz=gerekliyse)   # .../Pruvo
    if not pruvo_drive:
        print("Yedek ALINMADI — Drive yolu cozulemedi (yukaridaki uyariya bak).")
        return 1
    backup = os.path.join(pruvo_drive, "backup")

    # ---- KILIT: eszamanli iki kosum AYNI hedefe yazmasin -----------------
    # Kilit, --gerekliyse kararindan ONCE alinir: karar damgayi okur, damgayi da
    # kosan kosum yazar; kilitsiz okumak yarim/eski damgadan karar vermek olurdu.
    hal, kilit_fd, kilit_bilgi = kilit_al()
    if hal == "mesgul":
        sahip, yas, sahip_baslangici = kilit_bilgi
        kapsandi = atlama_kapsandi_mi(sahip_baslangici, en_yeni_kaynak_mtime(sirlar))
        print("yedek ATLANDI — baska bir yedek kosuyor (%s)." % sahip)
        print("  kilit: %s   (BEKLEMEDIK: push ASLA yavaslamaz/durmaz)" % kilit_yolu())
        if kapsandi:
            print("  kosan yedek bu kosumun isini kapsiyor (hicbir kaynak onun "
                  "baslangicindan sonra degismemis) — BITIRIRSE. Bitirmezse damgadaki "
                  "sahip baslangici cozulemez kalir ve pano UYARIR.")
        else:
            print("  ⚠️ kosan yedek bu degisiklikleri KAPSAMAYABILIR -> damgaya islendi; "
                  "pano '7) YEDEK TAZELIGI' uyaracak.")
        if yas is not None and yas > KILIT_UYARI_YASI:
            print("  ⚠️ kilit %.1f saattir tutuluyor — sahip surec ASILMIS olabilir "
                  "(cevapsiz Drive mount?). Kilidi KIRMIYORUZ (yasayan yazici veriyi "
                  "bozar); yedek bayatlarsa pano '7) YEDEK TAZELIGI' bunu gosterir."
                  % (yas / 3600.0))
        atlama_kaydet(backup, "baska yedek kosuyordu (%s)" % sahip, kapsandi=kapsandi,
                      sahip_baslangici=sahip_baslangici)
        return 0                     # FAIL-OPEN: pre-push bu koda BAKAR, 0 = push devam
    if hal == "kurulamadi":
        print("UYARI: %s — yedek KILITSIZ kosuyor (eszamanli kosum varsa yaris riski)."
              % kilit_bilgi, file=sys.stderr)

    try:
        return _yedekle(backup, gerekliyse, sirlar, sir_temizle, dahil, haric,
                        kilitsiz=(hal == "kurulamadi"),
                        baslangic=kilit_bilgi if hal == "alindi" else None)
    finally:
        kilit_birak(kilit_fd)


def _yedekle(backup, gerekliyse, sirlar, sir_temizle, dahil, haric, kilitsiz=False,
             baslangic=None):
    """Asil kopyalama — DAIMA kilit altinda cagrilir (bkz. main).

    `baslangic` = KILIT ALIS ANI (kilit_al'in dondurdugu deger). Kilit dosyasindaki
    imzayla BIREBIR ayni sayi olmali: atlayan kosum "bekledigim sahip damgayi yazdi
    mi" sorusunu esitlikle cozuyor. Burada yeniden time.time() cagirmak, time.time()
    monoton olmadigi icin damgayi imzadan KUCUK yapabilirdi (olculdu: -0,0003 sn)."""
    if not isinstance(baslangic, (int, float)):
        baslangic = time.time()     # kilitsiz yol (kilit kurulamadi)

    # UCUZ MOD (pre-push hook'u icin): son damgadan beri hicbir kaynak degismediyse
    # tek dosya bile kopyalama. Karar gerekli_mi()'de — fail-open (suphede yedekler).
    if gerekliyse:
        damga = damga_oku(backup)
        if not gerekli_mi(damga, en_yeni_kaynak_mtime(sirlar)):
            print("yedek GUNCEL (son damga: %s) — degisiklik yok, kopyalanmadi."
                  % damga.get("iso", "?"))
            return 0

    os.makedirs(os.path.join(backup, "memory"), exist_ok=True)

    # memory klasoru
    if os.path.isdir(MEMORY):
        shutil.copytree(MEMORY, os.path.join(backup, "memory"), dirs_exist_ok=True)
        print("yedek: memory/ ->", os.path.join(backup, "memory"))

    # ~/.claude/skills/ — global skill'ler (merge-kapisi dahil) GIT DISINDA tutuluyor
    # (mimar karari 21 Tem: repoya tasinmayacak) -> TEK kopya bu makinede. Yedeklenmezse
    # disk kaybinda SKILL.md + dal-olc.py + kabul-test.py (davranissal batarya) topluca gider.
    # Artik copytree DEGIL dosya-dosya: her dosya sir nobetinden gecer (bkz. sir_sebebi).
    yazilan = 0
    if os.path.isdir(SKILLS):
        hedef = os.path.join(backup, "skills")
        yazilan, bayat = skills_yaz(SKILLS, hedef, dahil, haric, sir_temizle=sir_temizle)
        print("yedek: skills/ -> %s  (%d dosya)" % (hedef, yazilan))
        for g, sebep in haric:
            print("  SIR NOBETI — paket DISI: skills/%s  (%s)" % (g, sebep))
        for yol in bayat:
            if sir_temizle:
                print("  BAYAT SIR KOPYASI SILINDI: " + yol)
            else:
                print("  ⚠️ BAYAT SIR KOPYASI hedefte DURUYOR: " + yol
                      + "   (silmek icin: python3 tools/yedekle.py --sir-temizle)")
    else:
        print("NOT: %s yok -> skill yedegi ATLANDI." % SKILLS)

    # Sirsiz kaynak haritasi + ajan baglam dosyalari. HEPSI GITIGNORE'DA (repo public, icerik
    # ticari gizli) -> git'te KOPYASI YOK, yani bu makine olurse tamamen kaybolurlardi.
    # (AGENTS.md kopyalanmaz: CLAUDE.md'ye symlink, ayri dosya degil.)
    repo_adlari = _repo_dosyalari(sirlar=False)
    for ad in repo_adlari:
        shutil.copy2(os.path.join(ROOT, ad), os.path.join(backup, ad))
        print("yedek:", ad)

    if sirlar:
        for name in (".thingiverse-token", ".r2-credentials.json", ".stl-backup-dir",
                     ".onizleme-kapat-anahtar", ".mukerrer-istisna.json"):
            p = os.path.join(ROOT, name)
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(backup, name))
                print("yedek (SIR):", name)
        print("NOT: bu klasoru kimseyle PAYLASMA — sir icerir.")

    # TAZELIK DAMGASI — en sonda: yalniz kosum GERCEKTEN tamamlandiysa yazilir.
    # (Basta yazilsaydi yarida patlayan bir kosum "taze" gorunurdu = sahte guven.)
    eksik = repo_eksikleri()
    if eksik:
        print("⚠️ KISMI YEDEK — repo kokunde BULUNAMAYAN beklenen dosya(lar): %s"
              % ", ".join(eksik))
        print("   kok: %s   (damga 'tam: false' isaretlenecek, pano TAZE SAYMAYACAK)" % ROOT)
    damga_yaz(backup, {"memory": len(_agac_dosyalari(MEMORY)),
                       "skills": yazilan, "skills_haric": len(haric),
                       "repo": len(repo_adlari)}, eksik=eksik,
              baslangic=baslangic, kilitsiz=kilitsiz)

    print("bitti ->", backup)
    return 0


if __name__ == "__main__":
    sys.exit(main())
