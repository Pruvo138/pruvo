#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/icra-kapisi.py — PreToolUse kancasi: ANA OTURUMDA `Agent` alt-ajani REDDEDILIR.

═══════════════════════════════════════════════════════════════════════════════
NEDEN VAR (Okan penceresi, 4 Eyl 2026)
═══════════════════════════════════════════════════════════════════════════════
4 Eyl 2026'da KraL ANA oturumunda icra `Agent` alt-ajaniyla acildi. Bu YASAK:
dogru arac `mcp__ccd_session__spawn_task` ([[chip-penceresini-okana-actirma]],
Okan emri 20 Agu 2026). Ihlali yakalayacak MAKINE kolu YOKTU — 29 Agu supurmesinde
rol/kilit kapilari `settings.json`'dan cikarilmisti ve CLAUDE.md'nin kendi satiri
bunu yaziyordu: "kurallar davranis kurali olarak gecerli, ZORLAYICISI YOK".
Ihlali INSAN (Okan) yakaladi. Okan'in hukmu: kapiyi SINIF olarak geri kur, ve
RED metni dogru araci ADIYLA soylesin.

`Agent` alt-ajani neden cip DEGILDIR ([[agent-altajani-cip-degildir]], 4 Eyl):
  * Okan'in panelinde YOK — sahiplenilemez, tiklanamaz, arsivlenemez;
  * `tools/cip-kapanis-kancasi.py` menzilinde YOK (settings.json'da `Stop` bagli,
    `SubagentStop` DEGIL) — kapanmadan dusebilir;
  * ama kutuya `BASLIYORUM` yazarsa `ACIK_BASLIYORUM` sayacini KIRLETIR.

═══════════════════════════════════════════════════════════════════════════════
IKI EMNIYET — CELISMEZLER (Okan sarti)
═══════════════════════════════════════════════════════════════════════════════
1. CANLI KANCA FAIL-OPEN, ISTISNASIZ. Bu kanca bu evin HER tool cagrisinda kosar
   (matcher "*"). Catlarsa evi KILITLEMEZ: her hata yolu (bozuk stdin, import
   hatasi, git kaydi okunamamasi, beklenmedik istisna) BLOKLAMADAN gecer.
   `main()` govdesinin tamami tek bir `except Exception` ile sarilidir ve o kol
   `GECER_HATA` dondurur.
2. AMA KENDI BATARYASI FAIL-CLOSED. `icra-kapisi-test.py` icinde bilinmeyen /
   ucuncu hal YESIL DEGIL KIRMIZIDIR: batarya, `karar()`in dondurdugu HAL adini
   `HALLER` kumesine karsi dogrular; kumede olmayan bir ad gorurse vaka DUSER
   ([[izin-tablosu-duymadigini-kirmizi-yakmali]] ·
   [[yeni-hal-cozucunun-varsayilan-kovasina-duser]]).
   Celiski yok: CANLI KANCA AFFEDER, OLCUM AFFETMEZ.

═══════════════════════════════════════════════════════════════════════════════
OLCULEN HARNESS SOZLESMESI (4 Eyl 2026, bu makinede SONDA ile — ezber DEGIL)
═══════════════════════════════════════════════════════════════════════════════
PreToolUse stdin (JSON) UST SEVIYE ALANLARI, gercek kayittan:
    cwd · effort · hook_event_name · permission_mode · prompt_id · scratchpad_dir
    session_id · tool_input · tool_name · tool_use_id · transcript_path
  🔴 `agent_id` PreToolUse yukunde YOKTUR (sondada 25/25 cagride `null`). Kimlik
     ekseni yine de sorulur — cunku `kimlik_ekseni()` ORTAMDAN da okur
     (`PRUVO_ISCI_KOSUMU`) ve o kol isci turlarinda DOLUDUR.
  `permission_mode` bu evde "bypassPermissions".
RED SOZLESMESI (olculdu): stdout'a
    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": "<metin>"}}
  ve **exit 0**. `deny`, bu evin `PermissionRequest` kolunun kosulsuz "allow"unu
  EZER: 4 Eyl 03:36'da canli oturumda olculdu — `tools/komut-stili-kapisi.py`
  (ayni sozlesmeyi kullanan PreToolUse kancasi) bir Bash cagrisini fiilen
  REDDETTI ve modele `permissionDecisionReason` metni dondu.
GECIS SOZLESMESI: stdout BOS + exit 0.

🔴 SONDANIN IKINCI OLCUMU (kurulum tuzagi): `.claude/settings.json`'a eklenen yeni
   kanca, DUZENLEMEYI YAPAN oturumda ETKI ETMEZ (hook yapilandirmasi oturum
   basinda donuyor); ayni degisiklik KOMSU CANLI oturumlarda ANINDA etkindir
   (sonda 25 kayittan 25'ini komsu oturumlardan topladi, kendi oturumundan 0).
   Yani "kurdum, kendi oturumumda denedim, gecti" bir YESIL DEGILDIR.

═══════════════════════════════════════════════════════════════════════════════
🔴 ARAC ADI: TAM ESITLIK — ONEK/ALT-DIZE/REGEX **YASAK**
═══════════════════════════════════════════════════════════════════════════════
Alt-ajan aracinin GERCEK adi 1365 transcript taranarak olculdu (ezberden degil):
    Agent                        3570 cagri   <- YASAKLANAN
    TaskCreate/TaskList/TaskOutput/TaskStop/TaskUpdate   597 cagri  <- SERBEST
`Task` adinda bir arac bu evde HIC gorulmedi; ama spec onu da yasakladigi icin
kumede DURUR. 🔴 Eger eslesme "Task ile baslayan" ya da `Agent|Task` REGEX'i olarak
yazilsaydi, arka plan gorev araclarinin BESI birden bloklanirdi — bu, kapinin
kendisinden daha buyuk bir ariza olurdu. Bu yuzden eslesme `frozenset` uyeligi ile
TAM ESITLIKTIR ve mutant M4 bunu olcer.
Ayni sebeple `settings.json` matcher'i "*"dir (sondayla Bash/Read/TaskStop
uzerinde fiilen dogrulandi) ve arac secimi BU GOVDEDE yapilir: olculmemis bir
matcher regex semantigine kapi emanet EDILMEZ ([[kapinin-menzili-cagri-yeridir]]).

═══════════════════════════════════════════════════════════════════════════════
🔴 ROL EKSENI — K203 TUZAGI (onek DEGIL, CAGRI BAGLAMI)
═══════════════════════════════════════════════════════════════════════════════
Muafiyet ROLE baglidir: ANA CHECKOUT'taki mimar oturumu RED alir, cip/worktree
oturumu ALMAZ. Rol cozumu `tools/mimar_kimlik.py::rol_ekseni`den TURETILIR —
bu govdede IKINCI bir "cip mi" testi YOKTUR ([[ikiz-tanim-sessiz-ayrisma]]).

K203'un olctugu kusur: kapi worktree ICINDEN cagrildiginda rol eksenini
KAYBEDIYORDU; sebep dizin oneki degil CAGRI BAGLAMIDIR. Bu makinede sondayla
dogrulandi: bir CIP oturumunda kancaya gecen ortam
    ENV_CLAUDE_PROJECT_DIR = /Users/okan/dev/pruvo/.claude/worktrees/<cip>
    cwd                    = /Users/okan/dev/pruvo/.claude/worktrees/<cip>
olur. Yani `${CLAUDE_PROJECT_DIR}` ile kurulan bir kanca, cip oturumunda
WORKTREE'DEKI (bayat ya da hic olmayan) kopyayi calistirir ve ana checkout'un
`.git/worktrees` kaydini goremez. KORUNMA, UC KATLI:
  (a) `settings.json` kaydi MUTLAK yoldur (`${CLAUDE_PROJECT_DIR}` KULLANILMAZ);
  (b) ev koku `__file__`ten turetilir — kurulu kopya kendi evini kendi soyler,
      cagiranin cwd'sinden DEGIL;
  (c) `.git/worktrees` kaydi (b)'deki MUTLAK ev kokunden okunur.
`os.environ`in `CLAUDE_PROJECT_DIR`i, `cwd` alani ve `os.getcwd()` rol kararinda
HIC OKUNMAZ — kaydirilabilir sinyaller ([[mimar_kimlik]] bas yorumu).

═══════════════════════════════════════════════════════════════════════════════
KAPSAM — NE YAPMAZ
═══════════════════════════════════════════════════════════════════════════════
* `SubagentStop` kancaya BAGLANMAZ (Okan bu secenegi secmedi). `Agent` ile acilmis
  bir isin kapanis kancasi menzilinde olmamasi kalemi ACIK kalir.
* Baska evleri (or. `~/dev/pruvo-hasat`) kapatmaz: her ev kendi kopyasini kurar,
  ve bu kopya kendi evi disindaki cagriya HUKUM VERMEZ (`GECER_BASKA_EV`).
* Bir DISIPLIN cihazidir, hapishane degil (memory/kapi-disiplin-ilkesi.md).
"""
import json
import os
import sys

# --- EV KOKU: kurulu kopya kendi evini KENDI konumundan soyler (K203/(b)) -----
def ev_kokunu_coz(baslangic):
    """`<x>/tools/icra-kapisi.py` konumundan EVIN ANA CHECKOUT kokunu turet.

    🔴 K203'UN CEKIRDEGI. Bir worktree'de `.git` bir DIZIN degil, icinde
    `gitdir: /<ana>/.git/worktrees/<ad>` yazan bir DOSYADIR. Naif turetim
    (`dirname(dirname(__file__))`) worktree kopyasi calistirildiginda WORKTREE
    kokunu verir; orada `.git/worktrees` YOKTUR, kayit okunamaz ve kapi sessizce
    `GECER_OLCULEMEDI_KAYIT`e duserek INERT olurdu — kusur "onek" degil
    CAGRI BAGLAMIDIR. Bu cozucu `.git` dosyasini okuyup ANA checkout'a geri
    doner, boylece worktree ICINDEN cagrilan kopya da rolu DOGRU cozer.
    Cozulemezse baslangic kokunu dondurur (fail-open zincirini bozmaz).
    """
    kok = os.path.dirname(os.path.dirname(os.path.realpath(baslangic)))
    git = os.path.join(kok, ".git")
    if os.path.isdir(git):
        return kok                                   # zaten ANA checkout
    try:
        with open(git, encoding="utf-8") as f:
            satir = f.read().strip()
    except Exception:
        return kok
    if not satir.startswith("gitdir:"):
        return kok
    gitdir = os.path.normpath(satir.split(":", 1)[1].strip())
    # <ana>/.git/worktrees/<ad>  ->  <ana>
    ust = os.path.dirname(os.path.dirname(os.path.dirname(gitdir)))
    return ust if os.path.isdir(os.path.join(ust, ".git", "worktrees")) else kok


EV_KOKU = ev_kokunu_coz(__file__)

# 🔴 TAM ESITLIK KUMESI — onek/alt-dize/regex DEGIL. Gerekce bas yorumda.
ALT_AJAN_ARACLARI = frozenset({"Agent", "Task"})

DOGRU_ARAC = "mcp__ccd_session__spawn_task"
GEREKCE_HAFIZASI = "chip-penceresini-okana-actirma"

# --- HALLER: batarya bu kumeye karsi dogrular; kumede olmayan ad KIRMIZI ------
# Tek RED hali `RED_ANA_OTURUM`dur; geri kalan her sey GECER. `GECER_OLCULEMEDI_*`
# kollari BILEREK gecirir (emniyet 1); bataryada bunlar AYRI vakalardir ve
# "olculemedi"nin sessizce `GECER_CIP`e karismadigi ORADA civilenir.
HALLER = frozenset({
    "GECER_ARAC_DISI",          # tool_name alt-ajan kumesinde degil
    "GECER_ISCI",               # kimlik ekseni ISCI (agent_id / PRUVO_ISCI_KOSUMU)
    "GECER_BASKA_EV",           # cagri bu evin disindan
    "GECER_CIP",                # rol = kayitli bir worktree koku
    "GECER_OLCULEMEDI_ROL",     # transcript damgasi yok -> fail-open
    "GECER_OLCULEMEDI_KAYIT",   # .git/worktrees okunamadi/bos -> fail-open
    "GECER_HATA",               # kancanin kendi istisnasi -> fail-open
    "RED_ANA_OTURUM",           # TEK RED
})
RED_HALLERI = frozenset({"RED_ANA_OTURUM"})


def kayitli_worktree_kokleri(ev_koku):
    """`<ev>/.git/worktrees/*/gitdir` → worktree kokleri.

    Doner: (kokler_kumesi, okundu_mu). `okundu_mu=False` "OLCEMEDIM" demektir ve
    bos kumeden AYRIDIR: bos kume "hic worktree yok" (mesru hal), okunamama ise
    olcum arizasidir. Ikisini tek kovaya atmak, [[iki-kovali-siniflama-ucuncu-
    sinifi-yutar]] sinifinin ta kendisi olurdu.

    🔴 ATLATILAN ATALET TUZAGI (merge oncesi kuru kosumda yakalandi): git, SON
    worktree kaldirildiginda `.git/worktrees` DIZININI SILER. "dizin yok" hali
    "okunamadi" sayilsaydi, evde hic cip agaci kalmadigi anda kapi
    `GECER_OLCULEMEDI_KAYIT`e duser ve TAM DA korumasi gereken durumda —
    mimarin yalniz ana checkout'ta calistigi anda — INERT olurdu
    ([[yeni-hal-cozucunun-varsayilan-kovasina-duser]]). Dogru okuma: `.git` bir
    DIZINSE repo saglamdir, `worktrees` yoksa "HIC WORKTREE YOK" demektir ve rol
    OLCULEBILIR (her oturum ANA'dir). `okundu=False` yalnizca repo kokunun
    kendisi cozulemediginde ya da gercek bir I/O hatasinda donulur.
    """
    git = os.path.join(ev_koku, ".git")
    if not os.path.isdir(git):
        return set(), False                     # burasi bir repo koku DEGIL
    kayit_dizini = os.path.join(git, "worktrees")
    kokler = set()
    if not os.path.exists(kayit_dizini):
        return kokler, True                     # HIC worktree yok — olculdu, bos
    try:
        adlar = os.listdir(kayit_dizini)
    except Exception:
        return kokler, False                    # gercek I/O arizasi
    for ad in adlar:
        try:
            with open(os.path.join(kayit_dizini, ad, "gitdir"), encoding="utf-8") as f:
                icerik = f.read().strip()
        except Exception:
            continue
        if not icerik:
            continue
        kok = os.path.normpath(os.path.dirname(icerik))
        if kok and kok != "/":
            kokler.add(kok)
    return kokler, True


def _ev_icinde_mi(yol, ev_koku):
    """`yol` bu evin agaci icinde mi? Bilesen sinirina saygili (onek testi DEGIL:
    `/dev/pruvo-hasat`, `/dev/pruvo`nun oneki DEGILDIR)."""
    try:
        y = os.path.realpath(yol)
        e = os.path.realpath(ev_koku)
    except Exception:
        return None
    return y == e or y.startswith(e + os.sep)


def karar(girdi, ev_koku=EV_KOKU, ortam=None, rol_coz=None, kimlik_coz=None):
    """TEK KARAR NOKTASI. Doner: (HAL, red_metni_ya_da_None).

    `rol_coz`/`kimlik_coz` yalniz BATARYA icin enjekte edilir; canlida `None`
    birakilir ve `mimar_kimlik`ten cozulur. Enjeksiyon noktasi olmasaydi mutantlar
    hedefe ULASAMAZDI ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
    """
    ad = girdi.get("tool_name")
    if ad not in ALT_AJAN_ARACLARI:            # TAM ESITLIK — mutant M4 olcer
        return "GECER_ARAC_DISI", None

    # --- kimlik ekseni: ISCI cagrisi kapidan TAM muaf -------------------------
    if kimlik_coz is None or rol_coz is None:
        tools = os.path.join(ev_koku, "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        import mimar_kimlik                     # ImportError -> disaridaki fail-open
        kimlik_coz = kimlik_coz or mimar_kimlik.kimlik_ekseni
        rol_coz = rol_coz or mimar_kimlik.rol_ekseni

    if kimlik_coz(girdi, os.environ if ortam is None else ortam) is not None:
        return "GECER_ISCI", None

    # --- SIRA ONEMLIDIR (batarya bunu ORTAYA CIKARDI) ------------------------
    # ROL once, EV MENZILI sonra. Ters sirada, bu evin `.git/worktrees`ine KAYITLI
    # ama ev agacinin DISINDA duran bir worktree (git buna izin verir:
    # `git worktree add /private/tmp/x`) `GECER_BASKA_EV` diye siniflanirdi.
    # Ikisi de GECER oldugu icin ariza SESSIZ kalirdi — ve `GECER_CIP` kolu
    # bataryada HIC uretilmedigi icin cip muafiyetini olduren mutant "hedefe
    # ULASMADI" verirdi ([[ad-iki-rolde-mutanti-golgeler]]). Once ROL sorulur:
    # "bu evin KAYITLI bir agacindan mi geliyor" sorusunun EVET cevabi kesindir.
    kokler, okundu = kayitli_worktree_kokleri(ev_koku)
    yol = girdi.get("transcript_path")
    if okundu and isinstance(yol, str) and yol.strip():
        if rol_coz(girdi, kokler) is not None:
            return "GECER_CIP", None

    # --- ev menzili: baska evin cagrisina HUKUM VERILMEZ ----------------------
    # Buraya gelen cagri bu evin kayitli bir agacindan GELMIYOR; oyleyse cwd
    # ev disindaysa hukum baska evin kapisinindir.
    cwd = girdi.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        if _ev_icinde_mi(cwd, ev_koku) is False:
            return "GECER_BASKA_EV", None

    # --- UCUNCU HALLER: olculemedi, `GECER_CIP` ile ASLA ayni ada dusmez ------
    # Sessiz karisma tam olarak [[olculemedi-bypass-degil-menzil-daraltmasi]]'nin
    # yasakladigi seydir: canlida gecirilir (emniyet 1) ama ADI AYRIDIR ve
    # bataryada AYRI vakasi vardir.
    if not okundu:
        return "GECER_OLCULEMEDI_KAYIT", None
    if not isinstance(yol, str) or not yol.strip():
        return "GECER_OLCULEMEDI_ROL", None

    return "RED_ANA_OTURUM", red_metni()


def red_metni():
    """RED metni: (a) kural, (b) DOGRU ARAC adiyla, (c) gerekce hafizasi adiyla.

    🔴 Uc jeton da METINDE BIREBIR bulunur; batarya ucunu de ARAR
    ([[kapi-red-metni-ikinci-kopyadir]]: metin ikinci bir kopyadir, olculmezse
    ayrisir). Jetonlar sabitlerden TURETILIR, elle yazilmaz."""
    return (
        "ICRA KAPISI — RED: mimarin ANA OTURUMUNDA `Agent` alt-ajani ile is "
        "acilmaz.\n"
        "KURAL (Okan, 20 Agu 2026): icra CIP+worktree'de kosar; cip Okan'in "
        "panelinde dogar, o sahiplenir/arsivler.\n"
        "DOGRU ARAC: " + DOGRU_ARAC + " — `Agent` DEGIL. `Agent` alt-ajani CIP "
        "DEGILDIR: Okan'in panelinde gorunmez ve cip kapanis kancasinin menzili "
        "disindadir (settings.json'da `Stop` bagli, `SubagentStop` DEGIL); "
        "kutuya BASLIYORUM yazarsa ACIK_BASLIYORUM sayacini kirletir.\n"
        "GEREKCE HAFIZASI: " + GEREKCE_HAFIZASI + " (govdesini AC — indeks "
        "basligiyla yetinmek bu ihlalin kok sebebiydi).\n"
        "CIP/worktree oturumlari bu kapidan MUAFTIR; muafiyet dizin onegine "
        "degil OTURUM ROLUNE baglidir."
    )


def main():
    """Kancanin giris noktasi. TAMAMI fail-open: hicbir hata bloklamaz."""
    try:
        girdi = json.load(sys.stdin)
        if not isinstance(girdi, dict):
            raise ValueError("stdin dict degil")
        hal, metin = karar(girdi)
    except Exception:                                  # noqa: BLE001 — EMNIYET 1
        _iz("GECER_HATA")
        return 0

    if hal in RED_HALLERI:
        sys.stdout.write(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": metin,
            }
        }, ensure_ascii=False) + "\n")
        return 0

    _iz(hal)
    return 0


def _iz(hal):
    """ALLOW kararinda stderr'e TEK SATIR iz; stdout BOS kalir.

    "Kapi kostu ve gecirdi" ile "kapi yok/coktu" ayrimini bu satir kurar —
    aksi halde `stdout bos => allow` fail-open korlugu olurdu (ayni cozum
    `mimar-icra-kapisi.py::iz_bas`ta da var). Arac disi cagrilarda SUSAR:
    bu kanca HER tool cagrisinda kosar, her birine satir basmak stderr'i bogardi.
    """
    if hal == "GECER_ARAC_DISI":
        return
    try:
        sys.stderr.write("ICRA-KAPISI allow " + hal + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
