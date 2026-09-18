#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/k340-menzil-kabul-test.py — İCRA KAPISI MENZİL bataryası (K340 · K336 · K332).

NE ÖLÇER (üç eksen, hepsi `tools/mimar-icra-kapisi.py`):
  K340① ETKİN CWD — kapı komutun DİZGESİNİ değil ETKİSİNİ ölçer: `cd <dizin> &&` ve
        `env -C/--chdir <dizin>` ile kaydırılan cwd çözülür, göreli yol ONA göre
        normalize edilir. Ölçülen kaçak (16 Eyl, canlı kapıya doğrudan çağrı):
          `env -C /private/tmp python3 x.py`      -> allow (iz=MIMAR-kural-yok)
          `cd /private/tmp && python3 x.py`       -> allow
          `env -C /private/tmp curl -s <url>`     -> allow  (curl yasağı da turlanıyordu)
  K340② BETİK İÇİ ÇAĞRI — repo İÇİ bir betiğin İÇİNDEN koşturulan repo DIŞI hedef
        artık ADIYLA stderr'e yazılır (`BETIK-ICI-DIS-CAGRI`). Bu kol RAPOR eder,
        REDDETMEZ (11 Eyl sözleşmesi); sessiz geçit değildir, ÖLÇÜLEN geçittir.
  K336  DAĞITIM AİLESİ — `kapi-dagitim-kapisi.py --ev <kardeş kök>` (doğrulama ayağı)
        kurucu ile AYNI kovadadır; `--filo` biçimi ve kayıtsız ev sınırı korunur.
  K332  ORTAK ALTYAPI — çipte `~/.claude/cron/` açılır, ANA oturumda KAPALI kalır;
        KONTROL: düzlem DIŞI repo-dışı yol çipte de REDDEDİLİR.

BİÇİM: her vaka bir KOMUT + BEKLENEN KARAR (+ opsiyonel İZ ÇAPASI). Mutantlar
ÖLDÜRDÜĞÜ KOLU ADIYLA basar; taban ile AYNI sonuç = mutant hedefe ULAŞMADI.

🔴 CI SINIRI SESSİZ DEĞİL: kanonik ev (`/Users/okan/dev/pruvo`) ve `~/.claude/cron/`
düzlemi CI'da YOKTUR. O vakalar uydurulmaz, `CI-DISI` adıyla basılır ve ayrı sayılır
(`CIDISI=` alanı) — yeşil sayılmazlar.

Kullanım:
    python3 tools/k340-menzil-kabul-test.py            # taban + mutasyon turu
    python3 tools/k340-menzil-kabul-test.py --taban    # yalnız taban batarya
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

BU = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(BU, "mimar-icra-kapisi.py")
BAGIMLILIKLAR = ("mimar_kimlik.py", "serbest_cagrilar.py", "kapi_dagitim.py")

KANONIK_EV = "/Users/okan/dev/pruvo"
CRON_KOK = os.path.expanduser("~/.claude/cron")

CAPA_REPO = 'REPO_ONEKI = "/Users/okan/dev/pruvo/"'
CAPA_WT = 'GIT_WORKTREE_KAYIT = "/Users/okan/dev/pruvo/.git/worktrees"'


def _damga(yol):
    return "".join(k if k.isalnum() else "-" for k in yol)


def _kapi_metni():
    with open(KAPI, encoding="utf-8") as f:
        return f.read()


def kopya_kur(dizin, metin):
    """Kapının İZOLE kopyası + bağımlılıkları. Döner: kopyanın yolu."""
    os.makedirs(dizin, exist_ok=True)
    for ad in BAGIMLILIKLAR:
        kaynak = os.path.join(BU, ad)
        if os.path.exists(kaynak):
            shutil.copy2(kaynak, os.path.join(dizin, ad))
    yol = os.path.join(dizin, "mimar-icra-kapisi.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return yol


def ev_fiksturu_kur(taban, metin):
    """Sentetik EV (kapının çapaları fikstür köküne çevrilir) + kayıtlı çip ağacı.

    Döner: (kok, wt, dis, kapi_yolu). `dis` repo DIŞI bir dizindir."""
    kok = os.path.realpath(os.path.join(taban, "ev"))
    wt = os.path.realpath(os.path.join(kok, ".claude", "worktrees", "cip-1"))
    dis = os.path.realpath(os.path.join(taban, "disarda"))
    os.makedirs(os.path.join(kok, "tools"))
    os.makedirs(os.path.join(kok, ".git", "worktrees", "cip-1"))
    os.makedirs(os.path.join(wt, "tools"))
    os.makedirs(dis)
    with open(os.path.join(kok, ".git", "worktrees", "cip-1", "gitdir"), "w",
              encoding="utf-8") as f:
        f.write(os.path.join(wt, ".git") + "\n")
    with open(os.path.join(wt, ".git"), "w", encoding="utf-8") as f:
        f.write("gitdir: " + os.path.join(kok, ".git", "worktrees", "cip-1") + "\n")

    if CAPA_REPO not in metin or CAPA_WT not in metin:
        raise RuntimeError("CAPA KIRIK: kapının REPO_ONEKI/GIT_WORKTREE_KAYIT çapası "
                           "bulunamadı — fikstür evi kurulamaz")
    metin = metin.replace(CAPA_REPO, 'REPO_ONEKI = "' + kok + '/"')
    metin = metin.replace(CAPA_WT, 'GIT_WORKTREE_KAYIT = "' + kok +
                          '/.git/worktrees"')

    # repo İÇİ araçlar + repo DIŞI hedef
    with open(os.path.join(dis, "arac.py"), "w", encoding="utf-8") as f:
        f.write("print('disarda')\n")
    with open(os.path.join(kok, "tools", "arac.py"), "w", encoding="utf-8") as f:
        f.write("import subprocess\n"
                "subprocess.run(['python3', 'tools/ikinci.py'])\n")
    with open(os.path.join(kok, "tools", "ikinci.py"), "w", encoding="utf-8") as f:
        f.write("print('repo ici')\n")
    # K340② fikstürü: repo İÇİ betik, İÇİNDE repo DIŞI çağrı
    with open(os.path.join(kok, "tools", "disari-cagiran.py"), "w",
              encoding="utf-8") as f:
        f.write("import subprocess\n"
                "subprocess.run(['python3', '" +
                os.path.join(dis, "arac.py") + "'])\n")
    # K340 REGRESYON FİKSTÜRÜ (canlı vakanın birebir biçimi)
    with open(os.path.join(kok, "tools", "d1-sync.py"), "w", encoding="utf-8") as f:
        f.write("print('durum')\n")
    return kok, wt, dis, kopya_kur(os.path.join(kok, "tools"), metin)


def _yuk(komut, tp_kok, cwd):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": komut},
        "transcript_path": "/x/.claude/projects/" + _damga(tp_kok) + "/o.jsonl",
        "cwd": cwd,
        "session_id": "s-olcum",
        "permission_mode": "bypassPermissions",
    }


def _cevre():
    """Koşucunun KİMLİĞİ ölçümü kirletmesin: PRUVO_ISCI_KOSUMU/agent izi temizlenir
    ([[isci-kirmizi-iddiasi-kendi-baglamindan-dogar]] dersinin ters yönü)."""
    e = dict(os.environ)
    for k in list(e):
        if k.startswith("PRUVO_ISCI") or k == "PRUVO_CLAUDE_ISCI_IZNI":
            e.pop(k, None)
    return e


def kos(kapi_yolu, komut, tp_kok, cwd):
    """Döner: (karar, stderr). Karar: allow/deny/COKTU."""
    p = subprocess.run([sys.executable, kapi_yolu],
                       input=json.dumps(_yuk(komut, tp_kok, cwd)),
                       capture_output=True, text=True, timeout=120, env=_cevre())
    if p.returncode != 0:
        return "COKTU", (p.stderr or "")[:200]
    if not p.stdout.strip():
        return "allow", p.stderr or ""
    try:
        h = (json.loads(p.stdout).get("hookSpecificOutput") or {})
    except Exception:
        return "PARSE-HATASI", (p.stdout or "")[:200]
    return (h.get("permissionDecision") or "allow"), p.stderr or ""


# ---------------------------------------------------------------------------
def vakalar(metin):
    """TÜM vakaları koşar. Döner: [(ad, gecti_mi, not)]."""
    sonuc = []
    cidisi = []

    def ekle(ad, kosul, notu=""):
        sonuc.append((ad, bool(kosul), str(notu)[:60]))

    taban = tempfile.mkdtemp(prefix="k340-menzil-")
    try:
        kok, wt, dis, kapi = ev_fiksturu_kur(taban, metin)
        tp_ana, tp_cip = kok, wt

        def olc(ad, komut, beklenen, tp=None, cwd=None, iz_capasi=None,
                iz_olmamali=None):
            karar, iz = kos(kapi, komut, tp or tp_ana, cwd or kok)
            ok = (karar == beklenen)
            notu = karar
            if ok and iz_capasi is not None:
                ok = iz_capasi in iz
                notu = karar + " iz=" + ("VAR" if ok else "YOK:" + iz_capasi)
            if ok and iz_olmamali is not None:
                ok = iz_olmamali not in iz
                notu = karar + " iz-yok=" + ("TAMAM" if ok else "SIZDI")
            ekle(ad, ok, notu)

        # === K340① ETKİN CWD — POZİTİF (kaçak KAPANDI mı?) ===================
        olc("V1a K340① `cd <disari> &&` goreli betik -> RED",
            "cd " + dis + " && python3 arac.py", "deny")
        olc("V1b K340① `env -C <disari>` -> RED",
            "env -C " + dis + " python3 arac.py", "deny")
        olc("V1c K340① `env --chdir=<disari>` -> RED",
            "env --chdir=" + dis + " python3 arac.py", "deny")
        olc("V1d K340① `env -C<disari>` (bitisik bicim) -> RED",
            "env -C" + dis + " python3 arac.py", "deny")
        olc("V1e K340① sarmalayici bayrak degeri argv0'i YUTMAZ (curl) -> RED",
            "env -C " + dis + " curl -s https://pruvo3d.com/", "deny")
        olc("V1f K340① `cd <disari>` SONRAKI segmente TASINIR -> RED",
            "cd " + dis + " ; python3 arac.py", "deny")
        # 🔴 `cd -` DEGIL `cd "$VAR"`: `cd -` token'i '-' ile basladigi icin BAYRAK
        # sayilir ve ciplak `cd` koluna (HOME) duser — yani cozulemezlik kolunu
        # OLCMEZDI. Olculdu (16 Eyl): `cd -` fikstürüyle M4 mutanti HEDEFE ULASMADI.
        olc("V1g K340① cozulemeyen kaydirma (`cd \"$VAR\"`) DISARI sayilir -> RED",
            'cd "$HEDEF" && python3 arac.py', "deny")
        olc("V1i K340① ciplak `cd` (HOME) repo DISIDIR -> RED",
            "cd && python3 arac.py", "deny")
        olc("V1h K340① CIP de kaydirmayi TURLAYAMAZ -> RED",
            "cd " + dis + " && python3 arac.py", "deny", tp=tp_cip, cwd=wt)

        # === K340① KONTROL — mesru cagri SERBEST (alarma donusmedi) ==========
        olc("V2a KONTROL repo-ici cagri (kaydirmasiz) GECER",
            "python3 tools/arac.py", "allow")
        olc("V2b KONTROL `cd <repo koku> &&` repo-ici betik GECER",
            "cd " + kok + " && python3 tools/arac.py", "allow")
        olc("V2c KONTROL `env -C <repo ici dizin>` GECER",
            "env -C " + os.path.join(kok, "tools") + " python3 arac.py", "allow")
        olc("V2d KONTROL REGRESYON: canli vaka birebir (`env -C <ev> "
            "python3 tools/d1-sync.py --durum`) GECER",
            "env -C " + kok + " python3 tools/d1-sync.py --durum", "allow")
        olc("V2e KONTROL `nice -n 10` bayrak degeri argv0 SANILMAZ",
            "nice -n 10 python3 tools/arac.py", "allow")

        # === K340② BETİK İÇİ ÇAĞRI (RAPOR kolu — karar DEGISMEZ) ============
        olc("V3a K340② repo-disi hedefi cagiran betik ADIYLA RAPOR EDILIR",
            "python3 tools/disari-cagiran.py", "allow",
            iz_capasi="BETIK-ICI-DIS-CAGRI")
        olc("V3b K340② rapor HEDEFI tasir (dizge degil COZULMUS yol)",
            "python3 tools/disari-cagiran.py", "allow",
            iz_capasi=os.path.join(dis, "arac.py"))
        olc("V3c K340② KONTROL repo-ICI cagri RAPOR URETMEZ (gurultu yok)",
            "python3 tools/ikinci.py", "allow",
            iz_olmamali="BETIK-ICI-DIS-CAGRI")
        olc("V3d K340② KARAR DEGISMEDI: rapor RED'e donusmez",
            "python3 tools/disari-cagiran.py", "allow")

        # === K340 TABAN — eski kollar AYNEN kosar (regresyon 0) =============
        olc("V4a TABAN repo-disi betik dogrudan -> RED",
            "python3 " + os.path.join(dis, "arac.py"), "deny")
        olc("V4b TABAN satir-ici kod -> RED", "python3 -c 'print(1)'", "deny")
        olc("V4c TABAN ANA oturumda curl -> RED", "curl -s https://pruvo3d.com/",
            "deny")

        # === K336 + K332 — KANONIK EV / ORTAK ALTYAPI DUZLEMI ===============
        # Bu iki eksen KANONIK evin ve `~/.claude/cron/` duzleminin VARLIGINA baglidir;
        # CI'da ikisi de YOK. Uydurmak yerine ADIYLA basilir ve AYRI sayilir.
        kanonik_var = (os.path.isdir(KANONIK_EV) and
                       os.path.isfile(os.path.join(KANONIK_EV, "tools",
                                                   "kapi-dagitim-kapisi.py")))
        if not kanonik_var:
            cidisi.append("K336 (kanonik ev yok: " + KANONIK_EV + ")")
        else:
            kdizin = os.path.join(taban, "kanonik")
            kkapi = kopya_kur(kdizin, metin)      # CAPA CEVRILMEZ: gercek ev olcusu
            kok_tp = KANONIK_EV
            wt_kok = None
            kayit = os.path.join(KANONIK_EV, ".git", "worktrees")
            if os.path.isdir(kayit):
                for ad in sorted(os.listdir(kayit)):
                    gd = os.path.join(kayit, ad, "gitdir")
                    if os.path.isfile(gd):
                        with open(gd, encoding="utf-8") as f:
                            wt_kok = os.path.dirname(f.read().strip())
                        break

            def kolc(ad, komut, beklenen, tp=None, cwd=None):
                karar, _ = kos(kkapi, komut, tp or kok_tp, cwd or KANONIK_EV)
                ekle(ad, karar == beklenen, karar)

            kardes = None
            for aday in ("pruvo-hasat", "pruvo-pazarlama", "pruvo-bot"):
                yol = os.path.join(os.path.dirname(KANONIK_EV), aday)
                if os.path.isdir(yol):
                    kardes = yol
                    break
            if kardes is None:
                cidisi.append("K336 POZITIF (kardes ev kokU diskte yok)")
            else:
                kolc("V5a K336 `kapi-dagitim-kapisi.py --ev <kardes kok>` GECER",
                     "python3 tools/kapi-dagitim-kapisi.py --ev " + kardes, "allow")
            kolc("V5b K336 KONTROL `--filo` bicimi GECMEYE DEVAM EDER",
                 "python3 tools/kapi-dagitim-kapisi.py --filo", "allow")
            kolc("V5c K336 SINIR: KAYITSIZ ev koku -> RED",
                 "python3 tools/kapi-dagitim-kapisi.py --ev /private/tmp/sahte-ev",
                 "deny")
            kolc("V5d K336 SINIR: dagitim ailesi DISI arac ayni argumanla -> RED",
                 "python3 tools/durum.py --ev " + (kardes or "/private/tmp/yok"),
                 "deny")

            k332_arac = os.path.join(CRON_KOK, "gozcu.py")
            if not os.path.isdir(CRON_KOK):
                cidisi.append("K332 (ortak altyapi duzlemi yok: " + CRON_KOK + ")")
            elif wt_kok is None:
                cidisi.append("K332 CIP yarisi (kayitli worktree yok)")
            else:
                kolc("V6a K332① CIP `~/.claude/cron/` duzlemini KOSTURUR",
                     "python3 " + k332_arac, "allow", tp=wt_kok, cwd=wt_kok)
                kolc("V6b K332① ANA oturumda AYNI cagri KAPALI kalir",
                     "python3 " + k332_arac, "deny")
                kolc("V6c K332④c KONTROL: duzlem DISI repo-disi yol CIP'te de RED",
                     "python3 /private/tmp/x.py", "deny", tp=wt_kok, cwd=wt_kok)
    finally:
        shutil.rmtree(taban, ignore_errors=True)
    return sonuc, cidisi


# ---------------------------------------------------------------------------
MUTANTLAR = [
    {
        "ad": "M1 `cd` KAYDIRMASI YUTULUR (etkin cwd guncellenmez)",
        "eski": '    return _coz(hedef, mevcut)',
        "yeni": '    return mevcut',
        "hedef": "V1a K340① `cd <disari> &&` goreli betik -> RED",
    },
    {
        "ad": "M2 `env -C` ADAYI YOK SAYILIR (_cwd_sec bazi doner)",
        "eski": '    if not adaylar:\n        return baz',
        "yeni": '    if True:\n        return baz',
        "hedef": "V1b K340① `env -C <disari>` -> RED",
    },
    {
        "ad": "M3 IKINCI OKUMA KALKAR (bayrak degeri argv0'i yine yutar)",
        "eski": ('                while tokenlar and not tokenlar[0].startswith("-"):\n'
                 '                    aday = tokenlar[0]'),
        "yeni": ('                while False:\n'
                 '                    aday = tokenlar[0]'),
        "hedef": "V1e K340① sarmalayici bayrak degeri argv0'i YUTMAZ (curl) -> RED",
    },
    {
        "ad": "M4 BELIRSIZ KAYDIRMA ICERIDE SAYILIR (fail-open yon)",
        "eski": '        return BELIRSIZ_CWD\n    return _coz(hedef, mevcut)',
        "yeni": '        return mevcut\n    return _coz(hedef, mevcut)',
        "hedef": "V1g K340① cozulemeyen kaydirma (`cd \"$VAR\"`) DISARI sayilir -> RED",
    },
    {
        "ad": "M5 BETIK-ICI OLCUM KORLESIR (icra deseni bosalir)",
        "eski": 'r"subprocess\\.(run|Popen|call|check_output|check_call)|os\\.system|os\\.exec|"',
        "yeni": 'r"(?!x)x|"',
        "hedef": "V3a K340② repo-disi hedefi cagiran betik ADIYLA RAPOR EDILIR",
    },
    {
        "ad": "M6 K336 KOVASI KURUCUYA GERI CAPALANIR (dagitim ailesi kalkar)",
        "eski": '    "tools/kapi-dagitim-kapisi.py",        # dogrulama/olcum ayagi (K336)',
        "yeni": "",
        "hedef": "V5a K336 `kapi-dagitim-kapisi.py --ev <kardes kok>` GECER",
    },
    {
        "ad": "M7 K332 ROL EKSENI R2'DE TUKETILMEZ (cip muafiyeti kalkar)",
        "eski": '        if disari and _ortak_altyapi_muaf(argumanlar, cwd, cip):',
        "yeni": '        if disari and _ortak_altyapi_muaf(argumanlar, cwd, False):',
        "hedef": "V6a K332① CIP `~/.claude/cron/` duzlemini KOSTURUR",
    },
    {
        "ad": "KONTROL iz metni degisir (DAVRANIS DISI)",
        "eski": '"MIMAR-KAPISI allow "',
        "yeni": '"MIMAR-KAPISI izin "',
        "hedef": None,
    },
]


def mutasyon_turu(taban_dusenler, atlanan_hedefler):
    kaynak = _kapi_metni()
    print("\n=== MUTASYON TURU ===")
    tamam = True
    for m in MUTANTLAR:
        if m["hedef"] is not None and m["hedef"] in atlanan_hedefler:
            print("  [CI-DISI] %-56s hedef vaka bu makinede KOSMADI" % m["ad"][:56])
            continue
        if m["eski"] not in kaynak:
            print("  🔴 %-60s CAPA TUTMADI (kaynak degismis)" % m["ad"][:60])
            tamam = False
            continue
        mutant = kaynak.replace(m["eski"], m["yeni"], 1)
        try:
            dusenler = {ad for ad, ok, _ in vakalar(mutant)[0] if not ok} - taban_dusenler
        except Exception as e:                            # noqa: BLE001
            dusenler = {"!!MUTANT_COKTU: %s" % e}
        if m["hedef"] is None:
            ok = not dusenler
            print("  %s %-56s KONTROL: dusen=%d %s" % (
                "[OK]" if ok else "🔴", m["ad"][:56], len(dusenler),
                "" if ok else sorted(dusenler)[:3]))
            tamam = tamam and ok
            continue
        if not dusenler:
            print("  🔴 %-56s MUTANT HEDEFE ULASMADI (taban ile AYNI)" % m["ad"][:56])
            tamam = False
            continue
        vurdu = m["hedef"] in dusenler
        print("  %s %-56s OLDURDUGU KOL: %s%s" % (
            "[OK]" if vurdu else "🔴", m["ad"][:56],
            m["hedef"][:58] if vurdu else "BEKLENEN KOL DUSMEDI",
            "  (+%d ek kol)" % (len(dusenler) - 1) if len(dusenler) > 1 else ""))
        tamam = tamam and vurdu
    return tamam


def main():
    print("=== TABAN BATARYA (kaynak: %s) ===" % KAPI)
    sonuc, cidisi = vakalar(_kapi_metni())
    dusenler = set()
    for ad, ok, notu in sonuc:
        if not ok:
            dusenler.add(ad)
        print("  %s %-66s %s" % ("[OK]" if ok else "🔴", ad[:66], notu))
    for c in cidisi:
        print("  [CI-DISI] %s — vaka KOSMADI, yesil SAYILMAZ" % c)
    print("IDDIA=%d GECTI=%d KIRMIZI=%d CIDISI=%d" % (
        len(sonuc), len(sonuc) - len(dusenler), len(dusenler), len(cidisi)))

    if "--taban" in sys.argv:
        return 0 if not dusenler else 1
    kosan = {ad for ad, _, _ in sonuc}
    atlanan = {m["hedef"] for m in MUTANTLAR
               if m["hedef"] is not None and m["hedef"] not in kosan}
    tamam = mutasyon_turu(dusenler, atlanan)
    print("\nSONUC: %s" % ("KABUL YESIL ✅" if (not dusenler and tamam)
                           else "KIRMIZI 🔴"))
    return 0 if (not dusenler and tamam) else 1


if __name__ == "__main__":
    sys.exit(main())
