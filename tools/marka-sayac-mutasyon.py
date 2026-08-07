#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA SAYAÇ KAPISI ÇÜRÜTME BATARYASI — kapı gerçekten yük taşıyor mu?

İKİ FAZ (kasıtlı ayrım):

  FAZ A — KOD MUTANTLARI (`tools/marka_model_build.py`). Her mutant uygulanır, kapı AYRI BİR
  SÜREÇTE koşturulur, kaynak geri alınır. Kabul: ÖLDÜRÜCÜLER kırmızı yakar, KONTROLLER yeşil
  kalır, düşen İDDİA İMZALARI ayrışır (ayrışmayan = 0), her mutantın KAYNAK İZİ (sha1)
  tabandan farklıdır — aynı uzunlukta mutasyon + bytecode önbelleği tuzağı burada KANITLANIR
  ([[mutasyon-bytecode-onbellegi]]).

  FAZ B — KAPI MUTANTLARI (`tools/marka-sayac-kapisi.py`). Bir iddiayı no-op'a çevirmek ya da
  sayacı sabitleyip iddia atlamak kapıyı KIRMIZI YAKMAZ (kod doğruyken kapı yine yeşildir) —
  bu yüzden "rc != 0" ölçütü kapı mutantları için ANLAMSIZDIR ve bir iddianın yük taşıdığını
  KANITLAMAZ ([[beyan-edilmis-survivor]]). Ölçüt buradaki gibi kurulur: kapı mutasyonu, o
  iddianın FAZ A'da yakaladığı EŞLİ KOD KUSURUYLA BİRLİKTE uygulanır ve
     · eşli kusur TABAN KAPIDA o imzayı düşürüyor olmalı (ön koşul, ölçülür),
     · mutant kapıda o imza ARTIK DÜŞMÜYOR olmalı (körlük kanıtı).
  Ayrıca rc 1 -> 0'a döndüyse "KOR=EVET" basılır: kapı o kusuru TAMAMEN göremez hale gelmiştir.
  Kapı mutantının KONTROLÜ tersidir: davranışsız değişiklikte imza DÜŞMEYE DEVAM etmelidir.

🔴 "SAYACI SABİTLE" TUZAĞI: `KAPI_SAYAC_SABIT` mutantı iddiayı atlarken `gecen`'i artırır —
IDDIA=n/taban satırı DEĞİŞMEZ. Bu yüzden batarya sayaca değil, DÜŞEN İMZAYA bakar; ölçüt
"IDDIA farklı mı" olsaydı bu mutant sağ kalırdı ([[mutasyon-kaniti-yeniden-uretilebilir]]).

Kullanım: python3 tools/marka-sayac-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(TOOLS, "marka_model_build.py")
KAPI = os.path.join(TOOLS, "marka-sayac-kapisi.py")


def _bir_marka_adi():
    """Marka-özel dal mutantı için MODEL BUTONU OLAN gerçek bir marka adı — bu dosyada SABİT
    marka adı tutulmaz (kapının MARKA_LITERAL iddiası bu dosyayı da tarıyor), katalogdan
    çalışma anında türetilir.

    🔴 NEDEN "BUTONU OLAN": butonsuz bir marka seçilseydi mutant HİÇBİR sayfayı düzeltmemiş
    olurdu ve imzası `ONCEKI_DAVRANIS` ile BİREBİR ÇAKIŞIRDI — iki mutant aynı imzayı
    düşürünce o eksen için ayırt edici kanıt kalmaz ([[beyan-edilmis-survivor]])."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, TOOLS)
    import json                            # noqa: PLC0415
    import marka_model_build as mm         # noqa: PLC0415
    kok = os.path.dirname(TOOLS)
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        products = json.load(f)
    with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
        index_html = f.read()
    veri = mm.gruplandir(products, mm.MarkaEvreni(index_html),
                         mm.cip_evreni_markalari(products, index_html))
    adaylar = sorted(ad for ad, d in veri.items()
                     if any(mm.yayimlanir_mi(g) for g in d["gruplar"].values()))
    if not adaylar:
        raise SystemExit("OLCULEMEDI: model butonu olan marka yok (mutant kurulamaz).")
    return adaylar[0]


# Marka sayfasının BÖLÜM AYRIMI çağrısı — birden çok mutantın ortak çapası.
_BOLUM_CAGRI = (
    '    diger, kalemler, sayilar = bolum_ayrimi(\n'
    '        [kucuk_urunler, d["marka_only"], d.get("ikincil", [])],\n'
    '        [g["urunler"] for g in buyuk_gruplar])\n'
    "    toplam = sayilar[\"toplam\"]")

# ONARIM ÖNCESİ DAVRANIŞ: üç kol yayımlanan kovadan ELENMEZ ("Diğer" tümleyen değildir),
# kova sayısı da toplam-kart farkından TÜRETİLİR. Jeneratörün ikiz kontrolü tripleMEZ
# (toplam değişmez) -> sapma SESSİZDİR; onu YALNIZ bölüm iddiaları görebilir.
_ESKI_DAVRANIS = (
    '        diger = _tekil(kucuk_urunler, d["marka_only"], d.get("ikincil", []))\n'
    '        kalemler = sayfa_kalemleri(diger, [g["urunler"] for g in buyuk_gruplar])\n'
    '        sayilar = {"toplam": len(kalemler), "kart": len(diger),\n'
    '                   "kova": len(kalemler) - len(diger),\n'
    '                   "kova_sayisi": len(buyuk_gruplar)}\n')


def _eski_davranis_mutanti(kosul):
    return (_BOLUM_CAGRI.rsplit("\n", 1)[0] + "\n"
            + ("    if %s:\n" % kosul)
            + _ESKI_DAVRANIS
            + "    toplam = sayilar[\"toplam\"]")


# (kimlik, öldürücü mü, eski_metin, yeni_metin)
MUTANTLAR = [
    # 1) Sayacı YİNE yalnız kartlara bağla (düzeltilen kusurun ta kendisi).
    ("SAYAC_YINE_KARTA", True,
     '(toplam === null ? "parça sayısı ölçülemedi" : (toplam + " parça")))',
     '(gorunenKart + " parça"))'),
    # 2) Kanonik toplam model kovalarını YOK SAYSIN (kart birimine düş).
    ("KOVA_TOPLAMI_YOK", True,
     "    return _tekil(kart_urunleri, *list(kova_listeleri))",
     "    return _tekil(kart_urunleri)"),
    # 3) Marka sayfasında kovaları hiç verme (jeneratör fail-closed mı?).
    ("MARKA_KOVA_SIFIR", True,
     _BOLUM_CAGRI,
     _BOLUM_CAGRI.replace('        [g["urunler"] for g in buyuk_gruplar])',
                          "        [])")),
    # 4) Kategori filtresini kovalara/kırılıma UYGULAMA (hep tam toplamı bas).
    ("KAPSAM_KIRILIMA_UYGULANMIYOR", True,
     "    return sayimla(ham, c);\n  }",
     "    return sayimla(ham, null);\n  }"),
    # 5) Tekilleştirmeyi NO-OP yap (mükerrer kart geri gelir).
    ("TEKIL_NOOP", True,
     "            if anahtar in gorulen:\n                continue\n            gorulen.add(anahtar)\n            out.append(p)",
     "            gorulen.add(anahtar)\n            out.append(p)"),
    # 6) Tekilleştirme SIRAYI BOZSUN (id'ye göre sırala).
    ("TEKIL_SIRA_BOZUK", True,
     "            out.append(p)\n    return out",
     '            out.append(p)\n    return sorted(out, key=lambda q: q.get("id") or "")'),
    # 7) İKİ SAYIYI AYRI KAYNAKTAN türet (kırılım kalemlerden değil kartlardan).
    ("IKI_SAYI_AYRI_KAYNAK", True,
     '            + _toplam_bloku(esc, kalemler, sayilar, "Bu markada", "model sayfalarında")',
     '            + _toplam_bloku(esc, diger, sayilar, "Bu markada", "model sayfalarında")'),
    # 8) FAIL-CLOSED'ı FAIL-OPEN'a çevir: kırılım okunamazsa kart sayısına düş (sessiz hata).
    ("TOPLAM_FAIL_OPEN", True,
     "    if(!el || el.length !== 1){ return null; }",
     "    if(!el || el.length !== 1){ return 0; }"),
    # 9) SINIF DEĞİL KATMAN onarımı: bölüm kimliğini YALNIZ >500 kalemli sayfalarda kur.
    #    Kapı yalnız büyük markalara bakıyorsa bu mutant SAĞ KALIR.
    ("ESIK_MARKA_BOLUM", True, _BOLUM_CAGRI, _eski_davranis_mutanti('sayilar["toplam"] <= 500')),
    # 10) SINIF DEĞİL VAKA onarımı (istemci): küçük sayfalarda yine kart sayısına düş.
    ("ESIK_MARKA_JS", True,
     "    if(toplam !== null && toplam < gorunenKart){ toplam = null; }",
     "    if(toplam !== null && toplam < gorunenKart){ toplam = null; }\n"
     "    if(gorunenKart < 120){ toplam = gorunenKart; }"),
    # 11) ONARIM ÖNCESİ DAVRANIŞ (tüm markalarda): bu koşum "ÖNCE" ölçümünün ta kendisidir —
    #     kapı kaç sayfada bölüm kimliğinin bozuk olduğunu KENDİ düzleminde basar.
    ("ONCEKI_DAVRANIS", True, _BOLUM_CAGRI, _eski_davranis_mutanti("True")),
    # 12) "Diğer"in tümleyen olmasını sağlayan ELEMEYİ geri al (kusurun kökü, :1722).
    ("ELEME_GERI_ALINDI", True,
     "    kart_urunleri = [p for p in _tekil(*kart_kollari) if p.get(\"id\") not in kova_ids]",
     "    kart_urunleri = _tekil(*kart_kollari)"),
    # 13) Model başlığında ∪kova yerine Σbuton bas (okuyucuyu toplamaya davet eden sayı).
    ("KOVA_SIGMA_BASILDI", True,
     '               + str(sayilar["kova"]) + \'</span> parça)</h2>\' if btns else "")',
     '               + str(sum(len(g["urunler"]) for g in buyuk_gruplar))\n'
     '               + \'</span> parça)</h2>\' if btns else "")'),
    # 14) Toplam CÜMLESİNİ ayrı kaynaktan türet (rozet doğru, cümle yanlış — sessiz ayrışma).
    ("CUMLE_AYRI_KAYNAK", True,
     '            + _toplam_bloku(esc, kalemler, sayilar, "Bu markada", "model sayfalarında")',
     '            + _toplam_bloku(esc, kalemler, dict(sayilar, kart=len(kucuk_urunler)),\n'
     '                            "Bu markada", "model sayfalarında")'),
    # 15) İstemcide "model sayfalarında" sayısını toplam olarak bas (bölüm kimliği istemcide).
    ("JS_KOVA_TOPLAM_BASILDI", True,
     '    yazSayim(dok, ".mm-sayim-kova", toplam === null ? "—" : (toplam - gorunenKart));',
     '    yazSayim(dok, ".mm-sayim-kova", toplam === null ? "—" : toplam);'),
    # --- KONTROL (yeşil kalmalı) ---
    ("KONTROL_JS_YORUM", False,
     "  function toplamla(dok, c){",
     "  // kontrol mutanti: davranissiz yorum\n  function toplamla(dok, c){"),
    ("KONTROL_ESDEGER_IFADE", False,
     "    return _tekil(kart_urunleri, *list(kova_listeleri))",
     "    return _tekil(kart_urunleri, *tuple(kova_listeleri))"),
    ("KONTROL_CSS_BOSLUK", False,
     "  .mm-toplam{margin:0 0 10px;font-size:14px;color:var(--gray-text)}",
     "  .mm-toplam{margin:0 0 10px; font-size:14px; color:var(--gray-text)}"),
]

# ---------------------------------------------------------------------- FAZ B: kapı mutantları
# (kimlik, öldürücü mü, eski, yeni, eşli KOD mutantı, o kusurun TABAN KAPIDA düşürdüğü imza)
KAPI_MUTANTLARI = [
    # (b) Bölüm kimliği iddiasını no-op yap.
    ("KAPI_KIMLIK_NOOP", True,
     '        kapi.iddia("BOLUM_KIMLIGI/" + yol, bolum + len(kova_idleri) == s["toplam"],',
     '        kapi.iddia("BOLUM_KIMLIGI/" + yol, True,',
     "ESIK_MARKA_BOLUM", "BOLUM_KIMLIGI"),
    # (d) Çakışma iddiasını ESKİ "kutsayan" haline döndür: çakışmayı kusur değil, doğru
    #     davranış say (kapının 7 Ağu'da ölçülen asıl körlüğü).
    ("KAPI_CAKISMA_KUTSAR", True,
     '    kapi.iddia("BIRIM_BOLUM/ayrik", olcum["kart_id"] == ["a", "b"],\n'
     '               "kart kolu kovadaki ürünü DÜŞÜRMEDİ: %r (hata=%s)"\n'
     '               % (olcum["kart_id"], olcum["hata"]))',
     '    kapi.iddia("BIRIM_BOLUM/ayrik",\n'
     '               len(mm.sayfa_kalemleri([a, b], [[a2, c]])) == 3,\n'
     '               "kart n kova cakismasi iki kez sayildi")',
     "ELEME_GERI_ALINDI", "BIRIM_BOLUM/ayrik"),
    # (f) Sayacı SABİTLE + iddia atla: IDDIA=n/taban satırı DEĞİŞMEZ, eksen sessizce gider.
    ("KAPI_SAYAC_SABIT", True,
     '    def iddia(self, kimlik, kosul, detay=""):\n        if kosul:',
     '    def iddia(self, kimlik, kosul, detay=""):\n'
     '        if kimlik.startswith("BOLUM_"):\n'
     "            self.gecen += 1\n"
     "            return\n"
     "        if kosul:",
     "KOVA_SIGMA_BASILDI", "BOLUM_KOVA"),
    # --- KONTROL (imza DÜŞMEYE DEVAM etmeli) ---
    ("KAPI_KONTROL_YORUM", False,
     "def _bolum_olc(mm, kart_kollari, kova_listeleri):",
     "# kontrol mutanti: davranissiz yorum\ndef _bolum_olc(mm, kart_kollari, kova_listeleri):",
     "ESIK_MARKA_BOLUM", "BOLUM_KIMLIGI"),
]


def kapi_kos():
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    shutil.rmtree(os.path.join(TOOLS, "__pycache__"), ignore_errors=True)
    cp = subprocess.run([sys.executable, "-B", KAPI], capture_output=True, text=True,
                        env=ortam, timeout=3600)
    cikti = cp.stdout + cp.stderr
    iz = (re.search(r"^IZ=(\S+)", cikti, re.M) or [None, "?"])[1]
    imzalar = (re.search(r"^IMZALAR=(.*)$", cikti, re.M) or [None, "?"])[1]
    iddia = (re.search(r"^IDDIA=(\S+)", cikti, re.M) or [None, "?"])[1]
    return cp.returncode, iz, imzalar, iddia


def _imza_kumesi(imzalar):
    """"A:3,B/x:1" -> {"A", "B/x"} (sayı DEĞİL kimlik karşılaştırılır)."""
    if not imzalar or imzalar in ("-", "?"):
        return set()
    return set(p.rsplit(":", 1)[0] for p in imzalar.split(",") if p)


def _yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def main():
    with open(HEDEF, "rb") as f:
        hedef_asil = f.read()
    with open(KAPI, "rb") as f:
        kapi_asil = f.read()
    metin = hedef_asil.decode("utf-8")
    kapi_metin = kapi_asil.decode("utf-8")

    # 16) MARKA-ÖZEL DAL: onarım tek bir markada çalışsın (sınıf değil vaka onarımı).
    #     Marka adı ÇALIŞMA ANINDA index.html evreninden alınır — bu dosyada sabit yok.
    MUTANTLAR.append(("MARKA_OZEL_DAL", True, _BOLUM_CAGRI,
                      _eski_davranis_mutanti('marka != "%s"' % _bir_marka_adi())))

    # ön kontrol: her mutantın eski metni HEDEF kaynağında TAM BİR KEZ geçmeli
    eksik = [k for k, _o, eski, _y in MUTANTLAR if metin.count(eski) != 1]
    eksik += [k for k, _o, eski, _y, _e, _i in KAPI_MUTANTLARI if kapi_metin.count(eski) != 1]
    if eksik:
        print("OLCULEMEDI: çapası bulunamayan/çoklu mutant: %s" % ", ".join(eksik))
        return 3
    kod_kimlikleri = {k for k, _o, _e, _y in MUTANTLAR}
    kayip_es = [k for k, _o, _e, _y, es, _i in KAPI_MUTANTLARI if es not in kod_kimlikleri]
    if kayip_es:
        print("OLCULEMEDI: eşli kod mutantı yok: %s" % ", ".join(kayip_es))
        return 3

    print("== TABAN ==")
    t_rc, t_iz, t_imza, t_iddia = kapi_kos()
    print("taban rc=%d IZ=%s IDDIA=%s IMZALAR=%s" % (t_rc, t_iz, t_iddia, t_imza))
    if t_rc != 0:
        print("OLCULEMEDI: taban YEŞİL değil, mutasyon ölçülemez.")
        return 3

    oldurucu_t = oldurucu_g = kontrol_t = kontrol_g = 0
    imzalar = {}
    kod_sonuc = {}
    try:
        print("== FAZ A: KOD MUTANTLARI (tools/marka_model_build.py) ==")
        for kimlik, oldurucu, eski, yeni in MUTANTLAR:
            _yaz(HEDEF, metin.replace(eski, yeni))
            rc, iz, imza, iddia = kapi_kos()
            kod_sonuc[kimlik] = {"rc": rc, "iz": iz, "imza": imza}
            uygulandi = iz != t_iz and iz != "?"
            if oldurucu:
                oldurucu_t += 1
                oldurucu_g += 1 if ((rc != 0) and uygulandi) else 0
                imzalar.setdefault(imza, []).append(kimlik)
            else:
                kontrol_t += 1
                kontrol_g += 1 if (rc == 0 and uygulandi) else 0
            print("  %-28s %-9s rc=%d uygulandi=%s IDDIA=%s IMZALAR=%s"
                  % (kimlik, "ÖLDÜRÜCÜ" if oldurucu else "KONTROL", rc,
                     "EVET" if uygulandi else "HAYIR", iddia, imza[:110]))
        _yaz(HEDEF, metin)

        print("== FAZ B: KAPI MUTANTLARI (tools/marka-sayac-kapisi.py + eşli kod kusuru) ==")
        for kimlik, oldurucu, eski, yeni, es, bek_imza in KAPI_MUTANTLARI:
            es_mut = next(m for m in MUTANTLAR if m[0] == es)
            es_sonuc = kod_sonuc[es]
            oncekosul = bek_imza in _imza_kumesi(es_sonuc["imza"])
            _yaz(HEDEF, metin.replace(es_mut[2], es_mut[3]))
            _yaz(KAPI, kapi_metin.replace(eski, yeni))
            rc, iz, imza, iddia = kapi_kos()
            _yaz(KAPI, kapi_metin)
            _yaz(HEDEF, metin)
            uygulandi = iz != es_sonuc["iz"] and iz != "?"
            kaldi = bek_imza in _imza_kumesi(imza)
            kor = (rc == 0)
            if oldurucu:
                oldurucu_t += 1
                oldu = oncekosul and uygulandi and not kaldi
                oldurucu_g += 1 if oldu else 0
                # Kapı mutantının imzası: hangi eksen KÖRLEŞTİ (kod imzalarıyla karışmasın).
                imzalar.setdefault("KOR:" + bek_imza + "@" + es, []).append(kimlik)
            else:
                kontrol_t += 1
                kontrol_g += 1 if (oncekosul and uygulandi and kaldi) else 0
            print("  %-28s %-9s es=%-18s onkosul=%s uygulandi=%s imza_kaldi=%s KOR=%s "
                  "rc=%d IDDIA=%s"
                  % (kimlik, "ÖLDÜRÜCÜ" if oldurucu else "KONTROL", es,
                     "EVET" if oncekosul else "HAYIR", "EVET" if uygulandi else "HAYIR",
                     "EVET" if kaldi else "HAYIR", "EVET" if kor else "HAYIR", rc, iddia))
    finally:
        with open(HEDEF, "wb") as f:
            f.write(hedef_asil)
        with open(KAPI, "wb") as f:
            f.write(kapi_asil)
        shutil.rmtree(os.path.join(TOOLS, "__pycache__"), ignore_errors=True)

    ayrismayan = sum(len(v) for v in imzalar.values() if len(v) > 1)
    print("\n== HUKUM ==")
    for imza, ks in sorted(imzalar.items()):
        if len(ks) > 1:
            print("  AYRISMAYAN: %s -> %s" % (", ".join(ks), imza[:120]))
    print("OLDURUCU=%d/%d  KONTROL=%d/%d  AYRISMAYAN=%d  TABAN_IDDIA=%s"
          % (oldurucu_g, oldurucu_t, kontrol_g, kontrol_t, ayrismayan, t_iddia))
    tamam = (oldurucu_g == oldurucu_t and kontrol_g == kontrol_t and ayrismayan == 0)
    print("HUKUM=" + ("YESIL" if tamam else "KIRMIZI"))
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())
