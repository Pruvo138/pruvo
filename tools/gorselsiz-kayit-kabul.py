#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gorselsiz-kayit-kabul.py — K313 SINIF KOLU kabul bataryasi.

SORU: `gorseller[0]` KART KAPAGI oldugu halde, gorselsiz bir kayit tasiyan bir PARTI
`tools/denetim-kapisi.py`'den GECIYOR mu?

26 Agu'da tekil kol kapandi (gorselsiz kayit 9->0, SILME YOK — kayitlar ONARILDI). Ama
bir daha girmesini engelleyen MEKANIZMA konmadi. Bu batarya once TABANI olcer (kapi
bugun bunu goruyor mu), sonra onarimin gercekten o kolu ekledigini MUTANT ile kanitlar.

KOLLAR
------
  TABAN-A  CANLI katalogda gorselsiz kayit sayimi (kapidan BAGIMSIZ; ham JSON okumasi).
  TABAN-B  FIKSTUR partisi denetim kapisina beslenir (SENTETIK depo; canli katalog
           OKUNMAZ, DEGISMEZ) -> rc + hangi id'lerin ADIYLA dustugu.
  TABAN-C  CANLI `--tum-katalog --envanter` rc + TOPLAM VURUS + TOPLAM AYRIK KAYIT
           (K5 karsilastirma tabani) + parti kipinde ham rc.
  K1..K6   Kabul (bkz. --help ciktisi ve rapor basliklari).

🔴 CANLI VERI: yalnizca OKUNUR. Bu betik `urunler.json`'a ASLA yazmaz, urun SILMEZ,
`--uygula` CAGIRMAZ. Mutasyon YALNIZ sentetik depodaki KOPYAYA uygulanir; izlenen
`tools/denetim-kapisi.py` bayt-esit kalir (koşum sonunda sha256 ile DOGRULANIR).

Cikti: stdout + `--cikti` dosyasi (varsayilan `.thing-cache/…` — GIT DISI, `.gitignore`'da;
ic kosum raporu izlenen agaca birakilmaz).

Kullanim:
    python3 tools/gorselsiz-kayit-kabul.py --taban     # ADIM 0B (onarim ONCESI de kosar)
    python3 tools/gorselsiz-kayit-kabul.py             # tam batarya (K1..K6)

Cikis kodlari: 0 = YESIL · 1 = KIRMIZI · 3 = OLCULEMEDI (fail-closed; sessiz yesil YOK).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "denetim-kapisi.py")
URUNLER = os.path.join(ROOT, "urunler.json")
INDEX = os.path.join(ROOT, "index.html")
CIKTI_VARSAYILAN = os.path.join(ROOT, ".thing-cache", "gorselsiz-kayit-kabul.txt")

if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from git_ortami import sentetik_git                                    # noqa: E402

_SATIRLAR = []

# --- K5 TABANI: ONARIM ONCESI OLCULDU (27 Agu, `--taban` kosumu). Elle YAZILMADI —
# asagidaki sayilar o koşumun ham ciktisindan BIREBIR alindi; taban gate sha256'si de
# birlikte civilendi ki "hangi surumun tabani" sorusu sonradan tartisilmasin
# ([[olcut-civilenirken-taban-olculmeli]] · [[kapanis-olcutu-onceden-civilenir]]).
TABAN_KAPI_SHA = "4c9a6f67f6af8dbb4e72af9eab5db4eebfe794e0a0e8c5464b6bc8f8cead513e"
TABAN_RC_PARTI = 0
TABAN_RC_ENVANTER = 0
TABAN_AYRIK = 274                      # TOPLAM AYRIK KAYIT (--tum-katalog --envanter)
TABAN_VURUS = 320                      # TOPLAM VURUS
TABAN_CANLI_CIPLAK_GORSELSIZ = 0       # canli katalogda beyansiz gorselsiz kayit


def _sayi(satir):
    """'  TOPLAM VURUS | 320' -> 320 (okunamazsa None; sessiz sifir YOK)."""
    parca = str(satir).rsplit("|", 1)
    try:
        return int(parca[-1].strip())
    except (ValueError, IndexError):
        return None


def yaz(s=""):
    print(s)
    _SATIRLAR.append(s)


# --------------------------------------------------------------------------- fiksturler
_YOK = object()          # `gorseller` ALANI HIC YOK


def _u(uid, gorseller=None, **kw):
    u = {"id": uid, "kategori": "Otomobil", "marka": ["Audi"],
         "baslik": "Audi A4 Uyumlu Braket %s" % uid,
         "aciklama": ("Araca birebir oturan dayanikli baglanti parcasi. "
                      "Yaklasik dis olculer: 40 × 30 × 12 mm."),
         "fiyat": "850 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}
    if gorseller is _YOK:
        del u["gorseller"]
    elif gorseller is not None:
        u["gorseller"] = gorseller
    u.update(kw)
    return u


# PARTI-KIRMIZI: dordu de gorselsiz ve HICBIRI dar istisnayi karsilamiyor -> RED beklenir.
def parti_kirmizi():
    return [
        _u("k1-bos-liste", gorseller=[]),
        _u("k1-alan-yok", gorseller=_YOK),
        _u("k1-bayraksiz-fiziksel", gorseller=[], tur="fiziksel"),
        _u("k1-bayrakli-baski", gorseller=[], gorselsiz=True),   # bayrak var, tur YOK
    ]


# PARTI-YESIL (POZITIF KONTROL): gorselleri TAM -> kapi bu partiye DOKUNMAMALI.
def parti_yesil():
    return [_u("k2-tam-%d" % i) for i in range(3)]


# PARTI-ISTISNA: acik beyan + hazir ticari mal -> DAR ISTISNA gecerli, RED BEKLENMEZ.
def parti_istisna():
    return [_u("k2b-bayrakli-fiziksel", gorseller=[], tur="fiziksel", gorselsiz=True)]


TABAN_URUNLER = [_u("taban-%d" % i) for i in range(3)]

_BEKLENEN_KIRMIZI = {"k1-bos-liste", "k1-alan-yok",
                     "k1-bayraksiz-fiziksel", "k1-bayrakli-baski"}


# --------------------------------------------------------------------------- sentetik depo
def _kaynak_kaydi(urunler):
    """Her fikstur icin SATILABILIR lisans kaydi — lisans kapisi (fail-closed) bu
    bataryanin olctugu eksen DEGIL; gurultuyu kaynaginda kes."""
    return {u["id"]: {"kaynak": "printables",
                      "link": "https://www.printables.com/model/1-%s" % u["id"],
                      "lisans": "CC BY"} for u in urunler}


def depo_kur(tmp, mutasyon=None):
    """Sentetik depo: tools/ + index.html kopyalanir, taban COMMIT edilir.

    mutasyon = (eski, yeni) -> YALNIZ depodaki denetim-kapisi.py KOPYASINA uygulanir.
    Capa tam 1 kez eslesmezse FAIL-LOUD (SystemExit) — sessiz atlama YOK
    ([[capa-cokmesi-arkasindaki-capalari-gizler]])."""
    depo = os.path.join(tmp, "depo")
    os.makedirs(depo)
    shutil.copytree(TOOLS, os.path.join(depo, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(INDEX, os.path.join(depo, "index.html"))
    if mutasyon is not None:
        eski, yeni = mutasyon
        hedef = os.path.join(depo, "tools", "denetim-kapisi.py")
        with open(hedef, encoding="utf-8") as f:
            src = f.read()
        if src.count(eski) != 1:
            raise SystemExit("MUTASYON CAPASI KAYIP/COKLU (%d adet): %r"
                             % (src.count(eski), eski))
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(src.replace(eski, yeni, 1))

    def _yaz(liste):
        with open(os.path.join(depo, "urunler.json"), "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False)

    _yaz(TABAN_URUNLER)
    with open(os.path.join(depo, ".urun-kaynaklari.json"), "w", encoding="utf-8") as f:
        json.dump(_kaynak_kaydi(TABAN_URUNLER), f, ensure_ascii=False)
    sentetik_git(depo, "init", "-q", capture_output=True)
    sentetik_git(depo, "add", "-A", capture_output=True)
    sentetik_git(depo, "commit", "-q", "-m", "taban", capture_output=True)
    return depo


def parti_kos(depo, parti):
    """Partiyi COMMIT ETMEDEN calisma agacina koy, kapiyi kostur -> (rc, cikti, rapor)."""
    tum = TABAN_URUNLER + parti
    with open(os.path.join(depo, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(tum, f, ensure_ascii=False)
    with open(os.path.join(depo, ".urun-kaynaklari.json"), "w", encoding="utf-8") as f:
        json.dump(_kaynak_kaydi(tum), f, ensure_ascii=False)
    rapor_yolu = os.path.join(depo, "rapor.json")
    p = subprocess.run([sys.executable, os.path.join(depo, "tools", "denetim-kapisi.py"),
                        "--rapor", rapor_yolu],
                       capture_output=True, text=True, errors="replace",
                       cwd=depo, timeout=900)
    try:
        with open(rapor_yolu, encoding="utf-8") as f:
            rapor = json.load(f)
    except (OSError, ValueError):
        rapor = None
    return p.returncode, (p.stdout or "") + (p.stderr or ""), rapor


def gorselsiz_vuruslari(rapor):
    """Rapordaki `gorselsiz` kapisi ihlallerinin id kumesi (hedef-kol atfi icin ADIYLA)."""
    if not rapor:
        return None
    return {it["id"] for it in (rapor.get("ihlal") or []) if it.get("kapi") == "gorselsiz"}


# --------------------------------------------------------------------------- TABAN-A
def taban_a():
    with open(URUNLER, encoding="utf-8") as f:
        kat = json.load(f)
    toplam = len(kat)
    yok, bicimsiz, muaf, ciplak = [], [], [], []
    for u in kat:
        if not isinstance(u, dict):
            continue
        uid = u.get("id")
        if "gorseller" not in u:
            yok.append(uid)
        else:
            g = u.get("gorseller")
            if isinstance(g, list):
                if not g:
                    yok.append(uid)
            else:
                bicimsiz.append(uid)
                continue
            if g:
                continue
        # buraya yalniz "gorsel HIC YOK" gelir
        if u.get("gorselsiz") is True and u.get("tur") == "fiziksel":
            muaf.append(uid)
        else:
            ciplak.append(uid)
    yaz("TABAN-A CANLI KATALOG (kapidan bagimsiz, ham JSON okumasi)")
    yaz("  TOPLAM_KAYIT              = %d" % toplam)
    yaz("  GORSEL_HIC_YOK            = %d" % len(yok))
    yaz("  ..bunun BAYRAKLI_MUAF'i   = %d  (gorselsiz:true + tur:fiziksel — MESRU istisna)"
        % len(muaf))
    yaz("  ..bunun CIPLAK_GORSELSIZ'i= %d  (beyansiz — ARIZA sinifi)" % len(ciplak))
    yaz("  GORSELLER_BICIMSIZ        = %d  (liste degil: str/dict/None)" % len(bicimsiz))
    for ad, lst in (("CIPLAK_GORSELSIZ", ciplak), ("BAYRAKLI_MUAF", muaf),
                    ("BICIMSIZ", bicimsiz)):
        if lst:
            yaz("  %s id'leri (ilk 20): %s" % (ad, ", ".join(str(x) for x in lst[:20])))
    yaz()
    return {"toplam": toplam, "ciplak": len(ciplak), "muaf": len(muaf),
            "bicimsiz": len(bicimsiz)}


# --------------------------------------------------------------------------- TABAN-B
def taban_b(tmp):
    depo = depo_kur(os.path.join(tmp, "tabanb"))
    rc_k, cik_k, rap_k = parti_kos(depo, parti_kirmizi())
    rc_y, cik_y, rap_y = parti_kos(depo, parti_yesil())
    rc_i, cik_i, rap_i = parti_kos(depo, parti_istisna())
    v_k = gorselsiz_vuruslari(rap_k)
    yaz("TABAN-B FIKSTUR -> DENETIM KAPISI (sentetik depo; canli katalog OKUNMADI)")
    yaz("  PARTI-KIRMIZI (4 gorselsiz kayit)  rc=%d  IHLAL=%d  gorselsiz_vurus=%s"
        % (rc_k, len(((rap_k or {}).get("ihlal")) or []),
           "YOK (kapi bu kolu OLCMUYOR)" if not v_k else sorted(v_k)))
    yaz("  PARTI-YESIL   (3 gorselli kayit)   rc=%d  IHLAL=%d"
        % (rc_y, len(((rap_y or {}).get("ihlal")) or [])))
    yaz("  PARTI-ISTISNA (1 bayrakli fizik.)  rc=%d  IHLAL=%d"
        % (rc_i, len(((rap_i or {}).get("ihlal")) or [])))
    yaz("  --- PARTI-KIRMIZI ham ciktisi (ilk 1200 krk) ---")
    for satir in cik_k[:1200].splitlines():
        yaz("  | " + satir)
    yaz()
    return {"rc_kirmizi": rc_k, "rc_yesil": rc_y, "rc_istisna": rc_i,
            "vurus": sorted(v_k) if v_k else []}


# --------------------------------------------------------------------------- TABAN-C
def _canli_kos(ekler, sure_tavani=3600):
    t0 = time.time()
    p = subprocess.run([sys.executable, KAPI] + ekler, capture_output=True,
                       text=True, errors="replace", cwd=ROOT, timeout=sure_tavani)
    return p.returncode, (p.stdout or "") + (p.stderr or ""), time.time() - t0


def _satir_bul(cikti, anahtar):
    for s in cikti.splitlines():
        if anahtar in s:
            return s.strip()
    return "(satir YOK: %s)" % anahtar


ANA_KAPI = "/Users/okan/dev/pruvo/tools/denetim-kapisi.py"


def _kendini_test(betik):
    """`--kendini-test` (CI bloklayici kolu, nobet.yml) — sentetik depo, canli veri YOK."""
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, betik, "--kendini-test"], capture_output=True,
                           text=True, errors="replace",
                           cwd=os.path.dirname(os.path.dirname(betik)), timeout=1800)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "KOSTURULAMADI: %s" % e, time.time() - t0
    return p.returncode, (p.stdout or "") + (p.stderr or ""), time.time() - t0


def taban_c():
    yaz("TABAN-C CANLI KAPI KOSUMU (salt okuma; --uygula YOK)")
    rc_p, cik_p, sn_p = _canli_kos([])
    yaz("  parti kipi (calisma agaci - HEAD)   rc=%d  (%.1f sn)" % (rc_p, sn_p))
    yaz("    | " + _satir_bul(cik_p, "=== DENETIM KAPISI ==="))
    yaz("    | " + _satir_bul(cik_p, "IHLAL        :"))
    rc_e, cik_e, sn_e = _canli_kos(["--tum-katalog", "--envanter"])
    yaz("  --tum-katalog --envanter            rc=%d  (%.1f sn)" % (rc_e, sn_e))
    ayrik = _satir_bul(cik_e, "TOPLAM AYRIK KAYIT")
    vurus = _satir_bul(cik_e, "TOPLAM VURUS")
    yaz("    | " + ayrik)
    yaz("    | " + vurus)
    for s in cik_e.splitlines():
        s = s.strip()
        if s.startswith("gorselsiz ") or " | " in s and s.split(" | ")[0].strip() == "gorselsiz":
            yaz("    | " + s)
    # --kendini-test: CI'da BLOKLAYICI kol (nobet.yml). Onarim bunu kotulestirmemeli.
    rc_kt, cik_kt, sn_kt = _kendini_test(KAPI)
    yaz("  --kendini-test (BU agac, sha %s)    rc=%s  (%.1f sn)"
        % (_sha(KAPI)[:12], rc_kt, sn_kt))
    yaz("    | " + _satir_bul(cik_kt, "DENETIM KAPISI — KENDINI TEST"))
    for s in cik_kt.splitlines():
        s = s.strip()
        if s.startswith("SONUC") or s.startswith("TOPLAM") or "gecti" in s.lower() \
                or "dusen" in s.lower() or s.startswith("✘"):
            yaz("    | " + s[:200])
    rc_kt_ana, cik_kt_ana, sn_kt_ana = (None, "", 0.0)
    if os.path.abspath(ANA_KAPI) != os.path.abspath(KAPI) and os.path.exists(ANA_KAPI):
        rc_kt_ana, cik_kt_ana, sn_kt_ana = _kendini_test(ANA_KAPI)
        yaz("  --kendini-test (ANA checkout REFERANS, sha %s) rc=%s  (%.1f sn)"
            % (_sha(ANA_KAPI)[:12], rc_kt_ana, sn_kt_ana))
        for s in cik_kt_ana.splitlines():
            s = s.strip()
            if s.startswith("SONUC") or s.startswith("TOPLAM") or s.startswith("✘"):
                yaz("    | " + s[:200])
    yaz()
    return {"rc_parti": rc_p, "rc_envanter": rc_e,
            "toplam_vurus": vurus, "toplam_ayrik": ayrik,
            "rc_kendini_test": rc_kt, "rc_kendini_test_ana": rc_kt_ana}


# --------------------------------------------------------------------------- K3 mutantlar
M1 = ("M1 gorsel kolu OLDURULUR (kural cagrisi bosaltilir)",
      ("    bulgular = _gorselsiz_bulgulari(urun)\n",
       "    bulgular = []                                  # MUTANT-M1\n"))
M2 = ("M2 DAR ISTISNA kolu OLDURULUR (beyanli fiziksel de kirmiziya duser)",
      ("    if not bulgular:\n        return None, \"\"                # dar istisna islendi",
       "    if False:\n        return None, \"\"                # MUTANT-M2"))


def k3_mutant(tmp, ad_mut, indeks):
    ad, mut = ad_mut
    depo = depo_kur(os.path.join(tmp, "mut%d" % indeks), mutasyon=mut)
    rc_k, _, rap_k = parti_kos(depo, parti_kirmizi())
    rc_y, _, rap_y = parti_kos(depo, parti_yesil())
    rc_i, _, rap_i = parti_kos(depo, parti_istisna())
    return {"ad": ad, "rc_kirmizi": rc_k, "rc_yesil": rc_y, "rc_istisna": rc_i,
            "vurus_kirmizi": sorted(gorselsiz_vuruslari(rap_k) or []),
            "vurus_istisna": sorted(gorselsiz_vuruslari(rap_i) or [])}


# --------------------------------------------------------------------------- K4 kapsam
def k4_kapsam():
    """Yeni kolun BUGUNKU CANLI katalogda kac kaydi kirmiziya dusurdugu — kapinin
    KENDI fonksiyonu cagrilir (kopya kural YOK)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("dk_olculen", KAPI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "kapi_gorselsiz"):
        return {"var": False, "sayi": None, "idler": []}
    with open(URUNLER, encoding="utf-8") as f:
        kat = json.load(f)
    dusen = []
    for u in kat:
        kapi, _g = mod.kapi_gorselsiz(u)
        if kapi:
            dusen.append(u.get("id"))
    return {"var": True, "sayi": len(dusen), "idler": dusen[:50]}


# --------------------------------------------------------------------------- main
def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description="K313 SINIF kolu kabul bataryasi")
    ap.add_argument("--taban", action="store_true",
                    help="ADIM 0B: yalniz TABAN-A/B/C (onarim ONCESI de kosar)")
    ap.add_argument("--cikti", default=CIKTI_VARSAYILAN, help="ham cikti dosyasi (GIT DISI)")
    args = ap.parse_args()

    kapi_sha_once = _sha(KAPI)
    yaz("=" * 78)
    yaz("K313 SINIF KOLU — GORSELSIZ KAYIT KABUL BATARYASI")
    yaz("  ROOT             : %s" % ROOT)
    yaz("  denetim-kapisi   : sha256 %s" % kapi_sha_once)
    yaz("  kip              : %s" % ("TABAN (ADIM 0B)" if args.taban else "TAM BATARYA"))
    yaz("=" * 78)
    yaz()

    hatalar = []
    a = taban_a()
    tmp = tempfile.mkdtemp(prefix="k313-gorselsiz-")
    try:
        b = taban_b(tmp)
        c = taban_c()

        if args.taban:
            yaz("TABAN HUKMU")
            olcuyor = bool(b["vurus"]) and b["rc_kirmizi"] != 0
            yaz("  Kapi gorselsiz kaydi ADIYLA olcuyor mu? -> %s"
                % ("EVET (kalem CURUR)" if olcuyor else "HAYIR (kalem AYAKTA)"))
            yaz("  PARTI-KIRMIZI rc = %d  (RED bekleniyorsa rc != 0)" % b["rc_kirmizi"])
            yaz("  CANLI ciplak gorselsiz kayit = %d" % a["ciplak"])
        else:
            # ---------------- K1
            yaz("K1 GORSELSIZ FIKSTUR PARTISI -> RED")
            k1_ok = (b["rc_kirmizi"] != 0 and set(b["vurus"]) == _BEKLENEN_KIRMIZI)
            yaz("  rc=%d (!=0 bekleniyor) · dusen kayitlar ADIYLA: %s"
                % (b["rc_kirmizi"], b["vurus"] or "YOK"))
            yaz("  beklenen kume: %s" % sorted(_BEKLENEN_KIRMIZI))
            yaz("  K1 = %s" % ("GECTI" if k1_ok else "DUSTU"))
            if not k1_ok:
                hatalar.append("K1")
            yaz()

            # ---------------- K2
            yaz("K2 POZITIF KONTROL — gorselleri TAM parti HALA GECER")
            k2_ok = (b["rc_yesil"] == 0)
            k2b_ok = (b["rc_istisna"] == 0)
            yaz("  PARTI-YESIL rc=%d (0 bekleniyor)   -> %s"
                % (b["rc_yesil"], "GECTI" if k2_ok else "DUSTU"))
            yaz("  PARTI-ISTISNA rc=%d (0 bekleniyor) -> %s  (dar istisna: beyan + tur=fiziksel)"
                % (b["rc_istisna"], "GECTI" if k2b_ok else "DUSTU"))
            yaz("  K2 = %s" % ("GECTI" if (k2_ok and k2b_ok) else "DUSTU"))
            if not (k2_ok and k2b_ok):
                hatalar.append("K2")
            yaz()

            # ---------------- K3
            yaz("K3 MUTANT — hedef-kol atfi (K182)")
            m1 = k3_mutant(tmp, M1, 1)
            m2 = k3_mutant(tmp, M2, 2)
            yaz("  %s" % m1["ad"])
            yaz("    PARTI-KIRMIZI rc=%d vurus=%s  (0 / BOS bekleniyor: fikstur YESIL'e doner)"
                % (m1["rc_kirmizi"], m1["vurus_kirmizi"] or "YOK"))
            yaz("    KONTROL PARTI-YESIL rc=%d (0, DEGISMEMELI)" % m1["rc_yesil"])
            m1_ok = (m1["rc_kirmizi"] == 0 and not m1["vurus_kirmizi"] and m1["rc_yesil"] == 0)
            yaz("    M1 = %s" % ("OLDU (kol GERCEKTEN olculuyor)" if m1_ok else "HAYATTA"))
            yaz("  %s" % m2["ad"])
            yaz("    PARTI-ISTISNA rc=%d vurus=%s  (!=0 bekleniyor: istisna kolu olculuyor)"
                % (m2["rc_istisna"], m2["vurus_istisna"] or "YOK"))
            yaz("    KONTROL PARTI-YESIL rc=%d (0, DEGISMEMELI — kapi 'her partiye kirmizi' "
                "alarmina cevrilmedi)" % m2["rc_yesil"])
            m2_ok = (m2["rc_istisna"] != 0 and m2["rc_yesil"] == 0)
            yaz("    M2 = %s" % ("OLDU" if m2_ok else "HAYATTA"))
            yaz("  K3 = %s" % ("GECTI" if (m1_ok and m2_ok) else "DUSTU"))
            if not (m1_ok and m2_ok):
                hatalar.append("K3")
            yaz()

            # ---------------- K4
            yaz("K4 KAPSAM — yeni kol BUGUNKU CANLI katalogda kac kaydi dusuruyor?")
            k4 = k4_kapsam()
            if not k4["var"]:
                yaz("  OLCULEMEDI: denetim-kapisi.py'de `kapi_gorselsiz` YOK.")
                hatalar.append("K4")
            else:
                yaz("  DUSEN_CANLI_KAYIT = %d   (beklenen 0 — tekil kol 26 Agu'da 9->0 kapandi)"
                    % k4["sayi"])
                if k4["idler"]:
                    yaz("  id'ler (ilk 50): %s" % ", ".join(str(x) for x in k4["idler"]))
                yaz("  K4 = %s" % ("GECTI" if k4["sayi"] == 0
                                   else "MIMAR KAPISI — MERGE ETME, canli katalogu kirmiziya dusuruyor"))
                if k4["sayi"] != 0:
                    hatalar.append("K4")
            yaz()

            # ---------------- K5
            yaz("K5 TABAN KOTULESMEDI — oncesi/sonrasi yan yana")
            yaz("  TABAN (27 Agu, --taban kosumu; gate sha %s):" % TABAN_KAPI_SHA[:12])
            yaz("    ONCE parti rc=%d · envanter rc=%d · TOPLAM AYRIK KAYIT=%d · TOPLAM VURUS=%d"
                % (TABAN_RC_PARTI, TABAN_RC_ENVANTER, TABAN_AYRIK, TABAN_VURUS))
            v_son, a_son = _sayi(c["toplam_vurus"]), _sayi(c["toplam_ayrik"])
            yaz("    SONRA parti rc=%d · envanter rc=%d · TOPLAM AYRIK KAYIT=%s · TOPLAM VURUS=%s"
                % (c["rc_parti"], c["rc_envanter"], a_son, v_son))
            yaz("  --kendini-test (CI bloklayici kolu): ONCE(ANA checkout)=%s · SONRA(bu agac)=%s"
                % (c["rc_kendini_test_ana"], c["rc_kendini_test"]))
            k5_ok = (c["rc_parti"] == TABAN_RC_PARTI
                     and c["rc_envanter"] == TABAN_RC_ENVANTER
                     and v_son == TABAN_VURUS and a_son == TABAN_AYRIK
                     and c["rc_kendini_test"] == 0
                     and (c["rc_kendini_test_ana"] is None
                          or c["rc_kendini_test"] == c["rc_kendini_test_ana"]))
            yaz("  K5 = %s" % ("GECTI" if k5_ok else "DUSTU"))
            if not k5_ok:
                hatalar.append("K5")
            yaz()

            # ---------------- K6
            yaz("K6 IKI ARDISIK KOSUM BIREBIR")
            b2 = taban_b(os.path.join(tmp, "tur2"))
            k4b = k4_kapsam()
            k6_ok = (b2["rc_kirmizi"] == b["rc_kirmizi"] and b2["vurus"] == b["vurus"]
                     and b2["rc_yesil"] == b["rc_yesil"] and b2["rc_istisna"] == b["rc_istisna"]
                     and k4b["sayi"] == k4["sayi"])
            yaz("  tur1: K1 rc=%d vurus=%s · K4 dusen=%s"
                % (b["rc_kirmizi"], b["vurus"], k4["sayi"]))
            yaz("  tur2: K1 rc=%d vurus=%s · K4 dusen=%s"
                % (b2["rc_kirmizi"], b2["vurus"], k4b["sayi"]))
            yaz("  K6 = %s" % ("GECTI" if k6_ok else "DUSTU"))
            if not k6_ok:
                hatalar.append("K6")
            yaz()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    kapi_sha_sonra = _sha(KAPI)
    yaz("IZLENEN DOSYA BUTUNLUGU")
    yaz("  denetim-kapisi.py sha256 once : %s" % kapi_sha_once)
    yaz("  denetim-kapisi.py sha256 sonra: %s" % kapi_sha_sonra)
    yaz("  BAYT-ESIT = %s (mutasyon YALNIZ sentetik kopyada)"
        % ("EVET" if kapi_sha_once == kapi_sha_sonra else "HAYIR — 🔴 MUTASYON SIZDI"))
    if kapi_sha_once != kapi_sha_sonra:
        hatalar.append("BUTUNLUK")
    yaz()
    yaz("=" * 78)
    if args.taban:
        yaz("TABAN KOSUMU BITTI (hukum yok — olcum).")
        rc = 0
    elif hatalar:
        yaz("KIRMIZI — dusen: %s" % ", ".join(hatalar))
        rc = 1
    else:
        yaz("YESIL — K1..K6 olculdu ve gecti.")
        rc = 0
    yaz("=" * 78)

    try:
        os.makedirs(os.path.dirname(args.cikti), exist_ok=True)
        with open(args.cikti, "w", encoding="utf-8") as f:
            f.write("\n".join(_SATIRLAR) + "\n")
        print("ham cikti -> %s" % args.cikti)
    except OSError as e:
        print("UYARI: cikti yazilamadi: %s" % e, file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
