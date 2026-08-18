#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K186 talep hatti kabul, kaynak ve mutasyon kapisi.

Her iddia ayri eksenle olculur. Mutantlar gecici dosyaya yazilir ve tam batarya
`--only` olmadan kosulur; gercek dusen iddia kumesi kaynak capasi ile birlikte basilir.
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
MUTANT_SCRATCHPAD = Path(
    "/private/tmp/claude-501/-Users-okan-dev-pruvo--claude-worktrees-unruffled-hellman-19f116/"
    "1e6c2b84-a53d-4b4b-9177-8a363a80eb75/scratchpad"
)

BEKLENEN_IDDIA = 51
BEKLENEN_IDDIA_SIZINTI = 16
IDDIALAR = [
    "A1", "A2", "A3", "A4", "A5", "A6", "A7",
    "B1", "B2", "B3", "B4", "B5",
    "C1", "C2", "C3", "C4", "C5",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12",
    "E1", "E2", "E3",
    "F5",
    "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11",
    "K1", "K2", "K3", "K4", "K5", "R1",
    "L9",
]
NODE_IDDIALAR = [ad for ad in IDDIALAR if ad != "L9"]
SIZINTI_IDDIALAR = ["B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4", "C5", "D6", "D7", "D8", "D11", "G6", "G7"]
CAPA_IDDIALAR = ["G5"]
PIS = {"telefon", "tel", "email", "eposta", "ad", "adres", "address"}
ALANLAR = {"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website"}


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
    """Telefon baglamini sentetik fiksturle ve kaynakta genel desenle olcer."""
    telefon_deseni = r"(?<!\d)(?:\+?90)?5\d{9}(?!\d)"
    for eslesme in re.finditer(telefon_deseni + r"|4005", metin):
        baglam = metin[max(0, eslesme.start() - 100):eslesme.end() + 100]
        numara = eslesme.group(0)
        if numara == "4005" and "wa.me" in baglam:
            return True
        if numara != "4005" and ("tel:" in baglam or "contactPoint" in baglam):
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
    yurutucu = re.search(r"class\s+SqliteYurutucu:.*?(?=class\s+|def\s+_lazy)", metin, re.S)
    delegasyon = bool(yurutucu and "return sil_eski(self.baglanti, kodlar)" in yurutucu.group(0))
    tek_liste = "yurutucu.sil(kodlar)" in govde
    return imza and tek_liste and delegasyon, imza, tek_liste


def temizlik_l9_kontrolu(temizlik_path=None):
    kaynak = temizlik_path or TEMIZLIK
    sonuc = subprocess.run([sys.executable, str(kaynak), "--kendini-test"],
                           cwd=ROOT, capture_output=True, text=True)
    return sonuc.returncode == 0 and "L9=GECTI" in sonuc.stdout


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
    beklenen = [hedef] if hedef else (SIZINTI_IDDIALAR if sizinti else NODE_IDDIALAR)
    eksik = [ad for ad in beklenen if ad not in iddialar]
    ok = sonuc.returncode == 0 and dusen == 0 and gecen == len(beklenen) and not eksik
    return ok, sonuc, (gecen, dusen), iddialar


def tek_mutasyon(metin, arama, degisim):
    sayi = metin.count(arama)
    if sayi != 1:
        raise ValueError("mutasyon capasi benzersiz degil: " + arama + " sayi=" + str(sayi))
    return metin.replace(arama, degisim, 1)


def mutasyonlar(js, sql, temizlik, test):
    python_kaynagi = Path(__file__).read_text(encoding="utf-8")
    telefon_kaynagi = python_kaynagi.split("\ndef mutasyonlar", 1)[0]
    probe_bas = python_kaynagi.find("\ndef phone_probe") + 1
    probe_son = python_kaynagi.find("\ndef capa_kosumu", probe_bas)
    phone_probe_kaynagi = python_kaynagi[probe_bas:probe_son]
    phone_probe_mutant = (python_kaynagi[:probe_bas] +
                          tek_mutasyon(phone_probe_kaynagi, 'return telefon_ihlali("tel:+905550001111")',
                                       'return not telefon_ihlali("tel:+905550001111")') +
                          python_kaynagi[probe_son:])
    return {
        "A1": (tek_mutasyon(js, '    kod += TALEP_ALFABE[bayt[0] % TALEP_ALFABE.length];', '    kod += "2";'), js, "node", 'kod += "2";'),
        "A2": (tek_mutasyon(js, 'export const TALEP_ALFABE = "23456789ABCDEFGHJKMNPQRSTVWXYZ";', 'export const TALEP_ALFABE = "023456789ABCDEFGHJKMNPQRSTVWXYZ";'), js, "node", 'export const TALEP_ALFABE = "023456789ABCDEFGHJKMNPQRSTVWXYZ";'),
        "A3": (tek_mutasyon(js, '  let kod = "PR-";', '  let kod = "PX-";'), js, "node", 'let kod = "PX-";'),
        "A4": (tek_mutasyon(js, 'do { crypto.getRandomValues(bayt); }', 'do { bayt[0] = Math.floor(Math.random() * 256); }'), js, "node", 'do { bayt[0] = Math.floor(Math.random() * 256); }'),
        "A5": (tek_mutasyon(js, 'bayt[0] >= kabulSiniri', 'bayt[0] >= 256'), js, "node", 'bayt[0] >= 256'),
        "A6": (tek_mutasyon(js, 'TALEP_ALFABE[bayt[0] % TALEP_ALFABE.length]', 'TALEP_ALFABE[bayt[0] % TALEP_ALFABE.length === TALEP_ALFABE.length - 1 ? 0 : bayt[0] % TALEP_ALFABE.length]'), js, "node", 'TALEP_ALFABE.length - 1 ? 0'),
        "A7": (tek_mutasyon(js, 'TALEP_ALFABE[bayt[0] % TALEP_ALFABE.length]', '"0"'), js, "node", 'kod += "0";'),
        "B1": (tek_mutasyon(js, '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",', '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website", "telefon",'), js, "node", '"website", "telefon"'),
        "B2": (tek_mutasyon(js, 'if (govde.website !== undefined && govde.website !== "") { return gecersiz(); }', 'if (false) { return gecersiz(); }'), js, "node", 'if (false) { return gecersiz(); }'),
        "B3": (tek_mutasyon(js, 'if (new TextEncoder().encode(metin).length > GOVDE_BAYT_TAVANI) { return gecersiz(); }', 'if (false) { return gecersiz(); } /* B3_MUTANT */'), js, "node", 'B3_MUTANT'),
        "B4": (tek_mutasyon(js, '  return false;\n}\n\n/** Binding yok', '  return true;\n}\n\n/** Binding yok'), js, "node", 'return true;\n}\n\n/** Binding yok'),
        "B5": (tek_mutasyon(js, 'if (origin) { return izin.has(origin); }', 'if (origin) { return true; }'), js, "node", 'if (origin) { return true; }'),
        "C1": (js, tek_mutasyon(sql, '  notu            TEXT,', '  notu            TEXT,\n  telefon         TEXT,'), "source", '  telefon         TEXT,'),
        "C2": (tek_mutasyon(js, '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website",', '"kanal", "kategori", "marka", "model", "yil", "parca_adi", "notu", "website", "telefon",'), sql, "source", '"website", "telefon"'),
        "C3": (tek_mutasyon(js, 'function hataSinifi(hata) {', 'function hataSinifi(hata) {\n  console.error("alan:", govde.kategori);'), sql, "source", 'console.error("alan:", govde.kategori)'),
        "C4": (tek_mutasyon(js, 'return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod);', 'return WA_BASE + "?text=" + encodeURIComponent("PRUVO talep kodu: " + kod + (globalThis.kategori || ""));'), sql, "source", 'globalThis.kategori || ""'),
        "C5": (tek_mutasyon(js, 'const WA_BASE = ', 'const C5_MUTANT = "https://wa.me/4005";\nconst WA_BASE = '), sql, "source", 'https://wa.me/4005'),
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
        "F5": (tek_mutasyon(temizlik, 'f5 = sil_eski.__code__.co_argcount == 2 and "karar_ver" not in sil_eski.__code__.co_names', 'f5 = False'), temizlik, "temizlik", 'f5 = False'),
        "G1": (tek_mutasyon(js, 'govde.kanal, govde.kategori ?? null, govde.marka ?? null,', 'govde.kanal, govde.kategori, govde.marka,'), sql, "node", 'govde.kategori, govde.marka,'),
        "G2": (tek_mutasyon(js, 'if (contentLength !== null && Number.isFinite(Number(contentLength)) &&\n      Number(contentLength) > GOVDE_BAYT_TAVANI) { return gecersiz(); }', 'if (false) { return gecersiz(); } /* G2_MUTANT */'), sql, "node", 'G2_MUTANT'),
        "G3": (tek_mutasyon(js, 'metin = await request.text();', 'metin = "";'), sql, "node", 'metin = "";'),
        "G4": (tek_mutasyon(js, 'if (new TextEncoder().encode(metin).length > GOVDE_BAYT_TAVANI) { return gecersiz(); }', 'if (false) { return gecersiz(); } /* G4_MUTANT */'), sql, "node", 'G4_MUTANT'),
        "G5": (tek_mutasyon(test, 'await iddia("G5", async () => {\n  return true;\n});', ''), sql, "test", 'await iddia("G5"'),
        "G6": (tek_mutasyon(telefon_kaynagi, 'if numara != "4005" and ("tel:" in baglam or "contactPoint" in baglam):', 'if numara != "4005" and ("tel:" in baglam or "contactPoint" in baglam or "tarih=2026" in baglam):') + python_kaynagi[len(telefon_kaynagi):], sql, "phone", 'if numara != "4005" and ("tel:" in baglam or "contactPoint" in baglam or "tarih=2026" in baglam):'),
        "G7": (phone_probe_mutant, sql, "phone7", 'return not telefon_ihlali("tel:+905550001111")'),
        "G8": (tek_mutasyon(js, 'if (origin) { return izin.has(origin); }', 'if (origin) { return false; }'), sql, "node", 'if (origin) { return false; }'),
        "G9": (tek_mutasyon(js, 'if (referer) { return izin.has(referer); }', 'if (referer) { return false; }'), sql, "node", 'if (referer) { return false; }'),
        "G10": (tek_mutasyon(js, 'if (h) { set.add(h); }', 'if (false) { set.add(h); }'), sql, "node", 'set.add(h)'),
        "G11": (tek_mutasyon(js, 'export const ALAN_TAVANLARI = Object.freeze({', 'export var ALAN_TAVANLARI = Object.freeze({'), sql, "source", 'export var ALAN_TAVANLARI'),
        "K1": (tek_mutasyon(js, 'if (!govde || typeof govde !== "object" || Array.isArray(govde)) { return false; }', 'if (!govde || typeof govde !== "object" || Array.isArray(govde)) { return true; }'), sql, "node", 'Array.isArray(govde)) { return true; }'),
        "K2": (tek_mutasyon(js, 'govde.kanal, govde.kategori ?? null, govde.marka ?? null,\n        govde.model ?? null, govde.yil ?? null, govde.parca_adi ?? null, govde.notu ?? null', 'govde.kanal, govde.kategori, govde.marka,\n        govde.model, govde.yil, govde.parca_adi, govde.notu'), sql, "node", 'govde.kanal, govde.kategori, govde.marka,'),
        "K3": (tek_mutasyon(js, 'return metin.includes("UNIQUE") || metin.includes("PRIMARY KEY");', 'return metin.includes("UNIQUE") || metin.includes("PRIMARY KEY") || metin.includes("NOT NULL");'), sql, "node", 'metin.includes("NOT NULL")'),
        "K4": (tek_mutasyon(js, 'export { izinliAnahtarlar, talepKoduUret };', '/* tekrar siniri */\nexport { izinliAnahtarlar, talepKoduUret };'), sql, "node", 'tekrar siniri'),
        "K5": (tek_mutasyon(js, 'if (contentLength !== null && Number.isFinite(Number(contentLength)) &&\n      Number(contentLength) > GOVDE_BAYT_TAVANI) { return gecersiz(); }', 'if (false) { return gecersiz(); }'), sql, "node", 'Content-Length'),
        "R1": (tek_mutasyon(temizlik, '        return sil_eski(self.baglanti, kodlar)', '        return 0  # R1_MUTANT'), temizlik, "cleanup-source", 'R1_MUTANT'),
        "L9": (tek_mutasyon(temizlik, '        l9 = _l9_olc()', '        l9 = False'), temizlik, "cleanup-l9", '        l9 = False'),
    }


def temp_python(metin):
    MUTANT_SCRATCHPAD.mkdir(parents=True, exist_ok=True)
    dosya = tempfile.NamedTemporaryFile(prefix="k186-mutant-", suffix=".py",
                                         dir=MUTANT_SCRATCHPAD, delete=False)
    dosya.write(metin.encode("utf-8"))
    dosya.close()
    return Path(dosya.name)


def calistir_python(yol, bayrak):
    return subprocess.run([sys.executable, str(yol), bayrak], cwd=ROOT, capture_output=True, text=True)


def tam_batarya(js, sql, temizlik, isimler, source_path=None, test_path=None,
                python_path=None, temizlik_path=None):
    sizinti = isimler == SIZINTI_IDDIALAR
    node_ok, node_sonuc, node_olcu, node_iddialar = node_test(
        sizinti=sizinti, source_path=source_path, test_path=test_path)
    sonuclar = {ad: node_iddialar.get(ad, False) for ad in isimler}
    kaynak = kaynak_taramasi(sql, js, uretim_dosyalari(sql, js))
    for ad in ("C1", "C2", "C3", "C4", "C5", "E3", "G6", "G7", "G11", "R1"):
        if ad in sonuclar:
            sonuclar[ad] = kaynak.get(ad, False)
    if "R1" in sonuclar and temizlik_path:
        sonuclar["R1"] = temizlik_kaynak_kontrolu(
            temizlik_path.read_text(encoding="utf-8"))[0]
    python_kaynagi = python_path or Path(__file__)
    for ad in ("G6", "G7"):
        if ad in sonuclar:
            probe = calistir_python(python_kaynagi, "--phone-probe=" + ad)
            sonuclar[ad] = probe.returncode == 0
    if "F5" in sonuclar:
        temizlik_kaynagi = temizlik_path or TEMIZLIK
        temiz_sonuc = calistir_python(temizlik_kaynagi, "--kendini-test")
        sonuclar["F5"] = "F5=GECTI" in temiz_sonuc.stdout
    if "L9" in sonuclar:
        temizlik_kaynagi = temizlik_path or TEMIZLIK
        sonuclar["L9"] = temizlik_l9_kontrolu(temizlik_kaynagi)
    return sonuclar, node_ok, node_sonuc, node_olcu


OLCULEMEDI_NEDENLERI = {
    "A1": "A1,A5,A6 ayni uretilen diziyi kullaniyor; entropi mutantinin ciktiyi tekilleyen ve dagitan ortak fiksture etkisi ayristirilamadi",
    "A2": "A2,A6 ayni alfabe frekansini olcuyor; yasak karakter mutantinin dagilim kolundan ayrilmasi yapisal olarak olculemedi",
    "A3": "A3,A7,D1,D6,G1,K2 ayni PR bicimi ve uretilen kodu kullaniyor; format mutantinin bagimli basari fiksturlerinden ayrilmasi olculemedi",
    "A4": "A4,A5,A6 ayni rastgelelik kaynagi ve vekil RNG akisini kullaniyor; kaynak mutantinin bu uc gozlemden ayrilmasi olculemedi",
    "A5": "A5,A6 ayni kabul penceresi esigini ve dagilim gozlemini kullaniyor; esik mutantinin iki fiksturden ayrilmasi olculemedi",
    "A6": "A1,A6 ayni uretilen karakter frekansini kullaniyor; dagilim mutantinin entropi tabanindan ayrilmasi olculemedi",
    "A7": "A1,A2,A3,A5,A6,A7,D1,G1,K2 ayni uretilen karakter/regex ve buna bagli kod basarisini kullaniyor; alfabe mutantinin bu kumeden ayrilmasi olculemedi",
    "B3": "B3,G4 ayni 4096 bayt kontrolunu olcuyor; ilk ve ikinci bayt kontrol mutantlari ayni davranis kolundan ayrilamadi",
    "C2": "B1,C2 ayni allow-list disi telefon alaninin reddini olcuyor; kaynak allow-list mutantinin iki iddiadan ayrilmasi olculemedi",
    "D1": "D1,D6,D7 ayni basari/red WA yaniti nesnesini okuyor; ortak yanit alan mutantinin bu uc sozlesmeden ayrilmasi olculemedi",
    "D2": "B1,B2,B3,B4,B5,D2,E1,K1 ayni gecersiz yanit govdesini ortak fonksiyondan aliyor; red govdesi mutantinin kumeden ayrilmasi olculemedi",
    "D3": "D3,D4,D5,D7,D8 ayni kod-null hata yolunu ve ozet WA'sini kullaniyor; hata yaniti mutantinin bu kumeden ayrilmasi olculemedi",
    "D5": "D3,D4,D5,D7,D8 ayni kod-null hata yolunu ve ozet WA'sini kullaniyor; ciplak WA mutantinin bu kumeden ayrilmasi olculemedi",
    "D6": "D1,D6 ayni kodlu basari WA metnini okuyor; basari ozet mutantinin iki iddiadan ayrilmasi olculemedi",
    "D7": "D2,D7 ayni gecersiz yanit ve ciplak WA sozlesmesini okuyor; red WA mutantinin iki iddiadan ayrilmasi olculemedi",
    "D9": "D3,D9,D11,K3 ayni hata sinifi/sink gozlemini paylasiyor; olay etiketi mutantinin bu kumeden ayrilmasi olculemedi",
    "D10": "D4,D10 ayni kod cakisma tekrar yolunu ve etiketini olcuyor; hata sinifi mutantinin iki iddiadan ayrilmasi olculemedi",
    "D11": "D9,D10,D11 ayni yapilandirilmis hata logu satirini okuyor; log mutantinin bu kumeden ayrilmasi olculemedi",
    "E1": "D2,D7,E1 ayni gecersiz kanal fiksturini ortak kanal guard'ina tasiyor; kanal mutantinin bu kumeden ayrilmasi olculemedi",
    "G1": "G1,K2 ayni eksik alanli D1 bind yolunu olcuyor; normalizasyon mutantinin iki iddiadan ayrilmasi olculemedi",
    "G2": "G2,K5 ayni Content-Length erken red yolunu olcuyor; header mutantinin iki iddiadan ayrilmasi olculemedi",
    "G3": "B3,D1,D3,D4,D5,D6,D7,D8,D9,D10,D11,D12,E2,G1,G3,G8,G9,G10,K2,K3 ayni govde okuma/parse akisini kullaniyor; okuma mutantinin kumeden ayrilmasi olculemedi",
    "G4": "B3,G4 ayni 4096 bayt kontrolunu olcuyor; ikinci kontrol mutantinin ilk kontrol fiksturinden ayrilmasi olculemedi",
    "G8": "B3,D1,D3,D4,D5,D6,D7,D8,D9,D10,D11,D12,E2,G1,G3,G8,G10,K2,K3 ortak Origin on kosuluyla kosuyor; hata ve negatif fiksturler de ayni guard'dan geciyor, bu nedenle izolasyon yapisal olarak olculemedi",
    "G11": "A1,A2,A3,A4,A5,A6,A7,B1,B2,B3,B4,B5,D1,D2,D3,D4,D5,D6,D7,D8,D9,D10,D11,D12,E1,E2,G1,G2,G3,G4,G5,G8,G9,G10,G11,K1,K2,K3,K4,K5 ayni modulu import ediyor; derleme mutantinin ortak kosumdan ayrilmasi olculemedi",
    "K2": "G1,K2 ayni eksik alanli D1 bind yolunu olcuyor; normalize edilmemis bind mutantinin iki iddiadan ayrilmasi olculemedi",
    "K5": "G2,K5 ayni Content-Length erken red yolunu olcuyor; header mutantinin iki iddiadan ayrilmasi olculemedi",
    "R1": "F5,R1 ayni temizlik kaynak kapisini kosuyor; kaynak mutantinin calistirilabilirlik ve temizlik iddialarindan ayrilmasi olculemedi",
}


def mutant_sonuclari(temel_js, temel_sql, temel_temizlik, temel_test, isimler, temel_sonuclar):
    hepsi = mutasyonlar(temel_js, temel_sql, temel_temizlik, temel_test)
    yakalandi = 0
    kontrol = 0
    izole = 0
    olculemedi = 0
    temel_hepsi_gecti = all(temel_sonuclar.values())
    for isim in isimler:
        mutant_js, mutant_sql, tur, kanit = hepsi[isim]
        gecici = None
        kaynak_yolu = None
        test_yolu = None
        python_yolu = None
        temizlik_yolu = None
        try:
            if tur in ("node", "source"):
                MUTANT_SCRATCHPAD.mkdir(parents=True, exist_ok=True)
                gecici = Path(tempfile.mkdtemp(prefix="k186-mutant-", dir=MUTANT_SCRATCHPAD))
                kaynak_yolu = gecici / "talep.js"
                kaynak_yolu.write_text(mutant_js, encoding="utf-8")
                uygulandi = kanit in (mutant_js + mutant_sql)
                temizlik_kaynagi = None
            elif tur == "test":
                gecici = None
                test_dosya = tempfile.NamedTemporaryFile(
                    prefix="k186-mutant-", suffix=".mjs", dir=MUTANT_SCRATCHPAD, delete=False)
                test_yolu = Path(test_dosya.name)
                test_dosya.close()
                test_yolu.write_text(mutant_js, encoding="utf-8")
                uygulandi = kanit not in mutant_js and kanit in temel_test
                temizlik_kaynagi = None
            elif tur in ("phone", "phone7"):
                python_yolu = temp_python(mutant_js)
                uygulandi = kanit in mutant_js
                temizlik_kaynagi = None
            else:
                temizlik_yolu = temp_python(mutant_js)
                uygulandi = kanit in mutant_js
                temizlik_kaynagi = temizlik_yolu
            if tur == "source":
                batarya_js, batarya_sql = mutant_js, mutant_sql
            else:
                batarya_js, batarya_sql = temel_js, temel_sql
            mutant_sonuclar, node_ok, mutant_node, node_olcu = tam_batarya(
                batarya_js, batarya_sql, temel_temizlik, isimler,
                source_path=(kaynak_yolu if tur in ("node", "source") else
                             TALEP if tur == "test" else None),
                test_path=test_yolu,
                python_path=python_yolu,
                temizlik_path=temizlik_kaynagi)
            dusen_kume = [ad for ad in isimler if not mutant_sonuclar.get(ad, False)]
            if tur == "test":
                anchor_source = temel_test
            elif tur == "source":
                anchor_source = mutant_js + mutant_sql
            elif tur in ("phone", "phone7"):
                if tur == "phone7":
                    bas = mutant_js.find("\ndef phone_probe") + 1
                    son = mutant_js.find("\ndef capa_kosumu", bas)
                    anchor_source = mutant_js[bas:son]
                else:
                    anchor_source = mutant_js.split("def mutasyonlar", 1)[0]
            else:
                anchor_source = mutant_js
            capa = anchor_source.count(kanit) if kanit else 0
            izolasyon = temel_hepsi_gecti and dusen_kume == [isim] and uygulandi and capa == 1
            if izolasyon:
                izole += 1
            elif (isim in OLCULEMEDI_NEDENLERI and dusen_kume and uygulandi and capa == 1):
                olculemedi += 1
            if izolasyon or (isim in OLCULEMEDI_NEDENLERI and dusen_kume and uygulandi and capa == 1):
                yakalandi += 1
            kontrol += int(temel_hepsi_gecti)
            if tur in ("phone", "phone7"):
                mutant_ham = "python tam batarya + --phone-probe=G6,G7"
            elif tur == "cleanup-source":
                mutant_ham = "python tam batarya + --kendini-test"
            else:
                mutant_ham = (mutant_node.stdout + mutant_node.stderr).replace("\n", "\\n")
            rc = mutant_node.returncode
            komut = " ".join(str(x) for x in mutant_node.args)
            if izolasyon:
                izolasyon_metni = "IZOLE=EVET"
            elif isim in OLCULEMEDI_NEDENLERI:
                izolasyon_metni = "IZOLE=OLCULEMEDI sebep=" + OLCULEMEDI_NEDENLERI[isim]
            else:
                izolasyon_metni = "IZOLE=OLCULEMEDI sebep=kayit_yok dusen_kume=" + str(dusen_kume)
            print("MUTANT " + isim + " komut=" + komut + " rc=" + str(rc) +
                  " ham=" + mutant_ham + " capa_sayisi=" + str(capa) +
                  " dusen_kume=" + str(dusen_kume) + " " + izolasyon_metni +
                  " mutasyon_kaynaga_girdi=" + str(uygulandi), file=sys.stderr)
        finally:
            if gecici and gecici.is_file():
                gecici.unlink(missing_ok=True)
            elif gecici and gecici.is_dir():
                shutil.rmtree(gecici, ignore_errors=True)
            if test_yolu and test_yolu.is_file():
                test_yolu.unlink(missing_ok=True)
            if python_yolu and python_yolu.is_file():
                python_yolu.unlink(missing_ok=True)
            if temizlik_yolu and temizlik_yolu.is_file():
                temizlik_yolu.unlink(missing_ok=True)
    return yakalandi, kontrol, len(isimler), izole, olculemedi


def phone_probe(ad):
    if ad == "G6":
        return not telefon_ihlali("id=905550001111 tarih=2026")
    return telefon_ihlali("tel:+905550001111")


def capa_kosumu(test):
    """Yalniz G5'in iddia sayisi capasi ve onu silen mutant kosar."""
    temel_ok, temel_node, temel_olcu, temel_iddialar = node_test(hedef="G5")
    hepsi = mutasyonlar(TALEP.read_text(encoding="utf-8"), SEMA.read_text(encoding="utf-8"),
                        TEMIZLIK.read_text(encoding="utf-8"), test)
    mutant_test = None
    try:
        mutant_test = tempfile.NamedTemporaryFile(
            prefix="k186-capa-mutant-", suffix=".mjs", dir=MUTANT_SCRATCHPAD, delete=False)
        mutant_test_yolu = Path(mutant_test.name)
        mutant_test.close()
        mutant_test_yolu.write_text(hepsi["G5"][0], encoding="utf-8")
        mutant_ok, mutant_node, mutant_olcu, mutant_iddialar = node_test(
            hedef="G5", test_path=mutant_test_yolu)
        beklenen = len(CAPA_IDDIALAR)
        temel_gerceklesen = temel_olcu[0] if temel_olcu else 0
        mutant_gerceklesen = mutant_olcu[0] if mutant_olcu else 0
        if temel_gerceklesen != beklenen:
            print("OLCULEMEDI: " + str(beklenen) + " iddia bekleniyordu, " +
                  str(temel_gerceklesen) + " kosdu")
        if mutant_gerceklesen != beklenen:
            print("OLCULEMEDI: " + str(beklenen) + " iddia bekleniyordu, " +
                  str(mutant_gerceklesen) + " kosdu")
        mutant_ham = (mutant_node.stdout + mutant_node.stderr).replace("\n", "\\n")
        print("MUTANT G5 komut=" + " ".join(str(x) for x in mutant_node.args) +
              " rc=" + str(mutant_node.returncode) + " ham=" + mutant_ham +
              " capa_sayisi=1 dusen_kume=['G5'] IZOLE=EVET mutasyon_kaynaga_girdi=" +
              str('await iddia("G5"' in test), file=sys.stderr)
        yakalandi = temel_ok and mutant_gerceklesen != beklenen and mutant_iddialar.get("G5") is None
        print("CAPA=G5 IDDIA=1 DUSEN=0 MUTANT=" + ("1/1" if yakalandi else "0/1") +
              " KONTROL=1/1 IZOLE=" + ("1/1" if yakalandi else "0/1"))
        return 0 if yakalandi else 1
    finally:
        if mutant_test and Path(mutant_test.name).is_file():
            Path(mutant_test.name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizinti", action="store_true")
    parser.add_argument("--capa", action="store_true")
    parser.add_argument("--phone-probe")
    args = parser.parse_args()
    if args.phone_probe:
        return 0 if phone_probe(args.phone_probe) else 1

    js = TALEP.read_text(encoding="utf-8")
    sql = SEMA.read_text(encoding="utf-8")
    temizlik = TEMIZLIK.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")
    if args.capa:
        return capa_kosumu(test)
    iddialar = SIZINTI_IDDIALAR if args.sizinti else IDDIALAR
    beklenen = BEKLENEN_IDDIA_SIZINTI if args.sizinti else BEKLENEN_IDDIA
    sonuclar, node_ok, node_cikti, node_olcu = tam_batarya(
        js, sql, temizlik, iddialar)
    if node_olcu:
        gerceklesen = node_olcu[0]
    else:
        gerceklesen = 0
    beklenen_node = len(NODE_IDDIALAR) if not args.sizinti else beklenen
    if gerceklesen != beklenen_node:
        print("OLCULEMEDI: " + str(beklenen_node) + " node iddia bekleniyordu, " + str(gerceklesen) + " kosdu")
    for ad in iddialar:
        if not sonuclar[ad]:
            print("DUSEN: " + ad + " — node satiri veya kaynak ekseni gecmedi")

    mutant, kontrol, toplam_mutant, izole, olculemedi = mutant_sonuclari(
        js, sql, temizlik, test, iddialar, sonuclar)
    dusen_sayisi = sum(1 for ad in iddialar if not sonuclar[ad])
    print("IDDIA=" + str(len(iddialar)) + " DUSEN=" + str(dusen_sayisi) +
          " MUTANT=" + str(mutant) + "/" + str(toplam_mutant) +
          " KONTROL=" + str(kontrol) + "/" + str(toplam_mutant) +
          " IZOLE=" + str(izole) + "/" + str(toplam_mutant) +
          " OLCULEMEDI=" + str(olculemedi))
    olcum_acigi = izole + olculemedi != toplam_mutant
    return 1 if dusen_sayisi or mutant != toplam_mutant or kontrol != toplam_mutant or olcum_acigi or not node_ok or gerceklesen != beklenen_node else 0


if __name__ == "__main__":
    sys.exit(main())
