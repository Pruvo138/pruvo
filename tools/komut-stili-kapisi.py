#!/usr/bin/env python3
"""PreToolUse (Bash) kancasi: onay penceresi TETIKLEYEN komut biçimlerini insan yerine
MAKINE reddeder (Okan, 17 Tem: "midem bulandi" — pencere yerine otomatik geri tepme).
Yasak biçim görülünce 'deny' döner; model komutu kurala uygun yeniden yazar (betiği
Write ile .py dosyasina yaz, düz çalıştır). İnsan onayı devreden çıkar."""
import json
import re
import sys

try:
    girdi = json.load(sys.stdin)
except Exception:
    sys.exit(0)

komut = (girdi.get("tool_input") or {}).get("command") or ""

YASAK = [
    (r"<<", "heredoc (<<)"),
    (r"\$[A-Za-z_{(?@#!]", "kabuk değişkeni/genişletmesi ($...)"),
    (r"(?<![0-9<>])>(?!&)\s", "çıktı yönlendirme (>)"),
    (r"(?m)^\s*for\s+\w+\s+in\s", "for döngüsü"),
    (r"(?m)^\s*while\s+", "while döngüsü"),
]

bulunan = [ad for desen, ad in YASAK if re.search(desen, komut)]
if bulunan:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "KOMUT STILI KAPISI (insan onayi yerine otomatik red): komutta "
                + ", ".join(bulunan)
                + " var — bunlar Okan'a onay penceresi dusurur. COZUM: betigi Write "
                "araciyla bir .py dosyasina yaz ve 'python3 /tam/yol/betik.py' ile düz "
                "calistir; cikti dosyaya python iciyle yazilsin (>' degil). CLAUDE.md "
                "KOMUT STILI bolumune bak."
            ),
        }
    }, ensure_ascii=False))
sys.exit(0)
