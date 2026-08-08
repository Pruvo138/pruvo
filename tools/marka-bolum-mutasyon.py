#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BÖLÜM KİMLİĞİ / KART YÜZEYİ ONARIMININ MUTASYON KANITI — sürücü REPODA durur.

🔴 NEDEN VAR: "kapı yeşil" bir onarımın ÖLÇTÜĞÜNÜ kanıtlamaz. Anlatılan batarya kanıt
değildir; sürücü repoda durmalı ve yeniden koşturulabilmelidir
([[mutasyon-kaniti-yeniden-uretilebilir]]).

NE ÖLÇER — İKİ KATMAN AYRI AYRI ([[beyan-edilmis-survivor]]: "savunma derinliği" ancak her
katman TEK BAŞINA kırmızı yakabiliyorsa kanıttır):

  KATMAN A (jeneratörün kendi fail-closed'u): mutant TEK BAŞINA uygulanır. `bolum_ayrimi`
    içindeki kimlik kontrolü build'i DURDURMALI -> kapı `FAIL_CLOSED/jenerator` basar.
  KATMAN B (kapının kendisi): AYNI mutant + jeneratörün iç kontrolü DEVRE DIŞI. Artık
    yalnız KAPI konuşur; her mutant KENDİ iddia kümesini düşürmeli ve iki mutant AYNI
    kümeye düşmemeli (yoksa eksen ayırt edici değildir).

KABUL (çıkış kodu DEĞİL, ölçülen iddia):
  · Katman B'de her öldürücü mutant kırmızı + düşen iddia KÜMELERİ PARÇALI FARKLI.
  · Kontrol mutantı (yalnız yorum) YEŞİL.
  · Çökerek düşen mutant ÖLDÜRÜLMÜŞ SAYILMAZ (traceback ayrı raporlanır).
  · Mutasyonun DİSKTEN geri okunarak uygulandığı `--iz` (kaynak sha1) ile doğrulanır
    ([[mutasyon-bytecode-onbellegi]] · [[mutasyon-diske-yazma-tuzagi]]).

Kullanım: python3 tools/marka-bolum-mutasyon.py [--dokum]
"""
import io
import os
import re
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(TOOLS, "marka_model_build.py")
KAPI = os.path.join(TOOLS, "marka-sayac-kapisi.py")

# Jeneratörün İÇ fail-closed'u (katman A). Katman B'de bu SUSTURULUR ki kapı tek başına
# ölçülebilsin.
IC_KONTROL = ('    if sayilar["kart"] + sayilar["kova"] != sayilar["toplam"]:',
              '    if False:')

# --------------------------------------------------------------------------- mutantlar
# Her mutant = (ad, [(eski, yeni), ...], aciklama)
MUTANTLAR = [
    ("M1_KIMLIK_KALDIR",
     [('               model_uyelik.get(p.get("id")) or []] for p in kalemler],',
       '               model_uyelik.get(p.get("id")) or []] for p in basili],')],
     "artım yükü yalnız SSR'de BASILI kalemleri taşır -> kart yüzeyi sessizce N'e daralır "
     "(kullanıcı 'tümünü göster'e bassa da markanın tümünü GÖREMEZ)"),

    ("M2_CAKISMA_KUTSA",
     [("    kart_urunleri = [p for p in _tekil(*kart_kollari) if p.get(\"id\") not in kova_ids]",
       "    kart_urunleri = list(_tekil(*kart_kollari))")],
     "bölüm elemesi KALDIRILDI = onarım öncesi yükleme dönüş (çakışma yine 'doğru davranış')"),

    ("M3_TEKIL_KALDIR",
     [("            if anahtar in gorulen:\n                continue",
       "            if False:\n                continue")],
     "tekilleştirme KALDIRILDI -> aynı ürün sayfada iki kez"),

    ("M4_MARKA_ONLY_ELEME_GERI",
     [("    toplam = sayilar[\"toplam\"]",
       "    yerel = _tekil(yerel, d[\"marka_only\"])\n    toplam = sayilar[\"toplam\"]")],
     "`marka_only` kolu elemeden SONRA geri eklendi = teşhis edilen (B) kusurunun aynısı "
     "(kovada görünen ürün yerel bölümde de listelenir)"),

    ("M5_DUZ_BAG_SUZGECI_KALDIR",
     [('    var duzler = dok.querySelectorAll(".mm-kalan-oge[data-kat]");',
       '    var duzler = [];')],
     "düz bağ öğeleri kapsam süzgecinden ÇIKARILDI -> ?kategori= altında başka kategorinin "
     "parça adları ekranda KALIR (kartlarda kapatılan kaçağın aynısı, bağ listesinde)"),
]

KONTROL = ("KONTROL_YORUM",
           [("# --------------------------------------------------------------------- sayfa üreticileri",
             "# --------------------------------------------------------------------- sayfa üreticileri\n# kontrol mutantı: yalnız yorum (davranış DEĞİŞMEZ)")],
           "yalnız yorum satırı — kapı YEŞİL kalmalı")


def oku():
    with io.open(HEDEF, encoding="utf-8") as f:
        return f.read()


def yaz(metin):
    with io.open(HEDEF, "w", encoding="utf-8") as f:
        f.write(metin)
    # Aynı uzunlukta + aynı saniyede yazılan mutasyon UYGULANMAYABİLİR (mtime çözünürlüğü /
    # bytecode önbelleği). mtime'ı ileri it ve pycache'i sil.
    now = time.time() + 2
    os.utime(HEDEF, (now, now))
    pc = os.path.join(TOOLS, "__pycache__")
    shutil.rmtree(pc, ignore_errors=True)


def iz():
    cp = subprocess.run([sys.executable, KAPI, "--iz"], capture_output=True, text=True,
                        cwd=os.path.dirname(TOOLS))
    m = re.search(r"IZ=([0-9a-f]+)", cp.stdout or "")
    return m.group(1) if m else None


def kapiyi_kostur():
    cp = subprocess.run([sys.executable, KAPI], capture_output=True, text=True,
                        cwd=os.path.dirname(TOOLS), timeout=3600)
    cikti = (cp.stdout or "") + (cp.stderr or "")
    dusen = set()
    for satir in cikti.splitlines():
        s = satir.strip()
        if s.startswith("DUSEN "):
            dusen.add(s[6:].split(" — ")[0].strip())
    aileler = {}
    for d in dusen:
        aileler[d.split("/")[0]] = aileler.get(d.split("/")[0], 0) + 1
    m = re.search(r"IDDIA=(\d+)/(\d+)\s+DUSEN=(\d+)", cikti)
    cokme = "Traceback (most recent call last)" in cikti
    return {"rc": cp.returncode, "dusen": dusen, "aileler": aileler, "cokme": cokme,
            "iddia": (int(m.group(1)), int(m.group(2))) if m else None,
            "kirpik": cikti[-500:]}


def uygula(taban, ciftler, ic_kontrol_kapali):
    metin = taban
    for eski, yeni in ciftler:
        if eski not in metin:
            return None, "ANCHOR BULUNAMADI: %r" % (eski[:80],)
        metin = metin.replace(eski, yeni, 1)
    if ic_kontrol_kapali:
        if IC_KONTROL[0] not in metin:
            return None, "IC_KONTROL anchor bulunamadı"
        metin = metin.replace(IC_KONTROL[0], IC_KONTROL[1], 1)
    return metin, None


def main():
    dokum = "--dokum" in sys.argv[1:]
    taban = oku()
    taban_iz = iz()
    print("TABAN IZ =", taban_iz)
    sonuc = {}
    try:
        # ---------------------------------------------------------- KATMAN A
        print()
        print("== KATMAN A: JENERATÖRÜN İÇ FAIL-CLOSED'U (mutant TEK BAŞINA) ==")
        for ad, ciftler, _acik in MUTANTLAR:
            metin, hata = uygula(taban, ciftler, False)
            if metin is None:
                print("  %-26s OLCULEMEDI: %s" % (ad, hata))
                sonuc[("A", ad)] = {"durum": "OLCULEMEDI"}
                continue
            yaz(metin)
            m_iz = iz()
            r = kapiyi_kostur()
            fc = any(d.startswith("FAIL_CLOSED/") for d in r["dusen"])
            sonuc[("A", ad)] = {"rc": r["rc"], "fail_closed": fc, "iz": m_iz,
                                "uygulandi": m_iz != taban_iz, "cokme": r["cokme"],
                                "aileler": r["aileler"]}
            print("  %-26s rc=%s uygulandi=%s fail_closed=%s cokme=%s aileler=%s"
                  % (ad, r["rc"], m_iz != taban_iz, fc, r["cokme"],
                     sorted(r["aileler"].items())))
        # ---------------------------------------------------------- KATMAN B
        print()
        print("== KATMAN B: KAPI TEK BAŞINA (jeneratörün iç kontrolü DEVRE DIŞI) ==")
        for ad, ciftler, acik in MUTANTLAR + [KONTROL]:
            kontrol = ad == KONTROL[0]
            metin, hata = uygula(taban, ciftler, not kontrol)
            if metin is None:
                print("  %-26s OLCULEMEDI: %s" % (ad, hata))
                sonuc[("B", ad)] = {"durum": "OLCULEMEDI"}
                continue
            yaz(metin)
            m_iz = iz()
            r = kapiyi_kostur()
            sonuc[("B", ad)] = {"rc": r["rc"], "dusen": r["dusen"], "iz": m_iz,
                                "uygulandi": m_iz != taban_iz, "cokme": r["cokme"],
                                "aileler": r["aileler"], "kontrol": kontrol}
            print("  %-26s rc=%s uygulandi=%s cokme=%s iddia=%s"
                  % (ad, r["rc"], m_iz != taban_iz, r["cokme"], r["iddia"]))
            print("      aileler=%s" % (sorted(r["aileler"].items()),))
            if dokum:
                print("      ornek=%s" % (sorted(r["dusen"])[:4],))
            print("      >> %s" % acik)
    finally:
        yaz(taban)
        geri = iz()
        print()
        print("DOSYA GERI ALINDI, iz =", geri, "(taban ile ayni:", geri == taban_iz, ")")

    # ---------------------------------------------------------------- HÜKÜM
    print()
    print("== HUKUM ==")
    hatalar = []
    b_kumeleri = {}
    for (kat, ad), d in sonuc.items():
        if kat != "B" or d.get("durum") == "OLCULEMEDI":
            if d.get("durum") == "OLCULEMEDI":
                hatalar.append("%s/%s ÖLÇÜLEMEDİ" % (kat, ad))
            continue
        if not d["uygulandi"]:
            hatalar.append("%s mutasyonu UYGULANMADI (iz değişmedi)" % ad)
        if d["kontrol"]:
            if d["rc"] != 0:
                hatalar.append("KONTROL mutantı BOZULDU (rc=%s, aileler=%s)"
                               % (d["rc"], sorted(d["aileler"].items())))
            continue
        if d["cokme"]:
            hatalar.append("%s ÇÖKEREK düştü — ÖLDÜRÜLMÜŞ SAYILMAZ" % ad)
        elif d["rc"] != 1 or not d["dusen"]:
            hatalar.append("%s HAYATTA KALDI (rc=%s)" % (ad, d["rc"]))
        else:
            b_kumeleri[ad] = frozenset(d["dusen"])
    # KÜME AYIRT EDİCİLİĞİ: iki mutant AYNI iddia kümesine düşmemeli
    esler = []
    adlar = sorted(b_kumeleri)
    for i in range(len(adlar)):
        for j in range(i + 1, len(adlar)):
            if b_kumeleri[adlar[i]] == b_kumeleri[adlar[j]]:
                esler.append((adlar[i], adlar[j]))
    for a, b in esler:
        hatalar.append("AYNI KÜMEYE DÜŞEN ÇİFT: %s == %s (eksen ayırt edici değil)" % (a, b))
    # KATMAN A: jeneratörün iç kontrolü kendi başına konuşuyor mu
    a_konusan = [ad for (kat, ad), d in sonuc.items()
                 if kat == "A" and d.get("fail_closed")]
    print("KATMAN_A_FAIL_CLOSED_YAKALADI =", sorted(a_konusan))
    print("KATMAN_B_OLDURULEN = %d/%d" % (len(b_kumeleri), len(MUTANTLAR)))
    for ad in adlar:
        aileler = {}
        for d in b_kumeleri[ad]:
            aileler[d.split("/")[0]] = aileler.get(d.split("/")[0], 0) + 1
        print("   %-26s dusen=%4d  aileler=%s"
              % (ad, len(b_kumeleri[ad]), sorted(aileler.items())))
    print("AYNI_KUMEYE_DUSEN =", esler if esler else "YOK")
    kontrol_d = sonuc.get(("B", KONTROL[0])) or {}
    print("KONTROL =", "YESIL" if kontrol_d.get("rc") == 0 else "BOZULDU")
    if hatalar:
        print()
        for h in hatalar:
            print("  HATA: " + h)
        print("HUKUM=KIRMIZI")
        return 1
    print("HUKUM=YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
