#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urunler.json -> Cloudflare D1 (katalog + arama indeksi). FAZ 1.

  python3 tools/d1-sync.py --sema     # semayi kur (bir kez / degisince)
  python3 tools/d1-sync.py            # DIFF-UPSERT: sadece degisen/yeni/silinen
  python3 tools/d1-sync.py --kuru     # hicbir sey yazma, ne yapacagini soyle
  python3 tools/d1-sync.py --durum    # SAYI + SEMA + ICERIK (urun_hash) + TURETILMIS KOLON
  python3 tools/d1-sync.py --durum --hizli   # yalniz SAYI + SEMA (icerik + turetilmis ATLANIR)
  python3 tools/d1-sync.py --kendini-test    # OFFLINE kabul testi (sqlite; D1'e dokunmaz)

*** NEDEN GERI-OKUMA (write-verify) VAR — 31 Tem, OLCULMUS OLAY ***
Tek alan degisimi (bir urunun kategori'si) push edildi; pre-push hook d1-sync'i kosturdu,
arac "degisen: 1 / 5 satir yazildi" BASTI ve exit 0 dondu — ama canli D1'deki deger ESKI
KALDI. Hemen ardindan --kuru yine "degisen: 1" diyordu: arac kendi yazmadigini goruyor ama
BASARI raporlamisti. Ayni komut elle tekrarlaninca yazma tuttu (ARALIKLI ariza).
  🔴 Hatanin sinifi SESSIZ: site urunu dogru gosterir (urunler.json'dan okur), Ege (WhatsApp
  botu) D1'den okudugu icin BAYAT veri gorur -> musteri urun varken kaybedilir, hicbir yerde
  alarm calmaz.
  🔴 --durum'un SAYI ekseni bunu GOREMEZ: toplam satir sayisi silme/eklemede degisir, ALAN
  GUNCELLEMESINDE DEGISMEZ. merge-kapisi'nin zorunlu "D1 teyidi" adimi bu vakada YESIL yaniyordu.
Bu yuzden iki eksen eklendi:
  (1) YAZMA SONRASI GERI-OKUMA — yazilan her satir KENDI anahtariyla geri okunur ve YAZILAN
      ALAN DEGERLERI karsilastirilir; tutmazsa BIR KEZ yeniden denenir, yine tutmazsa arac
      SIFIR-DISI cikar ve NE'nin yazilmadigini (id + alan + beklenen/bulunan) basar.
      Wrangler'in "N satir yazildi" ciktisi artik IDDIA'dir, dogrulanmadan basari sayilmaz.
  (2) --durum ICERIK EKSENI — sayi degil, urun_hash duzeyinde D1 ↔ urunler.json karsilastirmasi.
  (3) --durum TURETILMIS KOLON EKSENI (6 Agu) — urun_hash'in KAPSAMADIGI kolonlar
      (konfigur/taban_fiyat/marka_kanon/model_kanon/marka_arama) hedefli UPDATE ile
      senkronlanir; hash onlari OZETLEMEDIGI icin ICERIK ekseni de KORDUR. Olculen vaka:
      canli `marka_arama`da Honda 1898 iken olmasi gereken 1979 idi ve UC EKSEN DE YESIL
      yaniyordu. Eksen, kolonu URETEN govdeyi calistirir (ikinci yuklem YOK) ve fail-closed
      calisir: uretilemezse OLCULEMEDI, asla yesil. Ayrintili gerekce: turetilmis_eksen().

*** NEDEN DIFF-UPSERT SART ***
D1 ucretsiz katmanda GUNDE 100.000 SATIR YAZMA siniri var (okuma 100M, depolama 5 GB
— onlar bol). Her push'ta tam rebuild yazilirsa 50k urunde 2 rebuild limiti bitirir,
D1 hata dondurmeye baslar ve ARAMA COKER. Bu yuzden ürünün icerik ozeti (hash)
tutulur; ozeti degismeyen urune DOKUNULMAZ. Gunde ~600 yeni urun = ~600 yazma.

*** SIRA (seq) TUZAGI ***
`seq` yalniz urunler.json'daki kanonik sirayi temsil eden TAM SAYIDIR. Normalizasyon
siraya genis tam-sayi araliklari verir; yeni urun bu araliga tam sayiyla girer. Aralik
tukenirse kesir uretmek yerine fail-loud durur ve `--seq-normalize` ister.
"""

import argparse
import atexit
import errno
import fcntl
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
from git_ortami import git_ortami, sentetik_git
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arama
# SILME KARANTINASI (11 Agu 2026 vakasi). BAYRAKSIZ DAVRANIS DEGISMEZ: modul yalniz
# `--karantina-damgasi` verildiginde devreye girer (uzlastirici kolu). Pre-push kancasi
# ve CI senkron adimi bayraksiz kosar -> bugunku davranis BAYT AYNI.
import uzlastirici_karantina

# KONFIGUR dogrulama + sayi normalizasyonu TEK KAYNAK: konfigur-bundle-kapisi.py. Ayni
# fonksiyonlar hem Worker bundle artefaktini (shop/src/konfigurlar.js) hem D1 kolonunu
# uretir -> iki ayna INSAATAN ayrisamaz. Modul adi tire icerdigi icin duz `import` ile
# yuklenemez; importlib gerekir.
_KBK_YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "konfigur-bundle-kapisi.py")
_kbk_spec = importlib.util.spec_from_file_location("konfigur_bundle_kapisi", _KBK_YOL)
kbk = importlib.util.module_from_spec(_kbk_spec)
_kbk_spec.loader.exec_module(kbk)

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(KOK, "urunler.json")
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
# PARAMETRIK TABAN FIYAT kaynagi = jenerator/urunler/<id>.json "tabanFiyatTL" (tam sayi TL).
# TEK KAYNAK, build.py uret_taban_fiyatlar() ile AYNI dosyalari okur. Bu dizin GIT'TE
# (izlenir) -> hem yerelde hem GitHub Actions'ta erisilir. taban-fiyatlar.js DEGIL: o
# build.py ciktisi + gitignore -> CI'da/temiz checkout'ta olmayabilir (bayat/eksik).
JEN_URUN_DIR = os.path.join(KOK, "jenerator", "urunler")
# GIZLI kaynak kaydi (gitignore). "baski" alani (uretim ayar onerisi) buradan D1'e
# tasinir — PUBLIC urunler.json'a YAZILMAZ. Dosya yoksa (baska makine/CI) baski bos kalir.
KAYNAKLAR = os.path.join(KOK, ".urun-kaynaklari.json")
# YAZICI KILIDI (surecler-arasi). Ayni aile: .urunler.lock / .devam.lock / .yedek.lock
# (CLAUDE.md "ORTAK CALISMA"); 0 bayt degil, JSON bir SAHIP KAYDI tasir.
KILIT_ADI = "pruvo-d1-sync.lock"        # ORTAK git dizininde (tum worktree'ler paylasir)
KILIT_YEDEK_ADI = ".d1-sync.lock"       # git YOKSA geri cekilme: KOK'te (gitignore'da)


def _kilit_yolu(kok=None):
    """YAZICI kilidinin CAPASI. Doner: mutlak kilit dosyasi yolu.

    🔴 KAPSAM BIRIMI — `.urunler.lock` DESENI BURAYA KOREKORANE KOPYALANAMAZ.
    `urunler.json` HER CALISMA AGACINDA AYRI bir dosyadir; onu KOK'teki bir kilitle
    korumak DOGRU birimdir. Canli D1 (`pruvo-katalog`) ise TEK ve GLOBAL bir kaynaktir:
    ana agac ile `.claude/worktrees/*` agaclari AYRI KOK'lere sahiptir, dolayisiyla
    KOK'e capalanan bir kilit HER AGACA AYRI bir kilit dosyasi verir ve iki yazici
    AYNI canli veritabanina ayni anda yazar — kapatmaya calistigimiz arizanin ta
    kendisi. Olculen vakalar zaten merge/nobet turlarindan, yani WORKTREE'lerden cikti
    (K48: ucustaki yazici PID 86177). Kilit bu yuzden `git rev-parse --git-common-dir`e
    capalanir: bu dizin ana agac VE tum linkli worktree'ler icin AYNIDIR.
    Olculdugu yer: tools/d1-yazici-kilidi-test.py G ekseni (sentetik depo + gercek
    `git worktree add` + iki agactan GERCEK yaris).

    Ortam `git_ortami()` ile temizlenir: pre-push kancasi MUTLAK `GIT_DIR` ihrac eder
    ve miras baglam depo kesfini yanlis agaca capalar ([[kanca-git-dir-kok-cozumu]]).

    GERI CEKILME: git yoksa/depo degilse KOK'teki `.d1-sync.lock`. Bu bir GEVSEME
    DEGIL, olcunun MUMKUN OLMADIGI haldir (or. mutasyon aynasi, tarball checkout);
    o halde de kilit ALINIR, yalnizca kapsami tek agaca daralir.
    """
    kok = KOK if kok is None else kok
    try:
        r = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=kok,
                           capture_output=True, text=True, timeout=10,
                           env=git_ortami())
        ortak = r.stdout.strip()
        if r.returncode == 0 and ortak:
            if not os.path.isabs(ortak):
                ortak = os.path.join(kok, ortak)
            ortak = os.path.realpath(ortak)
            if os.path.isdir(ortak):
                return os.path.join(ortak, KILIT_ADI)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return os.path.join(kok, KILIT_YEDEK_ADI)


KILIT = _kilit_yolu()

# DB'yi ADIYLA cagiriyoruz (UUID DEGIL). NEDEN (olculdu 2026-07-22, T5): `npx wrangler@4`
# YUZER pin -> CI o an 4.86.0'a cozuyordu; 4.86.0'da `d1 execute <arg>` argumani AD olarak
# aranir, UUID verilince "Couldn't find DB with name '<uuid>'" -> exit 1: senkron ADIMI olu
# kaldi (Ege bayat katalog goruyordu). Yerelde wrangler 4.112.0+'ta UUID de calistigi icin
# ayrisma gizli kaldi. AD "pruvo-katalog" ise 4.86.0 VE 4.112.0'da (+ bos dizinde, wrangler.toml
# YOK iken) exit 0 -> surumden BAGIMSIZ. Bu yuzden execute yolu ADI kullanir; surum pini GEREKMEZ.
# wrangler.toml zaten gerekmiyordu (ad da UUID de hesap-duzeyinde --remote cozulur); asil sebep
# surum ayrismasiydi. Actions kimligi: CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID; yerelde
# wrangler'in kendi oturumu (npx wrangler login).
# UUID sabiti (DB) YALNIZ BELGE/REFERANS — hicbir kod yolu kullanmaz (olculdu, T8):
# execute yolu DB_AD kullanir; eski atif olan ci-d1-teshis.py sondasi T6'da sokuldu;
# d1-sync-durum-test.py DB'ye dokunmaz; olculmemis-siparis.py KENDI sabitini tanimlar;
# shop/wrangler.toml database_id ayri bir literal. Panel/CLI teshisinde ise yaradigi
# icin belge olarak KALIR (supheden kaldirilmadi).
DB = "3d99d15e-2342-4c23-9c2d-cb266f19c1ee"  # pruvo-katalog (UUID — yalniz belge)
DB_AD = "pruvo-katalog"  # execute yolunda KULLANILAN tanimlayici (surumden bagimsiz)

# Tek wrangler cagrisina konacak azami ifade sayisi (istek boyutu makul kalsin).
PARCA = 400
SEQ_ADIM = 1000000


# ── HATA KODU TESPITI — BICIMDEN BAGIMSIZ (31 Tem, run 30646713630'da OLCULDU) ───────
# Wrangler AYNI kodu en az UC ayri bicimde basar:
#     JSON govdesi   ->  "code": 7429          (TIRNAKLI — gercek --json yuku)
#     duz metin      ->  code: 7429
#     not/aciklama   ->  [code: 7429]          (KOSELI, tirnaksiz)
# Eski kural bir ALT-DIZE listesiydi ("code: 429", "status: 500", ...) ve yalniz duz-metin
# bicimini yakaliyordu. Gercek wrangler yuku JSON oldugu icin OLCULEN SONUC: 429/500/502/
# 503/504 kollarinin HEPSI OLUYDU (tirnak araya girdigi icin alt-dize tutmuyordu), 7429
# ise listede HIC yoktu; hatta `"code": 10000` bile auth koluna girmiyordu. Sonuc: D1'in
# CPU butcesi tukenip RESET edildigi GECICI ariza KALICI sanildi, tek bir yeniden deneme
# yapilmadan yayin dustu ve 25 urun TASLAK kaldi.
# Tek regex tum bicimleri ayni kola toplar; `code`/`status` ANAHTAR KELIMESI ZORUNLUDUR ->
# metinde gecen ciplak sayi ("7429 rows written", bir urun id'si) YANLISLIKLA hata sayilmaz.
_KOD_RE = re.compile(r'"?\b(?:code|status)"?\s*:\s*"?(\d{3,5})\b')
# GECICI = yeniden denemeye deger. 7429 = "D1 DB exceeded its CPU time limit and was reset"
# (baska bir push'un buyuk yazmasi butceyi harcar; DB reset olur, saniyeler icinde toparlar).
GECICI_KODLAR = frozenset({429, 500, 502, 503, 504, 7429})
# KALICI: kimlik dogrulama. Mevcut davranis KORUNUR (uc deneme sonrasi auth tanisi).
AUTH_KODLAR = frozenset({10000})


def hata_kodlari(ham):
    """Metindeki TUM wrangler/Cloudflare hata kodlarini (int kumesi) topla."""
    return {int(k) for k in _KOD_RE.findall(ham or "")}


def wrangler_hata_tanisi(ham):
    """Wrangler hata metnini siniflandir: auth, gecici veya bilinmeyen.

    code 10000 Wrangler/Cloudflare ciktisindan gelir; d1-sync bu kodu uretmez. Ancak
    tek bir 10000 cevabi gecici olabildigi icin wrangler() auth sonucunu da yeniden
    dener. Yalniz tum denemeler ayni sinifta basarisizsa kalici auth tanisi konur.
    """
    kucuk = (ham or "").lower()
    gecici_isaretler = (
        "timed out", "timeout", "etimedout", "econnreset", "econnrefused",
        "enotfound", "getaddrinfo", "socket hang up", "network error",
        "network connectivity", "fetch failed", "service unavailable",
        "bad gateway", "gateway timeout", "too many requests", "rate limit",
    )
    if any(isaret in kucuk for isaret in gecici_isaretler):
        return "gecici"
    kodlar = hata_kodlari(kucuk)
    if kodlar & GECICI_KODLAR:
        return "gecici"
    if kodlar & AUTH_KODLAR or "authentication error" in kucuk:
        return "auth"
    return None


# GECICI hatada denemeler ARASI bekleme (saniye). Deneme sayisi 3 -> en cok 2 bekleme.
# GEREKCE (olculdu 31 Tem): eski deger 0,25 s idi. CPU butcesi tukenip RESET edilen bir D1
# 250 ms'de toparlanmaz -> "yeniden deneme" KOZMETIK olur (uc deneme de ayni saniyeye duser
# ve hepsi ayni hatayi alir). 2 s ilk toparlanma penceresini, 8 s ise ayni anda kosan buyuk
# bir yazmanin (ornegin 1761 satirlik parti) bitmesini bekler. TAVAN 10 s: senkron adimi
# CI'da dakikalar suruyor, 10 s ne is akisini ne de pre-push hook'unu hissedilir yavaslatir;
# daha uzun bekleme (or. 30 s+) hook'u insanin iptal edecegi kadar uzatirdi.
GECICI_BEKLEME = (2.0, 8.0)


def hata_zarfi_metni(zarf):
    """Wrangler HATA zarfini insan/CI icin ADIYLA yaz (kod + ad + notlar)."""
    e = zarf.get("error") or {}
    satirlar = ["!! WRANGLER HATA CEVABI (basarili cikti DEGIL) — kod: %s · %s"
                % (e.get("code"), e.get("name") or "?")]
    if e.get("text"):
        satirlar.append("   " + str(e["text"]))
    for n in (e.get("notes") or []):
        if isinstance(n, dict) and n.get("text"):
            satirlar.append("   - " + str(n["text"]))
    kod = e.get("code")
    if kod in GECICI_KODLAR:
        satirlar.append("   (GECICI sinif — yeniden kosmak genelde yeter.)")
    return "\n".join(satirlar)


# ── PARSE KURALLARI — HEPSI FAIL-LOUD (supheliyi BASARI sayma) ───────────────────────
# 🔴 CURUTME DERSI (31 Tem, ilk onarim MERGE EDILMEDI): "ilk cozulebilen JSON on-ekini al"
# kurali eski `json.loads(stdout[i:])`nin BUTUNLUK sartini dusurmustu. Olculen sonuc:
#   rc=1 + KESIK yuk `[{"results":[{"id":"a"}],"success":tr`  -> `[{'id':'a'}]` DONUYORDU
#   rc=2 + `... d1_databases[0] field / npx: command failed`   -> `[0]` DONUYORDU
#   rc=0 + uyari satiri + GERCEK yuk                           -> `[0]` DONUYOR, yuk GORULMUYOR
# Asagi akista `dosya_calistir` bu ciktidan SESSIZCE "0 satir yazildi" uretir — wrangler
# rc=1 ile dusmusken. Tam da bu degisikligin gerekcesi olan "D1 reset ortasinda yazma"
# senaryosunda cikti KESIK gelmesi BEKLENIR: duzeltme arizayi gurultuluden SESSIZE cevirmis
# olurdu. Bu yuzden uc ayri kural birlikte kosar (her biri TEK BASINA no-op edilebilir ki
# kabul testi mutasyonla oldurulebilsin):
#   (1) _rc_hatali      — rc != 0 ise cikti ASLA basari sayilmaz.
#   (2) _basari_sekli_mi— cozulen deger wrangler BASARI SEKLI olmali: BOS OLMAYAN liste +
#                         her elemani results/success/meta tasiyan SOZLUK. `[0]` REDDEDILIR.
#   (3) _artik_gurultu_mu — cozulen yukten SONRA kalan artik yalniz bosluk/log satiri
#                         olabilir; JSON'un DEVAMI gibi duruyorsa (`,"success":tr`) yuk
#                         KESIKTIR -> FAIL-LOUD.
# On-ek taramasi KALIR: wrangler gercekten JSON'dan ONCE `▲ [WARNING] ... d1_databases[0]`
# gibi satirlar basar ve eski `find("[")` bunlari tolere ediyordu.
_SONUC_ANAHTARLARI = frozenset({"results", "success", "meta"})
# Artigin ILK anlamli karakteri bunlardan biriyse cozulen deger bir BUTUNUN PARCASIDIR
# (kesik/ic ice yuk), bagimsiz bir cikti degil.
_ARTIK_DEVAM_RE = re.compile(r'^[,:}\]"]')


def _rc_hatali(returncode):
    """wrangler SIFIR-DISI mi dondu? (rc != 0 -> cikti basari sayilamaz)"""
    return returncode != 0


def _basari_sekli_mi(deger):
    """wrangler --json BASARI sekli mi: bos olmayan liste + SONUC sozlukleri."""
    return (isinstance(deger, list) and len(deger) > 0
            and all(isinstance(e, dict) and (_SONUC_ANAHTARLARI & set(e)) for e in deger))


def _artik_gurultu_mu(artik):
    """Cozulen yukten sonraki artik zararsiz mi (bosluk / log satiri)?"""
    for satir in (artik or "").splitlines():
        s = satir.strip()
        if s and _ARTIK_DEVAM_RE.match(s):
            return False
    return True


def _json_tara(metin):
    """Metni soldan saga tara. Doner: (basari_yuku, hata_zarfi, json_adayi_var_mi)."""
    coz = json.JSONDecoder()
    metin = metin or ""
    aday, zarf, i, n = False, None, 0, len(metin)
    while i < n:
        if metin[i] not in "[{":
            i += 1
            continue
        aday = True
        try:
            deger, son = coz.raw_decode(metin, i)
        except ValueError:
            i += 1
            continue
        # 🔴 COZULEN DEGERIN ICINE GIRME: hata zarfinin ICINDEKI `"notes": [` dizisi de
        # gecerli JSON'dur; oradan devam edilirse zarf "basarili cikti" sanilir.
        i = max(son, i + 1)
        if _basari_sekli_mi(deger) and _artik_gurultu_mu(metin[son:]):
            return deger, None, True              # BASARILI cikti (sekil DEGISMEZ)
        if isinstance(deger, dict) and isinstance(deger.get("error"), dict):
            zarf = zarf or deger
    return None, zarf, aday


def wrangler_cikti_coz(stdout, ham="", returncode=0):
    """wrangler --json ciktisini coz — SUPHELIYI BASARI SAYMA.

    Doner: BASARILI cikti = LISTE (sekil DEGISMEZ: cagiranlar `r[0]["results"]` bekler).
    HATA zarfi ({"error": {...}}) gorulurse sys.exit ile ADIYLA raporlanir; her diger
    supheli hal FAIL-LOUD (sys.exit) — hicbir yolda "sanki bos sonuc" donmez.

    NEDEN ZARF ARANIYOR (31 Tem, run 30646713630): eski kod `stdout.find("[")` ile ILK
    koseli paranteze atliyordu. HATA yukunde bu, zarfin ICINDEKI `"notes": [` dizisidir ->
    json.loads "Extra data" ile duser ve arac elindeki `7429 / CPU time limit` mesajini
    YUTUP "wrangler ciktisi cozulemedi" der. Teshisi saatlerce geciktiren sey budur.
    """
    zarf = _json_tara(stdout)[1] or _json_tara(ham)[1]

    # (1) SIFIR-DISI CIKIS: komut DUSTU. Cikti ne kadar "cozulebilir" gorunse de basari
    # DEGILDIR (kesik yuk tam da burada beklenir). Zarf varsa ADIYLA bas, yoksa yuksek ses.
    if _rc_hatali(returncode):
        if zarf is not None:
            sys.exit(hata_zarfi_metni(zarf) + "\n" + ham[-2000:])
        sys.exit("wrangler SIFIR-DISI cikti (rc=%s) — cikti BASARI sayilmaz "
                 "(kesik/bozuk yuk olabilir):\n%s" % (returncode, ham[-2000:]))

    yuk, _, aday = _json_tara(stdout)
    if yuk is not None:
        return yuk
    if zarf is not None:
        sys.exit(hata_zarfi_metni(zarf) + "\n" + ham[-2000:])
    if not aday:
        sys.exit("wrangler cikti vermedi:\n" + ham[-2000:])
    sys.exit("wrangler ciktisi cozulemedi (BASARI sekli bulunamadi — liste-of-sonuc "
             "bekleniyordu):\n" + ham[-2000:])


def wrangler(args, girdi_dosya=None):
    """wrangler d1 execute calistir, JSON sonucu dondur."""
    komut = ["npx", "--yes", "wrangler@4", "d1", "execute", DB_AD, "--remote", "--json"] + args
    p = None
    ham = ""
    tani = None
    for deneme in range(3):
        p = subprocess.run(komut, cwd=KOK, capture_output=True, text=True)
        ham = (p.stdout or "") + (p.stderr or "")

        # Sandbox'li oturumlarda (Claude/CI) ~/.npm/_cacache yazilamayabilir (EPERM) ve
        # npx daha baslamadan duser (denetim 2026-07-15). Gecici bir npm cache ile TEK
        # SEFER yeniden dene — pre-push senkronunun sessizce kacmasini onler.
        if p.returncode != 0 and "EPERM" in ham and "_cacache" in ham:
            ort = dict(os.environ, npm_config_cache=tempfile.mkdtemp(prefix="pruvo-npm-"))
            p = subprocess.run(komut, cwd=KOK, capture_output=True, text=True, env=ort)
            ham = (p.stdout or "") + (p.stderr or "")

        # TANI YALNIZ SIFIR-DISI CIKISTA UYGULANIR. Kod tespiti artik tirnakli JSON'u da
        # gordugu icin, BASARILI bir cevabin ICINDEKI veri ("code":503 tasiyan bir satir)
        # yuzey olusturuyordu: rc=0 iken bile "D1 GECICI HATA" ile cikilabilirdi (fail-wrong).
        # Basarili kosum hata olarak siniflandirilamaz.
        tani = wrangler_hata_tanisi(ham) if p.returncode != 0 else None
        if p.returncode == 0 or tani not in ("auth", "gecici") or deneme == 2:
            break
        # ARTAN bekleme (bkz. GECICI_BEKLEME gerekcesi). time.sleep MODUL uzerinden
        # cagrilir ki kabul testi onu degistirip GERCEKTEN beklemesin.
        time.sleep(GECICI_BEKLEME[min(deneme, len(GECICI_BEKLEME) - 1)])

    if tani == "gecici":
        sys.exit(
            "D1 GECICI HATA, yeniden dene — ag/rate-limit/Cloudflare 5xx.\n"
            + ham[-2000:]
        )

    # 10000 tek basina kalici yetki kaniti degildir; iki retry da basarisiz olduktan
    # sonra auth olarak raporlanir. Token/oturum/config otomatik degistirilmez.
    if tani == "auth":
        sys.exit(
            "D1 GERCEK 10000 - auth — uc denemede de kimlik dogrulama basarisiz.\n"
            "  Token/oturum/config otomatik degistirilmedi.\n"
            + ham[-2000:]
        )

    return wrangler_cikti_coz(p.stdout or "", ham, p.returncode)


def sorgu(sql):
    return wrangler(["--command", sql])


def dosya_calistir(sql_metin):
    """Uzun SQL'i gecici dosyaya yazip calistir; (rows_written, rows_read) dondur."""
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
        f.write(sql_metin)
        yol = f.name
    try:
        sonuc = wrangler(["--file", yol])
        yaz = oku = 0
        for r in sonuc:
            m = r.get("meta") or {}
            yaz += m.get("rows_written") or 0
            oku += m.get("rows_read") or 0
        return yaz, oku
    finally:
        os.unlink(yol)


def q(s):
    """SQL metin sabiti — tek tirnak kacisi."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


# ══════════════════════════════════════════════════════════════════════════════
# YAZICI KILIDI — IKI ESZAMANLI YAZICI MESRU SATIR SILDIRIR
# ══════════════════════════════════════════════════════════════════════════════
# OLCULEN ARIZA (K48/K49): bu aracin YAZICI yolunda HICBIR kilit yoktu. Iki tam-katalog
# yazicisi ayni anda kosabiliyordu ve sinif UC KEZ atesledi:
#   kosum 31532464176 -> "D1'de FAZLA: 37" = 37 MESRU satir silindi
#   kosum 31502177931 -> "FAZLA: 41"
#   kosum 31546544881 -> "FAZLA: 5"  (5 mesru satir silindi, kardes oturum geri yazdi)
# K48 merge turunda ikinci yazici kosulmak uzereyken UCUSTAKI yazici (PID 86177, ~350 sn)
# TESADUFEN olculup durduruldu. BIZI KURAL DEGIL TESADUF KORUDU. Bu blok o tesadufu
# kurala cevirir.
#
# NEDEN SILME OLUYOR: yazici once D1'i OKUR, sonra urunler.json ile diff'ler, sonra YAZAR.
# Iki yazici bu OKU->PLANLA->YAZ penceresini ic ice gecirirse, digerinin HENUZ yazdigi
# satirlar birinin `fazla` kumesine duser ve DELETE edilir. Kilit bu yuzden tek bir
# ifadeyi degil, PENCERENIN TAMAMINI (okuma + plan + yazma + geri-okuma) kapsar.
#
# TASARIM KISITLARI (spec K49):
#  1. SURECLER-ARASI: `fcntl.flock` — cekirdek duzeyinde. Dosyanin ICERIGI (PID kaydi)
#     KARSILIKLI DISLAMA DEGILDIR, yalnizca TANIDIR; sahte bir kayit flock'u DELMEZ
#     ([[kutu-arsivle]] dersi: "kilit calinamaz").
#  2. FAIL-CLOSED, FAIL-SLOW DEGIL ([[fail-slow-fail-opendir]]): kilit SINIRLI sure
#     beklenir; alinamazsa yazici DURUR (rc=KILIT_MESGUL_RC) — sonsuz bloklama YOK,
#     sessizce devam etme YOK.
#  3. BAYAT KILIT OLDURMEZ: coken bir surecten kalan kayit sonsuza dek kilitlemez.
#     ⚠️ Devralma KENDISI bir fail-open kapisidir: yalnizca sahip PID'in gercekten OLU
#     oldugu OLCULDUGUNDE devralinir ("muhtemelen olmustur" ile DEGIL). Olculemeyen her
#     hal (izin hatasi / baska OSError) YASIYOR sayilir.
#  4. OKUYUCU YOLU ETKILENMEZ: `--durum` / `--kuru` / `--bayatlik` / `--kendini-test`
#     kilide DOKUNMAZ (aksi halde nobet/teyit yollari yaziciya bloklu olurdu).
#  5. MUTLU YOLDA CIKTI BASILMAZ — bayraksiz davranis BAYT AYNI kalsin diye. Ses yalnizca
#     ANORMAL hallerde cikar: beklendi · devralindi · reddedildi.
#
# 🔴 BILINEN SINIR (kacamaksiz, [[kapi-disiplin-ilkesi]]): flock TEK MAKINE kapsamlidir.
# GitHub Actions kosucusu ile yerel bir oturum arasindaki yarisi BU kilit KAPATMAZ; onu
# bayatlik kapisi + silme karantinasi kapatir. Bu blok, olculen vakanin ta kendisi olan
# AYNI MAKINEDEKI iki yaziciyi (pre-push kancasi × elle senkron × uzlastirici surucusu)
# kapatir.
KILIT_BEKLEME_SN = 20.0     # SINIRLI bekleme (asilma YOK); asilirsa fail-closed dur
KILIT_YOKLAMA_SN = 0.25
KILIT_MESGUL_RC = 9         # "baska yazici ucusta" — 1'den AYRI ki cagiran ayirt edebilsin
# Kilidi tutan acik dosya tanimlayicisi. flock OPEN FILE DESCRIPTION'a baglidir: ayni
# surecte IKINCI bir open() + flock ayni dosyada CAKISIR -> tutucu tek yerde tutulur.
_KILIT_TUTUCU = [None]


def pid_yasiyor(pid):
    """PID bu makinede YASIYOR mu?

    🔴 FAIL-CLOSED YON: "olu" hukmu KANIT ister. Yalnizca `ProcessLookupError` (cekirdek
    'boyle bir surec yok' dedi) OLU sayilir. Izin hatasi (baska kullanicinin sureci),
    olcumsuz OSError ve gecersiz kayit YASIYOR sayilir — cunku bu fonksiyonun 'False'
    dedigi yerde KILIT DEVRALINIR ve iki yazici ayni anda kosar.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return True
    if pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True          # surec VAR, sinyal yollama iznimiz yok
    except OSError:
        return True          # OLCULEMEDI -> olu SAYILMAZ
    return True


def kilit_kaydi_oku(yol):
    """Kilit dosyasindaki SAHIP KAYDI (dict) veya None (kayit yok/okunamadi/bozuk).

    Bozuk/eksik kayit "sahip YOK" demektir, "sahip OLU" demek DEGIL: gercek karsilikli
    dislama flock'tadir ve bu fonksiyon ancak flock BOSKEN danisilir. Bozuk bayta kalici
    kilitlenmek guvenlik kazandirmaz, yalnizca insan mudahalesi gerektiren bir DoS uretir.
    """
    try:
        with open(yol, encoding="utf-8") as f:
            ham = f.read().strip()
    except OSError:
        return None
    if not ham:
        return None
    try:
        kayit = json.loads(ham)
    except ValueError:
        return {"pid": None, "bozuk": ham[:200]}
    if not isinstance(kayit, dict):
        return {"pid": None, "bozuk": ham[:200]}
    return kayit


def kilit_kaydi_pid(kayit):
    """Kayittaki PID (int) veya None — kayit yok / alan yok / sayiya cevrilemiyor."""
    if not kayit:
        return None
    try:
        return int(kayit.get("pid"))
    except (TypeError, ValueError):
        return None


def _kilit_dur(mesaj):
    """FAIL-CLOSED cikis: yazici DURUR. rc 1'den AYRI (KILIT_MESGUL_RC)."""
    sys.stderr.write(mesaj.rstrip() + "\n")
    sys.stderr.flush()
    sys.exit(KILIT_MESGUL_RC)


def _kilit_yas(kayit):
    try:
        return "%.0f sn" % max(0.0, time.time() - float(kayit.get("baslangic")))
    except (TypeError, ValueError):
        return "bilinmiyor"


def yazici_kilidi_al(yol=None, bekleme=None, kol="yazici"):
    """YAZICI kilidini al. Alinamazsa SIFIR-DISI cikar (fail-closed). Doner: fd."""
    yol = KILIT if yol is None else yol
    bekleme = KILIT_BEKLEME_SN if bekleme is None else float(bekleme)
    try:
        fd = os.open(yol, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError as e:
        _kilit_dur("!! D1 YAZICI KILIDI ACILAMADI (%s): %s\n"
                   "   Kilit kurulamadan YAZILMAZ: iki eszamanli yazici MESRU satir "
                   "sildirir.\n   Yol: %s" % (type(e).__name__, e, yol))

    son = time.time() + max(0.0, bekleme)
    alindi = False
    beklendi = False
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            alindi = True
            break
        except OSError as e:
            if e.errno not in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
                os.close(fd)
                _kilit_dur("!! D1 YAZICI KILIDI OLCULEMEDI (flock %s): %s\n"
                           "   OLCULEMEDI bu depoda YESIL DEGILDIR -> yazma YAPILMADI.\n"
                           "   Yol: %s" % (type(e).__name__, e, yol))
            if time.time() >= son:
                break
            beklendi = True
            time.sleep(KILIT_YOKLAMA_SN)

    if not alindi:
        kayit = kilit_kaydi_oku(yol) or {}
        os.close(fd)
        _kilit_dur(
            "!! BASKA BIR D1 YAZICISI UCUSTA — bu kosum YAZMADAN durdu (fail-closed).\n"
            "   Kilidi tutan: PID %s · kol %s · yas %s · makine %s\n"
            "   %.1f sn beklendi, kilit birakilmadi. Iki eszamanli tam-katalog yazicisi\n"
            "   birbirinin YENI satirlarini 'fazla' sayip SILER (olculdu: 37 · 41 · 5\n"
            "   mesru satir). Bu yuzden beklemek yerine DURULUR.\n"
            "   Coz: ucustaki yazici bitince tekrar kos -> python3 tools/d1-sync.py\n"
            "   Kilit dosyasi: %s"
            % (kayit.get("pid"), kayit.get("kol"), _kilit_yas(kayit),
               kayit.get("makine"), bekleme, yol))

    # ── flock ALINDI. IKINCI KAT: dosyadaki kayit CANLI baska bir sureci mi gosteriyor? ──
    # Normalde imkansizdir (flock bos = sahip yok). Gerceklesirse flock'a guvenilemiyor
    # demektir (or. kilit dosyasi bir ag dosya sisteminde, ya da kayit elle kopyalandi) ->
    # FAIL-CLOSED dur. Bu kat, flock'un ACIK biraktigi bir kapiyi KAPATIR; hicbir zaman
    # flock'un KAPATTIGI bir kapiyi ACMAZ.
    kayit = kilit_kaydi_oku(yol)
    sahip = kilit_kaydi_pid(kayit)
    if sahip is not None and sahip != os.getpid() and pid_yasiyor(sahip):
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)
        _kilit_dur(
            "!! KILIT KAYDI CANLI BIR SURECE AIT (PID %s, yas %s) ama flock BOS.\n"
            "   Karsilikli dislama olculemiyor -> YAZILMADI (fail-closed).\n"
            "   Kilit dosyasi yerel bir dosya sisteminde mi? (flock ag FS'lerinde\n"
            "   guvenilmez.) Surec gercekten olduyse kilit dosyasini silin: %s"
            % (sahip, _kilit_yas(kayit), yol))

    if kayit is not None and sahip != os.getpid():
        # BAYAT KAYIT DEVRALINDI. Ses SART: fail-open yonunde tek adimimiz budur.
        print("d1-sync: BAYAT YAZICI KILIDI DEVRALINDI — kayittaki PID %s OLU "
              "(kayit yasi %s)." % (sahip if sahip is not None else "OKUNAMADI",
                                    _kilit_yas(kayit or {})))
    if beklendi:
        print("d1-sync: yazici kilidi beklendi, alindi.")

    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, json.dumps({
        "pid": os.getpid(),
        "baslangic": time.time(),
        "kol": kol,
        "makine": socket.gethostname(),
        "argv": sys.argv[1:][:12],
    }, ensure_ascii=False).encode("utf-8"))
    try:
        os.fsync(fd)
    except OSError:
        pass
    _KILIT_TUTUCU[0] = (fd, yol)
    return fd


def yazici_kilidi_birak():
    """Kilidi birak ve SAHIP KAYDINI TEMIZLE (bayat kayit birakma). Doner: birakildi mi."""
    tutucu = _KILIT_TUTUCU[0]
    if tutucu is None:
        return False
    fd, _yol = tutucu
    _KILIT_TUTUCU[0] = None
    try:
        os.ftruncate(fd, 0)
    except OSError:
        pass
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass
    return True


# Surec NASIL biterse bitsin (sys.exit / istisna / normal donus) kayit temizlenir.
# Cekirdek flock'u zaten surec olunce birakir; atexit'in ekledigi sey BAYAT KAYDIN
# silinmesidir — yoksa her cikis bir sonraki kosuma "devralindi" gurultusu birakirdi.
atexit.register(yazici_kilidi_birak)


# ══════════════════════════════════════════════════════════════════════════════
# TAVSIYE FILAMENT TIP KAPISI — dolumdan ONCE, FAIL-CLOSED, SAYIYLA
# ══════════════════════════════════════════════════════════════════════════════
# NEDEN VAR: `tavsiyeFilament` bir FIYAT girdisidir (on-secilen malzeme sepet carpanini
# surer) ve urun_hash'e girer. Beklenen tipte olmayan bir kayit gorulurse iki "kolay"
# yolun IKISI DE zararlidir:
#   * sessizce [] yapmak       -> urunun kendi onerisi duser, baska malzeme on-secilir,
#                                 ilan edilen tutar SESSIZCE kayar;
#   * dizeyi ["PETG"]'e cevirmek -> veri kusurunu GIZLER ve katalogda kalicilastirir.
# Dogru davranis DURMAK ve SAYIYI basmaktir: boylece sira kendini dayatir — katalog
# verisinin sahibi kaydi duzeltmeden dolum tamamlanmaz. Bu ev katalog verisinin yazari
# DEGILDIR; burasi kusuru ONARMAZ, GORUNUR KILAR.
#
# 🔴 KAPI `urunleri_oku()` ICINDE: senkron · --durum · --seq-normalize · --geriye-doldur
# yollarinin UCU DE katalogu BURADAN okur. Cagri yerlerine tek tek serpistirilseydi bir
# sonraki yol sessizce kapisiz kalirdi ([[nobetci-cagri-satiri-nobetsiz]]).
#
# 🔴 JETONLAR AYRIK (biri otekinin ALT DIZESI DEGIL): kirmizi kolun capasi
# TAVSIYE_FILAMENT_TIP_BOZUK, temiz kolunki TAVSIYE_FILAMENT_TIP_GECERLI.
JETON_TF_BOZUK = "TAVSIYE_FILAMENT_TIP_BOZUK"
JETON_TF_GECERLI = "TAVSIYE_FILAMENT_TIP_GECERLI"


def tavsiye_filament_tip_dokumu(urunler):
    """SAF — (dokum, bozuklar). Dosyaya/aga/D1'e DOKUNMAZ, birim testi burayi cagirir.

    dokum   {tip_etiketi: sayi} — or. {"YOK": 25312, "dizi": 293, "str": 10}
    bozuklar [(id, tip_etiketi, sebep), ...] — BEKLENEN tipte OLMAYAN her kayit.
    """
    dokum = {}
    bozuklar = []
    for u in urunler:
        if not isinstance(u, dict):
            dokum["kayit-sozluk-degil"] = dokum.get("kayit-sozluk-degil", 0) + 1
            bozuklar.append((None, type(u).__name__, "katalog ogesi sozluk degil"))
            continue
        etiket = arama.tavsiye_filament_tip_etiketi(u)
        dokum[etiket] = dokum.get(etiket, 0) + 1
        sebep = arama.tavsiye_filament_tip_sebebi(u)
        if sebep is not None:
            bozuklar.append((u.get("id"), etiket, sebep))
    return dokum, bozuklar


def tavsiye_filament_tip_raporu(dokum):
    """Dokumun tek satirlik insan-okur hali (sayi SIRALI, kararli)."""
    return " · ".join("%s=%d" % (k, dokum[k]) for k in sorted(dokum))


def tavsiye_filament_tip_kapisi(urunler):
    """FAIL-CLOSED: BEKLENEN tipte olmayan kayit varsa SAYIYLA basip sys.exit eder.

    Temiz katalogta tek satirlik GURULTULU teyit basar (sessiz yesil YOK: kapinin
    kostugu, ciktidan okunabilir olmali)."""
    dokum, bozuklar = tavsiye_filament_tip_dokumu(urunler)
    if not bozuklar:
        print("%s: %s (%d kayit)" % (JETON_TF_GECERLI, tavsiye_filament_tip_raporu(dokum),
                                     len(urunler)))
        return
    satirlar = ["!! %s — `tavsiyeFilament` alani BEKLENEN tipte olmayan %d kayit VAR."
                % (JETON_TF_BOZUK, len(bozuklar)),
                "   TIP DOKUMU: %s" % tavsiye_filament_tip_raporu(dokum),
                "   Bu kayitlar SESSIZCE NORMALIZE EDILMEZ (dizeyi tek elemanli diziye",
                "   cevirmek kusuru gizler; [] yapmak urunun kendi onerisini dusurup ilan",
                "   edilen tutari kaydirir). Senkron/dolum DURDU — kolon YARIM DOLMAZ."]
    for uid, etiket, sebep in bozuklar[:10]:
        satirlar.append("   - %s (tip: %s) : %s" % (uid, etiket, sebep))
    if len(bozuklar) > 10:
        satirlar.append("   ... +%d kayit daha" % (len(bozuklar) - 10))
    satirlar.append("   Coz: urunler.json'daki bu kayitlarda `tavsiyeFilament` DIZI olmali "
                    "(or. \"PETG\" -> [\"PETG\"]).")
    satirlar.append("   🔴 urunler.json'un tek yazari KATALOG EVIDIR; duzeltme oradan gelir.")
    sys.exit("\n".join(satirlar))


def urunleri_oku():
    with open(URUNLER, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, list):
        sys.exit("urunler.json dizi degil")
    # TIP KAPISI HER YOLDA: senkron da --durum da katalogu buradan okur. Bozuk kayitta
    # SAYIYLA durur; temizde tek satirlik teyit basar.
    tavsiye_filament_tip_kapisi(d)
    return d


# ══════════════════════════════════════════════════════════════════════════════
# KATALOG KAYNAGI — VARSAYILAN CALISMA AGACI, ISTENIRSE COMMIT'LI HEAD
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 OLCULEN TUZAK (5 Agu 2026, iki kez ayni gun): d1-sync katalogu DAIMA calisma
# agacindaki urunler.json'dan okur (`URUNLER` modul sabiti). Yani agacta baska bir
# oturumun COMMIT'LENMEMIS urunleri varsa senkron onlari CANLIYA yazar — ve bunu hicbir
# sey kirmizi yakmaz: bayatlik kapisi COMMIT GRAFIGINI olcer (HEAD uzak ucu biliyor mu),
# calisma agacinin o commit'ten SAPIP SAPMADIGINI olcmez. O gun model_kanon geriye
# doldurmasi tam bu yuzden ERTELENDI (agacta 105 commit'lenmemis urun vardi).
#
# COZUM: kaynak ACIKCA secilebilir olsun.
#   (bayraksiz)      CALISMA AGACI — bugunku davranis, BAYT AYNI. Kancalar buna bagli;
#                    varsayilani degistirmek 5 evin push yolunu tek hamlede degistirirdi.
#   --kaynak <yol>   verilen dosya (baska bir checkout, gecici cikarim, fikstur...).
#   --head           COMMIT'LI HEAD (`git show HEAD:urunler.json`) — agactaki
#                    commit'lenmemis urunler senkrona GIRMEZ.
#
# FAIL-CLOSED: secilen kaynak okunamaz / JSON dizi degilse ARAC DURUR. Sessizce calisma
# agacina DUSMEK, bayragin var olma sebebini yok ederdi (operator "HEAD'den kostum"
# sanirken agactan kosardi — tam da kapatmaya calistigimiz sessiz hata).
def head_katalogu():
    """`git show HEAD:urunler.json` icerigini GECICI bir dosyaya yazar.
    Doner: (yol, HEAD sha). FAIL-CLOSED: git okunamazsa sys.exit."""
    rc, sha = _git(["rev-parse", "HEAD"])
    if rc != 0 or not sha:
        sys.exit("!! --head COZULEMEDI: `git rev-parse HEAD` basarisiz (rc=%s).\n"
                 "   Sessizce calisma agacina DUSULMEZ — bayrak tam olarak bunu "
                 "onlemek icin var." % rc)
    try:
        p = subprocess.run(["git", "show", "HEAD:urunler.json"], cwd=KOK,
                           capture_output=True, text=True, timeout=120,
                           env=git_ortami())
    except Exception as e:                                        # noqa: BLE001
        sys.exit("!! --head COZULEMEDI: git show calistirilamadi (%s)." % (e,))
    if p.returncode != 0:
        sys.exit("!! --head COZULEMEDI: `git show HEAD:urunler.json` rc=%d\n   %s"
                 % (p.returncode, (p.stderr or "").strip()[:300]))
    fd, yol = tempfile.mkstemp(prefix="d1-sync-head-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(p.stdout)
    return yol, sha


def kaynak_coz(kaynak=None, head=False):
    """Katalog kaynagini SEC. Doner: (yol, beyan, gecici_mi).
    yol None = bayrak VERILMEDI -> cagiran modul sabitine DOKUNMAZ (bayt-ayni davranis)."""
    if kaynak and head:
        sys.exit("!! --kaynak ve --head BIRLIKTE verilemez (hangi kaynak? belirsizlik "
                 "fail-closed reddedilir).")
    if head:
        yol, sha = head_katalogu()
        return yol, "COMMIT'LI HEAD (%s)" % sha[:12], True
    if kaynak:
        yol = os.path.abspath(kaynak)
        if not os.path.exists(yol):
            sys.exit("!! --kaynak dosyasi YOK: %s" % yol)
        return yol, "--kaynak %s" % yol, False
    return None, "calisma agaci (%s)" % URUNLER, False


def kaynak_dogrula(yol):
    """Secilen kaynagin SEKLINI fail-closed dogrula. Doner: benzersiz id sayisi."""
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:                                        # noqa: BLE001
        sys.exit("!! KAYNAK OKUNAMADI (%s): %s\n   Calisma agacina SESSIZCE dusulmez."
                 % (yol, e))
    if not isinstance(d, list) or not d:
        sys.exit("!! KAYNAK gecerli bir urun DIZISI degil: %s" % yol)
    return len({u.get("id") for u in d if isinstance(u, dict) and u.get("id")})


def kaynak_sapmasi(secilen_yol):
    """Secilen kaynak ile CALISMA AGACI arasindaki id/hash farki (yalniz OLCUM, yazmaz).
    Doner: (yalniz_kaynakta, yalniz_agacta, hash_farki). Operatorun kaniti budur:
    "commit'lenmemis urun canliya yazilmadi" iddiasi BU sayilarla olculur."""
    def _oku(yol):
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    try:
        a = {u["id"]: arama.urun_hash(u) for u in _oku(secilen_yol)
             if isinstance(u, dict) and u.get("id")}
        b = {u["id"]: arama.urun_hash(u) for u in _oku(URUNLER)
             if isinstance(u, dict) and u.get("id")}
    except Exception as e:                                        # noqa: BLE001
        sys.exit("!! KAYNAK SAPMASI OLCULEMEDI (%s) — 'olcemedim' YESIL DEGILDIR." % (e,))
    return (sorted(set(a) - set(b)), sorted(set(b) - set(a)),
            sorted(i for i in set(a) & set(b) if a[i] != b[i]))


# ══════════════════════════════════════════════════════════════════════════════
# BAYATLIK KAPISI — "eski agac yeni partiyi D1'den SILMESIN" (31 Tem, adli olcum)
# ══════════════════════════════════════════════════════════════════════════════
# OLCULEN OLAY: CI'daki "Katalogu D1'e senkronla" adimi KENDI (eski) checkout'undan
# d1-sync kosar. O sirada daha yeni bir push, pre-push hook'uyla D1'i ZATEN
# guncellemistir. diff-upsert "yerelde olmayan id"yi D1'den DELETE ettigi icin ESKI
# kosum YENI partiyi SILER. Bir gunde 9 olay / 367 id sessizce silindi ve 9 olayin
# 9'unda CI sonucu `success` gorundu. Ikinci yuzey: pre-push hook push edilen commit'i
# degil CALISMA AGACINI yazar -> bayat bir worktree'den main'e push 3.498 id silerdi.
#
# KAPI: DELETE uygulanmadan once "bu agac yayindaki UCU biliyor mu" OLCULUR.
#   UC        = uzak main'in ucu HEAD'in ATASI (ya da HEAD'in kendisi) -> silme SERBEST
#   BAYAT     = uzak uc HEAD'in atasi DEGIL (ya da yerelde hic yok) -> silme YAPILMAZ
#   OLCULEMEDI= git yok / uzak okunamadi -> FAIL-CLOSED, silme YAPILMAZ
# UPSERT engellenmez (asil yikici islem DELETE'tir; bayat icerik yazimini P3
# uzlastiricisi kapatir). Engel olursa arac SIFIR-DISI cikar ve NE'yi silmedigini basar.
#
# NEDEN "ATA" (ancestor) VE "ESIT" DEGIL: pre-push hook'u push TAMAMLANMADAN once
# kosar -> o an uzak uc HENUZ eski commit'tir ve HEAD onun UZERINDEDIR. "Esit" sarti
# butun mesru push'lari kirardi. "Uzak uc benim atam" sarti tam olarak "yayinda olan
# her seyi biliyorum" demektir -> MESRU SILME (duzelt.py --toplu ile kaldirilan urun,
# commit'lenip push edilirken) GECER; BAYAT AGAC (CI'nin eski checkout'u, eski worktree)
# GECMEZ.
#
# NEDEN `ls-remote` (fetch DEGIL): nesne indirmez, yalniz ucun SHA'sini okur (~0,5-1 s).
# Uc SHA yerelde YOKSA zaten bizde olmayan bir sey yayindadir -> BAYAT (fail-closed).
#
# MALIYET: yalnizca SILINECEK id VARKEN olculur. Tipik urun partisinde silme 0'dir ->
# kapi hic calismaz, yayin yoluna maliyeti 0 sn.
UZAK = "origin"
UZAK_DAL = "refs/heads/main"


def _git(args, zaman_asimi=60):
    """git calistir. Doner: (rc, stdout.strip()). Calistirilamazsa (None, "")."""
    try:
        p = subprocess.run(["git"] + list(args), cwd=KOK, capture_output=True,
                           text=True, timeout=zaman_asimi, env=git_ortami())
    except Exception:                                             # noqa: BLE001
        return None, ""
    return p.returncode, (p.stdout or "").strip()


def bayatlik_olc():
    """Yazan agac yayindaki UCU biliyor mu? Doner: dict(durum, sebep, head, uzak).

    durum: "UC" (silme guvenli) | "BAYAT" (silme YASAK) | "OLCULEMEDI" (silme YASAK).
    HICBIR halde istisna sizdirmez: olculemeyen her sey FAIL-CLOSED sayilir.
    """
    def _sonuc(durum, sebep, head="?", uzak="?"):
        return {"durum": durum, "sebep": sebep, "head": head, "uzak": uzak}

    rc, _ = _git(["rev-parse", "--git-dir"])
    if rc != 0:
        return _sonuc("OLCULEMEDI", "git deposu okunamadi (git yok / depo degil)")
    rc, head = _git(["rev-parse", "HEAD"])
    if rc != 0 or not head:
        return _sonuc("OLCULEMEDI", "HEAD okunamadi (commit'siz depo?)")
    rc, cikti = _git(["ls-remote", UZAK, UZAK_DAL])
    if rc != 0 or not cikti:
        return _sonuc("OLCULEMEDI",
                      "uzak uc okunamadi: git ls-remote %s %s (ag/kimlik/uzak yok)"
                      % (UZAK, UZAK_DAL), head)
    uzak = cikti.split()[0].strip()
    if len(uzak) < 7:
        return _sonuc("OLCULEMEDI", "uzak uc SHA ayristirilamadi: %r" % cikti[:80], head)
    if uzak == head:
        return _sonuc("UC", "HEAD == uzak main ucu", head, uzak)
    rc, _ = _git(["cat-file", "-e", uzak + "^{commit}"])
    if rc != 0:
        return _sonuc("BAYAT", "uzak main ucu bu agacta YOK (yayinda bizde olmayan commit var)",
                      head, uzak)
    rc, _ = _git(["merge-base", "--is-ancestor", uzak, head])
    if rc == 0:
        return _sonuc("UC", "uzak main ucu HEAD'in atasi (agac uctan GERI DEGIL)", head, uzak)
    if rc == 1:
        return _sonuc("BAYAT", "uzak main ucu HEAD'in atasi DEGIL (agac uctan GERIDE/ayrik)",
                      head, uzak)
    return _sonuc("OLCULEMEDI", "merge-base olculemedi (rc=%s)" % rc, head, uzak)


def bayatlik_engel_metni(b, sayilar, silinen_ornek):
    """Yazma engellendiginde basilan YUKSEK SESLI metin (liste halinde satirlar).

    sayilar: {"yeni","degisen","silinen","baski","taban","konfigur","marka_kanon",
    "model_kanon", "marka_arama"} -> engellenen is.
    silinen_ornek: engellenen DELETE id'leri (en yikici kalem; ornekleri basilir).
    """
    toplam = sum(sayilar.values())
    satirlar = [
        "!! BAYATLIK KAPISI: BU AGACTAN D1'e HICBIR SEY YAZILMADI (durum: %s)." % b["durum"],
        "   Sebep: %s" % b["sebep"],
        "   HEAD=%s · uzak %s ucu=%s"
        % (str(b["head"])[:12], UZAK_DAL, str(b["uzak"])[:12]),
        "   Engellenen is (toplam %d): yeni %d | degisen %d | silinen %d | baski %d | "
        "taban %d | konfigur %d | marka_kanon %d | model_kanon %d | marka_arama %d"
        % (toplam, sayilar.get("yeni", 0), sayilar.get("degisen", 0),
           sayilar.get("silinen", 0), sayilar.get("baski", 0),
           sayilar.get("taban", 0), sayilar.get("konfigur", 0),
           sayilar.get("marka_kanon", 0), sayilar.get("model_kanon", 0),
           sayilar.get("marka_arama", 0)),
        "   NEDEN: bu agac yayindaki ucu bilmiyor. Yazma UYGULANSAYDI baska bir push'un",
        "   D1'e yeni yazdigi urunler SILINIR ya da alanlari ESKI degerlere GERI ALINIRDI",
        "   (site dogru gosterir, Ege bayat gorur = sessiz satis kaybi).",
    ]
    if silinen_ornek:
        satirlar.append(
            "   Silinmeyen id ornekleri: " + ", ".join(silinen_ornek[:10])
            + (" ... (+%d)" % (len(silinen_ornek) - 10) if len(silinen_ornek) > 10 else ""))
    satirlar += [
        "   Coz: agaci uca getir (git pull --ff-only / taze checkout) ve tekrar kos.",
        "   Emniyet agi: uctan kosan CI adimi + .github/workflows/d1-uzlastirici.yml (15 dk).",
        "   NOT: yayin DURMAZ — pre-push hook exit 0 doner, CI adimi continue-on-error.",
    ]
    return satirlar


def kolonlari_oku(tablo):
    """Canli tablonun KOLON ADLARI (kume). Tek PRAGMA — satir YAZMAZ."""
    r = sorgu("PRAGMA table_info(%s)" % tablo)
    return {s["name"] for s in ((r[0].get("results") or []) if r else [])}


def kolon_var_mi(tablo, kolon):
    """Canli tabloda kolon VAR mi? (PRAGMA — satir YAZMAZ, tek ucuz sorgu.)

    NEDEN GEREKLI: yeni kolon canli D1'e ancak `--sema` (ALTER) kosuldugunda girer. Kolonu
    kosulsuz SELECT'e koyarsak, --sema HENUZ kosmadan calisan bir senkron (or. pre-push
    hook'u) "no such column" ile duser ve TUM katalog senkronu olur -> Ege bayat katalog
    okur (sessiz satis kaybi). Kolon yoksa yalniz KONFIGUR senkronu atlanir, katalog akmaya
    devam eder; atlama GURULTULU basilir (asagida)."""
    r = sorgu("PRAGMA table_info(%s)" % tablo)
    return kolon in {s["name"] for s in (r[0].get("results") or [])}


def d1_mevcut(konfigur_kolonu=True, marka_kanon_kolonu=False, model_kanon_kolonu=False,
              marka_arama_kolonu=False):
    """D1'deki {id: (hash, baski)} + {id: taban_fiyat} + {id: seq} + en buyuk seq.
    baski da OKUNUR: baski senkronu (main) onu D1'dekiyle KIYASLAR — degismemisse yazmaz
    (yoksa her yerel kosum tum baski'lari yeniden yazardi).
    taban_fiyat da OKUNUR: taban senkronu (main) onu semadakiyle KIYASLAR — ayni mantik.
    seq de OKUNUR (mevcut_seq): diff_plan'in SEQ SANDVIC mantigi (asagida) icin GEREKLI —
    bkz. diff_plan docstring'i, "yeni" id dizide GERCEKTEN tepede mi yoksa mid-array mi
    ayirt edebilsin diye D1'deki HER satirin KENDI seq'i lazim (eskiden yalniz MAX(seq)
    okunuyordu, tek-tek satir seq'leri KAYIPTI).
    konfigur da OKUNUR (konfigur_kolonu=True ise): konfigur senkronu (main) onu urunler.json'dan
    turetilenle KIYASLAR — degismemisse yazmaz (taban_fiyat/baski ile AYNI desen).
    NOT: taban_fiyat kolonu --sema (GOC_KOLON ALTER) ile eklenir; bu SELECT'ten ONCE
    --sema kosmus olmali (canli uygulama sirasi muhendis raporunda). konfigur kolonu icin bu
    sart YUMUSATILDI: kolon yoksa cagiran konfigur_kolonu=False verir ve SELECT onu istemez
    (bkz. kolon_var_mi) -> --sema unutulsa bile katalog senkronu AKMAYA DEVAM EDER.
    marka_kanon da OKUNUR (marka_kanon_kolonu=True ise): AYNI kosullu desen — kolon canliya
    ALTER ile girmeden once bu kodu push'lamak GUVENLIDIR (SELECT'e KONMAZ, senkron akar).
    🔴 Bu sart, "kolonu SELECT eden kod once push'lanirsa HERKESIN push'u 'no such column'
    ile kirilir" tuzagini yapisal olarak kapatir (merge-kapisi §6.2 sema sirasi).
    model_kanon da OKUNUR (model_kanon_kolonu=True ise): marka_kanon ile BIREBIR ayni
    kosullu desen ve AYNI gerekce.
    marka_arama da OKUNUR (marka_arama_kolonu=True ise): UCUNCU kolon, AYNI kosullu desen.
    🔴 UC JSON-DIZI KOLONUNUN UCU DE KOSULLU: hicbiri ZORUNLU_KOLONLAR'da degil, uculu
    birlikte eksik olsa bile katalog senkronu AKAR."""
    kolonlar = ("id, hash, baski, taban_fiyat, seq"
                + (", konfigur" if konfigur_kolonu else "")
                + (", marka_kanon" if marka_kanon_kolonu else "")
                + (", model_kanon" if model_kanon_kolonu else "")
                + (", marka_arama" if marka_arama_kolonu else ""))
    r = sorgu("SELECT %s FROM urunler" % kolonlar)
    satirlar = (r[0].get("results") or []) if r else []
    mevcut = {s["id"]: (s["hash"], s.get("baski") or "") for s in satirlar}
    mevcut_taban = {s["id"]: int(s.get("taban_fiyat") or 0) for s in satirlar}
    mevcut_seq = {s["id"]: s["seq"] for s in satirlar if s.get("seq") is not None}
    mevcut_konfigur = ({s["id"]: (s.get("konfigur") or "") for s in satirlar}
                       if konfigur_kolonu else {})
    mevcut_marka_kanon = ({s["id"]: (s.get("marka_kanon") or "") for s in satirlar}
                          if marka_kanon_kolonu else {})
    mevcut_model_kanon = ({s["id"]: (s.get("model_kanon") or "") for s in satirlar}
                          if model_kanon_kolonu else {})
    mevcut_marka_arama = ({s["id"]: (s.get("marka_arama") or "") for s in satirlar}
                          if marka_arama_kolonu else {})
    r2 = sorgu("SELECT COALESCE(MAX(seq), 0) AS m FROM urunler")
    mseq = ((r2[0].get("results") or [{}])[0] or {}).get("m") or 0
    return (mevcut, mevcut_taban, mevcut_seq, int(mseq), mevcut_konfigur,
            mevcut_marka_kanon, mevcut_model_kanon, mevcut_marka_arama)


# Sonradan eklenen kolonlar. Mevcut D1 tablosunda CREATE TABLE IF NOT EXISTS bunlari
# EKLEMEZ (tablo zaten var) -> --sema calistiginda eksikler ALTER ile tamamlanir.
GOC_KOLON = [
    ("aciklama", "TEXT NOT NULL DEFAULT ''"),
    ("ege", "TEXT NOT NULL DEFAULT ''"),
    ("hs_baslik", "TEXT NOT NULL DEFAULT ''"),
    ("hs_baslik_kok", "TEXT NOT NULL DEFAULT ''"),
    ("hs_govde", "TEXT NOT NULL DEFAULT ''"),
    ("hs_govde_kok", "TEXT NOT NULL DEFAULT ''"),
    # BASKI onerisi (siparis yonetimi paketi) — gizli kayittan doldurulur (asagida).
    ("baski", "TEXT NOT NULL DEFAULT ''"),
    # PARAMETRIK TABAN FIYAT (TL, tam sayi) — jenerator/urunler/<id>.json tabanFiyatTL'den
    # doldurulur. Mevcut canli tabloda CREATE atlanir -> --sema ALTER ile ekler. HASH'e
    # KARISMAZ; hedefli UPDATE (taban_senkron_sql) ile senkronlanir (baski deseni).
    ("taban_fiyat", "INTEGER NOT NULL DEFAULT 0"),
    # KONFIGUR SEMASI (kanonik JSON metin) — urunler.json "konfigur" alanindan doldurulur.
    # Worker bundle'inin (shop/src/konfigurlar.js) D1 ikizi; HASH'e KARISMAZ, hedefli UPDATE
    # (konfigur_senkron_sql) ile senkronlanir. Gerekce -> d1-sema.sql konfigur kolonu yorumu.
    ("konfigur", "TEXT NOT NULL DEFAULT ''"),
    # ATOMIK YAYIN (31 Tem) — TASLAK/YAYINDA ayrimi. Yeni satir DAIMA yayinda=0 girer
    # (satir_sql INSERT VALUES); yayina alma AYRI ve ATOMIK bir adimdir
    # (tools/yayin-kapisi.py --yayinla: /urun/<id>/ CANLIDA 200 dondugu dogrulanmadan
    # UPDATE yapilmaz). KOLONLAR'da BILEREK YOK -> icerik upsert'i mevcut satirin
    # yayinda degerine DOKUNMAZ. Gerekce + olculen pencere -> d1-sema.sql yorumu.
    ("yayinda", "INTEGER NOT NULL DEFAULT 0"),
    ("release_id", "TEXT NOT NULL DEFAULT ''"),
    # TICARI HAL (31 Tem) — Ege fiziksel urunu ALGILASIN. Gerekce + uc-degerli `stokta`
    # semantigi d1-sema.sql'in "TICARI HAL" blogunda; kanonik degerler arama.tur_kanonik /
    # arama.stokta_kanonik. Bu ikisi taban_fiyat/konfigur'un AKSINE HASH'E GIRER ve icerik
    # upsert'i ile yazilir (KOLONLAR + satir_sql) — alanlar PUBLIC urunler.json'da oldugu
    # icin CI ve yerel AYNI degeri gorur, baski'daki "yetki" sorunu YOKTUR.
    # 🔴 ALTER DEFAULT'u -1 (BILINMIYOR), 0 DEGIL: goc anindan senkron bitene kadarki
    # pencerede mevcut 15.975 satir "stokta degil" DEGIL "bilinmiyor" olur (fail-closed
    # ama katalogu topluca TUKENMIS ilan etmez).
    ("tur", "TEXT NOT NULL DEFAULT ''"),
    ("stokta", "INTEGER NOT NULL DEFAULT -1"),
    # ALT KATEGORI (1 Agu) — kategori ICINDEKI daraltma etiketi. tur/stokta ile AYNI
    # sinif: PUBLIC urunler.json alani, icerik upsert'i ile yazilir, HASH'E GIRER
    # (KOLONLAR'da da VAR). Gerekce + fail-closed kural: d1-sema.sql altkategori yorumu
    # ve arama.altkategori_kanonik.
    ("altkategori", "TEXT NOT NULL DEFAULT ''"),
    # UYUM (2 Agu) — arac uyumlulugu (JSON dizi). altkategori/tur/stokta ile AYNI sinif:
    # PUBLIC urunler.json alani, icerik upsert'i ile yazilir, HASH'E GIRER (KOLONLAR'da da
    # VAR). Gerekce + fail-closed kural: d1-sema.sql uyum yorumu ve arama.uyum_kanonik.
    # ALTER DEFAULT'u '[]' ('' DEGIL): kolon JSON DIZI tasir, okuma ucu JSON.parse'i
    # kosulsuz uygulayabilsin (marka kolonunun deseni). Goc anindan senkron bitene kadarki
    # pencerede mevcut satirlar "uyum bilgisi yok" der — yanlis uyum VAAT ETMEZ.
    ("uyum", "TEXT NOT NULL DEFAULT '[]'"),
    # KANONIK MARKA UYELIGI (4 Agu) — urunun uye oldugu /marka/ sayfalarinin kanonik adlari
    # (JSON dizi). konfigur/taban_fiyat SINIFINDA: HASH'e KARISMAZ, HEDEFLI UPDATE ile
    # senkronlanir (marka_kanon_plan). Gerekce + olculen sessiz hata (9 markada 120 kalem
    # cip-sayfa ayrismasi): d1-sema.sql marka_kanon yorumu.
    # ALTER DEFAULT'u '[]' ('' DEGIL): kolon JSON DIZI tasir, okuma ucu JSON.parse'i
    # kosulsuz uygulayabilsin (marka/uyum kolonlarinin deseni). Goc anindan senkron bitene
    # kadarki pencerede mevcut satirlar "kanonik uyelik bilinmiyor" der — YANLIS uyelik
    # VAAT ETMEZ (uc bu kolona ancak dolduktan sonra gecirilir; bkz. muhendis raporu).
    ("marka_kanon", "TEXT NOT NULL DEFAULT '[]'"),
    # KANONIK MODEL UYELIGI (5 Agu) — urunun uye oldugu YAYIMLANAN /marka/<m>/<model>/
    # sayfalarinin kanonik etiketleri (JSON dizi). marka_kanon ile AYNI SINIF: HASH'e
    # KARISMAZ, HEDEFLI UPDATE ile senkronlanir (model_kanon_plan). Gerekce + olculen
    # sessiz hata (96 kovada 390 kalem sayfa-suzgec ayrismasi) ve "uc bunu HAM `model`in
    # YERINE degil BIRLESIM olarak okur" olcumu: d1-sema.sql model_kanon yorumu.
    # ALTER DEFAULT'u '[]' ('' DEGIL): kolon JSON DIZI tasir (marka/uyum/marka_kanon deseni);
    # goc anindan senkron bitene kadarki pencerede satirlar "kanonik model uyeligi bilinmiyor"
    # der — YANLIS uyelik VAAT ETMEZ.
    ("model_kanon", "TEXT NOT NULL DEFAULT '[]'"),
    # MARKA ARAMA UYELIGI (5 Agu) — `?q=<marka>` kolunun UCTA cozulmesi icin. marka_kanon /
    # model_kanon ile AYNI SINIF (hash'e karismaz, hedefli UPDATE, DEFAULT '[]') ama AYRI
    # kolon: marka_kanon cipi besler ve UYELIK tanimini tasimalidir; baslik uyumu ona
    # eklenseydi cip sayfadan fazla sayar ve marka-invaryant-kapisi.py FILTRE ekseni
    # bozulurdu. Gerekce + olculen sessiz hata (canli `?q=MAN` = 3539) ve "uc bunu ham
    # `marka` ile BIRLESIM DEGIL TEK BASINA okur" olcumu: d1-sema.sql marka_arama yorumu.
    ("marka_arama", "TEXT NOT NULL DEFAULT '[]'"),
    # TAVSIYE FILAMENT (11 Agu) — urunun KENDI malzeme onerisi (JSON dizi). tur/stokta/
    # altkategori/uyum ile AYNI SINIF: PUBLIC urunler.json alani, icerik upsert'i ile
    # yazilir, HASH'E GIRER (KOLONLAR'da da VAR). Gerekce + "liste SIRALANMAZ" kurali +
    # fail-closed yonu ("DUR", "BOSALT" degil): d1-sema.sql tavsiye_filament yorumu ve
    # arama.tavsiye_filament_kanonik.
    # ALTER DEFAULT'u '[]' ('' DEGIL): kolon JSON DIZI tasir, okuma ucu JSON.parse'i
    # kosulsuz uygulayabilir (marka/uyum/marka_kanon deseni). Goc anindan senkron bitene
    # kadarki pencerede mevcut satirlar "override YOK" der -> okuyan uc bugunku davranisi
    # (kategori haritasi) uygular; YANLIS bir malzeme ON-SECILMEZ.
    ("tavsiye_filament", "TEXT NOT NULL DEFAULT '[]'"),
]

# siparisler icin ayni mekanizma (shop kargo + siparis yonetimi paketleri): DEFAULT'lu
# ekleme -> eski siparis satirlari bozulmaz (kargo/KDV tahsil edilmedi, onay kutusu yoktu).
GOC_KOLON_SIPARIS = [
    ("kargo_kurus", "INTEGER NOT NULL DEFAULT 0"),
    ("kdv_kurus", "INTEGER NOT NULL DEFAULT 0"),
    ("odeme_yontemi", "TEXT NOT NULL DEFAULT 'kart'"),
    ("sozlesme_onay", "TEXT NOT NULL DEFAULT ''"),
    # Siparis yonetimi paketi: kargo firma+kodu + durum gecmisi (same-row, ek satir yazmaz).
    ("kargo_firma", "TEXT NOT NULL DEFAULT ''"),
    ("kargo_kodu", "TEXT NOT NULL DEFAULT ''"),
    ("durum_gecmisi", "TEXT NOT NULL DEFAULT ''"),
    # Reklam ROI olcumu (reklam-roi-sistemi.md Faz 0): atif kimlikleri (GA client_id + Meta
    # fbp/fbc + UTM) kompakt JSON. Purchase event (shop donus) bunlari kullanir; PII yok.
    ("atif", "TEXT NOT NULL DEFAULT ''"),
    # KANAL AYRACI (1 Agu 2026, WhatsApp siparis ucu — shop/src/yonet.js /wa-siparis):
    # 'site' | 'whatsapp'. DEFAULT 'site' -> ALTER anindan itibaren MEVCUT TUM satirlar
    # DOGRU degeri alir (hepsi site siparisiydi): geriye doldurma GEREKMEZ, `yayinda`
    # kolonundaki gibi bir sira tuzagi YOKTUR. Gerekce: tools/d1-sema.sql kanal yorumu.
    ("kanal", "TEXT NOT NULL DEFAULT 'site'"),
    # Dis sistemin KENDI siparis numarasi (Ege: PR-yyMMdd-HHmmss, sonek YOK). Mutabakat +
    # /wa-siparis idempotens anahtari. Site siparislerinde '' kalir.
    ("dis_no", "TEXT NOT NULL DEFAULT ''"),
]

# 🔴 dis_no TEKILLIGI ICIN AYRI BIR LISTE YOKTUR: kismi UNIQUE indeks asagidaki GOC_INDEKS
# KAYIT DEFTERINDE (`siparisler_kanal_dis_no`) tanimlidir. Ayri bir SIPARIS_INDEKS listesi
# tutulsaydi indeks kurulurdu ama KURULDUGU DOGRULANMAZDI (fail-closed hal makinesinin
# disinda kalirdi) — tek-yonlu kapi tam da orada acilir. Bkz. GOC_INDEKS yorumu.

# ON CONFLICT (UPDATE) sirasinda GUNCELLENEN kolonlar.
# "baski" BILEREK YOK: baski yalnizca gizli .urun-kaynaklari.json'da (CI'da yok).
# Content upsert'i baski'yi da yazsaydi CI HER kosumda baski'yi '' YAPARDI (D1'den
# SILERDI — 2026-07-18: canlida 7381 satirin hepsinde baski='' bulundu, sebep buydu).
# baski AYRI senkronla yonetilir (baski_senkron_sql + main) ve SADECE dosyasi olan
# ortam (yerel) yazar. INSERT VALUES'ta baski VAR (yeni satir onu alir); sadece
# CONFLICT/UPDATE yolu baski'ya dokunmaz.
#
# 🔴 KOLONLAR ile satir_sql'in INSERT listesi AYRISAMAZ: aradaki fark TAM OLARAK
# KASITLI_DISARIDA olmalidir (invaryant; tools/stok-d1-kapisi.py C ekseni bunu olcer).
# Yeni bir icerik kolonu INSERT'e eklenip KOLONLAR'a eklenmezse satir ILK yazimda dogru,
# sonraki her guncellemede ESKI deger ile kalir — sessiz bayatlik. Kapi bunu kirmizi yakar.
KOLONLAR = [
    "hash", "baslik", "kategori", "marka", "fiyat", "gorsel", "parametrik", "hs",
    "aciklama", "ege", "hs_baslik", "hs_baslik_kok", "hs_govde", "hs_govde_kok",
    # TICARI HAL — hash'e girdikleri icin ON CONFLICT yolunda da GUNCELLENMELIDIR:
    # "tukendi" isareti mevcut bir satirda degistiginde upsert calisir ve stokta'yi
    # yazar. KOLONLAR'da olmasalardi hash yeni degerle yazilir ama stokta ESKI kalirdi
    # (hash "senkron" der, veri bayat = en kotu tur sessiz hata).
    "tur", "stokta",
    # ALT KATEGORI — hash'e girdigi icin ON CONFLICT yolunda da GUNCELLENMELIDIR:
    # mevcut bir urunun altkategorisi degistiginde upsert calisir ve kolonu yazar.
    # KOLONLAR'da olmasaydi hash yeni degerle yazilir ama altkategori ESKI kalirdi
    # (hash "senkron" der, alt-filtre bayat = sessiz hata).
    "altkategori",
    # UYUM — hash'e girdigi icin ON CONFLICT yolunda da GUNCELLENMELIDIR: mevcut bir urunun
    # uyum listesi degistiginde upsert calisir ve kolonu yazar. KOLONLAR'da olmasaydi hash
    # yeni degerle yazilir ama uyum ESKI kalirdi (hash "senkron" der, Ege bayat uyum
    # servis eder = musteriye yanlis uyum vaadi, sessiz).
    "uyum",
    # TAVSIYE FILAMENT — hash'e girdigi icin ON CONFLICT yolunda da GUNCELLENMELIDIR:
    # mevcut bir urunun malzeme onerisi degistiginde upsert calisir ve kolonu yazar.
    # KOLONLAR'da olmasaydi satir ILK yazimda dogru, sonraki her guncellemede ESKI oneri
    # ile kalirdi — ve oneri bir FIYAT girdisi oldugu icin (on-secilen malzeme sepet
    # carpanini surer) edge modunda panel sunucudan FARKLI tutar gosterirdi: hash
    # "senkron" der, tutar ayrisir = sessiz fiyat sapmasi.
    "tavsiye_filament",
]

# satir_sql INSERT'inde YAZILAN ama ON CONFLICT/UPDATE yolunda BILEREK guncellenmeyen
# kolonlar — her biri icin GEREKCE (kapi gerekcesiz giris kabul etmez):
KASITLI_DISARIDA = {
    "id": "catisma anahtari — zaten esit, UPDATE'i anlamsiz",
    "seq": "katalog sirasi ILK eklemede sabitlenir; upsert'te korunur (rid/FTS rowid sabit)",
    "baski": "gizli .urun-kaynaklari.json'dan gelir; CI o dosyayi GORMEZ -> upsert yazsaydi "
             "her CI kosumu baski'yi '' yapip D1'den SILERDI (2026-07-18 olculdu)",
    "yayinda": "atomik yayin: 0 -> 1 gecisini YALNIZ yayin-kapisi yazar; icerik degisimi "
               "yayindaki urunu TASLAGA dusurmemeli",
}


def baski_haritasi():
    """Gizli .urun-kaynaklari.json'dan id -> baski onerisi. "-"/bos placeholder atlanir.
    Dosya yoksa (CI/baska makine) BOS harita — baski kolonu '' kalir, worker fallback'e duser.
    PUBLIC repoya sizmaz: yalnizca D1'e (ozel) yazilir, urunler.json'a DEGIL."""
    if not os.path.exists(KAYNAKLAR):
        return {}
    try:
        with open(KAYNAKLAR, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    harita = {}
    if isinstance(d, dict):
        for uid, kayit in d.items():
            if not isinstance(kayit, dict):
                continue
            b = (kayit.get("baski") or "").strip()
            if b and b != "-":
                harita[uid] = b
    return harita


# ─── BASKI ve DIFF-HASH AYRIMI (thrash onarimi, 2026-07-18) ───────────────────
# diff-upsert'in "hash" alani = SADECE arama.urun_hash(u) (PUBLIC icerik). baski ASLA
# hash'e KARISMAZ.
#   NEDEN (olculmus hata): eski etkin_hash() baski'yi hash'e katiyordu. Ama baski yalnizca
#   gizli .urun-kaynaklari.json'da; YEREL onu gorur, GitHub Actions (gitignore) GORMEZ.
#   Sonuc: yerel "baski'li hash", CI "baski'siz hash" yazip birbirini EZDI. Her push'ta
#   ~3.700 baski'li urun "degismis" gorunup yeniden yaziliyordu (12 urunluk batch'te
#   ~7.400 yazma = neredeyse tam rebuild; D1 gunluk 100.000 yazma limitine dogru kosuyordu).
#   Ustelik baski KOLONLAR'daydi -> CI content-upsert'i baski'yi '' yapip D1'den SILIYORDU.
# COZUM:
#   (1) hash iki ortamda AYNI (baski'siz) -> content thrash BITER.
#   (2) baski AYRI senkronlanir (baski_senkron_sql), yalnizca dosyasi olan ortam (yerel)
#       ve SADECE D1'dekinden farkliysa yazar -> degismeyen baski'ye dokunulmaz, CI silmez.
def baski_senkron_sql(uid, baski):
    """Tek urun icin SADECE baski kolonunu gunceller (content'e/hs'e dokunmaz -> hash ayni,
    FTS tetigi calismaz, ek satir yazmaz). Yalnizca baski FIILEN degistiyse cagrilir (main)."""
    return "UPDATE urunler SET baski=%s WHERE id=%s;" % (q(baski), q(uid))


# ─── PARAMETRIK TABAN FIYAT (D1 feed'i) ──────────────────────────────────────
# Parametrik urunun public fiyat'i BOS; taban fiyat jenerator/urunler/<id>.json
# tabanFiyatTL'de yasar. Bu bilgi D1'e HIC gitmiyordu -> Ege (bot) parametrik urunde
# fiyat goremiyor, siparisi insana devrediyor (sessiz satis kaybi). Cozum: taban_fiyat
# kolonu + HEDEFLI UPDATE (baski deseni). HASH'e KATILMAZ -> content thrash yok.
def taban_fiyat_haritasi():
    """jenerator/urunler/<id>.json -> {id: tabanFiyatTL(int)} (tabanFiyatTL None/eksik
    ATLANIR). build.py uret_taban_fiyatlar() ile AYNI dosya + AYNI kural (tek kaynak).
    Dizin yoksa (beklenmez; git'te izlenir) BOS harita -> taban_fiyat 0 kalir, Ege
    fallback'e duser (mevcut davranis, regresyon degil)."""
    harita = {}
    if not os.path.isdir(JEN_URUN_DIR):
        return harita
    for ad in sorted(os.listdir(JEN_URUN_DIR)):
        if not ad.endswith(".json"):
            continue
        try:
            with open(os.path.join(JEN_URUN_DIR, ad), encoding="utf-8") as f:
                sema = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        taban = sema.get("tabanFiyatTL")
        if taban is None:
            continue
        try:
            harita[sema.get("id") or ad[:-5]] = int(taban)
        except (TypeError, ValueError):
            continue
    return harita


def taban_senkron_sql(uid, taban):
    """Tek urun icin SADECE taban_fiyat kolonunu gunceller (content'e/hs'e DOKUNMAZ ->
    hash ayni, FTS tetigi (WHEN old.hs<>new.hs) CALISMAZ, ek FTS satiri yazmaz).
    Yalnizca taban FIILEN degistiyse cagrilir (taban_plan)."""
    return "UPDATE urunler SET taban_fiyat=%d WHERE id=%s;" % (int(taban), q(uid))


def izle(izleme, uid, sql, alanlar):
    """GERI-OKUMA IZI: bir SQL ifadesinin HANGI satirin HANGI alanlarini hangi degere
    getirmesi gerektigini kaydeder. `izleme` None ise (eski cagri yerleri / birim testler)
    NO-OP -> plan fonksiyonlarinin donus imzasi ve davranisi DEGISMEZ.

    🔴 NEDEN AYRI BIR AYNA DEGIL: beklenen deger, SQL'in URETILDIGI YERDE kaydedilir.
    Beklentiyi ikinci bir fonksiyonda yeniden turetmek [[ayna-kapi-kesif-ekseni]] sinifi
    bir drift acardi (plan degisir, ayna eskir, geri-okuma yanlis seyi dogrular)."""
    if izleme is not None:
        izleme.append({"id": uid, "sql": sql, "alanlar": alanlar})


def taban_plan(urunler, tabanlar, mevcut_taban, izleme=None):
    """SAF plan (canli D1'e DOKUNMAZ -> birim testi burayi cagirir). Doner: hedefli
    taban_fiyat UPDATE'leri listesi.
    - tabanlar   = {id: int}  jenerator semasindaki tabanFiyatTL (istenen deger)
    - mevcut_taban = {id: int} D1'deki mevcut taban_fiyat (yeni urun icin yok -> 0)
    KURAL: yalnizca semada taban VAR (parametrik) VE D1'deki degerden FARKLIYSA 1 UPDATE.
    Yeni urunde mevcut_taban 0 doner -> INSERT'ten SONRA (main ifade sirasi) UPDATE eder.
    Boylece 21 parametrik urun D1'de fiyati gorunur; hash'e dokunmadigi icin no-op tuzagina
    dusmez (diff_plan hash degismedi der ama taban_plan yine de senkronlar)."""
    if not tabanlar:
        return []
    out = []
    gorulen = set()
    for u in urunler:
        uid = u.get("id")
        if not uid or uid in gorulen:
            continue
        gorulen.add(uid)
        hedef = tabanlar.get(uid)
        if hedef is None:
            continue  # taban yok (normal urun / tabanFiyatTL null) -> taban_fiyat 0 kalir
        if int(hedef) != int(mevcut_taban.get(uid, 0)):
            sql = taban_senkron_sql(uid, hedef)
            out.append(sql)
            izle(izleme, uid, sql, {"taban_fiyat": int(hedef)})
    return out


# ─── KONFIGUR SEMASI (D1 feed'i — Worker bundle'inin ikizi) ──────────────────
# NEDEN: "olcuye ozel dekor" urununun fiyat semasi (boy araligi + capalar + malzeme
# katsayilari) IKI yerde yasiyordu: urun VERISI D1'de (otomatik, pre-push hook), SEMA
# Worker bundle'inda (shop/src/konfigurlar.js — ELLE uretilen artefakt + ELLE deploy).
# Iki kaynak = urun eklerken iki elle adim; 30 Tem'de ikisi de atlandi. Kolon o semayi
# D1'e tasir; urun eklenince hook zaten senkronlar.
#
# 🔴 NEDEN ICERIK-UPSERT'E KONMAZ (bu paketin EN KRITIK bulgusu, olculdu):
#   arama.urun_hash() konfigur alanini KAPSAMIYOR — yalnizca id/baslik/kategori/marka/
#   fiyat/gorsel/parametrik/haystack/aciklama/ege alanlarini ozetler. Yani BIR URUNUN
#   konfigur'u degisse (or. fiyat capasi 500 -> 700 TL) hash AYNI KALIR, diff_plan o urunu
#   "degismemis" sayar ve satiri yeniden YAZMAZ. konfigur KOLONLAR listesine (ON CONFLICT
#   UPDATE) konsaydi bu SESSIZ HATA uretirdi: D1'deki sema eskimis kalir, F4'te (Worker
#   D1'den okumaya cevrildiginde) musteriye ESKI fiyat cikardi ve hicbir uyari olmazdi.
#   Cozum taban_fiyat deseninin AYNISI: hash'e KARISMAZ + HEDEFLI UPDATE.
def konfigur_haritasi_d1(urunler):
    """urunler listesinden {id: kanonik-JSON-metin} + atlanan (bozuk) kayitlarin listesi.

    Doner: (harita, atlanan)  — atlanan = [(id, sebep), ...]

    DOGRULAMA TEK KAYNAK: konfigur-bundle-kapisi.py'nin _sema_dogrula + _sayi_normalize
    fonksiyonlari. Worker bundle'i ile D1 kolonu AYNI dogrulamadan ve AYNI sayi
    normalizasyonundan gecer -> ikisi insaatan ayrisamaz (1.0 vs 1 gibi yazim farki iki
    tarafta da ayni sekilde silinir).

    FAIL-CLOSED (bundle kapisiyla AYNI ilke, ama BLAST RADIUS'u dar): kapi (CI'da bloklayici)
    bozuk konfigur gorunce TUM artefakti uretmeyi reddeder. Burada ayni davranis TUM katalog
    senkronunu durdururdu — pre-push hook'u fail-open oldugu icin push yine gecer, ama D1
    bayat kalir ve Ege urunleri goremez (sessiz satis kaybi). Bu yuzden burada fail-closed
    SATIR DUZEYINDE uygulanir: bozuk kayit haritaya GIRMEZ -> konfigur_plan onu '' YAPAR ->
    Worker fail-closed 400 uretir (kalem WhatsApp'a duser). Okan kurali: "siparis kaybetmek
    yanlis tahsilattan iyidir". Atlanan kayitlar main'de GURULTULU basilir; CI'daki bundle
    kapisi zaten ayni veriyi kirmizi yakar."""
    harita = {}
    atlanan = []
    for u in urunler:
        if not isinstance(u, dict) or "konfigur" not in u:
            continue          # katalogun ~%99,9'u: konfigurlu DEGIL -> '' (sessiz, normal hal)
        uid = u.get("id")
        if not isinstance(uid, str) or not uid:
            atlanan.append(("<id YOK>", "id'siz konfigurlu urun kaydi"))
            continue
        if not u["konfigur"]:
            atlanan.append((uid, "konfigur alani VAR ama BOS/NULL"))
            continue
        sema_hata = kbk._sema_dogrula(uid, u["konfigur"])
        if sema_hata:
            atlanan.append((uid, sema_hata))
            continue
        harita[uid] = konfigur_kanonik(u["konfigur"])
    return harita, atlanan


def konfigur_kanonik(konf):
    """Konfigur objesini KANONIK JSON metne cevirir (D1'de saklanan bicim).
    sort_keys -> anahtar sirasi degisimi sahte UPDATE uretmez; kompakt ayirac -> D1'de
    gereksiz bayt yok; _sayi_normalize -> 1.0/1 yazim farki sahte UPDATE uretmez."""
    return json.dumps(kbk._sayi_normalize(konf), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


# ─── GENEL "METIN SEMA KOLONU" SENKRONU (konfigur bugun; sari seri YARIN) ────
# 🟡 NEDEN GENEL: konfigur TEK ornek DEGIL — parametrik ("olcuye ozel", sari seri) urunlerin
# semalari da AYNI ikiligi tasiyor: veri jenerator/urunler/<id>.json'da, Worker ise onlari
# shop/src/semalar.js'teki ELLE YAZILMIS statik import listesinden gorur (23 import satiri;
# konfigurlar.js'in aksine bir kapi tarafindan URETILMEZ bile). Bu yuzden "hash'e karismayan
# JSON sema kolonunu hedefli UPDATE ile senkronla" MAKINESI kolon-adindan bagimsiz yazildi;
# sari seri sirasi geldiginde yeni bir plan/SQL fonksiyonu DEGIL, yalnizca yeni bir kolon adi
# + kendi haritasi gerekir.
#
# NEDEN TEK JSON "zarf" KOLONU DEGIL (or. sema='{"konfigur":...,"parametrik":...}'):
#   1. ALTER TABLE ADD COLUMN bu semada O(1) ve deponun KANITLI deseni (GOC_KOLON ile bugune
#      dek 8 kolon boyle eklendi) -> "genisletilebilirlik" icin zarf sarti YOK.
#   2. AYRI kolon = AYRI sorgulanabilirlik: rapor/fail-closed kapisi `WHERE konfigur <> ''`
#      diyebilir; zarfta her satirin JSON'unu acmak gerekirdi.
#   3. IZOLASYON: sari seri semasindaki bir hata konfigur baytlarina DOKUNAMAZ (ayni satirin
#      ayni hucresini paylasmazlar).
#   4. Zarf, surum/goc alani (schemaVersion) ve zarf-ici birlestirme mantigi gerektirirdi =
#      bugun bedeli olan, karsiligi olmayan genellestirme.
def marka_kaynaklari(urunler):
    """MARKA TEK KAYNAKLARINI bir kez kurar: (mmb, evren, ek, sebep).

    sebep None = kuruldu; DOLU ise KURULAMADI (cagiran senkronu ATLAR).

    🔴 NEDEN ORTAK + BELLEKLI: marka_kanon ile marka_arama AYNI evreni kullanir ve
    `cip_evreni_markalari` katalogun TAMAMI uzerinde cip indeksini yeniden uretir. Iki ayri
    kurulum, pre-push kancasinda kosan bu araca bedava bir ikinci tam tarama eklerdi.
    (`model_kanon_haritasi` BILEREK KENDI kurulumunu yapar: o ayrica `gruplandir` da
    ister ve govdesi komsu bir kolonun isidir — buraya cekmek onun kabul testini bu dalin
    kapsamina sokardi. Yani kosum basina IKI kurulum var, UC degil.)
    🔴 BELLEK ANAHTARINDA `KOK` VAR: fail-closed dali (KOK bozuk -> sebep) bellek yuzunden
    SESSIZCE gecemesin — kok degisirse yeniden kurulur ve HATA yeniden olculur."""
    anahtar = (id(urunler), KOK)
    onceki = _MARKA_KAYNAK_BELLEK.get("anahtar")
    if onceki == anahtar:
        return _MARKA_KAYNAK_BELLEK["deger"]
    try:
        import marka_model_build as mmb                            # noqa: PLC0415
        with open(os.path.join(KOK, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
        evren = mmb.MarkaEvreni(index_html)
        ek = mmb.cip_evreni_markalari(urunler, index_html)
        sonuc = (mmb, evren, ek, None)
        if not evren.taninmis:
            sonuc = (None, None, None,
                     "marka evreni BOS (index.html TANINMIS_MARKALAR okunamamis)")
    except SystemExit as e:            # tek kaynak modulleri fail-closed sys.exit eder
        sonuc = (None, None, None, "SystemExit: %s" % (e.code,))
    except Exception as e:                                         # noqa: BLE001
        sonuc = (None, None, None, "%s: %s" % (type(e).__name__, e))
    # `urunler` referansi TUTULUR: yoksa liste cop toplanip id() baska bir nesneye
    # yeniden atanabilir ve bellek YANLIS katalogun evrenini dondurebilirdi.
    _MARKA_KAYNAK_BELLEK.update({"anahtar": anahtar, "deger": sonuc, "ref": urunler})
    return sonuc


_MARKA_KAYNAK_BELLEK = {}


def marka_kanon_haritasi(urunler):
    """{id: kanonik JSON dizi metni} — urunun UYE OLDUGU /marka/<slug>/ sayfalarinin
    kanonik adlari. Doner: (harita, sebep). sebep None = turetildi; DOLU ise TURETILEMEDI.

    🔴 IKINCI KATLAMA TABLOSU YOK: deger deponun TEK KAYNAGINDAN — ana sayfa marka
    filtresinin ta kendisi olan marka_model_build.marka_uyelikleri()'nden — turetilir
    (evren = index.html TANINMIS_MARKALAR portu + MARKA_ALIAS; ek evren = cip indeksi).
    Yeni bir liste ya da ikinci bir tablo ACILMAZ ([[ikiz-tanim-sessiz-ayrisma]]).

    🔴 FAIL-CLOSED YONU "ATLA", "BOSALT" DEGIL: tek kaynak okunamazsa (index.html bozuk,
    cip indeksi yuklenemedi...) BOS harita DONMEZ — sebep dondurulur ve cagiran senkronu
    ATLAR. Bos harita donseydi sema_plan her satiri '[]' YAPARDI: tek bir okuma hatasi
    TUM katalogu marka cipinden dusururdu. Bayat deger, bos degerden iyidir."""
    mmb, evren, ek, sebep = marka_kaynaklari(urunler)
    if sebep:
        return {}, sebep
    harita = {}
    for u in urunler:
        if not isinstance(u, dict):
            continue
        uid = u.get("id")
        if not uid:
            continue
        uyeler = mmb.marka_uyelikleri(u.get("marka") or [], evren, ek)
        if uyeler:
            # SIRA urunun kendi `marka` dizisinden gelir (marka_uyelikleri onu korur);
            # UYELIK anlami siradan BAGIMSIZDIR. Uyesiz urun haritaya GIRMEZ -> hedef
            # '[]' = D1 varsayilani -> UPDATE URETILMEZ (olcek kapisi; konfigur deseni).
            harita[uid] = json.dumps(uyeler, ensure_ascii=False, separators=(",", ":"))
    return harita, None


def model_kanon_haritasi(urunler):
    """{id: kanonik JSON dizi metni} — urunun UYE OLDUGU YAYIMLANAN /marka/<m>/<model>/
    sayfalarinin kanonik ETIKETLERI. Doner: (harita, sebep). sebep None = turetildi.

    🔴 IKINCI KATLAMA TABLOSU YOK (marka_kanon ile birebir ayni ilke): deger SAYFA
    URETICISININ KENDI YUKLEMINDEN — marka_model_build.gruplandir()'in kurdugu kovalardan —
    okunur. Kova["urunler"] TAM eslesmeyle giren urunlerin YANI SIRA kusak/varyant
    katlamasiyla giren urunleri de tasir ("Fiesta ST" -> Fiesta, "T4"/"T5" -> Transporter);
    yani ucun TAM ESITLIKLE kacirdigi tam da bu kalemler kolona yazilir.

    🔴 YALNIZ YAYIMLANAN KOVA (yayimlanir_mi): yayimlanmayan kovanin etiketi mimarin
    KAPATTIGI bir sayfanin adidir (rozet disi cift, model-olmayan cift, esik alti). Kanonik
    deger diye yazilsaydi kapali sayfa uc tarafindan geri acilirdi. Urun KAYBOLMAZ: kusak
    katlamasi onu ANA kovaya zaten koyar (olculdu). Cip evreni de bu kumenin ALTINDADIR.

    🔴 SIRA ALFABETIK: marka_kanon'un aksine urunun kendi dizisinden gelen dogal bir sira
    YOK. Sirasiz birakilsaydi kova yineleme sirasi degistiginde metin degisir ve HER senkron
    sahte UPDATE uretirdi (olcek kapisi).

    🔴 FAIL-CLOSED YONU "ATLA", "BOSALT" DEGIL: tek kaynak okunamazsa BOS harita DONMEZ —
    sebep dondurulur ve cagiran senkronu ATLAR. Bos harita sema_plan'a girseydi TUM katalog
    '[]' olurdu: tek okuma hatasi katalog capinda sessiz kayip. Bayat deger, bos degerden iyi.
    """
    try:
        import marka_model_build as mmb                            # noqa: PLC0415
        with open(os.path.join(KOK, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
        evren = mmb.MarkaEvreni(index_html)
        ek = mmb.cip_evreni_markalari(urunler, index_html)
        veri = mmb.gruplandir(urunler, evren, ek)
    except SystemExit as e:            # tek kaynak modulleri fail-closed sys.exit eder
        return {}, "SystemExit: %s" % (e.code,)
    except Exception as e:                                         # noqa: BLE001
        return {}, "%s: %s" % (type(e).__name__, e)
    if not evren.taninmis:
        return {}, "marka evreni BOS (index.html TANINMIS_MARKALAR okunamamis)"
    if not veri:
        return {}, "model kova evreni BOS (gruplandir hicbir marka dondurmedi)"
    toplam = {}
    for _marka, d in veri.items():
        for _canon, g in d["gruplar"].items():
            if not mmb.yayimlanir_mi(g):
                continue
            ad = g.get("display")
            if not ad:
                continue
            for p in g["urunler"]:
                uid = p.get("id") if isinstance(p, dict) else None
                if uid:
                    toplam.setdefault(uid, set()).add(ad)
    if not toplam:
        return {}, "yayimlanan model kovasi YOK (katlama/kuratorluk tek kaynagi bos okundu)"
    return ({uid: json.dumps(sorted(adlar), ensure_ascii=False, separators=(",", ":"))
             for uid, adlar in toplam.items()}, None)


def marka_alias_tersi(mmb, evren, ek_normlu):
    """{kanonik ad: [alias yazimi, ...]} — SAF, katalogdan BAGIMSIZ (birim testi burayi cagirir).

    🔴 IKINCI LISTE ACILMAZ: alias adlari index.html MARKA_ALIAS'tan (evren.marka_alias)
    gelir, kanonik karsilik ise `mmb.marka_adi_kanonu` — yani SORGU YOLUNUN KULLANDIGI
    YARGININ TA KENDISI — ile hesaplanir. Tabloya bakip degeri OKUMAK yerine yargiyi
    CALISTIRMAK sart: katlama kurali bir gun degisirse alias kolu kendiliginden izler.
    Kendine katlanan (k == alias) ya da taninmayan (k None) giris ATLANIR.
    Sira DETERMINISTIK (alfabetik) -> bayt-ayni kolon degeri, sahte UPDATE yok."""
    ters = {}
    for alias in sorted(getattr(evren, "marka_alias", None) or ()):
        k = mmb.marka_adi_kanonu(alias, evren, ek_normlu)
        if k and k != alias:
            ters.setdefault(k, []).append(alias)
    return ters


def marka_arama_haritasi(urunler):
    """{id: kanonik JSON dizi metni} — urunun MARKA SORGUSUYLA (`?q=<marka>`) eslesecegi
    marka adlari. Doner: (harita, sebep); marka_kanon_haritasi ile AYNI sozlesme.

    🔴 `model_kanon` ILE KARISTIRMA — AYRI EKSEN, AYRI HUKUM: model_kanon MODEL ekseninde
    ham `uyum[].model` ile BIRLESIM olarak okunur (kanon, hamin ust kumesi DEGIL). Bu kolon
    MARKA eksenindedir ve ham `marka` esitligini KAPSAR (olculdu: birlesim 0 kalem ekler),
    yani TEK BASINA okunur. Iki kolonun uctaki okuma kurali FARKLIDIR.

    🔴 KATLAMA/JETONLAMA GOVDESI BURADA YAZILMAZ. Deger DORT tek kaynaktan turer:
      1. `mmb.marka_uyelikleri`      -> UYELIK kolu   (sayfa/cip ile AYNI yuklem)
      2. `arama.baslik_marka_uyumlari` -> BASLIK kolu (baslikta TAM KELIME, uzun-once)
      3. `arama.marka_sorgusu_esler` -> GECIS YUKLEMININ TA KENDISI (suzgec)
      4. `marka_alias_tersi`         -> ALIAS kolu    (index.html MARKA_ALIAS + ayni yargi)
    Adaylar 1 ve 2'den toplanir, 3'ten GECIRILIR, sonra 4 ile GENISLETILIR. Yani kolon
    "birlesim" formulunu KOPYALAMAZ, uretim yuklemini CALISTIRIR: yuklem bir gun daralirsa
    (or. saf uyelige donulurse) kolon KENDILIGINDEN izler ([[ikiz-tanim-sessiz-ayrisma]]).

    🔴 "MARKA ADI MI" YARGISI DA TEK KAYNAKTAN: `mmb.marka_adi_kanonu` (index.html
    markaKatla portu + cip evreni). Baslik jetonlamasi VE alias kolu bu geri cagriyi
    kullanir; ikinci bir marka listesi ACILMAZ.

    🔴 ALIAS KOLU NEDEN VAR (5 Agu, MIMAR HUKMU): kolon "bu urun hangi marka SORGULARIYLA
    eslesir" degerini tasir. Site `?q=Vauxhall` sorgusunu `Opel`e KATLAR ve Opel'in TAM
    kumesini dondurur; kolon alias yazimini tasimasaydi uc o sorguyu HIC cozemez, musteri
    493 urunluk bir markayi canli aramada BULAMAZDI. Alternatif — uca alias tablosunu
    kopyalamak — IKIZ TANIM olurdu. Bu yuzden alias, KANONIGIN TASIYICI HER SATIRINA
    eklenir (yalniz `marka[]` alaninda 'Vauxhall' YAZAN satirlara DEGIL): site kumesi
    Opel'in TAMAMIDIR, alt kume yazmak yeni bir ayrisma acardi.
    🔴 `marka_kanon` BUNDAN ETKILENMEZ: alias YALNIZ bu kolona girer. Cip/sayfa evreni
    kanonik kalir, marka-invaryant-kapisi.py FILTRE ekseni bozulmaz.

    SIRA: UYELIK kolu (urunun `marka` dizisi sirasi) -> BASLIK kolunun ekledikleri (baslik
    sirasi) -> ALIAS kolu (alfabetik). Deterministik -> bayt-ayni deger, sahte UPDATE yok.

    FAIL-CLOSED YONU "ATLA", "BOSALT" DEGIL (marka_kanon ile ayni gerekce)."""
    mmb, evren, ek, sebep = marka_kaynaklari(urunler)
    if sebep:
        return {}, sebep
    ek_normlu = mmb.ek_marka_normlu(ek)
    # BELLEK: ayni jeton katalog boyunca on binlerce kez sorulur (18.533 urun x ~3 pencere).
    _bellek = {}

    def kanon(dizge):
        if dizge not in _bellek:
            _bellek[dizge] = mmb.marka_adi_kanonu(dizge, evren, ek_normlu)
        return _bellek[dizge]

    alias_ters = marka_alias_tersi(mmb, evren, ek_normlu)
    harita = {}
    for u in urunler:
        if not isinstance(u, dict):
            continue
        uid = u.get("id")
        if not uid:
            continue
        uyeler = mmb.marka_uyelikleri(u.get("marka") or [], evren, ek)
        baslik_uyum = arama.baslik_marka_uyumlari(u.get("baslik"), kanon)
        adaylar = list(uyeler) + [m for m in baslik_uyum if m not in uyeler]
        # 🔴 SUZGEC = URETIM YUKLEMI. `set(uyeler) | set(baslik_uyum)` yazmak AYNI sonucu
        # verirdi ama YUKLEMIN KOPYASI olurdu; boyle yazildiginda kolon yuklemi TASIR.
        deger = [m for m in adaylar
                 if arama.marka_sorgusu_esler(m, uyeler, baslik_uyum)]
        # ALIAS KOLU: kanonik ad kolona girdiyse onun alias yazimlari da girer (bkz. docstring).
        for m in list(deger):
            for a in alias_ters.get(m, ()):
                if a not in deger:
                    deger.append(a)
        if deger:
            # Eslesmesi olmayan urun haritaya GIRMEZ -> hedef '[]' = D1 varsayilani ->
            # UPDATE URETILMEZ (olcek kapisi; marka_kanon/konfigur deseni).
            harita[uid] = json.dumps(deger, ensure_ascii=False, separators=(",", ":"))
    return harita, None


def sema_senkron_sql(kolon, uid, deger):
    """Tek urun icin SADECE verilen METIN SEMA kolonunu gunceller (content'e/hs'e DOKUNMAZ ->
    hash ayni, FTS tetigi (WHEN old.hs<>new.hs) CALISMAZ, ek FTS satiri yazmaz).
    `kolon` SABIT bir tanimlayicidir (cagiran kod verir, kullanici girdisi DEGIL)."""
    return "UPDATE urunler SET %s=%s WHERE id=%s;" % (kolon, q(deger), q(uid))


def seq_hedefleri(urunler):
    """Kanonik katalog sirasini genis aralikli TAM SAYI seq haritasina cevir."""
    idler, gorulen = [], set()
    for u in urunler:
        uid = u.get("id") if isinstance(u, dict) else None
        if uid and uid not in gorulen:
            gorulen.add(uid)
            idler.append(uid)
    toplam = len(idler)
    return {uid: (toplam - i) * SEQ_ADIM for i, uid in enumerate(idler)}


def seq_sira_hali(urunler, mevcut_seq):
    """Doner: (kesirli id'ler, kanonik pozisyondan sapan id'ler, ornekler)."""
    beklenen = [u.get("id") for u in urunler if isinstance(u, dict) and u.get("id")]
    beklenen = list(dict.fromkeys(beklenen))
    def sira_anahtari(uid):
        try:
            return (0, -float(mevcut_seq[uid]), uid)
        except (TypeError, ValueError):
            return (1, 0, uid)
    canli = sorted(mevcut_seq, key=sira_anahtari)
    kesirli = [uid for uid, deger in mevcut_seq.items()
                if isinstance(deger, bool) or not isinstance(deger, int)]
    # D1'de eksik bir BAS blok, geri kalan her dogru urunun indeksini kaydirir. Pozisyonu
    # ham indeksle kiyaslamak o durumda 92 eksigi 23.795 sapma diye sisirir. Once ortak
    # kumenin goreli sirasini kiyasla; eksikleri ayrica sapma say.
    beklenen_kume = set(beklenen)
    eksik = [uid for uid in beklenen if uid not in mevcut_seq]
    beklenen_ortak = [uid for uid in beklenen if uid in mevcut_seq]
    canli_ortak = [uid for uid in canli if uid in beklenen_kume]
    ters = [uid for i, uid in enumerate(beklenen_ortak)
            if i >= len(canli_ortak) or canli_ortak[i] != uid]
    sapma = eksik + [uid for uid in ters if uid not in set(eksik)]
    ornek = []
    for uid in sapma[:10]:
        i = beklenen.index(uid)
        ornek.append((uid, mevcut_seq.get(uid), i + 1,
                      canli[i] if i < len(canli) else None))
    return kesirli, sapma, ornek


def seq_normalize(urunler):
    """Canli D1'de YALNIZ seq kolonunu kanonik siradan yeniden yazar ve dogrular."""
    yerel_id = len(seq_hedefleri(urunler))
    r = sorgu("SELECT id, seq FROM urunler")
    satirlar = (r[0].get("results") or []) if r else []
    once = len(satirlar)
    mevcut = {s["id"]: s.get("seq") for s in satirlar}
    kesirli, sapma, ornek = seq_sira_hali(urunler, mevcut)
    print("KESIRLI_SEQ_ONCE=%d" % len(kesirli))
    print("SAPAN_SEQ_ONCE=%d" % len(sapma))
    print("ORNEK_10=" + json.dumps(ornek, ensure_ascii=False, separators=(",", ":")))
    print("D1_SATIR_ONCE=%d" % once)
    print("YEREL_ID=%d" % yerel_id)
    if once != yerel_id or set(mevcut) != set(seq_hedefleri(urunler)):
        sys.exit("!! SEQ NORMALIZASYONU DURDU: D1 id kumesi kanonik katalogla ayni degil; "
                 "satir ekleme/silme YASAK oldugu icin once katalog senkronunu duzelt.")
    hedef = seq_hedefleri(urunler)
    ifadeler = ["UPDATE urunler SET seq=%d WHERE id=%s;" % (hedef[uid], q(uid))
                for uid in hedef if mevcut.get(uid) != hedef[uid]]
    for i in range(0, len(ifadeler), PARCA):
        yaz, _ = dosya_calistir("\n".join(ifadeler[i:i + PARCA]))
        print("  seq parca %d/%d — yazilan satir: %d"
              % (i // PARCA + 1, (len(ifadeler) + PARCA - 1) // PARCA, yaz))
    r2 = sorgu("SELECT id, seq FROM urunler")
    son_satirlar = (r2[0].get("results") or []) if r2 else []
    sonra = len(son_satirlar)
    son = {s["id"]: s.get("seq") for s in son_satirlar}
    son_kesirli, son_sapma, _ = seq_sira_hali(urunler, son)
    print("D1_SATIR_SONRA=%d" % sonra)
    print("SEQ_TAM_SAYI_SONRA=%s" % ("EVET" if not son_kesirli else "HAYIR"))
    fark = [uid for uid in hedef if son.get(uid) != hedef[uid]]
    if sonra != once or fark or son_sapma:
        # GERI ALMA da yalniz seq kolonuna dokunur. Eszamanli baska bir yazar satir
        # ekledi/sildiyse o satiri uydurmayiz; bu arac kendi seq yazisini geri cevirir.
        geri = ["UPDATE urunler SET seq=%s WHERE id=%s;" % (str(mevcut[uid]), q(uid))
                for uid in mevcut]
        for i in range(0, len(geri), PARCA):
            dosya_calistir("\n".join(geri[i:i + PARCA]))
        sys.exit("!! SEQ NORMALIZASYONU GERI ALINDI: satir %d->%d · deger farki=%d · "
                 "sira farki=%d. DUR." % (once, sonra, len(fark), len(son_sapma)))
    print("SEQ NORMALIZASYONU DOGRULANDI: %d satir, yalniz seq, kanonik sira ✅" % sonra)


def sema_plan(kolon, urunler, hedefler, mevcut, izleme=None, varsayilan=""):
    """SAF plan (canli D1'e DOKUNMAZ -> birim testi burayi cagirir). Doner: hedefli UPDATE'ler.
    - hedefler = {id: kanonik JSON}  urunler.json'dan turetilen ISTENEN deger
    - mevcut   = {id: metin}         D1'deki mevcut deger (yeni urun icin yok -> varsayilan)
    - varsayilan                     KOLONUN D1 DEFAULT'u. konfigur icin '' , marka_kanon
                                     icin '[]'. 🔴 SABIT '' VARSAYMAK OLCEK KAPISINI KIRARDI:
                                     JSON-dizi kolonlarda hedefsiz urunun hedefi '[]'dir ve
                                     D1'deki deger de '[]'; '' ile karsilastirilsaydi HER
                                     senkron 15.000+ gereksiz UPDATE uretirdi.

    KURAL: her urun icin HEDEF = hedefler.get(id, varsayilan); hedef D1'dekinden FARKLIYSA 1 UPDATE.
    - Semali urun: kanonik JSON yazilir.
    - Semasiz urun (~15.000): hedef '' = D1'deki varsayilan -> UPDATE URETILMEZ. (Bu sart
      olmasa her senkron 15.000 gereksiz yazma uretirdi — olcek kapisi burasi.)
    - Semasi KALDIRILAN / BOZULAN urun: hedef '' , D1'de dolu -> TEMIZLEYEN 1 UPDATE.
      taban_fiyat plani bu dalda "dokunma" der (stale birakir); sema'da stale deger =
      YANLIS FIYAT oldugu icin bilerek TEMIZLENIR (Worker fail-closed 400 -> WhatsApp).
    - Yeni urunde mevcut '' doner -> INSERT'ten SONRA (main ifade sirasi) UPDATE eder."""
    out = []
    gorulen = set()
    for u in urunler:
        if not isinstance(u, dict):
            continue
        uid = u.get("id")
        if not uid or uid in gorulen:
            continue
        gorulen.add(uid)
        hedef = hedefler.get(uid, varsayilan)
        if hedef != (mevcut.get(uid, varsayilan) or varsayilan):
            sql = sema_senkron_sql(kolon, uid, hedef)
            out.append(sql)
            izle(izleme, uid, sql, {kolon: hedef})
    return out


def konfigur_senkron_sql(uid, konfigur):
    """konfigur kolonu icin sema_senkron_sql (ince sarmalayici — cagri yerleri okunur kalsin)."""
    return sema_senkron_sql("konfigur", uid, konfigur)


def konfigur_plan(urunler, konfigurlar, mevcut_konfigur, izleme=None):
    """konfigur kolonu icin sema_plan (ince sarmalayici). Kurallar sema_plan docstring'inde."""
    return sema_plan("konfigur", urunler, konfigurlar, mevcut_konfigur, izleme)


def marka_kanon_plan(urunler, kanonlar, mevcut_kanon, izleme=None):
    """marka_kanon kolonu icin sema_plan (ince sarmalayici). VARSAYILAN '[]' — kolonun D1
    DEFAULT'u odur; uyesiz urun icin UPDATE URETILMEZ (olcek kapisi)."""
    return sema_plan("marka_kanon", urunler, kanonlar, mevcut_kanon, izleme,
                     varsayilan="[]")


def model_kanon_plan(urunler, kanonlar, mevcut_kanon, izleme=None):
    """model_kanon kolonu icin sema_plan (ince sarmalayici). VARSAYILAN '[]' — kolonun D1
    DEFAULT'u odur; hicbir yayimlanan model kovasina uye olmayan urun icin UPDATE URETILMEZ
    (olcek kapisi: katalogun ~%52'si model kovasi disinda)."""
    return sema_plan("model_kanon", urunler, kanonlar, mevcut_kanon, izleme,
                     varsayilan="[]")


def marka_arama_plan(urunler, aramalar, mevcut_arama, izleme=None):
    """marka_arama kolonu icin sema_plan (ince sarmalayici). VARSAYILAN '[]' — kolonun D1
    DEFAULT'u odur; eslesmesi olmayan urun icin UPDATE URETILMEZ (olcek kapisi)."""
    return sema_plan("marka_arama", urunler, aramalar, mevcut_arama, izleme,
                     varsayilan="[]")


def diff_plan(urunler, mevcut, baskilar, baski_yetki, mseq, mevcut_seq=None, izleme=None):
    """SAF diff (canli D1'e DOKUNMAZ -> birim testi burayi cagirir).
    mevcut = {id: (hash, baski)}. mevcut_seq = {id: seq} (OPSIYONEL; verilmezse legacy
    davranis birebir korunur -> eski birim testleri IMZA DEGISMEDEN gecer).
    Doner: (yeni, degisen, baski_guncelle, silinen, gorulen).
    - yeni/degisen: content upsert SQL'leri (baski INSERT VALUES'ta, CONFLICT'te DEGIL).
    - baski_guncelle: SADECE baski FIILEN degistiginde 1 UPDATE (yalniz baski_yetki=EVET).

    🔴 SEQ SANDVIC ONARIMI (30 Tem, olculdu — parite-test.js/parite-ege.js SIRA farki,
    26/1199 + 13/845 sorgu, anka-kusu-serit-dekoratif-figur / yarasa-serit-dekoratif-figur):
    Eski kod "yeni" (D1'de id'si bulunamayan) urunun dizide HER ZAMAN BASTA (gercekten en
    yeni) oldugunu VARSAYIYORDU -> sonraki=mseq+1 (katalogun TEPESI) verirdi. Bu varsayim
    NORMAL akista (yeni urun hep dizinin BASINA eklenir) dogrudur, ama bir urunun id'si
    AYNI dizi pozisyonunda DEGISTIRILDIGINDE (Okan'in "X = Y yeniden markalandi" gibi
    rename commit'leri: ayni urun, yeni id/baslik/gorsel) kirilir — eski id SILINIR, yeni
    id BRAND-NEW sanilir ve dizideki GERCEK (mid-array) konumu yok sayilarak katalogun
    TEPESINE atanir. KANIT (canli D1, olculdu): anka-kusu-serit-dekoratif-figur (dizi
    indeks 582, hemen ONCESI yarasa-serit-dekoratif-figur indeks 581) seq=14853 aldi —
    yarasa'nin seq'i olan 14852'den BUYUK -> ORDER BY seq DESC yarasa'yi anka-kusu'nun
    ONUNE koymasi gerekirken TERSINE cevirdi.
    COZUM: mevcut_seq verilmisse, her "yeni" id icin dizide ondan ONCE (HEAD tarafinda)
    duran, D1'de HALA BILINEN (mevcut_seq'te olan) bir komsu var mi diye PASS A ile
    bakilir. Yoksa (gercekten tepede) eski davranis (sonraki=mseq+1, ...) AYNEN kalir.
    Varsa, bu "yeni" id GERCEKTE mid-array'dir -> iki komsu arasindaki TAM SAYI orta
    nokta kullanilir. Tam sayi araligi kalmadiysa kesir uretmek YASAKTIR; arac fail-loud
    durur ve `--seq-normalize` ister."""
    mevcut_seq = mevcut_seq or {}
    yeni, degisen, baski_guncelle = [], [], []
    gorulen = set()
    sonraki = mseq

    # PASS A (dizi BASI -> SONU, tek gecis, mevcut_seq bossa NO-OP): her "olasi yeni" id
    # icin en yakin HEAD-tarafi (dizide ONCESINDE duran) D1'de HALA BILINEN komsunun seq'i.
    # None = bu id ile dizinin BASI arasinda D1'de bilinen hicbir komsu yok -> GERCEKTEN
    # tepede -> asagida legacy/sinirsiz havuz (sonraki) GECERLI kalir.
    ust_sinir = {}
    if mevcut_seq:
        son_bilinen = None
        gorulen_a = set()
        for u in urunler:
            uid = u.get("id")
            if not uid or uid in gorulen_a:
                continue
            gorulen_a.add(uid)
            if uid in mevcut_seq:
                son_bilinen = mevcut_seq[uid]
            else:
                ust_sinir[uid] = son_bilinen

    # ANA GECIS — TERS: dizinin BASI en yeni -> en yuksek seq alsin (eski davranisla
    # AYNI sira/anlam). `taban` = su ana dek (TAIL'den buraya) gezilen en yakin BILINEN
    # (D1'de mevcut) komsunun seq'i — mid-array "yeni" id'ler icin ALT sinir.
    taban = 0.0
    for u in reversed(urunler):
        uid = u.get("id")
        if not uid or uid in gorulen:
            continue
        gorulen.add(uid)
        h = arama.urun_hash(u)          # baski'SIZ — yerel ve CI AYNI degeri uretir
        kayit = mevcut.get(uid)         # (hash, baski) veya None
        eski_h = kayit[0] if kayit else None
        eski_baski = kayit[1] if kayit else ""
        baski = baskilar.get(uid, "")
        if eski_h is None:
            ust = ust_sinir.get(uid)
            if ust is None:
                # Gercekten tepede (D1'de bilinen hicbir HEAD-tarafi komsu yok) -> eski
                # davranis: katalogun ustune bas (sonraki=mseq+1, +2, ...).
                sonraki += 1
                atanan = sonraki
            else:
                # MID-ARRAY yeni id (rename / araya sikisma): yalniz TAM SAYI.
                alt = int(taban)
                yuksek = int(ust)
                if taban == 0:
                    # Katalogun en SONUNA ekleme: alt komsu yoktur; son bilinenin
                    # altindaki tam sayi guvenlidir (offline fikstur/geri doldurma yolu).
                    atanan = yuksek - 1
                elif yuksek - alt <= 1:
                    sys.exit("!! SEQ TAM SAYI ARALIGI TUKENDI: %s (alt=%s ust=%s). "
                             "Kesirli seq yazilmaz; once python3 tools/d1-sync.py "
                             "--seq-normalize kos." % (uid, taban, ust))
                else:
                    atanan = alt + (yuksek - alt) // 2
            taban = atanan
            sql = satir_sql(u, atanan, arama.haystack(u), h, baski)  # INSERT baski'yi da yazar
            yeni.append(sql)
            # YENI satir: INSERT VALUES baski'yi DA yazar -> beklentiye baski GIRER.
            izle(izleme, uid, sql, {"hash": h, "baslik": u.get("baslik") or "",
                                    "kategori": u.get("kategori") or "", "baski": baski,
                                    "tur": arama.tur_kanonik(u),
                                    "stokta": arama.stokta_kanonik(u)})
        else:
            if eski_h != h:
                sql = satir_sql(u, 0, arama.haystack(u), h, baski)  # seq ON CONFLICT'te korunur
                degisen.append(sql)
                # DEGISEN satir: ON CONFLICT yolu KOLONLAR'i gunceller, baski BILEREK DISARIDA
                # (bkz. KOLONLAR yorumu) -> beklentiye baski GIRMEZ, yoksa CI'da her degisen
                # urun sahte "baski uyusmazligi" verirdi (YANLIS-POZITIF = herkesin push'u kirilir).
                izle(izleme, uid, sql, {"hash": h, "baslik": u.get("baslik") or "",
                                        "kategori": u.get("kategori") or "",
                                        # tur/stokta KOLONLAR'da -> ON CONFLICT yolu da yazar
                                        # (baski'nin aksine; bkz. KOLONLAR yorumu).
                                        "tur": arama.tur_kanonik(u),
                                        "stokta": arama.stokta_kanonik(u)})
            # ICERIK degismis de degismemis de olsa: bu id D1'de zaten VAR, seq'i korunuyor
            # -> bir SONRAKI (daha HEAD tarafindaki) mid-array yeni id icin dogru ALT sinir.
            if uid in mevcut_seq:
                taban = mevcut_seq[uid]
        # baski senkronu: YALNIZ yetki varsa (CI atlar -> baski'yi silmez/ezmez),
        # MEVCUT satir icin (yeni urun baski'yi INSERT'te aldi), ve FIILEN degistiyse.
        if baski_yetki and eski_h is not None and baski != eski_baski:
            sql = baski_senkron_sql(uid, baski)
            baski_guncelle.append(sql)
            izle(izleme, uid, sql, {"baski": baski})
    silinen = [i for i in mevcut if i not in gorulen]
    return yeni, degisen, baski_guncelle, silinen, gorulen


# ══════════════════════════════════════════════════════════════════════════════
# GOC INDEKSLERI — ALTER'lardan SONRA kosan DDL'ler + hallerinin TEK KAYNAGI
# ══════════════════════════════════════════════════════════════════════════════
# Indeksler ALTER'lardan SONRA kosmak ZORUNDA (yoksa "no such column: yayinda"; olculdu
# 31 Tem canli D1'de: d1-sema.sql icine konunca --sema TAMAMEN dustu, cunku o dosya kolon
# gocunden ONCE uygulanir ve tablo zaten var oldugu icin CREATE TABLE IF NOT EXISTS
# atlanir). IF NOT EXISTS -> idempotent.
#
# 🔴 NEDEN KAYIT DEFTERI (sadece SQL listesi DEGIL) — TEK-YONLU KAPI PENCERESI:
# Bir goc "ALTER'lar + kismi UNIQUE indeks" seklindeyse, ALTER'lar GECIP indeks DUSERSE
# kolonlar VAR olur ama benzersizlik korumasi YOKTUR. Yazma tarafi genelde yalniz KOLON
# yoklugunu yakalar -> INSERT'ler gecer, yaris KORUMASIZ kalir. O pencerede tek bir ikiz
# satir olusursa `CREATE UNIQUE INDEX` BIR DAHA ASLA kurulamaz: `--sema` o noktadan sonra
# HER kosumda duser ve geri donus 3 adimli ELLE temizlik ister (kismi indeks dururken
# `DROP COLUMN` engellidir -> once DROP INDEX). Yani "sessiz basari" burada onarilabilir
# bir hata degil, KAPIYI KILITLEYEN bir hatadir.
# Bu yuzden her indeks BEYAN EDILIR (ad + gerekli kolonlar + benzersizlik + ikiz sorgusu)
# ve `--sema` kurulum IDDIASINI geri-okumayla KANITA cevirir; `--durum` "kolon VAR ama
# indeks YOK" halini AYRI ve GORUNUR bir hal olarak raporlar (eskiden YESIL goruyordu).
#
# gerekli: indeksin ihtiyac duydugu KOLONLAR. Hepsi yoksa indeks "UYGULANMAZ"dir (o goc
#   bu tabloya henuz gelmedi) — kirmizi DEGIL. BIR KISMI varsa "KOLON-YARIM" = KIRMIZI
#   (ALTER'lar yarida kalmis).
GOC_INDEKS = [
    {"ad": "urunler_yayin", "tablo": "urunler", "yayin": True,
     "gerekli": ("yayinda", "seq"), "benzersiz": False,
     "sql": "CREATE INDEX IF NOT EXISTS urunler_yayin     ON urunler(yayinda, seq DESC);"},
    {"ad": "urunler_yayin_kat", "tablo": "urunler", "yayin": True,
     "gerekli": ("yayinda", "kategori", "seq"), "benzersiz": False,
     "sql": "CREATE INDEX IF NOT EXISTS urunler_yayin_kat ON urunler(yayinda, kategori, seq DESC);"},
    # SIPARIS KANALI — site DISI uclarin (or. WhatsApp siparis ucu) dis referansi.
    # KISMI benzersizlik: dis_no BOS olan satirlar (site siparisleri) indekse GIRMEZ, yoksa
    # tum eski satirlar tek bir ('site','') anahtarinda cakisirdi.
    # ✅ KOLONLAR ARTIK BU DOSYADA (1 Agu 2026, siparis ucu dali birlestirildi):
    # GOC_KOLON_SIPARIS icinde kanal + dis_no var. Kayit onlardan ONCE yazilmisti; artik
    # ayni kosumda kolonlar ALTER ile gelir ve indeks HEMEN kurulup DOGRULANIR. Goc
    # kosmamis bir veritabaninda hal yine "UYGULANMAZ"dir (gurultu YOK).
    # 🔴 INDEKS ADI `siparisler_kanal_dis_no` — dal `siparisler_dis_no` diyordu; kayit
    # defterindeki ad KAZANDI (hal makinesi indeksi ADIYLA arar, iki ad ayrisirsa hal
    # sonsuza dek "INDEKS-YOK" kalirdi). d1-sema.sql da bu ada hizalandi.
    {"ad": "siparisler_kanal_dis_no", "tablo": "siparisler", "yayin": False,
     "gerekli": ("kanal", "dis_no"), "benzersiz": True,
     "sql": "CREATE UNIQUE INDEX IF NOT EXISTS siparisler_kanal_dis_no "
            "ON siparisler(kanal, dis_no) WHERE dis_no <> '';",
     # IKIZ SORGUSU — indeksi ENGELLEYEN satirlari SAYAR. 🔴 SILMEZ/TEMIZLEMEZ: veri silme
     # mimar/Okan karari; arac yalniz KAC TANE oldugunu ve elle temizlik gerektigini soyler.
     "ikiz_sql": "SELECT kanal, dis_no, COUNT(*) AS n FROM siparisler WHERE dis_no <> '' "
                 "GROUP BY kanal, dis_no HAVING COUNT(*) > 1"},
]

# SOZLESME SEMBOLU (tools/ara-maliyet-kapisi.py bunu ADIYLA import eder): atomik yayin
# DDL'leri. Kayit defterinden TURETILIR — ikinci bir elle liste tutulsaydi ikisi sessizce
# ayrisirdi (bir indeks eklenir, digeri kurulmaz; kimse gormez).
YAYIN_INDEKS = [ix["sql"] for ix in GOC_INDEKS if ix.get("yayin")]

# Hal adlari (tek kaynak — hem --sema hem --durum ayni kelimeleri kullansin).
IX_UYGULANMAZ = "UYGULANMAZ"    # gerekli kolonlarin HICBIRI yok -> bu goc henuz gelmedi
IX_KURULU = "KURULU"            # kolonlar VAR + indeks VAR
IX_INDEKS_YOK = "INDEKS-YOK"    # 🔴 kolonlar VAR ama indeks YOK = YARIDA KALMIS GOC
IX_KOLON_YARIM = "KOLON-YARIM"  # 🔴 kolonlarin BIR KISMI var = ALTER'lar yarida kalmis


def canli_indeks_adlari():
    """Canli veritabanindaki indeks adlari (kume). Tek SELECT — satir YAZMAZ."""
    r = sorgu("SELECT name FROM sqlite_master WHERE type='index'")
    return {s["name"] for s in ((r[0].get("results") or []) if r else [])}


def sema_hali(kayit=None):
    """Her goc indeksinin CANLI hali. Doner: [{ad, tablo, hal, eksik_kolon, benzersiz}].

    OKUMA MALIYETI: her TABLO icin 1 PRAGMA + TOPLAM 1 sqlite_master SELECT'i.
    """
    kayit = GOC_INDEKS if kayit is None else kayit
    indeksler = canli_indeks_adlari()
    kolonlar = {t: kolonlari_oku(t) for t in sorted({ix["tablo"] for ix in kayit})}
    hal = []
    for ix in kayit:
        var = kolonlar.get(ix["tablo"], set())
        eksik = [k for k in ix["gerekli"] if k not in var]
        if len(eksik) == len(ix["gerekli"]):
            h = IX_UYGULANMAZ
        elif eksik:
            h = IX_KOLON_YARIM
        elif ix["ad"] in indeksler:
            h = IX_KURULU
        else:
            h = IX_INDEKS_YOK
        hal.append({"ad": ix["ad"], "tablo": ix["tablo"], "hal": h,
                    "eksik_kolon": eksik, "benzersiz": ix.get("benzersiz", False),
                    "ikiz_sql": ix.get("ikiz_sql")})
    return hal


def ikiz_say(ikiz_sql):
    """Kismi UNIQUE indeksi ENGELLEYEN ikiz satirlari SAY.

    Doner: (grup_sayisi, fazla_satir, ornekler) · olculemezse None.
    🔴 SILME/TEMIZLEME YOK — bu fonksiyon yalnizca SELECT kosar. Hangi satirin silinecegi
    TICARI bir karardir (siparis kaydi!), araca birakilmaz.
    """
    if not ikiz_sql:
        return None
    try:
        r = sorgu(ikiz_sql)
    except SystemExit:
        return None
    satirlar = (r[0].get("results") or []) if r else []
    fazla = sum(int(s.get("n") or 0) - 1 for s in satirlar)
    ornek = [", ".join("%s=%r" % (k, v) for k, v in s.items()) for s in satirlar[:5]]
    return len(satirlar), fazla, ornek


def sema_sorunlari(hal):
    """Halden INSAN OKUR sorun satirlari uret (bos liste = temiz). Ikiz SAYIMI dahil."""
    satirlar = []
    for h in hal:
        if h["hal"] == IX_KOLON_YARIM:
            satirlar.append(
                "YARIDA KALMIS GOC (%s.%s): kolonlarin bir kismi EKSIK: %s — ALTER'lar "
                "tamamlanmadan indeks KURULAMAZ." % (h["tablo"], h["ad"],
                                                     ", ".join(h["eksik_kolon"])))
        elif h["hal"] == IX_INDEKS_YOK:
            s = ("YARIDA KALMIS GOC (%s.%s): KOLONLAR VAR ama INDEKS YOK." %
                 (h["tablo"], h["ad"]))
            if h["benzersiz"]:
                s += (" Bu KISMI UNIQUE indeks bir YARIS KORUMASIDIR: kurulmadigi surece "
                      "ikiz satir olusabilir ve olustugu anda indeks BIR DAHA KURULAMAZ "
                      "(tek-yonlu kapi).")
            satirlar.append(s)
            sayim = ikiz_say(h.get("ikiz_sql")) if h["benzersiz"] else None
            if sayim is None:
                if h["benzersiz"]:
                    satirlar.append("   ikiz satir sayimi OLCULEMEDI — 'ikiz yok' SAYILMAZ.")
            elif sayim[0]:
                satirlar.append(
                    "   🔴 IKIZ SATIR ZATEN VAR: %d anahtar · %d FAZLA satir. Indeks bu "
                    "haliyle KURULAMAZ; ELLE TEMIZLIK sart (arac SILMEZ — siparis kaydi "
                    "silmek mimar/Okan karari)." % (sayim[0], sayim[1]))
                for o in sayim[2]:
                    satirlar.append("     - %s" % o)
                satirlar.append(
                    "   Geri alma 3 ADIMLI ve SIRALI: (1) ikizleri ticari kararla temizle, "
                    "(2) CREATE UNIQUE INDEX'i kur, (3) teyit: d1-sync.py --durum. "
                    "Kismi indeks DURURKEN `DROP COLUMN` ENGELLIDIR -> once DROP INDEX.")
            else:
                satirlar.append(
                    "   ikiz satir: 0 — indeks SIMDI kurulabilir: "
                    "python3 tools/d1-sync.py --sema")
    return satirlar


def kolon_goc():
    """Eksik kolonlari ekle, ardindan goc indekslerini kur ve KURULDUGUNU DOGRULA.

    Doner: True = goc TAM (kolon + indeks DOGRULANDI) · False = YARIDA KALDI.
    🔴 Cagiran False'u SIFIR-DISI cikisa cevirmek ZORUNDA: "sessiz basari" bu gocte
    tek-yonlu kapi acar (bkz. GOC_INDEKS yorumu).
    Idempotent: SQLite'ta 'ADD COLUMN IF NOT EXISTS' yok, o yuzden once table_info'ya
    bakilir (kor ALTER ikinci calismada patlardi).
    """
    for tablo, kolonlar in (("urunler", GOC_KOLON), ("siparisler", GOC_KOLON_SIPARIS)):
        r = sorgu("PRAGMA table_info(%s)" % tablo)
        var = {s["name"] for s in (r[0].get("results") or [])}
        eksik = [(ad, tip) for ad, tip in kolonlar if ad not in var]
        if not eksik:
            print("%s kolonlari tam — goc gerekmedi" % tablo)
            continue
        dosya_calistir("\n".join(
            "ALTER TABLE %s ADD COLUMN %s %s;" % (tablo, ad, tip) for ad, tip in eksik))
        print("%s eklenen kolon: %s" % (tablo, ", ".join(ad for ad, _ in eksik)))
        # 🔴 SIRA UYARISI (sessiz-hata nobeti): `yayinda` DEFAULT 0 ile eklenir -> ALTER
        # anindan itibaren MEVCUT TUM satirlar TASLAK olur. Okuma tarafi (worker'daki
        # `yayinda=1` sarti) bu andan sonra ve GERIYE DOLDURMADAN once yayina alinirsa
        # TUM KATALOG bir anda gizlenir. Dogru sira: --sema -> --geriye-doldur -> (dogrula)
        # -> worker deploy. Uyari GURULTULU basilir; kimse "gormedim" diyemesin.
        if tablo == "urunler" and any(ad == "yayinda" for ad, _ in eksik):
            print("!! ATOMIK YAYIN: `yayinda` kolonu DEFAULT 0 ile eklendi — MEVCUT TUM "
                  "SATIRLAR TASLAK durumda.")
            print("!! Worker'daki `yayinda=1` sartini YAYINA ALMADAN ONCE sunu kos:")
            print("!!   python3 tools/yayin-kapisi.py --geriye-doldur")
            print("!! Teyit: python3 tools/yayin-kapisi.py --durum  (taslak sayisi ~0 olmali)")

    # ── INDEKSLER: kolonlar TAMAMLANDIKTAN sonra (kolon yokken CREATE INDEX tum --sema
    # kosumunu dusururdu — olculdu, bkz. GOC_INDEKS yorumu). Kurulum DENENIR; DUSERSE
    # yutulmaz ama kosum burada BITMEZ: asagidaki DOGRULAMA hukmu bassin diye hata
    # metni saklanir (yoksa "wrangler dustu" der, TEK-YONLU KAPI'yi kimse anlamazdi).
    kurulum_hatasi = {}
    once = {h["ad"]: h for h in sema_hali()}        # TEK olcum, sonra bellekten okunur
    for ix in GOC_INDEKS:
        h = once.get(ix["ad"]) or {"hal": IX_UYGULANMAZ}
        if h["hal"] in (IX_UYGULANMAZ, IX_KOLON_YARIM):
            continue                      # kolonlar hazir degil -> DDL denenmez
        if h["hal"] == IX_KURULU:
            continue                      # idempotent: zaten kurulu
        try:
            dosya_calistir(ix["sql"])
            print("indeks kuruldu (IDDIA): %s" % ix["ad"])
        except SystemExit as e:           # wrangler SIFIR-DISI (or. UNIQUE ihlali)
            kurulum_hatasi[ix["ad"]] = str(e.code)
            print("!! indeks KURULAMADI: %s" % ix["ad"])

    # ── DOGRULAMA — "kuruldu" IDDIASI burada KANITA cevrilir (geri-okuma deseni) ──────
    hal = sema_hali()
    sorunlar = sema_sorunlari(hal)
    print("goc indeks hali: " + " · ".join("%s=%s" % (h["ad"], h["hal"]) for h in hal))
    for ad, mesaj in sorted(kurulum_hatasi.items()):
        print("!! %s DDL hatasi: %s" % (ad, (mesaj or "")[:400]))
    if sorunlar:
        print("!! YARIDA KALMIS GOC — asagidaki hal(ler) FAIL-CLOSED:")
        for s in sorunlar:
            print("   " + s)
        return False
    return True


def uyum_metin(u):
    """`uyum` alaninin D1'de SAKLANAN bicimi: kanonik JSON DIZI metni.

    KAYNAK arama.uyum_kanonik(u) — urun_hash'i besleyen AYNI fonksiyon. Ikinci bir
    turetme yolu ACILMAZ: acilsaydi hash bir degeri, kolon baskasini gorurdu ve
    "hash senkron der, kolon bayat" ayrismasi dogardi ([[ikiz-tanim-sessiz-ayrisma]]).

    BICIM (yeni bir bicim ICAT EDILMEDI, mevcut karmasik alanlardan alindi):
      * JSON dizi metni + ensure_ascii=False -> `marka` kolonunun deseni (o da JSON dizi;
        Turkce karakterler kacissiz, D1'de okunur kalir).
      * sort_keys=True + kompakt ayirac -> `konfigur_kanonik` deseni: oge icindeki anahtar
        SIRASI degisimi (ayni veri, baska yazim) sahte bir UPDATE uretmesin, D1'de
        gereksiz bayt durmasin. urun_hash'in dis json.dumps'i da sort_keys=True kullanir
        -> hash'in gordugu normalizasyon ile kolonunki AYNI.
    BOS hal '[]' (kolon DEFAULT'u ile ayni) -> okuma ucu JSON.parse'i kosulsuz uygulayabilir.
    """
    return json.dumps(arama.uyum_kanonik(u), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def tavsiye_filament_metin(u):
    """`tavsiyeFilament` alaninin D1'de SAKLANAN bicimi: kanonik JSON DIZI metni.

    KAYNAK arama.tavsiye_filament_kanonik(u) — urun_hash'i besleyen AYNI fonksiyon
    (uyum_metin deseni). Ikinci bir turetme yolu ACILMAZ: acilsaydi hash bir degeri,
    kolon baskasini gorurdu ([[ikiz-tanim-sessiz-ayrisma]]).

    🔴 LISTE SIRALANMAZ: `sort_keys` yalniz SOZLUK anahtarlarini etkiler; dizi SIRASI
    girdideki gibi kalir ve kalmalidir — filament_ortak.on_secim() KALAN ILK adi
    on-secer, yani sira bir FIYAT girdisidir.
    🔴 TIP KUSURUNDA ISTISNA ATAR (fail-closed): bozuk kayit sessizce '[]' ya da
    tek elemanli diziye CEVRILMEZ; cagiran urunleri_oku()'daki tip kapisi zaten
    SAYIYLA durdurmus olur.
    BOS hal '[]' (kolon DEFAULT'u ile ayni) -> okuma ucu JSON.parse'i kosulsuz uygular.
    """
    return json.dumps(arama.tavsiye_filament_kanonik(u), ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"))


def satir_sql(u, seq, hs, h, baski=""):
    """Tek urun icin upsert. ON CONFLICT -> rid/seq korunur (FTS rowid'i sabit kalir)."""
    g = (u.get("gorseller") or [None])[0]
    e_bas = arama.ege_baslik(u)
    e_gov = arama.ege_govde(u)
    degerler = [
        q(u["id"]), q(h), str(seq), q(u.get("baslik") or ""), q(u.get("kategori") or ""),
        q(json.dumps(u.get("marka") or [], ensure_ascii=False)), q(u.get("fiyat") or ""),
        q(g), "1" if u.get("parametrik") else "0", q(hs),
        q(u.get("aciklama") or ""), q(u.get("ege") or ""),
        q(e_bas), q(arama.koke_cevir(e_bas)), q(e_gov), q(arama.koke_cevir(e_gov)),
        q(baski),
        # TICARI HAL — KANONIK degerler (arama.py tek kaynak). stokta TIRNAKSIZ yazilir:
        # q() ile yazilsaydi INTEGER kolona '0' METNI girer, uc taraftaki JS'te
        # Boolean('0') === true olur ve TUKENMIS urun STOKTA gorunurdu.
        q(arama.tur_kanonik(u)), str(arama.stokta_kanonik(u)),
        # ALT KATEGORI — KANONIK deger (arama.py tek kaynak; hash de AYNI fonksiyondan
        # besleniyor -> "hash degisti ama kolon degismedi" ayrismasi imkansiz).
        q(arama.altkategori_kanonik(u)),
        # UYUM — KANONIK JSON dizi metni (uyum_metin; arama.uyum_kanonik tek kaynak, hash de
        # AYNI fonksiyondan besleniyor -> "hash degisti ama kolon degismedi" ayrismasi imkansiz).
        q(uyum_metin(u)),
        # TAVSIYE FILAMENT — KANONIK JSON dizi metni (tavsiye_filament_metin;
        # arama.tavsiye_filament_kanonik tek kaynak, hash de AYNI fonksiyondan besleniyor
        # -> "hash degisti ama kolon degismedi" ayrismasi imkansiz).
        q(tavsiye_filament_metin(u)),
    ]
    # ATOMIK YAYIN: YENI satir DAIMA taslak (yayinda=0) girer. Kolon SQL'de ACIKCA
    # yazilir (DEFAULT'a guvenilmez): DEFAULT sonradan degistirilirse ya da tablo baska
    # bir yolla kurulursa yeni urun SESSIZCE yayinda dogar ve pencere geri gelirdi.
    # ON CONFLICT/UPDATE yolunda yayinda YOKTUR (KOLONLAR listesi) -> mevcut yayinda=1
    # satirin icerigi degisse de urun Ege'den KAYBOLMAZ.
    return (
        "INSERT INTO urunler (id,hash,seq,baslik,kategori,marka,fiyat,gorsel,parametrik,hs,"
        "aciklama,ege,hs_baslik,hs_baslik_kok,hs_govde,hs_govde_kok,baski,tur,stokta,"
        "altkategori,uyum,tavsiye_filament,yayinda) VALUES ("
        + ",".join(degerler) + ",0"
        + ") ON CONFLICT(id) DO UPDATE SET "
        + ", ".join("%s=excluded.%s" % (k, k) for k in KOLONLAR) + ";"
    )


# ─── YAZMA SONRASI GERI-OKUMA (write-verify) ─────────────────────────────────
# Tasarim kararlari (31 Tem, olculdu):
#  * NE OKUNUR: yalnizca YAZILAN satirlar, KENDI anahtarlariyla (id). Tam tablo taramasi
#    her yazmada pahali olurdu.
#  * NE KARSILASTIRILIR: satirin VARLIGI DEGIL, YAZILAN ALAN DEGERLERI. Varlik kontrolu
#    31 Tem vakasini YAKALAMAZDI: satir zaten VARDI, sadece kategori'si eskiydi.
#  * hash NEDEN YETERLI (content upsert icin): satir_sql hash'i icerikle AYNI ifadede yazar
#    ve hash = arama.urun_hash(u) (id/baslik/kategori/marka/fiyat/gorsel/parametrik/haystack/
#    aciklama/ege). Yani hash D1'de dogruysa o upsert FIILEN uygulanmistir. baslik+kategori
#    AYRICA okunur: hata mesaji insan tarafindan okunabilir olsun (31 Tem vakasi bir kategori
#    vakasiydi ve mesaj "beklenen Tamirat · bulunan Oyun/Hobi" demeli).
#  * HASH'E KARISMAYAN kolonlar (baski / taban_fiyat / konfigur) hedefli UPDATE ile yazilir;
#    onlar KENDI adlariyla dogrulanir (hash onlari GORMEZ — bu tam da sema kolonlarinin
#    var olma sebebi).
#  * ORNEKLEME YOK: yazilan id kumesinin TAMAMI dogrulanir. Sinir asagida BEYAN edilir.
# tur/stokta AYRICA okunur (hash onlari GORDUGU halde): bu ikisi bir VAAT tasiyor
# ("stokta var") ve tip hatasi sessiz — '0' METNI uc taraftaki JS'te true okunur. Ayni
# SELECT'e iki kolon eklemek bedava; karsiligi, yanlis tipin/degerin canliya yerlesemedigi.
GERI_OKUMA_KOLONLARI = ["hash", "baslik", "kategori", "baski", "taban_fiyat",
                        "tur", "stokta"]

# ICERIK UPSERT'inin CALISABILMESI icin canli tabloda BULUNMASI ZORUNLU kolonlar.
# konfigur'un aksine bunlar atlanabilir DEGIL: satir_sql'in INSERT listesindedirler,
# yoksa HER upsert "no such column" ile duser. Bu yuzden main() basinda GURULTULU
# olculur — kriptik yarim yazma yerine tek satirlik "kos: --sema" tanisi.
ZORUNLU_KOLONLAR = ["tur", "stokta", "uyum", "tavsiye_filament"]

# NEDEN `uyum` GERI_OKUMA_KOLONLARI'nda DEGIL (bilincli, gerekceli): uyum icerik upsert'i ile
# hash ile AYNI ifadede yazilir -> hash D1'de dogruysa o upsert FIILEN uygulanmistir (baslik/
# marka/fiyat/aciklama gibi diger icerik kolonlariyla ayni garanti). tur/stokta'nin AYRICA
# okunmasinin sebebi TIP ekseniydi ('0' METNI JS'te true okunur); uyum TEXT kolonudur, o sinif
# hata YOK. Ustelik tam-tablo geri-okuma yolunda (>800 id) uyum'u SELECT'e koymak her senkronda
# 16.874 satirlik JSON govdesini bosuna cekerdi.
# `tavsiye_filament` de AYNI GEREKCEYLE GERI_OKUMA_KOLONLARI'nda DEGIL: TEXT kolonudur (tip
# ekseni yok), icerik upsert'i ile hash ile AYNI ifadede yazilir ve tip kusuru zaten
# urunleri_oku()'daki FAIL-CLOSED kapida — yani D1'e ULASMADAN — durdurulur.

# BEYAN EDILEN OLCEK SINIRI: yazilan id sayisi bu esigi asarsa hedefli `IN (...)` parcalari
# yerine TEK tam-tablo SELECT'i kullanilir. 🔴 ORNEKLEME DEGIL — iki yol da yazilan id'lerin
# TAMAMINI dogrular, yalnizca sorgu BICIMI degisir (sessiz ornekleme YASAK; --kendini-test
# V34/V35 tam bunu olcer: 30 urunun 1'i kacinca KIRMIZI yanmali).
# OLCUM (31 Tem, canli D1, 15.163 satir; 7 kolon geri-okuma):
#     1 id -> 1 sorgu 2,6 s · 30 id -> 1 sorgu 2,8 s · 400 id -> 1 sorgu 2,9 s
#   1.200 id -> 3 sorgu 9,0 s · 2.500 id -> tam-tablo 1 sorgu 3,8 s · 15.188 id -> 4,0 s
# Yani: tam-tablo ~3,9 s SABIT; hedefli ~2,9 s/parca (PARCA=400). Kesisim ~2 parca (800 id).
TAM_OKUMA_ESIGI = 800


def geri_okuma_norm(kolon, deger):
    """Karsilastirma normalizasyonu. D1 (JSON) tarafi ile plan tarafi ayni TIPTE olmali,
    yoksa '700' != 700 gibi SAHTE uyusmazlik cikar = yanlis-pozitif = herkesin push'u kirilir."""
    if kolon == "taban_fiyat":
        try:
            return int(deger or 0)
        except (TypeError, ValueError):
            return -1
    if kolon == "stokta":
        # TIP EKSENI: D1'den '0' METNI donerse (kolon yanlislikla TEXT olarak kurulmus)
        # int('0') == 0 ile SESSIZCE esitlenirdi. Bu yuzden tip GEVSETILMEZ: bool/int
        # DISINDAKI her sey uyusmazlik olarak raporlanir (-9 hicbir mesru degerle esit degil).
        if isinstance(deger, bool) or not isinstance(deger, int):
            return -9
        return int(deger)
    return "" if deger is None else str(deger)


def beklenti_kur(izleme, silinen):
    """izleme kayitlari + silinen id'lerden {id: {"alanlar": {...}|None, "sql": [...]}}.
    alanlar None = satir D1'de HIC OLMAMALI (silme dogrulamasi).
    sql listesi YENIDEN DENEME icin saklanir (ayni ifadeler tekrar uygulanir)."""
    beklenti = {}
    for kayit in izleme:
        g = beklenti.setdefault(kayit["id"], {"alanlar": {}, "sql": []})
        g["alanlar"].update(kayit["alanlar"])
        g["sql"].append(kayit["sql"])
    for uid in silinen:
        beklenti[uid] = {"alanlar": None,
                         "sql": ["DELETE FROM urunler WHERE id=%s;" % q(uid)]}
    return beklenti


def beklenti_karsilastir(beklenti, bulunan):
    """SAF (D1'e/dosyaya DOKUNMAZ -> birim testi burayi cagirir).
    Doner: [(id, kolon, beklenen, bulunan)] — BOS liste = yazma DOGRULANDI."""
    fark = []
    for uid in sorted(beklenti):
        alanlar = beklenti[uid]["alanlar"]
        satir = bulunan.get(uid)
        if alanlar is None:                       # silinmis OLMALI
            if satir is not None:
                fark.append((uid, "<satir>", "SILINMIS", "HALA VAR"))
            continue
        if satir is None:                         # yazilmis OLMALI ama satir YOK
            fark.append((uid, "<satir>", "VAR", "SATIR YOK"))
            continue
        for kolon in sorted(alanlar):
            b = geri_okuma_norm(kolon, alanlar[kolon])
            v = geri_okuma_norm(kolon, satir.get(kolon))
            if b != v:
                fark.append((uid, kolon, b, v))
    return fark


def geri_oku(idler, konfigur_kolonu, marka_kanon_kolonu=False, model_kanon_kolonu=False,
             marka_arama_kolonu=False):
    """Yazilan id'leri D1'den geri oku. Doner: ({id: satir}, olcum)."""
    kolonlar = (["id"] + GERI_OKUMA_KOLONLARI
                + (["konfigur"] if konfigur_kolonu else [])
                + (["marka_kanon"] if marka_kanon_kolonu else [])
                + (["model_kanon"] if model_kanon_kolonu else [])
                + (["marka_arama"] if marka_arama_kolonu else []))
    sec = ", ".join(kolonlar)
    idler = sorted(idler)
    t0 = time.time()
    bulunan, okunan, sorgu_sayisi = {}, 0, 0
    if len(idler) > TAM_OKUMA_ESIGI:
        r = sorgu("SELECT %s FROM urunler" % sec)
        sorgu_sayisi = 1
        okunan += ((r[0].get("meta") or {}).get("rows_read") or 0) if r else 0
        istenen = set(idler)
        for s in ((r[0].get("results") or []) if r else []):
            if s["id"] in istenen:
                bulunan[s["id"]] = s
        yol = "tam-tablo"
    else:
        for i in range(0, len(idler), PARCA):
            parca = idler[i:i + PARCA]
            r = sorgu("SELECT %s FROM urunler WHERE id IN (%s)"
                      % (sec, ",".join(q(x) for x in parca)))
            sorgu_sayisi += 1
            okunan += ((r[0].get("meta") or {}).get("rows_read") or 0) if r else 0
            for s in ((r[0].get("results") or []) if r else []):
                bulunan[s["id"]] = s
        yol = "hedefli"
    return bulunan, {"id": len(idler), "sorgu": sorgu_sayisi, "okunan": okunan,
                     "sure": time.time() - t0, "yol": yol}


def geri_okuma_dogrula(beklenti, konfigur_kolonu, marka_kanon_kolonu=False,
                       model_kanon_kolonu=False, marka_arama_kolonu=False):
    """Yazilan satirlari geri okur, ALAN DEGERLERINI karsilastirir; uyusmazlikta ayni
    ifadeleri BIR KEZ yeniden uygular ve TEKRAR okur. Doner: kalan fark listesi (bos = OK).
    SONSUZ DONGU YOK — tam 2 tur, ucuncu deneme yapilmaz."""
    if not beklenti:
        print("geri-okuma: yazilan satir yok — dogrulanacak sey yok")
        return []
    bulunan, olcum = geri_oku(list(beklenti), konfigur_kolonu, marka_kanon_kolonu,
                              model_kanon_kolonu, marka_arama_kolonu)
    print("geri-okuma [%s]: %d id | %d sorgu | okunan satir: %d | %.2f s"
          % (olcum["yol"], olcum["id"], olcum["sorgu"], olcum["okunan"], olcum["sure"]))
    fark = beklenti_karsilastir(beklenti, bulunan)
    if not fark:
        print("GERI-OKUMA DOGRULANDI: %d satirin yazilan alan degerleri / silinmesi D1'de "
              "teyit edildi ✅" % len(beklenti))
        return []
    kotu = sorted({f[0] for f in fark})
    print("!! GERI-OKUMA UYUSMAZLIGI (1. tur): %d satir / %d alan — YENIDEN DENENIYOR"
          % (len(kotu), len(fark)))
    for uid, kolon, b, v in fark[:10]:
        print("   - %s . %s : beklenen %r · bulunan %r" % (uid, kolon, b, v))
    onarim = []
    for uid in kotu:
        onarim += beklenti[uid]["sql"]
    yaz, _ = dosya_calistir("\n".join(onarim))
    print("   yeniden deneme: %d ifade uygulandi (wrangler IDDIASI: %d satir yazildi)"
          % (len(onarim), yaz))
    bulunan2, olcum2 = geri_oku(kotu, konfigur_kolonu, marka_kanon_kolonu,
                                model_kanon_kolonu, marka_arama_kolonu)
    print("   2. geri-okuma [%s]: %d id | %d sorgu | okunan satir: %d | %.2f s"
          % (olcum2["yol"], olcum2["id"], olcum2["sorgu"], olcum2["okunan"], olcum2["sure"]))
    fark2 = beklenti_karsilastir({u: beklenti[u] for u in kotu}, bulunan2)
    if not fark2:
        print("GERI-OKUMA DOGRULANDI (2. turda): 1. tur yazmasi KACMISTI, onarildi ✅")
        return []
    return fark2


def icerik_ekseni(urunler, d1_hash):
    """SAF (D1'e/dosyaya DOKUNMAZ -> birim testi burayi cagirir). --durum ICERIK EKSENI:
    urun_hash duzeyinde D1 ↔ urunler.json karsilastirmasi.
    Doner: (uyusmaz, eksik, fazla); uyusmaz = [(id, beklenen_hash, d1_hash)].

    🔴 NEDEN SAYI YETMEZ: bir urunun ALANI degisip D1'e yazilamazsa satir SAYISI AYNI kalir
    -> eski --durum YESIL yanardi. Bu eksen tam o vakayi kirmizi yakar."""
    gorulen = set()
    uyusmaz, eksik = [], []
    for u in urunler:
        uid = u.get("id")
        if not uid or uid in gorulen:
            continue
        gorulen.add(uid)
        b = arama.urun_hash(u)
        v = d1_hash.get(uid)
        if v is None:
            eksik.append(uid)
        elif v != b:
            uyusmaz.append((uid, b, v))
    fazla = sorted(i for i in d1_hash if i not in gorulen)
    return uyusmaz, eksik, fazla


# ═══════════════════════════════════════════════════════════════════════════════
# TURETILMIS KOLON EKSENI (4. eksen) — urun_hash'in KAPSAMADIGI kolonlarin BAYATLIGI
# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 OLCULEN SESSIZ HATA (6 Agu 2026): `marka_arama` (ve kardesleri marka_kanon /
# model_kanon / konfigur / taban_fiyat) BILEREK urun_hash'in DISINDADIR — hedefli UPDATE
# ile senkronlanirlar (bkz. sema_plan / taban_plan). Ama --durum'un UC ekseni de bu
# kolonlara HIC BAKMIYORDU:
#     SAYI ekseni   -> satir sayisi degismez (kolon guncellemesi satir EKLEMEZ/SILMEZ)
#     SEMA ekseni   -> indeks/kolon VARLIGINA bakar, DEGERINE degil
#     ICERIK ekseni -> urun_hash'i kiyaslar; hash bu kolonlari OZETLEMEZ -> gormez
# Sonuc: kolon BAYAT kalirken UC EKSEN DE YESIL yanardi. Olculen vaka: bir urun partisinden
# sonra canli `marka_arama` kolonunda Honda 1898 (olmasi gereken 1979), Grom 43 (44) —
# Ege marka aramasinda yeni urunleri GOREMEZ, site gorur, hicbir alarm calmaz
# ([[ege-d1-bagimliligi]] sinifi sessiz satis kaybi).
#
# 🔴 IKINCI YUKLEM YOK: bu eksen kolonun degerini YENIDEN HESAPLAMAZ. Kolonu URETEN govdeyi
# (marka_arama_haritasi / marka_kanon_haritasi / model_kanon_haritasi / konfigur_haritasi_d1
# / taban_fiyat_haritasi) ve senkronun KENDI plan fonksiyonunu CALISTIRIR. Bayatlik tanimi
# bu yuzden "bir senkron bu kolona YAZAR MIYDI?" sorusunun ta kendisidir; uretim kurali bir
# gun degisirse eksen kendiliginden izler ([[ikiz-tanim-sessiz-ayrisma]]).
# 🔴 FAIL-CLOSED: uretici govde deger uretemezse (tek kaynak okunamadi, kolon canlida yok,
# modul dustu) sonuc YESIL DEGIL "OLCULEMEDI"dir ve cikis kodu bunu yansitir. Senkron
# yolunda ayni hal "DOKUNMA" (bayat > bos) demektir ve exit 0 doner — burada olculebilirlik
# ISTENIR, bilinmezlik yesil SAYILMAZ.

# HASH'IN (dolayisiyla ICERIK ekseninin) KAPSADIGI D1 kolonlari — IKINCI LISTE ACILMAZ,
# KOLONLAR'dan TURETILIR. Gerekce: KOLONLAR, icerik upsert'inin ON CONFLICT yolunda hash ILE
# AYNI IFADEDE yazilan kolonlardir; hash D1'de dogruysa o kolonlar FIILEN yazilmistir
# (satir_sql / GERI_OKUMA_KOLONLARI yorumlarindaki ayni gerekce). `id` catisma anahtaridir.
HASH_KAPSAMI = frozenset(KOLONLAR) | {"id"}

# TURETILMIS EKSENIN BILEREK DISINDA BIRAKILANLAR — her biri GEREKCELI (gerekcesiz giris
# YOK; kapsam_acigi() gerekcesi olmayan her kolonu OLCULEMEDI sayar).
EKSEN_DISI = {
    "rid": "SQLite rowid — urunler.json'dan TURETILMEZ, kiyaslanacak bir hedefi yok",
    "seq": "ozel turetilmis eksen: --durum tam-sayi + urunler.json kanonik sirasinda "
           "monotonluk iddiasini ayrica olcer",
    "baski": "gizli .urun-kaynaklari.json'dan gelir; dosya CI'da YOKTUR -> hedef degeri "
             "ORTAMA BAGLI. Bu eksene alinsaydi CI'da her kosum OLCULEMEDI yakardi. "
             "🔴 ACIK KALAN YUZEY: baski bayatligi bugun HICBIR eksende olculmuyor",
    "yayinda": "atomik yayin hali — yayin-kapisi.py yazar, urunler.json'dan turetilmez "
               "(taslak/yayinda ayrimi icerik degil SUREC halidir)",
    "release_id": "atomik yayin damgasi — yayin-kapisi.py yazar, ayni sinif",
}

TK_GUNCEL = "GUNCEL"
TK_BAYAT = "BAYAT"
TK_OLCULEMEDI = "OLCULEMEDI"


def konfigur_hedefleri(urunler):
    """(harita, sebep) sozlesmesine INCE sarmalayici — uretici govde konfigur_haritasi_d1.
    `atlanan` (bozuk konfigur) BILEREK yutulur: senkron yolunda da hedef '' olur (satir
    duzeyinde fail-closed), yani eksen senkronun GORDUGU hedefi gorur."""
    harita, _atlanan = konfigur_haritasi_d1(urunler)
    return harita, None


def taban_hedefleri(urunler):
    """(harita, sebep) sarmalayici — uretici govde taban_fiyat_haritasi (katalogu okumaz,
    jenerator semalarini okur).
    🔴 BOS HARITA = OLCULEMEDI, "guncel" DEGIL: taban_plan bos haritada [] doner (dokunma),
    yani sema dizini okunamadiginda eksen SESSIZCE YESIL yanardi — tam da kapattigimiz hal."""
    del urunler
    harita = taban_fiyat_haritasi()
    if not harita:
        return None, ("jenerator/urunler semasi BOS/okunamadi (%s) — taban fiyat hedefi "
                      "URETILEMEDI" % JEN_URUN_DIR)
    return harita, None


# HASH'A KARISMAYAN + urunler.json/git'teki semalardan TURETILEN kolonlarin KAYIT DEFTERI.
# Her giris: uretici govde (harita) + senkronun KENDI plan fonksiyonu + cozum komutu.
TURETILMIS_KAYIT = [
    {"kolon": "konfigur", "hedef": konfigur_hedefleri, "plan": konfigur_plan,
     "coz": "python3 tools/konfigur-bundle-kapisi.py"},
    {"kolon": "taban_fiyat", "hedef": taban_hedefleri, "plan": taban_plan,
     "coz": "python3 tools/d1-sync.py   (taban_plan hedefli UPDATE uretir)"},
    {"kolon": "marka_kanon", "hedef": marka_kanon_haritasi, "plan": marka_kanon_plan,
     "coz": "python3 tools/marka-invaryant-kapisi.py"},
    {"kolon": "model_kanon", "hedef": model_kanon_haritasi, "plan": model_kanon_plan,
     "coz": "python3 tools/model-kanon-d1-test.py"},
    {"kolon": "marka_arama", "hedef": marka_arama_haritasi, "plan": marka_arama_plan,
     "coz": "python3 tools/marka-arama-d1-test.py"},
]


def kapsam_acigi(tablo_kolonlari, kayit=None):
    """CANLI tabloda olup HICBIR eksenin kapsamadigi kolonlar (sirali liste).

    🔴 BU FONKSIYON OLMASA EKSEN KENDI KORLUGUNU TASIRDI: `marka_arama` tam olarak boyle
    dogdu — kolon canliya girdi, hash'e girmedi, kayit defterine de girmedi ve hicbir kapi
    onu SORMADI. Yeni bir kolon uc kumeden birine (hash kapsami / turetilmis kayit /
    GEREKCELI eksen disi) YAZILMADAN --durum yesil YANAMAZ."""
    kayit = TURETILMIS_KAYIT if kayit is None else kayit
    kapsanan = HASH_KAPSAMI | {k["kolon"] for k in kayit} | set(EKSEN_DISI)
    return sorted(k for k in tablo_kolonlari if k not in kapsanan)


def turetilmis_mevcut(tablo_kolonlari, kayit=None):
    """CANLI D1'deki turetilmis kolon degerleri: {kolon: {id: deger}}. TEK SELECT.
    Tabloda OLMAYAN kolon donen haritaya GIRMEZ -> cagiran onu OLCULEMEDI sayar."""
    kayit = TURETILMIS_KAYIT if kayit is None else kayit
    kolonlar = [k["kolon"] for k in kayit if k["kolon"] in tablo_kolonlari]
    if not kolonlar:
        return {}
    r = sorgu("SELECT id, %s FROM urunler" % ", ".join(kolonlar))
    satirlar = (r[0].get("results") or []) if r else []
    out = {}
    for kolon in kolonlar:
        if kolon == "taban_fiyat":     # taban_plan INT kiyaslar ('700' != 700 tuzagi)
            out[kolon] = {s["id"]: int(s.get(kolon) or 0) for s in satirlar}
        else:
            out[kolon] = {s["id"]: (s.get(kolon) or "") for s in satirlar}
    return out


def turetilmis_eksen(urunler, tablo_kolonlari, mevcutlar, kayit=None):
    """SAF (canli D1'e DOKUNMAZ — canli degerler `mevcutlar` ile GELIR) -> birim testi
    burayi cagirir, wrangler gerekmez.
    Doner: [{kolon, hal, sayi, sebep, ornek, coz}]; hal ∈ {GUNCEL, BAYAT, OLCULEMEDI}."""
    kayit = TURETILMIS_KAYIT if kayit is None else kayit
    out = []
    for k in kayit:
        kolon, coz = k["kolon"], k["coz"]

        def _olculemedi(sebep, _kolon=kolon, _coz=coz):
            out.append({"kolon": _kolon, "hal": TK_OLCULEMEDI, "sayi": None,
                        "sebep": sebep, "ornek": [], "coz": _coz})

        if kolon not in tablo_kolonlari:
            _olculemedi("kolon CANLI tabloda YOK (--sema kosmadi)")
            continue
        if kolon not in mevcutlar:
            _olculemedi("canli deger OKUNAMADI (SELECT bu kolonu dondurmedi)")
            continue
        try:
            hedefler, sebep = k["hedef"](urunler)
        except SystemExit as e:        # tek kaynak modulleri fail-closed sys.exit eder
            hedefler, sebep = None, "SystemExit: %s" % (e.code,)
        except Exception as e:                                     # noqa: BLE001
            hedefler, sebep = None, "%s: %s" % (type(e).__name__, e)
        if sebep or hedefler is None:
            _olculemedi("URETICI GOVDE hedef uretemedi: %s" % (sebep or "harita None"))
            continue
        izleme = []
        try:
            plan = k["plan"](urunler, hedefler, mevcutlar[kolon], izleme)
        except SystemExit as e:
            _olculemedi("PLAN govdesi dustu: SystemExit: %s" % (e.code,))
            continue
        except Exception as e:                                     # noqa: BLE001
            _olculemedi("PLAN govdesi dustu: %s: %s" % (type(e).__name__, e))
            continue
        out.append({"kolon": kolon, "hal": TK_BAYAT if plan else TK_GUNCEL,
                    "sayi": len(plan), "sebep": None, "coz": coz,
                    "ornek": [(i["id"], i["alanlar"].get(kolon)) for i in izleme[:5]]})
    return out


def turetilmis_sorunlari(hal, acik=()):
    """Halden INSAN OKUR sorun satirlari (bos liste = temiz).
    🔴 OLCULEMEDI de SORUNDUR: "bilmiyorum"u yesile saymak, kapatmaya calistigimiz
    sessizligin ta kendisi olurdu (fail-closed)."""
    satirlar = []
    for h in hal:
        if h["hal"] == TK_BAYAT:
            s = ("BAYAT TURETILMIS KOLON (%s): %d satirin CANLI degeri urunler.json'dan "
                 "TURETILEN degerle AYNI DEGIL. Bu kolon urun_hash'in KAPSAMI DISINDADIR -> "
                 "SAYI/SEMA/ICERIK eksenlerinin UCU DE bunu GOREMEZ (Ege bu kolondan okuyan "
                 "sorguda urunleri BULAMAZ, site bulur). Coz: %s"
                 % (h["kolon"], h["sayi"], h["coz"]))
            for uid, deger in h["ornek"]:
                s += "\n      - %s -> olmasi gereken: %s" % (uid, deger)
            satirlar.append(s)
        elif h["hal"] == TK_OLCULEMEDI:
            satirlar.append(
                "OLCULEMEDI (%s): %s — kolonun guncel olup olmadigi BILINMIYOR; YESIL "
                "SAYILMAZ (fail-closed). Coz: %s" % (h["kolon"], h["sebep"], h["coz"]))
    for kolon in acik:
        satirlar.append(
            "KAPSAM ACIGI (%s): canli tabloda VAR ama HICBIR eksen kapsamiyor — ne hash "
            "(KOLONLAR), ne TURETILMIS_KAYIT, ne GEREKCELI EKSEN_DISI. Bu kolon bugun "
            "sessizce bayatlayabilir. Coz: kolonu uc kumeden BIRINE yaz (d1-sync.py)."
            % kolon)
    return satirlar


def durum_uyumlu(d1_sayisi, urunler_benzersiz):
    """--durum FAIL-LOUD teyidi: D1 satir sayisi urunler.json'daki BENZERSIZ id sayisina
    ESIT mi? SAF fonksiyon (D1'e/dosyaya DOKUNMAZ) -> birim testi burayi cagirir, wrangler
    gerekmez. d1_sayisi None ise (D1 okunamadi / COUNT None dondu) UYUMSUZ say = fail-loud.
    NEDEN benzersiz: sync id'ye gore dedup eder (diff_plan 'gorulen'); D1'de her benzersiz id
    tam 1 satir olur, dolayisiyla dogru invariant D1 COUNT(*) == benzersiz id sayisi."""
    if d1_sayisi is None:
        return False
    try:
        return int(d1_sayisi) == int(urunler_benzersiz)
    except (TypeError, ValueError):
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# KENDINI TEST — OFFLINE kabul testi (canli D1'e / aga / urunler.json'a DOKUNMAZ)
# ═══════════════════════════════════════════════════════════════════════════════
# TASARIM: sahte bir "wrangler" YAZMAK YERINE gercek bir SQLite (bellek ici) kullanilir —
# d1-sync'in urettigi SQL zaten SQLite lehcesidir, boylece test EDILEN sey aracin GERCEK
# ifadeleridir (metin eslemesi degil). Iki uc degistirilir:
#   sorgu()          -> sqlite SELECT/PRAGMA (wrangler bicimli sonuc dondurur)
#   dosya_calistir() -> sqlite executescript  ... VEYA `dusur` fikstruyle: ifadeleri
#                       UYGULAMADAN "5 satir yazildi" RAPORLAR = 31 Tem'in SESSIZ ARIZASI.
# Her yeni iddia icin POZITIF ve NEGATIF vaka AYRI AYRI kosar; yanlis-pozitif nobeti
# (degisiklik yok / normal parti) ayri iki vakadir — bu arac pre-push hook'unda kosuyor,
# yanlis-pozitif TUM mimarlarin push'unu kirar.
_KT_SEMA = """
CREATE TABLE urunler (
  rid INTEGER PRIMARY KEY,
  id TEXT NOT NULL UNIQUE,
  hash TEXT NOT NULL,
  seq NUMERIC NOT NULL,
  baslik TEXT NOT NULL DEFAULT '',
  kategori TEXT NOT NULL DEFAULT '',
  marka TEXT NOT NULL DEFAULT '[]',
  fiyat TEXT NOT NULL DEFAULT '',
  gorsel TEXT,
  parametrik INTEGER NOT NULL DEFAULT 0,
  hs TEXT NOT NULL DEFAULT '',
  aciklama TEXT NOT NULL DEFAULT '',
  ege TEXT NOT NULL DEFAULT '',
  hs_baslik TEXT NOT NULL DEFAULT '',
  hs_baslik_kok TEXT NOT NULL DEFAULT '',
  hs_govde TEXT NOT NULL DEFAULT '',
  hs_govde_kok TEXT NOT NULL DEFAULT '',
  baski TEXT NOT NULL DEFAULT '',
  taban_fiyat INTEGER NOT NULL DEFAULT 0,
  konfigur TEXT NOT NULL DEFAULT '',
  yayinda INTEGER NOT NULL DEFAULT 0,
  release_id TEXT NOT NULL DEFAULT '',
  tur TEXT NOT NULL DEFAULT '',
  stokta INTEGER NOT NULL DEFAULT -1,
  altkategori TEXT NOT NULL DEFAULT '',
  uyum TEXT NOT NULL DEFAULT '[]',
  marka_kanon TEXT NOT NULL DEFAULT '[]',
  model_kanon TEXT NOT NULL DEFAULT '[]',
  marka_arama TEXT NOT NULL DEFAULT '[]',
  tavsiye_filament TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE senkron (anahtar TEXT PRIMARY KEY, deger TEXT NOT NULL);
"""
# 🔴 IKIZ TANIM UYARISI: yukaridaki fikstur semasi tools/d1-sema.sql'in ELLE tutulan
# kopyasidir (offline sqlite icin; gercek dosyada FTS5 trigram sanal tablosu ve tetikleyiciler
# var, sqlite3 modulunde tokenize='trigram' her derlemede yok). Kopya ORIJINALDEN AYRISIRSA
# bu kabul testi YESIL yanarken canli D1 baska bir semayla kosar. Ayrisma
# tools/stok-d1-kapisi.py C EKSENI tarafindan olculur (urunler tablosunun kolon KUMESI
# d1-sema.sql + GOC_KOLON ile birebir olmali).


def _kt_urun(uid, kategori="Oyun/Hobi", baslik=None):
    return {"id": uid, "baslik": baslik or ("Urun %s" % uid), "kategori": kategori,
            "marka": [], "fiyat": "100 TL",
            "gorseller": ["https://media.example/%s-1.jpg" % uid],
            "aciklama": "aciklama %s" % uid}


def _kt_kos(conn, urunler, argv, dusur=None, oku_patlat=False, tabanlar=None,
            bayatlik="UC", kok=None, turetilmis=None, kilit=None):
    """d1-sync'i OFFLINE kosar. Doner: (cikis_kodu, cikti_metni, sayac).
    dusur(sql, sayac) -> True ise o yazma UYGULANMAZ ama BASARI raporlanir (sessiz ariza).
    oku_patlat -> geri-okuma sorgusu istisna atar (OLCULEMEDI yolu).
    bayatlik -> bayatlik_olc()'un dondurecegi durum ("UC"/"BAYAT"/"OLCULEMEDI"); AG YOK.
       sayac["bayatlik"] kac kez olculdugunu tutar (maliyet ekseni: yazma yoksa 0 olmali).
    kok -> verilirse GERCEK bayatlik_olc() o git agacinda kosar (stub YOK) ve KOK oraya
       ayarlanir; uctan uca (git soyagaci + senkron) olcum icin.
    kilit -> YAZICI KILIDI dosya yolu. VERILMEZSE her kosum icin AYRI bir gecici yol
       kullanilir: kabul testi GERCEK depo kilidine (.d1-sync.lock) DOKUNMAZ ve ardisik
       vakalar birbirini kilitlemez. VERILIRSE gercek bir yaris olculebilir
       (tools/d1-yazici-kilidi-test.py bu ucu kullanir).
    turetilmis -> TURETILMIS_KAYIT yerine gecen FIKSTUR defteri.
       🔴 NEDEN GEREKLI: gercek kayit defteri KATALOG OLCEGINDE calisir — 3 urunluk
       fiksturde `model_kanon` "kova evreni BOS" der ve `taban_fiyat` semasi bu harness'ta
       BILEREK yok edilmistir (JEN_URUN_DIR yok-dizin). Ikisi de DOGRU sekilde OLCULEMEDI
       yakar; yani fikstur verilmezse --durum senaryolari fiksturden dogan bir kirmiziyla
       kosardi. Defter fiksturlenince EKSEN MAKINESI (sqlite'tan GERCEK SELECT ile) uctan
       uca olculur; URETICI GOVDELERIN kendisi tools/d1-sync-durum-test.py'de gercek
       koduyla olculur."""
    import contextlib
    import io
    import sqlite3

    sayac = {"yazma": 0, "okuma": 0, "dusurulen": 0, "geri_okuma": 0, "bayatlik": 0}

    def _bayatlik():
        sayac["bayatlik"] += 1
        return {"durum": bayatlik, "sebep": "sentetik fikstur (%s)" % bayatlik,
                "head": "a" * 40, "uzak": "b" * 40}

    def _sorgu(sql):
        sayac["okuma"] += 1
        if "WHERE id IN (" in sql:
            sayac["geri_okuma"] += 1
            if oku_patlat:
                raise RuntimeError("sentetik geri-okuma arizasi (ag/wrangler)")
        satirlar = [dict(r) for r in conn.execute(sql).fetchall()]
        return [{"results": satirlar,
                 "meta": {"rows_read": len(satirlar), "rows_written": 0}}]

    def _dosya_calistir(sql_metin):
        # IFADE IFADE uygulanir (d1-sync ifadeleri '\n' ile birlestirir) -> fikstur TEK BIR
        # URUNUN yazmasini dusurebilir. Bu, "geri-okuma orneklem aliyor mu" iddiasini
        # olculebilir kilar (bkz. V34): 30 urunluk partide yalniz 1'i kaybolur.
        sayac["yazma"] += 1
        yaz = 0
        for satir in [x for x in sql_metin.split("\n") if x.strip()]:
            if dusur and dusur(satir, sayac):
                sayac["dusurulen"] += 1
                yaz += 5           # SAHTE BASARI: yazmadi ama "5 satir yazdim" dedi
                continue
            once = conn.total_changes
            conn.executescript(satir)
            yaz += conn.total_changes - once
        return yaz, 0

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(urunler, f)
        yol = f.name
    # YAZICI KILIDI: verilmediyse VAKAYA OZEL gecici yol -> gercek `.d1-sync.lock`
    # dosyasina DOKUNULMAZ ve ardisik vakalar birbirini kilitlemez. `kilit` verilirse
    # GERCEK yaris olculebilir (iki surec ayni yolu paylasir).
    kilit_gecici = None
    if kilit is None:
        kilit_gecici = tempfile.mkdtemp(prefix="pruvo-kt-kilit-")
        kilit = os.path.join(kilit_gecici, "d1-sync.lock")

    g = globals()
    eski = {k: g[k] for k in ("sorgu", "dosya_calistir", "URUNLER", "KAYNAKLAR",
                              "JEN_URUN_DIR", "taban_fiyat_haritasi", "bayatlik_olc",
                              "KOK", "TURETILMIS_KAYIT", "KILIT")}
    eski_argv = sys.argv
    tampon = io.StringIO()
    try:
        g["sorgu"] = _sorgu
        g["dosya_calistir"] = _dosya_calistir
        g["KILIT"] = kilit
        if kok is None:
            g["bayatlik_olc"] = _bayatlik  # AG YOK: kapi kararini fikstur verir
        else:
            g["KOK"] = kok                 # GERCEK kapi, GERCEK git (sentetik depo)
        g["URUNLER"] = yol
        g["KAYNAKLAR"] = os.path.join(tempfile.gettempdir(), "pruvo-kt-yok.json")
        g["JEN_URUN_DIR"] = os.path.join(tempfile.gettempdir(), "pruvo-kt-yok-dizin")
        if tabanlar is not None:
            g["taban_fiyat_haritasi"] = lambda: dict(tabanlar)
        if turetilmis is not None:
            g["TURETILMIS_KAYIT"] = turetilmis
        sys.argv = ["d1-sync.py"] + argv
        kod = 0
        with contextlib.redirect_stdout(tampon):
            try:
                main()
            except SystemExit as e:
                c = e.code
                if c is None or c == 0:
                    kod = 0
                elif isinstance(c, int):
                    kod = c
                else:
                    kod = 1
                    print(c)      # sys.exit(mesaj) -> mesaj ciktiya girsin (stderr yerine)
    finally:
        # 🔴 KILIDI ELLE BIRAK: main() bu harness'ta AYNI SURECTE kosuyor, atexit HENUZ
        # atesleymez. Birakilmazsa bir sonraki vaka kendi kilidine takilirdi (flock ayni
        # surecte, AYRI open() ile de CAKISIR) — kabul testi kendi kendini bloklardi.
        yazici_kilidi_birak()
        for k, v in eski.items():
            g[k] = v
        sys.argv = eski_argv
        os.unlink(yol)
        if kilit_gecici:
            import shutil
            shutil.rmtree(kilit_gecici, ignore_errors=True)
    return kod, tampon.getvalue(), sayac


def _kt_turetilmis(hedefler=None, sebep=None):
    """TURETILMIS_KAYIT fiksturu — GERCEK kolon adlarini ve GERCEK plan govdelerini KORUR,
    yalnizca HEDEF URETICISINI fiksturler.
    hedefler = {kolon: {id: istenen deger}} · sebep = doluysa her kolon URETILEMEDI doner.
    🔴 Kolon adlari korunur: yoksa kapsam_acigi() fikstur yuzunden yanlis-pozitif yakardi
    (canli tabloda olup defterde olmayan kolonlar 'siniflandirilmamis' gorunurdu)."""
    hedefler = hedefler or {}

    def _uret(kolon):
        def _f(_urunler):
            if sebep:
                return None, sebep
            return dict(hedefler.get(kolon) or {}), None
        return _f

    return [dict(k, hedef=_uret(k["kolon"]), coz="fikstur") for k in TURETILMIS_KAYIT]


def _kt_baglan(yayinda_default=0):
    """yayinda_default: TABLO SEMASINDAKI varsayilan. 1 vermek SEMA DRIFT'ini taklit eder
    (biri DEFAULT'u degistirdi / tablo baska yoldan kuruldu). Yeni satirin taslak dogmasi
    SEMANIN DEFAULT'una DEGIL, INSERT'in acikca yazdigi degere bagli olmali."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_KT_SEMA.replace("yayinda INTEGER NOT NULL DEFAULT 0",
                                        "yayinda INTEGER NOT NULL DEFAULT %d" % yayinda_default))
    # ATOMIK YAYIN indeksleri fiksture de kurulur: canli D1'de 31 Tem'den beri VARLAR
    # (kolon_goc her --sema'da idempotent kurar). Fikstur onlarsiz dogsaydi SEMA EKSENI
    # her vakada "INDEKS-YOK" derdi = fiksturden dogan YANLIS POZITIF, olculen eksen
    # (siparis gocu) da o gurultunun altinda kalirdi.
    conn.executescript("\n".join(YAYIN_INDEKS))
    return conn


def _kt_deger(conn, uid, kolon):
    r = conn.execute("SELECT %s AS v FROM urunler WHERE id=?" % kolon, (uid,)).fetchone()
    return None if r is None else r["v"]


def _kt_git(yol, *args):
    """Sentetik depoda git kos (kimlik + imza ayarlari sabit; kullanicinin ayarina bagli
    KALMAZ -> CI'da da yerelde de ayni davranir)."""
    p = sentetik_git(yol, *args, kimlik_ad="KT", kimlik_eposta="kt@pruvo.test",
                      ayarlar=("-c", "commit.gpgsign=false", "-c",
                                "protocol.file.allow=always"),
                      capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip()


def _kt_depo_kur(tmp, urun_sayisi=1):
    """(uzak_bare, yerel) — main dali olan bir uzak + ona bagli bir yerel checkout."""
    uzak = os.path.join(tmp, "uzak.git")
    yerel = os.path.join(tmp, "yerel")
    os.makedirs(uzak)
    _kt_git(tmp, "init", "--bare", "--quiet", uzak)
    # 🔴 HERMETIKLIK: `init --bare`in HEAD'i kosucunun `init.defaultBranch` ayarina gore
    # dogar (yerelde `main`, GitHub kosucusunda BASKA olabilir). O zaman bu bare depodan
    # `clone` yapan fikstur DOGMAMIS bir dala dusuyor ve agac "commit'siz depo" gorunuyor
    # -> V46 (sig klon) yerelde BAYAT, CI'da OLCULEMEDI veriyordu (31 Tem, yayin durdu).
    # HEAD'i ACIKCA main'e capala: fikstur artik kosucunun ayarindan BAGIMSIZ.
    _kt_git(uzak, "symbolic-ref", "HEAD", "refs/heads/main")
    os.makedirs(yerel)
    _kt_git(yerel, "init", "--quiet")
    _kt_git(yerel, "checkout", "--quiet", "-B", "main")
    _kt_git(yerel, "remote", "add", "origin", uzak)
    with open(os.path.join(yerel, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([_kt_urun("u%02d" % i) for i in range(urun_sayisi)], f)
    _kt_git(yerel, "add", "-A")
    _kt_git(yerel, "commit", "--quiet", "-m", "taban")
    _kt_git(yerel, "push", "--quiet", "origin", "main")
    return uzak, yerel


# ── GOC INDEKSI FIKSTURU (sema ekseni) ────────────────────────────────────────────
# Gercek `siparisler` tablosunun BU TEST icin gereken en kucuk hali. kanal/dis_no kolonlari
# BILEREK burada YOK: goc penceresinin iki yakasi (kolon yok / kolon var) ayri ayri
# olculebilsin diye ALTER ile eklenir — canli gocun izledigi sirayla.
_KT_SIPARIS_SEMA = """
CREATE TABLE siparisler (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  siparis_no TEXT NOT NULL UNIQUE,
  tarih TEXT NOT NULL,
  durum TEXT NOT NULL DEFAULT 'bekliyor',
  tutar_kurus INTEGER NOT NULL,
  urunler TEXT NOT NULL
);
"""
_KT_SIPARIS_ALTER = [
    "ALTER TABLE siparisler ADD COLUMN kanal TEXT NOT NULL DEFAULT 'site';",
    "ALTER TABLE siparisler ADD COLUMN dis_no TEXT NOT NULL DEFAULT '';",
]


def _kt_goc_conn(kanal_kolonu=True, yarim=False, ikiz=0, indeks=False):
    """Goc fiksturu. kanal_kolonu: iki kolon da eklenmis mi · yarim: YALNIZ kanal eklendi
    (ALTER'lar yarida kaldi) · ikiz: ayni (kanal,dis_no) ile kac FAZLA satir · indeks:
    kismi UNIQUE indeks ONCEDEN kurulu mu."""
    conn = _kt_baglan()
    conn.executescript(_KT_SIPARIS_SEMA)
    if yarim:
        conn.executescript(_KT_SIPARIS_ALTER[0])
    elif kanal_kolonu:
        conn.executescript("\n".join(_KT_SIPARIS_ALTER))
    for i in range(1 + ikiz):
        if kanal_kolonu and not yarim:
            conn.execute("INSERT INTO siparisler (siparis_no,tarih,tutar_kurus,urunler,"
                         "kanal,dis_no) VALUES (?,?,?,?,?,?)",
                         ("PR-%03d" % i, "2026-07-25T10:00:00Z", 1000, "[]",
                          "whatsapp", "WA-1"))
        else:
            conn.execute("INSERT INTO siparisler (siparis_no,tarih,tutar_kurus,urunler)"
                         " VALUES (?,?,?,?)",
                         ("PR-%03d" % i, "2026-07-25T10:00:00Z", 1000, "[]"))
    if indeks:
        conn.executescript(GOC_INDEKS[-1]["sql"])
    conn.commit()
    return conn


def _kt_goc_kos(conn, fn):
    """sorgu/dosya_calistir uclarini sqlite'a baglayip fn'i kos. (kod, cikti, sonuc).
    dosya_calistir URETIMDEKI gibi davranir: SQL duserse wrangler rc!=0 -> SystemExit."""
    import contextlib
    import io
    import sqlite3

    def _sorgu(sql):
        satirlar = [dict(r) for r in conn.execute(sql).fetchall()]
        return [{"results": satirlar, "meta": {"rows_read": len(satirlar),
                                               "rows_written": 0}}]

    def _dosya_calistir(sql_metin):
        yaz = 0
        for satir in [x for x in sql_metin.split("\n") if x.strip()]:
            once = conn.total_changes
            try:
                conn.executescript(satir)
            except sqlite3.Error as e:
                sys.exit("wrangler SIFIR-DISI cikti (rc=1): %s" % e)
            yaz += conn.total_changes - once
        return yaz, 0

    g = globals()
    eski = {k: g[k] for k in ("sorgu", "dosya_calistir", "KILIT")}
    tampon = io.StringIO()
    kod, sonuc = 0, None
    # `fn` GERCEK main()'in --sema kolu olabilir -> yazici kilidini alir. Kilit VAKAYA
    # OZEL gecici yola bakar: gercek `.d1-sync.lock` dosyasina DOKUNULMAZ ve ardisik
    # vakalar birbirini bloklamaz (flock ayni surecte, AYRI open() ile de cakisir).
    kilit_gecici = tempfile.mkdtemp(prefix="pruvo-kt-goc-kilit-")
    try:
        g["sorgu"], g["dosya_calistir"] = _sorgu, _dosya_calistir
        g["KILIT"] = os.path.join(kilit_gecici, "d1-sync.lock")
        with contextlib.redirect_stdout(tampon):
            try:
                sonuc = fn()
            except SystemExit as e:
                c = e.code
                kod = 0 if c in (None, 0) else (c if isinstance(c, int) else 1)
                if not isinstance(c, int) and c is not None:
                    print(c)
    finally:
        yazici_kilidi_birak()
        for k, v in eski.items():
            g[k] = v
        import shutil
        shutil.rmtree(kilit_gecici, ignore_errors=True)
    return kod, tampon.getvalue(), sonuc


def _kt_sema_kos(conn):
    """GERCEK `--sema` yolunu (main) kos. SEMA dosyasi zararsiz bir DDL'e capalanir:
    olculen sey KOLON GOCU + INDEKS TEYIDI (fikstur sqlite'inda FTS5 sanal tablosu yok)."""
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False,
                                     encoding="utf-8") as f:
        f.write("CREATE TABLE IF NOT EXISTS senkron "
                "(anahtar TEXT PRIMARY KEY, deger TEXT NOT NULL);\n")
        yol = f.name
    g = globals()
    eski_sema, eski_argv = g["SEMA"], sys.argv
    try:
        g["SEMA"] = yol
        sys.argv = ["d1-sync.py", "--sema"]
        return _kt_goc_kos(conn, main)
    finally:
        g["SEMA"], sys.argv = eski_sema, eski_argv
        os.unlink(yol)


def _kt_durum_kos(conn):
    """`--durum --hizli`i OFFLINE kos (sayi ekseni TUTAR; olculen sey SEMA EKSENI)."""
    conn.execute("INSERT INTO urunler (id,hash,seq) VALUES ('u1','h',1)")
    conn.execute("INSERT INTO senkron (anahtar,deger) VALUES ('urun_sayisi','1')")
    conn.commit()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump([_kt_urun("u1")], f)
        yol = f.name
    g = globals()
    eski_u, eski_argv = g["URUNLER"], sys.argv
    try:
        g["URUNLER"] = yol
        sys.argv = ["d1-sync.py", "--durum", "--hizli"]
        return _kt_goc_kos(conn, main)
    finally:
        g["URUNLER"], sys.argv = eski_u, eski_argv
        os.unlink(yol)


def _kt_indeks_adlari(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")}


def _kt_siparis_sayisi(conn):
    return conn.execute("SELECT COUNT(*) FROM siparisler").fetchone()[0]


def _kt_bayatlik(yol):
    """bayatlik_olc()'u GERCEK git ile, verilen agacta kostur (AG YOK: uzak = yerel dizin)."""
    g = globals()
    eski = g["KOK"]
    try:
        g["KOK"] = yol
        return bayatlik_olc()
    finally:
        g["KOK"] = eski


def kendini_test():
    """Doner: 0 (tum vakalar gecti) / 1 (en az bir vaka kaldi)."""
    gecen, kalan = [0], [0]

    def dogrula(ad, kosul, detay=""):
        if kosul:
            gecen[0] += 1
            print("  GECTI  " + ad)
        else:
            kalan[0] += 1
            print("  KALDI  " + ad + ((" — " + str(detay)[:400]) if detay else ""))

    print("d1-sync KENDINI TEST (offline sqlite fikstur; canli D1'e DOKUNULMAZ)")

    # ── SAF BIRIM: karsilastirma cekirdegi ────────────────────────────────────────
    b = {"x": {"alanlar": {"hash": "H1", "kategori": "Tamirat"}, "sql": []}}
    dogrula("V1 SAF: alanlar birebir -> fark YOK",
            beklenti_karsilastir(b, {"x": {"hash": "H1", "kategori": "Tamirat"}}) == [])
    f = beklenti_karsilastir(b, {"x": {"hash": "H0", "kategori": "Oyun/Hobi"}})
    dogrula("V2 SAF: iki alan bayat -> 2 fark (kolon adlariyla)",
            [x[1] for x in f] == ["hash", "kategori"], f)
    dogrula("V3 SAF: satir HIC YOK -> '<satir>' farki",
            beklenti_karsilastir(b, {}) == [("x", "<satir>", "VAR", "SATIR YOK")])
    bs = {"x": {"alanlar": None, "sql": []}}
    dogrula("V4 SAF: silinmesi gereken satir HALA VAR -> fark",
            beklenti_karsilastir(bs, {"x": {"hash": "H"}}) ==
            [("x", "<satir>", "SILINMIS", "HALA VAR")])
    dogrula("V5 SAF: silinen satir gercekten yok -> fark YOK",
            beklenti_karsilastir(bs, {}) == [])
    bt = {"x": {"alanlar": {"taban_fiyat": 700}, "sql": []}}
    dogrula("V6 SAF (YANLIS-POZITIF NOBETI): taban_fiyat '700' (metin) == 700 (int)",
            beklenti_karsilastir(bt, {"x": {"taban_fiyat": "700"}}) == [])

    # ── SAF BIRIM: izleme kaydi (beklenti SQL'in URETILDIGI yerde dogar) ──────────
    iz = []
    u = _kt_urun("a", "Tamirat")
    diff_plan([u], {}, {"a": "PLA 0.2mm"}, True, 0, {}, iz)
    dogrula("V7 IZ: yeni urun -> hash+baslik+kategori+baski+tur+stokta beklentisi kaydedilir",
            len(iz) == 1
            and set(iz[0]["alanlar"]) == {"hash", "baslik", "kategori", "baski",
                                          "tur", "stokta"}
            and iz[0]["alanlar"]["kategori"] == "Tamirat", iz)
    # TICARI HAL geri-okumasi: `stokta` alani OLMAYAN urun -1 (BILINMIYOR) beklentisi
    # uretmeli — 0 (STOKTA DEGIL) DEGIL. Ikisi karisirsa katalogun tamami "tukendi" olur.
    dogrula("V7b IZ: `stokta` alani YOK -> beklenti -1 (BILINMIYOR), tur '' (ozel uretim)",
            iz[0]["alanlar"]["stokta"] == -1 and iz[0]["alanlar"]["tur"] == "", iz)
    iz2 = []
    diff_plan([u], {"a": ("ESKIHASH", "")}, {}, False, 1, {"a": 1}, iz2)
    dogrula("V8 IZ: DEGISEN satirda baski beklentiye GIRMEZ (ON CONFLICT baski'ya dokunmaz)",
            len(iz2) == 1 and "baski" not in iz2[0]["alanlar"], iz2)
    iz3 = []
    taban_plan([u], {"a": 700}, {}, iz3)
    sema_plan("konfigur", [u], {"a": '{"x":1}'}, {}, iz3)
    dogrula("V9 IZ: taban_plan + sema_plan hedefli UPDATE'leri de kaydeder",
            [sorted(k["alanlar"]) for k in iz3] == [["taban_fiyat"], ["konfigur"]], iz3)

    # ── DAVRANIS: POZITIF yol ─────────────────────────────────────────────────────
    conn = _kt_baglan()
    urunler = [_kt_urun("a"), _kt_urun("b"), _kt_urun("c")]
    kod, cikti, sayac = _kt_kos(conn, urunler, [])
    dogrula("V10 POZITIF: 3 yeni urun yazildi -> exit 0 + GERI-OKUMA DOGRULANDI",
            kod == 0 and "GERI-OKUMA DOGRULANDI" in cikti, cikti[-300:])
    dogrula("V11 POZITIF: geri-okuma FIILEN kosuldu (sorgu sayisi > 0)",
            sayac["geri_okuma"] >= 1, sayac)

    # YANLIS-POZITIF NOBETI 1/2 — degisiklik yok
    kod, cikti, sayac = _kt_kos(conn, urunler, [])
    dogrula("V12 YANLIS-POZITIF NOBETI: degisiklik yok -> exit 0, HIC yazma, HIC geri-okuma",
            kod == 0 and sayac["yazma"] == 0 and sayac["geri_okuma"] == 0
            and "degisiklik yok" in cikti, (kod, sayac))

    # YANLIS-POZITIF NOBETI 2/2 — normal parti (30 yeni + 1 alan degisimi)
    parti = [_kt_urun("p%02d" % i) for i in range(30)] + urunler
    parti[-3] = _kt_urun("a", "Tamirat")
    kod, cikti, sayac = _kt_kos(conn, parti, [])
    dogrula("V13 YANLIS-POZITIF NOBETI: normal parti (30 yeni + 1 alan degisimi) -> exit 0",
            kod == 0 and "GERI-OKUMA DOGRULANDI" in cikti, cikti[-300:])
    dogrula("V14 POZITIF: alan degisimi D1'e FIILEN islendi (kategori=Tamirat)",
            _kt_deger(conn, "a", "kategori") == "Tamirat", _kt_deger(conn, "a", "kategori"))

    # ── DAVRANIS: NEGATIF yol — sahte "yazildi" ───────────────────────────────────
    conn2 = _kt_baglan()
    dus_hep = lambda sql, s: "INSERT INTO urunler" in sql or "UPDATE urunler" in sql
    kod, cikti, sayac = _kt_kos(conn2, urunler, [], dusur=dus_hep)
    dogrula("V15 NEGATIF: yazma SESSIZCE dustu ama 'yazildi' denildi -> sifir-disi",
            kod != 0 and "DOGRULANAMADI" in cikti, (kod, cikti[-300:]))
    dogrula("V16 NEGATIF: mesaj SATIR YOK'u id ile gosteriyor",
            "SATIR YOK" in cikti and " a . <satir>" in cikti.replace("- a .", " a ."),
            cikti[-500:])

    # 🔴 31 TEM VAKASININ BIREBIR FIKSTURU: satir VAR, ALAN eski kaldi.
    conn3 = _kt_baglan()
    kod, _, _ = _kt_kos(conn3, urunler, [])                       # once saglikli senkron
    bozuk = [_kt_urun("a", "Tamirat"), urunler[1], urunler[2]]    # kategori degisti
    kod, cikti, sayac = _kt_kos(conn3, bozuk, [], dusur=dus_hep)
    dogrula("V17 NEGATIF (31 TEM FIKSTURU): satir VAR + alan ESKI -> sifir-disi",
            kod != 0 and "DOGRULANAMADI" in cikti, (kod, cikti[-400:]))
    dogrula("V18 NEGATIF (31 TEM FIKSTURU): mesajda kolon + beklenen/bulunan var",
            "kategori" in cikti and "'Tamirat'" in cikti and "'Oyun/Hobi'" in cikti,
            cikti[-400:])
    dogrula("V19 NEGATIF: satir VARLIGI korunuyor (varlik kontrolu TEK BASINA yakalamazdi)",
            _kt_deger(conn3, "a", "kategori") == "Oyun/Hobi",
            _kt_deger(conn3, "a", "kategori"))

    # ── YENIDEN DENEME (aralikli ariza) ───────────────────────────────────────────
    conn4 = _kt_baglan()

    def dus_ilk(sql, s):
        return s["yazma"] == 1 and "INSERT INTO urunler" in sql

    kod, cikti, sayac = _kt_kos(conn4, urunler, [], dusur=dus_ilk)
    dogrula("V20 RETRY POZITIF: 1. yazma kacti, 2. deneme tuttu -> exit 0",
            kod == 0 and "2. turda" in cikti, (kod, cikti[-400:]))
    dogrula("V21 RETRY POZITIF: yeniden deneme ciktida BASILIYOR (sessiz degil)",
            "yeniden deneme:" in cikti, cikti[-400:])
    dogrula("V22 RETRY POZITIF: satirlar gercekten D1'e girdi",
            _kt_deger(conn4, "a", "hash") is not None)

    conn5 = _kt_baglan()
    kod, cikti, sayac = _kt_kos(conn5, urunler, [], dusur=dus_hep)
    dogrula("V23 RETRY TUKENIR: iki deneme de kacti -> sifir-disi, SONSUZ DONGU YOK",
            kod != 0 and sayac["yazma"] <= 4, (kod, sayac))

    # ── SILME ekseni ──────────────────────────────────────────────────────────────
    conn6 = _kt_baglan()
    _kt_kos(conn6, urunler, [])
    kod, cikti, _ = _kt_kos(conn6, urunler[:2], [])
    dogrula("V24 SILME POZITIF: silinen satir gercekten gitti -> exit 0",
            kod == 0 and _kt_deger(conn6, "c", "hash") is None, (kod, cikti[-300:]))
    conn7 = _kt_baglan()
    _kt_kos(conn7, urunler, [])
    kod, cikti, _ = _kt_kos(conn7, urunler[:2], [],
                            dusur=lambda sql, s: "DELETE FROM urunler" in sql)
    dogrula("V25 SILME NEGATIF: DELETE kacti (satir duruyor) -> sifir-disi + 'HALA VAR'",
            kod != 0 and "HALA VAR" in cikti, (kod, cikti[-400:]))

    # ── HASH'E KARISMAYAN KOLON (taban_fiyat) ─────────────────────────────────────
    conn8 = _kt_baglan()
    _kt_kos(conn8, urunler, [])
    kod, cikti, _ = _kt_kos(conn8, urunler, [], tabanlar={"a": 700})
    dogrula("V26 TABAN POZITIF: hedefli taban_fiyat UPDATE'i yazildi + dogrulandi",
            kod == 0 and _kt_deger(conn8, "a", "taban_fiyat") == 700,
            (kod, _kt_deger(conn8, "a", "taban_fiyat")))
    conn9 = _kt_baglan()
    _kt_kos(conn9, urunler, [])
    kod, cikti, _ = _kt_kos(conn9, urunler, [], tabanlar={"a": 700},
                            dusur=lambda sql, s: "SET taban_fiyat" in sql)
    dogrula("V27 TABAN NEGATIF: taban_fiyat yazmasi kacti -> sifir-disi + kolon adi mesajda",
            kod != 0 and "taban_fiyat" in cikti, (kod, cikti[-400:]))

    # ── --kuru: yazma da geri-okuma da YOK ────────────────────────────────────────
    conn10 = _kt_baglan()
    _kt_kos(conn10, urunler, [])
    kod, cikti, sayac = _kt_kos(conn10, bozuk, ["--kuru"])
    dogrula("V28 KURU: exit 0 + HIC yazma + HIC geri-okuma",
            kod == 0 and sayac["yazma"] == 0 and sayac["geri_okuma"] == 0
            and "geri-okuma da yapilmadi" in cikti, (kod, sayac))
    dogrula("V29 KURU: D1 degeri DEGISMEDI (kuru kosum yazmaz)",
            _kt_deger(conn10, "a", "kategori") == "Oyun/Hobi")

    # ── GERI-OKUMA SORGUSU PATLARSA -> OLCULEMEDI (yesil DEGIL) ───────────────────
    conn11 = _kt_baglan()
    kod, cikti, _ = _kt_kos(conn11, urunler, [], oku_patlat=True)
    dogrula("V30 OLCULEMEDI: geri-okuma sorgusu patladi -> sifir-disi + 'OLCULEMEDI'",
            kod != 0 and "OLCULEMEDI" in cikti, (kod, cikti[-400:]))

    # ── --durum ICERIK EKSENI ─────────────────────────────────────────────────────
    conn12 = _kt_baglan()
    _kt_kos(conn12, urunler, [])
    tk = _kt_turetilmis()
    kod, cikti, _ = _kt_kos(conn12, urunler, ["--durum"], turetilmis=tk)
    dogrula("V31 DURUM POZITIF: sayi + icerik ekseni uyumlu -> exit 0",
            kod == 0 and "teyit (ICERIK ekseni)" in cikti, (kod, cikti[-400:]))
    dogrula("V31b DURUM TURETILMIS POZITIF: hash-disi kolonlar guncel -> teyit satiri + exit 0",
            kod == 0 and "teyit (TURETILMIS KOLON ekseni)" in cikti, (kod, cikti[-400:]))
    # 🔴 6 AGU SINIFI: SAYI tutuyor, HASH tutuyor, kolon BAYAT. Uc eksen de yesil yanardi.
    kod2, cikti2, _ = _kt_kos(conn12, urunler, ["--durum"],
                              turetilmis=_kt_turetilmis({"marka_arama": {"a": '["Honda"]'}}))
    dogrula("V31c DURUM TURETILMIS NEGATIF (6 AGU SINIFI): sayi + hash TUTUYOR ama "
            "marka_arama BAYAT -> sifir-disi + kolon adi + 'olmasi gereken'",
            kod2 != 0 and "BAYAT TURETILMIS KOLON (marka_arama)" in cikti2
            and "teyit (SAYI ekseni)" in cikti2 and "teyit (ICERIK ekseni)" in cikti2
            and "olmasi gereken" in cikti2, (kod2, cikti2[-600:]))
    kod3, cikti3, _ = _kt_kos(conn12, urunler, ["--durum"],
                              turetilmis=_kt_turetilmis(sebep="tek kaynak okunamadi"))
    dogrula("V31d DURUM TURETILMIS FAIL-CLOSED: uretici govde uretemedi -> OLCULEMEDI + "
            "sifir-disi (bilinmezlik YESIL sayilmaz)",
            kod3 != 0 and "OLCULEMEDI (marka_arama)" in cikti3, (kod3, cikti3[-500:]))
    conn12.execute("UPDATE urunler SET hash='BAYATHASH' WHERE id='a'")
    kod, cikti, _ = _kt_kos(conn12, urunler, ["--durum"], turetilmis=tk)
    dogrula("V32 DURUM NEGATIF (31 TEM SINIFI): SAYI TUTUYOR ama hash bayat -> sifir-disi",
            kod != 0 and "ICERIK EKSENI DRIFT" in cikti and "teyit (SAYI ekseni)" in cikti,
            (kod, cikti[-500:]))
    dogrula("V32b KORELME: turetilmis eksen eklendikten SONRA da 31 Tem vakasi ICERIK "
            "ekseninden yakalanir (turetilmis kolonlar GUNCEL iken)",
            kod != 0 and "teyit (TURETILMIS KOLON ekseni)" in cikti, (kod, cikti[-500:]))
    kod, cikti, _ = _kt_kos(conn12, urunler, ["--durum", "--hizli"], turetilmis=tk)
    dogrula("V33 DURUM --hizli: icerik ekseni BEYAN EDILEREK atlanir -> exit 0 + uyari",
            kod == 0 and "ICERIK EKSENI ATLANDI" in cikti, (kod, cikti[-400:]))
    dogrula("V33b DURUM --hizli: turetilmis eksen de BEYAN EDILEREK atlanir (sessiz DEGIL)",
            kod == 0 and "TURETILMIS KOLON EKSENI ATLANDI" in cikti, (kod, cikti[-400:]))

    # ── ORNEKLEME YASAGI: 30 urunluk partide YALNIZ 1 urunun yazmasi kaybolur ────
    # Geri-okuma yazilan id kumesinin TAMAMINI dogrulamazsa (ornekleme/kisaltma) bu vaka
    # YESIL yanar ve tek urun sessizce bayat kalir.
    conn13 = _kt_baglan()
    buyuk = [_kt_urun("p%02d" % i) for i in range(30)]
    kod, cikti, sayac = _kt_kos(conn13, buyuk, [],
                                dusur=lambda sql, s: "'p07'" in sql)
    dogrula("V34 ORNEKLEME YASAGI: 30 urunun 1'i (p07) kacti -> sifir-disi + id mesajda",
            kod != 0 and "p07" in cikti, (kod, cikti[-400:]))
    dogrula("V35 ORNEKLEME YASAGI: diger 29 urun gercekten yazildi (yanlis-pozitif degil)",
            _kt_deger(conn13, "p08", "hash") is not None
            and _kt_deger(conn13, "p07", "hash") is None)

    # ── ATOMIK YAYIN: TASLAK/YAYINDA sozlesmesi (31 Tem) ─────────────────────────
    # IDDIA 1 (pozitif eksen): senkronun YAZDIGI yeni satir TASLAK dogar. Bozulursa
    #   (satir_sql'e yayinda=1 konursa / kolon INSERT'ten dusurulup DEFAULT degistirilirse)
    #   urun sayfasi canlida YOKKEN Ege'ye gorunur = olculen 404 penceresi geri gelir.
    # IDDIA 2 (negatif eksen): ZATEN YAYINDA olan bir urunun ICERIGI degisince satir
    #   yeniden yazilir ama yayinda 1 KALIR. Bozulursa (KOLONLAR'a yayinda eklenirse)
    #   her toplu duzeltme TUM katalogu deploy suresince Ege'den gizler.
    conn14 = _kt_baglan()
    _kt_kos(conn14, urunler, [])
    dogrula("V36 YAYIN POZITIF: yeni satir TASLAK dogar (yayinda=0)",
            _kt_deger(conn14, "a", "yayinda") == 0,
            _kt_deger(conn14, "a", "yayinda"))
    conn14.execute("UPDATE urunler SET yayinda=1, release_id='r1'")
    urunler_degisik = [dict(u) for u in urunler]
    urunler_degisik[0] = dict(urunler_degisik[0], baslik="Yeni Baslik", kategori="Tamirat")
    kod, cikti, _ = _kt_kos(conn14, urunler_degisik, [])
    dogrula("V37 YAYIN NEGATIF: icerik degisti, satir yeniden yazildi -> yayinda 1 KALDI",
            kod == 0 and _kt_deger(conn14, "a", "kategori") == "Tamirat"
            and _kt_deger(conn14, "a", "yayinda") == 1,
            (kod, _kt_deger(conn14, "a", "yayinda"), _kt_deger(conn14, "a", "kategori")))
    dogrula("V38 YAYIN: yayina alan release_id icerik upsert'inde SILINMEDI",
            _kt_deger(conn14, "a", "release_id") == "r1",
            _kt_deger(conn14, "a", "release_id"))
    # Yeni urun MEVCUT yayindaki katalogun yanina eklenince: eskiler yayinda kalir,
    # YENI olan taslak olur (karisik parti — gercek push deseni).
    kod, _, _ = _kt_kos(conn14, [_kt_urun("zz")] + urunler_degisik, [])
    dogrula("V39 YAYIN KARISIK PARTI: yeni=taslak, eskiler yayinda (tek partide ikisi)",
            kod == 0 and _kt_deger(conn14, "zz", "yayinda") == 0
            and _kt_deger(conn14, "a", "yayinda") == 1,
            (kod, _kt_deger(conn14, "zz", "yayinda"), _kt_deger(conn14, "a", "yayinda")))

    # V40/V41 — "DEFAULT'a GUVENME" iddiasi. Olculdu (fault injection, 31 Tem): `yayinda`
    # kolonu INSERT listesinden dusurulup DEFAULT'a birakilinca V36-V39'un DORDU DE YESIL
    # kaliyordu (SAG KALAN MUTANT). Yani "taslak dogar" iddiasi semanin DEFAULT'una
    # bagliydi; DEFAULT bir gun 1 olsaydi her yeni urun SESSIZCE yayinda dogar ve olculen
    # 404 penceresi geri gelirdi. Bu iki vaka o mutanti oldurur.
    conn15 = _kt_baglan(yayinda_default=1)
    _kt_kos(conn15, urunler, [])
    dogrula("V40 DEFAULT DRIFT: sema DEFAULT'u 1 olsa BILE yeni satir TASLAK dogar",
            _kt_deger(conn15, "a", "yayinda") == 0, _kt_deger(conn15, "a", "yayinda"))
    _sql = satir_sql(_kt_urun("q1"), 1, "hs", "h")
    dogrula("V41 SQL SOZLESMESI: INSERT kolon listesi `yayinda`yi ACIKCA tasir ve 0 verir",
            ",yayinda) VALUES (" in _sql and _sql.split("VALUES (")[1].split(")")[0]
            .rstrip().endswith(",0"), _sql[:160])

    # ══════════════════════════════════════════════════════════════════════════
    # BAYATLIK KAPISI (31 Tem — 9 olay / 367 id sessizce silindi, 9'unda CI success)
    # ══════════════════════════════════════════════════════════════════════════
    # A) KARAR CEKIRDEGI — GERCEK git ile, AG YOK (uzak = yerel bare dizin).
    import shutil
    tmp = tempfile.mkdtemp(prefix="pruvo-bayatlik-")
    try:
        uzak, yerel = _kt_depo_kur(tmp)
        b = _kt_bayatlik(yerel)
        dogrula("V42 BAYATLIK: HEAD == uzak main ucu -> UC (silme SERBEST)",
                b["durum"] == "UC", b)

        # PRE-PUSH HALI: yerelde yeni commit var, uzak HENUZ eski uctadir. Kapi bunu
        # BAYAT sayarsa TUM MESRU PUSH'lar kirilir (paylasimli hook = herkesin push'u).
        with open(os.path.join(yerel, "urunler.json"), "w", encoding="utf-8") as f:
            json.dump([_kt_urun("u00"), _kt_urun("yeni1")], f)
        _kt_git(yerel, "add", "-A")
        _kt_git(yerel, "commit", "--quiet", "-m", "parti")
        b = _kt_bayatlik(yerel)
        dogrula("V43 BAYATLIK (PRE-PUSH): yerel UCTAN ILERIDE -> UC (mesru push kirilmaz)",
                b["durum"] == "UC", b)
        _kt_git(yerel, "push", "--quiet", "origin", "main")

        # 🔴 BUGUNKU OLAYIN GIT EKSENI: CI eski SHA'yi checkout etti, uc ilerledi.
        eski_sha = _kt_git(yerel, "rev-parse", "HEAD~1")[1]
        ci = os.path.join(tmp, "ci")
        _kt_git(tmp, "clone", "--quiet", uzak, ci)
        _kt_git(ci, "checkout", "--quiet", eski_sha)     # bayat checkout (detached)
        b = _kt_bayatlik(ci)
        dogrula("V44 BAYATLIK (BUGUNKU OLAY): eski SHA checkout + uc ilerledi -> BAYAT",
                b["durum"] == "BAYAT", b)

        # AYRIK (diverged) agac: uctan turemeyen kendi commit'i olan bayat worktree.
        ayrik = os.path.join(tmp, "ayrik")
        _kt_git(tmp, "clone", "--quiet", uzak, ayrik)
        _kt_git(ayrik, "checkout", "--quiet", "-B", "yan", eski_sha)
        with open(os.path.join(ayrik, "urunler.json"), "w", encoding="utf-8") as f:
            json.dump([_kt_urun("u00")], f)
        _kt_git(ayrik, "add", "-A")
        _kt_git(ayrik, "commit", "--quiet", "-m", "ayrik dal")
        b = _kt_bayatlik(ayrik)
        dogrula("V45 BAYATLIK: uctan AYRIK agac (bayat worktree deseni) -> BAYAT",
                b["durum"] == "BAYAT", b)

        # SIG (shallow) checkout: uc SHA'si yerelde YOK -> bilmedigimiz bir sey yayinda.
        sig = os.path.join(tmp, "sig")
        _kt_git(tmp, "clone", "--quiet", "--depth", "1", "file://" + uzak, sig)
        with open(os.path.join(yerel, "urunler.json"), "w", encoding="utf-8") as f:
            json.dump([_kt_urun("u00"), _kt_urun("yeni1"), _kt_urun("yeni2")], f)
        _kt_git(yerel, "add", "-A")
        _kt_git(yerel, "commit", "--quiet", "-m", "parti2")
        _kt_git(yerel, "push", "--quiet", "origin", "main")
        b = _kt_bayatlik(sig)
        dogrula("V46 BAYATLIK: uc commit'i agacta YOK (sig klon + uc ilerledi) -> BAYAT",
                b["durum"] == "BAYAT", b)

        # OLCULEMEDI = FAIL-CLOSED (uzak yok / git deposu degil).
        uzaksiz = os.path.join(tmp, "uzaksiz")
        _kt_git(tmp, "init", "--quiet", uzaksiz)
        _kt_git(uzaksiz, "commit", "--quiet", "--allow-empty", "-m", "x")
        b = _kt_bayatlik(uzaksiz)
        dogrula("V47 BAYATLIK: uzak okunamiyor -> OLCULEMEDI (yesil DEGIL)",
                b["durum"] == "OLCULEMEDI", b)
        b = _kt_bayatlik(os.path.join(tmp, "hicyok"))
        dogrula("V48 BAYATLIK: git deposu degil -> OLCULEMEDI (istisna SIZMAZ)",
                b["durum"] == "OLCULEMEDI", b)

        # ── YANLIS-POZITIF NOBETI: 25 GERCEK URUN COMMIT'I (paylasimli hook!) ──────
        # Kapi yanlis-pozitif verirse TUM mimarlarin push'u kirilir. Her adimda hem
        # PUSH'TAN ONCE (yerel ileride) hem PUSH'TAN SONRA (uc = HEAD) olculur.
        yanlis, olculen = [], 0
        katalog = [_kt_urun("u00")]
        for i in range(25):
            katalog.insert(0, _kt_urun("parti%02d" % i))
            with open(os.path.join(yerel, "urunler.json"), "w", encoding="utf-8") as f:
                json.dump(katalog, f)
            _kt_git(yerel, "add", "-A")
            _kt_git(yerel, "commit", "--quiet", "-m", "urun partisi %d" % i)
            d = _kt_bayatlik(yerel)["durum"]
            olculen += 1
            if d != "UC":
                yanlis.append(("push-oncesi", i, d))
            _kt_git(yerel, "push", "--quiet", "origin", "main")
            d = _kt_bayatlik(yerel)["durum"]
            olculen += 1
            if d != "UC":
                yanlis.append(("push-sonrasi", i, d))
        dogrula("V49 YANLIS-POZITIF NOBETI: 25 gercek urun commit'i x2 olcum -> KIRMIZI 0",
                yanlis == [] and olculen == 50, (yanlis[:5], olculen))

        # ── UPSERT EKSENI YANLIS-POZITIF NOBETI (UCTAN UCA) ──────────────────────
        # Kapi artik UPSERT'i de durduruyor -> mesru akan bir parti AKISI kirilmamali.
        # Bu nobet stub KULLANMAZ: her adimda GERCEK bayatlik_olc() gercek git agacinda
        # olcer ve GERCEK senkron (sqlite sahte D1) kosar. Bir tek yanlis-pozitif TUM
        # mimarlarin urun push'unu yazmasiz birakirdi.
        connU = _kt_baglan()
        katalogU = [_kt_urun("t00")]
        yaziU, kirmiziU, yazmayanU = 0, [], 0
        yaz_katalogU = os.path.join(tmp, "upsert")
        os.makedirs(yaz_katalogU, exist_ok=True)
        for i in range(25):
            katalogU.insert(0, _kt_urun("uparti%02d" % i))
            if i % 5 == 4:                       # her 5. partide bir ALAN degisimi de var
                katalogU[-1] = _kt_urun("t00", "Tamirat" if i % 10 == 4 else "Ev")
            with open(os.path.join(yerel, "urunler.json"), "w", encoding="utf-8") as f:
                json.dump(katalogU, f)
            _kt_git(yerel, "add", "-A")
            _kt_git(yerel, "commit", "--quiet", "-m", "upsert partisi %d" % i)
            # PRE-PUSH ANI: uzak HENUZ eski uctadir, yerel ILERIDEDIR (gercek hook hali).
            kodU, ciktiU, sayacU = _kt_kos(connU, katalogU, [], kok=yerel)
            if kodU != 0:
                kirmiziU.append((i, ciktiU[-200:]))
            if sayacU["yazma"] == 0:
                yazmayanU += 1
            yaziU += sayacU["yazma"]
            _kt_git(yerel, "push", "--quiet", "origin", "main")
        dogrula("V49b UPSERT YANLIS-POZITIF NOBETI: 25 gercek parti UCTAN UCA -> kirmizi 0",
                kirmiziU == [], (len(kirmiziU), kirmiziU[:2]))
        dogrula("V49c UPSERT NOBETI: 25 partinin 25'i D1'e FIILEN yazdi (sessiz atlama YOK)",
                yazmayanU == 0 and yaziU > 0, (yazmayanU, yaziU))
        dogrula("V49d UPSERT NOBETI: son partinin urunu D1'de VAR (yazma gercekten islendi)",
                _kt_deger(connU, "uparti24", "hash") is not None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # B) DAVRANIS — kapi silme yolunda FIILEN devrede mi (offline sqlite fikstur).
    # 🔴 BUGUNKU OLAYIN BIREBIR YENIDEN URETIMI: D1'de 42 YENI id var (baska bir push
    # onlari yazdi), bayat agacin urunler.json'unda YOKLAR -> eski kod hepsini SILERDI.
    yeni_parti = [_kt_urun("dp%06d" % i) for i in range(42)]
    eski_agac = [_kt_urun("a"), _kt_urun("b"), _kt_urun("c")]
    connB = _kt_baglan()
    _kt_kos(connB, eski_agac + yeni_parti, [])                    # yeni parti D1'e girdi
    kod, cikti, sayac = _kt_kos(connB, eski_agac, [], bayatlik="UC")   # KAPI ONCESI davranis
    kalan_once = sum(1 for u in yeni_parti if _kt_deger(connB, u["id"], "hash") is not None)
    dogrula("V50 YENIDEN URETIM (KAPI ONCESI = UC yolu): bayat agac 42 id'yi SILDI",
            kod == 0 and kalan_once == 0 and "silinen: 42" in cikti, (kod, kalan_once))

    connC = _kt_baglan()
    _kt_kos(connC, eski_agac + yeni_parti, [])
    kod, cikti, sayac = _kt_kos(connC, eski_agac, [], bayatlik="BAYAT")  # KAPI SONRASI
    kalan_sonra = sum(1 for u in yeni_parti if _kt_deger(connC, u["id"], "hash") is not None)
    dogrula("V51 YENIDEN URETIM (KAPI SONRASI): silinen 0 — 42 id'nin 42'si D1'de DURUYOR",
            kalan_sonra == 42, kalan_sonra)
    dogrula("V52 YENIDEN URETIM: engel SESSIZ DEGIL -> sifir-disi + id'ler mesajda",
            kod != 0 and "BAYATLIK KAPISI" in cikti and "dp0000" in cikti,
            (kod, cikti[-500:]))
    dogrula("V53 YENIDEN URETIM: D1'e HIC yazma yapilmadi",
            sayac["yazma"] == 0, sayac)

    # OLCULEMEDI de silmeyi durdurur (fail-closed; 'olcemedim' YESIL degildir).
    connD = _kt_baglan()
    _kt_kos(connD, eski_agac + yeni_parti, [])
    kod, cikti, _ = _kt_kos(connD, eski_agac, [], bayatlik="OLCULEMEDI")
    dogrula("V54 FAIL-CLOSED: OLCULEMEDI -> silme 0 + sifir-disi",
            kod != 0 and _kt_deger(connD, "dp000000", "hash") is not None, kod)

    # ── UPSERT EKSENI (KraL karari 31 Tem): bayat agac UPSERT de YAPAMAZ ──────────
    # Bayat upsert D1'e ESKI alan degerlerini YENI degerlerin ustune yazar — silmeyle
    # AYNI sessiz-bozulma sinifi. Bugun "3 bayat hash" olarak fiilen gozlendi.
    connE = _kt_baglan()
    _kt_kos(connE, eski_agac + yeni_parti, [])
    kod, cikti, sayac = _kt_kos(
        connE, [_kt_urun("a", "Tamirat"), _kt_urun("b"), _kt_urun("c")], [],
        bayatlik="BAYAT")
    dogrula("V55 UPSERT ENGELI: bayat agacin ALAN guncellemesi D1'e YAZILMADI",
            _kt_deger(connE, "a", "kategori") == "Oyun/Hobi" and kod != 0,
            (_kt_deger(connE, "a", "kategori"), kod))
    dogrula("V55b UPSERT ENGELI: D1'e HIC yazma cagrisi gitmedi + is dokumu mesajda",
            sayac["yazma"] == 0 and "Engellenen is" in cikti and "degisen 1" in cikti,
            (sayac, cikti[-600:]))
    # SALT-YENI parti (silme YOK): eski kapi bunu HIC olcmezdi, yeni kapi DURDURUR.
    connE2 = _kt_baglan()
    _kt_kos(connE2, eski_agac, [])
    kod, cikti, sayac = _kt_kos(connE2, eski_agac + [_kt_urun("yy")], [], bayatlik="BAYAT")
    dogrula("V55c UPSERT ENGELI: SILME YOK / yalniz YENI urun -> yine de yazilmadi",
            kod != 0 and sayac["yazma"] == 0 and sayac["bayatlik"] == 1
            and _kt_deger(connE2, "yy", "hash") is None, (kod, sayac))
    dogrula("V55d UPSERT ENGELI: OLCULEMEDI de upsert'i durdurur (fail-closed)",
            _kt_kos(connE2, eski_agac + [_kt_urun("yy")], [],
                    bayatlik="OLCULEMEDI")[0] != 0
            and _kt_deger(connE2, "yy", "hash") is None)
    _sayac_deger = connE2.execute(
        "SELECT deger AS v FROM senkron WHERE anahtar='urun_sayisi'").fetchone()
    dogrula("V55e SAHTE DAMGA YOK: senkron sayaci saglikli kosumun degerinde KALDI (3)",
            _sayac_deger is not None and _sayac_deger["v"] == "3",
            _sayac_deger["v"] if _sayac_deger else None)

    # ── MESRU SILME KAPANMADI (duzelt.py --toplu senaryosu) ───────────────────────
    # duzelt.py --toplu urunleri urunler.json'dan cikarir; commit+push'ta pre-push hook
    # d1-sync'i kosar ve o an agac UCTAN ILERIDEDIR (V43) -> durum UC -> SILME GECMELI.
    connF = _kt_baglan()
    toplu = [_kt_urun("k%02d" % i) for i in range(70)] + eski_agac
    _kt_kos(connF, toplu, [])
    kod, cikti, _ = _kt_kos(connF, eski_agac, [], bayatlik="UC")
    kalan_toplu = sum(1 for i in range(70) if _kt_deger(connF, "k%02d" % i, "hash") is not None)
    dogrula("V56 MESRU SILME: duzelt.py --toplu ile kaldirilan 70 urun D1'den SILINDI (exit 0)",
            kod == 0 and kalan_toplu == 0 and "silinen: 70" in cikti, (kod, kalan_toplu))

    # ── MALIYET EKSENI: YAZACAK IS varken TAM 1 kez, yoksa HIC olculmez ─────────
    connG = _kt_baglan()
    _kt_kos(connG, eski_agac, [])
    kod, cikti, sayac = _kt_kos(connG, eski_agac + [_kt_urun("z1")], [])
    dogrula("V57 MALIYET: yazacak is VARKEN (yalniz yeni urun) bayatlik TAM 1 kez olculur",
            kod == 0 and sayac["bayatlik"] == 1, sayac)
    connH = _kt_baglan()
    _kt_kos(connH, eski_agac, [])
    kod, cikti, sayac = _kt_kos(connH, eski_agac[:2], [], bayatlik="UC")
    dogrula("V58 MALIYET: silme VARKEN de bayatlik TAM 1 kez olculur (mukerrer olcum YOK)",
            kod == 0 and sayac["bayatlik"] == 1, sayac)

    # ── YAZACAK IS YOKSA: kapi HIC olculmez (0 git/ag cagrisi) ──────────────────
    # Yazmayan kosum zarar veremez; bayat da olsa engellenecek bir sey yoktur.
    connI = _kt_baglan()
    _kt_kos(connI, eski_agac + yeni_parti, [])
    kod, cikti, sayac = _kt_kos(connI, eski_agac + yeni_parti, [], bayatlik="BAYAT")
    dogrula("V59 MALIYET: degisiklik yokken bayatlik HIC olculmez -> exit 0",
            kod == 0 and "degisiklik yok" in cikti and sayac["bayatlik"] == 0, (kod, sayac))
    kod, cikti, sayac = _kt_kos(connI, eski_agac, ["--kuru"], bayatlik="BAYAT")
    dogrula("V59b MALIYET: --kuru bayatligi OLCMEZ ve engellemez (planlama araci)",
            kod == 0 and sayac["bayatlik"] == 0 and sayac["yazma"] == 0, (kod, sayac))

    # ── `--bayatlik` KOLU: CI adiminin ON-KOSULU bu cikis koduna bagli ───────────
    # deploy.yml bu kolu "bayat kosum D1'e HIC dokunmasin" on-kosulu olarak kullanir;
    # cikis kodu tersine donerse (ya da hep 0 olursa) CI kolu SESSIZCE olur.
    connJ = _kt_baglan()
    kod, cikti, sayac = _kt_kos(connJ, eski_agac, ["--bayatlik"], bayatlik="UC")
    dogrula("V60 --bayatlik: UC -> exit 0 + D1'e HIC dokunmaz",
            kod == 0 and sayac["yazma"] == 0 and sayac["okuma"] == 0
            and "bayatlik: UC" in cikti, (kod, sayac, cikti[-200:]))
    kod, cikti, sayac = _kt_kos(connJ, eski_agac, ["--bayatlik"], bayatlik="BAYAT")
    dogrula("V61 --bayatlik: BAYAT -> sifir-disi (CI on-kosulu ATLAR)",
            kod != 0 and sayac["yazma"] == 0, (kod, sayac))
    kod, cikti, sayac = _kt_kos(connJ, eski_agac, ["--bayatlik"], bayatlik="OLCULEMEDI")
    dogrula("V62 --bayatlik: OLCULEMEDI -> sifir-disi (olcemedim YESIL degil)",
            kod != 0, kod)

    # ── CI ON-KOSULU CAPASI: deploy.yml'deki senkron adimi bayatligi SORUYOR mu ──
    # NEDEN BURADA: `d1-sync.py` ci-kapsam/is-akisi kesif predikatlarina GIRMEZ ve
    # senkron adimi bilincli olarak `continue-on-error` (fail-open) -> Bolum D/E o
    # adimi GORMEZ. On-kosul satiri sessizce silinirse BAYAT KOSUM yine D1'e yazar
    # (upsert'ler bayat kalir) ve hicbir kapi kirmizi yanmaz. Capa burada yasar.
    _dy = os.path.join(KOK, ".github", "workflows", "deploy.yml")
    if not os.path.exists(_dy):
        dogrula("V63 CI ON-KOSUL CAPASI: deploy.yml BULUNAMADI (olculemedi = KIRMIZI)",
                False, _dy)
    else:
        with open(_dy, encoding="utf-8") as _f:
            _gv = _f.read()
        _adim = _gv.split("- name: Katalogu D1'e senkronla")
        _blok = _adim[1].split("\n  - name:")[0].split("\n\n  deploy:")[0] if len(_adim) > 1 else ""
        _on = _blok.find("d1-sync.py --bayatlik")
        _tam = _blok.find("python3 tools/d1-sync.py\n")
        dogrula("V63 CI ON-KOSUL CAPASI: senkron adimi ONCE `--bayatlik` sorar, SONRA senkronlar",
                len(_adim) == 2 and _on > 0 and _tam > _on, (len(_adim), _on, _tam))
        dogrula("V64 CI ON-KOSUL CAPASI: on-kosulun CIKIS KODU kullaniliyor (mensiyon degil)",
                "if ! python3 tools/d1-sync.py --bayatlik; then" in _blok,
                _blok[:400])

    # ══════════════════════════════════════════════════════════════════════════
    # WRANGLER HATA SINIFLANDIRMASI + CIKTI COZUMU (31 Tem, run 30646713630)
    # ══════════════════════════════════════════════════════════════════════════
    # OLCULEN OLAY: baska bir push'un 1761 satirlik yazmasi D1'in CPU butcesini harcadi,
    # DB reset edildi ve `yayin` isi kirmizi dustu -> 25 urun TASLAK kaldi. Ariza GECICI
    # idi (ayni sorgular saniyeler sonra geciyor) ama arac onu KALICI gibi isledi:
    #   (1) tani kolu OLUYDU: gercek yuk JSON/TIRNAKLI oldugu icin alt-dize listesi
    #       hicbir kodu yakalamiyordu -> yeniden deneme HIC denenmedi;
    #   (2) hata zarfi "basarili cikti" sanilip parse ediliyor, `7429 / CPU time limit`
    #       mesaji YUTULUP "cozulemedi" basiliyordu -> teshis saatlerce gecikti.
    # Bu vakalar iki kolu da yasatir.
    _YUK_7429 = ('{\n  "error": {\n'
                 '    "text": "A request to the Cloudflare API (/accounts/dbbe2a86.../'
                 'd1/database/3d99d15e-.../query) failed.",\n'
                 '    "notes": [\n      {\n        "text": "D1 DB exceeded its CPU time '
                 'limit and was reset. [code: 7429]"\n      }\n    ],\n'
                 '    "kind": "error",\n    "name": "APIError",\n    "code": 7429,\n'
                 '    "accountTag": "00000000000000000000000000000000"\n  }\n}')
    dogrula("V65 TANI POZITIF (GERCEK CI YUKU): 7429 CPU-reset zarfi -> GECICI",
            wrangler_hata_tanisi(_YUK_7429) == "gecici", wrangler_hata_tanisi(_YUK_7429))
    _bicimler = {
        'TIRNAKLI JSON  "code": 503': '{"error": {"code": 503, "name": "APIError"}}',
        "TIRNAKSIZ metin  code: 503": "Cloudflare API failed. code: 503",
        "KOSELI not  [code: 503]": "something broke [code: 503]",
    }
    _bicim_kirmizi = {a: wrangler_hata_tanisi(h) for a, h in _bicimler.items()
                      if wrangler_hata_tanisi(h) != "gecici"}
    dogrula("V66 TANI BICIM-BAGIMSIZLIGI: 503'un UC bicimi de GECICI (tirnak/koseli/duz)",
            _bicim_kirmizi == {}, _bicim_kirmizi)
    _kod_kirmizi = {k: wrangler_hata_tanisi('{"error": {"code": %d}}' % k)
                    for k in (429, 500, 502, 503, 504, 7429)
                    if wrangler_hata_tanisi('{"error": {"code": %d}}' % k) != "gecici"}
    dogrula("V67 TANI KUME: 429/500/502/503/504/7429 JSON bicimde HEPSI gecici",
            _kod_kirmizi == {}, _kod_kirmizi)
    # NEGATIF EKSEN — kapi gevsemesin: 10000 KALICI (auth) kolunda KALIR, alakasiz metin None.
    dogrula("V68 TANI NEGATIF: 10000 auth KOLUNDA KALIR (tirnakli + tirnaksiz)",
            wrangler_hata_tanisi('{"error": {"code": 10000, "name": "APIError"}}') == "auth"
            and wrangler_hata_tanisi("Authentication error [code: 10000]") == "auth",
            (wrangler_hata_tanisi('{"error": {"code": 10000}}'),))
    dogrula("V69 TANI NEGATIF: alakasiz metin -> None (her seye 'gecici' demez)",
            wrangler_hata_tanisi("Executed 3 commands in 0.42s") is None,
            wrangler_hata_tanisi("Executed 3 commands in 0.42s"))
    # 🔴 DAR TUTMA IDDIASI: kod tespiti `code`/`status` ANAHTARINA baglidir. Serbest
    # sayi eslesmesine kaysaydi (or. `\b7429\b`) BASARILI bir cikti ya da urun id'si
    # "gecici hata" sayilir, arac saglam kosumda bekleyip sifir-disi cikardi.
    _sayi_tuzagi = {
        "satir sayisi": "Successfully wrote 7429 rows in 1.2s",
        "urun id'si": '{"results": [{"id": "t429503", "hash": "H1"}], "success": true}',
        "sure/olcum": "duration: 502.4 ms, rows_read: 500",
    }
    _tuzak_kirmizi = {a: wrangler_hata_tanisi(h) for a, h in _sayi_tuzagi.items()
                      if wrangler_hata_tanisi(h) is not None}
    dogrula("V70 TANI YANLIS-POZITIF NOBETI: icinde 429/503/500 GECEN saglam metin -> None",
            _tuzak_kirmizi == {}, _tuzak_kirmizi)

    # ── CIKTI COZUMU: hata zarfi ADIYLA raporlanir, basarili SEKIL degismez ──────
    try:
        wrangler_cikti_coz(_YUK_7429, _YUK_7429)
        _zarf_mesaj = "(SystemExit ATILMADI — hata zarfi BASARI sanildi)"
    except SystemExit as e:
        _zarf_mesaj = str(e.code)
    dogrula("V71 PARSE POZITIF: hata zarfi ADIYLA basilir (7429 + CPU time limit)",
            "7429" in _zarf_mesaj and "CPU time limit" in _zarf_mesaj
            and "cozulemedi" not in _zarf_mesaj, _zarf_mesaj[:300])
    _basari = ('[\n  {\n    "results": [{"id": "a", "hash": "H1"}],\n'
               '    "success": true,\n    "meta": {"rows_written": 1, "rows_read": 0}\n  }\n]')
    _r = wrangler_cikti_coz(_basari, _basari)
    dogrula("V72 PARSE SEKLI DEGISMEDI: basarili cikti -> r[0]['results'] okunabilir",
            isinstance(_r, list) and _r[0]["results"][0]["id"] == "a"
            and _r[0]["meta"]["rows_written"] == 1, _r)
    _r2 = wrangler_cikti_coz("\n Proxy environment variables detected...\n" + _basari
                             + "\n", "")
    dogrula("V72b PARSE: JSON'dan ONCE/SONRA log satiri olsa da basari cozulur",
            isinstance(_r2, list) and _r2[0]["results"][0]["id"] == "a", _r2)
    try:
        wrangler_cikti_coz("wrangler kilitlendi, cikti yok", "wrangler kilitlendi, cikti yok")
        _cop = "(SystemExit ATILMADI)"
    except SystemExit as e:
        _cop = str(e.code)
    dogrula("V72c PARSE NEGATIF: GERCEKTEN cozulemeyen cikti hala ciplak mesaj verir",
            "cikti vermedi" in _cop or "cozulemedi" in _cop, _cop[:200])

    # ── FAIL-LOUD NOBETI: "cozulebilir ama YANLIS" JSON parcasi BASARI SAYILAMAZ ────
    # 🔴 BAGIMSIZ CURUTUCUNUN OLCTUGU 4 VAKA (girdiler AYNEN). Ilk onarim bu vakalarda
    # eski kodun FAIL-LOUD davranisini FAIL-OPEN'a cevirmisti: `raw_decode` ILK cozulebilen
    # ON-EKI aliyordu, eski `json.loads(stdout[i:])` ise kalanin TAMAMININ gecerli olmasini
    # zorluyordu. En yikici sonuc: KESIK yuk -> `dosya_calistir` SESSIZCE "0 satir yazildi"
    # der, oysa wrangler rc=1 ile dusmustur. D1 reset ortasinda ciktinin kesik gelmesi
    # BEKLENEN haldir; yani kusur tam da bu araci yazma sebebimiz olan senaryoda vururdu.
    def _coz_sonucu(stdout, rc):
        try:
            return ("DONDU", wrangler_cikti_coz(stdout, stdout, rc))
        except SystemExit as e:
            return ("EXIT", str(e.code))

    _KESIK = '[{"results":[{"id":"a"}],"success":tr'
    _NPX = ("X [WARNING] Unexpected fields found in d1_databases[0] field\n"
            "npx: command failed")
    _UYARI_YUK = ('X [WARNING] Unexpected fields found in d1_databases[0] field\n'
                  '[{"results":[{"id":"a","urun_hash":"H1"}],"success":true,'
                  '"meta":{"rows_written":1761}}]')
    _YARIM_ZARF = '{"error": {"text": "istek dustu", "notes": []'
    _v = _coz_sonucu(_KESIK, 1)
    dogrula("V75 FAIL-LOUD: rc=1 + KESIK JSON -> EXIT (eskiden [{'id':'a'}] DONUYORDU)",
            _v[0] == "EXIT", _v)
    _v = _coz_sonucu(_KESIK, 0)
    dogrula("V75b FAIL-LOUD: KESIK JSON rc=0'da da EXIT (butunluk sarti rc'den BAGIMSIZ)",
            _v[0] == "EXIT", _v)
    _v = _coz_sonucu(_NPX, 2)
    dogrula("V76 FAIL-LOUD: rc=2 + `d1_databases[0]` uyarisi -> EXIT ([0] DONMEZ)",
            _v[0] == "EXIT", _v)
    _v = _coz_sonucu(_UYARI_YUK, 0)
    dogrula("V77 GERCEK YUK GORULUR: uyari satirindaki `[0]` DEGIL, ASIL sonuc doner",
            _v[0] == "DONDU" and isinstance(_v[1], list) and len(_v[1]) == 1
            and _v[1][0]["meta"]["rows_written"] == 1761
            and _v[1][0]["results"][0]["urun_hash"] == "H1", _v)
    _v = _coz_sonucu(_YARIM_ZARF, 0)
    dogrula("V78 FAIL-LOUD: YARIM hata zarfi -> EXIT (eski kod da yeni kod da [] donerdi)",
            _v[0] == "EXIT", _v)
    _v = _coz_sonucu(_basari, 1)
    dogrula("V79 RC KAPISI: rc=1 + TAM GECERLI JSON -> yine de EXIT (rc BASARIYI EZER)",
            _v[0] == "EXIT" and "rc=1" in _v[1], _v)
    # KUSUR-2: tani YALNIZ rc!=0'da uygulanir. Basarili bir cevabin ICINDEKI veri
    # ("code":503 tasiyan bir satir) araci "GECICI HATA" ile dusuremez.
    _kod_veri = ('[{"results":[{"id":"a","code":503}],"success":true,"meta":{}}]')

    class _SahteP2:
        def __init__(self, kod, cikti):
            self.returncode, self.stdout, self.stderr = kod, cikti, ""

    _eski_run2 = subprocess.run
    subprocess.run = lambda *a, **k: _SahteP2(0, _kod_veri)
    try:
        try:
            _rr = ("DONDU", wrangler(["--command", "SELECT 1"]))
        except SystemExit as e:
            _rr = ("EXIT", str(e.code))
    finally:
        subprocess.run = _eski_run2
    dogrula("V80 TANI KAPSAMI: rc=0 + sonuc verisinde 'code':503 -> BASARI (gecici SAYILMAZ)",
            _rr[0] == "DONDU" and _rr[1][0]["results"][0]["code"] == 503, _rr)

    # ── CAGRI SATIRI CAPASI: wrangler() -> wrangler_cikti_coz BAGI (UCTAN UCA) ────
    # 🔴 OLU IDDIA DERSI (curutucu 2. tur, C6): `wrangler_cikti_coz(..., p.returncode)`
    # cagrisindaki UCUNCU ARGUMAN dusurulup `0` yazilinca (mutant) kabul testi 101/0
    # YESIL kaliyordu — cunku V79/V81 fonksiyonu DOGRUDAN cagiriyor, yani rc gardinin
    # BESLENDIGI satir nobetsizdi. Bu evde adi konmus desen: "nobetci cagri satiri
    # nobetsiz". Asagidaki iddia bagi UCTAN UCA (sahte subprocess ile) sinar.
    # PROBE NEDEN BU KADAR DAR: yuk TAM GECERLI bir wrangler basari yuku (bos olmayan
    # liste + results/success/meta + artik YOK). Boylece `_basari_sekli_mi` de
    # `_artik_gurultu_mu` da bu vakayi GECIRIR; onu durduran TEK sey cagri satirindan
    # gecen rc'dir. Kesik/bozuk bir probe secilseydi iddia sekil kuralinin sirtina biner
    # ve C6 mutanti yine hayatta kalirdi (curutucunun olctugu davranissal delta zaten
    # YALNIZ "rc != 0 + TAM GECERLI yuk" vakasindaydi).
    def _uctan_uca_wrangler(rc, cikti):
        eski = subprocess.run
        subprocess.run = lambda *a, **k: _SahteP2(rc, cikti)
        try:
            try:
                return ("DONDU", wrangler(["--command", "SELECT 1"]))
            except SystemExit as e:
                return ("EXIT", str(e.code))
        finally:
            subprocess.run = eski

    _uu = _uctan_uca_wrangler(1, _basari)
    dogrula("V84 CAGRI SATIRI: wrangler() rc=1 + TAM GECERLI yuk -> SIFIR-DISI (bag CANLI)",
            _uu[0] == "EXIT", _uu)
    # MUT: cagri satiri rc'yi GECIRMEZ (`wrangler_cikti_coz(..., 0)`) -> iddia KIRMIZI yanmali.
    _eski_coz = wrangler_cikti_coz
    globals()["wrangler_cikti_coz"] = (
        lambda stdout, ham="", returncode=0: _eski_coz(stdout, ham, 0))
    _mut_bag = _uctan_uca_wrangler(1, _basari)
    globals()["wrangler_cikti_coz"] = _eski_coz
    dogrula("V84b MUT-CAGRI-RC-DUSUR: rc gecirilmezse rc=1 cikti BASARI sanilir (iddia CANLI)",
            _mut_bag[0] == "DONDU", _mut_bag)
    dogrula("V84c MUT geri alindi: bag yine SIFIR-DISI",
            _uctan_uca_wrangler(1, _basari)[0] == "EXIT")

    # ── 🔴 MUTASYON IDDIALARI (parse kolu) ───────────────────────────────────────
    # PROBE SECIMI DAR: her probe YALNIZ oldurulen kuralin yakalayabilecegi vakadir.
    #  · rc kapisi probe'u = V79 girdisi (TAM GECERLI JSON + rc=1). Yuk saglam oldugu
    #    icin sekil/artik kurallari bu vakayi GECIRIR; onu durduran TEK sey rc kapisidir.
    #  · sekil kurali probe'u = V77 girdisi (uyaridaki `[0]` + gercek yuk, rc=0). rc
    #    kapisi burada devrede DEGIL; `[0]`i eleyen TEK sey liste-of-sonuc sartidir.
    _eski_rc = _rc_hatali
    globals()["_rc_hatali"] = lambda rc: False                 # MUT: rc kapisi NO-OP
    _mut_rc = _coz_sonucu(_basari, 1)
    globals()["_rc_hatali"] = _eski_rc
    dogrula("V81 MUT-RC-NOOP: rc kapisi oldurulunce rc=1 cikti BASARI sanilir (iddia CANLI)",
            _mut_rc[0] == "DONDU", _mut_rc)
    dogrula("V81b MUT geri alindi: rc=1 yine EXIT", _coz_sonucu(_basari, 1)[0] == "EXIT")
    _eski_sekil = _basari_sekli_mi
    globals()["_basari_sekli_mi"] = lambda d: isinstance(d, list)   # MUT: sekil sarti gevser
    _mut_sekil = _coz_sonucu(_UYARI_YUK, 0)
    globals()["_basari_sekli_mi"] = _eski_sekil
    dogrula("V82 MUT-SEKIL-NOOP: sekil sarti gevseyince uyaridaki `[0]` yuk sanilir",
            _mut_sekil == ("DONDU", [0]), _mut_sekil)
    dogrula("V82b MUT geri alindi: gercek yuk yine doner",
            _coz_sonucu(_UYARI_YUK, 0)[1][0]["meta"]["rows_written"] == 1761)
    #  · artik (butunluk) kurali probe'u AYRI bir girdi olmak ZORUNDA: V75'teki `_KESIK`
    #    yuku artik kurali no-op edilse BILE sekil kurali tarafindan eleniyor (icteki
    #    cozulebilen parca `[{"id":"a"}]` sonuc anahtari tasimaz) -> o vakayla kurulan
    #    iddia OLU olurdu. Bu probe'ta cozulen ILK deger BASARI SEKLINDE (sekil kurali
    #    GECIRIR); onu durduran TEK sey artiktaki `,` yani "bu bir BUTUNUN parcasi"dir.
    _PARCA_YUK = '{"sarmal": [{"results":[],"success":true,"meta":{}}], "hata'
    dogrula("V83 BUTUNLUK: sarmalanmis/kesik yukun ICINDEKI gecerli liste BASARI SAYILMAZ",
            _coz_sonucu(_PARCA_YUK, 0)[0] == "EXIT", _coz_sonucu(_PARCA_YUK, 0))
    _eski_artik = _artik_gurultu_mu
    globals()["_artik_gurultu_mu"] = lambda a: True             # MUT: artik sarti NO-OP
    _mut_artik = _coz_sonucu(_PARCA_YUK, 0)
    globals()["_artik_gurultu_mu"] = _eski_artik
    dogrula("V83b MUT-ARTIK-NOOP: butunluk sarti olunce parca BASARI sanilir (iddia CANLI)",
            _mut_artik[0] == "DONDU", _mut_artik)
    dogrula("V83c MUT geri alindi: parca yine EXIT",
            _coz_sonucu(_PARCA_YUK, 0)[0] == "EXIT")

    # ── GERI CEKILME: gecici sinifta ARTAN bekleme, deneme 3, TAVAN sinirli ──────
    class _SahteP:
        def __init__(self, kod, cikti):
            self.returncode, self.stdout, self.stderr = kod, cikti, ""

    _uykular, _cagri = [], [0]

    def _sahte_run(*a, **k):
        _cagri[0] += 1
        return _SahteP(1, _YUK_7429)

    _eski_run, _eski_sleep = subprocess.run, time.sleep
    subprocess.run, time.sleep = _sahte_run, _uykular.append   # GERCEK bekleme YOK
    try:
        try:
            wrangler(["--command", "SELECT 1"])
            _mesaj = "(SystemExit ATILMADI)"
        except SystemExit as e:
            _mesaj = str(e.code)
    finally:
        subprocess.run, time.sleep = _eski_run, _eski_sleep
    dogrula("V73 GERI CEKILME: 7429 -> 3 deneme yapilir (eskiden 1: kod olu, retry YOK)",
            _cagri[0] == 3, _cagri[0])
    dogrula("V73b GERI CEKILME: beklemeler ARTAN ve kozmetik DEGIL (>=2 s, toplam <=10 s)",
            _uykular == list(GECICI_BEKLEME) and _uykular[0] >= 2
            and _uykular[1] > _uykular[0] and sum(_uykular) <= 10, _uykular)
    dogrula("V73c GERI CEKILME: tukenince GECICI diye sifir-disi cikar (sessiz degil)",
            "GECICI HATA" in _mesaj, _mesaj[:200])

    # ── 🔴 MUTASYON IDDIASI: kod tespiti no-op edilirse V65 KIRMIZI yanmali ──────
    # PROBE NEDEN BU: iddiayi OLU birakmamak icin probe, YALNIZ onarilan kod-tespit
    # kuralinin yakalayabilecegi bir yuke cekildi. Gercek 7429 zarfinda ag/soket
    # alt-dizelerinden HICBIRI yok ("timeout" yok — metin "CPU time limit"; "fetch
    # failed" yok — metin "A request ... failed"), "rate limit"/"too many requests"
    # de gecmiyor. Yani bu yuku GECICI yapan TEK sey `code: 7429` tespitidir; regex
    # oldurulunce vaka DUSMEK ZORUNDA. (Desen: denetim-kapisi-test.py MUT-BOS-LISTE.)
    _eski_kod_re = _KOD_RE
    globals()["_KOD_RE"] = re.compile(r"(?!)")             # MUT: kod tespiti NO-OP
    _mutant_tani = wrangler_hata_tanisi(_YUK_7429)
    globals()["_KOD_RE"] = _eski_kod_re
    dogrula("V74 MUT-KOD-NOOP: kod tespiti oldurulunce GERCEK 7429 yuku 'gecici' OLMAZ",
            _mutant_tani != "gecici", _mutant_tani)
    dogrula("V74b MUT geri alindi: 7429 yine GECICI (mutant kalici yan etki birakmadi)",
            wrangler_hata_tanisi(_YUK_7429) == "gecici")

    # ══ SEMA EKSENI — GOC INDEKSLERI (tek-yonlu kapi nobeti) ═════════════════════
    # OLCULEN ARIZA: ALTER'lar gecip `CREATE UNIQUE INDEX` DUSERSE kolonlar VAR olur ama
    # yaris korumasi YOKTUR; yazma kapisi yalniz KOLON yoklugunu gordugu icin INSERT'ler
    # gecer. O pencerede olusan tek bir ikiz satir indeksi KALICI olarak kurulamaz yapar.
    # Once-kirmizi: bu vakalarin HEPSI eski kodda YESIL/SESSIZDI (--sema 0, --durum 0).

    # V75 HAL AYRIMI: dort hal AYRI AYRI (biri digerini maskelemesin).
    _ad = GOC_INDEKS[-1]["ad"]
    _h = lambda c: {x["ad"]: x["hal"] for x in _kt_goc_kos(c, sema_hali)[2]}   # noqa: E731
    dogrula("V75a HAL: kanal/dis_no kolonu YOK -> UYGULANMAZ (kirmizi DEGIL)",
            _h(_kt_goc_conn(kanal_kolonu=False))[_ad] == IX_UYGULANMAZ)
    dogrula("V75b HAL: kolon VAR + indeks YOK -> INDEKS-YOK (eskiden YESIL gorunuyordu)",
            _h(_kt_goc_conn())[_ad] == IX_INDEKS_YOK)
    dogrula("V75c HAL: kolon VAR + indeks VAR -> KURULU",
            _h(_kt_goc_conn(indeks=True))[_ad] == IX_KURULU)
    dogrula("V75d HAL: ALTER'lar YARIDA (yalniz kanal eklendi) -> KOLON-YARIM",
            _h(_kt_goc_conn(yarim=True))[_ad] == IX_KOLON_YARIM)

    # V76 TEMIZ GOC: indeks kurulur, kurulusu DOGRULANIR, kolon_goc True doner.
    _c = _kt_goc_conn()
    _kod, _cikti, _sonuc = _kt_goc_kos(_c, kolon_goc)
    dogrula("V76 TEMIZ GOC: kismi UNIQUE indeks KURULUR + kolon_goc True",
            _sonuc is True and _ad in _kt_indeks_adlari(_c), _cikti[-300:])

    # V77 IKIZ SATIR: indeks kurulamaz -> kolon_goc FALSE + ikiz SAYILIR + SILINMEZ.
    _c = _kt_goc_conn(ikiz=2)
    _once_satir = _kt_siparis_sayisi(_c)
    _kod, _cikti, _sonuc = _kt_goc_kos(_c, kolon_goc)
    dogrula("V77a IKIZ: indeks kurulamayinca kolon_goc FALSE (sessiz basari YOK)",
            _sonuc is False, _cikti[-300:])
    dogrula("V77b IKIZ: ikiz satir SAYILIR ve 'ELLE TEMIZLIK' hukmu basilir",
            "IKIZ SATIR ZATEN VAR" in _cikti and "2 FAZLA satir" in _cikti
            and "ELLE TEMIZLIK" in _cikti, _cikti[-400:])
    dogrula("V77c IKIZ: arac HICBIR SATIR SILMEDI (veri silme mimar/Okan karari)",
            _kt_siparis_sayisi(_c) == _once_satir == 3,
            "once=%s sonra=%s" % (_once_satir, _kt_siparis_sayisi(_c)))

    # V78 SIRA SERTLESTIRMESI: `--sema` indeks teyit edilmeden 'tamam' DEMEZ.
    _kod, _cikti, _ = _kt_sema_kos(_kt_goc_conn(ikiz=2))
    dogrula("V78a --sema: yarida kalmis gocte SIFIR-DISI cikar",
            _kod != 0 and "GOC YARIDA KALDI" in _cikti, "kod=%s" % _kod)
    dogrula("V78b --sema: yarida kalmis gocte 'goc TAMAM' DEMEZ",
            "goc TAMAM" not in _cikti, _cikti[-300:])
    _kod2, _cikti2, _ = _kt_sema_kos(_kt_goc_conn())
    dogrula("V78c --sema: temiz gocte exit 0 + 'goc TAMAM' (yanlis-pozitif nobeti)",
            _kod2 == 0 and "goc TAMAM" in _cikti2, "kod=%s" % _kod2)

    # V79 --durum: "kolon VAR ama indeks YOK" AYRI ve GORUNUR hal (eskiden YESIL).
    _kod, _cikti, _ = _kt_durum_kos(_kt_goc_conn())
    dogrula("V79a --durum: kolon VAR + indeks YOK -> exit 1 + 'YARIDA KALMIS GOC'",
            _kod == 1 and "YARIDA KALMIS GOC" in _cikti and _ad in _cikti,
            "kod=%s" % _kod)
    dogrula("V79b --durum: tek-yonlu kapi RISKI adiyla soylenir",
            "tek-yonlu kapi" in _cikti, _cikti[-300:])
    _kod, _cikti, _ = _kt_durum_kos(_kt_goc_conn(indeks=True))
    dogrula("V79c --durum: indeks kuruluyken SEMA ekseni TEMIZ (yanlis-pozitif nobeti)",
            _kod == 0 and "teyit (SEMA ekseni)" in _cikti, "kod=%s | %s" % (_kod, _cikti[-300:]))

    # V79d KOLON YOKKEN ESKI DAVRANIS: goc kosmadan once arac PATLAMAZ, kirmizi YAKMAZ.
    _c = _kt_goc_conn(kanal_kolonu=False)
    _kod, _cikti, _sonuc = _kt_goc_kos(_c, kolon_goc)
    _dkod, _dcikti, _ = _kt_durum_kos(_kt_goc_conn(kanal_kolonu=False))
    dogrula("V79d KOLON YOK: kolon_goc True + --durum exit 0 (eski davranis KORUNDU)",
            _sonuc is True and _dkod == 0 and "YARIDA KALMIS GOC" not in _dcikti,
            "goc=%s durum=%s" % (_sonuc, _dkod))
    # V79e — ⚠️ IDDIA 1 Agu 2026'da DEGISTI (siparis ucu dali birlestirildi). ESKI hali
    # "kolon_goc kosunca da siparisler indeksi UYGULANMAZ kalir" diyordu; o DOGRUYDU cunku
    # kanal/dis_no kolonlari BU DOSYADA TANIMLI DEGILDI. Artik GOC_KOLON_SIPARIS onlari
    # tasiyor -> kolon_goc AYNI kosumda kolonlari ekler ve indeksi kurar. Eski cumleyi
    # zorla yesil tutmak, gocun calistigini gizlemek olurdu. Iddia ikiye ayrildi:
    dogrula("V79e1 --durum (goc KOSMAMIS db): siparisler indeksi UYGULANMAZ — gurultu YOK",
            "%s=%s" % (_ad, IX_UYGULANMAZ) in _dcikti, _dcikti[-300:])
    dogrula("V79e2 kolon_goc: kolonlar YOKKEN bile TEK kosumda ALTER + indeks + DOGRULAMA",
            ("%s=%s" % (_ad, IX_KURULU)) in _cikti and _ad in _kt_indeks_adlari(_c),
            _cikti[-300:])

    # V79f SKIP DALI (kolonlari goc TASIMAYAN kayit): DDL DENENMEZ, kirmizi de YANMAZ.
    # NEDEN AYRI FIKSTUR: V79e2'den sonra gercek kayitlarin hepsinin kolonu goc listesinde
    # -> "kolonlar hazir degilse atla" dali URETIMDE ULASILMAZ hale geldi. Olculmeyen dal
    # cururur: yarin goc listesinde OLMAYAN bir kolona dayali kayit eklenirse (baska bir
    # dal, baska bir tablo) bu dal `--sema`nin tamamini dusurmemeli.
    _sahte = list(GOC_INDEKS) + [{
        "ad": "sahte_ix", "tablo": "siparisler", "yayin": False,
        "gerekli": ("hic_olmayan_kolon",), "benzersiz": False,
        "sql": "CREATE INDEX IF NOT EXISTS sahte_ix ON siparisler(hic_olmayan_kolon);"}]
    _c2 = _kt_goc_conn(kanal_kolonu=False)
    _g = globals()
    _eski_kayit = _g["GOC_INDEKS"]
    try:
        _g["GOC_INDEKS"] = _sahte
        _kod, _cikti2, _sonuc2 = _kt_goc_kos(_c2, kolon_goc)
    finally:
        _g["GOC_INDEKS"] = _eski_kayit
    dogrula("V79f SKIP: kolonu olmayan kayitta DDL denenmez, kolon_goc True kalir",
            _sonuc2 is True and "sahte_ix=%s" % IX_UYGULANMAZ in _cikti2
            and "sahte_ix" not in _kt_indeks_adlari(_c2), _cikti2[-300:])

    # V80 IKIZ TANIM NOBETI: her kaydin BEYAN ettigi `ad`, SQL'i KOSTURUNCA olusan indeks
    # adiyla AYNI olmali; `gerekli` de DDL'in dokundugu TUM kolonlari kapsamali. Beyan ile
    # uygulama ayrisirsa hal makinesi sonsuza dek "INDEKS-YOK" der (ya da tersi: kirmizi
    # yanmasi gereken hal yesil kalir). Metin AYRISTIRMASI YOK — SQL gercekten kosulur.
    import sqlite3 as _sq
    _beyan_ok, _kapsam_ok, _hata = True, True, ""
    for _ix in GOC_INDEKS:
        _t = _sq.connect(":memory:")
        _t.executescript("CREATE TABLE %s (%s);"
                         % (_ix["tablo"], ", ".join("%s TEXT" % k for k in _ix["gerekli"])))
        try:
            _t.executescript(_ix["sql"])
        except _sq.Error as e:
            _kapsam_ok, _hata = False, "%s: %s" % (_ix["ad"], e)
            continue
        _olusan = {r[0] for r in _t.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")}
        if _olusan != {_ix["ad"]}:
            _beyan_ok, _hata = False, "%s -> %s" % (_ix["ad"], sorted(_olusan))
    dogrula("V80a IKIZ TANIM: beyan edilen indeks adi = SQL'in FIILEN kurdugu ad",
            _beyan_ok, _hata)
    dogrula("V80b IKIZ TANIM: `gerekli` listesi DDL'in dokundugu kolonlari KAPSIYOR",
            _kapsam_ok, _hata)
    dogrula("V80c SOZLESME: YAYIN_INDEKS kayittan turer (ara-maliyet-kapisi.py bunu import "
            "eder) ve yalniz urunler indekslerini tasir",
            len(YAYIN_INDEKS) == 2 and all("urunler" in s for s in YAYIN_INDEKS))

    print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
    return 0 if kalan[0] == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sema", action="store_true", help="semayi kur")
    ap.add_argument("--kuru", action="store_true", help="yazmadan ne yapacagini soyle")
    ap.add_argument("--durum", action="store_true", help="D1 durumu (sayi + icerik ekseni)")
    ap.add_argument("--seq-normalize", action="store_true", dest="seq_normalize",
                    help="YALNIZ seq kolonunu urunler.json kanonik sirasindan tam sayi yaz")
    ap.add_argument("--hizli", action="store_true",
                    help="--durum ile: ICERIK eksenini ATLA (yalniz sayi; ~5 s ucuz)")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini",
                    help="OFFLINE kabul testi (sqlite fikstur; canli D1'e DOKUNMAZ)")
    ap.add_argument("--bayatlik", action="store_true",
                    help="YALNIZ olc: bu agac uzak main'in UCUNDA mi? (D1'e DOKUNMAZ; "
                         "UC -> 0, BAYAT/OLCULEMEDI -> 1). CI adimi bunu on-kosul yapar.")
    # KATALOG KAYNAGI (bkz. kaynak_coz ustundeki blok). BAYRAKSIZ DAVRANIS DEGISMEZ.
    ap.add_argument("--kaynak", default=None,
                    help="katalogu BU dosyadan oku (varsayilan: calisma agaci)")
    ap.add_argument("--head", action="store_true",
                    help="katalogu COMMIT'LI HEAD'den oku (git show HEAD:urunler.json) — "
                         "agactaki commit'lenmemis urunler senkrona GIRMEZ")
    # SILME KARANTINASI — bkz. tools/uzlastirici_karantina.py bas blogu.
    # BAYRAKSIZ DAVRANIS DEGISMEZ (pre-push kancasi / CI senkron adimi bayraksiz kosar).
    # Senkron kolunda: FAZLA id'ler ILK gozlemde SILINMEZ, damgaya yazilir; FARKLI bir
    # origin/main SHA'sindaki IKINCI gozlemde silinir; damga okunamazsa FAIL-CLOSED.
    # --durum kolunda: KARANTINADAKI id'ler drift HUKMUNDEN muaf tutulur (yalniz TEYIT
    # adimi icin — onarim ONCESI olcum bayraksiz kosar ve sapmayi TAM basar).
    ap.add_argument("--karantina-damgasi", dest="karantina_damgasi", default=None,
                    metavar="YOL",
                    help="D1'de FAZLA satirlarin silinmesini IKI GOZLEME yay (karantina "
                         "damgasi dosyasi). Damga okunamazsa SILME YAPILMAZ.")
    a = ap.parse_args()

    # 🔴 SIRA: kaynak, katalogu okuyan HER daldan (senkron / --durum / --kuru) ONCE
    # baglanir. Bayrak verilmediyse modul sabitine DOKUNULMAZ -> bugunku davranis BAYT
    # AYNI (kancalar buna bagli). Verildiyse GURULTULU basilir: sessiz kaynak degisimi,
    # kapatmaya calistigimiz hatanin ta kendisi olurdu.
    _kaynak_yolu, _kaynak_beyan, _kaynak_gecici = kaynak_coz(a.kaynak, a.head)
    if _kaynak_yolu:
        _adet = kaynak_dogrula(_kaynak_yolu)
        _yalniz_k, _yalniz_a, _hash_farki = kaynak_sapmasi(_kaynak_yolu)
        globals()["URUNLER"] = _kaynak_yolu
        print("KATALOG KAYNAGI: %s — %d benzersiz id" % (_kaynak_beyan, _adet))
        print("  calisma agacindan SAPMA: yalniz kaynakta %d · yalniz agacta %d · "
              "hash farki %d" % (len(_yalniz_k), len(_yalniz_a), len(_hash_farki)))
        for _etiket, _liste in (("agacta VAR kaynakta YOK (senkrona GIRMEYECEK)", _yalniz_a),
                                ("kaynakta VAR agacta YOK", _yalniz_k),
                                ("iki tarafta da VAR ama ICERIGI FARKLI", _hash_farki)):
            if _liste:
                print("   - %s: %d — %s%s"
                      % (_etiket, len(_liste), ", ".join(_liste[:5]),
                         " ..." if len(_liste) > 5 else ""))

    if a.kendini:
        sys.exit(kendini_test())

    if a.bayatlik:
        b = bayatlik_olc()
        print("bayatlik: %s — %s" % (b["durum"], b["sebep"]))
        print("  HEAD=%s · uzak %s ucu=%s"
              % (str(b["head"])[:12], UZAK_DAL, str(b["uzak"])[:12]))
        sys.exit(0 if b["durum"] == "UC" else 1)

    # ══ YAZICI KILIDI — kapsam CAGRI GRAFINDAN turetildi, ad deseninden DEGIL ══════
    # ([[kapsam-evrenini-cagri-grafindan-turet]]) `dosya_calistir()` = CANLI D1'e YAZAN
    # tek uc. main()'den ona giden TUM yollar:
    #   --sema           -> dosya_calistir(SEMA dosyasi) + kolon_goc() [ALTER/CREATE INDEX]
    #   --seq-normalize  -> seq_normalize() [UPDATE + geri alma UPDATE'leri]
    #   BAYRAKSIZ        -> diff-upsert (DELETE/INSERT/UPDATE) + senkron damgasi
    #                       + geri_okuma_dogrula() onarim yazmasi
    # OKUYUCU kollari (kilit ALINMAZ, cunku yaziciya bloklu olmamalilar):
    #   --durum · --kuru · --bayatlik · --kendini-test (ikisi zaten yukarida cikti)
    # 🔴 KILIT PENCERENIN TAMAMINI KAPSAR (D1 okumasi + diff plani + yazma + geri-okuma):
    # zarari veren sey tek bir DELETE degil, iki yazicinin OKU->PLANLA->YAZ penceresinin
    # IC ICE GECMESIDIR. Kilidi yazmanin hemen onune koymak arizayi KAPATMAZDI.
    if a.sema or a.seq_normalize or not (a.durum or a.kuru):
        yazici_kilidi_al(kol=("sema" if a.sema else
                              "seq-normalize" if a.seq_normalize else "senkron"))

    if a.seq_normalize:
        seq_normalize(urunleri_oku())
        return

    if a.sema:
        with open(SEMA, encoding="utf-8") as f:
            yaz, _ = dosya_calistir(f.read())
        # 🔴 SIRA SERTLESTIRMESI: burada "sema kuruldu" DENMEZ. Sema dosyasi uygulandi
        # demek goc BITTI demek DEGIL — kolon ALTER'lari ve INDEKSLER daha kosmadi ve
        # indeks DOGRULANMADAN "tamam" hukmu basmak, tek-yonlu kapi acan sessiz basaridir.
        print("sema dosyasi uygulandi (yazilan satir: %d) — goc HENUZ tamam degil" % yaz)
        if not kolon_goc():   # tablo zaten varsa CREATE atlanir -> eksikleri ALTER ekler
            sys.exit(
                "!! GOC YARIDA KALDI — 'sema kuruldu' DENMEZ.\n"
                "   Kolonlar eklenmis olabilir ama en az bir indeks KURULMADI. Kismi UNIQUE\n"
                "   indeks yoksa yaris KORUMASIZDIR: o pencerede olusacak ikiz satir indeksi\n"
                "   KALICI olarak kurulamaz hale getirir (--sema her kosumda duser).\n"
                "   Yukaridaki hal satirlarina bak; ikiz sayimi ve 3 adimli geri alma orada.")
        print("goc TAMAM: kolonlar + indeksler DOGRULANDI ✅")
        return

    if a.durum:
        r = sorgu("SELECT COUNT(*) AS n FROM urunler")
        n = ((r[0].get("results") or [{}])[0] or {}).get("n")
        r = sorgu("SELECT anahtar, deger FROM senkron")
        print("D1 urun sayisi:", n)
        for s in (r[0].get("results") or []):
            print("  %s = %s" % (s["anahtar"], s["deger"]))
        # FAIL-LOUD teyit: D1 satir sayisi urunler.json'daki BENZERSIZ id sayisiyla ORTUSMELI.
        # Eskiden --durum yalniz sayiyi BASIP exit 0 donerdi -> insan/hook/CI iki sayiyi ELLE
        # kiyaslamak zorundaydi ve kiyaslamayan "yesil" gorup gecerdi (Ege bayat katalog okur =
        # SESSIZ satis kaybi). Artik uyumsuzlukta exit 1: pre-push hook mesajinin ve CLAUDE.md'nin
        # isaret ettigi 'teyit' fiilen bir KAPI olur.
        urunler = urunleri_oku()
        benzersiz = len({u.get("id") for u in urunler if u.get("id")})
        print("urunler.json benzersiz id:", benzersiz)
        sorunlar = []
        if durum_uyumlu(n, benzersiz):
            print("teyit (SAYI ekseni): D1 == urunler.json benzersiz (%d) ✅" % benzersiz)
        else:
            sorunlar.append(
                "SAYI EKSENI DRIFT: D1=%s != urunler.json benzersiz=%d — senkron kacmis "
                "olabilir; Ege bayat katalog goruyor (yeni urunu ONEREMEZ)." % (n, benzersiz))

        # ── SEQ EKSENI — HASH DISI ama kanonik katalog sirasindan TURETILIR ─────────
        r_seq = sorgu("SELECT id, seq FROM urunler")
        seq_satirlar = (r_seq[0].get("results") or []) if r_seq else []
        seq_mevcut = {s["id"]: s.get("seq") for s in seq_satirlar}
        seq_kesirli, seq_sapma, seq_ornek = seq_sira_hali(urunler, seq_mevcut)
        print("seq ekseni: tam-sayi-olmayan=%d · kanonik-siradan-sapan=%d"
              % (len(seq_kesirli), len(seq_sapma)))
        for uid, deger, konum, canli_uid in seq_ornek:
            print("   - %s : canli seq=%r · beklenen konum=%d · o konumdaki canli id=%s"
                  % (uid, deger, konum, canli_uid))
        if seq_kesirli or seq_sapma:
            sorunlar.append(
                "SEQ EKSENI DRIFT: %d tam-sayi-olmayan + %d kanonik siradan sapan satir. "
                "Coz: python3 tools/d1-sync.py --seq-normalize"
                % (len(seq_kesirli), len(seq_sapma)))
        else:
            print("teyit (SEQ ekseni): seq tam sayi ve urunler.json sirasinda monoton ✅")

        # ── SEMA EKSENI (goc indeksleri) — "kolon VAR ama indeks YOK" AYRI HAL ────────
        # NEDEN BURADA: bu hal eskiden --durum'da GORUNMEZDI (sayi da icerik de tutar) ->
        # yarida kalmis bir goc YESIL raporlaniyordu. Maliyet: tablo basina 1 PRAGMA +
        # 1 sqlite_master SELECT'i (~birkac saniye); ikiz SAYIMI yalnizca BOZUK halde
        # kosar. --hizli bunu ATLAMAZ: sema hali sayi/icerik ekseninden BAGIMSIZ ve ucuz.
        hal = sema_hali()
        print("sema ekseni (goc indeksleri): "
              + " · ".join("%s=%s" % (h["ad"], h["hal"]) for h in hal))
        sema_sorun = sema_sorunlari(hal)
        if sema_sorun:
            for s in sema_sorun:
                print("   " + s)
            sorunlar.append(
                "SEMA EKSENI: YARIDA KALMIS GOC — %d indeks hali BOZUK (ayrinti yukarida). "
                "Coz: python3 tools/d1-sync.py --sema"
                % sum(1 for h in hal if h["hal"] in (IX_INDEKS_YOK, IX_KOLON_YARIM)))
        else:
            print("teyit (SEMA ekseni): beyan edilen goc indekslerinin hali temiz ✅")

        # ── TURETILMIS KOLON EKSENI (4.) — urun_hash'in KAPSAMADIGI kolonlar ───────
        # NEDEN VARSAYILAN ACIK: bu eksenin var olma sebebi, UC eksenin de YESIL yanarken
        # kolonun bayat kalabilmesiydi. Ayri bir bayrakta dursa merge-kapisi'nin zorunlu
        # D1 teyidi ayni korlukte kalirdi. --hizli BEYAN EDEREK atlar (sessiz atlama YOK).
        # MALIYET (olculdu, 20.850 urun): yerel turetim 18,0 s (model_kanon 12,9 · marka_arama
        # 4,9 · marka_kanon 0,2) + 1 SELECT. Karsiligi: kolon bayatligi artik SESSIZ degil.
        if a.hizli:
            print("!! TURETILMIS KOLON EKSENI ATLANDI (--hizli): konfigur/taban_fiyat/"
                  "marka_kanon/model_kanon/marka_arama urun_hash'in DISINDADIR -> ICERIK "
                  "ekseni onlari GORMEZ. Tam teyit: --hizli'siz kos.")
        else:
            t0 = time.time()
            tablo_kolonlari = kolonlari_oku("urunler")
            thal = turetilmis_eksen(urunler, tablo_kolonlari,
                                    turetilmis_mevcut(tablo_kolonlari))
            acik = kapsam_acigi(tablo_kolonlari)
            print("turetilmis kolon ekseni (urun_hash KAPSAMI DISI, %.2f s): "
                  % (time.time() - t0)
                  + " · ".join("%s=%s%s" % (h["kolon"], h["hal"],
                                            "" if h["sayi"] in (None, 0)
                                            else "(%d)" % h["sayi"]) for h in thal))
            turetilmis_sorun = turetilmis_sorunlari(thal, acik)
            if turetilmis_sorun:
                for s in turetilmis_sorun:
                    print("   " + s)
                sorunlar.append(
                    "TURETILMIS KOLON EKSENI: %d kolon BAYAT/OLCULEMEDI (ayrinti yukarida) "
                    "— SAYI, SEMA ve ICERIK eksenlerinin UCU DE bu hale KORDUR."
                    % len(turetilmis_sorun))
            else:
                print("teyit (TURETILMIS KOLON ekseni): %d hash-disi kolonun canli degeri "
                      "uretici govdenin bugun urettigiyle birebir ✅ "
                      "(eksen disi + GEREKCELI: %s)"
                      % (len(thal), ", ".join(sorted(EKSEN_DISI))))

        # ── ICERIK EKSENI (urun_hash) — VARSAYILAN ACIK ────────────────────────────
        # NEDEN VARSAYILAN: merge-kapisi'nin zorunlu D1 teyidi `d1-sync.py --durum` cagirir.
        # Eksen ayri bir bayrakta olsaydi (or. --derin) o kapi 31 Tem vakasina KOR kalmaya
        # devam ederdi (sayi tutuyor, icerik bayat). Maliyeti olculdu ve KABUL EDILEBILIR:
        # 15.163 satirin id+hash'i = tek SELECT, 5,2 s, rows_read 15.163, ~1,6 MB (hesap
        # Workers Paid; gunluk okuma kotasinin binde biri bile degil). Aceleci kullanim icin
        # --hizli BEYAN EDILEREK atlar ve neyin olculmedigini BASAR (sessiz atlama YOK).
        if a.hizli:
            print("!! ICERIK EKSENI ATLANDI (--hizli): ALAN guncellemesi satir SAYISINI "
                  "DEGISTIRMEZ -> sayi tutarken D1 icerigi BAYAT olabilir. Tam teyit: "
                  "--hizli'siz kos.")
        else:
            t0 = time.time()
            r = sorgu("SELECT id, hash FROM urunler")
            satirlar = (r[0].get("results") or []) if r else []
            okunan = ((r[0].get("meta") or {}).get("rows_read") or 0) if r else 0
            sure = time.time() - t0
            d1_hash = {s["id"]: s["hash"] for s in satirlar}
            uyusmaz, eksik, fazla = icerik_ekseni(urunler, d1_hash)
            print("icerik ekseni (urun_hash): %d D1 satiri | okunan satir: %d | %.2f s"
                  % (len(d1_hash), okunan, sure))
            # ── KARANTINA MUAFIYETI (YALNIZ --karantina-damgasi ile) ────────────────
            # NEDEN: karantina, ILK gozlemde silmeyi BILEREK ertelemektir. Teyit adimi
            # bu erteledigimiz satirlari "onarilamadi" sayarsa kosum HER karantina
            # aciliminda kirmizi yanar ve karantina fiilen geri alinir. Muafiyet YALNIZ
            # TEYIT adiminda (bayrakli cagride) uygulanir: onarim ONCESI olcum adimi
            # bayraksiz kosar, sapmayi TAM basar ve `d1-sapma-damgasi` alarm kanali
            # AYNEN kirmizi yakar -> sapma SUSTURULMUS OLMAZ.
            # FAIL-CLOSED: damga yoksa/bozuksa muaf kume BOStur (muafiyet KANIT ister).
            karantinali = []
            if a.karantina_damgasi:
                muaf = uzlastirici_karantina.karantinadaki(a.karantina_damgasi)
                karantinali = [u for u in fazla if u in muaf]
                fazla = [u for u in fazla if u not in muaf]
            print("  hash UYUSMAZ: %d | D1'de EKSIK: %d | D1'de FAZLA: %d%s"
                  % (len(uyusmaz), len(eksik), len(fazla),
                     (" (KARANTINADA, hukumden MUAF: %d)" % len(karantinali))
                     if karantinali else ""))
            for uid, b, v in uyusmaz[:10]:
                print("   - %s : urunler.json %s · D1 %s (D1 BAYAT)" % (uid, b, v))
            for uid in eksik[:10]:
                print("   - %s : D1'de YOK (Ege bu urunu ONEREMEZ)" % uid)
            for uid in fazla[:10]:
                print("   - %s : D1'de FAZLA (urunler.json'da yok)" % uid)
            for uid in karantinali[:10]:
                print("   - %s : D1'de FAZLA ama KARANTINADA (ilk gozlem — bu kosumda "
                      "SILINMEZ, ikinci gozlemde farkli origin/main SHA'si aranir)" % uid)
            if uyusmaz or eksik or fazla:
                sorunlar.append(
                    "ICERIK EKSENI DRIFT: %d bayat hash + %d eksik + %d fazla — SAYI tutsa "
                    "bile D1 icerigi urunler.json ile AYNI DEGIL (Ege bayat veri goruyor)."
                    % (len(uyusmaz), len(eksik), len(fazla)))
            else:
                print("teyit (ICERIK ekseni): %d urunun urun_hash'i D1 ile birebir ✅"
                      % len(d1_hash))

        if sorunlar:
            sys.exit("!! D1 SENKRON DRIFT:\n" + "\n".join("   " + s for s in sorunlar)
                     + "\n   Coz: python3 tools/d1-sync.py   (yerelde wrangler oturumu; "
                       "token gerekmez)")
        return

    urunler = urunleri_oku()
    # Tablo kolonlari TEK PRAGMA ile okunur (her kolon icin ayri sorgu = ayri wrangler
    # cagrisi = ~2,6 s bosuna).
    tablo_kolonlari = kolonlari_oku("urunler")
    # ZORUNLU kolonlar: yoksa satir_sql'in INSERT'i "no such column" ile duser ve parca
    # parca YARIM yazma birakir. FAIL-LOUD ve ONCEDEN: tek satirlik tani, yarim yazma yok.
    eksik_zorunlu = [k for k in ZORUNLU_KOLONLAR if k not in tablo_kolonlari]
    if eksik_zorunlu:
        sys.exit("!! D1 SEMASI ESKI — icerik upsert'i icin ZORUNLU kolon(lar) YOK: %s\n"
                 "   Bu kolonlar satir_sql'in INSERT listesindedir; olmadan HER upsert\n"
                 "   'no such column' ile duser (yarim yazma riski).\n"
                 "   Coz: python3 tools/d1-sync.py --sema   (once semayi kur, sonra senkron)"
                 % ", ".join(eksik_zorunlu))
    # KONFIGUR kolonu canli tabloda VAR mi? Yoksa (--sema henuz kosmadi) SELECT'e KONMAZ ve
    # konfigur senkronu ATLANIR — katalog senkronu (Ege'nin hayat damari) akmaya devam eder.
    konfigur_kolonu = "konfigur" in tablo_kolonlari
    # MARKA_KANON kolonu icin AYNI kosullu desen (bkz. d1_mevcut docstring'i): kolon canliya
    # ALTER ile girmeden bu kod push'lansa bile SELECT'e KONMAZ -> "no such column" ile
    # HERKESIN push'unu kiran sema SIRASI tuzagi yapisal olarak kapanir.
    marka_kanon_kolonu = "marka_kanon" in tablo_kolonlari
    # MODEL_KANON kolonu icin de AYNI kosullu desen (marka_kanon ile birebir): bu dal
    # ALTER'dan ONCE alinsa bile kolon SELECT'e KONMAZ, kimsenin push'u kirilmaz.
    model_kanon_kolonu = "model_kanon" in tablo_kolonlari
    # MARKA_ARAMA kolonu icin de AYNI kosullu desen (bu kolon canliya HENUZ girmedi; dal
    # ALTER'dan ONCE main'e alinsa bile senkron akmaya devam eder).
    marka_arama_kolonu = "marka_arama" in tablo_kolonlari
    (mevcut, mevcut_taban, mevcut_seq, mseq, mevcut_konfigur,
     mevcut_marka_kanon, mevcut_model_kanon, mevcut_marka_arama) = d1_mevcut(
        konfigur_kolonu, marka_kanon_kolonu, model_kanon_kolonu, marka_arama_kolonu)
    baskilar = baski_haritasi()
    tabanlar = taban_fiyat_haritasi()
    konfigurlar, konfigur_atlanan = konfigur_haritasi_d1(urunler)
    marka_kanonlar, marka_kanon_sebep = ({}, "kolon YOK")
    if marka_kanon_kolonu:
        marka_kanonlar, marka_kanon_sebep = marka_kanon_haritasi(urunler)
    model_kanonlar, model_kanon_sebep = ({}, "kolon YOK")
    if model_kanon_kolonu:
        model_kanonlar, model_kanon_sebep = model_kanon_haritasi(urunler)
    marka_aramalar, marka_arama_sebep = ({}, "kolon YOK")
    if marka_arama_kolonu:
        marka_aramalar, marka_arama_sebep = marka_arama_haritasi(urunler)
    # baski YETKISI = gizli kayit dosyasi bu ortamda VAR mi? YOKSA (CI) baski'ya HIC dokunma
    # (yoksa CI baski'yi D1'den silerdi). VARSA (yerel) baski'yi ayrica senkronla.
    baski_yetki = os.path.exists(KAYNAKLAR)
    print("urunler.json: %d urun | D1: %d urun | gizli baski kaydi: %d | baski yetki: %s | taban fiyat semasi: %d | konfigur semasi: %d"
          % (len(urunler), len(mevcut), len(baskilar),
             "EVET" if baski_yetki else "HAYIR (baski atlanir)", len(tabanlar),
             len(konfigurlar)))
    print("kanonik marka uyeligi (marka_kanon): %s"
          % ("%d urun" % len(marka_kanonlar) if marka_kanon_kolonu and not marka_kanon_sebep
             else "ATLANDI (%s)" % marka_kanon_sebep))
    print("kanonik model uyeligi (model_kanon): %s"
          % ("%d urun" % len(model_kanonlar) if model_kanon_kolonu and not model_kanon_sebep
             else "ATLANDI (%s)" % model_kanon_sebep))
    print("marka sorgusu eslesmesi (marka_arama): %s"
          % ("%d urun" % len(marka_aramalar) if marka_arama_kolonu and not marka_arama_sebep
             else "ATLANDI (%s)" % marka_arama_sebep))
    if not konfigur_kolonu:
        print("!! KONFIGUR KOLONU YOK — konfigur senkronu ATLANDI (katalog senkronu devam eder).\n"
              "   Coz: python3 tools/d1-sync.py --sema")
    if not marka_kanon_kolonu:
        print("!! MARKA_KANON KOLONU YOK — kanonik marka senkronu ATLANDI (katalog senkronu\n"
              "   devam eder; uc HENUZ bu kolonu okumamali).\n"
              "   Coz: python3 tools/d1-sync.py --sema")
    elif marka_kanon_sebep:
        # 🔴 TURETILEMEDI = "BOSALT" DEGIL "DOKUNMA". Bos harita ile plan kosulsaydi TUM
        # katalog '[]' olur ve uc her markayi bos gosterirdi (tek okuma hatasi -> katalog
        # capinda sessiz kayip). Bu yuzden SENKRON ATLANIR ve GURULTULU basilir.
        print("!! MARKA_KANON TURETILEMEDI — kolon OLDUGU GIBI birakildi (bayat > bos): %s\n"
              "   Coz: python3 tools/marka-invaryant-kapisi.py   (ayni tek kaynagi olcer)"
              % marka_kanon_sebep)
    if not model_kanon_kolonu:
        print("!! MODEL_KANON KOLONU YOK — kanonik model senkronu ATLANDI (katalog senkronu\n"
              "   devam eder; uc HENUZ bu kolonu okumamali).\n"
              "   Coz: python3 tools/d1-sync.py --sema")
    elif model_kanon_sebep:
        # 🔴 marka_kanon ile AYNI gerekce: TURETILEMEDI = "BOSALT" DEGIL "DOKUNMA".
        print("!! MODEL_KANON TURETILEMEDI — kolon OLDUGU GIBI birakildi (bayat > bos): %s\n"
              "   Coz: python3 tools/model-kanon-d1-test.py   (ayni tek kaynagi olcer)"
              % model_kanon_sebep)
    if not marka_arama_kolonu:
        print("!! MARKA_ARAMA KOLONU YOK — marka sorgusu senkronu ATLANDI (katalog senkronu\n"
              "   devam eder; uc `?q=<marka>` icin HENUZ bu kolonu okumamali).\n"
              "   Coz: python3 tools/d1-sync.py --sema")
    elif marka_arama_sebep:
        # 🔴 marka_kanon/model_kanon ile AYNI gerekce: TURETILEMEDI = "BOSALT" DEGIL "DOKUNMA".
        # Bos harita ile plan kosulsaydi TUM katalog '[]' olur ve uc HER marka sorgusuna
        # BOS donerdi (tek okuma hatasi -> katalog capinda sessiz kayip).
        print("!! MARKA_ARAMA TURETILEMEDI — kolon OLDUGU GIBI birakildi (bayat > bos): %s\n"
              "   Coz: python3 tools/marka-arama-d1-test.py   (ayni tek kaynagi olcer)"
              % marka_arama_sebep)
    if konfigur_atlanan:
        # GURULTU: bozuk konfigur SESSIZCE dusmesin. Kolon '' yapilir -> Worker fail-closed
        # 400 (WhatsApp); CI'daki bundle kapisi ayni veriyi zaten kirmizi yakar.
        print("!! BOZUK KONFIGUR (D1'de BOSALTILIR — urun kartla odenemez, WhatsApp'a duser): %d kayit"
              % len(konfigur_atlanan))
        for uid, sebep in konfigur_atlanan:
            print("   - %s: %s" % (uid, sebep))
        print("   Coz: python3 tools/konfigur-bundle-kapisi.py   (ayni veriyi dogrular)")

    # GERI-OKUMA IZI: plan fonksiyonlari SQL'i uretirken "hangi satirin hangi alani hangi
    # degere gelmeli" kaydini buraya birakir; yazmadan SONRA bu kayit D1'den geri okunup
    # dogrulanir (bkz. GERI_OKUMA_KOLONLARI bloku).
    izleme = []
    yeni, degisen, baski_guncelle, silinen, gorulen = diff_plan(
        urunler, mevcut, baskilar, baski_yetki, mseq, mevcut_seq, izleme)
    # TABAN FIYAT senkronu: baski'dan BAGIMSIZ + HASH'ten bagimsiz (git'te oldugu icin
    # yetki kapisi da yok — CI da yerel de ayni degeri gorur). Yeni urun taban_fiyat'i
    # INSERT DEFAULT 0 alir, bu UPDATE (ifade sirasinda INSERT'ten SONRA) fiyatini yazar.
    taban_guncelle = taban_plan(urunler, tabanlar, mevcut_taban, izleme)
    # KONFIGUR senkronu: taban_fiyat ile AYNI desen (hash'ten bagimsiz + hedefli UPDATE).
    # Kolon yoksa BOS liste (yukarida gurultulu basildi).
    konfigur_guncelle = (konfigur_plan(urunler, konfigurlar, mevcut_konfigur, izleme)
                         if konfigur_kolonu else [])
    # MARKA_KANON senkronu: konfigur ile AYNI desen. TURETILEMEDIYSE plan KOSULMAZ (bos
    # harita ile kosmak kolonu topluca '[]' yapardi — bkz. yukaridaki gurultulu uyari).
    marka_kanon_guncelle = (marka_kanon_plan(urunler, marka_kanonlar, mevcut_marka_kanon,
                                             izleme)
                            if (marka_kanon_kolonu and not marka_kanon_sebep) else [])
    # MODEL_KANON senkronu: marka_kanon ile AYNI desen ve AYNI fail-closed yonu.
    model_kanon_guncelle = (model_kanon_plan(urunler, model_kanonlar, mevcut_model_kanon,
                                             izleme)
                            if (model_kanon_kolonu and not model_kanon_sebep) else [])
    # MARKA_ARAMA senkronu: marka_kanon/model_kanon ile AYNI desen ve AYNI fail-closed yonu.
    marka_arama_guncelle = (marka_arama_plan(urunler, marka_aramalar, mevcut_marka_arama,
                                             izleme)
                            if (marka_arama_kolonu and not marka_arama_sebep) else [])
    print("yeni: %d | degisen: %d | baski-guncelle: %d | taban-guncelle: %d | konfigur-guncelle: %d | marka-kanon-guncelle: %d | model-kanon-guncelle: %d | marka-arama-guncelle: %d | silinen: %d | dokunulmayan: %d"
          % (len(yeni), len(degisen), len(baski_guncelle), len(taban_guncelle),
             len(konfigur_guncelle), len(marka_kanon_guncelle), len(model_kanon_guncelle),
             len(marka_arama_guncelle), len(silinen),
             len(gorulen) - len(yeni) - len(degisen)))

    if a.kuru:
        # KURU KOSUM: yazma da geri-okuma da YAPILMAZ (ikisi de D1'e cagri demektir).
        # Bayatlik da OLCULMEZ: kuru kosum planlama araci, hicbir seyi engellemez.
        print("(--kuru: hicbir sey yazilmadi, geri-okuma da yapilmadi)")
        return
    if (not yeni and not degisen and not baski_guncelle and not taban_guncelle
            and not konfigur_guncelle and not marka_kanon_guncelle
            and not model_kanon_guncelle and not marka_arama_guncelle and not silinen):
        # YAZACAK BIR SEY YOK -> bayatlik OLCULMEZ (maliyet 0). Yazmayan kosum zarar veremez.
        print("degisiklik yok — D1'e yazilmadi ✅")
        return

    # ══ BAYATLIK KAPISI — BAYAT AGAC D1'e HICBIR SEY YAZAMAZ ══════════════════════
    # KraL karari (31 Tem): kapi SILME ile sinirli KALMAZ, UPSERT'i de durdurur.
    # Gerekce: bayat upsert D1'e ESKI alan degerlerini YENI degerlerin ustune yazar —
    # silmeyle AYNI sessiz-bozulma sinifi, yalnizca daha az yikici (urunu kaldirmaz,
    # alani geriye alir). Bugun fiilen gozlendi ("3 bayat hash"). `--durum` icerik ekseni
    # bunu ancak BIR SONRAKI cagride gorur -> kacak yine SESSIZ kalirdi.
    # MALIYET: yalnizca YAZILACAK is varken olculur (medyan 0,81 s) ve yayin yolunda
    # DEGIL pre-push hook'unda oturur; yazacak bir sey yoksa hic olculmez.
    # FAIL-CLOSED: OLCULEMEDI de BAYAT gibi durdurur — "olcemedim" YESIL degildir.
    # YAYIN DURMAZ: hook her halukarda exit 0 doner, CI adimi `continue-on-error` —
    # bayat yazici yalnizca YAZMAZ ve yuksek sesle sifir-disi cikar.
    b = bayatlik_olc()
    print("bayatlik kapisi: %s — %s (HEAD=%s · uzak uc=%s)"
          % (b["durum"], b["sebep"], str(b["head"])[:12], str(b["uzak"])[:12]))
    if b["durum"] != "UC":
        sys.exit("\n".join(bayatlik_engel_metni(b, {
            "yeni": len(yeni), "degisen": len(degisen), "silinen": len(silinen),
            "baski": len(baski_guncelle), "taban": len(taban_guncelle),
            "konfigur": len(konfigur_guncelle),
            "marka_kanon": len(marka_kanon_guncelle),
            "model_kanon": len(model_kanon_guncelle),
            "marka_arama": len(marka_arama_guncelle)}, silinen)))

    # ══ SILME KARANTINASI — "D1'in ILERISI" ile "gercek oksuz" AYRI SORULARDIR ═════
    # OLCULDU 11 Agu 2026 (kosum 31532464176): bayatlik kapisi UC dedi (agac uzak main
    # ucundaydi) ve buna ragmen 37 MESRU satir silindi — cunku D1 git'ten ILERIDEYDI
    # (eszamanli partinin push'u henuz inmemisti). O yon bayatlik kapisinin ekseninde
    # YOK. Karantina o ekseni ZAMANLA ikame eder: bir id ancak FARKLI bir origin/main
    # SHA'sinda IKINCI kez FAZLA gorulurse silinir. Ayrinti + gerekce:
    # tools/uzlastirici_karantina.py bas blogu.
    karantina_olculemedi = False
    if a.karantina_damgasi:
        _fazla = list(silinen)
        _kk = uzlastirici_karantina.uygula(_fazla, a.karantina_damgasi, b["uzak"])
        silinen = list(_kk["silinecek"])
        # OLCULEMEDI hukmu YALNIZ silinecek aday VARKEN kosumu kirmiziya cevirir:
        # silme kolu bos bir kosumda okunamayan damga hicbir seyi engellememistir
        # (ve `uygula` o kosumda TAZE bir damga yazarak kendini onarir). Bayatlik
        # kapisinin "yalnizca SILINECEK id varken olcülür" ilkesiyle ayni yon.
        karantina_olculemedi = bool(_fazla) and _kk["hukum"] == "OLCULEMEDI"

    ifadeler = []
    for parca in [silinen[i:i + PARCA] for i in range(0, len(silinen), PARCA)]:
        ifadeler.append("DELETE FROM urunler WHERE id IN (%s);" % ",".join(q(i) for i in parca))
    # SIRA ONEMLI: yeni (INSERT) taban_guncelle/konfigur_guncelle'den (UPDATE) ONCE gelmeli ->
    # yeni urun once eklenir, sonra taban_fiyat'i ve konfigur'u yazilir (ayni --file'da sirali).
    ifadeler += (degisen + yeni + baski_guncelle + taban_guncelle + konfigur_guncelle
                 + marka_kanon_guncelle + model_kanon_guncelle + marka_arama_guncelle)

    top_yaz = 0
    for i in range(0, len(ifadeler), PARCA):
        yaz, _ = dosya_calistir("\n".join(ifadeler[i:i + PARCA]))
        top_yaz += yaz
        print("  parca %d/%d — yazilan satir: %d"
              % (i // PARCA + 1, (len(ifadeler) + PARCA - 1) // PARCA, yaz))

    yaz, _ = dosya_calistir(
        "INSERT INTO senkron (anahtar,deger) VALUES ('urun_sayisi',%s) "
        "ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger;" % q(str(len(gorulen)))
    )
    top_yaz += yaz

    print("TOPLAM yazilan satir (wrangler IDDIASI, asagida DOGRULANIR): %d" % top_yaz)
    if top_yaz > 100000:
        print("!! UYARI: bu tek calisma 100.000 satir yazma esigini asti.")

    # ── GERI-OKUMA DOGRULAMASI — "yazildi" IDDIASI burada KANITA cevrilir ────────────
    # Wrangler exit 0 + "N satir yazildi" TEK BASINA BASARI DEGILDIR (31 Tem: iddia dogru,
    # canli deger eski). Hata sinifi SESSIZ: site dogru gosterir, Ege bayat okur.
    beklenti = beklenti_kur(izleme, silinen)
    try:
        fark = geri_okuma_dogrula(beklenti, konfigur_kolonu, marka_kanon_kolonu,
                                  model_kanon_kolonu, marka_arama_kolonu)
    except SystemExit as e:
        # sorgu()/dosya_calistir() kendi icinde sys.exit ediyor olabilir. YUTMA: bu bir
        # "yesil" degil OLCULEMEDI'dir -> sifir-disi cikilir.
        sys.exit("!! GERI-OKUMA OLCULEMEDI (D1 sorgusu basarisiz) — yazma DOGRULANMADI, "
                 "'yazildi' iddiasi KANITSIZ.\n   %s" % (e.code,))
    except Exception as e:                                        # noqa: BLE001
        sys.exit("!! GERI-OKUMA OLCULEMEDI (%s) — yazma DOGRULANMADI, 'yazildi' iddiasi "
                 "KANITSIZ.\n   %s" % (type(e).__name__, e))
    if fark:
        satirlar = [
            "!! D1 YAZMA DOGRULANAMADI — iddia edilen yazma IKI DENEMEDE de D1'e islemedi.",
            "   Site urunu dogru gosterir ama Ege (WhatsApp botu) BAYAT veri gorur = sessiz",
            "   satis kaybi. Uyusmayan alan sayisi: %d" % len(fark)]
        for uid, kolon, b, v in fark[:20]:
            satirlar.append("   - %s . %s : beklenen %r · bulunan %r" % (uid, kolon, b, v))
        if len(fark) > 20:
            satirlar.append("   ... +%d alan daha" % (len(fark) - 20))
        satirlar.append("   Coz: python3 tools/d1-sync.py   (tekrar kos) — surerse ES ZAMANLI "
                        "ikinci bir senkron (CI adimi / baska oturumun pre-push hook'u) BAYAT "
                        "bir urunler.json ile ustune yaziyor olabilir.")
        sys.exit("\n".join(satirlar))

    # ── KARANTINA OLCULEMEDI -> SIFIR-DISI CIKIS (fail-closed, EN SONDA) ────────────
    # EKSIK/degisen kollari (ekleme + guncelleme) YAPILDI ve geri-okumayla dogrulandi;
    # bu satira gelmis olmak onun kanitidir. YALNIZ silme kolu olculemedi. "Olcemedim"
    # bu depoda YESIL DEGILDIR: sifir-disi cikilir, uzlastirici-onarim.py bunu imzadan
    # tanir (rc 4) ve YENIDEN DENEMEZ — tekrar okumak damgayi var etmez.
    if karantina_olculemedi:
        sys.exit(
            "%s hukum bu kosumda verilemedi.\n"
            "   Upsert kolu (EKSIK + bayat hash) UYGULANDI ve dogrulandi; SILME kolu "
            "fail-closed KAPALI kaldi.\n"
            "   Coz: karantina damgasi artifact'inin (`%s`) indirilmesini onar "
            "(actions: read izni / saklama suresi)."
            % (uzlastirici_karantina.OKUNAMADI_IMZASI, uzlastirici_karantina.DAMGA_ADI))


if __name__ == "__main__":
    main()
