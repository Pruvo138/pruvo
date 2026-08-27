#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/n2-kabul.py — N2 "kirleten onarir" UCTAN UCA KABUL (spec §2).

Okan onayli doktrin (19 Agu 2026). Okan'in vakasi birebir:
  "MaCiT 100-100 urun ekliyor, iletiyi gormedi, isine devam etti; tamirat
   yapilmadigi icin tum mimarlar MaCiT'i bekledi."
HUKUM: mesaj kacar, KAPI kacmaz.

Bu betik spec §2'nin ONCEDEN CIVILENMIS kabul listesini SENTETIK VAKALARLA
uctan uca kosar. Her vaka GERCEK mekanizmayi cagirir; hicbiri "iddiaya" bakmaz.

  A1  veri dosyasi degistiren GERCEK commit  -> kalem MaCiT'e (KraL'a DEGIL)
  A2  worker/ commit -> HocA · jenerator/ commit -> TeKiN
  A3  cok-seritli commit -> KraL VE ciktida `SAHIP=KraL SEBEP=cok-seritli` YAZAR
  A4  harita TEK KAYNAK: haritayi bozan mutant hem KAPIYI hem GOZCUYU kirmizi yakar
  B1  acik 🔧 varken yeni parti REDDEDILIR + kalem + `kabul:` komutu BASILIR
  B2  🔴 NEGATIF: suren/yarim is KESILMEZ (ayni kosumda kanit)
  B3  kalem kapaninca AYNI komut GECER (kapi kalici kilit degil)
  B4  kapi KURUCUDAN dagitildi: `KURULU_EV=n/n` + her ev YEDEKLI
  C1  zaman enjekte edilen fiksturle 4 saat -> devir + `DEVREDILDI` + ihlal +1
  C2  4 saat DOLMADAN devir YOK
  C3  devir sonrasi kalem IKI DEFTERDE BIRDEN acik kalmaz
  C4  🔴 K229 defteri HIC OLMAYAN ev: N2B kapisi UCUNCU KOVA (`N2B-DEFTER-YOK`)
      ile ayirir — GECER ama SESSIZ DEGIL; defterli+kalemli ev HALA RED
  Z1  her mekanizmada mutant + hedef-kol atfi (A/B/C kendini-testleri)
  Z2  urunler.json DEGISMEDI · baska evin defterine ELLE satir YAZILMADI

Hepsi HERMETIK: gecici dizinler, sentetik git deposu, sentetik defterler.
CANLI defterlere/posta kutularina/urunler.json'a DOKUNULMAZ (Z2 bunu OLCER).

  python3 tools/n2-kabul.py
    son satir + rc=0:  N2_KABUL=14/14
"""

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone


_BU_DIZIN = os.path.dirname(os.path.abspath(__file__))
_REPO_KOK = os.path.dirname(_BU_DIZIN)

# Sentetik git deposu kurucusunun TEK kaynagi (FALLBACK YOK).
sys.path.insert(0, _BU_DIZIN)
from git_ortami import sentetik_git   # noqa: E402


def _yukle(ad, dosya):
    yol = os.path.join(_BU_DIZIN, dosya)
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAHIP = _yukle("n2_sahip", "ev-sahip-kapisi.py")
PARTI = _yukle("n2_parti", "parti-kapisi.py")
DEVIR = _yukle("n2_devir", "devir-kapisi.py")
KURUCU = _yukle("n2_kurucu", "mimar-kapi-kur.py")
T4 = _yukle("n2_t4", "parti-borc-kapisi.py")


# ==============================================================================
# KOL-1/2 — DUZLEM (PLANE) OLCUMU + UCUNCU SINIF (Paket ③-g §H1, K3 #10 kanunu)
# ==============================================================================
# Canli KURUCU sabitleri korunur; test senaryolarinda bu override'lar
# non-existent path'lere yonlendirilir (CANLI ~/.claude/cron/ ve
# /Users/okan/dev/pruvo-bot SILINMEZ/TASINMAZ). Yollar TANIMINDAN alinir —
# elle kopya YASAK [[taban-kirmizisi-nobetciyi-susturur]].
_ISCI_YOL_OVERRIDE = None
_GOZCU_YOL_OVERRIDE = None
_DEFTERSIZ_EV_KOKU_OVERRIDE = None


def _isci_sarmalayici_yolu():
    return (_ISCI_YOL_OVERRIDE if _ISCI_YOL_OVERRIDE is not None
            else KURUCU.ISCI_SARMALAYICI_YOLU_SABIT)


def _gozcu_yolu():
    return (_GOZCU_YOL_OVERRIDE if _GOZCU_YOL_OVERRIDE is not None
            else KURUCU.GOZCU_YOLU)


def _defteriz_ev_koku():
    return (_DEFTERSIZ_EV_KOKU_OVERRIDE if _DEFTERSIZ_EV_KOKU_OVERRIDE is not None
            else DEFTERSIZ_EV_KOKU)


def _duzlem_status():
    """`cron` ve `kardes_depo` duzlemlerinin olculup olcemedigi.

    `cron`: ISCI_SARMALAYICI yolu + GOZCU yolu IKISI de dosya olarak var.
    `kardes_depo`: DEFTERSIZ_EV_KOKU dizin olarak var.

    Dondurur:
      {"cron": {"yollar": [...], "measured": bool, "sebep": str|None},
       "kardes_depo": {..., }}
    Yollar ELLE YAZILMAZ — tanimindan alinir.
    """
    isci = _isci_sarmalayici_yolu()
    gozcu = _gozcu_yolu()
    kardes = _defteriz_ev_koku()
    isci_var = os.path.isfile(isci)
    gozcu_var = os.path.isfile(gozcu)
    kardes_var = os.path.isdir(kardes)
    cron_ok = isci_var and gozcu_var
    return {
        "cron": {
            "yollar": [isci, gozcu],
            "measured": cron_ok,
            "sebep": (None if cron_ok else
                      "cron yollari eksik (isci_var=%s, gozcu_var=%s)"
                      % (isci_var, gozcu_var)),
        },
        "kardes_depo": {
            "yollar": [kardes],
            "measured": kardes_var,
            "sebep": (None if kardes_var else
                      "kardes_depo dizini yok (yol=%s)" % kardes),
        },
    }


# KOL-2 — UCUNCU SINIF (GECTI / KUSUR / OLCULEMEDI). K3 #10 kanunu:
# ikili siniflama ucuncuyu yutar [[iki-kovali-siniflama-ucuncu-sinifi-yutar]];
# olculemeyen vaka KUSUR SAYILMAZ, GECTI DE SAYILMAZ; ayri kovaya dusup OLCULEMEDI
# etiketiyle basılır.
DURUM_GECTI = "GECTI"
DURUM_KUSUR = "KUSUR"
DURUM_OLCULEMEDI = "OLCULEMEDI"

# Vaka -> ilgili duzlem (yalniz raporlama icin; olcum _duzlem_status()'tan gelir).
_VAKA_DUZLEMI = {
    "A4": "cron",
    "B4": "cron",
    "C4": "kardes_depo",
}

SONUCLAR = []  # (ad, durum, detay)


def kayit(ad, gecti, detay, *, olculemedi=False):
    if olculemedi:
        durum = DURUM_OLCULEMEDI
    elif gecti:
        durum = DURUM_GECTI
    else:
        durum = DURUM_KUSUR
    SONUCLAR.append((ad, durum, detay))
    print("%-4s %-11s %s" % (ad, durum, detay))


def _git(kok, *args, **kw):
    # Sentetik depoda git DAIMA kanonik yardimciyla kosar (miras GIT_* baglami
    # temizlenir, cwd sabitlenir); kimlik damgalari ek_ortam ile verilir.
    ek = {
        "GIT_AUTHOR_NAME": "N2", "GIT_AUTHOR_EMAIL": "n2@pruvo.local",
        "GIT_COMMITTER_NAME": "N2", "GIT_COMMITTER_EMAIL": "n2@pruvo.local",
        "GIT_CONFIG_GLOBAL": os.path.join(kok, ".gitconfig-yok"),
        "GIT_CONFIG_SYSTEM": os.path.join(kok, ".gitconfig-yok"),
    }
    ek.update(kw.pop("ek_ortam", {}) or {})
    return sentetik_git(kok, *args, ek_ortam=ek,
                        capture_output=True, text=True)


def _dosya(kok, goreli, icerik):
    tam = os.path.join(kok, goreli)
    os.makedirs(os.path.dirname(tam), exist_ok=True)
    with open(tam, "w", encoding="utf-8") as f:
        f.write(icerik)


# ==============================================================================
# A — SAHIP TESPITI (GERCEK git commit'leri uzerinden)
# ==============================================================================
def _sentetik_depo(kok):
    """Haritayi tasiyan sentetik bir git deposu kurar; commit sha'larini doner."""
    os.makedirs(kok, exist_ok=True)
    _git(kok, "init", "-q", "-b", "main")
    # Harita TEK KAYNAK — depoya AYNEN kopyalanir (ikinci kopya degil, ayni dosya).
    os.makedirs(os.path.join(kok, "tools"), exist_ok=True)
    shutil.copyfile(os.path.join(_BU_DIZIN, "ev-serit-haritasi.tsv"),
                    os.path.join(kok, "tools", "ev-serit-haritasi.tsv"))
    shutil.copyfile(os.path.join(_BU_DIZIN, "sahiplik-haritasi.tsv"),
                    os.path.join(kok, "tools", "sahiplik-haritasi.tsv"))
    _dosya(kok, "README.md", "sentetik\n")
    _git(kok, "add", "-A")
    _git(kok, "commit", "-q", "-m", "taban")

    shalar = {}
    senaryolar = (
        ("veri", [("urunler.json", '[{"id":"x"}]\n'),
                  ("urun-kaynaklari.json", "{}\n")]),
        ("worker", [("worker/src/index.js", "// ege\n")]),
        ("jenerator", [("jenerator/uret.py", "# parametrik sari seri\n")]),
        ("cok", [("urunler.json", '[{"id":"y"}]\n'),
                 ("worker/src/index.js", "// ege2\n")]),
        ("artik", [("bilinmeyen/dizin/x.txt", "?\n")]),
    )
    for ad, dosyalar in senaryolar:
        for goreli, icerik in dosyalar:
            _dosya(kok, goreli, icerik)
        _git(kok, "add", "-A")
        _git(kok, "commit", "-q", "-m", "n2-%s" % ad)
        p = _git(kok, "rev-parse", "HEAD")
        shalar[ad] = (p.stdout or "").strip()
    return shalar


def kabul_A(calisma):
    kok = os.path.join(calisma, "depo")
    shalar = _sentetik_depo(kok)

    # A1 — veri commit'i -> MaCiT (KraL'a DEGIL)
    s = SAHIP.kirmizi_sahibi(kok, shalar["veri"])
    kayit("A1", s["SAHIP"] == "MaCiT" and s["SEBEP"] == "tek-serit",
          "veri commit %s -> %s" % (shalar["veri"][:8], SAHIP.hukum_satiri(s)))

    # A2 — worker/ -> HocA ; jenerator/ -> TeKiN
    sw = SAHIP.kirmizi_sahibi(kok, shalar["worker"])
    sj = SAHIP.kirmizi_sahibi(kok, shalar["jenerator"])
    kayit("A2", sw["SAHIP"] == "HocA" and sj["SAHIP"] == "TeKiN",
          "worker -> %s | jenerator -> %s" % (sw["SAHIP"], sj["SAHIP"]))

    # A3 — cok-seritli -> KraL VE cikti acikca yazar
    sc = SAHIP.kirmizi_sahibi(kok, shalar["cok"])
    metin = SAHIP.hukum_satiri(sc)
    kayit("A3", sc["SAHIP"] == "KraL" and "SAHIP=KraL" in metin
          and "SEBEP=cok-seritli" in metin,
          "cok-seritli commit -> %s" % metin)

    # A4 — harita TEK KAYNAK: bozulunca KAPI da GOZCU de kirmizi.
    # A4 `cron` duzlemine bagimli (GOZCU_YOLU); duzlem olculemediğinde
    # yargilanmaz (K3 #10 KOL-2).
    duzlem = _duzlem_status()
    if not duzlem["cron"]["measured"]:
        print("OLCULEMEDI: A4 (duzlem=cron, yargilanmaz) — kapi YANMAZ")
        kayit("A4", False,
              "duzlem=cron olculemedi: %s" % duzlem["cron"]["sebep"],
              olculemedi=True)
    else:
        #   (i) KAPI ayagi: haritayi bozup ayni sha'yi sor
        harita = os.path.join(kok, "tools", "ev-serit-haritasi.tsv")
        with open(harita, encoding="utf-8") as f:
            saglam = f.read()
        with open(harita, "w", encoding="utf-8") as f:
            f.write("# harita BOZULDU (mutant): tek veri satiri birakilmadi\n")
        kapi_bozuk = SAHIP.kirmizi_sahibi(kok, shalar["veri"])
        kapi_kirmizi = (kapi_bozuk["SEBEP"] == SAHIP.SEBEP_OLCULEMEDI)

        #   (ii) GOZCU ayagi: gercek gozcu.py'nin HERMETIK kopyasina kurucunun
        #        yamasini uygula, koprunun ayni fonksiyonu okudugunu KANITLA.
        gozcu_kirmizi = None
        gozcu_saglam = None
        gozcu_not = ""
        try:
            with open(_gozcu_yolu(), encoding="utf-8") as f:
                gozcu_ham = f.read()
            yamali, durum = KURUCU.gozcu_yamala(gozcu_ham)
            if durum not in ("YAMALANDI", "ZATEN TAM"):
                gozcu_not = "gozcu yamasi uygulanamadi: %s" % durum
            else:
                gyol = os.path.join(calisma, "gozcu_kopya.py")
                with open(gyol, "w", encoding="utf-8") as f:
                    f.write(yamali)
                gspec = importlib.util.spec_from_file_location("n2_gozcu_kopya", gyol)
                gmod = importlib.util.module_from_spec(gspec)
                # gozcu.py kardes modullerini (`kilit`, `nobet-kapi`) KENDI dizininden
                # import eder; hermetik kopya baska dizinde durdugu icin o dizin
                # gecici olarak sys.path'e alinir. Kopya diske BIRAKILMAZ (calisma
                # dizini kabul sonunda silinir) — Okan'in "iz birakma" kurali.
                gdizin = os.path.dirname(os.path.abspath(_gozcu_yolu()))
                sys.path.insert(0, gdizin)
                try:
                    gspec.loader.exec_module(gmod)
                finally:
                    try:
                        sys.path.remove(gdizin)
                    except ValueError:
                        pass
                kapi_yolu = os.path.join(_BU_DIZIN, "ev-sahip-kapisi.py")
                # BOZUK harita tasiyan depo koku ile:
                gozcu_kirmizi = gmod.n2_sahip_coz(
                    shalar["veri"], kapi_yolu=kapi_yolu, repo_koku=kok)
                # SAGLAM harita ile (yan eksen: kopru gercekten OKUYOR mu?)
                with open(harita, "w", encoding="utf-8") as f:
                    f.write(saglam)
                gozcu_saglam = gmod.n2_sahip_coz(
                    shalar["veri"], kapi_yolu=kapi_yolu, repo_koku=kok)
                gozcu_not = "gozcu(bozuk)=%s gozcu(saglam)=%s" % (
                    gozcu_kirmizi, gozcu_saglam)
        except Exception as e:
            gozcu_not = "gozcu kopru olculemedi: %r" % e
        finally:
            with open(harita, "w", encoding="utf-8") as f:
                f.write(saglam)

        a4 = (kapi_kirmizi
              and gozcu_kirmizi is not None and gozcu_kirmizi[1] == "olculemedi"
              and gozcu_saglam is not None and gozcu_saglam == ("MaCiT", "tek-serit"))
        kayit("A4", a4, "kapi(bozuk)=%s | %s"
              % (SAHIP.hukum_satiri(kapi_bozuk), gozcu_not))


# ==============================================================================
# B — IS-BASLATMA KAPISI
# ==============================================================================
def _defter(yol, satirlar):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    govde = ["# sentetik defter", "", "## ACIK KALEMLER", "",
             "| id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |",
             "|---|---|---|---|---|---|"]
    for kimlik, durum, isim in satirlar:
        govde.append("| %s | 2026-08-19 | X→Y | %s | %s | - |"
                     % (kimlik, isim, durum))
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(govde) + "\n")


def kabul_B(calisma):
    kok_defter = os.path.join(calisma, "defterler")
    macit = os.path.join(kok_defter, "MaCiT", "memory", "acik-kalemler.md")
    _defter(macit, [("K777", "🔧", "100-100 partisinin kirmizisi")])
    _defter(os.path.join(kok_defter, "KraL", "memory", "acik-kalemler.md"), [])

    ev_koku = "/Users/okan/dev/pruvo-hasat"

    # B1 — acik 🔧 varken yeni parti REDDEDILIR + kalem + `kabul:` basilir
    s = PARTI.parti_karari(ev_koku, "parti-surucusu", koku_root=kok_defter)
    metin = PARTI.red_metni(s) if s["HUKUM"] == "RED" else ""
    b1 = (s["HUKUM"] == "RED" and s["KOL"] == PARTI.N2B_RED_JETON
          and "K777" in metin and "kabul: " in metin
          and "parti-borc-kapisi.py --ev MaCiT" in metin)
    kayit("B1", b1, "%s | kalem+kabul basildi=%s"
          % (PARTI.hukum_satiri(s), bool(metin and "kabul: " in metin)))
    if b1:
        for satir in metin.splitlines():
            print("       | %s" % satir)

    # B2 — 🔴 NEGATIF: suren/yarim is KESILMEZ (ayni kosumda kanit)
    #   (i) mantik ekseni: parti DISI komutlar yeni-is SAYILMAZ
    suren = ["git commit -m 'parti 47/100'",
             "python3 /Users/okan/dev/pruvo-hasat/tools/duzelt.py",
             "git -C /Users/okan/dev/pruvo-hasat push",
             "python3 tools/d1-sync.py --durum"]
    kesilen = [k for k in suren if PARTI.yeni_is_mi(k)]
    #   (ii) surec ekseni: KOSAN bir is, kapi YENI baslatmayi reddederken
    #        kesilmeden BITER (gercek surec, gercek dosya).
    kanit = os.path.join(calisma, "yarim-is-bitti.txt")
    betik = os.path.join(calisma, "yarim-is.sh")
    with open(betik, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\nsleep 2\necho BITTI > '%s'\n" % kanit)
    os.chmod(betik, 0o755)
    p = subprocess.Popen([betik])
    red2 = PARTI.parti_karari(ev_koku, "parti-surucusu", koku_root=kok_defter)
    rc_yarim = p.wait(timeout=30)
    bitti = os.path.isfile(kanit)
    b2 = (not kesilen) and rc_yarim == 0 and bitti and red2["HUKUM"] == "RED"
    kayit("B2", b2,
          "yeni-is sayilan suren komut=%s | yarim is rc=%d bitti=%s | "
          "ayni anda yeni parti=%s"
          % (kesilen or "-", rc_yarim, bitti, red2["HUKUM"]))

    # B3 — kalem KAPANINCA ayni komut GECER
    _defter(macit, [("K777", "KAPANDI", "100-100 partisinin kirmizisi")])
    sonra = PARTI.parti_karari(ev_koku, "parti-surucusu", koku_root=kok_defter)
    kayit("B3", sonra["HUKUM"] == "GECER" and sonra["KOL"] == PARTI.N2B_SUREN_JETON,
          "kalem KAPANDI -> %s" % PARTI.hukum_satiri(sonra))

    # B4 — kurucudan dagitim: KURULU_EV=n/n + her ev YEDEKLI + isci.sh/gozcu capa
    b4_detay = _kabul_B4(calisma)


def _kabul_B4(calisma):
    """Kurucuyu HERMETIK fikstur evlerinde --uygula ile kosar; yedekleri olcer.

    B4 `cron` duzlemine bagimli (ISCI_SARMALAYICI + GOZCU). Duzlem
    olculemediğinde yargilanmaz (K3 #10 KOL-2).
    """
    duzlem = _duzlem_status()
    if not duzlem["cron"]["measured"]:
        print("OLCULEMEDI: B4 (duzlem=cron, yargilanmaz) — kapi YANMAZ")
        kayit("B4", False,
              "duzlem=cron olculemedi: %s" % duzlem["cron"]["sebep"],
              olculemedi=True)
        return

    kurulum = os.path.join(calisma, "kurulum")
    evler = []
    for ad, ev in (("MaCiT", "MaCiT"), ("HocA", "HocA"), ("ArTisT", "ArTisT")):
        kok = os.path.join(kurulum, ad)
        os.makedirs(os.path.join(kok, ".claude"), exist_ok=True)
        with open(os.path.join(kok, ".claude", "settings.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"hooks": {"PreToolUse": []}}, f)
        evler.append((ad, kok, ".claude/mimar-icra-kapisi.py", "enjekte"))

    # isci.sh + gozcu.py HERMETIK kopyalari (canli dosyalara DOKUNULMAZ)
    isci_kopya = os.path.join(kurulum, "isci.sh")
    shutil.copyfile(_isci_sarmalayici_yolu(), isci_kopya)
    # 🔴 20 Agu 2026: CANLI isci.sh ARTIK YAMALI (blok 20 Agu 02:25'te kuruldu).
    # Yamali kopya gelince kurucu "ZATEN TAM" der, YEDEK URETMEZ; B4'un
    # `isci_yedek` ayagi kirmizi yanar ve — asil zarar — YAMA YOLU HIC
    # OLCULMEZ: batarya kirmizi olsa da olmasa da o kol artik kapsam DISI
    # kalirdi [[batarya-kapsam-tabani-sayiyla-civilenir]] · [[bayat-kabul-testi]].
    # Cozum: hermetik kopyadan blogu SOK — yama yolu her kosumda GERCEKTEN kosar.
    with open(isci_kopya, encoding="utf-8") as f:
        _isci_ham = f.read()
    _blok_sokuldu = False
    if KURUCU.PARTI_BAS in _isci_ham and KURUCU.PARTI_SON in _isci_ham:
        _b = _isci_ham.index(KURUCU.PARTI_BAS)
        _s = _isci_ham.index(KURUCU.PARTI_SON) + len(KURUCU.PARTI_SON)
        with open(isci_kopya, "w", encoding="utf-8") as f:
            f.write(_isci_ham[:_b] + _isci_ham[_s:])
        _blok_sokuldu = True
    # ON-KOSUL: kurucu kosmadan ONCE kopya YAMASIZ olmali — degilse "yamali"
    # sonucu kurucunun degil FIKSTURUN eseridir ve olcum BOSTUR.
    with open(isci_kopya, encoding="utf-8") as f:
        _on_kosul_yamasiz = KURUCU.PARTI_BAS not in f.read()
    gozcu_kopya = os.path.join(kurulum, "gozcu.py")
    shutil.copyfile(_gozcu_yolu(), gozcu_kopya)

    eski = (KURUCU.CODEX_EVLER, KURUCU.ISCI_SARMALAYICI_YOLU_SABIT,
            KURUCU.GOZCU_YOLU, KURUCU._parti_ev_cozulur_mu)
    KURUCU.CODEX_EVLER = tuple(evler)
    KURUCU.ISCI_SARMALAYICI_YOLU_SABIT = isci_kopya
    KURUCU.GOZCU_YOLU = gozcu_kopya
    # Fikstur kokleri gercek ev dizinlerine cozulmez; ev cozumu A/B'de ayrica
    # olculuyor — burada DAGITIM/YEDEK ekseni olculuyor.
    KURUCU._parti_ev_cozulur_mu = lambda kok: (os.path.basename(kok), None)

    tampon = io.StringIO()
    rc = None
    try:
        with redirect_stdout(tampon):
            try:
                KURUCU.parti_kapisi(True)
            except SystemExit as e:
                rc = e.code
    finally:
        (KURUCU.CODEX_EVLER, KURUCU.ISCI_SARMALAYICI_YOLU_SABIT,
         KURUCU.GOZCU_YOLU, KURUCU._parti_ev_cozulur_mu) = eski

    cikti = tampon.getvalue()
    beklenen = "KURULU_EV=%d/%d" % (len(evler), len(evler))
    # her ev YEDEKLI mi + kanca gercekten kablolandi mi
    yedekli, kabloluu = 0, 0
    for ad, kok, _g, _m in evler:
        dizin = os.path.join(kok, ".claude")
        if any(a.startswith("settings.json.yedek-n2-parti-")
               for a in os.listdir(dizin)):
            yedekli += 1
        try:
            with open(os.path.join(dizin, "settings.json"), encoding="utf-8") as f:
                veri = json.load(f)
            for blok in (veri.get("hooks") or {}).get("PreToolUse") or []:
                if blok.get("matcher") != KURUCU.PARTI_MATCHER:
                    continue
                if any("parti-kapisi.py" in (h.get("command") or "")
                       and "--kanca" in (h.get("command") or "")
                       for h in blok.get("hooks") or []):
                    kabloluu += 1
        except Exception:
            pass
    isci_yamali = KURUCU.PARTI_BAS in open(isci_kopya, encoding="utf-8").read()
    gozcu_yamali = KURUCU.GOZCU_BAS in open(gozcu_kopya, encoding="utf-8").read()
    isci_yedek = os.path.isfile(isci_kopya) and any(
        a.startswith("isci.sh.yedek-n2-parti-")
        for a in os.listdir(os.path.dirname(isci_kopya)))
    idempotent = KURUCU.gozcu_yamala(
        open(gozcu_kopya, encoding="utf-8").read())[1] == "ZATEN TAM"

    b4 = (rc == 0 and beklenen in cikti and yedekli == len(evler)
          and kabloluu == len(evler) and isci_yamali and gozcu_yamali
          and isci_yedek and idempotent and _on_kosul_yamasiz)
    kayit("B4", b4,
          "%s | rc=%s yedekli=%d/%d kablolu=%d/%d isci.sh=%s gozcu.py=%s "
          "isci_yedek=%s idempotent=%s | on-kosul: kopya yamasizdi=%s "
          "(blok sokuldu=%s)"
          % (beklenen, rc, yedekli, len(evler), kabloluu, len(evler),
             isci_yamali, gozcu_yamali, isci_yedek, idempotent,
             _on_kosul_yamasiz, _blok_sokuldu))
    for satir in cikti.splitlines():
        if satir.startswith(("YUZEY", "KURULU_EV", "ISCI_SH", "GOZCU",
                             "KAPSAM_DISI_EV", "TAM OLMAYAN")):
            print("       | %s" % satir)
    return b4


# ==============================================================================
# C — 4 SAATLIK DEVIR
# ==============================================================================
# 🔴 K229 — C fiksturunde defteri BILEREK acilmayan ev (canli duzlemin taklidi:
# 20 Agu 2026'da bes evden dordunde `acik-kalemler.md` HIC YOKTU).
DEFTERSIZ_EV = "HocA"
# Bu evin depo koku — N2B kapisinin ev cozumu YOL uzerinden calisir.
DEFTERSIZ_EV_KOKU = "/Users/okan/dev/pruvo-bot"


def kabul_C(calisma):
    simdi = datetime(2026, 8, 19, 20, 0, 0, tzinfo=timezone.utc)

    def kur(kok, yas_dk):
        # Izlenen evlere bos defter — AMA BIRI HARIC.
        # 🔴 K229: eski fikstur izlenen HER eve defter aciyordu ve gerekcesi
        # "defteri olmayan ev sayaci kirletir" idi. Bu, CANLI duzlemle CELISIR:
        # 20 Agu 2026'da bes evden DORDUNDE defter dosyasi HIC YOKTU. Fikstur o
        # hali disarida birakinca `DEFTER-YOK` bir daha OLCULMEZ hale geliyor
        # ve kapi bu vakayi kapsam DISI birakiyordu
        # [[batarya-kapsam-tabani-sayiyla-civilenir]]. Artik fikstur UCUNCU
        # KOVAYI DA TASIR: HocA'nin defteri BILEREK acilmaz.
        for ev in set(["KraL", "MaCiT"] + DEVIR.izlenen_evler()):
            os.makedirs(os.path.join(kok, ev, "memory"), exist_ok=True)
            with open(DEVIR.posta_yolu(ev, kok), "w", encoding="utf-8") as f:
                f.write("# sentetik posta kutusu\n")
            if ev == DEFTERSIZ_EV:
                continue
            _defter(DEVIR.defter_yolu(ev, kok), [])
        _defter(DEVIR.defter_yolu("MaCiT", kok),
                [("K777", "🔧", "100-100 partisinin kirmizisi")])
        _defter(DEVIR.defter_yolu("KraL", kok), [])
        kalemler, _o, _h = T4.acik_kalem_listesi(DEVIR.defter_yolu("MaCiT", kok))
        DEVIR._json_yaz(DEVIR.durum_yolu(kok), {
            "MaCiT/K777": {"imza": DEVIR._imza(kalemler[0]),
                           "damga": DEVIR._iso(simdi - timedelta(minutes=yas_dk))}})
        DEVIR._json_yaz(DEVIR.ihlal_yolu(kok), {})

    # C1 — 4 saat (300 dk) -> devir + DEVREDILDI + ihlal +1
    kok = os.path.join(calisma, "devir-300")
    kur(kok, 300)
    s = DEVIR.devret(simdi, koku_root=kok, uygula=True)
    with open(DEVIR.posta_yolu("KraL", kok), encoding="utf-8") as f:
        hedef_posta = f.read()
    with open(DEVIR.posta_yolu("MaCiT", kok), encoding="utf-8") as f:
        kaynak_posta = f.read()
    ihlal = DEVIR._json_oku(DEVIR.ihlal_yolu(kok), {})
    c1 = (len(s["devredilen"]) == 1
          and "DEVREDILDI: K777 -> KraL" in hedef_posta
          and "T5-IZ" in kaynak_posta
          and (ihlal.get("MaCiT") or {}).get("ihlal") == 1)
    kayit("C1", c1, "%s | kutu='%s' | ihlal=%s"
          % (DEVIR.hukum_satiri(s),
             hedef_posta.strip().splitlines()[-1],
             json.dumps(ihlal.get("MaCiT") or {}, ensure_ascii=False)))

    # C3 — tek sahip: iki defterde birden ACIK degil
    kaynak_acik = _acik_mi(DEVIR.defter_yolu("MaCiT", kok), "K777")
    hedef_acik = _acik_mi(DEVIR.defter_yolu("KraL", kok), "K777")
    kayit("C3", (not kaynak_acik) and hedef_acik,
          "kaynakta acik=%s hedefte acik=%s (beklenen False/True)"
          % (kaynak_acik, hedef_acik))

    # C2 — 4 saat DOLMADAN devir YOK (239 dk) + hicbir sey yazilmadi
    kok2 = os.path.join(calisma, "devir-239")
    kur(kok2, 239)
    once = _damgalar(kok2)
    s2 = DEVIR.devret(simdi, koku_root=kok2, uygula=True)
    with open(DEVIR.posta_yolu("KraL", kok2), encoding="utf-8") as f:
        posta2 = f.read()
    sonra = _damgalar(kok2)
    ihlal2 = DEVIR._json_oku(DEVIR.ihlal_yolu(kok2), {})
    c2 = (len(s2["devredilen"]) == 0 and "DEVREDILDI" not in posta2
          and _acik_mi(DEVIR.defter_yolu("MaCiT", kok2), "K777")
          and not _acik_mi(DEVIR.defter_yolu("KraL", kok2), "K777")
          and not ihlal2 and once == sonra)
    kayit("C2", c2, "239 dk -> %s | defter/posta imzalari degismedi=%s | ihlal=%s"
          % (DEVIR.hukum_satiri(s2), once == sonra,
             json.dumps(ihlal2, ensure_ascii=False)))

    # C4 — 🔴 K229 UCUNCU KOVA: defteri HIC OLMAYAN ev fiksturde TASINIR ve
    #      N2B kapisi onu KENDI jetonuyla ayirir (ne RED, ne sessiz gecis).
    #      C4 `kardes_depo` duzlemine bagimli (DEFTERSIZ_EV_KOKU); duzlem
    #      olculemediğinde yargilanmaz (K3 #10 KOL-2).
    duzlem_c = _duzlem_status()
    if not duzlem_c["kardes_depo"]["measured"]:
        print("OLCULEMEDI: C4 (duzlem=kardes_depo, yargilanmaz) — kapi YANMAZ")
        kayit("C4", False,
              "duzlem=kardes_depo olculemedi: %s" % duzlem_c["kardes_depo"]["sebep"],
              olculemedi=True)
    else:
        #        Dort ayak (hepsi AYNI kosumda):
        #        (a) ON-KOSUL: defter dosyasi GERCEKTEN yok — yoksa "DEFTER-YOK"
        #            sonucu kapinin degil FIKSTURUN eseri olurdu.
        #        (b) devir katmani bu evi OLCULEMEDI sayar ve SAYAR (gizlemez),
        #            devir sonucunu BOZMAZ.
        #        (c) N2B kapisi: MUAF OLMAYAN etiketle GECER + KOL=N2B-DEFTER-YOK,
        #            ve jeton N2B-OLCULEMEDI'den FARKLI (ucuncu kova ayakta).
        #        (d) NEGATIF: defteri OLAN + acik kalemli ev HALA RED (davranis
        #            degismedi) — kova ayrimi digerlerini yutmadi.
        defter_yolu_yok = DEVIR.defter_yolu(DEFTERSIZ_EV, kok2)
        c4_a = not os.path.exists(defter_yolu_yok)
        sinif4 = DEVIR.siniflandir(simdi, koku_root=kok2)
        defter_yok_kalemleri = [k for k in sinif4["kalemler"]
                                if k["ev"] == DEFTERSIZ_EV
                                and k["kol"] == DEVIR.N2C_OLCULEMEDI_JETON]
        c4_b = (len(defter_yok_kalemleri) == 1 and s2["olculemedi"] >= 1)
        n2b = PARTI.parti_karari(_defteriz_ev_koku(), "d2-2", koku_root=kok2)
        c4_c = (n2b["HUKUM"] == "GECER"
                and n2b["KOL"] == PARTI.N2B_DEFTER_YOK_JETON
                and n2b["KOL"] != PARTI.N2B_OLCULEMEDI_JETON
                and bool(n2b["SEBEP"]))
        n2b_neg = PARTI.parti_karari("/Users/okan/dev/pruvo-hasat", "d2-2",
                                     koku_root=kok2)
        c4_d = (n2b_neg["HUKUM"] == "RED"
                and n2b_neg["KOL"] == PARTI.N2B_RED_JETON)
        kayit("C4", c4_a and c4_b and c4_c and c4_d,
              "on-kosul defter YOK=%s (%s) | devir: %s kalemi OLCULEMEDI=%d "
              "(N2C olculemedi=%d) | N2B: %s | NEGATIF (defterli+kalemli ev): %s"
              % (c4_a, defter_yolu_yok, DEFTERSIZ_EV, len(defter_yok_kalemleri),
                 s2["olculemedi"], PARTI.hukum_satiri(n2b),
                 PARTI.hukum_satiri(n2b_neg)))
        print("       | SEBEP: %s" % (n2b["SEBEP"] or "(BOS — SESSIZ GECIS)"))


def _acik_mi(yol, kimlik):
    kalemler, okundu, _h = T4.acik_kalem_listesi(yol)
    return bool(okundu) and any(k["kimlik"] == kimlik for k in kalemler)


def _damgalar(kok):
    """Defter + posta dosyalarinin icerik imzalari (YAZILDI MI olcumu)."""
    out = {}
    for ev in ("KraL", "MaCiT"):
        for yol in (DEVIR.defter_yolu(ev, kok), DEVIR.posta_yolu(ev, kok)):
            try:
                with open(yol, "rb") as f:
                    out[yol] = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                out[yol] = None
    return out


# ==============================================================================
# Z — MUTANTLAR + IZ BIRAKMAMA
# ==============================================================================
def _kendini_test_kos(betik):
    p = subprocess.run([sys.executable, os.path.join(_BU_DIZIN, betik),
                        "--kendini-test"], capture_output=True, text=True)
    son = [s for s in (p.stdout or "").splitlines() if s.strip()]
    return p.returncode, (son[-1] if son else "")


def kabul_Z(calisma, once_imza):
    # Z1 — her mekanizmada mutant + hedef-kol atfi
    beklenen = {
        "ev-sahip-kapisi.py": "MUTANT=5/5 HEDEF_KOL_ATFI=5/5 KONTROL=3/3",
        # 20 Agu: K6 (T4 yuklenemez -> KIRMIZI + SEBEP) + K7 (enjekte kopya
        # uctan uca) eklendi -> KONTROL 5 -> 7 [[kapinin-menzili-cagri-yeridir]]
        # 20 Agu (N4A): cagri-yeri kolu M6 (tarayici korlesir) + M7 (regresyon,
        # startswith-only) + K8 (muafiyet GERCEK cagri yerlerine bagli)
        # -> MUTANT 5 -> 7, KONTROL 7 -> 8.
        # 20 Agu (K229): UCUNCU KOVA — M8 (kol bozulur) + M9 (kol OLCULEMEDI ile
        # BIRLESTIRILIR) -> MUTANT 7 -> 9; K9 (defteri yok ev GECER + ayri jeton)
        # + K10 (defterli evde davranis degismedi, bos defter HALA RED)
        # -> KONTROL 8 -> 10. Sayilar BUYUDU: kapsam kaybi oranla gizlenemez.
        # 🔴 K229 dalinda bu mutantlar M6/M7 idi; N4A ayni numaralari ALDIGI icin
        # tazeleme sirasinda M8/M9'a TASINDI [[ad-iki-rolde-mutanti-golgeler]].
        "parti-kapisi.py":    "MUTANT=9/9 HEDEF_KOL_ATFI=9/9 KONTROL=10/10",
        "devir-kapisi.py":    "MUTANT=5/5 HEDEF_KOL_ATFI=5/5 KONTROL=4/4",
    }
    satirlar, hepsi = [], True
    for betik, bek in beklenen.items():
        rc, son = _kendini_test_kos(betik)
        ok = (rc == 0 and son == bek)
        hepsi = hepsi and ok
        satirlar.append("%s rc=%d %s" % (betik, rc, son or "(cikti yok)"))
    kayit("Z1", hepsi, " · ".join(satirlar))

    # Z2 — urunler.json DEGISMEDI + baska evin defterine ELLE satir YAZILMADI
    sonra_imza = _canli_imza()
    degisen = [y for y in once_imza if once_imza[y] != sonra_imza.get(y)]
    kayit("Z2", not degisen,
          "canli urunler.json + 5 evin acik-kalemler.md + posta kutulari: "
          "degisen=%s (olculen dosya=%d)" % (degisen or "-", len(once_imza)))


def _canli_imza():
    """CANLI (fikstur olmayan) dosyalarin imzalari — kabul kosumu bunlara
    DOKUNMAMALIDIR. Var olmayan dosya None ile kaydedilir (sonradan
    OLUSTURULMASI da bir degisikliktir)."""
    yollar = [os.path.join(_REPO_KOK, "urunler.json")]
    for ev in sorted(T4.EV_BILINEN):
        dizin = T4.EV_DIZIN.get(ev)
        if not dizin:
            continue
        yollar.append(os.path.join(dizin, "memory", "acik-kalemler.md"))
        yollar.append(os.path.join(dizin, "memory", "mimar-posta-kutusu.md"))
        yollar.append(os.path.join(dizin, "memory", DEVIR.DURUM_DOSYA_ADI))
        yollar.append(os.path.join(dizin, "memory", DEVIR.IHLAL_DOSYA_ADI))
    out = {}
    for y in sorted(set(yollar)):
        try:
            with open(y, "rb") as f:
                out[y] = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            out[y] = None
    return out


# ==============================================================================
# KENDINI-TEST ALTYAPISI (K3 #10c — env bypass kaldirildi; mutasyon_kopya ile)
# ==============================================================================
# Canli _duzlem_status()'un govdesinde ortam degiskeni kontrolu YOKTUR — K3 #10c
# ile ONCEDEN beri yok; kendini-test artik mutasyonu CANLI dosyaya YAZMAZ.
# Bypass yuzeyi olmasin diye canli govde env bakmaz, test alt surecte KOPYA
# UZERINDE mutasyon uygular (`mutasyon_kopya.mutant_metni`).


# ==============================================================================
# MAIN
# ==============================================================================
def _kabul_durdur_ve_ozet(gecen, yargilanan, olcumeyen, olcum_duzlem_str,
                          kusurlu, her_iki_yok):
    """KOL-3 + KOL-4: cikti + rc hüküm.

    KOL-3: `N2_KABUL=<gecen>/<yargilanan> OLCULEMEYEN_VAKA=<n> OLCULEMEYEN_DUZLEM=<ad|->`
    KOL-4: yargilanan tumu gecti → rc=0 (OLCUME>0 olsa bile)
           yargilanan dustu → rc=1
           IKI duzlem de olculmedi → rc=2 OLCULEMEDI.
    """
    if kusurlu:
        print("KUSURLU: %s" % ", ".join(kusurlu))
    if her_iki_yok:
        rc = 2
    elif kusurlu:
        rc = 1
    else:
        rc = 0
    print("N2_KABUL=%d/%d OLCULEMEYEN_VAKA=%d OLCULEMEYEN_DUZLEM=%s"
          % (gecen, yargilanan, len(olcumeyen), olcum_duzlem_str))
    return rc


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="N2 'kirleten onarir' kabul betigi (K3 #10).")
    ap.add_argument("--hal-b", action="store_true",
                    help="cron duzlemi olculemedi san (HAL B)")
    ap.add_argument("--iki-duzlem-yok", action="store_true",
                    help="her iki duzlem de olculemedi san (rc=2)")
    ap.add_argument("--msabit-senaryo", action="store_true",
                    help="M-SABIT provokasyonu: ISCI gercek, GOZCU YOK")
    ap.add_argument("--kendini-test", action="store_true",
                    help="M5 + M-SABIT + KONTROL bataryasini kos (subprocess)")
    args = ap.parse_args()

    if args.kendini_test:
        return kendini_test()

    # CLI senaryolari: canli ~/.claude/cron/ ve /Users/okan/dev/pruvo-bot
    # SILINMEZ; override'lar non-existent path'lere yonlendirilir.
    global _ISCI_YOL_OVERRIDE, _GOZCU_YOL_OVERRIDE, _DEFTERSIZ_EV_KOKU_OVERRIDE
    if args.hal_b:
        _ISCI_YOL_OVERRIDE = "/tmp/n2kabul-hal-b-isci-nonexistent-%d" % os.getpid()
        _GOZCU_YOL_OVERRIDE = "/tmp/n2kabul-hal-b-gozcu-nonexistent-%d" % os.getpid()
    if args.iki_duzlem_yok:
        if not args.hal_b:
            _ISCI_YOL_OVERRIDE = "/tmp/n2kabul-hal-c-isci-nonexistent-%d" % os.getpid()
            _GOZCU_YOL_OVERRIDE = "/tmp/n2kabul-hal-c-gozcu-nonexistent-%d" % os.getpid()
        _DEFTERSIZ_EV_KOKU_OVERRIDE = "/tmp/n2kabul-hal-c-kardes-nonexistent-%d" % os.getpid()
    if args.msabit_senaryo:
        # M-SABIT provokasyonu: ISCI gercek yola, GOZCU nonexistent'e yonlendirilir.
        _ISCI_YOL_OVERRIDE = KURUCU.ISCI_SARMALAYICI_YOLU_SABIT
        _GOZCU_YOL_OVERRIDE = (
            "/tmp/n2kabul-msabit-gozcu-nonexistent-%d.py" % os.getpid())

    # Yol override baski: kapinin NEREYE baktigini CIKIDA goster — override
    # etkin degilken bu satir YOK (HAL A'da kapi kendi kanonik yolunu kullanir).
    if _ISCI_YOL_OVERRIDE is not None or _GOZCU_YOL_OVERRIDE is not None \
        or _DEFTERSIZ_EV_KOKU_OVERRIDE is not None:
        print("--- YONLENDIRME ---")
        if _ISCI_YOL_OVERRIDE is not None:
            print("ISCI_YOL_OVERRIDE: %s" % _ISCI_YOL_OVERRIDE)
        if _GOZCU_YOL_OVERRIDE is not None:
            print("GOZCU_YOL_OVERRIDE: %s" % _GOZCU_YOL_OVERRIDE)
        if _DEFTERSIZ_EV_KOKU_OVERRIDE is not None:
            print("DEFTERSIZ_EV_KOKU_OVERRIDE: %s" % _DEFTERSIZ_EV_KOKU_OVERRIDE)
        print("")

    print("N2 KABUL — 'kirleten onarir' (spec §2, Okan onayli doktrin)")
    print("depo koku: %s" % _REPO_KOK)
    print("")
    once = _canli_imza()
    calisma = tempfile.mkdtemp(prefix="n2-kabul-")
    try:
        print("--- A: SAHIP TESPITI ---")
        kabul_A(calisma)
        print("")
        print("--- B: IS-BASLATMA KAPISI ---")
        kabul_B(calisma)
        print("")
        print("--- C: 4 SAATLIK DEVIR ---")
        kabul_C(calisma)
        print("")
        print("--- Z: MUTANT + IZ ---")
        kabul_Z(calisma, once)
    finally:
        # Ureten temizler (Okan disk kurali).
        shutil.rmtree(calisma, ignore_errors=True)
    print("")

    gecen = sum(1 for _a, d, _d in SONUCLAR if d == DURUM_GECTI)
    kusurlu = [a for a, d, _d in SONUCLAR if d == DURUM_KUSUR]
    olcumeyen = [a for a, d, _d in SONUCLAR if d == DURUM_OLCULEMEDI]
    yargilanan = sum(1 for _a, d, _det in SONUCLAR
                     if d in (DURUM_GECTI, DURUM_KUSUR))

    # OLCULEMEYEN_DUZLEM raporu (virgulle sirali)
    olcum_duzlemler = set()
    for ad in olcumeyen:
        d = _VAKA_DUZLEMI.get(ad)
        if d:
            olcum_duzlemler.add(d)
    olcum_duzlem_str = ",".join(sorted(olcum_duzlemler)) if olcum_duzlemler else "-"

    if olcumeyen:
        print("OLCULEMEYEN VAKALAR (yargilanmaz) — kapi YANMAZ:")
        for a in olcumeyen:
            d = _VAKA_DUZLEMI.get(a, "?")
            print("  %s  (duzlem=%s)" % (a, d))

    duzlem = _duzlem_status()
    her_iki_yok = (not duzlem["cron"]["measured"]
                   and not duzlem["kardes_depo"]["measured"])

    return _kabul_durdur_ve_ozet(gecen, yargilanan, olcumeyen, olcum_duzlem_str,
                                kusurlu, her_iki_yok)


# ==============================================================================
# KENDINI-TEST (M5 + M-SABIT + KONTROL) — mutasyon_kopya ile
# ==============================================================================
def kendini_test():
    """K3 #10c §2 mutant + kontrol bataryasi (mutasyon_kopya ile).

    Canli dosyaya MUTASYON YAZILMAZ; `mutasyon_kopya` ile gecici bir `tools/`
    kopyasinda mutasyon uygulanir ve alt surecte kosulur. rc + vaka bazinda
    olculur. CANLI govde env anahtari UZERINDEN mutant rebind ETMEZ (K3 #10c).

      M5       : _duzlem_status()'in her iki duzlemini False yapar
                 (cron_ok tersi + kardes_depo.measured=False). HAL A'da 3
                 vaka OLCUME → her_iki_yok → rc=2.
      M-SABIT  : cron olcumunden GOZCU kontrolunu dusurur
                 (isci_var and gozcu_var → isci_var). --msabit-senaryo ile
                 ISCI=gercek + GOZCU=YOK provokasyonunda A4 KUSUR.
      KONTROL  : mutasyonsuz kopya HAL A senaryosunda 14/14 YESIL.
      CAPA_FAIL_CLOSED : etkisiz donusum (no-op) CapaHatasi yükseltmeli.
    """
    import mutasyon_kopya as mk

    print("N2 KABUL KENDINI-TEST (K3 #10c §2 — mutasyon_kopya ile)")
    print("")

    adimlar = []

    gecici = tempfile.mkdtemp(prefix="n2-kabul-kendini-")
    artik = []
    try:
        kok = mk.kopya_kok(gecici)
        kopya_dosya = os.path.join(kok, "tools", "n2-kabul.py")

        # Kopya metnini + modulunu BIR KEZ yukle (ciftler KAYNAGI buradan turer).
        with open(kopya_dosya, encoding="utf-8") as f:
            orjinal_metin = f.read()
        kopya_modul = mk.modul_yukle(kopya_dosya, "n2_kabul_kopya")

        # ---- M5 (H1 revert) ----
        print("M5 mutant — duzlem hükmünü tersine çeviren mutasyon")
        try:
            m5_metin = mk.mutant_metni(kopya_modul, orjinal_metin, [
                # _duzlem_status: cron_ok formulu tersine
                ("_duzlem_status",
                 r"cron_ok = isci_var and gozcu_var",
                 lambda s: s.replace("isci_var and gozcu_var",
                                     "not (isci_var and gozcu_var)")),
                # _duzlem_status: kardes_depo.measured kati False
                ("_duzlem_status",
                 r'"measured": kardes_var,',
                 lambda s: s.replace('"measured": kardes_var,',
                                     '"measured": False,')),
            ])
        except mk.CapaHatasi as e:
            m5_metin = None
            m5_capa = str(e)
        if m5_metin is not None:
            with open(kopya_dosya, "w", encoding="utf-8") as f:
                f.write(m5_metin)
            proc_m5 = subprocess.run(
                [sys.executable, kopya_dosya],
                capture_output=True, text=True)
            out_m5 = (proc_m5.stdout or "") + (proc_m5.stderr or "")
            m5_olcume3 = "OLCULEMEYEN_VAKA=3" in out_m5
            m5_olcume_d = "OLCULEMEYEN_DUZLEM=cron,kardes_depo" in out_m5
            m5_halA_kirik = "N2_KABUL=14/14" not in out_m5
            m5_ok = (m5_olcume3 and m5_olcume_d and m5_halA_kirik
                     and proc_m5.returncode in (0, 2))
            m5_durum = ("OLDURULDU (rc=%d, dusen=A4,B4,C4)"
                        % proc_m5.returncode if m5_ok else
                        "KACTI (rc=%d, OLCUME3=%s, OLMEYEN_DUZLEM=%s, 14kirildi=%s)"
                        % (proc_m5.returncode, m5_olcume3, m5_olcume_d, m5_halA_kirik))
            son_m5 = ([s for s in out_m5.splitlines() if s.strip()][-1]
                      if out_m5.strip() else "")
        else:
            proc_m5 = None
            m5_ok = False
            m5_durum = "CapaHatasi: %s" % m5_capa
            son_m5 = ""
        print("  rc=%s | %s" % (getattr(proc_m5, "returncode", "?"), m5_durum))
        if son_m5:
            print("  son: %s" % son_m5)
        print("")
        adimlar.append(("M5", m5_ok))

        # ---- KOPYA SIFIRLAMA ----
        with open(kopya_dosya, "w", encoding="utf-8") as f:
            f.write(orjinal_metin)
        kopya_modul = mk.modul_yukle(kopya_dosya, "n2_kabul_kopya")

        # ---- M-SABIT (GOZCU kontrolu dusurulmus) ----
        print("M-SABIT mutant — cron olcumunden GOZCU kontrolu dusurulur")
        print("  senaryo: --msabit-senaryo (ISCI=gercek, GOZCU=YOK)")
        print("  BUG formula sadece ISCI'a bakar → cron.measured=True → A4 proceed → kirmizi")
        try:
            ms_metin = mk.mutant_metni(kopya_modul, orjinal_metin, [
                ("_duzlem_status",
                 r"cron_ok = isci_var and gozcu_var",
                 lambda s: s.replace("isci_var and gozcu_var", "isci_var")),
            ])
        except mk.CapaHatasi as e:
            ms_metin = None
            ms_capa = str(e)
        if ms_metin is not None:
            with open(kopya_dosya, "w", encoding="utf-8") as f:
                f.write(ms_metin)
            proc_ms = subprocess.run(
                [sys.executable, kopya_dosya, "--msabit-senaryo"],
                capture_output=True, text=True)
            out_ms = (proc_ms.stdout or "") + (proc_ms.stderr or "")
            a4_dustu = "A4   KUSUR" in out_ms or "KUSURLU: A4" in out_ms
            b4_dustu = "B4   KUSUR" in out_ms or "KUSURLU: B4" in out_ms
            dusen = []
            if a4_dustu: dusen.append("A4")
            if b4_dustu: dusen.append("B4")
            ms_ok = (proc_ms.returncode != 0 and bool(dusen))
            ms_durum = ("OLDURULDU (rc=%d, dusen=%s)"
                        % (proc_ms.returncode, ",".join(dusen))
                        if ms_ok else
                        "KACTI (rc=%d, a4=%s, b4=%s)"
                        % (proc_ms.returncode, a4_dustu, b4_dustu))
            son_ms = ([s for s in out_ms.splitlines() if s.strip()][-1]
                      if out_ms.strip() else "")
        else:
            proc_ms = None
            ms_ok = False
            ms_durum = "CapaHatasi: %s" % ms_capa
            son_ms = ""
        print("  rc=%s | %s" % (getattr(proc_ms, "returncode", "?"), ms_durum))
        if son_ms:
            print("  son: %s" % son_ms)
        print("")
        adimlar.append(("M-SABIT", ms_ok))

        # ---- KOPYA SIFIRLAMA ----
        with open(kopya_dosya, "w", encoding="utf-8") as f:
            f.write(orjinal_metin)

        # ---- KONTROL ----
        print("KONTROL — mutasyonsuz kopya HAL A senaryosunda 14/14 beklenir")
        proc_k = subprocess.run(
            [sys.executable, kopya_dosya],
            capture_output=True, text=True)
        out_k = (proc_k.stdout or "") + (proc_k.stderr or "")
        kontrol_14 = "N2_KABUL=14/14" in out_k
        kontrol_kusur = "KUSURLU:" not in out_k
        kontrol_ok = (proc_k.returncode == 0 and kontrol_14 and kontrol_kusur)
        adimlar.append(("KONTROL", kontrol_ok))
        print("  rc=%d | N2_KABUL=14/14=%s | KUSURLU yok=%s"
              % (proc_k.returncode, kontrol_14, kontrol_kusur))
        print("")

        # ---- CAPA FAIL-CLOSED ----
        # mk.mutant_metni'nin 4. kolu: etkisiz donusum (no-op) CapaHatasi
        # yükseltmeli; yoksa mutant sessizce no-op olurdu (bayat capanin yuzuyu).
        print("CAPA_FAIL_CLOSED — etkisiz donusum CapaHatasi yükseltmeli")
        try:
            mk.mutant_metni(kopya_modul, orjinal_metin, [
                ("_duzlem_status",
                 r"cron_ok = isci_var and gozcu_var",
                 lambda s: s),  # no-op
            ])
            capa_ok = False
            capa_durum = "DUSTU (CapaHatasi BEKLENIYORDU, gelmedi)"
        except mk.CapaHatasi:
            capa_ok = True
            capa_durum = "GECTI"
        print("  %s" % capa_durum)
        print("")

        # Canli agac ARTIK kontrolu: uretim temizlendi mi?
        artik = mk.artik_yedekler()

    finally:
        # Ureten temizler (Okan disk kurali).
        shutil.rmtree(gecici, ignore_errors=True)

    mutant_basarili = sum(1 for ad, b in adimlar if ad in ("M5", "M-SABIT") and b)
    kontrol_basarili = 1 if next((b for ad, b in adimlar if ad == "KONTROL"), False) else 0

    print("MUTANT=%d/2 HEDEF_KOL_ATFI=%d/2 KONTROL=%d/1 CAPA_FAIL_CLOSED=%s"
          % (mutant_basarili, mutant_basarili, kontrol_basarili,
             "GECTI" if capa_ok else "DUSTU"))
    if artik:
        print("UYARI: artik yedek kaldi=%s" % artik)

    if mutant_basarili == 2 and kontrol_basarili == 1 and capa_ok and not artik:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
