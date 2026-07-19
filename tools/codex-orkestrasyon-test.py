#!/usr/bin/env python3
"""Codex KraL orkestrasyon + kredi kapisi kabul testi (ag yok)."""
import importlib.util
import json
import os
import subprocess
import sys
import tomllib

ROOT = "/Users/okan/dev/pruvo"


def oku_toml(yol):
    with open(yol, "rb") as f:
        return tomllib.load(f)


def test_config():
    cfg = oku_toml(os.path.join(ROOT, ".codex", "config.toml"))
    assert cfg["model"] == "gpt-5.6-sol"
    assert cfg["model_reasoning_effort"] == "medium"
    assert cfg["agents"]["max_depth"] == 1
    assert cfg["agents"]["max_threads"] <= 3
    assert cfg["shell_environment_policy"]["set"]["PRUVO_CODEX_ROLE"] == "architect"
    for ad, model, efor in (
        ("muhendis", "gpt-5.6-sol", "medium"),
        ("maraba", "gpt-5.6-terra", "low"),
        ("denetci", "gpt-5.6-terra", "medium"),
    ):
        ajan = oku_toml(os.path.join(ROOT, ".codex", "agents", ad + ".toml"))
        assert ajan["name"] == ad
        assert ajan["model"] == model
        assert ajan["model_reasoning_effort"] == efor
        assert ajan["shell_environment_policy"]["set"]["PRUVO_CODEX_ROLE"] == "worker"


def kilit_cagir(role, patch):
    env = dict(os.environ)
    env["PRUVO_CODEX_ROLE"] = role
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "codex-mimar-kilidi.py")],
        input=json.dumps({"tool_name": "apply_patch", "tool_input": {"patch": patch}}),
        text=True, capture_output=True, env=env,
    )
    return p.returncode, p.stdout + p.stderr


def test_kilit():
    kod, out = kilit_cagir("architect", "*** Update File: /Users/okan/dev/pruvo/tools/x.py")
    assert "deny" in out.lower(), (kod, out)
    kod, out = kilit_cagir("architect", "*** Update File: /Users/okan/dev/pruvo/tools/paket-x.md")
    assert "deny" not in out.lower(), (kod, out)
    kod, out = kilit_cagir("worker", "*** Update File: /Users/okan/dev/pruvo/tools/x.py")
    assert "deny" not in out.lower(), (kod, out)
    hooks = json.load(open(os.path.join(ROOT, ".codex", "hooks.json")))
    eslesmeler = [x.get("matcher", "") for x in hooks["hooks"]["PreToolUse"]]
    assert any("Edit" in x or "apply_patch" in x for x in eslesmeler)


def test_kredi():
    yol = os.path.join(ROOT, "tools", "thing-codex.py")
    spec = importlib.util.spec_from_file_location("thing_codex_kredi", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    eski = os.environ.pop("PRUVO_URUN_AI_IZNI", None)
    try:
        assert mod.ai_izinli() is False
        os.environ["PRUVO_URUN_AI_IZNI"] = "EVET"
        assert mod.ai_izinli() is True
    finally:
        if eski is None:
            os.environ.pop("PRUVO_URUN_AI_IZNI", None)
        else:
            os.environ["PRUVO_URUN_AI_IZNI"] = eski
    env = dict(os.environ)
    env.pop("PRUVO_URUN_AI_IZNI", None)
    p = subprocess.run([sys.executable, yol, "test-id"], capture_output=True, text=True, env=env)
    assert p.returncode != 0 and "KREDI KAPISI" in (p.stdout + p.stderr), (p.returncode, p.stdout, p.stderr)


def main():
    testler = [("config+ajanlar", test_config), ("mimar-kilidi", test_kilit), ("kredi-kapisi", test_kredi)]
    for ad, fn in testler:
        try:
            fn()
            print("ok", ad)
        except Exception as e:
            print("HATA", ad, e)
            return 1
    print("3/3 GECTI — Codex KraL orkestrasyonu kalici ve kredi kapisi kapali.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
