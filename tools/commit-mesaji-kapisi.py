#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/commit-mesaji-kapisi.py — COMMIT MESAJINDA TEDARIKCI/SATICI KIMLIGI NOBETCISI.

🔴 OLCULEN OLAY (1 Agu 2026): depo PUBLIC. Tedarikci adi commit MESAJLARINDA 5 commit'te,
satici/vitrin alan adi 2 commit'te gecti (7 vurus, 5 benzersiz commit). Icerik
degisikliklerinde (`git log --all -S`) vurus 0 — yani mevcut sizinti nobetcileri
(tools/kisisel-veri-test.py: dosya ADI + dosya ICERIGI eksenleri) bu ekseni HIC
GORMUYORDU. Commit mesaji ucuncu bir yuzeydir: nesne yazildiktan sonra DEGISTIRILEMEZ,
push edilince raw API'den anonim okunabilir ve geri alinamaz.

BU NOBETCININ KAPSAMI: YENI sizintiyi ONLEMEK. Gecmisin temizlenmesi AYRI bir istir
(tarihce yeniden yazimi + force-push = Okan kapisi) ve bu arac ona DOKUNMAZ.

═══════════════════════════════════════════════════════════════════════════════
IKI KOL — biri ONLER, digeri GORUNUR KILAR
═══════════════════════════════════════════════════════════════════════════════
  (1) `commit-msg` GIT KANCASI (tools/commit-mesaji-hook-kur.py kurar) — YAZIM ANINDA
      durdurur. TEK ONLEYICI KOL BUDUR: commit nesnesi daha yazilmamistir, mesaj hala
      duzenlenebilir. FAIL-CLOSED (bkz. asagi).
  (2) CI KOLU (`--ci`, .github/workflows/deploy.yml `mesaj-nobeti` job'u) — o itmenin
      GETIRDIGI commit mesajlarini tarar (GECMISI DEGIL). Kanca kurulmamis bir makineden
      ya da `--no-verify` ile gelen sizintiyi GORUNUR kilar.

🔴 CI KOLU YAYINI BLOKLAMAZ — OLCULMUS KARAR, GEREKCESI:
  deploy.yml `deploy` job'u YALNIZ `needs: build`'e baglidir. `mesaj-nobeti` job'unun
  `needs:` alani YOKTUR ve hicbir job ona bagli DEGILDIR -> kirmizi yansa bile Pages
  yayini CIKAR (olculebilir: tools/is-akisi-kapisi.py `_serit_b_joblar`).
  NEDEN BOYLE SECILDI (uc olcum):
    (a) TAMIR DEGERI SIFIR: deploy.yml yalniz `push: branches: [main]` ile kosar. O an
        commit ZATEN public remote'tadir; yayini durdurmak sizmis mesaji GERI GETIRMEZ.
        Sitede commit mesaji GORUNMEZ — yani "sizintili icerik canliya cikmasin" sinifi
        DEGILDIR (o sinif serit A'da kalir).
    (b) BEDELI OLCULDU: bu depoda kapi birikmesi CI'yi 21 gunde 0,42 -> 6,55 dk'ya
        cikardi; 28 Tem'de urunle ILGISIZ TEK bir kapi 6 SAATLIK canli 404 pencereleri
        acti. Mesaj sizintisi urun yayinini durdurursa ilk toplu iste kapi devre disi
        birakilir ([[kapi-birikimi-yayin-gecikmesi]]).
    (c) ONLEME ZATEN KANCADADIR ve kanca FAIL-CLOSED'dir. CI kolu ikinci hattir.
  `continue-on-error` KULLANILMADI (fail-open yazimi nobetci ihlalidir): rc dogrudan
  konusur, job kirmizi yanar, bildirim duser.

═══════════════════════════════════════════════════════════════════════════════
🔴 DESEN KAYNAGI — YASAKLI AD BU DOSYADA (ya da HERHANGI bir izlenen dosyada) YAZMAZ
═══════════════════════════════════════════════════════════════════════════════
Depo PUBLIC. Bir "yasakli adlar listesi" nobetcinin KENDISINDE o adlari sizdirirdi —
kapinin engellemek icin var oldugu seyin ta kendisi. Bu yuzden iki kaynak vardir:

  A) `.sizinti-desenleri.txt` (GITIGNORE'LU, yalniz yerel) — YAZIM/uretim kaynagi.
     Satir basina bir yasakli ad; `#` yorum. SADECE `--desen-yaz` okur.
  B) `tools/sizinti-desen-ozetleri.json` (IZLENEN) — ESLESME kaynagi: yalniz
     PBKDF2-HMAC-SHA256 ozetleri + ortak tuz + aday uzunluklari. Duz ad YOK.

NEDEN IKI DOSYA (ve neden yalniz gitignore'lu dosya YETMEZ): gitignore'lu dosya CI'da
ve her taze klonda YOKTUR. Tek kaynak o olsaydi CI kolu ad eksenini HIC olcemez, "olcemedigi
icin yesil" verirdi — bu depoda tekrar tekrar olculmus SESSIZ delik sinifi. Izlenen ozet
artefakti sayesinde IKI KOL DA HER YERDE AYNI SEYI olcer.

DURUSTCE BEYAN (ozet != mutlak gizlilik): dusuk entropili bir OZEL AD icin ozet, elinde
aday ad olan KARARLI bir saldirgan icin bir DOGRULAMA ORAKLIDIR; PBKDF2 dongusu bunu
yalniz PAHALILASTIRIR. Ortadan kaldirdigi sey OLCULEN maruziyettir: duz adin klonlanabilir
dosyada, `grep`'te, GitHub kod aramasinda ve yapay zeka egitim kazimalarinda DURMASI.
Bugunku alternatif (tools/kisisel-veri-test.py `_TED_PARCALAR`: adi PARCALARA bolup izlenen
dosyada tutmak) bu esikte KESIN OLARAK daha zayiftir.

🔴 DESEN DOSYASI YOKSA: FAIL-CLOSED (rc 2 = OLCULEMEDI, commit/CI KIRMIZI). GEREKCE:
  * `tools/sizinti-desen-ozetleri.json` IZLENEN bir dosyadir — her klonda ve CI'da VARDIR.
    Yoklugu normal calisma hali DEGIL, ya kapinin icinin bosaltilmasi ya da bozuk
    checkout'tur. Ikisi de sessizce gecmemelidir.
  * Bir sizinti kapisinda fail-open, kapinin KENDISINI en ucuz mutasyona acar: dosyayi
    sil -> kapi yesil. Ayni gerekce tools/gecmis-nobeti-hook-kur.py'de de olculdu.
  * Bos liste / bozuk sema / taninmayan algoritma / dusuk dongu da AYNI hukumdur:
    "hicbir sey olcemedim" YESIL DEGILDIR.
  * Cikis yolu git'in kendi `--no-verify` bayragidir (gurultulu ve kayitli), kapiyi
    sessizce gevsetmek DEGIL.
  BUNUN TERSI (bilincli): `.sizinti-desenleri.txt` YOKLUGU hukme GIRMEZ. O dosya yalniz
  `--desen-yaz` girdisidir; eslesme ozetlerden yapilir. Onu zorunlu tutmak her taze
  klonu/CI'yi kirmiziya boyar ve herkesi `--no-verify`e iter -> guvenligi AZALTIRDI.

═══════════════════════════════════════════════════════════════════════════════
IKI KURAL AILESI
═══════════════════════════════════════════════════════════════════════════════
  AD EKSENI (ozet)     : normalize edilmis mesajda, KELIME BASINDAN baslayan ve desen
                         uzunlugunda olan her aday ozetlenip karsilastirilir. Iki akis
                         taranir: (1) bosluklu normal akis ("zorbacix in" gibi ek/
                         noktalama ayrilmis yazimlar), (2) sikistirilmis akis (bosluklar
                         atilmis: "hayali vitrin" -> "hayalivitrin"). Ek/noktalama ve
                         Turkce harf (ğ/ı/ş/ç/ö/ü/İ) farklari NORMALIZE ile duser.
                         🔴 BU DOSYADAKI TUM ORNEKLER UYDURMADIR (bkz. `_UYDURMA`):
                         gercek yasakli ad ORNEK OLARAK BILE izlenen dosyaya yazilmaz.
  ALAN ADI EKSENI      : BICIM kuralidir, isim listesi DEGIL — mesajdaki her URL/host
                         jetonu, IZLENEN ve tamami PUBLIC olan PUBLIC_ALAN listesinde
                         degilse KIRMIZI. Satici/vitrin alan adi boylece ADI HIC
                         YAZILMADAN yakalanir. Kaynak dosya adlari (`.py`, `.md`, `.sh`...)
                         UZANTI listesiyle elenir, TLD listesi kapalidir -> `d1-sync.py`
                         ya da `DEVAM.md` yanlis-pozitif URETMEZ.

🔴 TESHIS SIZDIRMAZ: eslesen METIN hicbir zaman basilmaz — konum + uzunluk basilir.
Aksi halde kapi, sizintiyi PUBLIC GitHub Actions gunlugune kendi eliyle yazardi.
Kanca kolunda (yerel terminal, metni yazan kisi zaten gormustur) alan adi acik yazilir;
`--ci` kolunda MASKELENIR.

Kullanim:
    python3 tools/commit-mesaji-kapisi.py --commit-msg <mesaj-dosyasi>   # kanca kolu
    python3 tools/commit-mesaji-kapisi.py --ci                            # CI kolu
    python3 tools/commit-mesaji-kapisi.py --menzil <A>..<B>               # elle menzil
    python3 tools/commit-mesaji-kapisi.py --son <N>                       # son N commit (OLCUM)
    python3 tools/commit-mesaji-kapisi.py --kendini-test                  # kabul bataryasi
    python3 tools/commit-mesaji-kapisi.py --desen-yaz                     # ozet artefakti uret
Cikis kodu: 0 temiz · 1 SIZINTI · 2 OLCULEMEDI (fail-closed).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

OZET_DOSYA = os.path.join(TOOLS, "sizinti-desen-ozetleri.json")
DUZ_DESEN_DOSYA = os.path.join(ROOT, ".sizinti-desenleri.txt")

RC_TEMIZ = 0
RC_SIZINTI = 1
RC_OLCULEMEDI = 2

# Ozet artefakti sozlesmesi. `dongu` asagi cekilerek kapi ucuzlatilamaz (fail-closed).
ALGO = "pbkdf2_sha256"
ASGARI_DONGU = 5000
ASGARI_DESEN_UZUNLUGU = 4          # 3 harfli bir "desen" her mesajda yanardi
# 🔴 DONGU SAYISI OLCUMLE SECILDI (5000, 20000 DEGIL): gercek 400 commit mesajinda
# 20 000 dongu ile ad ekseni ortanca 299 ms / p95 2 176 ms / en kotu 3 965 ms surdu.
# Dort saniyelik bir `commit-msg` kancasi bu depoda OLCULMUS bir arizadir: yavas kapi
# devre disi birakilir (`--no-verify` aliskanligi) ve o an koruma SIFIRLANIR. Kaybedilen
# sey de kucuktur — dongu sayisi yalniz "aday adi olan saldirganin dogrulama maliyetini"
# carpar; adin kendisi zaten dusuk entropilidir ve gercek koruma duz adin klonlanabilir
# dosyada BULUNMAMASIDIR (bkz. baslik: durustce beyan).
VARSAYILAN_DONGU = 5000


# ---------------------------------------------------------------------------
# NORMALIZE + ADAY URETIMI
# ---------------------------------------------------------------------------
# Turkce'ye ozgu harfler NFKD ile ayrisip birlesen isaretleri dusunce ASCII'ye iner
# (ğ->g, ş->s, ç->c, ö->o, ü->u, İ->i). `ı` ayrisMAZ -> elle eslenir. Amac (ornek UYDURMA):
# "Zorbaçıx", "ZORBACIX", "zorbacix'in" ayni normal bicime insin.
_ELLE_ESLEM = {"ı": "i", "İ": "i", "ł": "l", "ø": "o", "đ": "d", "ß": "ss"}


def normalize(metin):
    """Kucuk harfli, ASCII harf/rakam disi her sey TEK bosluk olan akis."""
    if not metin:
        return ""
    metin = "".join(_ELLE_ESLEM.get(k, k) for k in metin)
    ayrik = unicodedata.normalize("NFKD", metin)
    ayrik = "".join(k for k in ayrik if not unicodedata.combining(k))
    ayrik = ayrik.lower()
    ayrik = "".join(k if ("a" <= k <= "z" or "0" <= k <= "9") else " " for k in ayrik)
    return " ".join(ayrik.split())


def _kelime_baslari(akis):
    """Akista kelime BASI olan indeksler (0 ve her bosluktan sonraki karakter)."""
    if not akis:
        return []
    yerler = [0]
    for i, k in enumerate(akis):
        if k == " " and i + 1 < len(akis):
            yerler.append(i + 1)
    return yerler


def adaylar(metin, uzunluk):
    """<uzunluk> karakterlik aday kumesi: bosluklu VE sikistirilmis akisin kelime
    baslarindan alinan dilimler. Kume -> tekrarli jetonlar bir kez ozetlenir.

    IKI AKIS BILEREK: bosluklu akis "zorbacix in" gibi ek/noktalama ayrilmis yazimi,
    sikistirilmis akis ise "hayali vitrin" gibi AYRIK yazilmis bitisik adi yakalar.
    (Ornekler UYDURMADIR — gercek yasakli ad bu dosyada YAZMAZ.)"""
    if uzunluk <= 0:
        return set()
    bosluklu = normalize(metin)
    kume = set()
    for bas in _kelime_baslari(bosluklu):
        dilim = bosluklu[bas:bas + uzunluk]
        if len(dilim) == uzunluk:
            kume.add(dilim)
    # Sikistirilmis akis: kelime baslarinin yeni indeksleri jeton uzunluklarindan turer.
    jetonlar = bosluklu.split(" ") if bosluklu else []
    sikisik = "".join(jetonlar)
    yer = 0
    for jeton in jetonlar:
        dilim = sikisik[yer:yer + uzunluk]
        if len(dilim) == uzunluk:
            kume.add(dilim)
        yer += len(jeton)
    return kume


# ---------------------------------------------------------------------------
# OZET ARTEFAKTI
# ---------------------------------------------------------------------------
def _ozetle(aday, tuz_bayt, dongu):
    return hashlib.pbkdf2_hmac("sha256", aday.encode("utf-8"), tuz_bayt, dongu).hex()


# ---------------------------------------------------------------------------
# SURE EKSENI OLCU BIRIMI — "REFERANS MAKINE MS" (gerekce: kabul bataryasi, I bolumu)
# ---------------------------------------------------------------------------
# Kalibrasyon makinesinde 5000 donguluk bir PBKDF2 cagrisi 0,4008 ms surdu. Sure
# butcesi (3000/400 ms) O makineye gore yazilmistir; baska bir makinede olculen ham
# ms, o makinenin OLCULEN birim maliyetiyle bu referansa cevrilir. Boylece butce her
# yerde AYNI seyi — yapilan isi — olcer, makine hizini DEGIL.
REFERANS_BIRIM_MS = 0.40


def referans_ms(ham_ms, birim_ms, referans_birim_ms=REFERANS_BIRIM_MS):
    """Bu makinede olculen ham ms -> REFERANS makine ms.

    birim_ms olculemezse 0.0 doner; cagiran `0 < sure` bekledigi icin bu FAIL-CLOSED
    kirmizi olur ("olcemedim" YESIL degildir)."""
    if not birim_ms or birim_ms <= 0:
        return 0.0
    return ham_ms * (referans_birim_ms / birim_ms)


def ozet_kaydi_yukle(yol=None):
    """(kayit, hata). FAIL-CLOSED: her arizada kayit None doner ve cagiran rc 2 verir.

    Dogrulanan sozlesme: algo · dongu >= ASGARI_DONGU · tuz hex · BOS OLMAYAN desen
    listesi · her desen {n >= ASGARI_DESEN_UZUNLUGU, ozet = 64 hane hex}."""
    yol = yol or OZET_DOSYA
    if not os.path.isfile(yol):
        return None, ("desen ozet dosyasi YOK: %s — izlenen bir dosyadir, her klonda "
                      "bulunmalidir. Uret: python3 tools/commit-mesaji-kapisi.py "
                      "--desen-yaz" % yol)
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:
        return None, "desen ozet dosyasi OKUNAMADI/AYRISTIRILAMADI: %s (%s)" % (yol, e)
    if not isinstance(veri, dict):
        return None, "desen ozet dosyasi sozluk DEGIL: %s" % yol
    if veri.get("algo") != ALGO:
        return None, ("desen ozet algoritmasi taninmiyor: %r (beklenen %r)"
                      % (veri.get("algo"), ALGO))
    dongu = veri.get("dongu")
    if not isinstance(dongu, int) or dongu < ASGARI_DONGU:
        return None, ("desen ozet donusu gecersiz/dusuk: %r (asgari %d) — kapi "
                      "ucuzlatilarak gevsetilemez" % (dongu, ASGARI_DONGU))
    tuz = veri.get("tuz")
    if not isinstance(tuz, str) or not re.fullmatch(r"[0-9a-f]{16,}", tuz or ""):
        return None, "desen ozet tuzu gecersiz (en az 8 bayt hex bekleniyor)"
    desenler = veri.get("desenler")
    if not isinstance(desenler, list) or not desenler:
        return None, ("desen listesi BOS ya da liste degil -> ad ekseni HICBIR SEY "
                      "olcemez (fail-closed; 'olcemedim' YESIL degildir)")
    temiz = []
    for i, d in enumerate(desenler):
        if not isinstance(d, dict):
            return None, "desen #%d sozluk degil" % i
        n = d.get("n")
        ozet = d.get("ozet")
        if not isinstance(n, int) or n < ASGARI_DESEN_UZUNLUGU:
            return None, ("desen #%d uzunlugu gecersiz: %r (asgari %d — daha kisa desen "
                          "her mesajda yanar)" % (i, n, ASGARI_DESEN_UZUNLUGU))
        if not isinstance(ozet, str) or not re.fullmatch(r"[0-9a-f]{64}", ozet or ""):
            return None, "desen #%d ozeti 64 haneli hex DEGIL" % i
        temiz.append((n, ozet))
    return {"dongu": dongu, "tuz": bytes.fromhex(tuz), "desenler": temiz}, None


def ad_isabetleri(mesaj, kayit):
    """[(desen_no, uzunluk), ...] — mesajda hangi desenler gecti.

    🔴 ESLESEN METIN DONMEZ ve BASILMAZ: teshis yalnizca desen sirasi + uzunluktur.
    Aksi halde kapi sizintiyi kendi ciktisiyla (CI gunlugu PUBLIC'tir) cogaltirdi."""
    if not kayit:
        return []
    uzunluklar = sorted({n for n, _ in kayit["desenler"]})
    aday_ozetleri = {}
    for n in uzunluklar:
        for aday in adaylar(mesaj, n):
            aday_ozetleri.setdefault(n, set()).add(
                _ozetle(aday, kayit["tuz"], kayit["dongu"]))
    isabet = []
    for i, (n, ozet) in enumerate(kayit["desenler"]):
        if ozet in aday_ozetleri.get(n, ()):
            isabet.append((i, n))
    return isabet


# ---------------------------------------------------------------------------
# ALAN ADI EKSENI — BICIM KURALI (isim listesi DEGIL)
# ---------------------------------------------------------------------------
# 🔴 NEDEN BICIM EKSENI: satici/vitrin alan adi PUBLIC bir dosyaya YAZILAMAZ. Bu yuzden
# kural tersine cevrilir: "taninan PUBLIC alan adlari" IZLENIR (hepsi zaten herkese
# acik), geri kalan HER alan adi KIRMIZI yanar. Boylece gizli alan adi ADI HIC
# YAZILMADAN yakalanir ve liste bayatlasa bile kapi fail-closed tarafa duser.
PUBLIC_ALAN = frozenset((
    # kendi yuzeylerimiz + platform/altyapi (hepsi sitede/DNS'te zaten aciktir)
    "pruvo3d.com", "github.com", "githubusercontent.com", "github.io",
    "cloudflare.com", "cloudflarestorage.com", "workers.dev", "pages.dev",
    "iyzico.com", "iyzipay.com", "google.com", "googleapis.com", "gstatic.com",
    "schema.org", "w3.org", "creativecommons.org", "openscad.org", "python.org",
    "nodejs.org", "npmjs.com", "wa.me", "whatsapp.com", "facebook.com",
    # commit trailer'larinda gecen kimlik alanlari (kisi/model kimligi, tedarikci DEGIL)
    "anthropic.com", "claude.com", "me.com", "icloud.com", "gmail.com",
    "users.noreply.github.com", "noreply.github.com",
    # urun kaynagi platformlari — katalogda ATIF ile zaten GORUNUR
    "thingiverse.com", "printables.com", "makerworld.com", "cults3d.com",
    "myminifactory.com", "prusa3d.com", "bambulab.com", "stlfinder.com",
    "notion.so", "notion.com",
))

# KAPALI TLD listesi: acik uclu bir "nokta gorursen alan adidir" kurali `d1-sync.py`,
# `DEVAM.md`, `paket-v7.tar.gz` gibi HER dosya adini yakalardi.
TLD = frozenset((
    "com", "net", "org", "io", "co", "dev", "app", "shop", "store", "online",
    "site", "web", "cloud", "tech", "info", "biz", "xyz", "tv",
    "tr", "de", "fr", "uk", "nl", "es", "it", "us", "ca", "ru", "cn", "se",
    # 🔴 DOSYA UZANTISIYLA CAKISAN GERCEK ccTLD'ler bilerek BURADADIR ve asagidaki
    # UZANTI listesiyle elenir. Boylece UZANTI elemesi YUK TASIR: kaldirilirsa
    # `DEVAM.md` / `d1-sync.py` / `libx.so` aninda yanlis-pozitif uretir (mutasyon
    # M10 bunu olcer). BEDELI ACIK BEYAN: `.md`/`.sh`/`.py`/`.so`/`.pl` uzantili bir
    # GERCEK alan adi bu eksende GORUNMEZ — o hal AD EKSENINE (ozet) birakilmistir.
    "md", "sh", "py", "so", "pl",
))
UZANTI = frozenset((
    "py", "js", "mjs", "cjs", "ts", "json", "jsonl", "md", "html", "htm", "css",
    "yml", "yaml", "sql", "sh", "txt", "xml", "csv", "tsv", "log", "lock", "toml",
    "ini", "cfg", "conf", "plist", "sample", "bak", "tmp", "orig", "rej", "patch",
    "diff", "pyc", "pyo", "map", "gz", "zip", "tar", "pdf", "svg", "png", "jpg",
    "jpeg", "webp", "gif", "ico", "stl", "3mf", "scad", "step", "stp", "obj", "mtl",
    "woff", "woff2", "ttf", "mp4", "webm", "env", "gitignore", "example",
    "so", "pl", "rs", "rb", "go", "c", "h", "cpp",
))

_URL_RE = re.compile(r"https?://([^\s/?#]+)", re.IGNORECASE)
_HOST_RE = re.compile(r"(?<![0-9A-Za-z@._-])"
                      r"([0-9A-Za-z](?:[0-9A-Za-z-]*[0-9A-Za-z])?"
                      r"(?:\.[0-9A-Za-z](?:[0-9A-Za-z-]*[0-9A-Za-z])?)+)")
_EPOSTA_RE = re.compile(r"[0-9A-Za-z._%+-]+@([0-9A-Za-z.-]+\.[A-Za-z]{2,})")


def _public_mi(host):
    host = host.lower().strip(".")
    for a in PUBLIC_ALAN:
        if host == a or host.endswith("." + a):
            return True
    return False


# ---------------------------------------------------------------------------
# KATALOG MARKA MUAFIYETI — OLCULEN YANLIS-POZITIF ONARIMI (1 Agu 2026)
# ---------------------------------------------------------------------------
# 🔴 OLCULEN ARIZA: alan adi ekseni SAF bicim kuraliydi -> PUBLIC_ALAN disindaki HER
# host kirmizi. `urunler.json`'daki 1291 gercek katalog markasinin `<marka>.com`
# haliyle olculdu: 1291/1291'i KIRMIZI yaniyordu. Yani "Bosch icin NGK muadili
# eklendi, bkz bosch.com" gibi TAMAMEN MESRU bir mesaj commit'i durduruyordu. Bu,
# gorevin adlandirdigi ALARM KORLUGU sinifinin ta kendisidir: mesru is engellenince
# cikis yolu `--no-verify` aliskanligi olur ve o an TUM eksenler (ad ekseni dahil)
# birden kapanir. Kapinin yanlis-pozitifi, kapinin KENDISINI kapatir.
#
# COZUM: markalar IZLENEN ve zaten PUBLIC olan `urunler.json`'un `marka` alanindan
# CALISMA ANINDA turetilir — yeni bir liste dosyasi YOK, bayatlama YOK, ve public
# olmayan hicbir ad yazilmaz. Bir host'un ILK etiketi katalog markasiysa YESIL.
#
# 🔴 GEVSEME DEGIL, cunku SIRA SABIT: ozet (ad) ekseni ONCE bakilir ve KAZANIR.
# Tedarikci/vitrin adi ozet artefaktindadir; marka listesine (kazara ya da kasten)
# girse bile ozet isabeti muafiyeti EZER ve host KIRMIZI kalir (iddia J3/J4 bunu
# olcer). Muafiyetin acabildigi tek kapi, ozette OLMAYAN + katalogda VAR OLAN, yani
# tanimi geregi zaten PUBLIC olan bir markadir.
#
# MALIYET: `urunler.json` 14,4 MB / 16 407 urun -> tam ayristirma 102 ms. Bu yuzden
# TEMBEL yuklenir: yalniz mesajda PUBLIC_ALAN disi bir host VARSA okunur (normal
# commit'lerin ezici cogunlugunda hic okunmaz) ve surec basina bir kez onbelleklenir.
URUNLER_JSON = os.path.join(ROOT, "urunler.json")
ASGARI_MARKA_UZUNLUGU = 4          # 3 harfli marka her alan adinda yanardi
_MARKA_ONBELLEK = {}


def katalog_markalari(yol=None):
    """Normalize edilmis katalog markasi kumesi. Dosya yoksa/bozuksa BOS kume.

    BOS kume = muafiyet YOK = eski KATI davranis; yani bu yolun arizasi kapiyi
    GEVSETMEZ, siki tarafa duser (fail-closed yonu)."""
    yol = yol or URUNLER_JSON
    if yol in _MARKA_ONBELLEK:
        return _MARKA_ONBELLEK[yol]
    kume = set()
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        for urun in (veri if isinstance(veri, list) else ()):
            if not isinstance(urun, dict):
                continue
            for marka in (urun.get("marka") or ()):
                if not isinstance(marka, str):
                    continue
                n = normalize(marka).replace(" ", "")
                # Salt rakam olan model kodlari (`1007`, `2002`) muafiyete girmez:
                # alan adi olarak gecmezler, kumeyi gereksiz genisletirlerdi.
                if len(n) >= ASGARI_MARKA_UZUNLUGU and any("a" <= k <= "z" for k in n):
                    kume.add(n)
    except (OSError, ValueError):
        kume = set()
    kume = frozenset(kume)
    _MARKA_ONBELLEK[yol] = kume
    return kume


def _host_desen_isabeti(host, kayit):
    """Host'un kendisi GIZLI DESEN mi (tedarikci/vitrin alan adi).

    Host'un etiket zinciri hem bosluklu ('vitrin com') hem sikistirilmis
    ('vitrincom') hem de govde ('vitrin') olarak ozetlenip karsilastirilir."""
    if not kayit:
        return None
    etiketler = [e for e in host.lower().strip(".").split(".") if e]
    if not etiketler:
        return None
    govde = etiketler[0]
    akislar = (" ".join(etiketler), "".join(etiketler), govde,
               " ".join(etiketler[:-1]), "".join(etiketler[:-1]))
    for i, (n, ozet) in enumerate(kayit["desenler"]):
        for akis in akislar:
            if len(akis) == n and _ozetle(akis, kayit["tuz"], kayit["dongu"]) == ozet:
                return i
    return None


def alan_adi_isabetleri(mesaj, kayit=None, markalar=None):
    """[(host, konum, desen_no), ...] — hukme giren host jetonlari.

    `desen_no` None ise "PUBLIC_ALAN'da olmayan TANINMAYAN host" (bicim kurali);
    sayi ise "host'un KENDISI gizli desen" -> host teshise ASLA yazilmaz.

    `markalar=None` -> katalog tembel yuklenir; `frozenset()` -> muafiyet KAPALI."""
    if not mesaj:
        return []
    bulunan = {}
    for re_ in (_URL_RE, _EPOSTA_RE):
        for m in re_.finditer(mesaj):
            host = m.group(1).lower().strip(".")
            if not _public_mi(host):
                bulunan.setdefault(host, m.start(1))
    for m in _HOST_RE.finditer(mesaj):
        jeton = m.group(1).lower().strip(".")
        etiketler = jeton.split(".")
        son = etiketler[-1]
        if son in UZANTI or son not in TLD:
            continue
        if len(etiketler) < 2 or not etiketler[0]:
            continue
        if _public_mi(jeton):
            continue
        bulunan.setdefault(jeton, m.start(1))
    if not bulunan:
        return []
    if markalar is None:
        markalar = katalog_markalari()
    isabet = []
    for host, konum in bulunan.items():
        # 🔴 SIRA GUVENLIK ICIN SABIT: once GIZLI DESEN, sonra marka muafiyeti.
        no = _host_desen_isabeti(host, kayit)
        if no is not None:
            isabet.append((host, konum, no))
            continue
        if normalize(host.split(".")[0]).replace(" ", "") in markalar:
            continue
        isabet.append((host, konum, None))
    return sorted(isabet)


def maskele(host):
    """`ornek.com` -> `o****.com` — CI gunlugu PUBLIC'tir, host acik yazilamaz."""
    etiketler = host.split(".")
    govde = etiketler[0]
    gizli = (govde[0] + "*" * (len(govde) - 1)) if govde else "*"
    return ".".join([gizli] + etiketler[1:])


# ---------------------------------------------------------------------------
# MESAJ HAZIRLAMA — git yorum satirlari HUKME GIRMEZ
# ---------------------------------------------------------------------------
_MAKAS = "------------------------ >8 ------------------------"


def mesaj_govdesi(ham, yorum_karakteri="#"):
    """commit-msg dosyasindan GERCEK mesaji cikar.

    🔴 NEDEN: `commit-msg` kancasi git yorumlari TEMIZLENMEDEN once kosar. Sablon
    yorumlari dal adini, DEGISEN DOSYA YOLLARINI ve `-v` ile TUM DIFF'i tasiyabilir.
    Yorumlar hukme girseydi kapi hem yanlis-pozitif uretir (dosya adlari) hem de
    KULLANICININ YAZMADIGI metni sucllardi. Makas satirindan sonrasi da atilir."""
    satirlar = []
    for satir in (ham or "").splitlines():
        if satir.startswith(yorum_karakteri) and _MAKAS in satir:
            break
        if satir.startswith(yorum_karakteri):
            continue
        satirlar.append(satir)
    return "\n".join(satirlar).strip()


def mesaj_kusurlari(mesaj, kayit, maskeli=False, markalar=None):
    """[teshis, ...] — bos liste = temiz. Eslesen METIN asla teshise girmez."""
    kusurlar = []
    for no, n in ad_isabetleri(mesaj, kayit):
        kusurlar.append(
            "TEDARIKCI/SATICI ADI: commit mesajinda gizli desen #%d (uzunluk %d) gecti. "
            "Depo PUBLIC — commit mesaji DEGISTIRILEMEZ ve raw API'den anonim okunur. "
            "(Eslesen metin BILEREK yazilmiyor: bu ciktinin kendisi de sizinti olurdu.)"
            % (no, n))
    for host, konum, no in alan_adi_isabetleri(mesaj, kayit, markalar):
        if no is not None:
            # 🔴 HOST GIZLI DESENIN KENDISI -> maskeli/acik FARK ETMEZ, YAZILMAZ.
            # Kanca kolunda bile: burada gorunen ad, ad ekseninin gizledigi adin
            # ta kendisidir; teshise yazmak nobetciyi sizinti kaynagina cevirirdi.
            kusurlar.append(
                "TEDARIKCI/SATICI ALAN ADI: commit mesajinda gizli desen #%d ile "
                "eslesen bir host gecti (konum %d). Alan adi BILEREK yazilmiyor. "
                "Mesaji duzenle: adres yerine notr ifade ('kaynak platform')."
                % (no, konum))
            continue
        gosterim = maskele(host) if maskeli else host
        kusurlar.append(
            "TANINMAYAN ALAN ADI: %r (konum %d) — commit mesajinda yalniz PUBLIC_ALAN "
            "listesindeki alan adlari ve KATALOG MARKASI alan adlari gecebilir. "
            "Satici/vitrin/tedarikci alan adi PUBLIC depoya girmez. Mesru ve PUBLIC "
            "bir alan adiysa tools/commit-mesaji-kapisi.py PUBLIC_ALAN listesine ekle."
            % (gosterim, konum))
    return kusurlar


# ---------------------------------------------------------------------------
# GIT MENZIL COZUMU (CI kolu)
# ---------------------------------------------------------------------------
SIFIR_SHA = "0" * 40


def _git(args, kok=None):
    return subprocess.run(["git", "-C", kok or ROOT] + args,
                          capture_output=True, text=True)


def menzil_mesajlari(menzil, kok=None):
    """(mesajlar, hata) — `A..B` menzilindeki commit mesajlari (NUL ayrilmis)."""
    p = _git(["log", "--format=%B%x00", menzil], kok=kok)
    if p.returncode != 0:
        return None, "git log %s rc=%d: %s" % (menzil, p.returncode,
                                               (p.stderr or "").strip()[:200])
    return [m for m in p.stdout.split("\0") if m.strip()], None


def _olay_yuku():
    yol = os.environ.get("GITHUB_EVENT_PATH")
    if not yol or not os.path.isfile(yol):
        return None
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def ci_mesajlari(kok=None, ortam=None, yuk=None):
    """(mesajlar, kaynak, hata) — BU ITMENIN getirdigi commit mesajlari.

    Sira: (1) git menzili `before..after` (tam gecmis varsa EN DOGRUSU),
          (2) olay yukundeki `commits[].message` (checkout SIG olsa bile calisir),
          (3) HICBIRI -> FAIL-CLOSED hata (sessizce 'hicbir sey taramadim' YOK)."""
    ortam = os.environ if ortam is None else ortam
    yuk = _olay_yuku() if yuk is None else yuk
    once = (yuk or {}).get("before") or ortam.get("GITHUB_EVENT_BEFORE") or ""
    sonra = ((yuk or {}).get("after") or ortam.get("GITHUB_SHA") or "")
    if once and sonra and once != SIFIR_SHA:
        p = _git(["cat-file", "-e", once + "^{commit}"], kok=kok)
        q = _git(["cat-file", "-e", sonra + "^{commit}"], kok=kok)
        if p.returncode == 0 and q.returncode == 0:
            mesajlar, hata = menzil_mesajlari("%s..%s" % (once, sonra), kok=kok)
            if mesajlar is not None:
                return mesajlar, "git menzili %s..%s" % (once[:8], sonra[:8]), None
            return None, None, hata
    commits = (yuk or {}).get("commits")
    if isinstance(commits, list) and commits:
        mesajlar = [c.get("message", "") for c in commits if isinstance(c, dict)]
        return ([m for m in mesajlar if m.strip()],
                "olay yuku (commits[], %d kayit)" % len(mesajlar), None)
    if sonra:
        mesajlar, hata = menzil_mesajlari("%s~1..%s" % (sonra, sonra), kok=kok)
        if mesajlar is not None:
            return mesajlar, "tek commit %s" % sonra[:8], None
    return None, None, ("bu itmenin GETIRDIGI commit'ler COZULEMEDI (ne git menzili ne "
                        "olay yuku) -> fail-closed KIRMIZI. 'Olcemedim' YESIL degildir.")


# ---------------------------------------------------------------------------
# DESEN YAZIMI
# ---------------------------------------------------------------------------
def desen_yaz(kaynak=None, hedef=None, dongu=VARSAYILAN_DONGU, tuz=None):
    """Gizli duz metin desen dosyasindan IZLENEN ozet artefaktini uret.

    Duz ad NE donulur NE basilir NE de hedefe yazilir. Ozetler SIRALANIR ->
    yazim sirasi bile bilgi tasimaz."""
    kaynak = kaynak or DUZ_DESEN_DOSYA
    hedef = hedef or OZET_DOSYA
    if not os.path.isfile(kaynak):
        return None, ("desen kaynagi YOK: %s — satir basina bir yasakli ad yaz "
                      "(bu dosya GITIGNORE'LUDUR ve asla commit'lenmez)." % kaynak)
    ham = []
    with open(kaynak, encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if not satir or satir.startswith("#"):
                continue
            ham.append(satir)
    normalize_edilmis = []
    for satir in ham:
        n = normalize(satir)
        if len(n) < ASGARI_DESEN_UZUNLUGU:
            return None, ("desen normalize edilince %d karakterden kisa kaldi -> "
                          "reddedildi (adi yazmiyoruz; kaynak dosyada duzelt)"
                          % ASGARI_DESEN_UZUNLUGU)
        normalize_edilmis.append(n)
        sikisik = n.replace(" ", "")
        if sikisik != n and len(sikisik) >= ASGARI_DESEN_UZUNLUGU:
            normalize_edilmis.append(sikisik)
    if not normalize_edilmis:
        return None, "desen kaynagi BOS -> uretilecek ozet yok (fail-closed)"
    tuz_bayt = bytes.fromhex(tuz) if tuz else os.urandom(16)
    desenler = sorted(
        ({"n": len(d), "ozet": _ozetle(d, tuz_bayt, dongu)}
         for d in sorted(set(normalize_edilmis))),
        key=lambda d: d["ozet"])
    veri = {
        "surum": 1,
        "algo": ALGO,
        "dongu": dongu,
        "tuz": tuz_bayt.hex(),
        "not": ("PBKDF2-HMAC-SHA256 ozetleri. Duz ad YOK ve OLMAYACAK (depo PUBLIC). "
                "Uretim: python3 tools/commit-mesaji-kapisi.py --desen-yaz "
                "(kaynak .sizinti-desenleri.txt, GITIGNORE'LU)."),
        "desenler": desenler,
    }
    with open(hedef, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return len(desenler), None


# ---------------------------------------------------------------------------
# KOLLAR
# ---------------------------------------------------------------------------
def _kayit_ya_da_cik(ozet_yolu=None):
    kayit, hata = ozet_kaydi_yukle(ozet_yolu)
    if kayit is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
    return kayit


def kol_commit_msg(yol, ozet_yolu=None):
    kayit = _kayit_ya_da_cik(ozet_yolu)
    if kayit is None:
        return RC_OLCULEMEDI
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            ham = f.read()
    except OSError as e:
        print("OLCULEMEDI (fail-closed KIRMIZI): commit mesaji dosyasi okunamadi: %s"
              % e, file=sys.stderr)
        return RC_OLCULEMEDI
    kusurlar = mesaj_kusurlari(mesaj_govdesi(ham), kayit, maskeli=False)
    if not kusurlar:
        return RC_TEMIZ
    print("COMMIT ENGELLENDI — mesajda tedarikci/satici kimligi:", file=sys.stderr)
    for k in kusurlar:
        print("  * " + k, file=sys.stderr)
    print("  COZUM: mesaji duzenle (ad yerine notr ifade: 'tedarikci partisi', "
          "'kaynak platform'). Gecmisi temizlemek ZORDUR: nesne yazildiktan sonra "
          "mesaj degistirilemez, tarihce yeniden yazimi + force-push gerekir.",
          file=sys.stderr)
    return RC_SIZINTI


def kol_ci(kok=None, ozet_yolu=None):
    kayit = _kayit_ya_da_cik(ozet_yolu)
    if kayit is None:
        return RC_OLCULEMEDI
    mesajlar, kaynak, hata = ci_mesajlari(kok=kok)
    if mesajlar is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    print("taranan commit mesaji: %d (kaynak: %s)" % (len(mesajlar), kaynak))
    toplam = 0
    for i, mesaj in enumerate(mesajlar):
        kusurlar = mesaj_kusurlari(mesaj_govdesi(mesaj), kayit, maskeli=True)
        for k in kusurlar:
            toplam += 1
            print("  [mesaj %d] %s" % (i, k), file=sys.stderr)
    if toplam:
        print("SIZINTI: %d bulgu — bu itmenin getirdigi mesajlarda tedarikci/satici "
              "kimligi. Bu job YAYINI DURDURMAZ (tamir degeri yok: commit zaten "
              "public); ONLEME kolu commit-msg kancasidir "
              "(python3 tools/commit-mesaji-hook-kur.py)." % toplam, file=sys.stderr)
        return RC_SIZINTI
    print("temiz: 0 bulgu.")
    return RC_TEMIZ


# ---------------------------------------------------------------------------
# KAYNAK TARAMA KOLU — UCUNCU YUZEY: NOBETCININ KENDI DOSYALARI
# ---------------------------------------------------------------------------
# 🔴 OLCULEN ARIZA (1 Agu 2026): bu dosyanin KENDI docstring/yorumlari, mekanizmayi
# anlatmak icin ORNEK diye GERCEK yasakli adi duz metin yaziyordu (6 satir, 2 desen).
# Yani "yasakli ad hicbir IZLENEN dosyada yazmaz" beyani kapinin KENDISINDE ihlaldi.
# Bu bir COMMIT MESAJI sizintisi degil ICERIK sizintisidir: depo PUBLIC, dosya ham
# olarak servis edilir, kod aramasi ve egitim kazimalari tarafindan okunur.
# NEDEN MEVCUT NOBETCILER GORMEDI: tools/kisisel-veri-test.py'nin icerik ekseni BASKA
# bir tedarikci kumesini (kendi parcali kaliplarini) tarar; bu artefaktin desenlerini
# BILMEZ. Iki kume arasindaki bosluk olculdu ve bu kol o bosluktur.
KAYNAK_TARAMA = (
    "tools/commit-mesaji-kapisi.py",
    "tools/commit-mesaji-hook-kur.py",
    "tools/commit-mesaji-mutasyon.py",
    "tools/sizinti-desen-ozetleri.json",
    ".github/workflows/deploy.yml",
)
# 🔴 KAPSAM DARALTMA — OLCULEN MALIYET. Tam kapsam (5 dosyanin TAMAMI) 31,7 s surdu;
# CI'da (olculen 3,58x) ~113 s eder ve bu deponun tekrar tekrar olctugu KAPI BIRIKMESI
# arizasini buyutur. Maliyetin ezici cogunlugu 131 KB'lik deploy.yml'dendir ve o
# dosyanin bu eksende TASIDIGI RISK yalniz `mesaj-nobeti` job'unun kendi metnidir
# (adim adlari + yorumlari) — geri kalan 40'tan fazla job'un bu nobetciyle ilgisi YOK
# ve onlar zaten tools/kisisel-veri-test.py'nin icerik ekseninde. Bu yuzden deploy.yml
# BLOK olarak taranir. Daraltma OLCULDU: 31,7 s -> 12,2 s, kapsam kaybi YOK (bu
# nobetcinin yazdigi/yazabilecegi tek yer o bloktur).
_BLOK_KAPSAM = {".github/workflows/deploy.yml": ("\n  mesaj-nobeti:", "\n  # ")}


def _kaynak_metni(yol, rel):
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    except OSError:
        return None
    kapsam = _BLOK_KAPSAM.get(rel)
    if kapsam:
        bas, son = kapsam
        if bas not in metin:
            # Blok BULUNAMADI -> daraltma yapilamadi. Sessizce "hicbir sey taramadim"
            # DEMEK YERINE tum dosya taranir (fail-closed yonu: pahali ama kor degil).
            return metin
        metin = metin.split(bas, 1)[1]
        return metin.split(son, 1)[0]
    return metin


def kaynak_tara(kayit, kok=None, dosyalar=KAYNAK_TARAMA):
    """[(dosya, desen_no), ...] — izlenen kaynaklarda DUZ METIN yasakli ad.

    🔴 MALIYET NOTU: adaylar TUM dosyalar boyunca TEK kumede toplanip bir kez
    ozetlenir (kaynaklar buyuk olcude ayni jetonlari paylasir). Eslesen METIN yine
    ASLA donmez/basilmaz."""
    kok = kok or ROOT
    uzunluklar = sorted({n for n, _ in kayit["desenler"]})
    # aday -> onu iceren dosyalar
    aday_dosya = {}
    for rel in dosyalar:
        metin = _kaynak_metni(os.path.join(kok, rel), rel)
        if metin is None:
            continue
        for n in uzunluklar:
            for aday in adaylar(metin, n):
                aday_dosya.setdefault((n, aday), set()).add(rel)
    ozet_aday = {}
    for (n, aday), _ in aday_dosya.items():
        ozet_aday.setdefault((n, _ozetle(aday, kayit["tuz"], kayit["dongu"])),
                             set()).update(aday_dosya[(n, aday)])
    bulgular = []
    for i, (n, ozet) in enumerate(kayit["desenler"]):
        for rel in sorted(ozet_aday.get((n, ozet), ())):
            bulgular.append((rel, i))
    return sorted(bulgular)


def kol_kaynak_tara(kok=None, ozet_yolu=None):
    kayit = _kayit_ya_da_cik(ozet_yolu)
    if kayit is None:
        return RC_OLCULEMEDI
    bulgular = kaynak_tara(kayit, kok=kok)
    print("taranan kaynak dosyasi: %d" % len(KAYNAK_TARAMA))
    if not bulgular:
        print("temiz: 0 vurus (izlenen kaynaklarda duz metin yasakli ad YOK).")
        return RC_TEMIZ
    for rel, no in bulgular:
        print("  * ICERIK SIZINTISI: %s dosyasinda gizli desen #%d DUZ METIN gecti. "
              "(Eslesen metin BILEREK yazilmiyor.) Ornekleri UYDURMA adla degistir."
              % (rel, no), file=sys.stderr)
    print("SIZINTI: %d vurus" % len(bulgular), file=sys.stderr)
    return RC_SIZINTI


def kol_menzil(menzil, kok=None, ozet_yolu=None, maskeli=True):
    kayit = _kayit_ya_da_cik(ozet_yolu)
    if kayit is None:
        return RC_OLCULEMEDI
    mesajlar, hata = menzil_mesajlari(menzil, kok=kok)
    if mesajlar is None:
        print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI
    toplam = 0
    for i, mesaj in enumerate(mesajlar):
        for k in mesaj_kusurlari(mesaj_govdesi(mesaj), kayit, maskeli=maskeli):
            toplam += 1
            print("  [mesaj %d] %s" % (i, k))
    print("taranan: %d mesaj · bulgu: %d" % (len(mesajlar), toplam))
    return RC_SIZINTI if toplam else RC_TEMIZ


# ===========================================================================
# KABUL BATARYASI (`--kendini-test`)
# ===========================================================================
# 🔴 FIKSTURLERDE GERCEK YASAKLI AD YOKTUR — UYDURMA adlar kullanilir. Gercek adi
# teste yazmak, kapinin engellemek icin var oldugu seyi IZLENEN bir dosyaya yazmak
# olurdu. Testin olctugu sey MEKANIZMADIR (normalize + aday + ozet + fail-closed),
# hangi adin yasakli oldugu DEGIL. Uydurma adlar `--desen-yaz` ile gecici bir ozet
# artefaktina donusur; boylece uretim yolu da AYNI kosumda sinanir.
#
# `gizlivitrin` UYDURMA BIR VITRIN GOVDESIDIR ve ozet artefaktina GIRER: alan adi
# ekseninin "host'un KENDISI gizli desen" kolunu (J3/J4) gercek uretim yoluyla
# olcebilmek icin gereklidir. Gercek vitrin adiyla HICBIR ilgisi yoktur.
_UYDURMA = ("Zorbacix", "HayaliVitrin", "gizlivitrin.example", "gizlivitrin")

# Gercek katalogdan ornekleme (yanlis-pozitif nobeti). Bunlar SATILAN URUN
# MARKALARIDIR: sitede zaten gorunurler, commit mesajinda gecmeleri SIZINTI DEGILDIR.
_KATALOG_MARKALARI = (
    "Ford", "BMW", "Volkswagen", "Toyota", "Mercedes", "Renault", "Peugeot", "Volvo",
    "Opel", "Citroen", "Audi", "Skoda", "Focus", "Honda", "Suzuki", "Yamaha", "Nissan",
    "F-150", "Fiesta", "Mitsubishi", "Golf", "Maverick", "Ranger", "Dacia", "Transit",
    "E46", "Mustang", "Tacoma", "Mondeo", "Corsa", "NGK", "E36", "Seat", "Land Rover",
    "Fiat", "Vauxhall", "Octavia", "Hyundai", "Explorer", "E30", "Porsche", "R1200GS",
    "Alfa Romeo", "Fusion", "Astra", "Passat", "Escape", "Duster", "Bronco", "Corolla",
    "Champion", "Evinrude", "Mercury", "Kawasaki", "Bosch",
)


def _gecici_kayit(tmp, adlar=_UYDURMA, dongu=ASGARI_DONGU):
    """Uydurma adlardan gecici ozet artefakti uret; (yol, kayit) dondur."""
    kaynak = os.path.join(tmp, "desenler.txt")
    with open(kaynak, "w", encoding="utf-8") as f:
        f.write("# uydurma fikstur adlari\n")
        for ad in adlar:
            f.write(ad + "\n")
    hedef = os.path.join(tmp, "ozetler.json")
    sayi, hata = desen_yaz(kaynak, hedef, dongu=dongu)
    if hata:
        raise AssertionError("fikstur artefakti uretilemedi: %s" % hata)
    kayit, hata = ozet_kaydi_yukle(hedef)
    if kayit is None:
        raise AssertionError("fikstur artefakti okunamadi: %s" % hata)
    return hedef, kayit, sayi


def kendini_test():
    """Kabul bataryasi. Cikis 0 = hepsi yesil."""
    import shutil as _shutil
    import tempfile
    import time

    iddia = []

    def kontrol(ad, sonuc, tani=""):
        iddia.append((ad, bool(sonuc), tani))

    tmp = tempfile.mkdtemp(prefix="pruvo-cm-")
    try:
        ozet_yolu, kayit, desen_sayisi = _gecici_kayit(tmp)
        kirmizi = _UYDURMA[0]
        vitrin = _UYDURMA[1]

        def kusur(metin, maskeli=False):
            return mesaj_kusurlari(mesaj_govdesi(metin), kayit, maskeli=maskeli)

        # ---- A) AD EKSENI ---------------------------------------------------
        kontrol("A0 artefakt uretildi (uydurma ad -> ozet)", desen_sayisi >= 3,
                "desen=%d" % desen_sayisi)
        kontrol("A1 duz yasakli ad KIRMIZI", kusur("%s partisi eklendi" % kirmizi))
        kontrol("A2 buyuk/kucuk harf farki KIRMIZI", kusur(kirmizi.upper() + " partisi"))
        kontrol("A3 Turkce ek + kesme isareti KIRMIZI",
                kusur("%s'nun stok listesi guncellendi" % kirmizi))
        kontrol("A4 Turkce harf varyanti KIRMIZI",
                kusur(kirmizi.replace("c", "ç").replace("i", "ı") + " partisi"))
        kontrol("A5 AYRIK yazilmis bitisik ad KIRMIZI (sikistirilmis akis)",
                kusur("hayali vitrin stok eslesmesi"))
        kontrol("A6 satir ortasinda/noktalamayla cevrili KIRMIZI",
                kusur("parti (%s) — 100 urun" % kirmizi))
        kontrol("A7 temiz mesaj YESIL",
                not kusur("tedarikci partisi: marin buji stok+fiyat eslesmeli (100 urun)"))
        kontrol("A8 near-miss (desenin ONEKI) YESIL — kural DAR",
                not kusur("%s partisi" % kirmizi[:-2]))
        kontrol("A9 ilgisiz uzun mesaj YESIL",
                not kusur("altkategori alani bos birakildi; mailbox'ta KraL'a bildirildi. "
                          "Evinrude-ozel 21 satir + stok-disi 30 satir elendi."))

        # ---- B) MARKA YANLIS-POZITIFI --------------------------------------
        marka_yesil = 0
        marka_kirmizi = []
        for marka in _KATALOG_MARKALARI:
            m = ("%s marin buji parti: stok+fiyat eslesmeli (100 urun), "
                 "%s uyumlu altkategori bos" % (marka, marka))
            if kusur(m):
                marka_kirmizi.append(marka)
            else:
                marka_yesil += 1
        kontrol("B1 katalog markalari YANLIS-POZITIF URETMEZ (%d/%d yesil)"
                % (marka_yesil, len(_KATALOG_MARKALARI)),
                not marka_kirmizi, "kirmizi yananlar: %r" % (marka_kirmizi,))

        # ---- C) ALAN ADI EKSENI --------------------------------------------
        kontrol("C1 taninmayan alan adi KIRMIZI", kusur("kaynak: gizlivitrin.com/urunler"))
        kontrol("C2 taninmayan e-posta alani KIRMIZI", kusur("iletisim: satis@gizlivitrin.com"))
        kontrol("C3 https URL'li taninmayan host KIRMIZI",
                kusur("bkz https://gizlivitrin.com/liste"))
        kontrol("C4 PUBLIC alan adi YESIL (pruvo3d.com)",
                not kusur("canli dogrulama: https://pruvo3d.com/urun/x/ 200"))
        kontrol("C5 commit trailer alani YESIL (anthropic.com)",
                not kusur("islem tamam\n\nCo-Authored-By: Claude Opus 5 "
                          "<noreply@anthropic.com>"))
        kontrol("C6 kaynak dosya adlari YESIL (.py/.md/.json/.yml)",
                not kusur("tools/d1-sync.py + DEVAM.md + urunler.json + deploy.yml "
                          "guncellendi"))
        kontrol("C7 arsiv/uzanti YESIL (paket-v7.tar.gz)",
                not kusur("onizleme/paket-v7.tar.gz R2'ye yuklendi"))
        kontrol("C8 platform alan adi YESIL (thingiverse.com)",
                not kusur("kaynak: https://www.thingiverse.com/thing:123 atif korundu"))
        kontrol("C9 uzantisi GERCEK ccTLD olan dosya adlari YESIL (.so/.pl/.sh)",
                not kusur("libhacim.so + arac.pl + kur.sh yeniden derlendi"))

        # ---- D) TESHIS SIZDIRMAZ -------------------------------------------
        ad_teshis = " ".join(kusur("%s partisi" % kirmizi))
        kontrol("D1 ad teshisi ESLESEN METNI YAZMAZ",
                kirmizi.lower() not in ad_teshis.lower(), ad_teshis[:120])
        # D2/D3 maskeleme kolunu TANINMAYAN (ama gizli desen OLMAYAN) bir host ile
        # olcer. 🔴 NEDEN `gizlivitrin.com` DEGIL: o host artik ozet ekseninden
        # yakalanir ve teshisi ADI HIC YAZMAZ (J5) — yani maskeleme kolundan HIC
        # gecmez. Maskeleme "adi bilinmeyen ama supheli host" hali icindir.
        maskeli = " ".join(kusur("kaynak: bilinmeyensatici.com", maskeli=True))
        kontrol("D2 --ci kolunda alan adi MASKELENIR",
                "bilinmeyensatici" not in maskeli and "b*" in maskeli, maskeli[:120])
        acik = " ".join(kusur("kaynak: bilinmeyensatici.com", maskeli=False))
        kontrol("D3 kanca kolunda alan adi ACIK (yerel teshis)",
                "bilinmeyensatici.com" in acik, acik[:120])

        # ---- E) GIT YORUM SATIRLARI HUKME GIRMEZ ---------------------------
        sablon = ("tedarikci partisi eklendi\n"
                  "# Please enter the commit message for your changes.\n"
                  "# On branch feature/gizlivitrin-com-entegrasyon\n"
                  "# Changes to be committed:\n"
                  "#\tmodified:   tools/%s-ekle.py\n" % kirmizi.lower())
        kontrol("E1 git SABLON yorumlari (dal adi + dosya yolu) hukme GIRMEZ",
                not kusur(sablon), " ".join(kusur(sablon))[:160])
        makas = ("temiz mesaj\n"
                 "# ------------------------ >8 ------------------------\n"
                 "# diff --git a/x b/x\n"
                 "+%s satiri\n" % kirmizi)
        kontrol("E2 MAKAS sonrasi diff govdesi hukme GIRMEZ", not kusur(makas))
        karma = "%s partisi\n# On branch main\n" % kirmizi
        kontrol("E3 yorumlar atilsa da GERCEK govdedeki sizinti YAKALANIR", kusur(karma))

        # ---- F) DESEN KAYNAGI FAIL-CLOSED ----------------------------------
        yok = os.path.join(tmp, "olmayan.json")
        k, h = ozet_kaydi_yukle(yok)
        kontrol("F1 ozet dosyasi YOK -> OLCULEMEDI (fail-closed)", k is None and h)
        bozuk = os.path.join(tmp, "bozuk.json")
        with open(bozuk, "w", encoding="utf-8") as f:
            f.write("{ bu json degil")
        k, _ = ozet_kaydi_yukle(bozuk)
        kontrol("F2 bozuk JSON -> OLCULEMEDI", k is None)
        with open(ozet_yolu, encoding="utf-8") as f:
            iyi = json.load(f)
        for ad, bozma in (
                ("F3 BOS desen listesi", {"desenler": []}),
                ("F4 dusuk dongu", {"dongu": 10}),
                ("F5 taninmayan algoritma", {"algo": "md5"}),
                ("F6 gecersiz tuz", {"tuz": "zz"}),
                ("F7 kisa desen uzunlugu", {"desenler": [{"n": 2, "ozet": "a" * 64}]}),
                ("F8 ozet hex degil", {"desenler": [{"n": 8, "ozet": "kisa"}]})):
            kopya = dict(iyi)
            kopya.update(bozma)
            yol2 = os.path.join(tmp, ad.split()[0] + ".json")
            with open(yol2, "w", encoding="utf-8") as f:
                json.dump(kopya, f)
            k, _ = ozet_kaydi_yukle(yol2)
            kontrol("%s -> OLCULEMEDI (fail-closed)" % ad, k is None)
        # F9: KARAR SABITLEME — gitignore'lu DUZ METIN dosyasinin yoklugu hukme GIRMEZ.
        kontrol("F9 duz metin desen dosyasi YOKKEN eslesme YINE calisir (fail-OPEN "
                "kararinin sabitlenmesi)",
                not os.path.exists(os.path.join(tmp, "yok.txt"))
                and bool(kusur("%s partisi" % kirmizi))
                and not kusur("temiz mesaj"))
        # F10: uretim kolu kaynak YOKKEN yazmaz (fail-closed)
        sayi, hata = desen_yaz(os.path.join(tmp, "yok.txt"), os.path.join(tmp, "c.json"))
        kontrol("F10 --desen-yaz kaynagi YOKKEN artefakt URETMEZ", sayi is None and hata)
        # F11: uretilen artefaktta DUZ AD YOK
        with open(ozet_yolu, encoding="utf-8") as f:
            artefakt = f.read().lower()
        kontrol("F11 uretilen artefaktta duz ad YOK",
                all(a.lower() not in artefakt for a in _UYDURMA))

        # ---- G) GERCEK GIT: SENTETIK DEPODA UCTAN UCA ----------------------
        depo = os.path.join(tmp, "depo")
        os.makedirs(os.path.join(depo, "tools"))
        subprocess.run(["git", "init", "-q", "-b", "main", depo], check=True)
        subprocess.run(["git", "-C", depo, "config", "user.email", "t@example.invalid"],
                       check=True)
        subprocess.run(["git", "-C", depo, "config", "user.name", "Test"], check=True)
        _shutil.copy2(os.path.abspath(__file__),
                      os.path.join(depo, "tools", "commit-mesaji-kapisi.py"))
        _shutil.copy2(ozet_yolu,
                      os.path.join(depo, "tools", "sizinti-desen-ozetleri.json"))
        _shutil.copy2(os.path.join(TOOLS, "commit-mesaji-hook-kur.py"),
                      os.path.join(depo, "tools", "commit-mesaji-hook-kur.py"))

        def yaz(ad, icerik):
            with open(os.path.join(depo, ad), "w", encoding="utf-8") as f:
                f.write(icerik)

        def commit(mesaj, ad):
            yaz(ad, "x\n")
            subprocess.run(["git", "-C", depo, "add", "-A"], check=True)
            return subprocess.run(["git", "-C", depo, "commit", "-m", mesaj],
                                  capture_output=True, text=True)

        def sayi_commit():
            p = subprocess.run(["git", "-C", depo, "rev-list", "--count", "HEAD"],
                               capture_output=True, text=True)
            return int(p.stdout.strip()) if p.returncode == 0 else 0

        # G0 — NEGATIF KONTROL: kanca YOKKEN kapi hicbir sey uretmez.
        p = commit("%s partisi (kanca YOK)" % kirmizi, "a.txt")
        kontrol("G0 kanca YOKKEN sizintili commit GECER (negatif kontrol)",
                p.returncode == 0)
        kontrol("G0b kanca YOKKEN kapi hicbir teshis URETMEZ",
                "COMMIT DURDURULDU" not in (p.stdout + p.stderr)
                and "TEDARIKCI" not in (p.stdout + p.stderr),
                (p.stdout + p.stderr)[:200])

        import importlib.util as _iu
        spec = _iu.spec_from_file_location(
            "pruvo_cm_kur", os.path.join(TOOLS, "commit-mesaji-hook-kur.py"))
        kur_mod = _iu.module_from_spec(spec)
        spec.loader.exec_module(kur_mod)
        rc_kur, kanca = kur_mod.kur(depo, sessiz=True)
        kontrol("G1 kanca kuruldu", rc_kur == 0 and kanca and os.path.isfile(kanca))
        kontrol("G1b kanca CALISTIRILABILIR",
                bool(kanca) and os.access(kanca, os.X_OK))
        kontrol("G1c kurulum IDEMPOTENT (ikinci kosum degistirmez)",
                kur_mod.kur(depo, sessiz=True)[0] == 0
                and kur_mod.kurulu_mu(kanca))

        onceki = sayi_commit()
        p = commit("%s partisi: 100 urun" % kirmizi, "b.txt")
        kontrol("G2 yasakli ad iceren mesajla commit REDDEDILDI (rc!=0)",
                p.returncode != 0, "rc=%d" % p.returncode)
        kontrol("G2b teshis mesaji uretildi",
                "COMMIT ENGELLENDI" in (p.stdout + p.stderr)
                or "COMMIT DURDURULDU" in (p.stdout + p.stderr),
                (p.stdout + p.stderr)[:200])
        kontrol("G2c teshis ESLESEN ADI YAZMADI",
                kirmizi.lower() not in (p.stdout + p.stderr).lower())
        kontrol("G2d commit OLUSMADI", sayi_commit() == onceki)

        p = commit("kaynak: gizlivitrin.com/urunler", "c.txt")
        kontrol("G3 taninmayan alan adiyla commit REDDEDILDI", p.returncode != 0)

        onceki = sayi_commit()
        p = commit("tedarikci partisi: marin buji stok+fiyat eslesmeli (100 urun)",
                   "d.txt")
        kontrol("G4 TEMIZ mesajla commit GECTI (rc=0)", p.returncode == 0,
                (p.stdout + p.stderr)[:200])
        kontrol("G4b commit OLUSTU", sayi_commit() == onceki + 1)

        # G5 — ozet artefakti SILININCE commit DURUR (uctan uca fail-closed)
        artefakt_yolu = os.path.join(depo, "tools", "sizinti-desen-ozetleri.json")
        os.rename(artefakt_yolu, artefakt_yolu + ".gizli")
        p = commit("tamamen temiz bir mesaj", "e.txt")
        kontrol("G5 ozet artefakti YOKKEN temiz commit bile DURUR (fail-closed)",
                p.returncode != 0, "rc=%d %s" % (p.returncode,
                                                 (p.stdout + p.stderr)[:160]))
        os.rename(artefakt_yolu + ".gizli", artefakt_yolu)

        # G6 — KAPI BETIGI SILININCE commit DURUR (kancanin ON-KOSULU fail-closed mi).
        # Bu, kancayi olduren en ucuz mutanttir: kapi betigi yoksa "yapacak bir sey yok"
        # deyip gecmek. Blokta `exit 1` VARDIR ve bu iddia onu nobetler.
        kapi_yolu = os.path.join(depo, "tools", "commit-mesaji-kapisi.py")
        os.rename(kapi_yolu, kapi_yolu + ".gizli")
        p = commit("tamamen temiz bir mesaj (kapi betigi YOK)", "g.txt")
        kontrol("G6 kapi BETIGI yokken commit DURUR (kanca on-kosulu fail-closed)",
                p.returncode != 0, "rc=%d %s" % (p.returncode,
                                                 (p.stdout + p.stderr)[:160]))
        os.rename(kapi_yolu + ".gizli", kapi_yolu)

        # G7 — kanca KALDIRILINCA hicbir sey uretilmez (negatif kontrol, ikinci yon)
        kur_mod.kur(depo, kaldir=True, sessiz=True)
        p = commit("%s partisi (kanca KALDIRILDI)" % kirmizi, "f.txt")
        kontrol("G7 kanca KALDIRILINCA sizintili commit yine GECER (negatif kontrol)",
                p.returncode == 0)
        kontrol("G7b kanca KALDIRILINCA kapi hicbir teshis URETMEZ",
                "COMMIT" not in (p.stdout + p.stderr).replace("commit", "")
                or "ENGELLENDI" not in (p.stdout + p.stderr),
                (p.stdout + p.stderr)[:160])

        # ---- H) CI KOLU MENZIL COZUMU --------------------------------------
        p = subprocess.run(["git", "-C", depo, "rev-list", "HEAD"],
                           capture_output=True, text=True)
        shalar = p.stdout.split()
        m, kaynak, hata = ci_mesajlari(
            kok=depo, ortam={"GITHUB_SHA": shalar[0]},
            yuk={"before": shalar[-1], "after": shalar[0]})
        kontrol("H1 CI kolu git menzilini cozdu", m is not None and hata is None,
                str(hata))
        m2, kaynak2, _ = ci_mesajlari(
            kok=depo, ortam={},
            yuk={"before": SIFIR_SHA, "after": "",
                 "commits": [{"message": "%s partisi" % kirmizi}]})
        kontrol("H2 git menzili COZULEMEZKEN olay yukune duser",
                m2 and "olay yuku" in (kaynak2 or ""))
        m3, _, hata3 = ci_mesajlari(kok=depo, ortam={}, yuk={})
        kontrol("H3 hicbir kaynak yokken FAIL-CLOSED (mesaj YOK + hata VAR)",
                m3 is None and bool(hata3))

        # ---- I) SURE OLCUMU (kanca kullanici bekletmemeli) -----------------
        # 🔴 ESIK MUTLAK MS DEGIL, "REFERANS MAKINE MS"IDIR — OLCUMLE DUZELTILDI
        # (1 Agu 2026). OLCULEN ARIZA: bu iki iddia bir Apple Silicon gelistirici
        # makinesinde kalibre edildi ve GitHub `ubuntu-latest` kosucusunda HIC
        # yesil yanmadi — job kurulusundan (40367736) itibaren HER kosumda kirmizi:
        #   I1  yerel 1748/1754/1782/1783/1789 ms   ·  CI 6289/6302/6416 ms
        #   I2  yerel  143/ 144/ 145/ 146/ 147 ms   ·  CI  511/ 525/ 522 ms
        # Kosum-ici degisim her iki makinede de %2'nin ALTINDA, oran ise iki
        # olcumde de AYNI (3,58x) -> kosucu gurultusu ya da bizim kodumuzda bir
        # gerileme DEGIL, sabit bir donanim hizi farki.
        # NEDEN NORMALIZE, NEDEN KOR GENISLETME DEGIL: kapinin suresinin %96,9'u
        # KACINILMAZ PBKDF2 cagrisidir (700 jetonda 4303 cagri x 0,4008 ms = 1725 ms
        # / olculen 1780 ms) — yani sure = YAPILAN IS x MAKINE HIZI. Esigi kor bir
        # sekilde 12 000 ms'ye cekmek "kanca kullaniciyi bekletmesin" iddiasini
        # ANLAMSIZLASTIRIRDI. Ustelik mutlak esik TERS yonde de bozuktu: gelistirici
        # makinesinde 1780/3000, yani gercek bir %68'lik gerilemeyi bile YESIL
        # yakardi. Bu yuzden olculen sure, o anki makinenin OLCULEN PBKDF2 birim
        # maliyetiyle referans makineye cevrilir: 3000/400 ms butcesi ve ANLAMI
        # aynen kalir, ama her makinede AYNI seyi (yapilan isi) olcer.
        # Cevrim MODUL DUZEYINDEKI `referans_ms()`tir (bu bolumun disinda tanimli):
        # I1/I2 ve I4 AYNI fonksiyonu cagirir, yani asagidaki enjeksiyon testi
        # gercek kod yolunu olcer — testin kendi icinde yeniden yazilmis bir kopyayi
        # DEGIL (olculdu: kopya yazildiginda olcegi olduren mutant SAG KALIYORDU).
        # 🔴 KALIBRASYON OLCUM PENCERESINE SERPISTIRILIR — OLCULEN ARIZA: ilk taslakta
        # birim maliyet SADECE BASTA ve 3 partinin EN IYISI (min) olarak olculuyordu.
        # tools/commit-mesaji-mutasyon.py kosumunda (25 ardisik kosum, makine isinip
        # yavasladi) bu ILGISIZ bir mutantta SAHTE-KIRMIZI uretti: kalibrasyon hizli
        # bir pencere yakalayip 1,07x dedi, oysa kapi kosumu sirasinda makine ~1,6x
        # yavaslamisti (ham 3817 ms / normalde 2352 ms). Yani hata kapida degil,
        # OLCU ALETINDEYDI: kisa bir pencerede olculen birim, uzun bir pencerede
        # kosan kapiyi temsil etmiyordu.
        # COZUM: partiler olcumun ONUNE, ARASINA ve SONUNA serpistirilir ve ORTANCA
        # alinir. Ortanca, "min"in aksine gecici bir hizli pencereye kanmaz; "max"in
        # aksine tek bir yavas partiyi butun olcume yaymaz.
        partiler = []

        def _parti():
            t = time.perf_counter()
            for i in range(100):
                _ozetle("olcum%08d" % i, kayit["tuz"], kayit["dongu"])
            partiler.append((time.perf_counter() - t) * 1000 / 100)

        def _birim():
            sirali = sorted(partiler)
            n = len(sirali)
            if not n:
                return 0.0
            return sirali[n // 2] if n % 2 else (sirali[n // 2 - 1] + sirali[n // 2]) / 2

        def _sure_ms(mesaj):
            t = time.perf_counter()
            kusur(mesaj)
            return (time.perf_counter() - t) * 1000

        uzun = " ".join(["kelime%d" % i for i in range(700)])
        orta = " ".join(["kelime%d" % i for i in range(50)])
        _parti()
        _parti()
        ham = _sure_ms(uzun)
        _parti()
        ham_orta = _sure_ms(orta)
        _parti()
        # Tek birim, TUM olcum penceresine yayilmis 4 partinin ORTANCASI.
        birim = _birim()
        yavaslik = (birim / REFERANS_BIRIM_MS) if birim else 0.0
        sure = referans_ms(ham, birim)
        sure_orta = referans_ms(ham_orta, birim)
        kontrol("I1 700 jetonlu (EN KOTU gercek mesaj) kapi < 3000 referans-ms "
                "[ham %.0f ms · makine %.2fx · %.0f referans-ms]"
                % (ham, yavaslik, sure),
                0 < sure < 3000, "%.0f referans-ms (ham %.0f ms)" % (sure, ham))
        kontrol("I2 50 jetonlu (ORTANCA gercek mesaj) kapi < 400 referans-ms "
                "[ham %.0f ms · %.0f referans-ms]" % (ham_orta, sure_orta),
                0 < sure_orta < 400,
                "%.0f referans-ms (ham %.0f ms)" % (sure_orta, ham_orta))
        # I3 — MAKINEDEN TAMAMEN BAGIMSIZ IS TAVANI. I1/I2 sure eksenidir; bu iddia
        # SURE OLCMEZ, YAPILAN ISI (PBKDF2 cagri sayisi) sozlesmesine karsi olcer.
        # SOZLESME: `adaylar()` her desen uzunlugu icin, IKI akista (bosluklu +
        # sikistirilmis), KELIME BASINA en fazla BIR aday uretir -> tavan
        # 2 x jeton x uzunluk_sayisi. Kelime-basi kisiti kaybolursa (ya da bir ucuncu
        # akis eklenirse) bu tavan ASILIR ve iddia her makinede KIRMIZI yanar.
        # 🔴 NEDEN "DOGRUSALLIK ORANI" DEGIL: onceki taslakta iddia 700/50 aday
        # ORANININ < 20x kalmasiydi. OLCULDU: aday sayisi TANIMI GEREGI dogrusaldir
        # (adaylar SABIT uzunlukta dilimlerdir, sayilari konum sayisiyla artar), yani
        # o oran gercek bir O(n^2) mutasyonunda bile 15,4x'te kaldi -> iddia ASLA
        # kirmizi yanamayan bir TAUTOLOJIYDI. Tavan bicimi ayni mutasyonu yakalar
        # (24 935 > 5 600).
        _uzunluklar = sorted({n for n, _ in kayit["desenler"]})
        aday_uzun = sum(len(adaylar(uzun, n)) for n in _uzunluklar)
        tavan = 2 * 700 * len(_uzunluklar)
        kontrol("I3 PBKDF2 cagri sayisi IS TAVANININ altinda (2 akis x kelime basi x "
                "desen uzunlugu) [%d / tavan %d]" % (aday_uzun, tavan),
                0 < aday_uzun <= tavan, "%d > %d" % (aday_uzun, tavan))
        # I4 — HUKUM DONANIMDAN BAGIMSIZ MI? Olculen kosucu yavasligi ENJEKTE edilir
        # (makineyi mesgul etmeye calismak olculdu: 24 CPU yakiciyla bile yavaslama
        # yalniz %4'tu, yani tekrarlanabilir bir CI taklidi DEGIL). Tekduze daha yavas
        # bir CPU'da kapi suresi de birim maliyet de AYNI katsayiyla buyur.
        def _hukum(ham_ms, birim_ms):
            return 0 < referans_ms(ham_ms, birim_ms) < 3000

        kontrol("I4 tekduze yavaslamada HUKUM DEGISMEZ (0,25x / 3,58x=olculen CI / "
                "10x / 40x enjekte)",
                all(_hukum(ham * k, birim * k) == _hukum(ham, birim)
                    for k in (0.25, 3.58, 10.0, 40.0)))
        # 🔴 IKINCI YON SART: yalniz KAPI yavaslarsa (birim maliyet SABIT) bu gercek
        # bir gerilemedir ve KIRMIZI yanmalidir. Bu iddia olmadan "her zaman yesil"
        # veren anlamsiz bir olcu birimi yazmis olurduk — sure butcesinin AMACI
        # (yavas kanca -> `--no-verify` aliskanligi) burada korunur.
        kontrol("I4b yalniz KAPI yavaslarsa (birim SABIT, 3x) KIRMIZI yanar — sure "
                "butcesi hala yuk tasiyor",
                _hukum(ham, birim) and not _hukum(ham * 3.0, birim))

        # ---- J) ALAN ADI EKSENI: YANLIS-POZITIF vs TEDARIKCI VITRINI -------
        # 🔴 IKI YONLU OLCUM. Yon 1: gercek katalog markalarinin alan adi hali YESIL
        # olmali (yoksa mesru is engellenir -> `--no-verify` aliskanligi -> o an TUM
        # eksenler kapanir). Yon 2: tedarikci/vitrin alan adi HALA KIRMIZI olmali.
        gercek_markalar = katalog_markalari()
        kontrol("J0 katalog marka kumesi urunler.json'dan turedi [%d marka]"
                % len(gercek_markalar), len(gercek_markalar) >= 100,
                "%d marka" % len(gercek_markalar))
        # Toplu suzgec SAF bicim+marka kuralini olcer (ozet ekseni disarida): 1291
        # marka icin ozetleme kabul bataryasini dakikalarca uzatirdi. Ozet ONCELIGI
        # ayrica J3/J4'te GERCEK artefaktla olculur.
        onceki_kirmizi, yeni_kirmizi = [], []
        for marka in sorted(gercek_markalar):
            m = "muadil parca eklendi, bkz https://%s.com/parts" % marka
            if alan_adi_isabetleri(m, None, frozenset()):
                onceki_kirmizi.append(marka)
            if alan_adi_isabetleri(m, None, gercek_markalar):
                yeni_kirmizi.append(marka)
        kontrol("J1 katalog marka alan adlari YESIL [%d/%d]"
                % (len(gercek_markalar) - len(yeni_kirmizi), len(gercek_markalar)),
                not yeni_kirmizi, "kirmizi kalan: %r" % (yeni_kirmizi[:5],))
        # J2 olcumu ANLAMLI kilar: muafiyet olmasa bu kume KIRMIZI yanardi. Tek
        # istisna `google` — PUBLIC_ALAN'da zaten var (platform alani ve ayni zamanda
        # katalog markasi), yani muafiyet ONCESI de yesildi. Beklenen: N-1.
        kontrol("J2 olcum ANLAMLI: muafiyet OLMADAN kume KIRMIZI yaniyordu "
                "[%d/%d; tek istisna PUBLIC_ALAN'daki 'google']"
                % (len(onceki_kirmizi), len(gercek_markalar)),
                len(onceki_kirmizi) == len(gercek_markalar) - 1,
                "%d/%d" % (len(onceki_kirmizi), len(gercek_markalar)))
        vitrin = "kaynak: https://gizlivitrin.com/urunler"
        kontrol("J3 tedarikci vitrini alan adi HALA KIRMIZI (ozet ekseninden)",
                bool(alan_adi_isabetleri(vitrin, kayit, gercek_markalar)))
        # 🔴 EN KRITIK IDDIA: muafiyet listesine vitrin adi (kazara ya da KASTEN)
        # girse BILE ozet onceligi muafiyeti EZER -> muafiyet bir BYPASS'a donusemez.
        zehirli = alan_adi_isabetleri(
            vitrin, kayit, frozenset(set(gercek_markalar) | {"gizlivitrin"}))
        kontrol("J4 vitrin adi MARKA MUAFIYETINE sokulsa bile ozet onceligi EZER "
                "(muafiyet bypass'a donusemez)",
                bool(zehirli) and zehirli[0][2] is not None, repr(zehirli)[:120])
        kontrol("J5 vitrin teshisi ALAN ADINI YAZMAZ (kanca kolunda BILE)",
                "gizlivitrin" not in " ".join(kusur(vitrin)).lower(),
                " ".join(kusur(vitrin))[:140])
        kontrol("J6 katalogda OLMAYAN taninmayan host HALA KIRMIZI (fail-closed)",
                bool(alan_adi_isabetleri("kaynak: bilinmeyensatici.com/liste",
                                         kayit, gercek_markalar)))
        kontrol("J7 urunler.json YOKKEN muafiyet KAPALI (bos kume = KATI davranis)",
                katalog_markalari(os.path.join(tmp, "yok.json")) == frozenset())

        # ---- K) BAYAT ADIM ADI NOBETI --------------------------------------
        # 🔴 OLCULEN ARIZA: deploy.yml adim adi "56 iddia" diyordu, gercek 58'di.
        # Bayat sayi kosumun neyi olctugu hakkinda YANLIS bilgi verir ve kimse
        # duzeltmez. COZUM: sayi adim ADINDAN CIKARILDI (gercek sayiyi bu betik
        # "SONUC: N/N" satiriyla KENDI basar) ve tekrari bu iddia engeller.
        yml = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
        try:
            with open(yml, encoding="utf-8") as f:
                yml_metin = f.read()
        except OSError:
            yml_metin = ""
        kontrol("K0 deploy.yml okunabildi (izlenen dosya; yoklugu OLCULEMEDI'dir)",
                bool(yml_metin))
        job = yml_metin.split("\n  mesaj-nobeti:", 1)[-1].split("\n  # ", 1)[0]
        adlar = re.findall(r"- name:.*", job)
        bayat = [a for a in adlar if re.search(r"\d+\s+iddia", a)]
        kontrol("K1 mesaj-nobeti adim ADLARINDA sabitlenmis iddia SAYISI YOK "
                "(bayatlayamaz) [%d adim]" % len(adlar),
                bool(yml_metin) and bool(adlar) and not bayat, "bayat: %r" % (bayat,))
        kontrol("K2 mesaj-nobeti job'u bu betigi GERCEKTEN kosuyor (iki kol)",
                "tools/commit-mesaji-kapisi.py --kendini-test" in job
                and "tools/commit-mesaji-kapisi.py --ci" in job)
    finally:
        _shutil.rmtree(tmp, ignore_errors=True)

    kirmizilar = [(a, t) for a, s, t in iddia if not s]
    for ad, sonuc, tani in iddia:
        print("  %s %s%s" % ("✅" if sonuc else "❌", ad,
                             ("  [%s]" % tani) if (tani and not sonuc) else ""))
    print("SONUC: %d/%d iddia yesil" % (len(iddia) - len(kirmizilar), len(iddia)))
    return RC_TEMIZ if not kirmizilar else RC_SIZINTI


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("--commit-msg", metavar="DOSYA")
    ap.add_argument("--ci", action="store_true")
    ap.add_argument("--menzil", metavar="A..B")
    ap.add_argument("--son", type=int, metavar="N")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--kaynak-tara", action="store_true",
                    help="izlenen nobetci kaynaklarinda DUZ METIN yasakli ad ara")
    ap.add_argument("--desen-yaz", action="store_true")
    ap.add_argument("--desen-kaynak", metavar="YOL")
    ap.add_argument("--ozet-dosya", metavar="YOL")
    ap.add_argument("--acik", action="store_true",
                    help="menzil/son kolunda alan adini MASKELEME (yerel teshis)")
    a = ap.parse_args(argv)

    if a.desen_yaz:
        sayi, hata = desen_yaz(a.desen_kaynak, a.ozet_dosya)
        if hata:
            print("HATA: %s" % hata, file=sys.stderr)
            return RC_OLCULEMEDI
        print("ozet artefakti yazildi: %d desen (duz ad YAZILMADI)" % sayi)
        return RC_TEMIZ
    if a.kendini_test:
        return kendini_test()
    if a.kaynak_tara:
        return kol_kaynak_tara(ozet_yolu=a.ozet_dosya)
    if a.commit_msg:
        return kol_commit_msg(a.commit_msg, a.ozet_dosya)
    if a.ci:
        return kol_ci(ozet_yolu=a.ozet_dosya)
    if a.menzil:
        return kol_menzil(a.menzil, ozet_yolu=a.ozet_dosya, maskeli=not a.acik)
    if a.son:
        return kol_menzil("-%d" % a.son, ozet_yolu=a.ozet_dosya, maskeli=not a.acik)
    ap.print_help()
    return RC_OLCULEMEDI


if __name__ == "__main__":
    sys.exit(main())
