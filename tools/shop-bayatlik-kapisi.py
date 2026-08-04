#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SHOP BAYATLIK KAPISI — "canli odeme worker'i main'in KAC COMMIT gerisinde?"

NEDEN VAR (OLCULDU 3 Agu 2026 — bu nobetci bir olayin faturasidir)
==================================================================
`deploy.yml`de `wrangler deploy|publish` VURUS SAYISI = 0. shop Worker'i CI'da HIC
yayinlanmiyor; her `shop/src` degisikligi elle `wrangler deploy` bekliyor ve BEKLERKEN
HICBIR ALARM CALMIYOR. Olculen sonuc: canli bundle 13 sa 15 dk bayat kaldi — main yesil,
CI yesil, site taze, ama ODEME YOLU ESKI KODU KOSUYORDU. 3 Agu 13:22Z'de elle deploy
edildi (surum cecc9d4f); MEKANIZMA yoktu.

Ayni sinif bu depoda EN AZ UC KEZ tekrarladi ve her seferinde PARA/SATIS maliyeti oldu:
  30 Tem  worker yayinlanmamis -> kart kanali 2 gun kapali;
  30 Tem 20:30 - 1 Agu 01:58 (14,5 sa) -> 676 fiziksel uruntte carpan hala uygulaniyor,
                 16.400 TL'lik parca icin canli uc 30.176,00 TL dondu (%84 fazla tahsilat);
  3 Agu   13 sa 15 dk bayat bundle.
Tekrar eden, YAPISAL bir delik: yayin adimi CI'da olmadigi surece bayatlik geri gelir.
`tools/fiziksel-canli-kapisi.py` bunun TEK BIR eksenini (fiziksel carpan) canlida olcer;
bu kapi NESIL sorusunu genel olarak sorar: canli bundle hangi surumu tasiyor ve depo
HEAD'i o surumden kac commit ileride.

🔴 OLCUM KAYNAGI — UC ADAY OLCULDU, BIRI SECILDI (3 Agu 2026)
=============================================================
A) CANLI BUNDLE'DAN DAVRANISSAL IMZA (uc'a istek atip cevabi kiyasla)
   Olculdu: worker'in TEK genel yuzeyi `/api/shop/*` ve HICBIR ucu surum/nesil BILDIRMIYOR
   (`curl -D -` : cf-ray disinda ayirt edici bassik yok; `/donus` 400 doner). Nesil ancak
   DEGISEN DAVRANIS uzerinden anlasilir -> her yeni commit icin ELLE yeni prova yazmak
   gerekir. Kapsam commit basina el emegine baglanir ve YENI degisiklikte SESSIZCE korlesir
   (tam da kapatmaya calistigimiz sinif). Bu kanal ZATEN VAR ve dar bir eksende kosuyor
   (fiziksel-canli-kapisi A/B/C/D iddialari) — genel nesil olcumu icin ELENDI.
B) BUNDLE'A GOMULU SURUM DAMGASI (kaynaga sha/commit yazip ucdan okumak)
   En kesin kimlik: canli bundle'in HANGI COMMIT oldugunu birebir soyler. ELENME SEBEBI
   OLCULDU: damga ancak DEPLOY EDILDIKTEN sonra canlanir; bu turda `wrangler deploy`
   KOSULMUYOR (yayin karari mimarda) -> kapi main'in BUGUNKU halinde ilk gunden KIRMIZI
   yanardi. "Uc 404 verirse yesil say" ise fail-open olurdu. Yani bu kanal bir DEPLOY
   penceresi gerektiriyor; ONERI olarak raporda durur, bugun kablolanamaz.
C) `wrangler deployments|versions list --json`  ← SECILDI
   Olculdu (3 Agu, yerel OAuth): ikisi de rc 0, makine-okunur JSON, aktif dagitim +
   %100 surum + `created_on` + `annotations["workers/triggered_by"]` verir. Kaynaga
   DOKUNMAZ (baska muhendislerin duzlemi guvende), deploy GEREKTIRMEZ, BUGUN olcer.
   YANLIS-POZITIF BUTCESI en dusuk olan kanal budur: hukum tek bir zaman damgasi ile
   commit zamanlarinin karsilastirilmasidir, ag'a bagimli ikinci bir yorum katmani yok.

   🔴 BU KANALIN OLCULEN TUZAGI — `wrangler secret put` NESLI TAZE GOSTERIR:
   secret degisimi KOD DEGISMEDEN yeni bir surum + yeni bir dagitim dogurur. Olculen
   ornek: 2 Agu 07:39:07Z surum 9d5ab6ed `triggered_by=secret`; ayni bundle'in KOD surumu
   50686981, 07:20:04Z. Naif "en yeni dagitim zamani" hukmu o anda 19 dk taze gosterirdi;
   secret degisimi gunlerce sonra yapilirsa maskeleme GUNLERCE surer. Bu yuzden KOD ZAMANI
   `triggered_by == "secret"` surumleri ATLANARAK, aktif surumden GERIYE dogru bulunur.
   Kabul testi C2 tam bu vakayi civiler; mutant M3 onu kirmizi yakar.

   BILINEN SINIRI (durust beyan): bu kanal "canli bundle hangi COMMIT" sorusuna ZAMAN
   uzerinden cevap verir. Bayat bir CALISMA AGACINDAN yapilan deploy (eski agac, yeni
   saat) TAZE gorunur — o hali ancak (B) kanali yakalar. Bu delik OLCULMUS degil
   VARSAYILAN bir risktir; kapatmasi deploy ritueline damga eklemekten gecer.

🔴 ESIK: 120 DAKIKA — GEREKCE OLCUMDEN GELIR, YUVARLAK SAYIDAN DEGIL
====================================================================
Olculdu (3 Agu; 20 Tem'den beri bundle'i etkileyen 73 commit x canli deploy gecmisi):
commit -> ILK SONRAKI kod deploy'u gecikmesi  N=73  min 1,9 dk · medyan 1.339,6 dk
(22,3 sa) · maks 13.198,7 dk (9,2 gun). MEDYAN HASTALIGIN KENDISIDIR, olcut olamaz.
Olcut, deploy'un FIILEN ayni oturumda yapildigi vakalarin ust siniridir:
    1,9 · 7,8 · 13,9 · 34,4 · 65,1 · 70,5 · 78,4 · 89,2 dk  (olculen "ayni oturum" kumesi)
ESIK bu kumenin en buyugunun (89,2) USTUNDE, olay penceresinin (795 dk = 13 sa 15 dk)
COK ALTINDA secildi: 120 dk. Sonuc: 8/8 saglikli deploy YANLIS ALARM URETMEZ, 3 Agu olayi
esigi 6,6 KAT asar (795/120) ve 2 saat icinde yakalanirdi.
ESIGI IKI YONDE DE NOBET ALTINDA: kabul testi D2 (119 dk -> bekliyor) ve D3 (121 dk ->
bayat) fiksturleri esigi ASAGI cekmeyi de YUKARI cekmeyi de KIRMIZI yakar; tek yonlu
nobetci bu depoda daha once isirdi ([[kapi-kapsam-eksen-secimi]]).

🔴 UC HAL + BIR HAL DAHA — "OLCULEMEDI" ASLA YESIL DEGIL
========================================================
    durum=taze       rc 0  canli kod surumu, bundle'i etkileyen TUM commit'lerden yeni.
    durum=bekliyor   rc 0  geride ama en eski yayinlanmamis commit ESIK'ten GENC (deploy
                           penceresi). BEYAN EDILMIS tolerans; sayi DAIMA basilir.
    durum=bayat      rc 1  geride VE en eski yayinlanmamis commit ESIK'ten YASLI.
    durum=olculemedi rc 2  ag/yetki/bicim/gecmis yetersiz VEYA olculen ref'in olculmesi
                           GEREKEN ref oldugu kanitlanamadi. SESSIZ YESIL YOKTUR:
                           "guncel" varsayimina DUSMEZ, kosum kirmizi yanar.

🔴 OLCULEN REF = OLCULMESI GEREKEN REF (4 Agu 2026 sorusturmasinin urunu)
========================================================================
KAPI HANGI GECMISI SORUYOR: `git log` DAIMA `ROOT`un HEAD'i uzerinde kosar, ama hukmun
anlami "uzak main ucundaki kod canliya inmis mi"dir. Ikisi ayrisirsa kapi SESSIZCE yanlis
soruyu cevaplar. OLCULDU (gecici tam klon, sig DEGIL; olcum betigi rapordadir):
    HEAD uzak ucun BIR commit gerisinde  -> `git log --since` 0 kayit -> "taze", 0,0 dk, rc 0
    ayni depo, HEAD uc'ta (TEK degisken) -> 1 kayit                 -> "bayat", 360,0 dk, rc 1
Yani bayat bir HEAD (worktree dali, detached, itilmemis/geride agac) SAHTE TAZE uretiyordu
ve bunun disaridan gorunen imzasi tam olarak `yas = 0,0 dk`ydi — `hukum()` 0,0'i YALNIZ
`geride` kumesi BOS iken dondurur. `gecmisi_yeterince_ac()` bu deligi KAPATMIYORDU: tam
klonda `--is-shallow-repository == false` gorup HEMEN `True` doner, yani "gecmis yeterli
mi" sorusunu DERINLIK ile olcer, GUNCELLIK ile degil (ayni fikstur: HEAD geride iken de
`True` dondu).
DUZELTME (fail-closed): `olculen_ref_dogrula()` HEAD'in uzak main ucu oldugunu KANIT ister.
Aday ucler: `refs/remotes/origin/main` ve `FETCH_HEAD`. Hicbiri okunamazsa -> OLCULEMEDI.
HEAD adaylardan BIRINE ESITSE kanit tamamdir (bu yol NESNE GRAFI GEZMEZ; sig checkout'ta
eksik nesne yuzunden yanlis kirmizi URETMEZ). Esitlik yoksa her aday HEAD'in ATASI olmali
(itilmemis yerel commit mesrudur); ata DEGILSE ya da ata iliskisi KARARLASTIRILAMIYORSA ->
OLCULEMEDI. `paket-tazelik-alarmi.yml` her kosumda `git fetch --depth=1 origin main` +
`git reset --hard FETCH_HEAD` yapar; OLCULDU (CI taklidi, gecici depo): o adimdan sonra
HEAD == FETCH_HEAD == refs/remotes/origin/main -> kapi ESITLIK yolundan gecer, CI YESIL
kalir. Ayrica `calisma_agaci_dogrula()`: yol kumesi DISKTEN, gecmis HEAD'den turer; bundle
dosyalarinda kaydedilmemis fark varsa iki nesil karisir -> OLCULEMEDI (bundle DISI kirlilik
— or. urunler.json parti yazimi — kapiyi TETIKLEMEZ, olculdu: 41 dosyalik bundle kumesinde
`urunler.json` YOKTUR).

🔴 4 AGU 2026 "AYRISMASI" — CURUTULDU, KAPI DOGRU OLCUYORDU
==========================================================
Sikayet: CI kosumu 30883459826 (06:17Z) "590,5 dk bayat" derken ayni betik yerelde 07:51Z'de
"taze, 0,0 dk" dedi. OLCULDU (`wrangler versions list`, salt okuma + `~/.wrangler/logs`):
    v51 7b2c9325  2026-08-03T19:46:30Z  version_upload   <- CI kosumunda canli olan KOD
    v52 79fe88ca  2026-08-04T07:31:24Z  version_upload   <- ARADA INEN DEPLOY (log kaniti)
    v53 da66d2cb  2026-08-04T07:56:36Z  version_upload
En eski yayinlanmamis bundle commit'i dec2dddf (2026-08-03T20:27:01Z); 06:17:32Z'de yasi
590,5 dk -> CI DOGRUYDU. 07:31:24Z'de pruvo-shop deploy edildi; en yeni bundle commit'i
5701a1a4 (2026-08-04T00:42:43Z) o surumden ESKI -> `geride` BOS -> "taze, 0,0 dk". YEREL DE
DOGRUYDU. Iki olcum 95 dk arayla, ARALARINDA BIR DEPLOY ile yapildi; ayni ana ait celiski
YOKTU. Kimlik ekseni de curudu: iki kosum da AYNI hesabi (dbbe2a86…) ve AYNI worker'i
sordu. Yukaridaki fail-closed duzeltme bu olayin sebebi DEGIL, olayi arastirirken OLCULEN
BASKA bir fail-open'in kapatilmasidir.

🔴 NEDEN YAYIN YOLUNU BLOKLAMAZ (yapisal secim, olculmus gerekce)
=================================================================
Bu kapi AGA ve CLOUDFLARE YETKISINE bagimlidir. Ag'a bagimli bir yanlis-pozitif
`deploy.yml` `build` isine konursa TUM EKIBIN yayinini durdurur ([[kapi-kapsam-eksen-secimi]]);
ayni gerekceyle `tools/fiziksel-canli-kapisi.py`nin CANLI kolu da bilerek
`paket-tazelik-alarmi.yml`e (cron serisi, `push` tetigi YOK, `deploy.yml`e `needs` ile
BAGLI DEGIL) kablolandi. Bu kapi da ORAYA girer: kirmizisi GORUNUR (kosum kirmizi + GitHub
bildirimi + is ozeti), yayin yoluna maliyeti 0 sn. Cadans 15 dk -> 13 sa 15 dk'lik korluk
penceresi <= 15 dk'ya duser (olculen iyilesme: 53 kat).
OFFLINE kolu (`--kendini-test`) deterministiktir ve `deploy.yml` `build` isinde BLOKLAYICI
kosar — ag gerektirmeyen kismi bloklamak yanlis-pozitif uretmez.

Kullanim:
    python3 tools/shop-bayatlik-kapisi.py              # canli olcum (npx wrangler)
    python3 tools/shop-bayatlik-kapisi.py --gh-ozet    # + $GITHUB_OUTPUT/$GITHUB_STEP_SUMMARY
    python3 tools/shop-bayatlik-kapisi.py --kendini-test   # OFFLINE kabul testi (CI)
Curutme (elde): python3 tools/shop-bayatlik-mutasyon.py
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SHOP = os.path.join(ROOT, "shop")
WRANGLER_TOML = os.path.join(SHOP, "wrangler.toml")

# 🔴 ESIK — gerekcesi dosya basinda OLCUMLE beyan edildi (8/8 saglikli deploy < 120 dk;
# olay penceresi 795 dk). Iki yonu de kabul testinde nobet altinda (D2/D3).
ESIK_DK = 120

# Bir surumun KOD tasiyip tasimadigi. `secret`: kod DEGISMEDI, damga tazelendi ->
# kod zamani icin ATLANIR (olculen maskeleme tuzagi, bkz. dosya basi).
KOD_TASIMAYAN = frozenset(("secret",))
# Kod tasidigi OLCULEN tetikler. Bilinmeyen bir tetik SESSIZCE kod sayilmaz: Cloudflare
# yeni bir deger (or. `rollback`) uretirse nesil bu veriden TURETILEMEZ -> fail-closed.
KOD_TASIYAN = frozenset(("version_upload", "deployment", "upload"))

# git gecmisi sig (shallow) checkout'ta kesiktir; kapi gerektigi kadar derinlestirir.
DERINLESTIRME_ADIMI = 500
DERINLESTIRME_TAVANI = 6

# Hukmun anlami "UZAK ANA DALDAKI kod canliya inmis mi"dir; `git log` ise HEAD'i sorar.
# Ikisinin ayni oldugu KANITLANMALIDIR (bkz. dosya basi "OLCULEN REF" bolumu).
ANA_DAL = "main"
UZAK_UC_ADAYLARI = ("refs/remotes/origin/%s" % ANA_DAL, "FETCH_HEAD")

IMPORT_RE = re.compile(r"""(?:^|[\n;])\s*import\s+(?:[^"';]*?\s+from\s+)?["']([^"']+)["']""")
DINAMIK_IMPORT_RE = re.compile(r"""\bimport\s*\(\s*["']([^"']+)["']""")


class Olculemedi(Exception):
    """FAIL-CLOSED tasiyicisi: olculemeyen her hal rc 2 ile disari cikar."""


# ---------------------------------------------------------------- zaman

def zaman_coz(ham):
    """ISO-8601 -> timezone-aware UTC datetime. Bicim bozuksa OLCULEMEDI."""
    if not isinstance(ham, str) or not ham.strip():
        raise Olculemedi("zaman damgasi yok/bos: %r" % (ham,))
    metin = ham.strip().replace("Z", "+00:00")
    try:
        d = datetime.datetime.fromisoformat(metin)
    except ValueError:
        raise Olculemedi("zaman damgasi cozulemedi: %r" % (ham,))
    if d.tzinfo is None:
        raise Olculemedi("zaman damgasi saat dilimsiz: %r" % (ham,))
    return d.astimezone(datetime.timezone.utc)


# ---------------------------------------------------------------- bundle kumesi

def wrangler_giris(toml_yolu):
    """wrangler.toml'dan (name, main) — bundle'in GIRIS noktasi TEK KAYNAKTAN gelir.

    Elle tutulan bir dosya listesi bu depoda cururdu ([[ikiz-tanim-sessiz-ayrisma]]):
    `shop/src/parametrik.js` bugun `jenerator/hacim.js`i, `semalar.js` 22 sema JSON'unu
    bundle'a sokuyor — hicbiri `shop/` altinda DEGIL. Kume ITHALAT GRAFINDEN turetilir."""
    try:
        with open(toml_yolu, encoding="utf-8") as f:
            metin = f.read()
    except OSError as e:
        raise Olculemedi("wrangler.toml okunamadi: %s" % e)
    bas = {}
    for satir in metin.splitlines():
        s = satir.strip()
        if s.startswith("["):
            break            # ilk tablodan sonrasi ust duzey degil
        m = re.match(r'^(name|main)\s*=\s*"([^"]+)"', s)
        if m:
            bas[m.group(1)] = m.group(2)
    if "name" not in bas or "main" not in bas:
        raise Olculemedi("wrangler.toml'da name/main bulunamadi")
    return bas["name"], bas["main"]


def _coz(kok_dizin, kaynak_yol, spec):
    aday = os.path.normpath(os.path.join(os.path.dirname(kaynak_yol), spec))
    if os.path.isfile(aday):
        return aday
    for ek in (".js", ".mjs", ".json", "/index.js"):
        if os.path.isfile(aday + ek):
            return aday + ek
    raise Olculemedi("ithalat cozulemedi: %s -> %s" % (
        os.path.relpath(kaynak_yol, kok_dizin), spec))


def bundle_dosyalari(kok, giris_mutlak, izlenen):
    """Bundle'a giren IZLENEN dosyalarin repo-goreli yollari (sirali).

    FAIL-CLOSED uc yol: cozulemeyen goreli ithalat · GORECELI OLMAYAN (npm) ithalat ·
    izlenmeyen dosya. Ucunde de OLCULEMEDI — cunku o hallerde "bundle'i etkileyen
    commit kumesi" artik depo dosyalarindan TURETILEMEZ."""
    if not os.path.isfile(giris_mutlak):
        raise Olculemedi("bundle giris dosyasi yok: %s" % giris_mutlak)
    gorulen, yigin = set(), [os.path.normpath(giris_mutlak)]
    while yigin:
        yol = yigin.pop()
        if yol in gorulen:
            continue                      # dongu KILITLENMEZ
        gorulen.add(yol)
        if not yol.endswith((".js", ".mjs")):
            continue                      # .json yaprak
        try:
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
        except OSError as e:
            raise Olculemedi("bundle dosyasi okunamadi: %s (%s)" % (yol, e))
        for spec in IMPORT_RE.findall(metin) + DINAMIK_IMPORT_RE.findall(metin):
            if not spec.startswith("."):
                raise Olculemedi(
                    "goreli OLMAYAN ithalat (%s <- %s): bundle artik yalniz depo "
                    "dosyalarindan turemiyor" % (spec, os.path.relpath(yol, kok)))
            yigin.append(_coz(kok, yol, spec))
    rel = sorted(os.path.relpath(y, kok) for y in gorulen)
    disarda = [y for y in rel if y not in izlenen]
    if disarda:
        raise Olculemedi("bundle'da IZLENMEYEN dosya var: %s" % ", ".join(disarda))
    return rel


def izlenen_kume(kok):
    r = subprocess.run(["git", "-C", kok, "ls-files"], capture_output=True, text=True)
    if r.returncode != 0:
        raise Olculemedi("git ls-files basarisiz: %s" % r.stderr.strip())
    return set(r.stdout.splitlines())


# ---------------------------------------------------------------- canli surum

def _tetik(surum):
    return ((surum.get("annotations") or {}).get("workers/triggered_by") or "").strip()


def kod_surumu(dagitimlar, surumler):
    """(kod_surum_id, kod_zamani, aktif_surum_id) — canli bundle'in KOD nesli.

    AKTIF dagitim = en yeni `created_on` (rollback da yeni bir dagitim uretir; "en yuksek
    surum numarasi" DEGIL — geri alinmis bir worker'da o hukum YANLIS olurdu, kabul C3).
    KOD zamani = aktif surumden GERIYE dogru, `secret` tetikli surumler ATLANARAK bulunan
    ilk kod tasiyan surumun `created_on`u (olculen maskeleme tuzagi, kabul C2)."""
    if not isinstance(dagitimlar, list) or not dagitimlar:
        raise Olculemedi("dagitim listesi bos/bicimsiz")
    if not isinstance(surumler, list) or not surumler:
        raise Olculemedi("surum listesi bos/bicimsiz")
    aktif = max(dagitimlar, key=lambda d: zaman_coz(d.get("created_on")))
    yuzde_yuz = [v for v in (aktif.get("versions") or [])
                 if v.get("percentage") == 100 and v.get("version_id")]
    if len(yuzde_yuz) != 1:
        raise Olculemedi("aktif dagitimda %%100 tek surum yok (%d aday)" % len(yuzde_yuz))
    aktif_id = yuzde_yuz[0]["version_id"]
    endeks = {}
    for v in surumler:
        if not isinstance(v, dict) or "id" not in v or not isinstance(v.get("number"), int):
            raise Olculemedi("surum kaydi bicimsiz: %r" % (v,))
        endeks[v["id"]] = v
    if aktif_id not in endeks:
        raise Olculemedi("aktif surum %s surum listesinde YOK (liste kisa/bicimsiz)"
                         % aktif_id[:8])
    aktif_no = endeks[aktif_id]["number"]
    adaylar = sorted((v for v in surumler if v["number"] <= aktif_no),
                     key=lambda v: v["number"])
    for v in reversed(adaylar):
        tetik = _tetik(v)
        if tetik in KOD_TASIMAYAN:
            continue
        if tetik not in KOD_TASIYAN:
            raise Olculemedi(
                "surum %s BILINMEYEN tetik tasiyor (%r): kod nesli bu veriden "
                "turetilemez" % (v["id"][:8], tetik))
        return v["id"], zaman_coz((v.get("metadata") or {}).get("created_on")), aktif_id
    raise Olculemedi("aktif surume kadar KOD tasiyan surum bulunamadi")


def wrangler_json(alt_komut, cfg=WRANGLER_TOML):
    """`npx wrangler@4 <alt> list --json` -> ayristirilmis JSON. Her hata OLCULEMEDI.

    Kimlik: CI'da CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID (wrangler ortamdan alir),
    yerelde `wrangler login` OAuth'u. d1-sync.py ile AYNI istemci/surum sabiti (`@4`)."""
    komut = ["npx", "--yes", "wrangler@4", alt_komut, "list", "-c", cfg, "--json"]
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        raise Olculemedi("wrangler %s calistirilamadi: %s" % (alt_komut, e))
    if r.returncode != 0:
        kuyruk = (r.stderr or r.stdout or "").strip()[-500:]
        raise Olculemedi("wrangler %s rc=%d: %s" % (alt_komut, r.returncode, kuyruk))
    try:
        return json.loads(r.stdout)
    except ValueError as e:
        raise Olculemedi("wrangler %s ciktisi JSON degil: %s" % (alt_komut, e))


# ---------------------------------------------------------------- commit sayimi

def _git(kok, *args):
    return subprocess.run(["git", "-C", kok] + list(args), capture_output=True, text=True)


def _ref_coz(kok, ref):
    """Ref -> commit sha, cozulmezse None. `--quiet` ile YOK olan ref hata BASMAZ."""
    r = _git(kok, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return None


def olculen_ref_dogrula(kok):
    """OLCULEN ref'in (HEAD) OLCULMESI GEREKEN ref (uzak main ucu) oldugunu KANITLAR.

    Kanit yoksa "guncel VARSAYILMAZ" -> OLCULEMEDI (rc 2). Gerekce ve olculen fikstur
    degerleri dosya basinda. Doner: (head_sha, kaniti_veren_ref)."""
    r = _git(kok, "rev-parse", "--verify", "HEAD")
    if r.returncode != 0 or not r.stdout.strip():
        raise Olculemedi("HEAD cozulemedi: %s" % (r.stderr or "").strip()[-200:])
    head = r.stdout.strip()
    cozulen = [(ad, sha) for ad, sha in ((a, _ref_coz(kok, a)) for a in UZAK_UC_ADAYLARI)
               if sha]
    if not cozulen:
        raise Olculemedi(
            "uzak %s ucu OKUNAMADI (denenen: %s): HEAD'in olculmesi GEREKEN ref oldugu "
            "KANITLANAMIYOR" % (ANA_DAL, ", ".join(UZAK_UC_ADAYLARI)))
    for ad, sha in cozulen:
        # 🔴 ESITLIK ONCE — bu yol NESNE GRAFI GEZMEZ. CI `git fetch --depth=1 origin
        # main` + `git reset --hard FETCH_HEAD` yapar; sig agacta eksik bir nesne
        # `merge-base`i patlatabilir, esitlik yolu o yanlis kirmiziyi URETMEZ.
        if sha == head:
            return head, ad
    for ad, sha in cozulen:
        a = _git(kok, "merge-base", "--is-ancestor", sha, head)
        if a.returncode == 1:
            raise Olculemedi(
                "HEAD (%s) uzak uc %s (%s) commit'ini ICERMIYOR: bundle commit'leri bu "
                "gecmiste GORUNMEZ, 'taze' hukmu SAHTE olurdu"
                % (head[:8], ad, sha[:8]))
        if a.returncode != 0:
            raise Olculemedi(
                "HEAD ile %s arasindaki ata iliskisi KARARLASTIRILAMADI (git rc=%d: %s)"
                % (ad, a.returncode, (a.stderr or "").strip()[-160:]))
    # HEAD uzak ucun ILERISINDE: itilmemis yerel commit mesrudur, uzak ucun TASIDIGI
    # her commit HEAD gecmisindedir -> olculecek kume eksik DEGIL.
    return head, "+".join(ad for ad, _ in cozulen)


def calisma_agaci_dogrula(kok, yollar):
    """Yol kumesi DISKTEN (`bundle_dosyalari`), gecmis HEAD'den turer. Bundle dosyalarinda
    kaydedilmemis fark varsa iki AYRI nesil karisir -> OLCULEMEDI. Bundle DISI kirlilik
    (or. `urunler.json` parti yazimi) bu kapiyi TETIKLEMEZ: suzgec `yollar` ile sinirli."""
    r = _git(kok, "diff", "--name-only", "HEAD", "--", *yollar)
    if r.returncode != 0:
        raise Olculemedi("git diff basarisiz: %s" % (r.stderr or "").strip()[-200:])
    sapan = sorted(s for s in r.stdout.splitlines() if s.strip())
    if sapan:
        raise Olculemedi(
            "calisma agaci HEAD'den AYRIK (%d bundle dosyasi: %s): olculen yol kumesi ile "
            "olculen gecmis AYRI nesillerden" % (len(sapan), ", ".join(sapan[:5])))
    return True


def gecmisi_yeterince_ac(kok, kod_zamani):
    """Sig checkout'ta gecmis kesiktir: `git log` HIC commit gostermeyip SAHTE 'taze'
    uretirdi. Gecmisin dibi kod_zamani'ndan YENI oldugu surece derinlestir; acilamazsa
    OLCULEMEDI (yesil sayilmaz).

    🔴 SINIRI (olculdu, bu yuzden `olculen_ref_dogrula` AYRI bir kapidir): burasi
    DERINLIK sorar, GUNCELLIK sormaz — tam klonda `--is-shallow-repository == false`
    gorup HEMEN True doner, HEAD uzak ucun GERISINDE olsa bile."""
    for _ in range(DERINLESTIRME_TAVANI + 1):
        r = _git(kok, "rev-parse", "--is-shallow-repository")
        if r.returncode != 0:
            raise Olculemedi("git rev-parse basarisiz: %s" % r.stderr.strip())
        if r.stdout.strip() != "true":
            return True                      # tam gecmis: kesinti YOK
        son = _git(kok, "log", "--format=%cI")
        if son.returncode != 0 or not son.stdout.strip():
            raise Olculemedi("sig gecmis okunamadi: %s" % son.stderr.strip())
        en_eski = zaman_coz(son.stdout.strip().splitlines()[-1])
        if en_eski < kod_zamani:
            return True                      # dip, canli kod zamanindan ESKI: yeterli
        # 🔴 `--filter=blob:none` ONCE: bu depoda `urunler.json` 16,5 MB ve HEMEN her
        # commit'te degisiyor -> blob'lu bir 500'luk derinlestirme yuzlerce MB ceker ve
        # 15 dakikada bir kosan alarmi bant genisligiyle cezalandirir. Yol-sinirli
        # `git log` YALNIZ agac/blob OID'lerini karsilastirir, blob ICERIGI istemez;
        # bu yuzden blobsuz gecmis bu olcum icin YETERLIDIR. Sunucu filtreyi reddederse
        # blob'lu derinlestirmeye DUSULUR (fail-closed degil, PAHALIYA gecis).
        f = _git(kok, "fetch", "--filter=blob:none",
                 "--deepen=%d" % DERINLESTIRME_ADIMI, "origin", "main")
        if f.returncode != 0:
            f = _git(kok, "fetch", "--deepen=%d" % DERINLESTIRME_ADIMI, "origin", "main")
        if f.returncode != 0:
            raise Olculemedi("gecmis derinlestirilemedi (sig checkout): %s"
                             % f.stderr.strip()[-300:])
    raise Olculemedi("gecmis %d adimda kod zamanina kadar acilamadi"
                     % DERINLESTIRME_TAVANI)


def bundle_commitleri(kok, yollar, kod_zamani):
    """kod_zamani'ndan SONRA bundle dosyalarina dokunan commit'ler [(sha, zaman, ozet)].

    Once OLCULEN REF ve CALISMA AGACI kanitlanir: `git log` HEAD'i sorar, hukum ise uzak
    main ucu hakkindadir; kanit yoksa bu fonksiyon BOS liste dondurup sahte 'taze'
    uretmek yerine OLCULEMEDI firlatir."""
    olculen_ref_dogrula(kok)
    calisma_agaci_dogrula(kok, yollar)
    gecmisi_yeterince_ac(kok, kod_zamani)
    r = _git(kok, "log", "--format=%H\x1f%cI\x1f%s",
             "--since=%s" % kod_zamani.isoformat(), "--", *yollar)
    if r.returncode != 0:
        raise Olculemedi("git log basarisiz: %s" % r.stderr.strip())
    kayit = []
    for satir in r.stdout.splitlines():
        if not satir.strip():
            continue
        parca = satir.split("\x1f")
        if len(parca) != 3:
            raise Olculemedi("git log satiri bicimsiz: %r" % satir)
        kayit.append((parca[0], zaman_coz(parca[1]), parca[2]))
    return kayit


# ---------------------------------------------------------------- hukum

def hukum(kod_zamani, commitler, simdi, esik_dk=ESIK_DK):
    """(durum, geride_sayisi, en_eski_yas_dk) — TEK yargi noktasi."""
    if simdi < kod_zamani:
        raise Olculemedi("saat sapmasi: 'simdi' canli kod zamanindan ESKI")
    geride = [c for c in commitler if c[1] > kod_zamani]
    if not geride:
        return "taze", 0, 0.0
    en_eski = min(c[1] for c in geride)
    yas = (simdi - en_eski).total_seconds() / 60.0
    if yas > esik_dk:
        return "bayat", len(geride), yas
    return "bekliyor", len(geride), yas


RC = {"taze": 0, "bekliyor": 0, "bayat": 1, "olculemedi": 2}


def gh_yaz(durum, ozet_metin, ortam=None):
    """`$GITHUB_OUTPUT` -> `durum=<etiket>` · `$GITHUB_STEP_SUMMARY` -> ozet. Yazilan
    dosya sayisini dondurur (kabul testi BIREBIR satiri olcer)."""
    ortam = os.environ if ortam is None else ortam
    yazilan = 0
    for degisken, icerik in (("GITHUB_OUTPUT", "durum=%s\n" % durum),
                             ("GITHUB_STEP_SUMMARY", ozet_metin + "\n")):
        yol = ortam.get(degisken)
        if not yol:
            continue
        try:
            with open(yol, "a", encoding="utf-8") as f:
                f.write(icerik)
            yazilan += 1
        except OSError as e:
            print("UYARI: %s yazilamadi: %s" % (degisken, e))
    return yazilan


# ---------------------------------------------------------------- canli kol

def canli_olcum(gh=False):
    try:
        ad, giris = wrangler_giris(WRANGLER_TOML)
        head, kanit_ref = olculen_ref_dogrula(ROOT)
        izlenen = izlenen_kume(ROOT)
        yollar = bundle_dosyalari(ROOT, os.path.join(SHOP, giris), izlenen)
        yollar = sorted(set(yollar) | {os.path.relpath(WRANGLER_TOML, ROOT)})
        dagitimlar = wrangler_json("deployments")
        surumler = wrangler_json("versions")
        kod_id, kod_zamani, aktif_id = kod_surumu(dagitimlar, surumler)
        commitler = bundle_commitleri(ROOT, yollar, kod_zamani)
        simdi = datetime.datetime.now(datetime.timezone.utc)
        durum, geride, yas = hukum(kod_zamani, commitler, simdi)
    except Olculemedi as e:
        print("OLCULEMEDI: %s" % e)
        print("  -> 'guncel' VARSAYILMADI. rc=2.")
        if gh:
            gh_yaz("olculemedi", "### shop bayatlik: OLCULEMEDI\n\n`%s`" % e)
        return RC["olculemedi"]

    print("worker            : %s" % ad)
    print("olculen ref       : HEAD %s  (uzak %s ucu KANITI: %s)"
          % (head[:8], ANA_DAL, kanit_ref))
    print("bundle dosyasi    : %d (ithalat grafinden turetildi)" % len(yollar))
    print("aktif surum       : %s" % aktif_id)
    print("canli KOD surumu  : %s  (%s)" % (kod_id, kod_zamani.isoformat()))
    print("bundle commit'i   : %d adet, canli koddan YENI" % geride)
    for sha, zaman, ozet in sorted(commitler, key=lambda c: c[1])[:10]:
        if zaman > kod_zamani:
            print("   %s  %s  %s" % (sha[:8], zaman.isoformat(), ozet[:70]))
    print("esik              : %d dk (beyan: dosya basi)" % ESIK_DK)
    print("en eski yayinlanmamis commit yasi: %.1f dk" % yas)
    print("DURUM             : %s (rc=%d)" % (durum.upper(), RC[durum]))
    if durum == "bayat":
        print("  -> CANLI ODEME WORKER'I BAYAT. Yayin: shop dizininden `npx wrangler deploy`"
              " (DEPLOY = OKAN/mimar karari).")
    if gh:
        ozet = ("### shop bayatlik nobeti: %s\n\n"
                "* canli KOD surumu: `%s` (%s)\n* geride commit: **%d**\n"
                "* en eski yayinlanmamis commit yasi: **%.1f dk** (esik %d dk)\n"
                % (durum.upper(), kod_id[:8], kod_zamani.isoformat(), geride, yas, ESIK_DK))
        if durum == "bayat":
            ozet += "\n**YAPILACAK:** shop worker'ini yeniden yayinla (`wrangler deploy`).\n"
        gh_yaz(durum, ozet)
    return RC[durum]


# ---------------------------------------------------------------- kabul testi

_SAYAC = {"n": 0, "kirmizi": []}


def iddia(kod, aciklama, sart):
    _SAYAC["n"] += 1
    if not sart:
        _SAYAC["kirmizi"].append(kod)
    print("  %s %-4s %s" % ("OK  " if sart else "KIRMIZI", kod, aciklama))


def _v(no, vid, iso, tetik="version_upload"):
    return {"id": vid, "number": no,
            "metadata": {"created_on": iso},
            "annotations": {"workers/triggered_by": tetik}}


def _d(vid, iso, yuzde=100, tetik="deployment"):
    return {"id": "dep-" + vid, "created_on": iso,
            "annotations": {"workers/triggered_by": tetik},
            "versions": [{"version_id": vid, "percentage": yuzde}]}


def _olculemedi_mi(fn, *a, **k):
    try:
        fn(*a, **k)
    except Olculemedi:
        return True
    except Exception:
        return False
    return False


def _yaz(dizin, gorece, icerik):
    yol = os.path.join(dizin, gorece)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)
    return yol


def kendini_test():
    """OFFLINE kabul testi — ag YOK, wrangler YOK, depo dosyasi YAZILMAZ."""
    print("SHOP BAYATLIK KAPISI — kabul testi (offline)")

    # ---- B: bundle kumesi (ithalat grafi) --------------------------------
    print("\nB. BUNDLE KUMESI (ithalat grafi)")
    with tempfile.TemporaryDirectory() as t:
        _yaz(t, "shop/src/index.js", 'import A from "./a.js";\nimport "../../ortak.js";\n')
        _yaz(t, "shop/src/a.js", 'import B from "./b.js";\nimport S from "../sema.json";\n')
        _yaz(t, "shop/src/b.js", 'import "./a.js";\n')          # dongu
        _yaz(t, "shop/sema.json", "{}")
        _yaz(t, "ortak.js", "export const X = 1;\n")
        _yaz(t, "shop/src/ALAKASIZ.js", 'import "./a.js";\n')
        izl = {"shop/src/index.js", "shop/src/a.js", "shop/src/b.js", "shop/sema.json",
               "ortak.js", "shop/src/ALAKASIZ.js"}
        kume = bundle_dosyalari(t, os.path.join(t, "shop/src/index.js"), izl)
        iddia("B1", "gecisli ithalat (index->a->b) kumede",
              {"shop/src/index.js", "shop/src/a.js", "shop/src/b.js"} <= set(kume))
        iddia("B2", "json ithalati + depo kokundeki ortak dosya kumede",
              {"shop/sema.json", "ortak.js"} <= set(kume))
        iddia("B3", "ITHAL EDILMEYEN dosya kumede DEGIL (ayirt edici eksen)",
              "shop/src/ALAKASIZ.js" not in kume)
        iddia("B7", "dongu kilitlenmez, kume 5 dosya", len(kume) == 5)

        _yaz(t, "shop/src/kirik.js", 'import "./yok-boyle-bir-sey.js";\n')
        iddia("B4", "cozulemeyen goreli ithalat -> OLCULEMEDI",
              _olculemedi_mi(bundle_dosyalari, t, os.path.join(t, "shop/src/kirik.js"),
                             izl | {"shop/src/kirik.js"}))
        _yaz(t, "shop/src/npm.js", 'import x from "hono";\n')
        iddia("B5", "goreli OLMAYAN (npm) ithalat -> OLCULEMEDI",
              _olculemedi_mi(bundle_dosyalari, t, os.path.join(t, "shop/src/npm.js"),
                             izl | {"shop/src/npm.js"}))
        iddia("B6", "bundle'da IZLENMEYEN dosya -> OLCULEMEDI",
              _olculemedi_mi(bundle_dosyalari, t, os.path.join(t, "shop/src/index.js"),
                             izl - {"ortak.js"}))
        iddia("B8", "olmayan giris dosyasi -> OLCULEMEDI",
              _olculemedi_mi(bundle_dosyalari, t, os.path.join(t, "yok.js"), izl))

    # ---- B9/B10: GERCEK depo (deterministik, ag YOK) ----------------------
    gercek_ad, gercek_giris = wrangler_giris(WRANGLER_TOML)
    gercek = bundle_dosyalari(ROOT, os.path.join(SHOP, gercek_giris), izlenen_kume(ROOT))
    iddia("B9", "gercek bundle 20+ dosya ve shop/src/index.js iceriyor",
          len(gercek) >= 20 and "shop/src/index.js" in gercek)
    iddia("B10", "gercek bundle shop/ DISINDAKI paylasilan kaynagi da goruyor "
                 "(secenekler.js) — elle liste bunu kacirirdi",
          "secenekler.js" in gercek and gercek_ad == "pruvo-shop")

    # ---- C: canli kod surumu ---------------------------------------------
    print("\nC. CANLI KOD SURUMU (dagitim/surum yorumu)")
    v1 = _v(10, "aaaaaaaa-1", "2026-08-02T07:20:04Z")
    v2 = _v(11, "bbbbbbbb-2", "2026-08-02T07:39:07Z", tetik="secret")
    v3 = _v(12, "cccccccc-3", "2026-08-03T13:22:45Z")
    d1 = _d("aaaaaaaa-1", "2026-08-02T07:20:07Z")
    d2 = _d("bbbbbbbb-2", "2026-08-02T07:39:07Z", tetik="secret")
    d3 = _d("cccccccc-3", "2026-08-03T13:22:48Z")

    kid, kz, aid = kod_surumu([d1, d3], [v1, v3])
    iddia("C1", "aktif dagitim en YENI created_on; kod surumu ondan okunur",
          kid == "cccccccc-3" and aid == "cccccccc-3"
          and kz == zaman_coz("2026-08-03T13:22:45Z"))
    kid2, kz2, aid2 = kod_surumu([d1, d2], [v1, v2])
    iddia("C2", "SECRET degisimi nesli tazelemez: kod zamani onceki KOD surumunden "
                "(olculen maskeleme tuzagi 2 Agu)",
          aid2 == "bbbbbbbb-2" and kid2 == "aaaaaaaa-1"
          and kz2 == zaman_coz("2026-08-02T07:20:04Z"))
    kid3, kz3, _ = kod_surumu([d3, _d("aaaaaaaa-1", "2026-08-03T15:00:00Z")], [v1, v3])
    iddia("C3", "GERI ALMA: aktif dagitim eski surumu tasiyorsa hukum EN YENI surumden "
                "DEGIL aktiften cikar",
          kid3 == "aaaaaaaa-1" and kz3 == zaman_coz("2026-08-02T07:20:04Z"))
    iddia("C4", "%100 surum yok -> OLCULEMEDI",
          _olculemedi_mi(kod_surumu, [_d("cccccccc-3", "2026-08-03T13:22:48Z", yuzde=50)],
                         [v1, v3]))
    iddia("C5", "bos dagitim listesi -> OLCULEMEDI (fail-open YOK)",
          _olculemedi_mi(kod_surumu, [], [v1, v3]))
    iddia("C6", "aktif surum, surum listesinde yoksa -> OLCULEMEDI",
          _olculemedi_mi(kod_surumu, [d3], [v1]))
    iddia("C7", "bozuk zaman damgasi -> OLCULEMEDI",
          _olculemedi_mi(kod_surumu, [_d("cccccccc-3", "dun aksam")], [v1, v3]))
    iddia("C8", "BILINMEYEN tetik (or. rollback) -> OLCULEMEDI, kod SAYILMAZ",
          _olculemedi_mi(kod_surumu, [_d("dddddddd-4", "2026-08-03T16:00:00Z")],
                         [v1, _v(13, "dddddddd-4", "2026-08-03T16:00:00Z",
                                 tetik="rollback")]))
    iddia("C9", "surum kaydinda number yoksa -> OLCULEMEDI",
          _olculemedi_mi(kod_surumu, [d3],
                         [{"id": "cccccccc-3", "metadata": {"created_on":
                                                            "2026-08-03T13:22:45Z"}}]))

    # ---- D: hukum + esik --------------------------------------------------
    print("\nD. HUKUM VE ESIK (%d dk)" % ESIK_DK)
    kz = zaman_coz("2026-08-03T13:22:45Z")
    c_once = ("1111111", zaman_coz("2026-08-03T12:17:40Z"), "deploy'dan ONCE")
    d_taze, g_taze, _ = hukum(kz, [c_once], zaman_coz("2026-08-03T20:00:00Z"))
    iddia("D1", "canli koddan ESKI commit geride SAYILMAZ -> taze, rc 0",
          d_taze == "taze" and g_taze == 0 and RC[d_taze] == 0)
    c119 = ("2222222", zaman_coz("2026-08-03T14:00:00Z"), "yeni")
    d119, g119, y119 = hukum(kz, [c119], zaman_coz("2026-08-03T15:59:00Z"))
    iddia("D2", "esik-1 dk (119,0) -> BEKLIYOR rc 0 (esigi ASAGI cekmek bu iddiayi kirar)",
          d119 == "bekliyor" and g119 == 1 and abs(y119 - 119.0) < 0.05 and RC[d119] == 0)
    d121, g121, y121 = hukum(kz, [c119], zaman_coz("2026-08-03T16:01:00Z"))
    iddia("D3", "esik+1 dk (121,0) -> BAYAT rc 1 (esigi YUKARI cekmek bu iddiayi kirar)",
          d121 == "bayat" and g121 == 1 and abs(y121 - 121.0) < 0.05 and RC[d121] == 1)
    # 3 Agu olayinin replayi: 13 sa 15 dk = 795 dk
    olay = ("3333333", zaman_coz("2026-08-03T00:07:00Z"), "olay commit'i")
    d_olay, g_olay, y_olay = hukum(zaman_coz("2026-08-02T20:00:00Z"), [olay, c119],
                                   zaman_coz("2026-08-03T13:22:00Z"))
    iddia("D4", "OLCULEN OLAY (795 dk) -> BAYAT, 2 commit geride",
          d_olay == "bayat" and g_olay == 2 and abs(y_olay - 795.0) < 0.6)
    cok = [("a", zaman_coz("2026-08-03T14:00:00Z"), ""),
           ("b", zaman_coz("2026-08-03T15:00:00Z"), ""),
           ("c", zaman_coz("2026-08-03T16:00:00Z"), ""),
           c_once]
    d_cok, g_cok, _ = hukum(kz, cok, zaman_coz("2026-08-03T19:00:00Z"))
    iddia("D5", "geride sayisi YALNIZ canli koddan yeni commit'leri sayar (3, 4 degil)",
          d_cok == "bayat" and g_cok == 3)
    iddia("D6", "saat sapmasi (simdi < kod zamani) -> OLCULEMEDI",
          _olculemedi_mi(hukum, kz, [c119], zaman_coz("2026-08-03T10:00:00Z")))
    iddia("D7", "rc haritasi: taze/bekliyor 0, bayat 1, olculemedi 2",
          RC == {"taze": 0, "bekliyor": 0, "bayat": 1, "olculemedi": 2})

    # ---- E: gh-ozet -------------------------------------------------------
    print("\nE. GITHUB CIKTISI")
    with tempfile.TemporaryDirectory() as t:
        cikti, ozet = os.path.join(t, "out"), os.path.join(t, "sum")
        sahte = {"GITHUB_OUTPUT": cikti, "GITHUB_STEP_SUMMARY": ozet}
        n = gh_yaz("bayat", "ozet", sahte)
        with open(cikti, encoding="utf-8") as f:
            satir = f.read()
        iddia("E1", "$GITHUB_OUTPUT satiri BIREBIR 'durum=bayat' + 2 dosya yazildi",
              satir == "durum=bayat\n" and n == 2)
        gh_yaz("olculemedi", "ozet2", sahte)
        with open(cikti, encoding="utf-8") as f:
            hepsi = f.read()
        iddia("E2", "OLCULEMEDI ayri satir yazar, 'taze' YAZMAZ",
              hepsi.endswith("durum=olculemedi\n") and "durum=taze" not in hepsi)

    # ---- F: UCTAN UCA (GERCEK git, ag YOK) --------------------------------
    # Fikstur `hukum()`u tek basina olcer; bu bolum GERCEK bir git deposunda
    # bundle_commitleri() + hukum() zincirini kosar. OLDURUCU (F1) ve KONTROL (F2)
    # AYNI depoda, tek degisken kod zamani -> kirmizi bir SEYI olctugunu kanitlar.
    print("\nF. UCTAN UCA (gercek git deposu, ag YOK)")
    with tempfile.TemporaryDirectory() as t:
        depo = os.path.join(t, "depo")
        os.makedirs(depo)
        _git(depo, "init", "-q", "-b", "main")
        _git(depo, "config", "user.email", "t@t")
        _git(depo, "config", "user.name", "t")
        def _islet(mesaj, iso):
            # commit ZAMANI hukmun girdisi -> deterministik olmali: hem author hem
            # COMMITTER damgasi sabitlenir (kapi %cI = committer tarihini okur).
            env = dict(os.environ, GIT_AUTHOR_DATE=iso, GIT_COMMITTER_DATE=iso)
            subprocess.run(["git", "-C", depo, "add", "-A"], capture_output=True)
            subprocess.run(["git", "-C", depo, "commit", "-q", "-m", mesaj],
                           env=env, capture_output=True, text=True)
            # commit MAIN'E INDI: fikstur uzak ucu de ilerletir. Bu satir sus payi DEGIL,
            # kapinin ON KOSULUDUR — `bundle_commitleri` artik HEAD'in uzak main ucu
            # oldugunu KANIT ister (G bolumu tam bu kanidin YOKLUGUNU olcer).
            _git(depo, "update-ref", "refs/remotes/origin/" + ANA_DAL, "HEAD")

        _yaz(depo, "shop/src/index.js", "// v1\n")
        _yaz(depo, "belge.md", "x\n")
        _islet("taban", "2026-08-03T10:00:00+0000")
        kz_f = zaman_coz("2026-08-03T13:00:00Z")
        _yaz(depo, "shop/src/index.js", "// v2 — bundle degisti\n")
        _islet("bundle degisikligi", "2026-08-03T14:00:00+0000")
        com = bundle_commitleri(depo, ["shop/src/index.js"], kz_f)
        d_f1, g_f1, y_f1 = hukum(kz_f, com, zaman_coz("2026-08-03T16:01:00Z"))
        iddia("F1", "OLDURUCU — bundle commit'i canli koddan 121 dk yeni: BAYAT rc 1",
              d_f1 == "bayat" and g_f1 == 1 and RC[d_f1] == 1 and abs(y_f1 - 121.0) < 0.6)
        kz_taze = zaman_coz("2026-08-03T15:00:00Z")
        com2 = bundle_commitleri(depo, ["shop/src/index.js"], kz_taze)
        d_f2, g_f2, _ = hukum(kz_taze, com2, zaman_coz("2026-08-03T23:00:00Z"))
        iddia("F2", "KONTROL — ayni depo, deploy commit'ten SONRA: TAZE rc 0 "
                    "(yanlis-pozitif yok)",
              d_f2 == "taze" and g_f2 == 0 and RC[d_f2] == 0)
        _yaz(depo, "belge.md", "y\n")
        _islet("bundle DISI degisiklik", "2026-08-03T18:00:00+0000")
        com3 = bundle_commitleri(depo, ["shop/src/index.js"], kz_taze)
        d_f3, _, _ = hukum(kz_taze, com3, zaman_coz("2026-08-03T23:00:00Z"))
        iddia("F3", "bundle DISI commit bayatlik URETMEZ (ayirt edici eksen)",
              d_f3 == "taze")

        # SIG (shallow) checkout — CI'nin varsayilan hali (actions/checkout fetch-depth 1
        # + `git fetch --depth=1`). 🔴 OLCULDU: sig depoda SINIR commit'i EBEVEYNSIZ
        # goründügü icin yol-sinirli `git log` onu "her dosyaya dokunmus" sayar ->
        # derinlestirmeyen bir kapi YANLIS commit'i (bundle DISI olani) bayatlik sanar.
        # Yani hata YALNIZ sahte-taze degil, SAHTE-BAYAT da olabilir. Bu yuzden iddia
        # "kac tane" degil "HANGI SHA" uzerinedir: sig cevabi TAM depo cevabina esit olmali.
        sig = os.path.join(t, "sig")
        k = subprocess.run(["git", "clone", "-q", "--depth=1", "file://" + depo, sig],
                           capture_output=True, text=True)
        if k.returncode == 0:
            _git(sig, "remote", "set-url", "origin", "file://" + depo)
            sig_mi = _git(sig, "rev-parse", "--is-shallow-repository").stdout.strip()
            # AYIRT EDICILIK: bu iddia YOL suzgecine DEGIL yalniz derinlestirmeye bakar
            # (yol suzgecinin kendi ayirt edici mutanti F3'te). Girdi = gecmisin dibi.
            gecmisi_yeterince_ac(sig, kz_f)
            sonra = _git(sig, "rev-parse", "--is-shallow-repository").stdout.strip()
            tam_n = len(_git(depo, "log", "--format=%H").stdout.split())
            sig_n = len(_git(sig, "log", "--format=%H").stdout.split())
            iddia("F4", "SIG checkout: gecmis kod zamanina kadar ACILIR (sig -> tam, "
                        "commit sayisi TAM depoyla esit); acilmazsa sinir commit'i "
                        "yol-sinirli log'da HER dosyaya dokunmus gorunur",
                  sig_mi == "true" and sonra == "false" and sig_n == tam_n and tam_n == 3)
        else:
            iddia("F4", "SIG checkout klonlanamadi -> OLCULEMEDI (yesil sayilmaz)", False)

    # ---- G: OLCULEN REF = OLCULMESI GEREKEN REF (4 Agu sorusturmasi) ------
    # 4 Agu'daki "ayrisma" CURUTULDU (aradaki deploy — dosya basi), ama sorusturmada
    # OLCULEN bir fail-open kaldi: HEAD uzak main ucunun gerisindeyken `git log --since`
    # BOS doner ve kapi "taze, 0,0 dk, rc 0" der. Bu bolum o hali GERCEK git deposunda
    # yeniden uretir. Her OLDURUCU'nun yaninda TEK DEGISKENI degistirilmis KONTROL vardir.
    print("\nG. OLCULEN REF VE CALISMA AGACI (fail-closed)")
    with tempfile.TemporaryDirectory() as t:
        depo = os.path.join(t, "depo")
        os.makedirs(depo)
        _git(depo, "init", "-q", "-b", ANA_DAL)
        _git(depo, "config", "user.email", "t@t")
        _git(depo, "config", "user.name", "t")

        def _g_islet(mesaj, iso, uc_ilerlesin=True):
            env = dict(os.environ, GIT_AUTHOR_DATE=iso, GIT_COMMITTER_DATE=iso)
            subprocess.run(["git", "-C", depo, "add", "-A"], capture_output=True)
            subprocess.run(["git", "-C", depo, "commit", "-q", "-m", mesaj],
                           env=env, capture_output=True, text=True)
            if uc_ilerlesin:
                _git(depo, "update-ref", "refs/remotes/origin/" + ANA_DAL, "HEAD")

        _yaz(depo, "shop/src/index.js", "// v1\n")
        _yaz(depo, "belge.md", "x\n")
        _g_islet("taban", "2026-08-03T10:00:00+0000")
        taban_sha = _git(depo, "rev-parse", "HEAD").stdout.strip()
        _yaz(depo, "shop/src/index.js", "// v2 — ODEME YOLU DEGISTI\n")
        _g_islet("odeme yolu commit'i", "2026-08-03T14:00:00+0000")
        kz_g = zaman_coz("2026-08-03T13:00:00Z")
        simdi_g = zaman_coz("2026-08-03T20:00:00Z")
        YOL = ["shop/src/index.js"]

        # G1 OLDURUCU — 4 Agu sorusturmasinda olculen imzanin BIREBIR fiksturu.
        _git(depo, "checkout", "-q", taban_sha)          # HEAD uzak ucun GERISINDE
        iddia("G1", "OLDURUCU — HEAD uzak main ucunun GERISINDE: OLCULEMEDI. (Eski kod "
                    "burada `git log` 0 kayit gorup 'taze', 0,0 dk, rc 0 dondururdu — "
                    "olculen sahte-taze)",
              _olculemedi_mi(bundle_commitleri, depo, YOL, kz_g))
        # G2 KONTROL — AYNI depo, TEK degisken: HEAD konumu. Kapi "her seye olculemedi"
        # demiyor; olcum FIILEN yapiliyor ve dogru hukum cikiyor.
        _git(depo, "checkout", "-q", ANA_DAL)
        com_g = bundle_commitleri(depo, YOL, kz_g)
        d_g, ge_g, y_g = hukum(kz_g, com_g, simdi_g)
        iddia("G2", "KONTROL — ayni depo, HEAD uzak uc'ta: olcum YAPILIR, BAYAT rc 1 "
                    "(360,0 dk)",
              d_g == "bayat" and ge_g == 1 and RC[d_g] == 1 and abs(y_g - 360.0) < 0.6)
        # G3 — HEAD uzak ucun ILERISINDE (itilmemis yerel commit): olcum SURMELI.
        # Yanlis-pozitif butcesi: bu kapi 15 dk'da bir kosuyor, mesru hal kirmizi YAKMAZ.
        _yaz(depo, "shop/src/index.js", "// v3 — henuz itilmedi\n")
        _g_islet("itilmemis yerel commit", "2026-08-03T16:00:00+0000", uc_ilerlesin=False)
        com_g3 = bundle_commitleri(depo, YOL, kz_g)
        iddia("G3", "HEAD uzak ucun ILERISINDE (itilmemis commit) -> olcum SURER, kume "
                    "eksik degil (2 commit)", len(com_g3) == 2)
        _git(depo, "update-ref", "refs/remotes/origin/" + ANA_DAL, "HEAD")

        # G4 — CI'nin FIILEN kurdugu hal: `git fetch --depth=1 origin main` FETCH_HEAD
        # birakir; `refs/remotes/origin/main` OLMAYABILIR. Kanit FETCH_HEAD'den gelmeli,
        # yoksa duzeltme her 15 dk'da bir CI'yi kirmizi yakardi (yanlis-pozitif butcesi).
        ci = os.path.join(t, "ci")
        os.makedirs(ci)
        _git(ci, "init", "-q", "-b", ANA_DAL)
        _git(ci, "config", "user.email", "t@t")
        _git(ci, "config", "user.name", "t")
        _yaz(ci, "shop/src/index.js", "// ci\n")
        subprocess.run(["git", "-C", ci, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", ci, "commit", "-q", "-m", "ci taban"],
                       env=dict(os.environ, GIT_AUTHOR_DATE="2026-08-03T10:00:00+0000",
                                GIT_COMMITTER_DATE="2026-08-03T10:00:00+0000"),
                       capture_output=True)
        ci_head = _git(ci, "rev-parse", "HEAD").stdout.strip()
        with open(os.path.join(ci, ".git", "FETCH_HEAD"), "w", encoding="utf-8") as f:
            f.write("%s\t\tbranch '%s' of file://uzak\n" % (ci_head, ANA_DAL))
        try:                       # kanit YOKSA bu iddia KIRMIZI yanmali, COKMEMELI
            g4 = olculen_ref_dogrula(ci)
        except Olculemedi:
            g4 = None
        iddia("G4", "CI HALI — refs/remotes/origin/main YOK, FETCH_HEAD == HEAD: kanit "
                    "FETCH_HEAD'den gelir, kapi YESIL kalir (CI 15 dk'da bir kosuyor)",
              g4 == (ci_head, "FETCH_HEAD"))
        # G5 — hicbir aday uc okunamiyor: "guncel VARSAYMA" YOK.
        os.remove(os.path.join(ci, ".git", "FETCH_HEAD"))
        iddia("G5", "hicbir uzak uc adayi okunamiyor -> OLCULEMEDI (sessiz 'taze' YOK)",
              _olculemedi_mi(olculen_ref_dogrula, ci))

        # G6 OLDURUCU — calisma agaci HEAD'den ayrik (bundle dosyasinda).
        _yaz(depo, "shop/src/index.js", "// KAYDEDILMEMIS odeme degisikligi\n")
        iddia("G6", "OLDURUCU — bundle dosyasinda kaydedilmemis fark: yol kumesi diskten, "
                    "gecmis HEAD'den -> OLCULEMEDI",
              _olculemedi_mi(bundle_commitleri, depo, YOL, kz_g))
        # G7 KONTROL — TEK degisken: kirli dosya bundle DISINDA. Bu depoda `urunler.json`
        # surekli yaziliyor ve bundle kumesinde DEGIL; kapi onu tetiklememeli.
        _yaz(depo, "shop/src/index.js", "// v3 — henuz itilmedi\n")   # geri al
        _yaz(depo, "belge.md", "bundle DISI kirlilik\n")
        com_g7 = bundle_commitleri(depo, YOL, kz_g)
        iddia("G7", "KONTROL — kirlilik bundle DISINDA (belge.md): olcum SURER "
                    "(yanlis-pozitif yok)", len(com_g7) == 2)

    print("\nIDDIA: %d · KIRMIZI: %d %s"
          % (_SAYAC["n"], len(_SAYAC["kirmizi"]), _SAYAC["kirmizi"] or ""))
    return 1 if _SAYAC["kirmizi"] else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true", dest="test",
                    help="OFFLINE kabul testi (ag/wrangler YOK)")
    ap.add_argument("--gh-ozet", action="store_true", dest="gh",
                    help="durumu $GITHUB_OUTPUT (durum=...) ve $GITHUB_STEP_SUMMARY'ye yaz")
    a = ap.parse_args()
    if a.test:
        return kendini_test()
    return canli_olcum(gh=a.gh)


if __name__ == "__main__":
    sys.exit(main())
