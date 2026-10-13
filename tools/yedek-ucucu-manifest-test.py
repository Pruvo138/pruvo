#!/usr/bin/env python3
"""Ucucu izin manifesti: TUKETIMLE kuculme yedek korumasini gecer, tuketilmemis dusus RED.

NEDEN VAR (12 Eki 2026): `.urunler-duzelt-izin.json` 18 girdinin 18'i HEAD'de tuketildigi
icin 4742 B -> 904 B kuculdu; koruma bunu veri kaybi sanip 22 ARDISIK kosumu kirmiziya
yakti (taban donuk). Onarim `tools/yedekle.py` icinde `UCUCU_MANIFESTLER` + tuketim
olcumudur (tanim `tools/izin-manifest-tuket.py`'den ice aktarilir). Bu test HERMETIKTIR:
sentetik git deposu + gecici "Drive" dizini; gercek Drive'a/HOME'a DOKUNMAZ.

VAKALAR
  V1 kanonik 18 girdi, hepsi HEAD'de tuketilmis, canli 2 girdi (%50 alti) -> GECER
  V2 bir girdi HEAD'de tuketilmemis                                     -> RED bayt-dususu
  V3 canli manifest bozuk JSON                                          -> RED
  V4 KUME DISI dosya ayni dususle                                       -> RED (eski davranis)
  V5 HEAD okunamiyor (commit'siz depo)                                  -> RED
MUTANTLAR (izole kopyada; ikisi de OLMEZSE test KIRMIZI)
  M1 tuketim olcumu daima True  -> V2 kirmizi yanmali
  M2 kume kontrolu her dosyayi gecirir -> V4 kirmizi yanmali
YAPI: kume EK_EVLER["pruvo"] icinde, tuketim modulunun 3 sabitiyle ESIT, `.diriltme`
kume DISINDA.

Cikis: 0 = VAKA=5/5 MUTANT=2/2 + YAPI · 1 = dustu · 2 = mutant capasi yok (OLCULEMEDI).
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
KANONIK = os.path.join(TOOLS, "yedekle.py")
TUKETIM = os.path.join(TOOLS, "izin-manifest-tuket.py")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)   # drive_yolu / git_ortami
from git_ortami import sentetik_git  # noqa: E402  (TEK guvenli sentetik git yolu)

AD = ".urunler-duzelt-izin.json"

MUTANTLAR = (
    ("M1-tuketim-daima-true", "V2",
     "def _ucucu_tuketim_olc(kaynak, varis):\n",
     "def _ucucu_tuketim_olc(kaynak, varis):\n    return (True, 1, 1, \"\")\n\n\n"
     "def _ucucu_tuketim_olc_ESKI(kaynak, varis):\n"),
    ("M2-kume-kontrolu-gecirir", "V4",
     "        return False  # KUME-DISI\n",
     "        return True  # KUME-DISI\n"),
)


# Miras git baglami `sentetik_git` icinde TEMIZLENIR: kanca icinden kosulursa `git init`
# GERCEK depoyu bozmasin ([[kanca-icinde-test-git-init-gercek-depoyu-bare-yapar]]).
# Genel config/kancalar da kum havuzuna sizmasin.
ORTAM = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
AYARLAR = ("-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false")


def git(depo, *arg):
    sentetik_git(depo, *arg, ek_ortam=ORTAM, ayarlar=AYARLAR, check=True,
                 capture_output=True)


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def urun(n):
    return {"id": "p%02d" % n, "ad": "Urun %02d" % n,
            "aciklama": "uzun aciklama %02d " % n + "x" * 60, "fiyat": "1%02d" % n}


def depo_kur(kok, commit=True):
    os.makedirs(kok)
    git(kok, "init", "-q")
    with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([urun(n) for n in range(20)], f, ensure_ascii=False, indent=2)
    if commit:
        git(kok, "add", "urunler.json")
        git(kok, "commit", "-qm", "katalog")
    return kok


def kanonik_manifest(bozuk_id=None):
    """18 girdi: p00..p17 alanlari HEAD'deki degerle ESIT (tuketilmis)."""
    m = {}
    for n in range(18):
        u = urun(n)
        m[u["id"]] = {"ad": u["ad"], "aciklama": u["aciklama"]}
    if bozuk_id:
        m[bozuk_id]["ad"] = "HEAD'DE OLMAYAN DEGER"
    return m


CANLI = {"p18": {"ad": "bekleyen 18"}, "p19": {"ad": "bekleyen 19"}}


def yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        if isinstance(veri, str):
            f.write(veri)
        else:
            json.dump(veri, f, ensure_ascii=False, indent=2)


def kopyala_dene(mod, kaynak, varis):
    """Doner: (red_sinifi | None, cikti). Red ise kanonik sha DEGISMEMIS olmali."""
    once = sha(varis)
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        try:
            mod._drive_kopyala(kaynak, varis)
        except mod.YedekKorumaHatasi as e:
            if sha(varis) != once:
                return ("RED-AMA-KANONIK-DEGISTI", tampon.getvalue())
            return (e.sinif, tampon.getvalue())
    return (None, tampon.getvalue())


def vakalar(mod, kok, etiket):
    """Doner: {vaka: gecti_mi}."""
    tmp = os.path.join(kok, etiket)
    depo = depo_kur(os.path.join(tmp, "depo"))
    commitsiz = depo_kur(os.path.join(tmp, "commitsiz"), commit=False)
    drive = os.path.join(tmp, "drive")
    os.makedirs(drive)
    sonuc = {}

    def hazirla(vaka, kok_dizin, ad, kanonik, canli):
        varis = os.path.join(drive, vaka, ad)
        os.makedirs(os.path.dirname(varis))
        yaz(varis, kanonik)
        kaynak = os.path.join(kok_dizin, ad)
        yaz(kaynak, canli)
        assert os.path.getsize(kaynak) < os.path.getsize(varis) * 0.5, vaka
        return kaynak, varis

    # V1 — tuketilmis dusus GECER, sayiyla basilir, kanonik guncellenir
    kaynak, varis = hazirla("V1", depo, AD, kanonik_manifest(), CANLI)
    red, cikti = kopyala_dene(mod, kaynak, varis)
    beklenen = "UCUCU_TUKETILDI dosya=%s dusen=18 tuketilen=18" % AD
    sonuc["V1"] = red is None and beklenen in cikti and sha(varis) == sha(kaynak)

    # V2 — bir girdi tuketilmemis -> RED bayt-dususu
    kaynak, varis = hazirla("V2", depo, AD, kanonik_manifest(bozuk_id="p05"), CANLI)
    red, cikti = kopyala_dene(mod, kaynak, varis)
    sonuc["V2"] = red == "bayt-dususu" and "UCUCU_TUKETILMEDI" in cikti

    # V3 — canli manifest bozuk JSON -> RED
    kaynak, varis = hazirla("V3", depo, AD, kanonik_manifest(), "{bozuk")
    red, _ = kopyala_dene(mod, kaynak, varis)
    sonuc["V3"] = red == "bayt-dususu"

    # V4 — kume disi dosya, ayni tuketilmis dusus -> RED (eski davranis)
    kaynak, varis = hazirla("V4", depo, ".baska-izin.json", kanonik_manifest(), CANLI)
    red, _ = kopyala_dene(mod, kaynak, varis)
    sonuc["V4"] = red == "bayt-dususu"

    # V5 — HEAD okunamiyor -> RED
    kaynak, varis = hazirla("V5", commitsiz, AD, kanonik_manifest(), CANLI)
    red, cikti = kopyala_dene(mod, kaynak, varis)
    sonuc["V5"] = red == "bayt-dususu" and "HEAD:urunler.json okunamadi" in cikti
    return sonuc


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def yapi_olc(mod):
    tm = modul_yukle(TUKETIM, "izin_manifest_tuket_test_%d" % os.getpid())
    kume = set(mod.UCUCU_MANIFESTLER)
    pruvo = set(mod.EK_EVLER["pruvo"])
    return {
        "kume-EK_EVLER-icinde": kume <= pruvo,
        "kume-tuketim-sabitleri": kume == {tm.DUZELT, tm.SIL, tm.RENAME},
        "diriltme-kume-disi": ".diriltme-izin.json" not in kume
                              and ".diriltme-izin.json" in pruvo,
    }


def main():
    kok = tempfile.mkdtemp(prefix="yedek-ucucu-test-")
    rc = 1
    try:
        mod = modul_yukle(KANONIK, "yedekle_ucucu_test_%d" % os.getpid())
        taban = vakalar(mod, kok, "taban")
        for v in sorted(taban):
            print("%s %s" % (v, "GECTI" if taban[v] else "DUSTU"))
        yapi = yapi_olc(mod)
        for k in sorted(yapi):
            print("YAPI %s %s" % (k, "GECTI" if yapi[k] else "DUSTU"))

        olen, olculemedi = 0, False
        kaynak_metin = open(KANONIK, encoding="utf-8").read()
        for ad, hedef_vaka, eski, yeni in MUTANTLAR:
            if kaynak_metin.count(eski) != 1:
                print("MUTANT %s OLCULEMEDI (capa %d kez)" % (ad, kaynak_metin.count(eski)))
                olculemedi = True
                continue
            mdir = os.path.join(kok, ad)
            os.makedirs(mdir)
            with open(os.path.join(mdir, "yedekle.py"), "w", encoding="utf-8") as f:
                f.write(kaynak_metin.replace(eski, yeni))
            shutil.copy(TUKETIM, os.path.join(mdir, "izin-manifest-tuket.py"))
            mmod = modul_yukle(os.path.join(mdir, "yedekle.py"),
                               "yedekle_ucucu_%s_%d" % (ad.split("-")[0], os.getpid()))
            ms = vakalar(mmod, kok, ad + "-kum")
            oldu = not ms[hedef_vaka]
            olen += 1 if oldu else 0
            print("MUTANT %s hedef=%s %s" % (ad, hedef_vaka,
                                             "OLDU (kirmizi)" if oldu else "HAYATTA"))

        vg = sum(1 for v in taban.values() if v)
        print("VAKA=%d/%d MUTANT=%d/%d" % (vg, len(taban), olen, len(MUTANTLAR)))
        if olculemedi:
            rc = 2
        elif vg == len(taban) and olen == len(MUTANTLAR) and all(yapi.values()):
            rc = 0
    finally:
        shutil.rmtree(kok, ignore_errors=True)
        print("GECICI_SILINDI=%s var=%s" % (kok, os.path.exists(kok)))
    return rc


if __name__ == "__main__":
    sys.exit(main())
