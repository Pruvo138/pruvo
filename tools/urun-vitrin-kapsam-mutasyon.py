#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — urun sayfasi / kart ayrimini koruyan kapi CANLI mi?

    python3 tools/urun-vitrin-kapsam-mutasyon.py      (0 = gecti, 1 = kaldi)

NE KORUNUYOR (isletme karari, 11 Agu — Okan)
════════════════════════════════════════════════════════════════════════════════
  * URUN SAYFASI : onerilen malzeme onden secili; vurgulanan tutar ONDAN turer.
  * KART/BESLEME/MARKUP : BASLANGIC tabaninda KALIR (Okan bunu acikca secti; kartin
    yukselmesi REDDEDILEN davranistir).
  * Bu iki kol ayni cekirdegi cagirir ama AYRI anahtarlara baglidir.

Bu batarya, tools/d1-fiyat-parite-kapisi.py'nin bu ayrimi GERCEKTEN olctugunu kanitlar:
kaynaklar BELLEKTE bozulur, kapi yeniden kosar ve rengi olculur. Kapi olmusse bozulmus
kaynak YESIL yanar ve batarya bunu KIRMIZI raporlar.

🔴 DISKE HICBIR MUTASYON YAZILMAZ ([[mutasyon-bytecode-onbellegi]]): Python hedefleri
`exec(compile(src, ...), types.ModuleType(...).__dict__)` ile bellekte kosar — .py dosyasi
olusmadigi icin CPython ne __pycache__ yazar ne okur. JS/HTML hedefleri kapinin kendi
STDIN'li kosucusuna METIN olarak gecer. Kosum sonunda canli dosyalarin sha256'si
bas = son karsilastirilir.

🔴 JETONLAR/CAPALAR AYRIK ([[maskeleme-kismi-kapatma]]): her mutant KENDI satirini hedefler
ve uygulanma UCU DE olculur — capa TAM 1 kez geciyor mu · eski metin gitti mi · yeni metin
geldi mi. Capa tutmazsa mutant "CAPA YOK" ile SAPMA sayilir (sessizce atlanmaz).

🔴 IKI KONTROL VARDIR ([[beyan-edilmis-survivor]]):
  M0  davranisi degistirmeyen yeniden adlandirma -> YESIL kalmali. Kalmazsa kapi "her
      degisiklikte kirmizi" demektir ve hicbir sey olcmuyordur.
  M9  FAIL-OPEN ISPATI: girdi ZEHIRLI iken kapinin hukum fonksiyonu yutucuya cevrilir ->
      YESIL bekleniyor. Bu bir "kapi saglam" iddiasi DEGIL, o hukum satirlarinin YUK
      TASIDIGININ kanitidir (M3 ayni zehirle KIRMIZI yaniyor; ikisi bir CIFTTIR).

🔴 RC YETMEZ — IZ DE ARANIR ([[hukum-yanlis-birimde]]): toplu rc, TEKIL ekseni gizler.
Bir mutant "KIRMIZI" derken kirmiziyi BASKA bir eksen uretiyor olabilir. Bu yuzden
IZLER sozlugu bazi mutantlara bir JETON sartI koyar: hukum GERCEKTEN o eksenden mi
cikti? Jeton `hatalar` alaninda aranirsa "o eksen KIRMIZI yakti" demektir; `cikti`
alaninda aranirsa "o kol GERCEKTEN kosuldu" demektir.

🔴 KARDES DEPO EKSENI (M13/M14 + M3'un izi, 11 Agu 2026): E10'un kardes-depo kolu CI'da
YAPISAL KIRMIZIYDI (agac hicbir zaman checkout edilmiyor -> rc=2 -> deploy skipped).
Onarim "agac yoksa KAPSAM DISI" oldu. Uc mutant onarimin iki ucunu birden kilitler:
  M13 agac GORUNMEZ, ihlal YOK   -> YESIL + KAPSAM DISI jetonu (CI kosumunun ta kendisi)
  M14 agac GORUNMEZ, ihlal VAR   -> KIRMIZI (kapsam-disi kolu gercek sizintiyi YUTMUYOR)
  M3  agac GORUNUR,  ihlal VAR   -> KIRMIZI **ve** hukum jetonu HATALAR'da (onarim
      fazla genisletilip agac VARKEN de hukum verilmez olursa jeton kaybolur -> SAPTI)
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

KAPI_YOL = os.path.join(TOOLS, "d1-fiyat-parite-kapisi.py")
HEDEF_DOSYALAR = {
    "secenekler": os.path.join(ROOT, "secenekler.js"),
    "index": os.path.join(ROOT, "index.html"),
    "d1sync": os.path.join(TOOLS, "d1-sync.py"),
    "build": os.path.join(TOOLS, "build.py"),
    "filament": os.path.join(TOOLS, "filament_ortak.py"),
    "kapi": KAPI_YOL,
}


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ═══════════════════════════════════════════════════════════ ZEHIRLER (girdi bozma)
# Zehir = kapinin GORMESI GEREKEN gercek dunya arizasi. Mutasyondan farki: kaynak
# kodun mantigini degil, kapinin OLCTUGU DURUMU bozar.
ZEHIRLER = {
    "vitrin": ("secenekler",
               "var ONERI_VITRIN_ACIK = false;",
               "var ONERI_VITRIN_ACIK = true;"),
    "kenar": ("d1sync",
              'q(u.get("fiyat") or "")',
              'q(_turetilmis_fiyat(u))'),
}

# ═══════════════════════════════════════════════════════════ MUTANTLAR
# (kod, aciklama, zehir, [(hedef, eski, yeni)], beklenen_rc)
MUTANTLAR = [
    ("M0", "KONTROL: davranisi degistirmeyen yeniden adlandirma", None,
     [("build",
       'def fiziksel_mi(p):\n    return bool(p) and p.get("tur") == TUR_FIZIKSEL',
       'def fiziksel_mi(kayit):\n    return bool(kayit) and kayit.get("tur") == TUR_FIZIKSEL')],
     0),

    ("M1", "bayrak ACIKKEN on-secim tabana sabitlendi (cip hep PLA)", None,
     [("build",
       "    return on_secim_tani(p)[1]",
       "    return VARSAYILAN_MALZEME")],
     1),

    ("M2", "ilan tutari CIPTEN AYRI turedi (sessiz zam/indirim)", None,
     [("build",
       "    return _birim_kurus(p, on_secim_malzeme(p))",
       "    return _birim_kurus(p, VARSAYILAN_MALZEME)")],
     1),

    ("M3", "KART DA YUKSELDI — kapsam sizintisi (Okan'in REDDETTIGI davranis)",
     "vitrin", [], 1),

    ("M4", "kart yuzeyi URUN SAYFASI turetmesini cagiriyor", None,
     [("index",
       "    if(!PRUVO_SECENEK.ONERI_VITRIN_ACIK || !PRUVO_SECENEK.vitrinBirimKurus)"
       "{ return p.fiyat; }",
       "    if(!PRUVO_SECENEK.ONERI_ONSECIM_ACIK || !PRUVO_SECENEK.ilanBirimKurus)"
       "{ return p.fiyat; }")],
     1),

    ("M5", "markup URUN SAYFASI koluna baglandi (dis listeleme sessizce zamlandi)", None,
     [("build",
       "    if ONERI_VITRIN_ACIK and pnum:",
       "    if ONERI_ONSECIM_ACIK and pnum:")],
     1),

    ("M6", "TANINMAYAN malzeme sessizce 'varsayilan'a cokuyor", None,
     [("filament",
       "    return ((TANI_TANINMAYAN if onerili else TANI_VARSAYILAN), guvenli)",
       "    return (TANI_VARSAYILAN, guvenli)")],
     1),

    ("M7", "kenar kolonu HAM alani birakti (kiyas tabani sessizce kaydi)",
     "kenar", [], 1),

    ("M8", "AZALTICI SOKULDU: taban secenegin tutari sayfadan kalkti", None,
     [("build",
       '    if p.get("parametrik") or p.get("konfigur"):\n        return None\n'
       "    return _birim_kurus(p, malzeme)",
       "    return None")],
     1),

    ("M10", "BILINCLI SECIM NOTU SOKULDU (sapan secim sessizce gecer)", None,
     [("build",
       "    if tani == filament_ortak.TANI_ONERI:",
       "    if False:")],
     1),

    ("M11", "NOT HER SECIMDE GORUNUYOR (yanlis-pozitif gurultu)", None,
     [("build",
       "oneriNot.hidden = !(_o && seciliMalzeme && seciliMalzeme !== _o);",
       "oneriNot.hidden = false;")],
     1),

    # M12 = E10'un (mesaj kanali ayrismasi) KENDI bekcisi. Kenar karti oneri alanini
    # TASIMIYOR; bugun zararsiz olmasinin TEK sebebi kart kolunun anahtari kapaliyken
    # kuralin alani HIC OKUMAMASIDIR. O erken donus kalkarsa kart kolu, alani TASIYAN
    # kartta baska, TASIMAYAN kartta baska tutar uretir -> ayni yuzeyin iki ureticisi
    # sessizce ayrisir. E10 kaniti bunu yakalamali.
    # ⚠️ OLCULDU: anahtar kisa-devresi IKI KATMANDA yazili (uretec sarmalayicisi +
    # ortak cekirdek). Yalniz BIRINI kaldirmak davranisi DEGISTIRMIYOR — digeri
    # yakaliyor (tek-katman mutant YESIL kaldi). Bu bir DELIK degil, savunma derinligi;
    # ama mutant SINIFI dogru ifade etmek icin IKISI birden kaldirilir: "kart kolu
    # kapali oldugu halde kural oneri alanini okuyor" hali ancak boyle olusur.
    ("M12", "kart kolu anahtari kapaliyken kural oneri alanini YINE DE okuyor "
            "(iki katmanli kisa-devre birden kaldirildi)", None,
     [("build",
       "    if not acik:\n        return (filament_ortak.TANI_KAPALI, VARSAYILAN_MALZEME)",
       "    if False:\n        return (filament_ortak.TANI_KAPALI, VARSAYILAN_MALZEME)"),
      ("filament",
       "    if not acik:\n        return (TANI_KAPALI, guvenli)",
       "    if False:\n        return (TANI_KAPALI, guvenli)")],
     1),

    # ── KARDES DEPO KOLU (E10) ────────────────────────────────────────────────────
    # 🔴 M13 CI KOSUMUNUN BENZESIMI. `os.path.exists(...)` kolu `True`ya sabitlenerek
    # kardes agac GORUNMEZ kilinir — CI runner'da `~` /home/runner'dir ve o agac hic
    # klonlanmaz. Bu mutant ONARIMDAN ONCE rc=2 (OLCULEMEDI) verirdi; yani `serit-a3`
    # her kosumda dusuyordu. Beklenen YESIL + kolun GERCEKTEN kosuldugunu gosteren
    # KAPSAM DISI jetonu (yalniz rc'ye bakmak "baska bir sebeple yesil"i gizlerdi).
    ("M13", "CI BENZESIMI: kardes agac GORUNMEZ, kapsam sizintisi YOK", None,
     [("kapi",
       "        if not os.path.exists(_edge.KARDES_WORKER):",
       "        if True:")],
     0),

    # 🔴 M14 KAPSAM DISI KOLU GERCEK IHLALI YUTUYOR MU? Ayni gorunmezlik + kart kolunu
    # ACAN zehir. Kapi KIRMIZI kalmali: kardes agacin yoklugu yalnizca O EKSENDE hukum
    # verdirmez, kapinin geri kalanini SUSTURMAZ. Yutsaydi onarim bir gevsetme olurdu.
    ("M14", "CI BENZESIMI + GERCEK SIZINTI: kapsam-disi kolu kapiyi SUSTURMUYOR",
     "vitrin",
     [("kapi",
       "        if not os.path.exists(_edge.KARDES_WORKER):",
       "        if True:")],
     1),

    ("M9", "FAIL-OPEN ISPATI: zehirli girdi + hukum fonksiyonu yutucu (CIFT: M3)",
     "vitrin",
     [("kapi",
       'def kontrol(kosul, mesaj):\n    print(("  ✅ " if kosul else "  ❌ ") + mesaj)\n'
       "    if not kosul:\n        HATALAR.append(mesaj)\n    return bool(kosul)",
       'def kontrol(kosul, mesaj):\n    print(("  ✅ " if kosul else "  ❌ ") + mesaj)\n'
       "    return bool(kosul)")],
     0),
]


# ═══════════════════════════════════════════════════════════ IZ SARTLARI
# kod -> (alan, jeton). alan: "hatalar" (kapinin KIRMIZI yaktigi iddialar) ·
# "olculemedi" · "cikti" (kapinin tam ciktisi). rc DOGRU ama iz YOKSA mutant SAPTI
# sayilir: rengin DOGRU EKSENDEN geldigi boyle kanitlanir ([[hukum-yanlis-birimde]]).
# Jetonlar kapinin kendi sabitlerinden gelir; elle kopya tutulmaz ([[ikiz-tanim-sessiz-ayrisma]]).
IZLER = {
    "M3": ("hatalar", "JETON_KARDES_HUKUM"),
    "M13": ("cikti", "JETON_KARDES_KAPSAM_DISI"),
    "M14": ("cikti", "JETON_KARDES_KAPSAM_DISI"),
}


# ═══════════════════════════════════════════════════════════ kosum altyapisi
def _uygula(kaynaklar, hedef, eski, yeni):
    """(ok, mesaj) — capa TAM 1 kez gecmeli; eski gitmeli, yeni gelmeli."""
    src = kaynaklar[hedef]
    n = src.count(eski)
    if n != 1:
        return (False, "capa %d kez gecti (1 olmali): %r" % (n, eski[:70]))
    yeni_src = src.replace(eski, yeni, 1)
    if eski in yeni_src and eski != yeni:
        return (False, "eski metin hala duruyor")
    if yeni not in yeni_src:
        return (False, "yeni metin yerlesmedi")
    kaynaklar[hedef] = yeni_src
    return (True, "ok")


def _modul(ad, src, yol):
    m = types.ModuleType(ad)
    m.__file__ = yol
    sys.modules[ad] = m
    exec(compile(src, yol, "exec"), m.__dict__)
    return m


def _kos(kaynaklar, fikstur):
    """Kapiyi verilen KAYNAK METINLERIYLE kosar; (rc, hata, izler) doner. Diske yazmaz.

    `izler` = {"hatalar", "olculemedi", "cikti"} — rc'nin DOGRU EKSENDEN geldigini
    olcmek icin (bkz. IZLER)."""
    onceki = {ad: sys.modules.get(ad)
              for ad in ("filament_ortak", "build", "_kapi_mut")}
    try:
        _modul("filament_ortak", kaynaklar["filament"], HEDEF_DOSYALAR["filament"])
        build_mod = _modul("build", kaynaklar["build"], HEDEF_DOSYALAR["build"])
        kapi = _modul("_kapi_mut", kaynaklar["kapi"], KAPI_YOL)
        yut = io.StringIO()
        with contextlib.redirect_stdout(yut):
            rc, _ozet = kapi.olc(kaynaklar["secenekler"], kaynaklar["index"],
                                 kaynaklar["d1sync"], kaynaklar["build"],
                                 fikstur["urunler"], fikstur["ref"], fikstur["urun"],
                                 fikstur["kosucu"], build_mod)
        izler = {"hatalar": "\n".join(getattr(kapi, "HATALAR", [])),
                 "olculemedi": "\n".join(getattr(kapi, "OLCULEMEDI", [])),
                 "cikti": yut.getvalue(),
                 "_modul": kapi}
        return (rc, None, izler)
    except Exception as e:                              # noqa: BLE001
        return (None, "%s: %s" % (type(e).__name__, e), None)
    finally:
        for ad, mod in onceki.items():
            if mod is None:
                sys.modules.pop(ad, None)
            else:
                sys.modules[ad] = mod


def main():
    bas_sha = {ad: _sha(y) for ad, y in HEDEF_DOSYALAR.items()}
    temiz = {ad: _oku(y) for ad, y in HEDEF_DOSYALAR.items()}

    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    # Referans dosyasi mutasyon hedefi DEGIL: gercek referanstan okunur.
    fo = _modul("_fo_temiz", temiz["filament"], HEDEF_DOSYALAR["filament"])
    gecici = tempfile.mkdtemp(prefix="kapsam-mut-")
    sapan = []
    try:
        fikstur = {"urunler": urunler,
                   "ref": os.path.join(gecici, "ref.json"),
                   "urun": os.path.join(gecici, "urunler.json"),
                   "kosucu": os.path.join(gecici, "kosucu.js")}
        with open(fikstur["ref"], "w", encoding="utf-8") as f:
            json.dump(fo.referans(), f, ensure_ascii=False)
        with open(fikstur["urun"], "w", encoding="utf-8") as f:
            json.dump(urunler, f, ensure_ascii=False)
        kapi_temiz = _modul("_kapi_temiz", temiz["kapi"], KAPI_YOL)
        with open(fikstur["kosucu"], "w", encoding="utf-8") as f:
            f.write(kapi_temiz.JS_KOSUCU)

        print("MUTASYON BATARYASI — urun sayfasi / kart ayrimi kapisi")
        print("hedefler: " + " · ".join(sorted(HEDEF_DOSYALAR)))

        # ---- TABAN: bozulmamis kaynakla kapi YESIL mi? (yoksa hicbir olcum anlamli degil)
        rc0, hata0, _iz0 = _kos(dict(temiz), fikstur)
        print("\nTABAN KOSUM (bozulmamis kaynak): rc=%s %s"
              % (rc0, "" if rc0 == 0 else ("HATA: %s" % hata0)))
        if rc0 != 0:
            print("TABAN KIRMIZI — mutasyon olcumu anlamsiz olurdu, DURDURULDU.")
            return 1

        print("\n%-4s %-62s %-9s %-9s %s"
              % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "SONUC"))
        for kod, aciklama, zehir, mutasyonlar, beklenen in MUTANTLAR:
            kaynaklar = dict(temiz)
            capa_hata = None
            if zehir:
                h, e, y = ZEHIRLER[zehir]
                ok, mesaj = _uygula(kaynaklar, h, e, y)
                if not ok:
                    capa_hata = "zehir(%s) %s" % (zehir, mesaj)
            for hedef, eski, yeni in mutasyonlar:
                if capa_hata:
                    break
                ok, mesaj = _uygula(kaynaklar, hedef, eski, yeni)
                if not ok:
                    capa_hata = "%s: %s" % (hedef, mesaj)
            if capa_hata:
                sapan.append("%s: CAPA YOK — %s" % (kod, capa_hata))
                print("%-4s %-62s %-9s %-9s CAPA YOK"
                      % (kod, aciklama[:62], beklenen, "-"))
                continue
            rc, hata, izler = _kos(kaynaklar, fikstur)
            if rc is None:
                sapan.append("%s: kosum dustu — %s" % (kod, hata))
                renk = "DUSTU"
            else:
                renk = {0: "YESIL", 1: "KIRMIZI", 2: "OLCULEMEDI"}.get(rc, "rc=%d" % rc)
            tamam = (rc == beklenen)
            if not tamam and rc is not None:
                sapan.append("%s: beklenen rc=%d, olculen rc=%s" % (kod, beklenen, rc))
            # IZ SARTI: rc dogru olsa bile renk DOGRU EKSENDEN gelmis mi?
            if tamam and kod in IZLER:
                alan, jeton_adi = IZLER[kod]
                jeton = getattr(izler["_modul"], jeton_adi, None)
                if jeton is None:
                    tamam = False
                    sapan.append("%s: IZ jetonu kapida YOK — %s sabiti kalkmis "
                                 "(ikiz tanim ayrismasi)" % (kod, jeton_adi))
                elif jeton not in izler[alan]:
                    tamam = False
                    sapan.append("%s: rc dogru (%d) ama IZ YOK — %r jetonu kapinin "
                                 "'%s' izinde bulunamadi; renk BASKA eksenden geliyor"
                                 % (kod, rc, jeton, alan))
            print("%-4s %-62s %-9s %-9s %s"
                  % (kod, aciklama[:62], {0: "YESIL", 1: "KIRMIZI"}.get(beklenen, beklenen),
                     renk, "OK" if tamam else "SAPTI"))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    son_sha = {ad: _sha(y) for ad, y in HEDEF_DOSYALAR.items()}
    degisen = [ad for ad in bas_sha if bas_sha[ad] != son_sha[ad]]
    if degisen:
        sapan.append("CANLI DOSYA DEGISTI (mutasyon diske sizdi): %s" % ", ".join(degisen))
    else:
        print("\nDISK TEMIZ: %d hedef dosyanin sha256'si bas = son (mutasyon diske YAZILMADI)"
              % len(bas_sha))

    kirmizi_beklenen = sum(1 for m in MUTANTLAR if m[4] == 1)
    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    print("\nOK: %d mutantin hepsi beklenen rengi verdi "
          "(%d KIRMIZI + M0 kontrol YESIL + M9 fail-open ispati YESIL + M13 CI "
          "benzesimi YESIL); %d mutantta ayrica IZ jetonu dogrulandi."
          % (len(MUTANTLAR), kirmizi_beklenen, len(IZLER)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
