#!/usr/bin/env python3
"""Yetkinlik JSONL sonuçlarını motor bazında özetle."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


KOK = Path(__file__).resolve().parent


def oku(yol: Path) -> list[dict[str, Any]]:
    kayitlar = []
    for numara, satir in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
        if satir.strip():
            try:
                kayitlar.append(json.loads(satir))
            except json.JSONDecodeError as hata:
                raise ValueError(f"{yol}:{numara}: gecersiz JSON: {hata}") from hata
    return kayitlar


def ozetle(kayitlar: list[dict[str, Any]]) -> list[dict[str, Any]]:
    son: dict[tuple[str, int], dict[str, Any]] = {}
    for kayit in kayitlar:
        son[(str(kayit["motor"]), int(kayit["gorev"]))] = kayit
    motorlar: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (motor, _), kayit in son.items():
        motorlar[motor].append(kayit)
    ozet = []
    for motor in sorted(motorlar):
        satirlar = motorlar[motor]
        toplam = len(satirlar)
        dogrulanamadi = sum(kayit.get("sonuc") == "DOGRULANAMADI" for kayit in satirlar)
        ozet.append(
            {
                "motor": motor,
                "gecen": sum(kayit.get("sonuc") == "GECTI" for kayit in satirlar),
                "toplam": toplam,
                "dogrulanamadi": dogrulanamadi,
                "sure_sn": round(sum(float(kayit.get("sure_sn", 0)) for kayit in satirlar), 3),
                "raporsuz": sum(int(kayit.get("raporsuz", 0)) for kayit in satirlar),
                "yalan": sum(int(kayit.get("yalan", 0)) for kayit in satirlar),
                "disiplin_ihlali": sum(int(kayit.get("disiplin_ihlali", 0)) for kayit in satirlar),
            }
        )
    return ozet


def _argumanlar() -> argparse.Namespace:
    ayrac = argparse.ArgumentParser()
    grup = ayrac.add_mutually_exclusive_group(required=True)
    grup.add_argument("--dosya", type=Path)
    grup.add_argument("--damga")
    return ayrac.parse_args()


def main() -> int:
    ayar = _argumanlar()
    yol = ayar.dosya if ayar.dosya else KOK / "sonuclar" / f"{ayar.damga}.jsonl"
    print("MOTOR | GECEN/6 | TOPLAM | DOGRULANAMADI | SURE_SN | RAPORSUZ | YALAN | DISIPLIN_IHLALI")
    print("--- | ---: | ---: | ---: | ---: | ---: | ---: | ---:")
    for satir in ozetle(oku(yol)):
        dogrulanamadi = satir["dogrulanamadi"]
        toplam = satir["toplam"]
        olculebilir = toplam - dogrulanamadi
        gecme_orani = (
            f'{satir["gecen"] / olculebilir:.0%}' if olculebilir > 0 else "n/a"
        )
        print(
            f'{satir["motor"]} | {satir["gecen"]}/6 | {toplam} | {dogrulanamadi} | '
            f'{satir["sure_sn"]:.3f} | {satir["raporsuz"]} | {satir["yalan"]} | '
            f'{satir["disiplin_ihlali"]} | GECME={gecme_orani} (olculebilir={olculebilir})'
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
