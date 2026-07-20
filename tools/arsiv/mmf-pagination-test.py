#!/usr/bin/env python3
"""MMF pagination regression testi.

Kapsam:
  - `tools/myminifactory-ara.py` icindeki tek satirlik off-by-one fix
  - total'in PER'e TAM bolunmedigi durumda son kismi da fetch edilir
  - eski kosulun (`page * PER > total`) 151-171 araligini dusurdugu kanitlanir
  - total PER'e TAM bolundugunde fazladan sayfa fetch edilmez

Kosum: `python3 tools/mmf-pagination-test.py`
"""
import contextlib
import importlib.util
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PER = 30
TERM = "zeta"


def _load():
    spec = importlib.util.spec_from_file_location(
        "myminifactory_ara", os.path.join(_HERE, "myminifactory-ara.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _idler(stdout):
    lines = stdout.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("IDLER"):
            return lines[i + 1].split() if i + 1 < len(lines) else []
    return []


def _mock_case(ara, total):
    pool = [
        {
            "id": 90000000 + i,
            "name": "Zeta bracket %d" % i,
            "url": "https://www.myminifactory.com/object/zeta-bracket-%d" % i,
            "tags": ["zeta"],
            "license": "BY",
            "licenses": None,
            "views": 0,
            "likes": 0,
        }
        for i in range(total)
    ]
    calls = []

    def search(term, per_page=30, page=1):
        assert term == TERM, term
        assert per_page == PER, per_page
        calls.append(page)
        start = (page - 1) * per_page
        return {"total_count": total, "items": pool[start:start + per_page]}

    ara.mmf.search = search
    ara.mmf.require_key = lambda: "TEST"
    ara.mevcut_idler = lambda: set()
    return calls


def _run_main(ara, total):
    calls = _mock_case(ara, total)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ara.main(TERM, 10 ** 9, derin=False)
    out = buf.getvalue()
    ids = _idler(out)
    return calls, ids, out


def _old_condition_count(total):
    page = 1
    count = 0
    while True:
        start = (page - 1) * PER
        if start >= total:
            break
        count += min(PER, total - start)
        page += 1
        if total and page * PER > total:
            break
    return count


def _check_partial(ara):
    calls, ids, _ = _run_main(ara, 171)
    old_count = _old_condition_count(171)
    assert len(calls) == 6, calls
    assert calls == [1, 2, 3, 4, 5, 6], calls
    assert len(ids) == 171, len(ids)
    assert old_count == 150, old_count
    print("ok partial 171/30: fetch=%d pages=%s ids=%d old=%d" % (len(calls), calls, len(ids), old_count))


def _check_exact(ara):
    calls, ids, _ = _run_main(ara, 180)
    old_count = _old_condition_count(180)
    assert len(calls) == 6, calls
    assert calls == [1, 2, 3, 4, 5, 6], calls
    assert len(ids) == 180, len(ids)
    assert old_count == 180, old_count
    print("ok exact   180/30: fetch=%d pages=%s ids=%d old=%d" % (len(calls), calls, len(ids), old_count))


def main():
    ara = _load()
    _check_partial(ara)
    _check_exact(ara)
    print("2/2 GECTI — MMF pagination fix: son kismi fetch eder, exact-multiple'i bozmaz.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("BASARISIZ:", e)
        sys.exit(1)
