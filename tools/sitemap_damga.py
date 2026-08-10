#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sitemap <lastmod> DAMGASI — tarihin YASADIGI YER.

SORUN (olculdu 11 Agu 2026): canli sitemap'te 26.696 URL'in HEPSI ayni <lastmod>
(build tarihi) tasiyordu. Google'a "her sey bugun degisti" diyor; olculen tarama
isteklerinin %93'u Refresh, Discovery %7.

KISIT: `urun/` ve `sitemap.xml` git'e GIRMEZ (gitignore) ve build CI'da kosar.
Yani "gecen sefer bu sayfa neydi" bilgisi bir yerde KALICI olmali. Secilen yer:

  1) BIRINCIL KAYNAK = GIT GECMISI (tek DOGRULUK kaynagi). `urunler.json` izlenen
     tek urun kaynagidir; bir urunun icerik hash'inin HANGI commit'te degistigi
     git'ten TURETILEBILIR (deploy.yml `fetch-depth: 0` zaten zorunlu). Yeni yazma
     yolu YOK, CI'ya yazma izni GEREKMEZ (deploy.yml `contents: read`).
  2) HIZLANDIRICI = `sitemap-damgalari.json` defteri (id-hash -> {h, t}), GIT'E
     GIRMEZ, Actions ONBELLEGINDE (actions/cache) tasinir. Defter KANIT DEGIL,
     yalnizca git yurumesinin maliyetini kesen bir onbellektir: dusse bile hicbir
     tarih YANLIS olmaz, yalnizca o kosumda git'ten yeniden turetilir.

  ELENEN SECENEKLER (hepsi OLCUMLE elendi, korlemesine degil):
   · IZLENEN (commit'li) defter -> OLCULDU 11 Agu 2026: 25.251 satirlik defteri
     tasiyan tek commit, pre-push sizinti nobetcisinde 296.511 aday uretti
     (tavan 150.000) ve kapi "OLCULEMEDI" deyip HER itmeyi durdurdu. Katalog
     787 urun/gun buyudugu icin bu sinir ZAMANLA KOTULESIR; anahtari hash'lemek
     (484.129 -> 296.511) yalnizca erteledi. Yani izlenen defter bu deponun KENDI
     guvenlik kapisiyla yapisal olarak bagdasmiyor.
   · CI'nin defteri COMMIT etmesi -> deploy.yml `permissions: contents: read`;
     yazma izni + push dongusu (push -> deploy -> push) yeni bir risk sinifi acar.
   · D1 tablosu/kolonu -> build CI'da D1 jetonu ister (bugun yok), ag bagimliligi
     ekler ve senkron aksarsa TUM tarihler duser.
  Onbellegin "kaliciligi zayif" itirazi burada ZARARSIZDIR cunku dogruluk ona
  BAGLI DEGILDIR: onbellek yoksa yurume SOGUK BASLAR (tavansiz, sure butceli) ve
  tarihler yine git'ten cikar; sure butcesi dolarsa cozulemeyen URL'de lastmod
  BASILMAZ ([[fail-slow-fail-opendir]]: rc kadar SURE de kabul kriteridir).

🔴 ALTIN KURAL — UYDURMA TARIH YAZILMAZ. Bir tarih YALNIZ su iki halde uretilir:
   (a) icerik hash'inin degistigi GECIS gercekten GORULDU (yeni commit'te hash
       mevcut degere esit, bir onceki commit'te DEGIL), ya da
   (b) yurume `urunler.json`'un ILK commit'ine kadar gitti ve hash orada da ayni
       (icerik dosyanin kendisi kadar eski).
   Bunlarin disinda tarih BILINMIYOR sayilir ve o URL'de <lastmod> etiketi HIC
   BASILMAZ. Eksik lastmod, YANLIS lastmod'dan iyidir: yanlis tarih Google'in bu
   sinyale guvenini kalici dusurur (ve tam da bugunku kusurun kendisidir).

KAPSAM: hash yalnizca urunun `urunler.json` KAYDINDAN turer. Sablon (build.py)
degisikligi tarihi OYNATMAZ — bu bilerek boyledir: sablon rotusu 25 bin sayfayi
"bugun degisti" ilan edip kusuru geri getirirdi.
"""

import datetime
import hashlib
import json
import os
import subprocess
import time

SURUM = 1
DEFTER_ADI = "sitemap-damgalari.json"

# SICAK yol (defter dolu): yalnizca defterden sonra degisenler cozulur -> tipik 1-3
# commit. Tavan asilirsa kalan urunler "bilinmiyor" olur (lastmod BASILMAZ).
VARSAYILAN_TAVAN = 300
# SOGUK yol (defter yok/bos): tavan KALKAR ama SURE butcesi baglar. Butce dolunca
# cozulemeyen URL lastmod'suz cikar — kapi ASILMAZ, uydurma da yapilmaz.
VARSAYILAN_SURE_BUTCESI = 240.0


# ----------------------------------------------------------------- hash
def urun_hash(p):
    """Bir urun kaydinin KANONIK icerik hash'i (16 hex).

    json.dumps(sort_keys=True) ile kanoniktir: `urunler.json` girintisi/anahtar
    sirasi degisse bile hash DEGISMEZ ([[urunler-json-bicim-diffi-icerigi-gizler]]
    — girinti 1<->2 kaymasi 565k satirlik diff uretiyordu; damga ondan etkilenmez).
    """
    ham = json.dumps(p, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()[:16]


def id_anahtari(pid):
    """Defter ANAHTARI = urun id'sinin hash'i, id'nin KENDISI DEGIL.

    Gerekce OLCULDU (11 Agu 2026): id'ler tireli sozcuklerden olustugu icin
    25.251 satirlik bir defter pre-push sizinti nobetcisinde 484.129 benzersiz
    aday uretti (tavan 150.000) ve KAPI 'OLCULEMEDI' deyip her itmeyi durdurdu.
    Anahtar hash'lenince satir basina ~3 jeton kalir; ayrica PUBLIC depoda
    duran bu onbellek dosyasi hicbir okunabilir ad TASIMAZ.
    """
    return hashlib.sha256(pid.encode("utf-8")).hexdigest()[:16]


def hashleri_hesapla(urunler, sadece=None):
    """[{...}] -> {id: hash}. `sadece` verilirse yalnizca o id'ler hash'lenir."""
    cikti = {}
    for p in urunler:
        pid = p.get("id")
        if not pid:
            continue
        if sadece is not None and pid not in sadece:
            continue
        cikti[pid] = urun_hash(p)
    return cikti


# ----------------------------------------------------------------- defter
def defter_yukle(yol):
    """Izlenen damga defterini oku. Yoksa/bozuksa BOS defter (fail-open DEGIL:
    bos defter yalnizca 'onbellek yok' demektir; tarihler yine git'ten turer,
    turetilemeyen URL'de lastmod BASILMAZ)."""
    bos = {"surum": SURUM, "taban_sha": None, "damgalar": {}}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (IOError, OSError, ValueError):
        return bos
    if not isinstance(d, dict) or not isinstance(d.get("damgalar"), dict):
        return bos
    if d.get("surum") != SURUM:
        return bos
    return d


def defter_yaz(yol, taban_sha, damgalar):
    """Gecerli JSON, ama URUN BASINA TEK SATIR: git diff'i yalnizca GERCEKTEN
    degisen urunleri gosterir (25 bin kayit girintili yazilsaydi her tazeleme
    devasa bir diff uretir ve gercek degisimi gizlerdi —
    [[urunler-json-bicim-diffi-icerigi-gizler]] ayni sinif)."""
    satirlar = ['{', '"surum": %d,' % SURUM,
                '"taban_sha": %s,' % json.dumps(taban_sha),
                '"damgalar": {']
    anahtarlar = sorted(damgalar)
    for sira, k in enumerate(anahtarlar):
        kayit = damgalar[k]
        satirlar.append('%s: {"h": %s, "t": %s}%s' % (
            json.dumps(k, ensure_ascii=False),
            json.dumps(kayit["h"]), json.dumps(kayit["t"]),
            "," if sira + 1 < len(anahtarlar) else ""))
    satirlar += ['}', '}', '']
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar))


# ----------------------------------------------------------------- git kaynagi
class GitKaynak(object):
    """`urunler.json`'a dokunan commit'leri YENIDEN->ESKIYE verir.

    Test edilebilirlik: `cozumle` bu sinifin ARAYUZUNU alir (commitler/hashler);
    testler sahte bir kaynak enjekte eder, gercek depo GEREKMEZ.
    """

    def __init__(self, kok, dosya="urunler.json"):
        self.kok = kok
        self.dosya = dosya
        self._commit_onbellek = None

    def _git(self, *argv):
        return subprocess.run(("git",) + argv, cwd=self.kok,
                              capture_output=True, text=True)

    def commitler(self):
        """[(sha, 'YYYY-MM-DD')] — yeniden eskiye. Shallow klonda/hatada bos."""
        if self._commit_onbellek is not None:
            return self._commit_onbellek
        r = self._git("log", "--format=%H|%cI", "--", self.dosya)
        kayitlar = []
        if r.returncode == 0:
            for satir in r.stdout.strip().splitlines():
                if "|" not in satir:
                    continue
                sha, iso = satir.split("|", 1)
                kayitlar.append((sha, iso[:10]))
        self._commit_onbellek = kayitlar
        return kayitlar

    def tam_gecmis_mi(self):
        """Klon shallow ise git gecmisi EKSIKTIR -> 'ilk commit' hukmu verilemez."""
        r = self._git("rev-parse", "--is-shallow-repository")
        return r.returncode == 0 and r.stdout.strip() == "false"

    def hashler(self, sha, sadece=None):
        """O commit'teki {id: hash}. Dosya okunamazsa None (bilinmiyor)."""
        r = subprocess.run(("git", "show", sha + ":" + self.dosya),
                           cwd=self.kok, capture_output=True)
        if r.returncode != 0:
            return None
        try:
            urunler = json.loads(r.stdout.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(urunler, list):
            return None
        return hashleri_hesapla(urunler, sadece=sadece)


# ----------------------------------------------------------------- cozumleme
def cozumle(mevcut_hashler, defter, git, tavan=VARSAYILAN_TAVAN,
            sure_butcesi=VARSAYILAN_SURE_BUTCESI, saat=None):
    """{id: hash} + defter + git kaynagi -> ({id: 'YYYY-MM-DD'}, tani).

    Sira:
      1) defterde AYNI hash varsa defterdeki tarih kullanilir. Bu, KARARLILIK
         garantisidir: icerik degismedikce tarih bugune KAYMAZ.
      2) hash defterdekinden farkli ya da id defterde yoksa -> git yurumesi.
      3) yurumede gecis GORULMEZSE (tavan asildi / gecmis eksik / calisma agaci
         commit'ten sapmis) tarih URETILMEZ: o id sonucta YER ALMAZ.
    """
    tarihler = {}
    kalan = set()
    damgalar = defter.get("damgalar") or {}
    for pid, h in mevcut_hashler.items():
        kayit = damgalar.get(id_anahtari(pid))
        if isinstance(kayit, dict) and kayit.get("h") == h and kayit.get("t"):
            tarihler[pid] = kayit["t"]
        else:
            kalan.add(pid)

    tani = {"defterden": len(tarihler), "gitten": 0, "cozulemedi": 0,
            "yurunen_commit": 0, "tavan_asildi": False, "sure_asildi": False,
            "gecmis_tam": True, "sure_sn": 0.0}
    if not kalan:
        return tarihler, tani

    saat = saat or time.time
    baslangic = saat()
    commitler = git.commitler()
    tam = git.tam_gecmis_mi() if hasattr(git, "tam_gecmis_mi") else True
    tani["gecmis_tam"] = bool(tam)
    if not commitler:
        tani["cozulemedi"] = len(kalan)
        return tarihler, tani

    pencere = commitler if tavan is None else commitler[:tavan]
    tani["tavan_asildi"] = tavan is not None and len(commitler) > tavan
    # aday[id] = simdiye kadar mevcut hash'i TASIYAN en eski commit'in tarihi
    aday = {}
    for sira, (sha, tarih) in enumerate(pencere):
        if not kalan:
            break
        # 🔴 SURE butcesi: kapi ASILMAZ (fail-slow = fail-open), cozulemeyen
        # URL lastmod'suz cikar. rc kadar SURE de kabul kriteridir.
        if sure_butcesi is not None and saat() - baslangic > sure_butcesi:
            tani["sure_asildi"] = True
            break
        tani["yurunen_commit"] = sira + 1
        H = git.hashler(sha, sadece=kalan)
        for pid in list(kalan):
            esit = (H or {}).get(pid) == mevcut_hashler[pid]
            if esit:
                aday[pid] = tarih          # hala ayni -> daha eskiye bak
            else:
                if pid in aday:            # (a) GECIS GORULDU
                    tarihler[pid] = aday[pid]
                    tani["gitten"] += 1
                kalan.discard(pid)         # aday yoksa: HEAD'de bile tutmuyor -> bilinmiyor

    # (b) pencere gercekten dosyanin ILK commit'ine kadar gittiyse ve hash hala
    #     ayniysa icerik dosya kadar eskidir; aksi halde BILINMIYOR (uydurma YOK).
    ilk_commite_ulasildi = (not tani["tavan_asildi"]) and (
        not tani["sure_asildi"]) and tam
    for pid in list(kalan):
        if ilk_commite_ulasildi and pid in aday:
            tarihler[pid] = aday[pid]
            tani["gitten"] += 1
            kalan.discard(pid)
    tani["cozulemedi"] = len(kalan)
    tani["sure_sn"] = round(saat() - baslangic, 2)
    return tarihler, tani


# ----------------------------------------------------------------- sitemap yuzeyi
def sitemap_tarihleri(urunler, urun_url, defter_yolu, git_kok,
                      tavan=None, git=None, ana_sayfa_url=None, defteri_tazele=True):
    """build.py yuzeyi: {url: 'YYYY-MM-DD'} dondurur.

    · urun URL'leri  -> git'ten turetilen gercek degisim tarihi
    · ana sayfa "/"  -> urun tarihlerinin EN YENISI (katalog listesi gercekten
                        o gun degisti; turetilmis, uydurma DEGIL)
    · digerleri      -> ANAHTAR YOK => cagiran <lastmod> BASMAZ (icerik/yasal
                        sayfalar ve marka/model sayfalari urun kaydindan
                        turetilemez; yanlis tarih yerine SESSIZLIK).

    TAVAN POLITIKASI: defter (onbellek) DOLU ise sicak yol — yalniz degisenler
    cozulur, tavan `VARSAYILAN_TAVAN`. Defter YOK/BOS ise soguk baslangictir:
    tavan KALKAR (tum gecmis), sure butcesi baglar. Boylece onbellek dusse bile
    tarihler DOGRU kalir, yalnizca o kosum yavaslar.
    """
    if git is None:
        git = GitKaynak(git_kok)
    mevcut = hashleri_hesapla(urunler)
    defter = defter_yukle(defter_yolu)
    if tavan is None:
        tavan = VARSAYILAN_TAVAN if (defter.get("damgalar") or {}) else None
    tarihler, tani = cozumle(mevcut, defter, git, tavan=tavan)
    if defteri_tazele and tarihler:
        # Onbellegi tazele (git'e GIRMEZ; actions/cache tasir). Yazilamazsa SESSIZ
        # gecilir: onbellek dogrulugun kosulu DEGIL, yalnizca hizidir.
        try:
            defter_yaz(defter_yolu, defter.get("taban_sha"),
                       {id_anahtari(pid): {"h": mevcut[pid], "t": t}
                        for pid, t in tarihler.items()})
        except (IOError, OSError):
            pass
    url_tarih = {}
    for pid, t in tarihler.items():
        url_tarih[urun_url(pid)] = t
    if ana_sayfa_url and tarihler:
        url_tarih[ana_sayfa_url] = max(tarihler.values())
    return url_tarih, tani


def bugun():
    return datetime.date.today().isoformat()


def defter_yolu(kok):
    return os.path.join(kok, DEFTER_ADI)
