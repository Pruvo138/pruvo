#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VARLIK KAPISI MUTASYON NOBETI — tools/varlik-test.py OLU NOBETCI mi?

NEDEN VAR: bir kabul testinin "yesil" olmasi tek basina hicbir sey kanitlamaz; asil soru
BOZULDUGUNDA KIRMIZI YANIYOR MU. Bu betik tools/build.py'nin GECICI bir kopyasina spec'in
5. bolumundeki alti mutanti tek tek uygular ve varlik-test'in her birinde beklenen rengi
verdigini olcer. GERCEK DEPO DOSYASINA DOKUNULMAZ: mutasyon, tools/ agacinin gecici bir
kopyasinda yapilir (kok girdileri ve .git gercek depoya symlink; .git gerekli cunku
varlik-test kiyas ureticisini git gecmisinden alir).

KONTROL MUTANTI ZORUNLU (M6): davranisi degistirmeyen bir yeniden adlandirma YESIL
kalmali. Aksi halde "her degisiklikte kirmizi yanan" bir kapi da bu testten gecerdi ve
kirmizilarin hicbir bilgi degeri olmazdi ([[fikstur-degeri-mutasyon-koru]]).

Kullanim: python3 tools/varlik-mutasyon.py
Cikis: 0 = alti mutantin altisi da beklenen rengi verdi · 1 = en az biri sapti.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
# Symlink DEGIL, gercek (bos) dizin olmasi gerekenler: uretim ciktilari.
YEREL_DIZINLER = ("varlik", "urun", "_yayin")

# (kod, aciklama, eski, yeni, beklenen_rc)
MUTANTLAR = [
    ("M1", "hash sabitlendi (icerik degisse de ad degismez)",
     'return hashlib.sha256(icerik.encode("utf-8")).hexdigest()[:VARLIK_HASH_UZUNLUK]',
     'return "0000000000"', 1),
    ("M2", "sayfadaki referans YANLIS ada baglandi",
     '    _VARLIK_ONBELLEK[ad] = url\n    return url',
     '    _VARLIK_ONBELLEK[ad] = url\n    return url.replace("-", "-0", 1)', 1),
    ("M3", "harici dosyaya CSS'in bir kismi yazilmadi (kirpma)",
     '        govde = yorum_soy.css_soy(icerik)',
     '        govde = yorum_soy.css_soy(icerik)[:-50]', 1),
    ("M4", "sayfa govdesinden bir meta alani dusuruldu",
     '<meta name="twitter:card" content="summary_large_image">\n', '', 1),
    ("M5", "satir-ici cekirdek kaynaktan koparildi (IKIZ uretildi)",
     '    parcalar = ["<style>" + cekirdek + "</style>",',
     '    parcalar = ["<style>:root{--navy:#12294d}*{box-sizing:border-box}</style>",', 1),
    ("M6", "KONTROL: davranisi degistirmeyen yeniden adlandirma",
     'def varlik_adres(onek, uzanti, icerik):', 'def varlik_adres(on_ek, uzanti, icerik):', 0),
]
# M6 yeniden adlandirmasinin govdedeki devami (tek mutant, uc nokta).
M6_EK = [
    ('                           % (onek, uzanti))', '                           % (on_ek, uzanti))'),
    ('    ad = "%s-%s.%s" % (onek, varlik_hash(govde), uzanti)',
     '    ad = "%s-%s.%s" % (on_ek, varlik_hash(govde), uzanti)'),
]

# ---------------------------------------------------------------------------
# CSS BEYAN YUZEYININ MUTANTLARI (11 Agu 2026)
# ---------------------------------------------------------------------------
# 🔴 NEDEN: 11 Agu'da eksen 2'nin CSS koluna beyan yuzeyi (BILEREK_DEGISEN_CSS)
# ACILDI — o kol bayt esitligiydi ve kacis yolu olmadigi icin paylasilan urun
# sayfasi CSS'ini FIILEN degistirilemez kiliyordu. Yuzey KAPIYI SUSTURMA KOLUDUR;
# susturma kolunun kendisi nobetsiz kalamaz ([[kapi-kapsam-genisletme-tuzagi]]).
# Yukaridaki alti mutant yalnizca TASIMA mekanigini olcer, YUZEYI olcmez.
#
# 🔴 HUKUM RC'YE BIRAKILMAZ: uc mutant da rc=1 verir; ayirt eden sey BASILAN
# JETONDUR. Jetonlar AYRIK secildi (hicbiri digerinin alt dizesi degil) —
# "2b BAYAT CSS BEYANI" · "2 CSS KAYIP/EKLENTI" · "0 CSS BEYAN YUZEYI BOZUK".
# (kod, aciklama, dosya, [(eski, yeni)], beklenen_rc, beklenen_jeton)
CSS_BEYAN_MUTANTLARI = [
    ("N1", "BAYAT BEYAN: beyanin isaret ettigi CSS artik o degil",
     "build.py",
     [(";width:fit-content;height:56px;",
       ";width:fit-content;height:57px;")],
     1, "2b BAYAT CSS BEYANI"),

    ("N2", "POZITIF KOL: beyan KAPSAMI DISINDA CSS degisikligi",
     "build.py",
     [("  .crumbs{font-size:13px;color:var(--gray-text);margin-bottom:18px}",
       "  .crumbs{font-size:12.5px;color:var(--gray-text);margin-bottom:18px}")],
     1, "2 CSS KAYIP/EKLENTI"),

    ("N3", "AYIRT EDICILIK GEVSETILDI: beyan her seyi yutabilir hale gelir",
     "varlik-test.py",
     [('        if len(gorunur) < 12 or not ("{" in yeni_p or ":" in yeni_p):',
       "        if False:")],
     1, "0 CSS BEYAN YUZEYI BOZUK"),
]


# ---------------------------------------------------------------------------
# GORSEL KOK MANDALI MUTANTLARI (13 Eyl 2026, KraL ana-oturum-17 hukmu)
# ---------------------------------------------------------------------------
# Mandal BUYUYEMEZ taban: 86 gelenek disi adres gecer, 87.si / listeden dusen / okunamayan
# dosya / tohum disi giris KIRMIZI; veri DUZELTILINCE bayat giris serit-a3'u BLOKLAMAZ ama
# `--mandal-nobet` (SERIT B) KIRMIZI yakar. Hukum rc + BASILAN JETON; katalog ve mandal
# mutasyonlari GECICI kokte (urunler.json symlink'i kopru edilir, canli dosya ELLENMEZ).
# Mandal kollari katalog GENELINDE olctugu icin orneklem 1 yeter (sure ~6x kisalir).
# (kod, aciklama, islem, ek_argumanlar, beklenen_rc, beklenen_jeton)
MANDAL_MUTANTLARI = [
    ("G1", "87. gelenek disi adres katalogda (mandal disi)",
     "katalog_kok_adres", [], 1, "GELENEK DISI ADRES MANDAL DISINDA"),
    ("G2", "mandaldan bir satir silindi, adres katalogda duruyor",
     "mandal_satir_sil", [], 1, "GELENEK DISI ADRES MANDAL DISINDA"),
    ("G3", "mandal dosyasi okunamaz (bozuk JSON) -> fail-closed",
     "mandal_boz", [], 1, "GORSEL KOK MANDALI OKUNAMADI"),
    ("G4", "KONTROL-BUYUME: mandala tohum disi giris eklendi",
     "mandal_buyut", [], 1, "GORSEL KOK MANDALI BUYUDU"),
    ("G5", "veri duzeltildi, giris BAYAT: serit-a3 BLOKLAMAZ",
     "katalog_duzelt", [], 0, "GORSEL KOK MANDALI BAYAT GIRIS"),
    ("G6", "ayni bayat giris --mandal-nobet (SERIT B) KIRMIZI",
     "katalog_duzelt", ["--mandal-nobet"], 1, "GORSEL KOK MANDALI BAYAT GIRIS"),
]
MANDAL_DOSYA = "varlik-gorsel-kok-mandali.json"


def _katalog_yaz(tmp, degistir):
    """Gecici kokteki urunler.json SYMLINK'ini kopru eder, degistirilmis KOPYA yazar."""
    with io.open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    if not degistir(urunler):
        return False
    yol = os.path.join(tmp, "urunler.json")
    os.unlink(yol)
    with io.open(yol, "w", encoding="utf-8") as f:
        json.dump(urunler, f, ensure_ascii=False)
    return True


def _mandal_yol(tmp):
    return os.path.join(tmp, "tools", MANDAL_DOSYA)


def _mandal_oku(tmp):
    with io.open(_mandal_yol(tmp), encoding="utf-8") as f:
        return json.load(f)


def _mandal_yaz(tmp, veri):
    with io.open(_mandal_yol(tmp), "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def mandal_mutasyonu(tmp, islem):
    """True = mutasyon uygulandi. False = capa bulunamadi (mutant OLCULEMEDI)."""
    if islem == "katalog_kok_adres":
        def kok_yap(urunler):
            for u in urunler:
                g = u.get("gorseller") or []
                if g and g[0].startswith("https://media.pruvo3d.com/urunler/"):
                    g[0] = g[0].replace("/urunler/", "/", 1)
                    return True
            return False
        return _katalog_yaz(tmp, kok_yap)
    if islem == "katalog_duzelt":
        ilk = (_mandal_oku(tmp).get("adresler") or [None])[0]
        if not ilk:
            return False

        def duzelt(urunler):
            for u in urunler:
                if u.get("id") == ilk["id"] and ilk["url"] in (u.get("gorseller") or []):
                    u["gorseller"] = [("https://media.pruvo3d.com/urunler/" + x.rsplit("/", 1)[1])
                                      if x == ilk["url"] else x for x in u["gorseller"]]
                    return True
            return False
        return _katalog_yaz(tmp, duzelt)
    if islem == "mandal_satir_sil":
        veri = _mandal_oku(tmp)
        if not veri.get("adresler"):
            return False
        veri["adresler"] = veri["adresler"][1:]
        _mandal_yaz(tmp, veri)
        return True
    if islem == "mandal_boz":
        with io.open(_mandal_yol(tmp), "w", encoding="utf-8") as f:
            f.write("{bozuk")
        return True
    if islem == "mandal_buyut":
        veri = _mandal_oku(tmp)
        veri.setdefault("adresler", []).append(
            {"id": "sahte-mandal-girisi", "url": "https://media.pruvo3d.com/sahte-mandal-1.jpg"})
        _mandal_yaz(tmp, veri)
        return True
    return False


def gecici_kok():
    tmp = tempfile.mkdtemp(prefix="varlik-mutasyon-")
    shutil.copytree(TOOLS, os.path.join(tmp, "tools"), symlinks=True)
    os.symlink(os.path.join(ROOT, ".git"), os.path.join(tmp, ".git"))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git") or ad in YEREL_DIZINLER:
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(tmp, ad))
    for ad in YEREL_DIZINLER:
        os.makedirs(os.path.join(tmp, ad), exist_ok=True)
    return tmp


def uygula(yol, ciftler):
    s = io.open(yol, encoding="utf-8").read()
    for eski, yeni in ciftler:
        n = s.count(eski)
        if n != 1:
            return None, "capa %d kez gecti (1 bekleniyordu): %r" % (n, eski[:60])
        s = s.replace(eski, yeni, 1)
    io.open(yol, "w", encoding="utf-8").write(s)
    return True, ""


def kos(tmp, ek=None, ornek="6"):
    p = subprocess.run([sys.executable, os.path.join(tmp, "tools", "varlik-test.py"),
                        "--ornek", ornek] + list(ek or []),
                       capture_output=True, text=True, timeout=3600)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _ozet(rel):
    with io.open(os.path.join(TOOLS, rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# Mutasyona acilan CANLI dosyalar — batarya bunlara ASLA yazmaz (mutasyon gecici
# kopyada olur). "yazmiyorum" bir BEYANDIR; kanit bas=son ozet esitligidir.
IZLENEN_CANLI = ("build.py", "varlik-test.py", MANDAL_DOSYA, os.path.join("..", "urunler.json"))


def main():
    ozetler = {rel: _ozet(rel) for rel in IZLENEN_CANLI}
    # 0) MUTASYONSUZ TABAN: kopya agac oldugu gibi YESIL olmali (yoksa mutant
    #    kirmizilarinin hicbiri mutasyondan geliyor sayilamaz).
    tmp = gecici_kok()
    try:
        rc, cikti = kos(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if rc != 0:
        print("TABAN KIRMIZI (rc=%d) -> mutasyon olcumu ANLAMSIZ.\n%s" % (rc, cikti[-1500:]))
        return 1
    print("  taban (mutasyonsuz): rc=0 YESIL")

    sapan = []
    print("\n%-4s %-58s %-8s %-8s %s" % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "SONUC"))
    for kod, aciklama, eski, yeni, beklenen in MUTANTLAR:
        ciftler = [(eski, yeni)] + (M6_EK if kod == "M6" else [])
        tmp = gecici_kok()
        try:
            ok, hata = uygula(os.path.join(tmp, "tools", "build.py"), ciftler)
            if not ok:
                sapan.append("%s: capa uygulanamadi (%s)" % (kod, hata))
                print("%-4s %-58s %-8s %-8s CAPA YOK" % (kod, aciklama[:58], beklenen, "-"))
                continue
            rc, cikti = kos(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        renk = "KIRMIZI" if rc == 1 else ("YESIL" if rc == 0 else "rc=%d" % rc)
        tamam = (rc == beklenen)
        if not tamam:
            sapan.append("%s: beklenen rc=%d, olculen rc=%d" % (kod, beklenen, rc))
        print("%-4s %-58s %-8s %-8s %s"
              % (kod, aciklama[:58], "KIRMIZI" if beklenen else "YESIL", renk,
                 "OK" if tamam else "SAPTI"))

    # --- CSS BEYAN YUZEYI (11 Agu): hukum rc + BASILAN JETON ile birlikte verilir.
    print("\n%-4s %-58s %-8s %-8s %s" % ("KOD", "CSS BEYAN YUZEYI MUTANTI",
                                         "BEKLENEN", "OLCULEN", "JETON"))
    for kod, aciklama, dosya, ciftler, beklenen, jeton in CSS_BEYAN_MUTANTLARI:
        tmp = gecici_kok()
        try:
            ok, hata = uygula(os.path.join(tmp, "tools", dosya), ciftler)
            if not ok:
                sapan.append("%s: capa uygulanamadi (%s)" % (kod, hata))
                print("%-4s %-58s %-8s %-8s CAPA YOK" % (kod, aciklama[:58], beklenen, "-"))
                continue
            rc, cikti = kos(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        renk = "KIRMIZI" if rc == 1 else ("YESIL" if rc == 0 else "rc=%d" % rc)
        jeton_var = jeton in cikti
        tamam = (rc == beklenen) and jeton_var
        if rc != beklenen:
            sapan.append("%s: beklenen rc=%d, olculen rc=%d" % (kod, beklenen, rc))
        if not jeton_var:
            sapan.append("%s: KIRMIZI ama YANLIS SEBEPTEN — beklenen jeton BASILMADI: %r"
                         % (kod, jeton))
        print("%-4s %-58s %-8s %-8s %s"
              % (kod, aciklama[:58], "KIRMIZI" if beklenen else "YESIL", renk,
                 ("%s ok" % jeton) if jeton_var else ("%s YOK" % jeton)))

    # --- GORSEL KOK MANDALI (13 Eyl): hukum rc + BASILAN JETON; orneklem 1.
    print("\n%-4s %-58s %-8s %-8s %s" % ("KOD", "GORSEL KOK MANDALI MUTANTI",
                                         "BEKLENEN", "OLCULEN", "JETON"))
    for kod, aciklama, islem, ek, beklenen, jeton in MANDAL_MUTANTLARI:
        tmp = gecici_kok()
        try:
            if not mandal_mutasyonu(tmp, islem):
                sapan.append("%s: capa uygulanamadi (%s)" % (kod, islem))
                print("%-4s %-58s %-8s %-8s CAPA YOK" % (kod, aciklama[:58], beklenen, "-"))
                continue
            rc, cikti = kos(tmp, ek=ek, ornek="1")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        renk = "KIRMIZI" if rc == 1 else ("YESIL" if rc == 0 else "rc=%d" % rc)
        jeton_var = jeton in cikti
        if rc != beklenen:
            sapan.append("%s: beklenen rc=%d, olculen rc=%d\n%s" % (kod, beklenen, rc, cikti[-800:]))
        if not jeton_var:
            sapan.append("%s: beklenen jeton BASILMADI: %r" % (kod, jeton))
        print("%-4s %-58s %-8s %-8s %s"
              % (kod, aciklama[:58], "KIRMIZI" if beklenen else "YESIL", renk,
                 ("%s ok" % jeton[:24]) if jeton_var else ("%s YOK" % jeton[:24])))

    for rel, beklenen_ozet in sorted(ozetler.items()):
        if _ozet(rel) != beklenen_ozet:
            sapan.append("tools/%s CANLI AGACTA degisti (mutasyon kopyada kalmadi)" % rel)
    print("\n  canli agac: %d dosya bayt-birebir ayni (mutasyon diske SIZMADI) — %s"
          % (len(ozetler), ", ".join("tools/%s" % r for r in sorted(ozetler))))

    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    _toplam = len(MUTANTLAR) - 1 + len(CSS_BEYAN_MUTANTLARI) + len(MANDAL_MUTANTLARI)
    print("\nMUTANT=%d/%d (tasima %d + CSS beyan yuzeyi %d + gorsel kok mandali %d) · "
          "KONTROL=YESIL (M6)"
          % (_toplam, _toplam, len(MUTANTLAR) - 1, len(CSS_BEYAN_MUTANTLARI),
             len(MANDAL_MUTANTLARI)))
    print("OK: her mutant beklenen rengi VE beklenen jetonu verdi; kontrol mutanti YESIL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
