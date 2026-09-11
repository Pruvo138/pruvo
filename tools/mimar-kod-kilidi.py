#!/usr/bin/env python3
"""PreToolUse kilidi (Edit|Write|MultiEdit): mimar oturumu kaynak/veri dosyasini
degistiremez VE calistirilabilir betik YAZAMAZ.

20 Tem guclendirmesi (KraL teshisi): eski surum yalnizca REPO ICINDEKI dosyalari
denetliyordu; scratchpad muafiyeti (".md spec yazsin diye" konmustu) keyfi program
yazarligina donusmustu — mimar /private/tmp/.../scratchpad/ altina .py yaziyor, sonra
Bash'ten 'python3 /tam/yol.py' ile kosturuyordu; repoya tek satir girmedigi icin kilit
hic yanmiyordu. Artik calistirilabilir uzanti KONUMDAN BAGIMSIZ reddedilir.
Ikinci ayak: tools/mimar-icra-kapisi.py (Bash) — repo disi betigi kosturmayi engeller.

20 Tem KALIBRASYONU — KIMLIK EKSENI (olculmus ariza: kapi mesru MUHENDIS ajanlarini da
kilitliyordu; 4 kez mesru isi engelledi, bir isci sed'e kacti = kapi guvenligi AZALTTI):
  * PreToolUse stdin JSON'unda `agent_id` DOLU ise cagri bir ALT AJANDAN gelmistir →
    kapi (cekirdek liste disinda) hicbir sey yapmaz.
  * agent_id kabuktan/env'den/cwd'den BESLENMEZ; Claude Code process'i icinde uretilir.
    agent_id tasimayan isci.sh ana oturumu icin ikinci eksen, ortak mimar_kimlik.py'deki
    KAPALI motor kumesine civilenmis PRUVO_ISCI_KOSUMU'dur. Bos/bilinmeyen deger
    fail-closed MIMAR kalir; cwd ve agent_type kimlik olarak kullanilmaz.
  * CEKIRDEK liste kimlikten BAGIMSIZDIR: ana repodaki kapi/kablo dosyalari kimse
    tarafindan degistirilemez. Kapi bakimi zaten WORKTREE'de yapilir; worktree
    kopyalari serbesttir.

MUAF KALAN (bilerek — kapatirsan mimarin isi durur):
  * .md her yerde (spec, DEVAM.md, hafiza, isci raporu) — mimarin ASIL isi
  * scratchpad'de VERI/NOT dosyalari (.txt/.json — commit mesaji, olcum notu)
  * worktree'ler: /Users/okan/dev/pruvo/.claude/worktrees/ ONEKI + git'e KAYITLI
    worktree kokleri (or. /private/tmp/pruvo-toka-jenerator) — mesru muhendis alani

BILINEN BYPASS (kapi disiplin cihazidir, hapishane DEGIL — memory/kapi-disiplin-ilkesi.md;
kayitli olmasi sart):
  * UZANTISIZ (shebang'li) betik yazimi: yasak ICRA_UZANTILARI listesine dayanir, yani
    uzantisiz bir ad (or. Write ile "analiz" + shebang) YAKALANMAZ. Bu yuzden "calistirilabilir
    betik YAZAMAZ" iddiasi TAM DEGIL — kapsam uzanti-tabanlidir. Ayni kök, icra kapisinin
    uzantisiz +x dosyayi dogrudan cagrida kacirmasiyla birdir. Kapatilmadi: uzanti listesini
    genisletmek veri/not dosyasi adlarinda yanlis-pozitif riski (disiplin cihazi, sinir degil).
  * 'git worktree add /private/tmp/x' TEK komutla kalici muaf bolge acar (yeni kok
    .git/worktrees'e kaydolur → worktree_ici() true doner). BILEREK kapatilmadi:
    git yonetimi mimarin kapisidir. Olcum: 'git worktree list' cikti sayisi.
  * agent_id DOLU cagri (alt ajan) CEKIRDEK disinda hicbir kurala tabi degildir.
"""
import json
import os
import sys

from mimar_kimlik import kimlik_ekseni

# Calistirilabilir uzantilar: KONUMDAN BAGIMSIZ yasak (scratchpad dahil).
ICRA_UZANTILARI = (
    ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".sh", ".bash", ".zsh", ".command",
)

REPO_ONEKI = "/Users/okan/dev/pruvo/"
WT_ONEK = "/Users/okan/dev/pruvo/.claude/worktrees/"
GIT_WORKTREE_KAYIT = "/Users/okan/dev/pruvo/.git/worktrees"

# ANA REPODAKI kapi + kablo dosyalari: KIMLIKTEN BAGIMSIZ kilitli. Isci de degistiremez.
# (Kapi bakim isi worktree'de yapilir; oradaki kopya serbesttir — vaka 72.)
# NOT: bu BILINCLI bir yanlis-pozitiftir; "isci bloklanmis" diye sokulmemeli.
# 20 Tem ONARIMI: liste NOBETCILERI de kapsar. Olculmus acik — eski liste yalnizca
# kapilarin KENDISINI koruyordu; kapiyi YALANCI yapan yol nobetciden geciyordu:
# kabul testini/mutasyon takimini/envanteri sessizce degistiren biri kapiyi hic
# ellemeden yesil yakar. urunler-guard + .git/hooks/pre-commit ayni sinifta: veri
# duzleminin ve commit zincirinin canli kablosu.
# MALIYET OLCUMU: bu genisletme HICBIR mesru ana-checkout isci vakasini bloklamaz —
# kaynak isi zaten ana checkout'ta COMMIT'lenemez (commit kapisi), worktree kopyasi
# serbesttir (vaka 72), ve pre-commit hook'u Write ile degil kurucu araciyla kurulur.
CEKIRDEK = {
    "/Users/okan/dev/pruvo/.claude/settings.json",
    "/Users/okan/dev/pruvo/.claude/settings.local.json",
    "/Users/okan/dev/pruvo/tools/mimar-kod-kilidi.py",
    "/Users/okan/dev/pruvo/tools/mimar_kimlik.py",
    "/Users/okan/dev/pruvo/tools/mimar-icra-kapisi.py",
    "/Users/okan/dev/pruvo/tools/mimar-commit-kapisi.py",
    "/Users/okan/dev/pruvo/tools/mimar-kapi-kur.py",
    "/Users/okan/dev/pruvo/tools/mimar-kilit-test.py",
    "/Users/okan/dev/pruvo/tools/id-rename-test.py",
    # NOBETCILER (kapiyi yalanci yapabilen dosyalar)
    "/Users/okan/dev/pruvo/tools/mimar-kapi-mutasyon-test.py",
    "/Users/okan/dev/pruvo/tools/mimar-commit-kapisi-test.py",
    "/Users/okan/dev/pruvo/tools/mimar-commit-kapisi-mutasyon.py",
    "/Users/okan/dev/pruvo/tools/kapi-envanteri.py",
    "/Users/okan/dev/pruvo/tools/urunler-guard.py",
    # CANLI KABLO
    "/Users/okan/dev/pruvo/.git/hooks/pre-commit",
    # CANLI PreToolUse/Bash ZINCIRI (20 Tem, B8): ikisi de settings.json'da KAYITLI ve
    # calisiyor; pre-commit'in kendi yorumu urunler-guard-hook.py'yi "birincil koruma"
    # diye adlandirir. CEKIRDEK'te olmadiklari icin tek Write ile susturulabiliyorlardi.
    # MALIYET OLCULDU: hicbir mesru isci vakasi bloklanmaz — ikisi de tools/*.py yani
    # KAYNAK'tir, ana checkout'ta zaten commit'lenemez (commit kapisi; env=worker
    # kaynagi acmaz), gelistirme yolu worktree'dir ve worktree kopyalari SERBEST kalir.
    "/Users/okan/dev/pruvo/tools/urunler-guard-hook.py",
    "/Users/okan/dev/pruvo/tools/komut-stili-kapisi.py",
}


def kimlik(girdi):
    return "ISCI" if kimlik_ekseni(girdi) is not None else "MIMAR"


def iz_bas(etiket):
    """ALLOW kararinda stderr'e TEK SATIR iz. stdout BOS kalir — allow karari
    stdout'a JSON olarak BASILMAZ ki zincirdeki baska kapilarin deny'ini ezmesin.
    Bu iz sayesinde kabul testi 'kapi kostu ve izin verdi' ile 'kapi yok/coktu'
    durumunu ayirt edebilir (eski fail-open korlugu)."""
    try:
        sys.stderr.write("MIMAR-KAPISI allow " + etiket + "\n")
    except Exception:
        pass


def kayitli_worktree_kokleri():
    """.git/worktrees/*/gitdir dosyalarindan worktree koklerini okur.
    Icerik '<kok>/.git' → dirname = kok. HATA olursa BOS kume (eski/dar davranisa
    dus, asla cokme)."""
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


def worktree_ici(yol):
    """ONEK + KAYIT birlesimi.
    ONEK tek basina yetmez: kayitli ama repo DISINDAKI worktree'ler var
    (olculdu: /private/tmp/pruvo-toka-jenerator).
    KAYIT tek basina yetmez: diskte canli ama kayitsiz mesru dizinler var
    (olculdu: .claude/worktrees/toka-fizik-analiz).
    Eski surum burada ALT-DIZE testi yapiyordu ('/.claude/worktrees/' in fp) →
    '/tmp/x/.claude/worktrees/kotu.py' gibi SAHTE yollar muafti (vaka 80/81)."""
    yol = os.path.normpath(yol)
    if yol.startswith(WT_ONEK):
        return True
    for kok in kayitli_worktree_kokleri():
        if yol == kok or yol.startswith(kok + "/"):
            return True
    return False


def reddet(gerekce):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": gerekce,
        }
    }, ensure_ascii=False))
    sys.exit(0)


# === 11 EYL 2026 — MIMAR KOD YAZIMI SAYACI (kilit yerine GORUNURLUK) ==============
# 🔴 Kilit kalktiginda gorunurluk de kalkarsa "mimar eli surmez" ilkesi OLCULEMEZ hale
# gelir ve ilke sessizce OLUR. O yuzden her yazim SAYILIR; kapanista tek satir basilir.
# Sayac oturum-bazlidir (kardes kapi `cip-kapanis-kancasi.py::_sayac` ile AYNI desen ve
# AYNI dizin). DISK KURALI (Okan 13 Agu, "makinede iz birakma"): `--rapor --temizle`
# raporu bastiktan SONRA oturum dosyasini SILER; kapanis yordami o bicimi cagirir.
SAYAC_DIZIN = os.path.expanduser("~/.claude/cron/mimar-kod-yazdi")


def _sayac_yolu(session_id):
    ad = "".join(k for k in str(session_id or "bilinmeyen")
                 if k.isalnum() or k in "-_")[:80] or "bilinmeyen"
    return os.path.join(SAYAC_DIZIN, ad + ".tsv")


def _kod_yazimi_kaydet(girdi, fp):
    """Bir mimar kod yazimini sayaca EKLE. Diske yazilamazsa SESSIZ gecer —
    sayac bir RAPOR ekseni, KARAR ekseni degil; yazamamak yazmayi engellemez."""
    try:
        os.makedirs(SAYAC_DIZIN, exist_ok=True)
        with open(_sayac_yolu(girdi.get("session_id")), "a", encoding="utf-8") as f:
            f.write("%s\t%s\n" % (girdi.get("tool_name") or "?", fp))
    except OSError:
        pass


def _rapor_bas(session_id, temizle=False):
    """`MIMAR_KOD_YAZDI=<n dosya>` — TEKIL dosya sayisi (ayni dosyaya 5 Edit = 1 dosya).
    Dosya yoksa 0 basar: "olculmedi" ile "yazmadi" ayrimini SESSIZ BIRAKMAMAK icin
    kaynak yolu da basilir."""
    yol = _sayac_yolu(session_id)
    dosyalar = []
    try:
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                parca = satir.rstrip("\n").split("\t")
                if len(parca) >= 2 and parca[1] not in dosyalar:
                    dosyalar.append(parca[1])
    except OSError:
        pass
    print("MIMAR_KOD_YAZDI=%d dosya  kaynak=%s" % (len(dosyalar), yol))
    for d in dosyalar:
        print("  * " + d)
    if temizle:
        try:
            os.remove(yol)
            print("SAYAC_TEMIZLENDI=1 (disk kurali: makinede iz birakma)")
        except OSError:
            print("SAYAC_TEMIZLENDI=0 (dosya yok ya da silinemedi)")
    return 0


# `--rapor` KIPI: stdin OKUNMADAN once ele alinir (kanca kipi stdin bekler, rapor kipi
# BEKLEMEZ — karistirilirsa kapanis yordami bir boru olur ve asilir).
if "--rapor" in sys.argv[1:]:
    _oturum = None
    _argv = sys.argv[1:]
    if "--oturum" in _argv:
        _i = _argv.index("--oturum")
        if _i + 1 < len(_argv):
            _oturum = _argv[_i + 1]
    sys.exit(_rapor_bas(_oturum, temizle=("--temizle" in _argv)))


try:
    girdi = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# NOT (20 Tem, mimar sorusu (a)): burada bir ara "cwd/CLAUDE_PROJECT_DIR worktree
# icindeyse TAM MUAF" seklinde bir OTURUM muafiyeti vardi. KALDIRILDI — cwd kaydirilabilir
# bir sinyal (kabuk cwd'si cagrilar arasi kalici, 'cd' makine olarak engellenmiyor, gercek
# worktree dizinleri diskte duruyor) → "cd <worktree>" tek komutluk muafiyet anahtari olurdu.
# Ortak kimlik ekseni bunun yerini alir: agent_id ya da kapali-kumeli isci sarmalayici izi.
fp = (girdi.get("tool_input") or {}).get("file_path") or ""
if not fp:
    sys.exit(0)

fp = os.path.normpath(fp)

# 0) CEKIRDEK: ana repodaki kapi/kablo dosyalari — KIMLIKTEN BAGIMSIZ deny.
if fp in CEKIRDEK:
    reddet(
        "MİMAR KAPISI — kapı/kablo dosyaları ana repoda kilitlidir (kimlikten bağımsız). "
        "Kapı işini KENDİ WORKTREE'NDE yap; oradaki kopya serbesttir."
    )

# 1) KIMLIK: agent_id doluysa cagri ALT AJANDAN gelir → mesru muhendis, kural uygulanmaz.
if kimlik(girdi) == "ISCI":
    iz_bas("ISCI")
    sys.exit(0)

# 2) Worktree'ler (Agent isolation:worktree) mesru muhendistir — TAM muaf.
#    Bu kontrol icra-uzantisi kontrolunden ONCE gelmeli: muhendis .py yazabilmeli.
#    agent_id ekseni bir surumde olurse sistem BURAYA duser (bugunku bilinen davranis),
#    "her sey mimar" felaketine degil.
if worktree_ici(fp):
    iz_bas("MIMAR-worktree")
    sys.exit(0)

# 3) Calistirilabilir betik yazarligi: KILIT KALKTI -> RAPOR (11 Eyl 2026, OKAN EMRI).
#
# 🔴 OKAN (11 Eyl, birebir): "tum tikayicilari kaldir".
# OLCULEN ARIZA (11 Eyl, bu kapinin KENDI canli kopyasi tarafindan uretildi): hazir
# bir 4 satirlik yamayi uygulayamadim ve bir CIPE devretmek zorunda kaldim = TUR KAYBI.
# Ayni tur icinde bu kilit bir OLCUM betigini scratchpad'e yazmayi da reddetti; betik
# worktree'ye yazilinca gecti — yani kilit isi ENGELLEMIYOR, sadece PAHALILASTIRIYORDU.
#
# 🔴 "MIMAR ELI SURMEZ" YORDAM ILKESI OLARAK KALIR (kral-yordam ④'te yazili), MAKINE
# KILIDI OLARAK DEGIL. Kilit yerine GORUNURLUK: her mimar kod yazimi SAYILIR ve
# kapanista `MIMAR_KOD_YAZDI=<n dosya>` diye basilir (`--rapor`). Gorunur kalsin,
# engellenmesin.
#
# ⚠️ KAPSAM — BU KOLDA DEGISEN TEK SEY ICRA UZANTISI YASAGIDIR. AYNEN KALAN kollar
# (bilerek, hepsi "yanlis isi yakalayan" siniftan):
#   * 0) CEKIRDEK: ana repodaki kapi/kablo/nobetci dosyalari KIMLIKTEN BAGIMSIZ kilitli.
#        Sebep: bir nobetciyi sessizce degistirmek kapiyi ellemeden YESIL yakar; mesru
#        yol (worktree kopyasi) ZATEN ACIK, yani bu kol tikayici DEGIL.
#   * 6) `urunler.json` / `.urun-kaynaklari.json`: veri butunlugu, MaCiT duzlemi
#        (`urunler-guard.py` + `duzelt.py` tek mesru yol) — AYRI kalem, KALIR.
#   * 6) `.html` / `.css` / `.sql` ve `.claude/settings*.json`: Okan emri kapsaminda
#        ADIYLA ANILMADI; hatasi sessizce CANLI SITEYE gider. Kapsam disi, KALIR.
#
# 🔴 SIRA TUZAGI (olculdu, bu turda yakalandi): asagidaki `sys.exit(0)` kolu
# adim 6'daki KAPI-ADI KALKANINI (`basename == "mimar-kod-kilidi.py"` /
# `"mimar-icra-kapisi.py"`) ERISILMEZ kilardi — o kalkan tam da "uzanti kurali bir
# gun daralirsa kapilar yine korunur" diye konmus bir REGRESYON KALKANIDIR ve bugun
# uzanti kurali TAM OLARAK daraldi. Kalkan bu yuzden adim 3'UN ONUNE alindi; CEKIRDEK
# (adim 0) kanonik ana-checkout yollarini, bu kol ise ADIN KENDISINI korur
# ([[cagri-yeri-envanterden-duserse-onarildi-sanilir]] sinifi).
if os.path.basename(fp) in ("mimar-kod-kilidi.py", "mimar-icra-kapisi.py"):
    reddet(
        "MİMAR KAPISI — kapı dosyasının KENDİSİ (" + os.path.basename(fp) + "). "
        "11 Eyl 2026'da çalıştırılabilir betik yazma yasağı KALKTI, ama kapıların "
        "kendini koruması KALDI: kapı işini KENDİ WORKTREE'NDE yap, oradaki kopya "
        "serbesttir."
    )

if fp.lower().endswith(ICRA_UZANTILARI):
    _kod_yazimi_kaydet(girdi, fp)
    iz_bas("MIMAR-KOD-YAZDI " + fp)
    sys.exit(0)

# 4) Not/spec/veri dosyalari: serbest (mimarin asil isi).
if fp.endswith(".md"):
    iz_bas("MIMAR-kural-yok")
    sys.exit(0)

# 5) Scratchpad muafiyeti YALNIZ veri/not dosyalari icin (betikler yukarida elendi).
if fp.startswith("/private/tmp/") and "/scratchpad/" in fp:
    iz_bas("MIMAR-kural-yok")
    sys.exit(0)
if "/scratchpad/" in fp and "/claude-" in fp:
    iz_bas("MIMAR-kural-yok")
    sys.exit(0)

# 6) Repo disindaki diger dosyalar (hafiza dosyalari vb.) bu kilidin konusu degil.
if not fp.startswith(REPO_ONEKI):
    iz_bas("MIMAR-kural-yok")
    sys.exit(0)

basename = os.path.basename(fp)
blocked = (
    fp.endswith(".html")
    or fp.endswith(".css")
    or fp.endswith(".sql")
    or basename == "urunler.json"
    or basename == ".urun-kaynaklari.json"
    or fp.endswith("/.claude/settings.json")
    or fp.endswith("/.claude/settings.local.json")
    # Kapilar kendilerini korur. (Uzanti kurali ve CEKIRDEK zaten yakalar; acik kayit =
    #  regresyon kalkani: uzanti listesi bir gun daralirsa kapilar yine korunur.)
    or basename == "mimar-kod-kilidi.py"
    or basename == "mimar-icra-kapisi.py"
)

if blocked:
    reddet(
        "MİMAR KOD-KİLİDİ (Okan 18 Tem): kaynak/veri dosyasına Edit/Write YASAK — işi "
        "emekli motor'e ya da worktree worker'a DELEGE et, spec'i .md dosyasına yaz. Kilidin "
        "kendisini de değiştiremezsin. İzinli: *.md, scratchpad'de veri/not dosyaları, "
        "worktree'ler."
    )
iz_bas("MIMAR-kural-yok")
sys.exit(0)
