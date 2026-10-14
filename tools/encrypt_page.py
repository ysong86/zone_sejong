# -*- coding: utf-8 -*-
"""dashboard.html 을 비밀번호로 암호화한 공개용 index.html 을 만든다.

  python tools/encrypt_page.py [입력=dashboard.html] [출력=site/index.html] [문 제목] [--video preview.mp4] [--contact "이름(메일)"] [--hits 배지주소] [--sister "이름|주소,이름|주소"]

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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;600;700&family=Nanum+Myeongjo:wght@800&display=swap">
<style>
:root{--ground:#F2F4F1;--panel:#fff;--ink:#15232A;--ink2:#4B5B62;--ink3:#7C8A8F;--line:#D6DDD9;--accent:#1D5C7C;--bad:#B03A3A;--btnink:#fff}
@media (prefers-color-scheme: dark){:root{--ground:#0E1619;--panel:#152125;--ink:#E3ECEA;--ink2:#A4B4B4;--ink3:#72858A;--line:#2B3B40;--accent:#74B8D6;--bad:#E07A72;--btnink:#0E1619;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--ground);color:var(--ink);
  font-family:"IBM Plex Sans KR","Malgun Gothic",system-ui,sans-serif;padding:24px 16px}
.box{width:100%;max-width:380px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:28px 26px}
.eb{font-size:11.5px;letter-spacing:.08em;color:var(--ink3);font-weight:600}
h1{font-family:"Nanum Myeongjo",serif;font-size:26px;margin:6px 0 4px;line-height:1.25;word-break:keep-all}
p{word-break:keep-all}
p{margin:0 0 18px;color:var(--ink2);font-size:13.5px;line-height:1.55}
label{display:block;font-size:12.5px;font-weight:600;margin-bottom:6px}
input[type=password]{width:100%;font:inherit;font-size:15px;padding:10px 12px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink)}
input[type=password]:focus{outline:2px solid var(--accent);outline-offset:1px}
.row{display:flex;align-items:center;gap:6px;margin:10px 0 16px;font-size:12.5px;color:var(--ink2)}
button{width:100%;font:inherit;font-weight:700;font-size:14.5px;padding:10px;border:0;border-radius:6px;background:var(--accent);color:var(--btnink);cursor:pointer}
button[disabled]{opacity:.6;cursor:wait}
.err{color:var(--bad);font-size:12.5px;min-height:18px;margin-top:10px}
.foot{margin-top:18px;font-size:12px;color:var(--ink3);line-height:1.6}
.foot .aside{display:block;font-style:italic;margin-bottom:6px;line-height:1.5}
.foot .names{display:block;white-space:nowrap;font-size:min(11.5px,3.2vw)}
</style></head>
<body>
<form class="box" id="f" autocomplete="off">
  <div class="eb">세종연구원 · 검토 자료</div>
  <h1>세종 생활권 재구조화 상황판</h1>
  <p>연구모임 내부 검토용입니다. 비밀번호를 입력하면 열립니다.</p>
  <label for="pw">비밀번호</label>
  <input type="password" id="pw" autofocus required>
  <div class="row"><input type="checkbox" id="rem"><label for="rem" style="margin:0;font-weight:400">이 브라우저에서 기억</label></div>
  <button id="go" type="submit">열기</button>
  <div class="err" id="err" role="alert"></div>
  <div class="foot"><span class="aside">연구원의 공식 업무가 아닌, 참여 연구자들의 호기심과 재미에서 시작한 작업입니다. 결과물은 참고용으로 봐 주세요.</span>제작: 세종연구원 연구모임<span class="names">김성표, 안용준, 김흥주, 남영식, 이재민, 이자은, 송양호</span></div>
</form>
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
.pv{margin-top:10px;background:transparent;color:var(--accent);border:1px solid var(--accent);font-weight:600;font-size:13.5px}
.pv:hover{background:color-mix(in srgb,var(--accent) 10%,transparent)}
.ask{margin-top:12px;font-size:12.5px;color:var(--ink2)}
.ask a{color:var(--accent);font-weight:600;text-decoration:none}
.ask a:hover{text-decoration:underline}
#pvm{position:fixed;inset:0;background:rgba(0,0,0,.72);display:none;align-items:center;justify-content:center;padding:16px;z-index:9}
#pvm.on{display:flex}
#pvm .in{width:min(960px,100%);background:var(--panel);border-radius:10px;overflow:hidden}
#pvm .bar{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;font-size:13px;font-weight:600}
#pvm .bar button{width:auto;background:transparent;color:var(--ink2);padding:2px 8px;font-size:18px;line-height:1}
#pvm video{display:block;width:100%;background:#000}
"""


HITS_CSS = """
.visitors{display:flex;align-items:center;gap:8px;margin-top:12px}
.visitors img{display:block;height:20px}
.vsub{font-size:11.5px;color:var(--ink3)}
"""


# 세종연구원 시그니처(국영문 좌우조합) — 문 상자 아래 공통. 공식 그림(assets/sri_signature.png)을 그대로 넣는다.
# 색은 바꾸지 않는다(사용자 지정: 남색·초록 그대로). 흰 판 위에 올려 어두운 화면에서도 보이게 한다.
# 크기는 상자 안 높이 48px(사용자 선호). 흐림은 크기가 아니라 저해상 그림 탓이었다 → 표시 폭의 약 3배 해상도 그림을 줄여 쓴다.
SRI_PNG = os.path.join(HERE, "assets", "sri_signature.png")
SRI_CSS = """
.sri{display:flex;justify-content:center;margin-top:16px;padding-top:14px;border-top:1px solid var(--line)}
.sri img{display:block;height:48px;width:auto;max-width:100%;background:#fff;border-radius:6px;padding:4px 8px;box-sizing:border-box}
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
.sister{margin:16px 0 0;padding:10px 12px;border:1px solid var(--line);border-radius:8px;display:flex;flex-direction:column;gap:4px}
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
    links = "".join(f'\n    <a href="{_h.escape(u.strip())}" target="_blank" rel="noopener">{_h.escape(n.strip())} ↗</a>'
                    for n, u in items)
    gate = gate.replace("</style>", SISTER_CSS + "</style>", 1)
    return gate.replace('  <div class="foot">',
                        f'  <nav class="sister" aria-label="함께 보는 상황판"><span class="eb">함께 보는 상황판</span>{links}\n  </nav>\n  <div class="foot">', 1)


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
                            '<button id="go" type="submit">열기</button>\n  <button class="pv" id="pv" type="button">▶ 30초 미리보기 — 어떤 상황판인지 먼저 보기</button>')
        gate = gate.replace("</form>", f"""</form>
<div id="pvm" role="dialog" aria-modal="true" aria-label="상황판 미리보기"><div class="in">
  <div class="bar"><span>상황판 미리보기 <small style="font-weight:400;color:var(--ink3)">· 수치는 흐리게 처리했습니다</small></span><button type="button" id="pvx" aria-label="닫기">×</button></div>
  <video id="pvv" controls playsinline preload="none" src="{v}"></video></div></div>""")
        gate = gate.replace("<script>", """<script>
(() => { const m = document.getElementById("pvm"), v = document.getElementById("pvv");
  const close = () => { m.classList.remove("on"); v.pause(); };
  document.getElementById("pv").onclick = () => { m.classList.add("on"); v.play().catch(() => {}); };
  document.getElementById("pvx").onclick = close;
  m.addEventListener("click", e => { if (e.target === m) close(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") close(); }); })();
""", 1)
    if video or contact:
        gate = gate.replace("</style>", PREVIEW_CSS + "</style>", 1)
    return gate


def main(src=None, out=None, title=None, video=None, contact=None, hits=None, sister=None):
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
    with open(out, "w", encoding="utf-8") as f:
        f.write(gate.replace("__PAYLOAD__", json.dumps(payload)))
    print("암호화:", out, f"{os.path.getsize(out) / 1024:.0f} KB")


if __name__ == "__main__":
    args, opts = [], {}
    it = iter(sys.argv[1:])
    for a in it:
        if a in ("--video", "--contact", "--hits", "--sister"):
            opts[a[2:]] = next(it)
        else:
            args.append(a)
    main(*args[:3], **opts)
