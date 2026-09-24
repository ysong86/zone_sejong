# -*- coding: utf-8 -*-
"""지식(livingzone.py) + 경계(assets) + 수집값(data/latest.json) → dashboard.html 한 파일."""
from __future__ import annotations

import datetime as dt
import json
import os

import livingzone as LZ

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

ANCHOR_KINDS = {
    "national": {"name": "국가중추기능", "color": "#6C2E86", "diamond": True},
    "city": {"name": "도시행정·부도심", "color": "#2F6DB5"},
    "center": {"name": "광역 상업중심", "color": "#C8475A"},
    "knowledge": {"name": "대학·연구", "color": "#1E8C84"},
    "medical": {"name": "상급 의료", "color": "#D08A1E"},
    "smart": {"name": "스마트시티 시범", "color": "#4E8F3A"},
    "industry": {"name": "산업단지", "color": "#7D6B4A"},
    "transport": {"name": "고속철도 관문", "color": "#3B4652"},
}
TYPE_NAMES = {"keep": "유지·고도화", "boost": "보강", "shift": "전환·재정의"}
API_STATUS = {
    "403": {"name": "활용신청 필요", "cls": "s403"},
    "todo": {"name": "주소 확인 전", "cls": "stodo"},
    "key": {"name": "별도 인증키", "cls": "skey"},
    "file": {"name": "파일 제공", "cls": "sfile"},
    "ok": {"name": "연동됨", "cls": "sok"},
}
ROAD_CLASSES = ("expressway", "brt", "arterial")
PROBED = "2026-09-24"


def _load(name):
    with open(os.path.join(ASSETS, name), encoding="utf-8") as f:
        return json.load(f)


def _roads():
    out = []
    for r in _load("sejong_roads.json")["roads"]:
        if r["cls"] not in ROAD_CLASSES:
            continue
        lines = [[[round(x, 5), round(y, 5)] for x, y in line] for line in r["lines"]]
        out.append({"name": r["name"], "cls": r["cls"], "lines": lines})
    return out


def _collected():
    """data/latest.json 의 실측으로 샘플을 덮는다. 없으면 None."""
    path = os.path.join(HERE, "data", "latest.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_data(demo: bool = True) -> dict:
    units = LZ.sample_units()
    apis = [dict(a) for a in LZ.APIS]
    asof, live_ind, counts, collected = {}, [], {}, None
    got = None if demo else _collected()
    if got:
        live_ind = got.get("live", [])
        for name, vals in got.get("units", {}).items():
            if name in units:
                # 실측 지표는 값이 없어도(None) 샘플을 남기지 않는다 — 빈칸이 정직하다.
                for k in live_ind:
                    units[name][k] = vals.get(k)
                for k in ("stores", "docs", "apt_n", "built"):
                    if k in vals:
                        units[name][k] = vals[k]
        live = set(got.get("sources", []))
        for a in apis:
            if a["id"] in live:
                a["status"] = "ok"
        asof, counts, collected = got.get("asof", {}), got.get("counts", {}), got.get("collected")
    admin_meta = {a["name"]: {"note": a.get("note", ""), "span": a.get("span"), "legal": a["legal"]}
                  for a in LZ.ADMIN}
    for n, m in admin_meta.items():
        units[n].update(m)
    geo = _load("sejong_units.json")
    zones = _load("sejong_zones.json")["zones"]
    return {
        "meta": {"demo": not got, "built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                 "asof": asof, "probed": PROBED, "live": live_ind, "counts": counts,
                 "collected": collected},
        "axes": LZ.AXES,
        "zones": LZ.ZONES,
        "indicators": LZ.INDICATORS,
        "units": units,
        "shapes": geo["units"],
        "outline": geo["outline"],
        "zoneShapes": zones,
        "roads": _roads(),
        "anchors": LZ.ANCHORS,
        "anchorKinds": ANCHOR_KINDS,
        "flows": LZ.FLOWS,
        "external": LZ.EXTERNAL,
        "externalSplit": LZ.EXTERNAL_SPLIT,
        "functions": LZ.FUNCTIONS,
        "planned": LZ.PLANNED,
        "lq": LZ.LQ,
        "diagnosis": LZ.DIAGNOSIS,
        "typeNames": TYPE_NAMES,
        "theory": LZ.THEORY,
        "strategy": LZ.STRATEGY,
        "cases": LZ.CASES,
        "apis": apis,
        "apiStatus": API_STATUS,
    }


def render(out_path: str, demo: bool = True) -> str:
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        tpl = f.read()
    data = json.dumps(build_data(demo), ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/")      # <script> 안에서 닫는 태그로 읽히지 않게
    html = tpl.replace("/*__DATA__*/null", data)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
