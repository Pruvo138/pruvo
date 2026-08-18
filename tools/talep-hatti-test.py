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
import shutil
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
    "K1", "K2", "K3", "K4", "K5",
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
    # A1 kabul vekili: 30 tabanli sayaç 100.000 farkli kodu deterministik üretir;
    # gerçek crypto yolu bu mutasyon bataryasinda A4 ile ayrıca korunur.
    ifade = (
        "import { pathToFileURL } from 'node:url';"
        "const c=globalThis.crypto;const eski=c.getRandomValues;let cagri=0;"
        "c.getRandomValues=(bayt)=>{const kod=Math.floor(cagri/6);"
        "const konum=cagri%6;const hane=Math.floor(kod/(30**(5-konum)))%30;"
        "bayt[0]=hane;cagri++;return bayt;};"
        "const m=await import(pathToFileURL(process.argv[1]).href);"
        "const s=new Set();let tekrar=false;let yasak=false;let bicim=true;"
        "for(let i=0;i<100000;i++){const k=m.talepKoduUret();if(s.has(k))tekrar=true;s.add(k);"
        "if(/[01ILOU]/.test(k))yasak=true;if(!m.TALEP_KOD_RE.test(k))bicim=false;}"
        "c.getRandomValues=eski;console.log(JSON.stringify({say:s.size,tekrar,yasak,bicim}));"
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
        return False, sonuc, None, {}
    gecen = int(eslesme.group(1))
    dusen = int(eslesme.group(2))
    iddialar = {}
    for satir in sonuc.stdout.splitlines():
        es = re.search(r"(?:✅|DUSEN:|❌)\s*([A-Z][0-9]+)", satir)
        if es:
            iddialar[es.group(1)] = satir.startswith("  ✅")
    beklenen = gecen == 1 if hedef else gecen > 0
    return sonuc.returncode == 0 and dusen == 0 and beklenen, sonuc, (gecen, dusen), iddialar


def tek_mutasyon(metin, arama, degisim):
    if metin.count(arama) != 1:
        raise ValueError("mutasyon capasi benzersiz degil: " + arama)
    return metin.replace(arama, degisim, 1)


def mutasyonlar(js, sql):
    return {
        "A1": (tek_mutasyon(js, "  return kod;\n}\n\nfunction benzersizCakisma",
                             '  return "PR-234567";\n}\n\nfunction benzersizCakisma'),
                js, "kod", 'return "PR-234567";'),
        "A2": (tek_mutasyon(js, 'export const TALEP_ALFABE = "23456789ABCDEFGHJKMNPQRSTVWXYZ";',
                             'export const TALEP_ALFABE = "023456789ABCDEFGHJKMNPQRSTVWXYZ";'),
                js, "kod", 'export const TALEP_ALFABE = "023456789ABCDEFGHJKMNPQRSTVWXYZ";'),
        "A3": (tek_mutasyon(js, '  let kod = "PR-";', '  let kod = "PX-";'), js, "kod", 'let kod = "PX-";'),
        "A4": (tek_mutasyon(js, "    do { crypto.getRandomValues(bayt); } while (bayt[0] >= kabulSiniri);",
                             "    do { bayt[0] = Math.floor(Math.random() * kabulSiniri); } while (bayt[0] >= kabulSiniri);"),
                js, "kod", "Math.random()"),
        "B1": (tek_mutasyon(js, '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",',
                             '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website", "telefon",'),
                js, "node", '"website", "telefon"'),
        "B2": (tek_mutasyon(js, 'if (govde.website !== undefined && govde.website !== "") { return gecersiz(); }',
                             'if (false) { return gecersiz(); }'), js, "node", "if (false)"),
        "B3": (tek_mutasyon(js, 'if (new TextEncoder().encode(metin).length > GOVDE_BAYT_TAVANI) { return gecersiz(); }',
                             'if (false) { return gecersiz(); }'), js, "node", "if (false)"),
        "B4": (tek_mutasyon(js, '  const referer = birHost(headers.get("Referer"));\n  if (referer) { return izin.has(referer); }\n  return false;',
                             '  const referer = birHost(headers.get("Referer"));\n  if (referer) { return izin.has(referer); }\n  return true;'),
                js, "node", "return true;"),
        "B5": (tek_mutasyon(js, 'if (origin) { return izin.has(origin); }', 'if (origin) { return true; }'),
                js, "node", 'if (origin) { return true; }'),
        "C1": (js, tek_mutasyon(sql, '  notu            TEXT,', '  notu            TEXT,\n  telefon         TEXT,'), "source", "  telefon         TEXT,"),
        "C2": (tek_mutasyon(js, '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",',
                             '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website", "telefon",'),
                sql, "source", '"website", "telefon"'),
        "C3": (tek_mutasyon(js, 'function hataSinifi(hata) {', 'function hataSinifi(hata) {\n  console.error("alan:", govde.kategori);'),
                sql, "source", 'console.error("alan:", govde.kategori)'),
        "C4": (tek_mutasyon(js, 'return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod);',
                             'return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod + govde.kategori);'),
                sql, "source", "govde.kategori"),
        "C5": (tek_mutasyon(js, 'https://wa.me/905451386526', 'https://wa.me/4005'), sql, "source", "https://wa.me/4005"),
        "D1": (tek_mutasyon(js, 'return cevap({ kod, wa: waAdresi(kod) }, 200);', 'return cevap({ kod }, 200);'),
                sql, "node", "return cevap({ kod }, 200);"),
        "D2": (tek_mutasyon(js, 'return cevap({ hata: "gecersiz", wa: WA_BASE }, status);',
                             'return cevap({ hata: "kural", wa: WA_BASE }, status);'), sql, "node", 'hata: "kural"'),
        "D3": (tek_mutasyon(js, 'return cevap({ kod: null, wa: WA_BASE }, 200);',
                             'return cevap({ kod: null, wa: WA_BASE }, 500);'), sql, "node", "}, 500);"),
        "D4": (tek_mutasyon(js, 'benzersizCakisma(e) && deneme < 4',
                             'benzersizCakisma(e) && deneme < 3'), sql, "node", "deneme < 3"),
        "E1": (tek_mutasyon(js, 'if (!KANALLAR.has(govde.kanal)) { return false; }',
                             'if (!KANALLAR.has(govde.kanal)) { return true; }'), sql, "node", "return true;"),
        "E2": (tek_mutasyon(js, 'govde[alan].length > tavan', 'govde[alan].length > tavan + 1'), sql, "node", "tavan + 1"),
        "K1": (tek_mutasyon(js, 'if (!govde || typeof govde !== "object" || Array.isArray(govde)) { return gecersiz(); }',
                             'if (false) { return gecersiz(); }'), sql, "node", "if (false)"),
        "K2": (tek_mutasyon(js, 'govde.kanal, govde.kategori ?? null, govde.marka ?? null,\n        govde.model ?? null, govde.yil ?? null, govde.parca_adi ?? null, govde.notu ?? null',
                             'govde.kanal, govde.kategori, govde.marka,\n        govde.model, govde.yil, govde.parca_adi, govde.notu'), sql, "node", "govde.kategori, govde.marka,"),
        "K3": (tek_mutasyon(js, 'return metin.includes("UNIQUE") || metin.includes("PRIMARY KEY");',
                             'return metin.includes("UNIQUE") || metin.includes("PRIMARY KEY") || metin.includes("CONSTRAINT");'),
                sql, "node", 'metin.includes("CONSTRAINT")'),
        "K4": (tek_mutasyon(js, '  }\n}\n\nexport { ALAN_TAVANLARI',
                             '  }\n  console.error("talep kod cakismasi: tekrar siniri");\n}\n\nexport { ALAN_TAVANLARI'),
                sql, "node", "tekrar siniri"),
        "K5": (tek_mutasyon(js, '  if (contentLength !== null && Number.isFinite(Number(contentLength)) &&\n      Number(contentLength) > GOVDE_BAYT_TAVANI) { return gecersiz(); }',
                             '  if (false) { return gecersiz(); }'), sql, "node", "if (false)"),
    }


def temizle_pycache():
    for yol in ROOT.rglob("__pycache__"):
        shutil.rmtree(yol, ignore_errors=True)


def mutant_sonuclari(temel_js, temel_sql, isimler):
    hepsi = mutasyonlar(temel_js, temel_sql)
    yakalandi = 0
    kontrol = 0
    for isim in isimler:
        mutant_js, mutant_sql, tur, kanit = hepsi[isim]
        gecici = Path(tempfile.mkdtemp(prefix="k186-mutant-"))
        try:
            yol = gecici / "talep.js"
            yol.write_text(mutant_js, encoding="utf-8")
            kanitli_js = yol.read_text(encoding="utf-8")
            uygulandi = kanit in (kanitli_js + mutant_sql)
            if not uygulandi:
                raise ValueError("mutasyon dosyaya girmedi: " + isim)

            if tur == "node":
                base_ok, base_sonuc, _, _ = node_test(isim, source_path=TALEP)
                mutant_ok, mutant_sonuc, _, _ = node_test(isim, source_path=yol)
            elif tur == "kod":
                base_iddialar, base_sonuc = kod_ekseni(TALEP)
                mutant_iddialar, mutant_sonuc = kod_ekseni(yol)
                base_ok = bool(base_iddialar.get(isim))
                mutant_ok = bool(mutant_iddialar.get(isim))
            else:
                temel = kaynak_taramasi(temel_sql, temel_js, uretim_dosyalari(temel_sql, temel_js))
                mutant = kaynak_taramasi(mutant_sql, mutant_js, uretim_dosyalari(mutant_sql, mutant_js))
                base_ok = bool(temel.get(isim))
                mutant_ok = bool(mutant.get(isim))
                base_sonuc = subprocess.CompletedProcess(["kaynak-taramasi", isim], 0,
                                                          "base=" + str(base_ok), "")
                mutant_sonuc = subprocess.CompletedProcess(["kaynak-taramasi", isim], 0,
                                                            "mutant=" + str(mutant_ok), "")
            kontrol += int(base_ok)
            tek_iddia = base_ok and not mutant_ok
            yakalandi += int(tek_iddia)
            if tur in ("kod", "node"):
                ham = (mutant_sonuc.stdout + mutant_sonuc.stderr).replace("\n", "\\n")
                print("MUTANT " + isim + " komut=" + " ".join(mutant_sonuc.args) +
                      " rc=" + str(mutant_sonuc.returncode) + " ham=" + ham +
                      " dusen_iddia=" + (isim if tek_iddia else "YOK") +
                      " mutasyon_kaynaga_girdi=" + str(uygulandi), file=sys.stderr)
            else:
                print("MUTANT " + isim + " komut=kaynak-taramasi rc=0 ham=" +
                      mutant_sonuc.stdout + " dusen_iddia=" + (isim if tek_iddia else "YOK") +
                      " mutasyon_kaynaga_girdi=" + str(uygulandi), file=sys.stderr)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
            temizle_pycache()
    return yakalandi, kontrol, len(isimler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizinti", action="store_true")
    args = parser.parse_args()
    js = TALEP.read_text(encoding="utf-8")
    sql = SEMA.read_text(encoding="utf-8")
    iddialar = SIZINTI_IDDIALAR if args.sizinti else IDDIALAR
    sonuclar = {}

    node_sonuc, node_cikti, node_olcu, node_iddialar = node_test(sizinti=args.sizinti)
    if node_olcu:
        gecen, dusen = node_olcu
        for ad in iddialar:
            if ad in node_iddialar:
                sonuclar[ad] = node_iddialar[ad]
    else:
        for ad in iddialar:
            if ad.startswith(("B", "D", "E", "K")):
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
