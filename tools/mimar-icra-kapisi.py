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
  3. [26 TEM'DE DEGISTI — asagidaki BaBa hukmune bak] codex artik KOSULSUZ redde DEGIL.
  4. python3/node — YALNIZ 'python3 tools/durum.py' ve 'python3 tools/d1-sync.py --durum'
     serbest (tam-yol ya da repo-goreli TAM esitlik; ekstra argüman = RED). Diger TUM
     tools/ araclari + node --check + -m + repo-ici betik = RED (test kosumu dahil).
  Bunun sonucu: eski '-m'/yol-ayristirma makinesi (modul_suphesi/betik_siniri) python
  tarafinda GEREKSIZ oldu ve KALDIRILDI — python GATE'i tek noktadadir (_py_izinli).
  dis_yol / F (betik repo_ici) / C (satir-ici) YALNIZ sh/bash/ruby/perl/php/osascript
  icin KALDI (onlarda -m yok). Sertligin bedeli YALNIZ mimara: ISCI (agent_id dolu)
  bu redlerin HICBIRINE takilmaz (main() basinda muaf; kanit: ISCI ikizleri).

🟢 26 TEM DOKTRIN DEGISIKLIGI (Senyor Advisor / BaBa hukmu — 22 Tem kural 3 GERI ALINDI):
  "'codex exec' cagirmak KENDI ELIYLE IS YAPMAK DEGIL, ISCI DAGITMAKTIR — Agent araciyla
  muhendis acmakla AYNI SINIF. Araya bir de Claude isci koymak (mimar->Claude->Codex)
  mekanik ise pahali katman bindirir, token rejimine aykiri." KraL evi bu hukme hizalandi;
  diger 5 evde codex zaten serbestti (tutarsizlik kapandi).
  KALAN TEK SART = KALITE KAPISI (kural degil, standart): cagri 'codex-isci' standardiyla
  yapilir, yani SONUC BIR DOSYAYA yazilir → '-o' / '--output-last-message'. Bu bayragi
  tasimayan 'codex exec' RED (raporsuz delege = kabul kapisi kurulmamis is).
  'codex --version' gibi ZARARSIZ GOZLEM cagrilari GECER.
  Ayristirma taklidi YOK: bayrak TAM TOKEN esitligiyle aranir, supheli form REDDEDILIR
  (memory/mimar-kapi-parser-taklidi.md — bu eksende ucuncu kez delik cikti).

🟢 27 TEM SIKILASTIRMA TURU (bagimsiz curutucunun olctugu 3 kusur + 4 on-var yanlis-pozitif):
  1. DARALTMA (en degerli hamle): kural artik segmentteki HERHANGI bir 'codex' token'ina
     degil, YALNIZ segmentin CALISTIRILAN PROGRAMINA (argv0 basename'i) bakar. Boylece
     'grep -rn codex ...', 'git commit -m codex', 'git log --grep codex',
     'ls .../Resources/codex' artik kurali HIC tetiklemez (4 yanlis-pozitif kapandi).
  2. ALT-KOMUT KAPISI (fail-closed): yalniz 'exec' delegasyondur. 'resume' etkilesimli
     TUI'yi surdurur = mimarin kendi eliyle isi; 'mcp'/'login'/BILINMEYEN → RED.
  3. BAYRAK DEGER SARTI: bayragin VARLIGI yetmiyordu ('codex exec -o' geciyordu) — artik
     bayraktan sonra bos-olmayan, '-' ile baslamayan bir token (ya da '=<yol>') sart.
  4. GOZLEM SIMETRISI: -v/-V/-h/--help/--version tek sinif (CODEX_GOZLEM_BAYRAKLARI =
     SURUM_BAYRAKLARI); eskiden '-V' geciyor '-v' gecmiyordu.
  Bu tur bir DARALTMA turudur: yakalama gucu OLCULDU, 15 bypass/kalkan fikstürünün hepsi
  DENY kaldi (memory/kapi-kapsam-genisletme-tuzagi.md).

🟢 27 TEM IKINCI TUR (BaBa doktrin hukmu: sart 6 EVE tasinir) — bagimsiz curutucunun
  ccb4482e sonrasi olctugu IKI kusur KAPATILDI (ikisi de "bayrak DEGERI" ekseninde):
  1. ESITLIKLI BICIMDE '-' ONEKI DENETIMI YOKTU: 'codex exec --output-last-message=-o "x"'
     ALLOW aliyordu — '=' sonrasi bos degil diye DEGERLI sayiliyor, oysa deger baska bir
     BAYRAK. Artik esitlikli bicimde de deger '-' ile basliyorsa DEGER SAYILMAZ (ayrik
     bicimdeki kural neydi ise o: 'codex exec -o -v "x"' zaten DENY idi, simdi iki bicim
     SIMETRIK — tek kaynak _codex_deger_gecerli()).
  2. SARMALAYICI BAYRAK-DEGERI SIZINTISI: 'nice -n 10 codex exec "x"' ALLOW aliyordu.
     sarmalayici_soy 'nice'i ve '-n'i soyuyor, ama '10' (bayragin DEGERI) argv0 sanildigi
     icin _codex_programi('10') False donuyor ve kural HIC calismiyordu. Ayni sizinti
     'env -u FOO codex ...', 'stdbuf -o 0 codex ...', 'time -o /tmp/t codex ...'.
     COZUM parser taklidi DEGIL, dis_yol'un zaten kullandigi IKI OKUMA idiomu
     (_sarmalayici_ikinci_okuma): ikinci okumada her atlanan bayragin ardindan bir token
     daha atlanabilir sayilir; iki okumadan BIRINDE argv0 'codex' ise kural o okumaya
     uygulanir (fail-closed). Hangi sarmalayicinin hangi bayragi deger alir TABLOSU
     TUTULMAZ ve YENI PROGRAM ADI EKLENMEZ (launcher/whitelist listesi YASAK — mimar
     hukmu; xargs/sudo/npx sinifi BILINEN BYPASS #1'de kayitli, kapatilmaz).
  KABUL EDILEN BEDEL (olculdu, tek sinif): 'wrapper + bayrak + PROGRAM + basename'i
  codex olan bir ARGUMAN' bicimi (or. 'time -p ls /Applications/.../codex') ikinci
  okumada yanlis-pozitif DENY alir. Sarmalayici + bayrak + tam o konum sarti gerektigi
  icin gercekte gorulmez; sarmalayicisiz hicbir cagri etkilenmez (nobetci: vaka 282).

SERBEST (mimar eliyle — yanlislikla kapatma, kapatirsan is durur):
  * codex: 'codex exec ... -o <dosya> "<spec>"' (ALT-KOMUT yalniz 'exec'; bayrak bir
    DEGERLE gelmeli) + gozlem: 'codex --version / -V / -v / --help / -h'
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
     🔸 27 TEM OLCUMU: codex bu sinifa DAHIL OLDU. Daraltmadan ONCE 'xargs codex exec',
     'sudo codex exec', 'npx codex exec', 'watch codex exec', 'make codex',
     'echo x | xargs codex exec' DENY aliyordu — ama bunu saglayan sey kasitli bir nobetci
     degil, 4 yanlis-pozitifi de ureten AYNI kaba token taramasiydi. Daraltma sonrasi 6'si
     da ALLOW. Ayni kok neden, ayni gerekce: launcher listesi tutulmaz.
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

# === 26 TEM (BaBa hukmu): codex KOSULSUZ RED -> KALITE KAPISI ===
# Codex'e is DEVRETMEK mimarin isidir; devretmenin KABUL KAPISI sonucun bir DOSYAYA
# yazilmasidir (skill: codex-isci). Bayrak TAM TOKEN esitligiyle aranir — bitisik kisa
# form ('-o/tmp/x.txt') BILEREK kabul edilmez: clap/argparse ayristirmasini taklit etmek
# bu repoda uc onarim turu boyunca delik uretti; supheli form = RED (fail-closed).
CODEX_CIKTI_BAYRAKLARI = {"-o", "--output-last-message"}
CODEX_CIKTI_ONEKI = "--output-last-message="
# Zararsiz GOZLEM cagrilari (icra degil): yalnizca KALAN TUM tokenlar bunlardansa gecer.
# 27 TEM: ayri liste tutmak asimetri uretmisti ('-V' geciyor, '-v' gecmiyordu) —
# SURUM_BAYRAKLARI ile AYNI SINIF, tek kaynak; iki liste artik ayrisamaz.
CODEX_GOZLEM_BAYRAKLARI = SURUM_BAYRAKLARI
# 27 TEM ALT-KOMUT KAPISI (FAIL-CLOSED): doktrin "codex EXEC" der. 'resume' etkilesimli
# TUI'yi surdurur = mimarin KENDI ELIYLE is yapmasi (delegasyon DEGIL); 'mcp'/'login' de
# delege degil. Beyaz liste TEK elemanli ve KAPALI: gelecekte cikacak her yeni alt-komut
# VARSAYILAN RED alir (bilinmeyeni gecirmek = kapiyi zamanla bosaltmak).
CODEX_IZINLI_ALTKOMUT = "exec"
# 27 TEM (2. tur) SURUM DAMGASI — tools/mimar-kapi-kur.py --codex-kurali bu dizeyi
# arayarak "bu evde SIKILASTIRILMIS codex kurali var mi" sorusunu MAKINE olarak yanitlar
# (idempotans + 6 ev dogrulamasi). Kurali degistirirsen damgayi da yukselt.
CODEX_KURAL_SURUMU = "27tem-2"

# ===================== 28 TEM: AGENT-KAPISI (BaBa/Senyor Advisor hukmu) =====================
# ASIMETRI TESHISI: mimar bir Claude iscisi (Agent/Task araci) acmak SIFIR surtunmeliyken,
# dogrudan 'codex exec' cagrisi cikti-dosyasi sarti (_codex_karari) tasimak ZORUNDA. Sonuc:
# MAKINE pahali yolu (Claude isci) tesvik edip ucuz yolu (Codex) cezalandiriyor. Bu kapi
# asimetriyi kapatir: mimar ANA oturumu (agent_id BOS) bir Claude iscisi acarken verdigi
# prompt/spec icinde su BEYAN SATIRI YOKSA cagri REDDEDILIR:
#     codex-muafiyet: <is tanimi> — <sinif>
# <sinif> = isin neden Codex'e VERILEMEDIGINI beyan eden yasak-sinif (codex-isci yasak
# listesi). Boylece Claude iscisi acmaya da Codex kadar TEK SATIR surtunme konur.
#
# MUAFIYETLER (kapi bunlara DOKUNMAZ):
#   1. agent_id DOLU (ISCI) her cagri TAM muaf — main() basinda zaten cikilir; kural
#      yalniz mimar ANA oturumuna (agent_id bos).
#   2. Agent/Task DISINDAKI hicbir arac etkilenmez (tool_name kapisi; Bash/Write/... eskisi gibi).
#   3. Mevcut '-o' codex kurali + tum kilit/icra kurallari AYNEN korunur (regresyon 0).
AGENT_ARACLARI = {"Agent", "Task"}
# Yasak-sinif token'lari (codex-isci yasak listesi). Bunlardan BIRI ayractan HEMEN sonra gelmeli.
AGENT_SINIFLARI = (
    "görsel", "gorsel",
    "sessiz-hata",
    "muhakeme",
    "ölçüm", "olcum",
    "güvenlik", "guvenlik",
    "şema", "sema",
)
# TEK makine-aranabilir regex (parser taklidi YOK — tek kaba tarama, fail-closed):
#   'codex-muafiyet:'  (etikette buyuk/kucuk DUYARSIZ — re.IGNORECASE)
#   + [^\S\n]*         (bosluk/tab esnek; NEWLINE degil -> kural TEK SATIRDA)
#   + \S               (is tanimi BOS OLAMAZ: en az bir bosluk-disi karakter)
#   + [^\n]*?          (is metninin kalani, LAZY, tek satir — '.' DOTALL degil)
#   + [—–-]            (ayrac: em-tire '—' / en-tire '–' / tire '-'; ucune tolerans)
#   + [^\S\n]*         (ayrac ile sinif arasi yalniz bosluk)
#   + (SINIF)          (yasak-sinif token'i ayractan HEMEN sonra)
# re.IGNORECASE: hem etiket hem sinif buyuk/kucuk duyarsiz. DOTALL YOK -> beyan tek satir.
AGENT_MUAFIYET_RE = re.compile(
    r"codex-muafiyet:[^\S\n]*\S[^\n]*?[—–-][^\S\n]*(?:" +
    "|".join(re.escape(s) for s in AGENT_SINIFLARI) + r")(?![\w-])",
    re.IGNORECASE,
)
# SURUM DAMGASI — tools/mimar-kapi-kur.py --agent-kapisi bu dizeyi arayarak "bu evde
# AGENT-KAPISI kurali var mi" sorusunu MAKINE olarak yanitlar (idempotans + 6 ev). Kurali
# degistirirsen damgayi da yukselt.
AGENT_KURAL_SURUMU = "13agu-1"
# Codex reddindeki gibi: AGENT reddinde GEREKCE_SONU KULLANILMAZ ("bu isi isciye delege et"
# der — oysa AGENT cagrisi ZATEN isci acma girisimi). Yerine IKI CIKISI net soyleyen kuyruk.
AGENT_SINIF_LISTESI = " / ".join(AGENT_SINIFLARI)
AGENT_ORNEK_SINIF = AGENT_SINIFLARI[0]
AGENT_GEREKCE = (
    "AGENT-KAPISI (28 Tem): mimar ANA oturumu bir Claude iscisi (Agent/Task) açıyor ama "
    "prompt/spec içinde 'codex-muafiyet:' BEYAN SATIRI YOK. Doktrin: Claude işçisi açmak da "
    "doğrudan 'codex exec' kadar TEK SATIR sürtünme taşır (asimetri kapatıldı). İKİ ÇIKIŞ: "
    "(a) İŞİ CODEX'E VER → codex-isci şablonu (codex exec -C <ev> -s workspace-write "
    "-o <scratchpad>/son-mesaj.txt \"<spec>\"); VEYA (b) prompt'a şu satırı EKLE: "
    "'codex-muafiyet: <iş tanımı> — {ornek}' (geçerli sınıf jetonları: {liste} — "
    "codex-isci yasak listesi)."
).format(ornek=AGENT_ORNEK_SINIF, liste=AGENT_SINIF_LISTESI)


def _agent_gorulen_sinif(prompt):
    """Beyan satirindaki ayraç-sonrasi ilk jetonu yalniz red tanisi icin ayiklar."""
    etiket = "codex-muafiyet:"
    for satir in prompt.splitlines():
        konum = satir.lower().find(etiket)
        if konum < 0:
            continue
        kalan = satir[konum + len(etiket):]
        ayrac = max(kalan.rfind("—"), kalan.rfind("–"), kalan.rfind("-"))
        if ayrac < 0:
            return "<ayrac-yok>"
        parcalar = kalan[ayrac + 1:].strip().split()
        return parcalar[0] if parcalar else "<bos>"
    return "<bulunamadi>"

# ============ 8 AGU: MCP-TARAYICI ICRA KAPISI (Okan teftisi K17, 2. ihtar) ============
# OLCULEN DELIK: 6 evin settings.json PreToolUse matcher'lari yalnizca 'Bash',
# 'Edit|Write|MultiEdit' ve 'Agent|Task' tutuyordu. Uc MCP tarayici sunucusunun ARAC
# ADLARI hicbir matcher'a ugramiyordu → mimar ANA oturumunda tarayici surmek SIFIR
# surtunmeliydi. Olculmus vaka: bir mimar 1 saatte baglaminin %58'ini ana dongude
# tarayici surerek yakti; her tur bir EKRAN GORUNTUSU tasir ve goruntu en pahali
# token sinifidir.
#
# KURAL: mimar ANA oturumunda (agent_id BOS) bu uc onekle baslayan HER arac REDDEDILIR;
# ISCI'de (agent_id DOLU) SERBEST.
#
# 🔴 KIMLIK TESPITI YENIDEN KULLANILIR, IKINCI MEKANIZMA YAZILMAZ: main() basindaki
# kimlik(girdi) == "ISCI" erken cikisi AGENT-KAPISI'nin da dayandigi TEK mekanizmadir;
# bu kural o cikisin ARDINDA durur, yani ayri bir 'isci mi' testi TASIMAZ. Ikiz tanim
# sessizce ayrisir (memory/ikiz-tanim-sessiz-ayrisma.md) — tek kaynak korunur.
#
# KAPSAM DAR TUTULUR (yanlis-pozitif = bu depoda YAYIN DURDURAN sinif; memory/
# kapi-kapsam-genisletme-tuzagi.md + tekil-yama-sinifi-kapatmaz.md): kural "mcp__ ile
# baslayan her sey" DEGIL, YALNIZ bu uc SUNUCU onekidir. mcp__visualize__*,
# mcp__Blender__*, mcp__ccd_session__*, mcp__scheduled-tasks__* vb. DOKUNULMAZ. Tek
# yonlu nobetci (yalniz "yakaliyor mu") olu nobetcidir; iki yon de olculur.
#
# PARSER TAKLIDI YOK (memory/mimar-kapi-parser-taklidi.md): tek soru "arac adi bu uc
# onekten biriyle BASLIYOR mu". Glob/joker genisletmesi, sunucu adi normalizasyonu,
# arac adi ayristirmasi YAPILMAZ. Karsilastirma buyuk/kucuk harf DUYARSIZDIR ve bu
# TEK KAYNAKTAN (asagidaki dongu) gelir — ayni sunucu adinin iki yazimi icin iki liste
# tutmak tam da ayrisan ikiz tanim olurdu.
MCP_TARAYICI_ONEKLERI = (
    "mcp__claude-in-chrome__",
    "mcp__Claude_Browser__",
    "mcp__Control_Chrome__",
)
# SURUM DAMGASI — tools/mimar-kapi-kur.py --mcp-kapisi bu dizeyi arayarak "bu evde
# MCP-TARAYICI kurali var mi" sorusunu MAKINE olarak yanitlar (idempotans + 6 ev
# dogrulamasi). Kurali degistirirsen damgayi da yukselt.
MCP_KURAL_SURUMU = "8agu-1"
MCP_GEREKCE = (
    "MCP-TARAYICI KAPISI (8 Ağu): mimar ANA oturumu bir tarayıcı aracı çağırıyor. Ana "
    "döngüde tarayıcı sürmek KAPALI — her tur ekran görüntüsü taşır ve görüntü EN PAHALI "
    "token sınıfıdır (ölçülen vaka: 1 saatte bağlamın %58'i). ÇÖZÜM: TARAYICIYI "
    "GÖRSEL-SINIF CLAUDE İŞÇİSİNE VER — Codex'e VERİLMEZ (görsel = codex-isci yasak "
    "listesi). İŞÇİ ŞABLONU (Agent aracı: model sonnet + isolation worktree + background), "
    "prompt'un ilk satırı: 'codex-muafiyet: tarayıcı ile <ne ölçülecek> — görsel'; spec'e "
    "ÇALIŞTIRILABİLİR kabul yaz (hangi URL'de hangi sayı ölçülecek), işçi ölçsün, sen "
    "SAYIYLA kapat. İşçi çağrılarında (agent_id dolu) bu kapı hiçbir kural uygulamaz — "
    "tarayıcı orada SERBESTTİR."
)


def _mcp_tarayici_mi(tool_name):
    """Arac adi KAPSAMDAKI uc tarayici sunucusundan birine mi ait?

    KABA + TEK SORU: ad, MCP_TARAYICI_ONEKLERI'nden biriyle BASLIYOR mu (buyuk/kucuk
    DUYARSIZ). Onek DISI hicbir 'mcp__...' araci etkilenmez — kapsam disi benzer adli
    araclar (mcp__visualize__*, mcp__Blender__*, mcp__ccd_session__*) ana oturumda
    REDDEDILMEZ; bu YANLIS-POZITIF ekseni ayri vakalarla olculur."""
    if not isinstance(tool_name, str) or not tool_name:
        return False
    ad = tool_name.lower()
    for onek in MCP_TARAYICI_ONEKLERI:
        if ad.startswith(onek.lower()):
            return True
    return False


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


# Codex reddinde GEREKCE_SONU KULLANILMAZ: o metin "bu isi isciye delege et" der, oysa
# codex cagrisi ZATEN delegedir (26 Tem hukmu) — yanlis yol tarif ederdi. Yerine eksik
# olan TEK seyi soyleyen kisa kuyruk.
CODEX_GEREKCE_SONU = (
    " DOGRUSU: codex exec -C /Users/okan/dev/pruvo -s workspace-write "
    "-o /<scratchpad>/son-mesaj.txt \"<spec>\" — sonra dosyayi oku, sayiyla kapat. "
    "(skill: codex-isci)"
)


def reddet(neden, sonu=None):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": GEREKCE_BASI + neden +
                                        (GEREKCE_SONU if sonu is None else sonu),
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


def _codex_programi(argv0):
    """27 TEM DARALTMASI — segmentin CALISTIRILAN programi codex mi?

    ESKI HALI (_codex_var) segmentteki HERHANGI bir token'da 'codex' basename'ini ya da
    'ChatGPT.app' alt-dizesini ariyordu. OLCULEN BEDEL — dort ON-VAR YANLIS-POZITIF:
    'grep -rn codex tools/', 'git commit -m codex', 'git log --grep codex',
    'ls /Applications/ChatGPT.app/Contents/Resources/codex' → dordu de DENY aliyordu,
    oysa calistirilan program grep/git/ls, codex DEGIL. Kural artik YALNIZ argv0'a bakar
    (tam yol ise SON BILESENI). 'ChatGPT.app' alt-dize testi de GEREKSIZ kaldi: o yolun
    basename'i zaten 'codex'.

    KABUL EDILEN BEDEL (olculdu, 6 komut): launcher-arkasi codex ('xargs codex exec',
    'sudo codex exec', 'npx codex exec' ...) eskiden — KURALIN GENISLIGI YUZUNDEN, tasarim
    geregi degil — DENY aliyordu, artik ALLOW. Bu, bas yorumdaki BILINEN BYPASS #1'in
    (launcher-arkasi cagri) tam olarak ayni kokudur ve orada "kapatilmaz" diye kayitlidir:
    launcher saymak sonsuz liste + yeni yanlis-pozitif acar. Yani kaybedilen sey KASITLI
    bir nobetci degil, ayni kaba taramanin yan urunuydu."""
    return os.path.basename(argv0) == "codex"


def _codex_deger_gecerli(deger):
    """27 TEM (2. tur) — cikti bayraginin DEGERI gecerli mi? IKI BICIMIN TEK KAYNAGI.

    Kural (kaba, iki soru): (a) bos olmasin, (b) '-' ile BASLAMASIN — '-' ile baslayan
    sey bir DEGER degil BASKA BIR BAYRAKtir, yani kabul kapisi bos kalir.

    NEDEN TEK FONKSIYON: bu repoda ayni eksende IKI KEZ ASIMETRI olctuk — once gozlem
    bayraklari ('-V' geciyor, '-v' gecmiyordu; ccb4482e'de SURUM_BAYRAKLARI'na
    birlestirildi), sonra cikti bayragi bicimleri (ayrik bicimde '-' denetimi VAR,
    esitlikli bicimde YOKTU → 'codex exec --output-last-message=-o "x"' ALLOW).
    Iki liste/iki gövde tutmak bu asimetriyi tekrar uretir; tek kaynak uretemez."""
    if not deger:
        return False
    if deger.startswith("-"):
        return False
    return True


def _codex_cikti_degerli(tokenlar):
    """27 TEM — cikti bayragi bir DOSYA DEGERIYLE mi geliyor? (eskiden VARLIGI yetiyordu)

    Olculen kusur: 'codex exec -o' (degersiz, son token) ve 'codex exec -o -s
    workspace-write' (degeri baska bir BAYRAK) GECIYORDU — yani kabul kapisi tek bir
    bos bayrakla bosa cikarilabiliyordu.

    KABA KURAL, PARSER TAKLIDI YOK (memory/mimar-kapi-parser-taklidi.md):
      * ayrik bicim ('-o X'): bayragin HEMEN ARDINDAN bos-olmayan ve '-' ile BASLAMAYAN
        bir token gelmeli.
      * esitlikli bicim ('--output-last-message=X'): '=' sonrasi AYNI SART (27 Tem 2. tur:
        eskiden yalniz "bos degil" bakiliyordu → '--output-last-message=-o' ALLOW aliyordu).
    Clap'in "hangi bayrak deger alir" tablosu taklit EDILMEZ, yol dogrulanmaz, dosya
    varligi sorulmaz — tek soru: "bayraktan sonra bir sey var mi".

    ILK ESLESME KARARI VERIR (kendi curutmemde olculdu): "bozuksa ARAMAYA DEVAM ET"
    demek 'codex exec --output-last-message -o /tmp/a.txt' gibi bir diziyi ACIYORDU —
    ilk bayragin degeri '-o' oluyor, ikinci okuma yesil yaniyordu. Supheli form = RED
    kuralinin geregi: ilk cikti bayragi DUZGUN degilse tum cagri REDDEDILIR."""
    for i, t in enumerate(tokenlar):
        if t in CODEX_CIKTI_BAYRAKLARI:
            if i + 1 >= len(tokenlar):
                return False
            return _codex_deger_gecerli(tokenlar[i + 1])
        if t.startswith(CODEX_CIKTI_ONEKI):
            return _codex_deger_gecerli(t[len(CODEX_CIKTI_ONEKI):])
    return False


def _sarmalayici_ikinci_okuma(tokenlar):
    """27 TEM (2. tur) — SARMALAYICI bayrak-DEGERI sizintisinin IKINCI OKUMASI.

    OLCULEN KUSUR: 'nice -n 10 codex exec "x"' ALLOW aliyordu. sarmalayici_soy 'nice'i
    soyar, ardindan bayraklari ('-n') atlar, ama '10' — yani bayragin DEGERI — komut
    adayi sanilir; argv0 '10' oldugu icin _codex_programi False doner ve codex kurali
    HIC calismaz. Ayni sizinti: 'env -u FOO codex ...', 'stdbuf -o 0 codex ...',
    'time -o /tmp/t codex ...'.

    IKI OKUMA IDIOMU (dis_yol'da zaten kullanilan desen; parser taklidi YASAK):
    "hangi sarmalayicinin hangi bayragi deger alir" TABLOSU tutulmaz. Bunun yerine
    belirsizlik IKI OKUMAYA bolunur — bu okumada her atlanan bayragin ARDINDAN gelen
    tiresiz token de o bayragin DEGERI olabilir sayilip atlanir. Cagiran (
    _codex_segment_karari) iki okumadan BIRINDE argv0 'codex' gorurse kurali o okumaya
    uygular: belirsizlik ICERI degil DISARI sayilir (fail-closed).

    LAUNCHER/WHITELIST LISTESI DEGIL (mimar hukmu): bu fonksiyon programlar kumesine
    TEK BIR AD EKLEMEZ; yalnizca ZATEN var olan SARMALAYICI kumesinin ayristirmasindaki
    belirsizligi cozer. xargs/sudo/npx/make/watch sinifi BILINEN BYPASS #1'de kayitlidir
    ve KAPATILMAZ.

    KABUL EDILEN BEDEL: 'sarmalayici + bayrak + PROGRAM + basename'i codex olan ARGUMAN'
    (or. 'time -p ls /Applications/.../codex') bu okumada yanlis-pozitif DENY alir.
    Sarmalayicisiz hicbir cagri etkilenmez (nobetci: vaka 282)."""
    okuma = list(tokenlar)
    while okuma:
        if re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", okuma[0]):
            okuma = okuma[1:]
            continue
        if os.path.basename(okuma[0]) in SARMALAYICI:
            okuma = okuma[1:]
            while okuma and okuma[0].startswith("-"):
                okuma = okuma[1:]
                # BAYRAK DEGERI: bayraktan sonraki tiresiz token o bayraga AIT OLABILIR
                # → bu okumada atlanir (ilk okuma onu argv0 sayar; iki okuma da sinanir).
                if okuma and not okuma[0].startswith("-"):
                    okuma = okuma[1:]
            continue
        break
    return okuma


def _codex_karari(tokenlar):
    """26 TEM (BaBa hukmu) + 27 TEM SIKILASTIRMA — codex cagrisinin KARARI. Doner:
        None      → segmentin CALISTIRILAN programi codex degil (kural uygulanmaz)
        "gecer"   → izinli (delege = mimarlik) — cagiran YINE DE devam eder, yani
                    diger kurallar bu segmentte KAPANMAZ (bkz. main(): 'continue' YOK)
        str       → red gerekcesi

    KABA + FAIL-CLOSED (parser taklidi YASAK). Sira:
      0. argv0 codex degilse KURAL HIC CALISMAZ (_codex_programi — 27 Tem daraltmasi).
      1. Ciplak 'codex' (argumansiz, etkilesimli TUI) = RED (kabul kapisi kurulamaz).
      2. GOZLEM: kalan TUM tokenlar gozlem bayragiysa gecer (-v/-V/-h/--help/--version).
      3. ALT-KOMUT: kalan[0] 'exec' DEGILSE RED (resume/mcp/login/bilinmeyen = varsayilan
         RED). Fail-closed: yeni alt-komut ciktiginda kapi kendiliginden ACILMAZ.
      4. CIKTI BAYRAGI + DEGER: '-o <yol>' / '--output-last-message <yol>' /
         '--output-last-message=<yol>'. Bitisik kisa form ('-o/tmp/x') KABUL EDILMEZ."""
    if not tokenlar or not _codex_programi(tokenlar[0]):
        return None
    kalan = tokenlar[1:]
    if not kalan:
        return (
            "çıplak 'codex' çağrısı (argümansız = etkileşimli TUI): kabul kapısı "
            "kurulamaz. Delege 'codex exec ... -o <dosya>' iledir."
        )
    if all(t in CODEX_GOZLEM_BAYRAKLARI for t in kalan):
        return "gecer"
    if kalan[0] != CODEX_IZINLI_ALTKOMUT:
        return (
            "codex alt-komutu 'exec' DEĞİL (" + kalan[0][:24] + "). Doktrin 'codex EXEC' "
            "der: 'resume' etkileşimli oturumu sürdürür — bu DELEGASYON değil, mimarın "
            "KENDİ ELİYLE iş yapmasıdır; 'mcp'/'login' vb. de delege değildir. Bilinmeyen "
            "alt-komut VARSAYILAN RED (fail-closed)."
        )
    if not _codex_cikti_degerli(kalan[1:]):
        return (
            "Codex çağrısı 'codex-isci' STANDARDINA uymuyor: sonucu dosyaya yazan bayrak "
            "bir DEĞERLE gelmiyor ('-o <dosya>' ya da '--output-last-message <dosya>', "
            "boşlukla ayrılmış ve ardından bir YOL; '--output-last-message=<yol>' de "
            "geçerli). Codex'e iş DEVRETMEK serbest (26 Tem: işçi dağıtmak mimarlıktır), "
            "raporsuz delege değil — kabul kapısı kurulmadan çağırma."
        )
    return "gecer"


def _codex_segment_karari(segment, tokenlar):
    """27 TEM (2. tur) — segmentin codex KARARI, IKI OKUMA ile (bkz.
    _sarmalayici_ikinci_okuma). Doner: _codex_karari ile ayni uc deger.

    Sira: (1) normal okuma (sarmalayici_soy sonucu) — daraltilmis argv0 kurali;
    (2) yalnizca (1) 'kural uygulanmaz' derse IKINCI OKUMA denenir. Boylece POZITIF
    kararlar (ozellikle 'gecer') degismez, yalnizca sizinti kapanir."""
    karar = _codex_karari(tokenlar)
    if karar is None:
        ikinci = _sarmalayici_ikinci_okuma(parcala(segment))
        if ikinci != tokenlar:
            karar = _codex_karari(ikinci)
    return karar


def _agent_karari(girdi):
    """28 TEM — AGENT-KAPISI karari (mimar ANA oturumu bir Claude iscisi acarken). Doner:
        "gecer" → prompt'ta gecerli 'codex-muafiyet: <is> — <sinif>' beyan satiri VAR
        str     → red gerekcesi (beyan satiri yok / gecersiz sinif)

    ISCI muafiyeti main() basinda (kimlik==ISCI) verilir; bu fonksiyon yalniz MIMAR icin
    cagrilir. tool_input.prompt taranir (Agent/Task araclarinin spec alani). Prompt yoksa
    ya da str degilse BOS sayilir → beyan yok → RED (fail-closed: eksik/bozuk girdi acmaz).
    KABA + TEK REGEX (parser taklidi yok): AGENT_MUAFIYET_RE tek makine-aranabilir desendir."""
    ti = girdi.get("tool_input") or {}
    prompt = ti.get("prompt")
    if not isinstance(prompt, str):
        prompt = ""
    if AGENT_MUAFIYET_RE.search(prompt):
        return "gecer"
    if "codex-muafiyet:" not in prompt.lower():
        return AGENT_GEREKCE
    return (
        "AGENT-KAPISI (28 Tem): BEYAN VAR, SINIF JETONU ESLESMEDI: gorulen "
        "'{gorulen}' · gecerli jetonlar: {liste}"
    ).format(gorulen=_agent_gorulen_sinif(prompt), liste=AGENT_SINIF_LISTESI)


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

    # === 28 TEM AGENT-KAPISI: mimar ANA oturumu Claude iscisi (Agent/Task) acarken
    # 'codex-muafiyet: <is> — <sinif>' beyan sarti. ISCI (agent_id dolu) YUKARIDA zaten
    # muaf cikti; Agent/Task DISINDAKI hicbir arac bu koldan gecmez (tool_name kapisi) —
    # Bash/Write/... asagidaki mevcut mantikla eskisi gibi islenir (regresyon 0).
    tool_name = girdi.get("tool_name") or ""
    if tool_name in AGENT_ARACLARI:
        agent_karari = _agent_karari(girdi)
        if agent_karari != "gecer":
            reddet(agent_karari, sonu="")
        iz_bas("MIMAR-agent-muafiyet")
        sys.exit(0)

    # === 8 AGU MCP-TARAYICI KAPISI: mimar ANA oturumunda tarayici icrasi KAPALI.
    # ISCI (agent_id dolu) YUKARIDA zaten muaf cikti — bu satirin kimlik testi TASIMAMASI
    # kasitlidir: tespit TEK KAYNAKTAN (main() basi) gelir, ikinci mekanizma yazilmaz.
    # Kapsam DISI hicbir arac bu koldan gecmez (_mcp_tarayici_mi onek kumesi); Bash/Agent/
    # Write kollarinin davranisi DEGISMEZ (regresyon 0).
    if _mcp_tarayici_mi(tool_name):
        reddet(MCP_GEREKCE, sonu="")

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
        # 26 TEM: kosulsuz codex reddi KALKTI; yerine kalite kapisi (cikti dosyasi sarti).
        # DIKKAT — 'gecer' halinde CONTINUE YOK: segmentin kalan denetimleri (repo-disi
        # betik, satir-ici kod, yol taramasi) calismaya devam eder. Aksi halde token
        # dizisine 'codex' + '-o' serpistirmek TUM kapiyi atlatan bir anahtar olurdu.
        # 27 TEM (2. tur): karar IKI OKUMA ile alinir — 'nice -n 10 codex exec' gibi
        # sarmalayici bayrak-degeri sizintisi kapanir (_codex_segment_karari).
        codex_karari = _codex_segment_karari(segment, tokenlar)
        if codex_karari is not None and codex_karari != "gecer":
            reddet(codex_karari, sonu=CODEX_GEREKCE_SONU)

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
