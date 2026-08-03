#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI — MARKA-MODEL SAYFASI ile ANA SAYFA FİLTRESİ AYNI ÜRÜNLERİ GÖSTERİYOR MU?

  python3 tools/model-uyelik-kapisi.py                 # kabul (sayı basar, eşik uygular)
  python3 tools/model-uyelik-kapisi.py --dokum         # sapan her çifti tek tek listele
  python3 tools/model-uyelik-kapisi.py --kendini-test  # mutasyon bataryası (öldürücü+kontrol)
  python3 tools/model-uyelik-kapisi.py --kok /yol      # BAŞKA ağaçtan oku (mutasyon için)

NE ÖLÇER: her yayımlanan /marka/<marka>/<model>/ sayfası için
    SAYFA  = jeneratörün (tools/marka_model_build.py) o sayfaya koyduğu ürünler
    FİLTRE = index.html'in ?marka=<marka>&model=<display> ile göstereceği ürünler
ve şunu basar:
    CIFT=N TEMIZ=N SAYFA_DAR=N FILTRE_DAR=N ETKILENEN_URUN=N
  SAYFA_DAR  : filtre gösteriyor, sayfada YOK (müşteri sayfada parçayı bulamaz)
  FILTRE_DAR : sayfa gösteriyor, filtre bulamıyor (çipe/deep-link'e tıklayan kaybeder)
  CAPRAZ     : iki yönde birden sapan çift (ayrı sayılır, TEMIZ'e karışmaz)
KABUL EŞİĞİ: SAYFA_DAR=0 · FILTRE_DAR=0 · CAPRAZ=0.

🔴 FİLTRE TARAFI YENİDEN YAZILMAZ: index.html'in GERÇEK kodu (norm + MARKA KÜRATÖRLÜĞÜ +
KANONİK MODEL EŞLEMESİ blokları) AYIKLANIP node ile koşturulur. Python'da bir "filtre portu"
yazsaydık kapı, üretimi değil kendi varsayımını aynalardı — ve iki gövde ayrıştığında yeşil
yanardı ([[ikiz-tanim-sessiz-ayrisma]], [[nobetci-fikstur-sekli]]).

FAIL-CLOSED: node yoksa, blok ayıklanamazsa, katalog boşsa ya da harness çökerse SONUC
OLCULEMEDI (çıkış 2) — "sapma bulamadım" diye YEŞİL denmez.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

DIR = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(DIR)


# ---------------------------------------------------------------- yardımcı
def _modul(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


def _bagimsiz_kanon(s):
    """YANLIŞ-POZİTİF ekseni için BAĞIMSIZ normalleştirme (spec §4.4).

    Bilerek model_kanon'dan FARKLI yazılmıştır: aksan çözümü unicodedata ile yapılır ve
    alfanümerik DIŞI her şey atılır. Amaç, "yeni giren ürün gerçekten o modelin parçası mı"
    sorusunu ölçülen kuralın KENDİSİYLE cevaplamamak — aynı fonksiyon iki tarafta da
    kullanılsaydı iddia totoloji olurdu."""
    t = unicodedata.normalize("NFKD", (s or "").replace("ı", "i").replace("İ", "i").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", t)


# ---------------------------------------------------------------- node koşumu (FİLTRE tarafı)
HARNESS = r"""
"use strict";
/* index.html'den AYIKLANMIS GERCEK kod (kopya DEGIL) */
__NORM__
__KURATORLUK__
__MODEL_KANON__

const girdi = JSON.parse(require("fs").readFileSync(process.argv[2], "utf8"));
const urunler = girdi.urunler;          // [{i, m:[ham marka...]}]
const ciftler = girdi.ciftler;          // [[marka, display], ...]

/* marka -> o markanin UYESI urun indeksleri (filtered() brandOk yuklemi) */
const markaIx = new Map();
for (const u of urunler) {
  const gorulen = new Set();
  for (const b of u.m) {
    const k = markaKatla(b);
    if (gorulen.has(k)) { continue; }
    gorulen.add(k);
    if (!markaIx.has(k)) { markaIx.set(k, []); }
    markaIx.get(k).push(u);
  }
}

const cikti = {};
for (const [marka, display] of ciftler) {
  const liste = markaIx.get(marka) || [];
  const ids = [];
  for (const u of liste) {
    /* filtered() model yuklemi — GERCEK modelEsler cagrilir */
    if (modelEsler(u.m, display, marka)) { ids.push(u.i); }
  }
  cikti[marka + "\t" + display] = ids;
}
process.stdout.write(JSON.stringify({ok: true, sonuc: cikti,
  anahtarOrnek: {f150: modelAnahtar("Ford", "F150"), fSerisi: modelAnahtar("Ford", "F-Series")}}));
"""


class Olculemedi(Exception):
    pass


def _blok_ayikla(index_html):
    """index.html'den GERÇEK JS parçaları (fail-closed)."""
    m = re.search(r"function norm\(s\)\{[\s\S]*?\n  \}", index_html)
    if not m:
        raise Olculemedi("index.html norm() ayıklanamadı")
    norm_src = m.group(0)

    def arasi(bas, son, ad):
        b, s = index_html.find(bas), index_html.find(son)
        if b == -1 or s == -1 or s <= b:
            raise Olculemedi("index.html %s bloğu ayıklanamadı (marker yok/taşınmış)" % ad)
        return index_html[index_html.index("\n", b) + 1:s]

    kurator = arasi("// --- MARKA KÜRATÖRLÜĞÜ BAŞ", "// --- MARKA KÜRATÖRLÜĞÜ SON ---",
                    "MARKA KÜRATÖRLÜĞÜ")
    kanon = arasi("// --- KANONİK MODEL EŞLEMESİ BAŞ", "// --- KANONİK MODEL EŞLEMESİ SON ---",
                  "KANONİK MODEL EŞLEMESİ")
    for imza in ("function modelKanon", "function modelOnekSiyir", "function modelAnahtar",
                 "function modelEsler", "MODEL_ALIAS"):
        if imza not in kanon:
            raise Olculemedi("KANONİK MODEL EŞLEMESİ bloğunda %s YOK" % imza)
    if "MARKA_ALIAS" not in kurator:
        raise Olculemedi("MARKA KÜRATÖRLÜĞÜ bloğunda MARKA_ALIAS YOK")
    return norm_src, kurator, kanon


def filtre_kumeleri(index_html, urunler, ciftler):
    """{(marka, display): set(urun_id)} — index.html'in GERÇEK yüklemiyle (node)."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        raise Olculemedi("node bulunamadı — filtre tarafı GERÇEK kodla koşturulamaz "
                         "(Python portu yazmak kapıyı totolojiye çevirirdi)")
    norm_src, kurator, kanon = _blok_ayikla(index_html)
    js = (HARNESS.replace("__NORM__", norm_src)
                 .replace("__KURATORLUK__", kurator)
                 .replace("__MODEL_KANON__", kanon))
    tmp = tempfile.mkdtemp(prefix="model-uyelik-node-")
    try:
        jsyol = os.path.join(tmp, "kosum.js")
        veriyol = os.path.join(tmp, "girdi.json")
        with open(jsyol, "w", encoding="utf-8") as f:
            f.write(js)
        with open(veriyol, "w", encoding="utf-8") as f:
            json.dump({"urunler": [{"i": p.get("id"),
                                    "m": [(x or "").strip()
                                          for x in (p.get("marka") or []) if (x or "").strip()]}
                                   for p in urunler if p.get("id")],
                       "ciftler": [[a, b] for a, b in ciftler]}, f, ensure_ascii=False)
        p = subprocess.run(["node", jsyol, veriyol], capture_output=True, text=True, timeout=900)
        if p.returncode != 0 or not (p.stdout or "").strip():
            raise Olculemedi("node koşumu çöktü (rc=%d): %s"
                             % (p.returncode, ((p.stderr or "").strip().splitlines() or [""])[-1][:200]))
        veri = json.loads(p.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not veri.get("ok"):
        raise Olculemedi("node koşumu ok=false döndü")
    return dict(((k.split("\t")[0], k.split("\t")[1]), set(v))
                for k, v in veri["sonuc"].items()), veri.get("anahtarOrnek", {})


# ---------------------------------------------------------------- ölçüm
def olc(kok, modul_yolu=None):
    """(satir, ayrinti) — hüküm VERMEZ, sayı üretir."""
    araclar = os.path.join(kok, "tools")
    if araclar not in sys.path:
        sys.path.insert(0, araclar)
    mm = _modul(modul_yolu or os.path.join(araclar, "marka_model_build.py"), "mm_model_kapisi")
    try:
        with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
    except Exception as e:                                        # noqa: BLE001
        raise Olculemedi("katalog/index.html okunamadı: %r" % (e,))
    if not urunler:
        raise Olculemedi("urunler.json BOŞ — üyelik ölçülemez")

    try:
        evren = mm.MarkaEvreni(index_html)
        ek = mm.cip_evreni_markalari(urunler, index_html)
        veri = mm.gruplandir(urunler, evren, ek)
    except SystemExit as e:                                       # noqa: BLE001
        raise Olculemedi("jeneratör fail-closed durdu: %r" % (e,))
    if not veri:
        raise Olculemedi("jeneratör HİÇ marka kovası üretmedi")

    # yayımlanan çiftler (üreticinin TEK KAYNAK yüklemi)
    yayimla = getattr(mm, "yayimlanir_mi", None)
    if yayimla is None:
        raise Olculemedi("jeneratörde yayimlanir_mi() YOK — sayfa evreni ölçülemez")
    ciftler, sayfa = [], {}
    for marka, d in veri.items():
        for g in d["gruplar"].values():
            if not yayimla(g):
                continue
            ciftler.append((marka, g["display"]))
            sayfa[(marka, g["display"])] = (
                set(p.get("id") for p in g["urunler"] if p.get("id")), g["canon"])
    if not ciftler:
        raise Olculemedi("yayımlanan model sayfası YOK — parite ölçülemez (fail-closed)")

    filtre, ornek = filtre_kumeleri(index_html, urunler, ciftler)

    urun_ix = dict((p["id"], p) for p in urunler if p.get("id"))
    temiz = sayfa_dar = filtre_dar = capraz = 0
    etkilenen = set()
    dokum = []
    for cift in ciftler:
        s, canon = sayfa[cift]
        f = filtre.get(cift, set())
        eksik_sayfada, eksik_filtrede = f - s, s - f
        if not eksik_sayfada and not eksik_filtrede:
            temiz += 1
            continue
        etkilenen |= eksik_sayfada | eksik_filtrede
        if eksik_sayfada and eksik_filtrede:
            capraz += 1
            tur = "CAPRAZ"
        elif eksik_sayfada:
            sayfa_dar += 1
            tur = "SAYFA_DAR"
        else:
            filtre_dar += 1
            tur = "FILTRE_DAR"
        dokum.append({"tur": tur, "marka": cift[0], "model": cift[1], "canon": canon,
                      "sayfa": len(s), "filtre": len(f),
                      "sayfada_yok": sorted(eksik_sayfada)[:5],
                      "filtrede_yok": sorted(eksik_filtrede)[:5]})

    # --- YANLIŞ-POZİTİF EKSENİ (spec §4.4): sayfaya giren HER ürün o modeli GERÇEKTEN taşıyor mu?
    # Kural: ürünün `marka` dizisinde ya da `uyum[].model`'inde, sayfanın adıyla BAĞIMSIZ
    # normalleştirme altında eşleşen bir jeton bulunmalı. Eşleşmeyen tek istisna sınıfı,
    # KÜRATÖRLÜ semantik alias'tır (MODEL_ALIAS: "F-Series" = "F-Serisi") — o da sessizce
    # muaf tutulmaz, alias KAYNAĞINDAN türetilir ve raporda AYRI listelenir.
    alias_kaynaklari = {}
    for (mk, kaynak), hedef_canon in (evren.model_alias or {}).items():
        alias_kaynaklari.setdefault((mk, hedef_canon), set()).add(kaynak)
    sahte, alias_aciklamali = [], []

    def _tasiyor(jetonlar, hedef):
        # marka öneki taşıyan yazım da sayılır ("peugeot206" -> "206")
        return bool(hedef) and (hedef in jetonlar
                                or any(j.endswith(hedef) and j != hedef for j in jetonlar))

    for (marka, display), (ids, canon) in sayfa.items():
        hedef = _bagimsiz_kanon(display)
        aliaslar = alias_kaynaklari.get((marka, canon), set())
        for pid in ids:
            p = urun_ix.get(pid) or {}
            jetonlar = set(_bagimsiz_kanon(x) for x in (p.get("marka") or []) if x)
            jetonlar |= set(_bagimsiz_kanon(o.get("model"))
                            for o in (p.get("uyum") or []) if (o.get("model") or "").strip())
            if _tasiyor(jetonlar, hedef):
                continue
            if any(_tasiyor(jetonlar, _bagimsiz_kanon(a)) for a in aliaslar):
                alias_aciklamali.append((marka, display, pid, sorted(aliaslar)))
                continue
            sahte.append((marka, display, pid, sorted(jetonlar)[:4]))

    # --- DISPLAY SORGULANABİLİR Mİ: sayfanın adı kendi kovasının anahtarına dönmeli
    #     (dönmezse o sayfa için ?model=<display> HİÇBİR ZAMAN doğru küme getirmez).
    sorgulanamaz = []
    for (marka, display), (_ids, canon) in sayfa.items():
        if evren.model_anahtari(marka, display) != canon:
            sorgulanamaz.append((marka, display, canon,
                                 evren.model_anahtari(marka, display)))

    satir = ("CIFT=%d TEMIZ=%d SAYFA_DAR=%d FILTRE_DAR=%d ETKILENEN_URUN=%d"
             % (len(ciftler), temiz, sayfa_dar, filtre_dar, len(etkilenen)))
    return satir, {"cift": len(ciftler), "temiz": temiz, "sayfa_dar": sayfa_dar,
                   "filtre_dar": filtre_dar, "capraz": capraz,
                   "etkilenen": len(etkilenen), "dokum": dokum, "sahte": sahte,
                   "alias_aciklamali": alias_aciklamali,
                   "sorgulanamaz": sorgulanamaz, "marka_sayisi": len(veri),
                   "anahtar_ornek": ornek}


# ---------------------------------------------------------------- kabul
def kabul(kok, dokum=False, modul_yolu=None):
    kaldi, gecen = [], []

    def dogrula(ad, kosul, detay=""):
        (gecen if kosul else kaldi).append(ad)
        print("  %s %s%s" % ("GECTI" if kosul else "KALDI", ad, (" — " + detay) if detay else ""))

    satir, a = olc(kok, modul_yolu)
    print("  " + satir + "  (CAPRAZ=%d · marka kovası=%d)" % (a["capraz"], a["marka_sayisi"]))
    print("  KANON ORNEK: modelAnahtar(Ford,'F150')=%s · modelAnahtar(Ford,'F-Series')=%s"
          % (a["anahtar_ornek"].get("f150"), a["anahtar_ornek"].get("fSerisi")))

    dogrula("K0 FAIL-CLOSED: ÖLÇÜLEN ÇİFT VAR", a["cift"] > 0,
            "cift=%d (0 çift 'sapma yok' diye YEŞİL geçemez)" % a["cift"])
    dogrula("K1 SAYFA_DAR=0 (filtrenin gösterdiği her ürün sayfada VAR)", a["sayfa_dar"] == 0,
            "sayfa_dar=%d" % a["sayfa_dar"])
    dogrula("K2 FILTRE_DAR=0 (sayfanın gösterdiği her ürünü filtre BULUR)", a["filtre_dar"] == 0,
            "filtre_dar=%d" % a["filtre_dar"])
    dogrula("K3 CAPRAZ=0 (iki yönde birden sapan çift YOK)", a["capraz"] == 0,
            "capraz=%d" % a["capraz"])
    dogrula("K4 YANLIŞ-POZİTİF YOK: sayfaya giren her ürün o model jetonunu GERÇEKTEN taşıyor",
            not a["sahte"], "sahte=%d %s" % (len(a["sahte"]), a["sahte"][:4]))
    if a["alias_aciklamali"]:
        print("  BILGI KÜRATÖRLÜ ALIAS ile açıklanan üyelik: %d ürün (muafiyet listesi DEĞİL, "
              "MODEL_ALIAS tablosundan türer) örnek: %s"
              % (len(a["alias_aciklamali"]), a["alias_aciklamali"][:2]))
    dogrula("K5 HER SAYFA KENDİ ADIYLA SORGULANABİLİR (display -> kova anahtarı)",
            not a["sorgulanamaz"],
            "sorgulanamaz=%d %s" % (len(a["sorgulanamaz"]), a["sorgulanamaz"][:3]))
    # KONTROL: kapı gerçekten AYRIŞMA ölçüyor mu — ölçülen küme boş/dejenere olmasın.
    dogrula("K6 KONTROL: ölçülen çiftlerin çoğu DOLU (dejenere ölçüm değil)",
            a["temiz"] + a["sayfa_dar"] + a["filtre_dar"] + a["capraz"] == a["cift"]
            and a["cift"] >= 50,
            "temiz=%d cift=%d" % (a["temiz"], a["cift"]))

    if dokum and a["dokum"]:
        print("\n  SAPAN ÇİFTLER (%d):" % len(a["dokum"]))
        for x in a["dokum"]:
            print("    %-10s %s / %s (canon=%s) sayfa=%d filtre=%d | sayfada yok: %s | filtrede yok: %s"
                  % (x["tur"], x["marka"], x["model"], x["canon"], x["sayfa"], x["filtre"],
                     x["sayfada_yok"], x["filtrede_yok"]))

    toplam = len(gecen) + len(kaldi)
    if kaldi:
        print("\nSONUC: %d/%d iddia KALDI ❌" % (len(kaldi), toplam))
        return 1
    print("\nSONUC: %d/%d iddia GECTI ✔" % (toplam, toplam))
    return 0


# ---------------------------------------------------------------- mutasyon
# (dosya, eski, yeni, beklenen, açıklama)
MUTANTLAR = [
    # --- ÖLDÜRÜCÜ ---
    ("tools/marka_model_build.py",
     "    for x in marka_dizisi:\n        t = (x or \"\").strip()",
     "    for x in marka_dizisi[1:2]:\n        t = (x or \"\").strip()", "KIRMIZI",
     "M1 ÜYELİĞİ marka[1]'E GERİ SABİTLE (ölçülen eski hata) -> sayfa filtreden daralır"),
    ("tools/marka_model_build.py",
     "    return model_kanon.onek_siyir(marka, model_ham, evren)",
     "    return (model_ham or \"\").strip()", "KIRMIZI",
     "M2 MARKA ÖNEKİNİ SIYIRMA: 'Peugeot 206' ayrı kovaya düşer -> sayfa/filtre ayrışır"),
    ("index.html",
     "    if(mk.indexOf(model) !== -1){ return true; }       // BUGÜNKÜ ham eşitlik — asla daralma\n"
     "    var hedef = modelAnahtar(hedefMarka, model);",
     "    return mk.indexOf(model) !== -1;\n"
     "    var hedef = modelAnahtar(hedefMarka, model);", "KIRMIZI",
     "M3 FİLTREYİ HAM EŞİTLİĞE DÖNDÜR (ölçülen eski hata) -> 'F150' vs 'F-150' ayrışır"),
    # 🔴 M4/M5/M7 KUPLAJI KIRAR, DEĞERİ DEĞİL: tabloyu index.html'de değiştiren mutant iki
    # tarafı BİRDEN kaydırdığı için parite bozulmaz (tek kaynağın tam olarak istenen etkisi;
    # ölçüldü — MARKA_ALIAS'ı index.html'den silmek CIFT'i 504->505 yapar ama TEMIZ kalır).
    # Ayrışmayı doğuran şey, BİR tarafın kaynağı okumayı bırakmasıdır; öldürücü mutant onu
    # taklit eder ([[beyan-edilmis-survivor]]: iddia ancak tek başına kırmızı yakılabiliyorsa kanıttır).
    ("tools/model_kanon.py", '    marka = _obje_ayikla(index_html, "MARKA_ALIAS")',
     "    marka = {}", "KIRMIZI",
     "M4 PYTHON TARAFI MARKA ALIAS'INI OKUMAYI BIRAKIR -> sayfa Vauxhall'ı ayırır, filtre katlar"),
    ("tools/model_kanon.py", "    return marka, model", "    return marka, {}", "KIRMIZI",
     "M5 PYTHON TARAFI MODEL ALIAS'INI OKUMAYI BIRAKIR -> F-Series/F-Serisi kovası ikiye bölünür"),
    ("tools/model_kanon.py", '    return _AYIRAC.sub("", t)', "    return t", "KIRMIZI",
     "M7 PYTHON KANONU AYIRAÇ ATMAYI BIRAKIR -> 'F-150'/'F150' sayfada ayrışır, filtrede birleşik"),
    ("index.html", 'return t.replace(/[\\s\\-\\._\\/]/g, "");', "return t;", "KIRMIZI",
     "M6 KANON AYIRAÇ ATMAYI KALDIR -> JS anahtarı Python anahtarından ayrışır"),
    # --- KONTROL (YEŞİL bekleniyor) ---
    ("tools/marka_model_build.py", "ESIK = 3", "ESIK = 4", "YESIL",
     "K1 İLGİSİZ: eşiği yükseltmek çift SAYISINI düşürür, PARİTEYİ bozmaz"),
    ("tools/cip-indeks.py", "SURUM = 1", "SURUM = 2", "YESIL",
     "K2 İLGİSİZ: indeks sürüm alanı model üyeliğinde rol OYNAMAZ"),
    ("index.html", 'var MODEL_TR = {"ı":"i"', 'var MODEL_TR = {"Û":"u","ı":"i"', "YESIL",
     "K3 İLGİSİZ: küçültmeden SONRA hiç görülmeyen büyük harf girdisi davranışı DEĞİŞTİRMEZ"),
]


def _kok_kur(tmp):
    """tools/ + index.html KOPYALANIR (mutant oraya uygulanır), gerisi SYMLINK."""
    os.makedirs(os.path.join(tmp, "tools"))
    for ad in os.listdir(os.path.join(GERCEK_KOK, "tools")):
        k = os.path.join(GERCEK_KOK, "tools", ad)
        if os.path.isfile(k):
            shutil.copy2(k, os.path.join(tmp, "tools", ad))
    shutil.copy2(os.path.join(GERCEK_KOK, "index.html"), os.path.join(tmp, "index.html"))
    for ad in os.listdir(GERCEK_KOK):
        if ad in ("tools", "index.html", ".git"):
            continue
        os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))


def kendini_test():
    print("MUTASYON — model üyeliği (mutant KOPYAYA uygulanır; gerçek ağaç DEĞİŞMEZ)")
    basarisiz, olcum = [], []
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = tempfile.mkdtemp(prefix="model-uyelik-mut-")
        try:
            _kok_kur(tmp)
            yol = os.path.join(tmp, *dosya.split("/"))
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            if eski not in metin:
                print("  HATA M%02d: mutant ÇAPASI BULUNAMADI (%s) -> %s" % (i, dosya, aciklama))
                basarisiz.append("M%02d capa yok" % i)
                continue
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, os.path.join(tmp, "tools", "model-uyelik-kapisi.py"),
                                "--kok", tmp], capture_output=True, text=True, timeout=1800)
            kirmizi = [s for s in (p.stdout or "").splitlines() if s.strip().startswith("KALDI")]
            # 🔴 ÇÖKME KIRMIZIYLA KARIŞMAZ: kabul ölçütü çıkış kodu DEĞİL, ölçülen iddia + işaret.
            if p.returncode not in (0, 1) or (p.returncode == 1 and not kirmizi):
                print("  HATA M%02d [%s] %s -> COKME/OLCULEMEDI (rc=%d) | %s"
                      % (i, beklenen, dosya, p.returncode, aciklama))
                print("        " + ((p.stderr or p.stdout or "").strip().splitlines() or [""])[-1][:180])
                basarisiz.append("M%02d [cokme]" % i)
                continue
            gercek = "YESIL" if p.returncode == 0 else "KIRMIZI"
            ok = gercek == beklenen
            sayi = [s for s in (p.stdout or "").splitlines() if "CIFT=" in s]
            print("  %-4s M%02d [%s] -> %s (%d iddia kırmızı) | %s"
                  % ("OK" if ok else "HATA", i, beklenen, gercek, len(kirmizi), aciklama))
            if sayi:
                print("        " + sayi[0].strip()[:140])
            for s in kirmizi[:2]:
                print("        " + s.strip()[:150])
            olcum.append((i, beklenen, gercek, len(kirmizi)))
            if not ok:
                basarisiz.append("M%02d" % i)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    oldurucu = sum(1 for _i, b, _g, _n in olcum if b == "KIRMIZI")
    kontrol = sum(1 for _i, b, _g, _n in olcum if b == "YESIL")
    print("\nMUTASYON: %d öldürücü + %d kontrol koştu · beklentiyi tutmayan: %d %s"
          % (oldurucu, kontrol, len(basarisiz), basarisiz or ""))
    return 1 if basarisiz else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK)
    ap.add_argument("--modul", default=None, help="marka_model_build.py yerine BAŞKA modül")
    ap.add_argument("--dokum", action="store_true")
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    try:
        return kabul(a.kok, a.dokum, a.modul)
    except Olculemedi as e:
        print("\nSONUC: OLCULEMEDI ❓  %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
