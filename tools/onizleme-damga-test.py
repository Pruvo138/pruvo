#!/usr/bin/env python3
"""onizleme damga + tek-yukleyici kilidi — hermetik kabul + mutasyon testi (BaBa 17:0x, 9 Eki 2026).

Hafif izole: gercek wrangler YOK, gercek ag YOK, gercek urunler.json/STATIK dizinine DOKUNULMAZ.
  - `foto-onizleme.py` ve `onizleme-makine-kos.py` modulleri BELLEKTE import edilir.
  - `_git` ve `subprocess.run` modulleri icinde monkeypatch'lenir (sagirlestirme).
  - `STATIK` gecici bir dizine yonlendirilir (test bitince silinir).
  - `ONIZLEME_KOS_HTTP_READER` env kancasi ile sagte HTTP okuyucu kullanilir.
  - Mutantlar: kaynak metin BELLEKTE okunur, replace edilir, `types.ModuleType + compile/exec` ile
    yeni modul nesnesine derlenir; sys.modules'a KONMAZ; gercek tools/*.py yazilmaz.

Vakalar (5):
  V1 damga dosyasi icerigi dogru (sha + dal + kirli)
  V2 kirli agac -> yukle rc=2 (YUKLE RED kirli-agac)
  V3 iki eszamanli yukleme SIRALI (ikincisi birincinin bitisinden SONRA baslar, zaman damgasiyla)
  V4 damga uyusmaz -> rc 2 (MAKINE_KOS HATA damga-uyusmaz)
  V5 damga uyusur -> rc 0 (MAKINE_KOS damga=... rc=0)

Mutantlar (4): biri oyle dezenanmis kaynakla yeniden calistirilir; vakalarin en az biri KIRMIZI olmalidir.
  M1 damga yazimi silinmis (_damga_yazi cagirisi kaldirilmis) -> V1 KIRMIZI
  M2 kirli denetimi silinmis (kirli>0 -> rc 2 yok) -> V2 KIRMIZI
  M3 flock silinmis (LK_EX|LK_NB yerine pass # MUTANT, AYNI GIRINTI, derlenebilir) -> V3 KIRMIZI
  M4 damga karsilastirmasi silinmis (okunan != beklenen -> rc 0) -> V4 KIRMIZI

Mutantlarin hedef satiri BIREDEN fazla / hic bulunmazsa veya compile basarisiz olursa o mutant SURVIVOR.

Cikti: "VAKA_KIRMIZI=0 SURVIVOR=0" (hepsi yesil) veya "VAKA_KIRMIZI=<n> SURVIVOR=<n>".
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
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOTO_PY = os.path.join(ROOT, "tools", "foto-onizleme.py")
MAK_PY = os.path.join(ROOT, "tools", "onizleme-makine-kos.py")
TEST_SHA = "deadbeef" + "0" * 32  # 40 hex
TEST_SHA8 = TEST_SHA[:8]
TEST_DAL = "dal/onizleme-test"


# ---------- Mutant kaynak durumu (None ise diskten oku) ----------

class _Kaynaklar:
    foto_metin = None
    mak_metin = None


# ---------- Modul yukleme + monkeypatch yardimcilari ----------

def _modul_kur(yol, metin, ad):
    """Verilen metin ile bellekte modul nesnesi kur; sys.modules'a koyma."""
    co = compile(metin, yol, "exec")
    m = types.ModuleType(ad)
    m.__file__ = yol
    exec(co, m.__dict__)
    return m


def _yukle_foto():
    """Orijinal (veya mutant kaynak durumundaki) foto modulunu bellekte kur."""
    if _Kaynaklar.foto_metin is not None:
        metin = _Kaynaklar.foto_metin
    else:
        with open(FOTO_PY) as f:
            metin = f.read()
    return _modul_kur(FOTO_PY, metin, "foto_onizleme_xyz")


def _yukle_mak():
    """Orijinal (veya mutant kaynak durumundaki) mak modulunu bellekte kur."""
    if _Kaynaklar.mak_metin is not None:
        metin = _Kaynaklar.mak_metin
    else:
        with open(MAK_PY) as f:
            metin = f.read()
    return _modul_kur(MAK_PY, metin, "onizleme_makine_kos_xyz")


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

    Her iki cagri farkli tmp dizini kullanir (paylasilan git-common-dir kilit dosyasinin
    sirayi zorlamasidir). Sahte wrangler upload 0,3 sn uyur; baslangic ve bitis zamanlari
    kaydedilir; iki cagrinin araliklari CAKISMAMALI (B.basla >= A.bitis ya da A.basla >= B.bitis).
    """
    tmp_a = tempfile.mkdtemp()
    tmp_b = tempfile.mkdtemp()
    try:
        foto_a = _yukle_foto()
        kur_a = _kur(foto_a, tmp_a, kirli=0)
        paylasilan_kok = kur_a._TEST_GIT_COMMON_DIR
        foto_b = _yukle_foto()
        _kur(foto_b, tmp_b, kirli=0, git_common_dir=paylasilan_kok)
        # V3 ozel: subprocess.run yerine zaman kaydeden sahte kullan (her modul kendi etiketi).
        zaman_kayit = []
        zaman_kilit = threading.Lock()

        class _ZamanliSubprocess:
            def __init__(self, etiket):
                self._etiket = etiket
            def run(self, *args, **kwargs):
                basla = time.time()
                time.sleep(0.3)  # wrangler upload suresi
                bitis = time.time()
                with zaman_kilit:
                    zaman_kayit.append((self._etiket, basla, bitis))
                return subprocess.CompletedProcess(
                    args=args if args else kwargs.get("args", []),
                    returncode=0, stdout="", stderr="")
            def __getattr__(self, ad):
                # Diger subprocess ozellikleri (Popen, ...) icin gercek modul
                return getattr(subprocess, ad)

        foto_a.subprocess = _ZamanliSubprocess("A")
        foto_b.subprocess = _ZamanliSubprocess("B")
        baslangic_lock = threading.Lock()
        tamam = []

        def yukle_thread(foto, etiket):
            # Surec ici istisnalar (ornek M2 mutant: kirli tanimsiz) ana akisa yine
            # vaka3'un tamam/basit kontroluyle yansir; threading'in otomatik
            # stack trace basmasini baskilamak icin try/except ici.
            try:
                rc = foto.yukle()
            except BaseException as e:
                rc = ("EXC", type(e).__name__)
            with baslangic_lock:
                tamam.append((etiket, rc))

        t1 = threading.Thread(target=yukle_thread, args=(foto_a, "A"))
        t2 = threading.Thread(target=yukle_thread, args=(foto_b, "B"))
        t1.start()
        time.sleep(0.05)  # A'nin once kilidi almasini sagla
        t2.start()
        t1.join()
        t2.join()
        assert len(tamam) == 2, "iki yukleme tamamlanmadi: %r" % tamam
        for etiket, rc in tamam:
            assert rc == 0, "%s rc=%d beklenen 0" % (etiket, rc)
        assert len(zaman_kayit) == 2, "subprocess zamanlari tamamlanmadi: %r" % zaman_kayit
        a_basla, a_bitis = next(b for tag, b, _ in zaman_kayit if tag == "A"), next(e for tag, _, e in zaman_kayit if tag == "A")
        b_basla, b_bitis = next(b for tag, b, _ in zaman_kayit if tag == "B"), next(e for tag, _, e in zaman_kayit if tag == "B")
        # Cakisma kontrolu: iki aralik cakismamali.
        cakisma_var = not (b_basla >= a_bitis or a_basla >= b_bitis)
        assert not cakisma_var, (
            "A ve B araliklari cakisiyor: A=[%.3f,%.3f] B=[%.3f,%.3f]" %
            (a_basla, a_bitis, b_basla, b_bitis))
        print("V3 sonuc=OK A_rc=0 B_rc=0 sirali=True A_aralik=[%.3f,%.3f] B_aralik=[%.3f,%.3f]" %
              (a_basla, a_bitis, b_basla, b_bitis))
        return True
    finally:
        shutil.rmtree(tmp_a, ignore_errors=True)
        shutil.rmtree(tmp_b, ignore_errors=True)
        if 'paylasilan_kok' in dir():
            shutil.rmtree(paylasilan_kok, ignore_errors=True)


def vaka4_damga_uyusmaz():
    """V4: HTTP okuyucu farkli sha dondururse damga_dogrula rc=2 doner."""
    mak = _yukle_mak()
    farkli_sha = "cafebabe" + "0" * 32
    os.environ["ONIZLEME_KOS_HTTP_READER"] = "sagte"
    mak._http_oku = lambda url: json.dumps({"sha": farkli_sha, "dal": TEST_DAL, "kirli": 0})
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

def _mutant_uygula(etiket, kaynak, hedef, yenisi, hedef_dosya, vakalar, beklenen_kirmizi):
    """Mutant metnini uygula; derle (SyntaxError -> SURVIVOR); vakalari mutantli kaynakla kos.

    Dondurur: (etiket, durum, sebep, beklenen_kirmizi, gerceklesen_kirmizi).
    """
    sayi = kaynak.count(hedef)
    if sayi != 1:
        return (etiket, "SURVIVOR", "hedef-%d-bulundu" % sayi, beklenen_kirmizi, set())
    silinen = kaynak.replace(hedef, yenisi, 1)
    try:
        compile(silinen, hedef_dosya, "exec")
    except SyntaxError as e:
        return (etiket, "SURVIVOR", "compile-hatasi: %s" % str(e)[:80],
                beklenen_kirmizi, set())
    if hedef_dosya == FOTO_PY:
        _Kaynaklar.foto_metin = silinen
    else:
        _Kaynaklar.mak_metin = silinen
    try:
        kirmizi = set()
        for ad, fn in vakalar:
            try:
                if not fn():
                    kirmizi.add(ad)
            except Exception:
                kirmizi.add(ad)
        if not beklenen_kirmizi.issubset(kirmizi):
            return (etiket, "SURVIVOR", "beklenen-kirmizi-gerceklesmedi",
                    beklenen_kirmizi, kirmizi)
        return (etiket, "OK", "", beklenen_kirmizi, kirmizi)
    finally:
        if hedef_dosya == FOTO_PY:
            _Kaynaklar.foto_metin = None
        else:
            _Kaynaklar.mak_metin = None


def mutant1_damga_silindi(vakalar):
    """M1: statik_kur icinden _damga_yazi cagirisi kaldirildi. V1 KIRMIZI olmali."""
    with open(FOTO_PY) as f:
        kaynak = f.read()
    return _mutant_uygula("M1", kaynak, "    _damga_yazi()\n", "", FOTO_PY, vakalar, {"V1"})


def mutant2_kirli_silindi(vakalar):
    """M2: kirli denetimi silindi (kirli>0 RED yok). V2 KIRMIZI olmali."""
    with open(FOTO_PY) as f:
        kaynak = f.read()
    hedef = ('        kirli = _kirli_sayisi()\n'
             '        if kirli > 0:\n'
             '            print("YUKLE RED kirli-agac kirli=" + str(kirli))\n'
             '            return 2\n')
    return _mutant_uygula("M2", kaynak, hedef, "", FOTO_PY, vakalar, {"V2"})


def mutant3_flock_silindi(vakalar):
    """M3: flock cagirisi silindi (AYNI GIRINTIYLE pass # MUTANT; derlenebilir kalmali). V3 KIRMIZI olmali."""
    with open(FOTO_PY) as f:
        kaynak = f.read()
    hedef = "            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)"
    yenisi = "            pass  # MUTANT"
    return _mutant_uygula("M3", kaynak, hedef, yenisi, FOTO_PY, vakalar, {"V3"})


def mutant4_karsilastirma_silindi(vakalar):
    """M4: damga_dogrula uyusmazda rc 0 donuyor. V4 KIRMIZI olmali."""
    with open(MAK_PY) as f:
        kaynak = f.read()
    hedef = ('    print("MAKINE_KOS HATA damga-uyusmaz beklenen=%s okunan=%s" % (beklenen8, okunan[:8]))\n'
             '    return (okunan, 2)\n')
    yenisi = "    return (okunan, 0)  # MUTANT: karsilastirma silindi\n"
    return _mutant_uygula("M4", kaynak, hedef, yenisi, MAK_PY, vakalar, {"V4"})


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
        etiket, durum, sebep, beklenen, gercek_set = mn(vakalar)
        if durum == "OK":
            print("MUTANT " + etiket + " OK beklenen_kirmizi=" + ",".join(sorted(beklenen)) +
                  " gerceklesen=" + ",".join(sorted(gercek_set & beklenen)))
        else:
            ek = " sebep=" + sebep if sebep else ""
            print("MUTANT " + etiket + " SURVIVOR beklenen_kirmizi=" + ",".join(sorted(beklenen)) +
                  " gerceklesen=" + ",".join(sorted(gercek_set)) + ek)
        if durum == "SURVIVOR":
            mutant_sonuc.append((etiket, beklenen, gercek_set, sebep))
    # Sonuc
    print("VAKA_KIRMIZI=" + str(len(kirmizi)) + " SURVIVOR=" + str(len(mutant_sonuc)))
    if kirmizi or mutant_sonuc:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())