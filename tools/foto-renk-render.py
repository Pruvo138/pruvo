#!/usr/bin/env python3
"""FOTO ④ TEK RENK ONIZLEMESI — saglayici build modeli (GLB) SECILEN STOK RENGINDE Blender ile cizilir.

Okan 14 Eki 2026 03:0x (Y1): tek renk (Siyah/Beyaz/Gri) secen musteri ④'te urunu O RENKTE gorur. Model
onizleme aninda kurulur (sunucu shop/src/foto.js renkIlerle), koşucu (tools/foto-uretec-kosucu.py renk
kuyrugu) bu araci cagirir. 2D boyama/posterize YOK: GLB'nin TUM doku/malzemesi atilir, model TEK
malzemeyle (filament hex'i) hacimli cizilir — renk farki yalniz isik/golgeden gelir.

Sistem python3:
  python3 tools/foto-renk-render.py --glb M.glb --renk F2F2F2 --cikti O.png [--kenar 1024] [--ornek 64]
                                   [--arka F4F5F7] [--dokulu]
  -> rc 0 + son satir `RENK-RENDER=OK bayt=<n> kenar=<n> yassi=<0|1> sure_sn=<n>`
     aksi rc != 0 + son satir `RENK-RENDER=YOK sebep=<kod>`
  --dokulu: TESHIS (kanit) — modeli kendi dokusuyla cizer (yerlesim/yon kontrolu); uretim yolu KULLANMAZ.
Blender ici (bu dosya kendini cagirir):
  Blender -b --factory-startup --python tools/foto-renk-render.py -- blender-ic --glb ... --cikti ...

SAHNE (TeKiN tools/foto_kart_render.py dersleri — Cycles CPU, sabit tohum, adaptif ornekleme KAPALI, denoise,
yumusak uc alan isigi key/fill/rim, golge yakalayici zemin, film seffaf -> duz arka plan uzerine kompozit):
- Yerlesim: Blender glTF ice aktarimi (+Y yukari -> +Z yukari, on yuz -Y). YASSI model (en ince eksen < 0.25 x orta
  eksen; kabartma plaket yatik gelir) DIK kaldirilir: kapali duz sirt tarafi (ince eksende kose yogunlugu yuksek
  uc) kameranin tersine, kabartma yuzu kameraya (-Y) doner.
- Kamera: on yuzden az +20 derece, yukseklik 12 derece, 85 mm; nesne kareye ~0.70 doluluk.
- Malzeme: Principled, Base Color = filament hex (sRGB -> lineer), roughness 0.5, metallic 0.
BLENDER KAPISI: jenerator tools/foto_kart_render.py `kapi_al` (ayni anda TEK Blender + bos bellek esigi) varsa
alinir; yoksa satir `KAPI=YOK` (koşucu launchd'de tek is sirayla kosar).
Test kancasi: FOTO_RENK_BLENDER (Blender ikilisi yerine komut; koşucu birim testi sahte Blender kullanir),
FOTO_RENK_KAPI_YOK=1 (kapi atlanir — yalniz hermetik test).
"""
import argparse
import os
import re
import shlex
import subprocess
import sys
import time

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
KENAR = 1024
ORNEK = 64
ARKA = "F8F9FA"          # notr studyo zemini merkezi (site kart zemini F4F5F7 ile uyumlu)
ARKA_KENAR = "E3E5E8"    # ... kenarlara dogru yumusak radyal degrade (tum turlerde AYNI sablon)
DOLULUK = 0.70
ROUGHNESS = 0.5
YASSI_ORAN = 0.25
AZ_OFSET = 20.0          # on yuzden saga donus (derece)
YUKSEKLIK = 12.0         # kamera yuksekligi (derece)
HEDEF_L = 0.05           # pozlama: L bunun altindaki (siyah) filamentte isik HEDEF_L / L kadar acilir
POZ_TAVAN = 1.4          # ... en cok 1.4x (beyaz/gri carpani 1: renkler arasi parlaklik farki korunur)
KEY_AZ, KEY_EL = 60.0, 38.0   # key isik: kameradan sola 60, yukari 38 derece (kabartmayi yalar)
KEY_GUC, FILL_GUC, RIM_GUC = 400.0, 60.0, 200.0
DUNYA_GUC = 0.18
SURE_SN = 900
KAPI_BELLEK_MB = 3072    # Blender kapisi bos bellek esigi (tek renk render'i icin)
KAPI_TAVAN_SN = 600      # kapi bekleme tavani; asilirsa render YOK, koşucu sonraki turda dener
HEX_KALIBI = re.compile(r"^#?[0-9A-Fa-f]{6}$")

try:
    import bpy  # noqa: F401
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# =====================================================================================
#                                   BLENDER TARAFI
# =====================================================================================
if IN_BLENDER:
    import math

    import numpy as np
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Matrix, Vector

    def sahne_kur(kenar, ornek, pozlama):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.device = 'CPU'
        sc.cycles.samples = ornek
        sc.cycles.seed = 0
        sc.cycles.use_animated_seed = False
        sc.cycles.use_adaptive_sampling = False
        sc.cycles.use_denoising = True
        try:
            sc.cycles.denoiser = 'OPENIMAGEDENOISE'
        except Exception as e:  # noqa: BLE001
            print("denoise uyari:", e)
        sc.render.threads_mode = 'FIXED'
        sc.render.threads = 8
        sc.render.resolution_x = kenar
        sc.render.resolution_y = kenar
        sc.render.resolution_percentage = 100
        sc.render.film_transparent = True
        sc.render.use_stamp = False
        sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGBA'
        sc.render.image_settings.color_depth = '8'
        # AgX: beyaz filamentte parlak yuzeyler KIRPILMAZ (Standard'da beyaz kabartma duz beyaza donuyordu, 14 Eki).
        try:
            sc.view_settings.view_transform = 'AgX'
        except TypeError:
            sc.view_settings.view_transform = 'Filmic'
        sc.view_settings.look = 'None'
        w = bpy.data.worlds.new("w")
        sc.world = w
        w.use_nodes = True
        nt = w.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputWorld")
        bg = nt.nodes.new("ShaderNodeBackground")
        bg.inputs[0].default_value = (0.78, 0.79, 0.80, 1)
        bg.inputs[1].default_value = DUNYA_GUC * pozlama
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
        return sc

    def pozlama_carpani(hx):
        """Isik carpani: renkler ARASI fark korunur (beyaz beyaz, gri gri gorunur — normallestirme YOK); yalniz cok
        koyu filamentte (siyah, L~0.01) isik en cok 2x acilir ki sekil parlama/golgeyle okunsun. Dokulu teshiste 1."""
        r, g, b = (_lin(c) for c in hex_rgb(hx))
        L = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return min(POZ_TAVAN, max(1.0, HEDEF_L / max(L, 1e-3)))

    def tek_malzeme(hx):
        m = bpy.data.materials.new("filament")
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        r, g, bl = (_lin(c) for c in hex_rgb(hx))
        b.inputs["Base Color"].default_value = (r, g, bl, 1)
        b.inputs["Roughness"].default_value = ROUGHNESS
        if "Metallic" in b.inputs:
            b.inputs["Metallic"].default_value = 0.0
        return m

    def dunya_koseleri(nesneler):
        parca = []
        for o in nesneler:
            me = o.data
            co = np.empty(len(me.vertices) * 3, dtype=np.float64)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            m = np.array(o.matrix_world, dtype=np.float64)
            parca.append(co @ m[:3, :3].T + m[:3, 3])
        return np.concatenate(parca, axis=0)

    def yerlesim(co):
        """Normallestirme matrisi: (donus, yassi mi). Yassi modelde kabartma yuzu -Y'ye, dik."""
        boy = co.max(axis=0) - co.min(axis=0)
        sira = np.argsort(boy)
        ince = int(sira[0])
        yassi = bool(boy[ince] < YASSI_ORAN * boy[sira[1]])
        R = Matrix.Identity(3)
        if yassi:
            lo, hi = co[:, ince].min(), co[:, ince].max()
            e = 0.02 * (hi - lo)
            n_lo = int((co[:, ince] < lo + e).sum())
            n_hi = int((co[:, ince] > hi - e).sum())
            # Kapali duz sirt ucunda kose yogunlugu yuksek -> kabartma ters yone (+) bakar.
            arti = n_lo >= n_hi
            # Kabartma normali -> -Y (kameraya). Acik eksen donusleri (zit vektorde keyfi eksen secimi YOK):
            #   Z: +Z -> X etrafinda +90 (eski +Y yukari) · -Z -> X etrafinda -90 (eski -Y yukari)
            #   Y: -Y -> donus yok · +Y -> Z etrafinda 180
            #   X: +X -> Z etrafinda -90 · -X -> Z etrafinda +90
            if ince == 2:
                R = Matrix.Rotation(math.radians(90.0 if arti else -90.0), 3, 'X')
            elif ince == 1:
                R = Matrix.Identity(3) if not arti else Matrix.Rotation(math.radians(180.0), 3, 'Z')
            else:
                R = Matrix.Rotation(math.radians(-90.0 if arti else 90.0), 3, 'Z')
        return R, yassi

    def isik(ad, konum, guc, boy, hedef, golge=True):
        l = bpy.data.lights.new(ad, 'AREA')
        l.energy = guc
        l.size = boy
        if not golge:
            for nesne, oz in ((l, "use_shadow"), (getattr(l, "cycles", None), "cast_shadow")):
                if nesne is not None and hasattr(nesne, oz):
                    setattr(nesne, oz, False)
        o = bpy.data.objects.new(ad, l)
        o.location = konum
        bpy.context.collection.objects.link(o)
        o.rotation_euler = (Vector(hedef) - Vector(konum)).to_track_quat('-Z', 'Y').to_euler()
        return o

    def yon(az, el):
        a, e = math.radians(az), math.radians(el)
        return Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))

    def kadrajla(sc, cam, pts, hedef, az, el, doluluk):
        d = yon(az, el)
        mesafe = 6.0
        cam.data.shift_x = 0.0
        cam.data.shift_y = 0.0
        for _ in range(16):
            cam.location = hedef + d * mesafe
            cam.rotation_euler = (hedef - cam.location).to_track_quat('-Z', 'Y').to_euler()
            bpy.context.view_layer.update()
            px = [world_to_camera_view(sc, cam, p) for p in pts]
            x0, x1 = min(p.x for p in px), max(p.x for p in px)
            y0, y1 = min(p.y for p in px), max(p.y for p in px)
            k = max(x1 - x0, y1 - y0) / doluluk
            mesafe *= (0.5 + 0.5 * k)
            cam.data.shift_x -= (0.5 - (x0 + x1) / 2.0)
            cam.data.shift_y -= (0.5 - (y0 + y1) / 2.0)

    def arka_plan(w, h, ic_hex, kenar_hex):
        """NOTR STUDYO zemini (Okan 14 Eki 03:5x "uygun arkaplan"): merkezde acik (ic) -> kenarlara dogru hafif koyu
        (kenar) yumusak radyal degrade; tum turlerde AYNI. Satir 0 = goruntunun USTU (Blender pikselleri alttan baslar,
        cagiran duzeltir)."""
        yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
        xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
        r = np.clip(np.sqrt((xx - 0.5) ** 2 + (yy - 0.42) ** 2) / 0.78, 0.0, 1.0) ** 1.6
        ic = np.array([c / 255.0 for c in hex_rgb(ic_hex)], dtype=np.float32)
        kenar = np.array([c / 255.0 for c in hex_rgb(kenar_hex)], dtype=np.float32)
        return ic * (1.0 - r[..., None]) + kenar * r[..., None]

    def kompozit(ham, cikti, arka_hex):
        """Seffaf render (golge yakalayici alfasi dahil) -> notr studyo degradesi uzerine, RGB PNG."""
        im = bpy.data.images.load(ham)
        w, h = im.size
        px = np.empty(w * h * 4, dtype=np.float32)
        im.pixels.foreach_get(px)
        px = px.reshape(h, w, 4)
        a = px[..., 3:4]
        arka = arka_plan(w, h, arka_hex, ARKA_KENAR)[::-1]   # Blender piksel dizisi alttan ustedir
        rgb = px[..., :3] * a + arka * (1.0 - a)
        out = np.concatenate([rgb, np.ones((h, w, 1), dtype=np.float32)], axis=2)
        yeni = bpy.data.images.new("kompozit", w, h, alpha=False)
        yeni.pixels.foreach_set(out.ravel())
        yeni.filepath_raw = cikti
        yeni.file_format = 'PNG'
        yeni.save()

    def blender_ic(argv):
        ap = argparse.ArgumentParser()
        ap.add_argument("mod", choices=["blender-ic"])
        ap.add_argument("--glb", required=True)
        ap.add_argument("--renk", required=True)
        ap.add_argument("--cikti", required=True)
        ap.add_argument("--kenar", type=int, default=KENAR)
        ap.add_argument("--ornek", type=int, default=ORNEK)
        ap.add_argument("--arka", default=ARKA)
        ap.add_argument("--dokulu", action="store_true")
        a = ap.parse_args(argv)
        poz = 1.0 if a.dokulu else pozlama_carpani(a.renk)
        sc = sahne_kur(a.kenar, a.ornek, poz)
        bpy.ops.import_scene.gltf(filepath=a.glb)
        nesneler = [o for o in sc.objects if o.type == 'MESH' and len(o.data.vertices)]
        if not nesneler:
            print("RENK-IC=YOK sebep=mesh-yok")
            sys.exit(3)
        co = dunya_koseleri(nesneler)
        R, yassi = yerlesim(co)
        Rn = np.array(R, dtype=np.float64)
        dc = co @ Rn.T
        mn, mx = dc.min(axis=0), dc.max(axis=0)
        olcek = 2.0 / float((mx - mn).max())
        merkez = Vector(((mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0, mn[2]))
        T = (Matrix.Scale(olcek, 4) @ Matrix.Translation(-merkez) @ R.to_4x4())
        mat = None if a.dokulu else tek_malzeme(a.renk)
        for o in nesneler:
            o.matrix_world = T @ o.matrix_world
            if mat is not None:
                o.data.materials.clear()
                o.data.materials.append(mat)
                for p in o.data.polygons:
                    p.material_index = 0
        bpy.context.view_layer.update()
        dc = dunya_koseleri(nesneler)
        n = max(1, len(dc) // 6000)
        pts = [Vector(p) for p in dc[::n]]
        zmax = float(dc[:, 2].max())
        hedef = Vector((0.0, 0.0, zmax / 2.0))
        bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0, 0, 0))
        bpy.context.active_object.is_shadow_catcher = True
        az = 270.0 + AZ_OFSET
        # Key soldan-yukaridan YALAYARAK (kabartma golgesi), fill zayif, rim arka kontur; hepsi pozlama carpaniyla.
        isik("key", hedef + yon(az - KEY_AZ, KEY_EL) * 5.0, KEY_GUC * poz, 3.0, hedef)
        isik("fill", hedef + yon(az + 60, 15) * 5.0, FILL_GUC * poz, 4.5, hedef, golge=False)
        isik("rim", hedef + yon(az + 165, 40) * 5.0, RIM_GUC * poz, 2.5, hedef, golge=False)
        cd = bpy.data.cameras.new("cam")
        cd.lens = 85.0
        cd.sensor_fit = 'HORIZONTAL'
        cd.sensor_width = 36.0
        cam = bpy.data.objects.new("cam", cd)
        sc.collection.objects.link(cam)
        sc.camera = cam
        kadrajla(sc, cam, pts, hedef, az, YUKSEKLIK, DOLULUK)
        ham = a.cikti + ".ham.png"
        sc.render.filepath = ham
        bpy.ops.render.render(write_still=True)
        kompozit(ham, a.cikti, a.arka)
        try:
            os.remove(ham)
        except OSError:
            pass
        print("RENK-IC=OK yassi=%d" % (1 if yassi else 0))


# =====================================================================================
#                                   SISTEM TARAFI
# =====================================================================================
def blender_komutu():
    k = os.environ.get("FOTO_RENK_BLENDER", "")
    return shlex.split(k) if k else [BLENDER]


def kapi_al(yaz):
    """Jenerator Blender kapisi (TEK Blender + bos bellek). Yoksa KAPI=YOK (koşucu zaten sirayla kosar)."""
    if os.environ.get("FOTO_RENK_KAPI_YOK") == "1":
        yaz("KAPI=YOK sebep=test")
        return
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    arac = os.path.join(jen, "tools")
    if not os.path.isfile(os.path.join(arac, "foto_kart_render.py")):
        yaz("KAPI=YOK sebep=arac-yok")
        return
    # Tek renk render'i (<= 1024 px, tek malzeme) kapinin varsayilan 8 GB bos bellek esigine ihtiyac duymaz
    # (14 Eki olcumu: makinede bos bellek ~7 GB, kapi 10 dk bekleyip asili sayildi). Esik KAPI_BELLEK_MB;
    # ortamda acikca verilmisse o gecer. Bekleme tavani KAPI_TAVAN_SN: asilirsa render YOK (koşucu sonra dener).
    os.environ.setdefault("PRUVO_BLENDER_MIN_BELLEK_MB", str(KAPI_BELLEK_MB))
    sys.path.insert(0, arac)
    try:
        import foto_kart_render  # noqa: E402
        foto_kart_render.kapi_al(toplam_sn=KAPI_TAVAN_SN)
        yaz("KAPI=ALINDI")
    finally:
        sys.path.remove(arac)


def png_mi(yol):
    try:
        with open(yol, "rb") as f:
            return f.read(8) == b"\x89PNG\r\n\x1a\n"
    except OSError:
        return False


def render(glb, renk, cikti, kenar=KENAR, ornek=ORNEK, arka=ARKA, dokulu=False, yaz=print):
    """Donus (rc, satir). rc 0 = cikti PNG yazildi."""
    if not os.path.isfile(glb) or os.path.getsize(glb) == 0:
        return 2, "RENK-RENDER=YOK sebep=glb-yok"
    if not HEX_KALIBI.match(renk or "") or not HEX_KALIBI.match(arka or ""):
        return 2, "RENK-RENDER=YOK sebep=renk-gecersiz"
    if not (64 <= int(kenar) <= 2048) or not (1 <= int(ornek) <= 1024):
        return 2, "RENK-RENDER=YOK sebep=parametre"
    if os.path.exists(cikti):
        os.remove(cikti)
    try:
        kapi_al(yaz)
    except SystemExit:
        return 1, "RENK-RENDER=YOK sebep=kapi"
    cmd = blender_komutu() + ["-b", "--factory-startup", "--python", os.path.abspath(__file__), "--",
                              "blender-ic", "--glb", os.path.abspath(glb), "--renk", renk.lstrip("#"),
                              "--cikti", os.path.abspath(cikti), "--kenar", str(int(kenar)),
                              "--ornek", str(int(ornek)), "--arka", arka.lstrip("#")]
    if dokulu:
        cmd.append("--dokulu")
    bas = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=SURE_SN,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    except subprocess.TimeoutExpired:
        return 1, "RENK-RENDER=YOK sebep=sure-asimi"
    except OSError:
        return 1, "RENK-RENDER=YOK sebep=blender-baslatilamadi"
    sure = int(time.time() - bas)
    m = re.search(r"RENK-IC=OK yassi=(\d)", p.stdout or "")
    if p.returncode != 0 or not m or not png_mi(cikti) or os.path.getsize(cikti) == 0:
        kuyruk = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()[-3:]
        yaz("BLENDER rc=%d %s" % (p.returncode, " | ".join(kuyruk)[:400]))
        return 1, "RENK-RENDER=YOK sebep=blender-rc-%d" % p.returncode
    return 0, "RENK-RENDER=OK bayt=%d kenar=%d yassi=%s sure_sn=%d" % (
        os.path.getsize(cikti), int(kenar), m.group(1), sure)


def main(argv):
    # ORTAK RENDER SOZLESMESI (BaBa 14 Eki 04:0x; TeKiN pruvo-jenerator tools/foto_kart_render.py AYNI CLI'yi
    # tasiyacak): --model <dosya> --renk HEX [--renk2 HEX --bolge2 ad] --arkaplan studyo --cikti png. Bu arac GECICI
    # kopru: yalniz GLB/glTF + tek malzeme; iki malzeme / 3MF isteyen cagri rc 2 (koşucu TeKiN aracini tercih eder).
    ap = argparse.ArgumentParser(description="④ tek renk onizlemesi: GLB -> secilen renkte Blender render")
    ap.add_argument("--model", "--glb", dest="model", required=True)
    ap.add_argument("--renk", required=True, help="filament hex (orn. F2F2F2)")
    ap.add_argument("--renk2", default="")
    ap.add_argument("--bolge2", default="")
    ap.add_argument("--arkaplan", choices=["studyo"], default="studyo")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--kenar", type=int, default=KENAR)
    ap.add_argument("--ornek", type=int, default=ORNEK)
    ap.add_argument("--arka", default=ARKA)
    ap.add_argument("--dokulu", action="store_true", help=argparse.SUPPRESS)
    # TeKiN ortak aracinin alt komutu (`sablon`) bu koprude de kabul edilir (koşucu tek cagri bicimi kullanir).
    a = ap.parse_args(argv[1:] if argv[:1] == ["sablon"] else argv)
    if a.renk2 or a.bolge2:
        print("RENK-RENDER=YOK sebep=iki-malzeme-desteklenmiyor")
        return 2
    if not a.model.lower().endswith((".glb", ".gltf")):
        print("RENK-RENDER=YOK sebep=bicim")
        return 2
    rc, satir = render(a.model, a.renk, a.cikti, a.kenar, a.ornek, a.arka, a.dokulu)
    print(satir)
    return rc


if __name__ == "__main__":
    if IN_BLENDER:
        blender_ic(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    else:
        sys.exit(main(sys.argv[1:]))
