#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — edge-kart-kapisi.py'nin KARDES DEPO AYRISTIRMASI canli mi?

NEDEN VAR (OLCULDU, 11 Agu 2026 — kardes mimar bulgusu):
    tools/edge-kart-kapisi.py, kardes depodaki (edge Worker) `KART_ALANLARI` sabitini
    su desenle okuyordu:
        re.search(r"KART_ALANLARI\\s*=\\s*([`\\"'])([\\s\\S]*?)\\1", w)
    Bu desen ILK tirnaktan ILK kapanan tirnaga kadarini gorur. Sabit JS'te
        const KART_ALANLARI =
          "u.id, ... u.parametrik," +
          " u.tur, u.konfigur," +
          " substr(u.aciklama, 1, 160) AS aciklama";
    seklinde COK PARCALI yazildiginda IKINCI ve sonraki parcalar GORUNMEZ. Kolon
    SELECT'te GERCEKTEN varken kapi "eksik alan(lar)" basar — sessiz, KOTUMSER yalan.

    OLCULEN KANIT (gercek kardes dosya, bellekte kopya uzerinde):
      `u.tur, u.konfigur` ILK parcada  -> eski desen eksik: [tavsiyeFilament]
      ayni ikili IKINCI parcaya tasindi -> eski desen eksik: [konfigur, tavsiyeFilament,
                                                             tur]   (ikisi YALAN)
                                           yeni ayristirma: [tavsiyeFilament]  (dogru)
    Korluk kardes depoda LOAD-BEARING bir yazim kisitina donusmustu ("yeni kolon alt
    satira degil BU satira yazilir") — yani bizim ayristirma hatamiz, baska bir evin
    kaynak duzenini belirliyordu.

🔴 ONARIMIN KENDISI DE BIR RISKTIR: bir ayristirmayi "daha genis" yapmak, fail-loud bir
kapiyi fail-open'a cevirmenin en ucuz yoludur ([[duzeltme-fail-open-cevirebilir]]).
Bu yuzden batarya TEK YONLU DEGILDIR — dort ayri kolu AYRI AYRI olur:
    A1  COK PARCA POZITIF   ikinci parcadaki alan GORULUYOR mu
    A2  GERCEK EKSIK        gercekten olmayan alan HALA "eksik" deniyor mu (fail-open?)
    A3  OLCULEMEDI          dinamik/cozulemeyen tanimda "alan yok" DENMIYOR mu
    A4  POZITIF KOL         var olan alan yanlislikla "eksik" sayilmiyor mu
    A5  YORUM TUZAGI        sabitin USTUNDEKI ayni adli YORUM kaynak sanilmiyor mu

🔴 JETONLAR AYRIK (bu depoda isirdi: [[maskeleme-kismi-kapatma]]). Kollarin capalari
birbirinin ALT DIZESI DEGILDIR — eski cikti "eksik alan(lar): YOK" diyerek POZITIF kolu
NEGATIF kolun govdesi icine gomuyordu; pozitif kolu olduren bir mutant o ortak govdeden
gecebilirdi. Simdi: WORKER_KART_TAM · WORKER_KART_EKSIK · OLCULEMEDI · WORKER_AGAC_YOK.

🔴 BYTECODE ONBELLEGI BAGISIKLIGI ([[mutasyon-bytecode-onbellegi]]): bu batarya HICBIR
mutasyonu DISKE YAZMAZ. Kaynak metin okunur, BELLEKTE degistirilir ve
`exec(compile(src, ...), types.ModuleType(...).__dict__)` ile calistirilir. Diskte .py
dosyasi olusmadigi icin CPython ne `__pycache__` yazar ne okur — "ayni saniyede ayni
uzunlukta yazilan mutasyon diske islenmez" tuzagi YAPISAL OLARAK GERCEKLESEMEZ. Ayrica her
mutant icin (a) capa TAM 1 kez geciyor mu, (b) eski metin gitti mi, (c) yeni metin geldi
mi UCU DE olculur; ve kosum sonunda canli dosyanin sha256'si bas=son karsilastirilir.

FIKSTURLER SENTETIKTIR: kardes depo (~/dev/pruvo-bot) diskte OLMASA da batarya kosar —
CI fresh checkout'unda YAPISAL kirmizi vermez. Katalog (urunler.json) OKUNMAZ.

KONTROL MUTANTI olculen eksenin ICINDEN secildi: bosluk kumesinin SIRASI degistirilir
(`" \\t\\r\\n"` -> `"\\t \\n\\r"`). Ayni satira dokunur ama uyelik testi sirasiz oldugu
icin davranis DEGISMEZ -> YESIL kalmali. Kalmazsa batarya "her degisiklikte kirmizi"
demektir ve hicbir sey olcmuyordur ([[beyan-edilmis-survivor]]).

Calistir:  python3 tools/edge-kart-tirnak-mutasyon.py   (0 = gecti, 1 = kaldi)
"""
import hashlib
import os
import sys
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(TOOLS, "edge-kart-kapisi.py")

# --------------------------------------------------------------------- fiksturler
# Gercek kardes dosyanin SEKLINI taklit eder ([[nobetci-fikstur-sekli]]): `const` +
# satir sonu + `+` ile birlestirilen parcalar + son parcada SQL fonksiyonu.
FIX_COK_PARCA = (
    "// KART SOZLESMESI (SENTETIK fikstur — gercek kardes dosya DEGIL).\n"
    "//   YORUM TUZAGI: KART_ALANLARI = \"u.sahte_kolon\"  <- bu bir YORUM, kaynak DEGIL.\n"
    "const KART_ALANLARI =\n"
    "  \"u.id, u.baslik, u.kategori, u.fiyat, u.parametrik,\" +\n"
    "  \" u.tur, u.konfigur,\" +   /* IKINCI parca — eski desen buraya KORDU */\n"
    "  \" substr(u.aciklama, 1, 160) AS aciklama\";\n"
    "\n"
    "function kartaCevir(r) { return { id: r.id }; }\n"
)

FIX_TEK_PARCA_TAM = (
    "const KART_ALANLARI = \"u.id, u.kategori, u.fiyat, u.parametrik, u.tur, u.konfigur\";\n"
)

FIX_DINAMIK = (
    "const SUTUNLAR = [\"u.id\", \"u.tur\", \"u.konfigur\"];\n"
    "const KART_ALANLARI = SUTUNLAR.join(\", \");\n"
)

FIX_TEMPLATE = (
    "const EK = \"u.tur\";\n"
    "const KART_ALANLARI = `u.id, u.kategori, u.fiyat, u.parametrik, u.konfigur, ${EK}`;\n"
)

# A4'un kontrol kumesi: FIX_TEK_PARCA_TAM'da hepsi GERCEKTEN var.
TAM_ALANLAR = ["fiyat", "kategori", "konfigur", "parametrik", "tur"]


# ------------------------------------------------------------------------ iddialar
def a1_cok_parca_pozitif(mod):
    """Ikinci dize parcasindaki `u.konfigur` GORULUYOR mu? (korlugun ta kendisi)"""
    satir, eksik = mod.worker_kapsam_satiri(FIX_COK_PARCA, ["tur", "konfigur"])
    return (eksik == [] and mod.JETON_TAM in satir), satir


def a2_gercek_eksik(mod):
    """GERCEKTEN olmayan alan HALA eksik deniyor mu? (onarim fail-open'a kaymis mi)"""
    satir, eksik = mod.worker_kapsam_satiri(
        FIX_COK_PARCA, ["tur", "konfigur", "tavsiyeFilament"])
    return (eksik == ["tavsiyeFilament"] and mod.JETON_EKSIK in satir), satir


def a3_olculemedi(mod):
    """Cozulemeyen tanimda 'alan yok' DENMEZ -> OLCULEMEDI (fail-closed)."""
    parcalar = []
    hepsi = True
    for ad, fx in (("dinamik-join", FIX_DINAMIK), ("template-interpolasyon", FIX_TEMPLATE)):
        satir, eksik = mod.worker_kapsam_satiri(fx, ["tur"])
        ok = (eksik is None and mod.JETON_OLCULEMEDI in satir
              and mod.JETON_TAM not in satir and mod.JETON_EKSIK not in satir)
        hepsi = hepsi and ok
        parcalar.append("%s:%s" % (ad, "OK" if ok else ("HATA -> " + satir[:110])))
    return hepsi, " | ".join(parcalar)


def a4_pozitif_kol(mod):
    """VAR olan alan yanlislikla 'eksik' sayiliyor mu? (yanlis-pozitif ekseni)"""
    satir, eksik = mod.worker_kapsam_satiri(FIX_TEK_PARCA_TAM, TAM_ALANLAR)
    return (eksik == [] and mod.JETON_TAM in satir), satir


def a5_yorum_tuzagi(mod):
    """Sabitin USTUNDEKI ayni adli YORUM satiri kaynak sanilmamali."""
    deger, parca, sebep = mod.js_sabit_dize(FIX_COK_PARCA, "KART_ALANLARI")
    ok = (deger is not None and "sahte_kolon" not in deger and "u.konfigur" in deger
          and "AS aciklama" in deger and parca == 3)
    return ok, "parca=%r sebep=%r deger=%r" % (parca, sebep, deger)


IDDIALAR = [
    ("A1 COK PARCA POZITIF (ikinci parcadaki alan goruluyor mu)", a1_cok_parca_pozitif),
    ("A2 GERCEK EKSIK      (olmayan alan hala eksik mi — fail-open?)", a2_gercek_eksik),
    ("A3 OLCULEMEDI        (dinamik tanimda sessiz yesil YOK)", a3_olculemedi),
    ("A4 POZITIF KOL       (var olan alan eksik sayilmiyor)", a4_pozitif_kol),
    ("A5 YORUM TUZAGI      (ustteki yorum kaynak sanilmiyor)", a5_yorum_tuzagi),
]

# ------------------------------------------------------------------------ mutantlar
# (ad, capa, yerine, KIRMIZI_beklenir_mi, oldurdugu_kol)
_ARTI_KOLU = ('        if c == "+":\n'
              '            i += 1\n'
              '            bekle_operand = True\n'
              '            continue\n')
_EKSIK_HESABI = ('    eksikler = [a for a in kontrol_alanlari\n'
                 '                if not re.search(r"\\b%s\\b" % re.escape(a), deger)]\n')
_OLCULEMEDI_KOLU = (
    '    if deger is None:\n'
    '        return ("edge Worker KART_ALANLARI %s: %s (kardes depo, KAPSAM DISI — hukum "\n'
    '                "VERILMEDI; \'cozemedim = alan yok\' sessiz gecisi YASAK)"\n'
    '                % (JETON_OLCULEMEDI, sebep), None)\n')
_CAPA_SATIRI = ('    m = re.search(r"^[ \\t]*(?:const[ \\t]+|let[ \\t]+|var[ \\t]+)?%s[ \\t]*=(?!=)"\n'
                '                  % re.escape(ad), kaynak, re.M)\n')

MUTANTLAR = [
    ("M-1 cok-parcali birlestirme SOKULDU (ilk parcaya geri donuldu — KORLUK GERI GELIR)",
     _ARTI_KOLU,
     '        if c == "+":\n'
     '            return "".join(parcalar), len(parcalar), None\n',
     True, "A1/A5"),
    ("M-2 FAIL-OPEN: gercekten eksik alan 'var' sayildi (eksik listesi bosaltildi)",
     _EKSIK_HESABI,
     "    eksikler = []\n",
     True, "A2"),
    ("M-3 OLCULEMEDI kolu SESSIZ YESILE cevrildi (cozemedim = alan yok)",
     _OLCULEMEDI_KOLU,
     '    if deger is None:\n'
     '        return ("edge Worker KART_ALANLARI %s (cozulemedi ama sorun yok)"\n'
     '                % JETON_TAM, [])\n',
     True, "A3"),
    ("M-4 POZITIF KOL OLDURULDU: var olan alan 'eksik' sayildi (yanlis-pozitif)",
     '                if not re.search(r"\\b%s\\b" % re.escape(a), deger)]',
     '                if re.search(r"\\b%s\\b" % re.escape(a), deger)]',
     True, "A4/A1"),
    ("M-5 SATIR BASI CAPASI SOKULDU (ustteki YORUM kaynak sanilir)",
     _CAPA_SATIRI,
     '    m = re.search(r"%s[ \\t]*=(?!=)" % re.escape(ad), kaynak)\n',
     True, "A5/A1"),
    ("M-6 KONTROL: bosluk kumesinin SIRASI degisti (davranis DEGISMEZ) — YESIL kalmali",
     '        if c in " \\t\\r\\n":\n',
     '        if c in "\\t \\n\\r":\n',
     False, "-"),
]


# --------------------------------------------------------------------------- kosum
def kaynak_oku():
    with open(HEDEF, encoding="utf-8") as f:
        return f.read()


def modul_yukle(src, etiket):
    """Kaynagi BELLEKTE modul olarak calistirir. DISKE YAZILMAZ -> __pycache__ YOK."""
    mod = types.ModuleType("edge_kart_kapisi_mutant_" + etiket)
    mod.__file__ = HEDEF          # modul icindeki os.path.abspath(__file__) icin sart
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    exec(compile(src, "<edge-kart-kapisi %s>" % etiket, "exec"), mod.__dict__)
    return mod


def mutasyon_uygula(src, eski, yeni):
    """(mutant_kaynak, hata) — uygulandigini UC eksende olcer."""
    n = src.count(eski)
    if n != 1:
        return None, "capa kaynakta %d kez geciyor (1 olmali) — edge-kart-kapisi.py degismis" % n
    mut = src.replace(eski, yeni, 1)
    if mut == src:
        return None, "mutasyon metni DEGISTIRMEDI"
    if eski in mut:
        return None, "eski metin mutantta HALA var (mutasyon uygulanmadi)"
    if yeni and yeni not in mut:
        return None, "yeni metin mutantta YOK"
    return mut, None


def iddialari_kos(mod):
    """[(ad, durum, detay)] — durum: PASS | FAIL | COKTU."""
    sonuc = []
    for ad, fn in IDDIALAR:
        try:
            ok, detay = fn(mod)
        except Exception as e:                                   # noqa: BLE001
            sonuc.append((ad, "COKTU", "%s: %s" % (type(e).__name__, e)))
            continue
        sonuc.append((ad, "PASS" if ok else "FAIL", detay))
    return sonuc


def main():
    if not os.path.exists(HEDEF):
        print("KIRMIZI: hedef bulunamadi: %s" % HEDEF)
        return 1
    src = kaynak_oku()
    bas_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    fails = []

    print("=== KONTROL KOSUMU (mutasyonsuz) — 5/5 iddia PASS olmali")
    kontrol = iddialari_kos(modul_yukle(src, "kontrol"))
    for ad, durum, detay in kontrol:
        print("  %-6s %s" % (durum, ad))
        if durum != "PASS":
            print("        %s" % detay[:400])
            fails.append("mutasyonsuz kosumda %s -> %s" % (ad, durum))

    print("\n=== MUTANTLAR (oldurucu olanlar en az 1 iddiayi FAIL etmeli)")
    kirmizi = 0
    beklenen = sum(1 for m in MUTANTLAR if m[3])
    kontrol_mutant = None
    for ad, eski, yeni, kirmizi_bekle, kol in MUTANTLAR:
        mut, hata = mutasyon_uygula(src, eski, yeni)
        if hata:
            print("  FAIL   %s -> MUTASYON UYGULANAMADI: %s" % (ad, hata))
            fails.append(ad + " (uygulanamadi)")
            continue
        try:
            mod = modul_yukle(mut, "mut")
        except Exception as e:                                   # noqa: BLE001
            print("  FAIL   %s -> MUTANT YUKLENEMEDI (%s: %s) — cokme KIRMIZI SAYILMAZ"
                  % (ad, type(e).__name__, e))
            fails.append(ad + " (yuklenemedi)")
            continue
        sonuc = iddialari_kos(mod)
        dusen = [s[0].split()[0] for s in sonuc if s[1] == "FAIL"]
        coken = [s[0].split()[0] for s in sonuc if s[1] == "COKTU"]
        if kirmizi_bekle:
            ok = bool(dusen) and not coken
            if ok:
                kirmizi += 1
            print("  %-6s %s" % ("PASS" if ok else "FAIL", ad))
            print("         beklenen kol: %s | DUSEN: %s | COKEN: %s"
                  % (kol, ", ".join(dusen) or "-", ", ".join(coken) or "-"))
            if not ok:
                fails.append(ad + (" (cokme kirmiziyla karismasin)" if coken
                                   else " (mutant YAKALANMADI — iddia OLU)"))
        else:
            ok = not dusen and not coken
            kontrol_mutant = "YESIL" if ok else "KIRMIZI"
            print("  %-6s %s -> %s" % ("PASS" if ok else "FAIL", ad, kontrol_mutant))
            if not ok:
                print("         DUSEN: %s | COKEN: %s"
                      % (", ".join(dusen) or "-", ", ".join(coken) or "-"))
                fails.append(ad + " (kontrol mutanti kirmizi yandi: batarya olcmuyor)")

    son_sha = hashlib.sha256(kaynak_oku().encode("utf-8")).hexdigest()
    if son_sha != bas_sha:
        fails.append("canli edge-kart-kapisi.py DEGISTI (bas!=son sha256)")
    print("\ncanli dosya sha256 bas=son: %s (mutasyon diske YAZILMADI)"
          % ("EVET ✔" if son_sha == bas_sha else "HAYIR ✘"))
    print("MUTANT_KIRMIZI=%d/%d  KONTROL_MUTANT=%s"
          % (kirmizi, beklenen, kontrol_mutant or "KOSULMADI"))
    if fails:
        print("SONUC: KIRMIZI ❌  (%d)" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("SONUC: YESIL ✅ — ayristirma onarimi CANLI (korluk, fail-open, sessiz yesil ve "
          "yanlis-pozitif kollari AYRI AYRI olculdu).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
