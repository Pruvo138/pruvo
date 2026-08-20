#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Talep sihirbazi + /talep ucu kabul kapisi.

Davranis vakalari gercek JavaScript govdelerini node ile calistirir. Kaynak
eksenleri yalnizca varlik/yokluk iddialarini olcer. Mutasyonlar bellek kopyasina
uygulanir; ana kaynak dosyalari hicbir zaman yazilmaz.
"""

import hashlib
import collections
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
FIELDS = ROOT / "talep-alanlari.js"
DEPLOY = ROOT / ".github" / "workflows" / "deploy.yml"
NOBET = ROOT / ".github" / "workflows" / "nobet.yml"
BUILD = ROOT / "tools" / "build.py"
# 🔴 19 AGU 2026 (K184/VAKA36) — OLCUM YUZEYI TASIYICIDAN ISE BAGLANDI.
# ONCESI: bu aile deploy.yml/nobet.yml'in KABUK METNINI okuyordu (`# VARLIK_KOPYA_KOLU_BAS`
# yorumlari, `while IFS= read -r` dongusu, `echo "YAYIN VARLIGI DOGRULANDI: $n"` regex'i).
# K215 o blogu tools/yayin-topla.py'ye tasiyinca capa 0'a dustu -> `dosya=0`,
# `KOPYA_KOLU=KIRIK`, uc eksen `OLCULEMEDI` ve BATARYA KORELDI (mutant 38->17, kontrol 16->3):
# yayin-varlik ailesinin ~21 mutanti + 13 kontrolu HIC KOSMUYORDU. Kirmizi gorunurdu, asil
# kayip ALTINDA sessizdi ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
# SIMDI: capa GOVDEDEN turer ve `count==1` ile dogrulanir —
#   (i) workflow tarafi: yayin ADIMININ `run:` komutu ayristirilir (DELEGASYON capasi);
#   (ii) arac tarafi: `MANIFESTO` icindeki adim TURLERI sayilir (MANIFESTO capasi).
# Davranis METINDEN degil, aracin KENDISI hermetik fiksturde KOSTURULARAK olculur.
YAYIN_TOPLA = ROOT / "tools" / "yayin-topla.py"
# Yayin adimi capasi: iki workflow'da da BIREBIR ayni ad, TAM 1 kez.
YAYIN_ADIM_ADI = "- name: Yayin klasorunu topla (beyaz liste)"
# Tasiyici arac degisirse capa da onunla degisir; ADI degil YOLU olculur.
YAYIN_ARAC_YOLU = "tools/yayin-topla.py"
# Satir-ici kolun DIRILDIGINI gosteren izler: K215 sonrasi bu KOD desenlerinden hicbiri
# workflow'da kalmamali (kalirsa TEK KAYNAK iddiasi yalan olur ve iki govde ayrisir).
# ⚠️ YALNIZ KOD SATIRLARI taranir (`_yorumsuz`): iki workflow'un yorumlari eski blogu
# ANLATIYOR; yorum metnini kanit saymak komsuyu sahte-kirmiziya yakardi
# ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).
SATIR_ICI_KOL_IZLERI = (
    r"while\s+IFS=\s*read\s+-r\s+varlik",
    r'cp\s+"_yayin/\$varlik"',
    r"test\s+-s\s+_site/jenerator/hacim\.js",
)


def _yorumsuz(kaynak):
    """YAML yorum satirlarini (ilk gorunur karakteri `#`) duser — kod satirlari kalir."""
    return "\n".join(
        satir for satir in kaynak.splitlines()
        if not satir.lstrip().startswith("#")
    )
INDEX_START = "// ---- TALEP-SIHIRBAZI-SOZLESME-BAS ----"
INDEX_END = "// ---- TALEP-SIHIRBAZI-SOZLESME-SON ----"
SIHIRBAZ_CSS_START = "/* ---- TALEP-SIHIRBAZI-CSS-BAS ---- */"
SIHIRBAZ_CSS_END = "/* ---- TALEP-SIHIRBAZI-CSS-SON ---- */"
SIHIRBAZ_MARKUP_START = "<!-- ---- TALEP-SIHIRBAZI-MARKUP-BAS ---- -->"
SIHIRBAZ_MARKUP_END = "<!-- ---- TALEP-SIHIRBAZI-MARKUP-SON ---- -->"
SIHIRBAZ_CTA_START = "<!-- ---- TALEP-SIHIRBAZI-CTA-BAS ---- -->"
SIHIRBAZ_CTA_END = "<!-- ---- TALEP-SIHIRBAZI-CTA-SON ---- -->"
SIHIRBAZ_JS_START = "// ---- TALEP-SIHIRBAZI-JS-BAS ----"
SIHIRBAZ_JS_END = "// ---- TALEP-SIHIRBAZI-JS-SON ----"
TALEP = ROOT / "shop" / "src" / "talep.js"

# İki dönem aynı kapıda ölçülür: bugün uç kendi tavanlarını tanımlar ve değer
# paritesi bağlayıcıdır; import geldiğinde inline tanım kırmızı olmalıdır.
# Geçişte yalnız bu sabit değişir; iki iddia yine ayrı ayrı basılır ve ölçülür.
# Böylece import, değer karşılaştırmasını kendi kendine doğrulayan totoloji yapmaz.
ITHAL_INDI = False


def oku(yol):
    return yol.read_text(encoding="utf-8")


def sha(yol):
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def yerel_script_kaynaklari(index_kaynak):
    """index.html'deki mevcut kaynak JS'leri dinamik olarak çıkarır.

    taban-fiyatlar.js ve filament-veri.js build sırasında üretilir; kaynak ağacında
    bulunmadıkları için SOYULACAK_JS'nin kaynak dosyası kapsamına girmezler.
    """
    adlar = []
    for src in re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', index_kaynak):
        temiz = src.split("?", 1)[0]
        if temiz.startswith("/") and temiz.endswith(".js"):
            yol = temiz[1:]
            if (ROOT / yol).is_file() and yol not in adlar:
                adlar.append(yol)
    return adlar


def yayin_araci(kaynak=None):
    """`tools/yayin-topla.py`'yi MODÜL olarak yükler — yayın kolunun TEK KAYNAĞI.

    `kaynak` verilirse o METİN yüklenir (kaynak mutantı). Dosya ASLA yazılmaz;
    `__file__` gerçek yola işaretlenir ki modülün `BUILD_YOLU`'su gerçek `build.py`'yi
    bulsun. Bu, ölçümün üretim gövdesinin TA KENDİSİNDEN geçmesini sağlar: metin
    araması yok, ikinci tanım yok ([[aracin-teshis-cumlesi-olcum-degil]]).
    """
    if kaynak is None:
        if getattr(yayin_araci, "_onbellek", None) is None:
            yayin_araci._onbellek = yayin_araci(YAYIN_TOPLA.read_text(encoding="utf-8"))
        return yayin_araci._onbellek
    ad_alani = {"__name__": "pruvo_yayin_topla", "__file__": str(YAYIN_TOPLA),
                "__builtins__": __builtins__}
    exec(compile(kaynak, str(YAYIN_TOPLA), "exec"), ad_alani)
    return types.SimpleNamespace(**ad_alani)


def soyulacak_js_kumesi(build_kaynak, arac=None):
    """`build.py::SOYULACAK_JS` — okuyucusu ARACIN kendi AST kolu (ikinci tanım YOK).

    Mutant metin geçici bir dosyaya yazılıp `yayin-topla.soyulacak_js()`'ten geçirilir;
    böylece ölçüm ile üretim aynı ayrıştırıcıyı kullanır. Eskiden burada ayrı bir regex
    + `literal_eval` vardı — iki okuyucu zamanla ayrışırdı.
    """
    arac = arac or yayin_araci()
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8",
                                     delete=False) as dosya:
        dosya.write(build_kaynak)
        yol = dosya.name
    try:
        return set(arac.soyulacak_js(yol))
    finally:
        os.unlink(yol)


# ---- ÇAPA (i): WORKFLOW DELEGASYONU — gövdeden türer, count==1 ---------------
def yayin_adim_komutu(workflow_kaynak):
    """Yayın adımının `run:` komutunu workflow GÖVDESİNDEN türetir.

    Çapa iki kez sayılır: adım adı TAM 1, adımın içindeki `run:` TAM 1. Adım
    silinir/ikizlenirse ya da bloklu kabuğa (`run: |`) dönerse burası HATA verir —
    sessizce 'ölçemedim' demez."""
    adet = workflow_kaynak.count(YAYIN_ADIM_ADI)
    if adet != 1:
        raise RuntimeError("yayın adımı çapası %d (1 bekleniyor)" % adet)
    satirlar = workflow_kaynak.splitlines()
    i = next(no for no, satir in enumerate(satirlar) if YAYIN_ADIM_ADI in satir)
    girinti = len(satirlar[i]) - len(satirlar[i].lstrip())
    komutlar = []
    for satir in satirlar[i + 1:]:
        if not satir.strip():
            continue
        if len(satir) - len(satir.lstrip()) <= girinti:
            break                                  # adım bitti (sonraki adım/blok)
        eslesme = re.match(r"\s*run:\s*(.*)$", satir)
        if eslesme:
            komutlar.append(eslesme.group(1).strip())
    if len(komutlar) != 1:
        raise RuntimeError("yayın adımı `run:` çapası %d (1 bekleniyor)" % len(komutlar))
    return komutlar[0]


def yayin_delegasyon_olc(workflow_kaynak, workflow_adi):
    """Bu workflow'un yayın adımı TEK KAYNAĞA delege ediyor mu (+ fork dirilmiş mi)."""
    try:
        komut = yayin_adim_komutu(workflow_kaynak)
    except RuntimeError as hata:
        return {"durum": "KIRIK", "sebep": "ÇAPA: %s" % hata, "yol": None}
    eslesme = re.match(r"^python3\s+(\S+\.py)$", komut)
    if not eslesme:
        return {"durum": "KIRIK", "yol": None,
                "sebep": "DELEGASYON: `run:` tek kaynağa gitmiyor: %r" % komut[:80]}
    yol = eslesme.group(1)
    if yol != YAYIN_ARAC_YOLU:
        return {"durum": "KIRIK", "yol": yol,
                "sebep": "DELEGASYON: adım %r betiğine gidiyor, ölçülen %r"
                         % (yol, YAYIN_ARAC_YOLU)}
    # TEK KAYNAK: satır-içi kol DİRİLMEMİŞ olmalı. Diriltilirse iki gövde ayrışır ve
    # hijyen şeridi YAYINDA KOŞMAYAN bir mantığı 'yeşil' diye ölçmeye devam eder.
    kod = _yorumsuz(workflow_kaynak)
    kalinti = [d for d in SATIR_ICI_KOL_IZLERI if re.search(d, kod)]
    if kalinti:
        return {"durum": "KIRIK", "yol": yol,
                "sebep": "TEK KAYNAK: satır-içi kol kalıntısı %s" % sorted(kalinti)}
    return {"durum": "TAMAM", "sebep": "", "yol": yol}


# ---- ÇAPA (ii): MANIFESTO — aracın VERİSİNDEN türer, count==1 ----------------
MANIFESTO_CAPALARI = ("DIZIN_KUR", "VARLIK_KOPYA", "VARLIK_DOGRULA", "KRITIK_VARLIK")


def manifesto_capalarini_olc(manifesto):
    """Ölçtüğümüz üç kol manifestoda TAM BİRER kez var mı (silinme VE ikizlenme)."""
    sayim = collections.Counter(adim.tur for adim in manifesto)
    bozuk = ["%s=%d" % (tur, sayim[tur]) for tur in MANIFESTO_CAPALARI
             if sayim[tur] != 1]
    if bozuk:
        raise RuntimeError("manifesto çapası 1 değil: %s" % ", ".join(bozuk))
    return sayim


def yayin_tasinan_kume(arac, build_kaynak):
    """Aracın yayına GERÇEKTEN taşıdığı JS varlık kümesi.

    Hüküm METİNDEN değil MANIFESTO'dan türer (`yayin_varligi_tasiniyor_mu`). ⚠️ Bu
    karşılaştırma DAR bir iddiadır ve öyle olduğu bilinçlidir: küme `SOYULACAK_JS`'ten
    türediği için eşitlik ancak `VARLIK_KOPYA` adımı düşerse bozulur. Totolojiye karşı
    asıl teminat AYRI ve BAĞIMSIZ referanstır: `index.html`'in yüklediği dosyalar
    ([[isci-yesil-tablo-ic-olcumu-bosaltir]])."""
    yol = None
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8",
                                     delete=False) as dosya:
        dosya.write(build_kaynak)
        yol = dosya.name
    try:
        return set(
            rel for rel in arac.soyulacak_js(yol)
            if arac.yayin_varligi_tasiniyor_mu(
                rel, manifesto=arac.MANIFESTO, build_yolu=yol)
        )
    finally:
        os.unlink(yol)


def varlik_paritesi_olc(deploy_kaynak, nobet_kaynak, build_kaynak, arac=None,
                        referans_kumesi=None):
    """İki workflow AYNI tek kaynağa mı delege ediyor + o kaynak neyi taşıyor.

    K215 sonrası 'parite' artık iki kabuk bloğunun birbirine benzemesi DEĞİL, ikisinin
    de TEK gövdeyi çağırması demektir; ayrışma riski bu yüzden 'fork geri döndü'
    biçiminde ölçülür."""
    try:
        arac = arac or yayin_araci()
        soyulacak = soyulacak_js_kumesi(build_kaynak, arac)
        referans = set(referans_kumesi) if referans_kumesi is not None else soyulacak
        manifesto_capalarini_olc(arac.MANIFESTO)
        tasinan = yayin_tasinan_kume(arac, build_kaynak)
    except Exception as hata:
        return {
            "parite": "OLCULEMEDI", "farklar": [str(hata)], "rc": 1,
            "soyulacak": set(), "deploy": set(), "nobet": set(),
        }
    farklar = []
    delegeler = {}
    for ad, kaynak in (("deploy.yml", deploy_kaynak), ("nobet.yml", nobet_kaynak)):
        delege = yayin_delegasyon_olc(kaynak, ad)
        delegeler[ad] = delege
        if delege["durum"] != "TAMAM":
            farklar.append("%s %s" % (ad, delege["sebep"]))
    if delegeler["deploy.yml"]["yol"] != delegeler["nobet.yml"]["yol"]:
        farklar.append("deploy.yml<>nobet.yml farklı tek kaynak: %r vs %r" % (
            delegeler["deploy.yml"]["yol"], delegeler["nobet.yml"]["yol"]))
    eksik = sorted(referans - tasinan)
    fazla = sorted(tasinan - referans)
    if eksik or fazla:
        farklar.append("taşınan küme eksik=%s fazla=%s" % (eksik or "YOK", fazla or "YOK"))
    parite = "TAMAM" if not farklar else "SAPMA"
    # Delegasyonu KIRIK olan workflow için taşınan küme HÜKÜM DEĞİLDİR: ölçtüğümüz
    # gövde o workflow'da koşmuyor demektir, boş küme döner ve `_site=HAYIR` basılır.
    return {
        "parite": parite, "farklar": farklar, "rc": 0 if parite == "TAMAM" else 1,
        "soyulacak": soyulacak,
        "deploy": tasinan if delegeler["deploy.yml"]["durum"] == "TAMAM" else set(),
        "nobet": tasinan if delegeler["nobet.yml"]["durum"] == "TAMAM" else set(),
    }


# ---- DAVRANIŞ: aracı HERMETİK FİKSTÜRDE KOŞTUR (metin okuma YOK) -------------
def yayin_fiksturunde_kos(arac, manifesto=None, bozan=None):
    """Aracın KENDİ fikstüründe `topla()` koşturur — ikinci fikstür tanımı ÜRETİLMEZ.

    `bozan(arac, kok)` fikstür kurulduktan SONRA çağrılır (arıza enjeksiyonu)."""
    man = arac.MANIFESTO if manifesto is None else manifesto
    gecici = tempfile.mkdtemp(prefix="pruvo-k184-yayin-")
    try:
        arac._fikstur_kur(gecici)
        if bozan is not None:
            bozan(arac, gecici)
        try:
            _adim, _slug, varlik = arac.topla(gecici, man)
        except Exception as hata:
            return {"rc": 1, "hata": str(hata), "varlik": 0, "ozet": None}
        return {"rc": 0, "hata": "", "varlik": varlik,
                "ozet": arac.agac_ozeti(arac._tam(gecici, arac.SITE))}
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _bozan_varlik_eksik(arac, kok):
    """Manifestte YAZAN varlığın `_yayin/` kopyası yok -> KOPYA kolu durdurmalı."""
    os.remove(arac._tam(kok, "_yayin/talep-alanlari.js"))


def _bozan_varlik_bos(arac, kok):
    """Varlık kopyalanır ama BOŞ -> yalnız DOĞRULAMA kolu görür (kopya kolu görmez)."""
    with open(arac._tam(kok, "_yayin/talep-alanlari.js"), "w", encoding="utf-8") as f:
        f.write("")


def _bozan_kritik_dusur(arac, kok):
    """Kritik varlık manifestten VE `_yayin`den düşer -> `_site`e hiç kopyalanmaz."""
    kalan = [rel for rel in arac.FIKSTUR_VARLIKLARI if rel != "jenerator/hacim.js"]
    with open(arac._tam(kok, arac.VARLIK_MANIFESTI), "w", encoding="utf-8") as f:
        f.write("\n".join(kalan) + "\n")
    os.remove(arac._tam(kok, "_yayin/jenerator/hacim.js"))


_DAVRANIS_ONBELLEGI = {}


def yayin_davranisi_olc(arac):
    """Yayın kolunun üç ekseni: POZİTİF (temiz koşum) + NEGATİF (arıza) birlikte.

    Yalnız 'temiz koşumda hata çıkmadı' demek AMBİYANS ölçmektir: kol tamamen sökülmüş
    olsa da temiz fikstürde hata çıkmaz. Bu yüzden her eksen bir ARIZA vakasıyla
    birlikte hüküm verir ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]])."""
    anahtar = id(arac)
    if anahtar in _DAVRANIS_ONBELLEGI:
        return _DAVRANIS_ONBELLEGI[anahtar][1]
    sonuc = _yayin_davranisi_hesapla(arac)
    _DAVRANIS_ONBELLEGI[anahtar] = (arac, sonuc)
    return sonuc


def _yayin_davranisi_hesapla(arac):
    olculemedi = {
        "kopya_kolu": "OLCULEMEDI", "varlik_dogrulama": "OLCULEMEDI",
        "kritik_varlik": "OLCULEMEDI", "rc": 1, "dosya": 0, "dogrulanan": 0,
        "esdegerlik": [], "sebep": "",
    }
    try:
        manifesto_capalarini_olc(arac.MANIFESTO)
    except RuntimeError as hata:
        olculemedi["sebep"] = "ÇAPA: %s" % hata
        return olculemedi
    try:
        temiz = yayin_fiksturunde_kos(arac)
        eksik = yayin_fiksturunde_kos(arac, bozan=_bozan_varlik_eksik)
        bos = yayin_fiksturunde_kos(arac, bozan=_bozan_varlik_bos)
        kritik = yayin_fiksturunde_kos(arac, bozan=_bozan_kritik_dusur)
    except Exception as hata:                 # fikstür kurulamadı -> ÖLÇÜLEMEDİ
        olculemedi["sebep"] = "FİKSTÜR: %s" % hata
        return olculemedi
    esdegerlik = arac._esdegerlik_hatalari(temiz["ozet"]) if temiz["rc"] == 0 else [
        "temiz fikstürde toplama KIRMIZI: %s" % temiz["hata"]
    ]
    beklenen_varlik = len(arac.FIKSTUR_VARLIKLARI)
    kopya_ok = (
        temiz["rc"] == 0 and not esdegerlik and
        eksik["rc"] != 0 and "talep-alanlari.js" in eksik["hata"]
    )
    dogrulama_ok = (
        temiz["rc"] == 0 and temiz["varlik"] == beklenen_varlik and
        bos["rc"] != 0 and "talep-alanlari.js" in bos["hata"]
    )
    kritik_ok = (
        temiz["rc"] == 0 and
        kritik["rc"] != 0 and "jenerator/hacim.js" in kritik["hata"]
    )
    sebepler = []
    if not kopya_ok:
        sebepler.append("KOPYA(temiz_rc=%d esdeg=%d eksik_rc=%d)" % (
            temiz["rc"], len(esdegerlik), eksik["rc"]))
    if not dogrulama_ok:
        sebepler.append("DOGRULAMA(varlik=%d/%d bos_rc=%d)" % (
            temiz["varlik"], beklenen_varlik, bos["rc"]))
    if not kritik_ok:
        sebepler.append("KRITIK(kritik_rc=%d)" % kritik["rc"])
    return {
        "kopya_kolu": "TAMAM" if kopya_ok else "KIRIK",
        "varlik_dogrulama": "TAMAM" if dogrulama_ok else "KIRIK",
        "kritik_varlik": "TAMAM" if kritik_ok else "KIRIK",
        "rc": 0 if (kopya_ok and dogrulama_ok and kritik_ok) else 1,
        "dosya": beklenen_varlik if kopya_ok else 0,
        "dogrulanan": temiz["varlik"] if dogrulama_ok else 0,
        "esdegerlik": esdegerlik,
        "sebep": "; ".join(sebepler),
    }


def yayin_yolu_vakasi(index_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak,
                      arac=None):
    """VAKA 36 — `index.html`'in yüklediği yerel JS'lerin yayına çıkan yolu, UÇTAN UCA.

    Dört koşul birden: (a) bağımsız referans = index'in `<script src>` dosyaları;
    (b) beyaz listede (`SOYULACAK_JS`) ve araç onları TAŞIYOR; (c) iki workflow da
    o tek kaynağa delege ediyor, satır-içi fork YOK; (d) aracın kopya/doğrulama/kritik
    kolları hermetik fikstürde GERÇEKTEN çalışıyor ve fail-closed."""
    arac = arac or yayin_araci()
    varlikler = yerel_script_kaynaklari(index_kaynak)
    olcum = varlik_paritesi_olc(deploy_kaynak, nobet_kaynak, build_kaynak, arac)
    soyulacak = olcum["soyulacak"]
    kopyalanacak = olcum["deploy"] & olcum["nobet"]
    davranis = yayin_davranisi_olc(arac)
    ok = (
        bool(varlikler) and olcum["parite"] == "TAMAM" and
        all(ad in soyulacak and ad in kopyalanacak for ad in varlikler) and
        davranis["kopya_kolu"] == "TAMAM" and
        davranis["varlik_dogrulama"] == "TAMAM" and
        davranis["kritik_varlik"] == "TAMAM"
    )
    return ok, varlikler, soyulacak, kopyalanacak


def capali_govde(kaynak, bas, son, etiket):
    if kaynak.count(bas) != 1 or kaynak.count(son) != 1:
        raise RuntimeError("%s çapa sayısı 1 değil" % etiket)
    bas_i = kaynak.index(bas) + len(bas)
    son_i = kaynak.index(son)
    if bas_i >= son_i:
        raise RuntimeError("%s çapa sırası bozuk" % etiket)
    return kaynak[bas_i:son_i]


def dizi_cikar(kaynak, ad):
    eslesme = re.search(r"\bvar\s+" + re.escape(ad) + r"\s*=\s*(\[[^;\n]*\])\s*;", kaynak)
    if not eslesme:
        raise RuntimeError("%s dizi tanımı çıkarılamadı" % ad)
    try:
        return json.loads(eslesme.group(1))
    except json.JSONDecodeError as hata:
        raise RuntimeError("%s dizi JSON değil: %s" % (ad, hata))


def node_calistir(kod):
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as dosya:
        dosya.write(kod)
        yol = dosya.name
    try:
        sonuc = subprocess.run(
            ["node", yol], text=True, capture_output=True, check=False
        )
    finally:
        try:
            os.unlink(yol)
        except FileNotFoundError:
            pass
    if sonuc.returncode != 0:
        raise RuntimeError("node rc=%d: %s" % (sonuc.returncode, (sonuc.stderr or sonuc.stdout).strip()))
    try:
        return json.loads(sonuc.stdout)
    except json.JSONDecodeError as hata:
        raise RuntimeError("node JSON çıktısı okunamadı: %s / %r" % (hata, sonuc.stdout[-500:]))


def index_vakalari(kaynak):
    block = capali_govde(kaynak, INDEX_START, INDEX_END, "sihirbaz")
    cats = dizi_cikar(kaynak, "CATEGORIES")
    gizli = dizi_cikar(kaynak, "GIZLI_KATEGORILER")
    fields = oku(FIELDS)
    durum = {
        "kategori": cats[0], "marka": "X", "model": "Y", "yil": "2015-2018",
        "parca_adi": "P", "notu": "", "website": "",
    }
    kod = r'''
const window = {};
var CATEGORIES = %s;
var GIZLI_KATEGORILER = %s;
eval(%s);
const durum = %s;
const bosParca = Object.assign({}, durum, {parca_adi: "   "});
const honeypot = Object.assign({}, durum, {website: "bot"});
const sonuc = {
  "1": window.__talepAdimGecerli(1, {}),
  "2": window.__talepAdimGecerli(1, {kategori: CATEGORIES[0]}),
  "3": window.__talepAdimGecerli(1, {kategori: "Jeneratör"}),
  "4": window.__talepAdimGecerli(1, {kategori: "UydurmaKategori"}),
  "5": window.__talepAdimGecerli(2, {marka: "X"}),
  "6": window.__talepAdimGecerli(2, {marka: "X", model: "Y"}),
  "7": window.__talepAdimGecerli(3, {parca_adi: "   "}),
  "8": window.__talepAdimGecerli(4, {}),
  "9": window.__talepAdimGecerli(5, {notu: "N", website: ""}),
  "10": window.__talepAdimGecerli(5, honeypot),
  "11": window.__talepAdimGecerli(6, durum),
  "12": window.__talepAdimGecerli(6, bosParca),
  "13": window.__talepGovdeKur(durum).website === "" && window.__talepGovdeKur(durum).kanal === "site" && Object.keys(window.__talepGovdeKur(durum)).join(",") === "kanal,kategori,marka,model,yil,parca_adi,notu,website",
  "14": !/\bad\b|\biletisim\b/.test(%s)
};
process.stdout.write(JSON.stringify(sonuc));
''' % (json.dumps(cats, ensure_ascii=False), json.dumps(gizli, ensure_ascii=False), json.dumps(fields + "\n" + block), json.dumps(durum, ensure_ascii=False), json.dumps(block))
    ham = node_calistir(kod)
    beklenen = {
        "1": False, "2": True, "3": False, "4": False, "5": False,
        "6": True, "7": False, "8": True, "9": True, "10": False,
        "11": True, "12": False, "13": True, "14": True,
    }
    return {k: ham[k] == beklenen[k] for k in ham}, block, cats, gizli


def sihirbaz_yuzeyleri(kaynak):
    tanimlar = {
        "css": (SIHIRBAZ_CSS_START, SIHIRBAZ_CSS_END),
        "markup": (SIHIRBAZ_MARKUP_START, SIHIRBAZ_MARKUP_END),
        "cta": (SIHIRBAZ_CTA_START, SIHIRBAZ_CTA_END),
        "js": (SIHIRBAZ_JS_START, SIHIRBAZ_JS_END),
    }
    yuzeyler = {}
    for ad, (bas, son) in tanimlar.items():
        if kaynak.count(bas) != 1 or kaynak.count(son) != 1:
            yuzeyler[ad] = ""
            continue
        yuzeyler[ad] = capali_govde(kaynak, bas, son, "sihirbaz " + ad)
    return yuzeyler


def sihirbaz_kaynagi(kaynak):
    yuzeyler = sihirbaz_yuzeyleri(kaynak)
    return "\n".join(yuzeyler.values())


def talep_drift_olc(fields_kaynak, talep_kaynak=None, ithal_indi=ITHAL_INDI):
    """İki drift iddiasını birbirinden bağımsız ölçer."""
    if talep_kaynak is None:
        if not TALEP.is_file():
            return {
                "deger_paritesi": "OLCULEMEDI",
                "ikinci_tanim": "OLCULEMEDI",
                "farklar": ["shop/src/talep.js yok"],
                "rc": None,
            }
        talep_kaynak = oku(TALEP)

    ortak = {
        alan: int(tavan)
        for alan, tavan, _ in re.findall(
            r"(kategori|marka|model|yil|parca_adi|notu):\s*\{\s*tavan:\s*([0-9]+),\s*zorunlu:\s*(true|false)",
            fields_kaynak,
        )
    }
    tablo_eslesme = re.search(
        r"(?:export\s+)?const\s+ALAN_TAVANLARI\s*=\s*Object\.freeze\(\s*\{(.*?)\}\s*\)",
        talep_kaynak,
        re.S,
    )
    alan_tavanlari = {}
    if tablo_eslesme:
        alan_tavanlari = {
            alan: int(tavan)
            for alan, tavan in re.findall(
                r"\b(kategori|marka|model|yil|parca_adi|notu)\s*:\s*([0-9]+)",
                tablo_eslesme.group(1),
            )
        }
    govde = re.search(r"\bGOVDE_BAYT_TAVANI\s*=\s*([0-9]+)", talep_kaynak)
    ortak_govde = re.search(r"PRUVO_TALEP_GOVDE_TAVANI\s*=\s*([0-9]+)", fields_kaynak)
    farklar = []
    if tablo_eslesme:
        for alan in sorted(set(ortak) | set(alan_tavanlari)):
            if alan_tavanlari.get(alan) != ortak.get(alan):
                farklar.append("%s: uç=%s ortak=%s" % (
                    alan, alan_tavanlari.get(alan), ortak.get(alan)
                ))
        if not govde or not ortak_govde or int(govde.group(1)) != int(ortak_govde.group(1)):
            farklar.append("GOVDE_BAYT_TAVANI: uç=%s ortak=%s" % (
                govde.group(1) if govde else "YOK",
                ortak_govde.group(1) if ortak_govde else "YOK",
            ))
        deger_paritesi = "TAMAM" if not farklar else "SAPMA"
    else:
        deger_paritesi = "OLCULEMEDI"

    ikinci_tanim = "VAR" if tablo_eslesme else "YOK"
    baglayici = ikinci_tanim if ithal_indi else deger_paritesi
    if baglayici == "OLCULEMEDI":
        rc = None
    elif (ithal_indi and baglayici == "VAR") or (not ithal_indi and baglayici == "SAPMA"):
        rc = 1
    else:
        rc = 0
    return {
        "deger_paritesi": deger_paritesi,
        "ikinci_tanim": ikinci_tanim,
        "farklar": farklar,
        "rc": rc,
    }


def talep_drift_vakalari(fields_kaynak, talep_kaynak=None, ithal_indi=ITHAL_INDI):
    """K186 ucunun iki bağımsız drift jetonunu vaka 15'e bağlar."""
    olcum = talep_drift_olc(fields_kaynak, talep_kaynak, ithal_indi)
    return {"15": None if olcum["rc"] is None else olcum["rc"] == 0}, olcum["farklar"]


def talep_e2e_vakalari(index_kaynak):
    """İstemci gövdesini doğrudan K186 talepKaydet fonksiyonuna verir."""
    if not TALEP.is_file():
        return {"16": None, "17": None, "18": None}, "shop/src/talep.js yok"
    fields = oku(FIELDS)
    block = capali_govde(index_kaynak, INDEX_START, INDEX_END, "sihirbaz")
    kod = r'''
import * as m from %s;
const k186GovdeKur = m.__talepGovdeKur || (m.default && m.default.__talepGovdeKur);
const kaydet = m.talepKaydet || (m.default && m.default.talepKaydet);
var window = globalThis;
var CATEGORIES = %s;
var GIZLI_KATEGORILER = %s;
eval(%s);
eval(%s);
const govdeKur = k186GovdeKur || window.__talepGovdeKur;
if (typeof govdeKur !== "function" || typeof kaydet !== "function") throw new Error("K186 talep API'si yok");
const durum = {kategori: CATEGORIES[0], marka: "X", model: "Y", yil: "2015-2018", parca_adi: "P", notu: "", website: ""};
const govde = govdeKur(durum);
const env = {KATALOG: {prepare: () => ({bind: () => ({run: async () => ({success: true})})})}};
const istek = (origin, body) => new Request("https://pruvo3d.com/api/shop/talep", {method:"POST", headers:Object.assign({"Content-Type":"application/json"}, origin ? {"Origin": origin} : {}), body:JSON.stringify(body || govde)});
const calistir = async () => {
  const ok = await kaydet(istek("https://pruvo3d.com", govde), env, {});
  const okGovde = await ok.json();
  const originsiz = await kaydet(istek("", govde), env, {});
  const red = await kaydet(istek("https://pruvo3d.com", Object.assign({}, govde, {parca_adi:"x".repeat(121)})), env, {});
  process.stdout.write(JSON.stringify({
    "16": ok.status === 200 && /^PR-/.test(okGovde.kod || ""),
    "17": originsiz.status === 400,
    "18": red.status === 400,
    "olcum": {originli_http: ok.status, kod: okGovde.kod || null, originsiz_http: originsiz.status, tavan_http: red.status}
  }));
};
calistir();
''' % (
        json.dumps(TALEP.as_uri()),
        json.dumps(dizi_cikar(index_kaynak, "CATEGORIES"), ensure_ascii=False),
        json.dumps(dizi_cikar(index_kaynak, "GIZLI_KATEGORILER"), ensure_ascii=False),
        json.dumps(fields), json.dumps(block),
    )
    # K186 dikişi ölçülebildiğinde de ÇAĞIRANIN beklediği 2'li demet dönmeli:
    # çıplak sözlük dönerse `e2e, _ = ...` çözülmesi patlar ve kapı VAKA=0 ile kör kalır.
    return node_calistir(kod), ""


def kaynak_vakalari(index_kaynak, index_block):
    yuzeyler = sihirbaz_yuzeyleri(index_kaynak)
    block_lower = index_block.lower()
    wa = re.findall(r"https://wa\.me/([^\"?\s<]+)", index_block)
    dis = re.findall(
        r'<script\s+src="http|<link[^>]+href="http|fetch\(["\']http|url\(\s*["\']?https?://',
        block_lower,
    )
    return {
        "19": index_block.count('<input type="file') == 0,
        "20": len(re.findall(r"\bvar\s+CATEGORIES\s*=", index_kaynak)) == 1 and len(re.findall(r"\bvar\s+CATEGORIES\s*=", index_block)) == 0,
        "21": not re.search(r"3d bask|3d print|üç boyutlu bask", block_lower),
        "22": not re.search(r"fethiye|göcek|muğla|dalaman", block_lower),
        "23": bool(wa) and all(num == "905451386526" for num in wa) and not re.search(r"532|595|4005", index_block),
        "24": not re.search(r"anthropic|openai|claude|kimi|moonshot|deepseek|gemini|/api/ege|llm|chat/completions", block_lower),
        "25": len(dis) == 0,
        "26": all(len(yuzeyler[ad]) >= 200 for ad in ("css", "markup", "cta", "js")),
        "27": all(token in yuzeyler[ad] for token, ad in (
            ("talepOverlay", "markup"), ("talepPanel", "markup"), ("talepAc", "cta"),
            (".talep-chip", "css"), ("talepDurum", "js"), ("__talepAdimGecerli", "js")
        )),
    }


def tek_kaynak_vakalari(index_kaynak, index_block, fields_kaynak):
    yuzey = sihirbaz_kaynagi(index_kaynak)
    ciplak = 0
    for tavan in (40, 60, 120, 500, 4096):
        ciplak += len(re.findall(r"(?<![A-Za-z0-9_])%d(?![A-Za-z0-9_])" % tavan, yuzey))
    beklenen = {
        "kategori": (40, True), "marka": (60, True), "model": (60, True),
        "yil": (20, False), "parca_adi": (120, True), "notu": (500, False),
    }
    tablo = re.findall(r"(kategori|marka|model|yil|parca_adi|notu): \{ tavan: ([0-9]+), zorunlu: (true|false) \}", fields_kaynak)
    tablo_tam = {alan: (int(tavan), zorunlu == "true") for alan, tavan, zorunlu in tablo}
    return {
        "30": ciplak == 0,
        "31": fields_kaynak.count("PRUVO_TALEP_ALANLARI =") == 1 and len(tablo) == 6 and tablo_tam == beklenen,
        "32": all(token in yuzey for token in ("parca_adi", "notu", "website")) and
               not any(token in yuzey for token in ("firma_web", "parca:", "not:", '"ad"', '"iletisim"')),
        "33": not re.search(r"(?<![A-Za-z0-9_])(?:40|60|120|500|4096)(?![A-Za-z0-9_])", index_block),
    }


def d2_vakalari(index_kaynak, worker_kaynak, fields_kaynak):
    index_block = capali_govde(index_kaynak, INDEX_START, INDEX_END, "sihirbaz")
    worker = re.sub(r"^import .*;\n", "", worker_kaynak, flags=re.MULTILINE)
    worker = re.sub(r"\bexport\s+const\b", "const", worker)
    worker = re.sub(r"\bexport\s+function\b", "function", worker)
    worker = worker.replace("export default {", "const defaultWorker = {")
    kod = r'''
var window = globalThis;
var CATEGORIES = %s;
var GIZLI_KATEGORILER = %s;
eval(%s);
eval(%s);
eval(%s);
const durum = {kategori: CATEGORIES[0], marka: "X", model: "Y", yil: "2015-2018", parca_adi: "P", notu: "N", website: ""};
const govde = window.__talepGovdeKur(durum);
%s
const env = {KATALOG: {prepare: () => ({bind: () => ({run: async () => ({success: true})})})}};
const istek = (origin) => new Request("https://pruvo3d.com/api/shop/talep", {method:"POST", headers: Object.assign({"Content-Type":"application/json"}, origin ? {"Origin": origin} : {}), body: JSON.stringify(govde)});
const sızıntıIstek = new Request("https://pruvo3d.com/api/shop/talep", {method:"POST", headers:{"Content-Type":"application/json","Origin":"https://pruvo3d.com","CF-Connecting-IP":"3"}, body: JSON.stringify(Object.assign({}, govde, {kategori:""}))});
const redIstek = new Request("https://pruvo3d.com/api/shop/talep", {method:"POST", headers:{"Content-Type":"application/json","Origin":"https://pruvo3d.com","CF-Connecting-IP":"4"}, body: JSON.stringify(Object.assign({}, govde, {parca_adi:"x".repeat(121)}))});
const fazlaIstek = new Request("https://pruvo3d.com/api/shop/talep", {method:"POST", headers:{"Content-Type":"application/json","Origin":"https://pruvo3d.com","CF-Connecting-IP":"5"}, body: JSON.stringify(Object.assign({}, govde, {fazla:"x"}))});
const calistir = async () => {
  const ok = await defaultWorker.fetch(istek("https://pruvo3d.com"), env, {});
  const okGovde = await ok.json();
  const kaynaksiz = await defaultWorker.fetch(istek(""), env, {});
  const red = await defaultWorker.fetch(sızıntıIstek, env, {});
  const redGovde = await red.json();
  const fazla = await defaultWorker.fetch(fazlaIstek, env, {});
  const fazlaGovde = await fazla.json();
  process.stdout.write(JSON.stringify({
    "31": ok.status === 200 && /^PR-[A-Z0-9]{6}$/.test(okGovde.kod || ""),
    "32": kaynaksiz.status === 400,
    "37": red.status === 400 && redGovde.hata === "gecersiz" && redGovde.wa === "https://wa.me/905451386526" && Object.keys(redGovde).sort().join(",") === "hata,wa",
    "38": (await defaultWorker.fetch(redIstek, env, {})).status === 400,
    "d2": {originli_http: ok.status, kod: okGovde.kod, originsiz_http: kaynaksiz.status}
  }));
};
calistir();
''' % (json.dumps(dizi_cikar(index_kaynak, "CATEGORIES"), ensure_ascii=False), json.dumps(dizi_cikar(index_kaynak, "GIZLI_KATEGORILER"), ensure_ascii=False), json.dumps(oku(ROOT / "secenekler.js")), json.dumps(fields_kaynak), json.dumps(index_block), worker)
    return node_calistir(kod)


def eski_tum_vakalari(index_kaynak, worker_kaynak, fields_kaynak, import_kullan=False):
    iv, ib, cats, gizli = index_vakalari(index_kaynak)
    if import_kullan and index_kaynak == oku(INDEX) and worker_kaynak == oku(WORKER):
        wv = worker_import_vakalari()
    else:
        wv = worker_fallback_vakalari(worker_kaynak, fields_kaynak)
    sv = kaynak_vakalari(index_kaynak, sihirbaz_kaynagi(index_kaynak), worker_kaynak)
    tv = tek_kaynak_vakalari(index_kaynak, ib, worker_kaynak, fields_kaynak)
    dv = d2_vakalari(index_kaynak, worker_kaynak, fields_kaynak)
    sonuc = {}
    sonuc.update({int(k): bool(v) for k, v in iv.items()})
    sonuc.update({int(k): bool(v) for k, v in wv.items()})
    sonuc.update({int(k): bool(v) for k, v in sv.items()})
    sonuc.update({int(k): bool(v) for k, v in tv.items()})
    sonuc.update({int(k): bool(v) for k, v in dv.items() if k != "d2"})
    if set(sonuc) != set(range(1, 39)):
        raise RuntimeError("vaka kümesi 1..38 değil: %r" % sorted(sonuc))
    return sonuc


def tum_vakalari(index_kaynak, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak,
                 arac=None):
    iv, ib, cats, gizli = index_vakalari(index_kaynak)
    sv = kaynak_vakalari(index_kaynak, sihirbaz_kaynagi(index_kaynak))
    tv = tek_kaynak_vakalari(index_kaynak, ib, fields_kaynak)
    drift, _ = talep_drift_vakalari(fields_kaynak)
    e2e, _ = talep_e2e_vakalari(index_kaynak)
    sonuc = {}
    sonuc.update({int(k): bool(v) for k, v in iv.items()})
    sonuc.update({int(k): v for k, v in drift.items()})
    sonuc.update({int(k): v for k, v in e2e.items() if k != "olcum"})
    sonuc.update({int(k): bool(v) for k, v in sv.items()})
    sonuc.update({int(k): bool(v) for k, v in tv.items()})
    sonuc[36] = yayin_yolu_vakasi(index_kaynak, deploy_kaynak, nobet_kaynak,
                                  build_kaynak, arac)[0]
    beklenen = set(range(1, 28)) | set(range(30, 34)) | {36}
    if set(sonuc) != beklenen:
        raise RuntimeError("vaka kümesi beklenenden farklı: %r" % sorted(sonuc))
    return sonuc


def normal_kos(index_kaynak, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak):
    sonuc = tum_vakalari(index_kaynak, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak)
    drift_olcumu = talep_drift_olc(fields_kaynak)
    if drift_olcumu["deger_paritesi"] == "SAPMA":
        print("DEGER_PARITESI SAPMA: %s" % "; ".join(drift_olcumu["farklar"]))
    dusen = 0
    olculemedi = 0
    if not TALEP.is_file():
        print("OLCULEMEDI: shop/src/talep.js YOK — K186 main'e inmeden istemci-uç dikişi ÖLÇÜLEMEZ")
    for num in sorted(sonuc):
        if sonuc[num] is None:
            print("VAKA %d OLCULEMEDI" % num)
            olculemedi += 1
        elif sonuc[num]:
            print("VAKA %d GECTI" % num)
        else:
            print("VAKA %d DUSTU" % num)
            dusen += 1
    arac = yayin_araci()
    yayin_ok, varlikler, soyulacak, kopyalanacak = yayin_yolu_vakasi(
        index_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak, arac
    )
    varlik_olcumu = varlik_paritesi_olc(deploy_kaynak, nobet_kaynak, build_kaynak, arac)
    if varlik_olcumu["parite"] != "TAMAM":
        print("VARLIK_PARITESI=%s rc=%d fark=%s" % (
            varlik_olcumu["parite"], varlik_olcumu["rc"],
            "; ".join(varlik_olcumu["farklar"]) or "YOK",
        ))
    else:
        print("VARLIK_PARITESI=TAMAM rc=0")
    davranis = yayin_davranisi_olc(arac)
    for workflow_adi, workflow in (("deploy.yml", deploy_kaynak), ("nobet.yml", nobet_kaynak)):
        delege = yayin_delegasyon_olc(workflow, workflow_adi)
        # 🔴 DELEGASYON KIRIKSA ARACIN YEŞİLİ O WORKFLOW İÇİN HÜKÜM DEĞİLDİR: ölçtüğümüz
        # gövde orada koşmuyor demektir. Yeşil aracı yeşil workflow saymak, tam da
        # taşıyıcı değişince kapanan gözün kendisi olurdu.
        if delege["durum"] != "TAMAM":
            print("KOPYA_KOLU=KIRIK workflow=%s rc=1 dosya=0 sebep=%s"
                  % (workflow_adi, delege["sebep"]))
            print("VARLIK_DOGRULAMA=KIRIK workflow=%s rc=1 dosya=0 sebep=DELEGASYON"
                  % workflow_adi)
            print("KRITIK_VARLIK=KIRIK workflow=%s rc=1 sebep=DELEGASYON" % workflow_adi)
            dusen += 1
            continue
        print("KOPYA_KOLU=%s workflow=%s rc=%d dosya=%d arac=%s%s" % (
            davranis["kopya_kolu"], workflow_adi, davranis["rc"], davranis["dosya"],
            delege["yol"], (" sebep=" + davranis["sebep"]) if davranis["sebep"] else "",
        ))
        print("VARLIK_DOGRULAMA=%s workflow=%s rc=%d dosya=%d" % (
            davranis["varlik_dogrulama"], workflow_adi, davranis["rc"],
            davranis["dogrulanan"],
        ))
        print("KRITIK_VARLIK=%s workflow=%s rc=%d" % (
            davranis["kritik_varlik"], workflow_adi, davranis["rc"]
        ))
        if davranis["kopya_kolu"] == "OLCULEMEDI" or davranis["kritik_varlik"] == "OLCULEMEDI":
            olculemedi += 1
        elif davranis["rc"] != 0:
            dusen += 1
    print("Yayın yolu VAKA 36: %s varlıkları=%s SOYULACAK_JS=%s _site=%s" % (
        "GECTI" if yayin_ok else "DUSTU", ",".join(varlikler) or "YOK",
        "EVET" if all(ad in soyulacak for ad in varlikler) else "HAYIR",
        "EVET" if all(ad in kopyalanacak for ad in varlikler) else "HAYIR",
    ))
    return sonuc, dusen, olculemedi, drift_olcumu["deger_paritesi"], drift_olcumu["ikinci_tanim"]


def degistir(kaynak, degisimler, etiket):
    kopya = kaynak
    for eski, yeni in degisimler:
        adet = kopya.count(eski)
        if adet != 1:
            raise RuntimeError("%s çapa sayısı %d (1 bekleniyor): %r" % (etiket, adet, eski[:100]))
        kopya = kopya.replace(eski, yeni, 1)
    return kopya


# 🔴 KAPSAM ÇAPASI (19 Ağu 2026, K184/VAKA36) — BATARYA SESSİZCE KÜÇÜLMESİN.
# 19 Ağu'da tam bu oldu: TEK bir `degistir` çapası bayatladı, fırlattığı istisna
# bataryayı ORTASINDAN kesti; `MUTANT 38/38 -> 17/17`, `KONTROL 16/16 -> 3/3` düştü ve
# çıktı yine "hepsi geçti" biçiminde YEŞİL sayılar bastı. Yani yayın-varlık ailesinin
# ~21 mutantı + 13 kontrolü hiç koşmadan kayboldu; görünen kırmızı asıl kaybı GİZLEDİ.
# Aşağıdaki TABAN, koşulan mutant/kontrol SAYISI altına düşerse kapı KIRMIZI yanar.
# Sayı büyürse (yeni mutant eklenirse) taban da büyütülür — küçültmek MİMAR KARARIDIR.
# Bugünkü fiili kadro (19 Ağu 2026): mutant 12 (istemci) + 5 (drift) + 11 (W+S) +
# 12 (Y) + 2 (fail-closed) = 42 · kontrol 3 + 7 (W+S) + 7 (Y) + 2 (fail-closed) = 19.
MUTANT_TABANI = 42
KONTROL_TABANI = 19


def kabul_rc(dusen, olculemedi, kendini_test, mutant_gecti, mutant_toplam,
             kontrol_gecti, kontrol_toplam):
    """Ölçüm, batarya ve KAPSAM hükümlerini ayrı ayrı fail-closed uygular."""
    # `--kendini-test` muafiyeti fail-loud hükmünü fail-open'a çevirdi.
    # Ölçülemeyen eksen, test kolundan bağımsız olarak kırmızı kalmalıdır.
    kaynak_hatasi = dusen > 0 or olculemedi > 0
    batarya_hatasi = kendini_test and (
        mutant_gecti != mutant_toplam or kontrol_gecti != kontrol_toplam
    )
    # Oran değil SAYI ölçülür: 17/17 de "hepsi geçti"dir ve tam o yüzden yanıltıcıdır.
    kapsam_hatasi = kendini_test and (
        mutant_toplam < MUTANT_TABANI or kontrol_toplam < KONTROL_TABANI
    )
    return 1 if kaynak_hatasi or batarya_hatasi or kapsam_hatasi else 0


def fail_closed_kendini_testleri():
    """F1/F3 regresyon mutantlarını, F2/F4 ölçülebilirlik kontrollerini çalıştırır.

    Mutantlar yalnızca bu fonksiyonun bellek kopyasında çalışır; alt süreç veya gerçek
    kaynak yazımı yoktur, dolayısıyla kendini çağıran sonsuz döngü oluşmaz.
    """
    kaynak = inspect.getsource(kabul_rc)
    # Taban sayıları mutant ad alanına da girmeli (kapsam kolu onlara bakıyor).
    ortam = {"MUTANT_TABANI": MUTANT_TABANI, "KONTROL_TABANI": KONTROL_TABANI}
    tam = MUTANT_TABANI, MUTANT_TABANI, KONTROL_TABANI, KONTROL_TABANI

    def hukum_yukle(mutant_kaynak):
        ad_alani = {}
        exec(mutant_kaynak, dict(ortam), ad_alani)
        return ad_alani["kabul_rc"]

    # F1 — ÖLÇÜLEMEDİ ekseni `--kendini-test`te fail-open'a çevrilirse YAKALANMALI.
    f1_hukum = hukum_yukle(degistir(
        kaynak,
        [("dusen > 0 or olculemedi > 0",
          "dusen > 0 or (olculemedi > 0 and not kendini_test)")],
        "F1",
    ))
    beklenen_rc = 1
    gercek_rc = kabul_rc(0, 4, True, *tam)
    mutant_rc = f1_hukum(0, 4, True, *tam)
    f1_ok = gercek_rc == beklenen_rc and mutant_rc == 0
    print("F1 %s beklenen_rc=%d gerçek_rc=%d mutant_rc=%d FAIL-OPEN=%s" % (
        "OLDU" if f1_ok else "OLMADI", beklenen_rc, gercek_rc, mutant_rc,
        "YAKALANDI" if f1_ok else "KAYDI",
    ))

    f2_rc = kabul_rc(0, 0, True, *tam)
    f2_ok = f2_rc == 0
    print("F2 %s beklenen_rc=0 gözlenen_rc=%d OLCULEMEDI=0 taban=%d/%d" % (
        "OLDU" if f2_ok else "OLMADI", f2_rc, MUTANT_TABANI, KONTROL_TABANI,
    ))

    # F3 — KAPSAM kolu sökülürse YAKALANMALI: batarya 1/1'e düşse bile 'hepsi geçti'
    # diyerek yeşil dönmek, 19 Ağu'da 21 mutantı sessizce yakan halin ta kendisidir.
    f3_hukum = hukum_yukle(degistir(
        kaynak,
        [("mutant_toplam < MUTANT_TABANI or kontrol_toplam < KONTROL_TABANI",
          "False")],
        "F3",
    ))
    f3_gercek = kabul_rc(0, 0, True, 1, 1, 1, 1)
    f3_mutant = f3_hukum(0, 0, True, 1, 1, 1, 1)
    f3_ok = f3_gercek == 1 and f3_mutant == 0
    print("F3 %s [kapsam kolu söküldü] beklenen_rc=1 gerçek_rc=%d mutant_rc=%d "
          "KAPSAM-KAYBI=%s" % (
              "OLDU" if f3_ok else "OLMADI", f3_gercek, f3_mutant,
              "YAKALANDI" if f3_ok else "KAYDI",
          ))

    # F4 — KANARYA: taban KARŞILANDIĞINDA kapsam kolu kimseyi kırmızıya yakmamalı
    # (yoksa kol 'her zaman kırmızı' olur ve hiçbir şey ölçmez).
    f4_ok = kabul_rc(0, 0, True, MUTANT_TABANI + 5, MUTANT_TABANI + 5,
                     KONTROL_TABANI + 5, KONTROL_TABANI + 5) == 0
    print("F4 %s [taban aşıldı] beklenen_rc=0 KANARYA=%s" % (
        "OLDU" if f4_ok else "OLMADI", "TEMIZ" if f4_ok else "SAHTE-KIRMIZI",
    ))
    return f1_ok, f2_ok, f3_ok, f4_ok


def mutasyonlar(index_kaynak, worker_kaynak):
    honeypot = '''  if (govde.website !== undefined && govde.website !== "") {
    return { ok: false, sebep: "HONEYPOT" };
  }
'''
    zorunlu = '''    if (tanim.zorunlu && !kayit[alan]) {
      return { ok: false, sebep: "ZORUNLU_ALAN" };
    }
'''
    hiz_once = '''  const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";
  if (talepHizAsildi(ip)) return talepRed(env, 429);

'''
    dogrulama_satiri = '''  const dogrulama = talepDogrula(govde);
  if (!dogrulama.ok) return talepRed(env);'''
    hiz_sonra = hiz_once.rstrip("\n")
    adim1 = '''    if(adim === 1){
      var kategori = talepMetin(durum.kategori);
      return CATEGORIES.indexOf(kategori) !== -1 && GIZLI_KATEGORILER.indexOf(kategori) === -1 &&
        talepAlanGecerli("kategori", kategori);
    }'''
    adim5 = '    if(adim === 5){ return talepAlanGecerli("notu", durum.notu) && !talepDolu(durum.website); }'
    wa_not = '      "Not: " + talepMetin(durum.notu)'
    wa_link = 'href="https://wa.me/905451386526" target="_blank" rel="noopener">WhatsApp üzerinden fotoğraf ilet'
    cta_wa_link = 'href="https://wa.me/905451386526?text=Merhaba%2C%20arad%C4%B1%C4%9F%C4%B1m%20bir%20yedek%20par%C3%A7a%20var.%20%C3%9Cretebilir%20misiniz%3F"'
    base = [
        ("M1", {"worker": [(honeypot, "")]}, {16}),
        ("M2", {"index": [(adim1, "    if(adim === 1){ return true; }")]}, {1, 3, 4}),
        ("M3", {"index": [(adim5, '    if(adim === 5){ return talepAlanGecerli("notu", durum.notu); }')]}, {10}),
        ("M4", {"index": [(wa_not, wa_not + ',\n      "ad: " + talepMetin(durum.notu)')]}, {14}),
        ("M5", {"index": [(SIHIRBAZ_MARKUP_START, SIHIRBAZ_MARKUP_START + '\n<input type="file">')]}, {21}),
        ("M6", {"index": [(SIHIRBAZ_MARKUP_START, SIHIRBAZ_MARKUP_START + '\n<p>3D baskı</p>')]}, {23}),
        ("M7", {"index": [(SIHIRBAZ_JS_START, '  if(false){ var CATEGORIES = ["mutant"]; }\n' + SIHIRBAZ_JS_START)]}, {22}),
        ("M8", {"worker": [(zorunlu, "")]}, {15, 37}),
        ("M9", {"index": [(wa_link, wa_link.replace("905451386526", "905325954005"))]}, {25}),
        ("M10", {"worker": [(hiz_once, ""), (dogrulama_satiri, dogrulama_satiri + "\n\n" + hiz_sonra)]}, {28}),
        ("M11", {"index": [(SIHIRBAZ_MARKUP_START, SIHIRBAZ_MARKUP_START + '\n<span>Fethiye</span>')]}, {24}),
        ("M12", {"index": [(SIHIRBAZ_CSS_START, SIHIRBAZ_CSS_START + '\n  .talep-panel{background:url(https://kotu.example/x.png)}')]}, {27}),
        ("M13", {"index": [(cta_wa_link, cta_wa_link.replace("905451386526", "905325954005"))]}, {25}),
        ("M14", {"index": [(SIHIRBAZ_MARKUP_START, "")]}, {29, 30}),
        ("M15", {"index": [("parca_adi: talepMetin(durum.parca_adi)", "parca: talepMetin(durum.parca_adi)")]}, {13, 31, 35}),
        ("M16", {"fields": [("parca_adi: { tavan: 120, zorunlu: true }", "parca_adi: { tavan: 200, zorunlu: true }")]}, {18, 34, 38}),
        ("M17", {"worker": [('return json({ hata: "gecersiz", wa: TALEP_WA }, kod || 400, env);', 'return json({ hata: "gecersiz", sebep: "X", wa: TALEP_WA }, kod || 400, env);')]}, {37}),
        ("M18", {"worker": [('if (origin !== "https://pruvo3d.com") return false;', 'if (false) return false;')]}, {32}),
        ("M19", {"worker": [('''    if (!tanim.honeypot && kayit[alan].length > tanim.tavan) {
      return { ok: false, sebep: "ALAN_TAVANI" };
    }''', '''    if (!tanim.honeypot && kayit[alan].length > tanim.tavan) {
      kayit[alan] = kayit[alan].slice(0, tanim.tavan);
    }''')]}, {18, 38}),
    ]
    return base


# ---- MANIFESTO MUTASYON YARDIMCILARI ----------------------------------------
# 🔴 Bu mutantlar aracın ÜRETİM fonksiyonundan (`topla()`) geçer; izole bir kopyada
# koşmazlar. Manifesto `topla()`'nın parametresi olduğu için mutant, gerçek gövdenin
# ta kendisini sürer ([[ad-iki-rolde-mutanti-golgeler]]).
def manifesto_adim_dusur(manifesto, tur):
    """Verilen TÜRDEKİ adımı manifestodan düşürür (çapa 1 -> 0)."""
    yeni = tuple(adim for adim in manifesto if adim.tur != tur)
    if len(yeni) == len(manifesto):
        raise RuntimeError("manifestoda %s adımı yok" % tur)
    return yeni


def manifesto_adim_ikizle(manifesto, tur):
    """Verilen TÜRDEKİ adımı ikizler (çapa 1 -> 2)."""
    yeni = []
    for adim in manifesto:
        yeni.append(adim)
        if adim.tur == tur:
            yeni.append(adim)
    if len(yeni) == len(manifesto):
        raise RuntimeError("manifestoda %s adımı yok" % tur)
    return tuple(yeni)


def manifesto_turu_degistir(manifesto, eski_tur, yeni_tur):
    """Adımın TÜRÜNÜ değiştirir (ör. `mkdir` -> `mkdir -p`)."""
    yeni = tuple(adim._replace(tur=yeni_tur) if adim.tur == eski_tur else adim
                 for adim in manifesto)
    if yeni == manifesto:
        raise RuntimeError("manifestoda %s adımı yok" % eski_tur)
    return yeni


def manifesto_kaynak_dusur(manifesto, kaynak):
    """Adımın KAYNAK listesinden tek bir yolu düşürür (aracın kendi yardımcısı)."""
    return yayin_araci()._manifestten_cikar(manifesto, kaynak)


def _bozan_site_onceden_var(arac, kok):
    os.mkdir(arac._tam(kok, arac.SITE))


def _bozan_varlik_dizini_bosalt(arac, kok):
    for ad in os.listdir(arac._tam(kok, "varlik")):
        os.remove(arac._tam(kok, "varlik/" + ad))


def _bozan_yeni_varlik_ekle(arac, kok):
    """Beyaz listeye YENİ bir JS eklenince yayına KENDİLİĞİNDEN girmeli (elle liste yok)."""
    kalan = list(arac.FIKSTUR_VARLIKLARI) + ["jenerator/yeni-varlik.js"]
    with open(arac._tam(kok, "_yayin/jenerator/yeni-varlik.js"), "w",
              encoding="utf-8") as f:
        f.write("// yeni\n")
    with open(arac._tam(kok, arac.VARLIK_MANIFESTI), "w", encoding="utf-8") as f:
        f.write("\n".join(kalan) + "\n")
    with open(arac._tam(kok, "tools/build.py"), "w", encoding="utf-8") as f:
        f.write("SOYULACAK_JS = (\n%s)\n" % "".join("    %r,\n" % r for r in kalan))


def _bozan_manifest_sirasi_ters(arac, kok):
    kalan = list(reversed(arac.FIKSTUR_VARLIKLARI))
    with open(arac._tam(kok, arac.VARLIK_MANIFESTI), "w", encoding="utf-8") as f:
        f.write("\n".join(kalan) + "\n")


def _bozan_alakasiz_kok_dosyasi(arac, kok):
    """Beyaz listede OLMAYAN kök dosyası: yayına SIZMAMALI (`_site` ağacı değişmez)."""
    with open(arac._tam(kok, "NOT-OKU.txt"), "w", encoding="utf-8") as f:
        f.write("beyaz listede yok\n")


def _bozan_icerik_manifest_bos_satir(arac, kok):
    """İçerik manifestinde SON boş satır: kabuk `read` semantiği — atlanmalı."""
    with open(arac._tam(kok, arac.ICERIK_MANIFESTI), "w", encoding="utf-8") as f:
        f.write("sss\nmarka\nkategori\n\n")


def arac_manifesto_ile(arac, manifesto):
    """Aynı aracın MANIFESTO'su değiştirilmiş görünümü (kaynak dosya YAZILMAZ)."""
    alan = dict(vars(arac))
    alan["MANIFESTO"] = manifesto
    return types.SimpleNamespace(**alan)


def manifesto_kaynak_sirasi_ters(manifesto, tur="DOSYALAR"):
    """Zararsız mutasyon: adımın kaynak SIRASI ters — çıktı ağacı DEĞİŞMEMELİ."""
    return tuple(
        adim._replace(kaynaklar=tuple(reversed(adim.kaynaklar)))
        if adim.tur == tur else adim
        for adim in manifesto
    )


def _yayin_y_vakasi(arac, ad, aciklama, manifesto=None, bozan=None,
                    beklenen_rc=1, beklenen_parca=None, beklenen_esdegerlik=None,
                    beklenen_varlik=None, beklenen_yol=None):
    """Tek Y vakası: aracı fikstürde koştur, beklenen hükümle karşılaştır, BAS."""
    sonuc = yayin_fiksturunde_kos(arac, manifesto=manifesto, bozan=bozan)
    esdeg = arac._esdegerlik_hatalari(sonuc["ozet"]) if sonuc["rc"] == 0 else []
    oldu = sonuc["rc"] == beklenen_rc
    if oldu and beklenen_parca is not None:
        oldu = beklenen_parca in sonuc["hata"]
    if oldu and beklenen_esdegerlik == "BOZUK":
        oldu = bool(esdeg)
    if oldu and beklenen_esdegerlik == "TEMIZ":
        oldu = not esdeg
    if oldu and beklenen_varlik is not None:
        oldu = sonuc["varlik"] == beklenen_varlik
    if oldu and beklenen_yol is not None:
        oldu = sonuc["ozet"] is not None and beklenen_yol in sonuc["ozet"]
    print("%s %s [%s] beklenen=rc%d/esdeg-%s/varlik-%s "
          "gözlenen=rc%d/esdeg%d/varlik%d hata=%r" % (
              ad, "OLDU" if oldu else "OLMADI", aciklama, beklenen_rc,
              beklenen_esdegerlik or "?", beklenen_varlik if beklenen_varlik is not None else "?",
              sonuc["rc"], len(esdeg), sonuc["varlik"], sonuc["hata"][:110]))
    return oldu


def yayin_kopya_kendini_testleri(deploy_kaynak, nobet_kaynak, build_kaynak,
                                 fields_kaynak):
    """GRUP Y — `tools/yayin-topla.py`'nin DAVRANIŞI (metin DEĞİL, koşum).

    🔴 HEDEF-KOL ATFI İKİ KOŞUMLUDUR: "kol söküldü" mutantları, aynı arızada TEMİZ
    manifestonun KIRMIZI verdiği (`yayin_davranisi_olc`) yerde YEŞİL beklenir. Yalnız
    "mutantta kırmızı" demek kolu değil ambiyansı ölçerdi ([[ad-iki-rolde-mutanti-golgeler]]).

    ⚠️ İKİNCİ TANIM ÜRETİLMEZ: fikstür ve beklenen ağaç aracın KENDİ tanımlarıdır
    (`_fikstur_kur`, `_esdegerlik_hatalari`); burada yalnız aracın kendi bataryasında
    OLMAYAN mutantlar sürülür (kol sökme + hedef-kol atfı).
    """
    arac = yayin_araci()
    M = arac.MANIFESTO
    varlik_sayisi = len(arac.FIKSTUR_VARLIKLARI)
    mutant_sonuclari = []
    kontrol_sonuclari = []
    baseline_varlik = varlik_paritesi_olc(deploy_kaynak, nobet_kaynak, build_kaynak, arac)
    baseline_drift = talep_drift_olc(fields_kaynak)
    print("Y-TABAN: VARLIK_PARITESI=%s DEGER_PARITESI=%s IKINCI_TANIM=%s varlık=%d" % (
        baseline_varlik["parite"], baseline_drift["deger_paritesi"],
        baseline_drift["ikinci_tanim"], varlik_sayisi))

    # ---- MUTANTLAR --------------------------------------------------------
    # 🔴 MANIFESTO LAZY KURULUR VE HER VAKA AYRI SARILIR. Sebebi bu chip'in kendisi:
    # 19 Ağu'da tek bir çapa istisnası bataryayı ortasından kesti ve geri kalan
    # mutantlar SESSİZCE koşmadı. Artık bir vaka patlarsa YALNIZ O VAKA düşer,
    # sayıya `False` olarak girer ve toplam KÜÇÜLMEZ ([[kapatmadan-gecme-dongusu]]).
    y_mutantlari = [
        # (ad, açıklama, manifesto üreteci, bozan, beklentiler)
        ("Y-M1", "VARLIK_KOPYA adımı düşürüldü",
         lambda: manifesto_adim_dusur(M, "VARLIK_KOPYA"), None,
         {"beklenen_rc": 1, "beklenen_parca": "yayin varligi yok/bos"}),
        ("Y-M2", "VARLIK_KOPYA + iki kontrol kolu düşürüldü -> JS'ler _site'te YOK",
         lambda: manifesto_adim_dusur(manifesto_adim_dusur(
             manifesto_adim_dusur(M, "VARLIK_KOPYA"), "VARLIK_DOGRULA"), "KRITIK_VARLIK"),
         None, {"beklenen_rc": 0, "beklenen_esdegerlik": "BOZUK"}),
        ("Y-M3", "VARLIK_DOGRULA düşürüldü + varlık BOŞ kopyalandı -> sessiz geçer",
         lambda: manifesto_adim_dusur(M, "VARLIK_DOGRULA"), _bozan_varlik_bos,
         {"beklenen_rc": 0}),
        ("Y-M4", "KRITIK_VARLIK düşürüldü + hacim.js beyaz listeden düştü",
         lambda: manifesto_adim_dusur(M, "KRITIK_VARLIK"), _bozan_kritik_dusur,
         {"beklenen_rc": 0}),
        ("Y-M5", "DIZIN_KUR -> DIZIN_KUR_P (mkdir -p) + _site ZATEN VAR",
         lambda: manifesto_turu_degistir(M, "DIZIN_KUR", "DIZIN_KUR_P"),
         _bozan_site_onceden_var, {"beklenen_rc": 0}),
        ("Y-M6", "DIZIN_DOLU düşürüldü + varlik/ BOŞ -> çıplak sayfa sessiz geçer",
         lambda: manifesto_adim_dusur(M, "DIZIN_DOLU"), _bozan_varlik_dizini_bosalt,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "BOZUK"}),
        ("Y-M7", "MANIFEST_DONGU düşürüldü -> içerik/yasal sayfalar yayına girmez",
         lambda: manifesto_adim_dusur(M, "MANIFEST_DONGU"), None,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "BOZUK"}),
        ("Y-M8", "AGAC(urun) düşürüldü -> ürün sayfaları yayına girmez",
         lambda: manifesto_kaynak_dusur(M, "urun"), None,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "BOZUK"}),
        ("Y-M9", "DOSYALAR'dan ozet.json düşürüldü",
         lambda: manifesto_kaynak_dusur(M, "ozet.json"), None,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "BOZUK"}),
        ("Y-M10", "DOSYA(index.built.html) düşürüldü -> ana sayfa yayına girmez",
         lambda: manifesto_kaynak_dusur(M, "index.built.html"), None,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "BOZUK"}),
    ]
    for ad, aciklama, uretec, bozan, beklentiler in y_mutantlari:
        try:
            mutant_sonuclari.append(_yayin_y_vakasi(
                arac, ad, aciklama, manifesto=uretec(), bozan=bozan, **beklentiler))
        except Exception as hata:
            mutant_sonuclari.append(False)
            print("%s OLMADI [%s] ÇAPA/KURULUM HATASI=%s" % (ad, aciklama, hata))

    # Y-M11 — ÇAPA MUTANTI: manifesto çapası ikizlenirse ölçüm OLCULEMEDI demeli ve
    # VAKA 36 DÜŞMELİ. `count==1` iddiası budur; sessizce "ilkini alırım" DEMEZ.
    try:
        capa_arac = arac_manifesto_ile(arac, manifesto_adim_ikizle(M, "VARLIK_DOGRULA"))
        capa_davranis = yayin_davranisi_olc(capa_arac)
        capa_vaka = yayin_yolu_vakasi(oku(INDEX), deploy_kaynak, nobet_kaynak,
                                      build_kaynak, capa_arac)[0]
        capa_ok = (
            capa_davranis["kopya_kolu"] == "OLCULEMEDI" and
            capa_davranis["sebep"].startswith("ÇAPA") and capa_vaka is False
        )
        print("Y-M11 %s [VARLIK_DOGRULA çapası İKİZLENDİ] beklenen=OLCULEMEDI/"
              "VAKA36-DUSTU gözlenen=%s/VAKA36-%s sebep=%r" % (
                  "OLDU" if capa_ok else "OLMADI", capa_davranis["kopya_kolu"],
                  "GECTI" if capa_vaka else "DUSTU", capa_davranis["sebep"][:80]))
    except Exception as hata:
        capa_ok = False
        print("Y-M11 OLMADI [çapa ikizleme] hata=%s" % hata)
    mutant_sonuclari.append(capa_ok)

    # Y-M12 — KAYNAK MUTANTI (spec §2 NEGATİF VAKA): aracın kopya kolunun GERÇEK
    # gövdesi bozulursa VAKA 36 HÂLÂ KIRMIZI olmalı. Mutasyon yalnız bellekte;
    # `tools/yayin-topla.py` diske YAZILMAZ (sha nöbeti bunu ayrıca ölçer).
    try:
        mutant_kaynak = degistir(
            YAYIN_TOPLA.read_text(encoding="utf-8"),
            [("        _dosya_kopyala(kok, kaynak, hedef)\n        kopyalanan += 1\n",
              "        kopyalanan += 1\n")],
            "Y-M12",
        )
        bozuk_arac = yayin_araci(mutant_kaynak)
        bozuk_davranis = yayin_davranisi_olc(bozuk_arac)
        bozuk_vaka = yayin_yolu_vakasi(oku(INDEX), deploy_kaynak, nobet_kaynak,
                                       build_kaynak, bozuk_arac)[0]
        bozuk_ok = (
            bozuk_davranis["kopya_kolu"] == "KIRIK" and bozuk_vaka is False
        )
        print("Y-M12 %s [_varlik_kopya GÖVDESİ bozuldu: cp kolu söküldü] "
              "beklenen=KOPYA_KOLU-KIRIK/VAKA36-DUSTU gözlenen=%s/VAKA36-%s" % (
                  "OLDU" if bozuk_ok else "OLMADI", bozuk_davranis["kopya_kolu"],
                  "GECTI" if bozuk_vaka else "DUSTU"))
    except Exception as hata:
        bozuk_ok = False
        print("Y-M12 OLMADI hata=%s" % hata)
    mutant_sonuclari.append(bozuk_ok)

    # ---- KONTROLLER (zararsız değişim -> hüküm DEĞİŞMEZ) ------------------
    y_kontrolleri = [
        ("Y-K1", "temiz manifesto + temiz fikstür", None, None,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "TEMIZ",
          "beklenen_varlik": varlik_sayisi}),
        ("Y-K2", "DOSYALAR kaynak SIRASI ters",
         lambda: manifesto_kaynak_sirasi_ters(M), None,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "TEMIZ",
          "beklenen_varlik": varlik_sayisi}),
        ("Y-K3", "beyaz listede OLMAYAN kök dosyası -> yayına SIZMAZ",
         None, _bozan_alakasiz_kok_dosyasi,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "TEMIZ",
          "beklenen_varlik": varlik_sayisi}),
        ("Y-K4", "varlık manifesti satır SIRASI ters",
         None, _bozan_manifest_sirasi_ters,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "TEMIZ",
          "beklenen_varlik": varlik_sayisi}),
        ("Y-K5", "içerik manifestinde SON boş satır (kabuk `read` semantiği)",
         None, _bozan_icerik_manifest_bos_satir,
         {"beklenen_rc": 0, "beklenen_esdegerlik": "TEMIZ",
          "beklenen_varlik": varlik_sayisi}),
        ("Y-K6", "beyaz listeye YENİ varlık -> elle liste tutmadan yayına girer",
         None, _bozan_yeni_varlik_ekle,
         {"beklenen_rc": 0, "beklenen_varlik": varlik_sayisi + 1,
          "beklenen_yol": "jenerator/yeni-varlik.js"}),
    ]
    for ad, aciklama, uretec, bozan, beklentiler in y_kontrolleri:
        try:
            kontrol_sonuclari.append(_yayin_y_vakasi(
                arac, ad, aciklama, manifesto=uretec() if uretec else None,
                bozan=bozan, **beklentiler))
        except Exception as hata:
            kontrol_sonuclari.append(False)
            print("%s OLMADI [%s] ÇAPA/KURULUM HATASI=%s" % (ad, aciklama, hata))

    # Y-K7: TEK KAYNAĞIN KENDİ BATARYASI CANLI MI. Bu bir delegasyondur, ikinci tanım
    # değil: aracın `kendini_test()`i ve tautoloji kanaryası (`_mutasyon_kontrol`)
    # yeşil değilse buradaki "davranış TAMAM" hükmü dayanaksız kalır.
    try:
        oz_hatalar, oz_iddia = arac.kendini_test()
        oz_mutasyon, _ = arac._mutasyon_kontrol()
        oz_ok = not oz_hatalar and not oz_mutasyon
        print("Y-K7 %s [araç öz-testi] iddia=%d hata=%d mutasyon_hatasi=%d" % (
            "OLDU" if oz_ok else "OLMADI", oz_iddia, len(oz_hatalar), len(oz_mutasyon)))
        if not oz_ok:
            for h in (oz_hatalar + oz_mutasyon)[:5]:
                print("  ! %s" % h)
    except Exception as hata:
        oz_ok = False
        print("Y-K7 OLMADI [araç öz-testi] hata=%s" % hata)
    kontrol_sonuclari.append(oz_ok)
    return mutant_sonuclari, kontrol_sonuclari


# ---- WORKFLOW / BEYAZ LİSTE MUTASYON ÇAPALARI -------------------------------
YAYIN_ADIM_SATIRI = "      - name: Yayin klasorunu topla (beyaz liste)\n"
YAYIN_RUN_SATIRI = "        run: python3 tools/yayin-topla.py\n"
# Fork'un DİRİLDİĞİ hal: adım tek kaynağa gitmeye devam etse bile ikinci bir adım
# aynı işi kabukta yeniden yapıyor -> iki gövde ayrışır.
DIRILEN_FORK = (
    YAYIN_RUN_SATIRI +
    "      - name: Eski varlik kolu (diriltildi)\n"
    "        run: |\n"
    "          while IFS= read -r varlik; do\n"
    '            cp "_yayin/$varlik" "_site/$varlik"\n'
    "          done < _yayin/site-varliklari.txt\n"
)
SATIR_ICI_KABUK = (
    "        run: |\n"
    "          mkdir _site\n"
    "          cp index.built.html _site/index.html\n"
)


def yayin_mutasyonlari(index_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak, baseline):
    """GRUP W + S — delegasyon çapası, tek kaynak ve istemci dikişi mutantları.

    Hepsinin ortak iddiası: mutant VAKA 36'yı DÜŞÜRMELİ. Yani ölçüm yüzeyi artık
    taşıyıcının metni değil, 'yayına giden yol gerçekten kurulu mu' sorusudur."""
    referans_kumesi = soyulacak_js_kumesi(build_kaynak)
    build_talep = '                "talep-alanlari.js",\n'
    build_bas = 'SOYULACAK_JS = ("secenekler.js", "konfigur.js",\n'
    vakalar = [
        # --- GRUP W: workflow delegasyonu + tek kaynak ---------------------
        ("W-M1", [(YAYIN_RUN_SATIRI, "        run: python3 tools/yayin-topla-eski.py\n")],
         [], None, "deploy.yml başka betiğe delege ediyor"),
        ("W-M2", [], [(YAYIN_RUN_SATIRI, "        run: python3 tools/yayin-topla-eski.py\n")],
         None, "nobet.yml başka betiğe delege ediyor"),
        ("W-M3", [(YAYIN_RUN_SATIRI, SATIR_ICI_KABUK)], [], None,
         "deploy.yml satır-içi kabuğa döndü"),
        ("W-M4", [], [(YAYIN_RUN_SATIRI, SATIR_ICI_KABUK)], None,
         "nobet.yml satır-içi kabuğa döndü"),
        ("W-M5", [("      - name: Yayin klasorunu topla (beyaz liste)\n",
                   "      - name: Yayin klasorunu topla (beyaz liste ARTIK YOK)\n")],
         [], None, "deploy.yml adım çapası 0 (adım adı bozuldu)"),
        ("W-M6", [], [(YAYIN_ADIM_SATIRI, YAYIN_ADIM_SATIRI + YAYIN_ADIM_SATIRI)],
         None, "nobet.yml adım çapası 2 (adım İKİZLENDİ)"),
        ("W-M7", [(YAYIN_RUN_SATIRI, DIRILEN_FORK)], [], None,
         "deploy.yml'de satır-içi varlık kolu DİRİLDİ (fork)"),
        ("W-M8", [], [(YAYIN_RUN_SATIRI, DIRILEN_FORK)], None,
         "nobet.yml'de satır-içi varlık kolu DİRİLDİ (fork)"),
        # --- GRUP S: beyaz liste × istemci dikişi --------------------------
        ("S-M1", [], [], [(build_talep, "")],
         "SOYULACAK_JS'ten talep-alanlari.js düştü (index onu YÜKLÜYOR)"),
        ("S-M2", [], [], [(build_bas, 'SOYULACAK_JS = ("konfigur.js",\n')],
         "SOYULACAK_JS'ten secenekler.js düştü (index onu YÜKLÜYOR)"),
    ]
    for ad, deploy_degisimleri, nobet_degisimleri, build_degisimleri, aciklama in vakalar:
        try:
            md = degistir(deploy_kaynak, deploy_degisimleri, ad) if deploy_degisimleri else deploy_kaynak
            mn = degistir(nobet_kaynak, nobet_degisimleri, ad) if nobet_degisimleri else nobet_kaynak
            mb = degistir(build_kaynak, build_degisimleri, ad) if build_degisimleri else build_kaynak
            mutant, _, _, _ = yayin_yolu_vakasi(index_kaynak, md, mn, mb)
            olcum = varlik_paritesi_olc(md, mn, mb, referans_kumesi=referans_kumesi)
            dusenler = [36] if mutant != baseline else []
            oldu = (
                olcum["parite"] in ("SAPMA", "OLCULEMEDI") and olcum["rc"] == 1 and
                dusenler == [36]
            )
            print("%s %s [%s] beklenen=SAPMA rc=1 düşen=[36] gözlenen=%s rc=%d "
                  "düşen=%s fark=%s" % (
                      ad, "OLDU" if oldu else "OLMADI", aciklama, olcum["parite"],
                      olcum["rc"], dusenler, "; ".join(olcum["farklar"])[:160] or "YOK"))
        except Exception as hata:
            oldu = False
            print("%s OLMADI [%s] hata=%s" % (ad, aciklama, hata))
        yield oldu

    # S-M3 — FAIL-CLOSED: beyaz liste OKUNAMAZSA hüküm 'ölçülemedi' değil KIRMIZI olur.
    # Sentetik gövde kullanılır: gerçek metni bozmak sözdizimi hatası verirdi ve ölçtüğümüz
    # sınıf (sabit-olmayan atama) görünmezdi.
    try:
        dinamik_build = "SOYULACAK_JS = tuple(x for x in ())\n"
        mutant, _, _, _ = yayin_yolu_vakasi(
            index_kaynak, deploy_kaynak, nobet_kaynak, dinamik_build)
        olcum = varlik_paritesi_olc(deploy_kaynak, nobet_kaynak, dinamik_build)
        oldu = (olcum["parite"] == "OLCULEMEDI" and olcum["rc"] == 1 and
                mutant is False and mutant != baseline)
        print("S-M3 %s [SOYULACAK_JS sabit DEĞİL -> beyaz liste okunamaz] "
              "beklenen=OLCULEMEDI rc=1 VAKA36-DUSTU gözlenen=%s rc=%d VAKA36-%s" % (
                  "OLDU" if oldu else "OLMADI", olcum["parite"], olcum["rc"],
                  "GECTI" if mutant else "DUSTU"))
    except Exception as hata:
        oldu = False
        print("S-M3 OLMADI hata=%s" % hata)
    yield oldu


def yayin_kontrolleri(index_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak):
    """GRUP W + S kontrolleri: zararsız değişim hükmü DEĞİŞTİRMEMELİ."""
    sonuclar = []
    vakalar = [
        # ⚠️ Kontrol çapası ADIM SATIRIDIR, yorum metni DEĞİL: eski K-1/K-2 kontrolleri
        # `# Ana sayfa:` yorumuna çapalıydı ve K215 o yorumu `tools/yayin-topla.py`'ye
        # taşıdı — çapa iki workflow'da da 0'a düştü. Kontroller ölçtükleri yüzeye
        # çapalanır ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
        ("W-K1", "deploy.yml'de yayın adımının ÜSTÜNE zararsız yorum",
         [(YAYIN_ADIM_SATIRI, "      # kontrol yorumu (zararsiz)\n" + YAYIN_ADIM_SATIRI)],
         [], []),
        ("W-K2", "nobet.yml'de yayın adımının ÜSTÜNE zararsız yorum",
         [], [(YAYIN_ADIM_SATIRI, "      # kontrol yorumu (zararsiz)\n" + YAYIN_ADIM_SATIRI)],
         []),
        ("W-K3", "deploy.yml'de KOMŞU adımın adı değişti",
         [("      - name: Pages artefaktini yukle\n",
           "      - name: Pages artefaktini yukle (kontrol)\n")], [], []),
        ("W-K4", "nobet.yml'de KOMŞU adımın adı değişti",
         [], [("      - name: JSON-LD sku kabul testi (uretilen sayfalar + feed capraz-kontrol)\n",
               "      - name: JSON-LD sku kabul testi (kontrol)\n")], []),
        ("S-K1", "SOYULACAK_JS eleman SIRASI değişti (küme semantiği)",
         [], [], [('SOYULACAK_JS = ("secenekler.js", "konfigur.js",\n',
                   'SOYULACAK_JS = ("konfigur.js", "secenekler.js",\n')]),
        ("S-K3", "build.py'de SOYULACAK_JS üstüne yorum",
         [], [], [('SOYULACAK_JS = ("secenekler.js", "konfigur.js",\n',
                   '# kontrol yorumu\nSOYULACAK_JS = ("secenekler.js", "konfigur.js",\n')]),
    ]
    for ad, aciklama, dd, nd, bd in vakalar:
        try:
            md = degistir(deploy_kaynak, dd, ad) if dd else deploy_kaynak
            mn = degistir(nobet_kaynak, nd, ad) if nd else nobet_kaynak
            mb = degistir(build_kaynak, bd, ad) if bd else build_kaynak
            olcum = varlik_paritesi_olc(md, mn, mb)
            vaka = yayin_yolu_vakasi(index_kaynak, md, mn, mb)[0]
            ok = olcum["parite"] == "TAMAM" and olcum["rc"] == 0 and vaka is True
            print("%s %s [%s] beklenen=TAMAM/VAKA36-GECTI gözlenen=%s rc=%d VAKA36-%s "
                  "fark=%s" % (ad, "OLDU" if ok else "OLMADI", aciklama, olcum["parite"],
                               olcum["rc"], "GECTI" if vaka else "DUSTU",
                               "; ".join(olcum["farklar"])[:120] or "YOK"))
        except Exception as hata:
            ok = False
            print("%s OLMADI [%s] hata=%s" % (ad, aciklama, hata))
        sonuclar.append(ok)

    # S-K2 — istemci tarafı zararsız değişim: `?v=` önbellek-kırıcı sorgu eklenince
    # `yerel_script_kaynaklari` onu SOYMALI ve VAKA 36 yine GEÇMELİ.
    try:
        mi = degistir(
            index_kaynak,
            [('<script src="/talep-alanlari.js"></script>',
              '<script src="/talep-alanlari.js?v=abc123"></script>')],
            "S-K2",
        )
        vaka = yayin_yolu_vakasi(mi, deploy_kaynak, nobet_kaynak, build_kaynak)
        ok = vaka[0] is True and "talep-alanlari.js" in vaka[1]
        print("S-K2 %s [index'te `?v=` önbellek-kırıcı sorgu] beklenen=VAKA36-GECTI "
              "gözlenen=VAKA36-%s varlıklar=%s" % (
                  "OLDU" if ok else "OLMADI", "GECTI" if vaka[0] else "DUSTU",
                  ",".join(vaka[1]) or "YOK"))
    except Exception as hata:
        ok = False
        print("S-K2 OLMADI hata=%s" % hata)
    sonuclar.append(ok)
    return sonuclar


def controls(index_kaynak, worker_kaynak, baseline):
    k1 = degistir(index_kaynak, [(".talep-chip{background:#fff;", ".talep-chip{background:#fefefe;")], "K1")
    k2 = degistir(worker_kaynak, [
        ("  const gelen = Object.keys(govde);", "  const gelen = Object.keys(govde).slice();")
    ], "K2")
    k3 = degistir(index_kaynak, [(">Eksik Parça Talebi</button>", ">İlerle</button>")], "K3")
    fields_kaynak = oku(FIELDS)
    c1 = tum_vakalari(k1, worker_kaynak, fields_kaynak, False) == baseline
    c2 = tum_vakalari(index_kaynak, k2, fields_kaynak, False) == baseline
    c3 = tum_vakalari(k3, worker_kaynak, fields_kaynak, False) == baseline
    print("K1 %s: CSS renk mutasyonu sonrası tüm vakalar aynı" % ("GECTI" if c1 else "DUSTU"))
    print("K2 %s: yerel değişken adı mutasyonu sonrası tüm vakalar aynı" % ("GECTI" if c2 else "DUSTU"))
    print("K3 %s: markup görünür metin mutasyonu sonrası tüm vakalar aynı" % ("GECTI" if c3 else "DUSTU"))
    return [c1, c2, c3]


# NOT (19 Agu 2026, K184/VAKA36): eski `yayin_kontrolu` KALDIRILDI. Cagiran yoktu ve
# `yayin_yolu_vakasi`'nin ESKI 3 argumanli imzasini tasiyordu — cagrilsa TypeError verirdi.
# Ayni iddia artik `yayin_kontrolleri` icindeki W-K1/W-K2 kontrolleridir (canli, sayilan).


def mutasyonlar_v2(index_kaynak):
    adim1 = '''    if(adim === 1){
      var kategori = talepMetin(durum.kategori);
      return CATEGORIES.indexOf(kategori) !== -1 && GIZLI_KATEGORILER.indexOf(kategori) === -1 &&
        talepAlanGecerli("kategori", kategori);
    }'''
    adim5 = '    if(adim === 5){ return talepAlanGecerli("notu", durum.notu) && !talepDolu(durum.website); }'
    wa_not = '      "Not: " + talepMetin(durum.notu)'
    wa_link = 'href="https://wa.me/905451386526" target="_blank" rel="noopener">WhatsApp üzerinden fotoğraf ilet'
    cta_wa_link = 'href="https://wa.me/905451386526?text=Merhaba%2C%20arad%C4%B1%C4%9F%C4%B1m%20bir%20yedek%20par%C3%A7a%20var.%20%C3%9Cretebilir%20misiniz%3F"'
    return [
        ("M1", {"index": [(adim1, "    if(adim === 1){ return true; }")]}, {1, 3, 4}),
        ("M2", {"index": [(adim5, '    if(adim === 5){ return talepAlanGecerli("notu", durum.notu); }')]}, {10}),
        ("M3", {"index": [(wa_not, wa_not + ',\n      "ad: " + talepMetin(durum.notu)')]}, {14}),
        ("M4", {"index": [(SIHIRBAZ_MARKUP_START, SIHIRBAZ_MARKUP_START + '\n<input type="file">')]}, {19}),
        ("M5", {"index": [(SIHIRBAZ_MARKUP_START, SIHIRBAZ_MARKUP_START + '\n<p>3D baskı</p>')]}, {21}),
        ("M6", {"index": [(SIHIRBAZ_JS_START, '  if(false){ var CATEGORIES = ["mutant"]; }\n' + SIHIRBAZ_JS_START)]}, {20}),
        ("M7", {"index": [(wa_link, wa_link.replace("905451386526", "905325954005"))]}, {23}),
        ("M8", {"index": [(SIHIRBAZ_MARKUP_START, SIHIRBAZ_MARKUP_START + '\n<span>Fethiye</span>')]}, {22}),
        ("M9", {"index": [(SIHIRBAZ_CSS_START, SIHIRBAZ_CSS_START + '\n  .talep-panel{background:url(https://kotu.example/x.png)}')]}, {25}),
        ("M10", {"index": [(cta_wa_link, cta_wa_link.replace("905451386526", "905325954005"))]}, {23}),
        ("M11", {"index": [(SIHIRBAZ_MARKUP_START, "")]}, {26, 27}),
        # Alan adi degisince K186 ucu de REDDEDER (`parca` izinli anahtar degil) — vaka 16
        # K186 main'e inmeden ONCE olculemedigi icin beklenen kumede yoktu.
        ("M12", {"index": [("parca_adi: talepMetin(durum.parca_adi)", "parca: talepMetin(durum.parca_adi)")]}, {13, 16, 32}),
    ]


def drift_mutasyonlari(fields_kaynak):
    # K186'nın gerçek şekli burada yalnızca bellek fikstürü olarak taklit edilir;
    # shop/src/talep.js bu dalda yoktur ve hiçbir zaman diske yazılmaz.
    fikstur = """const GOVDE_BAYT_TAVANI = 4096;
export const ALAN_TAVANLARI = Object.freeze({
  kategori: 40,
  marka: 60,
  model: 60,
  yil: 20,
  parca_adi: 120,
  notu: 500,
});
"""
    mutantlar = [
        ("M-A", fikstur.replace("parca_adi: 120", "parca_adi: 130"), False, "SAPMA", "VAR", 1),
        ("M-B", fikstur.replace("  notu: 500,\n", ""), False, "SAPMA", "VAR", 1),
        ("M-C", fikstur, True, "TAMAM", "VAR", 1),
        ("M-D", 'import "../../talep-alanlari.js";\n', True, "OLCULEMEDI", "YOK", 0),
        ("M-E", fikstur.replace("parca_adi: 120", "parca_adi: 130"), True, "SAPMA", "VAR", 1),
    ]
    for ad, mutant_talep, ithal_indi, beklenen_deger, beklenen_ikinci, beklenen_rc in mutantlar:
        olcum = talep_drift_olc(fields_kaynak, mutant_talep, ithal_indi)
        gozlenen = "DEGER_PARITESI=%s IKINCI_TANIM=%s rc=%s" % (
            olcum["deger_paritesi"], olcum["ikinci_tanim"], olcum["rc"]
        )
        beklenen = "DEGER_PARITESI=%s IKINCI_TANIM=%s rc=%s" % (
            beklenen_deger, beklenen_ikinci, beklenen_rc
        )
        oldu = (
            olcum["deger_paritesi"] == beklenen_deger and
            olcum["ikinci_tanim"] == beklenen_ikinci and
            olcum["rc"] == beklenen_rc
        )
        if olcum["deger_paritesi"] == "SAPMA":
            fark = "; ".join(olcum["farklar"])
            print("%s %s beklenen=%s gözlenen=%s fark=%s" % (
                ad, "OLDU" if oldu else "OLMADI", beklenen, gozlenen, fark or "YOK"
            ))
        else:
            print("%s %s beklenen=%s gözlenen=%s" % (
                ad, "OLDU" if oldu else "OLMADI", beklenen, gozlenen
            ))
        yield oldu


def controls_v2(index_kaynak, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak, baseline):
    k1 = degistir(index_kaynak, [('.talep-chip{background:#fff;', '.talep-chip{background:#fefefe;')], "K1")
    k2 = degistir(index_kaynak, [('var SHOP_UC = "/api/shop";', 'var SHOP_UC = "/api/shop"; // kontrol')], "K2")
    k3 = degistir(index_kaynak, [(">Eksik Parça Talebi</button>", ">İlerle</button>")], "K3")
    kontroller = [
        tum_vakalari(k1, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak) == baseline,
        tum_vakalari(k2, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak) == baseline,
        tum_vakalari(k3, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak) == baseline,
    ]
    for ad, ok in zip(("K1", "K2", "K3"), kontroller):
        print("%s %s: zararsız mutasyon sonrası tüm vakalar aynı" % (ad, "GECTI" if ok else "DUSTU"))
    return kontroller


def main():
    once_self = sha(Path(__file__))
    once_index = sha(INDEX)
    once_fields = sha(FIELDS)
    once_deploy = sha(DEPLOY)
    once_nobet = sha(NOBET)
    once_build = sha(BUILD)
    once_yayin = sha(YAYIN_TOPLA)
    index_kaynak = oku(INDEX)
    fields_kaynak = oku(FIELDS)
    deploy_kaynak = oku(DEPLOY)
    nobet_kaynak = oku(NOBET)
    build_kaynak = oku(BUILD)
    mutant_gecti = 0
    mutant_toplam = 0
    kontrol_gecti = 0
    kontrol_toplam = 0
    dusen = 0
    olculemedi = 0
    deger_paritesi = "OLCULEMEDI"
    ikinci_tanim = "OLCULEMEDI"
    baseline = {}
    try:
        baseline, dusen, olculemedi, deger_paritesi, ikinci_tanim = normal_kos(
            index_kaynak, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak
        )
        if "--kendini-test" in sys.argv:
            for ad, hedefler, beklenen in mutasyonlar_v2(index_kaynak):
                mutant_toplam += 1
                mi = degistir(index_kaynak, hedefler.get("index", []), ad)
                try:
                    mutant = tum_vakalari(mi, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak)
                    dusenler = sorted(num for num in baseline if baseline[num] is not None and mutant[num] != baseline[num])
                    beklenen_karsilandi = beklenen.issubset(set(dusenler))
                    beklenmeyen = set(dusenler) - beklenen
                    oldu = beklenen_karsilandi and not beklenmeyen
                    if oldu:
                        mutant_gecti += 1
                    print("%s %s beklenen=%s düşen=%s" % (ad, "OLDU" if oldu else "YASADI", sorted(beklenen), dusenler))
                except Exception as hata:
                    print("%s YASADI beklenen=%s hata=%s" % (ad, sorted(beklenen), hata))
            drift_sonuclari = list(drift_mutasyonlari(fields_kaynak))
            mutant_toplam += len(drift_sonuclari)
            mutant_gecti += sum(1 for ok in drift_sonuclari if ok)
            kontroller = controls_v2(
                index_kaynak, fields_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak, baseline
            )
            kontrol_toplam = len(kontroller)
            kontrol_gecti = sum(1 for ok in kontroller if ok)
            yayin_baseline = yayin_yolu_vakasi(
                index_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak
            )[0]
            yayin_mutant_sonuclari = list(yayin_mutasyonlari(
                index_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak, yayin_baseline
            ))
            mutant_toplam += len(yayin_mutant_sonuclari)
            mutant_gecti += sum(1 for ok in yayin_mutant_sonuclari if ok)
            yayin_kontrol_sonuclari = yayin_kontrolleri(
                index_kaynak, deploy_kaynak, nobet_kaynak, build_kaynak)
            kontrol_toplam += len(yayin_kontrol_sonuclari)
            kontrol_gecti += sum(1 for ok in yayin_kontrol_sonuclari if ok)
            kopya_mutant_sonuclari, kopya_kontrol_sonuclari = yayin_kopya_kendini_testleri(
                deploy_kaynak, nobet_kaynak, build_kaynak, fields_kaynak
            )
            mutant_toplam += len(kopya_mutant_sonuclari)
            mutant_gecti += sum(1 for ok in kopya_mutant_sonuclari if ok)
            kontrol_toplam += len(kopya_kontrol_sonuclari)
            kontrol_gecti += sum(1 for ok in kopya_kontrol_sonuclari if ok)
            f1_ok, f2_ok, f3_ok, f4_ok = fail_closed_kendini_testleri()
            mutant_toplam += 2
            mutant_gecti += int(f1_ok) + int(f3_ok)
            kontrol_toplam += 2
            kontrol_gecti += int(f2_ok) + int(f4_ok)
    except Exception as hata:
        print("KABUL HATASI: %s" % hata)
        dusen = max(dusen, 1)
    finally:
        sonra_self = sha(Path(__file__))
        sonra_index = sha(INDEX)
        sonra_fields = sha(FIELDS)
        sonra_deploy = sha(DEPLOY)
        sonra_nobet = sha(NOBET)
        sonra_build = sha(BUILD)
        sonra_yayin = sha(YAYIN_TOPLA)
        if (once_self != sonra_self or once_index != sonra_index or once_fields != sonra_fields or
                once_deploy != sonra_deploy or once_nobet != sonra_nobet or
                once_build != sonra_build or once_yayin != sonra_yayin):
            print("KAYNAK SHA DEĞİŞTİ: test fail-closed")
            dusen = max(dusen, 1)
        print("SHA talep-sihirbazi-test.py %s -> %s" % (once_self, sonra_self))
        print("SHA index %s -> %s" % (once_index, sonra_index))
        print("SHA talep-alanlari %s -> %s" % (once_fields, sonra_fields))
        print("SHA deploy.yml %s -> %s" % (once_deploy, sonra_deploy))
        print("SHA nobet.yml %s -> %s" % (once_nobet, sonra_nobet))
        print("SHA build.py %s -> %s" % (once_build, sonra_build))
        print("SHA yayin-topla.py %s -> %s" % (once_yayin, sonra_yayin))
        print("Tek kaynak: talep-alanlari.js tanım sayısı=1 istemci çıplak tavan sayısı=0")
        print("VAKA=%d DUSEN=%d OLCULEMEDI=%d DEGER_PARITESI=%s IKINCI_TANIM=%s MUTANT=%d/%d KONTROL=%d/%d" % (
            len(baseline), dusen, olculemedi, deger_paritesi, ikinci_tanim,
            mutant_gecti, mutant_toplam, kontrol_gecti, kontrol_toplam
        ))
    return kabul_rc(
        dusen, olculemedi, "--kendini-test" in sys.argv,
        mutant_gecti, mutant_toplam, kontrol_gecti, kontrol_toplam,
    )


if __name__ == "__main__":
    sys.exit(main())
