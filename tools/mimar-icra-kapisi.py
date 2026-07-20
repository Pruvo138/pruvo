#!/usr/bin/env python3
"""PreToolUse (Bash) kapisi — MIMAR ICRA KAPISI (20 Tem).

TESHIS: tools/mimar-kod-kilidi.py yalnizca DOSYA YAZARLIGINI denetliyordu. Mimar
analiz/olcum betigini scratchpad'e yazip 'python3 /private/tmp/.../analiz.py' ile
Bash'ten kosturunca repoya tek satir girmiyor, kilit hic yanmiyordu. Bu kapi o ikinci
ayagi kapatir: REPO DISINDAKI bir betigi yorumlayiciyla kosturmak reddedilir.

AMAC mimari felc etmek DEGIL: ICRA engellenir, YARGI + DOGRULAMA serbest kalir.

REDDEDILEN:
  * python3/node/sh/bash/... ile REPO DISI bir betik dosyasi kosturmak
    (or. python3 /private/tmp/.../scratchpad/analiz.py)
  * yorumlayiciya satir-ici kod vermek (-c / -e / --eval) ya da stdin'den kod okutmak
    (cat x.py | python3) — betigi hic yazmadan ayni icrayi yapmanin kestirmesi
  * repo disi calistirilabilir dosyayi dogrudan cagirmak (/tmp/.../x.sh, ./analiz.py)

SERBEST (yanlislikla kapatma — kapatirsan is durur):
  * repodaki MEVCUT araclar: python3 tools/d1-sync.py --durum, node tools/parite-test.js,
    python3 tools/durum.py, node --check tools/x.js ...
  * git'in tamami (status/diff/log/merge/commit/push/worktree) — merge mimarin kapisidir
  * curl ile salt-okunur canli dogrulama, grep/ls/rg/jq/wc/head/tail vb.
  * codex exec ile delegasyon
  * /.claude/worktrees/ icinden calisan oturumlar (muhendis alani) — TAM muaf

BILINEN BYPASS'LAR (kapi bir DISIPLIN cihazidir, hapishane DEGIL — KAYITLI olmalari sart):
  1. 'git worktree add /private/tmp/x' TEK komutla kalici muaf bolge acar: yeni kok
     .git/worktrees'e KAYITLI olur, sonrasinda oraya betik yazmak (kod-kilidi) ve
     oradan betik kosturmak (bu kapi) SERBEST olur. BILEREK kapatilmadi — git yonetimi
     mimarin kapisidir ve engellemek merge/temizlik isini felc eder. Olcum:
     'git -C /Users/okan/dev/pruvo worktree list' cikti sayisi.
  2. agent_id DOLU cagri (alt ajan) — kapi hicbir kural uygulamaz; stderr izi
     "MIMAR-KAPISI allow ISCI".
  3. Commit duzlemindeki bypass'lar tools/mimar-commit-kapisi.py bas yorumunda.
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

# Test kosucu modulleri: mimarin gorev tanimi "sonucu CALISTIRILABILIR TESTLE kapatmak"
# oldugu icin acilir, ama YALNIZ repo-ici hedeflerle (-m ile repo DISINA cikilamaz).
# IZINLI_MODULLER'e EKLENMEZ — ayri kume, ki mutasyon testi ikisini ayirt edebilsin.
TEST_MODULLERI = {"pytest", "unittest"}

# Yorumlayiciya disaridan kod enjekte eden ortam degiskenleri (VAR=deger python3 ...).
TEHLIKELI_ENV = {
    "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME", "PYTHONEXECUTABLE", "PYTHONWARNINGS",
    "NODE_OPTIONS", "NODE_PATH", "NODE_REPL_EXTERNAL_MODULE",
    "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
    "RUBYOPT", "PERL5OPT", "BASH_ENV", "ENV", "IFS", "PATH",
}

GEREKCE_BASI = "MİMAR İCRA KAPISI (20 Tem): "
GEREKCE_SONU = (
    " ÇÖZÜM: (a) işi MÜHENDİS/USTA/MARABA'ya ya da Codex'e DELEGE et (Agent aracı: "
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


def repo_ici(yol, cwd):
    """Repo agacinin ICINDE mi? Ana checkout ONEKI ya da git'e KAYITLI bir worktree koku.
    Kayit ekseni P2'nin (repo DISINDAKI mesru worktree, or. /private/tmp/pruvo-toka-jenerator)
    kimlikten BAGIMSIZ yedegidir: agent_id gelmese bile o betik kosar."""
    yol = os.path.expanduser(yol)
    if not os.path.isabs(yol):
        yol = os.path.join(cwd, yol)
    yol = os.path.normpath(yol)
    if yol.startswith(REPO_ONEKI):
        return True
    for kok in kayitli_worktree_kokleri():
        if yol == kok or yol.startswith(kok + "/"):
            return True
    return False


def _bayrak_degeri(ham):
    """Bayraga bitisik yazilmis degeri normalize eder: bastaki '=' (ve ':') soyulur.

    R2 kaniti: '=/private/tmp/disari' goreli sayilip cwd'ye ekleniyordu → repo-ici.
    Soyma DONGUSEL degil TEK katmanlidir; '==x' gibi patolojik girdide kalan '=x'
    yine GORELI sayilir ve o zaten repo-ici cozulur (fail-closed tarafta degiliz,
    ama bu form gecerli bir bayrak degeri degil)."""
    if not ham:
        return ""
    if ham[0] in "=:":
        return ham[1:]
    return ham


def modul_ayikla(argumanlar):
    """'-m MODUL' ve BITISIK '-mMODUL' formlarini birlikte ayiklar.

    🔴 20 Tem ONARIMI (R2 ikinci ayak): eski kod yalnizca `"-m" in argumanlar` bakiyordu
    → 'python3 -mpip install x' TUM -m denetimini atliyordu (sonra F adiminda ilk
    tiresiz token 'install' betik sanilip cwd'ye gore repo-ici cozuluyor ve ALLOW
    aliyordu). Olculdu ve KAPATILDI.

    YANLIS-POZITIF KALKANI: yalnizca ILK tirесiz token'a (betik/argv baslangici) KADAR
    olan yorumlayici bayraklarina bakilir. Boylece 'python3 tools/x.py -smth' gibi
    REPO BETIGINE giden argumanlar modul sanilmaz.

    Doner: (modul, modul_sonrasi_argumanlar) ya da (None, [])."""
    for i, t in enumerate(argumanlar):
        if not t.startswith("-"):
            break  # betik/argv basladi — sonrasi yorumlayici bayragi DEGIL
        if t.startswith("--") or t == "-":
            continue
        govde = t[1:]
        k = govde.find("m")
        if k < 0:
            continue
        # 'm'den onceki kisim yalnizca DEGERSIZ kisa bayrak harfleri olmali; degilse
        # bu token baska bir bayragin DEGERIDIR (or. '-s/repo/tools/mimar').
        if govde[:k] and not govde[:k].isalpha():
            continue
        kalan = _bayrak_degeri(govde[k + 1:])
        if kalan:
            return kalan, argumanlar[i + 1:]
        if i + 1 < len(argumanlar):
            return argumanlar[i + 1], argumanlar[i + 2:]
        return "", argumanlar[i + 1:]
    return None, []


def test_hedefleri(argumanlar):
    """'-m pytest/unittest' sonrasi HEDEF (yol) adaylarini cikarir.

    OLCULMUS ACIK (20 Tem): eski surum '-' ile baslayan token'lari komple eliyordu →
    BITISIK yazilmis deger ('-s/private/tmp/disari', '--start-directory=/tmp/x')
    hedef sayilmiyor, geriye repo-ici token kaliyor ve kapi ALLOW veriyordu; ayrik
    yazim ('-s /tmp/x') dogru sekilde deny idi. Artik bitisik deger de HEDEFTIR.

    🔴 20 Tem REGRESYON ONARIMI (R2): kisa bayrakta ham 't[2:]' aliniyordu →
    '-s=/private/tmp/disari' icin deger '=/private/tmp/disari' oluyor, basindaki '='
    yuzunden MUTLAK sayilmiyor, cwd'ye eklenip REPO-ICI kabul ediliyordu. Olculdu:
    repo disinda gercek icra kosturuldu. Artik kisa VE uzun bayrak degeri TEK
    ayristiricidan gecer ve bastaki '=' soyulur.

    Kural:
      '--bayrak=DEGER' -> DEGER hedef
      '-sDEGER'        -> DEGER hedef (kisa bayrak + bitisik deger, genel hal)
      '-s=DEGER'       -> DEGER hedef (bitisik + esitlikli form; '=' SOYULUR)
      '-s' / '--x'     -> degersiz bayrak, atlanir
      diger token      -> hedef (ayrik yazilmis deger de dahil; yol sayilmasi KATIDIR)"""
    hedefler = []
    for t in argumanlar:
        if t.startswith("--"):
            deger = t.split("=", 1)[1] if "=" in t else ""
        elif t.startswith("-"):
            deger = t[2:] if len(t) > 2 else ""
        else:
            hedefler.append(t)
            continue
        deger = _bayrak_degeri(deger)
        if deger:
            hedefler.append(deger)
    return hedefler


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

        # D) Bayraga GOMULU repo-disi betik yolu (node --require=/tmp/x.js repo.js gibi):
        #    ilk serbest arguman repo icinde olsa bile disaridan kod yuklenir.
        for t in argumanlar:
            aday = t.split("=", 1)[1] if (t.startswith("-") and "=" in t) else t
            if aday.lower().endswith(ICRA_UZANTILARI) and ("/" in aday or aday.startswith(".")):
                if not repo_ici(aday, cwd):
                    reddet(
                        "komutta repo DIŞINDAKİ bir betiğe yol var (" + aday + "). "
                        "Bayrağa gömülü olsa bile dışarıdan kod yüklenmesi kapalı."
                    )

        # E) Modul calistirma (python3 -m X): X dosya degil MODUL — repo kontrolu ise
        #    yaramaz. pip (kurulum betigi kosar), timeit/pdb/trace (-s ile kod alir),
        #    venv, http.server hepsi keyfi icra/disari acilma kapisi → varsayilan KAPALI.
        #    BITISIK form ('-mpip') de ayni denetimden gecer — bkz. modul_ayikla().
        modul, modul_sonrasi = modul_ayikla(argumanlar)
        if modul is not None:
            if modul in IZINLI_MODULLER:
                continue
            if modul in TEST_MODULLERI:
                # Test kosucusu: hedeflerin HEPSI repo-ici olmali. Hic yol argumani
                # yoksa cwd repo-ici olmali. Boylece mimar kendi kabul testini kosturur
                # ama -m ile repo DISINA cikamaz (vaka 85/86 allow, 87 deny).
                # BITISIK yazim da hedeftir (vaka 92/94 deny, 93/95 allow).
                hedefler = test_hedefleri(modul_sonrasi)
                if hedefler:
                    if all(repo_ici(h, cwd) for h in hedefler):
                        continue
                elif repo_ici(cwd, cwd):
                    continue
            reddet(
                "'" + ad + " -m " + (modul or "?") + "' modül üzerinden keyfi icra kapısıdır "
                "(pip kurulum betiği koşturur; timeit/pdb/trace -s ile kod alır; venv/"
                "http.server ortamı değiştirir/dışarı açar). İzinli modüller yalnız: " +
                ", ".join(sorted(IZINLI_MODULLER)) + "."
            )

        # F) Betik yolunu bul
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
