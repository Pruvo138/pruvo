#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/yaml-oku.py — GERCEK YAML AYRISTIRICISI (KATMAN 0, ortak kaynak).

NE YAPAR: bir is-akisi metnindeki her `run:` esleme girdisini GERCEK bir YAML
ayristiricisiyla cozer ve (anahtar_satir, ilk_ham_satir, son_ham_satir, deger) dondurur.
Yani hem SKALAR DEGERI (katlama/literal/tirnak/anchor kurallari ayristirici tarafindan
uygulanmis) hem de o degerin HAM SATIR ARALIGI verilir — ikincisi mutant ureticilerinin
(satir silme / yoruma cevirme) capasi icin sarttir.

🔴 NEDEN AYRI DOSYA (30 Tem, PARSER-FIRST hukmu):
  * tools/ci-kapsam-test.py (KATMAN 1) YAML katlamasini METIN duzleminde TAKLIT ediyordu.
    Olculdu (differential fuzzing, 1150 girdi): taklit ile gercek ayristirici 1037
    kiyaslanabilir girdinin 303'unde FARKLI hukum veriyordu — 274 sahte-KIRMIZI ve
    29 sahte-YESIL bilesenli. Yani taklit hem yayini gereksiz durduruyor hem de en az
    iki sinifta (TAB girintili satir, anchor'li blok) kapiyi SESSIZCE gevsetiyordu.
  * tools/is-akisi-kapisi.py (KATMAN 2) kesfini ci-kapsam-test.py'den ALIR; oradan
    ayristirici ithal etmek karsilikli bagimlilik yaratirdi. Bu dosya KATMAN 0'dir:
    kimseyi ithal etmez, herkes ithal edebilir ([[ayna-kapi-kesif-ekseni]]).
  * "PyYAML her yerde yok" gerekcesi OLCULDU ve CURUDU: CI'da PyYAML kurulu
    (deploy.yml `pip install boto3 pyyaml`), bu Mac'te PyYAML YOK ama ruby/psych VAR
    (Psych 3.1.0). Iki kol da GERCEK ayristiricidir ve ayni fuzz kumesinde
    psych <-> PyYAML sapmasi 0 olculdu.

KOL SIRASI: PyYAML -> ruby/psych -> (hicbiri yok) None.
`ayristirici_adi()` None dondururse CAGIRAN fail-closed davranmak ZORUNDADIR: bu dosya
kendi basina "taklit" yapmaz, tahmin uretmez.

KULLANIM (kutuphane):
    import yaml_oku
    bloklar, hata = yaml_oku.run_dugumleri(metin)
    # bloklar = [(anahtar_satir, ilk_ham, son_ham, deger), ...] ya da hata varsa None
    tetikler, hata = yaml_oku.tetikleyiciler(metin)
    # tetikler = {"push", "workflow_dispatch", ...} ya da hata varsa None
"""
import json
import subprocess

try:
    import yaml as _yaml
except Exception:  # pragma: no cover - ortam bagimli
    _yaml = None


# ---- RUBY/PSYCH YEDEK KOLU -------------------------------------------------
# Girdi : stdin'e JSON {"metinler": ["...", ...]}
# Cikti : stdout'a JSON [{"ok":true,"bloklar":[[anahtar,bas,son,deger], ...]}, ...]
# Anchor/alias: alias dugumu COZULUR (anchor tablosu belge boyunca toplanir); alias'in
# HAM satiri anchor'in satir araligiyla ORTUSTUGU icin cagiran tarafi normalize eder.
RUBY_KAYNAK = r"""
require 'yaml'
require 'json'

def capa_topla(node, capalar)
  return if node.nil?
  # 🔴 ALIAS DUGUMU CAPA TABLOSUNA YAZILMAZ: Psych'te Alias da `anchor`'a CEVAP VERIR,
  # ve belge sirasinda alias TANIMDAN SONRA geldigi icin tabloyu EZIYORDU -> `coz()`
  # alias'i yine bir Alias'a cozup vazgeciyordu (olculdu: `on: *t` psych'te None,
  # pyyaml'da {'push'} -> KOL SAPMASI). Yalniz TANIM dugumleri toplanir.
  if !node.is_a?(Psych::Nodes::Alias) &&
     node.respond_to?(:anchor) && node.anchor && !node.anchor.to_s.empty?
    capalar[node.anchor] ||= node
  end
  if node.respond_to?(:children) && node.children
    node.children.each { |c| capa_topla(c, capalar) }
  end
end

# ALIAS COZUMU — PyYAML `compose` SEMANTIGI:
#   * TANIMSIZ alias  -> ComposerError (pyyaml) => burada da HATA
#   * ILERI alias (tanimdan ONCE kullanim) -> pyyaml'da TANIMSIZDIR => HATA
# Ikisi de sessizce `nil`/`[]` donerse kol sapmasi olur (olculdu: `run: *yok`
# pyyaml HATA / psych [] ; `run: *c` ileri alias pyyaml HATA / psych blok).
def coz(node, capalar)
  gorulen = 0
  while node.is_a?(Psych::Nodes::Alias) && gorulen < 32
    hedef = capalar[node.anchor]
    if hedef.nil? || hedef.start_line > node.start_line
      raise "TANIMSIZ/ILERI ALIAS: *#{node.anchor}"
    end
    node = hedef
    gorulen += 1
  end
  node
end

def gez(node, capalar, out)
  return if node.nil?
  if node.is_a?(Psych::Nodes::Mapping)
    node.children.each_slice(2) do |k, v|
      next if v.nil?
      if k.is_a?(Psych::Nodes::Scalar) && k.value == 'run'
        hedef = coz(v, capalar)
        if hedef.is_a?(Psych::Nodes::Scalar)
          son = hedef.end_column == 0 ? hedef.end_line - 1 : hedef.end_line
          out << [k.start_line, hedef.start_line, son, hedef.value]
        end
      end
      gez(coz(v, capalar), capalar, out)
    end
  elsif node.respond_to?(:children) && node.children
    node.children.each { |c| gez(c, capalar, out) }
  end
end

girdi = JSON.parse($stdin.read)
sonuc = girdi['metinler'].map do |metin|
  begin
    # 🔴 TEK BELGE SARTI (P3): ONCE `Psych.parse` yalniz ILK belgeyi okuyordu, PyYAML
    # `compose_all` ise TUM belgeleri goruyordu -> ayni girdide farkli blok kumesi.
    # TETIK kolu bu yamayi almisti, RUN kolu ALMAMISTI: AYNI DOSYADA ASIMETRIK ONARIM.
    # Iki kol da artik "belge != 1 -> fail-closed".
    akis = Psych.parse_stream(metin)
    belgeler = akis.nil? ? [] : akis.children
    if belgeler.size != 1
      { 'ok' => false,
        'hata' => "TEK BELGE DEGIL (#{belgeler.size} belge) -> fail-closed" }
    else
      capalar = {}
      capa_topla(belgeler[0], capalar)
      out = []
      gez(belgeler[0], capalar, out)
      { 'ok' => true, 'bloklar' => out }
    end
  rescue => e
    { 'ok' => false, 'hata' => "#{e.class}: #{e.message}" }
  end
end
print JSON.generate(sonuc)
"""

# ---- RUBY/PSYCH TETIKLEYICI KOLU -------------------------------------------
# Girdi : stdin'e JSON {"metinler": ["...", ...]}
# Cikti : stdout'a JSON [{"ok":true,"tetikler":["push", ...]}, ...]
#
# 🔴 NEDEN DUGUM (Psych.parse) API'si, `Psych.load` DEGIL — YAML 1.1 `on:` TUZAGI:
# YAML 1.1'de ciplak `on` bir BOOLEAN'dir. `Psych.load` (ve PyYAML `safe_load`) bu
# anahtari **true / True** olarak COZER; yani `doc["on"]` HICBIR ZAMAN bulunmaz ve
# naif bir okuyucu "bu is akisinin tetikleyicisi YOK" hukmunu verir. O hukum bu depoda
# SESSIZ bir SINIFLAMA HATASIDIR: push ile kosan deploy.yml "BELIRSIZ" sayilirdi ve
# BELIRSIZ kapsam acisindan ELLE gibi ele alindigi icin CI'da fiilen kosan 124 dosya
# birden "kosmuyor" gorunurdu. DUGUM API'sinde anahtarin HAM metni ("on") gorunur ->
# tuzak yapisal olarak ORTADAN KALKAR; tirnakli `"on":` yazimi da AYNI ham metni verir.
# Yine de cagiran taraf ("on" VEYA True — ikisini de kabul et) kuralina uyabilsin diye
# ASAGIDAKI PyYAML kolu BOOLEAN cozumlu anahtari da ayrica kabul eder.
#
# 🔴 IKI KOL AYNI KUMEYI DONDURMEK ZORUNDADIR — ve bu artik FIILEN OLCULUYOR.
# ESKI YORUM YANLISTI: "tuketicideki TETIK_FIKSTURLERI bunu kilitler" deniyordu; KILITLEMIYORDU.
# TETIK_FIKSTURLERI yalniz O ANDA AKTIF olan kolda kosar (PyYAML varsa psych hic cagrilmaz),
# yani iki kol HIC karsilastirilmiyordu. Olculdu (bagimsiz curutucu, 25 girdi): UC ayrisma —
# `on: *t` (alias) psych ELLE / pyyaml OTOMATIK · ayni anchor eslemesi ELLE / OTOMATIK ·
# cok-belgeli `---` psych ELLE / pyyaml BELIRSIZ. Bu tam olarak [[ikiz-tanim-sessiz-ayrisma]]:
# YEREL-KIRMIZI / CI-YESIL uretir. ONARIM: (a) alias anchor tablosundan COZULUR ve cok-belgeli
# girdi IKI KOLDA da fail-closed hata olur, (b) `iki_kol_tetik_sapmasi()` iki kolu FIILEN
# karsilastirir ve tuketicideki nobetci sapmayi KIRMIZI yakar.
RUBY_TETIK_KAYNAK = r"""
require 'yaml'
require 'json'

def capa_topla(node, capalar)
  return if node.nil?
  # 🔴 ALIAS DUGUMU CAPA TABLOSUNA YAZILMAZ: Psych'te Alias da `anchor`'a CEVAP VERIR,
  # ve belge sirasinda alias TANIMDAN SONRA geldigi icin tabloyu EZIYORDU -> `coz()`
  # alias'i yine bir Alias'a cozup vazgeciyordu (olculdu: `on: *t` psych'te None,
  # pyyaml'da {'push'} -> KOL SAPMASI). Yalniz TANIM dugumleri toplanir.
  if !node.is_a?(Psych::Nodes::Alias) &&
     node.respond_to?(:anchor) && node.anchor && !node.anchor.to_s.empty?
    capalar[node.anchor] ||= node
  end
  if node.respond_to?(:children) && node.children
    node.children.each { |c| capa_topla(c, capalar) }
  end
end

def coz(node, capalar)
  # ALIAS COZUMU: PyYAML compose() alias dugumunu anchor'lanan DUGUMUN KENDISIYLE
  # degistirir; psych'te Alias ayri bir dugumdur. Cozmezsek ayni girdide iki kol
  # FARKLI hukum verir (olculdu: `on: *t` -> psych ELLE, pyyaml OTOMATIK).
  # TANIMSIZ ve ILERI alias PyYAML'da ComposerError'dur -> burada da HATA (P4).
  gorulen = 0
  while node.is_a?(Psych::Nodes::Alias) && gorulen < 32
    hedef = capalar[node.anchor]
    if hedef.nil? || hedef.start_line > node.start_line
      raise "TANIMSIZ/ILERI ALIAS: *#{node.anchor}"
    end
    node = hedef
    gorulen += 1
  end
  node
end

def tetik_kumesi(belge, capalar)
  return nil if belge.nil?
  belge = coz(belge.children[0], capalar) if belge.is_a?(Psych::Nodes::Document)
  return nil unless belge.is_a?(Psych::Nodes::Mapping)
  belge.children.each_slice(2) do |k, v|
    next if k.nil? || v.nil?
    next unless k.is_a?(Psych::Nodes::Scalar)
    next unless k.value.to_s.downcase == 'on'
    v = coz(v, capalar)
    if v.is_a?(Psych::Nodes::Scalar)
      return [v.value.to_s.strip]
    elsif v.is_a?(Psych::Nodes::Sequence)
      return v.children.map { |c| coz(c, capalar) }
                       .select { |c| c.is_a?(Psych::Nodes::Scalar) }
                       .map { |c| c.value.to_s.strip }
    elsif v.is_a?(Psych::Nodes::Mapping)
      return v.children.each_slice(2).map { |kk, _vv| kk }
                       .select { |kk| kk.is_a?(Psych::Nodes::Scalar) }
                       .map { |kk| kk.value.to_s.strip }
    end
    return []
  end
  nil
end

girdi = JSON.parse($stdin.read)
sonuc = girdi['metinler'].map do |metin|
  begin
    akis = Psych.parse_stream(metin)
    belgeler = akis.nil? ? [] : akis.children
    if belgeler.size != 1
      # COK BELGELI / BOS girdi -> FAIL-CLOSED. PyYAML `compose()` bu girdide zaten
      # ComposerError atiyor; psych'in ilk belgeyi sessizce okumasi KOL SAPMASIYDI.
      { 'ok' => false,
        'hata' => "TEK BELGE DEGIL (#{belgeler.size} belge) -> fail-closed" }
    else
      capalar = {}
      capa_topla(akis, capalar)
      t = tetik_kumesi(belgeler[0], capalar)
      if t.nil?
        { 'ok' => false, 'hata' => 'TETIKLEYICI YOK: kok esleme degil ya da `on:` anahtari yok' }
      else
        { 'ok' => true, 'tetikler' => t }
      end
    end
  rescue => e
    { 'ok' => false, 'hata' => "#{e.class}: #{e.message}" }
  end
end
print JSON.generate(sonuc)
"""

_PSYCH_SURUM = None

# 🔴 ORTAM DEGISKENI YOK (30 Tem, MIMAR HUKMU — bilincli tasarim karari):
# Bu modul BIR ZAMANLAR `PRUVO_YAML_AYRISTIRICI_YOK` ortam degiskenini okuyordu
# ("olcum kolaylassin" diye). O DUGME KALDIRILDI. Gerekce OLCULDU:
#   * Degisken set edilince tools/ci-kapsam-test.py — BLOKLAYICI bir CI kapisi —
#     SESSIZCE zayif (taklit) kola dusuyordu: rc DEGISMIYOR, kapi KIRMIZI YANMIYOR,
#     yalniz bir bilgi satiri basiliyordu (fail-closed DEGIL, sessiz zayiflama).
#   * deploy.yml'e IS ya da ADIM duzeyinde `env: PRUVO_YAML_AYRISTIRICI_YOK: "1"`
#     eklendiginde DORT kapi da (ci-kapsam ±--kendini-test, is-akisi ±--kendini-test)
#     YESIL kaliyordu — yani CI'ya konabilen, hicbir nobetcinin GORMEDIGI bir dugmeydi.
#   * "Bugun zararsiz oldugu olculdu" bir savunma DEGILDIR: yarin fallback kolu
#     ayristiriciyla ayrisirsa bu dugme sessiz bir KACIS YOLU olur.
# TESTLENEBILIRLIK KAYBOLMADI: fallback kolu ayristiriciyi_kapat() ile ENJEKSIYON
# olarak zorlanir (ortamdan DEGIL, cagiran kodun kendi elinden). Ortam degiskeni bir
# saldirgana/aceleci bir gelistiriciye acik; fonksiyon cagrisi yalniz TESTIN icinde.
_AYRISTIRICI_KAPALI = False


def ayristiriciyi_kapat(kapali=True):
    """YALNIZ TEST/FIKSTUR icin: GERCEK ayristirici kollarini devre disi birak.

    Fallback (taklit) kolunun tek karar mercii oldugu ortami ENJEKSIYONLA kurar;
    ORTAM DEGISKENI YOKTUR (yukaridaki gerekce). Geri almak: ayristiriciyi_kapat(False).
    Onbellekler temizlenir; CAGIRAN tuketicinin kendi onbellegini de temizlemelidir
    (ornegin ci-kapsam-test.py'nin `_MANTIKSAL_ONBELLEK`i)."""
    global _AYRISTIRICI_KAPALI, _PSYCH_SURUM
    _AYRISTIRICI_KAPALI = bool(kapali)
    _PSYCH_SURUM = None
    _ONBELLEK.clear()
    _TETIK_ONBELLEK.clear()
    return _AYRISTIRICI_KAPALI


def _psych_surumu():
    """ruby/psych VAR MI (varsa Psych surumu, yoksa False). Bir kez sorulur."""
    global _PSYCH_SURUM
    if _AYRISTIRICI_KAPALI:
        return False
    if _PSYCH_SURUM is None:
        try:
            r = subprocess.run(["ruby", "-ryaml", "-e", "print Psych::VERSION"],
                               capture_output=True, text=True, timeout=20)
            _PSYCH_SURUM = r.stdout.strip() if r.returncode == 0 else False
        except Exception:
            _PSYCH_SURUM = False
    return _PSYCH_SURUM


def _pyyaml_var():
    if _AYRISTIRICI_KAPALI:
        return False
    return _yaml is not None


def ayristirici_adi():
    """"pyyaml <surum>" | "psych <surum>" | None (hicbir GERCEK ayristirici yok)."""
    if _pyyaml_var():
        return "pyyaml %s" % _yaml.__version__
    s = _psych_surumu()
    if s:
        return "psych %s" % s
    return None


# ---- ORTAK: satir araligi normalizasyonu -----------------------------------
def _normalize(bloklar, metin):
    """[(anahtar, bas, son, deger)] -> temizlenmis liste.

    * ALIAS: alias'in ham satiri, anchor'in araliginin DISINDA kalir -> aralik
      alias satirinin KENDISINE indirgenir (deger COZULMUS haliyle kalir).
    * SONDAKI BOS ham satirlar aralikTAN DUSER (blok disi bos satir bloga girmesin).
    """
    satirlar = metin.splitlines()
    n = len(satirlar)
    temiz = []
    for anahtar, bas, son, deger in bloklar:
        if anahtar < 0 or anahtar >= n:
            continue
        if not (bas <= anahtar <= son):
            bas = son = anahtar          # alias: cozulmus deger, HAM satir alias'inki
        bas = max(bas, anahtar)
        son = max(son, bas)
        son = min(son, n - 1)
        while son > bas and not satirlar[son].strip():
            son -= 1
        temiz.append((anahtar, bas, son, deger))
    temiz.sort(key=lambda t: t[1])
    # Ic ice/ortusen araliklari ELE (fail-closed: belirsiz aralik uretme)
    sonuc = []
    sinir = -1
    for anahtar, bas, son, deger in temiz:
        if bas <= sinir:
            continue
        sonuc.append((anahtar, bas, son, deger))
        sinir = son
    return sonuc


def _bom_sil(metin):
    """🔴 BOM TEK KAYNAKTAN SILINIR (P4 — olculen KOL SAPMASI).

    PyYAML akis basindaki BOM'u (U+FEFF) YUTAR, ruby/psych YUTMAZ: `\\ufeffon: push`
    girdisinde pyyaml {'push'}/OTOMATIK, psych None/BELIRSIZ veriyordu. Tuketici
    duzeyinde olculen sonuc: BOM'lu TEK bir is akisi, psych ortaminda (YEREL) 125
    dosyayi KAPSAMSIZ yapip rc=1 uretirken CI'da (pyyaml) YESIL kaliyordu — yani
    YEREL-KIRMIZI / CI-YESIL. YAML sozlesmesi akis basinda BOM'a IZIN VERIR, dolayisiyla
    DOGRU hukum PyYAML'inkidir; normalizasyon iki kolun ONUNDE, TEK yerde yapilir.
    Satir numaralari DEGISMEZ (BOM ilk satirin basindadir, satir SAYISINI etkilemez)."""
    return metin[1:] if metin[:1] == "﻿" else metin


def _pyyaml_bloklar(metin):
    dugumler = []

    def gez(dugum):
        if isinstance(dugum, _yaml.MappingNode):
            for anahtar, deger in dugum.value:
                if (isinstance(anahtar, _yaml.ScalarNode) and anahtar.value == "run"
                        and isinstance(deger, _yaml.ScalarNode)):
                    son = (deger.end_mark.line - 1 if deger.end_mark.column == 0
                           else deger.end_mark.line)
                    dugumler.append((anahtar.start_mark.line, deger.start_mark.line,
                                     son, deger.value))
                gez(deger)
        elif isinstance(dugum, _yaml.SequenceNode):
            for x in dugum.value:
                gez(x)

    try:
        # 🔴 `compose_all` DEGIL `compose` (P3): compose_all TUM belgeleri gorurdu,
        # psych kolu ise yalniz ILK belgeyi -> ayni girdide farkli blok kumesi.
        # `compose` cok-belgeli girdide ComposerError atar = psych'in "belge != 1"
        # fail-closed dali. Gercek is akislari TEK belgedir; davranis degismez.
        gez(_yaml.compose(metin))
    except Exception as e:
        return None, "AYRISTIRMA HATASI (pyyaml): %s" % e
    return _normalize(dugumler, metin), None


_RUBY_ONBELLEK = {}


def _psych_bloklar_toplu(metinler):
    try:
        r = subprocess.run(["ruby", "-e", RUBY_KAYNAK],
                           input=json.dumps({"metinler": list(metinler)}),
                           capture_output=True, text=True, timeout=120)
    except Exception as e:
        return [(None, "AYRISTIRMA HATASI: ruby/psych cagrilamadi (%s)" % e)
                for _ in metinler]
    if r.returncode != 0:
        return [(None, "AYRISTIRMA HATASI: ruby/psych yardimcisi calismadi (rc=%d) %s"
                 % (r.returncode, r.stderr.strip()[:200])) for _ in metinler]
    try:
        kayitlar = json.loads(r.stdout)
    except Exception as e:
        return [(None, "AYRISTIRMA HATASI: ruby/psych JSON ciktisi cozulemedi (%s)" % e)
                for _ in metinler]
    sonuc = []
    for metin, kayit in zip(metinler, kayitlar):
        if not kayit.get("ok"):
            sonuc.append((None, "AYRISTIRMA HATASI (psych): %s" % kayit.get("hata")))
            continue
        sonuc.append((_normalize([tuple(b) for b in kayit["bloklar"]], metin), None))
    return sonuc


_ONBELLEK = {}


def run_dugumleri(metin):
    """(bloklar, hata) — bloklar = [(anahtar_satir, ilk_ham, son_ham, deger), ...].

    hata None degilse bloklar None'dir. Hicbir ayristirici yoksa
    hata = "AYRISTIRICI YOK" (cagiran fail-closed davranmali; bu dosya TAHMIN URETMEZ).
    Sonuc metne gore onbelleklenir (psych kolu her cagride bir ruby SURECI acar)."""
    metin = _bom_sil(metin)
    if metin in _ONBELLEK:
        return _ONBELLEK[metin]
    if _pyyaml_var():
        sonuc = _pyyaml_bloklar(metin)
    elif _psych_surumu():
        sonuc = _psych_bloklar_toplu([metin])[0]
    else:
        sonuc = (None, "AYRISTIRICI YOK")
    if len(_ONBELLEK) > 512:
        _ONBELLEK.clear()
    _ONBELLEK[metin] = sonuc
    return sonuc


def onbellegi_isit(metinler):
    """psych kolunda TOPLU ayristirma (tek ruby sureci) — cok fiksturlu nobetler icin."""
    if _pyyaml_var() or not _psych_surumu():
        return
    kalan = [m for m in metinler if m not in _ONBELLEK]
    if not kalan:
        return
    for metin, sonuc in zip(kalan, _psych_bloklar_toplu(kalan)):
        if len(_ONBELLEK) > 512:
            _ONBELLEK.clear()
        _ONBELLEK[metin] = sonuc


# ---- TETIKLEYICILER (`on:`) — is akisinin OTOMATIK mi ELLE mi oldugu -------
# NEDEN BURADA (KATMAN 0): tuketici (tools/ci-kapsam-test.py) "bu dosya CI'da GERCEKTEN
# kosuyor mu" sorusunu cevaplarken ELLE tetiklenen (`workflow_dispatch` disinda hicbir
# tetigi olmayan) bir is akisindaki cagriyi KAPSAM SAYMAMALIDIR. O ayrimin dayanagi
# `on:` bloguDUR ve METIN TAKLIDIYLE okunamaz: uc ayri yazim (skalar / dizi / esleme) +
# YAML 1.1 boolean tuzagi + tirnak/anchor kurallari ayristiricinin isidir
# ([[mimar-kapi-parser-taklidi]]). Kol sirasi run_dugumleri() ile AYNI: PyYAML -> psych.
_TETIK_ONBELLEK = {}


# GERCEK bir GitHub olay adinin yazim sekli. `on:` altinda bundan BASKA bir jeton
# (bos dize, YAML merge anahtari `<<`, noktalama) GitHub icin ANLAMSIZDIR.
_OLAY_ADI = __import__("re").compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _tetik_normalize(ham):
    """(kume, hata) — HAM tetik jetonlarini TEK KAYNAKTAN suz (IKI KOL da bunu cagirir).

    🔴 BOS/ANLAMSIZ TETIK KUMESI **BELIRSIZ**'DIR, "OTOMATIK" DEGIL (fail-closed).
    OLCULEN SAHTE-YESIL (bagimsiz curutucu): tetikleri YORUMA ALINMIS bir is akisi
    (`on:` altinda yalniz `# push:`) tetik kumesi olarak {''} veriyordu; '' hicbir
    ELLE tetigi olmadigi icin tuketici onu **OTOMATIK** sayiyordu. GitHub oyle bir
    is akisini HIC KOSTURMAZ -> o akista "kosuyor" gorunen her dosya sessizce
    kapsanmis sayilirdi. Ayni sinif: `on: ''`, `on:\\n  <<: *t` (merge anahtari ->
    ['<<']), ve genel olarak "ayristirici BASARILI ama kume BOS/anlamsiz".
    Bu yonde BELIRSIZ yalniz KAPSAMI DARALTIR (uyari satiri basilir, exit'i etkilemez)."""
    temiz = {str(t).strip() for t in (ham or [])}
    gecerli = {t for t in temiz if _OLAY_ADI.match(t)}
    if not gecerli:
        return None, ("TETIKLEYICI ANLAMSIZ: `on:` cozuldu ama gecerli olay adi YOK "
                      "(ham=%r) -> tetikleri yoruma alinmis / bos / merge-anahtarli "
                      "is akisi; GitHub bunu HIC kosturmaz (fail-closed BELIRSIZ)"
                      % (sorted(temiz),))
    return gecerli, None


def _pyyaml_tetikler(metin):
    """(kume, hata) — PyYAML DUGUM (compose) kolu.

    🔴 `safe_load` KULLANILMAZ: YAML 1.1'de ciplak `on` BOOLEAN'a cozulur ve sozlukte
    anahtar `True` olur. Dugum API'sinde ham metin ("on") korunur. Yine de sozlesme
    geregi ("on" VEYA True kabul edilmeli) BOOLEAN cozumu de kabul edilir: bir anahtar
    dugumunun etiketi bool ise degeri `_bool_on()` ile sinanir.

    NOT: `compose()` COK BELGELI girdide ComposerError atar -> BELIRSIZ. psych kolu da
    artik ayni yerde fail-closed (belge sayisi != 1); bu bilincli KOL PARITESIDIR."""
    try:
        kok = _yaml.compose(metin)
    except Exception as e:
        return None, "AYRISTIRMA HATASI (pyyaml): %s" % e
    if not isinstance(kok, _yaml.MappingNode):
        return None, "TETIKLEYICI YOK: kok bir YAML eslemesi degil"
    for anahtar, deger in kok.value:
        if not isinstance(anahtar, _yaml.ScalarNode):
            continue
        if not _on_anahtari(anahtar.value):
            continue
        if isinstance(deger, _yaml.ScalarNode):
            return _tetik_normalize([deger.value])
        if isinstance(deger, _yaml.SequenceNode):
            return _tetik_normalize([d.value for d in deger.value
                                     if isinstance(d, _yaml.ScalarNode)])
        if isinstance(deger, _yaml.MappingNode):
            return _tetik_normalize([k.value for k, _v in deger.value
                                     if isinstance(k, _yaml.ScalarNode)])
        return _tetik_normalize([])
    return None, "TETIKLEYICI YOK: `on:` anahtari yok"


def _on_anahtari(ham):
    """<ham> anahtar metni `on:` mi? YAML 1.1'de `on`/`On`/`ON` boolean'dir; dugum
    API'sinde HAM metin gorunur, `Psych.load`/`safe_load` kolunda `True` gelirdi.
    Ikisi de kabul edilir (SPEC: anahtar `"on"` VEYA `True` olabilir)."""
    if ham is True:
        return True
    return isinstance(ham, str) and ham.strip().lower() == "on"


def _psych_tetikler_toplu(metinler):
    try:
        r = subprocess.run(["ruby", "-e", RUBY_TETIK_KAYNAK],
                           input=json.dumps({"metinler": list(metinler)}),
                           capture_output=True, text=True, timeout=120)
    except Exception as e:
        return [(None, "AYRISTIRMA HATASI: ruby/psych cagrilamadi (%s)" % e)
                for _ in metinler]
    if r.returncode != 0:
        return [(None, "AYRISTIRMA HATASI: ruby/psych tetik yardimcisi calismadi "
                 "(rc=%d) %s" % (r.returncode, r.stderr.strip()[:200]))
                for _ in metinler]
    try:
        kayitlar = json.loads(r.stdout)
    except Exception as e:
        return [(None, "AYRISTIRMA HATASI: ruby/psych JSON tetik ciktisi cozulemedi (%s)"
                 % e) for _ in metinler]
    sonuc = []
    for kayit in kayitlar:
        if not kayit.get("ok"):
            sonuc.append((None, "%s" % kayit.get("hata")))
            continue
        # AYNI normalize govdesi (TEK KAYNAK) — kol ayrismasinin yasadigi yer burasiydi.
        sonuc.append(_tetik_normalize(kayit["tetikler"]))
    return sonuc


def tetikleyiciler(metin):
    """(tetik_kumesi, hata) — is akisi metnindeki TOP-LEVEL `on:` tetikleyici adlari.

    Uc yazim da desteklenir:
        on: push                          -> {"push"}
        on: [push, workflow_dispatch]     -> {"push", "workflow_dispatch"}
        on:\\n  schedule:\\n    - cron: ...  -> {"schedule"}
    hata None degilse kume None'dir. Hicbir GERCEK ayristirici yoksa
    hata = "AYRISTIRICI YOK" -> CAGIRAN FAIL-CLOSED davranmak ZORUNDADIR (bu depoda:
    sinif "BELIRSIZ", ve BELIRSIZ kapsam acisindan ELLE gibi ele alinir)."""
    metin = _bom_sil(metin)
    if metin in _TETIK_ONBELLEK:
        return _TETIK_ONBELLEK[metin]
    if _pyyaml_var():
        sonuc = _pyyaml_tetikler(metin)
    elif _psych_surumu():
        sonuc = _psych_tetikler_toplu([metin])[0]
    else:
        sonuc = (None, "AYRISTIRICI YOK")
    if len(_TETIK_ONBELLEK) > 512:
        _TETIK_ONBELLEK.clear()
    _TETIK_ONBELLEK[metin] = sonuc
    return sonuc


def kollar_mevcut():
    """(pyyaml_var, psych_var) — hangi GERCEK kol bu ortamda OLCULEBILIR."""
    return (_yaml is not None and not _AYRISTIRICI_KAPALI, bool(_psych_surumu()))


def iki_kol_tetik_sapmasi(metinler):
    """(sapmalar, olculen_kol) — IKI KOLU FIILEN KARSILASTIR (O3b nobetcisinin govdesi).

    sapmalar = [(indeks, pyyaml_hukmu, psych_hukmu), ...]; hukum = tetik kumesi (set)
    ya da None (= BELIRSIZ). HATA METINLERI KIYASLANMAZ, yalniz HUKUM: tuketicinin
    sinifi (OTOMATIK/ELLE/BELIRSIZ) yalniz kumeden turer.

    olculen_kol = kac GERCEK kol olculebildi (2 degilse karsilastirma YAPILAMADI —
    cagiran bunu GORUNUR bir OLCULEMEDI satiri olarak basmak ZORUNDADIR; sessiz
    'sapma yok' saymak bu nobetciyi olu yapar)."""
    pyyaml_var, psych_var = kollar_mevcut()
    if not (pyyaml_var and psych_var):
        return [], (1 if (pyyaml_var or psych_var) else 0)
    metinler = [_bom_sil(m) for m in metinler]
    psych = _psych_tetikler_toplu(metinler)
    sapmalar = []
    for i, metin in enumerate(metinler):
        p_kume, _p_hata = _pyyaml_tetikler(metin)
        r_kume, _r_hata = psych[i]
        if p_kume != r_kume:
            sapmalar.append((i, p_kume, r_kume))
    return sapmalar, 2


def iki_kol_run_sapmasi(metinler):
    """(sapmalar, olculen_kol) — `run:` KOLUNUN iki-kol paritesi (P3).

    🔴 NEDEN AYRI BIR NOBETCI: `KATLAMA_FIKSTURLERI` TAKLIT ile GERCEK ayristiriciyi
    karsilastirir, pyyaml ile psych'i DEGIL. O bosluk yuzunden `RUBY_KAYNAK`'taki Alias
    korumasini geri saran mutant IKI ORTAMDA DA rc=0 YESIL kaliyordu — yani `run:`
    kolunun ikiz tanimi TAMAMEN NOBETSIZDI. Olculdu (curutucu, 12 girdi): 4 yapisal
    ayrisma (ileri alias · tanimsiz alias · cok-belgeli · `---\\n---\\njobs:`).

    Hukum = blok listesi (anahtar_satir, ilk_ham, son_ham, deger) ya da None (= HATA).
    Hata METINLERI kiyaslanmaz; tuketici zaten yalniz bloklara/None'a bakar."""
    pyyaml_var, psych_var = kollar_mevcut()
    if not (pyyaml_var and psych_var):
        return [], (1 if (pyyaml_var or psych_var) else 0)
    metinler = [_bom_sil(m) for m in metinler]
    psych = _psych_bloklar_toplu(metinler)
    sapmalar = []
    for i, metin in enumerate(metinler):
        p_blok, _p_hata = _pyyaml_bloklar(metin)
        r_blok, _r_hata = psych[i]
        if p_blok != r_blok:
            sapmalar.append((i, p_blok, r_blok))
    return sapmalar, 2


def tetik_onbellegi_isit(metinler):
    """psych kolunda TOPLU tetik ayristirmasi (tek ruby sureci) — fikstur kumeleri icin."""
    if _pyyaml_var() or not _psych_surumu():
        return
    kalan = [m for m in metinler if m not in _TETIK_ONBELLEK]
    if not kalan:
        return
    for metin, sonuc in zip(kalan, _psych_tetikler_toplu(kalan)):
        if len(_TETIK_ONBELLEK) > 512:
            _TETIK_ONBELLEK.clear()
        _TETIK_ONBELLEK[metin] = sonuc


if __name__ == "__main__":  # kucuk teshis kolu (kapi DEGIL)
    import sys
    print("ayristirici: %s" % (ayristirici_adi() or "YOK"))
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            bloklar, hata = run_dugumleri(f.read())
        if hata:
            print("hata: %s" % hata)
        else:
            for anahtar, bas, son, deger in bloklar:
                print("  run@%d ham[%d..%d] %r" % (anahtar, bas, son, deger[:80]))
