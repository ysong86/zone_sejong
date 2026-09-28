# -*- coding: utf-8 -*-
"""dashboard.html 을 비밀번호로 암호화한 공개용 index.html 을 만든다.

  python tools/encrypt_page.py [입력=dashboard.html] [출력=site/index.html]

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
  <div class="foot">제작: 세종연구원 연구모임<span class="names">김성표, 안용준, 김흥주, 남영식, 이재민, 송양호, 이자은</span></div>
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


def main(src=None, out=None):
    src = src or os.path.join(HERE, "dashboard.html")
    out = out or os.path.join(HERE, "site", "index.html")
    with open(src, encoding="utf-8") as f:
        html = f.read()
    if not html.lstrip().lower().startswith("<!doctype"):
        html = "<!doctype html>\n" + html
    payload = encrypt(html, password())
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(GATE.replace("__PAYLOAD__", json.dumps(payload)))
    print("암호화:", out, f"{os.path.getsize(out) / 1024:.0f} KB")


if __name__ == "__main__":
    main(*(sys.argv[1:3]))
