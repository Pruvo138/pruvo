#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urunler.json -> Cloudflare D1 (katalog + arama indeksi). FAZ 1.

  python3 tools/d1-sync.py --sema     # semayi kur (bir kez / degisince)
  python3 tools/d1-sync.py            # DIFF-UPSERT: sadece degisen/yeni/silinen
  python3 tools/d1-sync.py --kuru     # hicbir sey yazma, ne yapacagini soyle
  python3 tools/d1-sync.py --durum    # SAYI ekseni + ICERIK ekseni (urun_hash) teyidi
  python3 tools/d1-sync.py --durum --hizli   # yalniz SAYI ekseni (icerik ekseni ATLANIR)
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

*** NEDEN DIFF-UPSERT SART ***
D1 ucretsiz katmanda GUNDE 100.000 SATIR YAZMA siniri var (okuma 100M, depolama 5 GB
— onlar bol). Her push'ta tam rebuild yazilirsa 50k urunde 2 rebuild limiti bitirir,
D1 hata dondurmeye baslar ve ARAMA COKER. Bu yuzden ürünün icerik ozeti (hash)
tutulur; ozeti degismeyen urune DOKUNULMAZ. Gunde ~600 yeni urun = ~600 yazma.

*** SIRA (seq) TUZAGI ***
Yeni urun urunler.json'un BASINA eklenir; dizi indeksini sira yapsaydik her eklemede
TUM urunlerin sirasi kayar, hepsi "degismis" gorunur ve her push tam rebuild olurdu
(yukaridaki limit tam da bu yuzden patlardi). Onun yerine her urune ilk eklendiginde
SABIT bir seq verilir; ORDER BY seq DESC = katalog sirasi (en yeni ustte).
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arama

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


def wrangler_hata_tanisi(ham):
    """Wrangler hata metnini siniflandir: auth, gecici veya bilinmeyen.

    code 10000 Wrangler/Cloudflare ciktisindan gelir; d1-sync bu kodu uretmez. Ancak
    tek bir 10000 cevabi gecici olabildigi icin wrangler() auth sonucunu da yeniden
    dener. Yalniz tum denemeler ayni sinifta basarisizsa kalici auth tanisi konur.
    """
    kucuk = ham.lower()
    gecici_isaretler = (
        "timed out", "timeout", "etimedout", "econnreset", "econnrefused",
        "enotfound", "getaddrinfo", "socket hang up", "network error",
        "network connectivity", "fetch failed", "service unavailable",
        "bad gateway", "gateway timeout", "too many requests", "rate limit",
        "code: 429", "status: 429", "code: 500", "status: 500",
        "code: 502", "status: 502", "code: 503", "status: 503",
        "code: 504", "status: 504",
    )
    if any(isaret in kucuk for isaret in gecici_isaretler):
        return "gecici"
    if re.search(r"\bcode\s*:\s*10000\b", kucuk) or "authentication error" in kucuk:
        return "auth"
    return None


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

        tani = wrangler_hata_tanisi(ham)
        if p.returncode == 0 or tani not in ("auth", "gecici") or deneme == 2:
            break
        time.sleep(0.25)

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

    i = p.stdout.find("[")
    if i == -1:
        sys.exit("wrangler cikti vermedi:\n" + ham[-2000:])
    try:
        return json.loads(p.stdout[i:])
    except json.JSONDecodeError:
        sys.exit("wrangler ciktisi cozulemedi:\n" + ham[-2000:])


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


def urunleri_oku():
    with open(URUNLER, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, list):
        sys.exit("urunler.json dizi degil")
    return d


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
                           text=True, timeout=zaman_asimi)
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

    sayilar: {"yeni","degisen","silinen","baski","taban","konfigur"} -> engellenen is.
    silinen_ornek: engellenen DELETE id'leri (en yikici kalem; ornekleri basilir).
    """
    toplam = sum(sayilar.values())
    satirlar = [
        "!! BAYATLIK KAPISI: BU AGACTAN D1'e HICBIR SEY YAZILMADI (durum: %s)." % b["durum"],
        "   Sebep: %s" % b["sebep"],
        "   HEAD=%s · uzak %s ucu=%s"
        % (str(b["head"])[:12], UZAK_DAL, str(b["uzak"])[:12]),
        "   Engellenen is (toplam %d): yeni %d | degisen %d | silinen %d | baski %d | "
        "taban %d | konfigur %d"
        % (toplam, sayilar.get("yeni", 0), sayilar.get("degisen", 0),
           sayilar.get("silinen", 0), sayilar.get("baski", 0),
           sayilar.get("taban", 0), sayilar.get("konfigur", 0)),
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


def kolon_var_mi(tablo, kolon):
    """Canli tabloda kolon VAR mi? (PRAGMA — satir YAZMAZ, tek ucuz sorgu.)

    NEDEN GEREKLI: yeni kolon canli D1'e ancak `--sema` (ALTER) kosuldugunda girer. Kolonu
    kosulsuz SELECT'e koyarsak, --sema HENUZ kosmadan calisan bir senkron (or. pre-push
    hook'u) "no such column" ile duser ve TUM katalog senkronu olur -> Ege bayat katalog
    okur (sessiz satis kaybi). Kolon yoksa yalniz KONFIGUR senkronu atlanir, katalog akmaya
    devam eder; atlama GURULTULU basilir (asagida)."""
    r = sorgu("PRAGMA table_info(%s)" % tablo)
    return kolon in {s["name"] for s in (r[0].get("results") or [])}


def d1_mevcut(konfigur_kolonu=True):
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
    --sema kosmus olmali (canli uygulama sirasi RAPOR-MIMARA.md'de). konfigur kolonu icin bu
    sart YUMUSATILDI: kolon yoksa cagiran konfigur_kolonu=False verir ve SELECT onu istemez
    (bkz. kolon_var_mi) -> --sema unutulsa bile katalog senkronu AKMAYA DEVAM EDER."""
    kolonlar = "id, hash, baski, taban_fiyat, seq" + (", konfigur" if konfigur_kolonu else "")
    r = sorgu("SELECT %s FROM urunler" % kolonlar)
    satirlar = (r[0].get("results") or []) if r else []
    mevcut = {s["id"]: (s["hash"], s.get("baski") or "") for s in satirlar}
    mevcut_taban = {s["id"]: int(s.get("taban_fiyat") or 0) for s in satirlar}
    mevcut_seq = {s["id"]: s["seq"] for s in satirlar if s.get("seq") is not None}
    mevcut_konfigur = ({s["id"]: (s.get("konfigur") or "") for s in satirlar}
                       if konfigur_kolonu else {})
    r2 = sorgu("SELECT COALESCE(MAX(seq), 0) AS m FROM urunler")
    mseq = ((r2[0].get("results") or [{}])[0] or {}).get("m") or 0
    return mevcut, mevcut_taban, mevcut_seq, int(mseq), mevcut_konfigur


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
]

# ON CONFLICT (UPDATE) sirasinda GUNCELLENEN kolonlar.
# "baski" BILEREK YOK: baski yalnizca gizli .urun-kaynaklari.json'da (CI'da yok).
# Content upsert'i baski'yi da yazsaydi CI HER kosumda baski'yi '' YAPARDI (D1'den
# SILERDI — 2026-07-18: canlida 7381 satirin hepsinde baski='' bulundu, sebep buydu).
# baski AYRI senkronla yonetilir (baski_senkron_sql + main) ve SADECE dosyasi olan
# ortam (yerel) yazar. INSERT VALUES'ta baski VAR (yeni satir onu alir); sadece
# CONFLICT/UPDATE yolu baski'ya dokunmaz.
KOLONLAR = [
    "hash", "baslik", "kategori", "marka", "fiyat", "gorsel", "parametrik", "hs",
    "aciklama", "ege", "hs_baslik", "hs_baslik_kok", "hs_govde", "hs_govde_kok",
]


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
def sema_senkron_sql(kolon, uid, deger):
    """Tek urun icin SADECE verilen METIN SEMA kolonunu gunceller (content'e/hs'e DOKUNMAZ ->
    hash ayni, FTS tetigi (WHEN old.hs<>new.hs) CALISMAZ, ek FTS satiri yazmaz).
    `kolon` SABIT bir tanimlayicidir (cagiran kod verir, kullanici girdisi DEGIL)."""
    return "UPDATE urunler SET %s=%s WHERE id=%s;" % (kolon, q(deger), q(uid))


def sema_plan(kolon, urunler, hedefler, mevcut, izleme=None):
    """SAF plan (canli D1'e DOKUNMAZ -> birim testi burayi cagirir). Doner: hedefli UPDATE'ler.
    - hedefler = {id: kanonik JSON}  urunler.json'dan turetilen ISTENEN deger
    - mevcut   = {id: metin}         D1'deki mevcut deger (yeni urun icin yok -> '')

    KURAL: her urun icin HEDEF = hedefler.get(id, '') ; hedef D1'dekinden FARKLIYSA 1 UPDATE.
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
        hedef = hedefler.get(uid, "")
        if hedef != (mevcut.get(uid, "") or ""):
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
    Varsa, bu "yeni" id GERCEKTE mid-array'dir -> katalogun tepesine DEGIL, en yakin
    HEAD-tarafi komsusunun seq'i ile en yakin TAIL-tarafi komsusunun seq'i ARASINDA bir
    FLOAT ara-deger alir (seq INTEGER sutunu REAL degeri de tasir — SQLite dinamik
    tipleme). Boylece HICBIR BASKA SATIRA DOKUNULMAZ / RENUMBERING GEREKMEZ, tek satirlik
    hedefli bir deger yeter (D1 gunluk yazma butcesini asmaz)."""
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
                # MID-ARRAY yeni id (rename / araya sikisma) -> gercek komsulari arasinda
                # FLOAT ara-deger. Hicbir baska satira DOKUNMAZ, renumbering YOK.
                atanan = (taban + ust) / 2.0
                if atanan <= taban:  # asiri-bolunmus (pratikte olmaz) -> guvenli dusme
                    atanan = ust - 1e-6
            taban = atanan
            sql = satir_sql(u, atanan, arama.haystack(u), h, baski)  # INSERT baski'yi da yazar
            yeni.append(sql)
            # YENI satir: INSERT VALUES baski'yi DA yazar -> beklentiye baski GIRER.
            izle(izleme, uid, sql, {"hash": h, "baslik": u.get("baslik") or "",
                                    "kategori": u.get("kategori") or "", "baski": baski})
        else:
            if eski_h != h:
                sql = satir_sql(u, 0, arama.haystack(u), h, baski)  # seq ON CONFLICT'te korunur
                degisen.append(sql)
                # DEGISEN satir: ON CONFLICT yolu KOLONLAR'i gunceller, baski BILEREK DISARIDA
                # (bkz. KOLONLAR yorumu) -> beklentiye baski GIRMEZ, yoksa CI'da her degisen
                # urun sahte "baski uyusmazligi" verirdi (YANLIS-POZITIF = herkesin push'u kirilir).
                izle(izleme, uid, sql, {"hash": h, "baslik": u.get("baslik") or "",
                                        "kategori": u.get("kategori") or ""})
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


# ATOMIK YAYIN indeksleri — ALTER'lardan SONRA kosmak ZORUNDA (yoksa "no such column:
# yayinda"; olculdu 31 Tem canli D1'de: d1-sema.sql icine konunca --sema TAMAMEN dustu,
# cunku o dosya kolon gocunden ONCE uygulanir ve tablo zaten var oldugu icin CREATE TABLE
# IF NOT EXISTS atlanir). IF NOT EXISTS -> idempotent.
YAYIN_INDEKS = [
    "CREATE INDEX IF NOT EXISTS urunler_yayin     ON urunler(yayinda, seq DESC);",
    "CREATE INDEX IF NOT EXISTS urunler_yayin_kat ON urunler(yayinda, kategori, seq DESC);",
]


def kolon_goc():
    """Eksik kolonlari ekle. Idempotent: SQLite'ta 'ADD COLUMN IF NOT EXISTS' yok,
    o yuzden once table_info'ya bakilir (kor ALTER ikinci calismada patlardi)."""
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
    # Kolonlar TAMAMLANDIKTAN sonra atomik yayin indeksleri (kolon yokken CREATE INDEX
    # tum --sema kosumunu dusururdu — olculdu, bkz. YAYIN_INDEKS yorumu).
    if kolon_var_mi("urunler", "yayinda"):
        dosya_calistir("\n".join(YAYIN_INDEKS))
        print("atomik yayin indeksleri kuruldu (urunler_yayin, urunler_yayin_kat)")


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
    ]
    # ATOMIK YAYIN: YENI satir DAIMA taslak (yayinda=0) girer. Kolon SQL'de ACIKCA
    # yazilir (DEFAULT'a guvenilmez): DEFAULT sonradan degistirilirse ya da tablo baska
    # bir yolla kurulursa yeni urun SESSIZCE yayinda dogar ve pencere geri gelirdi.
    # ON CONFLICT/UPDATE yolunda yayinda YOKTUR (KOLONLAR listesi) -> mevcut yayinda=1
    # satirin icerigi degisse de urun Ege'den KAYBOLMAZ.
    return (
        "INSERT INTO urunler (id,hash,seq,baslik,kategori,marka,fiyat,gorsel,parametrik,hs,"
        "aciklama,ege,hs_baslik,hs_baslik_kok,hs_govde,hs_govde_kok,baski,yayinda) VALUES ("
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
GERI_OKUMA_KOLONLARI = ["hash", "baslik", "kategori", "baski", "taban_fiyat"]

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


def geri_oku(idler, konfigur_kolonu):
    """Yazilan id'leri D1'den geri oku. Doner: ({id: satir}, olcum)."""
    kolonlar = ["id"] + GERI_OKUMA_KOLONLARI + (["konfigur"] if konfigur_kolonu else [])
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


def geri_okuma_dogrula(beklenti, konfigur_kolonu):
    """Yazilan satirlari geri okur, ALAN DEGERLERINI karsilastirir; uyusmazlikta ayni
    ifadeleri BIR KEZ yeniden uygular ve TEKRAR okur. Doner: kalan fark listesi (bos = OK).
    SONSUZ DONGU YOK — tam 2 tur, ucuncu deneme yapilmaz."""
    if not beklenti:
        print("geri-okuma: yazilan satir yok — dogrulanacak sey yok")
        return []
    bulunan, olcum = geri_oku(list(beklenti), konfigur_kolonu)
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
    bulunan2, olcum2 = geri_oku(kotu, konfigur_kolonu)
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
  release_id TEXT NOT NULL DEFAULT ''
);
CREATE TABLE senkron (anahtar TEXT PRIMARY KEY, deger TEXT NOT NULL);
"""


def _kt_urun(uid, kategori="Oyun/Hobi", baslik=None):
    return {"id": uid, "baslik": baslik or ("Urun %s" % uid), "kategori": kategori,
            "marka": [], "fiyat": "100 TL",
            "gorseller": ["https://media.example/%s-1.jpg" % uid],
            "aciklama": "aciklama %s" % uid}


def _kt_kos(conn, urunler, argv, dusur=None, oku_patlat=False, tabanlar=None,
            bayatlik="UC", kok=None):
    """d1-sync'i OFFLINE kosar. Doner: (cikis_kodu, cikti_metni, sayac).
    dusur(sql, sayac) -> True ise o yazma UYGULANMAZ ama BASARI raporlanir (sessiz ariza).
    oku_patlat -> geri-okuma sorgusu istisna atar (OLCULEMEDI yolu).
    bayatlik -> bayatlik_olc()'un dondurecegi durum ("UC"/"BAYAT"/"OLCULEMEDI"); AG YOK.
       sayac["bayatlik"] kac kez olculdugunu tutar (maliyet ekseni: yazma yoksa 0 olmali).
    kok -> verilirse GERCEK bayatlik_olc() o git agacinda kosar (stub YOK) ve KOK oraya
       ayarlanir; uctan uca (git soyagaci + senkron) olcum icin."""
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
    g = globals()
    eski = {k: g[k] for k in ("sorgu", "dosya_calistir", "URUNLER", "KAYNAKLAR",
                              "JEN_URUN_DIR", "taban_fiyat_haritasi", "bayatlik_olc",
                              "KOK")}
    eski_argv = sys.argv
    tampon = io.StringIO()
    try:
        g["sorgu"] = _sorgu
        g["dosya_calistir"] = _dosya_calistir
        if kok is None:
            g["bayatlik_olc"] = _bayatlik  # AG YOK: kapi kararini fikstur verir
        else:
            g["KOK"] = kok                 # GERCEK kapi, GERCEK git (sentetik depo)
        g["URUNLER"] = yol
        g["KAYNAKLAR"] = os.path.join(tempfile.gettempdir(), "pruvo-kt-yok.json")
        g["JEN_URUN_DIR"] = os.path.join(tempfile.gettempdir(), "pruvo-kt-yok-dizin")
        if tabanlar is not None:
            g["taban_fiyat_haritasi"] = lambda: dict(tabanlar)
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
        for k, v in eski.items():
            g[k] = v
        sys.argv = eski_argv
        os.unlink(yol)
    return kod, tampon.getvalue(), sayac


def _kt_baglan(yayinda_default=0):
    """yayinda_default: TABLO SEMASINDAKI varsayilan. 1 vermek SEMA DRIFT'ini taklit eder
    (biri DEFAULT'u degistirdi / tablo baska yoldan kuruldu). Yeni satirin taslak dogmasi
    SEMANIN DEFAULT'una DEGIL, INSERT'in acikca yazdigi degere bagli olmali."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_KT_SEMA.replace("yayinda INTEGER NOT NULL DEFAULT 0",
                                        "yayinda INTEGER NOT NULL DEFAULT %d" % yayinda_default))
    return conn


def _kt_deger(conn, uid, kolon):
    r = conn.execute("SELECT %s AS v FROM urunler WHERE id=?" % kolon, (uid,)).fetchone()
    return None if r is None else r["v"]


def _kt_git(yol, *args):
    """Sentetik depoda git kos (kimlik + imza ayarlari sabit; kullanicinin ayarina bagli
    KALMAZ -> CI'da da yerelde de ayni davranir)."""
    komut = ["git", "-c", "user.email=kt@pruvo.test", "-c", "user.name=KT",
             "-c", "commit.gpgsign=false", "-c", "protocol.file.allow=always",
             "-C", yol] + list(args)
    p = subprocess.run(komut, capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip()


def _kt_depo_kur(tmp, urun_sayisi=1):
    """(uzak_bare, yerel) — main dali olan bir uzak + ona bagli bir yerel checkout."""
    uzak = os.path.join(tmp, "uzak.git")
    yerel = os.path.join(tmp, "yerel")
    os.makedirs(uzak)
    _kt_git(tmp, "init", "--bare", "--quiet", uzak)
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
    dogrula("V7 IZ: yeni urun -> hash+baslik+kategori+baski beklentisi kaydedilir",
            len(iz) == 1 and set(iz[0]["alanlar"]) == {"hash", "baslik", "kategori", "baski"}
            and iz[0]["alanlar"]["kategori"] == "Tamirat", iz)
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
    kod, cikti, _ = _kt_kos(conn12, urunler, ["--durum"])
    dogrula("V31 DURUM POZITIF: sayi + icerik ekseni uyumlu -> exit 0",
            kod == 0 and "teyit (ICERIK ekseni)" in cikti, (kod, cikti[-400:]))
    conn12.execute("UPDATE urunler SET hash='BAYATHASH' WHERE id='a'")
    kod, cikti, _ = _kt_kos(conn12, urunler, ["--durum"])
    dogrula("V32 DURUM NEGATIF (31 TEM SINIFI): SAYI TUTUYOR ama hash bayat -> sifir-disi",
            kod != 0 and "ICERIK EKSENI DRIFT" in cikti and "teyit (SAYI ekseni)" in cikti,
            (kod, cikti[-500:]))
    kod, cikti, _ = _kt_kos(conn12, urunler, ["--durum", "--hizli"])
    dogrula("V33 DURUM --hizli: icerik ekseni BEYAN EDILEREK atlanir -> exit 0 + uyari",
            kod == 0 and "ICERIK EKSENI ATLANDI" in cikti, (kod, cikti[-400:]))

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

    print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
    return 0 if kalan[0] == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sema", action="store_true", help="semayi kur")
    ap.add_argument("--kuru", action="store_true", help="yazmadan ne yapacagini soyle")
    ap.add_argument("--durum", action="store_true", help="D1 durumu (sayi + icerik ekseni)")
    ap.add_argument("--hizli", action="store_true",
                    help="--durum ile: ICERIK eksenini ATLA (yalniz sayi; ~5 s ucuz)")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini",
                    help="OFFLINE kabul testi (sqlite fikstur; canli D1'e DOKUNMAZ)")
    ap.add_argument("--bayatlik", action="store_true",
                    help="YALNIZ olc: bu agac uzak main'in UCUNDA mi? (D1'e DOKUNMAZ; "
                         "UC -> 0, BAYAT/OLCULEMEDI -> 1). CI adimi bunu on-kosul yapar.")
    a = ap.parse_args()

    if a.kendini:
        sys.exit(kendini_test())

    if a.bayatlik:
        b = bayatlik_olc()
        print("bayatlik: %s — %s" % (b["durum"], b["sebep"]))
        print("  HEAD=%s · uzak %s ucu=%s"
              % (str(b["head"])[:12], UZAK_DAL, str(b["uzak"])[:12]))
        sys.exit(0 if b["durum"] == "UC" else 1)

    if a.sema:
        with open(SEMA, encoding="utf-8") as f:
            yaz, _ = dosya_calistir(f.read())
        print("sema kuruldu (yazilan satir: %d)" % yaz)
        kolon_goc()   # tablo zaten varsa CREATE atlanir -> yeni kolonlari ALTER ekler
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
            print("  hash UYUSMAZ: %d | D1'de EKSIK: %d | D1'de FAZLA: %d"
                  % (len(uyusmaz), len(eksik), len(fazla)))
            for uid, b, v in uyusmaz[:10]:
                print("   - %s : urunler.json %s · D1 %s (D1 BAYAT)" % (uid, b, v))
            for uid in eksik[:10]:
                print("   - %s : D1'de YOK (Ege bu urunu ONEREMEZ)" % uid)
            for uid in fazla[:10]:
                print("   - %s : D1'de FAZLA (urunler.json'da yok)" % uid)
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
    # KONFIGUR kolonu canli tabloda VAR mi? Yoksa (--sema henuz kosmadi) SELECT'e KONMAZ ve
    # konfigur senkronu ATLANIR — katalog senkronu (Ege'nin hayat damari) akmaya devam eder.
    konfigur_kolonu = kolon_var_mi("urunler", "konfigur")
    mevcut, mevcut_taban, mevcut_seq, mseq, mevcut_konfigur = d1_mevcut(konfigur_kolonu)
    baskilar = baski_haritasi()
    tabanlar = taban_fiyat_haritasi()
    konfigurlar, konfigur_atlanan = konfigur_haritasi_d1(urunler)
    # baski YETKISI = gizli kayit dosyasi bu ortamda VAR mi? YOKSA (CI) baski'ya HIC dokunma
    # (yoksa CI baski'yi D1'den silerdi). VARSA (yerel) baski'yi ayrica senkronla.
    baski_yetki = os.path.exists(KAYNAKLAR)
    print("urunler.json: %d urun | D1: %d urun | gizli baski kaydi: %d | baski yetki: %s | taban fiyat semasi: %d | konfigur semasi: %d"
          % (len(urunler), len(mevcut), len(baskilar),
             "EVET" if baski_yetki else "HAYIR (baski atlanir)", len(tabanlar),
             len(konfigurlar)))
    if not konfigur_kolonu:
        print("!! KONFIGUR KOLONU YOK — konfigur senkronu ATLANDI (katalog senkronu devam eder).\n"
              "   Coz: python3 tools/d1-sync.py --sema")
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
    print("yeni: %d | degisen: %d | baski-guncelle: %d | taban-guncelle: %d | konfigur-guncelle: %d | silinen: %d | dokunulmayan: %d"
          % (len(yeni), len(degisen), len(baski_guncelle), len(taban_guncelle),
             len(konfigur_guncelle), len(silinen),
             len(gorulen) - len(yeni) - len(degisen)))

    if a.kuru:
        # KURU KOSUM: yazma da geri-okuma da YAPILMAZ (ikisi de D1'e cagri demektir).
        # Bayatlik da OLCULMEZ: kuru kosum planlama araci, hicbir seyi engellemez.
        print("(--kuru: hicbir sey yazilmadi, geri-okuma da yapilmadi)")
        return
    if (not yeni and not degisen and not baski_guncelle and not taban_guncelle
            and not konfigur_guncelle and not silinen):
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
            "konfigur": len(konfigur_guncelle)}, silinen)))

    ifadeler = []
    for parca in [silinen[i:i + PARCA] for i in range(0, len(silinen), PARCA)]:
        ifadeler.append("DELETE FROM urunler WHERE id IN (%s);" % ",".join(q(i) for i in parca))
    # SIRA ONEMLI: yeni (INSERT) taban_guncelle/konfigur_guncelle'den (UPDATE) ONCE gelmeli ->
    # yeni urun once eklenir, sonra taban_fiyat'i ve konfigur'u yazilir (ayni --file'da sirali).
    ifadeler += degisen + yeni + baski_guncelle + taban_guncelle + konfigur_guncelle

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
        fark = geri_okuma_dogrula(beklenti, konfigur_kolonu)
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


if __name__ == "__main__":
    main()
