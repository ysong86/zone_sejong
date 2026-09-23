# -*- coding: utf-8 -*-
"""공공데이터포털 API 타진·수집.

지금(2026-09-23) 포털 5종은 모두 403(주소 맞음, 활용신청 안 됨)이다.
승인 전에는 응답 모양을 볼 수 없으므로, 여기서는
  1) --probe : 상태 코드 확인(403 = 신청만 남음 / 400 = 주소 틀림 / 200 = 됨)
  2) --collect : 200 이 나오는 서비스의 원 응답을 data/raw/ 에 저장
까지만 한다. 원 응답을 한 번 본 뒤 동별 집계(aggregate_*)를 채운다 —
응답 필드를 추측해서 짜 두면 틀린 값이 조용히 화면에 오를 수 있어서다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")

# {k} 자리에 인증키가 들어간다. 세종 = 행정코드 3611000000 / 시군구 36110 / TAGO cityCode 12
PROBES = {
    "mois_pop": "https://apis.data.go.kr/1741000/admmPpltnHhStus/selectAdmmPpltnHhStus"
                "?serviceKey={k}&admmCd=3611000000&srchFrYm={ym}&srchToYm={ym}&lv=3&regSeCd=1"
                "&type=JSON&numOfRows=100&pageNo=1",
    "mois_age": "https://apis.data.go.kr/1741000/admmSexdAgePpltn/selectAdmmSexdAgePpltn"
                "?serviceKey={k}&admmCd=3611000000&srchFrYm={ym}&srchToYm={ym}&lv=3&regSeCd=1"
                "&type=JSON&numOfRows=100&pageNo=1",
    "sbiz": "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
            "?serviceKey={k}&divId=signguCd&key=36110&type=json&numOfRows=1000&pageNo=1",
    "tago": "https://apis.data.go.kr/1613000/BusSttnInfoInqireService/getSttnNoList"
            "?serviceKey={k}&cityCode=12&_type=json&numOfRows=1000&pageNo=1",
    "rtms": "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
            "?serviceKey={k}&LAWD_CD=36110&DEAL_YMD={ym}&numOfRows=1000&pageNo=1",
    "hira": "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
            "?serviceKey={k}&sidoCd=410000&_type=json&numOfRows=1000&pageNo=1",
}


def load_key() -> str:
    for p in ("config.json", "config.example.json"):
        path = os.path.join(HERE, p)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                key = json.load(f).get("portal_key", "")
            if key:
                return key
    return os.environ.get("DATA_GO_KR_KEY", "")


def _ym(months_back: int = 2) -> str:
    d = dt.date.today().replace(day=1)
    for _ in range(months_back):
        d = (d - dt.timedelta(days=1)).replace(day=1)
    return d.strftime("%Y%m")


def _get(url: str, timeout: int = 25):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # 연결 실패
        return None, str(e).encode()


def probe(only=None) -> dict:
    key = load_key()
    if not key:
        print("인증키가 없습니다. config.json 의 portal_key 를 채우십시오.")
        return {}
    res = {}
    for name, tpl in PROBES.items():
        if only and name not in only:
            continue
        url = tpl.format(k=urllib.parse.quote(key, safe=""), ym=_ym())
        code, body = _get(url)
        head = body[:160].decode("utf-8", "replace").replace("\n", " ")
        meaning = {200: "됨", 403: "주소 맞음 · 활용신청 필요", 400: "주소·파라미터 틀림",
                   401: "키 오류", 404: "주소 없음"}.get(code, "확인 필요")
        print(f"{name:9s} {code}  {meaning}   {head[:90]}")
        res[name] = {"code": code, "body": body}
    return res


def collect() -> dict:
    """200 이 나오는 서비스의 원 응답만 저장한다. 집계는 응답을 본 뒤 붙인다."""
    os.makedirs(RAW, exist_ok=True)
    ok = []
    for name, r in probe().items():
        if r["code"] == 200:
            with open(os.path.join(RAW, f"{name}.json"), "wb") as f:
                f.write(r["body"])
            ok.append(name)
    print("저장한 원 응답:", ok or "없음")
    return {"saved": ok}
