#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — onizleme derleyici imajinin DRIFT + KAPSAM kapisi (tools/onizleme-kapisi.py).

DURUST ETIKET: olculen sey bir DISIPLIN/DRIFT kapisidir, GUVENLIK SINIRI DEGIL. Bu test
kapinin (a) fiilen ayirt edici oldugunu, (b) govdesi no-op yapilinca oldugunu, (c) CI
cagri satiri silinince oldugunu KANITLAR. Imajin guvenli oldugunu, uretecin dogru
geometri urettigini ya da paketin kaynaginin saglam oldugunu KANITLAMAZ.

BU DOSYA NEYIN YERINE GECTI (nobetci OLMEDI, GENELLESTI):
  Eski hali `duman_toka_kabul.py` idi: onizleme-imaj.yml metnindeki TEK BIR ailenin
  (toka) elle yazilmis curl'unu jeton jeton pinliyordu. O kapi 27 Tem kanamasini
  (imaj toka'siz cikti -> canli 404 -> musteri "Onizleme olusturulamadi") kapatiyordu
  ama SINIFI kapatmiyordu: elle yazilmis listeye girmeyen HER aile ayni sessizlikte
  kaliyordu. Yeni duman kapisi aile listesini DIZIN TARAMASIYLA uretir; dolayisiyla
  "toka pinlenmis mi" sorusunun yerini "musteriye ACIK her aile gercekten derleniyor
  mu" sorusu aldi. 27 Tem korumasi Bolum T'de GENEL bicimde yeniden olculur: servisten
  bir aile dusurulunce kapi KIRMIZI yanmak ZORUNDA.

OLCUM TAMAMEN OFFLINE + SENTETIK: Docker YOK, R2 YOK, openscad YOK, sir YOK.
Fikstur olarak sahte bir "paket" (kukla .scad'lar + eslem), sahte bir sema dizini ve
sahte bir secenekler.js uretilir; gercek onizleme/derleyici/server.py `--mock` ile
ayaga kaldirilir ve GERCEK kapi fonksiyonlari onun uzerinde kosturulur.

BOLUMLER:
  (NK) NEGATIF KONTROL — kapi govdesi sentetik iyi'yi gecirir, sentetik bozugu reddeder.
  (A)  TEMEL           — dogru kurulumda duman + parmakizi YESIL.
  (B1) MUT-scad        — bir .scad ICERIGI degisince parmakizi KIRMIZI + DOSYA ADINI soyler.
  (B2) MUT-kayit       — kayit (repo HEAD) tarafi degisince (paket dokunulmadan) KIRMIZI.
  (B3) MUT-eksik/fazla — pakete .scad eklenince/cikinca KIRMIZI + adiyla.
  (T)  27 TEM SINIFI   — musteriye ACIK bir aile servisten dusurulunce KIRMIZI (toka
                         korumasinin genellestirilmis hali).
  (C1) YENI AILE       — yeni sahte uretec ailesi eklenip SERVIS EDILINCE duman onu
                         KENDILIGINDEN dener (listede gorunur; elle liste guncellemesi YOK).
  (C2) YENI AILE eksik — ayni aile serviste YOKKEN duman KIRMIZI.
  (S)  OLU URETEC      — pakette olup hicbir ailenin surmedigi .scad kalirsa KIRMIZI.
  (D)  NO-OP MUTASYONU — kapi govdeleri AST ile `return []` yapilinca yukaridaki KIRMIZI'lar
                         KAYBOLMALI (yani raporlanan kirmizilik GERCEKTEN kapi govdesinden
                         geliyor; test baska bir seye bakip yanilmiyor).
  (E)  CI CAGRI SATIRI — onizleme-imaj.yml'de iki kapi komutu FIILEN kosuyor mu; satirlari
                         silinmis mutantta bu kontrol KIRMIZI yanmali (bu depoda olculmus
                         tuzak: nobetci yazilir, cagrisi silinince sessizce olur).
  (F)  YANLIS-POZITIF  — ilgisiz rutin duzenlemeler (bir `.md`, pakete giren `.scad`-DISI
                         bir dosya, bir YAML yorumu) kapiyi KIRMIZI YAKMAMALI.

Kullanim: python3 onizleme/test/duman_kabul.py
Cikis: 0 = YESIL, 1 = KIRMIZI (her kusur ayri satirda).
"""
import ast
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(TEST_DIR))
KAPI_YOL = os.path.join(REPO, "tools", "onizleme-kapisi.py")
SERVER_YOL = os.path.join(REPO, "onizleme", "derleyici", "server.py")
YML = os.path.join(REPO, ".github", "workflows", "onizleme-imaj.yml")

# (E) CI'da FIILEN kosmasi beklenen iki kapi cagrisi — duz alt-dize (ayristirici taklidi
# YOK; bkz. [[mimar-kapi-parser-taklidi]] ve tools/ci-kapsam-test.py TUR 2/3 dersleri).
CI_BEKLENEN = (
    "tools/onizleme-kapisi.py parmakizi-dogrula",
    "tools/onizleme-kapisi.py duman",
)


# --------------------------------------------------------------- modul yukleme

def kapi_yukle(kaynak=None, ad="onizleme_kapisi"):
    """tools/onizleme-kapisi.py'yi modul olarak yukler. `kaynak` verilirse (no-op
    mutasyonu) o METINDEN yuklenir — gercek dosyaya DOKUNULMAZ."""
    if kaynak is None:
        spec = importlib.util.spec_from_file_location(ad, KAPI_YOL)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    mod = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(ad, loader=None))
    mod.__file__ = KAPI_YOL
    exec(compile(kaynak, KAPI_YOL, "exec"), mod.__dict__)
    return mod


def noop_kaynak(fonksiyon_adlari):
    """AST ile verilen fonksiyonlarin GOVDESINI `return []` yapar.

    ANCHOR-BAGIMSIZ (bilincli): metin arama/replace YOK -> docstring/yorum degisince
    mutasyon bayatlamaz. Hedef bulunamazsa SESSIZ GECMEZ, istisna atar."""
    with open(KAPI_YOL, "r", encoding="utf-8") as f:
        agac = ast.parse(f.read(), filename=KAPI_YOL)
    bulundu = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.FunctionDef) and dugum.name in fonksiyon_adlari:
            dugum.body = [ast.Return(value=ast.List(elts=[], ctx=ast.Load()))]
            bulundu.add(dugum.name)
    eksik = set(fonksiyon_adlari) - bulundu
    if eksik:
        raise ValueError("no-op mutasyonu HEDEFINI BULAMADI: %s (fonksiyon yeniden "
                         "adlandirilmissa bu testi guncelle)" % ", ".join(sorted(eksik)))
    return ast.unparse(ast.fix_missing_locations(agac))


# ------------------------------------------------------------------- fikstur

ALFA_SEMA = {
    "id": "sentetik-aile-alfa",
    "parametreler": [
        {"ad": "boy", "tip": "sayi", "min": 10, "max": 100, "adim": 1, "varsayilan": 40},
    ],
}
BETA_SEMA = {
    "id": "sentetik-aile-beta",
    "parametreler": [
        {"ad": "boy", "tip": "sayi", "min": 10, "max": 100, "adim": 1, "varsayilan": 50},
        {"ad": "tip", "tip": "secim", "varsayilan": "duz",
         "secenekler": [{"deger": "duz"}, {"deger": "egri"}]},
    ],
}
# YENI AILE fiksturu (C1/C2): "repoya yeni bir uretec ailesi eklendi" senaryosu.
GAMA_SEMA = {
    "id": "sentetik-aile-gama",
    "parametreler": [
        {"ad": "boy", "tip": "sayi", "min": 5, "max": 60, "adim": 1, "varsayilan": 20},
    ],
}
SEMALAR = {"alfa": ALFA_SEMA, "beta": BETA_SEMA, "gama": GAMA_SEMA}


def eslem_blogu(scad, secici=None, varyantlar=None):
    return {"scad": scad, "secici": secici,
            "ortak": {"sayisal": {"Boy": {"terimler": {"boy": 1}}}},
            "varyantlar": varyantlar}


def fikstur_kur(kok, aileler=("alfa", "beta")):
    """(paket_dizin, sema_dizin, secenekler_js) uretir.

    beta CIFT URETECLIDIR (tip=duz -> beta.scad, tip=egri -> beta2.scad) — gercek
    pakette yay/vida ailelerinin sinifi; ikinci .scad'in denenmemis kalmadigini olcer."""
    paket = os.path.join(kok, "paket")
    sema = os.path.join(kok, "semalar")
    os.makedirs(paket, exist_ok=True)
    os.makedirs(sema, exist_ok=True)

    eslem = {"surum": 99, "aileler": {}}
    scadlar = {}
    for ad in aileler:
        if ad == "beta":
            scadlar["beta.scad"] = "// sentetik beta duz\ncube(Boy);\n"
            scadlar["beta2.scad"] = "// sentetik beta egri\nsphere(Boy);\n"
            eslem["aileler"]["sentetik-aile-beta"] = eslem_blogu(
                "beta.scad", "tip",
                {"duz": {"scad": "beta.scad"}, "egri": {"scad": "beta2.scad"}})
        else:
            scadlar["%s.scad" % ad] = "// sentetik %s\ncube(Boy);\n" % ad
            eslem["aileler"]["sentetik-aile-%s" % ad] = eslem_blogu("%s.scad" % ad)
        with open(os.path.join(sema, "sentetik-aile-%s.json" % ad), "w",
                  encoding="utf-8") as f:
            json.dump(SEMALAR[ad], f, ensure_ascii=False)
    for ad, govde in scadlar.items():
        with open(os.path.join(paket, ad), "w", encoding="utf-8") as f:
            f.write(govde)
    with open(os.path.join(paket, "eslem-ozel.json"), "w", encoding="utf-8") as f:
        json.dump(eslem, f, ensure_ascii=False)

    secenekler = os.path.join(kok, "secenekler.js")
    acik = json.dumps(["sentetik-aile-%s" % a for a in aileler])
    # NOT: ONIZLEME_KISITLAR bilerek TIRNAKSIZ anahtarla ve IC ICE yazilir — gercek
    # secenekler.js'teki yazim budur ve kapinin ilk surumu tam burada sessizce bos
    # sozluk dondurup 6 aileyi SAHTE-KIRMIZI yakmisti. Fikstur o dersi PINLER.
    with open(secenekler, "w", encoding="utf-8") as f:
        f.write("var ONIZLEME_AILELER = %s;\n" % acik)
        f.write('var ONIZLEME_KISITLAR = {\n'
                '  "sentetik-aile-beta": { tip: ["duz", "egri"] }\n};\n')
    return paket, sema, secenekler


def aile_sil(paket, aile_id):
    """Servis tarafindan (imaj) bir aileyi dusur — eslem'den cikar."""
    yol = os.path.join(paket, "eslem-ozel.json")
    with open(yol, "r", encoding="utf-8") as f:
        eslem = json.load(f)
    del eslem["aileler"][aile_id]
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(eslem, f, ensure_ascii=False)


def kayit_yaz(kapi, kok, paket):
    yol = os.path.join(kok, "parmakizi.json")
    kapi.manifest_yaz(yol, kapi.scad_parmakizlari(paket), "sentetik fikstur")
    return yol


# ------------------------------------------------------------------- servis

def _bos_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Servis(object):
    """server.py --mock ile ayaga kalkan GERCEK derleyici servisi (openscad GEREKMEZ)."""

    def __init__(self, paket):
        self.port = _bos_port()
        self.url = "http://127.0.0.1:%d" % self.port
        self.proc = subprocess.Popen(
            [sys.executable, SERVER_YOL, "--mock", "--paket", paket,
             "--port", str(self.port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def hazir(self, sn=20.0):
        son = time.time() + sn
        while time.time() < son:
            if self.proc.poll() is not None:
                return False
            try:
                urllib.request.urlopen(self.url + "/saglik", timeout=1).read()
                return True
            except Exception:                                # noqa: BLE001
                time.sleep(0.1)
        return False

    def kapat(self):
        try:
            self.proc.kill()
            self.proc.wait(timeout=5)
        except Exception:                                    # noqa: BLE001
            pass


def duman_kos(kapi, url, sema, secenekler, yaz=None):
    acik, semalar, kisitlar = kapi.duman_plani(sema, secenekler)
    return kapi.duman_kusurlari(url, acik, semalar, kisitlar, zaman_asimi=20, yaz=yaz)


# ------------------------------------------------------------------- CI kablo

def _icra_satirlari(metin):
    """YORUM OLMAYAN, adim ADI olmayan satirlarin govdeleri (tools/ci-kapsam-test.py ile
    ayni kaba + fail-closed yaklasim; YAML ayristiricisi TAKLIT EDILMEZ)."""
    out = []
    for ham in metin.splitlines():
        s = ham.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("- name:") or s.startswith("name:"):
            continue
        if s.startswith("run:"):
            s = s[4:].strip()
        if s:
            out.append(s)
    return out


def ci_kusurlari(metin):
    """KAPI GOVDESI (E) — iki kapi komutu YML'de FIILEN kosuyor mu."""
    govdeler = _icra_satirlari(metin)
    kusurlar = []
    for beklenen in CI_BEKLENEN:
        if not any(beklenen in g for g in govdeler):
            kusurlar.append(
                "CI CAGRI SATIRI YOK: onizleme-imaj.yml'de yorum olmayan hicbir icra "
                "govdesinde '%s' gecmiyor -> kapi yazildi ama CI'da KOSMUYOR "
                "(bu depoda olculmus tuzak)." % beklenen)
    return kusurlar


def ci_mutant(metin, beklenen):
    """Verilen kapi cagrisini iceren TUM icra satirlarini siler."""
    yeni = []
    for ham in metin.splitlines():
        s = ham.strip()
        if beklenen in s and not s.startswith("#"):
            continue
        yeni.append(ham)
    return "\n".join(yeni)


# ---------------------------------------------------------------------- main

def main():
    hatalar = []
    notlar = []

    def ok(etiket):
        print("  [OK ] " + etiket)

    def kirmizi(etiket):
        hatalar.append(etiket)
        print("  [RED] " + etiket)

    kapi = kapi_yukle()
    kok = tempfile.mkdtemp(prefix="duman-kabul-")
    servis = None
    sema_c = secenekler_c = None
    try:
        # ---------------- (NK) NEGATIF KONTROL: kapi govdesi ayirt edici mi
        iyi = {"a.scad": "11", "b.scad": "22"}
        if kapi.parmakizi_farklari(iyi, dict(iyi)):
            kirmizi("(NK) parmakizi_farklari SENTETIK IYI girdide kusur uydurdu")
        bozuk = kapi.parmakizi_farklari(iyi, {"a.scad": "99"})
        if not bozuk or not any("a.scad" in k for k in bozuk):
            kirmizi("(NK) parmakizi_farklari SENTETIK BOZUK girdiyi kusursuz saydi / adini "
                    "soylemedi -> lastik damga")
        else:
            ok("(NK) negatif kontrol: kapi govdesi iyi'yi gecirdi, bozugu ADIYLA reddetti")

        # ---------------- (A) TEMEL
        paket, sema, secenekler = fikstur_kur(os.path.join(kok, "a"))
        kayit = kayit_yaz(kapi, kok, paket)
        servis = Servis(paket)
        if not servis.hazir():
            kirmizi("(A) sentetik servis ayaga kalkmadi (server.py --mock)")
            return rapor(hatalar, notlar)
        temel_duman = duman_kos(kapi, servis.url, sema, secenekler)
        temel_pk_dizin = kapi.parmakizi_farklari(
            kapi.manifest_oku(kayit), kapi.scad_parmakizlari(paket))
        temel_pk_url = kapi.parmakizi_farklari(
            kapi.manifest_oku(kayit), kapi.servis_parmakizlari(servis.url))
        if temel_duman:
            kirmizi("(A) TEMEL duman KIRMIZI olmamaliydi: " + "; ".join(temel_duman))
        if temel_pk_dizin or temel_pk_url:
            kirmizi("(A) TEMEL parmakizi KIRMIZI olmamaliydi: %s / %s"
                    % (temel_pk_dizin, temel_pk_url))
        if not (temel_duman or temel_pk_dizin or temel_pk_url):
            ok("(A) TEMEL: duman + parmakizi (paket dizini VE kosan servis) YESIL")

        # ---------------- (B1) MUT-scad: paketteki .scad icerigi degisti
        beta_yol = os.path.join(paket, "beta.scad")
        with open(beta_yol, "r", encoding="utf-8") as f:
            beta_orj = f.read()
        with open(beta_yol, "w", encoding="utf-8") as f:
            f.write(beta_orj + "// KAYNAK DEGISTI\n")
        b1_dizin = kapi.parmakizi_farklari(kapi.manifest_oku(kayit),
                                           kapi.scad_parmakizlari(paket))
        b1_url = kapi.parmakizi_farklari(kapi.manifest_oku(kayit),
                                         kapi.servis_parmakizlari(servis.url))
        b1_ok = (bool(b1_dizin) and any("beta.scad" in k for k in b1_dizin)
                 and bool(b1_url) and any("beta.scad" in k for k in b1_url))
        if not b1_ok:
            kirmizi("(B1) .scad icerigi degisti ama parmakizi kapisi ADIYLA KIRMIZI "
                    "vermedi (dizin=%s / url=%s)" % (b1_dizin, b1_url))
        else:
            ok("(B1) MUT-scad: icerik degisince KIRMIZI + 'beta.scad' adiyla "
               "(hem paket dizini hem KOSAN SERVIS tarafinda)")
        with open(beta_yol, "w", encoding="utf-8") as f:
            f.write(beta_orj)

        # ---------------- (B2) MUT-kayit: repo HEAD tarafi degisti, paket dokunulmadi
        bozuk_kayit = kapi.manifest_oku(kayit)
        bozuk_kayit["alfa.scad"] = "0" * 64
        b2 = kapi.parmakizi_farklari(bozuk_kayit, kapi.scad_parmakizlari(paket))
        if not (b2 and any("alfa.scad" in k for k in b2)):
            kirmizi("(B2) kayit tarafi degisti ama kapi KIRMIZI vermedi: %s" % b2)
        else:
            ok("(B2) MUT-kayit: kayit tarafi degisince (paket DOKUNULMADAN) KIRMIZI "
               "+ 'alfa.scad' adiyla")

        # ---------------- (B3) eksik / fazla dosya
        b3_fazla = kapi.parmakizi_farklari(
            kapi.manifest_oku(kayit),
            dict(kapi.scad_parmakizlari(paket), **{"sonradan.scad": "ab" * 32}))
        eksik_kayit = dict(kapi.manifest_oku(kayit))
        eksik_kayit["hicyok.scad"] = "cd" * 32
        b3_eksik = kapi.parmakizi_farklari(eksik_kayit, kapi.scad_parmakizlari(paket))
        if not (b3_fazla and any("sonradan.scad" in k for k in b3_fazla)):
            kirmizi("(B3) pakete FAZLA dosya girdi ama kapi sustu: %s" % b3_fazla)
        elif not (b3_eksik and any("hicyok.scad" in k for k in b3_eksik)):
            kirmizi("(B3) kayittaki dosya paketten EKSIK ama kapi sustu: %s" % b3_eksik)
        else:
            ok("(B3) MUT-eksik/fazla: iki yon de KIRMIZI + dosya adiyla")

        # ---------------- (T) 27 TEM SINIFI: serviste aile dusurulurse
        servis.kapat()
        paket_t, sema_t, secenekler_t = fikstur_kur(os.path.join(kok, "t"))
        # secenekler.js (musteri/repo tarafi) beta'yi ACIK tutar; SERVIS beta'yi kaybeder.
        aile_sil(paket_t, "sentetik-aile-beta")
        servis = Servis(paket_t)
        if not servis.hazir():
            kirmizi("(T) servis ayaga kalkmadi")
        else:
            t_kusur = duman_kos(kapi, servis.url, sema_t, secenekler_t)
            if not (t_kusur and any("sentetik-aile-beta" in k and "SERVIS-DISI" in k
                                    for k in t_kusur)):
                kirmizi("(T) 27 TEM SINIFI ACIK: musteriye ACIK bir aile servisten "
                        "dusurulunce duman kapisi KIRMIZI vermedi: %s" % t_kusur)
            else:
                ok("(T) 27 TEM SINIFI: serviste olmayan ACIK aile -> KIRMIZI + aile adiyla "
                   "(eski toka-pin'inin genellestirilmis hali)")

        # ---------------- (C1) YENI SAHTE URETEC AILESI, servis EDILIYOR
        servis.kapat()
        paket_c, sema_c, secenekler_c = fikstur_kur(
            os.path.join(kok, "c"), aileler=("alfa", "beta", "gama"))
        servis = Servis(paket_c)
        if not servis.hazir():
            kirmizi("(C1) servis ayaga kalkmadi")
        else:
            satirlar = []
            c1_kusur = duman_kos(kapi, servis.url, sema_c, secenekler_c,
                                 yaz=satirlar.append)
            metin = "\n".join(satirlar)
            kapsandi = "sentetik-aile-gama" in metin
            if c1_kusur:
                kirmizi("(C1) yeni aile eklenince duman KIRMIZI oldu (olmamaliydi): %s"
                        % c1_kusur)
            if not kapsandi:
                kirmizi("(C1) YENI AILE KAPSANMADI: 'sentetik-aile-gama' duman ciktisinin "
                        "denenen aile listesinde GORUNMEDI -> sabit liste deligi hala acik")
            if not c1_kusur and kapsandi:
                ok("(C1) YENI AILE: yeni .scad + sema eklenince duman testi onu ELLE LISTE "
                   "GUNCELLEMESI OLMADAN dener (listede gorundu, YESIL)")

            # ---------------- (C2)+(S) ayni aile SERVISTEN dusurulunce
            aile_sil(paket_c, "sentetik-aile-gama")
            servis.kapat()
            servis = Servis(paket_c)
            if not servis.hazir():
                kirmizi("(C2) servis ayaga kalkmadi")
            else:
                c2_kusur = duman_kos(kapi, servis.url, sema_c, secenekler_c)
                if not (c2_kusur and any("sentetik-aile-gama" in k for k in c2_kusur)):
                    kirmizi("(C2) yeni aile SERVIS EDILEMEZ durumdayken duman KIRMIZI "
                            "vermedi: %s" % c2_kusur)
                else:
                    ok("(C2) YENI AILE servis edilemiyorsa KIRMIZI + aile adiyla")
                # (S) gama.scad pakette duruyor ama artik hicbir aile onu surmuyor.
                if not any("DENENMEMIS URETEC" in k and "gama.scad" in k
                           for k in c2_kusur):
                    kirmizi("(S) OLU URETEC: hicbir ailenin surmedigi 'gama.scad' pakette "
                            "kaldi ama kapi bunu soylemedi: %s" % c2_kusur)
                else:
                    ok("(S) OLU URETEC: pakette olup hic derletilmeyen .scad KIRMIZI + adiyla")

        # ---------------- (D) NO-OP MUTASYONU (kapi GERCEKTEN cagriliyor mu)
        noop = kapi_yukle(noop_kaynak({"parmakizi_farklari", "duman_kusurlari"}),
                          ad="onizleme_kapisi_noop")
        d_hata = []
        if noop.parmakizi_farklari(iyi, {"a.scad": "99"}):
            d_hata.append("parmakizi_farklari govdesi no-op yapildigi halde KIRMIZI verdi "
                          "-> raporlanan kirmizilik kapi govdesinden GELMIYOR")
        if servis and servis.proc.poll() is None and sema_c:
            acik_n, semalar_n, kisitlar_n = noop.duman_plani(sema_c, secenekler_c)
            if noop.duman_kusurlari(servis.url, acik_n, semalar_n, kisitlar_n,
                                    zaman_asimi=20):
                d_hata.append("duman_kusurlari govdesi no-op yapildigi halde KIRMIZI verdi "
                              "-> kapi govdesi load-bearing DEGIL")
        else:
            d_hata.append("duman no-op olcumu KOSMADI (servis ayakta degil) -> kanit eksik")
        for h in d_hata:
            kirmizi("(D) NO-OP: " + h)
        if not d_hata:
            ok("(D) NO-OP MUTASYONU: iki kapi govdesi de `return []` yapilinca yukaridaki "
               "KIRMIZI'lar KAYBOLDU -> kirmizilik gercekten kapi govdesinden geliyor")

        # ---------------- (E) CI CAGRI SATIRI
        e_mutasyon_hatasi = False
        if not os.path.isfile(YML):
            kirmizi("(E) workflow dosyasi yok: %s" % YML)
            e_mutasyon_hatasi = True
        else:
            with open(YML, "r", encoding="utf-8") as f:
                yml_metin = f.read()
            if "\t" in yml_metin:
                kirmizi("(E) YML'de sekme (TAB) karakteri var — YAML'de yasak")
            e_kusur = ci_kusurlari(yml_metin)
            if e_kusur:
                for k in e_kusur:
                    kirmizi("(E) " + k)
            else:
                ok("(E) CI CAGRI SATIRI: onizleme-imaj.yml iki kapi komutunu da FIILEN "
                   "kosuyor (%s)" % " · ".join(CI_BEKLENEN))
            for beklenen in CI_BEKLENEN:
                mutant = ci_mutant(yml_metin, beklenen)
                if mutant == yml_metin:
                    kirmizi("(E) MUTASYON BAYAT: '%s' iceren hicbir satir silinemedi "
                            "(cagri bicimi degistiyse bu testi guncelle)" % beklenen)
                    e_mutasyon_hatasi = True
                elif not ci_kusurlari(mutant):
                    kirmizi("(E) MUTASYON KOR: '%s' cagri satiri SILINDIGI halde kontrol "
                            "YINE YESIL -> nobetci lastik damga" % beklenen)
                    e_mutasyon_hatasi = True
            if not e_mutasyon_hatasi:
                ok("(E) MUTASYON: iki cagri satirinin her biri silininca kontrol KIRMIZI")

        # ---------------- (F) YANLIS-POZITIF
        f_sayac = 0
        f_hata = []
        # F1: ilgisiz bir .md duzenlemesi — kapi govdelerinin girdisi degil.
        with open(os.path.join(kok, "ILGISIZ-NOT.md"), "w", encoding="utf-8") as f:
            f.write("# ilgisiz rutin duzenleme\n")
        f_sayac += 1
        if kapi.parmakizi_farklari(kapi.manifest_oku(kayit),
                                   kapi.scad_parmakizlari(paket)):
            f_hata.append("F1 ilgisiz .md eklenmesi parmakizi kapisini KIRMIZI yakti")
        # F2: pakete .scad OLMAYAN bir dosya girdi (notlar) — kapsam disi kalmali.
        with open(os.path.join(paket, "NOTLAR.txt"), "w", encoding="utf-8") as f:
            f.write("ilgisiz\n")
        f_sayac += 1
        if kapi.parmakizi_farklari(kapi.manifest_oku(kayit),
                                   kapi.scad_parmakizlari(paket)):
            f_hata.append("F2 pakete giren .scad-DISI dosya parmakizi kapisini KIRMIZI yakti")
        # F3: onizleme-imaj.yml'e ilgisiz bir yorum satiri eklendi.
        if os.path.isfile(YML):
            with open(YML, "r", encoding="utf-8") as f:
                yml_metin = f.read()
            yorumlu = yml_metin.replace("jobs:", "# ilgisiz rutin yorum\njobs:", 1)
            f_sayac += 1
            if ci_kusurlari(yorumlu):
                f_hata.append("F3 ilgisiz YAML yorumu CI kablo kontrolunu KIRMIZI yakti")
        for h in f_hata:
            kirmizi("(F) YANLIS-POZITIF: " + h)
        if not f_hata:
            ok("(F) YANLIS-POZITIF: %d ilgisiz rutin degisiklik denendi, KIRMIZI sayisi 0"
               % f_sayac)
        notlar.append("yanlis-pozitif denemesi: %d · kirmizi: %d" % (f_sayac, len(f_hata)))

    finally:
        if servis:
            servis.kapat()
        shutil.rmtree(kok, ignore_errors=True)

    return rapor(hatalar, notlar)


def rapor(hatalar, notlar):
    for n in notlar:
        print("  [not] " + n)
    print("OZET: kusur=%d" % len(hatalar))
    if hatalar:
        print("\n".join("KIRMIZI: " + h for h in hatalar))
        return 1
    print("YESIL: onizleme drift+kapsam kapisi ayirt edici, govdesi load-bearing, "
          "CI cagri satirlari yerinde; yeni aile elle liste guncellemesi olmadan kapsandi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
