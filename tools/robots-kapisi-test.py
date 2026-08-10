#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL KAPISI — robots.txt parametreli URL kurallari (tarama butcesi).

NE KAPATIYORUZ: `?kategori=` `?marka=` `?ara=` `?sepet=` — ana sayfanin istemci
tarafi filtreleri. Hepsi ayni HTML'i dondurur, canonical ANA SAYFAYI gosterir
(olculdu 11 Agu 2026), yani tarama butcesi bosa gidiyor.

🔴 EN BUYUK RISK FAZLADAN KAPATMAKTIR. Olculdu (canli sitemap, 26.696 URL):
   yolunda "ara" gecen 2.169 · "marka" gecen 1.147 · "sepet" gecen 16 kanonik URL.
   Sorguya capalanmamis tek bir desen (`Disallow: /*ara`) bunlarin hepsini kapatir.
   Bu kapinin YANLIS-POZITIF ekseni tam olarak bunu olcer.

⚠️ robots ile kapatilan sayfa indeksten DUSMEZ; Google tarayamadigi icin canonical
sinyalini de GOREMEZ. Bu dort bicim bugun kanonik yuzunden zaten indekse girmiyor
(canonical -> ana sayfa; sitemap'te 0 parametreli URL olculdu), bu yuzden degisim
guvenli kabul edildi — gerekce muhendis raporunda.

IDDIALAR:
  1 ESLESTIRICI  — RFC 9309 (Google robots.txt) ornek tablosuyla dogrulanir
                   (kendi yazdigimiz esilestirici "parser taklidi" olmasin diye
                   spec'in KENDI orneklerine capalidir).
  2 ACIK KALIYOR — kanonik urun adresleri, marka/model sayfalari, ana sayfa,
                   /sitemap.xml, icerik/yasal sayfalar + katalogdan TURETILEN
                   "ara/marka/sepet" alt-dizeli yollar.
  3 KAPALI       — dort parametre, hem ILK hem SONRAKI sirada (`&`).
  4 SITEMAP      — `Sitemap:` satiri duruyor.
  5 MUTASYON     — genisletme (`Disallow: /`), sorgu capasinin dusmesi, `&`
                   bicimlerinin silinmesi, Sitemap satirinin silinmesi KIRMIZI;
                   davranissiz KONTROL mutanti YESIL.

Kosum: python3 tools/robots-kapisi-test.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import shutil

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools")
sys.path.insert(0, ARAC)

IDDIA = [0]
HATA = []


def bekle(kosul, mesaj):
    IDDIA[0] += 1
    if not kosul:
        HATA.append(mesaj)
        print("  ❌ %s" % mesaj)
    return bool(kosul)


# ------------------------------------------------- RFC 9309 eslestirici
def _desen_re(desen):
    """robots yol deseni -> regex. OZEL karakter YALNIZ `*` ve `$` (RFC 9309)."""
    son = desen.endswith("$")
    govde = desen[:-1] if son else desen
    parcalar = [re.escape(p) for p in govde.split("*")]
    return re.compile("^" + ".*".join(parcalar) + ("$" if son else ""))


def robots_karari(robots_metni, yol, ajan="*"):
    """True = TARANABILIR (Allow), False = KAPALI (Disallow).

    RFC 9309 §2.2.2: en UZUN (en spesifik) eslesen kural kazanir; esitlikte Allow.
    """
    gruplar, aktif, son_ua = {}, None, False
    for ham in robots_metni.splitlines():
        satir = ham.split("#", 1)[0].strip()
        if not satir or ":" not in satir:
            continue
        alan, deger = satir.split(":", 1)
        alan, deger = alan.strip().lower(), deger.strip()
        if alan == "user-agent":
            if not son_ua:
                aktif = []
            gruplar.setdefault(deger.lower(), aktif if aktif is not None else [])
            if aktif is None:
                aktif = []
            gruplar[deger.lower()] = aktif
            son_ua = True
            continue
        son_ua = False
        if alan in ("allow", "disallow") and aktif is not None:
            aktif.append((alan, deger))
    kurallar = gruplar.get(ajan.lower()) or gruplar.get("*") or []
    en_iyi = None                      # (uzunluk, izin_mi)
    for alan, desen in kurallar:
        if desen == "" and alan == "disallow":
            continue                   # bos Disallow = her sey serbest
        if _desen_re(desen).match(yol):
            aday = (len(desen), alan == "allow")
            if en_iyi is None or aday[0] > en_iyi[0] or (
                    aday[0] == en_iyi[0] and aday[1]):
                en_iyi = aday
    return True if en_iyi is None else en_iyi[1]


# RFC 9309 / Google robots.txt belgesindeki ORNEK TABLO — eslestiricinin kendi
# dogrulama fiksturU. Bir tanesi bile tutmazsa asagidaki hukumlerin hepsi supheli.
SPEC_ORNEKLERI = [
    ("User-agent: *\nDisallow: /fish\n", "/fish", False),
    ("User-agent: *\nDisallow: /fish\n", "/fish.html", False),
    ("User-agent: *\nDisallow: /fish\n", "/fish/salmon.html", False),
    ("User-agent: *\nDisallow: /fish\n", "/fishheads", False),
    ("User-agent: *\nDisallow: /fish\n", "/catfish", True),
    ("User-agent: *\nDisallow: /fish\n", "/Fish.asp", True),
    ("User-agent: *\nDisallow: /fish/\n", "/fish/", False),
    ("User-agent: *\nDisallow: /fish/\n", "/fish/?id=anything", False),
    ("User-agent: *\nDisallow: /fish/\n", "/fish", True),
    ("User-agent: *\nDisallow: /fish/\n", "/fish.html", True),
    ("User-agent: *\nDisallow: /*.php\n", "/filename.php", False),
    ("User-agent: *\nDisallow: /*.php\n", "/folder/filename.php?parameters", False),
    ("User-agent: *\nDisallow: /*.php$\n", "/filename.php", False),
    ("User-agent: *\nDisallow: /*.php$\n", "/filename.php?parameters", True),
    ("User-agent: *\nDisallow: /*.php$\n", "/filename.php5", True),
    ("User-agent: *\nAllow: /p\nDisallow: /\n", "/page", True),
    ("User-agent: *\nAllow: /folder\nDisallow: /folder\n", "/folder/page", True),
    ("User-agent: *\nAllow: /$\nDisallow: /\n", "/", True),
    ("User-agent: *\nAllow: /$\nDisallow: /\n", "/page.htm", False),
]


def eslestirici_dogrula():
    print("-- 1) ESLESTIRICI (RFC 9309 ornek tablosu) --")
    for metin, yol, beklenen in SPEC_ORNEKLERI:
        bekle(robots_karari(metin, yol) == beklenen,
              "RFC ornegi tutmadi: %r -> %s (beklenen %s)"
              % (yol, robots_karari(metin, yol), beklenen))


# ------------------------------------------------- fikstur yollari
def katalogdan_yanlis_pozitif_yollari():
    """Yanlis-pozitif korpusu KATALOGDAN turer (elle tutulan liste bayatlar —
    [[kapsam-evrenini-cagri-grafindan-turet]]): yolunda 'ara/marka/sepet/kategori'
    alt-dizesi gecen GERCEK kanonik adresler."""
    yollar = []
    try:
        with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
    except (IOError, OSError, ValueError):
        urunler = []
    for kelime in ("ara", "marka", "sepet", "kategori"):
        n = 0
        for p in urunler:
            pid = p.get("id") or ""
            if kelime in pid:
                yollar.append("/urun/" + pid + "/")
                n += 1
                if n >= 25:
                    break
    try:
        import sayfalar
        for slug in sayfalar.SITEMAP_SLUGS:
            if any(k in slug for k in ("ara", "marka", "sepet", "kategori")):
                yollar.append("/" + slug + "/")
    except Exception:
        pass
    yollar.append("/marka/")
    return yollar


ACIK_OLMASI_GEREKEN = [
    "/", "/sitemap.xml", "/robots.txt", "/urun/mazda-cx5-bardaklik-sepeti/",
    "/marka/", "/marka/audi/", "/marka/audi/a4/", "/hakkimizda/", "/sss/",
    "/merchant-feed.xml", "/urunler.json", "/index.html",
]

KAPALI_OLMASI_GEREKEN = [
    "/?kategori=Marin", "/?marka=Audi", "/?ara=conta", "/?sepet=1",
    "/?kategori=Otomobil&marka=MX-5",          # parametre IKINCI sirada (olculdu)
    "/?ara=conta&kategori=Marin", "/?kategori=Jenerat%C3%B6r",
    "/index.html?kategori=Marin",
    # 🔴 AYIRT EDICI: ILK parametre hedef DISI (reklam/utm/sayfa) — bu bicimleri
    # yalniz `Disallow: /*&<ad>=` satiri kapatir. `&` bicimi silinirse bunlar ACIK
    # kalir; fikstur olmasaydi "4 satir yeterli" iddiasi olculemezdi.
    "/?gclid=abc123&marka=Audi", "/?utm_source=x&kategori=Marin",
    "/?sayfa=2&ara=conta", "/?siparis=1&sepet=1",
]


def robots_iddialari(metin, yaz=True):
    """Mutasyon surucusunun de kosturdugu cekirdek. Dondurur: hata listesi."""
    yerel = []

    def kontrol(kosul, mesaj):
        IDDIA[0] += 1
        if not kosul:
            yerel.append(mesaj)
            if yaz:
                print("  ❌ %s" % mesaj)

    for yol in ACIK_OLMASI_GEREKEN:
        kontrol(robots_karari(metin, yol) is True,
                "ACIK kalmasi gereken yol KAPANDI: %s" % yol)
    fp = katalogdan_yanlis_pozitif_yollari()
    kapanan = [y for y in fp if robots_karari(metin, y) is not True]
    kontrol(not kapanan,
            "YANLIS-POZITIF: alt-dizeli %d kanonik yol kapandi (or. %s)"
            % (len(kapanan), kapanan[:3]))
    for yol in KAPALI_OLMASI_GEREKEN:
        kontrol(robots_karari(metin, yol) is False,
                "KAPANMASI gereken parametreli URL ACIK: %s" % yol)
    kontrol(re.search(r"(?m)^Sitemap:\s*https://pruvo3d\.com/sitemap\.xml\s*$", metin)
            is not None, "Sitemap satiri yok/bozuk")
    kontrol(re.search(r"(?m)^User-agent:\s*\*\s*$", metin) is not None,
            "User-agent: * satiri yok")
    return yerel, len(fp)


# ------------------------------------------------- mutasyon
MUTANTLAR = [
    ("desen GENISLETILDI: Disallow: /",
     'satirlar.append("Disallow: /*?" + ad + "=")',
     'satirlar.append("Disallow: /")', True),
    ("sorgu CAPASI dustu (/*ara ...) — yanlis-pozitif",
     'satirlar.append("Disallow: /*?" + ad + "=")\n'
     '        satirlar.append("Disallow: /*&" + ad + "=")',
     'satirlar.append("Disallow: /*" + ad)', True),
    ("& bicimi SILINDI — ikinci siradaki parametre acik kalir",
     '        satirlar.append("Disallow: /*&" + ad + "=")\n', ''),
    ("Sitemap satiri SILINDI",
     'satirlar += ["", "Sitemap: " + SITE + "/sitemap.xml", ""]',
     'satirlar += [""]', True),
    # KONTROL MUTANTI — davranissiz: iki Disallow satirinin SIRASI degisti.
    ("KONTROL: Disallow satirlarinin sirasi degisti (davranissiz)",
     '        satirlar.append("Disallow: /*?" + ad + "=")\n'
     '        satirlar.append("Disallow: /*&" + ad + "=")',
     '        satirlar.append("Disallow: /*&" + ad + "=")\n'
     '        satirlar.append("Disallow: /*?" + ad + "=")', False),
]


def _mutant_metni(kaynak, eski, yeni):
    return kaynak.replace(eski, yeni)


def mutasyon_ayagi(gercek_metin):
    print("-- 5) MUTASYON --")
    kaynak = open(os.path.join(ARAC, "build.py"), encoding="utf-8").read()
    gecen = 0
    for kayit in MUTANTLAR:
        ad, eski, yeni = kayit[0], kayit[1], kayit[2]
        kirmizi_bekleniyor = kayit[3] if len(kayit) > 3 else True
        IDDIA[0] += 1
        if kaynak.count(eski) != 1:
            HATA.append("mutant capasi bulunamadi (%d): %s" % (kaynak.count(eski), ad))
            print("  ❌ CAPA YOK (%d): %s" % (kaynak.count(eski), ad))
            continue
        tmp = tempfile.mkdtemp(prefix="robots-mut-")
        try:
            farm = os.path.join(tmp, "tools")
            os.makedirs(farm)
            for isim in os.listdir(ARAC):
                if isim != "build.py":
                    os.symlink(os.path.join(ARAC, isim), os.path.join(farm, isim))
            for isim in os.listdir(KOK):
                if isim not in ("tools", ".git"):
                    os.symlink(os.path.join(KOK, isim), os.path.join(tmp, isim))
            with open(os.path.join(farm, "build.py"), "w", encoding="utf-8") as f:
                f.write(_mutant_metni(kaynak, eski, yeni))
            surucu = os.path.join(tmp, "surucu.py")
            with open(surucu, "w", encoding="utf-8") as f:
                f.write(SURUCU % (json.dumps(farm), json.dumps(ARAC)))
            r = subprocess.run(("python3", surucu), capture_output=True, text=True)
            damga = [s for s in (r.stdout or "").splitlines()
                     if s.startswith("SURUCU HATA:")]
            if not damga:
                HATA.append("mutant surucusu COKTU (olcum yok): " + ad)
                print("  ❌ COKME: %s\n     %s" % (ad, (r.stdout + r.stderr)[-300:]))
                continue
            kirmizi = int(damga[0].split(":")[1]) > 0
            if kirmizi == kirmizi_bekleniyor:
                gecen += 1
                print("  ✅ %s -> %s" % (ad, "KIRMIZI" if kirmizi else "YESIL"))
            else:
                HATA.append("mutant beklenen isareti vermedi: " + ad)
                print("  ❌ %s -> %s (beklenen %s)" % (
                    ad, "KIRMIZI" if kirmizi else "YESIL",
                    "KIRMIZI" if kirmizi_bekleniyor else "YESIL"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("  mutant: %d/%d beklenen isareti verdi" % (gecen, len(MUTANTLAR)))


SURUCU = '''# otomatik uretildi — robots mutasyon surucusu
import importlib.machinery, os, sys
sys.dont_write_bytecode = True
FARM, ARAC = %s, %s
sys.path.insert(0, FARM)
build = importlib.machinery.SourceFileLoader(
    "build", os.path.join(FARM, "build.py")).load_module()
kapi = importlib.machinery.SourceFileLoader(
    "kapi", os.path.join(ARAC, "robots-kapisi-test.py")).load_module()
hata, _n = kapi.robots_iddialari(build.render_robots(), yaz=False)
print("SURUCU HATA:", len(hata))
sys.exit(1 if hata else 0)
'''


def main():
    eslestirici_dogrula()
    import importlib
    build = importlib.import_module("build")
    metin = build.render_robots()
    print("-- uretilen robots.txt --")
    for satir in metin.splitlines():
        print("   | " + satir)
    print("-- 2/3/4) ACIK / KAPALI / SITEMAP --")
    yerel, fp_n = robots_iddialari(metin)
    HATA.extend(yerel)
    print("  yanlis-pozitif korpusu: %d kanonik yol (katalogdan turetildi)" % fp_n)
    mutasyon_ayagi(metin)

    print("\nIDDIA: %d · HATA: %d" % (IDDIA[0], len(HATA)))
    if HATA:
        print("SONUC: KIRMIZI ❌")
        for h in HATA:
            print("   -", h)
        return 1
    print("SONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
