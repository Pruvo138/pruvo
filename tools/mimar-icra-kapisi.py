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
import datetime
import json
import os
import re
import shlex
import sys

from mimar_kimlik import (
    CANLI_ISCI_MOTORLARI,
    CODEX_IZINLI_MODELLER,
    CODEX_PENCERE_BITIS,
    CODEX_YASAK_MODELLER,
    EMEKLI_ISCI_MOTORLARI,
    ISCI_MOTORLARI,
    emekli_gerekcesi,
    emekli_motor_mu,
    kimlik_ekseni,
    rol_ekseni,
)

REPO_ONEKI = "/Users/okan/dev/pruvo/"
GIT_WORKTREE_KAYIT = "/Users/okan/dev/pruvo/.git/worktrees"

# 13 AGU Okan emri: KraL + MaCiT evlerinde Claude iscisi bir secenek degil, makine
# kuralidir. Ev karari bu TEK kapali kumeden ve evin kendi REPO_ONEKI sabitinden cikar;
# ikinci ev listesi tutulmaz.
SERT_BLOK_EVLER = ("pruvo", "pruvo-hasat")
EV_ADI = os.path.basename(os.path.normpath(REPO_ONEKI))


def kimlik(girdi):
    return "ISCI" if kimlik_ekseni(girdi) is not None else "MIMAR"


def kimlik_izi(girdi):
    eksen = kimlik_ekseni(girdi)
    return "ISCI(" + eksen + ")" if eksen is not None else "MIMAR"


def rol(girdi):
    """27 AGU (K318) — OTURUM ROLU. Doner: cip'in worktree koku ya da None (=ANA/olculemedi).

    Govde YOK: tek kaynak mimar_kimlik.rol_ekseni'dir; burada yalnizca kayit kumesi
    beslenir. Kapinin kendi 'cip mi' testi TASIMAMASI kasitlidir — ikinci mekanizma
    sessizce ayrisir ([[ikiz-tanim-sessiz-ayrisma]])."""
    return rol_ekseni(girdi, kayitli_worktree_kokleri())


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
# === 18 AGU K168 H1: defter-rotasyon.py serbest birakildi (K168 paketi). ===
# K168 sinif kararidir: "mimar DEVAM.md kota tavanini astiginda cabalayan CARE basar,
#  ama cabalayan CAGIRAMIYOR" bilinen kusuruna karsi bu komut — Python'un argparse
# izniyle — TAM ESITLIKLE serbest. Kapsam bilerek DAR: iki konumsal arg, DEVAM.md ve
#  DEVAM-ARSIV.md (kanonik yollar), bayrak YOK, kabuk operatoru YOK. Daha genis
#  erisim (or. --tavan-sayi, --tarih) mimar hukmu KAPALI tutar (K168 §2.H1).
# Yetki genisletme: tools/recete-kapisi.py bu komutu kapida kuru kontrol eder.
DEFTER_ROTASYON_YOL = REPO_ONEKI + "tools/defter-rotasyon.py"
DEFTER_ROTASYON_DEFTER = REPO_ONEKI + "DEVAM.md"
DEFTER_ROTASYON_ARSIV = REPO_ONEKI + "DEVAM-ARSIV.md"
KUTU_ARSIVLE_YOL = REPO_ONEKI + "tools/kutu-arsivle.py"

# === 20 AGU 2026 (K258) — "DEFTER BAKIMI" KOVASI ===========================
# OLCULEN ARIZA: kota kapilarinin BASTIGI carenin kendisi mimarin komut
# kumesinde YASAKTI. `defter-kota-kapisi.py` "CARE: ... defter-rotasyon.py ...
# --tavan-kaynaktan --isaretciye-indir" basiyordu ama K168 H1 kolu HER bayragi
# kesiyordu; `kutu-arsivle.py` kapida HIC gecmiyordu (genel `return False`).
# Sonuc: kapi cozumu soyluyor, kapi cozumu reddediyor — defter/kutu yedi-sekiz
# tur ELLE kirpildi.
#
# 🔴 KOVA ADLIDIR VE TURETILMISTIR, KAPI TOPTAN GEVSETILMEDI:
#   * yalniz IKI arac (defter bakimi araci) girer,
#   * her aracin izinli bayrak kumesi TAM ESITLIKLE tanimlidir,
#   * kumenin DISINDAKI her bayrak RED (serbest-bicim bayrak YOK),
#   * konumsal argumanlar kanonik yola TAM ESITLIKLE dogrulanir.
# Kapinin olcum/icra yasaginin GERI KALANI (curl / sort / tail / head / find /
# wc ve genel python) GEVSETILMEZ — bu kova onlara DOKUNMAZ.
DEFTER_BAKIMI_BAYRAKLARI = {
    DEFTER_ROTASYON_YOL: frozenset(("--tavan-kaynaktan", "--isaretciye-indir")),
    KUTU_ARSIVLE_YOL: frozenset(("--kuru",)),
}
# Aracin bekledigi KANONIK konumsal argumanlar (bos tuple = konumsal arg YOK).
DEFTER_BAKIMI_KONUMLARI = {
    DEFTER_ROTASYON_YOL: (DEFTER_ROTASYON_DEFTER, DEFTER_ROTASYON_ARSIV),
    KUTU_ARSIVLE_YOL: (),
}


def _bakim_bayraklari_izinli(arac_yolu, kalan_argumanlar):
    """DEFTER BAKIMI kovasi: bayrak kumesi TAM ESITLIK ile dogrulanir.

    True yalnizca su durumda: her bayrak aracin izinli kumesinde VE hicbiri
    tekrarlanmamis. Deger alan bayrak (`--tavan-sayi 130`) izinli kumede
    OLMADIGI icin zaten RED; `=`li yazim (`--tavan-sayi=130`) da kumeye TAM
    ESIT olmadigindan RED. Bilinmeyen arac -> RED (fail-closed).
    """
    izinli = DEFTER_BAKIMI_BAYRAKLARI.get(arac_yolu)
    if izinli is None:
        return False
    bayraklar = [a for a in kalan_argumanlar if a.startswith("-")]
    if len(bayraklar) != len(set(bayraklar)):
        return False
    return all(b in izinli for b in bayraklar)


def _bakim_konumlari_izinli(arac_yolu, kalan_argumanlar, cwd):
    """DEFTER BAKIMI kovasi: konumsal argumanlar kanonik yola TAM ESIT mi?"""
    beklenen = DEFTER_BAKIMI_KONUMLARI.get(arac_yolu)
    if beklenen is None:
        return False
    konumlar = [a for a in kalan_argumanlar if not a.startswith("-")]
    if len(konumlar) != len(beklenen):
        return False
    return all(_coz(v, cwd) == b for v, b in zip(konumlar, beklenen))

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
# 17 AGU K159: 4 yeni kural eklendi (pencere bitisi + model bayragi zorunlu + amiral
# yasak + bilinmeyen fail-closed) -> damga yukseldi.
CODEX_KURAL_SURUMU = "17agu-1"

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
AGENT_KURAL_SURUMU = "13agu-2"
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


def _sert_blok_gerekcesi():
    """KraL/MaCiT sert reddi; acik yollar kanonik sabitlerden turetilir."""
    return (
        "AGENT-KAPISI (13 Ağu Okan emri): bu evde mimar ANA oturumunun Claude işçisi "
        "(Agent/Task ve isci.sh claude) açması, 'codex-muafiyet:' beyanı bulunsa bile "
        "YASAKTIR. 'claude' motoru da aynı yasağın kapsamındadır; pahalı kat pahalı kattır. "
        "PRUVO_CLAUDE_ISCI_IZNI yalnızca tam olarak OKAN ise eski beyan kuralı çalışır; "
        "bu izni yalnızca Okan verir ve ajan kendi ayarlayamaz. İKİ AÇIK YOL: (a) " +
        ISCI_SARMALAYICI_YOLU + " <motor> <EV_KOKU> <SPEC_DOSYASI> [ETIKET] "
        "(ucuz motorlar: " + CANLI_MOTOR_LISTESI +
        "; kapalı motor kümesi: " + ISCI_MOTOR_LISTESI + "); (b) codex exec -C <ev> "
        "-s workspace-write -o <dosya> \"<spec>\"."
    )


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
MCP_KURAL_SURUMU = "20agu-2"

# 🔴 20 AGU (Okan emri: "KraL ve MaCiT evlerinde tarayiciyi ac — ikinizi de ac"):
# TARAYICI EKSENI ARTIK EV BAZLI. Bu iki evde ana oturum tarayiciyi KENDI SURER;
# kalan dort evde 8 Agu kurali AYNEN durur.
#
# 🔴🔴 IKI EKSEN AYRIDIR VE AYRI KALIR — BIRLESTIRME YASAK:
#   · SERT_BLOK_EVLER (yukarida)   -> CLAUDE ISCISI / Agent-Task yasagi (13 Agu Okan
#     emri; tek kacis PRUVO_CLAUDE_ISCI_IZNI=OKAN). Okuyanlar: _agent_karari + _isci_karari.
#   · TARAYICI_ACIK_EVLER (burasi) -> MCP tarayici araclarinin ANA OTURUMDA serbestligi.
# Iki kume BUGUN AYNI IKI EVI sayiyor ama ZIT hukum tasiyor: ayni evde tarayici ACIK,
# Claude iscisi KAPALI. Bu yuzden "ayni liste, sadelestirelim" DAVRANIS DEGISTIREN bir
# hatadir. Kumeyi bosaltmak/silmek/otekiyle degistirmek ikinci yasagi SESSIZCE acar ve
# hicbir yesil test gostermez — bu depoda olculdu (memory/ad-iki-rolde-mutanti-golgeler.md,
# K229 M6/M7). Nobetciler: mimar-kapi-mutasyon-test.py M1 (kumeleri birlestir -> Claude
# yasagi kolu KIRMIZI, tarayici kolu YESIL) + M2 (tarayici kolunu geri al -> tarayici kolu
# KIRMIZI, Claude yasagi kolu YESIL).
#
# FAIL-CLOSED taraf BILEREK secildi: liste ACIK evleri sayar, kapali evleri DEGIL.
# Tanimadik/yeni bir ev adi -> tarayici KAPALI (yeni ev sessizce acilmaz).
TARAYICI_ACIK_EVLER = ("pruvo", "pruvo-hasat")

# 🔴 ACIK EVDE KURAL VAR, BLOK YOK — MALIYET DISIPLINI (Okan, 20 Agu): tarayicida ONCE
# METIN. `get_page_content` / `read_page` ile oku; EKRAN GORUNTUSU yalnizca aranan rakam
# metinden okunamiyorsa ve TEK KARE alinir. Goruntu EN PAHALI token sinifidir — olculen
# vaka: 1 saatte baglamin %58'i. Bu bir MAKINE KAPISI degil, mimarin uydugu KURALDIR;
# kapi acik evde RED URETMEZ, disiplini mimar tasir.
TARAYICI_MALIYET_KURALI = (
    "TARAYICI MALİYET DİSİPLİNİ (20 Ağu): önce METİN — `get_page_content` / `read_page`. "
    "Ekran görüntüsü YALNIZCA aranan rakam metinden okunamıyorsa ve TEK KARE. Görüntü en "
    "pahalı token sınıfıdır (ölçülen vaka: 1 saatte bağlamın %58'i)."
)

MCP_GEREKCE = (
    "MCP-TARAYICI KAPISI (8 Ağu · 20 Ağu ev bazlı): mimar ANA oturumu bir tarayıcı aracı "
    "çağırıyor ve BU EV tarayıcıya açık evler arasında DEĞİL (açık evler: " +
    " / ".join(TARAYICI_ACIK_EVLER) + "). Bu evde ana döngüde tarayıcı sürmek KAPALI — her "
    "tur ekran görüntüsü taşır ve görüntü EN PAHALI token sınıfıdır (ölçülen vaka: 1 "
    "saatte bağlamın %58'i). ÇÖZÜM: TARAYICIYI GÖRSEL-SINIF CLAUDE İŞÇİSİNE VER — Codex'e "
    "VERİLMEZ (görsel = codex-isci yasak listesi). İŞÇİ ŞABLONU (Agent aracı: model sonnet "
    "+ isolation worktree + background), prompt'un ilk satırı: 'codex-muafiyet: tarayıcı "
    "ile <ne ölçülecek> — görsel'; spec'e ÇALIŞTIRILABİLİR kabul yaz (hangi URL'de hangi "
    "sayı ölçülecek), işçi ölçsün, sen SAYIYLA kapat. İşçi çağrılarında (agent_id dolu) bu "
    "kapı hiçbir kural uygulamaz — tarayıcı orada SERBESTTİR. " + TARAYICI_MALIYET_KURALI
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


def _tarayici_ekseni_acik_mi():
    """Bu EVDE ana oturumun tarayici surmesi serbest mi? (20 Agu Okan emri)

    🔴 SERT_BLOK_EVLER'e BAKMAZ ve BAKMAYACAK. O kume Claude iscisi / Agent-Task
    yasagini tasir; bu fonksiyon YALNIZ tarayici eksenini yanitlar. Iki eksenin tek
    yukleme indirgenmesi, tarayiciyi acan bir degisiklikte Claude yasagini da sessizce
    acar (memory/ad-iki-rolde-mutanti-golgeler.md)."""
    return EV_ADI in TARAYICI_ACIK_EVLER


# ============ 13 AGU: ISCI-SARMALAYICI KAPISI (goc karari) ============
# OLCULEN DELIK: 13 Agu gocu isci katini '~/.claude/cron/isci.sh <motor> <ev> <spec>
# [etiket]' sarmalayicisina tasidi. (O gunun ucuz kati minimax-m3/deepseek idi; 15 Agu
# emeklilikleriyle CANLI kat artik CANLI_ISCI_MOTORLARI'dir — bu metin TARIHTIR, dagitim
# tablosu DEGIL; guncel kume icin mimar_kimlik.py'ye bak.)
# Ama 20 Tem'in "repo DISINDAKI betigi kosturma" kurali (main() A adimi)
# sarmalayiciyi da REDDEDIYORDU. Sonuc TERSINE TESVIK: mimarin UCUZ motora is verme yolu
# MAKINE tarafindan kapali, geriye yalniz PAHALI yol (Claude iscisi = Agent araci) kaliyor.
# KANIT: '~/.claude/cron/isci.log' — sarmalayicinin tum kosumlari ev=pruvo-hasat; KraL
# evinde sarmalayici BIR KEZ BILE kosmadi.
#
# DOKTRIN (26 Tem BaBa hukmu ile AYNI SINIF): sarmalayiciyi cagirmak KENDI ELIYLE IS
# YAPMAK DEGIL, ISCI DAGITMAKTIR — tipki 'codex exec' gibi. Bu yuzden KOSULSUZ MUAFIYET
# DEGIL, ayni KALITE KAPISI kurulur.
#
# 🔴 YOL TAM ESITLIKLE ARANIR (basename/goreli yol KABUL EDILMEZ): aksi halde 'isci.sh'
# adli HER betik repo-disi muafiyet anahtari olurdu. '/tmp/isci.sh' bu yuzden RED alir.
#
# 🔴 20 AGU (K250) — EV-GORELI COZUMLEME, MAKINEYE CAKILI YOL DEGIL. Eski hali
# "/Users/okan/.claude/cron/isci.sh" diye SABIT yaziliydi. Iki kusur birden:
#   (a) TASIYICILIK: bu kural ARTIK commit'lenen sablonun icinde yasiyor (K250 hukmu —
#       kurulum betigi TEK TASIYICI degil), yani baska makinede/hesapta checkout edilen
#       her kopyaya AYNEN iniyor. Sabit yol o kopyalarda YANLIS olurdu.
#   (b) SIZINTI: bu depo PUBLIC; commit'lenen metinde kullanici adi tasiyan mutlak yol
#       istenmez.
# COZUMLEME expanduser'dir — TAM ESITLIK KARSILASTIRMASI AYNEN KALIR (asagidaki
# _isci_karari'nda '==' ile aranir). Yani kapi GENISLEMEDI, yalnizca ayni tek yolu
# tasinabilir bicimde HESAPLIYOR. HOME cozulemezse expanduser '~' ONEKINI OLDUGU GIBI
# birakir; o zaman hicbir gercek argv0 esitlesmez ve kural "sarmalayici DEGIL" der ->
# cagri A adimina duser ve REDDEDILIR (fail-closed, DAR taraf).
ISCI_SARMALAYICI_YOLU = os.path.expanduser("~/.claude/cron/isci.sh")
# m3-isci.sh YONLENDIRMEDIR: govdesi 'exec .../isci.sh minimax-m3 "$@"', yani imzasi
# MOTORSUZDUR (<ev> <spec> [etiket]) ve motoru minimax-m3'e CIVILIDIR. Karar verirken
# basina bu motor konmus gibi degerlendirilir — ayri bir kural govdesi YAZILMAZ.
ISCI_M3_SARMALAYICI_YOLU = os.path.expanduser("~/.claude/cron/m3-isci.sh")
ISCI_M3_CIVILI_MOTOR = "minimax-m3"
# KAPALI KUME ortak mimar_kimlik.py kaynagindan gelir; burada ikinci tablo tutulmaz.
# Argument sayisi (motor DAHIL): 3 (<motor> <ev> <spec>) ya da 4 (+ <etiket>).
ISCI_ARGUMAN_SAYILARI = (3, 4)
# SURUM DAMGASI — tools/mimar-kapi-kur.py --isci-kapisi bu dizeyi arayarak "bu evde
# ISCI-SARMALAYICI kurali var mi" sorusunu MAKINE olarak yanitlar (idempotans + 6 ev
# dogrulamasi; --codex-kurali / --agent-kapisi / --mcp-kapisi ile AYNI kalip). Kurali
# degistirirsen damgayi da yukselt.
ISCI_KURAL_SURUMU = "e50b19892a39"
ISCI_MOTOR_LISTESI = " / ".join(ISCI_MOTORLARI)
# 19 AGU (K214): INSAN-OKUR metin CANLI kumeden turer. Eski hali "minimax-m3 /
# deepseek-pro / deepseek-flash" diye ELLE yazilmisti — yani kapi reddederken mimara
# EMEKLI iki kati ONERIYORDU. Oneri de dagitimdir; o da canli kumeden cikmali.
CANLI_MOTOR_LISTESI = " / ".join(CANLI_ISCI_MOTORLARI)
EMEKLI_MOTOR_LISTESI = " / ".join(EMEKLI_ISCI_MOTORLARI)
ISCI_GEREKCE_SONU = (
    " DOGRUSU: " + ISCI_SARMALAYICI_YOLU + " <MOTOR> <EV_KOKU> <SPEC_DOSYASI> [ETIKET] "
    "(m3 kisayolu: " + ISCI_M3_SARMALAYICI_YOLU + " <EV_KOKU> <SPEC_DOSYASI> [ETIKET]). "
    "Gecerli motor: " + ISCI_MOTOR_LISTESI + "."
)
# motor=claude reddinde IKI CIKISI net soyleyen kuyruk (AGENT-KAPISI ile AYNI doktrin).
ISCI_CLAUDE_GEREKCESI = (
    "ISCI-SARMALAYICI KAPISI (13 Ağu): sarmalayıcı 'claude' MOTORUYLA çağrılıyor ama SPEC "
    "DOSYASINDA 'codex-muafiyet:' BEYAN SATIRI YOK. Bu şart olmasaydı sarmalayıcı "
    "AGENT-KAPISI'nı atlatan bir ANAHTAR olurdu (mimar -> isci.sh claude -> sürtünmesiz "
    "Claude işçisi). İKİ ÇIKIŞ: (a) İŞİ UCUZ MOTORA VER (" + CANLI_MOTOR_LISTESI +
    "); VEYA (b) spec dosyasına şu satırı EKLE: "
    "'codex-muafiyet: <iş tanımı> — {ornek}' (geçerli sınıf jetonları: {liste} — "
    "codex-isci yasak listesi)."
)


def _isci_karari(tokenlar):
    """13 AGU — isci sarmalayicisi cagrisinin KARARI. _codex_karari ile AYNI bicim:
        None    → segmentin CALISTIRILAN programi sarmalayici DEGIL (kural uygulanmaz)
        "gecer" → izinli (isci dagitmak mimarliktir) — cagiran SEGMENTI KAPATIR
        str     → red gerekcesi

    KABA + FAIL-CLOSED (parser taklidi YASAK). Sira:
      1. YOL: tokenlar[0] TAM ESITLIKLE iki sarmalayici yolundan biri olacak
         (basename esitligi / goreli yol KABUL EDILMEZ).
      2. m3-isci.sh YONLENDIRME: imza motorsuz, motor minimax-m3'e CIVILI — basina o
         motor konmus gibi degerlendirilir (ikiz kural govdesi yazilmaz).
      3. ARGUMAN SAYISI (motor dahil) 3 ya da 4; disi RED.
      4. MOTOR kapali kumeden olacak; bilinmeyen motor VARSAYILAN RED.
      5. motor == 'claude' ise AGENT-KAPISI'nin BEYAN SARTI AYNEN gecerli: SPEC DOSYASI
         okunur ve MEVCUT AGENT_MUAFIYET_RE ile eslesmeli (IKIZ TANIM YOK — ayni regex).
      6. Spec dosyasi okunamiyorsa RED: "beyani olcemedim" YESIL DEGILDIR (fail-closed).

    KIMLIK EKSENI TASINMAZ (spec md. 9): ISCI (agent_id DOLU) main() basinda zaten muaf;
    burada ikinci bir 'isci mi' testi YOKTUR (memory/ikiz-tanim-sessiz-ayrisma.md)."""
    if not tokenlar:
        return None
    argv0 = tokenlar[0]
    if argv0 == ISCI_M3_SARMALAYICI_YOLU:
        argumanlar = [ISCI_M3_CIVILI_MOTOR] + list(tokenlar[1:])
    elif argv0 == ISCI_SARMALAYICI_YOLU:
        argumanlar = list(tokenlar[1:])
    else:
        return None

    if len(argumanlar) not in ISCI_ARGUMAN_SAYILARI:
        return (
            "isçi sarmalayıcısı YANLIŞ ARGÜMAN SAYISIYLA çağrılıyor (motor dahil " +
            str(len(argumanlar)) + "; beklenen 3 ya da 4). Eksik/fazla argüman = kurulmamış "
            "delegasyon: hangi ev, hangi spec koşacağı belirsiz kalır."
        )

    motor = argumanlar[0]
    if motor not in ISCI_MOTORLARI:
        return (
            "isçi sarmalayıcısının MOTORU kapalı kümede DEĞİL (" + motor[:24] + "). "
            "Bilinmeyen motor VARSAYILAN RED (fail-closed): yarın eklenecek bir motor bu "
            "kapıyı kendiliğinden AÇMAZ."
        )

    # 19 AGU (K214) SIKILASTIRMA — EMEKLI KAT: kapali kume KIMLIK icindir (emekli
    # motorlarin ESKI turleri isci sayilmali), DAGITIM icin degil. Emekli bir kata
    # YENI IS yollamak sessizce KABUL ediliyordu; artik ACIK GEREKCEYLE reddedilir.
    # 🔴 'claude' BU KOLUN DISINDADIR — YORUM DEGIL, KOSUL. Onceki hali "claude emekli
    # DEGILDIR" diye YORUMLA guvence veriyordu; yorum olcum degildir ve OLCULDU (K214, ucuncu
    # eksen): `claude` bir gun EMEKLI_ISCI_MOTORLARI'na girerse bu kol asagidaki claude
    # kolundan ONCE donuyordu ve Okan'in YETKILI CIKISI SESSIZCE KAPANIYORDU —
    #   Ⓑ claude emekli DEGIL + PRUVO_CLAUDE_ISCI_IZNI=OKAN -> allow   (taban)
    #   Ⓓ claude EMEKLI      + PRUVO_CLAUDE_ISCI_IZNI=OKAN -> deny/EMEKLI  (REGRESYON)
    # Taban Ⓑ 'allow' oldugu icin Ⓓ'nin reddi gercek davranis gerilemesiydi.
    # HUKUM: 'claude'un DAGITIMI kendi koluna aittir (sert blok + OKAN izni + beyan sarti);
    # emekli KATI listesi onu YONETMEZ. Vakalar: mimar-kilit-test.py 922/923/924 — bu kosul
    # kaldirilirsa dordu de KIRMIZI yanar ([[ad-iki-rolde-mutanti-golgeler]]).
    if motor != "claude" and emekli_motor_mu(motor):
        return emekli_gerekcesi(motor)

    if (motor == "claude" and EV_ADI in SERT_BLOK_EVLER and
            os.environ.get("PRUVO_CLAUDE_ISCI_IZNI") != "OKAN"):
        return _sert_blok_gerekcesi()

    if motor == "claude":
        spec_yolu = argumanlar[2]
        try:
            with open(spec_yolu, encoding="utf-8") as f:
                spec_metni = f.read()
        except Exception:
            return (
                "isçi sarmalayıcısı 'claude' MOTORUYLA çağrılıyor ama SPEC DOSYASI "
                "OKUNAMADI (" + spec_yolu[:70] + "): beyanı ÖLÇEMEDİM. Ölçülemeyen beyan "
                "YEŞİL DEĞİLDİR (fail-closed)." + ISCI_CLAUDE_GEREKCESI.format(
                    ornek=AGENT_ORNEK_SINIF, liste=AGENT_SINIF_LISTESI)
            )
        if not AGENT_MUAFIYET_RE.search(spec_metni):
            return ISCI_CLAUDE_GEREKCESI.format(
                ornek=AGENT_ORNEK_SINIF, liste=AGENT_SINIF_LISTESI)

    return "gecer"


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
    "'python3 tools/d1-sync.py --durum'; /.claude/worktrees/ içinden çalışan işçi oturumları. "
    "(27 Ağu K318 — ROL EKSENİ: bu son madde artık ÖLÇÜLÜYOR. Çip/worktree oturumunda "
    "ölçüm komutları, curl ve python3/node ARAÇ koşumu SERBESTTİR; ana oturumda kapalıdır. "
    "Rol, oturum damgasından okunur — `cd <worktree>` rolü DEĞİŞTİRMEZ.)"
)


# Codex reddinde GEREKCE_SONU KULLANILMAZ: o metin "bu isi isciye delege et" der, oysa
# codex cagrisi ZATEN delegedir (26 Tem hukmu) — yanlis yol tarif ederdi. Yerine eksik
# olan TEK seyi soyleyen kisa kuyruk.
CODEX_GEREKCE_SONU = (
    " DOGRUSU: codex exec -C /Users/okan/dev/pruvo -s workspace-write "
    "-o /<scratchpad>/son-mesaj.txt \"<spec>\" — sonra dosyayi oku, sayiyla kapat. "
    "(skill: codex-isci)"
)


# 27 AGU (K318) — ROL TESHISI. main() doldurur, reddet() gerekcenin SONUNA ekler.
# NEDEN VAR: rol ekseni FAIL-CLOSED'dur; olculemeyen bir baglam ANA sayilir ve REDDEDILIR.
# Teshis satiri olmasaydi "neden hala reddediliyorum" sorusu yine HAFTALAR surerdi — bu
# isin BEDELI zaten oydu. Satir yalniz TANI tasir, karar TASIMAZ.
ROL_TANI = ""


def reddet(neden, sonu=None):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": GEREKCE_BASI + neden +
                                        (GEREKCE_SONU if sonu is None else sonu) +
                                        ROL_TANI,
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


def _codex_bugun():
    """PRUVO_BUGUN (YYYY-MM-DD) env'den okunur; yoksa sistem tarihi. V6 vakasi icin
    ENJEKTE EDILEBILIR olmali (test kapali pencereyi simule edebilmeli)."""
    cevre = os.environ.get("PRUVO_BUGUN")
    if cevre:
        try:
            return datetime.date.fromisoformat(cevre)
        except ValueError:
            pass
    return datetime.date.today()


def _codex_pencere_acik_mi():
    """Bugun, CODEX_PENCERE_BITIS dahil mi? Sonrasi = kapali. Tarih enjekte
    edilebilir (PRUVO_BUGUN). False donerse codex yeniden KAPALI sayilir
    ([[goc-yolu-eski-kapiya-takilir]] — istisnanin sessiz kalicilasmasini onler)."""
    try:
        bitis = datetime.date.fromisoformat(CODEX_PENCERE_BITIS)
    except ValueError:
        return False  # tek kaynak bozuksa kapali say (fail-closed)
    return _codex_bugun() <= bitis


def _codex_model_bayrak_var(kalan):
    """Kalan tokenlarda '-m' ya da '--model' VAR MI? Kaba tarama — parser taklidi
    YASAK (ayni sinif: c27de-1). Tek kriter: bayrak token olarak bulunuyor."""
    for t in kalan:
        if t == "-m" or t == "--model":
            return True
    return False


def _codex_model_adi(kalan):
    """Bayraktan HEMEN sonraki token, '-' ile baslamayan bir deger ise model adidir.
    Bitisik/esitlikli bicim (or. '-mluna', '--model=luna') YOK SAYILIR (fail-closed):
    kural yalniz acik ayrik bicimi kabul eder; bayraksiz sayfa zaten bir onceki
    kontrol ile REDDEDILDI. None donerse model gecersiz bicimde (hata mesajinda
    'belirsiz' muamelesi YAPILMAZ — tek bir kaba kural yeterli)."""
    for i, t in enumerate(kalan):
        if t == "-m" or t == "--model":
            if i + 1 < len(kalan):
                deger = kalan[i + 1]
                if deger and not deger.startswith("-"):
                    return deger
            return ""
    return None


def _codex_cikti_valid_helper(kalan):
    """Kural 1 icin OZGUN cikti-bayragi gecerliligi: mevcut _codex_cikti_degerli'nin
    MUTASYONLU halinden BAGIMSIZ olmali — yoksa ME11/ME13/ME14 (cikti-bayragi
    deger/bicim kontrollerini kaldiran mutantlar) yalnizca benim kural 1'i tetikler
    ve beklenen RED -> ALLOW gecisini SAGLAYAMAZ (mutant yapsa bile kural 1 onceki
    RED durumunu korur). Buradaki mantik _codex_cikti_degerli ile aynidir; mutasyon
    olsa bile bagimsiz degerlendirir. Cift degerlendirme maliyeti kucuk (cagri basina
    birkaç token tarama)."""
    tokenlar = kalan[1:]
    for i, t in enumerate(tokenlar):
        if t in CODEX_CIKTI_BAYRAKLARI:
            if i + 1 < len(tokenlar):
                deger = tokenlar[i + 1]
                if deger and not deger.startswith("-"):
                    return True
            return False
        if t.startswith(CODEX_CIKTI_ONEKI):
            deger = t[len(CODEX_CIKTI_ONEKI):]
            if deger and not deger.startswith("-"):
                return True
            return False
    return False


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
    # === 17 AGU K159: SURELI PENCERE + MODEL KAPISI (cikti-bayragi KURALINDAN SONRA) ===
    # Yer: mevcut cikti-bayragi kuralinin ARDINDA — boylece eski reddeden vakalar (cikti
    # bayragi yok/eksik) zaten oncesinde elendigi icin bu kurallarin kirmizi kumesini
    # SUNI olarak genisletmesi engellenir. Sira fail-fast: pencere -> model bayrak ->
    # amiral -> bilinmeyen. Tarih PRUVO_BUGUN env ile testten enjekte edilebilir (V6).
    # ALT-KOMUT KORUMASI (27 Tem ME10 uyumu): codex'in `exec` DISINDAKI alt-komutlari
    # (resume/mcp/login/apply) icin bu kurallar UYGULANMAZ. Alt-komut kapisi yukarida
    # zaten RED (kalan[0] != 'exec'); eger ME10 gibi bir mutasyon o kapisi kapatirsa,
    # alt-komut yine de 'exec' degilse burada `gecer` ile cikip model kurallarimizi
    # UYGULAMIYORUZ — yoksa ME10'un bekledigi {264..275} kirmizi kumesi TAM-ESITLIK
    # testini bozar.
    if kalan[0] != CODEX_IZINLI_ALTKOMUT:
        return "gecer"
    if not _codex_pencere_acik_mi():
        return (
            "codex SURELI PENCERESI KAPANDI (" + CODEX_PENCERE_BITIS + " dahil, "
            "bugun sonrasi). Sureli istisna 17->20 Agu ile sinirliydi; 20 Agu itibariyle "
            "codex yeniden KAPALI (emeklilik yururlukte). Yeni karar Okan'da — codex "
            "yerine kimi/minimax-m3'e delege et."
        )
    if not _codex_model_bayrak_var(kalan[1:]):
        if _codex_cikti_valid_helper(kalan):
            return (
                "codex cagrisinda MODEL BAYRAGI (-m ya da --model) YOK. Bayraksiz cagri "
                "saglayicinin VARSAYILAN amiral modeline duser; Okan emri: amiral yasak. "
                "DOGRUSU: codex exec -m <model> ... (izinli: " +
                ", ".join(CODEX_IZINLI_MODELLER) + ")."
            )
    model = _codex_model_adi(kalan[1:])
    # Kurallar 2 ve 3 SADECE model gercekten BELIRTILDIYSE tetiklenir (kural 1'in
    # erken donusu zaten no-flag durumunu elemis olsa da, mutasyon testinin mutlak
    # tek-iz ayirt ediciligi icin burada da `if model` ile bekci konuldu; boylece
    # M1 (-m zorunlulugu kaldirilir) bayraksiz vakayi ALLOW'a cevirir, M2 (amiral
    # reddi kaldirilir) ise YASAK listesini ATLAYARAK amiral'in kalan kurallardan
    # (ozellikle `not in IZINLI`) gecmesini engeller). Model yasak ise zaten kural 2
    # doner; kural 3 yasak'i tekrar kontrol etmez (`not in YASAK AND not in IZINLI`).
    if model:
        if model in CODEX_YASAK_MODELLER:
            return (
                "codex modeli AMIRAL SINIFINDA (" + model + "). Okan karari: amiral "
                "(" + ", ".join(sorted(CODEX_YASAK_MODELLER)) + " dahil) yasak. IZINLI: " +
                ", ".join(CODEX_IZINLI_MODELLER) + "."
            )
        if model not in CODEX_IZINLI_MODELLER and model not in CODEX_YASAK_MODELLER:
            return (
                "codex modeli IZINLI KUMEDE DEGIL (" + model + "). Fail-closed: yarin "
                "eklenecek bir model kapiyi kendiliginden ACMAMALI. IZINLI: " +
                ", ".join(CODEX_IZINLI_MODELLER) + "."
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
    if (EV_ADI in SERT_BLOK_EVLER and
            os.environ.get("PRUVO_CLAUDE_ISCI_IZNI") != "OKAN"):
        return _sert_blok_gerekcesi()
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
    """22 Tem — mimar tarafinda python/node ALLOWLIST'i. YALNIZ uc tam komut serbest:
        python3 tools/durum.py                          (baska argüman YOK)
        python3 tools/d1-sync.py --durum                (yalniz --durum)
        python3 tools/defter-rotasyon.py <defter> <arsiv>  (18 Agu K168 H1)
    3. satir (K168 H1): 'defter-rotasyon.py' uzerinden DEVAM.md -> DEVAM-ARSIV.md
    rotasyonu icin serbest. Konum argumanlari kanonik DEVAM.md ve DEVAM-ARSIV.md
    yolu olmali (baska yol = RED).

    === 20 AGU 2026 (K258): DEFTER BAKIMI KOVASI ===
    Bayrak YASAGI TOPTAN kaldirilmadi, ADLANDIRILMIS bir kovaya baglandi:
        python3 tools/defter-rotasyon.py DEVAM.md DEVAM-ARSIV.md
                [--tavan-kaynaktan] [--isaretciye-indir]
        python3 tools/kutu-arsivle.py [--kuru]
    Izinli bayrak kumesi TAM ESITLIKLE DEFTER_BAKIMI_BAYRAKLARI'nda tanimlidir;
    kume DISINDAKI her bayrak (--tavan-sayi / --tarih / --tavan 300 / =li yazim)
    RED kalir. Kapinin olcum/icra yasaginin GERI KALANI GEVSETILMEZ.
    tools/recete-kapisi.py bu serbesti KURU kontrol eder.
    Yol tam-yol ya da repo-goreli olabilir (_coz ile cozulur); node/python2/pypy
    icin IZINLI KOMUT YOKTUR (hepsi RED). 'Baska argüman eklenirse RED' — len
    kontrolu bunu saglar."""
    if not re.match(r"^python3(\.\d+)?$", ad):
        return False
    if not argumanlar:
        return False
    ilk = _coz(argumanlar[0], cwd)
    if ilk == DURUM_YOL:
        return len(argumanlar) == 1
    if ilk == D1_YOL:
        return len(argumanlar) == 2 and argumanlar[1] == "--durum"
    if ilk == DEFTER_ROTASYON_YOL:
        # K168 H1 + K258 DEFTER BAKIMI KOVASI. Eskiden HER bayrak kesiliyordu
        # ('hicbir arg "-" ile baslayamaz'); kapinin kendi bastigi CARE de o
        # yuzden reddediliyordu. Bayrak artik TOPTAN serbest DEGIL: yalnizca
        # DEFTER_BAKIMI_BAYRAKLARI kumesindekiler (TAM ESITLIK) gecer, kume
        # disindaki her bayrak — '--tavan-sayi 130' ve '--tavan-sayi=130'
        # dahil — RED kalir. Konumsal arg sayisi ve kanonik yol dogrulamasi
        # AYNEN durur.
        if not _bakim_bayraklari_izinli(DEFTER_ROTASYON_YOL, argumanlar[1:]):
            return False
        if not _bakim_konumlari_izinli(DEFTER_ROTASYON_YOL, argumanlar[1:], cwd):
            return False
        konumlar = [a for a in argumanlar[1:] if not a.startswith("-")]
        d1 = _coz(konumlar[0], cwd)
        d2 = _coz(konumlar[1], cwd)
        return d1 == DEFTER_ROTASYON_DEFTER and d2 == DEFTER_ROTASYON_ARSIV
    if ilk == KUTU_ARSIVLE_YOL:
        # K258: ORTAK POSTA KUTUSU bakimi. Kapida ONCEDEN HIC gecmiyordu ->
        # genel `return False`. Kanonik cagri konumsal arg ALMAZ (kutu/arsiv
        # yollari aracin kendi TEK KAYNAGINDAN gelir); izinli tek bayrak
        # '--kuru'. '--tavan 300' gibi sayi tasiyan hicbir bayrak GECMEZ —
        # tavan sahibi araciN kendisidir, komuta ELLE yazilan sayi ikinci
        # kopya olurdu ([[ikiz-tanim-sessiz-ayrisma]]).
        if not _bakim_bayraklari_izinli(KUTU_ARSIVLE_YOL, argumanlar[1:]):
            return False
        return _bakim_konumlari_izinli(KUTU_ARSIVLE_YOL, argumanlar[1:], cwd)
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
        iz_bas(kimlik_izi(girdi))
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

    # === 8 AGU MCP-TARAYICI KAPISI (20 AGU: EV BAZLI) ===
    # ISCI (agent_id dolu) YUKARIDA zaten muaf cikti — bu satirin kimlik testi TASIMAMASI
    # kasitlidir: tespit TEK KAYNAKTAN (main() basi) gelir, ikinci mekanizma yazilmaz.
    # Kapsam DISI hicbir arac bu koldan gecmez (_mcp_tarayici_mi onek kumesi); Bash/Agent/
    # Write kollarinin davranisi DEGISMEZ (regresyon 0).
    #
    # 🔴 20 AGU (Okan): ACIK EVLERDE (KraL/pruvo + MaCiT/pruvo-hasat) red YOK — mimar
    # tarayiciyi kendi surer, maliyet disiplini KURAL olarak tasinir (bkz.
    # TARAYICI_MALIYET_KURALI). Kalan dort evde 8 Agu reddi AYNEN durur. Bu kol
    # SERT_BLOK_EVLER'e DOKUNMAZ: Claude iscisi / Agent-Task yasagi YUKARIDAKI ayri
    # kolda, ayri kumeyle, DEGISMEDEN durur.
    if _mcp_tarayici_mi(tool_name):
        if not _tarayici_ekseni_acik_mi():
            reddet(MCP_GEREKCE, sonu="")
        # ACIK EV: hukum IMZADAN okunabilsin diye ayirt edici iz basilir
        # (memory/rc-hukmu-kapi-imzasini-ezer.md — rc tek basina hukum degildir).
        iz_bas("MIMAR-tarayici-acik-ev")
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

    # === 27 AGU 2026 (K318) — ROL EKSENI: ANA OTURUM mu, CIP/WORKTREE OTURUMU mu? ===
    # Gerekce ve olcum ekseninin TAMAMI mimar_kimlik.rol_ekseni'nin bas yorumundadir.
    # Burada yalnizca KAPSAM yazilidir — ve kapsam BILEREK DARDIR:
    #
    #   CIP'TE ACILAN (mimarin "kendi elimle is yapmam" kollari — icra/olcum):
    #     * OLCUM_KOMUTLARI (du/find/wc/head/tail/sed/awk/sort/stat/file ...)
    #     * curl / wget (canli dogrulama — cip'in KABUL olcumu bunsuz kapanmaz)
    #     * python3/node ALLOWLIST'i (durum.py + d1-sync.py disina cikis)
    #
    #   CIP'TE DE KAPALI KALAN (kapsam disi — bunlar "mimar eliyle is" kurali DEGIL,
    #   Okan emri ya da repo hijyeni tasir; acilsalardi bu bir GEVSETME olurdu):
    #     * AGENT-KAPISI (Claude iscisi / Agent-Task yasagi, 13 Agu Okan emri) — rol
    #       kolundan ONCE, main() basinda kosar ve bu satira HIC ugramaz.
    #     * ISCI-SARMALAYICI kapisi (isci.sh claude + sert blok evler) — dongude, rol
    #       bayragina BAKMAZ.
    #     * codex KALITE kapisi (-o <dosya> sarti) — delegasyon standardi herkese esittir.
    #     * A) repo DISINDAKI betigi dogrudan cagirma, A2) yorumlayiciya env ile kod
    #       enjeksiyonu, C) satir-ici kod (-c/-e/stdin), R2) argumanlarda repo DISI yol,
    #       F) betigin repo ICINDE olmasi — hepsi cipte de AYNEN kosar. Yani cip
    #       repo ICINDEKI araci kosturur; scratchpad betigi ve satir-ici kod ona da kapali
    #       (CLAUDE.md komut stili: betigi .py'ye YAZ, sonra duz calistir).
    #
    # ANA OTURUM icin DAVRANIS DEGISMEDI: cip_koku None kalir, asagidaki her kol bugunku
    # gibi REDDEDER (kontrol vakalari 800/801/805/806).
    global ROL_TANI
    cip_koku = rol(girdi)
    cip = cip_koku is not None
    if cip:
        iz_bas("CIP(" + os.path.basename(cip_koku) + ")")
    else:
        ROL_TANI = (
            " [ROL=ANA — bu oturum mimarin ANA oturumu sayildi. Rol ekseni "
            "OTURUM DAMGASINDAN (transcript_path) olculur ve git'e KAYITLI worktree "
            "kokleriyle TAM BILESEN esitligi aranir; cwd/beyan OKUNMAZ. Cip oturumunda "
            "hala RED aliyorsan olculen sey su: damga=" +
            (os.path.basename(os.path.dirname(str(girdi.get("transcript_path") or ""))) or
             "<YOK>")[:80] + " kayitli_worktree=" + str(len(kayitli_worktree_kokleri())) + "]"
        )

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
        if ad in OLCUM_KOMUTLARI and not cip:
            reddet(
                "ölçüm / dosya-tarama komutu (" + ad + "). Boyut, sayım, arama, içerik "
                "dökme, sıralama — bunlar İŞÇİNİN işidir; mimar okur, karar verir, ÖLÇTÜRÜR."
            )
        if ad in ("curl", "wget") and not cip:
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

        # === 13 AGU ISCI-SARMALAYICI KAPISI ===
        # A ADIMINDAN ONCE degerlendirilir: sarmalayicinin argumanlari BILEREK repo
        # DISIDIR (baska ev koku + scratchpad spec'i bu isin TANIMIDIR), yani A adimi ve
        # yol taramasi (dis_yol) bu cagriyi yapisal olarak reddederdi. 'gecer' halinde
        # segment KAPATILIR (continue) — codex kolundan FARKI budur ve bilerekdir.
        isci_karari = _isci_karari(tokenlar)
        if isci_karari is not None:
            if isci_karari != "gecer":
                reddet(isci_karari, sonu=ISCI_GEREKCE_SONU)
            continue

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
            # 27 AGU (K318): CIP'te ALLOWLIST atlanir — AMA SEGMENT KAPATILMAZ. Akis
            # bilerek asagi duser: C (satir-ici kod), R2 (argumanlarda repo DISI yol) ve
            # F (betik repo ICINDE mi) cipte de kosar. 'continue' yazmak, cipe
            # 'python3 -c ...' ve 'python3 /private/tmp/x.py' yollarini acardi —
            # o bir GEVSETME olurdu, kapsam duzeltmesi degil (vaka 808/809).
            if not cip:
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
