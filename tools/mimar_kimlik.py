#!/usr/bin/env python3
"""Mimar kapilarinin ortak, fail-closed ISCI kimlik ekseni."""
import os


# Kapali kume: bos ya da gelecekte eklenecek bilinmeyen bir motor kapiyi acmaz.
ISCI_MOTORLARI = ("minimax-m3", "kimi", "deepseek-pro", "deepseek-flash", "claude")


def kimlik_ekseni(girdi, ortam=None):
    """Kimlik kaynagini dondur; ``None`` her zaman MIMAR demektir."""
    aid = girdi.get("agent_id")
    if isinstance(aid, str) and aid.strip():
        return "agent_id"
    cevre = os.environ if ortam is None else ortam
    motor = cevre.get("PRUVO_ISCI_KOSUMU")
    if motor in ISCI_MOTORLARI:
        return "sarmalayici:" + motor
    return None
