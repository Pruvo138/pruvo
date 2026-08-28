#!/usr/bin/env python3
"""K340 BYPASS KANITI — iki bypass yolunun ONCE/SONRA hukmunu YAN YANA olcer.

Ayni PreToolUse girdisi IKI kapiya verilir:
  ONCE  = `origin/main`in kapisi (tools/ agaci `git archive` ile gecici dizine
          acilir; sonunda TAMAMEN SILINIR)
  SONRA = bu daldaki kapi (calisma agaci)
"Kapandi" iddiasi tek kapinin ciktisindan degil, IKI HUKMUN FARKINDAN okunur.

🔴 TABAN SAGLAMLIK KAPISI (ilk kosumda OLCULEN ARIZA): ilk surum ONCE tarafina
yalniz iki dosya kopyaliyordu; K343 kapiyi `serbest_cagrilar.py`ye bagladigi icin
import COKUYOR, rc!=0 doniyor ve bu "deny" diye okunuyordu -> ONCE sutunu HER SEYE
'deny' dedi, mesru allowlist cagrisina bile. Bozuk bir taban, "sonra" sutununu
anlamli gostererek kanit TAKLIDI uretir. Bu yuzden ONCE tarafi artik TAM tools/
agaciyla kurulur VE kendi KONTROL vakalariyla sinanir: taban kontrolleri beklendigi
gibi davranmazsa arac TABAN_BOZUK deyip rc=2 ile DURUR, tablo kanit SAYILMAZ.

Kullanim: python3 tools/k340/k340-bypass-kanit.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAPI_SONRA = os.path.join(KOK, "tools", "mimar-icra-kapisi.py")
FIK = os.path.join(KOK, "tools", "k340", "fikstur")
REPO = "/Users/okan/dev/pruvo"
TRANSCRIPT_KOK = "/Users/okan/.claude/projects"


def damga(yol):
    return "".join(k if k.isalnum() else "-" for k in yol)


ANA = {"transcript_path": TRANSCRIPT_KOK + "/" + damga(REPO) + "/oturum.jsonl"}
CIP = {"transcript_path": TRANSCRIPT_KOK + "/" + damga(KOK) + "/oturum.jsonl", "cwd": KOK}

# (baslik, komut, payload, beklenen_SONRA, taban_kontrolu_mu)
# taban_kontrolu_mu=True olan vakalar ONCE tarafinda da BELLI bir hukum vermek
# ZORUNDADIR; vermezse taban bozuktur ve tablo kanit sayilmaz.
VAKALAR = [
    ("① CANLI VAKA BIREBIR (etkisi allowlist komutu — dogru cevap ALLOW)",
     "env -C " + REPO + " python3 tools/d1-sync.py --durum", ANA, "allow", False),
    ("① AYIRT EDICI: ayni kacis yolu, allowlist DISI komut",
     "env -C " + REPO + " python3 tools/build.py", ANA, "deny", False),
    ("① ETKIN CWD repo DISI",
     "env -C /private/tmp python3 tools/d1-sync.py --durum", ANA, "deny", False),
    ("① esitlikli form --chdir=",
     "env --chdir=/private/tmp python3 tools/d1-sync.py --durum", ANA, "deny", False),
    ("① sarmalayici bayrak degeri (olcum kolu atlaniyordu)",
     "nice -n 10 head -5 " + REPO + "/DEVAM.md", ANA, "deny", False),
    ("① cd ile kaydirilmis cwd",
     "cd /private/tmp && python3 tools/d1-sync.py --durum", ANA, "deny", False),
    ("② CANLI VAKA AYNASI: subprocess icine saklanan repo-disi mutlak yol",
     "python3 " + FIK + "/kardes-ev-cagiran.py", CIP, "deny", False),
    ("② dogrudan repo-disi calistirilabilir (A' kolu)",
     "python3 " + FIK + "/dogrudan-disari.py", CIP, "deny", False),
    ("🔴 KONTROL: mesru repo-ICI betik-ici cagri SERBEST kalmali",
     "python3 " + FIK + "/iceri-cagiran.py", CIP, "allow", True),
    ("🔴 KONTROL: sarmalayicisiz mesru cagri SERBEST kalmali",
     "python3 tools/d1-sync.py --durum", ANA, "allow", True),
    # === KOMSU EKSEN REGRESYONU (K343 serbest cagri tablosu + K344 yeni kollar) ======
    # 🔴 NEDEN BURADA: K343'un tablosu bekciyi "PY_NODE kolu eslesince segmenti KAPATIR
    # (continue), boylece R2/F kollarina hic dusmez" diye serbest birakiyor. K340 tam
    # o `continue`in anlamini degistirdi ('sonraki OKUMA'). Tek okumali cagrilarda
    # davranis AYNI kalmali; bu dort satir onu OLCER, iddia etmez.
    ("KOMSU K344: bekci teslim-karari (repo DISI, serbest cagri tablosunda)",
     "python3 /Users/okan/.claude/cron/cip_dogum_bekcisi.py --teslim-karari",
     ANA, "allow", True),
    # 🔴 AYNI CAGRI, CIP KIMLIGIYLE. Canli olcum (28 Agu): bu cagri mimar cipinin
    # elinde R2 ile REDDEDILDI, oysa kapinin KENDI red metni onu SERBEST diye
    # listeliyor. Beklenen 'allow'dur; 'deny' cikarsa bu K340'in degil K343/K344'un
    # ekseninde bir bulgudur ve ADIYLA raporlanir ([[kapi-red-metni-ikinci-kopyadir]]).
    ("KOMSU K344 (CIP kimligi): bekci teslim-karari",
     "python3 /Users/okan/.claude/cron/cip_dogum_bekcisi.py --teslim-karari",
     CIP, "allow", False),
    ("KOMSU K344: kutu-arsivle --kapanislari-isle",
     "python3 tools/kutu-arsivle.py --kapanislari-isle", ANA, "allow", True),
    ("KOMSU K258: kutu-arsivle --kuru",
     "python3 tools/kutu-arsivle.py --kuru", ANA, "allow", True),
    ("KOMSU K168/K258: defter-rotasyon bakim cagrisi",
     "python3 tools/defter-rotasyon.py DEVAM.md DEVAM-ARSIV.md "
     "--tavan-kaynaktan --isaretciye-indir", ANA, "allow", True),
]


def kapiyi_kostur(kapi, komut, payload):
    girdi = {"tool_name": "Bash", "tool_input": {"command": komut},
             "cwd": payload.get("cwd", REPO)}
    girdi.update(payload)
    try:
        p = subprocess.run([sys.executable, kapi], input=json.dumps(girdi),
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        return "COKTU", str(e)[:80]
    ciktilar = (p.stdout or "") + " | " + (p.stderr or "")
    if "Traceback" in (p.stderr or ""):
        return "COKTU", (p.stderr or "").strip().splitlines()[-1][:80]
    if p.returncode != 0:
        return "deny", (p.stdout or p.stderr or "").strip()[:80]
    if (p.stdout or "").strip():
        return "deny", (p.stdout or "").strip()[:80]
    return "allow", ciktilar.strip()[:80]


def once_agacini_kur(hedef):
    """origin/main'in tools/ agacini gecici dizine acar. Doner: kapi yolu ya da None."""
    ham = subprocess.run(["git", "-C", KOK, "archive", "origin/main", "tools"],
                         capture_output=True, timeout=120)
    if ham.returncode != 0:
        return None
    with tarfile.open(fileobj=io.BytesIO(ham.stdout)) as t:
        t.extractall(hedef)
    kapi = os.path.join(hedef, "tools", "mimar-icra-kapisi.py")
    return kapi if os.path.exists(kapi) else None


def main():
    gecici = tempfile.mkdtemp(prefix="k340-kanit-")
    try:
        kapi_once = once_agacini_kur(gecici)
        if kapi_once is None:
            print("TABAN_BOZUK: origin/main tools/ agaci acilamadi")
            return 2

        satirlar = []
        for baslik, komut, payload, beklenen, taban_kontrol in VAKALAR:
            once, once_not = kapiyi_kostur(kapi_once, komut, payload)
            sonra, _ = kapiyi_kostur(KAPI_SONRA, komut, payload)
            satirlar.append((baslik, komut, once, once_not, sonra, beklenen, taban_kontrol))

        # --- TABAN SAGLAMLIK KAPISI ---
        taban_hatalari = []
        for baslik, _k, once, once_not, _s, beklenen, taban_kontrol in satirlar:
            if once == "COKTU":
                taban_hatalari.append(baslik[:50] + " -> ONCE COKTU: " + once_not)
            elif taban_kontrol and once != beklenen:
                taban_hatalari.append(
                    baslik[:50] + " -> ONCE=" + once + " (mesru cagri, 'allow' bekleniyordu)")
        if taban_hatalari:
            print("🔴 TABAN_BOZUK — ONCE tarafi guvenilir DEGIL, tablo KANIT SAYILMAZ:")
            for h in taban_hatalari:
                print("   " + h)
            return 2

        print("ONCE = origin/main kapisi (tam tools/ agaci) · SONRA = bu dal")
        print("-" * 104)
        kapanan, kontrol_bozulan, uyusmaz = 0, 0, 0
        for baslik, _k, once, _n, sonra, beklenen, _t in satirlar:
            if sonra != beklenen:
                uyusmaz += 1
            if once == "allow" and sonra == "deny":
                kapanan += 1
            if beklenen == "allow" and sonra != "allow":
                kontrol_bozulan += 1
            print("{:<62} ONCE={:<5} SONRA={:<5} beklenen={:<5} {}".format(
                baslik[:62], once, sonra, beklenen,
                "OK" if sonra == beklenen else "🔴UYUSMAZ"))
        print("-" * 104)
        print("KAPANAN DELIK (ONCE=allow -> SONRA=deny): " + str(kapanan))
        print("KONTROL BOZULAN (mesru cagri kapandi)   : " + str(kontrol_bozulan))
        print("BEKLENENLE UYUSMAYAN                    : " + str(uyusmaz))
        return 1 if (uyusmaz or kontrol_bozulan) else 0
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
        print("TEMIZLIK: gecici ONCE agaci SILINDI · kalinti=" +
              ("VAR " + gecici if os.path.exists(gecici) else "YOK"))


sys.exit(main())
