#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BAYAT BEYAN KAPISI — depodaki BEYAN ile kodun FIILEN yaptigi ayrisirsa KIRMIZI yakar.

NEDEN VAR (olculdu, 2026-08-04)
-------------------------------
Bu depoda yorumdaki/belgedeki cumle OLCUMUN KAYNAGI sayilir: sonraki turlar ona bakip
karar verir. Bir ifsa/istismar turu, COZULMUS sorunlari COZULMEMIS gibi anlatan dort
beyan olctu. Ikisi bu kapinin ekseninde:

  A  MUSTERI YUZU — `secenekler.js` (tarayiciya INEN dosya) vida ailesi icin fiyat
     formulunun olcuye gore degismedigini soyluyordu. Olculdu: `jenerator/hacim.js`
     vida ailesi bugun cap ve boy degisince farkli hacim uretiyor (dort urun tipinde
     de). Yani yanlis bir fiyat zafiyeti iddiasi musteriye servis ediliyordu.
  B  YONETIM HIZ SINIRI — bir paket belgesi yonetim uclarinin hiz sinirsiz oldugunu
     yaziyordu. Olculdu: `shop/src/yonet.js` giris kolunda pencere basina basarisiz
     deneme tavani + her denemede sabit gecikme + govde boyutu siniri VAR ve fiilen
     cagriliyor.

Ikisi de BAYATLADI cunku beyani olcen HICBIR SEY YOKTU ([[ikiz-tanim-sessiz-ayrisma]]).
Bu kapi o bosluktur: beyan ile davranis birbirinden ayrilirsa CI kirmizi yanar.

IDDIALAR (6 — sayi SABIT, mutant kosumlarinda da 6)
---------------------------------------------------
  A1  jenerator/hacim.js `vida` disa veriliyor ve dort urun tipinde de (cap+boy iki
      olcum noktasi = 12 nokta) SONLU POZITIF hacim uretiyor. FAIL-CLOSED on kosul:
      olculemiyorsa A2/A3/A4 bedavaya gecemez.
  A2  DAVRANIS — vida hacmi OLCUYE DUYARLI: civata cap, civata boy, somun cap, pul cap
      ve mil cap eksenlerinin BESINDE de hacim >%1 degisiyor.
  A3  IKIZ (TEK YONLU IMA) — `secenekler.js` vida icin bir DUYARSIZLIK beyani
      tasiyorsa, olculen davranis da duyarsiz olmalidir. Beyan yoksa iddia bos gecer;
      olduruculugu M1 mutantiyla KANITLANIR (bos gecen iddia OLU iddiadir).
  A4  IKIZ (PER-PARCA) — musteri yorumu cekirdek iddianin ustune "hangi parca BOY'a
      duyarli" AYRINTISI ekliyor (bugun: civata+mil boy'a duyarli, somun+pul yalniz
      cap'e). Bu ayrinti node probe'un OLCTUGU boy duyarliligiyla PARCA-PARCA
      karsilastirilir; yorum "pul boy'a duyarli" gibi yanlis bir ayrinti derse KIRMIZI
      (olduruculugu M7). FAIL-CLOSED: yorum dort parcanin birini adlandirmazsa da
      KIRMIZI (not curumesin). Olduruculugu M7, korlugu M8 kontrolu kanitlar.
  B1  DAVRANIS — shop/src/yonet.js giris kolunda hiz siniri YASIYOR: uc sabit tanimli
      ve POZITIF, bloke yordami tanim DISINDA fiilen cagriliyor, gecikme `await`li.
  B2  IKIZ (TEK YONLU IMA) — izlenen `.md` belgelerinde "yonetim uclari hiz sinirsiz"
      beyani varsa kodda da hiz siniri OLMAMALIDIR. Olduruculugu M3 kanitlar.

🔴 NEDEN TEK YONLU IMA: kural "beyan == davranis" ESITLIGI degildir. Esitlik kurulsaydi
formul bir gun gercekten duyarsizlasinca (regresyon) A3 de A2 ile birlikte kirmizi
yanardi; iki katman ayni anda dusunce hangisinin kirildigi OLCULEMEZDI
([[hukum-yanlis-birimde]]). Bu haliyle her mutant TEK bir iddiayi dusurur ve rapor
hangi eksenin kirildigini birim olarak soyler.

KAPSAM — bu kapi NE OLCMEZ (durustluk)
--------------------------------------
* Ayni turde olculen diger iki bayat beyan (servis-disi recetesi · hukuki acik) bu
  kapiya BAGLANMADI ve bu SESSIZ birakilmadi:
  - Servis-disi recetesi: onarim KARDES DEPODA (`~/dev/pruvo-bot`) ve hukum CANLI
    davranistan verilir. Agsiz/deterministik bir iddiaya cevrilemez — bu depodaki
    hicbir dosya o beyani yalanlayamaz. Baglanabilir olsaydi CI'da ag istegi olurdu.
  - Hukuki acik: zaten NOBETCISI VAR (`tools/cayma-beyani-kapisi.py`, dort beyan
    yuzeyi). Ikinci bir kapi ayni ekseni IKI KEZ sayardi; belgedeki metin artik
    "kapandi + nobetcisi su" diyor ve nobetci dususe kirmizi yakiyor.
* A2/A4 hacmi olcer, FIYATI degil: taban fiyat × hacim orani ayri kapilarda (fiyat
  prova / konfigur) olculur. Buradaki iddia "formul olcuye bakiyor mu" ekseni.
* A4 yorumun PROSE'unu ayristirir (per-parca boy iddiasi): cumleyi virgul/nokta ile
  fragmanlara bolup her fragmanda parca-adi + `boy` jetonu birlikte geciyor mu bakar.
  Katı bir bicim DAYATMAZ (musteri notu prose kalir); yalnizca "boy" iddiasinin
  olcumle celismesini yakalar.
* B1 STRUKTUREL bir olcumdur (kaynak metni), calisma zamani degil: yonet.js bir
  Worker modulu, izole kosumu wrangler ister. Sinir SOYLENIR, gizlenmez.

Offline (ag YOK), depoya DOSYA YAZMAZ. Mutant kosumu GERCEK dosyalari degistirmez:
metin eksenleri BELLEKTE degistirilir, node gerektiren eksen SISTEM gecici dizinine
kopyalanir (kaynak sha256 basta = sonda; --kendini-test bunu kendisi de basar).

Kullanim:
    python3 tools/bayat-beyan-kapisi.py
    python3 tools/bayat-beyan-kapisi.py --kendini-test

Cikis kodlari: 0 = YESIL · 1 = KIRMIZI · 2 = OLCULEMEDI (fail-closed).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
HACIM_YOL = os.path.join(ROOT, "jenerator", "hacim.js")
SECENEKLER_YOL = os.path.join(ROOT, "secenekler.js")
YONET_YOL = os.path.join(ROOT, "shop", "src", "yonet.js")

IDDIA_SAYISI = 6  # SABIT — mutant kosumlarinda da bu kadar iddia olculur.

# --------------------------------------------------------------------------- sozluk
# 🔴 SOZLUK DISIPLINI ([[nobetci-kendi-dosyasinda-sizinti]]): asagidaki desenler YALNIZ
# hedef dosyalarda aranir (secenekler.js / izlenen .md). Bu dosyanin KENDI govdesi
# taranmaz; taransaydi kapi kendi docstring'iyle kirmizi yanardi.

# "vida fiyat/hacim formulu olcuye bakmiyor" ailesindeki beyanlar. TR harfleri
# katlandiktan (asciye indirildikten) SONRA aranir.
DUYARSIZLIK_RE = re.compile(
    r"duyarsiz"
    r"|duyarli\s+degil"
    r"|capa\s+kilitli"
    r"|cakili"
    r"|olcuden\s+bagimsiz"
    r"|capa\s+gore\s+degismiyor"
    r"|olcuye\s+gore\s+degismiyor")
VIDA_RE = re.compile(r"vida")
VIDA_PENCERE = 260  # karakter — "vida" gecen yerin iki yani

# A4 — MUSTERI YORUMUNDAKI "HANGI PARCA NEYE DUYARLI" IDDIASI.
# Yorum, cekirdek iddianin ("olcuye duyarli") ustune HANGI parcanin BOY'a duyarli
# oldugunu da soyluyor. Bu ayrinti node probe'un OLCTUGU boy duyarliligiyla
# AYRISIRSA (or. yorum "pul boy'a duyarli" derse ama olcum 0 gosterirse) kirmizi
# yanmali ([[ikiz-tanim-sessiz-ayrisma]]).
VIDA_PARCALARI = ("civata", "somun", "pul", "mil")
# Yorumdaki per-parca iddiasini bulmak icin: "vida yok" capasindan ileri bir pencere;
# icindeki cumle virgul/noktali-virgul/nokta ile PARCALARA bolunur, her parcada
# ilgili parca-adi + "boy" jetonu birlikte geciyorsa o parca "boy'a duyarli" IDDIA
# edilmis demektir.
VIDA_YOK_CAPA_RE = re.compile(r"vida\s+yok")
VIDA_YOK_ILERI = 320   # karakter — sensitivite cumlesini kapsar, sonrasina tasmaz
BOY_JETON_RE = re.compile(r"\bboy\b")

# "yonetim uclari hiz sinirsiz" ailesindeki beyanlar.
YONETIM_RE = re.compile(r"yonetim\s+uc|yonetim\s+panel|yonet\s+uc")
HIZ_YOK_RE = re.compile(
    r"rate[-\s]?limit'?siz"
    r"|rate[-\s]?limitsiz"
    r"|rate[-\s]?limit\s+yok"
    r"|hiz\s+siniri\s+yok"
    r"|hiz\s+limiti\s+yok"
    r"|hiz\s+sinirsiz")
YONETIM_PENCERE = 240

# B1 — hiz sinirinin yasadigi yer (yapisal capalar).
SABIT_ADLARI = ("GIRIS_PENCERE_MS", "GIRIS_TAVAN", "GIRIS_GECIKME_MS")
BLOKE_ADI = "girisBlokeMi"
GECIKME_CAGRI_RE = re.compile(r"await\s+bekle\s*\(\s*GIRIS_GECIKME_MS\s*\)")

_KATLAMA = {
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
}


def katla(metin):
    """TR harflerini ASCII'ye indirip kucuk harfe cevirir (beyan aramasi icin)."""
    return "".join(_KATLAMA.get(k, k) for k in metin).lower()


def pencereler(metin, capa_re, genislik):
    """`capa_re` gecen her yerin +-genislik karakterlik pencerelerini dondurur."""
    return [metin[max(0, m.start() - genislik):m.end() + genislik]
            for m in capa_re.finditer(metin)]


def parca_boy_iddialari(secenekler_metni):
    """Musteri yorumundan per-parca BOY duyarliligi iddiasini cikarir.

    Donen: {parca: True/False} — yorumun o parca icin "boy'a duyarli" DEDIGI.
    Parca yorumda gecmiyorsa anahtar YOK (iddia edilmemis). Anlam:
      True  = yorum bu parcayi boy'a duyarli SAYIYOR
      False = yorum bu parcayi (boy'suz) yalniz cap'e duyarli SAYIYOR

    Cumle virgul/noktali-virgul/nokta ile bolunur; her fragmanda gecen parca-adi,
    o fragmanda `\\bboy\\b` jetonu VARSA boy-duyarli iddia edilmis sayilir. Boylece
    "civata ve mil cap+boy'a" fragmani civata+mil'i boy-duyarli, "somun ve pul yalniz
    cap'e" fragmani somun+pul'u cap-yalniz isaretler.
    """
    k = katla(secenekler_metni)
    m = VIDA_YOK_CAPA_RE.search(k)
    if not m:
        return {}
    bolge = k[m.start():m.start() + VIDA_YOK_ILERI]
    iddialar = {}
    for fragman in re.split(r"[,;.]", bolge):
        boy_var = bool(BOY_JETON_RE.search(fragman))
        for parca in VIDA_PARCALARI:
            if re.search(r"\b%s\b" % parca, fragman):
                # Ayni parca birden cok fragmanda gecerse "boy'a duyarli" diyen
                # fragman baskin (fail-loud: yanlis boy iddiasi gizlenmesin).
                iddialar[parca] = iddialar.get(parca, False) or boy_var
    return iddialar


# --------------------------------------------------------------------------- probe
PROBE = r"""
const H = require(%(hacim)s);
if (!H || typeof H.vida !== "function") {
  console.log(JSON.stringify({ vidaVar: false }));
} else {
  const v = (t, cap, boy) => H.vida({ urun_tipi: t, cap: cap, boy: boy });
  console.log(JSON.stringify({
    vidaVar: true,
    civata_kucuk: v("civata", 5, 20),
    civata_buyuk: v("civata", 12, 20),
    civata_uzun:  v("civata", 5, 40),
    somun_kucuk:  v("somun", 5, 20),
    somun_buyuk:  v("somun", 12, 20),
    somun_uzun:   v("somun", 5, 40),
    pul_kucuk:    v("pul", 5, 20),
    pul_buyuk:    v("pul", 12, 20),
    pul_uzun:     v("pul", 5, 40),
    mil_kucuk:    v("mil", 5, 20),
    mil_buyuk:    v("mil", 12, 20),
    mil_uzun:     v("mil", 5, 40),
  }));
}
"""


class Olculemedi(Exception):
    """Fail-closed: bir eksen OLCULEMEDI. YESIL veremeyiz, KIRMIZI da diyemeyiz."""


def hacim_probe(hacim_yol):
    """hacim.js'i node ile yukleyip vida hacimlerini olcer (ag YOK)."""
    betik = PROBE % {"hacim": json.dumps(hacim_yol)}
    with tempfile.NamedTemporaryFile("w", suffix=".cjs", encoding="utf-8",
                                     delete=False) as f:
        f.write(betik)
        yol = f.name
    try:
        r = subprocess.run([os.environ.get("NODE", "node"), yol],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise Olculemedi("node kosturulamadi (%s) — vida davranisi olculemedi; "
                         "deploy.yml setup-node BLOKLAYICI on-kosuldur." % e)
    finally:
        try:
            os.unlink(yol)
        except OSError:
            pass
    if r.returncode != 0:
        raise Olculemedi("node probe'u kosmadi (exit %d): %s"
                         % (r.returncode, (r.stderr or r.stdout or "")[:800]))
    satirlar = (r.stdout or "").strip().splitlines()
    if not satirlar:
        raise Olculemedi("node probe'u bos cikti verdi.")
    try:
        return json.loads(satirlar[-1])
    except ValueError as e:
        raise Olculemedi("probe ciktisi ayristirilamadi: %s" % e)


def _sonlu_pozitif(x):
    return isinstance(x, (int, float)) and x == x and abs(x) != float("inf") and x > 0


def _ayrisiyor(a, b, esik=0.01):
    """Iki hacim BIRBIRINDEN farkli mi (goreli fark > esik)? Float gurultusu degil."""
    if not (_sonlu_pozitif(a) and _sonlu_pozitif(b)):
        return False
    return abs(a - b) / max(a, b) > esik


# --------------------------------------------------------------------------- kosum
def kosum(probe, secenekler, yonet, belgeler):
    """Alti iddiayi olcer. (hatalar, rapor) dondurur; hatalar bos = YESIL.

    belgeler: {gorunur_yol: metin} — izlenen .md govdeleri.
    """
    hatalar, rapor = [], []

    def ol(kod, aciklama, gecti, kanit=""):
        rapor.append("  %-4s %-64s %s%s"
                     % (kod, aciklama, "✔" if gecti else "✘",
                        ("  " + kanit) if kanit else ""))
        if not gecti:
            hatalar.append("%s %s%s" % (kod, aciklama, ("  -> " + kanit) if kanit else ""))

    # ============================================ A — VIDA FIYAT BEYANI (MUSTERI YUZU)
    rapor.append("A) VIDA OLCU DUYARLILIGI (jenerator/hacim.js  <->  secenekler.js beyani)")

    olculenler = ["civata_kucuk", "civata_buyuk", "civata_uzun",
                  "somun_kucuk", "somun_buyuk", "somun_uzun",
                  "pul_kucuk", "pul_buyuk", "pul_uzun",
                  "mil_kucuk", "mil_buyuk", "mil_uzun"]
    vida_var = bool(probe.get("vidaVar"))
    bozuk = [ad for ad in olculenler if not _sonlu_pozitif(probe.get(ad))]
    ol("A1", "hacim.js `vida` disa veriliyor, 12 olcum noktasi SONLU POZITIF",
       vida_var and not bozuk,
       "" if (vida_var and not bozuk)
       else ("vida disa verilmemis" if not vida_var else "bozuk nokta: %s" % bozuk))

    eksenler = {
        "civata/cap": ("civata_kucuk", "civata_buyuk"),
        "civata/boy": ("civata_kucuk", "civata_uzun"),
        "somun/cap": ("somun_kucuk", "somun_buyuk"),
        "pul/cap": ("pul_kucuk", "pul_buyuk"),
        "mil/cap": ("mil_kucuk", "mil_buyuk"),
    }
    duyarsiz_eksenler = [ad for ad, (a, b) in eksenler.items()
                         if not _ayrisiyor(probe.get(a), probe.get(b))]
    fiilen_duyarli = vida_var and not bozuk and not duyarsiz_eksenler
    ol("A2", "DAVRANIS: vida hacmi 5 eksende de OLCUYE DUYARLI (>%1 degisim)",
       fiilen_duyarli,
       "" if fiilen_duyarli else "degismeyen eksen: %s" % (duyarsiz_eksenler or "olculemedi"))

    sec = katla(secenekler)
    beyan_pencereleri = [p for p in pencereler(sec, VIDA_RE, VIDA_PENCERE)
                         if DUYARSIZLIK_RE.search(p)]
    beyan_var = bool(beyan_pencereleri)
    # TEK YONLU IMA: beyan VARSA davranis da duyarsiz OLMALI.
    a3 = (not beyan_var) or (not fiilen_duyarli)
    ol("A3", "IKIZ: secenekler.js duyarsizlik beyani <-> olculen davranis AYRISMIYOR",
       a3,
       "beyan yok (davranis: %s)" % ("DUYARLI" if fiilen_duyarli else "duyarsiz")
       if not beyan_var
       else ("beyan VAR ama davranis DUYARLI — musteri yuzu dosyada BAYAT iddia: %r"
             % (beyan_pencereleri[0][-120:],) if fiilen_duyarli else "beyan davranisla uyumlu"))

    # A4 — PER-PARCA BOY IDDIASI <-> OLCULEN BOY DUYARLILIGI (musteri yorumu ayrintisi).
    # Cekirdek "olcuye duyarli" iddiasi A2/A3'te; A4 yorumun EKLEDIGI "hangi parca BOY'a
    # duyarli" ayrintisini olcumle karsilastirir. Yorum "pul boy'a duyarli" derse ama
    # olcum bunu 0 gosterirse -> BAYAT ayrinti -> KIRMIZI.
    olculen_boy = {
        "civata": _ayrisiyor(probe.get("civata_kucuk"), probe.get("civata_uzun")),
        "somun": _ayrisiyor(probe.get("somun_kucuk"), probe.get("somun_uzun")),
        "pul": _ayrisiyor(probe.get("pul_kucuk"), probe.get("pul_uzun")),
        "mil": _ayrisiyor(probe.get("mil_kucuk"), probe.get("mil_uzun")),
    }
    iddia_boy = parca_boy_iddialari(secenekler)
    eksik_parca = [p for p in VIDA_PARCALARI if p not in iddia_boy]
    ayrisan = [p for p in VIDA_PARCALARI
               if p in iddia_boy and iddia_boy[p] != olculen_boy[p]]
    # 🔴 BIRIM AYRIMI ([[hukum-yanlis-birimde]]): A4, davranis GENELDE duyarliyken
    # (A2 yesil) per-parca AYRINTIYI olcer. Formul topyekun duyarsizlassa (A2 KIRMIZI)
    # zaten per-parca boy da 0 olur; A4 o hali A2'ye BIRAKIR (tek mutant iki lambayi
    # yakmasin). Fail-closed yon korunur: A2 o durumda zaten kirmizi, kosum kirmizi.
    if not fiilen_duyarli:
        ol("A4", "IKIZ: yorumdaki per-parca BOY iddiasi <-> olculen boy duyarliligi AYRISMIYOR",
           True, "A2 ekseni sahipleniyor (davranis genelde duyarsiz) — A4 ertelendi")
    else:
        # FAIL-CLOSED: musteri notu bugun DORT parcayi da adlandiriyor. Biri kaybolursa
        # (not curudu) A4 kirmizi yanar — bos kume uzerinde sessizce yesillenmesin.
        a4 = not eksik_parca and not ayrisan
        ol("A4", "IKIZ: yorumdaki per-parca BOY iddiasi <-> olculen boy duyarliligi AYRISMIYOR",
           a4,
           ("adlandirilmayan parca: %s" % eksik_parca) if eksik_parca
           else ("ayrisan (yorum!=olcum): %s | yorum=%s olcum=%s"
                 % (ayrisan, {p: iddia_boy[p] for p in ayrisan},
                    {p: olculen_boy[p] for p in ayrisan})) if ayrisan
           else "4 parca da uyumlu (civata/mil boy+, somun/pul boy-)")

    # ============================================ B — YONETIM HIZ SINIRI BEYANI
    rapor.append("B) YONETIM GIRIS HIZ SINIRI (shop/src/yonet.js  <->  izlenen .md beyani)")

    eksik_sabit = [ad for ad in SABIT_ADLARI
                   if not re.search(r"\bconst\s+%s\s*=" % re.escape(ad), yonet)]
    # Sabitler POZITIF mi: `const X = <ifade>;` govdesinde en az bir pozitif sayi olsun.
    pozitifsiz = []
    for ad in SABIT_ADLARI:
        m = re.search(r"\bconst\s+%s\s*=\s*([^;]+);" % re.escape(ad), yonet)
        if not m:
            continue
        sayilar = [float(s) for s in re.findall(r"\d+(?:\.\d+)?", m.group(1))]
        if not sayilar or max(sayilar) <= 0:
            pozitifsiz.append(ad)
    # Bloke yordami TANIM DISINDA fiilen cagriliyor mu ([[nobetci-cagri-satiri-nobetsiz]]:
    # tanimin varligi kosuldugunun KANITI DEGILDIR).
    tum_gecis = len(re.findall(r"\b%s\s*\(" % re.escape(BLOKE_ADI), yonet))
    tanim = len(re.findall(r"function\s+%s\s*\(" % re.escape(BLOKE_ADI), yonet))
    cagri = tum_gecis - tanim
    gecikme = bool(GECIKME_CAGRI_RE.search(yonet))
    b1 = (not eksik_sabit) and (not pozitifsiz) and cagri >= 1 and gecikme
    ol("B1", "DAVRANIS: giris hiz siniri YASIYOR (3 sabit + fiili cagri + await gecikme)",
       b1,
       "" if b1 else "eksik sabit=%s pozitifsiz=%s cagri=%d gecikme=%s"
       % (eksik_sabit, pozitifsiz, cagri, gecikme))

    beyan_dosyalari = []
    for yol, metin in sorted(belgeler.items()):
        k = katla(metin)
        for p in pencereler(k, YONETIM_RE, YONETIM_PENCERE):
            if HIZ_YOK_RE.search(p):
                beyan_dosyalari.append(yol)
                break
    b2 = (not beyan_dosyalari) or (not b1)
    ol("B2", "IKIZ: belgedeki 'hiz sinirsiz' beyani <-> kodun hiz siniri AYRISMIYOR",
       b2,
       "beyan yok (%d belge tarandi, kod: %s)"
       % (len(belgeler), "SINIRLI" if b1 else "sinirsiz") if not beyan_dosyalari
       else ("beyan VAR ama kodda hiz siniri YASIYOR — BAYAT beyan: %s" % beyan_dosyalari
             if b1 else "beyan kodla uyumlu"))

    if len(rapor) - 2 != IDDIA_SAYISI:
        raise Olculemedi("iddia sayisi kaydi: %d beklenirken %d olculdu"
                         % (IDDIA_SAYISI, len(rapor) - 2))
    return hatalar, rapor


# --------------------------------------------------------------------------- girdi
def belgeleri_topla():
    """Izlenen .md govdeleri (git ls-files). git yoksa fail-closed."""
    try:
        r = subprocess.run(["git", "-C", ROOT, "ls-files", "*.md"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise Olculemedi("git ls-files kosturulamadi: %s" % e)
    if r.returncode != 0:
        raise Olculemedi("git ls-files rc=%d: %s" % (r.returncode, (r.stderr or "")[:400]))
    yollar = [s.strip() for s in (r.stdout or "").splitlines() if s.strip()]
    if not yollar:
        raise Olculemedi("izlenen .md bulunamadi — B2 bos kume uzerinde bedavaya gecerdi.")
    govdeler = {}
    for y in yollar:
        tam = os.path.join(ROOT, y)
        try:
            with open(tam, encoding="utf-8") as f:
                govdeler[y] = f.read()
        except (OSError, UnicodeDecodeError):
            continue
    if not govdeler:
        raise Olculemedi("izlenen .md dosyalarinin hicbiri okunamadi.")
    return govdeler


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def canli_kosum():
    return (hacim_probe(HACIM_YOL), _oku(SECENEKLER_YOL), _oku(YONET_YOL),
            belgeleri_topla())


# --------------------------------------------------------------------------- mutasyon
# Her mutant TEK degiskenlidir ve BEKLENEN kirmizi kumesi ONCEDEN yazilir. Olculen kume
# beklenene TAM ESIT degilse (fazlasi da eksigi de) mutasyon KALIR: fazlasi probe'un
# GENIS oldugunu, eksigi iddianin OLU oldugunu soyler ([[mutasyon-kaniti-yeniden-uretilebilir]]).
#
# 🔴 GERCEK DOSYAYA YAZILMAZ: metin eksenleri BELLEKTE degistirilir; node gerektiren
# eksen SISTEM gecici dizinine KOPYALANIR. Kaynak sha256'lari basta ve sonda basilir.


def _hacim_mutanti(eski, yeni):
    """hacim.js'in mutantli KOPYASINI gecici dizine yazip probe'lar (depo temiz kalir)."""
    kaynak = _oku(HACIM_YOL)
    if kaynak.count(eski) != 1:
        raise Olculemedi("MUTASYON CAPASI KAYIP/COKLU (%d adet): %r"
                         % (kaynak.count(eski), eski[:60]))
    ged = tempfile.mkdtemp(prefix="bayat-beyan-mutant-")
    yol = os.path.join(ged, "hacim.js")
    try:
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(eski, yeni, 1))
        return hacim_probe(yol)
    finally:
        try:
            os.unlink(yol)
            os.rmdir(ged)
        except OSError:
            pass


def _metin_mutanti(metin, eski, yeni, ad):
    if metin.count(eski) != 1:
        raise Olculemedi("MUTASYON CAPASI KAYIP/COKLU (%s, %d adet): %r"
                         % (ad, metin.count(eski), eski[:60]))
    return metin.replace(eski, yeni, 1)


# Capalar — GERCEK dosyalardaki bugunku metinden turer; kayarsa mutasyon PATLAR (sessizce
# yesil vermez).
CAPA_VIDA_SATIRI = "     VIDA yok: hacim/fiyat formulu OLCUYE DUYARLI"
CAPA_VIDA_FN = "  function vida(p) {"
CAPA_YAY_FN = "  function yay(p) {"
CAPA_BLOKE_CAGRI = "  if (girisBlokeMi(simdi)) {"
CAPA_BELGE = "tools/paket-siparis-yonetimi.md"
CAPA_BELGE_SATIRI = "- GÜVENLİK ÇİZGİLERİ: yönetim uçları anahtarsız istekte 404;"
CAPA_PUL_SATIRI = "somun ve pul YALNIZ CAP'e duyarli"


def mutantlar():
    """(kod, sinif, aciklama, beklenen_kirmizi, kurucu) listesi."""
    return [
        ("M1", "OLDURUCU",
         "secenekler.js'e ESKI duyarsizlik cumlesi geri konur (musteri yuzu bayat iddia)",
         {"A3"},
         lambda g: dict(g, secenekler=_metin_mutanti(
             g["secenekler"], CAPA_VIDA_SATIRI,
             "     VIDA yok: fiyat formulu capa duyarsiz", "secenekler.js"))),
        ("M2", "OLDURUCU",
         "hacim.js vida() olcuden BAGIMSIZ sabite cevrilir (formul regresyonu)",
         {"A2"},
         lambda g: dict(g, probe=_hacim_mutanti(
             CAPA_VIDA_FN, CAPA_VIDA_FN + "\n    if (p) { return 157.0542; }"))),
        ("M3", "OLDURUCU",
         "belgeye ESKI 'yonetim uclari hiz sinirsiz' beyani geri konur",
         {"B2"},
         lambda g: dict(g, belgeler=dict(g["belgeler"], **{CAPA_BELGE: _metin_mutanti(
             g["belgeler"][CAPA_BELGE], CAPA_BELGE_SATIRI,
             "- GÜVENLİK ÇİZGİLERİ: yönetim uçları rate-limit'siz ama anahtarsız "
             "istekte 404;", CAPA_BELGE)}))),
        ("M4", "OLDURUCU",
         "yonet.js giris kolunda bloke yordaminin CAGRISI no-op edilir",
         {"B1"},
         lambda g: dict(g, yonet=_metin_mutanti(
             g["yonet"], CAPA_BLOKE_CAGRI, "  if (false) {", "yonet.js"))),
        ("M5", "KONTROL",
         "secenekler.js'e DOGRU yonlu ('olcuye duyarli') ikinci bir cumle eklenir",
         set(),
         lambda g: dict(g, secenekler=_metin_mutanti(
             g["secenekler"], CAPA_VIDA_SATIRI,
             "     VIDA notu: formul olcuye duyarlidir.\n" + CAPA_VIDA_SATIRI,
             "secenekler.js"))),
        ("M6", "KONTROL",
         "hacim.js'te VIDA DISI bir aile (yay) sabitlenir — kapi kapsam disini saymaz",
         set(),
         lambda g: dict(g, probe=_hacim_mutanti(
             CAPA_YAY_FN, CAPA_YAY_FN + "\n    if (p) { return 1234.5; }"))),
        ("M7", "OLDURUCU",
         "yorum 'pul boy'a duyarli' der (olcumde 0) — bayat per-parca ayrinti",
         {"A4"},
         lambda g: dict(g, secenekler=_metin_mutanti(
             g["secenekler"], CAPA_PUL_SATIRI,
             "somun YALNIZ CAP'e, pul ise CAP+BOY'a duyarli", "secenekler.js"))),
        ("M8", "KONTROL",
         "per-parca iddiayi KORUYAN reword (YALNIZ->SADECE) — A4 kor degil",
         set(),
         lambda g: dict(g, secenekler=_metin_mutanti(
             g["secenekler"], CAPA_PUL_SATIRI,
             "somun ve pul SADECE CAP'e duyarli", "secenekler.js"))),
    ]


def kendini_test():
    print("=== BAYAT BEYAN KAPISI — KENDINI TEST (mutasyon)")
    onceki = {y: sha256(y) for y in (HACIM_YOL, SECENEKLER_YOL, YONET_YOL)}
    for y, h in sorted(onceki.items()):
        print("  sha256 ONCE  %-52s %s" % (os.path.relpath(y, ROOT), h))
    print()

    probe, sec, yon, belgeler = canli_kosum()
    taban = {"probe": probe, "secenekler": sec, "yonet": yon, "belgeler": belgeler}
    t_hatalar, t_rapor = kosum(**taban)
    t_kodlar = sorted({h.split()[0] for h in t_hatalar})
    print("  TABAN: %d iddia / %d KIRMIZI %s"
          % (IDDIA_SAYISI, len(t_hatalar), t_kodlar or ""))
    if t_hatalar:
        print("  🔴 TABAN KIRMIZI — mutasyon anlamsiz (once kapiyi yesillet).")
        for h in t_hatalar:
            print("     ✘ " + h)
        return 1
    print()

    tamam = True
    oldurucu = kontrol = 0
    for kod, sinif, aciklama, beklenen, kurucu in mutantlar():
        try:
            g = kurucu(taban)
            hatalar, rapor = kosum(**g)
        except Olculemedi as e:
            print("  %s %-9s OLCULEMEDI: %s" % (kod, sinif, e))
            tamam = False
            continue
        olculen = {h.split()[0] for h in hatalar}
        esit = olculen == beklenen
        sayi_tamam = (len(rapor) - 2) == IDDIA_SAYISI
        if sinif == "OLDURUCU":
            oldurucu += 1
        else:
            kontrol += 1
        print("  %s %-9s %s" % (kod, sinif, aciklama))
        print("      beklenen=%s  olculen=%s  iddia=%d  -> %s"
              % (sorted(beklenen) or "-", sorted(olculen) or "-", len(rapor) - 2,
                 "GECTI" if (esit and sayi_tamam) else "KALDI"))
        if not (esit and sayi_tamam):
            tamam = False

    print()
    sonraki = {y: sha256(y) for y in (HACIM_YOL, SECENEKLER_YOL, YONET_YOL)}
    for y, h in sorted(sonraki.items()):
        print("  sha256 SONRA %-52s %s" % (os.path.relpath(y, ROOT), h))
    bozulmadi = onceki == sonraki
    print("  KAYNAK BUTUNLUGU: %s" % ("SAGLAM (basta = sonda)" if bozulmadi
                                      else "🔴 BOZULDU — mutant diske sizmis"))
    print()
    print("MUTASYON: %d olduruculuk + %d kontrol | %s"
          % (oldurucu, kontrol,
             "GECTI — her mutant TAM beklenen iddiayi dusurdu, iddia sayisi sabit."
             if (tamam and bozulmadi)
             else "KALDI — iddia OLU, probe GENIS ya da kaynak bozuldu."))
    return 0 if (tamam and bozulmadi) else 1


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Bayat beyan kapisi (beyan <-> davranis)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="mutantlarla kapinin KIRMIZI yakabildigini kanitla")
    args = ap.parse_args()

    try:
        if args.kendini_test:
            return kendini_test()
        probe, sec, yon, belgeler = canli_kosum()
        hatalar, rapor = kosum(probe, sec, yon, belgeler)
    except Olculemedi as e:
        print("OLCULEMEDI (fail-closed, YESIL VERILMEZ): %s" % e)
        return 2
    except Exception as e:                                            # noqa: BLE001
        # Traceback CI logunda "cokme" olarak KIRMIZI ile karisir; hukum acikca basilir.
        print("OLCULEMEDI (beklenmeyen hata, fail-closed): %s: %s" % (type(e).__name__, e))
        return 2

    print("=== BAYAT BEYAN KAPISI (depo beyani <-> olculen davranis)")
    for s in rapor:
        print(s)
    print()
    print("IDDIA: %d | KIRMIZI: %d" % (IDDIA_SAYISI, len(hatalar)))
    if hatalar:
        print("KIRMIZI — %d iddia ihlal edildi:" % len(hatalar))
        for h in hatalar:
            print("  ✘ " + h)
        return 1
    print("YESIL — beyan ile davranis ayrismiyor (vida olcu duyarliligi + yonetim hiz siniri).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
