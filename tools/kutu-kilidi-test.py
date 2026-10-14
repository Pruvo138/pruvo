#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kutu-kilidi-test.py — KUTU KILIDI KALKTI kabul + mutant bataryasi (BaBa 8 Eki).

OLCULEN VAKA (8 Eki 00:5x): ortak kutu 544 > 500 -> `defter-kota-kapisi` KUTU_ASILDI rc=1
-> KraL'in ilgisiz dal commit'i DURDU; filonun her evi ayni kilide acikti. Rotasyon 5
blok tasidi, 524'te kaldi (kalan bloklar KORUMALI/genc) -> elle sikistirma gerekti.

HUKUM (olculen kollar):
  (a) 600 satirlik sahte kutu -> kapi rotasyonu YALNIZ KURU kosar (14 Eki), kutu bayt-ESIT,
      plan `KUTU_ROTASYON_KURU sonra_satir=<n>` basilir, KUTU kolu rc 0.
  (b) tum bloklar KORUMALI 600 satir -> `🟠 KUTU_TEFTIS` RAPOR, rc yine 0.
  (c) 49 saatlik KORUMALI blok tasinir, 47 saatlik tasinmaz (uc koruma sinifinda).
  (d) `Kapatan` satirinda `✔︎ KAPANDI` olan blok tasinir (yalniz govdede gecmesi YETMEZ).
  (e) tarihsiz KORUMALI blok tasinmaz (fail-safe = TASIMA).
  (f) UZUN_BLOK raporu sinirda: mimar 6/7, BaBa ⚖️ 10/11.
  (g) rotasyon kilidi baskasindayken commit yine gecer, `KUTU_TEFTIS=OLCULEMEDI`.
  (h) KANCA KOSUMU (pre-commit'in cagirdigi tam `main`): tavan asilmis sahte kutu bayt-ESIT
      kalir, `KUTU_ROTASYON_KURU` basilir (BaBa 14 Eki 10:4x: dal kodu + yazan kip = RED).
MUTANTLAR (izole kopyada; her biri HEDEF vakada KIRMIZI olmali, SURVIVOR 0):
  M1 KUTU rc'yi 1'e geri ceken · M2 48 saat kuralini silen · M3 KAPANDI kuralini silen ·
  M4 kancaya YAZAN kipi geri koyan (`--kuru` silinir) -> hedef (h) KIRMIZI.

IZOLASYON: her kosum `tempfile.mkdtemp` altinda <kok>/tools/ kopyasi kurar (kapi + taban +
serbest_cagrilar + kutu-arsivle). Kutu/arsiv/kilit o dizindedir; gercek kutuya, arsive ya
da beyan dosyasina dokunulmaz (kopyada `yedekle.py` YOK -> beyan kolu yazmaz). Silme YALNIZ
mkdtemp kokunde yapilir.

Kullanim: python3 tools/kutu-kilidi-test.py      (son satir: TEST=<g>/<n> MUTANT=<k>/<m>)
"""
import fcntl
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOPYA = ("defter-kota-kapisi.py", "defter-kota-taban.py", "serbest_cagrilar.py",
         "kutu-arsivle.py")
SIMDI = "2026-10-08 12:00"
# Dolgu (2026-10-08 11:00) bu anda 49 sa yasli: en az yas tabani (24 sa) onu TUTMAZ, yani
# kuru plan kutuyu tavan altina INDIREBILIR — kutunun yine de bayt-ESIT kalmasi tam olarak
# "kanca yazmadi" demektir (plan bos oldugu icin degismemis olamaz).
SIMDI_YASLI = "2026-10-10 12:00"
KUTU_ADI = "sahte-kutu.md"           # gercek kutunun adi DEGIL (beyan anahtari eslesmez)
TAVAN = 500                          # kutu-arsivle.py::VARSAYILAN_TAVAN (degisirse b3 KIRMIZI)
KAPANDI = "✔︎ KAPANDI"
BEKLEYEN = "ARŞİVLENEBİLİRİM"

FM = ("---\n"
      "name: sahte-kutu\n"
      "description: KABUL TESTI FIKSTURU — gercek kutu DEGIL; gercek kisisel veri YOK\n"
      "---\n"
      "\n")

MUTANTLAR = (
    ("M1 KUTU-RC-GERI", "defter-kota-kapisi.py",
     (("    KUTU_ASILDI: 0,\n", "    KUTU_ASILDI: 1,\n"),
      ("    KUTU_TEFTIS: 0,\n", "    KUTU_TEFTIS: 1,\n")), "b"),
    ("M2 48-SAAT-SIL", "kutu-arsivle.py",
     (("    if simdi_dk - blok_dk > KORUMA_OMRU_SAAT * 60:\n", "    if False:\n"),), "c"),
    ("M3 KAPANDI-SIL", "kutu-arsivle.py",
     (("        if KAPATAN_JETON in satirlar[x] and KAPANDI_ISARETI_RE.search(satirlar[x]):\n",
       "        if False:\n"),), "d"),
    ("M4 KANCA-YAZAN-KIP", "defter-kota-kapisi.py",
     (('    komut.append("--kuru")      # \U0001f534 dal kodu + yazan kip = RED (BaBa 14 Eki 10:4x)\n',
       "    pass  # MUTANT: yazan kip geri\n"),), "h"),
)


# ------------------------------------------------------------------ yardimcilar
def blok(baslik, govde=3, kuyruk=None, ek=None):
    s = baslik + "\n"
    k = 0
    while k < govde:
        s += "- sentetik satir %d (%s)\n" % (k, baslik[3:19])
        k += 1
    if ek:
        s += ek + "\n"
    if kuyruk:
        s += kuyruk + "\n"
    return s + "\n"


def dolgu(n, tarih="2026-10-08 11:00", ad="dolgu", govde=3):
    return "".join(blok("## %s — MimarA → MimarB: %s %d" % (tarih, ad, i), govde=govde)
                   for i in range(n))


def oku(yol):
    if not os.path.exists(yol):
        return ""
    with open(yol, "r", encoding="utf-8") as f:
        return f.read()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def izole_kok(mutant=None):
    kok = tempfile.mkdtemp(prefix="kutu-kilidi-")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in KOPYA:
        shutil.copy2(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    if mutant is not None:
        _ad, dosya, degisimler, _hedef = mutant
        yol = os.path.join(kok, "tools", dosya)
        metin = oku(yol)
        for eski, yeni in degisimler:
            if metin.count(eski) != 1:
                raise RuntimeError("MUTANT UYGULANAMADI (%s): desen %d kez" % (
                    _ad, metin.count(eski)))
            metin = metin.replace(eski, yeni)
        yaz(yol, metin)
    return kok


def alan(kok, ad):
    d = os.path.join(kok, ad)
    os.makedirs(d)
    return os.path.join(d, KUTU_ADI)


def kapi_kos(kok, kutu, simdi=SIMDI):
    env = dict(os.environ)
    env.pop("PRUVO_KUTU_YOLU", None)
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", "defter-kota-kapisi.py"),
                        "--kutu-kontrol", kok, "--kutu", kutu, "--simdi", simdi],
                       capture_output=True, text=True, env=env, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def kanca_kos(kok, kutu, simdi):
    """pre-commit'in cagirdigi TAM `main` (`defter-kota-kapisi.py <kok>`), sahte kutuyla."""
    env = dict(os.environ)
    env.pop("PRUVO_KUTU_YOLU", None)
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", "defter-kota-kapisi.py"),
                        "--kutu", kutu, "--simdi", simdi, kok],
                       capture_output=True, text=True, env=env, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def kuru_plan_satir(c):
    """`KUTU_ROTASYON_KURU ... sonra_satir=<n>` -> int ya da None (okunamadi)."""
    for satir in c.splitlines():
        if satir.startswith("KUTU_ROTASYON_KURU "):
            for parca in satir.split():
                if parca.startswith("sonra_satir=") and parca[12:].isdigit():
                    return int(parca[12:])
    return None


def arac_kos(kok, kutu, ekler):
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", "kutu-arsivle.py"),
                        "--kutu", kutu] + list(ekler),
                       capture_output=True, text=True, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def arsiv_yolu(kutu):
    return kutu[:-3] + "-arsiv.md"


def basliklar(metin):
    return [s for s in metin.splitlines() if s.startswith("## ")]


# ---------------------------------------------------------------------- vakalar
def v_a(kok, d):
    kutu = alan(kok, "a")
    metin = FM + dolgu(100, govde=4)
    yaz(kutu, metin)
    once = len(metin.splitlines())
    rc, c = kapi_kos(kok, kutu, simdi=SIMDI_YASLI)
    plan = kuru_plan_satir(c)
    d("a1 sahte kutu %d satir > tavan %d (fikstur)" % (once, TAVAN), once >= 600, "")
    d("a2 KUTU kolu rc=0 (kuru rotasyon sonrasi)", rc == 0, "rc=%d" % rc)
    d("a3 kapi rotasyonu YALNIZ KURU kostu (`KUTU_ROTASYON_KURU rc=0`, yazan jeton YOK)",
      "KUTU_ROTASYON_KURU rc=0 " in c and "KUTU_ROTASYON rc=" not in c, c[-400:])
    d("a4 kuru plan tavan altina iner (`sonra_satir=<n>` <= tavan)",
      plan is not None and plan <= TAVAN, "plan=%s" % plan)
    d("a5 kutu bayt-ESIT + arsiv OLUSMADI (kanca yazmadi)",
      oku(kutu) == metin and not os.path.exists(arsiv_yolu(kutu)), "")
    d("a6 `KUTU_TEFTIS` RAPOR basildi (kutu tavan ustunde kaldi, commit gecer)",
      ("\U0001f7e0 KUTU_TEFTIS satir=%d tavan=%d" % (once, TAVAN)) in c, c[-300:])


def v_b(kok, d):
    kutu = alan(kok, "b")
    metin = FM + "".join(blok("## 2026-10-08 11:00 — MimarA → MimarB (KORUMALI): konu %d" % i,
                              govde=4) for i in range(100))
    yaz(kutu, metin)
    once = len(metin.splitlines())
    rc, c = kapi_kos(kok, kutu)
    d("b1 tum-KORUMALI kutu %d satir > tavan (fikstur)" % once, once >= 600, "")
    d("b2 KUTU kolu rc=0 (KUTU_TEFTIS hali)", rc == 0, "rc=%d" % rc)
    d("b3 `🟠 KUTU_TEFTIS satir=<n> tavan=500 korumali=100` RAPOR basildi",
      ("\U0001f7e0 KUTU_TEFTIS satir=%d tavan=%d korumali=100" % (once, TAVAN)) in c, c[-500:])
    d("b4 kutu DEGISMEDI (korunan bloklar tasinmadi)", oku(kutu) == metin, "")


def v_c(kok, d):
    kutu = alan(kok, "c")
    k47, k49 = "2026-10-06 13:00", "2026-10-06 11:00"     # SIMDI'den 47 / 49 saat once
    parca = [FM, dolgu(3)]
    beklenen_kalir, beklenen_gider = [], []
    for tarih, liste, etiket in ((k47, beklenen_kalir, "47"), (k49, beklenen_gider, "49")):
        b1 = "## %s — MimarA → MimarB (KORUMALI): etiket %ss" % (tarih, etiket)
        b2 = "## %s — MimarA → MimarB: kapanis jetonlu %ss" % (tarih, etiket)
        b3 = "## %s — \U0001f680 BASLIYORUM · cip `ZzZ-Acik%ss-8Eki`" % (tarih, etiket)
        parca.append(blok(b1))
        parca.append(blok(b2, kuyruk="✅ IS BITTI — %s" % BEKLEYEN))
        parca.append(blok(b3))
        liste.extend([b1, b2, b3])
    parca.append(dolgu(2, tarih="2026-10-06 10:00", ad="eski dolgu"))
    yaz(kutu, "".join(parca))
    rc, c = arac_kos(kok, kutu, ["--tavan", "10", "--koru", "3", "--su-seviye-orani", "0.1",
                                 "--simdi", SIMDI])
    kalan, ars = oku(kutu), oku(arsiv_yolu(kutu))
    d("c0 arac rc=0", rc == 0, c[-400:])
    for b in beklenen_gider:
        d("c1 49s KORUMALI tasindi: %s" % b[31:70], b in ars and b not in kalan, "")
    for b in beklenen_kalir:
        d("c2 47s KORUMALI tasinmadi: %s" % b[31:70], b in kalan and b not in ars, "")
    d("c3 `KORUMA_DUSTU=3 yas=3 kapandi=0` basildi",
      "KORUMA_DUSTU=3 yas=3 kapandi=0" in c, [s for s in c.splitlines() if "KORUMA_D" in s])


def v_d(kok, d):
    kutu = alan(kok, "d")
    t = "2026-10-08 11:00"                            # 1 saatlik: YAS kurali DEVREDE DEGIL
    gider1 = "## %s — MimarA → MimarB (KORUMALI): kapandi etiketli" % t
    gider2 = "## %s — MimarA → MimarB: kapandi jetonlu" % t
    kalir1 = "## %s — MimarA → MimarB (KORUMALI): kapatan isaretsiz" % t
    kalir2 = "## %s — MimarA → MimarB (KORUMALI): isaret yalniz govdede" % t
    kapatan = "**Kapatan:** KraL satiri %s — BaBa (11:0x)" % KAPANDI
    metin = (FM + dolgu(3)
             + blok(gider1, ek=kapatan)
             + blok(kalir1, ek="**Kapatan:** KraL satiri bekleniyor — BaBa (11:0x)")
             + blok(kalir2, ek="- not: %s ifadesi yalniz govdede" % KAPANDI)
             + blok(gider2, ek=kapatan, kuyruk="✅ IS BITTI — %s" % BEKLEYEN))
    yaz(kutu, metin)
    # 1 saatlik bloklar en az yas tabaninin (24 sa) ALTINDA: bu vaka KAPANDI eksenini
    # olcer, taban ekseni kutu-arsivle-test.py `EAY` suitinde -> taban burada KAPALI.
    rc, c = arac_kos(kok, kutu, ["--tavan", "10", "--koru", "3", "--su-seviye-orani", "0.1",
                                 "--simdi", SIMDI, "--en-az-yas-sa", "0"])
    kalan, ars = oku(kutu), oku(arsiv_yolu(kutu))
    d("d0 arac rc=0", rc == 0, c[-400:])
    d("d1 `Kapatan ... ✔︎ KAPANDI` KORUMALI etiketli blok tasindi",
      gider1 in ars and gider1 not in kalan, "")
    d("d2 `Kapatan ... ✔︎ KAPANDI` bekleyen-jetonlu blok tasindi (D14 denetimi gecti)",
      gider2 in ars and gider2 not in kalan, "")
    d("d3 isaretsiz Kapatan -> KORUMALI kaldi", kalir1 in kalan and kalir1 not in ars, "")
    d("d4 isaret yalniz GOVDEDE -> KORUMALI kaldi", kalir2 in kalan and kalir2 not in ars, "")
    d("d5 `KORUMA_DUSTU=2 yas=0 kapandi=2` basildi", "KORUMA_DUSTU=2 yas=0 kapandi=2" in c,
      [s for s in c.splitlines() if "KORUMA_D" in s])


def v_e(kok, d):
    kutu = alan(kok, "e")
    tarihsiz = "## Tarihsiz not — MimarA → MimarB (KORUMALI): tarih okunamaz"
    bozuk = "## 2026-13-45 10:00 — MimarA → MimarB (KORUMALI): gecersiz tarih"
    eski = "## 2026-09-01 10:00 — MimarA → MimarB (KORUMALI): kontrol eski"
    yaz(kutu, FM + dolgu(3) + blok(tarihsiz) + blok(bozuk) + blok(eski))
    rc, c = arac_kos(kok, kutu, ["--tavan", "5", "--koru", "3", "--su-seviye-orani", "0.1",
                                 "--simdi", "2027-01-01 00:00"])
    kalan, ars = oku(kutu), oku(arsiv_yolu(kutu))
    d("e0 arac rc=0", rc == 0, c[-400:])
    d("e1 tarihsiz KORUMALI tasinmadi", tarihsiz in kalan and tarihsiz not in ars, "")
    d("e2 gecersiz tarihli (2026-13-45) KORUMALI tasinmadi", bozuk in kalan and bozuk not in ars, "")
    d("e3 KONTROL: ayni kosumda eski tarihli KORUMALI tasindi (kural DEVREDE)",
      eski in ars and eski not in kalan, "")


def v_f(kok, d):
    kutu = alan(kok, "f")
    m6 = "## 2026-10-08 10:00 — MimarA → MimarB: alti satir"
    m7 = "## 2026-10-08 10:01 — MimarA → MimarB: yedi satir"
    b10 = "## 2026-10-08 10:02 — ⚖️ BaBa → KraL: on satir"
    b11 = "## 2026-10-08 10:03 — ⚖️ BaBa → KraL: on bir satir"
    yaz(kutu, FM + blok(m6, govde=5) + "---\n\n" + blok(m7, govde=6)
        + blok(b10, govde=9) + blok(b11, govde=10))
    rc, c = arac_kos(kok, kutu, ["--teftis"])
    satirlar = [s for s in c.splitlines() if s.startswith("\U0001f7e0 UZUN_BLOK ")]
    d("f0 --teftis rc=0 ve UZUN_BLOK=2", rc == 0 and "UZUN_BLOK=2 " in c, c[-400:])
    d("f1 mimar 7 satir RAPOR edildi (satir=7)",
      any(m7[:60] in s and s.endswith(" satir=7") for s in satirlar), satirlar)
    d("f2 mimar 6 satir RAPOR edilmedi (ayrac/bos satir sayilmaz)",
      not any(m6[:60] in s for s in satirlar), satirlar)
    d("f3 BaBa ⚖️ 11 satir RAPOR edildi (satir=11)",
      any(b11[:60] in s and s.endswith(" satir=11") for s in satirlar), satirlar)
    d("f4 BaBa ⚖️ 10 satir RAPOR edilmedi", not any(b10[:60] in s for s in satirlar), satirlar)


def v_g(kok, d):
    kutu = alan(kok, "g")
    metin = FM + dolgu(100, govde=4)
    yaz(kutu, metin)
    kilit_yol = os.path.join(os.path.dirname(kutu), "." + KUTU_ADI + ".lock")
    fd = open(kilit_yol, "a+")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        rc, c = kapi_kos(kok, kutu)
    finally:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
        fd.close()
    d("g1 kilit baskasinda -> KUTU kolu rc=0", rc == 0, "rc=%d" % rc)
    d("g2 `KUTU_TEFTIS=OLCULEMEDI` basildi", "KUTU_TEFTIS=OLCULEMEDI" in c, c[-400:])
    d("g3 kutu DEGISMEDI", oku(kutu) == metin, "")


def v_h(kok, d):
    kutu = alan(kok, "h")
    metin = FM + dolgu(100, govde=4)
    yaz(kutu, metin)
    ham_once = open(kutu, "rb").read()
    _rc, c = kanca_kos(kok, kutu, SIMDI_YASLI)
    plan = kuru_plan_satir(c)
    d("h1 kanca kosumu `KUTU_ROTASYON_KURU sonra_satir=<n>` basti (n <= tavan: plan VARDI)",
      plan is not None and plan <= TAVAN, c[-500:])
    d("h2 kutu bayt-ESIT (dal kodu + yazan kip = RED)",
      open(kutu, "rb").read() == ham_once, "")
    d("h3 arsiv OLUSMADI", not os.path.exists(arsiv_yolu(kutu)), "")


VAKALAR = (("a", v_a), ("b", v_b), ("c", v_c), ("d", v_d), ("e", v_e), ("f", v_f),
           ("g", v_g), ("h", v_h))


def batarya(mutant=None, sessiz=False):
    """{vaka: [(ad, gecti, tani)]} — izole kopyada kosar, kok her halde silinir."""
    sonuc = {}
    kok = izole_kok(mutant)
    try:
        for anahtar, fn in VAKALAR:
            liste = []
            sonuc[anahtar] = liste

            def d(ad, kosul, tani, _l=liste):
                _l.append((ad, bool(kosul), tani))
                if not sessiz:
                    print("  %s %s" % ("✅" if kosul else "❌", ad))
                    if not kosul and tani != "":
                        print("      tani: %s" % (tani,))
            try:
                fn(kok, d)
            except Exception as e:                            # noqa: BLE001
                d("%s CALISTIRILAMADI: %s" % (anahtar, e), False, "")
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return sonuc


def main():
    tmp_once = len([x for x in os.listdir(tempfile.gettempdir())
                    if x.startswith("kutu-kilidi-")])
    print("=== KABUL (izole kopya, simdi=%s) ===" % SIMDI)
    sonuc = batarya()
    tum = [x for v in sonuc.values() for x in v]
    gecen = len([x for x in tum if x[1]])

    print("=== MUTANTLAR (izole kopya; hedef vaka KIRMIZI olmali) ===")
    olduren = 0
    for m in MUTANTLAR:
        try:
            ms = batarya(m, sessiz=True)
        except RuntimeError as e:
            print("  ❌ %s — %s (SAYILMADI = SURVIVOR)" % (m[0], e))
            continue
        hedef_kirmizi = [x[0] for x in ms[m[3]] if not x[1]]
        if hedef_kirmizi:
            olduren += 1
            print("  ✅ %s OLDU — hedef vaka (%s) KIRMIZI: %s"
                  % (m[0], m[3], "; ".join(hedef_kirmizi[:3])))
        else:
            print("  ❌ %s SURVIVOR — hedef vaka (%s) YESIL kaldi" % (m[0], m[3]))
    tmp_sonra = len([x for x in os.listdir(tempfile.gettempdir())
                     if x.startswith("kutu-kilidi-")])
    print("GECICI_DIZIN once=%d sonra=%d" % (tmp_once, tmp_sonra))
    rc = 0 if (gecen == len(tum) and olduren == len(MUTANTLAR)) else 1
    print("TEST=%d/%d MUTANT=%d/%d SURVIVOR=%d rc=%d"
          % (gecen, len(tum), olduren, len(MUTANTLAR), len(MUTANTLAR) - olduren, rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
