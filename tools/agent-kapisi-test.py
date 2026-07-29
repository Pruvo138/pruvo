#!/usr/bin/env python3
"""AGENT-KAPISI kabul testi (28 Tem).

BaBa/Senyor Advisor doktrini: mimar bir Claude iscisi (Agent/Task araci) acmak da dogrudan
'codex exec' kadar TEK SATIR surtunme tasimali → mimar ANA oturumu (agent_id BOS) Agent/Task
acarken prompt'ta 'codex-muafiyet: <is> — <sinif>' beyani YOKSA cagri REDDEDILIR. ISCI
(agent_id DOLU) TAM muaf; Agent/Task DISINDAKI hicbir arac etkilenmez.

UC BOLUM (her biri GERCEK PreToolUse JSON'u kapi BETIGINE besler — gercek arac CAGRILMAZ):
  A) GATE     — KraL tools/mimar-icra-kapisi.py davranisi: pozitif/negatif/muafiyet +
                >=10 RUTIN (Agent-disi) YESIL nobetcisi + REGEX KESINLIGI (ayrac/etiket
                buyuk-kucuk/bosluk/gecersiz-sinif/etiketsiz).
  B) KABLO    — tools/mimar-kapi-kur.py ANA AKISI Agent|Task matcher'ini settings.json'a
                ADDITIVE + IDEMPOTENT ekliyor mu (gecici settings kopyalari, canli AYAR'a
                DOKUNULMAZ).
  C) 6-EV     — kardes ev gate KOPYASINA AGENT blogunu enjekte edip compile + FIKSTUR
                (no-decl RED / with-decl GECER / isci muaf / codex regresyon) olcer;
                per-ev '.yedek-<ts>' geri-alma yolu da dahil. CANLI ev DEGISTIRILMEZ.

Cikis 0 = hepsi gecti.
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(TOOLS, "mimar-icra-kapisi.py")
KUR = os.path.join(TOOLS, "mimar-kapi-kur.py")
ISCI_ID = "a4482c781a922b6a1"
DECL = "codex-muafiyet: kapi kodu insasi — sessiz-hata"

# Kardes ev gate kopyalari (6ev-test ile ayni yollar). Yoksa C bolumu CEVRE-ATLANAN.
SIBLING_GATES = [
    ("MaCiT", "/Users/okan/dev/pruvo-hasat/.claude/mimar-icra-kapisi.py"),
    ("BaBa", "/Users/okan/dev/pruvo-advisor/.claude/mimar-icra-kapisi.py"),
]


def gate_kostur(gate_yolu, tool_name, tool_input, agent_id=None, cwd="/Users/okan/dev/pruvo"):
    """Doner: allow/deny/COKTU/PARSE-HATASI. GERCEK PreToolUse anlambilimi (6ev-test ile
    ayni): rc==0 + BOS stdout = ALLOW. Bazi ev kapilari (or. BaBa) allow yolunda stderr izi
    BASMAZ — bu BILINEN ve raporlanan bir farktir, karar vermez; crash rc!=0'da yakalanir.
    Betik hic kosmazsa (dosya yok) COKTU."""
    p = {
        "session_id": "agent-kapisi-test",
        "cwd": cwd,
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    if agent_id is not None:
        p["agent_id"] = agent_id
    ortam = dict(os.environ)
    ortam.pop("CLAUDE_PROJECT_DIR", None)
    try:
        r = subprocess.run([sys.executable, gate_yolu], input=json.dumps(p),
                           capture_output=True, text=True, env=ortam)
    except Exception:
        return "COKTU"
    if r.returncode != 0:
        return "COKTU"
    out = (r.stdout or "").strip()
    if not out:
        return "allow"
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return "PARSE-HATASI"


# (no, beklenen, tool_name, tool_input, agent_id, aciklama)
A_VAKALARI = [
    # --- CEKIRDEK: pozitif / negatif / muafiyet ---
    (1, "deny", "Agent", {"prompt": "Bir sey yap, spec burada."}, None,
     "MIMAR Agent + beyan YOK -> RED"),
    (2, "allow", "Agent", {"prompt": "Is X.\n" + DECL + "\nDevam."}, None,
     "MIMAR Agent + gecerli beyan -> GECER"),
    (3, "deny", "Task", {"prompt": "beyansiz task"}, None,
     "MIMAR Task + beyan YOK -> RED"),
    (4, "allow", "Task", {"prompt": DECL}, None,
     "MIMAR Task + beyan -> GECER"),
    (5, "allow", "Agent", {"prompt": "beyansiz isci"}, ISCI_ID,
     "ISCI Agent + beyan YOK -> GECER (muafiyet)"),
    (6, "allow", "Task", {"prompt": "beyansiz isci"}, ISCI_ID,
     "ISCI Task + beyan YOK -> GECER (muafiyet)"),
    (7, "deny", "Agent", {}, None,
     "prompt anahtari YOK -> RED (fail-closed)"),
    (8, "deny", "Agent", {"prompt": ""}, None,
     "bos prompt -> RED"),
    # --- REGEX KESINLIGI ---
    (10, "allow", "Agent", {"prompt": "codex-muafiyet: gorsel is - görsel"}, None,
     "tire '-' ayrac + sinif -> GECER"),
    (11, "allow", "Agent", {"prompt": "codex-muafiyet: is — muhakeme"}, None,
     "em-tire '—' ayrac -> GECER"),
    (12, "allow", "Agent", {"prompt": "codex-muafiyet: is – güvenlik"}, None,
     "en-tire '–' ayrac -> GECER"),
    (13, "allow", "Agent", {"prompt": "CODEX-MUAFIYET: olcum isi — ölçüm"}, None,
     "etikette BUYUK harf DUYARSIZ -> GECER"),
    (14, "allow", "Agent", {"prompt": "codex-muafiyet:\tis metni — şema"}, None,
     "bosluk/tab esnek -> GECER"),
    (15, "allow", "Agent", {"prompt": "onceki satir\nsatir\n" + DECL + "\nson"}, None,
     "cok satirli, beyan ortada -> GECER"),
    (16, "deny", "Agent", {"prompt": "codex-muafiyet: is — foobar"}, None,
     "GECERSIZ sinif -> RED"),
    (17, "deny", "Agent", {"prompt": "Bu is bir ölçüm ve güvenlik meselesi."}, None,
     "sinif KELIMELERI var ama ETIKET yok -> RED"),
    (18, "deny", "Agent", {"prompt": "codex-muafiyet: — ölçüm"}, None,
     "is tanimi BOS (ayrac hemen) -> RED"),
    (19, "deny", "Agent", {"prompt": "codex-muafiyet: is metni ama ayrac/sinif yok"}, None,
     "ayrac+sinif YOK -> RED"),
    (20, "allow", "Agent",
     {"prompt": "codex-muafiyet: AGENT-KAPISI gate kodu insasi — sessiz-hata/ölçüm sinifi (kapi kodu)"},
     None, "is metninde tire + sonra em-tire + sinif (gercek kullanim) -> GECER"),
    # --- RUTIN YESIL NOBETCISI (>=10 Agent-disi cagri; AGENT degisimi bunlari KIZARTMAMALI) ---
    (30, "allow", "Bash", {"command": "git -C /Users/okan/dev/pruvo status -sb"}, None, "rutin git"),
    (31, "allow", "Bash", {"command": "ls"}, None, "rutin ls"),
    (32, "allow", "Bash", {"command": "grep -rn WHATSAPP index.html"}, None, "rutin grep"),
    (33, "allow", "Bash", {"command": "jq . urunler.json"}, None, "rutin jq"),
    (34, "allow", "Bash", {"command": "gh run list --limit 1"}, None, "rutin gh"),
    (35, "allow", "Bash", {"command": "echo x"}, None, "rutin echo"),
    (36, "allow", "Bash", {"command": "cat DEVAM.md"}, None, "rutin cat"),
    (37, "allow", "Bash", {"command": "git -C /Users/okan/dev/pruvo merge dal"}, None, "rutin git merge"),
    (38, "allow", "Bash", {"command": "python3 tools/durum.py"}, None, "rutin durum.py (allowlist)"),
    (39, "allow", "Bash", {"command": "codex exec -o /tmp/x.txt \"spec\""}, None,
     "REGRESYON: codex -o (codex-isci) -> allow"),
    (40, "deny", "Bash", {"command": "codex exec \"x\""}, None,
     "REGRESYON: codex bayraksiz -> deny (mevcut kural korunur)"),
    (41, "deny", "Bash", {"command": "du -sh /"}, None,
     "REGRESYON: olcum du -> deny (22Tem kurali korunur)"),
    # Agent-disi ama Bash-disi bir tool_name gate'e ulasirsa (kablo di$i) -> allow (dokunmaz)
    (42, "allow", "Read", {"file_path": "/x"}, None, "Read tool -> AGENT kolu DISINDA, allow"),
    (43, "allow", "Skill", {"skill": "x"}, None, "Skill tool -> AGENT kolu DISINDA, allow"),
]


def bolum_a():
    print("=" * 84)
    print("A) GATE — KraL mimar-icra-kapisi.py AGENT-KAPISI davranisi")
    print("=" * 84)
    print("{:<4} {:<8} {:<8} {:<6} {}".format("No", "Beklenen", "Olculen", "Sonuc", "Vaka"))
    print("-" * 84)
    basarisiz = []
    for no, beklenen, tn, ti, aid, aciklama in A_VAKALARI:
        olculen = gate_kostur(GATE, tn, ti, aid)
        gecti = (olculen == beklenen)
        if not gecti:
            basarisiz.append((no, beklenen, olculen, aciklama))
        print("{:<4} {:<8} {:<8} {:<6} {}".format(
            no, beklenen, olculen, "OK" if gecti else "KIRMIZI", aciklama[:44]))
    rutin = [v for v in A_VAKALARI if v[2] not in ("Agent", "Task")]
    print("RUTIN/Agent-disi vaka sayisi: {} (bu degisiklik yuzunden kizaran: {})".format(
        len(rutin), len([b for b in basarisiz if b[0] in [v[0] for v in rutin]])))
    return basarisiz


def _kur_ile_kabla(ayar_yolu):
    """mimar-kapi-kur.py --uygula --ayar <ayar_yolu> kosturur; ciktiyi doner."""
    r = subprocess.run([sys.executable, KUR, "--uygula", "--ayar", ayar_yolu],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "")


def _agent_blok_var(ayar_yolu):
    veri = json.loads(io.open(ayar_yolu, encoding="utf-8").read())
    for blok in ((veri.get("hooks") or {}).get("PreToolUse") or []):
        if blok.get("matcher") == "Agent|Task":
            for k in (blok.get("hooks") or []):
                if "mimar-icra-kapisi.py" in (k.get("command") or ""):
                    return True
    return False


BASH_BLOK_KOMUT = 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-icra-kapisi.py"'
BASLANGIC_AYAR = {
    "hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [
            {"type": "command", "command": BASH_BLOK_KOMUT, "timeout": 30}]},
        {"matcher": "Edit|Write|MultiEdit", "hooks": [
            {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-kod-kilidi.py"'}]},
    ]}
}


def bolum_b(gecici):
    print("")
    print("=" * 84)
    print("B) KABLO — kur.py ANA AKISI Agent|Task matcher'ini ekliyor mu (gecici settings)")
    print("=" * 84)
    basarisiz = []

    # B1: Bash blogu VAR ama Agent yok -> Agent EKLENIR (Bash'e DOKUNULMAZ)
    ayar1 = os.path.join(gecici, "settings-1.json")
    io.open(ayar1, "w", encoding="utf-8").write(json.dumps(BASLANGIC_AYAR))
    rc, cikti = _kur_ile_kabla(ayar1)
    agent_eklendi = _agent_blok_var(ayar1)
    veri1 = json.loads(io.open(ayar1, encoding="utf-8").read())
    bash_hala = any(b.get("matcher") == "Bash" for b in veri1["hooks"]["PreToolUse"])
    ok1 = (rc == 0 and agent_eklendi and bash_hala)
    print("B1 Bash-var/Agent-yok -> Agent eklendi={} Bash-korundu={} rc={} : {}".format(
        agent_eklendi, bash_hala, rc, "OK" if ok1 else "KIRMIZI"))
    if not ok1:
        basarisiz.append(("B1", cikti[:120]))

    # B2: IDEMPOTANS — ayni ayara tekrar -> ZATEN KURULU, degisiklik yok
    rc2, cikti2 = _kur_ile_kabla(ayar1)
    ok2 = (rc2 == 0 and "ZATEN KURULU" in cikti2)
    print("B2 idempotans -> 'ZATEN KURULU' rc={} : {}".format(rc2, "OK" if ok2 else "KIRMIZI"))
    if not ok2:
        basarisiz.append(("B2", cikti2[:120]))

    # B3: BOS settings -> HEM Bash HEM Agent eklenir
    ayar3 = os.path.join(gecici, "settings-3.json")
    io.open(ayar3, "w", encoding="utf-8").write(json.dumps({}))
    rc3, cikti3 = _kur_ile_kabla(ayar3)
    veri3 = json.loads(io.open(ayar3, encoding="utf-8").read())
    bloklar = (veri3.get("hooks") or {}).get("PreToolUse") or []
    bash_v = any(b.get("matcher") == "Bash" and any(
        "mimar-icra-kapisi.py" in (k.get("command") or "") for k in b.get("hooks") or [])
        for b in bloklar)
    agent_v = _agent_blok_var(ayar3)
    ok3 = (rc3 == 0 and bash_v and agent_v)
    print("B3 bos-settings -> Bash={} Agent={} rc={} : {}".format(
        bash_v, agent_v, rc3, "OK" if ok3 else "KIRMIZI"))
    if not ok3:
        basarisiz.append(("B3", cikti3[:120]))
    return basarisiz


def _kur_modulu():
    spec = importlib.util.spec_from_file_location("mimar_kapi_kur", KUR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bolum_c(gecici):
    print("")
    print("=" * 84)
    print("C) 6-EV ENJEKSIYON — kardes ev KOPYASINA AGENT blogu enjekte + fikstur + geri-al yolu")
    print("=" * 84)
    mevcut = [(ad, y) for ad, y in SIBLING_GATES if os.path.exists(y)]
    if not mevcut:
        print("CEVRE-ATLANAN: bu makinede kardes ev gate'i yok (C bolumu kosmadi).")
        return [], True  # cevre-atlanan
    kur = _kur_modulu()
    basarisiz = []
    for ad, gate_yolu in mevcut:
        ev = os.path.join(gecici, "ev-" + ad)
        os.makedirs(os.path.join(ev, ".claude"), exist_ok=True)
        hedef_gate = os.path.join(ev, ".claude", "mimar-icra-kapisi.py")
        shutil.copyfile(gate_yolu, hedef_gate)
        # settings.json: Bash blogunda mimar-icra-kapisi.py komutu (Agent kablosu kopyalasin)
        io.open(os.path.join(ev, ".claude", "settings.json"), "w", encoding="utf-8").write(
            json.dumps({"hooks": {"PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command",
                 "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/mimar-icra-kapisi.py"'}]}]}}))
        rapor = []
        durum, yedek = kur._eve_agent_enjekte(ad, ev, ".claude/mimar-icra-kapisi.py", True, rapor)
        kuruldu = (durum == "KURULDU")
        # Enjekte edilen gate DAVRANISI (bagimsiz teyit)
        fx = []
        if kuruldu:
            fx = [
                ("no-decl mimar", "deny", gate_kostur(hedef_gate, "Agent",
                 {"prompt": "beyansiz"}, None, ev)),
                ("with-decl mimar", "allow", gate_kostur(hedef_gate, "Agent",
                 {"prompt": DECL}, None, ev)),
                ("isci muaf", "allow", gate_kostur(hedef_gate, "Agent",
                 {"prompt": "beyansiz"}, ISCI_ID, ev)),
                ("codex regresyon", "deny", gate_kostur(hedef_gate, "Bash",
                 {"command": 'codex exec "x"'}, None, ev)),
                ("rutin ls", "allow", gate_kostur(hedef_gate, "Bash",
                 {"command": "ls"}, None, ev)),
            ]
        # settings Agent|Task eklendi mi
        agent_kablo = _agent_blok_var(os.path.join(ev, ".claude", "settings.json"))
        # damga idempotans: ikinci enjeksiyon 'ZATEN TAM'
        durum2, _ = kur._eve_agent_enjekte(ad, ev, ".claude/mimar-icra-kapisi.py", True, [])
        fx_ok = all(bek == olc for _, bek, olc in fx)
        ok = kuruldu and fx_ok and agent_kablo and durum2 == "ZATEN TAM"
        print("EV {:<6} enjekte={:<8} settings={} idempotans={} fikstur={} : {}".format(
            ad, durum, agent_kablo, durum2, "OK" if fx_ok else "KIRMIZI",
            "OK" if ok else "KIRMIZI"))
        for etiket, bek, olc in fx:
            if bek != olc:
                print("      FIKSTUR KIRMIZI: {} beklenen={} olculen={}".format(etiket, bek, olc))
        # geri-alma yolu: yedek dosyasi olusmus mu (per-ev .yedek-<ts>)
        yedek_var = bool(yedek) and os.path.exists(yedek)
        if not yedek_var:
            print("      UYARI: per-ev yedek dosyasi bulunamadi ({})".format(yedek))
        if not ok or not yedek_var:
            basarisiz.append((ad, durum, fx))
    return basarisiz, False


def main():
    gecici = tempfile.mkdtemp(prefix="agent-kapisi-test-")
    try:
        a = bolum_a()
        b = bolum_b(gecici)
        c, cevre_atlanan = bolum_c(gecici)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    basarisiz = a + b + c
    print("")
    print("=" * 84)
    if basarisiz:
        print("SONUC: KIRMIZI — basarisiz:")
        for x in basarisiz:
            print("  " + str(x))
        sys.exit(1)
    if cevre_atlanan:
        print("SONUC: A+B GECTI; C bolumu CEVRE-ATLANAN (kardes ev yok — bu makineye ozel).")
    else:
        print("SONUC: A + B + C bolumlerinin HEPSI GECTI.")
    sys.exit(0)


if __name__ == "__main__":
    main()
