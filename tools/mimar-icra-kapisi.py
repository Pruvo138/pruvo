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

🔵 22 TEM SERTLESTIRME (Okan: "mimar HICBIR is yapmaz, yalniz delege eder" — bugun elden
kacan sinif HAFIF OLCUMLER). Mimar kimliginde (agent_id BOS) EK REDLER:
  1. OLCUM/dosya-tarama: du df ps top vm_stat memory_pressure sysctl find wc head tail sed
     awk sort stat file — HERHANGI bir segmentte (pipe dahil) argv0 ise RED.
  2. curl/wget — canli dogrulama iscinin isi, ISTISNA YOK.
  3. codex (her bicim: 'codex' basename ya da ChatGPT.app tam yolu) — iscinin cagirdigi arac.
  4. python3/node — YALNIZ 'python3 tools/durum.py' ve 'python3 tools/d1-sync.py --durum'
     serbest (tam-yol ya da repo-goreli TAM esitlik; ekstra argüman = RED). Diger TUM
     tools/ araclari + node --check + -m + repo-ici betik = RED (test kosumu dahil).
  Bunun sonucu: eski '-m'/yol-ayristirma makinesi (modul_suphesi/betik_siniri) python
  tarafinda GEREKSIZ oldu ve KALDIRILDI — python GATE'i tek noktadadir (_py_izinli).
  dis_yol / F (betik repo_ici) / C (satir-ici) YALNIZ sh/bash/ruby/perl/php/osascript
  icin KALDI (onlarda -m yok). Sertligin bedeli YALNIZ mimara: ISCI (agent_id dolu)
  bu redlerin HICBIRINE takilmaz (main() basinda muaf; kanit: ISCI ikizleri).

SERBEST (mimar eliyle — yanlislikla kapatma, kapatirsan is durur):
  * python YALNIZ: python3 tools/durum.py + python3 tools/d1-sync.py --durum (baska YOK)
  * git'in tamami (status/diff/log/merge-base/merge/commit/push/worktree) — merge mimarin
    kapisidir; MAKINE reddine sokulmaz (kilitlenme riski), DAVRANISSAL kural isciye delege
  * gh (deploy/PR durumu), ls, grep, jq, echo, cat — okuma/yargi
  * /.claude/worktrees/ icinden calisan oturumlar (isci/muhendis alani) — agent_id ile TAM muaf

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

# === 22 TEM (mimarin HAFIF-OLCUM kacisi kapatilir) ===
# Mimar SERBEST kosabildigi YALNIZ IKI python komutu (tam-yol ya da repo-goreli TAM esitlik).
DURUM_YOL = REPO_ONEKI + "tools/durum.py"
D1_YOL = REPO_ONEKI + "tools/d1-sync.py"

# Olcum / dosya-tarama komutlari: bunlar mimarin elinden kacan siniftir (boyut, sayim,
# arama, icerik dokme). Komut zincirinin HERHANGI bir segmentinde (pipe dahil —
# segmentlere_ayir '|'den boler) argv0 olarak gorunurse RED. Olcum = iscinin isi.
OLCUM_KOMUTLARI = {
    "du", "df", "ps", "top", "vm_stat", "memory_pressure", "sysctl", "find",
    "wc", "head", "tail", "sed", "awk", "sort", "stat", "file",
}

# python/node ailesi — mimar tarafinda YALNIZ iki izinli komut, digeri RED (araç/test
# kosumu iscinin isi). sh/bash/ruby/perl/php/osascript bu kisitin DISINDA (asagida
# satir-ici + repo-disi betik denetimi ile ele alinir).
PY_NODE = re.compile(r"^(python|python2|python3(\.\d+)?|pypy3?|node|nodejs)$")

# Basa yapisabilen zararsiz sarmalayicilar — soyulur, arkasindaki gercek komuta bakilir.
SARMALAYICI = {"env", "command", "exec", "nohup", "time", "caffeinate", "stdbuf", "nice"}

SURUM_BAYRAKLARI = {"--version", "-V", "--help", "-h", "-v"}
SATIR_ICI = {"-c", "-e", "--eval", "--eval-file", "-p", "--print", "-"}

# '-m X' (python modul) DENETIMI KALDIRILDI (22 Tem). Neden: PY_NODE ALLOWLIST'i python'i
# yalnizca iki tam komuta indirdi — '-m pip'/'-m timeit'/'-m http.server' vs. artik
# allowlist tarafindan reddedilir (durum.py/d1-sync.py degil). Ayri bir -m ayristirmasi
# (modul_suphesi/betik_siniri) ARTIK GEREKSIZ ve NOBETSIZ olurdu: mimar tarafinda python
# GATE'i tek noktadadir (_py_izinli). O yuzden o iki fonksiyon + IZINLI_MODULLER kaldirildi.
# (sh/bash icin -m yok; onlar satir-ici + repo-disi betik + dis_yol ile denetlenir.)

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
    "(b) TEST/ÖLÇÜM/CANLI DOĞRULAMA koşumu (parite, build, filament, curl, du/ps/find/wc/"
    "head/tail/sed/awk/sort, node --check ...) mimarın DEĞİL işçinin işidir — spec'e "
    "çalıştırılabilir KABUL TESTİ yaz, mühendis repoya koysun, işçi koştursun. "
    "SERBEST (mimar eliyle): git (status/diff/log/merge-base/merge/commit/push/worktree), "
    "gh, ls, grep, jq, echo, cat; python yalnız 'python3 tools/durum.py' ve "
    "'python3 tools/d1-sync.py --durum'; /.claude/worktrees/ içinden çalışan işçi oturumları."
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


def _codex_var(tokenlar):
    """Segmentte HERHANGI bir bicimde Codex cagrisi var mi? 'codex' basename'i (or.
    'codex exec ...') ya da ChatGPT.app tam yolu (or.
    /Applications/ChatGPT.app/Contents/Resources/codex). Codex = ISCININ cagirdigi arac."""
    for t in tokenlar:
        if os.path.basename(t) == "codex":
            return True
        if "ChatGPT.app" in t:
            return True
    return False


def _py_izinli(ad, argumanlar, cwd):
    """22 Tem — mimar tarafinda python/node ALLOWLIST'i. YALNIZ iki tam komut serbest:
        python3 tools/durum.py            (baska argüman YOK)
        python3 tools/d1-sync.py --durum  (yalniz --durum)
    Yol tam-yol ya da repo-goreli olabilir (_coz ile cozulur); node/python2/pypy icin
    IZINLI KOMUT YOKTUR (hepsi RED). 'Baska argüman eklenirse RED' — len kontrolu bunu saglar."""
    if not re.match(r"^python3(\.\d+)?$", ad):
        return False
    if not argumanlar:
        return False
    ilk = _coz(argumanlar[0], cwd)
    if ilk == DURUM_YOL:
        return len(argumanlar) == 1
    if ilk == D1_YOL:
        return len(argumanlar) == 2 and argumanlar[1] == "--durum"
    return False


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

        # === 22 TEM EKLERI (mimar HAFIF-OLCUM/CANLI-DOGRULAMA/DELEGE-ARACI kacisi) ===
        # Bu uc kural her SEGMENT icin kosar; 'git log | head -5' -> ikinci segment 'head'
        # (segmentlere_ayir '|'den boler) -> RED. Kimlik ekseni degismedi: ISCI cagrilari
        # main() basinda zaten muaf, bu blok yalniz MIMAR'da kosar.
        if ad in OLCUM_KOMUTLARI:
            reddet(
                "ölçüm / dosya-tarama komutu (" + ad + "). Boyut, sayım, arama, içerik "
                "dökme, sıralama — bunlar İŞÇİNİN işidir; mimar okur, karar verir, ÖLÇTÜRÜR."
            )
        if ad in ("curl", "wget"):
            reddet(
                "ağ / canlı doğrulama komutu (" + ad + "). Canonical URL, feed, deploy "
                "çıktısı doğrulamasını İŞÇİYE yaptır (git ve gh serbest kalır)."
            )
        if _codex_var(tokenlar):
            reddet(
                "Codex çağrısı. Codex'i İŞÇİ çağırır (delege ettiğin işi o koşturur); "
                "mimar spec yazar, çağırmaz."
            )

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

        # === 22 TEM: PYTHON/NODE ALLOWLIST ===
        # Mimar tarafinda python3/node ile ARAÇ/TEST kosumu KAPALI (Okan 20 Tem
        # "test kosumu dahil"). YALNIZ iki komut serbest: durum.py ve d1-sync.py --durum.
        # A2 (tehlikeli env) BU KONTROLUN ONUNDE calisir -> 'PYTHONPATH=... python3
        # d1-sync.py --durum' allowlist'e ULASMADAN env yuzunden reddedilir.
        # sh/bash/ruby/perl/php/osascript BU kisitin DISINDA (asagida C/E2/F ile denetlenir).
        if PY_NODE.match(ad):
            if _py_izinli(ad, argumanlar, cwd):
                continue
            reddet(
                "python3/node ile bir araç/test koşturuyorsun (" + ad + " " +
                (" ".join(argumanlar[:3]))[:70] + "). Mimar tarafında SERBEST yalnız iki "
                "komut: 'python3 tools/durum.py' ve 'python3 tools/d1-sync.py --durum'. "
                "Parite/build/filament/node --check ... = İŞÇİNİN işi."
            )

        # B) Surum/yardim: zararsiz (python/node yukarida ele alindi; bu satir sh vb. icin)
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

        # E) [KALDIRILDI 22 Tem] python '-m' denetimi (modul_suphesi) PY_NODE allowlist'e
        #    devroldu — python/node bu noktaya ULASMAZ (yukarida continue/reddet). Bu
        #    noktadan itibaren yalniz sh/bash/ruby/perl/php/osascript kalir; onlarda -m yok.

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
