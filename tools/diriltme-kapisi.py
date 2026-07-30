#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diriltme-kapisi.py — SILINMIS BIR URUNUN SESSIZCE GERI GELMESINE karsi nobetci.

🔴 DOKTRIN (bu dosyanin varlik sebebi, tek cumle):
    `urunler.json` cakismasi SATIR-DUZEYI MERGE ile COZULMEZ; urun verisi tasinacaksa
    TEMIZ DAL + YALNIZ KOD DOSYALARI, veri `tools/duzelt.py` ile.

OLCULEN GERCEK OLAY (30 Tem): bir mühendis dali main'e alinirken `urunler.json`'un
SATIR-DUZEYI 3-YOLLU MERGE'i, main'in BILEREK sildigi 2 kaydi GERI DIRILTTI. Biri
YASAK TUR (olcekli maket/model), biri dogrudan emirle silinmisti. Ustune
`tools/urunler-guard.py` YAPISI GEREGI "HEAD'de olup calisma agacindan silinmis urunu
geri ekler" oldugu icin elle yapilan duzeltme IKI KEZ ezildi (15068 -> 15070).
Push'tan hemen once ELLE yakalandi — bu sinifi goren HICBIR NOBETCI YOKTU. Bir dahaki
sefere yakalanmazsa yasak-tur urun CANLIYA doner ve hicbir yerde alarm calmaz.

⚠️ Neden mevcut kapilar bunu GORMEZ:
  * `urunler-guard.py` ekseni "HEAD'e gore kim degisti" — dirilen urun HEAD'de VARDI
    (merge sonrasi), guard onu KORUNACAK sayar; tam ters yone calisir.
  * `mukerrer-kontrol.py` ekseni "ayni id iki kez" — dirilen urun TEK kayittir.
  * `d1-sync.py --durum` ekseni "sayi tutuyor mu" — 15070 == 15070, YESIL yanar.
Yani sayi tutar, sema tutar, mukerrer yok; TEK sapan sey silinmis olmasi gereken bir
urunun geri gelmis olmasidir.

--------------------------------------------------------------------------------
IDDIA (TEK): <taban> durumunda GECMISTE SILINMIS olan bir urun id'si <yeni> durumunda
GERI GELMISSE -> KIRMIZI. YENI id eklemek SERBESTTIR (MaCiT'in normal ekleme akisi
kapiyi HIC tetiklemez, bkz. V9/V10 yanlis-pozitif nobetleri).

SILINMIS ID KUMESI GIT GECMISINDEN TURETILIR (ELLE LISTE TUTULMAZ — bayatlar):
    git log -U0 -p --first-parent --format='C %H' <taban> -- urunler.json
  * `+` satirlarinda gorulen HER id = "bu id bir zamanlar katalogda VARDI" (ever_seen).
    Dosyanin ilk hali de bir `+` blogu oldugu icin baslangic icerigi de kapsanir.
  * silinmis = ever_seen - <taban>'daki id'ler.
  * `--first-parent`: bu depoda tek yayin hatti main'dir; merge commit'in diffi ILK
    ebeveynine gore alinir -> bir dalda yapilip merge edilen silme de gorunur, ayni
    diff IKI KEZ sayilmaz. Siralama/yeniden dizme sonucu ETKILEMEZ: kume islemi
    ("hic gorulmus mu" - "su an var mi") satir tasimalarindan BAGIMSIZDIR.

📏 OLCULEN MALIYET + BEYAN EDILEN SINIR (ornekleme YOK — sessiz ornekleme YASAK):
  30 Tem, ana depo, TAM gecmis: 801 commit `urunler.json`'a dokunmus, uretilen diff
  ~68 MB, 44.262 id satiri, sure 4,2 s. Turetilen kume: ever_seen 16.058 · HEAD 15.068
  · **SILINMIS 990**. (Ornek: `1980-renault-re-20-turbo-model-araba`,
  `2021-hyundai-tucson-model-araba` — tam da YASAK olcekli-maket sinifi.)
  SINIR: kume TAM gecmisten turetilir, ornekleme/kisaltma YOKTUR. Cikti satir satir
  akitilir (68 MB bellege alinmaz). `--azami-sure` ile bir tavan verilebilir; tavan
  asilirsa kapi YESIL demez, **OLCULEMEDI** (rc 2) der.

🔴 FAIL-CLOSED — "olculemedi" ASLA yesil sayilmaz (rc 2):
  * depo SIG (shallow) klonlanmissa gecmis YOKTUR -> OLCULEMEDI. CI'da bu KRITIKTIR:
    `actions/checkout@v4` VARSAYILAN OLARAK `fetch-depth: 1` (sig) klonlar. deploy.yml'de
    checkout adimina `fetch-depth: 0` KONULMUSTUR; biri onu kaldirirsa bu kapi SESSIZCE
    yesile donmez, KIRMIZI/OLCULEMEDI ile bagirir.
  * `git` cagrilamiyorsa / `urunler.json` ayristirilamiyorsa -> OLCULEMEDI.
  * id satiri BEKLENMEYEN girintide gorulurse -> OLCULEMEDI. Olculen invariant (30 Tem,
    TAM gecmis): `urunler.json`'daki her `"id"` satiri ya 2 ya 4 bosluk girintilidir ve
    DAIMA ust duzey urun anahtaridir; ic ice (konfigur/parametre) bir `"id"` anahtari
    gecmisin TAMAMINDA YOKTUR. Kapi bunu VARSAYMAZ, her koşumda OLCER: sapma gorurse
    kendi ayikcalayicisina guvenmez ve OLCULEMEDI der.

MESRU GERI-EKLEME NASIL AYIRT EDILIR (kodda: `izin_oku` + `kapi`):
  Beyan dosyasi **`.diriltme-izin.json`** (depo KOKU, IZLENEN) — `{"<id>": "gerekce"}`.
  Bir id ancak burada BOS OLMAYAN bir gerekceyle beyan edilmisse dirilebilir.
  ⚠️ NEDEN `.urunler-sil-izin.json` DEGIL: `duzelt.py --sil`in urettigi o manifest
  (ve `.urunler-duzelt-izin.json`) `.gitignore`DADIR -> CI checkout'unda YOKTUR; onu
  dayanak yapmak kapiyi CI'da HIC calismaz hale getirirdi. Beyan IZLENEN olmak
  zorundadir ki inceleme (review) ve gecmis onu gorsun.
  Gerekcesiz/bos beyan KABUL EDILMEZ (V6). Beyan edilmis ama artik dirilme uretmeyen
  girisler BILGI olarak basilir, KIRMIZI YAPILMAZ: bir diriltme merge edildikten sonra
  girdi dogal olarak "bayat"lasir ve onu kirmizi saymak KALICI SAHTE-KIRMIZI uretirdi
  (bu kapi deploy.yml'de continue-on-error'SUZ kosar; tek sahte-kirmizi TUM EKIBIN
  yayinini durdurur — [[kapi-kapsam-eksen-secimi]]).

🔴 SALT-OKUNUR: bu kapi `urunler.json`'a ASLA yazmaz, hicbir repo dosyasina dokunmaz.
  Kabul testi sentetik gecici git depolari kurar; canli veriye dokunmaz ve koşum
  oncesi/sonrasi `git status --porcelain` + `urunler.json` sha256 esitligini KENDI olcer
  (V11). Kapiya bir yazma sokan mutasyon bu vakayi KIRMIZI yakar.

KULLANIM:
    python3 tools/diriltme-kapisi.py                  # CI/commit kipi: HEAD^1 -> HEAD
    python3 tools/diriltme-kapisi.py --calisma-agaci  # HEAD -> calisma agaci (push oncesi)
    python3 tools/diriltme-kapisi.py --taban main --yeni <dal>   # merge oncesi on-test
    python3 tools/diriltme-kapisi.py --kendini-test   # POZITIF+NEGATIF kabul (ag YOK)

CIKIS KODLARI: 0 = YESIL · 1 = KIRMIZI (diriltme) · 2 = OLCULEMEDI (gecmis okunamadi).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
URUNLER_ADI = "urunler.json"
IZIN_ADI = ".diriltme-izin.json"

YESIL, KIRMIZI, OLCULEMEDI = 0, 1, 2

# TEK KAYNAK: hem gecmis taramasi hem girinti nobeti bu deseni kullanir.
# Grup 1 = +/- · Grup 2 = girinti · Grup 3 = id.
ID_SATIRI = re.compile(r'^([-+])([ \t]*)"id"\s*:\s*"([^"]*)"')
# 30 Tem'de TAM gecmiste OLCULEN girintiler (ust duzey urun anahtari; eski cag 2, yeni cag 4).
BEKLENEN_GIRINTI = ("  ", "    ")


class Olculemedi(Exception):
    """Gecmis/dosya okunamadi -> yesil SAYILMAZ, rc 2."""


# ---------------------------------------------------------------- git yardimcilari
def _git(depo, *args, **kw):
    p = subprocess.run(["git", "-C", depo, *args], capture_output=True, text=True,
                       errors="replace", **kw)
    return p.returncode, p.stdout, p.stderr


def depo_kok(verilen=None):
    """Depo koku: verilen > bu dosyanin dizini > cwd. Kapinin BIR KOPYASI depo disina
    (or. scratchpad'e) konup mutasyon icin kosuldugunda ikinci dal devreye girer."""
    if verilen:
        return os.path.abspath(verilen)
    for aday in (TOOLS, os.getcwd()):
        rc, out, _ = _git(aday, "rev-parse", "--show-toplevel")
        if rc == 0 and out.strip():
            return out.strip()
    raise Olculemedi("git deposu bulunamadi (ne %s ne cwd bir git agaci)" % TOOLS)


def sig_mi(depo):
    rc, out, _ = _git(depo, "rev-parse", "--is-shallow-repository")
    if rc != 0:
        raise Olculemedi("`git rev-parse --is-shallow-repository` calismadi")
    return out.strip() == "true"


def rev_var_mi(depo, rev):
    rc, _o, _e = _git(depo, "rev-parse", "--verify", "--quiet", rev + "^{commit}")
    return rc == 0


def idler_revden(depo, rev):
    """<rev>:urunler.json icindeki id kumesi."""
    rc, out, err = _git(depo, "show", rev + ":" + URUNLER_ADI)
    if rc != 0:
        raise Olculemedi("`git show %s:%s` okunamadi: %s" % (rev, URUNLER_ADI, err.strip()[:200]))
    return idler_metinden(out, "%s:%s" % (rev, URUNLER_ADI))


def idler_dosyadan(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return idler_metinden(f.read(), yol)
    except OSError as e:
        raise Olculemedi("%s okunamadi: %s" % (yol, e))


def idler_metinden(metin, etiket):
    try:
        govde = json.loads(metin)
    except ValueError as e:
        raise Olculemedi("%s ayristirilamadi (bozuk JSON): %s" % (etiket, e))
    if not isinstance(govde, list):
        raise Olculemedi("%s bir DIZI degil (%s)" % (etiket, type(govde).__name__))
    out = set()
    for u in govde:
        if isinstance(u, dict) and isinstance(u.get("id"), str) and u["id"]:
            out.add(u["id"])
    return out


# ---------------------------------------------------------------- gecmis turetme
def gecmiste_gorulen(depo, rev, azami_sure=None):
    """(ever_seen, olcumler) — <rev>'in BIRINCI-EBEVEYN gecmisinde `+` satirinda gorulen
    TUM urun id'leri. Cikti AKITILIR (68 MB bellege alinmaz).

    FAIL-CLOSED: beklenmeyen girintide bir `"id"` satiri gorulurse Olculemedi."""
    komut = ["git", "-C", depo, "log", "-U0", "-p", "--no-color", "--first-parent",
             "--format=%H", rev, "--", URUNLER_ADI]
    t0 = time.time()
    try:
        p = subprocess.Popen(komut, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, errors="replace", bufsize=1024 * 1024)
    except OSError as e:
        raise Olculemedi("git log calistirilamadi: %s" % e)
    ever = set()
    cikan = set()
    satir_sayisi = 0
    bayt = 0
    try:
        for satir in p.stdout:
            bayt += len(satir)
            m = ID_SATIRI.match(satir)
            if not m:
                continue
            if m.group(2) not in BEKLENEN_GIRINTI:
                p.kill()
                raise Olculemedi(
                    "BEKLENMEYEN id GIRINTISI (%r) — bu kapinin ayikcalayicisi ust duzey "
                    "urun anahtarini tanimiyor olabilir; kendi olcumune GUVENMEZ. Satir: %s"
                    % (m.group(2), satir.strip()[:120]))
            satir_sayisi += 1
            if m.group(1) == "+":
                ever.add(m.group(3))
            else:
                cikan.add(m.group(3))
            if azami_sure and (time.time() - t0) > azami_sure:
                p.kill()
                raise Olculemedi(
                    "gecmis taramasi %.0f s tavanini asti — kume EKSIK olurdu, sessiz "
                    "ornekleme YAPILMAZ" % azami_sure)
    finally:
        try:
            p.stdout.close()
        except Exception:
            pass
        hata = p.stderr.read() if p.stderr else ""
        try:
            p.stderr.close()
        except Exception:
            pass
        p.wait()
    if p.returncode not in (0, -9):
        raise Olculemedi("git log basarisiz (rc=%s): %s" % (p.returncode, hata.strip()[:200]))
    return ever, {
        "sure_sn": round(time.time() - t0, 2),
        "diff_mb": round(bayt / 1e6, 1),
        "id_satiri": satir_sayisi,
        "ever_seen": len(ever),
        "cikan": len(cikan),
    }


# ---------------------------------------------------------------- beyan
def izin_oku(depo):
    """(izinli_idler, bilgi_satirlari, hatalar) — `.diriltme-izin.json`.

    FAIL-CLOSED: dosya BOZUKSA hata (yesil sayilmaz). BOS GEREKCELI giris KABUL EDILMEZ."""
    yol = os.path.join(depo, IZIN_ADI)
    if not os.path.exists(yol):
        return set(), [], []
    try:
        with open(yol, encoding="utf-8") as f:
            govde = json.load(f)
    except (OSError, ValueError) as e:
        return set(), [], ["%s okunamadi/ayristirilamadi: %s" % (IZIN_ADI, e)]
    if not isinstance(govde, dict):
        return set(), [], ["%s bir SOZLUK degil ({id: gerekce} bekleniyor)" % IZIN_ADI]
    izinli, bilgi, hatalar = set(), [], []
    for uid, gerekce in sorted(govde.items()):
        if not isinstance(gerekce, str) or not gerekce.strip():
            hatalar.append("%s GEREKCESIZ giris: %r -> beyan gerekce ISTER "
                           "(bos gerekce muafiyet SAYILMAZ)" % (IZIN_ADI, uid))
            continue
        izinli.add(uid)
        bilgi.append("%s — %s" % (uid, gerekce.strip()[:110]))
    return izinli, bilgi, hatalar


# ---------------------------------------------------------------- KAPI (SAF karar)
def dirilenleri_bul(silinmis, yeni_idler, izinli):
    """SAF karar: (dirilen, beyanli) — ag/dosya YOK. Mutasyon hedefi tam BURASI."""
    geri_gelen = silinmis & yeni_idler
    dirilen = sorted(geri_gelen - izinli)
    beyanli = sorted(geri_gelen & izinli)
    return dirilen, beyanli


def kapi(depo=None, taban=None, yeni_rev=None, yeni_dosya=None, azami_sure=None):
    """(durum, satirlar, olcumler). durum: "YESIL" | "KIRMIZI" | "OLCULEMEDI"."""
    satirlar = []
    olcumler = {}
    try:
        depo = depo_kok(depo)
        if sig_mi(depo):
            raise Olculemedi(
                "depo SIG (shallow) klonlanmis -> silinmis-id kumesi TURETILEMEZ. "
                "CI'da cozum: actions/checkout adimina `fetch-depth: 0`. "
                "Bu durum YESIL SAYILMAZ.")

        # --- taban / yeni cozumleme
        if yeni_dosya is None and yeni_rev is None:
            if not rev_var_mi(depo, "HEAD"):
                raise Olculemedi("HEAD yok (bos depo)")
            yeni_rev = "HEAD"
            if taban is None:
                taban = "HEAD^1" if rev_var_mi(depo, "HEAD^1") else None
        if taban is None and yeni_dosya is not None:
            taban = "HEAD"
        if taban is None:
            satirlar.append(("BILGI", "-", "tabanin ebeveyni YOK (ilk commit) -> "
                                           "karsilastirilacak onceki durum yok"))
            return "YESIL", satirlar, olcumler
        if not rev_var_mi(depo, taban):
            raise Olculemedi("taban revizyonu cozulemedi: %s" % taban)

        taban_idler = idler_revden(depo, taban)
        yeni_idler = (idler_dosyadan(yeni_dosya) if yeni_dosya is not None
                      else idler_revden(depo, yeni_rev))
        ever, olcumler = gecmiste_gorulen(depo, taban, azami_sure)
        silinmis = ever - taban_idler

        izinli, izin_bilgi, izin_hatalari = izin_oku(depo)
        olcumler.update({
            "depo": depo, "taban": taban,
            "yeni": yeni_dosya if yeni_dosya is not None else yeni_rev,
            "taban_id": len(taban_idler), "yeni_id": len(yeni_idler),
            "silinmis": len(silinmis), "beyan": len(izinli),
        })
        if izin_hatalari:
            for h in izin_hatalari:
                satirlar.append(("BEYAN", "-", h))

        dirilen, beyanli = dirilenleri_bul(silinmis, yeni_idler, izinli)
        olcumler["yeni_eklenen"] = len(yeni_idler - taban_idler)
        olcumler["dirilen"] = len(dirilen)
        olcumler["beyanli_dirilme"] = len(beyanli)

        for uid in dirilen:
            satirlar.append(("DIRILTME", uid,
                             "GECMISTE SILINMIS bu id geri geldi — satir-duzeyi merge "
                             "kurbani olabilir; yasak-tur urun canliya donebilir"))
        for uid in beyanli:
            satirlar.append(("BEYANLI", uid, "diriltme %s'de gerekceyle beyan edilmis"
                             % IZIN_ADI))
        for b in izin_bilgi:
            if b.split(" — ")[0] not in beyanli:
                satirlar.append(("BILGI", "-", "%s girisi su an dirilme uretmiyor "
                                               "(bayat olabilir): %s" % (IZIN_ADI, b)))
        if dirilen or izin_hatalari:
            return "KIRMIZI", satirlar, olcumler
        return "YESIL", satirlar, olcumler
    except Olculemedi as e:
        satirlar.append(("OLCULEMEDI", "-", str(e)))
        return "OLCULEMEDI", satirlar, olcumler


DURUM_KOD = {"YESIL": YESIL, "KIRMIZI": KIRMIZI, "OLCULEMEDI": OLCULEMEDI}


def rapor(durum, satirlar, olcumler):
    print("DIRILTME KAPISI — silinmis urun geri geldi mi")
    if olcumler:
        print("  depo / taban / yeni    : %s | %s -> %s" % (
            olcumler.get("depo", "?"), olcumler.get("taban", "?"), olcumler.get("yeni", "?")))
        print("  gecmis taramasi        : %s id satiri, %s MB diff, %s s "
              "(TAM gecmis — ornekleme YOK)" % (
                  olcumler.get("id_satiri", "?"), olcumler.get("diff_mb", "?"),
                  olcumler.get("sure_sn", "?")))
        print("  bir zamanlar var olan  : %s id" % olcumler.get("ever_seen", "?"))
        print("  tabanda duran          : %s id" % olcumler.get("taban_id", "?"))
        print("  SILINMIS (yasak kume)  : %s id" % olcumler.get("silinmis", "?"))
        print("  yenide duran           : %s id  (yeni eklenen: %s — SERBEST)" % (
            olcumler.get("yeni_id", "?"), olcumler.get("yeni_eklenen", "?")))
        print("  beyan (%s)  : %s giris" % (IZIN_ADI, olcumler.get("beyan", 0)))
    for sinif, uid, aciklama in satirlar:
        print("    %-10s %-38s %s" % (sinif, uid, aciklama))
    print("----------------------------------------------------------------------")
    if durum == "YESIL":
        print("SONUC: YESIL ✅  — gecmiste silinmis hicbir urun geri gelmemis "
              "(yeni id eklemek SERBEST).")
    elif durum == "KIRMIZI":
        print("SONUC: KIRMIZI ❌  — SILINMIS URUN(LER) DIRILMIS.")
        print("  DOKTRIN: urunler.json cakismasi satir-duzeyi merge ile COZULMEZ.")
        print("  COZUM: 1) dali main'e MERGE ETME; yalniz KOD dosyalarini tasi")
        print("         2) urun verisi degisecekse: python3 tools/duzelt.py ...")
        print("         3) geri-ekleme GERCEKTEN mesruysa %s'a id + GEREKCE yaz" % IZIN_ADI)
    else:
        print("SONUC: ⚪ OLCULEMEDI — silinmis-id kumesi turetilemedi; parite "
              "KANITLANMADI (sessiz yesil verilmez).")
    return DURUM_KOD[durum]


# ---------------------------------------------------------------- kendini test
def _kos(depo, *args, **kw):
    rc, out, err = _git(depo, *args, **kw)
    if rc != 0:
        raise RuntimeError("git %s -> rc=%d %s" % (" ".join(args), rc, err))
    return out


def _urun(uid, kategori="Marin"):
    return {"id": uid, "kategori": kategori, "marka": [], "baslik": uid,
            "aciklama": "test", "fiyat": "100 TL",
            "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}


def _yaz(depo, idler, girinti=4):
    """<girinti> = urun ANAHTARLARININ girintisi (gercek dosyada: yeni cag 4, eski cag 2).
    4 -> `json.dump(indent=2)` (dizi ogesi 2, anahtar 4 bosluk) = BUGUNKU bicim.
    2 -> dizi ogeleri sutun 0'da, anahtarlar 2 bosluk = ESKI cag bicimi."""
    yol = os.path.join(depo, URUNLER_ADI)
    urunler = [_urun(u) for u in idler]
    with open(yol, "w", encoding="utf-8") as f:
        if girinti == 4:
            json.dump(urunler, f, ensure_ascii=False, indent=2)
        else:
            govde = ",\n".join(json.dumps(u, ensure_ascii=False, indent=2) for u in urunler)
            f.write("[\n" + govde + "\n]")
        f.write("\n")


def _commit(depo, mesaj):
    _kos(depo, "add", "-A")
    _kos(depo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", mesaj)


def _depo_kur(kok, ad):
    depo = os.path.join(kok, ad)
    os.makedirs(depo)
    _kos(depo, "init", "-q", "-b", "main")
    return depo


def kendini_test():
    """POZITIF + NEGATIF vakalar. Her iddia icin iki yon de olculur (yalniz pozitif =
    olu nobetci). Ag YOK; sentetik gecici git depolari, CANLI VERIYE DOKUNULMAZ."""
    ham = ["DIRILTME KAPISI — KENDINI TEST (offline, sentetik git depolari)"]
    kirmizi = 0

    def iddia(ad, kosul, detay=""):
        nonlocal kirmizi
        if kosul:
            ham.append("    ✅ " + ad)
        else:
            kirmizi += 1
            ham.append("    ❌ " + ad + (" — " + str(detay) if detay else ""))

    with tempfile.TemporaryDirectory(prefix="pruvo-diriltme-") as kok:
        # ---- ORTAK TARIH: a,b,c eklendi -> b BILEREK silindi (yasak tur) -> d eklendi
        def temel_depo(ad, girinti=4):
            d = _depo_kur(kok, ad)
            _yaz(d, ["a", "b", "c"], girinti)
            _commit(d, "ilk katalog")
            _yaz(d, ["a", "c"], girinti)
            _commit(d, "b silindi (yasak tur: olcekli maket)")
            _yaz(d, ["a", "c", "d"], girinti)
            _commit(d, "d eklendi")
            return d

        # V0 — kume turetmenin KENDISI dogru mu (nobetin dayanagi)
        d0 = temel_depo("v0")
        ever, olc = gecmiste_gorulen(d0, "HEAD")
        taban = idler_revden(d0, "HEAD")
        iddia("V0 silinmis kume gecmisten TURETILIYOR (elle liste YOK): {b}",
              (ever - taban) == {"b"}, sorted(ever - taban))
        iddia("V0b ever_seen dosyanin ILK halini de kapsiyor (a,b,c,d)",
              ever == {"a", "b", "c", "d"}, sorted(ever))

        # V1 POZITIF — dirilen id -> KIRMIZI
        d1 = temel_depo("v1")
        _yaz(d1, ["a", "c", "d", "b"])
        _commit(d1, "b geri geldi (diriltme)")
        du, sa, _ = kapi(depo=d1)
        iddia("V1 [POZITIF] dirilen id -> KIRMIZI (rc 1)",
              du == "KIRMIZI" and DURUM_KOD[du] == 1, du)
        iddia("V1b teshis id'yi ADIYLA soyluyor",
              any(s[1] == "b" and s[0] == "DIRILTME" for s in sa), sa)

        # V2 NEGATIF — YENI id eklemek SERBEST
        d2 = temel_depo("v2")
        _yaz(d2, ["a", "c", "d", "e"])
        _commit(d2, "e eklendi (yeni id)")
        du, _s, _o = kapi(depo=d2)
        iddia("V2 [NEGATIF] YENI id eklenmesi -> YESIL", du == "YESIL", du)

        # V3 NEGATIF — hic degismemis dosya
        d3 = temel_depo("v3")
        with open(os.path.join(d3, "README.md"), "w") as f:
            f.write("x\n")
        _commit(d3, "urunler.json'a dokunmayan commit")
        du, _s, _o = kapi(depo=d3)
        iddia("V3 [NEGATIF] urunler.json hic degismemis -> YESIL", du == "YESIL", du)

        # V4 NEGATIF — silinmis SILINMIS kaldi
        d4 = temel_depo("v4")
        _yaz(d4, ["a", "c", "d", "e", "f"])
        _commit(d4, "iki yeni urun")
        du, _s, o4 = kapi(depo=d4)
        iddia("V4 [NEGATIF] silinmis id geri gelmedi -> YESIL", du == "YESIL", du)
        iddia("V4b yasak kume BOSALMADI (nobetin dayanagi hala duruyor)",
              o4.get("silinmis") == 1, o4.get("silinmis"))

        # V5 NEGATIF — BEYANLI mesru geri-ekleme (duzelt.py yolu)
        d5 = temel_depo("v5")
        _yaz(d5, ["a", "c", "d", "b"])
        with open(os.path.join(d5, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"b": "lisansi duzeltildi, KraL onayiyla geri alindi"}, f)
        _commit(d5, "b beyanla geri alindi")
        du, sa, _o = kapi(depo=d5)
        iddia("V5 [NEGATIF] gerekceli beyan -> YESIL (mesru geri-ekleme yolu)",
              du == "YESIL", du)
        iddia("V5b beyanli dirilme raporda GORUNUR (sessiz gecmez)",
              any(s[0] == "BEYANLI" and s[1] == "b" for s in sa), sa)

        # V6 POZITIF — GEREKCESIZ beyan kacis deligi OLMAZ
        d6 = temel_depo("v6")
        _yaz(d6, ["a", "c", "d", "b"])
        with open(os.path.join(d6, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"b": "   "}, f)
        _commit(d6, "b bos gerekceyle")
        du, sa, _o = kapi(depo=d6)
        iddia("V6 [POZITIF] BOS GEREKCELI beyan muafiyet SAYILMAZ -> KIRMIZI",
              du == "KIRMIZI", du)
        iddia("V6b tani gerekcesizligi soyluyor",
              any(s[0] == "BEYAN" for s in sa), sa)

        # V7 FAIL-CLOSED — SIG (shallow) depo
        d7 = temel_depo("v7")
        _yaz(d7, ["a", "c", "d", "b"])
        _commit(d7, "b geri geldi")
        sig = os.path.join(kok, "v7-sig")
        _kos(kok, "clone", "-q", "--depth", "1", "file://" + d7, sig)
        du, sa, _o = kapi(depo=sig)
        iddia("V7 [FAIL-CLOSED] SIG depo -> OLCULEMEDI (rc 2), ASLA yesil",
              du == "OLCULEMEDI" and DURUM_KOD[du] == 2, du)
        iddia("V7b tani `fetch-depth: 0` cozumunu soyluyor",
              any("fetch-depth" in s[2] for s in sa), sa)

        # V8 POZITIF — OLCULEN 30 TEM VAKASININ BIREBIR YENIDEN KURULUMU:
        # dal main'i kendi icine birlestirir ve urunler.json cakismasini "kendi tarafini
        # koruyarak" cozer; sonra o dal main'e alinir -> main'in BILEREK sildigi b GERI GELIR
        # (ve main'in ekledigi d SESSIZCE DUSER). Hicbir sayi/sema kapisi bunu gormez.
        d8 = _depo_kur(kok, "v8")
        _yaz(d8, ["a", "b", "c"])
        _commit(d8, "ilk katalog")
        _kos(d8, "checkout", "-q", "-b", "muhendis")
        _yaz(d8, ["a", "b", "c", "x"])
        _commit(d8, "dalda x eklendi")
        _kos(d8, "checkout", "-q", "main")
        _yaz(d8, ["a", "c"])
        _commit(d8, "b silindi (yasak tur: olcekli maket)")
        _yaz(d8, ["a", "c", "d"])
        _commit(d8, "d eklendi")
        _kos(d8, "checkout", "-q", "muhendis")
        _git(d8, "-c", "user.email=t@t", "-c", "user.name=t", "merge", "main")  # cakisir
        _yaz(d8, ["a", "b", "c", "x"])                       # "iki taraf da korunarak" cozum
        _commit(d8, "main birlestirildi: cakisma dalin tarafi korunarak cozuldu")
        _kos(d8, "checkout", "-q", "main")
        with open(os.path.join(d8, "tools.py"), "w") as f:   # main ilerledi (ff ENGELLENIR)
            f.write("# main tarafinda kod degisikligi\n")
        _commit(d8, "main'de kod degisikligi (urunler.json'a DOKUNULMADI)")
        _kos(d8, "-c", "user.email=t@t", "-c", "user.name=t",
             "merge", "-q", "muhendis", "-m", "dal alindi")
        du, sa, o8 = kapi(depo=d8)
        iddia("V8 [POZITIF] dal->main MERGE'i silinmis b'yi diriltti -> KIRMIZI",
              du == "KIRMIZI" and any(s[0] == "DIRILTME" and s[1] == "b" for s in sa),
              (du, sa))
        iddia("V8b tek suclu b: yeni gelen x DIRILTME sayilmaz (yeni id serbest)",
              o8.get("dirilen") == 1, (o8.get("dirilen"), sa))

        # V9 NEGATIF — MaCiT tipi TOPLU ekleme partisi (yanlis-pozitif nobeti)
        d9 = temel_depo("v9")
        parti = ["a", "c", "d"] + ["yeni-urun-%03d" % i for i in range(60)]
        _yaz(d9, parti)
        _commit(d9, "60 urun eklendi (MaCiT normal ekleme partisi)")
        du, sa, o9 = kapi(depo=d9)
        iddia("V9 [NEGATIF] 60'lik toplu ekleme partisi kapiyi TETIKLEMEZ -> YESIL",
              du == "YESIL" and o9.get("yeni_eklenen") == 60, (du, o9.get("yeni_eklenen")))

        # V10 NEGATIF — 2 BOSLUK girintili ESKI cag bicimi de ayristirilir
        d10 = temel_depo("v10", girinti=2)
        _yaz(d10, ["a", "c", "d", "b"], girinti=2)
        _commit(d10, "b geri geldi (eski 2-bosluk bicim)")
        du, _s, _o = kapi(depo=d10)
        iddia("V10 [POZITIF] 2-bosluk girintili ESKI bicimde de diriltme goruluyor",
              du == "KIRMIZI", du)

        # V11 FAIL-CLOSED — BEKLENMEYEN girinti: kapi KENDI ayikcalayicisina GUVENMEZ.
        # ⚠️ Fikstur GECERLI JSON'dur (json.dump indent=4 -> anahtarlar 8 bosluk); yani
        # vaka SADECE girinti nobetini olcer. Bozuk JSON kullansaydik ayni OLCULEMEDI
        # hukmu ayristirma hatasindan da gelirdi ve nobetin OLDUGU fark edilmezdi
        # (olculdu: girinti kolu no-op yapilinca bozuk-JSON fikstur yine YESIL veriyordu
        # = olu iddia).
        d11 = temel_depo("v11")
        with open(os.path.join(d11, URUNLER_ADI), "w", encoding="utf-8") as f:
            json.dump([_urun(u) for u in ["a", "c", "d"]], f, ensure_ascii=False, indent=4)
            f.write("\n")
        _commit(d11, "beklenmeyen girinti (anahtarlar 8 bosluk) — JSON GECERLI")
        du, sa, _o = kapi(depo=d11, taban="HEAD")
        iddia("V11 [FAIL-CLOSED] BEKLENMEYEN id girintisi -> OLCULEMEDI (yesil DEGIL)",
              du == "OLCULEMEDI" and any(s[0] == "OLCULEMEDI" and "GIRINTI" in s[2]
                                         for s in sa), (du, sa))

        # V17 SALT-OKUNURLUK (SENTETIK) — kapi kostugu deponun urunler.json'una DOKUNMAZ.
        # Gercek depo ayagi V14/V14b'de; bu ayak sentetik oldugu icin bir yazma mutasyonu
        # canli veriye HIC ulasmadan yakalanir.
        d17 = temel_depo("v17")
        yol17 = os.path.join(d17, URUNLER_ADI)
        with open(yol17, "rb") as f:
            once17 = hashlib.sha256(f.read()).hexdigest()
        _rc, once_p17, _e = _git(d17, "status", "--porcelain")
        kapi(depo=d17)
        with open(yol17, "rb") as f:
            sonra17 = hashlib.sha256(f.read()).hexdigest()
        _rc, sonra_p17, _e = _git(d17, "status", "--porcelain")
        iddia("V17 SALT-OKUNUR (sentetik): urunler.json sha256 + porcelain degismedi",
              once17 == sonra17 and once_p17 == sonra_p17,
              (once17[:12], sonra17[:12], once_p17, sonra_p17))

        # V12 POZITIF — diriltme + ayni commit'te yeni id: yeni id yesil SATIN ALMAZ
        d12 = temel_depo("v12")
        _yaz(d12, ["a", "c", "d", "b", "yepyeni"])
        _commit(d12, "diriltme + yeni urun ayni commit'te")
        du, sa, o12 = kapi(depo=d12)
        iddia("V12 [POZITIF] yeni id ile birlikte gelen diriltme yine KIRMIZI",
              du == "KIRMIZI" and o12.get("dirilen") == 1 and o12.get("yeni_eklenen") == 2,
              (du, o12.get("dirilen"), o12.get("yeni_eklenen")))

        # V13 — SAF karar fonksiyonu (mutasyon hedefi) yuk tasiyor mu
        iddia("V13 saf karar: silinmis&yeni -> dirilen",
              dirilenleri_bul({"b"}, {"a", "b"}, set()) == (["b"], []))
        iddia("V13b saf karar: beyanli olan dirilen SAYILMAZ",
              dirilenleri_bul({"b"}, {"a", "b"}, {"b"}) == ([], ["b"]))

    # ---- V14 SALT-OKUNURLUK (GERCEK depo, koşum oncesi/sonrasi sha256 + porcelain)
    try:
        gercek = depo_kok()
        urunler_yolu = os.path.join(gercek, URUNLER_ADI)

        def _sha():
            h = hashlib.sha256()
            with open(urunler_yolu, "rb") as f:
                for blok in iter(lambda: f.read(1 << 20), b""):
                    h.update(blok)
            return h.hexdigest()

        once_sha = _sha()
        _rc, once_porc, _e = _git(gercek, "status", "--porcelain")
        du, _s, o14 = kapi(depo=gercek)
        sonra_sha = _sha()
        _rc, sonra_porc, _e = _git(gercek, "status", "--porcelain")
        iddia("V14 SALT-OKUNUR: urunler.json sha256 koşum oncesi==sonrasi",
              once_sha == sonra_sha, (once_sha[:12], sonra_sha[:12]))
        iddia("V14b SALT-OKUNUR: `git status --porcelain` degismedi",
              once_porc == sonra_porc)
        # V15 YANLIS-POZITIF KANARYASI: gercek katalogda HEAD^1 -> HEAD YESIL olmali.
        iddia("V15 [NEGATIF] GERCEK depo HEAD^1 -> HEAD YESIL "
              "(kapi 'hep kirmizi' degil; silinmis kume %s id)" % o14.get("silinmis"),
              du == "YESIL", (du, o14))

        # V16 POZITIF, GERCEK KATALOG: gercekten silinmis bir id GERI KONULURSA kapi yanar.
        # Sentetik depo "kume turetme" yolunu olcer; bu vaka 990 kisilik GERCEK kumeye karsi
        # olcer. urunler.json'a DOKUNULMAZ — kopya GECICI dosyaya yazilir (salt-okunurluk
        # V14/V14b ile ayrica dogrulanir).
        gercek_ever, _o = gecmiste_gorulen(gercek, "HEAD")
        gercek_head = idler_revden(gercek, "HEAD")
        gercek_silinmis = sorted(gercek_ever - gercek_head)
        if not gercek_silinmis:
            iddia("V16 [POZITIF] GERCEK silinmis kume BOS -> vaka kurulamadi", False)
        else:
            kurban = gercek_silinmis[0]
            with open(urunler_yolu, encoding="utf-8") as f:
                govde = json.load(f)
            govde.append(_urun(kurban))
            gecici = os.path.join(tempfile.gettempdir(), "pruvo-diriltme-v16.json")
            try:
                with open(gecici, "w", encoding="utf-8") as f:
                    json.dump(govde, f, ensure_ascii=False, indent=2)
                du16, sa16, o16 = kapi(depo=gercek, taban="HEAD", yeni_dosya=gecici)
                iddia("V16 [POZITIF] GERCEK katalogda silinmis %r geri konunca -> KIRMIZI"
                      % kurban,
                      du16 == "KIRMIZI" and any(s[0] == "DIRILTME" and s[1] == kurban
                                                for s in sa16),
                      (du16, o16.get("dirilen")))
            finally:
                if os.path.exists(gecici):
                    os.remove(gecici)
    except Exception as e:                                   # pragma: no cover
        kirmizi += 1
        ham.append("    ❌ V14/V15 GERCEK depo olcumu yapilamadi — %s" % e)

    print("\n".join(ham))
    print("----------------------------------------------------------------------")
    if kirmizi == 0:
        print("SONUC: YESIL ✅ (kendini test) — POZITIF ve NEGATIF yonler ayri ayri olculdu.")
        return 0
    print("SONUC: KIRMIZI ❌ — %d iddia kaldi" % kirmizi)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--depo", help="depo koku (varsayilan: bu dosyanin deposu / cwd)")
    ap.add_argument("--taban", help="onceki durum (varsayilan: HEAD^1)")
    ap.add_argument("--yeni", dest="yeni_rev", help="yeni durum revizyonu (varsayilan: HEAD)")
    ap.add_argument("--calisma-agaci", action="store_true",
                    help="yeni durum = calisma agacindaki urunler.json (taban HEAD)")
    ap.add_argument("--azami-sure", type=float, default=None,
                    help="gecmis taramasi icin saniye tavani; asilirsa OLCULEMEDI")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    a = ap.parse_args()
    if a.kendini:
        return kendini_test()
    yeni_dosya = None
    if a.calisma_agaci:
        yeni_dosya = os.path.join(depo_kok(a.depo), URUNLER_ADI)
    durum, satirlar, olcumler = kapi(depo=a.depo, taban=a.taban, yeni_rev=a.yeni_rev,
                                     yeni_dosya=yeni_dosya, azami_sure=a.azami_sure)
    return rapor(durum, satirlar, olcumler)


if __name__ == "__main__":
    sys.exit(main())
