#!/usr/bin/env python3
"""onizleme damga + tek-yukleyici kilidi — hermetik kabul + mutasyon testi (BaBa 17:0x, 9 Eki 2026).

Hafif izole: gercek wrangler YOK, gercek ag YOK, gercek urunler.json/STATIK dizinine DOKUNULMAZ.
  - `foto-onizleme.py` ve `onizleme-makine-kos.py` modulleri import edilir.
  - `_git` ve `subprocess.run` modulleri icinde monkeypatch'lenir (sagirlestirme).
  - `STATIK` gecici bir dizine yonlendirilir (test bitince silinir).
  - `ONIZLEME_KOS_HTTP_READER` env kancasi ile sagte HTTP okuyucu kullanilir.

Vakalar (5):
  V1 damga dosyasi icerigi dogru (sha + dal + kirli)
  V2 kirli agac -> yukle rc=2 (YUKLE RED kirli-agac)
  V3 iki eszamanli yukleme SIRALI (ikincisi birincinin bitisinden SONRA baslar, zaman damgasiyla)
  V4 damga uyusmaz -> rc 2 (MAKINE_KOS HATA damga-uyusmaz)
  V5 damga uyusur -> rc 0 (MAKINE_KOS damga=... rc=0)

Mutantlar (4): biri oyle dezenanmis kaynakla yeniden calistirilir; vakalarin en az biri KIRMIZI olmalidir.
  M1 damga yazimi silinmis (_damga_yazi cagirisi kaldirilmis) -> V1 ve V5 KIRMIZI
  M2 kirli denetimi silinmis (kirli>0 -> rc 2 yok) -> V2 KIRMIZI
  M3 flock silinmis (LK_EX yerine LK_UN) -> V3 KIRMIZI
  M4 damga karsilastirmasi silinmis (okunan != beklenen -> rc 0) -> V4 KIRMIZI

Cikti: "VAKA_KIRMIZI=0 SURVIVOR=0" (hepsi yesil) veya "VAKA_KIRMIZI=<n> SURVIVOR=<mutant_listesi>"
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOTO_PY = os.path.join(ROOT, "tools", "foto-onizleme.py")
MAK_PY = os.path.join(ROOT, "tools", "onizleme-makine-kos.py")
TEST_SHA = "deadbeef" + "0" * 32  # 40 hex
TEST_SHA8 = TEST_SHA[:8]
TEST_DAL = "dal/onizleme-test"


# ---------- Modul yukleme + monkeypatch yardimcilari ----------

def _yukle_foto():
    spec = importlib.util.spec_from_file_location("foto_onizleme_xyz", FOTO_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _yukle_mak():
    spec = importlib.util.spec_from_file_location("onizleme_makine_kos_xyz", MAK_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sahte_git(kirli_sayisi=0, sha=TEST_SHA, dal=TEST_DAL, git_common_dir=None):
    def f(*args, **kwargs):
        if args[:2] == ("status", "--porcelain"):
            satirlar = [" degisti\n" for _ in range(kirli_sayisi)]
            return subprocess.CompletedProcess(args=args, returncode=0,
                                               stdout="".join(satirlar), stderr="")
        if args[:2] == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=sha + "\n", stderr="")
        if args[:3] == ("rev-parse", "--abbrev-ref", "HEAD"):
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=dal + "\n", stderr="")
        if args[:3] == ("rev-parse", "--git-common-dir"):
            yol = git_common_dir if git_common_dir is not None else os.path.join(ROOT, ".git")
            return subprocess.CompletedProcess(args=args, returncode=0,
                                               stdout=yol + "\n", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
    return f


def _sahte_subproc(rc=0, stdout="", stderr=""):
    def f(*args, **kwargs):
        return subprocess.CompletedProcess(args=args if args else kwargs.get("args", []),
                                          returncode=rc, stdout=stdout, stderr=stderr)
    return f


def _kur(foto_mod, tmpdir, kirli=0, subproc_rc=0, git_common_dir=None):
    """Test icin monkeypatch'lenmis ortami kur; geri donen (foto, lock_yol)."""
    foto_mod.STATIK = tmpdir
    # _kilitle icin kilit yolu: gecici bir tmp dizinine yonlendir (worktree'de .git dosya)
    gecici_kok = git_common_dir if git_common_dir is not None else tempfile.mkdtemp(prefix="onizleme-damga-test-")
    os.makedirs(gecici_kok, exist_ok=True)
    foto_mod._git = _sahte_git(kirli_sayisi=kirli, git_common_dir=gecici_kok)
    foto_mod.subprocess.run = _sahte_subproc(rc=subproc_rc)
    # Kilit tavanini testte 5 sn yap ki paralel iki yukleme makul surede bitsin
    foto_mod.KILIT_TAVAN = 5
    os.makedirs(tmpdir, exist_ok=True)
    foto_mod._TEST_GIT_COMMON_DIR = gecici_kok
    return foto_mod


# ---------- Vakalar ----------

def vaka1_damga_dogru():
    """V1: statik_kur sonrasi onizleme-surum.json dogru icerigi tasiyor."""
    tmp = tempfile.mkdtemp()
    try:
        foto = _yukle_foto()
        kur_foto = _kur(foto, tmp, kirli=0)
        foto.statik_kur()
        damga_yol = os.path.join(tmp, "onizleme-surum.json")
        with open(damga_yol) as f:
            d = json.load(f)
        assert d.get("sha") == TEST_SHA, "sha yanlis: %r" % d.get("sha")
        assert d.get("dal") == TEST_DAL, "dal yanlis: %r" % d.get("dal")
        assert d.get("kirli") == 0, "kirli yanlis: %r" % d.get("kirli")
        print("V1 sonuc=OK sha=" + d["sha"][:8] + " dal=" + d["dal"] + " kirli=" + str(d["kirli"]))
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if 'kur_foto' in dir() and hasattr(kur_foto, '_TEST_GIT_COMMON_DIR'):
            shutil.rmtree(kur_foto._TEST_GIT_COMMON_DIR, ignore_errors=True)


def vaka2_kirli_red():
    """V2: kirli agacta yukle rc=2 doner, YUKLE RED kirli-agac basar."""
    tmp = tempfile.mkdtemp()
    try:
        foto = _yukle_foto()
        kur_foto = _kur(foto, tmp, kirli=3)
        rc = foto.yukle()
        assert rc == 2, "kirli agacta rc=2 bekleniyordu, geldi=%d" % rc
        print("V2 sonuc=OK kirli=3 yukle_rc=2")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if 'kur_foto' in dir() and hasattr(kur_foto, '_TEST_GIT_COMMON_DIR'):
            shutil.rmtree(kur_foto._TEST_GIT_COMMON_DIR, ignore_errors=True)


def vaka3_kilit_sirali():
    """V3: iki eszamanli yukleme SIRALI calisir (ikincisi birincinin bitisinden SONRA baslar).

    Her iki cagri farkli tmp dizini kullanir (cunku tek tmp'yi paylasmak zaten dogal bir kilit noktasi
    olurdu; bizim amacimiz PAYLASILAN git-common-dir kilit dosyasinin sirayi zorlamasidir).
    """
    tmp_a = tempfile.mkdtemp()
    tmp_b = tempfile.mkdtemp()
    try:
        foto_a = _yukle_foto()
        kur_a = _kur(foto_a, tmp_a, kirli=0)
        # AYNI kilit yolu icin AYNI gecici_kok — kilit paylasilan olmali
        paylasilan_kok = kur_a._TEST_GIT_COMMON_DIR
        # Ikinci "foto" ornegi AYNI gecici_kok'a yazsin
        foto_b = _yukle_foto()
        _kur(foto_b, tmp_b, kirli=0, git_common_dir=paylasilan_kok)
        baslangic_lock = threading.Lock()
        tamam = []

        def yukle_thread(foto, etiket):
            rc = foto.yukle()
            with baslangic_lock:
                tamam.append((etiket, rc, time.time()))

        t1 = threading.Thread(target=yukle_thread, args=(foto_a, "A"))
        t2 = threading.Thread(target=yukle_thread, args=(foto_b, "B"))
        t1.start()
        time.sleep(0.05)  # A'nin once kilidi almasini sagla
        t2.start()
        t1.join()
        t2.join()
        assert len(tamam) == 2, "iki yukleme tamamlanmadi: %r" % tamam
        for etiket, rc, _ts in tamam:
            assert rc == 0, "%s rc=%d beklenen 0" % (etiket, rc)
        a_rc = next(t for e, t, _ in tamam if e == "A")
        b_rc = next(t for e, t, _ in tamam if e == "B")
        assert b_rc >= a_rc, "B A'dan once bitti: a=%r b=%r" % (a_rc, b_rc)
        print("V3 sonuc=OK A_rc=0 B_rc=0 sirali=True a_rc=%.3f b_rc=%.3f" % (a_rc, b_rc))
        return True
    finally:
        shutil.rmtree(tmp_a, ignore_errors=True)
        shutil.rmtree(tmp_b, ignore_errors=True)
        if 'paylasilan_kok' in dir():
            shutil.rmtree(paylasilan_kok, ignore_errors=True)


def vaka4_damga_uyusmaz():
    """V4: HTTP okuyucu farkli sha dondururse damga_dogrula rc=2 doner."""
    mak = _yukle_mak()
    # Sahte okuyucu: farkli sha
    farkli_sha = "cafebabe" + "0" * 32
    os.environ["ONIZLEME_KOS_HTTP_READER"] = "sagte"
    # Monkeypatch _http_oku (env kancasina ek olarak)
    mak._http_oku = lambda url: json.dumps({"sha": farkli_sha, "dal": TEST_DAL, "kirli": 0})
    # damga_dogrula icindeki 30 sn'lik beklemeyi kisa tutmak icin sabitler override
    mak.DAMGA_BEKLEME = 0.0
    okunan, rc = mak.damga_dogrula(TEST_SHA)
    assert rc == 2, "uyusmazda rc=2 bekleniyordu, geldi=%d okunan=%r" % (rc, okunan)
    assert okunan == farkli_sha, "okunan sha yanlis: %r" % okunan
    print("V4 sonuc=OK beklenen=%s okunan=%s rc=2" % (TEST_SHA8, farkli_sha[:8]))
    return True


def vaka5_damga_uyusur():
    """V5: HTTP okuyucu ayni sha dondururse damga_dogrula rc=0 doner."""
    mak = _yukle_mak()
    mak._http_oku = lambda url: json.dumps({"sha": TEST_SHA, "dal": TEST_DAL, "kirli": 0})
    mak.DAMGA_BEKLEME = 0.0
    okunan, rc = mak.damga_dogrula(TEST_SHA)
    assert rc == 0, "uyusurda rc=0 bekleniyordu, geldi=%d" % rc
    assert okunan == TEST_SHA, "okunan sha yanlis: %r" % okunan
    print("V5 sonuc=OK beklenen=%s okunan=%s rc=0" % (TEST_SHA8, okunan[:8]))
    return True


# ---------- Mutant motoru ----------

def _metni_kaynakla_sil(foto_mod=None, mak_mod=None):
    """Verilen modulun kaynak metnini oku."""
    if foto_mod is not None:
        with open(FOTO_PY) as f:
            return f.read(), "foto-onizleme.py"
    with open(MAK_PY) as f:
        return f.read(), "onizleme-makine-kos.py"


def _dosyaya_yaz_ic(yol, metin):
    """Bir dosyaya gecici olarak mutant metnini yaz; sonra geri yukle."""
    _YEDEK_DOSYA[yol] = open(yol).read()
    with open(yol, "w") as f:
        f.write(metin)


def _geri_yukle(yol):
    if yol in _YEDEK_DOSYA:
        with open(yol, "w") as f:
            f.write(_YEDEK_DOSYA[yol])
        del _YEDEK_DOSYA[yol]


_YEDEK_DOSYA = {}


def mutant1_damga_silindi(foto_uretec, mak_uretec, vakalar):
    """M1: statik_kur icinden _damga_yazi cagirisi kaldirildi. V1 KIRMIZI olmali
    (onizleme-surum.json dosyasi olusmaz)."""
    kaynak = open(FOTO_PY).read()
    # _damga_yazi() cagri satiri: "    _damga_yazi()" — sadece bu tek satiri sil
    silinen = kaynak.replace("    _damga_yazi()\n", "")
    assert silinen != kaynak, "M1: hedef satir bulunamadi (foto-onizleme.py'de _damga_yazi() yok)"
    _dosyaya_yaz_ic(FOTO_PY, silinen)
    return _mutant_kos("M1", vakalar, beklenen_kirmizi={"V1"})


def mutant2_kirli_silindi(foto_uretec, mak_uretec, vakalar):
    """M2: kirli denetimi silindi (kirli>0 RED yok). V2 KIRMIZI olmali."""
    kaynak = open(FOTO_PY).read()
    # kirli>0 ise YUKLE RED kirli-agac donduren 3 satiri sil
    hedef = ('        kirli = _kirli_sayisi()\n'
             '        if kirli > 0:\n'
             '            print("YUKLE RED kirli-agac kirli=" + str(kirli))\n'
             '            return 2\n')
    silinen = kaynak.replace(hedef, "")
    assert silinen != kaynak, "M2: hedef blok bulunamadi"
    _dosyaya_yaz_ic(FOTO_PY, silinen)
    return _mutant_kos("M2", vakalar, beklenen_kirmizi={"V2"})


def mutant3_flock_silindi(foto_uretec, mak_uretec, vakalar):
    """M3: flock cagirisi silindi (LK_EX yerine LK_UN gibi). V3 KIRMIZI olmali."""
    kaynak = open(FOTO_PY).read()
    # _kilitle icindeki fcntl.flock satirini LK_UN yap (kilitleme yok)
    hedef = "            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)"
    silinen = kaynak.replace(hedef, "fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # MUTANT")
    assert silinen != kaynak, "M3: hedef satir bulunamadi"
    _dosyaya_yaz_ic(FOTO_PY, silinen)
    return _mutant_kos("M3", vakalar, beklenen_kirmizi={"V3"})


def mutant4_karsilastirma_silindi(foto_uretec, mak_uretec, vakalar):
    """M4: damga_dogrula uyusmazda rc 2 donmuyor (son print + return 2 silindi). V4 KIRMIZI olmali."""
    kaynak = open(MAK_PY).read()
    # dongu bittikten sonraki: uyusmaz uyari baski + return (okunan, 2)
    hedef = ('    print("MAKINE_KOS HATA damga-uyusmaz beklenen=%s okunan=%s" % (beklenen8, okunan[:8]))\n'
             '    return (okunan, 2)\n')
    silinen = kaynak.replace(hedef, "    return (okunan, 0)  # MUTANT: karsilastirma silindi\n")
    assert silinen != kaynak, "M4: hedef blok bulunamadi"
    _dosyaya_yaz_ic(MAK_PY, silinen)
    return _mutant_kos("M4", vakalar, beklenen_kirmizi={"V4"})


def _mutant_kos(etiket, vakalar, beklenen_kirmizi):
    """Mutantli metin diskte; vakalari yeniden calistir; beklenen KIRMIZI set gerceklesmeli.

    Dondurur: (etiket, kirmizi_set). Gerceklesmemisse SURVIVOR olarak sayilir.
    """
    kirmizi = set()
    for ad, fn in vakalar:
        try:
            if not fn():
                kirmizi.add(ad)
        except Exception:
            kirmizi.add(ad)
    _geri_yukle(FOTO_PY if etiket in ("M1", "M2", "M3") else MAK_PY)
    if not beklenen_kirmizi.issubset(kirmizi):
        return (etiket, "SURVIVOR", beklenen_kirmizi, kirmizi)
    return (etiket, "OK", beklenen_kirmizi, kirmizi)


# ---------- Ana akis ----------

def main():
    vakalar = [
        ("V1", vaka1_damga_dogru),
        ("V2", vaka2_kirli_red),
        ("V3", vaka3_kilit_sirali),
        ("V4", vaka4_damga_uyusmaz),
        ("V5", vaka5_damga_uyusur),
    ]
    kirmizi = set()
    for ad, fn in vakalar:
        try:
            if not fn():
                kirmizi.add(ad)
        except Exception as e:
            print(ad + " sonuc=HATA " + type(e).__name__ + ": " + str(e)[:120])
            kirmizi.add(ad)
    # Mutantlar
    mutantlar = [mutant1_damga_silindi, mutant2_kirli_silindi,
                 mutant3_flock_silindi, mutant4_karsilastirma_silindi]
    mutant_sonuc = []
    for mn in mutantlar:
        etiket, durum, beklenen, gercek_set = mn(None, None, vakalar)
        print("MUTANT " + etiket + " " + durum +
              (" beklenen_kirmizi=" + ",".join(sorted(beklenen)) +
               " gerceklesen=" + ",".join(sorted(gercek_set & beklenen)) if durum == "OK" else
               " beklenen_kirmizi=" + ",".join(sorted(beklenen)) +
               " gerceklesen=" + ",".join(sorted(gercek_set))))
        if durum == "SURVIVOR":
            mutant_sonuc.append((etiket, beklenen, gercek_set))
    # Sonuc
    print("VAKA_KIRMIZI=" + str(len(kirmizi)) + " SURVIVOR=" + str(len(mutant_sonuc)))
    if kirmizi or mutant_sonuc:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())