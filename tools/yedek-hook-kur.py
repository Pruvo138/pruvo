#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre-push hook'una YEDEK BLOGUNU kurar (idempotent, tekrar-kosulabilir).

🖥️ YENI MAKINEDE / GOCTEN SONRA TEK YAPILACAK SEY:
        python3 tools/yedek-hook-kur.py
    Hook'lar `.git/hooks` altinda yasar ve GIT'E GIRMEZ -> her makinede yeniden kurulur.
    Elle hatirlanacak bir adim BIRAKILMASIN diye bu betik var; iki kez kosmak zararsiz.

NE YAPAR: `.git/hooks/pre-push` icine isaretli bir blok ekler. Blok her push'ta
`tools/yedekle.py --gerekliyse` cagirir (son damgadan beri degisiklik yoksa hicbir sey
kopyalanmaz -> push yavaslamaz).

NEDEN VAR (26 Tem olcumu): yedekle.py DOGRU calisiyordu ama ELLE cagriliyordu; 5 gun
kosulmadi ve mutasyon-kanitli skill dosyalari yedekte bayat kaldi. Otomasyon tek basina
yetmez (sessizce durabilir) -> gorunurluk `tools/durum.py` bolum 7'de, otomasyon burada.

🔴 FAIL-OPEN (pazarliksiz): yedek patlasa, Drive bagli olmasa, python3 bulunmasa bile
   PUSH DEVAM EDER. Blok icinde `exit` YOKTUR ve cagri `|| true` ile susturulur.
   Push'u durduran bir yedek kabul edilemez — D1 senkron blogunun emsali de budur.

GUVENLI KURULUM:
  * Mevcut pre-push (D1 senkronu) KORUNUR — blok isaretler arasina yazilir, dosyanin
    geri kalanina dokunulmaz. Ilk degisiklikte yanina `.pruvo-yedek-oncesi` kopyasi alinir.
  * Blok SEBEKE/D1 blogundan ONCE yerlestirilir: D1 blogu urunler.json degismediyse
    `exit 0` ile CIKIYOR -> sona eklenen bir blok cogu push'ta HIC CALISMAZDI.
  * Tekrar kosum blogu GUNCELLER, ikinci kopya YIGMAZ.

🔴 GERI YUKLEME (31 Tem 2026, hesap tasima denetimi) — NEDEN GENISLETILDI:
    Bu betik yalniz KENDI yedek blogunu kuruyordu. Oysa `.git/hooks` KLONLAMAYLA GELMEZ
    ve icinde yedek blogundan COK DAHA kritik iki kapi yasiyor:
      * pre-push D1 SENKRON BLOGU — kurulmazsa site yeni urunu gosterir, EGE GOREMEZ
        ve bu SESSIZDIR (bu sinifta 367 urunluk kayip zaten olculdu).
      * pre-commit GUARD/MUKERRER/MIMAR KAPISI — kurulmazsa urun verisi korumasiz kalir.
    Yeni hesapta bunlari "elle hatirlamak" = er ya da gec unutulur. `--geri-yukle`
    BES EVIN hook'larini Drive yedeginden (backup/ek/evler/<ev>/GIT-HOOKS/) tek komutla
    yerine koyar. Yedegi `tools/yedekle.py` uretir; ikisi ayni desenin iki ucudur.

Kullanim:
    python3 tools/yedek-hook-kur.py           # kur / guncelle (yalniz YEDEK blogu)
    python3 tools/yedek-hook-kur.py --kuru    # ne yapacagini goster, YAZMA
    python3 tools/yedek-hook-kur.py --kaldir  # yalniz yedek blogunu cikar
    python3 tools/yedek-hook-kur.py --geri-yukle       # 5 EVIN TUM hook'larini yedekten kur
    python3 tools/yedek-hook-kur.py --geri-yukle --kuru # ne kurulacagini goster, YAZMA
    python3 tools/yedek-hook-kur.py --kendini-test     # BOS klonda kur + kapinin ATESLEDIGINI kanitla
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile

BAS = "# >>> PRUVO YEDEK BLOGU (tools/yedek-hook-kur.py uretir — ELLE DUZENLEME) >>>"
SON = "# <<< PRUVO YEDEK BLOGU <<<"

BLOK = BAS + """
# FAIL-OPEN: yedek patlasa/Drive olmasa bile push ASLA durmaz (blokta 'exit' YOK).
# UCUZ: --gerekliyse son damgadan beri degisiklik yoksa tek dosya bile kopyalamaz.
# Gorunurluk: python3 tools/durum.py  -> "7) YEDEK TAZELIGI"
pruvo_kok=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$pruvo_kok" ] && [ -f "$pruvo_kok/tools/yedekle.py" ]; then
  if ! python3 "$pruvo_kok/tools/yedekle.py" --gerekliyse >/dev/null 2>&1; then
    echo "!! YEDEK alinamadi (push DEVAM ediyor) — kontrol: python3 tools/durum.py"
  fi
fi
""" + SON


def hook_yolu(repo):
    """Ortak git dizinindeki hooks/pre-push (worktree'de de ANA depoyu gosterir)."""
    p = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    return os.path.join(p.stdout.strip(), "hooks", "pre-push")


def yeni_icerik(mevcut, kaldir=False):
    """Blogu ekler/gunceller/cikarir. (yeni_metin, eylem) doner."""
    if mevcut is None:
        if kaldir:
            return None, "hook yok — yapacak bir sey yok"
        return "#!/bin/sh\n" + BLOK + "\n", "YENI hook olusturuldu"

    if BAS in mevcut and SON in mevcut:
        bas = mevcut.index(BAS)
        son = mevcut.index(SON) + len(SON)
        yeni = mevcut[:bas] + ("" if kaldir else BLOK) + mevcut[son:]
        if kaldir:
            yeni = yeni.replace("\n\n\n", "\n\n")
        return yeni, ("blok CIKARILDI" if kaldir else "mevcut blok GUNCELLENDI")

    if kaldir:
        return mevcut, "blok zaten yok"

    # Blok YOK -> shebang'in hemen ardina koy (D1 blogunun 'exit 0'larindan ONCE).
    satirlar = mevcut.splitlines(True)
    yer = 1 if satirlar and satirlar[0].startswith("#!") else 0
    return "".join(satirlar[:yer]) + BLOK + "\n" + "".join(satirlar[yer:]), "blok EKLENDI (basa)"


# ==================== GERI YUKLEME: 5 EVIN TUM HOOK'LARI =====================

def _yedek_hook_kokleri():
    """Drive yedegindeki hook klasorleri: [(ev_adi, GIT-HOOKS yolu)].
    Kaynak: tools/yedekle.py'nin yazdigi backup/ek/evler/<ev>/GIT-HOOKS/.
    Drive cozulemezse bos liste (cagiran GURULTULU uyarir)."""
    burasi = os.path.dirname(os.path.abspath(__file__))
    if burasi not in sys.path:
        sys.path.insert(0, burasi)
    try:
        import drive_yolu
        import yedekle
    except ImportError:
        return []
    pruvo = drive_yolu.pruvo_dizini()
    if not pruvo:
        return []
    evler = os.path.join(pruvo, "backup", yedekle.EK_KLASOR, "evler")
    if not os.path.isdir(evler):
        return []
    cikti = []
    for ad in sorted(os.listdir(evler)):
        kancalar = os.path.join(evler, ad, yedekle.GIT_HOOK_KLASOR)
        if os.path.isdir(kancalar):
            cikti.append((ad, kancalar))
    return cikti


def _ev_hedefi(ev_adi):
    """Yerel evin .git/hooks yolu — ROOT'un KARDESI olarak cozulur. Yoksa None."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    taban = os.path.dirname(repo)
    ev = repo if os.path.basename(repo) == ev_adi else os.path.join(taban, ev_adi)
    if not os.path.exists(os.path.join(ev, ".git")):
        return None
    p = subprocess.run(["git", "-C", ev, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    return os.path.join(p.stdout.strip(), "hooks")


def hook_geri_yukle(kuru=False, kaynaklar=None, hedef_coz=None):
    """Yedekteki hook'lari evlerin .git/hooks'una koyar. Doner: (yazilan, atlanan, ev).

    IDEMPOTENT: icerik AYNIYSA dokunmaz. FARKLIYSA once tek seferlik guvenlik kopyasi
    (.pruvo-geri-yukleme-oncesi) alir — mevcut bir kapiyi sessizce EZMEK, kurmamaktan
    daha tehlikelidir. `kaynaklar`/`hedef_coz` yalniz kendini-test icin enjekte edilir."""
    kaynaklar = _yedek_hook_kokleri() if kaynaklar is None else kaynaklar
    hedef_coz = _ev_hedefi if hedef_coz is None else hedef_coz
    yazilan = atlanan = ev_sayisi = 0
    if not kaynaklar:
        print("⚠️ Yedekte hook bulunamadi (Drive bagli mi? backup/ek/evler/*/GIT-HOOKS)")
        return 0, 0, 0
    for ev_adi, kok in kaynaklar:
        hedef = hedef_coz(ev_adi)
        if not hedef:
            print("  %-18s YEREL EV YOK -> atlandi" % ev_adi)
            continue
        ev_sayisi += 1
        os.makedirs(hedef, exist_ok=True)
        for ad in sorted(os.listdir(kok)):
            kaynak = os.path.join(kok, ad)
            if not os.path.isfile(kaynak):
                continue
            varis = os.path.join(hedef, ad)
            with open(kaynak, "rb") as f:
                yeni = f.read()
            mevcut = None
            if os.path.isfile(varis):
                with open(varis, "rb") as f:
                    mevcut = f.read()
            if mevcut == yeni:
                atlanan += 1
                continue
            print("  %-18s %s  <- %s" % (ev_adi, ad, "GUNCELLENIYOR" if mevcut else "KURULUYOR"))
            if kuru:
                continue
            if mevcut is not None:
                kopya = varis + ".pruvo-geri-yukleme-oncesi"
                if not os.path.exists(kopya):
                    shutil.copy2(varis, kopya)
            with open(varis, "wb") as f:
                f.write(yeni)
            os.chmod(varis, os.stat(varis).st_mode | stat.S_IXUSR | stat.S_IXGRP
                     | stat.S_IXOTH)
            yazilan += 1
    return yazilan, atlanan, ev_sayisi


# ==================== KENDINI TEST: kapı GERCEKTEN atesliyor mu ==============

_NOBETCI = ("#!/usr/bin/env python3\n"
            "import os,sys\n"
            "open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..',%r),'w')"
            ".write('ates')\n"
            "sys.exit(%d)\n")


def kendini_test():
    """BOS bir klonda hook'lari kurar ve KAPININ ATESLEDIGINI ICRAYLA kanitlar.

    🔴 NEDEN NOBETCI DOSYA: pre-commit/pre-push bloklari `[ -f tools/... ] || exit 0`
    ile korunur, yani bos bir depoda hicbir sey yapmadan cikarlar. "Kuruldu ve
    calistirilabilir" demek KURULUMU kanitlar, CALISTIGINI kanitlamaz. Bu yuzden
    hook'un cagirdigi araclarin yerine, cagrildiginda iz birakan sahte NOBETCI
    betikler konur; sonra GERCEK `git commit` / `git push` kosulur ve izin olusup
    olusmadigi olculur. Iz yoksa test KIRMIZI yanar."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kaynak_hooks = os.path.join(repo, ".git", "hooks")
    kontroller = []

    def kontrol(ad, kosul, ayrinti=""):
        kontroller.append(bool(kosul))
        print("  %s %s%s" % ("✅" if kosul else "❌", ad,
                             ("  — " + str(ayrinti)) if ayrinti else ""))

    with tempfile.TemporaryDirectory() as td:
        kum_kok = os.path.join(td, "sahte-yedek", "pruvo", "GIT-HOOKS")
        os.makedirs(kum_kok)
        for ad in ("pre-commit", "pre-push"):
            p = os.path.join(kaynak_hooks, ad)
            if os.path.isfile(p):
                shutil.copy2(p, os.path.join(kum_kok, ad))
        kontrol("kaynak hook'lar yedek duzeninde bulundu",
                len(os.listdir(kum_kok)) == 2, os.listdir(kum_kok))

        klon = os.path.join(td, "bos-klon")
        os.makedirs(os.path.join(klon, "tools"))
        subprocess.run(["git", "-C", klon, "init", "-q", "-b", "main"], check=True)
        subprocess.run(["git", "-C", klon, "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", klon, "config", "user.name", "t"], check=True)
        kontrol("taze klonda hook YOK (klonlama hook TASIMAZ — testin ONCULU)",
                not os.path.isfile(os.path.join(klon, ".git", "hooks", "pre-commit")))

        yazilan, _atlanan, _ev = hook_geri_yukle(
            kaynaklar=[("pruvo", kum_kok)], hedef_coz=lambda a: os.path.join(
                klon, ".git", "hooks"))
        kontrol("geri yukleme hook'lari YAZDI", yazilan == 2, "yazilan=%d" % yazilan)
        for ad in ("pre-commit", "pre-push"):
            p = os.path.join(klon, ".git", "hooks", ad)
            kontrol("%s kuruldu ve CALISTIRILABILIR" % ad,
                    os.path.isfile(p) and os.access(p, os.X_OK))

        # NOBETCILER: hook'un cagirdigi araclarin yerine iz birakan sahteler.
        for arac, iz, kod in (("mukerrer-kontrol.py", "IZ-MUKERRER", 1),
                              ("urunler-guard.py", "IZ-GUARD", 0),
                              ("d1-sync.py", "IZ-D1", 0),
                              ("yedekle.py", "IZ-YEDEK", 0)):
            with open(os.path.join(klon, "tools", arac), "w") as f:
                f.write(_NOBETCI % (iz, kod))

        with open(os.path.join(klon, "urunler.json"), "w") as f:
            f.write("[]\n")
        subprocess.run(["git", "-C", klon, "add", "-A"], check=True)
        r = subprocess.run(["git", "-C", klon, "commit", "-m", "deneme"],
                           capture_output=True, text=True)
        kontrol("pre-commit ATESLEDI (guard nobetcisi iz birakti)",
                os.path.exists(os.path.join(klon, "IZ-GUARD")))
        kontrol("pre-commit mukerrer kapisi commit'i BLOKLADI (exit 1 yolu)",
                r.returncode != 0 and "COMMIT ENGELLENDI" in (r.stdout + r.stderr),
                "rc=%d" % r.returncode)

        # Kapi bloklamayi biraksin -> commit gecsin, sonra PUSH kapisini olcelim.
        with open(os.path.join(klon, "tools", "mukerrer-kontrol.py"), "w") as f:
            f.write(_NOBETCI % ("IZ-MUKERRER", 0))
        subprocess.run(["git", "-C", klon, "add", "-A"], check=True)
        r2 = subprocess.run(["git", "-C", klon, "commit", "-m", "deneme2"],
                            capture_output=True, text=True)
        kontrol("kapi yesilken commit GECIYOR (fail-open degil, dogru kapi)",
                r2.returncode == 0, "rc=%d" % r2.returncode)

        uzak = os.path.join(td, "uzak.git")
        subprocess.run(["git", "init", "-q", "--bare", uzak], check=True)
        subprocess.run(["git", "-C", klon, "remote", "add", "origin", uzak], check=True)
        r3 = subprocess.run(["git", "-C", klon, "push", "-u", "origin", "main"],
                            capture_output=True, text=True)
        kontrol("push GECTI (hook fail-open: yedek/D1 push'u DURDURMAZ)",
                r3.returncode == 0, "rc=%d" % r3.returncode)
        kontrol("pre-push YEDEK blogu ATESLEDI (yedek nobetcisi iz birakti)",
                os.path.exists(os.path.join(klon, "IZ-YEDEK")))
        kontrol("🔴 pre-push D1 SENKRON blogu ATESLEDI (urunler.json degisti)",
                os.path.exists(os.path.join(klon, "IZ-D1")),
                (r3.stdout + r3.stderr).strip()[-120:])

    kirmizi = kontroller.count(False)
    print("\nTOPLAM %d kontrol, %d kirmizi" % (len(kontroller), kirmizi))
    print("SONUC: " + ("YESIL ✅ — hook'lar bos klonda kuruldu VE atesledi"
                       if not kirmizi else "KIRMIZI 🔴"))
    return 1 if kirmizi else 0


def main():
    kuru = "--kuru" in sys.argv
    kaldir = "--kaldir" in sys.argv
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__.strip())
        return 0
    gecerli = ("--kuru", "--kaldir", "--geri-yukle", "--kendini-test")
    bilinmeyen = [a for a in sys.argv[1:] if a not in gecerli]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        print("Gecerli: " + ", ".join(gecerli), file=sys.stderr)
        return 2

    if "--kendini-test" in sys.argv:
        return kendini_test()

    if "--geri-yukle" in sys.argv:
        print("HOOK GERI YUKLEME (kaynak: Drive yedegi backup/ek/evler/*/GIT-HOOKS)")
        yazilan, atlanan, ev = hook_geri_yukle(kuru=kuru)
        print("%d ev, %d hook yazildi, %d zaten guncel.%s"
              % (ev, yazilan, atlanan, "  (KURU KOSUM — yazilmadi)" if kuru else ""))
        if not ev:
            return 1
        return 0

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yol = hook_yolu(repo)
    if not yol:
        print("HATA: git deposu bulunamadi: " + repo, file=sys.stderr)
        return 1

    mevcut = None
    if os.path.isfile(yol):
        with open(yol, encoding="utf-8", errors="replace") as f:
            mevcut = f.read()

    yeni, eylem = yeni_icerik(mevcut, kaldir=kaldir)
    print("hook: " + yol)
    print("eylem: " + eylem)
    if yeni is None or yeni == mevcut:
        print("degisiklik YOK (idempotent).")
        return 0
    if kuru:
        print("KURU KOSUM — yazilmadi.")
        return 0

    # Ilk degisiklikte tek seferlik guvenlik kopyasi (D1 blogu kaybolmasin).
    kopya = yol + ".pruvo-yedek-oncesi"
    if mevcut is not None and not os.path.exists(kopya):
        shutil.copy2(yol, kopya)
        print("guvenlik kopyasi: " + kopya)

    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("yazildi + calistirilabilir yapildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
