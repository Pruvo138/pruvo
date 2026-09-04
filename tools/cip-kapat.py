#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ÇİP KAPANIŞ KILAVUZU — "işini bitir, kapanışını yaz, ağacını temizle" tek komut.

Okan bu komutu çip açanlara VERİR; çip kendi ağacında koşar ve ne yapacağını
ADIYLA öğrenir. Bilgi CLAUDE.md'ye, hafızaya ve üç ayrı araca dağılmıştı; burada
TEK yerden, ÖLÇÜLMÜŞ hâliyle söylenir.

🔴 HÜKMÜ KENDİ UYDURMAZ: "bu ağaç silinebilir mi" yargısı `arsiv-kapisi.py`den
gelir (dört kol: AGAC_KIRLI · ICERIK_DISARIDA · ITILMEMIS · KAPANIS_YOK; üç kova:
rc=0 ARSIVLENEBILIR / rc=1 ARSIVLENEMEZ / rc=2 OLCULEMEDI). İkinci bir silme
ölçütü yazmak, kapıyı atlatan ikinci bir yol açardı.

🔴 SİLME YALNIZ rc=0'da. `--uygula` silmeden HEMEN ÖNCE kapıyı YENİDEN koşar
(arada ağaç kirlenmiş olabilir); rc≠0 ise HİÇBİR ŞEY silinmez.

🔴 OTURUMU CANLI KENDİ AĞACINI SİLDİRMEZ: komut, sileceği ağacın İÇİNDEN
çağrıldıysa uygulamayı REDDEDER (çip kendi altındaki zemini çeker; git index ve
açık dosyalar bozulur → [[kendi-worktreeni-oturum-canliyken-kaldirma]]).

KULLANIM
  python3 tools/cip-kapat.py                 → kendi ağacını ölçer, NE YAPMALI der
  python3 tools/cip-kapat.py <agac-yolu>     → o ağacı ölçer
  python3 tools/cip-kapat.py <agac> --uygula → rc=0 ise worktree+dal siler (ANA checkout'tan)

ÇIKIŞ: 0 = temiz/arşivlendi · 1 = yapılacak iş VAR (adıyla) · 2 = ölçülemedi.
"""
import argparse
import os
import re
import subprocess
import sys

VARSAYILAN_REPO = "/Users/okan/dev/pruvo"
KAPI = os.path.join(VARSAYILAN_REPO, "tools", "arsiv-kapisi.py")
KUTU = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md")

# Kol -> (ne demek, NE YAPMALI). Metinler ARACIN CIKTISINDAN degil, kolun
# ADINDAN eslenir; kapi metnini degistirse de kilavuz kaymaz.
CARE = {
    "AGAC_KIRLI": (
        "Ağaçta commit'lenmemiş değişiklik var — silinirse O İŞ KAYBOLUR.",
        ["git -C {agac} status --short          # neyin durduğunu GÖR",
         "git -C {agac} add -A && git -C {agac} commit    # ya işle...",
         "git -C {agac} checkout -- .                      # ...ya da bilerek at"]),
    "ICERIK_DISARIDA": (
        "Dalın ucu main'in ATASI DEĞİL: içerik main'e girmemiş. Silmek işi yok eder.",
        ["git -C {repo} log --oneline main..{dal}                 # ne kadar iş var",
         "git -C {repo} diff --stat $(git -C {repo} merge-base main {dal}) {dal}",
         "# sonra: skill merge-kapisi yordamıyla main'e al (çakışma ön-testi + dalın kapıları + D1)"]),
    "ITILMEMIS": (
        "Dalın ucu hiçbir uzak ref'te yok: yerel disk tek kopya.",
        ["git -C {repo} push origin {dal}"]),
    "KAPANIS_YOK": (
        "Kutuda eşleşen SAYILI KAPANIŞ yok — iş görünmez kalır, sayaç kirlenir.",
        ["# kutuya sayılı kapanış yaz (aşağıdaki şablon), sonra bu komutu TEKRAR koş"]),
}

KAPANIS_SABLONU = """## <TARİH> — ✅ <ÇİP-ADI> (çip `{agac_adi}`) **SAYILI KAPANIŞ — <tek cümle sonuç>**

🔴 BAŞLIKTA WORKTREE ADI BACKTICK İÇİNDE GEÇSİN: eşleşme ad KÜMESİYLE kurulur;
worktree adı başlıkta yoksa kapanışı YAZILMIŞ çip kapıya YAZILMAMIŞ görünür.

**CANLIYA/DALA İNEN:** <sha> — <N dosya +X/−Y>
**KABUL (önceden çivilenen ölçütlerin her biri, SAYIYLA):**
① <ölçüt> = <sayı> ② <ölçüt> = <sayı> ...
🔴 **ÖLÇMEDİĞİM:** <varsa adıyla> — `OLCULEMEDI` yaz, YEŞİL SAYMA.
*Neyi ölçmek kapatır:* <tek cümle>
**MOTOR ORANI:** Claude <%> · m3 <%> · kimi <%> — <gerekçe>
**TEMİZLİK:** <du öncesi→sonrası, silinen geçici kalemler>
— <ÇİP-ADI>

✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM
"""


def kos(argv, cwd=None, sure=300):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                          timeout=sure, stdin=subprocess.DEVNULL)


def git(repo, *a):
    p = kos(["git", "-C", repo] + list(a))
    return (p.stdout or "").strip(), p.returncode


def agac_coz(yol):
    """(agac_koku, dal, repo_koku) — verilen yolun worktree kimligi."""
    ust, rc = git(yol, "rev-parse", "--show-toplevel")
    if rc != 0:
        return None, None, None
    dal, _ = git(yol, "rev-parse", "--abbrev-ref", "HEAD")
    ortak, rc2 = git(yol, "rev-parse", "--path-format=absolute", "--git-common-dir")
    repo = VARSAYILAN_REPO
    if rc2 == 0 and ortak.endswith(".git"):
        repo = os.path.dirname(ortak)
    return ust, dal, repo


def kapi_kos(agac, repo):
    p = kos([sys.executable, KAPI, agac, "--repo", repo], sure=600)
    ham = (p.stdout or "") + (p.stderr or "")
    kollar = dict(re.findall(r"KOL=(\w+) HAL=(\w+)", ham))
    m = re.search(r"HUKUM=(\w+) rc=(\d+)", ham)
    hukum = m.group(1) if m else "OLCULEMEDI"
    rc = int(m.group(2)) if m else 2
    return hukum, rc, kollar, ham


def taze_dokunus_dk(agac, tavan_dosya=4000):
    """Agactaki EN YENI dosya kac dakika once dokunuldu? (None = olculemedi)

    🔴 NEDEN: `--uygula` bir UCUNCU TARAFTIR — sileceigi agacin oturumu HALA CANLI
    olabilir. 4 Eyl 2026'da olculdu: arsivleyici canli bir cipin agacini sildi, cipin
    oturumu ROL=ANA'ya dustu, evindeki kapi o roldeki `python3` cagrilarini kesti ve
    cip kendi kapanisini bile YAZAMADI. Oz-agac emniyeti bunu YAKALAMAZ (silen baska
    bir surectir), o yuzden AYRI kol gerekir.

    🔴 CANLILIK KANITI olarak `ListAgents` KULLANILMAZ: yoklugu olum kaniti degildir
    ([[listagents-yoklugu-olum-kaniti-degil]]). Burada DISK olculur: yakin zamanda
    yazilmis bir agac CANLI SAYILIR (yanlis-pozitif ZARARSIZ — silme ERTELENIR;
    yanlis-negatif ZARARLI — canli cip kirilir). Olculemezse CANLI SAYILIR.
    """
    en_yeni = None
    sayac = 0
    for dizin, altlar, dosyalar in os.walk(agac):
        altlar[:] = [d for d in altlar if d not in (".git", "node_modules", "__pycache__")]
        for d in dosyalar:
            sayac += 1
            if sayac > tavan_dosya:
                break
            try:
                m = os.path.getmtime(os.path.join(dizin, d))
            except OSError:
                continue
            if en_yeni is None or m > en_yeni:
                en_yeni = m
        if sayac > tavan_dosya:
            break
    if en_yeni is None:
        return None
    import time as _t
    return (_t.time() - en_yeni) / 60.0


def icinde_mi(yol, agac):
    a = os.path.realpath(agac)
    y = os.path.realpath(yol)
    return y == a or y.startswith(a + os.sep)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("agac", nargs="?", default=os.getcwd())
    ap.add_argument("--uygula", action="store_true",
                    help="rc=0 ise worktree + dal SİL (ana checkout'tan koşulmalı)")
    ap.add_argument("--yas-tavani", type=int, default=20, metavar="DK",
                    help="ağaca bu kadar dakika içinde dokunulmuşsa CANLI say, SİLME "
                         "(varsayılan 20; bilerek geçmek için 0)")
    a = ap.parse_args()

    agac, dal, repo = agac_coz(a.agac)
    if not agac:
        print("🔴 git ağacı değil: %s" % a.agac)
        return 2
    agac_adi = os.path.basename(agac.rstrip("/"))
    ana_mi = os.path.realpath(agac) == os.path.realpath(repo)

    print("ÇİP KAPANIŞ KILAVUZU")
    print("  ağaç : %s%s" % (agac, "   (ANA CHECKOUT)" if ana_mi else ""))
    print("  dal  : %s" % dal)
    print("  repo : %s" % repo)
    print()

    if ana_mi:
        print("Bu ANA CHECKOUT — silinecek bir çip ağacı değil.")
        print("Evdeki kapanışsız çipleri görmek için:")
        print("  python3 %s/tools/cip-supurme.py" % repo)
        return 0

    # 🔴 ON KOSUL, KAPI SONRASI KONTROL DEGIL: oz-agac yasagi kapidan ONCE sorulur.
    # Kapidan sonra sorulsaydi kol YALNIZ rc=0 agacta calisirdi; kirmizi agacta akis
    # daha once cikar ve emniyet HIC KOSMAZDI — kabul bataryasi bunu "ULASMADI" diye
    # yakaladi ([[emniyet-kontrolu-yorumdan-once-korlestirir]] emsali).
    if a.uygula and icinde_mi(os.getcwd(), agac):
        print("🔴 UYGULAMA REDDEDİLDİ: bu komut, sileceği ağacın İÇİNDEN çağrıldı.")
        print("   Çip kendi altındaki zemini çekerse git index'i ve açık dosyaları bozulur.")
        print("   ÇARE: ana checkout'tan koş —")
        print("     python3 %s/tools/cip-kapat.py %s --uygula" % (repo, agac))
        return 2

    hukum, rc, kollar, ham = kapi_kos(agac, repo)
    print("KAPI (arsiv-kapisi.py): HUKUM=%s rc=%d" % (hukum, rc))
    for ad, hal in kollar.items():
        print("   KOL=%-16s HAL=%s" % (ad, hal))
    print()

    if rc != 0:
        print("YAPILACAK İŞ VAR — sıra önemli değil, hepsi kapanmalı:")
        print()
        sira = 0
        for ad, hal in kollar.items():
            if hal in ("TEMIZ", "KAPSAM_DISI"):
                continue
            sira += 1
            ne, komutlar = CARE.get(ad, ("(bilinmeyen kol)", []))
            print("  %d) KOL=%s  HAL=%s" % (sira, ad, hal))
            print("     %s" % ne)
            for k in komutlar:
                print("     $ " + k.format(agac=agac, repo=repo, dal=dal))
            print()
        if kollar.get("KAPANIS_YOK") not in (None, "TEMIZ", "KAPSAM_DISI"):
            print("KAPANIŞ ŞABLONU (kutuya EN ÜSTE, TEK Write, mevcut içeriği KAYBETMEDEN):")
            print("kutu: %s" % KUTU)
            print()
            print(KAPANIS_SABLONU.format(agac_adi=agac_adi))
        print("Hepsi kapandıktan sonra:  python3 %s/tools/cip-kapat.py %s --uygula"
              % (repo, agac))
        return 1 if hukum == "ARSIVLENEMEZ" else 2

    print("✅ ARŞİVLENEBİLİR — dört kol da temiz.")
    if not a.uygula:
        print()
        print("Silmek için (ANA CHECKOUT'tan koş, kendi ağacının içinden DEĞİL):")
        print("  python3 %s/tools/cip-kapat.py %s --uygula" % (repo, agac))
        print()
        print("Elle yapmak istersen birebir aynısı:")
        print("  git -C %s worktree remove %s" % (repo, agac))
        print("  git -C %s branch -d %s" % (repo, dal))
        return 0

    # 🔴 CANLI OTURUM EMNIYETI — kapidan AYRI kol. Kapi "icerik guvende mi" sorar;
    # bu kol "oturum hala calisiyor mu" sorar. Ikisi FARKLI sorulardir: dort kol da
    # yesilken bile canli bir cipin agacini silmek onu kirar (olculdu 4 Eyl).
    yas = taze_dokunus_dk(agac)
    if yas is None or yas < a.yas_tavani:
        print("🔴 SİLME ERTELENDİ — ağaç CANLI olabilir.")
        print("   en son dokunuş: %s (tavan %d dk)"
              % ("OLCULEMEDI" if yas is None else "%.1f dk önce" % yas, a.yas_tavani))
        print("   Canlı bir çipin ağacını silmek onu ROL=ANA'ya düşürür; evindeki")
        print("   kapılar o roldeki çağrılarını kesebilir ve çip kapanışını bile yazamaz.")
        print("   ÇARE: çipin `✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM` satırını bekle, ya da")
        print("   bilerek geç:  --yas-tavani 0")
        return 2

    # 🔴 TOCTOU: silmeden HEMEN ONCE kapiyi YENIDEN kos. Ilk olcumden bu yana agac
    # kirlenmis ya da dal geri alinmis olabilir; eski rc ile silmek fail-open olurdu.
    hukum2, rc2, _k2, _h2 = kapi_kos(agac, repo)
    if rc2 != 0:
        print("🔴 SİLME İPTAL: kapı silmeden hemen önce yeniden koştu ve rc=%d (%s) verdi."
              % (rc2, hukum2))
        print("   Ağaç ilk ölçümden sonra değişmiş. Baştan koş.")
        return 1

    du_once = kos(["du", "-sk", agac]).stdout.split()[0] if os.path.exists(agac) else "?"
    p = kos(["git", "-C", repo, "worktree", "remove", agac], sure=600)
    if p.returncode != 0:
        print("🔴 worktree remove DÜŞTÜ: %s" % ((p.stderr or "").strip()[-300:]))
        return 1
    p2 = kos(["git", "-C", repo, "branch", "-d", dal], sure=300)
    dal_hal = "SILINDI" if p2.returncode == 0 else ("KALDI: %s"
                                                   % (p2.stderr or "").strip()[-160:])
    print("ARŞİVLENDİ:")
    print("  worktree SILINDI (%s KB)" % du_once)
    print("  dal %s -> %s" % (dal, dal_hal))
    print("  ağaç diskte duruyor mu: %s" % os.path.exists(agac))
    return 0


if __name__ == "__main__":
    sys.exit(main())
