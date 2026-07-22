#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI D1 TESHIS SONDASI (GECICI) — olu senkron adiminin kok nedenini AYIRT eder.

NEDEN VAR (olculdu, 21-22 Tem): deploy.yml "Katalogu D1'e senkronla" adimi 21 Tem
09:23 UTC'den beri HER kosumda "Couldn't find DB with name '...'" ile exit 1
(continue-on-error maskeliyor; son yesil run 08:42 UTC). ELENENLER: database_id
(tek+gecerli, yerel `wrangler d1 list` teyitli) · hesap id · wrangler surumu
(4.112.0, pencerede yayin yok). KALAN IKI ADAY:
  (a) CI token'inin D1 yetkisi CF tarafinda dusmus — token GECERLI (ayni kosumda
      zone purge 200), GitHub secret 13 Tem'den beri degismemis.
  (b) ayni pencerede eklenen setup-node@v4 / Node 20 pini (commit 9362076,
      21 Tem 09:23:36 UTC — ilk kirmizi run ile birebir).
Bu sonda iki adayi ayirt edecek olcumleri yapar ve YALNIZ dar bir beyaz-liste
`anahtar=deger` cikti kumesi basar. Senkron adiminin davranisina DOKUNMAZ.

AYIRT MANTIGI (log'u okuyan icin):
  * d1_list_exit=0 + hedef_gorunur=EVET ama d1_execute_exit!=0  -> execute-ozel ariza
  * d1_list auth10000=EVET / hedef_gorunur=HAYIR                 -> aday (a) token/yetki
  * setup-node PATH'iyle KIRMIZI ama sistem node'uyla YESIL      -> aday (b) Node pini
  * ikisi de KIRMIZI                                             -> aday (a) guclenir

GUVENLIK — REPO PUBLIC, ACTIONS LOGU HERKESE ACIK:
  DB adi / UUID / hesap listesi / token / ham wrangler ciktisi ASLA basilmaz.
  TUM cikti tek kapidan (bas()) gecer; kapi beyaz-liste disi anahtari ya da
  UUID/uzun-hex/izinsiz karakter tasiyan degeri SANSUR'e cevirir (fail-closed).
  Kabul testi: tools/ci-d1-teshis-guvenlik-test.py (CI'da bu sondadan ONCE kosar).

Kullanim:
  python3 tools/ci-d1-teshis.py                     # CI sondasi (ag + wrangler)
  python3 tools/ci-d1-teshis.py --liste-json <yol>  # OFFLINE: verilen sahte `d1 list`
                                                    # JSON'unu ayni ayristirici+cikti
                                                    # kapisindan gecirir (guvenlik testi)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)

# ---------------------------------------------------------------------------
# CIKTI KAPISI — sondanin stdout'a cikan HER satiri buradan gecer.
# ---------------------------------------------------------------------------
IZINLI_ANAHTARLAR = {
    "node_surum",
    "npx_var",
    "wrangler_surum",
    "wrangler_surum_exit",
    "token_var",
    "d1_list_exit",
    "d1_list_auth10000",
    "toplam_db_adedi",
    "hedef_gorunur",
    "hedef_kaynak",
    "d1_execute_exit",
    "d1_execute_auth10000",
    "d1_execute_ad_hatasi",
    "sistem_node",
    "sistem_node_surum",
    "sistem_node_list_exit",
    "sistem_node_hedef_gorunur",
    "teshis_ic_hata",
}
# Deger: kisa, dar alfabe. UUID'nin zorunlu '-' ayraclari ve hesap-id'nin 32-hex
# govdesi asagidaki iki desenle ayrica avlanir (alfabe tek basina yetmez).
_DEGER_DESEN = re.compile(r"^[A-Za-z0-9.\-]{1,32}$")
_UUID_DESEN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_UZUN_HEX_DESEN = re.compile(r"[0-9a-fA-F]{20,}")


def bas(anahtar, deger):
    """Tek cikti kapisi. Beyaz-liste disi anahtar/deger -> SANSUR (fail-closed)."""
    deger = str(deger)
    if anahtar not in IZINLI_ANAHTARLAR:
        print("izinsiz_anahtar=SANSUR")
        return
    if (not _DEGER_DESEN.match(deger)
            or _UUID_DESEN.search(deger)
            or _UZUN_HEX_DESEN.search(deger)):
        print(anahtar + "=SANSUR")
        return
    print(anahtar + "=" + deger)


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------
def kos(komut, ortam=None, saniye=300):
    """Alt sureci kostur; (exit, stdout, stderr) dondur. Timeout -> exit 901."""
    try:
        p = subprocess.run(komut, cwd=KOK, capture_output=True, text=True,
                           env=ortam, timeout=saniye)
        return p.returncode, (p.stdout or ""), (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 901, "", ""
    except FileNotFoundError:
        return 902, "", ""


def hedef_db():
    """d1-sync.py'deki DB sabitini (senkron adiminin KULLANDIGI tanimlayici) oku.
    Tek kaynak: ayri bir kopya tutulmaz; sabit tasinirsa sonda HAYIR degil YOK der."""
    yol = os.path.join(TOOLS, "d1-sync.py")
    try:
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
    except OSError:
        return None
    m = re.search(r'^DB = "([0-9a-fA-F-]{36})"', metin, re.MULTILINE)
    return m.group(1) if m else None


def liste_coz(ham_json_metin, hedef):
    """`wrangler d1 list --json` metnini coz -> (toplam, gorunur) — ikisi de guvenli.
    Cozulemezse (-1, "BILINMIYOR")."""
    i = ham_json_metin.find("[")
    if i == -1:
        return -1, "BILINMIYOR"
    try:
        veri = json.loads(ham_json_metin[i:])
    except json.JSONDecodeError:
        return -1, "BILINMIYOR"
    if not isinstance(veri, list):
        return -1, "BILINMIYOR"
    gorunur = "HAYIR"
    if hedef:
        for kayit in veri:
            if isinstance(kayit, dict) and str(kayit.get("uuid", "")).lower() == hedef.lower():
                gorunur = "EVET"
                break
    else:
        gorunur = "BILINMIYOR"
    return len(veri), gorunur


def _npx():
    return ["npx", "--yes", "wrangler@4"]


# ---------------------------------------------------------------------------
# Sondalar
# ---------------------------------------------------------------------------
def surum_sondasi():
    kod, cikti, _ = kos(["node", "--version"])
    m = re.search(r"v\d+\.\d+\.\d+", cikti)
    bas("node_surum", m.group(0) if (kod == 0 and m) else "YOK")
    bas("npx_var", "EVET" if shutil.which("npx") else "HAYIR")
    kod, cikti, hata = kos(_npx() + ["--version"])
    m = re.search(r"\d+\.\d+\.\d+", cikti + hata)
    bas("wrangler_surum_exit", kod)
    bas("wrangler_surum", m.group(0) if m else "YOK")


def d1_list_sondasi(hedef, ortam=None, onek=""):
    """d1 list sondasi. onek=""  -> d1_list_* anahtarlari;
    onek="sistem" -> sistem_node_list_exit / sistem_node_hedef_gorunur."""
    kod, cikti, hata = kos(_npx() + ["d1", "list", "--json"], ortam=ortam)
    # Ham cikti GECICI dosyaya alinir (log'a degil) — ayristirici dosyadan okur.
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     prefix="pruvo-d1-teshis-") as f:
        f.write(cikti)
        gecici = f.name
    with open(gecici, encoding="utf-8") as f:
        toplam, gorunur = liste_coz(f.read(), hedef)
    os.unlink(gecici)
    if onek == "sistem":
        bas("sistem_node_list_exit", kod)
        bas("sistem_node_hedef_gorunur", gorunur if kod == 0 else "BILINMIYOR")
        return
    bas("d1_list_exit", kod)
    bas("d1_list_auth10000",
        "EVET" if ("code: 10000" in (cikti + hata) or "Authentication error" in (cikti + hata))
        else "HAYIR")
    bas("toplam_db_adedi", toplam if kod == 0 else -1)
    bas("hedef_gorunur", gorunur if kod == 0 else "BILINMIYOR")


def d1_execute_sondasi(hedef):
    if not hedef:
        bas("d1_execute_exit", 903)
        return
    kod, cikti, hata = kos(
        _npx() + ["d1", "execute", hedef, "--remote", "--json", "--command", "SELECT 1"])
    ham = cikti + hata
    bas("d1_execute_exit", kod)
    bas("d1_execute_auth10000",
        "EVET" if ("code: 10000" in ham or "Authentication error" in ham) else "HAYIR")
    # Yasanan tam belirti: wrangler UUID'yi ada dusurup "Couldn't find DB with name" diyor.
    bas("d1_execute_ad_hatasi", "EVET" if "Couldn't find DB with name" in ham else "HAYIR")


def sistem_node_sondasi(hedef):
    """Aday (b) testi: setup-node'un PATH'e koydugu hostedtoolcache node'u AYIKLANIR,
    runner'in kendi (sistem) node'uyla ayni d1 list sondasi tekrarlanir. setup-node
    izi yoksa (yerel kosum) sonda ATLANIR — sahte sinyal uretmez."""
    yol = os.environ.get("PATH", "")
    parcalar = yol.split(os.pathsep)
    suzgec = [p for p in parcalar if "hostedtoolcache" not in p.lower()]
    if suzgec == parcalar:
        bas("sistem_node", "ATLANDI")
        return
    yeni_yol = os.pathsep.join(suzgec)
    ortam = dict(os.environ, PATH=yeni_yol)
    if not (shutil.which("node", path=yeni_yol) and shutil.which("npx", path=yeni_yol)):
        bas("sistem_node", "YOK")
        return
    bas("sistem_node", "EVET")
    kod, cikti, _ = kos(["node", "--version"], ortam=ortam)
    m = re.search(r"v\d+\.\d+\.\d+", cikti)
    bas("sistem_node_surum", m.group(0) if (kod == 0 and m) else "YOK")
    d1_list_sondasi(hedef, ortam=ortam, onek="sistem")


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste-json", default=None,
                    help="OFFLINE: verilen d1-list JSON dosyasini ayristir + bas (ag yok)")
    args = ap.parse_args()

    hedef = hedef_db()
    bas("hedef_kaynak", "EVET" if hedef else "YOK")

    if args.liste_json:
        # Guvenlik kabul testinin yolu: ag/wrangler YOK, yalniz ayristirici + cikti kapisi.
        with open(args.liste_json, encoding="utf-8") as f:
            toplam, gorunur = liste_coz(f.read(), hedef)
        bas("d1_list_exit", 0)
        bas("toplam_db_adedi", toplam)
        bas("hedef_gorunur", gorunur)
        return 0

    surum_sondasi()
    if not os.environ.get("CLOUDFLARE_API_TOKEN"):
        bas("token_var", "HAYIR")  # fork/tokensiz kosum: ag sondalari deterministik atlanir
        return 0
    bas("token_var", "EVET")
    d1_list_sondasi(hedef)
    d1_execute_sondasi(hedef)
    sistem_node_sondasi(hedef)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # log'a traceback dokme: sinif adi yeter, gerisi SANSUR kapisinda
        bas("teshis_ic_hata", type(e).__name__)
        sys.exit(0)
