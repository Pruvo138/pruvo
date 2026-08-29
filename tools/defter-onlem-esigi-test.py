#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-onlem-esigi-test.py — K351 kabul bataryasi (29 Agu 2026).

OLCULEN ARIZA (cip `KraL-Tamirci-29Agu`, iddia degil — canli defterde iki kosum):
    defter 12.284 B / tavan 12.288 B (tavana 4 BAYT) iken yordamin emrettigi
        python3 tools/defter-rotasyon.py --tavan-kaynaktan
    `TASINAN=0 TASINAN_MADDE=0 ... TAVAN=DOLU_NO_OP` dondu ve dosya BIREBIR
    ayni kaldi. Onarim mekanizmasinin TAMAMI (cok-gecisli tasima +
    `--isaretciye-indir`) `if not _tavan_asildi_mi(...): return 0` erken
    cikisinin ARKASINDA yasiyor. Yani arac ancak tavan ASILDIKTAN sonra is
    yapabiliyor — ama tavan asildigi anda `defter-kota-kapisi.py` evin TUM
    commit'ini zaten kilitlemis oluyor. Koruma, korudugu isi ancak zarar
    olustuktan sonra yapabiliyor ([[koruma-kurali-korudugunu-durdurur]]).

ONARIM (K351): tavandan TURETILEN ikinci bir esik (`ONLEM_ORANI`,
`onlem_esikleri()`) TEK KAYNAKTA (`tools/defter-kota-taban.py`) tanimlanir ve
`defter-rotasyon.py --onlem` hedefi oraya ceker. Komut satirina SAYI YAZILMAZ.

🔴 BU BATARYANIN OLCTUGU DORT EKSEN (her biri en az bir MUTANTLA civilenmistir):
  V1  onlem esiginin ALTINDA  -> `--onlem` NO-OP (asagi dogru menzil siniri)
  V2  onlem ile tavan ARASINDA -> `--onlem` TASIR, `--tavan-kaynaktan` TASIMAZ
      (ASIL EKSEN: onarimin var olma sebebi)
  V3  tavanin USTUNDE -> eski davranis BOZULMAMIS (geriye uyum)
  V4  onlem esigi COZULEMEZSE -> rc=4 OLCULEMEDI; TAVANA SESSIZCE GERI DUSMEZ
      ([[olculemedi-bypass-degil-menzil-daraltmasi]])
  V5  KAPI HUKMU DEGISMEDI: onlem ile tavan arasindaki defter icin
      `tavan_asi_mi()` hala YESIL. Onlemi kapinin hukmune baglamak kilidi
      130/12288'den 117/11059'a CEKMEK olurdu — arizayi onarmak degil ONE ALMAK.

KONTROL KOPYASI ONCE: her mutant, mutasyonsuz bir KOPYADA once YESIL olan
bataryayla olculur. Kopyanin kendi cokmesi "mutant hedefini vurdu" diye
okunamaz ([[capa-cokmesi-arkasindaki-capalari-gizler]]).

Cikti son satiri:
    VAKA=<n> DUSEN=<n> MUTANT=<olduruldu>/<toplam> KONTROL=YESIL|KIRMIZI
rc=0 yalniz DUSEN=0 VE tum mutantlar oldurulduyse VE kontrol yesilse.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROTASYON = os.path.join(TOOLS, "defter-rotasyon.py")
TABAN = os.path.join(TOOLS, "defter-kota-taban.py")

DUSENLER = []
VAKA = [0]


def iddia(ad, kosul, beklenen, gercek):
    VAKA[0] += 1
    if not kosul:
        DUSENLER.append("%s beklenen=%s gercek=%s" % (ad, beklenen, gercek))
        print("DUSTU  %s  beklenen=%s gercek=%s" % (ad, beklenen, gercek))
    else:
        print("gecti  %s" % ad)


# ---------------------------------------------------------------------------
# FIKSTUR — sentetik defter. Boyut EKSENI ISTENEN degere gore kurulur.
# ---------------------------------------------------------------------------
BASLIK = "# DEVAM (fikstur)\n\n"
# 🔴 BU BLOGUN GOVDESINDE ACIK JETONU GECMEZ — ilk surumde govde "ACIK jetonu
# YOK" diye YAZIYORDU ve o dizge blogun KENDISINI vetoluyordu: fikstur kendi
# olcecegi seyi bozuyordu (kontrol kopyasi 3 iddiada KIRMIZI dondu, kod dogruydu).
KAPALI_BLOK = (
    "## ESKI IS KAPANDI — tam metin\n"
    + ("Kapanmis anlati satiri; tasinabilir olmali. %03d\n" % 0)
    + "".join("Kapanmis anlati satiri; tasinabilir olmali. %03d\n" % i
              for i in range(1, 18))
)
ACIK_BLOK = (
    "## ACIK KALEMLER\n"
    "- **K999** [ACIK] bu kalem acik, tasinmamali\n"
)
# 🔴 DOLGU SATIRI UZUN: bayt hedefine AZ SATIRLA ulasmali. Kisa dolguyla
# (~45 B/satir) 5,5 KB'lik bir fikstur 120 satiri asiyor ve SATIR ekseni
# istemeden tavanin ustune cikiyordu — olculen sey bayt ekseni sanilirken
# aslinda satir ekseniydi.
_DOLGU_GOVDE = "dolgu, acik kalir, tasinmaz " * 6


def defter_kur(yol, hedef_bayt, kapali_var=True):
    """Istenen bayta YAKIN, kapali blogu OLAN bir defter yazar.

    Dolgu KAPALI blogun ICINE degil, KORUMALI 'ACIK KALEMLER' blogunun icine
    konur: boylece "tasinabilir icerik" ile "dosya boyutu" eksenleri BAGIMSIZ
    kalir — aksi halde tasima her zaman hedefin altina indirirdi ve V2
    totoloji olurdu.
    """
    govde = BASLIK + (KAPALI_BLOK if kapali_var else "") + ACIK_BLOK
    i = 0
    while len(govde.encode("utf-8")) < hedef_bayt:
        govde += "- **K998** [ACIK] %s %04d\n" % (_DOLGU_GOVDE, i)
        i += 1
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde)
    return len(govde.encode("utf-8")), len(govde.splitlines())


def kos(rot_yol, defter, arsiv, bayraklar):
    r = subprocess.run([sys.executable, rot_yol, defter, arsiv] + list(bayraklar),
                       capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def bayt(yol):
    return os.path.getsize(yol)


def esikleri_oku(taban_yol):
    """Kopyadaki tabandan esikleri OKUR (ikinci kopya yazmamak icin)."""
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("t_taban_%d" % id(taban_yol), taban_yol)
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# BATARYA — verilen (rotasyon, taban) CIFTI uzerinde kosar.
# ---------------------------------------------------------------------------
def batarya(rot_yol, taban_yol, etiket):
    onceki = len(DUSENLER)
    try:
        mod = esikleri_oku(taban_yol)
    except Exception as e:                                   # noqa: BLE001
        iddia("%s::TABAN_YUKLENDI" % etiket, False, "yuklenir",
              "%s: %s" % (type(e).__name__, e))
        return len(DUSENLER) - onceki
    t_satir, t_bayt = mod.TAVAN_SATIR, mod.TAVAN_BAYT
    if hasattr(mod, "onlem_esikleri"):
        o_satir, o_bayt = mod.onlem_esikleri()
    else:
        o_satir, o_bayt = None, None

    calisma = tempfile.mkdtemp(prefix="k351-")
    try:
        arsiv = os.path.join(calisma, "ARSIV.md")
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("# ARSIV\n")

        # --- V1: ONLEM ESIGININ ALTINDA -> --onlem NO-OP -------------------
        d1 = os.path.join(calisma, "v1.md")
        hedef = (o_bayt if o_bayt else t_bayt) // 2
        defter_kur(d1, hedef)
        once = bayt(d1)
        rc, cikti = kos(rot_yol, d1, arsiv, ["--onlem"])
        iddia("%s::V1 onlem altinda NO-OP (dosya degismez)" % etiket,
              bayt(d1) == once, "bayt=%d" % once, "bayt=%d" % bayt(d1))
        iddia("%s::V1 rc=0" % etiket, rc == 0, "0", rc)

        # --- V2 ASIL EKSEN: ONLEM ile TAVAN ARASINDA ----------------------
        # Bu araligin TAMAMI, arizanin yasadigi bolgedir.
        if o_bayt is not None and o_bayt < t_bayt:
            ara_hedef = (o_bayt + t_bayt) // 2
        else:
            ara_hedef = t_bayt - 1          # onlem yoksa/tavana esitse: bitisik
        d2a = os.path.join(calisma, "v2a.md")
        d2b = os.path.join(calisma, "v2b.md")
        defter_kur(d2a, ara_hedef)
        shutil.copyfile(d2a, d2b)
        once2 = bayt(d2a)
        iddia("%s::V2 fikstur GERCEKTEN aralikta (onlem<bayt<=tavan)" % etiket,
              (o_bayt is None or once2 > o_bayt) and once2 <= t_bayt,
              "onlem=%s < %d <= tavan=%d" % (o_bayt, once2, t_bayt),
              "bayt=%d" % once2)

        rc_a, cikti_a = kos(rot_yol, d2a, arsiv, ["--tavan-kaynaktan"])
        iddia("%s::V2a --tavan-kaynaktan bu aralikta TASIMAZ (taban davranisi)"
              % etiket, bayt(d2a) == once2, "bayt=%d" % once2,
              "bayt=%d" % bayt(d2a))

        rc_b, cikti_b = kos(rot_yol, d2b, arsiv, ["--onlem"])
        iddia("%s::V2b --onlem bu aralikta TASIR (dosya KUCULUR)" % etiket,
              bayt(d2b) < once2, "<%d" % once2, "bayt=%d" % bayt(d2b))
        iddia("%s::V2b cikti ONLEM_HEDEFI satirini basar" % etiket,
              "ONLEM_HEDEFI" in cikti_b, "ONLEM_HEDEFI var",
              cikti_b.strip().splitlines()[-1] if cikti_b.strip() else "(bos)")
        iddia("%s::V2b hedef ONLEM esigidir (tavan DEGIL)" % etiket,
              ("bayt=%d" % o_bayt) in cikti_b if o_bayt is not None else False,
              "bayt=%s" % o_bayt,
              (re.search(r"ONLEM_HEDEFI[^\n]*", cikti_b) or ["(yok)"])[0]
              if isinstance(re.search(r"ONLEM_HEDEFI[^\n]*", cikti_b), re.Match)
              else "(yok)")

        # --- V3: TAVANIN USTUNDE -> geriye uyum korunur -------------------
        d3 = os.path.join(calisma, "v3.md")
        defter_kur(d3, t_bayt + 500)
        once3 = bayt(d3)
        rc3, _ = kos(rot_yol, d3, arsiv, ["--tavan-kaynaktan"])
        iddia("%s::V3 tavan ustunde --tavan-kaynaktan HALA TASIR" % etiket,
              bayt(d3) < once3, "<%d" % once3, "bayt=%d" % bayt(d3))

        # --- V5: KAPI HUKMU DEGISMEDI ------------------------------------
        ara_satir = (o_satir + t_satir) // 2 if o_satir else t_satir - 1
        asi, eksen, _, _ = mod.tavan_asi_mi(ara_satir, ara_hedef)
        iddia("%s::V5 onlem-tavan araliginda KAPI HUKMU hala YESIL" % etiket,
              asi is False, "asi=False", "asi=%s eksen=%s" % (asi, eksen))
        asi2, _, _, _ = mod.tavan_asi_mi(t_satir + 1, t_bayt + 1)
        iddia("%s::V5 tavan ustunde KAPI HUKMU hala KIRMIZI" % etiket,
              asi2 is True, "asi=True", "asi=%s" % asi2)
    finally:
        shutil.rmtree(calisma, ignore_errors=True)
    return len(DUSENLER) - onceki


# ---------------------------------------------------------------------------
# V4 — esik cozulemezse rc=4 (ayri kurulum: taban KIRPILIR)
# ---------------------------------------------------------------------------
def v4_failclosed():
    calisma = tempfile.mkdtemp(prefix="k351-v4-")
    try:
        rot = os.path.join(calisma, "defter-rotasyon.py")
        tab = os.path.join(calisma, "defter-kota-taban.py")
        shutil.copyfile(ROTASYON, rot)
        govde = open(TABAN, "r", encoding="utf-8").read()
        # `onlem_esikleri` SOKULUR (eski surumu taklit eder)
        govde = govde.replace("def onlem_esikleri(", "def _kaldirildi_onlem(")
        with open(tab, "w", encoding="utf-8") as f:
            f.write(govde)
        d = os.path.join(calisma, "d.md")
        a = os.path.join(calisma, "a.md")
        defter_kur(d, 4000)
        with open(a, "w", encoding="utf-8") as f:
            f.write("# ARSIV\n")
        once = bayt(d)
        rc, cikti = kos(rot, d, a, ["--onlem"])
        iddia("V4 onlem esigi yokken rc=4 (OLCULEMEDI)", rc == 4, "4", rc)
        iddia("V4 cikti OLCULEMEDI der", "OLCULEMEDI" in cikti,
              "OLCULEMEDI", cikti.strip()[-90:] or "(bos)")
        iddia("V4 dosyaya DOKUNULMAZ (sessiz tavana dusme YOK)",
              bayt(d) == once, "bayt=%d" % once, "bayt=%d" % bayt(d))
    finally:
        shutil.rmtree(calisma, ignore_errors=True)


# ---------------------------------------------------------------------------
# MUTANTLAR — her biri BIR ekseni oldurmeli
# ---------------------------------------------------------------------------
MUTANTLAR = (
    ("M1 onlem orani 1.0 (onlem == tavan)", "taban",
     ("ONLEM_ORANI = 0.90", "ONLEM_ORANI = 1.0")),
    ("M2 --onlem hedefi TAVANA geri duser", "rotasyon",
     ("        o_satir, o_bayt = _onlem_esikleri()",
      "        o_satir, o_bayt = TAVAN_SATIR, TAVAN_BAYT")),
    ("M3 kapi hukmu ONLEM esiginden turer (menzil kaymasi)", "taban",
     ("    satir_as = satir > TAVAN_SATIR\n    bayt_as = bayt > TAVAN_BAYT",
      "    _os, _ob = onlem_esikleri()\n"
      "    satir_as = satir > _os\n    bayt_as = bayt > _ob")),
    ("M4 --onlem bayragi YOK SAYILIR", "rotasyon",
     ("    if a.onlem:", "    if False and a.onlem:")),
)


def mutant_kos(ad, hedef, degisim):
    calisma = tempfile.mkdtemp(prefix="k351-m-")
    try:
        rot = os.path.join(calisma, "defter-rotasyon.py")
        tab = os.path.join(calisma, "defter-kota-taban.py")
        shutil.copyfile(ROTASYON, rot)
        shutil.copyfile(TABAN, tab)
        yol = rot if hedef == "rotasyon" else tab
        govde = open(yol, "r", encoding="utf-8").read()
        eski, yeni = degisim
        if eski not in govde:
            print("MUTANT_CAPASI_TUTMADI %s (capa bulunamadi)" % ad)
            return None                       # YAMA TUTMADI — mutant sayilmaz
        with open(yol, "w", encoding="utf-8") as f:
            f.write(govde.replace(eski, yeni, 1))
        oncesi = len(DUSENLER)
        batarya(rot, tab, "MUT")
        return len(DUSENLER) - oncesi
    finally:
        shutil.rmtree(calisma, ignore_errors=True)


def main():
    # 1) KONTROL KOPYASI — mutasyonsuz kopya once YESIL olmali.
    calisma = tempfile.mkdtemp(prefix="k351-k-")
    try:
        rot = os.path.join(calisma, "defter-rotasyon.py")
        tab = os.path.join(calisma, "defter-kota-taban.py")
        shutil.copyfile(ROTASYON, rot)
        shutil.copyfile(TABAN, tab)
        kontrol_dusen = batarya(rot, tab, "KONTROL")
    finally:
        shutil.rmtree(calisma, ignore_errors=True)
    kontrol = "YESIL" if kontrol_dusen == 0 else "KIRMIZI"

    # 2) CANLI GOVDE
    batarya(ROTASYON, TABAN, "CANLI")
    v4_failclosed()

    canli_dusen = len(DUSENLER)

    # 3) MUTANTLAR — her biri EN AZ BIR iddia oldurmeli
    olduruldu = 0
    yama_tutmadi = 0
    for ad, hedef, degisim in MUTANTLAR:
        n = mutant_kos(ad, hedef, degisim)
        if n is None:
            yama_tutmadi += 1
            print("MUTANT %s YAMA_TUTMADI" % ad)
            continue
        if n > 0:
            olduruldu += 1
            print("MUTANT %s OLDU (dusen_iddia=%d)" % (ad, n))
        else:
            print("MUTANT %s YASIYOR — batarya bu ekseni OLCMUYOR" % ad)
    # mutant kosumlarinin dusenleri hukme KARISMAZ
    del DUSENLER[canli_dusen:]

    print("VAKA=%d DUSEN=%d MUTANT=%d/%d YAMA_TUTMADI=%d KONTROL=%s"
          % (VAKA[0], len(DUSENLER), olduruldu, len(MUTANTLAR),
             yama_tutmadi, kontrol))
    for d in DUSENLER:
        print("  DUSEN: %s" % d)
    if DUSENLER or olduruldu != len(MUTANTLAR) or kontrol != "YESIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
