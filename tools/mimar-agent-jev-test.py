#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AGENT-KAPISI x JEV MOTOR SECIMI bataryasi (27 Eyl 2026, cip KraL-JevGomulu-27Eyl).

J2 §7.1: `mimar-icra-kapisi.py::_agent_karari` beyan satiri YOKSA karari EyLuL'un genel
kancasinin (motor-secimi.py) fonksiyonlarindan alir. Bu batarya o kolu AGSIZ olcer:
  * SAHTE motor-secimi fiksturu gecici dizine yazilir; kapinin MOTOR_SECIMI_YOLU oraya
    cevrilir. Fikstur ayirt edici bir GEREKCE_SABLON ve 0.8 OLMAYAN bir esik (0.75) tasir:
    kapi metni ya da esigi kendi kopyasindan okursa vaka kizarir (ikinci kopya nobetcisi).
  * Sahte Jev her cagriyi fikstur dizinine kaydeder -> "Jev'e soruldu mu / kac kez / hangi
    metin + esikle" IZDEN assert edilir, yalniz karardan degil.
  * Gercek motor-secimi.py makinede VARSA (yerel) ayrica G-vakalari: gercek modul + SAHTE
    Jev; red metni gercek GEREKCE_SABLON ile BIREBIR, esik gercek soru JSON'undan. CI'da
    modul yoktur -> G-vakalari ATLANDI diye SAYIYLA basilir (F-vakalari ayni kolu olcer).
  * Gercek ag YOK, gercek HOME'a ve jev-kayit'e yazim YOK (JEV_KAYIT_DIZINI gecici dizin).
  * Mutantlar kapinin GECICI kopyasina uygulanir, canli govdeye dokunulmaz; her mutantin
    HEDEF vakalari yazilidir ve kizarmalari sarttir (SURVIVOR=0). Once MUTASYONSUZ kopya
    (TABAN) yesil olmali.

Kullanim:
    python3 tools/mimar-agent-jev-test.py                 # vakalar + mutantlar
    python3 tools/mimar-agent-jev-test.py --kapi <yol> --yalniz-vakalar
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI_VARSAYILAN = os.path.join(TOOLS, "mimar-icra-kapisi.py")
GERCEK_MOTOR_SECIMI = "/Users/okan/.claude/jev/motor-secimi.py"

BEYAN = "isci-muafiyet: kapi kodu olcumu — sessiz-hata"
FIKSTUR_ESIK = 0.75
FIKSTUR_SABLON = "SAHTE-MOTOR-SECIMI-7f3a mekanik {olasilik} :: m3'e ver (fikstur)"

FIKSTUR_KAYNAK = r'''
import json, os, re, time
_KOK = os.path.dirname(os.path.abspath(__file__))
SORU_DOSYASI_VARSAYILAN = os.path.join(_KOK, "soru.json")
BUTCE_SANIYE = 0.5
MUAF_AJAN_TIPLERI = ("Explore",)
GEREKCE_SABLON = __SABLON__
ASIM_DESEN = re.compile(r"\[GEÇER:\s*(yargi|sessiz_hata)\]")


def _senaryo():
    with open(os.path.join(_KOK, "senaryo.json"), encoding="utf-8") as f:
        return json.load(f)


def _soru_yukle(yol):
    if _senaryo().get("soru_yok"):
        return None
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def gorev_metni(description, prompt):
    return ("GOREV|" + description + "\n" + prompt)[:1500]


def gorev_doner_mi(secim, insan_onayi):
    return secim == "mekanik" and not insan_onayi


def _asim_tara(description, prompt):
    for alan in (description or "", prompt or ""):
        m = ASIM_DESEN.search(alan)
        if m:
            return m.group(1)
    return None


def _muaf_mi(subagent_type, ev_adi, model):
    if subagent_type in MUAF_AJAN_TIPLERI:
        return True, "ajan_tipi"
    return False, None


class _SahteJev:
    @staticmethod
    def karar(istek, tasiyici=None, kayit_dizini=None, etiket=""):
        s = _senaryo()
        with open(os.path.join(_KOK, "cagri.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"metin": istek["metin"], "esik": istek["esik"],
                                "soru": istek["soru"], "etiket": etiket,
                                "secenekler": sorted(istek["secenekler"])},
                               ensure_ascii=False) + "\n")
        if s.get("gecikme"):
            time.sleep(s["gecikme"])
        if s.get("hata"):
            raise RuntimeError("sahte ariza")
        secim, p = s.get("secim"), s.get("olasilik")
        return {"ok": True, "tip": "secim", "secim": secim, "olasilik": p,
                "insan_onayi": secim is None or not (p >= istek["esik"])}


def _jev_modul_yukle():
    return _SahteJev
'''

# Gercek modulu AYNEN yukler, yalniz Jev'i sahtesiyle degistirir (ag yok).
GERCEK_SARMAL_KAYNAK = r'''
import importlib.util, os
_s = importlib.util.spec_from_file_location("gercek_motor_secimi", __GERCEK__)
_g = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_g)
globals().update({k: v for k, v in vars(_g).items() if not k.startswith("__")})
_fs = importlib.util.spec_from_file_location(
    "fikstur_jev", os.path.join(os.path.dirname(os.path.abspath(__file__)), "motor-secimi.py"))
_f = importlib.util.module_from_spec(_fs)
_fs.loader.exec_module(_f)


def _jev_modul_yukle():
    return _f._SahteJev
'''


def modul_yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Duzlem:
    """Gecici fikstur dizini + kapi modulu. Her vaka senaryo yazar, cagri izini sifirlar."""

    def __init__(self, kapi_yolu):
        self.kok = tempfile.mkdtemp(prefix="agent-jev-")
        self.fikstur = os.path.join(self.kok, "motor-secimi.py")
        self.sarmal = os.path.join(self.kok, "motor-secimi-gercek-sarmal.py")
        with open(self.fikstur, "w", encoding="utf-8") as f:
            f.write(FIKSTUR_KAYNAK.replace("__SABLON__", repr(FIKSTUR_SABLON)))
        with open(self.sarmal, "w", encoding="utf-8") as f:
            f.write(GERCEK_SARMAL_KAYNAK.replace("__GERCEK__", repr(GERCEK_MOTOR_SECIMI)))
        with open(os.path.join(self.kok, "soru.json"), "w", encoding="utf-8") as f:
            json.dump({"soru": "Sahte soru: hangi motor?", "esik": FIKSTUR_ESIK,
                       "secenekler": {"mekanik": "a", "yargi": "b", "sessiz_hata": "c"}}, f)
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        self.kapi = modul_yukle("kapi_agent_jev_test", kapi_yolu)

    def temizle(self):
        shutil.rmtree(self.kok, ignore_errors=True)

    def cagrilar(self):
        yol = os.path.join(self.kok, "cagri.jsonl")
        if not os.path.exists(yol):
            return []
        with open(yol, encoding="utf-8") as f:
            return [json.loads(s) for s in f if s.strip()]

    def kostur(self, tool_input, senaryo, modul="fikstur", tool_name="Agent",
               agent_id=None, ortam_ek=None):
        """Doner: dict(karar, gerekce, stderr, cagri, sure)."""
        with open(os.path.join(self.kok, "senaryo.json"), "w", encoding="utf-8") as f:
            json.dump(senaryo, f)
        yol = os.path.join(self.kok, "cagri.jsonl")
        if os.path.exists(yol):
            os.remove(yol)
        self.kapi.MOTOR_SECIMI_YOLU = {
            "fikstur": self.fikstur,
            "gercek": self.sarmal,
            "yok": os.path.join(self.kok, "olmayan-motor-secimi.py"),
            "bozuk": self._bozuk(),
        }[modul]
        payload = {"session_id": "agent-jev-test", "cwd": "/Users/okan/dev/pruvo",
                   "permission_mode": "bypassPermissions",
                   "hook_event_name": "PreToolUse", "tool_name": tool_name,
                   "tool_input": tool_input}
        if agent_id:
            payload["agent_id"] = agent_id
        eski_ortam = dict(os.environ)
        for ad in ("PRUVO_AGENT_JEV", "PRUVO_ISCI_KOSUMU", "PRUVO_CLAUDE_ISCI_IZNI",
                   "CLAUDE_PROJECT_DIR"):
            os.environ.pop(ad, None)
        os.environ["JEV_KAYIT_DIZINI"] = os.path.join(self.kok, "jev-kayit")
        os.environ.update(ortam_ek or {})
        eski_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(payload))
        out, err = io.StringIO(), io.StringIO()
        t0 = time.monotonic()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    self.kapi.main()
                except SystemExit:
                    pass
        finally:
            sys.stdin = eski_stdin
            os.environ.clear()
            os.environ.update(eski_ortam)
        sure = time.monotonic() - t0
        govde = out.getvalue().strip()
        karar, gerekce = "allow", None
        if govde:
            hso = json.loads(govde).get("hookSpecificOutput") or {}
            karar = hso.get("permissionDecision") or "allow"
            gerekce = hso.get("permissionDecisionReason")
        return {"karar": karar, "gerekce": gerekce, "stderr": err.getvalue(),
                "cagri": self.cagrilar(), "sure": sure}

    def _bozuk(self):
        yol = os.path.join(self.kok, "bozuk-motor-secimi.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write("raise RuntimeError('bozuk modul')\n")
        return yol


def tani(sonuc):
    """stderr'deki JEV-MOTOR tani satiri (yoksa None)."""
    for satir in sonuc["stderr"].splitlines():
        if "JEV-MOTOR karar=" in satir:
            return satir.split("JEV-MOTOR ", 1)[1]
    return None


def vakalar_kostur(kapi_yolu):
    d = Duzlem(kapi_yolu)
    k = d.kapi
    beyan_sarti = k.GEREKCE_BASI + k.AGENT_GEREKCE
    kirmizi = []
    toplam = [0]
    atlanan = []

    def vaka(no, aciklama, sonuc, sartlar):
        toplam[0] += 1
        bozuk = [ad for ad, tamam in sartlar if not tamam]
        if bozuk:
            kirmizi.append(no)
            print("VAKA %s KIRMIZI: %s | bozuk: %s | karar=%s tani=%s cagri=%d gerekce=%r"
                  % (no, aciklama, ", ".join(bozuk), sonuc["karar"], tani(sonuc),
                     len(sonuc["cagri"]), (sonuc["gerekce"] or "")[:90]))
        else:
            print("VAKA %s gecti: %s" % (no, aciklama))

    ti = lambda prompt, **ek: dict({"description": "is", "prompt": prompt}, **ek)
    try:
        # ---------------- POZITIF ----------------
        s = d.kostur(ti("Rakip sitelerin fiyat sayfasini incele, strateji oner."),
                     {"secim": "yargi", "olasilik": 0.93})
        vaka("P1", "yargi >= esik -> GECER", s, [
            ("allow", s["karar"] == "allow"),
            ("tani gecti/yargi", tani(s) == "karar=gecti sinif=yargi olasilik=0.93"),
            ("Jev 1 kez", len(s["cagri"]) == 1),
            ("esik JSON'dan", s["cagri"][:1] and s["cagri"][0]["esik"] == FIKSTUR_ESIK),
            ("soru JSON'dan", s["cagri"][:1] and s["cagri"][0]["soru"] == "Sahte soru: hangi motor?"),
            ("secenekler JSON'dan", s["cagri"][:1] and
             s["cagri"][0]["secenekler"] == ["mekanik", "sessiz_hata", "yargi"]),
            ("etiket", s["cagri"][:1] and s["cagri"][0]["etiket"] == "mimar-icra-kapisi"),
        ])
        s = d.kostur(ti("Odeme akisinin kapi kodunu denetle."),
                     {"secim": "sessiz_hata", "olasilik": 0.88})
        vaka("P2", "sessiz_hata >= esik -> GECER", s, [
            ("allow", s["karar"] == "allow"),
            ("tani gecti/sessiz_hata", tani(s) == "karar=gecti sinif=sessiz_hata olasilik=0.88"),
            ("Jev 1 kez", len(s["cagri"]) == 1),
        ])
        s = d.kostur(ti("Is: tabloyu duzenle.\n" + BEYAN + "\nDevam."),
                     {"secim": "mekanik", "olasilik": 0.99})
        vaka("P3", "gecerli beyan VAR -> GECER, Jev'e HIC sorulmaz", s, [
            ("allow", s["karar"] == "allow"),
            ("Jev 0 kez", len(s["cagri"]) == 0),
            ("tani yok", tani(s) is None),
            ("iz muafiyet", "MIMAR-agent-muafiyet" in s["stderr"]),
        ])
        s = d.kostur(ti("Dosyayi duzenle.", description="is [GEÇER: yargi]"),
                     {"secim": "mekanik", "olasilik": 0.99})
        vaka("P4", "asim etiketi [GEÇER: yargi] -> GECER, Jev'e sorulmaz", s, [
            ("allow", s["karar"] == "allow"),
            ("Jev 0 kez", len(s["cagri"]) == 0),
            ("tani asim", tani(s) == "karar=asim sinif=yargi olasilik=-"),
        ])
        s = d.kostur(ti("Tasarim secenekleri arasinda karar ver."),
                     {"secim": "yargi", "olasilik": 0.77})
        vaka("P5", "yargi 0.77 >= fikstur esigi 0.75 -> GECER (esik sabit 0.8 DEGIL)", s, [
            ("allow", s["karar"] == "allow"),
            ("tani gecti", tani(s) == "karar=gecti sinif=yargi olasilik=0.77"),
        ])
        s = d.kostur(ti("Is."), {"secim": "mekanik", "olasilik": 0.99}, tool_name="Task")
        vaka("P6", "Task araci da ayni kol (mekanik -> RED)", s, [
            ("deny", s["karar"] == "deny"),
            ("tani dondu", tani(s) == "karar=dondu sinif=mekanik olasilik=0.99"),
        ])
        s = d.kostur(ti("Beyansiz isci."), {"secim": "mekanik", "olasilik": 0.99},
                     agent_id="a1b2c3d4e5f60718")
        vaka("P7", "ISCI (agent_id dolu) -> GECER, Jev'e sorulmaz", s, [
            ("allow", s["karar"] == "allow"),
            ("Jev 0 kez", len(s["cagri"]) == 0),
        ])

        # ---------------- NEGATIF ----------------
        prompt = "urunler listesine su satiri ekle ve commit et"
        s = d.kostur(ti(prompt, description="liste ekle"),
                     {"secim": "mekanik", "olasilik": 0.95})
        beklenen = FIKSTUR_SABLON.format(olasilik="0.95")
        vaka("N1", "mekanik >= esik -> RED, metin motor-secimi sablonuyla BIREBIR", s, [
            ("deny", s["karar"] == "deny"),
            ("metin BIREBIR (baslik/kuyruk yok)", s["gerekce"] == beklenen),
            ("tani dondu", tani(s) == "karar=dondu sinif=mekanik olasilik=0.95"),
            ("Jev 1 kez", len(s["cagri"]) == 1),
            ("gorev_metni moduldan", s["cagri"][:1] and
             s["cagri"][0]["metin"] == "GOREV|liste ekle\n" + prompt),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "yargi", "olasilik": 0.6})
        vaka("N2", "yargi esik alti -> beyan sarti (AGENT_GEREKCE)", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani esik_alti", tani(s) == "karar=esik_alti sinif=yargi olasilik=0.6"),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "mekanik", "olasilik": 0.6})
        vaka("N3", "mekanik esik alti -> beyan sarti, m3 metni DEGIL", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani esik_alti", tani(s) == "karar=esik_alti sinif=mekanik olasilik=0.6"),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "yargi", "olasilik": 0.99}, modul="yok")
        vaka("N4", "motor-secimi modulu YOK -> beyan sarti", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani modul_yok", tani(s) == "karar=modul_yok sinif=- olasilik=-"),
            ("Jev 0 kez", len(s["cagri"]) == 0),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "yargi", "olasilik": 0.99, "hata": True})
        vaka("N5", "Jev ARIZA (karar istisna) -> beyan sarti", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani yok", tani(s) == "karar=yok sinif=- olasilik=-"),
            ("Jev 1 kez", len(s["cagri"]) == 1),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "yargi", "olasilik": 0.99, "gecikme": 2.0})
        vaka("N6", "Jev ZAMAN ASIMI (2 sn > butce 0.5) -> beyan sarti, butcede doner", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani yok", tani(s) == "karar=yok sinif=- olasilik=-"),
            ("sure < 1.5 sn", s["sure"] < 1.5),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": None, "olasilik": None})
        vaka("N7", "Jev motor=yok (secim None) -> beyan sarti", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani esik_alti", tani(s) == "karar=esik_alti sinif=- olasilik=-"),
        ])
        s = d.kostur(ti("Kodda ara.", subagent_type="Explore"), {"secim": "yargi", "olasilik": 0.99})
        vaka("N8", "muaf ajan tipi -> Jev'e sorulmaz, beyan sarti AYNEN", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani muaf", tani(s) == "karar=muaf sinif=- olasilik=-"),
            ("Jev 0 kez", len(s["cagri"]) == 0),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "yargi", "olasilik": 0.99},
                     ortam_ek={"PRUVO_AGENT_JEV": "kapali"})
        vaka("N9", "PRUVO_AGENT_JEV=kapali -> Jev'e sorulmaz, beyan sarti", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani kapali", tani(s) == "karar=kapali sinif=- olasilik=-"),
            ("Jev 0 kez", len(s["cagri"]) == 0),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "yargi", "olasilik": 0.99}, modul="bozuk")
        vaka("N10", "motor-secimi modulu BOZUK (import istisnasi) -> beyan sarti", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani ariza", tani(s) == "karar=ariza sinif=- olasilik=-"),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "yargi", "olasilik": 0.99, "soru_yok": True})
        vaka("N11", "soru JSON'u yok/bozuk -> beyan sarti", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ("tani soru_yok", tani(s) == "karar=soru_yok sinif=- olasilik=-"),
            ("Jev 0 kez", len(s["cagri"]) == 0),
        ])
        s = d.kostur(ti("isci-muafiyet: is — foobar"), {"secim": "yargi", "olasilik": 0.99})
        vaka("N12", "GECERSIZ beyan -> eski sinif reddi AYNEN, Jev'e sorulmaz", s, [
            ("deny", s["karar"] == "deny"),
            ("sinif reddi", "SINIF JETONU ESLESMEDI" in (s["gerekce"] or "")),
            ("Jev 0 kez", len(s["cagri"]) == 0),
        ])
        s = d.kostur(ti("Bir seyler yap."), {"secim": "baska", "olasilik": 0.99})
        vaka("N13", "kume disi secim -> beyan sarti", s, [
            ("deny", s["karar"] == "deny"),
            ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
        ])

        # ---------------- GERCEK MODUL (yerel) ----------------
        if os.path.isfile(GERCEK_MOTOR_SECIMI):
            g = modul_yukle("gercek_ms_olcum", GERCEK_MOTOR_SECIMI)
            gsoru = g._soru_yukle(g.SORU_DOSYASI_VARSAYILAN)
            prompt = "belirtilen dosyaya su satiri ekle"
            s = d.kostur(ti(prompt, description="satir ekle"),
                         {"secim": "mekanik", "olasilik": 0.95}, modul="gercek")
            vaka("G1", "GERCEK motor-secimi: mekanik -> metin gercek GEREKCE_SABLON'la BIREBIR", s, [
                ("deny", s["karar"] == "deny"),
                ("metin BIREBIR", s["gerekce"] == g.GEREKCE_SABLON.format(olasilik="0.95")),
                ("metin gercek gorev_metni", s["cagri"][:1] and
                 s["cagri"][0]["metin"] == g.gorev_metni("satir ekle", prompt)),
                ("esik gercek JSON", s["cagri"][:1] and gsoru is not None and
                 s["cagri"][0]["esik"] == gsoru["esik"]),
            ])
            ust = gsoru["esik"] if gsoru else 0.8
            s = d.kostur(ti("Rakip incelemesi yap."),
                         {"secim": "yargi", "olasilik": round(ust + 0.05, 2)}, modul="gercek")
            vaka("G2", "GERCEK motor-secimi: yargi >= gercek esik -> GECER", s, [
                ("allow", s["karar"] == "allow"),
            ])
            s = d.kostur(ti("Rakip incelemesi yap."),
                         {"secim": "yargi", "olasilik": round(ust - 0.01, 2)}, modul="gercek")
            vaka("G3", "GERCEK motor-secimi: yargi < gercek esik -> beyan sarti", s, [
                ("deny", s["karar"] == "deny"),
                ("AGENT_GEREKCE", s["gerekce"] == beyan_sarti),
            ])
        else:
            atlanan.extend(["G1", "G2", "G3"])
            print("GERCEK_MODUL=YOK -> G1/G2/G3 ATLANDI (CI beklenen; F-vakalari ayni kolu olcer)")
    finally:
        d.temizle()
    print("VAKALAR: %d kostu · %d kirmizi · %d atlandi" % (toplam[0], len(kirmizi), len(atlanan)))
    return kirmizi


# ---------------- MUTANTLAR (gecici kopyada) ----------------
# (ad, aciklama, eski, yeni, hedef vakalar — HEPSI kizarmali)
MUTANTLAR = [
    ("J1", "esik karsilastirmasi TERS",
     "insan_onayi is not False\n", "insan_onayi is not True\n", {"P1", "N2", "N3"}),
    ("J2", "mekanik -> gecer",
     "            return _HamGerekce(ms.GEREKCE_SABLON.format(olasilik=str(olasilik)))\n",
     '            return "gecer"\n', {"N1", "P6"}),
    ("J3", "Jev yok/zaman asimi -> gecer",
     '            _jev_tani("yok")\n            return None\n',
     '            _jev_tani("yok")\n            return "gecer"\n', {"N5", "N6"}),
    ("J4", "red metni IKINCI KOPYA (sablon moduldan okunmaz)",
     "_HamGerekce(ms.GEREKCE_SABLON.format(olasilik=str(olasilik)))",
     '_HamGerekce("MOTOR SEÇİMİ: bu görev mekanik (Jev mekanik {olasilik}). '
     "Alt-ajan açılmaz — m3'e ver.\".format(olasilik=str(olasilik)))", {"N1"}),
    ("J5", "beyan kolu silinir",
     '    if AGENT_MUAFIYET_RE.search(prompt):\n        return "gecer"\n', "", {"P3"}),
    ("J6", "Jev beyandan ONCE sorulur",
     "    if AGENT_MUAFIYET_RE.search(prompt):\n",
     "    if _agent_jev_karari(girdi) is None and AGENT_MUAFIYET_RE.search(prompt):\n", {"P3"}),
    ("J7", "red metnine GEREKCE_BASI eklenir",
     'bas="" if isinstance(agent_karari, _HamGerekce) else None', "bas=None", {"N1"}),
    ("J8", "asim etiketi yok sayilir",
     "        if asim is not None:\n", "        if False:\n", {"P4"}),
    ("J9", "kapali anahtari yok sayilir",
     '    if os.environ.get(AGENT_JEV_ORTAM) == "kapali":\n', "    if False:\n", {"N9"}),
    ("J10", "sessiz_hata gecen kumeden duser",
     'AGENT_JEV_GECEN_SINIFLAR = ("yargi", "sessiz_hata")\n',
     'AGENT_JEV_GECEN_SINIFLAR = ("yargi",)\n', {"P2"}),
    ("J11", "butce yok sayilir (iplik sonuna kadar beklenir)",
     "    iplik.join(butce)\n", "    iplik.join()\n", {"N6"}),
    ("J12", "muaf ajan -> gecer",
     '            _jev_tani("muaf")\n            return None\n',
     '            _jev_tani("muaf")\n            return "gecer"\n', {"N8"}),
    ("J13", "modul arizasi -> gecer",
     '        _jev_tani("ariza")\n        return None\n',
     '        _jev_tani("ariza")\n        return "gecer"\n', {"N10"}),
    ("J14", "esik soru JSON'u yerine sabit 0.8",
     '            "esik": soru["esik"],\n', '            "esik": 0.8,\n', {"P1", "P5"}),
    ("J15", "gorev_metni yerine ham prompt",
     '            "metin": ms.gorev_metni(description, prompt),\n',
     '            "metin": prompt,\n', {"N1"}),
]


def kopya_kostur(kok, ad, kaynak):
    yol = os.path.join(kok, ad + "-mimar-icra-kapisi.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak)
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--kapi", yol,
                        "--yalniz-vakalar"], capture_output=True, text=True, timeout=300)
    kirmizi = set()
    for satir in (p.stdout or "").splitlines():
        if satir.startswith("VAKA ") and " KIRMIZI:" in satir:
            kirmizi.add(satir.split()[1])
    return p.returncode, kirmizi, p


def mutantlar_kostur():
    with open(KAPI_VARSAYILAN, encoding="utf-8") as f:
        kaynak = f.read()
    kok = tempfile.mkdtemp(prefix="agent-jev-mutant-")
    survivor = []
    try:
        rc, kirmizi, p = kopya_kostur(kok, "TABAN", kaynak)
        if rc != 0 or kirmizi:
            print("TABAN KIRMIZI (mutasyonsuz kopya): rc=%d kirmizi=%s" % (rc, sorted(kirmizi)))
            print((p.stdout or "")[-1500:] + (p.stderr or "")[-800:])
            return None
        print("TABAN yesil (mutasyonsuz kopya rc=0)")
        for ad, aciklama, eski, yeni, hedef in MUTANTLAR:
            sayi = kaynak.count(eski)
            if sayi != 1:
                print("MUTANT %s CAPA HATASI: '%s' %d kez (1 olmali)" % (ad, eski.strip()[:60], sayi))
                survivor.append(ad)
                continue
            rc, kirmizi, _p = kopya_kostur(kok, ad, kaynak.replace(eski, yeni))
            eksik = hedef - kirmizi
            if rc == 0 or eksik:
                survivor.append(ad)
                print("MUTANT %s SURVIVOR: %s | rc=%d kirmizi=%s eksik_hedef=%s"
                      % (ad, aciklama, rc, sorted(kirmizi), sorted(eksik)))
            else:
                print("MUTANT %s olduruldu: %s | hedef %s ⊆ kirmizi %s"
                      % (ad, aciklama, sorted(hedef), sorted(kirmizi)))
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return survivor


def main():
    kapi = KAPI_VARSAYILAN
    if "--kapi" in sys.argv:
        kapi = sys.argv[sys.argv.index("--kapi") + 1]
    kirmizi = vakalar_kostur(kapi)
    if "--yalniz-vakalar" in sys.argv:
        sys.exit(1 if kirmizi else 0)
    if kirmizi:
        print("SONUC: KIRMIZI (vaka %s) — mutantlar kosulmadi" % ", ".join(kirmizi))
        sys.exit(1)
    survivor = mutantlar_kostur()
    if survivor is None:
        print("SONUC: KIRMIZI (TABAN)")
        sys.exit(1)
    print("MUTANT %d · SURVIVOR=%d%s" % (len(MUTANTLAR), len(survivor),
                                         (" (" + ", ".join(survivor) + ")") if survivor else ""))
    sys.exit(1 if survivor else 0)


if __name__ == "__main__":
    main()
