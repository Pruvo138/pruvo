#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""talepler tablosu icin 90 gunluk, durumdan bagimsiz temizlik araci."""

import argparse
import contextlib
import importlib.util
import io
import re
import sqlite3
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


SAKLAMA_GUN = 90
TAHMIN_TAVAN = 5000  # TAHMIN
KOD_ALFABE = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
KOD_UZUNLUGU = 6
KOD_DESENI = re.compile(
    r"^PR-[" + re.escape(KOD_ALFABE) + r"]{" + str(KOD_UZUNLUGU) + r"}$"
)
L9_IZINLI_DOSYALAR = {
    "tools/talep-temizlik.py", "tools/talep-hatti-test.py"
}


def esik_zamani(now=None):
    return (now or datetime.now(timezone.utc)) - timedelta(days=SAKLAMA_GUN)


def karar_ver(satirlar, esik, tavan):
    """D1 ve sqlite yurutuculerinin ortak, saf karar yordamidir."""
    sirali = []
    for kod, olusturma in satirlar:
        try:
            zaman = datetime.fromisoformat(olusturma.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            continue
        if zaman < esik:
            sirali.append((olusturma, kod))
    sirali = sorted(sirali, key=lambda kayit: (kayit[0], kayit[1]))
    parti = [kod for _, kod in sirali[:tavan]]
    return parti, len(sirali) - len(parti)


def sil_eski(baglanti, kodlar):
    """Yalniz verilen kod listesini siler; listeyi yeniden hesaplamaz."""
    toplam = 0
    for baslangic in range(0, len(kodlar), 500):
        parca = kodlar[baslangic:baslangic + 500]
        yerler = ",".join("?" for _ in parca)
        sonuc = baglanti.execute(
            "DELETE FROM talepler WHERE kod IN (" + yerler + ")", parca)
        toplam += sonuc.rowcount if sonuc.rowcount >= 0 else len(parca)
    return toplam


class SqliteYurutucu:
    def __init__(self, baglanti):
        self.baglanti = baglanti

    def satirlari_getir(self):
        return self.baglanti.execute(
            "SELECT kod, olusturma FROM talepler ORDER BY olusturma, kod"
        ).fetchall()

    def sil(self, kodlar):
        return sil_eski(self.baglanti, kodlar)


def _lazy_d1_wrangler():
    try:
        from d1_sync import wrangler
        return wrangler
    except ModuleNotFoundError:
        yol = Path(__file__).with_name("d1-sync.py")
        spec = importlib.util.spec_from_file_location("d1_sync", yol)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul.wrangler


class D1Yurutucu:
    def __init__(self, calistir=None):
        self.calistir = calistir or _lazy_d1_wrangler()
        self.karantina_kod = 0

    def _zarf(self, sql):
        zarf = self.calistir(["--command", sql])
        if not isinstance(zarf, list) or not zarf or not isinstance(zarf[0], dict):
            raise ValueError("D1 zarf sekli gecersiz")
        return zarf[0]

    def satirlari_getir(self):
        zarf = self._zarf(
            "SELECT kod, olusturma FROM talepler ORDER BY olusturma, kod")
        return [(satir["kod"], satir["olusturma"])
                for satir in zarf.get("results", [])]

    def sil(self, kodlar):
        toplam = 0
        izinli = []
        self.karantina_kod = 0
        for kod in kodlar:
            if kod_gecerli(kod):
                izinli.append(kod)
            else:
                self.karantina_kod += 1
        for baslangic in range(0, len(izinli), 500):
            parca = izinli[baslangic:baslangic + 500]
            ifadeler = ",".join("'" + str(kod).replace("'", "''") + "'"
                                 for kod in parca)
            zarf = self._zarf(
                "DELETE FROM talepler WHERE kod IN (" + ifadeler + ")")
            meta = zarf.get("meta", {})
            degisen = meta.get("changes")
            if degisen is None and zarf.get("results"):
                degisen = zarf["results"][0].get("changes")
            if degisen is None:
                raise RuntimeError(
                    "OLCULEMEDI: D1 changes bildirmedi (silinen sayi dogrulanamadi)"
                )
            toplam += int(degisen)
        return toplam


def kod_gecerli(kod):
    return isinstance(kod, str) and KOD_DESENI.fullmatch(kod) is not None


def _satir_yaz(uygula, sayi, kalan, kodlar, okunan=None, karantina=0):
    print("KURU=" + str(int(not uygula)) + " SILINECEK=" + str(sayi))
    print("KALAN=" + str(kalan))
    if okunan is not None:
        print("SORGU_KOSTU=EVET OKUNAN_SATIR=" + str(okunan))
    print("KARANTINA_KOD=" + str(karantina) +
          " TEMIZ=" + ("HAYIR" if karantina else "EVET"))
    print("ORNEK=" + ",".join(str(kod) for kod in kodlar[:5]))
    if not uygula:
        print("UYARI: silinen kod artik COZULEMEZ (Faz-2 'PR-...' aramasi bos doner).")


def calistir(db_yolu, uygula=False, d1=False, tavan=TAHMIN_TAVAN, yurutucu=None):
    if d1:
        yurutucu = yurutucu or D1Yurutucu()
        esik = esik_zamani()
        try:
            satirlar = yurutucu.satirlari_getir()
        except BaseException as hata:
            if "no such table" in str(hata).lower() and "talepler" in str(hata).lower():
                print("OLCULEMEDI: talepler tablosu canlida YOK")
                return 1
            raise
        kodlar, kalan = karar_ver(satirlar, esik, tavan)
        karantina = 0
        if uygula and kodlar:
            silinen = yurutucu.sil(kodlar)
            karantina = getattr(yurutucu, "karantina_kod", 0)
            if silinen != len(kodlar) - karantina:
                raise RuntimeError("D1 silinen kume sayilan kumeden ayristi")
        _satir_yaz(uygula, len(kodlar) - karantina, kalan, kodlar,
                   okunan=len(satirlar), karantina=karantina)
        return 0
    if db_yolu is None:
        print("KURU=1 SILINECEK=0 DB=YOK")
        print("KALAN=0")
        return 0
    yol = Path(db_yolu)
    if not yol.exists():
        print("KURU=" + str(int(not uygula)) + " SILINECEK=0 DB=YOK")
        print("KALAN=0")
        return 0
    with sqlite3.connect(yol) as baglanti:
        yurutucu = yurutucu or SqliteYurutucu(baglanti)
        esik = esik_zamani()
        kodlar, kalan = karar_ver(yurutucu.satirlari_getir(), esik, tavan)
        if uygula and kodlar:
            silinen = yurutucu.sil(kodlar)
            if silinen != len(kodlar):
                raise RuntimeError("sqlite silinen kume sayilan kumeden ayristi")
            baglanti.commit()
        _satir_yaz(uygula, len(kodlar), kalan, kodlar)
    return 0


def _fikstur(simdi):
    return [
        ("PR-Z89XYZ", (simdi - timedelta(days=89)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
        ("PR-P89XYZ", (simdi - timedelta(days=89)).isoformat()),
        ("PR-Z92XYZ", (simdi - timedelta(days=91)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
        ("PR-P92XYZ", (simdi - timedelta(days=91)).isoformat()),
        ("PR-BOZUK", "belli-degil"),
    ]


class SahteD1:
    def __init__(self, satirlar):
        self.satirlar = list(satirlar)
        self.silinen = []
        self.sql = []

    def calistir(self, argumanlar):
        sql = argumanlar[-1]
        self.sql.append(sql)
        if sql.startswith("SELECT"):
            return [{"results": [{"kod": kod, "olusturma": zaman}
                                  for kod, zaman in self.satirlar]}]
        kodlar = [kod for kod, _ in self.satirlar
                  if "'" + kod.replace("'", "''") + "'" in sql]
        self.silinen.extend(kodlar)
        return [{"results": [], "meta": {"changes": len(kodlar)}}]


def _sqlite_fikstur(satirlar):
    dosya = tempfile.NamedTemporaryFile(prefix="k190-talep-", suffix=".sqlite3")
    baglanti = sqlite3.connect(dosya.name)
    baglanti.execute("CREATE TABLE talepler (kod TEXT PRIMARY KEY, olusturma TEXT NOT NULL)")
    baglanti.executemany("INSERT INTO talepler (kod, olusturma) VALUES (?, ?)", satirlar)
    baglanti.commit()
    return dosya, baglanti


def f5_statik():
    """Silme yordamının karar hesabından bağımsız kaldığını ölçer."""
    return (sil_eski.__code__.co_argcount == 2 and
            "karar_ver" not in sil_eski.__code__.co_names)


def r1_davranissal():
    """91 günlük tek kaydın uygula koluyla gerçekten silindiğini ölçer."""
    simdi = datetime.now(timezone.utc)
    kayit = ("PR-R1", (simdi - timedelta(days=91)).isoformat())
    dosya, baglanti = _sqlite_fikstur([kayit])
    try:
        baglanti.close()
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            rc = calistir(dosya.name, uygula=True)
        with sqlite3.connect(dosya.name) as kontrol:
            kalan = kontrol.execute("SELECT COUNT(*) FROM talepler").fetchone()[0]
        return rc == 0 and kalan == 0
    finally:
        dosya.close()


class L10SahteD1:
    def __init__(self, satirlar=None, tablo_var=True):
        self.satirlar = list(satirlar or [])
        self.tablo_var = tablo_var

    def calistir(self, argumanlar):
        sql = argumanlar[-1]
        if not self.tablo_var:
            raise SystemExit("no such table: talepler")
        if sql.startswith("SELECT"):
            return [{"results": [{"kod": kod, "olusturma": zaman}
                                  for kod, zaman in self.satirlar]}]
        return [{"results": [], "meta": {"changes": 0}}]


class DegisensizD1:
    def calistir(self, argumanlar):
        return [{"results": []}]


def _d1_kuru_olc(yurutucu):
    cikti = io.StringIO()
    with contextlib.redirect_stdout(cikti):
        rc = calistir(None, d1=True, yurutucu=D1Yurutucu(yurutucu))
    return rc, cikti.getvalue()


def l10_olc():
    """D1 kuru kolunda yok, boş ve eski tablo hallerini ayırt eder."""
    simdi = datetime.now(timezone.utc)
    eski = ("PR-L10", (simdi - timedelta(days=91)).isoformat())
    yok_rc, yok_cikti = _d1_kuru_olc(
        L10SahteD1(tablo_var=False).calistir)
    bos_rc, bos_cikti = _d1_kuru_olc(
        L10SahteD1().calistir)
    eski_rc, eski_cikti = _d1_kuru_olc(
        L10SahteD1([eski]).calistir)
    yok = (yok_rc != 0 and
           "OLCULEMEDI: talepler tablosu canlida YOK" in yok_cikti and
           "SILINECEK=" not in yok_cikti)
    bos = (bos_rc == 0 and
           "SILINECEK=0" in bos_cikti and
           "KALAN=0" in bos_cikti and
           "SORGU_KOSTU=EVET" in bos_cikti and
           "OKUNAN_SATIR=0" in bos_cikti)
    eski_ok = (eski_rc == 0 and
               "SILINECEK=1" in eski_cikti and
               "SORGU_KOSTU=EVET" in eski_cikti and
               "OKUNAN_SATIR=1" in eski_cikti)
    return yok and bos and eski_ok


def d1_changes_olc():
    """D1 değişiklik sayısı yoksa kapının ölçümsüz kalmasını ölçer."""
    try:
        D1Yurutucu(DegisensizD1().calistir).sil(["PR-Z92XYZ"])
    except RuntimeError as hata:
        return str(hata) == (
            "OLCULEMEDI: D1 changes bildirmedi (silinen sayi dogrulanamadi)"
        )
    return False


def _l9_olc():
    proje = Path.cwd()
    artigi = list((proje / "tools").glob("*mutant*"))
    durum = __import__("subprocess").run(
        ["git", "status", "--porcelain"], cwd=proje,
        capture_output=True, text=True)
    yabanci = [satir for satir in durum.stdout.splitlines()
               if not any(yol in satir for yol in L9_IZINLI_DOSYALAR)]
    return not yabanci and not artigi


def kabul_bataryasi(mutant=None):
    simdi = datetime(2026, 8, 19, tzinfo=timezone.utc)
    esik = esik_zamani(simdi)
    temel = _fikstur(simdi)
    tavan = 2
    sqlite_dosya, sqlite = _sqlite_fikstur(temel)
    try:
        sqlite_yurutucu = SqliteYurutucu(sqlite)
        d1_sahte = SahteD1(temel)
        d1_yurutucu = D1Yurutucu(d1_sahte.calistir)
        sqlite_karar = karar_ver(sqlite_yurutucu.satirlari_getir(), esik, tavan)
        d1_karar = karar_ver(d1_yurutucu.satirlari_getir(), esik, tavan)
        l1 = sqlite_karar == d1_karar
        l1b = kabul_bataryasi.__code__.co_argcount == 1 and kaynakta_tek_karar()
        l2 = karar_ver(temel, esik, 2) == (["PR-P92XYZ", "PR-Z92XYZ"], 0)
        kuru_d1 = SahteD1(temel)
        calistir(sqlite_dosya.name, d1=False, tavan=2,
                 yurutucu=D1Yurutucu(kuru_d1.calistir))
        l3 = not kuru_d1.silinen
        bozuk = [("PR-BOZUK", "belli-degil"), ("PR-Z92XYZ", temel[2][1])]
        bozuk_d1 = SahteD1(bozuk)
        l4 = karar_ver(D1Yurutucu(bozuk_d1.calistir).satirlari_getir(), esik, 5)[0] == ["PR-Z92XYZ"]
        secim = ["PR-P92XYZ", "PR-Z92XYZ"]
        D1Yurutucu(d1_sahte.calistir).sil(secim)
        l5 = set(d1_sahte.silinen) == set(sqlite_karar[0])
        l6 = karar_ver(temel[:2], esik, 5)[0] == []
        l7 = karar_ver(temel, esik, 2) == karar_ver(list(reversed(temel)), esik, 2)
        l8 = kaynakta_tek_saklama()
        l9 = _l9_olc()
        l5b = d1_changes_olc()
        r1 = r1_davranissal()
        f5 = f5_statik()
        l10 = l10_olc()
        l11 = l11_olc()
        return {"L1": l1, "L1b": l1b, "L2": l2, "L3": l3, "L4": l4,
                "L5": l5, "L5b": l5b, "L6": l6, "L7": l7, "L8": l8,
                "L9": l9, "R1": r1, "F5": f5, "L10": l10,
                "L11a": l11["L11a"], "L11b": l11["L11b"],
                "L11c": l11["L11c"], "L11d": l11["L11d"]}
    finally:
        sqlite.close()
        sqlite_dosya.close()


def kaynakta_tek_karar():
    kaynak = Path(__file__).read_text(encoding="utf-8")
    govde = kaynak.split("def karar_ver", 1)[1].split("def sil_eski", 1)[0]
    return len(__import__("re").findall(r"^def karar_ver\(", kaynak, __import__("re").M)) == 1 and govde.count("datetime.fromisoformat") == 1


def kaynakta_tek_saklama():
    kaynak = Path(__file__).read_text(encoding="utf-8")
    govde = kaynak.split("def esik_zamani", 1)[1].split("def karar_ver", 1)[0]
    return len(__import__("re").findall(r"^SAKLAMA_GUN = 90$", kaynak, __import__("re").M)) == 1 and "timedelta(days=90)" not in govde


def _kanonik_talep_ayarlari():
    kanonik_yol = Path.cwd() / "shop" / "src" / "talep.js"
    if not kanonik_yol.exists():
        kanonik_yol = Path(__file__).resolve().parent.parent / "shop" / "src" / "talep.js"
    kaynak = kanonik_yol.read_text(encoding="utf-8")
    alfabe = re.search(r'export const TALEP_ALFABE = "([^"]+)";', kaynak)
    uzunluk = re.search(r"const KOD_UZUNLUGU = (\d+);", kaynak)
    if alfabe is None or uzunluk is None:
        raise RuntimeError("OLCULEMEDI: kanonik talep kodu ayarlari bulunamadi")
    return alfabe.group(1), int(uzunluk.group(1))


def l11_olc():
    """D1 DELETE sinirini, drift kapisini ve karantina alarmını ölçer."""
    simdi = datetime(2026, 8, 19, tzinfo=timezone.utc)
    eski = (simdi - timedelta(days=91)).isoformat()
    gecersiz = ["PR-A' OR 1=1--", "PR-AAAAA0"]
    gecerli = ["PR-P92XYZ", "PR-Z92XYZ"]
    sahte = SahteD1([(kod, eski) for kod in gecerli + gecersiz])
    cikti = io.StringIO()
    with contextlib.redirect_stdout(cikti):
        rc = calistir(None, uygula=True, d1=True, tavan=5000,
                      yurutucu=D1Yurutucu(sahte.calistir))
    delete_sql = [sql for sql in sahte.sql if sql.startswith("DELETE")]
    metin = cikti.getvalue()
    karantina = re.search(r"KARANTINA_KOD=(\d+)", metin)
    red_olculdu = (rc == 0 and
                   all(kod not in sql for sql in delete_sql for kod in gecersiz) and
                   all(kod not in sahte.silinen for kod in gecersiz) and
                   karantina is not None and int(karantina.group(1)) > 0)
    mesru_silindi = all(kod in sahte.silinen for kod in gecerli)
    kanonik_alfabe, kanonik_uzunluk = _kanonik_talep_ayarlari()
    drift_uyumlu = (kanonik_alfabe == KOD_ALFABE and
                    kanonik_uzunluk == KOD_UZUNLUGU)

    temiz_sahte = SahteD1([(kod, eski) for kod in gecerli])
    temiz_cikti = io.StringIO()
    with contextlib.redirect_stdout(temiz_cikti):
        temiz_rc = calistir(None, uygula=True, d1=True, tavan=5000,
                            yurutucu=D1Yurutucu(temiz_sahte.calistir))
    temiz_metin = temiz_cikti.getvalue()
    alarm_cikti = io.StringIO()
    with contextlib.redirect_stdout(alarm_cikti):
        _satir_yaz(True, 0, 0, [], karantina=2)
    alarm_metin = alarm_cikti.getvalue()
    alarm = ("KARANTINA_KOD=2" in alarm_metin and
             "TEMIZ=HAYIR" in alarm_metin and temiz_rc == 0 and
             "KARANTINA_KOD=0" in temiz_metin and "TEMIZ=EVET" in temiz_metin)
    return {"L11a": red_olculdu, "L11b": mesru_silindi,
            "L11c": drift_uyumlu, "L11d": alarm}


def mutant_bataryasi(temel):
    tanimlar = {
        "L1": ("l1 = " + "sqlite_karar == d1_karar", "l1 = False"),
        "L1b": ("l1b = " + "kabul_bataryasi.__code__.co_argcount == 1 and kaynakta_tek_karar()", "l1b = False"),
        "L2": ("l2 = karar_ver(temel, esik, " + "2) == ([\"PR-P92XYZ\", \"PR-Z92XYZ\"], 0)", "l2 = False"),
        "L3": ("l3 = " + "not kuru_d1.silinen", "l3 = False"),
        "L4": ("l4 = karar_ver(D1Yurutucu(bozuk_d1.calistir).satirlari_getir(), esik, " + "5)[0] == [\"PR-Z92XYZ\"]", "l4 = False"),
        "L5": ("l5 = " + "set(d1_sahte.silinen) == set(sqlite_karar[0])", "l5 = False"),
        "L5b": (
            "            if degisen is None:\n"
            "                raise RuntimeError(\n"
            "                    \"OLCULEMEDI: D1 changes bildirmedi (silinen sayi dogrulanamadi)\"\n"
            "                )",
            "            if degisen is None:\n"
            "                degisen = len(parca)"),
        "L6": ("l6 = karar_ver(temel[:2], esik, " + "5)[0] == []", "l6 = False"),
        "L7": ("l7 = karar_ver(temel, esik, " + "2) == karar_ver(list(reversed(temel)), esik, 2)", "l7 = False"),
        "L8": ("l8 = " + "kaynakta_tek_saklama()", "l8 = False"),
        "L9": ("l9 = " + "_l9_olc()", "l9 = False"),
        "R1": (
            "        if uygula and kodlar:\n"
            "            silinen = yurutucu.sil(kodlar)\n"
            "            if silinen != len(kodlar):\n"
            "                raise RuntimeError(\"sqlite silinen kume sayilan kumeden ayristi\")",
            "        if False and kodlar:\n"
            "            silinen = yurutucu.sil(kodlar)\n"
            "            if silinen != len(kodlar):\n"
            "                raise RuntimeError(\"sqlite silinen kume sayilan kumeden ayristi\")"),
        "F5": (
            "    return (sil_eski.__code__.co_argcount == 2 and\n"
            "            \"karar_ver\" not in sil_eski.__code__.co_names)",
            "    return False"),
        "L10-1": ("                print(\"OLCULEMEDI: talepler tablosu canlida YOK\")", "                print(\"OLCULEMEDI: talepler tablosu canlida YOK SILINECEK=0\")"),
        "L10-2": ("        print(\"SORGU_KOSTU=EVET OKUNAN_SATIR=\" + str(okunan))", "        print(\"OKUNAN_SATIR=\" + str(okunan))"),
        "L10-3": ("    print(\"KURU=\" + str(int(not uygula)) + \" SILINECEK=\" + str(sayi))", "    print(\"KURU=\" + str(int(not uygula)) + \" SILINECEK=0\")"),
        "L11a": (
            "KOD_DESENI = re.compile(\n"
            "    r\"^PR-[\" + re.escape(KOD_ALFABE) + r\"]{\" + str(KOD_UZUNLUGU) + r\"}$\"\n"
            ")",
            "KOD_DESENI = re.compile(r\"^PR-[A-Z0-9]{6}$\")"),
        "L11a-sizinti": ("            if kod_" + "gecerli(kod):", "            if True:"),
        "L11c": ("kanonik_uzunluk == " + "KOD_UZUNLUGU", "kanonik_uzunluk == " + "KOD_UZUNLUGU - 1"),
        "L11d": (
            "          \" TEMIZ=\" + (\"HAYIR\" if karantina else \"EVET\"))",
            "          \" TEMIZ=EVET\")"),
    }
    sonuc = []
    scratch = Path(tempfile.mkdtemp(prefix="k190-mutants-"))
    try:
        for ad, (arama, degisim) in tanimlar.items():
            kaynak = Path(__file__).read_text(encoding="utf-8")
            if kaynak.count(arama) != 1:
                sonuc.append((ad, False, [], "OLCULEMEDI: mutant arama benzersiz degil"))
                continue
            mutant = kaynak.replace(arama, degisim, 1)
            yol = None
            try:
                dosya = tempfile.NamedTemporaryFile(prefix="k190-mutant-", suffix=".py",
                                                     dir=scratch, delete=False)
                dosya.write(mutant.encode("utf-8"))
                dosya.close()
                yol = Path(dosya.name)
                derleme = compile(mutant, str(yol), "exec")
                del derleme
                calisma = __import__("subprocess").run(
                    [sys.executable, str(yol), "--kendini-test", "--mutant-run=" + ad],
                    capture_output=True, text=True)
                kalan = kabul_anahtar_sonuclari(calisma.stdout)
                dusen = [isim for isim, gecti in kalan.items() if not gecti]
                kaynak_farki = mutant != kaynak
                hedef_adi = {"L10-1": "L10", "L10-2": "L10", "L10-3": "L10",
                             "L11a-sizinti": "L11a"}.get(ad, ad)
                hedef = dusen == [hedef_adi]
                sonuc.append((ad, kaynak_farki and hedef, dusen,
                              "derlenebilir=EVET hedef_kol_atfi=" + ("EVET" if hedef else "HAYIR")))
            finally:
                if yol and yol.exists():
                    yol.unlink()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return sonuc


def kabul_anahtar_sonuclari(cikti):
    satir = next((satir for satir in cikti.splitlines() if satir.startswith("KABUL_BATARYASI=")), "")
    govde = satir[len("KABUL_BATARYASI="):]
    return {parca.split("=", 1)[0]: parca.split("=", 1)[1] == "GECTI"
            for parca in govde.split() if "=" in parca}


def kendini_test(mutant=None):
    if mutant:
        sonuclar = kabul_bataryasi(mutant)
        print("KABUL_BATARYASI=" + " ".join(ad + "=" + ("GECTI" if sonuclar[ad] else "DUSTU")
                                              for ad in sonuclar))
        return 0 if all(sonuclar.values()) else 1
    simdi = datetime.now(timezone.utc)
    dosya, baglanti = _sqlite_fikstur(_fikstur(simdi))
    try:
        esik = esik_zamani(simdi)
        kuru = karar_ver(SqliteYurutucu(baglanti).satirlari_getir(), esik, 5000)[0]
        silinen = sil_eski(baglanti, kuru)
        baglanti.commit()
        kalan = {kod for (kod,) in baglanti.execute("SELECT kod FROM talepler").fetchall()}
        f1 = len(kuru) == silinen == 2
        f2 = "PR-Z92XYZ" not in kalan and "PR-P92XYZ" not in kalan
        f3 = "PR-Z89XYZ" in kalan and "PR-P89XYZ" in kalan
        f4 = "PR-BOZUK" in kalan
        f5 = f5_statik()
        r1 = r1_davranissal()
    finally:
        baglanti.close()
        dosya.close()
    l_sonuclar = kabul_bataryasi()
    mutant_sonuclari = mutant_bataryasi(l_sonuclar)
    mutant_ok = sum(int(ok) for _, ok, _, _ in mutant_sonuclari)
    izole = sum(int(ok and "OLCULEMEDI" not in detay) for _, ok, _, detay in mutant_sonuclari)
    olculemedi = sum(int("OLCULEMEDI" in detay) for _, _, _, detay in mutant_sonuclari)
    sonuc = f1 and f2 and f3 and f4 and f5 and r1 and all(l_sonuclar.values()) and mutant_ok == len(mutant_sonuclari)
    print("KENDINI_TEST=" + ("GECTI" if sonuc else "DUSTU") +
          " F1=" + ("GECTI" if f1 else "DUSTU") +
          " F2=" + ("GECTI" if f2 else "DUSTU") +
          " F3=" + ("GECTI" if f3 else "DUSTU") +
          " F4=" + ("GECTI" if f4 else "DUSTU") +
          " F5=" + ("GECTI" if f5 else "DUSTU") +
          " R1=" + ("GECTI" if r1 else "DUSTU"))
    print("L-SONUCLARI=" + " ".join(ad + "=" + ("GECTI" if l_sonuclar[ad] else "DUSTU")
                                       for ad in l_sonuclar))
    print("MUTANT=" + str(mutant_ok) + "/" + str(len(mutant_sonuclari)) +
          " HEDEF_KOL_ATFI=" + str(mutant_ok) + "/" + str(len(mutant_sonuclari)) +
          " HAYATTA_KALAN=" + str(len(mutant_sonuclari) - mutant_ok) +
          " IZOLE=" + str(izole) + " OLCULEMEDI=" + str(olculemedi))
    for ad, ok, dusen, detay in mutant_sonuclari:
        print("MUTANT " + ad + " dusen_kume=" + str(dusen) + " " + detay)
    return 0 if sonuc else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path)
    parser.add_argument("--d1", action="store_true")
    parser.add_argument("--uygula", action="store_true")
    parser.add_argument("--kuru", action="store_true")
    parser.add_argument("--tavan", type=int, default=TAHMIN_TAVAN)
    parser.add_argument("--kendini-test", action="store_true")
    parser.add_argument("--mutant-run")
    args = parser.parse_args()
    if args.kuru and args.uygula:
        parser.error("--kuru ile --uygula birlikte kullanilamaz")
    if args.kendini_test:
        return kendini_test(args.mutant_run)
    return calistir(args.db, args.uygula, args.d1, args.tavan)


if __name__ == "__main__":
    sys.exit(main())
