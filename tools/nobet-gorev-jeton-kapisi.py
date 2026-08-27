#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K324 KAPISI — nobet turunun MAKINE HUKUM JETONU gorev metninde ISTENIYOR mu?

--------------------------------------------------------------------------
OLCULEN VAKA (27 Agu 2026, cip KraL-NobetTuru-27Agu)
--------------------------------------------------------------------------
`nobet-kapi.py` her turda isci ciktisindan `kosum_tur_hukmu()` ile bir makine
`HUKUM=` jetonu ayiklar; jeton YOKSA fail-closed `KOSUM_HUKMU=OLCULEMEDI`
basar. Zincir oradan sonra kendiliginden kirmiziya gider:

    jeton yok -> KOSUM_HUKMU=OLCULEMEDI          (nobet-kapi.py:2358)
              -> kalp `kosum_hukmu=OLCULEMEDI`   (gozcu.py:835)
              -> `uretken=false`                 (gozcu.uretken_mi)
              -> `GOZCU_URETMEDI_OLCULEMEDI`     (nobet-tetik.karar 3a)
              -> tetik rc=11 -> `BITIS rc=1`     (ci-nobeti.sh)

ANCAK isciye verilen gorev metni (`~/.claude/cron/ci-nobeti-gorev.md`) o
jetonu HIC ISTEMIYORDU: 37.755 baytin icinde `TUR_HUKMU` ve `KOSUM_HUKMU`
dizgeleri **0 kez** geciyordu. OKUYAN VAR, YAZAN YOK.
Olculen sonuc — gozcu.log 2026-08-27T20:23:02Z turu: isci
"CI TEMIZ — eski failure'larin hepsinin green replacement'i var" diye DUZ
METIN yazdi, tek makine jetonu basmadi ->
`KOSUM_HUKMU=OLCULEMEDI MOTOR_RC=0 TUR_HUKMU=-` -> saatlik hat `rc=1`.
Ayni desen 27 Agu 00:07-12:07 arasi 13 ardisik saat olculdu.

--------------------------------------------------------------------------
BU KAPI NE OLCER (uc AYRI kol; hicbiri otekini tekrar etmez)
--------------------------------------------------------------------------
K1 METIN     : gorev metni jetonu ADIYLA ve KAPALI SOZLUKLE istiyor mu?
K2 SOZLUK    : metindeki sozluk `kosum_hukmu_coz()`un GERCEKTEN tukettigi
               kumeyle ortusuyor mu? (ikiz liste yasak — tuketici KOSULUR)
K3 DAVRANIS  : jeton ciktida VARKEN ve YOKKEN tuketici FARKLI hukum uretiyor
               mu? Metin ekseni tek basina kabul DEGILDIR
               ([[kapinin-menzili-cagri-yeridir]], [[n2b-kapisi-dizge-olcer]]):
               "dosyada dizge var" ile "kol davranis degistiriyor" AYRI
               sorulardir ve bu kapi ikincisini de olcer.

Cikis: 0 = uc kol da yesil · 1 = en az biri kirmizi · 2 = arac hatasi.
Curutucu: `--mutasyon` — jetonu metinden ve sozlugu kaynaktan tek tek dusurur;
her mutant KENDI kolunu oldurmeli, otekiler YESIL kalmalidir.
"""

import argparse
import importlib.util
import io
import os
import sys

CRON = os.environ.get("PRUVO_NOBET_KOK") or os.path.join(
    os.path.expanduser("~"), ".claude", "cron")

# Gorev metninde BIREBIR aranan capalar (K1).
ISARET = "## 7) MAKINE HUKUM JETONU"
JETON_KALIBI = "HUKUM=<TEMIZ|KAPANDI|ONARIM_YOK|ONARIM_ILERLIYOR>"

# K2/K3'un olctugu sozlesme. 🔴 Bu tablo bir IKIZ LISTE DEGILDIR: her satiri
# `kosum_hukmu_coz()` KOSULARAK dogrulanir; kaynak degisirse kapi kirmizi yanar.
SOZLESME = (
    ("TEMIZ", "TEMIZ"),
    ("KAPANDI", "TEMIZ"),
    ("ONARIM_YOK", "TEMIZ"),
    ("ONARIM_ILERLIYOR", "ONARIM_DENENDI"),
    ("", "OLCULEMEDI"),
)

# 🔴 KANONIK BOLUM — KURUCU KAYNAK. `ci-nobeti-gorev.md` surum kontrolu DISINDA
# (`~/.claude/cron/`); metnin TEK KALICI KOPYASI burasidir. Makine yeniden
# kurulursa `--kur` onu geri yazar. Yoksa onarim, yedegi silinen bir dosyada
# yasar ve sessizce kaybolur (K304: yedek borcu).
KANONIK_BOLUM = u"""
## 7) MAKINE HUKUM JETONU — TURUN SON SATIRI (27 Agu 2026, cip KraL-NobetTuru-27Agu)

🔴 **Bu turun SON CEVABININ (nihai yanit metninin) son satiri BIREBIR su olmalidir:**

```
HUKUM=<TEMIZ|KAPANDI|ONARIM_YOK|ONARIM_ILERLIYOR>
```

🔴 **HANGI CIKTI? — KARISTIRMA.** Jeton **SENIN NIHAI YANITINA** gider; nobet onu
`isci.sh`in **stdout**'undan okur (`nobet-kapi.py:2357 kosum_tur_hukmu`).
`ci-nobeti.log`'a elle yazdigin `[<UTC>] ...` blogundaki `HUKUM=` satiri
**O CIKTI DEGILDIR** ve kapiya HIC ULASMAZ. Olculdu (20:23-20:25 turu):
loga `[2026-08-27T20:24:54Z] HUKUM=TEMIZ` yazilmisti, buna ragmen nihai yanitta
jeton olmadigi icin kapi `KOSUM_HUKMU=OLCULEMEDI ... TUR_HUKMU=-` yazdi.
Loga yazmaya DEVAM ET — jeton ONUN YERINE degil, NIHAI YANITIN SONUNA gelir.

**NEDEN (olculdu, iddia degil):** `nobet-kapi.py` turun hukmunu senin ciktindan
`kosum_tur_hukmu()` ile AYIKLAR ve `KOSUM_HUKMU=` diye basar. Jeton YOKSA
fail-closed `OLCULEMEDI` yazar; `gozcu.py` bunu `uretken=false` yapar,
`nobet-tetik.py` `GOZCU_URETMEDI_OLCULEMEDI` koluyla `rc=11` doner ve
**saatlik nobet hatti KIRMIZI kapanir** — CI tertemiz olsa bile.
27 Agu 20:23:02Z turunda tam bu oldu: raporda "CI TEMIZ — eski failure'larin
hepsinin green replacement'i var" yaziyordu, ama duz metindi; jeton yoktu ->
`KOSUM_HUKMU=OLCULEMEDI MOTOR_RC=0 TUR_HUKMU=-` -> `BITIS rc=1`.
Ayni desen 27 Agu 00:07-12:07 arasi **13 ardisik saat** olculdu.

**SOZLUK KAPALIDIR** (tuketici `nobet-kapi.kosum_hukmu_coz()`; baska deger
yazarsan `ONARIM_DENENDI` sayilir ve run-id denemesi ARTAR):

| yazacagin jeton      | ne zaman                                              |
|----------------------|-------------------------------------------------------|
| `HUKUM=TEMIZ`        | CI kirmizisi YOK ya da duran kirmizinin hepsinin yesil |
|                      | ardili var; onarilacak bir sey bulunmadi               |
| `HUKUM=KAPANDI`      | kirmizi VARDI, bu turda ONARDIN ve olcerek dogruladin  |
| `HUKUM=ONARIM_YOK`   | kirmizi var ama bu turun menzilinde DEGIL (baska ev /  |
|                      | Okan kapisi / dondurma emri) — ve bunu ADIYLA yazdin   |
| `HUKUM=ONARIM_ILERLIYOR` | onarima BASLADIN, bu turda bitmedi                 |

**KURALLAR:**
- Jeton **satirin basinda**, tek basina ve BUYUK HARF olmali. Cumle icine gomme
  ("hukum temiz" DEGIL), tirnak/backtick icine alma.
- Prose ozet YAZMAYA DEVAM ET — jeton onun YERINE degil, **SONUNA** gelir.
- 🔴 **TAHMIN YAZMA.** Olcemedigin bir eksen varsa jetonu `HUKUM=ONARIM_ILERLIYOR`
  yaz ve neyi olcemedigini ADIYLA belirt. `HUKUM=TEMIZ` bir BEYAN degil, bir
  OLCUM sonucudur ([[isci-yesil-tablo-ic-olcumu-bosaltir]]).
- `N2B HUKUM=...` satirlari kapi tarafindan ELENIR; onlar senin hukmun DEGILDIR.

**Kabul:** `python3 /Users/okan/dev/pruvo/tools/nobet-gorev-jeton-kapisi.py`
"""

_SAYAC = {"kol": 0, "gecen": 0}
_DUSEN = []


def olc(ad, beklenen, gozlenen):
    _SAYAC["kol"] += 1
    tamam = beklenen == gozlenen
    if tamam:
        _SAYAC["gecen"] += 1
    else:
        _DUSEN.append(ad)
        sys.stderr.write("[DUSTU] %s\n  beklenen=%r\n  gozlenen=%r\n"
                         % (ad, beklenen, gozlenen))
    print("KOL %-12s %s" % (ad, "GECTI" if tamam else "DUSTU"))
    return tamam


def _nobet_kapi(kaynak=None):
    if CRON not in sys.path:
        sys.path.insert(0, CRON)
    yol = kaynak or os.path.join(CRON, "nobet-kapi.py")
    spec = importlib.util.spec_from_file_location("nk_k324", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _gorev_metni(metin=None, yol=None):
    if metin is not None:
        return metin
    with io.open(yol or os.path.join(CRON, "ci-nobeti-gorev.md"),
                 encoding="utf-8") as f:
        return f.read()


def k1_metin(metin):
    """Gorev metni jetonu ADIYLA ve KAPALI SOZLUKLE istiyor mu?"""
    eksik = []
    if ISARET not in metin:
        eksik.append("BOLUM_YOK")
    if JETON_KALIBI not in metin:
        eksik.append("JETON_KALIBI_YOK")
    for jeton, _ in SOZLESME:
        if jeton and ("HUKUM=" + jeton) not in metin:
            eksik.append("SOZLUK_EKSIK:" + jeton)
    return olc("K1-METIN", [], eksik)


def k2_sozluk(NK):
    """Metindeki sozluk tuketicinin GERCEK davranisiyla ortusuyor mu?"""
    sapma = []
    for jeton, bekleniyor in SOZLESME:
        gorulen = NK.kosum_hukmu_coz(0, jeton, 0, 0)
        if gorulen != bekleniyor:
            sapma.append((jeton or "<YOK>", bekleniyor, gorulen))
    return olc("K2-SOZLUK", [], sapma)


# Gercek isci ciktisinin iskeleti — 20:23:02Z turundan alinmistir.
_CIKTI_TABAN = (
    "N2B HUKUM=GECER KOL=N2B-MUAF EV=KraL ACIK=0 KALEM=-\n"
    "CI TEMIZ - eski failure'larin hepsinin green replacement'i var\n"
    "ISCI_TEMIZLIK cikti_silinen=0 cikti_kalan=6\n"
)


def k3_davranis(NK):
    """Jeton VARKEN / YOKKEN tuketici FARKLI hukum uretiyor mu?"""
    jetonsuz = NK.kosum_hukmu_coz(
        0, NK.kosum_tur_hukmu(_CIKTI_TABAN), 0, 0)
    jetonlu = NK.kosum_hukmu_coz(
        0, NK.kosum_tur_hukmu(_CIKTI_TABAN + "HUKUM=TEMIZ\n"), 0, 0)
    # 🔴 `N2B HUKUM=GECER` satiri ELENMELIDIR: elenmezse jetonsuz cikti da
    # "hukum var" sanilir ve kol sahte yesil yanar.
    return olc("K3-DAVRANIS", ("OLCULEMEDI", "TEMIZ"), (jetonsuz, jetonlu))


def kos(metin=None, kaynak=None, yalniz=None):
    def istenir(ad):
        return yalniz is None or ad in yalniz
    try:
        NK = _nobet_kapi(kaynak)
    except Exception as hata:
        print("ARAC HATASI: nobet-kapi.py yuklenemedi: %s" % hata)
        return 2
    if istenir("K1"):
        k1_metin(_gorev_metni(metin))
    if istenir("K2"):
        k2_sozluk(NK)
    if istenir("K3"):
        k3_davranis(NK)
    return 0


def mutasyon():
    """Curutucu: her mutant KENDI kolunu oldurmeli, otekiler YESIL kalmali."""
    import re
    import shutil
    import tempfile

    metin = _gorev_metni()
    kaynak_yolu = os.path.join(CRON, "nobet-kapi.py")
    with io.open(kaynak_yolu, encoding="utf-8") as f:
        kaynak = f.read()

    mutantlar = [
        # (ad, hedef_kol, kontrol_kollari, metin_uretici, kaynak_uretici)
        ("M1-bolum-silinir", ["K1"], ["K2", "K3"],
         lambda: metin.replace(ISARET, "## 7) (SILINDI)"), None),
        ("M2-sozluk-daralir", ["K1"], ["K2", "K3"],
         lambda: metin.replace("HUKUM=ONARIM_YOK", "HUKUM=ONARIM_BILINMEZ"), None),
        # K2 ve K3 KAYNAK ekseni: sozluk kaynaktan kayarsa ikisi de olur;
        # K1 (metin ekseni) YESIL kalmali -> mutant "her seyi kirmadi".
        ("M3-tuketici-jetonu-yok-sayar", ["K2", "K3"], ["K1"], None,
         lambda: kaynak.replace(
             '    if hukum in ("TEMIZ", "KAPANDI", "ONARIM_YOK"):',
             '    if False:')),
        # K3'e OZEL: N2B eleme kolu olur -> jetonsuz cikti "GECER" okur.
        # K1/K2 YESIL kalir.
        ("M4-n2b-elemesi-korlesir", ["K3"], ["K1", "K2"], None,
         lambda: kaynak.replace(
             'if not s.lstrip().startswith("N2B ")',
             'if True')),
    ]

    olen = atif = 0
    for ad, hedef, kontrol, m_metin, m_kaynak in mutantlar:
        yeni_metin = m_metin() if m_metin else None
        yeni_kaynak = m_kaynak() if m_kaynak else None
        if m_metin and yeni_metin == metin:
            print("MUTANT %-30s CAPA_YOK (metin degismedi)" % ad)
            continue
        if m_kaynak and yeni_kaynak == kaynak:
            print("MUTANT %-30s CAPA_YOK (kaynak degismedi)" % ad)
            continue
        gecici = tempfile.mkdtemp(prefix="k324-m-")
        try:
            kaynak_kopya = None
            if yeni_kaynak is not None:
                kaynak_kopya = os.path.join(gecici, "nobet-kapi.py")
                with io.open(kaynak_kopya, "w", encoding="utf-8") as f:
                    f.write(yeni_kaynak)
            once = list(_DUSEN)
            onceki_sayac = dict(_SAYAC)
            kos(metin=yeni_metin, kaynak=kaynak_kopya,
                yalniz=set(hedef + kontrol))
            yeni_dusen = [d for d in _DUSEN[len(once):]]
            _SAYAC.clear()
            _SAYAC.update(onceki_sayac)
            del _DUSEN[len(once):]

            def _var(kume):
                return [h for h in kume
                        if any(d.startswith(h + "-") for d in yeni_dusen)]
            h_dusen = _var(hedef)
            k_dusen = _var(kontrol)
            oldu = len(h_dusen) == len(hedef)
            bu_atif = oldu and not k_dusen
            olen += int(oldu)
            atif += int(bu_atif)
            print("MUTANT %-30s %s ATIF=%s hedef_dusen=%d/%d kontrol_dusen=%s"
                  % (ad, "OLDU" if oldu else "YASADI",
                     "EVET" if bu_atif else "HAYIR",
                     len(h_dusen), len(hedef), k_dusen or "-"))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    print("MUTASYON OLEN=%d/%d ATIF=%d/%d"
          % (olen, len(mutantlar), atif, len(mutantlar)))
    return 0 if (olen == len(mutantlar) and atif == len(mutantlar)) else 1


def kur():
    """KANONIK_BOLUM'u kurulu gorev metnine YAZAR (yedek alarak, idempotent).

    🔴 Bu kol VAR cunku hedef dosya surum kontrolu DISINDADIR. Metnin tek
    kalici kopyasi bu dosyadadir; makine yeniden kurulursa ya da dosya
    yedeklerle birlikte silinirse onarim BURADAN geri gelir.
    """
    import shutil
    import time
    yol = os.path.join(CRON, "ci-nobeti-gorev.md")
    try:
        with io.open(yol, encoding="utf-8") as f:
            metin = f.read()
    except OSError as hata:
        print("KURULUM DUSTU: %s" % hata)
        return 2
    onceki = len(metin.encode("utf-8"))
    if ISARET in metin:
        print("ZATEN_KURULU bayt=%d — dokunulmadi." % onceki)
        return 0
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    yedek = "%s.yedek-nobetGorevJeton-%s" % (yol, damga)
    shutil.copy2(yol, yedek)
    with io.open(yol, "a", encoding="utf-8") as f:
        f.write(KANONIK_BOLUM)
    with io.open(yol, encoding="utf-8") as f:
        sonra = len(f.read().encode("utf-8"))
    print("KURULDU bayt %d -> %d" % (onceki, sonra))
    print("YEDEK %s" % yedek)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mutasyon", action="store_true",
                    help="curutucu: kollari tek tek oldur, atfi olc")
    ap.add_argument("--kur", action="store_true",
                    help="kanonik bolumu kurulu gorev metnine yaz (idempotent)")
    args = ap.parse_args(argv)
    if args.kur:
        return kur()
    if args.mutasyon:
        taban = kos()
        if taban != 0 or _DUSEN:
            print("🔴 TABAN YESIL DEGIL — mutant sonuclari yorumlanamaz. DUR.")
            return 1
        print("--- MUTANTLAR (bu satirlar NORMAL teshis ciktisidir) ---")
        return mutasyon()
    rc = kos()
    if rc == 2:
        return 2
    print("KAPI KOL=%d/%d DUSEN=%s"
          % (_SAYAC["gecen"], _SAYAC["kol"], ",".join(_DUSEN) or "-"))
    return 0 if not _DUSEN else 1


if __name__ == "__main__":
    sys.exit(main())
