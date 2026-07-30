#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONIZLEME DERLEYICI IMAJI — DRIFT + KAPSAM KAPISI (G2).

DURUST ETIKET (once bunu oku):
  Bu bir DISIPLIN / DRIFT kapisidir, GUVENLIK SINIRI DEGILDIR. Kanitladigi tek sey
  "imajin tasidigi .scad anlik goruntusu, repo HEAD'deki parmakizi kaydiyla ayni mi"
  ve "sitenin musteriye actigi her aile bu imajda GERCEKTEN derleniyor mu". Imajin
  guvenli oldugunu, uretecin dogru geometri urettigini ya da paketin kaynaginin
  saglam oldugunu KANITLAMAZ. Parmakizi kaydini yazan da paketi toplayan araciTIR
  (tools/onizleme-paket-yukle.py) — yani kotu niyetli bir yazar ikisini birlikte
  degistirebilir; kapi ONU yakalamaz. Yakaladigi sey KAZA'dir: paket guncellenip
  imaj yenilenmemesi, imaj yenilenip aile listesinin geride kalmasi, elle duzenlenmis
  bir .scad'in pakete sizmasi.

NEDEN VAR — olculmus iki delik:
  (1) DRIFT: uretec .scad'lari repo/kaynak tarafinda degisince jenerator CI YESIL
      yanar, ama derleyici imajina GOMULU anlik goruntu (Dockerfile: COPY paket-ozel/
      /srv/paket/) ESKI kalir. Calisma aninda R2 OKUNMAZ — imaj neyi tasiyorsa onu
      servis eder. 27 Tem'de toka bu yolla imajsiz kaldi (canli 404 "aile-yok",
      musteri "Onizleme olusturulamadi" gordu).
  (2) KAPSAM: duman testi ACIK/SABIT bir aile listesi (elle yazilmis 12 curl)
      uzerinden kosuyordu -> repoya yeni bir uretec ailesi eklenince duman testi onu
      HIC denemiyor, aile sessizce servis-disi kaliyordu.

BU DOSYANIN IKI KOMUTU:
  parmakizi-yaz     <paket_dizin>            -> repo HEAD kaydini (uret)/tazele
  parmakizi-dogrula --dizin D | --url U      -> KAYIT vs GERCEK; farkliysa exit 1,
                                                DRIFT EDEN DOSYAYI ADIYLA soyler
  duman             --url U                  -> DIZIN TARAMASIYLA uretilen aile
                                                listesini servise gercekten derletir

30 TEM ONARIM TURU (tur 3) — curutme turunun kapattigi alti delik:
  O2 KAPSAM   : kayit ARTIK paketin TUM dosyalarini tasir (uzanti beyaz listesi YOK).
                Eskiden yalniz `*.scad` hash'leniyordu ve `eslem-ozel.json` — aile->uretec
                eslemesi, katsayilar, `varyantlar`, yani GEOMETRIYI BELIRLEYEN yari —
                kapsam DISINDAYDI (olculdu: katsayi 1->1000, uc kapi da YESIL).
                Kayit surumu 1 -> 2; surum 1 kayitlari FAIL-CLOSED reddedilir.
  O3 BOS KUME : dogrulayici tarafinda ALT SINIR nobeti (bos kayit / bos paket / bos
                ONIZLEME_AILELER / bos sema dizini) — nobet eskiden yalniz YAZICIDAYDI,
                bos kayit + bos paket sessizce YESIL yaniyordu.
  O4 CAPRAZ   : "N/N kapsandi" ARTIK servisin kendi beyani degil. Servis `/parmakizi`
                beyani repo HEAD KAYDIYLA caprazlanir (ayrisirsa KAYIT KAZANIR),
                `/kapsam` beyani repo SEMASIYLA caprazlanir, ve eslemin PAKETTE OLMAYAN
                bir .scad'i surmesi (ters yon) yakalanir.
  O5 KISIT    : 🔴 GERI ALINDI — bkz. O8 (asagida). "Kisitla kapali" SINIFI ARTIK YOK.
  O1/O6       : CI cagri satiri nobeti tools/is-akisi-kapisi.py BOLUM B'ye baglandi
                (bu dosyanin ci-kapsam muafiyeti oradaki iddiaya KILITLI — B-CAPRAZ).
  O7          : kayittaki adlarin JENERIK kalmasi tools/kisisel-veri-test.py'de
                bloklayici nobetle zorlanir (marka/yol/e-posta/URL -> KIRMIZI).

30 TEM DAR ONARIM TURU (tur 5) — dogrulama turunun (tur 4) actigi iki delik:
  O8 KISIT    : 🔴 O5'IN ACTIGI MASKELEME KANALI KAPATILDI (D4). O5, ONIZLEME_KISITLAR
                ile kapatilan bir varyantin .scad'ini olu-uretec olcumunun DISINA
                cikariyordu. Olculdu (tur 4/M2-M3): pakete gercek bir olu .scad koyup
                (a) eslem-ozel.json'da onu SEMADA YASAL bir secici degerinin ureteci
                diye bildirmek, (b) secenekler.js'te o degeri kisitlamak — iki dosyada
                birer satir — dosyayi "kisitla kapali" saydirip kapiyi YESIL geciriyordu.
                Ustelik kisit sonradan GEVSETILDIGINDE hic derlenmemis o ureteci
                musteriye acan bloklayici kapi YOK (duman yalniz workflow_dispatch'te).
                ONARIM — KAVRAM DUZELTMESI: **kisit MUSTERI EVRENINI daraltir, IMAJ
                KABILIYETINI daraltmaz.** Duman testi imajin kabiliyetini olcer; bu
                yuzden `istek_setleri` artik AYRI bir .scad suren HER secici degerini
                ONIZLEME_KISITLAR'a BAKMADAN derletir. Sonuc: (i) Ç8/FP5 sahte-kirmizisi
                kaynagindan kalkti (dosya artik atlanmiyor, DERLENIYOR), (ii) "kisitla
                kapali" hukmu — dolayisiyla maskeleme kanali — TAMAMEN YOK OLDU,
                (iii) kisit gevsetmesi kapsami DEGISTIREMEZ. Invaryant makineye baglandi:
                `kisit_kapsam_kusurlari()` her ailede "kisitli plan == kisitsiz plan"
                oldugunu olcer; biri kisit-itaatini geri koyarsa KIRMIZI yanar.
  O9 KAYIT    : parmakizi kaydi ARTIK uretildigi R2 paket anahtarini tasir
                (`paket_anahtar`) ve `parmakizi-dogrula --paket-anahtar` bunu CI'nin
                tetiklendigi anahtarla CAPRAZLAR. Tur 4/D8 olcumu: is akisi yukleyiciyi
                HIC cagirmiyor ve `paket_anahtar` serbest metindi -> R2'de duran ESKI
                bir anahtarla is tetiklenip kayit-paket uyumsuzlugu sessiz kalabiliyordu.
  D2 YAPI     : paket dizini DUZ olmali — alt dizin bulunursa FAIL-CLOSED
                (`paket_yapi_kusurlari`). Olculdu: alt dizindeki dosyalar ne kayda ne
                servisin /parmakizi beyanina giriyordu (iki taraf da `os.listdir` +
                `isfile` kullanir) -> `include <alt/x.scad>` ile geometriyi belirleyen
                bir dosya parmakizi kapsaminin DISINDA kalabilirdi.

"REPO HEAD'DEKI PAKET KAYDI" NE DEMEK (kapsam durustlugu):
  .scad KAYNAKLARI BU PUBLIC REPODA DEGILDIR (uyelik ureteclerinin kodu gizli;
  bizim ureteclerimiz ayri depoda: pruvo-jenerator/jeneratorler). Repo HEAD'de
  duran sey iceriklerin SHA-256 PARMAKIZI KAYDIdir:
      onizleme/derleyici/paket-parmakizi.json
  Kayit, paketi toplayan tek yazar (tools/onizleme-paket-yukle.py) tarafindan
  paketin TA KENDISINDEN uretilir. Dolayisiyla "hash duzeyinde esitlik" iddiasi
  sudur: imajin tasidigi anlik goruntu == paket yuklendigi andaki icerik.
  Dosya ADLARI kayda ACIK yazilir; bu, deponun ONCEDEN VERILMIS karariyla uyumludur
  (onizleme-imaj.yml: "paket kaynagi ... dosyalar (adlar sir degil, icerik loglanmaz)"
  ve adim `ls paket-ozel` ciktisini public CI logunda zaten basar). ICERIK asla
  yazilmaz/loglanmaz — yalniz ozet.

AILE LISTESI NEREDEN GELIR (sabit liste YOK):
  * jenerator/urunler/*.json  -> DIZIN TARAMASI. Her dosya bir uretec ailesinin
    sema'sidir; parametre varsayilanlari duman istegini kurar. Yeni aile eklenince
    dosya kendiliginden taramaya girer.
  * secenekler.js ONIZLEME_AILELER -> musteriye ACILAN aileler (tek kaynak; Worker
    ve build.py da bunu okur). Bu kumedeki BIR aile /saglik'ta yoksa KIRMIZI:
    27 Tem toka kanamasinin tam sinifi.
  * GET /saglik -> imajin GERCEKTEN servis ettigi aileler. Semasi olan her servis
    ailesi de derletilir (paketteki fazladan aile sessizce denenmemis kalmasin).

KOMUT SATIRI:
  python3 tools/onizleme-kapisi.py parmakizi-yaz --dizin /tmp/paket
  python3 tools/onizleme-kapisi.py parmakizi-dogrula --dizin onizleme/derleyici/paket-ozel
  python3 tools/onizleme-kapisi.py parmakizi-dogrula --url http://127.0.0.1:18080
  python3 tools/onizleme-kapisi.py duman --url http://127.0.0.1:18080
Cikis kodu: 0 = YESIL, 1 = KIRMIZI (her kusur ayri satirda, dosya/aile ADIYLA).

KAPSAM (jeton ekseni, bilincli DAR): bu kapi YALNIZ .github/workflows/onizleme-imaj.yml
icinde kosar. Ana site yayini (deploy.yml -> GitHub Pages) bu kapiya BAGLI DEGILDIR —
alakasiz bir CSS/veri/`.md` duzenlemesi buradan KIRMIZI alip TUM SITE deploy'unu
durduramaz. Kabul testi: onizleme/test/duman_kabul.py
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
VARSAYILAN_MANIFEST = os.path.join(ROOT, "onizleme", "derleyici", "paket-parmakizi.json")
VARSAYILAN_SEMA_DIZIN = os.path.join(ROOT, "jenerator", "urunler")
VARSAYILAN_SECENEKLER = os.path.join(ROOT, "secenekler.js")
# SURUM 2 (30 Tem, O2 onarimi): kayit ARTIK paketin TUM dosyalarini tasir, yalniz
# *.scad'leri DEGIL. Surum 1 kayitlari FAIL-CLOSED reddedilir (asagida manifest_oku).
MANIFEST_SURUM = 2
ALGORITMA = "sha256"

# 🔴 UZANTI BEYAZ LISTESI YOK — BILINCLI (O2 onarimi, curutme turu Ç2-C).
# OLCULDU: kayit yalniz `*.scad` hash'lerken `eslem-ozel.json` (aile->uretec eslemesi,
# katsayilar, tablolar, `varyantlar`) parmakizi kapsaminin DISINDA kaliyordu; katsayi
# 1 -> 1000 degistirildiginde UC kapi da (parmakizi --dizin / --url, duman) YESIL kaldi.
# Yani kapi "imajin tasidigi paket repo kaydiyla ayni mi" derken paketin YARISINI
# olcuyordu. Artik paket dizinindeki HER duz dosya hash'lenir.
# HARIC TUTULAN: HICBIR SEY. Dizinler atlanir (paket DUZ bir dizindir; topla() duz
# yazar, Dockerfile `COPY paket-ozel/ /srv/paket/` ile duz kopyalar). Gecici/isletim
# sistemi dosyasi (`.DS_Store`, `__pycache__`) icin ISTISNA ACILMADI: CI paketi temiz
# bir `tar -xzf` ile kurar, ve pakete oraya ait olmayan bir dosya girmesi DRIFT/FAZLA
# olarak KONUSULMASI gereken bir olaydir (sessizce elenmesi gereken degil).
PAKET_HARIC = frozenset()


# --------------------------------------------------------------- parmakizi (B)

def _dosya_ozeti(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(65536), b""):
            h.update(blok)
    return h.hexdigest()


def paket_parmakizlari(dizin):
    """DIZIN TARAMASI: <dizin> altindaki HER duz dosyanin sha256'si (uzanti suzgeci YOK).

    Sabit dosya listesi YOK -> pakete giren yeni uretec de, yeni bir dosya TURU de
    (`.json`, `.txt`, ...) kendiliginden kapsanir. Alt dizinlere INILMEZ."""
    out = {}
    for ad in sorted(os.listdir(dizin)):
        if ad in PAKET_HARIC:
            continue
        yol = os.path.join(dizin, ad)
        if not os.path.isfile(yol):
            continue
        out[ad] = _dosya_ozeti(yol)
    return out


def paket_yapi_kusurlari(dizin):
    """D2 (tur 5) — PAKET DIZINI DUZ MU? Alt dizin varsa FAIL-CLOSED kusur dondurur.

    OLCULDU (tur 5): `paket_parmakizlari` ve server.py::paket_parmakizlari AYNI kurali
    kullanir — `os.listdir` + `os.path.isfile`, alt dizinlere INILMEZ. Yani bir alt
    dizindeki dosya NE kayda NE servisin /parmakizi beyanina girer: iki taraf da ayni
    korlukte oldugu icin `parmakizi_farklari` de sessiz kalir (kor nokta simetrik).
    OpenSCAD `include <alt/ortak.scad>` yazabildigi icin bu, GEOMETRIYI BELIRLEYEN bir
    dosyanin parmakizi kapsaminin tamamen DISINDA kalmasi demektir.
    Cozum kapsami GENISLETMEK degil (o, kaydin anahtar bicimini ve server.py'yi birlikte
    degistirir); paketin ZATEN BEYAN EDILMIS "duz dizin" sozlesmesini MAKINEYE baglamak:
    alt dizin gorulurse kapi KIRMIZI yanar ve dosya paketten cikarilir.

    KAPSAM SINIRI (beyan): bu kontrol yalniz `--dizin` yolunda (CI'da docker build'den
    ONCE, cekilen paket uzerinde) kosar. `--url` yolunda kosan imaja "alt dizinin var mi"
    diye sorulamaz (server.py boyle bir uc sunmuyor); o eksende olcum YOK.

    Ayrica DIGER kapsam siniflari OLCULDU ve BEYAN edilir (tur 5/D2):
      * sembolik bag  -> `os.path.isfile` bagi IZLER; hedef duz dosyaysa KAPSANIR
                         (icerik hash'lenir). Kirik bag `isfile` False doner -> sessizce
                         atlanir; asagida ayri kusur olarak yakalanir.
      * bos dosya     -> KAPSANIR (bos icerigin sha256'si).
      * yalniz IZIN BITI degisen dosya -> KAPSANMAZ. Kayit ICERIK eksenindedir; izin biti
                         tar arsivinden imaja gecer ama geometriye etki etmez. BEYAN.
      * BOM'lu / CRLF'li dosya -> KAPSANIR (bayt duzeyi hash; BOM ya da satir sonu
                         degisimi ICERIK degisimidir ve DRIFT/ICERIK olarak konusur)."""
    kusurlar = []
    for ad in sorted(os.listdir(dizin)):
        yol = os.path.join(dizin, ad)
        if os.path.isdir(yol):
            icerik = sorted(os.listdir(yol))[:5]
            kusurlar.append(
                "PAKET DUZ DEGIL: '%s' bir ALT DIZIN (%d giris%s) -> alt dizindeki "
                "dosyalar ne parmakizi kaydina ne imajin /parmakizi beyanina girer "
                "(iki taraf da yalniz duz dosyalari tarar), yani `include <%s/...>` ile "
                "GEOMETRIYI BELIRLEYEN bir dosya olcum disinda kalir (fail-closed). "
                "COZUM: paketi duzlestirin — tools/onizleme-paket-yukle.py::topla() duz "
                "yazar; alt dizin elle sizmis demektir."
                % (ad, len(icerik), (": " + ", ".join(icerik)) if icerik else "", ad))
        elif not os.path.isfile(yol):
            kusurlar.append(
                "PAKET GIRISI DOSYA DEGIL: '%s' duz dosya da dizin de degil (kirik "
                "sembolik bag / soket / fifo?) -> hash'lenemez ve SESSIZCE atlanirdi "
                "(fail-closed)." % ad)
    return kusurlar


def scad_alt_kumesi(parmakizlari):
    """Parmakizi sozlugunun yalniz *.scad kismi (olu-uretec olcumu bunu kullanir).
    TUREV bir gorunumdur — ikinci bir tarama/kayit DEGIL (tek kaynak: paket kaydi)."""
    return {ad: oz for ad, oz in parmakizlari.items() if ad.endswith(".scad")}


def scad_parmakizlari(dizin):
    """Geriye donuk ad: paket taramasinin *.scad gorunumu."""
    return scad_alt_kumesi(paket_parmakizlari(dizin))


def manifest_oku(yol):
    """Parmakizi kaydini oku -> {ad: ozet}. Dosya yoksa/bozuksa FAIL-CLOSED istisna.

    SURUM NOBETI (O2): surum 1 kayitlari yalniz `*.scad` tasiyordu; sessizce kabul
    edilirlerse kapi paketin YARISINI olcmeye geri doner. O yuzden eski surum
    ACIKCA reddedilir ve tek satirlik cozum talimati verilir."""
    with open(yol, "r", encoding="utf-8") as f:
        veri = json.load(f)
    surum = veri.get("surum")
    if surum != MANIFEST_SURUM:
        raise ValueError(
            "parmakizi kaydi ESKI SURUM (%r; beklenen %d) -> bu kayit paketin yalniz "
            "*.scad yarisini tasiyor, `eslem-ozel.json` gibi GEOMETRIYI BELIRLEYEN "
            "dosyalar olculmemis olur (fail-closed). "
            "COZUM (TEK SATIR, paketi toplayan makinede): python3 "
            "tools/onizleme-paket-yukle.py  -> paketi R2'ye yukler, bu kaydi surum %d "
            "olarak paketin TA KENDISINDEN uretir ve R2 anahtarini kayda yazar. "
            "🔴 SONRA: kaydi COMMIT + PUSH edin, ancak ondan sonra onizleme-imaj.yml'yi "
            "o ciktidaki 'R2 ANAHTARI' degeriyle tetikleyin — is akisi yukleyiciyi "
            "CAGIRMAZ ve repo HEAD'ini checkout eder, yani commit'lenmemis kayit CI'da "
            "GORUNMEZ (kilit KENDILIGINDEN COZULMEZ; tur 4/D8 olcumu)."
            % (surum, MANIFEST_SURUM, MANIFEST_SURUM))
    dosyalar = veri.get("dosyalar")
    if not isinstance(dosyalar, dict):
        raise ValueError("parmakizi kaydinda 'dosyalar' sozlugu yok: %s" % yol)
    return dosyalar


def manifest_paket_anahtari(yol):
    """O9 (tur 5) — kaydin URETILDIGI R2 paket anahtari; yoksa None.

    Kayit, paketi toplayan tek yazar tarafindan paketin TA KENDISINDEN uretilir; o
    yazar hangi R2 anahtarina yukledigini de bilir. Anahtari kayda YAZMAK, "bu kayit
    HANGI paket icin gecerli" sorusunu MAKINEYE baglar. Tur 4/D8 olcumu: is akisi
    girdisi (`paket_anahtar`) SERBEST METINDI ve R2'de duran ESKI bir anahtar girilerek
    is tetiklenebiliyordu -> kayit taze gorunurken imaj bambaska bir paketten derlenirdi.
    (Bu, kaydin GECERLILIK ETIKETIDIR; kaydi UYDURMAZ. Kaydi hala yalniz gercek paket
    uretir.)"""
    with open(yol, "r", encoding="utf-8") as f:
        veri = json.load(f)
    anahtar = veri.get("paket_anahtar")
    return anahtar if isinstance(anahtar, str) and anahtar else None


def paket_anahtar_kusurlari(manifest_yol, ci_anahtar):
    """KAPI GOVDESI (O9) — kayit HANGI R2 paketi icin uretildi, CI HANGISINI cekti.

    `ci_anahtar` bos ise (yerel kosum) olcum YAPILMAZ — bos liste doner. CI'da is akisi
    girdisi ZORUNLU oldugu icin orada daima dolu gelir; bayragin dusurulmesi ise
    tools/is-akisi-kapisi.py B_IDDIALAR['parmakizi-dizin'] jetonuyla KIRMIZI'ya bagli."""
    if not ci_anahtar:
        return []
    kayit_anahtar = manifest_paket_anahtari(manifest_yol)
    if not kayit_anahtar:
        return [
            "parmakizi kaydinda `paket_anahtar` YOK (%s) -> bu kaydin HANGI R2 paketi "
            "icin uretildigi bilinmiyor; is akisi '%s' anahtarini cekti (fail-closed). "
            "COZUM (paketi toplayan makinede, TEK SATIR): python3 "
            "tools/onizleme-paket-yukle.py  -> paketi yukler, kaydi anahtarla birlikte "
            "tazeler; ARDINDAN kaydi COMMIT + PUSH edip is akisini o ciktidaki 'R2 "
            "ANAHTARI' degeriyle tetikleyin." % (manifest_yol, ci_anahtar)]
    if kayit_anahtar != ci_anahtar:
        return [
            "KAYIT/PAKET ANAHTARI AYRISMASI: repo HEAD kaydi '%s' paketi icin uretilmis, "
            "is akisi ise '%s' anahtarini cekti -> kayit bu pakete AIT DEGIL "
            "(fail-closed; tur 4/D8-2: girdi serbest metin oldugu icin R2'de duran ESKI "
            "bir anahtarla is tetiklenebiliyordu). COZUM (TEK SATIR): is akisini "
            "paket_anahtar='%s' ile tetikleyin; yeni paket yayinlanacaksa once python3 "
            "tools/onizleme-paket-yukle.py kosun ve tazelenen kaydi AYNI commit'te "
            "push edin." % (kayit_anahtar, ci_anahtar, kayit_anahtar)]
    return []


def manifest_yaz(yol, parmakizlari, not_metni="", paket_anahtar=""):
    veri = {
        "surum": MANIFEST_SURUM,
        "algoritma": ALGORITMA,
        "paket_anahtar": paket_anahtar or "",
        "aciklama": ("Onizleme derleyici imajina gomulen paket anlik goruntusunun icerik "
                     "ozetleri — paket dizinindeki TUM dosyalar (*.scad + eslem-ozel.json "
                     "+ pakete giren her sey). TEK YAZAR: tools/onizleme-paket-yukle.py. "
                     "Elle duzenlenmez; paket yeniden yuklenince bu dosya da tazelenir ve "
                     "AYNI commit'te gider. Icerik/kaynak kod BURAYA YAZILMAZ — yalniz "
                     "dosya adi + ozet."),
        "not": not_metni,
        "dosyalar": dict(sorted(parmakizlari.items())),
    }
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    return veri


def parmakizi_farklari(kayit, taze):
    """KAPI GOVDESI (B) — kayit (repo HEAD) ile taze (imaj/paket) ozetlerini karsilastirir.

    Kusur listesi dondurur; BOS liste = YESIL. Her kusur DRIFT EDEN DOSYAYI ADIYLA
    soyler. Ozetlerin yalniz ilk 12 hanesi basilir (tam ozet zaten kayitta)."""
    kusurlar = []
    kayit_adlar = set(kayit)
    taze_adlar = set(taze)
    for ad in sorted(kayit_adlar - taze_adlar):
        kusurlar.append(
            "DRIFT/EKSIK: '%s' repo HEAD kaydinda VAR ama imaj/paket anlik goruntusunde "
            "YOK -> imaj bu dosyayi tasimiyor (uretec ise aile 404 'aile-yok' verir; "
            "eslem-ozel.json ise servis hic ayaga kalkmaz)." % ad)
    for ad in sorted(taze_adlar - kayit_adlar):
        kusurlar.append(
            "DRIFT/FAZLA: '%s' imaj/paket anlik goruntusunde VAR ama repo HEAD kaydinda "
            "YOK -> kayit bayat (paket yuklenirken parmakizi tazelenmemis)." % ad)
    for ad in sorted(kayit_adlar & taze_adlar):
        if kayit[ad] != taze[ad]:
            kusurlar.append(
                "DRIFT/ICERIK: '%s' icerigi kayittan FARKLI (kayit %s… / gercek %s…) -> "
                "imaj eski (ya da elle degistirilmis) bir surumu tasiyor."
                % (ad, kayit[ad][:12], taze[ad][:12]))
    return kusurlar


def alt_sinir_kusurlari(kayit, taze, kaynak_adi):
    """KAPI GOVDESI (B-alt) — BOS KUME FAIL-OPEN NOBETI (O3 onarimi, curutme turu Ç3/E1).

    OLCULDU: bos kayit ({}) + bos paket (0 dosya) kombinasyonu YESIL yaniyordu —
    `parmakizi_farklari` iki bos kumeyi "fark yok" sayar ve kapi "hash duzeyinde AYNI
    (0 .scad)" diye onaylardi. Bos-nobeti YALNIZ YAZICI taraftaydi (`parmakizi-yaz`,
    `parmakizi_tazele`); DOGRULAYICIDA yoktu. Kayit dosyasi bir kez `{}`'e duserse
    (kotu merge/cakisma cozumu — bu dal 135 commit geride tam da o riskteydi)
    dogrulayici sessizce yesil yanardi.

    OLCU SABIT SAYI DEGIL (mimar sarti): "kayittaki giris sayisi ile paketteki dosya
    sayisi ESIT ve IKISI DE > 0". Esitlik zaten EKSIK/FAZLA farklariyla olculur; burada
    ALT SINIR (>0) fail-closed baglanir. Boylece paket buyudukce esik bayatlamaz."""
    kusurlar = []
    if not kayit:
        kusurlar.append(
            "BOS KAYIT: repo HEAD parmakizi kaydinda 0 giris var -> karsilastirilacak "
            "hicbir sey yok, 'fark yok' hukmu ANLAMSIZ (fail-closed). Bu genellikle "
            "kotu bir merge/cakisma cozumunun kaydi bosaltmasidir. COZUM: kaydi "
            "paketten tazeleyin (python3 tools/onizleme-paket-yukle.py).")
    if not taze:
        kusurlar.append(
            "BOS PAKET: %s tarafinda 0 dosya var -> imaj/paket bos ya da yanlis yer "
            "olculuyor (fail-closed). Bos bir paketle derlenen imaj HICBIR aileyi "
            "servis edemez." % kaynak_adi)
    return kusurlar


# ------------------------------------------------------------------ HTTP (ortak)

def _get_json(url, zaman_asimi=30):
    with urllib.request.urlopen(url, timeout=zaman_asimi) as r:
        return json.loads(r.read().decode("utf-8"))


def servis_parmakizlari(taban_url, zaman_asimi=30):
    """KOSAN SERVISTEN (yani imajin ta kendisinden) ozetleri al: GET /parmakizi.

    'dosyalar' alani ZORUNLU (kayit surum 2 ile ayni eksen): yalniz 'scad' donen bir
    imaj BU KAPIDAN ESKIDIR ve paketin yarisini gizler -> fail-closed istisna."""
    veri = _get_json(taban_url.rstrip("/") + "/parmakizi", zaman_asimi)
    dosyalar = veri.get("dosyalar")
    if not isinstance(dosyalar, dict):
        raise ValueError(
            "/parmakizi yaniti 'dosyalar' sozlugu icermiyor -> imaj bu kapidan ESKI "
            "(yalniz *.scad bildiren surum; eslem-ozel.json olculemez). Imaji yeniden "
            "derleyin.")
    return dosyalar


def servis_aileleri(taban_url, zaman_asimi=30):
    veri = _get_json(taban_url.rstrip("/") + "/saglik", zaman_asimi)
    return sorted(veri.get("aileler") or []), bool(veri.get("mock"))


def servis_kapsami(taban_url, zaman_asimi=30):
    """GET /kapsam -> {aile: {"scad":..., "secici":..., "varyantlar": {...}}}.
    Uc yoksa (imaj bu kapidan ESKI) istisna atar -> duman KIRMIZI (fail-closed)."""
    veri = _get_json(taban_url.rstrip("/") + "/kapsam", zaman_asimi)
    aileler = veri.get("aileler")
    if not isinstance(aileler, dict):
        raise ValueError("/kapsam yaniti 'aileler' sozlugu icermiyor")
    return aileler


def servis_derle(taban_url, aile, parametreler, zaman_asimi=120):
    """POST /derle -> (http_kod, govde_uzunlugu, hata_metni)."""
    govde = json.dumps({"aile": aile, "parametreler": parametreler},
                       ensure_ascii=False).encode("utf-8")
    istek = urllib.request.Request(
        taban_url.rstrip("/") + "/derle", data=govde,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
            return r.status, len(r.read()), ""
    except urllib.error.HTTPError as e:
        ham = e.read().decode("utf-8", "replace")[:200]
        return e.code, 0, ham
    except urllib.error.URLError as e:
        return 0, 0, str(e.reason)


# ------------------------------------------------------------ aile plani (A)

def _dengeli_blok(kaynak, bas):
    """kaynak[bas] '{' ya da '[' iken DENGELI kapanisa kadar olan dilimi dondurur.
    Dize icindeki parantezler sayilmaz. (build.py'nin non-greedy `\\{.*?\\}` regex'i
    IC ICE objelerde ILK '}'de kesiyor — ONIZLEME_KISITLAR tam da ic ice.)"""
    acilis = kaynak[bas]
    kapanis = {"{": "}", "[": "]"}[acilis]
    derinlik = 0
    i = bas
    tirnak = None
    kacis = False
    while i < len(kaynak):
        ch = kaynak[i]
        if tirnak:
            if kacis:
                kacis = False
            elif ch == "\\":
                kacis = True
            elif ch == tirnak:
                tirnak = None
        elif ch in "\"'":
            tirnak = ch
        elif ch == acilis:
            derinlik += 1
        elif ch == kapanis:
            derinlik -= 1
            if derinlik == 0:
                return kaynak[bas:i + 1]
        i += 1
    raise ValueError("dengeli kapanis bulunamadi (konum %d)" % bas)


def _js_sabiti(kaynak, ad):
    """secenekler.js'ten `var <ad> = [...]/{...};` sabitini okur (JS -> JSON).

    ⚠️ OLCULEN TUZAK (bu kapinin ilk kosumunda yakalandi): secenekler.js'te
    ONIZLEME_KISITLAR `{ tip: ["duz"] }` biciminde — ANAHTARLAR TIRNAKSIZ ve obje IC
    ICE. build.py'nin `(\\{.*?\\}|\\[.*?\\])` + json.loads yardimcisi bu sabitte
    ayristirma HATASI verir. Ilk surumde bu hata sessizce yutuluyordu (`except:
    kisitlar = {}`) -> kapi 6 aileyi SAHTE-KIRMIZI yakti (kisitli secim degerleri
    denendi, sunucu 400 dondu). Bu yuzden: (a) dengeli-parantez cikarma, (b) tirnaksiz
    anahtarlarin tirnaklanmasi, (c) FAIL-CLOSED — ayristirma hatasi YUTULMAZ.

    Bilincli sinir: bu bir JS ayristiricisi DEGILDIR (bkz. [[mimar-kapi-parser-taklidi]]).
    Yalniz "JSON + tirnaksiz anahtar + sondaki virgul" alt kumesini cozer; daha egzotik
    bir yazim gelirse istisna atar (sessiz bos deger DONMEZ)."""
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*", kaynak)
    if not m:
        raise ValueError("secenekler.js'te %s bulunamadi (tek kaynak bozulmus)" % ad)
    bas = m.end()
    if bas >= len(kaynak) or kaynak[bas] not in "{[":
        raise ValueError("%s degeri '{' ya da '[' ile baslamiyor" % ad)
    ham = _dengeli_blok(kaynak, bas)
    # Tirnaksiz JS anahtarlarini tirnakla: `{ tip: [...]` -> `{ "tip": [...]`
    duz = re.sub(r"([{,]\s*)([A-Za-z_$][\w$]*)(\s*):", r'\1"\2"\3:', ham)
    duz = re.sub(r",(\s*[}\]])", r"\1", duz)          # sondaki virgul
    try:
        return json.loads(duz)
    except ValueError as e:
        raise ValueError("%s JSON'a cevrilemedi (%s) — secenekler.js yazimi bu kapinin "
                         "dar alt kumesinin disina cikti" % (ad, e))


def semalari_tara(sema_dizin):
    """DIZIN TARAMASI: jenerator/urunler/*.json -> {aile_id: sema}.
    Sabit aile listesi YOK; yeni bir uretec ailesi dosyasi eklenince otomatik girer."""
    semalar = {}
    for ad in sorted(os.listdir(sema_dizin)):
        if not ad.endswith(".json"):
            continue
        yol = os.path.join(sema_dizin, ad)
        if not os.path.isfile(yol):
            continue
        with open(yol, "r", encoding="utf-8") as f:
            sema = json.load(f)
        aile = sema.get("id") or ad[:-5]
        semalar[aile] = sema
    return semalar


def varsayilan_parametreler(sema, kisit):
    """Sema varsayilanlarindan duman istegi. ONIZLEME_KISITLAR'da yasakli bir secim
    varsayilani, izinli ilk degere cekilir (musteri sema kapisiyla ayni evren;
    onizleme/test/eslem-olcum.py varsayilan_set() ile ayni kural)."""
    p = {}
    for tanim in sema.get("parametreler") or []:
        p[tanim["ad"]] = tanim.get("varsayilan")
    for ad, izinli in (kisit or {}).items():
        if ad in p and izinli and p[ad] not in izinli:
            p[ad] = izinli[0]
    return p


def _izinli_degerler(tanim, kisit):
    degerler = [s["deger"] if isinstance(s, dict) else s
                for s in (tanim.get("secenekler") or [])]
    izinli = (kisit or {}).get(tanim["ad"])
    if izinli:
        degerler = [d for d in degerler if d in izinli]
    return degerler


def istek_setleri(sema, kisit, kapsam=None, secim_tara=0):
    """Bir aile icin duman istek setleri: [(etiket, parametreler, beklenen_scad), ...].

    VARYANT KORUMASI (regresyon onleme, bilincli): eski elle-yazilmis duman adimi yay
    ailesini IKI kez cagiriyordu (tip=spiral / tip=dalga) cunku o aile CIFT URETECLIDIR —
    secici degeri BASKA bir .scad'i surer. Aile listesi dizin taramasina cevrilirken bu
    koruma DUSSEYDI paketteki ikinci .scad sessizce denenmemis kalirdi.
    Kor tarama YERINE hedefli: servisin /kapsam ucu hangi secici degerinin hangi .scad'i
    surdugunu soyler -> varsayilan set + AYRI BIR .scad'e giden her secici degeri.
    Boylece 23 aile ~25 istekle kapanir (kor `secim_tara=1` taramasi 101 istek olcmustu).

    🔴 O8 (tur 5) — KISIT ARTIK VARYANT SUPURMESINI DARALTMAZ: asagidaki varyant
    dongusu ONIZLEME_KISITLAR'a BAKMAZ. Gerekce olculmus bir kavram hatasidir:
    ONIZLEME_KISITLAR MUSTERI EVRENINI daraltir (siteden hangi secenek secilebilir),
    IMAJ KABILIYETINI degil (imaj o ureteci derleyebiliyor mu). Duman testi ikincisini
    olcer. Eski hal (kisita uy + atlanani "kisitla kapali" say) iki zarar uretiyordu:
      (a) SAHTE-KIRMIZI (Ç8/FP5): atlanan .scad "olu uretec" diye yakiliyordu;
      (b) 🔴 MASKELEME (tur 4/D4): eslem-ozel.json + secenekler.js'te birer satirla
          GERCEK bir olu uretec kapsam disina cikarilip kapi YESIL gecirilebiliyordu,
          ve kisit gevsetildigi gun hic derlenmemis uretec musteriye aciliyordu.
    Ikisinin de kaynagi ayni satirdi (`if izinli and deger not in izinli: continue`).
    Kaldirilinca (a) kendiliginden duzeldi — dosya artik atlanmiyor, DERLENIYOR — ve
    (b)'nin kanali TAMAMEN yok oldu: kisit ne sikilastirilsin ne gevsetilsin, denenen
    .scad kumesi DEGISMEZ. Invaryant `kisit_kapsam_kusurlari()` ile makineye baglidir.
    MALIYET: kisitli bir secici degeri AYRI bir .scad suruyorsa istek sayisi +1 olur
    (bugunku canli kisit listesinde — cetvel/damga-kase/petek — cift-uretecli aile YOK,
    yani bugun +0). Yararli maliyettir: kisit kalkinca derlenmedigi CANLIDA anlasilan
    uretec, artik CI'da anlasiliyor.
    Taban (varsayilan) istek kisiti UYGULAMAYA DEVAM EDER: o istek "musterinin gordugu
    varsayilan" senaryosudur ve kisitli bir varsayilani zorlamak anlamsiz olurdu.

    secim_tara>0: ek olarak ilk N `secim` parametresinin izinli TUM degerleri (derin
    supurme; CI varsayilani 0)."""
    taban = varsayilan_parametreler(sema, kisit)
    kapsam = kapsam or {}
    varsayilan_scad = kapsam.get("scad")
    varyantlar = kapsam.get("varyantlar") or {}
    secici = kapsam.get("secici")
    if secici and taban.get(secici) in varyantlar:
        varsayilan_scad = varyantlar[taban[secici]]
    setler = [("varsayilan", taban, varsayilan_scad)]
    goruldu = {varsayilan_scad}

    if secici:
        # AYRI .scad'e giden secici degerleri (yay: dalga; vida: somun/pul ...).
        # 🔴 KISIT SUZGECI YOK (O8) — bkz. docstring. Bu dongude ONIZLEME_KISITLAR'a
        # BAKILMAZ; imajin tasidigi HER uretec, musteriye kapali olsa da derletilir.
        for deger, scad in sorted(varyantlar.items()):
            if scad in goruldu:
                continue
            yeni = dict(taban)
            yeni[secici] = deger
            setler.append(("%s=%s" % (secici, deger), yeni, scad))
            goruldu.add(scad)

    if secim_tara > 0:
        secimler = [p for p in (sema.get("parametreler") or [])
                    if p.get("tip") == "secim"]
        var_etiketler = set(e for e, _, _ in setler)
        for tanim in secimler[:secim_tara]:
            for d in _izinli_degerler(tanim, kisit):
                if d == taban.get(tanim["ad"]):
                    continue
                etiket = "%s=%s" % (tanim["ad"], d)
                if etiket in var_etiketler:
                    continue
                yeni = dict(taban)
                yeni[tanim["ad"]] = d
                scad = varyantlar.get(d, varsayilan_scad) if tanim["ad"] == secici \
                    else varsayilan_scad
                setler.append((etiket, yeni, scad))
    return setler


def kisit_kapsam_kusurlari(semalar, kapsam, kisitlar, hedefler):
    """O8 NOBETCISI (tur 5) — DUMAN KAPSAMI ONIZLEME_KISITLAR'DAN BAGIMSIZ OLMALI.

    Bu, O5'in actigi maskeleme kanalinin (tur 4/D4) yeniden acilmasini engelleyen
    INVARYANTTIR. Olctugu sey tek cumle: "ayni fikstur, kisitli ve KISITSIZ planlandiginda
    AYNI .scad kumesini derletir mi?" Hayirsa, ONIZLEME_KISITLAR imajin kabiliyet
    olcumunu daraltiyor demektir ve tam o daralma icine gercek bir olu uretec
    saklanabilir (iki dosyada birer satir yeter).

    NEDEN BLOKLAYICI BIR INVARYANT: `istek_setleri` bugun kisit suzgeci UYGULAMIYOR
    (O8). Ama bu, bir gun birinin "kisitli varyanti neden derliyoruz" deyip o satiri
    geri koymasini engellemez — ve o degisiklik, kapiyi SESSIZCE eski (maskelenebilir)
    haline dondururdu. Invaryant o tek satiri KIRMIZI'ya bagliyor.

    AYRICA GEVSETME EKSENI: kisit listesi degistiginde (sikilasma ya da GEVSEME) bu
    olcum kapsamin degismedigini soyler; yani "kisit gevsetildi, hic derlenmemis bir
    uretec musteriye acildi" senaryosu YAPISAL OLARAK imkansizdir — kisitliyken de
    derleniyordu.

    Kisit yalniz TABAN (varsayilan) istegin parametrelerini kaydirabilir; bu kaydirma
    denenen .scad KUMESINI degistirmemelidir."""
    kusurlar = []
    for aile in sorted(hedefler):
        sema = semalar.get(aile)
        if sema is None:
            continue
        aile_kapsam = (kapsam or {}).get(aile)
        kisitli = set(s for _, _, s in istek_setleri(
            sema, (kisitlar or {}).get(aile), aile_kapsam) if s)
        kisitsiz = set(s for _, _, s in istek_setleri(sema, None, aile_kapsam) if s)
        eksik = kisitsiz - kisitli
        if eksik:
            kusurlar.append(
                "KISIT KAPSAMI DARALTTI: '%s' ailesinde ONIZLEME_KISITLAR yuzunden %s "
                "duman planinin DISINDA kaldi (kisitsiz planda VAR). Kisit MUSTERI "
                "EVRENINI daraltir, IMAJ KABILIYETINI degil -> bu daralma bir olu "
                "ureteci maskeleyebilir ve kisit gevsetildigi gun hic derlenmemis bir "
                "uretec musteriye acilir (tur 4/D4). Duzeltme: istek_setleri varyant "
                "dongusunde kisit suzgeci KULLANMAMALI."
                % (aile, ", ".join(sorted(eksik))))
    return kusurlar


def kapsam_beyani_kusurlari(semalar, kapsam, kisitlar):
    """O4 onarimi (curutme turu Ç4/L1) — SERVISIN /kapsam BEYANINI BAGIMSIZ KAYNAKLA OLC.

    OLCULEN DELIK: "N/N ayri .scad kapsandi" cumlesi bir OLCUM DEGIL, servisin kendi
    iki beyaninin (`/kapsam` + `/parmakizi`) CARPIMIYDI. Comert yalan soyleyen bir
    stub (`/kapsam` her paket .scad'ini varyant diye bildirir, `/derle` her istege
    stub 200 doner) UC istekle 3/3 YESIL gecti.

    BAGIMSIZ KAYNAK: `jenerator/urunler/*.json` sema dizini — REPO tarafinda, servisin
    erisemedigi/etkileyemedigi bir kaynak. Servis "su parametre secicidir ve su
    degerler ayri uretec surer" diyorsa, o parametrenin ve o degerlerin SEMADA
    GERCEKTEN var olmasi gerekir. Semayla ortusmeyen bir beyan uydurulmustur.

    DAR (bilincli): yalniz `secici` ve `varyantlar` ANAHTARLARI olculur — .scad
    ADLARI degil (onlar paket kaydiyla, duman_kusurlari icinde caprazlanir)."""
    kusurlar = []
    for aile, tanim in sorted((kapsam or {}).items()):
        sema = semalar.get(aile)
        if sema is None:
            continue  # semasi olmayan servis ailesi: ayri sinif, orada raporlanir
        secici = (tanim or {}).get("secici")
        varyantlar = (tanim or {}).get("varyantlar") or {}
        if not secici and not varyantlar:
            continue
        tanimlar = {t.get("ad"): t for t in (sema.get("parametreler") or [])}
        if secici and secici not in tanimlar:
            kusurlar.append(
                "KAPSAM BEYANI UYDURMA: '%s' ailesinde servis '%s' parametresini SECICI "
                "diye bildirdi ama jenerator/urunler semasinda boyle bir parametre YOK "
                "-> /kapsam beyani bagimsiz kaynakla ortusmuyor (kapsama sayisi bu "
                "beyandan uretildigi icin 'N/N kapsandi' cumlesi guvenilmez)."
                % (aile, secici))
            continue
        if not secici:
            kusurlar.append(
                "KAPSAM BEYANI UYDURMA: '%s' ailesinde servis SECICISIZ varyant bildirdi "
                "(%d varyant) -> hangi parametrenin hangi ureteci surdugu semadan "
                "dogrulanamaz." % (aile, len(varyantlar)))
            continue
        yasal = set()
        for s in (tanimlar[secici].get("secenekler") or []):
            yasal.add(s["deger"] if isinstance(s, dict) else s)
        # 🔴 BOS `yasal` FAIL-OPEN OLMAZ (bu kontrolun KENDI ilk surumunde olculdu):
        # varyant bildirilmisken secici parametrenin semada HIC secenegi yoksa, servis
        # SECIM OLMAYAN bir parametreyi (or. sayisal `boy`) secici diye bildirmis
        # demektir — comert yalan stub'i tam bu bosluktan geciyordu.
        if varyantlar and not yasal:
            kusurlar.append(
                "KAPSAM BEYANI UYDURMA: '%s' ailesinde servis '%s' parametresini secici "
                "diye bildirip %d varyant saydi, ama semada bu parametrenin SECENEKLERI "
                "YOK (secim parametresi degil) -> beyan bagimsiz kaynakla celisiyor."
                % (aile, secici, len(varyantlar)))
            continue
        for deger in sorted(varyantlar, key=str):
            if yasal and deger not in yasal:
                kusurlar.append(
                    "KAPSAM BEYANI UYDURMA: '%s' ailesinde servis '%s=%r' varyantini "
                    "bildirdi ama semada bu parametrenin secenekleri arasinda boyle bir "
                    "deger YOK (%s) -> beyan bagimsiz kaynakla celisiyor."
                    % (aile, secici, deger, ", ".join(sorted(map(str, yasal)))))
    return kusurlar


def duman_plani(sema_dizin=None, secenekler_js=None):
    """(acik_aileler, semalar, kisitlar) — hepsi DIZIN TARAMASI + tek kaynak dosyadan."""
    sema_dizin = sema_dizin or VARSAYILAN_SEMA_DIZIN
    secenekler_js = secenekler_js or VARSAYILAN_SECENEKLER
    with open(secenekler_js, "r", encoding="utf-8") as f:
        kaynak = f.read()
    acik = list(_js_sabiti(kaynak, "ONIZLEME_AILELER"))
    # FAIL-CLOSED: kisit okunamazsa BOS SOZLUKLE devam ETME — kisitli secim degerleri
    # denenir ve kapi sahte-kirmizi yanar (bu kapinin ilk kosumunda aynen olculdu).
    kisitlar = _js_sabiti(kaynak, "ONIZLEME_KISITLAR")
    return acik, semalari_tara(sema_dizin), kisitlar


def duman_kusurlari(taban_url, acik_aileler, semalar, kisitlar,
                    zaman_asimi=120, yaz=None, secim_tara=0, manifest=None):
    """KAPI GOVDESI (A) — dizin taramasindan uretilen aile listesini SERVISE derletir.

    Kusur listesi dondurur; BOS liste = YESIL. Kusur siniflari:
      1. musteriye ACIK bir aile /saglik'ta YOK          (27 Tem toka sinifi)
      2. musteriye ACIK bir ailenin SEMASI dizinde YOK   (istek kurulamaz)
      3. derleme 200 + BOS OLMAYAN govde dondurmedi      (imaj o ureteci derleyemiyor)
      4. /kapsam okunamadi                               (imaj bu kapidan ESKI)
      5. pakette olup HIC denenmemis .scad kaldi         (aile hic baglanmamis/olu)
      6. BOS KUME: acik aile / sema / paket bos           (O3, fail-closed)
      7. KAYIT vs SERVIS BEYANI ayrisiyor                 (O4, KAYIT kazanir)
      8. /kapsam beyani sema ile ortusmuyor               (O4, bagimsiz capraz)
      9. eslem PAKETTE OLMAYAN bir .scad'i surdu          (O4, ters yon)
     10. ONIZLEME_KISITLAR duman kapsamini DARALTTI      (O8, maskeleme kanali)

    `manifest`: repo HEAD parmakizi kaydinin yolu. Verilirse servisin `/parmakizi`
    beyani KAYITLA caprazlanir; ayrisirsa KAYIT KAZANIR (O4)."""
    yaz = yaz or (lambda s: None)
    kusurlar = []
    try:
        servis, mock = servis_aileleri(taban_url, zaman_asimi)
    except Exception as e:                                   # noqa: BLE001
        return ["/saglik okunamadi (%s): servis ayakta mi?" % e]
    try:
        kapsam = servis_kapsami(taban_url, zaman_asimi)
    except Exception as e:                                   # noqa: BLE001
        return ["/kapsam okunamadi (%s): imaj bu kapidan ESKI (server.py'de /kapsam ucu "
                "yok) -> imaji yeniden derleyin." % e]
    try:
        servis_dosyalar = servis_parmakizlari(taban_url, zaman_asimi)
    except Exception as e:                                   # noqa: BLE001
        return ["/parmakizi okunamadi (%s): imaj bu kapidan ESKI -> imaji yeniden "
                "derleyin." % e]
    paket_scad = set(scad_alt_kumesi(servis_dosyalar))
    yaz("  servis /saglik: %d aile (mock=%s)" % (len(servis), mock))
    yaz("  repo taramasi: %d sema, musteriye acik %d aile"
        % (len(semalar), len(acik_aileler)))

    # --- (6) BOS KUME NOBETI — O3. Bos girdi "kusur yok" DEMEK DEGILDIR.
    # OLCULDU: ONIZLEME_AILELER=[] yapilinca 27 Tem sinifinin BIRINCIL kontrolu
    # (SERVIS-DISI AILE) tamamen oluyordu; geriye yalniz DENENMEMIS URETEC yedegi
    # kaliyordu ve o da dusen ailenin .scad'i baska bir aileyle PAYLASILIYORSA susar.
    if not acik_aileler:
        kusurlar.append(
            "BOS ACIK AILE LISTESI: secenekler.js ONIZLEME_AILELER bos -> 'musteriye "
            "acik her aile serviste var mi' kontrolu (27 Tem toka sinifinin BIRINCIL "
            "nobeti) hicbir sey olcmez (fail-closed). Liste gercekten bosaltildiysa "
            "onizleme ozelligi kapatilmis demektir; kapiyi da o zaman kaldirin.")
    if not semalar:
        kusurlar.append(
            "BOS SEMA DIZINI: jenerator/urunler/ taramasi 0 sema dondurdu -> hicbir "
            "duman istegi kurulamaz, 'TUM aileler derlendi' hukmu ANLAMSIZ "
            "(fail-closed).")
    if not paket_scad:
        kusurlar.append(
            "BOS PAKET: imajin /parmakizi beyaninda 0 adet *.scad var -> imaj hicbir "
            "ureteci tasimiyor; olu-uretec ve kapsama olcumlerinin PAYDASI bos "
            "(fail-closed).")

    # --- (7) KAYIT vs SERVIS BEYANI — O4. Servis "hepsini tasiyorum" derken repo HEAD
    # kaydi aksini soyluyorsa KAYIT KAZANIR: kayit servisin erisemedigi/etkileyemedigi
    # bagimsiz bir kaynaktir, `/parmakizi` ise servisin KENDI beyanidir.
    if manifest and os.path.exists(manifest):
        try:
            kayit = manifest_oku(manifest)
        except Exception as e:                               # noqa: BLE001
            kusurlar.append("KAYIT OKUNAMADI (%s): %s -> kapsama iddiasi bagimsiz "
                            "kaynakla caprazlanamadi (fail-closed)." % (manifest, e))
        else:
            for k in parmakizi_farklari(kayit, servis_dosyalar):
                kusurlar.append(
                    "KAYIT/SERVIS AYRISMASI (kayit kazanir): " + k)
    else:
        kusurlar.append(
            "KAYIT YOK (%s): servisin /parmakizi + /kapsam beyanlari BAGIMSIZ bir "
            "kaynakla caprazlanamiyor -> 'N/N .scad kapsandi' cumlesi bir OLCUM degil "
            "servisin kendi beyani olur (fail-closed, O4)." % manifest)

    # --- (8) /kapsam BEYANI vs REPO SEMASI — O4 bagimsiz capraz.
    kusurlar.extend(kapsam_beyani_kusurlari(semalar, kapsam, kisitlar))

    servis_kumesi = set(servis)
    for aile in sorted(acik_aileler):
        if aile not in servis_kumesi:
            kusurlar.append(
                "SERVIS-DISI AILE: '%s' secenekler.js ONIZLEME_AILELER'de (musteriye ACIK) "
                "ama imajin /saglik listesinde YOK -> canlida 404 'aile-yok' + musteride "
                "\"Onizleme olusturulamadi\" (27 Tem toka kanamasinin sinifi)." % aile)
        if aile not in semalar:
            kusurlar.append(
                "SEMASIZ AILE: '%s' ONIZLEME_AILELER'de ama jenerator/urunler/ taramasinda "
                "semasi YOK -> duman istegi kurulamaz." % aile)

    # Denenecek kume: musteriye acik ∪ serviste olan — ikisinin de semasi olmali.
    hedefler = sorted((set(acik_aileler) | servis_kumesi) & set(semalar) & servis_kumesi)
    semasiz_servis = sorted(servis_kumesi - set(semalar))
    if semasiz_servis:
        yaz("  UYARI (bloklamaz): serviste olup repoda semasi olmayan aile: %s"
            % ", ".join(semasiz_servis))
    yaz("  derletilecek aile (%d): %s" % (len(hedefler), ", ".join(hedefler)))

    # --- (10) KISIT-BAGIMSIZLIK INVARYANTI — O8. Duman kapsami ONIZLEME_KISITLAR'dan
    # ETKILENMEMELI; etkilenirse o daralmanin icine olu uretec saklanabilir (tur 4/D4).
    kusurlar.extend(kisit_kapsam_kusurlari(semalar, kapsam, kisitlar, hedefler))

    toplam_set = 0
    denenen_scad = set()
    for aile in hedefler:
        aile_kisit = kisitlar.get(aile)
        aile_kapsam = kapsam.get(aile)
        for etiket, parametreler, scad in istek_setleri(
                semalar[aile], aile_kisit, aile_kapsam, secim_tara):
            toplam_set += 1
            kod, boyut, hata = servis_derle(taban_url, aile, parametreler, zaman_asimi)
            if kod == 200 and boyut > 0:
                if scad:
                    denenen_scad.add(scad)
                yaz("  [OK ] %-38s %-22s %8d bayt" % (aile, etiket, boyut))
                continue
            kusurlar.append(
                "DERLENMEDI: '%s' [%s] -> HTTP %s, %d bayt%s"
                % (aile, etiket, kod, boyut, (" — " + hata) if hata else ""))
    yaz("  toplam derleme istegi: %d · basariyla derlenen ayri .scad: %d/%d"
        % (toplam_set, len(denenen_scad & paket_scad), len(paket_scad)))
    # O8: "kisitla kapali" SINIFI YOK. Bunun yerine kisitin kapsama ETKISI raporlanir —
    # beklenen deger DAIMA 0'dir (invaryant yukarida bloklayici olarak olculdu).
    musteriye_kapali = []
    for aile in sorted(hedefler):
        aile_kisit = (kisitlar or {}).get(aile) or {}
        aile_kapsam = kapsam.get(aile) or {}
        secici = aile_kapsam.get("secici")
        izinli = aile_kisit.get(secici) if secici else None
        if not izinli:
            continue
        for deger, scad in sorted((aile_kapsam.get("varyantlar") or {}).items()):
            if deger not in izinli and scad:
                musteriye_kapali.append("%s[%s=%s]->%s" % (aile, secici, deger, scad))
    if musteriye_kapali:
        yaz("  musteriye kapali varyant: %d (%s) — HEPSI YINE DE DERLETILDI "
            "(kisit musteri evrenini daraltir, imaj kabiliyetini DEGIL; O8)"
            % (len(musteriye_kapali), ", ".join(musteriye_kapali)))
    else:
        yaz("  musteriye kapali varyant: 0")

    # (9) TERS YON — O4. Eslem, PAKETTE OLMAYAN bir .scad'i surdugunu soyluyorsa
    # kapsama kredisi HAYALI bir dosyaya yaziliyor demektir. Curutme turunda (Ç7/M1)
    # olculdu: yalniz `paket - denenen` yonu kontrol ediliyordu, bu yon HIC.
    for ad in sorted(denenen_scad - paket_scad):
        kusurlar.append(
            "ESLEM HAYALI URETEC SURUYOR: '%s' /kapsam beyaninda varyant uretecidir ama "
            "imajin /parmakizi listesinde (paketinde) YOK -> kapsama kredisi var olmayan "
            "bir dosyaya yazildi; gercek imajda bu istek 500 'scad-eksik' verirdi." % ad)

    # (5) Paketteki her .scad EN AZ BIR KEZ derlenmis olmali. Denenmemis bir uretec,
    # sabit-liste devrindeki tam sessizligin kalintisidir: dosya imaja giriyor ama
    # hicbir duman istegi ona ulasmiyor -> bozuk oldugu CANLIDA anlasilir.
    # 🔴 O8: BURADA ISTISNA YOK. Eski "kisitla kapali -> atla" istisnasi (O5) tur 4/D4'te
    # maskeleme kanali olarak olculdu ve KALDIRILDI; kisitli varyantlar artik zaten
    # derletiliyor, dolayisiyla mesru bir "atla" sebebi de kalmadi.
    for ad in sorted(paket_scad - denenen_scad):
        kusurlar.append(
            "DENENMEMIS URETEC: '%s' imajin paketinde VAR ama hicbir duman istegi onu "
            "derletmedi -> ya bagli oldugu aile ONIZLEME_AILELER/servis disinda, ya da "
            "eslem onu hic surmuyor (olu dosya). Ikisi de sessiz kalmamali." % ad)
    return kusurlar


# ------------------------------------------------------------------------ main

def _kapat(kusurlar, yesil_mesaj):
    if kusurlar:
        for k in kusurlar:
            print("KIRMIZI: " + k)
        print("SONUC: KIRMIZI (%d kusur)" % len(kusurlar))
        return 1
    print("YESIL: " + yesil_mesaj)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    alt = ap.add_subparsers(dest="komut", required=True)

    a = alt.add_parser("parmakizi-yaz", help="paket dizininden repo HEAD kaydini tazele")
    a.add_argument("--dizin", required=True)
    a.add_argument("--manifest", default=VARSAYILAN_MANIFEST)
    a.add_argument("--not", dest="not_metni", default="")
    a.add_argument("--paket-anahtar", dest="paket_anahtar", default="",
                   help="kaydin uretildigi R2 nesne anahtari (O9): CI tetiklendigi "
                        "anahtarla caprazlanir")

    b = alt.add_parser("parmakizi-dogrula", help="kayit vs imaj/paket — drift varsa exit 1")
    b.add_argument("--dizin")
    b.add_argument("--url")
    b.add_argument("--manifest", default=VARSAYILAN_MANIFEST)
    b.add_argument("--paket-anahtar", dest="paket_anahtar", default="",
                   help="CI'nin cektigi R2 paket anahtari (O9). Verilirse kaydin "
                        "`paket_anahtar` alaniyla CAPRAZLANIR; uyusmazsa/eksikse "
                        "FAIL-CLOSED")

    c = alt.add_parser("duman", help="dizin taramasiyla aile listesini servise derlet")
    c.add_argument("--url", required=True)
    c.add_argument("--sema-dizin", default=VARSAYILAN_SEMA_DIZIN)
    c.add_argument("--secenekler", default=VARSAYILAN_SECENEKLER)
    c.add_argument("--manifest", default=VARSAYILAN_MANIFEST,
                   help="repo HEAD parmakizi kaydi — servisin /parmakizi beyanini "
                        "BAGIMSIZ kaynakla caprazlar (O4); ayrisirsa KAYIT kazanir")
    c.add_argument("--zaman-asimi", type=float, default=120)
    c.add_argument("--secim-tara", type=int, default=0,
                   help="DERIN SUPURME: her ailede ilk N secim parametresinin TUM izinli "
                        "degerlerini de derlet (0 = varsayilan; ayri .scad'e giden "
                        "varyantlar /kapsam uzerinden ZATEN hedeflenir)")

    args = ap.parse_args(argv)

    if args.komut == "parmakizi-yaz":
        yapi = paket_yapi_kusurlari(args.dizin)
        if yapi:
            return _kapat(yapi, "")
        pk = paket_parmakizlari(args.dizin)
        if not pk or not scad_alt_kumesi(pk):
            print("KIRMIZI: %s altinda dosya/uretec yok (%d dosya, %d .scad) — bos kayit "
                  "YAZILMAZ (fail-closed)." % (args.dizin, len(pk), len(scad_alt_kumesi(pk))))
            return 1
        manifest_yaz(args.manifest, pk, args.not_metni, args.paket_anahtar)
        print("parmakizi kaydi yazildi: %s (%d dosya, %d .scad)"
              % (args.manifest, len(pk), len(scad_alt_kumesi(pk))))
        return 0

    if args.komut == "parmakizi-dogrula":
        if bool(args.dizin) == bool(args.url):
            print("KIRMIZI: --dizin ya da --url'den TAM BIRI verilmeli.")
            return 1
        if not os.path.exists(args.manifest):
            print("KIRMIZI: parmakizi kaydi YOK: %s" % args.manifest)
            print("KIRMIZI: FAIL-CLOSED — kayit olmadan imajin bayat olup olmadigi "
                  "OLCULEMEZ. COZUM (TEK SATIR, paketi toplayan makinede): "
                  "python3 tools/onizleme-paket-yukle.py  -> paketi yukler VE bu kaydi "
                  "paketin ta kendisinden uretir; ARDINDAN kaydi COMMIT + PUSH edip is "
                  "akisini ciktidaki 'R2 ANAHTARI' degeriyle tetikleyin (is akisi "
                  "yukleyiciyi CAGIRMAZ, repo HEAD'ini checkout eder).")
            return 1
        try:
            kayit = manifest_oku(args.manifest)
        except Exception as e:                               # noqa: BLE001
            print("KIRMIZI: parmakizi kaydi okunamadi (%s): %s" % (args.manifest, e))
            return 1
        # O9 — KAYIT <-> R2 PAKET ANAHTARI CAPRAZI (tur 4/D8). CI hangi anahtari
        # cektiyse kayit da O anahtar icin uretilmis olmali. FAIL-CLOSED: alan yoksa
        # kayit bu kapidan ESKIdir (anahtarsiz kayit, "hangi paket" sorusunu yanitlamaz).
        anahtar_kusurlari = paket_anahtar_kusurlari(args.manifest, args.paket_anahtar)
        if anahtar_kusurlari:
            return _kapat(anahtar_kusurlari, "")
        if args.paket_anahtar:
            print("kayit/paket anahtari: %s (eslesti)" % args.paket_anahtar)
        try:
            if args.dizin:
                yapi = paket_yapi_kusurlari(args.dizin)
                if yapi:
                    return _kapat(yapi, "")
                taze = paket_parmakizlari(args.dizin)
                kaynak = "paket dizini %s" % args.dizin
            else:
                taze = servis_parmakizlari(args.url)
                kaynak = "kosan imaj %s/parmakizi" % args.url.rstrip("/")
        except Exception as e:                               # noqa: BLE001
            print("KIRMIZI: taze parmakizi alinamadi: %s" % e)
            return 1
        print("kayit: %d dosya (%d .scad) · gercek: %s -> %d dosya (%d .scad)"
              % (len(kayit), len(scad_alt_kumesi(kayit)), kaynak,
                 len(taze), len(scad_alt_kumesi(taze))))
        # ALT SINIR (O3) fail-closed: bos kume "fark yok" SAYILMAZ.
        kusurlar = alt_sinir_kusurlari(kayit, taze, kaynak)
        kusurlar.extend(parmakizi_farklari(kayit, taze))
        return _kapat(kusurlar,
                      "imaj anlik goruntusu repo HEAD kaydiyla hash duzeyinde AYNI "
                      "(%d dosya, %d .scad)."
                      % (len(kayit), len(scad_alt_kumesi(kayit))))

    # duman
    try:
        acik, semalar, kisitlar = duman_plani(args.sema_dizin, args.secenekler)
    except Exception as e:                                   # noqa: BLE001
        print("KIRMIZI: duman plani kurulamadi: %s" % e)
        return 1
    kusurlar = duman_kusurlari(args.url, acik, semalar, kisitlar,
                               args.zaman_asimi, yaz=print,
                               secim_tara=args.secim_tara, manifest=args.manifest)
    return _kapat(kusurlar,
                  "dizin taramasindan uretilen TUM aileler bu imajda derlendi "
                  "(musteriye acik %d aile)." % len(acik))


if __name__ == "__main__":
    sys.exit(main())
