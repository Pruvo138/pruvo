#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL KAPISI — sitemap <lastmod> GERCEK icerik-degisim tarihini gostersin.

Olculen kusur (11 Agu 2026): canli sitemap'te 26.696 URL'in HEPSI ayni <lastmod>
(benzersiz lastmod = 1). Bu kapi kusurun geri gelmesini KIRMIZI yakar.

IDDIALAR (calistirilabilir):
  1  KARARLILIK       — ayni katalog+gecmisle iki kez uret -> lastmod'lar BIREBIR ayni,
                        bugune KAYMIYOR.
  2  TEKIL DEGISIM    — tek urunun icerigi degisince YALNIZ o URL'in tarihi degisiyor.
  3  UYDURMA YOK      — gecis GORULMEDIYSE (tavan asildi / gecmis yok) tarih URETILMEZ,
                        o URL'de <lastmod> etiketi HIC BASILMAZ.
  4  DAGILIM          — uretilen sitemap'te benzersiz lastmod > 1 (tek degere duserse
                        kusur geri gelmis demektir).
  5  URL KAYBI YOK    — lastmod'lu/lastmod'suz fark etmez, URL sayisi degismiyor; XML
                        sitemap semasina gore gecerli.
  6  MUTASYON         — hash karsilastirmasini sokmek / hep TODAY basmak / cozulemeyene
                        TODAY yazmak KIRMIZI yakmali; KONTROL mutanti (davranissiz
                        degisiklik) YESIL kalmali ([[beyan-edilmis-survivor]] —
                        ayirt edici mutant yoksa eksen ayri iddia degildir).

Kosum:  python3 tools/sitemap-damga-test.py
        python3 tools/sitemap-damga-test.py --mutasyon   (yalniz mutasyon ayagi)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools")
sys.path.insert(0, ARAC)
import sitemap_damga as sd                                    # noqa: E402

IDDIA = [0]
HATA = []


def bekle(kosul, mesaj):
    IDDIA[0] += 1
    if not kosul:
        HATA.append(mesaj)
        print("  ❌ %s" % mesaj)
    return bool(kosul)


# ------------------------------------------------------------- sentetik depo
URUN_A = {"id": "a-urun", "kategori": "Marin", "baslik": "A", "aciklama": "a",
          "fiyat": "100 TL", "gorseller": ["https://m/a.jpg"], "marka": []}
URUN_B = {"id": "b-urun", "kategori": "Otomobil", "baslik": "B", "aciklama": "b",
          "fiyat": "200 TL", "gorseller": ["https://m/b.jpg"], "marka": ["Audi"]}
URUN_C = {"id": "c-urun", "kategori": "Ev", "baslik": "C", "aciklama": "c",
          "fiyat": "300 TL", "gorseller": ["https://m/c.jpg"], "marka": []}


def _git(kok, *argv, **kw):
    cev = dict(os.environ)
    cev.update(kw.get("cev") or {})
    r = subprocess.run(("git",) + argv, cwd=kok, capture_output=True,
                       text=True, env=cev)
    if r.returncode != 0 and not kw.get("hatayi_yut"):
        raise RuntimeError("git %s -> %s" % (" ".join(argv), r.stderr[:200]))
    return r


def _yaz_json(kok, urunler):
    with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(urunler, f, ensure_ascii=False, indent=2)


def _commit(kok, tarih_iso):
    damga = tarih_iso + "T12:00:00+03:00"
    _git(kok, "add", "-A")
    _git(kok, "commit", "-q", "-m", "parti", cev={
        "GIT_AUTHOR_DATE": damga, "GIT_COMMITTER_DATE": damga,
        "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@t"})


def sentetik_depo(dizin):
    """4 commit'lik gercek bir git deposu kurar (sahte git kaynagi DEGIL —
    hukum gercek `git log`/`git show` uzerinden verilir).

    T1 2026-01-05: A, B          T2 2026-02-10: B degisti + C eklendi
    T3 2026-03-15: urunler.json'a DOKUNMAYAN commit (yurumede atlanmali)
    T4 2026-04-20: A degisti
    """
    _git(dizin, "init", "-q", "-b", "main")
    _git(dizin, "config", "user.email", "t@t")
    _git(dizin, "config", "user.name", "T")
    _yaz_json(dizin, [dict(URUN_A), dict(URUN_B)])
    _commit(dizin, "2026-01-05")
    b2 = dict(URUN_B, fiyat="222 TL")
    _yaz_json(dizin, [dict(URUN_A), b2, dict(URUN_C)])
    _commit(dizin, "2026-02-10")
    with open(os.path.join(dizin, "NOT.md"), "w", encoding="utf-8") as f:
        f.write("alakasiz\n")
    _commit(dizin, "2026-03-15")
    a2 = dict(URUN_A, baslik="A v2")
    _yaz_json(dizin, [a2, b2, dict(URUN_C)])
    _commit(dizin, "2026-04-20")
    return [a2, b2, dict(URUN_C)]


class SayanGit(sd.GitKaynak):
    """Git'e KAC KEZ inildigini sayar (defter isabetinde inilmemeli)."""

    def __init__(self, *a, **kw):
        sd.GitKaynak.__init__(self, *a, **kw)
        self.okuma = 0

    def hashler(self, sha, sadece=None):
        self.okuma += 1
        return sd.GitKaynak.hashler(self, sha, sadece=sadece)


# ------------------------------------------------------------- cekirdek iddia
def cekirdek(modul, dizin, urunler):
    """Mutasyon surucusunun de kosturdugu iddialar. (modul = sitemap_damga)"""
    yerel_hata = []

    def yerel(kosul, mesaj):
        IDDIA[0] += 1
        if not kosul:
            yerel_hata.append(mesaj)
            print("  ❌ %s" % mesaj)

    defter = os.path.join(dizin, modul.DEFTER_ADI)
    mevcut = modul.hashleri_hesapla(urunler)

    # --- 1) bos defter + tam gecmis: tarihler GIT'ten turer
    t1, tani1 = modul.cozumle(mevcut, {"damgalar": {}}, modul.GitKaynak(dizin))
    yerel(t1.get("a-urun") == "2026-04-20",
          "A'nin tarihi son degisim commit'i degil: %r" % t1.get("a-urun"))
    yerel(t1.get("b-urun") == "2026-02-10",
          "B'nin tarihi 2026-02-10 degil: %r" % t1.get("b-urun"))
    yerel(t1.get("c-urun") == "2026-02-10",
          "C'nin tarihi 2026-02-10 degil: %r" % t1.get("c-urun"))
    bugun = modul.bugun()
    yerel(all(v != bugun for v in t1.values()),
          "tarihler BUGUNE kaymis: %r" % sorted(set(t1.values())))

    # --- 2) KARARLILIK: ikinci uretim birebir ayni
    t2, _ = modul.cozumle(mevcut, {"damgalar": {}}, modul.GitKaynak(dizin))
    yerel(t1 == t2, "iki uretim ayni degil: %r != %r" % (t1, t2))

    # --- 3) defter isabeti: git'e HIC inilmiyor + tarih defterden
    modul.defter_yaz(defter, "sha0",
                     {modul.id_anahtari(k): {"h": mevcut[k], "t": t1[k]} for k in t1})
    yuklu = modul.defter_yukle(defter)
    # Defter ANAHTARI hash'tir: okunabilir urun id'si dosyaya GIRMEZ (pre-push
    # sizinti nobetcisinin aday butcesi 484.129 > 150.000 ile patlamisti).
    metin = open(defter, encoding="utf-8").read()
    yerel(all(pid not in metin for pid in mevcut),
          "defterde okunabilir urun id'si var (jeton kutlesi + public depo)")
    sayan = SayanGit(dizin)
    t3, tani3 = modul.cozumle(mevcut, yuklu, sayan)
    yerel(t3 == t1, "defterden okunan tarihler git'inkiyle ayni degil")
    yerel(sayan.okuma == 0,
          "defter tam isabetliyken git'e inildi (%d okuma)" % sayan.okuma)
    yerel(tani3["defterden"] == len(mevcut) and tani3["gitten"] == 0,
          "tani yanlis: %r" % tani3)

    # --- 4) TEKIL DEGISIM: yalniz degisen urunun tarihi degisiyor
    degisen = [dict(p) for p in urunler]
    for p in degisen:
        if p["id"] == "b-urun":
            p["fiyat"] = "999 TL"
    _yaz_json(dizin, degisen)
    _commit(dizin, "2026-06-01")
    mevcut2 = modul.hashleri_hesapla(degisen)
    t4, _ = modul.cozumle(mevcut2, yuklu, modul.GitKaynak(dizin))
    yerel(t4.get("b-urun") == "2026-06-01",
          "degisen urunun tarihi guncellenmedi: %r" % t4.get("b-urun"))
    yerel(t4.get("a-urun") == t1.get("a-urun") and t4.get("c-urun") == t1.get("c-urun"),
          "degismeyen urunlerin tarihi oynadi: %r" % t4)

    # --- 5) UYDURMA YOK: tavan 1 -> gecis gorulemeyen id SONUCTA YOK
    t5, tani5 = modul.cozumle(mevcut2, {"damgalar": {}},
                              modul.GitKaynak(dizin), tavan=1)
    yerel("a-urun" not in t5 and "c-urun" not in t5,
          "tavan asilinca uydurma tarih yazildi: %r" % t5)
    yerel(tani5["cozulemedi"] >= 2, "cozulemedi sayaci yanlis: %r" % tani5)

    # --- 6) gecmis YOKSA hicbir tarih uretilmez
    class BosGit(object):
        def commitler(self):
            return []

        def tam_gecmis_mi(self):
            return False

        def hashler(self, sha, sadece=None):
            return {}

    t6, tani6 = modul.cozumle(mevcut2, {"damgalar": {}}, BosGit())
    yerel(t6 == {}, "gecmissiz ortamda tarih uretildi: %r" % t6)
    yerel(tani6["cozulemedi"] == len(mevcut2), "gecmissiz tani yanlis: %r" % tani6)

    # --- 6b) SURE BUTCESI dolunca: kapi ASILMAZ, tarih de UYDURULMAZ.
    #        Saat enjekte edilir: ilk commit islenir, ikinci turda butce dolar ->
    #        `aday` DOLU ama gecis GORULMEMISTIR; tarih basilmamali.
    class Saat(object):
        def __init__(self, degerler):
            self.degerler = list(degerler)

        def __call__(self):
            return self.degerler.pop(0) if self.degerler else 10 ** 6

    t6b, tani6b = modul.cozumle(mevcut2, {"damgalar": {}}, modul.GitKaynak(dizin),
                                tavan=None, sure_butcesi=10,
                                saat=Saat([0, 0, 1000, 1000, 1000]))
    yerel(tani6b["sure_asildi"] is True, "sure butcesi tetiklenmedi: %r" % tani6b)
    yerel("a-urun" not in t6b and "c-urun" not in t6b,
          "sure butcesi dolunca uydurma tarih yazildi: %r" % t6b)

    # --- 6c) ONBELLEK TAZELEME: sitemap_tarihleri defteri yazar (git'e girmez)
    onbellek = os.path.join(dizin, "onbellek-damga.json")
    url_t, _tani = modul.sitemap_tarihleri(
        degisen, lambda pid: "https://x/urun/" + pid + "/", onbellek, dizin)
    yerel(os.path.exists(onbellek), "onbellek dosyasi yazilmadi")
    yeniden = modul.defter_yukle(onbellek)
    yerel(len(yeniden.get("damgalar") or {}) == len(degisen),
          "onbellek eksik yazildi: %r" % len(yeniden.get("damgalar") or {}))
    yerel(url_t.get("https://x/urun/b-urun/") == "2026-06-01",
          "sitemap_tarihleri urun URL tarihi yanlis: %r" % url_t)

    # --- 7) COMMIT EDILMEMIS icerik: en yeni commit'te bile hash tutmuyor ->
    #        GECIS GORULMEDI -> tarih URETILMEZ (fail-closed; digerleri etkilenmez)
    sapmis = [dict(p) for p in degisen]
    for p in sapmis:
        if p["id"] == "c-urun":
            p["baslik"] = "C taslak (commit EDILMEDI)"
    mevcut3 = modul.hashleri_hesapla(sapmis)
    t7, _ = modul.cozumle(mevcut3, {"damgalar": {}}, modul.GitKaynak(dizin))
    yerel("c-urun" not in t7,
          "commit EDILMEMIS icerige tarih uretildi: %r" % t7.get("c-urun"))
    yerel(t7.get("a-urun") == "2026-04-20" and t7.get("b-urun") == "2026-06-01",
          "sapma digerlerinin tarihini bozdu: %r" % t7)

    # depoyu geri sar (mutasyon surucusu ayni dizini tekrar kullanabilsin)
    _git(dizin, "reset", "-q", "--hard", "HEAD~1")
    return yerel_hata


# ------------------------------------------------------------- sitemap yuzeyi
def sitemap_yuzeyi():
    """build.render_sitemap: etiket basma kurali + URL kaybi + sema."""
    import importlib
    build = importlib.import_module("build")
    urunler = [dict(URUN_A), dict(URUN_B), dict(URUN_C)]
    tarihler = {build.product_url("a-urun"): "2026-04-20",
                build.product_url("b-urun"): "2026-02-10",
                build.SITE + "/": "2026-04-20"}
    xml = build.render_sitemap(urunler, extra_urls=None, tarihler=tarihler)

    NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    kok = ET.fromstring(xml)                       # sema/ayristirma gecerliligi
    bekle(kok.tag == NS + "urlset", "kok etiketi urlset degil: %s" % kok.tag)
    kayitlar = kok.findall(NS + "url")
    loclar = [u.find(NS + "loc").text for u in kayitlar]
    lm = {u.find(NS + "loc").text:
          (u.find(NS + "lastmod").text if u.find(NS + "lastmod") is not None else None)
          for u in kayitlar}

    bekle(lm.get(build.product_url("a-urun")) == "2026-04-20",
          "A urun URL'inde tarih yanlis: %r" % lm.get(build.product_url("a-urun")))
    bekle(lm.get(build.product_url("c-urun")) is None,
          "tarihi BILINMEYEN URL'de <lastmod> BASILDI: %r"
          % lm.get(build.product_url("c-urun")))
    bekle(len(set(v for v in lm.values() if v)) > 1,
          "benzersiz lastmod sayisi 1 — kusur geri gelmis")

    # URL kaybi yok: eski (hep-TODAY) uretimle AYNI URL kumesi
    beklenen = [build.SITE + "/"] + [build.SITE + "/" + s + "/" for s in build.SITEMAP_SLUGS] \
        + [build.product_url(p["id"]) for p in urunler]
    bekle(loclar == beklenen,
          "URL kumesi/sirasi degisti (%d != %d)" % (len(loclar), len(beklenen)))
    bugun = sd.bugun()
    bekle(all(v != bugun for v in lm.values() if v),
          "sitemap'te BUGUN tarihi var (kayma)")
    return xml


# ------------------------------------------------------------- mutasyon ayagi
MUTANTLAR = [
    # (dosya, ad, eski, yeni, KIRMIZI_bekleniyor_mu)
    ("sitemap_damga.py", "defter hash karsilastirmasi SOKULDU (hep bugun)",
     'if isinstance(kayit, dict) and kayit.get("h") == h and kayit.get("t"):',
     'if isinstance(kayit, dict) and kayit.get("t") and False:', True),
    ("sitemap_damga.py", "cozulemeyene BUGUN yazildi (uydurma tarih)",
     '    tani["cozulemedi"] = len(kalan)\n    tani["sure_sn"]',
     '    for _pid in kalan:\n        tarihler[_pid] = bugun()\n'
     '    tani["cozulemedi"] = len(kalan)\n    tani["sure_sn"]', True),
    ("sitemap_damga.py", "gecis GORULMEDEN tarih yazildi (fail-open)",
     '                if pid in aday:            # (a) GECIS GORULDU\n'
     '                    tarihler[pid] = aday[pid]',
     '                if True:            # (a) GECIS GORULDU\n'
     '                    tarihler[pid] = aday.get(pid, bugun())', True),
    ("sitemap_damga.py", "sure butcesi dolunca ADAY tarih basiliyor (fail-open)",
     '    ilk_commite_ulasildi = (not tani["tavan_asildi"]) and (\n'
     '        not tani["sure_asildi"]) and tam',
     '    ilk_commite_ulasildi = (not tani["tavan_asildi"]) and tam', True),
    ("build.py", "render_sitemap HEP bugunu basiyor (kusurun kendisi)",
     '        lastmod = ("    <lastmod>%s</lastmod>\\n" % esc(tarih)) if tarih else ""',
     '        lastmod = "    <lastmod>%s</lastmod>\\n" % esc(TODAY)', True),
    # KONTROL MUTANTI — davranisi DEGISTIRMEYEN degisiklik: YESIL kalmali.
    # ([[fikstur-degeri-mutasyon-koru]] / [[beyan-edilmis-survivor]]: ayirt edici
    #  olmayan mutant, kapinin "her diff'e kirmizi yakan" olmadigini kanitlar.)
    ("sitemap_damga.py", "KONTROL: yalnizca tani sozlugune alan eklendi",
     '    tani["cozulemedi"] = len(kalan)\n    tani["sure_sn"]',
     '    tani["cozulemedi"] = len(kalan)\n    tani["_kontrol"] = 1\n'
     '    tani["sure_sn"]', False),
]


SURUCU_KAYNAK = '''# otomatik uretildi — mutasyon surucusu (mutasyon KANITI yeniden uretilebilir)
import importlib.machinery, os, sys
sys.dont_write_bytecode = True          # [[mutasyon-bytecode-onbellegi]]
FARM, DEPO, ARAC = %s, %s, %s
sys.path.insert(0, FARM)
mut = importlib.machinery.SourceFileLoader(
    "sitemap_damga", os.path.join(FARM, "sitemap_damga.py")).load_module()
sys.modules["sitemap_damga"] = mut
kapi = importlib.machinery.SourceFileLoader(
    "kapi", os.path.join(ARAC, "sitemap-damga-test.py")).load_module()
sys.path.insert(0, FARM)                # kapi ARAC'i one almisti -> farm geri one
urunler = kapi.sentetik_depo(DEPO)
hata = list(kapi.cekirdek(mut, DEPO, urunler))
kapi.sitemap_yuzeyi()
hata += list(kapi.HATA)
print("SURUCU HATA:", len(hata))
sys.exit(1 if hata else 0)
'''


def _farm_kur(tmp, mutant_dosya, mutant_kaynak):
    """Depo kokunun SEMBOLIK KOPYASI: tools/ altindaki her dosya symlink, yalniz
    mutasyona ugrayan dosya GERCEK kopya. Boylece gercek repo hic kirletilmez."""
    koktmp = os.path.join(tmp, "kok")
    farm = os.path.join(koktmp, "tools")
    os.makedirs(farm)
    for isim in os.listdir(KOK):
        if isim in ("tools", ".git"):
            continue
        os.symlink(os.path.join(KOK, isim), os.path.join(koktmp, isim))
    for isim in os.listdir(ARAC):
        if isim == mutant_dosya:
            continue
        os.symlink(os.path.join(ARAC, isim), os.path.join(farm, isim))
    with open(os.path.join(farm, mutant_dosya), "w", encoding="utf-8") as f:
        f.write(mutant_kaynak)
    return farm


def mutasyon_ayagi():
    print("\n-- MUTASYON AYAGI --")
    gecen = 0
    for dosya, ad, eski, yeni, kirmizi_bekleniyor in MUTANTLAR:
        IDDIA[0] += 1
        kaynak = open(os.path.join(ARAC, dosya), encoding="utf-8").read()
        if kaynak.count(eski) != 1:
            HATA.append("mutant capasi bulunamadi (%d kez): %s"
                        % (kaynak.count(eski), ad))
            print("  ❌ CAPA YOK (%d): %s" % (kaynak.count(eski), ad))
            continue
        tmp = tempfile.mkdtemp(prefix="damga-mut-")
        try:
            farm = _farm_kur(tmp, dosya, kaynak.replace(eski, yeni))
            depo = os.path.join(tmp, "depo")
            os.makedirs(depo)
            surucu = os.path.join(tmp, "surucu.py")
            with open(surucu, "w", encoding="utf-8") as f:
                f.write(SURUCU_KAYNAK % (json.dumps(farm), json.dumps(depo),
                                         json.dumps(ARAC)))
            r = subprocess.run(("python3", surucu), capture_output=True, text=True)
            # 🔴 Cokme kirmizi ile KARISMASIN ([[mutasyon-kaniti-yeniden-uretilebilir]]):
            # kabul, cikis kodu degil "SURUCU HATA: n" satirinin BASILMASI + isareti.
            damga = [s for s in (r.stdout or "").splitlines()
                     if s.startswith("SURUCU HATA:")]
            if not damga:
                HATA.append("mutant surucusu COKTU (olcum yok): " + ad)
                print("  ❌ COKME (iddia olculemedi): %s\n     %s"
                      % (ad, (r.stdout + r.stderr).strip()[-400:]))
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
    return gecen


# ------------------------------------------------------------------ main
def main():
    yalniz_mut = "--mutasyon" in sys.argv
    if not yalniz_mut:
        print("-- CEKIRDEK (sentetik git deposu) --")
        tmp = tempfile.mkdtemp(prefix="damga-test-")
        try:
            urunler = sentetik_depo(tmp)
            HATA.extend(cekirdek(sd, tmp, urunler))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print("-- SITEMAP YUZEYI (build.render_sitemap) --")
        sitemap_yuzeyi()
    mutasyon_ayagi()

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
