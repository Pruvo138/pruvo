#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K316 teshis — `birak` kapsaminin kaynakta neden 0 kez gectigini OLC."""
import os
import sys
import types

sys.path.insert(0, "/Users/okan/dev/pruvo/tools")
import mutasyon_kopya as MK

KILIT = "/Users/okan/.claude/cron/kilit.py"
with open(KILIT, encoding="utf-8") as f:
    kaynak = f.read()

mod = types.ModuleType("kilit_teshis")
mod.__file__ = KILIT
exec(compile(kaynak, KILIT, "exec"), mod.__dict__)

print("DOSYA_SON_20 = %r" % kaynak[-20:])
for ad in ("karar", "al", "birak"):
    blok = MK.kapsam_kaynagi(mod, ad)
    print("%-8s len=%4d count=%d son=%r" % (ad, len(blok), kaynak.count(blok), blok[-30:]))
