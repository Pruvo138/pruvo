#!/usr/bin/env python3
"""duzelt-toplu-test.py — tools/duzelt.py --toplu (batch) kipi kabul testi.

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
  (f) --alan aciklama REWORD'unde OTOMATIK EKLENEN OLCU SATIRI korunur
      (MaCiT dilim-30 kaybi): korunma, ciftleme yok, gomulu satir, placeholder,
      toplu kip, guard manifest gercekligi, alan regresyonu, desen kaymasi,
      KIRMIZI-MUTASYON.
  (g) GORSEL-KOKEN KAPISI GERCEK YAYIM YOLUNDA (U2 — DEVAM.md madde 10):
      koken kaniti olmadan figur (kategori "Skan Art") sayfa gorseli yayinlanamaz.
      Kapsanan: gorsel degisimi, kategori CEVIRME deligi, gecerli manifest GECER,
      1-baytlik sahte render, sahte STL, sha256 uyusmazligi, YANLIS-POZITIF
      kontrolu (platform kategorileri + dokunulmayan Skan Art), toplu kip,
      urun-ekle.py merge_safe kablolamasi, KIRMIZI-MUTASYON.
  (h) ALT KATEGORI KAPISI TOPLU EKLEME YOLUNDA (urun-ekle.py merge_safe): bilinmeyen
      deger, izinli-ama-yanlis-kategori, tedarikci IMZASI, YANLIS-POZITIF kontrolu
      (gecerli/alansiz/bos parti gecer), KIRMIZI-MUTASYON.
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
KAYNAK_KOKEN = os.path.join(KOK, "tools", "gorsel_koken.py")
KAYNAK_ARAMA = os.path.join(KOK, "tools", "arama.py")
KAYNAK_URUN_EKLE = os.path.join(KOK, "tools", "urun-ekle.py")

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


def sahte_repo(katalog=None):
    d = tempfile.mkdtemp(prefix="duzelt-toplu-testi-")
    os.makedirs(os.path.join(d, "tools"))
    shutil.copy(KAYNAK_DUZELT, os.path.join(d, "tools", "duzelt.py"))
    shutil.copy(KAYNAK_GUARD, os.path.join(d, "tools", "urunler-guard.py"))
    # duzelt.py gorsel_koken.py'yi KOSULSUZ import eder (nobetci "dosyasi yoksa gecer"
    # olamaz) -> sahte repoya da kopyalanmali.
    shutil.copy(KAYNAK_KOKEN, os.path.join(d, "tools", "gorsel_koken.py"))
    # duzelt.py arama.py'yi de KOSULSUZ import eder (alt kategori taksonomisi + imza
    # nobeti orada TEK kaynak olarak yasar) -> sahte repoya kopyalanmali.
    shutil.copy(KAYNAK_ARAMA, os.path.join(d, "tools", "arama.py"))
    with open(os.path.join(d, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(KATALOG if katalog is None else katalog, f, ensure_ascii=False, indent=2)
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


# ---------------------------------------------------------------- (e) konfigur whitelist
# Yapisal bosluk kapatildi: DEGISTIRILEBILIR'e "konfigur" eklendi (mevcut urunun konfigur
# alani mesru araçla — duzelt.py --toplu — yazilabilsin). urunler-guard.py alan-agnostik +
# deger-bagli oldugu icin GUVENLIK MODELI DEGISMEZ (yeni alan ozel muamele gormez).
KONF = {
    "renkler": ["Siyah"], "renkGorselIndeks": {"Siyah": 0},
    "boyutMm": {"min": 60, "max": 300, "adim": 10, "varsayilan": 150, "etiket": "Yukseklik"},
    "hacim": {"refYukseklikMm": 1899.739, "refHacimCm3": 239222.8},
    "fiyatCapalari": [[60, 150], [300, 1300]],
    "malzemeler": [{"ad": "PLA", "katsayi": 1.0}, {"ad": "PETG", "katsayi": 1.3}],
    "varsayilanMalzeme": "PLA",
}


def test_konfigur():
    print("\n(e) konfigur alani: whitelist KABUL + guard deger-bagli izin + KIRMIZI-MUTASYON")
    # (a) konfigur op KABUL + guard._authorized deger-bagli mesru/gayrimesru ayrimi
    repo = sahte_repo()
    mod = modul_yukle(repo, "duzelt.py", "duzelt_konf")
    guard = modul_yukle(repo, "urunler-guard.py", "guard_konf")
    kontrol("konfigur" in mod.DEGISTIRILEBILIR,
            "DEGISTIRILEBILIR 'konfigur' icerir (yapisal bosluk kapandi)")
    yol = islem_yaz(repo, [{"id": "test-urun-1", "alan": "konfigur", "deger": KONF}])
    rc, out, err = cagir(mod, ["--toplu", yol])
    kontrol(rc == 0, "konfigur op exit 0 (%s)" % (err.strip() or out.strip().splitlines()[-1:]))
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        yeni = {p["id"]: p for p in json.load(f)}
    kontrol(yeni["test-urun-1"].get("konfigur") == KONF, "urun-1 konfigur alani yazildi")
    kontrol(yeni["test-urun-1"]["baslik"] == "Test Urun 1"
            and yeni["test-urun-2"]["fiyat"] == "200 TL", "beyan disi alanlara DOKUNULMADI")
    with open(os.path.join(repo, ".urunler-duzelt-izin.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    kontrol(guard._authorized("test-urun-1", "konfigur", yeni["test-urun-1"], manifest),
            "guard._authorized: konfigur MESRU (deger manifestle birebir esit)")
    bozuk = dict(yeni["test-urun-1"])
    bozuk_konf = json.loads(json.dumps(KONF))
    bozuk_konf["fiyatCapalari"] = [[60, 999], [300, 1300]]      # farkli deger
    bozuk["konfigur"] = bozuk_konf
    kontrol(not guard._authorized("test-urun-1", "konfigur", bozuk, manifest),
            "guard._authorized: BEYAN DISI konfigur degeri mesru DEGIL (deger-bagli izin)")
    shutil.rmtree(repo, ignore_errors=True)

    # (b) KIRMIZI-MUTASYON: whitelist'ten 'konfigur' cikar -> ayni op REDDEDILIR (nobetci canli).
    repo2 = sahte_repo()
    mod2 = modul_yukle(repo2, "duzelt.py", "duzelt_konf_mut")
    mod2.DEGISTIRILEBILIR = frozenset(x for x in mod2.DEGISTIRILEBILIR if x != "konfigur")
    urunler_yol = os.path.join(repo2, "urunler.json")
    once = sha(urunler_yol)
    yol2 = islem_yaz(repo2, [{"id": "test-urun-1", "alan": "konfigur", "deger": KONF}])
    rc, out, err = cagir(mod2, ["--toplu", yol2])
    cikti = out + err
    kontrol(rc == 2, "MUTASYON: konfigur whitelist DISIYKEN op REDDEDILIR (rc=2, olculen %s)" % rc)
    kontrol("REDDEDILDI" in cikti, "MUTASYON: 'REDDEDILDI' uyarisi basildi")
    kontrol("izinsiz alan" in cikti, "MUTASYON: 'izinsiz alan' gerekcesi ciktida")
    kontrol(sha(urunler_yol) == once, "MUTASYON: urunler.json BYTE-ESIT (hicbir yazim yok)")
    kontrol(not os.path.exists(os.path.join(repo2, ".urunler-duzelt-izin.json")),
            "MUTASYON: izin manifesti OLUSMADI")
    shutil.rmtree(repo2, ignore_errors=True)


# ------------------------------------------------- (f) aciklama olcu satiri korumasi
# MaCiT dilim-30 (olculmus kayip): denetim kapisi yanlis-pozitifi yuzunden bir sekstant
# urununun aciklamasi `--alan aciklama` ile yeniden yazildi; STL'den turetilmis
# "Yaklaşık dış ölçüler: A × B × C mm." satiri SESSIZCE dustu. Kayip sessiz: urun canliya
# olcusuz cikar, musteri eksik bilgiyle siparis verir. Bu bolum kaybi kirmizi yakar.
OLCU_ESKI = "Yaklaşık dış ölçüler: 149 × 149 × 80 mm."
OLCU_YENI = "Yaklaşık dış ölçüler: 200 × 100 × 50 mm."
OLCU_GOMULU = "- Yaklaşık dış ölçüler: 42 × 30 × 8 mm."
YENI_METIN = ("Sekstant için yedek gölge filtresi tutucusu.\n"
              "- Paslanmaz vidalarla monte edilir.")

KATALOG_OLCU = [
    {"id": "olcu-son", "kategori": "Marin", "marka": [], "baslik": "Olcu Son",
     "aciklama": "Kayak taşıma arabası.\n- Kayışla bağlanır.\n" + OLCU_ESKI,
     "fiyat": "100 TL", "gorseller": ["https://media.pruvo3d.com/urunler/o1-1.jpg"]},
    {"id": "olcu-gomulu", "kategori": "Otomobil", "marka": ["Ford"], "baslik": "Olcu Gomulu",
     "aciklama": "Braket.\n" + OLCU_GOMULU + "\n- Dayanıklı malzemeyle özel üretilir.",
     "fiyat": "200 TL", "gorseller": ["https://media.pruvo3d.com/urunler/o2-1.jpg"]},
    {"id": "olcu-yok", "kategori": "Ev", "marka": [], "baslik": "Olcu Yok",
     "aciklama": "Basit conta.\nSipariş için \"Sipariş Ver\" butonundan bize ulaşın.",
     "fiyat": "300 TL", "gorseller": ["https://media.pruvo3d.com/urunler/o3-1.jpg"]},
    {"id": "olcu-placeholder", "kategori": "Ofis", "marka": [], "baslik": "Olcu Placeholder",
     "aciklama": "Ölçüsü verilmemiş ürün.\nYaklaşık dış ölçüler: yok.",
     "fiyat": "400 TL", "gorseller": ["https://media.pruvo3d.com/urunler/o4-1.jpg"]},
]

CAPA = "Yaklaşık dış ölçüler"


def _oku(repo):
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        return {p["id"]: p for p in json.load(f)}


def test_f_koruma():
    print("\n(f1) reword: olcu satiri KORUNUR (ONCE-KIRMIZI kanit)")
    repo = sahte_repo(KATALOG_OLCU)
    mod = modul_yukle(repo, "duzelt.py", "duzelt_f1")
    rc, out, err = cagir(mod, ["olcu-son", "--alan", "aciklama", "--deger", YENI_METIN])
    kontrol(rc == 0, "exit 0 (%s)" % err.strip())
    yeni = _oku(repo)["olcu-son"]["aciklama"]
    print("  --- yazilan aciklama ---")
    for satir in yeni.split("\n"):
        print("      | %s" % satir)
    print("  --- duzelt.py ciktisi ---")
    for satir in (out + err).strip().split("\n"):
        print("      > %s" % satir[:160])
    kontrol(OLCU_ESKI in yeni, "olcu satiri KORUNDU (yeni metinde yoktu)")
    kontrol(yeni.count(CAPA) == 1, "olcu satiri TEK kez (ciftleme yok)")
    kontrol(yeni.startswith(YENI_METIN), "yeni metin AYNEN ve BASTA duruyor")
    kontrol("KORUNDU" in (out + err), "cikti korumayi ACIKCA soyluyor ('KORUNDU')")
    kontrol(OLCU_ESKI in (out + err), "cikti korunan SATIRIN kendisini yaziyor")
    shutil.rmtree(repo, ignore_errors=True)


def test_f_ciftleme():
    print("\n(f2) yeni metin KENDI olcu satirini tasiyorsa YENISI kazanir, ciftleme YOK")
    repo = sahte_repo(KATALOG_OLCU)
    mod = modul_yukle(repo, "duzelt.py", "duzelt_f2")
    metin = YENI_METIN + "\n" + OLCU_YENI
    rc, out, err = cagir(mod, ["olcu-son", "--alan", "aciklama", "--deger", metin])
    kontrol(rc == 0, "exit 0 (%s)" % err.strip())
    yeni = _oku(repo)["olcu-son"]["aciklama"]
    print("  --- yazilan aciklama ---")
    for satir in yeni.split("\n"):
        print("      | %s" % satir)
    kontrol(yeni == metin, "yeni metin AYNEN yazildi (araca ek yapmadi)")
    kontrol(yeni.count(CAPA) == 1, "olcu satiri TEK kez (ciftleme yok)")
    kontrol(OLCU_YENI in yeni and OLCU_ESKI not in yeni, "YENI olcu kazandi, eski dusuruldu")
    kontrol("DEGISTI" in (out + err) or "değişti" in (out + err).lower(),
            "cikti eski olcunun degistigini soyluyor")
    shutil.rmtree(repo, ignore_errors=True)


def test_f_gomulu():
    print("\n(f3) olcu satiri aciklamanin ORTASINDA (liste isaretli) ise de korunur")
    repo = sahte_repo(KATALOG_OLCU)
    mod = modul_yukle(repo, "duzelt.py", "duzelt_f3")
    rc, out, err = cagir(mod, ["olcu-gomulu", "--alan", "aciklama", "--deger", YENI_METIN])
    kontrol(rc == 0, "exit 0 (%s)" % err.strip())
    yeni = _oku(repo)["olcu-gomulu"]["aciklama"]
    print("  --- yazilan aciklama ---")
    for satir in yeni.split("\n"):
        print("      | %s" % satir)
    kontrol("Yaklaşık dış ölçüler: 42 × 30 × 8 mm." in yeni, "gomulu olcu satiri KORUNDU")
    kontrol(yeni.count(CAPA) == 1, "TEK kez")
    kontrol(yeni.strip().split("\n")[-1].startswith("Yaklaşık"),
            "sona eklenirken liste isareti ('- ') temizlendi")
    # kapsam disi birakilan satis satiri: korunmaz AMA raporlanir
    kontrol("Dayanıklı malzemeyle" not in yeni, "satis/CTA satiri korunmadi (kapsam disi)")
    kontrol("DUSTU" in (out + err), "dusen satir ciktida 'DUSTU' olarak raporlandi")
    shutil.rmtree(repo, ignore_errors=True)


def test_f_placeholder():
    print("\n(f4) placeholder olcu satiri ('… : yok.') korunmaz ama SESSIZ de dusmez")
    repo = sahte_repo(KATALOG_OLCU)
    mod = modul_yukle(repo, "duzelt.py", "duzelt_f4")
    rc, out, err = cagir(mod, ["olcu-placeholder", "--alan", "aciklama", "--deger", YENI_METIN])
    kontrol(rc == 0, "exit 0 (%s)" % err.strip())
    yeni = _oku(repo)["olcu-placeholder"]["aciklama"]
    kontrol(yeni == YENI_METIN, "sayisiz placeholder geri yazilmadi")
    kontrol("DUSTU" in (out + err) and "yok." in (out + err),
            "placeholder dususu ciktida ACIKCA raporlandi")
    print("  --- duzelt.py ciktisi ---")
    for satir in (out + err).strip().split("\n"):
        print("      > %s" % satir[:160])
    shutil.rmtree(repo, ignore_errors=True)


def test_f_toplu():
    print("\n(f5) --toplu kipinde de AYNI koruma (ayni delik, ayni yama)")
    repo = sahte_repo(KATALOG_OLCU)
    mod = modul_yukle(repo, "duzelt.py", "duzelt_f5")
    yol = islem_yaz(repo, [
        {"id": "olcu-son", "alan": "aciklama", "deger": YENI_METIN},
        {"id": "olcu-gomulu", "alan": "fiyat", "deger": "999 TL"},
    ])
    rc, out, err = cagir(mod, ["--toplu", yol])
    kontrol(rc == 0, "exit 0 (%s)" % err.strip())
    d = _oku(repo)
    print("  --- yazilan aciklama ---")
    for satir in d["olcu-son"]["aciklama"].split("\n"):
        print("      | %s" % satir)
    kontrol(OLCU_ESKI in d["olcu-son"]["aciklama"], "toplu kipte olcu satiri KORUNDU")
    kontrol(d["olcu-son"]["aciklama"].count(CAPA) == 1, "TEK kez")
    kontrol(d["olcu-gomulu"]["fiyat"] == "999 TL", "ayni partideki diger alan etkilenmedi")
    kontrol("KORUNDU" in (out + err), "toplu ciktida koruma raporlandi")
    shutil.rmtree(repo, ignore_errors=True)


def test_f_guard():
    print("\n(f6) guard manifesti GERCEGI tasir (korunmus metin) — yoksa guard geri alir")
    repo = sahte_repo(KATALOG_OLCU)
    mod = modul_yukle(repo, "duzelt.py", "duzelt_f6")
    guard = modul_yukle(repo, "urunler-guard.py", "guard_f6")
    rc, out, err = cagir(mod, ["olcu-son", "--alan", "aciklama", "--deger", YENI_METIN])
    kontrol(rc == 0, "exit 0")
    urun = _oku(repo)["olcu-son"]
    with open(os.path.join(repo, ".urunler-duzelt-izin.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    kontrol(manifest["olcu-son"]["aciklama"] == urun["aciklama"],
            "manifest = urunler.json'daki GERCEK deger (korunmus metin)")
    kontrol(guard._authorized("olcu-son", "aciklama", urun, manifest),
            "guard._authorized: yazilan deger MESRU (guard geri almaz)")
    kontrol(not guard._authorized("olcu-son", "aciklama",
                                 dict(urun, aciklama=YENI_METIN), manifest),
            "guard._authorized: olcusuz ham metin MESRU DEGIL (deger-bagli izin korunuyor)")
    shutil.rmtree(repo, ignore_errors=True)


def test_f_alan_regresyonu():
    print("\n(f7) REGRESYON: diger alanlar (baslik/fiyat/kategori/marka/gorseller) etkilenmedi")
    for alan, deger, beklenen in (
        ("baslik", "Yeni Baslik", "Yeni Baslik"),
        ("fiyat", "1234 TL", "1234 TL"),
        ("kategori", "Elektronik", "Elektronik"),
        ("marka", '["Audi","BMW"]', ["Audi", "BMW"]),
        ("gorseller", '["https://media.pruvo3d.com/urunler/yeni-1.jpg"]',
         ["https://media.pruvo3d.com/urunler/yeni-1.jpg"]),
    ):
        repo = sahte_repo(KATALOG_OLCU)
        mod = modul_yukle(repo, "duzelt.py", "duzelt_f7_" + alan)
        onceki_aciklama = _oku(repo)["olcu-son"]["aciklama"]
        rc, out, err = cagir(mod, ["olcu-son", "--alan", alan, "--deger", deger])
        d = _oku(repo)["olcu-son"]
        kontrol(rc == 0, "[%s] exit 0 (%s)" % (alan, err.strip()))
        kontrol(d[alan] == beklenen, "[%s] deger yazildi (%r)" % (alan, d[alan]))
        kontrol(d["aciklama"] == onceki_aciklama,
                "[%s] aciklama HIC DEGISMEDI (koruma yolu tetiklenmedi)" % alan)
        kontrol("ACIKLAMA KORUMA" not in (out + err),
                "[%s] aciklama raporu basilmadi (gurultu yok)" % alan)
        shutil.rmtree(repo, ignore_errors=True)


def test_f_desen_kaymasi():
    print("\n(f8) DESEN KAYMASI: duzelt.py olcu deseni denetim-kapisi.py ile AYNI karari verir")
    repo = sahte_repo(KATALOG_OLCU)
    mod = modul_yukle(repo, "duzelt.py", "duzelt_f8")
    dk_yol = os.path.join(KOK, "tools", "denetim-kapisi.py")
    spec = importlib.util.spec_from_file_location("denetim_kapisi_f8", dk_yol)
    dk = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(dk)      # FAIL-CLOSED: import kirilirsa kapi susmaz, KIRMIZI yanar
    except Exception as e:               # noqa: BLE001 — kasitli genis yakalama, gerekce yukarida
        kontrol(False, "denetim-kapisi.py import edilemedi -> desen kaymasi DENETLENEMEDI (%r)" % e)
        shutil.rmtree(repo, ignore_errors=True)
        return
    fikstur = [
        "Yaklaşık dış ölçüler: 149 × 149 × 80 mm.",
        "Yaklaşık dış ölçüler: 40 x 20 x 10 mm.",
        "- Yaklaşık dış ölçüler: 42 × 30 × 8 mm.",
        "Yaklaşık dış ölçüler (15 cm boyda): 113 × 117 × 150 mm.",
        "Yaklaşık dış ölçüler: taban 137 × 135 × 70 mm.",
        "Yaklasik dis olculer: 64 × 64 × 30 mm.",
        "Yaklaşık dış ölçüler: Ø30 × 12 mm.",
        "Yaklaşık dış ölçüler: yok.",
        "Yaklaşık dış ölçüler: Belirtilmemiş.",
        "Yaklaşık dış ölçüler: - × - × - mm.",
        "M32×3.5 vida dişi, ~31 mm dış çap",
        "Sıradan bir açıklama satırı.",
    ]
    olcu_re = getattr(mod, "_OLCU_RE", None)
    if olcu_re is None:
        kontrol(False, "duzelt.py'de _OLCU_RE yok (koruma uygulanmamis)")
        shutil.rmtree(repo, ignore_errors=True)
        return
    ayrisan = [s for s in fikstur
               if bool(olcu_re.search(s)) != bool(dk._OLCU_RE.search(s))]
    for s in fikstur:
        print("      %s  %s" % ("OLCU " if olcu_re.search(s) else "     ", s))
    kontrol(not ayrisan, "12 fiksturun HEPSINDE ayni karar (ayrisan: %s)" % ayrisan)
    shutil.rmtree(repo, ignore_errors=True)


def test_f_mutasyon():
    print("\n(f9) KIRMIZI-MUTASYON: koruma devre disi birakilinca satir GERCEKTEN dusuyor")
    repo = sahte_repo(KATALOG_OLCU)
    mod = modul_yukle(repo, "duzelt.py", "duzelt_f9")
    if not hasattr(mod, "aciklama_koru"):
        kontrol(False, "duzelt.py'de aciklama_koru yok (koruma uygulanmamis)")
        shutil.rmtree(repo, ignore_errors=True)
        return
    mod.aciklama_koru = lambda eski, yeni: (yeni, [])   # mutasyon: koruma yok
    rc, out, err = cagir(mod, ["olcu-son", "--alan", "aciklama", "--deger", YENI_METIN])
    yeni = _oku(repo)["olcu-son"]["aciklama"]
    kontrol(rc == 0, "mutasyonlu kosum yine de exit 0")
    kontrol(CAPA not in yeni,
            "MUTASYON: koruma kapaliyken olcu satiri DUSTU (nobetci canli, testi kandirmiyor)")
    kontrol("KORUNDU" not in (out + err), "MUTASYON: koruma raporu da basilmadi")
    shutil.rmtree(repo, ignore_errors=True)


# ================================================= (g) GORSEL-KOKEN KAPISI ===
# U2 (DEVAM.md madde 10). ONCEKI DURUM (olculdu, bu bolum yazilmadan once):
# koken dogrulamasi YALNIZ pruvo-jenerator/.claude/gorsel-koken-kapisi.py'de, bir
# Claude Code PreToolUse hook'unda (matcher Edit|Write|MultiEdit) yasiyordu ->
# urunler.json'a PYTHON ile yazan gercek yayim yollarinin (duzelt.py, urun-ekle.py
# merge_safe) HICBIRINDE ateslemiyordu. 3 yoldan 3'unde cipasiz gorsel yayinlandi.
# Bu bolum o yollari kirmizi yakar.
FIGUR = {"id": "sahte-figur", "kategori": "Skan Art", "marka": [],
         "baslik": "Sahte Figur", "aciklama": "figur", "fiyat": "900 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/sahte-figur-p1.jpg"]}
KATALOG_KOKEN = [dict(FIGUR)] + [dict(p) for p in KATALOG]
YENI_GORSELLER = ["https://media.pruvo3d.com/urunler/metinden-uretilmis-p1.jpg",
                  "https://media.pruvo3d.com/urunler/metinden-uretilmis-p2.jpg"]


@contextlib.contextmanager
def koken_dizini(repo, kur=True):
    """Koken dizinini DETERMINISTIK yap: makinedeki gercek manifest deposu (KaaN)
    testin sonucunu etkilemesin."""
    d = os.path.join(repo, "urun-gorsel-koken")
    if kur:
        os.makedirs(d, exist_ok=True)
    eski = os.environ.get("GORSEL_KOKEN_DIR")
    os.environ["GORSEL_KOKEN_DIR"] = d
    try:
        yield d
    finally:
        if eski is None:
            os.environ.pop("GORSEL_KOKEN_DIR", None)
        else:
            os.environ["GORSEL_KOKEN_DIR"] = eski


def _stl_yaz(yol, ucgen=3):
    """Sayaci boyutla TUTAN gercek bir binary STL (kapi bicimi dogruluyor)."""
    with open(yol, "wb") as f:
        f.write(b"\x00" * 80)
        f.write(ucgen.to_bytes(4, "little"))
        f.write(b"\x00" * (50 * ucgen))
    return yol


def _png_yaz(yol, bayt=4096):
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(b"\x00" * max(0, bayt - 8))
    return yol


def _manifest_yaz(dizin, pid, gorseller, stl, sha_stl=None, sha_gorsel=None):
    man = {"kaynak_stl": stl,
           "gorseller": [{"dosya": os.path.basename(u),
                          "taban_render": tr} for u, tr in gorseller]}
    if sha_stl is not None:
        man["kaynak_stl_sha256"] = sha_stl
    if sha_gorsel is not None:
        for g in man["gorseller"]:
            g["sha256"] = sha_gorsel
    yol = os.path.join(dizin, pid + ".json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    return yol


def _tam_manifest(repo, dizin, pid="sahte-figur", gorseller=None,
                  render_bayt=4096, ucgen=3, sha_stl=None, sha_gorsel=None):
    """Gecerli bir koken kaydi kurar (STL + her gorsel icin taban render)."""
    varlik = os.path.join(repo, "varlik")
    os.makedirs(varlik, exist_ok=True)
    stl = _stl_yaz(os.path.join(varlik, pid + ".stl"), ucgen=ucgen)
    ciftler = []
    for i, url in enumerate(gorseller if gorseller is not None else YENI_GORSELLER, 1):
        ciftler.append((url, _png_yaz(os.path.join(varlik, "%s-r%d.png" % (pid, i)),
                                      bayt=render_bayt)))
    return _manifest_yaz(dizin, pid, ciftler, stl, sha_stl=sha_stl, sha_gorsel=sha_gorsel)


def _g_senaryo(ad, kur, beklenen_blok, arg=None):
    """Tek senaryo: repo kur -> duzelt.py cagir -> yazildi mi / byte-esit mi."""
    repo = sahte_repo(KATALOG_KOKEN)
    urunler_yol = os.path.join(repo, "urunler.json")
    once = sha(urunler_yol)
    with koken_dizini(repo) as dizin:
        if kur:
            kur(repo, dizin)
        mod = modul_yukle(repo, "duzelt.py", "duzelt_g_" + ad.replace(" ", "_")[:20])
        rc, out, err = cagir(mod, arg or ["sahte-figur", "--alan", "gorseller",
                                          "--deger", json.dumps(YENI_GORSELLER)])
    sonra = sha(urunler_yol)
    if beklenen_blok:
        kontrol(rc != 0, "%s: exit != 0 (olculen %s)" % (ad, rc))
        kontrol(once == sonra, "%s: urunler.json BYTE-ESIT (yazim YOK)" % ad)
        kontrol(not os.path.exists(os.path.join(repo, ".urunler-duzelt-izin.json")),
                "%s: guard izin manifesti de OLUSMADI" % ad)
        kontrol("GORSEL-KOKEN" in (out + err), "%s: gerekce ciktida gecti" % ad)
    else:
        kontrol(rc == 0, "%s: exit 0 (olculen %s | %s)" % (ad, rc, (err or out).strip()[:160]))
        kontrol(once != sonra, "%s: yazim GERCEKLESTI (yanlis-pozitif YOK)" % ad)
    shutil.rmtree(repo, ignore_errors=True)


def test_g_manifestsiz():
    print("\n(g1) manifest YOK -> figur gorseli yayinlanamaz")
    _g_senaryo("manifestsiz", None, True)


def test_g_gecerli():
    print("\n(g2) GECERLI manifest -> yayin GECER (kapi kilitlemiyor)")
    _g_senaryo("gecerli manifest", lambda r, d: _tam_manifest(r, d), False)


def test_g_kategori_cevirme():
    print("\n(g3) KATEGORI CEVIRME deligi: gorsellere dokunmadan Skan Art'a cevirme")
    _g_senaryo("kategori cevirme", None, True,
               arg=["test-urun-1", "--alan", "kategori", "--deger", "Skan Art"])


def test_g_sahte_render():
    print("\n(g4) 1 BAYTLIK sahte taban_render -> BLOCK (eski kapi bunu geciriyordu)")
    _g_senaryo("1 baytlik render", lambda r, d: _tam_manifest(r, d, render_bayt=1), True)


def test_g_sahte_stl():
    print("\n(g5) kaynak_stl gercek STL DEGIL -> BLOCK")

    def kur(repo, dizin):
        _tam_manifest(repo, dizin)
        with open(os.path.join(repo, "varlik", "sahte-figur.stl"), "wb") as f:
            f.write(b"BU BIR STL DEGIL" * 20)   # boyut yeterli, bicim degil
    _g_senaryo("sahte STL", kur, True)


def test_g_sha_uyusmazligi():
    print("\n(g6) beyan edilen sha256 diskle TUTMUYOR -> BLOCK (icerik baglama)")
    _g_senaryo("sha256 uyusmazligi",
               lambda r, d: _tam_manifest(r, d, sha_gorsel="0" * 64), True)


def test_g_yanlis_pozitif():
    print("\n(g7) YANLIS-POZITIF KONTROLU: platform kategorisi + dokunulmayan figur")
    _g_senaryo("platform urununde gorsel degisimi", None, False,
               arg=["test-urun-2", "--alan", "gorseller",
                    "--deger", json.dumps(YENI_GORSELLER)])
    _g_senaryo("figurun BASKA alani (gorseller sabit)", None, False,
               arg=["sahte-figur", "--alan", "fiyat", "--deger", "1234 TL"])
    _g_senaryo("figur SILME (yayin degil)", None, False,
               arg=["sahte-figur", "--sil", "test"])


def test_g_toplu():
    print("\n(g8) TOPLU kip: koken ihlali -> hicbir islem uygulanmaz (ya hep ya hic)")
    repo = sahte_repo(KATALOG_KOKEN)
    urunler_yol = os.path.join(repo, "urunler.json")
    once = sha(urunler_yol)
    with koken_dizini(repo):
        mod = modul_yukle(repo, "duzelt.py", "duzelt_g8")
        yol = islem_yaz(repo, [
            {"id": "test-urun-1", "alan": "fiyat", "deger": "555 TL"},
            {"id": "sahte-figur", "alan": "gorseller", "deger": YENI_GORSELLER},
        ])
        rc, out, err = cagir(mod, ["--toplu", yol])
    kontrol(rc != 0, "toplu: exit != 0 (olculen %s)" % rc)
    kontrol(once == sha(urunler_yol), "toplu: urunler.json BYTE-ESIT (masum islem de yazilmadi)")
    kontrol("GORSEL-KOKEN" in (out + err), "toplu: gerekce ciktida gecti")
    shutil.rmtree(repo, ignore_errors=True)


def test_g_urun_ekle():
    print("\n(g9) urun-ekle.py merge_safe: koken kaniti olmadan figur KATALOGA GIREMEZ")
    repo = sahte_repo(KATALOG_KOKEN)
    with open(os.path.join(repo, ".urun-kaynaklari.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)
    hata = io.StringIO()
    with contextlib.redirect_stderr(hata):       # veri_kok worktree uyarisi
        spec = importlib.util.spec_from_file_location("urun_ekle_g9", KAYNAK_URUN_EKLE)
        ue = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ue)
    kontrol(hasattr(ue, "gk") and hasattr(ue.gk, "zorla"),
            "urun-ekle.py gorsel_koken modulunu KOSULSUZ import ediyor")
    ue.URUNLER = os.path.join(repo, "urunler.json")
    ue.KAYNAK = os.path.join(repo, ".urun-kaynaklari.json")
    ue.LOCK = os.path.join(repo, ".urunler.lock")
    ue.ROOT = repo
    once = sha(ue.URUNLER)
    staged = [{"id": "777", "urun": dict(FIGUR, id="yeni-figur",
                                         gorseller=list(YENI_GORSELLER)),
               "src": {"kaynak": "Thingiverse"}}]
    with koken_dizini(repo):
        try:
            ue.merge_safe(staged)
            engellendi = False
        except ue.gk.KokenIhlali:
            engellendi = True
    kontrol(engellendi, "merge_safe KokenIhlali firlatti (yazim yok)")
    kontrol(once == sha(ue.URUNLER), "merge_safe: urunler.json BYTE-ESIT")
    with open(os.path.join(repo, ".urun-kaynaklari.json"), encoding="utf-8") as f:
        kontrol(json.load(f) == {}, "merge_safe: gizli kaynak kaydi da yazilmadi")

    # POZITIF KOL: gecerli koken kaydiyla AYNI cagri gecmeli (kapi kilitlemiyor).
    with koken_dizini(repo) as dizin:
        _tam_manifest(repo, dizin, pid="yeni-figur")
        n, _toplam = ue.merge_safe(staged)
    kontrol(n == 1, "gecerli manifestle AYNI ekleme GECTI (olculen %s)" % n)
    shutil.rmtree(repo, ignore_errors=True)


def test_g_mutasyon():
    print("\n(g10) KIRMIZI-MUTASYON: kapi no-op yapilinca cipasiz gorsel GERCEKTEN yayinlaniyor")
    repo = sahte_repo(KATALOG_KOKEN)
    with koken_dizini(repo):
        mod = modul_yukle(repo, "duzelt.py", "duzelt_g10")
        if not (hasattr(mod, "gk") and hasattr(mod.gk, "denetle")):
            kontrol(False, "duzelt.py'de gorsel_koken kablolamasi YOK")
            shutil.rmtree(repo, ignore_errors=True)
            return
        mod.gk.denetle = lambda eski, yeni, kok: []      # MUTASYON: kapi no-op
        rc, out, err = cagir(mod, ["sahte-figur", "--alan", "gorseller",
                                   "--deger", json.dumps(YENI_GORSELLER)])
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        yeni = {p["id"]: p for p in json.load(f)}
    kontrol(rc == 0, "mutasyonlu kosum exit 0")
    kontrol(yeni["sahte-figur"]["gorseller"] == YENI_GORSELLER,
            "MUTASYON: kapi kapaliyken CIPASIZ gorsel yayinlandi "
            "(nobetci canli, testi kandirmiyor)")
    kontrol("GORSEL-KOKEN" not in (out + err), "MUTASYON: gerekce de basilmadi")
    shutil.rmtree(repo, ignore_errors=True)


# ============================================= (h) ALT KATEGORI KAPISI (ekleme) ===
# OLCULEN ACIK: `altkategori` iki yerde fail-closed dogrulaniyordu (duzelt.py rc=5 ve CI
# kapisi tools/altkategori-kapisi.py) ama TOPLU EKLEME yolu urun-ekle.py merge_safe hicbir
# dogrulama yapmiyordu -> yeni/tedarikci-imzali bir deger kataloga DENETIMSIZ girip ancak
# CI'da yakalaniyordu (pre-push d1-sync CI'dan ONCE kosar). Olculen vaka: 34 "Pervaneler".
# Bu bolum o yolu kirmizi yakar.
URUN_EKLE_MODULLERI = ("veri_kok.py", "filament_ortak.py", "gorsel_mukerrer_kapisi.py",
                       "gorsel_boyut_kapisi.py", "gorsel_koken.py", "r2_anahtar.py",
                       "arama.py")


def _urun_ekle_yukle(repo, ad, mutasyon=None):
    """urun-ekle.py'yi (istege bagli MUTASYONLU) SAHTE repo kopyasindan yukler.

    Kopya sart: mutasyon kaynak METINDE yapilir, gercek tools/urun-ekle.py'ye ASLA
    dokunulmaz. Betik modullerini KENDI dizininden yukledigi icin bagimliliklar da
    sahte repoya kopyalanir.
    """
    for m in URUN_EKLE_MODULLERI:
        hedef = os.path.join(repo, "tools", m)
        if not os.path.exists(hedef):
            shutil.copy(os.path.join(KOK, "tools", m), hedef)
    with open(KAYNAK_URUN_EKLE, encoding="utf-8") as f:
        kaynak = f.read()
    if mutasyon:
        kaynak, uygulandi = mutasyon(kaynak)
        kontrol(uygulandi, "MUTASYON kaynak metne UYGULANDI (aksi halde test bos kosardi)")
    yol = os.path.join(repo, "tools", "urun-ekle.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak)
    hata = io.StringIO()
    with contextlib.redirect_stderr(hata):       # veri_kok kok uyarisi
        spec = importlib.util.spec_from_file_location(ad, yol)
        ue = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ue)
    ue.URUNLER = os.path.join(repo, "urunler.json")
    ue.KAYNAK = os.path.join(repo, ".urun-kaynaklari.json")
    ue.LOCK = os.path.join(repo, ".urunler.lock")
    ue.ROOT = repo
    with open(ue.KAYNAK, "w", encoding="utf-8") as f:
        json.dump({}, f)
    return ue


def _staged(uid, kategori, altkategori=None, **ek):
    """STAGE kaydi kurar. altkategori=None -> alan HIC yok; "" -> alan bos."""
    urun = {"id": uid, "kategori": kategori, "marka": [], "baslik": "Parti " + uid,
            "aciklama": "parti aciklamasi", "fiyat": "500 TL",
            "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}
    if altkategori is not None:
        urun["altkategori"] = altkategori
    urun.update(ek)
    return {"id": uid, "urun": urun, "src": {"kaynak": "Thingiverse"}}


def _h_senaryo(ad, staged, beklenen_blok, ad_ek=""):
    """Parti merge_safe'e verilir; reddedilirse HICBIR dosya yazilmamis olmali."""
    repo = sahte_repo()
    ue = _urun_ekle_yukle(repo, "urun_ekle_h_" + ad_ek)
    once = sha(ue.URUNLER)
    once_kaynak = sha(ue.KAYNAK)
    with koken_dizini(repo):
        try:
            n, _toplam = ue.merge_safe(staged)
            engellendi, sebep = False, ""
        except ue.AltkategoriIhlali as e:
            engellendi, sebep, n = True, str(e), 0
    if beklenen_blok:
        kontrol(engellendi, "%s: AltkategoriIhlali firlatildi" % ad)
        kontrol(once == sha(ue.URUNLER), "%s: urunler.json BYTE-ESIT (yazim YOK)" % ad)
        kontrol(once_kaynak == sha(ue.KAYNAK),
                "%s: .urun-kaynaklari.json da BYTE-ESIT (gizli kayit yazilmadi)" % ad)
        kontrol("ALT KATEGORI KAPISI" in sebep and "ALTKATEGORI_IZINLI" in sebep,
                "%s: gerekce actionable (izinli kume + genisletme yolu)" % ad)
    else:
        kontrol(not engellendi, "%s: GECTI (yanlis-pozitif YOK)" % ad)
        kontrol(n == len(staged), "%s: %d kayit gercekten yazildi (olculen %s)"
                % (ad, len(staged), n))
        kontrol(once != sha(ue.URUNLER), "%s: urunler.json DEGISTI" % ad)
    shutil.rmtree(repo, ignore_errors=True)


def test_h_bilinmeyen_deger():
    print("\n(h1) BILINMEYEN altkategori -> merge_safe REDDEDER (hicbir sey yazilmaz)")
    _h_senaryo("uydurma etiket", [_staged("parti-uydurma", "Marin", "Uydurma Etiket")],
               True, "h1")


def test_h_yanlis_kategori():
    print("\n(h2) izinli deger AMA YANLIS kategori altinda -> REDDEDER")
    _h_senaryo("yanlis kategori", [_staged("parti-yanlis-kat", "Otomobil", "Pervaneler")],
               True, "h2")


def test_h_imza():
    print("\n(h3) tedarikci IMZASI tasiyan deger (rakam/SKU) -> REDDEDER")
    _h_senaryo("imza nobeti", [_staged("parti-imza", "Marin", "Sintine 2K")], True, "h3")


def test_h_yanlis_pozitif():
    print("\n(h4) YANLIS-POZITIF KONTROLU: gecerli deger + altkategorisiz parti GECER")
    _h_senaryo("gecerli deger", [_staged("parti-gecerli", "Marin", "Pervaneler")],
               False, "h4a")
    _h_senaryo("altkategori YOK", [_staged("parti-alansiz", "Otomobil")], False, "h4b")
    _h_senaryo("altkategori BOS", [_staged("parti-bos", "Otomobil", "")], False, "h4c")


def _mutasyon_noop(kaynak):
    """merge_safe'teki dogrulamayi NO-OP'a cevir (girinti bozulmadan)."""
    eski = "alt_ihlal = _altkategori_ihlalleri(yeni)"
    if eski not in kaynak:
        return kaynak, False
    return kaynak.replace(eski, "alt_ihlal = []  # MUTASYON", 1), True


def test_h_mutasyon():
    print("\n(h5) KIRMIZI-MUTASYON: kapi no-op yapilinca gecersiz altkategori GERCEKTEN giriyor")
    repo = sahte_repo()
    ue = _urun_ekle_yukle(repo, "urun_ekle_h5", mutasyon=_mutasyon_noop)
    staged = [_staged("parti-uydurma", "Marin", "Uydurma Etiket")]
    engellendi = False
    with koken_dizini(repo):
        try:
            ue.merge_safe(staged)
        except ue.AltkategoriIhlali:
            engellendi = True
    with open(ue.URUNLER, encoding="utf-8") as f:
        katalog = {p["id"]: p for p in json.load(f)}
    kontrol(not engellendi, "mutasyonlu kosum istisna FIRLATMADI")
    kontrol(katalog.get("parti-uydurma", {}).get("altkategori") == "Uydurma Etiket",
            "MUTASYON: kapi kapaliyken gecersiz altkategori KATALOGA GIRDI "
            "(nobetci canli, testi kandirmiyor)")
    shutil.rmtree(repo, ignore_errors=True)


def main():
    print("duzelt.py --toplu kabul testi (SAHTE katalog; gercek urunler.json'a dokunulmaz)")
    test_a()
    test_b()
    test_c()
    test_d()
    test_konfigur()
    test_f_koruma()
    test_f_ciftleme()
    test_f_gomulu()
    test_f_placeholder()
    test_f_toplu()
    test_f_guard()
    test_f_alan_regresyonu()
    test_f_desen_kaymasi()
    test_f_mutasyon()
    test_g_manifestsiz()
    test_g_gecerli()
    test_g_kategori_cevirme()
    test_g_sahte_render()
    test_g_sahte_stl()
    test_g_sha_uyusmazligi()
    test_g_yanlis_pozitif()
    test_g_toplu()
    test_g_urun_ekle()
    test_g_mutasyon()
    test_h_bilinmeyen_deger()
    test_h_yanlis_kategori()
    test_h_imza()
    test_h_yanlis_pozitif()
    test_h_mutasyon()
    print("\n%s" % ("TUM KONTROLLER GECTI." if not hatalar
                    else "BASARISIZ (%d): \n  - %s" % (len(hatalar), "\n  - ".join(hatalar))))
    return 0 if not hatalar else 1


if __name__ == "__main__":
    sys.exit(main())
