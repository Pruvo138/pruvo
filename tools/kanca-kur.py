#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kanca-kur.py — git kanca KABLOLAMASINI IZLENEN kaynaga bagla (FAIL-CLOSED).

NE YAPAR: ANA checkout'un `core.hooksPath` ayarini izlenen `tools/kancalar`
dizinine baglar. Boylece kancalar `.git/hooks` altinda (commit EDILMEYEN, tek
makinede yasayan) kopyalar olmaktan cikar; DEPODA yasar, gozden gecirilir,
mutasyona ugratilir ve her klonda AYNI olur.

🔴 NEDEN GEREKTI (4 Agu 2026, olculdu): `tools/urunler-guard.py` katalog verisini
koruyan FAIL-LOUD bir nobetciye cevrildi, ama `.git/hooks/pre-commit` icinde
    python3 "$guard" --tetik commit >/dev/null 2>&1 || true
duruyordu — git-native yol FAIL-OPEN'di: cikis kodu da gerekce de yutuluyordu.
Koruma yalniz bu makinenin oturum kablosuyla (PreToolUse) blokluyordu; DUZ
TERMINALDE, CODEX'TE ve BASKA BIR MAKINEDE hic bloklamiyordu. Kancayi depoya
tasimadan bu delik her makinede yeniden aciliyordu.

═══════════════════════════════════════════════════════════════════════════════
🔴 KAPSAM BAYRAGI — BU DOSYANIN EN TEHLIKELI SATIRI
═══════════════════════════════════════════════════════════════════════════════
Bu depoda OLCULMUS tuzak vardir ([[kanca-sessiz-devre-disi]]): bir LINKED
WORKTREE icinde BAYRAKSIZ `git config core.hooksPath ...` yazmak degeri
PAYLASILAN `.git/config`'e yazar (rc=0, UYARI YOK) ve ANA CHECKOUT ile TUM
worktree'lerin kancalarini ayni anda oldurur — D1 senkronu dahil. Yani "kancalari
depoya bagla" adimi, yanlis yapilirsa tam da onlemeye calistigi sessizligi URETIR.

BU MAKINEDE OLCULDU (git 2.50.1, sentetik depolarla; tools/kanca-kablolama-test.py
VAKA 3 bunu KOSARAK yeniden uretir):
  * worktree'den BAYRAKSIZ `git config core.hooksPath X`  -> PAYLASILAN .git/config
  * worktree'den `git config --local core.hooksPath X`    -> PAYLASILAN .git/config
  * worktree'den `git config --worktree core.hooksPath X` -> .git/worktrees/<w>/config.worktree
  * `--worktree` deger `--local` degerini EZER (izole worktree override'i korunur)

SECIM: `--local` + ACIKCA `git -C <ANA CHECKOUT>`.
  * Kapsam ASLA cari dizine BIRAKILMAZ: hedef once `--git-common-dir`den
    turetilir, komut `-C <ana checkout>` ile kosar. Boylece betik bir
    worktree'den kosturulsa bile YAZILAN DOSYA onceden BILINIR ve BASILIR.
  * `--global` / `--system` KULLANILMAZ: makinedeki BASKA depolari kirletirdi.
  * `--worktree` KULLANILMAZ: kablolama tek bir worktree'de kalir, ana checkout
    korumasiz kalirdi (tam da onarilmak istenen hal).

DEGER: GORELI `tools/kancalar` (mutlak yol DEGIL). Olculdu ki git goreli
core.hooksPath'i CARI DIZINE gore degil ILGILI AGACIN TEPESINE gore cozer (alt
dizinden commit'te de dogru cozuldu). Sonucu:
  * her worktree KENDI agacindaki kancalari kosar -> bir kancayi degistiren dal
    o kancayi FIILEN test eder;
  * deger makineye ozel degildir, baska bir klonda da anlamlidir.
Bir worktree'nin `config.worktree`'sindeki `/dev/null` override'i (Claude Code
izolasyonu) bunu EZMEYE devam eder — mesrudur, DOKUNULMAZ.

═══════════════════════════════════════════════════════════════════════════════
FAIL-CLOSED SOZU: kuramadigi HER halde sifir-disi cikar ve NEDENINI basar.
"Kuruldu" ASLA VARSAYILMAZ — yazimdan SONRA etkin deger yeniden okunur, dizine
cozulur ve beklenen kancalar orada + calistirilabilir mi diye BAKILIR (kur ->
DOGRULA halkasi kapanir). Dogrulama gecmezse cikis 1'dir.

IDEMPOTENT: zaten dogru kabloluysa hicbir sey yazmaz, "DEGISIKLIK YOK" der (0).

YEDEK: `.git/hooks` altindaki (ornek olmayan) kancalar kablolama sonrasi ARTIK
KOSMAZ. Sessizce olu birakilmazlar: iceriklerinin izlenen esine BIREBIR esit
olmadigi her halde `.git/hooks-yedek-<zaman>/` altina kopyalanir ve UYARI basilir
(yerel bir ozellestirme varsa mimar onu gorup izlenen kaynaga tasisin).

Kullanim:
    python3 tools/kanca-kur.py            # kur + DOGRULA (rc 0/1)
    python3 tools/kanca-kur.py --kuru     # hicbir sey yazma, ne yapacagini yaz
    python3 tools/kanca-kur.py --dogrula  # yalniz dogrula (kurma)
    python3 tools/kanca-kur.py --depo X   # baska bir checkout'u hedefle (test/tani)
"""
import os
import shutil
import stat
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))

# IZLENEN kanca dizininin repo-goreli adi. TEK KAYNAK: nobetci ve kabul testi
# bu sabiti IMPORT eder, KOPYALAMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
KANCA_DIZINI = "tools/kancalar"

# Kurulumun kurdugu ayar. Kapsam bayragi burada, TEK YERDE.
AYAR = "core.hooksPath"
KAPSAM = "--local"

# Kablolamadan sonra ORADA + CALISTIRILABILIR olmasi beklenen kancalar.
BEKLENEN_KANCALAR = ("pre-commit", "commit-msg", "pre-push", "post-commit", "post-checkout")


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


def ana_checkout(baslangic):
    """ANA checkout'un koku. Linked worktree'den kosulsa da ANA'yi bulur.

    🔴 KAPSAM GUVENLIGININ ILK HALKASI: yazma komutu bu yola `-C` ile
    baglanir, cari dizine ASLA birakilmaz."""
    rc, cikti, hata = _git(baslangic, "rev-parse", "--path-format=absolute",
                           "--git-common-dir")
    if rc != 0 or not cikti:
        raise Hata("ANA checkout bulunamadi (git rev-parse rc=%d): %s"
                   % (rc, hata or "?"))
    if os.path.basename(cikti) != ".git":
        raise Hata("ortak git dizini '.git' ile bitmiyor (bare depo?): %s" % cikti)
    return os.path.dirname(cikti)


def kanca_kaynagi(kok):
    """(mutlak yol) — izlenen kanca dizini; yoksa/eksikse FAIL-CLOSED."""
    yol = os.path.join(kok, KANCA_DIZINI)
    if not os.path.exists(yol):
        raise Hata("izlenen kanca dizini YOK: %s -> kurulacak bir sey yok "
                   "(yanlis depo mu?)" % yol)
    if not os.path.isdir(yol):
        raise Hata("%s bir DIZIN degil -> core.hooksPath'e baglanamaz" % yol)
    eksik = [a for a in BEKLENEN_KANCALAR
             if not os.path.isfile(os.path.join(yol, a))]
    if eksik:
        raise Hata("izlenen kanca dizininde EKSIK kanca(lar): %s -> kablolama "
                   "yarim koruma olurdu" % ", ".join(eksik))
    return yol


def _calistirilabilir_yap(dizin, kuru):
    """x-biti olmayan kancalari calistirilabilir yap (git x-bitsiz kancayi
    SESSIZCE atlar -> 'dosya duruyor' yetmez). Yazilamiyorsa FAIL-CLOSED."""
    duzeltilen = []
    for ad in BEKLENEN_KANCALAR:
        yol = os.path.join(dizin, ad)
        st = os.stat(yol)
        if st.st_mode & stat.S_IXUSR:
            continue
        duzeltilen.append(ad)
        if kuru:
            continue
        try:
            os.chmod(yol, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError as e:
            raise Hata("%s calistirilabilir yapilamadi (%s) -> git onu sessizce "
                       "atlardi" % (yol, e))
    return duzeltilen


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
                    continue          # ayni kod -> yedeklenecek bir sey yok
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
    """(deger, kaynak_dosya) — ANA checkout icin ETKIN core.hooksPath.

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

    🔴 "Kurdum" BEYAN, "olctum" KANIT: bu fonksiyon yazma isleminden SONRA
    kosar ve etkin degeri git'ten YENIDEN okur."""
    bulgular = []
    deger, kaynak = etkin_deger(kok)
    beklenen_dizin = os.path.join(kok, KANCA_DIZINI)

    if deger is None:
        bulgular.append(("kablolama", False,
                         "%s AYARLI DEGIL -> git hala .git/hooks'u kosar; izlenen "
                         "kancalar DEVREDE DEGIL" % AYAR))
        return bulgular

    ham = deger.strip()
    cozulen = ham if os.path.isabs(ham) else os.path.normpath(os.path.join(kok, ham))
    if os.path.normpath(cozulen) != os.path.normpath(beklenen_dizin):
        bulgular.append(("kablolama", False,
                         "%s beklenen dizini GOSTERMIYOR: %r -> %s (beklenen %s)"
                         "   [kaynak: %s]"
                         % (AYAR, ham, cozulen, beklenen_dizin, kaynak or "?")))
        return bulgular
    bulgular.append(("kablolama", True,
                     "%s = %r -> %s   [kaynak: %s]" % (AYAR, ham, cozulen, kaynak or "?")))

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
    return bulgular


def kur(kok, kuru=False):
    """Kablolamayi yaz (idempotent). Yazilan dosya BASILIR."""
    kaynak_dizin = kanca_kaynagi(kok)
    duzeltilen = _calistirilabilir_yap(kaynak_dizin, kuru)
    if duzeltilen:
        print("  x-biti verildi: %s" % ", ".join(duzeltilen))

    mevcut, kaynak = etkin_deger(kok)
    if mevcut is not None:
        ham = mevcut.strip()
        cozulen = ham if os.path.isabs(ham) else os.path.normpath(os.path.join(kok, ham))
        if os.path.normpath(cozulen) == os.path.normpath(kaynak_dizin):
            print("  DEGISIKLIK YOK — %s zaten %r (kaynak: %s)" % (AYAR, ham, kaynak))
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
              % (kok, KAPSAM, AYAR, KANCA_DIZINI))
        return
    rc, _o, hata = _git(kok, "config", KAPSAM, AYAR, KANCA_DIZINI)
    if rc != 0:
        raise Hata("git config %s %s basarisiz (rc=%d): %s -> kablolama KURULMADI"
                   % (KAPSAM, AYAR, rc, hata or "?"))
    print("  YAZILDI: git -C %s config %s %s %s" % (kok, KAPSAM, AYAR, KANCA_DIZINI))


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
    bilinmeyen = [a for a in argv if a not in ("--kuru", "--dogrula")]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2

    try:
        kok = ana_checkout(kok_arg or os.path.dirname(TOOLS))
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
    if kirmizi:
        print("SONUC: KURULU DEGIL (%d eksen kirmizi) — fail-closed -> cikis 1"
              % len(kirmizi), file=sys.stderr)
        return 1
    print("SONUC: KABLOLAMA ETKIN ✅ (%d eksen)" % len(bulgular))
    return 0


if __name__ == "__main__":
    sys.exit(main())
