#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/devam-sinif-kapisi.py — IZLENEN KOK DEFTERLERINDE **ICERIK SINIFI** KAPISI.

🔴 NEDEN VAR (olculdu 1 Agu 2026): `DEVAM.md` 31 Tem'de Okan karariyla git TAKIBINE
alindi (devralan yarim isi gorebilsin diye). Alinmadan ONCE hassas bloklar
`DEVAM-ARSIV.md`'ye (git DISI) tasinmisti — ama o tarihten sonra BES ev ve cok
sayida oturum AYNI dosyaya yazmaya devam ediyor ve yazilanin ICERIK SINIFINI
kimse denetlemiyor. Depo PUBLIC (Pruvo138/pruvo): dosya ham olarak servis edilir,
kod aramasi ve egitim kazimalari tarafindan okunur, ve bir kez commit'lenen blob
silinse bile anonim olarak cekilebilir.

Yani bu, tam olarak SESSIZ-HATA sinifidir: hicbir sey kirmizi yanmaz, hicbir
ekran uyarmaz, yalnizca bir gun disaridan biri defteri okur.

MEVCUT NOBETCILER NEDEN YETMEZ (olculdu):
  * tools/kisisel-veri-test.py Kural B: DEVAM.md'yi AD ekseninde izin listesine
    aldi -> artik gecirir. Icerik eksenini o kural HIC olcmez.
  * tools/commit-mesaji-kapisi.py: COMMIT MESAJI ekseni; `--kaynak-tara` kolu ise
    yalnizca KENDI bes dosyasini tarar (KAYNAK_TARAMA), kok defterlerini DEGIL.
  * tools/kisisel-veri-test.py icerik ekseni: satici kisisel verisini uretilen
    HTML sayfalarinda arar; kok .md defterlerini taramaz.
Bu kapi o bosluktur.

NEDEN COMMIT-MSG DEGIL: ihlal MESAJDA degil DOSYA ICERIGINDEDIR. commit-msg
kancasi calisma agacini gormez.

NEDEN CI'DAKI `build` KOLU (yer secimi — GEREKCE):
  * git kancalari COMMIT EDILMEZ (.git/ depoda yasamaz). Bes ev + her yeni klon +
    her izole worktree icin "kanca kurulu mu" garantisi YOKTUR; `--no-verify` de
    tek satirda atlar. Bir kancaya baglanan kural, kurulu OLMAYAN makinede
    SESSIZCE yok demektir — bu kapinin kapatmak istedigi sinifin ta kendisi.
  * `build` isi yayin yolunun BASIDIR: `deploy` -> `needs: build`, `yayin` ->
    `needs: deploy`. Yani bu adim kirmizi yanarsa pruvo3d.com'a YAYIN CIKMAZ;
    kapi "bagiran ama bloklamayan" degildir. (Olcum: tools/is-akisi-kapisi.py
    SERIT tablosu + `needs` zinciri.)
  * tools/ci-kapsam-test.py `tools/*-kapisi.py` adini KESFEDER: bu betik
    deploy.yml'den silinirse ya da `echo`/`--help` ile mensiyona cevrilirse O
    kapi kirmizi yanar. Yani buradaki kablo KENDI nobetcisine sahiptir; bir
    kancadaki satirin boyle bir nobetcisi YOKTUR.
  Beyan edilen sinir: CI `push`ta kosar, yani ihlal main'e ULASTIKTAN sonra
  yakalanir ve YAYINI durdurur. O sinirin BEDELI 8-9 Agu 2026'da olculdu:
  `bdddaee0` DEVAM.md'ye bir E5 satiri soktu, `serit-a2`+`serit-a3` kirmizi
  yandi, `deploy`+`yayin` SKIPPED kaldi ve yayin ~1 SAAT durdu. Bu yuzden
  9 Agu 2026'da IKINCI (daha erken) bir kol eklendi: `--index`, COMMIT ANINDA
  INDEX'i yargilar (tools/kancalar/pre-commit adim 6). Kancanin kurulu olmasi
  hala GARANTI DEGILDIR — o yuzden ZORLAYICI kol CI'DA KALDI; erken kol onun
  YERINE GECMEZ, ONUNDE DURUR.

KAPSAM: `git ls-files` ciktisindan KOK seviyedeki (yolda '/' YOK) BELGE
uzantili dosyalar. Bugun uc dosya: DEVAM.md · README.md · ege-bilgi.md. Kural
ad-BAGIMSIZDIR: yarin izlenen yeni bir kok defteri (NOTLAR.md, DEVIR.md) acilirsa
kapsama KENDILIGINDEN girer. Muafiyet listesi YOKTUR (liste = curume).

🔴 YANLIS-POZITIF BUTCESI (bu dosyanin varlik sarti): DEVAM.md HER OTURUMDA
guncellenir. Kapi surekli yanarsa herkes `--no-verify` aliskanligina kayar ve
koruma SIFIRLANIR. Bu yuzden:
  * MESRU IS AKISI metni YESIL kalir: kapi ADLARI, olcum sayilari, dal/SHA,
    kime ne is dustugu, "fail-closed" beyani, kabul testi sayilari.
  * Desenler DAR ve ACIKTIR; genis kelime avina CIKILMAZ.
  * Butce KOSARAK olculur: --kendini-test hem gercek DEVAM.md'yi hem
    DEVAM-ARSIV.md'yi (varsa) tarar ve mesru satirlarda vurus SAYAR.

OLCULEN EKSENLER (her biri ayri bir sinif; hepsi FAIL-CLOSED):
  E1 satici-kimligi   — tedarikci/satici ADI ve GIZLI ALAN ADI. Kural KODA
                        YAZILMAZ: tools/commit-mesaji-kapisi.py'nin PBKDF2 OZET
                        mekanizmasi (tools/sizinti-desen-ozetleri.json) MODUL
                        olarak kullanilir. Duz ad bu dosyada GECMEZ.
  E2 oran-marj        — TICARI oran/iskonto/komisyon/alis-maliyet fiyati + MIKTAR.
                        AYIRT EDICI KELIME DEGIL SAYININ BOYUTUDUR: "marj" gibi
                        BELIRSIZ konu ancak miktar bir MUHENDISLIK birimi
                        (px/mm/ms/bayt/karakter...) tasirsa YESIL; para birimi
                        HER ZAMAN ticaridir; boyutsuz miktar (ciplak sayi, %)
                        KIRMIZI kalir (fail-closed).
  E3 gizli-dosya      — sir tasiyan gitignore'lu artefakt ADLARI (dar literal
                        liste). DEVAM-ARSIV.md BILEREK LISTEDE DEGIL: adi
                        CLAUDE.md'de zaten yazar ve defterin ilk satiri ona
                        isaret eder — sir tasiyan bir ad degildir.
  E4 sir-jeton        — jeton/anahtar BICIMLERI (ALLCAPS *_TOKEN/_KEY/_SECRET,
                        sk-/ghp_/AKIA, >=32 hane hex, >=40 karakter karisik
                        base64) + "wrangler secret" sinifi ifadeler.
  E5 kapi-bypass      — fail-open beyani, `--no-verify`, bypass, PRUVO_*_ATLA,
                        core.hooksPath, "kapiyi/nobetciyi devre disi", ve
                        NOBETCI KORLUGU (kapi/nobetci + gormez/kacirir/kor nokta).
  E6 guvenlik-bulgusu — "yasakli ad", "satici/tedarikci adi|kimligi", "ifsa",
                        "sizdi", ve GATE-ADI OLMAYAN "sizinti" kullanimi; ayrica
                        SUNUCU/API yuzeyi + istismar fiili es-olusumu
                        (or. "sunucuda tahsil edil...", "reddedilmeli", "kor").

🔴 ESLESEN METIN BASILMAZ. Cikti yalniz (dosya, satir no, eksen, DESEN ETIKETI)
tasir. Aksi halde kapi sizintiyi kendi CI gunlugunde (PUBLIC) cogaltirdi.

Kullanim:
    python3 tools/devam-sinif-kapisi.py               # izlenen kok defterlerini yargila
    python3 tools/devam-sinif-kapisi.py --kendini-test
    python3 tools/devam-sinif-kapisi.py --mutasyon    # KOPYA uzerinde mutasyon bataryasi
    python3 tools/devam-sinif-kapisi.py --dosya <yol> # tek dosya (tani/fikstur)
    python3 tools/devam-sinif-kapisi.py --index       # INDEX (commit ani) kolu

Cikis kodu: 0 = temiz · 1 = SINIF IHLALI · 2 = OLCULEMEDI (fail-closed).
"""
import argparse
import hashlib
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from git_ortami import sentetik_git

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

RC_TEMIZ = 0
RC_IHLAL = 1
RC_OLCULEMEDI = 2

KAPI_YOLU = "tools/devam-sinif-kapisi.py"

# Kok BELGE uzantilari — kapsam bunlarla sinirlidir. (index.html / urunler.json /
# *.js kok dosyalari BILEREK kapsam disi: onlar yayinlanan varliklardir ve kendi
# nobetcileri vardir; buraya alinmalari bloklayici yanlis-pozitif riski yaratir.)
BELGE_UZANTILARI = (".md", ".markdown", ".txt", ".rst", ".adoc")


# ===========================================================================
# E1 — SATICI KIMLIGI: OZET MEKANIZMASI (duz ad KODA YAZILMAZ)
# ===========================================================================
# TEK KAYNAK: tools/commit-mesaji-kapisi.py. Ikinci bir kopya = drift
# ([[ayna-kapi-kesif-ekseni]]). FAIL-CLOSED: modul ya da ozet artefakti
# yuklenemezse bu kapi YESIL VERMEZ (rc 2) — "olcemedim" YESIL degildir.
_OZET_SOZLESME = ("normalize", "ozet_kaydi_yukle", "ad_isabetleri", "adaylar",
                  "_ozetle", "alan_adi_isabetleri", "katalog_markalari")


def _git_ortami_modulu():
    """(fonksiyon, hata) — tools/git_ortami.py'nin `git_ortami()`si.

    🔴 TEK KAYNAK: git baglam scrub'i BU DOSYADA TANIMLI DEGILDIR; ikinci bir
    tanim [[ikiz-tanim-sessiz-ayrisma]] sinifidir ve `git_ortami.py --kendini-test`
    onu KIRMIZI yakar. YOL UZERINDEN yuklenir (import DEGIL): mutasyon bataryasi
    bu dosyanin KOPYASINI gecici bir dizinde kosturur ve orada `sys.path` ile
    yapilan bir import COZULMEZDI; TOOLS ise `--kok` ile GERCEK depoyu gosterir.
    Yalniz KABUL BATARYASI kullanir (sentetik depolar); GERCEK kol ortami
    BILEREK temizlemez — bkz. `_git`."""
    yol = os.path.join(TOOLS, "git_ortami.py")
    if not os.path.isfile(yol):
        return None, "git baglam scrub kaynagi YOK: %s" % yol
    try:
        spec = importlib.util.spec_from_file_location("pruvo_git_ortami", yol)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["pruvo_git_ortami"] = mod
        spec.loader.exec_module(mod)
    except Exception as e:                                  # noqa: BLE001
        return None, "git baglam scrub kaynagi YUKLENEMEDI: %s (%s)" % (yol, e)
    if not hasattr(mod, "git_ortami"):
        return None, "git_ortami.py'de git_ortami() YOK (sozlesme degismis)"
    return mod.git_ortami, None


def ozet_modulu(yol=None):
    """(modul, hata). tools/commit-mesaji-kapisi.py'yi MODUL olarak yukler."""
    yol = yol or os.path.join(TOOLS, "commit-mesaji-kapisi.py")
    if not os.path.isfile(yol):
        return None, ("desen kaynagi YOK: %s — E1 (satici kimligi) ekseni OLCULEMEZ. "
                      "Yasakli ad bu dosyaya YAZILAMAZ (depo PUBLIC), o yuzden ozet "
                      "mekanizmasi ZORUNLUDUR." % yol)
    try:
        spec = importlib.util.spec_from_file_location("pruvo_sizinti_ozet", yol)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["pruvo_sizinti_ozet"] = mod
        spec.loader.exec_module(mod)
    except Exception as e:                                  # noqa: BLE001
        return None, "desen kaynagi YUKLENEMEDI: %s (%s)" % (yol, e)
    for ad in _OZET_SOZLESME:
        if not hasattr(mod, ad):
            return None, ("desen kaynaginda %s YOK -> ozet sozlesmesi degismis "
                          "(fail-closed)" % ad)
    return mod, None


# ===========================================================================
# E2..E6 — DAR VE ACIK DESENLER
# ===========================================================================
# 🔴 DESEN YAZMA KURALI: her desen ya TAM BIR IFADEdir ya da IKI PARCANIN AYNI
# SATIRDA es-olusumudur. Tek basina genis kelime ("acik", "kapi", "guvenlik",
# "risk") DESEN DEGILDIR — olculdu: bunlar mesru is akisi metnini yakar.

# --- E2: ticari oran / marj — BIRIM (BOYUT) EKSENLI ------------------------
# 🔴 NEDEN BOYUT (olculdu 11 Agu 2026, DEVAM.md CTA blogu): kural "oran konusu +
# HERHANGI BIR RAKAM" idi. Bir MUHENDISLIK notu (CTA butonu ile WhatsApp hapi
# arasindaki YERLESIM payi) iki satirda KIRMIZI yandi; yazar kapiyi gecmek icin
# notu yeniden ADLANDIRDI. Kapi sizintiyi degil KELIMEYI kovaladi. Ayni sinifin
# onceki ornegi de tekil kelime yamasiyla ("guvenlik marji") kapatilmisti ->
# [[tekil-yama-sinifi-kapatmaz]] · [[envanter-drift-parti-basina]].
#
# AYIRT EDICI = SAYININ BOYUTU:
#   * TICARI KONU tek basina KIRMIZIDIR; boyut muafiyeti ONA ULASMAZ (bir ticari
#     oran, yaninda px yazarak aklanamaz).
#   * BELIRSIZ KONU ("marj") ancak MUHENDISLIK BOYUTU KANITLANIRSA yesildir.
#   * PARA BOYUTU satirda gorunurse muhendislik kaniti GECERSIZDIR (ustunluk).
#   * Boyutsuz miktar KIRMIZI kalir — "olcemedim" YESIL DEGILDIR.
# ⚠️ `%` KANIT DEGILDIR, BOYUTSUZDUR: bu isi baslatan gercek satirin kendisi
#    "~%5 (~7 px)" yaziyordu; `%` ticari sayilsaydi o satir YINE yanardi.
# ⚠️ MIKTAR = BAGIMSIZ SAYI JETONU, "herhangi bir rakam" DEGIL. Olculdu:
#    `CTA-A1` / `serit-a2` / `364095f6` icindeki rakam miktar degildir.

# 🧊 DONMUS KELIME MUAFIYETI — BUYUTULEMEZ (kabul testi A2 olcer). Boyut
# ekseninden onceki donemin TEK kalintisi: "guvenlik marji" bir KARAKTER butcesi
# sabitidir (tools/ege-bilgi-tavan-test.py GUVENLIK_MARJI=400) ve gercek defter
# metninde CIPLAK sayiyla gecer. YENI ornek buraya EKLENMEZ; birim yazilir.
E2_DONMUS_ONEKLER = ("guvenlik",)
E2_DONMUS = re.compile(r"\b(?:%s) marj\w*\b" % "|".join(E2_DONMUS_ONEKLER))

# TICARI KONU: tek basina yeterli (belirsizlik YOK).
E2_TICARI_KONU = re.compile(
    r"\b(iskonto|kar payi|karpayi|komisyon|alis fiyati|alim fiyati|"
    r"maliyet fiyati|tedarik fiyati|kur farki|doviz kuru)\b")
# BELIRSIZ KONU: ticari de olabilir muhendislik de — boyut karar verir.
E2_BELIRSIZ_KONU = re.compile(r"\bmarj\w*\b")

# MIKTAR / BOYUT olcumleri HAM metinde yapilir: normalize() `1,35`i `1 35`e boler,
# `%` ve `₺` gibi isaretleri SILER ve birim bitisikligini (`7 px`) korur ama para
# sembolunu kaybederdi -> [[olcum-birimi-bayt-utf16]] sinifi bir birim hatasi.
E2_SAYI = re.compile(r"(?<![0-9A-Za-z])\d[\d.,]*(?![0-9A-Za-z])")
E2_PARA = re.compile(
    r"(?:(?<![0-9A-Za-z])\d[\d.,]*\s*(?:tl|try|usd|eur|gbp|lira|kurus|"
    r"dolar|euro|sterlin)\b)|(?:[₺$€£]\s*\d)|(?:\d\s*[₺$€£])", re.I)
# KANONIK BIRIM KUMESI (uzunluk · sure · veri · frekans · kutle · metin/sayim).
# Uyelik olcutu BOYUTTUR, cumle kalibi DEGIL.
E2_BIRIM = re.compile(
    r"(?<![0-9A-Za-z])\d[\d.,]*\s*"
    r"(?:px|piksel|pt|rem|em|ch|vw|vh|dp|"
    r"mm|cm|km|um|inc|mikron|m|"
    r"ms|sn|saniye|dakika|dk|saat|hz|khz|mhz|fps|dpi|"
    r"bayt|byte|bit|kb|mb|gb|tb|"
    r"karakter|hane|satir|adet|derece|"
    r"gr|gram|kg|ml)\b", re.I)


def e2_bulgusu(ham, norm):
    """E2 hukmu -> desen etiketi ya da None (bkz. ustteki blok).

    FAIL-CLOSED: belirsiz konuda MUHENDISLIK BOYUTU KANITLANMADIKCA KIRMIZI."""
    if not E2_SAYI.search(ham):
        return None
    if E2_TICARI_KONU.search(norm):
        return "ticari-konu+miktar"
    if not E2_BELIRSIZ_KONU.search(E2_DONMUS.sub(" ", norm)):
        return None
    if E2_PARA.search(ham):
        return "belirsiz-konu+para-boyutu"
    if E2_BIRIM.search(ham):
        return None
    return "belirsiz-konu+boyutsuz-miktar"

# --- E3: sir tasiyan gitignore'lu artefaktlar (HAM metin, dar literal) ------
# DEVAM-ARSIV.md BILEREK YOK (bkz. baslik). .gitignore/.driveignore de YOK:
# ikisi de IZLENEN ve zaten PUBLIC.
E3_DESENLER = (
    ("r2-kimlik-dosyasi", re.compile(r"(?<![\w.-])\.r2-credentials\.json\b")),
    ("urun-kaynak-kaydi", re.compile(r"(?<![\w.-])\.urun-kaynaklari\.json\b")),
    ("sizinti-desen-kaynagi", re.compile(r"(?<![\w.-])\.sizinti-desenleri\.txt\b")),
    ("wrangler-gizli-degisken", re.compile(r"(?<![\w.-])\.dev\.vars\b")),
    ("ortam-dosyasi", re.compile(r"(?<![\w.-])\.env(\.[A-Za-z0-9_-]+)?\b")),
)

# --- E4: jeton / anahtar BICIMLERI (HAM metin) -----------------------------
# ⚠️ DAR TUTULDU: DEVAM.md 8 haneli git SHA'lariyla ve 9-11 haneli olcum
# sayilariyla DOLUDUR. Hex esigi 32'dir; bu depoda hicbir mesru satir o uzunlukta
# hex tasimaz (olculdu). Base64 esigi 40 VE uc karakter sinifinin de bulunmasi
# sartina baglidir.
E4_HAM = (
    ("allcaps-sir-adi",
     # ⚠️ ONEK'te ALT CIZGI SART: olculdu ki `[A-Z0-9]{2,}` oneki
     # CLOUDFLARE_API_TOKEN'i KACIRIYORDU ("...E_API" arasinda kelime siniri yok).
     re.compile(r"\b[A-Z][A-Z0-9_]{2,}_(TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|"
                r"CREDENTIALS|APIKEY)\b")),
    ("saglayici-jetonu", re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|"
                                    r"AKIA[0-9A-Z]{12,})\b")),
    ("uzun-hex", re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{32,}(?![0-9A-Za-z])")),
)
_E4_B64 = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])")
E4_NORM = re.compile(r"\b(wrangler secret|secret put|api anahtari|erisim anahtari|"
                     r"gizli anahtar|hesap kimligi)\b")

# --- E5: kapi bypass'i / fail-open / nobetci korlugu -----------------------
# NOT: normalize() alfanumerik olmayan her seyi BOSLUGA cevirir; bu yuzden
# "fail-open" -> "fail open", "--no-verify" -> "no verify", "core.hooksPath" ->
# "core hookspath". "fail-closed" -> "fail closed" ve DESENDE YOKTUR (mesru beyan).
E5_DESENLER = (
    ("fail-open-beyani", re.compile(r"\bfail open\b")),
    ("kanca-atlama-bayragi", re.compile(r"\bno verify\b")),
    ("bypass", re.compile(r"\bbypass\w*\b")),
    ("ortam-atlama-anahtari", re.compile(r"\bpruvo [a-z0-9]+ atla\b")),
    ("kanca-yolu-oldurme", re.compile(r"\bcore hookspath\b")),
    ("kapi-devre-disi", re.compile(
        r"\b(kapiyi|kapisini|nobetciyi|nobetcisini|korumayi|kancayi|kilidi)"
        r" devre disi\b")),
)
# NOBETCI KORLUGU: iki parcanin AYNI SATIRDA es-olusumu.
E5_KORUYUCU = re.compile(r"\b(nobetci|nobetcisi|nobetciler|kapi|kapisi|kapilar|"
                         r"guard|kanca|hook)\b")
E5_KORLUK = re.compile(r"\b(gormez|gormedi|gormuyor|gormezdi|kacirir|kacirdi|"
                       r"kaciriyor|kaciyordu|yakalamaz|yakalamadi|kor nokta|"
                       r"nobetsiz|atlanir|atlatilir|korumasiz)\b")

# --- E6: guvenlik bulgusu / sizinti olayi ----------------------------------
# 🔴 GATE-ADI / OLCUM ISTISNASI (yanlis-pozitif butcesinden GELDI — 1 Agu, 6665
# satirlik gercek arsiv korpusunda olculdu): "sizinti nobetcisi", "sizinti nobeti",
# "sizinti yok", "sizinti TEMIZ", "tedarikci-adi nobetcisi" MESRU IS AKISI
# metnidir (kapi ADI ya da OLCUM sonucu). Ilk surumde bunlar YANIYORDU; boyle bir
# kapi her oturumda kirmizi yanip `--no-verify` aliskanligi yaratirdi.
_GATE_ADI = (r"nobetci|nobetcisi|nobetcileri|nobeti|kapisi|kapi|kapilari|"
             r"taramasi|testi|deseni|desenleri|hatti|butcesi|olcumu|sayaci|"
             r"riski|sinifi|ekseni")
_OLCUM_SONUCU = r"yok|temiz|sifir|0\b"

# 🔴 IS-AKISI ADI ISTISNASI (14 Agu 2026 — yanlis-pozitif, AYNI GUN DORT KEZ olculdu).
# Deponun KENDI CI is akisi `.github/workflows/spec-ifsa-alarmi.yml` ve adi
# "Spec/tasarim ifsasi alarmi". Nobet cron'u her turda kosum ADLARINI deftere yaziyor;
# `ifsa` deseni bunu guvenlik bulgusu sanip commit'i DORT KEZ durdurdu ve her seferinde
# metni elle notrlemek gerekti — kapinin olcmesi gereken sey bir DOSYA ADI degildi.
# Istisna ELLE DEFTER DEGIL, `.github/workflows/` icinden TURER: yeni bir is akisi
# eklendiginde kendiliginden kapsanir, bayatlamaz
# ([[kapsam-evrenini-cagri-grafindan-turet]]).
# 🔴 DAR TUTULDU: yalnizca jetonun bir is-akisi KIMLIGININ ICINDE gectigi konum muaftir.
# "sunucu ifsa oldu" gibi GERCEK bulgu cumlesi KIRMIZI KALIR (kabul testinde olculur).
# Dizin okunamazsa muafiyet BOS kalir -> bugunku (fail-closed) davranis korunur.
def _is_akisi_kimlikleri():
    """`.github/workflows/` icindeki dosya adlari + `name:` degerleri (kucuk harf)."""
    kok = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       ".github", "workflows")
    kimlikler = set()
    try:
        adlar = sorted(os.listdir(kok))
    except OSError:
        return kimlikler
    for ad in adlar:
        if not ad.endswith((".yml", ".yaml")):
            continue
        kimlikler.add(ad.lower())
        kimlikler.add(os.path.splitext(ad)[0].lower())
        try:
            with open(os.path.join(kok, ad), encoding="utf-8", errors="replace") as f:
                for satir in f:
                    m = re.match(r"\s*name:\s*[\"']?(.+?)[\"']?\s*$", satir)
                    if m:
                        kimlikler.add(m.group(1).strip().lower())
                        break
        except OSError:
            continue
    return {k for k in kimlikler if k}


_IS_AKISI_KIMLIKLERI = _is_akisi_kimlikleri()


def _is_akisi_adinda_mi(ham, bas, son):
    """[bas,son) araligindaki isabet, bir is-akisi KIMLIGININ icinde mi geciyor?"""
    for kimlik in _IS_AKISI_KIMLIKLERI:
        yer = 0
        alt = ham.lower()
        while True:
            i = alt.find(kimlik, yer)
            if i < 0:
                break
            if i <= bas and son <= i + len(kimlik):
                return True
            yer = i + 1
    return False


E6_DESENLER = (
    ("yasakli-ad-ifadesi", re.compile(r"\byasakli ad\w*\b")),
    ("satici-kimlik-ifadesi",
     re.compile(r"\b(satici|tedarikci|tasarimci) (ad|adi|adini|kimlig|kimligi|"
                r"kimligini)\w*\b(?! ?(%s))" % _GATE_ADI)),
    ("ifsa", re.compile(r"\bifsa\w*\b")),
    ("sizdi", re.compile(r"\b(sizdi|sizmis|sizmisti|sizdirdi)\b")),
    # "sizinti" TEK BASINA kirmizidir; ARDINDAN bir KAPI-ADI ismi ya da bir OLCUM
    # SONUCU gelirse YESIL.
    ("sizinti-olayi", re.compile(
        r"\bsizinti\w*\b(?! ?(%s|%s))" % (_GATE_ADI, _OLCUM_SONUCU))),
)
# SUNUCU/API YUZEYI + ISTISMAR FIILI es-olusumu (istismar edilebilir acik tarifi).
E6_YUZEY = re.compile(r"\b(sunucu|sunucuda|sunucuya|sunucunun|sunucudaki|"
                      r"sunucu tarafinda|api|endpoint|uc noktasi)\b")
E6_ISTISMAR = re.compile(r"\b(tahsil edil\w*|fazla tahsil|eksik tahsil|"
                         r"dogrulanmiyor|dogrulanmadan|dogrulanmiyordu|yetkisiz|"
                         r"reddedilmeli|uygulanmamali|kor)\b")


def _b64_isabeti(ham):
    """>=40 karakterlik base64 gorunumlu dizide UC karakter sinifi da var mi.
    (Sinif sarti olmadan uzun duz metin/URL parcalari yanlis-pozitif verirdi.)"""
    for m in _E4_B64.finditer(ham):
        s = m.group(0)
        if (any(c.islower() for c in s) and any(c.isupper() for c in s)
                and any(c.isdigit() for c in s)):
            return True
    return False


# YEREL/DONGU adresleri E1 alan-adi ekseninde YANLIS-POZITIFTIR: satici/vitrin
# alan adi degil, gelistirme ucudur (olculdu: `http://localhost:8137` canli panel).
_YEREL_UC = re.compile(r"\b(localhost|127\.0\.0\.1|0\.0\.0\.0|::1)\b", re.I)


def satir_eksenleri(ham, norm, kayit=None, ozet=None, markalar=None,
                    ad_ekseni=True):
    """Tek satir -> [(eksen, desen_etiketi), ...]. Eslesen METIN DONMEZ.

    ad_ekseni=False: E1'in PBKDF2 AD kolu ATLANIR — metin_bulgulari() onu TUM
    belge icin TEK KUMEDE toplu ozetler (satir basina ozetleme O(satir x kelime)
    PBKDF2 demektir; olculdu: 244 satirda 4,0 s, 1061 satirda 26 s -> defter
    buyudukce bloklayici CI adimi surunur)."""
    bulgular = []

    # E1 — satici kimligi (ozet mekanizmasi; duz ad bu dosyada YOK)
    if ozet is not None and kayit is not None:
        if ad_ekseni:
            for no, _n in ozet.ad_isabetleri(ham, kayit):
                bulgular.append(("E1 satici-kimligi", "gizli-desen-#%d" % no))
        try:
            if not _YEREL_UC.search(ham):
                for kusur in ozet.alan_adi_isabetleri(ham, kayit, markalar):
                    bulgular.append(("E1 satici-kimligi", "taninmayan-alan-adi"))
                    del kusur
        except Exception:                                   # noqa: BLE001
            bulgular.append(("E1 satici-kimligi", "alan-adi-ekseni-OLCULEMEDI"))

    # E2 — ticari oran / marj (BOYUT ekseni)
    _e2 = e2_bulgusu(ham, norm)
    if _e2:
        bulgular.append(("E2 oran-marj", _e2))

    # E3 — gizli dosya adi
    for etiket, rx in E3_DESENLER:
        if rx.search(ham):
            bulgular.append(("E3 gizli-dosya", etiket))

    # E4 — jeton / anahtar
    for etiket, rx in E4_HAM:
        if rx.search(ham):
            bulgular.append(("E4 sir-jeton", etiket))
    if _b64_isabeti(ham):
        bulgular.append(("E4 sir-jeton", "uzun-base64"))
    if E4_NORM.search(norm):
        bulgular.append(("E4 sir-jeton", "sir-yonetimi-ifadesi"))

    # E5 — kapi bypass'i / nobetci korlugu
    for etiket, rx in E5_DESENLER:
        if rx.search(norm):
            bulgular.append(("E5 kapi-bypass", etiket))
    if E5_KORUYUCU.search(norm) and E5_KORLUK.search(norm):
        bulgular.append(("E5 kapi-bypass", "nobetci-korlugu"))

    # E6 — guvenlik bulgusu / sizinti olayi
    for etiket, rx in E6_DESENLER:
        for m in rx.finditer(norm):
            if (etiket == "ifsa"
                    and _is_akisi_adinda_mi(ham, m.start(), m.end())):
                continue
            bulgular.append(("E6 guvenlik-bulgusu", etiket))
            break
    if E6_YUZEY.search(norm) and E6_ISTISMAR.search(norm):
        bulgular.append(("E6 guvenlik-bulgusu", "sunucu-yuzeyi+istismar"))

    return bulgular


def _ad_ekseni_toplu(satirlar, kayit, ozet):
    """E1 AD kolu — TUM belge icin TEK kumede ozetleme (maliyet kontrolu).

    Adaylar once (uzunluk, aday) -> {satir no} eslemesinde toplanir, sonra HER
    BENZERSIZ aday BIR KEZ PBKDF2'lenir. Satir basina ozetlemeye gore is,
    belgedeki BENZERSIZ jeton sayisiyla sinirlanir. Hukum DEGISMEZ: ayni
    `adaylar()` + ayni `_ozetle()` kullanilir (TEK KAYNAK korunur)."""
    uzunluklar = sorted({n for n, _ in kayit["desenler"]})
    aday_satir = {}
    for i, ham in enumerate(satirlar, start=1):
        for n in uzunluklar:
            for aday in ozet.adaylar(ham, n):
                aday_satir.setdefault((n, aday), set()).add(i)
    ozet_satir = {}
    for (n, aday), nolar in aday_satir.items():
        anahtar = (n, ozet._ozetle(aday, kayit["tuz"], kayit["dongu"]))
        ozet_satir.setdefault(anahtar, set()).update(nolar)
    sonuc = []
    for no, (n, oz) in enumerate(kayit["desenler"]):
        for satir_no in sorted(ozet_satir.get((n, oz), ())):
            sonuc.append((satir_no, "E1 satici-kimligi", "gizli-desen-#%d" % no))
    return sonuc


def metin_bulgulari(metin, kayit=None, ozet=None, markalar=None):
    """Metin -> [(satir_no, eksen, etiket), ...] (1 tabanli satir numarasi)."""
    normalize = ozet.normalize if ozet is not None else (lambda s: s.lower())
    satirlar = metin.splitlines()
    sonuc = []
    if ozet is not None and kayit is not None:
        sonuc.extend(_ad_ekseni_toplu(satirlar, kayit, ozet))
    for i, ham in enumerate(satirlar, start=1):
        norm = normalize(ham)
        for eksen, etiket in satir_eksenleri(ham, norm, kayit, ozet, markalar,
                                             ad_ekseni=False):
            sonuc.append((i, eksen, etiket))
    return sorted(sonuc)


# ===========================================================================
# KAPSAM — IZLENEN KOK BELGELERI (fail-closed + canlilik capasi)
# ===========================================================================
def _kok_belge_mi(yol):
    """KOK seviyede BELGE mi? TEK KAYNAK ([[ikiz-tanim-sessiz-ayrisma]]).

    Hem IZLENEN kol (`git ls-files`) hem INDEX kolu (`git diff --cached`) kapsam
    kuralini BU predikattan turetir. Iki yerde iki kopya olsaydi biri
    daraltildiginda oteki sessizce genis kalirdi."""
    return "/" not in yol and yol.lower().endswith(BELGE_UZANTILARI)


def _git_ls_files(kok=None):
    try:
        r = subprocess.run(["git", "-C", kok or ROOT, "ls-files", "-z"],
                           capture_output=True, text=True)
    except OSError as e:
        return 127, "", "git calistirilamadi: %s" % e
    return r.returncode, r.stdout, r.stderr


def izlenen_kok_belgeleri(kosucu=None, kok=None):
    """(yollar, hata). FAIL-CLOSED + CANLILIK:
      * git rc != 0            -> OLCULEMEDI
      * rc=0 ama BOS liste     -> OLCULEMEDI (bu depoda imkansiz)
      * liste kapinin KENDI yolunu icermiyor -> OLCULEMEDI (sparse/partial
        checkout, yanlis ROOT, PATH'te git shim, bozuk index)
    Bu uc dal olmadan kapi "0 dosya tarandi -> temiz" diyerek SESSIZ YESIL yanardi."""
    rc, cikti, hata = (kosucu or (lambda: _git_ls_files(kok)))()
    if rc != 0:
        return None, "git ls-files basarisiz (rc=%s): %s" % (
            rc, (hata or "").strip() or "?")
    hepsi = [y for y in cikti.split("\0") if y]
    if not hepsi:
        return None, ("git ls-files BOS liste dondurdu (rc=0) — bu depoda imkansiz; "
                      "kapsam kaybolmus demektir. Bos kapsam SESSIZ YESIL SAYILMAZ.")
    if KAPI_YOLU not in hepsi:
        return None, ("CANLILIK — izlenen dosya listesi kapinin KENDI yolunu (%s) "
                      "icermiyor: git basarili dondu ama liste BOS ya da KISMI. "
                      "rc=0 geldi diye SESSIZ YESIL verilmez." % KAPI_YOLU)
    kok_belge = [y for y in hepsi if _kok_belge_mi(y)]
    if not kok_belge:
        return None, ("izlenen KOK belge dosyasi BULUNAMADI — bu depoda en az "
                      "DEVAM.md ve README.md izlenir. Kapsam bos: OLCULEMEDI.")
    return sorted(kok_belge), None


def dosya_metni(yol):
    """(metin, hata). Ayristirilamayan dosya YESIL DEGILDIR (fail-closed)."""
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except OSError as e:
        return None, "okunamadi: %s" % e
    try:
        return ham.decode("utf-8"), None
    except UnicodeDecodeError as e:
        return None, ("UTF-8 olarak COZULEMEDI (%s) — icerik ayristirilamayan bir "
                      "dosya taranmis SAYILMAZ" % e)


# ===========================================================================
# KOL: GERCEK TARAMA
# ===========================================================================
def tara(kok=None, dosyalar=None, ozet_yolu=None, kosucu=None, sessiz=False):
    """(rc, bulgular, taranan_satir). Cikti eslesen METNI ASLA tasimaz."""
    kok = kok or ROOT
    ozet, hata = ozet_modulu(ozet_yolu)
    if ozet is None:
        if not sessiz:
            print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI, [], 0
    kayit, khata = ozet.ozet_kaydi_yukle()
    if kayit is None:
        if not sessiz:
            print("OLCULEMEDI (fail-closed KIRMIZI): desen ozet artefakti — %s"
                  % khata, file=sys.stderr)
        return RC_OLCULEMEDI, [], 0
    try:
        markalar = ozet.katalog_markalari()
    except Exception:                                       # noqa: BLE001
        markalar = None

    if dosyalar is None:
        dosyalar, hata = izlenen_kok_belgeleri(kosucu=kosucu, kok=kok)
        if dosyalar is None:
            if not sessiz:
                print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
            return RC_OLCULEMEDI, [], 0

    bulgular = []
    satir_sayisi = 0
    for rel in dosyalar:
        tam = rel if os.path.isabs(rel) else os.path.join(kok, rel)
        metin, dhata = dosya_metni(tam)
        if metin is None:
            if not sessiz:
                print("OLCULEMEDI (fail-closed KIRMIZI): %s — %s" % (rel, dhata),
                      file=sys.stderr)
            return RC_OLCULEMEDI, [], satir_sayisi
        satir_sayisi += len(metin.splitlines())
        for no, eksen, etiket in metin_bulgulari(metin, kayit, ozet, markalar):
            bulgular.append((rel, no, eksen, etiket))

    if not sessiz:
        print("taranan kok belgesi: %d · satir: %d" % (len(dosyalar), satir_sayisi))
        for rel, no, eksen, etiket in bulgular:
            print("  * SINIF IHLALI: %s:%d — %s [%s]. Eslesen metin BILEREK "
                  "yazilmiyor." % (rel, no, eksen, etiket), file=sys.stderr)
        if bulgular:
            print("IHLAL: %d satir. COZUM: satirlari DEVAM-ARSIV.md'ye (git DISI) "
                  "TASI, yerine notr tek satirlik isaretci birak. Silme YOK, "
                  "tasima VAR." % len(bulgular), file=sys.stderr)
        else:
            print("temiz: 0 sinif ihlali.")
    return (RC_IHLAL if bulgular else RC_TEMIZ), bulgular, satir_sayisi


# ===========================================================================
# KOL: INDEX (COMMIT ANI) TARAMASI
# ===========================================================================
# 🔴 NEDEN VAR (olculdu 8-9 Agu 2026, BES KEZ tekrarlanan sinif): bu kapinin
# ZORLAYICI kolu CI'dadir ve CI yalniz PUSH'tan SONRA kosar. `bdddaee0`
# DEVAM.md:79'a bir E5 (kapi-bypass) satiri soktu; kapi dogru calisti, `serit-a2`
# VE `serit-a3` kirmizi yandi, `deploy`+`yayin` SKIPPED kaldi ve yayin ~1 SAAT
# durdu. Ihlal defterden cikarilinca kapi kendiliginden yesile dondu — yani
# maliyet ihlalin BUYUKLUGUNDEN degil YAKALANDIGI YERDEN geliyordu.
# Ayni sinif `bdddaee0`'de katalog alan kapisi icin de olculmustu: "kapilar
# YALNIZ CI'da yasiyordu -> yazim yolunda hicbir kol yoktu" (kancalar/pre-commit
# adim 5). Bu kol o adimin defter duzlemindeki esidir: ihlal COMMIT ANINDA durur,
# main'e HIC girmez, dolayisi ile yayini HIC durduramaz.
#
# ⚠️ CI KOLUNUN YERINE GECMEZ, ONUNDE DURUR. Kancalar commit EDILMEZ ve
# `--no-verify` ile atlanir; bu yuzden ZORLAYICI hukum `serit-a2`de KALIR
# (fail-open'a cevirme YOK, yalnizca daha erken ikinci bir kol).
#
# 🔴 EKSEN SECIMI — INDEX, CALISMA AGACI DEGIL ([[kanca-stage-disi-agaci-tarar]]):
# bu depoda BES ev ayni checkout'u paylasir. Calisma agacini yargilayan bir
# pre-commit kolu, BASKA bir oturumun yarim DEVAM.md taslagi yuzunden HERKESIN
# commit'ini kilitlerdi (olculmus zarar). Index ekseni yalnizca O COMMIT'in
# tasidigi icerigi yargilar: baskasinin kirli agaci kimseyi bloklamaz.
# ON-ELEME DE AYNI EKSENDEDIR (kabukta `git diff HEAD` ile elenmez) —
# [[kabul-araligi-karsilastirma-araligi]].
_BOS_AGAC = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _git(args, kok=None, ortam=None):
    """(rc, stdout_bytes, stderr). GERCEK YOLDA ORTAM TEMIZLENMEZ: kanca
    `GIT_INDEX_FILE` ihrac eder (`git commit <yol>` / `git commit -a` GECICI
    index kurar) ve kapi commit'in FIILEN tasidigi index'i olcmelidir
    (tools/katalog-alan-kapisi.py ile AYNI karar). <ortam> YALNIZ kabul
    bataryasinin SENTETIK depolari icindir: orada miras alinan GIT_DIR gercek
    depoyu isaret eder ve fikstur olcuLemez olurdu."""
    try:
        r = subprocess.run(["git", "-C", kok or ROOT] + list(args),
                           capture_output=True, env=ortam)
    except OSError as e:
        return 127, b"", "git calistirilamadi: %s" % e
    return r.returncode, r.stdout, r.stderr.decode("utf-8", "replace")


def _index_taban(kok=None, ortam=None):
    """Index'in karsilastirilacagi agac: HEAD varsa HEAD, yoksa BOS AGAC."""
    rc, _, _ = _git(["rev-parse", "--verify", "--quiet", "HEAD"], kok, ortam)
    return "HEAD" if rc == 0 else _BOS_AGAC


def index_kok_belgeleri(kosucu=None, kok=None, ortam=None):
    """(yollar, hata). INDEX'te EKLENEN/DEGISEN kok belgeleri (kapsam predikati
    IZLENEN kolla AYNI: `_kok_belge_mi`). Bos liste MESRU bir sonuctur (o commit
    kok defteri tasimiyor) — bu yuzden burada 'bos = OLCULEMEDI' KURALI YOKTUR;
    kolun canliligi `--kendini-test` I* iddialariyla DAVRANISSAL olcuLur."""
    if kosucu is None:
        def kosucu():
            return _git(["diff", "--cached", "--name-only",
                         "--diff-filter=ACMR", "-z",
                         _index_taban(kok, ortam)], kok, ortam)
    rc, cikti, hata = kosucu()
    if rc != 0:
        return None, ("git diff --cached basarisiz (rc=%s): %s"
                      % (rc, (hata or "").strip() or "?"))
    if isinstance(cikti, bytes):
        cikti = cikti.decode("utf-8", "replace")
    return sorted(y for y in cikti.split("\0") if y and _kok_belge_mi(y)), None


def index_metni(yol, kok=None, ortam=None):
    """(metin, hata). Icerik INDEX BLOB'undan okunur — calisma agacindan DEGIL.
    Ayristirilamayan blob YESIL DEGILDIR (fail-closed)."""
    rc, ham, hata = _git(["cat-file", "blob", ":" + yol], kok, ortam)
    if rc != 0:
        return None, ("index blob'u okunamadi (rc=%s): %s"
                      % (rc, (hata or "").strip() or "?"))
    try:
        return ham.decode("utf-8"), None
    except UnicodeDecodeError as e:
        return None, ("index blob'u UTF-8 olarak COZULEMEDI (%s) — icerik "
                      "ayristirilamayan bir dosya taranmis SAYILMAZ" % e)


def tara_index(kok=None, kosucu=None, ozet_yolu=None, sessiz=False, ortam=None):
    """(rc, bulgular, satir, taranan_yollar). COMMIT ANI kolu."""
    kok = kok or ROOT
    yollar, hata = index_kok_belgeleri(kosucu=kosucu, kok=kok, ortam=ortam)
    if yollar is None:
        if not sessiz:
            print("OLCULEMEDI (fail-closed KIRMIZI): %s" % hata, file=sys.stderr)
        return RC_OLCULEMEDI, [], 0, []
    if not yollar:
        # SESSIZ ATLAMA YOK: neden her seferinde basilir.
        if not sessiz:
            print("ATLANDI: bu commit'in INDEX'inde degisen KOK belge YOK "
                  "(on-eleme, index ekseni).")
        return RC_TEMIZ, [], 0, []

    ozet, ohata = ozet_modulu(ozet_yolu)
    if ozet is None:
        if not sessiz:
            print("OLCULEMEDI (fail-closed KIRMIZI): %s" % ohata, file=sys.stderr)
        return RC_OLCULEMEDI, [], 0, yollar
    kayit, khata = ozet.ozet_kaydi_yukle()
    if kayit is None:
        if not sessiz:
            print("OLCULEMEDI (fail-closed KIRMIZI): desen ozet artefakti — %s"
                  % khata, file=sys.stderr)
        return RC_OLCULEMEDI, [], 0, yollar
    try:
        markalar = ozet.katalog_markalari()
    except Exception:                                       # noqa: BLE001
        markalar = None

    bulgular = []
    satir_sayisi = 0
    for rel in yollar:
        metin, mhata = index_metni(rel, kok, ortam)
        if metin is None:
            if not sessiz:
                print("OLCULEMEDI (fail-closed KIRMIZI): %s — %s" % (rel, mhata),
                      file=sys.stderr)
            return RC_OLCULEMEDI, [], satir_sayisi, yollar
        satir_sayisi += len(metin.splitlines())
        for no, eksen, etiket in metin_bulgulari(metin, kayit, ozet, markalar):
            bulgular.append((rel, no, eksen, etiket))

    if not sessiz:
        print("INDEX kolu: %d kok belgesi · satir: %d" % (len(yollar), satir_sayisi))
        for rel, no, eksen, etiket in bulgular:
            print("  * SINIF IHLALI (INDEX): %s:%d — %s [%s]. Eslesen metin "
                  "BILEREK yazilmiyor." % (rel, no, eksen, etiket), file=sys.stderr)
        if bulgular:
            print("IHLAL: %d satir COMMIT'E GIRIYOR. COZUM: satirlari "
                  "DEVAM-ARSIV.md'ye (git DISI) TASI, yerine notr tek satirlik "
                  "isaretci birak. Silme YOK, tasima VAR." % len(bulgular),
                  file=sys.stderr)
        else:
            print("temiz: 0 sinif ihlali (index).")
    return ((RC_IHLAL if bulgular else RC_TEMIZ), bulgular, satir_sayisi, yollar)


# ===========================================================================
# KABUL BATARYASI
# ===========================================================================
# 🔴 FIKSTURLERDE GERCEK YASAKLI AD YOKTUR: E1 ekseni UYDURMA adlarla uretilmis
# GECICI bir ozet artefaktiyla olculur (uretim yolu da ayni kosumda sinanir).
_UYDURMA_AD = "Zorbacix"

# KIRMIZI fiksturler: her eksen icin en az bir SENTETIK hassas satir.
_KIRMIZI = [
    ("- Iskonto orani yuzde 22 olarak anlasildi.", "E2 oran-marj"),
    ("- Marj hesabi 1,35 katsayisiyla yapildi.", "E2 oran-marj"),
    ("- Aracilik marji islem basina 4500 TL; 12 adet uzerinden hesaplandi.",
     "E2 oran-marj"),                      # para boyutu > muhendislik kaniti
    ("- Anlasilan marj %18 seviyesinde tutuldu.", "E2 oran-marj"),   # % BOYUTSUZ
    ("- MARJ_ORANI=0.22 sabiti panelden okunuyor.", "E2 oran-marj"), # kod adi aklamaz
    ("- Iskonto 7 px kadar kucuk gorunse de uygulandi.", "E2 oran-marj"),
    # ^ TICARI konu, yanindaki muhendislik birimiyle AKLANAMAZ.
    ("- Kaynak kaydi .urun-kaynaklari.json dosyasinda tutuluyor.", "E3 gizli-dosya"),
    ("- Anahtarlar .r2-credentials.json icinde duruyor.", "E3 gizli-dosya"),
    ("- CLOUDFLARE_API_TOKEN degeri panelden alindi.", "E4 sir-jeton"),
    ("- Tuz degeri 37deae681fb6c8ab0832abe1e30f71c0 olarak sabit.", "E4 sir-jeton"),
    ("- Sir wrangler secret put ile yuklendi.", "E4 sir-jeton"),
    ("- Arac pre-push kancasina jetonsuz ve fail-open baglandi.", "E5 kapi-bypass"),
    ("- Acele push icin git push --no-verify kullanildi.", "E5 kapi-bypass"),
    ("- Kapi bypass yolu hala acik.", "E5 kapi-bypass"),
    ("- PRUVO_MUKERRER_ATLA=1 ile kapi atlanabiliyor.", "E5 kapi-bypass"),
    ("- core.hooksPath /dev/null yapilinca hicbir kanca kosmuyor.", "E5 kapi-bypass"),
    ("- Nobetci bu sinifi GORMEZ, kapsam disinda kaliyor.", "E5 kapi-bypass"),
    ("- Kapi bu ad halini KACIRDI.", "E5 kapi-bypass"),
    ("- Dosyanin kendi yorumlarinda iki gercek yasakli ad duz yaziliyordu.",
     "E6 guvenlik-bulgusu"),
    ("- Commit mesajlarinda satici kimligi vardi.", "E6 guvenlik-bulgusu"),
    ("- Duz merge kapatilan sizintiyi geri acardi.", "E6 guvenlik-bulgusu"),
    ("- Yorumlar ic arac adlarini ifsa ediyordu.", "E6 guvenlik-bulgusu"),
    ("- Bilgi PUBLIC repoya sizdi.", "E6 guvenlik-bulgusu"),
    # 🔴 IS-AKISI ADI MUAFIYETI — IKI YON DE VAKA (14 Agu 2026). Muafiyet, deponun KENDI
    # CI is akisi adini (`spec-ifsa-alarmi.yml` / "Spec/tasarim ifsasi alarmi") guvenlik
    # bulgusu sanan yanlis-pozitiften dogdu: kapi AYNI GUN DORT KEZ commit'i durdurdu.
    # TEK YON yazilsaydi (yalniz "muaf oldu mu") muafiyetin FAZLA GENISLEMESI gorunmez
    # kalirdi — ikinci vaka tam da onu olcer: gercek bir bulgu cumlesi KIRMIZI KALMALI.
    ("sunucu tarafinda ic rapor ifsa edildi", "E6 guvenlik-bulgusu"),
    # E1 ALAN ADI kolu: TANINMAYAN her alan adi kirmizidir (bicim kurali —
    # gizli vitrin/satici alan adi ADI HIC YAZILMADAN yakalanir). Ornek UYDURMA.
    # (`.example` UZANTI listesinde oldugu icin dosya adi sayilir -> gercek bir
    #  TLD ile yazilir; ad UYDURMADIR.)
    ("- Parcalar https://gizlivitrin.xyz/panel uzerinden alindi.",
     "E1 satici-kimligi"),
    ("- Sunucu fiyatlama fonksiyonu hala tur-KOR.", "E6 guvenlik-bulgusu"),
    ("- Bayat sepet satiri sunucuda hala fazla tahsil edilir.", "E6 guvenlik-bulgusu"),
]

# YESIL fiksturler: MESRU IS AKISI metni (kapi ADLARI, olcum sayilari, dal/SHA,
# kime ne is dustugu). Bunlarin yanmasi = herkesin `--no-verify` aliskanligi.
_YESIL = [
    "- Capa kalkani fail-closed: `7ef7427d`.",
    "- Nobetci desenine kelime siniri eklendi: `cbe6c2a6`.",
    "- Kapilar dalin agacinda: CI kapsami 143 kesif / 107 kosulan / 36 muaf.",
    "- Sizinti taramasi 1153 eklenen satirda 10 desen, 0 vurus.",
    "- Sizinti nobetcisi yesil; kapi envanteri 7/7.",
    "- Sizinti kapisi CI'da bloklayici seritte.",
    "- Kabul testi bagimsiz kosuldu: 14 vaka / 85 iddia / 0 kirmizi.",
    "- Dal main'e alindi: `364095f6` (ileri-sarma, taban `e84b2a65`).",
    "- Metin temizligi plani kardes mimara devredildi; teslim kardes mimarda.",
    "- Yayin suresi medyani 1296 saniye, MAD 115 saniye, 7 kosum.",
    "- D1 senkron teyidi: sayi ekseni 16.167 == 16.167; uyusmaz 0 / eksik 0 / fazla 0.",
    "- 200 TL taban tum urunlerde gecerli; parametrik sari seri haric.",
    "- Edge kartlarinda gosterim kismi fakat fail-closed.",
    "- Arama maliyet kapisi su an bloklamayan seritte; Serit A'ya tasima karari acik.",
    "- Mutasyon kopyada 3/3: kilit oldurulunce 4 iddia dustu.",
    "- Kapi envanteri 7/7; is akisi serit beyani 39.",
    "- Temizlik: worktree 5'ten 2'ye, yerel dal 16'dan 8'e indi.",
    "- Katalog: taban alti 0; D1 sayi ve hash ekseninde uyumlu.",
    "- Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).",
    "- Yedek 2645 dosya / 745824642 bayt; eksik 0, boyut farki 0.",
    "- Kosum `30678515290` (`86665da5`): envanter/build/deploy/yayin YESIL.",
    "- Vitrin https://pruvo3d.com uzerinden yayinlanir.",
    # 🔴 IS-AKISI ADI MUAFIYETI — IKI YON DE VAKA (14 Agu 2026). Muafiyet, deponun KENDI
    # CI is akisi adini (`spec-ifsa-alarmi.yml` / "Spec/tasarim ifsasi alarmi") guvenlik
    # bulgusu sanan yanlis-pozitiften dogdu: kapi AYNI GUN DORT KEZ commit'i durdurdu.
    # TEK YON yazilsaydi (yalniz "muaf oldu mu") muafiyetin FAZLA GENISLEMESI gorunmez
    # kalirdi — ikinci vaka tam da onu olcer: gercek bir bulgu cumlesi KIRMIZI KALMALI.
    "CI kosumu: Spec/tasarim ifsasi alarmi = success (spec-ifsa-alarmi.yml)",
    # --- 1 Agu: 6665 satirlik GERCEK arsiv korpusunda OLCULEN yanlis-pozitifler.
    # Ilk surumde bunlarin HEPSI yaniyordu; desenler daraltilarak kapatildi.
    "- `kisisel-veri-test.py` tedarikci-adi nobetcisi +104; git grep 0.",
    "- Satici adi kapisi 3 mutasyonla NOBETLI.",
    "- Merge kapisi: kapsam 5 dosya (+818/-35), sizinti yok, kabul 48/48.",
    "- Sizinti nobeti kosuldu; sizinti TEMIZ (desen 0 + elle gozden gecirme).",
    "- Sizinti taramasi 0 vurus; sizinti riski sifir.",
    "- GUVENLIK_MARJI=400 sabitiyle hizalandi; guvenlik marji 400 kaldi.",
    "- Canli panel http://localhost:8137 uzerinde kosuyor (launchd).",
    # --- 11 Agu: E2 BOYUT ekseni. Bu satirlar ESKI kuralda KIRMIZI yaniyordu.
    "- Masaustunde elde kalan marj ~%5 (~7 px); yerlesim toleransi.",
    "- CTA marji 12 px daraldi; esik 250 ms.",
    "- Ege tavan payi 400 karakter marjinda kaldi.",
    "- Genislik marji CTA-A1 ekseninde izlenecek.",   # rakam VAR, MIKTAR YOK
]


def _gecici_ozet(tmp, ozet, adlar=(_UYDURMA_AD,)):
    """UYDURMA adlarla GECICI bir ozet artefakti uretir (gercek uretim yolu)."""
    kaynak = os.path.join(tmp, "uydurma-desenler.txt")
    hedef = os.path.join(tmp, "uydurma-ozetler.json")
    with open(kaynak, "w", encoding="utf-8") as f:
        f.write("\n".join(adlar) + "\n")
    ozet.desen_yaz(kaynak=kaynak, hedef=hedef, dongu=ozet.ASGARI_DONGU)
    return hedef


def _sentetik_depo(t, ortam):
    """Ic hukmu OLMAYAN bos bir git deposu (kanca YOK, imza YOK)."""
    sentetik_git(t, "init", "-q", "-b", "main", capture_output=True,
                  kimlik_ad="Kapi Kabul Testi",
                  kimlik_eposta="kapi@ornek.gecersiz")
    for anahtar, deger in (("commit.gpgsign", "false"),
                           ("core.hooksPath", os.path.join(t, "kanca-yok"))):
        sentetik_git(t, "config", anahtar, deger, capture_output=True)


def _yaz_ekle(t, rel, icerik, ortam):
    tam = os.path.join(t, rel)
    if os.path.dirname(rel):
        os.makedirs(os.path.dirname(tam), exist_ok=True)
    if isinstance(icerik, bytes):
        with open(tam, "wb") as f:
            f.write(icerik)
    else:
        with open(tam, "w", encoding="utf-8") as f:
            f.write(icerik)
    _git(["add", "--", rel], t, ortam)


def _index_iddialari(ortam, ihlal_satiri, temiz_satiri):
    """[(ad, tamam_mi, gorulen), ...] — INDEX kolunun DAVRANIS iddialari."""
    sonuc = []

    def _kur(t):
        _sentetik_depo(t, ortam)
        _yaz_ekle(t, "README.md", "# depo\n", ortam)
        _yaz_ekle(t, "DEVAM.md", "# Defter\n" + temiz_satiri, ortam)
        sentetik_git(t, "commit", "-q", "-m", "ilk", capture_output=True,
                      ek_ortam=ortam)

    # I1 — INDEX'te ihlal COMMIT'I DURDURUR
    with tempfile.TemporaryDirectory() as t:
        _kur(t)
        _yaz_ekle(t, "DEVAM.md", "# Defter\n" + temiz_satiri + ihlal_satiri, ortam)
        rc, bulgular, _, yollar = tara_index(kok=t, sessiz=True, ortam=ortam)
        sonuc.append(("I1 index-ihlali-KIRMIZI", rc == RC_IHLAL and bool(bulgular),
                      "rc=%s bulgular=%r yollar=%r" % (rc, bulgular[:3], yollar)))

    # I2 — TEMIZ index YESIL ama FIILEN TARANMIS olmali (olu kol da yesil verir)
    with tempfile.TemporaryDirectory() as t:
        _kur(t)
        _yaz_ekle(t, "DEVAM.md", "# Defter\n" + temiz_satiri * 3, ortam)
        rc, bulgular, satir, yollar = tara_index(kok=t, sessiz=True, ortam=ortam)
        sonuc.append(("I2 temiz-index-TARANDI",
                      rc == RC_TEMIZ and yollar == ["DEVAM.md"] and satir >= 4,
                      "rc=%s satir=%s yollar=%r" % (rc, satir, yollar)))

    # I3 — EKSEN INDEX'TIR: baskasinin KIRLI calisma agaci commit'i KILITLEMEZ
    #      ([[kanca-stage-disi-agaci-tarar]]). Ayirt edici: index temiz, agac ihlalli.
    with tempfile.TemporaryDirectory() as t:
        _kur(t)
        _yaz_ekle(t, "DEVAM.md", "# Defter\n" + temiz_satiri * 2, ortam)
        with open(os.path.join(t, "DEVAM.md"), "a", encoding="utf-8") as f:
            f.write(ihlal_satiri)                    # STAGE EDILMEDI
        rc, bulgular, _, yollar = tara_index(kok=t, sessiz=True, ortam=ortam)
        sonuc.append(("I3 eksen-INDEX-agac-degil",
                      rc == RC_TEMIZ and yollar == ["DEVAM.md"],
                      "rc=%s bulgular=%r yollar=%r" % (rc, bulgular[:3], yollar)))

    # I4 — KAPSAM: alt dizindeki belge KOK defteri DEGILDIR (izlenen kolla ayni kural)
    with tempfile.TemporaryDirectory() as t:
        _kur(t)
        _yaz_ekle(t, "belge/NOT.md", "# not\n" + ihlal_satiri, ortam)
        rc, _, _, yollar = tara_index(kok=t, sessiz=True, ortam=ortam)
        sonuc.append(("I4 kapsam-alt-dizin-DISARIDA",
                      rc == RC_TEMIZ and yollar == [],
                      "rc=%s yollar=%r" % (rc, yollar)))

    # I5 — AD-BAGIMSIZ: YENI bir kok defteri kapsama KENDILIGINDEN girer
    #      (muafiyet/allow listesi YOK -> [[envanter-drift-parti-basina]])
    with tempfile.TemporaryDirectory() as t:
        _kur(t)
        _yaz_ekle(t, "NOTLAR.md", "# yeni defter\n" + ihlal_satiri, ortam)
        rc, _, _, yollar = tara_index(kok=t, sessiz=True, ortam=ortam)
        sonuc.append(("I5 yeni-kok-defteri-KIRMIZI",
                      rc == RC_IHLAL and yollar == ["NOTLAR.md"],
                      "rc=%s yollar=%r" % (rc, yollar)))

    # I6 — FAIL-CLOSED: git kapsam komutu dusrse YESIL VERILMEZ
    rc, _, _, _ = tara_index(kok=ROOT, sessiz=True, ortam=ortam,
                             kosucu=lambda: (128, b"", "fatal"))
    sonuc.append(("I6 git-dustu-OLCULEMEDI", rc == RC_OLCULEMEDI, "rc=%s" % rc))

    # I7 — FAIL-CLOSED: index blob'u UTF-8 degilse YESIL VERILMEZ
    with tempfile.TemporaryDirectory() as t:
        _kur(t)
        _yaz_ekle(t, "DEVAM.md", b"# Defter\ngecerli\n\xff\xfe\x00 bozuk\n", ortam)
        rc, _, _, _ = tara_index(kok=t, sessiz=True, ortam=ortam)
        sonuc.append(("I7 bozuk-blob-OLCULEMEDI", rc == RC_OLCULEMEDI, "rc=%s" % rc))

    return sonuc


def kendini_test():
    hatalar = []
    kontrol = 0

    ozet, hata = ozet_modulu()
    if ozet is None:
        print("A0 OLCULEMEDI: %s" % hata, file=sys.stderr)
        return 1
    kayit, khata = ozet.ozet_kaydi_yukle()
    if kayit is None:
        print("A0 OLCULEMEDI: %s" % khata, file=sys.stderr)
        return 1
    try:
        markalar = ozet.katalog_markalari()
    except Exception:                                       # noqa: BLE001
        markalar = None

    def _eksenler(satir):
        return {e for e, _ in satir_eksenleri(satir, ozet.normalize(satir),
                                              kayit, ozet, markalar)}

    # ---- A) KIRMIZI FIKSTURLER: her sentetik hassas satir YAKALANMALI
    for satir, beklenen in _KIRMIZI:
        kontrol += 1
        bulunan = _eksenler(satir)
        if beklenen not in bulunan:
            hatalar.append("A KIRMIZI KACTI (%s beklendi, bulunan %s): %r"
                           % (beklenen, sorted(bulunan) or "YOK", satir))

    # ---- B) YESIL FIKSTURLER: mesru is akisi metni YANMAMALI
    for satir in _YESIL:
        kontrol += 1
        bulunan = _eksenler(satir)
        if bulunan:
            hatalar.append("B YANLIS-POZITIF (desen DARALTILMALI) -> %s: %r"
                           % (sorted(bulunan), satir))

    # ---- A2) DONMUS KELIME MUAFIYETI BUYUYEMEZ ([[envanter-drift-parti-basina]])
    kontrol += 1
    if E2_DONMUS_ONEKLER != ("guvenlik",):
        hatalar.append("A2 DONMUS MUAFIYET DEGISTI -> %r. Yeni muhendislik marji "
                       "BOYUT eksenine (E2_BIRIM) girer, kelime listesine DEGIL."
                       % (E2_DONMUS_ONEKLER,))

    # ---- A3) IKIZ VAKA: iki satir arasindaki TEK fark BIRIMDIR. Hukum kelimeden
    #      degil BOYUTTAN geliyorsa bu uclu ayrisir ([[kabul-araligi-karsilastirma-araligi]]).
    for satir, kirmizi_beklenen in (
            ("- Elde kalan marj 7 px olarak olculdu.", False),
            ("- Elde kalan marj 7 TL olarak olculdu.", True),
            ("- Elde kalan marj 7 olarak olculdu.", True)):
        kontrol += 1
        kirmizi = "E2 oran-marj" in _eksenler(satir)
        if kirmizi != kirmizi_beklenen:
            hatalar.append("A3 IKIZ VAKA: %r -> %s (beklenen %s)"
                           % (satir, "KIRMIZI" if kirmizi else "YESIL",
                              "KIRMIZI" if kirmizi_beklenen else "YESIL"))

    # ---- C) E1: OZET MEKANIZMASI CANLI MI (uydurma ad + gercek uretim yolu)
    with tempfile.TemporaryDirectory() as tmp:
        sahte_yol = _gecici_ozet(tmp, ozet)
        sahte, shata = ozet.ozet_kaydi_yukle(sahte_yol)
        kontrol += 1
        if sahte is None:
            hatalar.append("C GECICI OZET URETILEMEDI: %s" % shata)
        else:
            kontrol += 3
            satir = "- Parca %s tedarikcisinden alindi." % _UYDURMA_AD
            bulunan = {e for e, _ in satir_eksenleri(
                satir, ozet.normalize(satir), sahte, ozet, markalar)}
            if "E1 satici-kimligi" not in bulunan:
                hatalar.append("C E1 (satir kolu) OLU: uydurma ad ozet "
                               "mekanizmasiyla YAKALANMADI -> %s" % sorted(bulunan))
            # 🔴 TOPLU KOL AYRI OLCULUR: gercek tarama _ad_ekseni_toplu()'yu
            # kullanir; satir kolu saglamken toplu kol olduruLURSE kapi sessizce
            # kor kalirdi (iki kod yolu, tek iddia = nobetsiz kol).
            belge = "# Defter\n- notr satir\n%s\n- baska notr satir\n" % satir
            toplu = metin_bulgulari(belge, sahte, ozet, markalar)
            if not any(e == "E1 satici-kimligi" and no == 3
                       for no, e, _ in toplu):
                hatalar.append("C E1 (TOPLU kol) OLU: uydurma ad belge ekseninde "
                               "3. satirda YAKALANMADI -> %r" % toplu)
            temiz = "- Dal main'e alindi: `364095f6`."
            bulunan2 = {e for e, _ in satir_eksenleri(
                temiz, ozet.normalize(temiz), sahte, ozet, markalar)}
            if "E1 satici-kimligi" in bulunan2:
                hatalar.append("C E1 YANLIS-POZITIF: notr satirda ad isabeti")

    # ---- D) FAIL-CLOSED: desen kaynagi YOKKEN yesil VERILMEZ
    with tempfile.TemporaryDirectory() as tmp:
        kontrol += 1
        rc, _, _ = tara(kok=ROOT, dosyalar=[os.path.join(tmp, "bos.md")],
                        ozet_yolu=os.path.join(tmp, "yok-boyle-bir-dosya.py"),
                        sessiz=True)
        if rc != RC_OLCULEMEDI:
            hatalar.append("D FAIL-CLOSED OLDU: desen kaynagi YOKKEN rc=%d "
                           "(2 bekleniyordu)" % rc)

    # ---- E) FAIL-CLOSED: dosya AYRISTIRILAMIYORSA yesil VERILMEZ
    with tempfile.TemporaryDirectory() as tmp:
        kontrol += 1
        bozuk = os.path.join(tmp, "bozuk.md")
        with open(bozuk, "wb") as f:
            f.write(b"gecerli satir\n\xff\xfe\x00 bozuk bayt\n")
        rc, _, _ = tara(kok=ROOT, dosyalar=[bozuk], sessiz=True)
        if rc != RC_OLCULEMEDI:
            hatalar.append("E FAIL-CLOSED OLDU: UTF-8 cozulemeyen dosyada rc=%d "
                           "(2 bekleniyordu)" % rc)

    # ---- F) CANLILIK: git rc=0 + BOS / KISMI liste -> OLCULEMEDI
    for ad, cikti in (("BOS", ""),
                      ("KISMI", "\0".join(["README.md", "index.html"]))):
        kontrol += 1
        yollar, hata = izlenen_kok_belgeleri(kosucu=lambda c=cikti: (0, c, ""))
        if yollar is not None:
            hatalar.append("F CANLILIK OLDU: %s listede kapsam kabul edildi -> %r"
                           % (ad, yollar))
    kontrol += 1
    yollar, _ = izlenen_kok_belgeleri(
        kosucu=lambda: (0, "\0".join(["README.md", "DEVAM.md", KAPI_YOLU]), ""))
    if yollar != ["DEVAM.md", "README.md"]:
        hatalar.append("F CANLILIK YANLIS-POZITIF: normal listede kapsam %r" % yollar)
    kontrol += 1
    yollar, _ = izlenen_kok_belgeleri(kosucu=lambda: (128, "", "fatal"))
    if yollar is not None:
        hatalar.append("F FAIL-LOUD OLDU: git rc!=0 iken kapsam dondu")

    # ---- G) GERCEK DOSYALAR: bugunku izlenen kok defterleri TEMIZ olmali
    #      (yanlis-pozitif butcesinin GERCEK olcumu — fikstur degil)
    kontrol += 1
    rc, bulgular, satir = tara(sessiz=True)
    if rc == RC_OLCULEMEDI:
        hatalar.append("G GERCEK TARAMA OLCULEMEDI")
    elif rc != RC_TEMIZ:
        hatalar.append("G GERCEK IZLENEN KOK BELGELERINDE %d SINIF IHLALI VAR "
                       "(tasinmasi gereken satirlar): %r"
                       % (len(bulgular), bulgular[:8]))
    print("gercek kapsam: %d satir tarandi, %d ihlal" % (satir, len(bulgular)))

    # ---- I) INDEX (COMMIT ANI) KOLU — DAVRANISSAL, SENTETIK DEPO UZERINDE
    #      🔴 BEYAN DEGIL DAVRANIS ([[kapi-beyanin-dogrulugunu-degil-varligini-olcer]]):
    #      "kola index ekseni eklendi" beyani kolun FIILEN gordugunu kanitlamaz.
    #      Olu bir kol (bozuk --diff-filter, yanlis kapsam predikati, index yerine
    #      calisma agacini okumak) HER durumda "degisen kok belge YOK" der ve
    #      SESSIZ YESIL verir. Asagidaki iddialar o sessiz yesili KIRMIZI yakar.
    ortam_fn, ohata = _git_ortami_modulu()
    kontrol += 1
    if ortam_fn is None:
        hatalar.append("I OLCULEMEDI: %s" % ohata)
    else:
        ihlal_satiri = "- Acele push icin git push --no-verify kullanildi.\n"
        temiz_satiri = "- Dal main'e alindi: `364095f6` (ileri-sarma).\n"
        sonuc = _index_iddialari(ortam_fn(), ihlal_satiri, temiz_satiri)
        for ad, tamam, gorulen in sonuc:
            kontrol += 1
            if not tamam:
                hatalar.append("I %s -> %s" % (ad, gorulen))

    # ---- H) YANLIS-POZITIF BUTCESI: DEVAM-ARSIV.md (git DISI) kapsam DISIDIR
    arsiv = os.path.join(ROOT, "DEVAM-ARSIV.md")
    if os.path.isfile(arsiv):
        kontrol += 1
        yollar, _ = izlenen_kok_belgeleri()
        if yollar and "DEVAM-ARSIV.md" in yollar:
            hatalar.append("H KAPSAM HATASI: DEVAM-ARSIV.md git DISI olmali ama "
                           "izlenen kok belgeleri arasinda gorundu")

    for h in hatalar:
        print("  ✗ %s" % h, file=sys.stderr)
    print("kendini-test: %d kontrol · %d hata" % (kontrol, len(hatalar)))
    return 1 if hatalar else 0


# ===========================================================================
# MUTASYON BATARYASI — KOPYA UZERINDE (canli dosyada mutant BIRAKILMAZ)
# ===========================================================================
_MUTANTLAR = [
    ("M1 E2 ticari konuyu oldur", "E2_TICARI_KONU = re.compile(",
     'E2_TICARI_KONU = re.compile(r"(?!x)x")  #', True),
    ("M2 E3 oldur", "E3_DESENLER = (", "E3_DESENLER = ()  # ", True),
    ("M3 E4 hex esigi gevset",
     r'r"(?<![0-9A-Za-z])[0-9a-fA-F]{32,}(?![0-9A-Za-z])"',
     r'r"(?<![0-9A-Za-z])[0-9a-fA-F]{999,}(?![0-9A-Za-z])"', True),
    ("M4 E5 desenleri oldur", "E5_DESENLER = (", "E5_DESENLER = ()  # ", True),
    ("M5 E5 korluk ekseni oldur", "E5_KORLUK = re.compile(",
     'E5_KORLUK = re.compile(r"(?!x)x")  #', True),
    ("M6 E6 desenleri oldur", "E6_DESENLER = (", "E6_DESENLER = ()  # ", True),
    ("M7 E6 sunucu-istismar ekseni oldur", "E6_ISTISMAR = re.compile(",
     'E6_ISTISMAR = re.compile(r"(?!x)x")  #', True),
    ("M8 E1 satir kolunu oldur",
     "            for no, _n in ozet.ad_isabetleri(ham, kayit):",
     "            for no, _n in []:", True),
    ("M8b E1 TOPLU kolunu oldur",
     "        anahtar = (n, ozet._ozetle(aday, kayit[\"tuz\"], kayit[\"dongu\"]))",
     "        anahtar = (n, \"0\" * 64)", True),
    ("M8c E1 alan adi kolunu oldur",
     "                for kusur in ozet.alan_adi_isabetleri(ham, kayit, markalar):",
     "                for kusur in []:", True),
    ("M8d E1 yerel-uc istisnasini genislet", "_YEREL_UC = re.compile(",
     '_YEREL_UC = re.compile(r".")  #', True),
    ("M9 fail-closed'u sessiz yesile cevir",
     "        return RC_OLCULEMEDI, [], 0\n    kayit, khata",
     "        return RC_TEMIZ, [], 0\n    kayit, khata", True),
    ("M10 canlilik nobetini oldur", "    if KAPI_YOLU not in hepsi:",
     "    if False:", True),
    # --- INDEX (commit ani) kolunun OLDURUCU mutantlari -----------------------
    ("M13 INDEX kolunu KOR ET (kapsam predikati)",
     "    return sorted(y for y in cikti.split(\"\\0\") if y and _kok_belge_mi(y))",
     "    return sorted(y for y in cikti.split(\"\\0\") if False)", True),
    ("M14 INDEX kolunu CALISMA AGACINA cevir",
     "        metin, mhata = index_metni(rel, kok, ortam)",
     "        metin, mhata = dosya_metni(os.path.join(kok, rel))", True),
    ("M15 INDEX kapsam fail-closed'unu sessiz yesile cevir",
     "        return RC_OLCULEMEDI, [], 0, []",
     "        return RC_TEMIZ, [], 0, []", True),
    ("M16 INDEX blob fail-closed'unu sessiz yesile cevir",
     "            return RC_OLCULEMEDI, [], satir_sayisi, yollar",
     "            return RC_TEMIZ, [], satir_sayisi, yollar", True),
    ("M17 E2 boyut ekseni OLDUR", "E2_BIRIM = re.compile(",
     'E2_BIRIM = re.compile(r"(?!x)x")  #', True),
    ("M18 E2 boyut ekseni SINIRSIZ GENISLET", "E2_BIRIM = re.compile(",
     'E2_BIRIM = re.compile(r"")  #', True),
    ("M19 E2 para ustunlugunu OLDUR", "E2_PARA = re.compile(",
     'E2_PARA = re.compile(r"(?!x)x")  #', True),
    ("M20 E2 miktarini `herhangi bir rakam`a geri al", "E2_SAYI = re.compile(",
     'E2_SAYI = re.compile(r"\\d")  #', True),
    ("M21 belirsiz konuyu TICARI say",
     '    if not E2_BELIRSIZ_KONU.search(E2_DONMUS.sub(" ", norm)):\n        return None',
     '    if E2_BELIRSIZ_KONU.search(norm):\n        return "ticari-konu+miktar"', True),
    ("M22 DONMUS muafiyeti BUYUT", 'E2_DONMUS_ONEKLER = ("guvenlik",)',
     'E2_DONMUS_ONEKLER = ("guvenlik", "yerlesim", "genislik")', True),
    ("M11 ILGISIZ: yorum satiri eklendi", "import argparse",
     "import argparse  # ilgisiz yorum (davranis degismez)", False),
    ("M12 ILGISIZ: cikti metni degistirildi", '"temiz: 0 sinif ihlali."',
     '"temiz: sifir sinif ihlali."', False),
]


def _sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def mutasyon():
    kaynak = os.path.abspath(__file__)
    once = _sha256(kaynak)
    with open(kaynak, encoding="utf-8") as f:
        govde = f.read()

    # 🔴 KOSUM ORTAMI (olculdu, [[anahat-referans-tautolojisi]]): mutant kopyasi
    # GECICI bir dizinde YAZILIR ve subprocess cwd=tmp'de calisir; kopyanin
    # KENDI dizini Python'un sys.path[0]'u olur. Dosyanin en ustundeki
    # `from git_ortami import sentetik_git` (plain import) bu yuzden GERCEK
    # tools/git_ortami.py'yi bulamaz -> ModuleNotFoundError. Bu cokme
    # MUTASYONDAN BAGIMSIZDIR (HER kopyayi ayni sekilde cokertir) ve "olcemedim"i
    # "oldurdum" ile KARISTIRIR — [[mutasyon-kaniti-yeniden-uretilebilir]].
    # Cozum: subprocess'e GERCEK tools/ dizinini iceren bir PYTHONPATH ver
    # (--kok GERCEK depoyu gosterdigi gibi PYTHONPATH da GERCEK tools/'u
    # gostersin).
    ortam = dict(os.environ)
    ortam["PYTHONPATH"] = os.pathsep.join(
        [TOOLS] + ([ortam["PYTHONPATH"]] if ortam.get("PYTHONPATH") else []))

    def _kendini_test_kostur(icerik, dizin):
        mutant_yol = os.path.join(dizin, "mutant-devam-sinif-kapisi.py")
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(icerik)
        return subprocess.run([sys.executable, mutant_yol, "--kendini-test",
                               "--kok", ROOT],
                              capture_output=True, text=True, cwd=dizin,
                              env=ortam)

    hatalar = []
    # 🔴 CANLILIK CAPASI: mutasyon uygulamadan ONCE MUTASYONSUZ kopyayi (govde
    # AYNEN, hicbir replace YOK) TAM AYNI kosum yolundan gecir. Bu kirmizi
    # cikarsa "yanlis dizindeyim / import cozulmedi" ile "oldurdum" AYIRT
    # EDILEMEZ -> batarya TAUTOLOJIKTIR ve asagidaki TUM mutant sonuclari
    # GUVENILMEZ sayilir (kosulmaz, tek hata olarak raporlanir).
    with tempfile.TemporaryDirectory() as tmp0:
        r0 = _kendini_test_kostur(govde, tmp0)
    canlilik_tamam = (r0.returncode == 0)
    print("MUTASYONSUZ KOPYA CANLILIK KONTROLU: %s (rc=%d)"
          % ("YESIL" if canlilik_tamam else "KIRMIZI", r0.returncode))
    if not canlilik_tamam:
        hatalar.append(
            "KOSUM ORTAMI BOZUK — mutasyonsuz kopya bile kirmizi (batarya "
            "TAUTOLOJIK): rc=%d\n%s" % (r0.returncode, r0.stderr[-400:]))
        print("ATLANDI: kosum ortami bozukken mutant sonuclari GUVENILMEZ "
              "sayilir (yukaridaki canlilik kontrolune bak).", file=sys.stderr)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            # Mutant AYRI bir dizinde kosar (canli dosyaya DOKUNULMAZ) ama --kok
            # ile GERCEK depoyu olcer; boylece kirmizi/yesil hukmu MUTASYONDAN
            # gelir, "yanlis dizinde kostum"dan degil (yukaridaki canlilik
            # kontrolu + PYTHONPATH bunu GARANTI eder).
            for ad, eski, yeni, oldurucu in _MUTANTLAR:
                if eski not in govde:
                    hatalar.append("%s: BAYAT MUTANT — capa metni bulunamadi: %r"
                                   % (ad, eski[:48]))
                    continue
                r = _kendini_test_kostur(govde.replace(eski, yeni, 1), tmp)
                kirmizi = (r.returncode != 0)
                if oldurucu and not kirmizi:
                    hatalar.append("%s: OLDURUCU MUTANT HAYATTA KALDI (rc=0) — o "
                                   "eksen NOBETSIZ" % ad)
                if (not oldurucu) and kirmizi:
                    hatalar.append("%s: ILGISIZ DEGISIKLIK KIRMIZI YANDI (rc=%d) — "
                                   "kapi asiri hassas\n%s"
                                   % (ad, r.returncode, r.stderr[-400:]))
                print("  %-40s -> %s (%s)"
                      % (ad, "KIRMIZI" if kirmizi else "YESIL",
                         "oldurucu" if oldurucu else "ilgisiz"))
    sonra = _sha256(kaynak)
    if once != sonra:
        hatalar.append("CANLI DOSYA DEGISTI! sha256 %s -> %s (mutant sizdi)"
                       % (once[:12], sonra[:12]))
    print("canli dosya sha256 esitligi: %s (%s)"
          % ("TAM" if once == sonra else "BOZUK", once[:16]))
    for h in hatalar:
        print("  ✗ %s" % h, file=sys.stderr)
    print("mutasyon: %d mutant · %d hata" % (len(_MUTANTLAR), len(hatalar)))
    return 1 if hatalar else 0


# ===========================================================================
def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kendini-test", action="store_true")
    p.add_argument("--mutasyon", action="store_true")
    p.add_argument("--dosya", action="append", default=None,
                   help="tek dosya tara (tani/fikstur); tekrarlanabilir")
    # --index: COMMIT ANI kolu (tools/kancalar/pre-commit adim 6). CI'da BILEREK
    # kosmaz — taze bir CI checkout'unda index HEAD ile aynidir, yani olcecek
    # STAGED icerik YOKTUR ve kol her seferinde "ATLANDI" derdi (sessiz yesil
    # yuzeyi). CI'daki ZORLAYICI hukum bayraksiz kol (`serit-a2`) + bu kolun
    # DAVRANISSAL kabul iddialari (`--kendini-test` I1..I7, `serit-a3`).
    p.add_argument("--index", action="store_true",
                   help="INDEX'te (staged) degisen kok belgelerini tara")
    # --kok: betik BASKA bir yerde dursa da GERCEK depoyu olcsun. MUTASYON
    # BATARYASI icin ZORUNLU: mutant kopya gecici bir dizinde kosar; --kok
    # olmadan kapsam olcumu o gecici dizinde OLCULEMEDI'ye duser ve HER mutant
    # (oldurucu olmayan dahil) kirmizi yanar -> mutasyon TAUTOLOJIYE doner
    # ("oldurdum" degil "yanlis dizindeyim" olculur). Olculdu: --kok'suz ilk
    # kosumda 12/12 mutant kirmizi, 2 ilgisiz mutant da dahil.
    p.add_argument("--kok", default=None,
                   help="olculecek depo koku (varsayilan: betigin ust dizini)")
    a = p.parse_args(argv)
    if a.kok:
        global ROOT, TOOLS
        ROOT = os.path.abspath(a.kok)
        TOOLS = os.path.join(ROOT, "tools")
    if a.kendini_test:
        return kendini_test()
    if a.mutasyon:
        return mutasyon()
    if a.index:
        rc, _, _, _ = tara_index()
        return rc
    rc, _, _ = tara(dosyalar=a.dosya)
    return rc


if __name__ == "__main__":
    sys.exit(main())
