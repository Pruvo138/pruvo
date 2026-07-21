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

Ag'a cikmaz. urunler.json / .urun-kaynaklari.json OKUNMAZ ve YAZILMAZ (sentetik katalog).
Cikis: 0 = yesil, 1 = kirmizi.   Calistir: python3 tools/nobetci-mutasyon-test.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

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
    return subprocess.run(["git"] + list(a), capture_output=True, text=True)


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


def main():
    tmp = tempfile.mkdtemp(prefix="pruvo-nobetci-mutasyon-")
    try:
        bolum_a(tmp)
        bolum_b(tmp)
        bolum_c(tmp)
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
