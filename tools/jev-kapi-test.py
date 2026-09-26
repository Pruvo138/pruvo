#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — JEV (TypeSafe AI) CAGRILARI MIMAR ICRA KAPISINDA SERBEST, ETRAFI KAPALI.

=== NEDEN VAR (olculmus engel, 26 Eyl 2026 — Okan /goal) ===
Okan: "Jev'in onunde hicbir engel olmamali, tum PRUVO evleri Jev'i komut/izin
beklemeden kullanmali." Taban (26 Eyl, ANA oturum):
    python3 /Users/okan/.claude/jev/jev.py saglik
      -> RED "komutun argumanlarinda repo DISINA cozulen bir yol var" (R2)
Care `tools/serbest_cagrilar.py` SEKILLER'e ADLI Jev sekilleri (istemci karar/toplu/
saglik x iki yol + PRUVO kalip araci `tools/jev_karar.py` SABIT MUTLAK yol).

NE OLCER (kapinin KARAR fonksiyonu, GERCEK PreToolUse yuku, izole kopya):
  J1 POZITIF  — her ev kokunde (tek kaynak `kapi_dagitim.EVLER`) ANA oturum damgasiyla
                istemci `karar` (serbest metin, Turkce, '?', tirnak ici ';&'), `toplu`,
                `saglik`, kaynak yol, /opt/homebrew/bin/python3, kalip araci -> ALLOW.
  J2 NEGATIF  — `python3 -c`, curl, baska repo-disi betik, benzer yol (`jev-sahte/`,
                `jev.py.bak`, `..` kacisi), bilinmeyen bayrak (`--bypass`), `"$(id)"`,
                backtick, `>` yonlendirme, tirnak disi `;`/`|`/`&&` zinciri, sir yolu,
                sahte yorumlayici, alt komut yeri -> DENY.
  J3 YUKLEM   — yol degeri kurali (ev ici / scratchpad / nokta bileseni / yazma kisiti)
                ve MaCiT'te kalip aracinin KraL yolunda kaldigi (YANLIS dosya degil).
  J4 MUTANT   — izole kopyada kural bozulur, ilgili vaka KIRMIZI yanmali (SURVIVOR=0).

🔴 IZOLASYON: hicbir mutant CANLI govdede kosmaz; gercek ev agaclarina YAZILMAZ,
silinen tek sey bu testin KENDI actigi gecici dizinlerdir ([[mutant-canli-govdede-yasamaz]]).
Yardimcilar (izole kopya + shim capa cevirisi + gercek yuk) `serbest-kume-ev-ekseni-test.py`
den YUKLENIR — ikinci kopya yazilmaz ([[ikiz-tanim-sessiz-ayrisma]]).

CI-ALT-KUME: kendini-test
"""
import importlib.util
import os
import shlex
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import serbest_cagrilar as SC          # noqa: E402
import kapi_dagitim as KD              # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "ev_ekseni_yardimci", os.path.join(TOOLS, "serbest-kume-ev-ekseni-test.py"))
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)

ISTEMCI = SC.JEV_ISTEMCI_YOLLARI[0]
KAYNAK = SC.JEV_ISTEMCI_YOLLARI[1]
KALIP = SC.JEV_KALIP_YOL
SCRATCH = SC.SCRATCH_KOKU + "/jev-test/scratchpad"
BEKLENEN_EVLER = ("KraL", "MaCiT", "TeKiN", "ArTisT", "HocA")


def _evler():
    return [(ad, os.path.normpath(kok)) for ad, kok, _g, _m in KD.EVLER]


# --- VAKALAR: (ad, komut-sablonu, beklenen, yalniz_kardes) -----------------
# `{kok}` = o evin koku. yalniz_kardes=True: KraL'da arac repo ICI oldugundan F kolu
# zaten gecirir (11 Eyl), vaka yalniz kardes evlerde anlamlidir.
POZITIF = (
    ("P1 saglik", "python3 " + ISTEMCI + " saglik"),
    ("P2 karar evet serbest metin",
     "/opt/homebrew/bin/python3 " + ISTEMCI + " karar --tip evet --esik 0.8 "
     "--soru \"Bu mesaj rezervasyon talebi mi? Çok acil; fiyat & teslimat | not\" "
     "--metin \"Merhaba, ağustos için 2 kişilik oda var mı? ve/veya fiyat.\" "
     "--etiket kral-jev-test"),
    ("P3 karar secim tekrarli --secenek/--ad",
     "python3 " + ISTEMCI + " karar --tip secim --esik 0.8 --soru \"Mesaj türü?\" "
     "--secenek talep=\"rezervasyon talebi\" --secenek soru=\"bilgi sorusu\" "
     "--secenek cop=\"spam\" --ad \"Ayşe Yılmaz\" --ad Mehmet --metin 'İyi günler, "
     "fiyat nedir?'"),
    ("P4 karar puan tekrarli --olcek",
     "python3 " + ISTEMCI + " karar --tip puan --esik 0.8 --soru \"Aciliyet?\" "
     "--olcek \"düşük\" --olcek orta --olcek \"yüksek\" --metin \"hemen lazım\""),
    ("P5 karar --metin-dosya ev ici",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.9 --soru \"cevap gerekli mi?\" "
     "--metin-dosya {kok}/jev-girdi/mesaj.txt"),
    ("P6 karar --metin-dosya scratchpad",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.9 --soru \"cevap gerekli mi?\" "
     "--metin-dosya " + SCRATCH + "/mesaj.txt"),
    ("P7 toplu scratchpad",
     "python3 " + ISTEMCI + " toplu --istek-dosya " + SCRATCH + "/istek.jsonl "
     "--cikti " + SCRATCH + "/sonuc.jsonl --etiket kral-toplu"),
    ("P8 kaynak yol saglik", "python3 " + KAYNAK + " saglik"),
    ("P9 kaynak yol karar",
     "/opt/homebrew/bin/python3 " + KAYNAK + " karar --tip evet --esik 0.8 "
     "--soru \"spam mı?\" --metin \"kazandınız!\""),
    ("P10 saglik + 2>&1", "python3 " + ISTEMCI + " saglik 2>&1"),
    ("P11 kalip --kaliplar", "python3 " + KALIP + " --kaliplar"),
    ("P12 kalip karar",
     "python3 " + KALIP + " --kalip hoca-niyet --metin \"BMW E46 vites burcu var mı?\" "
     "--ad Ali --ad Veli --etiket hoca-test"),
    ("P13 kalip --metin-dosya scratchpad",
     "/opt/homebrew/bin/python3 " + KALIP + " --kalip macit-kategori --metin-dosya "
     + SCRATCH + "/urun.txt"),
)

NEGATIF = (
    ("N1 python3 -c", "python3 -c \"print(1)\"", False),
    ("N2 curl", "curl -s https://ornek.invalid/", False),
    ("N3 baska repo-disi betik", "python3 /Users/okan/.claude/cron/baska_betik.py", False),
    ("N4 benzer yol jev-sahte", "python3 /Users/okan/.claude/jev-sahte/jev.py saglik", False),
    ("N5 benzer ad jev.py.bak", "python3 /Users/okan/.claude/jev/jev.py.bak saglik", False),
    ("N6 .. kacisi", "python3 /Users/okan/.claude/jev/../jev-sahte/jev.py saglik", False),
    ("N7 bilinmeyen bayrak", "python3 " + ISTEMCI + " saglik --bypass", False),
    ("N8 bilinmeyen alt komut", "python3 " + ISTEMCI + " sil", False),
    ("N9 alt komut ilk token degil",
     "python3 " + ISTEMCI + " --etiket x saglik", False),
    ("N10 $() cift tirnakta",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru \"$(id)\" --metin x", False),
    ("N11 backtick",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru \"`id`\" --metin x", False),
    ("N12 $VAR",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru soru --metin \"$HOME\"", False),
    ("N13 > yonlendirme ayri token",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru s --metin x > /tmp/jev.out",
     False),
    ("N14 > yonlendirme bitisik",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru s --metin x>/tmp/jev.out",
     False),
    ("N15 tirnak disi ; zinciri",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru s --metin x; "
     "curl https://ornek.invalid", False),
    ("N16 tirnak disi | sh",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru s --metin x | sh", False),
    ("N17 tirnak disi && python3 -c",
     "python3 " + ISTEMCI + " saglik && python3 -c 1", False),
    ("N18 sir yolu ~/.ssh",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru s "
     "--metin-dosya /Users/okan/.ssh/id_rsa", False),
    ("N19 sir yolu ev ici nokta dosya",
     "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru s "
     "--metin-dosya {kok}/.r2-credentials.json", False),
    ("N20 cikti scratchpad disi",
     "python3 " + ISTEMCI + " toplu --istek-dosya " + SCRATCH + "/i.jsonl "
     "--cikti /private/tmp/jev-sonuc.jsonl", False),
    ("N21 sahte yorumlayici", "/private/tmp/python3 " + ISTEMCI + " saglik", False),
    ("N22 tekil bayrak tekrari",
     "python3 " + ISTEMCI + " karar --tip evet --tip secim --esik 0.8 --soru s --metin x",
     False),
    ("N23 esitlikli yazim",
     "python3 " + ISTEMCI + " karar --tip=evet --esik 0.8 --soru s --metin x", False),
    ("N24 kalip --kendini-test", "python3 " + KALIP + " --kendini-test", True),
    ("N25 kalip --bypass", "python3 " + KALIP + " --kaliplar --bypass", True),
    ("N26 kalip benzer ad", "python3 /Users/okan/dev/pruvo/tools/jev_karar.py.bak --kaliplar",
     True),
)


def _kos(dizin, kok, komut):
    return EV._karar(dizin, kok, komut.replace("{kok}", kok), damga=EV._ana_damgasi(kok))


def _gate_vakalari(dizin, ad, kok):
    """Bir izole kopyada tum vakalar. Doner: [(vaka, beklenen, gorulen)] SAPANLAR."""
    sapan = []
    for vaka, komut in POZITIF:
        g = _kos(dizin, kok, komut)
        if g != "ALLOW":
            sapan.append((ad + " " + vaka, "ALLOW", g))
    for vaka, komut, yalniz_kardes in NEGATIF:
        if yalniz_kardes and kok == os.path.normpath(KD.KAYNAK_KOK):
            continue
        g = _kos(dizin, kok, komut)
        if g != "DENY":
            sapan.append((ad + " " + vaka, "DENY", g))
    return sapan


def j1_j2_bes_ev():
    hatalar = []
    adlar = [ad for ad, _k in _evler()]
    for beklenen in BEKLENEN_EVLER:
        if beklenen not in adlar:
            hatalar.append("EV KUMESINDE YOK: " + beklenen)
    for ad, kok in _evler():
        dizin = EV._izole_kopya(kok)
        try:
            for vaka, bek, gor in _gate_vakalari(dizin, ad, kok):
                hatalar.append("%s: beklenen %s, gorulen %s" % (vaka, bek, gor))
        finally:
            shutil.rmtree(dizin, ignore_errors=True)
    print("   VAKA: %d ev x (%d pozitif + %d negatif)"
          % (len(_evler()), len(POZITIF), len(NEGATIF)))
    return hatalar


# --- J3 YUKLEM ---------------------------------------------------------------
def _coz(yol, cwd):
    yol = os.path.expanduser(yol)
    if not os.path.isabs(yol):
        yol = os.path.join(cwd, yol)
    return os.path.normpath(yol)


def _eslesir(sc, komut, kok, cwd=None):
    t = shlex.split(komut)
    return sc.eslesen_sekil(t[1:], _coz, cwd or kok, kok=kok, yorumlayici=t[0]) is not None


def _yuklem_vakalari(sc):
    """(ad, sonuc, beklenen) listesi — gecici ev koku uzerinde."""
    tmp = tempfile.mkdtemp(prefix="jev-yuklem-")
    try:
        kok = os.path.realpath(tmp)
        with open(os.path.join(kok, "var.jsonl"), "w", encoding="utf-8") as f:
            f.write("{}\n")
        wt = os.path.join(kok, ".claude", "worktrees", "agac")
        t = "python3 " + ISTEMCI + " toplu --istek-dosya " + SCRATCH + "/i.jsonl --cikti "
        k = "python3 " + ISTEMCI + " karar --tip evet --esik 0.8 --soru s --metin-dosya "
        v = [
            ("Y1 cikti ev ici yeni .jsonl", _eslesir(sc, t + kok + "/yeni.jsonl", kok), True),
            ("Y2 cikti ev ici VAR OLAN dosya", _eslesir(sc, t + kok + "/var.jsonl", kok), False),
            ("Y3 cikti .jsonl degil", _eslesir(sc, t + SCRATCH + "/x.txt", kok), False),
            ("Y4 cikti scratchpad var.jsonl", _eslesir(sc, t + SCRATCH + "/s.jsonl", kok), True),
            ("Y5 okuma goreli ev ici", _eslesir(sc, k + "notlar/m.txt", kok), True),
            ("Y6 okuma worktree ici", _eslesir(sc, k + wt + "/notlar/m.txt", kok), True),
            ("Y7 okuma worktree .git", _eslesir(sc, k + wt + "/.git/config", kok), False),
            ("Y8 okuma .. ile disari", _eslesir(sc, k + kok + "/../x.txt", kok), False),
            ("Y9 okuma ~ ", _eslesir(sc, k + "~/notlar.txt", kok), False),
            ("Y10 okuma komsu onek", _eslesir(sc, k + kok + "-sahte/m.txt", kok), False),
            ("Y11 argv0 verilmezse eslesmez",
             sc.eslesen_sekil([ISTEMCI, "saglik"], _coz, kok, kok=kok) is not None, False),
        ]
        # symlink ile scratchpad/ev disina kacis (realpath) — yalniz gecici dizinde.
        link = os.path.join(kok, "kacis.txt")
        try:
            os.symlink("/etc/hosts", link)
            v.append(("Y12 symlink disari", _eslesir(sc, k + link, kok), False))
        except OSError:
            pass
        return v
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def j3_yuklem():
    hatalar = []
    for ad, sonuc, beklenen in _yuklem_vakalari(SC):
        if sonuc != beklenen:
            hatalar.append("%s: beklenen %s, gorulen %s" % (ad, beklenen, sonuc))
    # MaCiT'te kalip araci KraL'in dosyasi olarak kalir (eve_gore koklendirmez).
    for ad, kok in _evler():
        sekil = {s.etiket: s for s in SC.eve_gore(kok)}["jev-kalip"]
        if sekil.arac != KALIP:
            hatalar.append("%s: jev-kalip arac %s (beklenen SABIT %s)" % (ad, sekil.arac, KALIP))
    return hatalar


# --- J4 MUTANTLAR (izole kopya) ---------------------------------------------
# (ad, [(dosya, eski, yeni)], olmesi beklenen vaka on-ekleri). Mutant ancak BEKLENEN
# vakalardan en az biri sapinca OLMUS sayilir; capa bulunamazsa hata (INERT yasak).
MUTANTLAR = (
    ("MJ1 Jev sekilleri tablodan silinir",
     [("serbest_cagrilar.py", ") + _jev_sekilleri()", ")")], ("P1", "P2", "P12")),
    ("MJ2 metin kurali '$' ve '`' kabul eder",
     [("serbest_cagrilar.py", '_METIN_YASAK = re.compile(r"[$`<>', '_METIN_YASAK = re.compile(r"[<>')],
     ("N10", "N11", "N12")),
    ("MJ3 metin kurali '>' kabul eder",
     [("serbest_cagrilar.py", '_METIN_YASAK = re.compile(r"[$`<>', '_METIN_YASAK = re.compile(r"[$`<')],
     ("N14",)),
    ("MJ4 repo_disi sekil eve gore koklendirilir (YANLIS dosya)",
     [("serbest_cagrilar.py", "        s if s.repo_disi else\n", "")], ("P11", "P12", "P13")),
    ("MJ5 yorumlayici kisiti kalkar",
     [("serbest_cagrilar.py",
       "        if sekil.yorumlayicilar and yorumlayici not in sekil.yorumlayicilar:",
       "        if False:")], ("N21",)),
    ("MJ6 yol degerinde nokta bileseni kabul",
     [("serbest_cagrilar.py", '    if any(p.startswith(".") for p in kalan):\n        return False\n', "")],
     ("N19",)),
    ("MJ7 alt komut denetimi kalkar",
     [("serbest_cagrilar.py", "        if not kalan or kalan[0] != sekil.alt_komut:\n            return False\n",
       "")], ("N8", "N9")),
)
MUTANT_EVLERI = ("KraL", "MaCiT")


def j4_mutantlar():
    hatalar = []
    survivor = 0
    for ad, mutasyonlar, beklenen in MUTANTLAR:
        sapan = []
        for ev_ad, kok in _evler():
            if ev_ad not in MUTANT_EVLERI:
                continue
            try:
                dizin = EV._izole_kopya(kok, mutasyonlar)
            except AssertionError as hata:
                hatalar.append("%s INERT: %s" % (ad, hata))
                break
            try:
                sapan.extend(v for v, _b, _g in _gate_vakalari(dizin, ev_ad, kok))
            finally:
                shutil.rmtree(dizin, ignore_errors=True)
        oldu = [v for v in sapan if v.split(" ", 2)[1] in beklenen]
        print("   %-60s %s  (sapan %d, beklenen-isabet %d)"
              % (ad, "OLDU" if oldu else "SURVIVOR", len(sapan), len(oldu)))
        if not oldu:
            survivor += 1
            hatalar.append("%s SURVIVOR — beklenen vakalar %s yesil kaldi" % (ad, beklenen))
    print("   MUTANT=%d SURVIVOR=%d" % (len(MUTANTLAR), survivor))
    return hatalar


VAKALAR = (
    ("J1+J2 bes ev — pozitif ALLOW, negatif DENY (gercek yuk)", j1_j2_bes_ev),
    ("J3 yuklem — yol degeri + sabit kalip yolu", j3_yuklem),
    ("J4 izole mutantlar — SURVIVOR=0", j4_mutantlar),
)


def main():
    print("=== JEV KAPISI — serbest sekiller (Okan /goal 26 Eyl) ===")
    print("EVLER (tek kaynak kapi_dagitim.EVLER): %s" % ", ".join(a for a, _k in _evler()))
    tum = []
    for ad, fn in VAKALAR:
        try:
            hatalar = fn()
        except Exception as hata:
            hatalar = ["%s COKTU: %r" % (ad, hata)]
        print("  %-58s %s" % (ad, "TAMAM" if not hatalar else "KIRMIZI"))
        for h in hatalar:
            print("      - " + h)
        tum.extend(hatalar)
    print("BULGU=%d" % len(tum))
    return 0 if not tum else 1


if __name__ == "__main__":
    sys.exit(main())
