#!/usr/bin/env node
"use strict";

const assert = require("assert");
const { ucEtiketiTuret } = require("./parite-test.js");

assert.strictEqual(
  ucEtiketiTuret("https://pruvo-whatsapp-bot.gmlmz.workers.dev/ara"),
  "/ara Worker (pruvo-bot)"
);
assert.strictEqual(
  ucEtiketiTuret("https://pruvo3d.com/ara"),
  "/ara Worker (pruvo-bot)"
);
assert.strictEqual(ucEtiketiTuret("https://pruvo3d.com/"), "site (Pages)");
assert.strictEqual(ucEtiketiTuret("mailto:x"), "BILINMEYEN UC");

console.log("parite etiket testi: 4/4 GECTI");
