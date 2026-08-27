#!/usr/bin/env python3
"""K324 KABUL BATARYASI — taşıma birimi onarımı + yazım tetikli kutu kolu.

Iki onarimi ayri ayri OLCER, sonra her onarimi kendi MUTANTIYLA olduruр
HEDEF KOL ATFINI ayrica kanitlar.

🔴 HEDEF KOL ATFI (K182): bir mutantin "kirmizi geldi" demesi kanit DEGILDIR.
Her mutant icin (a) HEDEF vakalarin DUSTUGU, (b) hedef-DISI vakalarin
AYAKTA KALDIGI ayri ayri olculur. Ikisi birden tutmazsa mutant SAYILMAZ ve
batarya KIRMIZI doner.

🔴 YAMA_TUTMADI FAIL-LOUD (K316-V1 dersi): capasi kaynakta bulunamayan mutant
kapsami SESSIZCE daraltamaz. `MUTANT=n/m` payda SABIT MUTANT SAYISIDIR;
tutmayan capa rc!=0 uretir.

Kullanim:  python3 /tam/yol/tools/k324-kabul.py
"""
import collections
import importlib.util
import os
import shutil
import sys
import tempfile
import types

BURASI = os.path.dirname(os.path.abspath(__file__))
ROT_YOL = os.path.join(BURASI, "defter-rotasyon.py")
KUTU_YOL = os.path.join(BURASI, "kutu-arsivle.py")


def _modul_yukle(ad, kaynak, dosya_yolu):
    mod = types.ModuleType(ad)
    mod.__file__ = dosya_yolu
    kod = compile(kaynak, dosya_yolu, "exec")
    exec(kod, mod.__dict__)                                  # noqa: S102
    return mod


def _kaynak(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- FIKSTURLER
# Defterin IKINCI notasyonu: sutun 0'da hal jetonuyla baslayan PARAGRAFLAR.
# (Canli DEVAM.md `## 🔚 27 AGU TUR-2` blogunun sekli birebir taklit edilir.)
PROSE_GOVDE = [
    "🟢 **GUN KILIDI ACILDI (`aaaa1111`, 4 dosya):** kutu tavani bugun BES",
    "commit'i durdurdu; sinif onarildi ve kabul sayilari yazildi.",
    "✅ **BEKLEYEN IKI COMMIT INDI:** `bbbb2222` sabah-teslim · `cccc3333` K900.",
    "K900: `SERIT_KIRMIZI=0` CANLI, iki tur birebir.",
    "✅ **UC MERGE INDI:** `dddd4444` · `eeee5555`; kosum `9001`",
    "deploy success. 🔴 Bekleyen 3 jeton KUTUDA → K901 ②/③ CANLI.",
    "🔴 **YENI KALEMLER:** ⑥ kol canlida ATESLEMEDI · ⑦ batarya 4 vaka BAYAT.",
    "",
]

# SUTUN-0 SARTININ HEDEF VAKASI (M2): kapali bir segmentin GIRINTILI devam
# satiri ACIK jeton tasiyor. Sutun-0 sarti varken devam satiri segmente
# DAHILDIR -> segment ACIK sayilir -> HICBIR SEY tasinmaz. Sart kalkarsa
# devam satiri KENDI birimi olur, `✅` satiri yalniz kalir ve KAPALI sayilip
# TASINIR — yani acik is defterden kopariliр geride birakilir.
GIRINTILI_DEVAM_GOVDE = [
    "✅ **K902 KAPANDI** — birinci satir, kapanis HALI burada.",
    "  🔧 **K903** GIRINTILI devam satiri: bu is HALA ACIK.",
    "",
]

# SEGMENT SINIRININ `- ` SARTI (M3 hedefi): prose bolgesindeki kapali segmentin
# ARDINDAN acik bir `- ` maddesi geliyor. Sinir `- `'te durmazsa segment o
# maddeyi de yutar; birlesik birim ACIK olur ve kapali segment de TASINAMAZ.
SEGMENT_SINIRI_GOVDE = [
    "✅ **K906 KAPANDI** — prose bolgesindeki KAPALI segment.",
    "- 🔧 **K905** acik kalem: AYRI birim olmali, defterde KALMALI.",
    "",
]


def _tasinan_metinler(mod, govde):
    kova = collections.Counter()
    kalan, tasinacak = mod._maddeleri_isle(list(govde), kova, [])
    return kalan, tasinacak, kova


# -------------------------------------------------------------------- VAKALAR
def v1_kapali_segment_tasinir(mod):
    """HEDEF: prose bolgesindeki KAPALI hal segmenti TASINIR."""
    _kalan, tasinacak, _k = _tasinan_metinler(mod, PROSE_GOVDE)
    kapali = [t for t in tasinacak if t.startswith("✅ **BEKLEYEN IKI COMMIT")]
    return (len(kapali) == 1,
            "kapali segment tasinan=%d (beklenen 1) · tasinan_toplam=%d"
            % (len(kapali), len(tasinacak)))


def v2_acik_madde_tasinmaz(mod):
    """KONTROL: acik `- ` maddesi ASLA tasinmaz."""
    govde = ["- 🔧 **K907** acik kalem, kesinlikle defterde kalir.", ""]
    _kalan, tasinacak, _k = _tasinan_metinler(mod, govde)
    return (len(tasinacak) == 0, "tasinan=%d (beklenen 0)" % len(tasinacak))


def v3_acik_segment_tasinmaz(mod):
    """KONTROL: ACIK hal segmenti (🔴) TASINMAZ."""
    _kalan, tasinacak, _k = _tasinan_metinler(mod, PROSE_GOVDE)
    kacak = [t for t in tasinacak if t.startswith("🔴")]
    return (len(kacak) == 0, "kacan acik segment=%d (beklenen 0)" % len(kacak))


def v4_girintili_devam_bolunmez(mod):
    """HEDEF (sutun-0 sarti): GIRINTILI devam satiri segmenti BOLMEZ.

    Devam satiri ACIK oldugu icin BIRLESIK birim ACIK'tir -> tasinan=0.
    Sart kalkarsa `✅` satiri yalniz kalip KAPALI sayilir ve TASINIR.
    """
    _kalan, tasinacak, kova = _tasinan_metinler(mod, GIRINTILI_DEVAM_GOVDE)
    birim = sum(kova.values())
    return (birim == 1 and len(tasinacak) == 0,
            "birim=%d (beklenen 1 — segment BOLUNMEDI) tasinan=%d (beklenen 0)"
            % (birim, len(tasinacak)))


def v5_segment_siniri_maddede_durur(mod):
    """HEDEF (`- ` sarti): segment ardindaki ACIK maddeyi YUTMAZ.

    Beklenen: 2 birim; kapali segment TASINIR, acik madde KALIR.
    """
    kalan, tasinacak, kova = _tasinan_metinler(mod, SEGMENT_SINIRI_GOVDE)
    birim = sum(kova.values())
    madde_kaldi = any(s.startswith("- 🔧 **K905**") for s in kalan)
    return (birim == 2 and len(tasinacak) == 1 and madde_kaldi,
            "birim=%d (beklenen 2) tasinan=%d (beklenen 1) acik_madde_kaldi=%s"
            % (birim, len(tasinacak), madde_kaldi))


def v6_ortak_satir_segmenti_tasinmaz(mod):
    """KONTROL: kapanis HALI tasiyan ama ACIK kalem de anan segment TASINMAZ."""
    _kalan, tasinacak, _k = _tasinan_metinler(mod, PROSE_GOVDE)
    kacak = [t for t in tasinacak if t.startswith("✅ **UC MERGE INDI")]
    return (len(kacak) == 0,
            "ortak satir segmenti tasindi mi=%d (beklenen 0)" % len(kacak))


def v7_tasinan_metin_birebir(mod):
    """HEDEF: tasinan segment metnine `- ` oneki UYDURULMAZ."""
    _kalan, tasinacak, _k = _tasinan_metinler(mod, PROSE_GOVDE)
    if not tasinacak:
        return False, "tasinan YOK — birebirlik olculemedi"
    bozuk = [t for t in tasinacak if t.startswith("- ")]
    return (len(bozuk) == 0,
            "onek uydurulan=%d (beklenen 0) · ilk=%r" % (len(bozuk), tasinacak[0][:40]))


def v8_kalan_govde_birebir(mod):
    """KONTROL: tasinmayan her satir kalan govdede BIREBIR durur (kayip yok)."""
    kalan, tasinacak, _k = _tasinan_metinler(mod, PROSE_GOVDE)
    tasinan_satir = []
    for t in tasinacak:
        tasinan_satir.extend(t.split("\n"))
    toplam = len(kalan) + len(tasinan_satir)
    return (toplam == len(PROSE_GOVDE),
            "kalan=%d + tasinan=%d = %d (beklenen %d)"
            % (len(kalan), len(tasinan_satir), toplam, len(PROSE_GOVDE)))


def _sisik_kutu_metni(blok_sayisi=60):
    """Tavani ASAN gercekci kutu: her blok baslik + govde + ayrac."""
    parcalar = []
    for i in range(blok_sayisi):
        parcalar.append("## BLOK-%02d — kapanis" % i)
        parcalar.append("govde satiri A %d" % i)
        parcalar.append("govde satiri B %d" % i)
        parcalar.append("govde satiri C %d" % i)
        parcalar.append("---")
    return "\n".join(parcalar) + "\n"


def v9_kutu_yaz_sonrasi_hedef_disi_atlar(mod_kutu):
    """HEDEF (B kolu): kutu OLMAYAN bir yola yazim tetigi ATESLEMEZ.

    🔴 rc=0 TEK BASINA KANIT DEGILDIR — hedef sarti kalksa da rc 0 donerdi.
    Olculen sey: kutu tavani ASMIS haldeyken bile, DUZENLENEN dosya kutu
    olmadigi icin kutu BAYT BIREBIR ayni kalir.
    """
    gecici = tempfile.mkdtemp(prefix="k324-")
    try:
        yabanci = os.path.join(gecici, "baska.md")
        with open(yabanci, "w", encoding="utf-8") as f:
            f.write("## blok\ngovde\n")
        kutu = os.path.join(gecici, "kutu.md")
        with open(kutu, "w", encoding="utf-8") as f:
            f.write(_sisik_kutu_metni())
        onceki = _oku_bayt(kutu)
        rc = mod_kutu.main(["--kutu", kutu, "--tavan", "20",
                            "--yaz-sonrasi", yabanci])
        sonraki = _oku_bayt(kutu)
        return (rc == 0 and onceki == sonraki,
                "rc=%s kutu_degismedi=%s (tavan ASILMISKEN yabanci yol)"
                % (rc, onceki == sonraki))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _oku_bayt(yol):
    with open(yol, "rb") as f:
        return f.read()


def v12_kutu_yaz_sonrasi_gercekten_atesler(mod_kutu):
    """HEDEF (B kolu): kutu tavani ASMISKEN tetik GERCEKTEN rotasyon kosturur.

    Kolun VAR olmasi yetmez, ATESLEDIGI olculur ([[yeni-kol-onceki-kolun-golgesinde-olur]]).
    """
    gecici = tempfile.mkdtemp(prefix="k324-")
    try:
        kutu = os.path.join(gecici, "kutu.md")
        with open(kutu, "w", encoding="utf-8") as f:
            f.write(_sisik_kutu_metni())
        once = len(_oku_bayt(kutu).splitlines())
        rc = mod_kutu.main(["--kutu", kutu, "--tavan", "20",
                            "--yaz-sonrasi", kutu])
        sonra = len(_oku_bayt(kutu).splitlines())
        return (rc == 0 and sonra < once,
                "rc=%s satir %d -> %d (AZALMALI)" % (rc, once, sonra))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def v10_kutu_yaz_sonrasi_tavan_altinda_atlar(mod_kutu):
    """KONTROL (B kolu): tavan ALTINDAKI kutu icin tetik is YAPMAZ."""
    gecici = tempfile.mkdtemp(prefix="k324-")
    try:
        kutu = os.path.join(gecici, "kutu.md")
        with open(kutu, "w", encoding="utf-8") as f:
            f.write("## blok\ngovde\n")
        onceki = os.path.getsize(kutu)
        rc = mod_kutu.main(["--kutu", kutu, "--tavan", "300",
                            "--yaz-sonrasi", kutu])
        return (rc == 0 and os.path.getsize(kutu) == onceki,
                "rc=%s bayt %d->%d (degismemeli)"
                % (rc, onceki, os.path.getsize(kutu)))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def v11_kutu_yaz_sonrasi_fail_open(mod_kutu):
    """HEDEF (B kolu): kol ISTISNA atsa bile rc=0 doner (yazimi bloklamaz).

    🔴 "olmayan dosya" vakasi bu kolu OLCMEZ — orada erken `return RC_OK`
    calisir, `except` dalina HIC girilmez. Gercek istisna uretmek icin kutu
    yolu bir DIZIN verilir: `os.path.exists` TRUE, `open(...)` ise
    IsADirectoryError atar -> fail-open dali ATESLER.
    """
    gecici = tempfile.mkdtemp(prefix="k324-")
    try:
        dizin_olarak_kutu = os.path.join(gecici, "kutu-dizin")
        os.makedirs(dizin_olarak_kutu)
        rc = mod_kutu.main(["--kutu", dizin_olarak_kutu,
                            "--tavan", "1",
                            "--yaz-sonrasi", dizin_olarak_kutu])
        return (rc == 0, "rc=%s (beklenen 0 — ISTISNA'ya ragmen FAIL-OPEN)" % rc)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def v13_kanca_stdin_kipi_atesler(mod_kutu):
    """HEDEF (B kolu, kanca yuzeyi): `--yaz-sonrasi -` stdin JSON'undan yolu
    OKUR ve kutu tavani asmissa GERCEKTEN rotasyon kosturur.

    Kanca kablolamasinin TEK canli yuzeyi budur; okumazsa kanca sessizce
    hicbir sey yapmaz ve arıza GORUNMEZ olur.
    """
    import io as _io
    import json as _json
    gecici = tempfile.mkdtemp(prefix="k324-")
    eski_stdin = sys.stdin
    try:
        kutu = os.path.join(gecici, "kutu.md")
        with open(kutu, "w", encoding="utf-8") as f:
            f.write(_sisik_kutu_metni())
        once = len(_oku_bayt(kutu).splitlines())
        sys.stdin = _io.StringIO(_json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": kutu},
        }))
        rc = mod_kutu.main(["--kutu", kutu, "--tavan", "20",
                            "--yaz-sonrasi", "-"])
        sonra = len(_oku_bayt(kutu).splitlines())
        return (rc == 0 and sonra < once,
                "rc=%s stdin'den yol okundu, satir %d -> %d (AZALMALI)"
                % (rc, once, sonra))
    finally:
        sys.stdin = eski_stdin
        shutil.rmtree(gecici, ignore_errors=True)


ROT_VAKALARI = [
    ("V1 kapali segment TASINIR", v1_kapali_segment_tasinir),
    ("V2 KONTROL acik madde tasinmaz", v2_acik_madde_tasinmaz),
    ("V3 KONTROL acik segment tasinmaz", v3_acik_segment_tasinmaz),
    ("V4 girintili devam BOLUNMEZ", v4_girintili_devam_bolunmez),
    ("V5 segment siniri maddede DURUR", v5_segment_siniri_maddede_durur),
    ("V6 KONTROL ortak satir tasinmaz", v6_ortak_satir_segmenti_tasinmaz),
    ("V7 tasinan metin BIREBIR", v7_tasinan_metin_birebir),
    ("V8 KONTROL kalan govde birebir", v8_kalan_govde_birebir),
]

KUTU_VAKALARI = [
    ("V9 yaz-sonrasi hedef disi ATLAR", v9_kutu_yaz_sonrasi_hedef_disi_atlar),
    ("V10 KONTROL tavan altinda ATLAR", v10_kutu_yaz_sonrasi_tavan_altinda_atlar),
    ("V11 yaz-sonrasi FAIL-OPEN", v11_kutu_yaz_sonrasi_fail_open),
    ("V12 yaz-sonrasi GERCEKTEN atesler", v12_kutu_yaz_sonrasi_gercekten_atesler),
    ("V13 kanca stdin kipi ATESLER", v13_kanca_stdin_kipi_atesler),
]

# ---------------------------------------------------------------- MUTANTLAR
# 🔴 ATIF MODELI: TAM KUME ESITLIGI (alt kume DEGIL).
# Ilk surum "hedef vakalar dussun, BASKA hicbir vaka dusmesin" diyordu ve
# PAYLASILAN kolu olduren mutantlari (M1 segment tanima, M4 kanonik onek)
# GECERSIZ sayiyordu — oysa onlarin fazladan olduruculugu ARIZA degil,
# kolun BESLEDIGI vaka kumesinin ta kendisi. Buna karsilik "hedef dusenler
# alt kume olsun" demek de fail-open olurdu: mutantin sebep OLDUGU her
# kirmizi aciklanmis sayilirdi ([[sahte-bagimlilik-sekli-negatif-blogu-kutsar]]).
# Bu yuzden her mutant DUSURECEGI VAKA KUMESINI TAM olarak beyan eder ve
# kume BIREBIR tutmazsa mutant GECERSIZDIR: ne aciklanmamis kirmizi kalir,
# ne eksik kirmizi. `hedef` alani kumenin BIRINCIL uyesidir (raporda ADIYLA
# gecer), `beklenen` ise kolun tum ayak izidir.
# (ad, hedef_dosya, capa, yeni, BEKLENEN TAM dusen kume)
MUTANTLAR = [
    ("M1 segment tanima kolu OLDURULDU", "ROT",
     "    return any(satir.startswith(j) for j in HAL_SEGMENT_JETONLARI)",
     "    return False",
     # Segment HIC taninmazsa segmente dayanan DORT vaka birden duser.
     ["V1 kapali segment TASINIR", "V7 tasinan metin BIREBIR",
      "V4 girintili devam BOLUNMEZ", "V5 segment siniri maddede DURUR"]),

    ("M2 sutun-0 sarti KALDIRILDI", "ROT",
     "    if satir[:1].isspace():\n        return False\n"
     "    return any(satir.startswith(j) for j in HAL_SEGMENT_JETONLARI)",
     "    return any(satir.lstrip().startswith(j) for j in HAL_SEGMENT_JETONLARI)",
     ["V4 girintili devam BOLUNMEZ"]),

    ("M3 segment siniri `- ` sarti KALDIRILDI", "ROT",
     '                while (j < n and not govde[j].startswith("- ")\n'
     "                        and not _hal_segmenti_baslangici(govde[j])):",
     "                while (j < n\n"
     "                        and not _hal_segmenti_baslangici(govde[j])):",
     ["V5 segment siniri maddede DURUR"]),

    ("M4 kanonik onek kolu OLDURULDU", "ROT",
     '    return metin if metin.startswith("- ") else "- " + metin',
     "    return metin",
     # Onek olmadan HICBIR segment kapali siniflanamaz -> tasima uc vakada
     # olur. V4 AYAKTA KALIR: orada zaten beklenen `tasinan=0`.
     ["V1 kapali segment TASINIR", "V7 tasinan metin BIREBIR",
      "V5 segment siniri maddede DURUR"]),

    ("M5 yaz-sonrasi HEDEF sarti KALDIRILDI", "KUTU",
     '        if hedef != kutu_yolu:\n'
     '            print("YAZ_SONRASI=ATLANDI sebep=hedef-kutu-degil hedef=%s" % hedef)\n'
     '            return RC_OK',
     '        if hedef != kutu_yolu:\n            pass',
     ["V9 yaz-sonrasi hedef disi ATLAR"]),

    ("M6 yaz-sonrasi FAIL-OPEN kolu OLDURULDU", "KUTU",
     '        print("YAZ_SONRASI=OLCULEMEDI sebep=%s" % type(hata).__name__)\n'
     '        print("  ayrinti: %s" % str(hata)[:200])\n'
     '    return RC_OK',
     '        print("YAZ_SONRASI=OLCULEMEDI sebep=%s" % type(hata).__name__)\n'
     '        return RC_KIRMIZI\n'
     '    return RC_OK',
     ["V11 yaz-sonrasi FAIL-OPEN"]),

    ("M8 kanca stdin kipi OLDURULDU", "KUTU",
     '        if yaz_sonrasi_yolu == "-":\n'
     '            yaz_sonrasi_yolu = _kanca_stdin_yolu()',
     '        if False:\n            pass',
     ["V13 kanca stdin kipi ATESLER"]),

    # KONTROL MUTANTI: davranisa DOKUNMAYAN degisiklik — HICBIR vaka dusmemeli.
    ("M7 KONTROL (davranissiz)", "ROT",
     "def _kanonik_madde_metni(metin):",
     "def _kanonik_madde_metni(metin):  # K324 kontrol mutanti",
     []),
]


def _vakalari_kos(mod_rot, mod_kutu):
    sonuc = {}
    for ad, fn in ROT_VAKALARI:
        try:
            gecti, aciklama = fn(mod_rot)
        except Exception as h:                               # noqa: BLE001
            gecti, aciklama = False, "ISTISNA %s: %s" % (type(h).__name__, h)
        sonuc[ad] = (bool(gecti), aciklama)
    for ad, fn in KUTU_VAKALARI:
        try:
            gecti, aciklama = fn(mod_kutu)
        except Exception as h:                               # noqa: BLE001
            gecti, aciklama = False, "ISTISNA %s: %s" % (type(h).__name__, h)
        sonuc[ad] = (bool(gecti), aciklama)
    return sonuc


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", default=None,
                    help="ham ciktinin YAZILACAGI dosya (git DISI bir yol olmali)")
    a = ap.parse_args(argv)
    rot_kaynak = _kaynak(ROT_YOL)
    kutu_kaynak = _kaynak(KUTU_YOL)

    L = []
    P = L.append
    P("=== K324 KABUL BATARYASI ===")
    P("ROT =%s" % ROT_YOL)
    P("KUTU=%s" % KUTU_YOL)
    P("")

    # ---------- TABAN ----------
    mod_rot = _modul_yukle("k324_rot", rot_kaynak, ROT_YOL)
    mod_kutu = _modul_yukle("k324_kutu", kutu_kaynak, KUTU_YOL)
    taban = _vakalari_kos(mod_rot, mod_kutu)
    taban_dusen = [a for a, (g, _) in taban.items() if not g]
    P("--- TABAN ---")
    for ad, (g, ac) in taban.items():
        P("  %s %-38s %s" % ("YESIL" if g else "KIRMIZI", ad, ac))
    P("VAKA=%d TABAN_DUSEN=%d" % (len(taban), len(taban_dusen)))
    P("")

    # ---------- MUTANTLAR ----------
    P("--- MUTANTLAR (hedef-kol ATFI ayrica olculur) ---")
    yama_tutmadi = 0
    mutant_gecerli = 0
    atif_tam = 0
    for ad, hedef_dosya, capa, yeni, hedef_vakalar in MUTANTLAR:
        kaynak = rot_kaynak if hedef_dosya == "ROT" else kutu_kaynak
        if kaynak.count(capa) != 1:
            yama_tutmadi += 1
            P("  YAMA_TUTMADI %-42s capa_sayisi=%d" % (ad, kaynak.count(capa)))
            continue
        mutant_kaynak = kaynak.replace(capa, yeni, 1)
        try:
            if hedef_dosya == "ROT":
                m_rot = _modul_yukle("k324_rot_m", mutant_kaynak, ROT_YOL)
                m_kutu = _modul_yukle("k324_kutu_m", kutu_kaynak, KUTU_YOL)
            else:
                m_rot = _modul_yukle("k324_rot_m", rot_kaynak, ROT_YOL)
                m_kutu = _modul_yukle("k324_kutu_m", mutant_kaynak, KUTU_YOL)
        except Exception as h:                               # noqa: BLE001
            # Derlenmeyen mutant OLCUM DEGILDIR — yama tutmadi sayilir.
            yama_tutmadi += 1
            P("  YAMA_TUTMADI %-42s derlenmedi: %s" % (ad, type(h).__name__))
            continue
        sonuc = _vakalari_kos(m_rot, m_kutu)
        dusen = [a for a, (g, _) in sonuc.items() if not g]
        beklenen_dusen = [a for a in hedef_vakalar if a in dusen]
        eksik = [a for a in hedef_vakalar if a not in dusen]
        aciklanmayan = [a for a in dusen if a not in hedef_vakalar]
        if hedef_vakalar:
            # TAM KUME ESITLIGI: eksik kirmizi de, aciklanmayan kirmizi de RED.
            gecerli = not eksik and not aciklanmayan
            P("  %-42s KIRMIZI_VAKA=%d beklenen=%d dusen_eslesme=%d "
              "EKSIK=%d ACIKLANMAYAN=%d -> %s"
              % (ad, len(dusen), len(hedef_vakalar), len(beklenen_dusen),
                 len(eksik), len(aciklanmayan),
                 "GECERLI" if gecerli else "GECERSIZ"))
            P("      HEDEF KOL ATFI (birincil): %s" % hedef_vakalar[0])
            if len(hedef_vakalar) > 1:
                P("      KOLUN AYAK IZI: %s" % ", ".join(hedef_vakalar[1:]))
            if eksik:
                P("      🔴 EKSIK (mutant olduremedi): %s" % ", ".join(eksik))
            if aciklanmayan:
                P("      🔴 ACIKLANMAYAN KIRMIZI: %s" % ", ".join(aciklanmayan))
            if gecerli:
                mutant_gecerli += 1
                atif_tam += 1
        else:
            gecerli = not dusen
            P("  %-42s KIRMIZI_VAKA=%d -> %s (KONTROL: hepsi YESIL olmali)"
              % (ad, len(dusen), "GECERLI" if gecerli else "GECERSIZ"))
            if dusen:
                P("      🔴 KONTROL MUTANTI VAKA DUSURDU: %s" % ", ".join(dusen))
            if gecerli:
                mutant_gecerli += 1
    P("")
    P("MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d YAMA_TUTMADI=%d"
      % (mutant_gecerli, len(MUTANTLAR), atif_tam,
         len([m for m in MUTANTLAR if m[4]]), yama_tutmadi))

    rc = 0
    if taban_dusen:
        rc = 1
        P("🔴 TABAN KIRMIZI: %s" % ", ".join(taban_dusen))
    if yama_tutmadi:
        rc = 1
        P("🔴 YAMA_TUTMADI=%d — kapsam SESSIZCE daralamaz (fail-loud)" % yama_tutmadi)
    if mutant_gecerli != len(MUTANTLAR):
        rc = 1
        P("🔴 MUTANT eksik: %d/%d" % (mutant_gecerli, len(MUTANTLAR)))
    P("HUKUM=%s rc=%d" % ("YESIL" if rc == 0 else "KIRMIZI", rc))
    P("=== K324 KABUL SONU ===")

    cikti = "\n".join(L) + "\n"
    if a.cikti:
        with open(a.cikti, "w", encoding="utf-8") as f:
            f.write(cikti)
    sys.stdout.write(cikti)
    return rc


if __name__ == "__main__":
    sys.exit(main())
