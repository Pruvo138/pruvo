#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCI hattinin OAuth yenileme jetonunu YALNIZ `adwords` kapsamiyla uretir ve secret'a yazar.

══════════════════════════════════════════════════════════════════════════════
NEDEN VAR — OLCULEN ARIZA (23-24 Eyl 2026)
══════════════════════════════════════════════════════════════════════════════
22 Eyl'de jeton `gcloud auth application-default login --client-id-file ...` ile
uretildi. gcloud bu komutta `cloud-platform` kapsamini ZORUNLU tutar (dar kapsamla
koşulunca komut durur). Workspace'in Google Cloud OTURUM DENETIMI de Cloud kapsamli
jetonu yeniden-kimlik suresi dolunca durdurur. Sonuc: jeton secret'a 22 Eyl 19:51Z'de
kondu, 23 Eyl 11:59Z'den beri her zamanlanmis kosum
`invalid_grant / invalid_rapt` ile KIRMIZI (son yesil +9,2 sa, ilk kirmizi +16,1 sa).
gcloud ile yeniden uretmek AYNI sure sonra YINE olurdu: tekil yama.

Bu arac gcloud KULLANMAZ. Masaustu OAuth istemcisiyle loopback + PKCE akisini kendisi
kosar ve YALNIZ `https://www.googleapis.com/auth/adwords` ister. Kapsam donuste
OLCULUR: donen kume birebir {adwords} degilse (ornek: `cloud-platform` sizdiysa)
secret'a HICBIR SEY yazilmaz.

══════════════════════════════════════════════════════════════════════════════
🔴 SIFRE SINIFI — OKAN KAPISI
══════════════════════════════════════════════════════════════════════════════
Konsolda istemci anahtari eklemek (json indirmek) ve tarayicidaki onay tiki Okan'indir.
Arac degerleri EKRANA, LOG'A, DISKE yazmaz; `gh secret set`e argv ile DEGIL stdin ile
verir (argv `ps` ile gorunur). Indirilen istemci json'u is bitince SILINIR (disk kurali:
makinede iz birakma) — `--istemciyi-koru` ya da `--kuru` verilmezse.

Kullanim:
  python3 tools/reklam-oci-jeton-yenile.py --istemci ~/Downloads/client_secret_XXX.json
  python3 tools/reklam-oci-jeton-yenile.py --istemci <json> --kuru   # secret'a YAZMAZ

Cikis kodlari (yukleyiciyle AYNI sozlesme): 0 YESIL · 1 KIRMIZI · 2 GIRDI-YOK · 3 OLCULEMEDI
Kabul (arac bittikten sonra, secret'a yazildiysa): zamanlanmis ya da elle tetiklenen
`Reklam OCI kosucu` kosumu `HAL=EL-SIKISMA-TAMAM` basmali; KALICILIK kabulu
jetonun kurulmasindan >24 sa sonraki kosumun da yesil olmasidir.
"""

import argparse
import base64
import hashlib
import http.server
import importlib.util
import json
import os
import secrets
import subprocess
import sys
import urllib.parse
import webbrowser

TOOLS = os.path.dirname(os.path.abspath(__file__))
YUKLEYICI = os.path.join(TOOLS, "reklam-oci-yukleyici.py")

RC_YESIL = 0
RC_KIRMIZI = 1
RC_GIRDI_YOK = 2
RC_OLCULEMEDI = 3

# 🔴 TEK KAPSAM. Buna `cloud-platform` EKLENIRSE jeton yine oturum denetimine girer.
ADS_KAPSAMI = "https://www.googleapis.com/auth/adwords"
CLOUD_KAPSAM_ONEKI = "https://www.googleapis.com/auth/cloud"
YETKI_UCU = "https://accounts.google.com/o/oauth2/v2/auth"
VARSAYILAN_REPO = "Pruvo138/pruvo"
AKIS_ADI = "reklam-oci.yml"

# Secret adlari TEK KAYNAKTAN (yukleyicinin KIMLIK_ALANLARI) dogrulanir; asagidaki
# uclu o kumenin OAuth alt kumesidir ve `secret_adlari_dogrula` ayrismayi KIRMIZI yakar.
SECRET_ISTEMCI_ID = "GOOGLE_ADS_CLIENT_ID"
SECRET_ISTEMCI_SIRRI = "GOOGLE_ADS_CLIENT_SECRET"
SECRET_YENILEME = "GOOGLE_ADS_REFRESH_TOKEN"


def yukleyici_modulu():
    spec = importlib.util.spec_from_file_location("reklam_oci_yukleyici_jeton", YUKLEYICI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ══════════════════════════════════════════════════════════════════════════════
# SAF KOLLAR — kabul testi (`reklam-oci-kosucu-test.py` bolum 12) bunlari GERCEKTEN kosar
# ══════════════════════════════════════════════════════════════════════════════
def istemci_oku(metin):
    """Google'dan indirilen istemci json METNI -> (client_id, client_secret).

    Masaustu istemcisi `installed`, web istemcisi `web` anahtari tasir. Eksikse
    ValueError — mesaj DEGER TASIMAZ.
    """
    try:
        y = json.loads(metin)
    except ValueError:
        raise ValueError("istemci dosyasi JSON degil")
    if not isinstance(y, dict):
        raise ValueError("istemci dosyasi nesne degil")
    govde = y.get("installed") or y.get("web")
    if not isinstance(govde, dict):
        raise ValueError("istemci dosyasinda `installed`/`web` anahtari YOK")
    cid = str(govde.get("client_id") or "").strip()
    sir = str(govde.get("client_secret") or "").strip()
    if not cid or not sir:
        raise ValueError("istemci dosyasinda client_id ya da client_secret BOS")
    return cid, sir


def pkce_cifti(dogrulayici=None):
    """PKCE (S256). Doner: (dogrulayici, meydan_okuma)."""
    d = dogrulayici or secrets.token_urlsafe(64)
    ozet = hashlib.sha256(d.encode("ascii")).digest()
    return d, base64.urlsafe_b64encode(ozet).decode("ascii").rstrip("=")


def yetki_url(client_id, donus_url, meydan_okuma, durum):
    """Onay penceresinin URL'si. 🔴 Kapsam YALNIZ `ADS_KAPSAMI`dir.

    `access_type=offline` + `prompt=consent`: yenileme jetonu HER seferinde doner
    (ikinci onayda Google onu atlayabilir; atlarsa arac KIRMIZI yanar, yazmaz).
    """
    q = [
        ("client_id", client_id),
        ("redirect_uri", donus_url),
        ("response_type", "code"),
        ("scope", ADS_KAPSAMI),
        ("access_type", "offline"),
        ("prompt", "consent"),
        ("code_challenge", meydan_okuma),
        ("code_challenge_method", "S256"),
        ("state", durum),
    ]
    return YETKI_UCU + "?" + urllib.parse.urlencode(q)


def kapsam_hukmu(kapsam_metni):
    """Donen kapsam kumesi BIREBIR {adwords} mi. Doner: (rc, satir).

    🔴 Esitlik aranir, `in` DEGIL: "adwords var" demek `cloud-platform` da var
    olabilir demektir ve oturum denetimi tam olarak o fazlaliga takilir.
    """
    kume = set(str(kapsam_metni or "").split())
    if not kume:
        return RC_KIRMIZI, ("KAPSAM OLCULEMEDI: yanitta `scope` alani BOS — dar kapsam "
                            "KANITLANAMADI, secret'a yazilmaz")
    cloud = sorted(k for k in kume if k.startswith(CLOUD_KAPSAM_ONEKI))
    if cloud:
        return RC_KIRMIZI, ("KAPSAM GENIS: %s — Cloud kapsamli jeton oturum denetimiyle "
                            "(invalid_rapt) YINE olur" % ", ".join(cloud))
    if ADS_KAPSAMI not in kume:
        return RC_KIRMIZI, "KAPSAM EKSIK: %s donmedi" % ADS_KAPSAMI
    fazla = sorted(kume - {ADS_KAPSAMI})
    if fazla:
        return RC_KIRMIZI, "KAPSAM FAZLA: %s" % ", ".join(fazla)
    return RC_YESIL, "KAPSAM=DAR (yalniz adwords)"


def jeton_yaniti_hukmu(kod, govde):
    """Kod takasi yaniti -> (rc, satirlar, yenileme_jetonu|None). AG YOK.

    🔴 Satirlar DEGER TASIMAZ: ne erisim ne yenileme jetonu basilir.
    """
    try:
        k = int(kod or 0)
    except (TypeError, ValueError):
        k = 0
    if k == 0 or k == 429 or 500 <= k < 600:
        return RC_OLCULEMEDI, ["HAL=OLCULEMEDI — kod takasi CEVAPSIZ (HTTP %s)" % k], None
    if k != 200:
        hata = ""
        try:
            hata = str((json.loads(govde or "{}") or {}).get("error") or "")
        except ValueError:
            pass
        return RC_KIRMIZI, ["HAL=KIRMIZI — kod takasi REDDEDILDI (HTTP %s, error=%s)"
                            % (k, hata or "?")], None
    try:
        y = json.loads(govde or "{}") or {}
    except ValueError:
        return RC_KIRMIZI, ["HAL=KIRMIZI — kod takasi yaniti JSON degil"], None
    yenileme = str(y.get("refresh_token") or "")
    if not yenileme:
        return RC_KIRMIZI, ["HAL=KIRMIZI — yanitta refresh_token YOK (onay ekrani "
                            "atlanmis olabilir; Google hesabindaki uygulama erisimini "
                            "kaldirip yeniden dene)"], None
    k_rc, k_satir = kapsam_hukmu(y.get("scope"))
    if k_rc != RC_YESIL:
        return k_rc, ["HAL=KIRMIZI — %s" % k_satir], None
    return RC_YESIL, ["HAL=YESIL — yenileme jetonu ALINDI · %s" % k_satir], yenileme


def gh_secret_yaz(ad, deger, repo, calistir=None):
    """`gh secret set` — DEGER STDIN'DEN gider, argv'de ASLA durmaz. Doner: rc.

    🔴 `--body <deger>` argv'de durur ve `ps` ile gorunur; bu yol ACILMAZ.
    """
    calistir = calistir or subprocess.run
    p = calistir(["gh", "secret", "set", ad, "--repo", repo],
                 input=deger, text=True, capture_output=True)
    return int(getattr(p, "returncode", 1))


def istemci_sil(yol):
    """Indirilen istemci json'unu SIL. Doner: dosya artik YOK mu (bool)."""
    try:
        os.remove(yol)
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return not os.path.exists(yol)


def secret_adlari_dogrula(mod):
    """Buradaki uc secret adi yukleyicinin TEK KAYNAGINDA var mi. Doner: eksik listesi."""
    tek = set(getattr(mod, "ZORUNLU_ALAN_ADLARI", ()))
    return [a for a in (SECRET_ISTEMCI_ID, SECRET_ISTEMCI_SIRRI, SECRET_YENILEME)
            if a not in tek]


# ══════════════════════════════════════════════════════════════════════════════
# AG KOLLARI — yalniz `main()` cagirir
# ══════════════════════════════════════════════════════════════════════════════
def onay_kodu_bekle(sunucu, beklenen_durum, zaman_asimi=300):
    """Loopback sunucusunda TEK donusu bekler. Doner: (kod|None, hata_metni)."""
    sonuc = {}

    class _Isleyici(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server sozlesmesi)
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            sonuc["durum"] = (q.get("state") or [""])[0]
            sonuc["kod"] = (q.get("code") or [""])[0]
            sonuc["hata"] = (q.get("error") or [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>Tamam. Bu sekmeyi kapatabilirsiniz.</p>".encode("utf-8"))

        def log_message(self, *_a):   # istek satiri (kod tasir) log'a DUSMEZ
            pass

    sunucu.RequestHandlerClass = _Isleyici
    sunucu.timeout = zaman_asimi
    sunucu.handle_request()
    if not sonuc:
        return None, "onay penceresinden %d sn icinde donus GELMEDI" % zaman_asimi
    if sonuc.get("hata"):
        return None, "Google onayi REDDETTI: %s" % sonuc["hata"]
    if not secrets.compare_digest(sonuc.get("durum", ""), beklenen_durum):
        return None, "state ESLESMEDI (baska bir istek geldi) — kod KULLANILMADI"
    if not sonuc.get("kod"):
        return None, "donuste `code` YOK"
    return sonuc["kod"], ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--istemci", required=True,
                    help="Google Cloud konsolundan indirilen Masaustu istemci json'u")
    ap.add_argument("--repo", default=VARSAYILAN_REPO)
    ap.add_argument("--kuru", action="store_true",
                    help="jetonu al ve dogrula ama secret'a YAZMA")
    ap.add_argument("--istemciyi-koru", action="store_true",
                    help="istemci json'unu SILME (varsayilan: is bitince silinir)")
    ap.add_argument("--tarayici-acma", action="store_true",
                    help="URL'yi yalniz bas, tarayiciyi acma")
    a = ap.parse_args(argv)

    mod = yukleyici_modulu()
    eksik_ad = secret_adlari_dogrula(mod)
    if eksik_ad:
        print("HAL=OLCULEMEDI — secret adlari TEK KAYNAKTA yok: %s" % ", ".join(eksik_ad))
        return RC_OLCULEMEDI

    yol = os.path.expanduser(a.istemci)
    try:
        with open(yol, encoding="utf-8") as f:
            client_id, client_secret = istemci_oku(f.read())
    except OSError as e:
        print("HAL=GIRDI-YOK — istemci dosyasi okunamadi: %s" % e.strerror)
        return RC_GIRDI_YOK
    except ValueError as e:
        print("HAL=GIRDI-YOK — %s" % e)
        return RC_GIRDI_YOK

    rc = RC_KIRMIZI
    try:
        sunucu = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
        donus_url = "http://127.0.0.1:%d/" % sunucu.server_address[1]
        dogrulayici, meydan = pkce_cifti()
        durum = secrets.token_urlsafe(24)
        url = yetki_url(client_id, donus_url, meydan, durum)
        # 🔴 URL client_id TASIR (yukleyicide GIZLI sinifi): yalniz tarayici
        # acilmayacaksa basilir.
        if a.tarayici_acma:
            print("Onay penceresi (yalniz adwords kapsami):")
            print("  %s" % url)
        else:
            print("Tarayicida onay penceresi acildi (yalniz adwords kapsami); "
                  "hesabi secip Izin ver'e basin.")
            webbrowser.open(url)
        try:
            kod, hata = onay_kodu_bekle(sunucu, durum)
        finally:
            sunucu.server_close()
        if not kod:
            print("HAL=KIRMIZI — %s" % hata)
            return RC_KIRMIZI

        tas = mod.HttpTasiyici()
        h_kod, h_govde = tas.istek(mod.OAUTH_UCU, {
            "code": kod, "client_id": client_id, "client_secret": client_secret,
            "redirect_uri": donus_url, "grant_type": "authorization_code",
            "code_verifier": dogrulayici}, {}, bicim="form")
        rc, satirlar, yenileme = jeton_yaniti_hukmu(h_kod, h_govde)
        for s in satirlar:
            print(mod.gizle(s, [client_secret, client_id]))
        if rc != RC_YESIL:
            return rc

        # ── Yeni jeton GERCEKTEN takas ediliyor mu (hattin kullandigi AYNI govde) ──
        kml = mod.Kimlik({SECRET_ISTEMCI_ID: client_id,
                          SECRET_ISTEMCI_SIRRI: client_secret,
                          SECRET_YENILEME: yenileme})
        jeton, t_kod, t_hata = mod.erisim_jetonu_kodlu(kml, tas)
        if not jeton:
            print("HAL=KIRMIZI — yeni jeton takas EDILEMEDI (HTTP %s · OAUTH_SINIF=%s)"
                  % (t_kod, mod.oauth_hata_sinifi(t_hata)))
            return RC_KIRMIZI
        print("TAKAS=OK — yeni yenileme jetonu erisim jetonu uretiyor")

        if a.kuru:
            print("KURU — secret'a YAZILMADI (uc alan dogrulandi)")
            rc = RC_YESIL
        else:
            yazim = [(ad, gh_secret_yaz(ad, deger, a.repo)) for ad, deger in (
                (SECRET_ISTEMCI_ID, client_id),
                (SECRET_ISTEMCI_SIRRI, client_secret),
                (SECRET_YENILEME, yenileme))]
            for ad, yrc in yazim:
                print("SECRET %s rc=%d" % (ad, yrc))
            if any(yrc != 0 for _ad, yrc in yazim):
                print("HAL=KIRMIZI — secret yazimi TAMAMLANMADI (uclu TUTARSIZ olabilir)")
                return RC_KIRMIZI
            p = subprocess.run(["gh", "workflow", "run", AKIS_ADI, "--repo", a.repo],
                               capture_output=True, text=True)
            print("AKIS TETIKLENDI rc=%d — kabul: `gh run list --repo %s --workflow "
                  "\"Reklam OCI kosucu\" --limit 1` -> HAL=EL-SIKISMA-TAMAM"
                  % (p.returncode, a.repo))
            rc = RC_YESIL
        return rc
    finally:
        # `--kuru` ardindan gercek kosum gelir; json o kosumun sonunda silinir.
        if a.kuru and not a.istemciyi_koru:
            print("KURU — istemci json KORUNDU; gercek kosumun sonunda silinir")
        elif not a.istemciyi_koru:
            print("ISTEMCI JSON %s" % ("SILINDI" if istemci_sil(yol)
                                       else "SILINEMEDI — ELLE SIL: " + yol))


if __name__ == "__main__":
    sys.exit(main())
