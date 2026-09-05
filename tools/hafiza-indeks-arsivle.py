#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/hafiza-indeks-arsivle.py — HAFIZA INDEKSININ (MEMORY.md) TAVAN SAHIBI.

NE YAPAR: `~/.claude/projects/-Users-okan-dev-pruvo/memory/MEMORY.md` indeksi tavani
asinca, EN ESKI dokunulmus hedeflere isaret eden INDEKS GIRDILERINI `MEMORY-ARSIV.md`
dosyasina LOSSLESS tasir ve indeksi SU SEVIYESINE indirir.

=== NEDEN VAR (olculdu, 5 Eyl 2026 — SINIF ISI, tekil budama DEGIL) ===
MEMORY.md HER OTURUM baglama yuklenir; bayti dogrudan maliyettir. Buyume kaydi:
17.454 -> 18.230 -> 19.105 B (18 Agu, K179'da ELLE 14 girdi arsive tasindi) -> bugun
**19.002 B**. Yani tam bir TEKIL budama 18 gunde net ~100 bayt kazandirdi: sinif ACIK.
[[ucuncu-tekrar-sinif-kapisi]] geregi tekil kirpma YASAK — TAVAN + SAHIP + ROTASYON.
Bugune kadar bu dosyanin HICBIR tavan sahibi ve HICBIR rotasyon araci YOKTU.

=== TAVAN (CEZA) ile SU SEVIYESI (ONARIM) AYRI SAYIDIR — K353 dersi ===
Ikisi esitlenirse rotasyon tam tavanda durur, bir sonraki girdi yeniden asar ve kilit
geri gelir; care kilidin YANLIS tarafinda kalir
([[onarim-kolu-zarar-esiginin-arkasinda]]). Bu yuzden:
    TAVAN        = ceza noktasi (kota kapisi BURADA kirmizi yakar)
    SU SEVIYESI  = onarim hedefi (rotasyon BURAYA iner; tavana degdi diye DURMAZ)
🔴 BEST-EFFORT: su seviyesine inilemezse ama indeks TAVANIN ALTINA indiyse bu
BASARIDIR (kota saglandi); pay kisaligi ADIYLA basilir, kilit URETILMEZ.

=== ROTASYON BIRIMI = INDEKS GIRDISI (satir DEGIL) ===
Indeks 20 bolum satirindan olusur ve her satir `,` ile ayrilmis onlarca
`[Etiket](dosya.md) — kuyruk` girdisi tasir. Birim SATIR olsaydi tek hamlede bir
bolumun tamami giderdi; birim GIRDIdir.

🔴 KORUMALI — ASLA TASINMAZ:
  (i)   etiketinde 🔴 (ya da 🔴🔴) tasiyan her girdi,
  (ii)  "Acik kuyruk" bolumunun TAMAMI — acik kalem baglam disina duserse kuyruk
        olcum disi kalir ([[kayit-duzlemi-ikiye-ayrilirsa-kuyruk-olcum-disi]]),
  (iii) BOLUM BASLIKLARI (baslik bir GIRDI degildir; bolum satiri hicbir kosulda
        indeksten dusmez — bu yuzden satir ekseninin YAPISAL TABANI vardir, bkz.
        `yapisal_taban_satir()`),
  (iv)  arsiv ISARETCISI (`](MEMORY-ARSIV.md)`) — K179 emsali: bir bolumden bir sey
        tasindiysa o bolumun SONUNA TEK isaretci konur, IKINCISI ACILMAZ,
  (v)   hedef `.md` dosyasi DISKTE OLMAYAN girdi (bag butunlugu dogrulanamaz; kirik
        bag gizlenmez, INDEKSTE GORUNUR kalir).

🔴 SILME YOK, TASIMA VAR: `memory/` altindaki hicbir icerik `.md` dosyasi ACILMAZ,
DEGISTIRILMEZ, SILINMEZ. Bu arac YALNIZ iki dosyaya yazar: indeks ve arsiv.

=== HUKUM JETONLARI (kota kapisinin TUKETTIGI) ===
    HUKUM=TAVAN_BASARILI   rc=0  — tasindi, indeks tavanin altina indi.
    HUKUM=TAVAN_FAIL_LOUD  rc=1  — tavan asili ve TASINABILIR ICERIK TUKENDI
                                   (ya hic yok, ya yetmiyor). HICBIR SEY YAZILMAZ.
    HUKUM=DOLU_NO_OP       rc=0  — tavan altinda; is yok, dosya BAYT BAYT AYNI.
                                   (Ayrica `TAVAN=DOLU_NO_OP` jetonu basilir.)
    HUKUM=KORUMA_TUTTU     rc=0  — tavan asili ama tasinabilir=0'in SEBEBI KORUMA.
                                   Gorunurluk kota kirmizisina tercih edilir; hal
                                   GIZLENMEZ, sayilariyla BASILIR (Okan kurali ⑤).
🔴 `KORUMA_TUTTU` ile `TAVAN_FAIL_LOUD` AYNI KOVAYA DUSURULEMEZ
([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]): ilkinde yapilacak is KASITLI OLARAK
yapilmiyor (kilit uretmek masum bir commit'e bedel odetir), ikincisinde gercekten
yapacak is KALMAMISTIR ve birinin kalem kapatmasi gerekir.

TEK `HUKUM=` SATIRI basilir; `tasinabilir=<n>` jetonu YALNIZ o satirda gecer
(kapi ilk eslesmeyi okur — ikinci jeton hangi hukmun tuketildigini belirsiz birakirdi,
[[ayni-alan-iki-hukum-biri-sessiz]]).

=== EMNIYET ===
  * `--kuru` hicbir sey yazmaz (kapi bu bicimde cagirir).
  * flock (LOCK_EX|LOCK_NB) + atomik yazma (gecici dosya + fsync + os.replace).
    Kilit baskasindaysa rc=3 ve HICBIR SEY yazilmaz — sessiz basari YOK.
  * Ayristirma TUR-DONUSU ile dogrulanir: cozulen yapi BIREBIR geri kurulamiyorsa
    arac RC_KIRMIZI ile durur (yanlis ayristirilan bir indeks sessizce bozulamaz).
  * Yazmadan once `dogrula()` D1..D13 eksenini kosar; tek bir eksen bile duserse
    HICBIR SEY yazilmaz.

KABUL: python3 tools/hafiza-kota-kapisi-test.py   (AYRI tally; defter/kutu ile karisik degil)
KAPI : tools/defter-kota-kapisi.py  ucuncu eksen (HAFIZA_*) — tavani ve yolu BURADAN
       TURETIR, koda gomulu ikinci kopya ACMAZ ([[kapi-red-metni-ikinci-kopyadir]]).
"""
import argparse
import datetime
import fcntl
import os
import re
import sys
import tempfile

# --- TAVAN + SU SEVIYESI: TEK KAYNAK (bu dosya SAHIPTIR) ---------------------
# 🔴 Bu iki sayi baska hicbir yere KOPYALANMAZ. Kota kapisi bunlari sahipten okur;
# `defter-kota-kapisi.py::tek_kaynak_kontrol` ikinci bir sabit sahibini KIRMIZI yakar.
VARSAYILAN_TAVAN_BAYT = 16384
VARSAYILAN_TAVAN_SATIR = 45
SU_SEVIYESI_ORANI = 0.8

HAFIZA_VARSAYILAN = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/MEMORY.md")
ARSIV_VARSAYILAN = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/MEMORY-ARSIV.md")

RC_OK = 0
RC_KIRMIZI = 1      # tavan asili + tasinabilir tukendi / dogrulama dustu -> YAZILMADI
RC_KILIT = 3        # kilit baskasinda -> YAZILMADI (fail-closed)

ISARETCI_HEDEFI = "MEMORY-ARSIV.md"
ISARETCI_METNI = "[arşiv](" + ISARETCI_HEDEFI + ")"
KORUMALI_BOLUM_ONEKI = "Açık kuyruk"
KIRMIZI_ISARET = "🔴"

# dogrula()'nin bastigi iddia eksenleri; `lossless_dogrulama=GECTI (iddia=N)`
# satirindaki N BURADAN turer (elle yazilan sayi kaynagindan ayrisirdi).
IDDIA_EKSENLERI = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
                   "D11", "D12", "D13")

BOLUM_RE = re.compile(r"^(?P<ad>[^:\[]+:[ \t]*)(?P<govde>\S.*)$")
AYRAC_RE = re.compile(r",(?=\[)")
GIRDI_RE = re.compile(r"^\[(?P<etiket>[^\]]*)\]\((?P<hedef>[^)]+)\)(?P<kuyruk>.*)$",
                      re.S)


def su_seviyesi(tavan):
    """Tavandan ONARIM hedefini turetir. DAIMA tavanin ALTINDA kalir.

    Tavanla ESITLENEMEZ — esitlik tam da K353'te onarilan arizanin kendisidir.
    """
    if tavan is None:
        return None
    hedef = int(tavan * SU_SEVIYESI_ORANI)
    if hedef >= tavan:
        hedef = tavan - 1
    if hedef < 1:
        hedef = 1
    return hedef


SU_SEVIYESI_BAYT = su_seviyesi(VARSAYILAN_TAVAN_BAYT)
SU_SEVIYESI_SATIR = su_seviyesi(VARSAYILAN_TAVAN_SATIR)


# ---------------------------------------------------------------------------
# AYRISTIRMA
# ---------------------------------------------------------------------------
class Girdi(object):
    __slots__ = ("metin", "etiket", "hedef", "kuyruk", "tur", "bolum", "sira")

    def __init__(self, metin, tur, bolum, sira, etiket="", hedef="", kuyruk=""):
        self.metin = metin
        self.tur = tur              # "girdi" | "serbest"
        self.bolum = bolum
        self.sira = sira
        self.etiket = etiket
        self.hedef = hedef
        self.kuyruk = kuyruk

    @property
    def isaretci_mi(self):
        return ISARETCI_HEDEFI in self.metin and "](" in self.metin

    @property
    def kirmizi_mi(self):
        return KIRMIZI_ISARET in self.etiket


class Bolum(object):
    __slots__ = ("ad", "onek", "satir_no", "parcalar")

    def __init__(self, ad, onek, satir_no, parcalar):
        self.ad = ad
        self.onek = onek            # "Rol/ilke: " (iki nokta + bosluklar DAHIL)
        self.satir_no = satir_no
        self.parcalar = parcalar

    def govde(self, atlanan=()):
        return ",".join(p.metin for p in self.parcalar if p not in atlanan)

    def satir(self, atlanan=(), ek_parca=None):
        parcalar = [p.metin for p in self.parcalar if p not in atlanan]
        if ek_parca:
            parcalar.append(ek_parca)
        return self.onek + ",".join(parcalar)


def ayristir(metin):
    """(satirlar, bolumler) — TUR-DONUSU ile dogrulanir.

    Bolum satiri: bos olmayan, `](` iceren ve ilk `[` ONCESINDE `:` tasiyan satir.
    Gerisi (bos satirlar, olasi serbest metin) AYNEN korunur.
    """
    satirlar = metin.split("\n")
    bolumler = []
    for no, satir in enumerate(satirlar):
        if not satir.strip() or "](" not in satir:
            continue
        m = BOLUM_RE.match(satir)
        if not m:
            continue
        ad = m.group("ad").rstrip()
        if ad.endswith(":"):
            ad = ad[:-1]
        parcalar = []
        for sira, ham in enumerate(AYRAC_RE.split(m.group("govde"))):
            g = GIRDI_RE.match(ham)
            if g:
                parcalar.append(Girdi(ham, "girdi", ad, sira,
                                      g.group("etiket"), g.group("hedef"),
                                      g.group("kuyruk")))
            else:
                parcalar.append(Girdi(ham, "serbest", ad, sira))
        bolumler.append(Bolum(ad, m.group("ad"), no, parcalar))
    return satirlar, bolumler


def kur(satirlar, bolumler, atlanan=None, isaretci_eklenen=None):
    """Yapiyi metne geri kurar. atlanan bosken TUR-DONUSU = birebir ozgun metin."""
    atlanan = atlanan or set()
    isaretci_eklenen = isaretci_eklenen or set()
    yeni = list(satirlar)
    for b in bolumler:
        ek = ISARETCI_METNI if b.ad in isaretci_eklenen else None
        yeni[b.satir_no] = b.satir(atlanan=atlanan, ek_parca=ek)
    return "\n".join(yeni)


def yapisal_taban_satir(satirlar, bolumler):
    """Rotasyonun ULASABILECEGI EN KUCUK satir sayisi.

    🔴 Bolum BASLIKLARI korumalidir (kural iii): hicbir bolum satiri indeksten
    dusmez, aralarindaki ayrac satirlari da yerinde kalir. Yani satir ekseninin
    bir YAPISAL TABANI vardir ve su seviyesi bu tabanin ALTINDA olabilir. Bu hali
    sessizce "basarisizlik" saymak, tasima ile ULASILAMAYAN bir hedefi kilit
    gerekcesi yapmak olurdu; taban ADIYLA BASILIR.
    """
    return len("\n".join(satirlar).splitlines())


# ---------------------------------------------------------------------------
# KORUMA + ADAY SIRASI
# ---------------------------------------------------------------------------
def koruma_sebebi(parca, kok):
    """None = tasinabilir; aksi halde koruma sebebinin ADI."""
    if parca.tur != "girdi":
        return "SERBEST_PARCA"
    if parca.isaretci_mi:
        return "ARSIV_ISARETCISI"
    if parca.bolum.startswith(KORUMALI_BOLUM_ONEKI):
        return "ACIK_KUYRUK"
    if parca.kirmizi_mi:
        return "KIRMIZI"
    if not os.path.isfile(os.path.join(kok, parca.hedef)):
        return "HEDEF_YOK"
    return None


def adaylar(bolumler, kok):
    """(tasinabilir_sirali, koruma_sayaci) — sira DETERMINISTIK.

    Sira: hedef `.md` dosyasinin mtime'i ESKIDEN yeniye, esitlikte hedef ADINA,
    sonra bolum + ozgun sira. Ayni girdi kumesi ayni makinede DAIMA ayni sirayla
    tasinir (rastgelelik ya da sozluk sirasi YOK).
    """
    sayac = {}
    liste = []
    for b in bolumler:
        for p in b.parcalar:
            sebep = koruma_sebebi(p, kok)
            if sebep is None:
                yol = os.path.join(kok, p.hedef)
                try:
                    mt = os.path.getmtime(yol)
                except OSError:
                    continue
                liste.append((mt, p.hedef, p.bolum, p.sira, p))
            else:
                sayac[sebep] = sayac.get(sebep, 0) + 1
    liste.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return [t[4] for t in liste], sayac


# ---------------------------------------------------------------------------
# PLAN
# ---------------------------------------------------------------------------
class Plan(object):
    __slots__ = ("hukum", "rc", "tasinan", "tasinabilir", "korumali_kilitledi",
                 "koruma_sayaci", "once_bayt", "once_satir", "sonra_bayt",
                 "sonra_satir", "yeni_metin", "isaretci_eklenen", "taban_satir",
                 "su_bayt", "su_satir", "tavan_bayt", "tavan_satir",
                 "su_seviyesine_indi")


def tavan_asildi_mi(satir, bayt, tavan_satir, tavan_bayt):
    return satir > tavan_satir or bayt > tavan_bayt


def planla(metin, kok, tavan_bayt, tavan_satir, su_bayt, su_satir):
    """Tasima planini SAF olarak uretir (diskteki mtime disinda IO YOK)."""
    satirlar, bolumler = ayristir(metin)
    tur_donusu = kur(satirlar, bolumler)
    if tur_donusu != metin:
        raise ValueError("AYRISTIRMA TUR-DONUSU BOZUK — indeks guvenle cozulemedi")

    p = Plan()
    p.tavan_bayt = tavan_bayt
    p.tavan_satir = tavan_satir
    p.su_bayt = su_bayt
    p.su_satir = su_satir
    p.once_bayt = len(metin.encode("utf-8"))
    # 🔴 SATIR SAYIMI KAPIYLA AYNI SEMANTIKTE: kapi dosyayi `splitlines()` ile
    # olcer (kutu ekseninin `_kutu_olc`'i aynen boyle sayar). Burada `split("\n")`
    # kullansaydik sondaki newline yuzunden sahip 40, kapi 39 derdi — iki yuzeyin
    # SESSIZ AYRISMASI ([[ikiz-tanim-sessiz-ayrisma]]); kur() ic islerde ayni
    # `split("\n")`i kullanmaya devam eder (metni birebir geri kurmak icin sart).
    p.once_satir = len(metin.splitlines())
    p.taban_satir = yapisal_taban_satir(satirlar, bolumler)
    p.isaretci_eklenen = set()
    p.tasinan = []
    p.yeni_metin = metin
    p.sonra_bayt = p.once_bayt
    p.sonra_satir = p.once_satir

    sirali, sayac = adaylar(bolumler, kok)
    p.tasinabilir = len(sirali)
    p.koruma_sayaci = sayac
    p.korumali_kilitledi = sayac.get("KIRMIZI", 0) + sayac.get("ACIK_KUYRUK", 0)

    if not tavan_asildi_mi(p.once_satir, p.once_bayt, tavan_satir, tavan_bayt):
        p.hukum = "DOLU_NO_OP"
        p.rc = RC_OK
        p.su_seviyesine_indi = (p.once_bayt <= su_bayt)
        return p, satirlar, bolumler

    # Zaten var olan isaretcileri bul (ikinci isaretci ACILMAZ).
    isaretcili = set(b.ad for b in bolumler
                     for x in b.parcalar if x.isaretci_mi)

    atlanan = set()
    hedef_bayt = su_bayt
    for aday in sirali:
        atlanan.add(aday)
        if aday.bolum not in isaretcili:
            p.isaretci_eklenen.add(aday.bolum)
        aday_metin = kur(satirlar, bolumler, atlanan, p.isaretci_eklenen)
        p.tasinan.append(aday)
        p.yeni_metin = aday_metin
        p.sonra_bayt = len(aday_metin.encode("utf-8"))
        p.sonra_satir = len(aday_metin.splitlines())
        if p.sonra_bayt <= hedef_bayt and p.sonra_satir <= max(su_satir, p.taban_satir):
            break

    p.su_seviyesine_indi = (p.sonra_bayt <= su_bayt
                            and p.sonra_satir <= max(su_satir, p.taban_satir))

    if tavan_asildi_mi(p.sonra_satir, p.sonra_bayt, tavan_satir, tavan_bayt):
        # Tavanin ALTINA INILEMEDI. Yazma YOK: yarim tasima kilidi ACMAZ ama
        # indeksi bozar; hal ADIYLA basilir ve kalem kapatmak insana kalir.
        p.tasinan = []
        p.isaretci_eklenen = set()
        p.yeni_metin = metin
        p.sonra_bayt = p.once_bayt
        p.sonra_satir = p.once_satir
        if p.tasinabilir == 0 and p.korumali_kilitledi > 0:
            p.hukum = "KORUMA_TUTTU"
            p.rc = RC_OK
        else:
            p.hukum = "TAVAN_FAIL_LOUD"
            p.rc = RC_KIRMIZI
        return p, satirlar, bolumler

    p.hukum = "TAVAN_BASARILI"
    p.rc = RC_OK
    return p, satirlar, bolumler


# ---------------------------------------------------------------------------
# ARSIV METNI
# ---------------------------------------------------------------------------
def arsiv_eki(plan, tarih):
    """Arsive eklenecek metin + baslik-bloku bayti (h)."""
    parcalar = []
    onsoz = []
    if True:
        onsoz.append("\n## MEMORY.md indeksinden taşındı — %s "
                     "(tavan rotasyonu · hafiza-indeks-arsivle.py)\n\n" % tarih)
        onsoz.append(
            "Tavan %d B aşıldı (önce %d B / %d satır); hedef su seviyesi %d B. Taşınan "
            "yalnız İNDEKS GİRDİSİDİR — hafıza `.md` dosyalarının kendisi SİLİNMEDİ, "
            "TAŞINMADI, DEĞİŞTİRİLMEDİ; hepsi diskte duruyor ve `[[ad]]` ile hâlâ "
            "çağrılabilir.\n" % (plan.tavan_bayt, plan.once_bayt, plan.once_satir,
                                 plan.su_bayt))
    h = sum(len(x.encode("utf-8")) for x in onsoz)
    parcalar.extend(onsoz)

    gorulen = []
    for g in plan.tasinan:
        if g.bolum not in gorulen:
            gorulen.append(g.bolum)
    for bolum in gorulen:
        baslik = "\n### %s\n" % bolum
        h += len(baslik.encode("utf-8"))
        parcalar.append(baslik)
        for g in plan.tasinan:
            if g.bolum == bolum:
                parcalar.append("- " + g.metin + "\n")
    return "".join(parcalar), h


def arsiv_birlestir(arsiv_metin, ek):
    """Append-only: eski metin yeni metnin ONEKIDIR. Eksik newline h'ye sayilir."""
    ayrac = ""
    if arsiv_metin and not arsiv_metin.endswith("\n"):
        ayrac = "\n"
    return arsiv_metin + ayrac + ek, len(ayrac.encode("utf-8"))


# ---------------------------------------------------------------------------
# DOGRULAMA (D1..D13) — tek eksen duserse HICBIR SEY YAZILMAZ
# ---------------------------------------------------------------------------
def dogrula(metin, yeni_metin, arsiv_metin, yeni_arsiv, plan, h, kok):
    hatalar = []
    satirlar, bolumler = ayristir(metin)
    _, yeni_bolumler = ayristir(yeni_metin)
    tasinan_kimlik = set((g.bolum, g.metin) for g in plan.tasinan)

    # D1 — ayristirma tur-donusu (ozgun metin birebir geri kuruldu)
    if kur(satirlar, bolumler) != metin:
        hatalar.append("D1 ayristirma TUR-DONUSU bozuk")

    # D2 — girdi muhasebesi: kalan + tasinan == once
    once_girdi = sum(1 for b in bolumler for p in b.parcalar if p.tur == "girdi")
    kalan_girdi = sum(1 for b in yeni_bolumler for p in b.parcalar if p.tur == "girdi")
    eklenen_isaretci = len(plan.isaretci_eklenen)
    if kalan_girdi - eklenen_isaretci + len(plan.tasinan) != once_girdi:
        hatalar.append("D2 girdi muhasebesi tutmadi: once=%d kalan=%d(-%d isaretci) "
                       "tasinan=%d" % (once_girdi, kalan_girdi, eklenen_isaretci,
                                       len(plan.tasinan)))

    # D3 — tasinan her girdinin TAM METNI yeni arsivde
    eksik = [g.metin for g in plan.tasinan if g.metin not in yeni_arsiv]
    if eksik:
        hatalar.append("D3 tasinan %d girdi arsivde YOK (ilk: %s)"
                       % (len(eksik), eksik[0][:60]))

    # D4 — tasinmayan her girdinin TAM METNI yeni indekste
    kayip = [p.metin for b in bolumler for p in b.parcalar
             if (p.bolum, p.metin) not in tasinan_kimlik
             and p.metin not in yeni_metin]
    if kayip:
        hatalar.append("D4 tasinmayan %d girdi indeksten DUSMUS (ilk: %s)"
                       % (len(kayip), kayip[0][:60]))

    # D5 — KORUMA: tasinan hicbir girdi 🔴 tasimaz
    kirmizi = [g.metin for g in plan.tasinan if g.kirmizi_mi]
    if kirmizi:
        hatalar.append("D5 KORUMA IHLALI: %d KIRMIZI girdi tasinmis (ilk: %s)"
                       % (len(kirmizi), kirmizi[0][:60]))

    # D6 — KORUMA: "Acik kuyruk" bolumunden tasinan = 0
    kuyruk = [g.metin for g in plan.tasinan
              if g.bolum.startswith(KORUMALI_BOLUM_ONEKI)]
    if kuyruk:
        hatalar.append("D6 KORUMA IHLALI: Acik kuyruk bolumunden %d girdi tasinmis"
                       % len(kuyruk))

    # D7 — bolum basliklari ve SIRASI degismedi
    if [b.ad for b in bolumler] != [b.ad for b in yeni_bolumler]:
        hatalar.append("D7 bolum basliklari/sirasi DEGISTI")

    # D8 — bag butunlugu: tasinan her girdinin hedefi diskte VAR
    yok = [g.hedef for g in plan.tasinan
           if not os.path.isfile(os.path.join(kok, g.hedef))]
    if yok:
        hatalar.append("D8 bag butunlugu: %d hedef diskte YOK (ilk: %s)"
                       % (len(yok), yok[0]))

    # D9 — arsiv APPEND-ONLY (eski metin yeninin oneki)
    if not yeni_arsiv.startswith(arsiv_metin):
        hatalar.append("D9 arsiv append-only DEGIL: eski metin yeninin oneki degil")

    # D10 — bolum basina EN FAZLA bir arsiv isaretcisi
    for b in yeni_bolumler:
        n = sum(1 for p in b.parcalar if p.isaretci_mi)
        if n > 1:
            hatalar.append("D10 '%s' bolumunde %d arsiv isaretcisi (tavan 1)"
                           % (b.ad, n))

    # D11 — BAYT MUHASEBESI: sapma = h + 3n - indeks_duzeltmesi (denklem TUTMALI)
    n = len(plan.tasinan)
    dusen = len(metin.encode("utf-8")) - len(yeni_metin.encode("utf-8"))
    artan = len(yeni_arsiv.encode("utf-8")) - len(arsiv_metin.encode("utf-8"))
    girdi_bayt = sum(len(g.metin.encode("utf-8")) for g in plan.tasinan)
    duzeltme = dusen - girdi_bayt         # ayrac dususu - eklenen isaretciler
    beklenen = h + 3 * n - duzeltme
    if artan - dusen != beklenen:
        hatalar.append("D11 bayt denklemi TUTMADI: sapma=%d beklenen=%d "
                       "(dusen=%d artan=%d h=%d n=%d duzeltme=%d)"
                       % (artan - dusen, beklenen, dusen, artan, h, n, duzeltme))

    # D12 — tasinan girdi sayisi kadar madde satiri arsivde
    madde = sum(1 for s in yeni_arsiv[len(arsiv_metin):].split("\n")
                if s.startswith("- "))
    if madde != n:
        hatalar.append("D12 arsive eklenen madde satiri %d, tasinan %d" % (madde, n))

    # D13 — satir korunumu: baslik korumasi geregi satir sayisi DUSMEZ/ARTMAZ
    if len(yeni_metin.splitlines()) != len(metin.splitlines()):
        hatalar.append("D13 satir sayisi degisti (baslik korumasi ihlali)")

    return hatalar


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------
def oku(yol):
    try:
        with open(yol, "rb") as f:
            return f.read().decode("utf-8")
    except FileNotFoundError:
        return None
    except OSError as e:
        raise SystemExit("HATA: okunamadi %s -> %s" % (yol, e))


def kilit_al(yol):
    """(fd, hata) — LOCK_EX|LOCK_NB. Kilit baskasindaysa fd None (rc=3)."""
    try:
        fd = open(yol, "a+")
    except OSError as e:
        return None, "kilit dosyasi acilamadi: %s -> %s" % (yol, e)
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        fd.close()
        return None, "kilit BASKASINDA (%s): %s" % (yol, e)
    return fd, None


def kilit_birak(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    finally:
        fd.close()


def atomik_yaz(yol, metin):
    """Gecici dosya + fsync + os.replace. Kismi/yarim dosya GORUNMEZ."""
    dizin = os.path.dirname(os.path.abspath(yol)) or "."
    kip = os.stat(yol).st_mode & 0o777 if os.path.exists(yol) else None
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".hafiza-indeks-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(metin)
            f.flush()
            os.fsync(f.fileno())
        if kip is not None:
            os.chmod(gecici, kip)
        os.replace(gecici, yol)
        gecici = None
    finally:
        if gecici and os.path.exists(gecici):
            os.unlink(gecici)


# ---------------------------------------------------------------------------
# ANA
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="MEMORY.md indeksinin tavan sahibi + LOSSLESS rotasyon araci")
    ap.add_argument("--hafiza", default=HAFIZA_VARSAYILAN)
    ap.add_argument("--arsiv", default=ARSIV_VARSAYILAN)
    ap.add_argument("--kilit", default=None,
                    help="varsayilan: indeks ile ayni dizinde .<ad>.lock")
    ap.add_argument("--kuru", action="store_true",
                    help="KURU KOSUM — hicbir sey yazilmaz (kapi bunu cagirir)")
    ap.add_argument("--tavan-bayt", type=int, default=None)
    ap.add_argument("--tavan-satir", type=int, default=None)
    ap.add_argument("--su-seviye-orani", type=float, default=None)
    ap.add_argument("--tarih", default=None)
    a = ap.parse_args(argv)

    hafiza_yolu = os.path.abspath(os.path.expanduser(a.hafiza))
    arsiv_yolu = os.path.abspath(os.path.expanduser(a.arsiv))
    kilit_yolu = a.kilit or os.path.join(os.path.dirname(hafiza_yolu),
                                         "." + os.path.basename(hafiza_yolu) + ".lock")
    kok = os.path.dirname(hafiza_yolu)

    tavan_bayt = a.tavan_bayt if a.tavan_bayt is not None else VARSAYILAN_TAVAN_BAYT
    tavan_satir = a.tavan_satir if a.tavan_satir is not None else VARSAYILAN_TAVAN_SATIR
    oran = a.su_seviye_orani if a.su_seviye_orani is not None else SU_SEVIYESI_ORANI
    su_bayt = max(1, min(int(tavan_bayt * oran), tavan_bayt - 1))
    su_satir = max(1, min(int(tavan_satir * oran), tavan_satir - 1))
    tarih = a.tarih or datetime.date.today().isoformat()

    fd, hata = kilit_al(kilit_yolu)
    if fd is None:
        print("!! KILIT ALINAMADI — HICBIR SEY YAZILMADI: %s" % hata, file=sys.stderr)
        return RC_KILIT
    try:
        metin = oku(hafiza_yolu)
        if metin is None:
            print("!! INDEKS YOK: %s — olculemeyen sey yesil sayilmaz." % hafiza_yolu,
                  file=sys.stderr)
            return RC_KIRMIZI
        arsiv_metin = oku(arsiv_yolu)
        arsiv_var = arsiv_metin is not None
        if arsiv_metin is None:
            arsiv_metin = ""

        try:
            plan, _satirlar, bolumler = planla(metin, kok, tavan_bayt, tavan_satir,
                                               su_bayt, su_satir)
        except ValueError as e:
            print("!! %s — HICBIR SEY YAZILMADI (fail-closed)." % e, file=sys.stderr)
            return RC_KIRMIZI

        girdi_sayisi = sum(1 for b in bolumler for p in b.parcalar if p.tur == "girdi")
        print("ONCE bayt=%d satir=%d bolum=%d girdi=%d indeks=%s"
              % (plan.once_bayt, plan.once_satir, len(bolumler), girdi_sayisi,
                 hafiza_yolu))
        print("TAVAN bayt=%d satir=%d  SU_SEVIYESI bayt=%d satir=%d "
              "yapisal_taban_satir=%d"
              % (tavan_bayt, tavan_satir, su_bayt, su_satir, plan.taban_satir))
        if su_satir < plan.taban_satir:
            print("   (SATIR su seviyesi (%d) YAPISAL TABANIN (%d) ALTINDA: bolum "
                  "BASLIKLARI korumalidir, rotasyon satir dusuremez. Satir ekseninin "
                  "onarim hedefi bu kosumda TABANDIR; tavan (%d) asilmadigi surece "
                  "kilit URETILMEZ.)" % (su_satir, plan.taban_satir, tavan_satir))
        print("KORUMA %s" % (" ".join("%s=%d" % (k, v)
                                      for k, v in sorted(plan.koruma_sayaci.items()))
                             or "yok"))

        if plan.hukum == "DOLU_NO_OP":
            print("TAVAN=DOLU_NO_OP")
            print("HUKUM=DOLU_NO_OP rc=0 once_bayt=%d tavan_bayt=%d tasinabilir=%d "
                  "KORUMALI_BEKLEYEN=%d sebep=tavan ALTINDA, is yok (dosya BAYT BAYT "
                  "AYNI)" % (plan.once_bayt, tavan_bayt, plan.tasinabilir,
                             plan.korumali_kilitledi))
            return RC_OK

        if plan.hukum == "KORUMA_TUTTU":
            print("HUKUM=KORUMA_TUTTU rc=0 tasinabilir=0 KORUMALI_BEKLEYEN=%d "
                  "once_bayt=%d tavan_bayt=%d sebep=tasinabilir girdi YOK; kilitleyen "
                  "KORUMADIR (🔴 girdi ve/veya Acik kuyruk). Indeks tavanin USTUNDE "
                  "kalabilir — GORUNURLUK kota kirmizisina tercih edilir (Okan kurali "
                  "⑤); hal GIZLENMEDI, BASILDI."
                  % (plan.korumali_kilitledi, plan.once_bayt, tavan_bayt))
            return RC_OK

        if plan.hukum == "TAVAN_FAIL_LOUD":
            print("!! HUKUM=TAVAN_FAIL_LOUD rc=1 tasinabilir=%d KORUMALI_BEKLEYEN=%d "
                  "once_bayt=%d once_satir=%d tavan_bayt=%d tavan_satir=%d "
                  "sebep=tasinabilir icerik TUKENDI, indeks tavanin ALTINA inemiyor. "
                  "HICBIR SEY YAZILMADI." % (plan.tasinabilir, plan.korumali_kilitledi,
                                             plan.once_bayt, plan.once_satir,
                                             tavan_bayt, tavan_satir), file=sys.stderr)
            print("!! CARE: bu noktada oda acmanin yolu rotasyon DEGIL, KALEM "
                  "KAPATMAKTIR — indeksteki 🔴 girdilerden yururlukten dusenleri "
                  "MIMAR HUKMUYLE arsive al.", file=sys.stderr)
            return RC_KIRMIZI

        # --- TAVAN_BASARILI: ek + dogrulama --------------------------------
        ek, h_ek = arsiv_eki(plan, tarih)
        yeni_arsiv, h_ayrac = arsiv_birlestir(arsiv_metin, ek)
        h = h_ek + h_ayrac
        hatalar = dogrula(metin, plan.yeni_metin, arsiv_metin, yeni_arsiv, plan, h, kok)

        n = len(plan.tasinan)
        dusen = plan.once_bayt - plan.sonra_bayt
        artan = len(yeni_arsiv.encode("utf-8")) - len(arsiv_metin.encode("utf-8"))
        girdi_bayt = sum(len(g.metin.encode("utf-8")) for g in plan.tasinan)
        duzeltme = dusen - girdi_bayt
        print("tasinan_girdi=%d bolum_sayisi=%d isaretci_eklenen=%d"
              % (n, len(set(g.bolum for g in plan.tasinan)),
                 len(plan.isaretci_eklenen)))
        print("SONRA bayt=%d satir=%d (su seviyesi %d %s)"
              % (plan.sonra_bayt, plan.sonra_satir, su_bayt,
                 "ALTINDA" if plan.sonra_bayt <= su_bayt else "USTUNDE (BEST-EFFORT)"))
        print("KAYIPSIZLIK bayt: once=%d sonra=%d dusen=%d | arsiv_once=%d "
              "arsiv_sonra=%d artan=%d | sapma=%d"
              % (plan.once_bayt, plan.sonra_bayt, dusen,
                 len(arsiv_metin.encode("utf-8")),
                 len(yeni_arsiv.encode("utf-8")), artan, artan - dusen))
        print("SAPMA_BILESENLERI: arsiv_baslik_bloklari=+%d madde_onekleri=+%d "
              "indeks_ayrac_ve_isaretci_duzeltmesi=%+d  -> beklenen=%d"
              % (h, 3 * n, -duzeltme, h + 3 * n - duzeltme))
        print("arsiv_yeni_dosya=%s" % ("hayir" if arsiv_var else "EVET"))

        if hatalar:
            print("!! LOSSLESS DOGRULAMASI KIRMIZI — HICBIR SEY YAZILMADI:",
                  file=sys.stderr)
            for x in hatalar:
                print("!!   - %s" % x, file=sys.stderr)
            return RC_KIRMIZI
        print("lossless_dogrulama=GECTI (iddia=%d)" % len(IDDIA_EKSENLERI))

        print("HUKUM=TAVAN_BASARILI rc=0 tasinabilir=%d KORUMALI_BEKLEYEN=%d "
              "tasinan=%d sonra_bayt=%d sonra_satir=%d tavan_bayt=%d su_bayt=%d "
              "su_seviyesine_indi=%s"
              % (plan.tasinabilir, plan.korumali_kilitledi, n, plan.sonra_bayt,
                 plan.sonra_satir, tavan_bayt, su_bayt,
                 "EVET" if plan.su_seviyesine_indi else "HAYIR/BEST-EFFORT"))

        if a.kuru:
            print("KURU KOSUM — hicbir sey yazilmadi.")
            return RC_OK

        atomik_yaz(arsiv_yolu, yeni_arsiv)
        atomik_yaz(hafiza_yolu, plan.yeni_metin)
        print("YAZILDI: %s + %s" % (hafiza_yolu, arsiv_yolu))
        return RC_OK
    finally:
        kilit_birak(fd)


if __name__ == "__main__":
    sys.exit(main())
