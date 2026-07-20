#!/usr/bin/env python3
"""PreToolUse (Bash) kapisi — MIMAR ICRA KAPISI (20 Tem).

TESHIS: tools/mimar-kod-kilidi.py yalnizca DOSYA YAZARLIGINI denetliyordu. Mimar
analiz/olcum betigini scratchpad'e yazip 'python3 /private/tmp/.../analiz.py' ile
Bash'ten kosturunca repoya tek satir girmiyor, kilit hic yanmiyordu. Bu kapi o ikinci
ayagi kapatir — AMA YALNIZ segment BASINDA duran bir yorumlayici/betik icin: komut
';', '|', '&&', '||', '&' ile segmentlere bolunur ve denetim her segmentin ILK gercek
token'ina (yorumlayici mi, dogrudan-betik mi) uygulanir. Yani 'python3 /dis/x.py'
reddedilir; segment basi bir LAUNCHER (xargs / find -exec / make / sudo ...) ise ya da
ad ICRA_UZANTILARI ile bitmiyorsa denetim HIC uygulanmaz (BILINEN BYPASS'LAR'a bak).
Kapi bir DISIPLIN cihazidir, guvenlik siniri DEGIL — kapsami budur ve bilerek buyutulmez.

AMAC mimari felc etmek DEGIL: ICRA engellenir, YARGI + DOGRULAMA serbest kalir.

GERCEKTE REDDEDILEN (segment BASI yorumlayici ya da dogrudan-betik iken):
  * python3/node/sh/bash/... ile REPO DISI bir betik dosyasi kosturmak
    (or. python3 /private/tmp/.../scratchpad/analiz.py)
  * yorumlayiciya satir-ici kod vermek (-c / -e / --eval) ya da stdin'den kod okutmak
    (cat x.py | python3) — betigi hic yazmadan ayni icrayi yapmanin kestirmesi
  * repo disi calistirilabilir dosyayi dogrudan cagirmak — YALNIZ ICRA_UZANTILARI ile
    biten ad (/tmp/.../x.sh, ./analiz.py); UZANTISIZ +x dosya ('./analiz') YAKALANMAZ
  * HERHANGI bir bicimde '-m' (ayrik/bitisik/=li/birlesik) — izinli modul beyaz listesi disi
  * argumanlarda repo DISINA cozulen HERHANGI bir yol parcasi (bayraga bitisik olsa da)
  * yorumlayiciya kod enjekte eden tehlikeli ortam degiskeni (PYTHONPATH=/tmp/... python3 ...)

🔴 20 Tem TASARIM KARARI (mimar) — AYRISTIRMAYI TAKLIT ETME, SUPHEDE REDDET:
  Uc onarim turu boyunca delikler hep AYNI eksende cikti: kapi, Python'un argument
  parser'ini taklit etmeye calisiyordu (-W/-X deger alir mi, '-vs' birlesik mi, '='
  soyulur mu). Olculen sonuc: '-W ignore -m pip install requests' ve
  '-m unittest discover -vs/private/tmp/disari' ALLOW aliyordu ve repo DISINDA gercek
  dosya yazildi. Bu yaris kaybediliyor → ayristirici (modul_ayikla/test_hedefleri/
  _bayrak_degeri) SILINDI, yerine iki KABA + FAIL-CLOSED tarama kondu:
    R1) token taramasi: '-m' herhangi bir bicimde gorunuyorsa DENY (beyaz liste haric);
        kisa-bayrak kumesinde 'm' harfi geciyorsa da DENY (supheli form = red).
    R2) yol taramasi: icinde '/' gecen (ya da '.' ile baslayan) HER token, bayrak oneki
        SOYULARAK ve SOYULMADAN cozulur; iki okumadan BIRI repo disi cikarsa DENY.
  Bunu mumkun kilan sey KIMLIK EKSENI: agent_id DOLU cagrilar (ISCI) bu kapidan zaten
  MUAF. Yani sertlestirmenin yanlis-pozitif bedeli YALNIZ mimari etkiler — ve mimarin
  zaten bu komutlari kosturmamasi gerekiyor. Isci felce ugramaz (kanit: ISCI ikizleri).
  KAYBEDILEN: mimar artik '-m pytest <repo-ici>' / '-m unittest discover -s <repo-ici>'
  kosturamaz (eskiden acikti). Bilinerek verildi: bu is zaten isciye delege edilir.

SERBEST (yanlislikla kapatma — kapatirsan is durur):
  * repodaki MEVCUT araclar: python3 tools/d1-sync.py --durum, node tools/parite-test.js,
    python3 tools/durum.py, node --check tools/x.js ...
  * git'in tamami (status/diff/log/merge/commit/push/worktree) — merge mimarin kapisidir
  * curl ile salt-okunur canli dogrulama, grep/ls/rg/jq/wc/head/tail vb.
  * codex exec ile delegasyon
  * /.claude/worktrees/ icinden calisan oturumlar (muhendis alani) — TAM muaf

BILINEN BYPASS'LAR (kapi bir DISIPLIN cihazidir, hapishane DEGIL — memory/kapi-disiplin-ilkesi.md;
KAYITLI olmalari sart ama KAPATILMAZLAR: yeni launcher-yakalama kurali sonsuz launcher oyunu +
yeni yanlis-pozitif acar, ilke bunu yasaklar). 1-2-3'un ORTAK KOK NEDENI TEK: denetim yalnizca
segmentin YORUMLAYICI-BASLI (ya da dogrudan-betik) ilk token'ina uygulanir; girdi ayri
token/stdin ile tasinirsa ya da ad ICRA_UZANTILARI ile bitmezse segment "yorumlayici-basli"
gorunmez ve kural hic calismaz. 1-2-3 MAIN'de de vardir — bu dal onlari ACMADI (yeni degil).
  1. LAUNCHER-ARKASI cagri: 'echo /dis/x.py | xargs python3', 'find /dis -exec python3 {} \\;',
     ayni sinifta make / sudo / watch / uv / npx — girdiyi AYRI token ya da stdin tasir, segment
     basi bu launcher'dir (SARMALAYICI listesinde DEGIL) → denetim hic uygulanmaz, repo disinda
     GERCEK icra olur. Kapatilmadi: her launcher'i saymak sonsuz liste + yanlis-pozitif; mimar
     'xargs python3' yaziyorsa bu refleks degil BILINCLI kacistir.
  2. UZANTISIZ +x dosya dogrudan cagrisi: './analiz' (uzantisiz, shebang'li) — dogrudan-cagri
     kalkani (asagida A blogu) YALNIZ ICRA_UZANTILARI ile biten adi yakalar, uzantisiz ad
     yorumlayici da degildir → ALLOW. Kapatilmadi: ayni kök (uzanti listesi); listeyi genisletmek
     veri/not dosyasi adlarinda yanlis-pozitif riski.
  3. 'git worktree add /private/tmp/x' TEK komutla kalici muaf bolge acar: yeni kok
     .git/worktrees'e KAYITLI olur, sonrasinda oraya betik yazmak (kod-kilidi) ve
     oradan betik kosturmak (bu kapi) SERBEST olur. BILEREK kapatilmadi — git yonetimi
     mimarin kapisidir ve engellemek merge/temizlik isini felc eder. Olcum:
     'git -C /Users/okan/dev/pruvo worktree list' cikti sayisi.
  4. agent_id DOLU cagri (alt ajan) — kapi hicbir kural uygulamaz; stderr izi
     "MIMAR-KAPISI allow ISCI".
  5. Commit duzlemindeki bypass'lar tools/mimar-commit-kapisi.py bas yorumunda.
"""
import json
import os
import re
import shlex
import sys

REPO_ONEKI = "/Users/okan/dev/pruvo/"
GIT_WORKTREE_KAYIT = "/Users/okan/dev/pruvo/.git/worktrees"


def kimlik(girdi):
    aid = girdi.get("agent_id")
    if isinstance(aid, str) and aid.strip():
        return "ISCI"
    return "MIMAR"


def iz_bas(etiket):
    """ALLOW kararinda stderr'e TEK SATIR iz; stdout BOS kalir (permission semantigi
    degismez). Kabul testi bununla 'kapi kostu ve izin verdi' ile 'kapi yok/coktu'
    durumunu ayirir — eski surumde 'stdout bos => allow' fail-open korlugu vardi."""
    try:
        sys.stderr.write("MIMAR-KAPISI allow " + etiket + "\n")
    except Exception:
        pass


def kayitli_worktree_kokleri():
    """.git/worktrees/*/gitdir → worktree kokleri. Hata olursa BOS kume (dar davranis).
    Govde tools/mimar-kod-kilidi.py ile BIREBIR AYNI — bilerek KOPYALANDI: ortak modul
    tek ariza noktasi olurdu (iki kapi birden bozulur) ve import yolu kancanin cwd'sine
    bagimli olurdu."""
    kokler = set()
    try:
        for ad in os.listdir(GIT_WORKTREE_KAYIT):
            gitdir = os.path.join(GIT_WORKTREE_KAYIT, ad, "gitdir")
            try:
                with open(gitdir, encoding="utf-8") as f:
                    icerik = f.read().strip()
            except Exception:
                continue
            if not icerik:
                continue
            kok = os.path.normpath(os.path.dirname(icerik))
            if kok and kok != "/":
                kokler.add(kok)
    except Exception:
        return set()
    return kokler


YORUMLAYICI = re.compile(
    r"^(python|python2|python3(\.\d+)?|pypy3?|node|nodejs|deno|bun|ts-node|tsx|"
    r"sh|bash|zsh|ksh|dash|ruby|perl|php|osascript)$"
)

ICRA_UZANTILARI = (
    ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".sh", ".bash", ".zsh", ".command", ".rb", ".pl",
)

# Basa yapisabilen zararsiz sarmalayicilar — soyulur, arkasindaki gercek komuta bakilir.
SARMALAYICI = {"env", "command", "exec", "nohup", "time", "caffeinate", "stdbuf", "nice"}

SURUM_BAYRAKLARI = {"--version", "-V", "--help", "-h", "-v"}
SATIR_ICI = {"-c", "-e", "--eval", "--eval-file", "-p", "--print", "-"}

# 'python3 -m X' : X bir MODUL, dosya degil — repo-ici/disi kontrolu ise yaramaz.
# Cogu modul keyfi icra kapisidir: pip (kurulum betigi calistirir), timeit/pdb/trace
# (-s ile kod alir), venv, http.server (disari acar). Bu yuzden -m VARSAYILAN KAPALI,
# yalnizca zararsiz okuma/bicimlendirme modulleri izinli.
IZINLI_MODULLER = {"json.tool", "base64", "calendar", "this"}

# TEST_MODULLERI (pytest/unittest) KUMESI KALDIRILDI (20 Tem, 4. tur). Neyi kaybettik:
# mimarin '-m pytest <repo-ici>' kosturma hakkini. Neden: bu izin, hedef yollarini
# ayristirmayi (kisa/uzun/bitisik/=li bayrak degeri) ZORUNLU kiliyordu ve delikler tam
# oradan cikti (-vs/yol, -s=/yol). Kural sayisi azaldi, semantik netlesti: -m = DENY.

# Yorumlayiciya disaridan kod enjekte eden ortam degiskenleri (VAR=deger python3 ...).
TEHLIKELI_ENV = {
    "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME", "PYTHONEXECUTABLE", "PYTHONWARNINGS",
    "NODE_OPTIONS", "NODE_PATH", "NODE_REPL_EXTERNAL_MODULE",
    "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
    "RUBYOPT", "PERL5OPT", "BASH_ENV", "ENV", "IFS", "PATH",
}

GEREKCE_BASI = "MİMAR İCRA KAPISI (20 Tem): "
GEREKCE_SONU = (
    " ÇÖZÜM: (a) BU İŞİ WORKTREE'DE ÇALIŞAN BİR İŞÇİYE VER — işçi çağrılarında "
    "(agent_id dolu) bu kapı hiçbir kural uygulamaz; kabul testini ona YAZDIR "
    "(ör. tools/mimar-kilit-test.py'ye vaka ekletip 'python3 tools/mimar-kilit-test.py' "
    "ile kapat). Uzun hali: işi MÜHENDİS/USTA/MARABA'ya ya da Codex'e DELEGE et (Agent aracı: "
    "model opus/sonnet + isolation worktree + background) ve kabul testini ona YAZDIR; "
    "(b) ölçmek istiyorsan repodaki MEVCUT aracı koştur — node tools/parite-test.js, "
    "node tools/parite-ege.js, python3 tools/d1-sync.py --durum, python3 tools/durum.py, "
    "python3 tools/olculmemis-siparis.py, node --check <repo dosyası>; "
    "(c) yeni bir ölçüm gerekiyorsa onu .md spec'ine çalıştırılabilir KABUL TESTİ olarak "
    "yaz, mühendis repoya koysun — sonra sen koşturursun. "
    "SERBEST: git (status/diff/log/merge/commit/push), curl, grep/ls/jq, repo altındaki "
    "tools/ araçları, /.claude/worktrees/ içinden çalışan mühendis oturumları."
)


def reddet(neden):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": GEREKCE_BASI + neden + GEREKCE_SONU,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def segmentlere_ayir(komut):
    """Tirnak durumunu gozeterek ;, &&, ||, |, &, yeni-satir uzerinden bol."""
    segmentler = []
    parca = ""
    tirnak = None
    i = 0
    n = len(komut)
    while i < n:
        c = komut[i]
        if tirnak:
            parca += c
            if c == tirnak:
                tirnak = None
            i += 1
            continue
        if c in "'\"":
            tirnak = c
            parca += c
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            parca += komut[i:i + 2]
            i += 2
            continue
        if komut[i:i + 2] in ("&&", "||", ";;"):
            segmentler.append(parca)
            parca = ""
            i += 2
            continue
        if c in ";|&\n":
            segmentler.append(parca)
            parca = ""
            i += 1
            continue
        parca += c
        i += 1
    segmentler.append(parca)
    return [s.strip() for s in segmentler if s.strip()]


def parcala(segment):
    try:
        return shlex.split(segment)
    except Exception:
        return segment.split()


def sarmalayici_soy(tokenlar):
    """Basa yapisan env atamalarini/sarmalayicilari soyar.
    Doner: (kalan_tokenlar, gorulen_env_atamalari)."""
    atamalar = []
    while tokenlar:
        ilk = os.path.basename(tokenlar[0])
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", tokenlar[0])
        if m:
            atamalar.append(m.group(1))
            tokenlar = tokenlar[1:]
            continue
        if ilk in SARMALAYICI:
            tokenlar = tokenlar[1:]
            # env -i / -S gibi bayraklari da atla
            while tokenlar and tokenlar[0].startswith("-"):
                tokenlar = tokenlar[1:]
            continue
        break
    return tokenlar, atamalar


def _coz(yol, cwd):
    """Token'i mutlak yola cozer (goreli ise cwd'ye gore)."""
    yol = os.path.expanduser(yol)
    if not os.path.isabs(yol):
        yol = os.path.join(cwd, yol)
    return os.path.normpath(yol)


def repo_ici(yol, cwd):
    """Repo agacinin ICINDE mi? Ana checkout ONEKI ya da git'e KAYITLI bir worktree koku.
    Kayit ekseni P2'nin (repo DISINDAKI mesru worktree, or. /private/tmp/pruvo-toka-jenerator)
    kimlikten BAGIMSIZ yedegidir: agent_id gelmese bile o betik kosar."""
    yol = _coz(yol, cwd)
    if yol.startswith(REPO_ONEKI):
        return True
    for kok in kayitli_worktree_kokleri():
        if yol == kok or yol.startswith(kok + "/"):
            return True
    return False


def betik_siniri(argumanlar, cwd):
    """Yorumlayici bayraklarinin BITTIGI indeks = ilk GERCEK betik token'i.

    Yanlis-pozitif kalkani (vaka 129: 'python3 tools/durum.py -smth'): betikten SONRAKI
    argumanlar BETIGINDIR, yorumlayici bayragi degildir. Ama kalkan FAIL-CLOSED tutulur:
    sinir yalnizca token DISKTE VAR OLAN, repo-ici, calistirilabilir uzantili bir dosyaya
    cozuluyorsa kabul edilir. Eski surum "ilk tiresiz token"da kirilyordu — '-W ignore'
    gibi DEGER token'lari yuzunden -m denetimi komple atlaniyordu (olculmus delik A)."""
    for i, t in enumerate(argumanlar):
        if t.startswith("-"):
            continue
        if not t.lower().endswith(ICRA_UZANTILARI):
            continue
        if not repo_ici(t, cwd):
            continue
        if os.path.isfile(_coz(t, cwd)):
            return i
    return len(argumanlar)


def modul_suphesi(argumanlar, cwd):
    """R1 — '-m' TOKEN TARAMASI (ayristirma YOK, suphede RED).

    Python'un hangi kisa bayraginin deger aldigini TAKLIT ETMEYIZ. Betik sinirina kadar
    olan her tek-tireli token'a bakariz:
      * govde 'm' ile basliyorsa  -> modul adi ('-m X', '-mX', '-m=X'); beyaz listede
        degilse DENY.
      * govde icinde '/' varsa    -> yol parcasidir, R2'nin isi (burada atlanir).
      * govde icinde 'm' geciyorsa-> BIRLESIK kisa bayrak kumesi OLABILIR -> DENY.
    Doner: (True, ayrinti) reddedilecekse."""
    sinir = betik_siniri(argumanlar, cwd)
    for i, t in enumerate(argumanlar[:sinir]):
        if not t.startswith("-") or t == "-" or t.startswith("--"):
            continue
        govde = t[1:]
        if govde.startswith("m"):
            modul = govde[1:]
            if modul[:1] in ("=", ":"):
                modul = modul[1:]
            if not modul:
                modul = argumanlar[i + 1] if i + 1 < len(argumanlar) else ""
            if modul in IZINLI_MODULLER:
                continue
            return True, (modul or "?")
        if "/" in t:
            continue
        if "m" in govde:
            return True, t
    return False, ""


def dis_yol(argumanlar, cwd):
    """R2 — YOL TARAMASI (bayrak degeri ayristirilmaz; IKI okuma, biri disaridaysa RED).

    Bir token YOL sayilir: icinde '/' geciyorsa ya da '.' ile basliyorsa. Bayraga
    bitisik/=li yazilmis deger ayristirilmaz; token HEM ham HEM de oneki soyulmus
    (ilk '/'den itibaren, ve '='den sonrasi) okunur. Okumalardan BIRI repo disina
    cozulurse DENY — belirsizlik DISARI sayilir. Olculmus delikler: '-vs/private/tmp/...'
    (birlesik kisa bayrak) ve '-s=/private/tmp/...' (esitlikli bitisik form)."""
    for t in argumanlar:
        adaylar = []
        if t.startswith("-"):
            if "/" in t:
                adaylar.append(t)
                adaylar.append(t[t.index("/"):])
            if "=" in t:
                adaylar.append(t.split("=", 1)[1])
        elif "/" in t or t.startswith("."):
            adaylar.append(t)
        for aday in adaylar:
            if not aday:
                continue
            if "/" not in aday and not aday.startswith("."):
                continue
            if not repo_ici(aday, cwd):
                return aday
    return None


def main():
    try:
        girdi = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # KIMLIK (20 Tem kalibrasyonu): agent_id DOLU ise cagri ALT AJANDAN gelir — mesru
    # muhendis. Bash kapisi hicbir kural uygulamaz (satir-ici kod, scratchpad betigi,
    # -m pytest, repo-disi betik: hepsi serbest). Olculmus ariza buydu: kapi 4 kez mesru
    # isi engelledi, bir isci sed'e kacti (denetlenemez yol) = kapi guvenligi AZALTTI.
    if kimlik(girdi) == "ISCI":
        iz_bas("ISCI")
        sys.exit(0)

    komut = (girdi.get("tool_input") or {}).get("command") or ""
    if not komut.strip():
        iz_bas("MIMAR-kural-yok")
        sys.exit(0)

    # NOT (20 Tem, mimar sorusu (a)): burada eskiden "cwd worktree icindeyse TAM MUAF"
    # diye bir OTURUM muafiyeti vardi. KALDIRILDI — cwd saldirgan/kullanici tarafindan
    # kaydirilabilen bir sinyal (kabuk cwd'si cagrilar arasi kalici, 'cd' makine olarak
    # engellenmiyor) ve gercek worktree dizinleri diskte mevcut, yani "cd <worktree>" tek
    # komutluk bir muafiyet anahtari olurdu. Yerine TAMAMEN YOL-TABANLI ve kaydirilamaz
    # kural: repo agacinin (worktree'ler dahil) ICINDEKI betik kosar, DISINDAKI kosmaz.
    # Muhendis betigini kendi worktree'sine yazar — zaten kalici, gorunur ve denetlenebilir.
    # cwd yalnizca GORELI yolu cozmek icin kullanilir; muafiyet vermez.
    cwd = girdi.get("cwd") or REPO_ONEKI.rstrip("/")

    for segment in segmentlere_ayir(komut):
        tokenlar, env_atamalari = sarmalayici_soy(parcala(segment))
        if not tokenlar:
            continue
        argv0 = tokenlar[0]
        ad = os.path.basename(argv0)

        # A) Repo disi calistirilabilir dosyayi dogrudan cagirma (./x.sh, /tmp/.../x.py)
        if ("/" in argv0 or argv0.startswith(".")) and argv0.lower().endswith(ICRA_UZANTILARI):
            if not repo_ici(argv0, cwd):
                reddet(
                    "repo DIŞINDAKİ bir betiği doğrudan çalıştırıyorsun (" + argv0 + "). "
                    "Mimar kendi yazdığı programı koşturmaz — icra MÜHENDİSİN işidir."
                )
            continue

        if not YORUMLAYICI.match(ad):
            continue

        argumanlar = tokenlar[1:]

        # A2) Yorumlayiciya kod enjekte eden ortam degiskeni (PYTHONPATH=/tmp/... python3 ...)
        tehlikeli = [a for a in env_atamalari if a.upper() in TEHLIKELI_ENV]
        if tehlikeli:
            reddet(
                "yorumlayıcıya ortam değişkeniyle kod enjekte ediyorsun (" +
                ", ".join(tehlikeli) + "). Repo içindeki bir betik bile bu değişkenlerle "
                "repo dışından kod yükler."
            )

        # B) Surum/yardim: zararsiz
        if argumanlar and argumanlar[0] in SURUM_BAYRAKLARI:
            continue

        # C) Satir-ici kod / stdin'den kod: betigi hic yazmadan icra — reddedilir
        satir_ici = False
        for t in argumanlar:
            if t in SATIR_ICI:
                satir_ici = True
                break
            # bash -lc, sh -ec gibi birlesik bayraklar
            if ad in ("sh", "bash", "zsh", "ksh", "dash") and re.match(r"^-[a-zA-Z]*c$", t):
                satir_ici = True
                break
        if satir_ici:
            reddet(
                "yorumlayıcıya satır-içi kod veriyorsun (" + ad + " -c/-e/--eval ya da "
                "stdin). Bu, betiği hiç yazmadan aynı icrayı yapmanın kestirmesi — kapalı."
            )

        # D) [KALDIRILDI] "bayraga gomulu repo-disi BETIK yolu" ayri kural olarak
        #    gerekmiyor: R2 (dis_yol) yalnizca betik uzantililari degil, argumanlardaki
        #    HER yol parcasini denetler — daha genis ve daha az kural.

        # E/R1) '-m' TOKEN TARAMASI — ayristirma yok, suphede RED.
        supheli, ayrinti = modul_suphesi(argumanlar, cwd)
        if supheli:
            reddet(
                "yorumlayıcıya '-m' (modül) verdin ya da modül olabilecek şüpheli bir kısa "
                "bayrak kümesi var (" + ayrinti + "). '-m' modül üzerinden keyfi icra "
                "kapısıdır (pip kurulum betiği koşturur; timeit/pdb/trace -s ile kod alır; "
                "venv/http.server ortamı değiştirir/dışarı açar) ve mimar tarafında "
                "ayrıştırma YAPILMAZ — şüpheli her form kapalıdır. İzinli modüller yalnız: " +
                ", ".join(sorted(IZINLI_MODULLER)) + "."
            )

        # E2/R2) YOL TARAMASI — argumanlarda repo DISINA cozulen parca varsa RED.
        disari = dis_yol(argumanlar, cwd)
        if disari:
            reddet(
                "komutun argümanlarında repo DIŞINA çözülen bir yol var (" + disari + "). "
                "Bayrağa bitişik/eşitlikli yazılmış olsa bile açılmaz; belirsizlik DIŞARI "
                "sayılır (fail-closed)."
            )

        # F) Betik yolunu bul. R2 '/' iceren token'lari zaten denetledi; F'nin KALAN isi:
        #    (a) ciplak yorumlayici (stdin'den kod), (b) '/' ICERMEYEN goreli betik adi
        #    ('python3 analiz.py') — bu cwd repo DISINDA iken R2'ye takilmaz.
        betik = None
        for t in argumanlar:
            if t.startswith("-"):
                continue
            betik = t
            break

        if betik is None:
            reddet(
                "çıplak '" + ad + "' çağrısı stdin'den/etkileşimli kod çalıştırır "
                "(ör. 'cat betik.py | python3'). Kapalı."
            )

        if not repo_ici(betik, cwd):
            reddet(
                "repo DIŞINDAKİ bir betiği koşturuyorsun (" + betik + "). Scratchpad'e "
                "yazılmış analiz/ölçüm betikleri de buna dahildir — mimar kod yazmaz, "
                "kod YAZDIRIR; sonucu testle kapatır."
            )

    iz_bas("MIMAR-kural-yok")
    sys.exit(0)


main()
