"""대시보드를 **직접 만지면서 맞추는 조절기**를 만든다.

    python deck/build_tuner.py     →  deck/tuner.html

🔴 왜 만드는가 — 간격·크기는 **말로 주고받기 가장 비싼 종류**다.
   「조금 더 벌려」가 몇 px 인지 서로 모른 채 왕복하면 한 번에 한 값씩만
   고쳐진다. 사람이 직접 끌어 맞추고, 도구가 **CSS 값을 대신 읽어 준다.**

화면은 `output/report.html` 을 그대로 iframe 에 넣는다 — 사본을 만들면
진짜 화면과 어긋난다. 조절값은 iframe 안의 `<style id="tune">` 에만 쓰므로
원본 파일은 건드리지 않는다.

    좌우 비율은 카드 가운데 **손잡이를 끌어서** 맞춘다.
    나머지는 막대(슬라이더)로 맞춘다. 값은 한 번에 복사된다.
"""
from __future__ import annotations

import json
import re
import sys
import pathlib

DECK = pathlib.Path(__file__).resolve().parent
REPORT = DECK.parent / "skills" / "data-analysis" / "output" / "report.html"
OUT = DECK / "tuner.html"

# 조절할 지점 — (열쇠, 이름, CSS 선택자와 속성, 최소, 최대, 기본, 단위)
# 🔴 값이 아니라 **선택자**를 여기 적어 둔다. 나중에 값을 옮길 때
#    「어디를 고쳐야 하나」가 이 표 하나로 끝난다.
손잡이 = [
    ("cardpad", "카드 안쪽 여백", ".entry", "padding", 12, 48, 32, "px"),
    ("colgap", "좌우 칸 사이", ".entry", "column-gap", 8, 64, 24, "px"),
    ("rowgap", "위아래 블록 사이", ".entry", "row-gap", 8, 64, 24, "px"),
    ("headgap", "라벨 ↔ 순위 문구", ".entry-head .move", "gap", 0, 24, 8, "px"),
    ("itemsize", "품목명 크기", ".entry-head .item", "font-size", 16, 40, 24, "px"),
    ("ranksize", "순위 문구 크기", ".entry-head .move .rankword",
     "font-size", 12, 32, 18, "px"),
    ("saysize", "설명 문장 크기", ".say", "font-size", 12, 22, 16, "px"),
    ("barh", "막대 높이", ".chart .bar .track", "height", 10, 40, 21, "px"),
    ("bargap", "막대 사이", ".chart .bars", "gap", 2, 24, 9, "px"),
    ("rgap", "그래프 ↔ 도시 비교", ".col-r", "gap", 8, 72, 24, "px"),
    ("lgap", "설명 ↔ 벌어진 조건", ".col-l", "gap", 8, 72, 24, "px"),
    ("statpad", "「벌어진 조건」 여백", ".stat", "padding", 12, 48, 24, "px"),
]

TEMPLATE = """<title>대시보드 레이아웃 조절기</title>
<style>
:root { --ink:#3d3e42; --mid:#6e7075; --soft:#9a9ca2; --rule:#c2c4ca;
        --blue:#6b84f5; --deep:#4a63d8; --panel:#ffffff; }
* { box-sizing:border-box; }
body { margin:0; background:#eceef2; color:var(--ink);
       font-family:"Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif;
       display:grid; grid-template-columns: 1fr 300px; height:100vh; }
#stage { position:relative; overflow:hidden; }
iframe { width:100%; height:100%; border:0; background:#fff; display:block; }

/* 좌우 비율 손잡이 — 카드 가운데를 끌어 옮긴다 */
#grip { position:absolute; top:0; bottom:0; width:14px; cursor:col-resize;
        z-index:5; display:flex; align-items:center; justify-content:center; }
#grip::before { content:""; width:3px; height:64px; border-radius:2px;
                background:var(--blue); opacity:.55; }
#grip:hover::before, #grip.on::before { opacity:1; }
#griplab { position:absolute; top:12px; left:50%; transform:translateX(-50%);
           background:var(--deep); color:#fff; font-size:11px; padding:3px 9px;
           border-radius:3px; white-space:nowrap; z-index:6; }

aside { background:var(--panel); border-left:1px solid var(--rule);
        display:flex; flex-direction:column; min-height:0; }
aside h1 { margin:0; padding:14px 16px; font-size:15px;
           border-bottom:1px solid var(--rule); }
aside h1 small { display:block; font-weight:400; font-size:11.5px;
                 color:var(--soft); margin-top:3px; line-height:1.5; }
#knobs { flex:1; overflow-y:auto; padding:8px 16px 16px; }
.k { padding:9px 0; border-bottom:1px solid #eef0f3; }
.k .t { display:flex; justify-content:space-between; align-items:baseline;
        font-size:12.5px; margin-bottom:5px; }
.k .t b { font-weight:600; }
.k .t output { font-variant-numeric:tabular-nums; color:var(--deep);
               font-weight:600; }
.k input[type=range] { width:100%; accent-color:var(--blue); }
.k .sel { font-size:10.5px; color:var(--soft); font-family:Consolas,monospace; }
footer { border-top:1px solid var(--rule); padding:12px 16px;
         display:flex; flex-direction:column; gap:8px; }
button { font:inherit; font-size:13px; padding:8px 14px; cursor:pointer;
         border:1px solid var(--rule); background:#fff; }
button.go { background:var(--blue); border-color:var(--blue); color:#fff; }
button.go:hover { background:var(--deep); }
button:focus-visible { outline:2px solid var(--blue); outline-offset:2px; }
#msg { font-size:11.5px; color:#2f8f5b; min-height:1.2em; }
</style>

<div id="stage">
  <iframe id="v" title="대시보드 미리보기"></iframe>
  <div id="grip" hidden><span id="griplab" hidden></span></div>
</div>

<aside>
  <h1>레이아웃 조절기
    <small>막대를 움직이면 왼쪽 화면이 바로 바뀝니다.
      좌우 칸 비율은 화면 가운데 <b>파란 손잡이를 끌어서</b> 맞추세요.
      다 되면 아래 「값 복사」를 눌러 채팅에 붙여 주세요.</small></h1>
  <div id="knobs"></div>
  <footer>
    <button class="go" id="copy">값 복사</button>
    <button id="reset">처음으로</button>
    <div id="msg"></div>
  </footer>
</aside>

<script id="doc" type="text/plain">__DOC__</script>
<script>
const 손잡이 = __KNOBS__;
const 값 = {};
손잡이.forEach(k => 값[k.id] = k.def);
let 비율 = 1.25;                       // .entry 오른쪽 칸 배수 (기본 1.25fr)

const v = document.getElementById("v");
v.srcdoc = document.getElementById("doc").textContent;

function css() {
  const 줄 = 손잡이.map(k => `${k.sel}{${k.prop}:${값[k.id]}${k.unit} !important}`);
  줄.push(`.entry{grid-template-columns:minmax(0,1fr) minmax(0,${비율}fr) !important}`);
  return 줄.join("\\n");
}
function 칠하기() {
  const d = v.contentDocument;
  if (!d) return;
  let s = d.getElementById("tune");
  if (!s) { s = d.createElement("style"); s.id = "tune"; d.head.appendChild(s); }
  s.textContent = css();
  손잡이.forEach(k => {
    const o = document.getElementById("o_" + k.id);
    if (o) o.value = 값[k.id] + k.unit;
  });
  손잡이위치();
}

// ── 좌우 비율 손잡이 ──────────────────────────────────────────
const grip = document.getElementById("grip"), lab = document.getElementById("griplab");
function 첫카드() {
  const d = v.contentDocument;
  return d && d.querySelector(".entry");
}
function 손잡이위치() {
  const e = 첫카드();
  if (!e) { grip.hidden = true; return; }
  const r = e.getBoundingClientRect();
  const pad = parseFloat(v.contentWindow.getComputedStyle(e).paddingLeft);
  const gap = parseFloat(v.contentWindow.getComputedStyle(e).columnGap);
  const 안 = r.width - pad * 2 - gap;
  const 왼 = 안 / (1 + 비율);
  grip.hidden = false; lab.hidden = false;
  grip.style.left = (r.left + pad + 왼 + gap / 2 - 7) + "px";
  lab.textContent = `좌우 1 : ${비율.toFixed(2)}`;
}
let 끄는중 = false;
grip.addEventListener("pointerdown", e => {
  끄는중 = true; grip.classList.add("on"); grip.setPointerCapture(e.pointerId);
});
window.addEventListener("pointermove", e => {
  if (!끄는중) return;
  const el = 첫카드(); if (!el) return;
  const r = el.getBoundingClientRect();
  const pad = parseFloat(v.contentWindow.getComputedStyle(el).paddingLeft);
  const gap = parseFloat(v.contentWindow.getComputedStyle(el).columnGap);
  const 안 = r.width - pad * 2 - gap;
  const 왼 = Math.min(Math.max(e.clientX - (r.left + pad), 안 * 0.25), 안 * 0.75);
  비율 = Math.round(((안 - 왼) / 왼) * 100) / 100;
  칠하기();
});
window.addEventListener("pointerup", () => { 끄는중 = false; grip.classList.remove("on"); });

// ── 막대들 ────────────────────────────────────────────────────
document.getElementById("knobs").innerHTML = 손잡이.map(k => `
  <div class="k">
    <div class="t"><b>${k.name}</b><output id="o_${k.id}">${k.def}${k.unit}</output></div>
    <input type="range" id="r_${k.id}" min="${k.min}" max="${k.max}" step="1" value="${k.def}">
    <div class="sel">${k.sel} · ${k.prop}</div>
  </div>`).join("");
손잡이.forEach(k => {
  document.getElementById("r_" + k.id).addEventListener("input", e => {
    값[k.id] = +e.target.value; 칠하기();
  });
});

document.getElementById("reset").addEventListener("click", () => {
  손잡이.forEach(k => { 값[k.id] = k.def;
    document.getElementById("r_" + k.id).value = k.def; });
  비율 = 1.25; 칠하기();
});
document.getElementById("copy").addEventListener("click", async () => {
  const 바뀐 = 손잡이.filter(k => 값[k.id] !== k.def)
    .map(k => `${k.name}: ${값[k.id]}${k.unit}   (${k.sel} · ${k.prop})`);
  if (Math.abs(비율 - 1.25) > 0.01) 바뀐.push(`좌우 비율: 1 : ${비율.toFixed(2)}`);
  const 글 = 바뀐.length ? 바뀐.join("\\n") : "바꾼 값이 없습니다.";
  try {
    await navigator.clipboard.writeText(글);
    document.getElementById("msg").textContent = "복사했습니다 — 채팅에 붙여 넣으세요";
  } catch {
    document.getElementById("msg").textContent = "복사가 막혔습니다 — 콘솔에 출력했습니다";
    console.log(글);
  }
  setTimeout(() => document.getElementById("msg").textContent = "", 4000);
});

v.addEventListener("load", () => setTimeout(칠하기, 60));
window.addEventListener("resize", 손잡이위치);
</script>
"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not REPORT.exists():
        print(f"🔴 {REPORT} 가 없습니다. 먼저 run.py 를 돌리세요.")
        raise SystemExit(1)

    # 🔴 `</script>` 를 그대로 두면 담는 쪽 스크립트가 거기서 끊긴다
    문서 = REPORT.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
    표 = [{"id": i, "name": n, "sel": s, "prop": p,
          "min": lo, "max": hi, "def": d, "unit": u}
          for i, n, s, p, lo, hi, d, u in 손잡이]

    OUT.write_text(
        TEMPLATE.replace("__DOC__", 문서)
                .replace("__KNOBS__", json.dumps(표, ensure_ascii=False)),
        encoding="utf-8")
    print(f"→ {OUT.name} ({OUT.stat().st_size/1024:.0f}KB) · 손잡이 {len(표)}개")
    print("  브라우저로 열어 맞춘 뒤 「값 복사」를 눌러 채팅에 붙이세요.")


if __name__ == "__main__":
    main()
