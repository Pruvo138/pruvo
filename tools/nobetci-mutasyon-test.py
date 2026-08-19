#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nobetci-mutasyon-test.py — NOBETCILERIN KENDISINI olcen harness (S4 turu).

NEDEN VAR: bir kapinin YESIL yanmasi hicbir sey kanitlamaz; kanit, kapiyi BOZUNCA KIRMIZI
yandigini gormektir. Bu depoda olculdu: feed politika kapisinin kirmizi CIKIS YOLU (main()
return 1) ve _kendini_dogrula()'nin KENDISI hicbir testle korunmuyordu — self-check cagrisini
silen ya da bulucuyu olduren mutasyonlar CI'dan exit 0 aliyordu (sahte yesil).

🔴 MUTASYON DAIMA KOPYAYA UYGULANIR. Canli dosyayi mutasyona ugratip finally ile geri alma
deseni YASAK: tek bir kesinti calisma agacinda MUTANT birakir (bu depoda yasandi). Burada
tools/ dizininin SYMLINK aynasi kurulur, yalniz mutasyona ugrayan dosya GERCEK KOPYA olarak
yazilir, arac yolu parametreyle verilir. Canli tools/ dizinine HICBIR YAZMA yapilmaz.

NE OLCULUR:
  A) FEED POLITIKA KAPISI — kirmizi cikis yolu + self-check etkinligi.
     A0 kontrol: mutasyonsuz ayna + MESRU sentetik katalog -> YESIL (harness "hep kirmizi"
        degil; yanlis-pozitif nobetcisi de burada: durbun/kullук/cakmak metinleri gecer).
     A1 kirmizi yol: tabanda OLMAYAN gercek ihlal (elektronik sigara / vape) -> KIRMIZI.
     A2 bilinen borc: ayni ihlal tabanda yaziliysa -> YESIL (kapi asiri hevesli degil).
     A3 borc agirlasti: tabandaki urun YENI jeton kazandi -> KIRMIZI.
     A4..A17 MUTANTLAR: her biri gercek bir bozulmadir ve KIRMIZI yakmalidir. Bir mutant
        YESIL kalirsa o bozulma CI'dan sessizce gecebiliyor demektir.
        🔴 Bu kume AYNI ZAMANDA _kendini_dogrula()'nin KABLOLAMASINI korur: self-check cagrisi
        silinirse (hatalar = []) A4..A17'nin TAMAMI yesile doner ve bu harness kirmizi yanar.
        🔴 A14 (S5, M4 sinifi): feed KISMEN taranirsa kapi eskiden cikis 0 veriyordu —
           olculdu, 3000. siradaki GERCEK bir vape urunu SESSIZCE geciyordu.
        🔴 A15/A16/A17 (S5): S4'te eklenen uc nobetci FIKSTURUNUN ucu de tek satirla
           korlestirilebiliyordu (dongu oldurulur ya da liste bosaltilir) — kapi yesil kalirdi.
  B) KOK AYRIMI (kod koku / veri koku) — tools/veri_kok.py fiksturu. GERCEK bir git worktree
     kurulur; ekleme betigi ORADAN import edilip urunler.json yolunun ANA KOPYAYA cozuldugu
     olculur. ROOT tekrar __file__'dan turetilirse bu bolum KIRMIZI yanar.
  C) GORSEL BOYUT KAPISI KABLOLAMASI — ekleme betigindeki `gbk.secili_ele(...)` cagrisi
     uc ayri bicimde bozulur (donen deger atilir / olu koda alinir / govde no-op yapilir) ve
     tools/gorsel-boyut-test.py --tools <mutant-ayna> ile her birinin KIRMIZI yandigi olculur.
  D) IC RAPOR SIZINTI NOBETCISI (kisisel-veri-test.py: Kural A ad ailesi + Kural B kok
     belge izin listesi + CANLILIK capasi). GERCEK git indeksi olan GENIS aynada olculur
     (genis_ayna_kur; ayna_kur'a DOKUNULMADI — A/B/C onun bugunku sekline bagli).
     🔴 Bu bolum iki BEYAN EDILMIS KOR NOKTAYI kapatir ve kapali tutar:
        * D2: nobetci CAGRISININ main()'den silinmesi (eskiden sessiz yesil'di) —
          artik `taranan` sifirsa main() kirmizi yanar.
        * D3 TUZAK: Kural B'nin fikstur cagrisi ile YARGISINI BIRLIKTE oldurmek
          (her biri tek basina yakalaniyordu, IKISI BIRDEN Kural B'yi sessizlestiriyordu) —
          artik Kural A'nin fikstur fonksiyonundaki CAPRAZ prob yakalar.
     D6/D7: `git ls-files` rc=0 dondugu halde BOS liste vermesi (sparse/partial checkout,
     git shim) — canlilik capasi olmadan kapi "0 dosya tarandi" deyip YESIL yaniyordu.
  E) TABLO SAYACI TAM ESITLIGI (is-akisi-kapisi.py :: TABLO_TABANLARI ·
     tablo_sayaci_kontrol). 8 Agu 2026'da operator `<` -> `!=` yapildi ve tabanlar
     olculen sayilara cekildi; bu bolum o degisikligin GERCEKTEN olctugunu KOSTURARAK
     kanitlar (OZYINELEMELI ayna: dizinler GERCEK, dosyalar symlink — canli dosyaya
     mutasyon UYGULANMAZ).
       E0 kontrol : mutasyonsuz ayna -> YESIL (dususe bu bolumun TUM hukmu gecersiz)
       E1 oldurucu: SERIT_B'den bir giris DUSURULDU        -> KIRMIZI + tablo jetonu
       E2 oldurucu: SERIT_B'ye giris EKLENDI (taban ayni)  -> KIRMIZI + tablo jetonu
       E3 oldurucu: tablo_sayaci_kontrol() govdesi `return []` -> `--kendini-test` KIRMIZI
       E4 oldurucu: BOLUM G, G8 ekseninin `iddia += 1` sayaci SILINDI -> KIRMIZI
       E5 oldurucu: BOLUM G, taban guncellenmeden fazladan eksen sayaci EKLENDI -> KIRMIZI
       🔴 AYIRT EDICILER (["eski kod bu girdide ne yapiyordu" ekseni]): E1b/E2b/E4b/E5b
          ayni mutasyonu ESKI KOD ile (operator `<`, gerekirse eski taban) kosar ve jetonun
          HIC BASILMADIGINI olcer. Bu olcumler olmadan E1/E2/E4/E5'in kirmizisi degisiklige
          ATFEDILEMEZ (["beyan-edilmis-survivor"] tuzagi).
          Olculen paylar: SERIT_B 67/42 = 25 · BOLUM G iddia 8/7 = 1.

Ag'a cikmaz. urunler.json / .urun-kaynaklari.json OKUNMAZ ve YAZILMAZ (sentetik katalog).
Cikis: 0 = yesil, 1 = kirmizi.   Calistir: python3 tools/nobetci-mutasyon-test.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from git_ortami import sentetik_git
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable or "python3"
FAILS = []


def check(etiket, kosul, detay=""):
    print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", etiket, ("  -> " + detay) if detay else ""))
    if not kosul:
        FAILS.append(etiket)
    return kosul


# ---------------------------------------------------------------- ayna (mutasyon KOPYASI)
def ayna_kur(hedef_kok, mutasyonlar=None):
    """<hedef_kok>/tools/ = canli tools/ dizininin SYMLINK aynasi; <hedef_kok>/ = deponun
    kok DOSYALARININ aynasi (urun VERISI HARIC). mutasyonlar: {dosya_adi: [(eski, yeni), ...]}
    -> o dosya GERCEK KOPYA olarak yazilir. Doner: <hedef_kok>/tools yolu.

    Mutasyonun metni GERCEKTEN degistirdigi DOGRULANIR; degistirmiyorsa harness BAYATTIR
    (kod degismis, mutasyon artik bir sey bozmuyor) -> SystemExit ile gurultulu olur."""
    mutasyonlar = mutasyonlar or {}
    tools_h = os.path.join(hedef_kok, "tools")
    os.makedirs(tools_h, exist_ok=True)
    for ad in os.listdir(HERE):
        kaynak = os.path.join(HERE, ad)
        if not os.path.isfile(kaynak):
            continue
        hedef = os.path.join(tools_h, ad)
        if ad in mutasyonlar:
            with open(kaynak, encoding="utf-8") as f:
                metin = f.read()
            for eski, yeni in mutasyonlar[ad]:
                if eski not in metin:
                    raise SystemExit(
                        "HARNESS BAYAT: %s icinde mutasyon dayanagi bulunamadi: %r\n"
                        "(kod degismis olabilir — mutasyonu guncelle, YOKSA bu harness "
                        "hicbir sey olcmuyor demektir)" % (ad, eski[:90]))
                metin = metin.replace(eski, yeni)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin)
        else:
            os.symlink(kaynak, hedef)
    # kok dosyalari: build.py import aninda secenekler.js okur. Urun VERISI aynalanmaz.
    for ad in os.listdir(ROOT):
        if ad in ("urunler.json", ".urun-kaynaklari.json", ".urunler.lock", ".git"):
            continue
        kaynak = os.path.join(ROOT, ad)
        if os.path.isfile(kaynak):
            os.symlink(kaynak, os.path.join(hedef_kok, ad))
    return tools_h


# ---------------------------------------------------------------- A) feed politika kapisi
def _urun(uid, baslik, aciklama):
    return {"id": uid, "kategori": "Tamirat", "marka": [], "baslik": baslik,
            "aciklama": aciklama, "fiyat": "250 TL",
            "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}


# MESRU katalog — hicbiri bloklanmamali. Mimar KABUL listesindeki uc urun burada.
TEMIZ_KATALOG = [
    _urun("dacia-duster-cakmaklik-soketi-kapagi", "Dacia Duster çakmaklık soketi kapağı",
          "12V çakmaklık soketi için kapak. Yaklaşık dış ölçüler: 40 × 40 × 12 mm."),
    _urun("toyota-kulluk-iptal-kapagi", "Toyota küllük iptal kapağı",
          "Küllük yuvasını kapatan iptal kapağı. Yaklaşık dış ölçüler: 70 × 50 × 20 mm."),
    _urun("marin-el-durbunu-tutucu", "Marin el dürbünü tutucu",
          "Tekne konsoluna monte edilen dürbün yuvası. Yaklaşık dış ölçüler: 90 × 80 × 60 mm."),
    _urun("emniyet-kemeri-uyari-susturucu", "Suzuki Ignis emniyet kemeri uyarı susturucu",
          "Kemer ikaz sesini kısan aparat. Yaklaşık dış ölçüler: 30 × 20 × 10 mm."),
]

# GERCEK red metinleri — bloklanmali (mimar KABUL listesi).
KIRLI_KATALOG = TEMIZ_KATALOG + [
    _urun("elektronik-sigara-tutucu", "Elektronik Sigara Tutucu",
          "Bardaklık içine oturan tutucu. Yaklaşık dış ölçüler: 60 × 60 × 80 mm."),
    _urun("vape-stand", "vape stand",
          "Masaüstü stand. Yaklaşık dış ölçüler: 60 × 60 × 90 mm."),
]

# R2 (borc agirlasamaz) icin: TEK urunde IKI bloklayici jeton.
IKI_JETONLU = TEMIZ_KATALOG + [
    _urun("elektronik-sigara-tutucu", "Elektronik Sigara ve Vape Tutucu",
          "Bardaklık içine oturan tutucu. Yaklaşık dış ölçüler: 60 × 60 × 80 mm."),
]

BOS_TABAN = {"kok_baslangic": 0, "kok": []}
DOLU_TABAN = {"kok_baslangic": 2, "kok": [
    {"id": "elektronik-sigara-tutucu", "jeton": ["elektronik sigara"]},
    {"id": "vape-stand", "jeton": ["vape"]},
]}
EKSIK_JETON_TABAN = {"kok_baslangic": 1, "kok": [
    {"id": "elektronik-sigara-tutucu", "jeton": ["elektronik sigara"]},
]}

# --- MUTANTLAR: (etiket, [(eski, yeni), ...])  ya da  (etiket, [...], "beklenen_isaret") --
# 🔴 UCUNCU ELEMAN (isaret) VARSA: mutantin KIRMIZI yanmasi YETMEZ, KENDI sebebiyle yanmali.
# Sebep dogrulanmazsa bir mutant baska bir nobetciyi tetikleyerek "kaza eseri kirmizi" olur ve
# hedefledigi bozulma yine olcusuz kalir (yeni mutantlar bu yuzden isaretli).
KAPI = "feed-politika-kapisi.py"
MUTANTLAR = [
    ("A4  TR/ASCII kucultme varyantlari dusuruldu (ALL-CAPS kacis yolu acilir)",
     [("    return [tr] if tr == duz else [tr, duz]", "    return [tr]")]),
    ("A5  Turkce kucultme (TR_KUCUK) oldu",
     [('    return (s or "").translate(TR_KUCUK).lower()', '    return (s or "").lower()')]),
    ("A6  <description> tarama yolu oldu",
     [("        ja = bulucu(desc)", "        ja = []")]),
    ("A7  <title> tarama yolu oldu (SART-B: eskiden SESSIZ gecerdi)",
     [("        jb = bulucu(title)", "        jb = []")]),
    ("A8  R1 kurali (yeni borc) oldu",
     [("    for pid in sorted(set(ihlal) - set(taban)):", "    for pid in []:")]),
    ("A9  R2 kurali (borc agirlasamaz) oldu",
     [("    for pid in sorted(set(ihlal) & set(taban)):", "    for pid in []:")]),
    ("A10 taban ayristirmasi korlestirildi (her kayit TUM jetonlari tasiyor sayilir)",
     [('            kayit[k["id"]] = set(k.get("jeton") or [])',
       '            kayit[k["id"]] = set(BLOKLAYICI)')]),
    ("A11 BLOKLAYICI'ya kanitsiz jeton eklendi (1. turun hatasi: mesru parca bloklanir)",
     [('BLOKLAYICI = {\n    "elektronik sigara":',
       'BLOKLAYICI = {\n    "küllük": "kanitsiz tahmin",\n    "elektronik sigara":')]),
    ("A12 'dürbün' BLOKLAYICI'ya GERI tasindi (SART-A kilidi: mesru Marin urunu bloklanir)",
     [('BLOKLAYICI = {\n    "elektronik sigara":',
       'BLOKLAYICI = {\n    "dürbün": "geri tasindi",\n    "elektronik sigara":')]),
    ("A13 POZITIF nobetci listesi bosaltildi + jeton listesi bosaltildi",
     [("_POZITIF = [", "_POZITIF = [] or ["),
      ('    "elektronik sigara":\n        "DOGRUDAN KANIT', '    "yok-boyle-jeton":\n        "DOGRUDAN KANIT')]),
    # --- S5 turu: KISMI TARAMA + fiksturlerin KENDISI ------------------------------------
    # 🔴 A14 (M4 sinifi): feed'in <item> ayristirmasi KIRPILIR. Kapi kalan kalemleri tertemiz
    # bulur ve eskiden cikis 0 verirdi — ne self-check ne bu harness gorurdu. Olculdu: 3000.
    # siradaki GERCEK bir vape urunu SESSIZCE geciyordu. Fikstur katalogu 4 kalemdir; [:2]
    # yarisini kirpar (canlidaki [:200] tipi kirpmanin kucultulmus hali).
    ("A14 feed KIRPILDI (kalemlerin yarisi taranmiyor — M4: sessiz yesildi)",
     [("    for govde in _ITEM.findall(xml):", "    for govde in _ITEM.findall(xml)[:2]:")],
     "KISMI TARAMA"),
    # A15/A16/A17 — S4'te eklenen UC nobetci fiksturunun UCU DE tek satirla korlestirilebiliyordu.
    ("A15 _NEGATIF (yanlis-pozitif nobetcisi) dongusu oldu — fikstur dolu, nobetci kor",
     [("    for metin in _NEGATIF:", "    for metin in []:")],
     "NOBETCI DONGUSU KOSMADI: _NEGATIF"),
    ("A16 _RAPOR_POZITIF fikstur listesi BOSALTILDI (rapor katmani nobetcisi susar)",
     [("_RAPOR_POZITIF = [", "_RAPOR_POZITIF = [] if True else [")],
     "FIKSTUR KUCULDU: _RAPOR_POZITIF"),
    ("A17 _ASIMETRIK (title/description ayri-ayri) dongusu oldu — iki yol da nobetsiz kalir",
     [("    for etiket, baslik, aciklama, kirli, temiz in _ASIMETRIK:",
       "    for etiket, baslik, aciklama, kirli, temiz in []:")],
     "NOBETCI DONGUSU KOSMADI: _ASIMETRIK"),
]


def json_yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    return yol


def kapi_kos(tools_dizin, katalog_yol, taban_yol):
    r = subprocess.run([PY, os.path.join(tools_dizin, KAPI),
                        "--urunler", katalog_yol, "--taban", taban_yol],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def bolum_a(tmp):
    print("A) FEED POLITIKA KAPISI — kirmizi cikis yolu + self-check etkinligi")
    temiz = json_yaz(os.path.join(tmp, "temiz.json"), TEMIZ_KATALOG)
    kirli = json_yaz(os.path.join(tmp, "kirli.json"), KIRLI_KATALOG)
    iki = json_yaz(os.path.join(tmp, "iki-jeton.json"), IKI_JETONLU)
    bos = json_yaz(os.path.join(tmp, "taban-bos.json"), BOS_TABAN)
    dolu = json_yaz(os.path.join(tmp, "taban-dolu.json"), DOLU_TABAN)
    eksik = json_yaz(os.path.join(tmp, "taban-eksik.json"), EKSIK_JETON_TABAN)

    saglam = ayna_kur(os.path.join(tmp, "a-saglam"))

    kod, cikti = kapi_kos(saglam, temiz, bos)
    check("A0 mutasyonsuz ayna + MESRU katalog -> YESIL (yanlis-pozitif 0)", kod == 0,
          "cikis=%d %s" % (kod, cikti.strip().splitlines()[-1] if cikti.strip() else ""))

    kod, cikti = kapi_kos(saglam, kirli, bos)
    check("A1 tabanda OLMAYAN gercek ihlal -> KIRMIZI (main() return 1 yolu CANLI)",
          kod == 1 and "YENI POLITIKA IHLALI" in cikti, "cikis=%d" % kod)
    check("A1b iki gercek red de yakalandi (elektronik sigara + vape)",
          "elektronik-sigara-tutucu" in cikti and "vape-stand" in cikti)
    check("A1c MESRU urunlerin hicbiri ihlal listesinde degil",
          not any(u["id"] in cikti.split("RAPOR KATMANI")[0] for u in TEMIZ_KATALOG),
          "durbun/kullук/cakmak/susturucu metinleri bloklanmadi")

    kod, _ = kapi_kos(saglam, kirli, dolu)
    check("A2 ayni ihlal TABANDA yaziliysa -> YESIL (kapi asiri hevesli degil)", kod == 0,
          "cikis=%d" % kod)

    kod, cikti = kapi_kos(saglam, iki, eksik)
    check("A3 tabandaki urun YENI jeton kazandi -> KIRMIZI (R2)",
          kod == 1 and "YENI JETON KAZANDI" in cikti, "cikis=%d" % kod)

    for girdi in MUTANTLAR:
        etiket, degisim = girdi[0], girdi[1]
        isaret = girdi[2] if len(girdi) > 2 else None
        mdizin = ayna_kur(os.path.join(tmp, "a-mut-" + etiket.split()[0]), {KAPI: degisim})
        kod, cikti = kapi_kos(mdizin, temiz, bos)
        check(etiket + " -> KIRMIZI", kod == 1,
              "cikis=%d (YESIL kaldi: bu bozulma CI'dan SESSIZCE gecer)" % kod)
        if isaret:
            check("%s -> DOGRU SEBEPLE kirmizi (%r)" % (etiket.split()[0], isaret),
                  isaret in cikti,
                  "isaret bulundu" if isaret in cikti else
                  "isaret YOK: mutant BASKA bir nobetciyi tetiklemis (hedefledigi bozulma "
                  "yine olcusuz kaliyor)")


# ---------------------------------------------------------------- B) kok ayrimi
EKLE_BETIKLERI = ("urun-ekle.py", "printables-ekle.py", "makerworld-ekle.py")

PROB_KAYNAK = '''# -*- coding: utf-8 -*-
"""Fikstur probu: yanindaki ekleme betigini import edip cozulen kokleri basar."""
import importlib.util, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ad = sys.argv[1]
spec = importlib.util.spec_from_file_location("prob_hedef", os.path.join(HERE, ad))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("SONUC" + json.dumps({"tools": mod.TOOLS, "urunler": mod.URUNLER, "lock": mod.LOCK}))
'''


def git(*a):
    if len(a) >= 2 and a[0] == "-C":
        return sentetik_git(a[1], *a[2:], capture_output=True, text=True)
    return sentetik_git(os.getcwd(), *a, capture_output=True, text=True)


def bolum_b(tmp):
    print("B) KOK AYRIMI — kod koku worktree'de, VERI koku ANA KOPYADA (tools/veri_kok.py)")
    vk_yol = os.path.join(HERE, "veri_kok.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("veri_kok", vk_yol)
    vk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vk)

    # B1/B2/B3 — saf fonksiyon, git ENJEKTE edilir (ortamdan bagimsiz, uc dal da olculur).
    kod, veri, uyari = vk.cozumle("/x/ana/.claude/worktrees/w1/tools/urun-ekle.py",
                                  _git=lambda k: "/x/ana/.git")
    check("B1 worktree: VERI koku ana kopyaya cozuldu + uyari VAR",
          veri == "/x/ana" and kod == "/x/ana/.claude/worktrees/w1" and uyari,
          "veri=%s uyari=%s" % (veri, "VAR" if uyari else "YOK"))
    check("B1b uyari metni HER IKI kokun yolunu da gosteriyor",
          bool(uyari) and "/x/ana" in uyari and "/x/ana/.claude/worktrees/w1" in uyari)
    kod, veri, uyari = vk.cozumle("/x/ana/tools/urun-ekle.py", _git=lambda k: ".git")
    check("B2 ana kopya: tek kok, uyari YOK", veri == "/x/ana" and uyari is None,
          "veri=%s" % veri)
    kod, veri, uyari = vk.cozumle("/x/dis/tools/urun-ekle.py", _git=lambda k: None)
    check("B3 git yok / depo degil: kod koku = veri koku, uyari YOK (fikstur agaclari icin)",
          veri == "/x/dis" and uyari is None, "veri=%s" % veri)

    # B4 — GERCEK git worktree: ekleme betikleri ORADAN import edilir.
    ana = os.path.join(tmp, "b-ana")
    os.makedirs(os.path.join(ana, "tools"))
    with open(os.path.join(ana, "yer-tutucu.txt"), "w") as f:
        f.write("fikstur\n")
    r = git("init", ana)
    if r.returncode != 0:
        check("B4 git fikstur deposu kuruldu", False, r.stderr.strip()[:200])
        return
    git("-C", ana, "add", "-A")
    r = git("-C", ana, "-c", "user.email=fikstur@pruvo", "-c", "user.name=fikstur",
            "commit", "-m", "fikstur")
    if r.returncode != 0:
        check("B4 git fikstur commit'i", False, r.stderr.strip()[:200])
        return
    wt = os.path.join(tmp, "b-worktree")
    r = git("-C", ana, "worktree", "add", wt)
    if r.returncode != 0:
        check("B4 git worktree add", False, r.stderr.strip()[:200])
        return
    check("B4 gercek git worktree kuruldu", os.path.isfile(os.path.join(wt, ".git")),
          "worktree'de .git bir DOSYADIR (baglantili calisma agaci)")

    wt_tools = os.path.join(wt, "tools")
    os.makedirs(wt_tools, exist_ok=True)
    for ad in os.listdir(HERE):
        k = os.path.join(HERE, ad)
        if os.path.isfile(k) and not os.path.exists(os.path.join(wt_tools, ad)):
            os.symlink(k, os.path.join(wt_tools, ad))
    prob = os.path.join(wt_tools, "_prob.py")
    with open(prob, "w", encoding="utf-8") as f:
        f.write(PROB_KAYNAK)

    for betik in EKLE_BETIKLERI:
        r = subprocess.run([PY, prob, betik], capture_output=True, text=True)
        satir = [s for s in (r.stdout or "").splitlines() if s.startswith("SONUC")]
        if not satir:
            check("B5 %s worktree'den import edildi" % betik, False,
                  (r.stderr or "").strip()[-300:])
            continue
        d = json.loads(satir[0][len("SONUC"):])
        check("B5 %s — KOD koku worktree'de (moduller yanindan yuklenir)" % betik,
              os.path.realpath(d["tools"]) == os.path.realpath(wt_tools), d["tools"])
        # realpath: macOS'ta /var -> /private/var symlink'i iki YAZIMI da uretir; karsilastirma
        # yazim degil GERCEK HEDEF uzerinden yapilmali (yoksa dogru sonuc yanlis okunur).
        rp = os.path.realpath
        check("B6 %s — VERI (urunler.json + kilit) ANA KOPYAYA gidiyor" % betik,
              rp(d["urunler"]) == rp(os.path.join(ana, "urunler.json"))
              and rp(d["lock"]) == rp(os.path.join(ana, ".urunler.lock")), d["urunler"])
        check("B7 %s — worktree'ye YAZILMIYOR (sessiz yanlis-yer hatasi kapali)" % betik,
              not rp(d["urunler"]).startswith(rp(wt) + os.sep), d["urunler"])
        check("B8 %s — worktree'den kosunca STDERR'e GURULTULU uyari basildi" % betik,
              "WORKTREE'DEN KOSULUYOR" in (r.stderr or ""),
              "uyari %s" % ("basildi" if "WORKTREE'DEN KOSULUYOR" in (r.stderr or "") else "YOK"))


# ---------------------------------------------------------------- C) gorsel kapisi kablolamasi
CAGRI = "        secili, _bres = gbk.secili_ele(d, secili)"
KABLO_MUTANTLARI = [
    ("C1 donen deger ATILDI (cagri duruyor, filtre uygulanmiyor)",
     "        _atilan, _bres = gbk.secili_ele(d, secili)"),
    ("C2 cagri OLU KODA alindi",
     "        if False:\n            secili, _bres = gbk.secili_ele(d, secili)"),
    ("C3 cagri govdesi NO-OP yapildi (kapi cagriliyor ama hicbir sey elemiyor)",
     "        gbk.secili_ele(d, secili)"),
]


def bolum_c(tmp):
    print("C) GORSEL BOYUT KAPISI KABLOLAMASI — mutant AYNADA olculur (canli dizine dokunulmaz)")
    saglam = ayna_kur(os.path.join(tmp, "c-saglam"))
    r = subprocess.run([PY, os.path.join(saglam, "gorsel-boyut-test.py"), "--tools", saglam],
                       capture_output=True, text=True)
    check("C0 mutasyonsuz ayna -> YESIL (harness 'hep kirmizi' degil)", r.returncode == 0,
          "cikis=%d %s" % (r.returncode, (r.stdout or "").strip().splitlines()[-1:]))

    for etiket, yeni in KABLO_MUTANTLARI:
        mdizin = ayna_kur(os.path.join(tmp, "c-mut-" + etiket.split()[0]),
                          {"urun-ekle.py": [(CAGRI, yeni)]})
        r = subprocess.run([PY, os.path.join(mdizin, "gorsel-boyut-test.py"),
                            "--tools", mdizin], capture_output=True, text=True)
        check(etiket + " -> KIRMIZI", r.returncode == 1,
              "cikis=%d (YESIL kalirsa kablolama kopmasi SESSIZ)" % r.returncode)


# ---------------------------------------------------------------- D) ic rapor sizinti nobetcisi
# NEDEN AYRI (GENIS) AYNA: mevcut ayna_kur yalniz tools/ + kok DOSYALARINI aynalar ve
# hedef kok BIR GIT DEPOSU DEGILDIR. kisisel-veri-test.py ise (a) `git ls-files`
# calistirir, (b) hakkimizda/ iletisim/ sss/ gizlilik/ DIZINLERINDEN statik sayfa okur.
# 🔴 ayna_kur'a DOKUNULMADI: A/B/C bolumleri onun bugunku sekline bagli, degistirmek
# onlari SESSIZCE bozardi. Bu yuzden ayri bir genis-ayna yardimcisi eklendi.
# Gate SALT-OKUNURDUR (yalnizca git ls-files + dosya acma) -> urun verisini de
# aynalamak guvenlidir; ayna_kur'un veri dislama gerekcesi (YAZAN ekleme betikleri)
# burada gecerli degil.
#
# NE OLCULUR (hepsi GERCEK dosya + GERCEK git index uzerinde):
#   D0 mutasyonsuz TEMIZ ayna -> YESIL (harness "hep kirmizi" degil; yanlis-pozitif nobeti)
#   D1 SIZINTILI ayna (kokte IZLENEN TESLIM-NOTU.md) -> KIRMIZI (kapi gercekten yakaliyor)
#   D2..D7 MUTANTLAR: her biri gercek bir bozulmadir ve KIRMIZI yakmalidir.
#   🔴 D2/D3 daha once BEYAN EDILEN KOR NOKTALARDI (cagrinin ve fikstur katmaninin
#      silinmesi sessiz yesil veriyordu) — bu bolum onlari KAPATIR.
#   🔴 D3 TUZAK: fikstur extend'i ile Kural B yargisini AYRI AYRI oldurmek yakalanir,
#      ama IKISINI BIRLIKTE oldurmek Kural B'yi tamamen SESSIZLESTIRIR; bu yuzden
#      o mutant SIZINTILI aynada olculur (fikstur degil, GERCEK sizinti yakalar).
KVT = "kisisel-veri-test.py"
D_SIZINTI_ADI = "TESLIM-NOTU.md"   # ad-ailesi DISI: yalniz Kural B yakalar

D_NOBET_CAGRI = "    rapor_hatalari, taranan = ic_rapor_nobeti()"
D_EXTEND = "        hatalar.extend(kok_belge_fikstur_hatalari())"
D_B_YARGI = '    if "/" in yol:\n        return False\n'
D_CANLILIK = "    if KAPI_YOLU not in yollar:"
# ⚠️ `try:` SATIRI DA DEGISIME DAHIL: sadece govdeyi degistirmek sarkan bir `try:`
# birakir -> mutant SyntaxError verir, python cikis 1 doner ve kontrol "KIRMIZI"
# sanip YANLIS YERDEN gecerdi (olculdu: D6/D7 once tam olarak bu sekilde sahte
# PASS veriyordu). Bu yuzden asagida ayrica "Traceback stderr'de OLMAYACAK" sarti var.
D_GIT_GOVDE = ('    try:\n'
               '        r = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"],\n'
               '                           capture_output=True, text=True)\n'
               '    except OSError as e:\n'
               '        return 127, "", "git calistirilamadi: %s" % e\n'
               '    return r.returncode, r.stdout, r.stderr\n')

D_MUTANTLARI = [
    ("D2 main()'deki nobetci CAGRISI silindi (kapi hic kosmuyor)",
     [(D_NOBET_CAGRI, "    rapor_hatalari, taranan = [], 0")], True),
    ("D3 TUZAK: fikstur extend'i + Kural B yargisi BIRLIKTE olduruldu",
     [(D_EXTEND, "        pass"),
      (D_B_YARGI, '    if True:\n        return False\n')], True),
    ("D4 Kural B yargisi TEK BASINA olduruldu (fikstur katmani yakalamali)",
     [(D_B_YARGI, '    if True:\n        return False\n')], False),
    ("D5 fikstur extend'i TEK BASINA silindi (sizinti hala yakalanmali)",
     [(D_EXTEND, "        pass")], True),
    ("D6 git rc=0 + BOS liste (sparse/partial checkout taklidi)",
     [(D_GIT_GOVDE, '    return 0, "", ""\n')], False),
    ("D7 BIRLESIK: bos git + CANLILIK nobeti de silinmis (gercek sessiz-yesil hali)",
     [(D_GIT_GOVDE, '    return 0, "", ""\n'), (D_CANLILIK, "    if False:")], False),
]


def genis_ayna_kur(hedef_kok, mutasyonlar=None, sizintili=False):
    """GERCEK git indeksi olan genis ayna. Doner: (tools_dizini, hata_metni|None).

    mutasyonlar: {dosya_adi: [(eski, yeni), ...]} -> o dosya GERCEK KOPYA olarak yazilir
    (canli tools/ dizinine HICBIR YAZMA yapilmaz). Mutasyon metni GERCEKTEN
    degistirmiyorsa harness BAYATTIR -> SystemExit ile gurultulu olur.
    sizintili=True: koke IZLENEN bir ic rapor dosyasi konur (kapinin yakalamasi gereken).

    IZLENEN liste `git add -A` ile DEGIL, gercek deponun ls-files ciktisindan turetilen
    ACIK yol listesiyle kurulur: -A kullanilsaydi gitignore'daki ic dosyalar
    (CLAUDE.md/AGENTS.md/DEVAM.md) izlenen olur ve D0 kontrolu HAKSIZ yere kirmizi yanardi."""
    mutasyonlar = mutasyonlar or {}
    tools_h = os.path.join(hedef_kok, "tools")
    os.makedirs(tools_h, exist_ok=True)
    for ad in os.listdir(HERE):
        kaynak = os.path.join(HERE, ad)
        if not os.path.isfile(kaynak):
            continue
        hedef = os.path.join(tools_h, ad)
        if ad in mutasyonlar:
            with open(kaynak, encoding="utf-8") as f:
                metin = f.read()
            for eski, yeni in mutasyonlar[ad]:
                if eski not in metin:
                    raise SystemExit(
                        "HARNESS BAYAT (bolum D): %s icinde mutasyon dayanagi "
                        "bulunamadi: %r\n(kod degismis olabilir — mutasyonu guncelle, "
                        "YOKSA bu bolum hicbir sey olcmuyor demektir)" % (ad, eski[:90]))
                metin = metin.replace(eski, yeni)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin)
        else:
            os.symlink(kaynak, hedef)
    # kok: TUM girdiler (DIZINLER dahil — statik sayfalar oradan okunur), .git ve
    # zaten kurulmus tools/ haric.
    for ad in os.listdir(ROOT):
        if ad in (".git", "tools"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(hedef_kok, ad))

    r = git("init", hedef_kok)
    if r.returncode != 0:
        return tools_h, "git init basarisiz: %s" % (r.stderr or "").strip()[:160]
    r = git("-C", ROOT, "ls-files")
    if r.returncode != 0:
        return tools_h, "kaynak depo ls-files basarisiz: %s" % (r.stderr or "").strip()[:160]
    izlenen = [y for y in (r.stdout or "").splitlines() if y]
    # Yalniz KOK dosyalari + tools/ DOGRUDAN cocuklari eklenebilir: alt dizinler
    # ayna kokunde SYMLINK'tir ve git symlink'in OTESINDEKI yolu indeksleyemez.
    eklenecek = [y for y in izlenen
                 if ("/" not in y or (y.startswith("tools/") and "/" not in y[6:]))
                 and os.path.lexists(os.path.join(hedef_kok, y))]
    if not eklenecek:
        return tools_h, "aynaya eklenecek izlenen dosya bulunamadi"
    r = git("-C", hedef_kok, "add", "-f", "--", *eklenecek)
    if r.returncode != 0:
        return tools_h, "ayna git add basarisiz: %s" % (r.stderr or "").strip()[:160]
    if sizintili:
        with open(os.path.join(hedef_kok, D_SIZINTI_ADI), "w", encoding="utf-8") as f:
            f.write("# fikstur: kokte IZLENEN ic rapor — kapi bunu YAKALAMALI\n")
        r = git("-C", hedef_kok, "add", "-f", "--", D_SIZINTI_ADI)
        if r.returncode != 0:
            return tools_h, "sizinti fiksturu eklenemedi: %s" % (r.stderr or "").strip()[:160]
    return tools_h, None


def _kvt_kos(tools_dizin):
    return subprocess.run([PY, os.path.join(tools_dizin, KVT)],
                          capture_output=True, text=True)


def bolum_d(tmp):
    print("D) IC RAPOR SIZINTI NOBETCISI — mutant GENIS AYNADA olculur (canli dizine dokunulmaz)")
    tools_d, hata = genis_ayna_kur(os.path.join(tmp, "d-temiz"))
    if hata:
        check("D0 genis ayna kuruldu", False, hata)
        return
    r = _kvt_kos(tools_d)
    check("D0 mutasyonsuz TEMIZ ayna -> YESIL (harness 'hep kirmizi' degil)",
          r.returncode == 0,
          "cikis=%d %s" % (r.returncode, ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1:]))

    tools_s, hata = genis_ayna_kur(os.path.join(tmp, "d-sizinti"), sizintili=True)
    if hata:
        check("D1 sizintili ayna kuruldu", False, hata)
        return
    r = _kvt_kos(tools_s)
    check("D1 SIZINTILI ayna (kokte IZLENEN %s) -> KIRMIZI" % D_SIZINTI_ADI,
          r.returncode == 1 and "KOK BELGE IZINSIZ" in (r.stdout or ""),
          "cikis=%d (yesil kalirsa kapi gercek sizintiyi GORMUYOR)" % r.returncode)

    for etiket, degisimler, sizintili in D_MUTANTLARI:
        tools_m, hata = genis_ayna_kur(os.path.join(tmp, "d-mut-" + etiket.split()[0]),
                                       {KVT: degisimler}, sizintili=sizintili)
        if hata:
            check(etiket + " -> KIRMIZI", False, hata)
            continue
        r = _kvt_kos(tools_m)
        # 🔴 "Traceback YOK" sarti: mutant SyntaxError/istisna ile colduyse python
        # yine cikis 1 verir ve kontrol SAHTE PASS olurdu (olculdu — D6/D7 tam
        # olarak boyle sahte gecti). Kirmizi DAVRANISTAN gelmeli, colmekten degil.
        coldu = "Traceback" in (r.stderr or "")
        check(etiket + " -> KIRMIZI", r.returncode == 1 and not coldu,
              "cikis=%d ayna=%s%s (YESIL kalirsa bu bozulma CI'dan SESSIZCE gecer)"
              % (r.returncode, "sizintili" if sizintili else "temiz",
                 " ⚠️COKME: " + (r.stderr or "").strip().splitlines()[-1:][0][:80] if coldu else ""))


# ------------------------------------------------ E) tablo sayaci TAM ESITLIGI (8 Agu 2026)
# NEDEN UCUNCU AYNA: ayna_kur yalniz kok DOSYALARINI, genis_ayna_kur ise kok girdilerini
# SYMLINK DIZIN olarak aynalar. `os.walk` bir SYMLINK dizine INMEZ -> is-akisi-kapisi.py'nin
# kesif ekseni (ci-kapsam-test.py'den import edilir) alt dizinleri GOREMEZ ve mutasyonsuz
# aynada bile iddia sayisi DUSER. OLCULDU (8 Agu): genis-symlink sekilli aynada Bolum C
# 146 iddia kosturdu (TABAN 162) -> E0 kontrolu HAKSIZ yere KIRMIZI yandi; ozyinelemeli
# aynada 204 iddia ile YESIL. Yani kontrol mutantinin dususu aracin sekliydi, kapinin
# kusuru degil ([[fikstur-degeri-mutasyon-koru]]: kontrol mutanti olmadan bu gorulmezdi).
# 🔴 ayna_kur / genis_ayna_kur'a DOKUNULMADI: A..D bolumleri onlarin bugunku sekline bagli.
#
# 🔴🔴 CHECKOUT SEKLI TUZAGI (bagimsiz curutucu, 8 Agu — bu bolum BIR KEZ boyle KIRILDI):
# ilk hali `.git`i yalniz DIZIN adlarindan atiyordu. Worktree'de `.git` bir DOSYADIR ->
# symlink'lendi, aynada git CALISTI, kesif yasadi, E0 yesil yandi. TAZE KLONDA (=
# `actions/checkout` sekli) `.git` bir DIZINDIR -> atildi, aynada git YOK,
# ci-kapsam-test.py::kesfet (`git ls-files`) bos/None dondu, D ekseni ~45 iddia atladi,
# iddia 204 -> 148 ve kapi FAIL-CLOSED kirmizi cikti. Sonuc: klonda E0 KIRMIZI,
# E1..E5 "KACTI" ve E1b/E2b YANLIS SEBEPLE pass etti (jeton yok cunku eski kod kor degil,
# KESIF olmus). Yani "ayirt edici kanit" CI'da hicbir sey olcmuyordu.
# ONARIM (sekilden BAGIMSIZ, tek sekle ozel kod YOK): `.git` HER IKI sekilde de (dosya ve
# dizin) atlanir ve aynaya KENDI git deposu kurulur; izlenen yol listesi GERCEK depodan
# (`git -C ROOT ls-files`) turetilir. Boylece `git ls-files` ciktisi iki sekilde de AYNI
# olur. Kanit E0b'de: aynanin iddia sayisi CANLI depodakiyle karsilastirilir (sabit 204
# YAZILMAZ — ikiz sabit yine ayrisirdi, [[ikiz-tanim-sessiz-ayrisma]]).
E_KAPI = "tools/is-akisi-kapisi.py"
E_ATLA = {".git"}          # DIZIN ve DOSYA sekli: ikisi de atlanir (asagida)
E_IDDIA_RE = re.compile(r"Kendini-test iddiasi\s*:\s*(\d+)")

# --- MUTASYON CAPALARI (her biri TAM BIR KEZ eslesmeli; eslesmezse harness BAYAT) ---
# Giris silme/ekleme METIN olarak degil, tablo TANIMINDAN SONRA calisan tek satirla
# yapilir: sozluk govdesinin bicimine kilitlenmez, ama len(SERIT_B)'yi GERCEKTEN degistirir.
# 🔴 CAPA 19 Agu'da TAZELENDI (SERIT B onarimi — OLCULEN kusur): E1/E1b mutantlari
# `SERIT_B` tablosundan bir giris DUSURUYORDU, ama 14 Agu'da o tablo BOSALTILDI
# (`SERIT_B = {}`; 111 elle beyan T1 turetimine devredildi). Bos sozlukte
# `next(iter(SERIT_B))` StopIteration atiyor -> kapi mutant altinda COKUYOR, jeton
# basmadan bitiyor ve harness "KACTI/COKME" diyordu; yani EKSEN OLCULMUYORDU.
# Eksen DEGISMEDI ("izlenen bir tablodan giris dusunce TABLO SAYACI KIRMIZI yanar");
# yalnizca capa BUGUN DOLU olan bir tabloya (`D_MUTANTLAR`, taban 20) tasindi.
# Enjeksiyon tablo TANIMINDAN SONRA calismali; `E_MUTANTLAR` tanimi kaynakta
# `D_MUTANTLAR`dan SONRA geldigi icin ona capalanir (D_MUTANTLAR o noktada DOLU).
E_SERIT_CAPA = "E_MUTANTLAR = ("
E_SIL = ("D_MUTANTLAR = D_MUTANTLAR[:-1]  # MUTANT E1: bir giris DUSURULDU\n"
         + E_SERIT_CAPA)
E_EKLE = ('D_MUTANTLAR = D_MUTANTLAR + (("MUTANT E2: taban guncellenmeden EKLENEN "\n'
          '                              "sentetik giris",) + tuple(D_MUTANTLAR[0][1:]),)\n'
          + E_SERIT_CAPA)
E_OP_CAPA = "        if len(tablo) != taban:"
E_OP_ESKI = "        if len(tablo) < taban:"
# 🔴 IDDIA TELAFISI (19 Agu 2026, SERIT B onarimi — OLCULEN golgelenme): E1/E1b
# capasi bos `SERIT_B`den DOLU `D_MUTANTLAR`a tasininca, bir giris DUSURMEK ayni
# anda C-IDDIA sayacini da dusuruyor (223 < 224) ve kapi TABLO SAYACI kontrolune
# VARMADAN "BOLUM C IDDIA SAYACI KIRMIZI" ile cikis yapiyordu -> E1'in olctugu
# eksen (tablo<->taban ayrismasi) baska bir eksenin kirmizisiyla GOLGELENIYORDU
# (olculdu). Telafi, dusen girisin iddia kaybini geri koyar: C sayaci tabanda
# kalir, kirmizinin SEBEBI tek basina tablo sayacidir. Desen yeni degil — E6b
# ayni telafiyi ters yonde kullanir.
E_IDDIA_TELAFI_CAPA = ("    for ad, metin, beklenen in BOZUK_ORNEKLER:\n"
                       "        iddia += 1")
E_IDDIA_TELAFI = ("    iddia += 1  # MUTANT TELAFI: dusen tablo girisinin iddia kaybi\n"
                  + E_IDDIA_TELAFI_CAPA)
# 🔴 TABAN CAPASI ARTIK SAYISIZ (8 Agu, rebase dersi): once `("SERIT_B", 67),` metnine
# capalanmisti; main tabani 85'e cekince capa BAYATLADI (`HARNESS BAYAT` gurultulu
# durdu — dogru davranis, ama her taban bump'inda tekrarlanir). Yerine tablo
# TANIMINDAN SONRA calisan ve tabani len()'den TURETEN bir satir enjekte edilir:
# hedef "tabanin gercek sayidan DUSUK olmasi" halidir, belirli bir sayi DEGIL.
E_TABAN_GEVSET = (
    'TABLO_TABANLARI = tuple(\n'
    '    (_a, (len(D_MUTANTLAR) - 2 if _a == "D_MUTANTLAR" else _t))\n'
    '    for _a, _t in TABLO_TABANLARI)  # MUTANT: D_MUTANTLAR tabani GEVSEK (eski hal)\n'
    + E_SERIT_CAPA)
E_GOVDE_CAPA = ("    hatalar = []\n"
                "    kapsam = globals()\n"
                "    for ad, taban in TABLO_TABANLARI:")
E_GOVDE_NOOP = "    return []\n" + E_GOVDE_CAPA
E_JETON = "TABLO SAYACI KIRMIZI"
E_OZTEST_JETON = "TABLO-NOBETCISI OLU"

# --- BOLUM G IDDIA SAYACI (8 Agu, 2. tur: `temiz_iddia < 7` -> `!= G_IDDIA_TABANI`) ---
# Sayac G8 ekseninin `iddia += 1` satiri uzerinden surulur: bir eksenin sayaci DUSERSE
# (E4) ya da taban guncellenmeden ARTARSA (E5) kapi konusmali. Olculdu: gercek 8, eski
# taban 7 -> pay 1, yani eski `< 7` kolu E4'e de E5'e de KORDU (E4b/E5b bunu gosterir).
# 🔴 CAPA 19 Agu'da TAZELENDI (SERIT B onarimi): K183b sonrasi kapida taban 11 oldu,
# "= 8" capasi 0 eslesmeye dustu — bolum E "HARNESS BAYAT" ile hicbir sey olcmuyordu.
# Eski-gevsek simulasyonu da ayni pay-1 mantigiyla 10'a cekildi.
E_G_CAPA = ("    iddia += 1\n"
            "    if yayin is None:\n"
            '        hatalar.append("G8 OLCULEMEDI')
E_G_SAYAC_SIL = ('    if yayin is None:\n'
                 '        hatalar.append("G8 OLCULEMEDI')
E_G_SAYAC_EKLE = "    iddia += 1\n" + E_G_CAPA
E_G_TABAN_CAPA = "G_IDDIA_TABANI = 11"
E_G_TABAN_ESKI = "G_IDDIA_TABANI = 10"
E_G_OP_CAPA = "        if temiz_iddia != G_IDDIA_TABANI:"
E_G_OP_ESKI = "        if temiz_iddia < G_IDDIA_TABANI:"
E_G_JETON = "G-IDDIA SAYACI BOZUK"

# --- M6: YENI EKSENIN KENDISI SESSIZCE SILINEBILIYOR MU (3. tur, curutucu bulgusu) ---
# Curutucu olctu: BUYUME iddiasi blogu silinip operator `<`'ye dondurulunce kapi rc=0,
# `--kendini-test` rc=0 ve iddia sayisi HALA 204 idi -> eksen kendini koruyamiyordu.
# Onarim: blok ADLI fonksiyona (_tablo_mekanizma_kontrol) tasindi, sayac her iddianin
# YANINDA +1 edilir (lump ikiz YOK) ve KENDINI_TEST_TABAN gercek sayiya cekildi.
# E6  = buyume iddiasi SILINDI + operator `<`  -> iddia DUSER -> C IDDIA SAYACI KIRMIZI
# E6b = ayni + sayac ELLE TELAFI edildi (`iddia += 2`) -> sayi tekrar tabana esitlenir ->
#       jeton YOK. Yani kirmiziyi getiren sey TURETILEN SAYACTIR; ikiz telafi edilirse
#       eksen yine kaybolur. (Bugunku kodun M6'ya KOR olma hali bu mutantla gosterilir.)
E_M6_CAPA = ("        # BUYUME EKSENI (tam esitligin tek kanidi): taban = len - 1.\n"
             "        iddia += 1\n"
             '        globals()["TABLO_TABANLARI"] = (("B_IDDIALAR", len(B_IDDIALAR) - 1),)\n'
             '        if not any("TABLO SAYACI KIRMIZI" in h for h in tablo_sayaci_kontrol()):\n'
             '            hatalar.append("TABLO-NOBETCISI OLU (BUYUME EKSENI): taban guncellenmeden "\n'
             '                           "BUYUME gorunmez -> pay birikir, taban kozmetiklesir ve pay "\n'
             '                           "kadar giris tek commit\'te SESSIZCE silinebilir (olculdu: "\n'
             '                           "SERIT_B 67/42, pay 25). Operator `!=` olmali, `<` DEGIL.")\n')
E_M6_SIL = "        # MUTANT M6: BUYUME EKSENI SILINDI\n"
# Silinen blok TEK bir `iddia += 1` tasir -> telafi de +1 olmali. (Ilk yazimda +2 idi ve
# E6b'nin `beklenen iddia` probu bunu YAKALADI: 205 != 204 -> "KESIF OLMUS/HUKUM GECERSIZ".
# Prob calisiyor demektir; hukum, sayinin TESADUFEN denk gelmesine birakilmiyor.)
E_M6_TELAFI = "        # MUTANT M6b: sayac ELLE TELAFI edildi\n        iddia += 1\n"
E_C_IDDIA_JETON = "BOLUM C IDDIA SAYACI KIRMIZI"

# --- K26 SINIF DENGESI: `<` BILEREK KALIYOR (3. tur, spec hatasi geri alindi) ---
# Iki vaka AYNI capadan surulur (tablo TANIMINDAN SONRA calisan satir):
#   E7 YENIDEN DAGITIM: bir kanarya DUSER + bir oldurucu KOPYASI eklenir -> toplam 26
#      SABIT, siniflar 11/15 -> `<` ile KIRMIZI (kanarya 15 < 16). Yani `!=`in
#      hedefledigi kacisi `<` ZATEN yakaliyor; `!=`in bu eksende kazanci SIFIR.
#   E8 MESRU BUYUME (YANLIS-POZITIF KANARYASI): gercek bir oldurucu KOPYASI eklenir +
#      TABLO_TABANLARI tabani 26 -> 27 -> siniflar 11/16, toplam 27 -> YESIL olmali.
#      `!=` bu vakada rc=1 veriyordu = SAHTE-KIRMIZI = tum ekibin yayini durur.
E_K26_CAPA = "K26_BAGLAM_MUTANTLAR = ("
E_K26_DAGITIM = (
    "_k26_kan = [m for m in K26_SATIR_FIKSTURLERI if not m[2]][0]\n"
    "_k26_old = [m for m in K26_SATIR_FIKSTURLERI if m[2]][0]\n"
    "K26_SATIR_FIKSTURLERI = tuple(\n"
    "    m for m in K26_SATIR_FIKSTURLERI if m is not _k26_kan\n"
    ") + ((\"MUTANT E7 KOPYA \" + _k26_old[0],) + tuple(_k26_old[1:]),)\n"
    + E_K26_CAPA)
# E8 tabani da SAYISIZ: yeni giris eklenir ve K26 tabani len()'den YENIDEN TURETILIR
# (mesru buyumede tabanin AYNI commit'te guncellenmesi zaten beklenen davranistir).
E_K26_BUYUME = (
    "_k26_old = [m for m in K26_SATIR_FIKSTURLERI if m[2]][0]\n"
    "K26_SATIR_FIKSTURLERI = K26_SATIR_FIKSTURLERI + (\n"
    "    (\"MUTANT E8 KOPYA \" + _k26_old[0],) + tuple(_k26_old[1:]),)\n"
    "TABLO_TABANLARI = tuple(\n"
    "    (_a, (len(K26_SATIR_FIKSTURLERI)\n"
    '          if _a == "K26_SATIR_FIKSTURLERI" else _t))\n'
    "    for _a, _t in TABLO_TABANLARI)\n"
    + E_K26_CAPA)
E_K26_JETON = "sinif dengesi bozuldu"


def akis_ayna_kur(hedef_kok, mutasyonlar=None):
    """OZYINELEMELI ayna: DIZINLER gercek, DOSYALAR symlink, aynaya KENDI git deposu.
    Doner: <hedef_kok>.

    mutasyonlar: {depo-goreli-yol: [(eski, yeni), ...]} -> o dosya GERCEK KOPYA yazilir.
    Canli calisma agacina HICBIR YAZMA yapilmaz. Mutasyon metni GERCEKTEN degistirmiyorsa
    harness BAYATTIR -> SystemExit ile gurultulu olur.

    🔴 SEKILDEN BAGIMSIZ: kaynak checkout'ta `.git` DOSYA (worktree) ya da DIZIN (klon)
    olabilir; ikisi de ATLANIR ve ayna kendi deposunu kurar. Izlenen yol listesi GERCEK
    depodan turetilir -> `git ls-files` ciktisi iki sekilde de AYNI. Git kurulamazsa
    FAIL-CLOSED SystemExit: sessizce git'siz ayna kurmak, olcmedigi halde 'olctum' demektir
    (bu bolum tam olarak boyle kirildi)."""
    mutasyonlar = mutasyonlar or {}
    uygulanan = set()
    aynalanan = []
    for dizin, altlar, dosyalar in os.walk(ROOT):
        altlar[:] = [a for a in altlar if a not in E_ATLA]
        rel = os.path.relpath(dizin, ROOT)
        h = hedef_kok if rel == "." else os.path.join(hedef_kok, rel)
        os.makedirs(h, exist_ok=True)
        for ad in dosyalar:
            if ad in E_ATLA:       # `.git` DOSYA sekli (worktree) — dizin sekliyle ayni
                continue
            kaynak = os.path.join(dizin, ad)
            yol = ad if rel == "." else os.path.join(rel, ad)
            hedef = os.path.join(h, ad)
            if os.path.lexists(hedef):
                continue
            if yol in mutasyonlar:
                with open(kaynak, encoding="utf-8") as f:
                    metin = f.read()
                for eski, yeni in mutasyonlar[yol]:
                    if metin.count(eski) != 1:
                        raise SystemExit(
                            "HARNESS BAYAT (bolum E): %s icinde mutasyon dayanagi TAM BIR KEZ "
                            "eslesmedi (bulunan=%d): %r\n(kod degismis olabilir — mutasyonu "
                            "guncelle, YOKSA bu bolum hicbir sey olcmuyor demektir)"
                            % (yol, metin.count(eski), eski[:90]))
                    metin = metin.replace(eski, yeni)
                with open(hedef, "w", encoding="utf-8") as f:
                    f.write(metin)
                uygulanan.add(yol)
            elif yol.replace(os.sep, "/").startswith(".github/workflows/"):
                # 🔴 IS AKISI DOSYALARI GERCEK KOPYA (19 Agu 2026, SERIT B onarimi —
                # OLCULEN kusur): symlink olarak stage'lenen dosyanin git BLOB'u
                # dosyanin ICERIGI degil HEDEF YOLUDUR. Kapi is akislarini `git show`
                # ile de okuyunca YAML yerine 100 baytlik bir yol dizesi aliyor ve
                # "kok mapping degil" diye fail-closed KIRMIZI basiyordu — E0 kontrol
                # mutanti dahil TUM bolum E hukumleri bu yuzden gecersizdi (olculdu).
                # Kume dar: kapinin git'ten okudugu tek dizin. Mutasyon uygulanan
                # dosyalar zaten yukaridaki kolda gercek kopya yaziliyor.
                shutil.copyfile(kaynak, hedef)
            else:
                os.symlink(kaynak, hedef)
            aynalanan.append(yol)
    eksik = set(mutasyonlar) - uygulanan
    if eksik:
        raise SystemExit("HARNESS BAYAT (bolum E): mutasyon hedefi aynada bulunamadi: %s"
                         % sorted(eksik))

    # ---- aynaya KENDI git deposu (kesif `git ls-files` ile yapiliyor) --------------
    r = git("init", "--quiet", hedef_kok)
    if r.returncode != 0:
        raise SystemExit("HARNESS OLCEMEZ (bolum E): ayna git init basarisiz: %s"
                         % (r.stderr or "").strip()[:200])
    r = git("-C", ROOT, "ls-files")
    if r.returncode != 0:
        raise SystemExit("HARNESS OLCEMEZ (bolum E): kaynak depo `ls-files` basarisiz "
                         "(%s) -> aynanin izlenen listesi TURETILEMEZ"
                         % (r.stderr or "").strip()[:200])
    izlenen = [y for y in (r.stdout or "").splitlines() if y]
    mevcut = set(aynalanan)
    eklenecek = [y for y in izlenen if y in mevcut]
    if not eklenecek:
        raise SystemExit("HARNESS OLCEMEZ (bolum E): aynaya eklenecek IZLENEN dosya YOK "
                         "(kaynak depoda %d izlenen yol vardi)" % len(izlenen))
    # 🔴 `-f`: ayna kokunde .gitignore de aynalanir; izlenen listesi GERCEK depodan
    # geldigi icin ignore kurallarinin aynada listeyi kirpmasina izin verilmez.
    r = git("-C", hedef_kok, "add", "-f", "--", *eklenecek)
    if r.returncode != 0:
        raise SystemExit("HARNESS OLCEMEZ (bolum E): ayna `git add` basarisiz: %s"
                         % (r.stderr or "").strip()[:200])
    # 🔴 AYNAYA IKI COMMIT (19 Agu 2026, SERIT B onarimi — olculen kusur): kapinin
    # K80 "yeni CI adimi" ekseni `git rev-parse HEAD` VE `HEAD^` ister (bu itmenin
    # GETIRDIGI adimlari onceki commit'e gore turetir); commit'siz aynada HEAD hic
    # cozulmuyor, tek commit'te de HEAD^ cozulmuyordu ve KAPI mutasyondan BAGIMSIZ
    # "YENI CI ADIMI OLCULEMEDI" fail-closed kirmizisi basiyordu — E0 kontrol mutanti
    # dahil TUM bolum E hukumleri bu yuzden gecersizdi (olculdu). Once BOS bir taban
    # commit'i, sonra icerik commit'i: HEAD^ = bos taban. Kimlik config'e YAZILMAZ,
    # her commit'e `-c` ile verilir (sentetik_git deseni).
    # 🔴 COMMIT INDEX'TEN URETILIR, `git commit` KULLANILMAZ: ayna dosyalari SYMLINK
    # oldugu icin `git commit` calisma agacini tararken "Too many levels of symbolic
    # links" ile duser (olculdu). `write-tree` + `commit-tree` + `update-ref` yalniz
    # INDEX'i okur, calisma agacina HIC bakmaz — ayna zaten `git add -f` ile eksiksiz
    # stage'lenmisti. Kimlik ortam degiskeniyle verilir, hicbir config'e YAZILMAZ.
    kimlik_ortam = dict(os.environ)
    kimlik_ortam.update({
        "GIT_AUTHOR_NAME": "e-ayna", "GIT_AUTHOR_EMAIL": "e-ayna@ornek.gecersiz",
        "GIT_COMMITTER_NAME": "e-ayna", "GIT_COMMITTER_EMAIL": "e-ayna@ornek.gecersiz",
    })

    def _g(*args):
        return subprocess.run(["git", "-C", hedef_kok] + list(args),
                              capture_output=True, text=True, env=kimlik_ortam)

    r = _g("write-tree")
    if r.returncode != 0:
        raise SystemExit("HARNESS OLCEMEZ (bolum E): ayna write-tree basarisiz: %s"
                         % (r.stderr or "").strip()[:200])
    agac = (r.stdout or "").strip()
    # BOS taban commit'i: kapinin K80 ekseni `HEAD^`i (bu itmenin ONCESI) ister.
    r = _g("commit-tree", "-m", "ayna bos taban", agac)
    if r.returncode != 0:
        raise SystemExit("HARNESS OLCEMEZ (bolum E): ayna taban commit-tree basarisiz: %s"
                         % (r.stderr or "").strip()[:200])
    taban_sha = (r.stdout or "").strip()
    r = _g("commit-tree", "-p", taban_sha, "-m", "ayna icerik", agac)
    if r.returncode != 0:
        raise SystemExit("HARNESS OLCEMEZ (bolum E): ayna icerik commit-tree basarisiz: %s"
                         % (r.stderr or "").strip()[:200])
    tepe_sha = (r.stdout or "").strip()
    r = _g("update-ref", "HEAD", tepe_sha)
    if r.returncode != 0:
        raise SystemExit("HARNESS OLCEMEZ (bolum E): ayna update-ref basarisiz: %s"
                         % (r.stderr or "").strip()[:200])
    return hedef_kok


E_KOSUM = [0]      # kac tam kapi kosumu yapildi (sure beyani ciktida turer)


def _e_kos(kok, bayrak=None):
    """Kapiyi <kok> altinda kostur. Doner: (rc, cikti, coldu, iddia|None)."""
    E_KOSUM[0] += 1
    cmd = [PY, os.path.join(kok, "tools", "is-akisi-kapisi.py")]
    if bayrak:
        cmd.append(bayrak)
    # 🔴 Bytecode onbellegi devre disi: ayni uzunlukta/ayni saniyede yazilan mutant
    # eskisiyle karisabilir ([[mutasyon-bytecode-onbellegi]]).
    ortam = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(cmd, capture_output=True, text=True, env=ortam)
    cikti = (r.stdout or "") + (r.stderr or "")
    m = E_IDDIA_RE.search(cikti)
    return (r.returncode, cikti, "Traceback" in (r.stderr or ""),
            int(m.group(1)) if m else None)


def bolum_e(tmp):
    print("E) TABLO SAYACI TAM ESITLIGI — mutant OZYINELEMELI AYNADA olculur "
          "(canli dosyaya dokunulmaz)")
    e_baslangic = time.time()
    E_KOSUM[0] = 0
    oldurulen = 0
    toplam = 7

    # ---- CANLI TABAN: aynayi karsilastiracagimiz sayi CANLI depodan olculur -------
    # 🔴 Sabit (204 gibi) YAZILMAZ: ikiz sabit yine sessizce ayrisirdi. Canli kosum
    # kirmiziysa bu bolumun hukmu OLCULEMEDI'dir, "yesil" degil.
    canli_rc, _cc, canli_coldu, canli_iddia = _e_kos(ROOT)
    if canli_rc != 0 or canli_coldu or canli_iddia is None:
        check("E-TABAN: CANLI depoda kapi YESIL ve iddia sayisi okunabilir", False,
              "OLCULEMEDI: canli rc=%d coldu=%s iddia=%s -> ayna karsilastirmasi icin "
              "taban YOK; bolum E hukum VERMEZ" % (canli_rc, canli_coldu, canli_iddia))
        print("  MUTASYON: oldurulen=OLCULEMEDI/%d · kontrol=OLCULEMEDI" % toplam)
        return
    check("E-TABAN: CANLI depoda kapi YESIL (iddia=%d)" % canli_iddia, True,
          "ayna hukumleri bu tabana GORE kurulur (sabit yazilmaz)")

    kok0 = akis_ayna_kur(os.path.join(tmp, "e0"))
    rc, cikti, coldu, iddia0 = _e_kos(kok0)
    kontrol_yesil = rc == 0 and not coldu
    check("E0 KONTROL MUTANTI: mutasyonsuz ayna -> YESIL", kontrol_yesil,
          "MUTANT=<yok> · beklenen=YESIL(rc 0) · gozlenen=rc %d%s · HUKUM=%s "
          "(dususe E1..E5 hukmu GECERSIZ: arac olcmuyor)"
          % (rc, " COKME" if coldu else "", "YESIL" if kontrol_yesil else "KIRMIZI"))
    # 🔴 E0b — KESIF CANLILIK PROBU (bugunku kirilmanin tam nobetcisi): ayna rc=0 verse
    # bile kesif olmus olabilir; o zaman TUM mutant hukumleri "kesif olu" yuzunden dogar
    # ve degisiklige ATFEDILEMEZ. Iddia sayisi CANLI ile AYNI olmak ZORUNDA.
    kesif_yasiyor = iddia0 == canli_iddia
    check("E0b KESIF CANLILIK: aynanin iddia sayisi CANLI ile AYNI", kesif_yasiyor,
          "MUTANT=<yok> · beklenen=iddia %d · gozlenen=%s · HUKUM=%s (sapmada `git "
          "ls-files` aynada olmustur -> D ekseni atlanir, jeton yoklugu 'eski kod kor' "
          "SANILIR; checkout sekli tuzagi)"
          % (canli_iddia, iddia0, "KESIF YASIYOR" if kesif_yasiyor else "KESIF OLMUS"))

    for etiket, mut, bayrak, jeton in (
            ("E1 izlenen tablodan bir giris DUSURULDU (iddia telafili)",
             {E_KAPI: [(E_SERIT_CAPA, E_SIL),
                       (E_IDDIA_TELAFI_CAPA, E_IDDIA_TELAFI)]},
             None, E_JETON),
            ("E2 SERIT_B'ye giris EKLENDI (taban ayni)", {E_KAPI: [(E_SERIT_CAPA, E_EKLE)]},
             None, E_JETON),
            ("E3 tablo_sayaci_kontrol() govdesi `return []`",
             {E_KAPI: [(E_GOVDE_CAPA, E_GOVDE_NOOP)]}, "--kendini-test", E_OZTEST_JETON),
            ("E4 BOLUM G: G8 ekseninin `iddia += 1` sayaci SILINDI",
             {E_KAPI: [(E_G_CAPA, E_G_SAYAC_SIL)]}, None, E_G_JETON),
            ("E5 BOLUM G: taban guncellenmeden fazladan eksen sayaci EKLENDI",
             {E_KAPI: [(E_G_CAPA, E_G_SAYAC_EKLE)]}, None, E_G_JETON),
            ("E6 M6: BUYUME iddiasi SILINDI + operator `<` (yeni eksen sessizce silinir mi)",
             {E_KAPI: [(E_M6_CAPA, E_M6_SIL), (E_OP_CAPA, E_OP_ESKI)]}, None,
             E_C_IDDIA_JETON),
            ("E7 K26 YENIDEN DAGITIM: kanarya dusuruldu + oldurucu kopyasi eklendi (11/15)",
             {E_KAPI: [(E_K26_CAPA, E_K26_DAGITIM)]}, None, E_K26_JETON)):
        kok = akis_ayna_kur(os.path.join(tmp, "e-" + etiket.split()[0]), mut)
        rc, cikti, coldu, _i = _e_kos(kok, bayrak)
        # 🔴 KIRMIZI DAVRANISTAN gelmeli, COKMEDEN degil: cikis kodu degil BASILAN
        # jeton yargilanir ([[hukum-yanlis-birimde]]).
        olduruldu = rc == 1 and not coldu and jeton in cikti
        oldurulen += 1 if olduruldu else 0
        check(etiket + " -> KIRMIZI", olduruldu,
              "MUTANT=%s · beklenen=KIRMIZI(rc 1 + %r) · gozlenen=rc %d jeton %s%s · "
              "HUKUM=%s" % (etiket.split()[0], jeton, rc,
                            "VAR" if jeton in cikti else "YOK",
                            " ⚠️COKME" if coldu else "",
                            "OLDU" if olduruldu else "KACTI"))

    # --- YANLIS-POZITIF KANARYASI: MESRU degisiklik YESIL kalmali ---
    # 🔴 Bu iddia `<`i KORUYOR: K26 sinif kolu `!=` yapilirsa burada rc=1 cikar ve
    # bolum KIRMIZI yanar. Yani "tutarlilik" gerekcesiyle geri donen biri aninda gorur.
    kok = akis_ayna_kur(os.path.join(tmp, "e-E8"),
                        {E_KAPI: [(E_K26_CAPA, E_K26_BUYUME)]})
    rc, cikti, coldu, iddia8 = _e_kos(kok)
    e8_yesil = rc == 0 and not coldu
    check("E8 K26 MESRU BUYUME (gercek oldurucu eklendi, taban 26->27, siniflar 11/16) "
          "-> YESIL", e8_yesil,
          "MUTANT=E8 · beklenen=YESIL(rc 0) · gozlenen=rc %d%s iddia=%s · HUKUM=%s "
          "(KIRMIZI ise sinif kolu SAHTE-KIRMIZI yakiyor = tum ekibin yayini durur; "
          "`!=` bu vakada rc=1 veriyordu)"
          % (rc, " ⚠️COKME" if coldu else "", iddia8,
             "YANLIS-POZITIF YOK" if e8_yesil else "SAHTE-KIRMIZI"))

    # --- AYIRT EDICILER: ayni girdide ESKI KOD ne yapiyordu ---
    # 🔴 `kor` hukmu KESIF CANLILIGINI da sart kosar: 8 Agu'da E1b/E2b tam olarak
    # "jeton yok" diye PASS etmisti, ama sebep eski kodun korlugu DEGIL aynada olen
    # kesifti. Beklenen iddia sayisi CANLI olcumden gelir (sabit yazilmaz).
    for etiket, mut, jeton, bek_iddia, aciklama in (
            # 🔴 BEKLENEN IDDIA MUTANTIN ETKISINI TASIR (19 Agu 2026, SERIT B onarimi):
            # E1/E2 capasi bos `SERIT_B`den DOLU `D_MUTANTLAR`a tasindi; o tablo
            # KOSULAN mutant listesidir, yani bir giris dusmek/eklemek iddia sayisini
            # DOGRUDAN -1/+1 kaydirir. "Kesif yasiyor" kontrolu bu bilinen kaymayi
            # hesaba katmazsa mesru mutant "KESIF OLMUS" sanilir ve hukum gecersiz
            # ilan edilirdi (olculdu: 223 ve 225 gorulup 224 beklenmisti).
            ("E1b E1 + ESKI KOD (operator `<` + taban len-2 GEVSEK)",
             {E_KAPI: [(E_SERIT_CAPA, E_SIL), (E_SERIT_CAPA, E_TABAN_GEVSET),
                       (E_OP_CAPA, E_OP_ESKI),
                       (E_IDDIA_TELAFI_CAPA, E_IDDIA_TELAFI)]}, E_JETON, canli_iddia,
             "gevsek taban OLU korumadir: pay kadar beyan sessizce silinebilir "
             "(bu tablonun kendi tarihi: pay 25'te SABIT kalmisti)"),
            ("E2b E2 + operator `<` (taban gercek sayida)",
             {E_KAPI: [(E_SERIT_CAPA, E_EKLE), (E_OP_CAPA, E_OP_ESKI)]}, E_JETON,
             canli_iddia + 1,
             "taban guncellenmeden BUYUME gorunmezdi -> pay yeniden birikirdi"),
            ("E4b E4 + ESKI KOD (operator `<` + taban 7)",
             {E_KAPI: [(E_G_CAPA, E_G_SAYAC_SIL), (E_G_OP_CAPA, E_G_OP_ESKI),
                       (E_G_TABAN_CAPA, E_G_TABAN_ESKI)]}, E_G_JETON, canli_iddia,
             "1 paylik olu koruma: bir eksenin sayaci dususu `7 < 7` ile YESIL kalirdi"),
            ("E5b E5 + ESKI KOD (operator `<` + taban 7)",
             {E_KAPI: [(E_G_CAPA, E_G_SAYAC_EKLE), (E_G_OP_CAPA, E_G_OP_ESKI),
                       (E_G_TABAN_CAPA, E_G_TABAN_ESKI)]}, E_G_JETON, canli_iddia,
             "artis hic gorulmezdi -> pay birikir ve pay kadar eksen sessizce silinebilir"),
            ("E6b E6 + sayac ELLE TELAFI (`iddia += 1`, lump ikiz taklidi)",
             {E_KAPI: [(E_M6_CAPA, E_M6_SIL + E_M6_TELAFI), (E_OP_CAPA, E_OP_ESKI)]},
             E_C_IDDIA_JETON, canli_iddia,
             "ikiz sayac telafi edilirse eksen YINE sessizce kaybolur -> E6'nin "
             "kirmizisini getiren sey TURETILEN sayactir, iddianin varligi degil")):
        kok = akis_ayna_kur(os.path.join(tmp, "e-" + etiket.split()[0]), mut)
        rc, cikti, coldu, iddia = _e_kos(kok)
        kesif_ok = iddia == bek_iddia
        kor = jeton not in cikti and not coldu and kesif_ok
        check(etiket + " -> %r jetonu YOK (eski kod KOR)" % jeton, kor,
              "MUTANT=%s · beklenen=jeton YOK + iddia %s (kesif YASIYOR) · gozlenen=rc %d "
              "jeton %s iddia %s%s · HUKUM=%s (%s)"
              % (etiket.split()[0], bek_iddia, rc, "VAR" if jeton in cikti else "YOK",
                 iddia, " ⚠️COKME" if coldu else "",
                 "AYIRT EDICI" if kor else
                 ("KESIF OLMUS -> HUKUM GECERSIZ" if not kesif_ok else "AYIRT ETMIYOR"),
                 aciklama))

    # 🔴 SURE CIKTIDA BASILIR, YORUMDA TUTULMAZ: is akisi yorumundaki sabit sure beyani
    # ("olculdu 38 s") bu bolum eklenince bayatladi — olcum kendi ciktisinda yasar.
    print("  MUTASYON: oldurulen=%d/%d · kontrol=%s · sure=%.0f sn (%d varyant: her biri "
          "ayna + tam kapi kosumu)"
          % (oldurulen, toplam, "YESIL" if kontrol_yesil and kesif_yasiyor else "KIRMIZI",
             time.time() - e_baslangic, E_KOSUM[0]))


def main():
    tmp = tempfile.mkdtemp(prefix="pruvo-nobetci-mutasyon-")
    try:
        bolum_a(tmp)
        bolum_b(tmp)
        bolum_c(tmp)
        bolum_d(tmp)
        bolum_e(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("-" * 74)
    if FAILS:
        print("SONUC: KIRMIZI ❌  (%d basarisiz)" % len(FAILS))
        for f in FAILS:
            print("   - " + f)
        return 1
    print("SONUC: YESIL ✅  — nobetciler bozulunca KIRMIZI yaniyor (olculdu, tahmin degil).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
