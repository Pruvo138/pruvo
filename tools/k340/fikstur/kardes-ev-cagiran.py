#!/usr/bin/env python3
"""K340 KABUL FIKSTURU — CANLI VAKA ②'nin AYNASI. ASLA KOSULMAZ.

Canli vaka (28 Agu, cip `clever-rubin-3974c0`): MaCiT evinde (`~/dev/pruvo-hasat`)
bir worktree betiginin ICINDEN KraL evinin araci cagrildi ve kapi GORMEDI —
16 gorsel R2'ye yuklendi:
    subprocess.run(["python3", "/Users/okan/dev/pruvo/tools/r2-upload.py", ...])

Bu dosya ayni vakayi KraL evinde AYNALAR (yon ters, SINIF ayni): caginan ev KraL,
hedef kardes ev. Sentetik degildir — canli vakanin yol ekseni birebir korunmustur.

🔴 GOVDE CAGRILMAZ: fonksiyon tanimlidir, hicbir yerden cagrilmaz ve dosyanin
`__main__` kolu YOKTUR. Kapi govdeyi METIN olarak tarar; kosmasi GEREKMEZ.
"""
import subprocess


def asla_cagrilmaz():
    subprocess.run(["python3", "/Users/okan/dev/pruvo-hasat/tools/r2-upload.py",
                    "--kuru"], capture_output=True, text=True)
