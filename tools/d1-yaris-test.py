#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — pre-push D1 senkronunda YEREL YAZICI YARISI ayirt ediliyor mu?

  python3 tools/d1-yaris-test.py

OLCULEN SAHTE RED (25 Eyl gecesi 2. kez, MaCiT 26 Eyl uc dilim): ayni makinede iki push
ayni anda urunler.json degistirdi; ikincinin pre-push senkronu yerel flock'a carpip
ANINDA rc=1 verdi ("D1 SENKRONU BASARISIZ"), hemen ardindan `--durum` uyusmaz 0 dedi.
GERCEK HATA ile YARIS ayni rc'yi tasiyordu.

BU TEST DAVRANIS OLCER (CANLI D1'e / wrangler'a / aga DOKUNMAZ):
  A. `yaris_karari` karar tablosu (saf) — YAZ / KAPSANDI / YARIS, pozitif + negatif.
  B. GERCEK flock (gecici dosya, ayri surec tutar): bekleme 0 -> YerelYaziciUcusta
     (SystemExit alt sinifi, eski metin AYNEN); bekleme>0 -> tutan birakinca ALIR;
     tavan dolarsa yine YerelYaziciUcusta.
  C. `yaris_olc` GERCEK git fiksturunde (bare uzak + klon): uzak==push -> YAZ,
     uzak atasi -> YAZ, push KATI atasi -> KAPSANDI, ayrismis -> YARIS, uzak yok -> YARIS.
  D. `main()` UCTAN UCA (ayri surec; `_main` = yazma kaydi, D1 lease = no-op):
     D1 ortam yok + kilit tutuluyor -> rc=5, yazma 0, jeton basildi
     D2 bekleme + uzak==push -> rc=0, yazma 1
     D3 bekleme + push KATI ata -> rc=0, yazma 0, KAPSANDI jetonu
     D4 bekleme + ayrismis -> rc=5, yazma 0
     D5 KONTROL: cakisma yok -> yazma 1, yeniden olcum satiri YOK
  M. IZOLE MUTANTLAR (kum kopyasinda; canli govdeye dokunulmaz) — SURVIVOR=0 beklenir.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from git_ortami import git_ortami, sentetik_git  # noqa: E402
import veri_kok  # noqa: E402

GERCEK = os.path.join(TOOLS, "d1-sync.py")
gecen = [0]
kalan = [0]


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + str(detay)[:400] if detay else ""))


def _modul_yukle(yol):
    import importlib.util
    spec = importlib.util.spec_from_file_location("d1_sync_yaris", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── ALT SURECLER ─────────────────────────────────────────────────────────────
def alt_tut(kilit, sure):
    """Kilidi tut, TUTULDU bas, `sure` sn bekle, birak."""
    import fcntl
    with open(kilit, "r+") as fd:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
        print("TUTULDU", flush=True)
        time.sleep(float(sure))
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    return 0


def alt_main(d1_yolu, kilit):
    """main()'i yama ile kos; SONUC: {rc, yazdi} satiri bas."""
    m = _modul_yukle(d1_yolu)
    yazdi = []
    m.yazici_kilit_yolu = lambda: kilit
    m.dagitik_kilit_al = lambda *a, **k: None
    m._main = lambda a: yazdi.append(1)
    sys.argv = ["d1-sync.py"]
    try:
        rc = m.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    sys.stdout.flush()
    print("SONUC: " + json.dumps({"rc": rc, "yazdi": len(yazdi)}), flush=True)
    return 0


# ── FIKSTUR ──────────────────────────────────────────────────────────────────
def _git(kok, *args):
    p = sentetik_git(kok, *args, capture_output=True, text=True,
                     kimlik_ad="t", kimlik_eposta="t@t", timeout=120)
    if p.returncode != 0:
        raise RuntimeError("git %s rc=%d %s" % (args, p.returncode, p.stderr))
    return (p.stdout or "").strip()


def _commit(depo, ad):
    with open(os.path.join(depo, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([{"id": ad}], f)
    _git(depo, "add", "urunler.json")
    _git(depo, "commit", "-q", "-m", ad)
    return _git(depo, "rev-parse", "HEAD")


def fikstur(tmp):
    """bare uzak + klon; doner: (depo, {ad: sha}). Gecmis: taban -> c1 -> c2 ; taban -> yan."""
    uzak = os.path.join(tmp, "uzak.git")
    depo = os.path.join(tmp, "depo")
    os.makedirs(depo)
    _git(tmp, "init", "-q", "--bare", uzak)
    _git(uzak, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(depo, "init", "-q")
    _git(depo, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(depo, "remote", "add", "origin", uzak)
    s = {"taban": _commit(depo, "taban")}
    s["c1"] = _commit(depo, "c1")
    s["c2"] = _commit(depo, "c2")
    _git(depo, "checkout", "-q", "-b", "yan", s["taban"])
    s["yan"] = _commit(depo, "yan")
    _git(depo, "checkout", "-q", "main")
    return depo, s


def uzagi_kur(depo, sha):
    _git(depo, "push", "-q", "--force", "origin", "%s:refs/heads/main" % sha)


def tutucu_baslat(kilit, sure):
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--tut", kilit,
                          str(sure)], stdout=subprocess.PIPE, text=True)
    satir = p.stdout.readline()
    if "TUTULDU" not in satir:
        p.kill()
        raise RuntimeError("tutucu kilidi alamadi: %r" % satir)
    return p


def main_kos(d1_yolu, kilit, depo, ortam_ek, tutucu_sure=None):
    """Ayri surecte main(); doner: (rc, yazdi, cikti)."""
    tutucu = tutucu_baslat(kilit, tutucu_sure) if tutucu_sure else None
    ortam = veri_kok.kum_ortami(depo, git_ortami())
    ortam.pop("PRUVO_D1_YARIS_BEKLE_SN", None)
    ortam.pop("PRUVO_D1_PUSH_SHA", None)
    ortam.update(ortam_ek)
    try:
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--main", d1_yolu,
                            kilit], capture_output=True, text=True, timeout=120,
                           env=ortam, cwd=depo)
    finally:
        if tutucu:
            tutucu.wait(timeout=60)
    cikti = (p.stdout or "") + (p.stderr or "")
    for satir in (p.stdout or "").splitlines():
        if satir.startswith("SONUC: "):
            d = json.loads(satir[len("SONUC: "):])
            return d["rc"], d["yazdi"], cikti
    return None, None, cikti


def d_senaryolari(d1_yolu, tmp, etiket="", yalniz=None):
    """D1..D5 (ya da `yalniz` kumesi); doner {ad: (bool, detay)}. Mutant kosumlari
    ayni govdeyi yalniz HEDEF vakasiyla kosar (CI suresi)."""
    depo, s = fikstur(os.path.join(tmp, "d" + etiket))
    kilit = os.path.join(tmp, "kilit" + etiket)
    open(kilit, "w").close()
    sonuc = {}
    bekle = {"PRUVO_D1_YARIS_BEKLE_SN": "20"}

    def kos(ad):
        return yalniz is None or ad in yalniz

    if kos("D1"):
        rc, yz, ck = main_kos(d1_yolu, kilit, depo, {}, tutucu_sure=2)
        sonuc["D1"] = (rc == 5 and yz == 0 and "D1_SENKRON=YARIS SEBEP=YEREL_YARIS" in ck
                       and "D1 YAZICI UCUSTA" in ck, (rc, yz, ck[-300:]))

    uzagi_kur(depo, s["c2"])
    if kos("D2"):
        rc, yz, ck = main_kos(d1_yolu, kilit, depo,
                              dict(bekle, PRUVO_D1_PUSH_SHA=s["c2"]), tutucu_sure=1.5)
        sonuc["D2"] = (rc == 0 and yz == 1 and "YARIS SONRASI OLCUM: YAZ" in ck,
                       (rc, yz, ck[-300:]))
    if kos("D3"):
        rc, yz, ck = main_kos(d1_yolu, kilit, depo,
                              dict(bekle, PRUVO_D1_PUSH_SHA=s["c1"]), tutucu_sure=1.5)
        sonuc["D3"] = (rc == 0 and yz == 0 and "D1_SENKRON=KAPSANDI" in ck,
                       (rc, yz, ck[-300:]))
    if kos("D4"):
        rc, yz, ck = main_kos(d1_yolu, kilit, depo,
                              dict(bekle, PRUVO_D1_PUSH_SHA=s["yan"]), tutucu_sure=1.5)
        sonuc["D4"] = (rc == 5 and yz == 0 and "D1_SENKRON=YARIS" in ck,
                       (rc, yz, ck[-300:]))
    if kos("D5"):
        rc, yz, ck = main_kos(d1_yolu, kilit, depo,
                              dict(bekle, PRUVO_D1_PUSH_SHA=s["c1"]))
        sonuc["D5"] = (rc == 0 and yz == 1 and "YARIS SONRASI OLCUM" not in ck,
                       (rc, yz, ck[-300:]))
    return sonuc


ACIKLAMA = {
    "D1": "ortam YOK + kilit tutuluyor -> rc=5, yazma 0, YARIS jetonu + eski metin",
    "D2": "bekleme + uzak==push -> kilit alindi, rc=0, yazma 1 (sahte RED kapandi)",
    "D3": "🔴 bekleme + push KATI ata -> rc=0, yazma 0, KAPSANDI (eski katalog YAZILMAZ)",
    "D4": "bekleme + ayrismis uzak -> rc=5, yazma 0 (fail-closed)",
    "D5": "KONTROL: cakisma yok -> yazma 1, yeniden olcum YOK",
}

# (ad, eski, yeni, oldurmesi beklenen D vakasi)
MUTANTLAR = [
    ("M1 KAPSANDI kolu sokuldu (bekleme sonrasi hep yaz)",
     '        if karar != "YAZ":\n            yazici_kilidi_birak(yerel)',
     '        if False:\n            yazici_kilidi_birak(yerel)', "D3"),
    ("M2 ortamdaki bekleme yok sayildi (eski aninda-RED)",
     "yerel = yazici_kilidi_al(bekleme_sn=yaris_bekleme_sn())",
     "yerel = yazici_kilidi_al(bekleme_sn=0.0)", "D2"),
    ("M3 YARIS rc'si GERCEK HATA rc'sine (1) geri dondu",
     "                         % YARIS_JETONU)\n        return 5",
     "                         % YARIS_JETONU)\n        return 1", "D1"),
    ("M4 karar tablosunda KAPSANDI -> YAZ",
     '        return "KAPSANDI", ("push edilen', '        return "YAZ", ("push edilen', "D3"),
    ("M5 ayrismis uzak YAZ sayildi",
     '    return "YARIS", "uzak main %s push edilen commit\'ten AYRISMIS"',
     '    return "YAZ", "uzak main %s push edilen commit\'ten AYRISMIS"', "D4"),
]


def ana():
    tmp = tempfile.mkdtemp(prefix="d1-yaris-test-")
    # VERI KOKU gecici dizine: modul ANA kopyanin katalogunu/git'ini sansla gormesin.
    os.environ[veri_kok.ENV_AD] = tmp
    try:
        D1 = _modul_yukle(GERCEK)

        print("\n[A] KARAR TABLOSU (saf)")
        k = D1.yaris_karari
        dogrula("A1 uzak == push -> YAZ", k("aa", "aa", None, None)[0] == "YAZ")
        dogrula("A2 uzak YOK (ilk push) -> YAZ", k("aa", "", None, None)[0] == "YAZ")
        dogrula("A3 uzak push'un atasi -> YAZ", k("aa", "bb", True, False)[0] == "YAZ")
        dogrula("A4 🔴 push uzagin KATI atasi -> KAPSANDI",
                k("aa", "bb", False, True)[0] == "KAPSANDI")
        dogrula("A5 ayrismis -> YARIS", k("aa", "bb", False, False)[0] == "YARIS")
        dogrula("A6 ata olculemedi -> YARIS", k("aa", "bb", None, None)[0] == "YARIS")
        dogrula("A7 uzak olculemedi -> YARIS", k("aa", None, None, None)[0] == "YARIS")
        dogrula("A8 push sha yok -> YARIS", k("", "bb", None, None)[0] == "YARIS")
        dogrula("A9 bekleme ortami: yok/gecersiz/negatif -> 0, sayi -> sayi",
                D1.yaris_bekleme_sn({}) == 0 and D1.yaris_bekleme_sn({
                    D1.YARIS_BEKLE_ENV: "x"}) == 0 and D1.yaris_bekleme_sn({
                        D1.YARIS_BEKLE_ENV: "-3"}) == 0 and D1.yaris_bekleme_sn({
                            D1.YARIS_BEKLE_ENV: "480"}) == 480)

        print("\n[B] GERCEK flock (gecici dosya)")
        kilit = os.path.join(tmp, "b-kilit")
        open(kilit, "w").close()
        t = tutucu_baslat(kilit, 3)
        try:
            D1.yazici_kilidi_al(kilit, bekleme_sn=0.0, kol="YAZICI")
            b1 = ("DONDU", None)
        except D1.YerelYaziciUcusta as e:
            b1 = ("YARIS", e)
        except SystemExit as e:
            b1 = ("BASKA", e)
        dogrula("B1 bekleme 0 -> YerelYaziciUcusta (ayirt edilebilir sinif)",
                b1[0] == "YARIS", b1)
        dogrula("B2 sinif SystemExit alt sinifi + eski metin AYNEN (eski cagiranlar icin)",
                b1[0] == "YARIS" and isinstance(b1[1], SystemExit)
                and "D1 YAZICI UCUSTA — ikinci tam-katalog yazicisi fail-closed DURDU"
                in str(b1[1].code), b1)
        t0 = time.monotonic()
        try:
            D1.yazici_kilidi_al(kilit, bekleme_sn=0.6, kol="YAZICI")
            b3 = "DONDU"
        except D1.YerelYaziciUcusta as e:
            b3 = str(e.code)
        dogrula("B3 bekleme tavani dolunca yine YerelYaziciUcusta (beklendi basildi)",
                "beklendi=" in b3 and time.monotonic() - t0 >= 0.5, b3)
        t.wait(timeout=30)
        t = tutucu_baslat(kilit, 1.2)
        t0 = time.monotonic()
        fd = D1.yazici_kilidi_al(kilit, bekleme_sn=15, kol="YAZICI")
        sure = time.monotonic() - t0
        D1.yazici_kilidi_birak(fd)
        t.wait(timeout=30)
        dogrula("B4 bekleme>0: tutan birakinca kilit ALINDI ve BEKLEDI isareti kalkti",
                D1._SON_KILIT_BEKLEDI[0] is True and sure >= 0.8, (sure,))
        fd = D1.yazici_kilidi_al(kilit, bekleme_sn=15, kol="YAZICI")
        D1.yazici_kilidi_birak(fd)
        dogrula("B5 KONTROL: cakisma yokken BEKLEDI isareti False",
                D1._SON_KILIT_BEKLEDI[0] is False)

        print("\n[C] yaris_olc — GERCEK git fiksturu")
        depo, s = fikstur(os.path.join(tmp, "c"))
        uzagi_kur(depo, s["c1"])
        dogrula("C1 uzak == push -> YAZ", D1.yaris_olc(s["c1"], depo)[0] == "YAZ")
        dogrula("C2 uzak push'un atasi -> YAZ", D1.yaris_olc(s["c2"], depo)[0] == "YAZ")
        uzagi_kur(depo, s["c2"])
        c3 = D1.yaris_olc(s["c1"], depo)
        dogrula("C3 🔴 push uzagin KATI atasi -> KAPSANDI", c3[0] == "KAPSANDI", c3)
        c4 = D1.yaris_olc(s["yan"], depo)
        dogrula("C4 ayrismis -> YARIS", c4[0] == "YARIS", c4)
        c5 = D1.yaris_olc(s["c1"], depo, uzak="yok-boyle-uzak")
        dogrula("C5 uzak OLCULEMEDI -> YARIS", c5[0] == "YARIS", c5)

        print("\n[D] main() UCTAN UCA (ayri surec, gercek flock, gercek git)")
        for ad, (ok, detay) in sorted(d_senaryolari(GERCEK, tmp).items()):
            dogrula("%s %s" % (ad, ACIKLAMA[ad]), ok, detay)

        print("\n[M] IZOLE MUTANTLAR (kum kopyasi; canli govde DEGISMEZ)")
        kaynak = open(GERCEK, encoding="utf-8").read()
        survivor = 0
        for i, (ad, eski, yeni, hedef) in enumerate(MUTANTLAR):
            adet = kaynak.count(eski)
            dogrula("%s — capa govdede TAM 1 kez" % ad, adet == 1, "adet=%d" % adet)
            if adet != 1:
                survivor += 1
                continue
            kum = os.path.join(tmp, "kum%d" % i)
            veri_kok.kum_kur(os.path.join(kum, "tools"),
                             {"d1-sync.py": kaynak.replace(eski, yeni)}, TOOLS)
            sonuc = d_senaryolari(os.path.join(kum, "tools", "d1-sync.py"), tmp,
                                  etiket="m%d" % i, yalniz={hedef})
            oldu = not sonuc[hedef][0]
            if not oldu:
                survivor += 1
            dogrula("%s -> %s KIRMIZI yandi (mutant OLDU)" % (ad, hedef), oldu,
                    sonuc[hedef][1])
        dogrula("SURVIVOR=%d (beklenen 0)" % survivor, survivor == 0)
        print("SURVIVOR=%d" % survivor)
        dogrula("CANLI govde mutasyondan etkilenmedi",
                open(GERCEK, encoding="utf-8").read() == kaynak)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nNE OLCULMEDI (beyan): CANLI D1 yazimi ve dagitik lease (stub'landi; eksenleri "
          "d1-dagitik-kilit-test.py + d1-sync --kendini-test). Kancanin rc=5 kolu -> "
          "prepush-d1-kaynak-test.py [H].")
    print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
    return 1 if kalan[0] else 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--tut":
        sys.exit(alt_tut(sys.argv[2], sys.argv[3]))
    if len(sys.argv) >= 2 and sys.argv[1] == "--main":
        sys.exit(alt_main(sys.argv[2], sys.argv[3]))
    sys.exit(ana())
