#!/usr/bin/env python3
"""duzelt-toplu-testi.py — tools/duzelt.py --toplu (batch) kipi kabul testi.

GERCEK urunler.json'a DOKUNMAZ: her senaryo icin gecici bir SAHTE repo kurar
(<tmp>/tools/duzelt.py kopyasi + <tmp>/urunler.json). duzelt.py yollari kendi
__file__ konumundan turettigi icin kopya, sahte katalog uzerinde calisir.

Kontroller:
  (a) 3 kayitlik sahte katalogda 3 islem -> urunler.json'a YAZIM SAYACI == 1
      (_atomic_write monkeypatch ile sayilir) + manifest guard'in _authorized
      kontrolunden GECER.
  (b) ortadaki islem GECERSIZ -> urunler.json BYTE-ESIT kalir (sha256), manifest
      hic olusmaz, exit != 0 ve reddedilen islem ciktida adiyla gecer.
  (c) mevcut tek-urun kipi REGRESYONSUZ (--alan/--deger, --alan-sil, --sil).
  (d) flock: kilit baskasi tarafindan tutulurken ikinci toplu cagri BEKLER
      (serilesme); kilit birakilinca tamamlanir.
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
import contextlib
import fcntl

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK_DUZELT = os.path.join(KOK, "tools", "duzelt.py")
KAYNAK_GUARD = os.path.join(KOK, "tools", "urunler-guard.py")

KATALOG = [
    {"id": "test-urun-1", "kategori": "Marin", "marka": ["Volvo"],
     "baslik": "Test Urun 1", "aciklama": "aciklama 1", "fiyat": "100 TL",
     "gorseller": ["https://media.pruvo3d.com/urunler/t1-1.jpg"], "uyelik": "gizli"},
    {"id": "test-urun-2", "kategori": "Ofis", "marka": [],
     "baslik": "Test Urun 2", "aciklama": "aciklama 2", "fiyat": "200 TL",
     "gorseller": ["https://media.pruvo3d.com/urunler/t2-1.jpg"]},
    {"id": "test-urun-3", "kategori": "Ev", "marka": [],
     "baslik": "Test Urun 3", "aciklama": "aciklama 3", "fiyat": "300 TL",
     "gorseller": ["https://media.pruvo3d.com/urunler/t3-1.jpg"]},
]

hatalar = []


def kontrol(kosul, mesaj):
    if kosul:
        print("  OK   %s" % mesaj)
    else:
        print("  HATA %s" % mesaj)
        hatalar.append(mesaj)


def sahte_repo():
    d = tempfile.mkdtemp(prefix="duzelt-toplu-testi-")
    os.makedirs(os.path.join(d, "tools"))
    shutil.copy(KAYNAK_DUZELT, os.path.join(d, "tools", "duzelt.py"))
    shutil.copy(KAYNAK_GUARD, os.path.join(d, "tools", "urunler-guard.py"))
    with open(os.path.join(d, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(KATALOG, f, ensure_ascii=False, indent=2)
    return d


def modul_yukle(repo, dosya, ad):
    yol = os.path.join(repo, "tools", dosya)
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def cagir(mod, argv):
    """mod.main()'i verilen argv ile calistir; (rc, stdout, stderr) dondur."""
    eski = sys.argv
    sys.argv = ["duzelt.py"] + argv
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = mod.main()
            except SystemExit as e:  # argparse hatasi
                rc = e.code if isinstance(e.code, int) else 2
    finally:
        sys.argv = eski
    return rc, out.getvalue(), err.getvalue()


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def islem_yaz(repo, islemler):
    yol = os.path.join(repo, "islemler.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(islemler, f, ensure_ascii=False, indent=2)
    return yol


# ---------------------------------------------------------------- (a)
def test_a():
    print("\n(a) 3 islem -> TEK yazim + guard-uyumlu manifest")
    repo = sahte_repo()
    mod = modul_yukle(repo, "duzelt.py", "duzelt_a")
    guard = modul_yukle(repo, "urunler-guard.py", "guard_a")

    sayac = {"urunler": 0, "toplam": 0}
    gercek = mod._atomic_write

    def sayan(path, obj):
        sayac["toplam"] += 1
        if os.path.abspath(path) == os.path.abspath(mod.URUNLER):
            sayac["urunler"] += 1
        return gercek(path, obj)

    mod._atomic_write = sayan

    yol = islem_yaz(repo, [
        {"id": "test-urun-1", "alan": "fiyat", "deger": "555 TL"},
        {"id": "test-urun-2", "alan": "marka", "deger": ["BMW", "Mini"]},
        {"id": "test-urun-3", "alan-sil": "gorseller"},
    ])
    rc, out, err = cagir(mod, ["--toplu", yol])
    kontrol(rc == 0, "exit 0 (cikti: %s)" % (err.strip() or out.strip().splitlines()[-1:]))
    kontrol(sayac["urunler"] == 1,
            "urunler.json YAZIM SAYACI == 1 (olculen: %d)" % sayac["urunler"])

    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        yeni = {p["id"]: p for p in json.load(f)}
    kontrol(yeni["test-urun-1"]["fiyat"] == "555 TL", "urun-1 fiyat guncellendi")
    kontrol(yeni["test-urun-2"]["marka"] == ["BMW", "Mini"], "urun-2 marka listesi guncellendi")
    kontrol("gorseller" not in yeni["test-urun-3"], "urun-3 gorseller alani kaldirildi")
    kontrol(yeni["test-urun-1"]["baslik"] == "Test Urun 1"
            and yeni["test-urun-2"]["fiyat"] == "200 TL",
            "beyan disi alanlara DOKUNULMADI")

    with open(os.path.join(repo, ".urunler-duzelt-izin.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    kontrol(guard._authorized("test-urun-1", "fiyat", yeni["test-urun-1"], manifest),
            "guard._authorized: urun-1 fiyat MESRU")
    kontrol(guard._authorized("test-urun-2", "marka", yeni["test-urun-2"], manifest),
            "guard._authorized: urun-2 marka MESRU")
    kontrol(guard._authorized("test-urun-3", "gorseller", yeni["test-urun-3"], manifest),
            "guard._authorized: urun-3 alan-sil MESRU")
    kontrol(not guard._authorized("test-urun-2", "fiyat",
                                  dict(yeni["test-urun-2"], fiyat="9 TL"), manifest),
            "guard._authorized: BEYAN DISI degisim mesru DEGIL")
    shutil.rmtree(repo, ignore_errors=True)


# ---------------------------------------------------------------- (b)
def test_b():
    print("\n(b) ortadaki islem gecersiz -> HICBIR SEY yazilmaz (byte-esit)")
    for ad, ortadaki, beklenen_iz in (
        ("olmayan id", {"id": "yok-boyle-urun", "alan": "fiyat", "deger": "1 TL"},
         "yok-boyle-urun"),
        ("yasak alan", {"id": "test-urun-2", "alan": "id", "deger": "hack"},
         "islem #2"),
        ("izinsiz alan", {"id": "test-urun-2", "alan": "uyelik", "deger": "x"},
         "islem #2"),
    ):
        repo = sahte_repo()
        mod = modul_yukle(repo, "duzelt.py", "duzelt_b")
        urunler_yol = os.path.join(repo, "urunler.json")
        once = sha(urunler_yol)
        yol = islem_yaz(repo, [
            {"id": "test-urun-1", "alan": "fiyat", "deger": "555 TL"},
            ortadaki,
            {"id": "test-urun-3", "alan": "kategori", "deger": "Ofis"},
        ])
        rc, out, err = cagir(mod, ["--toplu", yol])
        cikti = out + err
        print("  [%s] rc=%s" % (ad, rc))
        kontrol(rc != 0, "[%s] exit != 0" % ad)
        kontrol(sha(urunler_yol) == once, "[%s] urunler.json BYTE-ESIT" % ad)
        kontrol(not os.path.exists(os.path.join(repo, ".urunler-duzelt-izin.json")),
                "[%s] izin manifesti OLUSMADI" % ad)
        kontrol(beklenen_iz in cikti,
                "[%s] reddedilen islem ciktida ('%s')" % (ad, beklenen_iz))
        kontrol("REDDEDILDI" in cikti, "[%s] 'REDDEDILDI' uyarisi basildi" % ad)
        shutil.rmtree(repo, ignore_errors=True)


# ---------------------------------------------------------------- (c)
def test_c():
    print("\n(c) tek-urun kipi REGRESYONSUZ")
    repo = sahte_repo()
    mod = modul_yukle(repo, "duzelt.py", "duzelt_c")
    urunler_yol = os.path.join(repo, "urunler.json")

    rc, out, err = cagir(mod, ["test-urun-1", "--alan", "fiyat", "--deger", "777 TL",
                               "--alan", "marka", "--deger", '["Audi"]'])
    kontrol(rc == 0, "tek-urun --alan/--deger exit 0 (%s)" % err.strip())
    with open(urunler_yol, encoding="utf-8") as f:
        d = {p["id"]: p for p in json.load(f)}
    kontrol(d["test-urun-1"]["fiyat"] == "777 TL", "tek-urun fiyat yazildi")
    kontrol(d["test-urun-1"]["marka"] == ["Audi"], "tek-urun JSON deger cozumlendi")

    rc, out, err = cagir(mod, ["test-urun-1", "--alan-sil", "uyelik"])
    kontrol(rc == 0, "tek-urun --alan-sil exit 0")
    with open(urunler_yol, encoding="utf-8") as f:
        d = {p["id"]: p for p in json.load(f)}
    kontrol("uyelik" not in d["test-urun-1"], "tek-urun alan kaldirildi")

    rc, out, err = cagir(mod, ["test-urun-2", "--sil", "test gerekcesi"])
    kontrol(rc == 0, "tek-urun --sil exit 0")
    with open(urunler_yol, encoding="utf-8") as f:
        kalan = [p["id"] for p in json.load(f)]
    kontrol("test-urun-2" not in kalan, "tek-urun silindi")
    with open(os.path.join(repo, ".urunler-sil-izin.json"), encoding="utf-8") as f:
        kontrol(json.load(f) == ["test-urun-2"], "silme manifesti yazildi")

    rc, out, err = cagir(mod, ["yok-boyle", "--alan", "fiyat", "--deger", "1 TL"])
    kontrol(rc == 1, "tek-urun olmayan id -> exit 1 (olculen %s)" % rc)
    rc, out, err = cagir(mod, ["test-urun-3", "--alan", "uyelik", "--deger", "x"])
    kontrol(rc == 2, "tek-urun izinsiz alan -> exit 2 (olculen %s)" % rc)
    rc, out, err = cagir(mod, ["test-urun-3", "--toplu", "/yok/dosya.json"])
    kontrol(rc == 2, "--toplu + tek-urun argumani REDDEDILIR (olculen %s)" % rc)
    shutil.rmtree(repo, ignore_errors=True)


# ---------------------------------------------------------------- (d)
def test_d():
    print("\n(d) flock: es zamanli toplu cagri SERILESIR")
    repo = sahte_repo()
    yol = islem_yaz(repo, [{"id": "test-urun-1", "alan": "fiyat", "deger": "888 TL"}])
    kilit = open(os.path.join(repo, ".urunler.lock"), "w")
    fcntl.flock(kilit, fcntl.LOCK_EX)
    p = subprocess.Popen([sys.executable, os.path.join(repo, "tools", "duzelt.py"),
                          "--toplu", yol],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    bekledi = False
    try:
        p.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        bekledi = True
    kontrol(bekledi, "kilit tutulurken ikinci cagri BEKLEDI (hata vermedi)")
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        d = {x["id"]: x for x in json.load(f)}
    kontrol(d["test-urun-1"]["fiyat"] == "100 TL", "kilit tutulurken yazim OLMADI")

    fcntl.flock(kilit, fcntl.LOCK_UN)
    kilit.close()
    try:
        out, err = p.communicate(timeout=15)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        p.kill()
        out, err, rc = b"", b"zaman asimi", -1
    kontrol(rc == 0, "kilit birakilinca tamamlandi, exit 0 (%s)" % err.decode()[:120])
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        d = {x["id"]: x for x in json.load(f)}
    kontrol(d["test-urun-1"]["fiyat"] == "888 TL", "kilit sonrasi yazim uygulandi")
    shutil.rmtree(repo, ignore_errors=True)


def main():
    print("duzelt.py --toplu kabul testi (SAHTE katalog; gercek urunler.json'a dokunulmaz)")
    test_a()
    test_b()
    test_c()
    test_d()
    print("\n%s" % ("TUM KONTROLLER GECTI." if not hatalar
                    else "BASARISIZ (%d): \n  - %s" % (len(hatalar), "\n  - ".join(hatalar))))
    return 0 if not hatalar else 1


if __name__ == "__main__":
    sys.exit(main())
