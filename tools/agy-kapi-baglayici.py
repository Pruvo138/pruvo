#!/usr/bin/env python3
"""agy-kapi-baglayici.py — agy cevirmeninin PRUVO PreToolUse kapilarina baglayicisi.

1 Kas 2026 (KARARLAR 92 EK 2): agy, m3 KARANTINA yedegi olarak isci kumesine
girdi (`mimar_kimlik.YEDEK_ISCI_MOTORLARI`). agy'nin kendi arac adlari Claude'un
adlari DEGILDIR; bu yuzden PRUVO kapilari agy cagrisini dogrudan GORMEZ. Bu
dosya o boslugu kapatir: cevirmen agy cagrisini Claude PreToolUse JSON'una
cevirir, bu baglayici da `<EV_KOKU>/.claude/settings.json::hooks.PreToolUse`
listesini OKUYUP her eslesen kapiyi AYNI stdin ile kosar.

TEK KAYNAK: kapi listesi burada KOPYALANMAZ. settings.json'a eklenen/cikarilan
kapi bir sonraki cagrida kendiliginden devreye girer/cikar.

=== CEVIRMEN SOZLESMESI (agy arac adi -> Claude tool_name) ====================
  run_command (CommandLine)                         -> Bash   tool_input.command
  write_to_file / replace_file_content /
  multi_replace_file_content / sed_file /
  notebook_edit (hedef dosya)                       -> Write/Edit tool_input.file_path
  define_subagent / invoke_subagent / run_workflow / schedule / send_message /
  manage_inbox / browser_subagent / generate_image / search_marketplace /
  manage_subagents
      -> baglayiciya GELMEDEN cevirmenin deny listesinde duser. Yine de buraya
         gelirse taninmayan tool_name sayilir -> DENY.

=== KARAR (fail-closed) =========================================================
  * stdin = Claude PreToolUse JSON (`tool_name`, `tool_input.command|file_path`, `cwd`).
  * taninmayan tool_name                         -> DENY
  * settings.json yok / bozuk / PreToolUse yok   -> DENY
  * gecersiz matcher regex'i / bilinmeyen kanca tipi -> DENY
  * kapi exit 2 ya da stdout JSON `decision` / `permissionDecision` = block/deny -> DENY
  * kapi cokerse (0/2 disi rc), zaman asimi (20 sn) ya da kosturulamazsa -> DENY
  * hepsi gecerse exit 0, stdout BOS.
  DENY: stdout `{"decision":"deny","reason":...}`, exit 2.

Kullanim:  agy-kapi-baglayici.py --ev <EV_KOKU>   (stdin: PreToolUse JSON)
"""
import json
import os
import re
import subprocess
import sys

ZAMAN_ASIMI_SN = 20
TANINAN_ARACLAR = ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit")
RED_DEGERLERI = ("block", "deny")


def reddet(sebep):
    print(json.dumps({"decision": "deny", "reason": sebep}, ensure_ascii=False))
    return 2


def ev_al(argv):
    """`--ev <yol>` zorunlu; yoksa None."""
    for i, a in enumerate(argv):
        if a == "--ev" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--ev="):
            return a.split("=", 1)[1]
    return None


def kapilari_oku(ev):
    """settings.json'dan [(matcher, komut)] listesi. Her kusur ValueError."""
    yol = os.path.join(ev, ".claude", "settings.json")
    try:
        with open(yol, encoding="utf-8") as f:
            ayar = json.load(f)
    except (OSError, ValueError) as e:
        raise ValueError("settings.json okunamadi: %s: %s" % (yol, type(e).__name__))
    liste = (ayar.get("hooks") or {}).get("PreToolUse") if isinstance(ayar, dict) else None
    if not isinstance(liste, list) or not liste:
        raise ValueError("settings.json hooks.PreToolUse yok/bos")
    kapilar = []
    for giris in liste:
        if not isinstance(giris, dict):
            raise ValueError("PreToolUse girisi sozluk degil")
        matcher = giris.get("matcher", "")
        for kanca in giris.get("hooks") or []:
            if not isinstance(kanca, dict) or kanca.get("type") != "command" \
                    or not isinstance(kanca.get("command"), str):
                raise ValueError("bilinmeyen kanca tipi: %r" % (kanca,))
            kapilar.append((matcher, kanca["command"]))
    return kapilar


def eslesir(matcher, arac):
    if matcher in ("", "*", None):
        return True
    return re.fullmatch(matcher, arac) is not None  # re.error -> cagiran DENY eder


def stdout_red_mu(cikti):
    """Kapinin stdout JSON'u red diyorsa sebebi, yoksa None."""
    metin = cikti.strip()
    if not metin.startswith("{"):
        return None
    try:
        d = json.loads(metin)
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    hso = d.get("hookSpecificOutput") if isinstance(d.get("hookSpecificOutput"), dict) else {}
    for k, v in (("decision", d.get("decision")),
                 ("permissionDecision", d.get("permissionDecision")),
                 ("permissionDecision", hso.get("permissionDecision"))):
        if isinstance(v, str) and v.lower() in RED_DEGERLERI:
            return (d.get("reason") or hso.get("permissionDecisionReason")
                    or d.get("permissionDecisionReason") or "%s=%s" % (k, v))
    return None


def kapi_kos(komut, ham, ev, cwd):
    """Tek kapiyi kosar. Gecerse None, reddederse sebep dizesi."""
    ortam = dict(os.environ)
    ortam["CLAUDE_PROJECT_DIR"] = ev
    try:
        p = subprocess.run(komut, shell=True, input=ham, capture_output=True,
                           cwd=cwd, env=ortam, timeout=ZAMAN_ASIMI_SN)
    except subprocess.TimeoutExpired:
        return "zaman asimi (%d sn): %s" % (ZAMAN_ASIMI_SN, komut)
    except OSError as e:
        return "kosturulamadi: %s: %s" % (komut, e)
    cikti = p.stdout.decode("utf-8", "replace")
    hata = p.stderr.decode("utf-8", "replace").strip()
    if p.returncode == 2:
        return "kapi reddetti (rc=2): %s: %s" % (komut, hata[-400:])
    if p.returncode != 0:
        return "kapi coktu (rc=%d): %s: %s" % (p.returncode, komut, hata[-400:])
    sebep = stdout_red_mu(cikti)
    if sebep:
        return "kapi reddetti (stdout): %s: %s" % (komut, sebep)
    return None


def main(argv):
    ev = ev_al(argv[1:])
    if not ev:
        return reddet("--ev <EV_KOKU> zorunlu")
    ev = os.path.abspath(ev)
    ham = sys.stdin.buffer.read()
    try:
        girdi = json.loads(ham.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return reddet("stdin PreToolUse JSON degil")
    arac = girdi.get("tool_name") if isinstance(girdi, dict) else None
    if arac not in TANINAN_ARACLAR:
        return reddet("taninmayan tool_name: %r" % (arac,))
    try:
        kapilar = kapilari_oku(ev)
    except ValueError as e:
        return reddet(str(e))
    cwd = girdi.get("cwd")
    if not isinstance(cwd, str) or not os.path.isdir(cwd):
        cwd = ev
    for matcher, komut in kapilar:
        try:
            if not eslesir(matcher, arac):
                continue
        except re.error:
            return reddet("gecersiz matcher: %r" % (matcher,))
        sebep = kapi_kos(komut, ham, ev, cwd)
        if sebep:
            return reddet(sebep)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
