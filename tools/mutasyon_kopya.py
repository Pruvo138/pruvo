#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON KOPYA KÖKÜ + ÇAPA TÜRETME — mutasyon sürücülerinin ORTAK gövdesi.

🔴 NEDEN VAR (12 Ağu 2026, bağımsız çürütücünün ölçtüğü İKİ ayrı arıza):

(a) **AĞAÇ KİRLİLİĞİ = KARDEŞ NÖBETÇİNİN HÜKMÜNÜ BOZAR.** Sürücüler mutantı CANLI
    `tools/marka_model_build.py`ye yazıyor, diske `*.mutasyon-yedek` bırakıp
    `finally`/`atexit` ile geri alıyordu. Koşum kesilirse (SIGKILL, CI iptali, paralel
    oturum) yedek AĞAÇTA KALIYOR. Ölçüldü: artık yedek yüzünden `marka-model-test.py`
    rc=1 verdi ("bölüm kimliği ayrıştı"); AYNI SHA'nın temiz kopyasında rc=0. Yani bir
    sürücünün YAN ETKİSİ başka bir kapının kırmızısı olarak okundu.
    → [[kapi-yan-etkisi-gizli-onkosul]]

(b) **ÇAPA BAYATLIĞI = SESSİZ KAPSAM KAYBI.** Çapa dizesi ELLE yazılınca hedef kod
    yeniden yazıldığında sessizce eşleşmez olur. Ölçüldü: `marka-sayac-mutasyon.py`nin
    üç çapası 8 Ağu `bolum_ayrimi` refaktöründen beri bayattı ve sürücü HİÇBİR mutantı
    ölçemiyordu (`rc=3 OLCULEMEDI`). Fail-closed'du ama kapsam kaybı aylarca sürebilirdi.
    → [[ikiz-tanim-sessiz-ayrisma]] · [[mutasyon-kaniti-yeniden-uretilebilir]]

ÇÖZÜM:
  (a) Mutasyon **KOPYAYA** uygulanır: `tools/` geçici bir köke KOPYALANIR, kökün geri
      kalanı sembolik bağlanır (kapı yine GERÇEK katalog + gerçek `index.html` ile koşar).
      Canlı ağaca tek bayt yazılmaz ve bu `agac_damgasi()` ile baş/son KANITLANIR.
  (b) Çapa **ELLE YAZILMAZ**: hedef fonksiyonun (ya da JS gövdesi sabitinin) KENDİ
      kaynağından TÜRETİLİR. Türetilemezse ya da dönüşüm ETKİSİZ kalırsa hüküm
      `OLCULEMEDI` DEĞİL **KIRMIZI**'dır — bayatlama sessiz kalamaz.
"""
import hashlib
import importlib.util
import inspect
import linecache
import os
import re
import shutil

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)


class CapaHatasi(Exception):
    """Çapa türetilemedi ya da dönüşüm etkisiz kaldı — KIRMIZI (ölçülemedi DEĞİL)."""


# --------------------------------------------------------------------- kopya kök
def kopya_kok(tmp, kok=None):
    """`tools/` KOPYALANMIŞ, geri kalanı SEMBOLİK bağlı geçici bir depo kökü kur.

    Dönüş: kopya kökün yolu. Mutasyon yalnız `<kok>/tools/...` altında yapılır;
    `urunler.json` / `index.html` gerçek dosyalara bağlıdır (ölçüm gerçek katalogda kalır)."""
    kaynak_kok = kok or ROOT
    hedef = os.path.join(tmp, "repo")
    os.makedirs(hedef)
    for ad in sorted(os.listdir(kaynak_kok)):
        kaynak = os.path.join(kaynak_kok, ad)
        if ad == "tools":
            shutil.copytree(kaynak, os.path.join(hedef, "tools"),
                            ignore=shutil.ignore_patterns("__pycache__"))
        else:
            os.symlink(kaynak, os.path.join(hedef, ad))
    return hedef


def artik_yedekler(dizin=None):
    """Mutasyon sürücüsünün ARTIK dosyaları — `<dosya>.<surucu>-yedek` kalıntıları.

    🔴 DESEN DAR TUTULUR: `"yedek" in ad` YAZILAMAZ — `tools/` altında `yedekle.py`,
    `yedek-hook-test.py`, `yedekle-test.py` gibi MEŞRU araçlar var ve geniş desen onları
    "artık" sayıp kapıyı HER KOŞUMDA kırmızı yakardı (ölçüldü: 8 yanlış-pozitif).
    Artık dosya BİLİNEN bir son ek taşır: `-yedek` ile BİTER ve bir uzantıdan SONRA gelir
    (`marka_model_build.py.mutasyon-yedek`)."""
    kok = dizin or TOOLS
    return sorted(a for a in os.listdir(kok)
                  if a.endswith("-yedek") and ".py." in a)


def agac_damgasi(yollar):
    """Canlı ağacın DEĞİŞMEDİĞİNİ kanıtlayan damga: (sha256, artık-dosya listesi).

    Sürücü bunu baş ve sonda okur; ikisi eşit değilse ya da artık dosya kaldıysa hüküm
    KIRMIZI olur — "geri aldım" BEYANI bu depoda kanıt sayılmaz, ÖLÇÜLÜR."""
    h = hashlib.sha256()
    for yol in yollar:
        with open(yol, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16], artik_yedekler()


# --------------------------------------------------------------------- çapa türetme
def modul_yukle(yol, ad="mutasyon_hedefi"):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kapsam_kaynagi(mod, kapsam):
    """`kapsam` = modüldeki bir NİTELİK adı. Fonksiyon ise KENDİ kaynağı (inspect),
    dize ise dizenin kendisi (JS gövdeleri, CSS). Çapa TEK KAYNAKTAN türer.

    `mod` bir SÖZLÜK ise önceden çözülmüş harita olarak kullanılır (bkz. kapsam_haritasi)."""
    if isinstance(mod, dict):
        if kapsam not in mod:
            raise CapaHatasi("kapsam haritada YOK: %s" % (kapsam,))
        return mod[kapsam]
    hedef = getattr(mod, kapsam, None)
    if hedef is None:
        raise CapaHatasi("kapsam YOK: %s (yüklem kaldırılmış ya da yeniden adlandırılmış)"
                         % (kapsam,))
    if isinstance(hedef, str):
        return hedef
    # 🔴 linecache TAZELENIR: sürücü aynı dosyaya mutant yazıp geri aldığı için
    # `inspect` BAYAT satır önbelleğinden okuyabiliyor ve `lineno is out of bounds`
    # ile patlıyordu (ölçüldü: 2. mutantta). Kaynak her çağrıda diskten doğrulanır.
    linecache.checkcache(getattr(mod, "__file__", None) or "")
    return inspect.getsource(hedef)


def kapsam_haritasi(mod, kapsamlar):
    """TÜM kapsam kaynaklarını mutasyondan ÖNCE, dosya EL DEĞMEMİŞKEN çöz.

    🔴 NEDEN ZORUNLU: kapsam kaynağını mutasyon SIRASINDA çözmek, `inspect`in okuduğu
    dosyanın o an MUTANT (ya da az önce mutanttan geri alınmış) olmasına bağımlıdır —
    yani çapa, ölçülen şeyin kendisinden etkilenir. Harita bir kez, temiz durumda kurulur
    ve tüm mutantlar ONDAN türer."""
    return {k: kapsam_kaynagi(mod, k) for k in sorted(set(kapsamlar))}


def capa_satiri(blok, kapsam, desen):
    """`blok` içinde `desen`e uyan TEK satırı döndür (çapa BURADA doğar)."""
    vurus = [s for s in blok.splitlines() if re.search(desen, s)]
    if len(vurus) != 1:
        raise CapaHatasi("%s içinde %r desenine uyan satır %d tane (1 olmalı)"
                         % (kapsam, desen, len(vurus)))
    return vurus[0]


def mutant_metni(mod, metin, ciftler):
    """`ciftler` = [(kapsam, desen, donusum), ...]; her biri için çapayı TÜRET, uygula.

    🔴 TEKİLLİK KAPSAMA GÖRE ÖLÇÜLÜR, DOSYAYA GÖRE DEĞİL: `    return out` gibi bir satır
    dosyada 5 kez geçer ama HEDEF FONKSİYONDA bir kez. Mutasyon bu yüzden önce kapsamın
    KENDİ bloğunu (fonksiyon kaynağı / JS gövdesi sabiti) yalıtır, dönüşümü orada uygular
    ve bloğu bir bütün olarak geri yazar. Blok da dosyada tam bir kez geçmek ZORUNDA.

    FAIL-CLOSED, DÖRT AYRI KOL — hepsi `CapaHatasi` (KIRMIZI) yükseltir:
      1. kapsam YOK (yüklem kaldırılmış/yeniden adlandırılmış),
      2. kapsamın bloğu dosyada tam bir kez geçmiyor,
      3. desene uyan satır kapsam içinde tek değil,
      4. dönüşüm ETKİSİZ (yeni satır eskisiyle aynı) -> mutant sessizce no-op olurdu.
    """
    sirali, gruplar = [], {}
    for kapsam, desen, donusum in ciftler:
        if kapsam not in gruplar:
            gruplar[kapsam] = []
            sirali.append(kapsam)
        gruplar[kapsam].append((desen, donusum))
    for kapsam in sirali:
        blok = kapsam_kaynagi(mod, kapsam)
        if metin.count(blok) != 1:
            raise CapaHatasi("%s bloğu kaynakta %d kez geçiyor (1 olmalı)"
                             % (kapsam, metin.count(blok)))
        yeni_blok = blok
        for desen, donusum in gruplar[kapsam]:
            eski = capa_satiri(yeni_blok, kapsam, desen)
            if yeni_blok.count(eski) != 1:
                raise CapaHatasi("%s içinde çapa %d kez geçiyor (1 olmalı): %r"
                                 % (kapsam, yeni_blok.count(eski), eski[:90]))
            yeni = donusum(eski)
            if yeni == eski:
                raise CapaHatasi("dönüşüm ETKİSİZ (mutant no-op olurdu): %r" % (eski[:90],))
            yeni_blok = yeni_blok.replace(eski, yeni, 1)
        metin = metin.replace(blok, yeni_blok, 1)
    return metin


def bir_marka_adi(kok=None):
    """Marka-özel dal mutantı için GERÇEK bir marka adı — sürücülerde SABİT marka adı
    TUTULMAZ (marka sayaç kapısının MARKA_LITERAL iddiası o dosyaları da tarıyor)."""
    with open(os.path.join(kok or ROOT, "index.html"), encoding="utf-8") as f:
        m = re.search(r"var TANINMIS_MARKALAR = \[(.*?)\];", f.read(), re.S)
    return re.findall(r'"([^"]+)"', m.group(1))[0]
