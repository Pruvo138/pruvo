#!/usr/bin/env python3
"""B7 KABUL BATARYASI — nobet turunun IZOLE kaydi + tavan asimi teshisi.

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B7 (4 kabul maddesi).
KANONIK KAYNAK: pruvo deposu `tools/n4b/nobet-tur-izolasyon-test.py`
                (cron duzleminde git YOK; kopyayi `b7-kur.py` tasir).

KOSUM:  python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
KABUL:  son satir `KABUL=GECTI (n/n vaka)` ve rc=0.
CAGRI YERI: `testler.py` PAKETLER listesi (--kendini-test yesili YETMEZ,
            [[kapinin-menzili-cagri-yeridir]]).

OLCULEN KABUL MADDELERI
  1) Bir `ci-nobeti` turunun TUM ciktisi, baska turlarin satirlari KARISMADAN
     okunabilir  -> BOLUM A (iki GERCEKTEN eszamanli isci.sh turu)
  2) Tavan asiminda turun SON 50 satiri hukme eklenir                -> BOLUM B
  3) `onarim_ilerliyor_mu` POZITIF ve NEGATIF kollari AYRI olculur   -> BOLUM C
  4) Mutant: izolasyon kaldirilinca test KIRMIZI yanar               -> BOLUM D

🔴 TAUTOLOJI KALKANI (A2): iki tur gercekten IC ICE kosmadiysa "izole" sonucu
bedavadir. A2 paylasilan `isci.log` deltasinda A<->B GECISI sayar; gecis 0 ise
hukum GECTI degil OLCULEMEDI olur.

🔴 HEDEF KOL ATFI (K182 / [[ad-iki-rolde-mutanti-golgeler]]): her mutantta
yalniz "hedef vaka KIRMIZI oldu" degil, "YAN EKSEN YESIL KALDI" da olculur.
Mutantin yasamasi kol saglam demek DEGIL, kol olculemedi demektir.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time

CRON_KOKU = "/Users/okan/.claude/cron"
ISCI_SH = os.path.join(CRON_KOKU, "isci.sh")
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
ISCI_LOG = os.path.join(CRON_KOKU, "isci.log")
TUR_CIKTI_DIZINI = os.path.join(CRON_KOKU, "isci-tur-cikti")

TAG_A = "B7TURA"
TAG_B = "B7TURB"
SATIR_ADEDI = 25            # tur basina uretilen essiz satir sayisi
ISCI_TIMEOUT = 120

VAKALAR = []                # (id, beklenen, olculen, gecti)


def vaka(vid, beklenen, olculen):
    gecti = (str(beklenen) == str(olculen))
    VAKALAR.append((vid, beklenen, olculen, gecti))
    print("VAKA=%-26s BEKLENEN=%-22s OLCULEN=%-22s SONUC=%s"
          % (vid, beklenen, olculen, "GECTI" if gecti else "KALDI"))
    return gecti


# ===========================================================================
# nobet-kapi.py'yi modul olarak yukle (tireli ad -> importlib)
# ===========================================================================

def kapi_yukle():
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    spec = importlib.util.spec_from_file_location("b7_nobet_kapi", NOBET_KAPI)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b7_nobet_kapi"] = mod
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# BOLUM A — IZOLASYON (uctan uca, GERCEK isci.sh + sahte motor ikilisi)
# ===========================================================================

SAHTE_MOTOR = textwrap.dedent("""\
    #!/bin/bash
    # B7 sahte motor: TAG ile etiketli N satir basar, arada bekler.
    # Bekleme SART: iki tur ic ice gecsin diye (A2 tautoloji kalkani).
    TAG="${B7_TAG:-B7TUR?}"
    N="${B7_SATIR:-25}"
    i=1
    while (( i <= N )); do
      echo "${TAG}_SATIR_${i} HUKUM=TEMIZ DAGITILAN=7"
      sleep 0.06
      i=$(( i + 1 ))
    done
    exit 0
""")


def temiz_env(ekstra=None):
    beyaz = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG",
             "LC_ALL", "LC_CTYPE", "TERM", "TMPDIR"}
    env = {k: v for k, v in os.environ.items() if k in beyaz}
    env["PRUVO_ISCI_BAGLAM"] = "kapali"
    env["PRUVO_ISCI_BEKCI_ARALIK"] = "1"
    env["BEKCI_SIGKILL_BEKLEME_SN"] = "3"
    if ekstra:
        env.update(ekstra)
    return env


def log_boyutu():
    return os.path.getsize(ISCI_LOG) if os.path.isfile(ISCI_LOG) else 0


def log_delta(once):
    """Snapshot'tan beri eklenen metin.

    🔴 isci.sh tur sonunda `isci-log-dondur.py` ile logu KIRPABILIR (6000 satir
    tavani). Kirpilma olursa offset gecersizdir; o durumda dosyanin TAMAMI
    okunur (bizim satirlarimiz en yeniler, kirpma onlari tutar).
    """
    if not os.path.isfile(ISCI_LOG):
        return ""
    boyut = os.path.getsize(ISCI_LOG)
    with open(ISCI_LOG, "rb") as dosya:
        if boyut >= once:
            dosya.seek(once)
        return dosya.read().decode("utf-8", errors="replace")


class IsciKosumu:
    """Bir isci.sh turunu ayri is parcaciginda kosar."""

    def __init__(self, tmp, sahte, etiket, tag, tur_cikti):
        self.etiket = etiket
        self.tag = tag
        self.tur_cikti = tur_cikti
        self.ev = os.path.join(tmp, "ev-%s" % etiket)
        os.makedirs(self.ev, exist_ok=True)
        self.spec = os.path.join(tmp, "spec-%s.md" % etiket)
        with open(self.spec, "w", encoding="utf-8") as dosya:
            dosya.write("# B7 TEST SPEC (%s)\nBos spec.\n" % etiket)
        self.profil = os.path.join(
            CRON_KOKU, "profil-kimi-%s" % re.sub(r"[^A-Za-z0-9._-]", "_",
                                                 os.path.basename(self.ev)))
        if os.path.exists(self.profil):
            shutil.rmtree(self.profil)
        os.makedirs(os.path.join(self.profil, "projects"))
        self.env = temiz_env({
            "PRUVO_ISCI_CLAUDE_BIN": sahte,
            "PRUVO_ISCI_TUR_CIKTI": tur_cikti,
            "B7_TAG": tag,
            "B7_SATIR": str(SATIR_ADEDI),
        })
        self.rc = None
        self.thread = threading.Thread(target=self._kos)

    def _kos(self):
        try:
            proc = subprocess.run(
                [ISCI_SH, "kimi", self.ev, self.spec, "kabul-b7-%s" % self.etiket],
                env=self.env, capture_output=True, text=True, timeout=ISCI_TIMEOUT)
            self.rc = proc.returncode
        except subprocess.TimeoutExpired:
            self.rc = -2

    def temizle(self):
        shutil.rmtree(self.profil, ignore_errors=True)


def izolasyon_kos(tmp, sahte, yol_a, yol_b):
    """Iki turu ESZAMANLI kosar; (delta, a, b) doner."""
    once = log_boyutu()
    a = IsciKosumu(tmp, sahte, "izo-a", TAG_A, yol_a)
    b = IsciKosumu(tmp, sahte, "izo-b", TAG_B, yol_b)
    a.thread.start()
    b.thread.start()
    a.thread.join()
    b.thread.join()
    delta = log_delta(once)
    a.temizle()
    b.temizle()
    return delta, a, b


def tag_say(yol, tag):
    if not os.path.isfile(yol):
        return -1
    with open(yol, encoding="utf-8", errors="replace") as dosya:
        return sum(1 for s in dosya if tag in s)


def gecis_say(metin):
    """Paylasilan log'da A<->B gecis sayisi (gercekten ic ice mi?)."""
    dizi = []
    for satir in metin.splitlines():
        if TAG_A in satir:
            dizi.append("A")
        elif TAG_B in satir:
            dizi.append("B")
    return sum(1 for i in range(1, len(dizi)) if dizi[i] != dizi[i - 1])


def bolum_a(tmp, sahte):
    """Kabul-1 + tautoloji kalkani. (gecti_mi, gecis_sayisi) doner."""
    print("--- BOLUM A: IZOLASYON (uctan uca, iki eszamanli tur) ---")
    yol_a = os.path.join(tmp, "tur-a.log")
    yol_b = os.path.join(tmp, "tur-b.log")
    delta, ka, kb = izolasyon_kos(tmp, sahte, yol_a, yol_b)

    gecis = gecis_say(delta)
    # A2 ONCE kosar: fixture gercekten ic ice degilse gerisi bedavadir.
    vaka("A2-ic-ice-gecti", "gecis>=1", "gecis=%d" % gecis if gecis >= 1 else "gecis=0")
    olculen_a2 = gecis >= 1

    vaka("A1a-A-kendi-satiri", SATIR_ADEDI, tag_say(yol_a, TAG_A))
    vaka("A1b-A-yabanci-satir", 0, max(0, tag_say(yol_a, TAG_B)))
    vaka("A1c-B-kendi-satiri", SATIR_ADEDI, tag_say(yol_b, TAG_B))
    vaka("A1d-B-yabanci-satir", 0, max(0, tag_say(yol_b, TAG_A)))
    vaka("A3a-baglanti-A", "VAR", "VAR" if ("TUR_CIKTI=%s" % yol_a) in delta else "YOK")
    vaka("A3b-baglanti-B", "VAR", "VAR" if ("TUR_CIKTI=%s" % yol_b) in delta else "YOK")
    vaka("A0-kosum-rc", "0,0", "%s,%s" % (ka.rc, kb.rc))

    # A4: env YOKKEN varsayilan ad -> isci-tur-cikti/<etiket>-...
    once = log_boyutu()
    d = IsciKosumu(tmp, sahte, "izo-c", "B7TURC", "")
    d.env.pop("PRUVO_ISCI_TUR_CIKTI", None)
    d.thread.start()
    d.thread.join()
    delta_c = log_delta(once)
    d.temizle()
    eslesme = re.findall(r"TUR_CIKTI=(\S+)", delta_c)
    varsayilan = eslesme[-1] if eslesme else ""
    beklenen_onek = os.path.join(TUR_CIKTI_DIZINI, "kabul-b7-izo-c-")
    vaka("A4-varsayilan-ad", "onek+VAR",
         ("onek+VAR" if varsayilan.startswith(beklenen_onek)
          and os.path.isfile(varsayilan) else "yol=%s" % (varsayilan or "-")))
    if varsayilan and os.path.isfile(varsayilan):
        os.remove(varsayilan)
    return olculen_a2


# ===========================================================================
# BOLUM B — TAVAN ASIMINDA SON-50 (kabul-2)
# ===========================================================================

def bolum_b(kapi, tmp, etiket=""):
    print("--- BOLUM B%s: TAVAN ASIMINDA SON 50 SATIR ---" % etiket)
    dolu = os.path.join(tmp, "dolu%s.log" % etiket)
    with open(dolu, "w", encoding="utf-8") as dosya:
        for i in range(1, 121):
            dosya.write("SATIR_%d\n" % i)
    bos = os.path.join(tmp, "bos%s.log" % etiket)
    open(bos, "w").close()

    _, metin = kapi._sure_tavani_sonucu(b"", lambda: None, 1500, dolu)
    m_satir = re.search(r"TUR_SON_50_SATIR=(\d+)", metin)
    vaka("B1a-satir-sayisi%s" % etiket, "50", m_satir.group(1) if m_satir else "YOK")
    vaka("B1b-son-satir%s" % etiket, "VAR", "VAR" if "SATIR_120" in metin else "YOK")
    vaka("B1c-51-onceki-yok%s" % etiket, "YOK",
         "VAR" if re.search(r"\bSATIR_70\b", metin) else "YOK")
    vaka("B1d-blok-basligi%s" % etiket, "VAR",
         "VAR" if "--- TUR SON 50 ---" in metin else "YOK")

    _, metin_bos = kapi._sure_tavani_sonucu(b"", lambda: None, 1500, bos)
    vaka("B2a-bos-sebep%s" % etiket, "CIKTI_AKMADI",
         "CIKTI_AKMADI" if "SEBEP=CIKTI_AKMADI" in metin_bos else "YOK")
    _, metin_yok = kapi._sure_tavani_sonucu(b"", lambda: None, 1500, None)
    vaka("B2b-yolsuz-sebep%s" % etiket, "YOL_YOK",
         "YOL_YOK" if "SEBEP=YOL_YOK" in metin_yok else "YOK")

    # B3 — GOMULU KANIT HUKUM EKSENINI EZMEZ
    kirli = os.path.join(tmp, "kirli%s.log" % etiket)
    with open(kirli, "w", encoding="utf-8") as dosya:
        dosya.write("motor calisti\nHUKUM=TEMIZ\nDAGITILAN=7\nKAPANAN=3\n")
    _, metin_k = kapi._sure_tavani_sonucu(b"", lambda: None, 1500, kirli)
    vaka("B3a-hukum-korundu%s" % etiket, "SURE_TAVANI",
         kapi.tur_hukmu_ayikla(metin_k))
    vaka("B3b-olcum-korundu%s" % etiket, 0,
         kapi.tur_olcumu_ayikla(metin_k, "DAGITILAN"))
    m = re.search(r"MASKELENEN=(\d+)", metin_k)
    n_maske = int(m.group(1)) if m else -1
    vaka("B3c-maskelenen-sayi%s" % etiket, "maskelenen>=3",
         "maskelenen>=3" if n_maske >= 3 else "maskelenen=%d" % n_maske)

    # B4 — _sureli_isci_bekle uctan uca yolu TASIYOR mu
    def dusen(_sn):
        raise subprocess.TimeoutExpired("x", _sn, output=b"")
    rc, metin_e2e = kapi._sureli_isci_bekle(dusen, lambda: None,
                                            kisa_tavan=1, uzun_tavan=2,
                                            tur_cikti_yolu=dolu)
    vaka("B4a-rc%s" % etiket, 1, rc)
    vaka("B4b-tavan-jetonu%s" % etiket, "VAR",
         "VAR" if "SURE_TAVANI_ASILDI=1" in metin_e2e else "YOK")
    vaka("B4c-son50-tasindi%s" % etiket, "VAR",
         "VAR" if "SATIR_120" in metin_e2e else "YOK")


# ===========================================================================
# BOLUM C — onarim_ilerliyor_mu IKI KOLU (kabul-3)
# ===========================================================================

def bolum_c(kapi, etiket=""):
    print("--- BOLUM C%s: ONARIM_ILERLIYOR IKI KOL ---" % etiket)
    vaka("C1-pozitif-hukum%s" % etiket, True,
         kapi.onarim_ilerliyor_mu("HUKUM=ONARIM_ILERLIYOR\n"))
    vaka("C2-pozitif-dagitilan%s" % etiket, True,
         kapi.onarim_ilerliyor_mu("DAGITILAN=2\n"))
    vaka("C3-pozitif-kapanan%s" % etiket, True,
         kapi.onarim_ilerliyor_mu("KAPANAN=1\n"))
    vaka("C4-negatif-bos%s" % etiket, False,
         kapi.onarim_ilerliyor_mu("motor bir sey yapmadi\n"))
    vaka("C5-negatif-sifir%s" % etiket, False,
         kapi.onarim_ilerliyor_mu("DAGITILAN=0\nKAPANAN=0\n"))

    # C6 — POZITIF KOL CAGRI YERINDE CANLI MI?
    # Bugune kadar YALNIZ negatif kol gozlendi (gozcu.log:1997). Pozitif kolun
    # OLU olmadigi, tavanin gercekten UZADIGI ile kanitlanir.
    for ad, cikti, beklenen in (
            ("C6a-pozitif-uzatti", b"DAGITILAN=2\n", 2),
            ("C6b-negatif-uzatmadi", b"hicbir sey\n", 1)):
        cagri = []

        def bekleyici(sn, _c=cikti):
            cagri.append(sn)
            raise subprocess.TimeoutExpired("x", sn, output=_c)
        kapi._sureli_isci_bekle(bekleyici, lambda: None,
                                kisa_tavan=1, uzun_tavan=2)
        vaka("%s%s" % (ad, etiket), beklenen, len(cagri))


# ===========================================================================
# BOLUM D — MUTANTLAR (kabul-4) + HEDEF KOL ATFI
# ===========================================================================

def sayim():
    return sum(1 for *_x, g in VAKALAR if g), len(VAKALAR)


def mutant_kos(ad, yama, geri, hedef_onek, yan_onek, kapi, tmp):
    """Mutanti uygular, bolumleri yeniden kosar, HEDEF+YAN eksenini ayri olcer."""
    isaret = len(VAKALAR)
    yama()
    try:
        bolum_b(kapi, tmp, etiket="-%s" % ad)
        bolum_c(kapi, etiket="-%s" % ad)
    finally:
        geri()
    yeni = VAKALAR[isaret:]
    del VAKALAR[isaret:]                    # mutant vakalari ANA tallye girmez
    hedef = [v for v in yeni if any(v[0].startswith(o) for o in hedef_onek)]
    yan = [v for v in yeni if any(v[0].startswith(o) for o in yan_onek)]
    hedef_oldu = bool(hedef) and all(not v[3] for v in hedef)
    yan_yesil = bool(yan) and all(v[3] for v in yan)
    print("MUTANT=%-24s HEDEF_KOL=%-8s (%d vaka) YAN_EKSEN=%-8s (%d vaka)"
          % (ad, "OLDU" if hedef_oldu else "YASADI", len(hedef),
             "YESIL" if yan_yesil else "KIRMIZI", len(yan)))
    return hedef_oldu, yan_yesil


def bolum_d(kapi, tmp, sahte):
    print("--- BOLUM D: MUTANTLAR ---")
    sonuclar = []

    # M1 — IZOLASYON KALDIRILDI (uctan uca): iki tur AYNI dosyaya yazar.
    ortak = os.path.join(tmp, "ortak.log")
    isaret = len(VAKALAR)
    delta, ka, kb = izolasyon_kos(tmp, sahte, ortak, ortak)
    del VAKALAR[isaret:]
    a_yabanci = tag_say(ortak, TAG_B)
    m1_hedef = a_yabanci > 0                # izolasyon YOK -> yabanci satir VAR
    m1_gecis = gecis_say(delta) >= 1
    print("MUTANT=%-24s HEDEF_KOL=%-8s (yabanci_satir=%d) YAN_EKSEN=%-8s (gecis=%s)"
          % ("M1-izolasyon-kaldirildi", "OLDU" if m1_hedef else "YASADI",
             max(0, a_yabanci), "YESIL" if m1_gecis else "KIRMIZI", m1_gecis))
    sonuclar.append(("M1-izolasyon-kaldirildi", m1_hedef, m1_gecis))

    # M2 — SON-50 BLOGU KALDIRILDI -> BOLUM B oler, BOLUM C yesil kalir.
    asil_blok = kapi._tur_son_blogu
    sonuclar.append(("M2-son50-kaldirildi",) + mutant_kos(
        "M2-son50-kaldirildi",
        lambda: setattr(kapi, "_tur_son_blogu", lambda *a, **k: ""),
        lambda: setattr(kapi, "_tur_son_blogu", asil_blok),
        # B1c NEGATIF iddiadir ("SATIR_70 YOK") ve blok silinince de dogru
        # kalir -> HEDEF degil YAN eksendedir. Bunu hedefe koymak mutanti
        # "yasadi" gosterir ([[ad-iki-rolde-mutanti-golgeler]]).
        ("B1a", "B1b", "B1d", "B2a", "B2b", "B3c", "B4c"),
        ("B1c", "B3a", "B3b", "B4a", "B4b", "C"),
        kapi, tmp))

    # M3 — MASKELEME KALDIRILDI -> OLCUM ekseni ezilir (DAGITILAN=7 sizar).
    # B3a (hukum ekseni) YAN eksendedir: blok HUKUM satirindan ONCE yazildigi
    # icin hukum maskesiz de korunur — iki ayri kalkan, ayri olculur.
    asil_maske = kapi._jetonlari_etkisizlestir
    sonuclar.append(("M3-maskeleme-kaldirildi",) + mutant_kos(
        "M3-maskeleme-kaldirildi",
        lambda: setattr(kapi, "_jetonlari_etkisizlestir", lambda s: s),
        lambda: setattr(kapi, "_jetonlari_etkisizlestir", asil_maske),
        ("B3b", "B3c"), ("B1", "B2", "B3a", "B4", "C"),
        kapi, tmp))

    # M4 — POZITIF KOL OLDURULDU -> BOLUM C pozitifleri oler, B yesil kalir.
    asil_ilerleme = kapi.onarim_ilerliyor_mu
    sonuclar.append(("M4-pozitif-kol-oldu",) + mutant_kos(
        "M4-pozitif-kol-oldu",
        lambda: setattr(kapi, "onarim_ilerliyor_mu", lambda c: False),
        lambda: setattr(kapi, "onarim_ilerliyor_mu", asil_ilerleme),
        ("C1", "C2", "C3", "C6a"),
        ("B1", "B2", "B3", "B4", "C4", "C5", "C6b"),
        kapi, tmp))

    # K0 — KONTROL MUTANTI: hicbir sey degistirmez, HER SEY yesil kalmali.
    isaret = len(VAKALAR)
    bolum_b(kapi, tmp, etiket="-K0")
    bolum_c(kapi, etiket="-K0")
    k0 = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    k0_yesil = all(v[3] for v in k0)
    print("MUTANT=%-24s HEDEF_KOL=%-8s (%d vaka)"
          % ("K0-kontrol", "YESIL" if k0_yesil else "KIRMIZI", len(k0)))
    return sonuclar, k0_yesil, len(k0)


# ===========================================================================

def main():
    if not os.path.isfile(NOBET_KAPI):
        print("KABUL=KALDI (nobet-kapi.py yok)")
        return 2
    kapi = kapi_yukle()
    eksik = [ad for ad in ("_tur_son_blogu", "_jetonlari_etkisizlestir",
                           "tur_son_satirlar", "tur_cikti_yolu_uret")
             if not hasattr(kapi, ad)]
    if eksik:
        print("KABUL=KALDI (B7 yamasi KURULU DEGIL: %s)" % ",".join(eksik))
        return 2

    tmp = tempfile.mkdtemp(prefix="b7-izolasyon-")
    bin_dizin = os.path.join(tmp, "bin")
    os.makedirs(bin_dizin)
    sahte = os.path.join(bin_dizin, "claude")
    with open(sahte, "w", encoding="utf-8") as dosya:
        dosya.write(SAHTE_MOTOR)
    os.chmod(sahte, 0o755)

    try:
        a2_saglam = bolum_a(tmp, sahte)
        bolum_b(kapi, tmp)
        bolum_c(kapi)
        mutantlar, k0_yesil, k0_n = bolum_d(kapi, tmp, sahte)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen, toplam = sayim()
    m_gecen = sum(1 for _, h, y in mutantlar if h and y)
    print("MUTANT=%d/%d  HEDEF_KOL_ATFI=%d/%d  KONTROL=%d/%d"
          % (m_gecen, len(mutantlar),
             sum(1 for _, h, _y in mutantlar if h), len(mutantlar),
             k0_n if k0_yesil else 0, k0_n))
    print("TOPLAM=%d GECTI=%d KALDI=%d" % (toplam, gecen, toplam - gecen))

    if not a2_saglam:
        print("KABUL=OLCULEMEDI (A2: iki tur IC ICE kosmadi — izolasyon iddiasi bedava)")
        return 3
    if not k0_yesil:
        print("KABUL=OLCULEMEDI (K0 kontrol mutanti kirmizi — batarya kararsiz)")
        return 3
    if gecen == toplam and m_gecen == len(mutantlar):
        print("KABUL=GECTI (%d/%d vaka)" % (gecen, toplam))
        return 0
    print("KABUL=KALDI (%d/%d vaka, %d/%d mutant)"
          % (gecen, toplam, m_gecen, len(mutantlar)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
