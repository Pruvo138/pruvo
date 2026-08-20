#!/usr/bin/env python3
"""K250 — ISCI-SARMALAYICI ISTISNASININ TASIYICISINI olcen kapi.

ARIZA (MaCiT bildirdi, KraL uc bacakta dogruladi, 20 Agu 2026):
  pruvo-hasat ana checkout DISK kopyasi : ISCI damgasi VAR, index 'S' (skip-worktree)
  ayni yol `git show HEAD:`             : damga YOK  — istisna git'e HIC girmemis
  canli worktree macit-audi-gorsel-gate : damga YOK, index 'H'
Yani istisna YALNIZ ana checkout'un disk kopyasinda yasiyordu. `git worktree add` ile
dogan HER agac istisnasiz doguyor, worktree-koklu mimar oturumu `isci.sh` ile hicbir
delegasyon YAPAMIYOR.

HUKUM (K250): care kurulum betigine `git worktree list` taramasi EKLEMEK DEGIL — o, her
worktree DOGUMUNDA yarisan tekil yamadir. Istisnayi COMMIT'LENEN SABLON tasiyacak
(ev-goreli / expanduser cozumleme; makineye cakili mutlak yol DEGIL), kurulum betigi TEK
TASIYICI olmayacak. Boylece yeni dogan her worktree istisnayi HAZIR alir.

BU KAPI NEYI OLCER: hukmun kendisini — TAZE BIR WORKTREE'DEN yapilan cagri-yeri probunu.
Kapinin menzili CAGRI YERIDIR ([[kapinin-menzili-cagri-yeridir]]): ana checkout'ta yesil
yanan kural worktree'de hic kosmuyor olabilir; bu yuzden batarya kendi hermetik "ev"ini
kurar, ONU commit'ler, `git worktree add` ile TAZE bir agac dogurur ve kapiyi O AGACIN
KOKUNDEN kosturur.

  python3 tools/isci-sablon-kapisi.py --kendini-test   # hermetik batarya (mutantli)
  python3 tools/isci-sablon-kapisi.py --durum          # 6 evin HEAD hali (SALT OKUNUR)

DORT CIVI (memory dersleri, bilerek yazildi):
  1. HUKUM IMZADAN OKUNUR, rc KOLUNDAN ONCE ([[rc-hukmu-kapi-imzasini-ezer]]). Kapi
     reddederken de rc=0 doner; karar stdout'taki permissionDecision'dir. rc yalnizca
     imza BOSSA (COKTU) konusur.
  2. PROB KENDI BAGLAMINI OLCMEZ ([[prob-kendi-baglamini-olcer]]). Prob ISCI kimliginde
     kurulmaz: payload'da `agent_id` YOKTUR ve ortamdan `PRUVO_ISCI_KOSUMU` /
     `CLAUDE_AGENT_ID` / `PRUVO_CLAUDE_ISCI_IZNI` SOKULUR. Sokum VARSAYILMAZ, DOGRULANIR:
     I6 pozitif kontrolu ayni komutu eksen ACIKKEN kosar; sonuc degismezse eksen zaten
     etkisizdi ve sokum bir sey KANITLAMIYOR demektir -> iddia KIRMIZI.
  3. NEGATIF TABAN sarttir. FAZ A, istisnayi tasimayan (bugunku gercek) sablonla ayni
     probu kosar ve RED bekler. A kirmizi yanarsa FAZ B'nin yesili TAUTOLOJIDIR
     ([[sahte-bagimlilik-sekli-negatif-blogu-kutsar]]).
  4. MUTANTIN YASAMASI "kol saglam" DEGIL "kol OLCULEMEDI"dir
     ([[ad-iki-rolde-mutanti-golgeler]]). Her mutant once metinde TEK eslesme oldugunu
     dogrular, sonra derlenir; ikisinden biri tutmazsa OLCULEMEDI yazilir, YESIL YAZILMAZ.

KAPSAM DISI HALI (K248 hal ayrimi deseni): batarya taban sablonunu GERCEK bir enjekte
evinden alir. Hicbir kardes ev bu makinede yoksa (ornegin CI kosucusu) bu KUSUR DEGILDIR
-> `KAPSAM_DISI` yazilir ve cikis 0 olur. Ev VAR ama sablon okunamiyorsa KUSURDUR.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUR_YOLU = os.path.join(KOK, "tools", "mimar-kapi-kur.py")

# Prob ortamindan SOKULEN kimlik degiskenleri (civi 2). Bu liste kapinin kimlik
# eksenini olusturan HER kaynagi kapsar; biri unutulursa prob kendi baglamini olcer.
KIMLIK_DEGISKENLERI = ("PRUVO_ISCI_KOSUMU", "CLAUDE_AGENT_ID", "PRUVO_CLAUDE_ISCI_IZNI")


def _kur_modulu():
    """mimar-kapi-kur.py'yi MODUL olarak yukler — sablon/enjeksiyon kodu IKIZLENMEZ.
    Bu batarya kuralin kendi metnini yeniden yazsaydi, gercek kurulum hattiyla sessizce
    ayrisir ve 'yesil' derken baska bir sablonu olcerdi."""
    spec = importlib.util.spec_from_file_location("mimar_kapi_kur", KUR_YOLU)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _git(kok, *args):
    return subprocess.run(["git", "-C", kok] + list(args),
                          capture_output=True, text=True)


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


# ============================== CAGRI-YERI PROBU ==============================

def prob(kapi_yolu, kok, komut, agent_id=None, eksen_env=None):
    """Kapiyi GERCEK PreToolUse payload'uyla, VERILEN KOKTEN kosturur.

    Doner: (hukum, rc, imza)
      hukum : "allow" / "deny" / "COKTU" / "PARSE-HATASI"
      imza  : kapinin kendi cikti metni (karar buradan okunur)

    🔴 SIRA CIVILI: imza ONCE okunur, rc SONRA. Kapi reddederken rc=0 doner; rc'den
    hukum cikarmak "ONARILDI" yanilgisini uretir ([[rc-hukmu-kapi-imzasini-ezer]]).
    """
    payload = {
        "session_id": "k250-cagri-yeri-probu",
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
    for ad in KIMLIK_DEGISKENLERI:          # civi 2 — kimlik ekseni SOKULUR
        ortam.pop(ad, None)
    ortam.update(eksen_env or {})           # pozitif kontrol bunu KASITLA geri koyar
    try:
        sonuc = subprocess.run([sys.executable, kapi_yolu], input=json.dumps(payload),
                               capture_output=True, text=True, env=ortam, cwd=kok)
    except Exception as hata:
        return "COKTU", -1, "subprocess: " + str(hata)[:80]
    imza = (sonuc.stdout or "").strip()
    if imza:
        try:
            veri = json.loads(imza)
        except Exception:
            return "PARSE-HATASI", sonuc.returncode, imza[:160]
        hukum = ((veri.get("hookSpecificOutput") or {}).get("permissionDecision")
                 or "allow")
        return hukum, sonuc.returncode, imza[:160]
    # imza BOS: ancak simdi rc konusur.
    if sonuc.returncode != 0:
        return "COKTU", sonuc.returncode, ("stderr: " + (sonuc.stderr or "").strip())[:160]
    return "allow", sonuc.returncode, "(imza yok = izin)"


def _prob_kimligi_sokuk_mu():
    """Sokumun KENDISINI dogrular: prob ortaminda kimlik degiskeni KALMAMIS olmali.
    Doner: (bool, kalanlar)."""
    ortam = dict(os.environ)
    for ad in KIMLIK_DEGISKENLERI:
        ortam.pop(ad, None)
    kalan = [ad for ad in KIMLIK_DEGISKENLERI if ad in ortam]
    return (not kalan), kalan


# ============================== HERMETIK EV FIKSTURU ==============================

def _kapsam_disi_provasi(kur):
    """CI kolunun ayagi: kardes ev YOKKEN taban sablonu None doner mi?

    🔴 NEDEN OLCULUR: bu batarya `nobet.yml` SERIT B'de kosuyor ve GitHub kosucusunda
    hicbir kardes ev YOK — yani orada HER ZAMAN bu kol calisir. Kol olculmemis olsaydi
    "CI'da yesil" beyani, aslinda hic kosmamis (ya da patlayan) bir koldan gelirdi.
    Prova GERCEK: ev listesi VAR OLMAYAN koklere cevrilir, uydurma bir bayrakla dal
    zorlanmaz. Doner: (bool, aciklama)."""
    sahte = tuple((ad, os.path.join(tempfile.gettempdir(), "pruvo-k250-ev-yok", ad),
                   goreli, mod) for ad, _kok, goreli, mod in kur.CODEX_EVLER)
    ad, metin, _g, _k = _taban_sablonu(kur, sahte)
    if metin is None and ad is None:
        return True, "ev yokken taban=None -> KAPSAM_DISI kolu (rc=0)"
    return False, "ev yokken taban DOLU dondu (%s) — KAPSAM_DISI kolu OLCULEMEDI" % ad


def _taban_sablonu(kur, evler=None):
    """TABAN sablon = GERCEK bir enjekte evinin kapi dosyasi, ISCI bloklari SOKULMUS.
    Yani 'bugun taze bir worktree'nin gordugu' metnin ta kendisi.

    Doner: (ad, metin, goreli, kaynak_kok) ya da (None, None, None, None) -> KAPSAM_DISI.
    """
    for ad, kok, _goreli, mod in (evler if evler is not None else kur.CODEX_EVLER):
        if mod != "enjekte" or not os.path.isdir(kok):
            continue
        goreli, _kablo = kur._kapi_yolu_olc(kok)
        if goreli is None:
            continue
        yol = os.path.join(kok, goreli)
        if not os.path.exists(yol):
            continue
        metin = _oku(yol)
        temiz = kur._blogu_sok(metin, kur.ISCI_TANIM_BAS, kur.ISCI_TANIM_SON)
        temiz = kur._blogu_sok(temiz, kur.ISCI_KIMLIK_CAGRI_BAS, kur.ISCI_KIMLIK_CAGRI_SON)
        temiz = kur._blogu_sok(temiz, kur.ISCI_CAGRI_BAS, kur.ISCI_CAGRI_SON)
        if kur.ISCI_DAMGA in temiz:
            continue                      # sokum tutmadi — bu evi TABAN yapma
        return ad, temiz, goreli, kok
    return None, None, None, None


def _fikstur_ev(dizin, goreli, taban_metni, ev_dizin_adi):
    """Hermetik 'ev' deposu kurar: izlenen kapi dosyasi + kablolu settings.json.

    🔴 DIZIN ADI KAYNAK EVIN ADIYLA AYNI OLMAK ZORUNDA. Kapinin `EV_ADI`'si
    `CLAUDE_PROJECT_DIR`'den turer (`_repo_kok`), yani FIKSTUR KOKUNUN adindan. Ad
    uydurulursa (`ev`) `SERT_BLOK_EVLER` uyelik ekseni degisir ve kurulumun kendi
    fiksturu `claude`+beyanli vakasinda deny yerine allow olcup enjeksiyonu GERI ALIR.
    Olculdu: ilk turda tam bu oldu ([[prob-kendi-baglamini-olcer]] — prob kendi
    baglamini olcerse taban degil kendi kurgusunu olcer)."""
    kok = os.path.join(dizin, ev_dizin_adi)
    os.makedirs(os.path.join(kok, os.path.dirname(goreli)), exist_ok=True)
    _yaz(os.path.join(kok, goreli), taban_metni)
    ayar_dizini = os.path.join(kok, ".claude")
    os.makedirs(ayar_dizini, exist_ok=True)
    _yaz(os.path.join(ayar_dizini, "settings.json"), json.dumps({
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
            "type": "command",
            "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/' + goreli + '"',
        }]}]}
    }, ensure_ascii=False, indent=2) + "\n")
    _git(kok, "init", "-q", "-b", "main")
    _git(kok, "config", "user.email", "k250@pruvo.local")
    _git(kok, "config", "user.name", "K250 Fikstur")
    _git(kok, "add", "-A")
    _git(kok, "commit", "-q", "-m", "taban: istisnasiz sablon")
    return kok


def _taze_worktree(kok, ad):
    """`git worktree add` ile TAZE agac dogurur — kusurun gerceklestigi tam yordam."""
    yol = os.path.join(os.path.dirname(kok), ad)
    sonuc = _git(kok, "worktree", "add", "-q", "--detach", yol, "HEAD")
    if sonuc.returncode != 0:
        return None, (sonuc.stderr or "").strip()[:120]
    return yol, ""


# ============================== IDDIA TABLOSU ==============================
# (anahtar, aciklama, komut_uretici(wt, spec), beklenen, eksen_env)
# 🔴 DARLIK iddialari (I2-I5) istisnanin GENISLEMEDIGINI olcer: yalniz TAM ESITLIKLE
# eslesen sarmalayici yolu, kapali kume motoru ve dogru argüman sayisi gecer. K250
# istisnayi TASIR, GENISLETMEZ; bu kollar dusmeden hicbir yesil anlamli degildir.

def _iddialar(kur, spec_yolu):
    W = kur.ISCI_SARMALAYICI_YOLU_SABIT
    CANLI = kur.CANLI_ISCI_MOTORLARI[0]
    return [
        ("I1", "TAZE WORKTREE: isci.sh cagrisi RED ALMIYOR (K250 hedefi)",
         lambda wt: W + " " + CANLI + " " + wt + " " + spec_yolu, "allow", None),
        ("I2", "DARLIK: repo-disi rastgele betik HALA RED",
         lambda wt: "python3 " + spec_yolu + ".sahte.py", "deny", None),
        ("I3", "DARLIK: sahte yoldaki 'isci.sh' HALA RED (basename anahtar DEGIL)",
         lambda wt: "/tmp/isci.sh " + CANLI + " " + wt + " " + spec_yolu, "deny", None),
        ("I4", "DARLIK: kapali kume DISI motor HALA RED (fail-closed)",
         lambda wt: W + " gpt-9 " + wt + " " + spec_yolu, "deny", None),
        ("I5", "DARLIK: eksik argüman HALA RED",
         lambda wt: W + " " + CANLI + " " + wt, "deny", None),
        ("I6", "KIMLIK SOKUMU DOGRULAMASI: ayni komut eksen ACIKKEN allow olmali",
         lambda wt: "python3 " + spec_yolu + ".sahte.py", "allow",
         {"PRUVO_ISCI_KOSUMU": kur.CANLI_ISCI_MOTORLARI[0]}),
        ("I7", "REGRESYON: rutin komut etkilenmedi",
         lambda wt: "ls", "allow", None),
    ]


def _tur(kapi_yolu, wt, kur, spec_yolu):
    """Bir agacta tum iddialari olcer. Doner: {anahtar: (hukum, beklenen, rc, imza)}."""
    sonuc = {}
    for anahtar, _acik, uret, beklenen, eksen in _iddialar(kur, spec_yolu):
        hukum, rc, imza = prob(kapi_yolu, wt, uret(wt), eksen_env=eksen)
        sonuc[anahtar] = (hukum, beklenen, rc, imza)
    return sonuc


# ============================== MUTANTLAR ==============================
# Her mutant: (ad, aciklama, eski_metin, yeni_metin, hedef_iddialar, yan_iddialar)
# hedef_iddialar BOS ise KONTROL mutantidir: hicbir iddia OLMEMELI.

MUTANTLAR = (
    ("M1-DARLIK-YUTMA",
     "sarmalayici yolu TAM ESITLIK yerine BASENAME ile aranirsa istisna genisler",
     "    elif argv0 == ISCI_SARMALAYICI_YOLU:",
     "    elif os.path.basename(argv0) == os.path.basename(ISCI_SARMALAYICI_YOLU):",
     ("I3",), ("I1", "I2", "I4", "I5", "I7")),
    ("M2-MOTOR-KUME-YUTMA",
     "kapali motor kumesi kolu kalkarsa bilinmeyen motor sessizce gecer",
     "    if motor not in ISCI_MOTORLARI:",
     "    if False:",
     ("I4",), ("I1", "I2", "I3", "I5", "I7")),
    ("M3-TASIYICI",
     "K250'nin TA KENDISI: istisna commit'lenen sablonda DEGILSE taze agac RED verir",
     None, None,                              # ozel: bloklar SOKULUR
     ("I1",), ("I2", "I3", "I4", "I5", "I7")),
    ("K0-KONTROL",
     "ilgisiz kol (MCP tarayici oneki) bozulunca HICBIR iddia olmemeli",
     '    "mcp__Control_Chrome__",',
     '    "mcp__Control_ChromeK0__",',
     (), ("I1", "I2", "I3", "I4", "I5", "I7")),
)


def _mutant_metni(kur, temiz_metin, eski, yeni):
    """Mutant metnini uretir. Doner: (metin, hata). Hata varsa OLCULEMEDI yazilir.
    🔴 TEK ESLESME SARTI: ad iki rolde geciyorsa mutant hedefi degil komsuyu vurur ve
    'yasadi' sonucu 'kol saglam' diye YANLIS okunur ([[ad-iki-rolde-mutanti-golgeler]])."""
    if eski is None:                          # M3: bloklari SOK (tasiyici mutanti)
        metin = kur._blogu_sok(temiz_metin, kur.ISCI_TANIM_BAS, kur.ISCI_TANIM_SON)
        metin = kur._blogu_sok(metin, kur.ISCI_KIMLIK_CAGRI_BAS, kur.ISCI_KIMLIK_CAGRI_SON)
        metin = kur._blogu_sok(metin, kur.ISCI_CAGRI_BAS, kur.ISCI_CAGRI_SON)
        if kur.ISCI_DAMGA in metin:
            return None, "blok sokumu tutmadi"
        return metin, None
    sayi = temiz_metin.count(eski)
    if sayi != 1:
        return None, "eslesme sayisi " + str(sayi) + " (1 bekleniyordu)"
    return temiz_metin.replace(eski, yeni, 1), None


# ============================== BATARYA ==============================

def kendini_test():
    print("K250 KABUL BATARYASI — ISCI-SARMALAYICI ISTISNASININ TASIYICISI")
    print("=" * 78)
    kur = _kur_modulu()

    sokuk, kalan = _prob_kimligi_sokuk_mu()
    print("PROB KIMLIGI: agent_id=YOK · sokulen ortam degiskenleri=" +
          ",".join(KIMLIK_DEGISKENLERI))
    print("SOKUM DOGRULAMASI: " + ("TEMIZ" if sokuk else "KIRMIZI kalan=" + str(kalan)))
    if not sokuk:
        print("SONUC: KIRMIZI — prob kendi baglamini olcuyor olabilir.")
        return 1

    prova_ok, prova_metni = _kapsam_disi_provasi(kur)
    print("KOSUCU PROVASI (CI kolu): " + ("✓ " if prova_ok else "🔴 ") + prova_metni)
    if not prova_ok:
        print("SONUC: KIRMIZI — CI'da kosacak kol OLCULEMEDI.")
        return 1

    ad, taban_metni, goreli, kaynak_kok = _taban_sablonu(kur)
    if taban_metni is None:
        print("")
        print("TABAN SABLONU: bu makinede hicbir enjekte evi YOK -> KAPSAM_DISI")
        print("Bu KUSUR DEGILDIR (K248 hal ayrimi): batarya gercek bir ev sablonuna")
        print("dayanir; ev yoksa olculecek sey de yoktur.")
        print("MUTANT=KAPSAM_DISI HEDEF_KOL_ATFI=KAPSAM_DISI KONTROL=KAPSAM_DISI")
        return 0
    print("TABAN SABLONU: " + ad + " evinden (" + goreli + "), ISCI bloklari SOKULMUS")

    dizin = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-k250-"))
    hatali = 0
    try:
        spec_yolu = os.path.join(dizin, "spec.md")
        _yaz(spec_yolu, "K250 prob speci.\ncodex-muafiyet: kapi olcumu — guvenlik\n")
        _yaz(spec_yolu + ".sahte.py", "print('repo disi betik')\n")

        kok = _fikstur_ev(dizin, goreli, taban_metni,
                          os.path.basename(os.path.normpath(kaynak_kok)))

        # ---------- FAZ A: NEGATIF TABAN (bugunku gercek hal) ----------
        print("")
        print("FAZ A — NEGATIF TABAN: istisna commit'lenen sablonda YOK")
        wt_a, hata = _taze_worktree(kok, "wt-taban")
        if wt_a is None:
            print("  TAZE WORKTREE ACILAMADI: " + hata + " -> OLCULEMEDI")
            return 1
        a = _tur(os.path.join(wt_a, goreli), wt_a, kur, spec_yolu)
        a_hukum, _b, a_rc, a_imza = a["I1"]
        a_beklenen = "deny"
        a_ok = (a_hukum == a_beklenen)
        print("  I1 taze worktree'den isci.sh : hukum=%s (beklenen=%s) rc=%s" %
              (a_hukum, a_beklenen, a_rc))
        print("     imza: " + a_imza[:110])
        print("  TABAN: " + ("KIRMIZI RED ✓ (prob gercekten olcuyor)" if a_ok
                             else "🔴 BEKLENEN RED GELMEDI — FAZ B'nin yesili TAUTOLOJI"))
        if not a_ok:
            hatali += 1

        # ---------- FAZ B: ONARILMIS (istisna COMMIT'LENDI) ----------
        print("")
        print("FAZ B — ONARILMIS: istisna enjekte edildi, STAGE'lendi, COMMIT'LENDI")
        rapor = []
        durum, _yedek = kur._eve_isci_enjekte(ad, kok, goreli, True, rapor)
        print("  enjeksiyon: " + durum)
        if durum != "KURULDU":
            for satir in rapor:
                print("   " + satir)
            print("  -> OLCULEMEDI")
            return 1
        kur._unskip_worktree(kok, goreli)
        _git(kok, "add", "--", goreli)
        _git(kok, "commit", "-q", "-m", "K250: istisna commit'lenen sablona tasindi")
        head_damga = kur._head_damgasi(kok, goreli)
        print("  HEAD damgasi: " + head_damga + "  (taze worktree bunu gorecek)")

        # SIZINTI — K250'nin sarti ISCI BLOGUNA dairdir; dosyanin geri kalaninda ZATEN
        # duran satirlar bu kalemin kapsami DEGIL (mutlak sayac komsuyu kirmiziya yakar,
        # [[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).
        onarilmis = _oku(os.path.join(kok, goreli))
        blok_siz = kur._sizinti_satirlari(kur._isci_blogu(onarilmis))
        onceki_siz = kur._sizinti_satirlari(taban_metni)
        eklenen_siz = kur._sizinti_satirlari(onarilmis) - onceki_siz
        print("  SIZINTI · ISCI blogunda=%d %s · yayimin EKLEDIGI=%d %s · "
              "taban zaten tasiyor=%d (AYRI kalem) · yayimin EKSILTTIGI=%d" % (
                  len(blok_siz), "✓" if not blok_siz else "🔴",
                  len(eklenen_siz), "✓" if not eklenen_siz else "🔴",
                  len(onceki_siz),
                  len(onceki_siz - kur._sizinti_satirlari(onarilmis))))
        if blok_siz or eklenen_siz:
            hatali += 1

        wt_b, hata = _taze_worktree(kok, "wt-onarilmis")
        if wt_b is None:
            print("  TAZE WORKTREE ACILAMADI: " + hata + " -> OLCULEMEDI")
            return 1
        kapi_b = os.path.join(wt_b, goreli)
        b = _tur(kapi_b, wt_b, kur, spec_yolu)
        print("")
        print("  %-4s %-6s %-8s %-4s %s" % ("IDDIA", "HUKUM", "BEKLENEN", "rc", "SONUC"))
        temiz_b = 0
        for anahtar, acik, _uret, beklenen, _eksen in _iddialar(kur, spec_yolu):
            hukum, _bek, rc, imza = b[anahtar]
            ok = (hukum == beklenen)
            temiz_b += 1 if ok else 0
            hatali += 0 if ok else 1
            print("  %-4s %-6s %-8s %-4s %s  %s" %
                  (anahtar, hukum, beklenen, rc, "✓" if ok else "🔴", acik))
        print("  TAZE_WORKTREE_IDDIA=%d/%d" % (temiz_b, len(b)))

        # ---------- MUTANTLAR ----------
        print("")
        print("MUTANTLAR — taze agactaki kapi metni uzerinde, hermetik")
        temiz_metin = _oku(kapi_b)
        mutant_gecen = atif_gecen = kontrol_gecen = 0
        mutant_top = sum(1 for m in MUTANTLAR if m[4])
        kontrol_top = sum(1 for m in MUTANTLAR if not m[4])
        for m_ad, m_acik, eski, yeni, hedefler, yanlar in MUTANTLAR:
            metin, hata = _mutant_metni(kur, temiz_metin, eski, yeni)
            if metin is None:
                print("  %-18s OLCULEMEDI (%s)" % (m_ad, hata))
                hatali += 1
                continue
            try:
                compile(metin, kapi_b, "exec")
            except SyntaxError as e:
                print("  %-18s OLCULEMEDI (derlenmedi: %s)" % (m_ad, str(e)[:50]))
                hatali += 1
                continue
            _yaz(kapi_b, metin)
            try:
                m = _tur(kapi_b, wt_b, kur, spec_yolu)
            finally:
                _yaz(kapi_b, temiz_metin)
            olen = [k for k in hedefler if m[k][0] != m[k][1]]
            yan_kirilan = [k for k in yanlar if m[k][0] != m[k][1]]
            if hedefler:
                hedef_ok = (len(olen) == len(hedefler))
                atif_ok = hedef_ok and not yan_kirilan
                mutant_gecen += 1 if hedef_ok else 0
                atif_gecen += 1 if atif_ok else 0
                hatali += 0 if atif_ok else 1
                print("  %-18s hedef=%s olen=%s %s | yan ekseni kirilan=%s %s" % (
                    m_ad, ",".join(hedefler), ",".join(olen) or "-",
                    "✓" if hedef_ok else "🔴",
                    ",".join(yan_kirilan) or "YOK", "✓" if not yan_kirilan else "🔴"))
                print("      %s" % m_acik)
            else:
                kontrol_ok = not yan_kirilan
                kontrol_gecen += 1 if kontrol_ok else 0
                hatali += 0 if kontrol_ok else 1
                print("  %-18s KONTROL: olen iddia=%s %s" % (
                    m_ad, ",".join(yan_kirilan) or "YOK",
                    "✓" if kontrol_ok else "🔴"))
                print("      %s" % m_acik)

        print("")
        print("MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d KONTROL=%d/%d" % (
            mutant_gecen, mutant_top, atif_gecen, mutant_top,
            kontrol_gecen, kontrol_top))
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
        print("TEMIZLIK: " + dizin + " -> " +
              ("SILINDI" if not os.path.exists(dizin) else "🔴 KALDI"))

    print("SONUC: " + ("YESIL" if hatali == 0 else "KIRMIZI (kusurlu iddia=%d)" % hatali))
    return 0 if hatali == 0 else 1


# ============================== DURUM (SALT OKUNUR) ==============================

_SURUM_RE = re.compile(r'ISCI_KURAL_SURUMU\s*=\s*[\'"]([^\'"]+)[\'"]')


def _isci_surumu(metin):
    """Metindeki ISCI kural SURUMU. Doner: surum dizesi ya da None (kural HIC yok).

    🔴 IKI SORU AYRI OLCULUR, cunku tek sutun ikisini YUTAR:
      (a) ISCI kurali bu kopyada HIC VAR MI  -> K250 arizasinin ekseni
      (b) VARSA hangi surum                  -> dagitim tazeligi ekseni
    Yalniz DAMGA (surum dizesi dahil) arayan bir sutun, surum yukseltilir yukseltilmez
    "kural YOK" der ve KAPI ZAYIFLADI izlenimi verir; oysa kural yerinde, yalniz eskidir.
    """
    m = _SURUM_RE.search(metin or "")
    return m.group(1) if m else None


def durum():
    """6 evin HEAD hali — TAZE BIR WORKTREE'NIN NE GORECEGI. Hicbir seye yazmaz."""
    kur = _kur_modulu()
    guncel = _isci_surumu(kur.ISCI_DAMGA)
    print("K250 DURUM — 'HEAD' sutunu TAZE WORKTREE'nin gorecegi haldir")
    print("GUNCEL SURUM (bu dalda): " + str(guncel))
    print("KURAL sutunu = ISCI kurali VAR MI (surumden BAGIMSIZ). K250 ekseni budur.")
    print("")
    bicim = "%-7s %-32s %-8s %-12s %-13s %s"
    print(bicim % ("EV", "KAPI", "MOD", "DISK", "INDEX", "HEAD (taze worktree)"))
    kuralsiz = bayat = 0
    for ad, kok, _g, mod in kur.CODEX_EVLER:
        if not os.path.isdir(kok):
            print(bicim % (ad, "-", mod, "-", "-", "EV YOK"))
            kuralsiz += 1
            continue
        goreli, _kablo = kur._kapi_yolu_olc(kok)
        if goreli is None:
            print(bicim % (ad, "?", mod, "-", "-", "OLCULEMEDI"))
            kuralsiz += 1
            continue
        yol = os.path.join(kok, goreli)
        disk = _isci_surumu(_oku(yol)) if os.path.exists(yol) else None
        liste = _git(kok, "ls-files", "-v", "--", goreli)
        satir = (liste.stdout or "").strip()
        index = ("izlenmiyor" if not satir else
                 ("skip-worktree" if satir[0] in ("S", "s") else "izlenen(" + satir[0] + ")"))
        gosterim = _git(kok, "show", "HEAD:" + goreli)
        if gosterim.returncode != 0:
            head_metni, head = None, "DOSYA-YOK"
        else:
            head_metni = gosterim.stdout or ""
            head_surum = _isci_surumu(head_metni)
            head = ("KURAL-YOK" if head_surum is None else
                    ("KURAL VAR (" + head_surum + ")" +
                     ("" if head_surum == guncel else " BAYAT")))
        if head in ("KURAL-YOK", "DOSYA-YOK"):
            kuralsiz += 1
        elif head.endswith("BAYAT"):
            bayat += 1
        print(bicim % (ad, goreli, mod, str(disk), index, head))
    toplam = len(kur.CODEX_EVLER)
    print("")
    print("HEAD_KURAL_TASIYAN_EV=%d/%d   HEAD_GUNCEL_EV=%d/%d" %
          (toplam - kuralsiz, toplam, toplam - kuralsiz - bayat, toplam))
    print("🔴 K250 ARIZASI = HEAD'de KURAL-YOK/DOSYA-YOK olan ev: %d" % kuralsiz)
    print("   O evlerde taze worktree ISTISNASIZ dogar; isci.sh delegasyonu KAPALI.")
    print("   'BAYAT' AYRI eksendir: kural YERINDE, yalniz eski surum — kapi ZAYIF DEGIL.")
    print("CARE: python3 " + KUR_YOLU + " --isci-kapisi --uygula")
    print("      python3 " + KUR_YOLU + " --sablon-yayimla --uygula   (sonra ev mimari commit'ler)")
    return 0 if kuralsiz == 0 else 1


def main():
    argv = sys.argv[1:]
    if "--kendini-test" in argv:
        sys.exit(kendini_test())
    if "--durum" in argv:
        sys.exit(durum())
    print(__doc__)
    sys.exit(0)


if __name__ == "__main__":
    main()
