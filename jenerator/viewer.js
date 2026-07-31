/* PRUVO — kutuphanesiz mini 3D gosterici (sari seri "Onizle (3D)").
   Binary kati modeli (Worker'in dondurdugu, istemcide gunzip edilmis ArrayBuffer) saf
   WebGL ile cizer: dondurme (fare/dokunmatik surukleme), yakinlastirma (tekerlek/
   iki parmak), duz (flat) golgeleme. Harici kutuphane YOK (proje kurali).

   Kullanim (urun sayfasini uretec basar):
     var g = PRUVO_VIEWER.goster(canvasEl, stlArrayBuffer);  // tekrar cagrilabilir
     g.sifirla();  g.yokEt();

   COK GOVDELI (2-RENK) GOSTERIM — 29 Tem 2026:
     var g = PRUVO_VIEWER.goster(canvasEl, [
       { buf: govdeStl, renk: [r,g,b] },     // 0. govde: cerceve kabugu
       { buf: yaziStl,  renk: [r,g,b] }      // 1. govde: kabartma yazi (2. malzeme)
     ]);
     g.renkAyarla(rgb)      -> 0. govdenin rengi (eski cagrilar aynen calisir)
     g.renklerAyarla([...])  -> govde basina renk
   Govdeler AYNI koordinat sisteminde gelir (derleyici ayni uretim modelini yalniz `Output`
   farkiyla surer) -> kamera/merkez TUM govdelerin ORTAK kutusundan hesaplanir;
   viewer hicbir govdeyi kaydirmaz/olceklemez (kaydirma = uretimde oturmayan parca).

   Not: bicim zaten yuzey-basina tekrarli kose tasir -> flat shading dogal olarak
   dogru; normal veriden okunur, sifirsa ucgenden yeniden hesaplanir. */
(function (root) {
  "use strict";

  // ------------------------------------------------------- kati model cozumu

  function stlCoz(buf) {
    if (!(buf instanceof ArrayBuffer) || buf.byteLength < 84) {
      throw new Error("stl-cok-kucuk");
    }
    var dv = new DataView(buf);
    var adet = dv.getUint32(80, true);
    if (84 + adet * 50 !== buf.byteLength) {
      // Metin bicimli veya bozuk govde — Worker ikili bicim uretir, burasi savunma.
      throw new Error("stl-binary-degil");
    }
    var poz = new Float32Array(adet * 9);
    var nor = new Float32Array(adet * 9);
    var o = 84;
    var enKucuk = [Infinity, Infinity, Infinity];
    var enBuyuk = [-Infinity, -Infinity, -Infinity];
    for (var i = 0; i < adet; i++) {
      var nx = dv.getFloat32(o, true), ny = dv.getFloat32(o + 4, true), nz = dv.getFloat32(o + 8, true);
      o += 12;
      var taban = i * 9;
      for (var k = 0; k < 3; k++) {
        var x = dv.getFloat32(o, true), y = dv.getFloat32(o + 4, true), z = dv.getFloat32(o + 8, true);
        o += 12;
        poz[taban + k * 3] = x; poz[taban + k * 3 + 1] = y; poz[taban + k * 3 + 2] = z;
        if (x < enKucuk[0]) enKucuk[0] = x; if (x > enBuyuk[0]) enBuyuk[0] = x;
        if (y < enKucuk[1]) enKucuk[1] = y; if (y > enBuyuk[1]) enBuyuk[1] = y;
        if (z < enKucuk[2]) enKucuk[2] = z; if (z > enBuyuk[2]) enBuyuk[2] = z;
      }
      o += 2; // attribute byte count
      if (nx === 0 && ny === 0 && nz === 0) {
        var ax = poz[taban], ay = poz[taban + 1], az = poz[taban + 2];
        var ux = poz[taban + 3] - ax, uy = poz[taban + 4] - ay, uz = poz[taban + 5] - az;
        var vx = poz[taban + 6] - ax, vy = poz[taban + 7] - ay, vz = poz[taban + 8] - az;
        nx = uy * vz - uz * vy; ny = uz * vx - ux * vz; nz = ux * vy - uy * vx;
        var boy = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
        nx /= boy; ny /= boy; nz /= boy;
      }
      for (var m = 0; m < 3; m++) {
        nor[taban + m * 3] = nx; nor[taban + m * 3 + 1] = ny; nor[taban + m * 3 + 2] = nz;
      }
    }
    return { poz: poz, nor: nor, adet: adet, enKucuk: enKucuk, enBuyuk: enBuyuk };
  }

  // ---------------------------------------------------------------- mat4 minik

  function mat4Carp(a, b) {
    var s = new Float32Array(16);
    for (var i = 0; i < 4; i++) {
      for (var j = 0; j < 4; j++) {
        s[j * 4 + i] = a[i] * b[j * 4] + a[4 + i] * b[j * 4 + 1] +
                       a[8 + i] * b[j * 4 + 2] + a[12 + i] * b[j * 4 + 3];
      }
    }
    return s;
  }

  function perspektif(fovy, oran, yakin, uzak) {
    var f = 1 / Math.tan(fovy / 2), nf = 1 / (yakin - uzak);
    return new Float32Array([f / oran, 0, 0, 0, 0, f, 0, 0,
                             0, 0, (uzak + yakin) * nf, -1,
                             0, 0, 2 * uzak * yakin * nf, 0]);
  }

  function donusX(a) {
    var c = Math.cos(a), s = Math.sin(a);
    return new Float32Array([1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]);
  }

  function donusY(a) {
    var c = Math.cos(a), s = Math.sin(a);
    return new Float32Array([c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]);
  }

  // ---------------------------------------------------------------- golgelendirici

  var VS = "attribute vec3 aPoz; attribute vec3 aNor;" +
    "uniform mat4 uProj; uniform mat4 uGoruntu; uniform mat4 uDonus;" +
    "varying vec3 vNor;" +
    "void main(){ vNor = mat3(uDonus[0].xyz, uDonus[1].xyz, uDonus[2].xyz) * aNor;" +
    " gl_Position = uProj * uGoruntu * uDonus * vec4(aPoz, 1.0); }";

  // Taban rengi UNIFORM (uRenk): varsayilan parlak sari (sari seri kimligi, isletme
  // karari 16 Tem — sitedeki sari rozetle #f7b500 uyumlu). Renk disaridan verilebilir
  // (goster(canvas, buf, {renk:[r,g,b]}) — or. musterinin sectigi cerceve rengi).
  var VARSAYILAN_RENK = [0.97, 0.71, 0.03];

  /* ISIK MODELI — TEK KAYNAK. Hem asagidaki GLSL parca golgelendiricisi hem
     JS ikizi golge() BU sayilardan turer; ikinci kopya YOKTUR (iki yerde ayri
     sabit tutulursa biri degisip digeri kalir ve OLCUM gercek ekrandan sapar —
     yazi gorunurlugu tam da bu sayilarla olculuyor).
       taban : ambient — golgeli yuzleri sifira dusurmez (form korunur)
       k1/yon1: ana isik (yumusak lambert)
       k2/yon2: dolgu isigi (ters yondeki yuzler tamamen olmesin)
       kParlak/us: KUCUK GEOMETRIYI GORUNUR KILAN kat (Blinn-Phong benzeri):
         kabartma yazinin 1,2 mm yan duvarlari on yuzle AYNI normale sahip
         DEGILDIR, ama sadece lambert'te ikisi de koyu renkte 15/255 seviyede
         ayrisiyordu = musteri yaziyi goremiyordu (29 Tem olcumu). Parlaklik
         terimi acisal farki cok daha genis bir araliga yayar. Renk DEGISTIRMEZ
         (uretilecek urun tek renk kalir) — yalniz isik. */
  var ISIK = {
    taban: 0.32,
    yon1: [0.5, 0.7, 0.6], k1: 0.60,
    yon2: [-0.6, -0.3, 0.4], k2: 0.175,
    yonParlak: [0.35, 0.45, 0.82], kParlak: 0.55, us: 14
  };

  function birim(v) {
    var b = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) || 1;
    return [v[0] / b, v[1] / b, v[2] / b];
  }

  function glsayi(x) {
    var s = String(x);
    return (s.indexOf(".") < 0 && s.indexOf("e") < 0) ? (s + ".0") : s;
  }

  function glvec(v) {
    return "vec3(" + glsayi(v[0]) + ", " + glsayi(v[1]) + ", " + glsayi(v[2]) + ")";
  }

  // Isik carpani (0..~1.6): JS ikizi. GLSL ile AYNI ISIK sayilarindan hesaplar.
  function carpan(n) {
    var b = birim(n);
    var l1 = birim(ISIK.yon1), l2 = birim(ISIK.yon2), lp = birim(ISIK.yonParlak);
    var i1 = Math.max(b[0] * l1[0] + b[1] * l1[1] + b[2] * l1[2], 0);
    var i2 = Math.max(b[0] * l2[0] + b[1] * l2[1] + b[2] * l2[2], 0);
    var ip = Math.max(b[0] * lp[0] + b[1] * lp[1] + b[2] * lp[2], 0);
    return ISIK.taban + ISIK.k1 * i1 + ISIK.k2 * i2 +
           ISIK.kParlak * Math.pow(ip, ISIK.us);
  }

  // Ekranda gorunecek 0..1 RGB (ekran kirpmasi dahil) — testler bunu olcer.
  function golge(n, renk) {
    var c = carpan(n), r = renk || VARSAYILAN_RENK;
    return [Math.min(1, r[0] * c), Math.min(1, r[1] * c), Math.min(1, r[2] * c)];
  }

  var FS = "precision mediump float; varying vec3 vNor; uniform vec3 uRenk;" +
    "void main(){ vec3 n = normalize(vNor);" +
    " float i1 = max(dot(n, normalize(" + glvec(ISIK.yon1) + ")), 0.0);" +
    " float i2 = max(dot(n, normalize(" + glvec(ISIK.yon2) + ")), 0.0);" +
    " float ip = max(dot(n, normalize(" + glvec(ISIK.yonParlak) + ")), 0.0);" +
    // Taban golgeli yuzleri koyu ama sifir-olmayan birakir (acik gri zeminle
    // cakismaz); parlaklik terimi kabartma kenarlarini one cikarir.
    " vec3 renk = uRenk * (" + glsayi(ISIK.taban) +
    " + " + glsayi(ISIK.k1) + " * i1" +
    " + " + glsayi(ISIK.k2) + " * i2" +
    " + " + glsayi(ISIK.kParlak) + " * pow(ip, " + glsayi(ISIK.us) + "));" +
    " gl_FragColor = vec4(renk, 1.0); }";

  function derleProgram(gl) {
    function derle(tip, kaynak) {
      var g = gl.createShader(tip);
      gl.shaderSource(g, kaynak);
      gl.compileShader(g);
      if (!gl.getShaderParameter(g, gl.COMPILE_STATUS)) {
        throw new Error("shader: " + gl.getShaderInfoLog(g));
      }
      return g;
    }
    var prog = gl.createProgram();
    gl.attachShader(prog, derle(gl.VERTEX_SHADER, VS));
    gl.attachShader(prog, derle(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      throw new Error("program: " + gl.getProgramInfoLog(prog));
    }
    return prog;
  }

  // ---------------------------------------------------------------- kamera (saf)

  var BASLANGIC = { yaw: 0.6, pitch: -0.5, zoom: 1 };
  var FOV = 0.7;
  var UZAKLIK_KAT = 2.6;

  /* Cizim matrisleri — SAF. ciz() bunu cagirir, olcum testi de AYNI fonksiyonu
     cagirir (kamera matematiginin ikinci kopyasi YOK: kopya olsaydi "yazi
     goruluyor" olcumu gercek ekrandan sessizce ayrisirdi). */
  function gorunum(model, oran, yaw, pitch, zoom) {
    var uzaklik = model.yaricap * UZAKLIK_KAT / zoom;
    var proj = perspektif(FOV, oran, model.yaricap * 0.01,
                          uzaklik + model.yaricap * 4);
    var goruntu = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                                    0, 0, -uzaklik, 1]);
    // once merkeze otele (donus matrisine sagdan carpilan oteleme)
    var otele = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                                  -model.merkez[0], -model.merkez[1], -model.merkez[2], 1]);
    var donus = mat4Carp(mat4Carp(donusX(pitch), donusY(yaw)), otele);
    return { proj: proj, goruntu: goruntu, donus: donus, uzaklik: uzaklik };
  }

  // ---------------------------------------------------------------- gosterici

  var kayitlar = new WeakMap(); // canvas -> durum (ayni canvas'a tekrar yukleme)

  /* Girdiyi TEK BICIME indirger: [{buf, renk}]. Iki cagri bicimi de desteklenir —
     goster(canvas, arrayBuffer, {renk})           (eski, TEK govde)
     goster(canvas, [{buf,renk},{buf,renk}])       (yeni, COK govde / 2 renk)
     Eski bicimin davranisi HARFI HARFINE korunur (renk verilmezse sari seri). */
  function govdeleriCoz(girdi, secenek) {
    if (Array.isArray(girdi)) {
      if (!girdi.length) { throw new Error("govde-yok"); }
      return girdi.map(function (g) {
        var r = g && g.renk;
        return { buf: g.buf, renk: (r && r.length === 3) ? r : VARSAYILAN_RENK };
      });
    }
    var renk = secenek && secenek.renk;
    return [{ buf: girdi, renk: (renk && renk.length === 3) ? renk : VARSAYILAN_RENK }];
  }

  function goster(canvas, girdi, secenek) {
    var durum = kayitlar.get(canvas);
    if (!durum) {
      var gl = canvas.getContext("webgl", { antialias: true }) ||
               canvas.getContext("experimental-webgl");
      if (!gl) { throw new Error("webgl-yok"); }
      durum = kur(canvas, gl);
      kayitlar.set(canvas, durum);
    }
    var govdeler = govdeleriCoz(girdi, secenek);
    durum.yukle(govdeler.map(function (g) { return stlCoz(g.buf); }));
    durum.renklerAyarla(govdeler.map(function (g) { return g.renk; }));
    // renkAyarla disari VERILIR: musteri Renk secimini degistirince sayfa modeli
    // YENIDEN INDIRMEDEN boyayabilsin (yeniden indirme derleyici kotasini yerdi
    // ve secim degisimi sessizce etkisiz kalirdi). renklerAyarla ayni isi cok
    // govdede yapar (govde rengi + yazi rengi ayri ayri).
    return { sifirla: durum.sifirla, yokEt: durum.yokEt,
             renkAyarla: durum.renkAyarla, renklerAyarla: durum.renklerAyarla };
  }

  function kur(canvas, gl) {
    var prog = derleProgram(gl);
    gl.useProgram(prog);
    gl.enable(gl.DEPTH_TEST);
    var uProj = gl.getUniformLocation(prog, "uProj");
    var uGoruntu = gl.getUniformLocation(prog, "uGoruntu");
    var uDonus = gl.getUniformLocation(prog, "uDonus");
    var uRenk = gl.getUniformLocation(prog, "uRenk");
    var aPoz = gl.getAttribLocation(prog, "aPoz");
    var aNor = gl.getAttribLocation(prog, "aNor");
    // GOVDE BASINA tampon cifti: cok govdeli (2-renk) urunde her govde kendi
    // VBO'suna yuklenir ve kendi uRenk'i ile cizilir.
    var govdeler = [];        // [{poz, nor, adet}]
    var model = null;         // {merkez, yaricap} — TUM govdelerin ORTAK kutusu
    var renkler = [VARSAYILAN_RENK];  // govde basina taban renk
    var yaw = BASLANGIC.yaw, pitch = BASLANGIC.pitch, zoom = BASLANGIC.zoom;
    var cizimIste = null;

    function boyutla() {
      var oran = root.devicePixelRatio || 1;
      var w = Math.max(1, Math.round(canvas.clientWidth * oran));
      var h = Math.max(1, Math.round(canvas.clientHeight * oran));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w; canvas.height = h;
      }
      gl.viewport(0, 0, w, h);
    }

    function ciz() {
      if (!model) { return; }
      boyutla();
      gl.clearColor(0.956, 0.965, 0.973, 1); // sayfanin acik gri zemini (#f4f6f8)
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      var oran = canvas.width / canvas.height;
      var g = gorunum(model, oran, yaw, pitch, zoom);
      gl.uniformMatrix4fv(uProj, false, g.proj);
      gl.uniformMatrix4fv(uGoruntu, false, g.goruntu);
      gl.uniformMatrix4fv(uDonus, false, g.donus);
      for (var i = 0; i < govdeler.length; i++) {
        var t = govdeler[i];
        gl.bindBuffer(gl.ARRAY_BUFFER, t.poz);
        gl.enableVertexAttribArray(aPoz);
        gl.vertexAttribPointer(aPoz, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, t.nor);
        gl.enableVertexAttribArray(aNor);
        gl.vertexAttribPointer(aNor, 3, gl.FLOAT, false, 0, 0);
        // Rengi olmayan govde 0. govdenin rengine DUSMEZ: kendi varsayilanini alir.
        gl.uniform3fv(uRenk, renkler[i] || VARSAYILAN_RENK);
        gl.drawArrays(gl.TRIANGLES, 0, t.adet * 3);
      }
    }

    function cizPlanla() {
      if (cizimIste) { return; }
      cizimIste = root.requestAnimationFrame(function () { cizimIste = null; ciz(); });
    }

    // ---- etkilesim: pointer olaylari (fare + dokunmatik tek yoldan) ----
    var parmaklar = new Map(); // pointerId -> {x, y}
    var sonMesafe = 0;

    function pointerDown(e) {
      parmaklar.set(e.pointerId, { x: e.clientX, y: e.clientY });
      canvas.setPointerCapture && canvas.setPointerCapture(e.pointerId);
      if (parmaklar.size === 2) {
        var ikisi = [...parmaklar.values()];
        sonMesafe = Math.hypot(ikisi[0].x - ikisi[1].x, ikisi[0].y - ikisi[1].y);
      }
      e.preventDefault();
    }

    function pointerMove(e) {
      var onceki = parmaklar.get(e.pointerId);
      if (!onceki) { return; }
      var yeni = { x: e.clientX, y: e.clientY };
      parmaklar.set(e.pointerId, yeni);
      if (parmaklar.size === 1) {
        yaw += (yeni.x - onceki.x) * 0.011;
        pitch += (yeni.y - onceki.y) * 0.011;
        pitch = Math.max(-1.55, Math.min(1.55, pitch));
        cizPlanla();
      } else if (parmaklar.size === 2) {
        var ikisi = [...parmaklar.values()];
        var mesafe = Math.hypot(ikisi[0].x - ikisi[1].x, ikisi[0].y - ikisi[1].y);
        if (sonMesafe > 0) {
          zoom = Math.max(0.3, Math.min(8, zoom * (mesafe / sonMesafe)));
          cizPlanla();
        }
        sonMesafe = mesafe;
      }
      e.preventDefault();
    }

    function pointerUp(e) {
      parmaklar.delete(e.pointerId);
      sonMesafe = 0;
    }

    function tekerlek(e) {
      zoom = Math.max(0.3, Math.min(8, zoom * (e.deltaY < 0 ? 1.12 : 0.89)));
      cizPlanla();
      e.preventDefault();
    }

    canvas.style.touchAction = "none";
    canvas.style.cursor = "grab";
    canvas.addEventListener("pointerdown", pointerDown);
    canvas.addEventListener("pointermove", pointerMove);
    canvas.addEventListener("pointerup", pointerUp);
    canvas.addEventListener("pointercancel", pointerUp);
    canvas.addEventListener("wheel", tekerlek, { passive: false });
    root.addEventListener("resize", cizPlanla);

    return {
      // Eski sozlesme: TEK renk = 0. govdenin (cerceve kabugu) rengi.
      renkAyarla: function (r) { renkler[0] = r; cizPlanla(); },
      renklerAyarla: function (dizi) {
        renkler = (dizi && dizi.length) ? dizi.slice() : [VARSAYILAN_RENK];
        cizPlanla();
      },
      /** veriler: stlCoz ciktisi ya da bunlarin DIZISI (cok govdeli 2-renk urun). */
      yukle: function (veriler) {
        var liste = Array.isArray(veriler) ? veriler : [veriler];
        for (var e = 0; e < govdeler.length; e++) {
          gl.deleteBuffer(govdeler[e].poz);
          gl.deleteBuffer(govdeler[e].nor);
        }
        govdeler = [];
        // ORTAK kutu: govdeler AYNI koordinat sisteminde oldugu icin kamera tum
        // parcalari birlikte cerceveler; hicbir govde tek basina merkezlenmez
        // (merkezleme yapilsaydi yazi cerceveden KAYARDI = uretimde oturmayan parca).
        var az = [Infinity, Infinity, Infinity], cok = [-Infinity, -Infinity, -Infinity];
        for (var i = 0; i < liste.length; i++) {
          var veri = liste[i];
          var poz = gl.createBuffer(), nor = gl.createBuffer();
          gl.bindBuffer(gl.ARRAY_BUFFER, poz);
          gl.bufferData(gl.ARRAY_BUFFER, veri.poz, gl.STATIC_DRAW);
          gl.bindBuffer(gl.ARRAY_BUFFER, nor);
          gl.bufferData(gl.ARRAY_BUFFER, veri.nor, gl.STATIC_DRAW);
          govdeler.push({ poz: poz, nor: nor, adet: veri.adet });
          for (var k = 0; k < 3; k++) {
            if (veri.enKucuk[k] < az[k]) { az[k] = veri.enKucuk[k]; }
            if (veri.enBuyuk[k] > cok[k]) { cok[k] = veri.enBuyuk[k]; }
          }
        }
        var merkez = [(az[0] + cok[0]) / 2, (az[1] + cok[1]) / 2, (az[2] + cok[2]) / 2];
        var yaricap = Math.max(0.001, Math.hypot(cok[0] - az[0], cok[1] - az[1],
                                                 cok[2] - az[2]) / 2);
        model = { merkez: merkez, yaricap: yaricap };
        zoom = BASLANGIC.zoom;
        cizPlanla();
      },
      sifirla: function () {
        yaw = BASLANGIC.yaw; pitch = BASLANGIC.pitch; zoom = BASLANGIC.zoom;
        cizPlanla();
      },
      yokEt: function () {
        canvas.removeEventListener("pointerdown", pointerDown);
        canvas.removeEventListener("pointermove", pointerMove);
        canvas.removeEventListener("pointerup", pointerUp);
        canvas.removeEventListener("pointercancel", pointerUp);
        canvas.removeEventListener("wheel", tekerlek);
        root.removeEventListener("resize", cizPlanla);
        for (var e = 0; e < govdeler.length; e++) {
          gl.deleteBuffer(govdeler[e].poz);
          gl.deleteBuffer(govdeler[e].nor);
        }
        govdeler = [];
        kayitlar.delete(canvas);
      },
    };
  }

  // ---------------------------------------------------------------- disari

  var API = {
    goster: goster,
    // testler icin saf cekirdek — ekranda gorunen sonucun AYNI matematigi
    // (kopya yok): olcum bunlari cagirir.
    _stlCoz: stlCoz,
    _gorunum: gorunum,
    _golge: golge,
    _carpan: carpan,
    _ISIK: ISIK,
    _FS: FS,
    _BASLANGIC: BASLANGIC,
    _VARSAYILAN_RENK: VARSAYILAN_RENK,
    _govdeleriCoz: govdeleriCoz,
  };
  root.PRUVO_VIEWER = API;
  if (typeof module === "object" && module.exports) { module.exports = API; }
})(typeof window !== "undefined" ? window : globalThis);
