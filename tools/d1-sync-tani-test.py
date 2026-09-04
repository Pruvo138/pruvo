#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""d1-sync.py `wrangler()` KABUL BATARYASI — hata tanisi + ZAMAN ASIMI + TEK UCUS.

  python3 tools/d1-sync-tani-test.py                 # CANLI govde
  python3 tools/d1-sync-tani-test.py --govde <yol>   # MUTANT govde (mutasyon turu)
  python3 tools/d1-sync-tani-test.py --kilit-tut <yol> --saniye N   # yardimci alt surec

D1'e ve aga DOKUNMAZ: hicbir vaka gercek `npx` calistirmaz. Gercek alt surec kullanan
vakalar (zaman asimi / mesru yavas kosum) `python3 -c "time.sleep(...)"` calistirir.

🔴 KILIT SENTETIK KOKTE: `wrangler()` artik TEK UCUS icin flock aliyor. Batarya
CANLI repo'nun `.git/config` inode'unu MESGUL ETMEZ — her vaka `git init`li gecici bir
kok kurar ve modulun `KOK`unu oraya cevirir; boylece batarya ne baska bir oturumun D1
yazicisini bloklar ne de onun tarafindan bloklanir.

TARIHCE:
  * (31 Tem) wrangler hata tanisi regresyonu — 3 vaka; KORUNDU.
  * (4 Eyl, K361) ZAMAN ASIMI + TEK UCUS. Olculen ariza: `subprocess.run` cagrisinda
    `timeout` YOKTU; asilan kosum sifir ciktiyla SONSUZA bekliyordu, makinede 7 asili
    `npm exec wrangler@4` birikti ve yayin 3 commit boyunca durdu — kanca yolunda
    SESSIZ hata.
"""
import argparse
import fcntl
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, BURASI)

# 🔴 OLCULEN MESRU (rc=0) WRANGLER KOSUM SURELERI — 4 Eyl 2026, bu makine, GERCEK D1 ucu.
# Tavan/taban/bekleme sabitleri bu sayilarin UZERINDE olmak ZORUNDA; altina inen bir sabit
# MESRU kosumu keser ve koruma korudugu yayini durdurur
# ([[koruma-kurali-korudugunu-durdurur]]). Batarya bunu B10/B11/C8 ile CIVILER.
# 🔴 EN YAVAS BASARILI KOSUM PAYLASILAN CACHE'TEN GELDI (364,0 sn) — yalnizca ozel
# cache olcumune bakan bir sabit (307,1) BUGUN OLCULEN mesru bir kosumu keserdi. Sabit,
# olcum geldikce YUKARI cekildi; tek turdan hukum verilmedi
# ([[tek-turdan-hukum-verme-anomali-kolu]]).
OLCULEN_MESRU_SURELER = (
    307.1, 140.0, 79.6, 11.1,   # OZEL npm cache — 4/4 rc=0
    364.0, 56.6,                # PAYLASILAN npm cache — 2/5 rc=0 (3/5 sondada kesildi)
    173.7,                      # mimar olcumu (ozel cache, soguk indirme)
)
OLCULEN_MESRU_EN_YAVAS = max(OLCULEN_MESRU_SURELER)  # 364.0 sn

# 🔴 4 EYL 2026 (BaBa emri) — POPULASYON IKIYE AYRILDI. Her cagri artik KALICI OZEL npm
# cache ile kosar; paylasilan cache (ve onun 364,0 sn'lik serilesme kuyrugu) TERK EDILDI.
# Yukaridaki dizi TARIHSEL KAYIT olarak DURUR (silinmedi) ama artik canli tavani BAGLAMAZ;
# bagladigi tek sey OKUYUCU_BEKLEME_SN'dir (C8 — o kol hala paylasilan makineyi bekler).
OLCULEN_ISINMIS_SURELER = (11.1, 1.5, 1.5)          # ozel cache DOLU iken
OLCULEN_SOGUK_SURELER = (307.1, 173.7, 140.0, 79.6, 27.9)   # cache DOLDURULURKEN
OLCULEN_ISINMIS_EN_YAVAS = max(OLCULEN_ISINMIS_SURELER)     # 11.1 sn
OLCULEN_SOGUK_EN_YAVAS = max(OLCULEN_SOGUK_SURELER)         # 307.1 sn

gecen = [0]
kalan = [0]
dusenler = []


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        dusenler.append(ad)
        print("  KALDI " + ad + (" — " + detay if detay else ""))


# ── SENTETIK KOK (flock CANLI .git/config'e DOKUNMASIN) ─────────────────────────────
def sentetik_kok_kur():
    kok = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-d1-tani-"))
    p = subprocess.run(["git", "init", "-q", kok], capture_output=True, text=True)
    if p.returncode != 0 or not os.path.isfile(os.path.join(kok, ".git", "config")):
        shutil.rmtree(kok, ignore_errors=True)
        raise SystemExit("!! SENTETIK KOK KURULAMADI (git init rc=%s) — batarya "
                         "OLCEMEZ, fail-closed." % p.returncode)
    return kok


def govde_yukle(govde_yolu):
    """d1-sync.py'yi (canli ya da mutant) yukle. Mutant SENTETIK tools/ altinda durur."""
    spec = importlib.util.spec_from_file_location("d1_sync_tani_govde", govde_yolu)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── SAHTE ALT SURECLER ──────────────────────────────────────────────────────────────
class Sonuc:
    def __init__(self, kod, stdout="", stderr=""):
        self.returncode = kod
        self.stdout = stdout
        self.stderr = stderr


def sayacli_sahte(sonuclar):
    """subprocess.run yerine gececek sahte; (fn, cagri_sayaci, kwargs_kaydi) dondur."""
    cagri = [0]
    kwargs_kaydi = []

    def sahte_run(*args, **kwargs):
        i = min(cagri[0], len(sonuclar) - 1)
        cagri[0] += 1
        kwargs_kaydi.append(kwargs)
        if isinstance(sonuclar[i], BaseException):
            raise sonuclar[i]
        return sonuclar[i]

    return sahte_run, cagri, kwargs_kaydi


def gercek_surec_sahtesi(kod_satirlari, ek_argv=()):
    """subprocess.run'i GERCEK bir alt surece yonlendirir (komut degisir, mekanik AYNI).

    `timeout`/`capture_output` gibi kwargs OLDUGU GIBI gecirilir — yani zaman asimi
    mekanigi GERCEKTEN olculur, taklit edilmez.
    """
    gercek_run = subprocess.run
    cagri = [0]
    kwargs_kaydi = []

    def sahte_run(komut, **kwargs):
        cagri[0] += 1
        kwargs_kaydi.append(kwargs)
        kwargs.pop("cwd", None)
        yeni = [sys.executable, "-c", "\n".join(kod_satirlari)] + list(ek_argv)
        return gercek_run(yeni, **kwargs)

    return sahte_run, cagri, kwargs_kaydi


def kosumu_calistir(D1, sahte_run, cagri_fn=None):
    """D1.wrangler'i sahte alt surecle kostur; (sonuc_ya_da_mesaj, patladi_mi) dondur."""
    eski_run, eski_sleep = D1.subprocess.run, D1.time.sleep
    D1.subprocess.run, D1.time.sleep = sahte_run, lambda saniye: None
    try:
        try:
            return (cagri_fn or (lambda: D1.wrangler(["--command", "SELECT 1"])))(), False
        except SystemExit as e:
            return str(e.code), True
        except BaseException as e:                                # noqa: BLE001
            # Mutant govde ciplak bir istisna sizdirirsa batarya COKMEZ, KIRMIZI olur:
            # "mutant olduremedi" ile "batarya coktu" ayirt edilebilsin
            # ([[mutant-kopyasi-cokerse-izin-okunur]]).
            return "!! CIPLAK ISTISNA SIZDI: %s: %s" % (type(e).__name__, e), False
    finally:
        D1.subprocess.run, D1.time.sleep = eski_run, eski_sleep


# ── KOL A — MEVCUT HATA TANISI (31 Tem regresyonu; DAVRANIS DEGISMEDI) ──────────────
def kol_a_tani(D1):
    sahte, cagri, _ = sayacli_sahte(
        [Sonuc(1, stderr="getaddrinfo ENOTFOUND registry.npmjs.org")])
    mesaj, patladi = kosumu_calistir(D1, sahte)
    dogrula("A1 gecici hata -> 3 deneme + dogru tani",
            patladi and cagri[0] == 3 and "GECICI HATA, yeniden dene" in mesaj,
            "cagri=%d mesaj=%r" % (cagri[0], mesaj))

    sahte, cagri, _ = sayacli_sahte([
        Sonuc(1, stderr="Authentication error [code: 10000]"),
        Sonuc(0, stdout='[{"results": [], "success": true}]'),
    ])
    sonuc, patladi = kosumu_calistir(D1, sahte)
    # 🔴 A1c: 10043 — CANLI olculen vaka (4 Eyl). Kod kovada DEGILKEN tani None donuyor
    #   ve retry HIC yapilmiyordu; ayni komut degisiklik olmadan ikinci kosumda rc=0
    #   verdi (51 satir, geri-okuma 51/51). Vaka bu kovayi CIVILER.
    _tani_10043 = D1.wrangler_hata_tanisi(
        'get: Please look at https://www.cloudflarestatus.com for issues or contact '
        'customer support. (10043)\n{"error": {"text": "... \"code\": 10043"}}')
    dogrula("A1c 10043 (Cloudflare SERVIS hatasi) -> GECICI (retry edilir)",
            _tani_10043 == "gecici", "tani=%r" % _tani_10043)
    # NEGATIF: kova genislemesin — alakasiz bir kod GECICI sayilmamali, yoksa kalici
    # ariza sonsuz retry'a girer ve teshis GECIKIR.
    _tani_yabanci = D1.wrangler_hata_tanisi('{"error": {"code": 10099}}')
    dogrula("A1d NEGATIF: kovada OLMAYAN kod (10099) GECICI SAYILMAZ",
            _tani_yabanci is None, "tani=%r" % _tani_yabanci)
    dogrula("A2 gecici 10000 -> retry ile basari",
            (not patladi) and cagri[0] == 2
            and sonuc == [{"results": [], "success": True}],
            "cagri=%d sonuc=%r" % (cagri[0], sonuc))

    sahte, cagri, _ = sayacli_sahte([Sonuc(1, stderr="Authentication error [code: 10000]")])
    mesaj, patladi = kosumu_calistir(D1, sahte)
    dogrula("A3 gercek auth -> 2 retry + GERCEK 10000",
            patladi and cagri[0] == 3 and "GERCEK 10000 - auth" in mesaj,
            "cagri=%d mesaj=%r" % (cagri[0], mesaj))

    sahte, cagri, _ = sayacli_sahte([Sonuc(0, stdout='[{"results": [], "success": true}]')])
    sonuc, patladi = kosumu_calistir(D1, sahte)
    dogrula("A4 basarili JSON -> eski davranis",
            (not patladi) and cagri[0] == 1
            and sonuc == [{"results": [], "success": True}],
            "cagri=%d sonuc=%r" % (cagri[0], sonuc))


# ── KOL B — ZAMAN ASIMI (fail-loud) ─────────────────────────────────────────────────
# "Asilan" alt surec: nabiz atar ve KENDILIGINDEN bitmez... ama SINIRLIDIR.
# 🔴 NEDEN SONSUZ DEGIL: mutasyon turunda `timeout=` kaldirilmis bir govde bu vakayi
# kosarsa, sonsuz bir cocuk BATARYAYI kilitlerdi ve mutant "olduremedi" mi yoksa
# "batarya asildi" mi ayirt edilemezdi. 25 sn, 2 sn'lik test tavaninin 12 katidir —
# canli kolda kesinlikle kesilir, mutant kolda ise vaka SESSIZ degil KIRMIZI duser.
ASILAN_KOD = [
    "import sys, time",
    "yol = sys.argv[1]",
    "bitis = time.time() + 25",
    "while time.time() < bitis:",
    "    f = open(yol, 'w')",
    "    f.write(str(time.time()))",
    "    f.close()",
    "    time.sleep(0.2)",
]
KISA_KOD = ["import time", "time.sleep(1.0)"]


def kol_b_zaman_asimi(D1, gecici_dizin):
    # B1-B6: GERCEKTEN asilan alt surec, tavan 2 sn'ye cekilmis.
    nabiz = os.path.join(gecici_dizin, "nabiz.txt")
    sahte, cagri, kwargs_kaydi = gercek_surec_sahtesi(ASILAN_KOD, ek_argv=(nabiz,))
    eski_tavan = D1.wrangler_tavani
    D1.wrangler_tavani = lambda: 2
    t0 = time.monotonic()
    try:
        mesaj, patladi = kosumu_calistir(D1, sahte)
    finally:
        D1.wrangler_tavani = eski_tavan
    gecen_sn = time.monotonic() - t0

    dogrula("B1 asilan alt surec -> TAVANDA SESLI DUSER",
            patladi and "WRANGLER ZAMAN ASIMI" in str(mesaj),
            "patladi=%s mesaj=%r" % (patladi, str(mesaj)[:200]))
    # Metin, TAKLIT alt sureci degil GERCEK wrangler komutunu tasimali: teshisi okuyan
    # kisi hangi cagrinin asildigini gormeli.
    dogrula("B2 red metni KOMUTU adiyla tasir",
            patladi and "KOMUT:" in str(mesaj)
            and "npx --yes wrangler@4 d1 execute" in str(mesaj),
            str(mesaj)[:200])
    dogrula("B3 red metni SURE + TAVAN sayisini tasir",
            patladi and "tavan=2 sn" in str(mesaj) and " sn boyunca" in str(mesaj),
            str(mesaj)[:200])
    dogrula("B4 red metni NE YAPILMALI + teshis komutunu tasir",
            patladi and "NE YAPILMALI" in str(mesaj)
            and "npm exec wrangler" in str(mesaj), str(mesaj)[:300])
    dogrula("B5 zaman asimi YENIDEN DENENMEZ (tek alt surec)",
            cagri[0] == 1, "cagri=%d" % cagri[0])
    dogrula("B6 tavan GERCEKTEN subprocess.run'a gecti",
            bool(kwargs_kaydi) and kwargs_kaydi[0].get("timeout") == 2,
            repr(kwargs_kaydi[:1]))

    # Asilan cocuk GERCEKTEN olduruldu mu? Nabiz dosyasi ilerlemeyi DURDURMALI.
    olcum1 = os.path.getmtime(nabiz) if os.path.exists(nabiz) else None
    time.sleep(1.2)
    olcum2 = os.path.getmtime(nabiz) if os.path.exists(nabiz) else None
    dogrula("B7 asilan alt surec OLDURULDU (nabiz durdu)",
            olcum1 is not None and olcum2 == olcum1,
            "nabiz1=%s nabiz2=%s" % (olcum1, olcum2))
    dogrula("B8 tavan asimi hizli kesildi (tavanin ~2 kati icinde)",
            gecen_sn < 8.0, "gecen=%.1fsn" % gecen_sn)

    # B9 POZITIF NOBETCI — MESRU YAVAS KOSUM KESILMEZ.
    sahte, cagri, _ = gercek_surec_sahtesi(KISA_KOD)
    D1.wrangler_tavani = lambda: 20
    try:
        mesaj, patladi = kosumu_calistir(D1, sahte)
    finally:
        D1.wrangler_tavani = eski_tavan
    # Alt surec rc=0 ama JSON basmaz -> cozucu "cikti vermedi" der. Onemli olan:
    # ZAMAN ASIMI DEGIL. Kesilseydi mesaj "WRANGLER ZAMAN ASIMI" olurdu.
    dogrula("B9 MESRU (tavan alti) kosum KESILMEZ — zaman asimi TETIKLENMEZ",
            "WRANGLER ZAMAN ASIMI" not in str(mesaj) and cagri[0] >= 1,
            "mesaj=%r" % str(mesaj)[:200])

    # B10-B13 SABIT EKSENI — tavan/taban OLCULEN mesru maksimumun UZERINDE mi?
    # 🔴 4 Eyl: populasyon IKIYE ayrildi (ozel cache ISINMIS / SOGUK). Her kol KENDI
    #   olculen maksimumuyla civilenir; tek bir sayiya bakan eski eksen, soguk kolu
    #   isinmis tavanla olcerdi (ya da tersi) ve MESRU kosumu keserdi.
    dogrula("B10 ISINMIS tavan, isinmis populasyonun en yavasinin (%.1fsn) UZERINDE"
            % OLCULEN_ISINMIS_EN_YAVAS,
            D1.WRANGLER_TAVAN_SN > OLCULEN_ISINMIS_EN_YAVAS,
            "tavan=%s" % D1.WRANGLER_TAVAN_SN)
    dogrula("B11 ISINMIS TABAN da o maksimumun UZERINDE",
            D1.WRANGLER_TAVAN_TABANI > OLCULEN_ISINMIS_EN_YAVAS,
            "taban=%s" % D1.WRANGLER_TAVAN_TABANI)
    dogrula("B10b SOGUK tavan, soguk populasyonun en yavasinin (%.1fsn) UZERINDE"
            % OLCULEN_SOGUK_EN_YAVAS,
            D1.WRANGLER_SOGUK_TAVAN_SN > OLCULEN_SOGUK_EN_YAVAS,
            "soguk_tavan=%s" % D1.WRANGLER_SOGUK_TAVAN_SN)
    # 🔴 KOL SECIMI GERCEKTEN CACHE'E BAGLI MI? (mutantsiz iddia OLU olurdu: iki sabit
    #   de dogru olabilir ama fonksiyon hep ayni kolu dondurebilirdi.)
    _gercek_isinmis = D1.npm_cache_isinmis
    try:
        D1.npm_cache_isinmis = lambda: False
        _soguk_donen = D1.wrangler_tavani()
        D1.npm_cache_isinmis = lambda: True
        _isinmis_donen = D1.wrangler_tavani()
    finally:
        D1.npm_cache_isinmis = _gercek_isinmis
    dogrula("B10c SOGUK cache -> GENIS tavan, ISINMIS cache -> DAR tavan (kol GERCEKTEN "
            "cache'e bagli)",
            _soguk_donen == D1.WRANGLER_SOGUK_TAVAN_SN
            and _isinmis_donen == D1.WRANGLER_TAVAN_SN
            and _soguk_donen > _isinmis_donen,
            "soguk=%s isinmis=%s" % (_soguk_donen, _isinmis_donen))

    eski_env = os.environ.get("PRUVO_WRANGLER_TAVAN_SN")
    try:
        os.environ["PRUVO_WRANGLER_TAVAN_SN"] = "5"
        dogrula("B12 env tavani TABANIN ALTINA INDIREMEZ",
                D1.wrangler_tavani() == D1.WRANGLER_TAVAN_TABANI,
                "tavan=%s" % D1.wrangler_tavani())
        os.environ["PRUVO_WRANGLER_TAVAN_SN"] = "1200"
        dogrula("B13 env tavani YUKARI cekebilir",
                D1.wrangler_tavani() == 1200, "tavan=%s" % D1.wrangler_tavani())
        os.environ["PRUVO_WRANGLER_TAVAN_SN"] = "abc"
        dogrula("B14 cop env -> varsayilana duser (sessiz sifira DEGIL)",
                D1.wrangler_tavani() == D1.WRANGLER_TAVAN_SN,
                "tavan=%s" % D1.wrangler_tavani())
    finally:
        if eski_env is None:
            os.environ.pop("PRUVO_WRANGLER_TAVAN_SN", None)
        else:
            os.environ["PRUVO_WRANGLER_TAVAN_SN"] = eski_env


# ── KOL C — TEK UCUS ────────────────────────────────────────────────────────────────
def kilit_tutan_alt_surec(kilit_yolu, saniye):
    """Yardimci: kilidi `saniye` boyunca TUT (ana test bunu alt surec olarak acar)."""
    fd = open(kilit_yolu, "r+")
    fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
    sys.stdout.write("TUTTUM\n")
    sys.stdout.flush()
    time.sleep(saniye)
    fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    fd.close()
    return 0


def _tutucu_ac(kilit_yolu, saniye):
    p = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--kilit-tut", kilit_yolu,
         "--saniye", str(saniye)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # "TUTTUM" gelene kadar bekle: yaris yok, kilit GERCEKTEN tutuluyor.
    satir = p.stdout.readline()
    return p, satir.strip() == "TUTTUM"


def kol_c_tek_ucus(D1):
    kilit_yolu = D1.yazici_kilit_yolu()

    # C1-C4: kilit BASKA surecte tutuluyorken cagri MESGUL demeli, npx CALISMAMALI.
    eski_bekleme = D1.OKUYUCU_BEKLEME_SN
    D1.OKUYUCU_BEKLEME_SN = 1.5
    tutucu, tuttu = _tutucu_ac(kilit_yolu, 12)
    try:
        dogrula("C1 yardimci surec kilidi GERCEKTEN tuttu (fikstur saglam)", tuttu)
        sahte, cagri, _ = sayacli_sahte([Sonuc(0, stdout='[{"results": [], "success": true}]')])
        yakalanan = []
        eski_stderr = sys.stderr
        sys.stderr = _YakalayanAkis(yakalanan)
        try:
            mesaj, patladi = kosumu_calistir(D1, sahte)
        finally:
            sys.stderr = eski_stderr
        stderr_metni = "".join(yakalanan)
        dogrula("C2 MESGUL kolu SESLI duser (ikinci cagri yiginI buyutmez)",
                patladi and "D1 ARACI MESGUL" in str(mesaj),
                "patladi=%s mesaj=%r" % (patladi, str(mesaj)[:200]))
        dogrula("C3 npx HIC CALISTIRILMADI (yigina EKLENMEDI)",
                cagri[0] == 0, "cagri=%d" % cagri[0])
        dogrula("C4 BEKLEME SESSIZ DEGIL — stderr'e adiyla duyuruldu",
                "BEKLENIYOR" in stderr_metni, repr(stderr_metni[:200]))
    finally:
        tutucu.kill()
        tutucu.wait(timeout=10)
        D1.OKUYUCU_BEKLEME_SN = eski_bekleme

    # C5 POZITIF NOBETCI: kilit SERBESTKEN cagri normal GECER.
    sahte, cagri, _ = sayacli_sahte([Sonuc(0, stdout='[{"results": [], "success": true}]')])
    sonuc, patladi = kosumu_calistir(D1, sahte)
    dogrula("C5 kilit SERBESTken cagri GECER ve npx 1 kez kosar",
            (not patladi) and cagri[0] == 1
            and sonuc == [{"results": [], "success": True}],
            "patladi=%s cagri=%d" % (patladi, cagri[0]))

    # C6: kilidi ZATEN tutan surec (yazici kolu) kendini KILITLEMEZ.
    tutucu, tuttu = _tutucu_ac(kilit_yolu, 8)
    eski_sahiplik = D1._YEREL_KILIT_SAHIBI
    D1._YEREL_KILIT_SAHIBI = True
    try:
        sahte, cagri, _ = sayacli_sahte([Sonuc(0, stdout='[{"results": [], "success": true}]')])
        t0 = time.monotonic()
        sonuc, patladi = kosumu_calistir(D1, sahte)
        sure = time.monotonic() - t0
        dogrula("C6 kilidi ZATEN tutan surec kendini KILITLEMEZ (deadlock yok)",
                (not patladi) and cagri[0] == 1 and sure < 3.0,
                "patladi=%s cagri=%d sure=%.2f" % (patladi, cagri[0], sure))
    finally:
        D1._YEREL_KILIT_SAHIBI = eski_sahiplik
        tutucu.kill()
        tutucu.wait(timeout=10)

    # C7: YAZICI kolunun ESKI davranisi BAYT AYNI — beklemez, aninda fail-closed.
    tutucu, tuttu = _tutucu_ac(kilit_yolu, 8)
    try:
        t0 = time.monotonic()
        try:
            fd = D1.yazici_kilidi_al(kilit_yolu)
            D1.yazici_kilidi_birak(fd)
            yazici_mesaj, yazici_patladi = "", False
        except SystemExit as e:
            yazici_mesaj, yazici_patladi = str(e.code), True
        yazici_sure = time.monotonic() - t0
        dogrula("C7 YAZICI kolu DEGISMEDI — beklemez, 'D1 YAZICI UCUSTA' der",
                yazici_patladi and "D1 YAZICI UCUSTA" in yazici_mesaj
                and yazici_sure < 2.0,
                "patladi=%s sure=%.2f mesaj=%r"
                % (yazici_patladi, yazici_sure, yazici_mesaj[:160]))
    finally:
        tutucu.kill()
        tutucu.wait(timeout=10)

    # C8: bekleme tavani da OLCULEN mesru maksimumun UZERINDE (mesru oncul beklenebilsin).
    dogrula("C8 bekleme tavani olculen en yavas MESRU kosumun UZERINDE",
            D1.OKUYUCU_BEKLEME_SN > OLCULEN_MESRU_EN_YAVAS,
            "bekleme=%s" % D1.OKUYUCU_BEKLEME_SN)

    # C9: yazici/salt-okuma siniflandirmasi DEGISMEDI (komsu kapinin capasi).
    def kip(**degisen):
        temel = dict(kendini=False, bayatlik=False, seq_normalize=False,
                     sema=False, durum=False, kuru=False)
        temel.update(degisen)
        return argparse.Namespace(**temel)

    yazicilar = [kip(), kip(sema=True), kip(seq_normalize=True)]
    saltlar = [kip(durum=True), kip(kuru=True), kip(bayatlik=True), kip(kendini=True)]
    dogrula("C9 yazici/salt-okuma siniflandirmasi DEGISMEDI",
            all(D1.yazici_yolu_mu(a) for a in yazicilar)
            and not any(D1.yazici_yolu_mu(a) for a in saltlar))


class _YakalayanAkis:
    def __init__(self, kova):
        self.kova = kova

    def write(self, metin):
        self.kova.append(metin)
        return len(metin)

    def flush(self):
        pass


# ── KOL D — `npx` YOK (cron duzlemi) ────────────────────────────────────────────────
def kol_d_npx_yok(D1):
    sahte, cagri, _ = sayacli_sahte([FileNotFoundError(2, "No such file or directory: 'npx'")])
    mesaj, patladi = kosumu_calistir(D1, sahte)
    dogrula("D1 `npx` yok -> SESLI red (sessiz traceback DEGIL)",
            patladi and "`npx` CALISTIRILAMADI" in str(mesaj),
            "patladi=%s mesaj=%r" % (patladi, str(mesaj)[:200]))
    dogrula("D2 red metni KULLANILAN PATH'i basar",
            patladi and "PATH=" in str(mesaj), str(mesaj)[:200])
    dogrula("D3 red metni ADAY TAM YOLLARI basar (PATH'e sorma dersi)",
            patladi and "ADAY TAM YOLLAR" in str(mesaj), str(mesaj)[:200])
    dogrula("D4 `npx` yok hali YENIDEN DENENMEZ", cagri[0] == 1, "cagri=%d" % cagri[0])


# ── KOL E — DISK (ureten temizler) ──────────────────────────────────────────────────
def kol_e_disk(D1):
    eperm = Sonuc(1, stderr="npm error code EPERM ... /Users/x/.npm/_cacache/tmp")
    basari = Sonuc(0, stdout='[{"results": [], "success": true}]')
    gorulen = []

    gercek_sahte, cagri, kwargs_kaydi = sayacli_sahte([eperm, basari])

    def sahte_run(*args, **kwargs):
        ort = kwargs.get("env") or {}
        if ort.get("npm_config_cache"):
            gorulen.append(ort["npm_config_cache"])
        return gercek_sahte(*args, **kwargs)

    sonuc, patladi = kosumu_calistir(D1, sahte_run)
    try:
        # 🔴 4 Eyl (BaBa emri) SONRASI: her cagri KALICI ozel cache ile kosar, EPERM
        #   kolu ise AYRICA bir GECICI cache acar. Yani `gorulen` artik IKI yol tasir ve
        #   ikisinin OMRU TERSTIR: kalici KALIR, gecici SILINIR. Vaka bunu AYIRIR —
        #   "len==1" beklentisi kalici cache'i gecici sanip yanlis kova uretirdi.
        kalici = [y for y in gorulen if y == D1.NPM_CACHE_DIZINI]
        gecici = [y for y in gorulen if y != D1.NPM_CACHE_DIZINI]
        dogrula("E1 EPERM kolu GECICI npm cache ACTI ve sonuc BASARILI",
                (not patladi) and len(gecici) == 1
                and sonuc == [{"results": [], "success": True}],
                "gecici=%r kalici=%r patladi=%s" % (gecici, kalici, patladi))
        dogrula("E2 acilan GECICI npm cache SILINDI (ureten temizler)",
                bool(gecici) and not os.path.exists(gecici[0]),
                "yol=%r var_mi=%s" % (gecici[:1],
                                      os.path.exists(gecici[0]) if gecici else "?"))
        dogrula("E3 KALICI ozel cache HER cagride kullanildi (paylasilan cache TERK)",
                bool(kalici),
                "kalici=%r (beklenen %s)" % (kalici, D1.NPM_CACHE_DIZINI))
        dogrula("E4 KALICI ozel cache SILINMEDI (gecici ile karistirilmadi)",
                os.path.isdir(D1.NPM_CACHE_DIZINI),
                "var_mi=%s" % os.path.isdir(D1.NPM_CACHE_DIZINI))
    finally:
        # Mutant govde temizligi ATLIYORSA vaka KIRMIZI olur ama artigi BATARYA siler:
        # olcum makinede iz birakmaz ([[diskte-iz-birakma-yasagi]]).
        # 🔴 KALICI cache BU DONGUYE GIRMEZ — batarya kendi disindaki kalici kaynagi silmez.
        for _y in gorulen:
            if _y != D1.NPM_CACHE_DIZINI:
                shutil.rmtree(_y, ignore_errors=True)


# ── ANA ────────────────────────────────────────────────────────────────────────────
def ana(govde_yolu):
    kok = sentetik_kok_kur()
    gecici_dizin = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-d1-tani-is-"))
    try:
        D1 = govde_yukle(govde_yolu)
        # 🔴 KOK sentetige cevrilir: flock CANLI repo'nun .git/config'ine DOKUNMAZ.
        D1.KOK = kok
        # Kilit yolunu SIMDI coz (onbellege gir): `subprocess.run` sahtelenmeden once.
        # Yoksa sahte, kilit yolunu cozen `git rev-parse` cagrisini da yutar ve
        # olctugumuz kol (npx) ile olcmedigimiz kol (git) BIRBIRINE KARISIR.
        kilit_yolu = D1.yazici_kilit_yolu()
        if os.path.dirname(os.path.dirname(kilit_yolu)) != kok:
            raise SystemExit("!! KILIT SENTETIK KOKTE DEGIL (%s) — batarya CANLI repo'yu "
                             "kilitleyebilirdi, fail-closed." % kilit_yolu)
        print("KOL A — hata tanisi (31 Tem regresyonu)")
        kol_a_tani(D1)
        print("KOL B — ZAMAN ASIMI")
        kol_b_zaman_asimi(D1, gecici_dizin)
        print("KOL C — TEK UCUS")
        kol_c_tek_ucus(D1)
        print("KOL D — `npx` YOK (cron duzlemi)")
        kol_d_npx_yok(D1)
        print("KOL E — DISK")
        kol_e_disk(D1)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
        shutil.rmtree(gecici_dizin, ignore_errors=True)

    iddia = gecen[0] + kalan[0]
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (iddia, gecen[0], kalan[0]))
    if dusenler:
        print("DUSENLER=" + ",".join(dusenler))
    print("SONUC: %d/%d" % (gecen[0], iddia))
    return 0 if kalan[0] == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--govde", default=os.path.join(BURASI, "d1-sync.py"),
                    help="olculecek d1-sync.py govdesi (mutasyon turu icin)")
    ap.add_argument("--kilit-tut", default=None, help="(yardimci) kilidi tut")
    ap.add_argument("--saniye", type=float, default=5.0)
    a = ap.parse_args()
    if a.kilit_tut:
        raise SystemExit(kilit_tutan_alt_surec(a.kilit_tut, a.saniye))
    raise SystemExit(ana(a.govde))
