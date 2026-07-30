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
  if node.respond_to?(:anchor) && node.anchor && !node.anchor.to_s.empty?
    capalar[node.anchor] = node
  end
  if node.respond_to?(:children) && node.children
    node.children.each { |c| capa_topla(c, capalar) }
  end
end

def gez(node, capalar, out)
  return if node.nil?
  if node.is_a?(Psych::Nodes::Mapping)
    node.children.each_slice(2) do |k, v|
      next if v.nil?
      if k.is_a?(Psych::Nodes::Scalar) && k.value == 'run'
        hedef = v.is_a?(Psych::Nodes::Alias) ? capalar[v.anchor] : v
        if hedef.is_a?(Psych::Nodes::Scalar)
          son = hedef.end_column == 0 ? hedef.end_line - 1 : hedef.end_line
          out << [k.start_line, hedef.start_line, son, hedef.value]
        end
      end
      gez(v, capalar, out)
    end
  elsif node.respond_to?(:children) && node.children
    node.children.each { |c| gez(c, capalar, out) }
  end
end

girdi = JSON.parse($stdin.read)
sonuc = girdi['metinler'].map do |metin|
  begin
    kok = Psych.parse(metin)
    capalar = {}
    capa_topla(kok, capalar)
    out = []
    gez(kok, capalar, out)
    { 'ok' => true, 'bloklar' => out }
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
        for kok in _yaml.compose_all(metin):
            gez(kok)
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
