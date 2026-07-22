#!/usr/bin/env python3
"""Kabul testi: mimar kapilari (Write/Edit/MultiEdit kilidi + Bash icra kapisi +
git commit kapisi + KABLO assertion).

Her vaka kancaya GERCEK PreToolUse JSON'unu stdin'den besler ve ciktidaki
permissionDecision'a bakar. "Bakildi iyi gorunuyor" kabul degildir.

20 Tem KALIBRASYONU:
  * Vaka tuple'i 6 alanli: (no, beklenen, arac, hedef, agent_id, aciklama).
    agent_id None ise payload'a ANAHTAR HIC KONMAZ (mimar cagrisi); dolu ise
    alt-ajan (ISCI) cagrisi taklit edilir.
  * FAIL-OPEN KORLUGU ONARILDI: eskiden "stdout bos => allow" sayiliyordu, yani
    kanca dosyasi silinse/coksede test YESIL yanardi. Artik kapi ALLOW yolunda
    stderr'e "MIMAR-KAPISI allow <kimlik>" izi basar; iz yoksa sonuc IZSIZ-ALLOW,
    dosya yoksa EKSIK-KANCA, returncode!=0 ise COKTU (hepsi KIRMIZI sayilir).
  * ATLANAN (kosulamayan) vaka sayisi ayrica raporlanir; >0 ise exit 1 — sessiz
    kirpma yasagi.

20 Tem ONARIMI — HERMETIKLIK (olculmus ariza: test yesili DAL DISI silinebilir bir
dizine asiliydi):
  * Kayitli-worktree vakalari (62/63/83/88) artik CANLI /private/tmp/pruvo-toka-jenerator
    kaydina bagli DEGIL — test kendi gecici worktree'sini kurar
    ('git worktree add --no-checkout --detach') ve sonunda kaldirir. Kuramazsa vakalar
    CEVRE-ATLANAN olarak RAPORLANIR (sessiz kirmizi YOK) ve ozet satirinda gorunur.
  * Kablo vakalari (110/111) CANLI .claude/settings.json yerine testin kendi kurdugu
    gecici kopyalar uzerinde kosar; 111 NEGATIF vakadir (eksik kanca 'yok' bildirilmeli)
    → "durum() daima var der" mutasyonu artik KIRMIZI yanar. Canli kablo durumu BILGI
    olarak basilir (teshis araci: python3 tools/kapi-envanteri.py).

IKI ATLAMA SINIFI (karistirma):
  * ATLANAN  = kapi kosmadi/coktu/izsiz (EKSIK-KANCA/COKTU/PARSE-HATASI/IZSIZ-ALLOW)
               → KIRMIZI sayilir, exit 1.
  * CEVRE-ATLANAN = cevre kurulamadi (or. gecici worktree acilamadi) → exit'i
               DEGISTIRMEZ ama sayisi ozette gorunur.

Kullanim:
    python3 tools/mimar-kilit-test.py                # repodaki kancalari test eder
    python3 tools/mimar-kilit-test.py /baska/tools   # izole kopyayi (mutasyon) test eder

Cikis kodu 0 = hepsi gecti, 1 = en az bir vaka basarisiz ya da atlandi.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(
    os.path.abspath(__file__))

KILIT = os.path.join(TOOLS, "mimar-kod-kilidi.py")
ICRA = os.path.join(TOOLS, "mimar-icra-kapisi.py")
COMMIT = os.path.join(TOOLS, "mimar-commit-kapisi.py")
KUR = os.path.join(TOOLS, "mimar-kapi-kur.py")

SCRATCH = "/private/tmp/claude-501/-Users-okan-dev-pruvo/2e8fe6f5-3e87-4e14-bc4d-d1447c25ea61/scratchpad"
REPO = "/Users/okan/dev/pruvo"
HAFIZA = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory"

# Canli olculmus bir alt-ajan agent_id'si bicimi (T0 olcumu, 20 Tem).
ISCI_ID = "a4482c781a922b6a1"

# Git'e KAYITLI, repo DISINDAKI mesru worktree. ARTIK SABIT DEGIL: test kendi gecici
# worktree'sini kurar ve bu isareti onun yoluyla degistirir (hermetiklik).
KAYITLI_WT = "<<KAYITLI_WT>>"
KAYITLI_WT_YOL = None  # main() icinde doldurulur; None ise vakalar CEVRE-ATLANAN

# Kosulamayan/karar uretmeyen sonuclar — "allow" diye YUTULMAZ.
ATLANAN_ISARETLER = ("EKSIK-KANCA", "COKTU", "PARSE-HATASI", "IZSIZ-ALLOW")

# (no, beklenen, arac, hedef, agent_id, aciklama)
VAKALAR = [
    (1, "deny", "Write", SCRATCH + "/analiz.py", None,
     "YENI: scratchpad'e betik yazarligi"),
    (2, "deny", "Write", REPO + "/tools/yeni.py", None,
     "regresyon: repo icine .py"),
    (3, "deny", "Write", REPO + "/urunler.json", None,
     "regresyon: urun verisi"),
    (4, "deny", "Write", REPO + "/tools/mimar-kod-kilidi.py", None,
     "kendini koruma (kilit)"),
    (5, "deny", "Write", REPO + "/tools/mimar-icra-kapisi.py", None,
     "kendini koruma (icra kapisi)"),
    (6, "deny", "Bash", "python3 " + SCRATCH + "/analiz.py", None,
     "YENI: kendi betigini kosturma"),
    (7, "allow", "Write", REPO + "/DEVAM.md", None,
     ".md her yerde serbest"),
    (8, "allow", "Write", SCRATCH + "/commit-msg.txt", None,
     "scratchpad veri/not dosyasi"),
    (9, "allow", "Write", HAFIZA + "/yeni-ders.md", None,
     "hafiza .md"),
    (10, "allow", "Write", REPO + "/.claude/worktrees/agent-x/tools/hepsi.py", None,
     "worktree muaf (muhendis alani)"),
    (11, "deny", "Bash", "node " + REPO + "/tools/parite-test.js", None,
     "22Tem: parite (node araci) = ISCI isi"),
    (12, "allow", "Bash", "python3 " + REPO + "/tools/d1-sync.py --durum", None,
     "mevcut repo araci (D1 durum)"),
    (13, "allow", "Bash", "git -C " + REPO + " status -sb", None,
     "git durum"),
    (14, "allow", "Bash", "git -C " + REPO + " merge filan-dal", None,
     "MERGE = mimarin kapisi"),
    (15, "deny", "Bash", "curl -s https://pruvo3d.com/", None,
     "22Tem: curl (canli dogrulama) = ISCI isi"),
]

# Spec disi ama porozite kapatan ek vakalar (raporda ayri bolum).
EK_VAKALAR = [
    (16, "deny", "Bash", "python3 -c \"import json;print(1)\"", None,
     "satir-ici kod (betik yazmadan icra)"),
    (17, "deny", "Bash", "cat " + SCRATCH + "/x.py | python3", None,
     "stdin'den kod okutma"),
    (18, "deny", "Bash", "bash -lc \"ls -la\"", None,
     "kabuk satir-ici kod"),
    (19, "deny", "Write", SCRATCH + "/analiz.sh", None,
     "scratchpad'e kabuk betigi"),
    (20, "deny", "Bash", SCRATCH + "/analiz.sh", None,
     "repo disi betigi dogrudan cagirma"),
    (21, "deny", "Bash", "node --check " + REPO + "/secenekler.js", None,
     "22Tem: node --check = ISCI isi"),
    (22, "allow", "Bash", "python3 " + REPO + "/tools/durum.py", None,
     "durum panosu"),
    (23, "allow", "Bash", "git -C " + REPO + " worktree list", None,
     "worktree yonetimi"),
    (24, "allow", "Bash", "grep -rn WHATSAPP " + REPO + "/index.html", None,
     "arama/okuma"),
    (25, "deny", "Bash", "codex exec \"specteki isi yap\"", None,
     "22Tem: Codex'i ISCI cagirir (mimar spec yazar)"),
    (26, "allow", "Write", REPO + "/tools/paket-yeni-is.md", None,
     "muhendislik paketi (spec)"),
    (27, "deny", "Bash", "python3 " + REPO + "/tools/parite-ege.js", None,
     "22Tem: parite-ege (python arac) = ISCI isi"),
]

# Devir mektubu §4 MERGE PROSEDURU + §7 acik isler. 22 TEM AYRIMI: GIT-ISI (fetch,
# merge-base, diff, merge-tree, push, worktree remove, branch -D) + gh + durum.py mimarin
# ELINDE KALIR (git makine reddine sokulmaz). Ama §4.7 CANLI DOGRULAMA (curl) ve §7 TEST
# KOSUMU (parite/filament/gitignore-kapisi/olculmemis) ARTIK ISCININ ISI -> mimar bu adimlari
# DELEGE eder (37/39/40/41/42 = deny). Merge prosedurunun "olcum" adimlari worktree worker'a.
MERGE_VAKALARI = [
    (31, "allow", "Bash", "git -C " + REPO + " fetch origin", None, "§4.1 fetch"),
    (32, "allow", "Bash", "git -C " + REPO + " merge-base main worktree-dal", None, "§4.2 kapsam"),
    (33, "allow", "Bash", "git -C " + REPO + " diff --stat abc123 HEAD", None, "§4.2 diff"),
    (34, "allow", "Bash", "git -C " + REPO + " merge-tree --write-tree --name-only main dal", None,
     "§4.3 cakisma denetimi"),
    (35, "allow", "Bash", "git -C " + REPO + " push origin main", None, "§4.6 push"),
    (36, "allow", "Bash", "gh run list --limit 1", None, "§4.7 deploy durumu (gh serbest)"),
    (37, "deny", "Bash", "curl -sI https://pruvo3d.com/", None,
     "22Tem: §4.7 canonical URL DOGRULAMA = ISCI isi"),
    (38, "allow", "Bash",
     "git -C " + REPO + " worktree remove --force " + REPO + "/.claude/worktrees/agent-x", None,
     "§4.8 temizlik"),
    (39, "deny", "Bash", "python3 tools/gitignore-kapisi.py --yaz", None,
     "22Tem: §7.1 arac kosumu = ISCI isi"),
    (40, "deny", "Bash", "python3 " + REPO + "/tools/filament-test.py", None,
     "22Tem: §7.2 test kosumu = ISCI isi"),
    (41, "deny", "Bash", "python3 " + REPO + "/tools/olculmemis-siparis.py", None,
     "22Tem: §7.4 arac kosumu = ISCI isi"),
    (42, "deny", "Bash", "node " + REPO + "/tools/parite-ege.js", None,
     "22Tem: arama paritesi (Ege) = ISCI isi"),
    (43, "allow", "Bash", "python3 tools/durum.py", None, "§2 durum panosu (goreli yol) — SERBEST 2'den biri"),
    (44, "allow", "Bash", "git -C " + REPO + " branch -D worktree-dal", None, "§4.8 dal silme"),
]

# MUHENDIS AKISI — OTURUM muafiyeti YOK (cwd kaydirilabilir sinyaldi, kaldirildi).
# Mimarin serbestligi YOL-tabanli: betigini worktree'ye yazar ve oradan kosturur.
# 30 ve 45 BILEREK deny KALIR: bunlar MIMAR kimligiyle (agent_id YOK) kosar.
# ISCI ikizleri asagida (60/61) — vaka SILINMEDI, kimlik ekseniyle IKIYE BOLUNDU.
WORKTREE = REPO + "/.claude/worktrees/agent-x"
MUHENDIS_VAKALARI = [
    (28, "allow", "Write", WORKTREE + "/tools/analiz.py", None,
     "muhendis betigini WORKTREE'sine yazar (Write=kod-kilidi, worktree muaf)"),
    (29, "deny", "Bash", "python3 " + WORKTREE + "/tools/analiz.py", None,
     "22Tem: MIMAR worktree python betigini bile KOSTURMAZ (isci/agent_id kosar)"),
    (30, "deny", "Write", SCRATCH + "/analiz.py", None,
     "MIMAR: worktree cwd'si MUAFIYET VERMEZ"),
    (45, "deny", "Bash", "python3 " + SCRATCH + "/analiz.py", None,
     "MIMAR: worktree cwd'si MUAFIYET VERMEZ"),
]

# Mimar sorusu (b) + enjeksiyon yuzeyleri.
MODUL_VAKALARI = [
    (46, "deny", "Bash", "python3 -m pip install requests", None,
     "-m pip: kurulum betigi kosturur"),
    (47, "deny", "Bash", "python3 -m timeit -s \"import os\" \"pass\"", None,
     "-m timeit -s: keyfi kod"),
    (48, "deny", "Bash", "python3 -m http.server 8000", None,
     "-m http.server: disari acar"),
    (49, "deny", "Bash", "python3 -m pdb " + REPO + "/tools/durum.py", None,
     "-m pdb: etkilesimli keyfi icra"),
    (50, "deny", "Bash", "python3 -m json.tool " + REPO + "/tools/taban-fiyatlar.js", None,
     "22Tem: -m (json.tool dahil) allowlist disi = RED"),
    (51, "deny", "Bash",
     "node --require=" + SCRATCH + "/kanca.js " + REPO + "/tools/parite-test.js", None,
     "bayraga gomulu repo-disi betik"),
    (52, "deny", "Bash",
     "PYTHONPATH=" + SCRATCH + " python3 " + REPO + "/tools/d1-sync.py --durum", None,
     "PYTHONPATH ile kod enjeksiyonu"),
    (53, "deny", "Bash",
     "NODE_OPTIONS=--require=" + SCRATCH + "/k.js node " + REPO + "/tools/parite-test.js", None,
     "NODE_OPTIONS ile kod enjeksiyonu"),
    (54, "allow", "Bash", "PRUVO_URUN_AI_IZNI=1 python3 tools/durum.py", None,
     "zararsiz env atamasi ENGELLENMEZ (allowlist komutu + zararsiz env)"),
]

# ISCI IKIZLERI — mesru muhendisin YAPABILMESI gerekenler (yanlis-pozitif nobetcisi).
# Olculmus ariza: kapi bunlarin hepsini blokluyordu; bir isci sed'e kacti.
ISCI_VAKALARI = [
    (60, "allow", "Write", SCRATCH + "/analiz.py", ISCI_ID,
     "P1 ikizi (vaka 1/30): scratchpad betigi"),
    (61, "allow", "Bash", "python3 " + SCRATCH + "/analiz.py", ISCI_ID,
     "P1 ikizi (vaka 6/45): betigi kosturma"),
    (62, "allow", "Write", KAYITLI_WT + "/tools/toka-olc.py", ISCI_ID,
     "P2: repo-disi kayitli worktree'ye yazma"),
    (63, "allow", "Bash", "python3 " + KAYITLI_WT + "/tools/toka-olc.py", ISCI_ID,
     "P2: repo-disi kayitli worktree betigi"),
    (64, "allow", "Write", REPO + "/index.html", ISCI_ID,
     "isci site kodunu yazabilir"),
    (65, "allow", "Write", REPO + "/urunler.json", ISCI_ID,
     "korumasi urunler-guard'da, kod-kilidinde degil"),
    (66, "allow", "Bash", "python3 -c \"print(1)\"", ISCI_ID,
     "isci satir-ici kod kosturabilir"),
    (67, "allow", "Bash", "python3 -m pytest /private/tmp/x", ISCI_ID,
     "isci -m ile repo disina cikabilir"),
    (68, "deny", "Write", REPO + "/.claude/settings.json", ISCI_ID,
     "CEKIRDEK: kablo (kimlikten bagimsiz)"),
    (69, "deny", "Write", REPO + "/tools/mimar-icra-kapisi.py", ISCI_ID,
     "CEKIRDEK: kapi (kimlikten bagimsiz)"),
    (70, "deny", "Write", REPO + "/tools/mimar-commit-kapisi.py", ISCI_ID,
     "CEKIRDEK: commit kapisi"),
    (71, "deny", "Write", REPO + "/tools/mimar-kilit-test.py", ISCI_ID,
     "CEKIRDEK: kabul testi"),
    (72, "allow", "Write", REPO + "/.claude/worktrees/wf-x/tools/mimar-icra-kapisi.py", ISCI_ID,
     "CEKIRDEK yanlis-pozitif URETMEZ (worktree kopyasi)"),
    (73, "allow", "Write", REPO + "/tools/yeni-arac.py", ISCI_ID,
     "isci ana repoda arac uretebilir"),
    (74, "allow", "Edit", REPO + "/index.html", ISCI_ID,
     "Edit araci da kancaya bagli"),
    (75, "allow", "MultiEdit", REPO + "/index.html", ISCI_ID,
     "MultiEdit araci da kancaya bagli"),
    # CEKIRDEK GENISLETMESI (20 Tem): kapiyi YALANCI yapabilen NOBETCILER + canli kablo.
    (76, "deny", "Write", REPO + "/tools/mimar-kapi-mutasyon-test.py", ISCI_ID,
     "CEKIRDEK: mutasyon takimi (nobetci)"),
    (77, "deny", "Write", REPO + "/tools/mimar-commit-kapisi-test.py", ISCI_ID,
     "CEKIRDEK: commit kapisi kabul testi"),
    (78, "deny", "Write", REPO + "/tools/urunler-guard.py", ISCI_ID,
     "CEKIRDEK: veri duzlemi nobetcisi"),
    (79, "deny", "Write", REPO + "/.git/hooks/pre-commit", ISCI_ID,
     "CEKIRDEK: canli commit kablosu"),
    (96, "deny", "Write", REPO + "/tools/kapi-envanteri.py", ISCI_ID,
     "CEKIRDEK: kapi envanteri (teshis)"),
    (97, "allow", "Write", REPO + "/.claude/worktrees/wf-x/tools/urunler-guard.py", ISCI_ID,
     "genisletme yanlis-pozitif URETMEZ (worktree kopyasi)"),
    (98, "allow", "Write", REPO + "/tools/duzelt.py", ISCI_ID,
     "komsu arac CEKIRDEK'e girmedi (asiri genisleme nobetcisi)"),
    # B8 (20 Tem): CANLI PreToolUse/Bash zincirindeki iki nobetci. Ikisi de
    # .claude/settings.json'da kayitli ve kosuyor; CEKIRDEK'te olmadiklari icin tek
    # Write ile susturulabiliyorlardi.
    (140, "deny", "Write", REPO + "/tools/urunler-guard-hook.py", ISCI_ID,
     "CEKIRDEK: canli Bash zinciri (veri guard kancasi)"),
    (141, "deny", "Write", REPO + "/tools/komut-stili-kapisi.py", ISCI_ID,
     "CEKIRDEK: canli Bash zinciri (komut stili)"),
    (142, "allow", "Write", REPO + "/.claude/worktrees/wf-x/tools/urunler-guard-hook.py",
     ISCI_ID, "B8 yanlis-pozitif URETMEZ (worktree kopyasi serbest)"),
    (143, "allow", "Write", REPO + "/.claude/worktrees/wf-x/tools/komut-stili-kapisi.py",
     ISCI_ID, "B8 yanlis-pozitif URETMEZ (worktree kopyasi serbest)"),
    # 4. TUR: sertlestirmenin bedeli YALNIZ mimara ait olmali — isci HICBIR yeni
    # vakada bloklanmamali (bu ikizler olmadan sertlestirme isciyi felc edebilirdi).
    (144, "allow", "Bash", "python3 -W ignore -m pip install requests", ISCI_ID,
     "isci ikizi (130): -W + -m serbest"),
    (145, "allow", "Bash", "python3 -m unittest discover -vs/private/tmp/disari", ISCI_ID,
     "isci ikizi (135): birlesik bayrak + repo disi hedef"),
    (146, "allow", "Bash", "python3 tools/durum.py -s/private/tmp/disari", ISCI_ID,
     "isci ikizi (150): repo-disi yol argumani"),
    (147, "allow", "Bash", "python3 -m pytest " + REPO + "/tools", ISCI_ID,
     "isci ikizi (85): -m pytest serbest"),
    # 22 TEM IKIZLERI: sertlestirmenin bedeli YALNIZ mimara — isci HICBIR yeni redde
    # takilmamali (olcum/curl/codex/python-arac/pipe hepsi ISCI icin serbest kalir).
    (300, "allow", "Bash", "du -sh /", ISCI_ID, "22Tem ikizi (200): olcum du serbest"),
    (301, "allow", "Bash", "ps aux", ISCI_ID, "22Tem ikizi (201): ps serbest"),
    (302, "allow", "Bash", "find /tmp -name x", ISCI_ID, "22Tem ikizi (202): find serbest"),
    (303, "allow", "Bash", "curl -s https://example.org", ISCI_ID,
     "22Tem ikizi (220): curl serbest"),
    (304, "allow", "Bash", "codex exec \"x\"", ISCI_ID, "22Tem ikizi (230): codex serbest"),
    (305, "allow", "Bash", "python3 " + REPO + "/tools/build.py", ISCI_ID,
     "22Tem ikizi (240): python arac serbest"),
    (306, "allow", "Bash", "git log | head -5", ISCI_ID,
     "22Tem ikizi (216): pipe olcum serbest"),
    (307, "allow", "Bash", "node --check tools/x.js", ISCI_ID,
     "22Tem ikizi (138): node serbest"),
]

# MIMAR TARAFI YENI VAKALAR (agent_id YOK) — onek/kayit duzeltmesi + test modulleri.
MIMAR_YENI_VAKALARI = [
    (80, "deny", "Write", REPO + "/tools/.claude/worktrees/kotu.py", None,
     "SAHTE worktree (alt-dize deligi kapandi)"),
    (81, "deny", "Write", "/private/tmp/x/.claude/worktrees/kotu.py", None,
     "SAHTE worktree, repo-disi varyant"),
    (82, "allow", "Write", REPO + "/.claude/worktrees/agent-x/tools/x.py", None,
     "regresyon: ONEK muafiyeti yasiyor"),
    (83, "allow", "Write", KAYITLI_WT + "/tools/toka-olc.py", None,
     "KAYITLI worktree (kimlikten bagimsiz yedek)"),
    (84, "deny", "Write", "/private/tmp/pruvo-toka-BASKA/tools/x.py", None,
     "negatif esik: kayitli DEGIL"),
    # 4. TUR TASARIM DEGISIKLIGI (20 Tem): '-m' HER BICIMDE kapali (beyaz liste haric).
    # 85/86/93/95/121/123/125 eskiden ALLOW idi; ayristirma kaldirildigi icin artik DENY.
    (85, "deny", "Bash", "python3 -m pytest " + REPO + "/tools", None,
     "-m pytest repo-ici DE kapandi (ayristirma yok)"),
    (86, "deny", "Bash", "python3 -m unittest discover -s " + REPO + "/tools", None,
     "-m unittest repo-ici DE kapandi"),
    (87, "deny", "Bash", "python3 -m pytest /private/tmp/x", None,
     "-m ile repo DISINA cikilamaz"),
    (88, "allow", "Bash", "bash " + KAYITLI_WT + "/tools/toka-olc.sh", None,
     "KAYITLI worktree SH betigi icra (kimlikten bagimsiz yedek; M4 nobetcisi)"),
    (254, "deny", "Bash", "python3 " + KAYITLI_WT + "/tools/toka-olc.py", None,
     "22Tem: MIMAR kayitli-worktree PYTHON betigini de KOSTURMAZ (allowlist disi)"),
    (89, "deny", "Edit", REPO + "/index.html", None,
     "Edit araci: mimar site kodunu duzenleyemez"),
    (90, "deny", "MultiEdit", REPO + "/index.html", None,
     "MultiEdit araci: ayni kural"),
    (91, "deny", "Write", REPO + "/.claude/settings.json", None,
     "CEKIRDEK, mimar tarafi"),
    # BITISIK-DEGERLI BAYRAK (20 Tem olcumu: '-s/yol' allow idi, '-s /yol' deny idi).
    (92, "deny", "Bash", "python3 -m unittest discover -s/private/tmp/disari", None,
     "BITISIK bayrakla repo DISINA cikilamaz"),
    (93, "deny", "Bash", "python3 -m unittest discover -s" + REPO + "/tools", None,
     "BITISIK bayrak repo-ici: -m yuzunden DENY"),
    (94, "deny", "Bash", "python3 -m pytest --rootdir=/private/tmp/disari", None,
     "--bayrak=DEGER ile repo DISINA cikilamaz"),
    (95, "deny", "Bash", "python3 -m pytest --rootdir=" + REPO + "/tools", None,
     "--bayrak=DEGER repo-ici: -m yuzunden DENY"),
    # R2 (20 Tem REGRESYON): '-s=/dis/yol' bitisik-ESITLIKLI form. Deger '=/dis/yol'
    # olarak okunuyor, basindaki '=' yuzunden goreli sayilip cwd'ye ekleniyor ve
    # REPO-ICI kabul ediliyordu → repo disinda GERCEK icra kaniti uretildi.
    # RED tarafi ve KABUL tarafi birlikte olculur (yanlis pozitif uretmemeli).
    (120, "deny", "Bash", "python3 -m unittest discover -s=/private/tmp/disari", None,
     "R2: '-s=/dis/yol' bitisik-esitlikli form DENY"),
    (121, "deny", "Bash", "python3 -m unittest discover -s=" + REPO + "/tools", None,
     "'-s=repo-ici' de -m yuzunden DENY (4. tur)"),
    (122, "deny", "Bash", "python3 -m unittest discover -s /private/tmp/disari", None,
     "R2: ayrik '-s /dis/yol' DENY"),
    (123, "deny", "Bash", "python3 -m unittest discover -s " + REPO + "/tools", None,
     "ayrik '-s repo-ici' de -m yuzunden DENY (4. tur)"),
    (124, "deny", "Bash",
     "python3 -m unittest discover --start-directory=/private/tmp/disari", None,
     "R2: '--start-directory=/dis/yol' DENY"),
    (125, "deny", "Bash",
     "python3 -m unittest discover --start-directory=" + REPO + "/tools", None,
     "'--start-directory=repo-ici' de -m yuzunden DENY"),
    # R2 ikinci ayak: BITISIK '-mMODUL' tum -m denetimini atliyordu.
    (126, "deny", "Bash", "python3 -mtimeit -s \"import os\" \"pass\"", None,
     "R2: '-mtimeit' bitisik modul formu DENY"),
    (127, "deny", "Bash", "python3 -mpip install requests", None,
     "R2: '-mpip' bitisik modul formu DENY"),
    (128, "deny", "Bash", "python3 -mjson.tool " + REPO + "/tools/taban-fiyatlar.js", None,
     "22Tem: '-mjson.tool' de allowlist disi = RED"),
    (129, "deny", "Bash", "python3 " + REPO + "/tools/durum.py -smth", None,
     "22Tem: durum.py + EKSTRA argüman = RED (allowlist tam esitlik)"),
    # --- 4. TUR (20 Tem): YORUMLAYICI ARGUMANI AYRISTIRMA DELIKLERI ---
    # Bagimsiz curutucu GERCEK ICRA ile olctu: asagidaki formlarda repo DISINDA dosya
    # yazildi (dal ALLOW / main DENY). Kok neden: DEGER ALAN kisa bayrak (-W/-X/-Q)
    # degerini AYRI token alir, eski tarama o tiresiz token'da 'break' ediyordu.
    (130, "deny", "Bash", "python3 -W ignore -m pip install requests", None,
     "A: '-W ignore' -m denetimini atlatamaz"),
    (131, "deny", "Bash", "python3 -W ignore::DeprecationWarning -m pip install x", None,
     "A: ':'li -W degeri de atlatamaz"),
    (132, "deny", "Bash", "python3 -X importtime -m pip list", None,
     "A: '-X importtime' -m denetimini atlatamaz"),
    (133, "deny", "Bash", "python3 -X utf8 -m http.server 8000", None,
     "A: '-X utf8' + http.server (disari acma)"),
    (134, "deny", "Bash", "python3 -W ignore -m pytest /private/tmp/disari", None,
     "A: -W kalkani + repo DISI test hedefi"),
    (135, "deny", "Bash", "python3 -m unittest discover -vs/private/tmp/disari", None,
     "B: BIRLESIK kisa bayrak '-vs/yol'"),
    (136, "deny", "Bash", "python3 -m unittest discover -vvs/private/tmp/disari", None,
     "B: '-vvs/yol' (iki harf + deger)"),
    # YANLIS-POZITIF NOBETCILERI (mimarin MESRU isi acik kalmali)
    (137, "deny", "Bash", "python3 --version", None,
     "22Tem: python3 --version bile allowlist disi = RED (yalniz 2 komut)"),
    (138, "deny", "Bash", "node --check tools/x.js", None,
     "22Tem: node --check = RED (node'da izinli komut yok)"),
    (139, "allow", "Bash", "grep -rn \"x\" tools/", None,
     "grep yorumlayici degil ALLOW"),
    # R2 NOBETCILERI: '-m' OLMADAN, yalniz YOL ekseni (mutasyon ayirt edebilsin).
    (150, "deny", "Bash", "python3 tools/durum.py -s/private/tmp/disari", None,
     "R2: bayraga BITISIK repo-disi yol (m yok)"),
    (151, "deny", "Bash", "python3 tools/durum.py --cikti=/private/tmp/disari/x.txt", None,
     "R2: '=' sonrasi repo-disi yol (m yok)"),
    (152, "deny", "Bash", "python3 tools/durum.py --cikti=" + REPO + "/tools/x.txt", None,
     "22Tem: durum.py + '--cikti=' EKSTRA argüman = RED (repo-ici olsa da)"),
    (153, "deny", "Bash", "node tools/parite-test.js /private/tmp/disari", None,
     "R2: tiresiz ARGUMAN olarak repo-disi yol"),
]

# CWD REPO DISINDA: '/' ICERMEYEN goreli betik adi R2'ye takilmaz — F adiminin
# (betik repo_ici) KALAN isi budur. Bu kume M18 mutasyonunun nobetcisidir.
DIS_CWD = "/private/tmp/disari"
DIS_CWD_VAKALARI = [
    (160, "deny", "Bash", "python3 analiz.py", None,
     "cwd repo DISI + goreli betik adi -> DENY (allowlist)"),
    (161, "allow", "Bash", "python3 " + REPO + "/tools/durum.py", None,
     "cwd disarida olsa da repo-ici durum.py ALLOW"),
    # M18 NOBETCISI (sh): F (betik repo_ici) sadece sh/bash icin canli. bash betigi
    # cwd repo DISINDA + '/' ICERMEYEN ad -> dis_yol takilmaz, YALNIZ F yakalar.
    (250, "deny", "Bash", "bash x.sh", None,
     "sh: cwd repo DISI + repo-disi betik -> F yakalar (M18 nobetcisi)"),
]

# === 22 TEM SERTLESTIRME VAKALARI (MIMAR kimligi, cwd=REPO) ===
# Okan 22 Tem: "mimar HICBIR is yapmaz" — hafif olcum sinifi kapatildi. Her rulun kendi
# nobetcisi (ME1..ME5 mutasyonlari bunlari kirmizi yakar).
MIMAR_22TEM_VAKALARI = [
    # (1) OLCUM / dosya-tarama — 16 komut + pipe-gomulu vaka
    (200, "deny", "Bash", "du -sh /", None, "olcum: du"),
    (201, "deny", "Bash", "ps aux", None, "olcum: ps"),
    (202, "deny", "Bash", "find /tmp -name x", None, "olcum: find"),
    (203, "deny", "Bash", "wc -l index.html", None, "olcum: wc"),
    (204, "deny", "Bash", "head -5 DEVAM.md", None, "olcum: head"),
    (205, "deny", "Bash", "tail -5 DEVAM.md", None, "olcum: tail"),
    (206, "deny", "Bash", "sed -n 1p index.html", None, "olcum: sed"),
    (207, "deny", "Bash", "awk '{print}' index.html", None, "olcum: awk"),
    (208, "deny", "Bash", "sort urunler.json", None, "olcum: sort"),
    (209, "deny", "Bash", "stat index.html", None, "olcum: stat"),
    (210, "deny", "Bash", "file index.html", None, "olcum: file"),
    (211, "deny", "Bash", "df -h", None, "olcum: df"),
    (212, "deny", "Bash", "vm_stat", None, "olcum: vm_stat"),
    (213, "deny", "Bash", "sysctl -a", None, "olcum: sysctl"),
    (214, "deny", "Bash", "top -l 1", None, "olcum: top"),
    (215, "deny", "Bash", "memory_pressure", None, "olcum: memory_pressure"),
    (216, "deny", "Bash", "git log | head -5", None, "PIPE: olcum segmenti (head) RED"),
    # (2) curl / wget
    (220, "deny", "Bash", "curl -s https://example.org", None, "canli dogrulama: curl"),
    (221, "deny", "Bash", "wget https://example.org", None, "canli dogrulama: wget"),
    # (3) codex (her bicim)
    (230, "deny", "Bash", "codex exec \"x\"", None, "codex basename"),
    (231, "deny", "Bash",
     "/Applications/ChatGPT.app/Contents/Resources/codex exec \"x\"", None,
     "codex tam yol (ChatGPT.app)"),
    # (4) python/node ALLOWLIST
    (240, "deny", "Bash", "python3 " + REPO + "/tools/build.py", None,
     "python repo-ici arac (allowlist disi) = RED"),
    (241, "deny", "Bash", "python3 tools/durum.py --ekstra-bayrak", None,
     "durum.py + EKSTRA argüman = RED (ME5 nobetcisi)"),
    (244, "deny", "Bash", "node tools/parite-test.js", None,
     "node: allowlist'te komut YOK = RED"),
    (242, "allow", "Bash", "python3 tools/durum.py", None,
     "durum.py (repo-goreli, argümansiz) ALLOW"),
    (243, "allow", "Bash", "python3 tools/d1-sync.py --durum", None,
     "d1-sync.py --durum (repo-goreli) ALLOW"),
    # (5) sh/bash NOBETCILERI — dis_yol (M13/M20) hala sh icin canli
    (251, "deny", "Bash", "bash tools/x.sh -s/private/tmp/disari", None,
     "sh: bitisik bayrakla repo-disi yol -> dis_yol (M13 nobetcisi)"),
    (253, "deny", "Bash", "bash tools/x.sh /private/tmp/disari", None,
     "sh: tiresiz repo-disi yol argumani -> dis_yol (M20 nobetcisi)"),
]

# COMMIT KAPISI — kanca degil, dogrudan betik cagrisi.
# (no, beklenen_exit, stdin, ek_env, gitdir_hazirlik, aciklama)
COMMIT_VAKALARI = [
    (100, 1, "urunler.json\ntools/build.py", {}, None, "temel red (kaynak/veri staged)"),
    (101, 0, "urunler.json", {"PRUVO_MIMAR_ONAY": "worker"}, None,
     "escape hatch VERI duzlemi: gecer AMA gurultulu + loglu"),
    (102, 1, "tools/x.PY", {}, None, "buyuk harf uzanti deligi (lower())"),
    (103, 0, "DEVAM.md", {}, "MERGE_HEAD", "sequencer istisnasi: gurultulu + loglu"),
    (104, 1, "index.html", {}, None, "istisnanin esigi: MERGE_HEAD yok"),
    # R1 (20 Tem REGRESYON): sequencer istisnasi main()'in basinda, korunan-dosya
    # kontrolunun ONUNDE ve kosulsuz 'return 0' idi → sahte .git/MERGE_HEAD yazan biri
    # index.html/tools/*.py commit'ini de aciyordu (main'de ayni vaka exit 1 idi).
    (109, 1, "index.html", {}, "MERGE_HEAD",
     "R1: sequencer istisnasi KORUNAN kaynagi ACMAZ"),
    (112, 1, "urunler.json", {}, "MERGE_HEAD",
     "R1: sequencer istisnasi KORUNAN veriyi ACMAZ"),
    (113, 1, "tools/x.py", {}, "CHERRY_PICK_HEAD",
     "R1: cherry-pick de kaynagi ACMAZ"),
    (105, 0, "DEVAM.md", {}, None, ".md serbest"),
    (106, 0, "urunler.json", {}, None, "kapsam disi toplevel (baska repo)"),
    (107, 1, "urunler.json\ntools/build.py", {"PRUVO_MIMAR_ONAY": "worker"}, None,
     "DARALTMA: worker onayi KAYNAGI acmaz (main kazanir)"),
    (108, 1, "tools/build.py", {"PRUVO_MIMAR_ONAY": "worker"}, None,
     "DARALTMA: yalniz kaynak + worker -> KAPALI"),
]

# no -> (stderr'de beklenen gurultu parcasi, log'da beklenen karar anahtari)
BYPASS_MUHASEBESI = {
    101: ("ESCAPE HATCH KULLANILDI", "allow-escape"),
    103: ("SEQUENCER ISTISNASI", "allow-sequencer"),
}


def kancayi_kostur(arac, hedef, cwd=REPO, agent_id=None):
    """PreToolUse kancasini gercek payload'la kosturur.
    Doner: (karar, gerekce_ozeti). Karar: allow/deny/EKSIK-KANCA/COKTU/
    PARSE-HATASI/IZSIZ-ALLOW."""
    if arac == "Bash":
        kanca = ICRA
        tool_input = {"command": hedef}
    else:  # Write | Edit | MultiEdit
        kanca = KILIT
        tool_input = {"file_path": hedef, "content": "x"}

    if not os.path.exists(kanca):
        return "EKSIK-KANCA", kanca

    payload = {
        "session_id": "test",
        "cwd": cwd,
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": arac,
        "tool_input": tool_input,
    }
    # agent_id YALNIZCA verildiginde konur — mimar payload'unda ANAHTAR HIC YOKTUR.
    if agent_id is not None:
        payload["agent_id"] = agent_id

    ortam = dict(os.environ)
    ortam.pop("CLAUDE_PROJECT_DIR", None)
    sonuc = subprocess.run(
        [sys.executable, kanca],
        input=json.dumps(payload),
        capture_output=True, text=True, env=ortam,
    )
    if sonuc.returncode != 0:
        return "COKTU", (sonuc.stderr or "")[:120]

    cikti = sonuc.stdout.strip()
    if not cikti:
        # Fail-open korlugu onarimi: iz yoksa "allow" SAYILMAZ.
        if "MIMAR-KAPISI allow" in (sonuc.stderr or ""):
            return "allow", ""
        return "IZSIZ-ALLOW", (sonuc.stderr or "")[:120]
    try:
        veri = json.loads(cikti)
    except Exception:
        return "PARSE-HATASI", cikti[:120]
    hso = veri.get("hookSpecificOutput") or {}
    return hso.get("permissionDecision", "allow"), (hso.get("permissionDecisionReason") or "")[:80]


def kume_kostur(baslik, vakalar, cwd=REPO):
    print("")
    print("=" * 84)
    print(baslik)
    print("=" * 84)
    print("{:<4} {:<8} {:<12} {:<7} {:<6} {:<40}".format(
        "No", "Beklenen", "Olculen", "Kimlik", "Sonuc", "Vaka"))
    print("-" * 84)
    basarisiz = []
    atlanan = []
    cevre_atlanan = []
    for no, beklenen, arac, hedef, agent_id, aciklama in vakalar:
        if KAYITLI_WT in hedef:
            if not KAYITLI_WT_YOL:
                cevre_atlanan.append(no)
                print("{:<4} {:<8} {:<12} {:<7} {:<6} {:<40}".format(
                    no, beklenen, "CEVRE-YOK", "ISCI" if agent_id else "MIMAR",
                    "ATLA", aciklama[:40]))
                continue
            hedef = hedef.replace(KAYITLI_WT, KAYITLI_WT_YOL)
        olculen, _ = kancayi_kostur(arac, hedef, cwd, agent_id)
        gecti = (olculen == beklenen)
        if olculen in ATLANAN_ISARETLER:
            atlanan.append(no)
        if not gecti:
            basarisiz.append((no, beklenen, olculen, aciklama))
        print("{:<4} {:<8} {:<12} {:<7} {:<6} {:<40}".format(
            no, beklenen, olculen, "ISCI" if agent_id else "MIMAR",
            "OK" if gecti else "KIRMIZI", aciklama[:40]))
    return basarisiz, atlanan, cevre_atlanan


def commit_kume_kostur(gecici_kok):
    print("")
    print("=" * 84)
    print("COMMIT KAPISI (git-native pre-commit betigi — stdin JSON'u YOK)")
    print("=" * 84)
    print("{:<4} {:<8} {:<8} {:<6} {:<44}".format("No", "Beklenen", "Olculen", "Sonuc", "Vaka"))
    print("-" * 84)
    basarisiz = []
    atlanan = []

    if not os.path.exists(COMMIT):
        print("EKSIK KANCA: " + COMMIT)
        return [(no, bek, "EKSIK-KANCA", ac) for no, bek, _, _, _, ac in COMMIT_VAKALARI], \
               [no for no, _, _, _, _, _ in COMMIT_VAKALARI]

    for no, beklenen, girdi, ek_env, hazirlik, aciklama in COMMIT_VAKALARI:
        gitdir = os.path.join(gecici_kok, "gd-" + str(no))
        os.makedirs(gitdir, exist_ok=True)
        if hazirlik:
            with open(os.path.join(gitdir, hazirlik), "w", encoding="utf-8") as f:
                f.write("deadbeef\n")

        ortam = dict(os.environ)
        ortam.pop("PRUVO_MIMAR_ONAY", None)  # ortamdan SILINEREK — miras alma
        ortam.update(ek_env)

        toplevel = "/private/tmp/baska-repo" if no == 106 else REPO
        sonuc = subprocess.run(
            [sys.executable, COMMIT, "--stdin", "--toplevel", toplevel, "--gitdir", gitdir],
            input=girdi, capture_output=True, text=True, env=ortam,
        )
        olculen = sonuc.returncode
        gecti = (olculen == beklenen)

        # BYPASS YOLLARI: sadece exit 0 yetmez — GURULTU + LOG da kanit
        # (sessiz bypass = muhasebe delinmesi).
        if no in BYPASS_MUHASEBESI and gecti:
            iz, anahtar = BYPASS_MUHASEBESI[no]
            gurultu = iz in (sonuc.stderr or "")
            log_yolu = os.path.join(gitdir, "pruvo-kapi-log.jsonl")
            log_var = False
            try:
                with open(log_yolu, encoding="utf-8") as f:
                    log_var = anahtar in f.read()
            except Exception:
                log_var = False
            if not (gurultu and log_var):
                gecti = False
                aciklama = aciklama + " [gurultu=%s log=%s]" % (gurultu, log_var)

        if not gecti:
            basarisiz.append((no, beklenen, olculen, aciklama))
        print("{:<4} {:<8} {:<8} {:<6} {:<44}".format(
            no, beklenen, olculen, "OK" if gecti else "KIRMIZI", aciklama[:44]))
    return basarisiz, atlanan


BEKLENEN_KABLO_ANAHTARLARI = (
    "BASH_ZINCIRI_ICRA", "YAZMA_ZINCIRI_KILIT", "PRECOMMIT_COMMIT_KAPISI")

TAM_AYAR = {
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [
                {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-icra-kapisi.py"'}]},
            {"matcher": "Write|Edit|MultiEdit", "hooks": [
                {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-kod-kilidi.py"'}]},
        ]
    }
}
EKSIK_AYAR = {
    "hooks": {
        "PreToolUse": [
            {"matcher": "Write|Edit|MultiEdit", "hooks": [
                {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-kod-kilidi.py"'}]},
        ]
    }
}
# B5 (20 Tem): "DOGRU KANCA, YANLIS MATCHER" ekseni. Iki kanca da settings.json'da
# KAYITLI ama icra kapisi Bash yerine Write blogunun altina kablolanmis → Bash aleti
# icin HIC kosmaz. Raporcu bu duruma 'var' derse kablo yalanidir; 'yok' demeli.
# Bu vaka N1 mutasyonunun (_zincirde_var icindeki matcher kontrolu silinir) nobetcisi:
# EKSIK_AYAR'da kanca HIC yok, o yuzden 111 bu mutasyonu yakalayamiyordu.
YANLIS_MATCHER_AYAR = {
    "hooks": {
        "PreToolUse": [
            {"matcher": "Write|Edit|MultiEdit", "hooks": [
                {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-kod-kilidi.py"'},
                {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/mimar-icra-kapisi.py"'}]},
        ]
    }
}


def _kablo_oku(ayar_yolu, precommit_yolu):
    sonuc = subprocess.run(
        [sys.executable, KUR, "--durum", "--ayar", ayar_yolu, "--precommit", precommit_yolu],
        capture_output=True, text=True)
    okunan = {}
    for satir in (sonuc.stdout or "").splitlines():
        if "=" in satir:
            k, _, v = satir.partition("=")
            okunan[k.strip()] = v.strip()
    return sonuc.returncode, okunan, sonuc.stdout


def kablo_kume_kostur(gecici_kok):
    """KABLO ASSERTION — raporcunun (mimar-kapi-kur.py --durum) KENDISI sinanir.

    Eski surumde tek vaka vardi (110) ve CANLI settings.json'u okuyordu: raporcu
    "her sey var" diye YALAN soylese bile YESIL yanardi (nobetsiz bolge) ve testin
    yesili dal-disi bir dosyaya asiliydi. Artik iki HERMETIK vaka:
      110 POZITIF: tam kurulu gecici kablo -> hepsi 'var', exit 0
      111 NEGATIF: Bash zinciri EKSIK gecici kablo -> BASH_ZINCIRI_ICRA='yok', exit 1
    Canli kablo BILGI olarak basilir (karar vermez); teshis araci:
    python3 tools/kapi-envanteri.py"""
    print("")
    print("=" * 84)
    print("KABLO ASSERTION (raporcu sinanir — HERMETIK gecici kopyalar)")
    print("=" * 84)
    basarisiz = []
    atlanan = []
    if not os.path.exists(KUR):
        print("110/111/114  EKSIK: " + KUR)
        return ([(110, "var", "EKSIK-KURUCU", "kablo raporu"),
                 (111, "yok", "EKSIK-KURUCU", "kablo negatif"),
                 (114, "yok", "EKSIK-KURUCU", "kablo yanlis-matcher")], [110, 111, 114])

    kablo_dizin = os.path.join(gecici_kok, "kablo")
    os.makedirs(kablo_dizin, exist_ok=True)
    tam_ayar = os.path.join(kablo_dizin, "settings-tam.json")
    eksik_ayar = os.path.join(kablo_dizin, "settings-eksik.json")
    yanlis_ayar = os.path.join(kablo_dizin, "settings-yanlis-matcher.json")
    tam_hook = os.path.join(kablo_dizin, "pre-commit-tam")
    bos_hook = os.path.join(kablo_dizin, "pre-commit-bos")
    with open(tam_ayar, "w", encoding="utf-8") as f:
        json.dump(TAM_AYAR, f)
    with open(eksik_ayar, "w", encoding="utf-8") as f:
        json.dump(EKSIK_AYAR, f)
    with open(yanlis_ayar, "w", encoding="utf-8") as f:
        json.dump(YANLIS_MATCHER_AYAR, f)
    with open(tam_hook, "w", encoding="utf-8") as f:
        f.write('#!/bin/sh\npython3 "$(git rev-parse --show-toplevel)/tools/mimar-commit-kapisi.py"\n')
    with open(bos_hook, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\nexit 0\n")

    # 110 POZITIF
    rc, okunan, ham = _kablo_oku(tam_ayar, tam_hook)
    eksik = [k for k in BEKLENEN_KABLO_ANAHTARLARI if okunan.get(k) != "var"]
    gecti = (rc == 0) and not eksik
    print("110  POZITIF exit={} eksik={} — {}".format(rc, eksik or "yok",
                                                      "OK" if gecti else "KIRMIZI"))
    if not gecti:
        basarisiz.append((110, "hepsi=var/exit0", str(okunan), "kablo pozitif"))

    # 111 NEGATIF — raporcu EKSIGI gormek ZORUNDA (yalanci raporcu nobetcisi)
    rc2, okunan2, ham2 = _kablo_oku(eksik_ayar, bos_hook)
    gecti2 = (rc2 == 1
              and okunan2.get("BASH_ZINCIRI_ICRA") == "yok"
              and okunan2.get("PRECOMMIT_COMMIT_KAPISI") == "yok"
              and okunan2.get("YAZMA_ZINCIRI_KILIT") == "var")
    print("111  NEGATIF exit={} okunan={} — {}".format(
        rc2, {k: okunan2.get(k) for k in BEKLENEN_KABLO_ANAHTARLARI},
        "OK" if gecti2 else "KIRMIZI"))
    if not gecti2:
        basarisiz.append((111, "bash=yok/precommit=yok/exit1", str(okunan2), "kablo negatif"))

    # 114 YANLIS MATCHER — kanca KAYITLI ama Bash yerine Write blogunda (B5 ekseni).
    # Raporcu matcher'i denetlemezse 'var' der; denetlerse 'yok' demeli.
    rc3, okunan3, ham3 = _kablo_oku(yanlis_ayar, tam_hook)
    gecti3 = (rc3 == 1
              and okunan3.get("BASH_ZINCIRI_ICRA") == "yok"
              and okunan3.get("YAZMA_ZINCIRI_KILIT") == "var"
              and okunan3.get("PRECOMMIT_COMMIT_KAPISI") == "var")
    print("114  YANLIS-MATCHER exit={} okunan={} — {}".format(
        rc3, {k: okunan3.get(k) for k in BEKLENEN_KABLO_ANAHTARLARI},
        "OK" if gecti3 else "KIRMIZI"))
    if not gecti3:
        basarisiz.append((114, "bash=yok/exit1", str(okunan3),
                          "kablo yanlis-matcher (dogru kanca, yanlis blok)"))

    # BILGI: canli kablo (karar vermez — teshis tools/kapi-envanteri.py'de)
    canli = subprocess.run([sys.executable, KUR, "--durum"], capture_output=True, text=True)
    print("BILGI canli kablo exit={} | {}".format(
        canli.returncode, " ".join((canli.stdout or "").split())[:120]))
    return basarisiz, atlanan


def gecici_worktree_kur(temel):
    """Repo DISINDA, git'e KAYITLI gecici bir worktree kurar (hermetiklik).
    '--no-checkout' sayesinde dosya kopyalanmaz — yalniz .git/worktrees kaydi olusur.
    Doner: yol ya da None (kurulamadiysa vakalar CEVRE-ATLANAN olur)."""
    yol = os.path.join(temel, "kayitli-wt")
    sonuc = subprocess.run(
        ["git", "-C", REPO, "worktree", "add", "--no-checkout", "--detach", yol, "HEAD"],
        capture_output=True, text=True)
    if sonuc.returncode != 0 or not os.path.isdir(yol):
        print("CEVRE: gecici worktree kurulamadi — " +
              (sonuc.stderr or "").strip().splitlines()[-1:][0] if sonuc.stderr else "?")
        return None
    return os.path.normpath(yol)


def gecici_worktree_kaldir(yol):
    """B6-yan (20 Tem): 'remove' donus kodu ARTIK DENETLENIR. Eskiden sessizdi —
    kaldirilamayan gecici worktree hem diskte hem .git/worktrees kaydinda kaliyor,
    yani test kendi kurdugu MUAF BOLGEYI sizdiriyordu (sonraki kosumlar bu kayittan
    etkilenir = hermetiklik kaybi). Doner: hata metni ya da None."""
    if not yol:
        return None
    sonuc = subprocess.run(["git", "-C", REPO, "worktree", "remove", "--force", yol],
                           capture_output=True, text=True)
    if sonuc.returncode != 0:
        return (sonuc.stderr or "?").strip().splitlines()[-1:] or ["?"]
    if os.path.exists(yol):
        return ["dizin hala diskte: " + yol]
    return None


def main():
    global KAYITLI_WT_YOL
    # realpath ZORUNLU: macOS'ta /var -> /private/var symlink'i; git kayda GERCEK yolu
    # yazar, kapi da kaydi oyle okur (olculdu: symlink'li yol deny aliyordu).
    temel = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-kapi-test-"))
    gecici_kok = os.path.join(temel, ".test-gitdir")
    os.makedirs(gecici_kok, exist_ok=True)
    KAYITLI_WT_YOL = gecici_worktree_kur(temel)

    kumeler = [
        ("ZORUNLU 15 VAKA (mimar spec'i) — MIMAR kimligi", VAKALAR, REPO),
        ("EK VAKALAR (porozite kapatma) — MIMAR kimligi", EK_VAKALAR, REPO),
        ("DEVIR MEKTUBU MERGE PROSEDURU — hepsi gecmeli", MERGE_VAKALARI, REPO),
        ("MUHENDIS AKISI — cwd: worktree (muafiyet YOK, yol-tabanli)", MUHENDIS_VAKALARI, WORKTREE),
        ("MODUL/ENJEKSIYON YUZEYI — MIMAR kimligi", MODUL_VAKALARI, REPO),
        ("ISCI IKIZLERI (agent_id DOLU) — YANLIS-POZITIF NOBETCISI", ISCI_VAKALARI, REPO),
        ("MIMAR TARAFI YENI VAKALAR (onek/kayit/test-modulu/Edit)", MIMAR_YENI_VAKALARI, REPO),
        ("CWD REPO DISINDA (F adiminin kalan isi) — MIMAR kimligi", DIS_CWD_VAKALARI, DIS_CWD),
        ("22 TEM SERTLESTIRME (olcum/curl/codex/python-allowlist/sh-nobetci)", MIMAR_22TEM_VAKALARI, REPO),
    ]

    toplam = sum(len(v) for _, v, _ in kumeler) + len(COMMIT_VAKALARI) + 3
    print("TOPLAM VAKA: {} (kanca {} + commit {} + kablo 3)".format(
        toplam, sum(len(v) for _, v, _ in kumeler), len(COMMIT_VAKALARI)))
    print("TOOLS DIZINI: " + TOOLS)
    print("GECICI KAYITLI WORKTREE: " + (KAYITLI_WT_YOL or "KURULAMADI (cevre-atlanan)"))

    basarisiz = []
    atlanan = []
    cevre_atlanan = []
    try:
        for baslik, vakalar, cwd in kumeler:
            b, a, c = kume_kostur(baslik, vakalar, cwd)
            basarisiz += b
            atlanan += a
            cevre_atlanan += c
        b, a = commit_kume_kostur(gecici_kok)
        basarisiz += b
        atlanan += a
        b, a = kablo_kume_kostur(gecici_kok)
        basarisiz += b
        atlanan += a
    finally:
        sizinti = gecici_worktree_kaldir(KAYITLI_WT_YOL)
        shutil.rmtree(temel, ignore_errors=True)

    print("")
    print("ATLANAN/KOSULAMAYAN VAKA (kapi kosmadi = KIRMIZI): {} {}".format(
        len(atlanan), atlanan or ""))
    # B6-yan (20 Tem): CEVRE-ATLANAN artik SESSIZ YESIL degil. Bu takim bir MERGE
    # KAPISI olarak kullaniliyor; "cevre bozuldu, 4 vaka kosmadi" durumu exit 0
    # dondurursse kapi yalan soyler. Gorunur (BUYUK HARF) + fail-loud.
    if cevre_atlanan:
        print("CEVRE-ATLANAN VAKA (CEVRE KURULAMADI — KOSULMAYAN VAKA VAR): {} {}".format(
            len(cevre_atlanan), cevre_atlanan))
    else:
        print("CEVRE-ATLANAN VAKA: 0")
    if sizinti:
        print("CEVRE SIZINTISI: gecici worktree KALDIRILAMADI — {}".format(sizinti))
    if basarisiz:
        print("SONUC: {}/{} gecti — KIRMIZI vakalar:".format(toplam - len(basarisiz), toplam))
        for no, beklenen, olculen, aciklama in basarisiz:
            print("  vaka {}: beklenen={} olculen={} ({})".format(no, beklenen, olculen, aciklama))
        sys.exit(1)
    if atlanan:
        print("SONUC: KIRMIZI — atlanan vaka var (sessiz kirpma yasak).")
        sys.exit(1)
    if cevre_atlanan or sizinti:
        print("SONUC: KIRMIZI — CEVRE-ATLANAN={} SIZINTI={}. Takim MERGE KAPISIDIR; "
              "kosulmayan vaka ya da sizdirilan gecici worktree ile YESIL YANMAZ.".format(
                  len(cevre_atlanan), bool(sizinti)))
        sys.exit(1)
    print("SONUC: {}/{} vaka GECTI (cevre-atlanan 0, sizinti yok).".format(toplam, toplam))
    sys.exit(0)


main()
