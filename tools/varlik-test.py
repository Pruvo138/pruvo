#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VARLIK KAPISI — tekrar eden CSS/JS'in icerik-adresli same-origin dosyaya tasinmasi.

NEDEN VAR (olculdu, 2 Agu 2026): urun sayfasinin ~%86'si her sayfada BIREBIR ayni
bayttı; gomulu CSS+JS sayfanin ucte ikisiydi. 16.874 urunde toplam yayin ~1,03 GB ve
GitHub Pages siniri ~1 GB. Bloklar /varlik/<ad>-<sha256-ilk10>.<uz> dosyalarina tasindi.
Bu tasimanin IKI hata sinifi SESSIZDIR ve ikisi de bu depoda YASANDI:
  (1) ONBELLEK: ayni adin ustune yazmak -> tarayici BAYAT CSS/JS servis eder
      ([[r2-sessiz-uzerine-yazma]], [[gorsel-anahtar-cakismasi]]). Ad icerikten TUREMELI.
  (2) IKIZ TANIM: satir-ici "kritik cekirdek" ile harici dosyanin AYRI metinler olmasi
      -> sessizce ayrisirlar ([[ikiz-tanim-sessiz-ayrisma]]). Cekirdek kaynagin DILIMI
      olmali, ikinci kopya DEGIL.
Ucuncu sinif: kirik referans (sayfadaki ad ile dosyanin adi ayrisirsa sayfa CIPLAK kalir)
ve sessiz kayip (harici dosyaya blogun bir kismi yazilmaz).

KABUL EKSENLERI (spec 4. bolum):
  1  ESKI uretici ile YENI uretici ciktisi arasinda CIKARIM KAYBI YOK: JSON-LD yapraklari,
     title/meta/canonical, gorunur metin, gorsel URL'leri ve baglanti hedefleri (yol +
     sorgu parametre DEGERLERI) kaybolmamis ve DEGISMEMIS. Bir baglantiya YENI parametre
     EKLENMESI serbesttir (tek serbestlik). Gerekce ve mutasyon kaniti -> cikarim_kaybi().
  1b Urune ozel VERI (URUN / URUN_SEMA / URUN_KONFIGUR) eski ile bayt-esit.
  2  Harici dosyaya cikan CSS + JS icerigi eski gomulu icerikle esit (kayip/eklenti yok).
  3  Sayfa sayisi degismedi; her sayfa hala uretiliyor (ornek uzerinde sayiyla).
  4  Yeni ortalama sayfa bayti OLCULDU ve eskisinden DUSUK.
  5  Yeni toplam yayin tahmini (ortalama x katalog + varlik dosyalari) OLCULDU ve dusuk.
  6  Icerik degismezse uretilen dosya ADI AYNI kalir (gereksiz cache-miss yok).
  7  Icerik BIR BAYT degisirse dosya adi DEGISIR (bayat varlik servis edilemez).
  8  Sayfadaki referans ile diskteki dosyanin adi BIREBIR ayni + ad dosyanin
     BAYTLARINDAN yeniden turetilebiliyor (kirik referans = ciplak sayfa).
  9  IKIZ YOK: satir-ici cekirdek + harici kalan = KAYNAGIN TA KENDISI; cekirdek
     bolgesini bozan bir mutant satir-ici ciktiyi da DEGISTIRIR.
 10  FAIL-CLOSED: varlik uretilemezse (bos govde / sinir isareti yok / yazilamayan
     dizin) build DURUR; sessizce ciplak sayfa URETMEZ.

ESKI URETICI NEREDEN GELIR: git gecmisinde `varlik_adres`i ICERMEYEN en son
tools/build.py. Boylece kiyas kendi kendini dogrulamaz ([[anahat-referans-tautolojisi]]).
Depo SIG (shallow) ise eksen 1/1b/2 OLCULEMEDI olur ve kapi rc 2 ile DURDURUR — yesile
donmez (deploy.yml `fetch-depth: 0` zorunlu on-kosuldur).

Kullanim:
    python3 tools/varlik-test.py
    python3 tools/varlik-test.py --ornek 12
"""
import hashlib
import inspect
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import build                                                             # noqa: E402
import yorum_soy                                                         # noqa: E402

HATALAR = []
BILGI = []
OLCULEMEDI = []


def bekle(kosul, mesaj):
    if not kosul:
        HATALAR.append(mesaj)
    return bool(kosul)


# --------------------------------------------------------------------- yardimcilar
_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
_SCRIPT_RE = re.compile(r"<script([^>]*)>(.*?)</script>", re.S)
_SCRIPT_SRC_RE = re.compile(r"<script[^>]*\ssrc=\"([^\"]+)\"[^>]*>\s*</script>")
_CSS_LINK_RE = re.compile(r"<link rel=\"stylesheet\" href=\"([^\"]+)\">")
_URUN_VERI_RE = re.compile(r"^var (URUN|URUN_SEMA|URUN_KONFIGUR|URUN_KART_SECIM) = (.*);$", re.M)


def _js_mi(oznitelikler):
    return yorum_soy._script_turu_js_mi(oznitelikler)


# --------------------------------------------------------- eksen 2: BILEREK degisen satirlar
# Eksen 2'nin IDDIASI: "varliga tasima sirasinda icerik KAYBOLMADI/EKLENMEDI".
# Kiyas nesnesi git gecmisindeki ESKI uretici oldugu icin, o commit'ten BU YANA yapilan
# HER MESRU icerik degisikligi de bu eksende kayip/eklenti gibi gorunur. Ikisi ayni sey
# DEGILDIR ve karistirilirsa eksen 2 "sayfa JS'i bir daha asla degismesin" kuralina doner.
# Bu yuzden BILEREK degisen satirlar BURADA, GEREKCESIYLE ve DAR desenle listelenir.
# 🔴 DAR TUTULACAK: her giris tek bir olayi anlatir; genel desen (ornegin butun `de(...)`
# cagrilari) YAZILMAZ — o, gercek bir icerik kaybini da maskelerdi.
BILEREK_DEGISEN = (
    # KART_SECIM: sabit deger yerine sayfadaki veriden okunur oldu.
    ("var KART_SECIM =", "kart secim verisi sabitten sayfa verisine tasindi"),
    ("var URUN_KART_SECIM =", "kart secim verisi sabitten sayfa verisine tasindi"),
    # 2026-08-03: uretilemez secenekte basilan MUSTERI METNI duzeltildi. Eski metin
    # "siparis verebilirsiniz, uretim etkilenmez" diyordu; o bolge OLCULDU ve uretim
    # ucunda karsiligi YOK (satis kapisi da ayni gun kapatildi). Bu bir ICERIK
    # duzeltmesidir, varliga tasima kaybi DEGIL. Iki cagri yeri de ayni cumleyi tasir.
    ("Bu seçenekle 3D önizleme şimdilik sunulamıyor",
     "uretilemez secenek metni duzeltildi — ESKI cumle (kiyas commit'inde)"),
    ("Bu seçenek üretim hattımızda henüz karşılanmıyor",
     "uretilemez secenek metni duzeltildi — YENI cumle"),
    # 2026-08-11: GA4 urun goruntuleme olayi. Bu satirin KUYRUGU her urunde FARKLIDIR
    # (govde o urunun kimligi/basligi/kategorisi/fiyatiyla basilir), bu yuzden TAM SATIR
    # olarak beyan EDILEMEZ; desen cagri ONEKIDIR ve AYIRT EDICIDIR (sayfada baska hicbir
    # satir bu oneki tasimaz). Ayni olayin 13 sabit satiri BILEREK_DEGISEN_TAM'dadir.
    # 🔴 IDDIA TASINDI: olayin FIILEN atesledigi + kalem kimliginin katalog kimligiyle
    # ayni oldugu tools/ga4-olay-kapisi.py (c) bolumunde node:vm ile olculur.
    ('window.pruvoGA4Track("view_item", ',
     "YENI: urun sayfasi GA4 view_item cagrisi (govde urun basina degisir)"),
    # 2026-08-11 — ONERILEN MALZEME ON-SECIMI + BILINCLI SECIM NOTU (Okan karari).
    # Sunucu yalniz VERIYI attribute olarak basar (data-oneri / data-kurus); METNI sayfa
    # JS'i yazar. Neden: metinler URUN BASINA degisir ve urun-basi gorunur metni sabit
    # dizeyle beyan etmek imkansizdir — sabit JS satiri beyan edilebilir, degisken metin
    # DEGIL. Dort satir da AYIRT EDICIDIR (sayfada baska hicbir satir bu onekleri tasimaz).
    # 🔴 IDDIA TASINDI: notun kosula bagli gorunurlugu + cip tutarlarinin tek turetme
    # noktasindan gelmesi tools/d1-fiyat-parite-kapisi.py E7/E9'da fail-closed olculur;
    # mutasyon kaniti tools/urun-vitrin-kapsam-mutasyon.py :: M8/M10/M11.
    ('var oneriNot = document.getElementById("oneriNot");',
     "YENI: bilincli-secim notu referansi"),
    ('oneriNot.textContent = "Seçtiğiniz malzeme,',
     "YENI: not METNI istemcide yazilir (sunucu yalniz data-oneri basar)"),
    ('oneriNot.hidden = !(_o && seciliMalzeme && seciliMalzeme !== _o);',
     "YENI: not YALNIZ onerilenden sapinca gorunur (yanlis-pozitif gurultu yok)"),
    ('cipler.querySelectorAll(".fil-cip[data-kurus]")',
     "YENI: her malzeme cipinin KENDI tutari gorunur etiketle yazilir "
     "(taban secenegin tutari sayfada okunur kalir)"),
    # 2026-08-20 — SATIN ALMA SERIDI (P2, ArTisT olcumu): dar ekranda fiyat + "Sepete Ekle"
    # ilk 812 px icinde tutulur. Dokuz satirin HEPSI YENIDIR (kiyas commit'inde yok) ve
    # her biri AYIRT EDICIDIR — `serit*` onekli hicbir dize eski sayfada gecmez.
    # 🔴 IDDIA TASINDI: seridin varligi/teklıgi, fiyat+CTA tasidigi, IKINCI bir sepet
    # mantigi DOGURMADIGI (delegasyon) ve sunucudan BOS fiyat geldigi
    # tools/ilk-ekran-kapisi.py A1/A6/A7'de fail-closed olculur; mutasyon kaniti ayni
    # dosyadaki `--kendini-test` (7 oldurucu; "serit SILINDI" ve "serit IKIZLENDI"
    # dogrudan bu satirlari hedefler).
    ('var serit=document.getElementById("satinSerit")',
     "YENI: satin alma seridi dugumleri (nobetci: ilk-ekran-kapisi.py A1)"),
    ('var seritLabel=seritSepet?',
     "YENI: serit etiketi + fiyat AYNA KAYNAGI (#opsiyonFiyat ya da .price)"),
    ('if(seritFiyat && fiyatKaynak)',
     "YENI: serit fiyati sayfanin kendi fiyat dugumunden AYNALANIR — ikinci hesap YOK "
     "(nobetci: ilk-ekran-kapisi.py A7)"),
    ('if(seritSepet){ var sD = has ?',
     "YENI: serit butonunun sepette/degil durumu #cartBtn ile AYNI kaynaktan"),
    ('seritSepet.classList.toggle("added", has)',
     "YENI: serit butonu gorunumu #cartBtn durumundan birebir kopyalanir"),
    ('seritSepet.setAttribute("aria-label", sD)',
     "YENI: ekran okuyucu metni gorunur metinle SENKRON (etiketli kalip kurali)"),
    ('if(seritLabel){ seritLabel.textContent',
     "YENI: serit etiketi 'Sepette ✓' / 'Sepete Ekle' — govde metniyle ayni sozluk"),
    ('if(serit && seritSepet){ seritSepet.addEventListener',
     "YENI: serit butonu #cartBtn'e DELEGE eder — secim kilidi/konfigurator gecerliligi "
     "TEK kod yolundan gecer (nobetci: ilk-ekran-kapisi.py A7)"),
    ('serit.hidden = false; serit.removeAttribute("hidden");',
     "YENI: serit ANCAK delegasyon kurulduysa acilir + `serit-var` govde sinifi "
     "(fail-closed: calismayan bir CTA gosterilmez)"),
)

# TAM SATIR eslesmeli girisler. NEDEN AYRI: yukaridaki liste ALT DIZE arar; ayirt edici
# alt dizesi OLMAYAN satirlar (ornegin yalnizca kapanis suslu parantezden olusan `}}}`)
# alt dize olarak yazilirsa o dizeyi ICEREN her satiri — yani gercek bir icerik kaybini
# da — maskelerdi. Tam satir eslesmesi mumkun olan EN DAR bicimdir.
# 2026-08-03 (45f30fd7): onizleme kisit YARGISI satir-ici dongudan cikarilip
# secenekler.js `onizlemeKisitIhlali()` TEK KAYNAGINA tasindi (ayni fonksiyonu Worker
# sema kapisi da cagirir). Satir-ici dongunun satirlari sayfa JS'inden GERCEKTEN cikti;
# bu bir varliga-tasima kaybi DEGIL, bilerek yapilan bir tek-kaynak refaktoru.
# Kisit yargisinin kendi iddiasi ayri kapida olculur: tools/onizleme-kisit-kosul-test.py.
BILEREK_DEGISEN_TAM = (
    # ESKI: satir-ici kisit dongusu (kiyas commit'inde)
    ("if(kis){ for(var ad in kis){ if(Object.prototype.hasOwnProperty.call(kis,ad)){",
     "kisit dongusu tek kaynaga tasindi — ESKI dongu basi"),
    ("var v=s.parametreler[ad];", "kisit dongusu tek kaynaga tasindi — ESKI deger okuma"),
    ("if(v!==undefined && kis[ad].indexOf(v)<0){",
     "kisit dongusu tek kaynaga tasindi — ESKI ihlal kosulu"),
    ("}}}", "kisit dongusu tek kaynaga tasindi — ESKI dongu kapanisi"),
    # YENI: tek kaynaktaki fonksiyona cagri
    ("var kisitFn=window.PRUVO_SECENEK&&PRUVO_SECENEK.onizlemeKisitIhlali;",
     "kisit dongusu tek kaynaga tasindi — YENI fonksiyon referansi (yoksa fail-closed)"),
    ("if(kis&&(!kisitFn||kisitFn(kis,s.parametreler))){",
     "kisit dongusu tek kaynaga tasindi — YENI ihlal kosulu (2 argumanli ilk hali)"),
    # 2026-08-03: `eger` KOSUL DEGERI fail-closed sertlestirmesi — cagriya 3. arguman
    # (URUN_SEMA) eklendi ki hicbir musteri girdisiyle eslesemeyen bir kosul degeri
    # (yazim hatasi) girdiyi sessizce etkisizlestiremesin. Yine varliga-tasima kaybi
    # DEGIL; iddiasi tools/onizleme-kisit-kosul-test.py'de olculur.
    ("if(kis&&(!kisitFn||kisitFn(kis,s.parametreler,URUN_SEMA))){",
     "kisit cagrisina sema argumani eklendi — YENI ihlal kosulu"),
    # 2026-08-08: Consent Mode v2'nin `ad_storage: denied` halinde Google'in SART KOSTUGU
    # iki ayar GA head blogunda HIC YOKTU. Ikisi de YENI satirdir; kiyas commit'inden bu
    # yana eklenmis bir ICERIK kazanimidir, varliga-tasima KAYBI DEGIL (eksen 2 yalniz
    # tasima kaybini/eklentisini olcer). Hicbir alani 'granted' YAPMAZLAR; varsayilan
    # denied aynen kalir -> riza yuzeyi genislemez.
    #   url_passthrough    : reklam tiklama kimligi (gclid/gbraid/wbraid) CEREZ YAZILMADAN
    #                        sayfadan sayfaya URL uzerinde tasinir.
    #   ads_data_redaction : riza yokken reklam isteklerinden tanimlayicilar SILINIR.
    # Iddialari ayri kapida olculur: tools/reklam-etiket-kapisi.py (eksen c) — o kapi
    # ikisinin de HER sayfa sinifinda bulundugunu fail-closed nobetler, yani bu iki giris
    # satirlarin GERCEKTEN durdugunu olcen bir iddiayi ORTADAN KALDIRMAZ.
    ("gtag('set', 'url_passthrough', true);",
     "Consent Mode v2 tasima ayari eklendi — YENI satir (nobetci: reklam-etiket-kapisi.py)"),
    ("gtag('set', 'ads_data_redaction', true);",
     "Consent Mode v2 tasima ayari eklendi — YENI satir (nobetci: reklam-etiket-kapisi.py)"),
    # 2026-09-05 — GA ETIKETI GEC YUKLEMEYE ALINDI (LCP kolu). ESKI hal `<script async
    # src=gtag/js>` idi: BOS govdeli bir <script src> etiketi, yani bu eksende JS GOVDESI
    # HIC YOKTU -> KAYIP tarafi bos, yalniz EKLENTI tarafi dogar. Dokuz satir da YENI'dir.
    # NEDEN VARLIGA-TASIMA KAYBI DEGIL: hicbir satir harici varliktan sayfaya geri
    # tasinmadi; olculmus bir performans kusuru (gtag/js iki paketi 351 KB, `async` bandi
    # BIRAKMAZ ve LCP gorselinin onunu tikiyordu) icin YUKLEME ANI degistirildi.
    # ETIKET KALDIRILMADI/KAPATILMADI: `gtag()` dataLayer'a yazar, kutuphane gelince kuyruk
    # oynar; riza varsayilani (denied) + iki tasima ayari + iki `config` cagrisi kutuphaneden
    # ONCE kuyrukta durur, Consent Mode v2 SIRASI korunur.
    # 🔴 SATIRLAR AYIRT EDICI: blok bilerek tek-satirlik konusan ifadelerle yazildi; bu
    # tabloya `}` / `try {` gibi ayirt edici OLMAYAN satir GIRMEDI (yukaridaki kural).
    # 🔴 IDDIA TASINDI, KALDIRILMADI: etiketin HER sayfa sinifinda FIILEN durdugunu
    # tools/reklam-etiket-kapisi.py (a) ekseni fail-closed olcer — `googletagmanager.com/
    # gtag/js` dizgesi TEK KAYNAKTA (build.py::GA_HEAD_SNIPPET) ve bes SINIF A kaynak
    # sayfasinda AYNEN gecer, yani o kapi bu beyanla korlesmez.
    # ✅ ACIK KALEM KAPANDI (5 Eyl 2026, cip KraL-LCPVarlik): blok artik URUN sayfasina
    # GOMULU DEGIL — build.py::ga_head_varlik() onu /varlik/gtag-gec-<hash>.js referansina
    # cevirir (atif modulunun emsali; GA_HEAD_SNIPPET tek parca dize sabiti olarak AYNEN
    # durur, satir-ici basim yolu ~1.300 sayfada degismedi). Olculen yuk 592 B/sayfa idi
    # (on-olcumdeki ~1.035 B HAM blok+HTML yorumudur; yorum zaten yayin_html'de soyuluyordu).
    # 🔴 BU DOKUZ GIRIS YINE DE DUSURULEMEZ — OLCULDU, VARSAYILMADI: eksen 2 kiyas govdesine
    # /varlik/*.js dosyalarini DA EKLER (asagida, "2 (JS: kayip/eklenti yok)" kolu), yani
    # varliga tasinan satirlar kiyasta HALA gorunur ve ESKI ureticide (bos govdeli
    # `<script async src=gtag/js>`) yoklar. Dokuzu cikarilmis bir kopya kosuldu: 12 ornek
    # sayfanin 12'sinde "2 <pid>: JS EKLENTI (9 satir)" KIRMIZISI dogdu. Beyan BAYAT DEGIL;
    # dusurmek kapiyi kirmiziya yakardi ([[bayat-taban-hipotezi-kosumdan-once-curutulur]]).
    ("(function(){var y=0,O=['pointerdown','keydown','touchstart','scroll'],i;",
     "GA etiketi gec yuklemeye alindi — YENI: kapanis + tetik olay kumesi"),
    ("function L(){if(y){return;}y=1;var s=document.createElement('script');s.async=true;",
     "GA etiketi gec yuklemeye alindi — YENI: tek-atislik yukleyici basi"),
    ('s.src="https://www.googletagmanager.com/gtag/js?id=G-5V53CQMSCE";document.head.appendChild(s);}',
     "GA etiketi gec yuklemeye alindi — YENI: etiket URL'i + enjeksiyon (kapi (a) bunu gorur)"),
    ("window.pruvoGtagYukle=L;",
     "GA etiketi gec yuklemeye alindi — YENI: erken tetik icin tek kanonik giris"),
    ("function T(){for(var k=0;k<O.length;k++){window.removeEventListener(O[k],T,true);}L();}",
     "GA etiketi gec yuklemeye alindi — YENI: ilk etkilesim tetigi (kendini soker)"),
    ("for(i=0;i<O.length;i++){window.addEventListener(O[i],T,{capture:true,passive:true});}",
     "GA etiketi gec yuklemeye alindi — YENI: etkilesim dinleyicilerinin baglanmasi"),
    ("function A(){setTimeout(L,800);}",
     "GA etiketi gec yuklemeye alindi — YENI: `load` sonrasi 800 ms gecikme"),
    ("if(document.readyState==='complete'){A();}else{window.addEventListener('load',A);}",
     "GA etiketi gec yuklemeye alindi — YENI: `load` gecmisse de calisan kol"),
    ("setTimeout(L,5000);})();",
     "GA etiketi gec yuklemeye alindi — YENI: 5.000 ms FAIL-OPEN tavani (olcumsuz kalmaz)"),
    # 2026-08-08 — RIZA BANDI REKLAM IZNINI DE ISTER OLDU (Okan karari). TEK OLAY, 19 satir:
    # 6 ESKI (dar analytics-only yol) + 13 YENI (kanonik dort-alan yolu + kapsam kaydi).
    # Varliga-tasima kaybi DEGIL; bant metni ayrica BILEREK_DEGISEN_METIN'de beyan edildi.
    # 🔴 SATIRLAR AYIRT EDICI SECILDI: kod BILEREK tek satirlik ve konusan ifadelerle
    # yazildi. Ilk (cok satirli) yazim `}` · `try {` · `} catch(e){}` gibi AYIRT EDICI
    # OLMAYAN satirlar uretiyordu; onlari beyan etmek GERCEK bir icerik kaybini da
    # maskelerdi. Bu tabloya boyle bir satir GIRMEZ.
    # 🔴 IDDIA TASINDI: yeni yolun her bant yuzeyinde FIILEN kabloli oldugunu
    # tools/reklam-etiket-kapisi.py SINIF C + (e) eksenleri fail-closed olcer.
    # --- ESKI (kiyas commit'indeki dar yol) ---
    ('function kaydet(deger){ try { localStorage.setItem(ANAHTAR, deger); } catch(e){} el.hidden = true; }',
     "riza kaydi kapsam bilgisi tasimiyordu — ESKI kaydet()"),
    ("gtag('consent', 'update', { 'analytics_storage': 'granted' }); } } catch(e){}",
     "geri yukleme yalniz analitigi aciyordu — ESKI kol"),
    ('if(secim === "kabul" || secim === "ret"){ return; }',
     "gorunurluk kapsami bilmiyordu — ESKI kosul"),
    ('if(typeof gtag === "function"){ gtag(\'consent\',\'update\',{\'analytics_storage\':\'granted\'}); }',
     "bant DAR grant yapiyordu (yalniz analytics_storage) — ESKI cagri"),
    ('try { secim = localStorage.getItem(ANAHTAR); } catch(e){}',
     "kapsam anahtari okunmuyordu — ESKI okuma"),
    ('var secim = null;',
     "kapsam degiskeni yoktu — ESKI bildirim"),
    # --- YENI (kanonik dort-alan yolu) ---
    ("else { gtag('consent', 'update', { 'analytics_storage': 'granted' }); } } } catch(e){}",
     "ESKI DAR kayit sessizce genisletilmez — YENI geri yukleme kolu"),
    ('function kapsamAdi(){ return window.PRUVO_RIZA_KAPSAMI || ""; }',
     "kapsam adi tek kaynaktan; kaynak kosmadiysa '' -> fail-closed"),
    ('function kaydet(deger){ var k = deger === "kabul" ? kapsamAdi() : ""; try { localStorage.setItem(ANAHTAR, deger); if(k){ localStorage.setItem(KAPSAM_ANAHTARI, k); } else { localStorage.removeItem(KAPSAM_ANAHTARI); } } catch(e){} if(deger !== "kabul" && typeof window.pruvoRizaUygula === "function"){ window.pruvoRizaUygula(\'denied\'); } el.hidden = true; }',
     "YENI kaydet(): kapsam kaydi + 'Reddet'te dort alanin geri cekilmesi"),
    ("if (localStorage.getItem('pruvo_onay_kapsam') === window.PRUVO_RIZA_KAPSAMI) { window.pruvoRizaUygula('granted'); }",
     "YENI geri yukleme: yalniz GUNCEL kapsamli kayit dort alani acar"),
    ('if(secim === "kabul" && kapsam && kapsam === kapsamAdi()){ return; }',
     "YENI gorunurluk: guncel kapsamda onaylanmissa bant cikmaz"),
    ('if(secim === "ret"){ return; }',
     "YENI gorunurluk: reddedene TEKRAR SORULMAZ"),
    ('if(typeof window.pruvoRizaUygula === "function"){ window.pruvoRizaUygula(\'granted\'); }',
     "YENI bant cagrisi: kanonik dort-alan yolu"),
    ('try { secim = localStorage.getItem(ANAHTAR); kapsam = localStorage.getItem(KAPSAM_ANAHTARI); } catch(e){}',
     "YENI okuma: kapsam anahtari da okunur"),
    ('var KAPSAM_ANAHTARI = "pruvo_onay_kapsam";',
     "YENI kapsam anahtari (dar eski onayi yeni kapsamdan ayirir)"),
    ('var secim = null, kapsam = null;',
     "YENI bildirim: kapsam degiskeni"),
    ("window.PRUVO_RIZA_ALANLARI = ['analytics_storage','ad_storage','ad_user_data','ad_personalization'];",
     "YENI TEK KANONIK KAYNAK: riza verilince acilacak alan kumesi"),
    ("window.PRUVO_RIZA_KAPSAMI = 'analitik+reklam';",
     "YENI kapsam adi (tek kaynak)"),
    ("window.pruvoRizaUygula = function(d){ var g={},a=window.PRUVO_RIZA_ALANLARI,i; for(i=0;i<a.length;i++){ g[a[i]]=d; } gtag('consent','update',g); };",
     "YENI grant/revoke yolu; bandin dort varyanti kumeyi elle TEKRARLAMAZ"),
    # 2026-08-08 — GOOGLE ADS DONUSUM ETIKETI yapilandirmasi eklendi (TEK satir).
    # Kiyas commit'inde HIC yoktu: Ads panelinde "Sayfa goruntuleme = Hatali
    # yapilandirilmis" bunun SONUCUYDU. Varliga-tasima kaybi DEGIL, eksik olcum
    # kablolamasinin tamamlanmasi.
    # 🔴 IDDIA TASINDI: satirin HER sayfa sinifinda fiilen durdugunu
    # tools/reklam-etiket-kapisi.py (f) ekseni fail-closed olcer (K16 mutanti nobetler).
    ("gtag('config', 'AW-18330673570');",
     "Ads donusum etiketi yapilandirmasi — YENI satir (nobetci: reklam-etiket-kapisi.py (f))"),
    # 2026-08-11 — SEPETE EKLE SESSIZ BASARISIZLIGININ ONARIMI. TEK OLAY, 27 satir
    # (3 ESKI + 24 YENI). Zorunlu malzeme secimi butonun 168 px ALTINDAYDI ve onden
    # secili DEGILDI: secimsiz tiklamada yalniz 500 ms titreme oluyor, hicbir hata METNI
    # cikmiyor, sepet BOS kaliyordu (dogrudan satis kaybi, canlida olculdu). Varliga-tasima
    # KAYBI DEGIL; sayfa JS'ine bilerek eklenen davranistir.
    # 🔴 SATIRLAR AYIRT EDICI: her giris YENI bir tanimlayici tasir (hataEl / hataKutusu /
    # hataGoster / hataGizle / kutu / kap / eksikAd / _ilkSecim / secimHata). Jenerik
    # satir (`return null;` · `}` · `hataGizle();`) BILEREK URETILMEDI — oyle bir satiri
    # beyan etmek GERCEK bir icerik kaybini da maskelerdi.
    # 🔴 IDDIA TASINDI: bu satirlarin DAVRANISI tools/sepet-secim-kapisi.py'de (uretilen
    # sayfanin KENDI JS'i node:vm'de tiklanarak) fail-closed olculur; 8 mutant nobetler.
    # --- ESKI (kiyas commit'inde) ---
    ('var seciliMalzeme = "";',
     "secim durumu bos basliyordu — ESKI malzeme bildirimi"),
    ('var seciliRenk = "";',
     "secim durumu bos basliyordu — ESKI renk bildirimi"),
    ('if(URUN_KONFIGUR && window.PRUVO_KONFIGUR && !PRUVO_KONFIGUR.gecerliMi()){ '
     'PRUVO_KONFIGUR.eksikVurgula(); return; }',
     "konfigur kolu SESSIZ donuyordu (yalniz titreme) — ESKI guard"),
    # --- YENI (on-secim + gorunur hata) ---
    ('function _ilkSecim(kok, secici, alan){ var ilk = (kok && kok.querySelector) ? '
     'kok.querySelector(secici) : null; return ilk ? (ilk.getAttribute(alan) || "") : ""; }',
     "baslangic secimi SAYFADAN okunur (JS'te ikinci varsayilan listesi tutulmaz)"),
    ('var seciliMalzeme = _ilkSecim(cipler, ".fil-cip.secili", "data-malzeme");',
     "YENI: malzeme durumu onden secili cipten baslar"),
    ('var seciliRenk = _ilkSecim(renkBtnlar, ".renk-btn.secili", "data-renk");',
     "YENI: renk durumu onden secili butondan baslar"),
    ('var hataEl = document.getElementById("secimHata");',
     "YENI: gorunur hata kutusu referansi"),
    ("function hataKutusu(){", "YENI: hata kutusu uretici (kutu sayfada yoksa fail-loud)"),
    ("if(hataEl || !document.createElement){ return hataEl; }",
     "YENI: kutu varsa yeniden uretilmez"),
    ('var kutu = document.createElement("div");', "YENI: yedek hata kutusu dugumu"),
    ('kutu.id = "secimHata"; kutu.className = "secim-hata";', "YENI: yedek kutu kimligi"),
    ('kutu.setAttribute("role", "alert"); kutu.setAttribute("aria-live", "assertive");',
     "YENI: ekran okuyucu duyurusu"),
    ('kutu.style.cssText = "margin:2px 0 12px;padding:9px 12px;border-radius:8px;'
     'background:#fdecea;border:1px solid #f0b3ae;color:#8f1d19;font-size:13.5px;'
     'font-weight:600;line-height:1.45";',
     "YENI: yedek kutu bicimi (paylasilan CSS'e kural EKLENMEDI)"),
    ("var kap = (btn.parentNode && btn.parentNode.parentNode) || btn.parentNode;",
     "YENI: yedek kutunun baglanacagi kapsayici"),
    ("if(kap && kap.appendChild){ kap.appendChild(kutu); hataEl = kutu; }",
     "YENI: yedek kutu DOM'a baglanir"),
    # ⚠️ Kapanis `}` bu iki satira BITISIK yazildi (build.py'de gerekcesi yazili):
    # yalniz `}` iceren bir satir AYIRT EDICI DEGILDIR, beyan edilemez.
    ("return hataEl; }", "YENI: hataKutusu() donusu"),
    ("function hataGoster(metin){", "YENI: gorunur uyari basici"),
    ("var kutu = hataKutusu();", "YENI: uyari basilacak kutu"),
    ('if(!kutu){ if(typeof alert === "function"){ alert(metin); } return; }',
     "YENI: SON CARE — kutu kurulamazsa bile sessiz donulmez"),
    ('kutu.textContent = metin; kutu.hidden = false; kutu.removeAttribute("hidden"); }',
     "YENI: uyari metni gorunur olur"),
    ('function hataGizle(){ if(hataEl){ hataEl.hidden = true; '
     'hataEl.setAttribute("hidden", "hidden"); hataEl.textContent = ""; } }',
     "YENI: eksik giderilince uyari kapanir"),
    ('if(!KART_SECIM || (seciliMalzeme && seciliRenk && !(seciliRenk === "Diğer" '
     '&& renkOzel && !renkOzel.value.trim()))){ hataGizle(); }',
     "YENI: render() secim tamamlaninca uyariyi kaldirir"),
    ("var eksikAd = [];", "YENI: eksik secim grubu adlari"),
    ('if(eksikM){ eksikAd.push("malzeme"); }', "YENI: eksik malzeme adi"),
    ('if(eksikR){ eksikAd.push("renk"); }', "YENI: eksik renk adi"),
    ('hataGoster(eksikAd.length ? ("Sepete eklemek için " + eksikAd.join(" ve ") + '
     '" seçin.") : "Sepete eklemek için istediğiniz rengi yazın.");',
     "YENI: METINLI uyari — titreme tek basina yetmez"),
    ('if(URUN_KONFIGUR && window.PRUVO_KONFIGUR && !PRUVO_KONFIGUR.gecerliMi()){ '
     'PRUVO_KONFIGUR.eksikVurgula(); hataGoster("Sepete eklemek için renk seçin."); return; }',
     "YENI: konfigur kolu da GORUNUR uyari basar"),
    # 2026-08-11 — GA4 E-TICARET HUNI OLAYLARI eklendi (14 satir, HEPSI YENI; kiyas
    # commit'inde HICBIRI yoktu). Kiyas commit'ine kadar GA4'e yalniz sayfa goruntuleme
    # gidiyordu: urun goruntuleme / sepete ekleme / odemeye baslama olaylarinin hicbiri
    # YOKTU, oysa Meta huni yuzeyi TAM kuruluydu. Varliga-tasima KAYBI DEGIL; eksik
    # olcum kablolamasinin tamamlanmasidir (AW donusum etiketi girisiyle AYNI sinif).
    # 🔴 SATIRLAR AYIRT EDICI: her giris YENI bir tanimlayici tasir (PRUVO_GA4_OLAYLARI /
    # pruvoGA4Track / gAtcAdet / gAtcKalem / gAtcVeri). Ciplak `}` / `};` satiri BILEREK
    # URETILMEDI — kapanislar bir onceki satira bitisik yazildi (jenerik satiri beyan
    # etmek GERCEK bir icerik kaybini da maskelerdi).
    # 🔴 IDDIA KALDIRILMADI, TASINDI: bu satirlarin DAVRANISI tools/ga4-olay-kapisi.py'de
    # olculur — uretilen sayfanin KENDI JS'i node:vm'de kosturulup olay kuyruguna DUSEN
    # cagri okunur; riza YOKKEN sifir olay beklenir. 10 mutant + 1 KONTROL nobetler
    # (tools/ga4-olay-mutasyon.py).
    ("window.PRUVO_GA4_OLAYLARI = ['view_item','add_to_cart','begin_checkout','generate_lead'];",
     "YENI: GA4 olay beyaz listesi — tek kanonik kaynak (satin alma BILEREK yok). "
     "9 Eyl 2026: `generate_lead` EKLENDI — WhatsApp CTA tiklamasi tek kaynaktan "
     "(build.py::GA_HEAD_SNIPPET) uretilen 36k sayfada da olculsun diye; DAVRANIS "
     "nobetcisi tools/ga4-olay-kapisi.py + ga4-olay-mutasyon.py (beyan korlestirmez)"),
    ("window.pruvoGA4Track = function(olay, veri){",
     "YENI: riza-kapili GA4 olay gondericisi"),
    ("try { if(localStorage.getItem('pruvo_onay_analitik') !== 'kabul'){ return; } } catch(e){ return; }",
     "YENI: gondericinin riza kapisi (Meta ile AYNI anahtar)"),
    ("var a = window.PRUVO_GA4_OLAYLARI, i;",
     "YENI: beyaz liste yerel referansi"),
    ("for(i=0;i<a.length;i++){ if(a[i] === olay){ gtag('event', olay, veri); return; } } };",
     "YENI: yalniz beyaz listedeki ad gonderilir (kapanis bitisik yazildi)"),
    # (view_item cagrisi TAM SATIR beyan EDILEMEZ — govdesi urun basina degisir;
    #  onek deseni yukarida BILEREK_DEGISEN'dedir.)
    ("var gAtcAdet = PRUVO_SECENEK.adetDuzelt(satir.adet);",
     "YENI: sepete ekleme adedi (tek kaynak: secenekler.js)"),
    ("var gAtcKalem = { item_id: URUN.fid, item_name: URUN.baslik,",
     "YENI: add_to_cart kalemi — item_id DAIMA katalog kimligi"),
    ("item_category: URUN.kategori, quantity: gAtcAdet };",
     "YENI: add_to_cart kalem alanlari (kisisel veri YOK)"),
    ('var gAtcVeri = { currency: "TRY", items: [gAtcKalem] };',
     "YENI: add_to_cart govdesi"),
    ("if(mAtcVeri.value != null){ gAtcVeri.value = mAtcVeri.value;",
     "YENI: tutar Meta govdesiyle AYNI degerden turer"),
    ("if(gAtcAdet > 0){ gAtcKalem.price = mAtcVeri.value / gAtcAdet; } }",
     "YENI: birim fiyat (kapanis bitisik yazildi)"),
    ('if(typeof window.pruvoGA4Track === "function"){ window.pruvoGA4Track("add_to_cart", gAtcVeri); }',
     "YENI: sepete ekleme olayi (Meta AddToCart ile AYNI noktadan)"),
    # 2026-08-11 — CTA DENGESI: sepet butonu artik ETIKETLI. Gorunur metin "Sepette ✓"
    # olurken aria-label "Sepete Ekle"de kalsaydi ekran okuyucu kullanicisi butonun ne
    # yaptigini YANLIS duyardi; bu TEK ve AYIRT EDICI satir durumu aria/title'a da yazar.
    # Eski `else` kolu (yazisiz ikon) YERINDE DURUYOR — satir SILINMEDI, EKLENDI.
    ('if(label){ var eD = has ? "Sepette ✓ — çıkarmak için tıklayın" : "Sepete Ekle"; '
     'btn.setAttribute("aria-label", eD); btn.setAttribute("title", eD); }',
     "YENI: etiketli sepet butonunda aria/title durum senkronu (nobetci: cta-denge-kapisi.py)"),
)

# ---------------------------------------------------------------- CSS BEYANI
# 🔴 NEDEN VAR (11 Agu 2026, OLCULEN KILITLENME): eksen 2'nin JS kolunda
# (BILEREK_DEGISEN / BILEREK_DEGISEN_TAM) ve eksen 1'de (BILEREK_DEGISEN_METIN) beyan
# yuzeyi vardi, eksen 2'nin CSS kolunda YOKTU. CSS kiyasi BAYT ESITLIGIDIR ve kiyas
# nesnesi git gecmisindeki DONMUS uretecidir -> paylasilan urun sayfasi CSS'i FIILEN
# DEGISTIRILEMEZ hale gelmisti: her degisiklik "2 CSS KAYIP/EKLENTI" ile kirmizi yanar,
# `--referans-tazele` ise kapi YESILKEN calisir. Yani cikis yolu olmayan bir kilit.
# Olculdu (11 Agu): Okan'in "Sepete Ekle WhatsApp'tan buyuk olsun" talebi bu kilide
# carpti; talep CSS'siz karsilanamaz (medya sorgusu satir-ici `style` ile yazilamaz).
#
# 🔴 KAPI ZAYIFLAMAZ — giris kurallari BILEREK_DEGISEN_METIN ile AYNI:
#   1. GRANUL: (ESKI parca, YENI parca, gerekce) ucLUSU; joker/regex/bolge muafiyeti YOK.
#      Saf eklenti icin ESKI "" birakilir.
#   2. YENI parca AYIRT EDICI olmali (>=12 gorunur karakter + `{` ya da `:` icermeli);
#      bosluk/parantez yigini beyan EDILEMEZ — oyle bir giris gercek bir kaybi maskelerdi.
#   3. Beyanlar YENI->ESKI yonunde BIRER KEZ uygulanir, sonra TAM BAYT ESITLIGI yine
#      aranir: beyan ikinci bir degisikligi MASKELEYEMEZ.
#   4. BAYAT BEYAN FAIL-LOUD: `yeni` parcasi uretilen CSS'te bulunamazsa kapi KIRMIZI.
#   5. IDDIA TASINIR: beyan edilen gorsel kural bir BASKA kapida fail-closed olculmelidir;
#      gerekce satirinda o kapi YAZILIR.
BILEREK_DEGISEN_CSS = (
    # 2026-08-11 — CTA DENGESI (Okan talebi). Iddia tools/cta-denge-kapisi.py'de fail-closed
    # olculur: CTA-A1-ORAN (Sepete Ekle alani >= WhatsApp), CTA-A2-BANT-PAYI (<%10),
    # CTA-A4-DOKUNMA-44. Mutasyon kaniti: tools/cta-denge-mutasyon.py (9 oldurucu).
    ("", ";flex-wrap:wrap;\n    justify-content:flex-end",
     "eylem blogu sarabilir + saga yaslanir (nobetci: cta-denge-kapisi.py)"),
    # 2026-08-11 (UCUNCU tur, Okan karari "etiketi kisalt"): hap etiketi artik HER
    # genislikte kisa oldugu icin uzun on-ekin gizlenmesi MOBIL BLOKTAN cikip TEMEL
    # CSS'e tasindi. Masaustu CTA dengesini tutan sey budur; kural mobil-only'ye geri
    # daralirsa hap buyur ve CTA-A1-ORAN KIRMIZI yanar (mutant: cta-denge-mutasyon M12).
    ("", "  \n\n\n\n  .wa-uzun{display:none}\n",
     "hap etiketi HER genislikte kisa — masaustu denge kaynagi "
     "(nobetci: cta-denge-kapisi.py CTA-A1-ORAN · mutant: cta-denge-mutasyon.py M12)"),
    # 2026-08-11 (ikinci tur, Okan): buton artik METNE gore buzusur. UCUNCU turda eski
    # `min-width` DENGE TABANI KALKTI: hap kisa etikete dusunce (masaustu 11.131 ->
    # 8.340 px² model) taban gereksizlesti ve buton masaustunde de GERCEK fit-content
    # oldu (155,8x56 = 8.725 px², oran 1,05).
    # Kol: CTA-A1-ORAN + CTA-A7-ETIKET-SIGDI (etiket kutuya sigiyor mu).
    ("", ";width:fit-content;height:56px;\n    padding:0 14px;gap:9px;"
         "color:#fff;font-size:16px;font-weight:700;font-family:inherit",
     "Sepete Ekle ETIKETLI + metne gore dar, tabansiz gercek fit-content "
     "(nobetci: cta-denge-kapisi.py CTA-A1-ORAN + CTA-A7-ETIKET-SIGDI)"),
    ("", "}\n  .cart-label{white-space:nowrap",
     "buton etiketi tek satirda kalir (nobetci: cta-denge-kapisi.py)"),
    ("", "   \n    .help-cta-inner{padding:8px 14px;gap:10px;flex-wrap:nowrap;\n"
         "      justify-content:space-between;text-align:left}\n"
         "    .help-cta-text{font-size:11px;line-height:1.3;display:-webkit-box;\n"
         "      -webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}\n"
         "    .help-cta-btn{padding:11px 14px;font-size:13px;gap:6px;min-height:44px;"
         "flex:none}\n"
         "    .eylem-ikonlar{flex-wrap:nowrap;width:100%}\n    \n\n\n\n"
         "    .ikon-sepet{flex:none}\n  ",
     "mobil sticky bant %16,6 -> %7,5 + Sepete Ekle mobilde TAM fit-content "
     "(`flex:none` buyumeyi durdurur; uzun on-ek gizlemesi UCUNCU turda temel CSS'e "
     "TASINDI ve sifirlanacak taban kalmadigi icin mobil min-width sifirlamasi SILINDI; "
     "nobetci: cta-denge-kapisi.py CTA-A2-BANT-PAYI + CTA-A1-ORAN)"),
    # 2026-08-11 — ONERILEN MALZEME ON-SECIMI (Okan karari). Iki YENI gorsel kural:
    # (1) cip tutari etiketi, (2) onerilenden sapinca cikan bilgi notu kutusu.
    # 🔴 IDDIA TASINDI: ogelerin GERCEKTEN basildigi/kosula bagli oldugu
    # tools/d1-fiyat-parite-kapisi.py E7/E9'da fail-closed olculur; mutasyon kaniti
    # tools/urun-vitrin-kapsam-mutasyon.py :: M8/M10/M11.
    ("", "\n   \n  .fil-tutar{font-size:11.5px;font-weight:700;color:var(--navy);"
         "margin-top:1px}",
     "malzeme cipi kendi tutarini gosterir (nobetci: d1-fiyat-parite-kapisi.py E7)"),
    ("", "\n  .fil-cip.secili .fil-tutar{color:#fff}",
     "secili cipte tutar okunur kalir (lacivert dolgu uzerinde beyaz)"),
    ("", "\n   \n  .oneri-not{margin:8px 0 0;padding:8px 11px;border-radius:8px;"
         "background:#fff7e6;\n"
         "    border:1px solid #f0d9a8;color:#6b4e11;font-size:12.5px;line-height:1.5}\n"
         "  .oneri-not[hidden]{display:none}",
     "bilincli-secim notu kutusu (nobetci: d1-fiyat-parite-kapisi.py E9)"),
    # 2026-08-20 — GUVEN SERIDI (P3) + SATIN ALMA SERIDI (P2) taban kurallari.
    # ArTisT olcumu: (P3) 11 urun sayfasinin hicbirinde CTA'nin yaninda guven ibaresi
    # yoktu; (P2) parametrik sayfalarda fiyat+CTA hicbir kaydirma noktasinda ilk ekranda
    # degildi. Serit MASAUSTUNDE GORUNMEZ (`display:none`) — orada fiyat/CTA iki kolonlu
    # duzende zaten ilk ekranda; `[hidden]` kurali medya sorgusundaki `display:flex`
    # yazar ozgullugunu EZER, yani JS baglanamadiysa calismayan bir CTA GORUNMEZ.
    # 🔴 IDDIA TASINDI: seridin varligi/teklıgi + guven seridinin HUKUKI VAAT TASIMADIGI
    # (iade hakki / kargo ucreti / teslim suresi YOK) ve yasal link etiketinin
    # sayfalar.CONTENT_PAGES'ten turedigi tools/ilk-ekran-kapisi.py A1..A7'de fail-closed
    # olculur; mutasyon kaniti ayni dosyada `--kendini-test` (7 oldurucu).
    ("", "\n\n\n  .guven-serit{display:flex;flex-wrap:wrap;align-items:center;"
         "gap:6px 14px;\n"
         "    margin-top:8px;font-size:12.5px;line-height:1.5;color:var(--gray-text)}\n"
         "  .guven-oge{display:inline-flex;align-items:center;gap:6px}\n"
         "  .guven-oge svg{width:14px;height:14px;fill:#178a44;flex:none}\n"
         "  .guven-link{color:var(--navy-2);font-weight:600;text-decoration:underline}\n"
         "  .guven-link:hover{color:var(--navy)}\n\n  \n\n\n\n\n"
         "  .satin-serit{display:none}\n  .satin-serit[hidden]{display:none}\n\n  ",
     "guven seridi + serit taban kurali (masaustunde gizli) "
     "(nobetci: ilk-ekran-kapisi.py A2/A4/A5)"),
    # 2026-08-20 — SATIN ALMA SERIDI, DAR EKRAN KOLU. `position:fixed` oldugu icin serit
    # KAYDIRMA KONUMUNDAN BAGIMSIZ olarak gorunur alanin altinda durur; ArTisT'in cividi
    # (375x812'de fiyat + "Sepete Ekle" ilk 812 px icinde) YAPISAL olarak burada karsilanir.
    # `body.serit-var` kancasi: dolgu/FAB/yukari-ok kaymasi YALNIZ serit gercekten
    # acildiysa uygulanir — paylasilan CSS yasal/icerik sayfalarina da basildigi icin
    # kosulsuz `body{padding-bottom}` oralarda 72 px olu bosluk birakirdi.
    ("", "}\n    \n\n\n\n\n"
         "    .satin-serit{display:flex;position:fixed;left:0;right:0;bottom:0;"
         "z-index:61;\n"
         "      align-items:center;gap:10px;padding:8px 12px "
         "calc(8px + env(safe-area-inset-bottom));\n"
         "      background:var(--gray-card);border-top:1px solid var(--gray-line);\n"
         "      box-shadow:0 -2px 12px rgba(18,41,77,.14)}\n"
         "    .satin-serit[hidden]{display:none}\n"
         "    .serit-fiyat{flex:1 1 auto;min-width:0;font-size:17px;font-weight:800;\n"
         "      color:var(--navy);line-height:1.25;overflow:hidden;"
         "text-overflow:ellipsis;\n"
         "      white-space:nowrap}\n"
         "    .serit-sepet{flex:none;display:inline-flex;align-items:center;"
         "justify-content:center;\n"
         "      gap:8px;min-height:44px;padding:10px 16px;border:none;"
         "border-radius:9px;\n"
         "      background:var(--navy);color:#fff;font-size:15px;font-weight:700;\n"
         "      font-family:inherit;cursor:pointer}\n"
         "    .serit-sepet svg{width:18px;height:18px;fill:#fff}\n"
         "    .serit-sepet.added{background:#178a44}\n"
         "    .serit-sepet.kilitli{opacity:.45;cursor:not-allowed}\n"
         "    .serit-label{white-space:nowrap}\n    \n\n\n\n\n\n"
         "    body.serit-var{padding-bottom:72px}\n"
         "    body.serit-var .cart-fab{bottom:80px}\n"
         "    body.serit-var .top-btn{bottom:80px}\n"
         "    body.serit-var.fab-var .top-btn{bottom:142px",
     "dar ekranda fiyat+CTA seridi + `serit-var` kancali dolgu "
     "(nobetci: ilk-ekran-kapisi.py A1/A7)"),
)


def css_beyani_uygula(yeni_css, tablo=None):
    """Beyan edilen CSS parcalarini YENI->ESKI yonunde BIRER KEZ geri cevirir.

    Doner: (donusmus_css, hatalar). Bulunmayan `yeni` parcasi BAYAT BEYANDIR ve
    hata olarak doner (sessiz muafiyet yok). `tablo` yalniz OZ-NOBETCININ sentetik
    fiksturleri icindir; uretimde daima BILEREK_DEGISEN_CSS kullanilir."""
    hatalar = []
    for i, (eski_p, yeni_p, gerekce) in enumerate(
            BILEREK_DEGISEN_CSS if tablo is None else tablo):
        gorunur = "".join(yeni_p.split())
        if len(gorunur) < 12 or not ("{" in yeni_p or ":" in yeni_p):
            hatalar.append("2b CSS BEYANI AYIRT EDICI DEGIL (#%d): %r -> gerekce: %s"
                           % (i, yeni_p[:40], gerekce))
            continue
        if yeni_p not in yeni_css:
            hatalar.append("2b BAYAT CSS BEYANI (uretilen CSS'te bulunamadi, #%d): %r "
                           "-> gerekce: %s. Kural artik yoksa GIRISI SIL."
                           % (i, yeni_p[:60], gerekce))
            continue
        yeni_css = yeni_css.replace(yeni_p, eski_p, 1)
    return yeni_css, hatalar


# --- CSS BEYAN YUZEYININ KENDI NOBETCISI (HER kosumda, olcumden ONCE) -----------
# 🔴 NEDEN: beyan yuzeyi kapiyi SUSTURMA kolusudur; susturma kolu nobetsiz kalamaz.
# Bu deponun olculmus sinifi: kapi kapsami genisletilince pozitif nobetci SESSIZCE
# olur ve kimse fark etmez ([[kapi-kapsam-genisletme-tuzagi]] · [[tekil-yama-sinifi-kapatmaz]]).
# Fiksturler SENTETIKTIR: gercek CSS'e, gercek tabloya ve diske DOKUNMAZ.
#   C1 AYIRT EDICILIK : ayirt edici olmayan (bosluk/parantez yigini) beyan REDDEDILIR.
#   C2 BAYAT BEYAN    : isaret ettigi CSS artik yoksa FAIL-LOUD (sessizce yutulmaz).
#   C3 MASKELEME YOK  : beyan kapsami DISINDAKI ikinci bir degisiklik HALA gorunur.
#   C4 KONTROL        : gecerli beyan uygulanir, hata URETMEZ ve eski hale DONER.
_CSS_OZ_ESKI = "  .zzfik-a{color:red}\n  .zzfik-b{color:blue}\n"
_CSS_OZ_YENI = "  .zzfik-a{color:red;font-weight:700}\n  .zzfik-b{color:blue}\n"
_CSS_OZ_GECERLI = ("", ";font-weight:700", "oz-nobetci fiksturu")


def css_beyan_mekanizmasi_dogrula():
    """Bos liste = yuzey saglam. Her giris bir BOZUKLUK teshisidir."""
    d = []
    _, h1 = css_beyani_uygula(_CSS_OZ_YENI, (("", "  }  ", "ayirt edici olmayan"),))
    if not any("AYIRT EDICI DEGIL" in x for x in h1):
        d.append("C1 ayirt edicilik sarti OLU: bosluk/parantez yigini beyan KABUL edildi "
                 "-> tek girisle butun CSS ekseni yutulabilirdi")
    _, h2 = css_beyani_uygula(_CSS_OZ_YENI, (("", ".zzfik-yok{color:#000}", "bayat"),))
    if not any("BAYAT CSS BEYANI" in x for x in h2):
        d.append("C2 bayat beyan nobeti OLU: uretilen CSS'te BULUNMAYAN beyan sessizce "
                 "yutuldu -> tablo olu muafiyet deposuna doner")
    ikinci = _CSS_OZ_YENI.replace(".zzfik-b{color:blue}", ".zzfik-b{color:green}")
    c3, h3 = css_beyani_uygula(ikinci, (_CSS_OZ_GECERLI,))
    if h3 or c3 == _CSS_OZ_ESKI:
        d.append("C3 MASKELEME: beyan kapsami DISINDAKI ikinci degisiklik beyan "
                 "uygulandiktan sonra KAYBOLDU -> beyan gercek bir kaybi gizleyebilir")
    c4, h4 = css_beyani_uygula(_CSS_OZ_YENI, (_CSS_OZ_GECERLI,))
    if h4 or c4 != _CSS_OZ_ESKI:
        d.append("C4 KONTROL: gecerli beyan ya hata uretti ya eski hale DONDURMEDI "
                 "(hata=%r) -> mekanizma her seye kirmizi yakan bir alarm" % (h4[:1],))
    return d


# ---------------------------------------------------------------- GORUNUR METIN BEYANI
# 🔴 NEDEN VAR (mimar karari, 8 Agu 2026): eksen 2'nin BILEREK_DEGISEN yuzeyi vardi,
# eksen 1'in (gorunur METIN) YOKTU. Bu bir ASIMETRIYDI: kiyas nesnesi git gecmisindeki
# DONMUS bir uretecidir, dolayisiyla o commit'ten bu yana yapilan BILEREK her metin
# degisikligi "cikarim kaybi" gibi gorunup TUM YAYINI durduruyordu (8 Agu'da iki kez
# yasandi). Eksen KALDIRILMADI; beyan yuzeyi acildi.
#
# 🔴 GIRIS KURALLARI — her biri kapinin gucunu KORUR:
#   1. GRANUL: (ESKI metin, YENI metin, gerekce) ucLUSU. Joker/regex/toplu muafiyet YOK;
#      "su cumle su cumleye dondu" denir, "bu bolgeye dokunma" DENMEZ.
#   2. IDDIA KALDIRILMAZ, TASINIR: beyan edilen YENI metnin sayfalarda GERCEKTEN durdugunu
#      olcen fail-closed bir eksen BASKA bir kapida bulunmak ZORUNDA (ornek: riza bandi
#      metni -> tools/reklam-etiket-kapisi.py SINIF C). Gerekce satirinda o kapi YAZILIR.
#   3. BEYAN EDILMEMIS her metin degisikligi HALA KIRMIZI yakar: beyanlar ESKI metne
#      uygulandiktan SONRA TAM ESITLIK yine aranir -> beyan ikinci bir degisikligi
#      MASKELEYEMEZ (B3 fiksturu bunu nobetler).
#   4. BAYAT BEYAN FAIL-LOUD: hicbir sayfada eslesmeyen giris sessizce durmaz, kapi
#      KIRMIZI yanar (S3 hijyeni) — yoksa tablo zamanla olu muafiyet deposuna doner.
# Bosluk serbest yazilir; kiyas normalize edilmis (tek bosluk) metin uzerinden yapilir.
BILEREK_DEGISEN_METIN = (
    # 2026-08-08 — RIZA BANDI METNI reklam cerezini de BEYAN EDER OLDU (Okan karari).
    # NEDEN ZORUNLU: ayni turda "Kabul Et" ad_storage/ad_user_data/ad_personalization
    # alanlarini da 'granted' yapar hale getirildi. Reklam cerezinden HIC soz etmeyen bir
    # metinle alinan onay bu izinleri KAPSAMAZ; metni degistirmeden izni genisletmek acik
    # riza olmazdi. Yani bu metin degisikligi bir CIKARIM KAYBI degil, hukuki ZORUNLULUK.
    # 🔴 IDDIA TASINDI, KALDIRILMADI: yeni metnin BES kaynak sayfada ve uretecte GERCEKTEN
    # durdugunu tools/reklam-etiket-kapisi.py SINIF C ekseni fail-closed olcer (bant yuzeyi
    # basina; metin tek kaynaktan bayt-birebir turer). Orada kirmizi yanmadan bu beyan
    # tek basina bir sey serbest birakmaz.
    ("Trafiği anlamak için isteğe bağlı analiz çerezleri (Google Analytics) kullanmak "
     "istiyoruz. Onayınız olmadan çalışmazlar. Gizlilik Politikası",
     "Trafiği anlamak için analiz çerezleri (Google Analytics), reklamlarımızın ölçümü ve "
     "kişiselleştirilmesi için reklam çerezleri (Google Ads) kullanmak istiyoruz. İkisi de "
     "isteğe bağlıdır; onayınız olmadan çalışmazlar. Onayınızı istediğiniz zaman Gizlilik "
     "Politikası sayfasından geri alabilirsiniz.",
     "riza bandi reklam cerezini beyan eder oldu; yeni metnin varligini "
     "tools/reklam-etiket-kapisi.py SINIF C ekseni fail-closed olcer"),
    # 2026-08-10 — OZEL URETIM URUN SAYFASINA TESLIM BEYANI EKLENDI.
    # NEDEN CIKARIM KAYBI DEGIL, EKLEME: 23.968 ozel uretim urununun sayfasinda
    # teslim suresi HIC yaziliydi degildi; ziyaretci "ne zaman elime gecer" bilmeden
    # odeme karari veriyordu. Sure sitede zaten 69 yerde (SSS · teslimat-iade ·
    # mesafeli-satis m.4) BU aralikla yazili — sayfa o taahhudu TEKRARLAR, YENI bir
    # taahhut ICAT ETMEZ. Eski metnin TEK BIR kelimesi bile kaybolmaz/degismez.
    # CAPA NEDEN BU: `Malzeme Rehberi` baglantisi malzeme blogunun KUYRUGUDUR ve o
    # blok "fiziksel ISE bos" kuralindadir -> capa BUTUN ozel uretim sayfalarinda
    # (kart-secim · sema · konfigur · panelsiz) VAR, hazir/stok sayfasinda YOK.
    # Yani beyan SINIF HIZALIDIR; urun katalogu degistikce bayatlamaz.
    # 🔴 IDDIA TASINDI, KALDIRILMADI: yeni cumlenin sayfalarda GERCEKTEN durdugunu
    # tools/cayma-beyani-kapisi.py B4 (varlik · tek kaynaktan turetilmis metin),
    # B5 (rakip teslim araligi YOK) ve B6 (hazir/stok sayfasina SIZMADI) fail-closed
    # olcer; E5 cumlenin build.py'de ikinci kez yazilmadigini nobetler.
    # Cumle BURAYA KOPYALANMAZ: tek kaynak secenekler.js BEYAN'dir, build uzerinden
    # okunur -> bu tablo cumle degisirse sessizce bayatlayamaz.
    ("Hangi malzeme nerede kullanılır? Malzeme Rehberi &rarr;",
     "Hangi malzeme nerede kullanılır? Malzeme Rehberi &rarr; "
     + build.BEYAN["SAYFA_OZEL"],
     "ozel uretim urun sayfasi teslim beyani (10 Agu); yeni metnin varligini "
     "tools/cayma-beyani-kapisi.py B4/B5/B6 + E5 fail-closed olcer"),
    # ⚠️ HAZIR/STOK metni (BEYAN["SAYFA_HAZIR"]) ayni turda DEGISTI (Okan karari:
    # "3-5 is gunu" hazir kola da yazildi) ama BURAYA GIRIS YAZILMAZ ve YAZILMAMALI:
    # `eski_kok_kur` eski ref'ten YALNIZ tools/build.py'yi alir, secenekler.js dahil
    # butun icerik kaynaklarini GUNCEL agactan symlink'ler. Yani BEYAN sozlugunden
    # gelen cumleler ESKI uretecin ciktisinda da yeni halleriyle gorunur -> gorunur
    # metin ekseninde fark YOKTUR. Buraya giris eklemek "hicbir sayfada eslesmeyen
    # BAYAT BEYAN" olurdu ve 1c hijyeni onu dogru sekilde KIRMIZI yakti (olculdu).
    # 2026-08-11 — CTA DENGESI: sepet butonu YAZISIZ ikondan ETIKETLI butona dondu.
    # Bu bir metin KAYBI degil EKLENTISIDIR: adet satirinin sagindaki buton artik
    # "Sepete Ekle" yazisini GORUNUR tasiyor (once yalniz aria-label/title'daydi).
    # CAPA NEDEN BU: adet secici ("Adet − +") kart-secim · sema · konfigur · fiziksel
    # panellerin HEPSINDE vardir ve butonun HEMEN SOLUNDADIR -> sinif hizali, katalog
    # degistikce bayatlamaz.
    # 🔴 IDDIA TASINDI, KALDIRILMADI: etiketin GERCEKTEN basildigini ve butonun
    # WhatsApp'i gectigini tools/cta-denge-kapisi.py CTA-A5-KANAL-WA + CTA-A1-ORAN
    # fail-closed olcer; mutasyon kaniti tools/cta-denge-mutasyon.py :: M3.
    ("Adet − +", "Adet − + Sepete Ekle",
     "sepet butonu etiketlendi (11 Agu); etiketin varligini "
     "tools/cta-denge-kapisi.py CTA-A5-KANAL-WA fail-closed olcer"),
)


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def _benzersiz_isaret(metin, i):
    """`metin`de GECMEYEN bir yer tutucu uret. Carpisma sessizce YANLIS kiyas uretirdi,
    o yuzden carpisma varken isaret uzatilir (fail-loud degil, fail-safe)."""
    isaret = "\x00BEYAN%d\x00" % i
    while isaret in metin:
        isaret = "\x00" + isaret
    return isaret


def _beyan_uygula(eski_metin, tablo=None):
    """Beyan edilen ESKI->YENI metin donusumlerini ESKI metne uygular.

    🔴 DONUSUM IDEMPOTENT OLMAK ZORUNDA (olculdu, 10 Agu 2026): bir beyan girisinin ESKI
    metni YENI metnin bir PARCASI olabilir — tipik hali "YENI = ESKI + eklenen cumle"
    (teslim beyani girisi tam boyle: ESKI, YENI'nin ONEKI). Duz `str.replace` o durumda
    ZATEN YENI halde olan bir metinde de ESKI oneki bulur ve eki IKINCI kez yapistirir.
    Sonuc: donusum metni BUYUTUR (olculdu: 4849 -> 4958 -> 5067 bayt, her uygulamada
    +109) ve IKI TARAFI DA AYNI olan bir kiyasta bile "GORUNUR METIN degisti" dogar.
    Bu, `--kendini-test` bataryasindaki UC KONTROL mutantini birden yanlis-KIRMIZI
    yakti (kapi kendi kirmizisini yakamaz hale geldi) ve olduruculerin bir kismi da
    kendi eksenleri yerine bu sahte metin bulgusundan kirmizi aliyordu.

    COZUM (kapiyi GEVSETMEZ): ESKI->YENI donusumunden ONCE metinde ZATEN VAR olan YENI
    gecisler maskelenir, donusum yalniz CIPLAK ESKI gecislere uygulanir, sonra maske
    geri alinir. Yani beyan "bu metin su hale geldi" der; "su metin durdukca sonsuza
    kadar ekle" DEMEZ. Beyan edilmemis ikinci bir degisiklik yine KIRMIZI yakar
    (B3/B11 fiksturleri nobetler) ve bayat beyan yine eslesmez (B6/B8 + 1c hijyeni).

    Doner: (donusmus_metin, eslesen_beyan_indeksleri). Eslesme kaydi BAYAT BEYAN
    hijyeni icindir: hangi girisin hangi sayfada tuttugu suite duzeyinde toplanir."""
    tablo = BILEREK_DEGISEN_METIN if tablo is None else tablo
    eslesen = set()
    for i, (eski, yeni, _gerekce) in enumerate(tablo):
        e, y = _norm(eski), _norm(yeni)
        if not e:
            continue
        isaret = None
        if y and y in eski_metin:
            isaret = _benzersiz_isaret(eski_metin, i)
            eski_metin = eski_metin.replace(y, isaret)
        if e in eski_metin:
            eski_metin = eski_metin.replace(e, y)
            eslesen.add(i)
        if isaret is not None:
            eski_metin = eski_metin.replace(isaret, y)
    return eski_metin, eslesen


_BILEREK_TAM = frozenset(d for d, _g in BILEREK_DEGISEN_TAM)


def _bilerek_degisti(satir):
    s = satir.strip()
    if s in _BILEREK_TAM:
        return True
    for desen, _gerekce in BILEREK_DEGISEN:
        if desen in s:
            return True
    return False


def iskelet(html):
    """Sayfanin CSS/JS YUZEYI CIKARILMIS hali: metin, meta, JSON-LD, gorsel URL'leri,
    kirilim... yani tasima isinin DOKUNMAMASI gereken her sey. JSON-LD script'i JS
    DEGILDIR -> KALIR (yapisal veri bu eksende olculur).
    CSS/JS yuzeyi tamamen SILINIR (yerine isaret konmaz): blok sayisi bilerek degisti
    (bir <script> gomulu iken iki referansa bolundu) — bu eksenin iddiasi blok SAYISI
    degil, bloklar DISINDAKI baytlarin ayni kalmasidir. Geriye kalan bos satir yiginlari
    tek satira indirilir; metin/oznitelik baytlari AYNEN kiyaslanir."""
    s = _STYLE_RE.sub("", html)

    def _s(m):
        return "" if _js_mi(m.group(1)) else m.group(0)
    s = _SCRIPT_RE.sub(_s, s)
    s = _SCRIPT_SRC_RE.sub("", s)
    s = _CSS_LINK_RE.sub("", s)
    return re.sub(r"\n[ \t]*(?:\n[ \t]*)+", "\n", s)


_LDJSON_RE = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_META_RE = re.compile(r'<meta\s+name="([^"]+)"\s+content="([^"]*)"')
_CANON_RE = re.compile(r'<link rel="canonical" href="([^"]+)">')
_A_RE = re.compile(r'<a\b[^>]*\bhref="([^"]*)"[^>]*>')
_IMGSRC_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]*)"')
_ETIKET_RE = re.compile(r"<[^>]+>")


def _duz_metin(s):
    """Gorunur metin: etiketler silinir, bosluk tek boslukta toplanir."""
    return re.sub(r"\s+", " ", _ETIKET_RE.sub(" ", s)).strip()


def _ldjson(s):
    """Sayfadaki JSON-LD bloklari — AYRISTIRILMIS. Ayristirilamayan blok HAM tutulur
    (sessizce dusurulmez: bozuk JSON-LD de bir kayiptir)."""
    out = []
    for g in _LDJSON_RE.findall(s):
        try:
            out.append(json.loads(g))
        except Exception:
            out.append({"__ham__": re.sub(r"\s+", " ", g).strip()})
    return out


def _yapraklar(nesne, yol=""):
    """JSON agacinin (yol -> deger) yapraklari. Sira BAGIMSIZ: liste ogeleri kendi
    icerigine gore siralanir ki JSON-LD dizisi yeniden siralanirsa YANLIS kirmizi olmasin."""
    if isinstance(nesne, dict):
        out = []
        for k in sorted(nesne):
            out += _yapraklar(nesne[k], yol + "/" + str(k))
        return out
    if isinstance(nesne, list):
        out = []
        for x in sorted(nesne, key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False)):
            out += _yapraklar(x, yol + "[]")
        return out
    return [(yol, nesne)]


def _baglantilar(s):
    """href -> (yol, {param: deger}) listesi. Sorgu AYRISTIRILIR ki `?a=1` -> `?a=1&b=2`
    zenginlestirmesi kayip sayilmasin, AMA var olan bir parametrenin DEGERI degisirse
    (ornegin marka=Volvo Penta -> marka=Volvo) KAYIP sayilsin."""
    out = []
    for h in _A_RE.findall(s):
        yol, _, sorgu = h.partition("?")
        parametre = {}
        for parca in sorgu.split("&"):
            if not parca:
                continue
            ad, _, deger = parca.partition("=")
            parametre[ad] = deger
        out.append((yol, parametre))
    return out


def _malzeme_tasima_beyani(p):
    """🔴 11 Agu 2026 — MALZEME KARTLARI YER DEGISTIRDI (kayip DEGIL, TASIMA).

    Zorunlu malzeme secimi "Sepete Ekle" butonunun 168 px ALTINDAYDI: secimsiz tiklama
    hicbir hata METNI basmadan dusuyor, sepet bos kaliyordu (canlida olculdu). Kartlar
    opsiyon panelinin ICINE, butonun USTUNE alindi; asagidaki bilgi bolumunde
    muhendislik-malzeme notu + Malzeme Rehberi linki KALDI. Hicbir kelime kaybolmadi.

    🔴 METIN ELLE YAZILMAZ: kart govdesi urunun KENDI tavsiye kumesinden
    (build._fil_cipleri) ve renk satiri build._renk_butonlari_html()'den TURETILIR ->
    filamentler.json / renk listesi degisince beyan kendiliginden tazelenir, BAYATLAMAZ
    ve urun-basi tavsiye varyantlari icin elle defter tutulmaz.

    IKI GIRIS AYIRT EDILEBILIR: yeni konumun etiketi "Malzeme seçimi", eski bolumun
    basligi "Malzeme"ydi -> 2. giris (ESKI konumu SILEN) 1. girisin YENI konumuna
    yanlislikla uygulanamaz. build.panel_malzeme_html etiketini degistirmeden once buraya bak.

    🔴 IDDIA TASINDI, KALDIRILMADI: kartlarin butondan ONCE basildigini ve secimin
    GERCEKTEN calistigini tools/sepet-secim-kapisi.py fail-closed olcer (8 mutant)."""
    try:
        kartlar = _norm(_duz_metin("".join(build._fil_cipleri(p))))
        renk = _norm(_duz_metin(build._renk_butonlari_html()))
    except Exception:
        return ()
    if not kartlar or not renk:
        return ()
    return (
        (renk, "Malzeme seçimi " + kartlar + " " + renk,
         "malzeme kartlari SECICI olarak butonun USTUNE tasindi — YENI konum "
         "(nobetci: tools/sepet-secim-kapisi.py)"),
        ("Malzeme " + kartlar, "",
         "malzeme kartlari bilgi bolumunden KALKTI — ESKI konum "
         "(nobetci: tools/sepet-secim-kapisi.py)"),
    )


def _onsecim_tutar_beyani(p):
    """🔴 11 Agu 2026 — URUN SAYFASININ VURGULADIGI TUTAR ONERILEN MALZEMEDEN TURER.

    Isletme karari (Okan): musteri urunun ICINE girdiginde onerilen malzeme onden secili
    gelir ve gorunen tutar ONUN tutaridir. Malzeme+renk zaten seciliyken "…'den baslayan"
    demek YANLIS olurdu (sayfa KESIN tutari yazar), bu yuzden JS oncesi statik metin de
    liste tutarindan on-secimli tutara gecti. LISTE tutari KAYBOLMADI: kart · besleme ·
    yapilandirilmis veri hala onu beyan eder ve her malzeme cipi KENDI tutarini tasir.

    🔴 CIFT ELLE YAZILMAZ: (eski metin -> yeni metin) urunun KENDI verisinden ve build'in
    KENDI bicimleyicisinden turetilir -> fiyat/kural degisince beyan kendiliginden
    tazelenir, BAYATLAMAZ ve urun-basi tutar varyantlari icin elle defter tutulmaz.
    Urun bu kolun DISINDAysa (olcuye ozel / yapilandiricili / fiyatsiz) giris URETILMEZ.
    Tutar AYNI kalan uründe (onerisi PLA) bile giris uretilir: degisen sey yalniz sayi
    degil, CUMLE KALIBIDIR — giris uretilmezse o sayfa yanlis-KIRMIZI yanardi.

    🔴 IDDIA TASINDI, KALDIRILMADI: gorunen tutarin sepet/sunucu tutariyla KURUS KURUS
    ayni oldugunu tools/onsecim-parite-kapisi.py, kart/besleme/markup yuzeyinin
    KAYMADIGINI tools/d1-fiyat-parite-kapisi.py fail-closed olcer."""
    try:
        if not build.ONERI_ONSECIM_ACIK or p.get("parametrik") or p.get("konfigur"):
            return ()
        ilan = build.ilan_kurus(p)
        ham = (p.get("fiyat") or "").strip()
        if ilan is None or not ham:
            return ()
        # 🔴 TUTAR ESIT OLSA BILE BEYAN URETILIR: degisen sey yalniz SAYI degil, CUMLE
        # KALIBIDIR ("… TL'den baslayan" -> kesin tutar). Onerisi PLA olan uründe sayi ayni
        # kalir ama metin yine degisir; giris uretilmezse o sayfa yanlis-KIRMIZI yanardi.
        eski = _norm(_duz_metin(build.esc(ham) + "&#39;den başlayan"))
        yeni = _norm(_duz_metin(build.taban_fiyat_metni(ilan / 100.0)))
    except Exception:
        return ()
    if not eski or not yeni:
        return ()
    return ((eski, yeni,
             "urun sayfasinin vurguladigi tutar ONERILEN malzemeden turer (11 Agu); "
             "kurus esitligini tools/onsecim-parite-kapisi.py, kart/besleme/markup "
             "yuzeyinin kaymadigini tools/d1-fiyat-parite-kapisi.py fail-closed olcer"),)


def _seri_etiket_beyani(p):
    """🔴 11 Agu 2026 — GIZLI SERI ADI MUSTERIYE GORUNEN YUZEYDEN KALKTI.

    CLAUDE.md kurali: parametrik serinin ic adi ("Jeneratör") musteriye gorunen yuzeyde
    GECMEZ. Kategori VERISI (urunler.json / D1 / sayfadaki URUN blogu) DEGISMEDI; yalniz
    GORUNEN etiket (rozet, breadcrumb, JSON-LD, ilgili-urun basligi, kategori linki)
    build.gorunur_kategori()'den gecer oldu.

    🔴 CIFT ELLE YAZILMAZ: (ic ad -> gorunur etiket) cifti build.gorunur_kategori()'nin
    KENDISINDEN turetilir -> esleme degisirse beyan kendiliginden tazelenir.
    Donusum YALNIZ parametrik urunde uygulanir (gorunur_kategori boyle karar verir);
    ayni kelimeyi TASIYAN gercek jenerator yedek parcalarinin sayfasinda hicbir sey
    degismez ve bu beyan orada HIC eslesmez.

    🔴 IDDIA TASINDI, KALDIRILMADI: gorunen yuzeyde ic ad izinin 0 oldugunu ve gercek
    urunde kelimenin KALDIGINI tools/ic-seri-izi-kapisi.py fail-closed olcer (7 mutant).

    Doner: (metin_beyanlari, deger_ciftleri) — deger ciftleri JSON-LD yapraklari ve
    baglanti sorgu degerleri icin ESDEGERLIK tanimlar."""
    ic = (p.get("kategori") or "")
    gor = build.gorunur_kategori(p)
    if not ic or gor == ic:
        return (), ()
    ger = ("ic seri adi musteriye gorunen yuzeyden kalkti (CLAUDE.md); nobetci: "
           "tools/ic-seri-izi-kapisi.py")
    metin = (
        ("&rsaquo; %s &rsaquo;" % ic, "&rsaquo; %s &rsaquo;" % gor, ger + " — breadcrumb"),
        (" %s Ölçüye Özel " % ic, " %s Ölçüye Özel " % gor, ger + " — kategori rozeti"),
        ("Diğer %s ürünleri" % ic, "Diğer %s ürünleri" % gor, ger + " — ilgili urun basligi"),
        ('"category":"%s"' % ic, '"category":"%s"' % gor, ger + " — JSON-LD metin kopyasi"),
        ('"name":"%s","item":"%s%s"' % (ic, build.SITE, build.kategori_url(ic)),
         '"name":"%s","item":"%s%s"' % (gor, build.SITE, build.kategori_url(gor)),
         ger + " — JSON-LD breadcrumb metin kopyasi"),
    )
    # Baglanti sorgu degeri HAM (kacisli) halde okunur -> hem duz hem kategori_url()
    # kacisli bicim beyan edilir; ikisi de AYNI kanonik fonksiyondan turer.
    ic_q = build.kategori_url(ic).split("=", 1)[1]
    gor_q = build.kategori_url(gor).split("=", 1)[1]
    return metin, ((ic, gor, ger), (ic_q, gor_q, ger + " — kategori linki"))


def _ilan_araligi_beyani(p):
    """🔴 12 Agu 2026 — YAPILANDIRILMIS VERI TEK FIYAT YERINE ARALIK BEYAN EDIYOR.

    Isletme karari (Okan): kart BASLANGIC tabanini, urun sayfasi ONERILEN malzemenin
    tutarini yazar. Iki sayi bilerek farkli oldugu surece markup'ta TEK fiyat basmak dis
    yuzeye eksik bilgi verir -> `Offer` yerine `AggregateOffer` + lowPrice/highPrice.
    lowPrice KARTIN yazdigi tutardir (degeri DEGISMEZ, yalniz anahtar cogalir); yeni
    yapraklar (lowPrice/highPrice/offerCount) EKLENTIDIR ve eksen 1 eklenti aramaz.
    DEGISEN tek yaprak `offers/@type`dir.

    🔴 IKINCI DEGISIKLIK — TABAN ARTIK TEK TURETME NOKTASINDAN: markup tabani onceden
    `price_number` (tum rakamlari birlestiren AYRI kural) ile hesaplaniyordu; kart ise
    `feed_price` ile. Olculdu: "300 TL (30 cm)" biciminde 1 kayitta kart 300 TL derken
    markup 30.030 TL beyan ediyordu. Iki yuzey artik AYNI sayidan turer. Cift ELLE
    YAZILMAZ: urunun KENDI verisinden ve build'in KENDI iki kuralindan turetilir, yani
    yalniz GERCEKTEN sapan kayitta uretilir ve katalog degisince bayatlamaz.

    🔴 IDDIA TASINDI, KALDIRILMADI: lowPrice == kart tutari, urun sayfasi tutari ==
    onerilen malzeme tutari ve lowPrice <= highPrice iliskisini tum uretilen sayfalarda
    tools/ilan-tutari-kapisi.py fail-closed olcer.

    Doner: (metin_beyanlari, deger_ciftleri) — JSON-LD script'i sayfada KALDIGI icin
    (bkz. iskelet: yapisal veri bu eksende olculur) hem GORUNUR METIN hem YAPRAK ekseni
    beyan ister; ikisi de AYNI iki degerden (taban + tavan) turer."""
    ger = ("markup tek fiyat yerine baslangic/tavan araligi beyan ediyor ve tabani "
           "kartla AYNI turetme noktasindan aliyor (12 Agu, Okan karari); nobetci: "
           "tools/ilan-tutari-kapisi.py")
    try:
        ham = (p.get("fiyat") or "").strip()
        eski_taban = build.price_number(ham)                 # ESKI ureteç kurali
        yeni_taban = build.ilan_tl_metni(build.vitrin_kurus(p))   # kartla AYNI nokta
        aralikli = build.malzeme_aralikli_mi(p)
        tavan = build.ilan_tl_metni(build.en_yuksek_kurus(p)) if aralikli else None
        if tavan == yeni_taban:
            tavan = None                                     # aralik acilmadi
    except Exception:
        return (), ()
    metin, deger = [], []
    if aralikli and tavan:
        metin.append(('"offers":{"@type":"Offer",', '"offers":{"@type":"AggregateOffer",',
                      ger + " — JSON-LD metin kopyasi (@type)"))
        deger.append(("Offer", "AggregateOffer", ger + " — JSON-LD @type yapragi"))
    if eski_taban and yeni_taban:
        if aralikli and tavan:
            metin.append(
                ('"price":"%s","priceValidUntil"' % eski_taban,
                 '"price":"%s","lowPrice":"%s","highPrice":"%s","offerCount":%d,'
                 '"priceValidUntil"' % (yeni_taban, yeni_taban, tavan,
                                        len(build.FILAMENT_SIRA)),
                 ger + " — JSON-LD metin kopyasi (aralik)"))
        elif eski_taban != yeni_taban:
            metin.append(('"price":"%s"' % eski_taban, '"price":"%s"' % yeni_taban,
                          ger + " — JSON-LD metin kopyasi (taban)"))
        if eski_taban != yeni_taban:
            deger.append((eski_taban, yeni_taban, ger + " — JSON-LD price yapragi"))
    return tuple(metin), tuple(deger)


def cikarim_kaybi(eski_html, yeni_html, beyan_tablosu=None, eslesen_kovasi=None,
                  deger_beyani=()):
    """🔴 EKSEN 1'IN IDDIASI (3 Agu'da DARALTILDI, gevsetilmedi):
    "eski sayfadan CIKARILABILEN hicbir sey kaybolmayacak ya da DEGISMEYECEK".

    NEDEN DEGISTI: eski hali `iskelet(eski) == iskelet(yeni)` idi — HAM BAYT esitligi.
    Kiyas nesnesi git gecmisindeki (yapisal olarak ESKI) uretici oldugu icin, o
    commit'ten bu yana yapilan HER MESRU icerik degisikligi de bu eksende "kayip" gibi
    gorunuyordu; eksen 2'nin BILEREK_DEGISEN muafiyet listesi tam da bu yuzden buyumustu.
    Bayt-esitligi bir CIKARIM iddiasi degildir; olculmesi gereken sey kayiptir.

    NE OLCULUR (hepsi KAYIP/DEGISIM yonunde, EKLEME serbest DEGIL — asagiya bak):
      * JSON-LD: eski agactaki HER (yol, deger) yapragi yenide de AYNEN bulunmali
        (fiyat, sku, brand, offers, breadcrumb, image). EKLEME serbest.
      * <title> · <meta name=...> · canonical: TAM esitlik (ekleme de degisim sayilir).
      * gorunur METIN: TAM esitlik — "vaat" metni ne kaybolur ne degisir. TEK istisna
        BILEREK_DEGISEN_METIN'de TEK TEK beyan edilen (ESKI -> YENI) donusumlerdir;
        beyanlar ESKI metne uygulandiktan SONRA esitlik YINE aranir, yani bir beyan
        ikinci bir (beyan edilmemis) degisikligi MASKELEYEMEZ.
      * <img src>: eski her gorsel yenide de olmali.
      * <a href>: eski her baglanti yenide de olmali; YOLU ayni olmali ve eski
        sorgu parametrelerinin HEPSI ayni DEGERLE durmali. YENI parametre EKLENEBILIR
        (kapsam zenginlestirmesi) — bu tek serbestlik ve BILEREK dar: parametre
        DEGERINI degistiren mutant (marka=Volvo Penta -> marka=Volvo) KIRMIZI yanar.
    Doner: bulgu listesi (bos = temiz)."""
    bulgu = []
    # DEGER ESDEGERLIGI (11 Agu): TEK TEK beyan edilen (ESKI deger -> YENI deger) ciftleri.
    # 🔴 DAR: yalniz TAM ESIT degerler eslenir (alt dize / joker YOK) -> beyan edilen cift
    # disindaki her degisiklik yine KIRMIZI yanar. Ciftler build fonksiyonundan TURETILIR.
    _esd = set()
    for _e, _y, _g in deger_beyani:
        _esd.add((_e, _y))

    def _esdeger(eski_deger, yeni_deger):
        return (eski_deger, yeni_deger) in _esd

    e_yap = dict(_yapraklar(_ldjson(eski_html)))
    y_yap = dict(_yapraklar(_ldjson(yeni_html)))
    for yol, deger in e_yap.items():
        if yol not in y_yap:
            bulgu.append("JSON-LD yapragi KAYIP: %s=%r" % (yol, deger))
        elif y_yap[yol] != deger and not _esdeger(deger, y_yap[yol]):
            bulgu.append("JSON-LD yapragi DEGISTI: %s: %r -> %r" % (yol, deger, y_yap[yol]))

    if _TITLE_RE.findall(eski_html) != _TITLE_RE.findall(yeni_html):
        bulgu.append("<title> degisti")
    if sorted(_META_RE.findall(eski_html)) != sorted(_META_RE.findall(yeni_html)):
        bulgu.append("<meta name=...> kumesi degisti")
    if _CANON_RE.findall(eski_html) != _CANON_RE.findall(yeni_html):
        bulgu.append("canonical degisti")

    # Beyanlar ESKI metne uygulanir, sonra TAM ESITLIK yine aranir (bkz. giris kurali 3).
    e_metin, eslesen = _beyan_uygula(_duz_metin(eski_html), beyan_tablosu)
    if eslesen_kovasi is not None:
        eslesen_kovasi.update(eslesen)
    # 🔴 KIYAS BOSLUK-NORMALIZE METIN UZERINDEN (tablo sozlesmesinin zaten SOYLEDIGI sey:
    # "Bosluk serbest yazilir; kiyas normalize edilmis (tek bosluk) metin uzerinden
    # yapilir"). Uygulama bunu beyan CERRAHISINDEN SONRA yapmiyordu: bir blogu SILEN beyan
    # arkasinda cift bosluk birakiyor ve iki taraf KELIMESI KELIMESINE ayni olsa bile
    # "GORUNUR METIN degisti" doguyordu. Normalize etmek hicbir KELIME degisikligini
    # gizlemez (yalniz bosluk sayisini esitler); kapinin gucu DEGISMEZ.
    if _norm(e_metin) != _norm(_duz_metin(yeni_html)):
        bulgu.append("GORUNUR METIN degisti")

    e_img, y_img = _IMGSRC_RE.findall(eski_html), set(_IMGSRC_RE.findall(yeni_html))
    for u in e_img:
        if u not in y_img:
            bulgu.append("<img src> KAYIP: %s" % u[:80])

    y_bag = _baglantilar(yeni_html)
    for yol, par in _baglantilar(eski_html):
        eslesen = [p for (y, p) in y_bag if y == yol]
        if not eslesen:
            bulgu.append("<a href> YOLU KAYIP: %s" % yol[:80])
            continue
        if not any(all(p.get(ad) == deger or _esdeger(deger, p.get(ad))
                       for ad, deger in par.items()) for p in eslesen):
            bulgu.append("<a href=%s> sorgu parametresi KAYIP/DEGISTI: eski=%r yeni=%r"
                         % (yol[:50], par, eslesen[:2]))
    return bulgu


def js_govdeleri(html):
    return [m.group(2) for m in _SCRIPT_RE.finditer(html) if _js_mi(m.group(1))]


def css_govdeleri(html):
    return _STYLE_RE.findall(html)


def satir_cantasi(metin):
    """Sirali olmayan 'kayip/eklenti var mi' olcusu: bosluk-normalize edilmis, bos
    olmayan satirlarin cok-kumesi. Blok sayfadan cikip dosyaya tasinirken SIRA degisir
    ama HICBIR SATIR kaybolmaz/eklenmez — olculen iddia budur."""
    from collections import Counter
    return Counter(p for p in (s.strip() for s in metin.split("\n")) if p)


def urun_verisi(html):
    return dict((m.group(1), m.group(2)) for m in _URUN_VERI_RE.finditer(html))


# --------------------------------------------------------------------- eski uretici
def git(*args):
    p = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


REFERANS_DOSYASI = os.path.join(TOOLS, "varlik-referans.json")


def _kesif_ref():
    """`varlik_adres`i ICERMEYEN en son tools/build.py commit'i — TOHUM kesfi.

    Bu, kapinin KURULUS referansidir. Artik TEK BASINA kullanilmaz (bkz. eski_ref):
    o olay bir daha OLMAYACAGI icin sonuc SABIT bir SHA'ya donmustur."""
    log = git("log", "--format=%H", "-n", "500", "--", "tools/build.py")
    if not log:
        return None
    for sha in log.split():
        icerik = git("show", sha + ":tools/build.py")
        if icerik is None:
            continue
        if "varlik_adres" not in icerik:
            return sha
    return None


KAYIT_YOK = "__DOSYA_YOK__"   # dosya HIC yok: mesru tohum hali, RED DEGIL


def _ref_cozulur(ref):
    """SHA bu depoda bir commit'e cozulebiliyor mu (cozulmuyorsa kayit GECERSIZ)."""
    p = subprocess.run(["git", "-C", ROOT, "cat-file", "-e", ref + "^{commit}"],
                       capture_output=True)
    return p.returncode == 0


def kayit_hukmu(ham, ref_cozulur=None):
    """🔴 KAYIT GECERLILIGININ TEK KANONIK HUKMU. Baska hicbir yerde ikinci bir
    ayristirma/gecerlilik kurali YAZILMAZ — cagiran taraf bu fonksiyonun GEREKCESINI okur.

    NEDEN TEK YER (olculdu, 8 Agu 2026): gecerlilik once IKI ayri yerde, IKI ayri kuralla
    tanimliydi (burada dict+str+len>=7; main()'de kendi yeniden-ayristirmasi). Aradaki
    bosluktan IKI sekil FAIL-OPEN geciyordu: (a) `"ref":"abc"` (kisa dize) -> kapi rc=0
    veriyor ve ekrana `KAYITLI aa1146605f` YAZIYORDU (yanlis beyan), (b) kayit bir JSON
    DIZISI -> rc=0 ve "kayit dosyasi YOK" diyordu (dosya VARDI).
    [[ikiz-tanim-sessiz-ayrisma]] / [[kabul-araligi-karsilastirma-araligi]] sinifi.
    Bugun gorunmuyordu cunku tohum ile kayit AYNI SHA; ilk gercek tazelemeden SONRA bozuk
    bir `ref` kapiyi SESSIZCE tohuma geri sarardi — dalin var olus sebebinin tersi.

    Doner: (kayit, gerekce).
      · (kayit, None)          -> GECERLI
      · (None, KAYIT_YOK)      -> dosya yok; tohum hali MESRU (red degil)
      · (None, "…")            -> GECERSIZ; gerekce cagirana AYNEN gider (rc=2)
    `ham` None ise dosya yok demektir. `ref_cozulur` yalniz test icin enjekte edilir."""
    if ham is None:
        return None, KAYIT_YOK
    try:
        k = json.loads(ham)
    except Exception as e:
        return None, "JSON ayristirilamadi (%s)" % str(e)[:70]
    if not isinstance(k, dict):
        return None, "kayit bir JSON NESNESI degil (%s)" % type(k).__name__
    if "ref" not in k:
        return None, "'ref' alani YOK"
    if not isinstance(k["ref"], str):
        return None, "'ref' bir dize DEGIL (%s)" % type(k["ref"]).__name__
    if len(k["ref"]) < 7:
        return None, "'ref' cok kisa (%d karakter, en az 7)" % len(k["ref"])
    coz = ref_cozulur or _ref_cozulur
    if not coz(k["ref"]):
        return None, "'ref' bu depoda bir commit'e cozulemiyor (%s)" % k["ref"][:16]
    return k, None


def referans_kaydi():
    """Kayitli kiyas referansi. Hukum kayit_hukmu()'nden gelir; BURADA kural YOK."""
    try:
        with io.open(REFERANS_DOSYASI, encoding="utf-8") as f:
            ham = f.read()
    except IOError:
        ham = None
    except Exception as e:
        return None, "kayit dosyasi OKUNAMADI (%s)" % str(e)[:70]
    return kayit_hukmu(ham)


def eski_ref():
    """KIYAS REFERANSI — kayitli, TAZELENEBILIR ve GORUNUR.

    🔴 NEDEN DEGISTI (olculdu, 8 Agu 2026): referans "`varlik_adres` icermeyen en son
    build.py" kesfiyle bulunuyordu. O olay 2 Agu'da BIR KEZ oldu ve bir daha olmayacak
    -> kesif her kosumda AYNI SHA'yi (aa1146605f) donduruyor, yani referans FIILEN
    DONMUS. Sonuc: kapi zamanla "varlik tasimasi kayipsiz mi?" sorusunu degil "sayfa
    2 Agu'dan beri degisti mi?" sorusunu olcuyor ([[anahat-referans-tautolojisi]],
    [[bayat-kabul-testi]]). Bugun bu, her mesru icerik degisikliginde beyan girisi
    yazmayi zorunlu kiliyor ve iki kez TUM YAYINI durdurdu.

    YENI YORDAM — referans DONMUS DEGIL, KAYITLI ve TAZELENEBILIR:
      · Kaynak: tools/varlik-referans.json (IZLENEN dosya) — elle SHA gomulu DEGIL,
        `--referans-tazele` yordami yazar ve her tazeleme bir COMMIT'tir (gorunur).
      · Tazeleme ancak kapi O AN YESILKEN yapilabilir: yani referans yalnizca
        "kayipsizligi kanitlanmis" bir noktaya ilerler. Kirmizi durumu YUTMAZ.
      · Dosya yoksa TOHUM kesfine dusulur (geriye donuk uyum) ve bu GORUNUR bicimde
        raporlanir. Kayit VAR ama GECERSIZ ise hukum OLCULEMEDI'dir (rc=2): olcum yine
        tohuma karsi kosar (sayilar gorunsun diye) ama YESIL HUKMU VERILMEZ.
      · Gecerlilik kurali TEK yerdedir: kayit_hukmu(). Cagiran taraf kendi ayristirmasini
        YAPMAZ, o fonksiyonun GEREKCESINI okur.
      · Her kosum referansin YASINI ve birikmis beyan sayisini BASAR -> bayatlik
        gorunur kalir, sessizce buyumez.
    Kapinin GUCU DEGISMEZ: tazelemeden SONRA yapilan her beyansiz icerik degisikligi
    yine KIRMIZI yanar; tazeleme yalnizca ZATEN kanitlanmis gecmisi taban yapar."""
    kayit, _gerekce = referans_kaydi()
    if kayit:
        return kayit["ref"]
    return _kesif_ref()


def eski_kok_kur(tmp, ref):
    """`ref`teki build.py'yi tmp'ye acar; diger girdileri guncel ROOT'a symlink.

    Kiyas yalniz varlik tasimasindan onceki URETICIYI sabitler. Tum `tools/` agacini
    eski ref'ten almak, sonradan genisleyen taksonomi gibi build.py disi kurallari da
    geri sarar ve varlik tasimasiyla ilgisiz sahte bayt farklari uretir.
    """
    p = subprocess.run(["git", "-C", ROOT, "archive", ref, "tools/build.py"],
                       capture_output=True)
    if p.returncode != 0:
        return False
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as t:
        t.extractall(tmp)
    tmp_tools = os.path.join(tmp, "tools")
    for ad in os.listdir(TOOLS):
        if ad == "build.py":
            continue
        os.symlink(os.path.join(TOOLS, ad), os.path.join(tmp_tools, ad))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(tmp, ad))
    return os.path.isfile(os.path.join(tmp, "tools", "build.py"))


_SURUCU = u'''import json, os, sys
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(KOK, "tools"))
import build
idler = json.load(open(sys.argv[1], encoding="utf-8"))
with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
    urunler = json.load(f)
harita = dict((p["id"], p) for p in urunler)
cikti = dict((i, build.render_product(harita[i], urunler, None)) for i in idler)
with open(sys.argv[2], "w", encoding="utf-8") as f:
    json.dump(cikti, f)
'''


def eski_render(tmp, idler):
    """ESKI build.py'yi AYRI SURECTE kosturur (modul adlari carpismasin)."""
    surucu = os.path.join(tmp, "_surucu.py")
    with io.open(surucu, "w", encoding="utf-8") as f:
        f.write(_SURUCU)
    gid = os.path.join(tmp, "_idler.json")
    gout = os.path.join(tmp, "_cikti.json")
    with io.open(gid, "w", encoding="utf-8") as f:
        json.dump(idler, f)
    p = subprocess.run([sys.executable, surucu, gid, gout], capture_output=True, text=True)
    if p.returncode != 0:
        return None, (p.stderr or "")[-1200:]
    with io.open(gout, encoding="utf-8") as f:
        return json.load(f), ""


# --------------------------------------------------------------------- ornek
EKSENLER = (
    ("parametrik", lambda p: bool(p.get("parametrik"))),
    ("semali", lambda p: bool(build.konf_sema(p.get("id")))),
    ("konfigurlu", lambda p: bool(p.get("konfigur"))),
    ("fiziksel", lambda p: bool(p.get("tur"))),
    ("altkategorili", lambda p: bool(p.get("altkategori"))),
    ("lisansli", lambda p: bool(p.get("lisans"))),
    ("gorselsiz", lambda p: not p.get("gorseller")),
    ("markasiz", lambda p: not p.get("marka")),
    ("sade", lambda p: True),
)


def ornek_sec(urunler, hedef):
    secim, gorulen = [], set()
    for ad, kosul in EKSENLER:
        for p in urunler:
            if p["id"] in gorulen:
                continue
            try:
                uygun = kosul(p)
            except Exception:
                uygun = False
            if uygun:
                secim.append((ad, p))
                gorulen.add(p["id"])
                break
    adim = max(1, len(urunler) // max(1, hedef))
    i = 0
    while len(secim) < hedef and i < len(urunler):
        p = urunler[i]
        if p["id"] not in gorulen:
            secim.append(("dolgu", p))
            gorulen.add(p["id"])
        i += adim
    return secim[:hedef]


# --------------------------------------------------------------------- kosum
def kendini_test():
    """🔴 EKSEN 1 MUTASYON KANITI — `cikarim_kaybi` GERCEK bir kaybi TEK BASINA yakiyor mu?

    Kapiyi DARALTMAK gevsetmekten ayirt edilemezse bu is bir susturmadir. Bu yuzden kanit
    ANLATILMAZ, KOSULUR: gercek bir urun sayfasi uretilir, kopyasina TEK bir kayip
    enjekte edilir ve `cikarim_kaybi` o kaybi yakalamak ZORUNDADIR. Yaninda KONTROL
    mutantlari durur (davranisi degistirmeyen degisiklikler YESIL kalmali) — yoksa
    "her seye kirmizi yak" da bu bataryayi gecerdi.
    Kabul olcutu cikis kodu DEGIL, olculen iddia sayisi + isaret sarti."""
    with io.open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    # Cok markali + fiyatli + gorselli bir MARIN urunu: hem `?marka=` cipi hem JSON-LD
    # offers hem gorsel tasir (butun eksenler tek fikstürde olculsun).
    aday = [p for p in urunler
            if (p.get("kategori") or "") == "Marin" and len(p.get("marka") or []) >= 2
            and (p.get("fiyat") or "").strip() and (p.get("gorseller") or [])]
    if not aday:
        print("OLCULEMEDI: kendini-test icin cok markali Marin urunu bulunamadi")
        return 2
    sayfa = iskelet(build.render_product(aday[0], urunler, None))
    if "brand-chip" not in sayfa or '"@type":"Product"' not in sayfa:
        print("OLCULEMEDI: fikstur sayfasi beklenen yuzeyi tasimiyor "
              "(marka cipi / Product JSON-LD)")
        return 2

    def ilk_deger(desen):
        m = re.search(desen, sayfa)
        return m.group(0) if m else None

    fiyat = ilk_deger(r'"price":"[^"]+"')
    gorsel = _IMGSRC_RE.findall(sayfa)
    marka_link = ilk_deger(r'<a class="brand-chip" href="/\?[^"]*marka=[^"]*">')
    # 🔴 Metin ornegi HAM HTML'den alinir. Ilk yazimda `_duz_metin()` ciktisindan
    # aliniyordu; o metin ham HTML'de GECMEDIGI icin `replace` hicbir sey degistirmiyor,
    # mutant FIILEN UYGULANMIYOR ve vaka sahte-yesil geciyordu ([[mutasyon-diske-yazma-tuzagi]]
    # ile ayni sinif). Asagidaki "mutant fiilen uygulandi mi" suzgeci de bu yuzden var.
    # <title>/<meta> icerigi HARIC tutulur: aksi halde "metin kaybi" vakasi aslinda
    # title eksenini olcer ve iki vaka AYNI seyi kanitlar (ayirt edicilik kaybi).
    # Aday metin GOVDEDEN secilir: <script> (JSON-LD dahil) ve <title> DISLANIR, yoksa
    # vaka aslinda JSON-LD ya da title eksenini olcer ve ayirt ediciligini kaybeder.
    baslik_metni = (_TITLE_RE.findall(sayfa) or [""])[0]
    govde = _TITLE_RE.sub("", _SCRIPT_RE.sub("", sayfa))
    metin_ornegi = None
    for g in re.findall(r">([^<>]{60,})<", govde):
        if g.strip() and g not in baslik_metni:
            metin_ornegi = g
            break

    vakalar = []

    def vaka(ad, yeni_sayfa, beklenen, iz=None):
        """`iz` = bu vakanin KANITLAMASI gereken EKSENIN bulgu imzasi.

        Neden var: yalniz KIRMIZI/YESIL bakan bir batarya, katmanlarin VEYA'sini olcer —
        bir vaka BASKA bir eksenden kirmizi alip kendi eksenini kanitlamis GORUNEBILIR
        (or. bir oznitelik mutanti yalnizca "gorunur metin" kolundan kirmizi alir ve
        oznitelik kolu kor kalir). `iz` verilmis KIRMIZI vakada bulgu listesi BOS OLMAMALI
        ve imzayi TASIYAN en az bir bulgu bulunmali; aksi halde vaka BASARISIZ ve sebebi
        `YANLIS EKSEN` yazilir (teshis yanlis yere bakmasin). `iz` verilmezse bugunku
        davranis aynen korunur."""
        vakalar.append((ad, yeni_sayfa, beklenen, iz))

    if fiyat:
        vaka("JSON-LD fiyat KAYBI", sayfa.replace(fiyat, '"__x__":"0"', 1), "KIRMIZI",
             "JSON-LD yapragi KAYIP")
        vaka("JSON-LD fiyat DEGISIMI",
             sayfa.replace(fiyat, '"price":"999999"', 1), "KIRMIZI",
             "JSON-LD yapragi DEGISTI")
    # Cip blogu tumden silinince YOL (`/`) hala baska baglantilarda durur; kaybolan sey
    # o baglantinin SORGU parametreleridir — imza olculen kola gore secildi.
    vaka("marka cipi BLOGU DUSTU", re.sub(r'<a class="brand-chip"[^>]*>[^<]*</a>', "", sayfa),
         "KIRMIZI", "sorgu parametresi KAYIP/DEGISTI")
    if marka_link:
        # 🔴 ASIL VAKA: kapsam parametresi EKLEMEK serbest, DEGERI degistirmek DEGIL.
        vaka("marka= parametresinin DEGERI degisti (katlanmis etikete kaydi)",
             sayfa.replace(marka_link, re.sub(r"marka=[^\"]*", "marka=Volvo", marka_link), 1),
             "KIRMIZI", "sorgu parametresi KAYIP/DEGISTI")
        vaka("KONTROL: linke kapsam parametresi EKLENDI (mesru zenginlestirme)",
             sayfa.replace(marka_link, marka_link.replace("/?", "/?kategori=Marin&"), 1),
             "YESIL")
    if metin_ornegi:
        vaka("GORUNUR METIN (vaat/kisit cumlesi) DUSTU",
             sayfa.replace(metin_ornegi, "", 1), "KIRMIZI", "GORUNUR METIN degisti")
    vaka("<title> DEGISTI", _TITLE_RE.sub("<title>x</title>", sayfa, 1), "KIRMIZI",
         "<title> degisti")
    vaka("canonical DUSTU", _CANON_RE.sub("", sayfa, 1), "KIRMIZI", "canonical degisti")
    if gorsel:
        # 🔴 TUM GECISLER: hedef URL sayfada BIRDEN COK `<img src>` icinde gecer (galeri ana
        # gorseli + ayni gorselin kucuk resmi). `count=1` yalniz ILKINI siliyordu; URL
        # `cikarim_kaybi` icindeki yeni-gorsel KUMESINDE hala durdugu icin "<img src> KAYIP"
        # bulgusu DOGMUYOR ve vaka sahte-YESIL geciyordu. Kayip GERCEKTEN olsun diye her
        # gecis silinir. `src="<url>"` deseni JSON-LD (`"image":[...]`) ya da og:/twitter:
        # (`content="..."`) yuzeyinde GECMEZ; olculdu — bu mutant o eksenleri kirletmez,
        # `iz` sarti da zaten ayni eksenden kirmizi almayi zorunlu kilar.
        vaka("<img src> DUSTU", sayfa.replace('src="%s"' % gorsel[0], 'src=""'), "KIRMIZI",
             "<img src> KAYIP")
    vaka("meta description DEGISTI",
         re.sub(r'(<meta\s+name="description"\s+content=")[^"]*(")', r"\1x\2", sayfa, count=1),
         "KIRMIZI", "<meta name=...> kumesi degisti")
    vaka("KONTROL: fazladan bosluk/satir sonu", sayfa.replace("\n", "\n\n"), "YESIL")
    vaka("KONTROL: hicbir sey degismedi", sayfa, "YESIL")

    print("EKSEN 1 KENDINI-TEST — `cikarim_kaybi` mutasyon bataryasi")
    basarisiz = []
    kirmizi_vaka = 0
    for ad, mutant, beklenen, iz in vakalar:
        # MUTANT FIILEN UYGULANDI MI: degismeyen bir "mutant" her zaman yesil gecer ve
        # bataryayi sessizce bosaltir. Kontrol vakasi "hicbir sey degismedi" HARIC.
        if beklenen == "KIRMIZI" and mutant == sayfa:
            print("  HATA %-58s MUTANT UYGULANMADI (sayfa DEGISMEDI)" % ad)
            basarisiz.append(ad + " [uygulanmadi]")
            kirmizi_vaka += 1
            continue
        # === 27 AGU 2026 (K323) — BEYAN TABLOSU IZOLASYONU ======================
        # 🔴 OLCULEN ARIZA: cagri `cikarim_kaybi(sayfa, mutant)` idi, yani beyan tablosu
        # None geciyordu ve `_beyan_uygula` MODUL CAPINDAKI BILEREK_DEGISEN_METIN'i
        # devreye sokuyordu. O tablo ESKI->YENI donusumunu YALNIZ ESKI tarafa uygular —
        # eksen 2'de DOGRUDUR (eski uretecin sayfasi ile yeninin kiyasi), ama BU
        # BATARYADA IKI TARAF DA AYNI GUNCEL URETECTEN gelir: aralarinda beyan edilmis
        # bir degisiklik YOKTUR. Sonuc: sayfa bir beyanin ESKI metnini tasiyorsa eski
        # taraf yeniden yazilir, yeni taraf yazilmaz ve KIYAS ASIMETRIK olur.
        # OLCULDU (27 Agu, fikstur sayfasi): tablo 3 girisli, ikisinin ESKI'si sayfada
        # geciyor; #1 (10 Agu teslim beyani) fiiliyen atesliyor ve YENI'si sayfada YOK
        # (maskeleme kolu bu yuzden devreye girmiyor) ->
        #     cikarim_kaybi(sayfa, sayfa, None) -> ['GORUNUR METIN degisti']
        #     cikarim_kaybi(sayfa, sayfa, ())   -> []
        # Yani kapi HICBIR SEY DEGISMEDIGINDE kirmizi yakiyordu: UC KONTROL vakasi birden
        # (hicbir-sey-degismedi · fazladan-bosluk · mesru-kapsam-parametresi) yanlis-KIRMIZI
        # aliyor, olduruculerin bir kismi da kendi ekseni yerine bu sahte metin bulgusundan
        # kirmizi aliyordu. SAHTE KIRMIZI GERCEK KIRMIZIYI GORUNMEZ YAPAR.
        # COZUM KAPIYI GEVSETMEZ: tablo BOS gecilir; oldurucu vakalar sayfayi GERCEKTEN
        # degistirdigi icin aynen kirmizi kalir (olculdu: 9/9). Eksen 2'nin uretim
        # kiyasinda tablo AYNEN kullanilmaya devam eder — burada degisen sey yalnizca
        # SELF-TEST'in kendi kiyasini izole etmesidir.
        bulgu = cikarim_kaybi(sayfa, mutant, ())
        gercek = "KIRMIZI" if bulgu else "YESIL"
        if beklenen == "KIRMIZI":
            kirmizi_vaka += 1
        ok = gercek == beklenen
        # EKSEN IMZASI: vaka KENDI eksenini mi olcuyor? Kirmizi olmak yetmez — bulgu
        # listesi bu vakanin iddia ettigi kolun imzasini TASIMALI.
        sebep = ""
        if beklenen == "KIRMIZI" and iz and not any(iz in b for b in bulgu):
            ok = False
            sebep = "YANLIS EKSEN: beklenen imza YOK -> %s" % iz
        print("  %-4s %-58s beklenen=%-7s olculen=%-7s %s"
              % ("OK" if ok else "HATA", ad, beklenen, gercek,
                 sebep or (bulgu[0][:70] if bulgu else "")))
        if not ok:
            basarisiz.append(ad + (" [YANLIS EKSEN]" if sebep else ""))
    # === 27 AGU 2026 (K323) — IZOLASYON NOBETCISI (kol yerinde MUTANT) =============
    # Yukaridaki `()` tek karakterlik bir duzeltmedir ve tam da bu yuzden SESSIZCE geri
    # alinabilir. Nobetci onu YERINDE olcer: ayni sayfa iki tarafa da verilir ve
    #   (a) IZOLE kiyas BOS bulgu vermeli (kolun kendisi),
    #   (b) MODUL TABLOSUYLA ayni kiyas bulgu URETMELI — yani kaldirilan asimetri
    #       GERCEKTEN vardi (hedef-kol atfi: bu uretilmiyorsa (a) bir sey KANITLAMAZ).
    # (b) fikstur sayfasinin bir beyanin ESKI metnini tasimasina baglidir; tasimiyorsa
    # mutant yonu OLCULEMEZ ve bu ADIYLA basilir — sessiz yesil YOK.
    izole = cikarim_kaybi(sayfa, sayfa, ())
    tablolu = cikarim_kaybi(sayfa, sayfa, None)
    if izole:
        print("  HATA %-58s IZOLE kiyas BOS olmali -> %s"
              % ("K323 BEYAN TABLOSU IZOLASYONU", izole[:2]))
        basarisiz.append("K323 izolasyon [izole kiyas kirmizi]")
    elif not tablolu:
        print("  OLCULEMEDI %-49s mutant yonu uretilemedi: fikstur sayfasi hicbir "
              "beyanin ESKI metnini tasimiyor" % "K323 BEYAN TABLOSU IZOLASYONU")
    else:
        print("  OK   %-58s izole=[] · modul tablosuyla=%s (asimetri GERCEK)"
              % ("K323 BEYAN TABLOSU IZOLASYONU", tablolu[:1]))

    print()
    print("  vaka=%d (oldurucu=%d · kontrol=%d) · fikstur urun=%s"
          % (len(vakalar), kirmizi_vaka, len(vakalar) - kirmizi_vaka, aday[0]["id"]))
    if kirmizi_vaka < 6 or (len(vakalar) - kirmizi_vaka) < 3:
        print("KIRMIZI: batarya YETERSIZ (oldurucu>=6 ve kontrol>=3 sarti)")
        return 1
    if basarisiz:
        print("KIRMIZI: %d vaka beklentiyi tutmadi -> %s" % (len(basarisiz), basarisiz))
        return 1
    print("OK: eksen 1 daraltmasi mutasyonla KANITLANDI "
          "(her oldurucu vaka TEK BASINA kirmizi, kontrol vakalari yesil).")
    return 0


_B_ESKI = "<p>Analiz cerezleri kullaniyoruz.</p><p>Kargo ayni gun cikar.</p>"
_B_YENI = "<p>Analiz ve reklam cerezleri kullaniyoruz.</p><p>Kargo ayni gun cikar.</p>"
_B_TABLO = (("Analiz cerezleri kullaniyoruz.",
             "Analiz ve reklam cerezleri kullaniyoruz.", "fikstur"),)

# ONEK FIKSTURU (10 Agu 2026): ESKI metnin YENI metnin ONEKI oldugu beyan sekli —
# "YENI = ESKI + eklenen cumle". Yukaridaki B fiksturunde ESKI ile YENI ORTADAN ayrisir,
# yani o fikstur duz `str.replace`in idempotent OLMAMASINI GOREMEZ; bu sekil gormeden
# kalinca uc KONTROL mutanti birden yanlis-KIRMIZI yandi. Metin UYDURMADIR (gercek
# beyan cumlesi buraya KOPYALANMAZ; tek kaynak build.BEYAN).
_BO_ESKI = "<p>Urun hazirlanir.</p>"
_BO_YENI = "<p>Urun hazirlanir. Kargo ertesi gun cikar.</p>"
_BO_IKI = "<p>Urun hazirlanir. Kargo ertesi gun cikar.</p><p>Kasa rengi mavi.</p>"
_BO_TABLO = (("Urun hazirlanir.",
              "Urun hazirlanir. Kargo ertesi gun cikar.", "onek fiksturu"),)


def beyan_mekanizmasi_dogrula():
    """GORUNUR-METIN BEYAN YUZEYININ KENDI NOBETCISI — HER kosumda calisir.

    🔴 NEDEN VARSAYILAN KOLDA: bu yuzey bir MUAFIYET yuzeyidir; sessizce "her metin
    degisikligini yut" haline donerse kapi olur ve kimse gormez. Fikstur bataryasi
    `--kendini-test` kolunda dursaydi CI'da HIC kosmazdi (deploy.yml yalniz bayraksiz
    cagirir) — nobetci nobetsiz kalirdi ([[nobetci-cagri-satiri-nobetsiz]]).

    AYIRT EDICI CIFTLER (tek yonlu batarya bu yuzeyi kanitlayamaz):
      B1/B2 : AYNI metin degisikligi — beyanliyken temiz, beyansizken KIRMIZI.
      B3    : beyan + IKINCI (beyan edilmemis) degisiklik -> KIRMIZI. Maskeleme ekseni:
              beyan bir degisikligi tolere eder, YANINDAKINI GIZLEMEZ.
      B4    : beyan var ama yeni metin BEYAN EDILENDEN farkli -> KIRMIZI (beyan serbest
              gecis kartina donmez).
      B5    : KONTROL — degisiklik yok, tablo bos -> temiz.
      B6    : beyan var ama karsiligi olan degisiklik SAYFADA YOK -> KIRMIZI (bayat beyan
              sayfa duzeyinde de fail-loud; suite duzeyi hijyen 1c'de).
    Doner: basarisiz vaka adlari (bos = saglam)."""
    dusen = []

    def vaka(ad, eski, yeni, tablo, beklenen):
        gercek = "KIRMIZI" if cikarim_kaybi(eski, yeni, tablo) else "TEMIZ"
        if gercek != beklenen:
            dusen.append("%s (beklenen=%s olculen=%s)" % (ad, beklenen, gercek))

    ikinci = _B_YENI.replace("Kargo ayni gun cikar.", "Kargo ertesi gun cikar.")
    vaka("B1 beyanli metin degisikligi", _B_ESKI, _B_YENI, _B_TABLO, "TEMIZ")
    vaka("B2 AYNI degisiklik BEYANSIZ", _B_ESKI, _B_YENI, (), "KIRMIZI")
    vaka("B3 beyan + ikinci beyansiz degisiklik", _B_ESKI, ikinci, _B_TABLO, "KIRMIZI")
    vaka("B4 yeni metin beyan edilenden farkli", _B_ESKI,
         _B_YENI.replace("reklam", "reklam ve olcum"), _B_TABLO, "KIRMIZI")
    vaka("B5 KONTROL degisiklik yok, tablo bos", _B_ESKI, _B_ESKI, (), "TEMIZ")
    vaka("B6 beyanin karsiligi sayfada YOK (bayat)", _B_ESKI, _B_ESKI, _B_TABLO, "KIRMIZI")
    # B9-B11: ESKI'nin YENI'nin ONEKI oldugu sekil (bkz. _BO_* fikstur gerekcesi).
    #   B9  : IDEMPOTENS — iki taraf da ZATEN YENI ise donusum HICBIR SEY degistirmemeli.
    #   B10 : AYIRT EDICI KONTROL — ciplak ESKI hala YENI'ye donusmeli (duzeltme
    #         "beyani hic uygulama"ya donmesin; o hal B9'u da gecerdi).
    #   B11 : MASKELEME EKSENI — iki taraf da YENI iken YANINDAKI beyansiz degisiklik
    #         yine KIRMIZI (idempotens duzeltmesi genel muafiyete donmesin).
    vaka("B9 ONEK beyani: iki taraf da ZATEN YENI (idempotens)",
         _BO_YENI, _BO_YENI, _BO_TABLO, "TEMIZ")
    vaka("B10 KONTROL ONEK beyani: ciplak ESKI hala YENI'ye donusuyor",
         _BO_ESKI, _BO_YENI, _BO_TABLO, "TEMIZ")
    vaka("B11 ONEK beyani ikinci beyansiz degisikligi MASKELEMEZ",
         _BO_IKI, _BO_IKI.replace("mavi", "kirmizi"), _BO_TABLO, "KIRMIZI")

    # Eslesme kaydi 1c hijyeninin GIRDISIDIR: bozulursa bayat beyan gorunmez olur.
    _, eslesen = _beyan_uygula(_duz_metin(_B_ESKI), _B_TABLO)
    if eslesen != {0}:
        dusen.append("B7 eslesme kaydi bozuk: %r (beklenen {0})" % (eslesen,))
    _, bos = _beyan_uygula(_duz_metin("<p>ilgisiz</p>"), _B_TABLO)
    if bos:
        dusen.append("B8 eslesmeyen beyan eslesmis sayildi: %r" % (bos,))
    # B12: ONEK beyani ZATEN YENI metinde ESLESMIS SAYILMAZ. Sayilsaydi 1c bayat-beyan
    # hijyeni kor kalirdi: gecmisi tazelendikten sonra gereksizlesmis bir giris, hicbir
    # ciplak ESKI gecis kalmadigi halde "tutuyor" gorunup tabloda sessizce yaslanirdi.
    _, onek_bos = _beyan_uygula(_duz_metin(_BO_YENI), _BO_TABLO)
    if onek_bos:
        dusen.append("B12 ONEK beyani ZATEN YENI metinde eslesmis sayildi: %r" % (onek_bos,))
    # B13 KONTROL: ciplak ESKI gecis VARKEN eslesme kaydi DUSMEZ (B12 "hic eslesme
    # kaydetme"ye donmesin).
    _, onek_var = _beyan_uygula(_duz_metin(_BO_ESKI), _BO_TABLO)
    if onek_var != {0}:
        dusen.append("B13 ciplak ESKI'de eslesme kaydi bozuk: %r (beklenen {0})" % (onek_var,))
    return dusen


def referans_hukmu_dogrula():
    """KAYIT GECERLILIK HUKMUNUN KENDI NOBETCISI — HER kosumda calisir.

    🔴 NEDEN VAR: 8 Agu'da bu kolda IKI sekil FAIL-OPEN olctu ve bataryada onlari
    yakalayan HICBIR vaka yoktu; batarya bu yuzden yesil yandi. "Bozuk kayit" tek
    sekille denenirse yalniz o sekil nobetlenir — sinif kapanmaz
    ([[tekil-yama-sinifi-kapatmaz]]). Bes bozuk SEKIL de ayri vakadir.

    Ayirt edici kontrol (R1/R8): gecerli kayit KABUL edilmeli — yoksa "her kaydi reddet"
    hali de bu bataryayi yesil gecerdi ve kapi kullanilamaz olurdu.
    Doner: basarisiz vaka adlari (bos = saglam)."""
    coz = lambda r: r == "aa1146605f"                                    # noqa: E731
    dusen = []

    def vaka(ad, ham, beklenen):
        kayit, gerekce = kayit_hukmu(ham, ref_cozulur=coz)
        if beklenen == "KABUL":
            gercek = "KABUL" if kayit is not None and gerekce is None else "RED"
        elif beklenen == "YOK":
            gercek = "YOK" if gerekce == KAYIT_YOK else "DIGER"
        else:
            gercek = "RED" if (kayit is None and gerekce not in (None, KAYIT_YOK)) else "KABUL"
        if gercek != beklenen:
            dusen.append("%s (beklenen=%s olculen=%s gerekce=%r)"
                         % (ad, beklenen, gercek, gerekce))

    gecerli = '{"ref": "aa1146605f", "tazelendi": "2026-08-02"}'
    vaka("R1 gecerli kayit", gecerli, "KABUL")
    # 🔴 8 Agu'da FAIL-OPEN olcuLEN iki sekil:
    vaka("R2 'ref' cok kisa (\"abc\")", '{"ref": "abc"}', "RED")
    vaka("R3 kayit bir JSON DIZISI", '[{"ref": "aa1146605f"}]', "RED")
    # zaten kapali olan uc sekil (regresyon nobeti):
    vaka("R4 'ref' sayi", '{"ref": 12345}', "RED")
    vaka("R5 'ref' alani YOK", '{"tazelendi": "2026-08-02"}', "RED")
    vaka("R6 bozuk JSON metni", "{ bozuk ][", "RED")
    vaka("R7 dosya YOK (mesru tohum hali)", None, "YOK")
    vaka("R8 KONTROL gecerli kayit + fazladan alan",
         '{"ref": "aa1146605f", "not": "x", "onceki_ref": null}', "KABUL")
    vaka("R9 'ref' depoda cozulemiyor", '{"ref": "0123456789abcdef"}', "RED")
    return dusen


# --------------------------------------------------------------------- cikarim beyani
# 🔴 16 Agu 2026 — VARLIK KAPISININ KASITLI DEGISIKLIK KILIDI (spec: cikarim beyani).
# NEDEN: cikarim_kaybi() bulgulari bugun KOMPLE KIRMIZI; ama merge `4380e7c8` gibi
# kasitli degisiklikler (rel-card hedefleri + breadcrumb adresi) icin bir KAYIT
# mekanizmasi lazim. Bugun `--referans-tazele` kapi YESIL degilken REDDEDILIR — yani
# kasitli ama kanitlanmis bir degisikligi tabana almak icin kapinin kendi kirmizisini
# once gecmeniz, sonra tazelemeyi kosmaniz gerekir. Iki adim birbirine bagli olunca
# kanitlanmamis bir hal "taban" yapilabilir ([[tavuk-yumurta-referans]]). Beyan bunu
# ACIK + KAYITLI hale getirir: beyan dosyasi yoksa bugunku kati davranis AYNEN kalir
# (fail-closed); beyan dosyasi varsa KIRMIZI bulgularin her biri beyandaki kapsama VE
# urunler listesine giriyorsa tazeleme GEVER, girmezse REDDEDILIR (kismi gecis YOK).
# Bypass EKLENMEDI: `--tazele-zorla` gibi bir acil kapak YOK, beyan KAYITTIR muafiyet
# degil ([[yedek-dusus-beyani-deseni]]).
BEYAN_DOSYASI = os.path.join(TOOLS, "varlik-cikarim-beyani.json")
# Kapali kume: beyan `kapsam` alani yalniz bu degerleri kabul eder. Disari birakma
# kasten YOK — yeni kapsam acmak TEK KAYNAK degisiklik demek, kapinin tasarim karari.
BEYAN_KAPSA_KUMESI = frozenset({"breadcrumb-adresi", "rel-card-hedefleri"})


def _beyan_dosyasi_oku():
    """Beyan dosyasini oku. None donusu = dosya yok VEYA bozuk (fail-closed davranis).

    Bozuk dosya "bos" sayilmaz; cunku "bos" ile "yok" AYNI kapinin iki durumudur ve
    ayrimi sadece okuyucu yapabilir. Burada hata YUTULMAZ (hata mesaji rapora eklenir
    mekanizma dogrulamada) ama geri donus None olur ki kapinin varsayilan KATI davranisi
    AYNEN korunsun."""
    try:
        with io.open(BEYAN_DOSYASI, encoding="utf-8") as f:
            ham = f.read()
    except IOError:
        return None
    try:
        return json.loads(ham)
    except ValueError:
        return None


def _beyan_yapisi_gecerli_mi(veri):
    """Beyan dosyasinin BEYAN YAPISI (dosya = dict + beyanlar = dizi) gecerli mi?

    AYRIT EDICI: beyan dosyasi JSON Object OLMALI (`{"beyanlar":[...]}`). Dizi, dize,
    null, sayi vs. YANLIS tip — boyle bir dosya tek satirlik "beyan" gibi gorunup
    kapinin onay kapisini sessizce acmasin ([[ikiz-tanim-sessiz-ayrisma]]).

    Doner: (gecerli_mi, gerekce)."""
    if not isinstance(veri, dict):
        return False, "beyan dosyasi bir JSON NESNESI degil (%s)" % type(veri).__name__
    if "beyanlar" not in veri:
        return False, "beyan dosyasinda 'beyanlar' alani YOK"
    if not isinstance(veri["beyanlar"], list):
        return False, "'beyanlar' bir DIZI degil (%s)" % type(veri["beyanlar"]).__name__
    return True, None


def _beyan_kayit_gecerli_mi(kayit, ref):
    """TEK bir beyan kaydinin sema kontrolu. Doner: (uyar_mi, gerekce)."""
    if not isinstance(kayit, dict):
        return False, "kayit bir sozluk degil"
    for alan in ("ref", "kapsam", "urunler"):
        if alan not in kayit:
            return False, "'%s' alani YOK" % alan
    if not isinstance(kayit["ref"], str) or len(kayit["ref"]) < 7:
        return False, "'ref' gecersiz (%r)" % (kayit.get("ref"),)
    if not _ref_cozulur(kayit["ref"]):
        return False, "'ref' depoda cozulemiyor (%s)" % kayit["ref"][:10]
    if ref is not None and kayit["ref"] != ref:
        return False, "'ref' aktif ref'e esit degil (%s vs %s)" % (
            kayit["ref"][:10], (ref or "?")[:10])
    if not isinstance(kayit["kapsam"], list):
        return False, "'kapsam' bir dizi degil"
    if not kayit["kapsam"]:
        return False, "'kapsam' bos (blanket beyan)"
    kume = set(kayit["kapsam"])
    if not kume.issubset(BEYAN_KAPSA_KUMESI):
        return False, "'kapsam' kapali kumede degil (%s)" % sorted(kume - BEYAN_KAPSA_KUMESI)
    # Joker / blanket kontrolu (T4): "*" veya "hepsi" gibi blanket deger YASAK.
    for deger in kayit["kapsam"]:
        if not isinstance(deger, str) or deger.strip() in ("", "*", "hepsi", "tumu", "all"):
            return False, "'kapsam' blanket deger tasiyor (%r)" % (deger,)
    if not isinstance(kayit["urunler"], list):
        return False, "'urunler' bir dizi degil"
    return True, None


def _bulgu_beyan_edilemez_mi(bulgu, urun):
    """🔴 BEYAN EDILEMEZ ALANLAR (spec 4): beyan olsa bile KIRMIZI kalir.

    Sinif KAPALI: 6 alan — urunun kendi gorseli · canonical · siparis/WhatsApp ·
    urun basligi (title/h1) · fiyat · JSON-LD offers.

    Doner: (edilemez_mi, sebep). edilemez_mi=True ise beyan kapsamina bakilmaz,
    bulgu KIRMIZI kalir."""
    b = bulgu
    # urun basligi: <title> tag'i. h1 cikarim_kaybi'da kontrol edilmiyor ama
    # spec'te h1 da yazildi; gelecekte eklendiginde buraya YAYILIR.
    if b == "<title> degisti":
        return True, "urun basligi (title) beyan edilemez"
    # Spec 4'te <meta name=...> acıkca BEYAN EDILEMEZ listesinde YOK — bu yuzden
    # burada beyan_edilemez DEGILDIR; kapsam adayi olarak siniflanir (varsayilan
    # kapsam sinifinda YOK, hata olarak raporlanir). Bu tasarim kasitli: spec
    # kapali kume tanimliyor, listeye alma = kapinin kapsam adayi olarak
    # siniflamasina izin verme. (T3 fiksturunda bu bulguyla kapinin davranisi
    # olculur; buradaki secim KONTROLDEN gecmeli.)
    if b == "canonical degisti":
        return True, "canonical beyan edilemez"
    if b == "GORUNUR METIN degisti":
        # Spec 4'teki BEYAN EDILEMEZ listesi: kendi gorseli · canonical · siparis ·
        # baslik (title/h1) · fiyat · JSON-LD offers. "GORUNUR METIN" bu listenin
        # DISINDA — yani kapsam adayidir. Title/h1 kendi bulgusu zaten
        # `<title> degisti` olarak beyan edilemez; GORUNUR METIN genellikle rel-card
        # ya da breadcrumb degisikliginin yan urunu (ayni urunde baska bulgularla
        # birlikte gelir). Beyan kapsaminda olmasi, beyan edilemez ayrik alanlarin
        # gecmesini ETKILEMEZ ([[ikiz-tanim-sessiz-ayrisma]] korumasi).
        return False, None
    # JSON-LD: urun verisi; offers dahil HICBIRI beyan edilemez ([[ikiz-tanim-
    # sessiz-ayrisma]] korumasi: offers'i tek basina muaf tutmak "urunun diger
    # JSON-LD yapraklari beyanli" gibi davranirdi).
    if b.startswith("JSON-LD yapragi KAYIP:") or b.startswith("JSON-LD yapragi DEGISTI:"):
        return True, "JSON-LD yapragi beyan edilemez (offers dahil)"
    # <img src> KAYIP: URL urunun kendi gorsellerinden biri mi?
    if b.startswith("<img src> KAYIP:"):
        url = b.split(": ", 1)[1].strip() if ": " in b else ""
        gorseller = (urun or {}).get("gorseller") or []
        # Hem tam eslesme hem prefix eslesmesi: gorseller bazen sorgu param.
        # tasir, bazen kirpilmis gosterilir.
        for g in gorseller:
            if not g:
                continue
            if url == g or url.startswith(g) or g in url:
                return True, "urunun kendi gorseli beyan edilemez"
        return False, None
    # <a href> baglantisi: siparis/WhatsApp mi?
    if b.startswith("<a href> YOLU KAYIP:") or "sorgu parametresi KAYIP/DEGISTI" in b:
        url = ""
        if b.startswith("<a href> YOLU KAYIP:"):
            url = b.split(": ", 1)[1].strip()
        else:
            m = re.match(r"<a href=([^>]+)>", b)
            if m:
                url = m.group(1).strip()
        url_lower = url.lower()
        if "wa.me/" in url_lower or "whatsapp" in url_lower or "siparis" in url_lower:
            return True, "siparis/WhatsApp baglantisi beyan edilemez"
        return False, None
    # Bilinmeyen bulgu tipi: guvenli taraf = beyan edilemez ([[kapsam-tek-tur-
    # tehlikesi]]). Yeni bulgu tipi eklenirse burasi acikca GENISLETILMELI; "bos
    # muafiyet" kapsama geri donus olur.
    return True, "bilinmeyen bulgu tipi (guvenli: edilemez)"


def _bulgu_kapsam_adayi(bulgu):
    """Bulgunun hangi KAPSA degeriyle esledigini ONE EDER.

    Returns kapsam_enum_value (string) or None if can't classify. BEYAN EDILEMEZ
    bulgular burada siniflanmaz — onlar `_bulgu_beyan_edilemez_mi` ile once REDDEDILIR.

    Kural (kasitli degisikliklerin yapisindan):
      · <img src> KAYIP (urunun kendi gorseli degil) -> rel-card-hedefleri
        (eski urun sayfasinda rel-card baska bir urun gosteriyordu, yeni sayfa
        farkli bir rel-card urun gosteriyor -> gorsel KAYIP = hedef degisti).
      · <a href> URL degisikligi:
          - breadcrumb-benzeri path (/kategori/, /marka/, /urun/<id>/) -> breadcrumb-adresi
          - diger -> rel-card-hedefleri
      · GORUNUR METIN degisti (side-effect: rel-card / breadcrumb degisikliginin
        yan urunu — anchor text, alt text, breadcrumb text). Tek basina bir
        beyan edilemez alan degil, ama her zaman bir baska bulguyla birlikte
        geliyorsa, o bulgunun kapsamina YONELIRILIR. Tek basina geldiginde
        (varsayilan) rel-card-hedefleri.
      · Bilinmeyen tipler (buraya gelmemeli) -> None, kapinin varsayilan KATI
        davranisiyla REDDEDILIR.
    """
    if bulgu.startswith("<img src> KAYIP:"):
        return "rel-card-hedefleri"
    if bulgu.startswith("<a href> YOLU KAYIP:"):
        url = bulgu.split(": ", 1)[1].strip()
        url_lower = url.lower()
        if "/kategori/" in url_lower or "/marka/" in url_lower or "/urun/" in url_lower:
            return "breadcrumb-adresi"
        return "rel-card-hedefleri"
    if "sorgu parametresi KAYIP/DEGISTI" in bulgu:
        m = re.match(r"<a href=([^>]+)>", bulgu)
        if m:
            url = m.group(1).strip().lower()
            if "/kategori/" in url or "/marka/" in url or "/urun/" in url:
                return "breadcrumb-adresi"
        return "rel-card-hedefleri"
    if bulgu == "GORUNUR METIN degisti":
        # Spec 4'te BEYAN EDILEMEZ listesinin DISINDA; beyan kapsaminda OLABILIR.
        # Varsayilan olarak rel-card-hedefleri'ne yonlendirilir (en sik yan urun).
        return "rel-card-hedefleri"
    if bulgu == "<meta name=...> kumesi degisti":
        # Spec 4'te BEYAN EDILEMEZ listesinin DISINDA; kapsam adayi.
        # (Meta description / og:image vs. dahil — spec kapali kume.)
        return "rel-card-hedefleri"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# K124 — TURETILMIS SINIFTA SORU DEGISTI: "insan beyan etti mi" -> "YENI HAL SAGLIKLI MI"
# ══════════════════════════════════════════════════════════════════════════════
# NEDEN VAR (16 Agu 2026, UC KEZ OLCULDU): rel-card (ilgili urun) havuzu KATALOGDAN
# TURETILIR. Her urun partisi komsu sayfalarin gosterdigi urunu degistirir; kapi bunu
# `CIKARIM KAYBI` sayar ve gecmesi icin birinin etkilenen urun kimliklerini ELLE
# `varlik-cikarim-beyani.json`'a yazmasini bekler. Yazilmayinca `serit-a3` kirmizi kalir
# ve YAYIN KAPANIR. Ustelik `--referans-tazele` kirmiziyken calismayi reddeder, yani taban
# kendini de onaramaz: KILITLI DONGU. 16 Agu'da yayin bu yuzden ucuncu kez durdu ve her
# seferinde bir insan elle beyan yazarak acti.
#
# 🔴 KUSUR OLGUDA DEGIL SORUDA: kapi dogru olcuyor ama YANLIS SORUYU soruyor. Makinenin
# turettigi ve makinenin DOGRULAYABILECEGI bir degisiklik icin insan sahitligi istiyor.
# Yeni yuklem: bulgu TURETILMIS sinifta ise beyan aranmaz, YENI HALIN SAGLIGI olculur.
#
# 🔴 BU BIR GEVSETME DEGIL — onemli eksende DAHA SIKI:
#   * Bugun bir insan, TUM rel-card'larini kaybetmis bir sayfayi da beyanla gecirebiliyor;
#     saglik kolu bunu KIRMIZI yakar (hedef sayisi AZALAMAZ).
#   * Saglik kolu GECMEZSE davranis BUGUNKUNUN AYNISI: bulgu `kapsam_disi` kalir, beyan
#     aranir, beyan yoksa KIRMIZI. Yani kol yalnizca EKLER, hicbir yolu acmaz.
#   * Urunun KENDI gorseli · canonical · siparis/WhatsApp baglantisi · baslik · fiyat ·
#     JSON-LD yapraklari BU KOLA HIC GIRMEZ: onlar `_bulgu_beyan_edilemez_mi` ile daha
#     once REDDEDILIR ve bloklayici kalir.
#   * Katalog id kumesi okunamazsa saglik OLCULEMEZ -> fail-closed (kol devreye girmez).
TURETILMIS_SINIFLAR = frozenset(("rel-card-hedefleri", "breadcrumb-adresi"))

_URUN_YOLU_RE = re.compile(r"^(?:https?://[^/]+)?/urun/([^/?#]+)/?$")
# Gorsel anahtari gelenegi: media.pruvo3d.com/urunler/<anahtar>.<uzanti>
_GORSEL_ANAHTAR_RE = re.compile(
    r"^https://media\.pruvo3d\.com/urunler/[A-Za-z0-9._-]+\.(?:jpg|jpeg|png|webp|avif)$")
# Turetilmis hedef SAYIMININ ekseni = medya HOST'u (gelenegin ONEKI degil). Gelenek disi
# anahtar sayimdan dusmez, gelenek kolunda ADIYLA yakalanir (bkz. _turetilmis_hedefler).
_MEDYA_HOST_RE = re.compile(r"^https?://media\.pruvo3d\.com/")

# ══════════════════════════════════════════════════════════════════════════════
# GORSEL KOK MANDALI — BUYUYEMEZ taban (KraL ana-oturum-17 hukmu, 13 Eyl 2026)
# ══════════════════════════════════════════════════════════════════════════════
# OLCULDU: katalogda 32 urun / 86 gorsel adresi medya host'unun KOKUNDE (`/urunler/` YOK;
# kaynak iki hasat partisi). m3 HEAD probu: kok adres 86/86 200, `/urunler/` karsiligi
# 86/86 404 -> musteri kirik gorsel GORMUYOR, R2 anahtar gelenegi ihlal. Gelenek kolunu
# "host+uzanti"ya indirmek sinifi YENI kayitlara acardi (YASAK); veri duzeltmesini
# beklemek gorunur zarari olmayan ihlal icin yayini belirsiz sure kapatirdi. Ucuncu yol:
#   * Liste (id+url) BUGUNKU katalogdan TURETILIP dosyaya donduruldu; ELLE yazilmaz.
#   * Tohumun ozet kumesi ASAGIDA KODDA donduruldu: dosyaya tohumda OLMAYAN giris
#     eklenirse KIRMIZI (`MANDAL BUYUDU`) — liste yalniz KUCULUR.
#   * Katalog GENELINDE (orneklem DEGIL, 37k kaydin hepsi) mandal disi gelenek disi
#     adres -> KIRMIZI. Orneklem piyangosu bu sinifi 18 gunde yalniz iki kez gordu.
#   * BAYAT giris (adres duzeltilmis, listede duruyor) serit-a3'te BLOKLAMAZ (MaCiT'in
#     duzeltme push'u kendi kirmizisina takilmasin); `--mandal-nobet` (SERIT B) bayati
#     KIRMIZI yakar ki liste fiilen kuculsun. Hedef MANDAL=0.
#   * Dosya okunamazsa FAIL-CLOSED: muafiyet YOK + KIRMIZI.
GORSEL_KOK_MANDALI = os.path.join(TOOLS, "varlik-gorsel-kok-mandali.json")
MANDAL_JETONU_OKUNAMADI = "GORSEL KOK MANDALI OKUNAMADI"
MANDAL_JETONU_BUYUDU = "GORSEL KOK MANDALI BUYUDU"
MANDAL_JETONU_DISI = "GELENEK DISI ADRES MANDAL DISINDA"
MANDAL_JETONU_BAYAT = "GORSEL KOK MANDALI BAYAT GIRIS"
# sha256("<id>\n<url>")[:16] — 13 Eyl 2026 tohumu (86 giris). BU KUME BUYUTULMEZ.
_MANDAL_TOHUM_OZETLERI = frozenset((
    "00a9db303338d4cf", "00f96fdfd0ed5d99", "01ac9c415eb99686", "07ae4aa2c2fc867f",
    "0cd4f94518653521", "0d6d192553b9a067", "0db4f10ceecf5a7f", "0ec0e58ee6a35684",
    "133fb60830b38f3a", "1448c8817b4df133", "1656adda856b2142", "1be7fcb5b5e67bb2",
    "2072adb74d428c8f", "24b37696fb45b28b", "28adcde7b21aee41", "2ecb067156588116",
    "31e1cae4acfce436", "3777e64f58e423c4", "39dfe638686bd906", "40535c5167e199f2",
    "4611d0f53966bc06", "4d11025389bca3e7", "4e6f78b7803874af", "52f846dd0526fdf1",
    "58b091601043d6f8", "5b39d8267abd30c8", "5c9c098cfcf6301e", "5dfdf54af74621a6",
    "5f843b70eb8baab7", "605c50a405a80ae7", "6554ed735da5ccf7", "69978719aa309597",
    "70883ea93363c30a", "783809e87527a058", "789c26442d224229", "7ba1db36f2af6e96",
    "7c7fe0a048213b7f", "837cc5970313164b", "8831d9100e53a305", "8cd8a9d54735b19a",
    "8eeeb873dfa55844", "92dbcf2bebcf0805", "94f92ad5affaa6d5", "951f143ef280431a",
    "99b2783506d67008", "9d08f3ec702a700d", "a3952f91beb6607f", "a3e09a39053e28d8",
    "a5e820a5b27f9a93", "abb708ef76d5f117", "b0504e7951dd9a64", "b139698a282564aa",
    "b223a5df5978b579", "b23c637a0001a305", "b5e21d7fa8bef760", "b8bc48f5df2ab309",
    "b8bdaab398cec1db", "ba8d82d988974c90", "bc40a7b606efaf7b", "c26c806db0d5d870",
    "c275596f94a26a04", "c58bcbe6fdd21c70", "c58e5ec54e9d6f5c", "c9786bb72f4e8ab1",
    "cb927689a21e01dc", "cb970a8f420674a0", "ce2a1b095c56120e", "cf8d8cedab398889",
    "d0c8d4303cf19dc7", "d2d67a6a41f8f931", "df9bdd91c77392e6", "e04957a8eeb78f5d",
    "e17e2308ad4f82f9", "e1c309a9b56a4ad2", "e284ec44510ffdeb", "e2a07950ab4d174c",
    "e3dabfbce8efa75a", "e5094d898d2c6d47", "e7e209249ac0dfcc", "e8024e17b80e94e3",
    "ef65e80806aa363e", "f1f2a02a1708bab5", "f6376e0a74ec3983", "f9024c4a762651a5",
    "fb083de4250e20f1", "fd48a1f02744569a",
))
# Sayfa duzeyi muafiyetin okudugu kume — `main` mandal hukmunden sonra DOLDURUR. Bos
# kalirsa (kendini-test, okunamayan dosya) muafiyet YOKTUR: katı taraf.
_MANDAL_ADRESLER = frozenset()


def _mandal_ozeti(pid, url):
    return hashlib.sha256((pid + "\n" + url).encode("utf-8")).hexdigest()[:16]


def mandal_oku(yol=None):
    """(girisler, hata) — FAIL-CLOSED: dosya yok / JSON bozuk / yapi yanlis -> (None, sebep)."""
    yol = yol or GORSEL_KOK_MANDALI
    try:
        with io.open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:                          # noqa: BLE001
        return None, "%s okunamadi (%s)" % (yol, type(e).__name__)
    girisler = veri.get("adresler") if isinstance(veri, dict) else None
    if not isinstance(girisler, list) or not all(
            isinstance(g, dict) and isinstance(g.get("id"), str) and isinstance(g.get("url"), str)
            for g in girisler):
        return None, "%s yapisi gecersiz (beklenen: {adresler:[{id,url}]})" % yol
    return girisler, ""


def mandal_hukmu(girisler, urunler, tohum=None):
    """(hatalar, bilgi, muaf_adresler, bayat_sayisi) — katalog GENELINDE mandal hukmu."""
    tohum = _MANDAL_TOHUM_OZETLERI if tohum is None else tohum
    hatalar, bilgi = [], []
    buyuyen = [g for g in girisler if _mandal_ozeti(g["id"], g["url"]) not in tohum]
    if buyuyen:
        hatalar.append("0 %s: tohumda OLMAYAN %d giris (liste yalniz KUCULUR): %s"
                       % (MANDAL_JETONU_BUYUDU, len(buyuyen),
                          [(g["id"][:40], g["url"][-40:]) for g in buyuyen[:3]]))
    gecerli = {(g["id"], g["url"]) for g in girisler if g not in buyuyen}
    katalogda = set()
    for u in (urunler or []):
        if not isinstance(u, dict):
            continue
        for url in (u.get("gorseller") or []):
            if isinstance(url, str) and _MEDYA_HOST_RE.match(url) \
                    and not _GORSEL_ANAHTAR_RE.match(url):
                katalogda.add((u.get("id", ""), url))
    disi = sorted(katalogda - gecerli)
    if disi:
        hatalar.append("1 KATALOG: %s — %s (%d, beyan edilemez): %s"
                       % (KIRIK_HEDEF_JETONU, MANDAL_JETONU_DISI + " / GELENEK DISI", len(disi),
                          [(i[:40], url) for i, url in disi[:3]]))
    canli = gecerli & katalogda
    bayat = sorted(gecerli - katalogda)
    bilgi.append("MANDAL=%d/%d (gorsel kok mandali: canli giris / tohum; hedef 0)"
                 % (len(canli), len(tohum)))
    if bayat:
        bilgi.append("%s (%d, serit-a3'te BLOKLAMAZ, listeden SIL): %s"
                     % (MANDAL_JETONU_BAYAT, len(bayat), [(i[:40], url[-40:]) for i, url in bayat[:3]]))
    return hatalar, bilgi, frozenset(url for _i, url in canli), len(bayat)


def _turetilmis_hedefler(html, urun):
    """(gorsel_urlleri, urun_idleri) — sayfadaki TURETILMIS hedefler.

    Urunun KENDI gorselleri ve KENDI `/urun/<id>/` adresi DISARIDA birakilir: onlar
    turetilmis degil, sayfanin kendi varligidir (beyan EDILEMEZ eksen).

    🔴 13 Eyl 2026 (K-VarlikOrneklem): suzgec eskiden `media.pruvo3d.com/urunler/`
    ALT-DIZESIYDI. Medya HOST'unda ama `/urunler/` DISINDA duran bir hedef gorseli
    (katalogda 32 urun / 86 adres: `https://media.pruvo3d.com/th5935668-g1.jpg`) sayimdan
    SESSIZCE dusuyor, gelenek kolu onu HIC gormuyor ve teshis "GORSEL hedefi AZALDI"
    diye YANLIS yere bakiyordu — 26 Agu'da bu yanlis teshis tekil beyanla kapatildi ve
    ayni veri kusuru 18 gun ortuldu. Suzgec artik HOST ekseninde: kusurlu anahtar
    sayimda KALIR ve gelenek kolu onu ADIYLA basar."""
    kendi_id = (urun or {}).get("id", "")
    kendi_gorseller = set((urun or {}).get("gorseller") or [])
    gorseller = [u for u in _IMGSRC_RE.findall(html)
                 if u not in kendi_gorseller and _MEDYA_HOST_RE.match(u)]
    idler = []
    for yol, _par in _baglantilar(html):
        m = _URUN_YOLU_RE.match((yol or "").strip())
        if m and m.group(1) != kendi_id:
            idler.append(m.group(1))
    return gorseller, idler


KIRIK_HEDEF_JETONU = "TURETILMIS HEDEF KIRIK"


def turetilmis_hedef_kirik_mi(yeni_html, urun, katalog_idler, mandal=None):
    """(kirik, tani) — YENI sayfanin turetilmis hedeflerinden biri KIRIK mi?

    KIRIK = (a) hedef urun KATALOGDA YOK (yetim) ya da (b) hedefin gorsel anahtari
    GELENEK DISI (musteri kirik/yanlis gorsel gorur). Bu iki eksen HEDEFIN KENDI
    halidir; halka kaymasinin (beyanla aciklanabilir) sonucu DEGILDIR.

    🔴 TEK KAYNAK: `turetilmis_hal_saglikli_mi` bu yuklemi CAGIRIR (ikinci kopya yok);
    `olc` ise ayni yuklemi BEYANLA GECEN turetilmis bulgulara da uygular — bir beyan
    halka kaymasini aciklayabilir, KIRIK hedefi mesrulastiramaz (26 Agu vakasi).
    Katalog kumesi BOS ise yetim ekseni OLCULEMEZ -> kirik=None (cagiran fail-closed)."""
    if not katalog_idler:
        return None, ("katalog id kumesi BOS -> hedeflerin varligi OLCULEMEDI "
                      "(fail-closed: saglik kolu devreye girmez)")
    y_gorsel, y_id = _turetilmis_hedefler(yeni_html, urun)
    yetim = [i for i in y_id if i not in katalog_idler]
    if yetim:
        return True, ("yeni hedef KATALOGDA YOK (%d): %s" % (len(yetim), yetim[:3]))
    # GORSEL KOK MANDALI: yalniz mandal hukmunun CANLI saydigi adresler muaftir (bos kume =
    # muafiyet YOK). Mandal disi gelenek disi adres katalog kolunda da ayrica KIRMIZI yanar.
    _mandal = _MANDAL_ADRESLER if mandal is None else mandal
    bozuk = [u for u in y_gorsel if not _GORSEL_ANAHTAR_RE.match(u) and u not in _mandal]
    if bozuk:
        return True, ("yeni hedefin gorsel anahtari GELENEK DISI (%d): %s"
                      % (len(bozuk), [u[:70] for u in bozuk[:3]]))
    return False, "kirik hedef 0 (yetim 0 · gelenek disi anahtar 0)"


def turetilmis_hal_saglikli_mi(eski_html, yeni_html, urun, katalog_idler):
    """(saglikli, tani) — TURETILMIS bulgular icin beyan YERINE olculen yuklem.

    SAGLIKLI = ucunun HEPSI:
      (1) sayfa turetilmis hedeflerini KAYBETMEMIS (gorsel ve baglanti sayisi AZALMAMIS),
      (2) yeni hedeflerin HEPSI katalogda VAR (yetim hedef yok),
      (3) yeni hedeflerin gorsel anahtarlari GELENEGE uygun (host + uzanti).
    (2)+(3) ve BOS katalog fail-closed kolu `turetilmis_hedef_kirik_mi`dedir (tek kaynak:
    burada ikinci bir `if not katalog_idler` kolu mutasyonda SURVIVOR olurdu).
    Herhangi biri saglanmazsa (saglikli=False, tani) doner ve cagiran BUGUNKU KATI
    davranisa geri duser — sessiz yesil YOKTUR."""
    e_gorsel, e_id = _turetilmis_hedefler(eski_html, urun)
    y_gorsel, y_id = _turetilmis_hedefler(yeni_html, urun)
    if len(y_gorsel) < len(e_gorsel):
        return False, ("turetilmis GORSEL hedefi AZALDI (%d -> %d): sayfa rel-card "
                       "blogunu kaybetmis olabilir" % (len(e_gorsel), len(y_gorsel)))
    if len(y_id) < len(e_id):
        return False, ("turetilmis URUN BAGLANTISI AZALDI (%d -> %d)"
                       % (len(e_id), len(y_id)))
    kirik, kirik_tani = turetilmis_hedef_kirik_mi(yeni_html, urun, katalog_idler)
    if kirik is not False:
        return False, kirik_tani
    return True, ("turetilmis hedefler SAGLIKLI: gorsel %d->%d · baglanti %d->%d · "
                  "yetim 0 · gelenek disi anahtar 0"
                  % (len(e_gorsel), len(y_gorsel), len(e_id), len(y_id)))


def turetilmis_hukum(kd, gecen, eski_html, yeni_html, urun, katalog_idler):
    """TURETILMIS sinif hukmu — `olc`dan AYRILDI ki sentetik fiksturle OLCULEBILSIN.

    Girdi: `cikarim_beyan_degerlendir`in kapsam_disi (kd) + beyanla gecen (gecen) listeleri.
    Doner: (kd, gecen, bilgi_satirlari, hata_satirlari).

    Sira (kol yalniz EKLER, hicbir yolu acmaz):
      1. Turetilmis bulgu (kd'de YA DA beyanla gecmis) varsa YENI sayfanin hedefleri
         KIRIK mi olculur. KIRIK ise: beyanla gecis IPTAL, hata basilir (beyan edilemez).
      2. KIRIK degilse kd'deki turetilmis bulgular icin bugunku saglik kolu (K124).
    🔴 NEDEN 1. ADIM (13 Eyl 2026): beyan once degerlendiriliyor ve beyanli urun saglik
    koluna HIC girmiyordu. 26 Agu'da `...-6523494` sayfasi 8 hedefinden 3'u gelenek disi
    (`media.pruvo3d.com/th...` — `/urunler/` YOK) iken TEKIL beyanla gecirildi; ayni
    veri kusuru 13 Eyl'de komsu urunde yayini durdurana dek gorunmedi."""
    bilgi, hata = [], []
    pid = (urun or {}).get("id", "")
    turetilmis_kd = [b for b in kd if _bulgu_kapsam_adayi(b) in TURETILMIS_SINIFLAR]
    turetilmis_gecen = [g for g in gecen if g[1] in TURETILMIS_SINIFLAR]
    if not (turetilmis_kd or turetilmis_gecen):
        return kd, gecen, bilgi, hata
    kirik, kirik_tani = turetilmis_hedef_kirik_mi(yeni_html, urun, katalog_idler)
    if kirik:
        hata.append("1 %s: %s — beyan da saglik kolu da GECIREMEZ (%d turetilmis bulgu, "
                    "%d'i beyanliydi): %s" % (pid, KIRIK_HEDEF_JETONU,
                                              len(turetilmis_kd) + len(turetilmis_gecen),
                                              len(turetilmis_gecen), kirik_tani))
        kd = [b for b in kd if _bulgu_kapsam_adayi(b) not in TURETILMIS_SINIFLAR]
        gecen = [g for g in gecen if g[1] not in TURETILMIS_SINIFLAR]
        return kd, gecen, bilgi, hata
    if turetilmis_kd:
        saglikli, tani = turetilmis_hal_saglikli_mi(eski_html, yeni_html, urun, katalog_idler)
        if saglikli:
            kd = [b for b in kd if _bulgu_kapsam_adayi(b) not in TURETILMIS_SINIFLAR]
            bilgi.append("TURETILMIS HAL SAGLIKLI: %s | %d bulgu BEYANSIZ gecti | %s"
                         % (pid, len(turetilmis_kd), tani))
        else:
            bilgi.append("TURETILMIS SAGLIK KOLU GECMEDI: %s | %s | beyan yolu "
                         "araniyor" % (pid, tani))
    return kd, gecen, bilgi, hata


def turetilmis_saglik_dogrula():
    """SAGLIK KOLUNUN KENDI NOBETI — HER kosumda calisir. Doner: dusen vaka adlari.

    Fiksturler SENTETIK: gercek katalogla, beyan dosyasiyla ve diskle ILGISI YOK."""
    dusen = []
    urun = {"id": "u1", "gorseller": ["https://media.pruvo3d.com/urunler/u1-1.jpg"]}
    katalog = {"u1", "u2", "u3", "u4"}

    def sayfa(hedefler, kendi=True):
        parca = []
        if kendi:
            parca.append('<img src="https://media.pruvo3d.com/urunler/u1-1.jpg">')
            parca.append('<a href="/urun/u1/">kendi</a>')
        for hid, gorsel in hedefler:
            parca.append('<img src="%s">' % gorsel)
            parca.append('<a href="/urun/%s/">k</a>' % hid)
        return "<html>" + "".join(parca) + "</html>"

    G = "https://media.pruvo3d.com/urunler/%s-1.jpg"
    eski = sayfa([("u2", G % "u2"), ("u3", G % "u3")])

    # S1 KONTROL — iyi huylu kayma (hedef DEGISTI, sayi AYNI, hepsi katalogda) -> SAGLIKLI
    ok, tani = turetilmis_hal_saglikli_mi(
        eski, sayfa([("u3", G % "u3"), ("u4", G % "u4")]), urun, katalog)
    if not ok:
        dusen.append("S1 iyi huylu kayma SAGLIKLI sayilmali (%s)" % tani)

    # S2 OLDURUCU — sayfa rel-card blogunu KAYBETTI -> SAGLIKSIZ
    ok, _ = turetilmis_hal_saglikli_mi(eski, sayfa([("u2", G % "u2")]), urun, katalog)
    if ok:
        dusen.append("S2 hedef AZALMASI saglikli sayildi (bugunku beyan yolu bunu "
                     "gecirebiliyordu — saglik kolu YAKALAMALI)")

    # S2b OLDURUCU — YALNIZ BAGLANTI azaldi (gorsel sayisi AYNI) -> SAGLIKSIZ.
    # 🔴 NEDEN AYRI VAKA: S2'de gorsel de baglanti da birlikte dusuyordu ve gorsel kolu
    # ONCE donduugu icin baglanti kolu HIC karar vermiyordu — mutasyon bataryasi bunu
    # SURVIVOR olarak yakaladi ([[fikstur-degeri-mutasyon-koru]]). Iki ekseni AYIRAN
    # fikstur olmadan "baglanti sayisi azalamaz" iddiasi olculmemis bir beyandi.
    yalniz_baglanti_dusuk = (
        "<html>"
        '<img src="https://media.pruvo3d.com/urunler/u1-1.jpg">'
        '<a href="/urun/u1/">kendi</a>'
        '<img src="' + (G % "u3") + '">'
        '<img src="' + (G % "u4") + '">'
        '<a href="/urun/u3/">k</a>'
        "</html>")
    ok, _ = turetilmis_hal_saglikli_mi(eski, yalniz_baglanti_dusuk, urun, katalog)
    if ok:
        dusen.append("S2b YALNIZ baglanti azalmasi saglikli sayildi (gorsel sayisi ayni)")

    # S3 OLDURUCU — yeni hedef KATALOGDA YOK (yetim/silinmis urun) -> SAGLIKSIZ
    ok, _ = turetilmis_hal_saglikli_mi(
        eski, sayfa([("u3", G % "u3"), ("YOK-URUN", G % "YOK-URUN")]), urun, katalog)
    if ok:
        dusen.append("S3 katalogda OLMAYAN hedef saglikli sayildi")

    # S4 OLDURUCU — gorsel anahtari GELENEK DISI (uzantisiz) -> SAGLIKSIZ
    ok, _ = turetilmis_hal_saglikli_mi(
        eski, sayfa([("u3", G % "u3"),
                     ("u4", "https://media.pruvo3d.com/urunler/u4-kaynak-slug")]),
        urun, katalog)
    if ok:
        dusen.append("S4 gelenek disi gorsel anahtari saglikli sayildi")

    # S5 FAIL-CLOSED — katalog kumesi BOS -> saglik kolu DEVREYE GIRMEZ
    ok, tani = turetilmis_hal_saglikli_mi(
        eski, sayfa([("u3", G % "u3"), ("u4", G % "u4")]), urun, set())
    if ok or "OLCULEMEDI" not in tani:
        dusen.append("S5 bos katalog kumesinde saglik kolu fail-closed OLMALI")

    # S6 KAPSAM — urunun KENDI gorseli/adresi turetilmis hedef SAYILMAZ
    g, i = _turetilmis_hedefler(eski, urun)
    if any("u1-1.jpg" in u for u in g) or "u1" in i:
        dusen.append("S6 urunun KENDI varliklari turetilmis hedef sayildi")

    # S7 SINIF KUMESI — yalniz iki turetilmis sinif bu kola girer
    if TURETILMIS_SINIFLAR != frozenset(("rel-card-hedefleri", "breadcrumb-adresi")):
        dusen.append("S7 TURETILMIS_SINIFLAR kumesi degismis (kapsam sessizce buyudu mu?)")

    # S8 BEYAN EDILEMEZ AYRIMI — kendi gorseli bu kola HIC girmemeli (once reddedilir)
    edilemez, _sebep = _bulgu_beyan_edilemez_mi(
        "<img src> KAYIP: https://media.pruvo3d.com/urunler/u1-1.jpg", urun)
    if not edilemez:
        dusen.append("S8 urunun KENDI gorseli beyan edilebilir sayildi (bloklayici "
                     "eksen saglik koluna sizabilir)")

    # S9 HOST EKSENI — medya host'unda `/urunler/` DISI hedef gorseli sayimdan DUSMEZ ve
    # teshis GELENEK DISI olur (AZALDI DEGIL). 13 Eyl 2026: eski alt-dize suzgeci bunu
    # "AZALDI" diye yanlis teshis etti; yanlis teshis 26 Agu'da tekil beyanla kapatilmisti.
    host_disi = sayfa([("u3", G % "u3"), ("u4", "https://media.pruvo3d.com/u4-1.jpg")])
    ok, tani = turetilmis_hal_saglikli_mi(eski, host_disi, urun, katalog)
    if ok or "GELENEK DISI" not in tani:
        dusen.append("S9 /urunler/ disi hedef gorseli GELENEK DISI diye teshis edilmeli "
                     "(%s)" % tani)

    # S10 OLDURUCU — BEYAN KIRIK HEDEFI MESRULASTIRAMAZ: beyanla gecmis turetilmis bulgu +
    # yeni sayfada gelenek disi hedef -> KIRMIZI, beyan gecisi IPTAL.
    beyanli = [("<img src> KAYIP: " + (G % "u2"), "rel-card-hedefleri", "fikstur beyani")]
    _kd, _gecen, _bi, _h = turetilmis_hukum([], beyanli, eski, host_disi, urun, katalog)
    if not any(KIRIK_HEDEF_JETONU in h for h in _h) or _gecen:
        dusen.append("S10 beyanla gecen turetilmis bulgu KIRIK hedefte KIRMIZI yanmali "
                     "(hata=%r gecen=%d)" % (_h[:1], len(_gecen)))

    # S11 KONTROL — beyanli + saglam hedef -> hata YOK, beyan gecisi KORUNUR
    saglam_sayfa = sayfa([("u3", G % "u3"), ("u4", G % "u4")])
    _kd, _gecen, _bi, _h = turetilmis_hukum([], beyanli, eski, saglam_sayfa, urun, katalog)
    if _h or len(_gecen) != 1:
        dusen.append("S11 beyanli + saglam hedefte KIRMIZI yandi ya da beyan gecisi dustu "
                     "(hata=%r gecen=%d)" % (_h[:1], len(_gecen)))

    # ── MUTASYON BATARYASI ────────────────────────────────────────────────────
    # 🔴 Bu kol beyanin YERINE geciyor; "vakalar var" demek yetmez, vakalarin TASIYICI
    # oldugu KANITLANMALI ([[mutasyon-kaniti-yeniden-uretilebilir]]). Yuklemin her AYRI
    # kolu bellekte tek tek etkisizlestirilir ve davranisin DEGISMESI beklenir; degismezse
    # o kol olu demektir (SURVIVOR) ve bu nobet KIRMIZI yanar. Mutasyon DISKE YAZILMAZ
    # ([[mutasyon-diske-yazma-tuzagi]]): kaynak metni `inspect` ile alinip exec edilir.
    # 13 Eyl 2026: kollar dort fonksiyona dagildi (hedef suzgeci · kirik hedef · saglik ·
    # hukum); mutant ORTAMI dordunu birlikte yeniden kurar (`_turetilmis_mutant_ortami`).
    def _kollar(ns):
        """NEGATIF vakalarin (hukum, tani ilk 40 harf) imzasi + hukum ciktisinin boyu.

        🔴 Her yuklem kolu icin AYIRT EDICI en az bir vaka olmali: aksi halde bir kol
        digerinin golgesinde kalir ve etkisizlestirilse bile imza degismez (SURVIVOR)."""
        fn = ns["turetilmis_hal_saglikli_mi"]

        def k(r):
            return (r[0], r[1][:40])
        return [
            k(fn(eski, sayfa([("u2", G % "u2")]), urun, katalog)),
            k(fn(eski, yalniz_baglanti_dusuk, urun, katalog)),
            k(fn(eski, sayfa([("u3", G % "u3"), ("YOK-URUN", G % "YOK")]), urun, katalog)),
            k(fn(eski, sayfa([("u3", G % "u3"),
                              ("u4", "https://media.pruvo3d.com/urunler/u4-kaynak-slug")]),
                 urun, katalog)),
            k(fn(eski, sayfa([("u3", G % "u3"), ("u4", G % "u4")]), urun, set())),
            k(fn(eski, host_disi, urun, katalog)),
            tuple(len(x) for x in ns["turetilmis_hukum"]([], beyanli, eski, host_disi,
                                                         urun, katalog)),
            ns["turetilmis_hedef_kirik_mi"](host_disi, urun, katalog, mandal=mandal_s12)[0],
        ]

    # S12 GORSEL KOK MANDALI — mandal kumesindeki gelenek disi adres KIRIK SAYILMAZ; ayni
    # adres mandal DISINDA iken S9/S10 KIRMIZI kalir (muafiyet yalniz verilen kumeye).
    mandal_s12 = frozenset(("https://media.pruvo3d.com/u4-1.jpg",))
    _kirik12, _tani12 = turetilmis_hedef_kirik_mi(host_disi, urun, katalog, mandal=mandal_s12)
    if _kirik12 is not False:
        dusen.append("S12 MANDAL icindeki adres KIRIK sayildi (%s)" % _tani12)

    _taban = _kollar(globals())
    _mutantlar = (
        ("GORSEL KOK MANDALI muafiyeti kaldirildi", "turetilmis_hedef_kirik_mi",
         " and u not in _mandal]", "]"),
        ("hedef-gorsel AZALMASI kolu", "turetilmis_hal_saglikli_mi",
         "    if len(y_gorsel) < len(e_gorsel):", "    if False:"),
        ("hedef-baglanti AZALMASI kolu", "turetilmis_hal_saglikli_mi",
         "    if len(y_id) < len(e_id):", "    if False:"),
        ("yetim hedef kolu", "turetilmis_hedef_kirik_mi", "    if yetim:", "    if False:"),
        ("gelenek disi anahtar kolu", "turetilmis_hedef_kirik_mi",
         "    if bozuk:", "    if False:"),
        ("bos katalog fail-closed kolu", "turetilmis_hedef_kirik_mi",
         "    if not katalog_idler:", "    if False:"),
        ("KIRIK hedef beyan-edilemez kolu", "turetilmis_hukum", "    if kirik:", "    if False:"),
        ("HOST suzgeci eski /urunler/ alt-dizesine geri alindi", "_turetilmis_hedefler",
         "_MEDYA_HOST_RE.match(u)", '"media.pruvo3d.com/urunler/" in u'),
    )
    for _ad, _fn, _capa, _yeni in _mutantlar:
        _ns, _hata = _turetilmis_mutant_ortami(_fn, _capa, _yeni)
        if _ns is None:
            dusen.append("MUTASYON CAPASI KAYIP (%s): %s" % (_ad, _hata))
            continue
        try:
            _sonuc = _kollar(_ns)
        except Exception:                                       # noqa: BLE001
            continue                                            # mutant patladi = OLDU
        if _sonuc == _taban:
            dusen.append("SURVIVOR: %s etkisizlestirildi ama HICBIR vaka degismedi "
                         "(kol olu — yuklem o ekseni gercekten olcmuyor)" % _ad)
    return dusen


_TURETILMIS_FONKSIYONLAR = ("_turetilmis_hedefler", "turetilmis_hedef_kirik_mi",
                            "turetilmis_hal_saglikli_mi", "turetilmis_hukum")


def _turetilmis_mutant_ortami(hedef_fn, capa, yeni):
    """(ortam, hata) — dort turetilmis fonksiyonu BELLEKTE yeniden kurar; `hedef_fn`in
    kaynaginda `capa` TAM BIR KEZ `yeni` ile degistirilir. Disk'e YAZILMAZ; modul
    globalleri KOPYALANIR (canli fonksiyonlar ezilmez). Capa 1 kez gecmiyorsa (None, hata)."""
    ns = dict(globals())
    for ad in _TURETILMIS_FONKSIYONLAR:
        try:
            kaynak = inspect.getsource(globals()[ad])
        except (OSError, TypeError, KeyError) as e:             # noqa: BLE001
            return None, "%s kaynagi okunamadi (%s)" % (ad, type(e).__name__)
        if ad == hedef_fn:
            if kaynak.count(capa) != 1:
                return None, "%r %s kaynaginda %d kez" % (capa.strip(), ad, kaynak.count(capa))
            kaynak = kaynak.replace(capa, yeni)
        exec(compile(kaynak, "<turetilmis-mutant>", "exec"), ns)  # noqa: S102
    return ns, ""


EKLEME_FIKSTUR_ONEK = "k-ekleme-fikstur-"


def katalog_basi_ekleme_dogrula(urunler, n_ek=5):
    """(K) + (M) — KATALOG BASINA KAYIT EKLEME senaryosu, GERCEK uretici ile. Doner: dusen.

    NEDEN (13 Eyl 2026): `urunler.json` yeni kaydi BASA ekler; her parti rel-card halkasini
    ve orneklemi kaydirir. Kapinin bu kaymaya karsi iki yukumlulugu var ve ikisi de
    GERCEK KATALOGDAN BAGIMSIZ olculmeli (gercek katalog o gun kusurlu olabilir):
      (K) basa N SAGLAM kayit eklenince turetilmis hukum SAHTE KIRMIZI uretmez;
      (M1) eklenen kayitlardan birinin gorsel anahtari gelenek disiysa KIRIK hedef KIRMIZI;
      (M2) halka DEGISMEDEN bir hedefin `<img src>`i kaybolursa KIRMIZI.
    Sablon: gercek katalogdaki saglam urunlerden (bellekte KOPYA, marka bosaltilir ki
    halka yalniz kategori halkasi olsun) 30'luk mini katalog. Hedef urun halkanin SONUNA
    yakin secilir: halka basa sarar, basa eklenen kayit hedefin rel-card'ina GIRER —
    girmezse senaryo KOR'dur ve bu ADIYLA basilir (sessiz yesil yok).
    Her iddianin TASIYICI oldugu bellek mutantiyla ayrica olculur."""
    dusen = []
    saglam = [u for u in (urunler or [])
              if isinstance(u, dict) and u.get("id") and u.get("kategori")
              and not u.get("parametrik")
              and (u.get("gorseller") or [])
              and all(_GORSEL_ANAHTAR_RE.match(g or "") for g in u["gorseller"])]
    sayac = {}
    for u in saglam:
        sayac[u["kategori"]] = sayac.get(u["kategori"], 0) + 1
    if not sayac or max(sayac.values()) < 30:
        return ["K/M OLCULEMEDI: sablon icin tek kategoride >=30 saglam urun yok"]
    kat = sorted(sayac.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    havuz = []
    for u in saglam:
        if u["kategori"] != kat:
            continue
        kopya = dict(u)
        kopya["marka"] = []
        kopya.pop("uyum", None)
        havuz.append(kopya)
        if len(havuz) == 30:
            break
    hedef = havuz[-2]

    def klonlar(kotu_ilk):
        cikti = []
        for i in range(n_ek):
            k = dict(havuz[0])
            k["id"] = "%s%d" % (EKLEME_FIKSTUR_ONEK, i)
            onek = ("https://media.pruvo3d.com/" if (kotu_ilk and i == 0)
                    else "https://media.pruvo3d.com/urunler/")
            k["gorseller"] = ["%s%s-1.jpg" % (onek, k["id"])]
            cikti.append(k)
        return cikti

    ekli_k = klonlar(False) + havuz
    ekli_m = klonlar(True) + havuz
    taban = build.render_product(hedef, havuz, None)
    sayfa_k = build.render_product(hedef, ekli_k, None)
    sayfa_m = build.render_product(hedef, ekli_m, None)
    if ("/urun/%s0/" % EKLEME_FIKSTUR_ONEK) not in sayfa_k:
        return ["K KOR: basa eklenen kayit hedefin rel-card halkasina GIRMEDI "
                "(senaryo kayma uretmiyor, iddialar OLCULEMEDI)"]
    hedef_gorsel = [u for u in _IMGSRC_RE.findall(taban)
                    if u not in set(hedef["gorseller"]) and _MEDYA_HOST_RE.match(u)]
    if not hedef_gorsel:
        return ["M2 KOR: taban sayfada turetilmis hedef gorseli yok"]
    kayipli = taban.replace('src="%s"' % hedef_gorsel[0], 'src=""')

    def kimlik(liste):
        return {u["id"] for u in liste}

    def senaryo(ns):
        """(K_tamam, M1_tamam, M2_tamam, K_teshis)"""
        hukum = ns["turetilmis_hukum"]

        def uygula(eski_h, yeni_h, katalog):
            bulgu = cikarim_kaybi(iskelet(eski_h), iskelet(yeni_h), ())
            gecen, kd, _be, _yb = cikarim_beyan_degerlendir(bulgu, hedef, [])
            kd2, _g, _bi, hata = hukum(kd, gecen, eski_h, yeni_h, hedef, katalog)
            return bulgu, kd2, hata
        b_k, kd_k, h_k = uygula(taban, sayfa_k, kimlik(ekli_k))
        k_tamam = bool(b_k) and not kd_k and not h_k
        _b, _kd, h_m = uygula(taban, sayfa_m, kimlik(ekli_m))
        m1_tamam = any(KIRIK_HEDEF_JETONU in h and "GELENEK DISI" in h for h in h_m)
        _b, kd_m2, h_m2 = uygula(taban, kayipli, kimlik(havuz))
        m2_tamam = any(b.startswith("<img src> KAYIP") for b in kd_m2) or bool(h_m2)
        return k_tamam, m1_tamam, m2_tamam, (len(b_k), kd_k[:2], h_k[:1])

    k_ok, m1_ok, m2_ok, k_teshis = senaryo(globals())
    if not k_ok:
        dusen.append("K SAHTE KIRMIZI: basa %d saglam kayit eklenince turetilmis hukum "
                     "gecmedi (bulgu=%d kalan=%r hata=%r)" % ((n_ek,) + k_teshis))
    if not m1_ok:
        dusen.append("M1 basa eklenen GELENEK DISI gorselli hedef %s + GELENEK DISI "
                     "basmadi" % KIRIK_HEDEF_JETONU)
    if not m2_ok:
        dusen.append("M2 halka degismeden hedef `<img src>` kaybi KIRMIZI yanmadi")
    if dusen:
        return dusen
    # TASIYICILIK: her iddia, onu bozan bellek mutantinda DUSMELI.
    for ad, fn, capa, yeni, indeks in (
            ("K <- saglik kolu hic gecirmez", "turetilmis_hukum",
             "        if saglikli:", "        if False:", 0),
            ("M1 <- HOST suzgeci /urunler/ alt-dizesine geri alindi", "_turetilmis_hedefler",
             "_MEDYA_HOST_RE.match(u)", '"media.pruvo3d.com/urunler/" in u', 1),
            ("M2 <- gorsel AZALMASI kolu", "turetilmis_hal_saglikli_mi",
             "    if len(y_gorsel) < len(e_gorsel):", "    if False:", 2)):
        ns, hata = _turetilmis_mutant_ortami(fn, capa, yeni)
        if ns is None:
            dusen.append("K/M MUTASYON CAPASI KAYIP (%s): %s" % (ad, hata))
            continue
        try:
            sonuc = senaryo(ns)
        except Exception:                                       # noqa: BLE001
            continue
        if sonuc[indeks]:
            dusen.append("K/M SURVIVOR: %s — iddia mutantta da GECTI (iddia tasiyici degil)"
                         % ad)
    return dusen


def cikarim_beyan_degerlendir(bulgular, urun, beyan_kayitlari):
    """Her bulgu icin beyan kayitlarini dolasir: BEYAN EDILEMEZ ise REDDEDILIR;
    KAPSAM adayi beyan kaydinin kapsamindaysa VE urun urunler listesindeyse GECER;
    aksi REDDEDILIR.

    Doner:
      (gecenler, kapsam_disi, beyan_edilemez, yapisi_bozuk_kayitlar)
    """
    gecenler = []
    kapsam_disi = []
    beyan_edilemez = []
    yapisi_bozuk_kayitlar = []
    if not beyan_kayitlari:
        # beyan YOK veya yapisal bozuk -> bugunku KATI davranis: HICBIRI gecmez.
        kapsam_disi.extend(bulgular)
        return gecenler, kapsam_disi, beyan_edilemez, yapisi_bozuk_kayitlar
    for bulgu in bulgular:
        edilemez, sebep = _bulgu_beyan_edilemez_mi(bulgu, urun)
        if edilemez:
            beyan_edilemez.append((bulgu, sebep))
            continue
        kapsam_adayi = _bulgu_kapsam_adayi(bulgu)
        if kapsam_adayi is None:
            kapsam_disi.append(bulgu)
            continue
        bulgu_eslesen = False
        for kayit in beyan_kayitlari:
            gecer, gerekce = _beyan_kayit_gecerli_mi(kayit, ref=None)
            if not gecer:
                yapisi_bozuk_kayitlar.append((kayit, gerekce))
                continue
            urun_id = (urun or {}).get("id", "")
            if urun_id not in kayit["urunler"]:
                continue
            if kapsam_adayi not in set(kayit["kapsam"]):
                continue
            gecenler.append((bulgu, kapsam_adayi, kayit.get("gerekce", "")))
            bulgu_eslesen = True
            break
        if not bulgu_eslesen:
            kapsam_disi.append(bulgu)
    return gecenler, kapsam_disi, beyan_edilemez, yapisi_bozuk_kayitlar


def cikarim_beyan_mekanizmasi_dogrula():
    """BEYAN KAPISININ KENDI NOBETI — HER kosumda calisir (kendini-test).

    🔴 NEDEN: beyan yuzeyi kapinin SUSTURMA kolusudur; sessizce "her seyi yut"
    haline donerse kapi olur ([[kapi-kapsam-genisletme-tuzagi]]). Fiksturler SENTETIK:
    gercek `urunler.json`'a, gercek beyan dosyasina ve diske DOKUNMAZ.

    Doner: basarisiz vaka adlari (bos = yuzey saglam).

    Vakalar:
      C1 BEYAN YAPISI    : beyan dosyasi bozuk/yanlis tip -> kati davranis (fail-closed).
      C2 BEYAN KAYDI     : kayit gecersiz (ref yok, kapsam bos, blanket) -> REDDEDILIR.
      C3 BEYAN EDILMEZ   : kendi gorseli / canonical / siparis / title / meta -> REDDEDILIR.
      C4 BEYAN KAPSAM    : beyan kapsaminda olmayan bulgu -> REDDEDILIR.
      C5 BEYAN URUNLER   : beyan urunler listesinde olmayan urun -> REDDEDILIR.
      C6 KONTROL         : beyan VAR, urun listede, kapsaminda -> GECER.
      C7 KONTROL YOK     : beyan dosyasi yok -> bugunku kati davranis, HICBIRI gecmez."""
    dusen = []

    urun = {"id": "u1", "gorseller": ["https://media.pruvo3d.com/urunler/u1-1.jpg"]}
    beyan_dosyasi = _beyan_dosyasi_oku()  # bu noktada dosya henuz yazilmamis OLMALI

    # C1/C2: beyan dosyasi YOKSA kati davranis (fail-closed).
    # Burada gercek dosyaya DOKUNMADAN SENTETIK verilerle mekanizma test edilir.
    bulgular = [
        "<a href=/urun/u2/> sorgu parametresi KAYIP/DEGISTI: eski={} yeni={}".replace(
            "{}", ""),
        "<img src> KAYIP: https://media.pruvo3d.com/urunler/u2-1.jpg",
    ]
    _, kd, be, _ = cikarim_beyan_degerlendir(bulgular, urun, beyan_kayitlari=None)
    if kd != bulgular or be:
        dusen.append("C7 beyan dosyasi YOKken bulgular gecmemeli (kat davranis): kd=%r be=%r"
                     % (kd, be))

    # C1: beyan verisi yanlis tipte (sozluk degil) -> bos kapsam_disi (fail-closed).
    _, kd, be, _ = cikarim_beyan_degerlendir(bulgular, urun, beyan_kayitlari=["yanlis"])
    if kd != bulgular:
        dusen.append("C1 beyan kayitlari yanlis tip -> kati davranis gecmedi")

    # C2: bos kapsam (blanket beyan) -> tum kayitlar YAPISI BOZUK sayilir; bulgular
    # kapsam_disi'ne duser.
    bos_kapsam = [{"ref": "4380e7c8b4c27d6538cb433e70bad32b685efc96",
                   "tarih": "2026-08-16", "gerekce": "x",
                   "kapsam": [], "urunler": ["u1"]}]
    _, kd, _, _ = cikarim_beyan_degerlendir(bulgular, urun, beyan_kayitlari=bos_kapsam)
    if not kd:
        dusen.append("C2 bos kapsam blanket beyan olarak REDDEDILMELI")

    # C2b: blanket deger ("*") -> yapisi bozuk.
    blanket = [{"ref": "4380e7c8b4c27d6538cb433e70bad32b685efc96",
                "tarih": "2026-08-16", "gerekce": "x",
                "kapsam": ["*"], "urunler": ["u1"]}]
    _, kd, _, yb = cikarim_beyan_degerlendir(bulgular, urun, beyan_kayitlari=blanket)
    if not yb:
        dusen.append("C2b blanket kapsam ('*') REDDEDILMELI (yapisal bozuk)")

    # C3: BEYAN EDILEMEZ alanlar (spec 4, 6 alt vaka — T5'te 5 sayilir cunku
    # JSON-LD offers "fiyat" kapsaminda eritilir).
    beyan_tek = [{"ref": "4380e7c8b4c27d6538cb433e70bad32b685efc96",
                  "tarih": "2026-08-16",
                  "gerekce": "x",
                  "kapsam": list(BEYAN_KAPSA_KUMESI),
                  "urunler": ["u1"]}]
    beyan_edilemez_bulgular = [
        ("kendi gorseli", "<img src> KAYIP: https://media.pruvo3d.com/urunler/u1-1.jpg"),
        ("canonical", "canonical degisti"),
        ("title", "<title> degisti"),
        ("fiyat (JSON-LD offers)",
         "JSON-LD yapragi DEGISTI: /offers/price: '100' -> '200'"),
        ("siparis/WhatsApp",
         "<a href=https://wa.me/905451386526> sorgu parametresi KAYIP/DEGISTI: eski={} yeni={}".replace(
             "{}", "")),
    ]
    for ad, bulgu in beyan_edilemez_bulgular:
        _, kd, be, _ = cikarim_beyan_degerlendir([bulgu], urun, beyan_kayitlari=beyan_tek)
        if kd or not be:
            dusen.append("C3 %s BEYAN EDILEMEZ olmali (beyan kapsamini icse bile): "
                         "kd=%r be=%r" % (ad, kd, be))

    # C4: bulgu kapsam adayi beyan kapsaminda DEGIL -> kapsam_disi.
    # Beyan kapsami sadece "breadcrumb-adresi" tutuyor, bulgu rel-card-hedefleri.
    sadece_breadcrumb = [{"ref": "4380e7c8b4c27d6538cb433e70bad32b685efc96",
                          "tarih": "2026-08-16",
                          "gerekce": "x",
                          "kapsam": ["breadcrumb-adresi"],
                          "urunler": ["u1"]}]
    rel_card_bulgu = "<img src> KAYIP: https://media.pruvo3d.com/urunler/u2-1.jpg"
    gecen, kd, be, _ = cikarim_beyan_degerlendir(
        [rel_card_bulgu], urun, beyan_kayitlari=sadece_breadcrumb)
    if gecen or kd != [rel_card_bulgu]:
        dusen.append("C4 bulgu kapsam adayi beyan kapsaminda degil -> kapsam_disi "
                     "(gecen=%r kd=%r)" % (gecen, kd))

    # C5: urun beyan urunler listesinde DEGIL -> kapsam_disi.
    beyan_baska_urun = [{"ref": "4380e7c8b4c27d6538cb433e70bad32b685efc96",
                         "tarih": "2026-08-16",
                         "gerekce": "x",
                         "kapsam": list(BEYAN_KAPSA_KUMESI),
                         "urunler": ["u99"]}]
    _, kd, _, _ = cikarim_beyan_degerlendir([rel_card_bulgu], urun,
                                            beyan_kayitlari=beyan_baska_urun)
    if kd != [rel_card_bulgu]:
        dusen.append("C5 urun beyan urunler listesinde degil -> kapsam_disi")

    # C6 KONTROL: beyan VAR, urun listede, kapsaminda -> GECER.
    gecen, kd, be, _ = cikarim_beyan_degerlendir([rel_card_bulgu], urun,
                                                 beyan_kayitlari=beyan_tek)
    if kd or be or len(gecen) != 1:
        dusen.append("C6 KONTROL: beyan+tum kosullar uyuyor -> GECMELI "
                     "(gecen=%r kd=%r be=%r)" % (gecen, kd, be))
    return dusen


def referans_tazele():
    """KIYAS REFERANSINI ILERLET — yalnizca kapi O AN YESILKEN, ve GORUNUR bicimde.

    YORDAM (elle degil, olculebilir):
      1. Kapi bayraksiz kolla TAM olarak kosulur. KIRMIZI ya da OLCULEMEDI ise tazeleme
         REDDEDILIR — aksi halde tazeleme, kanitlanmamis bir hali "taban" yapip
         gercek bir icerik kaybini yutardi.
      2. CIKARIM BEYANI (16 Agu): tools/varlik-cikarim-beyani.json VARSA kapi YESIL
         olsa bile KIRMIZI bulgularin tamami beyan kapsaminda olmali (kismi gecis YOK).
         Beyan YOKSA bugunku kati davranis AYNEN korunur (fail-closed).
      3. Yeni referans = tools/build.py'yi degistiren EN SON commit (HEAD tarafi).
      4. Kayit tools/varlik-referans.json'a yazilir: ref + tarih + onceki ref + o anki
         olcum. Dosya IZLENIR -> her tazeleme bir COMMIT'tir, sessiz olamaz.
      5. Tazeleme SONRASI hangi beyan girislerinin ARTIK GEREKSIZ oldugu BASILIR
         (yeni referansta o satirlar iki tarafta da vardir). Temizlik bilincli yapilir;
         betik tabloya DOKUNMAZ.
    Kapi ZAYIFLAMAZ: tazelemeden sonraki her beyansiz icerik degisikligi yine KIRMIZI."""
    print("REFERANS TAZELEME — once kapi bayraksiz kolla kosuluyor...")
    # AYRI SUREC: hukum bu betigin kendi ic durumundan degil, GERCEK cikis kodundan
    # okunur (rapor() sys.exit ile biter; ic cagri hukmu yutardi).
    kosum = subprocess.run([sys.executable, os.path.abspath(__file__)],
                           capture_output=True, text=True)
    print(kosum.stdout[-1200:])
    if kosum.returncode != 0:
        # CIKARIM BEYANI (16 Agu): kapinin kendi kirmizilari (BEYAN EDILEMEZ veya
        # beyan KAPSAMI DISINDA) bile bu kapidan GECEMEZ; kapi YESIL degilse tazeleme
        # de REDDEDILIR — beyan muafiyet KAYITTIR, bypass degildir.
        beyan_var_mi = _beyan_dosyasi_oku() is not None
        if beyan_var_mi:
            print("\nTAZELEME REDDEDILDI: beyan dosyasi VAR ama kapi YESIL degil "
                  "(rc=%d) — beyan KAYIT mekanizmasi muafiyet DEGILDIR. Once beyan "
                  "KAPSAMI DISINDA veya BEYAN EDILEMEZ bulguyu kapat." % kosum.returncode)
        else:
            print("\nTAZELEME REDDEDILDI: kapi YESIL degil (rc=%d). Once kirmiziyi kapat; "
                  "kanitlanmamis hal taban YAPILMAZ." % kosum.returncode)
        return 1
    # BEYAN KULLANIM SAYISI: beyan dosyasi varsa ve gecen bulgular varsa BASILIR.
    # Beyan KAYITTIR: sessiz gecis yok, hangi bulgunun hangi gerekceyle gectigi gorunur.
    gecen_sayisi = sum(1 for _s in (kosum.stdout or "").splitlines()
                       if "BEYAN KAPSAMINDA:" in _s)
    if gecen_sayisi:
        print("\n  beyanla gecen bulgu: %d (kayit; sessiz gecis YOK)" % gecen_sayisi)
    yeni_ref = (git("log", "-1", "--format=%H", "--", "tools/build.py") or "").strip()
    if not yeni_ref:
        print("TAZELEME REDDEDILDI: tools/build.py icin commit bulunamadi (SIG depo?)")
        return 2
    onceki = eski_ref()
    if yeni_ref == onceki:
        print("TAZELEME GEREKSIZ: referans zaten en guncel build.py commit'i (%s)"
              % yeni_ref[:10])
        return 0
    kayit = {
        "ref": yeni_ref,
        "tazelendi": (git("log", "-1", "--format=%cs", yeni_ref) or "").strip(),
        "onceki_ref": onceki,
        "yordam": "python3 tools/varlik-test.py --referans-tazele (kapi YESILKEN)",
        "not": ("Kiyas referansi. DONMUS SHA DEGIL: bu dosya yordamla yazilir ve her "
                "tazeleme bir commit'tir. Referans yalnizca kayipsizligi KANITLANMIS "
                "bir noktaya ilerler."),
    }
    with io.open(REFERANS_DOSYASI, "w", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False, indent=2) + "\n")
    print("\nREFERANS TAZELENDI: %s -> %s" % ((onceki or "-")[:10], yeni_ref[:10]))
    print("  kayit: %s (IZLENIR — commit et)" % REFERANS_DOSYASI)
    print("  ⚠️ Bu tazelemeden sonra asagidaki beyan girisleri BUYUK IHTIMALLE gereksiz")
    print("     (yeni referansta iki tarafta da varlar). GOZDEN GECIR ve SIL:")
    for d, g in BILEREK_DEGISEN_TAM:
        print("       · %-60s  %s" % (repr(d)[:60], g[:50]))
    for e, _y, g in BILEREK_DEGISEN_METIN:
        print("       · METIN %-54s  %s" % (repr(_norm(e))[:54], g[:50]))
    return 0


def mandal_nobet():
    """SERIT B — gorsel kok mandalinin FIILEN KUCULMESINI zorlar (NON-GROWTH).

    rc=1: mandal okunamaz · tohum disi giris (buyume) · mandal disi gelenek disi adres ·
    BAYAT giris (adres katalogda duzeltilmis, liste hala tasiyor). serit-a3 kolu bayati
    BLOKLAMAZ; kuculmeyi bu nobet ister. Ag YOK, diske YAZMAZ."""
    girisler, hata = mandal_oku()
    if girisler is None:
        print("KIRMIZI (1):\n  - 0 %s: %s — fail-closed" % (MANDAL_JETONU_OKUNAMADI, hata))
        return 1
    with io.open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    hatalar, bilgi, _adresler, bayat = mandal_hukmu(girisler, urunler)
    for b in bilgi:
        print("  · " + b)
    if bayat:
        hatalar.append("0 %s: %d giris artik katalogda YOK -> listeden SIL (liste yalniz KUCULUR)"
                       % (MANDAL_JETONU_BAYAT, bayat))
    if hatalar:
        print("\nKIRMIZI (%d):" % len(hatalar))
        for h in hatalar:
            print("  - " + h)
        return 1
    print("\nOK: gorsel kok mandali — buyume 0 · mandal disi 0 · bayat 0.")
    return 0


def main():
    global _MANDAL_ADRESLER
    if "--mandal-nobet" in sys.argv:
        sys.exit(mandal_nobet())
    if "--kendini-test" in sys.argv:
        sys.exit(kendini_test())
    if "--referans-tazele" in sys.argv:
        sys.exit(referans_tazele())
    # Muafiyet yuzeyinin nobeti HER kosumda, olcumden ONCE.
    for _d in beyan_mekanizmasi_dogrula():
        HATALAR.append("0 GORUNUR-METIN BEYAN YUZEYI BOZUK: %s" % _d)
    for _d in css_beyan_mekanizmasi_dogrula():
        HATALAR.append("0 CSS BEYAN YUZEYI BOZUK: %s" % _d)
    for _d in referans_hukmu_dogrula():
        HATALAR.append("0 KIYAS REFERANSI GECERLILIK HUKMU BOZUK: %s" % _d)
    for _d in cikarim_beyan_mekanizmasi_dogrula():
        HATALAR.append("0 CIKARIM BEYAN YUZEYI BOZUK: %s" % _d)
    # K124: saglik kolu beyan yerine gecen bir YUKLEMDIR — kendi nobeti de HER kosumda.
    for _d in turetilmis_saglik_dogrula():
        HATALAR.append("0 TURETILMIS SAGLIK KOLU BOZUK: %s" % _d)
    hedef = 12
    if "--ornek" in sys.argv:
        hedef = int(sys.argv[sys.argv.index("--ornek") + 1])

    with io.open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    # GORSEL KOK MANDALI — katalog GENELINDE hukum, sayfa olcumunden ONCE (muaf kume
    # sayfa duzeyi kirik-hedef yuklemine buradan gecer). Okunamazsa muafiyet YOK + KIRMIZI.
    _girisler, _mandal_hata = mandal_oku()
    if _girisler is None:
        HATALAR.append("0 %s: %s — fail-closed (muafiyet YOK)"
                       % (MANDAL_JETONU_OKUNAMADI, _mandal_hata))
    else:
        _m_hata, _m_bilgi, _MANDAL_ADRESLER, _m_bayat = mandal_hukmu(_girisler, urunler)
        HATALAR.extend(_m_hata)
        BILGI.extend(_m_bilgi)
    # K/M: katalog basina ekleme senaryosu (gercek uretici, bellekte mini katalog). Varlik
    # dizini asagida zaten SIFIRLANIR — bu cagrinin urettigi dosyalar olcume karismaz.
    _km = katalog_basi_ekleme_dogrula(urunler)
    for _d in _km:
        HATALAR.append("0 KATALOG BASI EKLEME (K/M) BOZUK: %s" % _d)
    if not _km:
        BILGI.append("K/M katalog basi ekleme: K sahte kirmizi 0 · M1 KIRIK hedef KIRMIZI · "
                     "M2 <img src> kaybi KIRMIZI · 3/3 iddia mutantta DUSTU")
    secim = ornek_sec(urunler, hedef)
    idler = [p["id"] for _, p in secim]
    BILGI.append("ornek: %d urun (%s)" % (len(secim), ", ".join(a for a, _ in secim)))

    # varlik dizinini sifirdan uret (bayat dosya olcume karismasin)
    if os.path.isdir(build.VARLIK_DIR):
        shutil.rmtree(build.VARLIK_DIR)
    build._VARLIK_ONBELLEK.clear()

    yeni = {}
    for _, p in secim:
        yeni[p["id"]] = build.render_product(p, urunler, None)

    # ---------------------------------------------------------------- 3
    bekle(len(yeni) == len(secim), "3 sayfa sayisi degisti: %d/%d" % (len(yeni), len(secim)))
    for pid, h in yeni.items():
        bekle(len(h) > 2000 and "<h1>" in h and '"@type":"Product"' in h,
              "3 %s: sayfa uretilmedi/eksik (h1 + Product JSON-LD yok)" % pid)

    # ---------------------------------------------------------------- 8
    for pid, h in yeni.items():
        refler = [u for u in (_CSS_LINK_RE.findall(h) + _SCRIPT_SRC_RE.findall(h))
                  if u.startswith(build.VARLIK_URL_ONEK)]
        if not bekle(len(refler) >= 2,
                     "8 %s: /varlik/ referansi < 2 (css + js beklenir) -> %r" % (pid, refler)):
            continue
        for u in refler:
            ad = u[len(build.VARLIK_URL_ONEK):]
            yol = os.path.join(build.VARLIK_DIR, ad)
            if not bekle(os.path.isfile(yol), "8 %s: referans edilen varlik DISKTE YOK: %s"
                         % (pid, ad)):
                continue
            with io.open(yol, encoding="utf-8") as f:
                govde = f.read()
            beklenen = "%s-%s%s" % (ad.rsplit("-", 1)[0], build.varlik_hash(govde),
                                    os.path.splitext(ad)[1])
            bekle(beklenen == ad,
                  "8 %s: dosya adi kendi BAYTLARINDAN turemiyor (%s != %s)"
                  % (pid, ad, beklenen))
        bekle("<style>" in h, "8 %s: satir-ici kritik cekirdek <style> yok" % pid)

    # ---------------------------------------------------------------- 6 + 7
    ornek_css = "a{color:red}\n"
    u1 = build.varlik_adres("test", "css", ornek_css)
    u2 = build.varlik_adres("test", "css", ornek_css)
    bekle(u1 == u2, "6 ayni icerik FARKLI ad uretti (%s != %s) — gereksiz cache-miss" % (u1, u2))
    u3 = build.varlik_adres("test", "css", ornek_css + "b{color:blue}\n")
    bekle(u1 != u3, "7 icerik degisti ama ad AYNI kaldi (%s) — BAYAT varlik servis edilir" % u1)
    # eksen 7'nin GERCEK yuzeydeki hali: HARICI dosyaya giden CSS'in tek karakteri
    # degisince sayfadaki CSS adresi degismeli. Capa bilerek KRITIK CEKIRDEGIN DISINDA
    # (kalan bolgede) secilir — cekirdekteki capa harici dosyayi zaten degistirmezdi.
    asil_css = build.PAGE_CSS
    try:
        css_ref_once = _CSS_LINK_RE.findall(next(iter(yeni.values())))
        build.PAGE_CSS = asil_css.replace(".help-cta-btn:hover{background:#1ebe5a}",
                                          ".help-cta-btn:hover{background:#1ebe5b}")
        bekle(build.PAGE_CSS != asil_css, "7 mutasyon capasi PAGE_CSS'te bulunamadi (help-cta-btn)")
        h2 = build.render_product(secim[0][1], urunler, None)
        css_ref_sonra = _CSS_LINK_RE.findall(h2)
        bekle(css_ref_once != css_ref_sonra,
              "7 PAGE_CSS bir bayt degisti ama sayfadaki CSS adresi AYNI (%r)" % css_ref_once)
    finally:
        build.PAGE_CSS = asil_css

    # ---------------------------------------------------------------- 9 (ikiz yok)
    cekirdek, kalan = build.css_bol(build.PAGE_CSS)
    bekle(cekirdek + build.KRITIK_CSS_SINIRI + kalan == build.PAGE_CSS,
          "9 cekirdek + sinir + kalan KAYNAGA esit degil — satir-ici blok kaynagin DILIMI degil")
    try:
        capa = "--navy:#12294d"
        bekle(capa in cekirdek, "9 mutasyon capasi kritik cekirdekte yok (%s)" % capa)
        build.PAGE_CSS = asil_css.replace(capa, "--navy:#12294e")
        h3 = build.render_product(secim[0][1], urunler, None)
        eski_ici = css_govdeleri(yeni[secim[0][1]["id"]])[0]
        yeni_ici = css_govdeleri(h3)[0]
        bekle(eski_ici != yeni_ici,
              "9 IKIZ TANIM: kritik cekirdek KAYNAKTAN turemiyor — kaynagi bozan mutant "
              "satir-ici ciktiyi DEGISTIRMEDI")
    finally:
        build.PAGE_CSS = asil_css

    # ---------------------------------------------------------------- 10 (fail-closed)
    def patlar(fn, ad):
        try:
            fn()
        except Exception:
            return True
        HATALAR.append("10 FAIL-OPEN: %s hata vermedi (sessizce ciplak sayfa uretilirdi)" % ad)
        return False

    patlar(lambda: build.varlik_adres("test", "css", "   \n  "), "bos govde")
    patlar(lambda: build.varlik_adres("test", "xml", "x"), "bilinmeyen uzanti")
    patlar(lambda: build.css_bol("a{color:red}"), "sinir isareti olmayan CSS")
    try:
        build.PAGE_CSS = asil_css.replace(build.KRITIK_CSS_SINIRI, "")
        patlar(lambda: build.render_product(secim[0][1], urunler, None),
               "sinir isareti silinmis PAGE_CSS ile render_product")
    finally:
        build.PAGE_CSS = asil_css
    eski_dir = build.VARLIK_DIR
    try:
        build.VARLIK_DIR = os.path.join(ROOT, "urunler.json", "olmaz")   # dosya altinda dizin
        patlar(lambda: build.varlik_adres("test", "css", "a{color:red}\n"), "yazilamayan dizin")
    finally:
        build.VARLIK_DIR = eski_dir

    # varlik dizinini olcum icin temizle-yeniden uret (test artifaktlari cikmasin)
    shutil.rmtree(build.VARLIK_DIR, ignore_errors=True)
    build._VARLIK_ONBELLEK.clear()
    yeni = {}
    for _, p in secim:
        yeni[p["id"]] = build.render_product(p, urunler, None)

    # ---------------------------------------------------------------- 1 / 1b / 2 / 4 / 5
    # REFERANS GORUNURLUGU: kayit hali + yas + birikmis beyan sayisi HER kosumda basilir.
    # Bayatlik sessizce buyumesin diye sayi rapora girer ([[bayat-kabul-testi]]).
    # 🔴 IKINCI AYRISTIRMA YOK: hukum TEK kanonik yerden (kayit_hukmu) gelir, burasi
    # yalnizca GEREKCEYI okur. Onceki halde burada ikinci bir kural vardi ve aradaki
    # bosluktan iki sekil FAIL-OPEN geciyordu ([[ikiz-tanim-sessiz-ayrisma]]).
    kayit, red = referans_kaydi()
    ref = eski_ref()
    beyan_ozeti = ("beyan: %d satir + %d gorunur-metin + %d css"
                   % (len(BILEREK_DEGISEN_TAM) + len(BILEREK_DEGISEN),
                      len(BILEREK_DEGISEN_METIN), len(BILEREK_DEGISEN_CSS)))
    if kayit and ref:
        yas = git("log", "-1", "--format=%cr", ref)
        BILGI.append("kiyas referansi: KAYITLI %s (%s) · tazelendi %s · %s"
                     % (ref[:10], (yas or "?").strip(),
                        kayit.get("tazelendi", "?"), beyan_ozeti))
    elif red == KAYIT_YOK:
        BILGI.append("kiyas referansi: TOHUM KESFI %s (kayit dosyasi YOK -> "
                     "`python3 tools/varlik-test.py --referans-tazele` ile kaydet) · %s"
                     % ((ref or "?")[:10], beyan_ozeti))
    else:
        # TESHIS METNI OLCTUGU SEYI SOYLER: tohuma FIILEN dusuluyor (olcum oradan kosar),
        # ama HUKUM yesil DEGIL. Onceki metin "tohum kesfine DUSULMEDI" diyordu; bu
        # yanlisti ve teshisi yanlis yere baktiriyordu.
        BILGI.append("kiyas referansi: KAYIT GECERSIZ -> olcum TOHUM %s uzerinden kosuldu"
                     % ((ref or "?")[:10]))
        OLCULEMEDI.append(
            "kiyas referansi kaydi GECERSIZ (%s): %s — olcum TOHUM referansina (%s) karsi "
            "kosuldu, HUKUM OLCULEMEDI (yesil DEGIL). Kaydi duzelt ya da sil."
            % (REFERANS_DOSYASI, red, (ref or "?")[:10]))
    if ref is None:
        OLCULEMEDI.append("1/1b/2 ESKI uretici bulunamadi (SIG depo ya da yeniden yazilmis "
                          "gecmis) — esdegerlik ve ortalama-dusus eksenleri OLCULEMEDI")
    else:
        tmp = tempfile.mkdtemp(prefix="varlik-eski-")
        try:
            if not eski_kok_kur(tmp, ref):
                OLCULEMEDI.append("1/1b/2 eski agac kurulamadi (%s)" % ref[:10])
            else:
                eski, hata = eski_render(tmp, idler)
                if eski is None:
                    OLCULEMEDI.append("1/1b/2 eski uretici kosmadi: %s" % hata)
                else:
                    olc(eski, yeni, secim, urunler, ref)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    rapor()


def olc(eski, yeni, secim, urunler, ref):
    # ------------------------------------------------------------------ 1
    eslesen_beyan = set()
    # URUN-BASI BEYANLAR (11 Agu): metin/deger beyanlari elle yazilmaz, urunun KENDI
    # verisinden turetilir (bkz. _malzeme_tasima_beyani / _seri_etiket_beyani). Statik
    # tablonun SONUNA eklenir -> 1c bayat-beyan hijyeninin indeksleri KAYMAZ.
    urun_ix = {u["id"]: u for (_e, u) in secim}
    # K124 saglik kolu icin TAM katalog id kumesi (yetim hedef olcumu). Kume BOS
    # cikarsa saglik kolu fail-closed davranir (bkz. turetilmis_hal_saglikli_mi).
    katalog_idler = {u.get("id") for u in (urunler or [])
                     if isinstance(u, dict) and u.get("id")}
    # CIKARIM BEYANI (16 Agu): kasitli degisiklikleri kayit mekanizmasiyla geciren
    # beyan dosyasi okunur; bulgular siniflanir ve beyan kapsaminda olanlar BASILIR,
    # kapsam disi + beyan edilemez olanlar HATA kalir (kapinin varsayilan KATI davranisi).
    beyan_veri = _beyan_dosyasi_oku()
    if beyan_veri is not None:
        gecerli_yapi, _ = _beyan_yapisi_gecerli_mi(beyan_veri)
        beyan_kayitlari = beyan_veri["beyanlar"] if gecerli_yapi else []
    else:
        beyan_kayitlari = []
    for pid in yeni:
        p_urun = urun_ix.get(pid, {"id": pid})
        seri_metin, seri_deger = _seri_etiket_beyani(p_urun)
        aralik_metin, aralik_deger = _ilan_araligi_beyani(p_urun)
        tablo = (BILEREK_DEGISEN_METIN + _malzeme_tasima_beyani(p_urun) + seri_metin
                 + _onsecim_tutar_beyani(p_urun) + aralik_metin)
        kayip = cikarim_kaybi(iskelet(eski[pid]), iskelet(yeni[pid]),
                              beyan_tablosu=tablo,
                              deger_beyani=seri_deger + aralik_deger,
                              eslesen_kovasi=eslesen_beyan)
        # BEYANLA GECEN BULGULAR baskiya girer; kapsam disi + beyan edilemez HATA olur.
        gecen, kd, be, yb = cikarim_beyan_degerlendir(kayip, p_urun, beyan_kayitlari)
        # K124 — TURETILMIS SINIF: beyan aranmaz, YENI HALIN SAGLIGI olculur. Saglik
        # gecmezse asagidaki kollar DEGISMEZ (bulgu `kd`de kalir, beyan aranir, yoksa
        # KIRMIZI): bu kol yalnizca EKLER, hicbir yolu acmaz.
        # 13 Eyl 2026: hukum `turetilmis_hukum`da (sentetik fiksturle olculur); KIRIK
        # hedef (yetim / gelenek disi anahtar) BEYANLA GECMIS bulguda da KIRMIZI yanar.
        kd, gecen, _t_bilgi, _t_hata = turetilmis_hukum(
            kd, gecen, eski[pid], yeni[pid], p_urun, katalog_idler)
        BILGI.extend(_t_bilgi)
        HATALAR.extend(_t_hata)
        for _b, _k, _g in gecen:
            BILGI.append("BEYAN KAPSAMINDA: %s | %s | %s -> %s"
                         % (pid, _k, _b[:60], _g[:50]))
        for _b, _sebep in be:
            HATALAR.append("1 %s: BEYAN EDILEMEZ bulgu beyan kapsaminda bile "
                           "giremez (%s): %s" % (pid, _sebep, _b[:80]))
        if kd:
            # Beyan YOKken "kapsam_disi" bos degil ama yine HATA: bugunku KATI davranis
            # aynen korunur. Bu durumda kelime "KAPSAMI DISINDA" yerine bugunku orijinal
            # "CIKARIM KAYBI" kullanilir ki okuyan kisi beyan dosyasinin yoklugundan
            # haberdar olsun ([[kapsam-tek-tur-tehlikesi]]).
            if beyan_kayitlari:
                HATALAR.append("1 %s: CIKARIM KAYBI beyan KAPSAMI DISINDA (%d): %s"
                               % (pid, len(kd), kd[:2]))
            else:
                HATALAR.append("1 %s: CIKARIM KAYBI (%d): %s"
                               % (pid, len(kd), kd[:2]))
        for _kayit, _gerekce in yb:
            HATALAR.append("1 %s: beyan dosyasi YAPISAL BOZUK KAYIT tasiyor: %s"
                           % (pid, _gerekce))
        bekle(urun_verisi(eski[pid]).get("URUN") == urun_verisi(yeni[pid]).get("URUN"),
              "1b %s: URUN verisi ayristi" % pid)
        for ad in ("URUN_SEMA", "URUN_KONFIGUR"):
            bekle(urun_verisi(eski[pid]).get(ad) == urun_verisi(yeni[pid]).get(ad),
                  "1b %s: %s verisi ayristi" % (pid, ad))

    # 1c BAYAT BEYAN HIJYENI (S3): hicbir ornek sayfada tutmayan bir gorunur-metin
    # beyani sessizce durmaz. Yoksa tablo zamanla OLU MUAFIYET DEPOSUNA doner ve
    # ilerideki gercek bir metin kaybini maskeleyebilecek girisler birikir.
    for i, (eski_m, _yeni_m, gerekce) in enumerate(BILEREK_DEGISEN_METIN):
        bekle(i in eslesen_beyan,
              "1c BAYAT GORUNUR-METIN BEYANI (hicbir ornek sayfada eslesmedi): %r "
              "-> gerekce: %s. Metin artik yoksa GIRISI SIL." % (_norm(eski_m)[:70], gerekce))

    # ------------------------------------------------------------------ 2 (CSS: BAYT-ESIT)
    pid0 = secim[0][1]["id"]
    e_css = css_govdeleri(eski[pid0])
    y_css = css_govdeleri(yeni[pid0])
    y_ref = [u for u in _CSS_LINK_RE.findall(yeni[pid0]) if u.startswith(build.VARLIK_URL_ONEK)]
    harici = ""
    for u in y_ref:
        with io.open(os.path.join(build.VARLIK_DIR, u[len(build.VARLIK_URL_ONEK):]),
                     encoding="utf-8") as f:
            harici += f.read()
    bekle(e_css and y_css, "2 CSS govdesi bulunamadi (olcum bosa dustu)")
    if e_css and y_css:
        # BEYAN EDILEN kurallar ESKI hallerine cevrilir; ARTAKALAN her fark hala KIRMIZI.
        y_tam, css_beyan_hatalari = css_beyani_uygula(y_css[0] + harici)
        for _h in css_beyan_hatalari:
            HATALAR.append(_h)
        bekle(y_tam == e_css[0],
              "2 CSS KAYIP/EKLENTI: satir-ici cekirdek + harici dosya, eski gomulu CSS'e "
              "BAYT-ESIT degil (%d + %d, beyan sonrasi %d != %d)"
              % (len(y_css[0]), len(harici), len(y_tam), len(e_css[0])))
        # sayfaya ozel ek <style> bloklari da aynen durmali
        bekle(e_css[1:] == y_css[1:], "2 sayfaya ozel satir-ici <style> bloklari ayristi")

    # ------------------------------------------------------------------ 2 (JS: kayip/eklenti yok)
    for pid in yeni:
        e_js = "\n".join(js_govdeleri(eski[pid]))
        y_js = "\n".join(js_govdeleri(yeni[pid]))
        for u in _SCRIPT_SRC_RE.findall(yeni[pid]):
            if not u.startswith(build.VARLIK_URL_ONEK):
                continue
            with io.open(os.path.join(build.VARLIK_DIR, u[len(build.VARLIK_URL_ONEK):]),
                         encoding="utf-8") as f:
                y_js += "\n" + f.read()
        ec, yc = satir_cantasi(e_js), satir_cantasi(y_js)
        kayip = [k for k in sorted((ec - yc).elements()) if not _bilerek_degisti(k)]
        eklenti = [k for k in sorted((yc - ec).elements()) if not _bilerek_degisti(k)]
        bekle(not kayip, "2 %s: JS KAYIP (%d satir) ilk: %r" % (pid, len(kayip), kayip[:2]))
        bekle(not eklenti, "2 %s: JS EKLENTI (%d satir) ilk: %r" % (pid, len(eklenti), eklenti[:2]))

    # ------------------------------------------------------------------ 4 / 5
    n = float(len(yeni))
    e_ort = sum(len(eski[p].encode("utf-8")) for p in yeni) / n
    y_ort = sum(len(yeni[p].encode("utf-8")) for p in yeni) / n
    vbayt = sum(os.path.getsize(os.path.join(build.VARLIK_DIR, a))
                for a in os.listdir(build.VARLIK_DIR))
    katalog = len(urunler)
    e_gb = e_ort * katalog / 1e9
    y_gb = (y_ort * katalog + vbayt) / 1e9
    bekle(y_ort < e_ort * 0.85,
          "4 ortalama sayfa bayti yeterince dusmedi: %.0f -> %.0f" % (e_ort, y_ort))
    bekle(y_gb < e_gb, "5 toplam yayin tahmini dusmedi: %.3f -> %.3f GB" % (e_gb, y_gb))
    BILGI.append("kiyas referansi: %s" % ref[:10])
    BILGI.append("ORTALAMA sayfa bayti: %.0f -> %.0f (%.1f%% dusus)"
                 % (e_ort, y_ort, 100.0 * (e_ort - y_ort) / e_ort))
    BILGI.append("TOPLAM yayin tahmini (%d urun): %.3f GB -> %.3f GB (varlik %d bayt)"
                 % (katalog, e_gb, y_gb, vbayt))


def rapor():
    for b in BILGI:
        print("  · " + b)
    if OLCULEMEDI:
        for o in OLCULEMEDI:
            print("OLCULEMEDI: " + o)
    if HATALAR:
        print("\nKIRMIZI (%d):" % len(HATALAR))
        for h in HATALAR:
            print("  - " + h)
        sys.exit(1)
    if OLCULEMEDI:
        print("\nOLCULEMEDI -> yesil DEGIL (rc 2)")
        sys.exit(2)
    print("\nOK: varlik kapisi — 10 eksen yesil.")


if __name__ == "__main__":
    main()
