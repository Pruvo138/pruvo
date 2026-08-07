"""PRUVO Ortak Drive'indaki STL klasorunun yolunu bulur — hesap adi degisse bile.

Neden var: yol, hesabin e-postasini iceriyor (.../GoogleDrive-<hesap>/Ortak Drive'lar/...).
Hesap yeniden adlandirilinca (15 Tem 2026: ONCEKI kurumsal hesaptan bugunku hesaba
gecildi) Drive uygulamasi mount klasorunun adini degistirir ve `.stl-backup-dir` bayatlar.
🔴 ONCEKI HESABIN ALAN ADI BURAYA YAZILMAZ: depo PUBLIC ve o ad baska bir ticari
olusuma aittir; tarihce notu icin ad DEGIL olay yeterlidir.

Eskiden bu SESSIZCE kiriliyordu, en tehlikeli yaniydi:
  - thingiverse-fetch/printables-fetch: `if os.path.isdir(bdir)` -> yedegi sessizce ATLAR
  - yedekle.py / thing-hazirla.py: `os.makedirs(...)` -> Drive yerine SAHTE yerel klasor yaratir
Iki durumda da "yedek aliniyor" sanip yedeksiz kalirdin.

Artik: (1) kayitli yolu dene, (2) tutmazsa mount'lari tara ve `.stl-backup-dir`'i kendin duzelt,
(3) hicbiri olmazsa GURULTULU uyar — sessizce gecme.
"""
import glob
import importlib.util
import os
import sys


def _kok():
    """`.stl-backup-dir`'in yasadigi kok: ANA calisma agaci (worktree DEGIL).

    🔴 NEDEN SABIT YAZILMIYOR (7 Agu 2026): kok eskiden "<gelistirici-evi>/depo" sabitiydi.
    O yol CI kosucusunda YOKTUR; ayni desen tools/cgt-ekle.py'de FileNotFoundError verip
    serit-a3'u kirmizi yakti ve deploy+yayin SKIPPED kaldi (yayin 4+ saat kapali). Yerelde
    HIC kirmizi yanmaz — yol bu makinede cozulur — yani "testler yesil" bu sinif icin kor.

    🔴 NEDEN NAIF `__file__` DE DEGIL: yedekle-test.py::_gercek_pruvo_dizini_saltokunur
    (yorumu: "worktree'de bile ana checkout'u gosterir") bu modulun ANA kopyayi hedefledigi
    varsayimina dayanir; `stl_dizini()` bayat kaydi DUZELTIRKEN CFG'ye YAZAR. Naif turetim
    o yazmayi worktree'ye kaydirirdi -> onbellek her worktree'de bastan taranir ve
    yedekle-test'in ".stl-backup-dir degismedi" nobetcisi BASKA bir dosyayi izlemeye baslar.
    Bu yuzden kok tools/veri_kok.py'ye SORULUR (tek kaynak; git'e sorar, worktree'de ANA
    kopyayi, temiz klonda/CI'da klonun kokunu verir).

    🔴 NEDEN try/except: yedekle-test.py::mutant_yaz bu dosyayi gecici bir dizine YALNIZ
    BASINA kopyalar (kardes veri_kok.py oraya gitmez). Sert bagimlilik o kabul testini
    kirardi; kardes yoksa kod koku'ne DUSER (o senaryoda gecici agac git deposu bile
    degildir, yani veri_kok da ayni degeri uretirdi). Ikiz tanim YOK: mantik veri_kok'ta.
    """
    kendi_dizin = os.path.dirname(os.path.abspath(__file__))
    vk_yol = os.path.join(kendi_dizin, "veri_kok.py")
    if os.path.exists(vk_yol):
        try:
            spec = importlib.util.spec_from_file_location("veri_kok_drive", vk_yol)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.cozumle(__file__)[1]
        except Exception:                                          # noqa: BLE001
            pass
    return os.path.dirname(kendi_dizin)


ROOT = _kok()
CFG = os.path.join(ROOT, ".stl-backup-dir")
# Hesap adi degisebilir -> GoogleDrive-* joker. Ortak Drive adi ("PRUVO/Pruvo") sabit.
DESEN = os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/Ortak Drive'lar/PRUVO/Pruvo/STL")


def stl_dizini(sessiz=False):
    """Canli STL klasoru yolunu dondurur; bulunamazsa None (ve uyarir).

    Bayat `.stl-backup-dir`'i bulursa kendisi duzeltir — bir dahaki sefere tarama gerekmez.
    """
    kayitli = open(CFG).read().strip() if os.path.exists(CFG) else ""
    if kayitli and os.path.isdir(kayitli):
        return kayitli

    bulunan = sorted(glob.glob(DESEN))
    if bulunan:
        yeni = bulunan[0]
        try:
            with open(CFG, "w") as w:
                w.write(yeni)
            if not sessiz:
                print("NOT: Drive yolu degismis, .stl-backup-dir duzeltildi -> " + yeni, file=sys.stderr)
        except Exception as e:
            if not sessiz:
                print("NOT: Drive yolu bulundu ama .stl-backup-dir yazilamadi: " + str(e), file=sys.stderr)
        return yeni

    if not sessiz:
        print(
            "UYARI: PRUVO Ortak Drive'i bulunamadi -> STL YEDEGI ALINMIYOR.\n"
            "  Kayitli yol: " + (kayitli or "(yok)") + "\n"
            "  Drive uygulamasi acik mi? Hesap baglantisi duruyor mu? (Hesap adi degistiyse\n"
            "  klasor adi da degisir; Drive'i acip yeniden giris yapmak yeter.)",
            file=sys.stderr,
        )
    return None


def pruvo_dizini(sessiz=False):
    """STL'in ust klasoru (.../Pruvo) — backup/ ve lisans belge/ orada. Yoksa None."""
    stl = stl_dizini(sessiz=sessiz)
    return os.path.dirname(stl) if stl else None
