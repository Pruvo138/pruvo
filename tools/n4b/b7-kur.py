#!/usr/bin/env python3
"""B7 KURUCU — nobet turunun IZOLE kaydi + tavan asiminda son-50 teshisi.

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B7.
DUZLEM: ~/.claude/cron (git YOK) -> her degisiklik IDEMPOTENT + YEDEKLI.

NEDEN (olculdu, gozcu.log:1993-1999, 2026-08-20T09:08:02Z turu):
  tur 1500 sn tavanini doldurdu ve OLDURULDU; "25 dakika boyunca NE YAPTI"
  sorusu log ekseninden cevaplanamadi. Iki ayri kok:
    (a) `isci.log` PAYLASILAN dosyadir — eszamanli turlarin satirlari IC ICE
        gecer (ayni pencerede `kabul-k184-kuyruk` + `citroen-d5-3-ekle`).
    (b) tavan asiminda hukme YALNIZ `SURE_TAVANI_ASILDI=1` yaziliyor; turun
        kendi ciktisindan hukme HICBIR SATIR gecmiyor.
  Sonuc: "HAT BOZUK" (tur bir yerde asildi) ile "KAT YOK" (motor beceremedi)
  ayrimi yapilamiyor ve tarife karari yanlis veriye dayaniyor.

NE YAPAR (4 yama, hepsi idempotent, marker: B7-TUR-IZOLASYONU):
  I1 isci.sh   : her tur KENDI dosyasina da yazar (TUR_CIKTI), paylasilan
                 log'a `TUR_CIKTI=<yol>` baglantisi duser, eski dosyalar budanir.
  I2 nobet-kapi: sabitler + `tur_cikti_yolu_uret` / `tur_son_satirlar` /
                 `_jetonlari_etkisizlestir` / `_tur_son_blogu`.
  I3 nobet-kapi: `_sure_tavani_sonucu` son-50 blogunu hukme EKLER;
                 `_sureli_isci_bekle` yolu tasir.
  I4 nobet-kapi: `_nobet_turunu_kos` PRUVO_ISCI_TUR_CIKTI ortamini kurar.

  Ayrica: kabul bataryasi (`nobet-tur-izolasyon-test.py`) cron duzlemine
  kopyalanir ve `testler.py` PAKETLER listesine EKLENIR (kapinin CAGRI YERI —
  `--kendini-test` yesili yetmez).

🔴 GOMULU KANIT MASKELEMESI: `tur_hukmu_ayikla` SONUNCU `HUKUM=` eslesenini
alir. Turun kendi ciktisinda `HUKUM=TEMIZ` gecerse, o satiri hukme ham gommek
SURE_TAVANI hukmunu EZERDI (fail-open). Bu yuzden gomulu satirlarda makine
atamasi `JETON=` -> `JETON:` maskelenir ve MASKELENEN sayisi raporlanir.

KOSUM:
    python3 tools/n4b/b7-kur.py            # yalniz OLCER, yazmaz
    python3 tools/n4b/b7-kur.py --uygula   # yamalari uygular (yedekli)
    python3 tools/n4b/b7-kur.py --geri-al DAMGA
"""

import argparse
import os
import re
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
ISCI_SH = os.path.join(CRON_KOKU, "isci.sh")
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
TESTLER = os.path.join(CRON_KOKU, "testler.py")
TEST_ADI = "nobet-tur-izolasyon-test.py"
TEST_HEDEF = os.path.join(CRON_KOKU, TEST_ADI)
TEST_KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_ADI)

MARKER = "B7-TUR-IZOLASYONU"


# ---------------------------------------------------------------------------
# I1 — isci.sh
# ---------------------------------------------------------------------------

I1A_ANKOR = 'chmod 600 "$CIKTI_DOSYASI"\n'

I1A_YENI = '''
# === B7-TUR-IZOLASYONU (20 Agu 2026, KraL-N4B) ===
# `$LOG` (isci.log) PAYLASILAN dosyadir: eszamanli turlarin satirlari IC ICE
# gecer ve bir turun ne yaptigi okunamaz. `$CIKTI_DOSYASI` bu isi GOREMEZ —
# mktemp'tir ve EXIT trap'inde SILINIR (tur oldurulunce de silinir).
# `$TUR_CIKTI` KALICIDIR, adi turu tanimlar ve paylasilan log'a
# `TUR_CIKTI=<yol>` satiriyla BAGLANIR: log ic ice olsa bile her BASLANGIC
# satirindan o turun IZOLE dosyasina gidilir.
# nobet-kapi.py yolu PRUVO_ISCI_TUR_CIKTI ile ONCEDEN verir (tavan asiminda
# son 50 satiri hukme ekleyebilmek icin yolu BILMESI gerekir).
TUR_CIKTI_DIZINI="$CRON_KOKU/isci-tur-cikti"
mkdir -p "$TUR_CIKTI_DIZINI" 2>/dev/null
TUR_CIKTI="${PRUVO_ISCI_TUR_CIKTI:-$TUR_CIKTI_DIZINI/${ETIKET:-etiketsiz}-$(date -u +%Y%m%dT%H%M%SZ)-$$.log}"
if ! : >> "$TUR_CIKTI" 2>/dev/null; then
  TUR_CIKTI="$CIKTI_DOSYASI"      # fail-open: izolasyon yoksa tur yine kossun
fi
chmod 600 "$TUR_CIKTI" 2>/dev/null
# === B7-TUR-IZOLASYONU SON ===
'''

I1B_ANKOR = 'echo "MOTOR=$LOG_MOTOR" >> "$LOG"\n'
I1B_YENI = 'echo "TUR_CIKTI=$TUR_CIKTI" >> "$LOG"   # B7-TUR-IZOLASYONU baglantisi\n'

I1C_ESKI = ' | tee -a "$LOG" "$CIKTI_DOSYASI"\n'
I1C_YENI = ' | tee -a "$LOG" "$CIKTI_DOSYASI" "$TUR_CIKTI"\n'

I1D_ANKOR = 'python3 "$CRON_KOKU/isci-log-dondur.py" "$LOG" 6000 3000 isci.log\n'

I1D_YENI = '''
# === B7-TUR-IZOLASYONU (budama) ===
# Okan disk kurali: makinede iz birakma. Tur dosyalari SINIRSIZ birikmez;
# en YENI 60 kalir. zsh glob niteleyicisi: N=eslesme yoksa sessiz,
# om=degisiklik zamanina gore yeniden eskiye, [61,-1]=61. ve sonrasi.
if [[ -d "$TUR_CIKTI_DIZINI" ]]; then
  B7_ESKILER=("$TUR_CIKTI_DIZINI"/*.log(Nom[61,-1]))
  if (( ${#B7_ESKILER} )); then
    rm -f "${B7_ESKILER[@]}"
  fi
  unset B7_ESKILER
fi
# === B7-TUR-IZOLASYONU (budama) SON ===
'''


# ---------------------------------------------------------------------------
# I2 — nobet-kapi.py sabitleri + yardimcilari
# ---------------------------------------------------------------------------

I2A_ANKOR = "TUR_ONARIM_ZAMAN_ASIMI_SN = 3000  # onarim ilerliyorsa tur tavani (50 dk)\n"

I2A_YENI = '''
# --- B7-TUR-IZOLASYONU (20 Agu 2026, KraL-N4B) -----------------------------
# Olculdu (gozcu.log:1993-1999): tur 1500 sn dolup oldurulunce hukme yalnizca
# `SURE_TAVANI_ASILDI=1` yaziliyor; turun kendi ciktisindan HICBIR satir
# gecmiyor ve paylasilan `isci.log` eszamanli turlarla ic ice oldugu icin
# "neden asildi" sorusu logsuz kaliyor. Care: her turun IZOLE dosyasi + tavan
# asiminda o dosyanin SON 50 satirinin hukme eklenmesi.
TUR_CIKTI_DIZINI = os.path.join(CRON_KOKU, "isci-tur-cikti")
TUR_SON_SATIR = 50
# 🔴 Gomulu kanit satiri makine jetonu tasiyabilir (`HUKUM=TEMIZ`,
# `DAGITILAN=7`). `tur_hukmu_ayikla` SONUNCU esleseni aldigi icin ham gomme
# SURE_TAVANI hukmunu EZERDI (fail-open). Gomulu satirda `JETON=` -> `JETON:`.
_MAKINE_JETONU = re.compile(r"(?<![A-Za-z0-9_])([A-Z][A-Z0-9_]{2,})\\s*=")
'''

I2B_ANKOR = "def _sure_tavani_sonucu(cikti, sonlandirici, tavan):\n"

I2B_YENI = '''def tur_cikti_yolu_uret(etiket="ci-nobeti", damga=None, pid=None):
    """B7: bu turun IZOLE cikti dosyasinin yolu (paylasilan isci.log DEGIL)."""
    damga = damga or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    pid = os.getpid() if pid is None else pid
    return os.path.join(TUR_CIKTI_DIZINI, "%s-%s-%d.log" % (etiket, damga, pid))


def tur_son_satirlar(yol, adet=TUR_SON_SATIR):
    """B7 kabul-2: (satirlar, sebep) doner.

    Bos/olmayan dosya SESSIZ bos string DEGIL, adi konmus bir OLCUMDUR:
    CIKTI_AKMADI = motor tavan boyunca TEK SATIR uretmedi (hat ekseni),
    OKUNAMADI    = dosya var ama okunamadi, YOL_YOK = yol hic verilmedi.
    """
    if not yol:
        return [], "YOL_YOK"
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            satirlar = [s.rstrip("\\n") for s in dosya]
    except OSError:
        return [], "OKUNAMADI"
    if not satirlar:
        return [], "CIKTI_AKMADI"
    return satirlar[-adet:], "TAMAM"


def _jetonlari_etkisizlestir(satir):
    """Gomulu kanit satiri hukum/olcum ayikcilarini YANILTMASIN."""
    return _MAKINE_JETONU.sub(lambda m: m.group(1) + ":", satir)


def _tur_son_blogu(tur_cikti_yolu, adet=TUR_SON_SATIR):
    """B7 kabul-2: son N satir + kaynak + sebep + MASKELENEN sayisi.

    Maskeleme SAYIYLA raporlanir: sessiz bir donusum degil, olculen bir islem.
    """
    satirlar, sebep = tur_son_satirlar(tur_cikti_yolu, adet)
    maskeli = []
    maskelenen = 0
    for satir in satirlar:
        yeni = _jetonlari_etkisizlestir(satir)
        if yeni != satir:
            maskelenen += 1
        maskeli.append("S%d| %s" % (adet, yeni))
    blok = "TUR_SON_%d_KAYNAK=%s\\n" % (adet, tur_cikti_yolu or "-")
    blok += "TUR_SON_%d_SATIR=%d SEBEP=%s MASKELENEN=%d\\n" % (
        adet, len(maskeli), sebep, maskelenen)
    if maskeli:
        blok += "--- TUR SON %d ---\\n" % adet
        blok += "\\n".join(maskeli) + "\\n"
        blok += "--- TUR SON %d SONU ---\\n" % adet
    return blok


'''


# ---------------------------------------------------------------------------
# I3 — hukme son-50 eklenmesi + yolun tasinmasi
# ---------------------------------------------------------------------------

I3A_ESKI = '''def _sure_tavani_sonucu(cikti, sonlandirici, tavan):
    """Isciyi sonlandirir; hafif hukmu SURE_TAVANI yapar, ARIZA'yi korur."""
    sonlandirici()
    metin = _metne_cevir(cikti)
    mevcut_hukum = tur_hukmu_ayikla(metin)
    hukum = mevcut_hukum if (mevcut_hukum or "").startswith("ARIZA") else "SURE_TAVANI"
    metin += "\\nSURE_TAVANI_ASILDI=1 TAVAN_SN=%d\\nHUKUM=%s rc=1\\n" % (tavan, hukum)
    return 1, metin
'''

I3A_YENI = '''def _sure_tavani_sonucu(cikti, sonlandirici, tavan, tur_cikti_yolu=None):
    """Isciyi sonlandirir; hafif hukmu SURE_TAVANI yapar, ARIZA'yi korur.

    B7: son-50 blogu HUKUM satirindan ONCE yazilir ve gomulu satirlarin
    makine jetonlari maskelidir -> `tur_hukmu_ayikla` yine SURE_TAVANI okur.
    """
    sonlandirici()
    metin = _metne_cevir(cikti)
    mevcut_hukum = tur_hukmu_ayikla(metin)
    hukum = mevcut_hukum if (mevcut_hukum or "").startswith("ARIZA") else "SURE_TAVANI"
    metin += "\\nSURE_TAVANI_ASILDI=1 TAVAN_SN=%d\\n" % tavan
    metin += _tur_son_blogu(tur_cikti_yolu)
    metin += "HUKUM=%s rc=1\\n" % hukum
    return 1, metin
'''

I3B_ESKI = '''def _sureli_isci_bekle(bekleyici, sonlandirici, kisa_tavan=None, uzun_tavan=None):
    """Isciyi 25 dk; onarim ilerleme izi varsa toplam 50 dk bekler.

    bekleyici(saniye) -> (rc, cikti); sure dolunca subprocess.TimeoutExpired firlatir.
    Bu ayrim testte sahte bekleyiciyle saniye beklemeden olculur.
    """
    kisa_tavan = TUR_ZAMAN_ASIMI_SN if kisa_tavan is None else kisa_tavan
    uzun_tavan = (TUR_ONARIM_ZAMAN_ASIMI_SN if uzun_tavan is None else uzun_tavan)
    try:
        return bekleyici(kisa_tavan)
    except subprocess.TimeoutExpired as hata:
        cikti = hata.output or b""
        if not onarim_ilerliyor_mu(cikti):
            return _sure_tavani_sonucu(cikti, sonlandirici, kisa_tavan)
    kalan = max(0, uzun_tavan - kisa_tavan)
    try:
        return bekleyici(kalan)
    except subprocess.TimeoutExpired as hata:
        return _sure_tavani_sonucu(hata.output or cikti, sonlandirici, uzun_tavan)
'''

I3B_YENI = '''def _sureli_isci_bekle(bekleyici, sonlandirici, kisa_tavan=None, uzun_tavan=None,
                       tur_cikti_yolu=None):
    """Isciyi 25 dk; onarim ilerleme izi varsa toplam 50 dk bekler.

    bekleyici(saniye) -> (rc, cikti); sure dolunca subprocess.TimeoutExpired firlatir.
    Bu ayrim testte sahte bekleyiciyle saniye beklemeden olculur.
    B7: `tur_cikti_yolu` tavan asiminda son-50 teshisinin KAYNAGIDIR; kolun
    kendisi degismez, yalnizca hukme kanit eklenir.
    """
    kisa_tavan = TUR_ZAMAN_ASIMI_SN if kisa_tavan is None else kisa_tavan
    uzun_tavan = (TUR_ONARIM_ZAMAN_ASIMI_SN if uzun_tavan is None else uzun_tavan)
    try:
        return bekleyici(kisa_tavan)
    except subprocess.TimeoutExpired as hata:
        cikti = hata.output or b""
        if not onarim_ilerliyor_mu(cikti):
            return _sure_tavani_sonucu(cikti, sonlandirici, kisa_tavan,
                                       tur_cikti_yolu)
    kalan = max(0, uzun_tavan - kisa_tavan)
    try:
        return bekleyici(kalan)
    except subprocess.TimeoutExpired as hata:
        return _sure_tavani_sonucu(hata.output or cikti, sonlandirici, uzun_tavan,
                                   tur_cikti_yolu)
'''


# ---------------------------------------------------------------------------
# I4 — tur ortami
# ---------------------------------------------------------------------------

I4_ESKI = '''def _nobet_turunu_kos(motor):
    """Nobet turunu durum-bagli tavanla kosar (motor ortami TEK kaynak: isci.sh)."""
    ortam = dict(os.environ)
    ortam["PRUVO_ISCI_BAGLAM"] = "kapali"   # nobet ISCI degil, TAMIRCI kimligidir
    surec = subprocess.Popen(
        [ISCI_SH, motor, EV_KOKU, GOREV_YOLU, "ci-nobeti"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, env=ortam, start_new_session=True,
    )

    def _bekle(zaman_asimi):
        cikti, _ = surec.communicate(timeout=zaman_asimi)
        return surec.returncode, _metne_cevir(cikti)

    return _sureli_isci_bekle(_bekle, lambda: _surec_grubunu_sonlandir(surec))
'''

I4_YENI = '''def _nobet_turunu_kos(motor):
    """Nobet turunu durum-bagli tavanla kosar (motor ortami TEK kaynak: isci.sh).

    B7: turun IZOLE cikti yolu BURADA uretilir ve ONCEDEN isciye verilir.
    Sebep: tavan asiminda surec OLDURULUR; yolu sonradan ogrenmenin yolu yok.
    """
    ortam = dict(os.environ)
    ortam["PRUVO_ISCI_BAGLAM"] = "kapali"   # nobet ISCI degil, TAMIRCI kimligidir
    tur_cikti = tur_cikti_yolu_uret("ci-nobeti")
    try:
        os.makedirs(TUR_CIKTI_DIZINI, exist_ok=True)
    except OSError:
        pass                                # fail-open: isci.sh kendi fallback'ine duser
    ortam["PRUVO_ISCI_TUR_CIKTI"] = tur_cikti
    print("TUR_CIKTI=%s" % tur_cikti)
    sys.stdout.flush()
    surec = subprocess.Popen(
        [ISCI_SH, motor, EV_KOKU, GOREV_YOLU, "ci-nobeti"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, env=ortam, start_new_session=True,
    )

    def _bekle(zaman_asimi):
        cikti, _ = surec.communicate(timeout=zaman_asimi)
        return surec.returncode, _metne_cevir(cikti)

    return _sureli_isci_bekle(_bekle, lambda: _surec_grubunu_sonlandir(surec),
                              tur_cikti_yolu=tur_cikti)
'''


# ---------------------------------------------------------------------------
# yardimcilar
# ---------------------------------------------------------------------------

def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(metin)


def yedekle(yol, damga):
    hedef = "%s.yedek-b7-%s" % (yol, damga)
    if not os.path.exists(hedef):
        shutil.copy2(yol, hedef)
    return hedef


def ekle_sonra(metin, ankor, yeni):
    """Ankor satirindan SONRA `yeni` ekler. (metin, uygulandi_mi)."""
    if yeni.strip() and yeni.strip().splitlines()[0] in metin:
        return metin, False
    if ankor not in metin:
        return metin, None                  # ankor YOK -> olculemedi
    return metin.replace(ankor, ankor + yeni, 1), True


def degistir(metin, eski, yeni):
    """Tam blok degisimi. (metin, uygulandi_mi)."""
    if yeni in metin:
        return metin, False                 # zaten uygulanmis
    if eski not in metin:
        return metin, None                  # ankor YOK -> olculemedi
    return metin.replace(eski, yeni, 1), True


def testler_kaydet(metin):
    """testler.py PAKETLER listesine test paketini EKLER (cagri yeri)."""
    if TEST_ADI in metin:
        return metin, False
    ankor = '    "kilit-tatbikat.py",\n'
    if ankor not in metin:
        return metin, None
    return metin.replace(ankor, ankor + '    "%s",\n' % TEST_ADI, 1), True


DURUM_ADLARI = {True: "UYGULANDI", False: "ZATEN_VARDI", None: "ANKOR_YOK"}


def olc():
    """Yalniz OLCER: her yamanin bugunku hali (yazma YOK)."""
    satirlar = []
    try:
        isci = oku(ISCI_SH)
        kapi = oku(NOBET_KAPI)
        tst = oku(TESTLER)
    except OSError as hata:
        print("HUKUM=OLCULEMEDI sebep=%s" % hata)
        return 2
    olculer = [
        ("I1a isci.sh TUR_CIKTI kurulumu", MARKER in isci),
        ("I1b isci.sh TUR_CIKTI baglanti satiri", 'echo "TUR_CIKTI=$TUR_CIKTI"' in isci),
        ("I1c isci.sh tee hedefi", '"$CIKTI_DOSYASI" "$TUR_CIKTI"' in isci),
        ("I1d isci.sh budama", "B7_ESKILER" in isci),
        ("I2a nobet-kapi sabitleri", "TUR_CIKTI_DIZINI" in kapi),
        ("I2b nobet-kapi yardimcilari", "_tur_son_blogu" in kapi),
        ("I3a son-50 hukme ekleniyor", "_tur_son_blogu(tur_cikti_yolu)" in kapi),
        ("I3b yol tasiniyor", "tur_cikti_yolu=tur_cikti" in kapi),
        ("I4 tur ortami", "PRUVO_ISCI_TUR_CIKTI" in kapi),
        ("T1 kabul bataryasi kuruldu", os.path.isfile(TEST_HEDEF)),
        ("T2 testler.py'ye kayitli (CAGRI YERI)", TEST_ADI in tst),
    ]
    kurulu = 0
    for ad, var in olculer:
        satirlar.append("YAMA=%-42s DURUM=%s" % (ad, "VAR" if var else "YOK"))
        kurulu += 1 if var else 0
    print("\n".join(satirlar))
    print("B7_KURULU=%d/%d" % (kurulu, len(olculer)))
    print("HUKUM=%s" % ("KURULU" if kurulu == len(olculer) else "EKSIK"))
    return 0 if kurulu == len(olculer) else 1


def uygula():
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rapor = []

    # --- isci.sh ---
    isci = oku(ISCI_SH)
    yedek_isci = yedekle(ISCI_SH, damga)
    isci, d = ekle_sonra(isci, I1A_ANKOR, I1A_YENI)
    rapor.append(("I1a TUR_CIKTI kurulumu", d))
    isci, d = ekle_sonra(isci, I1B_ANKOR, I1B_YENI)
    rapor.append(("I1b baglanti satiri", d))
    if I1C_YENI in isci:
        rapor.append(("I1c tee hedefi", False))
    elif I1C_ESKI in isci:
        sayi = isci.count(I1C_ESKI)
        isci = isci.replace(I1C_ESKI, I1C_YENI)
        rapor.append(("I1c tee hedefi (x%d)" % sayi, True))
    else:
        rapor.append(("I1c tee hedefi", None))
    isci, d = ekle_sonra(isci, I1D_ANKOR, I1D_YENI)
    rapor.append(("I1d budama", d))
    yaz(ISCI_SH, isci)

    # --- nobet-kapi.py ---
    kapi = oku(NOBET_KAPI)
    yedek_kapi = yedekle(NOBET_KAPI, damga)
    kapi, d = ekle_sonra(kapi, I2A_ANKOR, I2A_YENI)
    rapor.append(("I2a sabitler", d))
    if "_tur_son_blogu" in kapi:
        rapor.append(("I2b yardimcilar", False))
    elif I2B_ANKOR in kapi:
        kapi = kapi.replace(I2B_ANKOR, I2B_YENI + I2B_ANKOR, 1)
        rapor.append(("I2b yardimcilar", True))
    else:
        rapor.append(("I2b yardimcilar", None))
    kapi, d = degistir(kapi, I3A_ESKI, I3A_YENI)
    rapor.append(("I3a son-50 hukme", d))
    kapi, d = degistir(kapi, I3B_ESKI, I3B_YENI)
    rapor.append(("I3b yol tasima", d))
    kapi, d = degistir(kapi, I4_ESKI, I4_YENI)
    rapor.append(("I4 tur ortami", d))
    yaz(NOBET_KAPI, kapi)

    # --- kabul bataryasi + CAGRI YERI ---
    if os.path.isfile(TEST_KAYNAK):
        shutil.copy2(TEST_KAYNAK, TEST_HEDEF)
        os.chmod(TEST_HEDEF, 0o755)
        rapor.append(("T1 batarya kuruldu", True))
    else:
        rapor.append(("T1 batarya kuruldu", None))
    tst = oku(TESTLER)
    yedek_tst = yedekle(TESTLER, damga)
    tst, d = testler_kaydet(tst)
    rapor.append(("T2 testler.py kaydi", d))
    yaz(TESTLER, tst)

    for ad, durum in rapor:
        print("YAMA=%-32s SONUC=%s" % (ad, DURUM_ADLARI[durum]))
    ankorsuz = sum(1 for _, d in rapor if d is None)
    print("YEDEK=%s" % yedek_isci)
    print("YEDEK=%s" % yedek_kapi)
    print("YEDEK=%s" % yedek_tst)
    print("DAMGA=%s" % damga)
    print("ANKORSUZ=%d" % ankorsuz)
    print("HUKUM=%s" % ("UYGULANDI" if ankorsuz == 0 else "ANKOR_YOK"))
    return 0 if ankorsuz == 0 else 1


def geri_al(damga):
    n = 0
    for yol in (ISCI_SH, NOBET_KAPI, TESTLER):
        yedek = "%s.yedek-b7-%s" % (yol, damga)
        if os.path.isfile(yedek):
            shutil.copy2(yedek, yol)
            n += 1
            print("GERI_ALINDI=%s" % yol)
    print("GERI_ALINAN=%d" % n)
    return 0 if n else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="B7 kurucu (nobet tur izolasyonu)")
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--geri-al", metavar="DAMGA")
    args = ap.parse_args(argv)
    if args.geri_al:
        return geri_al(args.geri_al)
    if args.uygula:
        rc = uygula()
        print("--- KURULUM SONRASI OLCUM ---")
        olc()
        return rc
    return olc()


if __name__ == "__main__":
    sys.exit(main())
