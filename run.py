# -*- coding: utf-8 -*-
"""세종 생활권 재구조화 상황판.

  python run.py                 샘플로 dashboard.html 생성
  python run.py --open          생성 후 브라우저로 열기
  python run.py --probe         포털 API 상태 확인(403 = 활용신청만 남음)
  python run.py --collect       승인된 API 의 원 응답을 data/raw 에 저장
  python run.py --live          data/latest.json(실측)을 반영해 생성

윈도우에서는 C:\\Python313\\python.exe 를 직접 부를 것.
"""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_dashboard  # noqa: E402
import collect  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="세종 생활권 재구조화 상황판")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "dashboard.html"))
    a = ap.parse_args()
    if a.probe:
        collect.probe(a.only)
        return
    if a.collect:
        collect.collect()
    path = build_dashboard.render(a.out, demo=not a.live)
    print("생성:", path, f"{os.path.getsize(path) / 1024:.0f} KB")
    if a.open:
        webbrowser.open("file:///" + path.replace("\\", "/"))


if __name__ == "__main__":
    main()
