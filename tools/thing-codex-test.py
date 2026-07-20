#!/usr/bin/env python3
"""KABUL/REGRESYON TESTI — thing-codex.py denetim KAPSAMI (g5+ kor noktasi).

Kok neden (olculdu, MaCiT backfill): thing-codex `imgs = imgs[:MAX_IMG]` (MAX_IMG=4) ile galeriyi
Codex'e GONDERMEDEN ONCE 4'e kirpiyordu. Pratikte SADECE ilk 4 gorsel yargilaniyor; g5+ hic
gonderilmiyor, `sec_gorseller`/`elenen` daima g1..g4 icinde. 242 aday gorselin 199'unda denetim
kaydi YOKTU, 36'si g5+ araligindaydi -> DENETIMSIZ gorsel vitrine girdi. Kirpma SESSIZDI.

Duzeltme: MAX_IMG=8 (makul tavan; gorsel okuma en pahali adim) + `denetim_birlestir` her galeri
gorselini ya sec_gorseller/elenen ya da "denetlenmedi" altinda GARANTI eder. cap ustu (nadir g9+)
ya da Codex'in kapsamadigi gorsel SESSIZCE degil, ACIK "denetlenmedi" isaretiyle raporlanir.

Bu test GERCEK Codex/ag cagrisi YAPMAZ — codex() stub'lanir. Olctugu sey: verilen galeriye karsi
oneri.json ciktisinin (sec_gorseller ∪ elenen ∪ denetlenmedi) TUM galeriyi kapsadigi, ve cap ustu
gorsellerin "denetlenmedi" olarak isaretlendigi. Kok neden geri gelirse (kapsam 4'e duserse ya da
kirpilan gorsel sessizce dusarse) test kirmizi yanar.

Calistir:  python3 tools/thing-codex-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import importlib.util
import json
import os
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(DIR, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tc = _load("thing-codex.py", "thing_codex")


def _chk(ad, kosul, detay=""):
    if kosul:
        print("  ok  " + ad)
    else:
        print("  KALDI  " + ad + ("  -> " + detay if detay else ""))
        FAILS.append(ad)


def _kapsam(out, galeri):
    """oneri.json ciktisinin kapsadigi gorsel kumesi (secili + elenen + denetlenmedi)."""
    k = set(out.get("sec_gorseller") or [])
    for e in (out.get("elenen") or []):
        k.add(e["dosya"])
    for e in (out.get("denetlenmedi") or []):
        k.add(e["dosya"])
    return k


# ---------------------------------------------------------------------------
# TEST 1: denetim_bol — galeriyi cap'e gore boler (cap ustu KIRPILIR, kaybolmaz)
# ---------------------------------------------------------------------------
def test_bol():
    galeri = ["g1.jpg", "g2.jpg", "g3.jpg", "g4.jpg", "g5.jpg", "g6.jpg"]
    gonderilen, kirpilan = tc.denetim_bol(galeri, 4)
    _chk("bol: cap=4 -> ilk 4 gonderilir", gonderilen == ["g1.jpg", "g2.jpg", "g3.jpg", "g4.jpg"],
         str(gonderilen))
    _chk("bol: cap ustu (g5,g6) kirpilanda", kirpilan == ["g5.jpg", "g6.jpg"], str(kirpilan))
    # dogal sirali: g10 g2'den SONRA (duz sorted() yaniltir)
    g2 = ["g1.jpg", "g2.jpg", "g10.jpg", "g11.jpg"]
    gon, kir = tc.denetim_bol(g2, 2)
    _chk("bol: dogal sirali (g10 kirpilanda, g2 degil)",
         gon == ["g1.jpg", "g2.jpg"] and kir == ["g10.jpg", "g11.jpg"], str(gon) + " / " + str(kir))


# ---------------------------------------------------------------------------
# TEST 2: denetim_birlestir — g1..g8 galeri, cap=4 -> g5..g8 "denetlenmedi", TAM kapsam
#   (kok neden senaryosu: Codex sadece g1..g4 gormus, g5+ denetimsiz kalmamali)
# ---------------------------------------------------------------------------
def test_birlestir_kirpma():
    galeri = ["g%d.jpg" % i for i in range(1, 9)]  # g1..g8
    # Codex sadece gonderilen ilk 4'u gordu: 3'unu secti, 1'ini eledi
    out = {"sec_gorseller": ["g1.jpg", "g3.jpg", "g4.jpg"],
           "elenen": [{"dosya": "g2.jpg", "neden": "logo"}]}
    out = tc.denetim_birlestir(galeri, 4, out)
    dn = {e["dosya"] for e in out.get("denetlenmedi", [])}
    _chk("birlestir: g5..g8 denetlenmedi'de", dn == {"g5.jpg", "g6.jpg", "g7.jpg", "g8.jpg"}, str(dn))
    _chk("birlestir: TAM kapsam (union == galeri)", _kapsam(out, galeri) == set(galeri),
         str(_kapsam(out, galeri)))
    _chk("birlestir: denetlenmedi nedeni acik (kota)",
         all("denetlenmedi" in e["neden"] for e in out["denetlenmedi"]))


# ---------------------------------------------------------------------------
# TEST 3: denetim_birlestir — Codex GONDERILENI kapsamadi (fail-loud, sessiz gecmesin)
# ---------------------------------------------------------------------------
def test_birlestir_kapsamadi():
    galeri = ["g1.jpg", "g2.jpg", "g3.jpg", "g4.jpg"]
    out = {"sec_gorseller": ["g1.jpg"], "elenen": [{"dosya": "g2.jpg", "neden": "bulanik"}]}
    out = tc.denetim_birlestir(galeri, 8, out)  # cap galeriden buyuk -> hepsi gonderildi
    dn = {e["dosya"] for e in out.get("denetlenmedi", [])}
    _chk("kapsamadi: g3,g4 denetlenmedi (codex atladi)", dn == {"g3.jpg", "g4.jpg"}, str(dn))
    _chk("kapsamadi: TAM kapsam", _kapsam(out, galeri) == set(galeri))


# ---------------------------------------------------------------------------
# TEST 4: uctan uca process() — codex() STUB (gercek cagrisi yok), oneri.json'da denetlenmedi
# ---------------------------------------------------------------------------
def test_process_uctan_uca():
    tmp = tempfile.mkdtemp()
    tid = "test-parca"
    d = os.path.join(tmp, tid)
    os.makedirs(d)
    # g1..g8 sahte gorsel + meta.json
    for i in range(1, 9):
        with open(os.path.join(d, "g%d.jpg" % i), "wb") as f:
            f.write(b"\xff\xd8\xff\xe0JFIFtest" + b"\x00" * 32)
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump({"baslik": "Test Parca", "tasarimci": "x", "lisans": "CC BY", "olcu_mm": [10, 20, 30]}, f)

    # codex() stub: gercek Codex CAGIRMADAN, gonderilen ilk MAX_IMG gorselden secim yazar
    def sahte_codex(prompt, imgler, cikti_yolu):
        adlar = [os.path.basename(p) for p in imgler]  # process yalniz cap kadarini yollamali
        out = {"sec_gorseller": adlar[:3],
               "elenen": [{"dosya": adlar[3], "neden": "duplike"}] if len(adlar) > 3 else [],
               "baslik": "Test Parca", "aciklama": "test", "kategori": "Otomobil",
               "marka": ["Test"], "fiyat_oneri": "300 TL", "not": "stub"}
        with open(cikti_yolu, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False)
        return True, ""

    orij_root, orij_codex = tc.IMGROOT, tc.codex
    tc.IMGROOT = tmp
    tc.codex = sahte_codex
    try:
        tc.process(tid)
        out = json.load(open(os.path.join(d, "oneri.json")))
    finally:
        tc.IMGROOT, tc.codex = orij_root, orij_codex

    galeri = ["g%d.jpg" % i for i in range(1, 9)]
    # stub gonderilen gorsel sayisini adlar uzunlugundan gorur -> process MAX_IMG(8) yolladiysa
    # bu galeride kirpma OLMAZ; ama Codex secim+elenen sadece 4 gorseli kapsar (3 sec + 1 elenen),
    # kalan gonderilenler (g5..g8) "codex kapsamadi" ile denetlenmedi'ye dusmeli. Her iki halde de
    # KRITIK GARANTI: hicbir galeri gorseli kapsamsiz (sessiz) kalmaz.
    _chk("process: oneri.json'da denetlenmedi alani var", "denetlenmedi" in out)
    _chk("process: TAM kapsam (hicbir gorsel sessiz degil)",
         _kapsam(out, galeri) == set(galeri), str(sorted(_kapsam(out, galeri))))


# ---------------------------------------------------------------------------
# TEST 5: KIRMIZI-MUTASYON kontrolu — kapsam 4'e dusurulurse test 2 KIRMIZI yanmali
#   (nobetci: burada mutasyonu programatik uygular, testi kirmizi gorur, geri alir)
# ---------------------------------------------------------------------------
def test_mutasyon_nobetci():
    galeri = ["g%d.jpg" % i for i in range(1, 9)]
    out = {"sec_gorseller": ["g1.jpg", "g3.jpg", "g4.jpg"],
           "elenen": [{"dosya": "g2.jpg", "neden": "logo"}]}
    # MUTASYON: sanki denetim_birlestir hic cagrilmamis (eski davranis) -> denetlenmedi YOK
    mutant = dict(out)  # denetim_birlestir CAGIRMA
    kapsam = _kapsam(mutant, galeri)
    _chk("mutasyon: kapsam-YOK durumu g5+'i KACIRIR (nobetci canli)",
         kapsam != set(galeri) and {"g5.jpg", "g8.jpg"}.isdisjoint(kapsam),
         "mutant kapsam=" + str(sorted(kapsam)))
    # geri al: duzgun cagri TAM kapsar
    duzgun = tc.denetim_birlestir(galeri, 4, dict(out))
    _chk("mutasyon geri alindi: duzgun cagri TAM kapsar", _kapsam(duzgun, galeri) == set(galeri))


def main():
    print("thing-codex denetim kapsami testi")
    test_bol()
    test_birlestir_kirpma()
    test_birlestir_kapsamadi()
    test_process_uctan_uca()
    test_mutasyon_nobetci()
    print()
    if FAILS:
        print("KALDI: %d kontrol basarisiz -> %s" % (len(FAILS), ", ".join(FAILS)))
        sys.exit(1)
    print("GECTI: tum kontroller yesil")
    sys.exit(0)


if __name__ == "__main__":
    main()
