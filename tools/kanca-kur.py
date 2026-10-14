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

🔴 INDIRME KAPISI (14 Eki 2026, olculdu): `--tazele` kaynagi BULUNDUGU agactan
alir. ESKI tabanli bir agacin commit'i, baska bir dalin serdigi YENI kopyayi
eski kaynakla EZIYORDU ("BAYATTI -> yeniden serildi"): yeni eklenen kanca
bloklari TUM evler icin sessizce siliniyordu
([[bayat-agactan-commit-paylasilan-kancayi-eskiye-sarar]]). Onarim iki halkadir:
  (1) Her serimde kopyanin yanina KAYNAK DAMGASI yazilir (kaynak agacin HEAD
      commit'i + serilen her dosyanin sha256'si). `--tazele` aday kaynak,
      damgadaki commit'ten ESKIYSE (ata; ya da ayrisik ve kanca kaynagini
      degistiren yalniz damga tarafi) USTUNE YAZMAZ: rc 0 + gorunur UYARI.
      Aday YENIYSE, damga yoksa/okunamiyorsa ya da kopya ELLE DUZENLENMISSE
      (damgadaki sha256'dan sapmis) eskisi gibi yeniden serer (fail-closed).
  (2) `kanca-kur.py` + `git_ortami.py` de kopyanin yanina serilir ve kancalar
      ONCE o kurulu araci cagirir: eski agacin ESKI (kapisiz) kanca-kur.py'si
      paylasilan kopyaya hic dokunamaz.

Kullanim:
    python3 tools/kanca-kur.py            # kur/tazele + DOGRULA (rc 0/1)
    python3 tools/kanca-kur.py --kuru     # hicbir sey yazma, ne yapacagini yaz
    python3 tools/kanca-kur.py --dogrula  # yalniz dogrula (kurma)
    python3 tools/kanca-kur.py --tazele   # kopya bayatsa yeniden ser (kanca ici;
                                          # rc 3 = bayatti+tazelendi, 0 = guncel
                                          # ya da eski agac -> kopya korundu+UYARI)
    python3 tools/kanca-kur.py --depo X   # baska bir checkout'u hedefle (test/tani)
"""
import os
import shutil
import stat
import subprocess
import sys
import hashlib
import json
import time

# Kurulu kopya ortak `.git/pruvo-kancalar/`tan kosar: oraya __pycache__ yazma.
sys.dont_write_bytecode = True
from git_ortami import git_ortami  # noqa: E402

TOOLS = os.path.dirname(os.path.abspath(__file__))

# IZLENEN kaynak dizinin repo-goreli adi. TEK KAYNAK: nobetci ve kabul testi
# bu sabitleri IMPORT eder, KOPYALAMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
KANCA_DIZINI = "tools/kancalar"

# KURULAN kopyanin ORTAK `.git` dizini altindaki adi. `.git/hooks` DEGIL:
# oradaki (elle duzenlenmis, fail-open) kancalarin uzerine yazilmaz.
KURULU_DIZIN_ADI = "pruvo-kancalar"

# Kancalarin YANINA serilen araclar (kaynak: agacin `tools/` dizini). Kancalar
# `--tazele`yi ONCE bu kurulu kopyadan cagirir; eski agacin kapisiz kanca-kur'u
# paylasilan kopyayi geri saramaz. HEP-YA-HIC: biri eksikse hicbiri serilmez
# (git_ortami'siz kanca-kur import'ta coker).
KURULU_ARACLAR = ("kanca-kur.py", "git_ortami.py")

# Serilen kopyanin KAYNAK DAMGASI (kopya dizini icinde; git bu adi kanca sanmaz).
DAMGA_ADI = ".kaynak-damgasi.json"

# Surum karsilastirmasinda "kanca kaynagi degisti mi" sorusunun yollari = SERILEN
# KUMENIN TAMAMI. 🔴 (14 Eki curutme) `git_ortami.py` disarida birakilinca o
# dosyayi yalniz main'de degistiren bir commit, ayrisik dallarla main arasinda
# her commit'te rc 3 PING-PONG uretti (serilen ama surumde sayilmayan dosya).
SURUM_YOLLARI = (KANCA_DIZINI,) + tuple("tools/" + a for a in KURULU_ARACLAR)

# Ana hat dali: iki taraf da kanca kaynagini degistirmisse (gercek catisma)
# yalniz BU dala ait aday, bu dala ait OLMAYAN damgayi ezebilir.
ANA_DAL = "refs/heads/main"

# Indirme reddi mesajinin oneki: rc 0 olsa da main() bunu stderr'e BASAR.
UYARI_ONEKI = "UYARI:"

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
    # 🔴 Miras git baglami SILINIR: linked worktree kancasi GIT_DIR'i ihrac eder
    # ve ACIK `-C` hedefini ezer (or. ana checkout'un HEAD'i yerine worktree'nin
    # HEAD'i okunurdu). Tek tanim: git_ortami.
    try:
        p = subprocess.run(["git", "-C", cwd] + list(args),
                           capture_output=True, text=True, timeout=30,
                           env=git_ortami())
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


def dagitim(kaynak_dizin):
    """[(ad, kaynak_yolu), ...] — kurulu dizine serilecek dosyalar.

    Kancalar HER ZAMAN; KURULU_ARACLAR yalniz HEPSI agacin `tools/`unda varsa
    VE HEPSI DERLENIYORSA (hep-ya-hic).

    🔴 DERLEME SARTI (14 Eki curutme): kancalar ONCE kurulu araci cagirir. Bir
    agactaki yarim (sozdizimi bozuk) kanca-kur.py serilseydi TUM agaclarda
    commit/push `rc=1` ile durur, agac duzelse de kendiliginden onarilmazdi."""
    ciftler = [(ad, os.path.join(kaynak_dizin, ad)) for ad in BEKLENEN_KANCALAR]
    araclar = [(ad, os.path.join(os.path.dirname(kaynak_dizin), ad))
               for ad in KURULU_ARACLAR]
    if all(os.path.isfile(y) and _derlenir_mi(y) for _a, y in araclar):
        ciftler.extend(araclar)
    return ciftler


def _derlenir_mi(yol):
    """Python kaynagi sozdizimi olarak derleniyor mu? (yazmaz, calistirmaz)"""
    try:
        with open(yol, "rb") as f:
            compile(f.read(), yol, "exec", dont_inherit=True)
        return True
    except (OSError, SyntaxError, ValueError):
        return False


def sapma(kaynak_dizin, kurulu):
    """[ad, ...] — kurulan kopyanin kaynaktan BAYT olarak saptigi dosyalar.

    🔴 SECILEN TASARIMIN BEDELI: kopya, izlenen kaynagin bir SURETIDIR ve elle
    duzenlenebilir. Sapma sessiz kalirsa "depoda fail-closed, makinede
    fail-open" hali geri doner — o yuzden sapma bir KAPI eksenidir."""
    sapanlar = []
    for ad, k in dagitim(kaynak_dizin):
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


def _sha(yol):
    """sha256 hex ya da None (dosya yok/okunamiyor)."""
    try:
        with open(yol, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _kaynak_agaci(kaynak_dizin):
    """`<agac>/tools/kancalar` -> `<agac>`."""
    return os.path.dirname(os.path.dirname(os.path.normpath(kaynak_dizin)))


def _agac_commit(agac):
    """(sha|None) — agacin HEAD commit'i."""
    rc, cikti, _h = _git(agac, "rev-parse", "--verify", "-q", "HEAD^{commit}")
    return cikti if rc == 0 and cikti else None


def _kirli_mi(kaynak_dizin):
    """Agacin SURUM dosyalari HEAD'den farkli mi (stage'li/islenmemis)? None=olculemedi.

    🔴 NEDEN: `--tazele` pre-commit'ten kosar -> serilen icerik cogu zaman HENUZ
    COMMIT'LENMEMIS degisikliktir ve HEAD yalniz TABANIDIR. Damga yalniz commit'i
    kaydederse ayni tabandaki (ya da tabandan ilgisiz commit'lerle ilerlemis)
    her agac kendini 'esit/yeni' sanip yeni bloklari EZER."""
    yollar = ["%s/%s" % (KANCA_DIZINI, ad) for ad in BEKLENEN_KANCALAR]
    yollar.extend("tools/" + a for a in KURULU_ARACLAR)
    rc, cikti, _h = _git(_kaynak_agaci(kaynak_dizin), "--no-optional-locks", "status",
                         "--porcelain", "--untracked-files=all", "--", *yollar)
    return bool(cikti) if rc == 0 else None


def damga_oku(kurulu):
    """(dict|None) — kaynak damgasi; yoksa/bozuksa None."""
    try:
        with open(os.path.join(kurulu, DAMGA_ADI), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get("ozet"), dict):
        return None
    return d


def damga_yaz(kaynak_dizin, kurulu):
    """Kurulu kopyanin KAYNAK DAMGASINI yaz (atomik). Hata -> Hata."""
    ozet = {}
    for ad, _k in dagitim(kaynak_dizin):
        h = _sha(os.path.join(kurulu, ad))
        if h is not None:
            ozet[ad] = h
    d = {"commit": _agac_commit(_kaynak_agaci(kaynak_dizin)),
         "kirli": _kirli_mi(kaynak_dizin),
         "kaynak": os.path.normpath(kaynak_dizin),
         "zaman": time.strftime("%Y-%m-%dT%H:%M:%S"), "ozet": ozet}
    yol = os.path.join(kurulu, DAMGA_ADI)
    gecici = yol + ".pruvo-tmp"
    try:
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        os.replace(gecici, yol)
    except OSError as e:
        raise Hata("kaynak damgasi yazilamadi (%s): %s" % (yol, e))


def elle_duzenlenmis(damga, kurulu):
    """[ad, ...] — kurulu kopyada damgadaki sha256'dan sapan dosyalar."""
    return sorted(ad for ad, h in damga["ozet"].items()
                  if _sha(os.path.join(kurulu, ad)) != h)


def _ata_mi(agac, ata, torun):
    """True/False; git olcemezse None."""
    rc, _o, _h = _git(agac, "merge-base", "--is-ancestor", ata, torun)
    return {0: True, 1: False}.get(rc)


def _degisti_mi(agac, taban, uc):
    """SURUM_YOLLARI taban..uc arasinda degisti mi? True/False/None."""
    rc, _o, _h = _git(agac, "diff", "--quiet", taban, uc, "--", *SURUM_YOLLARI)
    return {0: False, 1: True}.get(rc)


def surum_karari(kaynak_dizin, kurulu):
    """(ser_mi, neden) — kopya SAPMISKEN aday kaynak USTUNE serilebilir mi?

    🔴 INDIRME KAPISI: aday, damgadaki kaynaktan ESKIYSE serilmez. Karar
    olculemiyorsa (damga yok/bozuk, commit cozulmuyor, git hatasi) eski davranis
    korunur: SERILIR (fail-closed — bayat mantik sessizce kosmaz)."""
    damga = damga_oku(kurulu)
    if damga is None:
        return True, "kaynak damgasi yok/okunamadi"
    elle = elle_duzenlenmis(damga, kurulu)
    if elle:
        return True, "kurulu kopya ELLE DUZENLENMIS (%s)" % ", ".join(elle)
    agac = _kaynak_agaci(kaynak_dizin)
    aday = _agac_commit(agac)
    kurulu_c = damga.get("commit")
    if not aday or not kurulu_c:
        return True, "commit cozulemedi (aday=%s, damga=%s)" % (aday, kurulu_c)
    rc, _o, _h = _git(agac, "cat-file", "-e", "%s^{commit}" % kurulu_c)
    if rc != 0:
        return True, "damga commit'i depoda yok (%s)" % kurulu_c[:12]
    # 🔴 KIRLI DAMGA: kopya `kurulu_c` + ISLENMEMIS degisiklikten serildi. Bu
    # icerik hicbir commit'te yok -> SANAL bir "kurulu_c'nin ana hatta olmayan
    # cocugu" gibi yargilanir. Olculemeyen (None) kirlilik de kirli sayilir.
    kirli = damga.get("kirli") is not False
    damga_kaynak = damga.get("kaynak") or ""
    if kirli:
        if (os.path.normpath(damga_kaynak) == os.path.normpath(kaynak_dizin)
                and (aday == kurulu_c or _ata_mi(agac, kurulu_c, aday))):
            return True, "ayni agac kendi kanca degisikligini yeniden seriyor"
    else:
        if aday == kurulu_c:
            return True, "ayni commit, agacta islenmemis kanca degisikligi"
        yeni = _ata_mi(agac, kurulu_c, aday)
        if yeni is None:
            return True, "ata iliskisi olculemedi"
        if yeni:
            return True, "aday kaynak damgadan YENI"
    neden_eski = ("bu agacin HEAD'i (%s) kurulu kopyanin kaynagindan (%s%s) ESKI"
                  % (aday[:12], kurulu_c[:12],
                     " + islenmemis degisiklik" if kirli else ""))
    # 🔴 "SAHIPSIZ DAMGA" KACISI YOK (14 Eki curutme, olculdu): "damga commit'i
    # hicbir dalda yok" ve "kirli damganin agaci silinmis" kacislari ESKI agaca
    # kapi aciyordu — amend, detached worktree commit'i ya da kapanan worktree
    # damgayi sahipsiz birakinca eski agac yeni kopyayi ezdi. Terk edilmis dal
    # kopyasindan cikis: ana hat kanca kaynagini degistirince ana hat kazanir
    # (asagidaki catisma kolu) ya da operator ana checkout'tan ACIKCA serer.
    if aday == kurulu_c or _ata_mi(agac, aday, kurulu_c):
        return False, neden_eski
    rc, taban, _h = _git(agac, "merge-base", aday, kurulu_c)
    if rc != 0 or not taban:
        return True, "ortak ata yok"
    aday_degisti = _degisti_mi(agac, taban, aday)
    kurulu_degisti = True if kirli else _degisti_mi(agac, taban, kurulu_c)
    if aday_degisti is None or kurulu_degisti is None:
        return True, "kanca kaynagi farki olculemedi"
    if kurulu_degisti and not aday_degisti:
        return False, ("%s (kanca kaynagini yalniz kurulu taraf degistirmis)"
                       % neden_eski.replace(" ESKI", " geride"))
    if aday_degisti and kurulu_degisti:
        aday_ana = _ata_mi(agac, aday, ANA_DAL)
        kurulu_ana = False if kirli else _ata_mi(agac, kurulu_c, ANA_DAL)
        if aday_ana and not kurulu_ana:
            return True, "catisma: aday ana hatta, kurulu kaynak degil"
        return False, ("catisma: iki ayrisik dal da kanca kaynagini degistirmis "
                       "(aday %s, kurulu %s)" % (aday[:12], kurulu_c[:12]))
    return True, "ayrisik dal, kanca kaynagini aday taraf degistirmis"


def _damga_ilerlet(kaynak_dizin, kurulu):
    """Kopya kaynakla ESITKEN damgayi tazele (yoksa / ozet bayatsa / aday
    yeniyse). Sessiz en-iyi-caba: bu yolda karar yoktur, yalniz kayit."""
    damga = damga_oku(kurulu)
    try:
        if damga is None or elle_duzenlenmis(damga, kurulu):
            damga_yaz(kaynak_dizin, kurulu)
            return
        # kirli damga + BAYT-ESIT temiz aday: icerik artik bir commit'te -> kesinles
        if damga.get("kirli") is not False and _kirli_mi(kaynak_dizin) is False:
            damga_yaz(kaynak_dizin, kurulu)
            return
        aday = _agac_commit(_kaynak_agaci(kaynak_dizin))
        kurulu_c = damga.get("commit")
        if aday and aday != kurulu_c and (
                not kurulu_c or _ata_mi(_kaynak_agaci(kaynak_dizin), kurulu_c, aday)):
            damga_yaz(kaynak_dizin, kurulu)
    except Hata:
        pass


def tazele(baslangic):
    """(rc, mesaj) — kurulu kopya izlenen kaynaktan BAYATSA yeniden ser.

    🔴 DELIK 1 ONARIMI: `git pull` izlenen kaynagi guncelleyince kopya BAYAT
    kalir ve commit aninda SESSIZCE eski mantigi kosturur. Bu fonksiyon kanca
    govdesinden (pre-commit/pre-push basi) ve post-merge/post-checkout'tan
    cagrilir.

    Cikis:
      0             -> kopya zaten GUNCEL, ya da karsilastirilacak kaynak YOK
                       (agac eski commit'te) -> yapacak sey yok, commit devam.
                       Ya da aday kaynak kurulu kopyadan ESKI -> kopya KORUNUR,
                       mesaj UYARI_ONEKI ile baslar ve stderr'e basilir.
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
        _damga_ilerlet(kaynak_dizin, kurulu)
        return 0, "kurulu kopya guncel"
    # 🔴 INDIRME KAPISI: ESKI agac YENI kopyayi EZMEZ (rc 0 + gorunur UYARI).
    ser_mi, neden = surum_karari(kaynak_dizin, kurulu)
    if not ser_mi:
        return 0, ("%s kurulu kanca kopyasi KORUNDU, eskiye SARILMADI — %s. "
                   "Agacini guncelle (git merge main) ki kendi kanca degisikligin "
                   "de serilebilsin. Kurulu kopya terk edilmis bir daldansa ana "
                   "checkout'tan ACIKCA ser: python3 tools/kanca-kur.py"
                   % (UYARI_ONEKI, neden))
    try:
        _ser(kaynak_dizin, kurulu, kuru=False)
    except Hata as e:
        return 1, "kopya bayatti ama YENIDEN SERILEMEDI: %s" % e
    try:
        damga_yaz(kaynak_dizin, kurulu)
    except Hata as e:
        return 1, "kopya yeniden serildi ama DAMGALANAMADI: %s" % e
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
    for ad, k in dagitim(kaynak_dizin):
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
    # Acik kurulum OPERATOR KARARIDIR (indirme kapisi yok): ana checkout'u
    # OTORITE yapar ve damgayi HER KOSUMDA ona yazar — icerik zaten esit olsa
    # bile (terk edilmis dal/sahipsiz damgadan cikis yolu budur; UYARI bunu soyler).
    if not kuru:
        damga_yaz(kaynak_dizin, kurulu)

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
        if rc != 0 or mesaj.startswith(UYARI_ONEKI):
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
