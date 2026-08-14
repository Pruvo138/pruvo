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
import tempfile
import time

TOOLS = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, TOOLS)

import mutasyon_kopya as mk                                        # noqa: E402

# 🔴 MUTASYON KOPYAYA UYGULANIR, CANLI AGACA ASLA (12 Agu 2026, bagimsiz curutucu olctu).
# ESKI TASARIM: mutant CANLI `tools/marka_model_build.py`ye yaziliyor, diske
# `*.mutasyon-yedek` birakilip atexit/sinyal kancalariyla geri aliniyordu. Kosum KESILIRSE
# yedek AGACTA KALIYOR ve KARDES nobetciyi kirmizi yakiyor: olculdu — artik yedek yuzunden
# `marka-model-test.py` rc=1 verdi ("bolum kimligi ayristi"), AYNI SHA'nin temiz kopyasinda
# rc=0. Yani bu surucunun YAN ETKISI baska bir kapinin hukmu olarak okundu
# ([[kapi-yan-etkisi-gizli-onkosul]]). Artik `tools/` gecici bir koke KOPYALANIR, kokun
# geri kalani sembolik baglanir; canli agac bas/son damgayla KANITLI olarak dokunulmaz.
CANLI_HEDEF = os.path.join(TOOLS, "marka_model_build.py")
# Kopya kok kurulunca doldurulur (mutasyonun ve kapi kosumunun TEK yeri).
KOPYA = {"kok": None, "hedef": None, "kapi": None, "artim": None}

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

    # ---- bagimsiz curutmenin actigi kirmizilarin nobetcileri (X1/X3/X4) ----
    ("X3_TESLIM_ADRESI_BOZ",
     [('    manifest = {"yuk": "/marka/" + marka_slug + "/parcalar.json", "uc": ctx["EDGE_UC"],',
       '    manifest = {"yuk": "/marka/" + marka_slug + "/parcalar.json", '
       '"uc": "https://yok-boyle-uc.invalid",')],
     "TESLIM YOLU bozuldu (edge ucu ölü adrese çevrildi): canlıda 32 büyük marka sayfası "
     "tek ek kart çizmez. Testler adresi sayfanın KENDİ beyanından okusaydı bu mutant "
     "YEŞİL geçerdi (bağımsız çürütmenin bulduğu tautoloji)"),

    ("X4_TUMUNU_GOSTER_OLU",
     [("    function devam(hepsi){\n      if(mesgul){ return; }",
       "    function devam(hepsi){\n      if(true){ return; }")],
     '"Tümünü göster" ve kaydırmada artım ÖLDÜRÜLDÜ: kullanıcı markanın tamamını '
     "GÖREMEZ (SSR'de basılı N kart + düz bağ listesinde kalır)"),

    ("X1_KART_N_DEGISTIR",
     [("MARKA_KART_N = 80", "MARKA_KART_N = 40")],
     "SSR'de basılan kart sayısı sessizce yarıya indi: kapı sabiti İTHAL etseydi bu "
     "mutant YEŞİL kalırdı (davranışsal çapa `BEKLENEN_KART_N` ile ölçülür)"),
]

KONTROL = ("KONTROL_YORUM",
           [("# --------------------------------------------------------------------- sayfa üreticileri",
             "# --------------------------------------------------------------------- sayfa üreticileri\n# kontrol mutantı: yalnız yorum (davranış DEĞİŞMEZ)")],
           "yalnız yorum satırı — kapı YEŞİL kalmalı")


def oku():
    with io.open(KOPYA["hedef"], encoding="utf-8") as f:
        return f.read()


def yaz(metin):
    """Mutanti KOPYAYA yaz (canli agac ASLA yazilmaz — bkz. dosya basi)."""
    with io.open(KOPYA["hedef"], "w", encoding="utf-8") as f:
        f.write(metin)
    # Aynı uzunlukta + aynı saniyede yazılan mutasyon UYGULANMAYABİLİR (mtime çözünürlüğü /
    # bytecode önbelleği). mtime'ı ileri it ve pycache'i sil.
    now = time.time() + 2
    os.utime(KOPYA["hedef"], (now, now))
    shutil.rmtree(os.path.join(KOPYA["kok"], "tools", "__pycache__"), ignore_errors=True)


def iz():
    cp = subprocess.run([sys.executable, KOPYA["kapi"], "--iz"], capture_output=True,
                        text=True, cwd=KOPYA["kok"])
    m = re.search(r"IZ=([0-9a-f]+)", cp.stdout or "")
    return m.group(1) if m else None


def _tek_kostur(cmd, onek):
    """Bir nöbetçiyi koştur; düşen iddia KİMLİKLERİNİ topla (önekli, iki araç karışmasın)."""
    cp = subprocess.run(cmd, capture_output=True, text=True,
                        cwd=KOPYA["kok"], timeout=3600)
    cikti = (cp.stdout or "") + (cp.stderr or "")
    dusen = set()
    for satir in cikti.splitlines():
        s = satir.strip()
        if s.startswith("DUSEN "):
            dusen.add(onek + ":" + s[6:].split(" — ")[0].strip())
    m = re.search(r"IDDIA=(\d+)/(\d+)", cikti)
    return {"rc": cp.returncode, "dusen": dusen,
            "cokme": "Traceback (most recent call last)" in cikti,
            "iddia": (int(m.group(1)), int(m.group(2))) if m else None}


def kapiyi_kostur():
    """İKİ nöbetçi birlikte: SSR kapısı + istemci davranış testi.

    🔴 NEDEN İKİSİ: bazı kusurlar YALNIZ davranışta görünür ("tümünü göster" ölü) ve
    yalnız kapıyı koşturan bir batarya onları HAYATTA bırakır — bağımsız çürütme X4'ü
    tam böyle buldu. İkisinin düşen kümesi BİRLEŞTİRİLİR; kimlikler araç önekiyle
    ayrılır ki hangi katmanın konuştuğu görünsün."""
    a = _tek_kostur([sys.executable, KOPYA["kapi"]], "KAPI")
    b = _tek_kostur([sys.executable, KOPYA["artim"]], "ARTIM")
    dusen = a["dusen"] | b["dusen"]
    aileler = {}
    for d in dusen:
        arac, kimlik = d.split(":", 1)
        aileler[arac + ":" + kimlik.split("/")[0].split(" ")[0]] = \
            aileler.get(arac + ":" + kimlik.split("/")[0].split(" ")[0], 0) + 1
    return {"rc": (1 if (a["rc"] or b["rc"]) else 0), "dusen": dusen, "aileler": aileler,
            "cokme": a["cokme"] or b["cokme"],
            "iddia": a["iddia"], "iddia_artim": b["iddia"],
            "rc_kapi": a["rc"], "rc_artim": b["rc"], "kirpik": ""}


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
    k86 = "--k86" in sys.argv[1:]
    mutantlar = ([m for m in MUTANTLAR if m[0] == "X4_TUMUNU_GOSTER_OLU"]
                 if k86 else MUTANTLAR)
    # 🔴 CANLI AGACIN DAMGASI: bu surucu artik canli dosyaya YAZMIYOR ve bunu BEYAN
    # ETMIYOR, OLCUYOR. Bas/son damga esit degilse ya da artik `*-yedek` dosyasi kaldiysa
    # hukum KIRMIZI olur ("geri aldim" iddiasi bu depoda kanit sayilmaz).
    damga_bas = mk.agac_damgasi([CANLI_HEDEF])
    tmp = tempfile.mkdtemp(prefix="mm-bolum-mutasyon-")
    sonuc = {}
    try:
        KOPYA["kok"] = mk.kopya_kok(tmp)
        KOPYA["hedef"] = os.path.join(KOPYA["kok"], "tools", "marka_model_build.py")
        KOPYA["kapi"] = os.path.join(KOPYA["kok"], "tools", "marka-sayac-kapisi.py")
        KOPYA["artim"] = os.path.join(KOPYA["kok"], "tools", "marka-artim-test.py")
        taban = oku()
        taban_iz = iz()
        print("TABAN IZ =", taban_iz)
        # ---------------------------------------------------------- KATMAN A
        print()
        print("== KATMAN A: JENERATÖRÜN İÇ FAIL-CLOSED'U (mutant TEK BAŞINA) ==")
        for ad, ciftler, _acik in mutantlar:
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
        for ad, ciftler, acik in mutantlar + [KONTROL]:
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
        shutil.rmtree(tmp, ignore_errors=True)

    # ---------------------------------------------------------------- HÜKÜM
    damga_son = mk.agac_damgasi([CANLI_HEDEF])
    agac_temiz = damga_bas == damga_son and not damga_son[1]
    print()
    print("AGAC_DAMGASI bas=%s son=%s artik=%s"
          % (damga_bas[0], damga_son[0], damga_son[1]))
    print("AGAC_KIRLILIGI =", "YOK" if agac_temiz else "VAR")
    print()
    print("== HUKUM ==")
    hatalar = []
    if not agac_temiz:
        hatalar.append("CALISMA AGACI KIRLENDI (mutasyon kopyaya uygulanmali): %s"
                       % (damga_son[1] or "damga degisti",))
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
    print("KATMAN_B_OLDURULEN = %d/%d" % (len(b_kumeleri), len(mutantlar)))
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
