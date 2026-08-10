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

  🔴 K-26 (30 Tem) — KABUK YAPISI EKSENI: Bolum B/D'nin "etkisiz mi" olcusu bir KAPALI
    LISTEYDI (`|| true` · `|| :` · `|| exit 0`). 14 dusman mutasyonu olculdu: 12'si
    SESSIZ YESIL gecti — `&` (arka plana atma) · `| tee` / `| cat` / `| head` (boru) ·
    `|| echo` (maske) · heredoc YEMI · CAGRILMAYAN fonksiyon YEMI · KOSMAYAN job
    (`if: false` + `needs:` yayilimi) · yalniz `workflow_call` tetikli OLU is akisi.
    Kapinin KENDI cagrisi da `&` ile olduruluyordu. Kapali liste yerine SEMANTIK olcu
    kondu: "bu satirin cikis kodunu KAPI mi belirliyor". Her kural GERCEK `bash -e`
    (GitHub'in varsayilan `run:` kabugu) ile OLCULDU; `; true` / `; exit 0` / `&&` /
    yonlendirme / pipefail'li boru OLDURMEDIGI icin BILEREK isaretlenmez ve
    yanlis-pozitif kanaryasi olarak PINLENIR.

  🔴 K-29 (30 Tem) — ADIM TURU NOBETI: Bolum D'nin capalari `ci-kapsam-test.py`
    KESFINDEN gelir; kabul testi KOSMAYAN bir adim (or. `npx wrangler containers push`)
    hicbir capaya eslesmez ve Bolum D onu HIC GORMEZ. Olculdu: registry-push adiminda
    5 fail-open mutasyonu 5/5 SESSIZ YESIL (pozitif kontrol KIRMIZI yaniyordu -> nobetci
    olu degil, KAPSAMI kordu). Cozum Bolum D'yi ADIM eksenine TASIMAK DEGIL (o eksende
    deploy.yml'in BILINCLI fail-open D1 adimi yanardi) — Bolum B deseninde DOSYA BAZLI
    POZITIF iddia: B_ADIM_IDDIALARI. Kuresel kapsam sayilari DEGISMEZ.

  🔴 K-21a (30 Tem) — D_IZIN DAYANAK KALITESI: eski D3 kurali yalnizca
    `os.path.exists` bakiyordu, yani `CNAME` / `README.md` gibi NOBETCI OLMAYAN her
    mevcut yol muafiyeti gecerli kiliyordu (olculdu: 4/4 kabul). Dayanak artik
    KESFEDILMIS bir kabul testi/kapi olmak, deploy.yml'de FIILEN KOSMAK ve muaf tutulan
    kapidan FARKLI olmak zorunda.

  🔴 K-25 (30 Tem) — BOLUM B KABA CAPA MIRASI: aday suzgeci `^python3\\s+<hedef>` idi;
    `python3 -u <yol>` · `env X=1 python3 <yol>` · `bash -c "python3 <yol>"` ·
    `python3 -X utf8 <yol>` · shebang ile dogrudan cagri MESRU yazimlardir ama capaya
    UYMUYORDU -> Bolum B POZITIF oldugu icin SAHTE KIRMIZI yakiyordu (olculdu: 5/6).
    Aday+hukum artik TEK KAYNAKTAN (SUZGEC.anlamli_cagri) gelir.

  🔴 K-20a (30 Tem) — BOLUM C TESISATI: `oz_cagri_kontrol()` yalniz "kendini_test()
    cagriliyor mu" diye bakiyordu. Olculdu: `for h in c_hata:` -> `for h in []:`
    mutasyonu CAGRIYI birakip SONUCU atiyor, 139 ariza-enjeksiyon iddiasi CI'da
    sessizce dusuyor ve kapi YESIL yaniyordu. Artik sonucun GERCEKTEN TUKETILDIGI
    (dongu/uretec/cagri argumani) VERI AKISI uzerinden dogrulanir.

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
satiri muhendis raporunda (hook'lar bu depoda COMMIT EDILMEZ).

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


# ---------------------------------------------------------------------------
# K-26 — KABUK YAPISI EKSENI: "cikis kodunu KIM belirliyor"
# ---------------------------------------------------------------------------
# 🔴 NEDEN VAR (30 Tem, 14 DUSMAN MUTASYONU OLCULDU — 12'si SESSIZ YESIL gecti):
# `B_ETKISIZ` bir KAPALI LISTEYDI (`|| true` · `|| :` · `|| exit 0`) ve bu depoda
# 53 `deploy.yml` kapi cagrisinin HEPSI onunla korunuyordu. Kapali listenin DISINDA
# kalan bicimler bir kapi adimini BEYANSIZ ve SESSIZCE olduruyordu:
#     python3 tools/kisisel-veri-test.py &            # arka plana at
#     python3 tools/kisisel-veri-test.py | tee kayit.log
#     python3 tools/kisisel-veri-test.py || echo hata
#     cat <<'EOF' ... python3 tools/kisisel-veri-test.py ... EOF   # heredoc YEMI
#     kapi() { python3 tools/kisisel-veri-test.py; }               # CAGRILMAYAN fonksiyon
# Kapinin KENDI cagrisi (`python3 tools/is-akisi-kapisi.py &`) de bu yolla olduruluyordu.
#
# 🔴 KAPALI LISTE YERINE SEMANTIK OLCU (kapsam GENISLEMEZ, HUKUM keskinlesir): bu bolum
# kesif kapsamina HICBIR SEY EKLEMEZ (`ci-kapsam-test.py` kosulan/muaf sayilari degismez,
# olculdu: 122/53/69 -> 122/53/69). Yalnizca ZATEN BULUNMUS bir cagri satirinda
# "cikis kodunu kim belirliyor" sorusu sorulur.
#
# 🔴 HER KURAL GERCEK KABUKLA OLCULDU (tahmin YOK — `bash -e <dosya>`, GitHub'in
# varsayilan `run:` kabugu; basarisiz bir kapi cagrisiyla):
#     duz cagri                 rc=1  BLOKLAR      `&& echo ok`      rc=1  BLOKLAR
#     `; true`                  rc=1  BLOKLAR      `2>&1` / `> log`  rc=1  BLOKLAR
#     `; exit 0`                rc=1  BLOKLAR      pipefail + `|tee` rc=1  BLOKLAR
#     `; :`  / `; echo x`       rc=1  BLOKLAR
#     `&` (arka plan)           rc=0  OLDURUR      `| tee` / `| cat` rc=0  OLDURUR
#     `|| echo` / `|| true`     rc=0  OLDURUR      heredoc / fonksiyon yemi  rc=0  OLDURUR
#
# 🔴 BEYAN — `; true` SINIFI BILEREK ISARETLENMEZ: errexit (GitHub `bash -e {0}`) ACIK
# oldugu icin `cagri ; true` yazimi cagrinin hatasini YUTMAZ (olculdu: rc=1). Onu
# "etkisizlestirme" saymak SAHTE-KIRMIZI yuzeyi acardi ve bu kapi continue-on-error'SUZ
# kosar ([[kapi-kapsam-eksen-secimi]]). Yanlis-pozitif kanaryasi olarak PINLENIR
# (K26_KANARYA) ki ileride "duzeltme" diye geri eklenmesin. `set +e` varken `;` de
# oldurur — o hali ZATEN `_set_e_etkisi` yakalar.

# `||` sag tarafi HATAYI YAYAN bir komutla bitiyorsa cagri BLOKLAMAYA devam eder
# (`|| exit 1` MESRUDUR — D_MUTANTLAR'da yanlis-pozitif kanaryasidir).
K26_HATA_YAYAN = re.compile(
    r"^(?:exit\s+(?!0(?![0-9]))[0-9]+|exit\s+\$\?|false|/bin/false"
    r"|return\s+(?!0(?![0-9]))[0-9]+)(?![\w./-])")

K26_ARKA_PLAN = "arka plana atilmis (`&`) -> kabuk beklemez, adim 0 ile doner"
K26_BORU = ("boru hattinda SON asama DEGIL (`|`) ve `set -o pipefail` KAPALI -> yalniz "
            "son asamanin cikis kodu sayilir")
K26_MASKE = "`|| <hata yaymayan komut>` -> cikis kodu maskelenir"
K26_HEREDOC = "heredoc GOVDESINDE (veri, ICRA DEGIL) -> satir hic calismaz"
K26_FONKSIYON = "CAGRILMAYAN kabuk fonksiyonunun (`%s`) govdesinde -> satir hic calismaz"
K26_ATLANAN_JOB = "job KOSMAZ (%s) -> icindeki hicbir adim calismaz"
K26_OLU_AKIS = ("is akisi yalnizca `workflow_call` ile tetikleniyor ve onu cagiran "
                "baska bir is akisi YOK -> dosyadaki hicbir adim calismaz")


def _ust_duzey_bol(satir):
    """([(onceki_op, segment), ...], hata) — <satir>'i UST DUZEY kabuk kontrol
    operatorlerine (`&&` `||` `|` `;` `&`) gore boler.

    Tirnak (`'` `"`), ters-egik kacis, komut ikamesi (`$( )`, backtick), alt kabuk
    `( )` ve grup `{ }` ICINDEKI operatorler UST DUZEY SAYILMAZ.
    Yonlendirmedeki `&` (`2>&1`, `>&2`, `&> log`) arka plan operatoru DEGILDIR.

    hata doluysa (dengesiz tirnak/parantez) CAGIRAN FAIL-OPEN davranir: bu kapi
    continue-on-error'SUZ kosar, ayristirilamayan bir satirda "etkisiz" demek
    SAHTE-KIRMIZI olurdu ([[kapi-kapsam-eksen-secimi]])."""
    parcalar = []
    op = ""
    tampon = []
    tek = cift = ters = False
    kacis = False
    derinlik = 0
    i, n = 0, len(satir)
    while i < n:
        c = satir[i]
        if kacis:
            tampon.append(c)
            kacis = False
            i += 1
            continue
        if c == "\\" and not tek:
            tampon.append(c)
            kacis = True
            i += 1
            continue
        if tek:
            tampon.append(c)
            if c == "'":
                tek = False
            i += 1
            continue
        if cift:
            tampon.append(c)
            if c == '"':
                cift = False
            i += 1
            continue
        if c == "'":
            tek = True
            tampon.append(c)
            i += 1
            continue
        if c == '"':
            cift = True
            tampon.append(c)
            i += 1
            continue
        if c == "`":
            ters = not ters
            tampon.append(c)
            i += 1
            continue
        if ters:
            tampon.append(c)
            i += 1
            continue
        if c == "(":
            derinlik += 1
            tampon.append(c)
            i += 1
            continue
        if c == ")":
            derinlik = max(0, derinlik - 1)
            tampon.append(c)
            i += 1
            continue
        # `{` / `}` YALNIZ AYRI JETONKEN grup sayilir (`{ echo a; exit 1; }`);
        # `${VAR}` ve `x{y}` gibi kullanimlar derinligi DEGISTIRMEZ.
        if c in "{}" and (i == 0 or satir[i - 1] in " \t;&|") \
                and (i + 1 >= n or satir[i + 1] in " \t;&|"):
            derinlik += 1 if c == "{" else -1
            derinlik = max(0, derinlik)
            tampon.append(c)
            i += 1
            continue
        if derinlik > 0:
            tampon.append(c)
            i += 1
            continue
        if satir.startswith("&&", i) or satir.startswith("||", i):
            parcalar.append((op, "".join(tampon)))
            op = satir[i:i + 2]
            tampon = []
            i += 2
            continue
        if c in "|;":
            parcalar.append((op, "".join(tampon)))
            op = c
            tampon = []
            i += 1
            continue
        if c == "&":
            onceki = satir[i - 1] if i else ""
            sonraki = satir[i + 1] if i + 1 < n else ""
            if onceki in "><" or sonraki == ">":   # `2>&1` · `>&2` · `&> log`
                tampon.append(c)
                i += 1
                continue
            parcalar.append((op, "".join(tampon)))
            op = "&"
            tampon = []
            i += 1
            continue
        tampon.append(c)
        i += 1
    parcalar.append((op, "".join(tampon)))
    hata = None
    if tek or cift or ters or derinlik or kacis:
        hata = "dengesiz tirnak/parantez/kacis"
    return parcalar, hata


def _hata_yayar_mi(segment):
    """<segment> (bir `||` sag tarafi) HATAYI YAYAN bir komutla mi bitiyor?
    `{ echo a; exit 1; }` gibi gruplar acilir ve SON basit komut olculur."""
    s = segment.strip()
    while s.startswith("{") or s.startswith("("):
        s = s[1:].strip()
        if s.endswith("}") or s.endswith(")"):
            s = s[:-1].strip()
    if s.endswith(";"):
        s = s[:-1].strip()
    ic, ic_hata = _ust_duzey_bol(s)
    if ic_hata:
        return True   # FAIL-OPEN: cozulemeyen sag taraf yanlis-pozitif uretmesin
    son = ""
    for _o, seg in ic:
        if seg.strip():
            son = seg.strip()
    return bool(K26_HATA_YAYAN.match(son))


def satir_sebepleri(satir, yol=None, pipefail_acik=False):
    """SATIR duzeyinde etkisizlestirme sebepleri (K-26). `B_ETKISIZ` kapali listesinin
    YERINI ALIR ve onu KAPSAR (`|| true` · `|| :` · `|| exit 0` hepsi `||` maskesi).

    <yol> verilirse yalnizca O YOLU tasiyan segment(ler) olculur; verilmezse satirin
    TAMAMI hedef sayilir (dis tuketici sozlesmesi).

    Kapsanmayan / BEYAN EDILEN siniflar:
      * komut ikamesi ICINDEKI cagri (`x=$(python3 tools/y.py)`) — cikis kodu degiskene
        gider ama `set -e` bunu YINE yakalar; olculmedi, ISARETLENMEZ (fail-open).
      * `trap`/`exec` ile degistirilrmis kabuk davranisi.
      * adim `shell:` anahtariyla errexit'siz ozel bir kabuga cevrilirse (or.
        `shell: bash {0}`) — AYRI sinif, bu turda KAPATILMADI (K-26x, rapora yazildi).
    """
    parcalar, hata = _ust_duzey_bol(satir)
    if hata:
        return []
    n = len(parcalar)
    if yol is None:
        hedefler = list(range(n))
    else:
        hedefler = [k for k, (_o, seg) in enumerate(parcalar) if yol in seg]
    if not hedefler:
        return []
    sebepler = []
    for k in hedefler:
        sonraki_op = parcalar[k + 1][0] if k + 1 < n else ""
        if sonraki_op == "&":
            sebepler.append(K26_ARKA_PLAN)
        if sonraki_op == "|" and not pipefail_acik:
            sebepler.append(K26_BORU)
        # `||` zinciri: hedeften sonra `;`/`&` gorene kadar giden AND-OR listesinde
        # `||` varsa cikis kodunu ZINCIRIN SONU belirler.
        j = k + 1
        zincirde_maske = False
        son_seg = parcalar[k][1]
        while j < n and parcalar[j][0] in ("&&", "||"):
            if parcalar[j][0] == "||":
                zincirde_maske = True
            son_seg = parcalar[j][1]
            j += 1
        if zincirde_maske and not _hata_yayar_mi(son_seg):
            sebepler.append(K26_MASKE)
    # sirayi koru, tekrari at
    gorulen = []
    for s in sebepler:
        if s not in gorulen:
            gorulen.append(s)
    return gorulen


def _pipefail_etkisi(satir):
    """`set -o pipefail` ACAR (True) / `set +o pipefail` KAPATIR (False); ilgisizse None.

    BIRLESIK KISA BAYRAKLAR da cozulur: `set -eo pipefail` (GitHub'in ACIK
    `shell: bash` kabugunun kullandigi yazim) — `-o`'nun bayrak grubunun SONUNDA
    olmasi sarttir, cunku `-o` bir sonraki jetonu ARGUMAN olarak alir."""
    jetonlar = satir.split()
    if not jetonlar or jetonlar[0] != "set":
        return None
    for i, j in enumerate(jetonlar[1:], 1):
        if len(j) >= 2 and j[0] in "-+" and j.endswith("o") \
                and i + 1 < len(jetonlar) and jetonlar[i + 1] == "pipefail":
            return j[0] == "-"
    return None


_HEREDOC_RE = re.compile(r"<<-?\s*(?P<t>['\"]?)(?P<ad>[A-Za-z_][A-Za-z0-9_]*)(?P=t)")
_FONK_RE = re.compile(
    r"^\s*(?:function\s+)?(?P<ad>[A-Za-z_][A-Za-z0-9_-]*)\s*\(\s*\)\s*\{?\s*$")


def _blok_baglami(satirlar):
    """[(satir, baglam_sebepleri), ...] — bir `run:` blogunun satirlarini ICRA BAGLAMINA
    gore etiketle (heredoc govdesi · CAGRILMAYAN fonksiyon govdesi).

    Bu iki sinif SATIR SEVIYESI degil BAGLAM seviyesidir: satir kusursuz gorunur ama
    KABUK ONU HIC CALISTIRMAZ. 30 Tem olcumunde ikisi de SESSIZ YESIL geciyordu."""
    # 1. gecis: heredoc govdesi + fonksiyon govdesi isaretle
    isaret = []          # (satir, tur, ad)  tur: "icra" | "heredoc" | "fonksiyon"
    hd_ad = None
    fonk_ad = None
    fonk_derinlik = 0
    for ham in satirlar:
        s = ham.strip()
        if hd_ad is not None:
            isaret.append((ham, "heredoc", hd_ad))
            if s == hd_ad:
                hd_ad = None
            continue
        if fonk_ad is not None:
            fonk_derinlik += s.count("{") - s.count("}")
            isaret.append((ham, "fonksiyon", fonk_ad))
            if fonk_derinlik <= 0:
                fonk_ad = None
                fonk_derinlik = 0
            continue
        m = _FONK_RE.match(ham)
        if m:
            fonk_ad = m.group("ad")
            fonk_derinlik = ham.count("{") - ham.count("}")
            isaret.append((ham, "icra", None))   # TANIM satiri kendisi icra edilir
            if fonk_derinlik <= 0:
                # `f() {` tek satirda kapanmadiysa govde sonraki satirlarda
                fonk_ad = None if "{" not in ham else fonk_ad
                if fonk_ad is not None:
                    fonk_derinlik = 1
            continue
        isaret.append((ham, "icra", None))
        hm = _HEREDOC_RE.search(ham)
        if hm and "<<<" not in ham:
            hd_ad = hm.group("ad")
    # 2. gecis: hangi fonksiyonlar CAGRILIYOR (fail-OPEN: fonksiyon govdesindeki
    # satirlarin ilk jetonu da sayilir -> ic ice cagri yanlis-pozitif uretmez)
    cagrilan = set()
    for ham, tur, _ad in isaret:
        if tur == "heredoc":
            continue
        s = ham.strip()
        if not s or s.startswith("#") or _FONK_RE.match(ham):
            continue
        parcalar, _h = _ust_duzey_bol(s)
        for _o, seg in parcalar:
            jet = seg.strip().split()
            if jet:
                cagrilan.add(jet[0].lstrip("{( "))
    sonuc = []
    for ham, tur, ad in isaret:
        if tur == "heredoc":
            sonuc.append((ham, [K26_HEREDOC]))
        elif tur == "fonksiyon" and ad not in cagrilan:
            sonuc.append((ham, [K26_FONKSIYON % ad]))
        else:
            sonuc.append((ham, []))
    return sonuc


def _kosmayan_joblar(jobs):
    """DAIMA-YANLIS `if:` tasiyan joblar + onlara `needs:` ile bagli joblar.
    `if:` ifadesinde `always()`/`cancelled()` gecen job FAIL-OPEN sayilir (atlanmaz)."""
    atlanan = set()
    for job_id, job in jobs.items():
        if isinstance(job, dict) and _yanlis_mu(job.get("if")):
            atlanan.add(job_id)
    degisti = True
    while degisti:
        degisti = False
        for job_id, job in jobs.items():
            if job_id in atlanan or not isinstance(job, dict):
                continue
            ifade = job.get("if")
            if isinstance(ifade, str) and ("always()" in ifade or "cancelled()" in ifade):
                continue
            needs = job.get("needs")
            if isinstance(needs, str):
                needs = [needs]
            if not isinstance(needs, list):
                continue
            if any(str(x) in atlanan for x in needs):
                atlanan.add(job_id)
                degisti = True
    return atlanan


# ---- SERIT AYRIMI: YAYINI BLOKLAYAN <-> BLOKLAMAYAN JOB --------------------
# NEDEN VAR (31 Tem 2026, olculmus karar): deploy.yml `build` job'u ikiye ayrildi.
# `deploy` YALNIZ `build`'e `needs:` ile baglidir; `serit-b` job'u KIRMIZI yansa bile
# yayin CIKAR. Bu BILINCLI bir karardir (kapi/test birikmesi 21 gunde CI'yi 0,42 ->
# 6,55 dk'ya cikardi ve 28 Tem'de TEK bir CI-meta kapisi 6 SAATLIK 404 pencereleri
# acti), AMA ayni mekanizma bir A-kapisini sessizce etkisizlestirmenin en ucuz yoludur:
# adimi silmeye / `|| true` yazmaya gerek yok, BASKA BIR JOB'A TASIMAK yeter.
#
# 🔴 Bolum D bu yuzden "yayini bloklamayan bir job'da kosan kapi cagrisi"ni FAIL-OPEN
# sayar ve SERIT_B tablosunda TEK TEK beyan ISTER. Joker (`*`) KABUL EDILMEZ: beyan
# adim adim yapilir, boylece "hepsini B'ye at" tek satirla yapilamaz.
YAYIN_ACTION_ONEKI = "actions/deploy-pages"

# ---- IS AKISI ROLLERI (5 Agu 2026) ----------------------------------------
# 🔴 NEDEN IKI DOSYA: GitHub bir KOSUMUN `conclusion`'ini o kosumdaki TUM joblarin
# EN KOTUSUNDEN turetir. Bloklamayan nobet/alarm joblari deploy.yml icindeyken
# kirmizilari YAYIN kosumunu boyuyordu; olculen bedel 28 ardisik "failure" kosum
# ve bunlarin 14'unde `deploy`+`yayin` YESIL ([[hukum-yanlis-birimde]]). Joblar
# nobet.yml'e TASINDI (susturulmadi): ayni komut, ayni fail-closed cikis kodu,
# AYRI `conclusion`.
#
# BU SABITLER SERIT AYRIMININ KAPSAMIDIR: SERIT_B beyani (Bolum D) ve BLOKLAYICI/
# BLOKLAMAZ dogrulamasi (Bolum F) HER IKI dosyada da isler. Nobet dosyasini bu
# listeden dusurmek 52 SERIT_B beyanini BIR ANDA denetimsiz birakirdi -> Bolum G
# (`yayin_sinyali_kontrol`) kapsamin bu iki dosyayi da tasidigini AYRICA olcer.
E_DOSYA = "deploy.yml"          # YAYIN is akisi (Pages deploy burada)
N_DOSYA = "nobet.yml"           # NOBET/ALARM seridi (yayini BLOKLAMAZ)
NOBET_DOSYALARI = (N_DOSYA,)
SERIT_B_DOSYALARI = (E_DOSYA,) + NOBET_DOSYALARI


def _yayin_isi(jobs):
    """Pages YAYININI fiilen yapan job'un id'si (bir adimi `actions/deploy-pages...`
    kullanir); bulunamazsa None. Job ADINA capalanmaz — ad degistirilerek kacilirdi."""
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, dict) and isinstance(step.get("uses"), str) \
                    and step["uses"].strip().startswith(YAYIN_ACTION_ONEKI):
                return job_id
    return None


def _serit_b_joblar(govde, ad=None):
    """(serit_b_job_kumesi, tani) — YAYINI BLOKLAMAYAN joblarin id kumesi.

    Yayini BLOKLAYAN kume = Pages yayin job'u + ona `needs:` ile GECISLI bagli TUM
    atalari. Bu kumenin DISINDA kalan bir job kirmizi yansa da `deploy` yine kosar,
    yani oradaki kapi cagrisinin cikis kodu YAYINI BLOKLAMAZ.
    Yayin job'u bulunamazsa (None, tani) doner -> cagiran FAIL-CLOSED davranir.

    🔴 <ad> NOBET dosyasi ise (5 Agu 2026 serit ayrimi): o dosyada Pages yayini YOKTUR
    ve `needs:` GitHub'da IS AKISI ICINDEDIR -> oradaki hicbir job yayin grafigine
    giremez, yani HEPSI serit B'dir. Bu bir fail-OPEN gevsemesi DEGILDIR, cunku:
      (a) yayin job'u orada BULUNURSA (biri Pages yayinini nobet dosyasina tasimissa)
          fail-closed KIRMIZI doner — "hepsi B" hukmu ancak yayin YOKKEN verilir;
      (b) oradaki her kapi cagrisi yine SERIT_B tablosunda TEK TEK beyan ister
          (Bolum D), yani "A kapisini sessizce B'ye kaydirma" yolu KAPALI kalir;
      (c) deploy.yml'in bu dosyayi `uses:` ile cagirmadigi Bolum G'de olculur
          (cagirsaydi joblar yayin grafigine GERI girerdi)."""
    jobs = govde.get("jobs") if isinstance(govde, dict) else None
    if not isinstance(jobs, dict) or not jobs:
        return None, "`jobs:` blogu okunamadi"
    yayin = _yayin_isi(jobs)
    if ad is not None and ad in NOBET_DOSYALARI:
        if yayin is not None:
            return None, ("%s bir NOBET is akisidir ama icinde Pages yayin job'u "
                          "(`%s`) VAR -> yayin nobet seridine tasinmis; serit ayrimi "
                          "OLCULEMEZ (fail-closed)" % (ad, yayin))
        return set(jobs), None
    if yayin is None:
        return None, ("Pages yayin job'u BULUNAMADI (`uses: %s...` tasiyan adim yok) -> "
                      "hangi joblarin yayini BLOKLAMADIGI olculemez" % YAYIN_ACTION_ONEKI)
    bloklayan = {yayin}
    degisti = True
    while degisti:
        degisti = False
        for job_id in list(bloklayan):
            job = jobs.get(job_id)
            if not isinstance(job, dict):
                continue
            needs = job.get("needs")
            if isinstance(needs, str):
                needs = [needs]
            if not isinstance(needs, list):
                continue
            for x in needs:
                if str(x) in jobs and str(x) not in bloklayan:
                    bloklayan.add(str(x))
                    degisti = True
    return set(jobs) - bloklayan, None


def _olu_is_akisi_mi(govde):
    """Is akisi YALNIZCA `workflow_call` ile mi tetikleniyor (yani onu cagiran baska bir
    is akisi olmadan HIC kosmaz)? deploy.yml (`push`) ve onizleme-imaj.yml
    (`workflow_dispatch`) bu kurala TAKILMAZ — olculdu, yanlis-pozitif YOK."""
    adlar = _tetik_adlari(govde)
    return bool(adlar) and adlar <= {"workflow_call"}


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


def icra_satirlari(metin):
    """TEK KAYNAK (K-26 genisletmesi) —
    [(job_id, adim_no, adim_adi, adim_sebep, satir, pipefail_acik), ...]

    `_run_satirlari()` bunun 5'li sarmalayicisidir (dis sozlesme bozulmasin diye).
    Ek olarak `adim_sebep`e SATIRIN HIC CALISMADIGI baglam sebepleri de girer:
      * heredoc govdesi                       (K26_HEREDOC)
      * CAGRILMAYAN kabuk fonksiyonu govdesi  (K26_FONKSIYON)
      * KOSMAYAN job (`if: false` + `needs:` yayilimi)  (K26_ATLANAN_JOB)
      * yalniz `workflow_call` tetikli OLU is akisi     (K26_OLU_AKIS)
    Bunlar SATIR degil BAGLAM ozellikleridir; o yuzden satir duzeyindeki `&`/`|`/`||`
    sebepleri (satir_sebepleri) AYRI tutulur ve CAGIRAN ekler."""
    govde, hata = ayristir(metin)
    if hata or not isinstance(govde, dict):
        return []
    jobs = govde.get("jobs")
    if not isinstance(jobs, dict):
        return []
    akis_sebep = [K26_OLU_AKIS] if _olu_is_akisi_mi(govde) else []
    atlanan = _kosmayan_joblar(jobs)
    kayitlar = []
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        job_sebep = list(akis_sebep)
        if job_id in atlanan:
            sebep_metni = ("DAIMA-YANLIS `if:`" if _yanlis_mu(job.get("if"))
                           else "`needs:` ile KOSMAYAN bir job'a bagli")
            job_sebep.append(K26_ATLANAN_JOB % sebep_metni)
        if _dogru_mu(job.get("continue-on-error")):
            job_sebep.append("job'da `continue-on-error: true`")
        if _yanlis_mu(job.get("if")) and job_id not in atlanan:
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
            pipefail = False
            for ham, baglam_sebep in _blok_baglami(SUZGEC.birlestir_devam(run)):
                s = ham.strip()
                if not s or s.startswith("#"):
                    continue  # kabuk yorumu -> ICRA DEGIL
                if not baglam_sebep:
                    pf = _pipefail_etkisi(s)
                    if pf is not None:
                        pipefail = pf
                    etki = _set_e_etkisi(s)
                    if etki is not None:
                        errexit_kapali = etki
                        continue
                sebep = list(adim_sebep) + list(baglam_sebep)
                if errexit_kapali:
                    sebep.append("ayni `run:` blogunda ONCE `set +e` var "
                                 "(errexit kapali -> cikis kodu bloklamaz)")
                kayitlar.append((job_id, i, adim_adi, sebep, s, pipefail))
    return kayitlar


def _run_satirlari(metin):
    """GERIYE DONUK SARMALAYICI — [(job_id, adim_no, adim_adi, adim_sebep, satir), ...].
    Govde `icra_satirlari()`tedir (K-26); ikinci kopya TUTULMAZ."""
    return [k[:5] for k in icra_satirlari(metin)]


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
    for job_id, adim_no, adim_adi, adim_sebep, s, pf in icra_satirlari(metin):
        if adim_sebep:
            continue
        if satir_sebepleri(s, aranan, pf):
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
    for job_id, adim_no, adim_adi, adim_sebep, s, pf in icra_satirlari(metin):
        hukum0, _s0, _a0 = SUZGEC.anlamli_cagri(s, yol)
        if hukum0 is None:
            continue  # satir bu yolla ILGISIZ
        sebep = list(adim_sebep)
        sebep.extend(satir_sebepleri(s, yol, pf))
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
    for job_id, adim_no, _adim_adi, adim_sebep, s, pf in icra_satirlari(metin):
        if adim_sebep:
            continue  # continue-on-error / daima-yanlis if: / `set +e` / baglam (K-26)
        # 🔴 K-25 (30 Tem): ADAY SUZGECI ARTIK `iddia.onek` DEGIL. Eski kaba capa
        # `^python3\s+<hedef>` isterdi; MESRU yazimlar
        #     python3 -u tools/onizleme-kapisi.py duman --url ...
        #     env PRUVO_X=1 python3 tools/onizleme-kapisi.py duman --url ...
        #     bash -c "python3 tools/onizleme-kapisi.py duman --url ..."
        # capaya UYMAZDI -> Bolum B "cagri YOK" der ve SAHTE KIRMIZI yakardi (Bolum B
        # POZITIF oldugu icin eksik capa fail-OPEN degil fail-CLOSED yonde patlar).
        # Hukum ZATEN dogru cozuyordu (SUZGEC.anlamli_cagri `-u`/`env`/`bash -c`
        # sarmallarini acar); eksik olan YALNIZ capaydi -> aday+hukum TEK KAYNAKTAN
        # alinir. (`etkili_kapi_cagrilari` 30 Tem'de ayni onarimi gormustu; Bolum B
        # geride kalmisti.)
        hukum, _suz_sebep, argumanlar = SUZGEC.anlamli_cagri(s, iddia.hedef)
        if hukum is None:
            continue  # satir bu hedefle ILGISIZ
        if satir_sebepleri(s, iddia.hedef, pf):
            continue  # K-26: `&` · boru · `||` maskesi -> cikis kodunu KAPI belirlemiyor
        if hukum == SUZGEC.HAYIR:
            continue  # MENSIYON komutu (`echo ...`) / ICRA-DISI bayrak -> govde kosmaz
        # argumanlar None (OLCULEMEDI) -> jeton sorgulanamaz, BUGUNKU davranis korunur
        # (fail-OPEN, bilincli: bu kapi continue-on-error'SUZ kosar).
        jeton = list(argumanlar) if argumanlar is not None else s.split()
        if any(y in jeton for y in B_YARDIM_BAYRAK):
            continue  # `--help` -> surec is yapmadan 0 doner (IKINCI savunma)
        if not all(z in jeton for z in iddia.jetonlar):
            continue  # zorunlu alt-komut/bayrak dusurulmus
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

# ---------------------------------------------------------------------------
# K-29 — ADIM TURU NOBETI (Bolum B tarzi POZITIF, DOSYA BAZLI iddia)
# ---------------------------------------------------------------------------
# 🔴 OLCULEN DELIK (30 Tem): `onizleme-imaj.yml` registry-push adiminda BES fail-open
# mutasyonu (`continue-on-error: true` · `exit 1`->`exit 0` · `if: false` · `set +e` ·
# hata yolunun `|| true` ile yutulmasi) 5/5 SESSIZ YESIL gecti. Pozitif kontrol (bir
# KAPI cagrisina `|| true`) KIRMIZI yandi -> nobetci OLU DEGIL, KAPSAMI KOR.
#
# KOK NEDEN (madde 26'nin AKRABASI, AYRI KOK): Bolum D'nin capalari
# `ci-kapsam-test.py` KESFINDEN gelir (kabul testi = `tools/*-test.py` · `*-kapisi.py` ...).
# `npx wrangler@4 containers push ...` KOSAN adim hicbir capaya eslesmez -> Bolum D o
# adimi HIC GORMEZ. 26 = ifade/kabuk BICIMI korlugu; 29 = ADIM TURU korlugu.
#
# 🔴 NEDEN KAPSAM GENISLETILMEDI ([[kapi-kapsam-genisletme-tuzagi]]): "kabul testi
# kosmayan her adim da korunsun" demek Bolum D'yi ADIM eksenine tasirdi; o eksende
# deploy.yml'in BILINCLI fail-open adimi ("Katalogu D1'e senkronla", continue-on-error)
# KIRMIZI yanar ve TUM EKIBIN yayini durur — bu tam olarak Bolum D'nin bastan
# KACINDIGI hata. Onun yerine Bolum B'nin deseni: TEK dosya, TEK adim, TEK iddia.
# Kuresel kapsam sayilari DEGISMEZ (olculdu: ci-kapsam-test.py 122/53/69 -> 122/53/69).
class BAdimIddiasi(object):
    """Bir IS AKISI ADIMININ "gercekten bloklayici" oldugu POZITIF iddiasi.

    kimlik        : rapor anahtari
    is_akisi      : dosya adi (DOSYA BAZLI — kuresel kural DEGIL)
    capa_jetonlari: adimin `run:` govdesinde AYNI SATIRDA gecmesi gereken jetonlar
                    (adimi bulmak icin; adim adina DEGIL ICRAYA capalanir ki mesru bir
                    yeniden adlandirma sahte-kirmizi yakmasin [[kapi-anchor-coupling-ikilemi]])
    hata_yolu     : `run:` govdesinde ETKILI bir satir olarak DURMASI gereken komut
                    (adimin BASARISIZLIK yolu). Bu satir duserse adim artik bloklamaz.
    neden         : tani metnine giren "bu neden bloklayici" cumlesi.
    """

    def __init__(self, kimlik, is_akisi, capa_jetonlari, hata_yolu, neden):
        self.kimlik = kimlik
        self.is_akisi = is_akisi
        self.capa_jetonlari = tuple(capa_jetonlari)
        self.hata_yolu = hata_yolu
        self.neden = neden


B_ADIM_IDDIALARI = (
    BAdimIddiasi(
        "registry-push", "onizleme-imaj.yml",
        ("wrangler", "containers", "push"), "exit 1",
        "onizleme derleyici imajini Cloudflare registry'ye iten TEK adim. Fail-open "
        "olursa imaj ITILMEMIS oldugu halde is YESIL yanar; bir sonraki onizleme "
        "kosumu BAYAT imajla calisir ve musteri yazisi/2-renk davranisi sessizce "
        "eski surumden gelir. Hicbir KABUL TESTI kosmadigi icin Bolum D bu adimi "
        "GORMEZ (K-29: adim TURU korlugu)."),
)

B_ADIM_YOK_TANI = (
    "ADIM TURU NOBETI KIRMIZI [%s]: %s dosyasinda `%s` jetonlarini AYNI ICRA SATIRINDA\n"
    "   tasiyan bir adim YOK -> adim silinmis / yoruma alinmis / `echo` mensiyonuna\n"
    "   cevrilmis olabilir.\n"
    "   NEDEN BLOKLAYICI: %s\n"
    "   GERI KOY: adimi `%s` icinde bloklayici bir `run:` adimi olarak.")

B_ADIM_ETKISIZ_TANI = (
    "ADIM TURU NOBETI KIRMIZI [%s]: %s dosyasindaki `%s` adimi ETKISIZLESTIRILMIS.\n"
    "   is akisi: %s · job: %s · adim %d %s\n"
    "   sebep(ler): %s\n"
    "   NEDEN BLOKLAYICI: %s\n"
    "   COZUM: etkisizlestirmeyi GERI AL (bu adim hicbir kabul testi kosmadigi icin\n"
    "   Bolum D onu GORMEZ — koruma YALNIZ bu iddiadadir).")

B_ADIM_HATA_YOLU_TANI = (
    "ADIM TURU NOBETI KIRMIZI [%s]: %s dosyasindaki `%s` adiminda BASARISIZLIK YOLU\n"
    "   (`%s`) ETKILI bir satir olarak YOK.\n"
    "   is akisi: %s · job: %s · adim %d %s\n"
    "   OLCULEN MUTASYONLAR: `exit 1` -> `exit 0` · hata yolunun `|| true` ile\n"
    "   yutulmasi · blok basina `set +e` — UCU DE adimi sessizce fail-open yapar ve\n"
    "   30 Tem olcumunde HICBIR nobetci konusmuyordu.\n"
    "   NEDEN BLOKLAYICI: %s\n"
    "   GERI KOY: adimin hata kolunda bloklayici bir `%s` satiri.")


def b_adim_hatalari(dizin, iddialar=None):
    """(hatalar, iddia_sayisi) — K-29 adim TURU iddialari.

    <iddialar> yalnizca BOLUM C (ariza enjeksiyonu) tarafindan SENTETIK tabloyla
    cagrilir; boylece bu GOVDE olculur, ikinci bir kopya YAZILMAZ."""
    iddialar = B_ADIM_IDDIALARI if iddialar is None else iddialar
    hatalar = []
    for iddia in iddialar:
        yol = os.path.join(dizin, iddia.is_akisi)
        if not os.path.exists(yol):
            hatalar.append("ADIM TURU NOBETI [%s]: %s bulunamadi (%s) -> iddianin "
                           "dayandigi is akisi kalkmis (fail-closed KIRMIZI)"
                           % (iddia.kimlik, iddia.is_akisi, yol))
            continue
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        adimlar = {}
        for job_id, adim_no, adim_adi, sebep, s, pf in icra_satirlari(metin):
            adimlar.setdefault((job_id, adim_no, adim_adi), []).append((sebep, s, pf))
        eslesen = [(a, v) for a, v in adimlar.items()
                   if any(all(j in s for j in iddia.capa_jetonlari)
                          and SUZGEC.etkili_arguman(s, iddia.capa_jetonlari[0])[0]
                          in (SUZGEC.EVET, SUZGEC.OLCULEMEDI, None)
                          for _sb, s, _pf in v)]
        if not eslesen:
            hatalar.append(B_ADIM_YOK_TANI % (
                iddia.kimlik, iddia.is_akisi, " ".join(iddia.capa_jetonlari),
                iddia.neden, iddia.is_akisi))
            continue
        for (job_id, adim_no, adim_adi), satirlar in eslesen:
            etiket = ("(%s)" % adim_adi) if adim_adi else ""
            # (1) ADIM duzeyinde etkisizlestirme (continue-on-error · DAIMA-YANLIS `if:` ·
            #     `set +e` · KOSMAYAN job · OLU is akisi). Capa satirinin KENDI kabuk
            #     yapisina BAKILMAZ: burada `... && { exit 0; } || true` MESRUDUR
            #     (PLAN KAPISI deseni) ve hata yolu ayri bir satirdadir.
            capa_sebep = []
            for sebep, s, _pf in satirlar:
                if all(j in s for j in iddia.capa_jetonlari):
                    capa_sebep = sebep
                    break
            if capa_sebep:
                hatalar.append(B_ADIM_ETKISIZ_TANI % (
                    iddia.kimlik, iddia.is_akisi, " ".join(iddia.capa_jetonlari),
                    iddia.is_akisi, job_id, adim_no, etiket,
                    " + ".join(capa_sebep), iddia.neden))
                continue
            # (2) BASARISIZLIK YOLU ETKILI olarak duruyor mu.
            etkili_hata_yolu = [
                s for sebep, s, pf in satirlar
                if s.strip() == iddia.hata_yolu and not sebep
                and not satir_sebepleri(s, None, pf)]
            if not etkili_hata_yolu:
                hatalar.append(B_ADIM_HATA_YOLU_TANI % (
                    iddia.kimlik, iddia.is_akisi, " ".join(iddia.capa_jetonlari),
                    iddia.hata_yolu, iddia.is_akisi, job_id, adim_no, etiket,
                    iddia.neden, iddia.hata_yolu))
    return hatalar, len(iddialar)


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
#
# 🔴 K-29 EKI (30 Tem, bu turun OZ-KORUMA olcumunde KACAN 13): kablo yalniz main()'de
# aranıyordu. `bolum_b()` govdesindeki `b_adim_hatalari(dizin)` satiri silinince ADIM
# TURU iddiasi GERCEK dosyalar icin hic kosmuyor, ama Bolum C onu SENTETIK tabloyla
# olcmeye devam ettigi icin kapi YESIL yaniyordu. Kablo tablosu bu yuzden
# (SAHIP_FONKSIYON -> ZORUNLU_CAGRILAR) ciftlerine genellestirildi.
KABLO_TABLOSU = (
    ("main", ("bolum_a", "bolum_b", "bolum_d", "bolum_e", "bloklayici_kapi_kontrol",
              "yayin_sinyali_kontrol")),
    # 🔴 BOLUM G TEK KAYNAK kablosu (5 Agu): zincir hesabi `_yayin_zinciri` ve yayin
    # job'unun kesfi `_yayin_isi` ile yapilir. Ikisi de Bolum D/F ile PAYLASILAN
    # graf mantigidir; yayin_sinyali_kontrol kendi kopyasini yazarsa iki bolum ayni
    # gercegi FARKLI olcmeye baslar ([[ikiz-tanim-sessiz-ayrisma]]).
    ("yayin_sinyali_kontrol", ("_yayin_zinciri", "_yayin_isi", "_needs_listesi")),
    # 🔴 Bolum F TEK KAYNAK kablosu: `_serit_b_joblar` ve `etkili_kapi_cagrilari`
    # Bolum D ile PAYLASILIR; biri bloklayici_kapi_kontrol'den dusurulurse beyan/
    # gercek dogrulamasi GERCEK deploy.yml icin HIC kosmaz (Bolum C sentetik
    # fiksturle YESIL demeye devam ederdi) — olculmus K-29 sinifi.
    ("bloklayici_kapi_kontrol", ("_serit_b_joblar", "etkili_kapi_cagrilari")),
    ("bolum_b", ("b_adim_hatalari", "b_capraz_hatalari", "oz_cagri_kontrol",
                 "tablo_sayaci_kontrol", "bolum_kablosu_kontrol")),
    ("kapi_cagrilari", ("satir_sebepleri",)),
    ("icra_satirlari", ("_blok_baglami", "_kosmayan_joblar", "_olu_is_akisi_mi",
                        "_pipefail_etkisi")),
    # 🔴 SERIT AYRIMI (31 Tem): `_serit_b_joblar(...)` ya da `_serit_b_hijyen(...)`
    # cagrisi bolum_d()'den dusurulurse serit nobeti GERCEK deploy.yml icin HIC
    # kosmaz — oysa Bolum C sentetik fiksturle olcmeye devam eder ve YESIL der.
    # Tam olculmus K-29 sinifi; kablo bu yuzden burada da tutulur.
    ("bolum_d", ("kapi_cagrilari", "_serit_b_joblar", "_serit_b_hijyen")),
    # 🔴 NOBETCININ NOBETCISI kablosu (8 Agu, 3. tur — bagimsiz curutucu M6): tablo/kablo
    # mekanizma iddialari kendini_test() govdesinde INLINE dururken sayaci elle yazilmis
    # bir IKIZDI; blok silinince sayac dusmuyordu ve eksen SESSIZCE kayboluyordu. Govde
    # ADLI fonksiyona tasindi ve CAGRISI buraya kablolandi: cagriyi silmek artik AST
    # kapisina takilir, govdeyi bosaltmak ise iddia sayisini dusurur (KENDINI_TEST_TABAN).
    ("kendini_test", ("_tablo_mekanizma_kontrol",)),
)

MAIN_BOLUM_TANI = (
    "BOLUM KABLOSU KOPMUS: %s() govdesinde %s cagrisi YOK -> o iddialar GERCEK is akisi "
    "dosyalari icin HIC kosmuyor.\n"
    "   🔴 Bu SESSIZ bir kacistir: Bolum C (kendini_test) o govdeyi sentetik "
    "fiksturlerle olcmeye devam eder ve 'saglam' der; oysa GERCEK dosyalar hic "
    "denetlenmez.\n"
    "   GERI KOY: %s() icinde `%s(...)` (ve sonucunu hatalara ekle).")


def bolum_kablosu_kontrol():
    """Kablo tablosundaki her SAHIP fonksiyonun govdesinde ZORUNLU cagrilar duruyor mu
    (AST, metin capasi DEGIL — [[kapi-anchor-coupling-ikilemi]])."""
    try:
        with open(os.path.abspath(__file__), encoding="utf-8") as f:
            agac = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        return ["BOLUM KABLOSU OLCULEMEDI: kendi kaynagi ayristirilamadi (%s)" % e]
    govdeler = {d.name: d for d in ast.walk(agac)
                if isinstance(d, ast.FunctionDef)}
    hatalar = []
    for sahip, gerekli in KABLO_TABLOSU:
        dugum = govdeler.get(sahip)
        if dugum is None:
            hatalar.append("BOLUM KABLOSU OLCULEMEDI: %s() fonksiyonu bulunamadi" % sahip)
            continue
        cagrilar = {alt.func.id for alt in ast.walk(dugum)
                    if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name)}
        for ad in gerekli:
            if ad not in cagrilar:
                hatalar.append(MAIN_BOLUM_TANI % (sahip, ad, sahip, ad))
    # SONUC TUKETIMI: cagri duruyor ama sonucu atiliyor mu (mutant 14 sinifi)
    for sahip, cagri_adi in SONUC_TUKETIM_TABLOSU:
        dugum = govdeler.get(sahip)
        if dugum is None:
            hatalar.append("SONUC TUKETIMI OLCULEMEDI: %s() bulunamadi" % sahip)
            continue
        if not _hatalara_akiyor_mu(
                dugum, lambda d, _a=cagri_adi: isinstance(d, ast.Call)
                and isinstance(d.func, ast.Name) and d.func.id == _a):
            hatalar.append(SONUC_TUKETIM_TANI % (sahip, cagri_adi, cagri_adi,
                                                 cagri_adi, cagri_adi))
    # MAIN SABIT NOBETI: nobetci silinince sabitin adi da main()'den duser (mutant 15)
    main_dugumu = govdeler.get("main")
    if main_dugumu is None:
        hatalar.append("MAIN SABIT NOBETI OLCULEMEDI: main() bulunamadi")
    else:
        karsilastirilan = set()
        for alt in ast.walk(main_dugumu):
            if not isinstance(alt, ast.Compare):
                continue
            for taraf in [alt.left] + list(alt.comparators):
                if isinstance(taraf, ast.Name):
                    karsilastirilan.add(taraf.id)
        for ad in MAIN_ZORUNLU_KARSILASTIRMA:
            if ad not in karsilastirilan:
                hatalar.append(MAIN_AD_TANI % (ad, ad))
    return hatalar


# ---- TABLO SAYACI NOBETCISI (30 Tem, oz-koruma olcumunde KACAN 10 ve 11) ----
# 🔴 OLCULEN KACIS: `B_ADIM_IDDIALARI = ()` ve `K26_SATIR_FIKSTURLERI = ()` yazmak
# nobetcileri SESSIZCE oldururdu — dongu bos liste uzerinde doner, hicbir iddia
# DUSMEZ, kapi YESIL yanar. Fikstur/iddia tablolari bu yuzden SAYIYLA korunur.
#
# 🔴 8 Agu 2026 — KURAL DEGISTI: `len(tablo) < taban` YERINE **TAM ESITLIK**
# (`len(tablo) != taban`). Neden (KraL karari, olculdu): `<` operatoru PAYIN
# BIRIKMESINE izin veriyor ve payi GORUNMEZ kiliyordu. Olcum: SERIT_B len=67 · taban=42
# -> pay 25, yani 25 beyan TEK commit'te silinse bile tablo sayaci YESIL kalirdi;
# tabanin var olus sebebi tam olarak o hali GORUNUR kilmakti. Ayni sapma main'de de
# vardi (66/41 = ayni 25) -> konvansiyon her yeni girise +1 bump yapip payi SABIT
# tutmus: kozmetik. Tabani bugunun sayisina cekmek bu turu kapatir, SINIFI kapatmaz.
# Tam esitlikte drift YAPISAL OLARAK imkansiz: her ekleme/silme AYNI commit'te bilincli
# bir taban guncellemesi ister, kapi kirmizi yanarken GERCEK sayiyi da BASAR (bump
# mekanik + kendi kendini belgeleyen olur).
#
# KOSUL (bu kural nereye UYGULANIR): korunan tablolarin HEPSI bu dosyanin icinde
# `globals()`ten okunur -> tabloyu buyuten commit ZATEN bu dosyayi aciyordur, yani bakim
# vergisi yerel ve sinirlidir. Baska bir DOSYADAN / PARTI BASINA buyuyen envanterlere
# (or. `BASLIK_DOGAN_ALLOW` sinifi) tam esitlik UYGULANMAZ: orada her parti yayini
# durdurur ([[envanter-drift-parti-basina]]). 8 Agu'da 18 girisin 18'i de olculdu, hepsi
# BU dosyada tanimli.
#
# (ci-kapsam-test.py::muaf_sayaci_kontrol "ayni desen" diye anilirdi; 8 Agu'da OLCULDU:
# orada sabit bir taban YOK, iddia `n != len(IZIN_LISTESI)` ile ZATEN tam esitliktir ve
# canli listeden TURETILIR -> o yuzey bu turda degistirilmedi.)
# TABAN sayilari bu turda OLCULDU; tablo degisiyorsa tabani AYNI commit'te guncelle.
TABLO_TABANLARI = (
    ("B_IDDIALAR", 5), ("B_MUTANTLAR", 10), ("B_JETON_MUTANTLAR", 4),
    ("B_TETIK_MUTANTLAR", 2), ("B_ADIM_IDDIALARI", 1), ("BOZUK_ORNEKLER", 9),
    # E_MUTANTLAR 1 Agu: 22 -> 25 (durum-test.py KOL GRANULU mutantlari eklendi).
    # E_MUTANTLAR 7 Agu: 25 -> 28 (konfigur-bundle bayraksiz kol mutantlari: 2 oldurucu
    # + 1 kanarya).
    ("D_MUTANTLAR", 20), ("E_MUTANTLAR", 28), ("K26_SATIR_FIKSTURLERI", 26),
    # 8 Agu: 5 -> 8 (taban tam-esitlige cevrildi; olculen pay 3 idi, olu koruma).
    ("K26_BAGLAM_MUTANTLAR", 8), ("K29_MUTANTLAR", 13),
    # 1 Agu: 4 -> 6 (durum-test.py'nin IKI kolu KOL GRANULUNDE eklendi). Taban
    # yukseltildi cunku kolu tabloDAN silmek, adimi deploy.yml'den silmekle AYNI
    # kapiyi acar: iddia dusar, kimse kirmizi gormez.
    # 7 Agu: 6 -> 7 (konfigur-bundle-kapisi.py'nin deploy.yml'deki BAYRAKSIZ kolu;
    # serit ayrimi `--kendini-test` kolunu nobet.yml'e tasiyinca dosya granullu kapsam
    # kapisi bayraksiz kolun silinmesini GORMEZ olmustu — olculdu, rc=0).
    ("E_ZORUNLU_CAGRILAR", 7), ("E_ZORUNLU_VARLIKLAR", 1),
    # 8 Agu: 5 -> 7 (taban tam-esitlige cevrildi; olculen pay 2 idi, olu koruma).
    # 8 Agu (3. tur): 7 -> 8 (kendini_test -> _tablo_mekanizma_kontrol kablosu eklendi;
    # M6 sinifi: inline blok + elle yazili `iddia += 6` ikizi eksenin SESSIZCE
    # silinmesine izin veriyordu).
    ("KABLO_TABLOSU", 8), ("B_MESRU_YAZIMLAR", 6),
    # 🔴 SERIT_B (31 Tem): tablo TABANLA TAM ESIT olmali (8 Agu; once yalniz "altina
    # dusemez"di). Kucultmek
    # tek basina bir kacis DEGILDIR (S3 bayatlik kurali zaten kirmizi yakar), ama
    # tabani burada tutmak "35 beyan tek commit'te sessizce silindi + ayni commit'te
    # adimlar A'ya geri tasindi" halini GORUNUR kilar. Bilerek kucultuluyorsa NEDENIYLE
    # birlikte guncelle (serit degisimi = KraL karari).
    # 2 Agu: 36 -> 38 (job `hacim-tam-takim`in iki kolu: jenerator/test/dogrula.py +
    # jenerator/test/kabul.py; dis bagimlilikli elle-tetik takim, gerekce tabloda).
    # 3 Agu: 38 -> 39 (onizleme vaat kapisinin `--kendini-test` kolu beyan edildi;
    # bayraksiz GERCEK olcum kolu serit A'da `build` job'unda bloklayici kalir).
    # 3 Agu: 39 -> 40 (kalibrasyon senkron kapisinin `--mutasyon` kolu beyan edildi;
    # bayraksiz GERCEK olcum kolu serit A'da `build` job'unda BLOKLAYICI kosar).
    # 3 Agu: 40 -> 41 (yayin erisim nobetcisinin kabul testi beyan edildi; GERCEK
    # olcum kolu CI'da HIC kosmaz, ayri cron alarm is akisindadir).
    # 8 Agu: 41 -> 42 (varlik kapisinin `--kendini-test` kolu beyan edildi; bayraksiz
    # GERCEK olcum kolu serit A'da `deploy.yml` job `serit-a3`te BLOKLAYICI kalir.
    # O kol daha once HICBIR is akisinda cagrilmiyordu ve KIRMIZI kaldigi gorulmemisti).
    # 8 Agu: 42 -> 85 (KESIF GENISLEMESI: `tools/ci-kapsam-test.py` kesif predikati
    # `*-mutasyon.py`yi gormuyordu; 43 surucunun 35'i hicbir OTOMATIK is akisinda
    # kosmuyordu ve UCU ZATEN BAYATLAMISTI. Esigi gecen 17 surucu nobet.yml
    # `serit-b`ye KENDI DUZ TEK KOMUT ADIMIYLA baglandi + kesif genislemesinin
    # ORTAYA CIKARDIGI 1 eski beyansiz adim (`yayin-sinyali-mutasyon.py`) beyan
    # edildi; her biri AYRI giris — toplu/joker beyan YOK.
    # 🔴 TABAN ARTIK GERCEK SAYIYA ESITLENDI (67 -> 85 degil, 42 -> 85): eski taban
    # 42 iken tablo FIILEN 67 giristi, yani 25 girisi tek commit'te silmek bu
    # sayaci HIC kirmizi yakmiyordu. Taban = gercek sayi oldugunda her KUCULME
    # bilincli bir guncelleme ister (tablonun BEYAN EDILEN amaci budur).
    # 🔴 8 Agu (dal, rebase): ENVANTER main'in — 85 giris ve yukaridaki gerekce AYNEN
    # KALDI, tek bir beyan dusurulmedi. Bu daldan gelen sey OPERATORDUR: kontrol artik
    # TAM ESITLIK (`len(tablo) != taban`). Gerekce: main tabani gercek sayiya cekerek
    # SILME eksenini kapatti ama `<` operatorunu birakti; payin BIRIKMESINE izin veren
    # sey tam olarak o operatordur ve bu tablonun kendi tarihi kaniti: 36->38->39->40->
    # 41->42 diye her yeni girise +1 bump yapilmis, pay 25'te SABIT kalmisti. 85 bugun
    # dogru; yarin 18 giris daha eklenip taban guncellenmezse yine kozmetiklesir.
    # Tam esitlikte bu YAPISAL OLARAK imkansiz. Taban bu satirda ELLE yazilmadi:
    # tablo birlestirmesinden SONRA agactan OLCULDU (len(SERIT_B) ile dogrulanir; bu
    # dosyanin oz-testi ve tools/nobetci-mutasyon-test.py BOLUM E o esitligi surer).
    # 9 Agu: +1 -> 86. Yeni giris ("nobet.yml", "serit-b", "tools/lcp-onculuk-kapisi.py");
    # tam esitlik operatoru geregi taban BILINCLI olarak ayni commit'te guncellendi.
    # 9 Agu: +1 -> 87. Yeni giris ("nobet.yml", "serit-b", "tools/r2-avif-mutasyon-test.py");
    # R1 sihirli-bayt whitelist'i AVIF'e acildi, bataryasi AYNI commit'te beyan edildi.
    # 9 Agu: +3 -> 90. Marka tek-sayfa davranis nobetcisi ile iki ayirt edici mutasyon
    # surucusu serit-b'ye AYRI duz komutlarla eklendi; ucu de AYNI commit'te tek tek
    # beyan edildi.
    # 9 Agu: +1 -> 91. Sentetik git fiksturu sizinti kapisi ve kendi testi ayni
    # arac yolundan serit-b'ye kablandi; tek yol beyani iki duz komutu kapsar.
    # 9 Agu: +1 -> 92. D1 seq tam-sayi/kanonik-sira araci icin agsiz kabul testi
    # serit-b'ye eklendi; gercek D1 yazma/geri-okuma nobeti serit A'da kaldi.
    # 10 Agu: +2 -> 94. Model uyeligi ve model baslik kollarinin KENDINI-TEST
    # bataryalari serit-b'ye tasindi; iki bayraksiz GERCEK katalog olcumu deploy.yml
    # serit-a3'te BLOKLAYICI kaldi.
    ("SERIT_B", 94),
    # 5 Agu: BOLUM G (yayin sinyali safligi) fikstur tablolari. Ikisi de
    # bosaltilirsa dongu bos liste uzerinde doner ve iki yonlu batarya SESSIZCE
    # oler — tam da bu tabanin engelledigi kacis.
    ("G_MUTANTLAR", 15), ("G_SIMULASYON", 6),
)

TABLO_TANI = (
    "TABLO SAYACI KIRMIZI: %s tablosunda %d giris var, TABAN %d (fark %+d).\n"
    "   🔴 IKI YON DE KIRMIZIDIR (8 Agu, tam esitlik):\n"
    "   (a) KUCULME — fikstur/iddia tablosunu kucultmek nobetciyi SESSIZCE oldurur:\n"
    "       dongu bos liste uzerinde doner, hicbir iddia DUSMEZ ve kapi YESIL yanar\n"
    "       (olculdu: `B_ADIM_IDDIALARI = ()` ve `K26_SATIR_FIKSTURLERI = ()`\n"
    "       mutantlari KACIYORDU).\n"
    "   (b) TABAN GUNCELLENMEDEN BUYUME — taban kozmetiklesir ve PAY BIRIKIR: pay\n"
    "       kadar giris tek commit'te silinse bile sayac YESIL kalir. Olculdu (8 Agu):\n"
    "       SERIT_B len=67 · taban=42 -> 25 beyan sessizce silinebilirdi.\n"
    "   YAPILACAK: degisim BILINCLIYSE tools/is-akisi-kapisi.py::TABLO_TABANLARI'nda\n"
    "   %s tabanini AYNI commit'te %d -> %d yap ve NEDENINI yaz.")


def tablo_sayaci_kontrol():
    """Fikstur/iddia tablolari TABANLA TAM ESIT mi (8 Agu; once yalniz 'altina dusmus mu').

    Tam esitlik secildi cunku `<` payin BIRIKMESINE izin verir ve payi gorunmez kilar
    (olculdu: SERIT_B 67/42 -> pay 25, main'de 66/41 -> ayni 25; her yeni girise +1 bump
    payi SABIT tutmus, yani taban kozmetiklesmisti). Gerekce blogu TABLO_TABANLARI'nin
    ustunde; tam esitligin UYGULANMA KOSULU da orada (tablolar BU dosyada buyur)."""
    hatalar = []
    kapsam = globals()
    for ad, taban in TABLO_TABANLARI:
        tablo = kapsam.get(ad)
        if tablo is None:
            hatalar.append("TABLO SAYACI: %s tablosu ARTIK YOK -> yeniden adlandirildiysa "
                           "TABLO_TABANLARI'ni guncelle" % ad)
            continue
        if len(tablo) != taban:
            hatalar.append(TABLO_TANI % (ad, len(tablo), taban, len(tablo) - taban,
                                         ad, taban, len(tablo)))
    # K26 satir fiksturlerinde IKI SINIF da TABANIN USTUNDE yasamali (yalniz kanarya
    # birakip oldurucularin hepsini silmek tablo BOYUNU korur ama nobetciyi bosaltirdi).
    #
    # 🔴 BU KOL BILEREK `<` (TAM ESITLIK DEGIL) — 8 Agu'da bir tur `!=` yapilip GERI
    # ALINDI. Olculen gerekce (curutucu, ayni gun):
    #   (a) KAZANC SIFIR: `!=`in hedefledigi kacis "toplami koruyup yeniden dagitim"
    #       (or. 11 oldurucu / 15 kanarya) ZATEN `<` ile kirmizi yanar — toplam sabitken
    #       bir sinif buyurken DIGERI mutlaka tabanin ALTINA duser. Ustelik bagimsiz K26
    #       siniflandirma testi de o halde kirmizidir.
    #   (b) BEDEL GERCEK: MESRU BUYUME (yeni bir GERCEK oldurucu fikstur eklenir; tablo
    #       26 -> 27, siniflar 11/16) `<` ile dogru sekilde rc=0 verirken `!=` ile rc=1
    #       veriyordu -> SAHTE-KIRMIZI, yani TUM EKIBIN yayini durur. Teshis metni de
    #       yanlis sey soyluyordu ("tablo BOYU korunup yeniden dagitim" derken tablo
    #       BUYUMUS oluyordu).
    # Envanter ekseninde tam esitlik garantisini TABLO_TABANLARI zaten tablo-tablo
    # veriyor (K26_SATIR_FIKSTURLERI dahil); bu SINIF kolu onun ustune ikinci bir
    # tavan koymaz. "Tutarlilik" gerekcesiyle burayi `!=` yapmak OLCULMUS bir gerileme
    # olur — BOLUM E'de iki vaka bunu koruyor (yeniden dagitim KIRMIZI · mesru buyume YESIL).
    oldurucu = sum(1 for m in K26_SATIR_FIKSTURLERI if m[2])
    kanarya = sum(1 for m in K26_SATIR_FIKSTURLERI if not m[2])
    if oldurucu < 10 or kanarya < 16:
        hatalar.append("TABLO SAYACI: K26_SATIR_FIKSTURLERI sinif dengesi bozuldu "
                       "(oldurucu=%d taban 10 · kanarya=%d taban 16) -> tablo BOYU "
                       "korunup bir SINIF bosaltilmis ya da siniflar arasi YENIDEN "
                       "DAGITIM yapilmis olabilir. Bir sinifi bilerek kucultuyorsan o "
                       "sinifin tabanini AYNI commit'te NEDENIYLE birlikte dusur."
                       % (oldurucu, kanarya))
    return hatalar


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
                return _tesisat_kontrol(dugum, alt)
        return [OZ_CAGRI_TANI]
    return ["OZ-CAGRI NOBETI OLCULEMEDI: main() fonksiyonu bulunamadi (dosya yeniden "
            "duzenlendiyse bu nobetciyi guncelle)"]


BOLUM_C_TESISAT_TANI = (
    "BOLUM C TESISATI KOPUK (K-20a): main() `kendini_test()` sonucunu `%s` adina "
    "BAGLIYOR ama o ad BLOKLAYICI kolda BIR DONGUYE ya da CAGRIYA hic girmiyor -> "
    "ariza-enjeksiyon BULGULARI TOPLANMIYOR.\n"
    "   🔴 OLCULEN KACIS (30 Tem, bu turun oz-koruma turu): `for h in c_hata:` satirini\n"
    "   `for h in []:` yapmak CAGRIYI birakip SONUCU atiyordu. oz_cagri_kontrol() yalniz\n"
    "   'cagri var mi' diye bakiyordu -> tatmin oluyor, Bolum C'nin TUM iddialari (139)\n"
    "   CI'da sessizce dusuyor ve kapi YESIL yaniyordu.\n"
    "   GERI KOY: main() icinde `for h in %s: hatalar.append(...)` (ya da "
    "`hatalar.extend(%s)`).")


def _ad_geciyor(dugum, ad):
    return any(isinstance(x, ast.Name) and x.id == ad for x in ast.walk(dugum))


def _hatalara_akiyor_mu(kapsam, esles):
    """<esles(dugum)> ile eslesen bir ifade HATA BIRIKTIRICISINE akiyor mu?

    Kabul edilen iki bicim:
      * `hatalar.extend(<X>)` / `hatalar.append(<X>)`   (X icinde eslesme var)
      * `for h in <X>: ... hatalar.extend/append(...)`  (dongu govdesi biriktiriyor)

    🔴 NEDEN "CAGRI VAR MI" YETMEZ (olculdu, oz-koruma turu mutant 14 ve 17): bir CAGRIYI
    birakip SONUCUNU ATMAK (`b_adim_hatalari(dizin)` · `for h in []:`) AST'te cagriyi
    yerinde birakir -> kablo nobetcisi tatmin olur, iddialar sessizce duser. Olcum bu
    yuzden CAGRIYA degil VERI AKISINA bakar.
    ⚠️ Biriktirici adi (`hatalar`) BILEREK sabit: bu dosyanin KENDI ic sozlesmesidir;
    yeniden adlandirilirsa nobetci KIRMIZI yanar ve guncellenmesi gerekir."""

    def biriktirici_cagrisi(d):
        return (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                and d.func.attr in ("extend", "append")
                and isinstance(d.func.value, ast.Name) and d.func.value.id == "hatalar")

    for alt in ast.walk(kapsam):
        if biriktirici_cagrisi(alt) and any(
                any(esles(x) for x in ast.walk(a)) for a in alt.args):
            return True
        if isinstance(alt, ast.For) and esles(alt.iter):
            if any(biriktirici_cagrisi(ic) for ic in ast.walk(alt)):
                return True
    return False


SONUC_TUKETIM_TANI = (
    "SONUC TUKETILMIYOR: %s() govdesinde `%s(...)` CAGRILIYOR ama sonucu HATA "
    "BIRIKTIRICISINE (`hatalar`) akmiyor -> iddialar kosuyor, BULGULARI ATILIYOR.\n"
    "   🔴 Bu SESSIZ bir kacistir ve kablo nobetcisini DELER: cagri yerinde durdugu icin\n"
    "   'kablo saglam' der. Olculdu (30 Tem): `hatalar.extend(%s(dizin)[0])` ->\n"
    "   `%s(dizin)` mutasyonu kapiyi YESIL birakiyordu.\n"
    "   GERI KOY: `hatalar.extend(%s(...)[0])`.")

# (sahip_fonksiyon, sonucu TUKETILMESI ZORUNLU cagri)
SONUC_TUKETIM_TABLOSU = (
    ("bolum_b", "b_adim_hatalari"),
    ("bolum_b", "tablo_sayaci_kontrol"),
    ("bolum_b", "b_capraz_hatalari"),
)

# main() govdesinde GERCEK BIR KARSILASTIRMAYA girmesi ZORUNLU sabitler.
# 🔴 "ADI GECIYOR MU" YETMEZ (olculdu, oz-koruma mutant 15): `if c_iddia <
# KENDINI_TEST_TABAN:` -> `if False:` mutasyonunda sabit TANI METNINDE hala geciyordu
# (`KENDINI_TEST_TABAN_TANI % (c_iddia, KENDINI_TEST_TABAN)`) -> ad-bazli olcum tatmin
# oluyor, nobetci OLU kaliyordu. Sart: sabit bir `ast.Compare` icinde YER ALMALI.
MAIN_ZORUNLU_KARSILASTIRMA = ("KENDINI_TEST_TABAN",)

MAIN_AD_TANI = (
    "MAIN SABIT NOBETI KIRMIZI: main() govdesinde `%s` HICBIR KARSILASTIRMAYA girmiyor "
    "-> o nobetci silinmis (sabit yalnizca tani metninde geciyor olabilir).\n"
    "   Olculdu (30 Tem): `if c_iddia < KENDINI_TEST_TABAN:` -> `if False:` mutasyonu "
    "Bolum C\n   iddia sayaci tabanini olduruyordu ve kapi YESIL yaniyordu.\n"
    "   GERI KOY: main() icinde `if c_iddia < %s: _cikis_yolu_kirmizi(...)`.")


def _tesisat_kontrol(main_dugumu, atama):
    """kendini_test() sonucunun BAGLANDIGI ad, main() icinde GERCEKTEN TUKETILIYOR mu.

    TUKETIM = ad bir `for ... in <ad>` dongusunun kaynagi, bir liste uretecinin kaynagi
    ya da bir CAGRI ARGUMANI olarak geciyor. Duz `if <ad>:` testi TUKETIM SAYILMAZ —
    olculen mutasyon tam olarak onu birakip donguyu bosaltiyordu.

    Bicime DEGIL VERI AKISINA bakilir ([[kapi-anchor-coupling-ikilemi]]): ad ATAMADAN
    turetilir, harfi harfine `c_hata` aranmaz -> mesru yeniden adlandirma sahte-kirmizi
    yakmaz."""
    adlar = [t.id for t in atama.targets[0].elts] if isinstance(
        atama.targets[0], ast.Tuple) else [
            atama.targets[0].id if isinstance(atama.targets[0], ast.Name) else None]
    hata_adi = adlar[0] if adlar else None
    if not hata_adi:
        return ["BOLUM C TESISATI OLCULEMEDI: kendini_test() sonucu bir ADA "
                "baglanmiyor (fail-closed KIRMIZI)"]
    # 🔴 "HERHANGI BIR DONGUDE GECIYOR" YETMEZ (olculdu, oz-koruma mutant 17): main()'de
    # IKI dongu var — `--kendini-test` kolunda RAPORLAYAN (print) ve BLOKLAYICI kolda
    # BIRIKTIREN. Mutasyon yalniz BIRIKTIRENI bosaltiyordu (`for h in []:`), raporlayan
    # dongu yerinde kaliyor ve zayif olcum tatmin oluyordu. Sart: ad HATA
    # BIRIKTIRICISINE (`hatalar`) akmali.
    if _hatalara_akiyor_mu(main_dugumu,
                           lambda d: isinstance(d, ast.Name) and d.id == hata_adi):
        return []
    return [BOLUM_C_TESISAT_TANI % (hata_adi, hata_adi, hata_adi)]


def bolum_b(dizin):
    """(hatalar, etkili_cagri_sayisi, iddia_sayisi, adim_iddia_sayisi).

    Bolum B'nin semantigi "BIR CAGRI GERCEKTEN KOSUYOR MU" oldugu icin kapinin KENDI ic
    self-test cagrisi da BURADA olculur (oz_cagri_kontrol) — ayni sinif, ayni bolum.
    K-29 ADIM TURU iddialari da ayni desendedir (dosya bazli POZITIF) -> burada kosar."""
    yol = os.path.join(dizin, B_IS_AKISI)
    if not os.path.exists(yol):
        return ["CAGRI NOBETI: %s bulunamadi (%s) -> hedeflerin kostugu is akisi kalkmis, "
                "olcum yapilamadi (fail-closed KIRMIZI)" % (B_IS_AKISI, yol)], 0, 0, 0
    hatalar = list(oz_cagri_kontrol()) + list(bolum_kablosu_kontrol())
    hatalar.extend(tablo_sayaci_kontrol())
    hatalar.extend(b_capraz_hatalari())
    # 🔴 SONUC ARA DEGISKENE ALINMAZ (olculdu, bu turun oz-koruma mutasyonu 13):
    # `adim_hata, adim_iddia = b_adim_hatalari(dizin)` + `hatalar.extend(adim_hata)`
    # yaziminda IKINCI satiri silmek CAGRIYI birakip SONUCU atiyordu -> AST kablo
    # nobetcisi (cagri duruyor) tatmin oluyor, K-29 iddialari GERCEK dosyalar icin
    # sessizce dusuyordu. Inline cagri bu deligi KAPATIR: extend'i silen CAGRIYI da
    # siler ve KABLO_TABLOSU konusur. Iddia SAYISI ayri ve TABLO_TABANLARI ile korumali.
    hatalar.extend(b_adim_hatalari(dizin)[0])
    adim_iddia = len(B_ADIM_IDDIALARI)
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
    return hatalar, toplam, len(B_IDDIALAR), adim_iddia


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


def kapi_cagrilari(metin, capalar, serit_b_joblar=()):
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
    D_IZIN beyan mekanizmasi ona da uygulanir.

    🔴 31 TEM EKI — SERIT AYRIMI: `serit_b_joblar` icindeki bir job'da kosan cagri da
    SEBEPLIDIR ("CI'da VAR ama yayini BLOKLAMAZ"). Beyani D_IZIN'de DEGIL SERIT_B
    tablosunda aranir (bkz. bolum_d) — cunku burada kaybi karsilayan sey "baska bir
    nobetci" degil, adimin SERIT B'ye ait olmasinin GEREKCESIDIR."""
    bulunan = []
    for job_id, adim_no, adim_adi, adim_sebep, s, pf in icra_satirlari(metin):
        for yol, onek in capalar:
            if not onek.match(s):
                continue
            sebep = list(adim_sebep)
            if job_id in serit_b_joblar:
                sebep.append(SERIT_B_SEBEP % job_id)
            sebep.extend(satir_sebepleri(s, yol, pf))
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
#   D3b (K-21a, 30 Tem) 🔴 "VAR OLMAK" YETMIYORDU: D3 yalnizca `os.path.exists`
#       bakiyordu, yani `CNAME` · `README.md` · `urunler.json` gibi NOBETCI OLMAYAN
#       herhangi bir mevcut yol muafiyeti gecerli kiliyordu. Dayanagin ISE YARAMASI
#       icin UC sart daha olculur:
#         (a) dayanak KESFEDILMIS bir kabul testi/kapi olmali (kesif ci-kapsam-test.py'den
#             IMPORT edilir, aynalanmaz) — yoksa "nobetci" bir veri dosyasi olabilir;
#         (b) dayanak deploy.yml'de FIILEN KOSUYOR olmali — kosmayan bir nobetci
#             "kaybi karsilamaz" (bu depoda OLCULDU: muaf listesindeki testlerin bir
#             kismi sessizce OLU cikti, madde 31/31b);
#         (c) dayanak, muafiyeti alan KAPININ KENDISI olamaz — kendi kendini
#             dayanak gostermek dairesel bir beyandir ve hicbir sey olcmez.
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


# ---- SERIT B BEYANI: yayini BLOKLAMAYAN job'da BILEREK kosan kapilar --------
# ANAHTAR : (is_akisi_dosya_adi, job_id, kapi_yolu)   — UCU DE TAM, joker YASAK
# DEGER   : GEREKCE metni (bos olamaz)
#
# 🔴 KURALLAR (kacis deligi olmasin diye dordu birden isler):
#   S1  gerekce BOS/bosluk            -> KIRMIZI (gerekcesiz serit degisimi yok)
#   S2  anahtarin herhangi bir alani `*` ya da bos -> KIRMIZI (BLANKET BEYAN YASAK;
#       "hepsini B'ye at" tek satirla yapilamaz, her adim TEK TEK beyan edilir)
#   S3  giris artik yayini bloklamayan bir cagriya karsilik gelmiyor -> KIRMIZI
#       (bayat beyan; liste kendiliginden buyuyup kalamaz)
#   S4  BEYANSIZ bir kapi cagrisi serit B job'unda bulunursa -> KIRMIZI (fail-closed)
#
# SERIT SECIM OLCUTU (spec, 31 Tem): "yanlis/eksik/sizintili icerik canliya cikmasin"
# diyen HER kapi SERIT A'dadir. Buraya YALNIZ aracin KENDINI sinadigi kapilar girer:
# mutasyon bataryalari · `--kendini-test` / `--ic-nobetci` kollari · CI/kapi meta
# kapilari · pano/teshis araci testleri · onizleme ve ayri-dagitim arayuz testleri.
# SUPHEDE A (fail-closed). Bir kapiyi buraya tasimak = KraL KARARI, tek basina alinmaz.
SERIT_B = {
    # --- R2 ONEK GELENEGI NOBETI (7 Agu 2026) — GERCEK olcum kolu da burada ----------
    # 🔴 ISTISNAI GIRIS: tabloya kural olarak yalniz "aracin KENDINI sinamasi" girer;
    # burada GERCEK tarama kolu (bayraksiz) B'dedir. GEREKCE (olculdu):
    #   (a) ONCEDEN VAR OLAN canli gercegi RAPORLAR: taranan yuzey katalogda ZATEN
    #       duran R2 anahtarlaridir. Yayini durdurmanin TAMIR DEGERI SIFIR — sapan
    #       anahtari yayindan alikoymak sayfayi 404 yapar, gorseli ONARMAZ (ayni R2
    #       anahtarinin uzerine yazmak bu depoda YASAK).
    #   (b) Kirmizinin sahibi KraL DEGIL: bir eksen urun VERISI duzlemindedir (baska
    #       mimarin sahasi), digeri kardes depodaki ikiz tanimla ayrisma (mimar karari
    #       bekliyor) -> bloklayici seritte TUM EKIBIN yayini baskasinin kuyrugunda
    #       beklerdi.
    #   (c) ONLEME kolu CI'da DEGIL kaynagin kendisindedir: r2_anahtar.gkey() bilinmeyen
    #       platformda FAIL-CLOSED (BilinmeyenPlatform) firlatir -> yeni sapma yazim
    #       aninda durur; bu kol GORUNURLUK hattidir.
    #   (d) Bedel olculdu: urunle ILGISIZ bir kapinin yayini durdurmasi bu depoda
    #       6 saatlik canli 404 pencereleri acti ([[kapi-birikimi-yayin-gecikmesi]]).
    ("nobet.yml", "r2-onek-nobeti", "tools/r2-onek-gelenek-kapisi.py"):
        "ONLEME r2_anahtar.gkey()'in FAIL-CLOSED yolundadir (bilinmeyen platform "
        "BilinmeyenPlatform firlatir); CI kolu GORUNURLUK hattidir. Kapi ONCEDEN VAR "
        "OLAN canli anahtarlari raporlar — yayini durdurmanin tamir degeri SIFIR "
        "(sapan anahtari yayindan alikoymak sayfayi 404 yapar, gorseli onarmaz; ayni "
        "R2 anahtarinin uzerine yazmak yasaktir). Bugun kirmizi yanan iki eksenin "
        "sahibi bu duzlem degil: biri urun VERISI, digeri kardes depodaki ikiz tanim.",
    # --- COMMIT MESAJI SIZINTI NOBETI (1 Agu 2026) — GERCEK olcum kolu da burada -----
    # 🔴 ISTISNAI GIRIS: bu tabloya kural olarak yalniz "aracin KENDINI sinamasi"
    # girer; burada GERCEK tarama kolu (`--ci`) da B'dedir. GEREKCE (olculdu):
    #   (a) deploy.yml YALNIZ `push: branches: [main]` ile ve PUSH'TAN SONRA kosar. O an
    #       commit ZATEN public remote'tadir ve commit MESAJI nesnenin degistirilemez
    #       parcasidir -> yayini durdurmanin TAMIR DEGERI SIFIRDIR (tek onarim tarihce
    #       yeniden yazimi + force-push'tur, Okan kapisi).
    #   (b) Commit mesaji SITEDE GORUNMEZ -> "sizintili icerik canliya cikmasin" sinifi
    #       DEGILDIR; serit secim olcutu bu adimi A'ya cagirmaz.
    #   (c) ONLEME kolu CI'da degil `commit-msg` KANCASINDADIR (fail-closed,
    #       tools/commit-mesaji-hook-kur.py) — CI kolu GORUNURLUK hattidir.
    #   (d) Olculen bedel: urunle ILGISIZ bir kapinin yayini durdurmasi bu depoda
    #       6 saatlik canli 404 pencereleri acti ([[kapi-birikimi-yayin-gecikmesi]]).
    ("nobet.yml", "mesaj-nobeti", "tools/commit-mesaji-kapisi.py"):
        "ONLEME `commit-msg` KANCASINDADIR (fail-closed); CI kolu ikinci hattir. "
        "Yayini durdurmanin tamir degeri SIFIR: deploy.yml push'tan SONRA kosar, "
        "commit zaten public'tir ve commit mesaji nesnenin DEGISTIRILEMEZ parcasidir; "
        "ayrica commit mesaji sitede GORUNMEZ (canliya cikan icerik sinifi degil).",
    # --- GECMIS GERI-DONUS NOBETI (1 Agu 2026) — GERCEK olcum kolu da burada --------
    # 🔴 ISTISNAI GIRIS, kardes commit-mesaji girisiyle AYNI gerekce zinciri:
    #   (a) deploy.yml push'TAN SONRA kosar; geri gelen commit'ler o an ZATEN public
    #       remote'tadir -> yayini durdurmanin TAMIR DEGERI SIFIRDIR (tek onarim yine
    #       tarihce yeniden yazimi + force-push, Okan kapisi).
    #   (b) Commit mesaji ve gecmisteki blob sitede GORUNMEZ -> "sizintili icerik
    #       canliya cikmasin" sinifi DEGILDIR.
    #   (c) ONLEME kolu CI'da degil `pre-push` KANCASINDADIR (fail-closed,
    #       tools/gecmis-geri-donus-hook-kur.py) — CI kolu ikinci hat/gorunurluktur.
    #   (d) Bedel olculdu: urunle ILGISIZ bir kapinin yayini durdurmasi bu depoda
    #       6 saatlik canli 404 pencereleri acti ([[kapi-birikimi-yayin-gecikmesi]]).
    ("nobet.yml", "mesaj-nobeti", "tools/gecmis-geri-donus-kapisi.py"):
        "ONLEME `pre-push` KANCASINDADIR (fail-closed); CI kolu ikinci hattir. "
        "Yayini durdurmanin tamir degeri SIFIR: deploy.yml push'tan SONRA kosar ve "
        "geri getirilen commit'ler o an zaten public'tir; ayrica commit mesaji ile "
        "gecmisteki blob sitede GORUNMEZ (canliya cikan icerik sinifi degil).",
    # --- YAYIN GECIKME NOBETCISI (1 Agu 2026) — GERCEK OLCUM KOLU CI'DA HIC YOK ------
    # 🔴 ISTISNAI GIRIS: yukaridaki kardeslerinde "gercek olcum kolu SERIT A'da
    # bloklayici kosuyor" denir; burada gercek olcum kolu CI'DA HICBIR SERITTE KOSMAZ
    # ve bu BILEREK boyledir. GEREKCE (1 Agu'ta olculdu): nobetci "canli, main'den ne
    # kadar geride" sorusunu olcer; YALNIZ CI'da kossaydi hat tikandigi anda O DA
    # KOSAMAZDI -> tam ihtiyac aninda susardi (o gun 20 commit birikene, 6 kosum ust
    # uste dusene ve canli ~1,5 saat bayatlayana kadar kimse fark etmedi). Olcum kolu
    # bu yuzden ELLE ve `tools/durum.py` bolum 9'dan kosar; CI'da yalnizca AGSIZ
    # fikstur/kablolama kabulu vardir. tools/yayin-gecikme-test.py :: 4a iddiasi
    # bayraksiz (olcum yapan) bir cagrinin deploy.yml'e sizmasini KIRMIZI yakar.
    ("nobet.yml", "serit-b", "tools/yayin-gecikme-test.py"):
        "Aracin KENDINI sinamasi: 15 AGSIZ fikstur + pano/bagimsizlik kablolamasi. "
        "Gercek olcum kolu CI'da BILEREK kosmaz (olctugu hatta bagimli olmasin diye), "
        "elle + tools/durum.py bolum 9'dan kosar; 'canliya sizintili icerik cikmasin' "
        "sinifi DEGILDIR, yayini durdurmasi olculmus zarardir.",
    # --- YAYIN ERISIM NOBETCISI (3 Agu 2026) — GERCEK OLCUM KOLU CI'DA HIC YOK ------
    # 🔴 ISTISNAI GIRIS, yayin-gecikme kardesiyle AYNI sinif: gercek olcum kolu CI'da
    # HICBIR SERITTE kosmaz ve bu BILEREK boyledir. Nobetci "yayinladigimiz sayfa
    # canlida GERCEKTEN ACIK MI" sorusunu CANLI GET ile olcer; aga bagimli bir kapiyi
    # `deploy`in onune koymak tek gecici DNS/oran-siniri hatasinda TUM EKIBIN yayinini
    # durdururdu ([[kapi-kapsam-eksen-secimi]]) — bu depoda kapi birikmesi yayin
    # suresini 21 gunde 15,6x uzatti ve musteriye 404 olarak yansidi
    # ([[kapi-birikimi-yayin-gecikmesi]]). Olcum kolu bu yuzden AYRI, seyrek kosan bir
    # alarm is akisindadir (.github/workflows/yayin-erisim-alarmi.yml — saatlik cron,
    # `push` tetikleyicisi YOK, ayri concurrency grubu). CI'da yalnizca YEREL fikstur
    # sunucusuyla (127.0.0.1, dis ag YOK) kosan kabul testi vardir;
    # tools/yayin-erisim-test.py :: E7 ekseni, bayraksiz (olcum yapan) bir cagrinin
    # deploy.yml'e sizmasini KIRMIZI yakar.
    ("nobet.yml", "serit-b", "tools/yayin-erisim-test.py"):
        "Aracin KENDINI sinamasi: yerel HTTP fikstur sunucusu (dis ag YOK) + kume "
        "turetimi + kablolama nobetleri. Gercek olcum kolu CI'da BILEREK kosmaz "
        "(aga bagimli yanlis-pozitif tum ekibin yayinini durdurur); canli kol "
        "yayin-erisim-alarmi.yml cron'unda kosar. 'Canliya sizintili icerik cikmasin' "
        "sinifi DEGILDIR.",
    # --- oz-nobetci / kendini-test kollari (gercek olcum kolu SERIT A'da BLOKLAYICI) ---
    ("nobet.yml", "serit-b", "tools/diriltme-kapisi.py"):
        "YALNIZ `--kendini-test` kolu; silinmis urun diriltme OLCUMU (bayraksiz kol) "
        "serit A'da bloklayici kosuyor.",
    # --- GIT BAGLAM SCRUB'I / TEK KAYNAK DRIFT NOBETI (6 Agu 2026) -----------------
    # Modulun BAYRAKSIZ kolu bir OLCUM DEGILDIR (yardim metni basar); tek kabul kolu
    # `--kendini-test`tir, yani giris "aracin KENDINI sinamasi" sinifina TAM oturur.
    # Serit A'ya konmadi cunku olctugu sey CANLIYA CIKAN ICERIK degil, kapilarin
    # KOK TURETIMININ tek kaynaktan gelmesidir: ikiz bir tanim belirse bile o gunun
    # yayini yanlis/sizintili icerik TASIMAZ — ama kapilar worktree/kanca baglaminda
    # sessizce yanlis agaci olcmeye baslar. Ikinci katman zaten SERIT A'dadir:
    # ic-rapor-adi-kapisi.py::IDDIA-6, spec-ifsa-kapisi.py::IDDIA-KOK3 ve
    # diriltme-kapisi.py::W1-W4 ayni onarimi DAVRANISSAL olcer (gercek worktree +
    # gercek commit + gercek kanca), yani bu adim TEK savunma hatti DEGILDIR.
    ("nobet.yml", "serit-b", "tools/git_ortami.py"):
        "YALNIZ `--kendini-test` kolu (scrub davranisi + `GIT_BAGLAM_DEGISKENLERI` "
        "ikinci-tanim/drift nobeti); bayraksiz kol olcum YAPMAZ. 'Canliya sizintili/"
        "yanlis icerik cikmasin' sinifi DEGILDIR — kok turetiminin TEK KAYNAKTAN "
        "gelmesini olcer. Ayni onarimin DAVRANISSAL ayagi serit A'da bloklayici "
        "kosuyor (ic-rapor-adi-kapisi.py --kendini-test :: IDDIA-6 ve "
        "spec-ifsa-alarmi.yml'deki spec-ifsa-kapisi.py --kendini-test :: IDDIA-KOK3).",
    ("nobet.yml", "serit-b", "tools/fikstur-git-sizinti-kapisi.py"):
        "Sentetik/gecici git depolarinin miras GIT_* baglamiyla ana depoya yonelmesini "
        "sinif olarak olcen nobet ve davranissal kendi testi; ayni gun yeni bir yayin "
        "bloklayicisi eklenmemesi karariyla serit-b'de, deploy needs zincirinde DEGIL.",
    ("nobet.yml", "serit-b", "tools/ege-bilgi-tavan-test.py"):
        "YALNIZ `--ic-nobetci` kolu (30 gecici fikstur); canli ege-bilgi.md tavan olcumu "
        "serit A'da bloklayici kosuyor.",
    ("nobet.yml", "serit-b", "tools/ege-kabiliyet-kapisi.py"):
        "YALNIZ `--ic-nobetci` kolu (73 fikstur); canli ege-bilgi.md kabiliyet-siniri "
        "hukmu serit A'da bloklayici kosuyor.",
    ("nobet.yml", "serit-b", "tools/konfigur-bundle-kapisi.py"):
        "YALNIZ `--kendini-test` kolu; artefakt DRIFT olcumu serit A'da bloklayici.",
    ("nobet.yml", "serit-b", "tools/sema-bundle-kapisi.py"):
        "YALNIZ `--kendini-test` kolu; sema-bundle DRIFT olcumu serit A'da bloklayici.",
    ("nobet.yml", "serit-b", "tools/konfigur-canli-kapisi.py"):
        "YALNIZ `--kendini-test` (offline karar mantigi + mutasyon) kolu; bu is akisinda "
        "canli karar hic verilmiyor.",
    ("nobet.yml", "serit-b", "tools/canli-saglik-kapisi.py"):
        "YALNIZ `--kendini-test` (offline vaka + mutasyon) kolu; canli saglik olcumu bu "
        "is akisinda kosmuyor.",
    ("nobet.yml", "serit-b", "tools/fiziksel-canli-kapisi.py"):
        "YALNIZ `--kendini-test` (offline karar mantigi + yerel kahin) kolu; canli fiziksel "
        "olcum bu is akisinda kosmuyor.",
    ("nobet.yml", "serit-b", "tools/yasal-sayfa-drift-kapisi.py"):
        "YALNIZ `--kendini-test` (bayatlatma + kirmizi-mutasyon) kolu; GERCEK yasal sayfa "
        "drift olcumu serit A'da bloklayici kosuyor.",
    ("nobet.yml", "serit-b", "tools/onizleme-vaat-kapisi.py"):
        "YALNIZ `--kendini-test` kolu (gecici AYNADA 7 kirmizi-mutant + 3 kontrol "
        "mutanti; canli agaca YAZMAZ, sha256 bas/son esitligi kendi olcer). GERCEK "
        "olcum kolu BAYRAKSIZ cagridir ve serit A'da (`build` job'u) BLOKLAYICI kosar: "
        "11 iddia — uretilemez bolgesi beyan edilmis ailenin satis allowlist'i ile "
        "KESISIMI BOS mu (∅) ve musteri uyari metninin IKI cagri yeri birebir ayni mi. "
        "Yani 'yanlis/uretilemez icerik canliya cikmasin' hukmunu veren kol A'dadir; "
        "buraya YALNIZ kapinin KENDI kirmizi yolunu deneyen mutasyon turu girer "
        "(agac temizken bloklayici kol DAIMA yesildir, kirmizi yolu hic denemez).",
    ("nobet.yml", "serit-b", "tools/varlik-test.py"):
        "YALNIZ `--kendini-test` kolu (eksen 1 `cikarim_kaybi` mutasyon bataryasi; "
        "agsiz, canli agaca YAZMAZ). GERCEK olcum kolu BAYRAKSIZ cagridir ve serit "
        "A'da (`deploy.yml` job `serit-a3`) BLOKLAYICI kosar — 'varliga tasimada icerik "
        "kaybolmasin' hukmunu o kol verir. Buraya YALNIZ kapinin KENDI kirmizi yolunu "
        "deneyen mutasyon turu girer.",
    ("nobet.yml", "serit-b", "tools/bayat-beyan-kapisi.py"):
        "HER IKI kol da (bayraksiz gercek tarama + `--kendini-test` mutasyonu) serit "
        "B'de kosar — komsularindan farkli olarak GERCEK olcum kolu da burada. Gerekce "
        "(KraL karari, 4 Agu 2026): bu bir 'sizintili/uretilemez icerik canliya "
        "cikmasin' A-kapisi DEGIL; kod YORUMU / izlenen .md BEYANI ile olculen "
        "davranisin (hacim.js · yonet.js) ic tutarliligini olcer. Korudugu yuzey "
        "musteriye render edilen icerik degil, kaynak yorumdur; yanlis-pozitifi TUM "
        "ekibin yayinini durdurmasi orantisiz olurdu. Offline, ag YOK, deterministik, "
        "mutasyon DAIMA KOPYAYA (kaynak sha256 bas=son).",
    ("nobet.yml", "serit-b", "tools/denetim-kapisi.py"):
        "YALNIZ `--kendini-test` kolu; urun denetimi `--commit-farki` serit A'da bloklayici.",
    ("nobet.yml", "serit-b", "tools/gramer-artigi-kapisi.py"):
        "YALNIZ `--kendini-test` kolu; canli katalog uzerindeki HAM bloklayici tarama "
        "serit A'da AYRI adim olarak kosuyor.",
    ("nobet.yml", "serit-b", "tools/uretim-butunluk-kapisi.py"):
        "YALNIZ `--kendini-test` kolu (tempfile fiksturu, urun/ ISTEMEZ); yayinlanan "
        "id<->sayfa butunlugu olcumu serit A'da build.py'den SONRA bloklayici kosuyor.",
    ("nobet.yml", "serit-b", "tools/yayin-ic-dil-kapisi.py"):
        "YALNIZ `--kendini-test` kolu (tempfile fiksturu, index.built.html ISTEMEZ); "
        "uretilen ciktinin yorum yuzeyi taramasi serit A'da bloklayici kosuyor.",
    # --- MUTLAK YOL KAPISI (8 Agu 2026) — GERCEK olcum kolu (bayraksiz) da burada ----
    # 🔴 ISTISNAI GIRIS: tabloya kural olarak yalniz "aracin KENDINI sinamasi" girer;
    # burada bayraksiz RAPOR kolu B'dedir. GEREKCE (mimar hukmu, olculdu):
    #   (a) Kapinin KENDI sozlesmesi: bayraksiz kol maruziyeti SAYIYLA basar ve rc=0
    #       verir; bloklayiciya cevirme (`--sifir-tolerans`) ve esik karari MIMARDADIR.
    #       Bloklayici kol, KACIRMA SINIFI kapanmadan ACILMAYACAK.
    #   (b) Raporladigi yuzey ONCEDEN VAR OLAN gercektir (depoda duran betiklerdeki
    #       makineye ozgu kok sabitleri) -> yayini durdurmanin TAMIR DEGERI SIFIR.
    #   (c) Yine de CI'da KOSMASI GEREKIR: olctugu sinif YERELDE DAIMA YESIL yanar
    #       (yol gelistirici makinesinde cozulur, yalniz kosucuda patlar). CI'da hic
    #       kosmayan kapi ise OLU NOBETCIDIR — tools/ci-kapsam-test.py bu dosyayi
    #       7 Agu'dan beri KAPSAMSIZ sayip serit A3'u BLOKLAMISTI (deploy+yayin
    #       skipped, 157 urun mahsur).
    #   (d) Bedel olculdu: urunle ILGISIZ bir kapinin yayini durdurmasi bu depoda
    #       6+ saatlik canli bayatlik pencereleri acti ([[kapi-birikimi-yayin-gecikmesi]]).
    ("nobet.yml", "serit-b", "tools/mutlak-yol-kapisi.py"):
        "BAYRAKSIZ RAPOR KOLU (rc DAIMA 0): kapinin kendi sozlesmesi maruziyeti SAYIYLA "
        "basmaktir; bloklayiciya cevirme (`--sifir-tolerans`) ve esik karari MIMARDADIR "
        "ve kacirma sinifi kapanmadan acilmayacak. Raporladigi yuzey ONCEDEN VAR OLAN "
        "gercektir (depoda duran makineye ozgu kok sabitleri) -> yayini durdurmanin tamir "
        "degeri SIFIR. CI'da kosmasi ZORUNLU cunku olctugu sinif YERELDE DAIMA YESIL yanar; "
        "CI'da hic kosmamak ise kapiyi ci-kapsam-test.py'ye KAPSAMSIZ gosterip serit A3'u "
        "bloklamisti.",
    ("nobet.yml", "serit-b", "tools/yayin-kapisi.py"):
        "YALNIZ `--kendini-test` (aday secimi + 200 sarti) kolu; GERCEK atomik yayin "
        "`yayin` job'unda, yayindan SONRA kosar.",
    # --- LCP ONCULUK KAPISI (9 Agu 2026) — GERCEK tarama kolu da burada --------------
    # 🔴 ISTISNAI GIRIS: tabloya kural olarak yalniz "aracin KENDINI sinamasi" girer;
    # burada gercek tarama kolu da B'dedir (bayrak YOK — tek komut hem tarar hem 8
    # mutantlik bataryayi kosar; bayrak eklemek ci-kapsam-test.py'ye ayri bir alt-kume
    # kapsam borcu yazardi). GEREKCE (olculdu):
    #   (a) Olctugu sinif PERFORMANS gerilemesidir, DOGRULUK hatasi degil: ikiz ayrisirsa
    #       sayfa yine DOGRU gorunur, yalniz LCP gorseli iki kez iner. Urun/odeme/yasal
    #       yuzeye dokunmaz -> yayini durdurmanin tamir degeri yok.
    #   (b) Yine de CI'da KOSMASI GEREKIR: ayrisma tamamen sessizdir ve mevcut hicbir
    #       kapi olcmez; CI'da hic kosmayan kapi OLU NOBETCIDIR
    #       ([[nobetci-cagri-satiri-nobetsiz]]).
    #   (c) Bedel olculdu: urunle ILGISIZ bir kapinin yayini durdurmasi bu depoda 6+
    #       saatlik canli bayatlik pencereleri acti ([[kapi-birikimi-yayin-gecikmesi]]).
    ("nobet.yml", "serit-b", "tools/lcp-onculuk-kapisi.py"):
        "GERCEK TARAMA + MUTASYON kolu (tek komut, bayraksiz). Olctugu sapma bir "
        "PERFORMANS gerilemesidir (preload ile srcset ayrisirsa LCP gorseli IKI KEZ "
        "iner), dogruluk hatasi DEGIL — sayfa her halukarda dogru gorunur ve urun/odeme/"
        "yasal yuzeye dokunmaz, yayini durdurmanin tamir degeri yok. CI'da kosmasi yine "
        "ZORUNLU cunku ayrisma tamamen sessizdir ve mevcut hicbir kapi bu ekseni olcmez; "
        "kosmayan kapi olu nobetcidir.",
    # ═══ MUTASYON SURUCULERI (8 Agu 2026) — KESIF GENISLEMESIYLE KABLOLANANLAR ═══
    # 🔴 ORTAK SINIF GEREKCESI (her giris ASAGIDA AYRICA kendi olcumuyle durur):
    # Bir mutasyon surucusu "kabul testi" DEGIL, bir kabul testinin/kapinin AYIRT
    # EDICILIGINI kanitlayan META araçtir. Olctugu iddia ZATEN baska bir adimda
    # (cogu serit A'da BLOKLAYICI) olculur; surucuyu bloklayici seride koymak
    # CIFT SAYIM olur ve daha kotusu, mutantlar kaynak METNINE capalidir -> hedef
    # kaynagin her MESRU refaktoru TUM EKIBIN yayinini durdururdu
    # ([[kapi-anchor-coupling-ikilemi]]). Depo konvansiyonu bu: A_MUTASYON kumesi ve
    # jenerator/test/kisit-mutasyon.js AYNI gerekceyle B'de/muaf.
    # 🔴 O HALDE NEDEN CI'DA HIC OLMASIN DEGIL DE B'DE OLSUN: kosmayan surucu
    # SESSIZCE CURUR. Olculdu (8 Agu, temiz klon): 43 surucunun 35'i hicbir OTOMATIK
    # is akisinda kosmuyordu ve UCU ZATEN BAYATLAMISTI (rc=1, "capa bulunamadi").
    # B seridi tam bu is icin var: kirmizi GORUNUR olur, yayin DURMAZ.
    # 🔴 BU GIRIS "YENI KABLOLANAN" DEGIL — KESIF GENISLEMESININ ORTAYA CIKARDIGI
    # ESKI BIR BEYANSIZ ADIM. `tools/yayin-sinyali-mutasyon.py` nobet.yml `serit-b`de
    # ZATEN kosuyordu, ama kesif predikati `*-mutasyon.py`yi gormedigi icin bu kapi
    # onu "kapi cagrisi" SAYMIYORDU -> beyan sorusu HIC SORULMAMISTI. Ayni korluk
    # ters yonde de vardi: cagri satiri silinse ci-kapsam-test.py UYARMAZDI.
    ("nobet.yml", "serit-b", "tools/yayin-sinyali-mutasyon.py"):
        "SERIT AYRIMININ KENDI iki yonlu curutme bataryasi (YON A: bloklamayan kirmizi "
        "yayin kosumunu boyamiyor · YON B: yayini DURDURAN kirmizi kosumu KIRMIZI "
        "yapiyor + `deploy: needs` daraltmasi kapali). Bloklayici seride konsaydi "
        "serit ayrimini olcen arac yayin seridini durdururdu — dairesel bagimlilik "
        "(kardesi `tools/serit-bolme-mutasyon.py` ile AYNI gerekce). Olculdu (8 Agu "
        "2026, temiz klon): rc=0, 1,1 s, canli dosyalarin sha256'si bas=son.",
    ("nobet.yml", "serit-b", "tools/kesif-kapsam-mutasyon.py"):
        "META-META surucu: ci-kapsam-test.py'nin KESIF ekseninin canli oldugunu "
        "kanitlar (daraltma VE gevsetme yonu ayri ayri kirmizi; kablolanan surucunun "
        "cagri satiri silinince KAPSAMSIZ kirmizisi yanar). Olctugu kapi "
        "`tools/ci-kapsam-test.py` ZATEN ayni job'da kosuyor -> bloklayici seritte "
        "cift sayim olurdu. Bellekte kosar, canli dosyaya YAZMAZ (sha256 bas=son).",
    ("nobet.yml", "serit-b", "tools/ata-lisans-mutasyon.py"):
        "Olctugu kapinin kendisi CI'da kosuyor; bu surucu onun AYIRT EDICILIGINI "
        "olcer (oldurucu 20/20 KIRMIZI, kontrol 3/3 YESIL). Mutantlar kaynak metnine "
        "capali -> bloklayici seritte mesru refaktor yayini durdururdu. Olculdu "
        "(temiz klon + bos HOME): rc=0, 18,1 s, calisma agaci kirlenmiyor.",
    ("nobet.yml", "serit-b", "tools/d1-sync-durum-mutasyon.py"):
        "d1-sync `--durum` kolunun AYIRT EDICILIGI (18 mutant: her OLDURUCU kirmizi, "
        "her KONTROL yesil). D1 duzlemi bu evin yayin yolunda DEGIL; kirmizisi yayini "
        "durdurmamali. Olculdu (temiz klon + bos HOME): rc=0, 1,8 s, ag YOK.",
    ("nobet.yml", "serit-b", "tools/duzelt-uyum-mutasyon.py"):
        "duzelt.py uyum kapisinin AYIRT EDICILIGI (her eksenin TEK-KIRMIZI mutanti "
        "var). Hedef kaynak urun VERISI duzlemindedir (MaCiT) -> kirmizisinin sahibi "
        "bu ev degil, bloklayici seritte tum ekip baskasinin kuyrugunda beklerdi. "
        "Olculdu (temiz klon + bos HOME): rc=0, 11,7 s.",
    ("nobet.yml", "serit-b", "tools/ege-bilgi-tavan-mutasyon.py"):
        "Ege-bilgi tavan kapisinin ic nobetcisinin AYIRT EDICILIGI (14/14 oldurucu "
        "olduruldu, 3 kontrol yesil). Kapinin KENDI kabul testi "
        "(`ege-bilgi-tavan-test.py --ic-nobetci`) ZATEN ayni job'da kosuyor -> "
        "bloklayicida cift sayim. Olculdu (temiz klon + bos HOME): rc=0, 0,8 s.",
    ("nobet.yml", "serit-b", "tools/gramer-kisaltma-mutasyon.py"):
        "Gramer kisaltma kolunun AYIRT EDICILIGI (8/8 oldurucu, taban oz-test 96 "
        "iddia). Olctugu kapi `gramer-artigi-kapisi.py` ZATEN ayni job'da "
        "`--kendini-test` ile kosuyor. Olculdu (temiz klon + bos HOME): rc=0, 2,6 s.",
    ("nobet.yml", "serit-b", "tools/konfigur-nobet-mutasyon.py"):
        "Konfigur nobetcisinin AYIRT EDICILIGI + AYNANIN KAYNAGA YAZAMADIGI. Sentetik "
        "depo aynasi kurar (urunler.json ve .urun-kaynaklari.json AYNA_HARIC); ag YOK, "
        "URL'ler fikstur dizesi. Olctugu kapi `konfigur-bundle-kapisi.py "
        "--kendini-test` ZATEN ayni job'da. Olculdu (temiz klon + bos HOME): rc=0, "
        "34,9 s — 40 s kablolama esiginin ALTINDA.",
    ("nobet.yml", "serit-b", "tools/mimar-commit-kapisi-mutasyon.py"):
        "Mimar commit kapisinin AYIRT EDICILIGI; mutasyon YALNIZ tempdir kopyasina "
        "uygulanir ('Gercek gate degismedi' satiri bunu basar). Kapinin kendisi "
        "MIMAR DISIPLIN cihazidir ve CI'da bloklayici kosmasi ANLAMSIZDIR (commit "
        "EDILMEYEN .claude kablolamasina bagli, R_YOL sinifi). Olculdu (temiz klon + "
        "bos HOME): rc=0, 9,4 s.",
    ("nobet.yml", "serit-b", "tools/parite-marka-mutasyon.js"):
        "Parite MARKA ekseninin AYIRT EDICILIGI (oldurucilerin hepsi kirmizi, "
        "kontrollerin hepsi yesil). Surucunun kendi beyani: AG/wrangler ISTEMEZ. "
        "Kardesi `tools/parite-mutasyon-test.js` SURE ile muaf (217 s); bu kol 1,2 s. "
        "Olculdu (temiz klon + bos HOME): rc=0, 1,2 s. node ISTER (setup-node "
        "on-kosulu bu job'da zaten var).",
    ("nobet.yml", "serit-b", "tools/reklam-etiket-mutasyon.py"):
        "Reklam etiket kapisinin AYIRT EDICILIGI (oldurucu mutantlarin hepsi TEK "
        "BASINA kirmizi, kontrol YESIL). Olctugu kapi `reklam-etiket-kapisi.py "
        "--kendini-test` ZATEN ayni job'da kosuyor. Olculdu (temiz klon + bos HOME): "
        "rc=0, 10,4 s.",
    ("nobet.yml", "serit-b", "tools/serit-bolme-mutasyon.py"):
        "SERIT AYRIMININ KENDI fail-open kolunun AYIRT EDICILIGI (6 iddia; fail-open "
        "KIRMIZI yaniyor, kontrol YESIL). Bloklayici seride konsaydi serit ayrimini "
        "olcen arac yayin seridini durdururdu — dairesel bagimlilik. Olculdu (temiz "
        "klon + bos HOME): rc=0, 1,0 s.",
    ("nobet.yml", "serit-b", "tools/shop-bayatlik-mutasyon.py"):
        "Shop bayatlik kapisinin AYIRT EDICILIGI (19 mutant, sapma 0). "
        "`shop/wrangler.toml` dosyasini OKUR — wrangler CLI/ag ISTEMEZ. Shop AYRI "
        "dagitim hedefidir (Cloudflare Worker), Pages yayinini bloklamasi yanlis "
        "serit olurdu. Olculdu (temiz klon + bos HOME): rc=0, 20,6 s.",
    ("nobet.yml", "serit-b", "tools/varlik-referans-mutasyon.py"):
        "8 AGU SOMUT VAKASI: kiyas referansi kaydinin ALTI bozuk sekli TEK BASINA "
        "rc=2 mi veriyor (ikisi o gun FAIL-OPEN'di: rc=0 verip YANLIS BEYAN "
        "basiyordu). Kapinin kendi ic nobetcisi `varlik-test.py --kendini-test` ZATEN "
        "ayni job'da -> bloklayicida cift sayim. Canli kaydi yedekler ve sha256 ile "
        "geri yukler. Olculdu (temiz klon + bos HOME): rc=0, 4,9 s.",
    ("nobet.yml", "serit-b", "tools/vitrin-kabul-mutasyon.py"):
        "Vitrin kabul kolunun AYIRT EDICILIGI (6 mutant: her OLDURUCU kirmizi, her "
        "KONTROL yesil). Olctugu kabul testi `jenerator/test/vitrin-kabul.js` serit "
        "A'da BLOKLAYICI kosuyor -> bu surucu bloklayicida CIFT SAYIM olurdu. "
        "Olculdu (temiz klon + bos HOME): rc=0, 33,0 s.",
    ("nobet.yml", "serit-b", "tools/wa-yetki-mutasyon.py"):
        "WhatsApp yetki kapisinin AYIRT EDICILIGI (5/5 mutant tuttu). Numara "
        "ayrimi (wa.me <-> tel:) MARKA kuralidir ve kapisi ayrica kosar; bu surucu "
        "yalniz o kapinin kor olmadigini kanitlar. Olculdu (temiz klon + bos HOME): "
        "rc=0, 0,9 s.",
    ("nobet.yml", "serit-b", "tools/yayin-erisim-mutasyon.py"):
        "Yayin erisim nobetcisinin AYIRT EDICILIGI (her eksenin TEK-KIRMIZI mutanti "
        "var). Nobetcinin GERCEK olcum kolu CI'da HIC kosmaz (ayri cron alarm is "
        "akisi, canli ag); kabul testi `yayin-erisim-test.py` ZATEN bu job'da. "
        "Olculdu (temiz klon + bos HOME): rc=0, 21,4 s, ag YOK.",
    ("nobet.yml", "serit-b", "tools/yedek-gorev-kapsam-mutasyon.py"):
        "yedekle.py'nin ~/.claude AGAC KAPSAMI + jeton DISLAMASI ekseninin AYIRT "
        "EDICILIGI. Surucunun kendi beyani: sahte HOME + sahte git deposu + drive "
        "STUB'u ile izole tempdir'de kosar, GERCEK HOME'a/hedefe YAZMAZ — bos HOME "
        "ile dogrulandi. Yedek duzlemi yayin yolunda DEGIL. Olculdu (temiz klon + "
        "bos HOME): rc=0, 3,0 s.",
    ("nobet.yml", "serit-b", "jenerator/test/dogrula.py"):
        "YALNIZ `--kendini-test` kolu (OpenSCAD yasak nobetcisinin kendi 18 iddiasi); "
        "jenerator ayri dagitim hedefi, Pages ciktisini uretmez.",
    ("nobet.yml", "serit-b", "jenerator/test/kabul.py"):
        "YALNIZ `--kendini-test` kolu — TEST HARNESS'ININ KENDI testi (sahte KIRMIZI / "
        "OLCULEMEDI / silinen test); yayinlanan icerige bakmaz.",
    ("nobet.yml", "serit-b", "jenerator/test/yay-tarama.py"):
        "YALNIZ `--kendini-test` kolu — TARAMA SURUCUSUNUN KENDI testi (izgara "
        "kapsami · fail-closed hukum · olu-eksen paylasimi · hacim.js ayrisma kapisi). "
        "Kardesleri dogrula.py/kabul.py ile AYNI band: yayinlanan icerige BAKMAZ. "
        "🔴 DURUST BEYAN (3 Agu 2026, curutucu duzeltmesi): bayraksiz (GERCEK olcum) "
        "kol OpenSCAD + kardes depodaki uretim modeli istedigi icin CI'da KOSMAZ ve "
        "MERGE KAPISINA DA BAGLI DEGILDIR — YALNIZ YERELDE, ELLE kosulur. Onceki "
        "beyan 'yerelde ve merge kapisinda kosulur' diyordu; olculdu, YALANDI (bu "
        "dize repoda kendi dosyasi + bu beyan + deploy.yml'in --kendini-test satiri "
        "disinda HIC gecmiyor). 🔴 KAPANAN KISIM (3 Agu 2026): hacim.js'e konan +%5 "
        "TAHSILAT mutanti artik `build` job'undaki (BLOKLAYICI) kalibrasyon senkron "
        "kapisinda kirmizi yaniyor — 3. katman dondurulmus kalibrasyon kaynagi, dis "
        "kaynak istemez, 12 aile / 300 set, `yay` DAHIL. 🟡 ACIK KALAN KISIM: o kapi "
        "hacim.js'i KALIBRASYON KAYNAGINA karsi olcer, GERCEK GEOMETRIYE karsi DEGIL; "
        "motor=uretim aileleri (huni · izgara · kasnak · kayis · oring · pervane · "
        "petek · rulman) ile bugun kaynaktan sapan rampa/profil kapsam DISIDIR ve "
        "gerekceleri olculen sapmalariyla kaynak-referans.json::disi_birakilan'da "
        "yazilidir.",
    ("nobet.yml", "serit-b", "jenerator/test/kalibrasyon-senkron.js"):
        "YALNIZ `--mutasyon` kolu (5 oldurucu + 3 kontrol mutant + 3 FAIL-CLOSED "
        "vakasi; hacim.js'in KOPYASINA uygulanir, canli agacin sha256'sini kendi "
        "olcer). GERCEK olcum "
        "kolu BAYRAKSIZ cagridir ve serit A'da (`build` job'u) BLOKLAYICI kosar: "
        "kardes ev yokken 39 iddia / ~3,5 s, `deploy: needs: build` oldugu icin "
        "kirmizisi yayini GERCEKTEN durdurur. Buraya yalniz kapinin KENDI kirmizi "
        "yolunu deneyen batarya girer (agac temizken bloklayici kol DAIMA yesildir, "
        "kirmizi yolu hic denemez) — onizleme-vaat-kapisi ile AYNI desen.",
    ("nobet.yml", "serit-b", "onizleme/test/eslem-olcum.py"):
        "YALNIZ `--kendini-test` kolu; onizleme ayri dagitim hedefi (imaj).",
    ("nobet.yml", "serit-b", "onizleme/test/iki-govde-olcum.py"):
        "YALNIZ `--kendini-test` (agsiz) kolu; onizleme olcum mantigi.",
    ("nobet.yml", "serit-b", "tools/iki-govde-kapisi.py"):
        "YALNIZ `--kendini-test` kolu. Bayraksiz (GERCEK olcum) kol serit A'da "
        "bloklayici kosuyor: 4. iddiasi YAYINLANAN secenekler.js ONIZLEME_PARCALAR "
        "listesi ile uretim eslem json'unun TEK KAYNAK paritesidir; sapinca site "
        "URETILEMEYEN 2-renk parcasi sunar. Ucret ekseni ayrica serit A'da "
        "(shop/test/iki-renk-ucret.mjs).",
    # --- mutasyon bataryalari / CI-kapi meta kapilari -----------------------
    ("nobet.yml", "serit-b", "tools/ara-maliyet-kapisi.py"):
        "IKI KOL DA burada (bayraksiz 600-sorgu olcumu + `--kendini-test` mutasyonu). "
        "Serit A'ya konmadi cunku bayraksiz kol ILK CI kosumunda yanlis-pozitif verip "
        "deploy'u atlatti (kosum 30654284096); kok neden onarildi ama hangi kolun "
        "girildigi SQLite SURUMUNE bagli -> CI davranisi yerelde tam dogrulanamiyor ve "
        "korudugu kaynak (araD1) bu depoda degil. Serit A'ya tasima karari MIMARIN.",
    ("nobet.yml", "serit-b", "tools/nobetci-mutasyon-test.py"):
        "SAF MUTASYON BATARYASI (bolumler A..E): kapilarin kendi kirmizi-yolunu olcer, "
        "yayinlanan hicbir ciktiya bakmaz. Mutant envanteri o dosyanin bolum "
        "TABLOLARINDADIR; buraya SAYI yazilmaz — 8 Agu'da buradaki '17 mutant' beyani "
        "gercek envanterle ayrismis bulundu (A 14 + C 3 + D 6 tablo mutanti + BOLUM E "
        "kollari), yani prozada tutulan sayi sessizce bayatliyor "
        "([[ikiz-tanim-sessiz-ayrisma]]).",
    ("nobet.yml", "serit-b", "tools/ci-kapsam-test.py"):
        "CI KAPSAM KAPISI — olctugu sey CI KABLOLAMASIDIR, yayinlanan icerik DEGIL. "
        "28 Tem'de o gunku 13 fail'in HEPSI bu adimdandi ve 6 SAATLIK 404 pencereleri "
        "acti; kapi KALDIRILMADI, dogru seride konumlandirildi.",
    ("nobet.yml", "serit-b", "tools/paket-tazelik-kapisi.py"):
        "ONIZLEME derleme paketinin (R2 imaj) tazeligi + oz-nobetci kollari; Pages "
        "yayin ciktisini uretmez.",
    # --- pano / teshis araci testleri ---------------------------------------
    ("nobet.yml", "serit-b", "tools/marka-panel-test.py"):
        "Marka DURUM PANOSU (parity-panel/CSV teshis ciktisi) testi; pruvo3d.com'a "
        "hicbir sey yayinlamaz.",
    ("nobet.yml", "serit-b", "tools/panel-mutasyon-test.py"):
        "Ustteki marka-panel-test.py'nin MUTASYON BATARYASI (7 mutant + 1 kontrol); "
        "olctugu sey KABUL TESTININ KENDISI, yayinlanan hicbir cikti DEGIL "
        "(nobetci-mutasyon-test.py ile ayni desen). Korudugu pano zaten serit B'de.",
    ("nobet.yml", "serit-b", "tools/panel-tazeleme-test.js"):
        "Panelin OTOMATIK TAZELEME davranis testi (node DOM saplamasi): tazeleme "
        "kullanicinin aramasini/filtresini/siralamasini SIFIRLAMIYOR mu. Panel bir "
        "TESHIS ciktisidir, Pages'e yayinlanmaz; kendi adimi olmasi kapsamin GORUNUR "
        "olmasi icindir (dolayli cagri ci-kapsam-test.py'de kapsam SAYILMAZ).",
    # --- REKLAM/OLCUM ETIKET KAPSAM NOBETCISI (8 Agu 2026) -----------------------
    # 🔴 ISTISNAI GIRIS: bu tabloya kural olarak yalniz "aracin KENDINI sinamasi"
    # girer; burada GERCEK olcum kolu (bayraksiz) da B'dedir. GEREKCE (olculdu):
    #   (a) SINIF SECIMI: olculen yuzey ZIYARETCIYE GIDEN icerik DEGIL, OLCUM
    #       kablolamasidir. Eksik bir GA etiketi musteriye yanlis/sizintili bir sey
    #       gostermez; bizim reklam butcemizi yanlis okutur. "Yanlis/eksik/sizintili
    #       icerik canliya cikmasin" sinifi DEGILDIR -> serit secim olcutu A'ya
    #       cagirmaz.
    #   (b) TAMIR DEGERI SIFIR: kapi kirmizi yandiginda yayini durdurmak canlida
    #       ZATEN duran (ve ayni eksigi tasiyan) sayfalari yerinde birakir; etiketi
    #       ONARMAZ, yalnizca onarimin yayina inmesini GECIKTIRIR.
    #   (c) ONLEME kolu CI'da degil TEK KAYNAKTADIR: GA blogu build.py::
    #       GA_HEAD_SNIPPET'ten turer ve dort sablon `{ga_head}` capasini kullanir;
    #       bu kol GORUNURLUK hattidir (ikiz ayrismasini + capa dusmesini yakalar).
    #   (d) Bedel olculdu: urunle ILGISIZ bir kapinin yayini durdurmasi bu depoda
    #       6 SAATLIK canli 404 pencereleri acti ([[kapi-birikimi-yayin-gecikmesi]]).
    ("nobet.yml", "serit-b", "tools/reklam-etiket-kapisi.py"):
        "Olculen yuzey ZIYARETCIYE GIDEN icerik DEGIL, OLCUM kablolamasidir (GA "
        "etiketi · riza blogu · url_passthrough/ads_data_redaction · syncUrl'un "
        "reklam parametresi korumasi) -> 'sizintili icerik canliya cikmasin' sinifi "
        "DEGIL. Yayini durdurmanin TAMIR DEGERI SIFIR: kirmizi an canlida ZATEN ayni "
        "eksigi tasiyan sayfalar durur, deploy'u bloklamak yalniz ONARIMI geciktirir. "
        "ONLEME kolu tek kaynaktadir (build.py::GA_HEAD_SNIPPET + `{ga_head}` capasi); "
        "bu kol GORUNURLUK hattidir. `--kendini-test` kolu ayni dosyanin ic nobetcisi.",
    ("nobet.yml", "serit-b", "tools/reklam-url-test.js"):
        "Ustteki kapinin (d) ekseninin DAVRANIS kolu (node DOM/URL saplamasi): "
        "?gclid ile gelen ziyaretci filtreye dokununca parametre URL'de KALIYOR mu + "
        "kapsam GENISLEMEDI mi. Ayni sinif ve ayni gerekce zinciri: olcum kablolamasi, "
        "musteriye giden icerik degil; yayini durdurmanin tamir degeri SIFIR. Kendi "
        "adimi olmasi kapsamin GORUNUR olmasi icindir (dolayli cagri ci-kapsam-test.py "
        "kapsaminda SAYILMAZ).",
    ("nobet.yml", "serit-b", "tools/backfill-koruma-test.py"):
        "marka-kapsama.py --backfill'in VERI KAYBI kapisi: bos hucre dolar, dolu hucre "
        "EZILMEZ/KUCULTULMEZ. Korudugu varlik gitignore'daki YEREL kapsama defteridir "
        "(.marka-kapsama.json) — Pages ciktisina ya da katalog/odeme hattina hicbir sey "
        "yazmaz; CI'da defter zaten YOKTUR, test SENTETIK fiksturle kosar. Bu yuzden "
        "kirmizisi yayini durdurmamalidir; ama CI'da GORUNUR olmalidir cunku arizanin "
        "kendisi (sessiz SET) tam da 'gorunmezlik' sinifindandi.",
    ("nobet.yml", "serit-b", "tools/backfill-mutasyon-test.py"):
        "Ustteki backfill-koruma-test.py'nin MUTASYON BATARYASI (6 mutant + 1 kontrol); "
        "olctugu sey KABUL TESTININ KENDISI. Korudugu kapi serit B'de oldugu icin "
        "batarya da serit B'dedir (panel-mutasyon-test.py ile ayni desen).",
    # --- "SESSIZ UZERINE YAZMA YASAK" kapanis kanitlari (8 Agu 2026) ----------------
    # Okan'in genel kurali ("sessiz uzerine yazma yasak") uc duzlemde kapatildi: hasat
    # muhasebesi (backfill, ustte), GORSEL (R2 anahtari) ve KANIT DEFTERI (parite kaydi).
    # Ucunun de GERCEK kapisi/kabul kolu SERIT A'da bloklayici kosuyor; buraya YALNIZ
    # "kabul testi gercekten olcuyor mu" bataryalari ile aracin KENDINI sinama kolu girer.
    ("nobet.yml", "serit-b", "tools/r2-ezme-mutasyon-test.py"):
        "tools/r2-upload.py EZME-KORUMASININ mutasyon bataryasi (6 mutant + 1 kontrol): "
        "koruma sokuldugunde TEK BASINA KIRMIZI yakiyor mu. Olctugu sey KABUL TESTININ "
        "KENDISI, yayinlanan hicbir cikti DEGIL (backfill-mutasyon-test.py / "
        "panel-mutasyon-test.py ile ayni desen). Korudugu KABUL TESTI "
        "(tools/r2-upload-test.py) SERIT A'da, deploy.yml'de BLOKLAYICI kosuyor; "
        "onleme kolu ise kaynagin kendisindedir (r2-upload.py varsayilanda fail-closed "
        "REDDEDER, ezmek ACIK --ezmeye-izin-ver ister). S3 mock'lanir: gercek R2'ye ne "
        "okuma ne yazma gider, adim ag GEREKTIRMEZ.",
    # --- R1 SIHIRLI-BAYT WHITELIST'I / AVIF EKSENI (9 Agu 2026) --------------------
    ("nobet.yml", "serit-b", "tools/r2-avif-mutasyon-test.py"):
        "tools/r2-upload.py R1 WHITELIST'ININ mutasyon bataryasi (6 mutant + 1 kontrol): "
        "AVIF kabulu marka kumesine BAGLI kaldi mi, yoksa `ftyp` tek basina yeterli "
        "sayilip kapi her ISO-BMFF govdesine (mp4/mov/heic) acildi mi. Olctugu sey KABUL "
        "TESTININ KENDISI, yayinlanan hicbir cikti DEGIL (r2-ezme-mutasyon-test.py / "
        "backfill-mutasyon-test.py ile ayni desen). Korudugu KABUL TESTI "
        "(tools/r2-upload-test.py) SERIT A'da, deploy.yml'de BLOKLAYICI kosuyor; onleme "
        "kolu ise kaynagin kendisindedir (r2-upload.py bilinmeyen govdeyi yukleme "
        "ONCESI fail-closed REDDEDER). S3 mock'lanir: gercek R2'ye ne okuma ne yazma "
        "gider, adim ag GEREKTIRMEZ.",
    ("nobet.yml", "serit-b", "tools/parite-kayit-test.py"):
        "tools/parite_kaydi.py YAZICISININ kabul testi: sayisal alanda gerileme "
        "varsayilanda REDDEDILIYOR mu (dosya BAYT BAYT degismeden), olcu iki kaynaktan "
        "mi aliniyor (mevcut kayit + MONOTON tavan), --kuru-prova tek bayt yazmiyor mu. "
        "SENTETIK gecici kokle kosar: canli jenerator/test/uretilebilirlik-parite.json "
        "ACILMAZ, urunler.json / uretilen sayfa / D1 / R2 / odeme yuzeylerine tek bayt "
        "yazmaz — 'canliya yanlis/sizintili icerik cikmasin' sinifi DEGILDIR. Ayni "
        "sozlesmenin GERCEK okuyucu kapisi (tools/onizleme-vaat-kapisi.py, bayraksiz "
        "kol) SERIT A'da, deploy.yml'de BLOKLAYICI kosmaya devam ediyor.",
    ("nobet.yml", "serit-b", "tools/parite-kayit-mutasyon-test.py"):
        "Ustteki parite-kayit-test.py'nin MUTASYON BATARYASI (8 mutant + 1 kontrol): "
        "tavan blogu bayatlatilarak kapi atlatilamiyor mu. Olctugu sey KABUL TESTININ "
        "KENDISI. Korudugu kabul testi serit B'de oldugu icin batarya da serit B'dedir "
        "(backfill-mutasyon-test.py ile ayni desen). Mutasyon gecici SYMLINK aynasina "
        "uygulanir, canli tools/ dizinine YAZILMAZ.",
    ("nobet.yml", "serit-b", "tools/durum-test.py"):
        "durum.py PANOSUNUN kabul testi; pano bir teshis ciktisidir, yayinlanmaz. "
        "IKI KOL DA bu job'da: bayraksiz (gercek pano ciktisi) + `--ic-nobetci` "
        "(6c sizinti muafiyetinin mutasyon bataryasi). ⚠️ Bu anahtar ARAC YOLU "
        "granulundedir, KOL granulunde DEGIL — yani tek basina bir kolun adimi "
        "silinirse BURASI kirmizi yanmaz. Kol capasi Bolum E'dedir "
        "(E_ZORUNLU_CAGRILAR: iki kol AYRI AYRI beyan edilmistir).",
    ("nobet.yml", "serit-b", "tools/durum-edge-test.py"):
        "durum.py EDGE_KATALOG sayaci (pano bolumu) testi; yayinlanan cikti uretmez.",
    ("nobet.yml", "serit-b", "tools/durum-yedek-test.py"):
        "durum.py '7) YEDEK TAZELIGI' pano bolumunun testi; yayinlanan cikti uretmez.",
    ("nobet.yml", "serit-b", "tools/yedek-sir-eleme-test.py"):
        "yedekle.py'nin SIR ELEMESI + yedek KOKU sir temizligi bataryasi (8 Agu 2026 "
        "Okan karari: jetonlar ortak Drive yedegine girmez). Serit B, cunku olctugu "
        "yuzey YEREL YEDEKLEME ARACIDIR: yayinlanan hicbir bayta dokunmaz (urunler.json/"
        "D1/R2/Pages/odeme yuzeyleri disinda, tamamen hermetik kum havuzunda kosar). "
        "Buradaki kirmizi 'yedek araci curudu' der, 'site bozuk' DEMEZ — yayini "
        "durdurmak yanlis olurdu ([[kapi-birikimi-yayin-gecikmesi]]). Kardesi "
        "durum-yedek-test.py ile AYNI serit ve AYNI gerekce.",
    ("nobet.yml", "serit-b", "tools/derin-cap-test.py"):
        "Hasat adaptorlerinin `--derin` pagination ayrimi (urun EKLEME araci) testi; "
        "yayin hattinda hicbir sey uretmez.",
    ("nobet.yml", "serit-b", "tools/d1-sync-tani-test.py"):
        "d1-sync HATA TANISI METNININ testi; GERCEK D1 yazma/geri-okuma nobeti "
        "(`d1-sync.py --kendini-test`) serit A'da bloklayici kaldi.",
    ("nobet.yml", "serit-b", "tools/d1-sync-durum-test.py"):
        "d1-sync DURUM TANISI aracinin testi; gercek yazma nobeti serit A'da.",
    ("nobet.yml", "serit-b", "tools/d1-seq-test.py"):
        "D1 seq tam-sayi ve kanonik-sira hesaplarinin agsiz kabul/mutasyon testi; "
        "gercek D1 yazma/geri-okuma nobeti serit A'da bloklayici kaldi.",
    ("nobet.yml", "serit-b", "tools/test-baski-senkron.py"):
        "Baski senkron ARACININ kabul testi; yayinlanan Pages ciktisini uretmez.",
    ("nobet.yml", "serit-b", "tools/edge-flip-hazirlik-test.py"):
        "EDGE_KATALOG bayragi icin SAF KARAR MANTIGI araci; yayinlanan icerigi "
        "uretmez/degistirmez.",
    ("nobet.yml", "serit-b", "tools/faz3-gecikme-test.py"):
        "Teshis araci faz3-gecikme.js'in yanlis-pozitif/negatif nobetcisi (sahte worker "
        "ucu); yayin ciktisi ekseninde degil.",
    ("nobet.yml", "serit-b", "tools/faz3-sayfalama-test.py"):
        "Teshis araci faz3-sayfalama.js'in 'OLCULEMEDI vs BOZUK' nobetcisi (sahte "
        "katalog ucu, yalniz 127.0.0.1). Kardesi faz3-gecikme-test.py ile AYNI serit: "
        "olctugu sey TESHIS ARACININ hukmu, yayinlanan icerik DEGIL — urunler.json'u "
        "yalniz OKUR, uretilen sayfa/D1/R2/odeme yuzeylerine dokunmaz, tek bayt "
        "yayinlamaz. Buradaki kirmizi 'nobetci curudu' der, 'site bozuk' DEMEZ; yayini "
        "durdurmak yanlis olurdu ([[kapi-birikimi-yayin-gecikmesi]]). Bir A-kapisinin "
        "buraya kaydirilmasi DEGILDIR: kapinin A karsiligi hic olmadi, arac bu dalda dogdu.",
    ("nobet.yml", "serit-b", "tools/kutu-arsivle-test.py"):
        "HIJYEN ARACI, YAYIN KAPISI DEGIL: tools/kutu-arsivle.py mimarlarin ORTAK POSTA "
        "KUTUSUNU (~/.claude/.../mimar-posta-kutusu.md) tavana indirir. Olctugu sey "
        "yazisma hijyenidir; urunler.json / index.html / uretilen sayfa / D1 / R2 / "
        "odeme yuzeylerinin HICBIRINE dokunmaz, yayinlanan tek bir bayt uretmez. "
        "Kabul testi + `--mutasyon` turu tempfile fiksturleriyle OFFLINE kosar ve "
        "GERCEK kutuya YAZMAZ. Bir A-kapisinin buraya kaydirilmasi DEGILDIR: kapinin "
        "A karsiligi hic olmadi, arac bu dalda dogdu.",
    ("nobet.yml", "serit-b", "tools/kanca-nobeti-test.py"):
        "YEREL GELISTIRME ORTAMI NOBETCISININ MANTIK TESTI, YAYIN KAPISI DEGIL: "
        "tools/kanca-nobeti.py ANA CHECKOUT'un git kancalarinin sessizce devre disi "
        "kalip kalmadigini olcer (1 Agu: `.git/config`'e `core.hooksPath = /dev/null` "
        "sizdi, D1 senkronu + commit guard'i hic kosmadi ve hicbir yerde kirmizi "
        "yanmadi). NOBETCININ KENDISI CI'DA KOSAMAZ: yargiladigi dosya "
        "`<ana>/.git/config`'tir ve CI ayri bir klon yapar, `.git/` commit'lenmez. "
        "Nobetci YEREL iki yoldan atesler (tools/durum.py bolum 8 + "
        "tools/yedek-hook-kur.py kurulum-sonrasi dogrulamasi); CI'ya baglanan sey "
        "yalnizca MANTIGIN kendisidir. Kabul testi + `--mutasyon` turu tempfile "
        "icinde SENTETIK git depolari kurar, GERCEK depoya DOKUNMAZ ve urunler.json / "
        "index.html / uretilen sayfa / D1 / R2 / odeme yuzeylerinin HICBIRINE "
        "dokunmaz — yayinlanan tek bir bayt uretmez. Buradaki kirmizi 'nobetcinin "
        "mantigi curudu' der, 'site bozuk' DEMEZ; yayini durdurmak yanlis olurdu "
        "([[kapi-birikimi-yayin-gecikmesi]]). Bir A-kapisinin buraya kaydirilmasi "
        "DEGILDIR: kapinin A karsiligi hic olmadi, arac bu dalda dogdu.",
    # --- KANCA KABLOLAMASI (4 Agu 2026) — ICERIK KOLU SERIT A'DADIR ---------
    # 🔴 AYRIM ACIK OLSUN: bu ailenin ICERIK kapisi
    # `tools/kanca-kablolama-nobeti.py --ci` adimidir ve SERIT A'da (job
    # `serit-a3`) BLOKLAYICI kosar — izlenen kanca kaynagi fail-open'a donerse
    # yayin DURUR. Asagidaki TEK giris (betik `kanca-kablolama-test.py`) o
    # kapinin degil, ARACIN KENDISININ sinamasidir; serit kuralinin "aracin
    # kendini sinamasi" maddesine girer. Betik iki adimda kosar (bayraksiz kabul
    # + `--mutasyon`); ikisi de bu tek giriste kapsanir.
    ("nobet.yml", "serit-b", "tools/kanca-kablolama-test.py"):
        "ARACIN KENDINI SINAMASI, YAYIN KAPISI DEGIL. Bu dosya iki kolu birden "
        "kosar: (a) bayraksiz kabul testi — tempfile icinde SENTETIK git depolari "
        "kurup GERCEK `git commit` ile 'eski govde gecti / izlenen govde durdu'yu "
        "olcer; (b) `--mutasyon` — kendi mutant bataryasi. IKISI DE tamamen "
        "OFFLINE'dir, GERCEK depoya / gercek `~/.gitconfig`e (sahte HOME + "
        "GIT_CONFIG_GLOBAL/SYSTEM katmanlari) DOKUNMAZ ve urunler.json · "
        "index.html · uretilen sayfa · D1 · R2 · odeme yuzeylerinin HICBIRINE "
        "dokunmaz — yayinlanan tek bir bayt uretmez. Buradaki kirmizi 'nobetcinin "
        "kabul testi curudu' der, 'site bozuk' DEMEZ; yayini durdurmak yanlis "
        "olurdu ([[kapi-birikimi-yayin-gecikmesi]]). ICERIK ekseni ZATEN serit "
        "A'da bloklar (`kanca-kablolama-nobeti.py --ci`), yani bir A-kapisinin "
        "buraya kaydirilmasi DEGILDIR: A kolu YERINDE DURUYOR.",
    # --- onizleme (ayri dagitim hedefi) arayuz testleri ---------------------
    ("nobet.yml", "serit-b", "onizleme/test/onbellek-surum.mjs"):
        "ONIZLEME alt sisteminin (ayri imaj dagitimi) onbellek surumu; Pages ciktisini "
        "uretmez.",
    ("nobet.yml", "serit-b", "onizleme/test/renk-yazi-gorunurluk.mjs"):
        "ONIZLEME ARAYUZU (viewer) gorunurluk testi; Pages ciktisini uretmez.",
    ("nobet.yml", "serit-b", "onizleme/test/iki-govde-kabul.mjs"):
        "ONIZLEME worker parca ucu + viewer kabulu (+ kirmizi-mutasyon turu); ayri "
        "dagitim hedefi.",
    # --- KATALOG ENVANTERI isi (RAPOR kolu; bloklayici kol serit A'da) ------
    ("nobet.yml", "envanter", "tools/denetim-kapisi.py"):
        "YALNIZ `--tum-katalog --envanter` (RAPOR) kolu. Bu kol TAM katalogu tarar ve "
        "ONCEDEN VAR OLAN kayitlari sayar; bugun 104 kayit KIRMIZI olurdu ve bloklayici "
        "baglansaydi TUM EKIBIN yayini dururdu. BLOKLAYICI kol AYNEN SERIT A'da duruyor: "
        "`--commit-farki` (job `build`) yeni/degisen her kaydi ayni sertlikte bloklar. "
        "KURAL: yeni/degisen kayit BLOKLAR · tam katalog RAPORLAR. Katalog okunamazsa "
        "rc 2 ile KIRMIZI yanar (olu nobetci olamaz).",
    # --- CRON NABZI isi (ALARM kolu; yayin kusuru DEGIL) --------------------
    ("nobet.yml", "cron-nabzi", "tools/cron-nabiz-kapisi.py"):
        "ZAMANLANMIS DENETIM NABZI — olctugu sey GitHub'in TETIKLEME MOTORU ve "
        "zamanlanmis denetimlerin TAZELIGIDIR, yayinlanan icerik DEGIL. Bu isin "
        "kirmizisi 'denetim yapilmiyor' der; o hal bir YAYIN kusuru degildir ve yayini "
        "durdurmak yanlis olurdu (olculdu: kapi birikmesi bu depoda yayin suresini "
        "21 gunde 15,6x uzatti ve musteriye 404 olarak yansidi -> "
        "[[kapi-birikimi-yayin-gecikmesi]]). Iki kol da burada: `--kendini-test` (agsiz "
        "fikstur) ve GERCEK API olcumu. Veri cekilemezse rc 2 ile KIRMIZI yanar "
        "(fail-closed; olu nobetci olamaz). 1 Agu: A4 PAKET ekseni eklendi — elle "
        "yayinlanan shop Worker'inin bayatligi (1 Agu: 14,5 saat, %84'e varan fazla "
        "tahsilat) ancak burada GORUNUR olur; olcumun KENDISI yayin yolundan ayri bir "
        "zamanlanmis is akisindadir (paket-tazelik-alarmi.yml, `push` tetikleyicisi YOK).",
    # --- JENERATOR HACIM TAM TAKIMI (2 Agu 2026) — DIS BAGIMLILIKLI, ELLE TETIK ----
    # Job `hacim-tam-takim` yalniz `workflow_dispatch` ile kosar ve `deploy` ona
    # `needs:` ile BAGLI DEGILDIR -> serit B. BILEREK boyle: bu iki kolun TAM kosumu
    # OpenSCAD (nightly AppImage + xvfb) ve iki DIS kaynak ister (private kardes depo
    # jetonu + gizli uretim paketi secret'i). Bloklayici `build` yoluna baglansaydi
    # jeton/secret baglanana kadar TUM EKIBIN yayini dururdu; ayrica OpenSCAD kurulumu
    # + 22 aile render'i yayin yolunu dakikalarca uzatirdi. Kusuru yayini durdurmaz
    # ama SESSIZ de kalmaz: on-kosul adimi eksik secret'ta OLCULEMEDI deyip KIRMIZI
    # yanar (fail-closed) ve kosum CI'da GORUNUR.
    # 🔴 Bu iki kolun `--kendini-test` KARDESLERI serit A'da BLOKLAYICI kosuyor
    # (job `serit-b` degil, `build`): kapinin kendi kablolamasi orada olculur.
    ("nobet.yml", "hacim-tam-takim", "jenerator/test/dogrula.py"):
        "Jeneratör TAM TAKIMI serit B'de: bayraksiz `--hepsi` kolu OpenSCAD + private "
        "kardes depo jetonu + gizli uretim paketi ister; bloklayici yola baglansaydi "
        "jeton/secret baglanana kadar tum ekibin yayini dururdu ve yayin yolu render "
        "suresince uzardi. Kusuru yayini DURDURMAZ ama sessiz kalmaz: eksik secret'ta "
        "on-kosul adimi OLCULEMEDI deyip KIRMIZI yanar. `--kendini-test` kolu serit "
        "A'da bloklayici kosuyor.",
    ("nobet.yml", "hacim-tam-takim", "jenerator/test/kabul.py"):
        "Jeneratör TAM TAKIMI serit B'de: bayraksiz kabul kolu TEST 1'i (hacim vs "
        "render) icerdigi icin ayni OpenSCAD + dis kaynak zincirine bagimlidir; "
        "bloklayici yola baglanmasi ayni yayin durdurma bedelini dogururdu. Kusuru "
        "yayini DURDURMAZ ama sessiz kalmaz (fail-closed on-kosul + CI'da gorunur "
        "adim). `--kendini-test` kolu serit A'da bloklayici kosuyor.",
    # --- MARKA SAYFASI ARTIM/FILTRE DAVRANISI (8 Agu 2026) -----------------
    ("nobet.yml", "serit-b", "tools/marka-artim-test.py"):
        "ISTEMCI DAVRANISI olcer (artimli kart cizimi + sayfa-ici model filtresi), "
        "yayin DOGRULUGUNU degil. Marka sayfasinin SSR yuzeyi — kart yuzeyi kimligi, "
        "bolum ayrimi (cakisma IHLAL), agirlik tavani, teslim yolunun kanonikligi — "
        "BLOKLAYICI seritte tools/marka-sayac-kapisi.py'de ZATEN olculuyor; bu adim o "
        "yuzeyin ISTEMCI ucunu (fetch gercekten cagrildi mi, kart cizdi mi, adres "
        "degismiyor mu, JS-siz hal saglam mi) node'da kosturur. Kirmizisi 'kalan kartlar "
        "artimli cizilmiyor' der — SSR'de basili N kart + duz bag listesi JS-siz halde "
        "ZATEN gorunur oldugu icin sayfa yine dogru ve eksiksiz linklidir, yayini "
        "durdurmanin tamir degeri yoktur.",
    ("nobet.yml", "serit-b", "tools/marka-bolum-mutasyon.py"):
        "Marka bolum kimligi kapisinin ayirt ediciligini iki katmanda mutasyonla olcer; "
        "agsiz ve deterministiktir. Yayin dogrulugunu degil nobetcinin KENDI koruma "
        "gucunu sinadigi icin serit B'de kosar; fail-closed kirmizisi gorunur kalir ama "
        "yayin yolunu durdurmaz.",
    ("nobet.yml", "serit-b", "tools/marka-sayfa-mutasyon.py"):
        "Marka tek-sayfa hukmunun 13 oldurucu ve 5 kontrol mutantiyla ayirt "
        "ediciligini olcer; agsiz ve deterministiktir. Yayin dogrulugunu degil "
        "nobetcinin KENDI koruma gucunu sinadigi icin serit B'de kosar; fail-closed "
        "kirmizisi gorunur kalir ama yayin yolunu durdurmaz.",
    ("nobet.yml", "serit-b", "tools/model-uyelik-kapisi.py"):
        "Aracin KENDINI sinayan 35 oldurucu + 7 kontrol mutasyon bataryasidir; "
        "bayraksiz GERCEK katalog olcumu deploy.yml serit-a3'te BLOKLAYICI kalir. "
        "Mutantlar gecici kopyaya uygulanir, yayinlanan icerigi uretmez; kirmizisi "
        "kapinin ayirt ediciliginin curudugunu soyler, katalogun bozuk oldugunu degil.",
    ("nobet.yml", "serit-b", "tools/model-baslik-kolu-test.py"):
        "Aracin KENDINI sinayan 18 oldurucu + 4 kontrol mutasyon bataryasidir; "
        "bayraksiz GERCEK katalog olcumu deploy.yml serit-a3'te BLOKLAYICI kalir. "
        "Mutantlar gecici kopyaya uygulanir, yayinlanan icerigi uretmez; kirmizisi "
        "kapinin ayirt ediciliginin curudugunu soyler, katalogun bozuk oldugunu degil.",
    # --- yayin SONRASI job (yapisal olarak yayini bloklayamaz) --------------
    ("deploy.yml", "yayin", "tools/yayin-kapisi.py"):
        "ATOMIK YAYIN adimi YAPISAL OLARAK yayindan SONRA kosar (`needs: deploy`): "
        "canli 200 dogrulanan taslaklari 'yayinda'ya alir. Yayini bloklamasi zaten "
        "MANTIKSIZ olurdu; buradaki kirmizi taslaklari TASLAK birakir (fail-closed).",
}

SERIT_B_SEBEP = ("yayini BLOKLAMAYAN job (`%s`) — `deploy` bu job'a `needs:` ile "
                 "BAGLI DEGIL (serit B)")

SERIT_B_TANI = (
    "SERIT B'DE BEYANSIZ KAPI: %s -> `%s`\n"
    "   is akisi: %s · job: %s · adim %d %s\n"
    "   NEDEN BLOKLAYICI: bu job kirmizi yansa da `deploy` KOSAR -> adim CI'da GORUNUR\n"
    "   ama yayini DURDURMAZ. Bir A-kapisini etkisizlestirmenin en ucuz yolu onu buraya\n"
    "   TASIMAKTIR (silmeye ya da `|| true` yazmaya gerek yok).\n"
    "   COZUM: adim SERIT A'ya (job `build`) geri tasinmali; BILEREK serit B ise\n"
    "   tools/is-akisi-kapisi.py::SERIT_B tablosuna (is_akisi, job, kapi_yolu) -> GEREKCE\n"
    "   olarak TEK TEK yaz. Joker (`*`) KABUL EDILMEZ; toplu beyan yapilamaz.")


def _serit_b_hijyen(kullanilan):
    """SERIT_B tablosunun KACIS DELIGI HIJYENI (S1/S2/S3). `kullanilan` = bu kosumda
    GERCEKTEN yayini bloklamayan bir cagriya karsilik gelen anahtarlar."""
    hatalar = []
    for anahtar, gerekce in sorted(SERIT_B.items()):
        etiket = "%s :: %s :: %s" % anahtar
        if not (isinstance(anahtar, tuple) and len(anahtar) == 3):
            hatalar.append("SERIT_B anahtari (is_akisi, job, kapi) UCLUSU DEGIL: %r"
                           % (anahtar,))
            continue
        if any((not isinstance(a, str)) or (not a.strip()) or ("*" in a)
               for a in anahtar):
            hatalar.append(
                "SERIT_B BLANKET/JOKER BEYAN: %s -> anahtarin her alani TAM ve joker(`*`)"
                "SIZ olmali. Toplu beyan tam da onlenmek istenen seydir: tek satirla "
                "butun kapilar yayini bloklamaz hale getirilebilirdi." % etiket)
            continue
        if not (isinstance(gerekce, str) and gerekce.strip()):
            hatalar.append("SERIT_B GEREKCESIZ giris (bos gerekce): %s" % etiket)
        if anahtar not in kullanilan:
            hatalar.append(
                "SERIT_B BAYAT giris (artik yayini bloklamayan bir kapi cagrisina "
                "karsilik gelmiyor — SIL ya da adimi geri tasi): %s" % etiket)
    return hatalar


# ---------------------------------------------------------------------------
# BOLUM F — BLOKLAYICI-BEYAN DOGRULAMASI (4 Agu 2026, olculmus delik)
# ---------------------------------------------------------------------------
# 🔴 OLCULEN OLAY: `run: python3 tools/kanca-kablolama-nobeti.py --ci` adimi
# `mesaj-nobeti` job'una (needs YOK, deploy'a bagli DEGIL -> BLOKLAMAYAN)
# konmustu; ama UC yer "SERIT A'da, job serit-a3, BLOKLAYICI" diyordu (deploy.yml
# yorumu, RAPOR, SERIT_B gerekcesi). is-akisi-kapisi bunu KACIRDI cunku:
#   (a) `kanca-kablolama-nobeti.py` ci-kapsam KESIF kuralina (`-test.py`/`-kapisi.py`)
#       UYMAZ (`-nobeti.py`) -> Bolum D onu bir "kapi cagrisi" olarak HIC gormedi;
#   (b) hicbir eksen "bu adim BLOKLAYICI olmali" BEYANINI GERCEGE karsi olcmuyordu.
# Yani kapi beyanin VARLIGINI olcuyordu, DOGRULUGUNU degil ([[ikiz-tanim-sessiz-
# ayrisma]], [[hukum-yanlis-birimde]]) — uc curutme turu tam bu yuzden gecti.
#
# Bu bolum IKI YONLU dogrular (TEK KAYNAK: `_serit_b_joblar` = yayini bloklamayan
# joblar; ayni fonksiyon Bolum D'de de kullanilir, kopya YOK):
#   YON 1 (BLOKLAYICI beyan): BLOKLAYICI_KAPILAR'daki her (is_akisi, hedef) FIILEN
#          yayini BLOKLAYAN bir job'da ETKILI kosmali. Adim yoksa / etkisizse /
#          yalniz BLOKLAMAYAN job(lar)da ise -> KIRMIZI.
#   YON 2 (BLOKLAMAZ beyan): SERIT_B'deki her (is_akisi, job, kapi) girisinin
#          job'u GERCEKTEN yayini bloklamayan kumede olmali. Girisin job'u
#          BLOKLAYAN bir job ise "yanlis GUVENLI beyani" -> KIRMIZI.
#
# ANAHTAR : (is_akisi_dosya_adi, hedef_betik_yolu)
# DEGER   : GEREKCE metni (neden BLOKLAYICI olmali; bos -> KIRMIZI).
BLOKLAYICI_KAPILAR = {
    ("deploy.yml", "tools/kanca-kablolama-nobeti.py"):
        "izlenen kanca kaynagi (`tools/kancalar`) fail-open'a donerse (biri "
        "`|| true` geri koyar ya da guard cagrisini siler) o kaynak main'e girip "
        "`kanca-kur.py` ile HER makineye yayilir ve katalog guard'i · D1 senkronu · "
        "mimar kapisi · mukerrer · commit-mesaji sizinti kapisi SESSIZCE susar. "
        "Bu PUSH-ONCESI kaynak butunlugu eksenidir; is-akisi-kapisi'nin kendisi "
        "gibi yayini BLOKLAMALI (deploy: needs zincirinde).",
}

BLOKLAYICI_TANI_YOK = (
    "BLOKLAYICI BEYAN AMA ADIM YOK/ETKISIZ: %s -> `%s`\n"
    "   BLOKLAYICI_KAPILAR bu kapinin yayini BLOKLAYAN bir job'da ETKILI kosmasini\n"
    "   beyan ediyor ama %s'de ETKILI bir cagri BULUNAMADI%s.\n"
    "   COZUM: adimi deploy: needs zincirindeki bir job'a (or. build/serit-a3) ETKILI\n"
    "   (fail-open'suz) ekle, ya da beyan bayatsa BLOKLAYICI_KAPILAR'dan cikar.")

BLOKLAYICI_TANI_BLOKLAMAZ = (
    "BLOKLAYICI BEYAN GERCEGE UYMUYOR: %s -> `%s`\n"
    "   Adim(lar) SU JOB(LAR)DA: %s — hepsi yayini BLOKLAMAYAN job (deploy bunlara\n"
    "   `needs:` ile bagli DEGIL). Beyan 'BLOKLAYICI' diyor, GERCEK 'bloklamaz' ->\n"
    "   BEYAN/GERCEK AYRISMASI (bugun kacirilan vaka: adim mesaj-nobeti'ndeydi).\n"
    "   COZUM: adimi deploy: needs zincirindeki bir job'a (build/serit-a2/serit-a3)\n"
    "   TASI. Yayini bloklayan job kumesi: %s.")

BLOKLAYICI_TANI_SERITB = (
    "SERIT_B GIRISININ JOB'U BLOKLAYICI (yanlis GUVENLI beyani): %s\n"
    "   SERIT_B bu girisi 'yayini BLOKLAMAYAN job'da kosuyor' diye beyan ediyor,\n"
    "   ama `%s` job'u FIILEN yayini BLOKLAYAN kumede (deploy: needs zinciri). Yani\n"
    "   giris bir A-kapisini yanlislikla 'guvenli B' diye etiketliyor.\n"
    "   COZUM: ya adimi gercekten bloklamayan bir job'a tasi ya girisi SERIT_B'den cikar.")


def bloklayici_kapi_kontrol(dizin, kapilar=None, serit_b_tablo=None):
    """(hatalar, iddia) — BLOKLAYICI/BLOKLAMAZ beyanlari GERCEGE karsi dogrular.

    TEK KAYNAK: yayini bloklamayan job kumesi `_serit_b_joblar`tan gelir (Bolum D
    ile ayni); "bloklayan" = o kumenin TUMLEYENI. Boylece iki bolum ayni gercegi
    olcer, sessizce ayrisamaz ([[ikiz-tanim-sessiz-ayrisma]]).

    `kapilar`/`serit_b_tablo` = kendini-test'in SENTETIK registry ile olcmesi icin;
    None ise CANLI BLOKLAYICI_KAPILAR / SERIT_B kullanilir."""
    if kapilar is None:
        kapilar = BLOKLAYICI_KAPILAR
    if serit_b_tablo is None:
        serit_b_tablo = SERIT_B
    hatalar = []
    iddia = 0
    # Is akisi bazinda serit_b_joblar'i (ve tumleyeni "bloklayan") bir kez coz.
    _onbellek = {}

    def serit_ayrimi(ad):
        if ad in _onbellek:
            return _onbellek[ad]
        yol = os.path.join(dizin, ad)
        if not os.path.exists(yol):
            sonuc = (None, None, None, "%s bulunamadi" % ad)
            _onbellek[ad] = sonuc
            return sonuc
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        govde, ayr_hata = ayristir(metin)
        if ayr_hata or not isinstance(govde, dict):
            sonuc = (metin, None, None, "%s ayristirilamadi: %s" % (ad, ayr_hata or "?"))
            _onbellek[ad] = sonuc
            return sonuc
        serit_b, sb_tani = _serit_b_joblar(govde, ad)
        if serit_b is None:
            sonuc = (metin, None, None, sb_tani)
            _onbellek[ad] = sonuc
            return sonuc
        jobs = govde.get("jobs") if isinstance(govde, dict) else {}
        bloklayan = set(jobs) - serit_b if isinstance(jobs, dict) else set()
        sonuc = (metin, serit_b, bloklayan, None)
        _onbellek[ad] = sonuc
        return sonuc

    # YON 1 — BLOKLAYICI beyanlari
    for (ad, hedef), gerekce in sorted(kapilar.items()):
        iddia += 1
        if not (isinstance(gerekce, str) and gerekce.strip()):
            hatalar.append("BLOKLAYICI_KAPILAR GEREKCESIZ giris (bos gerekce): "
                           "%s :: %s" % (ad, hedef))
            continue
        metin, serit_b, bloklayan, tani = serit_ayrimi(ad)
        if serit_b is None:
            hatalar.append("BLOKLAYICI BEYAN OLCULEMEDI (fail-closed KIRMIZI): "
                           "%s :: %s -> %s" % (ad, hedef, tani))
            continue
        etkili_joblar = []
        reddedilen = []
        for job_id, _adim_no, _adim_adi, satir, sebep in etkili_kapi_cagrilari(metin, hedef):
            if sebep:
                reddedilen.append((satir, "; ".join(sebep)))
                continue
            etkili_joblar.append(job_id)
        if not etkili_joblar:
            ek = ""
            if reddedilen:
                ek = " (REDDEDILEN: " + " | ".join(
                    "%r -> %s" % (k[:60], s) for k, s in reddedilen[:2]) + ")"
            hatalar.append(BLOKLAYICI_TANI_YOK % (ad, hedef, ad, ek))
            continue
        if all(j in serit_b for j in etkili_joblar):
            hatalar.append(BLOKLAYICI_TANI_BLOKLAMAZ % (
                ad, hedef, ", ".join(sorted(set(etkili_joblar))),
                ", ".join(sorted(bloklayan)) or "(bos)"))

    # YON 2 — SERIT_B girislerinin job'u GERCEKTEN bloklamayan mi
    for anahtar in sorted(serit_b_tablo):
        if not (isinstance(anahtar, tuple) and len(anahtar) == 3):
            continue  # sekil hatasi _serit_b_hijyen'in isi
        ad, job_id, kapi = anahtar
        iddia += 1
        _metin, serit_b, _bloklayan, tani = serit_ayrimi(ad)
        if serit_b is None:
            hatalar.append("SERIT_B JOB DOGRULAMASI OLCULEMEDI (fail-closed KIRMIZI): "
                           "%s :: %s :: %s -> %s" % (ad, job_id, kapi, tani))
            continue
        if job_id not in serit_b:
            hatalar.append(BLOKLAYICI_TANI_SERITB % (
                "%s :: %s :: %s" % anahtar, job_id))
    return hatalar, iddia


# ---------------------------------------------------------------------------
# BOLUM G — YAYIN SINYALI SAFLIGI (5 Agu 2026, IKI KEZ olculmus yanlis hukum)
# ---------------------------------------------------------------------------
# 🔴 OLCULEN OLAY: GitHub bir KOSUMUN `conclusion`'ini o kosumdaki TUM joblarin en
# kotusunden turetir. deploy.yml icinde yayini BLOKLAMAYAN nobet/alarm joblari da
# vardi; onlarin kirmizisi kosumu `failure` gosteriyordu. 28 ardisik kirmizi kosuma
# bakan mimar "yayin 11 saattir durdu, ~1.500 urun sitede yok" hukmunu verip deftere,
# posta kutusuna ve Okan'a yazdi. JOB duzeyinde olculdugunde o 28 kosumun 14'unde
# `deploy`+`yayin` YESIL kosmustu; gercek hasar TEK commit / 447 urundu. Ayni gun bir
# kez daha ekip "deploy kirmizi" sanip yanlis kaynagi aradi.
# Sinif: [[hukum-yanlis-birimde]] — TOPLU SONUC TEKIL EKSENI GIZLER.
#
# HUKUM: kosum kirmizisi YALNIZ "yayini durduran bir ariza var" demeli. Alarmlar
# SUSTURULMAZ; AYRI bir is akisina (nobet.yml) tasinir ve kendi `conclusion`'inda
# gorunur. Bu bolum o ayrimin BEYANINI degil GERCEGINI olcer.
#
# 🔴 KANONIK OLCUT — TEK FONKSIYON: `kosum_sonucu()`. Hem bu kapi hem iki yonlu
# mutasyon bataryasi (tools/yayin-sinyali-mutasyon.py) AYNI simulatoru kullanir;
# kabul araligi ile karsilastirma araligi ayri fonksiyonlardan turetilseydi sessizce
# ayrisirlardi ([[kabul-araligi-karsilastirma-araligi]], [[ikiz-tanim-sessiz-ayrisma]]).
#
# G-IDDIALARI (her biri TEK BASINA kirmizi yakabilmeli — [[beyan-edilmis-survivor]]):
#   G1  deploy.yml'deki HER job yayin job'una `needs:` ile BAGLI (atasi ya da ardili).
#       Bagsiz bir job = kosum rengini boyayan ama yayini durdurmayan alarm.
#   G2  nobet.yml VAR ve `on.push` ile tetiklenir -> alarmin GORUNUR KANALI yasiyor.
#   G3  nobet.yml'de Pages yayin job'u YOK (yayin nobet seridine kaydirilmamis).
#   G4  nobet.yml'deki hicbir JOB `continue-on-error: true` ya da DAIMA-YANLIS `if:`
#       ile susturulmamis -> "bloklamamak" SESSIZ OLMAK DEGILDIR.
#   G5  deploy.yml hicbir job'u nobet.yml'i `uses:` ile CAGIRMIYOR (cagirsaydi nobet
#       joblari yayin grafigine GERI girer ve rengi yine boyardi).
#   G6  nobet.yml `concurrency.cancel-in-progress` FALSE -> ard arda push'ta alarm
#       kosumu OLDURULMEZ (iptal = `cancelled` = nobet hic rapor etmez = gorunurluk
#       kaybi; cozulen kusurun TERSI).
#   G7  SERIT_B kapsami (SERIT_B_DOSYALARI) nobet dosyasini TASIYOR -> 52 beyan
#       denetimsiz kalamaz.
#   G8  `deploy: needs` listesi TABANIN ALTINA DUSMEDI (serit dusurerek "kosum
#       yesillesin" cozumu YASAK; deploy.yml'in kendi yorumu bunu sessiz fail-open
#       sayar).
YAYIN_NEEDS_TABANI = 4          # build · serit-a2 · serit-a3 · serit-a4 (5 Agu 2026)


def _needs_listesi(job):
    """Bir job'un `needs:` degerini LISTE olarak dondur (dize/liste/None hepsi)."""
    if not isinstance(job, dict):
        return []
    ham = job.get("needs")
    if isinstance(ham, str):
        return [ham]
    if isinstance(ham, list):
        return [str(x) for x in ham]
    return []


def _job_susturulmus(job):
    """Job SEVIYESINDE fail-open/olu mu (`continue-on-error: true` · daima-yanlis `if:`).
    ADIM seviyesi Bolum D'nin isidir; burada JOB rengi olculur."""
    if not isinstance(job, dict):
        return None
    if _dogru_mu(job.get("continue-on-error")):
        return "`continue-on-error: true`"
    if "if" in job and _yanlis_mu(job.get("if")):
        return "DAIMA-YANLIS `if: %r`" % (job.get("if"),)
    return None


def kosum_sonucu(govde, kirmizi_joblar):
    """(conclusion, kosan_joblar) — GitHub kosum sonucu SIMULATORU (KANONIK OLCUT).

    Model (GitHub davranisi):
      * bir job ancak TUM `needs:` bagimliliklari BASARILI bitince kosar; biri
        `failure`/`skipped` ise job ATLANIR (`skipped`) ve KENDI kirmizisi DOGMAZ;
      * `continue-on-error: true` tasiyan job basarisiz olsa da kosumun
        `conclusion`'ini KIRLETMEZ (GitHub bunu `success` sayar);
      * kosumun `conclusion`'i: kirletici EN AZ BIR job varsa "failure", yoksa
        "success". Atlanan joblar kosumu kirletmez.

    <kirmizi_joblar>: "bu job kosarsa KIRMIZI biter" varsayimi (mutasyon ekseni).
    Dongusel `needs:` grafiginde cozulemeyen joblar KOSMAZ sayilir (GitHub da
    kosumu baslatmaz); hukum bu yonde fail-closed'dir: cozulemeyen job "yesil"
    sayilmaz, sadece kosmaz."""
    jobs = govde.get("jobs") if isinstance(govde, dict) else None
    if not isinstance(jobs, dict) or not jobs:
        return None, set()
    kirmizi_joblar = set(kirmizi_joblar or ())
    durum = {}                      # job -> "success" | "failure" | "skipped"
    kalan = list(jobs)
    while True:
        ilerledi = False
        for job_id in list(kalan):
            gerekli = [n for n in _needs_listesi(jobs[job_id]) if n in jobs]
            if any(n not in durum for n in gerekli):
                continue
            if any(durum[n] != "success" for n in gerekli):
                durum[job_id] = "skipped"
            elif job_id in kirmizi_joblar:
                durum[job_id] = "failure"
            else:
                durum[job_id] = "success"
            kalan.remove(job_id)
            ilerledi = True
        if not kalan or not ilerledi:
            break
    kirletici = [j for j, d in durum.items()
                 if d == "failure" and not _dogru_mu(jobs[j].get("continue-on-error"))]
    kosan = set(j for j, d in durum.items() if d in ("success", "failure"))
    return ("failure" if kirletici else "success"), kosan


def _yayin_zinciri(jobs, yayin):
    """Yayin job'una `needs:` ile BAGLI job kumesi (atalari + ardillari + kendisi).

    ATA  = yayini BLOKLAYAN (kirmizisi yayini durdurur).
    ARDIL= yayindan SONRA kosan dogrulama (`yayin` job'u): kirmizisi yayin
           ZINCIRININ KENDI kusurudur, "alarm" degildir -> kosumu boyamasi DOGRUDUR."""
    ata = {yayin}
    degisti = True
    while degisti:
        degisti = False
        for job_id in list(ata):
            for n in _needs_listesi(jobs.get(job_id)):
                if n in jobs and n not in ata:
                    ata.add(n)
                    degisti = True
    ardil = {yayin}
    degisti = True
    while degisti:
        degisti = False
        for job_id, job in jobs.items():
            if job_id in ardil:
                continue
            if any(n in ardil for n in _needs_listesi(job)):
                ardil.add(job_id)
                degisti = True
    return ata | ardil, ata


G1_TANI = (
    "YAYIN SINYALI KIRLENIYOR: %s icindeki `%s` job'u yayin zincirine BAGLI DEGIL\n"
    "   (`%s` job'unun ne atasi ne ardili). Kirmizisi yayini DURDURMUYOR ama KOSUMUN\n"
    "   genel `conclusion`'ini `failure` yapiyor -> 'yayin durdu' YANLIS HUKMU.\n"
    "   OLCULDU (5 Agu): 28 ardisik kirmizi kosumun 14'unde deploy+yayin YESILDI;\n"
    "   yanlis hukum deftere/posta kutusuna/Okan'a yazildi.\n"
    "   COZUM: job'u `%s` is akisina TASI (susturma DEGIL — ayni komut, ayni cikis\n"
    "   kodu, AYRI conclusion). Yayini GERCEKTEN bloklamasi gerekiyorsa `deploy:\n"
    "   needs` listesine ekle.")


def yayin_sinyali_kontrol(dizin, nobet_dosyasi=None):
    """(hatalar, iddia) — BOLUM G. Yayin kosumunun rengi YALNIZ yayin zincirini anlatir.

    `nobet_dosyasi` None ise canli N_DOSYA kullanilir (kendini-test sentetik ad verir).
    Her eksen AYRI bir iddiadir; hicbiri digerinin arkasina saklanmaz."""
    if nobet_dosyasi is None:
        nobet_dosyasi = N_DOSYA
    hatalar = []
    iddia = 0

    def oku(ad):
        yol = os.path.join(dizin, ad)
        if not os.path.exists(yol):
            return None, None, "%s bulunamadi" % ad
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        govde, hata = ayristir(metin)
        if hata or not isinstance(govde, dict):
            return metin, None, "%s ayristirilamadi: %s" % (ad, hata or "?")
        return metin, govde, None

    _e_metin, e_govde, e_tani = oku(E_DOSYA)
    _n_metin, n_govde, n_tani = oku(nobet_dosyasi)

    # ---- G1: yayin is akisinda BAGSIZ job YOK -------------------------------
    iddia += 1
    if e_govde is None:
        hatalar.append("G1 OLCULEMEDI (fail-closed KIRMIZI): %s" % e_tani)
        e_jobs, yayin, zincir, ata = {}, None, set(), set()
    else:
        e_jobs = e_govde.get("jobs") if isinstance(e_govde.get("jobs"), dict) else {}
        yayin = _yayin_isi(e_jobs)
        if yayin is None:
            hatalar.append("G1 OLCULEMEDI (fail-closed KIRMIZI): %s icinde Pages yayin "
                           "job'u (`uses: %s...`) YOK -> yayin zinciri tanimsiz"
                           % (E_DOSYA, YAYIN_ACTION_ONEKI))
            zincir, ata = set(), set()
        else:
            zincir, ata = _yayin_zinciri(e_jobs, yayin)
            for job_id in sorted(set(e_jobs) - zincir):
                hatalar.append(G1_TANI % (E_DOSYA, job_id, yayin, nobet_dosyasi))

    # ---- G8: `deploy: needs` listesi KUCULMEDI ------------------------------
    iddia += 1
    if yayin is None:
        hatalar.append("G8 OLCULEMEDI (fail-closed KIRMIZI): yayin job'u bulunamadi -> "
                       "`needs` genisligi olculemedi")
    else:
        dogrudan = [n for n in _needs_listesi(e_jobs.get(yayin)) if n in e_jobs]
        if len(dogrudan) < YAYIN_NEEDS_TABANI:
            hatalar.append(
                "G8 `%s: needs` LISTESI KUCULDU: %d serit kaldi, TABAN %d (%s).\n"
                "   🔴 Bir seridi listeden dusurmek o seritteki kapilarin kirmizisini "
                "yayini DURDURMAZ hale getirir = SESSIZ FAIL-OPEN. Sinyal ayrimi bu "
                "listeyi DARALTARAK yapilamaz.\n"
                "   Bilerek daraltiliyorsa (serit birlestirme) TABANI da NEDENIYLE "
                "birlikte guncelle." % (yayin, len(dogrudan), YAYIN_NEEDS_TABANI,
                                        ", ".join(sorted(dogrudan)) or "(bos)"))

    # ---- G2: alarmin GORUNUR KANALI yasiyor ---------------------------------
    iddia += 1
    if n_govde is None:
        hatalar.append(
            "G2 ALARM KANALI YOK (fail-closed KIRMIZI): %s\n"
            "   🔴 Nobet is akisi olmadan bloklamayan alarmlar ya deploy.yml'e geri "
            "doner (renk kirlenir) ya da HIC KOSMAZ (sessizlik). Susturma cozum "
            "DEGILDIR — bugunku hatanin tersi kadar pahaliya patlar." % n_tani)
    elif not tetikleyici_var(n_govde, "push"):
        hatalar.append(
            "G2 ALARM KANALI TETIKLENMIYOR: %s `on.push` TASIMIYOR (alt anahtarlar: %s)\n"
            "   -> alarmlar main'e push'ta HIC kosmaz; kirmizi 'bir yerde gorunur' "
            "sarti duser." % (nobet_dosyasi, _on_alt_anahtarlari(n_govde)))

    # ---- G3: yayin nobet seridine kaydirilmamis ------------------------------
    iddia += 1
    if n_govde is None:
        hatalar.append("G3 OLCULEMEDI (fail-closed KIRMIZI): %s" % n_tani)
    else:
        n_jobs = n_govde.get("jobs") if isinstance(n_govde.get("jobs"), dict) else {}
        n_yayin = _yayin_isi(n_jobs)
        if n_yayin is not None:
            hatalar.append(
                "G3 YAYIN NOBET SERIDINE TASINMIS: %s icinde Pages yayin job'u `%s` VAR.\n"
                "   -> Bu dosyanin TUM joblari 'bloklamaz' sayiliyordu; yayin buraya "
                "girerse o hukum YANLISLASIR ve gercek yayin arizasi B seridine "
                "kaydirilmis olur." % (nobet_dosyasi, n_yayin))

    # ---- G4: nobet joblari SUSTURULMAMIS ------------------------------------
    iddia += 1
    if n_govde is None:
        hatalar.append("G4 OLCULEMEDI (fail-closed KIRMIZI): %s" % n_tani)
    else:
        n_jobs = n_govde.get("jobs") if isinstance(n_govde.get("jobs"), dict) else {}
        for job_id in sorted(n_jobs):
            sebep = _job_susturulmus(n_jobs[job_id])
            if sebep:
                hatalar.append(
                    "G4 ALARM SUSTURULMUS: %s :: `%s` job'u %s tasiyor.\n"
                    "   🔴 Bloklamamak SESSIZ OLMAK DEGILDIR: bu yazimla nobet kirmizisi "
                    "KENDI kosumunun conclusion'inda da GORUNMEZ olur ve 'alarm bir "
                    "yerde gorunur kalmali' sarti duser (fail-open yazimi bu depoda "
                    "nobetci ihlalidir)." % (nobet_dosyasi, job_id, sebep))

    # ---- G5: nobet, yayin grafigine GERI baglanmamis -------------------------
    iddia += 1
    if e_govde is None:
        hatalar.append("G5 OLCULEMEDI (fail-closed KIRMIZI): %s" % e_tani)
    else:
        cagri = "./.github/workflows/%s" % nobet_dosyasi
        for job_id, job in sorted(e_jobs.items()):
            if isinstance(job, dict) and str(job.get("uses") or "").strip() == cagri:
                hatalar.append(
                    "G5 NOBET YAYIN GRAFIGINE GERI BAGLANDI: %s :: `%s` job'u `uses: %s` "
                    "ile nobet seridini CAGIRIYOR -> cagrilan joblar bu kosumun job "
                    "grafiginde kosar ve kirmizilari yine YAYIN kosumunun rengini "
                    "boyar (ayrim fiilen geri alinmis olur)."
                    % (E_DOSYA, job_id, cagri))

    # ---- G6: alarm kosumu IPTALLE oldurulmuyor -------------------------------
    iddia += 1
    if n_govde is None:
        hatalar.append("G6 OLCULEMEDI (fail-closed KIRMIZI): %s" % n_tani)
    else:
        ham = n_govde.get("concurrency")
        iptal = ham.get("cancel-in-progress") if isinstance(ham, dict) else None
        if _dogru_mu(iptal):
            hatalar.append(
                "G6 ALARM KOSUMU IPTALLE OLDURULUYOR: %s :: `concurrency."
                "cancel-in-progress: true`.\n"
                "   -> Ard arda push'ta calisan nobet kosumu OLDURULUR, `conclusion` "
                "`cancelled` olur ve alarm HIC rapor etmez. Bu, cozulen kusurun TERSI: "
                "gorunurluk kaybi. (`false` ya da hic yazmamak dogrudur.)"
                % nobet_dosyasi)

    # ---- G7: SERIT_B kapsami nobet dosyasini TASIYOR -------------------------
    iddia += 1
    if nobet_dosyasi not in SERIT_B_DOSYALARI:
        hatalar.append(
            "G7 SERIT_B KAPSAMI NOBET DOSYASINI TASIMIYOR: `%s` SERIT_B_DOSYALARI "
            "icinde YOK.\n"
            "   -> Bolum D o dosyadaki kapi cagrilarini 'serit B' saymaz; %d beyan "
            "BIR ANDA denetimsiz kalir ve bir A-kapisini oraya kaydirmak BEYANSIZ "
            "mumkun olurdu (SERIT_B tam bunu engellemek icin var)."
            % (nobet_dosyasi, sum(1 for a, _j, _k in SERIT_B if a == nobet_dosyasi)))
    return hatalar, iddia


def _kosan_kapilar(dizin):
    """(kesif_kumesi, kosan_kume, tani) — K-21a dayanak dogrulamasi icin.

    `kosulan()` deploy.yml'i ister. Mutasyon kosumlarinda `--dizin` gecici bir kopyayi
    gosterebilir; orada deploy.yml yoksa GERCEK depo dosyasina duselir (D_IZIN bir
    DEPO BEYANIDIR, gecici bir kopyanin ozelligi degil). Ikisi de yoksa (None, None,
    tani) doner ve cagiran FAIL-CLOSED davranir."""
    mod = _ci_kapsam_modulu()
    if mod is None:
        return None, None, _CI_KAPSAM_HATA
    if not hasattr(mod, "kosulan"):
        return None, None, ("tools/ci-kapsam-test.py'de kosulan() YOK -> kesif "
                            "sozlesmesi degismis, D_IZIN dayanak kurallarini guncelle")
    try:
        kesif = mod.kesfet()
    except Exception as e:  # noqa: BLE001
        return None, None, "kesif cagrilamadi (%s: %s)" % (type(e).__name__, e)
    for aday in (os.path.join(dizin, E_DOSYA),
                 os.path.join(WORKFLOW_DIZIN, E_DOSYA)):
        if os.path.exists(aday):
            with open(aday, encoding="utf-8") as f:
                return set(kesif), set(mod.kosulan(f.read(), kesif)), None
    return set(kesif), None, "%s hicbir yerde bulunamadi" % E_DOSYA


def bolum_d(dizin):
    """(hatalar, olculen_kapi_cagrisi, etkisiz_sayisi, izinli_sayisi)."""
    capalar, capa_hata = kapi_capalari()
    if capalar is None:
        return ["ETKISIZLESTIRME NOBETI OLCULEMEDI (fail-closed KIRMIZI): %s"
                % capa_hata], 0, 0, 0
    hatalar = []
    toplam = 0
    etkisiz_anahtarlar = set()
    serit_b_kullanilan = set()
    for yol in is_akisi_dosyalari(dizin):
        ad = os.path.basename(yol)
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        # SERIT AYRIMI — DOSYA BAZLI POZITIF (Bolum E ile ayni disiplin,
        # [[kapi-kapsam-genisletme-tuzagi]]): kapsam SERIT_B_DOSYALARI'dir.
        # 🔴 5 Agu 2026: kapsam deploy.yml'den (deploy.yml + nobet.yml)'e GENISLETILDI.
        # Bloklamayan joblar nobet.yml'e tasinirken bu satir GUNCELLENMESEYDI 52
        # SERIT_B beyani TEK COMMIT'te denetimsiz kalirdi (tasima = beyan rejiminden
        # cikis) — tam da SERIT_B'nin engellemek icin var oldugu kacis. Kapsamin bu iki
        # dosyayi tasidigi Bolum G'de AYRICA olculur (ikiz tanim yok, TEK sabit).
        # Diger is akislarinda Pages yayini YOKTUR ve oraya kapi tasimak zaten
        # ci-kapsam-test.py'nin kuresel kapsam olcumunde gorunur.
        serit_b_joblar = set()
        if ad in SERIT_B_DOSYALARI:
            govde, ayr_hata = ayristir(metin)
            if ayr_hata:
                hatalar.append("SERIT AYRIMI OLCULEMEDI (fail-closed KIRMIZI): %s "
                               "ayristirilamadi -> %s" % (ad, ayr_hata))
            else:
                bulunan_b, sb_tani = _serit_b_joblar(govde, ad)
                if bulunan_b is None:
                    hatalar.append("SERIT AYRIMI OLCULEMEDI (fail-closed KIRMIZI): "
                                   "%s -> %s" % (ad, sb_tani))
                else:
                    serit_b_joblar = bulunan_b
        for job_id, adim_no, adim_adi, kapi, komut, sebep in kapi_cagrilari(
                metin, capalar, serit_b_joblar):
            toplam += 1
            if not sebep:
                continue
            # SERIT B sebebi AYRI bir beyan mekanizmasina gider (D_IZIN'e DEGIL):
            # kaybi karsilayan sey "baska bir nobetci" degil, adimin serit B'ye
            # ait olmasinin GEREKCESIDIR.
            serit_sebebi = [s for s in sebep if s.startswith("yayini BLOKLAMAYAN job")]
            diger_sebep = [s for s in sebep if not s.startswith("yayini BLOKLAMAYAN job")]
            if serit_sebebi:
                s_anahtar = (ad, job_id, kapi)
                serit_b_kullanilan.add(s_anahtar)
                if s_anahtar not in SERIT_B:
                    hatalar.append(SERIT_B_TANI % (
                        kapi, komut, ad, job_id, adim_no,
                        ("(%s)" % adim_adi) if adim_adi else ""))
            if not diger_sebep:
                continue
            anahtar = (ad, kapi)
            etkisiz_anahtarlar.add(anahtar)
            if anahtar in D_IZIN:
                continue
            hatalar.append(D_TANI_ONEK % (
                kapi, komut, ad, job_id, adim_no,
                ("(%s)" % adim_adi) if adim_adi else "", " + ".join(diger_sebep)))
    hatalar.extend(_serit_b_hijyen(serit_b_kullanilan))
    # D2/D3/D3b — izin listesi HIJYENI
    kesif_kumesi, kosan_kume, kesif_tani = (
        _kosan_kapilar(dizin) if D_IZIN else (set(), set(), None))
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
        else:
            # D3b (K-21a) — "var olmak" YETMEZ: dayanak GERCEK, KOSAN, BASKA bir
            # nobetci olmali.
            if nobetci == anahtar[1]:
                hatalar.append(
                    "D_IZIN DAIRESEL DAYANAK: %s -> muaf tutulan kapinin KENDISI "
                    "(%s) dayanak gosterilmis. Etkisizlestirilen bir kapi kendi "
                    "kaybini karsilayamaz; BASKA bir nobetcinin yolunu yaz ya da "
                    "muafiyeti kaldir." % (etiket, nobetci))
            elif kesif_kumesi is None:
                hatalar.append("D_IZIN DAYANAK DOGRULAMASI OLCULEMEDI (fail-closed "
                               "KIRMIZI): %s -> %s" % (etiket, kesif_tani))
            elif nobetci not in kesif_kumesi:
                hatalar.append(
                    "D_IZIN DAYANAGI NOBETCI DEGIL: %s -> `%s` repoda VAR ama "
                    "ci-kapsam-test.py kesfinde bir KABUL TESTI / KAPI degil "
                    "(kesif predikatlari: tools/*-test.py · test-*.py · *-kapisi.py · "
                    "shop|onizleme|jenerator/test/*).\n"
                    "   🔴 OLCULEN DELIK (K-21a): eski kural yalnizca `os.path.exists` "
                    "bakiyordu -> `CNAME` ya da `README.md` yazmak muafiyeti gecerli "
                    "kiliyordu ve 'kaybi su nobetci karsiliyor' beyani HICBIR SEY "
                    "olcmuyordu." % (etiket, nobetci))
            elif kosan_kume is None:
                hatalar.append("D_IZIN DAYANAK DOGRULAMASI OLCULEMEDI (fail-closed "
                               "KIRMIZI): %s -> %s" % (etiket, kesif_tani))
            elif nobetci not in kosan_kume:
                hatalar.append(
                    "D_IZIN DAYANAGI CI'DA KOSMUYOR: %s -> `%s` bir kabul testi ama "
                    "%s'de FIILEN kosmuyor (silinmis / yoruma alinmis / `--help`e "
                    "cevrilmis / muaf). Kosmayan bir nobetci kaybi KARSILAMAZ -> "
                    "muafiyetin dayanagi kagit uzerinde kalir."
                    % (etiket, nobetci, E_DOSYA))
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
# yakip tum yayini durdururdu. Iddia YALNIZ BEYAN EDILEN DOSYALARA capalanir.
#
# 🔴 5 Agu 2026 — DOSYA ALANI EKLENDI (serit ayriminin olculen bedeli): bloklamayan
# joblar nobet.yml'e tasininca 6 zorunlu cagrinin 4'u (ci-kapsam-test.py x2 ·
# durum-test.py x2) ARTIK deploy.yml'de DEGIL. Tablo tek dosyaya capali kalsaydi ya
# kapi sahte-KIRMIZI yanardi ya da (daha kotusu) girisler silinip iddia SESSIZCE
# duserdi. Her giris artik HANGI is akisinda kosmasi gerektigini SOYLER; tetikleyici
# iddiasi da o dosyalarin HEPSI icin ayri ayri olculur (nobet dosyasi `push` ile
# tetiklenmezse alarm hic kosmaz ve "gorunur kanal" iddiasi bosa duserdi).
E_TETIKLEYICILER = ("push",)
# (is_akisi, kapi_yolu, zorunlu_bayrak_ya_da_None, adim_etiketi)
#   bayrak None -> o bayragi TASIMAYAN (yani ana/bayraksiz kolu kosan) bir cagri sart
E_ZORUNLU_CAGRILAR = (
    (N_DOSYA, "tools/ci-kapsam-test.py", None,
     "CI kapsam kapisi — KAPSAM kolu (her kabul testi kosuluyor mu / gerekceli muaf mi)"),
    (N_DOSYA, "tools/ci-kapsam-test.py", "--kendini-test",
     "CI kapsam kapisi OZ-NOBETCILERI (bulgu1 + muaf sayaci + adim nobetcileri)"),
    # 🔴 31 TEM — ADIM TURU KORLUGU OLCUMU (madde 26/29 turu). deploy.yml'de 82 icra
    # adiminin 6'si HICBIR capaya eslesmiyordu: Bolum D yalnizca KESFEDILMIS kabul
    # testlerini (`tools/*-test.py` · `*-kapisi.py` ...) kosan adimlari gorur, bu ucu
    # KABUL TESTI DEGIL ama yayinin belkemigi. Olculdu (mutasyon): ucunu de fail-open
    # yapan/ silen mutantlarda DORT denetci de rc=0 veriyordu.
    (E_DOSYA, "tools/build.py", None,
     "SITE URETICISI — urun sayfalari + sitemap/robots + merchant feed. Adim duserse "
     "ya da fail-open olursa `_site` ESKI/BOS icerikle yayinlanir: tum urun sayfalari "
     "404, sitemap bayat. Hicbir KABUL TESTI kosmadigi icin Bolum D bu adimi GORMEZ."),
    (E_DOSYA, "tools/d1-sync.py", "--kendini-test",
     "D1 YAZMA GERI-OKUMA nobeti (write-verify + icerik ekseni). Adim fail-open olursa "
     "senkron sessizce bozulur: site urunu gosterir, Ege D1'den GOREMEZ (sessiz satis "
     "kaybi, [[ege-d1-bagimliligi]]). d1-sync.py kesif predikatina girmez -> Bolum D kor."),
    # 🔴 1 AGU — KOL GRANULU (olculen delik, [[nobetci-cagri-satiri-nobetsiz]]).
    # durum-test.py'nin IKI kolu var ve IKISI DE ayni job'da (`serit-b`) kosuyor:
    # bayraksiz kol "bugunku pano ciktisi temiz mi" der, `--ic-nobetci` kolu 6c
    # SIZINTI MUAFIYETININ kendi capasidir (mutasyon bataryasi). OLCULDU: `--ic-nobetci`
    # ADIMININ TAMAMI (name+run) silindiginde ci-kapsam-test.py · kapi-envanteri.py ·
    # is-akisi-kapisi.py UCU DE rc=0 veriyordu. Sebep: tek beyan mekanizmasi (SERIT_B)
    # ARAC YOLU granulunde anahtarlanir -- `("deploy.yml","serit-b","tools/durum-test.py")`
    # -- ve ayni job'daki BAYRAKSIZ cagri o anahtari doyurur; kol dusunce kimse gormez.
    # Bolum E ise KOL granulundedir (kapi + zorunlu bayrak). Bu yuzden iki kol da
    # AYRI AYRI beyan edilir: bir kolun adimi silinirse KIRMIZI yanan iddia odur.
    (N_DOSYA, "tools/durum-test.py", None,
     "DURUM PANOSU kabul testi — BAYRAKSIZ (gercek olcum) kolu. 6a/6b/6c sizinti "
     "kapilari burada GERCEK pano ciktisi uzerinde kosar; depo PUBLIC oldugu icin "
     "bu kol dusmesi sir/kimlik ekseninin CI'da hic olculmemesi demektir."),
    (N_DOSYA, "tools/durum-test.py", "--ic-nobetci",
     "6c 'uzun-anahtar' MUAFIYETININ oz-nobetcisi (S1-S4 sartlarinin her biri icin "
     "1:1 fikstur + mutant, ters-yon yan etki iddiasi, `/` kisa yolu esdegerlik "
     "olcumu). Bu kol dusmesi muafiyetin SESSIZCE genisletilebilmesi demektir: "
     "muafiyeti `return True`e cevirmek ya da S2 tavanini silmek 6c'yi sonsuza dek "
     "yesil birakirdi (olculdu 1 Agu — tavan silinince bu kol 7/12 KIRMIZI yaniyor)."),
    # 🔴 7 AGU — SERIT AYRIMININ ACTIGI KOL DELIGI ([[kapi-yan-etkisi-gizli-onkosul]]).
    # konfigur-bundle-kapisi.py'nin IKI kolu var ve serit ayriminda AYRI DOSYALARA
    # dagildi: BAYRAKSIZ (gercek artefakt DRIFT olcumu) deploy.yml `serit-a3`'te
    # BLOKLAYICI, `--kendini-test` ise nobet.yml `serit-b`de. OLCULDU (7 Agu): deploy.yml'
    # deki BAYRAKSIZ ADIM butunuyle silindiginde ci-kapsam-test.py rc=0 veriyordu —
    # cunku o kapi DOSYA granulunde bakar ve nobet.yml'deki `--kendini-test` cagrisi
    # dosyayi "kapsanmis" gosteriyordu. SERIT_B tablosundaki
    # ("nobet.yml","serit-b","tools/konfigur-bundle-kapisi.py") beyani zaten "artefakt
    # DRIFT olcumu serit A'da bloklayici" DIYORDU ama bu iddiayi kimse OLCMUYORDU.
    # NEDEN BLOKLAYICI: shop/src/konfigurlar.js urunler.json'dan URETILEN artefakttir;
    # kol duserse artefakt bayat kalir ve konfigurlu urun YANLIS/eksik fiyatla satilir
    # (sessiz tahsilat hatasi, PARA EKSENI).
    (E_DOSYA, "tools/konfigur-bundle-kapisi.py", None,
     "KONFIGUR BUNDLE DRIFT kapisi — BAYRAKSIZ (gercek artefakt karsilastirmasi) kolu. "
     "Yayin seridinde BLOKLAYICI kosmali; `--kendini-test` kolu nobet.yml'dedir ve "
     "onun varligi bu kolun yerini TUTMAZ (dosya granullu kapsam kapisi bu farki "
     "GORMEZ — olculdu, [[kapi-yan-etkisi-gizli-onkosul]])."),
)

# ---- ZORUNLU YAYIN VARLIKLARI (adim TURU korlugunun ikinci ekseni) ---------
# 🔴 31 TEM, OLCULEN SAG KALAN MUTANT: `cp jenerator/hacim.js ... _site/jenerator/`
# satiri `echo cp ...`'a cevrildiginde ci-kapsam-test.py (kapsam + oz-test) VE
# is-akisi-kapisi.py'nin UCU DE rc=0 verdi. Tek tuketici jenerator/test/kabul.py
# TEST 4'tur; o test OpenSCAD ister ve CI'da MUAFTIR -> iddia CI'da HIC olculmuyordu.
# Sonuc: parametrik urun sayfalari hacim.js'i 404 alir, konfigurator fiyat HESAPLAMAZ
# ve hicbir yerde alarm calmaz. Iddia burada, CI'da kosan bir kapida yasar.
# KAPSAM DAR TUTULUR (dosya bazli POZITIF, [[kapi-kapsam-genisletme-tuzagi]]):
# "her cp korunsun" DEMEZ — yalniz konfiguratorun CALISMASI icin sart olan varlik.
E_ZORUNLU_VARLIKLAR = (
    ("jenerator/hacim.js",
     "parametrik (sari seri) konfiguratorun hacim/fiyat cekirdegi. Yayin klasorune "
     "kopyalanmazsa urun sayfasi onu 404 alir ve fiyat hesaplanmaz."),
)

E_VARLIK_TANI = (
    "ZORUNLU YAYIN VARLIGI NOBETI KIRMIZI: %s dosyasinda `%s` varligini ETKILI bir\n"
    "   komutun ARGUMANI olarak tasiyan hicbir satir YOK.\n"
    "   Etkisiz sayilan haller: satir SILINMIS · YORUMA alinmis · `echo` MENSIYONUNA\n"
    "   cevrilmis · `|| true` / `continue-on-error: true` / `if: false` / `set +e`.\n"
    "   NEDEN BLOKLAYICI: %s\n"
    "   GERI KOY: 'Yayin klasorunu topla' adiminda `cp %s ... _site/jenerator/`.")

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
    """(hatalar, olculen_iddia_sayisi) — tetikleyici + zorunlu kapi adimlari.

    🔴 5 Agu 2026: DOSYA BAZLI. Zorunlu cagrilarin bir kismi nobet.yml'de kosar
    (serit ayrimi). Her giris kendi is akisinda aranir; dosya OKUNAMAZSA fail-closed
    KIRMIZI doner ("nobet dosyasi yok" YESIL degildir — o halde 4 zorunlu adim CI'da
    HIC kosmuyor demektir)."""
    hatalar = []
    iddia = 0
    _metinler = {}

    def dosya(ad):
        """(metin, govde) — okunamayan/ayristirilamayan dosya icin (None, None)."""
        if ad in _metinler:
            return _metinler[ad]
        yol = os.path.join(dizin, ad)
        if not os.path.exists(yol):
            _metinler[ad] = (None, None)
            return _metinler[ad]
        with open(yol, encoding="utf-8") as f:
            m = f.read()
        g, h = ayristir(m)
        _metinler[ad] = (m, None if (h or not isinstance(g, dict)) else g)
        return _metinler[ad]

    e_metin, e_govde = dosya(E_DOSYA)
    if e_metin is None:
        return ["TETIKLEYICI/ZORUNLU ADIM NOBETI: %s bulunamadi (%s) -> ana yayin is "
                "akisi kalkmis, olcum yapilamadi (fail-closed KIRMIZI)"
                % (E_DOSYA, os.path.join(dizin, E_DOSYA))], 0
    if e_govde is None:
        # Bicim hatasi BOLUM A'nin isi; burada IKINCI kez raporlanmaz (0 iddia olculdu).
        return [], 0
    # TETIKLEYICI: zorunlu cagri tasiyan HER is akisi icin ayri ayri. Nobet dosyasi
    # `push` ile tetiklenmezse alarm hic kosmaz -> "kirmizi kendi kanalinda GORUNUR"
    # iddiasi kagit uzerinde kalirdi ([[nobetci-cagri-satiri-nobetsiz]] sinifi).
    for is_akisi in sorted(set([E_DOSYA] + [a for a, _k, _b, _e in E_ZORUNLU_CAGRILAR])):
        _m, g = dosya(is_akisi)
        for ad in E_TETIKLEYICILER:
            iddia += 1
            if g is None:
                hatalar.append("TETIKLEYICI NOBETI OLCULEMEDI (fail-closed KIRMIZI): "
                               "%s okunamadi/ayristirilamadi -> `on.%s` iddiasi "
                               "olculemedi" % (is_akisi, ad))
                continue
            if not tetikleyici_var(g, ad):
                hatalar.append(E_TETIKLEYICI_TANI
                               % (is_akisi, ad, _on_alt_anahtarlari(g)))
    for is_akisi, kapi, bayrak, etiket in E_ZORUNLU_CAGRILAR:
        iddia += 1
        metin, _g = dosya(is_akisi)
        if metin is None:
            hatalar.append("ZORUNLU KAPI ADIMI OLCULEMEDI (fail-closed KIRMIZI): %s "
                           "bulunamadi -> `%s`%s adimi CI'da HIC kosmuyor olabilir"
                           % (is_akisi, kapi,
                              (" %s" % bayrak) if bayrak else " (BAYRAKSIZ)"))
            continue
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
                is_akisi, kapi, (" %s" % bayrak) if bayrak else " (BAYRAKSIZ)",
                etiket, ek))
    # ZORUNLU YAYIN VARLIGI yalniz YAYIN is akisindadir (`_site` toplama adimi).
    for varlik, neden in E_ZORUNLU_VARLIKLAR:
        iddia += 1
        if not etkili_mensiyon(e_metin, varlik):
            hatalar.append(E_VARLIK_TANI % (E_DOSYA, varlik, neden, varlik))
    return hatalar, iddia


# E_ZORUNLU_CAGRILAR'daki "bayrak None" hali: cagri, LISTEDEKI DIGER zorunlu
# bayraklarin HICBIRINI tasimamali (yani ana/bayraksiz kolu kosuyor olmali).
# `--deploy <yol>` gibi girdi seçen bayraklar kolu DEGISTIRMEZ -> gecerli sayilir.
E_KOL_BAYRAKLARI = frozenset(b for _a, _y, b, _e in E_ZORUNLU_CAGRILAR if b)


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

# ---- K-25: MESRU YAZIM KANARYALARI (Bolum B kaba capa mirasi) ---------------
# 🔴 OLCULEN DELIK: Bolum B'nin ADAY capasi `^python3\s+<hedef>` idi. Asagidaki
# yazimlarin HEPSI MESRUDUR ve SUZGEC hukmu onlari DOGRU cozer, ama kaba capa
# eslestirmedigi icin Bolum B "cagri YOK" deyip SAHTE KIRMIZI yakiyordu —
# ve sahte kirmizi bu depoda TUM EKIBIN yayinini durdurur.
# `onizleme-imaj.yml`'de `bash -c` sarmali fiilen kullanilabilir bir bicimdir.
B_MESRU_YAZIMLAR = (
    ("`python3 -u` (tamponsuz cikti)",
     "python3 -u tools/onizleme-kapisi.py duman --url http://127.0.0.1:18080"),
    ("`env VAR=1 python3` on-eki",
     "env PRUVO_ONIZLEME=1 python3 tools/onizleme-kapisi.py duman "
     "--url http://127.0.0.1:18080"),
    ("`bash -c \"...\"` sarmali",
     'bash -c "python3 tools/onizleme-kapisi.py duman --url http://127.0.0.1:18080"'),
    ("`python3 -X utf8` degerli yorumlayici bayragi",
     "python3 -X utf8 tools/onizleme-kapisi.py duman --url http://127.0.0.1:18080"),
    ("betik DOGRUDAN (shebang ile)",
     "tools/onizleme-kapisi.py duman --url http://127.0.0.1:18080"),
    ("`\\` satir devamli coksatir yazim",
     "python3 tools/onizleme-kapisi.py duman \\\n          --url http://127.0.0.1:18080"),
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

# ---- K-26 ekseni: KABUK YAPISI fiksturleri ---------------------------------
#
# Her satir GERCEK `bash -e` ile olculdu (bkz. bolum basligindaki tablo). "oldurur"
# sutunu TAHMIN DEGIL OLCUMDUR; kanarya satirlari (`; true`, `&&`, yonlendirme,
# pipefail) BILEREK burada durur ki ileride "kapsami genislet" diye SAHTE-KIRMIZI
# yuzeyi acilmasin ([[kapi-kapsam-genisletme-tuzagi]]).
#
# (ad, satir, ETKISIZ_olmali_mi, pipefail_acik)
K26_SATIR_FIKSTURLERI = (
    # --- GERCEK OLDURENLER (bash -e ile rc=0 olculdu) ---
    ("`&` arka plana atma", "python3 %s &" % D_HEDEF, True, False),
    ("`| tee` borusu", "python3 %s | tee kayit.log" % D_HEDEF, True, False),
    ("`| cat` borusu", "python3 %s | cat" % D_HEDEF, True, False),
    ("`| head -1` borusu", "python3 %s | head -1" % D_HEDEF, True, False),
    ("`|| echo` maskesi", 'python3 %s || echo "hata"' % D_HEDEF, True, False),
    ("`|| true` maskesi (eski kapali liste)", "python3 %s || true" % D_HEDEF, True, False),
    ("`|| :` maskesi (eski kapali liste)", "python3 %s || :" % D_HEDEF, True, False),
    ("`|| exit 0` maskesi (eski kapali liste)", "python3 %s || exit 0" % D_HEDEF,
     True, False),
    ("`|| /bin/true` maskesi", "python3 %s || /bin/true" % D_HEDEF, True, False),
    ("`&& ... || printf` zinciri", "python3 %s && echo ok || printf x" % D_HEDEF,
     True, False),
    # --- YANLIS-POZITIF KANARYALARI (bash -e ile rc=1 olculdu: BLOKLAR) ---
    ("duz cagri (MESRU)", "python3 %s" % D_HEDEF, False, False),
    ("`; true` (MESRU: errexit ACIK, hata yutulmaz)", "python3 %s ; true" % D_HEDEF,
     False, False),
    ("`; exit 0` (MESRU: errexit ACIK)", "python3 %s ; exit 0" % D_HEDEF, False, False),
    ("`; echo x` (MESRU)", "python3 %s ; echo x" % D_HEDEF, False, False),
    ("`&& echo ok` (MESRU: hata yayilir)", "python3 %s && echo ok" % D_HEDEF,
     False, False),
    ("`2>&1` yonlendirme (MESRU — `&` arka plan DEGIL)",
     "python3 %s 2>&1" % D_HEDEF, False, False),
    ("`> kayit.log` yonlendirme (MESRU)", "python3 %s > kayit.log" % D_HEDEF,
     False, False),
    ("`&> kayit.log` yonlendirme (MESRU)", "python3 %s &> kayit.log" % D_HEDEF,
     False, False),
    ("`|| exit 1` (MESRU: hata yayilir)", "python3 %s || exit 1" % D_HEDEF,
     False, False),
    ("`|| exit $?` (MESRU)", "python3 %s || exit $?" % D_HEDEF, False, False),
    ("`|| { echo a; exit 1; }` grup (MESRU)",
     "python3 %s || { echo a; exit 1; }" % D_HEDEF, False, False),
    ("`|| false` (MESRU: hata yayilir)", "python3 %s || false" % D_HEDEF, False, False),
    ("pipefail ACIK + `| tee` (MESRU)", "python3 %s | tee kayit.log" % D_HEDEF,
     False, True),
    ("boru SON asamasi (MESRU: cikis kodu bu asamanin)",
     "cat girdi.txt | python3 %s" % D_HEDEF, False, False),
    ("`||` TIRNAK ICINDE (MESRU: operator DEGIL)",
     'python3 %s --desen "a || true"' % D_HEDEF, False, False),
    ("`&` TIRNAK ICINDE (MESRU: operator DEGIL)",
     "python3 %s --desen 'x & y'" % D_HEDEF, False, False),
)

# BAGLAM fiksturleri: satir kusursuz gorunur ama KABUK ONU HIC CALISTIRMAZ.
K26_BAGLAM_FIKSTUR = """\
name: "Sentetik K26 baglam fiksturu"
on: workflow_dispatch
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: "Kapi: kisisel veri"
        run: |
          %s
"""

K26_BAGLAM_MUTANTLAR = (
    ("heredoc GOVDESI (veri, ICRA DEGIL)",
     "cat <<'EOF' > kayit.txt\n          python3 %s\n          EOF" % D_HEDEF, True),
    ("tirnaksiz heredoc GOVDESI",
     "cat <<EOF > kayit.txt\n          python3 %s\n          EOF" % D_HEDEF, True),
    ("CAGRILMAYAN fonksiyon govdesi",
     "kapi() {\n            python3 %s\n          }\n          echo tanimlandi" % D_HEDEF,
     True),
    # PIPEFAIL DURUMU `run:` BLOGUNDAN gelir (satir fiksturleri onu ELDEN verir; bu iki
    # satir `_pipefail_etkisi()` GOVDESINI surer — oz-koruma olcumunde KACAN 8).
    ("boru + pipefail KAPALI (varsayilan `bash -e`)",
     "python3 %s | tee kayit.log" % D_HEDEF, True),
    # --- YANLIS-POZITIF KANARYALARI ---
    ("boru + `set -o pipefail` ACIK (MESRU)",
     "set -o pipefail\n          python3 %s | tee kayit.log" % D_HEDEF, False),
    ("boru + `set -eo pipefail` ACIK (MESRU)",
     "set -eo pipefail\n          python3 %s | tee kayit.log" % D_HEDEF, False),
    ("CAGRILAN fonksiyon govdesi (MESRU)",
     "kapi() {\n            python3 %s\n          }\n          kapi" % D_HEDEF, False),
    ("heredoc BITTIKTEN SONRAKI satir (MESRU)",
     "cat <<'EOF' > kayit.txt\n          duz metin\n          EOF\n"
     "          python3 %s" % D_HEDEF, False),
)

# JOB/IS AKISI duzeyi: adim kusursuz ama job ya da is akisi HIC kosmaz.
K26_JOB_FIKSTUR = """\
name: "Sentetik K26 job fiksturu"
on: workflow_dispatch
jobs:
  on-kosul:
    if: false
    runs-on: ubuntu-latest
    steps:
      - run: echo "bu job KOSMAZ"
  kapilar:
    needs: on-kosul
    runs-on: ubuntu-latest
    steps:
      - name: "Kapi: kisisel veri"
        run: python3 %s
""" % D_HEDEF

K26_JOB_TEMIZ = K26_JOB_FIKSTUR.replace("    if: false\n", "")

K26_OLU_AKIS_FIKSTUR = """\
name: "Sentetik K26 olu is akisi"
on:
  workflow_call:
jobs:
  kapilar:
    runs-on: ubuntu-latest
    steps:
      - name: "Kapi: kisisel veri"
        run: python3 %s
""" % D_HEDEF

# ---- K-29 ekseni: ADIM TURU fiksturleri ------------------------------------
# Sentetik iddia GERCEK bir is akisi adina capalanir (b_adim_hatalari dosya adiyla
# arar) ama fikstur METNI sentetiktir -> gercek dosya degistikce bayatlamaz.
K29_IDDIA = BAdimIddiasi("sentetik-adim", "onizleme-imaj.yml",
                         ("zzzaract", "gonder"), "exit 1", "sentetik olcum")
K29_TEMIZ = """\
name: "Sentetik K29 fiksturu"
on: workflow_dispatch
jobs:
  itme:
    runs-on: ubuntu-latest
    steps:
      - name: "Registry'ye it (PLAN KAPISI)"
        if: ${{ inputs.push_et }}
        run: |
          zzzaract gonder imaj:ci 2> hata.log \\
            && { echo itildi; exit 0; } \\
            || true
          if grep -qi "Plan" hata.log; then
            echo "PLAN BEKLIYOR"
            exit 0
          fi
          cat hata.log
          exit 1
"""

# (ad, metin, KIRMIZI_olmali_mi)
K29_MUTANTLAR = (
    ("adima `continue-on-error: true`",
     K29_TEMIZ.replace('      - name: "Registry\'ye it (PLAN KAPISI)"\n',
                       '      - name: "Registry\'ye it (PLAN KAPISI)"\n'
                       "        continue-on-error: true\n"), True),
    ("hata yolu `exit 1` -> `exit 0`",
     K29_TEMIZ.replace("          cat hata.log\n          exit 1\n",
                       "          cat hata.log\n          exit 0\n"), True),
    ("adima `if: false`",
     K29_TEMIZ.replace("        if: ${{ inputs.push_et }}\n", "        if: false\n"),
     True),
    ("blok basina `set +e`",
     K29_TEMIZ.replace("        run: |\n", "        run: |\n          set +e\n"), True),
    ("hata yolu `|| true` ile yutuldu",
     K29_TEMIZ.replace("          cat hata.log\n          exit 1\n",
                       '          cat hata.log\n          echo hata || true\n'), True),
    ("adim BUTUNUYLE silindi",
     K29_TEMIZ.split('      - name: "Registry')[0]
     + "      - run: echo bos\n", True),
    ("cagri `echo` MENSIYONUNA cevrildi",
     K29_TEMIZ.replace("          zzzaract gonder imaj:ci",
                       "          echo zzzaract gonder imaj:ci"), True),
    ("job'a `continue-on-error: true`",
     K29_TEMIZ.replace("    runs-on: ubuntu-latest\n",
                       "    runs-on: ubuntu-latest\n    continue-on-error: true\n"), True),
    # --- YANLIS-POZITIF KANARYALARI: MESRU yazim KIRMIZI YANMAMALI ---
    ("TEMIZ fikstur (MESRU: `&& {...} || true` PLAN KAPISI deseni)", K29_TEMIZ, False),
    ("adim ADI degistirildi (MESRU: capa ICRAYA bagli, ADA degil)",
     K29_TEMIZ.replace('      - name: "Registry\'ye it (PLAN KAPISI)"',
                       "      - name: Imaji yayina gonder"), False),
    ("MESRU `if:` ifadesi",
     K29_TEMIZ.replace("        if: ${{ inputs.push_et }}\n",
                       "        if: ${{ github.ref == 'refs/heads/main' }}\n"), False),
    ("`set +e` SONRA `set -e` (geri acilmis) (MESRU)",
     K29_TEMIZ.replace("        run: |\n",
                       "        run: |\n          set +e\n          echo x\n"
                       "          set -e\n"), False),
    ("hata yolundan ONCE ek satir (MESRU)",
     K29_TEMIZ.replace("          cat hata.log\n          exit 1\n",
                       "          cat hata.log\n          echo 'basarisiz'\n"
                       "          exit 1\n"), False),
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
      - name: "Statik sayfalari uret"
        run: python3 tools/build.py
      - name: "D1 yazma geri-okuma"
        run: python3 tools/d1-sync.py --kendini-test
      - name: "Durum panosu kabul testi"
        run: python3 tools/durum-test.py
      - name: "6c sizinti muafiyeti ic nobetcisi"
        run: python3 tools/durum-test.py --ic-nobetci
      - name: "Konfigur bundle kapisi"
        run: python3 tools/konfigur-bundle-kapisi.py
      - name: "Yayin klasorunu topla"
        run: |
          mkdir -p _site/jenerator
          cp jenerator/hacim.js _site/jenerator/
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
    # --- 31 TEM: ADIM TURU KORLUGU (build.py · d1-sync --kendini-test · hacim.js) ---
    ("SITE URETICISI adimi butunuyle silindi",
     E_FIKSTUR_TEMIZ.replace('      - name: "Statik sayfalari uret"\n'
                             "        run: python3 tools/build.py\n", ""), True),
    ("SITE URETICISI cagrisi `echo` MENSIYONUNA cevrildi",
     E_FIKSTUR_TEMIZ.replace("        run: python3 tools/build.py\n",
                             "        run: echo python3 tools/build.py\n"), True),
    ("SITE URETICISI adimina `continue-on-error: true`",
     E_FIKSTUR_TEMIZ.replace('      - name: "Statik sayfalari uret"\n',
                             '      - name: "Statik sayfalari uret"\n'
                             "        continue-on-error: true\n"), True),
    ("D1 geri-okuma cagrisi `|| true` ile yutuldu",
     E_FIKSTUR_TEMIZ.replace("        run: python3 tools/d1-sync.py --kendini-test\n",
                             "        run: python3 tools/d1-sync.py --kendini-test "
                             "|| true\n"), True),
    ("D1 geri-okuma adimi BAYRAKSIZ kola cevrildi (--durum)",
     E_FIKSTUR_TEMIZ.replace("        run: python3 tools/d1-sync.py --kendini-test\n",
                             "        run: python3 tools/d1-sync.py --durum\n"), True),
    # 🔴 1 AGU — KOL GRANULU MUTANTLARI ([[nobetci-cagri-satiri-nobetsiz]]).
    # OLCULEN DELIK: durum-test.py'nin iki kolu da AYNI job'da kosuyor ve tek beyan
    # mekanizmasi (SERIT_B) ARAC YOLU granulunde anahtarli oldugu icin, bir kolun
    # adimi silindiginde ayni job'daki OTEKI kol anahtari doyuruyor ve UC denetci de
    # rc=0 veriyordu. Asagidaki iki mutant tam bu hali capalar: bir kol dusunce
    # Bolum E KIRMIZI yanmali. UCUNCUSU (kanarya) ters yonu tutar: kollarin AYRI
    # ADIMLARDA olmasi MESRUDUR ve tek basina kirmizi yakmamalidir.
    ("6c IC NOBETCI kolu (`--ic-nobetci`) adimi SILINDI — bayraksiz kol duruyor",
     E_FIKSTUR_TEMIZ.replace('      - name: "6c sizinti muafiyeti ic nobetcisi"\n'
                             "        run: python3 tools/durum-test.py --ic-nobetci\n",
                             ""), True),
    ("durum-test BAYRAKSIZ kol adimi SILINDI — `--ic-nobetci` kolu duruyor",
     E_FIKSTUR_TEMIZ.replace('      - name: "Durum panosu kabul testi"\n'
                             "        run: python3 tools/durum-test.py\n",
                             ""), True),
    ("6c ic nobetci kolu `|| true` ile yutuldu",
     E_FIKSTUR_TEMIZ.replace("        run: python3 tools/durum-test.py --ic-nobetci\n",
                             "        run: python3 tools/durum-test.py --ic-nobetci "
                             "|| true\n"), True),
    # 🔴 7 AGU — KONFIGUR BUNDLE BAYRAKSIZ KOLU (serit ayriminin actigi delik).
    # Olculdu: bu adim GERCEK deploy.yml'den silindiginde ci-kapsam-test.py rc=0
    # veriyordu (nobet.yml'deki `--kendini-test` cagrisi dosyayi kapsanmis gosterir).
    # Iki oldurucu + bir kanarya: kolun AYRI ADIMDA/JOB'DA olmasi MESRUDUR.
    ("KONFIGUR BUNDLE bayraksiz kol adimi SILINDI (`--kendini-test` baska dosyada)",
     E_FIKSTUR_TEMIZ.replace('      - name: "Konfigur bundle kapisi"\n'
                             "        run: python3 tools/konfigur-bundle-kapisi.py\n",
                             ""), True),
    ("KONFIGUR BUNDLE bayraksiz kolu `--kendini-test`e cevrildi (drift olcumu duser)",
     E_FIKSTUR_TEMIZ.replace("        run: python3 tools/konfigur-bundle-kapisi.py\n",
                             "        run: python3 tools/konfigur-bundle-kapisi.py "
                             "--kendini-test\n"), True),
    ("KONFIGUR BUNDLE adimi AYRI bir job'a tasindi (MESRU)",
     E_FIKSTUR_TEMIZ.replace('      - name: "Konfigur bundle kapisi"\n'
                             "        run: python3 tools/konfigur-bundle-kapisi.py\n",
                             "  dorduncu:\n    runs-on: ubuntu-latest\n    steps:\n"
                             '      - name: "Konfigur bundle kapisi"\n'
                             "        run: python3 tools/konfigur-bundle-kapisi.py\n"),
     False),
    ("YAYIN VARLIGI `cp jenerator/hacim.js` -> `echo cp ...` (OLCULEN SAG KALAN MUTANT)",
     E_FIKSTUR_TEMIZ.replace("          cp jenerator/hacim.js _site/jenerator/\n",
                             "          echo cp jenerator/hacim.js _site/jenerator/\n"),
     True),
    ("YAYIN VARLIGI satiri YORUMA alindi",
     E_FIKSTUR_TEMIZ.replace("          cp jenerator/hacim.js _site/jenerator/\n",
                             "          # cp jenerator/hacim.js _site/jenerator/\n"),
     True),
    # --- YANLIS-POZITIF KANARYALARI (MESRU yazim KIRMIZI YANMAMALI) ---
    ("build.py'ye MESRU ek arguman (`--sadece-ozet` DEGIL, girdi secen bayrak)",
     E_FIKSTUR_TEMIZ.replace("        run: python3 tools/build.py\n",
                             "        run: python3 tools/build.py --hizli\n"), False),
    ("yayin varligi `cp -a` ve TAM yol ile kopyalandi (MESRU)",
     E_FIKSTUR_TEMIZ.replace("          cp jenerator/hacim.js _site/jenerator/\n",
                             "          cp -a jenerator/hacim.js "
                             "_site/jenerator/hacim.js\n"), False),
    ("D1 adimi AYRI bir job'a tasindi (MESRU)",
     E_FIKSTUR_TEMIZ.replace('      - name: "D1 yazma geri-okuma"\n'
                             "        run: python3 tools/d1-sync.py --kendini-test\n",
                             "  ucuncu:\n    runs-on: ubuntu-latest\n    steps:\n"
                             '      - name: "D1 yazma geri-okuma"\n'
                             "        run: python3 tools/d1-sync.py --kendini-test\n"),
     False),
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


# BOLUM C ariza-enjeksiyon iddiasi TABANI. Bu turda OLCULDU; Bolum C buyuyebilir ama
# TABANIN ALTINA DUSEMEZ (dususe kapi KIRMIZI yanar). Bilerek azaltiliyorsa NEDENIYLE
# birlikte guncelle.
# 31 Tem: 143 -> 162. Fark = SERIT AYRIMI ekseninin 9 iddiasi (bkz.
# _serit_b_mekanizma_kontrol). Taban yukseltilmezse o dokuz iddia SESSIZCE silinebilirdi.
# 8 Agu: 162 -> 204 (OLCULEN pay 42 idi = olu koruma; 42 iddia tek commit'te silinse bile
# bu kol YESIL kalirdi). Yeni deger, A/B onarimlarindan SONRA olculdu.
#
# 🔴 OPERATOR BILEREK `<` KALIYOR (tam esitlige CEVRILMEZ — mimar karari, 8 Agu):
#   (a) Bu sayi TEK bir envanterin uzunlugu DEGIL, dosya boyunca ~200 iddianin
#       TOPLAMIDIR ve CALKANTISI YUKSEK: her kapi degisikligi iddia ekler. Tam esitlik
#       her mesru eklemede yayini durduran sahte-kirmizi uretirdi (bedeli olculdu:
#       [[kapi-birikimi-yayin-gecikmesi]]).
#   (b) Envanter ekseninde tam esitlik garantisini TABLO_TABANLARI ZATEN tablo-tablo
#       veriyor; bu toplam ikinci bir tavan koymaz, DUSUS nobetidir.
#   (c) Bu kolun IKINCI bir gorevi var: KESIF OLUMUNDE fail-closed KIRMIZI yakmak.
#       Olculdu (8 Agu, bagimsiz curutucu): git'siz bir agacta `git ls-files` bos doner,
#       D ekseni ~45 iddia atlar ve sayi 204 -> 148 duser; bu kol o hali KIRMIZI yakar.
#       Tam esitlik bu gorevi de yapardi ama (a) yuzunden bedeli agir.
KENDINI_TEST_TABAN = 204

KENDINI_TEST_TABAN_TANI = (
    "BOLUM C IDDIA SAYACI KIRMIZI: ariza-enjeksiyon %d iddia kosturdu, TABAN %d.\n"
    "   🔴 'hata YOK' ile 'OLCUM YOK' AYNI SEY DEGILDIR. Olculdu (30 Tem): "
    "`kendini_test()`\n"
    "   govdesi `return [], 0` yapilinca TUM ariza-enjeksiyon iddialari sessizce dustu "
    "ve\n   kapi YESIL yandi — kapinin olcum govdeleri no-op yapilabilir hale gelmisti.\n"
    "   GERI KOY: kendini_test() govdesini (ya da tabani bilincli olarak guncelle).")


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

    # B-MESRU-YAZIM (K-25): kaba capa mirasi. Bu yazimlarin HEPSI ETKILI SAYILMALI;
    # biri bile dususe Bolum B o bicimde SAHTE KIRMIZI yakar ve yayini durdurur.
    for ad, satir in B_MESRU_YAZIMLAR:
        iddia += 1
        n = len(etkili_cagrilar(B_JETON_FIKSTUR % satir, B_JETON_IDDIA))
        if n != 1:
            hatalar.append("B-MESRU-YAZIM SAHTE-KIRMIZI: %r yaziminda ETKILI cagri "
                           "sayisi %d (1 bekleniyordu) -> Bolum B'nin ADAY capasi bu "
                           "MESRU bicimi gormuyor; gercek is akisinda boyle yazilirsa "
                           "kapi sahte KIRMIZI yakar ve TUM EKIBIN yayini durur "
                           "([[kapi-kapsam-eksen-secimi]])" % (ad, n))

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
            iddia += 8
            hatalar.extend(_d_izin_mekanizma_kontrol())
            # SERIT AYRIMI MEKANIZMASI (31 Tem): "yayini bloklamayan job" ekseni
            # GERCEKTEN olcuyor mu + BLANKET beyan gercekten reddediliyor mu.
            iddia += 9
            hatalar.extend(_serit_b_mekanizma_kontrol())
            # BOLUM F MEKANIZMASI (4 Agu): BLOKLAYICI/BLOKLAMAZ beyani GERCEGE karsi
            # olculuyor mu. (ii) tam da uc curutmeyi geciren vakadir: adim
            # bloklamayan job'da + beyan 'bloklayici' -> KIRMIZI.
            iddia += 8
            hatalar.extend(_bolum_f_mekanizma_kontrol())

    # ---- NOBETCININ NOBETCISI: tablo + kablo kontrolleri GERCEKTEN olcuyor mu -
    # Govde ADLI bir fonksiyondadir (_tablo_mekanizma_kontrol) ve iddia sayisi ORADAN
    # TURETILIR — `iddia += N` ikizi BILEREK kaldirildi, gerekcesi o fonksiyonda.
    t_hatalar, t_iddia = _tablo_mekanizma_kontrol()
    iddia += t_iddia
    hatalar.extend(t_hatalar)

    # ---- K-26 EKSENI: KABUK YAPISI (cikis kodunu KIM belirliyor) --------------
    # Govde `satir_sebepleri()` no-op yapilirsa (or. `return []`) 10 NEGATIF iddia
    # birden duser; asiri agresif yapilirsa 16 YANLIS-POZITIF kanaryasi duser.
    for ad, satir, etkisiz_olmali, pf in K26_SATIR_FIKSTURLERI:
        iddia += 1
        sebepler = satir_sebepleri(satir, D_HEDEF, pf)
        if etkisiz_olmali and not sebepler:
            hatalar.append("K26-NEGATIF SESSIZ: %r bicimi ETKILI sayildi -> kapi adimi "
                           "bu yazimla BEYANSIZ oldurulebilir (gercek `bash -e` "
                           "olcumunde rc=0 veriyor)" % ad)
        if not etkisiz_olmali and sebepler:
            hatalar.append("K26-YANLIS-POZITIF: %r MESRU yazimi etkisizlestirilmis "
                           "sayildi -> %s  (gercek `bash -e` olcumunde rc=1, yani "
                           "BLOKLUYOR; bu sahte-kirmizi TUM EKIBIN yayinini durdurur)"
                           % (ad, "; ".join(sebepler)))

    capalar_k26, _kh = kapi_capalari()
    d_capalar_k26 = [(y, o) for y, o in (capalar_k26 or []) if y == D_HEDEF]
    if not d_capalar_k26:
        iddia += 1
        hatalar.append("K26-CAPA BAYAT: %s artik kesfedilmiyor -> baglam iddialari "
                       "olculemedi" % D_HEDEF)
    else:
        for ad, govde, etkisiz_olmali in K26_BAGLAM_MUTANTLAR:
            iddia += 1
            bulgu = kapi_cagrilari(K26_BAGLAM_FIKSTUR % govde, d_capalar_k26)
            sebepli = [b for b in bulgu if b[5]]
            if etkisiz_olmali and not sebepli:
                hatalar.append("K26-BAGLAM SESSIZ: %r -> satir ICRA EDILMEDIGI HALDE "
                               "etkili sayildi (bulgu=%r)" % (ad, bulgu))
            if not etkisiz_olmali:
                if sebepli:
                    hatalar.append("K26-BAGLAM YANLIS-POZITIF: %r MESRU yazimi "
                                   "etkisizlestirilmis sayildi -> %s"
                                   % (ad, sebepli[0][5]))
                if not bulgu:
                    hatalar.append("K26-BAGLAM CAPA BOZUK: %r yaziminda kapi cagrisi "
                                   "hic bulunamadi" % ad)
        # JOB duzeyi: `if: false` + `needs:` yayilimi
        iddia += 2
        job_bulgu = kapi_cagrilari(K26_JOB_FIKSTUR, d_capalar_k26)
        if not [b for b in job_bulgu if b[5]]:
            hatalar.append("K26-JOB SESSIZ: KOSMAYAN bir job'a (`if: false` olan job'a "
                           "`needs:` ile bagli) tasinan kapi cagrisi HALA etkili "
                           "sayildi -> kapi iki satirla sessizce oldurulebilir "
                           "(bulgu=%r)" % (job_bulgu,))
        temiz_job = kapi_cagrilari(K26_JOB_TEMIZ, d_capalar_k26)
        if not temiz_job or [b for b in temiz_job if b[5]]:
            hatalar.append("K26-JOB YANLIS-POZITIF: `if: false` KALDIRILMIS MESRU "
                           "`needs:` zincirinde cagri etkisiz sayildi (bulgu=%r)"
                           % (temiz_job,))
        # IS AKISI duzeyi: yalniz `workflow_call` -> OLU
        iddia += 2
        olu_bulgu = kapi_cagrilari(K26_OLU_AKIS_FIKSTUR, d_capalar_k26)
        if not [b for b in olu_bulgu if b[5]]:
            hatalar.append("K26-OLU-AKIS SESSIZ: yalnizca `workflow_call` ile tetiklenen "
                           "(yani onu cagiran olmadan HIC kosmayan) bir is akisina "
                           "tasinan kapi cagrisi HALA etkili sayildi (bulgu=%r)"
                           % (olu_bulgu,))
        for ad, metin in (("workflow_dispatch", B_FIKSTUR), ("push", E_FIKSTUR_TEMIZ)):
            if [b for b in kapi_cagrilari(metin, d_capalar_k26) if K26_OLU_AKIS in b[5]]:
                hatalar.append("K26-OLU-AKIS YANLIS-POZITIF: `%s` ile tetiklenen MESRU "
                               "is akisi OLU sayildi -> deploy.yml/onizleme-imaj.yml "
                               "KIRMIZI yanardi" % ad)

    # ---- K-29 EKSENI: ADIM TURU (kabul testi KOSMAYAN adim) -------------------
    # `b_adim_hatalari()` TA KENDISI sentetik bir tabloyla + gecici dizinle kosulur
    # (kopya mantik yazilmaz): govdesi no-op yapilirsa (or. `return [], 0`) 8 KIRMIZI
    # iddiasi duser, asiri agresif yapilirsa 5 YANLIS-POZITIF kanaryasi duser.
    gecici4 = tempfile.mkdtemp(prefix="pruvo-isakisi-k29-")
    try:
        k29_yol = os.path.join(gecici4, K29_IDDIA.is_akisi)
        for ad, metin, kirmizi_olmali in K29_MUTANTLAR:
            iddia += 1
            with open(k29_yol, "w", encoding="utf-8") as f:
                f.write(metin)
            k_bulgu, k_iddia = b_adim_hatalari(gecici4, (K29_IDDIA,))
            if k_iddia != 1:
                hatalar.append("K29-IDDIA SAYACI BOZUK: 1 bekleniyordu, %d" % k_iddia)
            if kirmizi_olmali and not k_bulgu:
                hatalar.append("K29-NEGATIF SESSIZ: %r mutasyonundan sonra ADIM TURU "
                               "nobetcisi HICBIR hata uretmedi -> kabul testi KOSMAYAN "
                               "adim yine beyansiz fail-open yapilabilir" % ad)
            if not kirmizi_olmali and k_bulgu:
                hatalar.append("K29-YANLIS-POZITIF: %r MESRU yazimi KIRMIZI yandi -> %s"
                               % (ad, k_bulgu[0].splitlines()[0]))
        # Dosya YOKSA fail-closed KIRMIZI (nobetci sessizce dusemez).
        iddia += 1
        os.remove(k29_yol)
        yok_bulgu, _ = b_adim_hatalari(gecici4, (K29_IDDIA,))
        if not any("bulunamadi" in h for h in yok_bulgu):
            hatalar.append("K29-FAIL-CLOSED OLU: iddianin is akisi dosyasi YOKKEN "
                           "nobetci KIRMIZI yakmadi (%r)" % (yok_bulgu,))
    finally:
        shutil.rmtree(gecici4, ignore_errors=True)

    # ---- E EKSENI: tetikleyici + zorunlu kapi adimi olcumu --------------------
    # bolum_e() TA KENDISI gecici bir dizinde kosulur (kopya mantik yazilmaz):
    # govdesi no-op yapilirsa (or. `return [], 0`) asagidaki 6 KIRMIZI iddiasi birden
    # duser; asiri agresif yapilirsa 6 YANLIS-POZITIF kanaryasi duser -> iki yonlu.
    gecici3 = tempfile.mkdtemp(prefix="pruvo-isakisi-e-")
    try:
        iddia += 1
        # 🔴 FIKSTUR HER ZORUNLU IS AKISINA yazilir (5 Agu serit ayrimi): tablo artik
        # dosya alani tasir ve zorunlu cagrilarin bir kismi nobet.yml'dedir. Tek dosya
        # yazilsaydi "temiz fikstur" KIRMIZI yanardi ve mutant sinyali GURULTUYE
        # gomulurdu. Mutasyon da AYNI SEKILDE her dosyaya uygulanir -> oldurucu mutant
        # her iki kanalda da olur, kontrol mutanti ikisinde de mesru kalir.
        e_dosyalari = sorted(set([E_DOSYA] + [a for a, _k, _b, _e in E_ZORUNLU_CAGRILAR]))

        def _e_yaz(metin):
            for _ad in e_dosyalari:
                with open(os.path.join(gecici3, _ad), "w", encoding="utf-8") as f:
                    f.write(metin)

        _e_yaz(E_FIKSTUR_TEMIZ)
        temiz_e, temiz_iddia = bolum_e(gecici3)
        if temiz_e:
            hatalar.append("E-POZITIF BOZUK: temiz sentetik fikstur icin bolum_e() %d "
                           "hata uretti -> %s" % (len(temiz_e), " ; ".join(temiz_e)))
        beklenen_iddia = (len(E_TETIKLEYICILER) * len(e_dosyalari)
                          + len(E_ZORUNLU_CAGRILAR) + len(E_ZORUNLU_VARLIKLAR))
        if temiz_iddia != beklenen_iddia:
            hatalar.append("E-IDDIA SAYACI BOZUK: %d bekleniyordu, %d olculdu -> govde "
                           "iddia atlamis olabilir" % (beklenen_iddia, temiz_iddia))
        # DOSYA ALANI CANLI MI: nobet dosyasi YOKKEN kapi fail-closed KIRMIZI yakmali
        # (aksi halde "tasindi" diye silinen bir is akisi iddialari SESSIZCE dusururdu).
        iddia += 1
        if len(e_dosyalari) > 1:
            _eksik = [a for a in e_dosyalari if a != E_DOSYA][0]
            os.remove(os.path.join(gecici3, _eksik))
            eksik_bulgu, _ = bolum_e(gecici3)
            if not any("OLCULEMEDI" in h for h in eksik_bulgu):
                hatalar.append("E-DOSYA ALANI OLU: `%s` is akisi SILINDIGINDE bolum_e() "
                               "fail-closed KIRMIZI yakmadi -> zorunlu adimlar bir "
                               "dosyayla birlikte sessizce dusurulebilirdi (%r)"
                               % (_eksik, eksik_bulgu))
        for ad, metin, kirmizi_olmali in E_MUTANTLAR:
            iddia += 1
            _e_yaz(metin)
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

    # ---- G EKSENI: YAYIN SINYALI SAFLIGI + KOSUM SONUCU SIMULATORU -----------
    g_hatalar, g_iddia = _g_kendini_test()
    hatalar.extend(g_hatalar)
    iddia += g_iddia
    return hatalar, iddia


# ---------------------------------------------------------------------------
# BOLUM G — KENDINI TEST (sentetik fikstur; GERCEK dosyalar degisince bayatlamaz)
# ---------------------------------------------------------------------------
# 🔴 IKI YONLU OLMAK ZORUNDA (mimar olcutu): tek yonlu kurulan bir ayrim sinyali
# TOPYEKUN oldurur. "Bloklamayan kirmizi kosumu boyamasin" (YON A) tek basina
# saglanabilir — hepsini susturarak. Bu yuzden YON B ("yayini durduran bir job
# kirmizi olunca kosum KIRMIZI olmali VE deploy KOSMAMALI") ayni bataryada olculur.
G_YAYIN_FIKSTUR = """\
name: "Sentetik G — yayin is akisi"
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
  serit-a2:
    runs-on: ubuntu-latest
    steps:
      - run: echo a2
  serit-a3:
    runs-on: ubuntu-latest
    steps:
      - run: echo a3
  serit-a4:
    runs-on: ubuntu-latest
    steps:
      - run: echo a4
  deploy:
    needs: [build, serit-a2, serit-a3, serit-a4]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/deploy-pages@v4
  yayin:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - run: echo yayin
"""

G_NOBET_FIKSTUR = """\
name: "Sentetik G — nobet seridi"
on:
  push:
    branches: [main]
concurrency:
  group: sentetik-nobet
  cancel-in-progress: false
jobs:
  alarm:
    runs-on: ubuntu-latest
    steps:
      - run: echo alarm
  ikinci-alarm:
    runs-on: ubuntu-latest
    steps:
      - run: echo ikinci
"""

# (ad, yayin_metni_donusturucu, nobet_metni_donusturucu, KIRMIZI_olmali_mi)
G_MUTANTLAR = (
    # --- OLDURUCULER ---
    ("bloklamayan alarm job'u YAYIN is akisina geri kondu (G1)",
     lambda y: y + "  alarm:\n    runs-on: ubuntu-latest\n    steps:\n"
                   "      - run: echo alarm\n", None, True),
    ("`deploy: needs` listesinden bir serit DUSURULDU (G8 — sessiz fail-open)",
     lambda y: y.replace("    needs: [build, serit-a2, serit-a3, serit-a4]\n",
                         "    needs: [build, serit-a2, serit-a3]\n"), None, True),
    ("`deploy: needs` BUTUNUYLE silindi (G8)",
     lambda y: y.replace("    needs: [build, serit-a2, serit-a3, serit-a4]\n", ""),
     None, True),
    ("nobet is akisinin `on.push` tetigi kaldirildi (G2 — alarm HIC kosmaz)",
     None, lambda n: n.replace("on:\n  push:\n    branches: [main]\n",
                               "on:\n  workflow_dispatch:\n"), True),
    ("nobet job'u `continue-on-error: true` ile SUSTURULDU (G4)",
     None, lambda n: n.replace("  alarm:\n    runs-on: ubuntu-latest\n",
                               "  alarm:\n    runs-on: ubuntu-latest\n"
                               "    continue-on-error: true\n"), True),
    ("nobet job'u DAIMA-YANLIS `if:` ile olduruldu (G4)",
     None, lambda n: n.replace("  alarm:\n    runs-on: ubuntu-latest\n",
                               "  alarm:\n    runs-on: ubuntu-latest\n"
                               "    if: false\n"), True),
    ("Pages yayini NOBET seridine kaydirildi (G3)",
     None, lambda n: n.replace("      - run: echo alarm\n",
                               "      - uses: actions/deploy-pages@v4\n"), True),
    # 🔴 G5 AYIRT EDICI OLMAK ZORUNDA ([[beyan-edilmis-survivor]]): cagiran job
    # `deploy: needs`'e de EKLENIR, boylece G1 (bagsiz job) ve G8 (liste kuculdu)
    # SUSAR ve KIRMIZI'yi TEK BASINA G5 yakar. Aksi halde "zincirden gecti" derken
    # aslinda G1'i olcmus olurduk.
    ("nobet seridi `uses:` ile yayin grafigine GERI baglandi (G5, TEK BASINA)",
     lambda y: (y + "  nobet-cagrisi:\n    uses: ./.github/workflows/%s\n" % N_DOSYA)
     .replace("    needs: [build, serit-a2, serit-a3, serit-a4]\n",
              "    needs: [build, serit-a2, serit-a3, serit-a4, nobet-cagrisi]\n"),
     None, True),
    ("nobet kosumu `cancel-in-progress: true` ile IPTAL EDILEBILIR yapildi (G6)",
     None, lambda n: n.replace("  cancel-in-progress: false\n",
                               "  cancel-in-progress: true\n"), True),
    ("nobet is akisi SILINDI (G2/G3/G4/G6 fail-closed)",
     None, "SIL", True),
    # --- KONTROLLER (mimarin istedigi uc eksen) ---
    ("KONTROL: job SIRASI degistirildi (davranis AYNI)",
     lambda y: y.replace(
         "  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo build\n"
         "  serit-a2:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo a2\n",
         "  serit-a2:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo a2\n"
         "  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo build\n"),
     None, False),
    ("KONTROL: davranis degistirmeyen YENIDEN ADLANDIRMA (adim adi + is akisi adi)",
     lambda y: y.replace('name: "Sentetik G — yayin is akisi"',
                         'name: "Sentetik G — YAYIN HATTI"')
                .replace("      - run: echo build\n",
                         '      - name: "Site uret"\n        run: echo build\n'),
     None, False),
    ("KONTROL: `needs` listesine DOKUNMAYAN bicimsel degisiklik (akis -> blok yazimi)",
     lambda y: y.replace("    needs: [build, serit-a2, serit-a3, serit-a4]\n",
                         "    needs:\n      - build\n      - serit-a2\n"
                         "      - serit-a3\n      - serit-a4\n"), None, False),
    ("KONTROL: nobet seridine YENI bir alarm job'u eklendi",
     None, lambda n: n + "  ucuncu-alarm:\n    runs-on: ubuntu-latest\n    steps:\n"
                         "      - run: echo ucuncu\n", False),
    ("KONTROL: yayin ARDILI (`yayin`) duruyor — ardil bagsiz DEGILDIR",
     lambda y: y, None, False),
)

# (ad, kirmizi_job, beklenen_conclusion, deploy_kosmali_mi) — KOSUM SONUCU SIMULATORU
G_SIMULASYON = (
    ("YON A: bloklamayan alarm (nobet is akisinda) kirmizi -> YAYIN kosumu ETKILENMEZ",
     "nobet:alarm", "success", True),
    ("YON B: `build` kirmizi -> yayin kosumu KIRMIZI + deploy KOSMAZ",
     "build", "failure", False),
    ("YON B: `serit-a2` kirmizi -> yayin kosumu KIRMIZI + deploy KOSMAZ",
     "serit-a2", "failure", False),
    ("YON B: `deploy` kirmizi -> yayin kosumu KIRMIZI (yayin adiminin kendisi)",
     "deploy", "failure", True),
    ("SINIR: `yayin` (yayin ARDILI) kirmizi -> kosum KIRMIZI ve bu DOGRUDUR "
     "(urunler canliya alinamadi = yayin zincirinin KENDI kusuru)",
     "yayin", "failure", True),
    ("TABAN: hicbir job kirmizi degil -> kosum YESIL, deploy KOSAR",
     None, "success", True),
)


# BOLUM G IDDIA SAYACI TABANI — `yayin_sinyali_kontrol()` kac EKSEN kosturuyor.
# 🔴 8 Agu 2026: `< 7` YERINE TAM ESITLIK (`!= 8`). Olculdu: gercek deger 8, taban 7 ->
# pay 1, yani bir eksenin sayaci sessizce dusebilirdi (tam da bu kolun engelledigi kacis).
# Kural gerekcesi TABLO_TABANLARI'nin ustundeki blokta; KOSUL burada da tutuyor:
# yayin_sinyali_kontrol() BU dosyada, muhendislik duzenlemesiyle buyur.
# YANLIS-POZITIF RISKI OLCULDU: sayac FIKSTUR-BAGIMSIZ — 15 G mutantinin 15'i de, ayrica
# GERCEK .github/workflows kosumu da 8 verdi. Yani tam esitlik fikstur degisiminden
# sahte-kirmizi yakmaz; yalniz EKSEN sayisi degisince konusur (ve o zaman konusmalidir).
G_IDDIA_TABANI = 8


def _g_kendini_test():
    """(hatalar, iddia) — Bolum G ariza enjeksiyonu + kosum sonucu simulatoru."""
    hatalar = []
    iddia = 0
    gecici = tempfile.mkdtemp(prefix="pruvo-isakisi-g-")
    try:
        def yaz(y_metin, n_metin):
            with open(os.path.join(gecici, E_DOSYA), "w", encoding="utf-8") as f:
                f.write(y_metin)
            n_yol = os.path.join(gecici, N_DOSYA)
            if n_metin is None:
                if os.path.exists(n_yol):
                    os.remove(n_yol)
                return
            with open(n_yol, "w", encoding="utf-8") as f:
                f.write(n_metin)

        # TABAN: temiz fikstur YESIL olmali (yanlis-pozitif nobeti).
        iddia += 1
        yaz(G_YAYIN_FIKSTUR, G_NOBET_FIKSTUR)
        temiz, temiz_iddia = yayin_sinyali_kontrol(gecici)
        if temiz:
            hatalar.append("G-POZITIF BOZUK: temiz sentetik fikstur %d hata uretti -> %s"
                           % (len(temiz), " ; ".join(h.splitlines()[0] for h in temiz)))
        if temiz_iddia != G_IDDIA_TABANI:
            hatalar.append(
                "G-IDDIA SAYACI BOZUK: %d iddia olculdu, TABAN %d (fark %+d).\n"
                "   🔴 IKI YON DE KIRMIZIDIR (8 Agu, tam esitlik):\n"
                "   (a) DUSUS — yayin_sinyali_kontrol() bir ekseni atlamis: o eksenin\n"
                "       hatalari artik HIC uretilmiyor ama kapi YESIL yanabilir.\n"
                "   (b) TABAN GUNCELLENMEDEN ARTIS — taban kozmetiklesir ve pay birikir;\n"
                "       pay kadar eksen sonradan sessizce silinebilir hale gelir\n"
                "       (olculdu 8 Agu: gercek 8 · taban 7 -> pay 1).\n"
                "   YAPILACAK: eksen sayisi BILEREK degistiyse G_IDDIA_TABANI'ni AYNI\n"
                "   commit'te %d -> %d yap ve NEDENINI yaz."
                % (temiz_iddia, G_IDDIA_TABANI, temiz_iddia - G_IDDIA_TABANI,
                   G_IDDIA_TABANI, temiz_iddia))
        # ARIZA ENJEKSIYONU
        for ad, y_don, n_don, kirmizi_olmali in G_MUTANTLAR:
            iddia += 1
            y = y_don(G_YAYIN_FIKSTUR) if callable(y_don) else G_YAYIN_FIKSTUR
            if n_don == "SIL":
                n = None
            elif callable(n_don):
                n = n_don(G_NOBET_FIKSTUR)
            else:
                n = G_NOBET_FIKSTUR
            yaz(y, n)
            bulgu, _ = yayin_sinyali_kontrol(gecici)
            if kirmizi_olmali and not bulgu:
                hatalar.append("G-NEGATIF SESSIZ: %r mutasyonundan sonra "
                               "yayin_sinyali_kontrol() HICBIR hata uretmedi -> o eksen "
                               "OLU" % ad)
            if not kirmizi_olmali and bulgu:
                hatalar.append("G-YANLIS-POZITIF: %r MESRU degisiklik KIRMIZI yandi -> %s"
                               % (ad, bulgu[0].splitlines()[0]))
        # G7: kapsam ekseni — SERIT_B_DOSYALARI'nda OLMAYAN bir nobet adi KIRMIZI.
        iddia += 1
        yaz(G_YAYIN_FIKSTUR, G_NOBET_FIKSTUR)
        kapsam_disi, _ = yayin_sinyali_kontrol(gecici, nobet_dosyasi="zzz-yok.yml")
        if not any(h.startswith("G7") for h in kapsam_disi):
            hatalar.append("G7 KAPSAM EKSENI OLU: SERIT_B_DOSYALARI disindaki bir nobet "
                           "dosyasi KIRMIZI yakmadi -> 52 serit-B beyani sessizce "
                           "denetimsiz birakilabilirdi (%r)" % (kapsam_disi,))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    # ---- KOSUM SONUCU SIMULATORU (KANONIK OLCUT, iki yonlu) -----------------
    y_govde, y_hata = ayristir(G_YAYIN_FIKSTUR)
    n_govde, n_hata = ayristir(G_NOBET_FIKSTUR)
    iddia += 1
    if y_hata or n_hata:
        hatalar.append("G-SIMULATOR OLCULEMEDI: sentetik fikstur ayristirilamadi "
                       "(%s / %s)" % (y_hata, n_hata))
    else:
        for ad, kirmizi, beklenen, deploy_kosmali in G_SIMULASYON:
            iddia += 1
            if kirmizi and kirmizi.startswith("nobet:"):
                # Alarm KENDI is akisinda kirmizi: yayin kosumu HIC etkilenmez +
                # alarm kendi kosumunda GORUNUR. IKI AYRI IDDIA.
                n_sonuc, _n_kosan = kosum_sonucu(n_govde, {kirmizi.split(":", 1)[1]})
                iddia += 1
                if n_sonuc != "failure":
                    hatalar.append("G-SIMULATOR: alarm kirmizi ama NOBET kosumunun "
                                   "conclusion'i %r -> alarm KENDI kanalinda GORUNMUYOR "
                                   "(susturma = cozulen kusurun tersi)" % n_sonuc)
                sonuc, kosan = kosum_sonucu(y_govde, ())
            else:
                sonuc, kosan = kosum_sonucu(y_govde, {kirmizi} if kirmizi else ())
            if sonuc != beklenen:
                hatalar.append("G-SIMULATOR YANLIS (%s): conclusion %r bekleniyordu, %r "
                               "olculdu" % (ad, beklenen, sonuc))
            if ("deploy" in kosan) != deploy_kosmali:
                hatalar.append("G-SIMULATOR YANLIS (%s): `deploy` kosmali=%r, olculen "
                               "kosan kume=%r" % (ad, deploy_kosmali, sorted(kosan)))
    return hatalar, iddia


S_HEDEF = D_HEDEF
S_CAGRI = "python3 " + S_HEDEF
# Sentetik SERIT fiksturu: `deploy` (Pages yayini) YALNIZ `build`'e baglidir; `build`
# de `onhazirlik`a. Yani BLOKLAYAN kume = {deploy, build, onhazirlik}; `serit-b`
# yayini bloklamaz. Ucu de AYNI kapiyi kosar -> eksen "job'a gore" ayirmali.
S_FIKSTUR = """\
name: "Sentetik SERIT fiksturu"
on:
  push:
    branches: [main]
jobs:
  onhazirlik:
    runs-on: ubuntu-latest
    steps:
      - name: "A-ata: kapi"
        run: %(c)s
  build:
    needs: onhazirlik
    runs-on: ubuntu-latest
    steps:
      - name: "A: kapi"
        run: %(c)s
  serit-b:
    runs-on: ubuntu-latest
    steps:
      - name: "B: kapi"
        run: %(c)s
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/deploy-pages@v4
""" % {"c": S_CAGRI}


def _serit_b_mekanizma_kontrol():
    """SERIT AYRIMI ekseninin KACIS DELIGI OLMAMASINI olcer (9 iddia).

    Sentetik bir deploy.yml gecici dizine yazilir ve bolum_d() TA KENDISI kosulur
    (kopya mantik yazilmaz — [[mimar-kapi-parser-taklidi]]).

      (i)    beyansiz serit-B cagrisi            -> KIRMIZI, TAM 1 tane
      (ii)   BLOKLAYAN joblardaki ayni cagri     -> SESSIZ (yanlis-pozitif nobeti)
      (iii)  gerekceli beyan                     -> bulgu DUSER
      (iv)   BOS gerekce                         -> KIRMIZI
      (v)    JOKER (`*`) beyan                   -> KIRMIZI ve bulguyu DUSURMEZ
      (vi)   BAYAT beyan (kullanilmayan anahtar) -> KIRMIZI
      (vii)  YANLIS JOB'a yazilmis beyan         -> KIRMIZI (job alani gercekten olculuyor)
      (viii) `deploy` serit-b'ye de BAGLANIRSA   -> cagri artik SEBEPSIZ (graf okunuyor)
      (ix)   Pages yayin adimi YOKSA             -> OLCULEMEDI, fail-closed KIRMIZI
    """
    global SERIT_B
    hatalar = []
    gecici = tempfile.mkdtemp(prefix="pruvo-isakisi-serit-")
    yedek = SERIT_B
    anahtar = (E_DOSYA, "serit-b", S_HEDEF)

    def yaz(metin):
        with open(os.path.join(gecici, E_DOSYA), "w", encoding="utf-8") as f:
            f.write(metin)

    def olc(tablo, metin=S_FIKSTUR):
        global SERIT_B
        SERIT_B = tablo
        yaz(metin)
        return bolum_d(gecici)

    try:
        # (i) + (ii) TABAN: beyan yok -> TAM 1 beyansiz bulgu (yalniz `serit-b`).
        taban, _t, _e, _i = olc({})
        beyansiz = [h for h in taban if "SERIT B'DE BEYANSIZ KAPI" in h]
        if len(beyansiz) != 1:
            hatalar.append("SERIT TABANI BOZUK: beyansiz serit-B cagrisi icin TAM 1 "
                           "bulgu bekleniyordu, %d bulundu (%r)" % (len(beyansiz), taban))
        if beyansiz and ("job: serit-b" not in beyansiz[0]):
            hatalar.append("SERIT EKSENI YANLIS JOB'U SUCLADI: bulgu `serit-b` job'unu "
                           "gostermiyor -> BLOKLAYAN joblar (build/onhazirlik) yanlis "
                           "siniflaniyor olabilir (%r)" % (beyansiz[0],))
        # (iii) gerekceli beyan -> bulgu DUSER
        gecerli, _t, _e, _i = olc({anahtar: "SENTETIK OLCUM GIRISI — mekanizma testi."})
        if any("SERIT B" in h for h in gecerli):
            hatalar.append("SERIT BEYAN KABULU BOZUK: gerekceli beyan bulguyu dusurmedi "
                           "(%r)" % (gecerli,))
        # (iv) BOS gerekce -> KIRMIZI
        bos, _t, _e, _i = olc({anahtar: "   "})
        if not any("SERIT_B GEREKCESIZ" in h for h in bos):
            hatalar.append("SERIT GEREKCE KAPISI OLU: bos gerekce KIRMIZI yakmadi (%r)"
                           % (bos,))
        # (v) JOKER beyan -> KIRMIZI + bulguyu DUSURMEZ (blanket yasak)
        joker, _t, _e, _i = olc({(E_DOSYA, "*", S_HEDEF): "Hepsini tek satirda beyan et."})
        if not any("BLANKET/JOKER" in h for h in joker):
            hatalar.append("SERIT JOKER KAPISI OLU: `*` iceren anahtar KIRMIZI yakmadi "
                           "-> tek satirla TUM kapilar serit B'ye atilabilirdi (%r)"
                           % (joker,))
        if not any("SERIT B'DE BEYANSIZ KAPI" in h for h in joker):
            hatalar.append("SERIT JOKER KACISI: joker beyan gercek bulguyu DUSURDU -> "
                           "blanket beyan fiilen ise yariyor (%r)" % (joker,))
        # (vi) BAYAT beyan -> KIRMIZI
        bayat, _t, _e, _i = olc({anahtar: "Gecerli.",
                                 (E_DOSYA, "serit-b", "tools/ci-kapsam-test.py"):
                                     "Bu fiksturde HIC kosmuyor."})
        if not any("SERIT_B BAYAT giris" in h for h in bayat):
            hatalar.append("SERIT BAYATLIK KAPISI OLU: kullanilmayan beyan KIRMIZI "
                           "yakmadi -> liste kendiliginden buyuyup kalabilir (%r)"
                           % (bayat,))
        # (vii) YANLIS JOB'a yazilmis beyan -> KIRMIZI (job alani gercekten olculuyor)
        yanlis_job, _t, _e, _i = olc({(E_DOSYA, "build", S_HEDEF): "Yanlis job."})
        if not any("SERIT B'DE BEYANSIZ KAPI" in h for h in yanlis_job):
            hatalar.append("SERIT JOB ALANI OLU: baska bir job icin yazilan beyan "
                           "`serit-b` bulgusunu dusurdu -> anahtarin job alani "
                           "olculmuyor (%r)" % (yanlis_job,))
        # (viii) `deploy` serit-b'ye de baglanirsa cagri artik SEBEPSIZ olmali
        bagli = S_FIKSTUR.replace("  deploy:\n    needs: build\n",
                                  "  deploy:\n    needs: [build, serit-b]\n")
        baglanan, _t, _e, _i = olc({}, bagli)
        if any("SERIT B'DE BEYANSIZ KAPI" in h for h in baglanan):
            hatalar.append("SERIT GRAFI OKUNMUYOR: `deploy` job'u serit-b'ye `needs:` ile "
                           "BAGLANDIGI halde cagri hala 'yayini bloklamaz' sayildi -> "
                           "eksen job ADINA capalanmis olabilir (%r)" % (baglanan,))
        # (ix) Pages yayin adimi YOKSA -> fail-closed OLCULEMEDI
        yayinsiz = S_FIKSTUR.replace("      - uses: actions/deploy-pages@v4\n",
                                     "      - run: echo yayin-yok\n")
        olcelemez, _t, _e, _i = olc({}, yayinsiz)
        if not any("SERIT AYRIMI OLCULEMEDI" in h for h in olcelemez):
            hatalar.append("SERIT FAIL-CLOSED OLU: Pages yayin adimi YOKKEN eksen sessizce "
                           "atlandi -> `actions/deploy-pages` satirini silmek TUM serit "
                           "nobetini kapatirdi (%r)" % (olcelemez,))
    finally:
        SERIT_B = yedek
        shutil.rmtree(gecici, ignore_errors=True)
    return hatalar


# Bolum F sentetik fiksturleri (S_FIKSTUR ile ayni topoloji: BLOKLAYAN =
# {deploy, build, onhazirlik}, BLOKLAMAYAN = {serit-b}).
# F_YALNIZ_B: cagri YALNIZ serit-b'de (bloklamayan) — bugun kacirilan vaka.
F_YALNIZ_B = """\
name: "Sentetik F fiksturu: cagri yalniz bloklamayan job'da"
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: "A: baska is"
        run: echo derleme
  serit-b:
    runs-on: ubuntu-latest
    steps:
      - name: "B: kapi"
        run: %(c)s
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/deploy-pages@v4
""" % {"c": S_CAGRI}

# F_YOK: cagri HICBIR yerde yok.
F_YOK = """\
name: "Sentetik F fiksturu: cagri yok"
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: "A: baska is"
        run: echo derleme
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/deploy-pages@v4
"""

# F_FAILOPEN: cagri BLOKLAYAN job'da AMA `|| true` ile etkisiz.
F_FAILOPEN = """\
name: "Sentetik F fiksturu: bloklayan job ama fail-open"
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: "A: kapi (fail-open)"
        run: %(c)s || true
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/deploy-pages@v4
""" % {"c": S_CAGRI}


def _bolum_f_mekanizma_kontrol():
    """BOLUM F (BLOKLAYICI-BEYAN DOGRULAMASI) KACIS DELIGI OLMAMASINI olcer (8 iddia).

    Sentetik deploy.yml gecici dizine yazilir ve bloklayici_kapi_kontrol() TA
    KENDISI SENTETIK registry ile kosulur (kopya mantik yazilmaz). Bu tam da uc
    curutmenin gecirdigi vakayi civiler: adim bloklamayan job'da + beyan
    'bloklayici' -> KIRMIZI."""
    hatalar = []
    gecici = tempfile.mkdtemp(prefix="pruvo-isakisi-f-")
    kapilar = {(E_DOSYA, S_HEDEF): "SENTETIK: bu kapi yayini BLOKLAMALI."}

    def yaz(metin):
        with open(os.path.join(gecici, E_DOSYA), "w", encoding="utf-8") as f:
            f.write(metin)

    def olc(metin, kap=None, sb=None):
        yaz(metin)
        return bloklayici_kapi_kontrol(gecici, kapilar=kap if kap is not None else kapilar,
                                       serit_b_tablo=sb if sb is not None else {})

    try:
        # (i) KONTROL: cagri BLOKLAYAN job'da (build) -> F sessiz
        iyi, _i = olc(S_FIKSTUR)
        if any("BLOKLAYICI" in h for h in iyi):
            hatalar.append("F-YANLIS-POZITIF: cagri bloklayan job'da oldugu halde F "
                           "kirmizi yakti (%r)" % (iyi,))
        # (ii) OLDURUCU (BUGUNKU VAKA): cagri YALNIZ bloklamayan job'da -> KIRMIZI
        kotu, _i = olc(F_YALNIZ_B)
        if not any("BEYAN GERCEGE UYMUYOR" in h for h in kotu):
            hatalar.append("F EKSENI OLU (BUGUNKU VAKA): adim yalniz BLOKLAMAYAN "
                           "job'da iken 'BLOKLAYICI' beyani KIRMIZI yakmadi -> uc "
                           "curutmeyi geciren tam bu delik (%r)" % (kotu,))
        # (iii) adim YOK -> KIRMIZI
        yok, _i = olc(F_YOK)
        if not any("ADIM YOK/ETKISIZ" in h for h in yok):
            hatalar.append("F ADIM-YOK KAPISI OLU: hic cagri olmayan fikstur icin "
                           "'BLOKLAYICI beyan' KIRMIZI yakmadi (%r)" % (yok,))
        # (iv) BOS gerekce -> KIRMIZI
        bos, _i = olc(S_FIKSTUR, kap={(E_DOSYA, S_HEDEF): "  "})
        if not any("GEREKCESIZ" in h for h in bos):
            hatalar.append("F GEREKCE KAPISI OLU: bos gerekce KIRMIZI yakmadi (%r)"
                           % (bos,))
        # (v) BLOKLAYAN job'da AMA fail-open -> ETKILI cagri yok -> KIRMIZI
        fo, _i = olc(F_FAILOPEN)
        if not any("ADIM YOK/ETKISIZ" in h for h in fo):
            hatalar.append("F ETKISIZLIK KAPISI OLU: bloklayan job'da `|| true` ile "
                           "etkisiz cagri 'bloklayici' sayildi (%r)" % (fo,))
        # (vi) YON 2 OLDURUCU: SERIT_B girisi BLOKLAYAN job'da -> KIRMIZI
        sb_kotu, _i = olc(S_FIKSTUR, kap={},
                          sb={(E_DOSYA, "build", S_HEDEF): "yanlislikla guvenli"})
        if not any("yanlis GUVENLI beyani" in h for h in sb_kotu):
            hatalar.append("F YON-2 OLU: SERIT_B girisi BLOKLAYAN bir job'u "
                           "gosterdigi halde KIRMIZI yakmadi (yanlis 'guvenli' "
                           "beyani gecti) (%r)" % (sb_kotu,))
        # (vii) YON 2 KONTROL: SERIT_B girisi bloklamayan job'da -> SESSIZ
        sb_iyi, _i = olc(S_FIKSTUR, kap={},
                         sb={(E_DOSYA, "serit-b", S_HEDEF): "gercekten guvenli"})
        if any("yanlis GUVENLI" in h for h in sb_iyi):
            hatalar.append("F YON-2 YANLIS-POZITIF: bloklamayan job'daki SERIT_B "
                           "girisi KIRMIZI yakti (%r)" % (sb_iyi,))
        # (viii) Pages yayin adimi YOKSA -> fail-closed OLCULEMEDI
        yayinsiz = S_FIKSTUR.replace("      - uses: actions/deploy-pages@v4\n",
                                     "      - run: echo yayin-yok\n")
        oy, _i = olc(yayinsiz)
        if not any("OLCULEMEDI" in h for h in oy):
            hatalar.append("F FAIL-CLOSED OLU: Pages yayin adimi YOKKEN F sessizce "
                           "gecti -> deploy-pages satirini silmek F'i kapatirdi (%r)"
                           % (oy,))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    return hatalar


def _tablo_mekanizma_kontrol():
    """(hatalar, iddia) — NOBETCININ NOBETCISI: tablo_sayaci_kontrol() ve
    bolum_kablosu_kontrol() govdeleri GERCEKTEN olcuyor mu (SENTETIK tablolarla surulur,
    kopya mantik yazilmaz; canli tablolar `finally` ile geri konur).

    🔴 OLCULEN KACIS (30 Tem oz-koruma turu, mutant 17/18): o iki govde `return []`
    yapilinca HICBIR sey konusmuyordu — DIGER nobetcileri koruyorlar ama KENDILERI
    korumasizdi.

    🔴 NEDEN ADLI FONKSIYON + TURETILEN SAYAC (8 Agu, 3. tur — bagimsiz curutucu M6):
    bu blok kendini_test() govdesinde INLINE dururken sayaci elle yazilmis bir IKIZDI
    (`iddia += 6`). Curutucu olctu: BUYUME iddiasi silinip operator `<`'ye dondurulunce
    kapi rc=0, `--kendini-test` rc=0 ve iddia sayisi HALA 204 kaliyordu -> yeni eksen
    SESSIZCE silinebiliyordu ("kapiya eklenen eksen kendini koruyamiyorsa eksen degil
    sustur"). Iki onarim birlikte:
      (1) ADLI fonksiyon + KABLO_TABLOSU kablosu -> CAGRININ silinmesi kablo kapisina
          takilir (bolum_kablosu_kontrol, AST ile).
      (2) iddia her iddianin YANINDA +1 edilir (lump ikiz YOK) -> bir iddia silindiginde
          sayac DUSER ve KENDINI_TEST_TABAN (`<`) o dususu KIRMIZI yakar.
    Govdenin bosaltilmasi (`return [], 0`) BOLUM E'de mutant olarak olculur."""
    hatalar = []
    iddia = 0
    _t_yedek = globals()["TABLO_TABANLARI"]
    _k_yedek = globals()["KABLO_TABLOSU"]
    try:
        iddia += 1
        globals()["TABLO_TABANLARI"] = (("B_IDDIALAR", 9999),)
        if not any("TABLO SAYACI KIRMIZI" in h for h in tablo_sayaci_kontrol()):
            hatalar.append("TABLO-NOBETCISI OLU: TABAN'in ALTINDA kalan bir tablo "
                           "KIRMIZI yakmadi -> fikstur tablolari sessizce bosaltilabilir")
        # BUYUME EKSENI (tam esitligin tek kanidi): taban = len - 1.
        iddia += 1
        globals()["TABLO_TABANLARI"] = (("B_IDDIALAR", len(B_IDDIALAR) - 1),)
        if not any("TABLO SAYACI KIRMIZI" in h for h in tablo_sayaci_kontrol()):
            hatalar.append("TABLO-NOBETCISI OLU (BUYUME EKSENI): taban guncellenmeden "
                           "BUYUME gorunmez -> pay birikir, taban kozmetiklesir ve pay "
                           "kadar giris tek commit'te SESSIZCE silinebilir (olculdu: "
                           "SERIT_B 67/42, pay 25). Operator `!=` olmali, `<` DEGIL.")
        # KONTROL IDDIASI (yanlis-pozitif kanaryasi): TAM taban KIRMIZI YAKMAMALI.
        iddia += 1
        globals()["TABLO_TABANLARI"] = (("B_IDDIALAR", len(B_IDDIALAR)),)
        if [h for h in tablo_sayaci_kontrol() if "B_IDDIALAR" in h]:
            hatalar.append("TABLO-NOBETCISI SAHTE-KIRMIZI: TAM tabanda (len == taban) "
                           "hata uretildi -> tam esitlik yanlis kuruldu ve TUM EKIBIN "
                           "yayini durur")
        iddia += 1
        globals()["TABLO_TABANLARI"] = (("HIC_OLMAYAN_TABLO_XYZ", 1),)
        if not any("ARTIK YOK" in h for h in tablo_sayaci_kontrol()):
            hatalar.append("TABLO-NOBETCISI OLU: ARTIK OLMAYAN bir tablo adi KIRMIZI "
                           "yakmadi -> yeniden adlandirma nobetciyi sessizce dusurur")
        globals()["TABLO_TABANLARI"] = _t_yedek
        iddia += 1
        globals()["KABLO_TABLOSU"] = (("main", ("hic_olmayan_fonksiyon_xyz",)),)
        if not any("BOLUM KABLOSU KOPMUS" in h for h in bolum_kablosu_kontrol()):
            hatalar.append("KABLO-NOBETCISI OLU: main()'de OLMAYAN bir zorunlu cagri "
                           "KIRMIZI yakmadi -> bolum kablolari sessizce kopabilir")
        iddia += 1
        globals()["KABLO_TABLOSU"] = (("hic_olmayan_fonksiyon_xyz", ("main",)),)
        if not any("OLCULEMEDI" in h for h in bolum_kablosu_kontrol()):
            hatalar.append("KABLO-NOBETCISI FAIL-OPEN: OLMAYAN bir SAHIP fonksiyon "
                           "sessizce gecti (fail-closed KIRMIZI olmaliydi)")
    finally:
        globals()["TABLO_TABANLARI"] = _t_yedek
        globals()["KABLO_TABLOSU"] = _k_yedek
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
        # ---- K-21a: "VAR OLMAK" YETMEZ (uc yeni kural) ----------------------
        # (iv) dayanak VAR ama NOBETCI DEGIL (kesif disi) -> KIRMIZI
        ilgisiz, _, _, _ = olc({anahtar: ("Alakasiz ama MEVCUT bir yol.", "CNAME")})
        if not any("NOBETCI DEGIL" in h for h in ilgisiz):
            hatalar.append("D-IZIN K-21a OLU: repoda VAR OLAN ama kabul testi/kapi "
                           "OLMAYAN bir yol (`CNAME`) muafiyeti gecerli kildi -> "
                           "'kaybi su nobetci karsiliyor' beyani HICBIR SEY olcmuyor "
                           "(%r)" % (ilgisiz,))
        # (v) dayanak DAIRESEL (muaf tutulan kapinin KENDISI) -> KIRMIZI
        dairesel, _, _, _ = olc({anahtar: ("Kendi kendini gosteriyor.", D_HEDEF)})
        if not any("DAIRESEL DAYANAK" in h for h in dairesel):
            hatalar.append("D-IZIN DAIRESEL KAPISI OLU: muaf tutulan kapinin KENDISI "
                           "dayanak gosterildiginde KIRMIZI yanmadi (%r)" % (dairesel,))
        # (vi) dayanak KESIFTE VAR ama deploy.yml'de KOSMUYOR -> KIRMIZI
        kesif_k, kosan_k, _t = _kosan_kapilar(gecici)
        kosmayan = sorted((kesif_k or set()) - (kosan_k or set()) - {anahtar[1]})
        if not kosmayan:
            hatalar.append("D-IZIN KOSAN-DAYANAK IDDIASI OLCULEMEDI: kesifte olup "
                           "deploy.yml'de kosmayan HICBIR kabul testi yok (muaf liste "
                           "bosalmis olabilir) -> iddia sinanmadi")
        else:
            olu_nobetci, _, _, _ = olc({anahtar: ("Kosmayan bir nobetciye dayaniyor.",
                                                  kosmayan[0])})
            if not any("CI'DA KOSMUYOR" in h for h in olu_nobetci):
                hatalar.append("D-IZIN KOSAN-DAYANAK KAPISI OLU: deploy.yml'de FIILEN "
                               "kosmayan bir nobetci (%s) dayanak gosterildiginde "
                               "KIRMIZI yanmadi -> muafiyet kagit uzerinde bir korumaya "
                               "dayanabilir (%r)" % (kosmayan[0], olu_nobetci))
        # (vii) YANLIS-POZITIF KANARYASI: kesifte VAR + deploy.yml'de KOSAN +
        #       muaf kapidan FARKLI bir dayanak KABUL EDILMELI.
        kosan_aday = sorted((kosan_k or set()) - {anahtar[1]})
        if kosan_aday:
            gecerli2, _, _, izinli2 = olc({anahtar: ("Gercek, kosan, farkli nobetci.",
                                                     kosan_aday[0])})
            if any("D_IZIN" in h and "BAYAT giris" not in h for h in gecerli2) \
                    or izinli2 != 1:
                hatalar.append("D-IZIN K-21a YANLIS-POZITIF: GECERLI bir dayanak (%s — "
                               "kesifte var, deploy.yml'de kosuyor, muaf kapidan farkli) "
                               "REDDEDILDI -> mesru bir beyan yapilamaz hale gelir (%r)"
                               % (kosan_aday[0], gecerli2))
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

    # 🔴 IDDIA SAYACI TABANI (K-20a, oz-koruma turu mutant 16): `kendini_test()` govdesi
    # `return [], 0` yapilinca 139 ariza-enjeksiyon iddiasinin HEPSI sessizce dusuyor ve
    # KAPI YESIL YANIYORDU (olculdu) — cunku "hata YOK" ile "OLCUM YOK" ayirt edilmiyordu.
    # Sayac tabani bu ikisini ayirir: Bolum C BUYUYEBILIR, KUCULEMEZ.
    # 🔴 Bulgu `hatalar`'a KONMAZ, DOGRUDAN cikilir: bu mutasyon Bolum C'yi oldurur,
    # yani raporu tam o olu yoldan gecirmek anlamsizdir (MAIN CIKIS KODU nobetcisiyle
    # ayni gerekce). Kabul edilen sinir: bu SATIRI da silen IKI ADIMLI mutasyon kacar.
    if c_iddia < KENDINI_TEST_TABAN:
        _cikis_yolu_kirmizi([KENDINI_TEST_TABAN_TANI % (c_iddia, KENDINI_TEST_TABAN)])

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
        print("  ✅ B-MESRU-YAZIM (K-25): %d MESRU bicim (`python3 -u`, `env X=1`, "
              "`bash -c`, `-X utf8`, shebang, `\\` devami) ETKILI sayiliyor — kaba capa "
              "mirasi SAHTE-KIRMIZI yakmiyor" % len(B_MESRU_YAZIMLAR))
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
        print("  ✅ D_IZIN DAYANAK KALITESI (K-21a): NOBETCI OLMAYAN mevcut yol "
              "(`CNAME`) KIRMIZI · DAIRESEL (kapinin kendisi) KIRMIZI · deploy.yml'de "
              "KOSMAYAN nobetci KIRMIZI · gercek+kosan+farkli dayanak KABUL")
        print("  ✅ SERIT AYRIMI (31 Tem): yayini BLOKLAMAYAN job'daki BEYANSIZ kapi "
              "KIRMIZI · BLOKLAYAN joblar (gecisli `needs:` atalari) SESSIZ · JOKER "
              "(`*`) beyan KIRMIZI ve bulguyu DUSURMEZ · yanlis job'a yazilan beyan "
              "KIRMIZI · BAYAT beyan KIRMIZI · `deploy` B'ye baglanirsa sebep DUSER · "
              "`actions/deploy-pages` adimi yoksa fail-closed OLCULEMEDI")
        print("  ✅ BOLUM F (BLOKLAYICI-BEYAN, 4 Agu): adim BLOKLAYAN job'da SESSIZ · "
              "adim yalniz BLOKLAMAYAN job'da iken 'bloklayici' beyani KIRMIZI (bugunku "
              "vaka) · adim YOK/fail-open KIRMIZI · bos gerekce KIRMIZI · SERIT_B girisi "
              "BLOKLAYAN job'u gosterirse 'yanlis guvenli' KIRMIZI · bloklamayan job "
              "SESSIZ · deploy-pages yoksa fail-closed OLCULEMEDI")
        print("  ✅ K26-KABUK YAPISI: %d satir fiksturu (%d gercek oldurucu + %d MESRU "
              "kanarya) dogru siniflandi — her biri `bash -e` ile OLCULDU"
              % (len(K26_SATIR_FIKSTURLERI),
                 sum(1 for m in K26_SATIR_FIKSTURLERI if m[2]),
                 sum(1 for m in K26_SATIR_FIKSTURLERI if not m[2])))
        print("  ✅ K26-BAGLAM: heredoc govdesi · CAGRILMAYAN fonksiyon govdesi · "
              "KOSMAYAN job (`needs:` yayilimi) · yalniz-`workflow_call` OLU is akisi "
              "ETKISIZ; cagrilan fonksiyon/temiz job/mesru tetikleyici ETKILI")
        print("  ✅ K29-ADIM TURU: %d fikstur (%d fail-open + %d mesru yazim) dogru "
              "siniflandi + dosya YOKKEN fail-closed KIRMIZI"
              % (len(K29_MUTANTLAR), sum(1 for m in K29_MUTANTLAR if m[2]),
                 sum(1 for m in K29_MUTANTLAR if not m[2])))
        print("  ✅ E-POZITIF: temiz sentetik fiksturde `on.push` + %d zorunlu kapi adimi "
              "+ %d zorunlu yayin varligi ETKILI sayiliyor (iddia sayaci da olculdu)"
              % (len(E_ZORUNLU_CAGRILAR), len(E_ZORUNLU_VARLIKLAR)))
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
    b_hata, cagri_sayisi, b_iddia_sayisi, b_adim_iddia = bolum_b(args.dizin)
    hatalar.extend(b_hata)
    d_hata, d_toplam, d_etkisiz, d_izinli = bolum_d(args.dizin)
    hatalar.extend(d_hata)
    e_hata, e_iddia = bolum_e(args.dizin)
    hatalar.extend(e_hata)
    f_hata, f_iddia = bloklayici_kapi_kontrol(args.dizin)
    hatalar.extend(f_hata)
    g_hata, g_iddia = yayin_sinyali_kontrol(args.dizin)
    hatalar.extend(g_hata)

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
    print("  ADIM TURU iddiasi (K-29) : %d  (%s — kabul testi KOSMAYAN, Bolum D'nin "
          "GORMEDIGI adimlar)" % (
              b_adim_iddia, ", ".join(i.kimlik for i in B_ADIM_IDDIALARI) or "-"))
    print("  Olculen kapi cagrisi     : %d  (is akisi dosyalarindaki kabul-testi cagrilari)"
          % d_toplam)
    print("  Etkisizlestirilmis       : %d  (fail-open: continue-on-error / `|| true` / "
          "`if: false` / `set +e`)" % d_etkisiz)
    print("  D_IZIN beyan edilmis     : %d  (%s)" % (
        d_izinli, ", ".join("%s::%s" % a for a in sorted(D_IZIN)) or "-"))
    print("  SERIT B beyani (tek tek) : %d  (yayini BLOKLAMAYAN job'da BILEREK kosan "
          "kapi; joker `*` YASAK)" % len(SERIT_B))
    print("  BLOKLAYICI beyan (F)     : %d iddia  (%d BLOKLAYICI_KAPILAR + %d SERIT_B "
          "girisi GERCEGE karsi: adim-job bloklayici mi?)"
          % (f_iddia, len(BLOKLAYICI_KAPILAR), len(SERIT_B)))
    print("  Tetikleyici/zorunlu adim : %d iddia  (%s: `on.push` + %d zorunlu kapi adimi "
          "+ %d zorunlu yayin varligi)"
          % (e_iddia, " + ".join(sorted(set([E_DOSYA] + [a for a, _k, _b, _e
                                                         in E_ZORUNLU_CAGRILAR]))),
             len(E_ZORUNLU_CAGRILAR), len(E_ZORUNLU_VARLIKLAR)))
    print("  Yayin sinyali (G)        : %d iddia  (%s kosum rengi YALNIZ yayin "
          "zincirini anlatir; alarmlar %s'de kendi conclusion'inda)"
          % (g_iddia, E_DOSYA, N_DOSYA))
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
