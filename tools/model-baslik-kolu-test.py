#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — MODEL SAYFASI ÜYELİK YÜKLEMİ: marka üyeliği ∧ model.

  python3 tools/model-baslik-kolu-test.py                 # kabul (çapalara karşı ölçer)
  python3 tools/model-baslik-kolu-test.py --kendini-test  # ayırt edici mutasyon bataryası
  python3 tools/model-baslik-kolu-test.py --kok /yol      # BAŞKA ağaçtan oku (mutasyon için)

NE ÖLÇER — model disjunkt'ının ÜÇ KOLU AYRI AYRI:
    (1) ham `uyum[].model`   (2) `model_kanon` kuşak/kanon katlaması   (3) BAŞLIKTA TAM KELİME
ve başlık kolunun KADEMELİ kuralını (güvenli jeton / tehlike sınıfı).

🔴 ÇAPALAR ÇAKILI, TOTOLOJİ DEĞİL: beklenen sayılar geçişten ÖNCE HEAD ağacından ve canlı
uçtan tespit edildi; kabul bu SABİT sayılara karşı ölçer, kendi ürettiği kümeye DEĞİL.
Katalog büyüdükçe sayı ARTABİLİR (yüklem yalnız genişletir) — bu yüzden ölçüt ">= çapa" ve
"asla küçülmez"dir; çapanın ALTINA düşmek KIRMIZI'dır.

🔴 AYIRT EDİCİ MUTANTLAR ÜÇ FARKLI SAYFADA ÜÇ FARKLI YÖNE kayar (tek bir "daima kırmızı"
kapı hepsini geçemez):
    M1 kanon/kuşak kolunu düşür  -> Transporter sınıfında DÜŞER
    M2 başlık kolunu düşür       -> Vitara sınıfında DÜŞER
    M3 tehlike korumasını düşür  -> Renault|5 turnusolunda ARTAR
    M4 bitişikliği `markaKatla()` ile yaz -> tehlike koruması ÖLÜR (Renault|5 ARTAR) ama
       Subaru|86 turnusolu M3'ten AYIRT EDER (M3'te artar, M4'te artmaz)
    + KONTROLLER (sıralama · davranışsız yeniden adlandırma · ilgisiz alan) YEŞİL kalmalı.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(DIR)

# ---------------------------------------------------------------- ÇAKILI ÇAPALAR
# (marka, model adı, ÖNCE, SONRA-en az) — ÖNCE değeri HEAD ağacından (5 Ağu, katalog 19.461),
# SONRA değeri aynı koşumda yeni yüklemle ölçüldü. Canlı teyit: `?ara=Vitara` 68 · resmî
# üyelik 8 · sayfa 27 -> 66 (Senyor Advisor ölçümü, 5 Ağu 16:00 TRT).
CAPALAR = [
    ("Suzuki", "Vitara", 27, 66),          # BAŞLIK kolu (kazancın tamamı bu koldan)
    ("Volkswagen", "Transporter", 144, 145),   # KANON/KUŞAK kolu taşıyor (KUSAK_ESLEME)
    ("Volkswagen", "Golf", 290, 300),
    ("Ford", "Focus", 305, 305),           # DEĞİŞMEYEN çapa: kol bu sayfada iş yapmıyor
    ("Ford", "Fiesta", 231, 231),          # DEĞİŞMEYEN çapa
    ("Opel", "Astra", 126, 128),
    ("Toyota", "Corolla", 128, 133),
]

# TURNUSOL — TEHLİKE SINIFI (kısa ya da tamamen sayısal jeton).
# Renault|5: korumayla başlık kolundan +3 ürün girer ("Renault 5 …" BİTİŞİK);
# koruma düşerse çıplak `\b5\b` "Clio 5"/"Espace 5" kuşak sayılarını da yakalar ve sayı ARTAR.
TEHLIKE_TURNUSOL = [
    ("Renault", "5", 11, 14),
]
# M3 ile M4'ü AYIRT EDEN turnusol: başlıkta "Subaru BRZ 86" geçer.
#   · doğru bitişiklik  -> "subaru 86" ARANIR, BULUNMAZ (marka ile jeton yan yana DEĞİL)
#   · markaKatla ile    -> "subaru brz" -> katla() -> "Subaru" -> EŞLEŞİR (koruma ölür)
#   · koruma tümden yok -> çıplak "86" EŞLEŞİR
# Yani M3 ve M4 bu turnusolu AYNI yönde ama FARKLI kümede kaydırır; ikisi de tabandan farklı.
AYIRT_TURNUSOL = ("Subaru", "86")

# BAŞLIK KOLU KADEMELİ KURAL FİKSTÜRÜ — (jeton, TEHLİKE mi).
# Kural TÜRETİLİR (uzunluk >= 4 ∧ sayısal değil = güvenli); sabit liste YOKTUR.
SINIF_FIKSTURU = [
    ("Vitara", False), ("Corolla", False), ("Transporter", False), ("Sync", False),
    ("iPhone", False), ("F-150", False),
    ("5", True), ("A", True), ("V", True), ("205", True), ("300", True), ("C5", True),
    ("E30", True), ("T4", True), ("FL", True), ("86", True), ("M54", True), ("N47", True),
]

# BİTİŞİKLİK FİKSTÜRÜ — (başlık, marka, jeton, kabul mü).
# 🔴 M4'ün ÇALIŞTIRILABİLİR KANITI: 2. ve 3. satır `markaKatla()` ile yazılmış bir
# bitişiklikte KABUL'e döner (önek kuralı "Renault Espace"i "Renault"a katlar).
# 🔴 İKİ AYRI EKSEN — M3 (koruma yok) ile M4'ü (katlamalı bitişiklik) AYIRT EDER:
#   MARKASIZ : jetondan önce markaya benzer HİÇBİR şey yok. Koruma yoksa GEÇER (M3 kırmızı);
#              katlamalı bitişiklik ÖNEK bulamaz, GEÇMEZ (M4 bu ekseni GEÇER).
#   KATLAMALI: jetondan önce "<marka> <başka model>" var. Koruma yoksa da, katlamalı
#              bitişiklikte de GEÇER (M3 ve M4 birlikte kırmızı).
# Böylece M3'ün kırmızı kümesi M4'ünkinden GERÇEKTEN farklı olur.
BITISIKLIK_MARKASIZ = [
    ("Clio 5 Cam Krikosu Dişlisi", "Renault", "5", False),
    ("Bardaklık 300 ml Kutu Adaptörü", "Chrysler", "300", False),
    ("BRZ 86 Şanzıman Kuyruk Mili Tapası", "Subaru", "86", False),
]
BITISIKLIK_KATLAMALI = [
    ("Renault 5 E-Tech Kapı Gözleri", "Renault", "5", True),
    ("Renault Espace 5 Bardaklık", "Renault", "5", False),
    ("Renault Clio 5 Cam Krikosu", "Renault", "5", False),
    ("Subaru BRZ / Toyota 86 Şanzıman Tapası", "Subaru", "86", False),
    ("Subaru 86 Şanzıman Tapası", "Subaru", "86", True),
    ("Suzuki Vitara İç Aydınlatma", "Suzuki", "Vitara", True),
    ("Grand Vitara Tavan Rayı", "Suzuki", "Vitara", True),   # güvenli jeton: çıplak YETER
]


def _modul(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


class Olculemedi(Exception):
    pass


def olc(kok):
    """(sayfa_sayilari, evren, mm) — hüküm VERMEZ, sayı üretir."""
    araclar = os.path.join(kok, "tools")
    if araclar not in sys.path:
        sys.path.insert(0, araclar)
    for _m in ("arama", "model_kanon", "marka_model_build"):
        sys.modules.pop(_m, None)
    try:
        mm = _modul(os.path.join(araclar, "marka_model_build.py"), "marka_model_build")
        with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
    except Exception as e:                                        # noqa: BLE001
        raise Olculemedi("katalog/jeneratör okunamadı: %r" % (e,))
    if not urunler:
        raise Olculemedi("urunler.json BOŞ")
    try:
        evren = mm.MarkaEvreni(index_html)
        ek = mm.cip_evreni_markalari(urunler, index_html)
        veri = mm.gruplandir(urunler, evren, ek)
    except SystemExit as e:                                       # noqa: BLE001
        raise Olculemedi("jeneratör fail-closed durdu: %r" % (e,))
    if not veri:
        raise Olculemedi("jeneratör HİÇ kova üretmedi")
    kova = {}
    for marka, d in veri.items():
        for canon, g in d["gruplar"].items():
            kova[(marka, canon)] = (len(g["urunler"]), mm.yayimlanir_mi(g),
                                    len(g.get("baslik_ekli") or ()),
                                    bool(g.get("birincil"))
                                    and (marka, canon) not in mm.ROZET_DISI
                                    and not mm.model_olmayan_cift_mi(marka, g["display"]))
    return kova, evren, mm


def sayi(kova, evren, marka, ad):
    """Kovanın ürün sayısı (kova YOKSA 0) — sayfa yayımda olmasa da ölçülür ki
    yargı kapısı (BASLIK_DOGAN_ALLOW) iddiayı gizlemesin."""
    canon = evren.model_anahtari(marka, ad)
    if not canon:
        return 0
    return (kova.get((marka, canon)) or (0, False, 0, False))[0]


def kabul(kok):
    kaldi, gecen = [], []

    def dogrula(ad, kosul, detay=""):
        (gecen if kosul else kaldi).append(ad)
        print("  %s %s%s" % ("GECTI" if kosul else "KALDI", ad, (" — " + detay) if detay else ""))

    kova, evren, mm = olc(kok)
    yayin = sum(1 for v in kova.values() if v[1])
    kalem = sum(v[0] for v in kova.values() if v[1])
    print("  SAYFA=%d KALEM=%d KOVA=%d" % (yayin, kalem, len(kova)))

    dogrula("B0 FAIL-CLOSED: ÖLÇÜLEN SAYFA VAR", yayin >= 500,
            "sayfa=%d (dejenere ölçüm YEŞİL geçemez)" % yayin)

    # --- A) ÇAPALAR: çakılı sayılara karşı, kendi kümemize karşı DEĞİL --------------
    capa_sapan = []
    for marka, ad, _once, beklenen in CAPALAR:
        n = sayi(kova, evren, marka, ad)
        if n < beklenen:
            capa_sapan.append("%s/%s: %d < çapa %d" % (marka, ad, n, beklenen))
    dogrula("B1 ÇAKILI ÇAPALARIN HEPSİ TUTUYOR (%d çapa; yüklem yalnız GENİŞLETİR)"
            % len(CAPALAR), not capa_sapan, "sapan=%s · ölçülen=%s"
            % (capa_sapan or "-",
               ["%s/%s=%d" % (m, a, sayi(kova, evren, m, a)) for m, a, _o, _b in CAPALAR]))

    # --- B) KOL AYRIMI: her kol AYRI sayfada iş yapıyor -----------------------------
    vitara = sayi(kova, evren, "Suzuki", "Vitara")
    transporter = sayi(kova, evren, "Volkswagen", "Transporter")
    dogrula("B2 BAŞLIK KOLU İŞ YAPIYOR (Vitara sınıfı: resmî üyelik 27 -> %d)" % vitara,
            vitara >= 66, "vitara=%d (çapa 66; başlık kolu düşerse 27'ye iner)" % vitara)
    dogrula("B3 KANON/KUŞAK KOLU İŞ YAPIYOR (Transporter sınıfı: %d)" % transporter,
            transporter >= 145,
            "transporter=%d (çapa 145; kanon kolu düşerse ~101 kalem/4 sayfa kaybolur)"
            % transporter)

    # --- C) TEHLİKE SINIFI: kural TÜRETİLİYOR (sabit liste değil) -------------------
    sinif_sapan = [(j, b, mm.tehlike_jetonu_mu(j))
                   for j, b in SINIF_FIKSTURU if mm.tehlike_jetonu_mu(j) != b]
    dogrula("B4 TEHLİKE SINIFI KURALI FİKSTÜRE UYUYOR (%d jeton; uzunluk<=3 YA DA sayısal)"
            % len(SINIF_FIKSTURU), not sinif_sapan, "sapan=%s" % (sinif_sapan or "-"))

    # --- D) BİTİŞİKLİK: `markaKatla()` DEĞİL, DÜZ İFADE ----------------------------
    def _bit(fikstur):
        sapan = []
        for baslik, marka, jeton, beklenen in fikstur:
            adlar = [mm._kelimeler(x) for x in mm.marka_yazimlari(marka, evren)]
            g = mm.baslikta_tam_kelime(mm._kelimeler(baslik), adlar, jeton)
            if g != beklenen:
                sapan.append("%r + %s|%s -> %s (beklenen %s)"
                             % (baslik, marka, jeton, g, beklenen))
        return sapan

    _s1 = _bit(BITISIKLIK_MARKASIZ)
    dogrula("B5a TEHLİKE JETONU MARKASIZ BAŞLIKTA GEÇMEZ (%d fikstür; koruma düşerse "
            "KIRMIZI)" % len(BITISIKLIK_MARKASIZ), not _s1, "sapan=%s" % (_s1[:3] or "-"))
    _s2 = _bit(BITISIKLIK_KATLAMALI)
    dogrula("B5b BİTİŞİKLİK ÖNEK KATLAMASINDAN BAĞIMSIZ (%d fikstür; 'Renault Espace 5' ve "
            "'Subaru BRZ / Toyota 86' REDDEDİLİR)" % len(BITISIKLIK_KATLAMALI),
            not _s2, "sapan=%s" % (_s2[:3] or "-"))

    # --- E) TURNUSOLLAR: tehlike sınıfı gürültüsü sayfaya SIZMIYOR ------------------
    tur_sapan = []
    for marka, ad, _once, tavan in TEHLIKE_TURNUSOL:
        n = sayi(kova, evren, marka, ad)
        if n > tavan:
            tur_sapan.append("%s/%s: %d > TAVAN %d (tehlike koruması gevşedi)"
                             % (marka, ad, n, tavan))
    dogrula("B6 TEHLİKE TURNUSOLU TAVANI AŞMIYOR (%s)"
            % ", ".join("%s|%s<=%d" % (m, a, t) for m, a, _o, t in TEHLIKE_TURNUSOL),
            not tur_sapan, "sapan=%s · ölçülen=%s"
            % (tur_sapan or "-",
               ["%s/%s=%d" % (m, a, sayi(kova, evren, m, a))
                for m, a, _o, _t in TEHLIKE_TURNUSOL]))
    _ac = evren.model_anahtari(*AYIRT_TURNUSOL)
    ayirt = (kova.get((AYIRT_TURNUSOL[0], _ac)) or (0, False, 0, False))[2]
    dogrula("B7 AYIRT EDİCİ TURNUSOL: %s|%s kovasına BAŞLIK KOLUNDAN ürün GİRMİYOR "
            "(katalogda 'Subaru <marka-dışı jeton> 86 …' başlıkları var; marka+model "
            "BİTİŞİK değil)" % AYIRT_TURNUSOL, ayirt == 0,
            "başlık kolundan eklenen=%d (0 olmalı; hem koruma düşerse hem de bitişiklik "
            "markaKatla ile yazılırsa dolar)" % ayirt)

    # --- F) YARGI KAPISI: yargısız sayfa DOĞMAZ ------------------------------------
    try:
        sys.path.insert(0, os.path.join(kok, "tools"))
        import arama as _arama                                     # noqa: PLC0415
        izin = set((mk, _arama.model_normalize(jt))
                   for mk, jt in _arama.BASLIK_DOGAN_ALLOW)
    except Exception as e:                                         # noqa: BLE001
        raise Olculemedi("arama.BASLIK_DOGAN_ALLOW okunamadı: %r" % (e,))
    # 🔴 BİRİM: "hüküm BEKLEYEN" = başlık kolu olmadan eşiği geçemeyen AMA başlık koluyla
    # eşiği geçen kova (yani hükmedilseydi SAYFA OLACAK olan). Eşiğin altında kalan kovalar
    # bir karar gerektirmez ve bu sayıya KARIŞMAZ — model-uyelik-kapisi K21 ile aynı birim.
    yargisiz_dogan, bekleyen = [], 0
    for (mk, canon), (n, yayimda, bek, aday) in kova.items():
        if not bek:
            continue
        if n - bek >= mm.ESIK:
            continue                     # başlık kolu OLMADAN da eşiği geçiyordu
        if yayimda and (mk, _arama.model_normalize(canon)) not in izin:
            yargisiz_dogan.append("%s|%s" % (mk, canon))
        if not yayimda and n >= mm.ESIK and aday:
            bekleyen += 1
    # 📌 Bu sayı, model-uyelik-kapisi K21'in bastığı sayıdan BİRKAÇ kova az olabilir ve bu
    # BEKLENENDİR: burada ölçüt SAYIMDIR (`n - başlık ekli < ESIK`), K21'de üreticinin
    # `baslik_dogan` bayrağıdır (eşik VE birincillik). Aradaki fark = başlık koluyla
    # BİRİNCİLLİK kazanan kovalar. İki ölçüt BİLEREK bağımsızdır (aynısı olsaydı iddia
    # totoloji olurdu); ikisi de aynı sıfırı — "yargısız doğan=0" — savunur.
    dogrula("B8 YARGISIZ SAYFA DOĞMUYOR (başlık kolu sayesinde eşiği geçen kova ancak "
            "yargılanmışsa yayımlanır; SAYIM birimiyle %d kova hüküm BEKLİYOR ve DOĞMADI)"
            % bekleyen,
            not yargisiz_dogan, "yargısız doğan=%s" % (yargisiz_dogan[:5] or "-"))

    # --- G) KAYBEDEN YOK: hiçbir ürün kovasından DÜŞMEZ ----------------------------
    # (Kol yalnız EKLER; ölçüt yapısal: başlık kolu hiçbir kovadan ürün ÇIKARMAZ.)
    dogrula("B9 KONTROL: ölçüm dejenere değil (başlık kolu GERÇEKTEN üyelik ekliyor)",
            sum(v[2] for v in kova.values()) > 1000,
            "başlık kolundan eklenen (kova,ürün) üyeliği=%d"
            % sum(v[2] for v in kova.values()))

    print("\nSONUC: %d/%d iddia %s" % (len(kaldi) if kaldi else len(gecen),
                                       len(gecen) + len(kaldi),
                                       "KALDI ❌" if kaldi else "GECTI ✔"))
    return 1 if kaldi else 0


# ---------------------------------------------------------------- mutasyon bataryası
MUTANTLAR = [
    # --- ÖLDÜRÜCÜ: üç kol + tehlike koruması, ÜÇÜ FARKLI SAYFADA ---
    ("tools/marka_model_build.py",
     "            for taban, _etiket in evren.kusak_tabanlari(kan, t):",
     "            for taban, _etiket in ():", "KIRMIZI",
     "M1 KANON/KUŞAK KOLUNU DÜŞÜR -> Transporter sınıfında sayı DÜŞER (B3 kırmızı; "
     "Vitara ve Renault|5 DEĞİŞMEZ -> eksen ayırt edici)"),
    ("tools/marka_model_build.py",
     "                if not any(baslikta_tam_kelime(baslik_kelimeleri, ad_kelimeleri, y)\n"
     "                           for y in yazimlar):\n                    continue",
     "                if True:\n                    continue", "KIRMIZI",
     "M2 BAŞLIK KOLUNU DÜŞÜR -> Vitara 66 -> 27 (B2 kırmızı; Transporter neredeyse "
     "değişmez -> eksen ayırt edici)"),
    ("tools/marka_model_build.py",
     "    j = \"\".join(_kelimeler(jeton))\n    return (not j) or len(j) <= 3 or j.isdigit()",
     "    j = \"\".join(_kelimeler(jeton))\n    return not j", "KIRMIZI",
     "M3 TEHLİKE SINIFI KORUMASINI DÜŞÜR -> çıplak `5` 'Clio 5'/'Espace 5'i yakalar, "
     "Renault|5 TAVANI AŞAR (B6) ve Subaru|86 kovası DOĞAR (B7)"),
    ("tools/marka_model_build.py",
     "    for aw in marka_ad_kelimeleri:\n"
     "        if aw and _dizi_iceriyor(baslik_kelimeleri, aw + jw):\n"
     "            return True\n    return False",
     "    for i in range(len(baslik_kelimeleri) - len(jw) + 1):\n"
     "        if baslik_kelimeleri[i:i + len(jw)] != jw or i == 0:\n"
     "            continue\n"
     "        if _MARKA_KATLA and _MARKA_KATLA(\" \".join(baslik_kelimeleri[:i])) \\\n"
     "                in _KATLA_HEDEF:\n"
     "            return True\n    return False", "KIRMIZI",
     "M4 BİTİŞİKLİĞİ `markaKatla()` İLE YAZ -> önek kuralı 'Renault Espace'i 'Renault'a "
     "katlar, tehlike koruması SESSİZCE ölür (B5 fikstürü + B7 Subaru|86 turnusolu)"),
    # --- KONTROL (YEŞİL bekleniyor) ---
    ("tools/marka_model_build.py",
     "    (\"BMW\", \"kserisi\"): \"K Serisi\",\n",
     "    (\"BMW\", \"kserisi\"): \"K Serisi\",  # yorum (davranış AYNI)\n", "YESIL",
     "K1 KONTROL: davranış değiştirmeyen yorum -> iddia bozulmamalı (daima-kırmızı bir "
     "kabul M1-M4'ü de geçerdi)"),
    ("tools/arama.py",
     "    (\"Audi\", \"Q3\"): \"arac/motosiklet model adi\",\n"
     "    (\"Audi\", \"TT\"): \"arac/motosiklet model adi\",",
     "    (\"Audi\", \"TT\"): \"arac/motosiklet model adi\",\n"
     "    (\"Audi\", \"Q3\"): \"arac/motosiklet model adi\",", "YESIL",
     "K2 KONTROL: allow envanterini YENİDEN SIRALA -> küme ve davranış AYNI"),
    ("tools/cip-indeks.py", "SURUM = 1", "SURUM = 2", "YESIL",
     "K3 KONTROL: İLGİSİZ ALAN (çip indeksi sürümü) model üyeliğinde rol OYNAMAZ"),
]

# M4 mutantının ihtiyaç duyduğu kanca — üretim gövdesine SIZMAZ, yalnız mutant kopyada
# anlam kazanır (gerçek ağaçta ikisi de None/boş kümedir).
_M4_KANCA = ("_MARKA_KATLA = None\n_KATLA_HEDEF = frozenset()\n\n\n"
             "def baslikta_tam_kelime(")


def _kok_kur(tmp):
    os.makedirs(os.path.join(tmp, "tools"))
    for ad in os.listdir(os.path.join(GERCEK_KOK, "tools")):
        k = os.path.join(GERCEK_KOK, "tools", ad)
        if os.path.isfile(k):
            shutil.copy2(k, os.path.join(tmp, "tools", ad))
    shutil.copy2(os.path.join(GERCEK_KOK, "index.html"), os.path.join(tmp, "index.html"))
    for ad in os.listdir(GERCEK_KOK):
        if ad in ("tools", "index.html", ".git"):
            continue
        os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))


def kendini_test():
    print("MUTASYON — başlık kolu (mutant KOPYAYA uygulanır; gerçek ağaç DEĞİŞMEZ)")
    basarisiz, olcum = [], []
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = tempfile.mkdtemp(prefix="baslik-kolu-mut-")
        try:
            _kok_kur(tmp)
            yol = os.path.join(tmp, *dosya.split("/"))
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            # 🔴 ÇAPA TAM BİR KEZ EŞLEŞMELİ: kayan çapa "geçti" DEĞİL, eksen ÖLÇÜLMEMİŞ demektir.
            if metin.count(eski) != 1:
                print("  HATA M%02d: mutant ÇAPASI %d eşleşme (%s) | EKSEN ÖLÇÜLMEDİ -> %s"
                      % (i, metin.count(eski), dosya, aciklama))
                basarisiz.append("M%02d capa %d" % (i, metin.count(eski)))
                continue
            metin = metin.replace(eski, yeni, 1)
            if "_MARKA_KATLA" in yeni:
                metin = metin.replace("def baslikta_tam_kelime(", _M4_KANCA, 1)
                # Mutantın GERÇEKTEN katlama yapması için kancayı evrene bağla.
                metin = metin.replace(
                    "        ad_kelimeleri = [_kelimeler(a) for a in marka_yazimlari(marka, evren)]",
                    "        ad_kelimeleri = [_kelimeler(a) for a in marka_yazimlari(marka, evren)]\n"
                    "        globals()[\"_MARKA_KATLA\"] = evren.katla\n"
                    "        globals()[\"_KATLA_HEDEF\"] = frozenset([marka])", 1)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin)
            p = subprocess.run([sys.executable,
                                os.path.join(tmp, "tools", "model-baslik-kolu-test.py"),
                                "--kok", tmp], capture_output=True, text=True, timeout=3600)
            kirmizi = [s for s in (p.stdout or "").splitlines() if s.strip().startswith("KALDI")]
            # 🔴 ÇÖKME KIRMIZIYLA KARIŞMAZ: kabul ölçütü çıkış kodu DEĞİL, ölçülen iddia + işaret.
            if p.returncode not in (0, 1) or (p.returncode == 1 and not kirmizi):
                print("  HATA M%02d [%s] -> COKME/OLCULEMEDI (rc=%d) | %s"
                      % (i, beklenen, p.returncode, aciklama))
                print("        " + ((p.stderr or p.stdout or "").strip().splitlines()
                                    or [""])[-1][:180])
                basarisiz.append("M%02d [cokme]" % i)
                continue
            gercek = "YESIL" if p.returncode == 0 else "KIRMIZI"
            ok = gercek == beklenen
            print("  %-4s M%02d [%s] -> %s (%d iddia kırmızı) | %s"
                  % ("OK" if ok else "HATA", i, beklenen, gercek, len(kirmizi), aciklama))
            for s in kirmizi[:2]:
                print("        " + s.strip()[:170])
            olcum.append((i, beklenen, gercek, tuple(s.strip()[:12] for s in kirmizi)))
            if not ok:
                basarisiz.append("M%02d" % i)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    # AYIRT EDİCİLİK: öldürücü mutantların KIRMIZI YAKTIĞI İDDİA KÜMELERİ birbirinden
    # FARKLI olmalı — aynı küme çıkarsa "daima kırmızı" tek bir eksen hepsini geçmiş olur.
    oldurucu = [(i, k) for i, b, _g, k in olcum if b == "KIRMIZI"]
    kumeler = {}
    for i, k in oldurucu:
        kumeler.setdefault(k, []).append(i)
    ayirt_edilemeyen = [v for v in kumeler.values() if len(v) > 1]
    if ayirt_edilemeyen:
        print("  UYARI: aynı iddia kümesini kırmızı yakan mutantlar (AYIRT EDİLEMİYOR): %s"
              % ayirt_edilemeyen)
        basarisiz.append("ayirt-edilemeyen %s" % ayirt_edilemeyen)
    kontrol = sum(1 for _i, b, _g, _k in olcum if b == "YESIL")
    print("\nMUTASYON: %d öldürücü + %d kontrol koştu · ayırt edici küme=%d · "
          "beklentiyi tutmayan: %d %s"
          % (len(oldurucu), kontrol, len(kumeler), len(basarisiz), basarisiz or ""))
    return 1 if basarisiz else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK)
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    try:
        return kabul(a.kok)
    except Olculemedi as e:
        print("\nSONUC: OLCULEMEDI ❓  %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
