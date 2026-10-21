#!/usr/bin/env python3
"""Mukerrer kapisinin pre-commit yargi kapsamini izole depolarda sinar.

Iki eksen olculur:
  * KAPSAM  — kanca commit'in DOKUNDUGU seyi mi yargiliyor, yoksa agacta/HEAD'de
              ne varsa hepsini mi (K143 (b) kolu).
  * ISTISNA — dogrulanmis mesru cift bir yere COKEBILIYOR mu ve o kayit
              GENISLEYIP gercek mukerreri kacirmiyor mu (K143 (a) kolu).

Sondaki MUTASYON KANITI iddialarin canli oldugunu gosterir: kapinin KOPYASINA
kasitli bir delik acilir ve ilgili iddianin KIRMIZI yanmasi SART kosulur. Kanit
anlatilmaz, KOSTURULUR ([[mutasyon-kaniti-yeniden-uretilebilir]]).
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile


TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(TOOLS, "mukerrer-kontrol.py")
# Kapinin kardes kapanisi (veri_kok.py ...) ELLE LISTELENMEZ — import'lardan TURETILIR.
_vk_spec = importlib.util.spec_from_file_location("veri_kok", os.path.join(TOOLS, "veri_kok.py"))
veri_kok = importlib.util.module_from_spec(_vk_spec)
_vk_spec.loader.exec_module(veri_kok)
TEMIZ = [
    {"id": "urun-a", "baslik": "Baslik A"},
    {"id": "urun-b", "baslik": "Baslik B"},
]
MUKERRER = [
    {"id": "urun-a", "baslik": "Ayni Baslik"},
    {"id": "urun-b", "baslik": "Ayni Baslik"},
]

# Kosan mutasyon — [(bul, koy), ...] ya da None. `_kapi_yaz` her depo kurulumunda
# uygular. Liste olmasinin sebebi: bazi savunmalar IKI KATMANLIDIR (okuyucu + eslestirici);
# boyle bir iddiayi ancak HER IKI katmani birden delen bir mutant sinayabilir.
MUTASYON = None


def _kapi_yaz(hedef):
    """Kapiyi hedefe serer; MUTASYON aciksa KOPYAYA uygular (kaynak agac KIRLENMEZ).

    Desen kaynakta yoksa YUKSEK SESLE duser: uygulanmamis bir mutasyonun
    "yakalandi" gorunmesi sahte kanittir ([[mutasyon-diske-yazma-tuzagi]])."""
    with open(KAPI, encoding="utf-8") as dosya:
        kaynak = dosya.read()
    for bul, koy in (MUTASYON or []):
        if bul not in kaynak:
            raise AssertionError(
                "MUTASYON UYGULANAMADI — desen kaynakta YOK: %r" % bul)
        kaynak = kaynak.replace(bul, koy, 1)
    veri_kok.kum_kur(os.path.dirname(hedef), {os.path.basename(hedef): kaynak}, TOOLS)
    shutil.copymode(KAPI, hedef)


def _kos(kok, *args, env_ek=None, veri=None):
    # VERI KOKU acikca kurulur (vars. kok; worktree vakalarinda ANA agac = uretim
    # cozumu) — git/__file__ sansina birakilmaz.
    ortam = veri_kok.kum_ortami(veri or kok)
    if env_ek:
        ortam.update(env_ek)
    return subprocess.run(
        [sys.executable, os.path.join(kok, "tools", "mukerrer-kontrol.py")] + list(args),
        cwd=kok,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=ortam,
    )


def _git(kok, *args):
    # KANONIK sentetik git (fikstur-git-sizinti-kapisi sozlesmesi): miras GIT_*
    # kesif baglami scrub'lanir, cwd acikca sabitlenir.
    from git_ortami import sentetik_git
    return sentetik_git(kok, *args, check=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True)


def _yaz(path, veri):
    with open(path, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False)
        dosya.write("\n")


def _depo(ilk=TEMIZ, commit=True, git=True):
    gecici = tempfile.TemporaryDirectory(prefix="pruvo-mukerrer-kapsam-")
    kok = gecici.name
    os.makedirs(os.path.join(kok, "tools"))
    _kapi_yaz(os.path.join(kok, "tools", "mukerrer-kontrol.py"))
    _yaz(os.path.join(kok, "urunler.json"), ilk)
    # Kaynak haritasi (21 Eki 2026): kapi harita yok/bozukken fail-closed rc=2 verir
    # (tools/mukerrer-kaynak-failclosed-test.py). Gercek depoda harita git-disi ama
    # VAR; fikstur de bos-ama-gecerli haritayla kurulur, yoksa her iddia rc=2'ye duser.
    _yaz(os.path.join(kok, ".urun-kaynaklari.json"), {})
    if not git:
        return gecici, kok
    _git(kok, "init", "-q")
    _git(kok, "config", "user.name", "Kapsam Testi")
    _git(kok, "config", "user.email", "kapsam@example.invalid")
    if commit:
        _git(kok, "add", "urunler.json", "tools")
        _git(kok, "commit", "-q", "--no-verify", "-m", "taban")
    return gecici, kok


def _a1():
    """Stage disi kalan YABANCI urun verisi commit'i bloklamaz."""
    gecici, kok = _depo()
    try:
        _yaz(os.path.join(kok, "urunler.json"), MUKERRER)
        with open(os.path.join(kok, "alakasiz.py"), "w", encoding="utf-8") as dosya:
            dosya.write("DEGER = 1\n")
        _git(kok, "add", "alakasiz.py")
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode == 0, sonuc
    finally:
        gecici.cleanup()


def _a2():
    gecici, kok = _depo()
    try:
        _yaz(os.path.join(kok, "urunler.json"), MUKERRER)
        _git(kok, "add", "urunler.json")
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode != 0 and "MUKERRER BASLIK" in sonuc.stdout, sonuc
    finally:
        gecici.cleanup()


def _a3():
    gecici, kok = _depo([{"id": "eski", "baslik": "Mevcut Baslik"}])
    try:
        _yaz(os.path.join(kok, "urunler.json"), [
            {"id": "yeni", "baslik": "Mevcut Baslik"},
            {"id": "eski", "baslik": "Mevcut Baslik"},
        ])
        _git(kok, "add", "urunler.json")
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode != 0 and "yeni, eski" in sonuc.stdout, sonuc
    finally:
        gecici.cleanup()


def _a4():
    """OLCULEMEDI yesil sayilmaz: git okunamiyorsa on-eleme ELEMEZ, tarama KOSAR.

    17 Agu 2026'da bu iddia "HEAD'siz depo" uzerinden olculuyordu; kapsam
    on-elemesi gelince o kurulum artik MESRU bir atlamadir (urun dosyasi
    stage'lenmemis). Iddianin ASIL konusu — olculemeyen seyin yesil sayilmamasi —
    korunuyor, olcum noktasi git'in KENDISININ okunamadigi hale tasindi."""
    gecici, kok = _depo(MUKERRER, git=False)
    try:
        sonuc = _kos(kok, "--pre-commit",
                     env_ek={"GIT_DIR": os.path.join(kok, "boyle-bir-git-yok")})
        return (
            sonuc.returncode != 0
            and "COMMIT KAYNAGI OKUNAMADI" in sonuc.stdout
            and "calisma agaci tarandi" in sonuc.stdout
        ), sonuc
    finally:
        gecici.cleanup()


def _a5():
    gecici, kok = _depo()
    try:
        _yaz(os.path.join(kok, "urunler.json"), MUKERRER)
        sonuc = _kos(kok)
        return sonuc.returncode != 0 and "MUKERRER BASLIK" in sonuc.stdout, sonuc
    finally:
        gecici.cleanup()


# ══════════════════════════════════════════════════════════════════════════════
# A6-A8 — ISTISNA KAYDI WORKTREE'DE DE GORULMELI (16 Agu 2026, olculdu)
# ══════════════════════════════════════════════════════════════════════════════
# `.mukerrer-istisna.json` .gitignore'dadir; `git worktree add` IZLENMEYEN dosyalari
# TASIMAZ. Olculen sonuc: AYNI HEAD icin ana agacta rc=0, worktree'de rc=1 — hukum
# AGACA GORE degisiyordu. Bedeli: iki tur kancayi ATLADI, `k119e` worktree'si
# temizlenemedi, urun verisine HIC dokunmayan commit'ler bile bloklandi.
# A6 dogru davranisi, A7+A8 ise duzeltmenin KAPSAMINI (fail-closed kalmasini) tutar.
KAYNAK_URL = "https://example.invalid/paylasilan-kaynak"


def _paylasilan_kaynak_deposu(istisna=None, eski_cift=False):
    """(gecici, ana_kok, worktree_kok) — ayni kaynagi paylasan IKI urun + worktree.

    `.urun-kaynaklari.json` COMMIT'LENIR (fikstur onu izlenen tutar),
    `.mukerrer-istisna.json` ise YALNIZ ana agaca IZLENMEDEN yazilir (gercekte
    .gitignore'da). Worktree'de urunler.json'a bir EK STAGE'LENIR: K143 kapsam
    on-elemesi urun dosyasina dokunmayan commit'i eler, bu iddialarin konusu ise
    kapsam DEGIL istisna COZUMLEMESIDIR — o yuzden tarama kapsam ICINE alinir.

    Kaynagi paylasan cift VARSAYILAN olarak commit'in EKLEDIGI `urun-c`yi icerir
    (14 Eki: HEAD'de zaten duran cift artik bloklamaz — istisna ekseni ancak YENI
    bir ciftte olculebilir). `eski_cift=True` cifti HEAD'deki iki kayda kurar
    (cgtrader vakasi, A15)."""
    gecici, kok = _depo()
    ikinci = "urun-b" if eski_cift else "urun-c"
    _yaz(os.path.join(kok, ".urun-kaynaklari.json"),
         {"urun-a": {"link": KAYNAK_URL}, ikinci: {"link": KAYNAK_URL}})
    _git(kok, "add", ".urun-kaynaklari.json")
    _git(kok, "commit", "-q", "--no-verify", "-m", "kaynaklar")
    if istisna is not None:
        _yaz(os.path.join(kok, ".mukerrer-istisna.json"), istisna)
    wt = os.path.join(kok, "wt")
    _git(kok, "worktree", "add", "-q", "-b", "dal", wt)
    _yaz(os.path.join(wt, "urunler.json"),
         TEMIZ + [{"id": "urun-c", "baslik": "Baslik C"}])
    _git(wt, "add", "urunler.json")
    return gecici, kok, wt


def _a6():
    gecici, ana, wt = _paylasilan_kaynak_deposu([{"kaynak": KAYNAK_URL}])
    try:
        sonuc = _kos(wt, "--pre-commit", veri=ana)
        return sonuc.returncode == 0, sonuc
    finally:
        gecici.cleanup()


def _a7():
    gecici, ana, wt = _paylasilan_kaynak_deposu(None)
    try:
        sonuc = _kos(wt, "--pre-commit", veri=ana)
        return (sonuc.returncode != 0
                and "MUKERRER KAYNAK" in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


def _a8():
    gecici, ana, wt = _paylasilan_kaynak_deposu(
        [{"kaynak": "https://example.invalid/BASKA-kaynak"}])
    try:
        sonuc = _kos(wt, "--pre-commit", veri=ana)
        return (sonuc.returncode != 0
                and "MUKERRER KAYNAK" in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


# ══════════════════════════════════════════════════════════════════════════════
# A9-A14 — K143 (17 Agu 2026, olculdu): KAPI FIILEN DEVRE DISI KALMISTI
# ══════════════════════════════════════════════════════════════════════════════
# (b) KAPSAM: kanca commit'in kapsamini hic sormuyordu. urunler.json
#     stage'lenmemisse yargi HEAD'e dusuyor — yani YALNIZ `DEVAM.md` degistiren bir
#     commit bile HEAD'de duran bir urun mukerrerinden BLOKLANIYORDU
#     ([[kanca-stage-disi-agaci-tarar]]). A9/A10 CIFTI ayirt edicidir: ayni HEAD,
#     tek fark urun dosyasinin stage'lenip stage'lenmedigi.
# (a) ISTISNA: BASLIK ekseninin istisnasi YOKTU; mimarca dogrulanmis mesru bir cift
#     hicbir yere cokemedi ve iki ev atlama degiskenini kullandi. A11-A13 istisnanin
#     hem CALISTIGINI hem de GENISLEMEDIGINI olcer.
CIFT_BASLIK = "Ayni Ad Farkli Tasarim"
BASLIK_CIFTI = [
    {"id": "kaynak-a-parca", "baslik": CIFT_BASLIK},
    {"id": "kaynak-b-parca", "baslik": CIFT_BASLIK},
]
UCUNCU_KAYIT = BASLIK_CIFTI + [{"id": "kaynak-c-parca", "baslik": CIFT_BASLIK}]
BASLIK_ISTISNASI = [{
    "baslik": CIFT_BASLIK,
    "idler": ["kaynak-a-parca", "kaynak-b-parca"],
    "neden": "Test fiksturu: incelenmis, birbirinden bagimsiz iki tasarim",
}]


def _baslik_depo(urunler, istisna):
    gecici, kok = _depo([{"id": "taban", "baslik": "Taban Kaydi"}])
    if istisna is not None:
        _yaz(os.path.join(kok, ".mukerrer-istisna.json"), istisna)
    _yaz(os.path.join(kok, "urunler.json"), urunler)
    _git(kok, "add", "urunler.json")
    return gecici, kok


def _a9():
    """HEAD'de GERCEK mukerrer var; commit urun dosyalarina DOKUNMUYOR -> rc=0."""
    gecici, kok = _depo(MUKERRER)
    try:
        with open(os.path.join(kok, "DEVAM.md"), "w", encoding="utf-8") as dosya:
            dosya.write("- defter satiri\n")
        _git(kok, "add", "DEVAM.md")
        sonuc = _kos(kok, "--pre-commit")
        return (sonuc.returncode == 0 and "ATLANDI" in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


def _a10():
    """AYNI HEAD, ama urunler.json STAGE'LENMIS -> tarama AYNEN kosar.

    14 Eki 2026: HEAD'deki cift artik BLOKLAMAZ (BaBa 20:1x sinif hukmu) ama
    tarama KOSMUS olmali — kanit, onceden-var NOT satirinin basilmasidir (A9'un
    ATLANDI satirindan ayirt edici)."""
    gecici, kok = _depo(MUKERRER)
    try:
        _yaz(os.path.join(kok, "urunler.json"),
             MUKERRER + [{"id": "urun-c", "baslik": "Baslik C"}])
        _git(kok, "add", "urunler.json")
        sonuc = _kos(kok, "--pre-commit")
        return (sonuc.returncode == 0
                and "NOT onceden-var MUKERRER BASLIK" in sonuc.stdout
                and "ATLANDI" not in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


def _a11():
    """Dogrulanmis cift istisnaya YAZILDIGINDA kapi susar (yargi bir yere coker)."""
    gecici, kok = _baslik_depo(BASLIK_CIFTI, BASLIK_ISTISNASI)
    try:
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode == 0, sonuc
    finally:
        gecici.cleanup()


def _a12():
    """Istisna ID KUMESINE bagli: UCUNCU kayit girince YENIDEN kirmizi yanar."""
    gecici, kok = _baslik_depo(UCUNCU_KAYIT, BASLIK_ISTISNASI)
    try:
        sonuc = _kos(kok, "--pre-commit")
        return (sonuc.returncode != 0
                and "MUKERRER BASLIK" in sonuc.stdout
                and "kaynak-c-parca" in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


def _a13():
    """`idler` alani OLMAYAN istisna GECERSIZDIR — joker istisna YOK (fail-closed)."""
    gecici, kok = _baslik_depo(
        BASLIK_CIFTI,
        [{"baslik": CIFT_BASLIK, "neden": "idler alani YOK — gecersiz olmali"}])
    try:
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode != 0 and "MUKERRER BASLIK" in sonuc.stdout, sonuc
    finally:
        gecici.cleanup()


def _a14():
    """Ilk commit (HEAD YOK) + urunler.json stage'li -> tarama yine KOSAR."""
    gecici, kok = _depo(TEMIZ, commit=False)
    try:
        _yaz(os.path.join(kok, "urunler.json"), MUKERRER)
        _git(kok, "add", "urunler.json")
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode != 0 and "MUKERRER BASLIK" in sonuc.stdout, sonuc
    finally:
        gecici.cleanup()


# A15-A16 — 14 Eki 2026 (BaBa 20:1x): HEAD'de ZATEN duran 14 cgtrader kaynak cifti
# MaCiT'in yalniz yeni urun ekleyen commit'ini kilitledi. Kapi artik commit'in
# YARATTIGI bulguyla bloklar; onceden-var cift gorunur NOT satiri olur.
def _a15():
    """HEAD'de onceden-var KAYNAK cifti + ilgisiz yeni urun -> rc=0 + NOT satiri."""
    gecici, ana, wt = _paylasilan_kaynak_deposu(None, eski_cift=True)
    try:
        sonuc = _kos(wt, "--pre-commit", veri=ana)
        return (sonuc.returncode == 0
                and "NOT onceden-var MUKERRER KAYNAK" in sonuc.stdout
                and "onceden-var 1" in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


def _a16():
    """Yeni kayit HEAD'deki cifte KATILIR (2 -> 3) -> yeni bulgu, rc=1."""
    gecici, kok = _depo(MUKERRER)
    try:
        _yaz(os.path.join(kok, "urunler.json"),
             MUKERRER + [{"id": "urun-c", "baslik": "Ayni Baslik"}])
        _git(kok, "add", "urunler.json")
        sonuc = _kos(kok, "--pre-commit")
        return (sonuc.returncode != 0
                and "MUKERRER BASLIK: Ayni Baslik -> urun-a, urun-b, urun-c" in sonuc.stdout
                and "NOT onceden-var" not in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


IDDIALAR = [
    ("A1 yabanci veri bloklamaz", _a1),
    ("A2 staged mukerrer yakalanir", _a2),
    ("A3 HEAD'e karsi mukerrer yakalanir", _a3),
    ("A4 git okunamiyorsa fail-closed (OLCULEMEDI yesil degil)", _a4),
    ("A5 bayraksiz tam katalog korunur", _a5),
    ("A6 worktree ANA AGACTAKI istisnayi gorur (ayni HEAD = ayni hukum)", _a6),
    ("A7 istisna HICBIR agacta yoksa worktree'de de KIRMIZI (fail-closed)", _a7),
    ("A8 paylasilan istisnanin VARLIGI degil ICERIGI hukum verir", _a8),
    ("A9 urun dosyasina dokunmayan commit TARANMAZ (kapsam on-elemesi)", _a9),
    ("A10 AYNI HEAD, urun dosyasi stage'liyken tarama AYNEN kosar", _a10),
    ("A11 dogrulanmis baslik cifti istisnaya yazilinca susar", _a11),
    ("A12 baslik istisnasi UCUNCU kayda GENISLEMEZ", _a12),
    ("A13 idler'siz baslik istisnasi GECERSIZ (joker yok)", _a13),
    ("A14 ilk commit'te (HEAD yok) tarama kosar", _a14),
    ("A15 HEAD'de onceden-var cift yeni urun commit'ini bloklamaz (NOT satiri)", _a15),
    ("A16 yeni kayit onceden-var cifte katilinca bloklar", _a16),
]

# ── MUTASYON KANITI ───────────────────────────────────────────────────────────
# Her mutant kapinin KOPYASINA bir delik acar; listelenen iddialarin HEPSININ
# KIRMIZI yanmasi SARTTIR. Yanmiyorsa iddia yesili bosuna veriyordur
# ([[test-hatali-davranisi-kutsar]]). Calisma agaci KIRLENMEZ: mutasyon yalniz
# gecici depoya serilen kopyaya uygulanir ve depo is bitince silinir.
ESLESTIRICI = "            if (baslik, frozenset(ilgili_idler)) in baslik_muaf:"
SINIFLAYICI = ("        if head_bulgu is None or (b[0], b[1], tuple(sorted(b[2])))"
               " not in head_bulgu:")
OKUYUCU_GUARDI = ("        if not isinstance(idler, list) or len(idler) < 2:\n"
                  "            continue")

MUTANTLAR = [
    (
        "M1 istisna ID KUMESINI yok sayip yalniz BASLIGA bakarsa",
        [(ESLESTIRICI, "            if any(baslik == b for b, _ in baslik_muaf):")],
        ["A12"],
    ),
    (
        "M2 istisna eslesmesi ALT KUMEYE gevserse",
        [(ESLESTIRICI,
          "            if any(baslik == b and s <= frozenset(ilgili_idler)"
          " for b, s in baslik_muaf):")],
        ["A12"],
    ),
    (
        "M3 kapsam on-elemesi urun dosyasi stage'liyken de elerse",
        [('    durum = _urun_stage_durumu()\n    if durum == "stage-disi":',
          '    durum = _urun_stage_durumu()\n'
          '    if durum in ("stage-disi", "stage"):')],
        ["A2", "A3", "A10", "A12", "A13", "A14"],
    ),
    (
        "M4 OLCULEMEDI hali atlama sayilirsa (fail-open)",
        [('    if r.returncode == 0:\n        return "stage-disi"',
          '    if r.returncode != 1:\n        return "stage-disi"')],
        ["A4"],
    ),
    (
        "M5 pre-commit kolu baslik istisnalarini hic okumazsa",
        [("    baslik_istisnalari = _baslik_istisnalari_oku(istisna_yolu())\n"
          "    urunler, gerekce = _commit_katalogu(durum)",
          "    baslik_istisnalari = set()\n"
          "    urunler, gerekce = _commit_katalogu(durum)")],
        ["A11"],
    ),
    (
        # A13 IKI KATMANLA korunur: (1) okuyucu `idler`siz kaydi ATAR, (2) eslestirici
        # TAM KUME esitligi arar, yani bos kume 2 kayitlik bir bulguya zaten uymaz.
        # Tek katmani delen bir mutant A13'u kirmiziya cevirmez — bu YANLIS BIR
        # BEKLENTIYDI, olculdu ve duzeltildi. Iddianin canli oldugunu ancak IKI
        # katmani birden delen bu mutant gosterir: joker istisna gercekten mumkun
        # olsaydi A13 yesil kalirdi.
        "M6 idler'siz kayit KABUL edilip bos kume JOKER sayilirsa (iki katman)",
        [(OKUYUCU_GUARDI,
          "        if not isinstance(idler, list):\n            idler = []"),
         (ESLESTIRICI,
          "            if any(baslik == b and (not s or s == frozenset(ilgili_idler))"
          " for b, s in baslik_muaf):")],
        ["A13"],
    ),
    (
        "M7 HEAD okunabildikce HER bulgu onceden-var sayilirsa",
        [(SINIFLAYICI, "        if head_bulgu is None:")],
        ["A2", "A3", "A7", "A8", "A16"],
    ),
    (
        # 14 Eki WIP'in ilk hali buydu: id'lerin hepsi HEAD'deyse onceden-var. Mevcut
        # iki kaydin basligini esitleyen commit'i GECIRIR — A2 olcer.
        "M8 siniflama bulgu kumesi yerine id-uyeligine bakarsa",
        [(SINIFLAYICI,
          "        if head_bulgu is None or any(i not in {u.get('id') for u in head}"
          " for i in b[2]):")],
        ["A2"],
    ),
    (
        "M9 HEAD okunamazsa bulgular onceden-var sayilirsa (fail-open)",
        [(SINIFLAYICI,
          "        if head_bulgu is not None and (b[0], b[1], tuple(sorted(b[2])))"
          " not in head_bulgu:")],
        ["A14"],
    ),
]


def _iddialari_kos(secim=None):
    sonuclar = {}
    for ad, sinama in IDDIALAR:
        etiket = ad.split(None, 1)[0]
        if secim is not None and etiket not in secim:
            continue
        try:
            gecti, sonuc = sinama()
        except Exception as hata:                                   # noqa: BLE001
            sonuclar[etiket] = (False, "%s: %s" % (type(hata).__name__, hata), ad, None)
        else:
            sonuclar[etiket] = (gecti, "rc=%d" % sonuc.returncode, ad, sonuc)
    return sonuclar


def _mutasyon_kaniti():
    global MUTASYON
    tum_etiketler = {ad.split(None, 1)[0] for ad, _ in IDDIALAR}
    basarisiz = []
    for mutant_ad, yama, beklenen_kirmizilar in MUTANTLAR:
        bilinmeyen = [e for e in beklenen_kirmizilar if e not in tum_etiketler]
        if bilinmeyen:
            basarisiz.append("%s -> bilinmeyen iddia etiketi %s" % (mutant_ad, bilinmeyen))
            continue
        MUTASYON = yama
        try:
            sonuclar = _iddialari_kos(set(beklenen_kirmizilar))
        except AssertionError as hata:
            MUTASYON = None
            basarisiz.append("%s -> %s" % (mutant_ad, hata))
            print("KALDI  %s (mutasyon uygulanamadi)" % mutant_ad)
            continue
        finally:
            MUTASYON = None
        hayatta = [e for e in beklenen_kirmizilar if sonuclar[e][0]]
        if hayatta:
            basarisiz.append("%s -> %s HALA YESIL (mutant hayatta)"
                             % (mutant_ad, ", ".join(sorted(hayatta))))
            print("KALDI  %s — hayatta kalan: %s" % (mutant_ad, ", ".join(sorted(hayatta))))
        else:
            print("OLDU   %s (kirmizi yanan: %s)"
                  % (mutant_ad, ", ".join(sorted(beklenen_kirmizilar))))
    return basarisiz


def main():
    sonuclar = _iddialari_kos()
    gecen = 0
    for ad, sinama in IDDIALAR:
        etiket = ad.split(None, 1)[0]
        gecti, ayrinti, _ad, sonuc = sonuclar[etiket]
        print("%s %s (%s)" % ("GECTI" if gecti else "KALDI", ad, ayrinti))
        if not gecti and sonuc is not None and sonuc.stdout.strip():
            print(sonuc.stdout.strip())
        gecen += int(gecti)
    toplam = len(IDDIALAR)
    print("SONUC: %d/%d iddia GECTI" % (gecen, toplam))

    print("\n-- MUTASYON KANITI (kapinin KOPYASINA delik acilir) --")
    mutant_hatalari = _mutasyon_kaniti()
    print("MUTASYON: %d/%d mutant OLDU"
          % (len(MUTANTLAR) - len(mutant_hatalari), len(MUTANTLAR)))
    for satir in mutant_hatalari:
        print("  !! %s" % satir)

    return 0 if (gecen == toplam and not mutant_hatalari) else 1


if __name__ == "__main__":
    sys.exit(main())
