# -*- coding: utf-8 -*-
"""dashboard.html 을 비밀번호로 암호화한 공개용 index.html 을 만든다.

  python tools/encrypt_page.py [입력=dashboard.html] [출력=site/index.html] [문 제목] [--video preview.mp4] [--contact "이름(메일)"] [--hits 배지주소] [--sister "이름|주소,이름|주소"] [--nav 상황판id]

- --video: 문에 '미리보기 영상' 버튼을 단다(출력 폴더에 같은 이름의 mp4 를 함께 올릴 것 — 비밀번호 없이 보인다).
- --hits: 조회수 배지(hits.sh)를 문 맨 아래에 단다. 첫 화면부터 세고, 풀린 상황판에서는 같은 배지를 옮겨 붙여 두 번 세지 않는다.
- --sister: '함께 보는 상황판' 링크 상자(자기 상황판은 빼고 넘길 것).
- --contact: 문 아래에 '비밀번호 문의' 줄을 단다. 괄호 안 메일 주소는 mailto 링크가 된다.

- 비밀번호는 config.json 의 "page_password"(저장소에 올라가지 않음).
- PBKDF2-SHA256(31만 회)로 키를 만들고 AES-256-GCM 으로 페이지 전체를 암호화한다.
  브라우저는 WebCrypto 로 같은 과정을 거쳐 푼다 — 비밀번호 없이는 소스를 봐도 암호문뿐이다.
- '이 브라우저에서 기억'을 켜면 비밀번호가 아니라 풀린 키를 localStorage 에 둔다.
  페이지를 다시 암호화하면(솔트가 바뀌면) 저장된 키는 자동으로 무효가 되고 다시 묻는다.
"""
from __future__ import annotations

import base64
import json
import os
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITER = 310000

GATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>세종 생활권 상황판</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* 대문(세종 이슈 대시보드)과 같은 말씨 — 종이색·검은 글자·얇은 선·각진 모서리, 강조는 남색 하나 */
:root{--ground:#F3F2EE;--panel:#FBFAF7;--ink:#111110;--ink2:#4A4A47;--ink3:#8B8A85;--line:#11111024;--line2:#11111012;--accent:#152484;--bad:#B03A3A;--btnink:#F3F2EE}
@media (prefers-color-scheme: dark){:root{--ground:#0F0F0E;--panel:#161615;--ink:#EDECE8;--ink2:#B2B1AC;--ink3:#76756F;--line:#EDECE82A;--line2:#EDECE814;--accent:#8EA0F2;--bad:#E07A72;--btnink:#0F0F0E;color-scheme:dark}}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--ground);color:var(--ink);font-family:"IBM Plex Sans KR","Malgun Gothic",system-ui,sans-serif;line-height:1.5;
  word-break:keep-all;-webkit-font-smoothing:antialiased}
a{color:inherit}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;letter-spacing:.06em}
.sheet{max-width:1120px;margin:0 auto;padding:0 40px 32px;min-height:100vh;display:flex;flex-direction:column}
.mast{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:18px 0;border-bottom:1px solid var(--ink);font-size:11.5px}
.mast b,.mast .lk{white-space:nowrap}
.mast b{font-weight:600;letter-spacing:.14em}
.mast .lk{color:var(--ink3);letter-spacing:.16em;display:inline-flex;align-items:center;gap:8px}
.mast .lk i{display:inline-block;width:7px;height:7px;background:var(--accent)}
.box{margin:auto 0;display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,1fr);column-gap:64px;padding:56px 0 0}
.intro{padding-bottom:40px}
.eb{font-size:12px;letter-spacing:.06em;color:var(--ink3);font-weight:500}
h1{font-weight:700;letter-spacing:-.045em;font-size:clamp(36px,5.2vw,68px);line-height:1.02;margin:14px 0 20px}
.intro p{margin:0;max-width:34em;font-size:15px;color:var(--ink2);line-height:1.65}
.enter{border-left:1px solid var(--line);padding:4px 0 40px 40px;display:flex;flex-direction:column}
label{display:block;font-size:12.5px;font-weight:500;letter-spacing:.04em;color:var(--ink3);margin-bottom:6px}
input[type=password]{width:100%;font:inherit;font-family:"IBM Plex Mono",monospace;font-size:20px;letter-spacing:.2em;padding:10px 0;
  border:0;border-bottom:1.5px solid var(--ink);border-radius:0;background:transparent;color:var(--ink)}
input[type=password]:focus{outline:none;border-bottom-color:var(--accent);box-shadow:0 1.5px 0 var(--accent)}
.row{display:flex;align-items:center;gap:8px;margin:14px 0 22px;font-size:13px;color:var(--ink2)}
.row input{accent-color:var(--accent);width:15px;height:15px;margin:0}
.row label{letter-spacing:0;font-size:13px;color:var(--ink2);margin:0;font-weight:400}
button{width:100%;font:inherit;font-weight:600;font-size:15px;padding:13px 16px;border:1px solid var(--ink);border-radius:0;background:var(--ink);
  color:var(--btnink);cursor:pointer;display:flex;justify-content:space-between;align-items:center;transition:background .2s,border-color .2s}
button::after{content:"→";font-weight:400}
button:hover{background:var(--accent);border-color:var(--accent)}
button[disabled]{opacity:.6;cursor:wait}
.err{color:var(--bad);font-size:13px;min-height:20px;margin-top:10px}
.foot{grid-column:1;border-top:1px solid var(--line);padding-top:16px;font-size:12px;color:var(--ink3);line-height:1.7}
.foot .aside{display:block;font-style:italic;margin-bottom:8px;max-width:40em}
.foot .names{display:block;font-size:11.5px}
@media (max-width:820px){
  .sheet{padding:0 20px 24px}
  .mast{font-size:10.5px}
  .box{grid-template-columns:minmax(0,1fr);padding-top:32px}
  .intro{padding-bottom:28px}
  .enter{border-left:0;border-top:1px solid var(--ink);padding:24px 0 32px}
  .foot{grid-column:1}
}
</style></head>
<body>
<main class="sheet">
<header class="mast"><b class="mono">SEJONG ISSUE DASHBOARD</b><span class="lk mono"><i></i>LOCKED</span></header>
<form class="box" id="f" autocomplete="off">
  <section class="intro">
  <div class="eb">세종연구원 · 검토 자료</div>
  <h1>세종 생활권 재구조화 상황판</h1>
  <p>연구모임 내부 검토용입니다. 비밀번호를 입력하면 열립니다.</p>
  </section>
  <section class="enter">
  <label for="pw">비밀번호</label>
  <input type="password" id="pw" autofocus required>
  <div class="row"><input type="checkbox" id="rem"><label for="rem">이 브라우저에서 기억</label></div>
  <button id="go" type="submit">열기</button>
  <div class="err" id="err" role="alert"></div>
  </section>
  <div class="foot"><span class="aside">연구원의 공식 업무가 아닌, 참여 연구자들의 호기심과 재미에서 시작한 작업입니다. 결과물은 참고용으로 봐 주세요.</span>제작: 세종연구원 연구모임<span class="names">김성표, 안용준, 김흥주, 남영식, 이재민, 이자은, 송양호</span></div>
</form>
</main>
<script>
const P = __PAYLOAD__;
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const SALT = b64(P.salt), IV = b64(P.iv), CT = b64(P.ct);
const KEYNAME = "zone_sejong_key:" + P.salt;
async function derive(pw){
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({name:"PBKDF2", salt:SALT, iterations:P.iter, hash:"SHA-256"}, base,
                                 {name:"AES-GCM", length:256}, true, ["decrypt"]);
}
async function open_(key){
  const buf = await crypto.subtle.decrypt({name:"AES-GCM", iv:IV}, key, CT);
  const html = new TextDecoder().decode(buf);
  document.open(); document.write(html); document.close();
}
async function tryStored(){
  let raw = null;
  try { raw = localStorage.getItem(KEYNAME); } catch(e) {}
  if (!raw) return;
  try {
    const key = await crypto.subtle.importKey("raw", b64(raw), {name:"AES-GCM"}, false, ["decrypt"]);
    await open_(key);
  } catch(e) { try { localStorage.removeItem(KEYNAME); } catch(_) {} }
}
document.getElementById("f").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = document.getElementById("go"), err = document.getElementById("err");
  btn.disabled = true; err.textContent = "";
  try {
    const key = await derive(document.getElementById("pw").value);
    if (document.getElementById("rem").checked) {
      const raw = new Uint8Array(await crypto.subtle.exportKey("raw", key));
      try { localStorage.setItem(KEYNAME, btoa(String.fromCharCode(...raw))); } catch(_) {}
    }
    await open_(key);
  } catch(ex) {
    err.textContent = "비밀번호가 맞지 않습니다. 다시 입력해 주세요.";
    btn.disabled = false;
    document.getElementById("pw").select();
  }
});
if (!window.crypto || !crypto.subtle) {
  document.getElementById("err").textContent = "이 브라우저는 암호 해제를 지원하지 않습니다. 최신 크롬·엣지로 열어 주세요.";
} else { tryStored(); }
</script>
</body></html>
"""


def password():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        pw = json.load(f).get("page_password", "")
    if not pw:
        raise SystemExit("config.json 에 page_password 가 없습니다.")
    return pw


def encrypt(html: str, pw: str) -> dict:
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, html.encode("utf-8"), None)     # 암호문 + 태그(16바이트) — WebCrypto 와 같은 배치
    enc = lambda b: base64.b64encode(b).decode("ascii")
    return {"salt": enc(salt), "iv": enc(iv), "ct": enc(ct), "iter": ITER}


PREVIEW_CSS = """
.pv{margin-top:8px;background:transparent;color:var(--ink);border:1px solid var(--line);font-weight:500;font-size:14px}
.pv::after{content:none}
.pv:hover{background:transparent;border-color:var(--ink);color:var(--accent)}
.pv{position:relative;overflow:hidden;border-color:var(--accent);color:var(--accent);font-weight:600}
.pv .pl{display:flex;align-items:center;gap:10px}
.pv .pi{position:relative;flex:none;width:22px;height:22px;border-radius:50%;background:var(--accent)}
.pv .pi::after{content:"";position:absolute;left:8.5px;top:6px;border-style:solid;border-width:5px 0 5px 8px;border-color:transparent transparent transparent var(--panel)}
.pv .pi::before{content:"";position:absolute;inset:0;border-radius:50%;border:2px solid var(--accent);animation:pvring 1.9s ease-out infinite}
.pv .pt{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11.5px;font-weight:500;letter-spacing:.06em;padding:2px 7px;border:1px solid currentColor}
.pv::before{content:"";position:absolute;top:0;bottom:0;left:-35%;width:28%;pointer-events:none;
  background:linear-gradient(100deg,transparent,color-mix(in srgb,var(--accent) 16%,transparent),transparent);animation:pvsweep 4.2s ease-in-out 1.2s infinite}
.pv:hover .pi{transform:scale(1.08)}
@keyframes pvring{0%{transform:scale(1);opacity:.75}100%{transform:scale(2.2);opacity:0}}
@keyframes pvsweep{0%{left:-35%}40%,100%{left:115%}}
.pv.seen{border-color:var(--line);color:var(--ink)}
.pv.seen .pi{background:var(--ink)}
.pv.seen .pi::before,.pv.seen::before{animation:none;display:none}
@media (prefers-reduced-motion: reduce){.pv .pi::before,.pv::before{animation:none;display:none}}
.ask{margin-top:auto;padding-top:14px;font-size:12.5px;color:var(--ink2)}
.ask a{color:var(--accent);font-weight:600;text-decoration:none}
.ask a:hover{text-decoration:underline}
#pvm{position:fixed;inset:0;background:rgba(0,0,0,.72);display:none;align-items:center;justify-content:center;padding:16px;z-index:9}
#pvm.on{display:flex}
#pvm .in{width:min(960px,100%);background:var(--panel);border-radius:0;overflow:hidden}
#pvm .bar{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;font-size:13px;font-weight:600}
#pvm .bar button{width:auto;background:transparent;border:0;color:var(--ink2);padding:2px 8px;font-size:18px;line-height:1}
#pvm .bar button::after{content:none}
#pvm video{display:block;width:100%;background:#000}
"""


HITS_CSS = """
.visitors{grid-column:2;grid-row:2;display:flex;align-items:center;gap:8px;align-self:start;border-top:1px solid var(--line);padding-top:16px}
@media (max-width:820px){.visitors{grid-column:1;grid-row:auto;border-top:0;padding-top:10px}}
.visitors img{display:block;height:20px}
.vsub{font-size:11.5px;color:var(--ink3)}
"""


# 세종연구원 시그니처(국영문 좌우조합) — 문 상자 아래 공통. 공식 그림(assets/sri_signature.png)을 그대로 넣는다.
# 색은 바꾸지 않는다(사용자 지정: 남색·초록 그대로). 흰 판 위에 올려 어두운 화면에서도 보이게 한다.
# 크기는 상자 안 높이 48px(사용자 선호). 흐림은 크기가 아니라 저해상 그림 탓이었다 → 표시 폭의 약 3배 해상도 그림을 줄여 쓴다.
SRI_PNG = os.path.join(HERE, "assets", "sri_signature.png")
SRI_CSS = """
.sri{grid-column:2;grid-row:2;display:flex;justify-content:flex-end;align-self:end;padding-top:16px}
.sri img{display:block;height:44px;width:auto;max-width:100%;background:#fff;border-radius:0;padding:4px 8px;box-sizing:border-box}
@media (max-width:820px){.sri{grid-column:1;grid-row:auto;justify-content:flex-start}}
"""


def _gate_sri(gate):
    if not os.path.exists(SRI_PNG):
        return gate
    with open(SRI_PNG, "rb") as f:
        src = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    gate = gate.replace("</style>", SRI_CSS + "</style>", 1)
    i = gate.rindex("\n</form>")   # 상자 안 맨 아래(구분선 아래 가운데) — 작게 두고, 선명도는 3배 해상도 그림을 줄여서
    return gate[:i] + f'\n  <div class="sri"><img src="{src}" alt="세종연구원 SEJONG RESEARCH INSTITUTE"></div>' + gate[i:]


SISTER_CSS = """
.sister{grid-column:1/-1;margin:0 0 16px;padding:10px 0;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:4px}
.sister .eb{margin-bottom:2px}
.sister a{font-size:13px;font-weight:600;text-decoration:none;color:var(--accent)}
.sister a:hover{text-decoration:underline}
"""


def _gate_sister(gate, sister):
    """'함께 보는 상황판' 링크 — sister = "이름|주소,이름|주소,…" (상황판 머리글 .sister 와 같은 모양)."""
    import html as _h
    items = [x.split("|", 1) for x in sister.split(",") if "|" in x]
    if not items:
        return gate
    if len(items) == 1:      # 대문 하나로 안내할 때 — 대문 안(iframe)에서 열렸으면 대문으로 돌아가게 _top
        n, u = items[0]
        label, links = "다른 상황판은", f'\n    <a href="{_h.escape(u.strip())}" target="_top">{_h.escape(n.strip())} →</a>'
    else:
        label = "함께 보는 상황판"
        links = "".join(f'\n    <a href="{_h.escape(u.strip())}" target="_blank" rel="noopener">{_h.escape(n.strip())} ↗</a>'
                        for n, u in items)
    gate = gate.replace("</style>", SISTER_CSS + "</style>", 1)
    return gate.replace('  <div class="foot">',
                        f'  <nav class="sister" aria-label="{label}"><span class="eb">{label}</span>{links}\n  </nav>\n  <div class="foot">', 1)


def _gate_hits(gate, hits):
    """조회수 배지를 문(첫 화면)에 단다. hits.sh 는 캐시를 안 쓰므로 상황판의 배지가 다시 불리면 두 번 센다 →
    풀린 상황판에서는 배지 src 를 지우고, 문에서 이미 받은 배지 그림(img 요소)을 그 자리에 옮겨 붙인다."""
    import html as _h
    gate = gate.replace("</style>", HITS_CSS + "</style>", 1)
    gate = gate.replace('</span></div>\n</form>',
                        '</span></div>\n  <div class="visitors"><img class="hitsbadge" src="' + _h.escape(hits) +
                        '" alt="조회수 오늘/전체" height="20" decoding="async"><span class="vsub">오늘 / 전체</span></div>\n</form>', 1)
    gate = gate.replace("  const html = new TextDecoder().decode(buf);\n  document.open(); document.write(html); document.close();",
                        """  let html = new TextDecoder().decode(buf);
  const gh = document.querySelector(".hitsbadge");
  if (gh) html = html.replace(/(class="hitsbadge"[^>]*?)\\ssrc="[^"]*"/, '$1 data-gate-src=""');
  document.open(); document.write(html); document.close();
  const slot = document.querySelector('.hitsbadge[data-gate-src]');
  if (gh && slot) { slot.replaceWith(gh); if (gh.complete && !gh.naturalWidth) gh.parentElement.hidden = true; else gh.parentElement.hidden = false; }""")
    gate = gate.replace("<script>", """<script>
(() => { const b = document.querySelector(".hitsbadge"); if (!b) return;
  const hide = () => { b.parentElement.style.display = "none"; }; b.addEventListener("error", hide); })();
""", 1)
    return gate


def _gate_extras(gate, video=None, contact=None):
    import html as _h
    import re as _re
    if contact:
        m = _re.match(r"\s*(.*?)\s*\(([^)]+@[^)]+)\)\s*$", contact)
        who = (f'{_h.escape(m.group(1))}(<a href="mailto:{_h.escape(m.group(2))}">{_h.escape(m.group(2))}</a>)'
               if m else _h.escape(contact))
        gate = gate.replace('<div class="err" id="err" role="alert"></div>',
                            '<div class="err" id="err" role="alert"></div>\n  <div class="ask">비밀번호 문의: ' + who + '</div>')
    if video:
        v = _h.escape(video)
        gate = gate.replace('<button id="go" type="submit">열기</button>',
                            '<button id="go" type="submit">열기</button>\n  <button class="pv" id="pv" type="button"><span class="pl"><i class="pi" aria-hidden="true"></i>미리보기 — 어떤 상황판인지 먼저 보기</span><span class="pt">30초</span></button>')
        gate = gate.replace("</form>", f"""</form>
<div id="pvm" role="dialog" aria-modal="true" aria-label="상황판 미리보기"><div class="in">
  <div class="bar"><span>상황판 미리보기 <small style="font-weight:400;color:var(--ink3)">· 수치는 흐리게 처리했습니다</small></span><button type="button" id="pvx" aria-label="닫기">×</button></div>
  <video id="pvv" controls playsinline preload="none" src="{v}"></video></div></div>""")
        gate = gate.replace("<script>", """<script>
(() => { const m = document.getElementById("pvm"), v = document.getElementById("pvv");
  const close = () => { m.classList.remove("on"); v.pause(); };
  const pv = document.getElementById("pv"), SEEN = "preview_seen:" + location.pathname;
  try { if (localStorage.getItem(SEEN)) pv.classList.add("seen"); } catch (_) {}
  pv.onclick = () => { m.classList.add("on"); v.play().catch(() => {});
    pv.classList.add("seen"); try { localStorage.setItem(SEEN, "1"); } catch (_) {} };
  document.getElementById("pvx").onclick = close;
  m.addEventListener("click", e => { if (e.target === m) close(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") close(); }); })();
""", 1)
    if video or contact:
        gate = gate.replace("</style>", PREVIEW_CSS + "</style>", 1)
    return gate


def main(src=None, out=None, title=None, video=None, contact=None, hits=None, sister=None, nav=None):
    src = src or os.path.join(HERE, "dashboard.html")
    out = out or os.path.join(HERE, "site", "index.html")
    with open(src, encoding="utf-8") as f:
        html = f.read()
    if not html.lstrip().lower().startswith("<!doctype"):
        html = "<!doctype html>\n" + html
    payload = encrypt(html, password())
    os.makedirs(os.path.dirname(out), exist_ok=True)
    gate = GATE
    if title:      # 다른 상황판(예: 상가공실)에 같은 문을 쓸 때 — 제목·기억 키 이름을 바꾼다
        gate = gate.replace("<h1>세종 생활권 재구조화 상황판</h1>", f"<h1>{title}</h1>").replace(
            "<title>세종 생활권 상황판</title>", f"<title>{title}</title>").replace(
            '"zone_sejong_key:"', '"' + os.path.splitext(os.path.basename(os.path.dirname(os.path.abspath(src))))[0] + '_key:"')
    gate = _gate_extras(gate, video, contact)
    if hits:
        gate = _gate_hits(gate, hits)
    if sister:
        gate = _gate_sister(gate, sister)
    gate = _gate_sri(gate)
    if nav:   # 세종 이슈 대시보드 공통 탭 줄(대문 iframe 안에서는 스스로 숨는다)
        gate = gate.replace("<body>", f'<body><script src="https://ysong86.github.io/nav.js" data-site="{nav}"></script>', 1)
    with open(out, "w", encoding="utf-8") as f:
        f.write(gate.replace("__PAYLOAD__", json.dumps(payload)))
    print("암호화:", out, f"{os.path.getsize(out) / 1024:.0f} KB")


if __name__ == "__main__":
    args, opts = [], {}
    it = iter(sys.argv[1:])
    for a in it:
        if a in ("--video", "--contact", "--hits", "--sister", "--nav"):
            opts[a[2:]] = next(it)
        else:
            args.append(a)
    main(*args[:3], **opts)
