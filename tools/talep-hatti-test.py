#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K186 talep hatti kabul bataryasi.

Kaynak eksenleri kelime avi degil, hedef yapinin sinirli ayrıştırmasidir. Mutantlar
gecici kopyalarda calisir; ana kaynak hicbir zaman mutasyona ugramaz.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TALEP = ROOT / "shop" / "src" / "talep.js"
TEST = ROOT / "shop" / "test" / "talep.mjs"
SEMA = ROOT / "tools" / "d1-sema.sql"
NODE = "node"

PIS = {"telefon", "tel", "email", "eposta", "ad", "adres", "address"}
ALANLAR = {"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website"}
IDDIALAR = [
    "A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "B5",
    "C1", "C2", "C3", "C4", "C5", "D1", "D2", "D3", "D4", "E1", "E2",
]
SIZINTI_IDDIALAR = ["B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4", "C5"]


def dengeli_blok(metin, baslangic):
    """JS benzeri parantezli bir blogu stringleri atlayarak ayristir."""
    acik = metin[baslangic]
    es = {"[": "]", "(": ")", "{": "}"}
    kapanis = es[acik]
    seviye = 0
    tirnak = None
    kacis = False
    for indis in range(baslangic, len(metin)):
        karakter = metin[indis]
        if tirnak:
            if kacis:
                kacis = False
            elif karakter == "\\":
                kacis = True
            elif karakter == tirnak:
                tirnak = None
            continue
        if karakter in ("'", '"', "`"):
            tirnak = karakter
            continue
        if karakter == acik:
            seviye += 1
        elif karakter == kapanis:
            seviye -= 1
            if seviye == 0:
                return metin[baslangic + 1:indis], indis + 1
    raise ValueError("dengeli blok bulunamadi")


def talepler_kolonlari(sql):
    eslesme = re.search(r"CREATE TABLE IF NOT EXISTS talepler\s*\(", sql, re.I)
    if not eslesme:
        return []
    govde, _ = dengeli_blok(sql, eslesme.end() - 1)
    kolonlar = []
    for satir in govde.splitlines():
        satir = satir.split("--", 1)[0].strip()
        kolon = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s+[A-Za-z]", satir)
        if kolon:
            kolonlar.append(kolon.group(1))
    return kolonlar


def izinli_liste_elemanlari(js):
    eslesme = re.search(r"const\s+izinliAnahtarlar\s*=\s*new\s+Set\s*\(", js)
    if not eslesme:
        return []
    govde, _ = dengeli_blok(js, eslesme.end() - 1)
    return re.findall(r"['\"]([^'\"]+)['\"]", govde)


def console_argumanlari(js):
    argumanlar = []
    for eslesme in re.finditer(r"console\.(?:log|error|warn)\s*\(", js):
        govde, _ = dengeli_blok(js, eslesme.end() - 1)
        argumanlar.append(govde)
    return argumanlar


def stringleri_sil(metin):
    sonuc = []
    indis = 0
    tirnak = None
    kacis = False
    while indis < len(metin):
        karakter = metin[indis]
        if tirnak:
            if kacis:
                kacis = False
            elif karakter == "\\":
                kacis = True
            elif karakter == tirnak:
                tirnak = None
            sonuc.append(" ")
            indis += 1
            continue
        if karakter in ("'", '"', "`"):
            tirnak = karakter
            sonuc.append(" ")
        else:
            sonuc.append(karakter)
        indis += 1
    return "".join(sonuc)


def talep_fonksiyonu(js, ad):
    eslesme = re.search(r"function\s+" + re.escape(ad) + r"\s*\(", js)
    if not eslesme:
        return ""
    govde, _ = dengeli_blok(js, js.find("{", eslesme.end()))
    return govde


def kaynak_taramasi(sql, js, uretim_dosyalar=None):
    kolonlar = talepler_kolonlari(sql)
    izinliler = izinli_liste_elemanlari(js)
    alan_kullanimi = set()
    for arguman in console_argumanlari(js):
        alan_kullanimi.update(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", stringleri_sil(arguman)))
    wa = talep_fonksiyonu(js, "waAdresi")
    wa_ident = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", stringleri_sil(wa)))
    beklenen = ["kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website"]
    c1 = bool(kolonlar) and not bool(set(kolonlar) & PIS)
    c2 = izinliler == beklenen and not bool(set(izinliler) & PIS)
    c3 = not bool(alan_kullanimi & ALANLAR)
    c4 = "encodeURIComponent" in wa and "kod" in wa_ident and not bool(wa_ident & ALANLAR)
    c5 = True
    for yol, metin in (uretim_dosyalar or []):
        if "4005" in metin:
            c5 = False
        for satir in metin.splitlines():
            if "905451386526" in satir and "wa.me" not in satir:
                c5 = False
    return {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5}


def uretim_dosyalari(sql, js):
    return [("tools/d1-sema.sql", sql), ("shop/src/talep.js", js),
            ("shop/src/index.js", (ROOT / "shop" / "src" / "index.js").read_text(encoding="utf-8"))]


def kod_ekseni(source_path):
    ifade = (
        "import { pathToFileURL } from 'node:url';"
        "const m=await import(pathToFileURL(process.argv[1]).href);"
        "const s=new Set();let yasak=false;let bicim=true;"
        "for(let i=0;i<100000;i++){const k=m.talepKoduUret();"
        "if(s.has(k))yasak=true;s.add(k);"
        "if(!m.TALEP_KOD_RE.test(k))bicim=true;}"
        "console.log(JSON.stringify({say:iym=s.size, bicim:!yasak, regex:bicim}));"
    )
    # Kod uzunlugunu ve yasak karakterleri ayri ve deterministik olcmek icin tek kosum.
    ifade = (
        "import { pathToFileURL } from 'node:url';"
        "const m=await import(pathToFileURL(process.argv[1]).href);"
        "const s=new Set();let tekrar=false;let yasak=false;let bicim=true;"
        "for(let i=0;i<100000;i++){const k=m.talepKoduUret();if(s.has(k))tekrar=true;s.add(k);"
        "if(/[01ILOU]/.test(k))yasak=true;if(!m.TALEP_KOD_RE.test(k))bicim=false;}"
        "console.log(JSON.stringify({say:s.size,tekrar,yasak,bicim}));"
    )
    sonuc = subprocess.run([NODE, "--input-type=module", "-e", ifade, str(source_path)],
                           cwd=ROOT, capture_output=True, text=True)
    if sonuc.returncode != 0:
        return {"A1": False, "A2": False, "A3": False, "A4": False}, sonuc
    try:
        veri = json.loads(sonuc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"A1": False, "A2": False, "A3": False, "A4": False}, sonuc
    kaynak = Path(source_path).read_text(encoding="utf-8")
    iddialar = {
        "A1": veri.get("say") == 100000 and not veri.get("tekrar"),
        "A2": not veri.get("yasak"),
        "A3": bool(veri.get("bicim")),
        "A4": "Math.random" not in kaynak and "crypto.getRandomValues" in kaynak,
    }
    return iddialar, sonuc


def node_test(hedef=None, sizinti=False, source_path=None):
    komut = [NODE, str(TEST)]
    if sizinti:
        komut.append("--sizinti")
    if hedef:
        komut.append("--only=" + hedef)
    ortam = os.environ.copy()
    if source_path:
        ortam["TALEP_SOURCE"] = str(source_path)
    sonuc = subprocess.run(komut, cwd=ROOT, env=ortam, capture_output=True, text=True)
    eslesme = re.search(r"GECEN=(\d+) DUSEN=(\d+)", sonuc.stdout)
    if not eslesme:
        return False, sonuc, None
    gecen = int(eslesme.group(1))
    dusen = int(eslesme.group(2))
    beklenen = gecen == 1 if hedef else gecen > 0
    return sonuc.returncode == 0 and dusen == 0 and beklenen, sonuc, (gecen, dusen)


def mutasyonlar(js, sql):
    return {
        "A1": (js.replace('  return kod;\n}\n\nfunction benzersizCakisma',
                           '  return "PR-234567";\n}\n\nfunction benzersizCakisma', 1), js, "kod"),
        "A2": (js.replace('export const TALEP_ALFABE = "23456789ABCDEFGHJKMNPQRSTVWXYZ";',
                           'export const TALEP_ALFABE = "023456789ABCDEFGHJKMNPQRSTVWXYZ";', 1), js, "kod"),
        "A3": (js.replace('  let kod = "PR-";', '  let kod = "PX-";', 1), js, "kod"),
        "A4": (js.replace('crypto.getRandomValues(bayt);', 'Math.random();', 1), js, "kod"),
        "B1": (js.replace('"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",',
                           '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website", "telefon",', 1), js, "node"),
        "B2": (js.replace('if (govde.website !== undefined && govde.website !== "") { return gecersiz(); }',
                           'if (false) { return gecersiz(); }', 1), js, "node"),
        "B3": (js.replace('new TextEncoder().encode(metin).length', 'metin.length', 1), js, "node"),
        "B4": (js.replace('if (!headers || typeof headers.get !== "function") { return false; }',
                           'if (!headers || typeof headers.get !== "function") { return true; }', 1), js, "node"),
        "B5": (js.replace('if (origin) { return izin.has(origin); }', 'if (origin) { return true; }', 1), js, "node"),
        "C1": (js, sql.replace('  notu            TEXT,', '  notu            TEXT,\n  telefon         TEXT,', 1), "source"),
        "C2": (js.replace('"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",',
                           '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website", "telefon",', 1), sql, "source"),
        "C3": (js.replace('function hataSinifi(hata) {', 'function hataSinifi(hata) {\n  console.error("alan:", govde.kategori);', 1), sql, "source"),
        "C4": (js.replace('return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod);',
                           'return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod + govde.kategori);', 1), sql, "source"),
        "C5": (js.replace('https://wa.me/905451386526', 'https://wa.me/4005', 1), sql, "source"),
        "D1": (js.replace('return cevap({ kod, wa: waAdresi(kod) }, 200);', 'return cevap({ kod }, 200);', 1), sql, "node"),
        "D2": (js.replace('return cevap({ hata: "gecersiz", wa: WA_BASE }, status);',
                           'return cevap({ hata: "kural", wa: WA_BASE }, status);', 1), sql, "node"),
        "D3": (js.replace('return cevap({ kod: null, wa: WA_BASE }, 200);',
                           'return cevap({ kod: null, wa: WA_BASE }, 500);', 1), sql, "node"),
        "D4": (js.replace('deneme < 5', 'deneme < 4', 1), sql, "node"),
        "E1": (js.replace('if (!KANALLAR.has(govde.kanal)) { return false; }',
                           'if (!KANALLAR.has(govde.kanal)) { return true; }', 1), sql, "node"),
        "E2": (js.replace('govde[alan].length > tavan', 'govde[alan].length > tavan + 1', 1), sql, "node"),
    }


def mutant_sonuclari(temel_js, temel_sql, isimler):
    hepsi = mutasyonlar(temel_js, temel_sql)
    yakalandi = 0
    kontrol = 0
    for isim in isimler:
        mutant_js, mutant_sql, tur = hepsi[isim]
        if tur == "talep":
            with tempfile.TemporaryDirectory(prefix="k186-mutant-") as gecici:
                yol = Path(gecici) / "talep.js"
                yol.write_text(mutant_js, encoding="utf-8")
                base_ok, base_sonuc, _ = node_test(isim, source_path=TALEP)
                mutant_ok, mutant_sonuc, _ = node_test(isim, source_path=yol)
        elif tur == "node":
            with tempfile.TemporaryDirectory(prefix="k186-mutant-") as gecici:
                yol = Path(gecici) / "talep.js"
                yol.write_text(mutant_js, encoding="utf-8")
                base_ok, base_sonuc, _ = node_test(isim, source_path=TALEP)
                mutant_ok, mutant_sonuc, _ = node_test(isim, source_path=yol)
        elif tur == "kod":
            with tempfile.TemporaryDirectory(prefix="k186-mutant-") as gecici:
                yol = Path(gecici) / "talep.js"
                yol.write_text(mutant_js, encoding="utf-8")
                base_iddialar, base_sonuc = kod_ekseni(TALEP)
                mutant_iddialar, mutant_sonuc = kod_ekseni(yol)
                base_ok = bool(base_iddialar.get(isim))
                mutant_ok = bool(mutant_iddialar.get(isim))
        else:
            temel = kaynak_taramasi(temel_sql, temel_js, uretim_dosyalari(temel_sql, temel_js))
            mutant = kaynak_taramasi(mutant_sql, mutant_js, uretim_dosyalari(mutant_sql, mutant_js))
            base_ok = bool(temel.get(isim))
            mutant_ok = bool(mutant.get(isim))
            base_sonuc = subprocess.CompletedProcess(["kaynak-taramasi", isim], 0, "base=" + str(base_ok), "")
            mutant_sonuc = subprocess.CompletedProcess(["kaynak-taramasi", isim], 0, "mutant=" + str(mutant_ok), "")
        kontrol += int(base_ok)
        yakalandi += int(base_ok and not mutant_ok)
        if tur in ("kod", "talep", "node"):
            ham = (mutant_sonuc.stdout + mutant_sonuc.stderr).replace("\n", "\\n")
            print("MUTANT " + isim + " komut=" + " ".join(mutant_sonuc.args) +
                  " rc=" + str(mutant_sonuc.returncode) + " ham=" + ham, file=sys.stderr)
    return yakalandi, kontrol, len(isimler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizinti", action="store_true")
    args = parser.parse_args()
    js = TALEP.read_text(encoding="utf-8")
    sql = SEMA.read_text(encoding="utf-8")
    iddialar = SIZINTI_IDDIALAR if args.sizinti else IDDIALAR
    sonuclar = {}

    node_sonuc, _, node_olcu = node_test(sizinti=args.sizinti)
    if node_olcu:
        gecen, dusen = node_olcu
        for ad in iddialar:
            if ad.startswith(("B", "D", "E")):
                sonuclar[ad] = ad in SIZINTI_IDDIALAR[:5] if args.sizinti else True
        if dusen:
            # Ayrintili adlar stdout'ta bulunur; parse edilemeyen durum fail-closed kalir.
            for ad in ["B1", "B2", "B3", "B4", "B5", "D1", "D2", "D3", "D4", "E1", "E2"]:
                if ad in sonuclar and re.search(r"❌ " + ad + r"\b", _.stdout):
                    sonuclar[ad] = False
    else:
        for ad in iddialar:
            if ad.startswith(("B", "D", "E")):
                sonuclar[ad] = False

    if not args.sizinti:
        a_sonuclar, _ = kod_ekseni(TALEP)
        sonuclar.update(a_sonuclar)
    kaynak = kaynak_taramasi(sql, js, uretim_dosyalari(sql, js))
    sonuclar.update(kaynak)
    for ad in iddialar:
        sonuclar.setdefault(ad, False)

    mutant, kontrol, toplam_mutant = mutant_sonuclari(js, sql, iddialar)
    dusen_sayisi = sum(1 for ad in iddialar if not sonuclar[ad])
    print("IDDIA=" + str(len(iddialar)) + " DUSEN=" + str(dusen_sayisi) +
          " MUTANT=" + str(mutant) + "/" + str(toplam_mutant) +
          " KONTROL=" + str(kontrol) + "/" + str(toplam_mutant))
    return 1 if dusen_sayisi or mutant != toplam_mutant or kontrol != toplam_mutant or not node_sonuc else 0


if __name__ == "__main__":
    sys.exit(main())
