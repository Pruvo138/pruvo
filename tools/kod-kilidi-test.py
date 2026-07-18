#!/usr/bin/env python3
import json
import subprocess
import sys


ALLOW_CASES = [
    "/Users/okan/dev/pruvo/DEVAM.md",
    "/Users/okan/dev/pruvo/tools/rapor.md",
    "/private/tmp/claude-501/x/scratchpad/deneme.py",
    "/Users/okan/dev/pruvo/.claude/worktrees/agent-abc123/tools/foo.py",
    "/Users/okan/dev/pruvo/.claude/worktrees/agent-abc123/urunler.json",
    "/Users/okan/dev/pruvo-pazarlama/tools/x.py",
    "/Users/okan/baska/yer/foo.py",
]

DENY_CASES = [
    "/Users/okan/dev/pruvo/tools/foo.py",
    "/Users/okan/dev/pruvo/urunler.json",
    "/Users/okan/dev/pruvo/index.html",
    "/Users/okan/dev/pruvo/.urun-kaynaklari.json",
    "/Users/okan/dev/pruvo/tools/mimar-kod-kilidi.py",
    "/Users/okan/dev/pruvo/.claude/settings.json",
    "/Users/okan/dev/pruvo/.claude/worktrees/x/../../../tools/hack.py",
]


def run_case(file_path: str) -> bool:
    payload = json.dumps({"tool_input": {"file_path": file_path}}).encode("utf-8")
    result = subprocess.run(
        ["python3", "/Users/okan/dev/pruvo/tools/mimar-kod-kilidi.py"],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    return '"permissionDecision": "deny"' in stdout


def main() -> int:
    total = len(ALLOW_CASES) + len(DENY_CASES)
    passed = 0

    for file_path in ALLOW_CASES:
        if run_case(file_path):
            print(f"FAIL allow: {file_path}")
            return 1
        passed += 1

    for file_path in DENY_CASES:
        if not run_case(file_path):
            print(f"FAIL deny: {file_path}")
            return 1
        passed += 1

    print(f"{passed}/{total} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
