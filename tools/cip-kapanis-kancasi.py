#!/usr/bin/env python3
"""CIP KAPANIS KANCASI (`Stop`) — biten cip, kapanmadan duramaz.

NEDEN VAR (olculmus, ucuncu tekrar): kapanis talimati 19 Agu'dan beri yururlukte
ama 3 Eyl'de kutuda `BASLIYORUM` yazip kapanisi OLMAYAN 13 blok olculdu (BaBa
sabah 19/23). Talimat tutmadi; `[[ucuncu-tekrar-sinif-kapisi]]` geregi tekil uyari
degil MEKANIZMA gerekti. Bu kanca cipin IYI NIYETINE degil `arsiv-kapisi.py`nin
rc'sine bakar.

SOZLESME — EZBERDEN DEGIL, BU MAKINEDE OLCULDU (4 Eyl 2026, Claude Code 2.1.222):
  stdin JSON alanlari: session_id · transcript_path · cwd · scratchpad_dir ·
    prompt_id · permission_mode · effort · hook_event_name · stop_hook_active ·
    last_assistant_message · background_tasks · session_crons
  BLOKLAMA: stdout'a {"decision":"block","reason":"..."} + exit 0
            -> modele "Stop hook feedback" olarak ulasir, oturum DURAMAZ.
  DONGU EMNIYETI: `stop_hook_active` bloklamadan dogan devam turunda true olur.

🔴 FAIL-OPEN, ISTISNASIZ. Bu kanca BES EVIN her oturumunda kosar; catlarsa filoyu
kilitler. Her hata yolu `exit 0` + BLOKLAMAMA ile biter. Kanca "olcemedim" diyorsa
karar VERMEZ — susar.

🔴 TAVAN: ayni oturumu en fazla `TAVAN` kez bloklar. `stop_hook_active` yalniz
ANLIK devam turunu isaretler; cip sonraki turda yine durmak isterse alan tekrar
false gelir ve tavan olmadan kanca sonsuz dongu uretirdi — kacinmaya calistigimiz
yakimin ta kendisi.
"""

import json
import os
import subprocess
import sys

TAVAN = 2
SAYAC_DIZIN = os.path.expanduser("~/.claude/cron/.cip-kapanis-sayaci")
KANONIK_KAPI = "/Users/okan/dev/pruvo/tools/arsiv-kapisi.py"
KANONIK_ENV = "PRUVO_KANONIK_TOOLS"


def _kapi_yolu():
    """(yol, nereden) — hukum kaynagi `arsiv-kapisi.py`nin yolu ve HANGI EKSENDEN.

    🔴 OLCULMUS KUSUR (5 Eyl): yol YALNIZ `KANONIK_KAPI` sabitiydi ve o sabit
    OKAN'IN MAKINESINE ozeldir. CI runner'inda checkout `/home/runner/work/...`
    altindadir, sabit yol YOKTUR -> kanca `arsiv-kapisi.py yok` deyip FAIL-OPEN
    geciyordu. Yani kabul bataryasinin "bloklamali" vakalari CI'da yapisal olarak
    kirmizi, kancanin kendisi ise CI evreninde OLU idi. Yerelde yol VAR oldugu
    icin bu korluk yerelde HIC gorunmez ([[kapinin-menzili-cagri-yeridir]]).

    Mutasyon turu bu kancanin KOPYASINI gecici bir dizine yazip kosar; kopyanin
    yaninda `arsiv-kapisi.py` YOKTUR. Kopyayi kosan harness kanonik `tools/`u BILIR
    ve `PRUVO_KANONIK_TOOLS` ile soyler (arsiv-kapisi.py ile AYNI sozlesme, ikinci
    bir isim acilmadi).

    🔴 IKINCI OLCUM (10 Eyl, cip `KraL-Tamirci-10Eyl`) — 5 Eyl'in ONARIMI YARIM
    KALMISTI: `KANONIK_KAPI` son satirda DENETIMSIZ donuyordu. Yani cozucu, iki
    ekseni de tutmayan bir kopyaya OKAN'IN DISKINDEKI yolu SESSIZCE veriyordu.
    Okan'in makinesinde o dosya VAR -> jeton dogru okunur -> batarya YESIL yanar;
    CI'da yok -> `_JETON_YEDEK` -> V8b KIRMIZI -> mutasyon turunun TABANI kirmizi
    -> 5 mutantin BESI de HIC OLCULMEZ. Yesili ureten sey sozlesme degil KOSUCUNUN
    DISKIYDI ([[iki-kollu-govde-tek-sabite-capalanirsa-kosucunun-diskini-olcer]]).
    CARE, `arsiv-kapisi.py::_kanonik_kaynak()` ile AYNI desendir (ikinci desen
    acilmadi): her aday `isfile` ile DENETLENIR, hicbiri tutmazsa donen sey
    `nereden="yok"`tur — sessiz ikame YOK. `nereden` ALANI OLCULEBILIR olsun diye
    disari verilir: kopyanin harness sozlesmesinden mi yoksa makineye ozel yoldan
    mi cozuldugu ARTIK bir iddiadir (V8e), maskelenemez."""
    adaylar = ((os.environ.get(KANONIK_ENV) or "", "harness ortami"),
               (os.path.dirname(os.path.realpath(__file__)), "arac dizini"),
               (os.path.dirname(KANONIK_KAPI), "makineye ozel kanonik repo"))
    for dizin, nereden in adaylar:
        aday = os.path.join(dizin, "arsiv-kapisi.py") if dizin else ""
        if aday and os.path.isfile(aday):
            return aday, nereden
    # Hicbir eksen tutmadi. FAIL-OPEN sozlesmesi korunur (main() `isfile` ile
    # bakar ve GECIRIR); ama hal ADIYLA tasinir, sessizce "cozuldu" sayilmaz.
    return KANONIK_KAPI, "yok"


KAPI, KAPI_NEREDEN = _kapi_yolu()

# ------------------- K396: KANCANIN ONERDIGI JETON, KAPININ OKUDUGU JETON OLMALI
# 🔴 OLCULEN KUSUR (10 Eyl 2026, iki ayri cip ust uste takildi): bu kanca cipe
# "'BEKLIYOR' olarak kutuya yaz" diyordu ama `BEKLIYOR` jetonu `arsiv-kapisi.py`
# GOVDESINDE HIC GECMIYORDU (`grep`=0). Kanca metni, kapinin IKINCI BIR KOPYASI
# gibi davraniyordu ve sessizce ondan AYRISMISTI ([[kapi-red-metni-ikinci-kopyadir]]).
# Yazan kisi kapiyi yesile cevirdigini SANIR, kapi rc=1 vermeye devam ederdi.
#
# 🔴 CARE GOMMEK DEGIL TURETMEK: jeton `kutu-arsivle.py`den (hukum kaynagi) OKUNUR.
# Sabit yazsaydik ayni ayrisma bir tur sonra geri gelirdi — ikiz tanim, tam olarak
# kapatilan kusurun kendisi ([[ikiz-tanim-sessiz-ayrisma]]).
# FAIL-OPEN sozlesmesi KORUNUR: kaynak okunamazsa kanca CATLAMAZ, jetonun yerine
# "olcemedim" diyen bir metin basar ve karar VERMEZ.
_JETON_YEDEK = "(jeton OKUNAMADI — `kutu-arsivle.py::MERGE_BEKLIYOR_JETON`e bak)"


def _muafiyet_jetonu():
    """`kutu-arsivle.py::MERGE_BEKLIYOR_JETON` — TEK KAYNAK, gomulu kopya YOK."""
    try:
        import importlib.util
        yol = os.path.join(os.path.dirname(os.path.realpath(KAPI)), "kutu-arsivle.py")
        if not os.path.isfile(yol):
            return _JETON_YEDEK
        spec = importlib.util.spec_from_file_location("kutu_arsivle_jeton", yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "MERGE_BEKLIYOR_JETON", None) or _JETON_YEDEK
    except Exception:                                        # noqa: BLE001
        return _JETON_YEDEK


MUAFIYET_JETONU = _muafiyet_jetonu()

RC_YESIL = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 2


def _gecti(sebep=None):
    """Bloklamadan cik. `sebep` yalnizca hata ayiklama icin stderr'e gider."""
    if sebep:
        sys.stderr.write("cip-kapanis-kancasi: GECTI — %s\n" % sebep)
    return 0


def _blokla(sebep):
    print(json.dumps({"decision": "block", "reason": sebep}, ensure_ascii=False))
    return 0


def _sayac(session_id):
    """(deger, artir_fn) — oturum basina blok sayisi; diske yazilamiyorsa 0 doner."""
    yol = os.path.join(SAYAC_DIZIN, "%s.txt" % session_id)
    deger = 0
    try:
        with open(yol, encoding="utf-8") as f:
            deger = int(f.read().strip() or "0")
    except (OSError, ValueError):
        deger = 0

    def artir():
        try:
            os.makedirs(SAYAC_DIZIN, exist_ok=True)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(str(deger + 1))
        except OSError:
            pass

    return deger, artir


def ana_checkout_mu(cwd):
    """cwd bir CIP agaci mi yoksa evin ANA checkout'u mu?

    Mimar oturumlari ana checkout'ta yasar ve CIP DEGILDIR — onlari bloklamak
    yanlis olur (mimarin isi surekli, tek bir dala baglanmaz)."""
    try:
        s = subprocess.run(["git", "-C", cwd, "rev-parse",
                            "--path-format=absolute", "--git-common-dir", "--git-dir"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None                                   # OLCULEMEDI
    if s.returncode != 0:
        return None
    parcalar = [x.strip() for x in s.stdout.splitlines() if x.strip()]
    if len(parcalar) < 2:
        return None
    ortak, kendi = os.path.realpath(parcalar[0]), os.path.realpath(parcalar[1])
    return ortak == kendi        # esitse ANA checkout, farkliysa worktree = CIP


def main():
    try:
        veri = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return _gecti("stdin JSON degil")
    if not isinstance(veri, dict):
        return _gecti("stdin sozluk degil")

    if veri.get("stop_hook_active"):
        return _gecti("stop_hook_active — dongu emniyeti")

    cwd = veri.get("cwd") or ""
    if not cwd or not os.path.isdir(cwd):
        return _gecti("cwd yok")

    ana = ana_checkout_mu(cwd)
    if ana is None:
        return _gecti("agac sinifi OLCULEMEDI — karar vermiyorum")
    if ana:
        return _gecti("ana checkout (mimar oturumu), cip degil")

    if not os.path.isfile(KAPI):
        return _gecti("arsiv-kapisi.py yok")

    session_id = str(veri.get("session_id") or "bilinmeyen")
    kac, artir = _sayac(session_id)
    if kac >= TAVAN:
        return _gecti("tavan (%d) doldu — bir daha bloklamiyorum" % TAVAN)

    # `--kutu` YALNIZ kabul bataryasi icindir: kanca uretimde ARGUMANSIZ cagrilir
    # (settings.json'daki komutta yoktur) ve kanonik kutuyu olcer. Bataryanin
    # fiksturlerinin canli kutuda karsiligi olamayacagi icin acik bir gecis sart;
    # ortam degiskeni YERINE acik bayrak secildi — ortam degiskeni sessiz bir
    # bypass yuzeyidir, bayrak cagri satirinda GORUNUR.
    kapi_argv = [sys.executable, KAPI, cwd]
    if "--kutu" in sys.argv:
        kapi_argv += ["--kutu", sys.argv[sys.argv.index("--kutu") + 1]]
    try:
        s = subprocess.run(kapi_argv, capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.SubprocessError) as e:
        return _gecti("kapi kosturulamadi: %s" % e)

    if s.returncode == RC_YESIL:
        return _gecti("kapi YESIL")

    kirmizi = [x.split()[0].replace("KOL=", "")
               for x in s.stdout.splitlines() if "HAL=KIRMIZI" in x]
    olculemedi = [x.split()[0].replace("KOL=", "")
                  for x in s.stdout.splitlines() if "HAL=OLCULEMEDI" in x]

    if s.returncode == RC_OLCULEMEDI and not kirmizi:
        # Kapi olcemedi. Kanca da karar VERMEZ — ama sessiz de kalmaz: bir kez
        # hatirlatir, sonra birakir (tavan zaten sinirliyor).
        artir()
        return _blokla(
            "KAPANIS KAPISI OLCEMEDI (%s). Bu bir ENGEL degil, bir UYARI: durmadan "
            "once kapanisini kutuya yaz. Neyi olcmek kapatir: "
            "`python3 %s %s` cikitisindaki OLCULEMEDI kolunun sebebi."
            % (", ".join(olculemedi) or "?", KAPI, cwd))

    artir()
    return _blokla(
        "DURMA — bu cip HENUZ KAPANMADI. `arsiv-kapisi.py` rc=%d, KIRMIZI kol: %s.\n"
        "Bu kollar kapanmadan oturum kapatilirsa arsivleme worktree'yi SILER ve is "
        "KAYBOLUR (olculmus vaka).\n"
        "Yap: (1) AGAC_KIRLI ise commit'le · (2) ITILMEMIS ise push'la · "
        "(3) KAPANIS_YOK ise ortak kutuya SAYILI KAPANIS blogunu yaz · "
        "(4) ICERIK_DISARIDA ise dali main'e al; merge hukmu SENDE DEGILSE once "
        "PUSH'la, sonra kapanis bloguna SU SATIRI birebir yaz:\n"
        "      %s: `<cip-adi>`\n"
        "    (muafiyet IKI SARTLIDIR: bu beyan + dalin uzak bir ref'te olmasi. "
        "Itilmemis dalda beyan HICBIR SEY degistirmez — kirmizi KALIR.)\n"
        "Sonra tekrar dur — bu kanca ayni oturumu en fazla %d kez uyarir.\n"
        "Kapinin tam ciktisi:\n%s"
        % (s.returncode, ", ".join(kirmizi) or "?", MUAFIYET_JETONU, TAVAN,
           s.stdout.strip()[:1500]))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                                   # noqa: BLE001
        # FAIL-OPEN: kanca catlarsa oturum ASLA kilitlenmez.
        sys.stderr.write("cip-kapanis-kancasi: catladi, GECIRILDI: %r\n" % (e,))
        sys.exit(0)
