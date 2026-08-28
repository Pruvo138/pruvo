#!/usr/bin/env python3
"""cf-durum.py — Cloudflare/GitHub panel durumunu TARAYICI YERINE API'den oku (SALT OKUMA).

Amac: panel turlarinin cogunu kaldirmak; Okan'in ekraninda pencere acilmasin.
Hicbir alt komut degisiklik yapmaz (POST yalniz GraphQL ANALITIK sorgusu icin).

Kimlik sirasi:
  1) ortam: CLOUDFLARE_API_TOKEN (+ varsa CLOUDFLARE_ACCOUNT_ID) — Actions ile ayni adlar
  2) dosya: ~/.claude/cron/.cf-token (varsa, kirpilmis icerik; yoksa/bossa sessizce gec)
  3) wrangler OAuth: ~/.wrangler/config/default.toml (oauth_token; suresi dolmussa
     yenileme BU ARACTAN YAPILMAZ — bir kez `npx --yes wrangler@4 whoami` kosulur)

Cikis kodlari: 0=basari · 3=kimlik yok/yetki eksik (OKAN KAPISI: kapsam panelde eklenir)
               4=ag/uc hatasi

GUVENLIK: token degeri hicbir ciktiya yazilmaz; hesap adi/id MASKELENIR; DNS kayit
icerikleri ilk 6 karakter + '…' ile gosterilir.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

CF_BASE = "https://api.cloudflare.com/client/v4"
GH_API = "https://api.github.com"
GH_REPO = "Pruvo138/pruvo"          # public repo — GitHub Pages dagitimlari burada
WRANGLER_TOML = os.path.expanduser("~/.wrangler/config/default.toml")
CF_TOKEN_DOSYA = os.path.expanduser("~/.claude/cron/.cf-token")
DB_AD = "pruvo-katalog"

RC_OK = 0
RC_YETKI = 3
RC_AG = 4

HTTP_ZAMAN_ASIMI = 30
D1_ZAMAN_ASIMI = 600


class YetkiEksik(Exception):
    """Kimlik yok ya da kapsam yetmiyor — OKAN KAPISI."""


class AgHatasi(Exception):
    """Ag ya da uc hatasi."""


def _maske(deger, n=6):
    deger = str(deger or "")
    return (deger[:n] + "…") if deger else "—"


# 🔴 28 Agu 2026 — TOKEN_BICIM_KOLU (Okan emri sinifi: canli sizinti yolu).
# ONCE: `~/.claude/cron/.cf-token` BOS DEGILSE token sayiliyordu ve icerik
# dogrudan `Authorization: Bearer <icerik>` basligina gidiyordu. Dosyaya bir ic
# hatirlatma metni yazilinca her kosum o metni ucuncu tarafa GONDERDI (401 doner
# ama baytlar GITMISTIR). Cloudflare API token'lari tek satir, `[A-Za-z0-9_-]`
# alfabesinde ve uzun olur; prose bu bicime UYMAZ.
# SIMDI: bicim tutmuyorsa icerik TOKEN DEGILDIR — dosya kolu sessizce ATLANIR ve
# sonraki kaynaga (wrangler OAuth) dusulur. Bu bir GEVSETME degil DARALTMADIR:
# gecerli bicimli token AYNEN kabul edilir, bos dosya AYNEN sessiz gecer.
# 🔴 ICERIK HICBIR YERE BASILMAZ — uyari satiri yalnizca BAYT SAYISI tasir.
# Kabul: python3 tools/cf-durum.py --kendini-test
_CF_TOKEN_BICIMI = re.compile(r"^[A-Za-z0-9_-]{30,}$")


def _dosya_tokeni(yol=None):
    """`.cf-token` icerigini YALNIZ token bicimindeyse dondur; aksi halde None."""
    hedef = yol or CF_TOKEN_DOSYA
    if not os.path.exists(hedef):
        return None
    try:
        with open(hedef, encoding="utf-8", errors="replace") as dosya:
            ham = dosya.read()
    except OSError:
        return None
    icerik = ham.strip()
    if not icerik:
        return None                      # bos dosya: eskisi gibi SESSIZ gec
    if "\n" in icerik or not _CF_TOKEN_BICIMI.match(icerik):
        sys.stderr.write(
            "UYARI: %s TOKEN BICIMINDE DEGIL (%d bayt) — kimlik kaynagi olarak "
            "KULLANILMADI, sonraki kaynaga dusuldu. Icerik BASILMAZ; token "
            "yenileme OKAN KAPISI'dir.\n" % (hedef, len(ham)))
        return None
    return icerik


def kimlik_bul():
    """(token, account_id|None, kaynak) dondur; bulamazsa YetkiEksik."""
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if tok:
        return tok, os.environ.get("CLOUDFLARE_ACCOUNT_ID"), "ortam(CLOUDFLARE_API_TOKEN)"
    tok = _dosya_tokeni()
    if tok:
        return tok, os.environ.get("CLOUDFLARE_ACCOUNT_ID"), "dosya(~/.claude/cron/.cf-token)"
    if os.path.exists(WRANGLER_TOML):
        icerik = open(WRANGLER_TOML).read()
        m = re.search(r'oauth_token\s*=\s*"([^"]+)"', icerik)
        if m:
            son = re.search(r'expiration_time\s*=\s*"([^"]+)"', icerik)
            if son:
                try:
                    bitis = datetime.fromisoformat(son.group(1).replace("Z", "+00:00"))
                    if bitis <= datetime.now(timezone.utc):
                        raise YetkiEksik(
                            "wrangler OAuth token SURESI DOLMUS (%s). Yenileme bu aractan "
                            "yapilmaz; bir kez: npx --yes wrangler@4 whoami (tarayici girisi "
                            "gerekebilir — OKAN KAPISI) ya da CLOUDFLARE_API_TOKEN verin."
                            % son.group(1))
                except ValueError:
                    pass  # tarih cozulemedi — token'i dene, uc karar versin
            return m.group(1), None, "wrangler-oauth(~/.wrangler/config/default.toml)"
    raise YetkiEksik(
        "Cloudflare kimligi YOK. Beklenen kaynaklar: ortamda CLOUDFLARE_API_TOKEN veya "
        "~/.claude/cron/.cf-token dosyasi veya ~/.wrangler/config/default.toml icinde "
        "oauth_token. Token uretme/degistirme "
        "OKAN KAPISI'dir — panelde 'My Profile → API Tokens' uzerinden salt-okuma "
        "kapsamli token eklenmeli.")


def _cf_istek(yol, token, kapsam, method="GET", data=None):
    """Cloudflare API cagrisi. 401/403 -> YetkiEksik(kapsam); diger -> AgHatasi."""
    govde = json.dumps(data).encode() if data is not None else None
    istek = urllib.request.Request(
        CF_BASE + yol, data=govde, method=method,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(istek, timeout=HTTP_ZAMAN_ASIMI) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise YetkiEksik(
                "yetki eksik (HTTP %s): %s — Cloudflare panelinde API token'a bu kapsam "
                "eklenmeli (OKAN KAPISI; bu araç token uretmez/degistirmez)."
                % (e.code, kapsam))
        raise AgHatasi("Cloudflare API HTTP %s (%s)" % (e.code, yol))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AgHatasi("Cloudflare API erisilemedi (%s): %s" % (yol, e))


def hesap_id_bul(token, bilinen=None):
    if bilinen:
        return bilinen
    res = _cf_istek("/accounts?per_page=5", token,
                    "Account → Account Settings → Read")
    hesaplar = res.get("result") or []
    if not hesaplar:
        raise YetkiEksik(
            "/accounts bos dondu — token hicbir hesaba hesap-duzeyinde bagli degil "
            "(zone-kapsamli token). Eksik kapsam: Account → Account Settings → Read "
            "(R2 icin ayrica Account → Cloudflare R2 → Read) — panelde token'a eklenmeli "
            "(OKAN KAPISI; bu arac token uretmez/degistirmez).")
    return hesaplar[0]["id"]


# ---------------------------------------------------------------- D1
def d1_durum():
    """Kanonik okuyucu tools/d1-sync.py --durum'dur; ikinci kopya YAZILMAZ, o cagrilir."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    arac = os.path.join(repo, "tools", "d1-sync.py")
    if not os.path.exists(arac):
        raise AgHatasi("tools/d1-sync.py bulunamadi: " + arac)
    print("(kanonik okuyucu: tools/d1-sync.py --durum --hizli cagriliyor)", flush=True)
    try:
        p = subprocess.run([sys.executable, arac, "--durum", "--hizli"],
                           cwd=repo, timeout=D1_ZAMAN_ASIMI)
    except subprocess.TimeoutExpired:
        raise AgHatasi("d1-sync.py --durum %ds icinde bitmedi." % D1_ZAMAN_ASIMI)
    if p.returncode != 0:
        raise AgHatasi("d1-sync.py --durum rc=%s (ustteki ciktiya bakin)" % p.returncode)


# ---------------------------------------------------------------- R2
def r2_durum(token, acc):
    res = _cf_istek("/accounts/%s/r2/buckets?per_page=50" % acc, token,
                    "Account → Cloudflare R2 → Read")
    kovalar = res.get("result") or []
    if isinstance(kovalar, dict):
        kovalar = kovalar.get("buckets", [])
    isimler = [k.get("name") for k in kovalar]

    olcum = {}
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sorgu = {"query": (
        "query { viewer { accounts(filter: {accountTag: \"%s\"}) { "
        "r2StorageAdaptiveGroups(limit: 200, filter: {datetime_geq: \"%s\"}, "
        "orderBy: [datetime_DESC]) { dimensions { bucketName datetime } "
        "max { objectCount payloadSize } } } } }" % (acc, since))}
    g = _cf_istek("/graphql", token, "Account → Account Analytics → Read",
                  method="POST", data=sorgu)
    if g.get("errors"):
        raise AgHatasi("GraphQL analitik hatasi: " +
                       json.dumps(g["errors"], ensure_ascii=False)[:300])
    gruplar = (((g.get("data") or {}).get("viewer") or {}).get("accounts") or [{}])[0]
    for satir in gruplar.get("r2StorageAdaptiveGroups") or []:
        ad = satir["dimensions"]["bucketName"]
        if ad not in olcum:  # DESC sirali — ilk gorulen en taze
            olcum[ad] = satir["max"]

    print("R2 kovalari (%d):" % len(isimler))
    for k in kovalar:
        ad = k.get("name")
        m = olcum.get(ad) or {}
        nesne = m.get("objectCount")
        boyut = m.get("payloadSize")
        boyut_s = ("%.2f GB" % (boyut / 1e9)) if isinstance(boyut, (int, float)) else "—"
        print("  %-22s nesne=%-8s boyut=%-9s olusturma=%s"
              % (ad, nesne if nesne is not None else "—", boyut_s,
                 k.get("creation_date", "—")))


# ---------------------------------------------------------------- Pages (GitHub)
def _gh_get(yol):
    istek = urllib.request.Request(GH_API + yol, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "pruvo-cf-durum"})
    try:
        with urllib.request.urlopen(istek, timeout=HTTP_ZAMAN_ASIMI) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise AgHatasi("GitHub API HTTP %s (%s)" % (e.code, yol))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AgHatasi("GitHub API erisilemedi: %s" % e)


def pages_durum(adet):
    """Site GitHub Pages'te (repo public): son N dagitim /deployments uzerinden.

    (/pages/builds ucu kimliksiz 404 veriyor; /deployments public ve yeterli —
    her dagitimin son durumu /deployments/{id}/statuses ile okunur.)"""
    deps = _gh_get("/repos/%s/deployments?per_page=%d" % (GH_REPO, adet))
    if not deps:
        print("GitHub dagitimi bulunamadi (%s)." % GH_REPO)
        return
    print("GitHub Pages son %d dagitim (%s):" % (len(deps), GH_REPO))
    for d in deps:
        durum = "—"
        try:
            sts = _gh_get("/repos/%s/deployments/%s/statuses?per_page=1"
                          % (GH_REPO, d.get("id")))
            if sts:
                durum = sts[0].get("state", "—")
        except AgHatasi:
            pass  # tekil durum okunamazsa satiri durumsuz birak
        print("  %-10s %-20s %-14s sha=%s"
              % (d.get("environment", "?"), d.get("created_at", "—"), durum,
                 (d.get("sha") or "")[:8] or "—"))


# ---------------------------------------------------------------- DNS
def dns_durum(token):
    zres = _cf_istek("/zones?name=pruvo3d.com", token,
                     "Zone → Zone → Read")
    zonlar = zres.get("result") or []
    if not zonlar:
        raise AgHatasi("pruvo3d.com zone'u bu hesapta gorunmuyor.")
    zid = zonlar[0]["id"]
    print("zone: pruvo3d.com (id=%s, durum=%s)"
          % (_maske(zid, 4), zonlar[0].get("status", "?")))
    res = _cf_istek("/zones/%s/dns_records?per_page=100" % zid, token,
                    "Zone → DNS → Read (wrangler OAuth bu kapsami TASIMIYOR; DNS icin "
                    "'Zone.DNS Read' kapsamli CLOUDFLARE_API_TOKEN gerekir)")
    kayitlar = res.get("result") or []
    print("DNS kayitlari (%d) — icerikler maskeli:" % len(kayitlar))
    for r in kayitlar:
        print("  %-6s %-40s proxied=%-5s icerik=%s"
              % (r.get("type"), r.get("name"), r.get("proxied"),
                 _maske(r.get("content"))))


# ---------------------------------------------------------------- orkestra
def _kosu(ad, fn):
    print("== %s ==" % ad, flush=True)
    try:
        fn()
        print(flush=True)
        return RC_OK
    except YetkiEksik as e:
        print("YETKI/KIMLIK EKSIK: %s\n" % e, flush=True)
        return RC_YETKI
    except AgHatasi as e:
        print("AG/UC HATASI: %s\n" % e, flush=True)
        return RC_AG


def _baslik_sizintisi_olc(token_dosyasi, wrangler_yolu):
    """Verilen `.cf-token` dosyasiyla kimlik kolunu kosar ve `Authorization`
    basligina FIILEN GIDEN degeri dondurur. AG'A CIKILMAZ (`urlopen` sahte).

    🔴 Olculen sey "fonksiyon None dondu" DEGIL, BASLIGA NE GITTIGIDIR. Mutant
    kosucusu ayni fonksiyonu MUTANT MODULDEN cagirir — iki tarafta AYNI olcum.
    Kimlik hic bulunamazsa "" doner.
    """
    yakalanan = []
    gercek_urlopen = urllib.request.urlopen

    def _sahte_urlopen(istek, timeout=None):
        yakalanan.append(istek.get_header("Authorization") or "")
        raise urllib.error.URLError("SAHTE UC — kendini-test, ag'a CIKILMADI")

    eski_dosya = globals()["CF_TOKEN_DOSYA"]
    eski_toml = globals()["WRANGLER_TOML"]
    eski_env = os.environ.pop("CLOUDFLARE_API_TOKEN", None)
    globals()["CF_TOKEN_DOSYA"] = token_dosyasi
    globals()["WRANGLER_TOML"] = wrangler_yolu
    urllib.request.urlopen = _sahte_urlopen
    try:
        try:
            tok, _hesap, _kaynak = kimlik_bul()
        except YetkiEksik:
            return ""
        try:
            _cf_istek("/user/tokens/verify", tok, "kendini-test")
        except (YetkiEksik, AgHatasi):
            pass
        return "".join(yakalanan)
    finally:
        urllib.request.urlopen = gercek_urlopen
        globals()["CF_TOKEN_DOSYA"] = eski_dosya
        globals()["WRANGLER_TOML"] = eski_toml
        if eski_env is not None:
            os.environ["CLOUDFLARE_API_TOKEN"] = eski_env


def _kendini_test():
    """`--kendini-test` — dosya kimlik kolu + hedef-kol atifli MUTANT. Ag YOK."""
    import importlib.util
    import io
    import shutil
    import tempfile

    sayac = {"vaka": 0, "gecen": 0, "kontrol": 0, "kontrol_gecen": 0}
    dusenler = []

    def olc(ad, beklenen, gozlenen, kontrol=False):
        sayac["vaka"] += 1
        if kontrol:
            sayac["kontrol"] += 1
        tamam = (beklenen == gozlenen)
        if tamam:
            sayac["gecen"] += 1
            if kontrol:
                sayac["kontrol_gecen"] += 1
        else:
            dusenler.append(ad)
            sys.stderr.write("[DUSTU] %s\n  beklenen=%r\n  gozlenen=%r\n"
                             % (ad, beklenen, gozlenen))
        print("VAKA %-50s %s%s" % (ad, "GECTI" if tamam else "DUSTU",
                                   " (KONTROL)" if kontrol else ""))
        return tamam

    kok = tempfile.mkdtemp(prefix="cf-token-kendini-test-")
    try:
        # 🔴 FIKSTURLER SENTETIKTIR — gercek `.cf-token` OKUNMAZ.
        SAHTE_TOKEN = "aB3" + ("x" * 30) + "_-9"
        GIZLI_JETON = "ICYAZISMA_BU_BIR_TOKEN_DEGILDIR_0001"
        gecerli = os.path.join(kok, "gecerli")
        prose = os.path.join(kok, "prose")
        bos = os.path.join(kok, "bos")
        yok_toml = os.path.join(kok, "olmayan.toml")
        var_toml = os.path.join(kok, "wrangler.toml")
        WRANGLER_TOKEN = "wr" + ("y" * 34)
        with open(gecerli, "w") as d:
            d.write(SAHTE_TOKEN + "\n")
        with open(prose, "w") as d:
            d.write(GIZLI_JETON + " — hatirlatma metni, " + ("z" * 700) + "\n")
        with open(bos, "w") as d:
            d.write("")
        with open(var_toml, "w") as d:
            d.write('oauth_token = "%s"\n' % WRANGLER_TOKEN)

        def _uyari_ile(yol):
            eski = sys.stderr
            sys.stderr = tampon = io.StringIO()
            try:
                sonuc = _dosya_tokeni(yol)
            finally:
                sys.stderr = eski
            return sonuc, tampon.getvalue()

        # --- B1: bicim kolu ucu ucuna ---------------------------------------
        t1, u1 = _uyari_ile(gecerli)
        olc("B1a gecerli bicimli token KABUL", (SAHTE_TOKEN, ""), (t1, u1),
            kontrol=True)
        t2, u2 = _uyari_ile(prose)
        olc("B1b prose REDDEDILIR + uyari basilir",
            (None, True), (t2, "TOKEN BICIMINDE DEGIL" in u2))
        olc("B1c uyari ICERIGI TASIMAZ", False, GIZLI_JETON in u2)
        t3, u3 = _uyari_ile(bos)
        olc("B1d bos dosya SESSIZ gecer (gerileme YOK)", (None, ""), (t3, u3),
            kontrol=True)

        # --- B2: ASIL KANIT — basliga NE GITTI ------------------------------
        # 🔴 POZITIF KONTROL ONCE: "sizmadi" iddiasi ancak YAKALAMA CALISIYORSA
        # anlam tasir; kopuk yakalamada da bos dizge gorunur (K182 sinifi).
        b2a = _baslik_sizintisi_olc(gecerli, yok_toml)
        olc("B2a POZITIF KONTROL: yakalama CANLI (gecerli token basliga gider)",
            True, SAHTE_TOKEN in b2a, kontrol=True)
        b2b = _baslik_sizintisi_olc(prose, yok_toml)
        olc("B2b prose'un BIR BAYTI BILE basliga GITMEZ",
            False, GIZLI_JETON in b2b)
        b2c = _baslik_sizintisi_olc(prose, var_toml)
        olc("B2c prose atlanir, WRANGLER koluna DUSULUR",
            (False, True), (GIZLI_JETON in b2c, WRANGLER_TOKEN in b2c))

        # --- B3: MUTANT — hedef kol ADIYLA ----------------------------------
        # Bicim kontrolu oldurulur: B2b/B2c KIRMIZI yanmali, B1a/B1d YESIL
        # kalmali (mutant "her seyi kirdi" ise kirmizinin SEBEBI hedef kol
        # OLDUGU KANITLANMAZ).
        CAPA = '    if "\\n" in icerik or not _CF_TOKEN_BICIMI.match(icerik):'
        MUTANT_ADI = "M-CF1-token-bicim-kolu-olur"
        HEDEF_KOL = "TOKEN_BICIM_KOLU"
        kaynak_yolu = os.path.abspath(__file__)
        with open(kaynak_yolu, encoding="utf-8") as d:
            kaynak = d.read()
        mutant_oldu = mutant_atif = False
        mutant_not = ""
        if kaynak.count(CAPA) != 1:
            mutant_not = "CAPA_SAYISI=%d" % kaynak.count(CAPA)
        else:
            kopya = os.path.join(kok, "cf_durum_mutant.py")
            with open(kopya, "w", encoding="utf-8") as d:
                d.write(kaynak.replace(CAPA, "    if False:", 1))
            spec = importlib.util.spec_from_file_location("cf_durum_mutant", kopya)
            mut = importlib.util.module_from_spec(spec)
            onceki = sys.dont_write_bytecode
            sys.dont_write_bytecode = True
            try:
                spec.loader.exec_module(mut)
            finally:
                sys.dont_write_bytecode = onceki
            m_b2b = mut._baslik_sizintisi_olc(prose, yok_toml)
            m_b2c = mut._baslik_sizintisi_olc(prose, var_toml)
            m_t1, _m_u1 = mut._dosya_tokeni(gecerli), ""
            m_t3 = mut._dosya_tokeni(bos)
            mutant_oldu = (GIZLI_JETON in m_b2b) and (GIZLI_JETON in m_b2c)
            kontrol_yesil = (m_t1 == SAHTE_TOKEN) and (m_t3 is None)
            mutant_atif = mutant_oldu and kontrol_yesil
            mutant_not = "oldurdugu=%s (B2b,B2c) kontrol_yesil=%s" % (
                HEDEF_KOL, kontrol_yesil)
        print("MUTANT %-34s %s ATIF=%s %s" % (
            MUTANT_ADI, "OLDU" if mutant_oldu else "YASADI",
            "EVET" if mutant_atif else "HAYIR", mutant_not))

        # --- CANLI DOSYANIN HALI (icerik OKUNMAZ, yalnizca BICIM hukmu) -----
        canli = "YOK"
        if os.path.exists(CF_TOKEN_DOSYA):
            eski = sys.stderr
            sys.stderr = io.StringIO()
            try:
                canli = "TOKEN_BICIMI" if _dosya_tokeni() else "BICIM_DISI"
            finally:
                sys.stderr = eski
        print("CANLI_CF_TOKEN=%s (icerik OKUNMADI/BASILMADI)" % canli)

        print("CF-KENDINI-TEST VAKA=%d/%d DUSEN=%d MUTANT=%d/1 ATIF=%d/1 "
              "KONTROL=%d/%d"
              % (sayac["gecen"], sayac["vaka"], len(dusenler),
                 1 if mutant_oldu else 0, 1 if mutant_atif else 0,
                 sayac["kontrol_gecen"], sayac["kontrol"]))
        return RC_OK if (not dusenler and mutant_atif) else 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d1", action="store_true", help="D1 katalog durumu (d1-sync.py uzerinden)")
    ap.add_argument("--r2", action="store_true", help="R2 kova listesi + nesne/boyut")
    ap.add_argument("--pages", action="store_true", help="GitHub Pages son dagitimlar")
    ap.add_argument("--dns", action="store_true", help="pruvo3d.com DNS kayitlari (maskeli)")
    ap.add_argument("--hepsi", action="store_true", help="hepsini sirayla")
    ap.add_argument("-n", type=int, default=5, help="--pages icin dagitim sayisi (vars. 5)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="dosya kimlik kolunun fail-closed davranisini OLCER (ag YOK)")
    a = ap.parse_args()
    if a.kendini_test:
        return _kendini_test()
    if not (a.d1 or a.r2 or a.pages or a.dns or a.hepsi):
        ap.print_help()
        return RC_OK

    rcler = []
    if a.d1 or a.hepsi:
        rcler.append(_kosu("D1", d1_durum))

    token = acc = None
    cf_gerek = a.r2 or a.dns or a.hepsi
    if cf_gerek:
        try:
            token, acc, kaynak = kimlik_bul()
            print("kimlik: %s (deger yazilmaz)" % kaynak)
        except (YetkiEksik, AgHatasi) as e:
            print("KIMLIK HATASI: %s" % e)
            return RC_YETKI if isinstance(e, YetkiEksik) else RC_AG

    if a.r2 or a.hepsi:
        # Hesap-duzeyi kapsam YALNIZ R2 icin gerek; zone-kapsamli token'da
        # /accounts bos doner — bu DNS'i engellemesin, R2 bolumu kendi hatasini versin.
        try:
            acc = hesap_id_bul(token, acc)
            print("hesap: id=%s\n" % _maske(acc, 4))
        except (YetkiEksik, AgHatasi) as e:
            print("!! hesap id cozulemedi — R2 bolumu icin eksik kapsam: %s\n" % e)
            rcler.append(_kosu("R2", lambda: (_ for _ in ()).throw(e)))
        else:
            rcler.append(_kosu("R2", lambda: r2_durum(token, acc)))
    if a.pages or a.hepsi:
        rcler.append(_kosu("PAGES", lambda: pages_durum(a.n)))
    if a.dns or a.hepsi:
        rcler.append(_kosu("DNS", lambda: dns_durum(token)))

    if RC_YETKI in rcler:
        return RC_YETKI
    if RC_AG in rcler:
        return RC_AG
    return RC_OK


if __name__ == "__main__":
    sys.exit(main())
