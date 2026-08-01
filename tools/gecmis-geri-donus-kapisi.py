#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gecmis-geri-donus-kapisi.py — TEMIZLENMIS SIZINTIYI GERI GETIREN PUSH/MERGE KAPISI.

🔴 OLCULEN OLAY (1 Agu 2026, IKI KEZ). `main`in gecmisi tedarikci adindan iki kez
temizlendi (mesaj ekseni). Iki kez de temizlik GERI GELDI. Sebep her seferinde AYNI ve
tek: temizlikten ONCEKI taban uzerine kurulmus bir dal `main`e merge edildi. Merge, o
dalin tasidigi ESKI (sizintili) commit'leri gecmise geri baglar; hicbir kapi kirmizi
yanmaz cunku:
  * `commit-msg` kancasi YALNIZ O AN YAZILAN mesaji gorur — merge ile geri gelen
    commit'lerin mesajlari YENIDEN YAZILMAZ, dolayisiyla kancaya HIC ugramaz;
  * deploy.yml `mesaj-nobeti` kolu itmenin getirdigi mesajlari tarar ama YAYINI
    bloklamaz ve zaten push'tan SONRA kosar;
  * `tools/kisisel-veri-test.py` icerik ekseni CALISMA AGACINI tarar — geri gelen
    commit calisma agacini bozmayabilir (dosyanin GUNCEL hali temiz olabilir),
    sizinti yalniz GECMISTE durur.
Yani "temizlendi" ile "temiz KALIR" arasindaki bosluk OLCULDU ve bu kapi o bosluktur.

BU KAPININ SORDUGU TEK SORU: bu itmenin `origin`e EKLEDIGI commit'lerden herhangi biri,
MESAJINDA ya da GETIRDIGI ICERIKTE yasakli adi tasiyor mu? Tasiyorsa push DURUR.
Commit'in YENI yazilmis ya da ESKI olmasi FARK ETMEZ — olculen olayda geri gelenler
ESKI commit'lerdi ve butun mesele odur.

═══════════════════════════════════════════════════════════════════════════════
IKI KOL
═══════════════════════════════════════════════════════════════════════════════
  (1) `pre-push` KANCASI (`--pre-push`, kurucu: tools/gecmis-geri-donus-hook-kur.py)
      — TEK ONLEYICI KOL. Nesneler heniz uzaga GITMEMISTIR; push durunca sizinti
      public olmaz. FAIL-CLOSED.
  (2) CI KOLU (`--ci`, deploy.yml) — kanca kurulmamis bir makineden ya da
      `--no-verify` ile gelen geri-donusu GORUNUR kilar. Ikinci hat.

🔴 KOL 2 YAYINI BLOKLAMAZ — `tools/commit-mesaji-kapisi.py`daki ayni olculmus karar:
  push'tan sonra kosar, o an commit ZATEN public remote'tadir, yayini durdurmak
  sizintiyi GERI GETIRMEZ; buna karsilik kapi birikmesi bu depoda CI'yi 21 gunde
  0,42 -> 6,55 dk'ya cikardi ve 28 Tem'de 6 saatlik canli 404 penceresi acti
  ([[kapi-birikimi-yayin-gecikmesi]]). Onleme KANCADADIR. `continue-on-error`
  KULLANILMAZ (fail-open yazimi nobetci ihlalidir): rc konusur, job kirmizi yanar.
  Serit olcumu: tools/is-akisi-kapisi.py `_serit_b_joblar`.

═══════════════════════════════════════════════════════════════════════════════
DESEN KAYNAGI — YENI KAYNAK UYDURULMAZ
═══════════════════════════════════════════════════════════════════════════════
Bu kapi KENDI desen listesini TUTMAZ. `tools/commit-mesaji-kapisi.py` modul olarak
yuklenir ve onun IZLENEN ozet artefakti (`tools/sizinti-desen-ozetleri.json`) ile
normalize/aday/ozet mekanizmasi OLDUGU GIBI kullanilir. Boylece:
  * yasakli ad yine hicbir izlenen dosyada DUZ YAZMAZ,
  * iki nobetci ayni seyi olcer (desen kumeleri ayrisamaz),
  * artefakt tazelenince (`--desen-yaz`) bu kapi da kendiliginden tazelenir.
Modul yuklenemezse hukum OLCULEMEDI'dir (rc 2), "desensiz gectim" DEGIL.

═══════════════════════════════════════════════════════════════════════════════
MENZIL — "YENI YAZILANLAR" DEGIL, "ORIGIN'E EKLENENLER"
═══════════════════════════════════════════════════════════════════════════════
Kapinin butun degeri buradadir. Taranan kume, itilen her ref icin
`<local_sha>` MINUS `<remote_sha>` = bu itmenin o ref'e EKLEDIGI commit'lerdir.
Merge ile geri gelen ESKI commit'ler bu kumenin ICINDEDIR (uzakta yoklar), dolayisiyla
taranirlar — olculen ariza tam olarak boyle yakalanir.
  * `remote_sha` sifirsa (YENI ref): menzil `<local_sha> --not --remotes=<uzak>`
    — tum gecmisi bastan taramamak icin, ama uzakta HIC olmayan her commit dahil.
  * `local_sha` sifirsa (ref SILINIYOR): taranacak sey YOKTUR.
  * `git rev-list` patlarsa hukum OLCULEMEDI'dir (rc 2).
TUM itilen ref'ler yargilanir, yalniz `main` DEGIL: depo PUBLIC, sizintili bir commit
hangi dala giderse gitsin anonim cekilebilir; ayrica bugunku dal yarinki merge'un
tabanidir (olculen arizanin ta kendisi).

═══════════════════════════════════════════════════════════════════════════════
ICERIK EKSENI — EKLENEN SATIRLAR (blob'un TAMAMI DEGIL) + OLCULMUS BUTCE
═══════════════════════════════════════════════════════════════════════════════
🔴 NEDEN TAM BLOB DEGIL — OLCULDU: ozet eslesmesi aday BASINA bir PBKDF2 cagrisidir
(bu makinede 0,405 ms). Tam blob taransaydi TEK BASINA `urunler.json` 1.033.813
benzersiz aday = 419 s yerel / ~1500 s CI ederdi. Boyle bir kapi ilk toplu iste devre
disi birakilir ([[kapi-birikimi-yayin-gecikmesi]]) — yani "kapsamli" yazim, kapiyi
OLDUREN yazimdir. EKLENEN SATIR ekseni ayni sizintiyi yakalar cunku sizinti gecmise bir
commit'in EKLEDIGI satirlarla girer; menzildeki her commit ayri ayri tarandigi icin
merge ile geri gelen commit kendi eklemeleriyle GORULUR. Olculen maliyet: tipik 5
commit'lik push 6,2 s; son 20 commit birlikte 21,4 s.

🔴 MERGE COMMIT'LERI: `-c` (birlesik diff) ile taranir — boylece hicbir ebeveynde
OLMAYAN, yalniz cakisma cozumunde uretilmis metin ("evil merge") de gorulur. Tek
ebeveynli commit'ler duz patch ile, KOK commit `--root` ile taranir (aksi halde ilk
commit'in tum icerigi HIC taranmazdi).

🔴 YENIDEN ADLANDIRMA TESPITI (`-M`) BILEREK KAPALI: acik olsaydi sizintili bir dosyayi
yeniden adlandiran commit "eklenen satir yok" gorunur, icerik taramadan gecerdi.
Kapali oldugunda ayni commit dosyanin TAMAMINI eklenmis sayar — pahali ama KOR DEGIL.

🔴 ADAY BUTCESI (fail-closed): benzersiz aday sayisi ADAY_BUTCESI'ni asarsa hukum
SIZINTI degil OLCULEMEDI'dir (rc 2) ve push DURUR. "Cok buyuk oldugu icin taramadim"
YESIL DEGILDIR — bu deponun tekrar tekrar olctugu sessiz delik sinifi budur. Butce
1.200 commit uzerinde olculerek secildi: `urunler.json`in TAM yeniden yazildigi 2
commit disinda en pahali TEK commit 57.339 aday, en pahali 20-commit'lik push 52.891
adaydir; butce onun ~2,6 kati. Cikis yolu git'in kendi `--no-verify` bayragidir
(gurultulu ve kayitli), kapiyi sessizce gevsetmek DEGIL.

🔴 TESHIS SIZDIRMAZ: eslesen METIN hicbir kolda basilmaz — commit + dosya + desen no
+ uzunluk basilir. Aksi halde kapi sizintiyi PUBLIC Actions gunlugune kendi eliyle
yazardi.

Kullanim:
    python3 tools/gecmis-geri-donus-kapisi.py --pre-push [--uzak origin]  # kanca kolu
    python3 tools/gecmis-geri-donus-kapisi.py --ci                        # CI kolu
    python3 tools/gecmis-geri-donus-kapisi.py --menzil <A>..<B>           # elle
    python3 tools/gecmis-geri-donus-kapisi.py --kendini-test              # kabul bataryasi
Cikis kodu: 0 temiz · 1 SIZINTI (push DURUR) · 2 OLCULEMEDI (fail-closed, push DURUR).
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_YOLU = os.path.join(TOOLS, "commit-mesaji-kapisi.py")

RC_TEMIZ = 0
RC_SIZINTI = 1
RC_OLCULEMEDI = 2

SIFIR_SHA = "0" * 40

# Olcum: 1.200 commit tarandi. urunler.json'in TAM yeniden yazildigi 2 commit disinda
# en pahali TEK commit 57.339 aday; en pahali 20-commit'lik push 52.891 aday. Butce
# bunun ~2,6 kati -> normal is GECER, patolojik yeniden-yazim OLCULEMEDI verir.
ADAY_BUTCESI = 150000

_KAPI = None


def kapi_modulu():
    """(modul, hata) — kardes nobetciyi modul olarak yukler. FAIL-CLOSED."""
    global _KAPI
    if _KAPI is not None:
        return _KAPI, None
    if not os.path.isfile(KAPI_YOLU):
        return None, ("desen mekanizmasi YOK: %s — bu kapi kendi desen listesini "
                      "TUTMAZ, kardes nobetciyi kullanir." % KAPI_YOLU)
    try:
        spec = importlib.util.spec_from_file_location(
            "pruvo_commit_mesaji_kapisi", KAPI_YOLU)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
    except Exception as e:                                    # noqa: BLE001
        return None, "desen mekanizmasi YUKLENEMEDI (%s): %s" % (KAPI_YOLU, e)
    for ad in ("ozet_kaydi_yukle", "adaylar", "_ozetle", "mesaj_kusurlari",
               "mesaj_govdesi"):
        if not hasattr(modul, ad):
            return None, ("desen mekanizmasi EKSIK: %s bulunamadi -> olcemem "
                          "(fail-closed)" % ad)
    _KAPI = modul
    return _KAPI, None


# ---------------------------------------------------------------------------
# GIT
# ---------------------------------------------------------------------------
def _git(args, kok=None):
    return subprocess.run(["git", "-C", kok or ROOT] + args,
                          capture_output=True, text=True, errors="replace")


def push_satirlari(metin):
    """pre-push stdin -> [(local_ref, local_sha, remote_ref, remote_sha), ...]

    Bicimi bozuk satir SESSIZCE ATILMAZ: cagiran hata listesini de alir."""
    kayitlar, hatalar = [], []
    for ham in (metin or "").splitlines():
        satir = ham.strip()
        if not satir:
            continue
        parca = satir.split()
        if len(parca) != 4:
            hatalar.append("pre-push satiri COZULEMEDI (4 alan bekleniyor): %r"
                           % satir[:120])
            continue
        kayitlar.append(tuple(parca))
    return kayitlar, hatalar


def eklenen_commitler(local_sha, remote_sha, kok=None, uzak="origin"):
    """(commit_listesi, hata) — bu itmenin o ref'e EKLEDIGI commit'ler.

    ESKI commit'ler de buradadir: olcut "yeni yazilmis mi" DEGIL, "uzakta var mi".
    """
    if local_sha == SIFIR_SHA:
        return [], None                      # ref siliniyor -> taranacak sey yok
    args = ["rev-list", local_sha]
    if remote_sha and remote_sha != SIFIR_SHA:
        p = _git(["cat-file", "-e", remote_sha + "^{commit}"], kok=kok)
        if p.returncode == 0:
            args += ["--not", remote_sha]
        else:
            args += ["--not", "--remotes=" + uzak]
    else:
        args += ["--not", "--remotes=" + uzak]
    p = _git(args, kok=kok)
    if p.returncode != 0:
        return None, ("git rev-list rc=%d: %s" % (p.returncode,
                                                  (p.stderr or "").strip()[:200]))
    return p.stdout.split(), None


def _ebeveyn_sayisi(sha, kok=None):
    p = _git(["rev-list", "--parents", "-n", "1", sha], kok=kok)
    if p.returncode != 0:
        return None
    return max(0, len(p.stdout.split()) - 1)


def eklenen_metin(sha, kok=None):
    """(metin, hata) — commit'in EKLEDIGI satirlar (dosya yolu basliklariyla birlikte).

    Merge -> `-c` birlesik diff (evil merge gorunur). Kok commit -> `--root`.
    `-M` KAPALI (gerekce: modul basligi).
    """
    n = _ebeveyn_sayisi(sha, kok=kok)
    if n is None:
        return None, "ebeveyn sayisi okunamadi: %s" % sha[:12]
    args = ["diff-tree", "--no-commit-id", "-p", "-r", "--no-color", "--no-renames",
            "--root"]
    if n > 1:
        args.append("-c")
    args.append(sha)
    p = _git(args, kok=kok)
    if p.returncode != 0:
        return None, ("git diff-tree rc=%d (%s): %s"
                      % (p.returncode, sha[:12], (p.stderr or "").strip()[:200]))
    onek = max(1, n) if n > 1 else 1
    parcalar, yol = [], "?"
    for satir in p.stdout.splitlines():
        if satir.startswith("diff --git ") or satir.startswith("diff --combined "):
            yol = satir.rsplit(" b/", 1)[-1] if " b/" in satir else satir.split()[-1]
            continue
        if satir.startswith("+++") or satir.startswith("---") or satir.startswith("@@"):
            continue
        if n > 1:
            bas = satir[:onek]
            if "+" in bas:
                parcalar.append(yol + " " + satir[onek:])
        elif satir.startswith("+"):
            parcalar.append(yol + " " + satir[1:])
    return "\n".join(parcalar), None


# ---------------------------------------------------------------------------
# TARAMA
# ---------------------------------------------------------------------------
class Bulgu(object):
    def __init__(self, sha, eksen, ayrinti):
        self.sha = sha
        self.eksen = eksen              # "mesaj" | "icerik"
        self.ayrinti = ayrinti

    def __str__(self):
        return "%s  [%s]  %s" % (self.sha[:12], self.eksen, self.ayrinti)


def commitleri_tara(shalar, kayit, modul, kok=None, maskeli=True,
                    butce=ADAY_BUTCESI, kirp=False):
    """(bulgular, olcum, hata) — mesaj + icerik ekseni.

    Adaylar TUM commit'ler boyunca TEK kumede toplanip BIR KEZ ozetlenir (commit'ler
    buyuk olcude ayni jetonlari paylasir).

    MESAJ ekseni HER ZAMAN TUM commit'leri kapsar (mesajlar ucuzdur). Butce YALNIZ
    ICERIK eksenini baglar.

    `kirp=False` (ONLEYICI kollar): butce asilirsa hata doner -> rc 2, push DURUR.
    `kirp=True`  (GORUNURLUK kolu): butce dolunca TARAMA DURUR, kapsanan/atlanan
        commit sayisi RAPORLANIR ve hukum kapsanan kume uzerinden verilir.
        🔴 NEDEN CI'da KIRPMA MESRU: (a) CI push'TAN SONRA kosar, hicbir seyi
        ONLEMEZ — oradaki rc 2 tek basina KIRMIZI GURULTUdur ve bu depoda kapi
        birikmesinin bedeli olculmustur; (b) her commit, kendisini GETIREN push'un
        KENDI CI kosumunda zaten taranir, yani zaman icinde kapsam TAMDIR;
        (c) asil olcumu ONLEYICI kol (pre-push) TAM menzil uzerinde yapar.
        Kirpma SESSIZ DEGILDIR: kac commit tarandi / kac tanesi atlandi basilir.
        Cagiran, kirpma modunda commit'leri YENIDEN ESKIYE siralı vermelidir.
    """
    bulgular = []
    olcum = {"commit": len(shalar), "aday": 0, "ozet_ms": 0.0, "eklenen_bayt": 0,
             "icerik_kapsanan": 0, "icerik_atlanan": 0}

    # --- MESAJ EKSENI ---
    for sha in shalar:
        p = _git(["log", "-1", "--format=%B", sha], kok=kok)
        if p.returncode != 0:
            return None, olcum, ("commit mesaji okunamadi (%s): %s"
                                 % (sha[:12], (p.stderr or "").strip()[:160]))
        for k in modul.mesaj_kusurlari(modul.mesaj_govdesi(p.stdout), kayit,
                                       maskeli=maskeli):
            bulgular.append(Bulgu(sha, "mesaj", k))

    # --- ICERIK EKSENI (eklenen satirlar) ---
    uzunluklar = sorted({n for n, _ in kayit["desenler"]})
    aday_commit = {}
    for sira, sha in enumerate(shalar):
        metin, hata = eklenen_metin(sha, kok=kok)
        if metin is None:
            return None, olcum, hata
        bu_commit = set()
        for n in uzunluklar:
            for aday in modul.adaylar(metin, n):
                bu_commit.add((n, aday))
        yeni_sayi = sum(1 for a in bu_commit if a not in aday_commit)
        if len(aday_commit) + yeni_sayi > butce:
            if not kirp:
                return None, olcum, (
                    "ADAY BUTCESI ASILDI: %d > %d benzersiz aday. Hukum OLCULEMEDI'dir "
                    "(fail-closed) — 'cok buyuk oldugu icin taramadim' YESIL DEGILDIR. "
                    "COZUM: itmeyi daha kucuk parcalara bol, ya da bilerek atlamak icin "
                    "`git push --no-verify` (gurultulu ve kayitli)."
                    % (len(aday_commit) + yeni_sayi, butce))
            olcum["icerik_atlanan"] = len(shalar) - sira
            break
        olcum["eklenen_bayt"] += len(metin)
        for anahtar in bu_commit:
            aday_commit.setdefault(anahtar, set()).add(sha)
        olcum["icerik_kapsanan"] += 1
    olcum["aday"] = len(aday_commit)

    t0 = time.perf_counter()
    ozet_commit = {}
    for (n, aday), shalar_kume in aday_commit.items():
        anahtar = (n, modul._ozetle(aday, kayit["tuz"], kayit["dongu"]))
        ozet_commit.setdefault(anahtar, set()).update(shalar_kume)
    olcum["ozet_ms"] = (time.perf_counter() - t0) * 1000.0

    for i, (n, ozet) in enumerate(kayit["desenler"]):
        for sha in sorted(ozet_commit.get((n, ozet), ())):
            bulgular.append(Bulgu(
                sha, "icerik",
                "bu commit'in EKLEDIGI satirlarda gizli desen #%d (uzunluk %d) DUZ "
                "METIN gecti. (Eslesen metin BILEREK yazilmiyor.)" % (i, n)))
    return bulgular, olcum, None


def _kayit_ya_da_hata(modul, ozet_yolu=None):
    kayit, hata = modul.ozet_kaydi_yukle(ozet_yolu)
    return kayit, hata


def _rapor(bulgular, olcum, baslik, kanca_kolu):
    print("%s: %d commit · %d benzersiz aday · ozetleme %.0f ms · eklenen %.1f KB"
          % (baslik, olcum["commit"], olcum["aday"], olcum["ozet_ms"],
             olcum["eklenen_bayt"] / 1024.0))
    print("  eksen kapsami: MESAJ %d/%d commit · ICERIK %d/%d commit"
          % (olcum["commit"], olcum["commit"],
             olcum.get("icerik_kapsanan", olcum["commit"]), olcum["commit"]))
    if olcum.get("icerik_atlanan"):
        # 🔴 SESSIZ DEGIL: kirpma HER ZAMAN sayiyla basilir.
        print("  ⚠️ ICERIK EKSENI KIRPILDI: aday butcesi (%d) doldu -> EN YENI %d "
              "commit tarandi, %d commit ICERIK ekseninde TARANMADI (mesaj ekseni "
              "hepsini kapsadi). Bu kol GORUNURLUKTUR; asil olcumu pre-push kancasi "
              "TAM menzil uzerinde yapar ve her commit kendisini getiren push'un CI "
              "kosumunda ayrica taranir."
              % (ADAY_BUTCESI, olcum.get("icerik_kapsanan", 0),
                 olcum["icerik_atlanan"]))
    if not bulgular:
        print("temiz: 0 bulgu.")
        return RC_TEMIZ
    print("", file=sys.stderr)
    if kanca_kolu:
        print("PUSH DURDURULDU — bu itme, temizlenmis sizintiyi GERI GETIRIYOR:",
              file=sys.stderr)
    else:
        print("GERI-DONUS: bu itme temizlenmis sizintiyi geri getirdi:", file=sys.stderr)
    for b in bulgular:
        print("  * " + str(b), file=sys.stderr)
    print("", file=sys.stderr)
    if kanca_kolu:
        print("  SEBEP (bu depoda IKI KEZ olculdu): temizlikten ONCEKI taban uzerine "
              "kurulmus bir dal main'e MERGE edildiginde, o dalin tasidigi ESKI "
              "sizintili commit'ler gecmise geri baglanir.", file=sys.stderr)
        print("  COZUM: dali merge ETME. Once `git fetch origin` + dalini TAZE "
              "origin/main uzerine `rebase` et (ya da islerini taze main uzerine "
              "`cherry-pick` et), sonra tekrar dene.", file=sys.stderr)
        print("  Bilerek atlamak: `git push --no-verify` (gurultulu ve kayitli).",
              file=sys.stderr)
    return RC_SIZINTI


# ---------------------------------------------------------------------------
# KOLLAR
# ---------------------------------------------------------------------------
def kol_pre_push(girdi=None, kok=None, uzak="origin", ozet_yolu=None,
                 butce=ADAY_BUTCESI):
    modul, hata = kapi_modulu()
    if modul is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    kayit, hata = _kayit_ya_da_hata(modul, ozet_yolu)
    if kayit is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    ham = sys.stdin.read() if girdi is None else girdi
    kayitlar, bicim_hatalari = push_satirlari(ham)
    if bicim_hatalari:
        for h in bicim_hatalari:
            print("OLCULEMEDI (fail-closed KIRMIZI): %s" % h, file=sys.stderr)
        return RC_OLCULEMEDI
    if not kayitlar:
        # Git bazi hallerde BOS stdin verir (or. hicbir sey itilmiyor). Taranacak
        # sey yoktur; bu "olcemedim" DEGIL, "olculecek sey yok"tur.
        print("itilen ref YOK — taranacak commit yok.")
        return RC_TEMIZ
    tum_shalar, ref_ozet = [], []
    for local_ref, local_sha, remote_ref, remote_sha in kayitlar:
        shalar, hata = eklenen_commitler(local_sha, remote_sha, kok=kok, uzak=uzak)
        if shalar is None:
            print("OLCULEMEDI (fail-closed KIRMIZI): %s (%s)" % (hata, remote_ref),
                  file=sys.stderr)
            return RC_OLCULEMEDI
        ref_ozet.append("%s +%d" % (remote_ref, len(shalar)))
        tum_shalar.extend(shalar)
    tum_shalar = sorted(set(tum_shalar))
    print("itilen ref: %s" % ", ".join(ref_ozet))
    # 🔴 `kirp` VERILMEZ (=False): bu ONLEYICI koldur. Butce asilirsa hukum
    # OLCULEMEDI'dir ve PUSH DURUR — kirpma yalniz gorunurluk kollarinda mesrudur.
    bulgular, olcum, hata = commitleri_tara(tum_shalar, kayit, modul, kok=kok,
                                            maskeli=False, butce=butce)
    if bulgular is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    return _rapor(bulgular, olcum, "geri-donus taramasi", kanca_kolu=True)


def kol_ci(kok=None, ozet_yolu=None, ortam=None, yuk=None, butce=ADAY_BUTCESI):
    modul, hata = kapi_modulu()
    if modul is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    kayit, hata = _kayit_ya_da_hata(modul, ozet_yolu)
    if kayit is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    ortam = os.environ if ortam is None else ortam
    yuk = modul._olay_yuku() if yuk is None else yuk
    once = (yuk or {}).get("before") or ortam.get("GITHUB_EVENT_BEFORE") or ""
    sonra = (yuk or {}).get("after") or ortam.get("GITHUB_SHA") or ""
    if not sonra:
        print("OLCULEMEDI (fail-closed KIRMIZI): itmenin ucu (GITHUB_SHA/after) "
              "COZULEMEDI.", file=sys.stderr)
        return RC_OLCULEMEDI
    if once and once != SIFIR_SHA and _git(["cat-file", "-e", once + "^{commit}"],
                                           kok=kok).returncode == 0:
        p = _git(["rev-list", "%s..%s" % (once, sonra)], kok=kok)
        kaynak = "git menzili %s..%s" % (once[:8], sonra[:8])
    else:
        p = _git(["rev-list", "-n", "50", sonra], kok=kok)
        kaynak = ("taban COZULEMEDI -> son 50 commit (sig checkout ya da ilk itme); "
                  "kapsam DAR olabilir")
    if p.returncode != 0:
        print("OLCULEMEDI (fail-closed KIRMIZI): git rev-list rc=%d: %s"
              % (p.returncode, (p.stderr or "").strip()[:200]), file=sys.stderr)
        return RC_OLCULEMEDI
    # rev-list ciktisi YENIDEN ESKIYE siralidir -> kirpma en YENI commit'leri korur.
    shalar = p.stdout.split()
    print("kaynak: %s" % kaynak)
    bulgular, olcum, hata = commitleri_tara(shalar, kayit, modul, kok=kok,
                                            maskeli=True, kirp=True, butce=butce)
    if bulgular is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    rc = _rapor(bulgular, olcum, "geri-donus taramasi (CI)", kanca_kolu=False)
    if rc == RC_SIZINTI:
        print("Bu job YAYINI DURDURMAZ (tamir degeri yok: commit zaten public). "
              "ONLEME kolu pre-push kancasidir: "
              "python3 tools/gecmis-geri-donus-hook-kur.py", file=sys.stderr)
    return rc


def kol_menzil(menzil, kok=None, ozet_yolu=None, maskeli=True):
    modul, hata = kapi_modulu()
    if modul is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    kayit, hata = _kayit_ya_da_hata(modul, ozet_yolu)
    if kayit is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    p = _git(["rev-list", menzil], kok=kok)
    if p.returncode != 0:
        print("OLCULEMEDI (fail-closed KIRMIZI): git rev-list %s rc=%d: %s"
              % (menzil, p.returncode, (p.stderr or "").strip()[:200]), file=sys.stderr)
        return RC_OLCULEMEDI
    bulgular, olcum, hata = commitleri_tara(p.stdout.split(), kayit, modul, kok=kok,
                                            maskeli=maskeli)
    if bulgular is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    return _rapor(bulgular, olcum, "geri-donus taramasi (%s)" % menzil,
                  kanca_kolu=False)


# ===========================================================================
# KABUL BATARYASI — SENTETIK DEPOLARDA GERCEK GIT
# ===========================================================================
# 🔴 FIKSTURLERDE GERCEK YASAKLI AD YOKTUR — uydurma adlar kullanilir ve gercek
# uretim yoluyla (`--desen-yaz`) gecici bir ozet artefaktina cevrilir. Testin olctugu
# sey MEKANIZMADIR, hangi adin yasakli oldugu DEGIL.
import json as _json                                                # noqa: E402
import shutil as _shutil                                            # noqa: E402
import tempfile as _tempfile                                        # noqa: E402

_UYDURMA = ("Zorbacix", "HayaliVitrin")


def _kos(args, kok):
    return subprocess.run(args, cwd=kok, capture_output=True, text=True,
                          errors="replace")


def _depo_kur(kok):
    _kos(["git", "init", "-q", "-b", "main", "."], kok)
    _kos(["git", "config", "user.email", "test@example.com"], kok)
    _kos(["git", "config", "user.name", "Test"], kok)
    _kos(["git", "config", "commit.gpgsign", "false"], kok)


def _yaz(kok, ad, icerik):
    yol = os.path.join(kok, ad)
    os.makedirs(os.path.dirname(yol), exist_ok=True) if os.path.dirname(yol) else None
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)


def _commit(kok, mesaj):
    _kos(["git", "add", "-A"], kok)
    p = _kos(["git", "commit", "-q", "--no-verify", "-m", mesaj], kok)
    return _kos(["git", "rev-parse", "HEAD"], kok).stdout.strip(), p


def _gecici_artefakt(tmp, adlar=_UYDURMA):
    """Uydurma adlardan GERCEK uretim yoluyla ozet artefakti uretir."""
    modul, hata = kapi_modulu()
    if modul is None:
        raise RuntimeError(hata)
    duz = os.path.join(tmp, "duz-desenler.txt")
    with open(duz, "w", encoding="utf-8") as f:
        f.write("\n".join(adlar) + "\n")
    hedef = os.path.join(tmp, "ozet.json")
    sayi, hata = modul.desen_yaz(kaynak=duz, hedef=hedef,
                                 dongu=modul.ASGARI_DONGU)
    if sayi is None:
        raise RuntimeError(hata)
    return hedef


def _push_girdisi(local_sha, remote_sha, ref="refs/heads/main"):
    return "%s %s %s %s\n" % (ref, local_sha, ref, remote_sha)


def kendini_test():
    """Kabul bataryasi. Cikis 0 = tum vakalar gecti."""
    hatalar = []
    vaka = [0]

    def kontrol(ad, kosul, ayrinti=""):
        vaka[0] += 1
        if kosul:
            print("  ok   %s" % ad)
        else:
            print("  FAIL %s %s" % (ad, ayrinti))
            hatalar.append(ad)

    tmp = _tempfile.mkdtemp(prefix="pruvo-geri-donus-")
    try:
        artefakt = _gecici_artefakt(tmp)

        # ---------------------------------------------------------------
        # VAKA 1 — ESKI SIZINTILI COMMIT'I GERI GETIREN MERGE ENGELLENIR
        # ---------------------------------------------------------------
        print("\nVAKA 1 — eski sizintili commit'i geri getiren MERGE")
        depo = os.path.join(tmp, "v1")
        os.makedirs(depo)
        _depo_kur(depo)
        _yaz(depo, "a.txt", "temiz taban\n")
        taban, _ = _commit(depo, "taban commit")
        # ESKI dal: mesajinda VE iceriginde uydurma yasakli ad
        _kos(["git", "checkout", "-q", "-b", "eski-taban"], depo)
        _yaz(depo, "b.txt", "tedarikci %s ile anlasma\n" % _UYDURMA[0])
        sizintili, _ = _commit(depo, "%s partisi: 12 urun" % _UYDURMA[0])
        _kos(["git", "checkout", "-q", "main"], depo)
        _yaz(depo, "c.txt", "temiz is\n")
        _commit(depo, "temiz is")
        # "uzak"in bildigi son hal = main'in su anki ucu (merge'den ONCE)
        uzak_sha = _kos(["git", "rev-parse", "HEAD"], depo).stdout.strip()
        _kos(["git", "merge", "-q", "--no-ff", "-m", "eski dali birlestir",
              "eski-taban"], depo)
        yerel_sha = _kos(["git", "rev-parse", "HEAD"], depo).stdout.strip()

        eklenen, hata = eklenen_commitler(yerel_sha, uzak_sha, kok=depo)
        kontrol("1a menzil eski sizintili commit'i ICERIYOR",
                eklenen is not None and sizintili in (eklenen or []),
                "(eklenen=%s)" % (len(eklenen or [])))

        rc = kol_pre_push(girdi=_push_girdisi(yerel_sha, uzak_sha), kok=depo,
                          ozet_yolu=artefakt)
        kontrol("1b MERGE PUSH'U ENGELLENDI (rc=1)", rc == RC_SIZINTI, "(rc=%d)" % rc)

        modul, _ = kapi_modulu()
        kayit, _ = modul.ozet_kaydi_yukle(artefakt)
        bulgular, olcum, _ = commitleri_tara(eklenen, kayit, modul, kok=depo)
        bulgular_tam = list(bulgular or [])
        eksenler = {b.eksen for b in (bulgular or [])}
        kontrol("1c IKI EKSEN de vurdu (mesaj + icerik)",
                eksenler == {"mesaj", "icerik"}, "(eksenler=%s)" % sorted(eksenler))
        kontrol("1d teshis EslESEN METNI basmiyor",
                all(_UYDURMA[0].lower() not in str(b).lower()
                    for b in (bulgular or [])))

        # ---------------------------------------------------------------
        # VAKA 2 — TEMIZ PUSH GECER
        # ---------------------------------------------------------------
        print("\nVAKA 2 — temiz push")
        depo2 = os.path.join(tmp, "v2")
        os.makedirs(depo2)
        _depo_kur(depo2)
        _yaz(depo2, "a.txt", "temiz taban\n")
        _commit(depo2, "taban commit")
        uzak2 = _kos(["git", "rev-parse", "HEAD"], depo2).stdout.strip()
        _yaz(depo2, "d.txt", "framework ve kool bir arac; tedarikci partisi 3 urun\n")
        _commit(depo2, "tedarikci partisi 3. dilim: notr mesaj")
        yerel2 = _kos(["git", "rev-parse", "HEAD"], depo2).stdout.strip()
        rc = kol_pre_push(girdi=_push_girdisi(yerel2, uzak2), kok=depo2,
                          ozet_yolu=artefakt)
        kontrol("2a temiz push GECTI (rc=0)", rc == RC_TEMIZ, "(rc=%d)" % rc)

        # yakin-kacirma (near-miss) yesil kalmali
        _yaz(depo2, "e.txt", "zorba bir cix ve hayali bir vitrin tasarimi\n")
        _commit(depo2, "yakin-kacirma metni")
        yerel2b = _kos(["git", "rev-parse", "HEAD"], depo2).stdout.strip()
        rc = kol_pre_push(girdi=_push_girdisi(yerel2b, uzak2), kok=depo2,
                          ozet_yolu=artefakt)
        kontrol("2b yakin-kacirma YANLIS-POZITIF uretmedi", rc == RC_TEMIZ,
                "(rc=%d)" % rc)

        # ---------------------------------------------------------------
        # VAKA 3 — OZET ARTEFAKTI YOKSA FAIL-CLOSED
        # ---------------------------------------------------------------
        print("\nVAKA 3 — ozet artefakti yok / bozuk (FAIL-CLOSED)")
        yok = os.path.join(tmp, "olmayan-artefakt.json")
        rc = kol_pre_push(girdi=_push_girdisi(yerel_sha, uzak_sha), kok=depo,
                          ozet_yolu=yok)
        kontrol("3a artefakt YOK -> rc=2 (OLCULEMEDI, push DURUR)",
                rc == RC_OLCULEMEDI, "(rc=%d)" % rc)
        bos = os.path.join(tmp, "bos-artefakt.json")
        with open(bos, "w", encoding="utf-8") as f:
            _json.dump({"surum": 1, "algo": "pbkdf2_sha256", "dongu": 5000,
                        "tuz": "00112233445566778899aabbccddeeff", "desenler": []}, f)
        rc = kol_pre_push(girdi=_push_girdisi(yerel_sha, uzak_sha), kok=depo,
                          ozet_yolu=bos)
        kontrol("3b BOS desen listesi -> rc=2 (fail-closed)", rc == RC_OLCULEMEDI,
                "(rc=%d)" % rc)
        ucuz = os.path.join(tmp, "ucuz-artefakt.json")
        with open(ucuz, "w", encoding="utf-8") as f:
            _json.dump({"surum": 1, "algo": "pbkdf2_sha256", "dongu": 1,
                        "tuz": "00112233445566778899aabbccddeeff",
                        "desenler": [{"n": 8, "ozet": "ab" * 32}]}, f)
        rc = kol_pre_push(girdi=_push_girdisi(yerel_sha, uzak_sha), kok=depo,
                          ozet_yolu=ucuz)
        kontrol("3c UCUZLATILMIS dongu -> rc=2 (kapi gevsetilemez)",
                rc == RC_OLCULEMEDI, "(rc=%d)" % rc)
        bozuk_girdi = "bu satir dort alan degil\n"
        rc = kol_pre_push(girdi=bozuk_girdi, kok=depo, ozet_yolu=artefakt)
        kontrol("3d BOZUK pre-push satiri -> rc=2 (sessizce atlanmaz)",
                rc == RC_OLCULEMEDI, "(rc=%d)" % rc)

        # ---------------------------------------------------------------
        # VAKA 4 — KANCA KALDIRILINCA HICBIR SEY URETMEZ
        # ---------------------------------------------------------------
        print("\nVAKA 4 — kanca kurulumu / kaldirilmasi")
        kur_yolu = os.path.join(TOOLS, "gecmis-geri-donus-hook-kur.py")
        if not os.path.isfile(kur_yolu):
            kontrol("4a kurucu betik MEVCUT", False, "(%s YOK)" % kur_yolu)
        else:
            depo4 = os.path.join(tmp, "v4")
            os.makedirs(depo4)
            _depo_kur(depo4)
            _yaz(depo4, "a.txt", "x\n")
            _commit(depo4, "taban")
            p = _kos(["python3", kur_yolu, "--repo", depo4], depo4)
            kanca = os.path.join(depo4, ".git", "hooks", "pre-push")
            kontrol("4a kurulum kancayi YAZDI + calistirilabilir",
                    p.returncode == 0 and os.path.isfile(kanca)
                    and os.access(kanca, os.X_OK), "(rc=%d)" % p.returncode)
            p = _kos(["python3", kur_yolu, "--repo", depo4, "--dogrula"], depo4)
            kontrol("4b --dogrula KURULU diyor", p.returncode == 0)
            p2 = _kos(["python3", kur_yolu, "--repo", depo4], depo4)
            with open(kanca, encoding="utf-8") as f:
                bir_kez = f.read()
            kontrol("4c kurulum IDEMPOTENT",
                    p2.returncode == 0 and bir_kez.count("--pre-push") == 1,
                    "(sayi=%d)" % bir_kez.count("--pre-push"))
            p = _kos(["python3", kur_yolu, "--repo", depo4, "--kaldir"], depo4)
            with open(kanca, encoding="utf-8") as f:
                kaldirilmis = f.read()
            kontrol("4d KALDIRINCA hicbir cagri KALMAZ",
                    p.returncode == 0
                    and "gecmis-geri-donus-kapisi.py" not in kaldirilmis,
                    "(kalinti var)")
            p = _kos(["python3", kur_yolu, "--repo", depo4, "--dogrula"], depo4)
            kontrol("4e kaldirilinca --dogrula KIRMIZI", p.returncode != 0)

        # ---------------------------------------------------------------
        # VAKA 5 — YENI DAL (remote_sha sifir) ve REF SILME
        # ---------------------------------------------------------------
        print("\nVAKA 5 — yeni dal / ref silme")
        shalar, hata = eklenen_commitler(SIFIR_SHA, SIFIR_SHA, kok=depo)
        kontrol("5a ref SILINIYOR -> taranacak commit yok",
                shalar == [] and hata is None)
        shalar, hata = eklenen_commitler(yerel_sha, SIFIR_SHA, kok=depo)
        kontrol("5b YENI dal -> uzakta olmayan TUM commit'ler taranir",
                shalar is not None and sizintili in (shalar or []),
                "(sayi=%s)" % (len(shalar or [])))

        # ---------------------------------------------------------------
        # VAKA 6 — ADAY BUTCESI ASILIRSA OLCULEMEDI (fail-closed)
        # ---------------------------------------------------------------
        print("\nVAKA 6 — aday butcesi")
        bulgular, olcum, hata = commitleri_tara(eklenen, kayit, modul, kok=depo,
                                                butce=1)
        kontrol("6a butce asilinca bulgular None + hata var",
                bulgular is None and hata is not None)
        kontrol("6b butce hatasi OLCULEMEDI diyor",
                bool(hata) and "OLCULEMEDI" in (hata or ""))
        # 🔴 KIRPMA KOLU (yalniz GORUNURLUK kollari): butce dolunca hata DEGIL,
        # kapsanan/atlanan SAYISI. OLCULEN OLAY (1 Agu 2026): force-push'tan sonra
        # CI'da `before` nesnesi ORTADAN KALKTI, kol "son 50 commit" tabanina dustu
        # ve 157.276 aday ile butceyi asip rc 2 verdi — hicbir sizinti YOKKEN.
        # CI push'tan SONRA kosar, hicbir seyi ONLEMEZ; oradaki rc 2 tek basina
        # kirmizi gurultudur ve bu depoda kapi birikmesinin bedeli olculmustur.
        b2, o2, h2 = commitleri_tara(eklenen, kayit, modul, kok=depo, butce=1,
                                     kirp=True)
        kontrol("6c kirpma modunda HATA YOK (rc 2 uretmez)",
                b2 is not None and h2 is None)
        kontrol("6d kirpma SESSIZ DEGIL: atlanan commit SAYISI raporlanir",
                o2.get("icerik_atlanan", 0) > 0,
                "(atlanan=%s)" % o2.get("icerik_atlanan"))
        kontrol("6e kirpilsa BILE MESAJ ekseni TUM commit'leri kapsar",
                o2["commit"] == len(eklenen)
                and any(b.eksen == "mesaj" for b in b2),
                "(commit=%d)" % o2["commit"])
        b3, o3, h3 = commitleri_tara(eklenen, kayit, modul, kok=depo, kirp=True)
        kontrol("6f butce dolmayinca kirpma modu TAM kapsar",
                h3 is None and o3.get("icerik_atlanan", 0) == 0
                and o3.get("icerik_kapsanan") == len(eklenen))
        kontrol("6g butce dolmayinca kirpma modu AYNI hukmu verir",
                {(b.sha, b.eksen) for b in b3} == {(b.sha, b.eksen)
                                                   for b in bulgular_tam})
        # 🔴 6h/6i SERIT AYRIMINI KOLLARIN KENDISINDE sabitler. Bunlar olmadan
        # "pre-push kolunu kirpma moduna al" mutanti SAG KALIYORDU (olculdu):
        # commitleri_tara duzeyindeki 6c-6g iddialari hangi KOLUN hangi modu
        # kullandigini OLCMEZ.
        rc = kol_pre_push(girdi=_push_girdisi(yerel_sha, uzak_sha), kok=depo,
                          ozet_yolu=artefakt, butce=1)
        kontrol("6h ONLEYICI kol (pre-push) butce asilinca rc=2 — KIRPMAZ",
                rc == RC_OLCULEMEDI, "(rc=%d)" % rc)
        rc = kol_ci(kok=depo, ozet_yolu=artefakt, ortam={"GITHUB_SHA": yerel_sha},
                    yuk={}, butce=1)
        kontrol("6i GORUNURLUK kolu (CI) butce asilinca rc=2 VERMEZ — kirpar",
                rc != RC_OLCULEMEDI, "(rc=%d)" % rc)

        # ---------------------------------------------------------------
        # VAKA 7 — SADECE ICERIK / SADECE MESAJ ekseni (biri digerini maskelemez)
        # ---------------------------------------------------------------
        print("\nVAKA 7 — eksenler BAGIMSIZ")
        depo7 = os.path.join(tmp, "v7")
        os.makedirs(depo7)
        _depo_kur(depo7)
        _yaz(depo7, "a.txt", "temiz\n")
        _commit(depo7, "taban")
        uzak7 = _kos(["git", "rev-parse", "HEAD"], depo7).stdout.strip()
        _yaz(depo7, "gizli.py", '"""ornek: %s ile calisir."""\n' % _UYDURMA[0])
        _commit(depo7, "notr mesaj, sizintili ICERIK")
        yerel7 = _kos(["git", "rev-parse", "HEAD"], depo7).stdout.strip()
        rc = kol_pre_push(girdi=_push_girdisi(yerel7, uzak7), kok=depo7,
                          ozet_yolu=artefakt)
        kontrol("7a mesaj TEMIZ + icerik SIZINTILI -> ENGELLENDI", rc == RC_SIZINTI,
                "(rc=%d)" % rc)
        depo8 = os.path.join(tmp, "v8")
        os.makedirs(depo8)
        _depo_kur(depo8)
        _yaz(depo8, "a.txt", "temiz\n")
        _commit(depo8, "taban")
        uzak8 = _kos(["git", "rev-parse", "HEAD"], depo8).stdout.strip()
        _yaz(depo8, "b.txt", "tamamen notr icerik\n")
        _commit(depo8, "%s partisi 4. dilim" % _UYDURMA[1])
        yerel8 = _kos(["git", "rev-parse", "HEAD"], depo8).stdout.strip()
        rc = kol_pre_push(girdi=_push_girdisi(yerel8, uzak8), kok=depo8,
                          ozet_yolu=artefakt)
        kontrol("7b icerik TEMIZ + mesaj SIZINTILI -> ENGELLENDI", rc == RC_SIZINTI,
                "(rc=%d)" % rc)

        # ---------------------------------------------------------------
        # VAKA 8 — YENIDEN ADLANDIRMA sizintiyi gizleyemez
        # ---------------------------------------------------------------
        print("\nVAKA 8 — yeniden adlandirma (-M kapali)")
        depo9 = os.path.join(tmp, "v9")
        os.makedirs(depo9)
        _depo_kur(depo9)
        _yaz(depo9, "kaynak.py", "# %s notu\n" % _UYDURMA[0] + "x = 1\n" * 40)
        _commit(depo9, "taban (sizintili dosya)")
        uzak9 = _kos(["git", "rev-parse", "HEAD"], depo9).stdout.strip()
        _kos(["git", "mv", "kaynak.py", "yeniad.py"], depo9)
        _commit(depo9, "yalnizca yeniden adlandirma")
        yerel9 = _kos(["git", "rev-parse", "HEAD"], depo9).stdout.strip()
        rc = kol_pre_push(girdi=_push_girdisi(yerel9, uzak9), kok=depo9,
                          ozet_yolu=artefakt)
        kontrol("8a yeniden adlandirma icerigi GIZLEYEMEDI", rc == RC_SIZINTI,
                "(rc=%d)" % rc)

        # ---------------------------------------------------------------
        # VAKA 9 — MERGE cakisma cozumunde uretilen metin (evil merge)
        # ---------------------------------------------------------------
        print("\nVAKA 9 — evil merge (hicbir ebeveynde olmayan metin)")
        depoA = os.path.join(tmp, "vA")
        os.makedirs(depoA)
        _depo_kur(depoA)
        _yaz(depoA, "f.txt", "taban\n")
        _commit(depoA, "taban")
        uzakA = _kos(["git", "rev-parse", "HEAD"], depoA).stdout.strip()
        _kos(["git", "checkout", "-q", "-b", "yan"], depoA)
        _yaz(depoA, "f.txt", "yan dal satiri\n")
        _commit(depoA, "yan dal")
        _kos(["git", "checkout", "-q", "main"], depoA)
        _yaz(depoA, "f.txt", "main satiri\n")
        _commit(depoA, "main degisikligi")
        _kos(["git", "merge", "--no-commit", "--no-ff", "yan"], depoA)
        _yaz(depoA, "f.txt", "cozum: %s kaynakli\n" % _UYDURMA[0])
        _kos(["git", "add", "-A"], depoA)
        _kos(["git", "commit", "-q", "--no-verify", "-m", "cakisma cozumu"], depoA)
        yerelA = _kos(["git", "rev-parse", "HEAD"], depoA).stdout.strip()
        rc = kol_pre_push(girdi=_push_girdisi(yerelA, uzakA), kok=depoA,
                          ozet_yolu=artefakt)
        kontrol("9a evil merge YAKALANDI", rc == RC_SIZINTI, "(rc=%d)" % rc)

        # ---------------------------------------------------------------
        # VAKA 10 — KOK commit taranir (--root)
        # ---------------------------------------------------------------
        print("\nVAKA 10 — kok commit")
        depoB = os.path.join(tmp, "vB")
        os.makedirs(depoB)
        _depo_kur(depoB)
        _yaz(depoB, "ilk.txt", "%s ile baslangic\n" % _UYDURMA[0])
        kokc, _ = _commit(depoB, "ilk commit")
        rc = kol_pre_push(girdi=_push_girdisi(kokc, SIFIR_SHA), kok=depoB,
                          ozet_yolu=artefakt)
        kontrol("10a KOK commit icerigi taranir", rc == RC_SIZINTI, "(rc=%d)" % rc)

        # ---------------------------------------------------------------
        # VAKA 11 — UCTAN UCA: GERCEK `git push`, GERCEK KANCA, GERCEK UZAK
        # ---------------------------------------------------------------
        # 🔴 NEDEN AYRI VAKA: yukaridaki vakalar kapinin HUKMUNU olcer; bu vaka
        # KABLOSUNU olcer — kanca gercekten devreye giriyor mu, nesneler uzaga
        # GITMIYOR mu, ve STDIN kancanin KALAN bloklarina geri veriliyor mu.
        # Son madde bir SESSIZ REGRESYON kapisidir: pre-push stdin'ini tuketip
        # birakmak D1 SENKRONUNU (ayni stdin'i `while read` ile okur) her push'ta
        # BOS girdiyle besler; senkron "degisiklik yok" sanip HIC KOSMAZ ve site
        # urunu gosterirken EGE GOREMEZ. Bu depoda olculmus satis kaybi sinifidir.
        print("\nVAKA 11 — uctan uca gercek push + stdin geri verimi")
        if not os.path.isfile(kur_yolu):
            kontrol("11a kurucu betik MEVCUT", False)
        else:
            uzak = os.path.join(tmp, "uzak.git")
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", uzak],
                           capture_output=True)
            yerel = os.path.join(tmp, "yerel")
            subprocess.run(["git", "clone", "-q", uzak, yerel], capture_output=True)
            _kos(["git", "config", "user.email", "t@example.com"], yerel)
            _kos(["git", "config", "user.name", "T"], yerel)
            _kos(["git", "config", "commit.gpgsign", "false"], yerel)
            os.makedirs(os.path.join(yerel, "tools"), exist_ok=True)
            for _ad in ("gecmis-geri-donus-kapisi.py", "commit-mesaji-kapisi.py"):
                _shutil.copy2(os.path.join(TOOLS, _ad),
                              os.path.join(yerel, "tools", _ad))
            _shutil.copy2(artefakt,
                          os.path.join(yerel, "tools", "sizinti-desen-ozetleri.json"))
            _yaz(yerel, "a.txt", "taban\n")
            _commit(yerel, "taban commit")
            _kos(["git", "push", "-q", "origin", "main"], yerel)
            _kos(["python3", kur_yolu, "--repo", yerel], yerel)
            kanca = os.path.join(yerel, ".git", "hooks", "pre-push")
            tanik = os.path.join(tmp, "stdin-tanigi.txt")
            with open(kanca, "a", encoding="utf-8") as f:
                f.write("\n# STDIN TANIGI (D1 senkronu taklidi)\n"
                        "while read -r lr ls rr rs; do\n"
                        '  echo "$rr $ls" >> "%s"\n'
                        "done\n"
                        "exit 0\n" % tanik)
            _yaz(yerel, "b.txt", "temiz is\n")
            _commit(yerel, "tedarikci partisi: notr mesaj")
            p = _kos(["git", "push", "origin", "main"], yerel)
            kontrol("11a TEMIZ push kanca ile GECTI", p.returncode == 0,
                    (p.stderr or "")[:160])
            kontrol("11b STDIN kalan bloga GERI VERILDI (D1 sessiz regresyonu YOK)",
                    os.path.isfile(tanik) and os.path.getsize(tanik) > 0)
            _yaz(yerel, "c.txt", "tedarikci %s ile anlasma\n" % _UYDURMA[0])
            _commit(yerel, "%s partisi: 12 urun" % _UYDURMA[0])
            p = _kos(["git", "push", "origin", "main"], yerel)
            cikti = (p.stdout or "") + (p.stderr or "")
            kontrol("11c SIZINTILI push GERCEKTEN DURDU", p.returncode != 0)
            kontrol("11d teshis UYDURMA ADI BASMIYOR",
                    _UYDURMA[0].lower() not in cikti.lower())
            uzak_uc = _kos(["git", "rev-parse", "main"], uzak).stdout.strip()
            yerel_uc = _kos(["git", "rev-parse", "HEAD"], yerel).stdout.strip()
            kontrol("11e nesneler uzaga GITMEDI", uzak_uc != yerel_uc)
            p = _kos(["git", "push", "--no-verify", "origin", "main"], yerel)
            kontrol("11f `--no-verify` cikis yolu CALISIYOR", p.returncode == 0)
            _kos(["python3", kur_yolu, "--repo", yerel, "--kaldir"], yerel)
            _yaz(yerel, "d.txt", "yine %s\n" % _UYDURMA[0])
            _commit(yerel, "%s ikinci parti" % _UYDURMA[0])
            p = _kos(["git", "push", "origin", "main"], yerel)
            cikti = (p.stdout or "") + (p.stderr or "")
            kontrol("11g kanca KALDIRILINCA push GECER (negatif kontrol)",
                    p.returncode == 0)
            kontrol("11h kanca KALDIRILINCA kapi HICBIR SEY uretmez",
                    "PUSH DURDURULDU" not in cikti
                    and "geri-donus taramasi" not in cikti)
            _kos(["python3", kur_yolu, "--repo", yerel], yerel)
            os.remove(os.path.join(yerel, "tools", "gecmis-geri-donus-kapisi.py"))
            _yaz(yerel, "e.txt", "x\n")
            _commit(yerel, "betik yok testi")
            p = _kos(["git", "push", "origin", "main"], yerel)
            kontrol("11i KAPI BETIGI YOKKEN push DURUR (fail-closed on-kosul)",
                    p.returncode != 0)

    finally:
        _shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d vaka · %d hata" % (vaka[0], len(hatalar)))
    if hatalar:
        for h in hatalar:
            print("  FAIL: " + h, file=sys.stderr)
        return 1
    print("KABUL BATARYASI GECTI.")
    return 0


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True, description=(
        "Temizlenmis sizintiyi geri getiren push/merge kapisi "
        "(mesaj + icerik ekseni)."))
    ap.add_argument("--pre-push", action="store_true",
                    help="pre-push kancasi kolu (menzil stdin'den)")
    ap.add_argument("--ci", action="store_true", help="CI kolu")
    ap.add_argument("--menzil", help="elle menzil, or. origin/main..HEAD")
    ap.add_argument("--kendini-test", action="store_true", help="kabul bataryasi")
    ap.add_argument("--uzak", default="origin", help="uzak adi (varsayilan: origin)")
    ap.add_argument("--kok", default=None, help="depo koku (varsayilan: bu depo)")
    ns = ap.parse_args(argv)
    secili = sum(bool(x) for x in (ns.pre_push, ns.ci, ns.menzil, ns.kendini_test))
    if secili != 1:
        ap.print_help()
        return RC_OLCULEMEDI
    if ns.kendini_test:
        return kendini_test()
    if ns.pre_push:
        return kol_pre_push(kok=ns.kok, uzak=ns.uzak)
    if ns.ci:
        return kol_ci(kok=ns.kok)
    return kol_menzil(ns.menzil, kok=ns.kok)


if __name__ == "__main__":
    sys.exit(main())
