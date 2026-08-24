#!/usr/bin/env python3
"""tools/mimar-icra-kapisi.py'yi .claude/settings.json'daki PreToolUse/Bash zincirine
kaydeder. DAR + IDEMPOTENT + TEK YONLU: yalnizca bu tek kancayi EKLER; hicbir mevcut
kancayi, izni ya da ayari silmez/degistirmez. Zaten kayitliysa dokunmaz.

Neden ayri arac: .claude/ gitignore'da ve commit EDILMIYOR — koruma tek makinede yasiyor.
Ayrica canli kanca konfigurasyonu Okan'in kapisi; muhendis oturumu kendi basina canli
ayar dosyasini degistirmez. Bu araci Okan (ya da mimar) BIR KEZ kostururur:

    python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py            # ne yapacagini yazar
    python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py --uygula   # uygular (yedekli)

Kurulumdan sonra dogrulama:
    python3 /Users/okan/dev/pruvo/tools/mimar-kilit-test.py

26 TEM EKI — '--izinler': permissions.allow dizisine codex icin IKI BELGELEYICI satir
ekler (kapi karari tools/mimar-icra-kapisi.py'de; bu satirlar YALNIZ belge/niyet).
Ayri mod olmasinin sebebi OLCULDU: .claude/ gitignore'da, yani muhendis dalindan
merge ile TASINMAZ — canli makinedeki dosyaya ancak commit'li bir araci kosturarak
girer. Kanca kurulumuyla ayni desen: DAR + IDEMPOTENT + TEK YONLU (silmez).

    python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py --izinler
    python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py --izinler --uygula

27 TEM EKI — '--codex-kurali' (BaBa doktrin hukmu): "codex exec CIKTI DOSYASI sarti" 6
EVDE de gecerli. Kural ARTIK BU BETIGE GOMULU (CODEX_SABLON) — makine/hesap gocunde
kapi-kuruluşuyla TEK HAMLEDE iner, kardes evlerin scratchpad'inde kalan bir sablona
bagli DEGIL. KraL evi 'kaynak' modundadir (kural commit'li tools/mimar-icra-kapisi.py'de
yasar; bu arac orayi YAZMAZ, yalnizca DOGRULAR); diger 5 ev 'enjekte' modundadir.

    python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py --codex-kurali
    python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py --codex-kurali --uygula

Desen (mevcut modlarla AYNI): DAR + IDEMPOTENT + YEDEKLI + FAIL-CLOSED.
  * her ev icin once <dosya>.yedek-<zaman> alinir (ev ICINDE, /tmp'de DEGIL),
  * enjeksiyon sonrasi dosya DERLENIR (compile) + IKI CANLI FIKSTUR kosturulur
    ('codex exec "x"' DENY olmali, 'ls' ALLOW kalmali); biri tutmazsa O EV DERHAL
    YEDEKTEN GERI ALINIR (yanlis-pozitif bir evin TUM delegasyonunu durdurur),
  * PER-MAKINE SIFIR-COMMIT: kardes repolara commit YOK; yedekler .git/info/exclude'a,
    izlenen dosyalar 'update-index --skip-worktree' ile git'in gozunden korunur,
  * mevcut kural blogu ESKI damgaliysa marker'lar arasi blok SOKULUP yenisi konur
    (kural yukseltmesi de tek hamle).
"""
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

# === 19 AGU 2026 (K214): MOTOR KUMESI TEK KAYNAKTAN TURETILIR ===
# OLCULEN KOK NEDEN: bu betik ISCI_MOTORLARI'ni KENDI GOVDESINE GOMUYORDU ve 13 Agu'da
# BES karde eve o donmus kopyayi kurdu. Sonuc: kurulan kapilar EMEKLI deepseek-*'i kabul
# edip CANLI birincil kimi'yi REDDEDIYORDU — tek kaynak (tools/mimar_kimlik.py) 15 Agu'da
# guncellenmisti ama kurulu kopyalar 13 Agu'da DONMUSTU ([[ikiz-tanim-sessiz-ayrisma]]).
# Kurulan kopya AYRI repolarda oldugu icin `import` edemez; bu yuzden deger KURULUM
# ANINDA tek kaynaktan okunup metne DOKULUR (mimar_kimlik.motor_blogu_kaynagi) ve blogun
# icine KAYNAK IMZASI damgalanir. Sapmayi tools/motor-tek-kaynak-kapisi.py olcer.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mimar_kimlik import (  # noqa: E402
    CANLI_ISCI_MOTORLARI,
    EMEKLI_ISCI_MOTORLARI,
    ISCI_MOTORLARI,
    isci_damgasi,
    motor_blogu_kaynagi,
)

AYAR = "/Users/okan/dev/pruvo/.claude/settings.json"
KOMUT = 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-icra-kapisi.py"'
KAYIT = {
    "type": "command",
    "command": KOMUT,
    "timeout": 30,
    "statusMessage": "mimar icra kapisi",
}

# 28 TEM AGENT-KAPISI: AYNI kapi betigi (mimar-icra-kapisi.py) Agent/Task matcher'ina da
# baglanir. Mimar ANA oturumu bir Claude iscisi (Agent/Task) acarken 'codex-muafiyet'
# beyanini denetler; kapi karari betikte, bu KAYIT yalniz KABLODUR. Ayri matcher blogu:
# Bash-ozel nobetciler (komut-stili/urunler-guard) Agent/Task'a KOSMASIN.
AGENT_MATCHER = "Agent|Task"
AGENT_KAYIT = {
    "type": "command",
    "command": KOMUT,
    "timeout": 30,
    "statusMessage": "mimar agent kapisi",
}


def _matcher_blogu(kancalar, matcher):
    """PreToolUse listesinde matcher'i TAM esit olan blok (yoksa None)."""
    for blok in kancalar:
        if blok.get("matcher") == matcher:
            return blok
    return None


def _blokta_hook_var(blok, dosya_adi):
    """Blok icinde komutu dosya_adi geciren bir hook var mi?"""
    if blok is None:
        return False
    return any(dosya_adi in (k.get("command") or "") for k in (blok.get("hooks") or []))


PRECOMMIT = "/Users/okan/dev/pruvo/.git/hooks/pre-commit"

# 26 TEM (BaBa hukmu): codex cagrisi mimara ACILDI (tools/mimar-icra-kapisi.py kalite
# kapisi: cikti dosyasi bayragi sart). Bu iki satir permissions.allow'da BELGELEYICIDIR
# — kapi karari degil, niyet kaydi.
IZIN_SATIRLARI = [
    "Bash(/Applications/ChatGPT.app/Contents/Resources/codex exec *)",
    "Bash(/Applications/ChatGPT.app/Contents/Resources/codex --version)",
]


def _guvenli_yaz(veri):
    """AYAR'a yedekli yazar; uretilen JSON bozuksa yedegi geri koyar. Doner: True/False."""
    yedek = AYAR + ".yedek"
    shutil.copyfile(AYAR, yedek)
    io.open(AYAR, "w", encoding="utf-8").write(
        json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
    try:
        json.loads(io.open(AYAR, encoding="utf-8").read())
    except Exception as hata:
        shutil.copyfile(yedek, AYAR)
        print("BOZUK JSON URETILDI — yedek geri konuldu. Hata: " + str(hata))
        return False
    return True


def izinler(uygula):
    """permissions.allow'a EKSIK olan codex satirlarini ekler. Hicbir girdiyi SILMEZ."""
    if not os.path.exists(AYAR):
        print("BULUNAMADI: " + AYAR)
        sys.exit(1)
    veri = json.loads(io.open(AYAR, encoding="utf-8").read())
    liste = veri.setdefault("permissions", {}).setdefault("allow", [])
    eksik = [s for s in IZIN_SATIRLARI if s not in liste]
    print("AYAR_DOSYASI=" + AYAR)
    print("MEVCUT_IZIN_SAYISI=" + str(len(liste)))
    print("EKSIK_SATIR=" + str(len(eksik)))
    if not eksik:
        print("ZATEN TAM — degisiklik yok.")
        sys.exit(0)
    for s in eksik:
        print("EKLENECEK: " + s)
    print("SILINEN/DEGISEN: YOK (arac yalnizca ekler)")
    if not uygula:
        print("")
        print("Kuru kosum. Uygulamak icin ayni komuta --uygula ekle.")
        sys.exit(0)
    liste.extend(eksik)
    if not _guvenli_yaz(veri):
        sys.exit(1)
    print("")
    print("EKLENDI. Yedek: " + AYAR + ".yedek")
    sys.exit(0)


def _pretooluse(veri):
    return ((veri.get("hooks") or {}).get("PreToolUse") or [])


def _zincirde_var(veri, matcher_parcasi, dosya_adi):
    """PreToolUse bloklarindan matcher'i verilen parcayi ICEREN blokta, komut
    dizesinde dosya adi geciyor mu? Canli komut
    'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/x.py"' bicimindedir → eslesme dosya ADI
    uzerinden (alt-dize) yapilir."""
    for blok in _pretooluse(veri):
        matcher = blok.get("matcher") or ""
        if matcher_parcasi not in matcher:
            continue
        for kanca in (blok.get("hooks") or []):
            if dosya_adi in (kanca.get("command") or ""):
                return True
    return False


def durum():
    """SALT-OKUNUR kablo raporu. Cikti MAKINE OKUNUR: her satir ANAHTAR=DEGER.
    Uc anahtardan biri 'yok' ise exit 1.

    HEDEF DOSYALAR --ayar / --precommit ile degistirilebilir: kabul testi raporcuyu
    CANLI settings.json'a bagli kalmadan, kendi kurdugu gecici kopyalar uzerinde
    hem POZITIF (hepsi var) hem NEGATIF (biri eksik) yonden sinar. Boylece "durum()
    daima var der" mutasyonu KIRMIZI yanar (eski surumde nobetsizdi)."""
    try:
        veri = json.loads(io.open(AYAR, encoding="utf-8").read())
    except Exception:
        veri = {}

    bash_var = _zincirde_var(veri, "Bash", "mimar-icra-kapisi.py")
    yazma_var = _zincirde_var(veri, "Write", "mimar-kod-kilidi.py")

    precommit_var = False
    try:
        precommit_var = "mimar-commit-kapisi.py" in io.open(
            PRECOMMIT, encoding="utf-8", errors="replace").read()
    except Exception:
        precommit_var = False

    print("BASH_ZINCIRI_ICRA=" + ("var" if bash_var else "yok"))
    print("YAZMA_ZINCIRI_KILIT=" + ("var" if yazma_var else "yok"))
    print("PRECOMMIT_COMMIT_KAPISI=" + ("var" if precommit_var else "yok"))
    print("AYAR_DOSYASI=" + AYAR)
    sys.exit(0 if (bash_var and yazma_var and precommit_var) else 1)


# ===================== 27 TEM: CODEX KURALI 6 EVE (BaBa hukmu) =====================
# Kural METNI burada YASAR. Sebep (BaBa): 5 kardes evin kapi sablonu scratchpad'de
# kalmisti (kalici degil) — makine/hesap gocunde kural kaybolur. Artik commit'li bir
# betige gomulu: 'git pull + --codex-kurali --uygula' = kural 6 evde.
#
# NE ENJEKTE EDILMEZ: launcher/whitelist LISTESI (xargs/sudo/npx sinifi). Mimar hukmu
# (kayitli): sonsuz liste = yorumlayicinin argüman ayristiricisini taklit etmek; bu kapi
# bir DISIPLIN cihazidir, guvenlik siniri degil. Bu blok programlar kumesine TEK BIR AD
# EKLEMEZ; yalnizca zaten var olan SARMALAYICI kumesinin belirsizligini iki okumaya bolar.

CODEX_DAMGA = 'CODEX_KURAL_SURUMU = "27tem-2"'
CODEX_TANIM_BAS = "# === PRUVO CODEX KURALI BASLANGIC (mimar-kapi-kur.py enjekte etti) ==="
CODEX_TANIM_SON = "# === PRUVO CODEX KURALI BITIS ==="
CODEX_CAGRI_BAS = "        # === PRUVO CODEX CAGRI BASLANGIC (mimar-kapi-kur.py) ==="
CODEX_CAGRI_SON = "        # === PRUVO CODEX CAGRI BITIS ==="

# Enjeksiyon ANKRAJLARI + ev kapisinda BULUNMASI ZORUNLU semboller (fail-closed:
# biri eksikse O EVE DOKUNULMAZ — yarim enjeksiyon kapiyi coker, kapi cokerse
# PreToolUse fail-open davranir ve koruma SESSIZCE yok olur).
CODEX_ANKRAJ_TANIM = "\ndef main():\n"
CODEX_ANKRAJ_CAGRI = "        ad = os.path.basename(argv0)\n"
CODEX_ZORUNLU_SEMBOL = (
    "SARMALAYICI = ", "SURUM_BAYRAKLARI = ", "def parcala(", "def reddet(",
    "import os", "import re", CODEX_ANKRAJ_TANIM, CODEX_ANKRAJ_CAGRI,
)

CODEX_TANIM_SABLON = '''

''' + CODEX_TANIM_BAS + '''
# 26 TEM (BaBa hukmu): "codex exec cagirmak KENDI ELIYLE IS YAPMAK DEGIL, ISCI
# DAGITMAKTIR" — codex mimara SERBEST. KALAN TEK SART = KALITE KAPISI: sonuc bir
# DOSYAYA yazilsin ('-o' / '--output-last-message'), yani delegenin KABUL KAPISI
# kurulu olsun (skill: codex-isci). 27 TEM'de iki turda sikilastirildi:
#   argv0 DARALTMASI (yanlis-pozitif) · ALT-KOMUT fail-closed · BAYRAK DEGER sarti ·
#   gozlem simetrisi · esitlikli bicimde '-' oneki · SARMALAYICI ikinci okuma.
# PARSER TAKLIDI YASAK (memory/mimar-kapi-parser-taklidi.md): supheli form = RED.
CODEX_CIKTI_BAYRAKLARI = {"-o", "--output-last-message"}
CODEX_CIKTI_ONEKI = "--output-last-message="
# Gozlem bayraklari SURUM_BAYRAKLARI ile AYNI SINIF (tek kaynak — ayri liste tutmak
# '-V geciyor, -v gecmiyor' asimetrisini uretmisti).
CODEX_GOZLEM_BAYRAKLARI = SURUM_BAYRAKLARI
CODEX_IZINLI_ALTKOMUT = "exec"
''' + CODEX_DAMGA + '''
CODEX_GEREKCE_SONU = (
    " DOGRUSU: codex exec -C <bu ev> -s workspace-write "
    "-o /<scratchpad>/son-mesaj.txt \\"<spec>\\" — sonra dosyayi oku, sayiyla kapat. "
    "(skill: codex-isci)"
)


def _codex_isci_mi(girdi):
    """KIMLIK EKSENI (delegasyon muafiyetinin temeli): agent_id DOLU ise cagri ISCI'den
    gelir ve HICBIR kural uygulanmaz. Blok bunu KENDI ICINDE tasir — cunku ev kapilarinin
    bir kismi (BaBa evi) main() basinda kimlik muafiyeti TASIMIYOR; tasiyanlar icin bu
    kontrol zararsiz tekrardir, tasimayanlar icin ISCI'yi felc olmaktan kurtarir."""
    try:
        aid = girdi.get("agent_id")
    except Exception:
        return False
    return isinstance(aid, str) and bool(aid.strip())


def _codex_reddet(neden):
    """Ev kapisinin reddet() fonksiyonunu kullanir. Iki imza var: KraL'da
    reddet(neden, sonu=None), yol-bagimsiz sablonda reddet(neden). Arity OLCULUR
    (try/except TypeError degil — o, reddet ICINDEKI bir TypeError'i maskeleyip
    cift cikti basabilirdi)."""
    try:
        arity = reddet.__code__.co_argcount
    except Exception:
        arity = 1
    if arity >= 2:
        reddet(neden, sonu=CODEX_GEREKCE_SONU)
    reddet(neden + CODEX_GEREKCE_SONU)


def _codex_programi(argv0):
    """Segmentin CALISTIRILAN programi codex mi? YALNIZ argv0 (tam yol ise SON BILESENI).
    Genis token taramasi BILEREK yapilmaz: 'grep -rn codex', 'git commit -m codex',
    'git log --grep codex', 'ls .../Resources/codex' yanlis-pozitif uretiyordu."""
    return os.path.basename(argv0) == "codex"


def _codex_deger_gecerli(deger):
    """Cikti bayraginin DEGERI gecerli mi? IKI BICIMIN (ayrik / esitlikli) TEK KAYNAGI:
    (a) bos olmasin, (b) '-' ile BASLAMASIN ('-' ile baslayan sey deger degil, BASKA BIR
    BAYRAKtir → kabul kapisi bos kalir). Iki gövde tutmak bu asimetriyi tekrar uretir."""
    if not deger:
        return False
    if deger.startswith("-"):
        return False
    return True


def _codex_cikti_degerli(tokenlar):
    """Cikti bayragi bir DOSYA DEGERIYLE mi geliyor? (bayragin VARLIGI YETMEZ)
    ILK ESLESME KARARI VERIR: "bozuksa aramaya devam et" demek
    'codex exec --output-last-message -o /tmp/a.txt' dizisini ACIYORDU."""
    for i, t in enumerate(tokenlar):
        if t in CODEX_CIKTI_BAYRAKLARI:
            if i + 1 >= len(tokenlar):
                return False
            return _codex_deger_gecerli(tokenlar[i + 1])
        if t.startswith(CODEX_CIKTI_ONEKI):
            return _codex_deger_gecerli(t[len(CODEX_CIKTI_ONEKI):])
    return False


def _codex_karari(tokenlar):
    """None = kural uygulanmaz · "gecer" = izinli · str = red gerekcesi.
    Sira: (0) argv0 codex degil -> None · (1) ciplak 'codex' = TUI -> RED ·
    (2) kalan TUM tokenlar gozlem bayragi -> gecer · (3) alt-komut 'exec' DEGILSE RED
    (fail-closed: yeni alt-komut kendiliginden ACILMAZ) · (4) cikti bayragi + DEGER."""
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


def _sarmalayici_ikinci_okuma(tokenlar):
    """SARMALAYICI bayrak-DEGERI sizintisinin IKINCI OKUMASI.
    Olculen kusur: 'nice -n 10 codex exec "x"' ALLOW aliyordu — '10' (bayragin DEGERI)
    argv0 sanildigi icin kural HIC calismiyordu ('env -u FOO codex', 'stdbuf -o 0 codex'
    ayni sinif). Cozum PARSER TABLOSU DEGIL, dis_yol'un IKI OKUMA idiomu: bu okumada her
    atlanan bayragin ardindaki tiresiz token de o bayragin degeri olabilir sayilip
    atlanir; iki okumadan BIRINDE argv0 'codex' ise kural o okumaya uygulanir."""
    okuma = list(tokenlar)
    while okuma:
        if re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", okuma[0]):
            okuma = okuma[1:]
            continue
        if os.path.basename(okuma[0]) in SARMALAYICI:
            okuma = okuma[1:]
            while okuma and okuma[0].startswith("-"):
                okuma = okuma[1:]
                if okuma and not okuma[0].startswith("-"):
                    okuma = okuma[1:]
            continue
        break
    return okuma


def _codex_segment_karari(segment, tokenlar):
    """Segmentin codex KARARI, IKI OKUMA ile. Once normal okuma; YALNIZ o "kural
    uygulanmaz" derse ikinci okuma denenir → POZITIF kararlar degismez, sizinti kapanir."""
    karar = _codex_karari(tokenlar)
    if karar is None:
        ikinci = _sarmalayici_ikinci_okuma(parcala(segment))
        if ikinci != tokenlar:
            karar = _codex_karari(ikinci)
    return karar
''' + CODEX_TANIM_SON + '''
'''

CODEX_CAGRI_SABLON = (
    CODEX_CAGRI_BAS + "\n"
    "        codex_karari = _codex_segment_karari(segment, tokenlar)\n"
    '        if (codex_karari is not None and codex_karari != "gecer"\n'
    "                and not _codex_isci_mi(girdi)):\n"
    "            _codex_reddet(codex_karari)\n"
    + CODEX_CAGRI_SON + "\n"
)

# (mimar, ev koku, kapi dosyasi (ev-goreli), mod)
# 'kaynak' = kural commit'li dosyada yasar; bu arac YAZMAZ, yalnizca DOGRULAR.
# 'enjekte' = per-makine kopyaya marker'li blok enjekte edilir (commit YOK).
# KraL koku YOL-BAGIMSIZ turetilir (bu betigin bir ust dizini): boylece MUHENDIS DALINDA
# kosarken dalin kendi tools/ kopyasini, canli makinede canli tools/'u dogrular.
CODEX_KRAL_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CODEX_EVLER = (
    ("KraL", CODEX_KRAL_KOK, "tools/mimar-icra-kapisi.py", "kaynak"),
    ("MaCiT", "/Users/okan/dev/pruvo-hasat", ".claude/mimar-icra-kapisi.py", "enjekte"),
    ("KaaN", "/Users/okan/dev/pruvo-jenerator", ".claude/mimar-icra-kapisi.py", "enjekte"),
    ("ArTisT", "/Users/okan/dev/pruvo-pazarlama", ".claude/mimar-icra-kapisi.py", "enjekte"),
    ("HocA", "/Users/okan/dev/pruvo-bot", ".claude/mimar-icra-kapisi.py", "enjekte"),
    ("BaBa", "/Users/okan/dev/pruvo-advisor", ".claude/mimar-icra-kapisi.py", "enjekte"),
)

# Ev kabul testi (yol-bagimsiz sablon) fikstürleri: 26/27 Tem doktrini "codex serbest"
# degil "codex ciktisiz RED" der → o evdeki 'allow' beklentisi BAYAT kalir ve kurulumdan
# sonra evin kendi testi KIRMIZI yanar. Fikstürler de kural ile BIRLIKTE tasinir.
CODEX_TEST_ESKI = (
    '    (6, "allow", "ICRA", {"command": "codex exec \'x\'"}, None,\n'
    '     "codex = delegasyon araci, serbest"),\n'
)
CODEX_TEST_YENI = (
    "    # === PRUVO CODEX FIKSTURLERI BASLANGIC (mimar-kapi-kur.py) ===\n"
    '    (6, "deny", "ICRA", {"command": "codex exec \'x\'"}, None,\n'
    '     "26Tem: codex DELEGE serbest ama cikti dosyasi bayraksiz cagri RED"),\n'
    '    (8, "allow", "ICRA", {"command": "codex exec -o /tmp/son-mesaj.txt \'x\'"}, None,\n'
    '     "27Tem: \'-o <dosya>\' = codex-isci standardi -> GECER"),\n'
    '    (9, "deny", "ICRA", {"command": "codex exec --output-last-message=-o \'x\'"}, None,\n'
    '     "27Tem-2: \'=\' sonrasi deger BASKA BIR BAYRAK -> RED"),\n'
    '    (10, "deny", "ICRA", {"command": "nice -n 10 codex exec \'x\'"}, None,\n'
    '     "27Tem-2: sarmalayici bayrak-degeri sizintisi -> ikinci okuma RED"),\n'
    '    (11, "allow", "ICRA", {"command": "codex exec \'x\'"}, ISCI_ID,\n'
    '     "ISCI muaf: kalite kapisi YALNIZ mimara ait"),\n'
    '    (12, "allow", "ICRA", {"command": "codex --version"}, None,\n'
    '     "zararsiz gozlem cagrisi -> GECER"),\n'
    "    # === PRUVO CODEX FIKSTURLERI BITIS ===\n"
)

CODEX_YEDEK_DESEN = ".claude/*.yedek-*"


def _oku(yol):
    return io.open(yol, encoding="utf-8").read()


def _yaz(yol, metin):
    io.open(yol, "w", encoding="utf-8").write(metin)


def _blogu_sok(metin, bas, son):
    """Marker'lar arasindaki blogu (marker'lar dahil) SOKER. Yoksa metni aynen doner."""
    while True:
        i = metin.find(bas)
        if i < 0:
            return metin
        j = metin.find(son, i)
        if j < 0:
            return metin
        metin = metin[:i] + metin[j + len(son):]


def _git(kok, *args):
    try:
        return subprocess.run(["git", "-C", kok] + list(args),
                              capture_output=True, text=True)
    except Exception:
        return None


def _yedeklerimi_gizle(kok):
    """Yedek dosyalari kardes reponun 'git status'unu KIRLETMESIN → .git/info/exclude
    (per-makine, commit EDILMEZ). Doner: "eklendi" / "zaten" / "yok"."""
    yol = os.path.join(kok, ".git", "info", "exclude")
    if not os.path.isdir(os.path.dirname(yol)):
        return "yok"
    try:
        mevcut = _oku(yol) if os.path.exists(yol) else ""
    except Exception:
        return "yok"
    if CODEX_YEDEK_DESEN in mevcut:
        return "zaten"
    ek = mevcut
    if ek and not ek.endswith("\n"):
        ek += "\n"
    ek += "# mimar-kapi yedekleri (per-makine; commit YOK)\n" + CODEX_YEDEK_DESEN + "\n"
    try:
        _yaz(yol, ek)
    except Exception:
        return "yok"
    return "eklendi"


def _skip_worktree(kok, goreli):
    """Izlenen (H) kapi dosyasinin YEREL degisikligi git'e gorunmesin: index bayragi
    'skip-worktree'. Commit DEGILDIR, per-makine index durumudur; geri alma:
    git -C <ev> update-index --no-skip-worktree -- <dosya>.
    Doner: "kuruldu" / "zaten" / "izlenmiyor" / "hata"."""
    liste = _git(kok, "ls-files", "-v", "--", goreli)
    if liste is None or liste.returncode != 0:
        return "hata"
    satir = (liste.stdout or "").strip()
    if not satir:
        return "izlenmiyor"
    if satir[0] in ("S", "s"):
        return "zaten"
    sonuc = _git(kok, "update-index", "--skip-worktree", "--", goreli)
    if sonuc is None or sonuc.returncode != 0:
        return "hata"
    return "kuruldu"


def _kapi_fikstur(kapi_yolu, kok, komut, agent_id=None):
    """Kurulan kapiyi GERCEK PreToolUse payload'u ile kosturur (gercek 'codex' CAGRILMAZ —
    yalnizca kapi betigi kosar). Doner: allow/deny/COKTU/PARSE-HATASI."""
    payload = {
        "session_id": "kur-fikstur",
        "cwd": kok,
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": komut},
    }
    if agent_id is not None:
        payload["agent_id"] = agent_id
    ortam = dict(os.environ)
    ortam["CLAUDE_PROJECT_DIR"] = kok
    try:
        sonuc = subprocess.run([sys.executable, kapi_yolu], input=json.dumps(payload),
                               capture_output=True, text=True, env=ortam)
    except Exception:
        return "COKTU"
    if sonuc.returncode != 0:
        return "COKTU"
    cikti = (sonuc.stdout or "").strip()
    if not cikti:
        return "allow"
    try:
        veri = json.loads(cikti)
    except Exception:
        return "PARSE-HATASI"
    return ((veri.get("hookSpecificOutput") or {}).get("permissionDecision") or "allow")


def _test_dosyasi_guncelle(kok, uygula):
    """Evin kendi kabul testindeki BAYAT 'codex serbest' beklentisini doktrine hizalar.
    Doner: durum metni."""
    yol = os.path.join(kok, ".claude", "mimar-kapi-test.py")
    if not os.path.exists(yol):
        return "test-yok"
    try:
        metin = _oku(yol)
    except Exception:
        return "okunamadi"
    if "PRUVO CODEX FIKSTURLERI BASLANGIC" in metin:
        return "zaten"
    if CODEX_TEST_ESKI not in metin:
        return "ankraj-yok"
    if not uygula:
        return "GUNCELLENECEK"
    yeni = metin.replace(CODEX_TEST_ESKI, CODEX_TEST_YENI, 1)
    try:
        compile(yeni, yol, "exec")
    except SyntaxError:
        return "derlenmedi"
    shutil.copyfile(yol, yol + ".yedek-" + time.strftime("%Y%m%d-%H%M%S"))
    _yaz(yol, yeni)
    return "guncellendi"


def _eve_enjekte(ad, kok, goreli, uygula, rapor):
    """Tek eve kurali enjekte eder. Doner: (durum, yedek_yolu ya da None)."""
    yol = os.path.join(kok, goreli)
    if not os.path.exists(yol):
        return "KAPI-DOSYASI-YOK", None
    metin = _oku(yol)
    if CODEX_DAMGA in metin:
        return "ZATEN TAM", None

    eksik = [s for s in CODEX_ZORUNLU_SEMBOL if s not in metin]
    if eksik:
        rapor.append("      zorunlu sembol EKSIK: " + repr(eksik[0]))
        return "UYUMSUZ-KAPI (dokunulmadi)", None

    if not uygula:
        return "ENJEKTE EDILECEK", None

    yedek = yol + ".yedek-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(yol, yedek)

    # Eski damgali blok varsa SOK (kural yukseltmesi de tek hamle).
    temiz = _blogu_sok(metin, CODEX_TANIM_BAS, CODEX_TANIM_SON)
    temiz = _blogu_sok(temiz, CODEX_CAGRI_BAS, CODEX_CAGRI_SON)
    yeni = temiz.replace(CODEX_ANKRAJ_TANIM, CODEX_TANIM_SABLON + CODEX_ANKRAJ_TANIM, 1)
    yeni = yeni.replace(CODEX_ANKRAJ_CAGRI, CODEX_ANKRAJ_CAGRI + CODEX_CAGRI_SABLON, 1)
    _yaz(yol, yeni)

    def geri_al(neden):
        shutil.copyfile(yedek, yol)
        rapor.append("      GERI ALINDI (" + neden + ") — yedek: " + yedek)

    try:
        compile(yeni, yol, "exec")
    except SyntaxError as hata:
        geri_al("SyntaxError: " + str(hata)[:60])
        return "GERI ALINDI (derlenmedi)", yedek

    # CANLI FIKSTURLER — biri tutmazsa ev DERHAL geri alinir.
    olcumler = [
        ("codex exec \"x\"", None, "deny"),
        ("codex exec -o /tmp/son-mesaj.txt \"x\"", None, "allow"),
        ("nice -n 10 codex exec \"x\"", None, "deny"),
        ("codex exec --output-last-message=-o \"x\"", None, "deny"),
        ("ls", None, "allow"),
        ("git status", None, "allow"),
        ("codex exec \"x\"", "a4482c781a922b6a1", "allow"),
    ]
    for komut, aid, beklenen in olcumler:
        olculen = _kapi_fikstur(yol, kok, komut, aid)
        if olculen != beklenen:
            geri_al("fikstur '" + komut + "' beklenen=" + beklenen +
                    " olculen=" + str(olculen))
            return "GERI ALINDI (fikstur)", yedek

    rapor.append("      yedek: " + yedek)
    rapor.append("      info/exclude: " + _yedeklerimi_gizle(kok) +
                 " | skip-worktree: " + _skip_worktree(kok, goreli) +
                 " | ev testi: " + _test_dosyasi_guncelle(kok, uygula))
    return "KURULDU", yedek


def codex_kurali(uygula):
    """6 EVE codex kalite kapisini kurar/dogrular. Cikis 0 = 6 evin hepsi TAM."""
    print("CODEX KURALI DAMGASI: " + CODEX_DAMGA)
    print("MOD: " + ("UYGULA" if uygula else "KURU KOSUM (degisiklik yok)"))
    print("")
    eksik = 0
    for ad, kok, goreli, mod in CODEX_EVLER:
        rapor = []
        yol = os.path.join(kok, goreli)
        if not os.path.isdir(kok):
            durum_metni = "EV YOK"
        elif mod == "kaynak":
            # KraL: kural COMMIT'LI kaynakta yasar; bu arac commit'li kaynagi YAZMAZ.
            try:
                durum_metni = "ZATEN TAM" if CODEX_DAMGA in _oku(yol) else \
                    "EKSIK (kaynak dosya — elle/dal ile guncellenir, arac YAZMAZ)"
            except Exception:
                durum_metni = "KAPI-DOSYASI-YOK"
        else:
            durum_metni, _ = _eve_enjekte(ad, kok, goreli, uygula, rapor)
        if durum_metni != "ZATEN TAM" and not (uygula and durum_metni == "KURULDU"):
            eksik += 1
        print("{:<7} {:<34} {:<9} {}".format(ad, goreli, mod, durum_metni))
        for satir in rapor:
            print(satir)
    print("")
    print("TAM OLMAYAN EV: " + str(eksik))
    if not uygula:
        print("Kuru kosum. Uygulamak icin ayni komuta --uygula ekle.")
    print("Dogrula: python3 /Users/okan/dev/pruvo/tools/mimar-kapi-6ev-test.py")
    sys.exit(0 if eksik == 0 else 1)


# ===================== 28 TEM: AGENT-KAPISI 6 EVE (BaBa/Senyor Advisor hukmu) =====================
# Kural METNI burada da YASAR (codex kuralindaki desenin AYNISI): mimar ANA oturumu bir
# Claude iscisi (Agent/Task) acarken prompt'ta 'codex-muafiyet: <is> — <sinif>' beyani sart.
# KraL 'kaynak' modundadir (kural commit'li tools/mimar-icra-kapisi.py'de; bu arac orayi
# YAZMAZ, yalnizca DOGRULAR); diger 5 ev 'enjekte' modundadir (per-makine kopyaya blok
# enjekte + settings Agent|Task kablosu, commit YOK). Desen: DAR + IDEMPOTENT + YEDEKLI +
# FAIL-CLOSED (zorunlu sembol/anksraj eksikse O EVE DOKUNULMAZ; enjeksiyon sonrasi compile +
# CANLI FIKSTUR, biri tutmazsa ev DERHAL YEDEKTEN geri alinir — tek-ev FP tum evi durdurmaz).
AGENT_DAMGA = 'AGENT_KURAL_SURUMU = "13agu-2"'
AGENT_TANIM_BAS = "# === PRUVO AGENT-KAPISI BASLANGIC (mimar-kapi-kur.py enjekte etti) ==="
AGENT_TANIM_SON = "# === PRUVO AGENT-KAPISI BITIS ==="
AGENT_CAGRI_BAS = "    # === PRUVO AGENT-KAPISI CAGRI BASLANGIC (mimar-kapi-kur.py) ==="
AGENT_CAGRI_SON = "    # === PRUVO AGENT-KAPISI CAGRI BITIS ==="
# Enjeksiyon ANKRAJLARI (6 evde de var oldugu OLCULDU — tools/inspect ile) + bulunmasi
# ZORUNLU semboller (fail-closed: biri eksikse ev ATLANIR, yarim enjeksiyon kapiyi cokertir).
AGENT_ANKRAJ_TANIM = "\ndef main():\n"
AGENT_ANKRAJ_CAGRI = '    komut = (girdi.get("tool_input") or {}).get("command") or ""\n'
AGENT_ZORUNLU_SEMBOL = (
    "def reddet(", "import os", "import re",
    AGENT_ANKRAJ_TANIM, AGENT_ANKRAJ_CAGRI,
)

AGENT_TANIM_SABLON = '''

''' + AGENT_TANIM_BAS + '''
# 28 TEM (BaBa/Senyor Advisor hukmu): mimar bir Claude iscisi (Agent/Task) acmak da
# dogrudan 'codex exec' kadar TEK SATIR surtunme tasimali. Mimar ANA oturumu (agent_id
# BOS) Agent/Task acarken prompt'ta 'codex-muafiyet: <is> — <sinif>' beyani YOKSA RED.
# ISCI (agent_id dolu) TAM muaf. Agent/Task DISINDA hicbir arac etkilenmez. PARSER TAKLIDI
# YASAK: tek makine-aranabilir regex (AGENT_MUAFIYET_RE); supheli form = RED (fail-closed).
AGENT_ARACLARI = {"Agent", "Task"}
SERT_BLOK_EVLER = ("pruvo", "pruvo-hasat")
EV_ADI = os.path.basename(os.path.normpath(
    globals().get("REPO_ONEKI") or REPO_ONEKLERI[0]))
AGENT_SINIFLARI = (
    "görsel", "gorsel",
    "sessiz-hata",
    "muhakeme",
    "ölçüm", "olcum",
    "güvenlik", "guvenlik",
    "şema", "sema",
)
AGENT_MUAFIYET_RE = re.compile(
    r"codex-muafiyet:[^\\S\\n]*\\S[^\\n]*?[—–-][^\\S\\n]*(?:" +
    "|".join(re.escape(_s) for _s in AGENT_SINIFLARI) + r")(?![\\w-])",
    re.IGNORECASE,
)
''' + AGENT_DAMGA + '''
AGENT_SINIF_LISTESI = " / ".join(AGENT_SINIFLARI)
AGENT_ORNEK_SINIF = AGENT_SINIFLARI[0]
AGENT_GEREKCE = (
    "AGENT-KAPISI (28 Tem): mimar ANA oturumu bir Claude iscisi (Agent/Task) aciyor ama "
    "prompt/spec icinde 'codex-muafiyet:' BEYAN SATIRI YOK. IKI CIKIS: (a) ISI CODEX'E VER "
    "-> codex-isci sablonu (codex exec -C <ev> -s workspace-write -o <scratchpad>/son-mesaj.txt "
    "\\"<spec>\\"); VEYA (b) prompt'a su satiri EKLE: "
    "'codex-muafiyet: <is tanimi> — {ornek}' (gecerli sinif jetonlari: {liste} — "
    "codex-isci yasak listesi)."
).format(ornek=AGENT_ORNEK_SINIF, liste=AGENT_SINIF_LISTESI)


def _sert_blok_gerekcesi():
    _sarmalayici = globals().get(
        "ISCI_SARMALAYICI_YOLU", os.path.expanduser("~/.claude/cron/isci.sh"))
    # 19 AGU (K214): varsayilanlar da TURETILIR. Eskiden burada ikinci bir GOMULU liste
    # dururdu (kimi YOK, emekli deepseek VAR) — ISCI blogu henuz enjekte edilmemis bir
    # evde AGENT-KAPISI'nin sert-blok metni o donmus listeyi mimara ONERIYORDU.
    _motorlar = globals().get("ISCI_MOTORLARI", ()) or ''' + repr(ISCI_MOTORLARI) + '''
    _canli = globals().get("CANLI_ISCI_MOTORLARI", ()) or ''' + repr(CANLI_ISCI_MOTORLARI) + '''
    _motor_listesi = " / ".join(_motorlar)
    return (
        "AGENT-KAPISI (13 Agu Okan emri): bu evde mimar ANA oturumunun Claude iscisi "
        "(Agent/Task ve isci.sh claude) acmasi, 'codex-muafiyet:' beyani bulunsa bile "
        "YASAKTIR. 'claude' motoru da ayni yasagin kapsamindadir; pahali kat pahali kattir. "
        "PRUVO_CLAUDE_ISCI_IZNI yalnizca tam olarak OKAN ise eski beyan kurali calisir; "
        "bu izni yalnizca Okan verir ve ajan kendi ayarlayamaz. IKI ACIK YOL: (a) " +
        _sarmalayici + " <motor> <EV_KOKU> <SPEC_DOSYASI> [ETIKET] "
        "(ucuz motorlar: " + " / ".join(_canli) +
        "; kapali motor kumesi: " + _motor_listesi + "); (b) codex exec -C <ev> "
        "-s workspace-write -o <dosya> \\\"<spec>\\\"."
    )


def _agent_gorulen_sinif(prompt):
    """Beyan satirindaki ayrac-sonrasi ilk jetonu yalniz red tanisi icin ayiklar."""
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


def _agent_isci_mi(girdi):
    try:
        aid = girdi.get("agent_id")
    except Exception:
        return False
    return isinstance(aid, str) and bool(aid.strip())


def _agent_reddet(neden):
    try:
        arity = reddet.__code__.co_argcount
    except Exception:
        arity = 1
    if arity >= 2:
        reddet(neden, sonu="")
    reddet(neden)


def _agent_karari(girdi):
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
''' + AGENT_TANIM_SON + '''
'''

AGENT_CAGRI_SABLON = (
    AGENT_CAGRI_BAS + "\n"
    '    _agent_tool = girdi.get("tool_name") or ""\n'
    "    if _agent_tool in AGENT_ARACLARI and not _agent_isci_mi(girdi):\n"
    "        _ag_karar = _agent_karari(girdi)\n"
    '        if _ag_karar != "gecer":\n'
    "            _agent_reddet(_ag_karar)\n"
    + AGENT_CAGRI_SON + "\n"
)

AGENT_ISCI_ID = "a4482c781a922b6a1"  # canli olculmus bir alt-ajan agent_id bicimi


def _agent_fikstur(kapi_yolu, kok, tool_name, tool_input, agent_id=None, ek_env=None):
    """Kurulan kapiyi GERCEK PreToolUse payload'u ile kosturur (gercek arac CAGRILMAZ —
    yalnizca kapi betigi kosar). Doner: allow/deny/COKTU/PARSE-HATASI."""
    payload = {
        "session_id": "agent-kur-fikstur",
        "cwd": kok,
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    if agent_id is not None:
        payload["agent_id"] = agent_id
    ortam = dict(os.environ)
    ortam["CLAUDE_PROJECT_DIR"] = kok
    ortam.pop("PRUVO_ISCI_KOSUMU", None)
    ortam.update(ek_env or {})
    try:
        sonuc = subprocess.run([sys.executable, kapi_yolu], input=json.dumps(payload),
                               capture_output=True, text=True, env=ortam)
    except Exception:
        return "COKTU"
    if sonuc.returncode != 0:
        return "COKTU"
    cikti = (sonuc.stdout or "").strip()
    if not cikti:
        return "allow"
    try:
        veri = json.loads(cikti)
    except Exception:
        return "PARSE-HATASI"
    return ((veri.get("hookSpecificOutput") or {}).get("permissionDecision") or "allow")


def _agent_ev_settings(kok, uygula):
    """Evin .claude/settings.json'una Agent|Task matcher blogunu ekler. Komutu BASH
    blogundaki mimar-icra-kapisi.py hook'undan KOPYALAR (yol per-ev dogru olur). Additive +
    idempotent + yedekli. Doner: durum metni (settings-yok/PreToolUse-yok/bash-icra-yok/
    zaten/EKLENECEK/kuruldu/yazim-bozuk)."""
    yol = os.path.join(kok, ".claude", "settings.json")
    if not os.path.exists(yol):
        return "settings-yok"
    try:
        veri = json.loads(_oku(yol))
    except Exception:
        return "settings-bozuk"
    kancalar = (veri.get("hooks") or {}).get("PreToolUse")
    if not isinstance(kancalar, list):
        return "PreToolUse-yok"
    komut = None
    for blok in kancalar:
        if blok.get("matcher") == "Bash":
            for k in (blok.get("hooks") or []):
                if "mimar-icra-kapisi.py" in (k.get("command") or ""):
                    komut = k.get("command")
                    break
    if not komut:
        return "bash-icra-yok"
    agent_blok = None
    for blok in kancalar:
        if blok.get("matcher") == AGENT_MATCHER:
            agent_blok = blok
            break
    if agent_blok is not None and any(
            "mimar-icra-kapisi.py" in (k.get("command") or "")
            for k in (agent_blok.get("hooks") or [])):
        return "zaten"
    if not uygula:
        return "EKLENECEK"
    shutil.copyfile(yol, yol + ".yedek-" + time.strftime("%Y%m%d-%H%M%S"))
    if agent_blok is None:
        agent_blok = {"matcher": AGENT_MATCHER, "hooks": []}
        kancalar.append(agent_blok)
    agent_blok.setdefault("hooks", []).append(
        {"type": "command", "command": komut, "timeout": 30,
         "statusMessage": "mimar agent kapisi"})
    _yaz(yol, json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
    try:
        json.loads(_oku(yol))
    except Exception:
        return "yazim-bozuk"
    return "kuruldu"


def _eve_agent_enjekte(ad, kok, goreli, uygula, rapor):
    """Tek eve AGENT-KAPISI kuralini enjekte eder (+ settings Agent|Task kablosu).
    Codex enjeksiyonuyla AYNI desen. Doner: (durum, yedek_yolu ya da None)."""
    yol = os.path.join(kok, goreli)
    if not os.path.exists(yol):
        return "KAPI-DOSYASI-YOK", None
    metin = _oku(yol)
    if AGENT_DAMGA in metin:
        return "ZATEN TAM", None

    eksik = [s for s in AGENT_ZORUNLU_SEMBOL if s not in metin]
    if eksik:
        rapor.append("      zorunlu sembol EKSIK: " + repr(eksik[0]))
        return "UYUMSUZ-KAPI (dokunulmadi)", None

    if not uygula:
        return "ENJEKTE EDILECEK", None

    yedek = yol + ".yedek-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(yol, yedek)

    # Eski damgali blok varsa SOK (kural yukseltmesi de tek hamle).
    temiz = _blogu_sok(metin, AGENT_TANIM_BAS, AGENT_TANIM_SON)
    temiz = _blogu_sok(temiz, AGENT_CAGRI_BAS, AGENT_CAGRI_SON)
    # ISCI blogu Agent sembollerini import aninda kullanir; surum yukseltmesinde yeni
    # Agent tanimi mevcut ISCI taniminin ONUNDE kalmalidir.
    if ISCI_TANIM_BAS in temiz:
        yeni = temiz.replace(ISCI_TANIM_BAS, AGENT_TANIM_SABLON + "\n" + ISCI_TANIM_BAS, 1)
    else:
        yeni = temiz.replace(AGENT_ANKRAJ_TANIM,
                            AGENT_TANIM_SABLON + AGENT_ANKRAJ_TANIM, 1)
    yeni = yeni.replace(AGENT_ANKRAJ_CAGRI, AGENT_CAGRI_SABLON + AGENT_ANKRAJ_CAGRI, 1)
    _yaz(yol, yeni)

    def geri_al(neden):
        shutil.copyfile(yedek, yol)
        rapor.append("      GERI ALINDI (" + neden + ") — yedek: " + yedek)

    try:
        compile(yeni, yol, "exec")
    except SyntaxError as hata:
        geri_al("SyntaxError: " + str(hata)[:60])
        return "GERI ALINDI (derlenmedi)", yedek

    # CANLI FIKSTURLER — AGENT gate + regresyon (rutin/codex) birlikte; biri tutmazsa geri al.
    beyanli_beklenen = "deny" if ad in ("KraL", "MaCiT") else "allow"
    olcumler = [
        ("Agent", {"prompt": "beyansiz mimar spec"}, None, "deny"),
        ("Agent", {"prompt": "codex-muafiyet: parti dilimi tarama — olcum"}, None,
         beyanli_beklenen),
        ("Agent", {"prompt": "codex-muafiyet: parti dilimi tarama — ölçüm"}, None,
         beyanli_beklenen),
        ("Agent", {"prompt": "codex-muafiyet: parti dilimi tarama — gizlilik"}, None, "deny"),
        ("Agent", {"prompt": "is X\ncodex-muafiyet: kapi kodu — sessiz-hata"}, None,
         beyanli_beklenen),
        ("Task", {"prompt": "beyansiz"}, None, "deny"),
        ("Agent", {"prompt": "beyansiz"}, AGENT_ISCI_ID, "allow"),
        ("Bash", {"command": "ls"}, None, "allow"),
        ("Bash", {"command": 'codex exec "x"'}, None, "deny"),
    ]
    for tn, ti, aid, beklenen in olcumler:
        olculen = _agent_fikstur(yol, kok, tn, ti, aid)
        if olculen != beklenen:
            geri_al("fikstur tn=" + tn + " beklenen=" + beklenen + " olculen=" + str(olculen))
            return "GERI ALINDI (fikstur)", yedek

    rapor.append("      yedek: " + yedek)
    rapor.append("      info/exclude: " + _yedeklerimi_gizle(kok) +
                 " | skip-worktree: " + _skip_worktree(kok, goreli) +
                 " | settings Agent|Task: " + _agent_ev_settings(kok, uygula))
    return "KURULDU", yedek


def agent_kapisi(uygula):
    """6 EVE AGENT-KAPISI kurar/dogrular. Cikis 0 = 6 evin hepsi TAM. KraL 'kaynak' modda
    yalnizca DOGRULANIR (kural commit'li kaynakta; arac YAZMAZ). KraL settings Agent|Task
    kablosu ANA AKISTA (python3 mimar-kapi-kur.py --uygula) kurulur, burada DEGIL."""
    print("AGENT-KAPISI DAMGASI: " + AGENT_DAMGA)
    print("MOD: " + ("UYGULA" if uygula else "KURU KOSUM (degisiklik yok)"))
    print("")
    eksik = 0
    for ad, kok, goreli, mod in CODEX_EVLER:
        rapor = []
        yol = os.path.join(kok, goreli)
        if not os.path.isdir(kok):
            durum_metni = "EV YOK"
        elif mod == "kaynak":
            try:
                durum_metni = "ZATEN TAM" if AGENT_DAMGA in _oku(yol) else \
                    "EKSIK (kaynak dosya — elle/dal ile guncellenir, arac YAZMAZ)"
            except Exception:
                durum_metni = "KAPI-DOSYASI-YOK"
        else:
            durum_metni, _ = _eve_agent_enjekte(ad, kok, goreli, uygula, rapor)
        if durum_metni != "ZATEN TAM" and not (uygula and durum_metni == "KURULDU"):
            eksik += 1
        print("{:<7} {:<34} {:<9} {}".format(ad, goreli, mod, durum_metni))
        for satir in rapor:
            print(satir)
    print("")
    print("TAM OLMAYAN EV: " + str(eksik))
    if not uygula:
        print("Kuru kosum. Uygulamak icin ayni komuta --uygula ekle.")
    print("Dogrula: python3 /Users/okan/dev/pruvo/tools/agent-kapisi-test.py")
    sys.exit(0 if eksik == 0 else 1)


# ===================== 8 AGU: MCP-TARAYICI KAPISI 6 EVE (Okan teftisi K17) =====================
# OLCULEN DELIK: 6 evin settings.json PreToolUse matcher'lari yalnizca Bash / Write-Edit /
# Agent|Task tutuyordu; uc MCP tarayici sunucusunun arac adlari HICBIR kapidan gecmiyordu.
# Bu mod o kolu 6 EVE kurar. Desen CODEX/AGENT modlariyla AYNI: DAR + IDEMPOTENT + YEDEKLI +
# FAIL-CLOSED (zorunlu sembol/ankraj eksikse O EVE DOKUNULMAZ; enjeksiyon sonrasi compile +
# CANLI FIKSTUR, biri tutmazsa ev DERHAL YEDEKTEN geri alinir).
#
# 🔴 YOL FARKI OLCULUR, VARSAYILMAZ (Okan uyarisi): KraL evinde kapi '.claude/' altinda
# DEGIL, 'tools/mimar-icra-kapisi.py'dedir; 5 kardes evde '.claude/mimar-icra-kapisi.py'.
# Yanlis yola yazmak "kuruldu" der ama HICBIR SEYI kilitlemez. Bu yuzden kablonun komutu
# _kapi_yolu_olc() ile IKI KAYNAKTAN olculur (evin settings.json'undaki mevcut kanca komutu
# + diskteki aday yollar); ikisi de bos donerse ev FAIL-CLOSED atlanir.
#
# 🔴 KIMLIK TESPITI YENIDEN KULLANILIR: enjekte edilen blok kendi 'isci mi' testini
# YAZMAZ, AGENT-KAPISI'nin _agent_isci_mi()'sini cagirir — bu yuzden AGENT_DAMGA bir
# ZORUNLU SEMBOLDUR (yoksa eve dokunulmaz). Ikiz tanim sessizce ayrisir.
MCP_DAMGA = 'MCP_KURAL_SURUMU = "20agu-2"'
MCP_TANIM_BAS = "# === PRUVO MCP-TARAYICI KAPISI BASLANGIC (mimar-kapi-kur.py enjekte etti) ==="
MCP_TANIM_SON = "# === PRUVO MCP-TARAYICI KAPISI BITIS ==="
MCP_CAGRI_BAS = "    # === PRUVO MCP-TARAYICI CAGRI BASLANGIC (mimar-kapi-kur.py) ==="
MCP_CAGRI_SON = "    # === PRUVO MCP-TARAYICI CAGRI BITIS ==="
MCP_ANKRAJ_TANIM = "\ndef main():\n"
MCP_ANKRAJ_CAGRI = '    komut = (girdi.get("tool_input") or {}).get("command") or ""\n'
# AGENT_DAMGA ZORUNLUDUR: blok _agent_isci_mi()'yi CAGIRIR (ikinci tespit yazilmaz).
# 20 AGU: 'EV_ADI = ' de ZORUNLU — tarayici ekseni EV BAZLI oldu ve ev adini AGENT
# blogundan OKUR (ikiz tanim yazmaz). AGENT blogu kurulmamis eve DOKUNULMAZ (fail-closed):
# EV_ADI yoksa _tarayici_ekseni_acik_mi() NameError'a duser ve kapi cokerdi.
MCP_ZORUNLU_SEMBOL = (
    "def reddet(", "import os", "def _agent_isci_mi(", AGENT_DAMGA, "EV_ADI = ",
    MCP_ANKRAJ_TANIM, MCP_ANKRAJ_CAGRI,
)

# settings.json matcher'i: uc sunucu oneki. Hem 'search' hem 'fullmatch' anlambiliminde
# calisir (onek + '.*'), boylece harness'in matcher semantigi TAKLIT EDILMEZ. Kapsam
# disi adlar (mcp__visualize__*, mcp__Blender__*) bu desene UGRAMAZ; nihai karar zaten
# kapi betigindedir (matcher genis olsa bile betik dar davranir).
MCP_MATCHER = "mcp__(claude-in-chrome|Claude_Browser|Control_Chrome)__.*"

MCP_TANIM_SABLON = '''

''' + MCP_TANIM_BAS + '''
# 8 AGU (Okan teftisi K17): mimar ANA oturumunda tarayici icrasi KAPALI; ISCI'de SERBEST.
# Her tur ekran goruntusu tasir, goruntu en pahali token sinifidir (olculen vaka: 1 saatte
# baglamin %58'i). KAPSAM DAR: yalniz asagidaki UC SUNUCU oneki — mcp__visualize__*,
# mcp__Blender__*, mcp__ccd_session__* vb. DOKUNULMAZ (yanlis-pozitif = yayin durduran
# sinif). PARSER TAKLIDI YOK: tek soru "ad bu uc onekten biriyle BASLIYOR mu".
MCP_TARAYICI_ONEKLERI = (
    "mcp__claude-in-chrome__",
    "mcp__Claude_Browser__",
    "mcp__Control_Chrome__",
)
''' + MCP_DAMGA + '''

# 🔴 20 AGU (Okan emri: "KraL ve MaCiT evlerinde tarayiciyi ac — ikinizi de ac"):
# TARAYICI EKSENI ARTIK EV BAZLI. Bu iki evde ana oturum tarayiciyi KENDI SURER;
# kalan dort evde 8 Agu kurali AYNEN durur.
#
# 🔴🔴 IKI EKSEN AYRIDIR VE AYRI KALIR — BIRLESTIRME YASAK:
#   · SERT_BLOK_EVLER (AGENT blogu) -> CLAUDE ISCISI / Agent-Task yasagi (13 Agu Okan
#     emri; tek kacis PRUVO_CLAUDE_ISCI_IZNI=OKAN). Okuyanlar: _agent_karari + _isci_karari.
#   · TARAYICI_ACIK_EVLER (burasi)  -> MCP tarayici araclarinin ANA OTURUMDA serbestligi.
# Iki kume BUGUN AYNI IKI EVI sayiyor ama ZIT hukum tasiyor: ayni evde tarayici ACIK,
# Claude iscisi KAPALI. "Ayni liste, sadelestirelim" DAVRANIS DEGISTIREN bir hatadir;
# kumeyi bosaltmak/silmek/otekiyle degistirmek ikinci yasagi SESSIZCE acar ve hicbir
# yesil test gostermez (memory/ad-iki-rolde-mutanti-golgeler.md, K229 M6/M7).
#
# FAIL-CLOSED taraf BILEREK secildi: liste ACIK evleri sayar, kapali evleri DEGIL.
# Tanimadik/yeni bir ev adi -> tarayici KAPALI (yeni ev sessizce acilmaz).
TARAYICI_ACIK_EVLER = ("pruvo", "pruvo-hasat")

# ACIK EVDE KURAL VAR, BLOK YOK — maliyet disiplini mimarin uydugu KURALDIR.
TARAYICI_MALIYET_KURALI = (
    "TARAYICI MALIYET DISIPLINI (20 Agu): once METIN — `get_page_content` / `read_page`. "
    "Ekran goruntusu YALNIZCA aranan rakam metinden okunamiyorsa ve TEK KARE. Goruntu en "
    "pahali token sinifidir (olculen vaka: 1 saatte baglamin %58'i)."
)
MCP_GEREKCE = (
    "MCP-TARAYICI KAPISI (8 Agu · 20 Agu ev bazli): mimar ANA oturumu bir tarayici araci "
    "cagiriyor ve BU EV tarayiciya acik evler arasinda DEGIL (acik evler: " +
    " / ".join(TARAYICI_ACIK_EVLER) + "). Bu evde ana dongude tarayici surmek KAPALI — her "
    "tur ekran goruntusu tasir ve goruntu EN PAHALI token sinifidir (olculen vaka: 1 "
    "saatte baglamin %58'i). COZUM: TARAYICIYI GORSEL-SINIF CLAUDE ISCISINE VER — Codex'e "
    "VERILMEZ (gorsel = codex-isci yasak listesi). ISCI SABLONU (Agent araci: model sonnet "
    "+ isolation worktree + background), prompt'un ilk satiri: 'codex-muafiyet: tarayici "
    "ile <ne olculecek> — gorsel'; spec'e CALISTIRILABILIR kabul yaz (hangi URL'de hangi "
    "sayi olculecek), isci olcsun, sen SAYIYLA kapat. Isci cagrilarinda (agent_id dolu) bu "
    "kapi hicbir kural uygulamaz. " + TARAYICI_MALIYET_KURALI
)


def _tarayici_ekseni_acik_mi():
    """Bu EVDE ana oturumun tarayici surmesi serbest mi? (20 Agu Okan emri)

    🔴 SERT_BLOK_EVLER'e BAKMAZ ve BAKMAYACAK. EV_ADI AGENT blogundan gelir (ikiz tanim
    yazilmaz; AGENT_DAMGA + 'EV_ADI = ' bu blogun ZORUNLU sembolleridir)."""
    return EV_ADI in TARAYICI_ACIK_EVLER


def _mcp_tarayici_mi(tool_name):
    """Arac adi KAPSAMDAKI uc tarayici sunucusundan birine mi ait? Buyuk/kucuk DUYARSIZ
    onek testi; kapsam disi hicbir 'mcp__...' araci etkilenmez."""
    if not isinstance(tool_name, str) or not tool_name:
        return False
    _ad = tool_name.lower()
    for _onek in MCP_TARAYICI_ONEKLERI:
        if _ad.startswith(_onek.lower()):
            return True
    return False


def _mcp_reddet(neden):
    """Ev kapisinin reddet() fonksiyonunu kullanir. Iki imza var: KraL'da
    reddet(neden, sonu=None), yol-bagimsiz sablonda reddet(neden). Arity OLCULUR."""
    try:
        arity = reddet.__code__.co_argcount
    except Exception:
        arity = 1
    if arity >= 2:
        reddet(neden, sonu="")
    reddet(neden)
''' + MCP_TANIM_SON + '''
'''

# 🔴 KIMLIK: _agent_isci_mi() — AGENT-KAPISI'nin TESPITI YENIDEN KULLANILIR.
MCP_CAGRI_SABLON = (
    MCP_CAGRI_BAS + "\n"
    '    _mcp_tool = girdi.get("tool_name") or ""\n'
    "    if (_mcp_tarayici_mi(_mcp_tool) and not _agent_isci_mi(girdi)\n"
    "            and not _tarayici_ekseni_acik_mi()):\n"
    "        _mcp_reddet(MCP_GEREKCE)\n"
    + MCP_CAGRI_SON + "\n"
)

# Kapi dosyasinin ev-goreli aday yollari (OLCULUR, varsayilmaz).
MCP_KAPI_ADAYLARI = ("tools/mimar-icra-kapisi.py", ".claude/mimar-icra-kapisi.py")


def _settingsten_kapi_komutu(kok):
    """Evin settings.json'undaki HERHANGI bir PreToolUse kancasindan mimar-icra-kapisi.py
    komutunu ayikla (yoksa None). BIRINCI KAYNAK: canli kablo ne diyorsa o."""
    yol = os.path.join(kok, ".claude", "settings.json")
    if not os.path.exists(yol):
        return None
    try:
        veri = json.loads(_oku(yol))
    except Exception:
        return None
    for blok in ((veri.get("hooks") or {}).get("PreToolUse") or []):
        for k in (blok.get("hooks") or []):
            komut = k.get("command") or ""
            if "mimar-icra-kapisi.py" in komut:
                return komut
    return None


def _kapi_yolu_olc(kok):
    """Evdeki kapinin GERCEK ev-goreli yolunu OLCER (sabit varsayilmaz).

    IKI KAYNAK, fail-closed birlesim:
      (1) DISK — MCP_KAPI_ADAYLARI'ndan diskte VAR olan(lar).
      (2) KABLO — settings.json'daki mevcut kanca komutunda gecen aday.
    Karar diskte VAR olan adaydir; birden fazla varsa kablonun gosterdigi tercih edilir
    (kablo da sessizse ilk aday). Hicbiri diskte yoksa (None, komut) doner ve cagiran
    evi ATLAR — yanlis yola yazmak 'kuruldu' der ama hicbir seyi kilitlemez."""
    komut = _settingsten_kapi_komutu(kok)
    diskte = [a for a in MCP_KAPI_ADAYLARI if os.path.exists(os.path.join(kok, a))]
    if not diskte:
        return None, komut
    if komut:
        for aday in diskte:
            if aday in komut:
                return aday, komut
    return diskte[0], komut


def _mcp_ev_settings(kok, goreli, uygula):
    """Evin .claude/settings.json'una MCP_MATCHER blogunu ekler. Komut, OLCULEN kapi
    yolundan turetilir (evin mevcut kanca komutu varsa AYNEN o kullanilir — bicim/degisken
    kullanimi evden eve farkli olabilir). Additive + idempotent + yedekli."""
    yol = os.path.join(kok, ".claude", "settings.json")
    if not os.path.exists(yol):
        return "settings-yok"
    try:
        veri = json.loads(_oku(yol))
    except Exception:
        return "settings-bozuk"
    mevcut_komut = _settingsten_kapi_komutu(kok)
    if mevcut_komut and goreli in mevcut_komut:
        komut = mevcut_komut
    else:
        komut = 'python3 "${CLAUDE_PROJECT_DIR:-.}/' + goreli + '"'
    kancalar = veri.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if not isinstance(kancalar, list):
        return "PreToolUse-bozuk"
    mcp_blok = None
    for blok in kancalar:
        if blok.get("matcher") == MCP_MATCHER:
            mcp_blok = blok
            break
    if mcp_blok is not None and any(
            "mimar-icra-kapisi.py" in (k.get("command") or "")
            for k in (mcp_blok.get("hooks") or [])):
        return "zaten"
    if not uygula:
        return "EKLENECEK"
    shutil.copyfile(yol, yol + ".yedek-" + time.strftime("%Y%m%d-%H%M%S"))
    if mcp_blok is None:
        mcp_blok = {"matcher": MCP_MATCHER, "hooks": []}
        kancalar.append(mcp_blok)
    mcp_blok.setdefault("hooks", []).append(
        {"type": "command", "command": komut, "timeout": 30,
         "statusMessage": "mimar mcp tarayici kapisi"})
    _yaz(yol, json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
    try:
        json.loads(_oku(yol))
    except Exception:
        return "yazim-bozuk"
    return "kuruldu"


# Enjeksiyon sonrasi CANLI FIKSTURLER: (tool_name, tool_input, agent_id, beklenen).
# UC EKSEN BIRDEN: (a) ana-oturum TARAYICI HUKMU (20 Agu: EV BAZLI), (b) ISCI GECER,
# (c) KAPSAM DISI yanlis-pozitif YOK, + (d) REGRESYON (codex/agent/rutin kollari
# degismedi). Biri tutmazsa ev geri alinir.
#
# 🔴 20 AGU: ilk uc vakanin beklentisi ARTIK EVE BAGLI — sabit "deny" YAZILMAZ, sentinel
# ile isaretlenir ve _eve_mcp_enjekte icinde ev adindan TURETILIR. Sabit yazsaydik acik
# evlerde (KraL/MaCiT) enjeksiyon her seferinde "fikstur tutmadi" deyip evi GERI ALIRDI —
# yani kural kurulmus gibi gorunup hicbir eve inmezdi.
#
# 🔴 SON IKI VAKA = NEGATIF KONTROL (eksen ayriminin CANLI kaniti): ayni evde tarayici
# ACILIRKEN Claude iscisi (Agent) yasagi AYNEN durmali. Beklentileri TERS yonde ev bazli
# (tarayici: acik evde allow · Agent beyanli: acik evde deny) — iki eksen tek kumeye
# indirgenirse bu ikili AYNI anda yesil kalamaz.
MCP_TARAYICI_BEKLENTI = "<TARAYICI-EV-BAZLI>"
# Tarayici ekseninde ACIK evlerin ADLARI (CODEX_EVLER'deki ad alani). Bu liste enjekte
# edilen TARAYICI_ACIK_EVLER kumesinin DIZIN adlariyla ayni evleri gostermelidir.
MCP_TARAYICI_ACIK_EV_ADLARI = ("KraL", "MaCiT")
MCP_FIKSTURLERI = (
    ("mcp__claude-in-chrome__computer", {}, None, MCP_TARAYICI_BEKLENTI),
    ("mcp__Claude_Browser__computer", {}, None, MCP_TARAYICI_BEKLENTI),
    ("mcp__Control_Chrome__open_url", {}, None, MCP_TARAYICI_BEKLENTI),
    ("mcp__claude-in-chrome__computer", {}, AGENT_ISCI_ID, "allow"),
    ("mcp__Claude_Browser__computer", {}, AGENT_ISCI_ID, "allow"),
    ("mcp__Control_Chrome__open_url", {}, AGENT_ISCI_ID, "allow"),
    ("mcp__visualize__show_widget", {}, None, "allow"),
    ("mcp__Blender__get_objects_summary", {}, None, "allow"),
    ("mcp__ccd_session__mark_chapter", {}, None, "allow"),
    ("Bash", {"command": "ls"}, None, "allow"),
    ("Bash", {"command": 'codex exec "x"'}, None, "deny"),
    ("Bash", {"command": "codex exec -o /tmp/son-mesaj.txt \"x\""}, None, "allow"),
    ("Agent", {"prompt": "beyansiz mimar spec"}, None, "deny"),
    # 🔴 NEGATIF KONTROL (20 Agu): gecerli BEYANLI Agent — SERT_BLOK evlerinde (KraL/MaCiT)
    # RED kalmali. Tam da tarayicinin acildigi iki ev. Beklenti ISCI enjektorundeki
    # 'beyanli_beklenen' ile AYNI kuraldan turer; burada da ev bazli sentinel kullanilir.
    ("Agent", {"prompt": "is X\ncodex-muafiyet: kapi kodu — sessiz-hata"}, None,
     "<AGENT-SERT-BLOK-EV-BAZLI>"),
)


def _eve_mcp_enjekte(ad, kok, goreli, uygula, rapor):
    """Tek eve MCP-TARAYICI kuralini enjekte eder (+ settings MCP matcher kablosu).
    CODEX/AGENT enjeksiyonlariyla AYNI desen. Doner: (durum, yedek_yolu ya da None)."""
    yol = os.path.join(kok, goreli)
    if not os.path.exists(yol):
        return "KAPI-DOSYASI-YOK", None
    metin = _oku(yol)
    if MCP_DAMGA in metin:
        # Kural VAR; kablo eksik olabilir (ayri eksen) — kablo durumu raporlanir.
        rapor.append("      settings MCP matcher: " + _mcp_ev_settings(kok, goreli, uygula))
        return "ZATEN TAM", None

    eksik = [s for s in MCP_ZORUNLU_SEMBOL if s not in metin]
    if eksik:
        rapor.append("      zorunlu sembol EKSIK: " + repr(eksik[0]))
        return "UYUMSUZ-KAPI (dokunulmadi)", None

    if not uygula:
        return "ENJEKTE EDILECEK", None

    yedek = yol + ".yedek-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(yol, yedek)

    temiz = _blogu_sok(metin, MCP_TANIM_BAS, MCP_TANIM_SON)
    temiz = _blogu_sok(temiz, MCP_CAGRI_BAS, MCP_CAGRI_SON)
    yeni = temiz.replace(MCP_ANKRAJ_TANIM, MCP_TANIM_SABLON + MCP_ANKRAJ_TANIM, 1)
    yeni = yeni.replace(MCP_ANKRAJ_CAGRI, MCP_CAGRI_SABLON + MCP_ANKRAJ_CAGRI, 1)
    _yaz(yol, yeni)

    def geri_al(neden):
        shutil.copyfile(yedek, yol)
        rapor.append("      GERI ALINDI (" + neden + ") — yedek: " + yedek)

    try:
        compile(yeni, yol, "exec")
    except SyntaxError as hata:
        geri_al("SyntaxError: " + str(hata)[:60])
        return "GERI ALINDI (derlenmedi)", yedek

    # 🔴 20 AGU: EV BAZLI beklentiler. IKI SENTINEL, TERS YONDE — bu evde tarayici ACIK
    # ise Claude iscisi (beyanli Agent) hala KAPALI olmalidir. Ikisi ayni ev listesinden
    # okunur ama ZIT hukum uretir; iki eksen tek kumeye indirgenirse ikisi AYNI anda
    # tutamaz ve ev GERI ALINIR (sessiz gecis yok).
    tarayici_acik = ad in MCP_TARAYICI_ACIK_EV_ADLARI
    sert_blok_ev = ad in ("KraL", "MaCiT")
    for tn, ti, aid, beklenen in MCP_FIKSTURLERI:
        if beklenen == MCP_TARAYICI_BEKLENTI:
            beklenen = "allow" if tarayici_acik else "deny"
        elif beklenen == "<AGENT-SERT-BLOK-EV-BAZLI>":
            beklenen = "deny" if sert_blok_ev else "allow"
        olculen = _agent_fikstur(yol, kok, tn, ti, aid)
        if olculen != beklenen:
            geri_al("fikstur tn=" + tn + " beklenen=" + beklenen + " olculen=" + str(olculen))
            return "GERI ALINDI (fikstur)", yedek

    rapor.append("      yedek: " + yedek)
    rapor.append("      info/exclude: " + _yedeklerimi_gizle(kok) +
                 " | skip-worktree: " + _skip_worktree(kok, goreli) +
                 " | settings MCP matcher: " + _mcp_ev_settings(kok, goreli, uygula))
    return "KURULDU", yedek


def mcp_kapisi(uygula):
    """6 EVE MCP-TARAYICI kapisini kurar/dogrular. Cikis 0 = 6 evin hepsi TAM (kural + kablo).

    KraL 'kaynak' modda: kural commit'li tools/mimar-icra-kapisi.py'de yasar, bu arac orayi
    YAZMAZ — yalnizca DOGRULAR; ama KABLOSUNU (settings MCP matcher) burada kurar, cunku
    .claude/ commit EDILMEZ ve baska hicbir akis onu kurmuyor."""
    print("MCP-TARAYICI KAPISI DAMGASI: " + MCP_DAMGA)
    print("MATCHER: " + MCP_MATCHER)
    print("MOD: " + ("UYGULA" if uygula else "KURU KOSUM (degisiklik yok)"))
    print("")
    eksik = 0
    for ad, kok, _varsayilan_goreli, mod in CODEX_EVLER:
        rapor = []
        if not os.path.isdir(kok):
            print("{:<7} {:<34} {:<9} {}".format(ad, "-", mod, "EV YOK"))
            eksik += 1
            continue
        # 🔴 YOL OLCUMU (sabit varsayilmaz): KraL tools/, kardesler .claude/ altinda.
        goreli, _kablo = _kapi_yolu_olc(kok)
        if goreli is None:
            print("{:<7} {:<34} {:<9} {}".format(
                ad, "?", mod, "KAPI YOLU OLCULEMEDI (diskte aday yok) — DOKUNULMADI"))
            eksik += 1
            continue
        if mod == "kaynak":
            try:
                kural = MCP_DAMGA in _oku(os.path.join(kok, goreli))
            except Exception:
                kural = False
            kablo = _mcp_ev_settings(kok, goreli, uygula)
            rapor.append("      settings MCP matcher: " + kablo)
            if not kural:
                durum_metni = "EKSIK (kaynak dosya — dal ile guncellenir, arac YAZMAZ)"
            elif kablo in ("zaten", "kuruldu"):
                durum_metni = "ZATEN TAM"
            else:
                durum_metni = "KURAL VAR / KABLO EKSIK (" + kablo + ")"
        else:
            durum_metni, _ = _eve_mcp_enjekte(ad, kok, goreli, uygula, rapor)
        if durum_metni != "ZATEN TAM" and not (uygula and durum_metni == "KURULDU"):
            eksik += 1
        print("{:<7} {:<34} {:<9} {}".format(ad, goreli, mod, durum_metni))
        for satir in rapor:
            print(satir)
    print("")
    print("TAM OLMAYAN EV: " + str(eksik))
    print("KURULU_EV=" + str(len(CODEX_EVLER) - eksik) + "/" + str(len(CODEX_EVLER)))
    if not uygula:
        print("Kuru kosum. Uygulamak icin ayni komuta --uygula ekle.")
    print("Dogrula: python3 /Users/okan/dev/pruvo/tools/mimar-kapi-6ev-test.py")
    sys.exit(0 if eksik == 0 else 1)


# ===================== 13 AGU: ISCI-SARMALAYICI KAPISI 6 EVE (goc karari) =====================
# OLCULEN DELIK: 13 Agu gocu isci katini '~/.claude/cron/isci.sh <motor> <ev> <spec>
# [etiket]' sarmalayicisina tasidi, ama 20 Tem'in "repo DISINDAKI betigi kosturma" kurali
# sarmalayiciyi da reddediyordu -> mimarin UCUZ motora is verme yolu MAKINE tarafindan
# kapali, geriye yalniz PAHALI yol (Claude iscisi) kaliyordu. Bu mod o kolu 6 EVE kurar.
# Desen CODEX/AGENT/MCP modlariyla AYNI: DAR + IDEMPOTENT + YEDEKLI + FAIL-CLOSED.
#
# 🔴 IKIZ TANIM YASAGI: enjekte edilen blok AGENT_MUAFIYET_RE'yi YENIDEN TANIMLAMAZ,
# AGENT-KAPISI'nin regex'ini ve _agent_isci_mi()'sini CAGIRIR. Bu yuzden AGENT_DAMGA bir
# ZORUNLU SEMBOLDUR: AGENT-KAPISI kurulmamis eve DOKUNULMAZ (yoksa motor=claude beyan
# sarti sessizce kaybolur ve sarmalayici AGENT-KAPISI'ni atlatan anahtara doner).
ISCI_DAMGA = 'ISCI_KURAL_SURUMU = "' + isci_damgasi() + '"'
ISCI_TANIM_BAS = "# === PRUVO ISCI-SARMALAYICI KAPISI BASLANGIC (mimar-kapi-kur.py enjekte etti) ==="
ISCI_TANIM_SON = "# === PRUVO ISCI-SARMALAYICI KAPISI BITIS ==="
ISCI_KIMLIK_CAGRI_BAS = "    # === PRUVO ISCI KIMLIK CAGRI BASLANGIC (mimar-kapi-kur.py) ==="
ISCI_KIMLIK_CAGRI_SON = "    # === PRUVO ISCI KIMLIK CAGRI BITIS ==="
ISCI_CAGRI_BAS = "        # === PRUVO ISCI-SARMALAYICI CAGRI BASLANGIC (mimar-kapi-kur.py) ==="
ISCI_CAGRI_SON = "        # === PRUVO ISCI-SARMALAYICI CAGRI BITIS ==="
ISCI_ANKRAJ_TANIM = "\ndef main():\n"
ISCI_ANKRAJ_KIMLIK = "    # === PRUVO MCP-TARAYICI CAGRI BASLANGIC (mimar-kapi-kur.py) ==="
# CAGRI ankraji SEGMENT DONGUSUNUN icindedir (codex kolunun kullandigi ankrajin AYNISI) —
# kural 'gecer' halinde segmenti 'continue' ile KAPATMAK ZORUNDA oldugu icin dongu DISINA
# enjekte edilemez: sarmalayicinin argumanlari BILEREK repo DISIDIR.
ISCI_ANKRAJ_CAGRI = "        ad = os.path.basename(argv0)\n"
ISCI_ZORUNLU_SEMBOL = (
    "def reddet(", "import os", "def _agent_isci_mi(", AGENT_DAMGA,
    ISCI_ANKRAJ_TANIM, ISCI_ANKRAJ_KIMLIK, ISCI_ANKRAJ_CAGRI,
)

ISCI_TANIM_SABLON = '''

''' + ISCI_TANIM_BAS + '''
# 13 AGU (goc karari): sarmalayiciyi cagirmak KENDI ELIYLE IS YAPMAK DEGIL, ISCI
# DAGITMAKTIR (26 Tem BaBa hukmu ile AYNI SINIF) — ama KOSULSUZ MUAFIYET DEGIL, ayni
# KALITE KAPISI: yol TAM ESITLIK · argüman 3-4 · motor KAPALI KUME · motor=claude ise
# AGENT-KAPISI'nin BEYAN SARTI (AYNI regex) · spec okunamiyorsa RED (fail-closed).
#
# 🔴 20 AGU (K250) — EV-GORELI COZUMLEME. Bu blok ARTIK evin COMMIT'LENEN kapi
# dosyasinda yasiyor (bkz. --sablon-yayimla): yani her taze worktree'ye ve baska bir
# makineye/hesaba checkout ile iniyor. Makineye cakili "/Users/<ad>/..." yolu orada
# YANLIS olurdu ve kullanici adini da tasirdi. TAM ESITLIK KARSILASTIRMASI DEGISMEDI —
# _isci_karari hala '==' ile ariyor; kapi GENISLEMEDI, ayni tek yolu tasinabilir
# bicimde HESAPLIYOR. HOME cozulemezse expanduser '~' onekini birakir, hicbir gercek
# argv0 esitlesmez ve cagri A adimina dusup REDDEDILIR (fail-closed, DAR taraf).
ISCI_SARMALAYICI_YOLU = os.path.expanduser("~/.claude/cron/isci.sh")
ISCI_M3_SARMALAYICI_YOLU = os.path.expanduser("~/.claude/cron/m3-isci.sh")
ISCI_M3_CIVILI_MOTOR = "minimax-m3"
''' + motor_blogu_kaynagi() + '''ISCI_ARGUMAN_SAYILARI = (3, 4)
''' + ISCI_DAMGA + '''
ISCI_MOTOR_LISTESI = " / ".join(ISCI_MOTORLARI)
CANLI_MOTOR_LISTESI = " / ".join(CANLI_ISCI_MOTORLARI)
EMEKLI_MOTOR_LISTESI = " / ".join(EMEKLI_ISCI_MOTORLARI)
ISCI_GEREKCE_SONU = (
    " DOGRUSU: " + ISCI_SARMALAYICI_YOLU + " <MOTOR> <EV_KOKU> <SPEC_DOSYASI> [ETIKET] "
    "(m3 kisayolu: " + ISCI_M3_SARMALAYICI_YOLU + " <EV_KOKU> <SPEC_DOSYASI> [ETIKET]). "
    "Gecerli motor: " + ISCI_MOTOR_LISTESI + "."
)
ISCI_CLAUDE_GEREKCESI = (
    "ISCI-SARMALAYICI KAPISI (13 Agu): sarmalayici 'claude' MOTORUYLA cagriliyor ama SPEC "
    "DOSYASINDA 'codex-muafiyet:' BEYAN SATIRI YOK. Bu sart olmasaydi sarmalayici "
    "AGENT-KAPISI'ni atlatan bir ANAHTAR olurdu. IKI CIKIS: (a) ISI UCUZ MOTORA VER "
    "(" + CANLI_MOTOR_LISTESI + "); VEYA (b) spec dosyasina su satiri EKLE: "
    "'codex-muafiyet: <is tanimi> - " + AGENT_ORNEK_SINIF + "' (gecerli sinif jetonlari: " +
    AGENT_SINIF_LISTESI + ")."
)
# 19 AGU (K214): emekli kata IS YOLLAMA reddinin gerekcesi. Kimlik ekseni DOKUNULMAZ —
# emekli motorlarin ESKI turleri isci sayilmaya devam eder (mimar_kimlik.py doktrini).
ISCI_EMEKLI_GEREKCESI_ONEKI = "EMEKLI motor ("
ISCI_EMEKLI_GEREKCESI_SONU = (
    "): bu kata YENI IS YOLLANMAZ. Kimlik tanimada gecerli kalir (eski turlar isci "
    "sayilir), ama dagitim CANLI kumeden yapilir — canli kume: " + CANLI_MOTOR_LISTESI +
    " (birincil: " + CANLI_ISCI_MOTORLARI[0] + "). Emekli kume: " + EMEKLI_MOTOR_LISTESI + "."
)


def _isci_kimlik_ekseni(girdi):
    """None = MIMAR; agent_id veya kapali motor kumesi = ISCI kimlik kaynagi."""
    aid = girdi.get("agent_id")
    if isinstance(aid, str) and aid.strip():
        return "agent_id"
    motor = os.environ.get("PRUVO_ISCI_KOSUMU")
    if motor in ISCI_MOTORLARI:
        return "sarmalayici:" + motor
    return None


def _isci_iz_bas(etiket):
    try:
        sys.stderr.write("MIMAR-KAPISI allow " + etiket + "\\n")
    except Exception:
        pass


def _isci_reddet(neden):
    """Ev kapisinin reddet() fonksiyonunu kullanir. Iki imza var: KraL'da
    reddet(neden, sonu=None), yol-bagimsiz sablonda reddet(neden). Arity OLCULUR."""
    try:
        arity = reddet.__code__.co_argcount
    except Exception:
        arity = 1
    if arity >= 2:
        reddet(neden, sonu=ISCI_GEREKCE_SONU)
    reddet(neden + ISCI_GEREKCE_SONU)


def _isci_karari(tokenlar):
    """None = kural uygulanmaz · "gecer" = izinli (isci dagitmak mimarliktir) ·
    str = red gerekcesi. m3-isci.sh YONLENDIRMEDIR: imzasi MOTORSUZDUR ve motoru
    minimax-m3'e CIVILIDIR — basina o motor konmus gibi degerlendirilir."""
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
            "isci sarmalayicisi YANLIS ARGUMAN SAYISIYLA cagriliyor (motor dahil " +
            str(len(argumanlar)) + "; beklenen 3 ya da 4)."
        )
    motor = argumanlar[0]
    if motor not in ISCI_MOTORLARI:
        return (
            "isci sarmalayicisinin MOTORU kapali kumede DEGIL (" + motor[:24] + "). "
            "Bilinmeyen motor VARSAYILAN RED (fail-closed)."
        )
    # 19 AGU (K214) SIKILASTIRMA — EMEKLI KAT: kapali kume KIMLIK icindir, DAGITIM icin
    # degil. 'claude' EMEKLI DEGILDIR: asagidaki claude kolu AYNEN korunur.
    if motor in EMEKLI_ISCI_MOTORLARI:
        return ISCI_EMEKLI_GEREKCESI_ONEKI + motor[:24] + ISCI_EMEKLI_GEREKCESI_SONU
    if (motor == "claude" and EV_ADI in SERT_BLOK_EVLER and
            os.environ.get("PRUVO_CLAUDE_ISCI_IZNI") != "OKAN"):
        return _sert_blok_gerekcesi()
    if motor == "claude":
        spec_yolu = argumanlar[2]
        try:
            with open(spec_yolu, encoding="utf-8") as _f:
                spec_metni = _f.read()
        except Exception:
            return (
                "isci sarmalayicisi 'claude' MOTORUYLA cagriliyor ama SPEC DOSYASI "
                "OKUNAMADI (" + spec_yolu[:70] + "): beyani OLCEMEDIM. Olculemeyen beyan "
                "YESIL DEGILDIR (fail-closed). " + ISCI_CLAUDE_GEREKCESI
            )
        if not AGENT_MUAFIYET_RE.search(spec_metni):
            return ISCI_CLAUDE_GEREKCESI
    return "gecer"
''' + ISCI_TANIM_SON + '''
'''

ISCI_KIMLIK_CAGRI_SABLON = (
    ISCI_KIMLIK_CAGRI_BAS + "\n"
    "    _isci_eksen = _isci_kimlik_ekseni(girdi)\n"
    "    if _isci_eksen is not None:\n"
    '        _isci_iz_bas("ISCI(" + _isci_eksen + ")")\n'
    "        sys.exit(0)\n"
    + ISCI_KIMLIK_CAGRI_SON + "\n"
)

# 🔴 KIMLIK: _agent_isci_mi() — AGENT-KAPISI'nin TESPITI YENIDEN KULLANILIR.
# 🔴 OLCULEN KUSUR (BaBa evi, hermetik kopyada yakalandi): kimlik kontrolu 'continue'yi
# de kapsayacak sekilde yazilinca ISCI kimligindeki sarmalayici cagrisi bloktan HIC
# gecmiyor, sonra A adimina (repo-disi betik) dusup RED aliyordu. KraL'da gorunmez, cunku
# orada ISCI main() BASINDA cikar; BaBa evinin kapisi kimlik ekseni TASIMIYOR ve kusur
# orada gorundu. DOGRUSU: kimlik YALNIZ REDDI kosullar, SEGMENT KAPANISI ('continue') her
# iki kimlikte de olur — boylece ISCI davranisi 6 evde AYNI kalir.
ISCI_CAGRI_SABLON = (
    ISCI_CAGRI_BAS + "\n"
    "        _isci_karar = _isci_karari(tokenlar)\n"
    "        if _isci_karar is not None:\n"
    '            if _isci_karar != "gecer" and not _agent_isci_mi(girdi):\n'
    "                _isci_reddet(_isci_karar)\n"
    "            continue\n"
    + ISCI_CAGRI_SON + "\n"
)


def _isci_fikstur_specleri():
    """Enjeksiyon sonrasi CANLI FIKSTURLER icin gecici spec dosyalari (hermetik).
    Doner: (beyansiz_yol, beyanli_yol, hic_yazilmayan_yol)."""
    dizin = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-isci-kur-spec-"))
    beyansiz = os.path.join(dizin, "beyansiz.md")
    beyanli = os.path.join(dizin, "beyanli.md")
    _yaz(beyansiz, "Olcum isi. Beyan satiri YOK.\n")
    _yaz(beyanli, "Is X.\ncodex-muafiyet: kapi kodu insasi " + "—" + " sessiz-hata\n")
    return dizin, beyansiz, beyanli, os.path.join(dizin, "hic-yazilmadi.md")


def _eve_isci_enjekte(ad, kok, goreli, uygula, rapor):
    """Tek eve ISCI-SARMALAYICI kuralini enjekte eder. CODEX/AGENT/MCP ile AYNI desen.
    Doner: (durum, yedek_yolu ya da None).

    K259 (24 Agu 2026) — DAMGA ICERIKTEN TURETILIR ([[emir-canliligi-kurulu-kopyadan-
    olculur]]): 'ZATEN TAM' karari artik ICERIK ESITLIGIYLE verilir, damga esitligiyle
    degil. Kurulu kopyadaki ISCI blogu tek kaynaktan uretilenle birebir ayniysa
    ZATEN_AYNI (dosyaya dokunmaz; idempotent); degilse yeniden yazilir (DAGITILDI).
    'IKINCI KAYNAK BIRAKMA' (mimar hukmu): kurulu kopyadaki deger tek kaynaktan EZILIR,
    'zaten tanimliysa dokunma' davranisi KALDIRILDI."""
    yol = os.path.join(kok, goreli)
    if not os.path.exists(yol):
        return "KAPI-DOSYASI-YOK", None
    metin = _oku(yol)

    # K259: icerik esitligi. Kurulu kopyadaki ISCI blogu (marker'lar dahil) ile
    # ISCI_TANIM_SABLON birebir ayniysa ZATEN_AYNI; yoksa yeniden yazilacak (DAGITILDI).
    mevcut_isci_blogu = _isci_blogu(metin)
    yeni_isci_blogu = ISCI_TANIM_SABLON
    if (mevcut_isci_blogu and
            mevcut_isci_blogu.strip() == yeni_isci_blogu.strip()):
        rapor.append("      ZATEN_AYNI: kurulu kopya tek kaynakla birebir (icerik esit)")
        return "ZATEN_AYNI", None

    eksik = [s for s in ISCI_ZORUNLU_SEMBOL if s not in metin]
    if eksik:
        rapor.append("      zorunlu sembol EKSIK: " + repr(eksik[0]))
        return "ATLANDI:UYUMSUZ-KAPI (dokunulmadi)", None

    if not uygula:
        return "ENJEKTE EDILECEK", None

    yedek = yol + ".yedek-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(yol, yedek)

    temiz = _blogu_sok(metin, ISCI_TANIM_BAS, ISCI_TANIM_SON)
    temiz = _blogu_sok(temiz, ISCI_KIMLIK_CAGRI_BAS, ISCI_KIMLIK_CAGRI_SON)
    temiz = _blogu_sok(temiz, ISCI_CAGRI_BAS, ISCI_CAGRI_SON)
    yeni = temiz.replace(ISCI_ANKRAJ_TANIM, ISCI_TANIM_SABLON + ISCI_ANKRAJ_TANIM, 1)
    yeni = yeni.replace(ISCI_ANKRAJ_KIMLIK,
                        ISCI_KIMLIK_CAGRI_SABLON + ISCI_ANKRAJ_KIMLIK, 1)
    yeni = yeni.replace(ISCI_ANKRAJ_CAGRI, ISCI_CAGRI_SABLON + ISCI_ANKRAJ_CAGRI, 1)
    _yaz(yol, yeni)

    def geri_al(neden):
        shutil.copyfile(yedek, yol)
        rapor.append("      GERI ALINDI (" + neden + ") — yedek: " + yedek)

    try:
        compile(yeni, yol, "exec")
    except SyntaxError as hata:
        geri_al("SyntaxError: " + str(hata)[:60])
        return "GERI ALINDI (derlenmedi)", yedek

    dizin, beyansiz, beyanli, yok_spec = _isci_fikstur_specleri()
    try:
        W = ISCI_SARMALAYICI_YOLU_SABIT
        beyanli_beklenen = "deny" if ad in ("KraL", "MaCiT") else "allow"
        # 19 AGU (K214): DAGITIM fiksturleri CANLI motorla kosar — birincil kat
        # CANLI_ISCI_MOTORLARI[0]'dan TURETILIR, elle yazilmaz. Emekli kat ayri bir
        # DENY fiksturuyle civilenir; boylece "kimi gecti mi" ve "deepseek reddedildi mi"
        # eksenleri her evin kurulumunda CANLI olarak olculur.
        CANLI = CANLI_ISCI_MOTORLARI[0]
        EMEKLI = EMEKLI_ISCI_MOTORLARI[-1]
        olcumler = [
            ("Bash", {"command": W + " " + CANLI + " " + kok + " " + beyansiz}, None, "allow"),
            ("Bash", {"command": W + " " + CANLI + " " + kok + " " + beyansiz + " etiket"},
             None, "allow"),
            ("Bash", {"command": ISCI_M3_YOLU_SABIT + " " + kok + " " + beyansiz}, None, "allow"),
            ("Bash", {"command": W + " gpt-9 " + kok + " " + beyansiz}, None, "deny"),
            # EMEKLI KAT: kapali kumede OLMASINA ragmen yeni is REDDEDILIR (sikilastirma).
            ("Bash", {"command": W + " " + EMEKLI + " " + kok + " " + beyansiz}, None, "deny"),
            ("Bash", {"command": W + " " + CANLI + " " + kok}, None, "deny"),
            ("Bash", {"command": W + " claude " + kok + " " + beyansiz}, None, "deny"),
            ("Bash", {"command": W + " claude " + kok + " " + beyanli}, None,
             beyanli_beklenen),
            ("Bash", {"command": W + " claude " + kok + " " + yok_spec}, None, "deny"),
            ("Bash", {"command": "/tmp/isci.sh " + CANLI + " " + kok + " " + beyansiz},
             None, "deny"),
            ("Bash", {"command": W + " " + CANLI + " " + kok + " " + beyansiz}, AGENT_ISCI_ID,
             "allow"),
            # REGRESYON: diger kollar degismedi.
            ("Bash", {"command": "ls"}, None, "allow"),
            ("Bash", {"command": 'codex exec "x"'}, None, "deny"),
            ("Bash", {"command": 'codex exec -o /tmp/son-mesaj.txt "x"'}, None, "allow"),
            ("Agent", {"prompt": "beyansiz mimar spec"}, None, "deny"),
            ("Agent", {"prompt": "is X\ncodex-muafiyet: kapi kodu — sessiz-hata"}, None,
             beyanli_beklenen),
        ]
        # 🔴 KIMLIK EKSENI — DAGITIM DEGIL (K214 ayrimi): asagidaki 'deepseek-flash'
        # BILEREK EMEKLI bir motordur ve BILEREK 'allow' bekler. Emekli bir katta
        # BASLAMIS eski bir tur hala kosuyor olabilir; kimligini geriye donuk tanimak
        # ZORUNDAYIZ (mimar_kimlik.py: "kapali kume KIMLIK TANIMA icindir"). Bunu
        # canli motora "duzeltmek" kapiyi delerdi: emekli sarmalayicidan gelen cagri
        # MIMAR sayilip allowlist'e carpar ve kosan tur ortasinda olurdu.
        olcumler += [
            ("Bash", {"command": "python3 /private/tmp/analiz.py"}, None, "allow",
             {"PRUVO_ISCI_KOSUMU": "deepseek-flash"}),
            ("Bash", {"command": "curl -s https://example.invalid"}, None, "allow",
             {"PRUVO_ISCI_KOSUMU": "claude"}),
            ("Bash", {"command": "python3 /private/tmp/analiz.py"}, None, "deny",
             {"PRUVO_ISCI_KOSUMU": "gpt-9"}),
            ("Bash", {"command": "python3 /private/tmp/analiz.py"}, None, "deny", {}),
        ]
        for olcum in olcumler:
            tn, ti, aid, beklenen = olcum[:4]
            ek_env = olcum[4] if len(olcum) > 4 else {}
            olculen = _agent_fikstur(yol, kok, tn, ti, aid, ek_env)
            if olculen != beklenen:
                geri_al("fikstur tn=" + tn + " beklenen=" + beklenen +
                        " olculen=" + str(olculen))
                return "GERI ALINDI (fikstur)", yedek
    finally:
        shutil.rmtree(dizin, ignore_errors=True)

    rapor.append("      yedek: " + yedek)
    rapor.append("      info/exclude: " + _yedeklerimi_gizle(kok) +
                 " | skip-worktree: " + _skip_worktree(kok, goreli))
    return "DAGITILDI", yedek


# Kural METNI icindeki yollarin ARAC tarafindaki ikizi (fikstur kurmak icin). Tek kaynak
# olmadigi icin degil, sablonun ICINDE yasayan sabitlere aractan erisilemedigi icin var;
# ISCI_TANIM_SABLON metninde AYNEN gecmesi asagidaki 'oz-tutarlilik' kontrolu ile civilidir.
# 20 AGU (K250): ikizin de COZUMLEMESI ayni — sablonda yazan ifade `os.path.expanduser(...)`,
# aractaki degeri o ifadenin BU makinede cozulmus hali. Oz-tutarlilik nobetcisi ikisini
# birden olcer (hem IFADE sablonda geciyor mu, hem DEGER cozulmusuyle esit mi).
ISCI_SARMALAYICI_IFADESI = 'os.path.expanduser("~/.claude/cron/isci.sh")'
ISCI_M3_IFADESI = 'os.path.expanduser("~/.claude/cron/m3-isci.sh")'
ISCI_SARMALAYICI_YOLU_SABIT = os.path.expanduser("~/.claude/cron/isci.sh")
ISCI_M3_YOLU_SABIT = os.path.expanduser("~/.claude/cron/m3-isci.sh")


def isci_kapisi(uygula):
    """6 EVE ISCI-SARMALAYICI kapisini kurar/dogrular. Cikis 0 = 6 evin hepsi TAM.
    KraL 'kaynak' modda: kural commit'li tools/mimar-icra-kapisi.py'de yasar, bu arac
    orayi YAZMAZ — yalnizca DOGRULAR (icerik esitligi).

    K259 (24 Agu 2026): dagitim SESSIZ ATLAMAZ — her ev icin sonuc BASILIR
    (DAGITILDI / ZATEN_AYNI / ATLANDI:<sebep>). 'ZATEN TAM' hukmu YALNIZCA icerik
    esitligi olculdukten sonra verilebilir; damga esitligi tek basina yeterli degildir.
    'Zaten tanimliysa dokunma' davranisi KALDIRILDI: kurulu kopya tek kaynaktan EZILIR
    (idempotent uretim)."""
    print("ISCI-SARMALAYICI KAPISI DAMGASI: " + ISCI_DAMGA)
    print("SARMALAYICI: " + ISCI_SARMALAYICI_YOLU_SABIT + " | YONLENDIRME: " +
          ISCI_M3_YOLU_SABIT)
    print("MOD: " + ("UYGULA" if uygula else "KURU KOSUM (degisiklik yok)"))
    # OZ-TUTARLILIK (ikiz tanim nobetcisi): aractaki yol sabitleri sablonun ICINDEKI
    # tanimlarla AYNI olmali; ayrisirsa fikstur YANLIS komutu olcer ve "kuruldu" der.
    # 20 AGU (K250) IKI EKSEN: (1) sablonda EV-GORELI IFADE aynen geciyor mu, (2) aractaki
    # DEGER o ifadenin bu makinede cozulmus haline esit mi. Yalniz (1) olcuseydi arac,
    # sablon expanduser'a gecerken kendi sabitini eski mutlak yolda birakabilir ve fikstur
    # baska bir komutu olcerdi ([[ad-iki-rolde-mutanti-golgeler]]).
    for _ifade, _sabit in ((ISCI_SARMALAYICI_IFADESI, ISCI_SARMALAYICI_YOLU_SABIT),
                           (ISCI_M3_IFADESI, ISCI_M3_YOLU_SABIT)):
        if _ifade not in ISCI_TANIM_SABLON:
            print("OZ-TUTARLILIK KIRMIZI: sablonda IFADE gecmiyor -> " + _ifade)
            sys.exit(1)
        if _sabit != os.path.expanduser(_ifade.split('"')[1]):
            print("OZ-TUTARLILIK KIRMIZI: arac DEGERI ifadeyle ayristi -> " + _sabit)
            sys.exit(1)
    print("")
    eksik = 0
    sayac = {"DAGITILDI": 0, "ZATEN_AYNI": 0, "ATLANDI": 0, "DIGER": 0}
    for ad, kok, _varsayilan_goreli, mod in CODEX_EVLER:
        rapor = []
        if not os.path.isdir(kok):
            print("{:<7} {:<34} {:<9} {}".format(ad, "-", mod, "ATLANDI:EV YOK"))
            sayac["ATLANDI"] += 1
            eksik += 1
            continue
        goreli, _kablo = _kapi_yolu_olc(kok)
        if goreli is None:
            print("{:<7} {:<34} {:<9} {}".format(
                ad, "?", mod, "ATLANDI:KAPI YOLU OLCULEMEDI (diskte aday yok)"))
            sayac["ATLANDI"] += 1
            eksik += 1
            continue
        if mod == "kaynak":
            # KraL: kural commit'li kaynakta yasar; bu arac orayi YAZMAZ, yalniz DOGRULAR.
            # K259: 'ZATEN_AYNI' yalniz ICERIK ESITLIGIYLE; damga tek basina yeterli degil.
            try:
                kaynak_metin = _oku(os.path.join(kok, goreli))
            except Exception:
                durum_metni = "ATLANDI:KAPI-DOSYASI-YOK"
            else:
                mevcut = _isci_blogu(kaynak_metin)
                if (mevcut and
                        mevcut.strip() == ISCI_TANIM_SABLON.strip()):
                    durum_metni = "ZATEN_AYNI"
                else:
                    durum_metni = "ATLANDI:KAYNAK-EKSIK (dal ile guncellenir, arac YAZMAZ)"
        else:
            durum_metni, _ = _eve_isci_enjekte(ad, kok, goreli, uygula, rapor)
        if durum_metni in sayac:
            sayac[durum_metni] += 1
        elif durum_metni.startswith("ATLANDI"):
            sayac["ATLANDI"] += 1
        else:
            sayac["DIGER"] += 1
        if durum_metni not in ("ZATEN_AYNI", "DAGITILDI"):
            eksik += 1
        print("{:<7} {:<34} {:<9} {}".format(ad, goreli, mod, durum_metni))
        for satir in rapor:
            print(satir)
    print("")
    # K259: dagitim Raporu — her ev icin sonuc ayri ayri BASILDI; burada TOPLAM.
    print("DAGITIM OZETI: DAGITILDI=" + str(sayac["DAGITILDI"]) +
          " · ZATEN_AYNI=" + str(sayac["ZATEN_AYNI"]) +
          " · ATLANDI=" + str(sayac["ATLANDI"]) +
          " · DIGER=" + str(sayac["DIGER"]))
    print("TAM OLMAYAN EV: " + str(eksik))
    print("KURULU_EV=" + str(len(CODEX_EVLER) - eksik) + "/" + str(len(CODEX_EVLER)))
    if not uygula:
        print("Kuru kosum. Uygulamak icin ayni komuta --uygula ekle.")
    print("Dogrula: python3 /Users/okan/dev/pruvo/tools/mimar-kilit-test.py")
    sys.exit(0 if eksik == 0 else 1)


# ==============================================================================
# 20 AGU (K250) — SABLON YAYIMI: ISTISNAYI COMMIT'LENEN SABLON TASIR
# ==============================================================================
# OLCULEN ARIZA (MaCiT bildirdi, KraL uc bacakta dogruladi): ISCI-SARMALAYICI istisnasi
# YALNIZ ana checkout'un DISK kopyasinda yasiyordu. Uc bacak:
#   pruvo-hasat ana checkout disk kopyasi : ISCI damgasi VAR, index 'S' (skip-worktree)
#   ayni yol, `git show HEAD:`            : damga YOK  (istisna git'e HIC girmemis)
#   canli worktree macit-audi-gorsel-gate : damga YOK, index 'H'
# Sonuc: `git worktree add` ile dogan HER agac istisnasiz doguyor; worktree-koklu bir
# mimar oturumu `isci.sh` ile hicbir delegasyon YAPAMIYOR — mekanik/hacim isini ucuz
# kata verme yolu MAKINE tarafindan kapali kaliyor (13 Agu'nun TERSINE TESVIKI, geri).
#
# 🔴 CARE TEKIL YAMA DEGIL (K250 hukmu): kurulum betigine `git worktree list` taramasi
# EKLEMEK, her worktree DOGUMUNDA yarisan bir yamadir — arada dogan agac yine istisnasiz
# olur ve sinif kusuru kapanmaz. Cozum TASIYICIYI degistirmektir: kural evin IZLENEN kapi
# dosyasina yazilir, skip-worktree KALDIRILIR, dosya STAGE'lenir; ev mimari commit'ler.
# O andan itibaren HEAD kurali tasir ve `git worktree add` ile dogan her agac istisnayi
# HAZIR alir — kurulum betigi TEK TASIYICI olmaktan cikar (KraL evi 'kaynak' modda zaten
# boyle calisiyordu; bu mod diger 5 evi ayni hale getirir).
#
# 🔴 BU MOD KOMMIT ETMEZ. Kardes deponun tarihine yazmak o evin mimarinin isidir; burada
# yalnizca ENJEKTE + UNSKIP + STAGE yapilir ve commit komutu BASILIR. Boylece kosan bir
# komsu oturumun agaci sessizce commit'lenmez ([[coklu-ajan-calismasi]]).
#
# 🔴 SIZINTI KAPISI (fail-closed) — AMA MUTLAK SAYAC DEGIL, ONCE/SONRA FARKI.
# Sablon MAKINEYE CAKILI ev yolu (`/Users/<ad>/`) tasimamali; K250'nin 'ev-goreli
# cozumleme' sarti burada CIVILENIR. Ancak kapi IKI SORUYU AYIRIR:
#   (a) BU YAYIMIN EKLEDIGI sizinti satiri var mi   -> VARSA fail-closed, ev ATLANIR
#   (b) HEAD'de ZATEN duran sizinti satiri var mi   -> RAPOR EDILIR, BLOKLAMAZ
# Mutlak sayac olcseydi kapi, kendisinden once oraya yazilmis (ve zaten git tarihinde
# duran) satirlar yuzunden HER evi bloklardi: yayim hic olmaz, K250 kapanmaz ve kapi
# "komsuyu kirmiziya yakar" ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).
# Olculdu (K250 ilk turu): enjekte ev dosyasi HEAD'de 3 sizinti satiri TASIYOR ve bu
# yayimin ekledigi satir sayisi 0 — hatta ISCI blogunun expanduser'a gecisi 3 satir
# EKSILTIYOR. Mutlak esik bu turu yanlis-kirmizi yakmisti.

SIZINTI_DESENI = re.compile(r"/Users/[A-Za-z0-9._-]+/")


def _sizinti_satirlari(metin):
    """Sizinti tasiyan satirlarin KUMESI (kirpilmis). Sayac degil KUME: ayni satirin
    yerinin degismesi 'yeni sizinti' sayilmasin."""
    return set(s.strip() for s in (metin or "").splitlines() if SIZINTI_DESENI.search(s))


def _isci_blogu(metin):
    """Enjekte edilen ISCI TANIM blogunun govdesi (marker'lar arasi). Yoksa ""."""
    bas = metin.find(ISCI_TANIM_BAS)
    son = metin.find(ISCI_TANIM_SON)
    if bas < 0 or son < 0 or son < bas:
        return ""
    return metin[bas:son + len(ISCI_TANIM_SON)]


def _unskip_worktree(kok, goreli):
    """skip-worktree bayragini KALDIRIR (yayim icin sart: bayrakliyken 'git add' yerel
    degisikligi index'e almaz). Doner: "kaldirildi" / "zaten" / "izlenmiyor" / "hata"."""
    liste = _git(kok, "ls-files", "-v", "--", goreli)
    if liste is None or liste.returncode != 0:
        return "hata"
    satir = (liste.stdout or "").strip()
    if not satir:
        return "izlenmiyor"
    if satir[0] not in ("S", "s"):
        return "zaten"
    sonuc = _git(kok, "update-index", "--no-skip-worktree", "--", goreli)
    if sonuc is None or sonuc.returncode != 0:
        return "hata"
    return "kaldirildi"


def _head_damgasi(kok, goreli):
    """HEAD'deki kopya ISCI damgasini tasiyor mu — yani TAZE WORKTREE ne gorecek?
    Doner: "VAR" / "YOK" / "DOSYA-YOK" / "olculemedi"."""
    sonuc = _git(kok, "show", "HEAD:" + goreli)
    if sonuc is None:
        return "olculemedi"
    if sonuc.returncode != 0:
        return "DOSYA-YOK"
    return "VAR" if ISCI_DAMGA in (sonuc.stdout or "") else "YOK"


def _eve_sablon_yayimla(ad, kok, goreli, uygula, rapor):
    """Tek evde istisnayi COMMIT'LENEBILIR hale getirir. Doner: durum metni."""
    yol = os.path.join(kok, goreli)
    if not os.path.exists(yol):
        return "KAPI-DOSYASI-YOK"
    metin = _oku(yol)
    if ISCI_DAMGA not in metin:
        return "DAMGA YOK (once --isci-kapisi --uygula)"
    # SIZINTI — iki eksen ayri (yukaridaki blok yorumu). Once K250'nin KENDI sarti:
    # enjekte edilen ISCI blogu sizinti TASIYAMAZ (ev-goreli cozumleme sarti).
    blok_sizintisi = _sizinti_satirlari(_isci_blogu(metin))
    if blok_sizintisi:
        rapor.append("      SIZINTI (ISCI BLOGU): " + sorted(blok_sizintisi)[0][:80] +
                     " — EV ATLANDI (fail-closed; sablon ev-goreli cozumlemeli)")
        return "SIZINTI-BLOK (dokunulmadi)"
    gosterim = _git(kok, "show", "HEAD:" + goreli)
    head_metni = gosterim.stdout if (gosterim and gosterim.returncode == 0) else ""
    onceki = _sizinti_satirlari(head_metni)
    simdiki = _sizinti_satirlari(metin)
    eklenen = simdiki - onceki
    if eklenen:
        rapor.append("      SIZINTI (YAYIMIN EKLEDIGI " + str(len(eklenen)) + " satir): " +
                     sorted(eklenen)[0][:80] + " — EV ATLANDI (fail-closed)")
        return "SIZINTI-YENI (dokunulmadi)"
    if onceki:
        rapor.append("      not: HEAD'de ZATEN duran sizinti satiri=" + str(len(onceki)) +
                     " · bu yayimin ekledigi=0 · eksilttigi=" +
                     str(len(onceki - simdiki)) + " (bloklamaz; AYRI kalem)")
    izleme = _git(kok, "ls-files", "-v", "--", goreli)
    if izleme is None or izleme.returncode != 0 or not (izleme.stdout or "").strip():
        rapor.append("      dosya bu depoda IZLENMIYOR — once 'git add -f " + goreli +
                     "' gerekir; yayim TASIYICI degistiremez")
        return "IZLENMIYOR (dokunulmadi)"
    if not uygula:
        return "YAYIMLANACAK (skip-worktree kalkar + stage)"
    unskip = _unskip_worktree(kok, goreli)
    ekle = _git(kok, "add", "--", goreli)
    if ekle is None or ekle.returncode != 0:
        return "GIT ADD KIRMIZI"
    rapor.append("      skip-worktree: " + unskip + " | stage: eklendi")
    rapor.append("      COMMIT (ev mimarinin isi): git -C " + kok +
                 " commit -m 'K250: isci-sarmalayici istisnasi commit'lenen sablona tasindi' -- " +
                 goreli)
    return "STAGE'LENDI (commit ev mimarinde)"


def sablon_yayimla(uygula):
    """K250 — istisnayi TASIYAN katmani degistirir: 5 enjekte evinde kapi dosyasinin
    skip-worktree bayragini kaldirir ve stage'ler. KraL 'kaynak' modda ZATEN commit'li,
    dokunulmaz. Cikis 0 = her evde HEAD ya damgayi tasiyor ya da stage'lenmis durumda."""
    print("SABLON YAYIMI (K250) — DAMGA: " + ISCI_DAMGA)
    print("MOD: " + ("UYGULA" if uygula else "KURU KOSUM (degisiklik yok)"))
    print("KURAL: ENJEKTE + UNSKIP + STAGE. COMMIT YOK (ev mimarinin isi).")
    print("")
    print("{:<7} {:<34} {:<9} {:<10} {}".format("EV", "KAPI", "MOD", "HEAD", "DURUM"))
    eksik = 0
    for ad, kok, _varsayilan_goreli, mod in CODEX_EVLER:
        rapor = []
        if not os.path.isdir(kok):
            print("{:<7} {:<34} {:<9} {:<10} {}".format(ad, "-", mod, "-", "EV YOK"))
            eksik += 1
            continue
        goreli, _kablo = _kapi_yolu_olc(kok)
        if goreli is None:
            print("{:<7} {:<34} {:<9} {:<10} {}".format(
                ad, "?", mod, "-", "KAPI YOLU OLCULEMEDI — DOKUNULMADI"))
            eksik += 1
            continue
        if mod == "kaynak":
            durum_metni = "KAYNAK (commit'li; arac YAZMAZ)"
        else:
            durum_metni = _eve_sablon_yayimla(ad, kok, goreli, uygula, rapor)
        head = _head_damgasi(kok, goreli)
        # HUKUM: HEAD damgayi tasiyorsa is BITMIS demektir; tasimiyorsa ancak bu turda
        # STAGE'lendiyse "yolda" sayilir — digerlerinin hepsi EKSIKTIR.
        if head != "VAR" and not durum_metni.startswith("STAGE'LENDI"):
            eksik += 1
        print("{:<7} {:<34} {:<9} {:<10} {}".format(ad, goreli, mod, head, durum_metni))
        for satir in rapor:
            print(satir)
    print("")
    print("HEDEF: her evde HEAD=VAR — o zaman taze worktree istisnayi HAZIR alir.")
    print("TAM OLMAYAN EV: " + str(eksik))
    print("YAYIM_EV=" + str(len(CODEX_EVLER) - eksik) + "/" + str(len(CODEX_EVLER)))
    if not uygula:
        print("Kuru kosum. Uygulamak icin ayni komuta --uygula ekle.")
    sys.exit(0 if eksik == 0 else 1)


# ==============================================================================
# N2 (B) — PARTI KAPISI DAGITIMI (19 Agu 2026, Okan onayli doktrin)
# ==============================================================================
# "Mesaj kacar, KAPI kacmaz." Acik 🔧 varken YENI parti/isci baslatma REDDEDILIR.
# 🔴 IKINCI KURUCU YAZILMADI: dagitim bu dosyanin (mevcut kurucu hattinin) yeni
#    bir kolu olarak yasar — `--parti-kapisi [--uygula]`.
#
# IKI YUZEY:
#   (1) `~/.claude/cron/isci.sh` govdesine markerli blok — CRON surucleri
#       (macit-parti-surucusu.sh vb.) PreToolUse kancasini GORMEZ; tek bogaz
#       isci.sh'tir. Idempotent + yedekli.
#   (2) Her evin `.claude/settings.json`ina `Bash` matcher'li PreToolUse kancasi
#       + evin `.claude/parti-kapisi.py` kopyasi (enjekte modu).
#
# KAPSAM: yalniz T4'un (`parti-borc-kapisi.py`) EV_DIZIN'inde COZULEBILEN evler.
# Cozulemeyen ev KURULMAZ ve `KAPSAM_DISI` olarak SATIRLA YAZILIR — sessiz
# kirpma YOK (kirpilani yazmayan rapor "hepsini kapsadim" diye okunur).
PARTI_KAPISI_ADI = "parti-kapisi.py"
PARTI_KAPISI_KAYNAK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), PARTI_KAPISI_ADI)
PARTI_MATCHER = "Bash"
PARTI_BAS = "# === N2-PARTI-KAPISI BAS ==="
PARTI_SON = "# === N2-PARTI-KAPISI SON ==="

PARTI_ISCI_BLOK = PARTI_BAS + '''
# N2 (B), 19 Agu 2026 — Okan onayli doktrin. Okan'in vakasi: "MaCiT 100-100 urun
# ekliyor, iletiyi gormedi, isine devam etti; tamirat yapilmadigi icin tum
# mimarlar MaCiT'i bekledi." Mesaj kacar, KAPI kacmaz.
#
# 🔴 SUREN IS KESILMEZ: bu blok tur BASLAMADAN once kosar. Zaten kosan bir tura
#    DOKUNMAZ; yalnizca YENISININ acilmasini durdurur.
# 🔴 Muafiyet (tamir/onarim/kabul/nobet/posta/devir etiketleri) kapinin ICINDE
#    tanimlidir — burada IKINCI liste tutulmaz ([[ikiz-tanim-sessiz-ayrisma]]).
N2_PARTI_KAPISI=/Users/okan/dev/pruvo/tools/parti-kapisi.py
if [[ -f "$N2_PARTI_KAPISI" ]]; then
  if ! python3 "$N2_PARTI_KAPISI" --isci-kapi "$ISTENEN_MOTOR" "$EV_KOKU" "$SPEC_DOSYASI" "$ETIKET"; then
    echo "N2-PARTI-KAPISI: YENI is REDDEDILDI — suren isini bitir, kalemi KAPAT." >&2
    exit 3
  fi
else
  echo "N2B-KAPI-YOK: $N2_PARTI_KAPISI bulunamadi — parti kapisi KOSMADI." >&2
fi
''' + PARTI_SON


# --- YUZEY 3: gozcu.py — kirmizi kosumun SAHIBI (N2 A) ------------------------
# Gozcu ile kapi AYNI fonksiyondan okur: `tools/ev-sahip-kapisi.py`. Gozcu KENDI
# harita kopyasini TUTMAZ; harita bozulursa kol OLCULEMEDI doner ve gozcu
# KIRMIZI yanar (spec §2-A4'un "tek kaynak" kanitinin gozcu ayagi).
GOZCU_YOLU = "/Users/okan/.claude/cron/gozcu.py"
GOZCU_BAS = "# === N2-SAHIP-KOPRUSU BAS ==="
GOZCU_SON = "# === N2-SAHIP-KOPRUSU SON ==="

GOZCU_KOPRU = GOZCU_BAS + '''
# N2 (A), 19 Agu 2026 — kirmizi kosumun SAHIBI HARITADAN turetilir.
# TEK KAYNAK: /Users/okan/dev/pruvo/tools/ev-serit-haritasi.tsv
# TEK OKUYUCU: /Users/okan/dev/pruvo/tools/ev-sahip-kapisi.py:kirmizi_sahibi
# Gozcu kendi ev tablosunu TUTMAZ. Harita bozulursa SEBEP=olculemedi doner ve
# tur KIRMIZI biter — "sessiz KraL'a yikma" davranisi YOKTUR.
N2_SAHIP_KAPISI = "/Users/okan/dev/pruvo/tools/ev-sahip-kapisi.py"
N2_REPO_KOKU = "/Users/okan/dev/pruvo"


def n2_sahip_coz(sha, kapi_yolu=None, repo_koku=None):
    """headSha -> (SAHIP, SEBEP). Kapi/harita yuklenemezse ('KraL','olculemedi')."""
    kapi_yolu = kapi_yolu or N2_SAHIP_KAPISI
    repo_koku = repo_koku or N2_REPO_KOKU
    if not sha:
        return ("KraL", "olculemedi")
    try:
        import importlib.util as _n2_ilu
        _n2_spec = _n2_ilu.spec_from_file_location("pruvo_n2a_sahip", kapi_yolu)
        if _n2_spec is None or _n2_spec.loader is None:
            return ("KraL", "olculemedi")
        _n2_mod = _n2_ilu.module_from_spec(_n2_spec)
        _n2_spec.loader.exec_module(_n2_mod)
        _s = _n2_mod.kirmizi_sahibi(repo_koku, sha)
        return (_s.get("SAHIP") or "KraL", _s.get("SEBEP") or "olculemedi")
    except Exception:
        return ("KraL", "olculemedi")


''' + GOZCU_SON

# (anchor, yeni_metin) ciftleri. Her capa TAM ESLESMELIDIR; biri bayatsa
# yama YAPILMAZ (yanlis yere enjekte etmek kapiyi korlestirir).
GOZCU_YAMALARI = (
    ("def kalp_satiri(kalp):",
     GOZCU_KOPRU + "\n\ndef kalp_satiri(kalp):"),
    ('"KAT_MIMAR=%d KAT_OKAN=%d GUNLUK=%d ARTIK_SILINEN=%d CI_SEBEP=%s rc=%d") % (',
     '"KAT_MIMAR=%d KAT_OKAN=%d GUNLUK=%d ARTIK_SILINEN=%d CI_SEBEP=%s rc=%d '
     'SAHIP=%s SEBEP=%s") % ('),
    ("        int(kalp.get(\"rc\") or 0),\n    )",
     "        int(kalp.get(\"rc\") or 0),\n"
     "        kalp.get(\"sahip\") or \"-\",\n"
     "        kalp.get(\"sahip_sebep\") or \"-\",\n    )"),
    ('    kalp = {\n        "damga": _damga(simdi),',
     "    # N2 (A): kirmizi kosumun SAHIBI — harita TEK KAYNAK.\n"
     "    n2_sahip = (\"-\", \"-\")\n"
     "    if tetik == \"CI_KIRMIZI\" and yeni:\n"
     "        n2_sahip = n2_sahip_coz(yeni[0].get(\"sha\"))\n"
     "        if n2_sahip[1] == \"olculemedi\":\n"
     "            rc = max(rc, 1)   # harita/git olculemedi -> GOZCU KIRMIZI\n"
     "\n"
     '    kalp = {\n        "damga": _damga(simdi),\n'
     '        "sahip": n2_sahip[0],\n'
     '        "sahip_sebep": n2_sahip[1],'),
)


def gozcu_yamala(metin):
    """Gozcu kaynagina N2 sahip koprusunu uygular.

    Return: (yeni_metin, durum). durum: "ZATEN TAM" | "YAMALANDI" |
            "CAPA-BULUNAMADI(<capa>)". SAF FONKSIYON — dosyaya DOKUNMAZ,
    boylece kabul testi HERMETIK bir kopya uzerinde ayni yamayi olcebilir.
    """
    if GOZCU_BAS in metin:
        return metin, "ZATEN TAM"
    for capa, yeni in GOZCU_YAMALARI:
        if metin.count(capa) != 1:
            return metin, "CAPA-BULUNAMADI(%s)" % capa[:48]
    for capa, yeni in GOZCU_YAMALARI:
        metin = metin.replace(capa, yeni, 1)
    return metin, "YAMALANDI"


def _gozcu_dosya_yamala(yol, uygula):
    if not os.path.isfile(yol):
        return "GOZCU-YOK"
    try:
        metin = _oku(yol)
    except Exception as e:
        return "GOZCU-OKUNAMADI(%r)" % e
    yeni, durum = gozcu_yamala(metin)
    if durum in ("ZATEN TAM",) or durum.startswith("CAPA-BULUNAMADI"):
        return durum
    if not uygula:
        return "EKLENECEK"
    try:
        shutil.copyfile(yol, yol + ".yedek-n2-sahip-" +
                        time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
        _yaz(yol, yeni)
    except Exception as e:
        return "YAZILAMADI(%r)" % e
    return "KURULDU"


def _parti_ev_cozulur_mu(kok):
    """Bu depo koku T4'un EV_DIZIN'inde bir EV'e coz(ulebil)iyor mu?

    parti-kapisi.py'nin KENDI `ev_coz`unu cagirir — kurucu ikinci bir ev
    tablosu TUTMAZ. Return: (EV|None, hata|None)."""
    try:
        _spec = importlib.util.spec_from_file_location(
            "pruvo_n2b_kapi", PARTI_KAPISI_KAYNAK)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        return _mod.ev_coz(kok)
    except Exception as e:
        return None, "parti-kapisi.py yuklenemedi: %r" % e


def _parti_t4_dogrula(hedef):
    """Dagitilan kopya BAGIMLILIGIYLA (T4) birlikte CALISIYOR mu?

    🔴 20 Agu 2026 (canli bloker): kopya `<ev>/.claude/` altina konur, T4
    (`parti-borc-kapisi.py`) kardes DEGILDIR. Dosyanin var olmasi kapinin
    kostugunu KANITLAMAZ — 20 Agu'da tam bu fark yuzunden bes evin isci hatti
    `N2B-OLCULEMEDI` ile oldu ve dagitim raporu yine de "KURULDU" yaziyordu.
    Bu yuzden kopya CALISTIRILIR [[aracin-teshis-cumlesi-olcum-degil]].

    Return: "T4-OK" | "T4-KIRIK(...)" | "HEDEF-YOK" | "T4-OLCULEMEDI(...)"
    """
    if not os.path.isfile(hedef):
        return "HEDEF-YOK"
    try:
        p = subprocess.run([sys.executable, hedef, "--t4-durum"],
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        return "T4-OLCULEMEDI(%s: %s)" % (type(e).__name__, e)
    ham = ((p.stdout or "") + (p.stderr or "")).strip().replace("\n", " ⏎ ")
    if p.returncode == 0 and "DURUM=YUKLENDI" in ham:
        return "T4-OK"
    return "T4-KIRIK(rc=%d %s)" % (p.returncode, ham[-320:] or "(cikti yok)")


def _parti_isci_sh_yamala(yol, uygula):
    """isci.sh govdesine markerli blogu ekler. Idempotent + yedekli.

    Ekleme noktasi: ETIKET normalizasyonundan SONRA, ilk `TARAYICI_TURU=false`
    satirindan ONCE (o noktada MOTOR/EV_KOKU/SPEC/ETIKET degiskenleri DOLU).
    """
    if not os.path.isfile(yol):
        return "ISCI-SH-YOK"
    try:
        metin = _oku(yol)
    except Exception as e:
        return "ISCI-SH-OKUNAMADI(%r)" % e
    if PARTI_BAS in metin:
        return "ZATEN TAM"
    capa = "TARAYICI_TURU=false"
    if capa not in metin:
        # Capa bayatladi: SESSIZ EKLEME YOK (yanlis yere enjekte etmek
        # degiskensiz bir baglamda kapiyi korlestirir).
        return "CAPA-BULUNAMADI(%s)" % capa
    if not uygula:
        return "EKLENECEK"
    try:
        shutil.copyfile(yol, yol + ".yedek-n2-parti-" +
                        time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
        yeni = metin.replace(capa, PARTI_ISCI_BLOK + "\n\n" + capa, 1)
        _yaz(yol, yeni)
    except Exception as e:
        return "YAZILAMADI(%r)" % e
    return "KURULDU"


def _parti_ev_settings(kok, goreli, uygula):
    """Evin .claude/settings.json'una Bash matcher'li PreToolUse kancasi ekler.
    Additive + idempotent + yedekli."""
    yol = os.path.join(kok, ".claude", "settings.json")
    if not os.path.exists(yol):
        return "settings-yok"
    try:
        veri = json.loads(_oku(yol))
    except Exception:
        return "settings-bozuk"
    kancalar = veri.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if not isinstance(kancalar, list):
        return "PreToolUse-bozuk"
    blok = _matcher_blogu(kancalar, PARTI_MATCHER)
    if _blokta_hook_var(blok, PARTI_KAPISI_ADI):
        return "zaten"
    if not uygula:
        return "EKLENECEK"
    komut = 'python3 "${CLAUDE_PROJECT_DIR:-.}/' + goreli + '" --kanca'
    shutil.copyfile(yol, yol + ".yedek-n2-parti-" +
                    time.strftime("%Y%m%d-%H%M%S"))
    if blok is None:
        blok = {"matcher": PARTI_MATCHER, "hooks": []}
        kancalar.append(blok)
    blok.setdefault("hooks", []).append(
        {"type": "command", "command": komut, "timeout": 30,
         "statusMessage": "N2 parti kapisi"})
    _yaz(yol, json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
    try:
        json.loads(_oku(yol))
    except Exception:
        return "yazim-bozuk"
    return "kuruldu"


def parti_kapisi(uygula):
    """N2 (B) parti kapisini isci.sh'e + cozulebilen her eve kurar/dogrular."""
    print("N2 PARTI KAPISI DAGITIMI (Okan onayli doktrin, 19 Agu 2026)")
    print("KAYNAK: " + PARTI_KAPISI_KAYNAK)
    print("MOD: " + ("UYGULA" if uygula else "KURU KOSUM (degisiklik yok)"))
    print("")

    if not os.path.isfile(PARTI_KAPISI_KAYNAK):
        print("KAYNAK YOK — dagitim YAPILAMAZ: " + PARTI_KAPISI_KAYNAK)
        print("KURULU_EV=0/0")
        sys.exit(1)

    # --- YUZEY 1: isci.sh (CRON'u da kapsar) --------------------------------
    # 🔴 `ISCI_SARMALAYICI_YOLU` bu dosyada MODUL SABITI DEGILDIR — o ad
    # `ISCI_TANIM_SABLON` metninin ICINDE gecer (evlere enjekte edilen kod).
    # Modul duzeyindeki gercek sabit `ISCI_SARMALAYICI_YOLU_SABIT`tir.
    isci_durum = _parti_isci_sh_yamala(ISCI_SARMALAYICI_YOLU_SABIT, uygula)
    print("YUZEY 1  isci.sh  %-46s %s"
          % (ISCI_SARMALAYICI_YOLU_SABIT, isci_durum))

    # --- YUZEY 3: gozcu.py (N2-A sahip koprusu) -----------------------------
    gozcu_durum = _gozcu_dosya_yamala(GOZCU_YOLU, uygula)
    print("YUZEY 3  gozcu.py %-46s %s" % (GOZCU_YOLU, gozcu_durum))
    print("")

    # --- YUZEY 2: evler ------------------------------------------------------
    kapsam, kapsam_disi = [], []
    for ad, kok, _goreli, mod in CODEX_EVLER:
        if not os.path.isdir(kok):
            kapsam_disi.append((ad, kok, "EV YOK"))
            continue
        ev, hata = _parti_ev_cozulur_mu(kok)
        if ev is None:
            kapsam_disi.append((ad, kok, "EV COZULEMEDI: %s" % (hata or "-")))
            continue
        kapsam.append((ad, kok, ev, mod))

    print("%-8s %-10s %-34s %-9s %s"
          % ("KURUCU", "T4-EV", "KOK", "MOD", "DURUM"))
    print("-" * 96)
    eksik = 0
    for ad, kok, ev, mod in kapsam:
        rapor = []
        if mod == "kaynak":
            goreli = "tools/" + PARTI_KAPISI_ADI
            hedef = os.path.join(kok, goreli)
            kopya = "ZATEN TAM" if os.path.isfile(hedef) else "KAYNAK-DOSYA-YOK"
        else:
            goreli = ".claude/" + PARTI_KAPISI_ADI
            hedef = os.path.join(kok, goreli)
            try:
                kaynak_metin = _oku(PARTI_KAPISI_KAYNAK)
                var = os.path.isfile(hedef) and _oku(hedef) == kaynak_metin
            except Exception:
                var = False
            if var:
                kopya = "ZATEN TAM"
            elif not uygula:
                kopya = "KOPYALANACAK"
            else:
                try:
                    os.makedirs(os.path.dirname(hedef), exist_ok=True)
                    if os.path.isfile(hedef):
                        shutil.copyfile(hedef, hedef + ".yedek-n2-parti-" +
                                        time.strftime("%Y%m%d-%H%M%S"))
                    shutil.copyfile(PARTI_KAPISI_KAYNAK, hedef)
                    kopya = "KURULDU"
                except Exception as e:
                    kopya = "KOPYALANAMADI(%r)" % e
        kablo = _parti_ev_settings(kok, goreli, uygula)
        # 🔴 Dosya YERINDE olmasi YETMEZ: bagimliligi (T4) yuklenebiliyor mu?
        t4 = (_parti_t4_dogrula(hedef) if kopya in ("ZATEN TAM", "KURULDU")
              else "-")
        tam = (kopya in ("ZATEN TAM", "KURULDU")
               and kablo in ("zaten", "kuruldu")
               and t4 == "T4-OK")
        if not tam:
            eksik += 1
        print("%-8s %-10s %-34s %-9s dosya=%s | settings=%s | %s"
              % (ad, ev, kok, mod, kopya, kablo, t4))
        for satir in rapor:
            print(satir)

    for ad, kok, neden in kapsam_disi:
        print("%-8s %-10s %-34s %-9s KAPSAM_DISI: %s"
              % (ad, "-", kok, "-", neden))

    print("-" * 96)
    print("KAPSAM_DISI_EV=%d (yukarida satirlariyla YAZILDI — sessiz kirpma yok)"
          % len(kapsam_disi))
    print("TAM OLMAYAN EV: %d" % eksik)
    print("ISCI_SH=%s" % isci_durum)
    print("GOZCU=%s" % gozcu_durum)
    print("KURULU_EV=%d/%d" % (len(kapsam) - eksik, len(kapsam)))
    if not uygula:
        print("Kuru kosum. Uygulamak icin ayni komuta --uygula ekle.")
    print("Dogrula: python3 " + os.path.join(
        os.path.dirname(os.path.abspath(__file__)), PARTI_KAPISI_ADI)
        + " --kendini-test")
    iyi = ("ZATEN TAM", "KURULDU", "EKLENECEK")
    sys.exit(0 if (eksik == 0 and isci_durum in iyi and gozcu_durum in iyi)
             else 1)


def main():
    global AYAR, PRECOMMIT
    argv = sys.argv[1:]
    uygula = "--uygula" in argv
    if "--ayar" in argv:  # test/kuru kosum icin baska bir settings.json'a isaret et
        AYAR = argv[argv.index("--ayar") + 1]
    if "--precommit" in argv:  # kabul testi kendi HERMETIK kopyasini gosterir
        PRECOMMIT = argv[argv.index("--precommit") + 1]

    if "--durum" in argv:  # SALT-OKUNUR: settings.json'a YAZMAZ
        durum()

    if "--izinler" in argv:  # 26 Tem: codex belgeleyici izin satirlari
        izinler(uygula)

    if "--codex-kurali" in argv:  # 27 Tem (BaBa hukmu): kural 6 EVE
        codex_kurali(uygula)

    if "--agent-kapisi" in argv:  # 28 Tem (BaBa hukmu): AGENT-KAPISI 6 EVE
        agent_kapisi(uygula)

    if "--mcp-kapisi" in argv:  # 8 Agu (Okan teftisi K17): MCP-TARAYICI KAPISI 6 EVE
        mcp_kapisi(uygula)

    if "--isci-kapisi" in argv:  # 13 Agu (goc karari): ISCI-SARMALAYICI KAPISI 6 EVE
        isci_kapisi(uygula)

    if "--sablon-yayimla" in argv:  # 20 Agu (K250): istisnayi COMMIT'LENEN sablon tasisin
        sablon_yayimla(uygula)

    if "--parti-kapisi" in argv:  # 19 Agu (Okan doktrini): N2 PARTI KAPISI
        parti_kapisi(uygula)

    if not os.path.exists(AYAR):
        print("BULUNAMADI: " + AYAR)
        sys.exit(1)

    ham = io.open(AYAR, encoding="utf-8").read()
    veri = json.loads(ham)

    # 28 TEM: kanca IKI matcher'a baglanir — Bash (mevcut) + Agent|Task (AGENT-KAPISI).
    # Ikisi de mimar-icra-kapisi.py'ye gider; AYRI blok cunku Bash-ozel nobetciler
    # (komut-stili/urunler-guard) Agent/Task'a KOSMAMALI. Additive + idempotent: her iki
    # blok da BAGIMSIZ denetlenir; hangisi eksikse yalniz o eklenir (early-exit yalnizca
    # IKISI DE varsa).
    kancalar = veri.setdefault("hooks", {}).setdefault("PreToolUse", [])
    bash_blogu = _matcher_blogu(kancalar, "Bash")
    agent_blogu = _matcher_blogu(kancalar, AGENT_MATCHER)
    bash_var = _blokta_hook_var(bash_blogu, "mimar-icra-kapisi.py")
    agent_var = _blokta_hook_var(agent_blogu, "mimar-icra-kapisi.py")

    if bash_var and agent_var:
        print("ZATEN KURULU (Bash + Agent/Task) — degisiklik yok. "
              "Dogrula: python3 tools/mimar-kilit-test.py")
        sys.exit(0)

    print("PreToolUse/Bash        mimar-icra-kapisi.py: " + ("var" if bash_var else "EKLENECEK"))
    print("PreToolUse/" + AGENT_MATCHER + "  mimar-icra-kapisi.py: " +
          ("var" if agent_var else "EKLENECEK"))
    print("SILINEN/DEGISEN         : YOK (arac yalnizca ekler)")

    if not uygula:
        print("")
        print("Kuru kosum. Uygulamak icin: python3 " + os.path.abspath(__file__) + " --uygula")
        sys.exit(0)

    if not bash_var:
        if bash_blogu is None:
            bash_blogu = {"matcher": "Bash", "hooks": []}
            kancalar.append(bash_blogu)
        bash_blogu.setdefault("hooks", []).append(KAYIT)
    if not agent_var:
        if agent_blogu is None:
            agent_blogu = {"matcher": AGENT_MATCHER, "hooks": []}
            kancalar.append(agent_blogu)
        agent_blogu.setdefault("hooks", []).append(AGENT_KAYIT)

    yedek = AYAR + ".yedek"
    shutil.copyfile(AYAR, yedek)
    io.open(AYAR, "w", encoding="utf-8").write(
        json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
    # yazilanin gecerli JSON oldugunu teyit et, degilse yedegi geri koy
    try:
        json.loads(io.open(AYAR, encoding="utf-8").read())
    except Exception as hata:
        shutil.copyfile(yedek, AYAR)
        print("BOZUK JSON URETILDI — yedek geri konuldu. Hata: " + str(hata))
        sys.exit(1)
    print("")
    print("KURULDU (Bash + Agent/Task). Yedek: " + yedek)
    print("Dogrula: python3 /Users/okan/dev/pruvo/tools/mimar-kilit-test.py")
    print("NOT: kanca yeni oturumda etkin olur.")


if __name__ == "__main__":
    main()
