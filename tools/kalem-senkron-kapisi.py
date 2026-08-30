#!/usr/bin/env python3
"""KALEM SENKRON KAPISI (K309, 26 Agu 2026).

OLCULEN ARIZA
-------------
Kalem kuyrugunun IKI kayit duzlemi var:
  * KAYNAK-DOGRUSU : ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md
                     (tablo satiri = kalem; nobet kapisi `kabul:` komutunu BURADAN okur
                     ve KENDISI kosar)
  * CALISMA DEFTERI: <repo>/DEVAM.md (canli durum, anlati)

Kaynak-dogrusunda SATIRI OLMAYAN bir kalem, defterin kendi kural blogunun deyisiyle
"VERILMIS SAYILMAZ": ne kapanabilir, ne olculebilir, ne dagitilabilir. Yani nobetin
olcum evreninin DISINDADIR. Bu kapi tam o AYRISMAYI sayar.

SINIF: [[kapinin-menzili-cagri-yeridir]] — kapi VAR, kural VAR, menzil kuyrugun
yarisini GORMUYOR.

HUKUM BICIMI — TABAN RATCHET, AMBIYANS DEGIL
--------------------------------------------
Bugunku ayrisma buyuk (bkz. tools/kalem-senkron-taban.json). Kapi bugunku sayiyi
ANINDA kirmiziya yakmaz — komsunun yayinini durduran kapi geri alinir
([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]). Kapi bir RATCHET'tir:
  * menzil_disi <= taban  -> GECER
  * menzil_disi >  taban  -> KIRMIZI, ve YENI (tabanda olmayan) id'ler ADIYLA basilir
Taban ELLE yazilmaz: yalnizca `--taban-yaz` OLCEREK yazar ([[K201]] — kayit kendini
olcmez). Tabani YUKSELTMEK ayrica `--gerekce "<metin>"` ister; boylece "kirmizi geldi,
tabani buyutelim" sessiz bir kacis olmaz.

MENZIL / `OLCULEMEDI` — MUAFIYET DEGIL, DARALTMA
------------------------------------------------
Kaynak-dogrusu defteri repo DISINDADIR. Iki AYRI kol vardir ve karistirilmazlar:

  * CANLI KOL (varsayilan / `--canli` / `--rapor`): defterin BULUNDUGU duzlemde
    kosar (mimar makinesi, nobet). Defter ya da DEVAM.md okunamazsa kapi SESSIZ
    YESIL DONMEZ: `OLCULEMEDI` jetonu + SIFIR-DISI rc basar
    ([[olculemedi-bypass-degil-menzil-daraltmasi]]). Taban dosyasi yoksa da ayni.

  * HERMETIK KOL (`--kendini-test` / `--mutasyon`): fikstur uzerinde kosar, ag/dis
    dosya ISTEMEZ; CI'da bu kol baglidir (nobet.yml `serit-b`).

🔴 CI'da CANLI KOL BILEREK KOSMAZ ve bu bir MUAFIYET DEGIL, MENZIL DARALTMASIDIR:
   olculecek duzlem (memory/) CI checkout'unda YOKTUR, dolayisiyla orada canli kolu
   kosturmak KALICI `OLCULEMEDI` kirmizisi uretir, `serit-b`yi surekli kirmizi birakir
   ve gercek regresyon sinyalini oldurur ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).
   Bunun yerine CI, kapinin KENDI davranisini — OLCULEMEDI kolunun sifir-disi rc'si
   DAHIL — fikstur uzerinde olcer; canli kol defterin oldugu duzlemde kosar.
   Muafiyet listesi kabul DEGILDIR ve burada KULLANILMAMISTIR: canli kolun
   fail-closed'ligi V5/V5b/V6 vakalariyla olculur ve M1 mutantiyla ISPATLANIR
   (kol sessiz yesile cevrilince o uc vaka OLUR).

BILINEN BYPASS (kayitli olmasi sart — kapi disiplin cihazidir, hapishane DEGIL)
------------------------------------------------------------------------------
  * `PRUVO_KALEM_DEFTER` / `PRUVO_KALEM_DEVAM` / `PRUVO_KALEM_TABAN` ortam
    degiskenleri duzlemi kaydirabilir (fikstur kosumu bunlarla yapilir). Sahte bir
    defter gostererek ayrismayi 0 gostermek MUMKUNDUR. Kapatilmadi: fikstursuz
    kendini-test yazilamaz ve bu kapi bir SAYIM nobetcisidir, guvenlik siniri degil.
    Gosterilen yol OKUNAMAZSA fail-closed `OLCULEMEDI` doner (sessiz genisleme yok).
  * `KABUL_VAR` sayaci BLOK duzeyindedir = UST SINIR. Bir maddede birden cok id
    geciyorsa (or. "K272·K273·K274·K277") ve maddede `kabul:` varsa DORDU de sayilir.
    Bilerek boyle: sayi "en fazla bu kadari kabul komutu tasiyor OLABILIR" der;
    kalem-basi kesin olcum kalemin KENDI satiri acildiginda yapilir.

KULLANIM
--------
    python3 tools/kalem-senkron-kapisi.py --kendini-test   # HERMETIK (CI: serit-b)
    python3 tools/kalem-senkron-kapisi.py --mutasyon       # 2 mutant + KONTROL
    python3 tools/kalem-senkron-kapisi.py --rapor          # ON-OLCUM + durum kirilimi
    python3 tools/kalem-senkron-kapisi.py                  # CANLI hukum (taban ratchet)
    python3 tools/kalem-senkron-kapisi.py --taban-yaz [--gerekce "..."]

CIKIS KODLARI
-------------
    0  GECTI            (canli: menzil_disi <= taban · hermetik: tum vakalar yesil)
    1  TABAN_ASILDI     (canli kirmizi)
    2  KENDINI_TEST_KIRMIZI / MUTASYON_KIRMIZI
    3  OLCULEMEDI_DUZLEM (defter ya da DEVAM.md okunamadi)
    4  OLCULEMEDI_TABAN  (taban dosyasi yok / bozuk)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

RC_GECTI = 0
RC_TABAN_ASILDI = 1
RC_TEST_KIRMIZI = 2
RC_OLCULEMEDI_DUZLEM = 3
RC_OLCULEMEDI_TABAN = 4

BURASI = os.path.dirname(os.path.abspath(__file__))
REPO_KOK = os.path.dirname(BURASI)

DEFTER_VARSAYILAN = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md")
DEVAM_VARSAYILAN = os.path.join(REPO_KOK, "DEVAM.md")
TABAN_VARSAYILAN = os.path.join(BURASI, "kalem-senkron-taban.json")

# Kaynak-dogrusu TABLO SATIRI: satir basinda '| K<sayi> |'. Anlati icindeki atiflar
# (or. "[[K182]]", "K256'dan DOGDU") SATIR DEGILDIR ve sayilmaz.
DEFTER_SATIR_RE = re.compile(r"^\|\s*(K\d+)\s*\|", re.M)

# DEVAM.md id gecisi. `\b` ONEKTE aranir, sonek ARANMAZ: "K222Rc" -> K222,
# "K104B" -> K104 (ikisi de ayni kalemin ekidir). Bu, bagimsiz dogrulamada
# kullanilan `grep -o "K[0-9][0-9]*"` ile BIREBIR ayni kumeyi verir.
DEVAM_ID_RE = re.compile(r"\bK(\d+)")

ISARETLER = ("🔴", "🔧", "✅", "🟠", "⚠️", "⚠", "⛔", "⚖️", "⚖", "🔁", "🔚")
KABUL_RE = re.compile(r"kabul\s*:", re.I)

# Blok basi: madde imi, baslik, alinti, tablo satiri, ya da satir basinda duran isaret.
BLOK_BASI_RE = re.compile(
    r"^(?:\s*[-*+]\s|#{1,6}\s|>\s|\|)|^(?:" + "|".join(re.escape(i) for i in ISARETLER) + ")")


class Olculemedi(Exception):
    """Duzlem okunamadi — YESIL DEGIL, sifir-disi rc."""

    def __init__(self, mesaj, rc=RC_OLCULEMEDI_DUZLEM):
        super().__init__(mesaj)
        self.rc = rc


# ── DUZLEM COZUMU ────────────────────────────────────────────────────────────────
def yollar():
    return (
        os.environ.get("PRUVO_KALEM_DEFTER") or DEFTER_VARSAYILAN,
        os.environ.get("PRUVO_KALEM_DEVAM") or DEVAM_VARSAYILAN,
        os.environ.get("PRUVO_KALEM_TABAN") or TABAN_VARSAYILAN,
    )


def _oku(yol, etiket):
    try:
        with open(yol, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise Olculemedi(
            "OLCULEMEDI — %s duzlemi OKUNAMADI (%s): %s. Olculemeyen ayrisma YESIL "
            "DEGILDIR (fail-closed)." % (etiket, yol, type(e).__name__))


# ── OLCUM ────────────────────────────────────────────────────────────────────────
def defter_idleri(metin):
    """(satir_sayisi, benzersiz_id_kumesi). Ayni id iki satirda gecebilir (canli
    defterde olculdu: K29 iki kez) — o yuzden ikisi AYRI dondurulur, biri otekinin
    yerine gecmez."""
    hepsi = DEFTER_SATIR_RE.findall(metin)
    return len(hepsi), set(hepsi)


def _bloklar(metin):
    """[(bas_offset, bit_offset, blok_metni)] — id'yi isaretine ve `kabul:` alanina
    baglamak icin. Blok, madde imi/baslik/isaret ile baslar, bir sonrakine kadar surer."""
    satirlar = metin.splitlines(keepends=True)
    basliklar = []
    ofs = 0
    for s in satirlar:
        if BLOK_BASI_RE.match(s):
            basliklar.append(ofs)
        ofs += len(s)
    if not basliklar or basliklar[0] != 0:
        basliklar.insert(0, 0)
    sinirlar = basliklar + [len(metin)]
    return [(sinirlar[i], sinirlar[i + 1], metin[sinirlar[i]:sinirlar[i + 1]])
            for i in range(len(basliklar))]


def _isaret(blok_metni, id_yerel_ofs):
    """Id'den ONCE gelen SON isaret. Yoksa blogun HERHANGI bir isareti. Yoksa ISARETSIZ."""
    once = blok_metni[:id_yerel_ofs]
    en_son, en_son_ofs = None, -1
    for i in ISARETLER:
        p = once.rfind(i)
        if p > en_son_ofs:
            en_son, en_son_ofs = i, p
    if en_son is not None:
        return en_son
    for i in ISARETLER:
        if i in blok_metni:
            return i
    return "ISARETSIZ"


def devam_kalemleri(metin):
    """{id: {"isaret":…, "kabul_var":bool, "satir":n}} — id'nin ILK gecisi baglayicidir."""
    kayit = {}
    for bas, _bit, blok in _bloklar(metin):
        blok_kabul = bool(KABUL_RE.search(blok))
        for m in DEVAM_ID_RE.finditer(blok):
            kid = "K" + m.group(1)
            if kid in kayit:
                # Ayni id birden cok blokta gecebilir; `kabul:` VARLIGI birlesiktir
                # (bir blokta yaziliysa kalem icin YAZILMISTIR).
                kayit[kid]["kabul_var"] = kayit[kid]["kabul_var"] or blok_kabul
                continue
            mutlak = bas + m.start()
            kayit[kid] = {
                "isaret": _isaret(blok, m.start()),
                "kabul_var": blok_kabul,
                "satir": metin.count("\n", 0, mutlak) + 1,
            }
    return kayit


def olc():
    defter_yolu, devam_yolu, _ = yollar()
    defter_metni = _oku(defter_yolu, "KAYNAK-DOGRUSU (acik-kalemler.md)")
    devam_metni = _oku(devam_yolu, "CALISMA DEFTERI (DEVAM.md)")
    satir_sayisi, defter_ids = defter_idleri(defter_metni)
    devam = devam_kalemleri(devam_metni)
    menzil_disi = {k: v for k, v in devam.items() if k not in defter_ids}
    return {
        "kaynak_dogrusu_satir": satir_sayisi,
        "kaynak_dogrusu_benzersiz_id": len(defter_ids),
        "kaynak_dogrusu_mukerrer": satir_sayisi - len(defter_ids),
        "devam_md_benzersiz_id": len(devam),
        "menzil_ici": len(devam) - len(menzil_disi),
        "menzil_disi": len(menzil_disi),
        "menzil_disi_ids": sorted(menzil_disi, key=lambda k: int(k[1:])),
        "menzil_disi_kayit": menzil_disi,
        "defter_ids": sorted(defter_ids, key=lambda k: int(k[1:])),
    }


# ── TABAN ────────────────────────────────────────────────────────────────────────
def taban_oku():
    _, _, taban_yolu = yollar()
    try:
        with open(taban_yolu, encoding="utf-8") as f:
            veri = json.load(f)
    except Exception as e:
        raise Olculemedi(
            "OLCULEMEDI — TABAN dosyasi okunamadi/bozuk (%s): %s. Tabansiz hukum "
            "verilmez (fail-closed); once `--taban-yaz` ile OLCEREK yaz."
            % (taban_yolu, type(e).__name__), rc=RC_OLCULEMEDI_TABAN)
    if not isinstance(veri.get("menzil_disi"), int) or \
            not isinstance(veri.get("menzil_disi_ids"), list):
        raise Olculemedi(
            "OLCULEMEDI — TABAN dosyasinin sema alanlari eksik (%s): `menzil_disi` (int) "
            "ve `menzil_disi_ids` (list) ZORUNLU." % taban_yolu, rc=RC_OLCULEMEDI_TABAN)
    return veri


def taban_yaz(gerekce=None):
    _, _, taban_yolu = yollar()
    o = olc()  # 🔴 TABAN OLCULEREK yazilir; elle sayi KABUL EDILMEZ ([[K201]]).
    eski = None
    try:
        eski = taban_oku()
    except Olculemedi:
        pass
    if eski is not None and o["menzil_disi"] > eski["menzil_disi"] and not gerekce:
        print("RED — TABAN YUKSELTILEMEZ: olculen %d > mevcut taban %d. Ratchet yalnizca "
              "ASAGI serbesttir; yukseltmek ACIK gerekce ister: --gerekce \"<metin>\"."
              % (o["menzil_disi"], eski["menzil_disi"]))
        return RC_TABAN_ASILDI
    veri = {
        "_nasil": "python3 tools/kalem-senkron-kapisi.py --taban-yaz  (ELLE YAZILMAZ)",
        "menzil_disi": o["menzil_disi"],
        "menzil_disi_ids": o["menzil_disi_ids"],
        "kaynak_dogrusu_satir": o["kaynak_dogrusu_satir"],
        "kaynak_dogrusu_benzersiz_id": o["kaynak_dogrusu_benzersiz_id"],
        "devam_md_benzersiz_id": o["devam_md_benzersiz_id"],
    }
    if gerekce:
        veri["yukseltme_gerekcesi"] = gerekce
    with open(taban_yolu, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    print("TABAN YAZILDI (olculerek) — MENZIL_DISI=%d dosya=%s"
          % (o["menzil_disi"], taban_yolu))
    return RC_GECTI


# ── HUKUM KOLLARI ────────────────────────────────────────────────────────────────
def canli():
    o = olc()
    taban = taban_oku()
    eski_ids = set(taban["menzil_disi_ids"])
    yeni = [k for k in o["menzil_disi_ids"] if k not in eski_ids]
    print("KALEM-SENKRON CANLI — MENZIL_DISI=%d TABAN=%d YENI=%d"
          % (o["menzil_disi"], taban["menzil_disi"], len(yeni)))
    asildi = o["menzil_disi"] > taban["menzil_disi"]
    if asildi:
        print("KIRMIZI — TABAN ASILDI: kaynak-dogrusunda satiri OLMAYAN kalem sayisi "
              "%d -> %d. Yeni id(ler): %s"
              % (taban["menzil_disi"], o["menzil_disi"],
                 ", ".join(yeni) or "(sayi artti, id kumesi degismedi)"))
        print("CARE: kalemi `acik-kalemler.md` tablosuna SATIR olarak ac (durum + `kabul:` "
              "alani). Kaynak-dogrusunda satiri olmayan kalem nobet tarafindan OLCULEMEZ.")
        return RC_TABAN_ASILDI
    print("GECTI — taban asilmadi (ratchet). Yeni id: %s" % (", ".join(yeni) or "yok"))
    return RC_GECTI


def rapor():
    o = olc()
    print("═══ K309 KAPSAM ON-OLCUMU (olculdu, oncul DEGIL) ═══")
    print("KAYNAK_DOGRUSU_SATIR=%d" % o["kaynak_dogrusu_satir"])
    print("KAYNAK_DOGRUSU_BENZERSIZ_ID=%d" % o["kaynak_dogrusu_benzersiz_id"])
    print("KAYNAK_DOGRUSU_MUKERRER_SATIR=%d" % o["kaynak_dogrusu_mukerrer"])
    print("DEVAM_MD_BENZERSIZ_ID=%d" % o["devam_md_benzersiz_id"])
    print("MENZIL_ICI=%d" % o["menzil_ici"])
    print("MENZIL_DISI=%d" % o["menzil_disi"])
    print("MENZIL_DISI_IDLER=%s" % ", ".join(o["menzil_disi_ids"]))
    kovalar = {}
    kabul_var = 0
    for kid, v in o["menzil_disi_kayit"].items():
        kovalar.setdefault(v["isaret"], []).append(kid)
        if v["kabul_var"]:
            kabul_var += 1
    print("─── DURUM KIRILIMI (DEVAM.md metnindeki isaret) ───")
    for isaret in sorted(kovalar, key=lambda i: (-len(kovalar[i]), i)):
        idler = sorted(kovalar[isaret], key=lambda k: int(k[1:]))
        print("KOVA %-10s = %3d  %s" % (isaret, len(idler), ", ".join(idler)))
    toplam = sum(len(v) for v in kovalar.values())
    print("KOVA_TOPLAM=%d (MENZIL_DISI ile esit olmali: %s)"
          % (toplam, "EVET" if toplam == o["menzil_disi"] else "HAYIR"))
    print("─── MAKINE-OKUNUR `kabul:` ALANI (BLOK duzeyi = UST SINIR) ───")
    print("KABUL_VAR=%d" % kabul_var)
    print("KABUL_YOK=%d" % (o["menzil_disi"] - kabul_var))
    return RC_GECTI


# ── FIKSTURLER + KENDINI TEST ────────────────────────────────────────────────────
# Defter fiksturu BILEREK mukerrer satir tasir (K20 iki kez) — canli defterde olculen
# hal budur (K29 iki satir) ve `satir != benzersiz` ayrimi V9 ile civilenir.
_FIK_DEFTER = """# fikstur defter
| id | durum |
|---|---|
| K20 | ACIK |
| K20 | ACIK (mukerrer) |
| K21 | ACIK |
| K99 | KAPANDI |
"""

_FIK_DEVAM_AYRISIK = """# fikstur DEVAM
- 🔴 **K20:** defterde VAR.
- 🔧 **K500:** defterde YOK. kabul: `python3 /tam/yol.py`
- ✅ **K501:** defterde YOK, kabul alani YOK.
- 🟠 **K502** defterde YOK, kabul alani YOK.
"""

_FIK_DEVAM_TEMIZ = """# fikstur DEVAM
- 🔴 **K20:** defterde VAR.
- 🔧 **K21:** defterde VAR.
- ✅ **K99:** defterde VAR.
"""

_FIK_DEVAM_TASAN = """# fikstur DEVAM
- 🔴 **K20:** defterde VAR.
- 🔧 **K500:** YOK.
- 🔧 **K501:** YOK.
- 🔧 **K502:** YOK.
- 🔧 **K503:** YOK.
"""


def _kos(kok, defter, devam, taban, bayraklar, betik=None):
    """Kapiyi ALT SUREC olarak kosturur — rc GERCEKTEN olculur, taklit edilmez."""
    ort = dict(os.environ)
    for anahtar, deger in (("PRUVO_KALEM_DEFTER", defter),
                           ("PRUVO_KALEM_DEVAM", devam),
                           ("PRUVO_KALEM_TABAN", taban)):
        if deger is None:
            ort.pop(anahtar, None)
        else:
            ort[anahtar] = deger
    p = subprocess.run(
        [sys.executable, betik or os.path.abspath(__file__)] + list(bayraklar),
        cwd=kok, env=ort, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _fikstur_kur(kok):
    yol = {}
    for ad, icerik in (("defter.md", _FIK_DEFTER),
                       ("devam-ayrisik.md", _FIK_DEVAM_AYRISIK),
                       ("devam-temiz.md", _FIK_DEVAM_TEMIZ),
                       ("devam-tasan.md", _FIK_DEVAM_TASAN)):
        p = os.path.join(kok, ad)
        with open(p, "w", encoding="utf-8") as f:
            f.write(icerik)
        yol[ad] = p
    for ad, sayi, idler in (("taban-3.json", 3, ["K500", "K501", "K502"]),
                            ("taban-0.json", 0, [])):
        p = os.path.join(kok, ad)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"menzil_disi": sayi, "menzil_disi_ids": idler}, f)
        yol[ad] = p
    yol["_yok_"] = os.path.join(kok, "olmayan-dizin", "olmayan.md")
    return yol


def vakalar(kok, betik=None):
    """[(ad, gecti, detay)] — HERMETIK: ag ve dis dosya ISTEMEZ."""
    f = _fikstur_kur(kok)
    sonuc = []

    def ekle(ad, kosul, detay):
        sonuc.append((ad, bool(kosul), detay))

    # V1 — MENZIL DISI VAR: uc id (K500/K501/K502) defterde YOK, sayilir ve ADIYLA basilir.
    rc, cikti = _kos(kok, f["defter.md"], f["devam-ayrisik.md"], f["taban-3.json"],
                     ["--rapor"], betik)
    ekle("V1 MENZIL DISI VAR -> MENZIL_DISI=3 + id'ler ADIYLA, MENZIL_ICI=1",
         rc == RC_GECTI and "MENZIL_DISI=3" in cikti and "MENZIL_ICI=1" in cikti
         and "K500" in cikti and "K501" in cikti and "K502" in cikti,
         (rc, cikti[-240:]))

    # V2 — MENZIL DISI YOK: DEVAM'daki her id defterde VAR -> 0 (defter ayristirmasi calisir).
    rc, cikti = _kos(kok, f["defter.md"], f["devam-temiz.md"], f["taban-0.json"],
                     ["--rapor"], betik)
    ekle("V2 MENZIL DISI YOK -> MENZIL_DISI=0 ve MENZIL_ICI=3",
         rc == RC_GECTI and "MENZIL_DISI=0" in cikti and "MENZIL_ICI=3" in cikti,
         (rc, cikti[-240:]))

    # V3 — TABAN ESIT: 3 == 3 -> GECER (bugunku ayrisma kataloju ANINDA yakmaz).
    rc, cikti = _kos(kok, f["defter.md"], f["devam-ayrisik.md"], f["taban-3.json"],
                     [], betik)
    ekle("V3 TABAN ESIT (3==3) -> rc 0 GECTI (ambiyans kirmizisi YOK)",
         rc == RC_GECTI and "GECTI" in cikti and "TABAN=3" in cikti,
         (rc, cikti[-240:]))

    # V4 — TABAN ASILDI: 4 > 3 -> KIRMIZI + YENI id (K503) ADIYLA.
    rc, cikti = _kos(kok, f["defter.md"], f["devam-tasan.md"], f["taban-3.json"],
                     [], betik)
    ekle("V4 TABAN ASILDI (4>3) -> rc %d KIRMIZI + yeni id K503 ADIYLA" % RC_TABAN_ASILDI,
         rc == RC_TABAN_ASILDI and "TABAN ASILDI" in cikti and "K503" in cikti,
         (rc, cikti[-240:]))

    # V5 — 🔴 DUZLEM YOK (memory dizini CI'da yok): `OLCULEMEDI` + SIFIR-DISI rc.
    #      SESSIZ YESIL DONMEZ ([[olculemedi-bypass-degil-menzil-daraltmasi]]).
    rc, cikti = _kos(kok, f["_yok_"], f["devam-ayrisik.md"], f["taban-3.json"], [], betik)
    ekle("V5 DEFTER DUZLEMI YOK -> 'OLCULEMEDI' jetonu VE rc!=0 (sessiz yesil YASAK)",
         rc != RC_GECTI and rc == RC_OLCULEMEDI_DUZLEM and "OLCULEMEDI" in cikti,
         (rc, cikti[-240:]))

    # V5b — ayni kol `--rapor`da da fail-closed (kol TEK cagri yerinde degil).
    rc, cikti = _kos(kok, f["_yok_"], f["devam-ayrisik.md"], f["taban-3.json"],
                     ["--rapor"], betik)
    ekle("V5b DUZLEM YOK + --rapor -> yine 'OLCULEMEDI' + rc!=0",
         rc == RC_OLCULEMEDI_DUZLEM and "OLCULEMEDI" in cikti, (rc, cikti[-240:]))

    # V6 — TABAN DOSYASI YOK: tabansiz hukum verilmez, AYRI rc ile fail-closed.
    rc, cikti = _kos(kok, f["defter.md"], f["devam-ayrisik.md"], f["_yok_"], [], betik)
    ekle("V6 TABAN DOSYASI YOK -> 'OLCULEMEDI' + rc %d (duzlem rc'sinden AYRI)"
         % RC_OLCULEMEDI_TABAN,
         rc == RC_OLCULEMEDI_TABAN and "OLCULEMEDI" in cikti, (rc, cikti[-240:]))

    # V7 — DURUM KIRILIMI + `kabul:` sayaci gercekten olculuyor (kova toplami = MENZIL_DISI).
    rc, cikti = _kos(kok, f["defter.md"], f["devam-ayrisik.md"], f["taban-3.json"],
                     ["--rapor"], betik)
    ekle("V7 DURUM KIRILIMI: 🔧/✅/🟠 kovalari 1'er · KOVA_TOPLAM=3 · KABUL_VAR=1 KABUL_YOK=2",
         rc == RC_GECTI and "KOVA 🔧" in cikti and "KOVA ✅" in cikti
         and "KOVA 🟠" in cikti and "KOVA_TOPLAM=3" in cikti
         and "KABUL_VAR=1" in cikti and "KABUL_YOK=2" in cikti,
         (rc, cikti[-400:]))

    # V8 — rc'ler BIRBIRINDEN AYRI: hicbir hal otekine karismaz.
    ekle("V8 rc kumesi AYRI: GECTI=0 · TABAN_ASILDI=1 · OLCULEMEDI_DUZLEM=3 · "
         "OLCULEMEDI_TABAN=4",
         len({RC_GECTI, RC_TABAN_ASILDI, RC_OLCULEMEDI_DUZLEM, RC_OLCULEMEDI_TABAN}) == 4,
         (RC_GECTI, RC_TABAN_ASILDI, RC_OLCULEMEDI_DUZLEM, RC_OLCULEMEDI_TABAN))

    # V9 — MUKERRER SATIR: `satir` ile `benzersiz id` AYRI olculur (canli defterde K29
    #      iki satir; tek sayi ikisini birden temsil ETMEZ).
    rc, cikti = _kos(kok, f["defter.md"], f["devam-ayrisik.md"], f["taban-3.json"],
                     ["--rapor"], betik)
    ekle("V9 MUKERRER SATIR AYRI OLCULUR: SATIR=4 · BENZERSIZ_ID=3 · MUKERRER=1",
         rc == RC_GECTI and "KAYNAK_DOGRUSU_SATIR=4" in cikti
         and "KAYNAK_DOGRUSU_BENZERSIZ_ID=3" in cikti
         and "KAYNAK_DOGRUSU_MUKERRER_SATIR=1" in cikti,
         (rc, cikti[-300:]))
    return sonuc


def _kisa(vaka_adi):
    return vaka_adi.split()[0]


def kendini_test():
    with tempfile.TemporaryDirectory(prefix="kalem-senkron-") as kok:
        sonuclar = vakalar(kok)
    gecti = sum(1 for _, g, _ in sonuclar if g)
    for ad, g, detay in sonuclar:
        print("  %s %s" % ("✔" if g else "✘", ad))
        if not g:
            print("      DETAY: %r" % (detay,))
    kaldi = len(sonuclar) - gecti
    print("KALEM-SENKRON KENDINI-TEST — IDDIA=%d GECTI=%d KALDI=%d HUKUM=%s"
          % (len(sonuclar), gecti, kaldi, "YESIL" if kaldi == 0 else "KIRMIZI"))
    return RC_GECTI if kaldi == 0 else RC_TEST_KIRMIZI


# ── MUTASYON ─────────────────────────────────────────────────────────────────────
# Her mutant HANGI vakayi oldurdugunu AYRICA kanitlar ([[K182]]): "kirmizi geldi"
# kanit degildir, kirmizinin SEBEBI hedef kol olmalidir. Ayrica IZOLASYON olculur:
# hedef disindaki vakalar YASAMALI, yoksa mutant "her seyi kirmiziya yakan" bir
# alarmdir ve hicbir kolu KANITLAMAZ. Mutasyon GECICI KOPYADA kosar — canli dosyaya
# (ne kapiya, ne acik-kalemler.md'ye) ASLA dokunulmaz.
MUTANTLAR = [
    ("M1 OLCULEMEDI kolu SESSIZ YESILE cevrilir (duzlem/taban yoksa rc 0 doner) — "
     "yani 'CI'da dizin yok' hali sessizce gecer",
     "        self.rc = rc",
     "        self.rc = RC_GECTI",
     ("V5", "V5b", "V6"),
     ("V1", "V2", "V3", "V4", "V7", "V8", "V9")),

    ("M2 TABAN RATCHET kolu kaldirilir (`menzil_disi > taban` -> her zaman False) — "
     "yani ayrisma buyuse de kapi susar",
     '    asildi = o["menzil_disi"] > taban["menzil_disi"]',
     "    asildi = False",
     ("V4",),
     ("V1", "V2", "V3", "V5", "V5b", "V6", "V7", "V8", "V9")),
]

# KONTROL MUTANTI: ILGISIZ ve GERCEK bir kol bozulur — `--taban-yaz`in "tabani
# yukseltmek gerekce ister" ratchet reddi. Hicbir V vakasi `--taban-yaz` kosmaz,
# dolayisiyla vakalar TAUTOLOJI degilse HEPSI YESIL kalmali. Kalirlarsa batarya
# "her mutasyonda kirmizi yanan" bir alarm DEGILDIR.
KONTROL = (
    "KONTROL: `--taban-yaz` ratchet reddi (`taban yukseltmek gerekce ister`) devre "
    "disi birakilir — ILGISIZ kol; TUM vakalar YESIL kalmali",
    '    if eski is not None and o["menzil_disi"] > eski["menzil_disi"] and not gerekce:',
    "    if False:",
)


# 🔴 CAPA MENZILI GOVDEYLE SINIRLIDIR ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
# OLCULDU (ilk kosum): her capa dosyada IKI kez gecer — biri GERCEK kod, oteki bu
# bolumdeki MUTANTLAR/KONTROL tablosunda duran METIN kopyasi. `count != 1` kolu o yuzden
# ucunu birden "CAPA COKMESI" ile dusurdu. Care capayi gevsetmek DEGIL (o, mutasyon
# tablosundaki metni de mutasyona ugratir ve mutantı anlamsiz kilar), MENZILI DARALTMAK:
# ikame yalnizca SINIR jetonundan ONCEKI govdeye uygulanir, tablo bolumu DOKUNULMAZ.
# SINIR jetonu parcali kuruldu ki jetonun KENDISI dosyada iki kez gecmesin.
_MUTASYON_SINIRI = "MUTANT" + "LAR = ["


def _mutant_kopya(kok, eski, yeni, ad):
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        kaynak = f.read()
    kesim = kaynak.find(_MUTASYON_SINIRI)
    if kesim < 0 or kaynak.count(_MUTASYON_SINIRI) != 1:
        return None, ("SINIR JETONU BOZUK — %r dosyada %d kez gecti (1 bekleniyor); "
                      "capa menzili olculemez (fail-closed)."
                      % (_MUTASYON_SINIRI, kaynak.count(_MUTASYON_SINIRI)))
    govde, kuyruk = kaynak[:kesim], kaynak[kesim:]
    if govde.count(eski) != 1:
        return None, ("CAPA COKMESI — mutant %s icin capa GOVDEDE %d kez bulundu "
                      "(1 bekleniyor): %r" % (ad, govde.count(eski), eski))
    hedef = os.path.join(kok, "mutant.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni) + kuyruk)
    return hedef, None


def mutasyon():
    tum_yesil = True
    with tempfile.TemporaryDirectory(prefix="kalem-senkron-mut-") as kok:
        # 🔴 TABAN ONCE OLCULUR: mutasyondan once vakalarin hepsi yesil OLMALI, yoksa
        #    "mutant oldurdu" hukmu taban kirmizisiyla karisir ([[bayat-taban-hipotezi]]).
        taban_kok = os.path.join(kok, "taban")
        os.makedirs(taban_kok, exist_ok=True)
        taban_sonuc = {_kisa(a): g for a, g, _ in vakalar(taban_kok)}
        if not all(taban_sonuc.values()):
            print("MUTASYON DURDU — TABAN KIRMIZI: %s"
                  % ", ".join(a for a, g in taban_sonuc.items() if not g))
            return RC_TEST_KIRMIZI
        print("  TABAN=%d/%d YESIL (mutasyon oncesi)"
              % (sum(taban_sonuc.values()), len(taban_sonuc)))

        for ad, eski, yeni, olmeli, yasamali in MUTANTLAR:
            alt = os.path.join(kok, "m-" + _kisa(ad))
            os.makedirs(alt, exist_ok=True)
            betik, hata = _mutant_kopya(alt, eski, yeni, _kisa(ad))
            if hata:
                print("  ✘ %s\n      %s" % (ad, hata))
                tum_yesil = False
                continue
            sonuc = {_kisa(a): g for a, g, _ in vakalar(alt, betik)}
            oldu = [v for v in olmeli if not sonuc.get(v, True)]
            sagkalan = [v for v in olmeli if sonuc.get(v, False)]
            izolasyon = [v for v in yasamali if not sonuc.get(v, False)]
            ok = not sagkalan and not izolasyon
            tum_yesil = tum_yesil and ok
            print("  %s %s" % ("✔" if ok else "✘", ad))
            print("      HEDEF KOL OLDU: %s" % (", ".join(oldu) or "(HICBIRI!)"))
            print("      IZOLASYON: %d/%d vaka YASADI"
                  % (len(yasamali) - len(izolasyon), len(yasamali)))
            if sagkalan:
                print("      🔴 HEDEF VAKA SAGKALDI: %s — mutant hedef kolu OLDURMEDI"
                      % ", ".join(sagkalan))
            if izolasyon:
                print("      🔴 IZOLASYON BOZUK (yan hasar): %s" % ", ".join(izolasyon))

        ad, eski, yeni = KONTROL
        alt = os.path.join(kok, "m-kontrol")
        os.makedirs(alt, exist_ok=True)
        betik, hata = _mutant_kopya(alt, eski, yeni, "KONTROL")
        if hata:
            print("  ✘ %s\n      %s" % (ad, hata))
            tum_yesil = False
        else:
            sonuc = {_kisa(a): g for a, g, _ in vakalar(alt, betik)}
            olen = [v for v, g in sonuc.items() if not g]
            ok = not olen
            tum_yesil = tum_yesil and ok
            print("  %s %s" % ("✔" if ok else "✘", ad))
            print("      KONTROL=%s%s" % ("YESIL" if ok else "KIRMIZI",
                                          "" if ok else " — olen: " + ", ".join(olen)))
    print("KALEM-SENKRON MUTASYON — MUTANT=%d KONTROL=1 HUKUM=%s"
          % (len(MUTANTLAR), "YESIL" if tum_yesil else "KIRMIZI"))
    return RC_GECTI if tum_yesil else RC_TEST_KIRMIZI


# ── GIRIS ────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Kalem senkron kapisi (K309)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="HERMETIK fikstur bataryasi (CI: nobet.yml serit-b)")
    ap.add_argument("--mutasyon", action="store_true",
                    help="2 hedef-kol atifli mutant + KONTROL mutanti")
    ap.add_argument("--rapor", action="store_true",
                    help="CANLI on-olcum + durum kirilimi + `kabul:` sayaci")
    ap.add_argument("--canli", action="store_true", help="CANLI hukum (varsayilan)")
    ap.add_argument("--taban-yaz", action="store_true",
                    help="Tabani OLCEREK yaz (elle sayi kabul edilmez)")
    ap.add_argument("--gerekce", default=None,
                    help="Tabani YUKSELTMEK icin acik gerekce")
    a = ap.parse_args()

    if a.kendini_test:
        return kendini_test()
    if a.mutasyon:
        return mutasyon()
    try:
        if a.taban_yaz:
            return taban_yaz(a.gerekce)
        if a.rapor:
            return rapor()
        return canli()
    except Olculemedi as e:
        print(str(e))
        return e.rc


if __name__ == "__main__":
    sys.exit(main())
