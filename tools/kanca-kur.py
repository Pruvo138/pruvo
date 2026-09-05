#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kanca-kur.py — git kanca KABLOLAMASINI IZLENEN kaynaktan KUR (FAIL-CLOSED).

NE YAPAR: izlenen `tools/kancalar` kaynagindan, ORTAK `.git` dizini altindaki
`pruvo-kancalar/` dizinine bir KOPYA serer ve ANA checkout'un `core.hooksPath`
ayarini o kopyanin MUTLAK yoluna baglar. Boylece kancalar `.git/hooks` altinda
(commit EDILMEYEN, tek makinede yasayan, elle duzenlenen) dosyalar olmaktan
cikar; kaynak DEPODA yasar, gozden gecirilir, mutasyona ugratilir ve her klonda
AYNIDIR — kurulan kopya ise kaynaktan SAPAMAZ (drift nobetcisi, asagida).

🔴 NEDEN GEREKTI (4 Agu 2026, olculdu): `tools/urunler-guard.py` katalog verisini
koruyan FAIL-LOUD bir nobetciye cevrildi, ama `.git/hooks/pre-commit` icinde
    python3 "$guard" --tetik commit >/dev/null 2>&1 || true
duruyordu — git-native yol FAIL-OPEN'di: cikis kodu da gerekce de yutuluyordu.
Koruma yalniz bu makinenin oturum kablosuyla (PreToolUse) blokluyordu; DUZ
TERMINALDE, emekli motor'TE ve BASKA BIR MAKINEDE hic bloklamiyordu.

═══════════════════════════════════════════════════════════════════════════════
🔴 DEGER SECIMI — GORELI YOL OLCULEREK ELENDI (KUSUR 2, mimar iadesi)
═══════════════════════════════════════════════════════════════════════════════
Ilk tasarim `core.hooksPath = tools/kancalar` (GORELI) idi. Goreli deger git
tarafindan ILGILI AGACIN TEPESINE gore cozulur — yani HER worktree KENDI
agacindaki kancalari kosar. Kulaga dogru gelir; OLCULDU ki YIKICIDIR:

    ana checkout (tools/kancalar VAR)        commit rc=0  kosan: pre-commit, commit-msg, post-commit
    ESKI dal worktree'si (dizin YOK)         commit rc=0  kosan: 🔴 HICBIRI  (SESSIZ)
    ana checkout ESKI commit'e alinirsa      commit rc=0  kosan: 🔴 HICBIRI  (SESSIZ)

`tools/kancalar` TASIMAYAN her agacta git, var olmayan bir dizini kanca dizini
sanar ve HICBIR kancayi UYARISIZ kosmaz: katalog guard'i, mukerrer kontrolu,
mimar kapisi, commit-mesaji sizinti kapisi ve **pre-push D1 SENKRONU** oradan
sessizce duserdi. Bu, tam da kapatilmak istenen [[kanca-sessiz-devre-disi]]
deligini YENI BIR YERDE yeniden uretmek olurdu (D1 sessiz kaymasi bu depoda
"site gosterir, EGE GOREMEZ" demektir).

ELENEN SECENEKLER (hepsi kosularak olculdu):
  1. GORELI `tools/kancalar` — yukaridaki tablo. ELENDI.
  2. MUTLAK `<ana checkout>/tools/kancalar` — worktree'lerde kancalar yasar
     (olculdu), AMA (a) ana checkout eski bir commit'e alininca yine HICBIRI
     kosmaz, (b) ana agacta yapilan her `git checkout` TUM worktree'lerin
     kancalarini sessizce degistirir (calisma agaci = kablolama). ELENDI.
  3. Kopyayi `.git/hooks` UZERINE sermek (hic `core.hooksPath` yazmadan) —
     calisir (ortak dizin), ama (a) makinede var olan kancalarin UZERINE yazar,
     (b) "kablolama kurulu mu" sorusu artik config'ten OLCULEMEZ, yalniz
     bayt-karsilastirmasiyla tahmin edilir. ELENDI.
  4. ✅ SECILEN: kopya ORTAK `.git/pruvo-kancalar/` altina serilir,
     `core.hooksPath` o kopyanin MUTLAK yoluna baglanir.
     * `.git` ORTAK dizindir -> ana checkout + TUM worktree'ler ayni kopyayi
       kosar, agacin hangi commit'te oldugundan BAGIMSIZ (olculdu: eski dal
       worktree'sinde de pre-commit/commit-msg/post-commit KOSTU).
     * Mutlak -> calisma agacinin icerigine hic bagli degil.
     * `.git/hooks` UZERINE yazilmaz (ayri dizin); oradaki eski kancalar
       yedeklenir ve devre disi kalir.
     * Kopya kaynaktan SAPABILIR -> bu bir BEDELDIR ve karsiligi
       tools/kanca-kablolama-nobeti.py'nin SAPMA eksenidir (bayt-esitligi;
       sapma KIRMIZI).
     * Izole worktree'nin `config.worktree` override'i (`/dev/null`) bu mutlak
       degeri de EZER (olculdu) -> Claude Code izolasyonu KORUNUR.

═══════════════════════════════════════════════════════════════════════════════
🔴 KAPSAM BAYRAGI — BU DOSYANIN EN TEHLIKELI SATIRI
═══════════════════════════════════════════════════════════════════════════════
Bu depoda OLCULMUS tuzak vardir ([[kanca-sessiz-devre-disi]]): bir LINKED
WORKTREE icinde BAYRAKSIZ `git config core.hooksPath ...` yazmak degeri
PAYLASILAN `.git/config`'e yazar (rc=0, UYARI YOK) ve ANA CHECKOUT ile TUM
worktree'lerin kancalarini ayni anda oldurur — D1 senkronu dahil.

BU MAKINEDE OLCULDU (git 2.50.1, sentetik depolarla):
  * worktree'den BAYRAKSIZ `git config core.hooksPath X`  -> PAYLASILAN .git/config
  * worktree'den `git config --local core.hooksPath X`    -> PAYLASILAN .git/config
  * worktree'den `git config --worktree core.hooksPath X` -> .git/worktrees/<w>/config.worktree
  * `--worktree` deger `--local` degerini EZER (izole worktree override'i korunur)

SECIM: `--local` + ACIKCA `git -C <ANA CHECKOUT>`.
  * Kapsam ASLA cari dizine BIRAKILMAZ: hedef once `--git-common-dir`den
    turetilir, komut `-C <ana checkout>` ile kosar, YAZILAN KOMUT BASILIR.
  * `--global` / `--system` KULLANILMAZ: makinedeki BASKA depolari kirletirdi.
  * `--worktree` KULLANILMAZ: kablolama tek bir worktree'de kalir, ana checkout
    korumasiz kalirdi.

═══════════════════════════════════════════════════════════════════════════════
FAIL-CLOSED SOZU: kuramadigi HER halde sifir-disi cikar ve NEDENINI basar.
"Kuruldu" ASLA VARSAYILMAZ — yazimdan SONRA etkin deger yeniden okunur, dizine
cozulur, kancalar orada + calistirilabilir mi ve KAYNAKLA BAYT-ESIT mi diye
BAKILIR (kur -> DOGRULA halkasi kapanir).

IDEMPOTENT: zaten dogru kabloluysa ve kopya guncelse hicbir sey YAZILMAZ.

🔴 DELIK 2 KAPISI (mimar iadesi): bulundugumuz LINKED WORKTREE kendi
`config.worktree`sinde `core.hooksPath`i BASKA yere baglamissa, kurulan `--local`
degeri o worktree'de GOLGELENIR ve worktree ESKI fail-open kancalari kosturmaya
DEVAM EDER. Dogrulama artik o worktree'nin FIILEN halini de olcer; gercek-yol
golge varsa "ETKIN ✅" DEMEZ, sifir-disi cikip gercek careyi basar. (/dev/null
golgesi KASITLI izolasyondur -> NOT basilir, hata degil.)

🔴 DELIK 1 KAPISI: `git pull` izlenen kaynagi guncelleyince kurulan KOPYA bayat
kalir. `--tazele` (kanca govdelerinden + post-merge/post-checkout'tan cagrilir)
kopya bayatsa yeniden serer ve TAZELE_BAYATTI (3) doner; kanca bunu gorunce
commit/push'u DURDURUR -> bayat mantik ASLA sessizce kosmaz.

Kullanim:
    python3 tools/kanca-kur.py            # kur/tazele + DOGRULA (rc 0/1)
    python3 tools/kanca-kur.py --kuru     # hicbir sey yazma, ne yapacagini yaz
    python3 tools/kanca-kur.py --dogrula  # yalniz dogrula (kurma)
    python3 tools/kanca-kur.py --tazele   # kopya bayatsa yeniden ser (kanca ici;
                                          # rc 3 = bayatti+tazelendi, 0 = guncel)
    python3 tools/kanca-kur.py --depo X   # baska bir checkout'u hedefle (test/tani)
"""
import os
import shutil
import stat
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))

# IZLENEN kaynak dizinin repo-goreli adi. TEK KAYNAK: nobetci ve kabul testi
# bu sabitleri IMPORT eder, KOPYALAMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
KANCA_DIZINI = "tools/kancalar"

# KURULAN kopyanin ORTAK `.git` dizini altindaki adi. `.git/hooks` DEGIL:
# oradaki (elle duzenlenmis, fail-open) kancalarin uzerine yazilmaz.
KURULU_DIZIN_ADI = "pruvo-kancalar"

AYAR = "core.hooksPath"
KAPSAM = "--local"

BEKLENEN_KANCALAR = ("pre-commit", "commit-msg", "pre-push", "post-commit",
                     "post-checkout", "post-merge")

# `--tazele` cikis kodu: kopya BAYATTI ve YENIDEN SERILDI. Kancalar bu kodu
# GORUNCE commit/push'u DURDURUR ("kopya bayatti, tazelendi, tekrar dene") —
# boylece BAYAT mantik ASLA sessizce kosmaz (DELIK 1 onarimi).
TAZELE_BAYATTI = 3


class Hata(Exception):
    """Kurulamama/dogrulanamama — cagirici sifir-disi cikar."""


def _git(cwd, *args):
    """(rc, stdout, stderr) — git yoksa/donarsa fail-closed tani doner."""
    try:
        p = subprocess.run(["git", "-C", cwd] + list(args),
                           capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return 127, "", "git binary'si PATH'te YOK"
    except subprocess.TimeoutExpired:
        return 124, "", "git 30 sn icinde yanit vermedi"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def ortak_git_dizini(baslangic):
    """ORTAK `.git` dizini (linked worktree'de de ANA deponunki)."""
    rc, cikti, hata = _git(baslangic, "rev-parse", "--path-format=absolute",
                           "--git-common-dir")
    if rc != 0 or not cikti:
        raise Hata("ortak git dizini bulunamadi (git rev-parse rc=%d): %s"
                   % (rc, hata or "?"))
    return cikti


def ana_checkout(baslangic):
    """ANA checkout'un koku. Linked worktree'den kosulsa da ANA'yi bulur.

    🔴 KAPSAM GUVENLIGININ ILK HALKASI: yazma komutu bu yola `-C` ile
    baglanir, cari dizine ASLA birakilmaz."""
    ortak = ortak_git_dizini(baslangic)
    if os.path.basename(ortak) != ".git":
        raise Hata("ortak git dizini '.git' ile bitmiyor (bare depo?): %s" % ortak)
    return os.path.dirname(ortak)


def kurulu_dizin(baslangic):
    """Kurulan kopyanin MUTLAK yolu: <ortak .git>/pruvo-kancalar."""
    return os.path.join(ortak_git_dizini(baslangic), KURULU_DIZIN_ADI)


def kanca_kaynagi(kok):
    """(mutlak yol) — IZLENEN kanca kaynagi; yoksa/eksikse FAIL-CLOSED."""
    yol = os.path.join(kok, KANCA_DIZINI)
    if not os.path.exists(yol):
        raise Hata("izlenen kanca dizini YOK: %s -> kurulacak bir sey yok "
                   "(yanlis depo mu, ya da agac eski bir commit'te mi?)" % yol)
    if not os.path.isdir(yol):
        raise Hata("%s bir DIZIN degil -> kaynak olarak kullanilamaz" % yol)
    eksik = [a for a in BEKLENEN_KANCALAR
             if not os.path.isfile(os.path.join(yol, a))]
    if eksik:
        raise Hata("izlenen kanca dizininde EKSIK kanca(lar): %s -> kablolama "
                   "yarim koruma olurdu" % ", ".join(eksik))
    return yol


def sapma(kaynak_dizin, kurulu):
    """[ad, ...] — kurulan kopyanin kaynaktan BAYT olarak saptigi kancalar.

    🔴 SECILEN TASARIMIN BEDELI: kopya, izlenen kaynagin bir SURETIDIR ve elle
    duzenlenebilir. Sapma sessiz kalirsa "depoda fail-closed, makinede
    fail-open" hali geri doner — o yuzden sapma bir KAPI eksenidir."""
    sapanlar = []
    for ad in BEKLENEN_KANCALAR:
        k = os.path.join(kaynak_dizin, ad)
        h = os.path.join(kurulu, ad)
        if not os.path.isfile(h):
            sapanlar.append("%s (kurulu kopyada YOK)" % ad)
            continue
        try:
            if open(k, "rb").read() != open(h, "rb").read():
                sapanlar.append("%s (icerik SAPMIS)" % ad)
        except OSError as e:
            sapanlar.append("%s (okunamadi: %s)" % (ad, e))
    return sapanlar


def cari_toplevel(baslangic):
    """(yol|None) — <baslangic>'in bulundugu calisma agacinin tepesi."""
    rc, cikti, _h = _git(baslangic, "rev-parse", "--path-format=absolute",
                         "--show-toplevel")
    return cikti if rc == 0 and cikti else None


def en_iyi_kaynak(baslangic, ana_kok):
    """(kaynak_dizin|None) — sapma/tazeleme icin en guvenilir izlenen kaynak.

    🔴 KUSUR 2 dersinin ikizi: kaynak ONCE bulundugumuz agactan alinir (o agac
    izlenen `tools/kancalar`i tasiyorsa), yoksa ANA checkout'tan. Ikisi de
    tasimiyorsa (agac eski bir commit'te) kaynak YOKTUR -> kopya otoritedir,
    tazeleme yapilamaz (bu SESSIZ olum DEGILDIR: kurulu kopya ortak `.git`
    altindadir ve kosar)."""
    cari = cari_toplevel(baslangic)
    for aday in (cari, ana_kok):
        if not aday:
            continue
        dizin = os.path.join(aday, KANCA_DIZINI)
        if os.path.isdir(dizin) and all(
                os.path.isfile(os.path.join(dizin, a)) for a in BEKLENEN_KANCALAR):
            return dizin
    return None


def tazele(baslangic):
    """(rc, mesaj) — kurulu kopya izlenen kaynaktan BAYATSA yeniden ser.

    🔴 DELIK 1 ONARIMI: `git pull` izlenen kaynagi guncelleyince kopya BAYAT
    kalir ve commit aninda SESSIZCE eski mantigi kosturur. Bu fonksiyon kanca
    govdesinden (pre-commit/pre-push basi) ve post-merge/post-checkout'tan
    cagrilir.

    Cikis:
      0             -> kopya zaten GUNCEL, ya da karsilastirilacak kaynak YOK
                       (agac eski commit'te) -> yapacak sey yok, commit devam.
      TAZELE_BAYATTI-> kopya BAYATTI, YENIDEN SERILDI. Cagiran kanca commit'i
                       DURDURUR (sonraki commit taze mantikla kosar).
      1             -> tazeleme HATASI (fail-closed: cagiran kanca durdurur)."""
    try:
        ana_kok = ana_checkout(baslangic)
        kurulu = kurulu_dizin(baslangic)
    except Hata as e:
        return 1, "tazeleme baglami cozulemedi: %s" % e
    kaynak_dizin = en_iyi_kaynak(baslangic, ana_kok)
    if kaynak_dizin is None:
        return 0, "karsilastirilacak izlenen kaynak yok (agac eski commit'te olabilir)"
    sapanlar = sapma(kaynak_dizin, kurulu)
    if not sapanlar:
        return 0, "kurulu kopya guncel"
    try:
        _ser(kaynak_dizin, kurulu, kuru=False)
    except Hata as e:
        return 1, "kopya bayatti ama YENIDEN SERILEMEDI: %s" % e
    return TAZELE_BAYATTI, ("kurulu kopya BAYATTI (%s) -> yeniden serildi (kaynak: %s)"
                            % (", ".join(sapanlar), kaynak_dizin))


def golge_worktree_kontrol(baslangic, kurulu):
    """(tamam, mesaj) — bulundugumuz worktree kurulan degeri GOLGELIYOR mu?

    🔴 DELIK 2 ONARIMI ([[hukum-yanlis-birimde]]): kurulum `--local` degeri ANA
    checkout'un paylasilan config'ine yazar. Bir LINKED WORKTREE kendi
    `config.worktree`sinde `core.hooksPath`i FARKLI bir yere baglamissa (or.
    eski `.git/hooks`), o worktree kurulumdan SONRA da ESKI fail-open kancalari
    kosturur — kurulum ise ANA agaci dogrulayip "ETKIN ✅" der. Yanlis birimde
    yesil. Bu kontrol o worktree'nin FIILEN halini yargilar.

    hal:
      tamam=True  -> golge yok, ya da golge KASITLI izolasyon (/dev/null +
                     config.worktree). Ikinci halde mesaj NOT'tur, hata degil.
      tamam=False -> gercek-yol golge: worktree kurulan degeri golgeliyor ve
                     ESKI kancalari kosturuyor -> FAIL-CLOSED + gercek care."""
    top = cari_toplevel(baslangic)
    if not top:
        return True, None
    try:
        ana_kok = ana_checkout(baslangic)
    except Hata:
        return True, None
    if os.path.normpath(top) == os.path.normpath(ana_kok):
        return True, None                        # ana checkout, worktree degil

    deger, kaynak = etkin_deger(top)
    kaynak_dosya = (kaynak or "").replace("file:", "")
    # Golge YALNIZ worktree'ye ozel katmandan gelir; paylasilan config'ten gelen
    # deger zaten ANA ile aynidir, golge degildir.
    if os.path.basename(kaynak_dosya) != "config.worktree":
        return True, None
    if deger is None:
        return True, None

    ham = deger.strip()
    cozulen = ham if os.path.isabs(ham) else os.path.normpath(os.path.join(top, ham))
    if os.path.normpath(cozulen) == os.path.normpath(kurulu):
        return True, None                        # worktree de dogru yeri gosteriyor

    if os.path.normpath(ham) == os.path.normpath("/dev/null"):
        return True, ("NOT: bu worktree config.worktree ile /dev/null'a baglanmis "
                      "(KASITLI izolasyon) -> ana deponun kancalari burada "
                      "KOSMAYACAK; mesru.")

    return False, ("bu LINKED WORKTREE'nin config.worktree'si core.hooksPath'i "
                   "%r'a baglamis -> kurulan %s'i GOLGELIYOR ve ESKI kancalar "
                   "kosmaya DEVAM EDER. Care: git -C %s config --worktree --unset "
                   "core.hooksPath   (ya da bu worktree'yi de kurulan dizine "
                   "bagla: git -C %s config --worktree core.hooksPath %s)"
                   % (ham, kurulu, top, top, kurulu))


def _ser(kaynak_dizin, kurulu, kuru):
    """Kaynagi kurulu dizine ser (idempotent). Serilen kanca adlarini doner."""
    islemler = []
    if not kuru:
        try:
            os.makedirs(kurulu, exist_ok=True)
        except OSError as e:
            raise Hata("kurulu kanca dizini olusturulamadi (%s): %s" % (kurulu, e))
    for ad in BEKLENEN_KANCALAR:
        k = os.path.join(kaynak_dizin, ad)
        h = os.path.join(kurulu, ad)
        try:
            ayni = (os.path.isfile(h) and open(k, "rb").read() == open(h, "rb").read()
                    and (os.stat(h).st_mode & stat.S_IXUSR))
        except OSError:
            ayni = False
        if ayni:
            continue
        islemler.append(ad)
        if kuru:
            continue
        # 🔴 ATOMIK RENAME, in-place copyfile DEGIL (olculdu): `--tazele` bir
        # KANCA GOVDESINDEN cagrilir ve kancanin KENDI dosyasini yeniden serer.
        # `copyfile` AYNI inode'u truncate edip yeniden yazar; git'in o an KOSAN
        # kanca icin acik tuttugu FD bozulur (shell scripti byte-offset'ten okur,
        # icerik kayinca GERISINI COP OKUR). Gecici dosyaya yazip `os.replace` ile
        # atomik degistirince YENI bir inode olusur; kosan process ESKI inode'unu
        # (acik FD'siyle) SAGLAM okumaya devam eder, sonraki cagri yeniyi alir.
        gecici = h + ".pruvo-tmp"
        try:
            shutil.copyfile(k, gecici)
            os.chmod(gecici, 0o755)
            os.replace(gecici, h)
        except OSError as e:
            try:
                os.remove(gecici)
            except OSError:
                pass
            raise Hata("%s kurulu dizine serilemedi (%s): %s -> kablolama YARIM "
                       "kalirdi" % (ad, h, e))
    return islemler


def _eski_kancalari_yedekle(kok, kaynak_dizin, kuru):
    """`.git/hooks` altindaki ornek-olmayan kancalari yedekle (gerekiyorsa).

    Kablolamadan sonra bu dosyalar ARTIK KOSMAZ. Izlenen esine BIREBIR esit
    olanlar zaten ayni koddur -> yedeklenmez. Farkli/fazla olan her dosya
    yedeklenir ve UYARI basilir: yerel bir ozellestirme sessizce kaybolmasin."""
    hooks = os.path.join(kok, ".git", "hooks")
    if not os.path.isdir(hooks):
        return None, []
    adaylar = []
    for ad in sorted(os.listdir(hooks)):
        if ad.endswith(".sample"):
            continue
        yol = os.path.join(hooks, ad)
        if not os.path.isfile(yol):
            continue
        esi = os.path.join(kaynak_dizin, ad)
        if os.path.isfile(esi):
            try:
                if open(yol, "rb").read() == open(esi, "rb").read():
                    continue
            except OSError:
                pass
        adaylar.append(ad)
    if not adaylar:
        return None, []
    yedek = os.path.join(kok, ".git", "hooks-yedek-%s" % time.strftime("%Y%m%d-%H%M%S"))
    if not kuru:
        try:
            os.makedirs(yedek, exist_ok=True)
            for ad in adaylar:
                shutil.copy2(os.path.join(hooks, ad), os.path.join(yedek, ad))
        except OSError as e:
            raise Hata("eski kancalar yedeklenemedi (%s): %s -> kablolama YAPILMADI "
                       "(yedeklenmemis ozellestirme sessizce olu kalirdi)" % (yedek, e))
    return yedek, adaylar


def etkin_deger(kok):
    """(deger, kaynak_dosya) — <kok> icin ETKIN core.hooksPath.

    `.git/config` GREP'LENMEZ: `--worktree` ile yazilmis bir deger orada HIC
    gorunmez ama yine de ETKINDIR ([[kanca-sessiz-devre-disi]] DENEY 4)."""
    rc, cikti, hata = _git(kok, "config", "--show-origin", "--get", AYAR)
    if rc == 1 and not cikti:
        return None, None
    if rc != 0:
        raise Hata("%s okunamadi (rc=%d): %s" % (AYAR, rc, hata or "?"))
    if "\t" in cikti:
        kaynak, _s, deger = cikti.partition("\t")
        return deger, kaynak
    return cikti, "?"


def dogrula(kok):
    """[(eksen, tamam_mi, mesaj)] — kablolama FIILEN gecerli mi?

    🔴 "Kurdum" BEYAN, "olctum" KANIT: yazma isleminden SONRA kosar ve etkin
    degeri git'ten YENIDEN okur."""
    bulgular = []
    deger, kaynak = etkin_deger(kok)
    beklenen = kurulu_dizin(kok)

    if deger is None:
        bulgular.append(("kablolama", False,
                         "%s AYARLI DEGIL -> git hala .git/hooks'u kosar; izlenen "
                         "kaynaktan kurulan kancalar DEVREDE DEGIL" % AYAR))
        return bulgular

    ham = deger.strip()
    cozulen = ham if os.path.isabs(ham) else os.path.normpath(os.path.join(kok, ham))
    if os.path.normpath(cozulen) != os.path.normpath(beklenen):
        bulgular.append(("kablolama", False,
                         "%s beklenen dizini GOSTERMIYOR: %r -> %s (beklenen %s)"
                         "   [kaynak: %s]"
                         % (AYAR, ham, cozulen, beklenen, kaynak or "?")))
        return bulgular
    bulgular.append(("kablolama", True,
                     "%s = %s   [kaynak: %s]" % (AYAR, cozulen, kaynak or "?")))

    if not os.path.isdir(cozulen):
        bulgular.append(("dizin", False, "cozulen yol bir DIZIN degil: %s" % cozulen))
        return bulgular
    for ad in BEKLENEN_KANCALAR:
        yol = os.path.join(cozulen, ad)
        if not os.path.isfile(yol):
            bulgular.append(("kanca %s" % ad, False, "YOK: %s -> hic kosmaz" % yol))
            continue
        st = os.stat(yol)
        if not (st.st_mode & stat.S_IXUSR):
            bulgular.append(("kanca %s" % ad, False,
                             "calistirilabilir DEGIL (x-biti yok) -> git SESSIZCE atlar"))
            continue
        if not open(yol, encoding="utf-8", errors="replace").read().strip():
            bulgular.append(("kanca %s" % ad, False, "BOS -> hicbir kapi kosmaz"))
            continue
        bulgular.append(("kanca %s" % ad, True, "mevcut + calistirilabilir (%d bayt)"
                         % st.st_size))

    try:
        kaynak_dizin = kanca_kaynagi(kok)
    except Hata as e:
        bulgular.append(("sapma", False, "kaynakla karsilastirilamadi: %s" % e))
        return bulgular
    sapanlar = sapma(kaynak_dizin, cozulen)
    if sapanlar:
        bulgular.append(("sapma", False,
                         "kurulu kopya IZLENEN kaynaktan SAPMIS: %s -> tazelemek "
                         "icin: python3 tools/kanca-kur.py" % ", ".join(sapanlar)))
    else:
        bulgular.append(("sapma", True, "kurulu kopya izlenen kaynakla BAYT-ESIT"))
    return bulgular


def kur(kok, kuru=False):
    """Kopyayi ser + kablolamayi yaz (idempotent). Yazilan komut BASILIR."""
    kaynak_dizin = kanca_kaynagi(kok)
    kurulu = kurulu_dizin(kok)

    serilen = _ser(kaynak_dizin, kurulu, kuru)
    if serilen:
        print("  %d kanca %s: %s"
              % (len(serilen), "SERILECEK" if kuru else "SERILDI", ", ".join(serilen)))
    else:
        print("  kurulu kopya zaten GUNCEL (%s)" % kurulu)

    mevcut, kaynak = etkin_deger(kok)
    if mevcut is not None:
        ham = mevcut.strip()
        cozulen = ham if os.path.isabs(ham) else os.path.normpath(os.path.join(kok, ham))
        if os.path.normpath(cozulen) == os.path.normpath(kurulu):
            print("  DEGISIKLIK YOK — %s zaten %s (kaynak: %s)" % (AYAR, cozulen, kaynak))
            return
        print("  UYARI: mevcut %s = %r (kaynak: %s) UZERINE yazilacak"
              % (AYAR, ham, kaynak))

    yedek, adaylar = _eski_kancalari_yedekle(kok, kaynak_dizin, kuru)
    if adaylar:
        print("  UYARI: .git/hooks altindaki su kancalar kablolamadan sonra ARTIK "
              "KOSMAYACAK: %s" % ", ".join(adaylar))
        print("  Yedek: %s   (yerel ozellestirme varsa %s altina tasi)"
              % (yedek, KANCA_DIZINI))

    # 🔴 KAPSAM: ACIK bayrak (KAPSAM) + ACIK hedef (-C kok). Cari dizine
    # BIRAKILMAZ; bayraksiz yazim bir worktree'den kosuldugunda PAYLASILAN
    # config'e sizardi ve bu tam da onlenmek istenen olaydir.
    if kuru:
        print("  [KURU] yazilacakti: git -C %s config %s %s %s"
              % (kok, KAPSAM, AYAR, kurulu))
        return
    rc, _o, hata = _git(kok, "config", KAPSAM, AYAR, kurulu)
    if rc != 0:
        raise Hata("git config %s %s basarisiz (rc=%d): %s -> kablolama KURULMADI"
                   % (KAPSAM, AYAR, rc, hata or "?"))
    print("  YAZILDI: git -C %s config %s %s %s" % (kok, KAPSAM, AYAR, kurulu))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    kok_arg = None
    if "--depo" in argv:
        i = argv.index("--depo")
        if i + 1 >= len(argv):
            print("HATA: --depo bir yol bekler", file=sys.stderr)
            return 2
        kok_arg = argv[i + 1]
        del argv[i:i + 2]
    kuru = "--kuru" in argv
    yalniz_dogrula = "--dogrula" in argv
    yalniz_tazele = "--tazele" in argv
    bilinmeyen = [a for a in argv if a not in ("--kuru", "--dogrula", "--tazele")]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2

    baslangic = kok_arg or os.path.dirname(TOOLS)

    # --tazele: kanca govdesinden cagrilan HAFIF yol (DELIK 1). Kablolamaya
    # DOKUNMAZ, config YAZMAZ; yalniz kopya bayatsa yeniden serer ve durumu
    # cikis koduyla bildirir.
    if yalniz_tazele:
        rc, mesaj = tazele(baslangic)
        if rc != 0:
            print("kanca-kur --tazele: %s" % mesaj, file=sys.stderr)
        return rc

    try:
        kok = ana_checkout(baslangic)
    except Hata as e:
        print("🔴 KURULAMADI: %s" % e, file=sys.stderr)
        return 1
    print("KANCA KABLOLAMA KURULUMU — ANA checkout: %s" % kok)

    if not yalniz_dogrula:
        try:
            kur(kok, kuru=kuru)
        except Hata as e:
            print("🔴 KURULAMADI: %s" % e, file=sys.stderr)
            return 1
        except OSError as e:
            print("🔴 KURULAMADI: dosya sistemi hatasi: %s" % e, file=sys.stderr)
            return 1
        if kuru:
            print("KURU KOSUM — hicbir sey yazilmadi, dogrulama ATLANDI.")
            return 0

    # kur -> DOGRULA halkasi: "kuruldu" VARSAYILMAZ, OLCULUR.
    try:
        bulgular = dogrula(kok)
    except Hata as e:
        print("🔴 DOGRULANAMADI: %s" % e, file=sys.stderr)
        return 1
    for eksen, tamam, mesaj in bulgular:
        print("  %s %-16s %s" % ("✅" if tamam else "🔴", eksen, mesaj))
    kirmizi = [b for b in bulgular if not b[1]]

    # 🔴 DELIK 2: bulundugumuz worktree kurulan degeri GOLGELIYOR mu? dogrula()
    # ANA checkout'u yargilar; bir linked worktree'nin config.worktree'si baska
    # yere baglanmissa o worktree ESKI kancalari kosturur ve "ETKIN ✅" YALAN
    # olurdu. Bu kontrol o worktree'nin FIILEN halini olcer.
    try:
        kurulu = kurulu_dizin(baslangic)
        golge_ok, golge_mesaj = golge_worktree_kontrol(baslangic, kurulu)
    except Hata as e:
        golge_ok, golge_mesaj = True, None
        print("  ⚪ golge kontrolu OLCULEMEDI: %s" % e)
    if golge_mesaj and golge_ok:
        print("  ℹ️  %s" % golge_mesaj)
    elif not golge_ok:
        print("  🔴 golge worktree   %s" % golge_mesaj)

    if kirmizi or not golge_ok:
        n = len(kirmizi) + (0 if golge_ok else 1)
        print("SONUC: KURULU DEGIL (%d eksen kirmizi) — fail-closed -> cikis 1"
              % n, file=sys.stderr)
        return 1
    print("SONUC: KABLOLAMA ETKIN ✅ (%d eksen)" % len(bulgular))
    return 0


if __name__ == "__main__":
    sys.exit(main())
