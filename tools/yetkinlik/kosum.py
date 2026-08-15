#!/usr/bin/env python3
"""Yetkinlik görevlerini motorlarda çalıştıran ve bağımsız doğrulayan koşucu."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dogrula import dogrula
from fikstur import uret


KOK = Path(__file__).resolve().parent
GOREVLER = {
    1: "01-tarayici-panel.md",
    2: "02-olcum-teshis.md",
    3: "03-toplu-donusum.md",
    4: "04-kirmiziyi-onarma.md",
    5: "05-uzun-baglam-tarama.md",
    6: "06-talimat-disiplini.md",
}
GECICI_KOK = Path("/private/tmp/claude-501")
ISCI = Path("/Users/okan/.claude/cron/isci.sh")
CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")


@contextmanager
def _kilit(yol: Path) -> Iterator[None]:
    tanimlayici = os.open(yol, os.O_RDONLY)
    try:
        fcntl.flock(tanimlayici, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(tanimlayici, fcntl.LOCK_UN)
        os.close(tanimlayici)


def _iz_durumu(yollar: list[Path]) -> dict[str, int]:
    durum: dict[str, int] = {}
    for yol in yollar:
        try:
            durum[str(yol)] = yol.stat().st_mtime_ns
        except OSError:
            continue
    return durum


def _claude_profil_yolu(motor: str, calisma: Path, gorev: int) -> Path | None:
    if motor == "codex":
        return None
    son_ek = "-tarayici" if gorev == 1 else ""
    return Path(f"/Users/okan/.claude/cron/profil-{motor}-{calisma.name}{son_ek}")


def _iz_adaylari(motor: str, calisma: Path) -> list[Path]:
    if motor == "codex":
        return sorted(Path.home().glob(".codex/sessions/**/*.jsonl"))
    profil_koku = _claude_profil_yolu(motor, calisma, 1)
    profil = profil_koku / "projects" if profil_koku else Path("/dev/null")
    return sorted(profil.glob("**/*.jsonl")) if profil.is_dir() else []


def _degisen_izler(
    once: dict[str, int], sonra: list[Path], baglam_yolu: Path | None = None
) -> list[Path]:
    sonuc = []
    for yol in sonra:
        try:
            if once.get(str(yol)) == yol.stat().st_mtime_ns:
                continue
            if baglam_yolu is not None:
                metin = yol.read_text(encoding="utf-8", errors="replace")
                if str(baglam_yolu) not in metin:
                    continue
            sonuc.append(yol)
        except OSError:
            continue
    return sonuc


def _spec_yaz(gorev: int, calisma: Path) -> Path:
    kaynak = KOK / "gorevler" / GOREVLER[gorev]
    somut = kaynak.read_text(encoding="utf-8").replace("<CALISMA>", str(calisma))
    hedef = calisma / "spec.md"
    hedef.write_text(somut, encoding="utf-8")
    return hedef


def _motor_kostur(motor: str, gorev: int, calisma: Path, spec: Path) -> tuple[int, str]:
    if motor in {"minimax-m3", "kimi"}:
        etiket = "panel-yetkinlik" if gorev == 1 else f"yetkinlik-g{gorev}"
        komut = [str(ISCI), motor, str(calisma), str(spec), etiket]
        kosum = subprocess.run(
            komut,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        return kosum.returncode, kosum.stdout

    son_mesaj = calisma / "son-mesaj.txt"
    sandbox = "danger-full-access" if gorev == 1 else "workspace-write"
    komut = [
        str(CODEX),
        "exec",
        "-C",
        str(calisma),
        "-o",
        str(son_mesaj),
        "--skip-git-repo-check",
        "--sandbox",
        sandbox,
        "-",
    ]
    kosum = subprocess.run(
        komut,
        input=spec.read_text(encoding="utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    cikti = son_mesaj.read_text(encoding="utf-8", errors="replace") if son_mesaj.is_file() else kosum.stdout
    return kosum.returncode, cikti


def _kaydet(damga: str, sonuc: dict[str, object]) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", damga):
        raise ValueError("--damga yalniz harf, sayi, nokta, alt cizgi ve tire icerebilir")
    hedef = KOK / "sonuclar" / f"{damga}.jsonl"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with hedef.open("a", encoding="utf-8") as dosya:
        dosya.write(json.dumps(sonuc, ensure_ascii=False, sort_keys=True) + "\n")
        dosya.flush()
        os.fsync(dosya.fileno())
    log = KOK / "log" / f"{damga}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as dosya:
        dosya.write(
            f"BASLANGIC={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
            f"MOTOR={sonuc.get('motor')} GOREV={sonuc.get('gorev')} DAMGA={damga}\n"
        )
        dosya.write(
            f"BITIS={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
            f"RC={sonuc.get('motor_rc')} SURE_SN={sonuc.get('sure_sn')} "
            f"SONUC={sonuc.get('sonuc')} YALAN={sonuc.get('yalan')}\n"
        )
        dosya.flush()
        os.fsync(dosya.fileno())
    return hedef


def tek_kosum(motor: str, gorev: int, damga: str) -> dict[str, object]:
    calisma = GECICI_KOK / f"yetkinlik-{motor}-g{gorev}"
    calisma_kilidi = KOK / "gorevler" / GOREVLER[gorev]
    tarayici_kilidi = KOK / "README.md"
    ana_kilit = tarayici_kilidi if gorev == 1 else calisma_kilidi
    profil = _claude_profil_yolu(motor, calisma, gorev)
    baslangic = time.monotonic()
    sonuc: dict[str, object]
    with _kilit(ana_kilit):
        if calisma.exists():
            shutil.rmtree(calisma)
        if profil and profil.exists():
            shutil.rmtree(profil)
        calisma.mkdir(parents=True, mode=0o700)
        try:
            gercek = uret(gorev, calisma)
            spec = _spec_yaz(gorev, calisma)
            once = _iz_durumu(_iz_adaylari(motor, calisma)) if gorev == 1 else {}
            rc, cikti = _motor_kostur(motor, gorev, calisma, spec)
            baglam = calisma if motor == "codex" else None
            izler = _degisen_izler(once, _iz_adaylari(motor, calisma), baglam) if gorev == 1 else []
            sonuc = dogrula(gorev, calisma, gercek, cikti, izler, motor=motor, motor_rc=rc, sure_sn=round(time.monotonic() - baslangic, 3))
            sonuc.update(
                {
                    "motor": motor,
                    "motor_rc": rc,
                    "sure_sn": round(time.monotonic() - baslangic, 3),
                    "damga": damga,
                    "iz_dosyasi_sayisi": len(izler),
                }
            )
        except BaseException as hata:
            sonuc = {
                "gorev": gorev,
                "sonuc": "DOGRULANAMADI",
                "kabul": None,
                "raporsuz": 1,
                "yalan": 0,
                "disiplin_ihlali": 0,
                "pytest_rc": None,
                "nedenler": [f"kosucu hatasi: {type(hata).__name__}: {hata}"],
                "motor": motor,
                "motor_rc": None,
                "sure_sn": round(time.monotonic() - baslangic, 3),
                "damga": damga,
                "iz_dosyasi_sayisi": 0,
            }
        finally:
            shutil.rmtree(calisma, ignore_errors=True)
            if profil:
                shutil.rmtree(profil, ignore_errors=True)
    _kaydet(damga, sonuc)
    return sonuc


def _argumanlar() -> argparse.Namespace:
    ayrac = argparse.ArgumentParser()
    ayrac.add_argument("--motor", required=True, choices=["minimax-m3", "kimi", "codex"])
    ayrac.add_argument("--gorev", required=True, choices=["1", "2", "3", "4", "5", "6", "hepsi"])
    ayrac.add_argument("--damga", required=True)
    return ayrac.parse_args()


def main() -> int:
    ayar = _argumanlar()
    gorevler = list(range(1, 7)) if ayar.gorev == "hepsi" else [int(ayar.gorev)]
    cikis = 0
    for gorev in gorevler:
        sonuc = tek_kosum(ayar.motor, gorev, ayar.damga)
        print(
            f'GOREV={gorev} MOTOR={ayar.motor} SONUC={sonuc["sonuc"]} '
            f'SURE_SN={sonuc["sure_sn"]} RAPORSUZ={sonuc["raporsuz"]} '
            f'YALAN={sonuc["yalan"]} DISIPLIN_IHLALI={sonuc["disiplin_ihlali"]}'
        )
        if sonuc["sonuc"] != "GECTI":
            cikis = 1
    return cikis


if __name__ == "__main__":
    sys.exit(main())
