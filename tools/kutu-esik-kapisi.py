#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORTAK POSTA KUTUSU ESİK KAPISI — yazmadan once tavani olcer.

NEDEN VAR (olculdu, 18 Agu 2026): ortak posta kutusu 22:45'te elle rotasyonla
budandiktan 16 dakika sonra 333 satira yeniden tasti. Bu, elle rotasyonun
besinci tekrariydi. Rotasyon aracinda bilinen esik, kutuya yazan PreToolUse
yolunda olculmedigi icin bu kapı yazmadan once esigi kontrol eder.

KAPI SOZLESMESI:
  * JSON bozuksa veya hedef ortak kutu degilse 0 (fail-open).
  * Hedef kutu tavani asiyorsa tools/kutu-arsivle.py yazmadan once cagrilir.
  * Rotasyon sonrasi kutu hala tavani asiyor ya da rotasyon basarisizsa 2.
"""
import argparse
import fcntl
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


TOOLS = os.path.dirname(os.path.abspath(__file__))
ARSIV_ARACI = os.path.join(TOOLS, "kutu-arsivle.py")
IZINLI_ARACLAR = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
KUTU_VARSAYILAN_YOLU = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md")


class _SahteSonuc(object):
    """M2 mutantinin rotasyon cagrisini kaldirdigini gosteren sahte sonuc."""

    returncode = 0
    stdout = ""
    stderr = ""


def arsiv_araci_yolu():
    """Arşiv aracının test kancasını veya üretim yolunu döndür."""
    return os.environ.get("PRUVO_KUTU_ESIK_ARSIV_ARACI", ARSIV_ARACI)


def zaman_asimi_saniyesi():
    """Rotasyon alt süreci için test kancalı timeout değerini döndür."""
    try:
        return float(os.environ.get("PRUVO_KUTU_ESIK_ZAMAN_ASIMI", "60"))
    except (TypeError, ValueError):
        return 60


def arsiv_modulu_yukle(arac_yolu=None):
    """Tavan ve varsayilan kutu yolu icin arşiv aracini modul olarak yukle."""
    arac_yolu = arac_yolu or arsiv_araci_yolu()
    spec = importlib.util.spec_from_file_location("kutu_arsivle_esik_kaynagi",
                                                  arac_yolu)
    if spec is None or spec.loader is None:
        raise ImportError("kutu-arsivle.py modul spec'i olusturulamadi")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def kutu_satir_sayisi(yol):
    """Kutu mevcutsa UTF-8 baytlarini gercek dosya satirlari olarak say."""
    with open(yol, "rb") as dosya:
        return len(dosya.read().decode("utf-8").splitlines())


def kutu_bayt(yol):
    with open(yol, "rb") as dosya:
        return dosya.read()


def ci_ortaminda():
    """GERCEK_KUTU ekseninin KAPSAM_DISI sayilabildigi tek ortam: GitHub runner.

    Yerel kosumda kutu yoksa eksen KIRMIZI kalir (fail-closed korunur);
    runner'da mimar kutusu YAPISAL olarak yoktur, olculemezlik bilgi tasimaz
    (chip-duzeni-kapisi'nin KUTU_KAPSAM_DISI deseni, CI-tespitine daraltilmis).
    """
    return os.environ.get("GITHUB_ACTIONS") == "true"


def hedef_kutu_mu(file_path, kutu_yolu):
    try:
        return os.path.realpath(os.path.expanduser(file_path)) == os.path.realpath(
            os.path.expanduser(kutu_yolu))
    except (AttributeError, TypeError, ValueError):
        return False


def rotasyon_ciktisini_yaz(sonuc):
    """Rotasyon araci ciktisinin son 20 satirini stderr'e ekle."""
    for etiket, metin in (("stdout", getattr(sonuc, "stdout", "")),
                           ("stderr", getattr(sonuc, "stderr", ""))):
        satirlar = (metin or "").splitlines()
        if satirlar:
            sys.stderr.write("rotasyon %s son 20 satir:\n" % etiket)
            sys.stderr.write("\n".join(satirlar[-20:]) + "\n")


def kapidan_gecir(payload, kutu_yolu):
    """Tek bir PreToolUse payload'i icin rc dondur."""
    if not isinstance(payload, dict):
        return 0
    arac = payload.get("tool_name")
    if arac not in IZINLI_ARACLAR:
        return 0
    girdi = payload.get("tool_input")
    if not isinstance(girdi, dict):
        return 0
    file_path = girdi.get("file_path")
    if not file_path or not hedef_kutu_mu(file_path, kutu_yolu):
        return 0

    if not os.path.exists(kutu_yolu):
        # dosya YOK = ilk yaratim; tavan kavrami yok, fail-open MESRU
        return 0

    arsiv_araci = arsiv_araci_yolu()
    try:
        arsiv_mod = arsiv_modulu_yukle(arsiv_araci)
        # ESİK TEK KAYNAK: sabit deger burada yeniden tanimlanmaz.
        tavan = arsiv_mod.VARSAYILAN_TAVAN
    except Exception as hata:
        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): esik kaynagi (%s) "
            "yuklenemedi (%s) -> esik OLCULEMEDI, yazma REDDEDILDI.\n" %
            (arsiv_araci, hata))
        return 2

    try:
        once = kutu_satir_sayisi(kutu_yolu)
    except (OSError, UnicodeDecodeError) as hata:
        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): hedef kutu olculemedi (%s) "
            "-> yazma REDDEDILDI.\n" % hata)
        return 2

    if once <= tavan:
        print("ESIK ALTI satir=%d tavan=%d" % (once, tavan))
        return 0

    try:
        sonuc = subprocess.run(
            [sys.executable, arsiv_araci, "--kutu", kutu_yolu],
            capture_output=True, text=True, timeout=zaman_asimi_saniyesi())
    except (OSError, subprocess.TimeoutExpired) as hata:
        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): rotasyon istisna ile basarisiz "
            "(%s) -> yazma REDDEDILDI.\n" % hata)
        return 2

    try:
        sonra = kutu_satir_sayisi(kutu_yolu)
    except (OSError, UnicodeDecodeError) as hata:
        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): rotasyon sonrasi kutu olculemedi "
            "(%s) -> yazma REDDEDILDI.\n" % hata)
        rotasyon_ciktisini_yaz(sonuc)
        return 2

    if sonuc.returncode == 0 and sonra <= tavan:
        print("ROTASYON TETIKLENDI once=%d sonra=%d tavan=%d" %
              (once, sonra, tavan))
        return 0

    sys.stderr.write(
        "KUTU ESIK KAPISI (fail-closed): kutu %d satir, tavan %d. "
        "Rotasyon rc=%s ile tavani indiremedi -> yazma REDDEDILDI.\n" %
        (sonra, tavan, sonuc.returncode))
    rotasyon_ciktisini_yaz(sonuc)
    return 2


def stdin_payload():
    try:
        return json.load(sys.stdin), None
    except (ValueError, TypeError) as hata:
        return None, hata


def kanca_main(kutu_yolu):
    payload, hata = stdin_payload()
    if hata is not None:
        sys.stderr.write("UYARI: PreToolUse JSON parse edilemedi: %s\n" % hata)
        return 0
    return kapidan_gecir(payload, kutu_yolu)


def frontmatter():
    return ("---\nname: mimar-posta-kutusu\ndescription: test kutusu\n"
            "metadata:\n  node_type: memory\n  type: project\n---\n\n")


def sahte_kutu_metni(tavan, blok_sayisi, blok_satiri, dev_blok=False):
    """Gercek kutunun frontmatter + yeni->eski ## blok seklini kur."""
    metin = frontmatter()
    if dev_blok:
        blok_sayisi = 1
        blok_satiri = max(blok_satiri, tavan)
    for blok in range(blok_sayisi):
        metin += "## 2026-08-%02d — Test blok %d\n" % (18 - blok, blok + 1)
        for satir in range(blok_satiri):
            metin += "olcum-blok-%d-satir-%d\n" % (blok + 1, satir + 1)
    return metin


def payload_yaz(kutu_yolu, arac="Write", file_path=None):
    return {"tool_name": arac,
            "tool_input": {"file_path": file_path or kutu_yolu,
                            "content": "yeni yazi\n"}}


def kanca_cagir(kapi_yolu, kutu_yolu, payload, ortam=None):
    """Test koşumunu üretim kancalarını temizleyerek veya ezerek çağır."""
    env = os.environ.copy()
    env.pop("PRUVO_KUTU_ESIK_ARSIV_ARACI", None)
    env.pop("PRUVO_KUTU_ESIK_ZAMAN_ASIMI", None)
    if ortam:
        env.update(ortam)
    return subprocess.run([sys.executable, kapi_yolu, "--kutu", kutu_yolu],
                          input=json.dumps(payload), capture_output=True,
                          text=True, env=env)


def yeni_fikstur(kok, tavan, metin):
    kutu = os.path.join(kok, "kutu.md")
    arsiv = os.path.join(kok, "kutu-arsiv.md")
    with open(kutu, "w", encoding="utf-8", newline="") as dosya:
        dosya.write(metin)
    with open(arsiv, "w", encoding="utf-8", newline="") as dosya:
        dosya.write("---\nname: kutu-arsiv\n---\n\n## eski arsiv\narsiv satiri\n")
    return kutu, arsiv


def arsiv_stub(kok, eylem):
    """V7/V8 için yalnız modül yüklenince tanımlı, çalışınca davranan stub."""
    yol = os.path.join(kok, "arsiv-stub-%s.py" % eylem)
    if eylem == "uyku":
        govde = (
            "import time\n"
            "VARSAYILAN_TAVAN = 300\n"
            "if __name__ == '__main__':\n"
            "    time.sleep(5)\n")
    else:
        govde = (
            "import os\n"
            "import sys\n"
            "VARSAYILAN_TAVAN = 300\n"
            "if __name__ == '__main__':\n"
            "    os.remove(sys.argv[-1])\n")
    with open(yol, "w", encoding="utf-8", newline="") as dosya:
        dosya.write(govde)
    return yol


def arsiv_stub_cagri_izleyici(kok):
    """Subprocess gercekten baslarsa iz birakan test arşiv araci kur."""
    yol = os.path.join(kok, "arsiv-stub-cagri.py")
    iz = os.path.join(kok, "arsiv-stub-cagri.iz")
    govde = (
        "VARSAYILAN_TAVAN = 300\n"
        "if __name__ == '__main__':\n"
        "    with open(%r, 'wb') as dosya:\n"
        "        dosya.write(b'cagrildi\\n')\n" % iz)
    with open(yol, "w", encoding="utf-8", newline="") as dosya:
        dosya.write(govde)
    return yol, iz


def vaka_satiri(numara, yesil, rc, ayrintilar):
    return "V%d %s rc=%d %s" % (numara, "YESIL" if yesil else "KIRMIZI", rc,
                                 ayrintilar)


def kendini_test():
    """V1..V11 kabulini yalniz gecici kutu/arşiv fikstürleriyle kos."""
    kaynak = arsiv_modulu_yukle(ARSIV_ARACI)
    tavan = kaynak.VARSAYILAN_TAVAN
    kapi_yolu = os.path.abspath(__file__)
    gercek_kutu = os.path.expanduser(kaynak.KUTU_VARSAYILAN)
    gercek_once = None
    try:
        gercek_once = kutu_bayt(gercek_kutu)
    except (OSError, IOError) as hata:
        gercek_hata = str(hata)
    else:
        gercek_hata = None

    sonuclar = []

    # V1: ilgisiz arac, kutu tavani asmis olsa da kapı olcmez.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v1-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 7, max(20, tavan // 4)))
        once = kutu_bayt(kutu)
        sonuc = kanca_cagir(kapi_yolu, kutu, payload_yaz(kutu, "Bash"))
        sonra = kutu_bayt(kutu)
        iyi = sonuc.returncode == 0 and once == sonra
        sonuclar.append(vaka_satiri(1, iyi, sonuc.returncode,
                                    "kutu_bayt_once=%d kutu_bayt_sonra=%d degisti=%s" %
                                    (len(once), len(sonra), "EVET" if once != sonra else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V2: baska dosya yolu, hedef kutu yine tavani asiyor.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v2-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 7, max(20, tavan // 4)))
        baska = os.path.join(kok, "baska.md")
        with open(baska, "w", encoding="utf-8") as dosya:
            dosya.write("baska dosya\n")
        once = kutu_bayt(kutu)
        sonuc = kanca_cagir(kapi_yolu, kutu, payload_yaz(kutu, "Write", baska))
        sonra = kutu_bayt(kutu)
        iyi = sonuc.returncode == 0 and once == sonra
        sonuclar.append(vaka_satiri(2, iyi, sonuc.returncode,
                                    "kutu_bayt_once=%d kutu_bayt_sonra=%d degisti=%s" %
                                    (len(once), len(sonra), "EVET" if once != sonra else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V3: hedef kutu tavanin altinda.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v3-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 1, max(1, tavan // 4)))
        once = kutu_bayt(kutu)
        sonuc = kanca_cagir(kapi_yolu, kutu, payload_yaz(kutu))
        sonra = kutu_bayt(kutu)
        satir = kutu_satir_sayisi(kutu)
        iyi = sonuc.returncode == 0 and once == sonra and satir <= tavan and "ESIK ALTI" in sonuc.stdout
        sonuclar.append(vaka_satiri(3, iyi, sonuc.returncode,
                                    "satir=%d tavan=%d kutu_degisti=%s cikti=ESIK_ALTI" %
                                    (satir, tavan, "EVET" if once != sonra else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V4: rotasyon indirir; bayt ve arsiv buyumesi lossless olarak olculur.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v4-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 7, max(20, tavan // 4)))
        kutu_once = kutu_bayt(kutu)
        arsiv_once = kutu_bayt(arsiv)
        sonuc = kanca_cagir(kapi_yolu, kutu, payload_yaz(kutu))
        kutu_sonra = kutu_bayt(kutu)
        arsiv_sonra = kutu_bayt(arsiv)
        kutu_onyazi_korundu = kutu_once.startswith(kutu_sonra)
        tasinan = kutu_once[len(kutu_sonra):] if kutu_onyazi_korundu else b""
        tasinan_bayt = len(tasinan)
        satir = kutu_satir_sayisi(kutu)
        kayipsiz = (kutu_onyazi_korundu and
                    len(kutu_once) == len(kutu_sonra) + tasinan_bayt and
                    arsiv_sonra.endswith(tasinan) and
                    len(arsiv_sonra) - len(arsiv_once) >= tasinan_bayt)
        iyi = (sonuc.returncode == 0 and satir <= tavan and
               len(arsiv_sonra) > len(arsiv_once) and
               "ROTASYON TETIKLENDI" in sonuc.stdout and kayipsiz)
        sonuclar.append(vaka_satiri(4, iyi, sonuc.returncode,
                                    "once_satir=%d sonra_satir=%d tavan=%d tasinan_bayt=%d arsiv_delta_bayt=%d lossless=%s" %
                                    (len(kutu_once.decode("utf-8").splitlines()), satir, tavan,
                                     tasinan_bayt, len(arsiv_sonra) - len(arsiv_once),
                                     "EVET" if kayipsiz else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V5: tek dev blok korunur; arşiv rc=0 verse bile kutu tavani asik kalir.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v5-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 1, tavan + 20, True))
        once = kutu_bayt(kutu)
        sonuc = kanca_cagir(kapi_yolu, kutu, payload_yaz(kutu))
        sonra = kutu_bayt(kutu)
        satir = kutu_satir_sayisi(kutu)
        iyi = (sonuc.returncode == 2 and once == sonra and satir > tavan and
               "fail-closed" in sonuc.stderr)
        sonuclar.append(vaka_satiri(5, iyi, sonuc.returncode,
                                    "satir=%d tavan=%d kutu_degisti=%s fail_closed=%s" %
                                    (satir, tavan, "EVET" if once != sonra else "HAYIR",
                                     "EVET" if "fail-closed" in sonuc.stderr else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V6: rotasyon kilidi disaridan tutulur; arşiv rc=3 ve kapı rc=2 verir.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v6-")
    kilit = None
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 7, max(20, tavan // 4)))
        kilit_yolu = os.path.join(kok, ".kutu.md.lock")
        kilit = open(kilit_yolu, "a+")
        fcntl.flock(kilit.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        once = kutu_bayt(kutu)
        sonuc = kanca_cagir(kapi_yolu, kutu, payload_yaz(kutu))
        sonra = kutu_bayt(kutu)
        satir = kutu_satir_sayisi(kutu)
        iyi = (sonuc.returncode == 2 and once == sonra and satir > tavan and
               "fail-closed" in sonuc.stderr and "rc=3" in sonuc.stderr)
        sonuclar.append(vaka_satiri(6, iyi, sonuc.returncode,
                                    "satir=%d tavan=%d kutu_degisti=%s fail_closed=%s arsiv_rc=3" %
                                    (satir, tavan, "EVET" if once != sonra else "HAYIR",
                                     "EVET" if "fail-closed" in sonuc.stderr else "HAYIR")))
    finally:
        if kilit is not None:
            fcntl.flock(kilit.fileno(), fcntl.LOCK_UN)
            kilit.close()
        shutil.rmtree(kok)

    # V7: rotasyon alt sureci timeout'a ugrar; istisna kolu fail-closed olcmelidir.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v7-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 7, max(20, tavan // 4)))
        stub = arsiv_stub(kok, "uyku")
        once = kutu_bayt(kutu)
        sonuc = kanca_cagir(
            kapi_yolu, kutu, payload_yaz(kutu),
            {"PRUVO_KUTU_ESIK_ARSIV_ARACI": stub,
             "PRUVO_KUTU_ESIK_ZAMAN_ASIMI": "1"})
        sonra = kutu_bayt(kutu)
        iyi = (sonuc.returncode == 2 and once == sonra and
               "fail-closed" in sonuc.stderr and
               "rotasyon istisna" in sonuc.stderr)
        sonuclar.append(vaka_satiri(7, iyi, sonuc.returncode,
                                    "kutu_degisti=%s fail_closed=%s rotasyon_istisna=%s" %
                                    ("EVET" if once != sonra else "HAYIR",
                                     "EVET" if "fail-closed" in sonuc.stderr else "HAYIR",
                                     "EVET" if "rotasyon istisna" in sonuc.stderr else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V8: rotasyon kutuyu sildi; sonraki olcum kolu fail-closed olcmelidir.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v8-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 7, max(20, tavan // 4)))
        stub = arsiv_stub(kok, "sil")
        sonuc = kanca_cagir(
            kapi_yolu, kutu, payload_yaz(kutu),
            {"PRUVO_KUTU_ESIK_ARSIV_ARACI": stub})
        silindi = not os.path.exists(kutu)
        iyi = (sonuc.returncode == 2 and silindi and
               "fail-closed" in sonuc.stderr and
               "rotasyon sonrasi kutu olculemedi" in sonuc.stderr)
        sonuclar.append(vaka_satiri(8, iyi, sonuc.returncode,
                                    "kutu_silindi=%s fail_closed=%s sonrasi_olcum=%s" %
                                    ("EVET" if silindi else "HAYIR",
                                     "EVET" if "fail-closed" in sonuc.stderr else "HAYIR",
                                     "EVET" if "rotasyon sonrasi kutu olculemedi" in sonuc.stderr else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V9: hedef kutuda esik kaynagi yoksa kapı fail-closed kalmalidir.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v9-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 7, max(20, tavan // 4)))
        once = kutu_bayt(kutu)
        sonuc = kanca_cagir(
            kapi_yolu, kutu, payload_yaz(kutu),
            {"PRUVO_KUTU_ESIK_ARSIV_ARACI": os.path.join(kok, "yok.py")})
        sonra = kutu_bayt(kutu)
        iyi = (sonuc.returncode == 2 and once == sonra and
               "esik kaynagi" in sonuc.stderr and
               "yuklenemedi" in sonuc.stderr)
        sonuclar.append(vaka_satiri(9, iyi, sonuc.returncode,
                                    "kutu_degisti=%s esik_kaynagi_fail_closed=%s" %
                                    ("EVET" if once != sonra else "HAYIR",
                                     "EVET" if "esik kaynagi" in sonuc.stderr and
                                     "yuklenemedi" in sonuc.stderr else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V10: ayni yok esik kaynagi hedef olmayan dosyada hic yuklenmez; izin surer.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v10-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan,
                                   sahte_kutu_metni(tavan, 7, max(20, tavan // 4)))
        baska = os.path.join(kok, "baska.md")
        with open(baska, "w", encoding="utf-8") as dosya:
            dosya.write("baska dosya\n")
        once = kutu_bayt(kutu)
        sonuc = kanca_cagir(
            kapi_yolu, kutu, payload_yaz(kutu, "Write", baska),
            {"PRUVO_KUTU_ESIK_ARSIV_ARACI": os.path.join(kok, "yok.py")})
        sonra = kutu_bayt(kutu)
        iyi = sonuc.returncode == 0 and once == sonra and not sonuc.stderr
        sonuclar.append(vaka_satiri(10, iyi, sonuc.returncode,
                                    "kutu_degisti=%s hedef_disinda_esik_yuklenmedi=%s" %
                                    ("EVET" if once != sonra else "HAYIR",
                                     "EVET" if not sonuc.stderr else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    # V11: hedef kutu var ama UTF-8 olarak okunamaz; rotasyon baslamamalidir.
    kok = tempfile.mkdtemp(prefix="kutu-esik-v11-")
    try:
        kutu, arsiv = yeni_fikstur(kok, tavan, "gecersiz utf8 fiksturu\n")
        with open(kutu, "wb") as dosya:
            dosya.write(b"---\nname: kutu\n---\n\n\xff\xfe gecersiz\n")
        kutu_once = kutu_bayt(kutu)
        arsiv_once = kutu_bayt(arsiv)
        stub, cagri_izi = arsiv_stub_cagri_izleyici(kok)
        sonuc = kanca_cagir(
            kapi_yolu, kutu, payload_yaz(kutu),
            {"PRUVO_KUTU_ESIK_ARSIV_ARACI": stub})
        kutu_sonra = kutu_bayt(kutu)
        arsiv_sonra = kutu_bayt(arsiv)
        cagri = os.path.exists(cagri_izi)
        iyi = (sonuc.returncode == 2 and os.path.exists(kutu) and
               kutu_once == kutu_sonra and arsiv_once == arsiv_sonra and
               "hedef kutu olculemedi" in sonuc.stderr and not cagri)
        sonuclar.append(vaka_satiri(11, iyi, sonuc.returncode,
                                    "hedef_var=%s kutu_degisti=%s arsiv_degisti=%s "
                                    "rotasyon_cagrildi=%s hedef_kutu_olculemedi=%s" %
                                    ("EVET" if os.path.exists(kutu) else "HAYIR",
                                     "EVET" if kutu_once != kutu_sonra else "HAYIR",
                                     "EVET" if arsiv_once != arsiv_sonra else "HAYIR",
                                     "EVET" if cagri else "HAYIR",
                                     "EVET" if "hedef kutu olculemedi" in sonuc.stderr else "HAYIR")))
    finally:
        shutil.rmtree(kok)

    for satir in sonuclar:
        print(satir)
    yesil = sum(1 for satir in sonuclar if " YESIL " in satir)
    print("KENDINI-TEST: %d/%d" % (yesil, len(sonuclar)))

    if gercek_once is None:
        if ci_ortaminda():
            print("GERCEK_KUTU_BAYT: KUTU_KAPSAM_DISI (CI ortami; %s)" %
                  gercek_hata)
            gercek_ayni = True
        else:
            print("GERCEK_KUTU_BAYT: OLCULEMEDI: %s" % gercek_hata)
            gercek_ayni = False
    else:
        try:
            gercek_sonra = kutu_bayt(gercek_kutu)
        except (OSError, IOError) as hata:
            print("GERCEK_KUTU_BAYT: OLCULEMEDI: %s" % hata)
            gercek_ayni = False
        else:
            gercek_ayni = gercek_once == gercek_sonra
            print("GERCEK_KUTU_BAYT_DEGISMEDI=%s bayt_once=%d bayt_sonra=%d" %
                  ("EVET" if gercek_ayni else "HAYIR", len(gercek_once),
                   len(gercek_sonra)))
    return 0 if yesil == len(sonuclar) and gercek_ayni else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ortak posta kutusu yazma esik kapisi")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--kutu", default=None, help="yalniz test icin hedef kutu yolu")
    args = ap.parse_args(argv)
    if args.kendini_test:
        return kendini_test()
    kutu_yolu = (args.kutu or os.environ.get("PRUVO_KUTU_ESIK_KUTU") or
                 KUTU_VARSAYILAN_YOLU)
    return kanca_main(os.path.abspath(os.path.expanduser(kutu_yolu)))


if __name__ == "__main__":
    sys.exit(main())
