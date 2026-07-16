/* PRUVO — kutuphanesiz mini 3D gosterici (sari seri "Onizle (3D)").
   Binary STL'i (Worker'in dondurdugu, istemcide gunzip edilmis ArrayBuffer) saf
   WebGL ile cizer: dondurme (fare/dokunmatik surukleme), yakinlastirma (tekerlek/
   iki parmak), duz (flat) golgeleme. Harici kutuphane YOK (proje kurali).

   Kullanim (urun sayfasi build.py uretir):
     var g = PRUVO_VIEWER.goster(canvasEl, stlArrayBuffer);  // tekrar cagrilabilir
     g.sifirla();  g.yokEt();

   Not: STL zaten yuzey-basina tekrarli kose tasir -> flat shading dogal olarak
   dogru; normal STL'den okunur, sifirsa ucgenden yeniden hesaplanir. */
(function (root) {
  "use strict";

  // ---------------------------------------------------------------- STL cozumu

  function stlCoz(buf) {
    if (!(buf instanceof ArrayBuffer) || buf.byteLength < 84) {
      throw new Error("stl-cok-kucuk");
    }
    var dv = new DataView(buf);
    var adet = dv.getUint32(80, true);
    if (84 + adet * 50 !== buf.byteLength) {
      // ASCII STL veya bozuk govde — Worker binstl uretir, burasi savunma.
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

  var FS = "precision mediump float; varying vec3 vNor;" +
    "void main(){ vec3 n = normalize(vNor);" +
    " float i1 = max(dot(n, normalize(vec3(0.5, 0.7, 0.6))), 0.0);" +
    " float i2 = max(dot(n, normalize(vec3(-0.6, -0.3, 0.4))), 0.0) * 0.35;" +
    // Sari seri kimligi (Okan, 16 Tem): model sitedeki sari rozetle (#f7b500)
    // uyumlu parlak sari. Carpan araligi 0.32..~1.06 tutulur: tavan 1'i ancak
    // en dik acida asar, kanal doygunlasip yuzey detayini yutmaz; 0.32 taban
    // golgeli yuzleri koyu-sari birakir (acik gri zeminle cakismaz).
    " vec3 renk = vec3(0.97, 0.71, 0.03) * (0.32 + 0.60 * i1 + 0.5 * i2);" +
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

  // ---------------------------------------------------------------- gosterici

  var kayitlar = new WeakMap(); // canvas -> durum (ayni canvas'a tekrar yukleme)

  function goster(canvas, stlBuf) {
    var durum = kayitlar.get(canvas);
    if (!durum) {
      var gl = canvas.getContext("webgl", { antialias: true }) ||
               canvas.getContext("experimental-webgl");
      if (!gl) { throw new Error("webgl-yok"); }
      durum = kur(canvas, gl);
      kayitlar.set(canvas, durum);
    }
    durum.yukle(stlCoz(stlBuf));
    return { sifirla: durum.sifirla, yokEt: durum.yokEt };
  }

  function kur(canvas, gl) {
    var prog = derleProgram(gl);
    gl.useProgram(prog);
    gl.enable(gl.DEPTH_TEST);
    var uProj = gl.getUniformLocation(prog, "uProj");
    var uGoruntu = gl.getUniformLocation(prog, "uGoruntu");
    var uDonus = gl.getUniformLocation(prog, "uDonus");
    var aPoz = gl.getAttribLocation(prog, "aPoz");
    var aNor = gl.getAttribLocation(prog, "aNor");
    var pozTampon = gl.createBuffer();
    var norTampon = gl.createBuffer();

    var model = null;         // {adet, merkez, yaricap}
    var yaw = 0.6, pitch = -0.5, zoom = 1;
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
      var uzaklik = model.yaricap * 2.6 / zoom;
      gl.uniformMatrix4fv(uProj, false,
        perspektif(0.7, oran, model.yaricap * 0.01, uzaklik + model.yaricap * 4));
      // goruntu: modeli merkeze tasi + kameradan geri cek
      var goruntu = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                                      0, 0, -uzaklik, 1]);
      gl.uniformMatrix4fv(uGoruntu, false, goruntu);
      // donus: once merkeze otele (donus matrisine sagdan carpilan oteleme)
      var otele = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                                    -model.merkez[0], -model.merkez[1], -model.merkez[2], 1]);
      var donus = mat4Carp(mat4Carp(donusX(pitch), donusY(yaw)), otele);
      gl.uniformMatrix4fv(uDonus, false, donus);
      gl.drawArrays(gl.TRIANGLES, 0, model.adet * 3);
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
      yukle: function (veri) {
        gl.bindBuffer(gl.ARRAY_BUFFER, pozTampon);
        gl.bufferData(gl.ARRAY_BUFFER, veri.poz, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(aPoz);
        gl.vertexAttribPointer(aPoz, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, norTampon);
        gl.bufferData(gl.ARRAY_BUFFER, veri.nor, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(aNor);
        gl.vertexAttribPointer(aNor, 3, gl.FLOAT, false, 0, 0);
        var merkez = [(veri.enKucuk[0] + veri.enBuyuk[0]) / 2,
                      (veri.enKucuk[1] + veri.enBuyuk[1]) / 2,
                      (veri.enKucuk[2] + veri.enBuyuk[2]) / 2];
        var yaricap = Math.max(0.001, Math.hypot(
          veri.enBuyuk[0] - veri.enKucuk[0],
          veri.enBuyuk[1] - veri.enKucuk[1],
          veri.enBuyuk[2] - veri.enKucuk[2]) / 2);
        model = { adet: veri.adet, merkez: merkez, yaricap: yaricap };
        zoom = 1;
        cizPlanla();
      },
      sifirla: function () { yaw = 0.6; pitch = -0.5; zoom = 1; cizPlanla(); },
      yokEt: function () {
        canvas.removeEventListener("pointerdown", pointerDown);
        canvas.removeEventListener("pointermove", pointerMove);
        canvas.removeEventListener("pointerup", pointerUp);
        canvas.removeEventListener("pointercancel", pointerUp);
        canvas.removeEventListener("wheel", tekerlek);
        root.removeEventListener("resize", cizPlanla);
        kayitlar.delete(canvas);
      },
    };
  }

  // ---------------------------------------------------------------- disari

  root.PRUVO_VIEWER = {
    goster: goster,
    // testler icin saf cekirdek
    _stlCoz: stlCoz,
  };
})(typeof window !== "undefined" ? window : globalThis);
