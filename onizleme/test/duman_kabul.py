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

  --- 30 Tem ONARIM TURU (tur 3) — curutme turunun kapattigi alti delik ---
  (O2) PARMAKIZI KAPSAMI — kayit paketin TAMAMINI olcuyor mu: `eslem-ozel.json` icerigi
                         degisince KIRMIZI · pakete giren yeni dosya TURU (.txt) KIRMIZI ·
                         surum 1 (yalniz *.scad) kaydi FAIL-CLOSED reddediliyor.
  (O3) BOS KUME        — bos kayit · bos paket · bos ONIZLEME_AILELER · bos sema dizini
                         AYRI AYRI KIRMIZI (eskiden nobet yalniz YAZICIDAYDI, dogrulayici
                         bos kumede sessizce YESIL yaniyordu). Regresyon: OLMAYAN kayit
                         hala fail-closed.
  (O4) KAPSAMA CAPRAZI — "N/N kapsandi" servisin kendi beyani DEGIL: comert yalan ·
                         eksik beyan · /parmakizi yalani (KAYIT kazanir) · eslemin
                         PAKETTE OLMAYAN bir .scad'i surmesi -> dordu de KIRMIZI.
  (O5) KISIT/OLU AYRIMI— ONIZLEME_KISITLAR ile BILINCLI kapatilan varyant "olu uretec"
                         SAYILMAZ (YESIL + "kisitla kapali: N"), ama GERCEK olu uretec
                         HALA KIRMIZI (bu onarim Ç5'i gevsetmemeli).
  (D2) YENI GOVDE NO-OP— yukaridaki her yeni nobet govdesi AYRI AYRI oldurulunce ilgili
                         KIRMIZI KAYBOLMALI (KACAN = 0).
  (E)  CI CAGRI SATIRI — UC kapi adimi (kabul testinin KENDISI dahil) CI'da FIILEN
                         BLOKLAYICI kosuyor mu. Olcum tools/is-akisi-kapisi.py BOLUM B'ye
                         DELEGE edilir (gercek YAML ayristiricisi); curutme turunda
                         olculen 8 etkisizlestirme mutasyonunun HEPSI KIRMIZI olmali.
                         (Eski duz-alt-dize yontemi 8'in 7'sini sessizce geciriyordu.)
  (F)  YANLIS-POZITIF  — 8 MESRU rutin senaryo (yeni aile · yalniz yorum degisimi · yeni
                         opsiyonel sema parametresi · kapi kosturmayan yeni CI adimi ·
                         yeni ONIZLEME_KISITLAR kisiti · ters siralı paket yazimi ·
                         ilgisiz `.md` · ilgisiz YAML yorumu) KIRMIZI YAKMAMALI.

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

# 🔴 KALDIRILDI (30 Tem, O1): eski `CI_BEKLENEN` + `ci_kusurlari()` ikilisi CI kablosunu
# DUZ ALT-DIZE ile olcuyordu. Curutme turunda bu yontemin 8 mutasyondan 7'sini SESSIZCE
# gecirdigi olculdu (`|| true` · `continue-on-error: true` · `echo ` mensiyonu · `--help` ·
# `if: false` · tetikleyici degisimi · ve KABUL TESTININ KENDI cagri satirinin silinmesi).
# Yerine GERCEK nobetci kullanilir: tools/is-akisi-kapisi.py BOLUM B (gercek YAML
# ayristiricisi + jeton/yardim/etkisizlestirme/tetikleyici nobetleri). Bu dosya o
# nobetciyi MODUL olarak yukler; ikinci bir kopya TUTULMAZ ([[ayna-kapi-kesif-ekseni]]).


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


def kayit_yaz(kapi, kok, paket, ad="parmakizi.json"):
    """O2: kayit paketin TUM dosyalarindan uretilir (eslem-ozel.json dahil)."""
    yol = os.path.join(kok, ad)
    kapi.manifest_yaz(yol, kapi.paket_parmakizlari(paket), "sentetik fikstur")
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


def duman_kos(kapi, url, sema, secenekler, yaz=None, manifest=None):
    acik, semalar, kisitlar = kapi.duman_plani(sema, secenekler)
    return kapi.duman_kusurlari(url, acik, semalar, kisitlar, zaman_asimi=20, yaz=yaz,
                                manifest=manifest)


class Yalanci(object):
    """SAHTE derleyici servisi — /saglik /kapsam /parmakizi /derle BEYANLARINI mutasyona
    acar. Amaci gercek server.py'nin yerine gecmek DEGIL; "servis KENDI hakkinda yalan
    soylerse kapi ne yapar" sorusunu olcmek (O4: kapsama iddiasinin servisin beyanindan
    bagimsiz bir kaynakla caprazlanmasi)."""

    def __init__(self, aileler, kapsam, parmakizi, derle_kod=200, derle_boyut=684):
        import http.server
        import threading
        veri = {"saglik": {"durum": "hazir", "aileler": sorted(aileler), "mock": True},
                "kapsam": {"aileler": kapsam},
                "parmakizi": {"algoritma": "sha256", "dosyalar": parmakizi}}

        class Islem(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):          # sessiz
                pass

            def _yaz(self, kod, govde):
                ham = json.dumps(govde).encode("utf-8")
                self.send_response(kod)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(ham)))
                self.end_headers()
                self.wfile.write(ham)

            def do_GET(self):
                ad = self.path.lstrip("/")
                if ad in veri:
                    return self._yaz(200, veri[ad])
                self._yaz(404, {"hata": "bulunamadi"})

            def do_POST(self):
                uz = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(uz)
                if derle_kod != 200:
                    return self._yaz(derle_kod, {"hata": "sentetik"})
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(derle_boyut))
                self.end_headers()
                self.wfile.write(b"x" * derle_boyut)

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Islem)
        self.url = "http://127.0.0.1:%d" % self.srv.server_address[1]
        self.is_parcacigi = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.is_parcacigi.start()

    def kapat(self):
        try:
            self.srv.shutdown()
            self.srv.server_close()
        except Exception:                                    # noqa: BLE001
            pass


# ------------------------------------------------------------------- CI kablo

def _satir_donustur(metin, capa, donustur):
    """capa'yi ICEREN yorum-olmayan satirlari donustur(satir) ile degistir.
    donustur None dondururse satir SILINIR."""
    yeni = []
    for ham in metin.splitlines():
        s = ham.strip()
        if capa in s and not s.startswith("#"):
            sonuc = donustur(ham)
            if sonuc is None:
                continue
            yeni.append(sonuc)
            continue
        yeni.append(ham)
    return "\n".join(yeni) + "\n"


def _adim_ozelligi(metin, capa, ozellik):
    """capa'yi iceren satirin AIT OLDUGU adimin `- name:` satirinin ALTINA bir
    ozellik (`continue-on-error: true` / `if: false`) enjekte eder."""
    satirlar = metin.splitlines()
    hedef = None
    for i, ham in enumerate(satirlar):
        if capa in ham.strip() and not ham.strip().startswith("#"):
            hedef = i
            break
    if hedef is None:
        return metin
    for i in range(hedef, -1, -1):
        s = satirlar[i].lstrip()
        if s.startswith("- name:"):
            girinti = " " * (len(satirlar[i]) - len(s) + 2)
            satirlar.insert(i + 1, girinti + ozellik)
            break
    return "\n".join(satirlar) + "\n"


# CURUTME TURUNDA OLCULEN 8 MUTASYON — 7'si SESSIZCE YESIL geciyordu.
# Capa olarak KABUL TESTININ KENDI cagrisi (f) ve kapi cagrilari kullanilir.
_CAPA_KAPI = "tools/onizleme-kapisi.py duman"
_CAPA_PK = "tools/onizleme-kapisi.py parmakizi-dogrula"
_CAPA_KABUL = "onizleme/test/duman_kabul.py"


def ci_mutantlar(metin):
    """[(ad, mutant_metin), ...] — hepsi BOLUM B tarafindan KIRMIZI yakilmali."""
    return [
        ("(a) kapi cagri satirlari TAMAMEN silindi",
         _satir_donustur(_satir_donustur(metin, _CAPA_KAPI, lambda s: None),
                         _CAPA_PK, lambda s: None)),
        ("(b) `|| true` eklendi",
         _satir_donustur(metin, _CAPA_KAPI, lambda s: s + " || true")),
        ("(c) adima `continue-on-error: true` eklendi",
         _adim_ozelligi(metin, _CAPA_KAPI, "continue-on-error: true")),
        ("(d) `echo ` ile mensiyona cevrildi",
         _satir_donustur(metin, _CAPA_KAPI,
                         lambda s: s.replace("python3", "echo python3", 1))),
        ("(e) `--help`e cevrildi",
         _satir_donustur(metin, _CAPA_KAPI, lambda s: s + " --help")),
        ("(f) KABUL TESTININ KENDI cagri satiri silindi",
         _satir_donustur(metin, _CAPA_KABUL, lambda s: None)),
        ("(g) adima `if: false` eklendi",
         _adim_ozelligi(metin, _CAPA_KAPI, "if: false")),
        ("(h) is akisi tetigi workflow_call'a cevrildi",
         metin.replace("  workflow_dispatch:", "  workflow_call:", 1)),
    ]


def is_akisi_kapisi_yukle():
    """tools/is-akisi-kapisi.py'yi MODUL olarak yukle (CI kablo nobetcisi ORADADIR;
    burada ikinci bir kopyasi TUTULMAZ — [[ayna-kapi-kesif-ekseni]])."""
    yol = os.path.join(REPO, "tools", "is-akisi-kapisi.py")
    if not os.path.exists(yol):
        return None
    try:
        spec = importlib.util.spec_from_file_location("pruvo_is_akisi", yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:                                        # noqa: BLE001
        return None
    if not (hasattr(mod, "B_IDDIALAR") and hasattr(mod, "b_iddia_hatalari")):
        return None
    return mod


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
        temel_duman = duman_kos(kapi, servis.url, sema, secenekler, manifest=kayit)
        temel_pk_dizin = kapi.parmakizi_farklari(
            kapi.manifest_oku(kayit), kapi.paket_parmakizlari(paket))
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
                                           kapi.paket_parmakizlari(paket))
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
        b2 = kapi.parmakizi_farklari(bozuk_kayit, kapi.paket_parmakizlari(paket))
        if not (b2 and any("alfa.scad" in k for k in b2)):
            kirmizi("(B2) kayit tarafi degisti ama kapi KIRMIZI vermedi: %s" % b2)
        else:
            ok("(B2) MUT-kayit: kayit tarafi degisince (paket DOKUNULMADAN) KIRMIZI "
               "+ 'alfa.scad' adiyla")

        # ---------------- (B3) eksik / fazla dosya
        b3_fazla = kapi.parmakizi_farklari(
            kapi.manifest_oku(kayit),
            dict(kapi.paket_parmakizlari(paket), **{"sonradan.scad": "ab" * 32}))
        eksik_kayit = dict(kapi.manifest_oku(kayit))
        eksik_kayit["hicyok.scad"] = "cd" * 32
        b3_eksik = kapi.parmakizi_farklari(eksik_kayit, kapi.paket_parmakizlari(paket))
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
        # Kayit MUTASYONDAN SONRA yazilir: olculen sinif "servis-disi aile", kayit
        # ayrismasi DEGIL (iki sinif birbirine karismasin).
        kayit_t = kayit_yaz(kapi, kok, paket_t, "parmakizi-t.json")
        servis = Servis(paket_t)
        if not servis.hazir():
            kirmizi("(T) servis ayaga kalkmadi")
        else:
            t_kusur = duman_kos(kapi, servis.url, sema_t, secenekler_t, manifest=kayit_t)
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
        kayit_c = kayit_yaz(kapi, kok, paket_c, "parmakizi-c.json")
        servis = Servis(paket_c)
        if not servis.hazir():
            kirmizi("(C1) servis ayaga kalkmadi")
        else:
            satirlar = []
            c1_kusur = duman_kos(kapi, servis.url, sema_c, secenekler_c,
                                 yaz=satirlar.append, manifest=kayit_c)
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
            kayit_c2 = kayit_yaz(kapi, kok, paket_c, "parmakizi-c2.json")
            servis.kapat()
            servis = Servis(paket_c)
            if not servis.hazir():
                kirmizi("(C2) servis ayaga kalkmadi")
            else:
                c2_kusur = duman_kos(kapi, servis.url, sema_c, secenekler_c,
                                     manifest=kayit_c2)
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
                                    zaman_asimi=20, manifest=kayit_c2):
                d_hata.append("duman_kusurlari govdesi no-op yapildigi halde KIRMIZI verdi "
                              "-> kapi govdesi load-bearing DEGIL")
        else:
            d_hata.append("duman no-op olcumu KOSMADI (servis ayakta degil) -> kanit eksik")
        for h in d_hata:
            kirmizi("(D) NO-OP: " + h)
        if not d_hata:
            ok("(D) NO-OP MUTASYONU: iki kapi govdesi de `return []` yapilinca yukaridaki "
               "KIRMIZI'lar KAYBOLDU -> kirmizilik gercekten kapi govdesinden geliyor")

        # ---------------- (O2) PARMAKIZI KAPSAMI = PAKETIN TAMAMI
        # Curutme turu Ç2-C: `eslem-ozel.json` parmakizi kapsaminin DISINDAYDI; katsayi
        # 1 -> 1000 degistirildiginde UC kapi da YESIL kaldi. Eslem aile->uretec
        # eslemesini, katsayilari ve `varyantlar`i tasir = GEOMETRIYI BELIRLEYEN yari.
        paket_o2, sema_o2, secenekler_o2 = fikstur_kur(os.path.join(kok, "o2"))
        kayit_o2 = kayit_yaz(kapi, kok, paket_o2, "parmakizi-o2.json")
        eslem_yol = os.path.join(paket_o2, "eslem-ozel.json")
        with open(eslem_yol, "r", encoding="utf-8") as f:
            eslem_ham = f.read()
        # (O2-a) eslem ICERIGI degisti (katsayi/surum) — .scad'lere DOKUNULMADI.
        with open(eslem_yol, "w", encoding="utf-8") as f:
            f.write(eslem_ham.replace('"surum": 99', '"surum": 999'))
        o2_a = kapi.parmakizi_farklari(kapi.manifest_oku(kayit_o2),
                                       kapi.paket_parmakizlari(paket_o2))
        if not (o2_a and any("eslem-ozel.json" in k for k in o2_a)):
            kirmizi("(O2) ESLEM DRIFTI KACTI: eslem-ozel.json icerigi degistigi halde "
                    "parmakizi kapisi ADIYLA KIRMIZI vermedi: %s" % o2_a)
        else:
            ok("(O2) ESLEM KAPSAMDA: eslem-ozel.json icerigi degisince KIRMIZI + adiyla "
               "(curutme turunda bu mutasyon UC kapidan da YESIL geciyordu)")
        with open(eslem_yol, "w", encoding="utf-8") as f:
            f.write(eslem_ham)
        # (O2-b) pakete YENI BIR DOSYA TURU girdi (.txt) — uzanti beyaz listesi YOK.
        with open(os.path.join(paket_o2, "NOTLAR.txt"), "w", encoding="utf-8") as f:
            f.write("pakete sonradan giren ilgisiz dosya\n")
        o2_b = kapi.parmakizi_farklari(kapi.manifest_oku(kayit_o2),
                                       kapi.paket_parmakizlari(paket_o2))
        if not (o2_b and any("NOTLAR.txt" in k for k in o2_b)):
            kirmizi("(O2) YENI DOSYA TURU KACTI: pakete giren .txt yakalanmadi -> "
                    "kapsam hala uzantiya bagli: %s" % o2_b)
        else:
            ok("(O2) UZANTI BEYAZ LISTESI YOK: pakete giren .txt de DRIFT/FAZLA olarak "
               "adiyla KIRMIZI")
        os.remove(os.path.join(paket_o2, "NOTLAR.txt"))
        # (O2-c) SURUM NOBETI: surum 1 kaydi (yalniz 'scad') FAIL-CLOSED reddedilmeli.
        eski_kayit = os.path.join(kok, "parmakizi-surum1.json")
        with open(eski_kayit, "w", encoding="utf-8") as f:
            json.dump({"surum": 1, "algoritma": "sha256",
                       "scad": {"alfa.scad": "0" * 64}}, f)
        try:
            kapi.manifest_oku(eski_kayit)
            kirmizi("(O2) SURUM NOBETI OLU: surum 1 kaydi (paketin yarisi) sessizce "
                    "kabul edildi -> kapi eski kapsama geri doner")
        except ValueError:
            ok("(O2) SURUM NOBETI: surum 1 kaydi FAIL-CLOSED reddedildi (tek satirlik "
               "cozum talimatiyla)")

        # ---------------- (O3) BOS KUME FAIL-CLOSED
        # Curutme turu Ç3/E1: bos kayit + bos paket = YESIL idi (nobet yalniz YAZICIDA).
        o3_hata = []
        bos_kayit = os.path.join(kok, "parmakizi-bos.json")
        kapi.manifest_yaz(bos_kayit, {}, "bos")
        bos_paket = os.path.join(kok, "bos-paket")
        os.makedirs(bos_paket, exist_ok=True)
        # (O3-a) BOS KAYIT + BOS PAKET -> KIRMIZI (eskiden YESIL)
        a3 = kapi.alt_sinir_kusurlari(kapi.manifest_oku(bos_kayit),
                                      kapi.paket_parmakizlari(bos_paket), "bos paket")
        if not (any("BOS KAYIT" in k for k in a3) and any("BOS PAKET" in k for k in a3)):
            o3_hata.append("bos kayit + bos paket FAIL-OPEN kaldi: %s" % a3)
        # (O3-b) BOS PAKET tek basina (kayit dolu) -> KIRMIZI
        b3_ = kapi.alt_sinir_kusurlari(kapi.manifest_oku(kayit_o2),
                                       {}, "bos paket")
        if not any("BOS PAKET" in k for k in b3_):
            o3_hata.append("dolu kayit + bos paket KIRMIZI vermedi: %s" % b3_)
        # (O3-c) BOS ACIK AILE LISTESI ve BOS SEMA -> duman govdesi KIRMIZI
        if servis and servis.proc.poll() is None:
            bos_aile = kapi.duman_kusurlari(servis.url, [], {"x": {}}, {},
                                            zaman_asimi=20, manifest=kayit_c2)
            if not any("BOS ACIK AILE LISTESI" in k for k in bos_aile):
                o3_hata.append("ONIZLEME_AILELER=[] KIRMIZI vermedi: %s" % bos_aile)
            bos_sema = kapi.duman_kusurlari(servis.url, ["x"], {}, {},
                                            zaman_asimi=20, manifest=kayit_c2)
            if not any("BOS SEMA DIZINI" in k for k in bos_sema):
                o3_hata.append("bos sema dizini KIRMIZI vermedi: %s" % bos_sema)
        else:
            o3_hata.append("O3-c OLCULEMEDI (servis ayakta degil) -> kanit eksik")
        # (O3-d) REGRESYON: OLMAYAN kayit hala fail-closed (curutme turu E2)
        yok_kayit = os.path.join(kok, "hic-olmayan-kayit.json")
        if kapi.main(["parmakizi-dogrula", "--dizin", paket_o2,
                      "--manifest", yok_kayit]) != 1:
            o3_hata.append("REGRESYON: olmayan kayit artik fail-closed DEGIL")
        for h in o3_hata:
            kirmizi("(O3) BOS KUME: " + h)
        if not o3_hata:
            ok("(O3) BOS KUME FAIL-CLOSED: bos kayit · bos paket · bos aile listesi · "
               "bos sema dizini AYRI AYRI KIRMIZI; olmayan kayit hala fail-closed")

        # ---------------- (O4) KAPSAMA IDDIASI BAGIMSIZ KAYNAKLA CAPRAZ
        # Curutme turu Ç4/L1: "N/N kapsandi" servisin KENDI iki beyaninin carpimiydi;
        # comert yalan soyleyen stub 3 istekle 3/3 YESIL gecti.
        o4_hata = []
        gercek_pk = kapi.paket_parmakizlari(paket_o2)
        # (O4-a) COMERT YALAN: /kapsam TUM paket .scad'lerini tek ailenin varyanti sayar.
        # Iki aile de /saglik'ta bildirilir -> SERVIS-DISI AILE sinifi karismasin;
        # olculen TEK sey /kapsam beyaninin uydurma olmasi.
        comert = Yalanci(
            aileler=["sentetik-aile-alfa", "sentetik-aile-beta"],
            kapsam={"sentetik-aile-alfa": {
                        "scad": "alfa.scad", "secici": "boy",
                        "varyantlar": {"10": "beta.scad", "20": "beta2.scad"}},
                    "sentetik-aile-beta": {
                        "scad": "beta.scad", "secici": "tip",
                        "varyantlar": {"duz": "beta.scad", "UYDURMA": "beta2.scad"}}},
            parmakizi=gercek_pk)
        try:
            c_kusur = duman_kos(kapi, comert.url, sema_o2, secenekler_o2,
                                manifest=kayit_o2)
            if not any("KAPSAM BEYANI UYDURMA" in k for k in c_kusur):
                o4_hata.append("COMERT YALAN GECTI: /kapsam uydurma secici/varyant "
                               "bildirdigi halde KIRMIZI yok: %s" % c_kusur)
        finally:
            comert.kapat()
        # (O4-b) EKSIK BEYAN: /kapsam yalniz 1 aile bildirir, paket 3 .scad tasir.
        eksik = Yalanci(
            aileler=["sentetik-aile-alfa", "sentetik-aile-beta"],
            kapsam={"sentetik-aile-alfa": {"scad": "alfa.scad", "secici": None,
                                           "varyantlar": {}},
                    "sentetik-aile-beta": {"scad": "beta.scad", "secici": None,
                                           "varyantlar": {}}},
            parmakizi=gercek_pk)
        try:
            e_kusur = duman_kos(kapi, eksik.url, sema_o2, secenekler_o2,
                                manifest=kayit_o2)
            if not any("DENENMEMIS URETEC" in k and "beta" in k for k in e_kusur):
                o4_hata.append("EKSIK BEYAN GECTI: gercekte 3 .scad varken 1 beyan "
                               "edildi ama denenmemis uretec KIRMIZI'si yok: %s" % e_kusur)
        finally:
            eksik.kapat()
        # (O4-c) SERVIS /parmakizi YALANI: kayit ile ayrisir -> KAYIT KAZANIR.
        yalan_pk = dict(gercek_pk)
        yalan_pk["alfa.scad"] = "9" * 64
        yalanci_pk = Yalanci(
            aileler=["sentetik-aile-alfa", "sentetik-aile-beta"],
            kapsam={"sentetik-aile-alfa": {"scad": "alfa.scad", "secici": None,
                                           "varyantlar": {}},
                    "sentetik-aile-beta": {"scad": "beta.scad", "secici": None,
                                           "varyantlar": {}}},
            parmakizi=yalan_pk)
        try:
            p_kusur = duman_kos(kapi, yalanci_pk.url, sema_o2, secenekler_o2,
                                manifest=kayit_o2)
            if not any("KAYIT/SERVIS AYRISMASI" in k and "alfa.scad" in k
                       for k in p_kusur):
                o4_hata.append("SERVIS BEYANI KAYITLA CAPRAZLANMADI: %s" % p_kusur)
        finally:
            yalanci_pk.kapat()
        # (O4-d) ESLEM HAYALI URETEC SURUYOR (ters yon; curutme turu Ç7/M1).
        hayali = Yalanci(
            aileler=["sentetik-aile-alfa", "sentetik-aile-beta"],
            kapsam={"sentetik-aile-alfa": {"scad": "alfa.scad", "secici": None,
                                           "varyantlar": {}},
                    "sentetik-aile-beta": {
                        "scad": "beta.scad", "secici": "tip",
                        "varyantlar": {"duz": "beta.scad", "egri": "yokboyle.scad"}}},
            parmakizi=gercek_pk)
        try:
            h_kusur = duman_kos(kapi, hayali.url, sema_o2, secenekler_o2,
                                manifest=kayit_o2)
            if not any("HAYALI URETEC" in k and "yokboyle.scad" in k for k in h_kusur):
                o4_hata.append("TERS YON KACTI: eslem PAKETTE OLMAYAN bir .scad'i "
                               "surdugu halde KIRMIZI yok: %s" % h_kusur)
        finally:
            hayali.kapat()
        for h in o4_hata:
            kirmizi("(O4) KENDINDEN-MENKUL OLCUM: " + h)
        if not o4_hata:
            ok("(O4) KAPSAMA CAPRAZLANDI: comert yalan · eksik beyan · /parmakizi yalani "
               "(kayit kazandi) · hayali uretec — DORDU DE KIRMIZI")

        # ---------------- (O5) KISITLA KAPALI != OLU
        # Curutme turu Ç8/FP5: kisit yuzunden ATLANAN .scad'i kapi "olu uretec" diye
        # KIRMIZI yakiyordu. LATENT: kisit listesine yay/vida girdigi gun patlar.
        o5_hata = []
        paket_o5, sema_o5, secenekler_o5 = fikstur_kur(os.path.join(kok, "o5"))
        # beta CIFT URETECLI (duz->beta.scad, egri->beta2.scad); 'egri' KISITLANIR.
        with open(secenekler_o5, "w", encoding="utf-8") as f:
            f.write('var ONIZLEME_AILELER = ["sentetik-aile-alfa", '
                    '"sentetik-aile-beta"];\n')
            f.write('var ONIZLEME_KISITLAR = {\n'
                    '  "sentetik-aile-beta": { tip: ["duz"] }\n};\n')
        kayit_o5 = kayit_yaz(kapi, kok, paket_o5, "parmakizi-o5.json")
        servis.kapat()
        servis = Servis(paket_o5)
        if not servis.hazir():
            o5_hata.append("servis ayaga kalkmadi")
        else:
            o5_satir = []
            o5_kusur = duman_kos(kapi, servis.url, sema_o5, secenekler_o5,
                                 yaz=o5_satir.append, manifest=kayit_o5)
            o5_metin = "\n".join(o5_satir)
            if any("DENENMEMIS URETEC" in k and "beta2.scad" in k for k in o5_kusur):
                o5_hata.append("SAHTE-KIRMIZI SURUYOR: kisitla kapatilan 'beta2.scad' "
                               "hala 'olu uretec' diye yakiliyor")
            if o5_kusur:
                o5_hata.append("kisit fiksturu KIRMIZI oldu (olmamaliydi): %s" % o5_kusur)
            if "kisitla kapali: 1" not in o5_metin:
                o5_hata.append("cikti 'kisitla kapali: N' satirini basmadi -> ayrim "
                               "gorunmuyor: %s" % o5_metin)
            # O5 GEVSETME KONTROLU: GERCEK olu uretec HALA KIRMIZI olmali.
            with open(os.path.join(paket_o5, "olu.scad"), "w", encoding="utf-8") as f:
                f.write("// hicbir ailenin surmedigi dosya\ncube(1);\n")
            kayit_o5b = kayit_yaz(kapi, kok, paket_o5, "parmakizi-o5b.json")
            servis.kapat()
            servis = Servis(paket_o5)
            if not servis.hazir():
                o5_hata.append("(gevsetme kontrolu) servis ayaga kalkmadi")
            else:
                g_kusur = duman_kos(kapi, servis.url, sema_o5, secenekler_o5,
                                    manifest=kayit_o5b)
                if not any("DENENMEMIS URETEC" in k and "olu.scad" in k
                           for k in g_kusur):
                    o5_hata.append("🔴 GEVSEME: O5 onarimi Ç5'i OLDURDU — GERCEK olu "
                                   "uretec 'olu.scad' artik KIRMIZI vermiyor: %s"
                                   % g_kusur)
        for h in o5_hata:
            kirmizi("(O5) KISIT/OLU AYRIMI: " + h)
        if not o5_hata:
            ok("(O5) KISITLA KAPALI != OLU: kisitlanmis varyant YESIL + 'kisitla kapali: 1' "
               "satiri; GERCEK olu uretec HALA KIRMIZI (Ç5 gevsemedi)")

        # ---------------- (D2) YENI NOBET GOVDELERI LOAD-BEARING MI (K-C)
        # Yukaridaki O2/O3/O4/O5 KIRMIZI'lari GERCEKTEN yeni govdelerden mi geliyor?
        # Her govde ayri ayri OLDURULUR ve ilgili iddianin KAYBOLMASI beklenir. Bir
        # govde oldurulunce iddia YINE de kirmizi kaliyorsa, o iddia baska bir seye
        # bakip yaniliyordur (lastik damga).
        d2_hata = []
        # (i) alt_sinir_kusurlari (O3) — oldurulunce bos kume yeniden FAIL-OPEN olmali.
        n_alt = kapi_yukle(noop_kaynak({"alt_sinir_kusurlari"}), ad="k_noop_alt")
        if n_alt.alt_sinir_kusurlari(n_alt.manifest_oku(bos_kayit),
                                     n_alt.paket_parmakizlari(bos_paket), "x"):
            d2_hata.append("alt_sinir_kusurlari OLDURULDUGU halde O3 kirmizisi surdu "
                           "-> O3 iddiasi baska bir seye bakiyor")
        # (ii) kapsam_beyani_kusurlari (O4) — oldurulunce comert yalan yeniden GECMELI.
        n_kap = kapi_yukle(noop_kaynak({"kapsam_beyani_kusurlari"}), ad="k_noop_kapsam")
        sahte_kapsam = {"sentetik-aile-alfa": {
            "scad": "alfa.scad", "secici": "boy",
            "varyantlar": {"10": "beta.scad"}}}
        if n_kap.kapsam_beyani_kusurlari({"sentetik-aile-alfa": ALFA_SEMA},
                                         sahte_kapsam, {}):
            d2_hata.append("kapsam_beyani_kusurlari OLDURULDUGU halde O4 kirmizisi "
                           "surdu -> O4-a iddiasi baska bir seye bakiyor")
        elif not kapi.kapsam_beyani_kusurlari({"sentetik-aile-alfa": ALFA_SEMA},
                                              sahte_kapsam, {}):
            d2_hata.append("GERCEK kapsam_beyani_kusurlari ayni girdide KIRMIZI vermedi "
                           "-> negatif kontrol yok, iddia anlamsiz")
        # (iii) kisitla_kapali_scadler GEVSETME yonu: HER SEYI 'kisitla kapali' saymak
        # olu-uretec kontrolunu oldurur. Bu mutasyon O5'in gercek riskidir (O5 onarimi
        # Ç5'i gevsetirse tam boyle gorunur) -> KIRMIZI'nin KAYBOLDUGU gosterilir.
        n_kis = kapi_yukle(ad="k_gevsek_kisit")
        _tum = set(n_kis.scad_alt_kumesi(n_kis.paket_parmakizlari(paket_o5)))
        n_kis.kisitla_kapali_scadler = lambda *a, **k: set(_tum)
        if servis and servis.proc.poll() is None:
            acik_g, semalar_g, kisit_g = n_kis.duman_plani(sema_o5, secenekler_o5)
            g2 = n_kis.duman_kusurlari(servis.url, acik_g, semalar_g, kisit_g,
                                       zaman_asimi=20, manifest=kayit_o5b)
            if any("DENENMEMIS URETEC" in k and "olu.scad" in k for k in g2):
                d2_hata.append("kisitla_kapali_scadler HER SEYI kapali saydigi halde "
                               "'olu.scad' kirmizisi surdu -> O5'in Ç5'i koruma iddiasi "
                               "bu govdeye bagli DEGIL (olcum yanlis yere bakiyor)")
        else:
            d2_hata.append("(iii) OLCULEMEDI (servis ayakta degil)")
        # (iv) paket_parmakizlari uzanti suzgeci geri konursa (O2 gevsetmesi) eslem
        # drifti yeniden KACMALI -> O2 iddiasinin bu govdeye bagli oldugu kanitlanir.
        n_pk = kapi_yukle(ad="k_gevsek_kapsam")
        n_pk.paket_parmakizlari = lambda d: n_pk.scad_alt_kumesi(
            kapi.paket_parmakizlari(d))
        with open(eslem_yol, "w", encoding="utf-8") as f:
            f.write(eslem_ham.replace('"surum": 99', '"surum": 999'))
        if n_pk.parmakizi_farklari(
                {a: o for a, o in kapi.manifest_oku(kayit_o2).items()
                 if a.endswith(".scad")},
                n_pk.paket_parmakizlari(paket_o2)):
            d2_hata.append("uzanti suzgeci geri konuldugu halde eslem drifti HALA "
                           "yakalaniyor -> O2 iddiasi kapsam degisiminden gelmiyor")
        with open(eslem_yol, "w", encoding="utf-8") as f:
            f.write(eslem_ham)
        for h in d2_hata:
            kirmizi("(D2) YENI GOVDE NO-OP: " + h)
        if not d2_hata:
            ok("(D2) YENI GOVDELER LOAD-BEARING: alt_sinir · kapsam_beyani · "
               "kisitla_kapali · paket kapsami AYRI AYRI oldurulunce ilgili KIRMIZI "
               "KAYBOLDU (KACAN = 0)")

        # ---------------- (E) CI CAGRI SATIRI — GERCEK NOBETCIYE DELEGE
        # 🔴 IKINCI KOPYA ACILMADI: bu bolum kendi YAML/kabuk mantigini KURMAZ; kabloyu
        # olcen makine tools/is-akisi-kapisi.py BOLUM B'dir (gercek YAML ayristiricisi +
        # jeton/yardim/etkisizlestirme/tetikleyici nobetleri). Burada o makinenin
        # GOVDESI mutasyonlu YML metinleri uzerinde kosturulur; makine no-op yapilirsa
        # asagidaki 8 iddia birden duser.
        e_hata = []
        if not os.path.isfile(YML):
            e_hata.append("workflow dosyasi yok: %s" % YML)
        else:
            with open(YML, "r", encoding="utf-8") as f:
                yml_metin = f.read()
            if "\t" in yml_metin:
                e_hata.append("YML'de sekme (TAB) karakteri var — YAML'de yasak")
            isa = is_akisi_kapisi_yukle()
            if isa is None:
                e_hata.append("tools/is-akisi-kapisi.py MODUL olarak yuklenemedi -> "
                              "CI kablo nobeti OLCULEMEDI (fail-closed)")
            else:
                # Bu dosyanin KENDI cagrisi da dahil, uc kapi adiminin hepsi iddia
                # tablosunda olmali (curutme turu Ç1-f: nobetci kendi cagri satirini
                # korumuyordu).
                kimlikler = set(i.kimlik for i in isa.B_IDDIALAR)
                for gerekli in ("duman_kabul", "parmakizi-dizin", "parmakizi-url",
                                "duman-url"):
                    if gerekli not in kimlikler:
                        e_hata.append("IDDIA YOK: is-akisi-kapisi.py B_IDDIALAR'inda "
                                      "'%s' yok -> o cagri satiri NOBETSIZ" % gerekli)
                ilgili = [i for i in isa.B_IDDIALAR if i.kimlik != "iki-govde"]
                # TABAN: degismemis YML'de dordu de ETKILI olmali.
                for iddia in ilgili:
                    hata, n = isa.b_iddia_hatalari(yml_metin, iddia)
                    if hata or n < 1:
                        e_hata.append("TABAN: '%s' iddiasi degismemis YML'de etkili "
                                      "sayilmadi (%d cagri) -> %s"
                                      % (iddia.kimlik, n, hata))
                # 8 MUTASYON — curutme turunda 7'si SESSIZCE YESIL gecmisti.
                for ad, mutant in ci_mutantlar(yml_metin):
                    if mutant == yml_metin:
                        e_hata.append("MUTASYON BAYAT: %r hicbir sey degistirmedi "
                                      "(cagri bicimi degistiyse bu testi guncelle)" % ad)
                        continue
                    yakalandi = False
                    for iddia in ilgili:
                        hata, _ = isa.b_iddia_hatalari(mutant, iddia)
                        if hata:
                            yakalandi = True
                            break
                    if not yakalandi:
                        e_hata.append("MUTASYON KOR: %r uygulandigi halde BOLUM B "
                                      "hicbir iddiada KIRMIZI vermedi -> nobetci bu "
                                      "bicimde OLU (curutme turunun 7/8 deligi)" % ad)
        for h in e_hata:
            kirmizi("(E) CI KABLOSU: " + h)
        if not e_hata:
            ok("(E) CI KABLOSU: uc kapi adimi da is-akisi-kapisi.py BOLUM B iddiasiyla "
               "NOBETTE; %d etkisizlestirme mutasyonunun HEPSI KIRMIZI"
               % len(ci_mutantlar("")))

        # ---------------- (F) YANLIS-POZITIF (K-D listesi)
        f_hata = []
        f_sayac = 0

        def fp(etiket, kirmizi_mi, ayrinti=""):
            nonlocal f_sayac
            f_sayac += 1
            if kirmizi_mi:
                f_hata.append("%s -> KIRMIZI yandi %s" % (etiket, ayrinti))

        # F1: yeni aile eklendi (sema + .scad + ONIZLEME_AILELER, imaj yenilendi)
        # -> (C1) bolumunde zaten YESIL olctuk; burada sayaca girer.
        fp("F1 yeni aile eklendi (imaj yenilendi)", bool(c1_kusur), str(c1_kusur))
        # F2: .scad'de YALNIZ YORUM degisti ve paket YENIDEN YUKLENDI (kayit tazelendi).
        paket_f, sema_f, secenekler_f = fikstur_kur(os.path.join(kok, "f"))
        alfa_f = os.path.join(paket_f, "alfa.scad")
        with open(alfa_f, "a", encoding="utf-8") as f:
            f.write("// yalnizca aciklama satiri eklendi\n")
        kayit_f = kayit_yaz(kapi, kok, paket_f, "parmakizi-f.json")
        fp("F2 .scad'de yalniz yorum degisti (paket yeniden yuklendi)",
           bool(kapi.parmakizi_farklari(kapi.manifest_oku(kayit_f),
                                        kapi.paket_parmakizlari(paket_f))))
        # F3: semaya YENI OPSIYONEL parametre eklendi (imaj/eslem ESKI kalir).
        sema_f_yol = os.path.join(sema_f, "sentetik-aile-alfa.json")
        with open(sema_f_yol, "r", encoding="utf-8") as f:
            sema_f_veri = json.load(f)
        sema_f_veri["parametreler"].append(
            {"ad": "opsiyonel_yeni", "tip": "sayi", "min": 0, "max": 9, "adim": 1,
             "varsayilan": 0})
        with open(sema_f_yol, "w", encoding="utf-8") as f:
            json.dump(sema_f_veri, f, ensure_ascii=False)
        servis.kapat()
        servis = Servis(paket_f)
        if servis.hazir():
            f3_kusur = duman_kos(kapi, servis.url, sema_f, secenekler_f,
                                 manifest=kayit_f)
            fp("F3 semaya yeni OPSIYONEL parametre eklendi", bool(f3_kusur),
               str(f3_kusur))
        else:
            f_hata.append("F3 OLCULEMEDI (servis ayaga kalkmadi)")
        # F4: yml'e KAPI KOSTURMAYAN yeni bir adim eklendi.
        if os.path.isfile(YML) and isa is not None:
            with open(YML, "r", encoding="utf-8") as f:
                yml_metin = f.read()
            yeni_adim = yml_metin.replace(
                "      - uses: actions/checkout@v4",
                "      - uses: actions/checkout@v4\n"
                "      - name: Ilgisiz yeni adim\n        run: echo merhaba", 1)
            f4_kirmizi = any(isa.b_iddia_hatalari(yeni_adim, i)[0]
                             for i in isa.B_IDDIALAR if i.kimlik != "iki-govde")
            fp("F4 yml'e kapi kosturmayan yeni adim eklendi", f4_kirmizi)
            # F8: ilgisiz YAML yorumu.
            yorumlu = yml_metin.replace("jobs:", "# ilgisiz rutin yorum\njobs:", 1)
            f8_kirmizi = any(isa.b_iddia_hatalari(yorumlu, i)[0]
                             for i in isa.B_IDDIALAR if i.kimlik != "iki-govde")
            fp("F8 ilgisiz YAML yorumu eklendi", f8_kirmizi)
        # F5: ONIZLEME_KISITLAR'a kisit eklendi -> (O5) bolumunde YESIL olculdu.
        fp("F5 ONIZLEME_KISITLAR'a cift-uretecli aile kisiti eklendi", bool(o5_hata))
        # F6: paket dosyalari TERS SIRAYLA yazildi (ayni icerik) -> hash sira bagimsiz.
        paket_f6 = os.path.join(kok, "f6", "paket")
        os.makedirs(paket_f6, exist_ok=True)
        for ad in sorted(os.listdir(paket_f), reverse=True):
            shutil.copy(os.path.join(paket_f, ad), os.path.join(paket_f6, ad))
        fp("F6 paket dosyalari ters sirayla yazildi (ayni icerik)",
           bool(kapi.parmakizi_farklari(kapi.manifest_oku(kayit_f),
                                        kapi.paket_parmakizlari(paket_f6))))
        # F7: ilgisiz bir .md duzenlemesi (paket disinda).
        with open(os.path.join(kok, "ILGISIZ-NOT.md"), "w", encoding="utf-8") as f:
            f.write("# ilgisiz rutin duzenleme\n")
        fp("F7 ilgisiz .md duzenlemesi (paket disi)",
           bool(kapi.parmakizi_farklari(kapi.manifest_oku(kayit_f),
                                        kapi.paket_parmakizlari(paket_f))))
        for h in f_hata:
            kirmizi("(F) YANLIS-POZITIF: " + h)
        if not f_hata:
            ok("(F) YANLIS-POZITIF: %d mesru rutin senaryo denendi, KIRMIZI sayisi 0"
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
