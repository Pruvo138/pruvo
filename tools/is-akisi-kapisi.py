#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/is-akisi-kapisi.py — IS AKISI BICIM KAPISI + CAGRI/ETKISIZLESTIRME NOBETLERI.

NEDEN VAR (29-30 Tem, GERCEK HASAR OLCULDU): deploy.yml'e eklenen bir adim ADI
TIRNAKSIZ yazildi ve icinde ": " (iki nokta + BOSLUK) tasiyordu:

    - name: Iki govde eslem kapisi (2-renk: -D farki yalniz Output)

YAML plain scalar'da bu bir AYRISTIRMA HATASIDIR. Sonuc: GitHub "workflow file issue"
deyip isi HIC baslatmadi -> kosum 0 saniyede `startup_failure`, is sayisi 0. Yani
`urun/` uretimi, sitemap, **butun kapilar** ve Pages yayini KOSMADI; ~7 dakika TUM
EKIBIN yayini durdu. Onarim: b7e9f845 (adi tirnaklandi), kosum 30492882992 SUCCESS.

🔴 HICBIR KAPI YAKALAMADI. Sebep: `tools/ci-kapsam-test.py` (ve `paket-tazelik-kapisi.py`)
is akisi dosyalarinda **METIN arar, YAML AYRISTIRMAZ** — yani "kapi var" sanilan yerde
bu sinif icin koruma YOKTU. Bu dosya o bosluga GERCEK bir ayristirici koyar.

ISLER (iki bolum, ayri eksenler):

  BOLUM A — BICIM: `.github/workflows/*.yml|*.yaml` altindaki TUM dosyalar GERCEK bir
    YAML ayristiricisiyla (PyYAML) ayristirilir. Ayristirma hatasi = KIRMIZI. Ek olarak
    `startup_failure` ureten BILINEN tuzaklar olculur:
      A1 ayristirma hatasi (tirnaksiz `": "`, kapanmamis tirnak, TAB, bozuk girinti...)
      A2 TEKRARLANAN ANAHTAR (PyYAML'in KENDISI bunu SESSIZCE yer: son deger kazanir;
         GitHub ise "workflow file issue" verir -> ozel Loader ile yakalanir)
      A3 govde yapisi: kok mapping · `on:` VAR · `jobs:` VAR + mapping + BOS DEGIL
      A4 job yapisi: mapping · (`runs-on` VEYA `uses`) · `steps` liste + bos degil
      A5 step yapisi: mapping · (`uses` VEYA `run`) · `run` BOS DEGIL

  BOLUM B — CAGRI NOBETI: `onizleme/test/iki-govde-olcum.py` GERCEKTEN kosuyor mu.
    Olculen delik (mimar, 30 Tem): bu testin `onizleme-imaj.yml`'deki cagri satiri
    NOBETSIZDI — cagriyi sil / yoruma al / `|| true` ekle -> DORT denetci de rc=0.
    `ci-kapsam-test.py` bu dosyayi "muaf" tutuyor ve muafiyet gerekcesi cagri satirinin
    "paket-tazelik-kapisi.py'nin imaj-akisi nobetiyle ayni dosyada durdugunu" soyluyordu;
    OLCULDU: paket-tazelik-kapisi.py'nin `CAGRI_CAPASI` sabiti YALNIZ KENDI cagri
    satirini ("tools/paket-tazelik-kapisi.py --paket") izliyor -> iddia YANLISTI.

  BOLUM D — KAPI ADIMI ETKISIZLESTIRME NOBETI (30 Tem, TUM 43 KAPIYI ILGILENDIREN
    SISTEMIK DELIK): `ci-kapsam-test.py` bir kabul testinin CI adiminin SILINMESINI /
    YORUMA ALINMASINI yakalar, ama adima `continue-on-error: true` ya da komuta
    `|| true` EKLENMESINI YAKALAMAZ. Yani "CI'da VAR" ile "CI'da BLOKLAR" ayni sey
    DEGILDI; herhangi bir kapi TEK SATIRLA, sessizce etkisizlestirilebiliyordu ve
    hicbir nobetci konusmuyordu.
    OLCULDU (30 Tem, gecici kopyada — canli deploy.yml'e mutasyon UYGULANMADI): 6 ayri
    kapi adimina (kisisel-veri-test · enjeksiyon-kapisi · ci-kapsam-test ·
    is-akisi-kapisi · nobetci-mutasyon-test · shop/test/fiyat-prova.mjs) ayri ayri
    `continue-on-error: true` ve `|| true` enjekte edildi = 12 mutant; HEPSINDE
    `ci-kapsam-test.py` rc=0 VE bu kapi (D'siz hali) rc=0 idi.
    Bolum D: is akisi dosyalarindaki HER kabul-testi cagrisini bulur (kesif
    `ci-kapsam-test.py`'den IMPORT edilir, KOPYALANMAZ — [[ayna-kapi-kesif-ekseni]]) ve
    o cagrinin ETKILI olup olmadigini olcer. Etkisiz + IZINSIZ = KIRMIZI.

  🔴 MESRU FAIL-OPEN KIRILMAZ: `continue-on-error: true` bu depoda BILINCLI olarak da
    kullanilir (deploy.yml "Katalogu D1'e senkronla": senkron patlasa da site
    yayimlanabilsin). Kor bir "hicbir adimda continue-on-error olmasin" kurali bu
    adimi KIRMIZI yakar ve TUM EKIBIN yayinini durdururdu. Bolum D bu yuzden ADIM
    ekseninde DEGIL **KAPI CAGRISI** ekseninde kurulur: yalnizca KESFEDILMIS bir kabul
    testini kosan bir cagri etkisizlestirilirse konusur. D1 senkron adimi hicbir kabul
    testi kosmaz -> Bolum D onu GORMEZ (olculdu: baseline YESIL, D1 adimi yanmiyor).
    Beyan edilmis fail-open ile sessiz etkisizlestirmeyi ayirt eden ikinci mekanizma
    `D_IZIN` izin listesidir; kacis deligi olmasin diye girisi (a) GEREKCE metni ve
    (b) ISE YARAR/OLCULEBILIR bir alternatif nobetci YOLU ister (yol repoda YOKSA
    KIRMIZI — gerekce sessizce bayatlayamaz), ve liste BOYU raporda basilir.

KAPSAM GENISLETME TUZAGINDAN KACINMA ([[kapi-kapsam-genisletme-tuzagi]]): Bolum B
`ci-kapsam-test.py`'nin KURESEL `kosulan()` kapsamina onizleme-imaj.yml EKLEMEZ. Eklenseydi
`onizleme/test/iki-govde-olcum.py` + `duman_toka_kabul.py` bir anda "kosuluyor" sayilir,
kural 4 (BAYAT izin) yanar, muafiyetler soklurdu ve o dosyanin muaf SAYACI kayardi. Onun
yerine burada **DOSYA-BAZLI POZITIF nobetci** var: tek hedef, tek is akisi, tek iddia.
(Depoda olculmus kural: negatif kapsam kuresel, POZITIF kapsam SAYFA/DOSYA BAZLI olmali.)
Bolum D ayni kurala UYAR ve ters yondedir: iddiasi NEGATIF ("bu cagri etkisizlestirilmis
DEGIL") oldugu icin KURESEL olmasi gerekir; buna karsilik `ci-kapsam-test.py`'nin POZITIF
`kosulan()` kapsamina HICBIR SEY EKLEMEZ -> o kapinin "kosulan"/"muaf" SAYILARI degismez
(olculdu: once 43/77, sonra 43/77).

🔴 KAPI KENDINI KILITLEMESIN — kapsam BILEREK DAR: A yalnizca is akisi dosyalarinin
AYRISTIRILABILIRLIGINE + GitHub'in ZORUNLU kildigi iskelete bakar. Bilinmeyen/yeni
GitHub anahtarlari, ifade (`${{ }}`) icerigi, kabuk sozdizimi, action surumleri, `if:`
mantigi DENETLENMEZ — hepsi yanlis-pozitif yuzeyidir ve bu kapi deploy.yml'de
continue-on-error'SUZ kosar (tek sahte-kirmizi TUM ekibin yayinini durdurur,
[[kapi-kapsam-eksen-secimi]]).

⚠️ CI'YA KOYMAK TEK BASINA YETMEZ: deploy.yml'in KENDISI bozulursa hicbir adim kosmaz —
bu kapi da kosmaz. CI'daki degeri (a) DIGER is akislarini (onizleme-imaj.yml) korumak,
(b) bozulmayi bir sonraki YESIL push'ta yakalamak. GERCEK koruma PUSH ONCESIDIR:
    python3 tools/is-akisi-kapisi.py
tek komut olarak kosar (ag YOK, dosya YAZMAZ, ~0,1 s). Onerilen .git/hooks/pre-push
satiri RAPOR-MIMARA.md'de (hook'lar bu depoda COMMIT EDILMEZ).

AYRISTIRICI SECIMI (30 Tem — AYRISTIRICI BAGIMSIZLIGI, push-oncesi yolu acar):
  1. PyYAML (CI'da var: deploy.yml "pip install boto3 pyyaml")
  2. PyYAML yoksa **ruby/psych** (`ruby -ryaml`) — bu Mac'te PyYAML YOK ama ruby VAR,
     yani kapi eskiden YEREL olarak HIC olcemiyordu (rc=2 ÖLÇÜLEMEDİ) ve push-oncesi
     korumasi kagit uzerinde kaliyordu. Psych ayni hukumleri verir (olculdu: ciplak
     `on:` -> bool True, girintide TAB -> SyntaxError, tirnaksiz ": " -> SyntaxError,
     tekrarlanan anahtari SESSIZCE yer, `<<:` merge'i destekler).
  3. Ikisi de yoksa **YESIL SAYMAZ** -> exit 2 + "OLCULEMEDI" basligi.
Ruby kolunda anahtar TIPI korunur (YAML 1.1'de ciplak `on:` BOOLEAN true'dur; JSON
anahtari daima dize oldugu icin bool anahtarlar ASCII bir isaretciyle tasinir ve
Python tarafinda geri cevrilir) — aksi halde iki ayristirici `on:` maddesinde AYRISIRDI.
BEYAN — bilinen TEK sapma: ruby kolunda tekrar denetimi HAM skalar metnini karsilastirir,
PyYAML ise COZULMUS degeri; yani ayni mapping'de `on:` ile `"on":` birlikte yazilirsa ruby
"tekrar" der, PyYAML demez. Is akisi dosyalarinda bu yazim yoktur ve GitHub da onu reddeder.

KENDINI TEST (BOLUM C — bayraksiz/BLOKLAYICI kolda da kosar): kapinin olcum govdeleri
SENTETIK bozuk/gecerli is akislarina karsi ARIZA ENJEKSIYONU ile sinanir. Govde no-op
yapilirsa (or. `return []`) sentetik-bozuk iddialari duser -> kapi KIRMIZI. Bu yuzden
nobetci `--kendini-test` KOLUNDA YASAMAZ (o adim silinirse kol hic kosmaz) — bayraksiz
kosumun icinden cagrilir; `--kendini-test` yalnizca AYRINTILI raporlar.

Kullanim:
    python3 tools/is-akisi-kapisi.py                  # bloklayici kapi (CI adimi)
    python3 tools/is-akisi-kapisi.py --kendini-test   # ariza-enjeksiyon raporu
    python3 tools/is-akisi-kapisi.py --dizin /gecici/mutant-workflows   # mutasyon olcumu

Cikis kodlari: 0 = YESIL · 1 = KIRMIZI · 2 = OLCULEMEDI (ayristirici yok).
"""
import argparse
import ast
import collections.abc
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
WORKFLOW_DIZIN = os.path.join(ROOT, ".github", "workflows")

OLCULEMEDI = 2


# ---------------------------------------------------------------------------
# ORTAK "GERCEK ICRA MI" SUZGECI (KABUK EKSENI) — tools/icra-suzgeci.py
# ---------------------------------------------------------------------------
# KATMANLAMA (DONGU YOK):
#   tools/icra-suzgeci.py            (katman 0 — saf kabuk; YAML BILMEZ)
#     ^-- tools/ci-kapsam-test.py    (katman 1 — kesif + kapsam)
#           ^-- BU DOSYA             (katman 2 — YAML ekseni + etkisizlestirme)
#                 ^-- jenerator/test/kabul.py · tools/konfigur-nobet-mutasyon.py
# Suzgec YAML'a BAGIMLI DEGIL, o yuzden import dongusu olusmaz. YAML ekseni
# (ayristir / _dogru_mu / _yanlis_mu / B_ETKISIZ / _set_e_etkisi) BU dosyada kalir
# ve tuketiciler onu BURADAN alir -> ikinci bir "etkisiz mi" mantigi TUTULMAZ.
def _suzgec_yukle():
    """tools/icra-suzgeci.py'yi MODUL olarak yukle (FAIL-CLOSED: yoksa RuntimeError)."""
    import importlib.util
    yol = os.path.join(TOOLS, "icra-suzgeci.py")
    if not os.path.exists(yol):
        raise RuntimeError(
            "tools/icra-suzgeci.py YOK -> ortak 'gercek icra mi' suzgeci yuklenemedi; "
            "bu kapi `--help`/`echo` sinifi anlamsiz cagrilari GORMEZ (fail-closed).")
    if "pruvo_icra_suzgeci" in sys.modules:
        return sys.modules["pruvo_icra_suzgeci"]
    spec = importlib.util.spec_from_file_location("pruvo_icra_suzgeci", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_icra_suzgeci"] = mod
    spec.loader.exec_module(mod)
    for ad in ("anlamli_cagri", "cagri_sayilir", "etkili_arguman", "birlestir_devam",
               "onek_re", "EVET", "HAYIR", "OLCULEMEDI"):
        if not hasattr(mod, ad):
            raise RuntimeError("tools/icra-suzgeci.py'de %s YOK -> suzgec sozlesmesi "
                               "degismis (fail-closed)" % ad)
    return mod


SUZGEC = _suzgec_yukle()

# ---------------------------------------------------------------------------
# AYRISTIRICI — GERCEK YAML, taklit YOK ([[mimar-kapi-parser-taklidi]]).
# ---------------------------------------------------------------------------
try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - ortama bagli
    _yaml = None

AYRISTIRICI_YOK_TANI = (
    "🔴 OLCULEMEDI — HICBIR YAML AYRISTIRICISI YOK (ne PyYAML ne ruby/psych), bu kapi\n"
    "   HICBIR SEY olcemedi ve YESIL SAYILMADI.\n"
    "   is akisi dosyalari AYRISTIRILMADI: bugunku `startup_failure` sinifi (tirnaksiz\n"
    "   \": \" iceren adim adi) SU AN korunmasizdir.\n"
    "   KURTARMA: pip install pyyaml   (CI'da deploy.yml'in 'Python bagimliliklari' adimi)\n"
    "   ya da: ruby kur (kapi `ruby -ryaml` yedegini kendiliginden kullanir)")

# ---------------------------------------------------------------------------
# YEDEK AYRISTIRICI — ruby/psych. PyYAML yoksa kapi rc=2 ile SUSUYORDU; bu Mac'te
# PyYAML yok, ruby VAR -> push-oncesi koruma fiilen KAGIT UZERINDEYDI. Psych GERCEK bir
# YAML ayristiricisidir (taklit DEGIL, [[mimar-kapi-parser-taklidi]] ihlali yok).
#
# ANAHTAR TIPI ISARETCILERI: JSON anahtari daima dizedir, ama YAML 1.1'de ciplak `on:`
# BOOLEAN true'ya cozulur (hem PyYAML hem Psych boyle yapar). Isaretci olmasa `on:`
# anahtari ruby kolunda "true" DIZESI olur, `_on_var()` onu bulamaz ve iki ayristirici
# AYRI HUKUM verirdi (tam da ayristirici-bagimsizliginin anlamsizlasmasi).
# ⚠️ ISARETCI ASCII: NUL bayti KULLANILMAZ — NUL iceren kaynak dosyayi git/grep IKILI
# (binary) sayar (olculdu: `grep` bu dosyanin hicbir satirini basmadi) ve argv'ye zaten
# konulamaz. Bu uc dize is akisi dosyalarinda anahtar olarak gecmez.
BOOL_TRUE_ISARET = "<<PRUVO-YAML-BOOL-TRUE>>"
BOOL_FALSE_ISARET = "<<PRUVO-YAML-BOOL-FALSE>>"
NULL_ISARET = "<<PRUVO-YAML-NULL>>"

RUBY_KAYNAK = r"""
require 'yaml'
require 'json'
require 'date'

BT = '<<PRUVO-YAML-BOOL-TRUE>>'
BF = '<<PRUVO-YAML-BOOL-FALSE>>'
BN = '<<PRUVO-YAML-NULL>>'

def anahtar(k)
  return BT if k.equal?(true)
  return BF if k.equal?(false)
  return BN if k.nil?
  k.is_a?(String) ? k : k.to_s
end

def don(v)
  case v
  when Hash then v.each_with_object({}) { |(k, val), h| h[anahtar(k)] = don(val) }
  when Array then v.map { |x| don(x) }
  when String, Integer, Float, TrueClass, FalseClass, NilClass then v
  else v.to_s
  end
end

# A2 — tekrarlanan anahtar. Psych de PyYAML gibi SESSIZCE son degeri alir; GitHub ise
# "workflow file issue" verir -> AST uzerinde ozel olarak aranmasi SART.
# `<<` (merge) anahtari YAML'da MESRUDUR ve atlanir.
def tekrar_bul(node)
  if node.is_a?(Psych::Nodes::Mapping)
    gorulen = {}
    node.children.each_slice(2) do |k, _v|
      next unless k.is_a?(Psych::Nodes::Scalar)
      next if k.value == '<<' && !k.quoted
      if gorulen.key?(k.value)
        return [k.value, gorulen[k.value] + 1, k.start_line + 1]
      end
      gorulen[k.value] = k.start_line
    end
  end
  if node.respond_to?(:children) && node.children
    node.children.each do |c|
      r = tekrar_bul(c)
      return r if r
    end
  end
  nil
end

def yukle(metin)
  begin
    Psych.safe_load(metin, permitted_classes: [Date, Time], aliases: true)
  rescue ArgumentError, TypeError
    Psych.safe_load(metin, [Date, Time], [], true)
  end
end

metin = $stdin.read
begin
  t = tekrar_bul(Psych.parse_stream(metin))
  if t
    puts JSON.generate({'durum' => 'tekrar', 'anahtar' => t[0], 'ilk' => t[1],
                        'ikinci' => t[2]})
  else
    puts JSON.generate({'durum' => 'ok', 'govde' => don(yukle(metin))})
  end
rescue Psych::SyntaxError => e
  puts JSON.generate({'durum' => 'hata', 'mesaj' => e.message.to_s})
rescue StandardError => e
  puts JSON.generate({'durum' => 'hata', 'mesaj' => e.class.to_s + ': ' + e.message.to_s})
end
"""

_RUBY_SURUM = None  # None=henuz sorulmadi · False=yok · str=Psych surumu


def _ruby_psych_surumu():
    """ruby/psych VAR MI (varsa Psych surumu, yoksa False). Bir kez sorulur."""
    global _RUBY_SURUM
    if _RUBY_SURUM is None:
        try:
            r = subprocess.run(["ruby", "-ryaml", "-e", "print Psych::VERSION"],
                               capture_output=True, text=True, timeout=30)
            _RUBY_SURUM = r.stdout.strip() if (r.returncode == 0 and r.stdout.strip()) \
                else False
        except (OSError, subprocess.SubprocessError):
            _RUBY_SURUM = False
    return _RUBY_SURUM


def _isaret_geri(deger):
    """ruby kolundan gelen bool/null ANAHTAR isaretcilerini gercek tiplerine cevir."""
    if isinstance(deger, dict):
        yeni = {}
        for a, d in deger.items():
            if a == BOOL_TRUE_ISARET:
                a = True
            elif a == BOOL_FALSE_ISARET:
                a = False
            elif a == NULL_ISARET:
                a = None
            yeni[a] = _isaret_geri(d)
        return yeni
    if isinstance(deger, list):
        return [_isaret_geri(x) for x in deger]
    return deger


def _ruby_ayristir(metin):
    """(govde, hata_metni) — ruby/psych kolu. Hukum metinleri PyYAML koluyla AYNI
    oneklere sahiptir ('TEKRARLANAN ANAHTAR: ' / 'AYRISTIRMA HATASI: ') cunku
    BOZUK_ORNEKLER beklentileri ve tuketiciler o oneklere bakar."""
    try:
        r = subprocess.run(["ruby", "-e", RUBY_KAYNAK], input=metin,
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "AYRISTIRMA HATASI: ruby/psych cagrilamadi (%s)" % e
    if r.returncode != 0 or not r.stdout.strip():
        return None, ("AYRISTIRMA HATASI: ruby/psych yardimcisi calismadi (rc=%d) %s"
                      % (r.returncode, (r.stderr or "").strip().replace("\n", " | ")[:300]))
    try:
        d = json.loads(r.stdout)
    except ValueError as e:
        return None, "AYRISTIRMA HATASI: ruby/psych JSON ciktisi cozulemedi (%s)" % e
    durum = d.get("durum")
    if durum == "tekrar":
        return None, ("TEKRARLANAN ANAHTAR: tekrarlanan anahtar %r (satir %s ve %s)"
                      % (d.get("anahtar"), d.get("ilk"), d.get("ikinci")))
    if durum == "hata":
        return None, "AYRISTIRMA HATASI: %s" % str(d.get("mesaj", "")).replace("\n", " | ")
    return _isaret_geri(d.get("govde")), None


def ayristirici_var():
    return _yaml is not None or bool(_ruby_psych_surumu())


def ayristirici_adi():
    if _yaml is not None:
        return "PyYAML %s" % _yaml.__version__
    s = _ruby_psych_surumu()
    if s:
        return "ruby/psych %s (PyYAML YOK — yedek kol)" % s
    return "YOK"


class TekrarlananAnahtar(Exception):
    """A2 — ayni mapping'de AYNI anahtar iki kez. PyYAML bunu sessizce yer (son deger
    kazanir), GitHub ise "workflow file issue" verir -> ozel olarak yakalanmasi SART."""

    def __init__(self, anahtar, ilk_mark, ikinci_mark):
        self.anahtar = anahtar
        self.ilk_satir = ilk_mark.line + 1
        self.ikinci_satir = ikinci_mark.line + 1
        super().__init__("tekrarlanan anahtar %r (satir %d ve %d)"
                         % (anahtar, self.ilk_satir, self.ikinci_satir))


def _loader_sinifi():
    """Tekrarlanan anahtari YAKALAYAN SafeLoader alt sinifi (PyYAML varsa)."""
    if _yaml is None:
        return None

    class TekrarKontrolluLoader(_yaml.SafeLoader):
        pass

    def _mapping(loader, node, deep=False):
        # ⚠️ TEKRAR DENETIMI flatten_mapping()'DEN ONCE, HAM node.value uzerinde yapilir.
        # Sebep: merge anahtari (`<<: *anchor`) YAML'da MESRUDUR ve flatten sonrasi
        # birlestirilen ciftler node.value'ya EKLENIR -> hem acikca yazilan hem miras
        # alinan bir anahtar iki kez gorunur ve SAHTE-KIRMIZI yanardi. Ham denetim
        # yalnizca ACIKCA IKI KEZ YAZILMIS anahtari yakalar (istenen tam olarak bu).
        gorulen = {}
        for anahtar_node, _deger in node.value:
            if anahtar_node.tag == "tag:yaml.org,2002:merge":
                continue
            try:
                anahtar = loader.construct_object(anahtar_node, deep=True)
            except Exception:
                continue  # anahtar cozulemiyorsa tekrar iddiasi kurulamaz -> sus
            if not isinstance(anahtar, collections.abc.Hashable):
                continue
            if anahtar in gorulen:
                raise TekrarlananAnahtar(anahtar, gorulen[anahtar], anahtar_node.start_mark)
            gorulen[anahtar] = anahtar_node.start_mark
        return _yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    TekrarKontrolluLoader.add_constructor("tag:yaml.org,2002:map", _mapping)
    return TekrarKontrolluLoader


_RUBY_ONBELLEK = {}


def ayristir(metin):
    """(govde, hata_metni) — GERCEK ayristirma. Hata varsa govde None.

    PyYAML varsa O kullanilir (CI kolu). Yoksa ruby/psych yedegi (yerel kol) — sonuc
    metne gore ONBELLEKLENIR cunku her cagri bir ruby SURECI acar (kendini-test 30+
    ayri ayristirma yapar). Tuketiciler donen govdeyi DEGISTIRMEZ (salt-okunur)."""
    if _yaml is None:
        if not _ruby_psych_surumu():
            raise RuntimeError("hicbir YAML ayristiricisi yok")
        if metin not in _RUBY_ONBELLEK:
            _RUBY_ONBELLEK[metin] = _ruby_ayristir(metin)
        return _RUBY_ONBELLEK[metin]
    loader = _loader_sinifi()
    try:
        return _yaml.load(metin, Loader=loader), None
    except TekrarlananAnahtar as e:
        return None, "TEKRARLANAN ANAHTAR: %s" % e
    except _yaml.YAMLError as e:
        # PyYAML tanisi satir/kolon + baglam tasir; ham haliyle basilir (en faydali mesaj).
        return None, "AYRISTIRMA HATASI: %s" % str(e).replace("\n", " | ")


# ---------------------------------------------------------------------------
# BOLUM A — BICIM OLCUMU
# ---------------------------------------------------------------------------
# YAML 1.1'de cikplak `on` anahtari BOOLEAN True'ya cozulur (PyYAML boyle yapar).
# GitHub `on:` yazimini kabul eder -> ikisi de gecerli sayilmali. `"on"` tirnakli
# yazim ise dize olarak gelir.
ON_ANAHTARLARI = (True, "on", "On", "ON")


def _on_var(govde):
    for a in ON_ANAHTARLARI:
        if a in govde:
            return True
    return False


def bicim_hatalari(yol, metin):
    """<yol> is akisi dosyasinin BICIM hatalarini (liste) dondur. Bos liste = temiz.

    Kapsam BILEREK DAR (kapi kendini kilitlemesin): yalnizca (1) ayristirilabilirlik,
    (2) tekrarlanan anahtar, (3) GitHub'in ZORUNLU iskeleti. Bilinmeyen anahtar,
    ifade icerigi, kabuk sozdizimi, action surumu DENETLENMEZ."""
    ad = os.path.basename(yol)
    govde, hata = ayristir(metin)
    if hata:
        return ["%s: %s" % (ad, hata)]

    hatalar = []
    if govde is None:
        return ["%s: dosya BOS ya da yalniz yorum -> GitHub is akisi olarak gecersiz" % ad]
    if not isinstance(govde, dict):
        return ["%s: kok govde mapping DEGIL (%s) -> gecersiz is akisi"
                % (ad, type(govde).__name__)]

    # A3 — zorunlu iskelet
    if not _on_var(govde):
        hatalar.append("%s: `on:` tetikleyicisi YOK -> GitHub is akisini baslatamaz" % ad)
    if "jobs" not in govde:
        hatalar.append("%s: `jobs:` YOK -> gecersiz is akisi" % ad)
        return hatalar
    jobs = govde["jobs"]
    if not isinstance(jobs, dict):
        hatalar.append("%s: `jobs:` mapping DEGIL (%s) -> gecersiz"
                       % (ad, type(jobs).__name__))
        return hatalar
    if not jobs:
        hatalar.append("%s: `jobs:` BOS -> hicbir is tanimli degil" % ad)
        return hatalar

    # A4/A5 — job + step iskeleti
    for job_id, job in jobs.items():
        etiket = "%s [job %s]" % (ad, job_id)
        if not isinstance(job, dict):
            hatalar.append("%s: job govdesi mapping DEGIL (%s)"
                           % (etiket, type(job).__name__))
            continue
        if "uses" in job:
            continue  # yeniden kullanilabilir is akisi cagrisi: runs-on/steps ISTEMEZ
        if "runs-on" not in job:
            hatalar.append("%s: `runs-on` YOK (ve `uses` de yok) -> is baslatilamaz" % etiket)
        if "steps" not in job:
            hatalar.append("%s: `steps` YOK" % etiket)
            continue
        steps = job["steps"]
        if not isinstance(steps, list):
            hatalar.append("%s: `steps` liste DEGIL (%s) -> girinti hatasi olabilir"
                           % (etiket, type(steps).__name__))
            continue
        if not steps:
            hatalar.append("%s: `steps` BOS liste" % etiket)
            continue
        for i, step in enumerate(steps, 1):
            s_etiket = "%s adim %d" % (etiket, i)
            if not isinstance(step, dict):
                hatalar.append("%s: adim mapping DEGIL (%s) -> girinti hatasi olabilir"
                               % (s_etiket, type(step).__name__))
                continue
            if "uses" not in step and "run" not in step:
                hatalar.append("%s (%r): ne `run` ne `uses` var -> gecersiz adim"
                               % (s_etiket, step.get("name", "")))
                continue
            if "run" in step:
                govde_run = step["run"]
                if govde_run is None or not isinstance(govde_run, str) \
                        or not govde_run.strip():
                    hatalar.append("%s (%r): `run:` BOS -> gecersiz adim"
                                   % (s_etiket, step.get("name", "")))
    return hatalar


def is_akisi_dosyalari(dizin):
    """<dizin> altindaki is akisi dosyalarini (tam yol, sirali) dondur."""
    if not os.path.isdir(dizin):
        return []
    return sorted(
        os.path.join(dizin, ad) for ad in os.listdir(dizin)
        if ad.endswith((".yml", ".yaml")) and os.path.isfile(os.path.join(dizin, ad)))


def bolum_a(dizin):
    """(hatalar, olculen_dosya_sayisi)."""
    dosyalar = is_akisi_dosyalari(dizin)
    if not dosyalar:
        return ["is akisi dizininde HIC .yml/.yaml yok: %s -> olculecek sey bulunamadi "
                "(dizin yolu degistiyse kapiyi guncelle)" % dizin], 0
    hatalar = []
    for yol in dosyalar:
        with open(yol, encoding="utf-8") as f:
            hatalar.extend(bicim_hatalari(yol, f.read()))
    return hatalar, len(dosyalar)


# ---------------------------------------------------------------------------
# BOLUM B — POZITIF CAGRI NOBETI (dosya bazli: "su cagri GERCEKTEN kosuyor mu")
# ---------------------------------------------------------------------------
# 30 Tem (O1 onarimi) — TEK HEDEFTEN IDDIA TABLOSUNA. Bolum D "kesfedilmis bir kapi
# cagrisi etkisizlestirilmis mi" diye NEGATIF/KURESEL sorar; cagri hic YOKSA D susar
# (yok olan bir cagri "etkisizlestirilmis" degildir). Curutme turunda bunun bedeli
# olculdu: onizleme-imaj.yml'deki uc kapi adimina uygulanan 8 mutasyonun 7'si SESSIZCE
# YESIL gecti — `|| true` · `continue-on-error: true` · `echo ` ile mensiyona cevirme ·
# `--help` · `if: false` · tetikleyici degisimi · ve en agiri KABUL TESTININ KENDI
# CAGRI SATIRININ SILINMESI ([[nobetci-cagri-satiri-nobetsiz]] sinifi).
#
# KAPSAM GENISLETME TUZAGINDAN KACINMA ([[kapi-kapsam-genisletme-tuzagi]]): tablo
# `ci-kapsam-test.py`'nin KURESEL `kosulan()` kapsamina HICBIR SEY EKLEMEZ (o kapinin
# "kosulan"/"muaf" SAYILARI degismez). Her satir tek is akisi + tek komut hakkinda
# DOSYA BAZLI POZITIF bir iddiadir — depoda olculmus kural: negatif kapsam kuresel,
# pozitif kapsam dosya bazli olmali.
B_IS_AKISI = "onizleme-imaj.yml"

# Cikis kodunu ANLAMSIZLASTIRAN bayraklar: surec is YAPMADAN 0 ile doner.
# KAPALI LISTE (bilincli): GitHub ifade dili gibi burada da "bilinmeyen = etkisiz DEGIL"
# varsayilir. `--help` curutme turunda fiilen olculmus mutasyondur.
B_YARDIM_BAYRAK = frozenset(("--help", "-h", "--version", "-V"))


class BIddia(object):
    """Tek bir POZITIF cagri iddiasi.

    kimlik   : rapor/capraz-kontrol anahtari (ci-kapsam gerekce metni buna atif yapar)
    hedef    : `python3 <hedef>` ile baslamasi gereken betik yolu (repoda VAR OLMALI)
    jetonlar : komut satirinda GECMESI ZORUNLU ek jetonlar (alt-komut/bayrak). Bos ise
               yalniz betigin kosmasi yeterli. `--help`e cevirme mutasyonu tam olarak
               burada yakalanir: alt-komut jetonu kalsa bile yardim bayragi etkisizdir.
    tetik    : is akisi dosyasinin `on:` bloğunda BULUNMASI gereken tetikleyicilerden
               EN AZ BIRI. `workflow_dispatch` -> `workflow_call` mutasyonu isi elle
               tetiklenemez hale getirir ve tum adimlari sessizce olduren tek satirdir.
    neden    : tani metnine giren "bu neden bloklayici" cumlesi.
    """

    def __init__(self, kimlik, hedef, jetonlar, tetik, neden):
        self.kimlik = kimlik
        self.hedef = hedef
        self.jetonlar = tuple(jetonlar)
        self.tetik = tuple(tetik)
        self.neden = neden
        # Negatif ileri-bakis (?![\w./-]) uzun bir baska yolun on-eki olarak yanlis
        # eslesmeyi engeller ama `<hedef> --url ...` bayrakli cagriyi DOGRU eslestirir
        # (ci-kapsam-test.py `_onek_re` ile ayni desen).
        self.onek = re.compile(r"^python3\s+" + re.escape(hedef) + r"(?![\w./-])")


B_IDDIALAR = (
    BIddia("iki-govde", "onizleme/test/iki-govde-olcum.py", (), ("workflow_dispatch",),
           "bu olcum 2-renk (iki govde) GEOMETRISINI openscad ile GERCEKTEN olcen tek "
           "nobetci. Cagri etkisizlesirse musteri yazisi STL'e islenmeden teslim "
           "edilebilir ve HICBIR kapi konusmaz (30 Tem olcumu: 4 denetci de rc=0)."),
    BIddia("duman_kabul", "onizleme/test/duman_kabul.py", (), ("workflow_dispatch",),
           "drift+kapsam kapisinin (tools/onizleme-kapisi.py) AYIRT EDICILIGINI olcen "
           "tek kabul testi. Curutme turunda olculdu: zincirin tamami bu adima asiliydi "
           "ama adimin KENDI cagri satirini koruyan hicbir nobetci YOKTU -> satir "
           "silinince her sey sessizce yesil kaliyordu."),
    BIddia("parmakizi-dizin", "tools/onizleme-kapisi.py",
           ("parmakizi-dogrula", "--dizin", "--paket-anahtar"), ("workflow_dispatch",),
           "imaja GOMULECEK paket anlik goruntusunu repo HEAD kaydiyla karsilastiran "
           "UCUZ fail-fast kapi (docker build'den ONCE). Etkisizlesirse bayat/elle "
           "duzenlenmis bir paketle pahali imaj derlenir. `--paket-anahtar` jetonu "
           "ZORUNLU (O9/tur 5): o bayrak dusurulurse kayit ile CI'nin FIILEN cektigi "
           "R2 paketi arasindaki capraz sessizce olur ve R2'de duran eski bir anahtarla "
           "is tetiklemek yeniden gorunmez hale gelir (tur 4/D8-2)."),
    BIddia("parmakizi-url", "tools/onizleme-kapisi.py",
           ("parmakizi-dogrula", "--url"), ("workflow_dispatch",),
           "KOSAN IMAJIN kendisine sorulan drift kapisi (/parmakizi). Etkisizlesirse "
           "`COPY paket-ozel/` ile gomulen anlik goruntunun repo kaydindan sapmasi "
           "olculmez (27 Tem toka kanamasinin drift ayagi)."),
    BIddia("duman-url", "tools/onizleme-kapisi.py", ("duman", "--url"),
           ("workflow_dispatch",),
           "musteriye ACIK her ailenin bu imajda GERCEKTEN derlendigini olcen kapsam "
           "kapisi. Etkisizlesirse aile listesine yeni giren uretecler sessizce "
           "denenmemis kalir (sabit 12-curl devrindeki sinif geri doner)."),
)

# ---- B-CAPRAZ (O6): MUAFIYET GEREKCESI ile IDDIA birbirine KILITLI ----------
# Curutme turu bulgusu: yeni yazilan `tools/onizleme-kapisi.py` dogrudan
# `ci-kapsam-test.py` IZIN_LISTESI'ne alinmisti ve gerekce metni "onizleme-imaj.yml'de
# bloklayici kosar" DIYORDU — ama bunu dogrulayan HICBIR MAKINE yoktu (o kapi yalniz
# deploy.yml'e bakar). [[kapi-kapsam-genisletme-tuzagi]] sinifi.
# COZUM: muafiyet ile B iddiasi CIFT YONLU baglanir.
#   B5a  anahtar IZIN_LISTESI'nde YOKSA -> KIRMIZI (muafiyet sessizce dusmus; dosya
#        artik "kosuluyor" sayiliyorsa bu tablo satiri da bayattir)
#   B5b  anahtarin B iddiasi YOKSA      -> KIRMIZI (gerekce metni makinesiz kalmis)
# Boylece "muafiyeti birak, iddiayi sil" ya da tersi TEK ADIMDA yapilamaz.
B_MUAFIYET_DAYANAGI = {
    "onizleme/test/duman_kabul.py": ("duman_kabul",),
    "tools/onizleme-kapisi.py": ("parmakizi-dizin", "parmakizi-url", "duman-url"),
}

# Geriye donuk ad (fikstur/mutant uretimi ve tanilar bunu kullanir).
B_HEDEF = B_IDDIALAR[0].hedef

B_ONEK = B_IDDIALAR[0].onek
# Etkisizlestirme: kabuk duzeyinde cikis kodunu yutan formlar.
# ⚠️ SON EK `\b` DEGIL (olculdu, bu kapinin KENDI ariza kaydi): `\b` bir KELIME karakteri
# komsulugu ister -> satir sonundaki `|| :` HIC eslesmiyordu ve `|| :` mutasyonu kapidan
# YESIL geciyordu (nobetci o bicimde OLU). Negatif ileri-bakis `(?![\w./-])` hem satir
# sonunu hem `;`/bosluk komsulugunu kapsar, `|| true2` gibi baska komutu ise eslestirmez.
# TEK KAYNAK: kabuk duzeyinde cikis kodunu yutan formlar. Bolum B ve Bolum D AYNI
# capayi kullanir (ikinci bir "etkisiz mi" mantigi TUTULMAZ).
# `|| exit 0` da eklendi: `|| true` ile ayni islevde, kapali listede ve tek anlamli
# (`|| exit 1` MESRUDUR ve eslesmez).
B_ETKISIZ = re.compile(
    r"\|\|\s*(?:true|/bin/true|:|exit\s+0)(?![\w./-])")


def _dogru_mu(deger):
    """YAML'da `true` bool gelir; `"true"` dize gelir — ikisi de GitHub icin dogrudur."""
    if isinstance(deger, bool):
        return deger
    if isinstance(deger, str):
        return deger.strip().lower() == "true"
    return False


# `if:` DAIMA-YANLIS KAPALI LISTESI. GitHub ifade dili YORUMLANMAZ — yalnizca bu SONLU
# kume "her zaman yanlis" sayilir. Bilinmeyen ifade "yanlis DEGIL" varsayilir.
# 🔴 BEYAN (bilincli, [[kapi-disiplin-ilkesi]]): bu yonde fail-OPEN'dir — biri
# `if: ${{ 1 == 2 }}` yazarsa kapi SUSAR. Alternatif (ifade degerlendirici yazmak) bu
# depoda UC KEZ olculmus sahte-kirmizi yuzeyidir ve bu kapi continue-on-error'SUZ kosar.
DAIMA_YANLIS_IFADELER = frozenset((
    "false", "'false'", '"false"', "0", "!true", "! true", "!(true)",
))


def _yanlis_mu(deger):
    """`if:` degeri HER ZAMAN YANLIS mi (bool `False` ya da DAIMA_YANLIS_IFADELER'den
    biri; `${{ }}` sarmali soyulur). Ifade DEGERLENDIRILMEZ.

    TEK KAYNAK: Bolum B ve Bolum D bu fonksiyonu kullanir. Eski hali yalnizca harfi
    harfine `false` diyordu; kapali liste `${{ false }}` / `'false'` / `0` / `!true`
    yazimlarini da kapsar — B'nin olculmus mutantlari (`if: false`) AYNEN korunur."""
    if isinstance(deger, bool):
        return not deger
    if not isinstance(deger, str):
        return False
    s = deger.strip()
    while s.startswith("${{") and s.endswith("}}"):
        s = s[3:-2].strip()
    return s.lower() in DAIMA_YANLIS_IFADELER


def _tetik_adlari(govde):
    """Is akisi dosyasinin `on:` blogundaki tetikleyici adlari (kume).
    YAML 1.1'de ciplak `on:` BOOLEAN true'ya cozulur -> her iki anahtar da denenir."""
    ham = None
    for anahtar in ("on", True, "true"):
        if isinstance(govde, dict) and anahtar in govde:
            ham = govde[anahtar]
            break
    if isinstance(ham, str):
        return {ham}
    if isinstance(ham, list):
        return set(str(x) for x in ham)
    if isinstance(ham, dict):
        return set(str(k) for k in ham)
    return set()


def _run_satirlari(metin):
    """TEK KAYNAK — YAML EKSENI: [(job_id, adim_no, adim_adi, adim_sebep, satir), ...]

    Bir is akisi dosyasinin TUM `run:` bloklarindaki ICRA satirlarini dondurur:
      * job/adim sinirlari AYRISTIRICIDAN gelir (TAHMIN EDILMEZ)
      * kabuk yorumlari (strip sonrasi `#`) ELENIR
      * `\\` SATIR DEVAMLARI BIRLESTIRILIR (SUZGEC.birlestir_devam) -> mesru
        `python3 tools/x.py \\` + `--bayrak` yazimi YARIM gorunmez
      * `set +e` / `set -e` satirlari ELENIR ve errexit durumu adim_sebep'e islenir
      * adim_sebep: job/adim duzeyindeki ETKISIZLESTIRME sebepleri (continue-on-error,
        DAIMA-YANLIS `if:`) + ayni blokta ONCE gelen `set +e`. BOS ise adim BLOKLAR.
      * SATIR duzeyindeki `|| true` sebebi CAGIRAN ekler (o bir SATIR ozelligidir;
        mesru ornek: onizleme-imaj.yml'de `npx wrangler ... || true` AYNI adimdaki
        baska satirlari etkisizlestirmez).

    Bolum B, Bolum D, Bolum E ve DIS tuketiciler (jenerator/test/kabul.py,
    tools/konfigur-nobet-mutasyon.py) BU fonksiyondan beslenir -> "adim/satir gercekten
    kosuyor mu" mantiginin ikinci kopyasi TUTULMAZ ([[ayna-kapi-kesif-ekseni]])."""
    govde, hata = ayristir(metin)
    if hata or not isinstance(govde, dict):
        return []  # bicim hatasi Bolum A'nin isi; burada IKINCI kez raporlanmaz
    jobs = govde.get("jobs")
    if not isinstance(jobs, dict):
        return []
    kayitlar = []
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        job_sebep = []
        if _dogru_mu(job.get("continue-on-error")):
            job_sebep.append("job'da `continue-on-error: true`")
        if _yanlis_mu(job.get("if")):
            job_sebep.append("job'da DAIMA-YANLIS `if: %r`" % (job.get("if"),))
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for i, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                continue
            adim_sebep = list(job_sebep)
            if _dogru_mu(step.get("continue-on-error")):
                adim_sebep.append("adimda `continue-on-error: true`")
            if _yanlis_mu(step.get("if")):
                adim_sebep.append("adimda DAIMA-YANLIS `if: %r`" % (step.get("if"),))
            run = step.get("run")
            if not isinstance(run, str):
                continue
            adim_adi = step.get("name") if isinstance(step.get("name"), str) else ""
            errexit_kapali = False
            for ham in SUZGEC.birlestir_devam(run):
                s = ham.strip()
                if not s or s.startswith("#"):
                    continue  # kabuk yorumu -> ICRA DEGIL
                etki = _set_e_etkisi(s)
                if etki is not None:
                    errexit_kapali = etki
                    continue
                sebep = list(adim_sebep)
                if errexit_kapali:
                    sebep.append("ayni `run:` blogunda ONCE `set +e` var "
                                 "(errexit kapali -> cikis kodu bloklamaz)")
                kayitlar.append((job_id, i, adim_adi, sebep, s))
    return kayitlar


def etkili_mensiyon(metin, aranan):
    """DIS TUKETICI SOZLESMESI (jenerator/test/kabul.py TEST 4).

    [(job_id, adim_no, adim_adi, satir), ...] — <aranan> metnini GERCEK bir komutun
    ARGUMANI olarak tasiyan ve ETKISIZLESTIRILMEMIS icra satirlari.

    OLCULEN DELIK (30 Tem, DUZ-MENSIYON 1): kabul.py TEST 4
    `"jenerator/hacim.js" in deploy_metni` diyordu. `cp jenerator/hacim.js ...`
    satiri yoruma alinsa (`# cp ...`) ya da `echo cp ...`'a cevrilse metin HALA
    dosyada geciyor -> iddia True kaliyor ve "deploy kopyasi bayt-ozdes" testi
    SESSIZCE anlamini yitiriyordu (olculdu: iki mutantta da beyaz=True)."""
    bulunan = []
    for job_id, adim_no, adim_adi, adim_sebep, s in _run_satirlari(metin):
        if adim_sebep:
            continue
        if B_ETKISIZ.search(s):
            continue
        hukum, _sebep = SUZGEC.etkili_arguman(s, aranan)
        if hukum in (SUZGEC.EVET, SUZGEC.OLCULEMEDI):
            bulunan.append((job_id, adim_no, adim_adi, s))
    return bulunan


def etkili_kapi_cagrilari(metin, yol):
    """DIS TUKETICI SOZLESMESI (tools/konfigur-nobet-mutasyon.py bolum_g).

    [(job_id, adim_no, adim_adi, satir, sebep_listesi), ...] — <yol>'u kosan cagrilar
    ve etkisizlestirme SEBEPLERI. sebep BOS ise cagri GERCEKTEN BLOKLAYICIDIR.

    OLCULEN DELIK (30 Tem, DUZ-MENSIYON 2): konfigur-nobet-mutasyon.py
    `"konfigur-test.py" in adim and "run:" in adim` ile adim ariyor, `continue-on-error`
    metnine bakiyordu. `echo python3 tools/konfigur-test.py --anahat` ve yoruma alinmis
    cagri mutantlarinda rapor HALA "BLOKLAYICI" yaziyordu (olculdu).

    🔴 ADAY SUZGECI OLARAK `onek_re` KULLANILMAZ (olculdu: yanlis-pozitif F10):
    `run: bash -c "python3 tools/ci-kapsam-test.py"` MESRU bir yazimdir ama kaba
    `^python3 <yol>` capasina UYMAZ -> aday hic bulunmaz ve "cagri YOK" hukmu SAHTE
    KIRMIZI uretirdi. Burada aday+hukum TEK ADIMDA SUZGEC.anlamli_cagri()'dan gelir
    (`bash -c`, tek-jetonluk tirnakli skalar, `python3 -u`, `env VAR=1` hepsi cozulur).
    Bolum D'nin `kapi_cagrilari()` fonksiyonu 121 kesif yolunu gezdigi icin BILINCLI
    olarak kaba capada kalir (beyan: D_MUTANTLAR ustundeki "BEYAN EDILMIS SINIR")."""
    bulunan = []
    for job_id, adim_no, adim_adi, adim_sebep, s in _run_satirlari(metin):
        hukum0, _s0, _a0 = SUZGEC.anlamli_cagri(s, yol)
        if hukum0 is None:
            continue  # satir bu yolla ILGISIZ
        sebep = list(adim_sebep)
        if B_ETKISIZ.search(s):
            sebep.append("komutta `|| true` / `|| :` / `|| exit 0` (cikis kodu yutulur)")
        hukum, suz_sebep, _arg = SUZGEC.anlamli_cagri(s, yol)
        if hukum == SUZGEC.HAYIR:
            sebep.append("cagri ANLAMSIZ: %s" % suz_sebep)
        bulunan.append((job_id, adim_no, adim_adi, s, sebep))
    return bulunan


def etkili_cagrilar(metin, iddia=None):
    """<metin> (bir is akisi dosyasinin TAM metni) icinde <iddia>'yi FIILEN kosan
    (etkili) cagrilari dondur: [(job_id, adim_no, komut_satiri), ...].
    `iddia` verilmezse tablonun ILK satiri (iki-govde) olculur.

    ETKILI DEGIL sayilan haller (curutme turunda fiilen olculmus 8 mutasyonun tamami):
      * cagri satiri SILINDI                          -> hic eslesme yok
      * cagri satiri YORUMA alindi (`# python3 ...`)  -> satir suzulur
      * `echo ` ile MENSIYONA cevrildi                 -> satir `python3` ile BASLAMIYOR
      * zorunlu alt-komut/bayrak DUSURULDU             -> jeton sarti tutmuyor
      * `--help` / `-h` / `--version` eklendi          -> surec is YAPMADAN 0 doner
      * satirda `|| true` / `|| :` / `|| exit 0` var   -> cikis kodu yutulur
      * ayni `run:` blogunda ONCE `set +e` var          -> errexit kapali
      * adimda (ya da job'da) `continue-on-error: true`
      * adimda (ya da job'da) DAIMA-YANLIS `if:` (`false`, `${{ false }}`, `0`, ...)
    Ayristirma GERCEK YAML uzerinden yapilir (adim/job sinirlari TAHMIN EDILMEZ);
    `run: |` blogunun ICINDEKI kabuk yorumlari satir bazinda suzulur.

    🔴 30 TEM EKI (dal): job/adim sinirlari + `\\` satir devami + `set +e` ARTIK
    ORTAK SUZGECTEN gelir (_run_satirlari) — "adim gercekten kosuyor mu" mantiginin
    ikinci kopyasi TUTULMAZ ([[ayna-kapi-kesif-ekseni]]). Ayrica cagrinin ANLAMLI
    olmasi da sart (SUZGEC.cagri_sayilir): `--help` ile cagrilan ya da `echo`
    mensiyonuna cevrilmis bir satir ETKILI SAYILMAZ. main'in KAPALI-LISTE yardim
    bayragi ve zorunlu-jeton sartlari AYNEN KORUNUR (iki savunma birden)."""
    iddia = iddia or B_IDDIALAR[0]
    bulunan = []
    for job_id, adim_no, _adim_adi, adim_sebep, s in _run_satirlari(metin):
        if adim_sebep:
            continue  # continue-on-error / daima-yanlis if: / `set +e`
        if not iddia.onek.match(s):
            continue  # per-IDDIA capa (main'in cok-iddiali tablosu)
        if B_ETKISIZ.search(s):
            continue  # `|| true` / `|| :` / `|| exit 0` cikis kodunu yutar
        jeton = s.split()
        if any(y in jeton for y in B_YARDIM_BAYRAK):
            continue  # `--help` -> surec is yapmadan 0 doner (main kapali listesi)
        if not all(z in jeton for z in iddia.jetonlar):
            continue  # zorunlu alt-komut/bayrak dusurulmus
        if not SUZGEC.cagri_sayilir(s, iddia.hedef):
            continue  # MENSIYON komutu (`echo ...`) / anlamsiz bayrak -> govde kosmaz
        bulunan.append((job_id, adim_no, s))
    return bulunan


B_TANI_KALIP = (
    "CAGRI NOBETI KIRMIZI [%s]: %s dosyasinda `python3 %s%s` ETKILI olarak kosmuyor.\n"
    "   Etkisiz sayilan haller: satir SILINMIS · YORUMA alinmis · `echo ` ile mensiyona\n"
    "   cevrilmis · zorunlu alt-komut dusurulmus · `--help`/`-h` eklenmis ·\n"
    "   `|| true` / `|| :` / `|| exit 0` eklenmis · ayni blokta once `set +e` ·\n"
    "   adim/job'da `continue-on-error: true` ya da DAIMA-YANLIS `if:`.\n"
    "   NEDEN BLOKLAYICI: %s\n"
    "   GERI KOY: `%s` is akisinda bloklayici bir `run:` satiri olarak.")

B_TETIK_TANI = (
    "TETIKLEYICI NOBETI KIRMIZI [%s]: %s dosyasinin `on:` blogunda %s tetikleyicilerinden\n"
    "   HICBIRI yok (bulunan: %s) -> is ELLE TETIKLENEMEZ, yani icindeki TUM kapi\n"
    "   adimlari tek satirlik bir degisiklikle sessizce olur. Curutme turunda olculdu:\n"
    "   `workflow_dispatch` -> `workflow_call` mutasyonu 8 mutasyonun en sessizidir.")


def b_iddia_hatalari(metin, iddia):
    """Tek bir B iddiasini olc -> (hatalar, etkili_cagri_sayisi)."""
    hatalar = []
    govde, ayr_hata = ayristir(metin)
    if not ayr_hata and isinstance(govde, dict):
        tetikler = _tetik_adlari(govde)
        if iddia.tetik and not (tetikler & set(iddia.tetik)):
            hatalar.append(B_TETIK_TANI % (
                iddia.kimlik, B_IS_AKISI, " / ".join(iddia.tetik),
                ", ".join(sorted(tetikler)) or "(hicbiri)"))
    cagrilar = etkili_cagrilar(metin, iddia)
    if not cagrilar:
        hatalar.append(B_TANI_KALIP % (
            iddia.kimlik, B_IS_AKISI, iddia.hedef,
            (" " + " ".join(iddia.jetonlar)) if iddia.jetonlar else "",
            iddia.neden, B_IS_AKISI))
    return hatalar, len(cagrilar)


def b_capraz_hatalari():
    """B-CAPRAZ (O6) — ci-kapsam muafiyeti ile B iddiasi CIFT YONLU kilitli mi.

    Gerekce metnini AYRISTIRMAZ (metin capasi bayatlar): dogrudan
    `ci-kapsam-test.py::IZIN_LISTESI` sozlugunun ANAHTARLARINA ve bu dosyadaki
    `B_IDDIALAR` kimliklerine bakar. Ikisinden biri dusürse KIRMIZI."""
    hatalar = []
    kimlikler = set(i.kimlik for i in B_IDDIALAR)
    mod = _ci_kapsam_modulu()
    if mod is None:
        return ["B-CAPRAZ OLCULEMEDI (fail-closed KIRMIZI): %s" % _CI_KAPSAM_HATA]
    izin = getattr(mod, "IZIN_LISTESI", None)
    if not isinstance(izin, dict):
        return ["B-CAPRAZ OLCULEMEDI (fail-closed KIRMIZI): ci-kapsam-test.py'de "
                "IZIN_LISTESI sozlugu YOK -> sozlesme degismis, B_MUAFIYET_DAYANAGI'ni "
                "guncelle"]
    for yol, gerekli in sorted(B_MUAFIYET_DAYANAGI.items()):
        if yol not in izin:                                     # B5a
            hatalar.append(
                "B-CAPRAZ: '%s' artik ci-kapsam-test.py IZIN_LISTESI'nde DEGIL, ama bu "
                "dosyada hala onun adina B iddiasi tutuluyor (%s). Muafiyet kalktiysa "
                "dosya deploy.yml'de kosuyor demektir -> B_MUAFIYET_DAYANAGI girisini "
                "SIL; kosmuyorsa muafiyeti geri koy." % (yol, ", ".join(gerekli)))
        eksik = [k for k in gerekli if k not in kimlikler]
        if eksik:                                               # B5b
            hatalar.append(
                "B-CAPRAZ: '%s' ci-kapsam-test.py'de GEREKCELI MUAF ve gerekce metni "
                "'%s' B iddialarina dayaniyor, ama bu iddialar B_IDDIALAR tablosunda YOK "
                "-> muafiyetin MAKINE DAYANAGI dusmus, gerekce sessizce bayatlar "
                "([[kapi-kapsam-genisletme-tuzagi]] sinifi). Iddiayi geri koy ya da "
                "muafiyeti kaldir." % (yol, ", ".join(eksik)))
    return hatalar


OZ_CAGRI_TANI = (
    "OZ-CAGRI NOBETI KIRMIZI: bu dosyanin main() govdesinde `kendini_test()` cagrisinin "
    "SONUCU bir atamaya baglanmiyor -> BOLUM C (ariza enjeksiyonu) bloklayici kolda "
    "kosmuyor demektir ve kapinin olcum govdeleri sessizce no-op yapilabilir.\n"
    "   OLCULDU (30 Tem, bu kapinin KENDI mutasyon turu): `c_hata, c_iddia = kendini_test()` "
    "satiri silinince 7 govde mutasyonundan 6'si yakalanmaya devam ediyor ama BU biri "
    "KACIYORDU (hem --kendini-test hem bloklayici kol rc=0).\n"
    "   GERI KOY: main() icinde `c_hata, c_iddia = kendini_test()` (atama SART; sonucu "
    "atilan cikplak cagri sayilmaz).")


# main() govdesinde cagrilmasi ZORUNLU bolum fonksiyonlari (AST ile aranir).
# NEDEN: `bolum_e(args.dizin)` satiri silinirse tetikleyici + zorunlu-adim iddialari
# CI'da HIC kosmaz; Bolum C (kendini_test) bolum_e()'yi SENTETIK fiksturlerle olcmeye
# devam ettigi icin "govde saglam" der ve delik SESSIZCE geri gelir. Aynisi bolum_a/b/d
# icin de gecerli. Duz isim cagrisi araniyor (or. `bolum_e(...)`).
MAIN_ZORUNLU_BOLUMLER = ("bolum_a", "bolum_b", "bolum_d", "bolum_e")

MAIN_BOLUM_TANI = (
    "BOLUM KABLOSU KOPMUS: main() govdesinde %s cagrisi YOK -> o bolumun iddialari "
    "CI'da HIC kosmuyor.\n"
    "   🔴 Bu SESSIZ bir kacistir: Bolum C (kendini_test) o bolumun GOVDESINI sentetik "
    "fiksturlerle olcmeye devam eder ve 'saglam' der; oysa GERCEK is akisi dosyalari "
    "hic denetlenmez.\n"
    "   GERI KOY: main() icinde `%s(args.dizin)` (ve sonucunu `hatalar`'a ekle).")


def bolum_kablosu_kontrol():
    """main() govdesinde bolum_a/b/d/e cagrilari duruyor mu (AST, metin capasi DEGIL)."""
    try:
        with open(os.path.abspath(__file__), encoding="utf-8") as f:
            agac = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        return ["BOLUM KABLOSU OLCULEMEDI: kendi kaynagi ayristirilamadi (%s)" % e]
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef) and dugum.name == "main"):
            continue
        cagrilar = {alt.func.id for alt in ast.walk(dugum)
                    if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name)}
        return [MAIN_BOLUM_TANI % (b, b) for b in MAIN_ZORUNLU_BOLUMLER
                if b not in cagrilar]
    return ["BOLUM KABLOSU OLCULEMEDI: main() fonksiyonu bulunamadi"]


def oz_cagri_kontrol():
    """OZ-CAGRI NOBETI — main() BLOKLAYICI kolunda kendini_test() GERCEKTEN cagriliyor mu.

    YONTEM: AST (metin capasi DEGIL). Kendi kaynagini ayristirir, `main` fonksiyonunu bulur
    ve govdesinde degeri `kendini_test(...)` cagrisi olan bir ATAMA arar. Atama sarti
    bilincli: sonucu atilan cikplak bir cagri hatalari toplamaya girmez, yani nobetci yine
    olur. AST secildi cunku metin capasi (satiri harfiyen aramak) bu dosyanin kendi
    bicimlendirmesine kilitlenir ve mesru bir yeniden-adlandirmada sahte-kirmizi yakar
    ([[kapi-anchor-coupling-ikilemi]]: anchor-BAGIMSIZ olcum tercih edilir).

    🔴 KABUL EDILEN SINIR (sonsuz geriye gidis burada KESILIR — ci-kapsam-test.py ile ayni
    beyan): BU fonksiyonun bolum_b()'den yapilan cagrisi kendi basina nobetsizdir. Yani
    "hem oz_cagri_kontrol() cagrisini hem kendini_test() cagrisini birden silen" IKI ADIMLI
    bir mutasyon kacar. Tek-adimli mutasyon kapsanir; ustu bir harness sorusudur
    (tools/nobetci-mutasyon-test.py sinifi)."""
    import ast
    kaynak_yol = os.path.abspath(__file__)
    try:
        with open(kaynak_yol, encoding="utf-8") as f:
            agac = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        return ["OZ-CAGRI NOBETI OLCULEMEDI: kendi kaynagi ayristirilamadi (%s)" % e]
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef) and dugum.name == "main"):
            continue
        for alt in ast.walk(dugum):
            if not isinstance(alt, ast.Assign):
                continue
            deger = alt.value
            if isinstance(deger, ast.Call) and isinstance(deger.func, ast.Name) \
                    and deger.func.id == "kendini_test":
                return []
        return [OZ_CAGRI_TANI]
    return ["OZ-CAGRI NOBETI OLCULEMEDI: main() fonksiyonu bulunamadi (dosya yeniden "
            "duzenlendiyse bu nobetciyi guncelle)"]


def bolum_b(dizin):
    """(hatalar, etkili_cagri_sayisi, iddia_sayisi).

    Bolum B'nin semantigi "BIR CAGRI GERCEKTEN KOSUYOR MU" oldugu icin kapinin KENDI ic
    self-test cagrisi da BURADA olculur (oz_cagri_kontrol) — ayni sinif, ayni bolum."""
    yol = os.path.join(dizin, B_IS_AKISI)
    if not os.path.exists(yol):
        return ["CAGRI NOBETI: %s bulunamadi (%s) -> hedeflerin kostugu is akisi kalkmis, "
                "olcum yapilamadi (fail-closed KIRMIZI)" % (B_IS_AKISI, yol)], 0, 0
    hatalar = list(oz_cagri_kontrol()) + list(bolum_kablosu_kontrol())
    hatalar.extend(b_capraz_hatalari())
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    toplam = 0
    for iddia in B_IDDIALAR:
        hedef_yol = os.path.join(ROOT, iddia.hedef)
        if not os.path.exists(hedef_yol):
            hatalar.append("CAGRI NOBETI [%s]: hedef betik YOK (%s) -> nobetci bayat; "
                           "hedef yeniden adlandirildiysa B_IDDIALAR tablosunu guncelle"
                           % (iddia.kimlik, iddia.hedef))
            continue
        i_hata, n = b_iddia_hatalari(metin, iddia)
        hatalar.extend(i_hata)
        toplam += n
    return hatalar, toplam, len(B_IDDIALAR)


# ---------------------------------------------------------------------------
# BOLUM D — KAPI ADIMI ETKISIZLESTIRME NOBETI ("CI'da VAR" != "CI'da BLOKLAR")
# ---------------------------------------------------------------------------
# KESIF IMPORT EDILIR, AYNALANMAZ ([[ayna-kapi-kesif-ekseni]]): ci-kapsam-test.py'nin
# kesif predikatlari (tools/*-test.py · test-*.py · *-kapisi.py · shop|onizleme|jenerator
# /test/*) ve `<yorumlayici> <yol>` capasi (`_onek_re`, uzantidan python3/node) BURADA
# YENIDEN YAZILMAZ. Sebep: bu depoda IKI KEZ olculdu — bir kapinin kesfini "aynalayan"
# ikinci arac eksenlerin birini kacirinca sessizce yarim koruma verir.
_CI_KAPSAM = None
_CI_KAPSAM_HATA = None


def _ci_kapsam_modulu():
    """ci-kapsam-test.py'yi MODUL olarak yukle (tire iceren dosya adi -> importlib).
    Modul govdesi yalnizca sabit/fonksiyon tanimlar (main() korumali) -> yan etkisi yok."""
    global _CI_KAPSAM, _CI_KAPSAM_HATA
    if _CI_KAPSAM is not None or _CI_KAPSAM_HATA is not None:
        return _CI_KAPSAM
    import importlib.util
    yol = os.path.join(TOOLS, "ci-kapsam-test.py")
    if not os.path.exists(yol):
        _CI_KAPSAM_HATA = ("tools/ci-kapsam-test.py YOK -> kapi kesfi (hangi dosyalar "
                           "kabul testi) yapilamadi")
        return None
    try:
        spec = importlib.util.spec_from_file_location("pruvo_ci_kapsam", yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001 — her tur import arizasi ayni hukmu verir
        _CI_KAPSAM_HATA = "tools/ci-kapsam-test.py MODUL olarak yuklenemedi (%s)" % e
        return None
    for ad in ("kesfet", "_onek_re"):
        if not hasattr(mod, ad):
            _CI_KAPSAM_HATA = ("tools/ci-kapsam-test.py'de %s() YOK -> kesif sozlesmesi "
                               "degismis, Bolum D'yi guncelle" % ad)
            return None
    _CI_KAPSAM = mod
    return mod


def kapi_capalari():
    """[(kapi_yolu, derlenmis_onek_re), ...] — kesif + capa ci-kapsam-test.py'den.
    (None, tani) doner olculemezse."""
    mod = _ci_kapsam_modulu()
    if mod is None:
        return None, _CI_KAPSAM_HATA
    try:
        kesif = mod.kesfet()
    except SystemExit as e:  # kesfet() git ls-files rc!=0 olursa sys.exit eder
        return None, "kesif basarisiz (git ls-files rc!=0): %s" % e
    except Exception as e:  # noqa: BLE001 — `git` binary'si YOKSA FileNotFoundError gelir
        # OLCULDU (30 Tem): PATH'te git olmayan bir ortamda bu satir CIPLAK TRACEBACK
        # veriyordu (rc=1 ama teshis yok). Fail-closed KIRMIZI kalir, tanisi okunur olur.
        return None, "kesif cagrilamadi (%s: %s)" % (type(e).__name__, e)
    if not kesif:
        return None, "kesif BOS liste dondurdu -> predikat bozulmus ya da git agaci yok"
    return [(y, mod._onek_re(y)) for y in kesif], None


def _set_e_etkisi(satir):
    """Bir kabuk satiri `errexit`i KAPATIYOR (True) / ACIYOR (False) mu; ilgisizse None.

    Kapali liste: `set +e`, `set +ex`, `set +o errexit` kapatir; `set -e`, `set -eu`,
    `set -o errexit` acar. GitHub varsayilan kabugu `bash -e {0}` oldugu icin errexit
    BASLANGICTA ACIKTIR -> `set +e`'den SONRAKI bir kapi cagrisinin cikis kodu YUTULUR."""
    jetonlar = satir.split()
    if not jetonlar or jetonlar[0] != "set":
        return None
    i = 1
    while i < len(jetonlar):
        j = jetonlar[i]
        if j in ("-o", "+o"):
            if i + 1 < len(jetonlar) and jetonlar[i + 1] == "errexit":
                return j == "+o"
            i += 2
            continue
        if j.startswith("+") and "e" in j[1:]:
            return True
        if j.startswith("-") and "e" in j[1:]:
            return False
        i += 1
    return None


def kapi_cagrilari(metin, capalar):
    """Bir is akisi dosyasinin metninde KESFEDILMIS kabul testlerini kosan cagrilari
    ve her birinin ETKISIZLESTIRME SEBEPLERINI dondur.

    [(job_id, adim_no, adim_adi, kapi_yolu, komut, [sebep, ...]), ...]
    sebep listesi BOS ise cagri ETKILIDIR.

    Ayristirma GERCEK YAML (adim/job sinirlari TAHMIN EDILMEZ); `run:` blogu SATIR
    BAZINDA gezilir cunku `|| true` bir ADIM ozelligi degil SATIR ozelligidir — mesru
    ornek: onizleme-imaj.yml'de `npx wrangler ... || true` satiri, AYNI adimda bulunan
    baska satirlari etkisizlestirmez ve hicbir kapi cagrisi tasimaz.

    🔴 30 TEM EKI — ICRA-DISI BAYRAK (DELIK 1) ETKISIZLESTIRME SAYILIR: adim CI'da
    GORUNUR, exit 0 verir ve "kapi var" sanilir, ama olcum govdesi HIC kosmaz. Bu
    Bolum D'nin ta kendisidir ("CI'da VAR" != "CI'da BLOKLAR") -> `--help`/`-h`/
    `--version` ile cagrilan bir kapi artik SEBEPLI (fail-open) raporlanir ve
    D_IZIN beyan mekanizmasi ona da uygulanir."""
    bulunan = []
    for job_id, adim_no, adim_adi, adim_sebep, s in _run_satirlari(metin):
        for yol, onek in capalar:
            if not onek.match(s):
                continue
            sebep = list(adim_sebep)
            if B_ETKISIZ.search(s):
                sebep.append("komutta `|| true` / `|| :` / `|| exit 0` "
                             "(cikis kodu yutulur)")
            hukum, suz_sebep, _arg = SUZGEC.anlamli_cagri(s, yol)
            if hukum == SUZGEC.HAYIR:
                sebep.append("cagri ANLAMSIZ (olcum govdesi kosmaz): %s" % suz_sebep)
            bulunan.append((job_id, adim_no, adim_adi, yol, s, sebep))
            break
    return bulunan


# ---- D IZIN LISTESI: BEYAN EDILMIS fail-open -------------------------------
# ANAHTAR : (is_akisi_dosya_adi, kapi_yolu)
# DEGER   : (GEREKCE metni, OLCULEBILIR alternatif nobetci yolu)
#
# 🔴 KACIS DELIGI OLMASIN — uc kural birden isler:
#   D2  gerekce BOS/bosluk -> KIRMIZI (gerekcesiz muafiyet yok).
#   D3  ikinci alan repoda VAR OLMAYAN bir yol -> KIRMIZI. Bu, bu depoda OLCULMUS
#       "gerekce metnindeki koruma iddiasi hic denetlenmiyor, sessizce bayatliyor"
#       tuzagina karsi tek OLCULEBILIR dayanaktir: giris "kaybi su nobetci karsiliyor"
#       demek zorunda ve o nobetcinin varligi her kosumda dogrulanir.
#   D4  giris ARTIK etkisizlestirilmis bir cagriya karsilik gelmiyorsa -> KIRMIZI
#       (bayat muafiyet; liste kendiliginden BUYUYUP kalamaz).
# Liste BOYU raporda basilir -> buyumesi gozden kacmaz.
#
# BUGUN BOS (olculdu 30 Tem): deploy.yml + onizleme-imaj.yml'de etkisizlestirilmis
# HICBIR kapi cagrisi yok. deploy.yml'in BILINCLI fail-open adimi ("Katalogu D1'e
# senkronla", continue-on-error: true) hicbir KABUL TESTI kosmaz -> Bolum D onu GORMEZ
# ve buraya girmesi GEREKMEZ. Mekanizmanin uc kuralı sentetik girislerle sinanir
# (kendini_test D-IZIN iddialari).
D_IZIN = {}

D_TANI_ONEK = (
    "KAPI ADIMI ETKISIZLESTIRILMIS (fail-open, BEYANSIZ): %s -> `%s`\n"
    "   is akisi: %s · job: %s · adim %d %s\n"
    "   sebep(ler): %s\n"
    "   NEDEN BLOKLAYICI: adim CI'da GORUNUR ama cikis kodu bloklamaz -> 'kapi var'\n"
    "   sanilirken koruma YOKTUR ('CI'da VAR' != 'CI'da BLOKLAR'). Bu tek satirla her\n"
    "   kapi sessizce oldurulebiliyordu (olculdu 30 Tem: 12 mutantta 2 denetci de rc=0).\n"
    "   COZUM: etkisizlestirmeyi GERI AL. Fail-open GERCEKTEN isteniyorsa\n"
    "   tools/is-akisi-kapisi.py icindeki D_IZIN'e (gerekce, alternatif-nobetci-yolu)\n"
    "   ciftiyle YAZ — yol repoda var olmak ZORUNDA.")


def bolum_d(dizin):
    """(hatalar, olculen_kapi_cagrisi, etkisiz_sayisi, izinli_sayisi)."""
    capalar, capa_hata = kapi_capalari()
    if capalar is None:
        return ["ETKISIZLESTIRME NOBETI OLCULEMEDI (fail-closed KIRMIZI): %s"
                % capa_hata], 0, 0, 0
    hatalar = []
    toplam = 0
    etkisiz_anahtarlar = set()
    for yol in is_akisi_dosyalari(dizin):
        ad = os.path.basename(yol)
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        for job_id, adim_no, adim_adi, kapi, komut, sebep in kapi_cagrilari(metin, capalar):
            toplam += 1
            if not sebep:
                continue
            anahtar = (ad, kapi)
            etkisiz_anahtarlar.add(anahtar)
            if anahtar in D_IZIN:
                continue
            hatalar.append(D_TANI_ONEK % (
                kapi, komut, ad, job_id, adim_no,
                ("(%s)" % adim_adi) if adim_adi else "", " + ".join(sebep)))
    # D2/D3 — izin listesi HIJYENI
    for anahtar, deger in sorted(D_IZIN.items()):
        etiket = "%s :: %s" % anahtar
        if not (isinstance(deger, (tuple, list)) and len(deger) == 2):
            hatalar.append("D_IZIN girisi (gerekce, nobetci_yolu) CIFTI DEGIL: %s -> %r"
                           % (etiket, deger))
            continue
        gerekce, nobetci = deger
        if not (isinstance(gerekce, str) and gerekce.strip()):
            hatalar.append("D_IZIN GEREKCESIZ giris (bos gerekce): %s" % etiket)
        if not (isinstance(nobetci, str) and nobetci.strip()):
            hatalar.append("D_IZIN OLCULEBILIR DAYANAK YOK: %s -> ikinci alan bos; "
                           "kaybi karsilayan nobetcinin repo yolunu yaz" % etiket)
        elif not os.path.exists(os.path.join(ROOT, nobetci)):
            hatalar.append("D_IZIN DAYANAGI BAYAT: %s -> gerekcenin dayandigi nobetci "
                           "repoda YOK (%s). Gerekce sessizce bayatlamis: ya yolu "
                           "duzelt ya muafiyeti kaldir." % (etiket, nobetci))
        # D4 — bayat muafiyet: artik etkisizlestirilmis bir cagri degil
        if anahtar not in etkisiz_anahtarlar:
            hatalar.append("D_IZIN BAYAT giris (artik etkisizlestirilmis bir kapi "
                           "cagrisina karsilik gelmiyor — SIL): %s" % etiket)
    return hatalar, toplam, len(etkisiz_anahtarlar), len(D_IZIN)


# ---------------------------------------------------------------------------
# BOLUM E — TETIKLEYICI + ZORUNLU KAPI ADIMI NOBETI (deploy.yml, DOSYA BAZLI POZITIF)
# ---------------------------------------------------------------------------
# NEDEN VAR (30 Tem yargi turu, OLCULEN DELIK 2 ve 4):
#
#   D2) deploy.yml'in GERCEK `on.push` blogu SILINDI ve yerine
#         on:
#           workflow_dispatch:
#             inputs:
#               push: {...}
#       yazildi. `on:` anahtari DURUYOR ve `push` metni dosyada GECIYOR -> Bolum A3'un
#       "`on:` var mi" iddiasi tatmin oluyor, METIN arayan hicbir kapi da fark etmiyor.
#       SONUC: main'e push edilince is akisi HIC TETIKLENMEZ — urun sayfalari, sitemap,
#       TUM kapilar ve Pages yayini kosmaz; kimse KIRMIZI gormez cunku KOSUM YOKTUR.
#       Olculdu: dort denetci de rc=0.
#       🔴 IDDIA AYRISTIRILMIS AGACTA KURULUR: `on` DUGUMUNUN DOGRUDAN ALTINDA `push`
#       aranir. METIN ARAMASI YASAK (metin `inputs.push`'u da bulur -> tam bu delik).
#
#   D1/D4) `tools/ci-kapsam-test.py`'nin BAYRAKSIZ (kapsam kolu) adimi `--help`'e
#       cevrildi ya da butunuyle silindi. O betigin KENDI nobetcisi bunu yakalar, AMA
#       ayni surecte yasar; iki ADIM birden silinirse o surec HIC kosmaz. Buradaki
#       iddia BAGIMSIZ BIR SURECTEN (bu kapinin kendi CI adimindan) ayni seyi olcer.
#
# KAPSAM DOSYA BAZLI POZITIF (depoda olculmus kural, [[kapi-kapsam-genisletme-tuzagi]]):
# "her is akisinda push olsun" DEMEZ — onizleme-imaj.yml BILINCLI olarak yalniz
# `workflow_dispatch` ile tetiklenir (imaj sik degismez) ve kor bir kural onu KIRMIZI
# yakip tum yayini durdururdu. Iddia TEK DOSYAYA (deploy.yml) capalanir.
E_DOSYA = "deploy.yml"
E_TETIKLEYICILER = ("push",)
# (kapi_yolu, zorunlu_bayrak_ya_da_None, adim_etiketi)
#   bayrak None -> o bayragi TASIMAYAN (yani ana/bayraksiz kolu kosan) bir cagri sart
E_ZORUNLU_CAGRILAR = (
    ("tools/ci-kapsam-test.py", None,
     "CI kapsam kapisi — KAPSAM kolu (her kabul testi kosuluyor mu / gerekceli muaf mi)"),
    ("tools/ci-kapsam-test.py", "--kendini-test",
     "CI kapsam kapisi OZ-NOBETCILERI (bulgu1 + muaf sayaci + adim nobetcileri)"),
)

E_TETIKLEYICI_TANI = (
    "TETIKLEYICI NOBETI KIRMIZI: %s dosyasinda AYRISTIRILMIS `on` dugumunun DOGRUDAN\n"
    "   altinda `%s` tetikleyicisi YOK.\n"
    "   `on` dugumunun dogrudan alt anahtarlari: %s\n"
    "   OLCULEN DELIK (30 Tem): gercek `on.push` blogu silinip `push` bir\n"
    "   `workflow_dispatch.inputs` GIRDISI olarak yazilinca `on:` anahtari duruyor,\n"
    "   `push` metni dosyada geciyor ve DORT denetci de rc=0 veriyordu. Ama main'e\n"
    "   push edilince is akisi HIC TETIKLENMEZ: urun sayfalari, sitemap, TUM kapilar\n"
    "   ve Pages yayini kosmaz — kimse kirmizi gormez cunku KOSUM YOKTUR.\n"
    "   GERI KOY:\n"
    "     on:\n"
    "       push:\n"
    "         branches: [main]\n"
    "       workflow_dispatch:")

E_ZORUNLU_TANI = (
    "ZORUNLU KAPI ADIMI NOBETI KIRMIZI: %s dosyasinda `%s`%s ETKILI olarak kosan\n"
    "   hicbir adim YOK.  (adim: %s)\n"
    "   Etkisiz sayilan haller: satir SILINMIS · YORUMA alinmis · `--help`/`-h`/\n"
    "   `--version` ile cagrilmis · `echo` MENSIYONUNA cevrilmis · `|| true` /\n"
    "   `continue-on-error: true` / `if: false` / `set +e` ile etkisizlestirilmis.\n"
    "   NEDEN BAGIMSIZ SURECTEN OLCULUR: bu iddianin sahibi ci-kapsam-test.py'dir ve\n"
    "   kendi nobetcisi KENDI surecinde yasar; iki adimi birden silen bir mutasyonda o\n"
    "   surec HIC kosmaz. Bu kapi AYRI bir CI adimidir -> o halde de konusur.%s")


def _on_dugumu(govde):
    """(on_dugumu, kullanilan_anahtar) — YAML 1.1'de ciplak `on:` BOOLEAN True'ya
    cozulur; `"on"` tirnakli yazim dizedir. Ikisi de gecerlidir."""
    for a in ON_ANAHTARLARI:
        if a in govde:
            return govde[a], a
    return None, None


def tetikleyici_var(govde, ad):
    """<ad> tetikleyicisi `on` dugumunun DOGRUDAN ALTINDA var mi (AYRISTIRILMIS AGAC).

    🔴 METIN ARAMASI DEGIL AGAC SORGUSU: delik 2 tam olarak "metin geciyor ama agacta
    baska yerde" haliydi (`on.workflow_dispatch.inputs.push`). Desteklenen GitHub
    yazimlari:
        on: push                 -> dize
        on: [push, workflow_dispatch]  -> liste
        on: {push: {...}, ...}   -> mapping (en yaygin)
    Bilinmeyen bir govde tipinde FAIL-CLOSED (False) doner: "olculemedi" YESIL sayilmaz.
    """
    dugum, _anahtar = _on_dugumu(govde)
    if dugum is None:
        return False
    if isinstance(dugum, dict):
        return ad in dugum
    if isinstance(dugum, (list, tuple)):
        return ad in dugum
    if isinstance(dugum, str):
        return dugum.strip() == ad
    return False


def _on_alt_anahtarlari(govde):
    dugum, _ = _on_dugumu(govde)
    if isinstance(dugum, dict):
        return ", ".join(repr(a) for a in dugum) or "(bos mapping)"
    if isinstance(dugum, (list, tuple)):
        return ", ".join(repr(a) for a in dugum) or "(bos liste)"
    if dugum is None:
        return "(`on` anahtari YOK)"
    return repr(dugum)


def bolum_e(dizin):
    """(hatalar, olculen_iddia_sayisi) — deploy.yml tetikleyicisi + zorunlu kapi adimlari."""
    yol = os.path.join(dizin, E_DOSYA)
    if not os.path.exists(yol):
        return ["TETIKLEYICI/ZORUNLU ADIM NOBETI: %s bulunamadi (%s) -> ana yayin is "
                "akisi kalkmis, olcum yapilamadi (fail-closed KIRMIZI)"
                % (E_DOSYA, yol)], 0
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    govde, hata = ayristir(metin)
    if hata or not isinstance(govde, dict):
        # Bicim hatasi BOLUM A'nin isi; burada IKINCI kez raporlanmaz (0 iddia olculdu).
        return [], 0
    hatalar = []
    iddia = 0
    for ad in E_TETIKLEYICILER:
        iddia += 1
        if not tetikleyici_var(govde, ad):
            hatalar.append(E_TETIKLEYICI_TANI
                           % (E_DOSYA, ad, _on_alt_anahtarlari(govde)))
    for kapi, bayrak, etiket in E_ZORUNLU_CAGRILAR:
        iddia += 1
        etkili = []
        reddedilen = []
        for _j, _i, _ad, satir, sebep in etkili_kapi_cagrilari(metin, kapi):
            hukum, _s, argumanlar = SUZGEC.anlamli_cagri(satir, kapi)
            if sebep or hukum == SUZGEC.HAYIR:
                reddedilen.append((satir, "; ".join(sebep) or "anlamsiz cagri"))
                continue
            # argumanlar None (OLCULEMEDI) -> bayrak sorgulanamaz, KABUL (fail-open)
            if argumanlar is None:
                etkili.append(satir)
                continue
            if bayrak is None and bayrak_disi(argumanlar):
                etkili.append(satir)
            elif bayrak is not None and bayrak in argumanlar:
                etkili.append(satir)
            else:
                reddedilen.append((satir, "bayrak beklentisi tutmadi (aranan %r, "
                                          "bulunan %r)" % (bayrak, argumanlar)))
        if not etkili:
            ek = ""
            if reddedilen:
                ek = "\n   REDDEDILEN ADAY(LAR): " + " | ".join(
                    "%r -> %s" % (k[:80], s) for k, s in reddedilen[:3])
            hatalar.append(E_ZORUNLU_TANI % (
                E_DOSYA, kapi, (" %s" % bayrak) if bayrak else " (BAYRAKSIZ)",
                etiket, ek))
    return hatalar, iddia


# E_ZORUNLU_CAGRILAR'daki "bayrak None" hali: cagri, LISTEDEKI DIGER zorunlu
# bayraklarin HICBIRINI tasimamali (yani ana/bayraksiz kolu kosuyor olmali).
# `--deploy <yol>` gibi girdi seçen bayraklar kolu DEGISTIRMEZ -> gecerli sayilir.
E_KOL_BAYRAKLARI = frozenset(b for _y, b, _e in E_ZORUNLU_CAGRILAR if b)


def bayrak_disi(argumanlar):
    """<argumanlar> hicbir KOL bayragi tasimiyor mu (yani ana kol kosuluyor mu)."""
    return not (set(argumanlar) & E_KOL_BAYRAKLARI)


# ---------------------------------------------------------------------------
# BOLUM C — KENDINI TEST (ARIZA ENJEKSIYONU; bayraksiz kolda BLOKLAYICI)
# ---------------------------------------------------------------------------
# Sentetik fikstur: GECERLI ama "alisilmadik" bir is akisi. Sentetik olmasi SART —
# gercek dosyalarin icerigi degistikce nobetci bayatlamasin.
GECERLI_ORNEK = """\
name: "Sentetik: gecerli is akisi"

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  UZUN: "deger"
  IKINCI: 3

jobs:
  temel: &ortak
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: "Turkce + emoji: sicak ogun cigdem 🚀 (2-renk: -D)"
        if: ${{ github.ref == 'refs/heads/main' && !cancelled() }}
        env:
          COK: |
            satir1
            satir2
        run: |
          echo "cok satirli"
          python3 -c 'print(1)'
          echo bitti   # satir sonu yorumu
      - name: Katlanan blok
        run: >-
          echo tek
          satira
  klon:
    <<: *ortak
  matrisli:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest]
        surum: ["20", "22"]
    steps:
      - run: echo "${{ matrix.surum }}"
"""

# Mutasyon capasi: matrisli job'un TEK adimi (fikstur icinde biricik satir).
SON_ADIM = '      - run: echo "${{ matrix.surum }}"'

# Ariza enjeksiyonu fiksturleri: (ad, metin, beklenen_hata_alt_dizesi)
BOZUK_ORNEKLER = (
    # 1) BUGUNKU GERCEK OLAY: tirnaksiz adim adinda ": " -> plain scalar ayristirma hatasi.
    ("gercek olay — tirnaksiz adim adinda \": \"",
     GECERLI_ORNEK.replace(
         '      - name: "Turkce + emoji: sicak ogun cigdem 🚀 (2-renk: -D)"',
         "      - name: Turkce + emoji: sicak ogun cigdem 🚀 (2-renk: -D)"),
     "AYRISTIRMA HATASI"),
    # 2) PyYAML'in KENDISI bunu sessizce yer -> ozel Loader olmasa YESIL gecerdi.
    ("tekrarlanan anahtar (`runs-on` iki kez)",
     GECERLI_ORNEK.replace("    runs-on: ubuntu-latest",
                           "    runs-on: ubuntu-latest\n    runs-on: ubuntu-22.04", 1),
     "TEKRARLANAN ANAHTAR"),
    ("bos `run:`", GECERLI_ORNEK.replace(SON_ADIM, "      - run:"), "`run:` BOS"),
    ("`on:` blogu yok",
     GECERLI_ORNEK.replace("on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n",
                           ""),
     "`on:` tetikleyicisi YOK"),
    ("`jobs:` yok", GECERLI_ORNEK.split("jobs:")[0], "`jobs:` YOK"),
    # 6) GIRINTI: adim listesi bir seviye kaydirilinca blok mapping cakisir.
    ("girinti bozuk (adim tiresi kaydi)",
     GECERLI_ORNEK.replace("    steps:\n      - uses: actions/checkout@v4",
                           "    steps:\n      uses: actions/checkout@v4", 1),
     "AYRISTIRMA HATASI"),
    # 7) YAPISAL girinti: `steps` liste yerine skalar -> ayristirma GECER, iskelet BOZUK.
    ("`steps` liste degil (skalar)",
     GECERLI_ORNEK.replace("    steps:\n" + SON_ADIM + "\n", "    steps: bozuk\n"),
     "liste DEGIL"),
    # 8) Adimda ne `run` ne `uses` -> GitHub "workflow file issue".
    ("adimda ne `run` ne `uses`",
     GECERLI_ORNEK.replace(SON_ADIM, "      - name: bos adim"),
     "ne `run` ne `uses`"),
    # 9) TAB karakteri: YAML girintide TAB KABUL ETMEZ (klasik startup_failure).
    ("girintide TAB karakteri",
     GECERLI_ORNEK.replace("    runs-on: ${{ matrix.os }}",
                           "\truns-on: ${{ matrix.os }}", 1),
     "AYRISTIRMA HATASI"),
)

# B ekseni ariza enjeksiyonu: gercek cagri satiri uzerinde 3 etkisizlestirme.
B_ORNEK_CAGRI = "python3 " + B_HEDEF + " --url http://127.0.0.1:18080"
B_FIKSTUR = """\
name: "Sentetik cagri fiksturu"
on: workflow_dispatch
jobs:
  imaj:
    runs-on: ubuntu-latest
    steps:
      - name: Imaj duman testi
        run: |
          echo hazir
          %s
          docker stop x
""" % B_ORNEK_CAGRI

B_MUTANTLAR = (
    ("cagri SILINDI", B_FIKSTUR.replace("          %s\n" % B_ORNEK_CAGRI, "")),
    ("cagri YORUMA alindi", B_FIKSTUR.replace("          %s" % B_ORNEK_CAGRI,
                                              "          # %s" % B_ORNEK_CAGRI)),
    ("cagriya `|| true` eklendi", B_FIKSTUR.replace("          %s" % B_ORNEK_CAGRI,
                                                    "          %s || true" % B_ORNEK_CAGRI)),
    # `|| :` — kabugun "hicbir sey yap, 0 don" komutu. Bu bicim ILK YAZIMDA KACIYORDU
    # (B_ETKISIZ'de `\b` kullanilmisti); nobetci olarak KALIR ki geri gelmesin.
    ("cagriya `|| :` eklendi", B_FIKSTUR.replace("          %s" % B_ORNEK_CAGRI,
                                                 "          %s || :" % B_ORNEK_CAGRI)),
    ("job'a `continue-on-error: true`",
     B_FIKSTUR.replace("    runs-on: ubuntu-latest",
                       "    runs-on: ubuntu-latest\n    continue-on-error: true")),
    ("adima `continue-on-error: true`",
     B_FIKSTUR.replace("      - name: Imaj duman testi",
                       "      - name: Imaj duman testi\n        continue-on-error: true")),
    # --- 30 Tem (O1): curutme turunda SESSIZ gecen bicimler nobetci olarak PINLENDI.
    ("`echo ` ile MENSIYONA cevrildi",
     B_FIKSTUR.replace("          %s" % B_ORNEK_CAGRI,
                       "          echo %s" % B_ORNEK_CAGRI)),
    ("cagriya `|| exit 0` eklendi",
     B_FIKSTUR.replace("          %s" % B_ORNEK_CAGRI,
                       "          %s || exit 0" % B_ORNEK_CAGRI)),
    ("ayni blokta ONCE `set +e`",
     B_FIKSTUR.replace("          echo hazir", "          echo hazir\n          set +e")),
    ("adima DAIMA-YANLIS `if: ${{ false }}`",
     B_FIKSTUR.replace("      - name: Imaj duman testi",
                       "      - name: Imaj duman testi\n        if: ${{ false }}")),
)

# B-JETON/YARDIM ekseni: iddia JETON istedigi zaman `--help` ve eksik alt-komut
# mutasyonlari OLU sayilmali. Sentetik iddia gercek bir betige capalanir (repoda VAR)
# ama fikstur METNI sentetiktir.
B_JETON_IDDIA = BIddia("sentetik-jeton", "tools/onizleme-kapisi.py",
                       ("duman", "--url"), ("workflow_dispatch",), "sentetik olcum")
B_JETON_TABAN = ("python3 tools/onizleme-kapisi.py duman "
                 "--url http://127.0.0.1:18080")
B_JETON_FIKSTUR = """\
name: "Sentetik jeton fiksturu"
on: workflow_dispatch
jobs:
  imaj:
    runs-on: ubuntu-latest
    steps:
      - name: Imaj duman testi
        run: |
          %s
"""
B_JETON_MUTANTLAR = (
    ("`--help` eklendi", B_JETON_TABAN + " --help"),
    ("`-h` eklendi", B_JETON_TABAN.replace(" --url", " -h --url")),
    ("zorunlu alt-komut (`duman`) dusuruldu",
     B_JETON_TABAN.replace(" duman ", " ")),
    ("zorunlu bayrak (`--url`) dusuruldu",
     "python3 tools/onizleme-kapisi.py duman"),
)

# B-TETIK ekseni: `on:` tetikleyicisi degisince is ELLE tetiklenemez -> tum adimlar oto.
B_TETIK_MUTANTLAR = (
    ("workflow_dispatch -> workflow_call",
     B_FIKSTUR.replace("on: workflow_dispatch", "on: workflow_call")),
    ("`on:` yalniz push",
     B_FIKSTUR.replace("on: workflow_dispatch", "on:\n  push:\n    branches: [main]")),
)

# ---- D ekseni ariza enjeksiyonu fiksturleri --------------------------------
#
# 🔴 BEYAN EDILMIS SINIR — `python3 -u <yol>` / `env X=1 python3 <yol>` FORMLARI
# BOLUM D'DE GORUNMEZ (bu turda OLCULDU, bu fikstur listesinin kendi bulgusu):
# Bolum D'nin ADAY capasi ci-kapsam-test.py'nin `_onek_re`'sidir ve `^python3\\s+<yol>`
# ister. `run: python3 -u tools/kisisel-veri-test.py` bu capaya UYMAZ -> Bolum D o
# satirda 0 cagri gorur ve (fail-OPEN) SUSAR. Capa BILEREK genisletilmedi:
#   (a) Kapsam ekseni ZATEN konusuyor: ayni daralik `kosulan()` icinde de vardir ->
#       o yol "kosulmuyor" sayilir, KAPSAMSIZ olur ve ci-kapsam-test.py KIRMIZI yanar.
#       Yani depo bu formda korumasiz DEGIL; yalniz teshis Bolum D'den degil kapsam
#       kapisindan gelir. (Ayrica ci-kapsam-test.py'nin T8 `sayilamayan_python3`
#       UYARISI bu formlari zaten "bare forma cevir" diye isaretler.)
#   (b) Capayi genisletmek POZITIF ekseni de genisletirdi ([[kapi-kapsam-eksen-secimi]]):
#       `kosulan()` sayisi degisir, muafiyetler bayatlar ve tek bir yanlis-pozitif
#       TUM ekibin yayinini durdurur. Bu turun sinirinda o risk alinmadi.
# Ortak suzgecin KENDISI bu formu DOGRU cozer (ci-kapsam-test.py SUZGEC_FIKSTURLERI:
# `python3 -u tools/zzz-sentetik-test.py` -> EVET), yani eksik CAPADA, hukumde degil.
#
# Hedef kapi yolu SENTETIK degil GERCEK olmali (capa ci-kapsam-test.py kesfinden gelir),
# ama fikstur METNI sentetiktir -> gercek dosyalarin icerigi degistikce bayatlamaz.
D_HEDEF = "tools/kisisel-veri-test.py"
D_CAGRI = "python3 " + D_HEDEF
D_FIKSTUR = """\
name: "Sentetik D fiksturu"
on: workflow_dispatch
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: "Kapi: kisisel veri"
        run: %s
      - name: Bilincli fail-open — kapi KOSMAZ (mesru)
        continue-on-error: true
        run: |
          python3 tools/d1-sync.py
          npx wrangler@4 containers push x 2> log || true
""" % D_CAGRI

# (ad, metin, cagri_ETKISIZ_olmali_mi)
D_MUTANTLAR = (
    ("adima `continue-on-error: true`",
     D_FIKSTUR.replace('      - name: "Kapi: kisisel veri"',
                       '      - name: "Kapi: kisisel veri"\n        continue-on-error: true'),
     True),
    ("job'a `continue-on-error: true`",
     D_FIKSTUR.replace("    runs-on: ubuntu-latest",
                       "    runs-on: ubuntu-latest\n    continue-on-error: true"),
     True),
    ("komuta `|| true`",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: %s || true\n" % D_CAGRI), True),
    # ⚠️ `|| :` BLOK skalarda yazilir: `run: foo || :` YAML'da GECERSIZDIR (satir sonundaki
    # `:` mapping gostergesidir) -> inline yazim ayristirma hatasi verir ve mutasyon
    # "cagri bulunamadi" ile karisirdi (olculdu: bulgu=[]). Gercek dunyada da bu bicim
    # ancak blok/tirnakli skalarda yazilabilir.
    ("komuta `|| :` (blok skalar)",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: |\n          %s || :\n" % D_CAGRI), True),
    ("komuta `|| exit 0`",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: %s || exit 0\n" % D_CAGRI), True),
    ("adima `if: false`",
     D_FIKSTUR.replace('      - name: "Kapi: kisisel veri"',
                       '      - name: "Kapi: kisisel veri"\n        if: false'), True),
    ("adima `if: ${{ false }}`",
     D_FIKSTUR.replace('      - name: "Kapi: kisisel veri"',
                       '      - name: "Kapi: kisisel veri"\n'
                       "        if: ${{ false }}"), True),
    ("job'a `if: false`",
     D_FIKSTUR.replace("    runs-on: ubuntu-latest",
                       "    runs-on: ubuntu-latest\n    if: false"), True),
    ("ayni blokta ONCE `set +e`",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: |\n          set +e\n          %s\n" % D_CAGRI), True),
    # --- YANLIS-POZITIF KANARYALARI: etkisiz SAYILMAMALI ---
    ("MESRU `if:` ifadesi (daima-yanlis DEGIL)",
     D_FIKSTUR.replace('      - name: "Kapi: kisisel veri"',
                       '      - name: "Kapi: kisisel veri"\n'
                       "        if: ${{ github.ref == 'refs/heads/main' }}"), False),
    ("`|| exit 1` (MESRU: hata yayilir)",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: %s || exit 1\n" % D_CAGRI), False),
    ("ayni blokta `set +e` SONRA `set -e` (geri acilmis)",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: |\n          set +e\n          echo x\n"
                       "          set -e\n          %s\n" % D_CAGRI), False),
    ("`|| true` BASKA satirda (ayni adimda, kapi satiri temiz)",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: |\n          docker stop x || true\n"
                       "          %s\n" % D_CAGRI), False),
    ("continue-on-error BASKA adimda (kapi adimi temiz)",
     D_FIKSTUR, False),
    # --- ICRA-DISI BAYRAK (30 Tem, DELIK 1): adim GORUNUR, exit 0, olcum KOSMAZ ---
    ("cagri `--help`'e cevrildi (DELIK 1)",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: %s --help\n" % D_CAGRI), True),
    ("cagri `-h`'ye cevrildi",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: %s -h\n" % D_CAGRI), True),
    ("cagri `--version`'a cevrildi",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: %s --version\n" % D_CAGRI), True),
    # --- YANLIS-POZITIF KANARYALARI: MESRU bayrak/yazim etkisiz SAYILMAMALI ---
    ("`--kendini-test` (MESRU: olcumun ta kendisi)",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: %s --kendini-test\n" % D_CAGRI), False),
    ("`--deploy <yol>` (MESRU: girdi seçer, olcum kosar)",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: %s --deploy /tmp/x.yml\n" % D_CAGRI), False),
    ("`\\` satir devami (MESRU coksatir yazim)",
     D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                       "        run: |\n          %s \\\n            --kendini-test\n"
                       % D_CAGRI), False),
)

# ---- E ekseni ariza enjeksiyonu fiksturleri --------------------------------
# `on` dugumu SENTETIK bir is akisi uzerinde sinanir -> gercek deploy.yml degistikce
# bayatlamaz. E_HEDEF gercek bir kapi yolu olmak ZORUNDA (E_ZORUNLU_CAGRILAR'dan gelir).
E_FIKSTUR_TEMIZ = """\
name: "Sentetik E fiksturu"

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: "CI kapsam kapisi"
        run: python3 tools/ci-kapsam-test.py
      - name: "CI kapsam kapisi oz-nobetcileri"
        run: python3 tools/ci-kapsam-test.py --kendini-test
"""

# (ad, metin, KIRMIZI_olmali_mi)
E_MUTANTLAR = (
    ("gercek `on.push` silindi, `workflow_dispatch.inputs.push` SAHTE (DELIK 2)",
     E_FIKSTUR_TEMIZ.replace(
         "on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n",
         "on:\n  workflow_dispatch:\n    inputs:\n      push:\n"
         '        description: "sahte push girdisi"\n        required: false\n'), True),
    ("`on` govdesi bos mapping",
     E_FIKSTUR_TEMIZ.replace(
         "on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n",
         "on:\n  workflow_dispatch:\n"), True),
    ("bayraksiz kapsam adimi `--help`'e cevrildi (DELIK 1)",
     E_FIKSTUR_TEMIZ.replace("        run: python3 tools/ci-kapsam-test.py\n",
                             "        run: python3 tools/ci-kapsam-test.py --help\n"),
     True),
    ("bayraksiz kapsam ADIMI butunuyle silindi (DELIK 4)",
     E_FIKSTUR_TEMIZ.replace('      - name: "CI kapsam kapisi"\n'
                             "        run: python3 tools/ci-kapsam-test.py\n", ""), True),
    ("oz-nobetci cagrisi `echo` MENSIYONUNA cevrildi (DELIK 3)",
     E_FIKSTUR_TEMIZ.replace(
         "        run: python3 tools/ci-kapsam-test.py --kendini-test\n",
         "        run: echo python3 tools/ci-kapsam-test.py --kendini-test\n"), True),
    ("oz-nobetci adimina `continue-on-error: true`",
     E_FIKSTUR_TEMIZ.replace('      - name: "CI kapsam kapisi oz-nobetcileri"\n',
                             '      - name: "CI kapsam kapisi oz-nobetcileri"\n'
                             "        continue-on-error: true\n"), True),
    # --- YANLIS-POZITIF KANARYALARI: MESRU yazim KIRMIZI YANMAMALI ---
    ("`on: [push, workflow_dispatch]` liste yazimi (MESRU)",
     E_FIKSTUR_TEMIZ.replace("on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n",
                             "on: [push, workflow_dispatch]\n"), False),
    ('`"on":` tirnakli anahtar (MESRU)',
     E_FIKSTUR_TEMIZ.replace("on:\n  push:", '"on":\n  push:'), False),
    ("`on.push` EK anahtarlarla (paths-ignore) (MESRU)",
     E_FIKSTUR_TEMIZ.replace("    branches: [main]\n",
                             "    branches: [main]\n    paths-ignore: ['**.md']\n"), False),
    ("bayraksiz adima MESRU `if:` ifadesi (MESRU)",
     E_FIKSTUR_TEMIZ.replace('      - name: "CI kapsam kapisi"\n',
                             '      - name: "CI kapsam kapisi"\n'
                             "        if: ${{ github.ref == 'refs/heads/main' }}\n"),
     False),
    ("bayraksiz adima `continue-on-error: false` (MESRU: acik bloklayici beyan)",
     E_FIKSTUR_TEMIZ.replace('      - name: "CI kapsam kapisi"\n',
                             '      - name: "CI kapsam kapisi"\n'
                             "        continue-on-error: false\n"), False),
    ("iki adim AYRI job'lara tasindi (MESRU)",
     E_FIKSTUR_TEMIZ.replace(
         '      - name: "CI kapsam kapisi oz-nobetcileri"\n'
         "        run: python3 tools/ci-kapsam-test.py --kendini-test\n",
         "  ikinci:\n    runs-on: ubuntu-latest\n    steps:\n"
         '      - name: "CI kapsam kapisi oz-nobetcileri"\n'
         "        run: python3 tools/ci-kapsam-test.py --kendini-test\n"), False),
)

# Bolum A ucdan-uca fiksturu: bolum_a() GERCEK bir dizinden okuyup hatalari
# TOPLUYOR mu (govde `hatalar.extend(...)` yerine ciplak cagriya cevrilirse duser).
A_UCTAN_UCA_BOZUK = GECERLI_ORNEK.replace(
    '      - name: "Turkce + emoji: sicak ogun cigdem 🚀 (2-renk: -D)"',
    "      - name: Turkce + emoji: sicak ogun cigdem 🚀 (2-renk: -D)")

# Alt-surec ozyineleme kilidi: main()'in CIKIS KODU ucdan uca olculurken kapi kendini
# alt-surec olarak cagirir. Cocuk bu degiskeni gorunce AYNI iddiayi ATLAR (aksi halde
# sonsuz ozyineleme). Tek seviye derinlik yeter.
ALT_SUREC_BAYRAGI = "PRUVO_IS_AKISI_ALT_SUREC"

MAIN_CIKIS_TANI = (
    "MAIN CIKIS KODU NOBETI KIRMIZI: hata VARKEN main() 1 DONMUYOR (olculen rc=%r).\n"
    "   OLCULDU (30 Tem, bu kapinin KENDI mutasyon turu): main()'deki "
    "`return 1` -> `return 0` yapilinca kapi 'SONUC: KIRMIZI ❌' YAZIYOR ama SUREC 0 ile\n"
    "   cikiyordu -> CI adimi YESIL yanar, kapi tamamen OLU olur ve hicbir nobetci\n"
    "   konusmazdi (hem bayraksiz hem --kendini-test kolu rc=0 olculdu).\n"
    "   GERI KOY: main() icinde hatalar varken `return 1`.")

MAIN_AST_TANI = (
    "MAIN CIKIS KODU (AST) NOBETI KIRMIZI: main() govdesinde `return 1` (sabit 1 donusu) "
    "YOK.\n   Metin capasi DEGIL, AST olcumu ([[kapi-anchor-coupling-ikilemi]]: "
    "anchor-BAGIMSIZ olcum tercih edilir).\n"
    "   GERI KOY: hatalar varken `return 1`.")


def _cikis_yolu_kirmizi(tanilar):
    """main()'in CIKIS YOLU suclu oldugunda kullanilan TEK cikis: teshisi bas ve
    sureci DOGRUDAN 1 ile sonlandir (main()'in `return`'une GUVENMEDEN).

    🔴 KABUL EDILEN SINIR (sonsuz geriye gidis burada KESILIR — oz_cagri_kontrol() ile
    ayni beyan): bu fonksiyonun KENDI `sys.exit(1)` satirini de degistiren IKI ADIMLI bir
    mutasyon kacar. Tek-adimli mutasyon (`return 1` -> `return 0`) kapsanir."""
    print("IS AKISI KAPISI — CIKIS YOLU NOBETI")
    for t in tanilar:
        print("  ❌ " + t)
    print("SONUC: KIRMIZI ❌  (cikis yolu suclu -> main() return'une guvenilmedi)")
    sys.exit(1)


def _main_ast_return1_var():
    """main() govdesinde sabit `return 1` var mi (AST). (ok, tani_listesi)."""
    try:
        with open(os.path.abspath(__file__), encoding="utf-8") as f:
            agac = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        return False, ["MAIN CIKIS KODU (AST) OLCULEMEDI: kendi kaynagi "
                       "ayristirilamadi (%s)" % e]
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef) and dugum.name == "main"):
            continue
        for alt in ast.walk(dugum):
            if isinstance(alt, ast.Return) and isinstance(alt.value, ast.Constant) \
                    and alt.value.value == 1 and not isinstance(alt.value.value, bool):
                return True, []
        return False, [MAIN_AST_TANI]
    return False, ["MAIN CIKIS KODU (AST) OLCULEMEDI: main() bulunamadi"]


def kendini_test():
    """(hatalar, calisan_iddia_sayisi) — kapinin OLCUM GOVDELERI gercekten olcuyor mu.

    GOVDE NO-OP OLURSA KIRMIZI: bicim_hatalari() `return []` yapilirsa 6 bozuk
    fiksturun HICBIRI hata uretmez -> 6 iddia birden duser. etkili_cagrilar()
    `return []` yapilirsa POZITIF iddia duser; `return [1]` gibi sabit donerse 4
    mutant iddiasi birden duser. Yani hem sessiz-yesil hem sabit-donus kapatilir."""
    hatalar = []
    iddia = 0

    # A-POZITIF: gecerli ama ALISILMADIK YAML (anchor/alias, matrix, `if:` ifadesi,
    # cok satirli `run: |`, katlanan `>-`, uzun `env:`, Turkce karakter, emoji,
    # satir sonu yorumu) YANMAMALI. Yanma = tum ekibin yayini durur.
    iddia += 1
    pozitif = bicim_hatalari("sentetik-gecerli.yml", GECERLI_ORNEK)
    if pozitif:
        hatalar.append("A-POZITIF YANDI (YANLIS-POZITIF): gecerli sentetik is akisi %d hata "
                       "uretti -> %s" % (len(pozitif), " ; ".join(pozitif)))

    # A-NEGATIF: her bozuk fikstur KIRMIZI olmali VE dogru taniyi vermeli.
    for ad, metin, beklenen in BOZUK_ORNEKLER:
        iddia += 1
        bulgu = bicim_hatalari("sentetik-bozuk.yml", metin)
        if not bulgu:
            hatalar.append("A-NEGATIF SESSIZ: %r mutasyonu hic hata uretmedi "
                           "(olcum govdesi no-op mu?)" % ad)
        elif not any(beklenen in h for h in bulgu):
            hatalar.append("A-NEGATIF TANI KAYDI: %r icin %r bekleniyordu, gelen: %s"
                           % (ad, beklenen, " ; ".join(bulgu)))

    # B-POZITIF: sentetik fiksturde cagri ETKILI sayilmali.
    iddia += 1
    if len(etkili_cagrilar(B_FIKSTUR)) != 1:
        hatalar.append("B-POZITIF BOZUK: sentetik fiksturde tam 1 etkili cagri bekleniyordu, "
                       "%d bulundu -> capa (B_ONEK) bozulmus"
                       % len(etkili_cagrilar(B_FIKSTUR)))

    # B-NEGATIF: etkisizlestirme bicimlerinin HEPSI 0 etkili cagri vermeli.
    for ad, metin in B_MUTANTLAR:
        iddia += 1
        n = len(etkili_cagrilar(metin))
        if n != 0:
            hatalar.append("B-NEGATIF SESSIZ: %r mutasyonundan sonra cagri HALA etkili "
                           "sayildi (%d) -> nobetci bu bicimde OLU" % (ad, n))

    # B-JETON-POZITIF: zorunlu jetonlar tamken cagri ETKILI sayilmali.
    iddia += 1
    if len(etkili_cagrilar(B_JETON_FIKSTUR % B_JETON_TABAN, B_JETON_IDDIA)) != 1:
        hatalar.append("B-JETON-POZITIF BOZUK: tam jetonlu sentetik cagri ETKILI "
                       "sayilmadi -> jeton sarti asiri dar (yanlis-pozitif riski)")

    # B-JETON-NEGATIF: `--help` / eksik alt-komut / eksik bayrak -> 0 etkili cagri.
    for ad, satir in B_JETON_MUTANTLAR:
        iddia += 1
        n = len(etkili_cagrilar(B_JETON_FIKSTUR % satir, B_JETON_IDDIA))
        if n != 0:
            hatalar.append("B-JETON-NEGATIF SESSIZ: %r mutasyonundan sonra cagri HALA "
                           "etkili sayildi (%d) -> `--help`/eksik alt-komut bu bicimde "
                           "kaciyor (curutme turunda olculmus delik)" % (ad, n))

    # B-TETIK-POZITIF/NEGATIF: `on:` tetikleyicisi nobeti canli mi.
    iddia += 1
    t_hata, _ = b_iddia_hatalari(B_FIKSTUR, B_IDDIALAR[0])
    if any("TETIKLEYICI NOBETI" in h for h in t_hata):
        hatalar.append("B-TETIK-POZITIF YANDI: workflow_dispatch tasiyan gecerli fikstur "
                       "tetikleyici nobetini KIRMIZI yakti (yanlis-pozitif)")
    for ad, metin in B_TETIK_MUTANTLAR:
        iddia += 1
        m_hata, _ = b_iddia_hatalari(metin, B_IDDIALAR[0])
        if not any("TETIKLEYICI NOBETI" in h for h in m_hata):
            hatalar.append("B-TETIK-NEGATIF SESSIZ: %r mutasyonu tetikleyici nobetini "
                           "KIRMIZI yakmadi -> is elle tetiklenemez hale getirilebilir "
                           "ve tum kapi adimlari sessizce olur" % ad)

    # B-CAPRAZ MEKANIZMASI (O6): muafiyet <-> iddia kilidi GERCEKTEN olcuyor mu.
    # Bu iddia gercek dosyalara DOKUNMAZ; b_capraz_hatalari()'nin GOVDESINI sentetik
    # girdilerle surer (ayni fonksiyon, ikinci kopya YOK).
    iddia += 2
    _yedek = dict(B_MUAFIYET_DAYANAGI)
    try:
        B_MUAFIYET_DAYANAGI.clear()
        B_MUAFIYET_DAYANAGI["tools/kesinlikle-muaf-olmayan-dosya.py"] = ("iki-govde",)
        if not any("artik ci-kapsam-test.py IZIN_LISTESI'nde DEGIL" in h
                   for h in b_capraz_hatalari()):
            hatalar.append("B-CAPRAZ B5a OLU: IZIN_LISTESI'nde OLMAYAN bir yol icin "
                           "iddia tutulmasi KIRMIZI yakmadi")
        B_MUAFIYET_DAYANAGI.clear()
        B_MUAFIYET_DAYANAGI["tools/onizleme-kapisi.py"] = ("hic-olmayan-iddia-kimligi",)
        if not any("MAKINE DAYANAGI dusmus" in h for h in b_capraz_hatalari()):
            hatalar.append("B-CAPRAZ B5b OLU: muafiyetin dayandigi B iddiasi SILINDIGI "
                           "halde KIRMIZI yanmadi -> gerekce sessizce bayatlayabilir")
    finally:
        B_MUAFIYET_DAYANAGI.clear()
        B_MUAFIYET_DAYANAGI.update(_yedek)

    # ---- A-UCTAN-UCA: bolum_a() GERCEK bir dizinden okuyup HATALARI TOPLUYOR mu.
    # OLCULEN KACAK (30 Tem): bolum_a() icindeki `hatalar.extend(bicim_hatalari(...))`
    # ciplak cagriya (`bicim_hatalari(...)`) cevrilince TUM A ekseni sessizce olurdu ve
    # yukaridaki A iddialari (bicim_hatalari()'ni DOGRUDAN cagirdiklari icin) HABERSIZ
    # kaliyordu -> kapi rc=0. Bu iddia govdeye DEGIL bolum_a()'nin CIKTISINA bakar.
    iddia += 2
    gecici = tempfile.mkdtemp(prefix="pruvo-isakisi-oz-")
    try:
        with open(os.path.join(gecici, "bozuk.yml"), "w", encoding="utf-8") as f:
            f.write(A_UCTAN_UCA_BOZUK)
        bozuk_hata, bozuk_n = bolum_a(gecici)
        if bozuk_n != 1:
            hatalar.append("A-UCTAN-UCA KESIF BOZUK: gecici dizinde 1 is akisi "
                           "bekleniyordu, bolum_a %d saydi" % bozuk_n)
        if not any("AYRISTIRMA HATASI" in h for h in bozuk_hata):
            hatalar.append("A-UCTAN-UCA SESSIZ: bolum_a() bozuk bir is akisi dosyasi "
                           "icin hata DONDURMEDI (%d hata) -> hatalar TOPLANMIYOR "
                           "(or. `hatalar.extend(...)` ciplak cagriya cevrilmis)"
                           % len(bozuk_hata))
        # POZITIF karsi-kontrol: gecerli dosyada bolum_a SUSMALI (aksi halde yukaridaki
        # iddia "her zaman hata var" diye sahte-yesil olurdu).
        os.remove(os.path.join(gecici, "bozuk.yml"))
        with open(os.path.join(gecici, "gecerli.yml"), "w", encoding="utf-8") as f:
            f.write(GECERLI_ORNEK)
        temiz_hata, _ = bolum_a(gecici)
        if temiz_hata:
            hatalar.append("A-UCTAN-UCA YANLIS-POZITIF: bolum_a() gecerli is akisi icin "
                           "%d hata uretti -> %s" % (len(temiz_hata),
                                                     " ; ".join(temiz_hata)))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    # ---- MAIN CIKIS KODU: iki BAGIMSIZ nobetci (AST + UCTAN UCA alt-surec).
    # 🔴 NEDEN `hatalar`'A EKLENMEZ, DOGRUDAN sys.exit(1) EDILIR (OZ-GONDERME KILIDI):
    # bu iki nobetcinin kolladigi mutasyon main()'in `return 1` YOLUNU bozar. Bulguyu
    # `hatalar`'a koymak ise raporu tam O bozuk yoldan gecirir -> olculdu (30 Tem):
    # `return 1` -> `return 0` mutasyonunda kapi "SONUC: KIRMIZI ❌" YAZIYOR ama surec
    # 0 ile cikiyordu; CI adimi YESIL yanardi. Cikis yolu SUCLUYSA cikis yolu
    # KULLANILAMAZ -> teshis basilir ve surec HEMEN 1 ile sonlanir.
    iddia += 1
    ast_ok, ast_hata = _main_ast_return1_var()
    if not ast_ok:
        _cikis_yolu_kirmizi(ast_hata)

    if os.environ.get(ALT_SUREC_BAYRAGI) != "1":
        iddia += 1
        gecici2 = tempfile.mkdtemp(prefix="pruvo-isakisi-rc-")
        try:
            with open(os.path.join(gecici2, "bozuk.yml"), "w", encoding="utf-8") as f:
                f.write(A_UCTAN_UCA_BOZUK)
            cevre = dict(os.environ)
            cevre[ALT_SUREC_BAYRAGI] = "1"
            r = subprocess.run([sys.executable, os.path.abspath(__file__),
                                "--dizin", gecici2],
                               capture_output=True, text=True, env=cevre, timeout=300)
            rc = r.returncode
        except subprocess.SubprocessError as e:
            rc = None
            hatalar.append("MAIN CIKIS KODU NOBETI OLCULEMEDI: alt surec kosulamadi (%s)"
                           % e)
        finally:
            shutil.rmtree(gecici2, ignore_errors=True)
        if rc is not None and rc != 1:
            _cikis_yolu_kirmizi([MAIN_CIKIS_TANI % rc])

    # ---- D EKSENI: kapi cagrisi etkisizlestirme olcumu -----------------------
    capalar, capa_hata = kapi_capalari()
    if capalar is None:
        iddia += 1
        hatalar.append("D-OLCULEMEDI: kapi kesfi alinamadi -> %s" % capa_hata)
    else:
        d_capalar = [(y, o) for y, o in capalar if y == D_HEDEF]
        iddia += 1
        if not d_capalar:
            hatalar.append("D-CAPA BAYAT: %s artik kesfedilmiyor -> D_HEDEF sabitini "
                           "gercek bir kabul testine guncelle" % D_HEDEF)
        else:
            # D-POZITIF: temiz fiksturde cagri BULUNMALI ve ETKILI olmali. Ayrica
            # MESRU fail-open adimi (continue-on-error + `|| true`, ama KAPI KOSMAZ)
            # hicbir bulgu uretmemeli -> tam 1 cagri, 0 sebep.
            temiz = kapi_cagrilari(D_FIKSTUR, d_capalar)
            if len(temiz) != 1 or temiz[0][5]:
                hatalar.append("D-POZITIF BOZUK: temiz fiksturde tam 1 ETKILI kapi "
                               "cagrisi bekleniyordu, bulunan: %r" % (temiz,))
            for ad, metin, etkisiz_olmali in D_MUTANTLAR:
                iddia += 1
                bulgu = kapi_cagrilari(metin, d_capalar)
                sebepli = [b for b in bulgu if b[5]]
                if etkisiz_olmali and not sebepli:
                    hatalar.append("D-NEGATIF SESSIZ: %r mutasyonundan sonra kapi "
                                   "cagrisi HALA etkili sayildi -> nobetci bu bicimde "
                                   "OLU (bulgu=%r)" % (ad, bulgu))
                if not etkisiz_olmali:
                    if sebepli:
                        hatalar.append("D-YANLIS-POZITIF: %r MESRU yazimi "
                                       "etkisizlestirilmis sayildi -> %s"
                                       % (ad, sebepli[0][5]))
                    if len(bulgu) != 1:
                        hatalar.append("D-YANLIS-POZITIF/CAPA: %r yaziminda tam 1 kapi "
                                       "cagrisi bekleniyordu, %d bulundu"
                                       % (ad, len(bulgu)))
            # D-IZIN MEKANIZMASI: uc kural (gerekce · olculebilir dayanak · bayatlik).
            # D_IZIN bugun BOS oldugu icin mekanizma SENTETIK girislerle sinanir.
            iddia += 4
            hatalar.extend(_d_izin_mekanizma_kontrol())

    # ---- E EKSENI: tetikleyici + zorunlu kapi adimi olcumu --------------------
    # bolum_e() TA KENDISI gecici bir dizinde kosulur (kopya mantik yazilmaz):
    # govdesi no-op yapilirsa (or. `return [], 0`) asagidaki 6 KIRMIZI iddiasi birden
    # duser; asiri agresif yapilirsa 6 YANLIS-POZITIF kanaryasi duser -> iki yonlu.
    gecici3 = tempfile.mkdtemp(prefix="pruvo-isakisi-e-")
    try:
        iddia += 1
        e_yol = os.path.join(gecici3, E_DOSYA)
        with open(e_yol, "w", encoding="utf-8") as f:
            f.write(E_FIKSTUR_TEMIZ)
        temiz_e, temiz_iddia = bolum_e(gecici3)
        if temiz_e:
            hatalar.append("E-POZITIF BOZUK: temiz sentetik fikstur icin bolum_e() %d "
                           "hata uretti -> %s" % (len(temiz_e), " ; ".join(temiz_e)))
        if temiz_iddia != 1 + len(E_ZORUNLU_CAGRILAR):
            hatalar.append("E-IDDIA SAYACI BOZUK: %d bekleniyordu, %d olculdu -> govde "
                           "iddia atlamis olabilir"
                           % (1 + len(E_ZORUNLU_CAGRILAR), temiz_iddia))
        for ad, metin, kirmizi_olmali in E_MUTANTLAR:
            iddia += 1
            with open(e_yol, "w", encoding="utf-8") as f:
                f.write(metin)
            e_bulgu, _ = bolum_e(gecici3)
            if kirmizi_olmali and not e_bulgu:
                hatalar.append("E-NEGATIF SESSIZ: %r mutasyonundan sonra bolum_e() "
                               "HICBIR hata uretmedi -> nobetci bu bicimde OLU" % ad)
            if not kirmizi_olmali and e_bulgu:
                hatalar.append("E-YANLIS-POZITIF: %r MESRU yazimi KIRMIZI yandi -> %s"
                               % (ad, e_bulgu[0].splitlines()[0]))
    finally:
        shutil.rmtree(gecici3, ignore_errors=True)

    # ---- F EKSENI: DIS TUKETICI SOZLESMESI + SATIR DEVAMI ---------------------
    # NEDEN AYRI (olculdu, bu turun oz-koruma mutasyon listesi S15/S16): asagidaki iki
    # mutasyon dort denetciden HICBIRINI kirmizi yakmiyordu ->
    #   S16) `etkili_mensiyon()` govdesi sabit non-bos liste dondurur yapilirsa
    #        jenerator/test/kabul.py TEST 4'un `beyaz` iddiasi DAIMA True olur. Tek
    #        tuketici kabul.py'dir ve o openscad'a bagli oldugu icin CI'da MUAF ->
    #        hicbir kapi konusmaz. Sozlesme BURADA (CI'da kosan kapida) olculur.
    #   S15) `_run_satirlari()` SUZGEC.birlestir_devam yerine duz splitlines() kullanirsa
    #        `\` ile bolunmus MESRU bir kapi cagrisi YARIM gorunur; bugun deploy.yml'de
    #        oyle bir satir olmadigi icin degisiklik SESSIZ kalir ve bir sonraki mesru
    #        coksatir yazimda SAHTE KIRMIZI olarak geri doner.
    F_MENSIYON_FIKSTUR = """\
name: "Sentetik F fiksturu"
on: workflow_dispatch
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: "Varlik kopyasi"
        run: |
          cp jenerator/zzz-sentetik.js _site/jenerator/
          echo cp jenerator/zzz-mensiyon.js _site/jenerator/
          # cp jenerator/zzz-yorum.js _site/jenerator/
      - name: "Satir devamli kapi cagrisi"
        run: |
          python3 tools/kisisel-veri-test.py \\
            --kendini-test
"""
    for varlik, bulunmali, etiket in (
            ("jenerator/zzz-sentetik.js", True, "GERCEK `cp` argumani ETKILI"),
            ("jenerator/zzz-mensiyon.js", False, "`echo` icindeki mensiyon ETKILI DEGIL"),
            ("jenerator/zzz-yorum.js", False, "kabuk YORUMU ETKILI DEGIL")):
        iddia += 1
        bulundu = bool(etkili_mensiyon(F_MENSIYON_FIKSTUR, varlik))
        if bulundu != bulunmali:
            hatalar.append("F-MENSIYON SOZLESMESI BOZUK (%s): %s icin bulundu=%r, "
                           "beklenen %r -> etkili_mensiyon() govdesi no-op/ters yapilmis "
                           "olabilir (tuketici: jenerator/test/kabul.py TEST 4)"
                           % (etiket, varlik, bulundu, bulunmali))
    # SATIR DEVAMI: `\` ile bolunmus cagri TEK satir olarak gorulmeli.
    iddia += 1
    devam_satirlari = [s for _j, _i, _ad, _sb, s in _run_satirlari(F_MENSIYON_FIKSTUR)
                       if "kisisel-veri-test.py" in s]
    if not (len(devam_satirlari) == 1 and "--kendini-test" in devam_satirlari[0]):
        hatalar.append("F-SATIR-DEVAMI BOZUK: `\\` ile bolunmus cagri BIRLESTIRILMEDI "
                       "(bulunan: %r) -> _run_satirlari() SUZGEC.birlestir_devam yerine "
                       "duz splitlines() kullaniyor olabilir; mesru coksatir yazim "
                       "SAHTE KIRMIZI yakar" % (devam_satirlari,))
    return hatalar, iddia


def _d_izin_mekanizma_kontrol():
    """D_IZIN'in KACIS DELIGI OLMAMASINI olcer — bugun liste BOS oldugu icin
    gecici olarak SENTETIK girisler enjekte edilip bolum_d() TA KENDISI kosulur
    (kopya mantik yazilmaz). Sentetik is akisi gecici bir dizine yazilir.

    (i)   gerekce BOS               -> KIRMIZI
    (ii)  dayanak yolu repoda YOK   -> KIRMIZI  (gerekce sessizce bayatlayamaz)
    (iii) gecerli giris             -> etkisizlestirme KABUL EDILIR (o bulgu duser)"""
    global D_IZIN
    hatalar = []
    etkisiz_metin = D_FIKSTUR.replace("        run: %s\n" % D_CAGRI,
                                      "        run: %s || true\n" % D_CAGRI)
    gecici = tempfile.mkdtemp(prefix="pruvo-isakisi-izin-")
    yedek = D_IZIN
    try:
        with open(os.path.join(gecici, B_IS_AKISI), "w", encoding="utf-8") as f:
            f.write(etkisiz_metin)
        anahtar = (B_IS_AKISI, D_HEDEF)

        def olc(izin):
            global D_IZIN
            D_IZIN = izin
            return bolum_d(gecici)

        # TABAN: izin YOK -> etkisizlestirme KIRMIZI konusmali.
        taban, _, taban_etkisiz, _ = olc({})
        if taban_etkisiz != 1 or not any("BEYANSIZ" in h for h in taban):
            hatalar.append("D-IZIN TABANI BOZUK: izinsiz etkisizlestirme KIRMIZI "
                           "konusmadi (etkisiz=%d, hatalar=%r)" % (taban_etkisiz, taban))
        # (iii) gecerli giris -> o bulgu duser (dayanak: bu dosyanin kendisi, hep var).
        gecerli, _, _, izinli = olc({anahtar: ("SENTETIK OLCUM GIRISI — mekanizma testi.",
                                               "tools/is-akisi-kapisi.py")})
        if any("BEYANSIZ" in h for h in gecerli) or izinli != 1:
            hatalar.append("D-IZIN KABULU BOZUK: gerekceli+dayanakli giris bulguyu "
                           "dusurmedi (izinli=%d, hatalar=%r)" % (izinli, gecerli))
        # (i) gerekce BOS -> KIRMIZI
        bos, _, _, _ = olc({anahtar: ("   ", "tools/is-akisi-kapisi.py")})
        if not any("GEREKCESIZ" in h for h in bos):
            hatalar.append("D-IZIN GEREKCE KAPISI OLU: bos gerekce KIRMIZI yakmadi "
                           "(%r)" % (bos,))
        # (ii) dayanak repoda YOK -> KIRMIZI
        bayat, _, _, _ = olc({anahtar: ("Gerekce var ama dayanak yok.",
                                        "tools/olmayan-nobetci-test.py")})
        if not any("DAYANAGI BAYAT" in h for h in bayat):
            hatalar.append("D-IZIN OLCULEBILIR DAYANAK KAPISI OLU: var olmayan nobetci "
                           "yolu KIRMIZI yakmadi (%r)" % (bayat,))
    finally:
        D_IZIN = yedek
        shutil.rmtree(gecici, ignore_errors=True)
    return hatalar


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dizin", default=WORKFLOW_DIZIN,
                    help="is akisi dizini (kirmizi-mutasyon icin gecici kopya verilebilir)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="YALNIZ ariza-enjeksiyon nobetcilerini AYRINTILI raporlar "
                         "(bayraksiz kosumda da BLOKLAYICI olarak kosarlar)")
    args = ap.parse_args()

    if not ayristirici_var():
        print("IS AKISI BICIM KAPISI")
        print(AYRISTIRICI_YOK_TANI)
        print("SONUC: OLCULEMEDI ⚪ (YESIL DEGIL)")
        return OLCULEMEDI

    # 🔴 TEK CAGRI NOKTASI (bilincli, olculdu 30 Tem): kendini_test() main() icinde
    # YALNIZ BURADA cagrilir ve iki kol da bu sonucu kullanir. Eskiden iki ayri cagri
    # vardi ve oz_cagri_kontrol() (AST) `--kendini-test` kolundaki cagriyi gorup tatmin
    # oluyordu -> BLOKLAYICI koldaki cagri silinse bile nobetci SUSUYORDU (olculdu: M7
    # mutasyonu iki kolda da rc=0). Tek cagri noktasi bu delige yer BIRAKMAZ.
    c_hata, c_iddia = kendini_test()

    if args.kendini_test:
        print("IS AKISI KAPISI — ARIZA ENJEKSIYONU (%d iddia)" % c_iddia)
        print("  Ayristirici: %s" % ayristirici_adi())
        if c_hata:
            for h in c_hata:
                print("  ❌ " + h)
            print("SONUC: KIRMIZI ❌")
            return 1
        print("  ✅ A-POZITIF: gecerli/alisilmadik YAML yanmiyor (anchor/alias, matrix, "
              "`if:`, `run: |`, `>-`, uzun env, Turkce, emoji)")
        print("  ✅ A-NEGATIF: %d bozuk fikstur KIRMIZI + tani dogru" % len(BOZUK_ORNEKLER))
        print("  ✅ B-POZITIF: sentetik cagri etkili sayiliyor (+ jeton tam olunca da)")
        print("  ✅ B-NEGATIF: %d etkisizlestirme + %d jeton/yardim + %d tetikleyici "
              "biciminde cagri OLU sayiliyor"
              % (len(B_MUTANTLAR), len(B_JETON_MUTANTLAR), len(B_TETIK_MUTANTLAR)))
        print("  ✅ B-CAPRAZ (O6): muafiyet<->iddia kilidi iki yonde de KIRMIZI yakiyor")
        print("  ✅ A-UCTAN-UCA: bolum_a() gecici dizinden okuyup hatalari TOPLUYOR "
              "(+ gecerli dosyada susuyor)")
        print("  ✅ MAIN CIKIS KODU: AST'te `return 1` var + alt surec hatali dizinde "
              "rc=1 donuyor")
        print("  ✅ D-POZITIF: temiz fiksturde kapi cagrisi ETKILI; MESRU fail-open adimi "
              "(kapi kosmayan continue-on-error) bulgu URETMIYOR")
        print("  ✅ D-NEGATIF/D-YANLIS-POZITIF: %d fikstur (%d etkisizlestirme + %d mesru "
              "yazim) dogru siniflandi"
              % (len(D_MUTANTLAR), sum(1 for m in D_MUTANTLAR if m[2]),
                 sum(1 for m in D_MUTANTLAR if not m[2])))
        print("  ✅ D_IZIN MEKANIZMASI: gerekcesiz giris KIRMIZI · var olmayan dayanak "
              "yolu KIRMIZI · gerekceli+dayanakli giris kabul")
        print("  ✅ E-POZITIF: temiz sentetik fiksturde `on.push` + %d zorunlu kapi adimi "
              "ETKILI sayiliyor (iddia sayaci da olculdu)" % len(E_ZORUNLU_CAGRILAR))
        print("  ✅ E-NEGATIF/E-YANLIS-POZITIF: %d fikstur (%d sessiz-kacis + %d mesru "
              "yazim) dogru siniflandi"
              % (len(E_MUTANTLAR), sum(1 for m in E_MUTANTLAR if m[2]),
                 sum(1 for m in E_MUTANTLAR if not m[2])))
        print("  ✅ F-MENSIYON SOZLESMESI: etkili_mensiyon() `cp` argumanini bulur, "
              "`echo`/yorum mensiyonunu BULMAZ (tuketici jenerator/test/kabul.py CI'da "
              "muaf oldugu icin sozlesme BURADA olculur)")
        print("  ✅ F-SATIR-DEVAMI: `\\` ile bolunmus cagri TEK satir olarak goruluyor")
        print("SONUC: YESIL ✅")
        return 0

    hatalar = []
    a_hata, dosya_sayisi = bolum_a(args.dizin)
    hatalar.extend(a_hata)
    b_hata, cagri_sayisi, b_iddia_sayisi = bolum_b(args.dizin)
    hatalar.extend(b_hata)
    d_hata, d_toplam, d_etkisiz, d_izinli = bolum_d(args.dizin)
    hatalar.extend(d_hata)
    e_hata, e_iddia = bolum_e(args.dizin)
    hatalar.extend(e_hata)

    # BOLUM C bayraksiz (bloklayici) kolda da BLOKLAR — `--kendini-test` adimi silinse
    # bile nobetci yasar (ci-kapsam-test.py'nin 27 Tem'de olctugu delik).
    for h in c_hata:
        hatalar.append("KENDINI-TEST: " + h)

    print("IS AKISI BICIM KAPISI")
    print("  Ayristirici              : %s" % ayristirici_adi())
    print("  Ayristirilan is akisi    : %d  (%s)" % (
        dosya_sayisi,
        ", ".join(os.path.basename(y) for y in is_akisi_dosyalari(args.dizin)) or "-"))
    print("  B iddiasi (pozitif cagri): %d  (%s)" % (
        b_iddia_sayisi, ", ".join(i.kimlik for i in B_IDDIALAR)))
    print("  Etkili B cagrisi         : %d  (%s)" % (cagri_sayisi, B_IS_AKISI))
    print("  B-CAPRAZ muafiyet kilidi : %d  (%s)" % (
        len(B_MUAFIYET_DAYANAGI), ", ".join(sorted(B_MUAFIYET_DAYANAGI)) or "-"))
    print("  Olculen kapi cagrisi     : %d  (is akisi dosyalarindaki kabul-testi cagrilari)"
          % d_toplam)
    print("  Etkisizlestirilmis       : %d  (fail-open: continue-on-error / `|| true` / "
          "`if: false` / `set +e`)" % d_etkisiz)
    print("  D_IZIN beyan edilmis     : %d  (%s)" % (
        d_izinli, ", ".join("%s::%s" % a for a in sorted(D_IZIN)) or "-"))
    print("  Tetikleyici/zorunlu adim : %d iddia  (%s: `on.push` + %d zorunlu kapi adimi)"
          % (e_iddia, E_DOSYA, len(E_ZORUNLU_CAGRILAR)))
    print("  Kendini-test iddiasi     : %d" % c_iddia)
    print("-" * 70)
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("-" * 70)
        print("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1
    print("SONUC: YESIL ✅  — is akislari ayristirilabilir · %d POZITIF cagri iddiasinin "
          "hepsi etkili · muafiyet kilidi saglam · hicbir kapi cagrisi beyansiz fail-open "
          "degil · deploy.yml `on.push` ile tetiklenir + zorunlu kapi adimlari etkili."
          % b_iddia_sayisi)
    return 0


if __name__ == "__main__":
    sys.exit(main())
