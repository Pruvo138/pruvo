#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kapsam-disi-sinif-kapisi.py — DURUST-SINIR BEYANI <-> GORUNUR KATALOG kolu.

NEDEN VAR (BaBa 7 Eyl 2026, KARAR 1 — 3. tekrar, tekil yama YASAK):
`tools/sayfalar.py` landing metinlerinde musteriye BIREBIR sunu soyluyoruz:

    "Sintine, deniz suyu, motor sogutma ve sirkulasyon pompalarinin carki (impeller)
     — basinc seviyesi ne olursa olsun — kapsamimizin disindadir; sivi tasiyan bir
     pompa carkini da tekneyi iten ana pervaneyi de uretmeyiz."

Ayni eksende katalogta GORUNUR kayitlar bunun tersini vaat ediyordu. Ayni celiski
UC KEZ tekil olarak duzeltildi (ArTisT bildirimi · d23ce4c0 · ee6406e3) ve her
seferinde geri geldi, cunku HICBIR kapi durust-sinir METNI ile katalog BASLIK/
ACIKLAMASI arasina bakmiyordu: `denetim-kapisi.py` alan/sema olcer, sinif olcmez.
Bu dosya o sinif bosluguna kurulmustur.

TEK KAYNAK — ELLE SINIF LISTESI YOK:
Yasak sinifin jetonlari `sayfalar.py`'deki durust-sinir madde isaretinden (`<li>`)
CALISMA ANINDA TURETILIR. Metin degisirse kapi kendiliginde onu izler; ikinci bir
"yasak liste" tanimi acilmaz (ikiz tanim = kaymanin kaynagi). Metin bulunamaz ya da
turetme BOS kalirsa kapi YESILE DUSMEZ — birebir `OLCULEMEDI` basip rc=3 doner.

MADDE ISARETI IKI KOLLUDUR ve kapi IKISINI DE turetir:
  * URETIRIZ kolu  : "Hava tasiyan fan pervanesi ve havalandirma carki uretiriz."
  * KAPSAM-DISI kolu: yukaridaki cumle.
Parca adi (`cark`, `pervane`) HER IKI KOLDA gectigi icin jeton olarak oradan cikar;
ayirt eden sey ORTAM'dir (hava vs sivi). Bu yuzden parca jetonlari iki kolun
KESISIMINDEN, sivi baglam ifadeleri yalniz KAPSAM-DISI kolundan turetilir.

IKI YONLU + NON-GROWTH (ders: [[grep-sifir-nobetcisi-yasak-kaydinda-oludur]]):
tek yonlu bir "sayi==0" nobetcisi, muafiyet sicili sessizce sisirilerek yesile
cevrilebilirdi. Bu yuzden kapi IKI yone birden bakar:
  YON 1 (celiski) : sinif icindeki GORUNUR kayit sicilde degilse  -> KIRMIZI
  YON 2 (sicil)   : sicil buyurse / olu kayit tasirsa / sicildeki
                    kayit zaten sinif disiysa (dolgu)             -> KIRMIZI
Sicil ELLE SINIF LISTESI DEGILDIR: sinifi tanimlamaz, sinif ICINDEN insan eliyle
adjudike edilmis TEKIL kayitlari tasir, her biri gerekcesiyle, sayisi CIVILI.

CIKIS KODLARI: 0 temiz · 1 celiski (YON 1) · 2 sicil ihlali (YON 2) · 3 OLCULEMEDI.
"""
import argparse
import json
import os
import re
import sys

# --- YOL COZUMU -------------------------------------------------------------
# Tek sabite capalanmaz: kok `__file__`den turer, `--ev` ile izole kopyaya
# yoneltilebilir. Boylece mutant IZOLE kopyada olculur, canli govde yamanmaz.
# ([[iki-kollu-govde-tek-sabite-capalanirsa-kosucunun-diskini-olcer]])
_BU = os.path.dirname(os.path.abspath(__file__))
VARSAYILAN_EV = os.path.dirname(_BU)

# --- MUAFIYET SICILI (NON-GROWTH, sayisi CIVILI) ----------------------------
# K376'nin insan eliyle adjudike ettigi CELISMEYEN 4 kayit. Her biri sinif
# icindedir (basliginda impeller/empeller gecer) ama sivi tasiyan pompa carki
# DEGILDIR. Bu sicil sinifi TANIMLAMAZ; sinif icinden istisna tasir.
MUAFIYET_SICILI = {
    "audi-merkezi-kilit-pompas-ark-impeller":
        "vakum/basinc pompasi = HAVA duzlemi; sivi tasimaz (durust-sinir URETIRIZ kolu)",
    "sea-doo-impeller-konisi":
        "impellerin KONISI = aksesuar govdesi, carkin kendisi degil",
    "volvo-penta-empeller-motor-stop-tirnagi":
        "empeller YUVASININ tirnak/kilit parcasi = aksesuar, carkin kendisi degil",
    "bosch-arm-cim-bicme-fan-makara":
        "motor sogutma FANI = hava tasiyan fan pervanesi (durust-sinir URETIRIZ kolu)",
    # --- BaBa 7 Eyl 18:5x, B MADDESI: taban kuyrugunun 22 kaydi adjudike edildi.
    # Olcut `sayfalar.py`nin durust-sinir maddesi: HAVA tasiyan fan/cark URETIRIZ;
    # SIVI tasiyan pompa carki (basinc ne olursa olsun) + tekneyi iten pervane
    # URETMEYIZ. Alet ve tahrik dislisi sivi TASIMAZ -> muaf. 13'u gizlendi, bu 9'u
    # sinif icinde GORUNUR kalir ve gerekcesiyle burada tasinir.
    # (a) HAVA duzlemi — durust-sinir URETIRIZ kolu
    "avuc-taslama-motor-fani-pervane-d17":
        "avuc taslama motor FANI = hava tasiyan fan pervanesi, sivi tasimaz",
    "sac-kurutma-makinesi-fan-pervanesi-60mm-7-kanat":
        "sac kurutma makinesi FANI = hava tasiyan fan pervanesi, sivi tasimaz",
    "sac-kurutma-makinesi-fan-pervanesi-63mm":
        "sac kurutma makinesi FANI = hava tasiyan fan pervanesi, sivi tasimaz",
    "suzuki-lt80-sogutma-pervanesi":
        "hava sogutmali ATV fani (150 mm) = hava duzlemi, sivi sogutma degil",
    "bisiklet-sabun-kopugu-makinesi":
        "KOPUK carki = kopuk cirpar, pompa carki DEGIL; sivi basma islevi yok",
    # (b) ALET — parcanin kendisi cark/pervane degil, ona hizmet eden el aleti
    "evinrude-johnson-pervane-mili-anahtari":
        "pervane MILI ANAHTARI = el aleti; carkin/pervanenin kendisi degil",
    "yamaha-pervane-mili-anahtari":
        "pervane MILI ANAHTARI = el aleti; carkin/pervanenin kendisi degil",
    # (c) TAHRIK DISLISI — pompayi doner, sivi tasiyan cark degil
    "honda-crm250-mk2-su-pompasi-disli":
        "su pompasi TAHRIK DISLISI = pompayi doner, sivi tasiyan cark degil",
    "yamaha-aerox-devirdaim-tahrik-carki":
        "devirdaim TAHRIK carki = tahrik dislisi duzlemi, sivi tasiyan cark degil",
}
# NON-GROWTH capasi: sicil buyuyemez, buyurse YON 2 kirmizi yanar.
# 4 -> 13 (BaBa 7 Eyl 18:5x B maddesi: taban kuyrugundan 9 kayit adjudike edilip
# gerekcesiyle sicile alindi; kalan 13 kayit `gizli:true` yapildi).
SICIL_TAVANI = 13

# --- TABAN KUYRUGU (ONCEDEN VAR OLAN, HENUZ ADJUDIKE EDILMEMIS) -------------
# 🔴 BU KAPI KURULURKEN OLCULEN GERCEK (7 Eyl 2026): K376 sinifi BASLIK uzerinden
# saymisti (gorunur 9). Metinden TURETILMIS sinif ACIKLAMAYI da okuyunca gorunur
# sinif ici kayit sayisi cok daha buyuk cikti — "su pompasi carki", "santrifuj su
# pompasi", "ROV sintine pompasi itici pervanesi", "tekne icin genel amacli
# pervane" gibi, basliginda 'impeller' GECMEYEN kayitlar. Bunlarin sinifi (gercek
# celiski mi, aksesuar/hava muafiyeti mi) BaBa'nin karari, KraL'in degil.
# Bu dosya onlari SESSIZCE GECMEZ ve YAYINI DA DURDURMAZ: kuyruk olarak CIVILENIR,
# her kosumda SAYIYLA basilir ve MANDAL gibi calisir — kuyruk BUYUYEMEZ.
# Depodaki yerlesik ayrim budur (bkz. deploy.yml `denetim-kapisi --commit-farki`:
# "BLOKLAYAN SEY: yalniz BU ITMENIN GETIRDIGI ihlal"). Gevsetme degil AYIRMA.
# K376'nin kendi kabul cumlesi de bunu ister: "YENI kayit ayni celiskiyi
# dogurursa kapi KIRMIZI yanar".
TABAN_DOSYASI = "kapsam-disi-taban.json"
# Kuyrugun civili boyu. Taban dosyasini duzenleyerek kapiyi susturmak isteyen biri
# bu sayiya carpar: dosya buyurse YON 2 kirmizi yanar. Kuyruk KUCULEBILIR (serbest).
# 🔴 MANDAL KUYRUKLA BIRLIKTE INER (22 -> 0, BaBa 7 Eyl 18:5x B): kuyruk bosaldigi
# halde tavan 22'de biraksaydik, 22 yeni celiski kuyruga yazilarak SESSIZCE
# susturulabilirdi — mandal yalniz asagi doner, tavan da onunla iner. Kabul kolu
# `kapsam-disi-sinif-test.py::M3` bunu olcer (kuyruga 1 id eklemek rc=2 vermeli).
TABAN_TAVANI = 0

# --- TURKCE ISLEV SOZCUKLERI ------------------------------------------------
# Dilbilimsel iskele, SINIF LISTESI DEGIL: iki kolun kesisiminden anlamsiz ortak
# sozcukleri (fiil/baglac) eler. Buraya bir PARCA adi yazmak kapiyi korlestirirdi;
# bunu kabul testi `test_islev_sozcuklerinde_parca_adi_yok` olcer.
ISLEV_SOZCUKLERI = {
    "tasiyan", "tasiyani", "uretiriz", "uretmeyiz", "olursa", "olsun", "kapsamimizin",
    "disindadir", "seviyesi", "bir", "ile", "veya", "hangi", "ayrica", "yani",
}

_TR_KUCUK = str.maketrans({
    "I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç",
})
# 🔴 ASCII KATLAMA ZORUNLU, SUS DEGIL: katalog ayni sozcugu iki yazimla tasiyor
# ("empeller yuvasinda" ASCII, "İmpeller Yuvası" diakritikli — ikisi de canli
# kayit). Katlamasiz eslesme, diakritiksiz yazilmis bir celiskiyi SESSIZCE
# kacirirdi. Kapinin hem turetme hem katalog tarafi AYNI normalize()den gecer.
_KATLA = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"})
_SESLI = "aeiou"


def normalize(s):
    """Kucult (Turkce dogru) + ASCII katla + kesme/noktalama sadelestir."""
    if not s:
        return ""
    s = s.translate(_TR_KUCUK).lower().translate(_KATLA)
    s = s.replace("’", "'").replace("ʼ", "'")
    s = re.sub(r"['’]", "", s)          # "impeller'i" -> "impelleri"
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return " ".join(s.split())


def _sesli_duyarsiz_kalip(jeton):
    """'impeller' -> r'\\b[ie]mp[ie]ll[ie]r'  (KENDI seslileri, TUM sesliler DEGIL)

    Alintilanmis parca adi katalogta hem 'impeller' hem 'empeller' yaziliyor;
    varyantlari ELLE saymak yerine mekanik turetiriz. AMA sesli sinifi jetonun
    KENDI seslileriyle sinirlidir.
    🔴 OLCULDU (ilk kosum, bu dosyanin ilk hali): sinif TUM sesliler olunca
    `[aeiou]mp[aeiou]ll[aeiou]r` Turkce **'ampuller'** sozcugunu yakaladi ve
    40'tan fazla far/ampul kaydini yanlis pozitif olarak kirmiziya yakti. Kendi
    seslileriyle ({i,e}) sinirlandirilinca 'ampuller' (a,u) dusuyor, 'empeller'
    duruyor. Kabul testi bu iki vakayi da ADIYLA olcer.
    Bas sinir `\\b`: 'sempeller' gibi bir bilesigin icinde tesadufen yanmasin.
    """
    kendi = "".join(sorted(set(ch for ch in jeton if ch in _SESLI)))
    if not kendi:
        return r"\b" + re.escape(jeton)
    parcalar = [r"\b"]
    for ch in jeton:
        parcalar.append("[" + kendi + "]" if ch in _SESLI else re.escape(ch))
    return "".join(parcalar)


def _govde(jeton, n=4):
    return jeton[:n]


class Turetme(object):
    """Durust-sinir madde isaretinden turetilmis yasak sinif."""

    def __init__(self, alias, parca, sivi, hava, kaynak_satir):
        self.alias = alias                # ['impeller']
        self.parca = parca                # ['cark', 'pervane'] (govde)
        self.sivi = sivi                  # ['sintine', 'deniz suyu', ...]
        self.hava = hava                  # ['hava', 'fan', 'havalandirma'] (bilgi)
        self.kaynak_satir = kaynak_satir
        self._alias_re = [re.compile(_sesli_duyarsiz_kalip(a)) for a in alias]

    def bos_mu(self):
        return not self.alias or not self.parca or not self.sivi

    def sinifta_mi(self, metin):
        """(bool, gerekce) — metin yasak sinifa giriyor mu?"""
        n = normalize(metin)
        for a_re, a in zip(self._alias_re, self.alias):
            if a_re.search(n):
                return True, "parca adi '%s' (sesli-duyarsiz) gecti" % a
        # B kolu: parca adi + sivi baglami birlikte (metin 'impeller' demese bile)
        vurulan_parca = [p for p in self.parca if p in n]
        if vurulan_parca:
            vurulan_sivi = [s for s in self.sivi if s in n]
            if vurulan_sivi:
                return True, ("parca '%s' + sivi baglam '%s'"
                              % (vurulan_parca[0], vurulan_sivi[0]))
        return False, ""


def turet(sayfalar_yolu):
    """sayfalar.py -> Turetme | None (None = OLCULEMEDI)."""
    try:
        with open(sayfalar_yolu, encoding="utf-8") as f:
            src = f.read()
    except OSError:
        return None

    # Durust-sinir madde isareti: <li><strong>Pervane / cark:</strong> ... </li>
    # Capa METNIN KENDISI degil, YAPISI: "uretiriz." ile biten bir URETIRIZ kolu +
    # "uretmeyiz" ile biten bir KAPSAM-DISI kolu tasiyan, parantezli parca adi olan
    # madde. Boylece ArTisT cumleyi yeniden yazarsa kapi kirilmaz, izler.
    aday = None
    aday_satir = 0
    for m in re.finditer(r"<li>(.*?)</li>", src, re.S):
        govde = re.sub(r"<[^>]+>", " ", m.group(1))
        n = normalize(govde)
        if "uretiriz" in n and "uretmeyiz" in n and "kapsamimizin disindadir" in n:
            if re.search(r"\(([A-Za-zÇĞİÖŞÜçğıöşü]{4,})\)", govde):
                aday = govde
                aday_satir = src.count("\n", 0, m.start()) + 1
                break
    if aday is None:
        return None

    # Kolu ikiye ayir: ilk "uretiriz." cumlesi = URETIRIZ kolu, kalani KAPSAM-DISI.
    kesim = re.search(r"üretiriz\s*\.", aday)
    if not kesim:
        return None
    uretiriz_kolu = aday[:kesim.end()]
    kapsam_disi_kolu = aday[kesim.end():]
    if not normalize(kapsam_disi_kolu):
        return None

    n_uret = normalize(uretiriz_kolu).split()
    n_disi = normalize(kapsam_disi_kolu).split()

    # (1) ALIAS: kapsam-disi kolundaki parantezli parca adi ("(impeller)").
    alias = []
    for a in re.findall(r"\(([A-Za-zÇĞİÖŞÜçğıöşü]{4,})\)", kapsam_disi_kolu):
        na = normalize(a)
        if na and na not in alias:
            alias.append(na)

    # (2) PARCA: IKI KOLDA DA gecen sozcukler (4 harflik govde eslesmesi).
    #     Parca adi iki kolda da gecer cunku ayrim ORTAMdadir, parcada degil.
    uret_govde = set(_govde(w) for w in n_uret if len(w) >= 4)
    parca = []
    for w in n_disi:
        if len(w) < 4 or w in ISLEV_SOZCUKLERI:
            continue
        g = _govde(w)
        if g in uret_govde and g not in parca:
            parca.append(g)

    # (3) SIVI BAGLAM: kapsam-disi kolundaki ortam ifadeleri.
    #     "Sintine, deniz suyu, motor sogutma ve sirkulasyon pompalarinin carki"
    #     -> 'pompa' oncesindeki virgul/'ve' ile ayrilmis liste.
    # 🔴 AYIRMA HAM METINDE YAPILIR, normalize()DEN SONRA DEGIL: normalize()
    # noktalamayi siler, dolayisiyla normalize edilmis metinde virgul KALMAZ ve
    # liste tek bir run-on ifadeye ("sintine deniz suyu motor sogutma") cokerdi —
    # o ifade hicbir urun metnine uymaz, yani 'sintine' ekseni SESSIZCE OLU olurdu.
    # (Ilk kosumda tam bu oldu; ROV sintine kayitlari yalniz 'pompa' koluyla yandi.)
    sivi = []
    liste_m = re.search(r"^(.*?)\bpompa", kapsam_disi_kolu, re.I)
    if liste_m:
        for parca_ifade in re.split(r",|\sve\s", liste_m.group(1)):
            p = normalize(parca_ifade)
            if p and len(p) >= 4 and p not in sivi:
                sivi.append(p)
    sivi.append("pompa")                       # 'pompalarinin' -> pompa hatti
    # "sivi tasiyan bir pompa carkini" -> 'tasiyan'in onundeki ortam sozcugu
    for m2 in re.finditer(r"(\w+)\s+tasiyan", normalize(kapsam_disi_kolu)):
        w = m2.group(1)
        if w not in sivi:
            sivi.append(w)
    sivi = [s for s in sivi if s not in ISLEV_SOZCUKLERI]

    # (4) HAVA (bilgi ekseni; URETIRIZ kolunun ortam sozcukleri)
    hava = [w for w in n_uret if len(w) >= 3 and w not in ISLEV_SOZCUKLERI
            and _govde(w) not in set(parca)]

    return Turetme(alias, parca, sivi, hava, aday_satir)


def taban_oku(ev):
    """(set(id), hata_metni|None) — onceden var olan, adjudike edilmemis kuyruk."""
    yol = os.path.join(ev, "tools", TABAN_DOSYASI)
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except OSError as e:
        return set(), "acilamadi (%s)" % e
    except ValueError as e:
        return set(), "gecerli JSON degil (%s)" % e
    kuyruk = veri.get("kuyruk") if isinstance(veri, dict) else None
    if not isinstance(kuyruk, list) or not all(isinstance(x, str) for x in kuyruk):
        return set(), "'kuyruk' anahtari metin id dizisi olmali"
    return set(kuyruk), None


def gorunur_kayitlar(urunler_yolu):
    with open(urunler_yolu, encoding="utf-8") as f:
        data = json.load(f)
    return [u for u in data if u.get("gizli") is not True], len(data)


def calistir(ev, sessiz=False):
    sayfalar = os.path.join(ev, "tools", "sayfalar.py")
    urunler = os.path.join(ev, "urunler.json")

    t = turet(sayfalar)
    if t is None or t.bos_mu():
        print("OLCULEMEDI — durust-sinir madde isareti %s icinde cozulemedi "
              "(metin tasindi/bozuldu ya da turetme BOS)." % sayfalar)
        print("NEYI OLCMEK KAPATIR: `<li>` icinde hem 'üretiriz.' hem 'üretmeyiz' "
              "hem 'kapsamımızın dışındadır' hem parantezli parca adi tasiyan madde "
              "isaretinin varligi. Kapi YESILE DUSMEZ.")
        return 3

    try:
        gorunur, toplam = gorunur_kayitlar(urunler)
    except (OSError, ValueError) as e:
        print("OLCULEMEDI — katalog okunamadi: %s" % e)
        return 3

    if not sessiz:
        print("TURETME (kaynak: %s, madde ~satir %d)" % (sayfalar, t.kaynak_satir))
        print("  parca adi (alias, sesli-duyarsiz): %s" % ", ".join(t.alias))
        print("  parca jetonlari (iki kolun kesisimi): %s" % ", ".join(t.parca))
        print("  sivi baglam ifadeleri: %s" % ", ".join(t.sivi))
        print("KATALOG: %d kayit, %d gorunur" % (toplam, len(gorunur)))

    sinifta = []
    for u in gorunur:
        metin = "%s %s" % (u.get("baslik") or "", u.get("aciklama") or "")
        var, gerekce = t.sinifta_mi(metin)
        if var:
            sinifta.append((u.get("id"), u.get("baslik") or "", gerekce))

    sinif_idler = set(i for i, _b, _g in sinifta)

    taban, taban_hata = taban_oku(ev)
    if taban_hata:
        print("OLCULEMEDI — taban kuyrugu okunamadi: %s" % taban_hata)
        print("NEYI OLCMEK KAPATIR: %s dosyasinin gecerli JSON olmasi ve "
              "{\"kuyruk\": [<id>, ...]} tasimasi. Kapi YESILE DUSMEZ." % TABAN_DOSYASI)
        return 3

    yeni = [x for x in sinifta
            if x[0] not in MUAFIYET_SICILI and x[0] not in taban]
    kuyrukta = [x for x in sinifta if x[0] in taban]
    kapanmis = sorted(taban - sinif_idler)

    if not sessiz:
        print("SINIF ICI gorunur kayit: %d — sicil muafi %d · taban kuyrugu %d "
              "(tavan %d) · YENI %d"
              % (len(sinifta), len(sinifta) - len(yeni) - len(kuyrukta),
                 len(kuyrukta), TABAN_TAVANI, len(yeni)))
        if kapanmis:
            print("  KUYRUK AZALDI (%d kayit artik sinif disi/gizli): %s"
                  % (len(kapanmis), ", ".join(kapanmis)))

    # --- YON 2: SICIL + TABAN BUTUNLUGU (NON-GROWTH MANDALI) ---------------
    sicil_ihlali = []
    if len(MUAFIYET_SICILI) > SICIL_TAVANI:
        sicil_ihlali.append(
            "NON-GROWTH: muafiyet sicili %d kayit, tavan %d — sessizce buyutulmus."
            % (len(MUAFIYET_SICILI), SICIL_TAVANI))
    if len(taban) > TABAN_TAVANI:
        sicil_ihlali.append(
            "NON-GROWTH: taban kuyrugu %d kayit, tavan %d — kuyruk BUYUYEMEZ "
            "(mandal yalniz asagi doner). Yeni celiskiyi kuyruga yazarak "
            "susturamazsin." % (len(taban), TABAN_TAVANI))
    for sid, gerekce in sorted(MUAFIYET_SICILI.items()):
        if not gerekce.strip():
            sicil_ihlali.append("sicil kaydi gerekcesiz: %s" % sid)
        elif sid not in sinif_idler:
            sicil_ihlali.append(
                "OLU/DOLGU sicil kaydi: %s — gorunur katalogda sinif icinde DEGIL "
                "(silinmis, gizlenmis ya da bastan sinif disi). Sicil, yakalamadigi "
                "kaydi mesrulastiramaz; dusur ve SICIL_TAVANI'ni birlikte indir."
                % sid)

    if sicil_ihlali:
        print("")
        print("KIRMIZI — YON 2 (sicil/taban butunlugu): %d ihlal" % len(sicil_ihlali))
        for s in sicil_ihlali:
            print("  * %s" % s)
        return 2

    if yeni:
        print("")
        print("KIRMIZI — YON 1 (durust-sinir celiskisi): %d YENI GORUNUR kayit"
              % len(yeni))
        for uid, baslik, gerekce in yeni:
            print("  * %s | %s | %s" % (uid, baslik[:64], gerekce))
        print("")
        # 🔴 `ISCIYE:` isareti ZORUNLU (K179/recete-kapisi, 9 Eyl 2026): bu recete
        # URUN duzlemine (MaCiT) yazilir — `duzelt.py` mevcut kaydi DEGISTIREN tek
        # mesru aractir ve MIMAR onu kosmaz (CLAUDE.md: "KraL urunu YAZMAZ").
        # Isaretsiz birakilirsa recete mimar-icra-kapisi'na sorulur, REDDEDILIR ve
        # `recete-kapisi.py` SERIT B'yi kirmiziya yakar (7 Eyl'den beri oyleydi).
        # Isaret kapiyi GEVSETMEZ: yol nobeti aynen surer, yalniz recetenin HANGI
        # KATA yazildigini beyan eder.
        print("Durust-sinir beyani bu sinifi kapsam DISI ilan ediyor "
              "(kaynak: tools/sayfalar.py, ~satir %d). COZUM: ISCIYE: (urun duzlemi) kaydi "
              "`python3 tools/duzelt.py --toplu <islem.json>` ile `gizli:true` yap "
              "(URUN SILINMEZ) ya da gercekten hava/aksesuar duzlemindeyse "
              "MUAFIYET_SICILI'ne gerekcesiyle ekle ve SICIL_TAVANI'ni birlikte yukselt."
              % t.kaynak_satir)
        print("Taban kuyruguna EKLEMEK bir cozum DEGILDIR: kuyruk tavani civili.")
        return 1

    print("")
    print("TEMIZ — durust-sinir beyaniyla celisen YENI gorunur kayit: 0 "
          "(sinif ici %d = sicil %d + taban kuyrugu %d)"
          % (len(sinifta), len(sinifta) - len(kuyrukta), len(kuyrukta)))
    if kuyrukta:
        print("🔔 ACIK KUYRUK: %d onceden var olan gorunur kayit hala durust-sinir "
              "sinifinda — sinifi (gercek celiski / aksesuar / hava muafiyeti) "
              "BaBa adjudike edecek. Kapi bunlari BLOKLAMAZ, unutturmaz." % len(kuyrukta))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ev", default=VARSAYILAN_EV,
                    help="olculecek depo koku (izole mutant kopyasi icin)")
    ap.add_argument("--sessiz", action="store_true")
    a = ap.parse_args()
    return calistir(a.ev, a.sessiz)


if __name__ == "__main__":
    sys.exit(main())
