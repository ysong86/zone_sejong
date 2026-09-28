# -*- coding: utf-8 -*-
"""행복청 지구단위계획 e-book(happycity2030.or.kr, 로그인 불필요)을 텍스트 줄로 되살린다.

e-book 은 페이지마다 xhtml + css 로, 글자 하나하나가 <span class="Tbox_n"> 이고 위치(left/top)는 css 에 있다.
같은 높이(top)끼리 묶어 왼쪽부터 이으면 줄이 된다.

  python tools/ebook_text.py 5_1_2 7 [찾을말 ...]
    → data/raw/ebook/5_1_2_7.txt 로 저장, 찾을말이 있으면 그 줄 앞뒤를 보여 준다.
"""
from __future__ import annotations

import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "raw", "ebook")
BASE = "https://happycity2030.or.kr/ebook/plan/{book}/{ver}/epub/OEBPS/content/"


def get(url):
    with urllib.request.urlopen(url, timeout=40) as r:
        return r.read().decode("utf-8", "replace").lstrip("﻿")


def page_lines(base, n):
    html = get(f"{base}page{n:05d}.xhtml")
    css = get(f"{base}css/page{n:05d}.css")
    pos = {}
    for m in re.finditer(r"\.(Tbox_\d+)\s*\{([^}]*)\}", css):
        left = re.search(r"left:\s*(-?[\d.]+)px", m.group(2))
        top = re.search(r"top:\s*(-?[\d.]+)px", m.group(2))
        if left and top:
            pos[m.group(1)] = (float(top.group(1)), float(left.group(1)))
    chars = []
    for m in re.finditer(r'<span id="(Tbox_\d+)"[^>]*>(.*?)</span>', html, flags=re.S):
        t = re.sub(r"<[^>]+>", "", m.group(2)).replace("&nbsp;", " ").replace("&amp;", "&")
        if m.group(1) in pos:
            chars.append((*pos[m.group(1)], t))
    chars.sort()
    lines, cur, last_top, last_left = [], "", None, None
    for top, left, t in chars:
        if last_top is None or abs(top - last_top) > 6:
            if cur.strip():
                lines.append(cur)
            cur, last_left = "", None
        if last_left is not None and left - last_left > 28:
            cur += " │ " if left - last_left > 60 else " "
        cur += t
        last_top, last_left = top, left
    if cur.strip():
        lines.append(cur)
    return lines


def main(book, ver, words):
    base = BASE.format(book=book, ver=ver)
    os.makedirs(OUT, exist_ok=True)
    allines, n = [], 1
    while True:
        try:
            ls = page_lines(base, n)
        except Exception:
            break
        allines += [f"[p{n}] {l}" for l in ls]
        n += 1
    path = os.path.join(OUT, f"{book}_{ver}.txt")
    open(path, "w", encoding="utf-8").write("\n".join(allines))
    print("pages", n - 1, "lines", len(allines), "→", path)
    for w in words:
        for i, l in enumerate(allines):
            if w in l:
                print("\n".join(allines[max(0, i - 1): i + 6]))
                print("----")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
