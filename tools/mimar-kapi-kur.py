#!/usr/bin/env python3
"""tools/mimar-icra-kapisi.py'yi .claude/settings.json'daki PreToolUse/Bash zincirine
kaydeder. DAR + IDEMPOTENT + TEK YONLU: yalnizca bu tek kancayi EKLER; hicbir mevcut
kancayi, izni ya da ayari silmez/degistirmez. Zaten kayitliysa dokunmaz.

Neden ayri arac: .claude/ gitignore'da ve commit EDILMIYOR — koruma tek makinede yasiyor.
Ayrica canli kanca konfigurasyonu Okan'in kapisi; muhendis oturumu kendi basina canli
ayar dosyasini degistirmez. Bu araci Okan (ya da mimar) BIR KEZ kostururur:

    python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py            # ne yapacagini yazar
    python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py --uygula   # uygular (yedekli)

Kurulumdan sonra dogrulama:
    python3 /Users/okan/dev/pruvo/tools/mimar-kilit-test.py
"""
import io
import json
import os
import shutil
import sys

AYAR = "/Users/okan/dev/pruvo/.claude/settings.json"
KOMUT = 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-icra-kapisi.py"'
KAYIT = {
    "type": "command",
    "command": KOMUT,
    "timeout": 30,
    "statusMessage": "mimar icra kapisi",
}


PRECOMMIT = "/Users/okan/dev/pruvo/.git/hooks/pre-commit"


def _pretooluse(veri):
    return ((veri.get("hooks") or {}).get("PreToolUse") or [])


def _zincirde_var(veri, matcher_parcasi, dosya_adi):
    """PreToolUse bloklarindan matcher'i verilen parcayi ICEREN blokta, komut
    dizesinde dosya adi geciyor mu? Canli komut
    'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/x.py"' bicimindedir → eslesme dosya ADI
    uzerinden (alt-dize) yapilir."""
    for blok in _pretooluse(veri):
        matcher = blok.get("matcher") or ""
        if matcher_parcasi not in matcher:
            continue
        for kanca in (blok.get("hooks") or []):
            if dosya_adi in (kanca.get("command") or ""):
                return True
    return False


def durum():
    """SALT-OKUNUR kablo raporu. Cikti MAKINE OKUNUR: her satir ANAHTAR=DEGER.
    Uc anahtardan biri 'yok' ise exit 1.

    HEDEF DOSYALAR --ayar / --precommit ile degistirilebilir: kabul testi raporcuyu
    CANLI settings.json'a bagli kalmadan, kendi kurdugu gecici kopyalar uzerinde
    hem POZITIF (hepsi var) hem NEGATIF (biri eksik) yonden sinar. Boylece "durum()
    daima var der" mutasyonu KIRMIZI yanar (eski surumde nobetsizdi)."""
    try:
        veri = json.loads(io.open(AYAR, encoding="utf-8").read())
    except Exception:
        veri = {}

    bash_var = _zincirde_var(veri, "Bash", "mimar-icra-kapisi.py")
    yazma_var = _zincirde_var(veri, "Write", "mimar-kod-kilidi.py")

    precommit_var = False
    try:
        precommit_var = "mimar-commit-kapisi.py" in io.open(
            PRECOMMIT, encoding="utf-8", errors="replace").read()
    except Exception:
        precommit_var = False

    print("BASH_ZINCIRI_ICRA=" + ("var" if bash_var else "yok"))
    print("YAZMA_ZINCIRI_KILIT=" + ("var" if yazma_var else "yok"))
    print("PRECOMMIT_COMMIT_KAPISI=" + ("var" if precommit_var else "yok"))
    print("AYAR_DOSYASI=" + AYAR)
    sys.exit(0 if (bash_var and yazma_var and precommit_var) else 1)


def main():
    global AYAR, PRECOMMIT
    argv = sys.argv[1:]
    uygula = "--uygula" in argv
    if "--ayar" in argv:  # test/kuru kosum icin baska bir settings.json'a isaret et
        AYAR = argv[argv.index("--ayar") + 1]
    if "--precommit" in argv:  # kabul testi kendi HERMETIK kopyasini gosterir
        PRECOMMIT = argv[argv.index("--precommit") + 1]

    if "--durum" in argv:  # SALT-OKUNUR: settings.json'a YAZMAZ
        durum()

    if not os.path.exists(AYAR):
        print("BULUNAMADI: " + AYAR)
        sys.exit(1)

    ham = io.open(AYAR, encoding="utf-8").read()
    veri = json.loads(ham)

    kancalar = veri.setdefault("hooks", {}).setdefault("PreToolUse", [])
    bash_blogu = None
    for blok in kancalar:
        if blok.get("matcher") == "Bash":
            bash_blogu = blok
            break
    if bash_blogu is None:
        bash_blogu = {"matcher": "Bash", "hooks": []}
        kancalar.append(bash_blogu)

    liste = bash_blogu.setdefault("hooks", [])
    if any("mimar-icra-kapisi.py" in (k.get("command") or "") for k in liste):
        print("ZATEN KURULU — degisiklik yok. Dogrula: python3 tools/mimar-kilit-test.py")
        sys.exit(0)

    mevcut = [os.path.basename((k.get("command") or "").split('/')[-1]).strip('"')
              for k in liste]
    print("PreToolUse/Bash zincirinde SU AN: " + (", ".join(mevcut) or "(bos)"))
    print("EKLENECEK               : mimar-icra-kapisi.py")
    print("SILINEN/DEGISEN         : YOK (arac yalnizca ekler)")

    if not uygula:
        print("")
        print("Kuru kosum. Uygulamak icin: python3 " + os.path.abspath(__file__) + " --uygula")
        sys.exit(0)

    liste.append(KAYIT)
    yedek = AYAR + ".yedek"
    shutil.copyfile(AYAR, yedek)
    io.open(AYAR, "w", encoding="utf-8").write(
        json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
    # yazilanin gecerli JSON oldugunu teyit et, degilse yedegi geri koy
    try:
        json.loads(io.open(AYAR, encoding="utf-8").read())
    except Exception as hata:
        shutil.copyfile(yedek, AYAR)
        print("BOZUK JSON URETILDI — yedek geri konuldu. Hata: " + str(hata))
        sys.exit(1)
    print("")
    print("KURULDU. Yedek: " + yedek)
    print("Dogrula: python3 /Users/okan/dev/pruvo/tools/mimar-kilit-test.py")
    print("NOT: kanca yeni oturumda etkin olur.")


main()
