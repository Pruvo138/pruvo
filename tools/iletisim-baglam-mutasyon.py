#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/iletisim-baglam-mutasyon.py — ILETISIM YUZEYI NOBETCISI icin MUTASYON SURUCUSU.

Neyi kanitlar: tools/kisisel-veri-test.py icindeki "iletisim yuzeyi nobetcisi"
(telefon baglam ekseni T1/T2 · e-posta alan adi ekseni E1/E2 · kanonik desen kaynagi K1)
GERCEKTEN olcuyor mu. Anlatilan batarya kanit degildir; surucu depoda DURUR ve yeniden
kosturulabilir ([[mutasyon-kaniti-yeniden-uretilebilir]]).

KABUL (cikis kodu 0 icin HEPSI sart):
  * her OLDURUCU mutant KIRMIZI yakar,
  * her KONTROL mutant YESIL kalir,
  * DUSEN IDDIA KIMLIKLERI mutantlar arasinda AYRISIR — iki oldurucu mutant ayni
    kimlik kumesini dusuruyorsa ikisi ayri bir iddia OLCMUYOR demektir
    ([[beyan-edilmis-survivor]]); AYRISMAYAN sayisi 0 olmali,
  * ONBELLEK KANITI gecmeli (asagi).

🔴 PYTHON BYTECODE ONBELLEGI TUZAGI ([[mutasyon-bytecode-onbellegi]]) — ELE ALINDI VE
KANITLANDI: AYNI UZUNLUKTA bir mutasyon AYNI SANIYE icinde yazilirsa, importlib kaynak
dosyanin (mtime, boyut) ikilisini degismemis gorur ve __pycache__'teki ESKI .pyc'yi
kullanir; mutant diske yazilmistir ama CALISMAZ. O halde "mutant kirmizi yandi" hukmu
BIR ONCEKI mutantin iddiasina aittir. Bu surucu:
  (1) her mutasyondan sonra ilgili __pycache__ dizinlerini SILER,
  (2) kaynagin mtime'ini benzersiz ve ARTAN bir degere ceker,
  (3) cocuk sureci `-B` + PYTHONDONTWRITEBYTECODE=1 ile kosturur,
  (4) `--onbellek-kaniti` kolu ile TUZAGI ONCE URETIR sonra KAPATIR: ayni uzunlukta bir
      mutasyon, mtime GERI ALINARAK yazildiginda kapi YESIL kalir (tuzak dogrulandi),
      ayni mutasyon onbellek temizlenip mtime bumplandiginda KIRMIZI yanar (kapatildi).
      Iki hal de OLCULUR; biri beklenmedik cikarsa surucu KIRMIZI doner.

🔴 IZOLE KOPYA (7 Eki 2026): mutant ve onbellek tuzagi CANLI kaynaga YAZILMAZ. Her
mutant (ve onbellek kaniti) `mutasyon_kopya.kopyada_kos` ile gecici kopyada kurulur,
kapi KOPYADAN kosar (ROOT'u kendi __file__'indan turetir), kopya silinir. Eski
`_uygula`/`_geri_al` + `finally` yolu SIGKILL'de ev dosyasini mutant birakiyordu.

Kullanim:
    python3 tools/iletisim-baglam-mutasyon.py                 # tam batarya + onbellek kaniti
    python3 tools/iletisim-baglam-mutasyon.py --onbellek-kaniti   # yalniz onbellek kaniti
Cikis kodu: 0 gecti · 1 kaldi/ayristiramadi.
"""
import importlib.util
import os
import py_compile
import re
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "kisisel-veri-test.py")
KANONIK = os.path.join(TOOLS, "commit-mesaji-kapisi.py")
sys.path.insert(0, TOOLS)

from mutasyon_kopya import kopyada_kos, kopyada_mi  # noqa: E402


def _kopyada(yol, kopya):
    """Canli yolun (KAPI/KANONIK) kopya kokteki karsiligi."""
    return os.path.join(kopya, os.path.relpath(yol, ROOT))

# ---------------------------------------------------------------- IDDIA KIMLIK ESLEMESI
# Cikti satiri -> DUSEN IDDIA KIMLIGI. Kimlikler mutantlar arasinda karsilastirilir.
_KIMLIK = (
    ("OLCULEMEDI (K1)", "K1-OLCULEMEDI"),
    ("OLCULEMEDI (CANLILIK", "CANLILIK"),
    ("OLCULEMEDI (iletisim", "OLCULEMEDI"),
    ("FIKSTUR(kirmizi) KACTI — T1", "FIK-T1"),
    ("FIKSTUR(kirmizi) KACTI — T2", "FIK-T2"),
    ("FIKSTUR(kirmizi) KACTI — E1", "FIK-E1"),
    ("FIKSTUR(yesil) YANLIS-POZITIF", "FIK-YESIL"),
    ("E2 YARGISI OLU", "E2-OLU"),
    ("SIRA BOZUK", "SIRA"),
    ("GEREKCESIZ e-posta muafiyeti", "MUAF-GEREKCE"),
    ("MUAFIYET BICIMI BOZUK", "MUAF-BICIM"),
    ("E2E:", "E2E"),
    ("IDDIA KOSMADI", "DEFTER"),
    ("TABAN BOS", "TABAN"),
    ("TELEFON BAGLAM IHLALI (T1)", "T1"),
    ("TELEFON BAGLAM IHLALI (T2)", "T2"),
    ("TANINMAYAN E-POSTA ALAN ADI (E1)", "E1"),
    ("TEDARIKCI/SATICI ALAN ADI (E2)", "E2"),
)


def kimlikler(cikti):
    """Cocuk ciktisindan DUSEN IDDIA kimlik kumesi."""
    bulunan = set()
    for satir in (cikti or "").splitlines():
        for imza, kimlik in _KIMLIK:
            if imza in satir:
                bulunan.add(kimlik)
    return bulunan


# ---------------------------------------------------------------- MUTANTLAR
# (ad, oldurucu_mu, [(dosya, eski, yeni), ...], niyet)
MUTANTLAR = [
    ("M1 DESEN-KORLESTIR", True, [
        (KANONIK,
         r'_EPOSTA_RE = re.compile(r"[0-9A-Za-z._%+-]+@([0-9A-Za-z.-]+\.[A-Za-z]{2,})")',
         r'_EPOSTA_RE = re.compile(r"[0-9A-Za-z._%+-]+@([0-9A-Za-z.-]+\.[A-Za-z]{9,})")')],
     "KANONIK e-posta deseni korlestirilir (AYNI UZUNLUK — onbellek tuzagi adayi); "
     "e-posta ekseni hicbir host goremez"),

    # Capa 3 satir: `for yol in sorted(dosyalar):` kapida 2 kez geciyor (7 Eki 2026 olculdu,
    # surucu BAYAT); `taban["dosya"] += 1` izi onu iletisim_tara dongusune tekillestirir.
    ("M2 TARAMA-YUZEYINI-DARALT", True, [
        (KAPI,
         "    for yol in sorted(dosyalar):\n"
         "        metin = dosyalar[yol]\n"
         "        taban[\"dosya\"] += 1\n",
         "    for yol in sorted(dosyalar)[:1]:\n"
         "        metin = dosyalar[yol]\n"
         "        taban[\"dosya\"] += 1\n")],
     "tarama dongusu ilk dosyada durur -> yuzey daralir"),

    ("M3 MUAFIYET-LISTESINI-GENISLET", True, [
        (KAPI, "        if (host, yol) in _EPOSTA_MUAFIYET:",
         "        if (host, yol) or _EPOSTA_MUAFIYET:")],
     "muafiyet kosulu HER host icin dogru olur -> E1 tamamen sessizlesir"),

    ("M4 IDDIA-SAYACINI-SABITLE+IDDIA-ATLA", True, [
        (KAPI, "    eksik = sorted(_BEKLENEN_IDDIA - defter)",
         "    eksik = sorted(_BEKLENEN_IDDIA - _BEKLENEN_IDDIA)"),
        (KAPI, "        kusurlar.extend(telefon_baglam_kusurlari(yol, metin))",
         "        kusurlar.extend([])")],
     "defter kapisi sabitlenir VE telefon ekseni taramadan cikarilir "
     "(sayi tutar, iddia kosmaz)"),

    # Eski M5 (WA/arama capraz baglam kuralini tersine cevir) hedefi 28 Agu TEK HAT emriyle
    # KALKTI (capa 0 kez geciyordu). Telefon ekseninin bugunku ikinci iddiasi T2'dir.
    ("M5 T2-PV-COZUCUSUNU-ATLA", True, [
        (KAPI, "    if _ARAMA_RE.search(pv_birlestir(metin)):\n",
         "    if _ARAMA_RE.search(metin):\n")],
     "T2 pv (data-a..l) parcalarini birlestirmeden ham metne bakar -> T1'in kopyasi olur, "
     "pv-parcali yasak numara kacar"),

    ("M6 DESEN-MUAFIYET-SIRASINI-BOZ", True, [
        (KAPI, "        no = cmk._host_desen_isabeti(host, kayit)",
         "        no = None if (host, yol) in _EPOSTA_MUAFIYET "
         "else cmk._host_desen_isabeti(host, kayit)")],
     "muafiyet gizli desenden ONCE bakilir -> muaf bir host gizli ad olsa bile gecer"),

    ("M7 KANONIK-KAYNAGI-KOPAR", True, [
        (KAPI, "    kayit, kayit_hata = cmk.ozet_kaydi_yukle()",
         '    kayit, kayit_hata = cmk.ozet_kaydi_yukle("/yok/desen-ozetleri.json")')],
     "tek kanonik desen kaynagindan kopulur (ikiz tanim geri gelir)"),

    ("K1 KONTROL: salt yorum", False, [
        (KAPI, "def iletisim_tara(dosyalar, cmk, kayit, markalar):",
         "# KONTROL MUTANTI: salt yorum satiri — davranis DEGISMEZ.\n"
         "def iletisim_tara(dosyalar, cmk, kayit, markalar):")],
     "davranissiz degisiklik — YESIL kalmali (batarya asiri-duyarli degil)"),

    ("K2 KONTROL: rezerve liste sirasi", False, [
        (KAPI,
         '_REZERVE_ALAN = frozenset(("example.com", "example.net", "example.org", "ornek.com"))',
         '_REZERVE_ALAN = frozenset(("ornek.com", "example.org", "example.net", "example.com"))')],
     "kume elemanlarinin YAZIM sirasi degisir, KUME ayni — YESIL kalmali"),
]


# ---------------------------------------------------------------- KOSUM ALTYAPISI
def _pycache_temizle(kok):
    """`kok` altindaki __pycache__ dizinlerini siler (bayat .pyc mutantı maskeleyemesin).

    Yalniz KOPYA kokunde cagrilir — canli agacin onbellegine dokunulmaz."""
    for d in (os.path.join(kok, "tools", "__pycache__"), os.path.join(kok, "__pycache__")):
        if os.path.islink(d):
            continue
        shutil.rmtree(d, ignore_errors=True)


def _mtime_bump(yol, adim):
    """Kaynagin mtime'ini BENZERSIZ ve ARTAN bir degere ceker (ayni-saniye tuzagi)."""
    t = time.time() + 100 + adim * 10
    os.utime(yol, (t, t))


def _kos(ek_ortam=None, bayrakli=True, kopya=None):
    """Kapiyi kosar; `kopya` verilirse KOPYADAN (cwd=kopya), verilmezse canli agactan."""
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    if ek_ortam:
        ortam.update(ek_ortam)
    komut = [sys.executable]
    if bayrakli:
        komut.append("-B")
    komut += [_kopyada(KAPI, kopya) if kopya else KAPI, "--yalniz-iletisim"]
    p = subprocess.run(komut, capture_output=True, text=True, cwd=kopya or ROOT, env=ortam)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _mutant_metinleri(duzenlemeler):
    """[(dosya, eski, yeni)] -> ({rel: mutant metin}, hata). Canliya YAZMAZ, yalniz okur."""
    icerik = {}
    for yol, _e, _y in duzenlemeler:
        if yol not in icerik:
            with open(yol, encoding="utf-8") as f:
                icerik[yol] = f.read()
    for yol, eski, yeni in duzenlemeler:
        if icerik[yol].count(eski) != 1:
            return None, ("MUTASYON UYGULANAMADI: %s icinde hedef metin %d kez geciyor "
                          "(1 bekleniyordu) -> surucu BAYAT."
                          % (os.path.basename(yol), icerik[yol].count(eski)))
        icerik[yol] = icerik[yol].replace(eski, yeni, 1)
    return {os.path.relpath(y, ROOT): m for y, m in icerik.items()}, None


def _mutant_kos(metinler, adim):
    """Mutanti gecici kopyada kurar (onbellek silinir + mtime bump) ve kapiyi KOPYADAN kosar."""
    def kos(kopya):
        _pycache_temizle(kopya)
        for i, rel in enumerate(sorted(metinler)):
            _mtime_bump(os.path.join(kopya, rel), adim * 10 + i)
        return _kos(kopya=kopya)
    return kopyada_kos("iletisim-mutant-", metinler, kos)


# ---------------------------------------------------------------- ONBELLEK KANITI
_ONB_ESKI = (r'_EPOSTA_RE = re.compile(r"[0-9A-Za-z._%+-]+@'
             r'([0-9A-Za-z.-]+\.[A-Za-z]{2,})")')
_ONB_YENI = (r'_EPOSTA_RE = re.compile(r"[0-9A-Za-z._%+-]+@'
             r'([0-9A-Za-z.-]+\.[A-Za-z]{9,})")')


def onbellek_kaniti():
    """TUZAGI ONCE URETIR, SONRA KAPATIR. (gecti_mi, satirlar).

    Tum adimlar TEK bir gecici kopyada kosar; canli KANONIK'e ve canli __pycache__'e
    dokunulmaz, kopya `kopyada_kos` tarafindan silinir."""
    with open(KANONIK, encoding="utf-8") as f:
        asil = f.read()
    if asil.count(_ONB_ESKI) != 1 or len(_ONB_ESKI) != len(_ONB_YENI):
        return False, ["ONBELLEK KANITI KURULAMADI: hedef metin tek degil ya da "
                       "mutasyon AYNI UZUNLUKTA degil (%d vs %d)"
                       % (len(_ONB_ESKI), len(_ONB_YENI))]
    return kopyada_kos("iletisim-onbellek-", {}, lambda kopya: _onbellek_adimlari(kopya, asil))


def _onbellek_adimlari(kopya, asil):
    satirlar = []
    kanonik = _kopyada(KANONIK, kopya)
    kapi = _kopyada(KAPI, kopya)
    pycache = os.path.join(kopya, "tools", "__pycache__")
    if not kopyada_mi(kanonik, kopya):
        return False, ["ONBELLEK KANITI KURULAMADI: kanonik kaynak kopya DISINDA"]
    gecti = True
    # (0) Bayat .pyc URET. 🔴 Kapi sureci .pyc YAZMAZ: `git_ortami` import aninda
    # `sys.dont_write_bytecode = True` kurar (7 Eki 2026 olculdu: onbellek yazimi acik
    # kosumda bile kanonik .pyc 0). Tuzak yine GERCEKTIR — kapi .pyc OKUR ve onu baska
    # bir tuketici (kanonigi git_ortami'dan ONCE yukleyen herhangi bir surec) yazabilir.
    # O tuketici burada `py_compile` (TIMESTAMP gecersizlestirme = importlib varsayilani)
    # ile temsil edilir; eksen OLCULUR: .pyc var mi + kapi sureci yazdi mi.
    _pycache_temizle(kopya)
    ortam = dict(os.environ)
    ortam.pop("PYTHONDONTWRITEBYTECODE", None)
    p = subprocess.run([sys.executable, kapi, "--yalniz-iletisim"],
                       capture_output=True, text=True, cwd=kopya, env=ortam)
    kapi_yazdi = os.path.isfile(importlib.util.cache_from_source(kanonik))
    hedef_pyc = py_compile.compile(
        kanonik, cfile=importlib.util.cache_from_source(kanonik), doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
    satirlar.append("  (0) taban kosum rc=%d · kapi sureci kanonik .pyc yazdi=%s · "
                    "bayat .pyc (py_compile) %s"
                    % (p.returncode, "EVET" if kapi_yazdi else "HAYIR",
                       os.path.basename(hedef_pyc) if hedef_pyc and os.path.isfile(hedef_pyc)
                       else "YOK"))
    if p.returncode != 0 or not (hedef_pyc and os.path.isfile(hedef_pyc)):
        satirlar.append("  🔴 KANIT KURULAMADI: taban kirmizi ya da kanonik .pyc "
                        "uretilemedi -> tuzak kurulamaz, mitigasyon olculemez.")
        return False, satirlar
    st = os.stat(kanonik)

    # (1) TUZAK: ayni uzunlukta mutasyon + mtime GERI ALINIR + onbellek DURUR.
    with open(kanonik, "w", encoding="utf-8") as f:
        f.write(asil.replace(_ONB_ESKI, _ONB_YENI, 1))
    os.utime(kanonik, ns=(st.st_atime_ns, st.st_mtime_ns))
    p1 = subprocess.run([sys.executable, kapi, "--yalniz-iletisim"],
                        capture_output=True, text=True, cwd=kopya, env=ortam)
    satirlar.append("  (1) TUZAK (mtime geri alindi, .pyc duruyor) -> rc=%d %s"
                    % (p1.returncode, "YESIL (mutasyon UYGULANMADI)" if p1.returncode == 0
                       else "KIRMIZI (mutasyon uygulandi)"))
    if p1.returncode != 0:
        satirlar.append("     NOT: bu ortamda tuzak URETILEMEDI (loader kaynagi yine "
                        "de okudu). Mitigasyon yine de (2)'de olculuyor.")

    # (2) MITIGASYON: onbellek silinir + mtime bumplanir -> mutasyon UYGULANMALI.
    _pycache_temizle(kopya)
    _mtime_bump(kanonik, 999)
    p2 = subprocess.run([sys.executable, "-B", kapi, "--yalniz-iletisim"],
                        capture_output=True, text=True, cwd=kopya,
                        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    satirlar.append("  (2) MITIGASYON (.pyc silindi + mtime bump + -B) -> rc=%d %s"
                    % (p2.returncode, "KIRMIZI (mutasyon UYGULANDI)" if p2.returncode
                       else "YESIL (mutasyon HALA uygulanmadi)"))
    if p2.returncode == 0:
        satirlar.append("  🔴 MITIGASYON YETERSIZ: ayni uzunluktaki mutasyon hala "
                        "uygulanmiyor -> tum batarya hukmu SUPHELIDIR.")
        gecti = False
    else:
        satirlar.append("     dusen iddia kimlikleri: %s"
                        % ",".join(sorted(kimlikler(p2.stdout + p2.stderr))) or "-")
    return gecti, satirlar


# ---------------------------------------------------------------- ANA
def main():
    yalniz_kanit = "--onbellek-kaniti" in sys.argv[1:]

    print("ONBELLEK KANITI (ayni uzunluk + ayni saniye tuzagi):")
    kanit_gecti, kanit_satirlari = onbellek_kaniti()
    for s in kanit_satirlari:
        print(s)
    if yalniz_kanit:
        print("SONUC: %s" % ("GECTI" if kanit_gecti else "KALDI"))
        return 0 if kanit_gecti else 1

    print()
    rc0, cikti0 = _kos()
    print("TABAN (mutasyonsuz): rc=%d %s" % (rc0, "YESIL" if rc0 == 0 else "KIRMIZI"))
    if rc0 != 0:
        print("🔴 TABAN KIRMIZI — mutasyon olcumu anlamsiz. Cikti:")
        print(cikti0)
        return 1
    taban_satiri = [s for s in cikti0.splitlines() if s.startswith("YEŞİL")]
    for s in taban_satiri:
        print("  " + s)

    print()
    sonuc = []
    for adim, (ad, oldurucu, duzenlemeler, niyet) in enumerate(MUTANTLAR, start=1):
        metinler, hata = _mutant_metinleri(duzenlemeler)
        if hata:
            print("🔴 %-42s %s" % (ad, hata))
            sonuc.append((ad, oldurucu, None, set(), hata))
            continue
        rc, cikti = _mutant_kos(metinler, adim)
        kim = kimlikler(cikti) if rc != 0 else set()
        beklenen = "KIRMIZI" if oldurucu else "YEŞİL"
        gercek = "KIRMIZI" if rc != 0 else "YEŞİL"
        isaret = "✓" if beklenen == gercek else "🔴"
        print("%s %-42s beklenen=%-7s gercek=%-7s dusen iddia: %s"
              % (isaret, ad, beklenen, gercek, ",".join(sorted(kim)) or "-"))
        print("      niyet: %s" % niyet)
        sonuc.append((ad, oldurucu, rc, kim, None))

    # --- KABUL
    oldurucular = [s for s in sonuc if s[1]]
    kontroller = [s for s in sonuc if not s[1]]
    o_gecen = [s for s in oldurucular if s[2] not in (None, 0)]
    k_gecen = [s for s in kontroller if s[2] == 0]

    imzalar = {}
    for ad, _o, _rc, kim, _h in oldurucular:
        imzalar.setdefault(frozenset(kim), []).append(ad)
    ayrismayan = [adlar for adlar in imzalar.values() if len(adlar) > 1]
    ayrismayan_sayisi = sum(len(a) for a in ayrismayan)

    print()
    print("OLDURUCU: %d/%d · KONTROL: %d/%d · BENZERSIZ IMZA: %d/%d · AYRISMAYAN: %d"
          % (len(o_gecen), len(oldurucular), len(k_gecen), len(kontroller),
             len(imzalar), len(oldurucular), ayrismayan_sayisi))
    for adlar in ayrismayan:
        print("  🔴 AYNI IMZA (ayri iddia OLCMUYOR): %s" % " | ".join(adlar))
    print("ONBELLEK KANITI: %s" % ("GECTI" if kanit_gecti else "KALDI"))

    tamam = (len(o_gecen) == len(oldurucular) and len(k_gecen) == len(kontroller)
             and ayrismayan_sayisi == 0 and kanit_gecti)
    print("SONUC: %s" % ("GECTI" if tamam else "KALDI"))
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())
