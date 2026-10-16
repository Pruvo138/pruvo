#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/rum-vekil-olc.py (CF RUM gunluk sayim -> D1'e yazar).

KABUL SORUSU: "bu satiri silsem hangi iddia kirmizi yanar?"
Cevap her vaka icin ADIYLA yazildi. Test IKI kola ayrilir:

  A) VAKALAR — araci DEGISTIRMEDEN, fikstur uzerinde davranis olcer.
     Asil iddia: ayni gun ikinci kosumda CIFT SAYIM YOK; token sizmaz;
     cikti rakam tasimaz; sinif toplamlari birebir.
  B) MUTANTLAR — araci IZOLE KOPYADA bozar, KIRMIZI yanmasini bekler.
     Kopya `tempfile.mkdtemp` altinda; GERCEK EV YOLUNA DOKUNULMAZ, silinen yalnizca
     testin KENDI urettigi gecici dizindir.

Kosum (borusuz):  python3 tools/rum-vekil-test.py
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(ROOT, "tools", "rum-vekil-olc.py")

# V1 fikstur — gercek CF RUM yanit bicimi (tek satir kaynagi: GraphQL adaptoru).
# Toplamlar spec'teki KANIT ile birebir:
#   facebook 92+62+28+7+1 = 190, instagram 62, google 31+27+6+4 = 68,
#   bos/dogrudan 24, iyzipay/odeme 2; bing/chatg/ic/diger = 0.
V1_FIKSTUR = {
    "data": {
        "viewer": {
            "accounts": [
                {
                    "rumPageloadEventsAdaptiveGroups": [
                        {"count": 92,    "dimensions": {"refererHost": "facebook.com"}},
                        {"count": 62,    "dimensions": {"refererHost": "l.facebook.com"}},
                        {"count": 28,    "dimensions": {"refererHost": "m.facebook.com"}},
                        {"count": 7,     "dimensions": {"refererHost": "lm.facebook.com"}},
                        {"count": 1,     "dimensions": {"refererHost": "LM.FACEBOOK.COM"}},  # buyuk harf
                        {"count": 62,    "dimensions": {"refererHost": "instagram.com"}},
                        {"count": 31,    "dimensions": {"refererHost": "www.google.com.tr"}},
                        {"count": 27,    "dimensions": {"refererHost": "google.com"}},
                        {"count": 6,     "dimensions": {"refererHost": "google.com.tr"}},
                        {"count": 4,     "dimensions": {"refererHost": "com.google.android.googlequicksearchbox"}},
                        {"count": 24,    "dimensions": {"refererHost": ""}},  # dogrudan
                        {"count": 2,     "dimensions": {"refererHost": "api.iyzipay.com"}},
                    ]
                }
            ]
        }
    }
}

# V1 beklenen sinif toplamlari (gun=2026-10-16).
V1_BEKLENEN = {
    "facebook": 190, "instagram": 62, "google": 68, "bing": 0,
    "chatgpt": 0, "ic": 0, "dogrudan": 24, "odeme": 2, "diger": 0,
}

GUN = "2026-10-16"
TEST_TOKEN = "TESTTOKEN123"


def fikstur_yaz(icerik):
    fd, yol = tempfile.mkstemp(prefix="rum-fikstur-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(icerik, f)
    return yol


def vt_oku(yol):
    """Test kolu sqlite — D1'in yerel mukabili; SELECT ile tum satirlari okur."""
    conn = sqlite3.connect(yol)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(
            "SELECT gun, kaynak, n FROM rum_vekil WHERE gun=? ORDER BY kaynak", (GUN,)
        ).fetchall()]
    finally:
        conn.close()


def kos(arac, fikstur_yol, vt_yol=None, env_ek=None, cwd=None):
    """Araci alt surec olarak kosar; (rc, stdout, stderr) doner."""
    ortam = os.environ.copy()
    ortam.pop("CLOUDFLARE_API_TOKEN", None)
    ortam.pop("CLOUDFLARE_ACCOUNT_ID", None)
    if env_ek:
        ortam.update(env_ek)
    cmd = [sys.executable, arac, "--gun", GUN, "--fikstur", fikstur_yol]
    if vt_yol:
        cmd += ["--vt", vt_yol]
    p = subprocess.run(cmd, capture_output=True, text=True, env=ortam,
                       cwd=cwd, timeout=120)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def izole_kopya(tmp):
    """Araci gecici dizine kopyalar. MUTANT CANLI GOVDEDE YASAMAZ: bozulan dosya
    repodaki degil, BU kopyadir."""
    hedef_tools = os.path.join(tmp, "tools")
    os.makedirs(hedef_tools, exist_ok=True)
    hedef = os.path.join(hedef_tools, "rum-vekil-olc.py")
    shutil.copyfile(ARAC, hedef)
    return hedef


def mutasyonla(yol, eski, yeni):
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    if govde.count(eski) != 1:
        raise AssertionError("MUTANT CAPASI BAYAT: %r govdede %d kez gecti (1 bekleniyordu)"
                             % (eski, govde.count(eski)))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni))


def v1_birebir(arac, hata):
    """V1 — fikstur uzerinde V1_BEKLENEN ile satirlari birebir karsilastir."""
    fy = fikstur_yaz(V1_FIKSTUR)
    vt = tempfile.mktemp(prefix="rum-vt-", suffix=".sqlite")
    try:
        rc, out, err = kos(arac, fy, vt_yol=vt)
        if rc != 0:
            hata.append("V1 fikstur -> rc=%d (0 bekleniyordu)\n  out: %s\n  err: %s"
                        % (rc, out, err))
            return
        if "RUM_VEKIL=YAZILDI" not in out:
            hata.append("V1 cikti YAZILDI jetonu tasimaz: %r" % out)
        satirlar = vt_oku(vt)
        by_kaynak = {r["kaynak"]: r["n"] for r in satirlar}
        for sinif, bek in V1_BEKLENEN.items():
            if by_kaynak.get(sinif) != bek:
                hata.append("V1 sinif toplami sapmali: %s -> %s (bek %d)  satir=%r"
                            % (sinif, by_kaynak.get(sinif), bek, satirlar))
            else:
                pass
    finally:
        for p in (fy, vt):
            try:
                os.unlink(p)
            except OSError:
                pass


def v2_ciftlenmez(arac, hata):
    """V2 — ayni gun ikici kez kosunca cift sayim YOK (DELETE + INSERT) VE her iki
    kosum da rc=0 donmeli (INSERT basarisiz olursa = DELETE calismamis demektir)."""
    fy = fikstur_yaz(V1_FIKSTUR)
    vt = tempfile.mktemp(prefix="rum-vt-", suffix=".sqlite")
    try:
        rc1, _, _ = kos(arac, fy, vt_yol=vt)
        satirlar1 = vt_oku(vt)
        rc2, _, _ = kos(arac, fy, vt_yol=vt)
        satirlar2 = vt_oku(vt)
        if rc1 != 0 or rc2 != 0:
            hata.append("V2 rc sapmali: ilk=%d ikinci=%d (0 bekleniyordu)" % (rc1, rc2))
        if satirlar1 != satirlar2:
            hata.append("V2 ayni gun iki kosum farkli: ilk=%r ikinci=%r"
                        % (satirlar1, satirlar2))
    finally:
        for p in (fy, vt):
            try:
                os.unlink(p)
            except OSError:
                pass


def v3_env_yok(arac, hata):
    """V3 — env yoksa rc=3 + OLCULEMEDI; --fikstur verilse bile canliya gecmez."""
    fy = fikstur_yaz(V1_FIKSTUR)
    vt = tempfile.mktemp(prefix="rum-vt-", suffix=".sqlite")
    try:
        # fikstur verilip env OLMADAN --fikstur kolu SAGLIKLI calismali (env yoklugu
        # SADECE canli GraphQL kolu icin fail-closed; spec "env yok -> rc=3").
        # Burada --fikstur VERMEYEREK canli yolun envsiz davranisini olc.
        ortam = os.environ.copy()
        ortam.pop("CLOUDFLARE_API_TOKEN", None)
        ortam.pop("CLOUDFLARE_ACCOUNT_ID", None)
        p = subprocess.run([sys.executable, arac, "--gun", GUN],
                           capture_output=True, text=True, env=ortam,
                           cwd=os.path.dirname(ARAC), timeout=120)
        if p.returncode != 3 or "RUM_VEKIL=OLCULEMEDI sebep=JETON-YOK" not in (p.stdout + p.stderr):
            hata.append("V3 env yok: rc=%d (bek 3) JETON-YOK bekleniyordu\n  out: %s\n  err: %s"
                        % (p.returncode, p.stdout, p.stderr))
    finally:
        for p in (fy, vt):
            try:
                os.unlink(p)
            except OSError:
                pass


def v4_errors_dolu(arac, hata):
    """V4 — GraphQL `errors` dolu gelince rc=3 + GRAFIK-HATA."""
    fik = {
        "errors": [{"message": "yanlis filtre"}],
        "data": {"viewer": {"accounts": [{"rumPageloadEventsAdaptiveGroups": []}]}},
    }
    fy = fikstur_yaz(fik)
    vt = tempfile.mktemp(prefix="rum-vt-", suffix=".sqlite")
    try:
        rc, out, err = kos(arac, fy, vt_yol=vt)
        if rc != 3 or "GRAFIK-HATA" not in (out + err):
            hata.append("V4 errors dolu: rc=%d GRAFIK-HATA bekleniyordu\n  out: %s\n  err: %s"
                        % (rc, out, err))
    finally:
        for p in (fy, vt):
            try:
                os.unlink(p)
            except OSError:
                pass


def v5_stdout_sayi_yok(arac, hata):
    """V5 — basarili kosumda stdout HICBIR rakam dizgesi tasimaz (gun=Y-M-D formati
    disinda; '-' ve ':' tasimayan sayi)."""
    fy = fikstur_yaz(V1_FIKSTUR)
    vt = tempfile.mktemp(prefix="rum-vt-", suffix=".sqlite")
    try:
        rc, out, err = kos(arac, fy, vt_yol=vt)
        if rc != 0:
            hata.append("V5 basarili kosum YAZILDI vermedi: rc=%d\n  out: %s\n  err: %s"
                        % (rc, out, err))
            return
        # "gun=2026-10-16" YILAN KABULDE cikar (tarih formati); geri kalan metin
        # icindeki HICBIR rakam dizisi gecmemeli.
        kalinti = out.replace("gun=2026-10-16", "").replace("gun=2026-10-16T", "")
        sayilar = re.findall(r"\d+", kalinti)
        if sayilar:
            hata.append("V5 stdout rakam tasiyor: %r (bulunan diziler: %s)" % (out, sayilar))
    finally:
        for p in (fy, vt):
            try:
                os.unlink(p)
            except OSError:
                pass


def v6_token_sizmaz(arac, hata):
    """V6 — sahte token `TESTTOKEN123` (env olarak canli GraphQL kolu kullanir)
    HICBIR cikti/hata metninde gecmemeli."""
    fy = fikstur_yaz(V1_FIKSTUR)
    vt = tempfile.mktemp(prefix="rum-vt-", suffix=".sqlite")
    try:
        # --fikstur verilse bile ortama token koyup HICBIR yerde gorunmedigini olc:
        # simdi fikstur kolu AGA CIKMAZ; token env'de durur, fikstur kullansa bile
        # grafik_kullan_ici_kolonu olmadigi icin kod AG'A GITMEZ; dolayisiyla test
        # canli GraphQL hata yolunu OLER: GRAFIAK-HATA (errors) alip JETON'un
        # stdout/stderr'de gecmedigini kontrol eder.
        fik_errs = {"errors": [{"message": "yetkisiz"}], "data": {"viewer": {"accounts": []}}}
        fy2 = fikstur_yaz(fik_errs)
        rc, out, err = kos(arac, fy2, vt_yol=vt,
                            env_ek={"CLOUDFLARE_API_TOKEN": TEST_TOKEN,
                                    "CLOUDFLARE_ACCOUNT_ID": "ACCT"})
        if rc != 3:
            hata.append("V6 canli kol errors bekliyordu, rc=%d\n  out: %s\n  err: %s"
                        % (rc, out, err))
        if TEST_TOKEN in out or TEST_TOKEN in err:
            hata.append("V6 token '%s' stdout/stderr'da gecti" % TEST_TOKEN)
    finally:
        for p in (fy, vt):
            try:
                os.unlink(p)
            except OSError:
                pass


def v7_sorgu_bicimi(arac, hata):
    """V7 — canli kolun GONDERDIGI GraphQL govdesi kanitli bicimde mi (ag YOK: urlopen
    sahtesi govdeyi yakalar ve ag hatasi firlatir). Fikstur vakalari sorgu metnini HIC
    olcmez; 17 Eki'de `viewer.accounts(` (gecersiz) + `String!` bu boslukta yasadi."""
    import importlib.util
    import urllib.error
    yakala = {}
    sp = importlib.util.spec_from_file_location("rum_vekil_v7", arac)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)

    def sahte(req, timeout=None):
        yakala["govde"] = req.data
        raise urllib.error.URLError("V7 sahte ag")

    eski = m.urllib.request.urlopen
    m.urllib.request.urlopen = sahte
    try:
        m.graphql_yukle(GUN, "T", "ACCT")
    except Exception:
        pass
    finally:
        m.urllib.request.urlopen = eski
    if "govde" not in yakala:
        hata.append("V7 canli kol ag cagrisi yapmadi (govde yakalanamadi)")
        return
    g = json.loads(yakala["govde"].decode("utf-8"))
    q = g.get("query", "")
    tek = re.sub(r"\s+", " ", q)
    sartlar = [
        ("viewer { accounts(filter: {accountTag: $accountTag})" in tek, "viewer{accounts} ic ice degil"),
        ("viewer." not in q, "noktali alan yolu (gecersiz GraphQL)"),
        ("$accountTag: string!" in q, "accountTag skaleri kucuk harf `string!` degil"),
        ("$gun: Date!" in q, "gun skaleri `Date!` degil"),
        ("dimensions { refererHost }" in tek, "refererHost boyutu yok"),
        (q.count("{") == q.count("}"), "suslu parantez dengesiz"),
        (g.get("variables") == {"accountTag": "ACCT", "gun": GUN}, "variables beklenen degil"),
    ]
    for ok, neden in sartlar:
        if not ok:
            hata.append("V7 sorgu bicimi: %s" % neden)


MUTANTLAR = [
    ("M1 DELETE kaldirildi -> V2 cift sayar",
     'DELETE FROM rum_vekil WHERE gun=',
     '/* DELUMAN */ SELECT 1 FROM rum_vekil WHERE gun=',
     "V2_ciftlenmez",
     "DELETE kalkarsa ayni gun ikinci kosum INSERT'i katar ve satirlar COGALIR"),
    ("M2 siniflama daraltildi (l.facebook.com cikar) -> V1 sapmali",
     '("facebook.com", "l.facebook.com", "m.facebook.com", "lm.facebook.com")',
     '("facebook.com", "m.facebook.com", "lm.facebook.com")',
     "V1_birebir",
     "l.facebook.com cikarilinca 62 sayim facebook yerine 'diger'e duser"),
    ("M3 stdout'a toplam basildi -> V5 rakam tasiyor",
     'print("RUM_VEKIL=YAZILDI gun=%s" % gun)',
     'print("RUM_VEKIL=YAZILDI gun=%s n=%d" % (gun, 999))',
     "V5_stdout_sayi_yok",
     "toplam stdout'a basildiginde 'dijital iz' olarak CI loguna sizar"),
    ("M4 noktali alan yolu geri geldi -> V7 gecersiz sorgu",
     '        "  viewer {\\n"\n        "    accounts(filter: {accountTag: $accountTag}) {\\n"',
     '        "  viewer.accounts(filter: {accountTag: $accountTag}) {\\n"\n        "    {\\n"',
     "V7_sorgu_bicimi",
     "17 Eki m3 cikisi `viewer.accounts(` idi: fikstur vakalari yesil kaldi, canlida her gun OLCULEMEDI olurdu"),
]


VAKA_FONKS = {
    "V1_birebir": v1_birebir,
    "V2_ciftlenmez": v2_ciftlenmez,
    "V3_env_yok": v3_env_yok,
    "V4_errors_dolu": v4_errors_dolu,
    "V5_stdout_sayi_yok": v5_stdout_sayi_yok,
    "V6_token_sizmaz": v6_token_sizmaz,
    "V7_sorgu_bicimi": v7_sorgu_bicimi,
}


def main():
    gecen = 0
    toplam_vaka = 7
    hata = []

    v1_birebir(ARAC, hata)
    v2_ciftlenmez(ARAC, hata)
    v3_env_yok(ARAC, hata)
    v4_errors_dolu(ARAC, hata)
    v5_stdout_sayi_yok(ARAC, hata)
    v6_token_sizmaz(ARAC, hata)
    v7_sorgu_bicimi(ARAC, hata)
    gecen = toplam_vaka - len(hata)

    mutant_puan = 0
    mutant_toplam = len(MUTANTLAR)
    tmp = tempfile.mkdtemp(prefix="rum-vekil-mutant-")
    try:
        for ad, capa, yerine, vaka_jeton, iddia in MUTANTLAR:
            k = izole_kopya(tmp)
            try:
                mutasyonla(k, capa, yerine)
            except AssertionError as e:
                hata.append("%s: %s" % (ad, e))
                continue
            # Ilgili vakayi mutant kopya uzerinde kos; beklenti: KIRMIZI yanar.
            v_hata = []
            VAKA_FONKS[vaka_jeton](k, v_hata)
            if v_hata:
                mutant_puan += 1
            else:
                hata.append("%s: MUTANT HAYATTA (vaka %s YESIL kaldi)\n  iddia: %s"
                            % (ad, vaka_jeton, iddia))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.exists(tmp):
            hata.append("TEMIZLIK: gecici dizin silinemedi: %s" % tmp)

    print("KABUL %d/%d MUTANT %d/%d" % (gecen, toplam_vaka, mutant_puan, mutant_toplam))
    for h in hata:
        print("KIRMIZI: %s" % h)
    if hata:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())