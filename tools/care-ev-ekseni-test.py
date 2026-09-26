#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — defter kotasi CARE satiri kapiyi CAGIRAN EVIN defterini mi gosteriyor?

  python3 tools/care-ev-ekseni-test.py

OLCULEN KUSUR (MaCiT Pentax kapanisi madde 3d, 26 Eyl 2026): pruvo-hasat pre-commit'i
KANONIK kapiyi (`/Users/okan/dev/pruvo/tools/defter-kota-kapisi.py`) kendi kokuyle
cagirir. hasat DEVAM.md tavanda durunca kapinin onerdigi rotasyon komutu KraL'in
`/Users/okan/dev/pruvo/DEVAM.md`'sini hedefliyordu: `_hukum_red` ve `care_son_satirlari`
`serbest_cagrilar.cagri_ornegi`'ne `kok` GECIRMIYORDU. Ustelik `kok` gecilse bile arac
yolu `pruvo-hasat/tools/defter-rotasyon.py`ye koklenirdi — o evde `tools/` YOK.

OLCULEN (fiksturde; canli defterlere DOKUNMAZ, sayac gecici dosyaya yonlenir):
  P1 care_son DEVAM ekseni: fikstur evinin DEVAM.md + DEVAM-ARSIV.md'si; kanonik degil
  P2 arac yolu DISKTE VAR (tools/ tasimayan evde kosan kapinin kopyasina duser)
  P3 `_hukum_red` CARE + KISA FORM satirlari fikstur evinin defterini gosterir
  P4 evin KENDI tools/defter-rotasyon.py'si varsa o kullanilir (kardes kopya korunur)
  P5 UCTAN UCA: gercek git fiksturunde tavan asan staged DEVAM.md -> rc!=0 ve
     `CARE_SON: [EKSEN=DEVAM]` fikstur yolunu tasir
  N1 KONTROL: kok verilmezse kanonik defter (eski davranis bayt ayni)
  N2 KONTROL: KUTU ekseni (filonun ortak kutusu) kok verilse de KANONIK kalir
  M  IZOLE MUTANTLAR (kum kopyasi) — SURVIVOR=0
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from git_ortami import git_ortami, sentetik_git  # noqa: E402
import veri_kok  # noqa: E402

KAPI = os.path.join(TOOLS, "defter-kota-kapisi.py")
KANONIK_ONEK = "/Users/okan/dev/pruvo/"
gecen = [0]
kalan = [0]


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + str(detay)[:400] if detay else ""))


def alt_olc(kapi_yolu, ev, ev_araci):
    """Taze surecte kapiyi yukle, CARE metinlerini JSON bas."""
    import importlib.util
    sys.path.insert(0, os.path.dirname(kapi_yolu))
    spec = importlib.util.spec_from_file_location("defter_kota_kapisi_care", kapi_yolu)
    k = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(k)
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        k._hukum_red(k.TAVAN_SATIR + 5, 100, "SATIR", ev)
    buf_k = io.StringIO()
    with contextlib.redirect_stderr(buf_k):
        k._hukum_red(k.TAVAN_SATIR + 5, 100, "SATIR", k._SC.KANONIK_KOK)
    sonuc = {
        "red_kanonik": [s for s in buf_k.getvalue().splitlines() if "KISA FORM" in s],
        "devam_ev": dict(k.care_son_satirlari(0, 0, 0, 1, kok=ev))["DEVAM"],
        "devam_kanonik": dict(k.care_son_satirlari(0, 0, 0, 1))["DEVAM"],
        "kutu_ev": dict(k.care_son_satirlari(1, 0, 0, 0, kok=ev))["KUTU"],
        "kutu_kanonik": dict(k.care_son_satirlari(1, 0, 0, 0))["KUTU"],
        "devam_ev_araci": dict(k.care_son_satirlari(0, 0, 0, 1, kok=ev_araci))["DEVAM"],
        "red": [s for s in buf.getvalue().splitlines() if "CARE:" in s or "KISA FORM" in s],
    }
    print("SONUC: " + json.dumps(sonuc, ensure_ascii=False))
    return 0


def olc(kapi_yolu, ev, ev_araci, sayac):
    ortam = dict(git_ortami(), PRUVO_DEFTER_KOTA_SAYAC=sayac)
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--alt", kapi_yolu,
                        ev, ev_araci], capture_output=True, text=True, timeout=120,
                       env=ortam)
    for s in (p.stdout or "").splitlines():
        if s.startswith("SONUC: "):
            return json.loads(s[len("SONUC: "):])
    return {"HATA": (p.stdout or "")[-300:] + (p.stderr or "")[-600:]}


def hukumler(r, ev, ev_araci):
    """{ad: (bool, detay)} — mutant kosumlari ayni hukumleri kullanir."""
    if "HATA" in r:
        return {a: (False, r["HATA"]) for a in ("P1", "P2", "P3", "P4", "N1", "N2", "N3")}
    d = r["devam_ev"]
    tok = d.split()
    ev_devam = os.path.join(ev, "DEVAM.md")
    return {
        "P1": (ev_devam in tok and os.path.join(ev, "DEVAM-ARSIV.md") in tok
               and KANONIK_ONEK + "DEVAM.md" not in tok, d),
        "P2": (len(tok) > 1 and os.path.isfile(tok[1]), d),
        # CARE satiri evin defterini gosterir; KISA FORM (konumsuz = kanonik defter)
        # bu evde KOMUT olarak ONERILMEZ.
        "P3": (len([s for s in r["red"] if "!! CARE:" in s]) == 1
               and all(ev_devam in s.split() and KANONIK_ONEK + "DEVAM.md" not in s.split()
                       for s in r["red"] if "!! CARE:" in s)
               and all("defter-rotasyon.py" not in s
                       for s in r["red"] if "KISA FORM" in s), r["red"]),
        "N3": (any("KISA FORM da serbesttir: python3" in s and "defter-rotasyon.py" in s
                   for s in r["red_kanonik"]), r["red_kanonik"]),
        "P4": (r["devam_ev_araci"].split()[1:2] == [
            os.path.join(ev_araci, "tools", "defter-rotasyon.py")], r["devam_ev_araci"]),
        "N1": (KANONIK_ONEK + "DEVAM.md" in r["devam_kanonik"].split(), r["devam_kanonik"]),
        "N2": (r["kutu_ev"] == r["kutu_kanonik"], (r["kutu_ev"], r["kutu_kanonik"])),
    }


ACIKLAMA = {
    "P1": "DEVAM CARE'i CAGIRAN EVIN DEVAM.md + DEVAM-ARSIV.md'sini gosteriyor (kanonik degil)",
    "P2": "tools/ tasimayan evde arac yolu DISKTE VAR (olu komut basilmiyor)",
    "P3": "_hukum_red CARE + KISA FORM satirlari evin defterini gosteriyor",
    "P4": "evin KENDI tools/defter-rotasyon.py'si varsa o kullaniliyor",
    "N1": "KONTROL: kok verilmezse kanonik defter (eski davranis)",
    "N2": "KONTROL: KUTU ekseni (ortak kutu) kok verilse de KANONIK",
    "N3": "KONTROL: kanonik evde KISA FORM hala oneriliyor",
}

# (ad, dosya, eski, yeni, oldurmesi beklenen hukum)
MUTANTLAR = [
    ("M1 _hukum_red kok'u DUSURDU (eski kusur birebir)", "defter-kota-kapisi.py",
     '_SC.cagri_ornegi("rotasyon-bakim", kok=kok)', '_SC.cagri_ornegi("rotasyon-bakim")',
     "P3"),
    ("M2 care_son ev ekseni kok'u DUSURDU", "defter-kota-kapisi.py",
     "ev = kok if eksen in CARE_EV_EKSENLERI else None", "ev = None", "P1"),
    ("M3 arac geri dususu SOKULDU (hasat/tools/... olu yol)", "serbest_cagrilar.py",
     "    if kok and not os.path.isfile(arac):", "    if False:", "P2"),
    ("M4 KUTU da eve kokledi (asiri genisleme)", "defter-kota-kapisi.py",
     'CARE_EV_EKSENLERI = frozenset({"DEVAM"})',
     'CARE_EV_EKSENLERI = frozenset({"DEVAM", "KUTU"})', "N2"),
    ("M5 KISA FORM her evde onerildi (konumsuz = kanonik defter)", "defter-kota-kapisi.py",
     "    if not kok or os.path.normpath(kok) == _SC.KANONIK_KOK:", "    if True:", "P3"),
]


def _git(kok, *args):
    p = sentetik_git(kok, *args, capture_output=True, text=True,
                     kimlik_ad="t", kimlik_eposta="t@t", timeout=120)
    if p.returncode != 0:
        raise RuntimeError("git %s rc=%d %s" % (args, p.returncode, p.stderr))


def uctan_uca(tmp, sayac):
    """Gercek git fiksturu: tavan asan staged DEVAM.md -> kapi rc!=0 + CARE_SON ev yolu."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "defter_kota_taban_care", os.path.join(TOOLS, "defter-kota-taban.py"))
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    ev = os.path.join(tmp, "e2e-ev")
    os.makedirs(ev)
    _git(ev, "init", "-q")
    with open(os.path.join(ev, "DEVAM.md"), "w", encoding="utf-8") as f:
        f.write("".join("- satir %d\n" % i for i in range(t.TAVAN_SATIR + 20)))
    _git(ev, "add", "DEVAM.md")
    ortam = dict(git_ortami(), PRUVO_DEFTER_KOTA_SAYAC=sayac)
    p = subprocess.run([sys.executable, KAPI, ev], capture_output=True, text=True,
                       timeout=300, env=ortam, cwd=ev)
    son = [s for s in (p.stderr or "").splitlines() if "CARE_SON: [EKSEN=DEVAM]" in s]
    return p.returncode, son, (p.stderr or "")[-400:]


def ana():
    tmp = tempfile.mkdtemp(prefix="care-ev-ekseni-")
    sayac = os.path.join(tmp, "sayac.tsv")
    try:
        ev = os.path.join(tmp, "hasat-gibi")          # tools/ YOK (pruvo-hasat gibi)
        os.makedirs(ev)
        ev_araci = os.path.join(tmp, "kardes-ev")     # kendi araci VAR
        os.makedirs(os.path.join(ev_araci, "tools"))
        open(os.path.join(ev_araci, "tools", "defter-rotasyon.py"), "w").close()

        print("\n[P/N] gercek kapi (taze surec)")
        r = olc(KAPI, ev, ev_araci, sayac)
        for ad, (ok, detay) in sorted(hukumler(r, ev, ev_araci).items()):
            dogrula("%s %s" % (ad, ACIKLAMA[ad]), ok, detay)

        print("\n[P5] UCTAN UCA — gercek git fiksturu, kapi alt surecte")
        rc, son, kuyruk = uctan_uca(tmp, sayac)
        ev_e2e = os.path.join(tmp, "e2e-ev", "DEVAM.md")
        dogrula("P5a tavan asan staged DEVAM.md -> kapi rc!=0", rc != 0, "rc=%d" % rc)
        dogrula("P5b CARE_SON [EKSEN=DEVAM] fikstur evinin DEVAM.md'sini gosteriyor",
                len(son) == 1 and ev_e2e in son[0].split()
                and KANONIK_ONEK + "DEVAM.md" not in son[0].split(), son or kuyruk)

        print("\n[M] IZOLE MUTANTLAR (kum kopyasi; canli govde DEGISMEZ)")
        survivor = 0
        for i, (ad, dosya, eski, yeni, hedef) in enumerate(MUTANTLAR):
            kaynak = open(os.path.join(TOOLS, dosya), encoding="utf-8").read()
            adet = kaynak.count(eski)
            dogrula("%s — capa govdede TAM 1 kez" % ad, adet == 1, "adet=%d" % adet)
            if adet != 1:
                survivor += 1
                continue
            kum_tools = os.path.join(tmp, "kum%d" % i, "tools")
            # defter-rotasyon.py da serilir: M3 disindaki kumlarda arac geri dususu
            # GERCEKTEN bir dosya bulsun (yoksa M3 "bedava" olurdu).
            veri_kok.kum_kur(kum_tools, {"defter-kota-kapisi.py": None,
                                         "serbest_cagrilar.py": None,
                                         "defter-rotasyon.py": None}, TOOLS)
            # kum_kur var olani EZMEZ: mutant metni sonradan YAZILIR (sira garantisi).
            with open(os.path.join(kum_tools, dosya), "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
            rm = olc(os.path.join(kum_tools, "defter-kota-kapisi.py"), ev, ev_araci, sayac)
            ok, detay = hukumler(rm, ev, ev_araci)[hedef]
            if ok:
                survivor += 1
            dogrula("%s -> %s KIRMIZI yandi (mutant OLDU)" % (ad, hedef), not ok, detay)
            dogrula("%s — canli %s mutasyondan etkilenmedi" % (ad, dosya),
                    open(os.path.join(TOOLS, dosya), encoding="utf-8").read() == kaynak)
        dogrula("SURVIVOR=%d (beklenen 0)" % survivor, survivor == 0)
        print("SURVIVOR=%d" % survivor)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nNE OLCULMEDI (beyan): onerilen komutun MaCiT oturumunda mimar-icra-kapisi'ndan "
          "gecip gecmedigi (ev disi konum argumani) — bu test yalniz CARE METNINI olcer.")
    print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
    return 1 if kalan[0] else 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--alt":
        sys.exit(alt_olc(sys.argv[2], sys.argv[3], sys.argv[4]))
    sys.exit(ana())
