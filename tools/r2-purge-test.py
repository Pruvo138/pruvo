#!/usr/bin/env python3
"""r2-purge.py icin agsiz kabul bataryasi."""

import contextlib
import io
import json
import pathlib
import tempfile
import types
import urllib.error
from unittest import mock


BETIK = pathlib.Path(__file__).with_name("r2-purge.py")
ONARIM = '''    if not urls:
        print("URL YOK")
        return 2

'''
BEYAZ_LISTE = '''    if (
        not anahtar.strip()
        or ANAHTAR_DESENI.fullmatch(anahtar) is None
        or anahtar.startswith("/")
        or anahtar.endswith("/")
        or "//" in anahtar
        or not parcalar
        or any(not parca or parca in (".", "..") for parca in parcalar)
    ):
        raise ValueError("ANAHTAR GECERSIZ")
'''
YALNIZ_BOS_DIZE = '''    if not anahtar:
        raise ValueError("ANAHTAR GECERSIZ")
'''
JETON = "SAHTEJETON123"
HATA_KOLLARI = (
    (
        'print("YETKISIZ (401)", file=sys.stderr)',
        'print("YETKISIZ (401) %s" % jeton, file=sys.stderr)',
        urllib.error.HTTPError("https://ornek.invalid", 401, "yetkisiz", {}, None),
    ),
    (
        'print("HTTP HATASI (%d)" % exc.code, file=sys.stderr)',
        'print("HTTP HATASI (%d) %s" % (exc.code, jeton), file=sys.stderr)',
        urllib.error.HTTPError("https://ornek.invalid", 500, "sunucu", {}, None),
    ),
    (
        'print("AG HATASI", file=sys.stderr)',
        'print("AG HATASI %s" % jeton, file=sys.stderr)',
        urllib.error.URLError("ag yok"),
    ),
    (
        'print("YANIT HATASI", file=sys.stderr)',
        'print("YANIT HATASI %s" % jeton, file=sys.stderr)',
        None,
    ),
)


def modulu_yukle(kaynak=None):
    if kaynak is None:
        kaynak = BETIK.read_text(encoding="utf-8")
    modul = types.ModuleType("r2_purge")
    modul.__file__ = str(BETIK)
    exec(compile(kaynak, str(BETIK), "exec"), modul.__dict__)
    return modul


class SahteYanit:
    def __init__(self, success=True, govde=None):
        self.govde = (
            json.dumps({"success": success}).encode("utf-8")
            if govde is None
            else govde
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.govde


def kos(modul, argv, urlopen, token_path):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch.object(modul, "TOKEN_PATH", token_path), \
            mock.patch.object(modul.urllib.request, "urlopen", urlopen), \
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = modul.main(argv)
    return rc, stdout.getvalue(), stderr.getvalue()


def dogrula(kosul, mesaj):
    if not kosul:
        raise AssertionError(mesaj)


def sizinti_yok(stdout, stderr):
    cikti = stdout + stderr
    return JETON not in cikti and JETON[:8] not in cikti


def sizinti_dogrula(stdout, stderr, mesaj):
    cikti = stdout + stderr
    dogrula(JETON not in cikti, "%s tam jeton" % mesaj)
    dogrula(JETON[:8] not in cikti, "%s ilk 8 karakter" % mesaj)


def hata_urlopen(hata):
    if hata is None:
        return mock.Mock(return_value=SahteYanit(govde=b"JSON DEGIL"))
    return mock.Mock(side_effect=hata)


def anahtar_bataryasi_dusen(modul, gecersizler, gecerliler, token_path):
    dusen = 0
    for anahtar in gecersizler:
        ac = mock.Mock(return_value=SahteYanit())
        rc, stdout, stderr = kos(
            modul, ["--anahtar", anahtar], ac, token_path
        )
        if not (
            rc == 2
            and "ANAHTAR GECERSIZ" in stdout + stderr
            and ac.call_count == 0
        ):
            dusen += 1
    for anahtar in gecerliler:
        ac = mock.Mock(return_value=SahteYanit())
        rc, _, _ = kos(modul, ["--anahtar", anahtar], ac, token_path)
        beklenen = "https://media.pruvo3d.com/" + anahtar
        if rc != 0 or ac.call_count != 1:
            dusen += 1
            continue
        govde = json.loads(ac.call_args.args[0].data.decode("utf-8"))
        if govde["files"] != [beklenen]:
            dusen += 1
    return dusen


def main():
    modul = modulu_yukle()
    dusen = 0
    reddedilen = 0
    yanlis_pozitif = 0
    gecersiz_anahtarlar = (
        "",
        "   ",
        "//baska-alan.com/x.jpg",
        "urunler/%2e%2e/gizli",
        "https://baska-alan.com/x.jpg",
        "HTTPS://baska-alan.com/x.jpg",
        "/urunler/x.jpg",
        "urunler/x.jpg/",
        "urunler//x.jpg",
        "urunler/./x.jpg",
        "urunler/../x.jpg",
        "urunler/x jpg.jpg",
        "urunler/x?a=1",
        "urunler/x#p",
    )
    gecerli_anahtarlar = (
        "urunler/normal-1.jpg",
        "urunler/alt-klasor/ad_2.jpg",
        "urunler/ad.with.dots-3.jpg",
    )

    with tempfile.TemporaryDirectory() as gecici:
        kok = pathlib.Path(gecici)
        yok_token = kok / "yok-token"
        sahte_token = kok / "token"
        sahte_token.write_text(JETON + "\n", encoding="utf-8")

        try:
            ac = mock.Mock(return_value=SahteYanit())
            rc, stdout, _ = kos(modul, ["https://media.pruvo3d.com/urunler/x.jpg"], ac, yok_token)
            dogrula(rc == 2 and "JETON YOK" in stdout and ac.call_count == 0, "T1")
        except Exception:
            dusen += 1

        try:
            ac = mock.Mock(return_value=SahteYanit())
            urls = ["https://media.pruvo3d.com/urunler/%d.jpg" % i for i in range(60)]
            rc, _, _ = kos(modul, urls, ac, sahte_token)
            boyutlar = [len(json.loads(c.args[0].data.decode("utf-8"))["files"]) for c in ac.call_args_list]
            dogrula(rc == 0 and ac.call_count == 2 and boyutlar == [30, 30], "T2")
        except Exception:
            dusen += 1

        try:
            ac = mock.Mock(return_value=SahteYanit())
            rc, _, _ = kos(modul, ["--anahtar", "urunler/x-1.jpg"], ac, sahte_token)
            govde = json.loads(ac.call_args.args[0].data.decode("utf-8"))
            dogrula(
                rc == 0 and govde["files"] == ["https://media.pruvo3d.com/urunler/x-1.jpg"],
                "T3",
            )
        except Exception:
            dusen += 1

        try:
            ac = mock.Mock(return_value=SahteYanit())
            _, stdout, stderr = kos(
                modul, ["https://media.pruvo3d.com/urunler/x.jpg"], ac, sahte_token
            )
            sizinti_dogrula(stdout, stderr, "T4")
        except Exception:
            dusen += 1

        try:
            ac = mock.Mock(return_value=SahteYanit(success=False))
            rc, _, _ = kos(modul, ["https://media.pruvo3d.com/urunler/x.jpg"], ac, sahte_token)
            dogrula(rc == 1, "T5")
        except Exception:
            dusen += 1

        try:
            ac = mock.Mock(return_value=SahteYanit())
            with mock.patch.object(
                modul, "jeton_oku", side_effect=AssertionError("jeton okunmamali")
            ):
                rc, stdout, _ = kos(modul, [], ac, sahte_token)
            dogrula(rc == 2 and "URL YOK" in stdout and ac.call_count == 0, "T6")
        except Exception:
            dusen += 1

        try:
            kaynak = BETIK.read_text(encoding="utf-8")
            mutant_kaynak = kaynak.replace(ONARIM, "", 1)
            dogrula(mutant_kaynak != kaynak, "T7 mutant uygulanamadi")
            mutant = modulu_yukle(mutant_kaynak)
            ac = mock.Mock(return_value=SahteYanit())
            rc, stdout, _ = kos(mutant, [], ac, sahte_token)
            mutant_yakalandi = not (
                rc == 2 and "URL YOK" in stdout and ac.call_count == 0
            )
            dogrula(rc == 0 and ac.call_count == 0 and mutant_yakalandi, "T7")
        except Exception:
            dusen += 1

        try:
            ac = hata_urlopen(HATA_KOLLARI[0][2])
            rc, stdout, stderr = kos(
                modul, ["https://media.pruvo3d.com/urunler/x.jpg"], ac, sahte_token
            )
            dogrula(rc != 0, "T8 rc")
            sizinti_dogrula(stdout, stderr, "T8")
        except Exception:
            dusen += 1

        try:
            ac = hata_urlopen(HATA_KOLLARI[1][2])
            rc, stdout, stderr = kos(
                modul, ["https://media.pruvo3d.com/urunler/x.jpg"], ac, sahte_token
            )
            dogrula(rc != 0, "T9 rc")
            sizinti_dogrula(stdout, stderr, "T9")
        except Exception:
            dusen += 1

        try:
            ac = hata_urlopen(HATA_KOLLARI[2][2])
            rc, stdout, stderr = kos(
                modul, ["https://media.pruvo3d.com/urunler/x.jpg"], ac, sahte_token
            )
            dogrula(rc != 0, "T10 rc")
            sizinti_dogrula(stdout, stderr, "T10")
        except Exception:
            dusen += 1

        try:
            ac = hata_urlopen(HATA_KOLLARI[3][2])
            rc, stdout, stderr = kos(
                modul, ["https://media.pruvo3d.com/urunler/x.jpg"], ac, sahte_token
            )
            dogrula(rc != 0, "T11 rc")
            sizinti_dogrula(stdout, stderr, "T11")
        except Exception:
            dusen += 1

        yakalanan_kol = 0
        try:
            kaynak = BETIK.read_text(encoding="utf-8")
            for eski, yeni, hata in HATA_KOLLARI:
                mutant_kaynak = kaynak.replace(eski, yeni, 1)
                dogrula(mutant_kaynak != kaynak, "T12 mutant uygulanamadi")
                mutant = modulu_yukle(mutant_kaynak)
                ac = hata_urlopen(hata)
                rc, stdout, stderr = kos(
                    mutant,
                    ["https://media.pruvo3d.com/urunler/x.jpg"],
                    ac,
                    sahte_token,
                )
                if rc != 0 and not sizinti_yok(stdout, stderr):
                    yakalanan_kol += 1
            dogrula(yakalanan_kol == 4, "T12")
        except Exception:
            dusen += 1

        anahtar_red_rc = -1
        try:
            ac = mock.Mock(return_value=SahteYanit())
            anahtar_red_rc, stdout, stderr = kos(
                modul, ["--anahtar", "https://baska-alan.com/x.jpg"], ac, sahte_token
            )
            dogrula(
                anahtar_red_rc == 2
                and "ANAHTAR GECERSIZ" in stdout + stderr
                and ac.call_count == 0,
                "T13",
            )
            sizinti_dogrula(stdout, stderr, "T13")
        except Exception:
            dusen += 1

        try:
            ac = mock.Mock(return_value=SahteYanit())
            rc, stdout, stderr = kos(
                modul, ["--anahtar", "urunler/../../gizli"], ac, sahte_token
            )
            dogrula(
                rc == 2
                and "ANAHTAR GECERSIZ" in stdout + stderr
                and ac.call_count == 0,
                "T14",
            )
            sizinti_dogrula(stdout, stderr, "T14")
        except Exception:
            dusen += 1

        try:
            ac = mock.Mock(return_value=SahteYanit())
            rc, _, _ = kos(
                modul, ["--anahtar", "urunler/normal-1.jpg"], ac, sahte_token
            )
            govde = json.loads(ac.call_args.args[0].data.decode("utf-8"))
            dogrula(
                rc == 0
                and ac.call_count == 1
                and govde["files"]
                == ["https://media.pruvo3d.com/urunler/normal-1.jpg"],
                "T15",
            )
        except Exception:
            dusen += 1

        for sira, anahtar in enumerate(gecersiz_anahtarlar, start=16):
            try:
                ac = mock.Mock(return_value=SahteYanit())
                rc, stdout, stderr = kos(
                    modul, ["--anahtar", anahtar], ac, sahte_token
                )
                dogrula(
                    rc == 2
                    and "ANAHTAR GECERSIZ" in stdout + stderr
                    and ac.call_count == 0,
                    "T%d" % sira,
                )
                reddedilen += 1
            except Exception:
                dusen += 1

        for sira, anahtar in enumerate(gecerli_anahtarlar, start=30):
            try:
                ac = mock.Mock(return_value=SahteYanit())
                rc, _, _ = kos(
                    modul, ["--anahtar", anahtar], ac, sahte_token
                )
                beklenen = "https://media.pruvo3d.com/" + anahtar
                govde = json.loads(ac.call_args.args[0].data.decode("utf-8"))
                dogrula(
                    rc == 0
                    and ac.call_count == 1
                    and govde["files"] == [beklenen],
                    "T%d" % sira,
                )
            except Exception:
                yanlis_pozitif += 1
                dusen += 1

        try:
            kaynak = BETIK.read_text(encoding="utf-8")
            mutant_kaynak = kaynak.replace(BEYAZ_LISTE, "", 1)
            dogrula(mutant_kaynak != kaynak, "T33 mutant uygulanamadi")
            mutant = modulu_yukle(mutant_kaynak)
            dogrula(
                anahtar_bataryasi_dusen(
                    mutant,
                    gecersiz_anahtarlar,
                    gecerli_anahtarlar,
                    sahte_token,
                ) > 0,
                "T33 mutant bataryayi kirmadi",
            )
        except Exception:
            dusen += 1

        try:
            kaynak = BETIK.read_text(encoding="utf-8")
            mutant_kaynak = kaynak.replace(BEYAZ_LISTE, YALNIZ_BOS_DIZE, 1)
            dogrula(mutant_kaynak != kaynak, "T34 mutant uygulanamadi")
            mutant = modulu_yukle(mutant_kaynak)
            dogrula(
                anahtar_bataryasi_dusen(
                    mutant,
                    gecersiz_anahtarlar,
                    gecerli_anahtarlar,
                    sahte_token,
                ) > 0,
                "T34 mutant bataryayi kirmadi",
            )
        except Exception:
            dusen += 1

    print("TEST=VAKA=34 DUSEN=%d" % dusen)
    print("RED_EDILEN=%d/14" % reddedilen)
    print("YANLIS_POZITIF=%d" % yanlis_pozitif)
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
