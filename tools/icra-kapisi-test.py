#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/icra-kapisi-test.py — `tools/icra-kapisi.py` kabul bataryasi + mutasyon turu.

🔴 BATARYA FAIL-CLOSED (canli kanca fail-open olmasina RAGMEN — celiski YOK, bkz.
kapinin bas yorumu "IKI EMNIYET"). Uc yerde uygulanir:
  1. Her vaka, `karar()`in dondurdugu HAL adini `HALLER` kumesine karsi dogrular;
     kumede olmayan bir ad gorulurse vaka DUSER — "bilmedigim hal" YESIL DEGIL
     KIRMIZIDIR ([[izin-tablosu-duymadigini-kirmizi-yakmali]] ·
     [[yeni-hal-cozucunun-varsayilan-kovasina-duser]]).
  2. `V_HAL_KAPSAMI`: `HALLER` kumesindeki HER hal en az bir vakada FIILEN
     uretilmis olmali. Uretilmemis bir hal = olculmemis kova.
  3. Mutant, "kirmizi geldi" ile yetinmez: OLDURDUGU KOLU ADIYLA basar ve
     BEKLENEN kolun dustugu ayrica dogrulanir ([[mutant-yardimcisi-neyi-yamadigi-
     imzasindan-okunmaz]]). Taban ile AYNI sonuc = mutant hedefe ULASMADI.

Kullanim:
    python3 tools/icra-kapisi-test.py            # taban + mutasyon turu
    python3 tools/icra-kapisi-test.py --taban    # yalniz taban batarya
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

BU = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(BU, "icra-kapisi.py")
KIMLIK = os.path.join(BU, "mimar_kimlik.py")


# ---------------------------------------------------------------------------
def _yukle(yol, ad="icra_kapisi_olcum"):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _yuk(tool_name, transcript, cwd, **ek):
    """Sondayla OLCULMUS PreToolUse yuku (alanlar birebir o kayittan)."""
    y = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {},
        "transcript_path": transcript,
        "cwd": cwd,
        "session_id": "s-olcum",
        "tool_use_id": "tu-olcum",
        "prompt_id": "p-olcum",
        "permission_mode": "bypassPermissions",
        "effort": "high",
        "scratchpad_dir": "/private/tmp/olcum",
    }
    y.update(ek)
    return y


def _damga(yol):
    return "".join(k if k.isalnum() else "-" for k in yol)


# ---------------------------------------------------------------------------
# SENTETIK EV FIKSTURU — gercek git kaydi bicimiyle, realpath ile
# ([[sentetik-git-fiksturunde-realpath-sart]]: /var -> /private/var symlink'i
# eslesmeyi sessizce bozar; her yol realpath'ten gecirilir).
# ---------------------------------------------------------------------------
def ev_fiksturu_kur(taban, kapi_kaynagi):
    """Doner: (ana_kok, worktree_kok, worktree_icindeki_kapi_yolu)."""
    ana = os.path.realpath(os.path.join(taban, "ana"))
    # Gercek yerlesim: cip agaci evin ICINDE (.claude/worktrees/<ad>).
    wt = os.path.realpath(os.path.join(ana, ".claude", "worktrees", "cip-1"))
    os.makedirs(os.path.join(ana, "tools"))
    os.makedirs(os.path.join(ana, ".git", "worktrees", "cip-1"))
    os.makedirs(os.path.join(wt, "tools"))

    # <ana>/.git/worktrees/cip-1/gitdir  ->  <wt>/.git   (git'in gercek bicimi)
    with open(os.path.join(ana, ".git", "worktrees", "cip-1", "gitdir"), "w",
              encoding="utf-8") as f:
        f.write(os.path.join(wt, ".git") + "\n")
    # <wt>/.git  DOSYADIR (dizin degil) ve ana kayda geri isaret eder
    with open(os.path.join(wt, ".git"), "w", encoding="utf-8") as f:
        f.write("gitdir: " + os.path.join(ana, ".git", "worktrees", "cip-1") + "\n")

    for kok in (ana, wt):
        shutil.copy2(kapi_kaynagi, os.path.join(kok, "tools", "icra-kapisi.py"))
        shutil.copy2(KIMLIK, os.path.join(kok, "tools", "mimar_kimlik.py"))
    return ana, wt, os.path.join(wt, "tools", "icra-kapisi.py")


# ---------------------------------------------------------------------------
def vakalar(kapi_kaynagi):
    """TUM vakalari kosar. Doner: [(vaka_adi, gecti_mi, not)] ."""
    sonuc = []
    gorulen_haller = set()

    def ekle(ad, kosul, notu=""):
        sonuc.append((ad, bool(kosul), notu))

    taban = tempfile.mkdtemp(prefix="icra-kapisi-olcum-")
    try:
        ana, wt, wt_kapi = ev_fiksturu_kur(taban, kapi_kaynagi)
        mod = _yukle(os.path.join(ana, "tools", "icra-kapisi.py"), "ik_ana")
        mod_wt = _yukle(wt_kapi, "ik_wt")

        ana_tp = "/Users/x/.claude/projects/" + _damga(ana) + "/oturum.jsonl"
        cip_tp = "/Users/x/.claude/projects/" + _damga(wt) + "/oturum.jsonl"

        def karar(m, yuk, kok=None):
            hal, metin = m.karar(yuk, ev_koku=kok or ana, ortam={})
            gorulen_haller.add(hal)
            # FAIL-CLOSED 1: bilinmeyen hal -> vakayi DUSUR
            if hal not in m.HALLER:
                return "!!BILINMEYEN_HAL:" + str(hal), metin
            return hal, metin

        # === ② POZITIF: ana checkout + mimar rolu + Agent -> BLOK ============
        hal, metin = karar(mod, _yuk("Agent", ana_tp, ana))
        ekle("V1a POZITIF ana+Agent -> RED_ANA_OTURUM", hal == "RED_ANA_OTURUM", hal)
        ekle("V1b RED metninde `spawn_task` VAR",
             metin is not None and "mcp__ccd_session__spawn_task" in metin)
        ekle("V1c RED metninde gerekce hafizasi ADIYLA VAR",
             metin is not None and "chip-penceresini-okana-actirma" in metin)
        ekle("V1d RED metninde KURAL cumlesi VAR",
             metin is not None and "ANA OTURUM" in metin and "Agent" in metin)
        hal, _ = karar(mod, _yuk("Task", ana_tp, ana))
        ekle("V1e POZITIF ana+Task -> RED_ANA_OTURUM", hal == "RED_ANA_OTURUM", hal)

        # === ③a YANLIS-POZITIF: sira disi araclar GECER ======================
        for ad in ("Bash", "Read", "Edit", "Write", "Glob", "Grep"):
            hal, _ = karar(mod, _yuk(ad, ana_tp, ana))
            ekle("V2a %s (ana oturum) GECER" % ad, hal == "GECER_ARAC_DISI", hal)

        # 🔴 ONEK TUZAGI: `Task*` arka plan gorev araclari SERBEST kalmali.
        # Olculdu (1365 transcript): bu bes ad 597 kez cagrilmis; `Agent|Task`
        # REGEX'i ya da "Task ile baslayan" eslesmesi BESINI birden bloklardi.
        for ad in ("TaskCreate", "TaskList", "TaskOutput", "TaskStop", "TaskUpdate"):
            hal, _ = karar(mod, _yuk(ad, ana_tp, ana))
            ekle("V2b ONEK TUZAGI %s GECER" % ad, hal == "GECER_ARAC_DISI", hal)
        hal, _ = karar(mod, _yuk("mcp__ccd_session__spawn_task", ana_tp, ana))
        ekle("V2c DOGRU ARAC (spawn_task) GECER", hal == "GECER_ARAC_DISI", hal)

        # === ③b CIP/worktree oturumu GECER ==================================
        hal, _ = karar(mod, _yuk("Agent", cip_tp, wt))
        ekle("V3a CIP oturumu + Agent GECER", hal == "GECER_CIP", hal)

        # 🔴 SIRA CIVISI: ev agacinin DISINDA duran ama `.git/worktrees`e KAYITLI
        # bir cip de CIP'tir (git buna izin verir: `git worktree add /private/tmp/x`).
        # Ev-menzili kolu rolden ONCE sorulsaydi bu cagri `GECER_BASKA_EV` olurdu;
        # ikisi de GECER oldugu icin ariza SESSIZ kalir, `GECER_CIP` kolu hic
        # uretilmez ve M6 mutanti hedefe ULASAMAZDI. Bu vaka o sirayi civiler.
        dis_wt = os.path.realpath(os.path.join(taban, "disarda", "cip-2"))
        os.makedirs(os.path.join(dis_wt, "tools"))
        os.makedirs(os.path.join(ana, ".git", "worktrees", "cip-2"))
        with open(os.path.join(ana, ".git", "worktrees", "cip-2", "gitdir"), "w",
                  encoding="utf-8") as f:
            f.write(os.path.join(dis_wt, ".git") + "\n")
        hal, _ = karar(mod, _yuk("Agent",
                                 "/Users/x/.claude/projects/" + _damga(dis_wt) +
                                 "/o.jsonl", dis_wt))
        ekle("V3b EV DISINDAKI KAYITLI cip -> GECER_CIP (BASKA_EV degil)",
             hal == "GECER_CIP", hal)

        # === 🔴 K203: WORKTREE ICINDEN cagrilan KOPYA rolu DOGRU cozer =======
        # Ayri iddia: kapinin worktree'deki kopyasi kendi EV_KOKU'nu ANA
        # checkout'a cozmeli; cozemezse `.git/worktrees` okunamaz ve kapi
        # sessizce INERT olur (GECER_OLCULEMEDI_KAYIT).
        ekle("V4a K203 worktree kopyasi EV_KOKU -> ANA checkout",
             mod_wt.ev_kokunu_coz(wt_kapi) == ana,
             mod_wt.ev_kokunu_coz(wt_kapi))
        kokler, okundu = mod_wt.kayitli_worktree_kokleri(mod_wt.ev_kokunu_coz(wt_kapi))
        ekle("V4b K203 worktree kopyasi git kaydini OKUR", okundu and wt in kokler,
             "okundu=%s kok=%d" % (okundu, len(kokler)))
        hal, _ = karar(mod_wt, _yuk("Agent", ana_tp, ana),
                       kok=mod_wt.ev_kokunu_coz(wt_kapi))
        ekle("V4c K203 worktree kopyasi ANA'yi hala REDDEDER",
             hal == "RED_ANA_OTURUM", hal)
        hal, _ = karar(mod_wt, _yuk("Agent", cip_tp, wt),
                       kok=mod_wt.ev_kokunu_coz(wt_kapi))
        ekle("V4d K203 worktree kopyasi CIP'i GECIRIR", hal == "GECER_CIP", hal)

        # === ③c BASKA EV GECER ==============================================
        yabanci = os.path.realpath(os.path.join(taban, "baska-ev"))
        os.makedirs(yabanci)
        hal, _ = karar(mod, _yuk("Agent", "/x/projects/y/oturum.jsonl", yabanci))
        ekle("V5a BASKA EV + Agent GECER", hal == "GECER_BASKA_EV", hal)
        # Bilesen siniri: '<ana>-hasat' , '<ana>'nin oneki DEGILDIR.
        kardes = ana + "-hasat"
        os.makedirs(kardes)
        hal, _ = karar(mod, _yuk("Agent", "/x/projects/y/oturum.jsonl", kardes))
        ekle("V5b KARDES EV (ad oneki) GECER — onek testi degil",
             hal == "GECER_BASKA_EV", hal)

        # === ③e ISCI kimligi GECER ==========================================
        hal, _ = karar(mod, _yuk("Agent", ana_tp, ana, agent_id="alt-ajan-1"))
        ekle("V6a ISCI (agent_id dolu) GECER", hal == "GECER_ISCI", hal)
        h2, _ = mod.karar(_yuk("Agent", ana_tp, ana), ev_koku=ana,
                          ortam={"PRUVO_ISCI_KOSUMU": "minimax-m3"})
        gorulen_haller.add(h2)
        ekle("V6b ISCI (PRUVO_ISCI_KOSUMU) GECER", h2 == "GECER_ISCI", h2)

        # === UCUNCU HAL: OLCULEMEDI kollari AYRI ADLA gecer ==================
        yuk = _yuk("Agent", ana_tp, ana)
        yuk.pop("transcript_path")
        hal, _ = karar(mod, yuk)
        ekle("V7a transcript YOK -> GECER_OLCULEMEDI_ROL (CIP'e KARISMAZ)",
             hal == "GECER_OLCULEMEDI_ROL", hal)
        bos = os.path.realpath(os.path.join(taban, "kayitsiz"))
        os.makedirs(os.path.join(bos, "tools"))
        hal, _ = karar(mod, _yuk("Agent", ana_tp, bos), kok=bos)
        ekle("V7b .git YOK (repo koku degil) -> GECER_OLCULEMEDI_KAYIT",
             hal == "GECER_OLCULEMEDI_KAYIT", hal)

        # 🔴 ATALET CIVISI: git SON worktree kaldirilinca `.git/worktrees`
        # DIZININI SILER. O hal "okunamadi" sayilsaydi kapi, evde hic cip agaci
        # kalmadigi anda — yani mimarin YALNIZ ana checkout'ta calistigi anda —
        # sessizce INERT olurdu. Bu vaka onu civiler: worktree'siz repoda ANA
        # oturum HALA reddedilir.
        agacsiz = os.path.realpath(os.path.join(taban, "agacsiz"))
        os.makedirs(os.path.join(agacsiz, "tools"))
        os.makedirs(os.path.join(agacsiz, ".git"))          # worktrees ALT DIZINI YOK
        agacsiz_tp = "/Users/x/.claude/projects/" + _damga(agacsiz) + "/o.jsonl"
        hal, _ = karar(mod, _yuk("Agent", agacsiz_tp, agacsiz), kok=agacsiz)
        ekle("V7c WORKTREE'SIZ repo -> ANA hala RED (INERT DEGIL)",
             hal == "RED_ANA_OTURUM", hal)

        # === UCTAN UCA SOZLESME (alt surec — gercek stdout/rc) ===============
        ana_kapi = os.path.join(ana, "tools", "icra-kapisi.py")
        p = subprocess.run([sys.executable, ana_kapi], input=json.dumps(
            _yuk("Agent", ana_tp, ana)), capture_output=True, text=True, timeout=60)
        ekle("V8a UCTAN UCA RED: rc=0 (sozlesme)", p.returncode == 0, "rc=%d" % p.returncode)
        try:
            cikti = json.loads(p.stdout)
        except Exception:
            cikti = {}
        h = cikti.get("hookSpecificOutput") or {}
        ekle("V8b UCTAN UCA RED: hookEventName=PreToolUse",
             h.get("hookEventName") == "PreToolUse", str(h.get("hookEventName")))
        ekle("V8c UCTAN UCA RED: permissionDecision=deny",
             h.get("permissionDecision") == "deny", str(h.get("permissionDecision")))
        ekle("V8d UCTAN UCA RED: reason `spawn_task` tasir",
             "mcp__ccd_session__spawn_task" in str(h.get("permissionDecisionReason")))

        p = subprocess.run([sys.executable, ana_kapi], input=json.dumps(
            _yuk("Bash", ana_tp, ana)), capture_output=True, text=True, timeout=60)
        ekle("V9a UCTAN UCA GECIS: rc=0 + stdout BOS",
             p.returncode == 0 and p.stdout.strip() == "",
             "rc=%d stdout=%r" % (p.returncode, p.stdout[:40]))

        # === ③d BOZUK STDIN GECER (fail-open) ===============================
        for etiket, girdi in (("bozuk JSON", "{bu json degil"), ("bos", ""),
                              ("dizi", "[1,2,3]"), ("null", "null")):
            p = subprocess.run([sys.executable, ana_kapi], input=girdi,
                               capture_output=True, text=True, timeout=60)
            ekle("V10 BOZUK STDIN (%s) GECER: rc=0 + stdout BOS" % etiket,
                 p.returncode == 0 and p.stdout.strip() == "",
                 "rc=%d stdout=%r" % (p.returncode, p.stdout[:40]))

        # === ③e mimar_kimlik IMPORT EDILEMIYOR -> GECER (fail-open) =========
        kirik = os.path.realpath(os.path.join(taban, "kimliksiz"))
        os.makedirs(os.path.join(kirik, "tools"))
        os.makedirs(os.path.join(kirik, ".git", "worktrees"))
        shutil.copy2(kapi_kaynagi, os.path.join(kirik, "tools", "icra-kapisi.py"))
        # mimar_kimlik.py BILEREK kopyalanmadi
        p = subprocess.run(
            [sys.executable, os.path.join(kirik, "tools", "icra-kapisi.py")],
            input=json.dumps(_yuk("Agent", "/x/projects/y/o.jsonl", kirik)),
            capture_output=True, text=True, timeout=60,
            env=dict(os.environ, PYTHONPATH="", PRUVO_ISCI_KOSUMU=""))
        ekle("V11a mimar_kimlik YOK -> rc=0 + BLOKLAMAZ",
             p.returncode == 0 and p.stdout.strip() == "",
             "rc=%d stdout=%r" % (p.returncode, p.stdout[:60]))
        ekle("V11b mimar_kimlik YOK -> stderr izi GECER_HATA",
             "GECER_HATA" in p.stderr, p.stderr.strip()[:60])
        gorulen_haller.add("GECER_HATA")

        # === FAIL-CLOSED 2: HALLER kumesinin HER uyesi FIILEN uretildi mi? ===
        eksik = sorted(set(mod.HALLER) - gorulen_haller)
        ekle("V_HAL_KAPSAMI: HALLER kumesinin her uyesi uretildi",
             not eksik, "uretilmeyen=%s" % (eksik or "yok"))
        fazla = sorted(gorulen_haller - set(mod.HALLER))
        ekle("V_HAL_KAPALILIK: kume disi hal URETILMEDI",
             not fazla, "kume_disi=%s" % (fazla or "yok"))
    finally:
        shutil.rmtree(taban, ignore_errors=True)
    return sonuc


# ---------------------------------------------------------------------------
# MUTASYON TURU — her mutant HEDEF KOLU ADIYLA olduruyor mu?
# 🔴 3 Eyl dersi: mutant kaynagi kabul kosucusuna FIILEN iletilmezse dort mutant
# da "ULASMADI" verir. Burada `vakalar(kapi_kaynagi)` mutant DOSYASINI parametre
# olarak alir ve fikstur o dosyadan kurulur — iletim yolu TEK.
# ---------------------------------------------------------------------------
MUTANTLAR = [
    {
        "ad": "M1 ONEK TUZAGI: kumeye Task* araclari eklenir",
        "eski": 'ALT_AJAN_ARACLARI = frozenset({"Agent", "Task"})',
        "yeni": ('ALT_AJAN_ARACLARI = frozenset({"Agent", "Task", "TaskStop", '
                 '"TaskCreate", "TaskList", "TaskOutput", "TaskUpdate"})'),
        "hedef": "V2b ONEK TUZAGI TaskStop GECER",
    },
    {
        "ad": "M2 ROL EKSENI TERS: ANA oturum CIP sayilir",
        "eski": '    return "RED_ANA_OTURUM", red_metni()',
        "yeni": '    return "GECER_CIP", None',
        "hedef": "V1a POZITIF ana+Agent -> RED_ANA_OTURUM",
    },
    {
        "ad": "M3 UCUNCU HAL YUTULUR: kayit okunamayinca CIP denir",
        "eski": '        return "GECER_OLCULEMEDI_KAYIT", None',
        "yeni": '        return "GECER_CIP", None',
        "hedef": "V7b .git YOK (repo koku degil) -> GECER_OLCULEMEDI_KAYIT",
    },
    {
        "ad": "M4 K203 GERI SARILIR: ev koku naif turetilir (.git dosyasi okunmaz)",
        "eski": "    if os.path.isdir(git):\n        return kok",
        "yeni": "    if True:\n        return kok",
        "hedef": "V4a K203 worktree kopyasi EV_KOKU -> ANA checkout",
    },
    {
        "ad": "M7 ATALET: `worktrees` dizini yoksa 'okunamadi' sayilir",
        "eski": '    if not os.path.exists(kayit_dizini):\n        return kokler, True',
        "yeni": '    if not os.path.exists(kayit_dizini):\n        return kokler, False',
        "hedef": "V7c WORKTREE'SIZ repo -> ANA hala RED (INERT DEGIL)",
    },
    {
        "ad": "M5 RED METNI ARACI SOYLEMEZ",
        "eski": '        "DOGRU ARAC: " + DOGRU_ARAC + " — `Agent` DEGIL.',
        "yeni": '        "Baska bir yol kullan. ',
        "hedef": "V1b RED metninde `spawn_task` VAR",
    },
    {
        "ad": "M6 CIP MUAFIYETI KALKAR: cip de reddedilir",
        "eski": ('        if rol_coz(girdi, kokler) is not None:\n'
                 '            return "GECER_CIP", None'),
        "yeni": '        if False:\n            return "GECER_CIP", None',
        "hedef": "V3a CIP oturumu + Agent GECER",
    },
    {
        "ad": "KONTROL stderr iz metni degisir (DAVRANIS DISI)",
        "eski": '"ICRA-KAPISI allow "',
        "yeni": '"ICRA-KAPISI izin "',
        "hedef": None,          # KONTROL: batarya YESIL KALMALI
    },
]


def mutasyon_turu(taban_dusenler):
    kaynak = open(KAPI, encoding="utf-8").read()
    print("\n=== MUTASYON TURU ===")
    tamam = True
    for m in MUTANTLAR:
        if m["eski"] not in kaynak:
            print("  🔴 %-62s CAPA TUTMADI (kaynak degismis)" % m["ad"][:62])
            tamam = False
            continue
        mutant = kaynak.replace(m["eski"], m["yeni"], 1)
        d = tempfile.mkdtemp(prefix="icra-kapisi-mutant-")
        try:
            yol = os.path.join(d, "icra-kapisi.py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(mutant)
            dusenler = {ad for ad, ok, _ in vakalar(yol) if not ok} - taban_dusenler
        except Exception as e:                        # noqa: BLE001
            dusenler = {"!!MUTANT_COKTU: %s" % e}
        finally:
            shutil.rmtree(d, ignore_errors=True)

        if m["hedef"] is None:                        # KONTROL
            ok = not dusenler
            print("  %s %-58s KONTROL: dusen=%d %s" % (
                "[OK]" if ok else "🔴", m["ad"][:58], len(dusenler),
                "" if ok else sorted(dusenler)[:3]))
            tamam = tamam and ok
            continue
        if not dusenler:
            print("  🔴 %-58s MUTANT HEDEFE ULASMADI (taban ile AYNI)" % m["ad"][:58])
            tamam = False
            continue
        vurdu = m["hedef"] in dusenler
        print("  %s %-58s OLDURDUGU KOL: %s%s" % (
            "[OK]" if vurdu else "🔴", m["ad"][:58],
            m["hedef"] if vurdu else "BEKLENEN KOL DUSMEDI",
            "  (+%d ek kol)" % (len(dusenler) - 1) if len(dusenler) > 1 else ""))
        tamam = tamam and vurdu
    return tamam


# ---------------------------------------------------------------------------
def main():
    print("=== TABAN BATARYA (kaynak: %s) ===" % KAPI)
    sonuc = vakalar(KAPI)
    dusenler = set()
    for ad, ok, notu in sonuc:
        if not ok:
            dusenler.add(ad)
        print("  %s %-62s %s" % ("[OK]" if ok else "🔴", ad[:62], notu[:40]))
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (
        len(sonuc), len(sonuc) - len(dusenler), len(dusenler)))

    if "--taban" in sys.argv:
        return 0 if not dusenler else 1
    tamam = mutasyon_turu(dusenler)
    print("\nSONUC: %s" % ("KABUL YESIL ✅" if (not dusenler and tamam)
                           else "KIRMIZI 🔴"))
    return 0 if (not dusenler and tamam) else 1


if __name__ == "__main__":
    sys.exit(main())
