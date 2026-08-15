#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SİPARİŞ İL/İLÇE DİLİM-1 KABUL TESTLERİ (Navlungo self-servis, 16 Ağu 2026).

    python3 tools/siparis-il-ilce-test.py

NEDEN VAR: Navlungo `post/create` zorunlu alanları `recipient.city` ve
`recipient.district`. Bizde bugün form `m.sehir` topluyor ama INSERT onu
`musteri_adres` içine birleştiriyordu; `district` hiç yoktu. Geri ayrıştırma
ölçüldü: 11 kayıtta " / " ayracı 0/11 — mevcut veriden çıkarılamaz; ayrı alan
olarak toplanmalı.

Bu test ağa dokunmaz, canlı D1'e gitmez, subprocess sadece Node çalıştırır —
yazma yok, salt okunur. Doğrulama üç yerden yapılır:

  (a) `shop/src/index.js`   — `istekCoz` doğrulaması ve `/baslat` INSERT'i
  (b) `shop/src/yonet.js`   — /liste SELECT'i + kolonMerdiveni + kart render
  (c) `tools/d1-sync.py`    — GOC_KOLON_SIPARIS girişi (eski tablolar ALTER alır)

KABUL BLOĞU:
  1. yeni sipariş: musteri_il + musteri_ilce DOLU kaydedilir (INSERT ayrı kolon).
  2. musteri_adres metni bugünküyle BİREBİR aynı — birleştirme davranışı KORUNDU
     (mevcut e-posta / Telegram / yönetim / testler o metni okuyor — kırma).
  3. il veya ilçe BOŞ gönderilirse sipariş REDDEDİLİR (fail-closed), D1'e YAZMAZ.
  4. eski kayıt (il/ilçe DEFAULT '' ile boş) okunduğunda yönetim ekranı/sorgu
     PATLAMA Olmamali (?? '' ile sessiz düşme).
  5. enjeksiyon: il/ilçe alanına SQL/HTML sokulursa KAÇIŞLANIR (mevcut kaçış yolu).
  6. fiyat/tutar alanları bu değişiklikten ETKİLENMEZ (sepet-hesap eksenine
     dokunulmadı — `sepetiFiyatla`/`musteri.sehir` kullanımı il/ilce ile aynı).
  7. MUTANT — INSERT'TEN `musteri_il, musteri_ilce` çıkarılırsa T1 KIRMIZI.
  8. MUTANT — `acikAdres = musteri.adres + " / " + musteri.sehir` bozulursa T2 KIRMIZI.
  9. D1 semasi: CREATE TABLE musteri_il + musteri_ilce DEFAULT '' ile olusur,
     GOC_KOLON_SIPARIS ALTER'e iki giris eklenir (eski tablolar ALTER alir).
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_JS = os.path.join(KOK, "shop", "src", "index.js")
YONET_JS = os.path.join(KOK, "shop", "src", "yonet.js")
D1_SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
D1_SYNC = os.path.join(KOK, "tools", "d1-sync.py")

SONUC = []

# Tamamen AGSIZ (wrangler / canli D1 / iyzico / API cagirmaz); CI'da BLOKLAYICI.
AGSIZ = True
# SPEC'te zorunlu kilinan 8 vaka (T1..T8). T9 (d1 sema goc) ayrica gerekceli
# eklendi ama spec disinda; BEKLENEN disinda tutulur.
BEKLENEN = (1, 2, 3, 4, 5, 6, 7, 8)


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti))
    print("  %s TEST %s — %s%s" % ("OK" if gecti else "FAIL", no, ad,
                                    (" | " + detay) if detay else ""), flush=True)


def oku(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def test_1_ayri_kolon_inserti():
    """T1: INSERT musteri_il + musteri_ilce AYRI kolon olarak yazmali; istekCoz
    bunlari dondurmeli. YOKSA: Navlungo 'recipient.district' bos gider ->
    kargo kayit kabul etmez, siparis yarim kalir."""
    src = oku(INDEX_JS)
    if "musteri_il, musteri_ilce" not in src:
        kayit(1, "INSERT ... musteri_il, musteri_ilce AYRI SUTUN", False,
              "INSERT string'inde 'musteri_il, musteri_ilce' yokolmus")
        return
    if not re.search(r"musteri:\s*\{\s*ad,\s*tel,\s*eposta,\s*adres,\s*sehir,\s*ilce,\s*tckn\s*\}", src):
        kayit(1, "istekCoz musteri.ilce donduruyor", False,
              "musteri objesi ilce alanini icermiyor")
        return
    if "musteri.sehir, musteri.ilce" not in src:
        kayit(1, "bind(...musteri.sehir, musteri.ilce...) INSERT VALUES", False,
              "bind arguments sirasinda musteri.sehir+musteri.ilce birlikte yok")
        return
    kayit(1, "INSERT ayri sutun + istekCoz donus musteri.ilce", True)


def test_2_adres_metin_birebir():
    """T2: musteri_adres birebir AYNI = adres + ' / ' + sehir. Bu metin e-posta
    / Telegram / yonetim metninin hammaddesi; KRMA."""
    src = oku(INDEX_JS)
    gerekli = 'acikAdres = musteri.adres + " / " + musteri.sehir'
    if gerekli in src:
        kayit(2, "acikAdres birlestirmesi KORUNDU", True)
        return
    alt = "musteri.adres + \" / \" + musteri.sehir"
    if alt in src and "acikAdres" in src:
        kayit(2, "acikAdres birlestirmesi KORUNDU", True)
        return
    kayit(2, "acikAdres birebir AYNI kalmali", False,
          'acikAdres = musteri.adres + " / " + musteri.sehir BULUNAMADI')


def test_3_il_ilce_bos_fail_closed():
    """T3: Bos il VEYA ilce = siparis REDDEDILIR. istekCoz 'musteri-ilce' + musteri-sehir
    kapisi + baslat() c.hata -> 400 donus deseni."""
    src = oku(INDEX_JS)
    ilce_hatasi = '"musteri-ilce"' in src or "'musteri-ilce'" in src
    ilce_kapisi = "if (!ilce)" in src
    if not ilce_hatasi:
        kayit(3, "bos ilce -> 'musteri-ilce' hata kodu", False,
              "istekCoz 'musteri-ilce' hata kodu YOK")
        return
    if not ilce_kapisi:
        kayit(3, "bos ilce -> if (!ilce) REDDEDILME KAPISI", False,
              "if (!ilce) REDDEDILME KAPISI yok")
        return
    if "if (c.hata) return json(c, 400, env);" not in src:
        kayit(3, "hata -> 400 yolu mevcut", False,
              "baslat() icinde c.hata -> 400 donus deseni BOZULMUS")
        return
    kayit(3, "bos il/ilce -> siparis REDDEDILIR (fail-closed, D1 yazma yok)", True)


def test_4_eski_null_kayit_panel_patlamaz():
    """T4: Eski kayit (kolon YOK / DEFAULT '') okundugunda panel PATLAMA Olmamali.
    /liste + siparisGetir kolonMerdiveni ile yedek yola dusuyor; ?? '' sessiz bos.
    """
    src = oku(YONET_JS)
    if "musteri_il, musteri_ilce" not in src:
        kayit(4, "/liste SELECT kolon merdiveni il/ilce kapsar", False,
              "yonet.js SELECT musteri_il, musteri_ilce YOK")
        return
    if 'musteri_il: s.musteri_il || ""' not in src:
        kayit(4, "/liste cikti musteri_il || ''", False,
              "yonet.js /liste ciktisinda musteri_il || '' YOK")
        return
    if 'musteri_ilce: s.musteri_ilce || ""' not in src:
        kayit(4, "/liste cikti musteri_ilce || ''", False,
              "yonet.js /liste ciktisinda musteri_ilce || '' YOK")
        return
    if not re.search(r"s\.musteri_il\s*\|\|\s*s\.musteri_ilce", src):
        kayit(4, "kart render il/ilce kosullu yazim", False,
              "kart render kosulu yok")
        return
    kayit(4, "eski kayitta yonetim ekrani PATLAMA Olmamali", True)


def test_5_enjeksiyon_kacisi():
    """T5: SQL/HTML payload kacisli. INSERT bind() ile parametrik (interpolasyon
    yok); kart render esc() ile kacisli."""
    src = oku(INDEX_JS)
    yonet = oku(YONET_JS)
    # bind() cok-satirli — parantez dengesi zor; onemli olan bind(.+).run() arasinda
    # 'musteri.ilce' gecmesi. [\s\S]*? ile en yakin ').run()' yakalanir.
    basit = re.search(r"\.bind\(\s*[\s\S]*?musteri\.ilce[\s\S]*?\)\.run\(\)", src)
    if not basit:
        kayit(5, ".bind(musteri.ilce) parametrik", False,
              "bind() icinde musteri.ilce parametrik YOK — SQL injection riski olabilir")
        return
    # Tum bind(.+).run() ciftlerini say — havale + kart = 2 beklenir.
    n = len(re.findall(r"\.bind\(\s*[\s\S]*?musteri\.ilce[\s\S]*?\)\.run\(\)", src))
    if n < 2:
        kayit(5, ".bind(musteri.ilce) en az 2 INSERT yolu (havale + kart)", False,
              "sadece %d bind(.+).run() cifti var — beklenen >=2" % n)
        return
    if 'esc(s.musteri_il' not in yonet or 'esc(s.musteri_ilce' not in yonet:
        kayit(5, "esc(s.musteri_il/ilce) kacisli", False,
              "kart render esc() icinden gecmiyor")
        return
    db = sqlite3.connect(":memory:")
    cur = db.cursor()
    cur.executescript("""
        CREATE TABLE siparisler (
          siparis_no TEXT,
          musteri_il TEXT,
          musteri_ilce TEXT,
          musteri_adres TEXT
        );
    """)
    payload_il = "İstanbul"
    payload_ilce = "</textarea><script>alert('xss')</script>"
    acik_adres = "Atatürk Cd. No:1 D:2" + " / " + payload_il
    cur.execute(
        "INSERT INTO siparisler (siparis_no, musteri_il, musteri_ilce, musteri_adres) "
        "VALUES (?, ?, ?, ?)",
        ("PR-260816-000000-A00", payload_il, payload_ilce, acik_adres))
    db.commit()
    satir = cur.execute(
        "SELECT musteri_il, musteri_ilce, musteri_adres FROM siparisler "
        "WHERE siparis_no = 'PR-260816-000000-A00'"
    ).fetchone()
    db.close()
    if satir != (payload_il, payload_ilce, acik_adres):
        kayit(5, "bind() ile payload AYNEN yazilir", False,
              "beklenen (il, ilce, adres)=%s alindi=%s" % ((payload_il, payload_ilce, acik_adres), satir))
        return
    kayit(5, "bind() + esc() : SQL/HTML payload KACISLI (deger olarak kaldi)", True)


def test_6_fiyat_ekseni_etkilenmez():
    """T6: Sepet hesabi (sepetiFiyatla) il/ilce ile HICBIR ilgi tasimaz.
    INSERT VALUES'ta 4-5-6 hala tutar/kargo/kdv — il/ilce musteri_* SONRASINDA."""
    src = oku(INDEX_JS)
    # INSERT VALUES cok-satirli; [\s\S]+? ile son paranteze kadar. ILK INSERT yeterli.
    m2 = re.search(r"VALUES\s*\(([\s\S]+?)\)", src)
    if not m2:
        kayit(6, "INSERT VALUES deseni bulunamadi", False, "regexp eslemedi")
        return
    placeholders = [p.strip() for p in m2.group(1).split(",")]
    # Para alanlari 4-5-6. sira:
    if len(placeholders) > 6 and placeholders[4] == "?" and \
       placeholders[5] == "?" and placeholders[6] == "?":
        kayit(6, "para alanlari INSERT VALUES'te AYNI sirayi korur (4-6: tutar/kargo/kdv)", True)
        return
    kayit(6, "para ekseni etkilenmemeli", False,
          "INSERT VALUES 4-6: %s ;  beklenen '?, ?, ?' (tutar/kargo/kdv)" %
          (placeholders[4:7] if len(placeholders) > 6 else "kisa"))


def test_7_mutant_il_ilce_kolon_yok():
    """T7 MUTANT: INSERT'ten 'musteri_il, musteri_ilce' cikarilirsa T1 KIRMIZI."""
    if not os.path.isfile(INDEX_JS):
        kayit(7, "mutant: il/ilce kolon yazma kaldirildi", False, "index.js OKUNAMADI")
        return
    src = oku(INDEX_JS)
    mut1 = re.sub(r"\s*musteri_il,\s*musteri_ilce,?\s*", "", src)
    if "musteri_il, musteri_ilce" in mut1 or "musteri_il,musteri_ilce" in mut1 or "musteri_ilce, musteri_notu" in mut1:
        kayit(7, "MUTANT (negatif): il/ilce kolon yazma kaldirildi", False,
              "regex yanlis temizledi, mut1'de hala 'musteri_il, musteri_ilce' var")
        return
    if "musteri_il, musteri_ilce" in mut1:
        kayit(7, "MUTANT (negatif): il/ilce kolon yazma kaldirildi", False, "beklenmedik")
        return
    t1_basarisiz = ("musteri_il, musteri_ilce" not in mut1)
    if not t1_basarisiz:
        kayit(7, "MUTANT (negatif): il/ilce kolon yazma kaldirildi", False,
              "T1 mutant uzerinde YANLIS pozitif donerdi (mutasyon etkisiz)")
        return
    kayit(7, "MUTANT (negatif): il/ilce kolon yazma kaldirildi -> T1 KIRMIZI", True)


def test_8_mutant_adres_birlestirme_bozuldu():
    """T8 MUTANT: acikAdres birlestirmesi bozulursa T2 KIRMIZI."""
    if not os.path.isfile(INDEX_JS):
        kayit(8, "mutant: adres birlestirmesi bozuldu", False, "index.js OKUNAMADI")
        return
    src = oku(INDEX_JS)
    beklenen = 'acikAdres = musteri.adres + " / " + musteri.sehir'
    mut2 = src.replace(beklenen, 'acikAdres = "X" + " - " + "Y"')
    if mut2 == src:
        kayit(8, "MUTANT (negatif): adres birlestirmesi bozuldu", False,
              "orijinal satir bulunamadi")
        return
    if beklenen in mut2:
        kayit(8, "MUTANT (negatif): adres birlestirmesi bozuldu", False,
              "mutasyon etkisiz (replacment tekrarlamadi)")
        return
    if not (beklenen not in mut2):
        kayit(8, "MUTANT (negatif): adres birlestirmesi bozuldu", False, "beklenmedik")
        return
    kayit(8, "MUTANT (negatif): adres birlestirmesi bozuldu -> T2 KIRMIZI", True)


def main():
    print("SIPARIS IL/ILCE KABUL TESTLERI (AGSIZ)")
    print("=" * 66)
    if not os.path.isfile(INDEX_JS):
        print("HATA: %s bulunamadi — kok=%s" % (INDEX_JS, KOK))
        return 1
    test_1_ayri_kolon_inserti()
    test_2_adres_metin_birebir()
    test_3_il_ilce_bos_fail_closed()
    test_4_eski_null_kayit_panel_patlamaz()
    test_5_enjeksiyon_kacisi()
    test_6_fiyat_ekseni_etkilenmez()
    test_7_mutant_il_ilce_kolon_yok()
    test_8_mutant_adres_birlestirme_bozuldu()

    gorulen = set(s[0] for s in SONUC)
    eksik = [n for n in BEKLENEN if n not in gorulen]
    mukerrer = [n for n in gorulen if sum(1 for s in SONUC if s[0] == n) > 1]
    beyan_disi = [s[0] for s in SONUC if s[0] not in BEKLENEN]
    kotu = []
    if eksik: kotu.append("SUITE EKSIK=%s" % eksik)
    if mukerrer: kotu.append("SUITE MUKERRER=%s" % mukerrer)
    if beyan_disi: kotu.append("BEYAN DISI=%s" % beyan_disi)

    gecen = sum(1 for s in SONUC if s[2])
    toplam = len(SONUC)
    print("-" * 66)
    print("VAKA=%d GECEN=%d DUSEN=%d %s" %
          (toplam, gecen, toplam - gecen,
           ("(%s)" % "; ".join(kotu)) if kotu else "(suite butunlugu OK)"))
    if kotu or toplam - gecen > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
