#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K186 talep hatti kabul, kaynak ve mutasyon kapisi.

Her iddia ayri eksenle olculur. Mutantlar gecici dosyaya yazilir, hedef iddia
`--only` ile izole kosulur ve kaynak capasi diske girdigi sayiyla basilir.
"""

import argparse
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
TEMIZLIK = ROOT / "tools" / "talep-temizlik.py"
NODE = "node"

BEKLENEN_IDDIA = 50
BEKLENEN_IDDIA_SIZINTI = 14
IDDIALAR = [
    "A1", "A2", "A3", "A4", "A5", "A6", "A7",
    "B1", "B2", "B3", "B4", "B5",
    "C1", "C2", "C3", "C4", "C5",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12",
    "E1", "E2", "E3",
    "F5",
    "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11",
    "K1", "K2", "K3", "K4", "K5", "R1",
]
SIZINTI_IDDIALAR = ["B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4", "C5", "D6", "D7", "D8", "D11"]
PIS = {"telefon", "tel", "email", "eposta", "ad", "adres", "address"}
ALANLAR = {"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website"}
KANONIK_WA_NUMARASI = "90545" + "1386526"


def dengeli_blok(metin, baslangic):
    acik = metin[baslangic]
    kapanis = {"[": "]", "(": ")", "{": "}"}[acik]
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
        elif karakter == acik:
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
    sonuc = []
    for eslesme in re.finditer(r"console\.(?:log|error|warn)\s*\(", js):
        govde, _ = dengeli_blok(js, eslesme.end() - 1)
        sonuc.append(govde)
    return sonuc


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
        elif karakter in ("'", '"', "`"):
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


def telefon_ihlali(metin):
    """Numarayi yalniz kanonik telefon baglaminda kontrol eder."""
    for eslesme in re.finditer(re.escape(KANONIK_WA_NUMARASI) + r"|4005", metin):
        baglam = metin[max(0, eslesme.start() - 100):eslesme.end() + 100]
        numara = eslesme.group(0)
        if numara == "4005" and ("wa.me" in baglam or "tel:" in baglam or "contactPoint" in baglam):
            return True
        if numara == KANONIK_WA_NUMARASI and ("tel:" in baglam or "contactPoint" in baglam):
            return True
    return False


def yil_sayisal_karsilastirma(sql):
    yorum_suzulmus = re.sub(r"--[^\n]*", "", sql)
    for ifade in yorum_suzulmus.split(";"):
        if "talepler" not in ifade.lower():
            continue
        if re.search(r"\byil\b\s*(?:<=|>=|<>|=|<|>)", ifade, re.I):
            return True
        if re.search(r"\bBETWEEN\b[^;]*\byil\b|\byil\b[^;]*\bBETWEEN\b", ifade, re.I):
            return True
        if re.search(r"CAST\s*\([^)]*\byil\b[^)]*AS\s+INTEGER", ifade, re.I):
            return True
    return False


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
    c5 = all(not telefon_ihlali(metin) for _, metin in (uretim_dosyalar or []))
    return {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5,
            "E3": not yil_sayisal_karsilastirma(sql),
            "G11": len(re.findall(r"(?:export\s+)?const\s+ALAN_TAVANLARI\s*=", js)) == 1,
            "G6": not telefon_ihlali("id=4005 tarih=2026"),
            "G7": telefon_ihlali("https://wa.me/4005"),
            "R1": temizlik_kaynak_kontrolu(TEMIZLIK.read_text(encoding="utf-8"))[0]}


def uretim_dosyalari(sql, js):
    return [("tools/d1-sema.sql", sql), ("shop/src/talep.js", js),
            ("shop/src/index.js", (ROOT / "shop" / "src" / "index.js").read_text(encoding="utf-8"))]


def temizlik_kaynak_kontrolu(metin):
    imza = bool(re.search(r"def\s+sil_eski\s*\(\s*baglanti\s*,\s*kodlar\s*\)", metin))
    calistir = re.search(r"def\s+calistir\s*\(.*?\n(?=def\s|if __name__)", metin, re.S)
    govde = calistir.group(0) if calistir else ""
    tek_liste = "sil_eski(baglanti, kodlar)" in govde
    return imza and tek_liste, imza, tek_liste


def node_test(hedef=None, sizinti=False, source_path=None, test_path=None):
    komut = [NODE, str(test_path or TEST)]
    if sizinti:
        komut.append("--sizinti")
    if hedef:
        komut.append("--only=" + hedef)
    ortam = dict(__import__("os").environ)
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
    beklenen = [hedef] if hedef else (SIZINTI_IDDIALAR if sizinti else IDDIALAR)
    eksik = [ad for ad in beklenen if ad not in iddialar]
    ok = sonuc.returncode == 0 and dusen == 0 and gecen == len(beklenen) and not eksik
    return ok, sonuc, (gecen, dusen), iddialar


def tek_mutasyon(metin, arama, degisim):
    sayi = metin.count(arama)
    if sayi != 1:
        raise ValueError("mutasyon capasi benzersiz degil: " + arama + " sayi=" + str(sayi))
    return metin.replace(arama, degisim, 1)


def mutasyonlar(js, sql, temizlik, test):
    return {
        "A1": (tek_mutasyon(js, '    kod += TALEP_ALFABE[bayt[0] % TALEP_ALFABE.length];', '    kod += "2";'), js, "node", 'kod += "2";'),
        "A2": (tek_mutasyon(js, 'export const TALEP_ALFABE = "23456789ABCDEFGHJKMNPQRSTVWXYZ";', 'export const TALEP_ALFABE = "023456789ABCDEFGHJKMNPQRSTVWXYZ";'), js, "node", 'export const TALEP_ALFABE = "023456789ABCDEFGHJKMNPQRSTVWXYZ";'),
        "A3": (tek_mutasyon(js, '  let kod = "PR-";', '  let kod = "PX-";'), js, "node", 'let kod = "PX-";'),
        "A4": (tek_mutasyon(js, 'do { crypto.getRandomValues(bayt); }', 'do { Math.random(); }'), js, "node", 'do { Math.random(); }'),
        "A5": (tek_mutasyon(js, 'bayt[0] >= kabulSiniri', 'bayt[0] >= 256'), js, "node", 'bayt[0] >= 256'),
        "A6": (tek_mutasyon(js, 'Math.floor(256 / TALEP_ALFABE.length) * TALEP_ALFABE.length', '256'), js, "node", 'const kabulSiniri = 256;'),
        "A7": (tek_mutasyon(js, 'TALEP_ALFABE[bayt[0] % TALEP_ALFABE.length]', '"0"'), js, "node", 'kod += "0";'),
        "B1": (tek_mutasyon(js, '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",', '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website", "telefon",'), js, "node", '"website", "telefon"'),
        "B2": (tek_mutasyon(js, 'if (govde.website !== undefined && govde.website !== "") { return gecersiz(); }', 'if (false) { return gecersiz(); }'), js, "node", 'if (false) { return gecersiz(); }'),
        "B3": (tek_mutasyon(js, 'if (new TextEncoder().encode(metin).length > GOVDE_BAYT_TAVANI) { return gecersiz(); }', 'if (false) { return gecersiz(); } /* B3_MUTANT */'), js, "node", 'B3_MUTANT'),
        "B4": (tek_mutasyon(js, '  return false;\n}\n\n/** Binding yok', '  return true;\n}\n\n/** Binding yok'), js, "node", 'return true;\n}\n\n/** Binding yok'),
        "B5": (tek_mutasyon(js, 'if (origin) { return izin.has(origin); }', 'if (origin) { return true; }'), js, "node", 'if (origin) { return true; }'),
        "C1": (js, tek_mutasyon(sql, '  notu            TEXT,', '  notu            TEXT,\n  telefon         TEXT,'), "source", '  telefon         TEXT,'),
        "C2": (tek_mutasyon(js, '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",', '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website", "telefon",'), sql, "source", '"website", "telefon"'),
        "C3": (tek_mutasyon(js, 'function hataSinifi(hata) {', 'function hataSinifi(hata) {\n  console.error("alan:", govde.kategori);'), sql, "source", 'console.error("alan:", govde.kategori)'),
        "C4": (tek_mutasyon(js, 'return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod);', 'return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod + govde.kategori);'), sql, "source", 'govde.kategori);'),
        "C5": (tek_mutasyon(js, 'https://wa.me/905451386526', 'https://wa.me/4005'), sql, "source", 'https://wa.me/4005'),
        "D1": (tek_mutasyon(js, 'return cevap({ kod, wa: waAdresi(kod) }, 200);', 'return cevap({ kod }, 200);'), sql, "node", 'return cevap({ kod }, 200);'),
        "D2": (tek_mutasyon(js, 'return cevap({ hata: "gecersiz", wa: WA_BASE }, status);', 'return cevap({ hata: "kural", wa: WA_BASE }, status);'), sql, "node", 'hata: "kural"'),
        "D3": (tek_mutasyon(js, 'talepOlayiSay(env, benzersizCakisma(e) ? "kod_cakisma" : "d1_hata");\n      return cevap({ kod: null, wa: waOzeti(govde) }, 200);', 'talepOlayiSay(env, benzersizCakisma(e) ? "kod_cakisma" : "d1_hata");\n      return cevap({ kod: null, wa: WA_BASE }, 200); // D3_MUTANT'), sql, "node", 'D3_MUTANT'),
        "D4": (tek_mutasyon(js, 'benzersizCakisma(e) && deneme < 4', 'benzersizCakisma(e) && deneme < 3'), sql, "node", 'deneme < 3'),
        "D5": (tek_mutasyon(js, 'return WA_BASE + "?text=" + encodeURIComponent(metin);', 'return WA_BASE;'), sql, "node", 'return WA_BASE;'),
        "D6": (tek_mutasyon(js, 'return cevap({ kod, wa: waAdresi(kod) }, 200);', 'return cevap({ kod, wa: waOzeti(govde) }, 200); // D6_MUTANT'), sql, "node", '// D6_MUTANT'),
        "D7": (tek_mutasyon(js, 'return cevap({ hata: "gecersiz", wa: WA_BASE }, status);', 'return cevap({ hata: "gecersiz", wa: waAdresi("RED") }, status);'), sql, "node", 'wa: waAdresi("RED")'),
        "D8": (tek_mutasyon(js, 'const temiz = deger.replace(/[\\u0000-\\u001f\\u007f]/gu, " ").replace(/\\s+/gu, " ").trim();', 'const temiz = deger;'), sql, "node", 'const temiz = deger;'),
        "D9": (tek_mutasyon(js, 'talepOlayiSay(env, benzersizCakisma(e) ? "kod_cakisma" : "d1_hata");', 'talepOlayiSay(env, benzersizCakisma(e) ? "kod_cakisma" : "yapilandirma"); // D9_MUTANT'), sql, "node", 'D9_MUTANT'),
        "D10": (tek_mutasyon(js, 'talepOlayiSay(env, benzersizCakisma(e) ? "kod_cakisma" : "d1_hata");', 'talepOlayiSay(env, benzersizCakisma(e) ? "d1_hata" : "d1_hata");'), sql, "node", 'benzersizCakisma(e) ? "d1_hata" : "d1_hata"'),
        "D11": (tek_mutasyon(js, 'console.error("talep_kod_uretilemedi sebep=" + sebep + " zaman=" + new Date().toISOString());', 'console.error("talep_kod_uretilemedi ZZQX-SIZINTI-CAPASI sebep=" + sebep + " zaman=" + new Date().toISOString());'), sql, "node", 'ZZQX-SIZINTI-CAPASI'),
        "D12": (tek_mutasyon(js, 'talepOlayiSay(env, "yapilandirma");', 'talepOlayiSay(env, "d1_hata");'), sql, "node", 'talepOlayiSay(env, "d1_hata");'),
        "E1": (tek_mutasyon(js, 'if (!KANALLAR.has(govde.kanal)) { return false; }', 'if (!KANALLAR.has(govde.kanal)) { return true; }'), sql, "node", 'if (!KANALLAR.has(govde.kanal)) { return true; }'),
        "E2": (tek_mutasyon(js, 'govde[alan].length > tavan', 'govde[alan].length > tavan + 1'), sql, "node", 'tavan + 1'),
        "E3": (js, tek_mutasyon(sql, 'CREATE INDEX IF NOT EXISTS talepler_durum', 'SELECT yil FROM talepler WHERE yil > 2010;\nCREATE INDEX IF NOT EXISTS talepler_durum'), "source", 'SELECT yil FROM talepler WHERE yil > 2010;'),
        "F5": (tek_mutasyon(temizlik, 'f5 = sil_eski.__code__.co_argcount == 2 and "silinecek_kodlar" not in sil_eski.__code__.co_names', 'f5 = False'), temizlik, "temizlik", 'f5 = False'),
        "G1": (tek_mutasyon(js, 'govde.kanal, govde.kategori ?? null, govde.marka ?? null,', 'govde.kanal, govde.kategori, govde.marka,'), sql, "node", 'govde.kategori, govde.marka,'),
        "G2": (tek_mutasyon(js, 'if (contentLength !== null && Number.isFinite(Number(contentLength)) &&\n      Number(contentLength) > GOVDE_BAYT_TAVANI) { return gecersiz(); }', 'if (false) { return gecersiz(); } /* G2_MUTANT */'), sql, "node", 'G2_MUTANT'),
        "G3": (tek_mutasyon(js, 'metin = await request.text();', 'metin = "";'), sql, "node", 'metin = "";'),
        "G4": (tek_mutasyon(js, 'if (new TextEncoder().encode(metin).length > GOVDE_BAYT_TAVANI) { return gecersiz(); }', 'if (false) { return gecersiz(); } /* G4_MUTANT */'), sql, "node", 'G4_MUTANT'),
        "G5": (tek_mutasyon(test, 'await iddia("G5", async () => {\n  return true;\n});', ''), sql, "test", 'await iddia("G5"'),
        "G6": (tek_mutasyon(Path(__file__).read_text(encoding="utf-8"), 'if numara == "4005" and ' + '("wa.me" in baglam or "tel:" in baglam or "contactPoint" in baglam):', 'if numara == "4005" and ("wa.me" not in baglam and "tel:" not in baglam and "contactPoint" not in baglam):'), sql, "phone", 'if numara == "4005" and ("wa.me" not in baglam'),
        "G7": (tek_mutasyon(Path(__file__).read_text(encoding="utf-8"), 'return telefon_ihlali(' + '"https://wa.me/4005")', 'return not telefon_ihlali("https://wa.me/4005")'), sql, "phone7", 'return not telefon_ihlali("https://wa.me/4005")'),
        "G8": (tek_mutasyon(js, 'if (origin) { return izin.has(origin); }', 'if (origin) { return false; }'), sql, "node", 'if (origin) { return false; }'),
        "G9": (tek_mutasyon(js, 'if (referer) { return izin.has(referer); }', 'if (referer) { return false; }'), sql, "node", 'if (referer) { return false; }'),
        "G10": (tek_mutasyon(js, 'if (h) { set.add(h); }', 'if (false) { set.add(h); }'), sql, "node", 'set.add(h)'),
        "G11": (tek_mutasyon(js, 'export const ALAN_TAVANLARI = Object.freeze({', 'export const ALAN_TAVANLARI = Object.freeze({\nconst ALAN_TAVANLARI = {};'), sql, "source", 'const ALAN_TAVANLARI = {};'),
        "K1": (tek_mutasyon(js, 'if (!alanlarGecerli(govde)) { return gecersiz(); }', 'if (false) { return gecersiz(); }'), sql, "node", 'if (false) { return gecersiz(); }'),
        "K2": (tek_mutasyon(js, 'govde.kanal, govde.kategori ?? null, govde.marka ?? null,\n        govde.model ?? null, govde.yil ?? null, govde.parca_adi ?? null, govde.notu ?? null', 'govde.kanal, govde.kategori, govde.marka,\n        govde.model, govde.yil, govde.parca_adi, govde.notu'), sql, "node", 'govde.kanal, govde.kategori, govde.marka,'),
        "K3": (tek_mutasyon(js, 'return metin.includes("UNIQUE") || metin.includes("PRIMARY KEY");', 'return metin.includes("UNIQUE") || metin.includes("PRIMARY KEY") || metin.includes("NOT NULL");'), sql, "node", 'metin.includes("NOT NULL")'),
        "K4": (tek_mutasyon(js, 'export { izinliAnahtarlar, talepKoduUret };', '/* tekrar siniri */\nexport { izinliAnahtarlar, talepKoduUret };'), sql, "node", 'tekrar siniri'),
        "K5": (tek_mutasyon(js, 'if (contentLength !== null && Number.isFinite(Number(contentLength)) &&\n      Number(contentLength) > GOVDE_BAYT_TAVANI) { return gecersiz(); }', 'if (false) { return gecersiz(); }'), sql, "node", 'Content-Length'),
        "R1": (tek_mutasyon(temizlik, '            sil_eski(baglanti, kodlar)', '            sil_eski(baglanti, esik)'), temizlik, "cleanup-source", '            sil_eski(baglanti, esik)'),
    }


def temp_python(metin):
    dosya = tempfile.NamedTemporaryFile(prefix="k186-mutant-", suffix=".py", dir=ROOT / "tools", delete=False)
    dosya.write(metin.encode("utf-8"))
    dosya.close()
    return Path(dosya.name)


def calistir_python(yol, bayrak):
    return subprocess.run([sys.executable, str(yol), bayrak], cwd=ROOT, capture_output=True, text=True)


def mutant_sonuclari(temel_js, temel_sql, temel_temizlik, temel_test, isimler):
    hepsi = mutasyonlar(temel_js, temel_sql, temel_temizlik, temel_test)
    yakalandi = 0
    kontrol = 0
    for isim in isimler:
        mutant_js, mutant_sql, tur, kanit = hepsi[isim]
        gecici = None
        kaynak_yolu = None
        try:
            if tur in ("node", "source"):
                gecici = Path(tempfile.mkdtemp(prefix="k186-mutant-"))
                kaynak_yolu = gecici / "talep.js"
                kaynak_yolu.write_text(mutant_js, encoding="utf-8")
                uygulandi = kanit in (mutant_js + mutant_sql)
                base_ok, base_sonuc, _, _ = node_test(isim, source_path=TALEP)
                mutant_ok, mutant_sonuc, _, _ = node_test(isim, source_path=kaynak_yolu)
                if tur == "source":
                    base_deger = kaynak_taramasi(temel_sql, temel_js, uretim_dosyalari(temel_sql, temel_js)).get(isim, False)
                    mutant_deger = kaynak_taramasi(mutant_sql, mutant_js, uretim_dosyalari(mutant_sql, mutant_js)).get(isim, False)
                    base_ok, mutant_ok = base_deger, mutant_deger
                    ham = "base=" + str(base_ok) + " mutant=" + str(mutant_ok)
                else:
                    ham = (mutant_sonuc.stdout + mutant_sonuc.stderr).replace("\n", "\\n")
            elif tur == "test":
                gecici = Path(tempfile.mkdtemp(prefix="k186-mutant-"))
                mutant_test = gecici / "talep.mjs"
                mutant_test.write_text(mutant_js, encoding="utf-8")
                uygulandi = kanit not in mutant_js and kanit in temel_test
                base_ok, base_sonuc, _, _ = node_test(isim, source_path=TALEP)
                mutant_ok, mutant_sonuc, _, _ = node_test(isim, source_path=TALEP, test_path=mutant_test)
                ham = (mutant_sonuc.stdout + mutant_sonuc.stderr).replace("\n", "\\n")
            elif tur in ("phone", "phone7"):
                gecici = temp_python(mutant_js)
                uygulandi = kanit in mutant_js
                base_sonuc = calistir_python(Path(__file__), "--phone-probe=" + isim)
                mutant_sonuc = calistir_python(gecici, "--phone-probe=" + isim)
                base_ok = base_sonuc.returncode == 0
                mutant_ok = mutant_sonuc.returncode == 0
                ham = (mutant_sonuc.stdout + mutant_sonuc.stderr).replace("\n", "\\n")
            else:
                gecici = temp_python(mutant_js)
                uygulandi = kanit in mutant_js
                base_sonuc = calistir_python(TEMIZLIK, "--kendini-test")
                mutant_sonuc = calistir_python(gecici, "--kendini-test")
                base_ok = base_sonuc.returncode == 0
                mutant_ok = mutant_sonuc.returncode == 0
                ham = (mutant_sonuc.stdout + mutant_sonuc.stderr).replace("\n", "\\n")
            if tur == "test":
                anchor_source = temel_test
            elif tur == "source":
                anchor_source = mutant_js + mutant_sql
            elif tur in ("phone", "phone7"):
                if tur == "phone7":
                    bas = mutant_js.find("def phone_probe")
                    son = mutant_js.find("\ndef main", bas)
                    anchor_source = mutant_js[bas:son]
                else:
                    anchor_source = mutant_js.split("def mutasyonlar", 1)[0]
            else:
                anchor_source = mutant_js
            capa = anchor_source.count(kanit) if kanit else 0
            kontrol += int(base_ok)
            tek_iddia = base_ok and not mutant_ok and uygulandi and capa == 1
            yakalandi += int(tek_iddia)
            rc = mutant_sonuc.returncode if 'mutant_sonuc' in locals() else 0
            komut = " ".join(str(x) for x in mutant_sonuc.args) if 'mutant_sonuc' in locals() else ""
            print("MUTANT " + isim + " komut=" + komut + " rc=" + str(rc) +
                  " ham=" + ham + " capa_sayisi=" + str(capa) +
                  " dusen_iddia=" + (isim if tek_iddia else "YOK") +
                  " dusen_liste=" + ("[" + isim + "]" if tek_iddia else "[]") +
                  " mutasyon_kaynaga_girdi=" + str(uygulandi), file=sys.stderr)
        finally:
            if gecici and gecici.is_file():
                gecici.unlink(missing_ok=True)
            elif gecici and gecici.is_dir():
                shutil.rmtree(gecici, ignore_errors=True)
    return yakalandi, kontrol, len(isimler)


def phone_probe(ad):
    if ad == "G6":
        return not telefon_ihlali("id=4005 tarih=2026")
    return telefon_ihlali("https://wa.me/4005")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizinti", action="store_true")
    parser.add_argument("--phone-probe")
    args = parser.parse_args()
    if args.phone_probe:
        return 0 if phone_probe(args.phone_probe) else 1

    js = TALEP.read_text(encoding="utf-8")
    sql = SEMA.read_text(encoding="utf-8")
    temizlik = TEMIZLIK.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")
    iddialar = SIZINTI_IDDIALAR if args.sizinti else IDDIALAR
    beklenen = BEKLENEN_IDDIA_SIZINTI if args.sizinti else BEKLENEN_IDDIA
    node_ok, node_cikti, node_olcu, node_iddialar = node_test(sizinti=args.sizinti)
    sonuclar = {ad: node_iddialar.get(ad, False) for ad in iddialar}
    kaynak = kaynak_taramasi(sql, js, uretim_dosyalari(sql, js))
    for ad in ("C1", "C2", "C3", "C4", "C5", "E3", "G6", "G7", "G11", "R1"):
        if ad in sonuclar:
            sonuclar[ad] = kaynak.get(ad, False)
    if not args.sizinti:
        temiz_sonuc = subprocess.run([sys.executable, str(TEMIZLIK), "--kendini-test"], cwd=ROOT, capture_output=True, text=True)
        sonuclar["F5"] = temiz_sonuc.returncode == 0 and "F5=GECTI" in temiz_sonuc.stdout
    if node_olcu:
        gerceklesen = node_olcu[0]
    else:
        gerceklesen = 0
    if gerceklesen != beklenen:
        print("OLCULEMEDI: " + str(beklenen) + " iddia bekleniyordu, " + str(gerceklesen) + " kosdu")
    for ad in iddialar:
        if not sonuclar[ad]:
            print("DUSEN: " + ad + " — node satiri veya kaynak ekseni gecmedi")

    mutant, kontrol, toplam_mutant = mutant_sonuclari(js, sql, temizlik, test, iddialar)
    dusen_sayisi = sum(1 for ad in iddialar if not sonuclar[ad])
    print("IDDIA=" + str(len(iddialar)) + " DUSEN=" + str(dusen_sayisi) +
          " MUTANT=" + str(mutant) + "/" + str(toplam_mutant) +
          " KONTROL=" + str(kontrol) + "/" + str(toplam_mutant))
    return 1 if dusen_sayisi or mutant != toplam_mutant or kontrol != toplam_mutant or not node_ok or gerceklesen != beklenen else 0


if __name__ == "__main__":
    sys.exit(main())
