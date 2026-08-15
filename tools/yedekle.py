#!/usr/bin/env python3
"""Makine olursa kaybolacak yeri-doldurulamaz yerel dosyalari Drive'a yedekler.
Drive yolu tools/drive_yolu.py ile cozulur (kayitli .stl-backup-dir bayatsa kendini duzeltir).
Hedef: <Pruvo>/backup-v2/  (memory klasoru + global skill'ler + ~/.claude altindaki elle
yazilmis agaclar: zamanlanmis gorev tanimlari / cron nobeti / planlar
+ .urun-kaynaklari.json + baglam .md'leri).

SIRLAR — UC AYRI REJIM, KARISTIRMA:
  1. REPO KOKUNDEKI SANCAKLI SIR LISTESI (.thingiverse-token, .r2-credentials.json, ...):
     🔴 8 AGU 2026 — YAZMA YOLU KAPANDI (Okan karari: "jetonlari yedekten cikar").
     Bu dosyalar HICBIR BAYRAKLA yedege GIRMEZ; yalniz bu makinede dururlar.
     Kaybolmalari hicbir seyi kirmaz: hepsi kaynagindan yeniden uretilebilir (SIR_KOKENI).
     "--sirlar" EMEKLI oldu — kabul edilir (bilinmeyen-bayrak fail-closed'i tetiklemesin)
     ama KAPSAMI DEGISTIRMEZ. Eleme kanonik kumeden turer (REPO_SIR + SIR_ADLARI),
     ELLE IKINCI LISTE ACILMAZ; elenen her kalem ADIYLA sayilir (bkz. repo_kok_ayrimi).
     Yedek KOKUNDE onceki surumlerden kalan kopyalar "--sir-temizle" ile FAIL-CLOSED
     silinir (yereldeki asil VAR+okunabilir degilse SILINMEZ; bkz. yedek_kok_sir_temizle).
     🔴 DIKKAT (1 Agu 2026 hizalamasi): "PAYLASMA" yalniz --sirlar'a OZGU DEGILDIR.
     31 Tem EK KAPSAM genislemesinden beri VARSAYILAN kosum da ticari gizli icerik
     tasir (raporlar/ — IBAN/VKN gecen tasinma envanteri —, .tedarikci-fiyat/,
     .uyelik-*). Bu yedek klasoru HICBIR KOSUMDA paylasilabilir degildir.
  2. ~/.claude/skills AGACI: burada sir OLMAMASI gerekir; agac vetted degil (elle duzenlenen,
     git disi bir alan) -> ad kara-listesi + ad deseni + ICERIK imzasi ile KOSULSUZ elenir.
     Bu filtre "--sirlar" ile ACILMAZ: sancakli liste bilinen 5 dosyadir, skills agaci degil.
     Elenen her dosya SEBEBIYLE raporlanir (sessiz atlamak yok). Icerik imzasi bulunursa
     yalniz IMZA SINIFI basilir — eslesen metin ASLA ekrana/loga yazilmaz.
  3. ~/.claude ALTINDAKI ELLE YAZILMIS AGACLAR (7 Agu 2026, YENI KAPSAM — AGAC_KAPSAMI):
     scheduled-tasks (gorev TANIM metinleri) · cron (nobet surucusu + crontab) ·
     plans (plan belgeleri). `cron` agacinin ICINDE gercek `.ci-token` / `.gh-token`
     duruyor ve hedef ORTAK Drive. Bu yuzden eleme kara-liste (desen) DEGIL, ACIK
     ALLOWLIST ile yapilir: yalniz agacin izinli uzantilari girer, GERI KALAN HER SEY
     (uzantisiz jetonlar dahil) disarida kalir ve SEBEBIYLE SAYILIR. Sir nobeti
     allowlist'ten ONCE kosar (bkz. agac_plani: her katman TEK BASINA olculsun) —
     bu sayede `.log` gibi allowlist disi dosyalarin ICERIGI de taranmis olur.

BAYAT SIR NOBETI: bu filtre 26 Tem'de eklendi; ondan onceki surum skills agacini FILTRESIZ
copytree ile kopyaliyordu. Hedefte elenmis bir dosyanin ESKI kopyasi duruyorsa gurultulu
uyarilir; "--sir-temizle" ile silinir (varsayilan SILMEZ — yedekten veri silmek elle onaylanir).

TAZELIK DAMGASI (26 Tem): kosum sonunda `backup/.son-yedek.json` yazilir (zaman + sayilar).
NEDEN DAMGA, NEDEN MTIME DEGIL: shutil.copy2 KAYNAK mtime'ini korur -> yedekteki dosyanin
mtime'i "yedek ne zaman kosuldu"yu DEGIL "kaynak ne zaman duzenlendi"yi soyler. Tazeligi
mtime'dan olcmek yaniltir (26 Tem: Drive'daki dosyalar 21 Tem gorunuyordu cunku kaynak o
tarihliydi). Damgayi `tools/durum.py` panosu okur -> bayatlik GORUNUR olur.

KILIT (26 Tem, `.yedek.lock`): bu betik artik HER push'ta (pre-push hook) kosuyor ve bu
repoda paralel oturum NORMAL -> eszamanli iki kosum AYNI hedefe yazardi (yarim/karismis
yedek) ve sonda damga yine "tam" derdi = SESSIZ HATA. Cozum: ROOT/.yedek.lock uzerinde
flock (`.urunler.lock` deseni).
  - NON-BLOCKING (LOCK_NB): kilit doluysa BEKLEMEYIZ -> push ASLA yavaslamaz/durmaz
    (pre-push fail-open sozlesmesi). Ayni isi zaten oteki kosum yapiyor.
  - ATLANAN kosum damgada `son_atlama*` alanlarina yazilir; GUVEN alanlarina (zaman/
    tam/sayilar) DOKUNMAZ -> atlanan kosum ASLA "tam yedek aldim" demez.
  - ATLAMA ZARARSIZ MI: iki OLCUM birden gerekir, biri bile tutmazsa pano UYARIR.
    (1) `son_atlama_kapsandi` — kosan yedek BASLARKEN butun degisiklikler yerinde
        miydi (atlama_kapsandi_mi)?  (2) `son_atlama_sahip_baslangici` — beklenen o
    kosum damgayi GERCEKTEN yazdi mi? Tek basina (1) bir VARSAYIMDIR: sahip kilidi
    alip asilir/olurse dosya yedege hic girmez ve pano esige kadar (2 gun) "taze"
    der. Kilit imzasi bu yuzden TAM HASSAS (repr) yazilir ve damganin `baslangic`i
    kilit alis aniyla BIREBIR AYNI sayidir — cozum esitlikle yapilabilsin diye
    (`%.3f` yuvarlamasi olculdu: 10000 kararin ~%46'si yanlis, test %37 flake).
  - `baslangic` alani: damga artik kosumun BASLANGIC anini da tasir. Kopyalama atomik
    degil; kosum basladiktan SONRA degisen dosya yedege girmemis olabilir. Bu yuzden
    hem `--gerekliyse` karari hem panonun "atlama kapsandi mi" karari `zaman` (bitis)
    degil `baslangic` ile verilir. Yoksa "atlandi" uyarisi ya hic temizlenmez ya da
    kapsanmayan bir degisiklik "taze" sayilir.
  - KILIT NEDEN BAYATLAMAZ: flock cekirdek tarafindan tutulur, surec olunce (crash,
    kill -9) OTOMATIK birakilir -> pid-dosyasi kilitlerindeki "olu surec sonsuza dek
    bloklar" sinifi burada YOK. Geriye kalan `.yedek.lock` DOSYASI 0 bayttir, kilit
    degildir; bilerek SILMEYIZ (silmek iki surecin AYRI inode kilitlemesine yol acar).
    Geriye tek patolojik hal kalir: YASAYAN ama asilmis sahip (cevapsiz Drive mount).
    Onu KIRMAYIZ (yasayan yaziciyi kirmak tam da onlemeye calistigimiz bozulmadir);
    GORUNUR yapariz: kilit dosyasina pid+baslangic yazilir, atlayan kosum bunu basar,
    1 saati asan sahip icin gurultulu uyarir, damga tazelenmedigi icin pano esikte
    "YEDEK BAYAT" der.

K1 (27 Tem) — `bitti=` YALNIZ TAMAMLANAN KOSUMDA: kilit izine basari isareti sadece
  _yedekle() normal donup 0 verdiginde yazilir; istisnada `hata=` yazilir ve pano
  "⚠⚠ YARIM KALMIS YEDEK" der. Eskiden `finally` istisnada da `bitti=` yaziyordu ->
  kosum ortada cokse bile pano "taze" diyordu (gercek icrayla olculdu). MESRU ATLAMA
  (kilit mesgul) bu yoldan AYRIDIR: orada kilit hic bizde olmaz, kirmiziya cevrilmez.

K3 (27 Tem) — "DEGISIKLIK YOK" != "YEDEK BAYAT": `--gerekliyse` GUNCEL yolu artik
  olcumunu damgaya yazar (`dogrulandi` + `dogrulama_imzasi`) ve pano esik asilsa bile
  "✅ GUNCEL (son gercek yedek: ...)" der. Iddia OLCUME dayanir: kaynak imzasi
  (dosya ADEDI + TOPLAM BAYT + en yeni mtime) kopyanin `kaynak_imzasi`na esit olmali;
  imza olculemezse dogrulama alani YAZILMAZ -> pano ⚪ OLCULEMEDI/BAYAT der. `kilitsiz`
  notu KOSUM-YEREL: dogrulama kosumu kilidi tuttuysa miras bayrak silinir.

K6 (31 Tem) — IMZA = KOPYA PLANI (fail-open onarimi): `kaynak_imzasi()` kendi yol
  yuruyusunu YAPMAZ; olctugu kume `yedek_plani()`dir. Eskiden ayri yuruyordu ve
  ek kokleri `os.path.join(ev, giris)` ile kuruyordu -> EK_EVLER'deki GLOB'lu
  girisler ("olcum/*.py") ne isfile ne isdir oldugu icin SESSIZCE atlaniyordu.
  Olculdu: imza 767 dosya, plan 2642; farkin 1934'u glob kapsami. O dosyalar
  degistiginde imza kimildamiyor, `--gerekliyse` "guncel" deyip YEDEGI ATLIYORDU.
  Artik imza/dogrulama/kopyalama TEK listeden turer (bkz. yedek_plani docstring'i).

EK KAPSAM (31 Tem 2026, hesap tasima denetimi): artik YALNIZ KraL evi degil, BES+BIR
evin tamami ve TUM hafiza uzaylari kapsanir -> `backup/ek/`. Ayrinti ve gerekce icin
EK_EVLER sabitinin ustundeki blogu oku. Ozet kural: "git'te varsa yedekleme" (5 ev de
uzak depoya itilmis), izlenmeyen + kirli + .git/hooks alinir, sir nobetinden gecer.

Kullanim:
    python3 tools/yedekle.py              # sirsiz (memory + skills + kaynak haritasi + .md + ek)
    python3 tools/yedekle.py --kuru       # KURU KOSUM: ne kopyalanacagini listeler, YAZMAZ
    python3 tools/yedekle.py --gerekliyse # UCUZ MOD: son damgadan beri degisiklik yoksa CIKAR
    python3 tools/yedekle.py --dogrula    # OLCUM: plandaki her dosya hedefte VAR MI (yazmaz)
    python3 tools/yedekle.py --sirlar     # EMEKLI — kapsami DEGISTIRMEZ (sir yedege girmez)
    python3 tools/yedekle.py --sir-temizle  # hedefteki sir kopyalarini SIL (kok + skills)
    python3 tools/yedekle.py --kuru-prova   # SILME PROVASI: ne silinecegini basar, SILMEZ
"""
import errno
import fcntl
import filecmp
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time


class YedekKorumaHatasi(RuntimeError):
    """Saglam kanonik yedegin supheli kaynakla ezilmesini fail-closed durdurur."""


# Korumanin ATLADIGI dosyalar: (hedef_yolu, sebep). Kosum sonunda basilir ve cikis
# kodunu KIRMIZI yapar — atlama SESSIZ olamaz, yoksa "yedek alindi" yalan olur.
_KORUMA_KARANTINA = []


# Bir kaynagin bayt VEYA JSON kayit sayisi onceki kanonigin yarısından aza dusuyorsa
# bunu normal guncelleme degil veri-kaybi adayi sayiyoruz. %50 esigi; kucuk duzenlemeleri
# engellemez, fakat yarim/yanlis filtreleme gibi kitlesel kaybi iyi yedegin ustune yazmaz.
ANI_DUSUS_ESIGI = 0.50

# Her dosya icin 20 degisik kanonik onceki surum: push-temelli sik yedekte birden cok
# kurtarma noktasi verirken Drive kullanimini sinirli tutar. Ayni icerik yeni surum acmaz.
SURUM_SAKLA = 20


# --------------------------------------------------------------- DUSUS BEYANI
# 🔴 NEDEN VAR (olculdu 15 Agu 2026): koruma dogru calisiyordu ama MESRU kucultmeyi
# yanlis kucultmeden ayirt edemiyordu. Iki gercek vaka ayni gun karantinaya dustu:
#   * `DEVAM.md` 24.578 -> 5.308 bayt — mimarin KASITLI defter sikistirmasi;
#   * `posta-kutusu-kaan-izleme-ankor.txt` 485 -> 185 bayt — ROLLING izleme ankoru.
# Ikisi de her kosumda rc=1 uretiyordu; surekli kirmizi kirmiziyi DEGERSIZLESTIRIR ve
# o dosyalarin yedegi BAYAT kalirdi. Cozum ad-bazli istisna DEGIL — kardes
# `.diriltme-izin.json` ile AYNI desende bir BEYAN: dusus BIR KEZ ve GEREKCESIYLE
# ilan edilir, kapi beyani gorunce gecirir. [[koruma-kurali-korudugunu-durdurur]]
#
# BEYAN BLANKET DEGILDIR — iki tur, ikisi de SAYIYA BAGLI:
#   "tek-seferlik": yalniz ILAN EDILEN kaynak boyutu icin gecerli. Dosya sonra baska
#                   bir boyuta duserse beyan ESLESMEZ -> yeni dusus YENI bir yargidir.
#   "surekli"     : rolling artefakt (kilit/ankor/sayac). `azami_bayt` TAVANI zorunlu:
#                   beyan ancak kaynak bu tavanin ALTINDAysa gecer. Boylece 10 MB'lik
#                   bir veri dosyasi "rolling" ilan edilerek sessizce kaybedilemez.
# Beyan dosyasi YOKSA koruma TAM GUCTEDIR (fail-closed varsayilan). Dosya BOZUKSA da
# tam guctedir + UYARI basilir; "bozuk beyan" korumayi ACAMAZ ama yedegi de DUSURMEZ
# (kosumu dusurmek, az once kapatilan sinifin ta kendisiydi).
DUSUS_BEYAN_ADI = ".yedek-dusus-izin.json"
# Yol TEMBEL cozulur: `ROOT` bu satirdan SONRA tanimlaniyor (modul yuklenirken calisma
# agaci hesaplaniyor). None = "henuz cozulmedi"; okuyucu cagri aninda ROOT'a bakar.
DUSUS_BEYAN_YOLU = None
# Kullanilan beyanlar: (dosya_adi, tur, gerekce). Kosum sonunda BASILIR — beyanla
# gecen bir dusus de SESSIZ olamaz.
_BEYAN_KULLANILDI = []
_BEYAN_UYARISI = []


def _dusus_beyani_oku(yol=None):
    """Beyan haritasi. Dosya yok/bozuksa BOS doner (koruma tam gucte kalir)."""
    yol = yol or DUSUS_BEYAN_YOLU or os.path.join(ROOT, DUSUS_BEYAN_ADI)
    try:
        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as hata:
        _BEYAN_UYARISI.append("beyan dosyasi OKUNAMADI (%s) -> koruma TAM GUCTE" % hata)
        return {}
    if not isinstance(veri, dict):
        _BEYAN_UYARISI.append("beyan dosyasi sozluk DEGIL -> koruma TAM GUCTE")
        return {}
    return veri


def _dusus_beyanli_mi(kaynak, beyanlar=None):
    """Bu kaynagin dususu ILAN EDILMIS mi? Doner: (evet_mi, tur, gerekce).

    ⚠️ Eslesme DOSYA ADI uzerindendir (kapinin hata metinleri de ad basar). Ayni ada
    sahip iki dosya varsa beyan ikisini de kapsar — bu yuzden beyan TEK BASINA yetmez,
    daima bir SAYI sartiyla birlikte olcuLur (tek-seferlik: tam boyut · surekli: tavan).
    """
    beyanlar = _dusus_beyani_oku() if beyanlar is None else beyanlar
    kayit = beyanlar.get(os.path.basename(kaynak))
    if not isinstance(kayit, dict):
        return (False, None, None)
    tur = kayit.get("tur")
    gerekce = kayit.get("gerekce") or ""
    try:
        kaynak_boyut = os.path.getsize(kaynak)
    except OSError:
        return (False, None, None)
    if tur == "tek-seferlik":
        if kayit.get("kaynak_bayt") == kaynak_boyut:
            return (True, tur, gerekce)
        return (False, None, None)
    if tur == "surekli":
        tavan = kayit.get("azami_bayt")
        if isinstance(tavan, int) and kaynak_boyut <= tavan:
            return (True, tur, gerekce)
        return (False, None, None)
    return (False, None, None)


def _beyan_gecerse(kaynak, beyanlar=None):
    """Beyan varsa kullanildi defterine yazar ve True doner."""
    evet, tur, gerekce = _dusus_beyanli_mi(kaynak, beyanlar)
    if evet:
        _BEYAN_KULLANILDI.append((os.path.basename(kaynak), tur, gerekce))
    return evet


def _json_kayit_sayisi(yol):
    """Ust seviye liste/sozluk kayit sayisi; JSON degilse None (icerik BASILMAZ)."""
    if os.path.splitext(yol)[1].lower() != ".json":
        return None
    try:
        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return len(veri) if isinstance(veri, (list, dict)) else None


def _ciddi_dusus_var(yeni, eski):
    return eski > 0 and yeni < eski * ANI_DUSUS_ESIGI


def _yedek_korumasi(kaynak, varis):
    """Sifir/ani dususu olcer; suphede kanonige tek bayt yazmadan once durur."""
    kaynak_boyut = os.path.getsize(kaynak)
    # 🔴 SIFIR BAYT = ancak KARSISINDA DOLU BIR YEDEK VARSA gerilemedir (olculdu 15 Agu):
    # kural kosulsuzdu ve `mimar-posta-kutusu.md.lock` gibi MESRU olarak daima 0 bayt olan
    # flock nobetcisini "veri kaybi" sanip TUM yedek kosumunu dusurdu -> koruma girdiginden
    # beri hicbir yedek tamamlanmadi (yani veri kaybina karsi kurulan kural, veri kaybi
    # riskini ARTIRDI). Fonksiyonun geri kalani ZATEN gerileme-temellidir; sifir kolu tek
    # basina bu ilkenin disinda kalmisti -> [[kabul-araligi-karsilastirma-araligi]].
    # Korunan hal AYNEN durur: dolu bir kanonik yedegin uzerine 0 bayt YAZILAMAZ.
    if kaynak_boyut == 0:
        if os.path.isfile(varis) and os.path.getsize(varis) > 0:
            if _beyan_gecerse(kaynak):
                return
            raise YedekKorumaHatasi(
                "YEDEK REDDEDILDI: kaynak 0 bayt; kanonik yedek DEGISMEDI (%s)" %
                os.path.basename(kaynak))
        return
    if not os.path.isfile(varis):
        return
    yedek_boyut = os.path.getsize(varis)
    if _ciddi_dusus_var(kaynak_boyut, yedek_boyut):
        if not _beyan_gecerse(kaynak):
            raise YedekKorumaHatasi(
                "YEDEK REDDEDILDI: bayt olcusu ciddi dustu (%d -> %d); kanonik DEGISMEDI"
                " (%s) — kasitliysa %s icine BEYAN yaz"
                % (yedek_boyut, kaynak_boyut, os.path.basename(kaynak),
                   DUSUS_BEYAN_ADI))
        return
    kaynak_kayit = _json_kayit_sayisi(kaynak)
    yedek_kayit = _json_kayit_sayisi(varis)
    if (kaynak_kayit is not None and yedek_kayit is not None and
            _ciddi_dusus_var(kaynak_kayit, yedek_kayit)):
        if _beyan_gecerse(kaynak):
            return
        raise YedekKorumaHatasi(
            "YEDEK REDDEDILDI: kayit olcusu ciddi dustu (%d -> %d); kanonik DEGISMEDI"
            " (%s) — kasitliysa %s icine BEYAN yaz"
            % (yedek_kayit, kaynak_kayit, os.path.basename(kaynak), DUSUS_BEYAN_ADI))


def _surum_yolu(varis):
    govde, uzanti = os.path.splitext(varis)
    damga = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    aday = "%s.%s%s" % (govde, damga, uzanti)
    sira = 1
    while os.path.exists(aday):
        aday = "%s.%s-%02d%s" % (govde, damga, sira, uzanti)
        sira += 1
    return aday


def _surumleri_buda(varis):
    govde, uzanti = os.path.splitext(varis)
    desen = "%s.[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9]*%s" % (govde, uzanti)
    surumler = sorted(glob.glob(desen), key=os.path.getmtime, reverse=True)
    for eski in surumler[SURUM_SAKLA:]:
        os.unlink(eski)


def _ham_drive_kopyala(kaynak, varis):
    """Icerigi DAIMA kopyala; metadata reddini yut ama GORUNUR birak.

    🔴 OLCULDU (14 Agu 2026): hedef Google Drive **Ortak Drive** (CloudStorage) baglama
    noktasi. Klasorler YAZILABILIR (sonda: 5/5 basamak rc=0) ama saglayici genisletilmis
    oznitelik/metadata yazmayi REDDEDIYOR (`xattr -l` her seviyede EPERM). `shutil.copy2`
    icerikle BIRLIKTE metadata da kopyaladigi icin `[Errno 1] Operation not permitted`
    firlatiyor ve TUM yedegi dusuruyordu -> depo gunlerce yedeksiz kaldi.

    Ayrim: ICERIK kaybi KABUL EDILEMEZ, metadata kaybi kabul edilebilir (tazelik zaten
    mtime'dan degil DAMGA'dan turer — bkz. dosya basligi). Bu yuzden once `copy2`
    denenir (mtime korunur; artimli kopyalama kararlari ona bakar), reddedilirse icerik
    `copy` ile yazilir ve mtime AYRICA denenir. Metadata yine reddedilirse SESSIZ
    gecilmez: sayac artar, ozet satirinda basilir.
    """
    try:
        shutil.copy2(kaynak, varis)
        return True
    except OSError as e:
        if e.errno not in (errno.EPERM, errno.EACCES, errno.ENOTSUP, errno.EOPNOTSUPP):
            raise
    shutil.copy(kaynak, varis)          # ICERIK: burada hata olursa YUTULMAZ, yukari gider
    try:
        os.utime(varis, (os.path.getatime(kaynak), os.path.getmtime(kaynak)))
    except OSError:
        _DRIVE_METADATA_REDDI.append(varis)
    return True


def _drive_kopyala(kaynak, varis):
    """Tum yedek siniflari icin koruma + tarihli surum + kanonik guncelleme."""
    _yedek_korumasi(kaynak, varis)
    if os.path.isfile(varis) and filecmp.cmp(kaynak, varis, shallow=False):
        return True
    surum = None
    if os.path.isfile(varis):
        surum = _surum_yolu(varis)
        shutil.copyfile(varis, surum)
    try:
        sonuc = _ham_drive_kopyala(kaynak, varis)
    except BaseException:
        # Kanonik yazim baslamadan once alinmis surum kurtarma noktasi olarak KALIR.
        raise
    if surum is not None:
        _surumleri_buda(varis)
    return sonuc


_DRIVE_METADATA_REDDI = []


def ana_calisma_agaci(taban=None):
    """Repo koku — DAIMA ANA calisma agaci, worktree DEGIL.

    `taban` verilirse o dizinden cozer (test bir WORKTREE yolu verip ANA agaci
    dondurdugunu kanitlayabilsin diye; varsayilan betigin kendi konumu).

    🔴 NEDEN (F1, 26 Tem — "sahte tazelik" hatasi): kok eskiden __file__'dan
    cozuluyordu (dirname(__file__)/..). Hook ise `git rev-parse --show-toplevel`
    kullanir -> WORKTREE'den push edilince ROOT=WORKTREE oluyordu. Worktree'de
    .urun-kaynaklari.json ve DEVAM-ARSIV.md gitignore'lu (YOK) -> o iki dosya
    TAZELENMIYOR ama TAM GUVEN damgasi yaziliyor ve panonun saati sifirlaniyordu.
    Bu repoda normal push ZATEN worktree push'u (mühendisler worktree'de calisir)
    -> hata surekli tetiklenirdi. Olculdu: pano "14 dk once" derken
    .urun-kaynaklari.json yedegi ~21 saat, DEVAM-ARSIV.md ~2 gun bayatti.
    Ayrica worktree'nin CLAUDE.md/DEVAM.md fotografi ana kopyanin UZERINE yaziliyordu.

    --git-common-dir worktree'de de ANA .git'i gosterir (durum.py'nin ana_repo()
    ile ayni yontem). Git yoksa __file__ tabanina duser."""
    if taban is None:
        taban = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    try:
        p = subprocess.run(["git", "-C", taban, "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True)
        ortak = p.stdout.strip()
        if p.returncode == 0 and ortak:
            return os.path.dirname(ortak.rstrip("/"))
    except OSError:
        pass
    return taban


ROOT = ana_calisma_agaci()
MEMORY = os.path.expanduser("~/.claude/projects/-Users-okan-dev-pruvo/memory")
# 🔴 YEDEK KOK KLASORU — TEK KAYNAK (14 Agu 2026). Eskiden bes ayri yerde elle
# `backup` yaziliyordu. Ad DEGISTI cunku eski `backup/` altindaki nesneler Ortak
# Drive'da BIZIM kimligimizle kullanilamiyor hale gelmisti: klasoru LISTELEMEK EPERM
# veriyordu (olculdu), oysa ayni klasorde yeni dosya olusturma/ezme/silme SERBESTTI.
# Uc hipotez olcerek elendi (bayat kilit · macOS TCC · metadata/xattr); kalan sebep
# eski nesnelerin Drive sahipligi. Taze kok bu sinifi tumden atlar.
# Eski klasor SILINMEDI: dogrulanmis ilk yeni yedekten SONRA bu kokun ICINE tasinir
# (`_eski-backup-2026-08-14`), boylece yedek TEK YERDE toplanir.
YEDEK_KOK_ADI = "backup-v2"
SKILLS = os.path.expanduser("~/.claude/skills")

# ========== ~/.claude ALTINDAKI ELLE YAZILMIS AGACLAR (7 Agu 2026) ===========
# 🔴 NEDEN (olculdu): bu agaclar yedek kapsaminda HIC GECMIYORDU -> diskte TEK
# KOPYA, surum gecmisi YOK, hicbir depoda karsiligi YOK. Bu makinede 2-3 gunde bir
# hesap rotasyonu var; KOSUM KAYITLARI zaten hesapla olur, ama bu METINLER de
# yedeksizse yordamin KENDISI kalici olarak kaybolur (yeniden yazilamaz).
GOREVLER = os.path.expanduser("~/.claude/scheduled-tasks")   # gorev TANIM metinleri
CRON = os.path.expanduser("~/.claude/cron")                  # nobet surucusu + crontab
PLANLAR = os.path.expanduser("~/.claude/plans")              # elle yazilmis plan belgeleri

# 🔴 ACIK ALLOWLIST — FAIL-CLOSED, DESEN DEGIL.
# Bu agaclar JETON YUZEYINE KOMSU, hatta `cron` agacinin ICINDE gercek `.ci-token`
# ve `.gh-token` duruyor; yedek hedefi ise ORTAK Drive'dir.
# Kara-liste (desen) yaklasimi burada YETMEZ: desen listesi "bugun bildigimiz"
# jeton adlarini eler, YARIN eklenecek adi ELEMEZ (sessiz sizinti sinifi). Bu
# yuzden kural TERSINE cevrildi: yalniz ACIKCA IZINLI uzantilar yedege girer,
# geri kalan HER SEY disarida kalir ve SEBEBIYLE SAYILIR. Jeton dosyalari klasik
# olarak UZANTISIZDIR -> adlarini onceden bilmemize GEREK KALMADAN elenirler.
#
# TEK TABLO, UC AGAC — BILEREK: ucu de ayni hukumden gecer. Her agac icin ayri
# fonksiyon yazsaydik IKIZ TANIM olurdu ve bu depoda olculmus bicimde sessizce
# AYRISIRDI (biri sertlesir, otekinde delik acik kalir).
#
# (etiket, kaynak kok, backup/ altindaki hedef klasor, IZINLI uzantilar)
AGAC_KAPSAMI = (
    # Gorev tanimi Markdown'dir; yaninda ayar/olcum JSON ve duz metin not olabilir.
    ("gorev", GOREVLER, "gorev-tanimlari", (".md", ".txt", ".json")),
    # Nobet surucusu bir kabuk betigi, zamanlama ise crontab metnidir.
    # 🔴 `.log` BILEREK IZINSIZ: log turetilmis (yeniden uretilir), SINIRSIZ BUYUR
    # ve icinde kosum ciktisi (jeton yankisi) tasiyabilir. Yedege ALINMAZ, ama
    # SESSIZCE dusmez: kac dosya, hangi sebeple elendigi SAYILIR ve BASILIR.
    ("cron", CRON, "cron-nobet", (".sh", ".crontab", ".md", ".txt", ".json")),
    # Plan belgeleri saf Markdown.
    ("plan", PLANLAR, "planlar", (".md", ".txt", ".json")),
)

# Repo kokunden BEKLENEN dosyalar. Biri eksikse yedek KISMIDIR -> tam guven
# damgasi ATILMAZ (bkz. damga_yaz "tam" alani). Ilke: eksik yedek, eksik oldugunu SOYLER.
#
# 🔴 30 TEM — SESSIZ KAPSAM DARALMASI ONARILDI (yedekle-test.py'nin 179 kontrolunun 1'i
# aylardir KIRMIZI idi: "_repo_dosyalari 4 dosya donduruyor -> 3"). Liste "CLAUDE.md"
# diyordu; oysa tek kaynak AGENTS.md'ye gecildiginde CLAUDE.md bir SYMLINK oldu ve
# _repo_dosyalari()'nin `not islink` suzgeci onu ELEDI. Sonuc: ajan baglam dosyasi
# (AGENTS.md) HICBIR yedege girmiyordu — ustelik gitignore'da oldugu icin git'te de
# kopyasi yok, yani disk kaybinda TAMAMEN gidiyordu. GERCEK Drive damgasi bunu
# dogruluyor: "repo": 3. Liste artik GERCEK DOSYAYI (AGENTS.md) adlandirir.
# Tekrari repo_eksikleri() engeller: BEKLENEN bir ad symlink'e donerse artik SESSIZCE
# dusmez, "eksik" sayilir -> damga tam=False + pano uyarir.
REPO_BEKLENEN = (".urun-kaynaklari.json", "AGENTS.md", "DEVAM.md", "DEVAM-ARSIV.md")
REPO_SIR = (".thingiverse-token", ".r2-credentials.json", ".stl-backup-dir",
            ".onizleme-kapat-anahtar", ".mukerrer-istisna.json")

# ============================ EK KAPSAM (31 Tem 2026) ========================
# 🔴 NEDEN: hesap tasima denetiminde olculdu — bu betik 5 evin YALNIZ BIRINI
# (KraL) ve o evin yalniz 4 kok dosyasini yedekliyordu. HICBIR DEPODA olmayan su
# kalici bilgi TAMAMEN yedeksizdi:
#   * 6 ayri hafiza uzayi (~/.claude/projects/*/memory) — advisor/bot/hasat/
#     jenerator/pazarlama + eski Documents-pruvo. Yalnizca KraL'inki aliniyordu.
#   * her evin .git/hooks'u (guard + pre-push; "commit EDILMEZ" kurali geregi
#     git'te KOPYASI YOK) ve .claude/ kapi betikleri (mimar-icra-kapisi.py ...).
#   * KraL'da raporlar/, .uyelik-kodlar/ (parametrik seri OpenSCAD kaynagi),
#     .marka-kapsama.json, .stl-r2-manifest.json, tedarikci iskonto kurallari.
#   * MaCiT'te 3 izlenmeyen DEVAM-*-MARIN.md, ArTisT'te gorseller/ (reklam
#     kreatifleri), KaaN'da ciktilar/ + kalibrasyon (olculmus STL kuponlari).
#
# ILKE — "GIT'TE VARSA YEDEKLEME": her ev icin `git ls-files` bir kez okunur ve
# IZLENEN dosyalar atlanir (5 evin hepsi uzak depoya ITILMIS: git zaten yedek).
# Boylece 7,7 GB'lik `olcum/` icinden yalniz izlenmeyen betikler alinir, allowlist
# dosya dosya sayilmak zorunda kalmaz ve yeni dosya kendiliginden kapsama girer.
# DEGISTIRILMIS izlenen dosyalar AYRI klasore (KIRLI-IZLENEN) alinir: calisma
# agacindaki o icerik henuz hicbir depoda yoktur.
#
# EVLER KOKE GORECE COZULUR (os.path.dirname(ROOT)), MUTLAK YAZILMAZ: yedekle-test
# kum havuzu sahte bir ROOT kurar; mutlak yol yazsaydik test GERCEK evleri okur,
# gercek veriyi kum havuzuna kopyalar ve dosya-sayisi kontrolleri kirilirdi.
EK_KLASOR = "ek"                     # backup/ek/... — mevcut duzeni BOZMAZ

# Ev -> yedeklenecek YOL LISTESI (dosya ya da dizin; dizin izlenmeyenleri icin gezilir).
# Listede OLMAYAN her izlenmeyen giris "KAPSAM DISI" olarak RAPORLANIR (sessiz dusmez).
EK_EVLER = {
    "pruvo": (
        ".claude/settings.json", ".claude/settings.local.json", ".claude/launch.json",
        ".claude/commands", ".claude/skills", ".claude/R2-JETON-IPTAL-SPEC.md",
        ".codex", "raporlar", "teslimler",
        "tools/URUN-EKLEME-REHBERI.md", "tools/arastirma-sari-fiyat.md",
        "tools/yedek-topolojisi-raporu.md", "taban-fiyatlar.js",
        ".marka-kapsama.json", ".stl-r2-manifest.json", ".stl-eslesmeyen-manifest.json",
        ".uyelik-kodlar", ".uyelik-parametreler.json", ".tedarikci-fiyat",
        ".urunler-duzelt-izin.json", ".diriltme-izin.json", ".urunler-sil-izin.json",
        ".urunler-id-rename-izin.json",
        "urun-kaynaklari.json", "_yayin-icerik-dizinleri.txt",
        "worker-iyzico-webhook/worker.js", "worker-iyzico-webhook/wrangler.toml",
        # Uyelik ureteci degisken adlari eslemi: TICARI VERI (sir degil, kimlik
        # bilgisi degil). Kanonik kopyasi R2 `pruvo-ozel` kovasinda ama Drive'da
        # yoktu -> R2 erisimi kesilirse parametrik onizleme derlemesi yeniden
        # uretilemezdi. Ayni sinif: .uyelik-parametreler.json / .uyelik-kodlar/.
        "onizleme/derleyici/eslem-ozel.json",
    ),
    "pruvo-pazarlama": (".claude", "gorseller"),
    "pruvo-bot": (".claude",),
    # 🔴 hasat/olcum GLOB ILE DARALTILDI: olcudu -> 13.838 izlenmeyen dosya / 6,06 GB.
    # Bunlarin ezici cogunlugu platformlardan INDIRILMIS gorsel/STL (yeniden
    # indirilebilir), kalici bilgi DEGIL. Kalici olan, elle yazilmis olcum/ayiklama
    # betikleri ve tablolar: onlar uzantiyla alinir.
    # 🔴 KOK DEFTERLERI ADSIZ GLOB (7 Agu 2026): burada eskiden 3 kok .md dosyasi
    # TEK TEK adiyla yaziliyordu. Iki olculmus kusur:
    #   (1) GIZLILIK — depo PUBLIC; o adlar 5 ucuncu-taraf pazaryeri etiketi tasiyordu,
    #       yani hangi kanallardan calisildigini yayina veriyordu (ticari bilgi).
    #   (2) DRIFT — elle yazilmis liste bayatliyor: 7 Agu olcumunde 3 adin 1'i evde
    #       ARTIK YOK, buna karsilik ayni bicimde 4 ad kapsam DISINDA duruyordu.
    # Glob ikisini birden kapatir: ad yayina girmez, yeni defter kendiliginden kapsanir.
    "pruvo-hasat": (".claude", "AGENTS.md",
                    "olcum/*.py", "olcum/*.md", "olcum/*.json", "olcum/*.tsv",
                    "kalibrasyon/*.tsv", "kalibrasyon/*.py", "kalibrasyon/*.md",
                    "DEVAM-*.md"),
    "pruvo-jenerator": (".claude", ".codex", "AGENTS.md", "ciktilar", "kalibrasyon",
                        "referans", "dogrulama/hacim.js"),
    "pruvo-advisor": (".claude", "AGENTS.md"),
}

# TURETILMIS/YENIDEN URETILEBILIR — kapsam disi raporunda GURULTU yapmasin diye
# ADIYLA taninir. Bunlar "unutulmus" degil, BILEREK disarida: build.py ciktisi,
# indirilmis onbellek, yerel wrangler durumu, log.
EK_TURETILMIS = {
    ".thing-cache", "urun", "sitemap.xml", "robots.txt", ".nojekyll", "stl",
    ".wrangler", ".urunler-guard.log", ".DS_Store", "node_modules", "scratchpad",
    "dist", "build", ".next", "__pycache__", ".venv",
    # worktrees: git'ten yeniden uretilir, ICINDE tam bir repo kopyasi tasir.
    "worktrees", "scratchpad_out",
    # build.py / sayfalar.py ciktilari (gitignore'lu ama URETILMIS — kaynak degil):
    "ozet.json", "filament-veri.js", "merchant-feed.xml", "index.built.html", "marka",
}
# Kilit/gecici dosyalar (icerigi yok, yedegi anlamsiz).
EK_TURETILMIS_DESEN = ("*.lock", "*.tmp", "*.pyc", "*.log", ".dogrula-kilit",
                       "*.yedek-oncesi", "*.pruvo-yedek-oncesi")

# SIR KOKENI — yedeklenMEYEN kimlik bilgileri icin GERI KAZANIM haritasi.
# 🔴 BURADA DEGER YOKTUR VE ASLA OLMAYACAK: yalniz "nereden yeniden alinir" ve
# "saglanmazsa ne kirilir". Yeni hesapta yedekten donen bir sir DEGIL, kaynagindan
# yeniden uretilen bir sir isteriz — yedege giren sir, yedegi paylasilamaz yapar
# (hedef ORTAK Drive'dir; paylasim bir tiklamadir).
SIR_KOKENI = {
    ".r2-credentials.json": ("Cloudflare paneli > R2 > Manage API Tokens",
                             "gorsel yukleme (r2-upload.py) durur; site gorselleri "
                             "yayinlanamaz"),
    ".thingiverse-token": ("Thingiverse geliştirici uygulama sayfasi",
                           "Thingiverse metadata cekimi durur"),
    ".cults3d-credentials.json": ("Cults3D hesap ayarlari",
                                  "Cults3D kaynak cekimi durur"),
    ".mmf-token": ("MyMiniFactory geliştirici anahtari",
                   "MMF cekimi durur (platform zaten emekli)"),
    ".gemini-key": ("Google AI Studio", "Gemini cagrilari durur (Gemini EMEKLI — "
                    "yeni hesapta yeniden saglanmasi GEREKMEZ)"),
    ".yonet-anahtar": ("shop worker yonetim anahtari — wrangler secret",
                       "shop yonetim ucu kilitlenir"),
    ".onizleme-kapat-anahtar": ("shop worker onizleme anahtari — wrangler secret",
                                "onizleme kapatma ucu calismaz"),
    ".stl-backup-dir": ("otomatik: drive_yolu.py mount'u tarayip kendi yazar",
                        "hicbir sey — betik kendini duzeltir"),
    ".dev.vars": ("wrangler yerel gizli degiskenleri (panelden yeniden girilir)",
                  "shop worker'in yerel gelistirme kosumu calismaz"),
    "secrets.local.txt": ("Cloudflare Workers secret'lari (wrangler secret put)",
                          "Ege (bot) worker'i yerelde kosmaz"),
    # 🔴 ADSIZ KALEM (7 Agu 2026): burada eskiden ucuncu-taraf platformun ADI
    # geciyordu; depo PUBLIC ve o ad hangi kanaldan calisildigini yayina verir.
    # Anahtar HICBIR YERDE gercek dosyayla ESLESTIRILMEZ — SIR_KOKENI'nin tek
    # okuyucusu _geri_kazanim_metni(), yani salt METIN uretimi (yol cozme,
    # os.path.exists ya da uyelik testi YOK). GERI KAZANIM KAYBOLMAZ: dosyanin
    # GERCEK adi ayni raporda, ad deseni ile elenen kalem olarak zaten satirlanir
    # (ek_ev_plani -> haric -> SIR ENVANTERI); bu tablo ona RECETE ekler.
    ".<platform>-session-cookie": (
        "ilgili platforma tarayicidan yeniden giris "
        "(gercek dosya adi bu raporun eleme satirlarinda)",
        "o platformun hasadi durur"),
    "auth.json": ("ChatGPT/Codex girisi (codex login)", "Codex isci cagrilari durur"),
}

GIT_HOOK_KLASOR = "GIT-HOOKS"        # her evin .git/hooks'u (git'te ASLA yok)
KIRLI_KLASOR = "KIRLI-IZLENEN"       # izlenen ama DEGISTIRILMIS dosyalarin kopyasi
MEMORY_EVLER = "memory-evler"        # KraL disindaki hafiza uzaylari
GENEL_AYAR_KLASOR = "claude-genel"   # ~/.claude/settings.json
KAPSAM_DISI_ADI = "KAPSAM-DISI.txt"  # gorulen ama alinmayan girisler (gorunur bosluk)
SIR_ENVANTER_ADI = "SIR-ENVANTERI.txt"  # sirlarin YOLU — DEGERI ASLA YAZILMAZ

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_yolu

BAYRAKLAR = {"--kuru", "--dry-run", "--gerekliyse", "--sirlar", "--sir-temizle",
             "--kuru-prova", "--dogrula", "-h", "--help"}

# Tazelik damgasi — backup/ kokunde. durum.py panosu BU dosyayi okur (tek kaynak).
DAMGA_ADI = ".son-yedek.json"

# ATLAMA KAYDI — AYRI DOSYA, bilerek.
# 🔴 NEDEN AYRI: damgayi yalniz KILIDI TUTAN kosum yazar (yani tek yazici, zaten
# serilestirilmis). Atlayan kosum ise kilidi TUTMUYOR; ayni dosyada oku-degistir-yaz
# yapinca iki surec birbirinin yazimini ezebiliyordu — olculdu: 20 paralel
# `--gerekliyse` ciftinin 2'sinde atlayan kosum, kazananin taze `baslangic`ini eski
# degerle geri yazdi ve pano YANLIS ⚠⚠ verdi. Ayri dosyada her dosyanin TEK yazici
# sinifi olur; yaris yapisal olarak yok olur (kilit + bounded-retry gibi olasilikci
# bir cozume gerek kalmaz). Pano ikisini okuyup birlestirir.
ATLAMA_ADI = ".son-yedek-atlama.json"

# Eszamanlilik kilidi — ANA calisma agacinin kokunde (gitignore'lu).
# NEDEN ROOT: ROOT worktree'den de ANA agaci gosterir (ana_calisma_agaci), yani
# worktree push'u ile main push'u AYNI kilit dosyasinda yarisir. Kilidi worktree'ye
# koysaydik iki farkli worktree'den gelen push'lar birbirini HIC gormezdi.
# NEDEN HEDEFTE (Drive) DEGIL: CloudStorage/FUSE mount'ta flock semantigi garanti
# degil; kilit yerel diskte olmali. Hedef zaten makine basina tek.
KILIT_ADI = ".yedek.lock"
KILIT_UYARI_YASI = 3600.0   # sn. Bundan uzun tutulan kilit "asili surec" suphesi -> gurultu.

# ---- GURULTU (turetilmis; sir DEGIL, sadece yedege deger etmez) --------------
GURULTU_DIZIN = {"__pycache__", ".git", "node_modules", ".venv", ".mypy_cache", ".pytest_cache"}
GURULTU_DOSYA = ("*.pyc", "*.pyo", ".DS_Store")

# ---- SIR NOBETI (skills agacinda kosulsuz) ----------------------------------
# Tam ad kara listesi: repoda bilinen sir dosyalari + CNAME (mimar emri: yedek paketine girmez).
SIR_ADLARI = {
    ".r2-credentials.json", ".thingiverse-token", ".stl-backup-dir",
    ".onizleme-kapat-anahtar", "cname", ".env", ".netrc", ".npmrc", ".pypirc",
    "credentials", "id_rsa", "id_ed25519", "id_ecdsa",
}
# Ad desenleri (kucuk harfe indirgenmis ad uzerinde fnmatch).
SIR_DESENLERI = (
    "*credential*", "*secret*", "*token*", "*passwd*", "*password*", "*apikey*",
    "*api-key*", "*api_key*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "*.keystore", "*.ppk", ".env.*", "*.env", "id_rsa*", "id_ed25519*", "*.asc",
    # 31 Tem — EK KAPSAM ile birlikte: artik skills disindaki agaclar da bu nobetten
    # geciyor (kardes evler, .claude/, .codex/). Oralardaki bilinen sir bicimleri:
    "*.dev.vars", "*cookie*", "secrets.local*", "*auth.json", "*.credentials",
    "*-key", "*_key", "*anahtar",
)
# Icerik imzalari: YUKSEK SINYAL olanlar (yanlis-pozitif ucuz degil ama fail-closed sectik).
# (etiket, regex) -- rapora YALNIZ etiket girer, eslesen metin GIRMEZ.
SIR_IMZALARI = (
    ("ozel anahtar blogu", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS/R2 erisim anahtari", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub jetonu", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("Slack jetonu", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Anthropic API anahtari", re.compile(r"sk-ant-api[0-9]{2}-[A-Za-z0-9_\-]{20,}")),
    ("Google API anahtari", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("Cloudflare global key alani", re.compile(
        r"\"(?:secret_access_key|access_key_id|api_token|apiToken)\"\s*:\s*\"[^\"]{16,}\"")),
)
ICERIK_TARAMA_SINIRI = 2 * 1024 * 1024  # 2 MiB'den buyuk dosyanin yalniz basi taranir


def _gurultu_mu(ad):
    return any(fnmatch.fnmatch(ad, d) for d in GURULTU_DOSYA)


def _icerik_imzasi(yol):
    """Dosya icinde yuksek-sinyal kimlik imzasi varsa ETIKETINI dondurur, yoksa None.
    Okunamayan dosya -> fail-closed: 'okunamadi' etiketi (yedege ALINMAZ).

    🔴 IKI ASAMALI OKUMA (31 Tem): once 8 KiB bakilir; NUL varsa dosya IKILIDIR ve
    GERISI OKUNMAZ. Eskiden 2 MiB'lik tam okuma NUL kontrolunden ONCE yapiliyordu;
    ek kapsamla (yuzlerce JPG/PNG/STL) bu, plan hesabinda yuzlerce MB'lik bosuna
    okuma demekti. Davranis AYNI: ikili dosya zaten None donuyordu."""
    try:
        with open(yol, "rb") as f:
            bas = f.read(8192)
            if b"\0" in bas:
                return None    # ikili dosya: imza taramasi anlamsiz — GERISINI OKUMA
            ham = bas + f.read(max(0, ICERIK_TARAMA_SINIRI - len(bas)))
    except Exception as e:
        return "okunamadi (%s)" % type(e).__name__
    if b"\0" in ham[:8192]:
        return None  # ikili dosya: imza taramasi anlamsiz (gurultu zaten elenmis olur)
    metin = ham.decode("utf-8", "ignore")
    for etiket, kalip in SIR_IMZALARI:
        if kalip.search(metin):
            return etiket
    return None


def sir_sebebi(yol, ad):
    """Dosya sir sayiliyorsa INSANA OKUNUR sebep, degilse None.
    Sebep metni ASLA sirrin kendisini icermez (yalniz kural/imza sinifi)."""
    dusuk = ad.lower()
    if dusuk in SIR_ADLARI:
        return "ad kara listede"
    for desen in SIR_DESENLERI:
        if fnmatch.fnmatch(dusuk, desen):
            return "ad deseni: %s" % desen
    imza = _icerik_imzasi(yol)
    if imza:
        return "icerik imzasi: %s" % imza
    return None


# ================= KOK SIR ELEMESI (8 Agu 2026, OKAN KARARI) =================
# 🔴 KARAR: "Jetonlari yedekten cikar." Sir dosyalari ORTAK Drive yedegine ARTIK
# KOPYALANMAZ; yalniz bu makinede dururlar. Kaybolmalari hicbir seyi kirmaz —
# hepsi kaynagindan YENIDEN URETILEBILIR (recete: SIR_KOKENI tablosu).
# ONCEKI HAL (olculdu): `--sirlar` bayragi REPO_SIR'i yedek KOKUNE kopyaliyordu ve
# `--sir-temizle` o kokteki kopyalara HIC ULASMIYORDU (yalniz skills_yaz'a geciyordu)
# -> "temizleme araci var" beyani bu kalemler icin GERCEK DEGILDI.
#
# 🔴 KUME ELLE YAZILMAZ: eleme KANONIK kumeden TURER (REPO_SIR + SIR_ADLARI).
# Ucuncu bir elle liste acmak bu depoda OLCULMUS bir sinifitir ([[envanter-drift-parti-basina]],
# [[tekil-yama-sinifi-kapatmaz]]): elle liste parti basina bayatlar ve yarin kanonik
# kumeye eklenen ad ELENMEDEN yedege sizar. Buraya bir ad eklemek isteyen REPO_SIR
# ya da SIR_ADLARI'na ekler; eleme, silme ve envanter UCU DE ayni anda ogrenir.

def kok_sir_kumesi():
    """Yedek/repo KOKUNDE sir sayilan ADLAR — KANONIK kumelerin birlesimi (TEK tanim).
    Kucuk harfe indirgenmis frozenset doner (dosya sistemi buyuk/kucuk harf ayirmayabilir)."""
    return frozenset(a.lower() for a in tuple(REPO_SIR) + tuple(SIR_ADLARI))


def kok_sir_adi_mi(ad):
    """Ad kanonik sir kumesinde mi? (ad karsilastirmasi — dosya ACILMAZ)"""
    return ad.lower() in kok_sir_kumesi()


def kok_sir_sebebi(yol, ad):
    """Kokteki bir kalem sir mi? -> INSANA OKUNUR sebep ya da None (TEK tanim).

    Ad kanonik kumedeyse dosyaya HIC BAKILMAZ (sancakli liste yeter); aksi halde
    sir_sebebi'nin tam nobetine (ad deseni + ICERIK imzasi) duser. Sebep metni
    ASLA sirrin kendisini tasimaz."""
    if kok_sir_adi_mi(ad):
        return "kanonik sir kumesi (REPO_SIR + SIR_ADLARI)"
    return sir_sebebi(yol, ad)


def repo_kok_ayrimi():
    """Repo kokundeki yedek adaylarinin SIR ELEMESI. Doner: (dahil, elenen).

    dahil  : [ad]            -> yedege GIRER
    elenen : [(ad, sebep)]   -> yedege GIRMEZ; ADIYLA basilir (ad sir degil, ICERIK sir).

    Aday kume = REPO_BEKLENEN + REPO_SIR (yani `--sirlar`in eskiden actigi kume de
    ADAYDIR — ama elemeden GECEMEZ). Boylece "sessiz atlama" yok: her elenen kalem
    sayilir ve adiyla raporlanir.

    🔴 ELEME AD EKSENLIDIR, ICERIK TARAMASI DEGIL: REPO_BEKLENEN dosyalari (AGENTS.md,
    DEVAM.md ...) yanlis-pozitif bir icerik imzasi yuzunden SESSIZCE yedek disi
    kalmasin diye burada icerik nobeti KOSMAZ — o sinif 30 Tem'de bir kez yasandi
    (CLAUDE.md symlink'i) ve repo_eksikleri() ancak VARLIGI olcer, elenmeyi olcmez."""
    dahil, elenen = [], []
    for ad in tuple(REPO_BEKLENEN) + tuple(REPO_SIR):
        p = os.path.join(ROOT, ad)
        if not os.path.exists(p) or os.path.islink(p):
            continue
        if kok_sir_adi_mi(ad):
            elenen.append((ad, "kanonik sir kumesi (REPO_SIR + SIR_ADLARI)"))
        else:
            dahil.append(ad)
    return dahil, elenen


def skills_plani(kok=None):
    """~/.claude/skills agacini tarar.

    Doner: (dahil, haric, gurultu)
      dahil   : [koke gorece yol]           -> yedege GIRER
      haric   : [(gorece yol, sebep)]       -> SIR nobeti eledi
      gurultu : [gorece yol | "<dizin>/ (dizin budandi)"]  -> turetilmis, alinmaz

    F4 DUZELTMESI (26 Tem): budanan dizinler (__pycache__ ...) RAPORLANIR. Eskiden
    os.walk budamasi sessizce yutuyordu -> kuru kosum "[skills-gurultu] 0" diyordu
    ama agacta 2 .pyc vardi (15 dosya -> 13+0+0 raporlaniyordu). "Elenen her sey
    raporlanir" iddiasi tutmuyordu. Dizin ADIYLA raporlanir, ICI GEZILMEZ: .git /
    node_modules gibi devasa dizinlerde sayim icin yuruyus yapmak pahaliya patlar.
    """
    kok = SKILLS if kok is None else kok
    dahil, haric, gurultu = [], [], []
    if not os.path.isdir(kok):
        return dahil, haric, gurultu
    for dizin, altlar, dosyalar in os.walk(kok):
        for budanan in sorted(a for a in altlar if a in GURULTU_DIZIN):
            gurultu.append(os.path.relpath(os.path.join(dizin, budanan), kok)
                           + "/ (dizin budandi)")
        altlar[:] = sorted(a for a in altlar if a not in GURULTU_DIZIN)
        for ad in sorted(dosyalar):
            tam = os.path.join(dizin, ad)
            gor = os.path.relpath(tam, kok)
            if os.path.islink(tam):
                # symlink hedefi agac disina cikabilir (sir sizma yolu) -> alinmaz.
                haric.append((gor, "symlink (hedefi agac disina cikabilir)"))
                continue
            if _gurultu_mu(ad):
                gurultu.append(gor)
                continue
            sebep = sir_sebebi(tam, ad)
            if sebep:
                haric.append((gor, sebep))
                continue
            dahil.append(gor)
    return sorted(dahil), sorted(haric), sorted(gurultu)


def skills_yaz(kok, hedef, dahil, haric, sir_temizle=False):
    """Plani hedefe yazar (idempotent: ayni dosya uzerine yazilir, mukerrer yigilmaz).

    Doner: (yazilan_sayisi, bayat_sir_yollari)
    bayat_sir: ELENMIS bir dosyanin hedefte duran ESKI kopyasi (filtresiz surumden kalma).
    """
    yazilan = 0
    for gor in dahil:
        kaynak = os.path.join(kok, gor)
        varis = os.path.join(hedef, gor)
        os.makedirs(os.path.dirname(varis), exist_ok=True)
        if _drive_kopyala_karantinali(kaynak, varis):
            yazilan += 1
    bayat = []
    for gor, _sebep in haric:
        varis = os.path.join(hedef, gor)
        if os.path.exists(varis):
            bayat.append(varis)
            if sir_temizle:
                os.remove(varis)
    return yazilan, bayat


def yedek_kok_sir_plani(backup, adlar=None):
    """Yedek KOKUNDE duran sir kopyalarini BULUR (hicbir sey silmez/acmaz).

    Doner: [(ad, hedef_yol, yerel_yol, yerel_tamam, engel)]
      yerel_tamam : yereldeki ASIL var VE okunabilir mi (fail-closed on kosul)
      engel       : yerel_tamam False ise SEBEP metni, degilse ""

    `adlar` verilirse YALNIZ o adlara bakilir (tekil, elle onaylanmis kaldirma icin);
    varsayilan KANONIK KUMENIN TAMAMIDIR. Kisitlama kalici bir kural DEGILDIR.

    🔴 DOSYA ICERIGI ACILMAZ: varlik/okunabilirlik os.stat + os.access ile olculur."""
    kume = kok_sir_kumesi() if adlar is None else frozenset(a.lower() for a in adlar)
    try:
        girisler = sorted(os.listdir(backup))
    except OSError:
        return []
    cikti = []
    for giris in girisler:
        if giris.lower() not in kume:
            continue
        hedef = os.path.join(backup, giris)
        if not os.path.isfile(hedef):
            continue                     # dizin/link: bu kapinin konusu degil
        yerel = os.path.join(ROOT, giris)
        if not os.path.isfile(yerel):
            cikti.append((giris, hedef, yerel, False,
                          "yereldeki ASIL YOK (silinirse tek kopya gider)"))
        elif not os.access(yerel, os.R_OK):
            cikti.append((giris, hedef, yerel, False, "yereldeki asil OKUNAMIYOR"))
        else:
            cikti.append((giris, hedef, yerel, True, ""))
    return cikti


def yedek_kok_sir_temizle(backup, kuru_prova=False, adlar=None):
    """Yedek KOKUNDEKI sir kopyalarini KALDIRIR — FAIL-CLOSED.

    Doner: (islenen[(ad, yol)], atlanan[(ad, sebep)], bulunan_sayisi)
      islenen : fail-closed on kosulu GECEN kalemler — `kuru_prova=False` ise SILINDI,
                `kuru_prova=True` ise SILINECEKTI (dosyaya DOKUNULMADI).

    🔴 TEK KOD YOLU, BILEREK: prova ile gercek silme AYNI listeyi ayni suzgecten
    uretir. Ayri bir "prova hesaplayicisi" yazsaydik ikiz tanim olurdu ve bu depoda
    olculmus bicimde ayrisirdi ([[ikiz-tanim-sessiz-ayrisma]]) — prova "silinecek"
    dedigi halde gercek kosum baskasini silerdi.

    🔴 ONARILAN KUSUR (8 Agu 2026): `--sir-temizle` bayragi YALNIZ skills_yaz()'a
    geciyordu; yedek KOKUNDEKI sirlara ULASAN HICBIR KOD YOLU YOKTU. Yani arac
    "temizler" diyordu ama o kalemler icin bu GERCEK DEGILDI.

    🔴 FAIL-CLOSED ON KOSUL: bir kalem ancak yereldeki ASLI VAR ve OKUNABILIR ise
    silinir. Dogrulanamayan kalem SILINMEZ, KIRMIZI raporlanir — yanlis silme
    KALICI kayiptir, birakilan kopya ise bir sonraki kosumda yine gorunur.
    `kuru_prova=True` hicbir sey silmez, yalniz ne silinecegini dondurur."""
    islenen, atlanan = [], []
    plan = yedek_kok_sir_plani(backup, adlar=adlar)
    for ad, hedef, yerel, tamam, engel in plan:
        if not tamam:
            atlanan.append((ad, engel + "  [yerel: %s]" % yerel))
            continue
        if kuru_prova:
            islenen.append((ad, hedef))     # DOSYAYA DOKUNULMAZ — yalniz beyan
            continue
        try:
            os.remove(hedef)
            islenen.append((ad, hedef))
        except OSError as e:
            atlanan.append((ad, "silinemedi: %s" % type(e).__name__))
    return islenen, atlanan, len(plan)


def yedek_kok_sir_raporu(backup, sir_temizle, kuru_prova=False, adlar=None):
    """Kok sir temizligini KOSAR ve GURULTULU raporlar. Doner: sayilar dict'i.

    `sir_temizle` False ise (bayraksiz normal kosum) HICBIR SEY SILINMEZ ama bulunan
    kalemler UYARIYLA listelenir: yedekten veri silmek DAIMA elle onaylanir.
    Hesap TEK YOLDAN gecer — prova ile gercek silme ayni suzgeci kullanir."""
    prova = kuru_prova or not sir_temizle
    islenen, atlanan, bulunan = yedek_kok_sir_temizle(backup, kuru_prova=prova,
                                                      adlar=adlar)
    print("  KOK SIR TARAMASI: %d kalem yedek KOKUNDE (kanonik kume: %d ad) — %s"
          % (bulunan, len(kok_sir_kumesi()),
             "KURU PROVA (hicbir sey silinmedi)" if prova else "TEMIZLIK KOSTU"))
    for ad, yol in islenen:
        print("    %s %s   (%s)"
              % ("KURU PROVA — SILINECEK:" if prova else "SIR KOPYASI SILINDI:", ad, yol))
    for ad, sebep in atlanan:
        print("    🔴 SILINMEDI (fail-closed): %s   -> %s" % (ad, sebep))
    if prova and not kuru_prova and islenen:
        print("      (silmek icin: python3 tools/yedekle.py --sir-temizle)")
    return {"kok_sir_bulunan": bulunan,
            "kok_sir_silinen": 0 if prova else len(islenen),
            "kok_sir_atlanan": len(atlanan)}


def _agac_izinli_mi(ad, izinli):
    """Bir dosya agacin ACIK ALLOWLIST'inde mi? (TEK tanim, fail-closed)

    Uzantisiz dosya (".gh-token" / ".ci-token" gibi gizli dosyalar dahil) splitext
    ile "" uzanti verir -> listede olmadigi icin ELENIR. Bu, kural konusunun ta
    kendisidir: jeton dosyalari klasik olarak uzantisizdir ve tam da bu yolla
    disarida kalirlar — ADLARINI onceden bilmemize GEREK KALMADAN."""
    return os.path.splitext(ad)[1].lower() in izinli


def agac_plani(agac):
    """AGAC_KAPSAMI'ndaki BIR agaci tarar (skills_plani ile AYNI sekil).

    `agac` = (etiket, kok, hedef_klasor, izinli_uzantilar)
    Doner: (dahil, haric, gurultu)
      dahil   : [koke gorece yol]        -> yedege GIRER
      haric   : [(gorece yol, sebep)]    -> yedege GIRMEZ, SEBEBIYLE sayilir
      gurultu : [gorece yol | "<dizin>/ (dizin budandi)"]

    IKI KATMAN, IKI AYRI SORU — SIRA ONEMLI ve BILEREK BOYLE:
      1. SIR NOBETI (sir_sebebi): ad kara-listesi + ad deseni + ICERIK imzasi.
      2. ACIK ALLOWLIST (_agac_izinli_mi): uzanti izinli mi?
    Sir nobeti ONCE kosar ki ELEME SEBEBI ayirt edici olsun: allowlist onde olsaydi
    jeton-adli bir dosya "allowlist disi" diye elenir, sir katmani HIC ATESLEMEZ ve
    "sir nobeti bunu yakaliyor" iddiasi BEYAN EDILMIS SURVIVOR olurdu (katmanlarin
    VEYA'si yesil yanar, katmanin kendisi olculmemis kalir). Simdi her katman TEK
    BASINA kirmiziya cevrilebiliyor: izinli uzantili ama jeton-adli/imzali dosyayi
    YALNIZ katman 1, zararsiz adli ama izinsiz uzantili dosyayi YALNIZ katman 2 eler.

    🔴 KATMAN 1 ONDE OLDUGU ICIN LOG'LARIN ICERIGI DE TARANIR: `cron` agacindaki
    `.log` dosyalari zaten allowlist disidir, ama sir nobeti onlardan ONCE kosar ->
    icinde jeton yankisi olan bir log "icerik imzasi" sebebiyle elenir. Yani
    "log'u kapsama almiyoruz" karari, "log'un icine bakmiyoruz" demek DEGILDIR.

    🔴 SEBEP METNI ASLA SIRRIN KENDISINI TASIMAZ (sir_sebebi sozlesmesi): yalniz
    kural adi ya da imza SINIFI. Dosyanin ICERIGI okunmaz/yazilmaz/basilmaz."""
    _etiket, kok, _hedef, izinli = agac
    dahil, haric, gurultu = [], [], []
    if not os.path.isdir(kok):
        return dahil, haric, gurultu
    for dizin, altlar, dosyalar in os.walk(kok):
        for budanan in sorted(a for a in altlar if a in GURULTU_DIZIN):
            gurultu.append(os.path.relpath(os.path.join(dizin, budanan), kok)
                           + "/ (dizin budandi)")
        altlar[:] = sorted(a for a in altlar if a not in GURULTU_DIZIN)
        for ad in sorted(dosyalar):
            tam = os.path.join(dizin, ad)
            gor = os.path.relpath(tam, kok)
            if os.path.islink(tam):
                haric.append((gor, "symlink (hedefi agac disina cikabilir)"))
                continue
            if _gurultu_mu(ad):
                gurultu.append(gor)
                continue
            sebep = sir_sebebi(tam, ad)                 # KATMAN 1 — sir nobeti
            if sebep:
                haric.append((gor, sebep))
                continue
            if not _agac_izinli_mi(ad, izinli):         # KATMAN 2 — acik allowlist
                haric.append((gor, "allowlist disi: uzanti %r izinli degil (izinli: %s)"
                                   % (os.path.splitext(ad)[1].lower(),
                                      ", ".join(izinli))))
                continue
            dahil.append(gor)
    return sorted(dahil), sorted(haric), sorted(gurultu)


def agac_yaz(kok, hedef, dahil, etiket=""):
    """Bir agacin izinli dosyalarini hedefe yazar. Doner: (hedefte_olan, yeni).

    `hedefte_olan` = kopyalama BASARIYLA tamamlanan dosya sayisi (plan uzunlugu ile
    esit olmali; kopyalanamayan dosya SAYILMAZ -> sayac gercegi soyler, iddiayi degil).
    Idempotent kopya kullanilir: bu betik HER push'ta kosuyor."""
    olan = yeni = 0
    for gor in dahil:
        try:
            if _kopyala_gerekliyse(os.path.join(kok, gor), os.path.join(hedef, gor)):
                yeni += 1
            olan += 1
        except (OSError, shutil.Error) as e:
            print("  ⚠️ %s: kopyalanamadi %s (%s)" % (etiket.upper(), gor, type(e).__name__))
    return olan, yeni


def _agac_dosyalari(kok):
    """Kuru kosum listelemesi icin: kokun altindaki tum dosyalar (gorece, sirali)."""
    cikti = []
    if not os.path.isdir(kok):
        return cikti
    for dizin, _altlar, dosyalar in os.walk(kok):
        for ad in dosyalar:
            cikti.append(os.path.relpath(os.path.join(dizin, ad), kok))
    return sorted(cikti)


def _repo_dosyalari(sirlar=False):
    """Repo kokunden yedeklenecek dosya adlari — SIR ELEMESINDEN GECMIS liste.

    🔴 `sirlar` EMEKLI (8 Agu 2026, Okan karari): eskiden True olunca REPO_SIR'i
    kopya planina EKLIYORDU. Artik KAPSAMI DEGISTIRMEZ — sir dosyalari hicbir
    bayrakla yedege girmez (bkz. repo_kok_ayrimi). Parametre CAGRI UYUMU icin
    duruyor (durum.py iki adayli imza olcumu, yedekle-test cagrilari)."""
    _ = sirlar
    return repo_kok_ayrimi()[0]


def repo_eksikleri():
    """BEKLENEN ama repo kokunde OLMAYAN (ya da SYMLINK'e donmus) dosyalar.
    Bos degilse yedek KISMIDIR. (Sir listesi burada sayilmaz: onlar zaten kosullu.)

    🔴 SYMLINK NEDEN 'EKSIK' SAYILIR (30 Tem, olculdu): _repo_dosyalari() symlink'leri
    ELER. Eskiden repo_eksikleri() os.path.exists() ile bakiyordu ve exists() symlink'i
    IZLER -> beklenen bir ad symlink'e dondugu anda dosya "var" gorunuyor ama yedege
    GIRMIYORDU. Tam olarak bu oldu: CLAUDE.md AGENTS.md'ye symlink yapilinca ajan
    baglam dosyasi sessizce yedek disi kaldi (damga "tam": true demeye devam etti).
    Artik ayni durum GURULTULU: eksik listesine girer, damga tam=False olur."""
    eksik = []
    for a in REPO_BEKLENEN:
        p = os.path.join(ROOT, a)
        if not os.path.exists(p) or os.path.islink(p):
            eksik.append(a)
    return eksik


# ===================== EK KAPSAM: plan / kopyalama / dogrulama ===============

def ev_yollari():
    """Bilinen 5+1 evin TAM yolu — ROOT'un KARDESI olarak cozulur, mutlak YAZILMAZ.
    Doner: [(ev_adi, tam_yol)] yalniz DIZIN OLARAK VAR OLANLAR.
    Kum havuzunda (sahte ROOT) hicbiri bulunmaz -> ek kapsam kendini kapatir."""
    taban = os.path.dirname(ROOT)
    cikti = []
    for ad in sorted(EK_EVLER):
        yol = ROOT if os.path.basename(ROOT) == ad else os.path.join(taban, ad)
        if os.path.isdir(os.path.join(yol, ".git")) or os.path.isfile(os.path.join(yol, ".git")):
            cikti.append((ad, yol))
    return cikti


def ek_etkin_mi():
    """Ek kapsam bu ortamda anlamli mi? (en az bir bilinen ev var mi)
    GORUNUR karar: kapaliysa main() bunu BASAR, sessizce dusmez."""
    return bool(ev_yollari())


def _git_izlenenler(ev):
    """Evin git'te IZLENEN dosyalari (gorece yol kumesi). Git yoksa bos kume."""
    try:
        p = subprocess.run(["git", "-C", ev, "ls-files", "-z"],
                           capture_output=True, text=True)
    except OSError:
        return set()
    if p.returncode != 0:
        return set()
    return set(x for x in p.stdout.split("\0") if x)


def _git_kirliler(ev):
    """Izlenen ama DEGISTIRILMIS/EKLENMIS dosyalar (gorece yol listesi).
    Bu icerik henuz hicbir depoda YOK -> ayri klasore yedeklenir."""
    try:
        p = subprocess.run(["git", "-C", ev, "status", "--porcelain", "-uno", "-z"],
                           capture_output=True, text=True)
    except OSError:
        return []
    if p.returncode != 0:
        return []
    cikti = []
    for kayit in p.stdout.split("\0"):
        if len(kayit) > 3 and kayit[2] == " ":
            yol = kayit[3:]
            if os.path.isfile(os.path.join(ev, yol)):
                cikti.append(yol)
    return sorted(cikti)


def _turetilmis_mi(ad):
    if ad in EK_TURETILMIS:
        return True
    return any(fnmatch.fnmatch(ad, d) for d in EK_TURETILMIS_DESEN)


def _kok_desen_tutuyor(ad, desenler):
    """Kok seviyesi glob eslesmesi — TEK TANIM.

    🔴 NEDEN AYRI FONKSIYON: ayni hukum ek_ev_plani icinde IKI yerde gerekiyor —
    (a) dosyayi kapsama ALIRKEN, (b) KAPSAM-DISI kesfinde ayni dosyayi TEKRAR
    raporlamamak icin. Iki yerde ayri ayri yazilsaydi ikiz tanim sessizce
    ayrisirdi: biri genisleyip digeri genislemeyince ayni dosya hem yedege girer
    hem "alinmadi" diye raporlanir, ya da tam tersi sessiz bosluk kalirdi."""
    return any(fnmatch.fnmatch(ad, d) for d in desenler)


def _kanca_kapsamda_mi(ad):
    """`.git/hooks` altindaki bir dosya yedek KAPSAMINDA mi? (TEK tanim)

    🔴 NEDEN AYRI FONKSIYON (31 Tem, CI'da KIRMIZI yakalandi): git HER klonda
    `.git/hooks` icine 14 adet `*.sample` sablonu yazar. Bunlar git'in kendi
    varsayilanidir, KALICI BILGI DEGILDIR ve kopya plani (ek_ev_plani) onlari
    ATLAR. Ama kaynak_imzasi() ayni elemeyi YAPMIYORDU -> iki tanim ayristi ve
    imza, yedege HIC girmeyen dosyalari sayar oldu. Sonucu SESSIZ-YESIL bir
    fail-open'dir: taze checkout / bos HOME'da (yedeklenecek gercek kaynak SIFIR)
    olcum None yerine {"adet": 14, ...} donuyordu -> pano "olculemedi" demek
    yerine UYDURMA bir imza uzerinden karsilastirma yapiyordu. Kapi bunu
    "K5: kaynak yoksa olcum None doner (uydurma imza YOK)" ile yakaladi.
    31 TEM (fail-open onarimi): ayrisma artik YAPISAL olarak imkansiz — imza da
    dogrulama da kopya da yedek_plani() uzerinden bu SUZGECTEN GECMIS listeyi
    kullanir; bu fonksiyonun tek cagirani ek_ev_plani'dir."""
    return not ad.endswith(".sample")


def ek_ev_plani(ev, izlenenler=None):
    """Bir evin EK yedek plani.

    Doner: (dahil, haric, kapsam_disi)
      dahil       : [(gorece kaynak yolu, gorece hedef yolu)]
      haric       : [(gorece yol, sebep)]   -> SIR nobeti eledi (yedege GIRMEZ)
      kapsam_disi : [gorece giris]          -> gorulen ama allowlist'te olmayan

    KURAL: git'te IZLENEN dosya ALINMAZ (uzak depoda zaten var). Izlenen ama
    KIRLI olan dosya KIRLI-IZLENEN/ altina alinir (calisma agacindaki o icerik
    hicbir depoda yok). .git/hooks HER ZAMAN alinir (git'e giremez)."""
    izlenenler = _git_izlenenler(ev) if izlenenler is None else izlenenler
    ad = os.path.basename(ev)
    izin = EK_EVLER.get(ad, ())
    dahil, haric, kapsam_disi = [], [], []

    def _dosya_ekle(gor, hedef_gor):
        tam = os.path.join(ev, gor)
        if os.path.islink(tam):
            haric.append((gor, "symlink (hedefi agac disina cikabilir)"))
            return
        sebep = sir_sebebi(tam, os.path.basename(gor))
        if sebep:
            haric.append((gor, sebep))
            return
        dahil.append((gor, hedef_gor))

    def _dizin_gez(taban, desenler=None):
        """taban altindaki IZLENMEYEN dosyalar; `desenler` varsa gorece yola fnmatch
        (HERHANGI biri tutuyorsa alinir).

        🔴 DESEN LISTESI, TEK DESEN DEGIL (31 Tem): ayni tabana bakan butun glob
        girisleri cagiran tarafta BIRLESTIRILIP tek yuruyuse verilir. Eskiden her
        desen icin AYRI os.walk kosuyordu; hasat/olcum agacinda 22.173 giris var ve
        4 desen (*.py/*.md/*.json/*.tsv) o agaci 4 KEZ geziyordu. Kume AYNI (birlesim),
        maliyet dusuk: bu fonksiyon artik `--gerekliyse` yolunda (imza) da kosuyor."""
        for dizin, altlar, dosyalar in os.walk(taban):
            altlar[:] = sorted(a for a in altlar
                               if a not in GURULTU_DIZIN and not _turetilmis_mi(a))
            for dosya in sorted(dosyalar):
                gor = os.path.relpath(os.path.join(dizin, dosya), ev)
                if gor in izlenenler or _turetilmis_mi(dosya) or _gurultu_mu(dosya):
                    continue
                if desenler and not any(fnmatch.fnmatch(gor, d) for d in desenler):
                    continue
                _dosya_ekle(gor, gor)

    glob_gruplari = []        # [(taban, [desen, ...])] — ilk gorulme sirasi korunur
    kok_desenleri = []        # "/" TASIMAYAN glob'lar: yalniz evin KOKUNDE eslesir
    for giris in izin:
        # GLOB DESTEGI: "olcum/*.py" gibi girisler agir dizinleri UZANTIYLA daraltir.
        # Olculdu: hasat/olcum'da 13.838 izlenmeyen dosya / 6,06 GB var ve neredeyse
        # tamami YENIDEN INDIRILEBILIR gorsel; kalici olan yalniz elle yazilmis betikler.
        if "*" in giris or "?" in giris:
            # 🔴 KOK SEVIYESI GLOB AYRI COZULUR (7 Agu 2026): "AD-*.md" gibi, icinde
            # "/" OLMAYAN desen tek tek yazilmis KOK dosyalarinin yerini tutar ve
            # os.walk ile cozulMEZ. Iki olculmus sebep:
            #   (1) MALIYET/KAPSAM: asagidaki taban cozumu "/" yoksa evin KOKUNE duser;
            #       hasat kokunde 22.173 giris (6,06 GB) var ve bu fonksiyon
            #       `--gerekliyse` imza yolunda da kosuyor -> her nabizda tum agac
            #       (olcum/ dahil, hem de IKINCI kez) gezilirdi.
            #   (2) DOGRULUK: fnmatch "/" karakterini AYIRAC SAYMAZ; "AD-*.md" deseni
            #       "AD-birdizin/derin/x.md" gibi ALT AGAC dosyalarini da yutardi —
            #       yerini aldigi kok adlarindan DAHA GENIS bir kume.
            # listdir cozumu kapsami elle yazilmis kok adlariyla AYNI sinifta tutar.
            if "/" not in giris:
                kok_desenleri.append(giris)
                continue
            onek = giris.split("*")[0].split("?")[0].rstrip("/")
            taban = os.path.join(ev, os.path.dirname(onek) if "/" in onek else onek)
            if not os.path.isdir(taban):
                taban = os.path.join(ev, os.path.dirname(giris))
            if os.path.isdir(taban):
                for _t, _d in glob_gruplari:
                    if _t == taban:
                        _d.append(giris)
                        break
                else:
                    glob_gruplari.append((taban, [giris]))
            continue
        tam = os.path.join(ev, giris)
        if os.path.isfile(tam):
            if giris in izlenenler:
                continue                       # git'te var -> yedege gerek yok
            _dosya_ekle(giris, giris)
        elif os.path.isdir(tam):
            _dizin_gez(tam)

    for taban, desenler in glob_gruplari:      # agir agac BIR KEZ gezilir
        _dizin_gez(taban, desenler=desenler)

    # KOK SEVIYESI GLOB'LAR — yalniz `ev` kokundeki DOSYALAR (alt agaca INMEZ).
    # Suzgecler tek tek yazilmis kok girisiyle AYNI: izlenen atlanir (git zaten yedek),
    # turetilmis/gurultu elenir, symlink ve sir _dosya_ekle icinde `haric`e duser.
    if kok_desenleri:
        try:
            kok_girisleri = sorted(os.listdir(ev))
        except OSError:
            kok_girisleri = []
        for giris in kok_girisleri:
            if not _kok_desen_tutuyor(giris, kok_desenleri):
                continue
            if giris in izlenenler or _turetilmis_mi(giris) or _gurultu_mu(giris):
                continue
            if not os.path.isfile(os.path.join(ev, giris)):
                continue                       # dizin/soket: kok glob'u dosya alir
            _dosya_ekle(giris, giris)

    # .git/hooks — "hook'lar commit EDILMEZ" kurali geregi git'te KOPYASI YOK.
    kancalar = os.path.join(ev, ".git", "hooks")
    if os.path.isdir(kancalar):
        for dosya in sorted(os.listdir(kancalar)):
            if not _kanca_kapsamda_mi(dosya):      # git'in kendi sablonlari
                continue
            tam = os.path.join(kancalar, dosya)
            if not os.path.isfile(tam) or os.path.islink(tam):
                continue
            sebep = sir_sebebi(tam, dosya)
            if sebep:
                haric.append((".git/hooks/" + dosya, sebep))
                continue
            dahil.append((os.path.join(".git", "hooks", dosya),
                          os.path.join(GIT_HOOK_KLASOR, dosya)))

    # KIRLI izlenen dosyalar — calisma agacindaki icerik henuz depoda yok.
    for gor in _git_kirliler(ev):
        tam = os.path.join(ev, gor)
        if os.path.islink(tam):
            continue
        sebep = sir_sebebi(tam, os.path.basename(gor))
        if sebep:
            haric.append((gor + " (kirli)", sebep))
            continue
        dahil.append((gor, os.path.join(KIRLI_KLASOR, gor)))

    # KAPSAM DISI KESFI — kok seviyesindeki izlenmeyen girisler allowlist'te mi?
    # Amac: yeni bir kalici bilgi turu ortaya cikinca SESSIZ kalmasin. Bu yuzden
    # gurultuyu (uretilmis sayfa, bos dizin, bilinen sir) ELEYIP kalanini basiyoruz;
    # gurultulu liste okunmaz, okunmayan liste bosluk gizler.
    izin_kok = set(g.split("/")[0] for g in izin)
    try:
        girisler = sorted(os.listdir(ev))
    except OSError:
        girisler = []
    for giris in girisler:
        if giris in izin_kok or giris == ".git" or _turetilmis_mi(giris):
            continue
        # KOK GLOB'unun ALDIGI DOSYA zaten karara baglandi (dahil ya da sir-disi
        # `haric`); burada tekrar raporlanirsa envanter/rapor MUKERRER satir alir.
        # DIZIN eslesirse BILEREK dusmez: kok glob'u dizin gezmez, gorunur bosluk kalir.
        if (kok_desenleri and _kok_desen_tutuyor(giris, kok_desenleri)
                and os.path.isfile(os.path.join(ev, giris))):
            continue
        if giris in izlenenler or any(x.startswith(giris + "/") for x in izlenenler):
            continue                            # git'te var -> bosluk DEGIL
        # 🔴 8 Agu 2026: REPO_SIR ARTIK "ana yedek zaten aliyor" DEGIL (sir yazma yolu
        # KAPANDI). Bu yuzden buradan DUSMEZ: alttaki kok sir nobetine iner ve
        # SIR ENVANTERINE adiyla girer. Yoksa kalem sessizce hicbir listede gorunmezdi
        # ve "yedekte de yok, envanterde de yok" = olculmemis bosluk olurdu.
        if ev == ROOT and giris in REPO_BEKLENEN:
            continue                            # ana yedek zaten aliyor
        tam = os.path.join(ev, giris)
        if os.path.islink(tam):
            continue                            # symlink: hedefi zaten ayrica degerlendirilir
        # BILINEN SIR: bosluk degil, ENVANTER kalemi (deger ASLA kopyalanmaz/yazilmaz).
        sebep = kok_sir_sebebi(tam, giris) if os.path.isfile(tam) else None
        if sebep:
            haric.append((giris, sebep))
            continue
        if os.path.isdir(tam):
            try:
                icerik = os.listdir(tam)
            except OSError:
                icerik = []
            if not icerik:
                continue                        # bos dizin: yedeklenecek bilgi yok
            # build.py ciktisi: SEO acilis sayfasi dizini (yalniz index.html).
            if set(icerik) <= {"index.html", ".DS_Store"}:
                continue
        kapsam_disi.append(giris)
    return dahil, sorted(haric), kapsam_disi


def ek_memory_kokleri():
    """KraL disindaki hafiza uzaylari: [(namespace, memory yolu)].
    MEMORY (KraL) haric tutulur — o zaten backup/memory'ye aliniyor."""
    projeler = os.path.dirname(os.path.dirname(MEMORY))   # ~/.claude/projects
    cikti = []
    if not os.path.isdir(projeler):
        return cikti
    for ad in sorted(os.listdir(projeler)):
        yol = os.path.join(projeler, ad, "memory")
        if os.path.isdir(yol) and os.path.abspath(yol) != os.path.abspath(MEMORY):
            cikti.append((ad, yol))
    return cikti


def _genel_ayar_yolu():
    """~/.claude/settings.json — makine geneli izin/hook ayari (TEK tanim)."""
    return os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(MEMORY)),
                                        "..", "settings.json"))


def _ek_ev_hedefi(ev_adi, hedef_gor):
    """Bir kardes ev dosyasinin backup/ kokune gorece HEDEFI (TEK tanim)."""
    return os.path.join(EK_KLASOR, "evler", ev_adi, hedef_gor)


def _ek_memory_girdileri():
    """KraL disindaki hafiza uzaylarinin dosyalari (TEK tanim).
    Doner: [(kaynak_tam_yol, backup/ kokune gorece hedef)]."""
    cikti = []
    for ns, yol in ek_memory_kokleri():
        for dizin, altlar, dosyalar in os.walk(yol):
            altlar[:] = [a for a in altlar if a not in GURULTU_DIZIN]
            for dosya in sorted(dosyalar):
                if _gurultu_mu(dosya):
                    continue
                kaynak = os.path.join(dizin, dosya)
                cikti.append((kaynak, os.path.join(EK_KLASOR, MEMORY_EVLER, ns,
                                                   os.path.relpath(kaynak, yol))))
    return cikti


def _genel_ayar_girdisi():
    """~/.claude/settings.json girdisi (TEK tanim).
    Doner: (kaynak, backup/'a gorece hedef, sir_sebebi) ya da dosya yoksa None.
    `sir_sebebi` doluysa dosya KOPYALANMAZ, envantere girer (ek_yaz) ve plana GIRMEZ."""
    genel = _genel_ayar_yolu()
    if not os.path.isfile(genel):
        return None
    return (genel, os.path.join(EK_KLASOR, GENEL_AYAR_KLASOR, "settings.json"),
            sir_sebebi(genel, os.path.basename(genel)))


def yedek_plani(sirlar=False):
    """🔴 YEDEGE GERCEKTEN GIREN DOSYALARIN TEK TANIMI — imza/dogrulama/kopya buradan turer.
    Doner: [(kaynak_tam_yol, backup/ kokune gorece hedef yol)].

    NEDEN TEK TANIM (31 Tem 2026, SESSIZ FAIL-OPEN onarimi — OLCULDU): kaynak_imzasi()
    eskiden KENDI yol yuruyusunu yapiyor ve ek kokleri `os.path.join(ev, giris)` ile
    kuruyordu. EK_EVLER["pruvo-hasat"] girislerinin 7'si GLOB tasir ("olcum/*.py");
    glob'lu yol ne isfile ne isdir oldugu icin SESSIZCE atlaniyordu. Olcum: imza 767
    dosya, kopya plani 2642 dosya; yalniz planda olan 1935 dosyanin 1934'u glob
    kapsamiydi (1'i kirli-izlenen). Sonuc, bu betigin varlik sebebi olan sinifin ta
    kendisiydi: o 1934 dosya degistiginde imza KIMILDAMIYOR, `--gerekliyse` "guncel"
    deyip YEDEGI ATLIYOR, kimse fark etmiyor, veri kaybi sonra patliyordu.
    Artik imza (kaynak_imzasi), dogrulama (ek_dogrula) ve kopyalama (ek_yaz/_yedekle)
    AYNI listeden turer -> iki tanim BIR DAHA AYRISAMAZ. Nobetci: durum-yedek-test.py
    bolum 11 (glob kapsamindaki dosya degisince imza DEGISMELI + kosum ATLAMAMALI).

    EK KAPSAM `ek_etkin_mi()` ile kapilidir — _yedekle() ile BIREBIR ayni kosul: ek
    faz kosmuyorsa o dosyalar hedefe yazilmaz, plana da girmemeli (yoksa --dogrula
    yazilmamis dosyalari "EKSIK" diye kirmizi yakardi)."""
    plan = []
    # ---- ANA YEDEK: memory + skills + repo kok dosyalari --------------------
    if os.path.isdir(MEMORY):
        for dizin, altlar, dosyalar in os.walk(MEMORY):
            altlar[:] = [a for a in altlar if a not in GURULTU_DIZIN]
            for dosya in sorted(dosyalar):
                kaynak = os.path.join(dizin, dosya)
                plan.append((kaynak, os.path.join("memory",
                                                  os.path.relpath(kaynak, MEMORY))))
    for gor in skills_plani()[0]:              # sir nobetinden GECMIS liste
        plan.append((os.path.join(SKILLS, gor), os.path.join("skills", gor)))
    # ~/.claude altindaki elle yazilmis agaclar (gorev tanimlari / cron nobeti /
    # planlar) — sir nobeti + acik allowlist'ten GECMIS liste. Plana buradan girer;
    # imza/dogrulama/kopya ucu de bu TEK tanimdan turer.
    for agac in AGAC_KAPSAMI:
        _etiket, kok, hedef_klasor, _izinli = agac
        for gor in agac_plani(agac)[0]:
            plan.append((os.path.join(kok, gor), os.path.join(hedef_klasor, gor)))
    for ad in _repo_dosyalari(sirlar):
        plan.append((os.path.join(ROOT, ad), ad))
    # ---- EK KAPSAM: kardes evler + diger hafiza uzaylari + genel ayar -------
    if ek_etkin_mi():
        for ad, ev in ev_yollari():
            dahil, _haric, _disi = ek_ev_plani(ev)
            for gor, hedef_gor in dahil:
                plan.append((os.path.join(ev, gor), _ek_ev_hedefi(ad, hedef_gor)))
        plan.extend(_ek_memory_girdileri())
        genel = _genel_ayar_girdisi()
        if genel and not genel[2]:             # sir nobeti elediyse yedege GIRMEZ
            plan.append((genel[0], genel[1]))
    return plan


# KARANTINA: koruma bir DOSYAYI reddettiginde o dosya ATLANIR, kosum DEVAM EDER.
def _drive_kopyala_karantinali(kaynak, varis):
    """`_drive_kopyala` + tek-dosya karantinasi. Doner: True=kopyalandi, False=atlandi.

    🔴 NEDEN VAR (olculdu 15 Agu 2026, AYNI GUN IKI KEZ): koruma dogru sinifi olcuyordu
    ama YANLIS GRANULERLIKTE davraniyordu — tek bir dosyanin reddi `copytree` yurumesini
    ortasindan kesip TUM yedegi dusuruyordu. Iki mesru vaka ayni gun yasandi:
      1. `mimar-posta-kutusu.md.lock` — flock nobetcisi, MESRU olarak daima 0 bayt;
      2. `posta-kutusu-kaan-izleme-ankor.txt` — izleme ankoru, 485 -> 185 bayta MESRU dustu.
    Ikisinde de sonuc AYNI: veri kaybina karsi kurulan koruma, yedek zincirini TAMAMEN
    kapatarak veri kaybi riskini ARTIRDI. Ilk vaka sifir-kolu onarimiyla kapatilmisti;
    ayni sinif AYNI GUN tekrar edince tekil yama BIRAKILDI ve sinif kapatildi
    -> [[tekil-yama-sinifi-kapatmaz]] · [[koruma-kurali-korudugunu-durdurur]].

    KORUNAN HAL AYNEN DURUYOR: reddedilen dosyanin kanonik yedegi TEK BAYT degismez.
    Degisen tek sey, redde ugramayan DIGER dosyalarin da yedeklenebilmesidir.
    Sessizlik YOK: atlanan her dosya `_KORUMA_KARANTINA`ya girer, ozet satirinda
    basilir ve kosumun cikis kodunu KIRMIZI yapar.
    """
    try:
        return _drive_kopyala(kaynak, varis)
    except YedekKorumaHatasi as e:
        _KORUMA_KARANTINA.append((varis, str(e)))
        return False


def _kopyala_gerekliyse(kaynak, varis):
    """Idempotent kopya: hedef AYNI boyut ve >= mtime ise DOKUNMAZ.
    Doner: True = kopyalandi, False = zaten guncel.
    🔴 NEDEN: ek kapsam yuzlerce MB gorsel/STL tasiyor ve bu betik HER push'ta
    kosuyor. Kosulsuz copy2 her push'u Drive'a yuzlerce MB yazmaya zorlardi."""
    try:
        k = os.stat(kaynak)
        h = os.stat(varis)
        if k.st_size == h.st_size and int(k.st_mtime) <= int(h.st_mtime):
            return False
    except OSError:
        pass
    os.makedirs(os.path.dirname(varis), exist_ok=True)
    return _drive_kopyala_karantinali(kaynak, varis)


def ek_yaz(backup):
    """EK KAPSAMI hedefe yazar. Doner: sayilar dict'i.

    Sir DEGERI hicbir yere yazilmaz: elenen dosyalarin YALNIZ yolu ve SEBEP SINIFI
    envantere girer (sir_sebebi metni kural/imza sinifi tasir, icerik TASIMAZ)."""
    kok = os.path.join(backup, EK_KLASOR)
    sayilar = {"ek_dosya": 0, "ek_yeni": 0, "ek_haric": 0, "ek_memory": 0,
               "ek_ev": 0, "ek_kapsam_disi": 0}
    envanter = []
    kapsam_disi_rapor = []

    for ad, ev in ev_yollari():
        dahil, haric, kapsam_disi = ek_ev_plani(ev)
        for gor, hedef_gor in dahil:
            try:
                yazildi = _kopyala_gerekliyse(
                    os.path.join(ev, gor),
                    os.path.join(backup, _ek_ev_hedefi(ad, hedef_gor)))
            except (OSError, shutil.Error) as e:
                print("  ⚠️ EK: kopyalanamadi %s/%s (%s)" % (ad, gor, type(e).__name__))
                continue
            sayilar["ek_dosya"] += 1
            sayilar["ek_yeni"] += 1 if yazildi else 0
        sayilar["ek_haric"] += len(haric)
        sayilar["ek_ev"] += 1
        for gor, sebep in haric:
            envanter.append("%s/%s   -> SEBEP: %s" % (ad, gor, sebep))
        for giris in kapsam_disi:
            kapsam_disi_rapor.append("%s/%s" % (ad, giris))
        sayilar["ek_kapsam_disi"] += len(kapsam_disi)
        print("  EK ev: %-16s %4d dosya (%d yeni), %d sir-disi, %d kapsam-disi"
              % (ad, len(dahil), sayilar["ek_yeni"], len(haric), len(kapsam_disi)))

    # Diger hafiza uzaylari — 5 evin en kritik varligi, hicbir depoda YOK.
    # (Liste _ek_memory_girdileri()'nden gelir: imza/dogrulama ile AYNI TANIM.)
    for kaynak, hedef_gor in _ek_memory_girdileri():
        try:
            if _kopyala_gerekliyse(kaynak, os.path.join(backup, hedef_gor)):
                sayilar["ek_yeni"] += 1
            sayilar["ek_memory"] += 1
            sayilar["ek_dosya"] += 1
        except (OSError, shutil.Error):
            pass
    if sayilar["ek_memory"]:
        print("  EK hafiza uzaylari: %d dosya, %d uzay"
              % (sayilar["ek_memory"], len(ek_memory_kokleri())))

    # ~/.claude/settings.json — makine geneli izin/hook ayari (sir nobetinden gecer)
    genel_girdi = _genel_ayar_girdisi()
    if genel_girdi:
        genel, genel_hedef, sebep = genel_girdi
        if sebep:
            envanter.append("%s   -> SEBEP: %s" % (genel, sebep))
            sayilar["ek_haric"] += 1
        else:
            try:
                if _kopyala_gerekliyse(genel, os.path.join(backup, genel_hedef)):
                    sayilar["ek_yeni"] += 1
                sayilar["ek_dosya"] += 1
            except (OSError, shutil.Error):
                pass

    # GORUNUR BOSLUK: alinmayanlar dosyaya yazilir. BOSSA DOSYA YAZILMAZ.
    _ek_rapor_yaz(kok, KAPSAM_DISI_ADI, kapsam_disi_rapor,
                  "EK KAPSAM DISI — gorulen ama yedege ALINMAYAN girisler.\n"
                  "Turetilmis/yeniden uretilebilir olanlar zaten elenmistir; burada\n"
                  "kalanlar GOZDEN GECIRILMELIDIR (deger tasiyorsa EK_EVLER'e ekle).\n")
    _ek_rapor_yaz(kok, SIR_ENVANTER_ADI, envanter,
                  "SIR ENVANTERI — bu dosyalar SIR TASIDIGI icin yedege ALINMADI.\n"
                  "🔴 BURADA YALNIZ YOL VE SEBEP SINIFI VARDIR; SIRRIN DEGERI YOKTUR.\n"
                  "Yeni hesapta bunlar KAYNAGINDAN yeniden saglanmalidir.\n"
                  "🔴 YINE DE: BU YEDEK KLASORU KIMSEYLE PAYLASILMAZ. Bu eleme AD\n"
                  "DESENINE gore yapilir, ICERIGE gore DEGIL — yedekte ad suzgecinden\n"
                  "gecen ticari gizli metin (raporlar/, .tedarikci-fiyat/, .uyelik-*)\n"
                  "vardir. Koruma paylasmama kuralindadir, yedek disi birakmakta degil.\n"
                  + _geri_kazanim_metni())
    return sayilar


def _geri_kazanim_metni():
    """Envanterin basligina eklenen GERI KAZANIM tablosu + yol bagimliligi uyarisi.
    Deger TASIMAZ; yalniz kaynak ve kirilma sonucu."""
    satirlar = ["", "GERI KAZANIM — nereden yeniden alinir / saglanmazsa ne kirilir:"]
    for ad in sorted(SIR_KOKENI):
        kaynak, kirilan = SIR_KOKENI[ad]
        satirlar.append("  %-28s kaynak: %s" % (ad, kaynak))
        satirlar.append("  %-28s kirilir: %s" % ("", kirilan))
    satirlar += [
        "",
        "⚠️ YOL BAGIMLILIGI (tasima riski): depolar ~/dev/pruvo… DISINA kurulursa",
        "   hafiza namespace yolu (~/.claude/projects/-Users-okan-dev-<ev>), launchd",
        "   plist'i ve izin satirlari KIRILIR; kurumsal bellek SESSIZCE gorunmez olur.",
        "   Geri yuklerken evleri AYNI yola kur ya da namespace adlarini elle esle.",
        "",
        "🔧 HOOK'LAR KLONLAMAYLA GELMEZ: yeni makinede",
        "   python3 tools/yedek-hook-kur.py --geri-yukle",
        "   (kanit: --kendini-test  ->  bos klonda kurulum + kapinin atesledigi olculur)",
        "",
    ]
    return "\n".join(satirlar) + "\n"


def _ek_rapor_yaz(kok, ad, satirlar, basli):
    """Rapor dosyasi — SATIR YOKSA DOSYA DA YOK (bos dosya sahte is izlenimi verir
    ve izole test ortaminda beklenmedik dosya sayisi yaratir)."""
    yol = os.path.join(kok, ad)
    if not satirlar:
        try:
            os.remove(yol)
        except OSError:
            pass
        return
    try:
        os.makedirs(kok, exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(basli)
            f.write("olculdu: %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
            f.write("-" * 70 + "\n")
            for s in satirlar:
                f.write(s + "\n")
    except OSError as e:
        print("  NOT: %s yazilamadi (%s)" % (ad, e))


def ek_dogrula(backup, ornek=8):
    """--dogrula: PLANDAKI her dosya hedefte GERCEKTEN var mi, boyutu tutuyor mu?
    Ayrica `ornek` kadar dosyada sha256 karsilastirir. Doner: (rapor dict, kirmizi).
    IDDIA DEGIL OLCUM: 'yedeklendi' demek yerine hedefi okur.

    Plan yedek_plani()'ndan gelir — imzayi olcen fonksiyonla AYNI TANIM (bkz. oradaki
    31 Tem gerekcesi); ayri bir liste kurmak, kapatilan ayrisma deligini geri acardi."""
    import hashlib
    plan = [(kaynak, os.path.join(backup, hedef))
            for kaynak, hedef in yedek_plani(sirlar=False)]

    eksik, boyut_farki, sha_farki, tamam, bayt = [], [], [], 0, 0
    for kaynak, varis in plan:
        try:
            k = os.stat(kaynak)
        except OSError:
            continue                     # kaynak kayboldu (yaris) -> sayma
        try:
            h = os.stat(varis)
        except OSError:
            eksik.append(varis)
            continue
        if k.st_size != h.st_size:
            boyut_farki.append("%s  (kaynak %d B / yedek %d B)"
                               % (varis, k.st_size, h.st_size))
            continue
        tamam += 1
        bayt += h.st_size
    adim = max(1, len(plan) // max(1, ornek))
    for kaynak, varis in plan[::adim][:ornek]:
        try:
            with open(kaynak, "rb") as f:
                a = hashlib.sha256(f.read()).hexdigest()
            with open(varis, "rb") as f:
                b = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            continue
        sha_farki.append((os.path.basename(varis), a[:16], a == b))
    return ({"plan": len(plan), "tamam": tamam, "bayt": bayt, "eksik": eksik,
             "boyut_farki": boyut_farki, "sha": sha_farki},
            bool(eksik or boyut_farki or [x for x in sha_farki if not x[2]]))


def kilit_yolu():
    """Kilit dosyasinin tam yolu (ANA calisma agacinin kokunde)."""
    return os.path.join(ROOT, KILIT_ADI)


SAHIP_OKUMA_DENEME = 5        # x SAHIP_OKUMA_ARALIGI = en fazla 100 ms (kilidi BEKLEMEZ)
SAHIP_OKUMA_ARALIGI = 0.02


def _sahip_imzasi(baslangic, pid=None, bitti=None, hata=None):
    """Kilit dosyasina yazilan sahip satiri.

    🔴 TAM HASSASIYET (repr): imza eskiden `%.3f` ile MILISANIYEYE YUVARLANIYORDU,
    karsilastirma (atlama_kapsandi_mi) ise tam hassas mtime ile yapiliyordu ->
    yuvarlama yonune gore karar YANLIS cikiyordu. Olculdu: 200 denemenin 94'u (%47)
    yanlis; yedekle-test.py 16 kosumun 6'sinda kirmizi yaniyordu (flake). repr(float)
    Python'da TAM tur-donusu garantiler: float(repr(x)) == x.

    `bitti` doluysa satir "bu kosum DUZGUN BITTI" demektir (kilit_birak yazar).
    🔴 NEDEN BOSALTMIYORUZ (curutucu F1): kilit_birak eskiden dosyayi ftruncate ile
    BOSALTIYORDU. Sahip hizli bitince (or. `--gerekliyse` GUNCEL yolu) atlayan kosum
    kilidi hala TUTULUYOR bulup imzayi BOS okuyordu (20 kosumun 15'i) -> sahip
    tanimlanamiyor -> fail-closed yanlis ⚠⚠ uyari. Iz birakmak hem bu bosluğu kapatir
    hem panoya "temiz bitti mi, yarida mi kaldi" ayrimini verir.

    🔴 `hata` (K1, 27 Tem — MERGE BLOKLAYICI kusurun onarimi): kosum ISTISNAYLA
    bittiginde iz `bitti=` TASIMAZ, yerine `hata=<an>` tasir. Sebep tur-4'te GERCEK
    ICRAYLA olculdu: `main()`in `finally` blogu istisna yolunda DA `bitti=` yaziyordu
    -> durum.kilit_durumu izi 'yok' sayiyor, pano "YARIM KALMIS YEDEK" DEMIYOR, damga
    da eski kaldigi icin "taze" diyordu. Yani dalin getirdigi nobetci, kilidin EN SIK
    hata biciminde OLUYDU (izden `bitti=` elle silinince pano dogru sekilde
    "⚠⚠ YARIM KALMIS YEDEK" diyor). `hata=` alanini durum.py'nin ayristirmasi
    GORMEZDEN gelir (yalniz pid/baslangic/bitti arar) -> iz `bitti=`siz kalir,
    surec de olmustur => pano 'yarim' der. Teshis icin an yine kayitli olur."""
    satir = "pid=%d baslangic=%s iso=%s" % (
        os.getpid() if pid is None else pid, repr(float(baslangic)),
        time.strftime("%Y-%m-%d %H:%M:%S"))
    if bitti is not None:
        satir += " bitti=%s" % repr(float(bitti))
    if hata is not None:
        satir += " hata=%s" % repr(float(hata))
    return satir + "\n"


def _imza_coz(metin):
    """Sahip satirindan (pid, baslangic, bitti) ayiklar. Bozuk/eksikse None doner."""
    pid = baslangic = bitti = None
    for parca in (metin or "").split():
        if parca.startswith("baslangic="):
            try:
                baslangic = float(parca.split("=", 1)[1])
            except ValueError:
                baslangic = None
        elif parca.startswith("bitti="):
            try:
                bitti = float(parca.split("=", 1)[1])
            except ValueError:
                bitti = None
        elif parca.startswith("pid="):
            try:
                pid = int(parca.split("=", 1)[1])
            except ValueError:
                pid = None
    return pid, baslangic, bitti


def _kilit_sahibi_bilgisi(fd, deneme=None, aralik=None):
    """Kilidi TUTAN kosumun kendi yazdigi satiri (pid + baslangic) okur.
    Kilitsiz okuma -> BEST EFFORT: bos/bozuksa 'bilgi yok' der, ASLA patlamaz.
    Doner: (metin, yas_saniye | None, sahip_baslangici | None).

    NEDEN KISA TEKRAR: sahip once flock alir, imzasini MIKROSANIYELER SONRA yazar.
    Eszamanli iki push tam bu bosluga dusuyor (olculdu: 3 turun 2'sinde) -> sahip
    baslangici okunamadigi icin atlama "kapsama bilinmiyor" = fail-closed uyari
    uretiyordu; her paralel push'ta bosuna sari pano (gurultulu pano = olu pano).
    Burada KILIT BEKLENMIYOR, yalnizca teshis satiri icin en fazla 100 ms okunuyor."""
    deneme = SAHIP_OKUMA_DENEME if deneme is None else deneme
    aralik = SAHIP_OKUMA_ARALIGI if aralik is None else aralik
    ham = ""
    for i in range(max(1, deneme)):
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            ham = os.read(fd, 256).decode("utf-8", "replace").strip()
        except OSError:
            ham = ""
        if ham:
            break
        if i + 1 < deneme:
            time.sleep(aralik)
    if not ham:
        return "sahip bilgisi yok", None, None
    _pid, baslangic, _bitti = _imza_coz(ham)
    yas = None if baslangic is None else (time.time() - baslangic)
    return ham.replace("\n", " "), yas, baslangic


def atlama_kapsandi_mi(sahip_baslangici, kaynak_mtime):
    """ATLANAN kosumun isini, KOSMAKTA OLAN yedek kapsiyor mu? (saf fonksiyon)

    Kosan yedek `sahip_baslangici`nda basladi -> o andan ONCE degismis her kaynak
    onun kopyasina girer. Demek ki en yeni kaynak mtime'i sahip baslangicindan
    kucuk/esitse atlanan kosumun yapacagi FAZLADAN bir is YOKTU: atlama zararsiz.
    Aksi halde (ya da olcemedigimiz her halde) FAIL-CLOSED: kapsanmadi say, pano uyarsin.

    NEDEN ZAMAN TOLERANSI DEGIL: eszamanli iki push'ta sahip baslangici ile atlama
    ani mikrosaniyelerle ayrilir; "atlama baslangictan sonra mi" diye bakmak yazi-tura
    olur ve pano her paralel push'ta bosuna sariya doner (gurultulu pano = olu pano).
    Burada karar OLCUMLE veriliyor: degisen bir sey var miydi?"""
    if not isinstance(sahip_baslangici, (int, float)):
        return False
    if not isinstance(kaynak_mtime, (int, float)):
        return False
    return kaynak_mtime <= sahip_baslangici


def kilit_al(yol=None):
    """Yedeklemeyi tek kosuma serilestirir. BEKLEMEZ (LOCK_NB).

    Doner: (hal, fd, bilgi)
      hal 'alindi'     -> fd ile kilit BIZDE; bilgi = KILIT ALIS ANI (float).
                          Bu an damgaya `baslangic` olarak yazilir; boylece kilit
                          dosyasindaki imza ile damga BIREBIR AYNI degeri tasir
                          (atlayan kosum "sahibim damgayi yazdi mi" karsilastirmasini
                          esitlikle yapabilsin; time.time() MONOTON DEGIL, iki ayri
                          okuma milisaniye altinda geriye gidebiliyor).
      hal 'mesgul'     -> baska kosum yediyor; bilgi = (sahip satiri, yas, baslangic).
      hal 'kurulamadi' -> kilit dosyasi bile acilamadi (ROOT yazilamiyor).
                          FAIL-OPEN: cagiran KILITSIZ devam eder — yedegin hic
                          alinmamasi, nadir bir yaris ihtimalinden daha pahali.
    """
    yol = kilit_yolu() if yol is None else yol
    try:
        fd = os.open(yol, os.O_CREAT | os.O_RDWR, 0o600)
    except OSError as e:
        return "kurulamadi", None, ("kilit dosyasi acilamadi: %s" % e)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        bilgi = _kilit_sahibi_bilgisi(fd)
        os.close(fd)
        return "mesgul", None, bilgi
    alis = time.time()
    try:                                    # sahip imzasi: atlayan kosum bunu basar
        os.ftruncate(fd, 0)
        os.write(fd, _sahip_imzasi(alis).encode("utf-8"))
    except OSError:
        pass                                # imza kolaylik; kilit yine gecerli
    return "alindi", fd, alis


def kilit_birak(fd, baslangic=None, basardi=False):
    """Kilidi birakir. Dosyayi SILMEZ (silmek iki surecin ayri inode kilitlemesine
    yol acar) ve BOSALTMAZ: imzanin ustune sonuc isaretini yazar.

    🔴 NEDEN BOSALTMIYORUZ: bosaltma, kilit HALA TUTULURKEN oluyordu; hizli biten bir
    sahibi yakalayan atlayan kosum imzayi bos okuyup sahibi tanimlayamiyordu (olculdu:
    20 kosumun 15'i) ve fail-closed yanlis uyari uretiyordu. `bitti=` isareti hem bu
    boslugu kapatir hem panoya "temiz bitti" (sessiz) ile "yarida kaldi" (pid olu,
    isaret yok -> UYAR) ayrimini kazandirir.

    🔴 `basardi` (K1, 27 Tem): `bitti=` YALNIZ tamamlanan kosumda yazilir. Eskiden
    `finally` blogu istisnada da `bitti=` yaziyordu ve pano en sik hata biciminde
    (kosum ortada cokuyor) SUSUYORDU — dalin kendi amaci olen yerdi. Simdi:
      basardi=True  -> `bitti=` (pano SESSIZ; temiz birakma)
      basardi=False -> `hata=`  (pano 'yarim' -> ⚠⚠ YARIM KALMIS YEDEK)
    FAIL-CLOSED varsayilan: cagiran basariyi ACIKCA bildirmezse iz `bitti=` TASIMAZ.
    ⚠️ MESRU ATLAMA YOLU BUNDAN AYRIDIR: kilit mesgulse main() kilit_fd=None ile
    doner, buraya hic girmez (fail-open atlama kirmiziya CEVRILMEZ)."""
    if fd is None:
        return
    try:
        try:
            if isinstance(baslangic, (int, float)):
                os.ftruncate(fd, 0)
                os.lseek(fd, 0, os.SEEK_SET)
                simdi = time.time()
                if basardi:
                    imza = _sahip_imzasi(baslangic, bitti=simdi)
                else:
                    imza = _sahip_imzasi(baslangic, hata=simdi)
                os.write(fd, imza.encode("utf-8"))
            else:
                os.ftruncate(fd, 0)     # baslangic bilinmiyorsa iz birakma
        except OSError:
            pass
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def damga_oku(backup):
    """backup/.son-yedek.json -> dict, yoksa/bozuksa None (ASLA patlamaz)."""
    return _json_oku(backup, DAMGA_ADI)


def atlama_oku(backup):
    """backup/.son-yedek-atlama.json -> dict, yoksa/bozuksa None (ASLA patlamaz)."""
    return _json_oku(backup, ATLAMA_ADI)


def _json_oku(backup, ad):
    try:
        with open(os.path.join(backup, ad), encoding="utf-8", errors="replace") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return None
    return veri if isinstance(veri, dict) else None


def _json_atomik_yaz(backup, ad, veri):
    """JSON'u ATOMIK yazar (tmp + os.replace) — okuyucu ASLA yarim dosya gormez.
    Bu dosyalarin her birinin TEK yazici sinifi vardir (damga: kilidi tutan kosum,
    atlama: atlayan kosum) -> oku-degistir-yaz yarisi yapisal olarak yok."""
    try:
        os.makedirs(backup, exist_ok=True)
        gecici = os.path.join(backup, ad + ".tmp-%d" % os.getpid())
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(gecici, os.path.join(backup, ad))
        return True
    except OSError as e:
        print("NOT: %s yazilamadi (%s) — yedek YINE DE alindi." % (ad, e))
        return False


def _damga_dosyasi_yaz(backup, veri):
    return _json_atomik_yaz(backup, DAMGA_ADI, veri)


def damga_yaz(backup, sayilar, eksik=None, baslangic=None, kilitsiz=False, imza=None):
    """Kosum sonunda tazelik damgasini yazar. Basarisiz olursa YEDEGI BOZMAZ
    (uyari basar, cikis kodunu degistirmez) — damga bir kolaylik, yedek asil is.

    F1: `eksik` doluysa damga "tam": False ile isaretlenir. TAM GUVEN damgasi
    yalniz gercekten eksiksiz kosumda atilir; pano kismi yedegi TAZE SAYMAZ.

    `baslangic`: bu kosumun BASLADIGI an. Kopyalama atomik degil -> baslangictan
    SONRA degisen kaynak yedege girmemis olabilir; pano ve --gerekliyse karari bunu
    referans alir (bkz. modul basligi).
    ATLAMA KAYDI KORUNUR: onceki damgadaki `son_atlama*` alanlari tasinir — yoksa
    tamamlanan kosum, kendisinden ONCE atlanmis (ve dolayisiyla kapsanmamis olabilecek)
    bir kosumun izini siler ve pano o kaybi hic gormezdi."""
    eksik = list(eksik or [])
    onceki = damga_oku(backup) or {}
    veri = {"surum": 4, "zaman": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "baslangic": baslangic if isinstance(baslangic, (int, float)) else time.time(),
            "tam": not eksik, "eksik": eksik, "kok": ROOT}
    if kilitsiz:
        veri["kilitsiz"] = True
    # 🔴 KAYNAK IMZASI (K3): bu KOPYANIN ICINDEKI kaynak kumesinin parmak izi.
    # ⚠️ KOSUM BASINDA olculur, sonunda DEGIL: kopyalama atomik degil, kosum
    # SIRASINDA degisen bir dosya yedege GIRMEMIS olabilir. Sonda olcsek o
    # degisiklik imzaya girer ve bir sonraki `--gerekliyse` "imzalar ayni" deyip
    # panoyu GUNCEL yakardi — kapatmaya calistigimiz sessiz-yesilin ta kendisi.
    if isinstance(imza, dict):
        veri["kaynak_imzasi"] = imza
    # ONEK ILE tasi, ELLE LISTELEME: sabit liste bir kez eksik kaldi ve pano her
    # paralel push'ta bosuna uyardi (kabul testi yakaladi). Yeni bir `son_atlama_*`
    # alani eklendiginde burayi guncellemek GEREKMEZ.
    for alan in onceki:
        if alan.startswith("son_atlama"):
            veri[alan] = onceki[alan]
    veri.update(sayilar)
    return _damga_dosyasi_yaz(backup, veri)


def damga_tazele(backup, baslangic, imza=None, kilitsiz=False):
    """`--gerekliyse` OLCUMU: kopyalama YAPILMADI ama "hicbir kaynak son kosumdan beri
    degismemis" OLCULDU -> damganin `baslangic`i bu ana ilerletilir.

    🔴 NEDEN (curutucu F2): baskin gercek yol iki paralel `--gerekliyse` push'udur ve
    o yolda kazanan kosum GUNCEL deyip damga YAZMIYORDU. Atlayan kosumun bekledigi
    "sahip damgayi yazdi mi" sorusu boylece TANIM GEREGI asla saglanamiyor, uyari
    YAPISKAN kaliyordu (20/20 yanlis ⚠⚠; ancak bir kaynak degisince kalkiyordu).
    Pano tek gorunur kanal oldugu icin bu, "gurultulu pano = olu pano" demekti.

    🔴 NEDEN OLCUM ZAYIFLAMIYOR (uyariyi susturmak icin degil): bu kosum
    `en_yeni_kaynak_mtime() <= eski baslangic` esitsizligini GERCEKTEN olctu. Yeni
    referans olarak KILIT ALIS ANI kullanilir; o an mtime taramasindan ONCEDIR, yani
    taramadan sonra degisen dosya bir sonraki kosumda YINE yakalanir. `zaman` ve
    sayilar DOKUNULMAZ — onlar son GERCEK kopyalamaya aittir, pano yasi ondan okur.
    `eksik/tam` yeniden degerlendirilir (4 ucuz exists cagrisi): araya silinmis bir
    beklenen dosya "tam" kalmasin.

    🔴 K3 — "DEGISIKLIK YOK" ILE "YEDEK BAYAT" AYRI SEYLERDIR: bu yol `zaman`a
    DOKUNMAZ (dogru: son GERCEK kopyalama o an oldu), ama pano bayatligi `zaman`dan
    olctugu icin degismeyen bir sistemde 2 gun sonra BOSUNA "⚠⚠ YEDEK BAYAT" diyordu.
    Artik bu kosum OLCUMUNU damgaya yazar:
      `dogrulandi`        -> dogrulamanin ANI (sayi; pano tazeligini buradan olcer)
      `dogrulama_imzasi`  -> O KOSUMDA olculen kaynak imzasi
    Pano GUNCEL diyebilmek icin `dogrulama_imzasi`nin damganin `kaynak_imzasi`na
    (kopyanin icerigi) ESIT oldugunu KENDISI dogrular — iddiaya GUVENMEZ.
    ⚠️ IMZA OLCULEMEDIYSE (imza=None) dogrulama alanlari YAZILMAZ, varsa SILINIR:
    sessiz yesil uretmek yerine pano ⚪ OLCULEMEDI/BAYAT der (fail-closed).

    🔴 `kilitsiz` KOSUM-YEREL (K3): eskiden `dict(onceki)` ile MIRAS aliniyordu ->
    bir kez kilitsiz kosan sistemde not SONSUZA DEK yapisiyordu. Artik bayrak bu
    kosumun kendi halini gosterir (kilitliyse SILINIR).
    ⚠️ ILAN EDILMIS KOR NOKTA: kilitsiz bir KOPYALAMA'dan sonra kilitli bir
    dogrulama kosumu notu temizler; `zaman`/sayilar hala o kopyaya aittir."""
    onceki = damga_oku(backup)
    if not isinstance(onceki, dict) or not isinstance(onceki.get("zaman"), (int, float)):
        return False                    # ortada tamamlanmis kosum yok -> uydurma
    veri = dict(onceki)
    veri["baslangic"] = float(baslangic)
    veri["dogrulandi_iso"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(imza, dict):
        veri["dogrulandi"] = float(baslangic)
        veri["dogrulama_imzasi"] = imza
    else:                               # OLCULEMEDI -> yesil iddia BIRAKMA
        veri.pop("dogrulandi", None)
        veri.pop("dogrulama_imzasi", None)
    if kilitsiz:
        veri["kilitsiz"] = True
    else:
        veri.pop("kilitsiz", None)
    eksik = repo_eksikleri()
    veri["eksik"] = eksik
    veri["tam"] = (not eksik) and bool(onceki.get("tam", True))
    return _damga_dosyasi_yaz(backup, veri)


def atlama_kaydet(backup, sebep, kapsandi=False, sahip_baslangici=None):
    """Kilit alinamadigi icin ATLANAN kosumu damgaya isler.

    🔴 GUVEN ALANLARINA DOKUNMAZ (zaman/iso/baslangic/tam/eksik/sayilar): bu kosum
    HICBIR SEY yedeklemedi; tazelik iddiasi son GERCEK kosuma aittir. Atlama yalniz
    `son_atlama*` alanlarina yazilir.

    IKI ALAN, IKI AYRI SORU (ikisi de OLCUM, varsayim DEGIL):
      `son_atlama_kapsandi`         -> atlama_kapsandi_mi(): kosan yedek BASLARKEN
                                       butun degisiklikler yerinde miydi?
      `son_atlama_sahip_baslangici` -> hangi kosumun BITMESINI bekliyoruz? Panoda
                                       damganin `baslangic`i bu degerden KUCUKSE o
                                       kosum damgayi HIC yazmamistir (asildi/oldu)
                                       -> pano UYARIR.
    🔴 NEDEN IKISI BIRDEN (curutucu senaryosu, 26 Tem): tek basina `kapsandi=True`
    "kosan yedek BITECEK" VARSAYIMIDIR. Sahip kilidi aldiktan sonra asilir/olurse
    dosya yedege hic girmez; atlayan kosum "kapsandi" demistir ve pano esige kadar
    (2 gun) "taze" der = tam da kapatmaya calistigimiz sessiz-hata sinifi. Bekleyen
    sahibin baslangicini yazip panoda COZUMLEYEREK varsayim olcume cevrilir.
    AYRI DOSYAYA (ATLAMA_ADI) yazilir ve damga OKUNMAZ/DEGISTIRILMEZ: oku-degistir-yaz
    yarisi boylece yapisal olarak yok (bkz. ATLAMA_ADI gerekcesi)."""
    veri = {"son_atlama": time.time(),
            "son_atlama_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "son_atlama_sebep": sebep,
            "son_atlama_kapsandi": bool(kapsandi)}
    if isinstance(sahip_baslangici, (int, float)):
        veri["son_atlama_sahip_baslangici"] = sahip_baslangici
    # sahibi tanimlayamadiysak alan HIC yazilmaz -> pano fail-closed UYARIR
    return _json_atomik_yaz(backup, ATLAMA_ADI, veri)


def kaynak_imzasi(sirlar=False):
    """Yedeklenecek kaynak KUMESININ icerik parmak izi — YEDEK PLANINDAN turer.
    Doner: {"adet": n, "bayt": toplam_boyut, "mtime": en_yeni} ya da olculemezse None.

    🔴 KUME yedek_plani()'DIR, AYRI BIR YURUYUS DEGIL (31 Tem — fail-open onarimi):
    imza kendi kok listesini kurdugu surece kopya planiyla AYRISABILIYORDU ve ayristi
    da (glob'lu 1934 dosya imzaya HIC girmiyordu; gerekce yedek_plani docstring'inde).
    Imzanin sordugu soru "yedege girecek dosyalarda degisiklik var mi"dir; o kumenin
    tanimi TEK yerdedir. Buraya ikinci bir os.walk EKLEME — bolum 11 nobetcisi
    "imza adedi == plan uzunlugu" invaryantini olcer ve ayrisma KIRMIZI yanar.

    🔴 NEDEN MTIME TEK BASINA YETMEZ (K3, 27 Tem): pano artik esigi asmis bir yedegi
    "degisiklik YOK" OLCUMUNE dayanarak GUNCEL sayabiliyor. Boyle bir iddia mtime'dan
    fazlasina dayanmak zorunda, yoksa K1'i kapatip ayni sessiz-yesil deligini baska
    kapidan acmis olurduk. Imza UC eksen tasir:
      adet  -> dosya EKLENMESI/SILINMESI (mtime tabani hic degismeyebilir)
      bayt  -> mtime KORUNARAK yapilan icerik degisikligi (kopyalama/geri yukleme)
      mtime -> siradan duzenleme (mevcut davranis)
    Maliyet artmaz: os.stat TEK cagride hem boyut hem mtime verir; eskiden getmtime
    de ayni stat'i yapiyordu.

    OKUNAMAYAN DOSYA ATLANMAZ, SAYILIR DEGIL: stat patlarsa o dosya imzaya girmez —
    bu imzayi DEGISTIRIR (adet duser) ve karsilastirma "degisti" der = fail-closed."""
    adet = 0
    bayt = 0
    enyeni = None
    for kaynak, _hedef in yedek_plani(sirlar):
        try:
            st = os.stat(kaynak)
        except OSError:
            continue
        adet += 1
        bayt += st.st_size
        if enyeni is None or st.st_mtime > enyeni:
            enyeni = st.st_mtime
    if enyeni is None:
        return None                      # hicbir kaynak okunamadi -> OLCULEMEDI
    return {"adet": adet, "bayt": bayt, "mtime": enyeni}


def imza_esit_mi(a, b):
    """Iki kaynak imzasi AYNI kumeyi mi gosteriyor? (saf fonksiyon, fail-closed)
    Eksik/bozuk/tur uyusmayan her halde False -> "degisti" say, yedekle/uyar."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    for alan in ("adet", "bayt", "mtime"):
        x, y = a.get(alan), b.get(alan)
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return False
        if x != y:
            return False
    return True


def en_yeni_kaynak_mtime(sirlar=False):
    """Yedeklenecek kaynaklardaki EN YENI mtime. Hicbiri okunamazsa None.
    (kaynak_imzasi'nin mtime eksenine ince kabuk — TEK gezinme kodu orada.)"""
    imza = kaynak_imzasi(sirlar)
    return None if imza is None else imza["mtime"]


def gerekli_mi(damga, kaynak_mtime, imza=None):
    """--gerekliyse karari (saf fonksiyon). FAIL-OPEN: emin olamadigimiz her halde
    YEDEKLE (damga yok/bozuk, mtime olculemedi). Yalniz 'damga var VE kaynak ondan
    eski' halinde atlar — yani atlamak KANITA bagli, yedeklemek varsayilan.

    REFERANS = `baslangic` (kosumun BASLADIGI an), varsa. Bitis (`zaman`) ile
    karsilastirmak yaniltir: kopyalama atomik degil, kosum SIRASINDA degisen dosya
    yedege girmemis olabilir ama mtime'i bitisten KUCUK oldugu icin "guncel" sayilirdi.
    Eski surum damgalarinda `baslangic` yok -> `zaman`a duser (davranis degismez).

    🔴 IMZA EKSENI (K3): `imza` verildi VE damgada karsilastirilabilir bir
    `kaynak_imzasi` VARSA, imzalar farkliysa mtime ne derse desin YEDEKLE. Bu
    daraltma DEGIL genisletmedir (atlama sartlari artti) -> fail-open korunur;
    ayrica mtime'i korunarak degistirilmis dosyanin sessizce atlanmasini kapatir."""
    if not isinstance(damga, dict):
        return True
    referans = damga.get("baslangic")
    if not isinstance(referans, (int, float)):
        referans = damga.get("zaman")
    if not isinstance(referans, (int, float)):
        return True
    if kaynak_mtime is None:
        return True
    if isinstance(imza, dict) and isinstance(damga.get("kaynak_imzasi"), dict):
        if not imza_esit_mi(imza, damga["kaynak_imzasi"]):
            return True
    return kaynak_mtime > referans


def main():
    # --help yedekleme BASLATMASIN (denetim 2026-07-15: --help dogrudan yaziyordu).
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__.strip())
        return 0
    # BILINMEYEN BAYRAK = FAIL-CLOSED. Yazim hatasi ("--kuruu") sessizce GERCEK yedek
    # baslatmasin; ayni sinif hata --help'te bir kez yasandi.
    bilinmeyen = [a for a in sys.argv[1:] if a not in BAYRAKLAR]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        print("Gecerli: " + ", ".join(sorted(BAYRAKLAR)), file=sys.stderr)
        return 2

    kuru = ("--kuru" in sys.argv) or ("--dry-run" in sys.argv)
    gerekliyse = "--gerekliyse" in sys.argv
    sirlar = "--sirlar" in sys.argv
    sir_temizle = "--sir-temizle" in sys.argv
    kuru_prova = "--kuru-prova" in sys.argv
    if sirlar:
        print("NOT: --sirlar EMEKLI (8 Agu 2026, Okan karari) — sir dosyalari yedege "
              "ARTIK GIRMEZ; bayrak kapsami DEGISTIRMEZ.")

    # ---- KURU PROVA: hicbir sey SILINMEZ/YAZILMAZ, ne silinecegini basar -----
    if kuru_prova:
        pruvo_drive = drive_yolu.pruvo_dizini(sessiz=True)
        if not pruvo_drive:
            print("KURU PROVA OLCULEMEDI — Drive yolu cozulemedi.", file=sys.stderr)
            return 1
        backup = os.path.join(pruvo_drive, YEDEK_KOK_ADI)
        print("KURU PROVA — hicbir dosya SILINMEDI/YAZILMADI.")
        print("Hedef: " + backup)
        sayilar = yedek_kok_sir_raporu(backup, sir_temizle=True, kuru_prova=True)
        # skills agacindaki BAYAT sir kopyalari (mevcut yol) — ayni provada gorunsun.
        _s_dahil, s_haric, _g = skills_plani()
        s_bayat = [os.path.join(backup, "skills", g) for g, _s in s_haric
                   if os.path.exists(os.path.join(backup, "skills", g))]
        print("  SKILLS BAYAT SIR KOPYASI: %d" % len(s_bayat))
        for y in s_bayat:
            print("    KURU PROVA — SILINECEK: " + y)
        kok_silinecek = sayilar["kok_sir_bulunan"] - sayilar["kok_sir_atlanan"]
        print("TOPLAM SILINECEK: %d (kok %d + skills %d) · SILINMEYECEK (fail-closed): %d"
              % (kok_silinecek + len(s_bayat), kok_silinecek, len(s_bayat),
                 sayilar["kok_sir_atlanan"]))
        print("Gercek silme icin: python3 tools/yedekle.py --sir-temizle")
        return 0

    # ---- DOGRULAMA KOSUMU: hicbir sey yazmaz, hedefi OLCER -----------------
    if "--dogrula" in sys.argv:
        pruvo_drive = drive_yolu.pruvo_dizini()
        if not pruvo_drive:
            print("DOGRULANAMADI — Drive yolu cozulemedi.", file=sys.stderr)
            return 1
        backup = os.path.join(pruvo_drive, YEDEK_KOK_ADI)
        rapor, kirmizi = ek_dogrula(backup)
        print("DOGRULAMA — hedef: " + backup)
        print("  planda %d dosya; hedefte BOYUTU TUTAN %d dosya, %d bayt"
              % (rapor["plan"], rapor["tamam"], rapor["bayt"]))
        print("  EKSIK: %d   BOYUT FARKI: %d" % (len(rapor["eksik"]), len(rapor["boyut_farki"])))
        for y in rapor["eksik"][:20]:
            print("    EKSIK: " + y)
        for y in rapor["boyut_farki"][:20]:
            print("    FARK : " + y)
        for ad, sha, esit in rapor["sha"]:
            print("    sha256 %s %s  %s" % ("ESIT " if esit else "FARKLI", sha, ad))
        print("SONUC: " + ("🔴 KIRMIZI — yedek EKSIK/BOZUK" if kirmizi
                           else "✅ YESIL — plandaki her dosya hedefte, boyutlar tutuyor"))
        return 1 if kirmizi else 0

    dahil, haric, gurultu = skills_plani()

    # ---- KURU KOSUM: hicbir sey yazma, sadece plani bas -------------------
    if kuru:
        pruvo_drive = drive_yolu.pruvo_dizini(sessiz=True)
        hedef = os.path.join(pruvo_drive, YEDEK_KOK_ADI) if pruvo_drive else None
        print("KURU KOSUM — hicbir dosya YAZILMADI.")
        print("Hedef: " + (hedef or "(Drive COZULEMEDI — gercek kosumda yedek ALINMAZ)"))
        mem = _agac_dosyalari(MEMORY)
        print("-" * 70)
        print("[memory] %d dosya  <- %s" % (len(mem), MEMORY))
        for g in mem:
            print("    memory/" + g)
        print("[skills] %d dosya  <- %s" % (len(dahil), SKILLS))
        for g in dahil:
            print("    skills/" + g)
        print("[skills-HARIC (sir nobeti)] %d dosya" % len(haric))
        for g, sebep in haric:
            print("    skills/%s   -> ELENDI: %s" % (g, sebep))
        print("[skills-gurultu (turetilmis)] %d giris" % len(gurultu))
        for g in gurultu:
            print("    skills/" + g)
        # ---- ~/.claude ELLE YAZILMIS AGACLAR (gorev / cron / plan) --------
        agac_toplam = 0
        agac_haric_toplam = 0
        for agac in AGAC_KAPSAMI:
            etiket, kok, hedef_klasor, _izinli = agac
            a_dahil, a_haric, a_gurultu = agac_plani(agac)
            agac_toplam += len(a_dahil)
            agac_haric_toplam += len(a_haric)
            print("[%s] %d dosya  <- %s" % (hedef_klasor, len(a_dahil), kok))
            for g in a_dahil:
                print("    %s/%s" % (hedef_klasor, g))
            print("[%s-DISLANAN (sir nobeti + acik allowlist)] %d dosya"
                  % (etiket, len(a_haric)))
            for g, sebep in a_haric:
                print("    %s/%s   -> DISLANDI: %s" % (hedef_klasor, g, sebep))
            print("[%s-gurultu (turetilmis)] %d giris" % (etiket, len(a_gurultu)))
        repo, kok_elenen = repo_kok_ayrimi()
        print("[repo] %d dosya  <- %s" % (len(repo), ROOT))
        for a in repo:
            print("    " + a)
        print("[repo-SIR ELEMESI (kanonik kume: REPO_SIR + SIR_ADLARI)] %d dosya"
              % len(kok_elenen))
        for a, sebep in kok_elenen:
            print("    %s   -> ELENDI, YEDEGE GIRMEZ: %s" % (a, sebep))
        eksik = repo_eksikleri()
        print("[repo-EKSIK (beklenen ama yok)] %d" % len(eksik))
        for a in eksik:
            print("    %s   -> KISMI YEDEK: damga 'tam: false' olur" % a)
        # ---- EK KAPSAM (kardes evler + diger hafiza uzaylari) --------------
        ek_toplam = 0
        if not ek_etkin_mi():
            print("[EK KAPSAM] KAPALI — bilinen kardes ev bulunamadi (kok: %s)" % ROOT)
        else:
            for ad, ev in ev_yollari():
                e_dahil, e_haric, e_disi = ek_ev_plani(ev)
                ek_toplam += len(e_dahil)
                print("[ek/%s] %d dosya  <- %s" % (ad, len(e_dahil), ev))
                for g, sebep in e_haric:
                    print("    %s   -> SIR NOBETI ELEDI: %s" % (g, sebep))
                for g in e_disi:
                    print("    %s   -> KAPSAM DISI (gozden gecir)" % g)
            for ns, yol in ek_memory_kokleri():
                n = len(_agac_dosyalari(yol))
                ek_toplam += n
                print("[ek/memory-evler/%s] %d dosya" % (ns, n))
            # ~/.claude/settings.json: PLANDA sayilir (bkz. yedek_plani) ama bu
            # dokumde eksikti -> TOPLAM ile hemen altindaki KAYNAK IMZASI adedi
            # 1 fark ediyordu. Sayilar ayni sayfada CELISMEZ.
            _genel = _genel_ayar_girdisi()
            if _genel and _genel[2]:
                print("[ek/claude-genel] settings.json -> SIR NOBETI ELEDI: %s" % _genel[2])
            elif _genel:
                ek_toplam += 1
                print("[ek/claude-genel] 1 dosya  <- %s" % _genel[0])
        print("-" * 70)
        print("TOPLAM YEDEKLENECEK: %d dosya "
              "(memory %d + skills %d + claude-agaclari %d + repo %d + ek %d)"
              % (len(mem) + len(dahil) + agac_toplam + len(repo) + ek_toplam,
                 len(mem), len(dahil), agac_toplam, len(repo), ek_toplam))
        if haric:
            print("SIR NOBETI: %d dosya paket DISINDA birakilacak." % len(haric))
        if agac_haric_toplam:
            print("AGAC DISLAMA: %d dosya paket DISINDA birakilacak." % agac_haric_toplam)
        # BEYAN HIZALAMASI (1 Agu 2026) — gercek kosumdaki uyarinin AYNISI kuru
        # kosumda da basilir; envanterin DOGRULAMA komutu budur, beyan orada da
        # gercekle ayni olmalidir. (Gerekce: gercek kosumdaki ayni metnin yaninda.)
        print("🔴 BU YEDEK KLASORU KIMSEYLE PAYLASILMAZ (link/dosya/e-posta) — ticari gizli")
        print("   icerik tasir: raporlar/, .tedarikci-fiyat/, .uyelik-*. Sir nobeti ADA gore")
        print("   eler, ICERIGE gore degil.")
        damga = damga_oku(hedef) if hedef else None
        print("TAZELIK DAMGASI: %s" % (damga.get("iso") if damga else "(yok)"))
        k_imza = kaynak_imzasi(sirlar)
        print("KAYNAK IMZASI: %s" % (k_imza or "(OLCULEMEDI)"))
        print("--gerekliyse karari: %s"
              % ("YEDEKLE" if gerekli_mi(damga, None if k_imza is None else k_imza["mtime"],
                                         imza=k_imza) else "ATLA (guncel)"))
        # Kilit DENENMEZ: kuru kosumda kilidi bir an icin almak, o sirada kosan
        # GERCEK bir yedegi atlatirdi. Sadece dosya icerigine bakilir (best effort).
        tutuluyor = ""
        try:
            with open(kilit_yolu(), encoding="utf-8", errors="replace") as f:
                tutuluyor = f.read(256).strip()
        except OSError:
            pass
        print("KILIT: %s   %s" % (kilit_yolu(),
                                  ("(su an TUTULUYOR gorunuyor: %s)" % tutuluyor.replace("\n", " "))
                                  if tutuluyor else "(bos — tutulmuyor gorunuyor)"))
        return 0

    # ---- GERCEK KOSUM ----------------------------------------------------
    # Drive yolunu drive_yolu cozer: bayatsa kendi duzeltir, mount yoksa uyarip None doner.
    # None'da DURUYORUZ — eskiden makedirs Drive yerine sahte yerel klasor yaratip "yedeklendi" diyordu.
    pruvo_drive = drive_yolu.pruvo_dizini(sessiz=gerekliyse)   # .../Pruvo
    if not pruvo_drive:
        print("Yedek ALINMADI — Drive yolu cozulemedi (yukaridaki uyariya bak).")
        return 1
    backup = os.path.join(pruvo_drive, YEDEK_KOK_ADI)

    # ---- KILIT: eszamanli iki kosum AYNI hedefe yazmasin -----------------
    # Kilit, --gerekliyse kararindan ONCE alinir: karar damgayi okur, damgayi da
    # kosan kosum yazar; kilitsiz okumak yarim/eski damgadan karar vermek olurdu.
    hal, kilit_fd, kilit_bilgi = kilit_al()
    if hal == "mesgul":
        sahip, yas, sahip_baslangici = kilit_bilgi
        kapsandi = atlama_kapsandi_mi(sahip_baslangici, en_yeni_kaynak_mtime(sirlar))
        print("yedek ATLANDI — baska bir yedek kosuyor (%s)." % sahip)
        print("  kilit: %s   (BEKLEMEDIK: push ASLA yavaslamaz/durmaz)" % kilit_yolu())
        if kapsandi:
            print("  kosan yedek bu kosumun isini kapsiyor (hicbir kaynak onun "
                  "baslangicindan sonra degismemis) — BITIRIRSE. Bitirmezse damgadaki "
                  "sahip baslangici cozulemez kalir ve pano UYARIR.")
        else:
            print("  ⚠️ kosan yedek bu degisiklikleri KAPSAMAYABILIR -> damgaya islendi; "
                  "pano '7) YEDEK TAZELIGI' uyaracak.")
        if yas is not None and yas > KILIT_UYARI_YASI:
            print("  ⚠️ kilit %.1f saattir tutuluyor — sahip surec ASILMIS olabilir "
                  "(cevapsiz Drive mount?). Kilidi KIRMIYORUZ (yasayan yazici veriyi "
                  "bozar); yedek bayatlarsa pano '7) YEDEK TAZELIGI' bunu gosterir."
                  % (yas / 3600.0))
        atlama_kaydet(backup, "baska yedek kosuyordu (%s)" % sahip, kapsandi=kapsandi,
                      sahip_baslangici=sahip_baslangici)
        return 0                     # FAIL-OPEN: pre-push bu koda BAKAR, 0 = push devam
    if hal == "kurulamadi":
        print("UYARI: %s — yedek KILITSIZ kosuyor (eszamanli kosum varsa yaris riski)."
              % kilit_bilgi, file=sys.stderr)

    # 🔴 K1: BASARI BAYRAGI. `finally` istisnada da kosar; iz `bitti=` yalniz
    # _yedekle() NORMAL donduyse ve cikis kodu 0 ise yazilir. Istisna ya da
    # sifir-olmayan kod -> `hata=` -> pano "⚠⚠ YARIM KALMIS YEDEK" der.
    basardi = False
    try:
        kod = _yedekle(backup, gerekliyse, sirlar, sir_temizle, dahil, haric,
                       kilitsiz=(hal == "kurulamadi"),
                       baslangic=kilit_bilgi if hal == "alindi" else None)
        basardi = (kod == 0)
        return kod
    finally:
        kilit_birak(kilit_fd, baslangic=kilit_bilgi if hal == "alindi" else None,
                    basardi=basardi)


def _yedekle(backup, gerekliyse, sirlar, sir_temizle, dahil, haric, kilitsiz=False,
             baslangic=None):
    """Asil kopyalama — DAIMA kilit altinda cagrilir (bkz. main).

    `baslangic` = KILIT ALIS ANI (kilit_al'in dondurdugu deger). Kilit dosyasindaki
    imzayla BIREBIR ayni sayi olmali: atlayan kosum "bekledigim sahip damgayi yazdi
    mi" sorusunu esitlikle cozuyor. Burada yeniden time.time() cagirmak, time.time()
    monoton olmadigi icin damgayi imzadan KUCUK yapabilirdi (olculdu: -0,0003 sn)."""
    if not isinstance(baslangic, (int, float)):
        baslangic = time.time()     # kilitsiz yol (kilit kurulamadi)

    # KAYNAK IMZASI kosum BASINDA olculur (bkz. damga_yaz gerekcesi): kopyalama
    # sirasinda degisen dosya imzaya GIRMEZ, bir sonraki kosumda YAKALANIR.
    bas_imza = kaynak_imzasi(sirlar)

    # UCUZ MOD (pre-push hook'u icin): son damgadan beri hicbir kaynak degismediyse
    # tek dosya bile kopyalama. Karar gerekli_mi()'de — fail-open (suphede yedekler).
    if gerekliyse:
        damga = damga_oku(backup)
        if not gerekli_mi(damga, None if bas_imza is None else bas_imza["mtime"],
                          imza=bas_imza):
            # OLCUMU KAYDET (bkz. damga_tazele): "degisiklik yok" bir olcumdur, damga
            # yazmaya hakki vardir; yoksa atlayan kardes kosumun uyarisi YAPISKAN kalir.
            tazelendi = damga_tazele(backup, baslangic, imza=bas_imza, kilitsiz=kilitsiz)
            print("yedek GUNCEL (son damga: %s) — degisiklik yok, kopyalanmadi.%s"
                  % (damga.get("iso", "?"),
                     "  (damga dogrulandi)" if tazelendi else ""))
            return 0

    os.makedirs(os.path.join(backup, "memory"), exist_ok=True)

    # memory klasoru
    if os.path.isdir(MEMORY):
        shutil.copytree(MEMORY, os.path.join(backup, "memory"), dirs_exist_ok=True,
                        copy_function=_drive_kopyala_karantinali)
        print("yedek: memory/ ->", os.path.join(backup, "memory"))

    # ~/.claude/skills/ — global skill'ler (merge-kapisi dahil) GIT DISINDA tutuluyor
    # (mimar karari 21 Tem: repoya tasinmayacak) -> TEK kopya bu makinede. Yedeklenmezse
    # disk kaybinda SKILL.md + dal-olc.py + kabul-test.py (davranissal batarya) topluca gider.
    # Artik copytree DEGIL dosya-dosya: her dosya sir nobetinden gecer (bkz. sir_sebebi).
    yazilan = 0
    if os.path.isdir(SKILLS):
        hedef = os.path.join(backup, "skills")
        yazilan, bayat = skills_yaz(SKILLS, hedef, dahil, haric, sir_temizle=sir_temizle)
        print("yedek: skills/ -> %s  (%d dosya)" % (hedef, yazilan))
        for g, sebep in haric:
            print("  SIR NOBETI — paket DISI: skills/%s  (%s)" % (g, sebep))
        for yol in bayat:
            if sir_temizle:
                print("  BAYAT SIR KOPYASI SILINDI: " + yol)
            else:
                print("  ⚠️ BAYAT SIR KOPYASI hedefte DURUYOR: " + yol
                      + "   (silmek icin: python3 tools/yedekle.py --sir-temizle)")
    else:
        print("NOT: %s yok -> skill yedegi ATLANDI." % SKILLS)

    # ~/.claude altindaki ELLE YAZILMIS agaclar. Hicbiri depoda YOK, surum gecmisi
    # YOK; hesap rotasyonunda KOSUM KAYDI zaten olur, metin de kaybolursa yordam
    # geri getirilemez. Her biri sir nobeti + ACIK ALLOWLIST'ten gecer — `cron`
    # agacinin ICINDE gercek jetonlar duruyor (bkz. AGAC_KAPSAMI gerekcesi).
    agac_sayilari = {}
    for agac in AGAC_KAPSAMI:
        etiket, kok, hedef_klasor, _izinli = agac
        a_dahil, a_haric, a_gurultu = agac_plani(agac)
        olan = yeni_a = 0
        if os.path.isdir(kok):
            a_hedef = os.path.join(backup, hedef_klasor)
            olan, yeni_a = agac_yaz(kok, a_hedef, a_dahil, etiket=etiket)
            print("yedek: %s/ -> %s  (%d dosya, %d yeni)"
                  % (hedef_klasor, a_hedef, olan, yeni_a))
            # 🔴 OLCULEBILIR DISLAMA: kac dosya, hangi sebeple yedek DISINDA kaldi.
            # Sessiz atlama yok — sayilmayan eleme, olculmemis eleme demektir.
            print("  %s DISLAMA: %d dosya yedege GIRMEDI (kaynak agac: %s)"
                  % (etiket.upper(), len(a_haric), kok))
            for g, sebep in a_haric:
                print("    DISLANDI: %s/%s   -> %s" % (hedef_klasor, g, sebep))
            print("  %s GURULTU (turetilmis): %d giris" % (etiket.upper(), len(a_gurultu)))
        else:
            print("NOT: %s yok -> %s yedegi ATLANDI." % (kok, etiket))
        agac_sayilari[etiket] = olan
        agac_sayilari[etiket + "_yeni"] = yeni_a
        agac_sayilari[etiket + "_haric"] = len(a_haric)

    # Sirsiz kaynak haritasi + ajan baglam dosyalari. HEPSI GITIGNORE'DA (repo public, icerik
    # ticari gizli) -> git'te KOPYASI YOK, yani bu makine olurse tamamen kaybolurlardi.
    # (CLAUDE.md kopyalanmaz: AGENTS.md'ye SYMLINK, ayri dosya degil — yon 30 Tem'de
    #  duzeltildi; eskiden burada tam TERSI yaziyordu ve gercek dosya yedeksiz kalmisti.)
    repo_adlari, kok_elenen = repo_kok_ayrimi()
    for ad in repo_adlari:
        _drive_kopyala_karantinali(os.path.join(ROOT, ad), os.path.join(backup, ad))
        print("yedek:", ad)

    # 🔴 SIR YAZMA YOLU KAPALI (8 Agu 2026, Okan karari) — SESSIZ ATLAMA YOK.
    # Elenen her kalem SAYIYLA ve ADIYLA basilir; ad sir DEGIL, icerik sirdir ve
    # icerik hicbir zaman okunmaz/yazilmaz/basilmaz.
    print("SIR ELEMESI: %d kalem yedege GIRMEDI (kanonik kume: REPO_SIR + SIR_ADLARI)"
          % len(kok_elenen))
    for ad, sebep in kok_elenen:
        print("  ELENDI (yedege GIRMEDI): %s   -> %s" % (ad, sebep))
    if kok_elenen:
        print("  (geri kazanim receteleri: SIR_KOKENI tablosu / %s)" % SIR_ENVANTER_ADI)

    # Yedek KOKUNDE onceki surumlerden kalmis sir kopyalari: --sir-temizle ile SILINIR,
    # bayraksiz kosumda YALNIZ UYARILIR (yedekten veri silmek elle onaylanir).
    kok_sir_sayilari = yedek_kok_sir_raporu(backup, sir_temizle=sir_temizle)

    # ---- EK KAPSAM: 5+1 evin izlenmeyen kalici bilgisi + diger hafiza uzaylari ----
    # Kum havuzunda (sahte ROOT) kardes ev YOKTUR -> faz kendini kapatir ve bunu BASAR.
    ek_sayilar = {}
    if ek_etkin_mi():
        print("EK KAPSAM:")
        ek_sayilar = ek_yaz(backup)
        print("  EK TOPLAM: %d dosya (%d yeni/degismis), %d sir-disi, %d kapsam-disi"
              % (ek_sayilar["ek_dosya"], ek_sayilar["ek_yeni"],
                 ek_sayilar["ek_haric"], ek_sayilar["ek_kapsam_disi"]))
    else:
        print("EK KAPSAM: KAPALI — bilinen kardes ev yok (kok: %s)" % ROOT)

    # TAZELIK DAMGASI — en sonda: yalniz kosum GERCEKTEN tamamlandiysa yazilir.
    # (Basta yazilsaydi yarida patlayan bir kosum "taze" gorunurdu = sahte guven.)
    eksik = repo_eksikleri()
    if eksik:
        print("⚠️ KISMI YEDEK — repo kokunde BULUNAMAYAN beklenen dosya(lar): %s"
              % ", ".join(eksik))
        print("   kok: %s   (damga 'tam: false' isaretlenecek, pano TAZE SAYMAYACAK)" % ROOT)
    sayilar = {"memory": len(_agac_dosyalari(MEMORY)),
               "skills": yazilan, "skills_haric": len(haric),
               "repo": len(repo_adlari), "kok_sir_elenen": len(kok_elenen)}
    sayilar.update(kok_sir_sayilari)
    sayilar.update(agac_sayilari)
    sayilar.update(ek_sayilar)
    damga_yaz(backup, sayilar, eksik=eksik,
              baslangic=baslangic, kilitsiz=kilitsiz, imza=bas_imza)

    # BEYAN HIZALAMASI (1 Agu 2026) — "PAYLASMA" uyarisi eskiden YALNIZ --sirlar
    # dalinda basiliyordu; VARSAYILAN kosumun paylasilabilir oldugu izlenimi veriyordu.
    # 31 Tem EK KAPSAM genislemesinden beri bu DOGRU DEGIL: varsayilan kosum da ticari
    # gizli icerik tasiyor (raporlar/ — icinde IBAN/VKN gecen tasinma envanteri —,
    # .tedarikci-fiyat/, .uyelik-parametreler.json, .uyelik-kodlar/). Sir nobeti AD
    # DESENINE gore eler, ICERIGE gore degil; bu metinler suzgecten gecer. Koruma
    # "yedege almamak"ta degil PAYLASMAMA kuralindadir -> uyari artik KOSULSUZ basilir.
    # Kapsam DARALTILMADI, hicbir dosya ad ile elenmedi.
    if _DRIVE_METADATA_REDDI:
        print("NOT: %d dosyada metadata (mtime/xattr) yazilamadi — icerik TAM kopyalandi. "
              "Hedef Ortak Drive saglayicisi metadata yazmayi reddediyor; tazelik DAMGADAN "
              "turer, mtime'dan DEGIL." % len(_DRIVE_METADATA_REDDI))
    print("🔴 BU YEDEK KLASORU KIMSEYLE PAYLASILMAZ (link/dosya/e-posta) — ticari gizli")
    print("   icerik tasir: raporlar/, .tedarikci-fiyat/, .uyelik-*. Sir nobeti ADA gore")
    print("   eler, ICERIGE gore degil.")
    # KARANTINA OZETI — atlama SESSIZ olamaz. Kosum tamamlandi (diger her dosya
    # yedeklendi) ama en az bir dosya korumaya takildi: cikis kodu KIRMIZI, cunku
    # "yedek alindi" beyani bu dosyalar icin DOGRU DEGIL. Kanonik yedekleri
    # DEGISMEDI — korunan hal budur.
    # BEYANLA GECEN DUSUSLER — beyan bir muafiyet degil bir KAYITTIR: her kullanim
    # adiyla, turuyle ve gerekcesiyle basilir. Basilmazsa beyan sessiz bir arka kapiya
    # doner ve korumanin anlami kalmaz.
    for uyari in _BEYAN_UYARISI:
        print("BEYAN UYARISI: %s" % uyari)
    if _BEYAN_KULLANILDI:
        print("DUSUS BEYANI KULLANILDI: %d dosya (kucultme ILAN EDILMISTI, yedek "
              "GUNCELLENDI)" % len(_BEYAN_KULLANILDI))
        for ad, tur, gerekce in _BEYAN_KULLANILDI:
            print("  BEYANLI: %s [%s] -> %s" % (ad, tur, gerekce))
    if _KORUMA_KARANTINA:
        print("KORUMA KARANTINASI: %d dosya ATLANDI (kanonik yedekleri DEGISMEDI); "
              "diger dosyalar yedeklendi." % len(_KORUMA_KARANTINA))
        for yol, sebep in _KORUMA_KARANTINA:
            print("  ATLANDI: %s   -> %s" % (os.path.basename(yol), sebep))
        print("bitti (karantinali) ->", backup)
        return 1
    print("bitti ->", backup)
    return 0


if __name__ == "__main__":
    sys.exit(main())
