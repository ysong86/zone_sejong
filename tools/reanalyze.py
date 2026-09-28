# -*- coding: utf-8 -*-
"""받아 둔 원자료(data/raw)로 집계만 다시 한다 — 전체 재수집(건축물대장 4만 동, 10분 남짓) 없이.

  python tools/reanalyze.py [--refresh 서비스 ...]
  예) python tools/reanalyze.py --refresh reb     공실률만 새로 받고 나머지는 원자료로

지표 정의·분류를 고친 뒤 결과를 확인할 때 쓴다. 정기 갱신은 run.py --collect --live.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import collect  # noqa: E402

REFRESH = {
    "reb": collect.fetch_vacancy,
    "sgis": collect.fetch_sgis_company,
    "kosis": collect.fetch_commute,
    "neis": collect.fetch_schools,
    "arch": lambda: collect.fetch_permits(collect.load_key()),
    "hs": lambda: collect.fetch_housing(collect.load_key()),
}


def raw(name):
    with open(os.path.join(HERE, "data", "raw", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    fresh = set(argv[argv.index("--refresh") + 1:]) if "--refresh" in argv else set()
    p, a, sb = raw("mois_pop"), raw("mois_age"), raw("sbiz")
    company = REFRESH["sgis"]() if "sgis" in fresh else raw("sgis_company")
    vacancy = REFRESH["reb"]() if "reb" in fresh else raw("reb_vacancy")
    schools = REFRESH["neis"]() if "neis" in fresh else raw("neis")["items"]
    commute = REFRESH["kosis"]() if "kosis" in fresh else None
    permits = REFRESH["arch"]() if "arch" in fresh else (
        raw("permits")["items"] if os.path.exists(os.path.join(HERE, "data", "raw", "permits.json")) else [])
    housing = REFRESH["hs"]() if "hs" in fresh else (
        raw("housing")["items"] if os.path.exists(os.path.join(HERE, "data", "raw", "housing.json")) else [])
    res = collect.analyze(p["ym"], p["now"], p["before"], a["items"], sb["stdrYm"], sb["items"],
                          raw("tago")["items"], raw("rtms")["items"], raw("hira")["items"],
                          raw("kspo")["items"], raw("park")["items"], collect.load_libraries(),
                          raw("bld")["items"], schools, company, vacancy, permits, housing)
    path = os.path.join(HERE, "data", "latest.json")
    with open(path, encoding="utf-8") as f:
        old = json.load(f)
    res["commute"] = commute or old.get("commute")
    res["collected"] = old.get("collected") or dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    res["sources"] = [s for s in collect.LIVE_IND if (s != "arch" or permits) and (s != "hs" or housing)] + (["kosis"] if res["commute"] else [])
    res["live"] = [i for ids in collect.LIVE_IND.values() for i in ids]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("다시 집계:", path)


if __name__ == "__main__":
    main(sys.argv[1:])
