# -*- coding: utf-8 -*-
"""읍면동 경계(assets/sejong_admin.json) → 생활권 경계(assets/sejong_zones.json).

행복도시 6개 생활권 + S생활권(국가상징구역) + 읍면 지역을
구성 동의 합집합으로 만든다. 한 번만 돌리면 되는 빌드 도구라 shapely 를 쓴다.

  python tools/make_zones.py

OSM 경계에는 어진동(1-5)·가람동(S)이 따로 없다. 어진동은 도담동 면에,
가람동은 한솔동 면에 들어 있다고 보고 묶는다(zones 의 note 참고).
"""
from __future__ import annotations

import json
import os
import sys

from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from livingzone import ZONES  # noqa: E402

SRC = os.path.join(HERE, "assets", "sejong_admin.json")
OUT = os.path.join(HERE, "assets", "sejong_zones.json")


def to_poly(rings):
    polys = []
    for ring in rings:
        if len(ring) >= 4:
            p = Polygon(ring)
            if not p.is_valid:
                p = p.buffer(0)
            polys.append(p)
    return unary_union(polys)


def rings_of(geom, eps=0.00008):
    geom = geom.simplify(eps)
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    out = []
    for p in polys:
        if p.area <= 2e-7:
            continue
        # 구멍(interior)도 같은 목록에 넣는다 — 화면은 evenodd 로 칠한다.
        for ring in [p.exterior, *p.interiors]:
            if len(ring.coords) >= 4:
                out.append([[round(x, 6), round(y, 6)] for x, y in ring.coords])
    return out


def clean_units(admin):
    """나성동·세종동처럼 OSM 외곽링만 남아 행복도시 전체를 덮는 면을 바로잡는다.

    작은 면부터 차례로 확정하고, 큰 면에서는 이미 확정된 작은 면을 뺀다.
    겹침이 없는 정상 면에는 아무 일도 일어나지 않는다.
    """
    items = sorted(((d["name"], d["kind"], to_poly(d["rings"])) for d in admin["dongs"]),
                   key=lambda t: t[2].area)
    done = {}
    for name, kind, geom in items:
        taken = unary_union(list(done.values())) if done else None
        if taken is not None and geom.intersects(taken):
            geom = geom.difference(taken.buffer(0.00005))
        done[name] = geom
    return {n: g for n, g in done.items()}, {d["name"]: d["kind"] for d in admin["dongs"]}


def main():
    admin = json.load(open(SRC, encoding="utf-8"))
    shapes, kinds = clean_units(admin)
    units = []
    for name, g in shapes.items():
        p = g.representative_point() if g.area < 0.0008 or name in ("나성동", "세종동") else g.centroid
        if not g.contains(p):
            p = g.representative_point()
        units.append({"name": name, "kind": kinds[name], "rings": rings_of(g),
                      "label": [round(p.x, 6), round(p.y, 6)],
                      "km2": round(g.area * 111.0 * 111.0 * 0.8036, 2)})
        print(f"{name:6s} {units[-1]['km2']:8.2f} km2  label {units[-1]['label']}")
    json.dump({"_source": "OSM 행정경계(sejong_admin.json)를 겹침 정리한 것(tools/make_zones.py)",
               "outline": admin["outline"], "units": units},
              open(os.path.join(HERE, "assets", "sejong_units.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    out = []
    for z in ZONES:
        geoms = [shapes[n] for n in z["units"] if n in shapes]
        missing = [n for n in z["units"] if n not in shapes]
        if missing:
            print("경계 없음:", z["id"], missing)
        # 단순화 오차로 이웃 면 사이에 틈이 남으므로 살짝 불렸다 되돌린다(약 30m).
        u = unary_union([g.buffer(0.0003) for g in geoms]).buffer(-0.0003)
        u = u.simplify(0.00012)
        polys = list(u.geoms) if isinstance(u, MultiPolygon) else [u]
        rings = [[[round(x, 6), round(y, 6)] for x, y in p.exterior.coords]
                 for p in polys if p.area > 1e-6]
        c = u.representative_point() if z["id"] in ("R", "S") else u.centroid
        out.append({"id": z["id"], "rings": rings,
                    "label": [round(c.x, 6), round(c.y, 6)]})
    json.dump({"_source": "sejong_admin.json 의 동 경계를 합친 것(tools/make_zones.py)",
               "zones": out}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print("저장:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
