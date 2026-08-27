#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TEK KOMUTLUK KOSUCU — isci prozasina GUVENILMEZ.

Adimlari SIRAYLA kosar, HAM ciktiyi GIT-DISI tek dosyaya doker, ekrana yalniz
kisa ozet basar. Sayilar DOSYADAN okunur.
([[ucuz-isci-yesil-tablo-uydurur]] · [[isci-yesil-tablo-ic-olcumu-bosaltir]])

  --tur 1 : KURULUM (kuru + gercek) + A1 (ortam) + teslim karari KURU
  --tur 2 : A2..A5 (canli spec URETILIR) + teslim bataryasi + bekci tabani
  --tur 3 : B8 — `bekci-kur.py` baslik hizalamasi + damga bayt esitligi
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import time

WT = os.path.dirname(os.path.abspath(__file__))
CRON = "/Users/okan/.claude/cron"
CIKTI = "/private/tmp/pruvo-sabah-teslim"
PY = sys.executable or "python3"
DAMGA_DESENI = re.compile(r"^(KURULDU|KOSTU)=", re.M)
KALP = os.path.join(CRON, "bekci-teslim-kalp.md")

TURLAR = {
    1: [
        ("1a-KURULUM-KURU", [PY, os.path.join(WT, "kur.py"), "--kuru"], 180, True),
        ("1b-KURULUM", [PY, os.path.join(WT, "kur.py")], 300, True),
        ("1c-A1-ORTAM", [PY, os.path.join(CRON, "sabah-kabul.py"), "--faz", "on"], 600, False),
        ("1d-TESLIM-KARARI-KURU",
         [PY, os.path.join(CRON, "cip_dogum_bekcisi.py"), "--teslim-karari", "--kuru"],
         120, False),
    ],
    # TUR 6 = TEMIZ YENIDEN KURULUM + TAM KABUL. `--geri-al` ONCE kurulum-oncesi
    # hale sarar, sonra duzeltilmis yamalar SIFIRDAN uygulanir — boylece "yama
    # ustune yama" katmanlanmasi olmaz ve capa dogrulamasi gercekten kosar.
    6: [
        ("6a-GERI-AL", [PY, os.path.join(WT, "kur.py"), "--geri-al"], 180, True),
        ("6b-KURULUM", [PY, os.path.join(WT, "kur.py")], 300, True),
        ("6c-SABAH-KABUL-TAM", [PY, os.path.join(CRON, "sabah-kabul.py"), "--faz", "tam"], 1800, False),
        ("6d-BEKCI-TESLIM", [PY, os.path.join(CRON, "bekci-kabul.py"), "--faz", "teslim"], 900, False),
        ("6e-BEKCI-YUZEY", [PY, os.path.join(CRON, "bekci-kabul.py"), "--faz", "yuzey"], 900, False),
        ("6f-BEKCI-YON", [PY, os.path.join(CRON, "bekci-kabul.py"), "--faz", "yon"], 900, False),
    ],
    2: [
        ("2a-SABAH-KABUL-TAM", [PY, os.path.join(CRON, "sabah-kabul.py"), "--faz", "tam"], 1800, False),
        ("2b-BEKCI-TESLIM", [PY, os.path.join(CRON, "bekci-kabul.py"), "--faz", "teslim"], 900, False),
        ("2c-BEKCI-YON", [PY, os.path.join(CRON, "bekci-kabul.py"), "--faz", "yon"], 900, False),
        ("2d-BEKCI-YUZEY", [PY, os.path.join(CRON, "bekci-kabul.py"), "--faz", "yuzey"], 900, False),
    ],
}


def kos(argv, zaman_asimi):
    basla = time.time()
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=zaman_asimi)
        return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - basla
    except subprocess.TimeoutExpired:
        return 124, "ZAMAN_ASIMI %ds" % zaman_asimi, time.time() - basla
    except Exception as hata:
        return 125, "%s: %s" % (type(hata).__name__, hata), time.time() - basla


def _kalp_dokumu():
    """(sha1, bayt, damga_satirlari) — damgalar BAYT BIREBIR kiyaslanacak."""
    try:
        with open(KALP, "rb") as f:
            ham = f.read()
    except OSError as hata:
        return "-", -1, ["OKUNAMADI:%s" % type(hata).__name__], ""
    metin = ham.decode("utf-8", "replace")
    damgalar = [s for s in metin.splitlines() if DAMGA_DESENI.match(s)]
    return hashlib.sha1(ham).hexdigest(), len(ham), damgalar, metin


def tur3(yaz):
    """B8 — kurucu VAR OLAN baslıgi yeni sozlesmeye HIZALIYOR mu, damgalar
    BAYT BIREBIR duruyor mu. Iki iddia AYRI AYRI olculur."""
    sha1, b1, d1, m1 = _kalp_dokumu()
    yaz("B8_T1_SHA1=%s BAYT=%d DAMGA_ADEDI=%d" % (sha1, b1, len(d1)))
    for s in d1:
        yaz("B8_T1_DAMGA %r" % s)
    yaz("--- B8_T1 TAM METIN ---")
    yaz(m1.rstrip("\n"))

    rc, cikti, sure = kos([PY, os.path.join(CRON, "bekci-kur.py")], 240)
    yaz("\nB8_KURUCU_RC=%d SURE=%.1fs" % (rc, sure))
    yaz(cikti.rstrip("\n"))

    sha3, b3, d3, m3 = _kalp_dokumu()
    yaz("\nB8_T3_SHA1=%s BAYT=%d DAMGA_ADEDI=%d" % (sha3, b3, len(d3)))
    yaz("--- B8_T3 TAM METIN ---")
    yaz(m3.rstrip("\n"))

    hizalandi = ("9" in m3 and "15" in m3 and m3 != m1)
    damga_ayni = (d1 == d3)
    yaz("\nB8_BASLIK_DEGISTI=%d  (1 = kurucu var-olan basligi TAZELEDI)"
        % (0 if sha3 == sha1 else 1))
    yaz("B8_DAMGA_BAYT_BIREBIR=%d  (1 = damgalara DOKUNULMADI)" % int(damga_ayni))
    yaz("B8_HIZALAMA_IPUCU=%d" % int(hizalandi))
    # idempotens: ikinci kosum degistirmemeli
    rc2, cikti2, _ = kos([PY, os.path.join(CRON, "bekci-kur.py")], 240)
    sha4, _, d4, _ = _kalp_dokumu()
    yaz("B8_IDEMPOTENT=%d rc2=%d  (1 = ikinci kosum dosyayi DEGISTIRMEDI)"
        % (int(sha4 == sha3), rc2))
    yaz("B8_DAMGA_IKINCI_TURDA_BIREBIR=%d" % int(d3 == d4))
    return 0


def tur7(yaz):
    """URETEN TEMIZLER (Okan, USTUN kural). du ONCE -> temizlik -> du SONRA.

    KORUNAN: her dokunulan dosya icin **EN ESKI** `.yedek-sabahteslim-*` kopya
    (o, degisiklikten ONCEKI gercek halidir); fazlalar SILINIR.
    """
    import glob
    import shutil as sh

    hedefler = ["/private/tmp/pruvo-sabah-teslim",
                "/private/tmp/pruvo-bekci-teslim",
                os.path.join(CRON, "__pycache__")]

    def _du(etiket):
        for h in hedefler:
            rc, cikti, _ = kos(["du", "-sk", h], 60)
            yaz("DU_%s %s" % (etiket, (cikti or "").strip() or "(yok)"))
        rc, cikti, _ = kos(["df", "-k", "/"], 60)
        yaz("DF_%s %s" % (etiket, (cikti or "").strip().splitlines()[-1]))

    yaz("########## TEMIZLIK — ONCE ##########")
    _du("ONCE")

    # 1) yedek fazlaliklari: her dosya icin EN ESKI kalir
    yaz("\n########## YEDEK BUDAMA (en ESKI kalir) ##########")
    for ad in ("kral-sabah.py", "sabah-kabul.py", "cip_dogum_bekcisi.py",
               "bekci-kabul.py", "bekci-kur.py"):
        adaylar = sorted(glob.glob(os.path.join(CRON, ad + ".yedek-sabahteslim-*")))
        if not adaylar:
            yaz("YEDEK %-24s adet=0 (KORUNAN yok)" % ad)
            continue
        korunan, fazla = adaylar[0], adaylar[1:]
        for f in fazla:
            try:
                os.unlink(f)
            except OSError as hata:
                yaz("  SILINEMEDI %s (%s)" % (f, type(hata).__name__))
        yaz("YEDEK %-24s adet=%d KORUNAN=%s silinen=%d"
            % (ad, len(adaylar), os.path.basename(korunan), len(fazla)))

    # 2) gecici cikti duzlemleri
    yaz("\n########## GECICI DUZLEMLER ##########")
    for d in ("/private/tmp/pruvo-sabah-teslim",):
        sh.rmtree(d, ignore_errors=True)
        yaz("SILINDI %s var=%d" % (d, int(os.path.isdir(d))))
    # prompt duzlemi CANLIDIR (rutin her sabah oraya yazar) — yalniz BUGUNKU
    # dosya silinir, dizin KALIR.
    for f in glob.glob("/private/tmp/pruvo-bekci-teslim/prompt-*.md"):
        try:
            os.unlink(f)
            yaz("SILINDI %s" % f)
        except OSError as hata:
            yaz("SILINEMEDI %s (%s)" % (f, type(hata).__name__))
    for f in glob.glob(os.path.join(CRON, "__pycache__", "*sabah*")) + \
             glob.glob(os.path.join(CRON, "*.pyc")):
        try:
            os.unlink(f)
            yaz("SILINDI %s" % f)
        except OSError:
            pass

    yaz("\n########## TEMIZLIK — SONRA ##########")
    _du("SONRA")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", type=int, required=True, choices=(1, 2, 3, 4, 5, 6, 7, 8))
    ap.add_argument("--anahtar", default=None)
    ap.add_argument("--task-id", default=None)
    a = ap.parse_args()

    os.makedirs(CIKTI, exist_ok=True)
    ham_yol = os.path.join(CIKTI, "tur%d.log" % a.tur)
    satirlar = []

    def yaz(s):
        satirlar.append(s)

    yaz("SABAH+TESLIM TUR %d — %s" % (a.tur, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
    ozet = []

    if a.tur == 8:
        # 🔴 SON DOGRULAMA: crontab'in YARIN 06:20'de kosacagi komutun BIREBIR
        # tekrari. `--kendini-test`in capraz kolu bunu zaten olcuyor, ama o kol
        # `--ortam-testi` modunu kosturuyor; burada TAM IS kosar.
        # Komut, crontab satirindan OKUNUR — elle yazilmaz.
        rcC, ciktiC, _ = kos(["crontab", "-l"], 30)
        satir = "-"
        for s in (ciktiC or "").splitlines():
            t = s.strip()
            if t and not t.startswith("#") and "kral-sabah.py" in t:
                satir = t
        yaz("CRONTAB_SATIRI: %s" % satir)
        parcalar = [p for p in satir.split() if p.startswith("/")]
        if len(parcalar) < 2:
            yaz("CRON_KOMUTU=OLCULEMEDI (satir cozulemedi)")
            ozet.append("8-CRON-TEKRARI=OLCULEMEDI")
        else:
            argv = parcalar[:2]
            yaz("CRON_KOMUTU: %s" % " ".join(argv))
            rc8, cikti8, sure8 = kos(argv, 300)
            yaz(cikti8.rstrip("\n"))
            yaz("---- CRON TEKRARI rc=%d sure=%.1fs ----" % (rc8, sure8))
            ozet.append("8-CRON-TEKRARI=rc%d" % rc8)
        # teslim kolu ayni gun ikinci kez: SESSIZ kalmali
        rc9, cikti9, _ = kos(
            [PY, os.path.join(CRON, "cip_dogum_bekcisi.py"), "--teslim-karari"], 120)
        yaz("\n########## TESLIM KOLU (spec ARTIK VAR) ##########")
        yaz(cikti9.rstrip("\n"))
        ozet.append("8b-TESLIM=rc%d" % rc9)
    elif a.tur == 7:
        tur7(yaz)
        ozet.append("7-TEMIZLIK=bak")
    elif a.tur == 3:
        tur3(yaz)
        ozet.append("3-B8=bak")
    elif a.tur == 4:
        # B1 CANLI: teslim kolu GERCEKTEN kosar; cipi mimar oturumu dogurur.
        rc, cikti, sure = kos(
            [PY, os.path.join(CRON, "cip_dogum_bekcisi.py"), "--teslim-karari"], 180)
        yaz("########## TESLIM KARARI (CANLI) ##########")
        yaz(cikti.rstrip("\n"))
        yaz("---- rc=%d sure=%.1fs ----" % (rc, sure))
        prompt_yolu = "-"
        for satir in cikti.splitlines():
            if satir.startswith("PROMPT_YOLU="):
                prompt_yolu = satir.split("=", 1)[1].strip()
        yaz("\n########## URETILEN PROMPT (AYNEN) ##########")
        if prompt_yolu != "-" and os.path.isfile(prompt_yolu):
            with open(prompt_yolu, encoding="utf-8") as f:
                yaz(f.read().rstrip("\n"))
            yaz("\nPROMPT_BAYT=%d" % os.path.getsize(prompt_yolu))
        else:
            yaz("PROMPT YOK (yol=%s)" % prompt_yolu)
        yaz("\n########## TESLIM LOG KUYRUGU ##########")
        try:
            with open(os.path.join(CRON, "bekci-bildirim.log"), encoding="utf-8") as f:
                for s in f.read().splitlines()[-6:]:
                    yaz(s)
        except OSError as hata:
            yaz("LOG OKUNAMADI: %s" % type(hata).__name__)
        ozet.append("4-TESLIM-KARARI=rc%d" % rc)
    elif a.tur == 5:
        # (c) KAYIT — cip DOGDU, task_id geri yaziliyor.
        rc, cikti, sure = kos(
            [PY, os.path.join(CRON, "cip_dogum_bekcisi.py"), "--teslim-kaydet",
             "--anahtar", str(a.anahtar), "--task-id", str(a.task_id)], 120)
        yaz("########## TESLIM KAYDI (CANLI) ##########")
        yaz(cikti.rstrip("\n"))
        yaz("---- rc=%d sure=%.1fs ----" % (rc, sure))
        yaz("\n########## TESLIM LOG KUYRUGU ##########")
        try:
            with open(os.path.join(CRON, "bekci-bildirim.log"), encoding="utf-8") as f:
                for s in f.read().splitlines()[-4:]:
                    yaz(s)
        except OSError as hata:
            yaz("LOG OKUNAMADI: %s" % type(hata).__name__)
        # B3 IKINCI SAVUNMA: ayni gun IKINCI kosum ikinci cip URETMEZ
        rc2, cikti2, _ = kos(
            [PY, os.path.join(CRON, "cip_dogum_bekcisi.py"), "--teslim-karari"], 120)
        yaz("\n########## B3 CANLI — AYNI GUN IKINCI KOSUM ##########")
        yaz(cikti2.rstrip("\n"))
        yaz("---- rc=%d ----" % rc2)
        ozet.append("5-TESLIM-KAYIT=rc%d 5b-IKINCI-KOSUM=rc%d" % (rc, rc2))
    else:
        kesildi = False
        for ad, argv, zaman_asimi, zorunlu in TURLAR[a.tur]:
            yaz("\n\n########## ADIM %s ##########" % ad)
            yaz("KOMUT: %s" % " ".join(argv))
            if kesildi:
                yaz("ATLANDI (onceki zorunlu adim dustu)")
                ozet.append("%s=ATLANDI" % ad)
                continue
            rc, cikti, sure = kos(argv, zaman_asimi)
            yaz(cikti.rstrip("\n"))
            yaz("---- ADIM %s rc=%d sure=%.1fs ----" % (ad, rc, sure))
            ozet.append("%s=rc%d(%.0fs)" % (ad, rc, sure))
            if zorunlu and rc != 0:
                kesildi = True
                yaz("\n🔴 ZINCIR KESILDI: zorunlu adim %s rc=%d" % (ad, rc))

    yaz("\n\n########## OZET ##########")
    yaz(" ".join(ozet))
    # tur7 kendi cikti dizinini SILER; kaniti yazabilmek icin geri acilir.
    # Dizin bu tek dosyayla kalir ve mimar okuduktan sonra ELLE silinir.
    os.makedirs(CIKTI, exist_ok=True)
    with open(ham_yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    print("HAM=%s" % ham_yol)
    print("OZET: %s" % " ".join(ozet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
