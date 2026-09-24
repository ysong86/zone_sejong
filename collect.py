# -*- coding: utf-8 -*-
"""공공데이터포털 API 타진·수집·행정동 집계.

  probe()    서비스별 상태 코드(403 = 주소 맞음·활용신청 필요 / 200 = 됨)
  collect()  승인된 서비스를 받아 data/raw/ 에 원 응답을 남기고,
             행정동 단위로 집계해 data/latest.json 을 쓴다.

지금 붙어 있는 것(2026-09-24): 행안부 인구·세대, 행안부 성·연령별 인구,
소상공인 상가정보, TAGO 버스정류소, 국토부 아파트 매매 실거래가,
심평원 병원정보, 체육진흥공단 전국체육시설.

점포·정류장은 좌표로 행정동 면에 넣는다(점포 자료의 행정동명은 분동 전
기준이라 집현동이 없다). 지도에 거주 위치가 없으므로 '시가지 격자점' —
행정동 면 안의 120m 격자 가운데 점포나 정류장 300m 안에 드는 점 — 을
주민이 사는 곳의 대용으로 쓴다.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
LATEST = os.path.join(HERE, "data", "latest.json")

PROBES = {
    "mois_pop": "https://apis.data.go.kr/1741000/admmPpltnHhStus/selectAdmmPpltnHhStus"
                "?serviceKey={k}&admmCd=3611000000&srchFrYm={ym}&srchToYm={ym}&lv=3&regSeCd=1"
                "&type=JSON&numOfRows=100&pageNo=1",
    "mois_age": "https://apis.data.go.kr/1741000/admmSexdAgePpltn/selectAdmmSexdAgePpltn"
                "?serviceKey={k}&admmCd=3611000000&srchFrYm={ym}&srchToYm={ym}&lv=3&regSeCd=1"
                "&type=JSON&numOfRows=100&pageNo=1",
    "sbiz": "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
            "?serviceKey={k}&divId=signguCd&key=36110&type=json&numOfRows=1000&pageNo={page}",
    "tago": "https://apis.data.go.kr/1613000/BusSttnInfoInqireService/getSttnNoList"
            "?serviceKey={k}&cityCode=12&_type=json&numOfRows=1000&pageNo={page}",
    "rtms": "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
            "?serviceKey={k}&LAWD_CD=36110&DEAL_YMD={ym}&numOfRows=1000&pageNo={page}&_type=json",
    "hira": "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
            "?serviceKey={k}&sidoCd=410000&_type=json&numOfRows=1000&pageNo={page}",
    "kspo": "https://apis.data.go.kr/B551014/SRVC_API_SFMS_FACI/TODZ_API_SFMS_FACI"
            "?serviceKey={k}&resultType=json&numOfRows=500&pageNo={page}"
            "&cp_nm=%EC%84%B8%EC%A2%85%ED%8A%B9%EB%B3%84%EC%9E%90%EC%B9%98%EC%8B%9C",
    "park": "https://apis.data.go.kr/5690000/sjParkStat/sj_00000290"
            "?serviceKey={k}&pageIndex={page}&pageUnit=200&dataTy=json",
}


# ── 공통 ──────────────────────────────────────────────────────────────
def load_key() -> str:
    path = os.path.join(HERE, "config.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            key = json.load(f).get("portal_key", "")
        if key:
            return key
    return os.environ.get("DATA_GO_KR_KEY", "")


def _q(key):
    return urllib.parse.quote(key, safe="")


def _ym(months_back: int) -> str:
    d = dt.date.today().replace(day=1)
    for _ in range(months_back):
        d = (d - dt.timedelta(days=1)).replace(day=1)
    return d.strftime("%Y%m")


def _shift(ym: str, months: int) -> str:
    y, m = int(ym[:4]), int(ym[4:])
    m += months
    while m <= 0:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return f"{y}{m:02d}"


def _get(url: str, timeout: int = 60):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode()


def _json(url, tries=4):
    """포털은 가끔 타임아웃이나 빈 본문을 준다. 몇 번 다시 시도한다."""
    import time
    last = None
    for i in range(tries):
        code, body = _get(url)
        if code == 200:
            try:
                return json.loads(body)
            except ValueError:
                last = "JSON 아님: " + body[:80].decode("utf-8", "replace")
        else:
            last = f"HTTP {code}"
            if code in (401, 403):
                break
        time.sleep(2 * (i + 1))
    raise RuntimeError(last)


def _save_raw(name, obj):
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def probe(only=None) -> dict:
    key = load_key()
    if not key:
        print("인증키가 없습니다. config.json 의 portal_key 를 채우십시오.")
        return {}
    res = {}
    for name, tpl in PROBES.items():
        if only and name not in only:
            continue
        code, body = _get(tpl.format(k=_q(key), ym=_ym(2), page=1))
        head = body[:160].decode("utf-8", "replace").replace("\n", " ")
        meaning = {200: "됨", 403: "주소 맞음 · 활용신청 필요", 400: "주소·파라미터 틀림",
                   401: "키 오류", 404: "주소 없음"}.get(code, "확인 필요")
        print(f"{name:9s} {code}  {meaning}   {head[:80]}")
        res[name] = code
    return res


# ── 받기 ──────────────────────────────────────────────────────────────
def _mois(service, oper, key, ym):
    url = (f"https://apis.data.go.kr/1741000/{service}/{oper}?serviceKey={_q(key)}"
           f"&admmCd=3611000000&srchFrYm={ym}&srchToYm={ym}&lv=3&regSeCd=1&type=JSON"
           f"&numOfRows=100&pageNo=1")
    d = _json(url)["Response"]
    if d["head"]["resultCode"] != "0":
        return []
    items = d["items"]["item"] if d.get("items") else []
    return [items] if isinstance(items, dict) else items


def fetch_population(key):
    """가장 최근 달과 12개월 전. 이번 달 자료는 다음 달 초에 올라오므로 거슬러 찾는다."""
    for back in range(1, 5):
        ym = _ym(back)
        now = _mois("admmPpltnHhStus", "selectAdmmPpltnHhStus", key, ym)
        if now:
            break
    else:
        raise RuntimeError("최근 4개월 인구 자료 없음")
    before = _mois("admmPpltnHhStus", "selectAdmmPpltnHhStus", key, _shift(ym, -12))
    age = _mois("admmSexdAgePpltn", "selectAdmmSexdAgePpltn", key, ym)
    _save_raw("mois_pop", {"ym": ym, "now": now, "before": before})
    _save_raw("mois_age", {"ym": ym, "items": age})
    return ym, now, before, age


def _paged(tpl, key, pick, **kw):
    items, page = [], 1
    while True:
        d = _json(tpl.format(k=_q(key), page=page, **kw))
        got, total = pick(d)
        items += got
        if not got or len(items) >= total:
            return items, d
        page += 1


def fetch_stores(key):
    def pick(d):
        b = d["body"]
        return b.get("items") or [], int(b.get("totalCount", 0))
    items, last = _paged(PROBES["sbiz"], key, pick)
    ym = last["header"].get("stdrYm")
    _save_raw("sbiz", {"stdrYm": ym, "items": items})
    return ym, items


def fetch_stops(key):
    def pick(d):
        b = d["response"]["body"]
        it = (b["items"].get("item") or []) if isinstance(b.get("items"), dict) else []
        return ([it] if isinstance(it, dict) else it), int(b.get("totalCount", 0))
    items, _ = _paged(PROBES["tago"], key, pick)
    _save_raw("tago", {"items": items})
    return items


def fetch_hospitals(key):
    def pick(d):
        b = d["response"]["body"]
        it = (b["items"].get("item") or []) if isinstance(b.get("items"), dict) else []
        return ([it] if isinstance(it, dict) else it), int(b.get("totalCount", 0))
    items, _ = _paged(PROBES["hira"], key, pick)
    _save_raw("hira", {"items": items})
    return items


def fetch_sports(key):
    def pick(d):
        b = d["response"]["body"]
        it = (b["items"].get("item") or []) if isinstance(b.get("items"), dict) else []
        return ([it] if isinstance(it, dict) else it), int(b.get("totalCount", 0))
    items, _ = _paged(PROBES["kspo"], key, pick)
    _save_raw("kspo", {"items": items})
    return items


def fetch_parks(key):
    """세종시 도시공원정보. 시(시설관리사업소)가 관리하는 공원만 들어 있다(70곳, 대부분 1·2생활권)."""
    def pick(d):
        return d["body"].get("items") or [], int(d["header"].get("totalCount", 0))
    items, _ = _paged(PROBES["park"], key, pick)
    _save_raw("park", {"items": items})
    return items


def load_libraries():
    """전국도서관표준데이터(사용자가 내려받은 파일)에서 뽑은 세종 도서관. API 가 아니라 파일이다."""
    with open(os.path.join(HERE, "assets", "sejong_libraries.json"), encoding="utf-8") as f:
        return json.load(f)["records"]


def fetch_trades(key, ym_end, months=12):
    out = []
    for i in range(months):
        ym = _shift(ym_end, -i)

        def pick(d):
            b = d["response"]["body"]
            it = (b["items"].get("item") or []) if isinstance(b.get("items"), dict) else []
            return ([it] if isinstance(it, dict) else it), int(b.get("totalCount", 0))
        items, _ = _paged(PROBES["rtms"], key, pick, ym=ym)
        out += items
    _save_raw("rtms", {"to": ym_end, "months": months, "items": out})
    return out


# ── 기하 ──────────────────────────────────────────────────────────────
LAT0 = 36.55
MX = 111320.0 * math.cos(math.radians(LAT0))   # 경도 1도 = m
MY = 110950.0


def _xy(lon, lat):
    return lon * MX, lat * MY


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi:
            inside = not inside
        j = i
    return inside


def _in_unit(lon, lat, rings):
    # 외곽·구멍 링이 섞여 있으므로 짝홀로 판정한다.
    return sum(_in_ring(lon, lat, r) for r in rings) % 2 == 1


class Grid:
    """점 목록을 격자에 넣어 반경 질의를 빠르게."""
    def __init__(self, pts, cell=500.0):
        self.cell, self.b = cell, {}
        for p in pts:
            x, y = _xy(p[0], p[1])
            self.b.setdefault((int(x // cell), int(y // cell)), []).append((x, y, p))

    def near(self, lon, lat, r):
        x, y = _xy(lon, lat)
        c, n = self.cell, int(math.ceil(r / self.cell))
        cx, cy = int(x // c), int(y // c)
        for i in range(cx - n, cx + n + 1):
            for j in range(cy - n, cy + n + 1):
                for px, py, p in self.b.get((i, j), ()):
                    if (px - x) ** 2 + (py - y) ** 2 <= r * r:
                        yield p

    def nearest(self, lon, lat, rmax=8000.0):
        x, y = _xy(lon, lat)
        best = None
        for p in self.near(lon, lat, rmax):
            px, py = _xy(p[0], p[1])
            d = math.hypot(px - x, py - y)
            if best is None or d < best:
                best = d
        return best


def _bbox(rings):
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return min(xs), min(ys), max(xs), max(ys)


def _points_in(rings, step=120.0):
    x0, y0, x1, y1 = _bbox(rings)
    dlon, dlat = step / MX, step / MY
    pts = []
    lat = y0 + dlat / 2
    while lat < y1:
        lon = x0 + dlon / 2
        while lon < x1:
            if _in_unit(lon, lat, rings):
                pts.append((lon, lat))
            lon += dlon
        lat += dlat
    return pts


def _dist_to_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


# ── 집계 ──────────────────────────────────────────────────────────────
SERVICES = {  # 15분 생활서비스 8종
    "식료품·편의점": lambda s: s["indsMclsNm"] == "식료품 소매" or s["indsSclsNm"] in ("슈퍼마켓", "편의점"),
    "약국": lambda s: s["indsSclsNm"] == "약국",
    "음식점": lambda s: s["indsLclsNm"] == "음식" and s["indsMclsNm"] not in ("주점", "비알코올 "),
    "카페": lambda s: s["indsMclsNm"].strip() == "비알코올",
    "학원": lambda s: s["indsLclsNm"] == "교육",
    "미용·세탁": lambda s: s["indsMclsNm"] in ("이용·미용", "세탁"),
}
# 의원은 심평원 병원정보로 센다(상가정보보다 정확). 치과·한의원·요양·정신병원은 뺀다.
CLINIC_KINDS = ("의원", "병원", "종합병원", "보건소", "보건지소", "보건진료소")
# 운동시설은 체육진흥공단 전국체육시설(정상운영)로 센다. 당구장·무도학원은 뺀다.
SPORT_EXCLUDE = ("당구장", "무도학원")
WALK = 1000.0          # 직선 1km ≈ 우회 1.25배 도보 15분(4.8km/h)
BUS_R = 400.0
BUILT_R = 300.0


def analyze(pop_ym, pop_now, pop_before, age, store_ym, stores, stops, trades, hosps, sports,
            parks=(), libs=()) -> dict:
    import livingzone as LZ
    with open(os.path.join(HERE, "assets", "sejong_units.json"), encoding="utf-8") as f:
        shapes = {u["name"]: u for u in json.load(f)["units"]}
    with open(os.path.join(HERE, "assets", "sejong_roads.json"), encoding="utf-8") as f:
        brt_lines = [l for r in json.load(f)["roads"] if r["cls"] == "brt" for l in r["lines"]]
    with open(os.path.join(HERE, "assets", "sejong_units.json"), encoding="utf-8") as f:
        outline = json.load(f)["outline"]

    code2unit = {c: a["name"] for a in LZ.ADMIN for c in a["codes"]}
    units = {a["name"]: {} for a in LZ.ADMIN}

    # 인구·세대
    def by_unit(items, field):
        out = {}
        for it in items:
            u = code2unit.get(it["admmCd"])
            if u:
                out[u] = out.get(u, 0) + int(it[field] or 0)
        return out
    pop = by_unit(pop_now, "totNmprCnt")
    hh = by_unit(pop_now, "hhCnt")
    pop0 = by_unit(pop_before, "totNmprCnt")
    for u, v in pop.items():
        units[u]["pop"] = v
        units[u]["hh"] = round(v / hh[u], 2) if hh.get(u) else None
    grouped = {n for g in LZ.CHG_GROUPS for n in g}
    for u in pop:
        if u in grouped:
            continue
        if pop0.get(u):
            units[u]["chg"] = round((pop[u] - pop0[u]) / pop0[u] * 100, 1)
    for g in LZ.CHG_GROUPS:
        a, b = sum(pop.get(u, 0) for u in g), sum(pop0.get(u, 0) for u in g)
        if b:
            for u in g:
                units[u]["chg"] = round((a - b) / b * 100, 1)

    # 연령(10세 단위)
    agg = {}
    for it in age:
        u = code2unit.get(it["admmCd"])
        if not u:
            continue
        a = agg.setdefault(u, {"tot": 0, "old": 0, "kid": 0})
        a["tot"] += int(it["totNmprCnt"] or 0)
        for sex in ("male", "feml"):
            for band in (0, 10):
                a["kid"] += int(it.get(f"{sex}{band}AgeNmprCnt") or 0)
            for band in (60, 70, 80, 90, 100):
                a["old"] += int(it.get(f"{sex}{band}AgeNmprCnt") or 0)
    for u, a in agg.items():
        if a["tot"]:
            units[u]["old"] = round(a["old"] / a["tot"] * 100, 1)
            units[u]["kid"] = round(a["kid"] / a["tot"] * 100, 1)

    # 점포·정류장을 면에 넣는다
    def locate(lon, lat):
        for n, s in shapes.items():
            x0, y0, x1, y1 = s.setdefault("_bb", _bbox(s["rings"]))
            if x0 <= lon <= x1 and y0 <= lat <= y1 and _in_unit(lon, lat, s["rings"]):
                return n
        return None

    st_pts = [(float(s["lon"]), float(s["lat"]), s) for s in stores if s.get("lon") and s.get("lat")]
    counts, lcls = {}, {}
    for lon, lat, s in st_pts:
        u = locate(lon, lat)
        if not u:
            continue
        counts[u] = counts.get(u, 0) + 1
        lcls.setdefault(u, {}).setdefault(s["indsLclsNm"], 0)
        lcls[u][s["indsLclsNm"]] += 1
    n_cls = len({s["indsLclsNm"] for _, _, s in st_pts})
    for u, c in lcls.items():
        tot = sum(c.values())
        h = -sum(v / tot * math.log(v / tot) for v in c.values() if v)
        units[u]["mix"] = round(h / math.log(n_cls), 2) if tot >= 20 else None
        units[u]["stores"] = tot
        if units[u].get("pop"):
            units[u]["dens"] = round(tot / units[u]["pop"] * 1000, 1)

    stop_pts = [(float(s["gpslong"]), float(s["gpslati"]), s) for s in stops
                if s.get("gpslong") and s.get("gpslati")]
    stop_pts = [p for p in stop_pts if _in_unit(p[0], p[1], outline)]
    # BRT 정류장 = BRT 도로선 40m 안 또는 이름에 BRT
    brt_xy = [[_xy(*p) for p in l] for l in brt_lines]

    def near_brt(lon, lat):
        x, y = _xy(lon, lat)
        for l in brt_xy:
            for (ax, ay), (bx, by) in zip(l, l[1:]):
                if _dist_to_seg(x, y, ax, ay, bx, by) <= 40:
                    return True
        return False
    brt_pts = [p for p in stop_pts if "BRT" in p[2].get("nodenm", "").upper() or near_brt(p[0], p[1])]

    hosp_pts = [(float(h["XPos"]), float(h["YPos"]), h) for h in hosps if h.get("XPos") and h.get("YPos")]
    svc_grids = {k: Grid([p for p in st_pts if f(p[2])]) for k, f in SERVICES.items()}
    svc_grids["의원"] = Grid([p for p in hosp_pts if p[2].get("clCdNm") in CLINIC_KINDS])
    sp_pts = [(float(f["faci_lot"]), float(f["faci_lat"]), f) for f in sports
              if f.get("faci_stat_nm") == "정상운영" and f.get("faci_lot") and f.get("faci_lat")
              and f.get("ftype_nm") not in SPORT_EXCLUDE]
    svc_grids["운동시설"] = Grid(sp_pts)
    pub = {}
    for lon, lat, f in sp_pts:
        if f.get("faci_gb_nm") != "공공":
            continue
        u = locate(lon, lat)
        if u:
            pub[u] = pub.get(u, 0) + 1
    for u in units:
        if units[u].get("pop"):
            units[u]["psport"] = round(pub.get(u, 0) / units[u]["pop"] * 10000, 1)
            units[u]["psport_n"] = pub.get(u, 0)
    docs = {}
    for lon, lat, h in hosp_pts:
        u = locate(lon, lat)
        if u:
            docs[u] = docs.get(u, 0) + int(h.get("drTotCnt") or 0)
    for u, d in docs.items():
        if units[u].get("pop"):
            units[u]["med"] = round(d / units[u]["pop"] * 10000, 1)
            units[u]["docs"] = d
    any_grid = Grid(st_pts + stop_pts)
    stop_grid, brt_grid = Grid(stop_pts), Grid(brt_pts, cell=1000.0)
    lib_pts = [(float(r["경도"]), float(r["위도"]), r) for r in libs if r.get("경도") and r.get("위도")]
    lib_grid = Grid(lib_pts, cell=1000.0)

    for n, s in shapes.items():
        pts = [p for p in _points_in(s["rings"]) if next(any_grid.near(p[0], p[1], BUILT_R), None)]
        if not pts:
            continue
        svc = sum(sum(1 for g in svc_grids.values() if next(g.near(lon, lat, WALK), None))
                  for lon, lat in pts) / len(pts)
        bus = sum(1 for lon, lat in pts if next(stop_grid.near(lon, lat, BUS_R), None)) / len(pts)
        dists = [brt_grid.nearest(lon, lat, 12000.0) for lon, lat in pts]
        dists = [d for d in dists if d is not None]
        units[n]["svc"] = round(svc, 1)
        units[n]["bus"] = round(bus * 100)
        # 읍면은 BRT 순환축 밖이라 값이 수십~수백 분으로 튀어 지도 색을 망친다 — 계산하지 않는다.
        in_ring = LZ.ADMIN_ZONE.get(n) != "R"
        units[n]["brt"] = round(sum(dists) / len(dists) * 1.25 / (4000 / 60), 1) if dists and in_ring else None
        units[n]["built"] = len(pts)
        if lib_pts:
            units[n]["lib"] = round(sum(1 for lon, lat in pts if next(lib_grid.near(lon, lat, WALK), None))
                                    / len(pts) * 100)

    # 아파트 ㎡당 매매가(12개월 중앙값) — 법정동 이름으로 행정동에 넣는다
    legal2unit = {l: a["name"] for a in LZ.ADMIN for l in a["legal"]}
    legal2unit.update({"가람동": "한솔동", "어진동": "도담·어진동"})
    per = {}
    for t in trades:
        if (t.get("cdealType") or "").strip():      # 해제된 거래
            continue
        umd = (t.get("umdNm") or "").split()[0]
        u = legal2unit.get(umd)
        try:
            price = int(str(t["dealAmount"]).replace(",", "")) / float(t["excluUseAr"])
        except (ValueError, ZeroDivisionError, KeyError):
            continue
        if u:
            per.setdefault(u, []).append(price)
    for u, v in per.items():
        if len(v) >= 5:
            v.sort()
            m = len(v) // 2
            units[u]["apt"] = round(v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2)
            units[u]["apt_n"] = len(v)

    points = {
        "park": [{"n": p.get("nm"), "t": p.get("se"), "a": p.get("ar"), "lon": p["lo"], "lat": p["la"]}
                 for p in parks if p.get("lo") and p.get("la")],
        "lib": [{"n": r["도서관명"], "t": r["도서관유형"], "lon": lon, "lat": lat} for lon, lat, r in lib_pts],
    }
    return {
        "points": points,
        "asof": {"park": dt.date.today().strftime("%Y-%m-%d"),
                 "lib": max((r.get("데이터기준일자") or "" for r in libs), default=""), "kspo": dt.date.today().strftime("%Y-%m-%d"), "hira": dt.date.today().strftime("%Y-%m-%d"), "mois_pop": pop_ym, "mois_age": pop_ym, "sbiz": store_ym,
                 "tago": dt.date.today().strftime("%Y-%m-%d"), "rtms": f"{_shift(pop_ym, -11)}~{pop_ym}"},
        "counts": {"stores": len(st_pts), "stops": len(stop_pts), "brt_stops": len(brt_pts),
                   "trades": sum(len(v) for v in per.values()),
                   "hospitals": len(hosp_pts), "sports": len(sp_pts),
                   "parks": len(points["park"]), "libraries": len(lib_pts)},
        "units": units,
    }


LIVE_IND = {"mois_pop": ["pop", "chg", "hh"], "mois_age": ["old", "kid"],
            "sbiz": ["mix", "dens", "svc"], "tago": ["bus", "brt"], "rtms": ["apt"], "hira": ["med"], "kspo": ["psport"], "lib": ["lib"], "park": []}


def collect() -> dict:
    key = load_key()
    if not key:
        raise SystemExit("인증키가 없습니다. config.json 의 portal_key 를 채우십시오.")
    print("인구·연령 …")
    pop_ym, now, before, age = fetch_population(key)
    print("  기준", pop_ym, "행정동", len(now))
    print("상가 …")
    store_ym, stores = fetch_stores(key)
    print("  기준", store_ym, "점포", len(stores))
    print("버스정류소 …")
    stops = fetch_stops(key)
    print("  정류장", len(stops))
    print("아파트 실거래 12개월 …")
    trades = fetch_trades(key, pop_ym)
    print("  거래", len(trades))
    print("병원정보 …")
    hosps = fetch_hospitals(key)
    print("  의료기관", len(hosps))
    print("체육시설 …")
    sports = fetch_sports(key)
    print("  체육시설", len(sports))
    print("도시공원·도서관 …")
    parks, libs = fetch_parks(key), load_libraries()
    print("  공원", len(parks), "도서관", len(libs))
    res = analyze(pop_ym, now, before, age, store_ym, stores, stops, trades, hosps, sports, parks, libs)
    res["sources"] = list(LIVE_IND)
    res["live"] = [i for ids in LIVE_IND.values() for i in ids]
    res["collected"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LATEST, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("저장:", LATEST, res["counts"])
    return res
