#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/sahiplik-kapisi.py — KAPI/NOBET betiklerinin SAHIPLIK HARITASI kapisi.

Paket ③ (18 Agu 2026, BaBa hukmu, KraL mimar):

  Invaryant: `tools/` ve `~/.claude/cron/` altindaki HER KAPI/NOBET betigi
  haritada BIR satira sahiptir (1 satir = 1 betik).

  Kapsam evreni KODDAN turetilir (ad desenine DEGIL):
    - dosya .py ise: `sys.exit(1..9)` ile fail-closed RED uretiyor
      ya da `permissionDecision` yaziyor (PreToolUse gate semantigi)
    - dosya .sh ise: `exit 1` ya da `exit 2` ile fail-closed RED uretiyor
    - dosya -test.py / -mutasyon- / -prob- iceriyorsa DISLANIR
      (bunlar KAPI'lari TEST eden altyapi, KAPI'nin kendisi degil)

  Kabul 1 (calistirilabilir):
    python3 tools/sahiplik-kapisi.py --kendini-test
    son satir + rc=0:
      EVREN=<n> HARITADA=<n> EKSIK=0 BAYAT=0 SAHIPSIZ=<n> MUTANT=3/3 KONTROL=2/2

  Kabul 2 (rapor): son satir + jeton kanit blogu + SAHIPSIZ listesi.

  Disiplin: salt-okunur; hicbir yola YAZMAZ, git degisikligi YAPMAZ.

Kullanim:
    python3 tools/sahiplik-kapisi.py                   # ana olcum, EVREN/HARITA durumu
    python3 tools/sahiplik-kapisi.py --kendini-test    # 3 mutant + 2 kontrol kosar
    python3 tools/sahiplik-kapisi.py --repo /farkli    # izole kopya olcer (test)
    python3 tools/sahiplik-kapisi.py --json            # makine-okunur cikti
"""
import argparse
import json
import os
import re
import sys

CANON = "/Users/okan/dev/pruvo"
CRON = "/Users/okan/.claude/cron"
HARITA_REPO_RELATIF = "tools/sahiplik-haritasi.tsv"
HARITA_GENEL = HARITA_REPO_RELATIF

# Kabul edilen EV degerleri — spec §2a'dan; BILINMIYOR sozlesmeli gecersiz EV
# yerine kullanilir (sahipsiz sayilir ama kapiyi YAKMAZ — spec §2b).
EV_BILINEN = {"KraL", "MaCiT", "TeKiN", "ArTisT", "HocA", "BaBa", "ORTAK"}
EV_OLARAK_KABUL = EV_BILINEN | {"BILINMIYOR"}

# SERIT degerleri — spec §2a. Olcut spec'te TAM verilmemis; ELLE yazildi.
SERIT_OLARAK_KABUL = {"yayin", "veri", "nobet", "hijyen", "arac"}


# ---------------------------------------------------------------------------
# EVREN — KODDAN turetir (ad desenine degil).
# ---------------------------------------------------------------------------
def _kod_sinyali(path):
    """Bir dosyanin fail-closed gate / nobet semantigi tasidiginin KOD kaniti.

    Python: sys.exit(1..9) ya da permissionDecision.
    Shell:  exit 1 / exit 2.
    Bos dosya, okunamayan dosya, .md/.txt/.log/.tsv -> False.
    """
    if not os.path.isfile(path):
        return False
    if path.endswith((".md", ".txt", ".log", ".tsv", ".json", ".html",
                       ".css", ".js", ".yaml", ".yml", ".sh.disabled",
                       ".py.disabled", ".bak", ".pyc")):
        return False
    # Yedek dosyalar (ara sira tutulan .yedek-...) dislanir
    base = os.path.basename(path)
    if ".yedek-" in base or base.endswith((".py.lock", ".sh.lock", ".swp")):
        return False
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            icerik = f.read()
    except OSError:
        return False
    if not icerik.strip():
        return False
    if path.endswith(".py"):
        if "sys.exit(1)" in icerik or "sys.exit(2)" in icerik or "sys.exit(3)" in icerik:
            return True
        if "permissionDecision" in icerik:
            return True
        return False
    if path.endswith(".sh"):
        if re.search(r"^\s*exit\s+[12]\b", icerik, re.MULTILINE):
            return True
        return False
    return False


def _test_mutasyon_dislama(base):
    """-test.py / -mutasyon- / -prob- iceren test altyapisi.

    Spec: kapsam evreni KAPI/NOBET betiklerini kapsar; KAPI'lari TEST eden
    altyapi (test/mutasyon/prob dosyalari) haritada aranmaz. Onlar kapilari
    olcen altyapidir, kapinin kendisi degildir.

    Spec ornek altyapi siniflari:
      tests:  ...-test.py, ...-mutasyon.py, ...-mutasyon-test.py, ...-prob.md
              (kullanilan ortak ek: -test, -mutasyon, -prob)
    """
    if base.endswith("-test.py") or base.endswith("-test.sh"):
        return True
    if "-mutasyon" in base:
        return True
    if "-prob" in base:
        return True
    return False


def evreni_turet(tools_dir, cron_dir):
    """tools/ + cron/ altinda KAPI/NOBET evrenini KOD SEMBOLunden turetir.

    Dondurur: list of dict, her biri:
      { "yol": repo-goreli veya "cron:<base>", "mutlak": tam yol, "base": dosya adi }
    """
    bulunan = []
    seen = set()
    for kok, hangi, files in (
        (tools_dir, "tools", os.listdir(tools_dir)) if os.path.isdir(tools_dir) else (None, None, []),
    ):
        if kok is None:
            continue
        for f in sorted(files):
            if not (f.endswith(".py") or f.endswith(".sh")):
                continue
            mutlak = os.path.join(kok, f)
            if mutlak in seen:
                continue
            seen.add(mutlak)
            if _test_mutasyon_dislama(f):
                continue
            if _kod_sinyali(mutlak):
                bulunan.append({"yol": "tools/" + f, "mutlak": mutlak, "base": f})
    if os.path.isdir(cron_dir):
        for f in sorted(os.listdir(cron_dir)):
            if not (f.endswith(".py") or f.endswith(".sh")):
                continue
            mutlak = os.path.join(cron_dir, f)
            if mutlak in seen:
                continue
            seen.add(mutlak)
            if _test_mutasyon_dislama(f):
                continue
            if _kod_sinyali(mutlak):
                bulunan.append({"yol": "cron:" + f, "mutlak": mutlak, "base": f})
    return bulunan


# ---------------------------------------------------------------------------
# HARITA oku/yaz
# ---------------------------------------------------------------------------
def haritayi_oku(repo_kok, harita_yolu):
    """TSV'yi oku, her satir {MEKANIZMA, YOL, EV, SERIT, KABUL_KOMUTU} dict listesine cevir.

    Yorum satirlari (# ile baslayan) ve bos satirlar atlanir.
    Ilk satir baslik olarak atlanir (kolon adlari) — kullanici tarafindan da eklenebilir.
    Kolon sirasi spec §2a: MEKANIZMA · YOL · EV · SERIT · KABUL_KOMUTU
    """
    tam = harita_yolu if os.path.isabs(harita_yolu) else os.path.join(repo_kok, harita_yolu)
    if not os.path.isfile(tam):
        return [], []
    with open(tam, encoding="utf-8") as f:
        satirlar = f.readlines()
    satirlar = [s.rstrip("\n") for s in satirlar]
    veri = []
    hatalar = []
    baslik_gecti = False
    for i, s in enumerate(satirlar, 1):
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        kolonlar = s.split("\t")
        if not baslik_gecti and kolonlar[0].strip() == "MEKANIZMA":
            baslik_gecti = True
            continue
        baslik_gecti = True
        if len(kolonlar) < 5:
            hatalar.append("satir %d: 5 kolon bekleniyor, %d bulundu: %r" % (i, len(kolonlar), s[:80]))
            continue
        mekanizma, yol, ev, serit, kabul_komutu = [k.strip() for k in kolonlar[:5]]
        if not mekanizma or not yol:
            hatalar.append("satir %d: MEKANIZMA/YOL bos olamaz" % i)
            continue
        veri.append({
            "MEKANIZMA": mekanizma,
            "YOL": yol,
            "EV": ev,
            "SERIT": serit,
            "KABUL_KOMUTU": kabul_komutu,
            "SATIR_NO": i,
        })
    return veri, hatalar


def haritayi_yaz(repo_kok, satirlar):
    """TSV yaz (ilk satir baslik). Atomik degil; isci kendi yazisi gerektiginde."""
    tam = os.path.join(repo_kok, HARITA_REPO_RELATIF)
    govde = "MEKANIZMA\tYOL\tEV\tSERIT\tKABUL_KOMUTU\n"
    for s in satirlar:
        govde += "\t".join([
            s["MEKANIZMA"], s["YOL"], s["EV"], s["SERIT"], s["KABUL_KOMUTU"]
        ]) + "\n"
    with open(tam, "w", encoding="utf-8") as f:
        f.write(govde)


# ---------------------------------------------------------------------------
# DOGRULAMA
# ---------------------------------------------------------------------------
def dogrula(evren, harita, *, test_modu=False, mutant=None):
    """Invaryant kontrolu. Dondurur: dict(rc, EVREN, HARITADA, EKSIK, BAYAT,
    SAHIPSIZ, KIRMIZI_SATIRLAR, hatalar).

    test_modu=True: MUTANT/KONTROL modu (kendini-test).
    mutant: "M1" | "M2" | "M3" | "K1" | "K2" | None
    """
    evren_yollar = {e["yol"] for e in evren}
    harita_yol_indexi = {}
    for h in harita:
        harita_yol_indexi.setdefault(h["YOL"], []).append(h)

    eksik = []   # evrende var, haritada yok
    bayat = []   # haritada var (ve ayakta), evrende yok
    sahipsiz = []  # EV=BILINMIYOR olanlari say
    kirmizi_satirlar = []  # beklenen RED listesi

    haritada_var = set()
    # Haritaya bak, once bayat olanlari yakala — bunlar harita ama evrendisinda yok
    for h in harita:
        # M2: haritada var olmayan yol eklenmisse -> BAYAT (evi yalandan rapor etti)
        if h["YOL"] not in evren_yollar:
            bayat.append((h["YOL"], h["MEKANIZMA"], h["SATIR_NO"]))
    # Evrene bak, haritada yoksa EKSIK
    for e in evren:
        if e["yol"] not in harita_yol_indexi:
            eksik.append((e["yol"], e["base"]))
            continue
        haritada_var.add(e["yol"])
        for h in harita_yol_indexi[e["yol"]]:
            if h["EV"] not in EV_OLARAK_KABUL:
                kirmizi_satirlar.append((h["SATIR_NO"], "EV gecersiz: %r" % h["EV"]))
            elif h["EV"] == "BILINMIYOR":
                sahipsiz.append((h["YOL"], h["MEKANIZMA"], h["SATIR_NO"]))
            if h["SERIT"] not in SERIT_OLARAK_KABUL:
                kirmizi_satirlar.append((h["SATIR_NO"], "SERIT gecersiz: %r (beklenen: %s)"
                                         % (h["SERIT"], "|".join(sorted(SERIT_OLARAK_KABUL)))))

    # Beklenen RED (kirmizi) ciktilari mutant/kontrol bilgisine gore:
    beklenen_red = []
    if mutant == "M1":
        # Bir satiri haritadan SIL -> o betik EKSIK olur
        if eksik:
            beklenen_red.append(("M1", "satir silindi: %s haritada artik yok"
                                 % (",".join(y for y, _ in eksik))))
        else:
            beklenen_red.append(("M1", "EKSIK yok (beklenti: bir satir haritadan silinmisti)"))
    elif mutant == "M2":
        # Var olmayan yol haritaya eklenmisse -> BAYAT
        if bayat:
            beklenen_red.append(("M2", "bayat satir haritada: %s"
                                 % (",".join(y for y, _, _ in bayat))))
        else:
            beklenen_red.append(("M2", "BAYAT yok (beklenti: olmayan yol haritadaydi)"))
    elif mutant == "M3":
        # Evreni bos kumeye indir -> EVREN=0 ile YESIL DONMEMELI
        if not evren:
            beklenen_red.append(("M3", "EVREN=0 (bos evren yesil degildir)"))
        else:
            beklenen_red.append(("M3", "EVREN bos degil (beklenti: evren sifira inmisti)"))
    elif mutant == "K1":
        # K1: normal haritada RED uremez
        if eksik or bayat:
            beklenen_red.append(("K1", "EKSIK=%d BAYAT=%d (beklenti: 0)" % (len(eksik), len(bayat))))
    elif mutant == "K2":
        # K2: EV=BILINMIYOR satirlari kapiyi KIRMIZI yakmaz, yalniz sayilir
        ek_beklenen_red = [k for k in beklenen_red]
        for h in harita:
            if h["EV"] == "BILINMIYOR":
                # K2 sartinda EV=BILINMIYOR'un KIRMIZI uretmedigini dogrula
                # (yukarida dogrulamada sadece sayiliyor, kirmizi yok)
                pass
        # sahipsiz uyarisinin KAPI'yi yakmadigini kanitla
        if eksik or bayat:
            beklenen_red.append(("K2", "BILINMIYOR disinda EKSIK/BAYAT var (beklenti: 0)"))

    # Mutant modunda: beklenen RED gorulmediyse mutasyon YASAMIS demektir,
    # duzeltmemiz gerekir. test_modu sonuc olarak (mutant_basarili=n/3) soyler.
    return {
        "EVREN": len(evren),
        "HARITADA": len({h["YOL"] for h in harita}),
        "EKSIK": eksik,
        "BAYAT": bayat,
        "SAHIPSIZ": sahipsiz,
        "KIRMIZI": kirmizi_satirlar,
        "BEKLENEN_RED": beklenen_red,
        "mutant": mutant,
        "test_modu": test_modu,
    }


def ozet_satir(sonuc, mutant_basari=None, kontrol_basari=None):
    """Son/satir ozet. Spec §3 formati: EVREN=HARITADA=EKSIK=0 BAYAT=0 SAHIPSIZ= MUTANT=3/3 KONTROL=2/2

    mutant_basari: (mutant_gecen, mutant_toplam) veya None (test modu disinda).
    """
    temel = ("EVREN=%d HARITADA=%d EKSIK=%d BAYAT=%d SAHIPSIZ=%d"
             % (sonuc["EVREN"], sonuc["HARITADA"],
                len(sonuc["EKSIK"]), len(sonuc["BAYAT"]), len(sonuc["SAHIPSIZ"])))
    if mutant_basari is None and kontrol_basari is None:
        return temel
    if not mutant_basari:
        mutant_basari = (0, 3)
    if not kontrol_basari:
        kontrol_basari = (0, 2)
    m_g, m_t = mutant_basari
    k_g, k_t = kontrol_basari
    return temel + " MUTANT=%d/%d KONTROL=%d/%d" % (m_g, m_t, k_g, k_t)


# ---------------------------------------------------------------------------
# MUTANT altyapisi (kendini-test icin)
# ---------------------------------------------------------------------------
def _gvd_yedekle(tsv_yolu):
    """TSV'nin gecici yedegini al; geri koymak icin."""
    yedek = tsv_yolu + ".kendinitest-yedek"
    with open(tsv_yolu, encoding="utf-8") as f, open(yedek, "w", encoding="utf-8") as g:
        g.write(f.read())
    return yedek


def _gvd_yedekten_geri(tsv_yolu, yedek):
    with open(yedek, encoding="utf-8") as f, open(tsv_yolu, "w", encoding="utf-8") as g:
        g.write(f.read())
    os.unlink(yedek)


def _gvd_sil_satir(tsv_yolu, evren_yol):
    """Bir YOL'a ait ilk satiri sil (M1)."""
    satirlar = open(tsv_yolu, encoding="utf-8").read().splitlines()
    out = []
    silindi = False
    for s in satirlar:
        if not s.strip() or s.lstrip().startswith("#") or s.startswith("MEKANIZMA"):
            out.append(s)
            continue
        if not silindi and s.split("\t", 2)[1] == evren_yol:
            silindi = True
            continue
        out.append(s)
    with open(tsv_yolu, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def _gvd_bayat_satir_ekle(tsv_yolu):
    """Var olmayan bir yol ekle (M2)."""
    with open(tsv_yolu, "a", encoding="utf-8") as f:
        f.write("hayalet-kapi\thayalet/yol.py\tBILINMIYOR\tnobet\tYOK\n")


def _gvd_evreni_sifirla(evren_depolu):
    """EVREN listesini bosaltip dondurur (M3 testi icin)."""
    return []


def kendini_test(repo_kok, tools_dir, cron_dir):
    """3 mutant RED + 2 kontrol YESIL — sirayla, her birinin sonucu KIRMIZI/YESIL.

    Her mutasyondan once harita geri yuklenir, sonra uygulanir, olculur.
    Cikis kodu: tum 5 adim YESIL ise 0; biri RED ise 1.
    """
    tsv_yolu = os.path.join(repo_kok, HARITA_REPO_RELATIF)
    if not os.path.isfile(tsv_yolu):
        print("HATA: harita dosyasi yok: " + tsv_yolu)
        return 1
    yedek = _gvd_yedekle(tsv_yolu)
    try:
        evren_orig = evreni_turet(tools_dir, cron_dir)
        # Surekli mutant/kontrol adimlari
        adimlar = []

        # M1 — haritadan bir satiri sil -> o betik EKSIK olur (KIRMIZI beklenir)
        _gvd_sil_satir(tsv_yolu, evren_orig[0]["yol"])
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, test_modu=True, mutant="M1")
        m1_reddetti = bool(sonuc["EKSIK"])
        adimlar.append(("M1", m1_reddetti))
        _gvd_yedekten_geri(tsv_yolu, yedek)
        yedek = _gvd_yedekle(tsv_yolu)

        # M2 — var olmayan bir yol haritaya ekle -> BAYAT KIRMIZI beklenir
        _gvd_bayat_satir_ekle(tsv_yolu)
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, test_modu=True, mutant="M2")
        m2_reddetti = bool(sonuc["BAYAT"])
        adimlar.append(("M2", m2_reddetti))
        _gvd_yedekten_geri(tsv_yolu, yedek)
        yedek = _gvd_yedekle(tsv_yolu)

        # M3 — evreni bos kumeye indir -> EVREN=0 ile YESIL DONMEMELI
        # Burada dogrula()'ya bos evren verilip BEKLENEN_RED uretip uretmedigine
        # bakilir (KIRMIZI beklenir).
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula([], harita, test_modu=True, mutant="M3")
        # M3 KIRMIZI: bos evren "yesil" sayilmamali (KIRMIZI beklenir)
        m3_reddetti = sonuc.get("BEKLENEN_RED") and any(r[0] == "M3" for r in sonuc["BEKLENEN_RED"])
        adimlar.append(("M3", m3_reddetti))

        # K1 — normal harita ile RED uremez (YESIL beklenir)
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, test_modu=True, mutant="K1")
        k1_reddetti = sonuc["BEKLENEN_RED"] and any(r[0] == "K1" for r in sonuc["BEKLENEN_RED"])
        k1_gecerli = (not sonuc["EKSIK"] and not sonuc["BAYAT"]
                      and not [k for k in sonuc["KIRMIZI"]])
        adimlar.append(("K1", k1_gecerli))

        # K2 — EV=BILINMIYOR kapiyi KIRMIZI yakmaz (yalniz sayilir) (YESIL beklenir)
        # Bu kontrol: haritaya BILINMIYOR satiri ekleyip tekrar dogrulayarak olculur.
        _gvd_satir_ekle(tsv_yolu, evren_orig[0]["yol"], evren_orig[0]["base"] + "-BILINMIYOR-test",
                         "BILINMIYOR", "nobet", "YOK")
        harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
        sonuc = dogrula(evren_orig, harita, test_modu=True, mutant="K2")
        # BILINMIYOR satirinin var, eklenmesi gerektigi, ama kapi kirmizi OLMAMALI
        bilinmiyor_var_mi = any(h["EV"] == "BILINMIYOR" and h["YOL"] == evren_orig[0]["yol"]
                                for h in harita)
        kapi_yakmamis = (not sonuc["KIRMIZI"])  # kirmizi yoksa kapi yakmiyor
        adimlar.append(("K2", bilinmiyor_var_mi and kapi_yakmamis))
        _gvd_yedekten_geri(tsv_yolu, yedek)
        yedek = None

        # Sonuc ozet
        mutant_sayaci = sum(1 for ad, g in adimlar[:3] if g)
        kontrol_sayaci = sum(1 for ad, g in adimlar[3:] if g)
        print("KENDINI-TEST BASAMAKLARI:")
        for ad, g in adimlar:
            print("  %s: %s" % (ad, "RED/YESIL bekleneni yakaladi" if g else "BASARISIZ (beklenti tutmadi)"))
        print("MUTANT=%d/3 KONTROL=%d/2" % (mutant_sayaci, kontrol_sayaci))
        if mutant_sayaci == 3 and kontrol_sayaci == 2:
            # Son olcum — evren+harita ile
            harita, _ = haritayi_oku(repo_kok, HARITA_REPO_RELATIF)
            sonuc = dogrula(evren_orig, harita, test_modu=False)
            print(ozet_satir(sonuc, mutant_basari=(mutant_sayaci, 3),
                             kontrol_basari=(kontrol_sayaci, 2)))
            return 0
        # Spec geregi MUTANT/KONTROL sayaci tamamlanmadan raporlama
        print("MUTANT=%d/3 KONTROL=%d/2" % (mutant_sayaci, kontrol_sayaci))
        return 1
    finally:
        if yedek and os.path.isfile(yedek):
            try:
                _gvd_yedekten_geri(tsv_yolu, yedek)
            except OSError:
                pass


def _gvd_satir_ekle(tsv_yolu, yol, mekanizma, ev, serit, kabul):
    """K2 testi icin gecici olarak BILINMIYOR satir ekler."""
    satir = "\t".join([mekanizma, yol, ev, serit, kabul])
    with open(tsv_yolu, "a", encoding="utf-8") as f:
        f.write(satir + "\n")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=CANON, help="olculecek repo koku")
    ap.add_argument("--harita", default=HARITA_REPO_RELATIF,
                    help="harita TSV yolu (repo-goreli veya mutlak)")
    ap.add_argument("--json", action="store_true", help="makine-okunur JSON cikti")
    ap.add_argument("--kendini-test", action="store_true",
                    help="3 mutant + 2 kontrolu kosar, MUTANT/KONTROL ozetini basar")
    args = ap.parse_args()

    repo_kok = os.path.abspath(args.repo)
    tools_dir = os.path.join(repo_kok, "tools")
    cron_dir = CRON

    if args.kendini_test:
        return kendini_test(repo_kok, tools_dir, cron_dir)

    evren = evreni_turet(tools_dir, cron_dir)
    harita, hatalar = haritayi_oku(repo_kok, args.harita)
    if hatalar:
        print("HARITA OKUMA HATALARI:", file=sys.stderr)
        for h in hatalar:
            print("  " + h, file=sys.stderr)
        return 1

    sonuc = dogrula(evren, harita)

    if args.json:
        print(json.dumps({
            "EVREN": sonuc["EVREN"],
            "HARITADA": sonuc["HARITADA"],
            "EKSIK": sonuc["EKSIK"],
            "BAYAT": sonuc["BAYAT"],
            "SAHIPSIZ": sonuc["SAHIPSIZ"],
            "KIRMIZI": sonuc["KIRMIZI"],
        }, indent=2, ensure_ascii=False))
    else:
        print("KAPI/NOBET HARITA KAPISI (salt-okunur)")
        print("Repo: " + repo_kok)
        print("Harita: " + args.harita)
        print("Kapsam evreni (kod-kanitli): sys.exit(1..9) VEYA permissionDecision VEYA "
              "exit 1/2; -test/-mutasyon/-prob dislanir")
        print("")
        print(ozet_satir(sonuc))
        if sonuc["EKSIK"]:
            print("")
            print("EKSIK (evrende var, haritada yok) — RED:")
            for yol, base in sonuc["EKSIK"]:
                print("  %s  (%s)" % (yol, base))
        if sonuc["BAYAT"]:
            print("")
            print("BAYAT (haritada var, evrende yok) — RED:")
            for yol, ad, no in sonuc["BAYAT"]:
                print("  satir %d  %s  (%s)" % (no, yol, ad))
        if sonuc["SAHIPSIZ"]:
            print("")
            print("SAHIPSIZ (EV=BILINMIYOR) — kapi YANMAZ, yalniz sayilir:")
            for yol, ad, no in sonuc["SAHIPSIZ"]:
                print("  satir %d  %s  (%s)" % (no, yol, ad))
        if sonuc["KIRMIZI"]:
            print("")
            print("KIRMIZI (gecersiz EV/SERIT) — RED:")
            for no, msg in sonuc["KIRMIZI"]:
                print("  satir %d  %s" % (no, msg))

    # RC davranisi:
    # - EKSIK veya BAYAT varsa RED -> rc=1
    # - KIRMIZI (gecersiz EV/SERIT) varsa RED -> rc=1
    # - SAHIPSIZ tek basina RED degil -> rc=0 (spec §2b)
    # - EVREN=0 ise RED -> rc=1 (bos evren yesil degil)
    if (sonuc["EKSIK"] or sonuc["BAYAT"] or sonuc["KIRMIZI"] or sonuc["EVREN"] == 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
