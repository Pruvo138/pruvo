#!/usr/bin/env python3
"""agy-kapi-baglayici.py kabul + mutant bataryasi (1 Kas 2026, KARARLAR 92 EK 2).

IKI BOLUM:
  1) MEKANIZMA (her yerde, CI dahil): sentetik settings.json + sentetik kapilarla
     baglayicinin karar sozlesmesi — exit 2 / stdout deny / permissionDecision deny /
     cokme / zaman asimi / taninmayan tool / settings.json yok / --ev yok /
     gecersiz matcher -> DENY; gecen kapi ve eslesmeyen matcher -> izin.
  2) GERCEK KAPILAR: `<EV>/.claude/settings.json` (gitignore — CI'da YOK) varsa IZOLE
     gecici kopya repoya (tools/ kopyasi + settings.json, mutlak `/Users/okan/dev/pruvo/tools/`
     oneki kopyaya cevrilir) kurulur ve her PreToolUse kapisi icin 1 yasak + 1 masum
     cagri kosulur. Yasak cagrinin DENY gerekcesinde O KAPININ dosya adi aranir —
     baska kapinin reddi o kapinin kaniti SAYILMAZ. Red uretemeyen kapi OLCULEMEDI
     (sebebiyle) yazilir, kacak sayilmaz.

KIMLIK: kapilar `PRUVO_ISCI_KOSUMU` doluysa ISCI muaf cikar; bu batarya kurali olcmek
icin cevreyi `mimar_kimlik.kapi_cevresi("MIMAR")` ile KURAR (kosucunun kimligini
olcmez).

IZOLASYON: yikici yuk YOK; gercek ev yolu silinmez. Tum gecici dosyalar
`tempfile.mkdtemp` altinda ve `finally` ile silinir. Write yukleri yalniz JSON'dur —
baglayici araci CALISTIRMAZ, yalniz kapilara sorar.

MUTANT: baglayicinin `reddet` fonksiyonu deny->izin cevrilmis kopyasi ayni yasak
cagrilara karsi kosulur; KACAK > 0 olmali (aksi halde batarya hukumsuz -> rc=1).

Cikti: `DENY N/N KACAK 0` + `MUTANT KIRMIZI ...`. rc=0 yalniz ikisi birden tutarsa.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

BU = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(BU)
BAGLAYICI = os.path.join(BU, "agy-kapi-baglayici.py")
GERCEK_ONEK = "/Users/okan/dev/pruvo/tools/"
sys.path.insert(0, BU)
from mimar_kimlik import kapi_cevresi  # noqa: E402


def cevre():
    e = kapi_cevresi("MIMAR")
    for k in list(e):
        if k.startswith("GIT_"):
            e.pop(k)
    return e


def kos(baglayici, ev, girdi, ev_arg=True, zaman=60):
    argv = [sys.executable, baglayici] + (["--ev", ev] if ev_arg else [])
    p = subprocess.run(argv, input=json.dumps(girdi).encode(), capture_output=True,
                       env=cevre(), cwd=ev if os.path.isdir(ev) else None, timeout=zaman)
    cikti = p.stdout.decode("utf-8", "replace")
    try:
        d = json.loads(cikti) if cikti.strip() else {}
    except ValueError:
        d = {}
    red = p.returncode == 2 and d.get("decision") == "deny"
    return red, d.get("reason", "") or cikti.strip()[:200], p.returncode


def bash(cmd, cwd, **ek):
    d = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
         "tool_input": {"command": cmd}, "cwd": cwd}
    d.update(ek)
    return d


def yaz_arac(arac, yol, cwd):
    return {"hook_event_name": "PreToolUse", "tool_name": arac,
            "tool_input": {"file_path": yol, "content": "x\n"}, "cwd": cwd}


def sentetik_ev(kok, ad, kapilar):
    """kapilar: [(matcher, python_govdesi)] -> <kok>/<ad> altinda ev kurar."""
    ev = os.path.join(kok, ad)
    os.makedirs(os.path.join(ev, ".claude"))
    giris = []
    for i, (matcher, govde) in enumerate(kapilar):
        yol = os.path.join(ev, "kapi%d.py" % i)
        with open(yol, "w", encoding="utf-8") as f:
            f.write("import sys, json, time\nsys.stdin.read()\n" + govde + "\n")
        giris.append({"matcher": matcher, "hooks": [
            {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR}/kapi%d.py"' % i}]})
    with open(os.path.join(ev, ".claude", "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"hooks": {"PreToolUse": giris}}, f)
    return ev


def mekanizma_vakalari(kok):
    """[(ad, ev, girdi, beklenen_red, ev_arg, gerekce_icermeli)]"""
    v = []
    gec = sentetik_ev(kok, "gec", [("Bash", "sys.exit(0)")])
    v.append(("gecen kapi -> izin", gec, bash("ls", gec), False, True, None))
    e2 = sentetik_ev(kok, "e2", [("Bash", "sys.exit(0)"), ("Bash", "sys.exit(2)")])
    v.append(("exit 2 -> DENY", e2, bash("ls", e2), True, True, "rc=2"))
    blk = sentetik_ev(kok, "blk", [("*", 'print(json.dumps({"decision":"block","reason":"B"}))')])
    v.append(("stdout decision=block -> DENY", blk, bash("ls", blk), True, True, "stdout"))
    pd = sentetik_ev(kok, "pd", [("Edit|Write|MultiEdit", 'print(json.dumps({"hookSpecificOutput":'
                                  '{"permissionDecision":"deny","permissionDecisionReason":"P"}}))')])
    v.append(("permissionDecision=deny -> DENY", pd, yaz_arac("Write", pd + "/a.txt", pd),
              True, True, "stdout"))
    v.append(("eslesmeyen matcher -> izin", pd, bash("ls", pd), False, True, None))
    cok = sentetik_ev(kok, "cok", [("Bash", "raise RuntimeError('cokme')")])
    v.append(("coken kapi -> DENY", cok, bash("ls", cok), True, True, "coktu"))
    za = sentetik_ev(kok, "za", [("Bash", "time.sleep(40)")])
    v.append(("zaman asimi 20 sn -> DENY", za, bash("ls", za), True, True, "zaman asimi"))
    rx = sentetik_ev(kok, "rx", [("Bash(", "sys.exit(0)")])
    v.append(("gecersiz matcher -> DENY", rx, bash("ls", rx), True, True, "matcher"))
    for ad in ("Agent", "define_subagent", "send_message", ""):
        d = bash("ls", gec)
        d["tool_name"] = ad
        v.append(("taninmayan tool %r -> DENY" % ad, gec, d, True, True, "taninmayan"))
    yok = os.path.join(kok, "yok")
    os.makedirs(yok)
    v.append(("settings.json yok -> DENY", yok, bash("ls", yok), True, True, "settings.json"))
    v.append(("--ev yok -> DENY", gec, bash("ls", gec), True, False, "--ev"))
    return v


def gercek_ev_kur(kok):
    """Gercek settings.json yoksa (None, sebep)."""
    kaynak = os.path.join(EV, ".claude", "settings.json")
    if not os.path.isfile(kaynak):
        return None, "<EV>/.claude/settings.json yok (gitignore; CI kosucusunda kapi listesi bulunmaz)"
    ev = os.path.join(kok, "ev")
    shutil.copytree(BU, os.path.join(ev, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    os.makedirs(os.path.join(ev, ".claude"))
    with open(kaynak, encoding="utf-8") as f:
        metin = f.read()
    with open(os.path.join(ev, ".claude", "settings.json"), "w", encoding="utf-8") as f:
        f.write(metin.replace(GERCEK_ONEK, os.path.join(ev, "tools") + "/"))
    return ev, None


def kapi_vakalari(ev, kok):
    """[(kapi_dosyasi, yasak_girdi|None, masum_girdi, olculemedi_sebebi|None)]"""
    tr_buyuk = os.path.join(kok, "buyuk.jsonl")
    tr_kucuk = os.path.join(kok, "kucuk.jsonl")
    for yol, jeton in ((tr_buyuk, 600000), (tr_kucuk, 1000)):
        with open(yol, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "assistant", "message": {
                "usage": {"input_tokens": jeton}, "content": []}}) + "\n")
    kod_kilidi_hedef = GERCEK_ONEK + "mimar_kimlik.py"   # CEKIRDEK: yalniz JSON yuku, yazilmaz
    return [
        ("komut-stili-kapisi.py", None, bash("ls", ev),
         "11 Eyl 2026 OKAN EMRI ile red yetkisi kaldirildi; kapi yalniz stderr'e RAPOR eder"),
        ("urunler-guard-hook.py", bash("git commit -m x", ev), bash("git status", ev), None),
        ("parti-kapisi.py", None, bash("ls", ev),
         "kanca() DAIMA rc=0 doner; deny ureten fonksiyon kaynaktan SILINMIS"),
        ("mimar-icra-kapisi.py", bash('python3 -c "print(1)"', ev), bash("ls", ev), None),
        ("mimar-icra-kapisi.py", bash("curl https://example.invalid", ev), bash("ls", ev), None),
        ("icra-kapisi.py", None, bash("ls", ev),
         "yalniz `Agent` tool_name'i reddeder; baglayici `Agent`'i kapiya gondermeden "
         "taninmayan tool diye DENY eder (mekanizma bolumunde olculdu)"),
        ("baglam-kotasi-kapisi.py", bash("make", ev, transcript_path=tr_buyuk),
         bash("make", ev, transcript_path=tr_kucuk), None),
        ("mimar-kod-kilidi.py", yaz_arac("Write", kod_kilidi_hedef, ev),
         yaz_arac("Write", os.path.join(ev, "notlar.txt"), ev), None),
    ]


def batarya(baglayici, kok, sessiz=False, zaman_asimi_dahil=True):
    """(deny_ok, deny_toplam, kacak, yanlis_red, olculemedi, satirlar)"""
    ok = toplam = kacak = yanlis = 0
    olculemedi = []
    satir = []
    for ad, ev, girdi, bek, ev_arg, icermeli in mekanizma_vakalari(kok):
        if not zaman_asimi_dahil and "zaman asimi" in ad:
            continue
        red, sebep, rc = kos(baglayici, ev, girdi, ev_arg)
        if bek:
            toplam += 1
            if red and (icermeli is None or icermeli in sebep):
                ok += 1
                satir.append("  DENY   %s" % ad)
            else:
                kacak += 1
                satir.append("  KACAK  %s (rc=%d %s)" % (ad, rc, sebep[:120]))
        elif red:
            yanlis += 1
            satir.append("  YANLIS-RED %s (%s)" % (ad, sebep[:160]))
        else:
            satir.append("  IZIN   %s" % ad)
    ev, sebep = gercek_ev_kur(kok)
    if ev is None:
        olculemedi.append("GERCEK KAPILAR: " + sebep)
    else:
        for kapi, yasak, masum, osebep in kapi_vakalari(ev, kok):
            red, s, rc = kos(baglayici, ev, masum)
            if red:
                yanlis += 1
                satir.append("  YANLIS-RED %s masum (%s)" % (kapi, s[:160]))
            else:
                satir.append("  IZIN   %s masum" % kapi)
            if yasak is None:
                olculemedi.append("%s: %s" % (kapi, osebep))
                continue
            toplam += 1
            red, s, rc = kos(baglayici, ev, yasak)
            if red and kapi in s:
                ok += 1
                satir.append("  DENY   %s yasak (%s)" % (kapi, yasak["tool_input"].get(
                    "command") or yasak["tool_input"].get("file_path")))
            else:
                kacak += 1
                satir.append("  KACAK  %s yasak (rc=%d %s)" % (kapi, rc, s[:160]))
    if not sessiz:
        print("\n".join(satir))
    return ok, toplam, kacak, yanlis, olculemedi


def mutant_yaz(kok):
    with open(BAGLAYICI, encoding="utf-8") as f:
        kaynak = f.read()
    imza = "def reddet(sebep):\n"
    if kaynak.count(imza) != 1:
        return None
    yol = os.path.join(kok, "mutant-baglayici.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(imza, imza + "    return 0  # MUTANT deny->izin\n"))
    return yol


def main():
    kok = tempfile.mkdtemp(prefix="agy-baglayici-test-")
    try:
        ok, toplam, kacak, yanlis, olculemedi = batarya(BAGLAYICI, os.path.join(kok, "a"))
        for o in olculemedi:
            print("OLCULEMEDI %s" % o)
        print("DENY %d/%d KACAK %d YANLIS_RED %d" % (ok, toplam, kacak, yanlis))
        mutant = mutant_yaz(kok)
        if mutant is None:
            print("MUTANT KURULAMADI: `def reddet(sebep):` imzasi tek degil -> hukumsuz")
            return 1
        _, mt, mkacak, _, _ = batarya(mutant, os.path.join(kok, "m"), sessiz=True,
                                      zaman_asimi_dahil=False)
        mutant_kirmizi = mkacak > 0
        print("MUTANT %s (deny->izin: kacak %d/%d)" % (
            "KIRMIZI" if mutant_kirmizi else "YESIL — BATARYA HUKUMSUZ", mkacak, mt))
        return 0 if (toplam > 0 and ok == toplam and kacak == 0 and yanlis == 0
                     and mutant_kirmizi) else 1
    finally:
        if os.path.basename(kok).startswith("agy-baglayici-test-") and \
                os.path.realpath(kok).startswith(os.path.realpath(tempfile.gettempdir())):
            shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
