# -*- coding: utf-8 -*-
"""상황판 소개 영상(약 20초, MP4) — 실제 화면을 열어 스크롤·클릭하는 모습을 녹화한다.

  python tools/make_video.py
    입력: dashboard.html(평문, 로컬)   출력: docs/생활권상황판_소개.mp4

녹화에는 마우스 포인터가 찍히지 않으므로 화면에 가짜 포인터·클릭 물결·자막을 얹는다.
설치된 Chrome 을 쓴다(playwright 브라우저 내려받기 불필요).
"""
from __future__ import annotations

import glob
import os
import subprocess
import time

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "file:///" + os.path.join(HERE, "dashboard.html").replace("\\", "/")
TMP = os.path.join(HERE, "data", "video_tmp")
OUT = os.path.join(HERE, "docs", "생활권상황판_소개.mp4")
W, H = 1440, 810
LENGTH = 20.0

OVERLAY = r"""
(() => {
  const css = document.createElement('style');
  css.textContent = `
  #vcur{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;
        transform:translate(-3px,-2px);transition:none;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
  .vring{position:fixed;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;border:3px solid #1D5C7C;
         z-index:2147483646;pointer-events:none;animation:vr .6s ease-out forwards}
  @keyframes vr{from{transform:scale(.3);opacity:.9}to{transform:scale(1.4);opacity:0}}
  #vcap{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:2147483645;pointer-events:none;
        background:rgba(21,35,42,.88);color:#fff;font:700 21px/1.3 "IBM Plex Sans KR","Malgun Gothic",sans-serif;
        padding:10px 22px;border-radius:999px;letter-spacing:-.01em;opacity:0;transition:opacity .35s}
  #vcap small{font-weight:400;font-size:15px;opacity:.85;margin-left:10px}
  html{scroll-behavior:auto!important}`;
  document.head.appendChild(css);
  const c = document.createElement('div'); c.id = 'vcur';
  c.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M4 2l15 9.5-6.6 1.6 3.9 7.4-3.1 1.6-3.9-7.5L4 19.5z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
  const cap = document.createElement('div'); cap.id = 'vcap'; document.body.appendChild(cap);
  document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  document.addEventListener('mousedown', e => {
    const r = document.createElement('div'); r.className = 'vring';
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
    document.body.appendChild(r); setTimeout(() => r.remove(), 700);
  }, true);
  window.__cap = (t, s) => { cap.innerHTML = t + (s ? '<small>' + s + '</small>' : ''); cap.style.opacity = t ? 1 : 0; };
  window.__scroll = (y, ms) => new Promise(res => {
    const y0 = scrollY, t0 = performance.now(), ease = t => t < .5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2) / 2;
    (function step(now){ const k = Math.min(1, (now - t0) / ms); scrollTo(0, y0 + (y - y0) * ease(k));
      k < 1 ? requestAnimationFrame(step) : res(); })(t0);
  });
  window.__top = sel => { const el = document.querySelector(sel); return el ? el.getBoundingClientRect().top + scrollY : 0; };
})();
"""


def main():
    os.makedirs(TMP, exist_ok=True)
    for f in glob.glob(os.path.join(TMP, "*.webm")):
        os.remove(f)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=1, color_scheme="light",
                            record_video_dir=TMP, record_video_size={"width": W, "height": H})
        t_open = time.time()
        pg = ctx.new_page()
        pg.goto(SRC, wait_until="networkidle")
        pg.evaluate("try{localStorage.clear()}catch(e){}")
        pg.evaluate(OVERLAY)
        pg.mouse.move(W * 0.55, H * 0.45)
        pg.wait_for_timeout(600)
        start = time.time() - t_open                       # 이 시점부터 영상으로 쓴다

        def cap(t, s=""):
            pg.evaluate("([t,s]) => __cap(t,s)", [t, s])

        def scroll_to(sel, ms, off=70):
            y = pg.evaluate(f"__top('{sel}')") - off
            pg.evaluate(f"__scroll({max(0, y)}, {ms})")

        def move_click(sel, steps=18, click=True, dx=0.5, dy=0.5):
            box = pg.locator(sel).first.bounding_box()
            x, y = box["x"] + box["width"] * dx, box["y"] + box["height"] * dy
            pg.mouse.move(x, y, steps=steps)
            if click:
                pg.mouse.down(); pg.mouse.up()
                pg.locator(sel).first.click(force=True)
            return x, y

        # 0~3초 — 제목·네 단계
        cap("세종 생활권 재구조화 상황판", "공공데이터 25개 지표 · 행정동 지도")
        pg.wait_for_timeout(1500)
        move_click("#axes .axis:nth-child(1)", click=False)
        pg.wait_for_timeout(500)
        move_click("#axes .axis:nth-child(4)", steps=20, click=False)
        pg.wait_for_timeout(500)

        # 3~7초 — 지표 지도
        cap("지표 지도", "지표를 고르면 행정동 25곳이 칠해집니다")
        scroll_to("#bench-sec", 900, 20)
        pg.wait_for_timeout(250)
        move_click('.ind[data-i="emp"]')
        pg.wait_for_timeout(650)
        move_click('.ind[data-i="svc"]', steps=12)
        pg.wait_for_timeout(500)
        move_click('#map .u[data-n="나성동"]', steps=20, click=False)
        pg.wait_for_timeout(700)

        # 7~10초 — 광역 흐름
        cap("광역 관계", "선 위에 올리면 통근 인원과 행선지가 나옵니다")
        move_click('#views [data-v="region"]', steps=16)
        pg.wait_for_timeout(500)
        # 곡선 위 실제 점(길이의 60%)을 화면 좌표로 바꿔 그 위에 올린다 — 상자 중심은 선을 벗어난다
        pt = pg.evaluate("""() => { const p = document.querySelector('#g-ext .xg[data-x="dj"] .fxhit');
            const L = p.getTotalLength(), q = p.getPointAtLength(L * 0.6), m = p.getScreenCTM();
            return [q.x * m.a + q.y * m.c + m.e, q.x * m.b + q.y * m.d + m.f]; }""")
        pg.mouse.move(pt[0], pt[1], steps=22)
        pg.wait_for_timeout(1700)

        # 10~13초 — ① 진척도
        cap("① 개발·건설 진척도", "조성 중인 생활권은 다른 잣대로")
        pg.mouse.move(W * 0.9, H * 0.3, steps=8)
        scroll_to("#progress-sec", 1100, 10)
        pg.wait_for_timeout(500)
        move_click('.pc.building', steps=20, click=False, dy=0.3)
        pg.wait_for_timeout(900)

        # 13~16초 — ② 생활권 진단
        cap("② 계획기능 실현도", "건축물 연면적으로 본 기능 특화도")
        scroll_to("#zones", 1000, 90)
        pg.wait_for_timeout(400)
        move_click('.zc[data-z="6"]', steps=20, click=False, dy=0.35)
        pg.wait_for_timeout(1000)

        # 16~18초 — ③④ 연계·광역
        cap("③ 생활권 간 연계 · ④ 광역", "KTDB 통행·인구총조사 통근")
        scroll_to("#matrix", 900, 120)
        pg.wait_for_timeout(1100)

        # 18~20초 — 개선방향
        cap("개선방향", "국내외 이론에 근거한 단계별 처방")
        scroll_to("#strat", 900, 110)
        pg.wait_for_timeout(1300)
        cap("")
        pg.wait_for_timeout(500)

        end = time.time() - t_open
        video = pg.video.path()
        ctx.close()
        b.close()

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    dur = min(LENGTH, end - start)
    cmd = [ff, "-y", "-ss", f"{start:.2f}", "-i", video, "-t", f"{dur:.2f}",
           "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
           "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"영상: {OUT}  ({dur:.1f}초, 녹화 {end - start:.1f}초)")


if __name__ == "__main__":
    main()
