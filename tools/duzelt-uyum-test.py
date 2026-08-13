#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/duzelt-uyum-test.py — `uyum` YAZMA YOLU kabul testi (tools/duzelt.py).

NE KORUR: `uyum` (urunun NEYE UYDUGU) alani duzelt.py'nin izinli kumesine acildi ve
`marka` artik ondan TURETILIYOR. Bu birlesim SESSIZ HATA sinifidir: `marka` haystack()
uzerinden ARAMA METNINE girer, yani yanlis turetilen bir `marka` hicbir kirmizi
yakmadan 13.040 kayitta arama sonucunu dusurebilir. Bu yuzden turetim ve dogrulama
tek kaynaktan (tools/arama.py) gelir ve burada UCTAN UCA — GERCEK duzelt.py SUREC
olarak kosturularak, GERCEK cikis kodlari ve GERCEK disk sha256'si olculerek — sinanir.

GERCEK urunler.json'a DOKUNULMAZ: her senaryo icin gecici bir SAHTE repo kurulur
(<tmp>/tools/{duzelt,arama,gorsel_koken}.py + <tmp>/urunler.json). duzelt.py yollarini
kendi __file__ konumundan turettigi icin kopya sahte katalog uzerinde calisir.

IDDIALAR (her biri AYRI eksen; her birinin TEK-KIRMIZI mutanti tools/duzelt-uyum-mutasyon.py'de):
  D1  `uyum` TOPLU ve TEKIL yolun IKISINDE de kabul ediliyor (rc=0, disk sha256 DEGISTI)
  D2  Yazimdan sonra `marka` == arama.marka_uyumdan_turet(u) — turetim GERCEKTEN kostu
      (deger BAGIMSIZ CAPA ile karsilastirilir; guard izin manifesti de ayni degeri tasir)
  D3  Ayni cagrida `uyum` + `marka` -> rc=RC_UYUM, disk sha256 DEGISMEDI (iki kaynak yarisamaz)
  D4  1500'luk partinin ICINDEKI TEK kirli kayit TUM partiyi dusuruyor (atomik), disk DEGISMEDI
  D5  `uyum`u DOLU bir kayitta YALNIZ `marka` degistirmek REDDEDILIYOR (K5 sessiz ayrismasi)
  D6  `--alan-sil uyum` rc=0, `marka` AYNEN duruyor, uyum_sebebi YESIL
  D7  Cagrinin DOKUNMADIGI, `uyum`u zaten kirli bir kayit cagriyi DUSURMUYOR (kapi kapsami)
  D8  Dort kapi cikis kodu (gorsel-koken 4 / altkategori 5 / ticari hal 6 / uyum 7) AYRI

🔴 FIKSTUR DISIPLINI ([[fikstur-degeri-mutasyon-koru]]): `uyum`dan TURETILEN `marka`
(TURETILEN) ile elle yazilabilecek "makul" deger (ELLE_MAKUL) BILEREK AYRISIR — `uyum`
bir MODEL jetonu tasir, yalniz markadan turetim onu DUSURUR. Ayrisma olmasaydi
"turetim hic kosmadi" mutanti YESIL gecerdi. Fiksturdeki her ad UYDURMA ya da acik
arac markasidir; gercek tedarikci adi / firma numarasi GIRMEZ.

Kullanim (CI'da BLOKLAYICI, tam takim — alt kume bayragi YOK):
    python3 tools/duzelt-uyum-test.py
Cikis 0 = her iddia olculdu ve gecti.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

# duzelt.py bunlari KOSULSUZ import eder -> sahte repoya da kopyalanmalilar.
YARDIMCILAR = ("gorsel_koken.py", "arama.py")

# 🔴 BAGIMSIZ CAPA — duzelt.RC_UYUM'dan import EDILMEZ. Iki taraf ayni sabiti okusaydi
# kod sessizce degistirilip test yine yesil yanardi ([[kapi-anchor-coupling-ikilemi]]).
# Ayni gerekceyle diger uc kapi kodu da burada ELLE yazilidir.
RC_UYUM = 7
RC_GORSEL_KOKEN = 4
RC_ALTKATEGORI = 5
RC_TICARI_HAL = 6

# ── FIKSTUR ─────────────────────────────────────────────────────────────────────────
# `uyum` ikinci ogeyi MODELSIZ, birincisini MODELLI tutar: turetim marka VE model
# jetonlarini SIRAYLA toplar, yani yalniz markadan turetim gorunur bir fark uretir.
UYUM_GECERLI = [{"marka": "Ford", "model": "Focus", "yil": [2011, 2018]},
                {"marka": "Mini"}]
TURETILEN = ["Ford", "Focus", "Mini"]     # arama.marka_uyumdan_turet(UYUM_GECERLI) BEKLENENI
ELLE_MAKUL = ["Ford", "Mini"]             # elle yazilabilecek "makul" deger — AYRISIR
UYUM_KIRLI = [{"marka": "Sinamarka"}]     # KAPALI kume disi (uydurma) -> uyum_sebebi KIRMIZI

satirlar = []
hatalar = []
kirmizi = set()          # KIRMIZI YANAN IDDIA KODLARI (mutasyon surucusunun olctugu kume)


def kontrol(kod, kosul, mesaj):
    satirlar.append(("  ✔ " if kosul else "  ✘ ") + "%-3s %s" % (kod, mesaj))
    if not kosul:
        kirmizi.add(kod)
        hatalar.append("%s %s" % (kod, mesaj))


# ── sahte repo ──────────────────────────────────────────────────────────────────────
def urun(uid, **ek):
    u = {"id": uid, "kategori": "Otomobil", "marka": [],
         "baslik": "Sinama %s" % uid, "aciklama": "sinama aciklamasi",
         "fiyat": "100 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}
    u.update(ek)
    return u


def sahte_repo(katalog):
    d = tempfile.mkdtemp(prefix="duzelt-uyum-testi-")
    os.makedirs(os.path.join(d, "tools"))
    shutil.copy(os.path.join(TOOLS, "duzelt.py"), os.path.join(d, "tools", "duzelt.py"))
    for ad in YARDIMCILAR:
        shutil.copy(os.path.join(TOOLS, ad), os.path.join(d, "tools", ad))
    shutil.copy(os.path.join(ROOT, "index.html"), os.path.join(d, "index.html"))
    with open(os.path.join(d, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(katalog, f, ensure_ascii=False, indent=2)
    return d


def temizle(*repolar):
    for r in repolar:
        shutil.rmtree(r, ignore_errors=True)


def cagir(repo, *argv):
    """duzelt.py'yi SUREC olarak kostur -> GERCEK cikis kodu (in-process cagri
    cikis kodunu ve argparse davranisini taklit ederdi)."""
    r = subprocess.run([sys.executable, os.path.join(repo, "tools", "duzelt.py")]
                       + list(argv), capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def islem_yaz(repo, islemler):
    yol = os.path.join(repo, "islemler.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(islemler, f, ensure_ascii=False)
    return yol


def kayit(repo, uid):
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        for u in json.load(f):
            if isinstance(u, dict) and u.get("id") == uid:
                return u
    return None


def katalog_hash(repo):
    with open(os.path.join(repo, "urunler.json"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def manifest_oku(repo):
    yol = os.path.join(repo, ".urunler-duzelt-izin.json")
    if not os.path.exists(yol):
        return {}
    with open(yol, encoding="utf-8") as f:
        try:
            m = json.load(f)
        except ValueError:
            return {}
    return m if isinstance(m, dict) else {}


def _arama():
    """Testin KENDI agacindaki arama.py — duzelt.py'nin kullandigi TEK kaynagin ta
    kendisi. (Mutasyon surucusu bu dosyayi mutasyonladiginda test onu OLCER.)"""
    spec = importlib.util.spec_from_file_location(
        "arama_uyum_testi", os.path.join(TOOLS, "arama.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── D1 ──────────────────────────────────────────────────────────────────────────────
def d1_kabul():
    """`uyum` TOPLU VE TEKIL yolun IKISINDE de yazilabiliyor mu?"""
    repo = sahte_repo([urun("uyum-toplu", marka=list(ELLE_MAKUL)),
                       urun("uyum-tekil", marka=list(ELLE_MAKUL))])
    once = katalog_hash(repo)
    yol = islem_yaz(repo, [{"id": "uyum-toplu", "alan": "uyum", "deger": UYUM_GECERLI}])
    rc, cikti = cagir(repo, "--toplu", yol)
    kontrol("D1", rc == 0, "TOPLU yol: gecerli `uyum` KABUL EDILDI (rc=%d)%s"
            % (rc, "" if rc == 0 else " | " + cikti.strip().splitlines()[-1:][0][:120]
               if cikti.strip() else ""))
    kontrol("D1", katalog_hash(repo) != once, "TOPLU yol: urunler.json sha256 DEGISTI")
    kontrol("D1", (kayit(repo, "uyum-toplu") or {}).get("uyum") == UYUM_GECERLI,
            "TOPLU yol: `uyum` degeri diske BIREBIR yazildi")

    once2 = katalog_hash(repo)
    rc2, cikti2 = cagir(repo, "uyum-tekil", "--alan", "uyum",
                        "--deger", json.dumps(UYUM_GECERLI, ensure_ascii=False))
    kontrol("D1", rc2 == 0, "TEKIL yol: gecerli `uyum` KABUL EDILDI (rc=%d)%s"
            % (rc2, "" if rc2 == 0 else " | " + cikti2.strip().splitlines()[-1:][0][:120]
               if cikti2.strip() else ""))
    kontrol("D1", katalog_hash(repo) != once2, "TEKIL yol: urunler.json sha256 DEGISTI")
    kontrol("D1", (kayit(repo, "uyum-tekil") or {}).get("uyum") == UYUM_GECERLI,
            "TEKIL yol: `uyum` degeri diske BIREBIR yazildi")
    temizle(repo)


# ── D2 ──────────────────────────────────────────────────────────────────────────────
def d2_turetim():
    """`marka` GERCEKTEN `uyum`dan mi turedi? Olcu BAGIMSIZ CAPA (TURETILEN sabiti)."""
    repo = sahte_repo([urun("uyum-turetim", marka=list(ELLE_MAKUL))])
    yol = islem_yaz(repo, [{"id": "uyum-turetim", "alan": "uyum", "deger": UYUM_GECERLI}])
    rc, _cikti = cagir(repo, "--toplu", yol)
    k = kayit(repo, "uyum-turetim") or {}
    kontrol("D2", rc == 0, "turetim olculebilmesi icin yazim gecmeli (rc=%d)" % rc)
    kontrol("D2", k.get("marka") == TURETILEN,
            "`marka` uyum'dan TURETILDI: beklenen %s, olculen %s"
            % (json.dumps(TURETILEN, ensure_ascii=False),
               json.dumps(k.get("marka"), ensure_ascii=False)))
    kontrol("D2", TURETILEN != ELLE_MAKUL and k.get("marka") != ELLE_MAKUL,
            "FIKSTUR DISIPLINI: turetilen deger, elle yazilabilecek makul degerden (%s) "
            "AYRISIYOR — 'turetim hic kosmadi' mutanti bu yuzden yesil GECEMEZ"
            % json.dumps(ELLE_MAKUL, ensure_ascii=False))
    kontrol("D2", (manifest_oku(repo).get("uyum-turetim") or {}).get("marka") == TURETILEN,
            "guard IZIN MANIFESTI de TURETILEN degeri tasiyor (yoksa guard turetimi "
            "HEAD'e geri alir ve turetim sessizce ETKISIZ kalirdi)")
    temizle(repo)


# ── D3 ──────────────────────────────────────────────────────────────────────────────
def d3_iki_kaynak():
    """`uyum` + `marka` ayni cagrida -> RC_UYUM, disk DOKUNULMAMIS."""
    repo = sahte_repo([urun("uyum-catisma", marka=list(ELLE_MAKUL))])
    once = katalog_hash(repo)
    yol = islem_yaz(repo, [
        {"id": "uyum-catisma", "alan": "uyum", "deger": UYUM_GECERLI},
        {"id": "uyum-catisma", "alan": "marka", "deger": ["Ford"]},
    ])
    rc, cikti = cagir(repo, "--toplu", yol)
    kontrol("D3", rc == RC_UYUM,
            "ayni cagrida `uyum`+`marka` -> rc=%d (beklenen RC_UYUM=%d)" % (rc, RC_UYUM))
    kontrol("D3", katalog_hash(repo) == once, "disk sha256 DEGISMEDI")
    kontrol("D3", (kayit(repo, "uyum-catisma") or {}).get("marka") == ELLE_MAKUL
            and (kayit(repo, "uyum-catisma") or {}).get("uyum") is None,
            "kayit HIC dokunulmadan kaldi (ne `marka` ne `uyum`)")
    kontrol("D3", "uyum-catisma" in cikti,
            "reddedilen kayit ciktida ADIYLA gecti (sessiz red yok)")
    temizle(repo)


# ── D4 ──────────────────────────────────────────────────────────────────────────────
PARTI_BOYU = 1500


def d4_atomik():
    """1500'luk partinin ICINDEKI tek kirli kayit TUM partiyi dusurur mu?"""
    katalog = [urun("parti-%04d" % i, marka=list(ELLE_MAKUL)) for i in range(PARTI_BOYU)]
    repo = sahte_repo(katalog)
    once = katalog_hash(repo)
    islemler = [{"id": "parti-%04d" % i, "alan": "uyum", "deger": UYUM_GECERLI}
                for i in range(PARTI_BOYU)]
    islemler[750] = {"id": "parti-0750", "alan": "uyum", "deger": UYUM_KIRLI}
    yol = islem_yaz(repo, islemler)
    rc, cikti = cagir(repo, "--toplu", yol)
    kontrol("D4", rc == RC_UYUM, "%d islemlik partide TEK kirli kayit -> rc=%d "
            "(beklenen RC_UYUM=%d)" % (PARTI_BOYU, rc, RC_UYUM))
    kontrol("D4", katalog_hash(repo) == once,
            "ATOMIK: disk sha256 DEGISMEDI (parti diske hic dokunmadi)")
    kontrol("D4", (kayit(repo, "parti-0000") or {}).get("uyum") is None
            and (kayit(repo, "parti-1499") or {}).get("uyum") is None,
            "partinin TEMIZ kayitlari da yazilmadi (ya hep ya hic)")
    kontrol("D4", "parti-0750" in cikti,
            "reddedilen kayit ciktida ADIYLA gecti (hangi kayit oldugu gorunuyor)")
    temizle(repo)


# ── D5 ──────────────────────────────────────────────────────────────────────────────
def d5_marka_elle():
    """`uyum` DOLU bir kayitta YALNIZ `marka` degistirmek -> K5 ikiz ayrismasi REDDEDILIR.

    Yazilan deger (["Yanmar"]) HERHANGI bir turetimin sonucuna ESIT DEGILDIR: boylece
    'turetim daraltildi' sinifindan bir mutant bu iddiayi tesadufen yesile ceviremez.
    """
    for kip in ("TOPLU", "TEKIL"):
        repo = sahte_repo([urun("uyum-dolu", marka=list(TURETILEN), uyum=UYUM_GECERLI)])
        if kip == "TOPLU":
            yol = islem_yaz(repo, [{"id": "uyum-dolu", "alan": "marka",
                                    "deger": ["Yanmar"]}])
            rc, _cikti = cagir(repo, "--toplu", yol)
        else:
            rc, _cikti = cagir(repo, "uyum-dolu", "--alan", "marka",
                               "--deger", '["Yanmar"]')
        kontrol("D5", rc == RC_UYUM,
                "%s yol: uyum DOLU kayitta yalniz `marka` degistirmek REDDEDILDI "
                "(rc=%d, beklenen RC_UYUM=%d)" % (kip, rc, RC_UYUM))
        kontrol("D5", (kayit(repo, "uyum-dolu") or {}).get("marka") == TURETILEN,
                "%s yol: `marka` diskte DEGISMEDI" % kip)
        temizle(repo)


# ── D6 ──────────────────────────────────────────────────────────────────────────────
def d6_alan_sil():
    """`--alan-sil uyum` GECERLI kalir ve `marka`ya DOKUNMAZ."""
    arama = _arama()
    repo = sahte_repo([urun("uyum-silinecek", marka=list(TURETILEN), uyum=UYUM_GECERLI)])
    yol = islem_yaz(repo, [{"id": "uyum-silinecek", "alan-sil": "uyum"}])
    rc, _cikti = cagir(repo, "--toplu", yol)
    k = kayit(repo, "uyum-silinecek") or {}
    kontrol("D6", rc == 0, "--alan-sil uyum rc=0 (olculen %d)" % rc)
    kontrol("D6", "uyum" not in k, "`uyum` alani kayittan KALKTI")
    kontrol("D6", k.get("marka") == TURETILEN,
            "`marka` AYNEN duruyor (eski kayit sekline donus MESRUDUR): olculen %s"
            % json.dumps(k.get("marka"), ensure_ascii=False))
    kontrol("D6", arama.uyum_sebebi(k) is None,
            "silme sonrasi uyum_sebebi YESIL (sebep: %r)" % (arama.uyum_sebebi(k),))
    temizle(repo)


# ── D7 ──────────────────────────────────────────────────────────────────────────────
def d7_kapsam():
    """Kapi kapsami = DOKUNULAN kayitlar. Ilgisiz eski bir ihlal mesru duzeltmeyi
    bloklamaz (katalog geneli eksen tools/uyum-kapisi.py'nin isidir)."""
    repo = sahte_repo([urun("temiz-kayit", marka=list(ELLE_MAKUL)),
                       urun("kirli-kayit", marka=list(ELLE_MAKUL), uyum=UYUM_KIRLI)])
    once = katalog_hash(repo)
    yol = islem_yaz(repo, [{"id": "temiz-kayit", "alan": "fiyat", "deger": "777 TL"}])
    rc, _cikti = cagir(repo, "--toplu", yol)
    kontrol("D7", rc == 0,
            "DOKUNULMAYAN kirli kayit cagriyi DUSURMEDI (rc=%d)" % rc)
    kontrol("D7", (kayit(repo, "temiz-kayit") or {}).get("fiyat") == "777 TL",
            "ilgisiz mesru duzeltme diske yazildi")
    kontrol("D7", katalog_hash(repo) != once, "urunler.json sha256 DEGISTI")
    kontrol("D7", (kayit(repo, "kirli-kayit") or {}).get("uyum") == UYUM_KIRLI,
            "kirli kayit AYNEN duruyor (cagri onu ne onardi ne bozdu)")
    temizle(repo)


# ── D8 ──────────────────────────────────────────────────────────────────────────────
def d8_cikis_kodlari():
    """Dort kapi, dort AYRI cikis kodu — her biri KENDI ihlaliyle uretilir."""
    olculen = {}

    repo = sahte_repo([urun("koken-kayit")])
    yol = islem_yaz(repo, [{"id": "koken-kayit", "alan": "kategori", "deger": "Skan Art"}])
    olculen["gorsel-koken"], _c = cagir(repo, "--toplu", yol)
    temizle(repo)

    repo = sahte_repo([urun("alt-kayit")])
    yol = islem_yaz(repo, [{"id": "alt-kayit", "alan": "altkategori",
                            "deger": "Sinama Alt Kategori"}])
    olculen["altkategori"], _c = cagir(repo, "--toplu", yol)
    temizle(repo)

    repo = sahte_repo([urun("hal-kayit")])
    yol = islem_yaz(repo, [{"id": "hal-kayit", "alan": "tur", "deger": "sinama-sinifi"}])
    olculen["ticari-hal"], _c = cagir(repo, "--toplu", yol)
    temizle(repo)

    repo = sahte_repo([urun("uyum-kayit")])
    yol = islem_yaz(repo, [{"id": "uyum-kayit", "alan": "uyum", "deger": UYUM_KIRLI}])
    olculen["uyum"], _c = cagir(repo, "--toplu", yol)
    temizle(repo)

    kontrol("D8", olculen["gorsel-koken"] == RC_GORSEL_KOKEN,
            "gorsel-koken ihlali -> rc=%d (beklenen %d)"
            % (olculen["gorsel-koken"], RC_GORSEL_KOKEN))
    kontrol("D8", olculen["altkategori"] == RC_ALTKATEGORI,
            "altkategori ihlali -> rc=%d (beklenen %d)"
            % (olculen["altkategori"], RC_ALTKATEGORI))
    kontrol("D8", olculen["ticari-hal"] == RC_TICARI_HAL,
            "ticari hal ihlali -> rc=%d (beklenen %d)"
            % (olculen["ticari-hal"], RC_TICARI_HAL))
    kontrol("D8", olculen["uyum"] == RC_UYUM,
            "uyum ihlali -> rc=%d (beklenen %d)" % (olculen["uyum"], RC_UYUM))
    kontrol("D8", len(set(olculen.values())) == 4,
            "dort kapi kodu birbirinden AYRI: %s"
            % json.dumps(olculen, ensure_ascii=False, sort_keys=True))


# ── kosum ───────────────────────────────────────────────────────────────────────────
IDDIALAR = (("D1", d1_kabul), ("D2", d2_turetim), ("D3", d3_iki_kaynak),
            ("D4", d4_atomik), ("D5", d5_marka_elle), ("D6", d6_alan_sil),
            ("D7", d7_kapsam), ("D8", d8_cikis_kodlari))


def main():
    print("DUZELT `uyum` YAZMA YOLU KABUL TESTI")
    print("-" * 78)
    for kod, fn in IDDIALAR:
        try:
            fn()
        except Exception as e:                                    # noqa: BLE001
            # Cokme SESSIZ olmasin ve KIRMIZI ile karismasin: kod kirmizi kumeye girer
            # ama gerekcesi ACIKCA "COKTU" yazar (bkz. [[hukum-yanlis-birimde]]).
            kontrol(kod, False, "IDDIA COKTU: %s: %s" % (type(e).__name__, e))
    for s in satirlar:
        print(s)
    print("-" * 78)
    print("IDDIA SAYISI: %d" % len(satirlar))
    print("KIRMIZI IDDIA: %s" % (",".join(sorted(kirmizi)) or "-"))
    if hatalar:
        print("KIRMIZI — %d bulgu:" % len(hatalar))
        for h in hatalar:
            print("  ✘ " + h)
        return 1
    print("YESIL — %d iddia olculdu ve gecti (%d eksen)."
          % (len(satirlar), len(IDDIALAR)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
