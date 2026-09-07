#!/usr/bin/env python3
"""MOTOR-YOK KAPISI — kabul + mutant (KraL-KimiIptal-7Eyl, madde 5).

OKAN KARARI (6 Eyl 2026, 17:4x — BaBa kutuya yazdi): yedek motor IPTAL,
`minimax-m3` TEK motor. Buradaki hukum sudur:

    🔴 m3 DUSERSE KOSUM DURUR — CLAUDE'A DUSMEZ.

OLCULEN KUSUR (bu kapi kurulmadan onceki davranis): `isci.sh` uc motorunun
anahtar dosyasini okuyamazsa ortam override'larini KURMUYOR ama kosumu da
DURDURMUYORDU. `CLAUDE_ENV` o noktada zaten DOGAL Claude ayarlariyla kurulu
oldugu icin tur sessizce Okan'in Claude hesabinda kosuyor, log'a yalnizca
"(geri-donus: anahtar yok)" diye bir ETIKET dusuyordu. Yani "ucuz kata
verdim" karari faturayi Claude'a cevirebiliyordu.

NE OLCULUR (iki kol — biri olmadan digeri hukumsuzdur):
  MUTANT  : m3 ucu BOZUK (anahtar dosyasi YOK) -> rc=1 + stderr'de
            `HAL=MOTOR-YOK` + sahte claude ikilisi HIC CAGRILMADI.
  KONTROL : ayni izole kurulum, anahtar VAR -> `HAL=MOTOR-YOK` BASILMAZ.
            Bu kol olmadan mutant hukumsuzdur: kapi her kosumda kirmizi
            yaniyor da olabilirdi ([[mutantli-kosum-tabanla-ayniysa-mutant-
            ulasmadi]]). Kontrol, kolun GERCEKTEN o dalda ateslendigini
            kanitlar.

IZOLASYON (Okan disk kurali + filo dersi):
  * Mutant CANLI govdede KOSMAZ — `tempfile.mkdtemp` altinda izole bir
    CRON_KOKU kurulur ([[mutant-canli-govdede-yasamaz]]).
  * GERCEK `.minimax-anahtar` OKUNMAZ, KOPYALANMAZ, SILINMEZ. Kontrol kolu
    kendi SAHTE anahtarini yazar.
  * GERCEK `isci.log` KIRLETILMEZ: izole kokte bos bir log kullanilir.
  * Silme yalnizca `tempfile.mkdtemp` ile alinan yol AGACINDA yapilir ve
    once o yolun gercekten gecici oldugu DOGRULANIR (gercek ev yoluna
    `rmtree` = filo dersi geregi KIRMIZI).
  * Destek dosyalari KOPYALANMAZ, SEMBOLIK BAGLANIR (181 MB'lik cron
    agacini cogaltmak Okan disk kuralini ihlal ederdi).

KOSUM:  python3 tools/motor-yok-kapisi-test.py
CIKTI:  VAKA=<ad> BEKLENEN=<x> OLCULEN=<y> SONUC=GECTI|KALDI
        son satir: KABUL=GECTI|KALDI (rc=0 ise iki kol da gecti)
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile

GERCEK_CRON = "/Users/okan/.claude/cron"
GERCEK_ISCI = os.path.join(GERCEK_CRON, "isci.sh")
GERCEK_SABITLER = os.path.join(GERCEK_CRON, "isci-sabitler.zsh")
ANAHTAR_ADI = ".minimax-anahtar"
MOTOR = "minimax-m3"

# Izole kokte SEMBOLIK BAGLANMAYACAK olanlar: ya yeniden yazilir (isci.sh,
# sabitler, log) ya da BILEREK yok birakilir (mutantta anahtar).
BAGLANMAZ = {"isci.sh", "isci-sabitler.zsh", "isci.log", ANAHTAR_ADI}


def _izole_kok_kur(tmp, anahtar_yaz):
    """Izole bir CRON_KOKU kurar. anahtar_yaz=False ise m3 ucu BOZUKTUR."""
    kok = os.path.join(tmp, "cron")
    os.makedirs(kok, exist_ok=True)

    # 1) Destek yuzeyi: gercek cron agacindaki her girdi SEMBOLIK baglanir.
    for ad in os.listdir(GERCEK_CRON):
        if ad in BAGLANMAZ:
            continue
        hedef = os.path.join(GERCEK_CRON, ad)
        bag = os.path.join(kok, ad)
        try:
            os.symlink(hedef, bag)
        except OSError:
            pass

    # 2) Sabitler: CRON_KOKU izole koke CIVILENIR (tek satir degisir).
    with open(GERCEK_SABITLER, encoding="utf-8") as f:
        sabitler = f.read()
    civili = sabitler.replace(
        "CRON_KOKU=" + GERCEK_CRON, "CRON_KOKU=" + kok, 1)
    if civili == sabitler:
        return None, "SABITLER_CAPASI_TUTMADI"
    with open(os.path.join(kok, "isci-sabitler.zsh"), "w", encoding="utf-8") as f:
        f.write(civili)

    # 3) isci.sh: BIREBIR kopya (olculen govde CANLI govdedir).
    shutil.copy2(GERCEK_ISCI, os.path.join(kok, "isci.sh"))
    os.chmod(os.path.join(kok, "isci.sh"), 0o755)

    # 4) Bos log (gercek isci.log KIRLETILMEZ).
    open(os.path.join(kok, "isci.log"), "w", encoding="utf-8").close()

    # 5) Anahtar: yalnizca KONTROL kolunda, SAHTE icerikle.
    if anahtar_yaz:
        ay = os.path.join(kok, ANAHTAR_ADI)
        with open(ay, "w", encoding="utf-8") as f:
            f.write("sahte-anahtar-yalnizca-test\n")
        os.chmod(ay, stat.S_IRUSR | stat.S_IWUSR)

    return kok, None


# ESKI (kaldirilan) davranisin BIREBIR metni. 3. kol bunu IZOLE kopyaya geri
# koyar: kapi kaldirilirsa testin GERCEKTEN kirmizi yandigini olcer.
ESKI_KOL_CAPA = "    exit 1\n    # === MOTOR-YOK KAPISI SON ==="
ESKI_KOL_YERINE = ('    LOG_MOTOR="$ISTENEN_MOTOR (geri-donus: anahtar yok)"\n'
                   "    # === MOTOR-YOK KAPISI SON ===")


def _eski_kola_dondur(kok):
    """Izole kopyadaki MOTOR-YOK kolunu ESKI geri-donus haline cevirir."""
    yol = os.path.join(kok, "isci.sh")
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    if ESKI_KOL_CAPA not in govde:
        return "CAPA_TUTMADI"  # fail-closed: capa kaydiysa hukum verilmez
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(ESKI_KOL_CAPA, ESKI_KOL_YERINE, 1))
    return None


def _kos(tmp, kok, etiket):
    """Izole isci.sh'i sahte claude ikilisiyle kosar."""
    bin_dizin = os.path.join(tmp, "bin")
    os.makedirs(bin_dizin, exist_ok=True)
    capture = os.path.join(tmp, "claude-cagrildi.txt")
    sahte = os.path.join(bin_dizin, "claude")
    with open(sahte, "w", encoding="utf-8") as f:
        f.write(
            "#!/bin/bash\n"
            "# Sahte claude: GERCEK API CAGRISI YAPMAZ. Cagrildigini kaydeder.\n"
            'echo "CAGRILDI model=${ANTHROPIC_MODEL:-yok}" >> "' + capture + '"\n'
            "exit 0\n")
    os.chmod(sahte, 0o755)

    ev = os.path.join(tmp, "ev")
    os.makedirs(ev, exist_ok=True)
    spec = os.path.join(tmp, "spec.md")
    with open(spec, "w", encoding="utf-8") as f:
        f.write("# GECICI TEST SPEC — is YAPMAZ (motor-yok-kapisi-test)\n")

    ortam = dict(os.environ)
    ortam["PRUVO_ISCI_CLAUDE_BIN"] = sahte
    ortam.pop("PRUVO_CLAUDE_ISCI_IZNI", None)  # izin kolu BU dali ACMAMALI

    p = subprocess.run(
        [os.path.join(kok, "isci.sh"), MOTOR, ev, spec, etiket],
        capture_output=True, text=True, env=ortam, timeout=300)
    claude_cagrildi = os.path.exists(capture) and os.path.getsize(capture) > 0
    return p.returncode, (p.stdout or "") + (p.stderr or ""), claude_cagrildi


def _guvenli_sil(yol, tmp_onek):
    """Yalnizca gercekten gecici olan agaci siler (filo dersi)."""
    gercek = os.path.realpath(yol)
    if not os.path.basename(gercek).startswith(tmp_onek):
        print("TEMIZLIK_ATLANDI: gecici olmayan yol " + gercek)
        return
    for korunan in (GERCEK_CRON, os.path.expanduser("~/dev"),
                    os.path.expanduser("~/.claude/projects")):
        if gercek == korunan or gercek.startswith(korunan + os.sep):
            print("TEMIZLIK_ATLANDI: korunan agac " + gercek)
            return
    shutil.rmtree(gercek, ignore_errors=True)


def main():
    # 🔴 ON KOSUL: bu kapi CANLI isci hattini (`~/.claude/cron`) olcer; o hat
    # CI kosucusunda YOKTUR. Orada "yesil" basmak SAHTE YESIL olurdu, "kirmizi"
    # basmak ise tum ekibin yayinini yanlis-pozitifle durdururdu. Ucuncu hal:
    # ONKOSUL_YOK + rc=3 (bu depoda `isci-*-test.py` ailesinin kanonu). Bu
    # dosya BILEREK `deploy.yml`e BAGLANMAZ; hukmu YEREL kosumda okunur.
    if not os.path.isdir(GERCEK_CRON) or not os.path.isfile(GERCEK_ISCI):
        print("ONKOSUL_YOK: canli isci hatti yok (" + GERCEK_CRON + ")")
        print("KABUL=OLCULEMEDI (0 vaka) — bu kapi YEREL kosulur, CI'da DEGIL")
        return 3

    onek = "motor-yok-test-"
    tmp = tempfile.mkdtemp(prefix=onek)
    sonuclar = []
    try:
        # ---------------- MUTANT: m3 ucu BOZUK (anahtar YOK) ----------------
        m_tmp = os.path.join(tmp, "mutant")
        os.makedirs(m_tmp, exist_ok=True)
        kok, hata = _izole_kok_kur(m_tmp, anahtar_yaz=False)
        if hata:
            print("VAKA=mutant BEKLENEN=izole-kurulum OLCULEN=" + hata +
                  " SONUC=KALDI")
            sonuclar.append(False)
        else:
            rc, cikti, claude_cagrildi = _kos(m_tmp, kok, "kabul-motor-yok-mutant")
            hal_var = "HAL=MOTOR-YOK" in cikti
            gecti = (rc == 1) and hal_var and (not claude_cagrildi)
            print("VAKA=mutant BEKLENEN=rc=1+HAL=MOTOR-YOK+claude-cagrilmadi "
                  "OLCULEN=rc=%d hal_motor_yok=%s claude_cagrildi=%s SONUC=%s"
                  % (rc, hal_var, claude_cagrildi, "GECTI" if gecti else "KALDI"))
            if not gecti:
                print("  MUTANT_CIKTI(son 400): " + cikti.strip()[-400:])
            sonuclar.append(gecti)

        # ---------------- KONTROL: anahtar VAR -> MOTOR-YOK BASILMAZ --------
        k_tmp = os.path.join(tmp, "kontrol")
        os.makedirs(k_tmp, exist_ok=True)
        kok2, hata2 = _izole_kok_kur(k_tmp, anahtar_yaz=True)
        if hata2:
            print("VAKA=kontrol BEKLENEN=izole-kurulum OLCULEN=" + hata2 +
                  " SONUC=KALDI")
            sonuclar.append(False)
        else:
            rc2, cikti2, _ = _kos(k_tmp, kok2, "kabul-motor-yok-kontrol")
            hal_var2 = "HAL=MOTOR-YOK" in cikti2
            gecti2 = not hal_var2
            print("VAKA=kontrol BEKLENEN=HAL=MOTOR-YOK-BASILMAZ "
                  "OLCULEN=rc=%d hal_motor_yok=%s SONUC=%s"
                  % (rc2, hal_var2, "GECTI" if gecti2 else "KALDI"))
            if not gecti2:
                print("  KONTROL_CIKTI(son 400): " + cikti2.strip()[-400:])
            sonuclar.append(gecti2)

        # -------- KAPI-KALDIRILDI mutanti: test GERCEKTEN kirmizi yanar mi? --
        # 🔴 Bu kol olmadan yukaridaki iki kol "kapi var" demez, yalnizca
        # "bugun boyle davraniyor" der. Burada kapiyi IZOLE kopyadan
        # SOKUYORUZ ve mutant kolunun olcutunun DUSMESINI bekliyoruz.
        e_tmp = os.path.join(tmp, "eski")
        os.makedirs(e_tmp, exist_ok=True)
        kok3, hata3 = _izole_kok_kur(e_tmp, anahtar_yaz=False)
        capa_hatasi = hata3 or _eski_kola_dondur(kok3) if not hata3 else hata3
        if hata3 or capa_hatasi:
            print("VAKA=kapi-kaldirildi BEKLENEN=izole-mutant OLCULEN=" +
                  str(hata3 or capa_hatasi) + " SONUC=KALDI")
            sonuclar.append(False)
        else:
            rc3, cikti3, claude3 = _kos(e_tmp, kok3, "kabul-motor-yok-eski")
            hal3 = "HAL=MOTOR-YOK" in cikti3
            # Kapi SOKULDUGU icin mutant olcutu DUSMELI: ya MOTOR-YOK
            # basilmaz ya da claude CAGRILIR (eski sessiz dusus).
            olcut_dustu = (not hal3) or claude3
            print("VAKA=kapi-kaldirildi BEKLENEN=mutant-olcutu-DUSER "
                  "OLCULEN=rc=%d hal_motor_yok=%s claude_cagrildi=%s SONUC=%s"
                  % (rc3, hal3, claude3, "GECTI" if olcut_dustu else "KALDI"))
            if not olcut_dustu:
                print("  ESKI_CIKTI(son 400): " + cikti3.strip()[-400:])
            sonuclar.append(olcut_dustu)
    finally:
        _guvenli_sil(tmp, onek)

    hukum = "GECTI" if all(sonuclar) and len(sonuclar) == 3 else "KALDI"
    print("KABUL=%s (%d vaka)" % (hukum, len(sonuclar)))
    return 0 if hukum == "GECTI" else 1


if __name__ == "__main__":
    sys.exit(main())
