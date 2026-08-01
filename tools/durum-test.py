#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DURUM PANOSU KABUL TESTLERI — tools/paket-durum-panosu.md'deki 5 madde.

    python3 tools/durum-test.py

Testler GECICI repo kurar (tempfile + git init) — GERCEK repoda dal acilmaz/silinmez
(guard katmani + eszamanli oturumlar bozulmasin). Tek istisna madde 5: gercek repoda
durum.py'yi SALT-OKUNUR kosar ve `git status --porcelain`in oncesi/sonrasi ayni
kaldigini kanitlar.

  1. Ucu main'de olan dal        -> "icerigi main'de" sinifi (ucu-main-de)
  2. SQUASH-MERGE edilmis dal    -> yine "icerigi main'de"  <-- ASIL RISK
     `git branch --merged` bunu KACIRIR; test bunu ayrica kanitlar (2b).
  3. Gercekten bitmemis dal      -> "devam ediyor"
  4. Aktif worktree'si olan dal  -> "artik dal" listesine DUSMEZ
  5. durum.py gercek repoda exit 0 + repo durumunu DEGISTIRMIYOR
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import durum  # noqa: E402

SONUC = []


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti))
    print("  %s TEST %s — %s%s" % ("✅" if gecti else "❌", no, ad,
                                   (" | " + detay) if detay else ""), flush=True)


def kos(repo, *args):
    p = subprocess.run(["git", "-C", repo] + list(args),
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("git %s -> %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout.strip()


def yaz(repo, ad, icerik):
    with open(os.path.join(repo, ad), "w") as f:
        f.write(icerik)


def sahne_kur(tmp):
    """Dort dalli gecici repo: ucu-merged, squash-merged, bitmemis, worktree'li."""
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    kos(repo, "init", "-q", "-b", "main")
    kos(repo, "config", "user.email", "test@example.invalid")
    kos(repo, "config", "user.name", "durum-test")
    yaz(repo, "a.txt", "taban\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "taban")

    # (1) ucu main'de olan dal: normal (fast-forward olmayan) merge
    kos(repo, "checkout", "-q", "-b", "dal-uc-merged")
    yaz(repo, "b.txt", "uc\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "uc dal isi")
    kos(repo, "checkout", "-q", "main")
    kos(repo, "merge", "-q", "--no-ff", "-m", "merge: uc", "dal-uc-merged")

    # (2) squash-merge: dalda UC commit, main'de TEK commit
    #     -> dal ucu main'in atasi DEGIL, tek tek patch-id'ler de TUTMAZ.
    kos(repo, "checkout", "-q", "-b", "dal-squash")
    yaz(repo, "c.txt", "birinci\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "squash isi 1")
    yaz(repo, "c.txt", "birinci\nikinci\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "squash isi 2")
    yaz(repo, "d.txt", "ucuncu\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "squash isi 3")
    kos(repo, "checkout", "-q", "main")
    kos(repo, "merge", "-q", "--squash", "dal-squash")
    kos(repo, "commit", "-q", "-m", "squash merge: dal-squash (3 commit tek committe)")

    # main baska bir isle ilerlesin (gercek hayat: merge sonrasi main durmuyor)
    yaz(repo, "e.txt", "main devam\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "main: alakasiz is")

    # (3) gercekten bitmemis dal
    kos(repo, "checkout", "-q", "-b", "dal-devam", "main")
    yaz(repo, "f.txt", "yarim is\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "yarim is")
    kos(repo, "checkout", "-q", "main")

    # (4) worktree'si olan, icerigi main'de olan dal (artik listesine DUSMEMELI)
    kos(repo, "checkout", "-q", "-b", "dal-worktreeli")
    yaz(repo, "g.txt", "wt\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "wt isi")
    kos(repo, "checkout", "-q", "main")
    kos(repo, "merge", "-q", "--no-ff", "-m", "merge: wt", "dal-worktreeli")
    kos(repo, "worktree", "add", "-q", os.path.join(tmp, "wt"), "dal-worktreeli")
    return repo


def test_1_2_3(repo):
    s1 = durum.dal_sinifi(repo, "dal-uc-merged")
    kayit(1, "ucu main'de olan dal -> icerigi main'de",
          s1 in ("ucu-main-de", "icerigi-main-de"), "sinif=%s" % s1)

    s2 = durum.dal_sinifi(repo, "dal-squash")
    kayit(2, "SQUASH-MERGE edilmis dal -> icerigi main'de",
          s2 in ("ucu-main-de", "icerigi-main-de"), "sinif=%s" % s2)

    # 2b: `git branch --merged` bu dali KACIRIYOR mu? Kacirmiyorsa test 2 anlamsiz
    #     olur (tuzak yeniden uretilememis demektir) -> bilerek dogruluyoruz.
    merged = kos(repo, "branch", "--merged", "main", "--format=%(refname:short)").splitlines()
    kayit("2b", "tuzak gercek: `git branch --merged` squash dali KACIRIYOR",
          "dal-squash" not in merged, "--merged listesi=%s" % merged)

    s3 = durum.dal_sinifi(repo, "dal-devam")
    kayit(3, "bitmemis dal -> devam ediyor", s3 == "devam", "sinif=%s" % s3)


def test_4(repo, tmp):
    wt_dallari = set(w["dal"] for w in durum.worktreeler(repo) if w["dal"])
    dallar = [d for d in durum.yerel_dallar(repo) if d != "main"]
    artik = [d for d in dallar
             if durum.dal_sinifi(repo, d) != "devam" and d not in wt_dallari]
    kayit(4, "aktif worktree'li dal ARTIK listesine dusmuyor",
          "dal-worktreeli" not in artik and "dal-worktreeli" in wt_dallari,
          "artik=%s" % artik)


def test_5():
    once = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                          capture_output=True, text=True).stdout
    p = subprocess.run([sys.executable, os.path.join(TOOLS, "durum.py")],
                       capture_output=True, text=True)
    sonra = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                           capture_output=True, text=True).stdout
    kayit(5, "gercek repoda exit 0 + repo durumu DEGISMEDI",
          p.returncode == 0 and once == sonra,
          "exit=%d, durum ayni=%s" % (p.returncode, once == sonra))
    if p.returncode != 0:
        print(p.stderr[:600])
    return p.stdout


def mesru_kelime_yolu(s):
    """"uzun-anahtar" muafiyeti: `/` ile ayrilmis DUZ KELIME dizisi mi?

    KURULUS VAKASI (1 Agu 2026, CI run 30691723803, is `serit-b`, headSha 1580c654):
    6c KIRMIZI yandi -> `yakalanan=['uzun-anahtar']`. Yakalanan dizgi bir SIR DEGIL,
    panonun `1) AKTIF WORKTREE'LER` bolumunde KISALTILMADAN basilan bir GIT COMMIT
    BASLIGIYDI (kaynak: tools/durum.py :: main(), `--format=%cr — %h %s`; 2) bolumu
    konuyu [:56] kirpar, 1) bolumu KIRPMAZ). 69 karakterlik, tamami BUYUK HARF +
    `/` olan bir marin kategori listesi ("TRIM/MANIFOLD/CONTA/..." gibi). Desen
    base64 alfabesini kullandigi ve `/` o alfabede oldugu icin, egik cizgiyle
    ayrilmis kelime dizileri ANAHTAR sanildi. Deger commit gecmisinde ZATEN
    PUBLIC'tir; sir/kimlik degildir.

    ⚠️ MUAFIYETIN SINIRI — KARA LISTE DEGIL, BEYAZ LISTE. Desen DARALTILMADI
    (base64 alfabesi yerinde duruyor); yalnizca su IKI sartin IKISINI DE saglayan
    vuruslar muaf sayilir:
      (1) `/` ile ayrilan HER segment YALNIZCA ASCII HARF, ve 2..20 harf uzunlugunda
          (rakam/`+` iceren ya da 20'den uzun ayracsiz govde = ANAHTAR suphesi,
          muaf DEGIL — base64/base32 anahtarlari pratikte her ikisini de tasir),
      (2) HER segment TEK BICIMDE: ya tamami buyuk, ya tamami kucuk, ya Bas-harfli
          (segment ICINDE karisik buyuk/kucuk = base64 imzasi, muaf DEGIL).
    Iki sart da _muafiyet_fiksturleri()/--ic-nobetci mutasyonlariyla capalanmistir:
    her sarti tek tek gevseten mutant, sir-benzeri bir fiksturu sizdirir -> KIRMIZI.
    """
    if not isinstance(s, str) or "/" not in s:
        return False
    for p in s.split("/"):
        # (1) yalnizca harf + makul kelime boyu
        if not p.isascii() or not p.isalpha() or not (2 <= len(p) <= 20):
            return False
        # (2) segment ici bicim tekdüze (ALLCAPS / alllower / Basharfli)
        if not (p.isupper() or p.islower() or (p[0].isupper() and p[1:].islower())):
            return False
    return True


# Muafiyet fiksturleri. SIR DEGIL — hepsi bu dosyada uretilmis UYDURMA dizgilerdir.
#   MUAF_OLMALI : gercek vaka(lar) — muafiyet OLU olmasin diye.
#   SIZMAMALI   : sir-benzeri sekiller — muafiyet GENIS olmasin diye. Her kalemin
#                 yanindaki not, onu hangi SARTIN durdurdugunu soyler.
_MUAF_OLMALI = [
    # kurulus vakasinin sekli (gercek commit basligindan; public)
    "TRIM/MANIFOLD/CONTA/HORTUM/KORUK/KAPLIN/DISTRIBUTOR/TANK/YOKE/STARTER",
    # ayni sekil kucuk harf ve Bas-harfli varyantlariyla
    "trim/manifold/conta/hortum/koruk/kaplin/distributor/tank/yoke/starter",
    "Trim/Manifold/Conta/Hortum/Koruk/Kaplin/Distributor/Tank/Yoke/Starter",
]
_SIZMAMALI = [
    # sart (1) durdurur: ayracsiz 45 harflik tek govde (base32 anahtar sekli)
    "ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRS",
    # sart (1) durdurur: segmentlerde RAKAM var (base64/anahtar govdesi)
    "ABC123DEF456/GHI789JKL012/MNO345PQR678/STU901VWX234",
    # sart (2) durdurur: segment ICINDE karisik buyuk/kucuk (base64 imzasi)
    "wJalrXUtnFEMIK/bPxRfiCYzEXA/mPLEkeyQwErTy/AbCdEfGhIj",
    # sart (1) durdurur: `+` ve `/` karisik ham base64 govdesi
    "aGVsbG9+/Xb3JsZFRoaXNJc0FGYWtlU2VjcmV0VmFsdWUxMjM0NQ",
]


def _muafiyet_fiksturleri(fonk=None):
    """Muafiyet fonksiyonunu fiksturlerle olcer. Doner: bozuk kalemlerin listesi."""
    f = fonk or mesru_kelime_yolu
    bozuk = []
    for s in _MUAF_OLMALI:
        if not f(s):
            bozuk.append("muaf-olmali-degil<%d kr>" % len(s))
    for s in _SIZMAMALI:
        if f(s):
            bozuk.append("SIZDI<%d kr>" % len(s))
    return bozuk


# --ic-nobetci MUTASYONLARI: muafiyetin HER sartini tek tek gevsetir. Gevseyen
# muafiyet sir-benzeri bir fiksturu gecirirse mutant OLDU (=KIRMIZI) demektir.
# Olu iddia kabul edilmez: bir sart mutasyona ragmen YESIL kalirsa, o sart
# TASIYICI DEGILDIR ve muafiyet o kadar dar degildir -> ic nobetci kirmizi yanar.
def _mutant_hepsini_gecir(s):
    return isinstance(s, str) and "/" in s          # M1: sartlarin ikisi de silindi


def _mutant_uzunluk_tavani_yok(s):
    if not isinstance(s, str):
        return False
    for p in s.split("/"):                          # M2: 2..20 tavani kalkti
        if not p.isascii() or not p.isalpha():
            return False
        if not (p.isupper() or p.islower() or (p[0].isupper() and p[1:].islower())):
            return False
    return True


def _mutant_rakam_serbest(s):
    if not isinstance(s, str) or "/" not in s:
        return False
    for p in s.split("/"):                          # M3: isalpha -> isalnum
        if not p.isascii() or not p.isalnum() or not (2 <= len(p) <= 20):
            return False
        if not (p.isupper() or p.islower() or (p[0].isupper() and p[1:].islower())):
            return False
    return True


def _mutant_bicim_sarti_yok(s):
    if not isinstance(s, str) or "/" not in s:
        return False
    for p in s.split("/"):                          # M4: segment ici bicim sarti kalkti
        if not p.isascii() or not p.isalpha() or not (2 <= len(p) <= 20):
            return False
    return True


def ic_nobetci():
    """`python3 tools/durum-test.py --ic-nobetci` — muafiyetin KENDI capasi."""
    print("\n6c MUAFIYET IC NOBETCISI (mutasyon) — sir-benzeri dizgi sizarsa mutant OLUR\n")
    sonuc = []

    bozuk = _muafiyet_fiksturleri()
    sonuc.append(("F0 gercek muafiyet fiksturleri (muaf-olmali + sizmamali)", not bozuk,
                  "bozuk=%s" % bozuk))

    mutantlar = [
        ("M1 iki sart da silindi (`/` varsa muaf)", _mutant_hepsini_gecir),
        ("M2 segment uzunluk tavani (2..20) silindi", _mutant_uzunluk_tavani_yok),
        ("M3 harf sarti gevsetildi (isalpha -> isalnum)", _mutant_rakam_serbest),
        ("M4 segment ici bicim (ALLCAPS/alllower/Bas) sarti silindi", _mutant_bicim_sarti_yok),
    ]
    for ad, m in mutantlar:
        sizan = [s for s in _SIZMAMALI if m(s)]
        sonuc.append((ad + " -> OLMELI", bool(sizan),
                      "sizan fikstur sayisi=%d" % len(sizan)))

    for ad, gecti, detay in sonuc:
        print("  %s %s | %s" % ("✅" if gecti else "❌", ad, detay))
    kirmizi = [a for a, g, _ in sonuc if not g]
    print("\n%s  %d/%d\n" % ("✅ HEPSI YESIL" if not kirmizi else "❌ KIRMIZI",
                             len(sonuc) - len(kirmizi), len(sonuc)))
    return 1 if kirmizi else 0


def test_sizinti(cikti):
    """Repo PUBLIC + cikti yerelde okunuyor -> uc ayri sizinti kapisi.

    NOT: "cikti icinde 'secret' kelimesi geciyor mu" diye BAKMIYORUZ — ilk
    surumde oyleydi ve YANLIS ALARM verdi: gercek bir commit basligi
    ("...yukle.py artik secret...") kelimeyi masumca iceriyordu. Kelime degil
    SIR DEGERI ve SIR OKUMA aranir.
    """
    # (a) statik: durum.py sir dosyalarina hic dokunmuyor
    with open(os.path.join(TOOLS, "durum.py")) as f:
        kaynak = f.read()
    dokunulan = [ad for ad in (".r2-credentials", ".urun-kaynaklari", ".env",
                               "wrangler.toml", "credentials")
                 if ad in kaynak]
    kayit("6a", "durum.py sir dosyasi OKUMUYOR (statik)", not dokunulan,
          "gecen ad=%s" % dokunulan)

    # (b) sir DEGERLERI ciktida gecmiyor (deger asla basilmaz, sadece sayi)
    sirlar = []
    # Sir dosyalari gitignore'da: worktree'de DEGIL, ANA repo kokunde durur.
    # (Ilk surum ROOT'a bakti -> 0 aday buldu -> test BOSA gecti. Bos gecen test
    #  test degildir; ana repo koku alinir.)
    sir_kok = durum.ana_repo(ROOT)
    for ad in (".r2-credentials.json", ".urun-kaynaklari.json"):
        yol = os.path.join(sir_kok, ad)
        if not os.path.isfile(yol):
            continue
        try:
            with open(yol, errors="replace") as f:
                veri = json.load(f)
        except (ValueError, OSError):
            continue
        yigin = [veri]
        while yigin:
            o = yigin.pop()
            if isinstance(o, dict):
                yigin.extend(o.values())
            elif isinstance(o, list):
                yigin.extend(o)
            elif isinstance(o, str) and len(o) >= 12:
                sirlar.append(o)
    sizan = sum(1 for s in sirlar if s in cikti)
    kayit("6b", "sir DEGERI ciktida yok (deger basilmaz)", sizan == 0,
          "%d aday deger tarandi, %d sizinti" % (len(sirlar), sizan))

    # (c) kimlik-bicimli dizgi (IBAN / uzun anahtar / telefon) ciktida yok
    desenler = {
        "IBAN": r"TR\d{24}",
        "uzun-anahtar": r"\b[A-Za-z0-9/+]{40,}\b",
        "telefon": r"\b(?:90|\+90)?5\d{9}\b",
    }
    yakalanan = []
    for ad, d in desenler.items():
        vurus = [m.group(0) for m in re.finditer(d, cikti)]
        if ad == "uzun-anahtar":
            vurus = [v for v in vurus if not mesru_kelime_yolu(v)]
        if vurus:
            yakalanan.append(ad)
    # OLU MUAFIYET NOBETI: muafiyet fonksiyonu birisi tarafindan korlestirilirse
    # (or. `return True`) yukaridaki filtre sessizce her seyi gecirirdi ve 6c
    # SONSUZA DEK yesil yanardi. Fiksturler bunu AYNI kosumda kirmizi yakar.
    fikstur = _muafiyet_fiksturleri()
    kayit("6c", "ciktida kimlik-bicimli dizgi yok",
          not yakalanan and not fikstur,
          "yakalanan=%s%s" % (yakalanan,
                              (" | MUAFIYET FIKSTURU BOZUK: %s" % fikstur) if fikstur else ""))


def main():
    if "--ic-nobetci" in sys.argv:
        return ic_nobetci()
    print("\nDURUM PANOSU KABUL TESTLERI (gecici repo — gercek repoya dokunulmaz)\n")
    tmp = tempfile.mkdtemp(prefix="durum-test-")
    try:
        repo = sahne_kur(tmp)
        test_1_2_3(repo)
        test_4(repo, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    cikti = test_5()
    test_sizinti(cikti)

    basarisiz = [s for s in SONUC if not s[2]]
    print("\n%s  %d/%d test gecti\n"
          % ("✅ HEPSI YESIL" if not basarisiz else "❌ KIRMIZI",
             len(SONUC) - len(basarisiz), len(SONUC)))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
