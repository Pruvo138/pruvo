#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOTOR TEK-KAYNAK KAPISI — tek kaynak ile KURULU KAPI KOPYALARI arasindaki sapmayi olcer.

NEDEN VAR (K214, 19 Agu 2026 — TeKiN'in capraz-ev kirmizisi, kok MIMARCA olculdu):
`tools/mimar_kimlik.py` isci motor kumelerinin TEK KAYNAGIDIR ve 15 Agu'da guncellendi
(kimi BIRINCIL, deepseek-* EMEKLI). Ama KURUCU (`tools/mimar-kapi-kur.py`) listeyi kendi
govdesine GOMUYORDU ve 13 Agu'da BES karde eve o DONMUS kopyayi kurdu:

    tek kaynak : minimax-m3, kimi, deepseek-pro, deepseek-flash, claude   (kimi VAR)
    kurulu kopya: minimax-m3,       deepseek-pro, deepseek-flash, claude   (kimi YOK)

Sonuc: bes ev EMEKLI deepseek'i KABUL ederken CANLI BIRINCIL kimi'yi REDDEDIYORDU.
Bugun maskeli (her sey luna'da kosuyor), ama 22 Agu'da kimi donunce o evlerin mimarlari
birincil kata is YOLLAYAMAZ. Klasik [[ikiz-tanim-sessiz-ayrisma]]: tek kaynak dogruydu,
TURETIM ZINCIRI kopuktu — ve kopukluk 6 gun boyunca SESSIZ kaldi.

BU KAPI O SESSIZLIGI KALDIRIR. Iki eksen olcer (K177 ayrimi):

  EKSEN 1 — TURETIM ZINCIRI (repo ICI, HER ZAMAN olculur, cikis kodunu ETKILER)
    (a) Kurucu kumeleri GOMMEZ; tek kaynaktan TURETIR.
    (b) Kurucunun URETECEGI blok, tek kaynaktan simdi yeniden uretilenle BIREBIR ayni.
    (c) KraL kaynagi (`tools/mimar-icra-kapisi.py`) kendi ikiz tanimini TUTMAZ, import eder.
  EKSEN 2 — KURULU KOPYALAR (karde evlerin DISKI, varsa olculur)
    Her evin kurulu kapisindaki turetilen adlar + KAYNAK IMZASI tek kaynakla BIREBIR.

🔴 EV YOKSA (CI checkout'unda karde evler DISKTE DEGILDIR) o ev `EV_KAPSAM_DISI` ILAN
EDILIR ve cikis kodunu ETKILEMEZ — sessizce yesil sayilmaz, RAPORDA GORUNUR. Bu, olculemeyeni
"yesil" saymak DEGIL, KAPSAM DISI ILAN etmektir (chip-duzeni-kapisi.py'nin K177 kalibi).
Ev DISKTE ise ve SAPMISSA KIRMIZI. Ev diskte ama OKUNAMIYOR/AYRISTIRILAMIYORSA da KIRMIZI
(fail-closed: "olcemedim" YESIL DEGILDIR).

KOL KODLARI (mutant hedef-kol atfi bunlarin uzerinden yapilir — K182):
    KOL=KURUCU-GOMULU    kurucuda GOMULU (turetilmemis) kume atamasi var
    KOL=SABLON-SAPMA     kurucunun uretecegi blok tek kaynakla ayni DEGIL
    KOL=KAYNAK-IKIZ      KraL kaynagi kumeyi import etmek yerine YENIDEN TANIMLIYOR
    KOL=SAPMA-DEGER      kurulu kopyadaki kume degeri tek kaynaktan FARKLI
    KOL=IMZA             kurulu kopyadaki KAYNAK IMZASI yeniden uretilenle uyusmuyor
    KOL=IKIZ-TANIM       kurulu kopyada bir ad BIRDEN COK (ya da hic) atanmis
    KOL=OLCULEMEDI       dosya var ama okunamadi/ayristirilamadi (fail-closed KIRMIZI)

KOSUM:
    python3 tools/motor-tek-kaynak-kapisi.py                # uretim olcumu
    python3 tools/motor-tek-kaynak-kapisi.py --kendini-test # mutant + kontrol bataryasi
    python3 tools/motor-tek-kaynak-kapisi.py --curutme      # kol oldurulunce mutant SUSMALI
"""
import ast
import importlib.util
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
KUR_YOLU = os.path.join(TOOLS, "mimar-kapi-kur.py")
KAYNAK_KAPI_YOLU = os.path.join(TOOLS, "mimar-icra-kapisi.py")

sys.path.insert(0, TOOLS)
import mimar_kimlik  # noqa: E402


# ============================== SAF OLCUM CEKIRDEGI ==============================
# Bu fonksiyonlar DISK BILMEZ: metin alir, bulgu doner. Kendini-test onlari sentetik
# metinle kosturur (hermetik) — gercek evlere ve gercek tek kaynaga DOKUNMAZ.

def _modul_atamalari(agac, ad):
    """<ad>'a yapilan MODUL SEVIYESI atamalar (govde icindekiler sayilmaz)."""
    return [
        dugum for dugum in agac.body
        if isinstance(dugum, ast.Assign)
        and any(isinstance(h, ast.Name) and h.id == ad for h in dugum.targets)
    ]


def _tum_atamalar(agac, ad):
    """<ad>'a yapilan HER atama (ic ice olanlar dahil) — ikiz tanim nobeti icin."""
    return [
        dugum for dugum in ast.walk(agac)
        if isinstance(dugum, ast.Assign)
        and any(isinstance(h, ast.Name) and h.id == ad for h in dugum.targets)
    ]


def kumeleri_ayikla(metin, etiket):
    """Kurulu bir kapi kopyasindan turetilen adlari + imzayi ayiklar.

    Doner: (kumeler_dict, imza_ya_None, [bulgu, ...]). Bulgu listesi BOS degilse
    o dosya KIRMIZI'dir. Ayristirilamayan dosya FAIL-CLOSED bulgu uretir."""
    try:
        agac = ast.parse(metin, filename=etiket)
    except SyntaxError as hata:
        return {}, None, ["KOL=OLCULEMEDI %s: ayristirilamadi (%s)" % (etiket, hata)]

    bulgular = []
    kumeler = {}
    for ad in mimar_kimlik.MOTOR_TURETILEN_ADLAR:
        atamalar = _tum_atamalar(agac, ad)
        if len(atamalar) != 1:
            bulgular.append(
                "KOL=IKIZ-TANIM %s: '%s' icin atama sayisi %d (beklenen TAM 1)"
                % (etiket, ad, len(atamalar)))
            continue
        try:
            kumeler[ad] = tuple(ast.literal_eval(atamalar[0].value))
        except (ValueError, TypeError, SyntaxError) as hata:
            bulgular.append(
                "KOL=OLCULEMEDI %s: '%s' SABIT bir deger degil (%s)" % (etiket, ad, hata))

    imza_atamalari = _tum_atamalar(agac, mimar_kimlik.MOTOR_IMZA_ADI)
    imza = None
    if len(imza_atamalari) != 1:
        bulgular.append(
            "KOL=IKIZ-TANIM %s: '%s' icin atama sayisi %d (beklenen TAM 1)"
            % (etiket, mimar_kimlik.MOTOR_IMZA_ADI, len(imza_atamalari)))
    else:
        try:
            imza = ast.literal_eval(imza_atamalari[0].value)
        except (ValueError, TypeError, SyntaxError) as hata:
            bulgular.append(
                "KOL=OLCULEMEDI %s: imza SABIT bir deger degil (%s)" % (etiket, hata))
    return kumeler, imza, bulgular


def sapmayi_olc(metin, etiket, beklenen_kumeler, beklenen_imza):
    """Kurulu kopyayi BEKLENEN (tek kaynak) degerlerle karsilastirir -> [bulgu, ...]."""
    kumeler, imza, bulgular = kumeleri_ayikla(metin, etiket)
    for ad in mimar_kimlik.MOTOR_TURETILEN_ADLAR:
        if ad not in kumeler:
            continue  # ayiklama zaten bulgu uretti
        if kumeler[ad] != tuple(beklenen_kumeler[ad]):
            bulgular.append(
                "KOL=SAPMA-DEGER %s: '%s' SAPTI\n"
                "            kurulu : %s\n"
                "            kaynak : %s\n"
                "            EKSIK  : %s\n"
                "            FAZLA  : %s"
                % (etiket, ad,
                   ", ".join(kumeler[ad]) or "(bos)",
                   ", ".join(beklenen_kumeler[ad]) or "(bos)",
                   ", ".join(m for m in beklenen_kumeler[ad] if m not in kumeler[ad])
                   or "-",
                   ", ".join(m for m in kumeler[ad] if m not in beklenen_kumeler[ad])
                   or "-"))
    if imza is not None and imza != beklenen_imza:
        bulgular.append(
            "KOL=IMZA %s: kaynak imzasi uyusmuyor (kurulu=%s kaynak=%s) -> kopya "
            "DONMUS ya da ELLE duzenlenmis" % (etiket, imza, beklenen_imza))
    return bulgular


def kurucu_gomulu_kume_bulgulari(metin, etiket):
    """EKSEN 1a — kurucuda GOMULU (turetilmemis) kume atamasi var mi?

    Kurucu kumeleri `from mimar_kimlik import ...` ile ALMALI; kendi govdesinde
    `ISCI_MOTORLARI = (...)` gibi bir atama tutarsa 13 Agu donmasi TEKRARLAR."""
    try:
        agac = ast.parse(metin, filename=etiket)
    except SyntaxError as hata:
        return ["KOL=OLCULEMEDI %s: ayristirilamadi (%s)" % (etiket, hata)]
    bulgular = []
    for ad in mimar_kimlik.MOTOR_TURETILEN_ADLAR:
        for atama in _tum_atamalar(agac, ad):
            bulgular.append(
                "KOL=KURUCU-GOMULU %s:%d '%s' GOMULU olarak ataniyor — tek kaynaktan "
                "TURETILMELI (mimar_kimlik.motor_blogu_kaynagi)"
                % (etiket, atama.lineno, ad))
    return bulgular


def sablon_sapmasi_bulgulari(sablon_metni, beklenen_blok, etiket):
    """EKSEN 1b — kurucunun ENJEKTE EDECEGI sablon, tek kaynaktan SIMDI uretilen blogu
    BIREBIR tasiyor mu?

    🔴 BU KOLUN SINIRI (bilerek yazildi): uretim kosumunda iki taraf da ayni
    `motor_blogu_kaynagi()` cagrisindan gelir, yani kol ORADA kismen TOTOLOJIKTIR —
    yakaladigi tek sey "biri sablondaki cagriyi SABIT METINLE degistirdi" halidir.
    Ve yakaladigi tam olarak 13 Agu'da OLAN seydir: blok metne GOMULMUSTU. Kolun
    gercekten olctugu `--curutme` C4'te kanitlanir (blok donunca kol konusmali)."""
    if beklenen_blok in sablon_metni:
        return []
    return [
        "KOL=SABLON-SAPMA %s: kurucunun uretecegi ISCI blogu, tek kaynaktan SIMDI "
        "uretilenle BIREBIR ayni DEGIL -> kurulan kopya DONUK dogar (blok sabit "
        "metne gomulmus olabilir)" % etiket
    ]


def kaynak_ikiz_bulgulari(metin, etiket):
    """EKSEN 1c — KraL kaynagi kumeyi IMPORT mu ediyor, yoksa YENIDEN mi tanimliyor?"""
    try:
        agac = ast.parse(metin, filename=etiket)
    except SyntaxError as hata:
        return ["KOL=OLCULEMEDI %s: ayristirilamadi (%s)" % (etiket, hata)]
    bulgular = []
    for atama in _modul_atamalari(agac, "ISCI_MOTORLARI"):
        bulgular.append(
            "KOL=KAYNAK-IKIZ %s:%d 'ISCI_MOTORLARI' YENIDEN TANIMLANIYOR — kaynak kapi "
            "tek kaynaktan import ETMELI" % (etiket, atama.lineno))
    ithal = any(
        isinstance(d, ast.ImportFrom) and d.module == "mimar_kimlik"
        and any(a.name == "ISCI_MOTORLARI" for a in d.names)
        for d in ast.walk(agac))
    if not ithal:
        bulgular.append(
            "KOL=KAYNAK-IKIZ %s: 'from mimar_kimlik import ISCI_MOTORLARI' YOK — kaynak "
            "kapi tek kaynagi okumuyor" % etiket)
    return bulgular


# ============================== EV KESFI (IKINCI LISTE YOK) ==============================

def _kur_modulu():
    """Kurucuyu modul olarak yukler — EV LISTESI ORADAN gelir, burada TUTULMAZ."""
    spec = importlib.util.spec_from_file_location("mimar_kapi_kur", KUR_YOLU)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _ev_kapi_yolu(kur, kok, varsayilan_goreli):
    """Evin kapi dosyasinin TAM yolu. Kurucunun kendi olcerini kullanir; olcer
    bir sey soylemezse varsayilan goreli yola duser."""
    try:
        goreli, _kablo = kur._kapi_yolu_olc(kok)
    except Exception:
        goreli = None
    return os.path.join(kok, goreli or varsayilan_goreli)


# ============================== URETIM OLCUMU ==============================

def uretim_olcumu():
    """(rc, satirlar) — iki ekseni olcer ve insan-okur rapor uretir."""
    satirlar = ["MOTOR TEK-KAYNAK KAPISI"]
    satirlar.append("=" * 72)
    beklenen = mimar_kimlik.motor_kumeleri()
    imza = mimar_kimlik.motor_imzasi()
    satirlar.append("TEK KAYNAK      : tools/mimar_kimlik.py")
    for ad in mimar_kimlik.MOTOR_TURETILEN_ADLAR:
        satirlar.append("  %-22s %s" % (ad, ", ".join(beklenen[ad]) or "(bos)"))
    satirlar.append("  %-22s %s" % ("KAYNAK IMZASI", imza))
    satirlar.append("")

    hatalar = []

    # --- EKSEN 1: TURETIM ZINCIRI (repo ICI — CI'da da TAM olculur) ---
    satirlar.append("EKSEN 1 — TURETIM ZINCIRI (repo ici, cikis kodunu ETKILER)")
    try:
        with open(KUR_YOLU, encoding="utf-8") as dosya:
            kur_metni = dosya.read()
    except Exception as hata:
        kur_metni = None
        hatalar.append("KOL=OLCULEMEDI %s: okunamadi (%s)" % (KUR_YOLU, hata))
    if kur_metni is not None:
        gomulu = kurucu_gomulu_kume_bulgulari(kur_metni, "tools/mimar-kapi-kur.py")
        hatalar.extend(gomulu)
        satirlar.append("  (a) kurucu GOMULU kume tutmuyor          : %s"
                        % ("EVET" if not gomulu else "HAYIR (%d)" % len(gomulu)))

    try:
        kur = _kur_modulu()
    except Exception as hata:
        kur = None
        hatalar.append("KOL=OLCULEMEDI kurucu import edilemedi: %r" % (hata,))
    if kur is not None:
        sablon_bulgu = sablon_sapmasi_bulgulari(
            getattr(kur, "ISCI_TANIM_SABLON", ""),
            mimar_kimlik.motor_blogu_kaynagi(), "tools/mimar-kapi-kur.py")
        hatalar.extend(sablon_bulgu)
        satirlar.append("  (b) uretilecek blok kaynakla birebir     : %s"
                        % ("EVET" if not sablon_bulgu else "HAYIR"))

    try:
        with open(KAYNAK_KAPI_YOLU, encoding="utf-8") as dosya:
            kaynak_metni = dosya.read()
    except Exception as hata:
        kaynak_metni = None
        hatalar.append("KOL=OLCULEMEDI %s: okunamadi (%s)" % (KAYNAK_KAPI_YOLU, hata))
    if kaynak_metni is not None:
        ikiz = kaynak_ikiz_bulgulari(kaynak_metni, "tools/mimar-icra-kapisi.py")
        hatalar.extend(ikiz)
        satirlar.append("  (c) KraL kaynagi tek kaynagi import ediyor: %s"
                        % ("EVET" if not ikiz else "HAYIR (%d)" % len(ikiz)))
    satirlar.append("")

    # --- EKSEN 2: KURULU KOPYALAR (karde evlerin diski) ---
    satirlar.append("EKSEN 2 — KURULU KOPYALAR (ev diskte YOKSA KAPSAM DISI)")
    kapsam_disi = 0
    olculen = 0
    if kur is None:
        satirlar.append("  EV LISTESI OKUNAMADI (kurucu import edilemedi)")
    else:
        for ad, kok, varsayilan_goreli, mod in kur.CODEX_EVLER:
            if mod == "kaynak":
                # KraL: kural commit'li dosyada YASAR ve tek kaynagi IMPORT eder;
                # burada turetilmis LITERAL BEKLENMEZ (eksen 1c onu zaten olctu).
                satirlar.append("  %-7s %-46s KAYNAK MOD (eksen 1c'de olculdu)"
                                % (ad, "tools/mimar-icra-kapisi.py"))
                continue
            if not os.path.isdir(kok):
                kapsam_disi += 1
                satirlar.append("  %-7s %-46s EV_KAPSAM_DISI (ev diskte yok)" % (ad, kok))
                continue
            yol = _ev_kapi_yolu(kur, kok, varsayilan_goreli)
            if not os.path.exists(yol):
                kapsam_disi += 1
                satirlar.append("  %-7s %-46s EV_KAPSAM_DISI (kapi dosyasi yok)"
                                % (ad, os.path.relpath(yol, kok)))
                continue
            try:
                with open(yol, encoding="utf-8") as dosya:
                    metin = dosya.read()
            except Exception as hata:
                hatalar.append("KOL=OLCULEMEDI %s: okunamadi (%s)" % (yol, hata))
                satirlar.append("  %-7s %-46s KIRMIZI (okunamadi)" % (ad, yol))
                continue
            olculen += 1
            bulgular = sapmayi_olc(metin, yol, beklenen, imza)
            hatalar.extend(bulgular)
            satirlar.append("  %-7s %-46s %s"
                            % (ad, os.path.relpath(yol, kok),
                               "TAM" if not bulgular else "KIRMIZI (%d)" % len(bulgular)))
    satirlar.append("")
    satirlar.append("OLCULEN EV: %d · KAPSAM DISI EV: %d" % (olculen, kapsam_disi))
    if kapsam_disi:
        satirlar.append(
            "NOT: KAPSAM DISI evler cikis kodunu ETKILEMEZ (CI checkout'unda karde "
            "evler diskte olmaz). Sessiz yesil DEGIL — yukarida ADIYLA sayildi.")
    satirlar.append("")

    if hatalar:
        satirlar.append("BULGULAR (%d):" % len(hatalar))
        for bulgu in hatalar:
            satirlar.append("  ❌ " + bulgu)
        satirlar.append("")
        satirlar.append("SONUC: KIRMIZI")
        satirlar.append(
            "ONARIM: tek kaynagi (tools/mimar_kimlik.py) duzelt, sonra kurulu kopyalari "
            "KURUCUYLA yeniden uret:")
        satirlar.append(
            "  python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py --isci-kapisi --uygula")
        satirlar.append("ELLE YAMA YASAK: yamanan kopya bir sonraki kurulumda geri doner.")
        return 1, satirlar
    satirlar.append("SONUC: YESIL — turetim zinciri saglam, olculen kopyalar kaynakla birebir.")
    return 0, satirlar


# ============================== KENDINI TEST (HERMETIK) ==============================
# 🔴 GERCEK EVLERE ve GERCEK TEK KAYNAGA DOKUNULMAZ: mutantlar SENTETIK metin uzerinde
# kosar. Boylece batarya CI'da da, Okan'in makinesinde de AYNI sonucu verir ve yarim
# kalan bir kosum diski KIRLI birakmaz.

def _sentetik_kurulu_kopya(kumeler, imza, ek=""):
    """Kurulu bir kapi kopyasinin ILGILI kismini taklit eden sentetik kaynak."""
    govde = ["import os", "", "ISCI_SARMALAYICI_YOLU = '/Users/okan/.claude/cron/isci.sh'"]
    for ad in mimar_kimlik.MOTOR_TURETILEN_ADLAR:
        govde.append("%s = %r" % (ad, tuple(kumeler[ad])))
    govde.append('%s = "%s"' % (mimar_kimlik.MOTOR_IMZA_ADI, imza))
    govde.append("ISCI_KURAL_SURUMU = '19agu-4'")
    if ek:
        govde.append(ek)
    return "\n".join(govde) + "\n"


def _kaynak_kumeler():
    return mimar_kimlik.motor_kumeleri()


# (ad, uretici, beklenen_kol ya da None, aciklama)
# beklenen_kol None => KONTROL: bulgu URETMEMELI (yanlis-pozitif nobeti).
def _mutantlar():
    kaynak = _kaynak_kumeler()
    imza = mimar_kimlik.motor_imzasi()
    birincil = mimar_kimlik.CANLI_ISCI_MOTORLARI[0]

    def temiz():
        return _sentetik_kurulu_kopya(kaynak, imza)

    def kimi_dusur():
        """M1 — TEK KAYNAKTAN birincil canli motor DUSURULMUS gibi kurulmus kopya.
        13 Agu vakasinin TA KENDISI: kurulu kopyada `kimi` YOK."""
        bozuk = dict(kaynak)
        bozuk["ISCI_MOTORLARI"] = tuple(
            m for m in kaynak["ISCI_MOTORLARI"] if m != birincil)
        return _sentetik_kurulu_kopya(bozuk, imza)

    def elle_satir_ekle():
        """M2 — kurulu kopyaya ELLE ikinci bir tanim satiri eklenmis (donma/yama)."""
        return _sentetik_kurulu_kopya(
            kaynak, imza, ek='ISCI_MOTORLARI = ("minimax-m3", "claude")')

    def imza_donmus():
        """M3 — degerler elle guncellenmis ama IMZA eski kalmis (yarim yama)."""
        return _sentetik_kurulu_kopya(kaynak, "0" * 16)

    def bozuk_sozdizimi():
        """M4 — dosya ayristirilamiyor: 'olcemedim' YESIL DEGILDIR (fail-closed)."""
        return temiz() + "\ndef ("

    def imza_silinmis():
        """M5 — imza satiri tamamen silinmis (nobetci koru kalmamali)."""
        metin = temiz()
        return "\n".join(
            s for s in metin.splitlines()
            if not s.startswith(mimar_kimlik.MOTOR_IMZA_ADI)) + "\n"

    return [
        ("M1 birincil canli motor kurulu kopyada YOK", kimi_dusur, "KOL=SAPMA-DEGER",
         "13 Agu vakasi: tek kaynakta '%s' VAR, kurulu kopyada YOK" % birincil),
        ("M2 kurulu kopyaya ELLE ikinci tanim satiri", elle_satir_ekle, "KOL=IKIZ-TANIM",
         "donma/elle yama: ayni ad iki kez atanmis"),
        ("M3 degerler taze ama IMZA donmus", imza_donmus, "KOL=IMZA",
         "yarim yama: imza kaynakla uyusmuyor"),
        ("M4 kopya AYRISTIRILAMIYOR", bozuk_sozdizimi, "KOL=OLCULEMEDI",
         "fail-closed: olculemeyen kopya YESIL DEGILDIR"),
        ("M5 IMZA SATIRI SILINMIS", imza_silinmis, "KOL=IKIZ-TANIM",
         "imzayi silerek nobetciden kacilamaz"),
        ("K1 KONTROL: kopya kaynakla birebir", temiz, None,
         "yanlis-POZITIF nobeti: temiz kopya bulgu URETMEMELI"),
    ]


def kendini_test():
    satirlar = ["MOTOR TEK-KAYNAK KAPISI — KENDINI TEST (hermetik, sentetik metin)"]
    satirlar.append("=" * 72)
    kaynak = _kaynak_kumeler()
    imza = mimar_kimlik.motor_imzasi()
    hata = []

    for ad, uretici, beklenen_kol, aciklama in _mutantlar():
        bulgular = sapmayi_olc(uretici(), "<sentetik>", kaynak, imza)
        kollar = sorted({b.split()[0] for b in bulgular})
        if beklenen_kol is None:
            if bulgular:
                hata.append("%s: KONTROL bulgu URETTI -> %s" % (ad, kollar))
                sonuc = "KIRMIZI"
            else:
                sonuc = "SESSIZ (beklenen)"
        elif beklenen_kol in kollar:
            sonuc = "YAKALANDI (%s)" % beklenen_kol
        else:
            hata.append("%s: hedef kol YAKALANMADI (beklenen %s, gorulen %s)"
                        % (ad, beklenen_kol, kollar or "hicbiri"))
            sonuc = "KACTI"
        satirlar.append("  %-46s %s" % (ad, sonuc))
        satirlar.append("      %s" % aciklama)

    # TEK KAYNAK MUTANTI (spec kabul 3): kaynaktan birincil canli motoru DUSUR ->
    # kurulu (TAZE) kopya artik SAPMIS gorunmeli; geri al -> YESIL. Hermetik: gercek
    # tek kaynak dosyasi DEGISTIRILMEZ, kumeler KOPYA uzerinde oynatilir.
    birincil = mimar_kimlik.CANLI_ISCI_MOTORLARI[0]
    taze_kopya = _sentetik_kurulu_kopya(kaynak, imza)
    kaynak_mutant = dict(kaynak)
    kaynak_mutant["ISCI_MOTORLARI"] = tuple(
        m for m in kaynak["ISCI_MOTORLARI"] if m != birincil)
    mutant_bulgular = sapmayi_olc(taze_kopya, "<sentetik>", kaynak_mutant, imza)
    geri_bulgular = sapmayi_olc(taze_kopya, "<sentetik>", kaynak, imza)
    satirlar.append("")
    satirlar.append("TEK KAYNAK MUTANTI (kaynaktan '%s' dusurulunce):" % birincil)
    kollar = sorted({b.split()[0] for b in mutant_bulgular})
    if "KOL=SAPMA-DEGER" not in kollar:
        hata.append("TEK KAYNAK MUTANTI: sapma kolu yakalanmadi (gorulen %s)" % kollar)
    satirlar.append("  mutant -> %s" % (", ".join(kollar) or "SESSIZ (KIRMIZI!)"))
    if geri_bulgular:
        hata.append("TEK KAYNAK MUTANTI GERI ALINDI ama bulgu SURUYOR -> %s"
                    % sorted({b.split()[0] for b in geri_bulgular}))
    satirlar.append("  geri al -> %s"
                    % ("SESSIZ (beklenen)" if not geri_bulgular else "BULGU SURUYOR"))

    # EKSEN 1 mutantlari — GERCEK repo dosyalarinin KOPYA METNI uzerinde.
    satirlar.append("")
    satirlar.append("EKSEN 1 MUTANTLARI (repo ici turetim zinciri):")
    gomulu_mutant = "ISCI_MOTORLARI = ('minimax-m3', 'claude')\n"
    bulgular = kurucu_gomulu_kume_bulgulari(gomulu_mutant, "<sentetik-kurucu>")
    if not any(b.startswith("KOL=KURUCU-GOMULU") for b in bulgular):
        hata.append("E1a: kurucuda GOMULU kume yakalanmadi")
    satirlar.append("  E1a kurucuda GOMULU kume            -> %s"
                    % ("YAKALANDI" if bulgular else "KACTI"))
    try:
        with open(KUR_YOLU, encoding="utf-8") as dosya:
            gercek_kurucu = dosya.read()
        temiz_bulgu = kurucu_gomulu_kume_bulgulari(gercek_kurucu, "tools/mimar-kapi-kur.py")
    except Exception as istisna:
        temiz_bulgu = ["okunamadi: %r" % (istisna,)]
    if temiz_bulgu:
        hata.append("E1a KONTROL: GERCEK kurucu hala GOMULU kume tutuyor -> %s" % temiz_bulgu)
    satirlar.append("  E1a KONTROL gercek kurucu           -> %s"
                    % ("SESSIZ (beklenen)" if not temiz_bulgu else "BULGU VAR"))

    # E1b — 13 AGU VAKASININ TA KENDISI: sablondaki TURETILMIS blok, DONMUS bir sabit
    # metinle degistirilmis (kimi YOK). Kol bunu yakalamali; saglam sablon sessiz kalmali.
    taze_blok = mimar_kimlik.motor_blogu_kaynagi()
    donmus_blok = taze_blok.replace(
        repr(tuple(kaynak["ISCI_MOTORLARI"])),
        repr(tuple(m for m in kaynak["ISCI_MOTORLARI"] if m != birincil)))
    bulgular = sablon_sapmasi_bulgulari(
        "ISCI_M3_CIVILI_MOTOR = 'minimax-m3'\n" + donmus_blok, taze_blok, "<sentetik-sablon>")
    if not any(b.startswith("KOL=SABLON-SAPMA") for b in bulgular):
        hata.append("E1b: sablondaki DONMUS blok yakalanmadi")
    satirlar.append("  E1b sablonda DONMUS blok             -> %s"
                    % ("YAKALANDI" if bulgular else "KACTI"))
    if sablon_sapmasi_bulgulari(
            "ISCI_M3_CIVILI_MOTOR = 'minimax-m3'\n" + taze_blok, taze_blok, "<sentetik>"):
        hata.append("E1b KONTROL: SAGLAM sablon bulgu uretti (yanlis-pozitif)")
    satirlar.append("  E1b KONTROL saglam sablon           -> SESSIZ (beklenen)")

    ikiz_mutant = "ISCI_MOTORLARI = ('minimax-m3',)\n"
    bulgular = kaynak_ikiz_bulgulari(ikiz_mutant, "<sentetik-kaynak>")
    if not any(b.startswith("KOL=KAYNAK-IKIZ") for b in bulgular):
        hata.append("E1c: kaynakta IKIZ tanim yakalanmadi")
    satirlar.append("  E1c kaynakta IKIZ tanim             -> %s"
                    % ("YAKALANDI" if bulgular else "KACTI"))
    try:
        with open(KAYNAK_KAPI_YOLU, encoding="utf-8") as dosya:
            gercek_kaynak = dosya.read()
        temiz_bulgu = kaynak_ikiz_bulgulari(gercek_kaynak, "tools/mimar-icra-kapisi.py")
    except Exception as istisna:
        temiz_bulgu = ["okunamadi: %r" % (istisna,)]
    if temiz_bulgu:
        hata.append("E1c KONTROL: GERCEK kaynak tek kaynagi import etmiyor -> %s" % temiz_bulgu)
    satirlar.append("  E1c KONTROL gercek kaynak           -> %s"
                    % ("SESSIZ (beklenen)" if not temiz_bulgu else "BULGU VAR"))

    satirlar.append("")
    if hata:
        satirlar.append("KIRMIZI (%d):" % len(hata))
        for h in hata:
            satirlar.append("  ❌ " + h)
        return 1, satirlar
    satirlar.append("SONUC: YESIL — her mutant HEDEF KOLUYLA yakalandi, kontroller sessiz.")
    return 0, satirlar


# ============================== CURUTME ==============================
# [[isci-yesil-tablo-ic-olcumu-bosaltir]]: bir mutantin KIRMIZI vermesi, o mutantin
# HEDEF KOLU olctugunun kaniti DEGILDIR — tautoloji hedefle birlikte duser. Burada
# her kolun GOVDESI oldurulur ve o kola bagli mutantin SUSMASI beklenir. Susmuyorsa
# mutant baska bir seyi olcuyordur.

def curutme():
    satirlar = ["MOTOR TEK-KAYNAK KAPISI — CURUTME (kol oldurulunce mutant SUSMALI)"]
    satirlar.append("=" * 72)
    kaynak = _kaynak_kumeler()
    imza = mimar_kimlik.motor_imzasi()
    hata = []

    def _kollari_al(metin, beklenen_kumeler=None, beklenen_imza=None):
        bulgular = sapmayi_olc(
            metin, "<curutme>",
            kaynak if beklenen_kumeler is None else beklenen_kumeler,
            imza if beklenen_imza is None else beklenen_imza)
        return sorted({b.split()[0] for b in bulgular})

    # C1 — SAPMA-DEGER kolu: beklenen kume mutantin kumesine ESITLENIRSE (kol etkisiz),
    # M1 SUSMALI. Susmuyorsa M1 sapmayi degil baska bir seyi olcuyor demektir.
    birincil = mimar_kimlik.CANLI_ISCI_MOTORLARI[0]
    bozuk = dict(kaynak)
    bozuk["ISCI_MOTORLARI"] = tuple(m for m in kaynak["ISCI_MOTORLARI"] if m != birincil)
    m1_metni = _sentetik_kurulu_kopya(bozuk, imza)
    canli = _kollari_al(m1_metni)
    olu = _kollari_al(m1_metni, beklenen_kumeler=bozuk)
    if "KOL=SAPMA-DEGER" not in canli:
        hata.append("C1: kol CANLIYKEN M1 sessiz — mutant hedef kolu olcmuyor")
    if "KOL=SAPMA-DEGER" in olu:
        hata.append("C1: kol OLDURULDUGUNDE M1 hala konusuyor -> tautoloji")
    satirlar.append("  C1 SAPMA-DEGER  canli=%s  olu=%s"
                    % (canli or "SESSIZ", olu or "SESSIZ"))

    # C2 — IMZA kolu: beklenen imza kopyanınkine esitlenirse M3 SUSMALI.
    m3_metni = _sentetik_kurulu_kopya(kaynak, "0" * 16)
    canli = _kollari_al(m3_metni)
    olu = _kollari_al(m3_metni, beklenen_imza="0" * 16)
    if "KOL=IMZA" not in canli:
        hata.append("C2: kol CANLIYKEN M3 sessiz")
    if "KOL=IMZA" in olu:
        hata.append("C2: kol OLDURULDUGUNDE M3 hala konusuyor -> tautoloji")
    satirlar.append("  C2 IMZA         canli=%s  olu=%s"
                    % (canli or "SESSIZ", olu or "SESSIZ"))

    # C3 — IKIZ-TANIM kolu: ikinci tanim satiri KALDIRILIRSA M2 SUSMALI.
    m2_metni = _sentetik_kurulu_kopya(
        kaynak, imza, ek='ISCI_MOTORLARI = ("minimax-m3", "claude")')
    canli = _kollari_al(m2_metni)
    olu = _kollari_al(_sentetik_kurulu_kopya(kaynak, imza))
    if "KOL=IKIZ-TANIM" not in canli:
        hata.append("C3: kol CANLIYKEN M2 sessiz")
    if "KOL=IKIZ-TANIM" in olu:
        hata.append("C3: ikinci tanim YOKKEN M2 hala konusuyor -> tautoloji")
    satirlar.append("  C3 IKIZ-TANIM   canli=%s  olu=%s"
                    % (canli or "SESSIZ", olu or "SESSIZ"))

    # C4 — SABLON-SAPMA kolu: bu kol uretim kosumunda kismen totolojiktir (iki taraf da
    # ayni fonksiyondan gelir). Burada TOTOLOJI OLMADIGI kanitlanir: beklenen blok
    # DONMUS olanla degistirilince kol SUSMALI, taze blokla KONUSMALI.
    birincil = mimar_kimlik.CANLI_ISCI_MOTORLARI[0]
    taze_blok = mimar_kimlik.motor_blogu_kaynagi()
    donmus_blok = taze_blok.replace(
        repr(tuple(kaynak["ISCI_MOTORLARI"])),
        repr(tuple(m for m in kaynak["ISCI_MOTORLARI"] if m != birincil)))
    donmus_sablon = "ISCI_M3_CIVILI_MOTOR = 'minimax-m3'\n" + donmus_blok
    canli = ["KOL=SABLON-SAPMA"] if sablon_sapmasi_bulgulari(
        donmus_sablon, taze_blok, "<curutme>") else []
    olu = ["KOL=SABLON-SAPMA"] if sablon_sapmasi_bulgulari(
        donmus_sablon, donmus_blok, "<curutme>") else []
    if not canli:
        hata.append("C4: kol CANLIYKEN E1b sessiz")
    if olu:
        hata.append("C4: beklenen blok DONMUSA esitlenince E1b hala konusuyor -> tautoloji")
    satirlar.append("  C4 SABLON-SAPMA canli=%s  olu=%s"
                    % (canli or "SESSIZ", olu or "SESSIZ"))

    satirlar.append("")
    if hata:
        satirlar.append("KIRMIZI (%d):" % len(hata))
        for h in hata:
            satirlar.append("  ❌ " + h)
        return 1, satirlar
    satirlar.append("SONUC: YESIL — her mutant kendi HEDEF KOLUNA bagli (tautoloji yok).")
    return 0, satirlar


def main():
    argv = sys.argv[1:]
    if "--kendini-test" in argv:
        rc, satirlar = kendini_test()
    elif "--curutme" in argv:
        rc, satirlar = curutme()
    else:
        rc, satirlar = uretim_olcumu()
    for satir in satirlar:
        print(satir)
    sys.exit(rc)


if __name__ == "__main__":
    main()
