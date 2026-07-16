/* dogrula.py yardimcisi: stdin'den {"fonksiyon":"oring","setler":[{...},...]} okur,
   jenerator/hacim.js'i yukler, her set icin hacmi (mm3) JSON dizisi olarak basar.
   Hata durumunda stderr'e mesaj, cikis kodu 1. */
"use strict";
var path = require("path");
var HACIM = require(path.join(__dirname, "..", "hacim.js"));

var ham = "";
process.stdin.on("data", function (d) { ham += d; });
process.stdin.on("end", function () {
  var istek;
  try { istek = JSON.parse(ham); }
  catch (e) { console.error("gecersiz JSON: " + e.message); process.exit(1); }
  var fn = HACIM[istek.fonksiyon];
  if (typeof fn !== "function") {
    console.error("hacim.js icinde fonksiyon yok: " + istek.fonksiyon);
    process.exit(1);
  }
  var sonuc = [];
  for (var i = 0; i < istek.setler.length; i++) {
    var h = fn(istek.setler[i]);
    if (typeof h !== "number" || !isFinite(h) || h <= 0) {
      console.error("set " + i + " icin gecersiz hacim: " + h);
      process.exit(1);
    }
    sonuc.push(h);
  }
  process.stdout.write(JSON.stringify(sonuc));
});
